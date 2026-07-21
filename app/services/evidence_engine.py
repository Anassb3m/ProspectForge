"""Website Evidence Extraction Engine."""

from dataclasses import dataclass
import re


@dataclass
class ExtractedEvidence:
    code: str
    category: str
    evidence_text: str
    confidence: float
    source_url: str | None = None


EVIDENCE_PATTERNS = [
    {
        "code": "OPERATIONS.COMPLEXITY.MULTI_BRANCH",
        "category": "complexity",
        "keywords": [r"\bbranches?\b", r"\bdepots?\b", r"\bregional offices?\b", r"\bagences?\b", r"\bmulti-?sites?\b"],
        "label": "Multi-branch or regional depot operations",
    },
    {
        "code": "OPERATIONS.COMPLEXITY.RECURRING_CONTRACTS",
        "category": "complexity",
        "keywords": [
            r"maintenance contracts?", r"planned preventative maintenance", r"ppm contracts?",
            r"contrats? d'entretien", r"contrats? de maintenance", r"contrats? de SAV"
        ],
        "label": "Recurring service / maintenance contracts",
    },
    {
        "code": "OPERATIONS.COMPLEXITY.ON_CALL_247",
        "category": "complexity",
        "keywords": [r"24/7", r"24 hours", r"emergency call-?out", r"astreinte", r"24h/24", r"dépannage d'urgence"],
        "label": "24/7 emergency callout or on-call service",
    },
    {
        "code": "TECH.OPPORTUNITY.MANUAL_JOB_SHEETS",
        "category": "technology",
        "keywords": [r"paper job sheets?", r"manual forms?", r"bons? d'intervention papier", r"formulaire pdf"],
        "label": "Paper job sheets or manual document workflows",
    },
    {
        "code": "TRIGGER.HIRING.SERVICE_COORDINATOR",
        "category": "trigger",
        "keywords": [r"hiring.*service coordinator", r"recrutement.*planificateur", r"recrutement.*assistante sav"],
        "label": "Hiring service coordinators or planners",
    },
]


def extract_evidence_from_page_content(
    html_or_text: str, source_url: str | None = None
) -> list[ExtractedEvidence]:
    """Extract evidence items from page text matching evidence taxonomy."""
    extracted: list[ExtractedEvidence] = []
    text_lower = html_or_text.lower()

    for pattern in EVIDENCE_PATTERNS:
        for kw in pattern["keywords"]:
            match = re.search(kw, text_lower)
            if match:
                start = max(0, match.start() - 40)
                end = min(len(html_or_text), match.end() + 60)
                snippet = html_or_text[start:end].strip()

                extracted.append(
                    ExtractedEvidence(
                        code=pattern["code"],
                        category=pattern["category"],
                        evidence_text=f"[{pattern['label']}] Snippet: ...{snippet}...",
                        confidence=0.85,
                        source_url=source_url,
                    )
                )
                break  # match once per taxonomy code per page

    return extracted
