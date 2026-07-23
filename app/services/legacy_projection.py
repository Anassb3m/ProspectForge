from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Any, List

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

@dataclass
class LegacyProspectProxy:
    id: str
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
    award_history: Optional[List[Any]] = None
    last_tender_date: Optional[datetime] = None
    contact_source: Optional[str] = None
    contact_confidence: Optional[str] = None
    needs_manual_review: bool = False
    data_source: str = "normalized_v3"
    informed_at: Optional[datetime] = None
    opted_out: bool = False
    opted_out_at: Optional[datetime] = None
    urgency_score: int = 0
    priority_level: str = "Medium"
    source: str = "Unknown"
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    current_status: str = "New"
    next_action: Optional[str] = None
    next_action_date: Optional[datetime] = None
    contact_status: str = "No email yet"
    award_count: int = 0
    award_total_value: float = 0.0
    score_badges: List[str] = field(default_factory=list)
    why_this_lead: List[str] = field(default_factory=list)
    fit_score: int = 0
    timing_score: int = 0
    contactability_score: int = 0
    acquisition_score: int = 0
    acquisition_stage: str = "discovered"
    city: Optional[str] = None
    department: Optional[str] = None
    dirigeants: Optional[List[Any]] = None
    market_play_code: Optional[str] = None
    opportunity_score: int = 0
    pain_score: int = 0
    trigger_score: int = 0
    authority_score: int = 0
    readiness_state: Optional[str] = None
    readiness_failures: Optional[List[Any]] = None
    suspected_pain: Optional[str] = None
    why_now: Optional[str] = None
    recommended_buyer_role: Optional[str] = None
    personalization_brief: Optional[str] = None
    recommended_offer: Optional[str] = None
    contact_discovery_state: Optional[str] = None
    outreach_events: List[Any] = field(default_factory=list)
    legacy_id: Optional[int] = None

    @classmethod
    def from_models(cls, company: Any, opp: Any) -> "LegacyProspectProxy":
        return cls(
            id=opp.id,
            company_name=company.canonical_name,
            sector="Field Services", # Default placeholder
            company_size="unknown",
            signal_type="OTHER",
            priority_level=opp.priority,
            acquisition_stage=opp.status,
            urgency_score=int(opp.latest_score),
            opportunity_score=int(opp.latest_score),
            created_at=company.created_at,
            updated_at=opp.updated_at
        )
