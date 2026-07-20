"""Bounded nightly contact-dossier refresh; never performs outreach."""

from __future__ import annotations

import logging

from sqlalchemy import and_, or_, select

from app.config import get_settings
from app.contact_intelligence.service import (
    DiscoveryAlreadyRunning,
    DiscoveryNotEligible,
    run_contact_discovery,
)
from app.database import async_session_factory
from app.models import Prospect

logger = logging.getLogger(__name__)


async def run_nightly_contact_discovery() -> dict[str, int]:
    settings = get_settings()
    stats = {"selected": 0, "completed": 0, "skipped": 0, "errors": 0, "outreach_events": 0}
    async with async_session_factory() as session:
        result = await session.execute(
            select(Prospect.id)
            .where(
                and_(
                    Prospect.anonymized.is_(False),
                    Prospect.opted_out.is_(False),
                    Prospect.opportunity_score >= settings.contact_min_opportunity_score,
                    or_(Prospect.website.isnot(None), Prospect.email.isnot(None)),
                    or_(
                        Prospect.contact_discovery_state.is_(None),
                        Prospect.contact_confidence.in_(["none", "needs_review", "unverified"]),
                    ),
                )
            )
            .order_by(Prospect.opportunity_score.desc())
            .limit(settings.nightly_contact_batch_size)
        )
        ids = list(result.scalars().all())
    stats["selected"] = len(ids)
    for prospect_id in ids:
        async with async_session_factory() as session:
            try:
                prospect = await session.get(Prospect, prospect_id)
                if prospect is None:
                    stats["skipped"] += 1
                    continue
                await run_contact_discovery(session, prospect, actor="scheduler")
                await session.commit()
                stats["completed"] += 1
            except (DiscoveryNotEligible, DiscoveryAlreadyRunning):
                await session.rollback()
                stats["skipped"] += 1
            except Exception:
                await session.rollback()
                stats["errors"] += 1
                logger.exception("Contact discovery failed prospect_id=%s", prospect_id)
    logger.info("Nightly contact discovery complete stats=%s", stats)
    return stats


async def run_nightly_contact_discovery_safe() -> dict[str, int]:
    try:
        return await run_nightly_contact_discovery()
    except Exception:
        logger.exception("Nightly contact discovery batch failed")
        return {"selected": 0, "completed": 0, "skipped": 0, "errors": 1, "outreach_events": 0}
