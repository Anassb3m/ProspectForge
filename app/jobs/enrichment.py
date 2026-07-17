"""Contact enrichment orchestration."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.commercial import recompute_commercial_state, validate_contact_confidence
from app.discovery.contacts import discover_contacts
from app.discovery.emails import extract_domain
from app.models import Prospect

logger = logging.getLogger(__name__)


async def enrich_prospect_contacts(
    db: AsyncSession,
    prospect: Prospect,
    *,
    person_name: str | None = None,
    domain: str | None = None,
    run_harvester: bool = True,
    verify: bool = True,
    apply_best: bool = False,
) -> dict[str, Any]:
    if person_name:
        prospect.decision_maker_name = person_name

    domain = domain or extract_domain(prospect.website, prospect.email)
    result = await discover_contacts(
        website=prospect.website,
        domain=domain,
        person_name=person_name or prospect.decision_maker_name,
        run_harvester=run_harvester,
        verify=verify,
    )

    prospect.contact_candidates = result.get("candidates")
    prospect.contact_source = result.get("contact_source")
    conf = result.get("contact_confidence") or "none"
    try:
        conf = validate_contact_confidence(conf)
    except ValueError:
        conf = "domain_and_pattern_only"
    prospect.contact_confidence = conf
    prospect.contact_discovery_state = result.get("contact_discovery_state") or "guessed"
    prospect.needs_manual_review = bool(result.get("needs_manual_review"))

    from app.commercial import is_suppressed

    if apply_best and result.get("best_email") and result.get("usable_for_send"):
        best_email = result["best_email"]
        if not await is_suppressed(db, email=best_email, siren=prospect.siren):
            prospect.email = best_email
        else:
            prospect.contact_confidence = "needs_review"
            prospect.needs_manual_review = True
            result["message"] = "Discovered email is on the suppression list."

    await recompute_commercial_state(db, prospect)
    await db.flush()
    return result
