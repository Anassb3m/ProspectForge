"""Acquisition cockpit: multi-source discovery, ICP queue, deep enrich, bulk ops."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.discovery.annuaire import linkedin_people_url
from app.discovery.emails import linkedin_search_url
from app.discovery.enrich import apply_enrichment_to_prospect
from app.jobs.enrichment import enrich_prospect_contacts
from app.models import CHANNELS, EVENT_TYPES, User, Prospect
from app.schemas import EnrichRequest, EnrichResult, EmailCandidateOut, IngestionResult
from app import services

router = APIRouter(tags=["sourcing"])
templates = Jinja2Templates(directory="app/templates")


async def _mark_enqueue_failed(db: AsyncSession, run, exc: Exception) -> None:
    now = datetime.now(timezone.utc)
    run.status = "enqueue_failed"
    run.heartbeat_at = now
    run.finished_at = now
    run.error_count = 1
    run.error_categories_json = {"QUEUE_UNAVAILABLE": 1}
    run.error_summary = str(exc)[:4000]
    run.stats_json = {
        "status": "enqueue_failed",
        "errors": 1,
        "error_categories": {"QUEUE_UNAVAILABLE": 1},
    }
    await db.commit()


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


@router.post("/api/sourcing/ingest", response_model=IngestionResult, status_code=status.HTTP_202_ACCEPTED)
async def api_run_ingestion(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    background: bool = Query(True),
    mode: str = Query("full", pattern="^(full|decp|registry)$"),
    play_code: str = Query("FIELD_OPERATIONS_FR_V2"),
    days: Optional[int] = None,
    max_companies: int = Query(80, ge=1, le=2000),
    contacts: bool = False,
    skip_sirene: bool = False,
):
    from app.jobs.ingestion import run_ingestion
    from app.plays import validate_ingestion_request
    from app.services.pipeline_runs import create_pipeline_run
    from app.workers.tasks import ingest_market_play

    try:
        validate_ingestion_request(play_code, mode)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not 1 <= max_companies <= 2000:
        raise HTTPException(
            status_code=422,
            detail="Max candidates must be between 1 and 2000 per recoverable run",
        )
    if contacts:
        raise HTTPException(
            status_code=422,
            detail=(
                "Contact discovery is a separate readiness-gated stage and "
                "cannot be requested during source ingestion"
            ),
        )
    if background:
        queued_run = await create_pipeline_run(
            db,
            play_code=play_code,
            mode=mode,
            discovery_limit=max_companies,
            run_contacts=contacts,
            skip_sirene=skip_sirene,
            requested_by=user.email,
        )
        await db.commit()
        try:
            ingest_market_play.delay(
                play_code=play_code,
                mode=mode,
                discovery_limit=max_companies,
                run_contacts=contacts,
                skip_sirene=skip_sirene,
                requested_by=user.email,
                correlation_id=queued_run.correlation_id,
                pipeline_run_id=queued_run.id,
            )
        except Exception as exc:
            await _mark_enqueue_failed(db, queued_run, exc)
            raise HTTPException(
                status_code=503,
                detail=f"Ingestion queue unavailable; run {queued_run.id} was not queued",
            ) from exc
        return IngestionResult(run_id=queued_run.id, status="queued")
    stats = await run_ingestion(
        play_code=play_code,
        mode=mode,  # type: ignore[arg-type]
        days_back=days,
        max_companies=max_companies,
        run_contact_discovery=contacts,
        skip_sirene=skip_sirene,
        requested_by=user.email,
    )
    return IngestionResult(
        run_id=stats.get("run_id"),
        status=stats.get("status", "completed"),
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
    prospect_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    run_contacts: bool = False,
    verify: bool = False,
):
    prospect = await services.get_legacy_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    if run_contacts:
        raise HTTPException(
            status_code=422,
            detail="Contact discovery must be queued through the separate readiness-gated stage",
        )
    if verify:
        raise HTTPException(
            status_code=422,
            detail="Contact verification belongs to the separate contact-discovery stage",
        )
    from app.services.evidence_queue import (
        dispatch_evidence_enrichment,
        queue_evidence_enrichment,
    )

    run, items = await queue_evidence_enrichment(db, [prospect], actor=_.email)
    dispatch = await dispatch_evidence_enrichment(db, run, items)
    if dispatch["dispatch_errors"]:
        raise HTTPException(
            status_code=503,
            detail=f"Evidence run {run.id} is durable but remains pending because the queue is unavailable",
        )
    return {
        "status": run.status,
        "run_id": run.id,
        "work_item_ids": [item.id for item in items],
        "prospect_id": prospect.id,
    }


@router.post("/api/sourcing/bulk-enrich", status_code=status.HTTP_202_ACCEPTED)
async def api_bulk_enrich(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    limit: int = Query(30, ge=1, le=100),
    run_contacts: bool = False,
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

    if run_contacts:
        raise HTTPException(
            status_code=422,
            detail="Bulk contact discovery is gated separately after evidence enrichment",
        )
    prospects = list(
        (
            await db.execute(select(Prospect).where(Prospect.id.in_(ids)))
        ).scalars().all()
    )
    from app.services.evidence_queue import (
        dispatch_evidence_enrichment,
        queue_evidence_enrichment,
    )

    run, items = await queue_evidence_enrichment(db, prospects, actor=_.email)
    dispatch = await dispatch_evidence_enrichment(db, run, items)
    if dispatch["dispatch_errors"]:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Evidence run {run.id} retained {dispatch['dispatch_errors']} pending work items "
                "because the queue is unavailable"
            ),
        )
    return {
        "run_id": run.id,
        "queued": dispatch["dispatched"],
        "duplicates": run.duplicate_count,
        "ids": ids,
        "contact_queued": 0,
    }


@router.post("/api/prospects/{prospect_id}/enrich", response_model=EnrichResult)
async def api_enrich_prospect(
    prospect_id: str,
    data: EnrichRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    prospect = await services.get_legacy_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    result = await enrich_prospect_contacts(
        db,
        prospect,
        person_name=data.person_name,
        domain=data.domain,
        run_harvester=data.run_harvester,
        verify=data.verify,
        apply_best=data.apply_best,
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
    prospect_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    email: str = Form(...),
    confidence: str = Form("manual"),
    source: str = Form("manual"),
):
    prospect = await services.get_legacy_prospect(db, prospect_id)
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
    prospect_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    prospect = await services.get_legacy_prospect(db, prospect_id)
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
    # Queue health stats (SQL aggregations)
    from sqlalchemy import func

    # Base query for stats
    base_stat_q = select(Prospect.id).where(and_(Prospect.anonymized.is_(False), Prospect.opted_out.is_(False)))

    total = await db.scalar(select(func.count()).select_from(base_stat_q.subquery()))
    hot = await db.scalar(select(func.count()).select_from(base_stat_q.where(Prospect.acquisition_score >= 70).subquery()))
    ready = await db.scalar(select(func.count()).select_from(base_stat_q.where(Prospect.acquisition_stage == "contact_ready").subquery()))
    with_dm = await db.scalar(select(func.count()).select_from(base_stat_q.where(Prospect.decision_maker_name.isnot(None)).subquery()))
    decp = await db.scalar(select(func.count()).select_from(base_stat_q.where(Prospect.signal_type == "DECP_WIN").subquery()))
    registry = await db.scalar(select(func.count()).select_from(base_stat_q.where(Prospect.signal_type.in_(("REGISTRY_FIELD", "REGISTRY_IT"))).subquery()))
    review = await db.scalar(select(func.count()).select_from(base_stat_q.where(Prospect.needs_manual_review.is_(True)).subquery()))

    stats = {
        "total": total or 0,
        "hot": hot or 0,
        "ready": ready or 0,
        "with_dm": with_dm or 0,
        "decp": decp or 0,
        "registry": registry or 0,
        "review": review or 0,
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
async def page_enrich_panel(
    request: Request,
    prospect_id: str,
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
async def form_enrich_prospect(
    request: Request,
    prospect_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    person_name: Annotated[Optional[str], Form()] = None,
    domain: Annotated[Optional[str], Form()] = None,
    apply_best: Annotated[Optional[str], Form()] = None,
    verify: Annotated[Optional[str], Form()] = "on",
):
    prospect = await services.get_legacy_prospect(db, prospect_id)
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
    prospect_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    prospect = await services.get_legacy_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    from app.services.evidence_queue import (
        dispatch_evidence_enrichment,
        queue_evidence_enrichment,
    )

    run, items = await queue_evidence_enrichment(db, [prospect], actor=user.email)
    dispatch = await dispatch_evidence_enrichment(db, run, items)
    if dispatch["dispatch_errors"]:
        raise HTTPException(
            status_code=503,
            detail=f"Evidence run {run.id} is durable but its work remains pending",
        )
    return HTMLResponse(
        f'<tr id="sourcing-row-{prospect.id}" class="bg-indigo-500/10">'
        '<td colspan="8" class="px-4 py-4 text-sm text-indigo-300">'
        f'Evidence enrichment queued for {escape(prospect.company_name)} · run {run.id}. '
        'Contact discovery remains a separate readiness-gated action. '
        f'<a class="underline" href="/prospects/{prospect.opportunity_id}">Open prospect</a>'
        '</td></tr>'
    )


@router.post("/prospects/{prospect_id}/use-email", response_class=HTMLResponse)
async def form_use_email(
    prospect_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    email: Annotated[str, Form()],
    confidence: Annotated[str, Form()] = "manual",
    source: Annotated[str, Form()] = "manual",
):
    prospect = await services.get_legacy_prospect(db, prospect_id)
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
    prospect_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    prospect = await services.get_legacy_prospect(db, prospect_id)
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
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    max_companies: Annotated[int, Form()] = 60,
    mode: Annotated[str, Form()] = "full",
    play_code: Annotated[str, Form()] = "FIELD_OPERATIONS_FR_V2",
    contacts: Annotated[Optional[str], Form()] = None,
    skip_sirene: Annotated[Optional[str], Form()] = None,
):
    from app.plays import validate_ingestion_request
    from app.services.pipeline_runs import create_pipeline_run
    from app.workers.tasks import ingest_market_play

    try:
        validate_ingestion_request(play_code, mode)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if contacts:
        raise HTTPException(
            status_code=422,
            detail=(
                "Contact discovery is a separate readiness-gated stage and "
                "cannot be requested during source ingestion"
            ),
        )

    queued_run = await create_pipeline_run(
        db,
        play_code=play_code,
        mode=mode,
        discovery_limit=max_companies,
        run_contacts=bool(contacts),
        skip_sirene=bool(skip_sirene),
        requested_by=user.email,
    )
    await db.commit()
    try:
        ingest_market_play.delay(
            play_code=play_code,
            mode=mode,
            discovery_limit=max_companies,
            run_contacts=bool(contacts),
            skip_sirene=bool(skip_sirene),
            requested_by=user.email,
            correlation_id=queued_run.correlation_id,
            pipeline_run_id=queued_run.id,
        )
    except Exception as exc:
        await _mark_enqueue_failed(db, queued_run, exc)
        raise HTTPException(
            status_code=503,
            detail=f"Ingestion queue unavailable; run {queued_run.id} was not queued",
        ) from exc
    labels = {
        "full": "DECP awards + field-service registry",
        "decp": "DECP public awards only",
        "registry": "Field-service registry only",
    }
    return templates.TemplateResponse(
        request,
        "partials/ingestion_status.html",
        {
            "user": user,
            "message": (
                f"Run {queued_run.id} queued ({play_code}, {labels.get(mode, mode)}, "
                f"max {max_companies}, durable enrichment queued separately, "
                f"skip Sirene={'on' if skip_sirene else 'off'})."
            ),
        },
    )


@router.post("/sourcing/bulk-enrich", response_class=HTMLResponse)
async def form_bulk_enrich(
    request: Request,
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

    prospects = list(
        (
            await db.execute(select(Prospect).where(Prospect.id.in_(ids)))
        ).scalars().all()
    )
    from app.services.evidence_queue import (
        dispatch_evidence_enrichment,
        queue_evidence_enrichment,
    )

    run, items = await queue_evidence_enrichment(db, prospects, actor=user.email)
    dispatch = await dispatch_evidence_enrichment(db, run, items)

    return templates.TemplateResponse(
        request,
        "partials/ingestion_status.html",
        {
            "user": user,
            "message": (
                f"Evidence run {run.id}: {dispatch['dispatched']} queued, "
                f"{dispatch['dispatch_errors']} durable pending, {run.duplicate_count} duplicate requests. "
                "Contact discovery is queued separately only after readiness gates pass."
            ),
        },
    )
