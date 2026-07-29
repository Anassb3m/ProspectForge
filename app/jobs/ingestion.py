"""
Multi-source acquisition engine (V3 — field-service market play).

Sources:
  A) DECP public awards (timing — not proof of software need)
  B) Recherche Entreprises field-service NAF hunt (structural candidates)
  C) Deep enrich: Annuaire → Sirene → contacts → opportunity score + readiness

Run:
  python -m app.jobs.ingestion --mode full
  python -m app.jobs.ingestion --mode decp --max-companies 50
  python -m app.jobs.ingestion --mode registry --max-companies 80
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import async_session_factory, init_db
from app.discovery.annuaire import discover_companies_for_play_checkpointed
from app.discovery.decp import aggregate_by_siret, filter_relevant, load_decp
from app.commercial import is_suppressed, recompute_commercial_state, upsert_evidence
from app.discovery.enrich import apply_enrichment_to_prospect, deep_enrich
from app.models import (
    FailedWorkItem,
    OutreachEvent,
    PipelineRun,
    Prospect,
    SourceCheckpoint,
    WorkItem,
)
from app.plays import DEFAULT_PLAY_CODE, validate_ingestion_request
from app.services.normalized import upsert_normalized_company
from app.services.pipeline_runs import apply_committed_totals, create_pipeline_run
from app.services.run_lock import acquisition_run_locks

logger = logging.getLogger(__name__)

DATA_SOURCE_DECP = "DECP public awards (data.gouv.fr) — field-service play filters + Sirene"
DATA_SOURCE_REG = "Recherche Entreprises — field-service NAF/play filters + Sirene"


def _parse_date(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val)[:10]).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


async def _find_prospect(session, *, siret: str | None, siren: str | None) -> Prospect | None:
    if siret:
        r = await session.execute(
            select(Prospect)
            .options(selectinload(Prospect.outreach_events))
            .where(Prospect.siret == siret)
        )
        p = r.scalar_one_or_none()
        if p:
            return p
    if siren:
        r = await session.execute(
            select(Prospect)
            .options(selectinload(Prospect.outreach_events))
            .where(Prospect.siren == siren)
            .order_by(Prospect.id)
            .limit(1)
        )
        return r.scalar_one_or_none()
    return None


async def upsert_prospect(
    session,
    *,
    base: dict[str, Any],
    signal_type: str,
    source: str,
    data_source: str,
    play_code: str,
    deep: bool = True,
    skip_sirene: bool = False,
    verify_email: bool = False,
) -> tuple[Prospect | None, bool, str]:
    """
    Create/update prospect. Returns (prospect|None, created, status).
    status: created|updated|skipped_compliance|error
    """
    siret = base.get("siret")
    siren = base.get("siren")
    if not siret and not siren:
        return None, False, "error"

    if await is_suppressed(session, siren=siren):
        return None, False, "skipped_compliance"

    enrich_data: dict[str, Any] = dict(base)
    if deep:
        enrich_data = await deep_enrich(
            siren=siren,
            siret=siret,
            company_name=base.get("company_name"),
            existing=base,
            # Raw source ingestion never performs contact discovery. Contact
            # work is a separate durable stage with its own eligibility gates.
            run_contacts=False,
            verify_email=verify_email,
            infer_web=True,
            skip_sirene=skip_sirene,
        )
        if enrich_data.get("sirene_blocked") and not base.get("company_name"):
            return None, False, "skipped_compliance"

    # Prefer enriched identity
    siret = enrich_data.get("siret") or siret
    siren = enrich_data.get("siren") or siren
    name = enrich_data.get("company_name") or base.get("company_name") or f"SIREN {siren}"

    prospect = await _find_prospect(session, siret=siret, siren=siren)
    created = False

    if prospect is None:
        prospect = Prospect(
            company_name=str(name)[:200],
            signal_type=signal_type,
            signal_details=(base.get("signal_details") or "")[:2000] or None,
            source=source,
            acquisition_stage="researching",
            needs_manual_review=True,
            contact_confidence="none",
            contact_source="none",
            market_play_code=play_code,
            readiness_state="research_required",
            manual_review_state="unreviewed",
        )
        session.add(prospect)

        await session.flush()
        session.add(
            OutreachEvent(
                prospect_id=prospect.id,
                channel="Email",
                event_type="New",
                notes=f"Discovered via {source} acquisition engine",
            )
        )
        created = True
    else:
        # Merge award history if present
        if base.get("award_history"):
            existing = list(prospect.award_history or [])
            seen = {(a.get("id"), a.get("date"), (a.get("objet") or "")[:80]) for a in existing}
            for a in base["award_history"]:
                key = (a.get("id"), a.get("date"), (a.get("objet") or "")[:80])
                if key not in seen:
                    existing.append(a)
                    seen.add(key)
            existing.sort(key=lambda a: a.get("date") or "", reverse=True)
            prospect.award_history = existing[:50]
            ltd = _parse_date(base.get("last_tender_date"))
            if ltd:
                old_ltd = prospect.last_tender_date
                if old_ltd and old_ltd.tzinfo is None:
                    old_ltd = old_ltd.replace(tzinfo=timezone.utc)
                if not old_ltd or ltd > old_ltd:
                    prospect.last_tender_date = ltd
            # Upgrade signal if public award is stronger
            if signal_type in ("DECP_WIN", "PUBLIC_AWARD", "BOAMP_WIN"):
                prospect.signal_type = signal_type
                if base.get("signal_details"):
                    prospect.signal_details = str(base["signal_details"])[:2000]
                prospect.source = "DECP"
                prospect.data_source = data_source

    # Apply enrichment fields + scores
    if base.get("award_history") and not prospect.award_history:
        prospect.award_history = base["award_history"]
        prospect.last_tender_date = _parse_date(base.get("last_tender_date"))
    if base.get("signal_details") and not prospect.signal_details:
        prospect.signal_details = str(base["signal_details"])[:2000]
    if base.get("evidence"):
        enrich_data["evidence"] = base["evidence"]
    if base.get("award_history"):
        enrich_data["award_history"] = base.get("award_history") or enrich_data.get("award_history")

    if prospect.market_play_code and prospect.market_play_code != play_code:
        raise ValueError(
            f"identity collision across plays for prospect {prospect.id}: "
            f"{prospect.market_play_code} != {play_code}"
        )
    prospect.market_play_code = play_code
    apply_enrichment_to_prospect(prospect, enrich_data)

    # The explicit opportunity link is the only bridge between the compatibility
    # projection and the canonical schema. Never resolve this relationship by
    # company name or an inferred domain.
    opportunity = await upsert_normalized_company(
        session=session,
        company_name=str(name)[:200],
        siren=siren,
        siret=siret,
        website=enrich_data.get("website"),
        city=enrich_data.get("city"),
        department=enrich_data.get("department"),
        payload=base,
        play_code=play_code,
    )
    prospect.company_id = opportunity.company_id
    prospect.opportunity_id = opportunity.id

    # Dedupe-aware evidence upsert (normalized table is source of truth)
    await upsert_evidence(
        session,
        prospect.id,
        list(base.get("evidence") or enrich_data.get("evidence") or [])[:20],
    )
    await recompute_commercial_state(session, prospect)
    await session.flush()

    return prospect, created, "created" if created else "updated"


def _error_category(exc: Exception) -> tuple[str, bool]:
    """Return a stable operator-facing category and conservative retry policy."""
    name = type(exc).__name__
    if name in {"TimeoutException", "ReadTimeout", "ConnectTimeout"}:
        return "UPSTREAM_TIMEOUT", True
    if name in {"ConnectError", "RemoteProtocolError"}:
        return "UPSTREAM_UNAVAILABLE", True
    if name in {"IntegrityError", "DataError"}:
        return "PERSISTENCE_REJECTED", False
    if isinstance(exc, ValueError):
        return "INVALID_SOURCE_RECORD", False
    return "UNCLASSIFIED", False


async def _record_failed_item(
    session,
    *,
    pipeline_run_id: str,
    task_name: str,
    source_name: str,
    source_record_key: str | None,
    payload: dict[str, Any],
    exc: Exception,
) -> str:
    category, retryable = _error_category(exc)
    failed_id = str(uuid.uuid4())
    safe_payload = json.loads(json.dumps(payload, default=str))
    async with session.begin_nested():
        session.add(
            FailedWorkItem(
                id=failed_id,
                original_work_item_id=failed_id,
                task_name=task_name,
                error_type=category,
                error_message=str(exc)[:4000],
                traceback_info=traceback.format_exc()[-12000:],
                kwargs={
                    "pipeline_run_id": pipeline_run_id,
                    "source_name": source_name,
                    "source_record_key": source_record_key,
                    "payload": safe_payload,
                    "retryable": retryable
                }
            )
        )
        await session.flush()
    return category


async def _ensure_enrichment_work_item(
    session,
    *,
    pipeline_run_id: str,
    prospect_id: int,
    play_code: str,
    source_name: str,
    source_payload: dict[str, Any],
    skip_sirene: bool,
) -> tuple[WorkItem, bool]:
    """Persist an idempotent enrichment stage; never call it inline."""
    canonical_payload = json.dumps(source_payload, default=str, sort_keys=True)
    fingerprint = hashlib.sha256(canonical_payload.encode()).hexdigest()
    idempotency_key = f"enrich:{play_code}:{prospect_id}:{fingerprint}"
    existing = await session.scalar(
        select(WorkItem).where(WorkItem.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return existing, False
    item = WorkItem(
        pipeline_run_id=pipeline_run_id,
        idempotency_key=idempotency_key,
        task_name="extract_website_evidence",
        payload={
            "prospect_id": prospect_id,
            "play_code": play_code,
            "source_name": source_name,
            "skip_sirene": skip_sirene,
            "run_contacts": False,
            "source_fingerprint": fingerprint,
        },
        status="pending",
        retry_count=0,
        max_retries=3,
    )
    session.add(item)
    await session.flush()
    return item, True


async def _dispatch_enrichment_work(
    session, *, pipeline_run_id: str
) -> dict[str, int]:
    """Dispatch durable pending work without losing it when the broker is down."""
    from app.workers.tasks import extract_website_evidence

    items = list(
        (
            await session.execute(
                select(WorkItem)
                .where(
                    WorkItem.pipeline_run_id == pipeline_run_id,
                    WorkItem.task_name == "extract_website_evidence",
                    WorkItem.status == "pending",
                )
                .order_by(WorkItem.created_at, WorkItem.id)
            )
        )
        .scalars()
        .all()
    )
    stats = {"pending": len(items), "dispatched": 0, "dispatch_errors": 0}
    for item in items:
        try:
            extract_website_evidence.delay(
                str(item.payload["prospect_id"]),
                work_item_id=item.id,
            )
            item.status = "enqueued"
            stats["dispatched"] += 1
        except Exception:
            # Pending is recoverable and truthful. A reconciler can dispatch it
            # later; never mark broker acceptance when enqueue failed.
            logger.exception("Could not dispatch work_item=%s", item.id)
            stats["dispatch_errors"] += 1
    await session.commit()
    return stats


async def ingest_decp(
    session,
    *,
    days_back: int,
    max_companies: int,
    play_code: str,
    skip_sirene: bool,
    pipeline_run_id: str,
) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "awards": 0,
        "companies": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
        "error_categories": {},
        "enrichment_queued": 0,
    }
    settings = get_settings()
    logger.info("DECP source: loading parquet…")
    raw = await load_decp()
    filtered = filter_relevant(
        raw,
        days_back=days_back,
        min_montant=settings.decp_min_montant or None,
        max_rows=settings.decp_max_awards or None,
        play_code=play_code,
    )
    stats["awards"] = filtered.height
    companies = aggregate_by_siret(filtered)[:max_companies]
    stats["companies"] = len(companies)

    for i, company in enumerate(companies):
        base = {
            "siret": company.get("siret"),
            "siren": company.get("siren"),
            "company_name": company.get("company_name"),
            "award_history": company.get("award_history"),
            "last_tender_date": company.get("last_tender_date"),
            "signal_details": company.get("signal_details"),
            "objets_joined": company.get("objets_joined"),
        }
        if company.get("objets_joined"):
            base["signal_details"] = (
                f"{company.get('signal_details') or ''} — {company['objets_joined'][:400]}"
            )
        try:
            async with session.begin_nested():
                prospect, created, status = await upsert_prospect(
                    session,
                    base=base,
                    signal_type="PUBLIC_AWARD",
                    source="DECP",
                    data_source=DATA_SOURCE_DECP,
                    play_code=play_code,
                    deep=False,
                    skip_sirene=skip_sirene,
                )
                if prospect is not None:
                    _, work_created = await _ensure_enrichment_work_item(
                        session,
                        pipeline_run_id=pipeline_run_id,
                        prospect_id=prospect.id,
                        play_code=play_code,
                        source_name="decp",
                        source_payload=base,
                        skip_sirene=skip_sirene,
                    )
                    stats["enrichment_queued"] += int(work_created)
            if status == "created":
                stats["created"] += 1
            elif status == "updated":
                stats["updated"] += 1
            else:
                stats["skipped"] += 1
        except Exception as exc:
            logger.exception("DECP upsert failed for %s", company.get("siren"))
            stats["errors"] += 1
            category = await _record_failed_item(
                session,
                pipeline_run_id=pipeline_run_id,
                task_name="persist_decp_company",
                source_name="decp",
                source_record_key=company.get("siret") or company.get("siren"),
                payload=base,
                exc=exc,
            )
            categories = stats["error_categories"]
            categories[category] = int(categories.get(category) or 0) + 1
            continue

        if (i + 1) % 15 == 0:
            await session.commit()
            logger.info("DECP progress %d/%d %s", i + 1, len(companies), stats)
        if settings.insee_api_key:
            await asyncio.sleep(settings.sirene_delay_seconds)

    await session.commit()
    return stats


async def ingest_registry(
    session,
    *,
    max_companies: int,
    play_code: str,
    skip_sirene: bool,
    pipeline_run_id: str,
) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "companies": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
        "error_categories": {},
        "enrichment_queued": 0,
    }
    settings = get_settings()
    logger.info("Registry source: field-service play hunt…")
    checkpoint_name = f"registry:{play_code}:all"
    checkpoint_row = await session.scalar(
        select(SourceCheckpoint).where(SourceCheckpoint.source_name == checkpoint_name)
    )
    checkpoint_before = {"partition": 0, "offset": 0}
    if checkpoint_row is not None:
        try:
            loaded = json.loads(checkpoint_row.high_water_mark)
            if isinstance(loaded, dict):
                checkpoint_before = {
                    "partition": int(loaded.get("partition", 0)),
                    "offset": int(loaded.get("offset", 0)),
                }
        except (TypeError, ValueError, json.JSONDecodeError):
            raise ValueError(f"Invalid durable checkpoint for {checkpoint_name}")

    companies, checkpoint_after, exhausted = (
        await discover_companies_for_play_checkpointed(
            play_code,
            max_results=max_companies,
            pages_per_query=4,
            checkpoint=checkpoint_before,
        )
    )
    stats["companies"] = len(companies)
    stats["checkpoint_before"] = checkpoint_before
    stats["checkpoint_after"] = checkpoint_after
    stats["source_exhausted"] = exhausted

    for i, company in enumerate(companies):
        base = {
            **company,
            "signal_details": (
                f"Field-service registry · NAF {company.get('naf_code')} · "
                f"{company.get('company_size')} · "
                f"{(company.get('decision_maker_title') or '')}"
            ),
        }
        try:
            async with session.begin_nested():
                prospect, created, status = await upsert_prospect(
                    session,
                    base=base,
                    signal_type="REGISTRY_FIELD",
                    source="Annuaire",
                    data_source=DATA_SOURCE_REG,
                    play_code=play_code,
                    deep=False,
                    skip_sirene=skip_sirene,
                )
                if prospect is not None:
                    _, work_created = await _ensure_enrichment_work_item(
                        session,
                        pipeline_run_id=pipeline_run_id,
                        prospect_id=prospect.id,
                        play_code=play_code,
                        source_name="registry",
                        source_payload=base,
                        skip_sirene=skip_sirene,
                    )
                    stats["enrichment_queued"] += int(work_created)
            if status == "created":
                stats["created"] += 1
            elif status == "updated":
                stats["updated"] += 1
            else:
                stats["skipped"] += 1
        except Exception as exc:
            logger.exception("Registry upsert failed for %s", company.get("siren"))
            stats["errors"] += 1
            category = await _record_failed_item(
                session,
                pipeline_run_id=pipeline_run_id,
                task_name="persist_registry_company",
                source_name="registry",
                source_record_key=company.get("siret") or company.get("siren"),
                payload=base,
                exc=exc,
            )
            categories = stats["error_categories"]
            categories[category] = int(categories.get(category) or 0) + 1
            continue

        if (i + 1) % 15 == 0:
            await session.commit()
            logger.info("Registry progress %d/%d %s", i + 1, len(companies), stats)
        if settings.insee_api_key:
            await asyncio.sleep(settings.sirene_delay_seconds)

    if checkpoint_row is None:
        checkpoint_row = SourceCheckpoint(
            source_name=checkpoint_name,
            high_water_mark=json.dumps(checkpoint_after, sort_keys=True),
        )
        session.add(checkpoint_row)
    else:
        checkpoint_row.high_water_mark = json.dumps(checkpoint_after, sort_keys=True)
        checkpoint_row.last_run_at = datetime.now(timezone.utc)
    await session.commit()
    return stats


async def run_ingestion(
    *,
    mode: Literal["full", "decp", "registry"] = "full",
    play_code: str,
    days_back: int | None = None,
    max_companies: int | None = None,
    run_contact_discovery: bool | None = None,
    skip_sirene: bool = False,
    requested_by: str | None = None,
    correlation_id: str | None = None,
    pipeline_run_id: str | None = None,
) -> dict[str, Any]:
    play = validate_ingestion_request(play_code, mode)
    settings = get_settings()
    days_back = days_back if days_back is not None else settings.decp_days_back
    max_companies = max_companies if max_companies is not None else settings.decp_max_companies
    if not 1 <= max_companies <= 2000:
        raise ValueError("max_companies must be between 1 and 2000")
    if run_contact_discovery is None:
        run_contact_discovery = settings.ingestion_run_contacts
    if run_contact_discovery:
        raise ValueError(
            "Contact discovery cannot run inside source ingestion; use the "
            "separate readiness-gated contact stage"
        )

    totals: dict[str, Any] = {
        "status": "running",
        "mode": mode,
        "play": play_code,
        "play_version": str(play.get("version") or "unknown"),
        "discovery_limit": max_companies,
        "run_contacts_requested": bool(run_contact_discovery),
        "contact_stage": "separate_readiness_gated_stage",
        "skip_sirene": skip_sirene,
        "decp": {},
        "registry": {},
        "raw_discovered": 0,
        # Raw payload storage is not yet activated. This counter deliberately
        # remains zero rather than claiming canonical prospects are raw rows.
        "raw_persisted": 0,
        "created": 0,
        "updated": 0,
        "enrichment_queued": 0,
        "contact_queued": 0,
        "errors": 0,
        "error_categories": {},
    }

    async with async_session_factory() as session:
        run: PipelineRun | None = None
        resolved_run_id: str | None = None
        try:
            if pipeline_run_id:
                run = await session.get(PipelineRun, pipeline_run_id)
                if run is None:
                    raise ValueError(f"Unknown pipeline_run_id: {pipeline_run_id}")
                resolved_run_id = run.id
                requested = run.request_config_json or {}
                expected = {
                    "play_code": play_code,
                    "mode": mode,
                    "discovery_limit": max_companies,
                    "run_contacts": bool(run_contact_discovery),
                    "skip_sirene": skip_sirene,
                }
                mismatches = {
                    key: (requested.get(key), value)
                    for key, value in expected.items()
                    if requested.get(key) != value
                }
                if mismatches:
                    raise ValueError(
                        f"Queued run configuration mismatch: {mismatches}"
                    )
            else:
                run = await create_pipeline_run(
                    session,
                    play_code=play_code,
                    mode=mode,
                    discovery_limit=max_companies,
                    run_contacts=bool(run_contact_discovery),
                    skip_sirene=skip_sirene,
                    requested_by=requested_by,
                    correlation_id=correlation_id,
                )
                pipeline_run_id = run.id
                resolved_run_id = run.id
            totals["run_id"] = run.id
            await session.commit()

            connectors = (
                ["decp", "registry"] if mode == "full" else [mode]
            )
            lock_keys = [
                f"ingestion:{play_code}:{connector}:all"
                for connector in connectors
            ]
            async with acquisition_run_locks(
                session, lock_keys
            ) as (acquired, blocked_key):
                if not acquired:
                    now = datetime.now(timezone.utc)
                    run.status = "skipped_overlap"
                    run.heartbeat_at = now
                    run.finished_at = now
                    totals["status"] = "skipped_overlap"
                    totals["skip_reason"] = f"active lock {blocked_key}"
                    apply_committed_totals(run, totals)
                    await session.commit()
                    return totals

                run.status = "running"
                run.heartbeat_at = datetime.now(timezone.utc)
                await session.commit()

                if mode == "full":
                    decp_limit = (max_companies + 1) // 2
                    registry_limit = max_companies // 2
                else:
                    decp_limit = max_companies
                    registry_limit = max_companies

                if mode in ("full", "decp") and decp_limit:
                    d = await ingest_decp(
                        session,
                        days_back=days_back,
                        max_companies=decp_limit,
                        play_code=play_code,
                        skip_sirene=skip_sirene,
                        pipeline_run_id=run.id,
                    )
                    totals["decp"] = d
                    totals["raw_discovered"] += d.get("companies", 0)
                    totals["created"] += d.get("created", 0)
                    totals["updated"] += d.get("updated", 0)
                    totals["enrichment_queued"] += d.get("enrichment_queued", 0)
                    totals["errors"] += d.get("errors", 0)

                if mode in ("full", "registry") and registry_limit:
                    r = await ingest_registry(
                        session,
                        max_companies=registry_limit,
                        play_code=play_code,
                        skip_sirene=skip_sirene,
                        pipeline_run_id=run.id,
                    )
                    totals["registry"] = r
                    totals["raw_discovered"] += r.get("companies", 0)
                    totals["created"] += r.get("created", 0)
                    totals["updated"] += r.get("updated", 0)
                    totals["enrichment_queued"] += r.get("enrichment_queued", 0)
                    totals["errors"] += r.get("errors", 0)
                    run.checkpoint_before_json = r.get("checkpoint_before")
                    run.checkpoint_after_json = r.get("checkpoint_after")

                for source in ("decp", "registry"):
                    categories = (totals.get(source) or {}).get(
                        "error_categories", {}
                    )
                    for category, count in categories.items():
                        totals["error_categories"][category] = (
                            int(totals["error_categories"].get(category) or 0)
                            + int(count)
                        )

                dispatch = await _dispatch_enrichment_work(
                    session, pipeline_run_id=run.id
                )
                totals["enrichment_dispatch"] = dispatch
                totals["enrichment_queued"] = dispatch["dispatched"]
                if dispatch["dispatch_errors"]:
                    totals["errors"] += dispatch["dispatch_errors"]
                    totals["error_categories"]["QUEUE_UNAVAILABLE"] = dispatch[
                        "dispatch_errors"
                    ]

                # Contact discovery is deliberately not invoked here. The
                # request remains visible and the gated stage can be activated
                # independently after score reconciliation.
                totals["contact_queued"] = 0
                totals["status"] = (
                    "completed_with_errors" if totals["errors"] else "completed"
                )
                run.status = totals["status"]
                run.heartbeat_at = datetime.now(timezone.utc)
                run.finished_at = run.heartbeat_at
                apply_committed_totals(run, totals)
                await session.commit()
        except Exception as exc:
            await session.rollback()
            if resolved_run_id is not None:
                async with async_session_factory() as failure_session:
                    failed_run = await failure_session.get(
                        PipelineRun, resolved_run_id
                    )
                    if failed_run is not None:
                        now = datetime.now(timezone.utc)
                        failed_run.status = "failed"
                        failed_run.heartbeat_at = now
                        failed_run.finished_at = now
                        failed_run.error_count = max(failed_run.error_count, 1)
                        failed_run.error_categories_json = {"RUN_FAILED": 1}
                        failed_run.error_summary = str(exc)[:4000]
                        totals["status"] = "failed"
                        totals["errors"] = max(int(totals["errors"]), 1)
                        totals["error_categories"] = {"RUN_FAILED": 1}
                        totals["error"] = str(exc)[:4000]
                        failed_run.stats_json = totals
                        await failure_session.commit()
            raise

    logger.info("Ingestion complete: %s", totals)
    return totals


async def run_ingestion_safe(**kwargs) -> dict[str, Any]:
    """Compatibility wrapper that preserves failure semantics."""
    return await run_ingestion(**kwargs)


async def rescore_all() -> int:
    """Recompute V4 opportunity scores for all opportunities."""
    from app.services.scoring_v4 import calculate_opportunity_score_v4
    from app.models import Opportunity
    from sqlalchemy.orm import selectinload

    n = 0
    async with async_session_factory() as session:
        result = await session.execute(
            select(Opportunity)
            .options(
                selectinload(Opportunity.company),
                selectinload(Opportunity.evidence_items)
            )
        )
        for opp in result.scalars().unique().all():
            calculate_opportunity_score_v4(session, opp)
            n += 1
        await session.commit()
    logger.info("Rescored %d opportunities (V4)", n)
    return n


async def main_async(args: argparse.Namespace) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    await init_db()
    if args.rescore_only:
        print({"rescored": await rescore_all()})
        return
    stats = await run_ingestion(
        mode=args.mode,
        play_code=args.play_code,
        days_back=args.days,
        max_companies=args.max_companies,
        run_contact_discovery=args.contacts,
        skip_sirene=args.skip_sirene,
    )
    print(stats)


def main() -> None:
    parser = argparse.ArgumentParser(description="ProspectForge multi-source acquisition")
    parser.add_argument(
        "--mode",
        choices=["full", "decp", "registry"],
        default="full",
        help="full=DECP+registry, decp=awards only, registry=field-service hunt",
    )
    parser.add_argument("--play-code", type=str, default=DEFAULT_PLAY_CODE)
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--max-companies", type=int, default=None)
    parser.add_argument("--contacts", action="store_true")
    parser.add_argument("--skip-sirene", action="store_true")
    parser.add_argument("--rescore-only", action="store_true")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
