"""Contact enrichment orchestration (replaces Hunter.io paid path)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.discovery.contacts import discover_contacts
from app.discovery.emails import extract_domain
from app.models import Prospect
from app.scoring import apply_score

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
    """
    Run contact discovery waterfall on a prospect.
    If apply_best, write best verified/likely email onto the prospect.
    """
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
    prospect.contact_confidence = result.get("contact_confidence")
    prospect.needs_manual_review = bool(result.get("needs_manual_review"))

    if apply_best and result.get("best_email"):
        prospect.email = result["best_email"]
        if result.get("contact_confidence") in ("verified", "likely"):
            prospect.needs_manual_review = False

    apply_score(prospect, list(prospect.outreach_events or []))
    try:
        from app.discovery.enrich import apply_enrichment_to_prospect

        apply_enrichment_to_prospect(prospect, {})
    except Exception:
        pass
    await db.flush()
    return result
