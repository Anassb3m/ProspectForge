from typing import Annotated

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi.templating import Jinja2Templates

from app.auth import get_current_user
from app.database import get_db
from app.config import get_settings
from app.models import FailedWorkItem, PipelineRun, User, WorkItem, WorkerNode
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

    # Worker states
    worker_nodes = await db.scalars(select(WorkerNode))
    workers_healthy = 0
    workers_total = 0
    now_utc = datetime.now(timezone.utc)
    for node in worker_nodes:
        workers_total += 1
        # heartbeat within 3 minutes
        if node.status == "active" and node.last_heartbeat_at and (now_utc - node.last_heartbeat_at).total_seconds() < 180:
            workers_healthy += 1
            
    if workers_total == 0:
        worker_state = "unknown"
        worker_reason = "No workers registered"
    elif workers_healthy > 0:
        worker_state = "healthy"
        worker_reason = f"{workers_healthy}/{workers_total} workers active"
    else:
        worker_state = "degraded"
        worker_reason = "No active workers, or all stale"

    queue_names = (
        "source-ingestion",
        "identity-domain",
        "website-evidence",
        "buyer-contact",
        "campaigns-notifications",
    )
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
    if redis_state != "healthy" or stale_runs or work_counts["failed"]:
        overall = "degraded"
    if latest_run is not None and latest_run.status == "failed":
        overall = "degraded"
    return {
        "status": overall,
        "database": "healthy",
        "redis": redis_state,
        "workers": {
            "state": worker_state,
            "reason": worker_reason,
            "total": workers_total,
            "healthy": workers_healthy,
        },
        "queues": queue_lengths,
        "work_items": work_counts,
        "stale_active_runs": stale_runs,
        "latest_run": (
            {
                "id": latest_run.id,
                "play_code": latest_run.play_code,
                "connector": latest_run.connector_code,
                "status": latest_run.status,
                "heartbeat_at": latest_run.heartbeat_at,
                "errors": latest_run.error_count,
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
    from app.models import ContactDiscoveryRun
    contact_runs_result = await db.execute(
        select(ContactDiscoveryRun).order_by(ContactDiscoveryRun.finished_at.desc().nulls_last()).limit(10)
    )
    contact_runs = contact_runs_result.scalars().all()

    return templates.TemplateResponse(
        request,
        "operations/index.html",
        {
            "user": user,
            "pipeline_runs": pipeline_runs,
            "failed_items": failed_items,
            "contact_runs": contact_runs,
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
        
    task_name = failed_item.task_name
    payload = failed_item.payload or {}
    args = payload.get("args", [])
    kwargs = payload.get("kwargs", {})
    
    try:
        celery_app.send_task(task_name, args=args, kwargs=kwargs)
        failed_item.resolved = True
        await db.commit()
        return {"status": "success", "message": f"Task {task_name} retried"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue retry: {str(e)}")
