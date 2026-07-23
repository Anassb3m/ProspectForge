import logging
import asyncio
from typing import Any, Dict


from app.workers.celery_app import celery_app
from app.database import async_session_factory
from app.models import Prospect

logger = logging.getLogger(__name__)

def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# --- Ingestion Queue ---
@celery_app.task(bind=True, max_retries=3)
def ingest_market_play(self, play_code: str, mode: str, limit: int = 10) -> Dict[str, Any]:
    """Discover companies from configured sources (DECP, Registry, Companies House)."""
    logger.info("Ingesting market play %s in mode %s (limit %d)", play_code, mode, limit)
    from app.jobs.ingestion import run_ingestion
    stats = run_async(run_ingestion(mode=mode, max_companies=limit, run_contact_discovery=False, skip_sirene=False))
    return {"status": "ok", "play_code": play_code, "stats": stats}

# --- Identity / Domain Queue ---
@celery_app.task(bind=True, max_retries=3)
def resolve_company_identity(self, company_id: str) -> Dict[str, Any]:
    """Find the canonical web domain and merge dupes."""
    logger.info("Resolving identity for %s", company_id)
    # Placeholder for future Phase 3 normalizations
    return {"status": "ok"}

# --- Website Evidence Queue ---
@celery_app.task(bind=True, max_retries=3)
def extract_website_evidence(self, company_id: str, url: str) -> Dict[str, Any]:
    """Scrape website to find pain points, tech stack, and offerings."""
    logger.info("Extracting evidence from %s for %s", url, company_id)

    async def _do_enrich():
        from app.discovery.enrich import deep_enrich, apply_enrichment_to_prospect
        async with async_session_factory() as session:
            prospect = await session.get(Prospect, company_id)
            if not prospect:
                return {"status": "not_found"}

            # Use deep enrich
            data = await deep_enrich(
                prospect.siren, prospect.siret, prospect.website, prospect.name, prospect.decision_maker_name
            )
            apply_enrichment_to_prospect(prospect, data)
            await session.commit()
            return {"status": "ok", "log": data.get("enrichment_log")}

    return run_async(_do_enrich())

# --- Buyer / Contact Queue ---
@celery_app.task(bind=True, max_retries=3)
def contact_discovery_run(self, company_id: str) -> Dict[str, Any]:
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
def campaign_send_touch(self, prospect_id: str, touch_id: str) -> Dict[str, Any]:
    """Execute a personalized outreach touchpoint."""
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
def recalculate_scores(self) -> Dict[str, Any]:
    logger.info("Running score recalculations")
    from app.jobs.recalculate_scores import recalculate_all_scores
    run_async(recalculate_all_scores())
    return {"status": "ok"}

@celery_app.task(bind=True, max_retries=1)
def retention_sweep(self) -> Dict[str, Any]:
    logger.info("Running retention anonymization sweep")
    from app.jobs.retention import anonymize_stale_prospects
    run_async(anonymize_stale_prospects())
    return {"status": "ok"}
