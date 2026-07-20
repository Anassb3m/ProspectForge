"""Prospect CRUD, CSV import/export, bulk actions — API + HTML."""

from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.commercial import is_suppressed
from app.database import get_db
from app.messaging import drafts_for_prospect
from app.models import (
    COMPANY_SIZES,
    EVENT_TYPES,
    PRIORITY_LEVELS,
    SECTORS,
    SIGNAL_TYPES,
    SOURCES,
    CHANNELS,
    User,
)
from app.schemas import (
    BulkStatusUpdate,
    ImportResult,
    ProspectCreate,
    ProspectDetail,
    ProspectListResponse,
    ProspectOut,
    ProspectUpdate,
)
from app import services

router = APIRouter(tags=["prospects"])
templates = Jinja2Templates(directory="app/templates")


def _to_out(p) -> ProspectOut:
    return ProspectOut(
        id=p.id,
        company_name=p.company_name,
        sector=p.sector,
        company_size=p.company_size,
        signal_type=p.signal_type,
        signal_details=p.signal_details,
        decision_maker_name=p.decision_maker_name,
        decision_maker_title=p.decision_maker_title,
        linkedin_url=p.linkedin_url,
        email=p.email,
        phone=p.phone,
        website=p.website,
        siren=p.siren,
        siret=p.siret,
        naf_code=p.naf_code,
        award_history=p.award_history,
        last_tender_date=p.last_tender_date,
        contact_source=p.contact_source,
        contact_confidence=p.contact_confidence,
        needs_manual_review=bool(p.needs_manual_review),
        data_source=p.data_source,
        informed_at=p.informed_at,
        opted_out=p.opted_out,
        opted_out_at=p.opted_out_at,
        urgency_score=p.urgency_score,
        priority_level=p.priority_level,
        source=p.source,
        notes=p.notes,
        created_at=p.created_at,
        updated_at=p.updated_at,
        current_status=p.current_status,
        next_action=p.next_action,
        next_action_date=p.next_action_date,
        contact_status=p.contact_status,
        award_count=p.award_count,
        award_total_value=p.award_total_value,
        score_badges=p.score_badges,
        why_this_lead=p.why_this_lead,
        fit_score=getattr(p, "fit_score", 0) or 0,
        timing_score=getattr(p, "timing_score", 0) or getattr(p, "trigger_score", 0) or 0,
        contactability_score=getattr(p, "contactability_score", 0) or getattr(p, "authority_score", 0) or 0,
        acquisition_score=getattr(p, "opportunity_score", 0) or getattr(p, "acquisition_score", 0) or 0,
        acquisition_stage=getattr(p, "acquisition_stage", None) or "discovered",
        city=getattr(p, "city", None),
        department=getattr(p, "department", None),
        dirigeants=getattr(p, "dirigeants", None),
        market_play_code=getattr(p, "market_play_code", None),
        opportunity_score=getattr(p, "opportunity_score", 0) or 0,
        pain_score=getattr(p, "pain_score", 0) or 0,
        trigger_score=getattr(p, "trigger_score", 0) or 0,
        authority_score=getattr(p, "authority_score", 0) or 0,
        readiness_state=getattr(p, "readiness_state", None),
        readiness_failures=getattr(p, "readiness_failures", None),
        suspected_pain=getattr(p, "suspected_pain", None),
        why_now=getattr(p, "why_now", None),
        recommended_buyer_role=getattr(p, "recommended_buyer_role", None),
        personalization_brief=getattr(p, "personalization_brief", None),
        recommended_offer=getattr(p, "recommended_offer", None),
        manual_review_state=getattr(p, "manual_review_state", None),
        contact_discovery_state=getattr(p, "contact_discovery_state", None),
    )


# ── JSON API ─────────────────────────────────────────────────────────────────


