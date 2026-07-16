"""
Multi-source acquisition engine.

Sources:
  A) DECP public awards (timing + capacity signal)
  B) Recherche Entreprises IT SMEs (ICP volume + dirigeants)
  C) Deep enrich: Annuaire → Sirene → contacts → ICP score

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
from app.discovery.annuaire import discover_it_smes
from app.discovery.decp import aggregate_by_siret, filter_relevant, load_decp
from app.discovery.enrich import apply_enrichment_to_prospect, deep_enrich
from app.models import OutreachEvent, Prospect

logger = logging.getLogger(__name__)

DATA_SOURCE_DECP = "DECP consolidated public awards (data.gouv.fr) + Sirene/Annuaire"
DATA_SOURCE_REG = "Recherche Entreprises (api.gouv.fr) IT SME hunt + Sirene"


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
            sector=enrich_data.get("sector") or "IT / Digital",
            company_size=enrich_data.get("company_size") or "1-10",
            signal_type=signal_type,
            signal_details=(base.get("signal_details") or "")[:2000] or None,
            data_source=data_source,
            source=source,
            acquisition_stage="discovered",
            needs_manual_review=True,
            contact_confidence="none",
            contact_source="none",
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
            if ltd and (not prospect.last_tender_date or ltd > prospect.last_tender_date):
                prospect.last_tender_date = ltd
            # Upgrade signal if DECP is stronger
            if signal_type == "DECP_WIN":
                prospect.signal_type = "DECP_WIN"
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

    apply_enrichment_to_prospect(prospect, enrich_data)
    await session.flush()
    return prospect, created, "created" if created else "updated"


async def ingest_decp(
    session,
    *,
    days_back: int,
    max_companies: int,
    run_contacts: bool,
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
                signal_type="DECP_WIN",
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
    logger.info("Registry source: hunting IT SMEs…")
    companies = await discover_it_smes(max_results=max_companies, pages_per_query=4)
    stats["companies"] = len(companies)

    for i, company in enumerate(companies):
        base = {
            **company,
            "signal_details": (
                f"IT SME registry hunt · NAF {company.get('naf_code')} · "
                f"{company.get('company_size')} · "
                f"{(company.get('decision_maker_title') or '')}"
            ),
        }
        try:
            _, created, status = await upsert_prospect(
                session,
                base=base,
                signal_type="REGISTRY_IT",
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
    mode: Literal["full", "decp", "registry"] = "full",
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
        "decp": {},
        "registry": {},
        "created": 0,
        "updated": 0,
        "errors": 0,
    }

    async with async_session_factory() as session:
        if mode in ("full", "decp"):
            d = await ingest_decp(
                session,
                days_back=days_back,
                max_companies=max_companies,
                run_contacts=bool(run_contact_discovery),
            )
            totals["decp"] = d
            totals["created"] += d.get("created", 0)
            totals["updated"] += d.get("updated", 0)
            totals["errors"] += d.get("errors", 0)

        if mode in ("full", "registry"):
            # Registry fills ICP volume; slightly higher cap for full mode
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

    logger.info("Ingestion complete: %s", totals)
    return totals


async def run_ingestion_safe(**kwargs) -> dict[str, Any]:
    try:
        return await run_ingestion(**kwargs)
    except Exception:
        logger.exception("Ingestion job failed")
        return {"errors": 1}


async def rescore_all() -> int:
    """Recompute acquisition + urgency scores for all prospects."""
    from app.discovery.enrich import apply_enrichment_to_prospect

    n = 0
    async with async_session_factory() as session:
        result = await session.execute(
            select(Prospect)
            .options(selectinload(Prospect.outreach_events))
            .where(Prospect.anonymized.is_(False))
        )
        for p in result.scalars().unique().all():
            apply_enrichment_to_prospect(p, {})
            n += 1
        await session.commit()
    logger.info("Rescored %d prospects", n)
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
        choices=["full", "decp", "registry"],
        default="full",
        help="full=DECP+registry, decp=awards only, registry=IT SME hunt",
    )
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--max-companies", type=int, default=None)
    parser.add_argument("--contacts", action="store_true")
    parser.add_argument("--skip-sirene", action="store_true")
    parser.add_argument("--rescore-only", action="store_true")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
