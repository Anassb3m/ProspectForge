"""Pydantic request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import (
    CHANNELS,
    COMPANY_SIZES,
    EVENT_TYPES,
    SECTORS,
    SIGNAL_TYPES,
    SOURCES,
)


# ── Auth ─────────────────────────────────────────────────────────────────────


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: str | None = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class LoginForm(BaseModel):
    email: EmailStr
    password: str


# ── Outreach events ──────────────────────────────────────────────────────────


class EventCreate(BaseModel):
    channel: str
    event_type: str
    notes: Optional[str] = None
    next_action: Optional[str] = Field(default=None, max_length=300)
    next_action_date: Optional[datetime] = None
    event_date: Optional[datetime] = None

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        if v not in CHANNELS:
            raise ValueError(f"channel must be one of {CHANNELS}")
        return v

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if v not in EVENT_TYPES:
            raise ValueError(f"event_type must be one of {EVENT_TYPES}")
        return v


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prospect_id: int
    channel: str
    event_type: str
    event_date: datetime
    notes: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[datetime] = None


# ── Prospects ────────────────────────────────────────────────────────────────


class ProspectCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    sector: str
    company_size: str
    signal_type: str
    signal_details: Optional[str] = None
    decision_maker_name: Optional[str] = Field(default=None, max_length=150)
    decision_maker_title: Optional[str] = Field(default=None, max_length=150)
    linkedin_url: Optional[str] = Field(default=None, max_length=300)
    email: Optional[str] = Field(default=None, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=50)
    website: Optional[str] = Field(default=None, max_length=300)
    siren: Optional[str] = Field(default=None, max_length=9)
    siret: Optional[str] = Field(default=None, max_length=14)
    naf_code: Optional[str] = Field(default=None, max_length=10)
    data_source: str = Field(min_length=1, max_length=200)
    informed_at: Optional[datetime] = None
    source: str
    notes: Optional[str] = None

    @field_validator("sector")
    @classmethod
    def validate_sector(cls, v: str) -> str:
        if v not in SECTORS:
            raise ValueError(f"sector must be one of {SECTORS}")
        return v

    @field_validator("company_size")
    @classmethod
    def validate_company_size(cls, v: str) -> str:
        if v not in COMPANY_SIZES:
            raise ValueError(f"company_size must be one of {COMPANY_SIZES}")
        return v

    @field_validator("signal_type")
    @classmethod
    def validate_signal_type(cls, v: str) -> str:
        if v not in SIGNAL_TYPES:
            raise ValueError(f"signal_type must be one of {SIGNAL_TYPES}")
        return v

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if v not in SOURCES:
            raise ValueError(f"source must be one of {SOURCES}")
        return v


class ProspectUpdate(BaseModel):
    company_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    sector: Optional[str] = None
    company_size: Optional[str] = None
    signal_type: Optional[str] = None
    signal_details: Optional[str] = None
    decision_maker_name: Optional[str] = Field(default=None, max_length=150)
    decision_maker_title: Optional[str] = Field(default=None, max_length=150)
    linkedin_url: Optional[str] = Field(default=None, max_length=300)
    email: Optional[str] = Field(default=None, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=50)
    website: Optional[str] = Field(default=None, max_length=300)
    data_source: Optional[str] = Field(default=None, max_length=200)
    informed_at: Optional[datetime] = None
    source: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("sector")
    @classmethod
    def validate_sector(cls, v: str | None) -> str | None:
        if v is not None and v not in SECTORS:
            raise ValueError(f"sector must be one of {SECTORS}")
        return v

    @field_validator("company_size")
    @classmethod
    def validate_company_size(cls, v: str | None) -> str | None:
        if v is not None and v not in COMPANY_SIZES:
            raise ValueError(f"company_size must be one of {COMPANY_SIZES}")
        return v

    @field_validator("signal_type")
    @classmethod
    def validate_signal_type(cls, v: str | None) -> str | None:
        if v is not None and v not in SIGNAL_TYPES:
            raise ValueError(f"signal_type must be one of {SIGNAL_TYPES}")
        return v

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str | None) -> str | None:
        if v is not None and v not in SOURCES:
            raise ValueError(f"source must be one of {SOURCES}")
        return v


class ProspectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | str
    company_name: str
    sector: str
    company_size: str
    signal_type: str
    signal_details: Optional[str] = None
    decision_maker_name: Optional[str] = None
    decision_maker_title: Optional[str] = None
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    siren: Optional[str] = None
    siret: Optional[str] = None
    naf_code: Optional[str] = None
    award_history: Optional[list] = None
    last_tender_date: Optional[datetime] = None
    contact_source: Optional[str] = None
    contact_confidence: Optional[str] = None
    needs_manual_review: bool = False
    data_source: str
    informed_at: Optional[datetime] = None
    opted_out: bool
    opted_out_at: Optional[datetime] = None
    urgency_score: int
    priority_level: str
    source: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    current_status: str = "New"
    next_action: Optional[str] = None
    next_action_date: Optional[datetime] = None
    contact_status: str = "No email yet"
    award_count: int = 0
    award_total_value: float = 0.0
    score_badges: list[str] = []
    why_this_lead: list[str] = []
    fit_score: int = 0
    timing_score: int = 0
    contactability_score: int = 0
    acquisition_score: int = 0
    acquisition_stage: str = "discovered"
    city: Optional[str] = None
    department: Optional[str] = None
    dirigeants: Optional[list] = None
    market_play_code: Optional[str] = None
    opportunity_score: int = 0
    pain_score: int = 0
    trigger_score: int = 0
    authority_score: int = 0
    readiness_state: Optional[str] = None
    readiness_failures: Optional[list] = None
    suspected_pain: Optional[str] = None
    why_now: Optional[str] = None
    recommended_buyer_role: Optional[str] = None
    personalization_brief: Optional[str] = None
    recommended_offer: Optional[str] = None
    manual_review_state: Optional[str] = None
    contact_discovery_state: Optional[str] = None


class ProspectDetail(ProspectOut):
    outreach_events: list[EventOut] = []


class ProspectListResponse(BaseModel):
    items: list[ProspectOut]
    total: int
    page: int
    page_size: int


class BulkStatusUpdate(BaseModel):
    prospect_ids: list[int | str]
    channel: str = "Email"
    event_type: str
    notes: Optional[str] = None

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        if v not in CHANNELS:
            raise ValueError(f"channel must be one of {CHANNELS}")
        return v

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if v not in EVENT_TYPES:
            raise ValueError(f"event_type must be one of {EVENT_TYPES}")
        return v


class ImportRowError(BaseModel):
    row: int
    errors: list[str]


class ImportResult(BaseModel):
    created: int
    failed: int
    errors: list[ImportRowError]


# ── Dashboard ────────────────────────────────────────────────────────────────


class SignalTypeMetrics(BaseModel):
    signal_type: str
    total: int
    contacted: int
    replied: int
    reply_rate: float


class ChannelMetrics(BaseModel):
    channel: str
    sent: int
    replied: int
    reply_rate: float


class ObjectionNote(BaseModel):
    note: str
    count: int


class DashboardMetrics(BaseModel):
    # Section A: Today's priorities
    opportunities_awaiting_qualification: int = 0
    contacts_awaiting_review: int = 0
    drafts_awaiting_approval: int = 0
    overdue_follow_ups: int = 0
    failed_or_blocked_jobs: int = 0
    replies_needing_classification: int = 0

    # Section B: Funnel counts
    funnel_universe: int = 0
    funnel_icp_eligible: int = 0
    funnel_domain_verified: int = 0
    funnel_evidence_enriched: int = 0
    funnel_human_accepted: int = 0
    funnel_contact_ready: int = 0
    funnel_in_outreach: int = 0
    funnel_positive_reply: int = 0
    funnel_meeting: int = 0
    funnel_proposal: int = 0
    funnel_won: int = 0

    # Section C: Pipeline throughput
    companies_imported_per_day: float = 0.0
    opportunities_created_per_day: float = 0.0
    qualification_acceptance_rate: float = 0.0
    contact_ready_yield: float = 0.0
    duplicate_rate: float = 0.0
    domain_verification_rate: float = 0.0
    evidence_coverage: float = 0.0
    stale_data_count: int = 0

    # Legacy fields (to keep for backward compatibility or till template fully replaced)
    total_prospects: int = 0
    contacted_this_week: int = 0
    reply_rate: float = 0.0
    meeting_rate: float = 0.0
    by_signal_type: list[SignalTypeMetrics] = Field(default_factory=list)
    by_channel: list[ChannelMetrics] = Field(default_factory=list)
    common_objections: list[ObjectionNote] = Field(default_factory=list)
    high_priority_count: int = 0
    follow_ups_due_count: int = 0
    new_decp_this_week: int = 0
    verified_email_pct: float = 0.0
    needs_review_count: int = 0


class FollowUpItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    prospect_id: int
    company_name: str
    current_status: str
    priority_level: str
    urgency_score: int
    next_action: Optional[str] = None
    next_action_date: Optional[datetime] = None
    decision_maker_name: Optional[str] = None
    channel: Optional[str] = None
    days_overdue: int = 0


class EnrichRequest(BaseModel):
    person_name: Optional[str] = None
    domain: Optional[str] = None
    apply_best: bool = False
    run_harvester: bool = True
    verify: bool = True


class EmailCandidateOut(BaseModel):
    email: str
    pattern: Optional[str] = None
    priority: Optional[int] = None
    confidence: Optional[str] = None
    is_reachable: Optional[str] = None
    is_deliverable: Optional[bool] = None


class EnrichResult(BaseModel):
    domain: Optional[str] = None
    candidates: list[EmailCandidateOut] = []
    best_email: Optional[str] = None
    contact_source: Optional[str] = None
    contact_confidence: Optional[str] = None
    needs_manual_review: bool = True
    message: Optional[str] = None


class IngestionResult(BaseModel):
    awards: int = 0
    companies: int = 0
    created: int = 0
    updated: int = 0
    skipped_filter: int = 0
    skipped_sirene: int = 0
    errors: int = 0