@router.get("/api/prospects", response_model=ProspectListResponse)
async def api_list_prospects(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    sector: Optional[str] = None,
    signal_type: Optional[str] = None,
    priority_level: Optional[str] = None,
    status_filter: Annotated[Optional[str], Query(alias="status")] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    include_opted_out: bool = False,
    sort_by: str = "urgency_score",
    sort_dir: str = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    items, total = await services.list_prospects(
        db,
        sector=sector,
        signal_type=signal_type,
        priority_level=priority_level,
        status=status_filter,
        source=source,
        search=search,
        min_score=min_score,
        max_score=max_score,
        include_opted_out=include_opted_out,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return ProspectListResponse(
        items=[_to_out(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/api/prospects", response_model=ProspectOut, status_code=status.HTTP_201_CREATED)
async def api_create_prospect(
    data: ProspectCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    prospect = await services.create_prospect(db, data)
    if not prospect:
        raise HTTPException(status_code=500, detail="Failed to create prospect")
    return _to_out(prospect)


@router.post("/api/prospects/import", response_model=ImportResult)
async def api_import_csv(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    content = await file.read()
    return await services.import_csv(db, content)


@router.get("/api/prospects/export/csv")
async def api_export_csv(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    sector: Optional[str] = None,
    signal_type: Optional[str] = None,
    priority_level: Optional[str] = None,
    status_filter: Annotated[Optional[str], Query(alias="status")] = None,
    include_opted_out: bool = False,
):
    items, _ = await services.list_prospects(
        db,
        sector=sector,
        signal_type=signal_type,
        priority_level=priority_level,
        status=status_filter,
        include_opted_out=include_opted_out,
        page=1,
        page_size=10_000,
    )
    csv_data = services.export_csv(items)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=prospects.csv"},
    )


@router.post("/api/prospects/bulk-status")
async def api_bulk_status(
    data: BulkStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    from app.schemas import EventCreate

    updated = 0
    skipped = 0
    errors: list[str] = []
    for pid in data.prospect_ids:
        prospect = await services.get_prospect(db, pid)
        if not prospect:
            errors.append(f"id={pid}: not found")
            continue
        if prospect.opted_out:
            skipped += 1
            continue
        try:
            await services.log_event(
                db,
                prospect,
                EventCreate(
                    channel=data.channel,
                    event_type=data.event_type,
                    notes=data.notes,
                ),
            )
            updated += 1
        except services.ComplianceError as exc:
            errors.append(f"id={pid}: {exc}")
    return {"updated": updated, "skipped": skipped, "errors": errors}


@router.get("/api/prospects/{prospect_id}", response_model=ProspectDetail)
async def api_get_prospect(
    prospect_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    base = _to_out(prospect)
    return ProspectDetail(
        **base.model_dump(),
        outreach_events=list(prospect.outreach_events or []),
    )


@router.patch("/api/prospects/{prospect_id}", response_model=ProspectOut)
async def api_update_prospect(
    prospect_id: int,
    data: ProspectUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    updates = data.model_dump(exclude_unset=True)
    prospect = await services.update_prospect(db, prospect, updates)
    return _to_out(prospect)


# ── HTML pages ───────────────────────────────────────────────────────────────


@router.get("/prospects", response_class=HTMLResponse)
async def page_prospects(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    sector: Optional[str] = None,
    signal_type: Optional[str] = None,
    priority_level: Optional[str] = None,
    status_filter: Annotated[Optional[str], Query(alias="status")] = None,
    search: Optional[str] = None,
    sort_by: str = "urgency_score",
    page: int = 1,
):
    items, total = await services.list_prospects(
        db,
        sector=sector,
        signal_type=signal_type,
        priority_level=priority_level,
        status=status_filter,
        search=search,
        sort_by=sort_by,
        page=page,
        page_size=50,
    )
    ctx = {
        "user": user,
        "prospects": items,
        "total": total,
        "page": page,
        "filters": {
            "sector": sector or "",
            "signal_type": signal_type or "",
            "priority_level": priority_level or "",
            "status": status_filter or "",
            "search": search or "",
            "sort_by": sort_by,
        },
        "sectors": SECTORS,
        "signal_types": SIGNAL_TYPES,
        "priority_levels": PRIORITY_LEVELS,
        "event_types": EVENT_TYPES,
        "channels": CHANNELS,
        "sources": SOURCES,
    }
    # HTMX partial refresh
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/prospect_table.html", ctx)
    return templates.TemplateResponse(request, "prospects.html", ctx)


@router.get("/prospects/new", response_class=HTMLResponse)
async def page_new_prospect(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
):
    return templates.TemplateResponse(
        request,
        "prospect_form.html",
        {
            "user": user,
            "prospect": None,
            "sectors": SECTORS,
            "company_sizes": COMPANY_SIZES,
            "signal_types": SIGNAL_TYPES,
            "sources": SOURCES,
        },
    )


@router.post("/prospects/new", response_class=HTMLResponse)
async def form_create_prospect(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    company_name: Annotated[str, Form()],
    sector: Annotated[str, Form()],
    company_size: Annotated[str, Form()],
    signal_type: Annotated[str, Form()],
    data_source: Annotated[str, Form()],
    source: Annotated[str, Form()],
    signal_details: Annotated[Optional[str], Form()] = None,
    decision_maker_name: Annotated[Optional[str], Form()] = None,
    decision_maker_title: Annotated[Optional[str], Form()] = None,
    linkedin_url: Annotated[Optional[str], Form()] = None,
    email: Annotated[Optional[str], Form()] = None,
    phone: Annotated[Optional[str], Form()] = None,
    website: Annotated[Optional[str], Form()] = None,
    notes: Annotated[Optional[str], Form()] = None,
    informed_at: Annotated[Optional[str], Form()] = None,
):
    from datetime import datetime

    informed = None
    if informed_at:
        try:
            informed = datetime.fromisoformat(informed_at)
        except ValueError:
            informed = None

    try:
        data = ProspectCreate(
            company_name=company_name,
            sector=sector,
            company_size=company_size,
            signal_type=signal_type,
            signal_details=signal_details or None,
            decision_maker_name=decision_maker_name or None,
            decision_maker_title=decision_maker_title or None,
            linkedin_url=linkedin_url or None,
            email=email or None,
            phone=phone or None,
            website=website or None,
            data_source=data_source,
            informed_at=informed,
            source=source,
            notes=notes or None,
        )
        prospect = await services.create_prospect(db, data)
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "prospect_form.html",
            {
                "user": user,
                "prospect": None,
                "error": str(exc),
                "sectors": SECTORS,
                "company_sizes": COMPANY_SIZES,
                "signal_types": SIGNAL_TYPES,
                "sources": SOURCES,
            },
            status_code=400,
        )
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=f"/prospects/{prospect.id}", status_code=303)


@router.get("/prospects/{prospect_id}", response_class=HTMLResponse)
async def page_prospect_detail(
    prospect_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    prospect.is_suppressed = await is_suppressed(  # type: ignore[attr-defined]
        db,
        email=prospect.email,
        siren=prospect.siren,
    )
    return templates.TemplateResponse(
        request,
        "prospect_detail.html",
        {
            "user": user,
            "prospect": prospect,
            "message_drafts": drafts_for_prospect(prospect),
            "event_types": EVENT_TYPES,
            "channels": CHANNELS,
        },
    )


@router.get("/prospects/{prospect_id}/edit", response_class=HTMLResponse)
async def page_edit_prospect(
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
        "prospect_form.html",
        {
            "user": user,
            "prospect": prospect,
            "sectors": SECTORS,
            "company_sizes": COMPANY_SIZES,
            "signal_types": SIGNAL_TYPES,
            "sources": SOURCES,
        },
    )


@router.post("/prospects/{prospect_id}/edit", response_class=HTMLResponse)
async def form_edit_prospect(
    prospect_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    company_name: Annotated[str, Form()],
    sector: Annotated[str, Form()],
    company_size: Annotated[str, Form()],
    signal_type: Annotated[str, Form()],
    data_source: Annotated[str, Form()],
    source: Annotated[str, Form()],
    signal_details: Annotated[Optional[str], Form()] = None,
    decision_maker_name: Annotated[Optional[str], Form()] = None,
    decision_maker_title: Annotated[Optional[str], Form()] = None,
    linkedin_url: Annotated[Optional[str], Form()] = None,
    email: Annotated[Optional[str], Form()] = None,
    phone: Annotated[Optional[str], Form()] = None,
    website: Annotated[Optional[str], Form()] = None,
    notes: Annotated[Optional[str], Form()] = None,
    informed_at: Annotated[Optional[str], Form()] = None,
):
    from datetime import datetime

    from fastapi.responses import RedirectResponse

    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    informed = prospect.informed_at
    if informed_at:
        try:
            informed = datetime.fromisoformat(informed_at)
        except ValueError:
            pass

    await services.update_prospect(
        db,
        prospect,
        {
            "company_name": company_name,
            "sector": sector,
            "company_size": company_size,
            "signal_type": signal_type,
            "signal_details": signal_details or None,
            "decision_maker_name": decision_maker_name or None,
            "decision_maker_title": decision_maker_title or None,
            "linkedin_url": linkedin_url or None,
            "email": email or None,
            "phone": phone or None,
            "website": website or None,
            "data_source": data_source,
            "informed_at": informed,
            "source": source,
            "notes": notes or None,
        },
    )
    return RedirectResponse(url=f"/prospects/{prospect_id}", status_code=303)


@router.get("/import", response_class=HTMLResponse)
async def page_import(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
):
    return templates.TemplateResponse(request, "import.html", {"user": user, "result": None})


@router.post("/import", response_class=HTMLResponse)
async def form_import(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    content = await file.read()
    result = await services.import_csv(db, content)
    return templates.TemplateResponse(
        request, "import.html", {"user": user, "result": result}
    )
