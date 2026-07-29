from celery import Celery, Task
from celery.schedules import crontab
import asyncio
import logging
import traceback
import uuid

from app.config import Settings, get_settings
from celery.signals import worker_ready, worker_shutting_down

logger = logging.getLogger(__name__)
settings = get_settings()
broker_url = settings.celery_broker_url
result_backend = settings.celery_result_backend


def build_beat_schedule(config: Settings | None = None) -> dict:
    """Build only schedules explicitly enabled by operator configuration."""
    resolved = config or get_settings()
    schedule: dict = {}
    if resolved.enable_scheduler and resolved.enable_nightly_ingestion:
        schedule["nightly-ingestion"] = {
            "task": "app.workers.tasks.ingest_market_play",
            "schedule": crontab(hour=1, minute=0),
            "kwargs": {
                "play_code": resolved.active_market_play,
                "mode": "registry",
                "discovery_limit": resolved.nightly_ingestion_limit,
                "run_contacts": False,
                "skip_sirene": False,
                "requested_by": "celery-beat",
            },
        }
    if resolved.enable_scheduler and resolved.enable_nightly_contact_discovery:
        schedule["nightly-contact-discovery"] = {
            "task": "app.workers.tasks.contact_discovery_run",
            "schedule": crontab(hour=1, minute=45),
            "kwargs": {"company_id": "ALL"},
        }
    if resolved.enable_scheduler and resolved.enable_score_reconciliation:
        schedule["recalculate-scores"] = {
            "task": "app.workers.tasks.recalculate_scores",
            "schedule": crontab(hour=2, minute=0),
        }
    if resolved.enable_scheduler and resolved.enable_retention_sweep:
        schedule["retention-anonymize"] = {
            "task": "app.workers.tasks.retention_sweep",
            "schedule": crontab(hour=3, minute=0, day_of_week="sunday"),
        }
    return schedule

class ProspectForgeTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        from app.database import async_session_factory
        from app.models import FailedWorkItem, WorkItem

        async def _record_failure():
            async with async_session_factory() as session:
                work_item_id = kwargs.get("work_item_id")
                work_item = (
                    await session.get(WorkItem, work_item_id)
                    if work_item_id
                    else None
                )
                failed_item = FailedWorkItem(
                    id=str(uuid.uuid4()),
                    original_work_item_id=work_item_id or task_id,
                    pipeline_run_id=(
                        work_item.pipeline_run_id if work_item is not None else None
                    ),
                    task_name=self.name,
                    source_name=(
                        str(work_item.payload.get("source_name") or "worker")
                        if work_item is not None
                        else "worker"
                    ),
                    source_record_key=(
                        str(work_item.payload.get("prospect_id") or "")
                        if work_item is not None
                        else None
                    ),
                    payload={"args": args, "kwargs": kwargs},
                    error_category="TASK_RETRIES_EXHAUSTED",
                    retryable=False,
                    error_message=str(exc),
                    traceback=traceback.format_exc() if einfo else None
                )
                session.add(failed_item)
                await session.commit()

        try:
            asyncio.run(_record_failure())
        except Exception:
            logger.exception("Could not persist Celery task failure task_id=%s", task_id)
        super().on_failure(exc, task_id, args, kwargs, einfo)


async def _heartbeat_loop(worker_hostname: str):
    from app.database import async_session_factory
    from app.models import WorkerNode
    from sqlalchemy.dialects.postgresql import insert
    from datetime import datetime, timezone
    import asyncio
    
    while True:
        try:
            async with async_session_factory() as session:
                now = datetime.now(timezone.utc)
                stmt = insert(WorkerNode).values(
                    id=worker_hostname,
                    hostname=worker_hostname,
                    worker_type="celery",
                    status="active",
                    started_at=now,
                    last_heartbeat_at=now
                ).on_conflict_do_update(
                    index_elements=['id'],
                    set_={"last_heartbeat_at": now, "status": "active"}
                )
                await session.execute(stmt)
                await session.commit()
        except Exception:
            logger.exception("Worker heartbeat failed")
        await asyncio.sleep(60)

@worker_ready.connect
def start_heartbeat(sender=None, **kwargs):
    hostname = sender.hostname if sender else f"worker-{uuid.uuid4()}"
    import threading
    
    def run_loop():
        asyncio.run(_heartbeat_loop(hostname))
        
    t = threading.Thread(target=run_loop, daemon=True)
    t.start()

@worker_shutting_down.connect
def stop_heartbeat(sender=None, **kwargs):
    from app.database import async_session_factory
    from app.models import WorkerNode
    import asyncio
    hostname = sender.hostname if sender else None
    if not hostname: return
    
    async def _mark_offline():
        async with async_session_factory() as session:
            node = await session.get(WorkerNode, hostname)
            if node:
                node.status = "offline"
                await session.commit()
    
    try:
        asyncio.run(_mark_offline())
    except Exception:
        logger.exception("Failed to mark worker offline")



celery_app = Celery(
    "prospectforge",
    broker=broker_url,
    backend=result_backend,
    include=["app.workers.tasks"],
    task_cls=ProspectForgeTask,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.workers.tasks.ingest_*": {"queue": "source-ingestion"},
        "app.workers.tasks.resolve_*": {"queue": "identity-domain"},
        "app.workers.tasks.extract_*": {"queue": "website-evidence"},
        "app.workers.tasks.contact_*": {"queue": "buyer-contact"},
        "app.workers.tasks.campaign_*": {"queue": "campaigns-notifications"},
    },
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule=build_beat_schedule(settings),
)

logger.info(
    "Celery automation scheduler=%s schedules=%s play=%s limit=%d outreach_enabled=%s",
    settings.enable_scheduler,
    sorted(celery_app.conf.beat_schedule),
    settings.active_market_play,
    settings.nightly_ingestion_limit,
    settings.outreach_enabled,
)

if __name__ == "__main__":
    celery_app.start()
