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
import logging
from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import async_session_factory, init_db
from app.discovery.annuaire import discover_companies_for_play
from app.discovery.decp import aggregate_by_siret, filter_relevant, load_decp
from app.commercial import is_suppressed, recompute_commercial_state, upsert_evidence
from app.discovery.enrich import apply_enrichment_to_prospect, deep_enrich
from app.models import IngestionRun, OutreachEvent, Prospect
from app.plays import DEFAULT_PLAY_CODE
from app.services.normalized import upsert_normalized_company

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
    deep: bool = True,
    run_contacts: bool = False,
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
            run_contacts=run_contacts,
            verify_email=verify_email,
            infer_web=True,
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
            sector=enrich_data.get("sector") or "Field Services",
            company_size=enrich_data.get("company_size") or "unknown",
            signal_type=signal_type,
            signal_details=(base.get("signal_details") or "")[:2000] or None,
            data_source=data_source,
            source=source,
            acquisition_stage="researching",
            needs_manual_review=True,
            contact_confidence="none",
            contact_source="none",
            market_play_code=DEFAULT_PLAY_CODE,
            readiness_state="research_required",
            manual_review_state="unreviewed",
        )
        session.add(prospect)

        # Dual-write to Normalized schema
        await upsert_normalized_company(
            session=session,
            company_name=str(name)[:200],
            siren=siren,
            siret=siret,
            website=enrich_data.get("website"),
            city=enrich_data.get("city"),
            department=enrich_data.get("department"),
            payload=base,
            play_code=DEFAULT_PLAY_CODE
        )

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

    prospect.market_play_code = prospect.market_play_code or DEFAULT_PLAY_CODE
    apply_enrichment_to_prospect(prospect, enrich_data)

    # Dedupe-aware evidence upsert (normalized table is source of truth)
    await upsert_evidence(
        session,
        prospect.id,
        list(base.get("evidence") or enrich_data.get("evidence") or [])[:20],
    )
    await recompute_commercial_state(session, prospect)
    await session.flush()

    return prospect, created, "created" if created else "updated"


async def ingest_decp(
    session,
    *,
    days_back: int,
    max_companies: int,
    run_contacts: bool,
    play_code: str,
    skip_sirene_block: bool = False,
) -> dict[str, int]:
    stats = {"awards": 0, "companies": 0, "created": 0, "updated": 0, "skipped": 0, "errors": 0}
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
            _, created, status = await upsert_prospect(
                session,
                base=base,
                signal_type="PUBLIC_AWARD",
                source="DECP",
                data_source=DATA_SOURCE_DECP,
                deep=True,
                run_contacts=run_contacts,
            )
            if status == "created":
                stats["created"] += 1
            elif status == "updated":
                stats["updated"] += 1
            else:
                stats["skipped"] += 1
        except Exception:
            logger.exception("DECP upsert failed for %s", company.get("siren"))
            stats["errors"] += 1
            await session.rollback()
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
    run_contacts: bool,
) -> dict[str, int]:
    stats = {"companies": 0, "created": 0, "updated": 0, "skipped": 0, "errors": 0}
    settings = get_settings()
    logger.info("Registry source: field-service play hunt…")
    companies = await discover_companies_for_play(
        DEFAULT_PLAY_CODE, max_results=max_companies, pages_per_query=4
    )
    stats["companies"] = len(companies)

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
            _, created, status = await upsert_prospect(
                session,
                base=base,
                signal_type="REGISTRY_FIELD",
                source="Annuaire",
                data_source=DATA_SOURCE_REG,
                deep=True,
                run_contacts=run_contacts,
            )
            if status == "created":
                stats["created"] += 1
            elif status == "updated":
                stats["updated"] += 1
            else:
                stats["skipped"] += 1
        except Exception:
            logger.exception("Registry upsert failed for %s", company.get("siren"))
            stats["errors"] += 1
            await session.rollback()
            continue

        if (i + 1) % 15 == 0:
            await session.commit()
            logger.info("Registry progress %d/%d %s", i + 1, len(companies), stats)
        if settings.insee_api_key:
            await asyncio.sleep(settings.sirene_delay_seconds)

    await session.commit()
    return stats


async def run_ingestion(
    *,
    mode: Literal["full", "decp", "registry", "companies_house"] = "full",
    play_code: str = DEFAULT_PLAY_CODE,
    days_back: int | None = None,
    max_companies: int | None = None,
    run_contact_discovery: bool | None = None,
    skip_sirene: bool = False,
) -> dict[str, Any]:
    settings = get_settings()
    days_back = days_back if days_back is not None else settings.decp_days_back
    max_companies = max_companies if max_companies is not None else settings.decp_max_companies
    if run_contact_discovery is None:
        run_contact_discovery = settings.ingestion_run_contacts

    totals: dict[str, Any] = {
        "mode": mode,
        "play": play_code,
        "decp": {},
        "registry": {},
        "companies_house": {},
        "created": 0,
        "updated": 0,
        "errors": 0,
    }

    async with async_session_factory() as session:
        run = IngestionRun(
            adapter=mode,
            market_play_code=play_code,
            status="running",
        )
        session.add(run)
        await session.flush()

        try:
            if mode in ("full", "decp"):
                d = await ingest_decp(
                    session,
                    days_back=days_back,
                    max_companies=max_companies,
                    run_contacts=bool(run_contact_discovery),
                    play_code=play_code,
                )
                totals["decp"] = d
                totals["created"] += d.get("created", 0)
                totals["updated"] += d.get("updated", 0)
                totals["errors"] += d.get("errors", 0)

            if mode in ("full", "registry"):
                reg_max = max_companies if mode == "registry" else max(40, max_companies // 2)
                r = await ingest_registry(
                    session,
                    max_companies=reg_max,
                    run_contacts=bool(run_contact_discovery),
                )
                totals["registry"] = r
                totals["created"] += r.get("created", 0)
                totals["updated"] += r.get("updated", 0)
                totals["errors"] += r.get("errors", 0)

            if mode == "companies_house":
                logger.info("Companies House ingestion requested (play %s)", play_code)
                totals["companies_house"] = {"companies": 0, "created": 0, "updated": 0, "errors": 0}

            run.status = "completed"
            run.stats_json = totals
            run.finished_at = datetime.now(timezone.utc)
            await session.commit()
        except Exception as exc:
            run.status = "failed"
            run.error_summary = str(exc)[:2000]
            run.finished_at = datetime.now(timezone.utc)
            await session.commit()
            raise

    logger.info("Ingestion complete: %s", totals)
    return totals


async def run_ingestion_safe(**kwargs) -> dict[str, Any]:
    try:
        return await run_ingestion(**kwargs)
    except Exception:
        logger.exception("Ingestion job failed")
        return {"errors": 1}


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
        choices=["full", "decp", "registry", "companies_house"],
        default="full",
        help="full=DECP+registry, decp=awards only, registry=field-service hunt, companies_house=UK",
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
