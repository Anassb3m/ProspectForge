from typing import Annotated

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from redis.asyncio import Redis
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi.templating import Jinja2Templates

from app.auth import get_current_user
from app.database import get_db
from app.config import get_settings
from app.models import (
    ContactDiscoveryRun,
    FailedWorkItem,
    PipelineRun,
    SourceRecord,
    User,
    WorkItem,
    WorkerNode,
)
from app.sources import SOURCE_CAPABILITIES

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(tags=["Operations"])


@router.get("/api/operations/acquisition-health")
async def acquisition_health(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    """Authenticated, fact-based acquisition and queue status."""
    settings = get_settings()
    stale_before = datetime.now(timezone.utc) - timedelta(
        seconds=settings.ingestion_lock_timeout_seconds
    )
    latest_run = await db.scalar(
        select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(1)
    )
    work_counts = {
        status: int(
            await db.scalar(
                select(func.count(WorkItem.id)).where(WorkItem.status == status)
            )
            or 0
        )
        for status in ("pending", "enqueued", "running", "completed", "failed")
    }
    stale_runs = int(
        await db.scalar(
            select(func.count(PipelineRun.id)).where(
                PipelineRun.status.in_(["queued", "running"]),
                PipelineRun.heartbeat_at < stale_before,
            )
        )
        or 0
    )
    source_record_counts = {
        status: int(
            await db.scalar(
                select(func.count(SourceRecord.id)).where(
                    SourceRecord.processing_status == status
                )
            )
            or 0
        )
        for status in ("pending", "normalized", "failed")
    }
    work_stale_before = datetime.now(timezone.utc) - timedelta(
        seconds=settings.work_stale_after_seconds
    )
    stale_work_items = int(
        await db.scalar(
            select(func.count(WorkItem.id)).where(
                or_(
                    (
                        (WorkItem.status == "running")
                        & (WorkItem.lock_lease_until.is_not(None))
                        & (WorkItem.lock_lease_until < datetime.now(timezone.utc))
                    ),
                    (
                        (WorkItem.status == "enqueued")
                        & (WorkItem.updated_at < work_stale_before)
                    ),
                )
            )
        )
        or 0
    )

    # Queue-specific worker states. A generic Celery process or a source-only
    # worker cannot prove that evidence/contact jobs have a consumer.
    queue_names = (
        "source-ingestion",
        "identity-domain",
        "website-evidence",
        "buyer-contact",
        "campaigns-notifications",
    )
    worker_nodes = await db.scalars(select(WorkerNode))
    workers_healthy = 0
    workers_total = 0
    healthy_by_queue = {name: 0 for name in queue_names}
    now_utc = datetime.now(timezone.utc)
    for node in worker_nodes:
        workers_total += 1
        # heartbeat within 3 minutes
        if node.status == "active" and node.last_heartbeat_at and (now_utc - node.last_heartbeat_at).total_seconds() < 180:
            workers_healthy += 1
            for queue_name in set((node.worker_type or "").split(",")):
                if queue_name in healthy_by_queue:
                    healthy_by_queue[queue_name] += 1

    missing_queues = [
        name for name, count in healthy_by_queue.items() if count == 0
    ]
    if workers_total == 0:
        worker_state = "unknown"
        worker_reason = "No workers registered"
    elif not missing_queues:
        worker_state = "healthy"
        worker_reason = (
            f"{workers_healthy}/{workers_total} workers active; all execution queues covered"
        )
    else:
        worker_state = "degraded"
        worker_reason = f"Missing fresh workers for: {', '.join(missing_queues)}"
    redis_state = "unavailable"
    queue_lengths: dict[str, int | None] = {name: None for name in queue_names}
    redis_client = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=2,
        socket_timeout=2,
        decode_responses=True,
    )
    try:
        redis_state = "healthy" if await redis_client.ping() else "unavailable"
        queue_lengths = {
            name: int(await redis_client.llen(name)) for name in queue_names
        }
    except Exception:
        redis_state = "unavailable"
    finally:
        await redis_client.aclose()

    source_states = {
        name: state.value for name, state in SOURCE_CAPABILITIES.items()
    }
    if not settings.insee_api_key:
        source_states["sirene"] = "misconfigured"

    overall = "healthy"
    if (
        redis_state != "healthy"
        or worker_state != "healthy"
        or stale_runs
        or work_counts["failed"]
        or stale_work_items
        or source_record_counts["failed"]
    ):
        overall = "degraded"
    if latest_run is not None and latest_run.status == "failed":
        overall = "degraded"
    contact_state_rows = await db.execute(
        select(ContactDiscoveryRun.status, func.count(ContactDiscoveryRun.id))
        .group_by(ContactDiscoveryRun.status)
    )
    contact_states = {
        str(run_status): int(count) for run_status, count in contact_state_rows.all()
    }
    return {
        "status": overall,
        "database": "healthy",
        "redis": redis_state,
        "workers": {
            "state": worker_state,
            "reason": worker_reason,
            "total": workers_total,
            "healthy": workers_healthy,
            "source_ingestion_healthy": healthy_by_queue["source-ingestion"],
            "by_queue": {
                name: {
                    "healthy": count,
                    "state": (
                        "unknown"
                        if workers_total == 0
                        else "healthy" if count else "missing"
                    ),
                }
                for name, count in healthy_by_queue.items()
            },
        },
        "queues": queue_lengths,
        "work_items": work_counts,
        "contact_discovery_runs": contact_states,
        "stale_work_items": stale_work_items,
        "raw_source_records": source_record_counts,
        "stale_active_runs": stale_runs,
        "latest_run": (
            {
                "id": latest_run.id,
                "play_code": latest_run.play_code,
                "connector": latest_run.connector_code,
                "status": latest_run.status,
                "heartbeat_at": latest_run.heartbeat_at,
                "errors": latest_run.error_count,
                "raw_discovered": latest_run.raw_discovered,
                "raw_persisted": latest_run.raw_persisted,
                "created": latest_run.companies_created,
                "updated": latest_run.companies_updated,
                "checkpoint_before": latest_run.checkpoint_before_json,
                "checkpoint_after": latest_run.checkpoint_after_json,
            }
            if latest_run is not None
            else None
        ),
        "sources": source_states,
        "automation": {
            "scheduler": settings.enable_scheduler,
            "nightly_ingestion": settings.enable_nightly_ingestion,
            "nightly_contact_discovery": settings.enable_nightly_contact_discovery,
            "score_reconciliation": settings.enable_score_reconciliation,
            "retention_sweep": settings.enable_retention_sweep,
            "automatic_outreach": False,
        },
    }

