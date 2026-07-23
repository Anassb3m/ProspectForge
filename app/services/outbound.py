import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Prospect, OutreachEvent

logger = logging.getLogger(__name__)

class OutboundProvider:
    """Base class for outbound messaging providers (e.g., SMTP, Lemlist, Reply.io)."""

    async def send_message(self, prospect: Prospect, subject: str, body: str) -> bool:
        raise NotImplementedError

    async def sync_events(self, db: AsyncSession) -> None:
        """Fetch replies, bounces, and opt-outs from the provider."""
        raise NotImplementedError

class DummyOutboundProvider(OutboundProvider):
    """A dummy provider for Phase 10 implementation."""

    async def send_message(self, prospect: Prospect, subject: str, body: str) -> bool:
        logger.info(f"DummyProvider sending message to {prospect.email}: {subject}")
        # In a real provider, we would return a provider_message_id
        return True

    async def sync_events(self, db: AsyncSession) -> None:
        logger.info("DummyProvider syncing events (bounces, opt-outs, replies)...")
        # Example of how sync_events would process a simulated bounce:
        # event = OutreachEvent(prospect_id=..., channel="Email", event_type="Bounced")
        # prospect.opted_out = True
        # db.add(event)
        # await db.flush()

async def evaluate_stop_rules(prospect: Prospect, db: AsyncSession) -> bool:
    """
    Evaluates whether an active campaign sequence should be stopped for this prospect.
    Returns True if the sequence should STOP.
    """
    if prospect.opted_out or prospect.is_suppressed:
        return True

    if prospect.current_status in ("Replied", "MeetingBooked", "Unqualified"):
        return True

    return False

async def execute_sequence_step(db: AsyncSession, prospect: Prospect, touch: Any) -> bool:
    """
    Execute a sequence draft. Requires approval workflows.
    """
    if getattr(prospect, "manual_review_state", None) != "accepted":
        logger.warning(f"Prospect {prospect.id} not accepted. Cannot execute sequence.")
        return False

    if await evaluate_stop_rules(prospect, db):
        logger.info(f"Stop rules triggered for prospect {prospect.id}. Halting sequence.")
        return False

    provider = DummyOutboundProvider()
    subject = getattr(touch, "subject", "Subject")
    body = getattr(touch, "body", "Body")

    success = await provider.send_message(prospect, subject, body)
    if success:
        event = OutreachEvent(
            prospect_id=prospect.id,
            channel="Email",
            event_type="Sent",
            notes=f"Sent {subject}"
        )
        db.add(event)
        await db.flush()

    return success
