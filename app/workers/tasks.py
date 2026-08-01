import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select

from app.config import get_settings
from app.workers.celery_app import celery_app
from app.database import async_session_factory
from app.models import PipelineRun, Prospect, WorkItem
from app.plays import validate_ingestion_request

logger = logging.getLogger(__name__)

def run_async(coro):
    """Run one coroutine in a fresh worker-local loop."""
    return asyncio.run(coro)

# --- Ingestion Queue ---
@celery_app.task(bind=True, max_retries=3)
def ingest_market_play(
    self,
    *,
    play_code: str,
    mode: str,
    discovery_limit: int,
    run_contacts: bool = False,
    skip_sirene: bool = False,
    requested_by: str | None = None,
    correlation_id: str | None = None,
    pipeline_run_id: str | None = None,
) -> dict[str, Any]:
    """Discover companies from configured sources (DECP, Registry, Companies House)."""
    validate_ingestion_request(play_code, mode)
    if not 1 <= discovery_limit <= 2000:
        raise ValueError("discovery_limit must be between 1 and 2000")
    correlation_id = correlation_id or str(uuid.uuid4())
    logger.info(
        "Ingestion requested play=%s mode=%s limit=%d contacts=%s skip_sirene=%s "
        "correlation_id=%s",
        play_code,
        mode,
        discovery_limit,
        run_contacts,
        skip_sirene,
        correlation_id,
    )
    from app.jobs.ingestion import run_ingestion
    try:
        return run_async(
            run_ingestion(
                play_code=play_code,
                mode=mode,
                max_companies=discovery_limit,
                run_contact_discovery=run_contacts,
                skip_sirene=skip_sirene,
                requested_by=requested_by,
                correlation_id=correlation_id,
                pipeline_run_id=pipeline_run_id,
            )
        )
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            raise
        raise self.retry(
            exc=exc,
            countdown=min(120, 5 * (2 ** self.request.retries)),
        )


@celery_app.task(bind=True, max_retries=3)
def ingest_failed_raw_source(self, failed_item_id: str) -> dict[str, Any]:
    """Reconcile one operator-approved raw failure from durable source data."""
    from app.jobs.ingestion import reconcile_failed_raw_item

    try:
        return run_async(reconcile_failed_raw_item(failed_item_id))
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            raise
        raise self.retry(
            exc=exc,
            countdown=min(120, 5 * (2 ** self.request.retries)),
        )


@celery_app.task(bind=True, max_retries=3)
def ingest_recover_stale_work(self, limit: int = 500) -> dict[str, Any]:
    """Reclaim stale work leases, then dispatch only committed pending rows."""

    async def _recover() -> dict[str, Any]:
        from app.jobs.ingestion import _dispatch_enrichment_work
        from app.services.recovery import recover_stale_work_items

        async with async_session_factory() as session:
            result = await recover_stale_work_items(session, limit=limit)
            dispatch = {"pending": 0, "dispatched": 0, "dispatch_errors": 0}
            for run_id in result["pipeline_run_ids"]:
                run_dispatch = await _dispatch_enrichment_work(
                    session, pipeline_run_id=run_id
                )
                for key in dispatch:
                    dispatch[key] += int(run_dispatch[key])
            return {**result, "dispatch": dispatch}

    try:
        return run_async(_recover())
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            raise
        raise self.retry(
            exc=exc,
            countdown=min(120, 5 * (2 ** self.request.retries)),
        )

# --- Identity / Domain Queue ---
@celery_app.task(bind=True, max_retries=3)
def resolve_company_identity(self, company_id: str) -> dict[str, Any]:
    """Find the canonical web domain and merge dupes."""
    logger.info("Resolving identity for %s", company_id)
    return {
        "status": "disabled",
        "reason": "Canonical identity stage is not activated in this release",
    }

