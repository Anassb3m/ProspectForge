import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Prospect, MessageDraft
from app.services.outbound import execute_sequence_step
from app.config import get_settings

logger = logging.getLogger(__name__)

async def run_campaign_step(db: AsyncSession, prospect_id: str, touch_id: str) -> bool:
    """Executes a single step in a sequence for a prospect."""
    
    settings = get_settings()
    if not settings.outreach_enabled:
        logger.warning("OUTREACH_ENABLED is False. Skipping campaign touch %s for %s", touch_id, prospect_id)
        return False

    prospect = await db.get(Prospect, prospect_id)
    if not prospect:
        logger.error("Prospect %s not found.", prospect_id)
        return False
        
    touch = await db.get(MessageDraft, touch_id)
    if not touch:
        logger.error("Touch %s not found.", touch_id)
        return False
        
    success = await execute_sequence_step(db, prospect, touch)
    if success:
        logger.info("Successfully executed sequence step %s for prospect %s", touch_id, prospect_id)
    else:
        logger.error("Failed to execute sequence step %s for prospect %s", touch_id, prospect_id)
        
    return success
