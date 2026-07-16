"""SQLAlchemy 2.0 models — prospects, outreach events, users."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# ── Constants (shared with schemas / validation) ─────────────────────────────

SECTORS = (
    "Construction",
    "Manufacturing",
    "Logistics",
    "Engineering",
    "Professional Services",
    "Field Services",
    "Facilities / Maintenance",
    "IT / Digital",
    "Other",
)

COMPANY_SIZES = ("1-10", "11-50", "51-200", "200+", "unknown")

SIGNAL_TYPES = (
    "DECP_WIN",
    "BOAMP_WIN",
    "PUBLIC_AWARD",
    "REGISTRY_FIELD",
    "STRUCTURAL",
    "MOROCCO_OPS",
    "PAIN_POST",
    "REGISTRY_IT",  # legacy — penalized in V3 field play
    "OTHER",
)

SOURCES = ("DECP", "BOAMP", "LinkedIn", "Manual", "Registry", "Annuaire", "Website", "Jobs")

ACQUISITION_STAGES = (
    "discovered",
    "researching",
    "enriched",
    "human_review_required",
    "contact_ready",
    "in_outreach",
    "conversation",
    "meeting",
    "parked",
    "suppressed",
)

READINESS_STATES = (
    "insufficient_identity",
    "research_required",
    "buyer_required",
    "contact_required",
    "proof_required",
    "human_review_required",
    "contact_ready",
    "suppressed",
)

CONTACT_VERIFICATION_STATES = (
    "untested",
    "syntax_valid",
    "domain_valid",
    "deliverable",
    "catch_all",
    "risky",
    "indeterminate",
    "invalid",
    "bounced",
    "confirmed_by_reply",
    "published_personal",
    "published_generic",
    "domain_and_pattern_only",
    "verified",  # legacy alias
    "likely",
    "unverified",
    "needs_review",
    "none",
)

PRIORITY_LEVELS = ("High", "Medium", "Low")

CHANNELS = ("LinkedIn", "Email", "Phone")

CONTACT_SOURCES = ("reacher", "theharvester", "manual", "sirene", "none")
CONTACT_CONFIDENCE = ("verified", "likely", "unverified", "needs_review", "none")

EVENT_TYPES = (
    "New",
    "Sent",
    "Replied",
    "Refused",
    "MeetingBooked",
    "PositiveConversation",
    "ProposalSent",
    "ClosedWon",
    "ClosedLost",
    "OptOut",
)

# Kanban columns map event types into pipeline stages
KANBAN_COLUMNS = {
    "New": ("New",),
    "Sent": ("Sent",),
    "Replied": ("Replied", "PositiveConversation"),
    "Meeting": ("MeetingBooked", "ProposalSent"),
    "Closed": ("ClosedWon", "ClosedLost", "Refused", "OptOut"),
}

# Event types that count as "contacted" for metrics
CONTACTED_EVENT_TYPES = (
    "Sent",
    "Replied",
    "Refused",
    "MeetingBooked",
    "PositiveConversation",
    "ProposalSent",
    "ClosedWon",
    "ClosedLost",
)

REPLY_EVENT_TYPES = ("Replied", "PositiveConversation", "MeetingBooked", "ProposalSent", "ClosedWon")
MEETING_EVENT_TYPES = ("MeetingBooked", "ProposalSent", "ClosedWon")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Prospect(Base):
    __tablename__ = "prospects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_name: Mapped[str] = mapped_column(String(200), index=True)
    sector: Mapped[str] = mapped_column(String(100))
    company_size: Mapped[str] = mapped_column(String(20))
    signal_type: Mapped[str] = mapped_column(String(50), index=True)
    signal_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    decision_maker_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    decision_maker_title: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    # French registry / DECP discovery fields
    siren: Mapped[Optional[str]] = mapped_column(String(9), index=True, nullable=True)
    siret: Mapped[Optional[str]] = mapped_column(String(14), unique=True, nullable=True, index=True)
    naf_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)
    award_history: Mapped[Optional[list[Any]]] = mapped_column(JSON, nullable=True)
    last_tender_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    contact_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    contact_confidence: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    diffusion_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    contact_candidates: Mapped[Optional[list[Any]]] = mapped_column(JSON, nullable=True)
    needs_manual_review: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", index=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Acquisition intelligence (v2.2)
    dirigeants: Mapped[Optional[list[Any]]] = mapped_column(JSON, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fit_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    timing_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    contactability_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    acquisition_score: Mapped[int] = mapped_column(Integer, default=50, server_default="50", index=True)
    score_breakdown: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    acquisition_stage: Mapped[str] = mapped_column(
        String(30), default="discovered", server_default="discovered", index=True
    )
    last_enriched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── V3 commercial / evidence fields ──────────────────────────────────
    market_play_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    pain_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    trigger_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    authority_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    value_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    data_quality_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    opportunity_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0", index=True)
    readiness_state: Mapped[str] = mapped_column(
        String(40), default="research_required", server_default="research_required", index=True
    )
    readiness_failures: Mapped[Optional[list[Any]]] = mapped_column(JSON, nullable=True)
    suspected_pain: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    why_now: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_buyer_role: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    personalization_brief: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_offer: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    evidence_json: Mapped[Optional[list[Any]]] = mapped_column(JSON, nullable=True)
    manual_review_state: Mapped[str] = mapped_column(
        String(30), default="unreviewed", server_default="unreviewed", index=True
    )
    qualification_decision: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    qualification_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_discovery_state: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    # published | inferred | guessed | user_supplied

    # GDPR / compliance trail
    data_source: Mapped[str] = mapped_column(String(200))
    informed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    opted_out: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    opted_out_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    urgency_score: Mapped[int] = mapped_column(Integer, default=50, server_default="50", index=True)
    priority_level: Mapped[str] = mapped_column(String(10), default="Medium", server_default="Medium")
    source: Mapped[str] = mapped_column(String(50))

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    anonymized: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    outreach_events: Mapped[list["OutreachEvent"]] = relationship(
        back_populates="prospect",
        order_by="OutreachEvent.event_date",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def current_status(self) -> str:
        """Derived from most recent outreach event — never stored redundantly."""
        if not self.outreach_events:
            return "New"
        return self.outreach_events[-1].event_type

    @property
    def last_event_date(self) -> datetime | None:
        if not self.outreach_events:
            return None
        return self.outreach_events[-1].event_date

    @property
    def next_action(self) -> str | None:
        if not self.outreach_events:
            return None
        return self.outreach_events[-1].next_action

    @property
    def next_action_date(self) -> datetime | None:
        if not self.outreach_events:
            return None
        return self.outreach_events[-1].next_action_date

    @property
    def award_count(self) -> int:
        if not self.award_history:
            return 0
        return len(self.award_history)

    @property
    def award_total_value(self) -> float:
        if not self.award_history:
            return 0.0
        total = 0.0
        for a in self.award_history:
            try:
                total += float(a.get("montant") or 0)
            except (TypeError, ValueError):
                pass
        return total

    @property
    def contact_status(self) -> str:
        conf = (self.contact_confidence or "").lower()
        disc = (self.contact_discovery_state or "").lower()
        if conf in ("confirmed_by_reply", "published_personal", "deliverable", "verified"):
            return "Usable contact"
        if conf in ("catch_all", "indeterminate") or disc == "guessed":
            return "Guessed / risky — review"
        if self.email and conf in ("likely", "published_generic", "unverified"):
            return "Email candidate"
        if self.needs_manual_review or conf in ("needs_review", "none"):
            return "Needs review"
        return "No email yet"

    @property
    def score_badges(self) -> list[str]:
        if self.score_breakdown and isinstance(self.score_breakdown, dict):
            badges = self.score_breakdown.get("badges") or []
            if badges:
                return list(badges)[:8]
        badges: list[str] = []
        if self.signal_type in ("DECP_WIN", "BOAMP_WIN", "PUBLIC_AWARD"):
            badges.append("Public award")
        if self.signal_type == "REGISTRY_FIELD":
            badges.append("Field registry")
        if self.award_count >= 2:
            badges.append(f"{self.award_count} awards")
        if self.company_size in ("11-50", "51-200"):
            badges.append("SME fit")
        if self.decision_maker_name:
            badges.append("Person named")
        if self.readiness_state == "contact_ready":
            badges.append("Meeting-ready")
        elif self.readiness_state == "human_review_required":
            badges.append("Needs human OK")
        return badges

    @property
    def why_this_lead(self) -> list[str]:
        if self.score_breakdown and isinstance(self.score_breakdown, dict):
            return list(self.score_breakdown.get("reasons") or [])[:5]
        out = []
        if self.why_now:
            out.append(self.why_now)
        if self.suspected_pain:
            out.append(self.suspected_pain)
        return out[:5]

    @property
    def primary_rank(self) -> int:
        return self.opportunity_score or self.acquisition_score or self.urgency_score or 0


class OutreachEvent(Base):
    __tablename__ = "outreach_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(20))
    event_type: Mapped[str] = mapped_column(String(20), index=True)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_action: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    next_action_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # V3 structured fields (optional)
    event_kind: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    pipeline_stage_after: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    personalization_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    objection_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    prospect: Mapped["Prospect"] = relationship(back_populates="outreach_events")


class MarketPlay(Base):
    __tablename__ = "market_plays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    offer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    offer_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvidenceSignal(Base):
    """Independent evidence item — not a single signal_type field."""

    __tablename__ = "evidence_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(30), index=True)
    # structural_fit, pain, trigger, value, exclusion, contact, compliance
    signal_type: Mapped[str] = mapped_column(String(80), index=True)
    label: Mapped[str] = mapped_column(String(200))
    evidence_text: Mapped[str] = mapped_column(Text)
    evidence_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, default=50, server_default="50")
    strength: Mapped[int] = mapped_column(Integer, default=50, server_default="50")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    manually_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    observed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QualificationReview(Base):
    __tablename__ = "qualification_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id", ondelete="CASCADE"), index=True)
    reviewer_email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    decision: Mapped[str] = mapped_column(String(30))  # accept, reject, research_more, park
    fit_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    pain_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    trigger_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    buyer_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    contact_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    offer_match_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    reason_codes: Mapped[Optional[list[Any]]] = mapped_column(JSON, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id", ondelete="CASCADE"), index=True)
    task_type: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(300))
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=50, server_default="50")
    status: Mapped[str] = mapped_column(String(20), default="open", server_default="open", index=True)
    origin: Mapped[str] = mapped_column(String(20), default="manual", server_default="manual")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class SuppressionEntry(Base):
    __tablename__ = "suppression_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)  # email, domain, siren, person
    value_normalized: Mapped[str] = mapped_column(String(320), index=True)
    reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    adapter: Mapped[str] = mapped_column(String(40), index=True)
    market_play_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="running", server_default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    stats_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    log_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class OfferAsset(Base):
    __tablename__ = "offer_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    market_play_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    asset_type: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    url_or_path: Mapped[str] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    proof_tags: Mapped[Optional[list[Any]]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
