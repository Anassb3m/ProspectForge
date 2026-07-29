"""Canonical pipeline-run creation and counter projection."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PipelineRun
from app.plays import require_play


async def create_pipeline_run(
    session: AsyncSession,
    *,
    play_code: str,
    mode: str,
    discovery_limit: int,
    run_contacts: bool,
    skip_sirene: bool,
    requested_by: str | None,
    correlation_id: str | None = None,
    partition_key: str = "all",
) -> PipelineRun:
    play = require_play(play_code)
    correlation_id = correlation_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    run = PipelineRun(
        play_code=play_code,
        play_version=str(play.get("version") or "unknown"),
        connector_code=mode,
        partition_key=partition_key,
        mode=mode,
        status="queued",
        request_config_json={
            "play_code": play_code,
            "play_version": str(play.get("version") or "unknown"),
            "mode": mode,
            "discovery_limit": discovery_limit,
            "run_contacts": run_contacts,
            "skip_sirene": skip_sirene,
            "source_partitions": [partition_key],
            "requested_by": requested_by,
            "requested_at": now.isoformat(),
            "correlation_id": correlation_id,
            "application_revision": os.getenv("APP_REVISION")
            or os.getenv("GIT_SHA")
            or "unknown",
        },
        requested_by=requested_by,
        correlation_id=correlation_id,
        application_revision=os.getenv("APP_REVISION") or os.getenv("GIT_SHA"),
        started_at=now,
        heartbeat_at=now,
    )
    session.add(run)
    await session.flush()
    return run


def apply_committed_totals(run: PipelineRun, totals: dict[str, Any]) -> None:
    """Project only final committed outcomes onto operator-visible columns."""
    run.raw_discovered = int(totals.get("raw_discovered") or 0)
    run.raw_persisted = int(totals.get("raw_persisted") or 0)
    run.duplicate_count = int(totals.get("duplicates") or 0)
    run.invalid_count = int(totals.get("invalid") or 0)
    run.companies_created = int(totals.get("created") or 0)
    run.companies_updated = int(totals.get("updated") or 0)
    run.enrichment_queued = int(totals.get("enrichment_queued") or 0)
    run.contact_queued = int(totals.get("contact_queued") or 0)
    run.error_count = int(totals.get("errors") or 0)
    run.error_categories_json = totals.get("error_categories") or {}
    run.stats_json = totals
