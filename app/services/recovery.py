"""Durable recovery operations for abandoned pipeline work."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import FailedWorkItem, PipelineRun, WorkItem


RECOVERABLE_TASKS = {"extract_website_evidence"}


async def recover_stale_work_items(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    limit: int = 500,
) -> dict[str, Any]:
    """Reclaim expired leases and dead-letter work that exhausted retries.

    Rows are locked with ``SKIP LOCKED`` so concurrent maintenance workers can
    run safely. Recovery changes durable state only; the caller dispatches the
    returned pipeline runs after this transaction commits.
    """
    if not 1 <= limit <= 2000:
        raise ValueError("limit must be between 1 and 2000")
    resolved_now = now or datetime.now(timezone.utc)
    stale_before = resolved_now - timedelta(
        seconds=get_settings().work_stale_after_seconds
    )
    rows = list(
        (
            await session.execute(
                select(WorkItem)
                .where(
                    or_(
                        (
                            (WorkItem.status == "running")
                            & (WorkItem.lock_lease_until.is_not(None))
                            & (WorkItem.lock_lease_until < resolved_now)
                        ),
                        (
                            (WorkItem.status == "enqueued")
                            & (WorkItem.updated_at < stale_before)
                        ),
                    )
                )
                .order_by(WorkItem.updated_at, WorkItem.id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        .scalars()
        .all()
    )
    recovered = 0
    exhausted = 0
    unsupported = 0
    run_ids: set[str] = set()
    for item in rows:
        next_retry = int(item.retry_count or 0) + 1
        can_retry = (
            item.task_name in RECOVERABLE_TASKS
            and next_retry <= int(item.max_retries or 0)
        )
        if can_retry:
            item.status = "pending"
            item.retry_count = next_retry
            item.lock_lease_until = None
            run_ids.add(item.pipeline_run_id)
            recovered += 1
            continue

        existing = await session.scalar(
            select(FailedWorkItem.id).where(
                FailedWorkItem.original_work_item_id == item.id,
                FailedWorkItem.resolved.is_(False),
            )
        )
        item.status = "failed"
        item.retry_count = next_retry
        item.lock_lease_until = None
        if existing is None:
            reason = (
                "Stale work item uses an unsupported recovery task"
                if item.task_name not in RECOVERABLE_TASKS
                else "Stale work item exhausted its retry budget"
            )
            session.add(
                FailedWorkItem(
                    id=str(uuid.uuid4()),
                    original_work_item_id=item.id,
                    pipeline_run_id=item.pipeline_run_id,
                    task_name=f"app.workers.tasks.{item.task_name}",
                    source_name=str(
                        (item.payload or {}).get("source_name") or "worker"
                    ),
                    source_record_key=(
                        str((item.payload or {}).get("prospect_id") or "") or None
                    ),
                    payload={
                        "args": [str((item.payload or {}).get("prospect_id") or "")],
                        "kwargs": {"work_item_id": item.id},
                    },
                    error_category=(
                        "STALE_TASK_UNSUPPORTED"
                        if item.task_name not in RECOVERABLE_TASKS
                        else "TASK_RETRIES_EXHAUSTED"
                    ),
                    retryable=False,
                    error_message=reason,
                )
            )
        if item.task_name not in RECOVERABLE_TASKS:
            unsupported += 1
        else:
            exhausted += 1

    for run_id in {item.pipeline_run_id for item in rows}:
        run = await session.get(PipelineRun, run_id)
        if run is not None:
            run.heartbeat_at = resolved_now
            recovered_for_run = sum(
                1
                for item in rows
                if item.pipeline_run_id == run_id and item.status == "pending"
            )
            run.retry_count = int(run.retry_count or 0) + recovered_for_run
            run.enrichment_failed = int(run.enrichment_failed or 0) + sum(
                1
                for item in rows
                if item.pipeline_run_id == run_id and item.status == "failed"
            )
    await session.commit()
    return {
        "scanned": len(rows),
        "recovered": recovered,
        "exhausted": exhausted,
        "unsupported": unsupported,
        "pipeline_run_ids": sorted(run_ids),
    }
