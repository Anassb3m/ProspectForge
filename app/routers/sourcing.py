"""Acquisition cockpit: multi-source discovery, ICP queue, deep enrich, bulk ops."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.discovery.annuaire import linkedin_people_url
from app.discovery.emails import linkedin_search_url
from app.discovery.enrich import apply_enrichment_to_prospect, deep_enrich
from app.jobs.enrichment import enrich_prospect_contacts
from app.models import CHANNELS, EVENT_TYPES, User, Prospect
from app.schemas import EnrichRequest, EnrichResult, EmailCandidateOut, IngestionResult
from app import services

router = APIRouter(tags=["sourcing"])
templates = Jinja2Templates(directory="app/templates")


async def _load_sourcing_queue(
    db: AsyncSession,
    *,
    contact_filter: str | None = None,
    needs_review: bool | None = None,
    signal_type: str | None = None,
    stage: str | None = None,
    min_acquisition: int | None = None,
    has_dm: bool | None = None,
    search: str | None = None,
    sort: str = "acquisition",
    limit: int = 150,
) -> list[Prospect]:
    q = (
        select(Prospect)
        .options(selectinload(Prospect.outreach_events))
        .where(
            and_(
                Prospect.anonymized.is_(False),
                Prospect.opted_out.is_(False),
            )
        )
    )
    if signal_type:
        q = q.where(Prospect.signal_type == signal_type)
    if stage:
        q = q.where(Prospect.acquisition_stage == stage)
    if min_acquisition is not None:
        q = q.where(Prospect.acquisition_score >= min_acquisition)
    if needs_review is True:
        q = q.where(Prospect.needs_manual_review.is_(True))
    if has_dm is True:
        q = q.where(Prospect.decision_maker_name.isnot(None))
    if contact_filter == "verified":
        q = q.where(Prospect.contact_confidence == "verified")
    elif contact_filter == "ready":
        q = q.where(Prospect.acquisition_stage == "contact_ready")
    elif contact_filter == "needs_review":
        q = q.where(
            or_(
                Prospect.needs_manual_review.is_(True),
                Prospect.contact_confidence.in_(["needs_review", "none"]),
                Prospect.contact_confidence.is_(None),
            )
        )
    elif contact_filter == "no_email":
        q = q.where(or_(Prospect.email.is_(None), Prospect.email == ""))
    elif contact_filter == "has_dirigeant":
        q = q.where(Prospect.decision_maker_name.isnot(None))
    if search:
        like = f"%{search}%"
        q = q.where(
            or_(
                Prospect.company_name.ilike(like),
                Prospect.siren.ilike(like),
                Prospect.siret.ilike(like),
                Prospect.decision_maker_name.ilike(like),
                Prospect.city.ilike(like),
            )
        )

    if sort == "urgency":
        q = q.order_by(Prospect.urgency_score.desc())
    elif sort == "fit":
        q = q.order_by(Prospect.fit_score.desc())
    elif sort == "timing":
        q = q.order_by(Prospect.timing_score.desc())
    elif sort == "recent":
        q = q.order_by(Prospect.created_at.desc())
    else:
        q = q.order_by(Prospect.acquisition_score.desc(), Prospect.urgency_score.desc())

    q = q.limit(limit)
    result = await db.execute(q)
    return list(result.scalars().unique().all())


@router.get("/api/sourcing/queue")
async def api_sourcing_queue(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    contact_filter: Optional[str] = None,
    needs_review: Optional[bool] = None,
    signal_type: Optional[str] = None,
    stage: Optional[str] = None,
    min_acquisition: Optional[int] = None,
    search: Optional[str] = None,
    sort: str = "acquisition",
):
    items = await _load_sourcing_queue(
        db,
        contact_filter=contact_filter,
        needs_review=needs_review,
        signal_type=signal_type,
        stage=stage,
        min_acquisition=min_acquisition,
        search=search,
        sort=sort,
    )
    from app.routers.prospects import _to_out

    return {"items": [_to_out(p) for p in items], "total": len(items)}


@router.post("/api/sourcing/ingest", response_model=IngestionResult)
async def api_run_ingestion(
    background_tasks: BackgroundTasks,
    _: Annotated[User, Depends(get_current_user)],
    background: bool = Query(True),
    mode: str = Query("full", pattern="^(full|decp|registry)$"),
    days: Optional[int] = None,
    max_companies: Optional[int] = Query(80, ge=1, le=500),
    contacts: bool = False,
    skip_sirene: bool = False,
):
    from app.jobs.ingestion import run_ingestion
    from app.workers.tasks import ingest_market_play

    if background:
        ingest_market_play.delay(
            play_code="DEFAULT",
            mode=mode,
            limit=max_companies,
        )
        return IngestionResult(companies=0, created=0, updated=0)
    stats = await run_ingestion(
        mode=mode,  # type: ignore[arg-type]
        days_back=days,
        max_companies=max_companies,
        run_contact_discovery=contacts,
        skip_sirene=skip_sirene,
    )
    return IngestionResult(
        awards=stats.get("decp", {}).get("awards", 0) if isinstance(stats.get("decp"), dict) else 0,
        companies=(
            (stats.get("decp", {}) or {}).get("companies", 0)
            + (stats.get("registry", {}) or {}).get("companies", 0)
        ),
        created=stats.get("created", 0),
        updated=stats.get("updated", 0),
        errors=stats.get("errors", 0),
    )


@router.post("/api/prospects/{prospect_id}/deep-enrich")
async def api_deep_enrich(
    prospect_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    run_contacts: bool = True,
    verify: bool = False,
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    data = await deep_enrich(
        siren=prospect.siren,
        siret=prospect.siret,
        company_name=prospect.company_name,
        existing={
            "website": prospect.website,
            "email": prospect.email,
            "dirigeants": prospect.dirigeants,
        },
        run_contacts=run_contacts,
        verify_email=verify,
    )
    apply_enrichment_to_prospect(prospect, data)
    await db.flush()
    from app.routers.prospects import _to_out

    return {"prospect": _to_out(prospect), "log": data.get("enrichment_log")}


@router.post("/api/sourcing/bulk-enrich")
async def api_bulk_enrich(
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    limit: int = Query(30, ge=1, le=100),
    run_contacts: bool = True,
):
    """Deep-enrich top unscored / thin prospects in background."""
    result = await db.execute(
        select(Prospect)
        .where(
            and_(
                Prospect.anonymized.is_(False),
                Prospect.opted_out.is_(False),
                or_(
                    Prospect.last_enriched_at.is_(None),
                    Prospect.decision_maker_name.is_(None),
                    Prospect.acquisition_score < 55,
                ),
            )
        )
        .order_by(Prospect.acquisition_score.desc())
        .limit(limit)
    )
    ids = [p.id for p in result.scalars().all()]

    from app.workers.tasks import extract_website_evidence, contact_discovery_run

    for pid in ids:
        extract_website_evidence.delay(company_id=str(pid), url="")
        if run_contacts:
            contact_discovery_run.delay(company_id=str(pid))
            
    return {"queued": len(ids), "ids": ids}


@router.post("/api/prospects/{prospect_id}/enrich", response_model=EnrichResult)
async def api_enrich_prospect(
    prospect_id: int,
    body: EnrichRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    result = await enrich_prospect_contacts(
        db,
        prospect,
        person_name=body.person_name,
        domain=body.domain,
        run_harvester=body.run_harvester,
        verify=body.verify,
        apply_best=body.apply_best,
    )
    # Refresh acquisition scores after contact change
    apply_enrichment_to_prospect(prospect, {})
    await db.flush()
    return EnrichResult(
        domain=result.get("domain"),
        candidates=[
            EmailCandidateOut(**c) for c in (result.get("candidates") or []) if "email" in c
        ],
        best_email=result.get("best_email"),
        contact_source=result.get("contact_source"),
        contact_confidence=result.get("contact_confidence"),
        needs_manual_review=bool(result.get("needs_manual_review")),
        message=result.get("message"),
    )


@router.post("/api/prospects/{prospect_id}/use-email")
async def api_use_email(
    prospect_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    email: str = Form(...),
    confidence: str = Form("manual"),
    source: str = Form("manual"),
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    if confidence not in {"published_personal", "published_generic", "confirmed_by_reply"}:
        raise HTTPException(
            status_code=400,
            detail="Inferred/Reacher-only candidates require a source-backed Contact Intelligence review",
        )
    from app.commercial import recompute_commercial_state, validate_contact_confidence, validate_discovery_state

    prospect.email = email.strip().lower()
    prospect.contact_source = source
    try:
        prospect.contact_confidence = validate_contact_confidence(confidence)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    prospect.contact_discovery_state = validate_discovery_state("published")
    prospect.needs_manual_review = prospect.contact_confidence not in (
        "deliverable", "verified", "published_personal", "confirmed_by_reply", "manual_confirmed",
    )
    await recompute_commercial_state(db, prospect)
    await db.flush()
    return {"ok": True, "email": prospect.email, "opportunity_score": prospect.opportunity_score}


@router.post("/api/prospects/{prospect_id}/mark-reviewed")
async def api_mark_reviewed(
    prospect_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    prospect.needs_manual_review = False
    prospect.reviewed_at = datetime.now(timezone.utc)
    await db.flush()
    return {"ok": True}


# ── HTML cockpit ─────────────────────────────────────────────────────────────


@router.get("/sourcing", response_class=HTMLResponse)
async def page_sourcing(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    contact_filter: Optional[str] = None,
    needs_review: Optional[bool] = None,
    signal_type: Optional[str] = None,
    stage: Optional[str] = None,
    min_acquisition: Optional[int] = Query(None),
    search: Optional[str] = None,
    sort: str = "acquisition",
):
    items = await _load_sourcing_queue(
        db,
        contact_filter=contact_filter,
        needs_review=needs_review,
        signal_type=signal_type or None,
        stage=stage,
        min_acquisition=min_acquisition,
        search=search,
        sort=sort,
    )
    # Queue health stats
    all_q = await db.execute(
        select(Prospect).where(
            and_(Prospect.anonymized.is_(False), Prospect.opted_out.is_(False))
        )
    )
    all_p = list(all_q.scalars().all())
    stats = {
        "total": len(all_p),
        "hot": sum(1 for p in all_p if (p.acquisition_score or 0) >= 70),
        "ready": sum(1 for p in all_p if p.acquisition_stage == "contact_ready"),
        "with_dm": sum(1 for p in all_p if p.decision_maker_name),
        "decp": sum(1 for p in all_p if p.signal_type == "DECP_WIN"),
        "registry": sum(1 for p in all_p if p.signal_type in ("REGISTRY_FIELD", "REGISTRY_IT")),
        "review": sum(1 for p in all_p if p.needs_manual_review),
    }
    ctx = {
        "user": user,
        "prospects": items,
        "stats": stats,
        "filters": {
            "contact_filter": contact_filter or "",
            "needs_review": needs_review,
            "signal_type": signal_type or "",
            "stage": stage or "",
            "min_acquisition": min_acquisition or "",
            "search": search or "",
            "sort": sort,
        },
        "event_types": EVENT_TYPES,
        "channels": CHANNELS,
        "linkedin_search_url": linkedin_search_url,
        "linkedin_people_url": linkedin_people_url,
    }
    if request.headers.get("HX-Request") and request.headers.get("HX-Target") == "sourcing-table":
        return templates.TemplateResponse(request, "partials/sourcing_table.html", ctx)
    return templates.TemplateResponse(request, "sourcing.html", ctx)


@router.get("/prospects/{prospect_id}/enrich", response_class=HTMLResponse)
async def page_enrich_modal(
    prospect_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    return templates.TemplateResponse(
        request,
        "partials/enrich_panel.html",
        {
            "user": user,
            "prospect": prospect,
            "result": None,
            "linkedin_url": linkedin_people_url(
                prospect.company_name,
                prospect.decision_maker_name,
                prospect.decision_maker_title,
            ),
        },
    )


@router.post("/prospects/{prospect_id}/enrich", response_class=HTMLResponse)
async def form_enrich(
    prospect_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    person_name: Annotated[Optional[str], Form()] = None,
    domain: Annotated[Optional[str], Form()] = None,
    apply_best: Annotated[Optional[str], Form()] = None,
    verify: Annotated[Optional[str], Form()] = "on",
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    result = await enrich_prospect_contacts(
        db,
        prospect,
        person_name=person_name or None,
        domain=domain or None,
        run_harvester=True,
        verify=bool(verify),
        apply_best=bool(apply_best),
    )
    apply_enrichment_to_prospect(prospect, {})
    await db.flush()
    prospect = await services.get_prospect(db, prospect_id)
    return templates.TemplateResponse(
        request,
        "partials/enrich_panel.html",
        {
            "user": user,
            "prospect": prospect,
            "result": result,
            "linkedin_url": linkedin_people_url(
                prospect.company_name,
                person_name or prospect.decision_maker_name,
                prospect.decision_maker_title,
            ),
        },
    )


@router.post("/prospects/{prospect_id}/deep-enrich", response_class=HTMLResponse)
async def form_deep_enrich(
    prospect_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    data = await deep_enrich(
        siren=prospect.siren,
        siret=prospect.siret,
        company_name=prospect.company_name,
        existing={"website": prospect.website, "email": prospect.email},
        run_contacts=True,
        verify_email=False,
    )
    apply_enrichment_to_prospect(prospect, data)
    await db.flush()
    prospect = await services.get_prospect(db, prospect_id)
    # Return refreshed table row if HTMX from queue
    if request.headers.get("HX-Target", "").startswith("sourcing-row"):
        return templates.TemplateResponse(
            request,
            "partials/sourcing_row.html",
            {
                "user": user,
                "prospect": prospect,
                "linkedin_search_url": linkedin_search_url,
                "linkedin_people_url": linkedin_people_url,
            },
        )
    return templates.TemplateResponse(
        request,
        "partials/enrich_panel.html",
        {
            "user": user,
            "prospect": prospect,
            "result": {
                "message": f"Deep enrich done: {', '.join(data.get('enrichment_log') or [])}",
                "candidates": prospect.contact_candidates or [],
                "best_email": prospect.email,
                "contact_confidence": prospect.contact_confidence,
            },
            "linkedin_url": linkedin_people_url(
                prospect.company_name,
                prospect.decision_maker_name,
                prospect.decision_maker_title,
            ),
            "flash": "Deep enrichment complete",
        },
    )


@router.post("/prospects/{prospect_id}/use-email", response_class=HTMLResponse)
async def form_use_email(
    prospect_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    email: Annotated[str, Form()],
    confidence: Annotated[str, Form()] = "manual",
    source: Annotated[str, Form()] = "manual",
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    if confidence not in {"published_personal", "published_generic", "confirmed_by_reply"}:
        raise HTTPException(
            status_code=400,
            detail="Add a public evidence URL in Contact Intelligence before selecting this address",
        )
    from app.commercial import recompute_commercial_state, validate_contact_confidence

    prospect.email = email.strip().lower()
    prospect.contact_source = source
    try:
        conf = validate_contact_confidence(confidence)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    prospect.contact_confidence = conf
    prospect.contact_discovery_state = "published"
    await recompute_commercial_state(db, prospect)
    await db.flush()
    prospect = await services.get_prospect(db, prospect_id)
    return templates.TemplateResponse(
        request,
        "partials/enrich_panel.html",
        {
            "user": user,
            "prospect": prospect,
            "result": {
                "message": f"Using {prospect.email}",
                "candidates": prospect.contact_candidates or [],
                "best_email": prospect.email,
                "contact_confidence": prospect.contact_confidence,
            },
            "linkedin_url": linkedin_people_url(
                prospect.company_name,
                prospect.decision_maker_name,
                prospect.decision_maker_title,
            ),
            "flash": f"Email set · opportunity {prospect.opportunity_score}",
        },
    )


@router.post("/prospects/{prospect_id}/mark-reviewed", response_class=HTMLResponse)
async def form_mark_reviewed(
    prospect_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    prospect.needs_manual_review = False
    prospect.reviewed_at = datetime.now(timezone.utc)
    await db.flush()
    return HTMLResponse(
        f'<tr id="sourcing-row-{prospect_id}" class="bg-emerald-50">'
        f'<td colspan="8" class="py-2 text-sm text-emerald-700 px-4">'
        f"✓ {prospect.company_name} marked reviewed</td></tr>"
    )


@router.post("/sourcing/run-ingestion", response_class=HTMLResponse)
async def form_run_ingestion(
    request: Request,
    background_tasks: BackgroundTasks,
    user: Annotated[User, Depends(get_current_user)],
    max_companies: Annotated[int, Form()] = 60,
    mode: Annotated[str, Form()] = "full",
    play_code: Annotated[str, Form()] = "FIELD_OPERATIONS_FR_V2",
    contacts: Annotated[Optional[str], Form()] = None,
    skip_sirene: Annotated[Optional[str], Form()] = None,
):
    from app.workers.tasks import ingest_market_play

    if mode not in ("full", "decp", "registry", "companies_house"):
        mode = "full"
    
    ingest_market_play.delay(
        play_code=play_code,
        mode=mode,
        limit=max_companies,
    )
    labels = {
        "full": "DECP awards + field-service registry",
        "decp": "DECP public awards only",
        "registry": "Field-service registry only",
        "companies_house": "Companies House (UK)",
    }
    return templates.TemplateResponse(
        request,
        "partials/ingestion_status.html",
        {
            "user": user,
            "message": (
                f"Acquisition engine started ({labels.get(mode, mode)}, max {max_companies}). "
                "Sirene + Annuaire enrich run automatically. Refresh queue in a few minutes."
            ),
        },
    )


@router.post("/sourcing/bulk-enrich", response_class=HTMLResponse)
async def form_bulk_enrich(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Form()] = 25,
):
    result = await db.execute(
        select(Prospect.id)
        .where(
            and_(
                Prospect.anonymized.is_(False),
                Prospect.opted_out.is_(False),
                or_(
                    Prospect.last_enriched_at.is_(None),
                    Prospect.decision_maker_name.is_(None),
                ),
            )
        )
        .limit(limit)
    )
    ids = [row[0] for row in result.all()]

    from app.workers.tasks import extract_website_evidence, contact_discovery_run

    for pid in ids:
        extract_website_evidence.delay(company_id=str(pid), url="")
        contact_discovery_run.delay(company_id=str(pid))
        
    return templates.TemplateResponse(
        request,
        "partials/ingestion_status.html",
        {
            "user": user,
            "message": f"Deep-enrich queued for {len(ids)} prospects (dirigeants + emails + ICP score).",
        },
    )
