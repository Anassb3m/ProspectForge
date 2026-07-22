"""SQLAlchemy 2.0 models — prospects, outreach events, users."""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
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
    contact_confidence: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
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
    contact_people: Mapped[list["ContactPerson"]] = relationship(
        back_populates="prospect", cascade="all, delete-orphan", lazy="selectin"
    )
    contact_points: Mapped[list["ContactPoint"]] = relationship(
        back_populates="prospect", cascade="all, delete-orphan", lazy="selectin"
    )
    contact_discovery_runs: Mapped[list["ContactDiscoveryRun"]] = relationship(
        back_populates="prospect", cascade="all, delete-orphan", lazy="selectin"
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
    def email_redacted(self) -> str | None:
        if not self.email or "@" not in self.email:
            return None
        local, domain = self.email.split("@", 1)
        return f"{local[:1]}***@{domain}"

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


class ContactPerson(Base):
    """A public professional identity associated with one prospect."""

    __tablename__ = "contact_people"
    __table_args__ = (
        UniqueConstraint(
            "prospect_id", "normalized_name", "normalized_role", name="uq_contact_person_identity"
        ),
        CheckConstraint(
            "role_category IN ('owner','executive','operations','service','maintenance',"
            "'technical','exploitation','administration_finance','commercial',"
            "'planning_methods','legal_representative','other','unknown')",
            name="ck_contact_people_role_category",
        ),
        CheckConstraint(
            "company_match_state IN ('exact','strong','probable','ambiguous','conflicting','unknown')",
            name="ck_contact_people_company_match",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prospect_id: Mapped[int] = mapped_column(
        ForeignKey("prospects.id", ondelete="CASCADE"), index=True
    )
    full_name: Mapped[str] = mapped_column(String(200))
    normalized_name: Mapped[str] = mapped_column(String(200), index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    job_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    normalized_role: Mapped[str] = mapped_column(String(120), default="unknown", server_default="unknown")
    role_category: Mapped[str] = mapped_column(String(40), default="unknown", server_default="unknown")
    buyer_role_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    company_match_state: Mapped[str] = mapped_column(
        String(20), default="unknown", server_default="unknown"
    )
    identity_confidence: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    linkedin_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_primary_candidate: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    manually_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    prospect: Mapped["Prospect"] = relationship(back_populates="contact_people")
    contact_points: Mapped[list["ContactPoint"]] = relationship(back_populates="person")
    evidence: Mapped[list["ContactEvidence"]] = relationship(back_populates="person")


class ContactPoint(Base):
    """A source-backed route to a company or person; values may still require review."""

    __tablename__ = "contact_points"
    __table_args__ = (
        UniqueConstraint("prospect_id", "kind", "value_normalized", name="uq_contact_point_value"),
        CheckConstraint(
            "kind IN ('email','phone','contact_form','linkedin','website',"
            "'generic_contact_page','other')",
            name="ck_contact_points_kind",
        ),
        CheckConstraint(
            "publication_state IN ('published_personal','published_role','published_generic',"
            "'not_published','unknown')",
            name="ck_contact_points_publication",
        ),
        CheckConstraint(
            "deliverability_state IN ('deliverable','catch_all','risky','invalid','indeterminate',"
            "'unchecked','error')",
            name="ck_contact_points_deliverability",
        ),
        CheckConstraint(
            "person_match_state IN ('exact_person_published','exact_person_pattern_confirmed',"
            "'strong_person_match','role_mailbox','generic_company_mailbox','pattern_inferred',"
            "'name_only_guess','conflicting','unknown')",
            name="ck_contact_points_person_match",
        ),
        CheckConstraint(
            "utility_state IN ('usable_personal','usable_role','usable_generic',"
            "'manual_confirmation_required','verification_required','invalid','suppressed',"
            "'stale','no_contact')",
            name="ck_contact_points_utility",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prospect_id: Mapped[int] = mapped_column(
        ForeignKey("prospects.id", ondelete="CASCADE"), index=True
    )
    person_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contact_people.id", ondelete="SET NULL"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(30), index=True)
    value_normalized: Mapped[str] = mapped_column(String(500))
    value_display: Mapped[str] = mapped_column(String(500))
    domain: Mapped[Optional[str]] = mapped_column(String(253), nullable=True, index=True)
    source_class: Mapped[str] = mapped_column(String(50), default="legacy", server_default="legacy")
    publication_state: Mapped[str] = mapped_column(
        String(30), default="unknown", server_default="unknown"
    )
    person_match_state: Mapped[str] = mapped_column(
        String(40), default="unknown", server_default="unknown"
    )
    deliverability_state: Mapped[str] = mapped_column(
        String(30), default="unchecked", server_default="unchecked"
    )
    verification_state: Mapped[str] = mapped_column(
        String(30), default="unchecked", server_default="unchecked"
    )
    utility_state: Mapped[str] = mapped_column(
        String(40), default="no_contact", server_default="no_contact", index=True
    )
    confidence_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    is_usable: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", index=True)
    requires_manual_review: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1"
    )
    is_suppressed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    manually_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    prospect: Mapped["Prospect"] = relationship(back_populates="contact_points")
    person: Mapped[Optional["ContactPerson"]] = relationship(back_populates="contact_points")
    evidence: Mapped[list["ContactEvidence"]] = relationship(back_populates="contact_point")
    verification_events: Mapped[list["ContactVerificationEvent"]] = relationship(
        back_populates="contact_point", cascade="all, delete-orphan"
    )


class ContactEvidence(Base):
    __tablename__ = "contact_evidence"
    __table_args__ = (UniqueConstraint("fingerprint", name="uq_contact_evidence_fingerprint"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prospect_id: Mapped[int] = mapped_column(
        ForeignKey("prospects.id", ondelete="CASCADE"), index=True
    )
    person_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contact_people.id", ondelete="SET NULL"), nullable=True, index=True
    )
    contact_point_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contact_points.id", ondelete="SET NULL"), nullable=True, index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    source_adapter: Mapped[str] = mapped_column(String(60), index=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_domain: Mapped[Optional[str]] = mapped_column(String(253), nullable=True)
    source_record_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    page_title: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    evidence_type: Mapped[str] = mapped_column(String(60), index=True)
    excerpt: Mapped[Optional[str]] = mapped_column(String(600), nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confidence: Mapped[int] = mapped_column(Integer, default=50, server_default="50")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    raw_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    person: Mapped[Optional["ContactPerson"]] = relationship(back_populates="evidence")
    contact_point: Mapped[Optional["ContactPoint"]] = relationship(back_populates="evidence")


class ContactDiscoveryRun(Base):
    __tablename__ = "contact_discovery_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prospect_id: Mapped[int] = mapped_column(
        ForeignKey("prospects.id", ondelete="CASCADE"), index=True
    )
    run_type: Mapped[str] = mapped_column(String(30), default="full", server_default="full")
    triggered_by: Mapped[str] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(30), default="running", server_default="running", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    adapters_requested: Mapped[Optional[list[Any]]] = mapped_column(JSON, nullable=True)
    adapters_completed: Mapped[Optional[list[Any]]] = mapped_column(JSON, nullable=True)
    pages_examined: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    people_found: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    contact_points_found: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    published_emails_found: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    generated_candidates: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    verified_deliverable: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    catch_all: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    invalid: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    manual_review_required: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    errors: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    timings: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    result_summary: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    prospect: Mapped["Prospect"] = relationship(back_populates="contact_discovery_runs")


class ContactVerificationEvent(Base):
    __tablename__ = "contact_verification_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contact_point_id: Mapped[int] = mapped_column(
        ForeignKey("contact_points.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(60))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deliverability_state: Mapped[str] = mapped_column(String(30))
    is_catch_all: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    smtp_state: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    mx_state: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    raw_summary: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    contact_point: Mapped["ContactPoint"] = relationship(back_populates="verification_events")


class ContactManualReview(Base):
    __tablename__ = "contact_manual_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contact_point_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contact_points.id", ondelete="SET NULL"), nullable=True, index=True
    )
    person_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contact_people.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reviewer: Mapped[str] = mapped_column(String(150))
    decision: Mapped[str] = mapped_column(String(40))
    previous_state: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    new_state: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


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


# ── Multi-Market Domain Models ────────────────────────────────────────────────

class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    canonical_name: Mapped[str] = mapped_column(String(255), index=True)
    legal_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    country_code: Mapped[str] = mapped_column(String(2), default="GB", index=True)
    jurisdiction_code: Mapped[str] = mapped_column(String(10), default="GB-EW")
    legal_form_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_status: Mapped[str] = mapped_column(String(50), default="active", index=True)
    incorporated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    dissolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    primary_domain_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    merged_into_company_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("companies.id"), nullable=True
    )
    record_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    identifiers: Mapped[list["CompanyIdentifier"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    domains: Mapped[list["CompanyDomain"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    classifications: Mapped[list["CompanyClassification"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    locations: Mapped[list["CompanyLocation"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    estimates: Mapped[list["CompanyEstimate"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    opportunities: Mapped[list["Opportunity"]] = relationship(back_populates="company", cascade="all, delete-orphan")


class CompanyIdentifier(Base):
    __tablename__ = "company_identifiers"
    __table_args__ = (UniqueConstraint("scheme", "value_normalized", name="uq_identifier_scheme_value"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    scheme: Mapped[str] = mapped_column(String(50), index=True)
    value_normalized: Mapped[str] = mapped_column(String(100), index=True)
    value_display: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    source_record_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="identifiers")


class CompanyName(Base):
    __tablename__ = "company_names"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    name_type: Mapped[str] = mapped_column(String(50), default="legal")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CompanyClassification(Base):
    __tablename__ = "company_classifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    scheme: Mapped[str] = mapped_column(String(50), index=True)
    code: Mapped[str] = mapped_column(String(50), index=True)
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="classifications")


class CompanyLocation(Base):
    __tablename__ = "company_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    location_type: Mapped[str] = mapped_column(String(50), default="registered")
    street: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    locality: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    country_code: Mapped[str] = mapped_column(String(2), default="GB")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="locations")


class CompanyDomain(Base):
    __tablename__ = "company_domains"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    domain_normalized: Mapped[str] = mapped_column(String(255), index=True)
    domain_role: Mapped[str] = mapped_column(String(50), default="primary")
    verification_state: Mapped[str] = mapped_column(String(50), default="candidate")
    match_score: Mapped[float] = mapped_column(Float, default=0.0)
    match_reasons_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped["Company"] = relationship(back_populates="domains")


class CompanyEstimate(Base):
    __tablename__ = "company_estimates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    estimate_type: Mapped[str] = mapped_column(String(50), default="field_technicians")
    lower_bound: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    upper_bound: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    point_estimate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    method_code: Mapped[str] = mapped_column(String(50), default="composite")
    confidence: Mapped[str] = mapped_column(String(20), default="medium")
    assumptions_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped["Company"] = relationship(back_populates="estimates")


class SourceConnector(Base):
    __tablename__ = "source_connectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    country_coverage: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SourceRun(Base):
    __tablename__ = "source_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    connector_code: Mapped[str] = mapped_column(String(50), index=True)
    play_version_code: Mapped[str] = mapped_column(String(100), index=True)
    query_config_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="running")
    items_discovered: Mapped[int] = mapped_column(Integer, default=0)
    items_normalized: Mapped[int] = mapped_column(Integer, default=0)
    items_rejected: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    records: Mapped[list["SourceRecord"]] = relationship(back_populates="source_run")


class SourceRecord(Base):
    __tablename__ = "source_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("source_runs.id"), index=True
    )
    external_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    record_type: Mapped[str] = mapped_column(String(50), default="company")
    payload_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    payload_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source_run: Mapped["SourceRun"] = relationship(back_populates="records")


class MarketPlayVersion(Base):
    __tablename__ = "market_play_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    play_code: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    status: Mapped[str] = mapped_column(String(20), default="pilot")
    jurisdiction: Mapped[str] = mapped_column(String(10), default="GB")
    locale: Mapped[str] = mapped_column(String(10), default="en-GB")
    icp_config_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    opportunities: Mapped[list["Opportunity"]] = relationship(back_populates="play_version")


class Opportunity(Base):
    __tablename__ = "opportunities"
    __table_args__ = (UniqueConstraint("company_id", "play_version_id", name="uq_company_play_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    play_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("market_play_versions.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="discovered", index=True)
    status_reason_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    latest_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="opportunities")
    play_version: Mapped["MarketPlayVersion"] = relationship(back_populates="opportunities")
    evidence_items: Mapped[list["EvidenceItem"]] = relationship(back_populates="opportunity")
    compliance_decisions: Mapped[list["ComplianceDecision"]] = relationship(back_populates="opportunity")
    score_snapshots: Mapped[list["ScoreSnapshot"]] = relationship(back_populates="opportunity")


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    opportunity_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(100), index=True)
    category: Mapped[str] = mapped_column(String(50), index=True)
    evidence_text: Mapped[str] = mapped_column(Text)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    verification_state: Mapped[str] = mapped_column(String(50), default="verified")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    opportunity: Mapped[Optional["Opportunity"]] = relationship(back_populates="evidence_items")


class Person(Base):
    __tablename__ = "people"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    full_name: Mapped[str] = mapped_column(String(200), index=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    roles: Mapped[list["PersonRole"]] = relationship(back_populates="person", cascade="all, delete-orphan")


class PersonRole(Base):
    __tablename__ = "person_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("people.id", ondelete="CASCADE"), index=True
    )
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    raw_title: Mapped[str] = mapped_column(String(200))
    normalized_role: Mapped[str] = mapped_column(String(100), index=True)
    seniority: Mapped[str] = mapped_column(String(50), default="executive")
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source_evidence_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    person: Mapped["Person"] = relationship(back_populates="roles")


class CompliancePolicy(Base):
    __tablename__ = "compliance_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(50), index=True)
    jurisdiction: Mapped[str] = mapped_column(String(10))
    rules_config_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ComplianceDecision(Base):
    __tablename__ = "compliance_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    opportunity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("opportunities.id", ondelete="CASCADE"), index=True
    )
    policy_code: Mapped[str] = mapped_column(String(50))
    decision: Mapped[str] = mapped_column(String(20))
    reasons_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    opportunity: Mapped["Opportunity"] = relationship(back_populates="compliance_decisions")


class ScoreSnapshot(Base):
    __tablename__ = "score_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    opportunity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("opportunities.id", ondelete="CASCADE"), index=True
    )
    total_score: Mapped[float] = mapped_column(Float)
    hard_gates_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    breakdown_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    opportunity: Mapped["Opportunity"] = relationship(back_populates="score_snapshots")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200))
    play_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("market_play_versions.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="draft")
    daily_send_cap: Mapped[int] = mapped_column(Integer, default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    touches: Mapped[list["Touch"]] = relationship(back_populates="campaign")


class Touch(Base):
    __tablename__ = "touches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("campaigns.id"), index=True
    )
    opportunity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("opportunities.id"), index=True
    )
    step_number: Mapped[int] = mapped_column(Integer, default=1)
    channel: Mapped[str] = mapped_column(String(50), default="Email")
    status: Mapped[str] = mapped_column(String(50), default="scheduled")
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_citations_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    campaign: Mapped["Campaign"] = relationship(back_populates="touches")


# ── Durable Runtime Models (Phase 2) ─────────────────────────────────────────

class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    play_code: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(30), default="running", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    stats_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)


class WorkItem(Base):
    __tablename__ = "work_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipeline_runs.id"), index=True)
    task_name: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    lock_lease_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    pipeline_run: Mapped["PipelineRun"] = relationship()


class SourceRateBudget(Base):
    __tablename__ = "source_rate_budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    daily_limit: Mapped[int] = mapped_column(Integer)
    used_today: Mapped[int] = mapped_column(Integer, default=0)
    reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SourceCheckpoint(Base):
    __tablename__ = "source_checkpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    high_water_mark: Mapped[str] = mapped_column(String(200))
    last_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FailedWorkItem(Base):
    __tablename__ = "failed_work_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_work_item_id: Mapped[str] = mapped_column(String(36), index=True)
    pipeline_run_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    task_name: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    error_message: Mapped[str] = mapped_column(Text)
    traceback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
