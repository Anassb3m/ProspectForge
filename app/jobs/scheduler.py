"""APScheduler in-process background jobs."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.jobs.recalculate_scores import recalculate_all_scores
from app.jobs.retention import anonymize_stale_prospects

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def start_scheduler() -> AsyncIOScheduler:
    if scheduler.running:
        return scheduler

    settings = get_settings()

    # Nightly DECP discovery + Sirene enrich at 01:00 UTC
    if settings.enable_nightly_ingestion:
        from app.jobs.ingestion import run_ingestion_safe

        scheduler.add_job(
            run_ingestion_safe,
            CronTrigger(hour=1, minute=0),
            id="decp_ingestion",
            replace_existing=True,
            max_instances=1,
        )

    # Nightly urgency recalculation at 02:00 UTC (after ingestion)
    scheduler.add_job(
        recalculate_all_scores,
        CronTrigger(hour=2, minute=0),
        id="recalculate_scores",
        replace_existing=True,
        max_instances=1,
    )

    # Weekly retention sweep Sundays 03:00 UTC
    scheduler.add_job(
        anonymize_stale_prospects,
        CronTrigger(day_of_week="sun", hour=3, minute=0),
        id="retention_anonymize",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    logger.info("APScheduler started (ingestion + score recalc + retention)")
    return scheduler


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
