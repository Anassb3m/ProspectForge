"""Buyer Role Localization and Contact Resolution Engine."""

from dataclasses import dataclass
import re


@dataclass
class ResolvedBuyerRole:
    raw_title: str
    normalized_role: str
    seniority: str
    priority_rank: int
    matched_play_role: str


ROLE_DICTIONARY_UK = [
    {"pattern": r"managing director|owner|founder|co-founder", "role": "MANAGING_DIRECTOR", "seniority": "executive", "rank": 1},
    {"pattern": r"operations director|head of operations|director of operations", "role": "OPERATIONS_DIRECTOR", "seniority": "executive", "rank": 2},
    {"pattern": r"service director|service manager|head of service", "role": "SERVICE_DIRECTOR", "seniority": "director", "rank": 3},
    {"pattern": r"field service manager|contracts manager|operations manager", "role": "FIELD_SERVICE_MANAGER", "seniority": "manager", "rank": 4},
    {"pattern": r"technical director|head of engineering", "role": "TECHNICAL_DIRECTOR", "seniority": "executive", "rank": 5},
    {"pattern": r"general manager|branch manager", "role": "GENERAL_MANAGER", "seniority": "manager", "rank": 6},
]

ROLE_DICTIONARY_FR = [
    {"pattern": r"gérant|gerant|président|president|directeur général|directeur general", "role": "GERANT_PRESIDENT", "seniority": "executive", "rank": 1},
    {"pattern": r"directeur des opérations|directeur des operations|responsable d'exploitation", "role": "DIRECTEUR_OPERATIONS", "seniority": "executive", "rank": 2},
    {"pattern": r"responsable sav|responsable service client|directeur sav", "role": "RESPONSABLE_SAV", "seniority": "manager", "rank": 3},
    {"pattern": r"directeur technique|responsable technique", "role": "DIRECTEUR_TECHNIQUE", "seniority": "executive", "rank": 4},
    {"pattern": r"responsable maintenance|chef d'équipe", "role": "RESPONSABLE_MAINTENANCE", "seniority": "manager", "rank": 5},
]


def resolve_buyer_role(title: str, jurisdiction: str = "GB") -> ResolvedBuyerRole:
    """Normalize raw title string to target market buyer role."""
    t_lower = title.lower().strip()
    dictionary = ROLE_DICTIONARY_GB if jurisdiction == "GB" else ROLE_DICTIONARY_FR

    for entry in dictionary:
        if re.search(entry["pattern"], t_lower):
            return ResolvedBuyerRole(
                raw_title=title,
                normalized_role=entry["role"],
                seniority=entry["seniority"],
                priority_rank=entry["rank"],
                matched_play_role=entry["role"],
            )

    return ResolvedBuyerRole(
        raw_title=title,
        normalized_role="OTHER_EXECUTIVE",
        seniority="manager",
        priority_rank=99,
        matched_play_role="OTHER",
    )


ROLE_DICTIONARY_GB = ROLE_DICTIONARY_UK