# --- Website Evidence Queue ---
@celery_app.task(bind=True, max_retries=3)
def extract_website_evidence(
    self,
    company_id: str,
    url: str = "",
    *,
    work_item_id: str | None = None,
) -> dict[str, Any]:
    """Scrape website to find pain points, tech stack, and offerings."""
    logger.info("Extracting evidence from %s for %s", url, company_id)

    async def _do_enrich():
        from app.discovery.enrich import deep_enrich, apply_enrichment_to_prospect
        async with async_session_factory() as session:
            item = None
            if work_item_id:
                item = await session.scalar(
                    select(WorkItem)
                    .where(WorkItem.id == work_item_id)
                    .with_for_update()
                )
                if item is None:
                    return {"status": "not_found", "work_item_id": work_item_id}
                if item.status == "completed":
                    return {"status": "already_completed", "work_item_id": item.id}
                item.status = "running"
                item.lock_lease_until = datetime.now(timezone.utc) + timedelta(minutes=5)
                await session.commit()
            prospect_key: int | str = int(company_id) if str(company_id).isdigit() else company_id
            prospect = await session.get(Prospect, prospect_key)
            if not prospect:
                if item is not None:
                    item.status = "failed"
                    item.lock_lease_until = None
                    await session.commit()
                return {"status": "not_found"}

            work_payload = item.payload if item is not None else {}
            data = await deep_enrich(
                siren=prospect.siren,
                siret=prospect.siret,
                company_name=prospect.company_name,
                existing={
                    "website": prospect.website,
                    "email": prospect.email,
                    "decision_maker_name": prospect.decision_maker_name,
                    "dirigeants": prospect.dirigeants,
                },
                run_contacts=False,
                infer_web=True,
                skip_sirene=bool(work_payload.get("skip_sirene")),
            )
            apply_enrichment_to_prospect(prospect, data)
            if item is not None:
                item.status = "completed"
                item.lock_lease_until = None
                await session.flush()
                run = await session.get(PipelineRun, item.pipeline_run_id)
                if run is not None:
                    run.enrichment_completed = int(
                        await session.scalar(
                            select(func.count(WorkItem.id)).where(
                                WorkItem.pipeline_run_id == run.id,
                                WorkItem.task_name == "extract_website_evidence",
                                WorkItem.status == "completed",
                            )
                        )
                        or 0
                    )
                    run.enrichment_failed = int(
                        await session.scalar(
                            select(func.count(WorkItem.id)).where(
                                WorkItem.pipeline_run_id == run.id,
                                WorkItem.task_name == "extract_website_evidence",
                                WorkItem.status == "failed",
                            )
                        )
                        or 0
                    )
                    run.heartbeat_at = datetime.now(timezone.utc)
            await session.commit()
            return {
                "status": "ok",
                "work_item_id": work_item_id,
                "log": data.get("enrichment_log"),
            }

    async def _record_retry(exc: Exception, final: bool) -> None:
        if not work_item_id:
            return
        async with async_session_factory() as session:
            item = await session.get(WorkItem, work_item_id)
            if item is None:
                return
            item.retry_count = int(item.retry_count or 0) + 1
            item.lock_lease_until = None
            item.status = "failed" if final else "pending"
            await session.flush()
            run = await session.get(PipelineRun, item.pipeline_run_id)
            if run is not None:
                run.enrichment_failed = int(
                    await session.scalar(
                        select(func.count(WorkItem.id)).where(
                            WorkItem.pipeline_run_id == run.id,
                            WorkItem.task_name == "extract_website_evidence",
                            WorkItem.status == "failed",
                        )
                    )
                    or 0
                )
                run.retry_count = int(run.retry_count or 0) + 1
                run.heartbeat_at = datetime.now(timezone.utc)
            await session.commit()

    try:
        return run_async(_do_enrich())
    except Exception as exc:
        final = self.request.retries >= self.max_retries
        run_async(_record_retry(exc, final))
        if final:
            raise
        raise self.retry(exc=exc, countdown=min(60, 2 ** (self.request.retries + 1)))

# --- Buyer / Contact Queue ---
@celery_app.task(bind=True, max_retries=3)
def contact_discovery_run(self, company_id: str) -> dict[str, Any]:
    """Run Apollo/Hunter/Reacher waterfall to find DMs and verify emails."""
    logger.info("Running contact discovery for %s", company_id)
    if company_id == "ALL":
        # Run bulk discovery (for Beat)
        from app.jobs.contact_discovery import run_nightly_contact_discovery
        stats = run_async(run_nightly_contact_discovery())
        return {"status": "ok", "stats": stats}

    async def _do_contact_discovery():
        from app.contact_intelligence.service import run_contact_discovery
        async with async_session_factory() as session:
            prospect = await session.get(Prospect, company_id)
            if not prospect:
                return {"status": "not_found"}
            await run_contact_discovery(session, prospect, actor="worker")
            await session.commit()
            return {"status": "ok"}

    return run_async(_do_contact_discovery())

# --- Campaigns & Notifications Queue ---
@celery_app.task(bind=True, max_retries=3)
def campaign_send_touch(self, prospect_id: str, touch_id: str) -> dict[str, Any]:
    """Execute a personalized outreach touchpoint."""
    if not get_settings().outreach_enabled:
        return {
            "status": "disabled",
            "reason": "Automatic outreach is disabled by configuration",
        }
    logger.info("Executing campaign touch %s for prospect %s", touch_id, prospect_id)

    async def _do_send_touch():
        from app.jobs.campaigns import run_campaign_step
        async with async_session_factory() as session:
            success = await run_campaign_step(session, prospect_id, touch_id)
            await session.commit()
            return {"status": "ok" if success else "failed"}

    return run_async(_do_send_touch())

# --- Administrative & Maintenance (Beat) ---
@celery_app.task(bind=True, max_retries=1)
def recalculate_scores(self) -> dict[str, Any]:
    logger.info("Running score recalculations")
    from app.jobs.recalculate_scores import recalculate_all_scores
    run_async(recalculate_all_scores())
    return {"status": "ok"}

@celery_app.task(bind=True, max_retries=3)
def recalculate_opportunity_score(self, opportunity_id: int) -> dict[str, Any]:
    logger.info("Recalculating score for opportunity %s", opportunity_id)
    
    async def _do_recalc():
        from app.database import async_session_factory
        from app.models import Opportunity, Prospect
        from app.services.scoring_v4 import calculate_opportunity_score_v4
        from app.commercial import recompute_commercial_state
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        async with async_session_factory() as session:
            opp = await session.scalar(
                select(Opportunity)
                .options(selectinload(Opportunity.company), selectinload(Opportunity.evidence_items))
                .where(Opportunity.id == opportunity_id)
            )
            if not opp:
                return {"status": "not_found"}
                
            await calculate_opportunity_score_v4(session, opp)
            prospect = await session.scalar(select(Prospect).where(Prospect.opportunity_id == opp.id))
            if prospect and not prospect.anonymized:
                prospect.opportunity_score = opp.latest_score
                await recompute_commercial_state(session, prospect)
                
            await session.commit()
            return {"status": "ok"}
            
    return run_async(_do_recalc())

@celery_app.task(bind=True, max_retries=1)
def retention_sweep(self) -> dict[str, Any]:
    logger.info("Running retention anonymization sweep")
    from app.jobs.retention import anonymize_stale_prospects
    run_async(anonymize_stale_prospects())
    return {"status": "ok"}
