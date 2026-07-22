from enum import Enum
from pydantic import BaseModel
from typing import Optional, List

class EvidenceCategory(str, Enum):
    STRUCTURAL_FIT = "structural_fit"
    TRIGGER = "trigger"
    TECHNOLOGY = "technology"
    NEGATIVE = "negative"

class SignalType(str, Enum):
    # Structural
    PUBLIC_SERVICE_DELIVERY = "PUBLIC_SERVICE_DELIVERY"
    FIELD_SERVICE_OPERATIONS = "FIELD_SERVICE_OPERATIONS"
    # Trigger
    PUBLIC_AWARD_RECENT = "PUBLIC_AWARD_RECENT"
    PUBLIC_AWARD_MULTI = "PUBLIC_AWARD_MULTI"
    # Negative
    BANKRUPT = "BANKRUPT"
    DISSOLVED = "DISSOLVED"
    NO_WEBSITE = "NO_WEBSITE"
    # Tech
    USES_EXCEL = "USES_EXCEL"
    USES_SAP = "USES_SAP"

class EvidenceExtraction(BaseModel):
    category: EvidenceCategory
    signal_type: SignalType
    label: str
    evidence_text: str
    source_type: str
    confidence: int
    strength: int
    manually_confirmed: bool = False
    evidence_url: Optional[str] = None

def evaluate_negative_rules(evidence_items: List[EvidenceExtraction]) -> bool:
    """Returns True if negative evidence makes this prospect invalid."""
    for item in evidence_items:
        if item.category == EvidenceCategory.NEGATIVE:
            if item.signal_type in [SignalType.BANKRUPT, SignalType.DISSOLVED]:
                return True
    return False
