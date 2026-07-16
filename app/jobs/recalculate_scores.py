"""Nightly urgency score recalculation — captures decay for stale prospects."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import async_session_factory
from app.models import Prospect
from app.scoring import apply_score

logger = logging.getLogger(__name__)


async def recalculate_all_scores() -> int:
    """Recalculate urgency scores for all non-anonymized prospects. Returns count."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Prospect)
            .options(selectinload(Prospect.outreach_events))
            .where(Prospect.anonymized.is_(False))
        )
        prospects = list(result.scalars().unique().all())
        for p in prospects:
            apply_score(p, list(p.outreach_events or []))
        await session.commit()
        logger.info("Recalculated urgency scores for %d prospects", len(prospects))
        return len(prospects)
