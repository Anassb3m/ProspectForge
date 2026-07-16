"""GDPR retention: anonymize prospects inactive 3+ years (CNIL B2B guidance)."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import async_session_factory
from app.models import Prospect

logger = logging.getLogger(__name__)

RETENTION_YEARS = 3


async def anonymize_stale_prospects() -> int:
    """Flag and scrub personal data on prospects with no activity for 3+ years."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=365 * RETENTION_YEARS)
    count = 0

    async with async_session_factory() as session:
        result = await session.execute(
            select(Prospect)
            .options(selectinload(Prospect.outreach_events))
            .where(Prospect.anonymized.is_(False))
        )
        prospects = list(result.scalars().unique().all())

        for p in prospects:
            last_activity = p.updated_at or p.created_at
            if p.outreach_events:
                last_event = p.outreach_events[-1].event_date
                if last_event and (last_activity is None or last_event > last_activity):
                    last_activity = last_event

            if last_activity is None:
                continue
            if last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=timezone.utc)
            if last_activity > cutoff:
                continue

            p.decision_maker_name = None
            p.decision_maker_title = None
            p.email = None
            p.phone = None
            p.linkedin_url = None
            p.notes = "[anonymized — retention policy]"
            p.anonymized = True
            count += 1

        await session.commit()
        if count:
            logger.info("Anonymized %d prospects under retention policy", count)
        return count
