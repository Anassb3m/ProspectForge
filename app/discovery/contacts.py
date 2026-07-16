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

    if best and best.get("confidence") == "verified":
        source = "reacher"
        confidence = "verified"
        needs_review = False
    elif best and best.get("confidence") == "likely":
        source = "reacher"
        confidence = "likely"
        needs_review = False
    elif best and harvested and best["email"] in harvested:
        source = "theharvester"
        confidence = best.get("confidence") or "unverified"
        needs_review = confidence != "verified"
    elif best:
        source = "reacher" if verify else "manual"
        confidence = best.get("confidence") or "unverified"
        needs_review = confidence not in ("verified", "likely")
    else:
        source = "none"
        confidence = "needs_review"
        needs_review = True

    return {
        "domain": domain,
        "candidates": candidates,
        "best_email": best["email"] if best else None,
        "best": best,
        "contact_source": source,
        "contact_confidence": confidence,
        "needs_manual_review": needs_review,
        "harvested_count": len(harvested),
        "message": None if best else "No verified email — needs manual review / LinkedIn name",
    }
