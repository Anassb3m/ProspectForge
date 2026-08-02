"""Durable operator-triggered evidence enrichment queue."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PipelineRun, Prospect, WorkItem
from app.services.pipeline_runs import create_pipeline_run


def _work_key(prospect: Prospect) -> str:
    revision = (
        prospect.last_enriched_at.isoformat()
        if prospect.last_enriched_at is not None
        else "never"
    )
    digest = hashlib.sha256(
        f"operator-evidence:{prospect.id}:{revision}".encode()
    ).hexdigest()[:32]
    return f"operator-evidence:{prospect.id}:{digest}"


async def queue_evidence_enrichment(
    session: AsyncSession,
    prospects: Iterable[Prospect],
    *,
    actor: str,
) -> tuple[PipelineRun, list[WorkItem]]:
    """Commit idempotent WorkItems before any broker publication."""
    selected = list(prospects)
    run = await create_pipeline_run(
        session,
        play_code="FIELD_OPERATIONS_FR_V2",
        mode="operator-evidence",
        discovery_limit=max(1, len(selected)),
        run_contacts=False,
        skip_sirene=False,
        requested_by=actor,
        partition_key="operator",
    )
    created: list[WorkItem] = []
    duplicate_count = 0
    for prospect in selected:
        key = _work_key(prospect)
        existing = await session.scalar(
            select(WorkItem.id).where(WorkItem.idempotency_key == key)
        )
        if existing is not None:
            duplicate_count += 1
            continue
        item = WorkItem(
            pipeline_run_id=run.id,
            idempotency_key=key,
            task_name="extract_website_evidence",
            payload={
                "prospect_id": prospect.id,
                "opportunity_id": prospect.opportunity_id,
                "source_name": "operator",
                "skip_sirene": False,
            },
            status="pending",
            max_retries=3,
        )
        session.add(item)
        created.append(item)
    await session.flush()
    run.enrichment_queued = len(created)
    run.duplicate_count = duplicate_count
    if not created:
        run.status = "skipped_duplicate"
        run.finished_at = datetime.now(timezone.utc)
    await session.commit()
    return run, created


async def dispatch_evidence_enrichment(
    session: AsyncSession, run: PipelineRun, items: list[WorkItem]
) -> dict[str, int]:
    if not items:
        return {"pending": 0, "dispatched": 0, "dispatch_errors": 0}
    from app.jobs.ingestion import _dispatch_enrichment_work

    result = await _dispatch_enrichment_work(session, pipeline_run_id=run.id)
    await session.refresh(run)
    # A fast worker can finish the run before the publisher regains control.
    # Never move a terminal durable run backwards to ``running``.
    if run.status not in {"completed", "completed_with_errors"}:
        run.status = "running" if result["dispatched"] else "queue_unavailable"
    run.error_count = result["dispatch_errors"]
    run.error_categories_json = (
        {"QUEUE_UNAVAILABLE": result["dispatch_errors"]}
        if result["dispatch_errors"]
        else {}
    )
    run.error_summary = (
        f"{result['dispatch_errors']} evidence work item(s) remain pending"
        if result["dispatch_errors"]
        else None
    )
    await session.commit()
    return result
