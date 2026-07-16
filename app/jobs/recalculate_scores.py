"""Nightly / manual opportunity score recalculation (V3 only)."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.commercial import recompute_commercial_state
from app.database import async_session_factory
from app.models import Prospect

logger = logging.getLogger(__name__)


async def recalculate_all_scores() -> int:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Prospect)
            .options(selectinload(Prospect.outreach_events))
            .where(Prospect.anonymized.is_(False))
        )
        prospects = list(result.scalars().unique().all())
        for p in prospects:
            await recompute_commercial_state(session, p)
        await session.commit()
        logger.info("Recalculated V3 commercial state for %d prospects", len(prospects))
        return len(prospects)
