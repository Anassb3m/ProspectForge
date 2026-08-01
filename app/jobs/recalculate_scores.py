"""Nightly / manual opportunity score recalculation."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.commercial import recompute_commercial_state
from app.database import async_session_factory
from app.models import Opportunity, Prospect
from app.services.scoring_v4 import calculate_opportunity_score_v4

logger = logging.getLogger(__name__)


async def recalculate_all_scores() -> int:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Opportunity)
            .options(
                selectinload(Opportunity.company),
                selectinload(Opportunity.evidence_items)
            )
        )
        opportunities = list(result.scalars().unique().all())
        for opp in opportunities:
            # V4 Canonical Scoring
            await calculate_opportunity_score_v4(session, opp)
            
            # Legacy Projection Update
            prospect = await session.scalar(
                select(Prospect).where(Prospect.opportunity_id == opp.id)
            )
            if prospect and not prospect.anonymized:
                # Update Prospect scores from Opportunity
                prospect.opportunity_score = opp.latest_score
                await recompute_commercial_state(session, prospect)
                
        await session.commit()
        logger.info("Recalculated V4 scores for %d opportunities", len(opportunities))
        return len(opportunities)