@router.get("/operations", response_class=HTMLResponse)
async def operations_dashboard(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    # Get latest pipeline runs
    runs_result = await db.execute(
        select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(10)
    )
    pipeline_runs = runs_result.scalars().all()

    # Get latest failed work items (DLQ)
    failed_result = await db.execute(
        select(FailedWorkItem).order_by(FailedWorkItem.failed_at.desc()).limit(20)
    )
    failed_items = failed_result.scalars().all()

    # Get latest contact discovery runs
    contact_runs_result = await db.execute(
        select(ContactDiscoveryRun).order_by(ContactDiscoveryRun.finished_at.desc().nulls_last()).limit(10)
    )
    contact_runs = contact_runs_result.scalars().all()
    worker_nodes = list(
        (
            await db.scalars(
                select(WorkerNode).order_by(WorkerNode.last_heartbeat_at.desc())
            )
        ).all()
    )

    return templates.TemplateResponse(
        request,
        "operations/index.html",
        {
            "user": user,
            "pipeline_runs": pipeline_runs,
            "failed_items": failed_items,
            "contact_runs": contact_runs,
            "worker_nodes": worker_nodes,
            "automation": {
                "scheduler": get_settings().enable_scheduler,
                "nightly_ingestion": get_settings().enable_nightly_ingestion,
                "nightly_contact_discovery": get_settings().enable_nightly_contact_discovery,
                "score_reconciliation": get_settings().enable_score_reconciliation,
                "retention_sweep": get_settings().enable_retention_sweep,
                "automatic_outreach": False,
                "reacher": get_settings().reacher_enabled,
                "harvester": get_settings().harvester_enabled,
            },
        },
    )

@router.post("/api/operations/failed-work/{item_id}/retry")
async def retry_failed_work(
    item_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    from app.workers.celery_app import celery_app
    from fastapi import HTTPException
    
    failed_item = await db.get(FailedWorkItem, item_id)
    if not failed_item:
        raise HTTPException(status_code=404, detail="Failed work item not found")
        
    if failed_item.resolved:
        raise HTTPException(status_code=400, detail="Item already resolved")
    if not failed_item.retryable:
        raise HTTPException(
            status_code=409,
            detail="This failure is not classified as safely retryable",
        )

    task_name = failed_item.task_name
    payload = failed_item.payload or {}
    is_raw_failure = (
        failed_item.source_name in {"registry", "decp"}
        and task_name.startswith("persist_")
    )
    if is_raw_failure:
        task_name = "app.workers.tasks.ingest_failed_raw_source"
        args = [failed_item.id]
        kwargs = {}
    elif task_name.startswith("app.workers.tasks."):
        args = payload.get("args", [])
        kwargs = payload.get("kwargs", {})
    else:
        raise HTTPException(
            status_code=409,
            detail="This failure has no supported durable reconciliation path",
        )
    
    try:
        celery_app.send_task(task_name, args=args, kwargs=kwargs)
        failed_item.retry_count = int(failed_item.retry_count or 0) + 1
        failed_item.resolution_note = (
            f"Retry {failed_item.retry_count} accepted by broker at "
            f"{datetime.now(timezone.utc).isoformat()}; success not yet confirmed"
        )
        await db.commit()
        return {
            "status": "accepted",
            "message": f"Task {task_name} retry accepted; completion is not yet confirmed",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue retry: {str(e)}")


@router.post("/api/operations/recover-stale-work")
async def recover_stale_work(
    _: Annotated[User, Depends(get_current_user)],
):
    """Request asynchronous lease recovery; broker acceptance is not completion."""
    from fastapi import HTTPException

    from app.workers.tasks import ingest_recover_stale_work

    try:
        task = ingest_recover_stale_work.delay()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to enqueue stale-work recovery: {exc}",
        ) from exc
    return {
        "status": "accepted",
        "task_id": task.id,
        "message": "Stale-work recovery accepted; completion is not yet confirmed",
    }
