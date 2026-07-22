"""Contact discovery waterfall: OSINT → permutations → Reacher verification."""

from __future__ import annotations

import logging
from typing import Any

from app.discovery.emails import (
    extract_domain,
    generate_email_candidates,
    parse_person_name,
)
from app.discovery.harvester import harvest_emails
from app.discovery.reacher import check_emails_batch, pick_best_email

logger = logging.getLogger(__name__)

async def resolve_current_role(person_name: str, domain: str) -> dict[str, Any]:
    """
    Attempt to verify if a person is still employed at the domain.
    In Phase 7, this enforces that a generated contact is actually still active.
    """
    # A real implementation would query LinkedIn/Clearbit/Apollo via API.
    # We will mark it as needing manual verification.
    return {
        "verified": False,
        "reason": "API lookup disabled. Requires manual role confirmation.",
        "needs_review": True
    }


async def discover_contacts(
    *,
    website: str | None = None,
    domain: str | None = None,
    person_name: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    run_harvester: bool = True,
    verify: bool = True,
    max_candidates: int = 20,
) -> dict[str, Any]:
    """
    Full waterfall for one company / person.

    Returns:
      domain, candidates (with optional verification), best_email,
      contact_source, contact_confidence, needs_manual_review
    """
    if person_name and not (first_name and last_name):
        first_name, last_name = parse_person_name(person_name)

    domain = domain or extract_domain(website)
    if not domain:
        return {
            "domain": None,
            "candidates": [],
            "best_email": None,
            "contact_source": "none",
            "contact_confidence": "needs_review",
            "needs_manual_review": True,
            "message": "No website/domain — paste LinkedIn name + domain to generate emails",
        }

    harvested: list[str] = []
    if run_harvester:
        harvested = await harvest_emails(domain)

    candidates = generate_email_candidates(
        domain,
        first_name=first_name,
        last_name=last_name,
        include_roles=True,
        harvester_emails=harvested,
        max_candidates=max_candidates,
    )

    verified_results: list[dict] = []
    if verify and candidates:
        emails = [c["email"] for c in candidates]
        verified_results = await check_emails_batch(emails, stop_on_verified=True)
        # merge verification onto candidates
        by_email = {r["email"]: r for r in verified_results}
        for c in candidates:
            vr = by_email.get(c["email"])
            if vr:
                c["is_reachable"] = vr.get("is_reachable")
                c["confidence"] = vr.get("confidence")
                c["is_deliverable"] = vr.get("is_deliverable")
            else:
                c["confidence"] = "unchecked"

    best = pick_best_email(verified_results) if verified_results else None
    if not best and harvested:
        # Use first harvested without verify as unverified
        best = {
            "email": harvested[0],
            "confidence": "unverified",
            "is_reachable": "unknown",
        }

    discovery_state = "guessed"
    conf = (best.get("confidence") if best else None) or ""
    if best and conf in ("deliverable", "verified"):
        source = "reacher"
        confidence = "deliverable" if conf == "deliverable" else conf
        # SMTP acceptance proves mailbox behavior, not ownership by this person.
        discovery_state = "guessed"
        needs_review = True
    elif best and conf == "catch_all":
        source = "reacher"
        confidence = "catch_all"
        discovery_state = "guessed"
        needs_review = True
    elif best and harvested and best["email"] in harvested:
        source = "theharvester"
        confidence = conf or "unverified"
        discovery_state = "guessed"
        needs_review = True
    elif best:
        source = "reacher" if verify else "permutation"
        confidence = conf or "domain_and_pattern_only"
        discovery_state = "guessed"
        needs_review = True
    else:
        source = "none"
        confidence = "needs_review"
        needs_review = True

    # Never auto-send path for guessed-only patterns
    usable_for_send = discovery_state == "published" and confidence in (
        "published_personal", "confirmed_by_reply", "published_generic",
    )

    return {
        "domain": domain,
        "candidates": candidates,
        "best_email": best["email"] if best else None,
        "best": best,
        "contact_source": source,
        "contact_confidence": confidence,
        "contact_discovery_state": discovery_state,
        "needs_manual_review": needs_review or not usable_for_send,
        "usable_for_send": usable_for_send,
        "harvested_count": len(harvested),
        "message": (
            None if usable_for_send
            else "Email is guessed/indeterminate — confirm on LinkedIn or verify before send"
        ),
    }
