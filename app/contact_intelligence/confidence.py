"""Honest contact utility derivation and primary-path ranking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.contact_intelligence.types import UtilityState


def derive_utility(
    *,
    kind: str,
    publication_state: str,
    deliverability_state: str,
    person_match_state: str,
    suppressed: bool = False,
    manually_confirmed: bool = False,
    expires_at: datetime | None = None,
) -> str:
    if suppressed:
        return UtilityState.SUPPRESSED
    if expires_at is not None:
        expiry = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
        if expiry < datetime.now(timezone.utc):
            return UtilityState.STALE
    if deliverability_state == "invalid":
        return UtilityState.INVALID
    if deliverability_state in {"catch_all", "risky", "indeterminate", "error"}:
        return UtilityState.MANUAL_CONFIRMATION_REQUIRED
    if kind in {"contact_form", "phone", "linkedin", "generic_contact_page"}:
        return UtilityState.USABLE_GENERIC if kind == "contact_form" else UtilityState.USABLE_ROLE
    if kind != "email":
        return UtilityState.NO_CONTACT
    if manually_confirmed and deliverability_state != "invalid":
        return UtilityState.USABLE_PERSONAL
    if publication_state == "published_personal" and person_match_state in {
        "exact_person_published", "strong_person_match"
    }:
        return UtilityState.USABLE_PERSONAL
    if publication_state == "published_role" or person_match_state == "role_mailbox":
        return UtilityState.USABLE_ROLE
    if publication_state == "published_generic" or person_match_state == "generic_company_mailbox":
        return UtilityState.USABLE_GENERIC
    if person_match_state == "exact_person_pattern_confirmed":
        return (
            UtilityState.USABLE_PERSONAL
            if deliverability_state == "deliverable"
            else UtilityState.VERIFICATION_REQUIRED
        )
    if person_match_state in {"pattern_inferred", "name_only_guess"}:
        return UtilityState.MANUAL_CONFIRMATION_REQUIRED
    return UtilityState.VERIFICATION_REQUIRED


UTILITY_RANK = {
    "usable_personal": 0,
    "usable_role": 1,
    "usable_generic": 2,
    "manual_confirmation_required": 3,
    "verification_required": 4,
    "stale": 5,
    "no_contact": 6,
    "invalid": 8,
    "suppressed": 9,
}
KIND_RANK = {"email": 0, "phone": 1, "contact_form": 2, "linkedin": 3, "website": 4}


def primary_sort_key(point: Any) -> tuple[int, int, int, int]:
    return (
        UTILITY_RANK.get(str(point.utility_state), 7),
        KIND_RANK.get(str(point.kind), 8),
        0 if getattr(point, "manually_confirmed", False) else 1,
        -int(getattr(point, "confidence_score", 0) or 0),
    )


def is_usable(utility_state: str) -> bool:
    return utility_state in {"usable_personal", "usable_role", "usable_generic"}
