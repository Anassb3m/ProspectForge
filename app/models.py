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
    "IT / Digital",
    "Other",
)

COMPANY_SIZES = ("1-10", "11-50", "51-200", "200+")

SIGNAL_TYPES = (
    "DECP_WIN",
    "BOAMP_WIN",
    "MOROCCO_OPS",
    "PAIN_POST",
    "REGISTRY_IT",
    "OTHER",
)

SOURCES = ("DECP", "BOAMP", "LinkedIn", "Manual", "Registry", "Annuaire")

ACQUISITION_STAGES = (
    "discovered",
    "enriched",
    "contact_ready",
    "in_outreach",
    "parked",
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
        if self.email and self.contact_confidence == "verified":
            return "Verified email"
        if self.email and self.contact_confidence in ("likely", "unverified"):
            return "Email found"
        if self.needs_manual_review or self.contact_confidence == "needs_review":
            return "Needs review"
        return "No email yet"

    @property
    def score_badges(self) -> list[str]:
        """Human-readable reasons — prefer ICP breakdown when present."""
        if self.score_breakdown and isinstance(self.score_breakdown, dict):
            badges = self.score_breakdown.get("badges") or []
            if badges:
                return list(badges)[:8]
        badges: list[str] = []
        if self.signal_type in ("DECP_WIN", "BOAMP_WIN"):
            badges.append("Public win")
        if self.signal_type == "REGISTRY_IT":
            badges.append("IT registry")
        if self.award_count >= 2:
            badges.append(f"{self.award_count} awards")
        details = (self.signal_details or "").lower()
        if "cybersécurité" in details or "cyber" in details:
            badges.append("Cyber")
        if self.naf_code and self.naf_code[:2] in ("62", "63", "58"):
            badges.append("IT NAF")
        if self.company_size in ("11-50", "51-200"):
            badges.append("SME fit")
        if self.decision_maker_name:
            badges.append("DM named")
        if self.priority_level == "High":
            badges.append("High urgency")
        return badges

    @property
    def why_this_lead(self) -> list[str]:
        if self.score_breakdown and isinstance(self.score_breakdown, dict):
            return list(self.score_breakdown.get("reasons") or [])[:5]
        return []

    @property
    def primary_rank(self) -> int:
        """Single number for queue sort — acquisition score preferred."""
        return self.acquisition_score or self.urgency_score or 0


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

    prospect: Mapped["Prospect"] = relationship(back_populates="outreach_events")
