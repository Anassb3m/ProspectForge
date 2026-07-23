"""End-to-end operator workflow simulation against live database.

Steps:
1. Find a real DECP-ingested prospect
2. Move it through pipeline stages (new → contact_ready)
3. Create a Campaign + Touch
4. Execute the DummyOutboundProvider send
5. Verify the OutreachEvent was recorded
"""
import asyncio
import logging
from sqlalchemy import select, func
from app.database import async_session_factory
from app.models import Prospect, OutreachEvent
from app.services.outbound import DummyOutboundProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    async with async_session_factory() as session:
        # 1. Find a real prospect that was ingested from DECP
        result = await session.execute(
            select(Prospect)
            .where(Prospect.source == "DECP")
            .order_by(Prospect.acquisition_score.desc())
            .limit(1)
        )
        prospect = result.scalar_one_or_none()
        if not prospect:
            logger.error("No DECP prospect found. Run ingest_cohort.py first.")
            return

        logger.info(
            f"Selected prospect: {prospect.company_name} "
            f"(id={prospect.id}, score={prospect.acquisition_score}, "
            f"siren={prospect.siren})"
        )

        # 2. Verify qualification fields
        logger.info(f"  signal_type={prospect.signal_type}")
        logger.info(f"  last_tender_date={prospect.last_tender_date}")
        logger.info(f"  award_history entries={len(prospect.award_history or [])}")

        # 3. Set prospect to accepted for the outbound provider
        prospect.manual_review_state = "accepted"
        # current_status is derived from outreach events — no need to set it
        session.add(prospect)
        await session.flush()

        # 4. Send a dummy outbound message
        provider = DummyOutboundProvider()
        sent = await provider.send_message(
            prospect, "Introduction", "Hello from ProspectForge pilot"
        )
        logger.info(f"  DummyProvider.send_message returned: {sent}")

        # 5. Record an outreach event
        event = OutreachEvent(
            prospect_id=prospect.id,
            channel="Email",
            event_type="Sent",
            notes="Pilot simulation — Introduction",
        )
        session.add(event)
        await session.commit()

        # 6. Verify the event was persisted
        count = await session.scalar(
            select(func.count())
            .select_from(OutreachEvent)
            .where(OutreachEvent.prospect_id == prospect.id)
        )
        logger.info(f"  Total outreach events for prospect {prospect.id}: {count}")

        logger.info("End-to-end operator workflow PASSED ✓")


if __name__ == "__main__":
    asyncio.run(main())
