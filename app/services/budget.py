"""Source budget enforcement."""

from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.models import SourceRateBudget

async def check_and_consume_budget(session, source_name: str, amount: int = 1) -> bool:
    """Returns True if budget allows the request, False otherwise."""
    now = datetime.now(timezone.utc)
    budget = await session.scalar(
        select(SourceRateBudget)
        .where(SourceRateBudget.source_name == source_name)
        .with_for_update()
    )
    if not budget:
        # Default behavior if no budget explicitly defined
        return True
    
    if budget.reset_at.tzinfo is None:
        budget.reset_at = budget.reset_at.replace(tzinfo=timezone.utc)
        
    if now >= budget.reset_at:
        budget.used_today = 0
        # Reset at next UTC midnight
        next_day = now + timedelta(days=1)
        budget.reset_at = datetime(next_day.year, next_day.month, next_day.day, tzinfo=timezone.utc)
    
    if budget.used_today + amount > budget.daily_limit:
        return False
        
    budget.used_today += amount
    return True
