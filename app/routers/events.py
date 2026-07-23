"""Outreach event logging — API + HTMX partials."""

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import CHANNELS, EVENT_TYPES, User
from app.schemas import EventCreate, EventOut
from app import services

router = APIRouter(tags=["events"])
templates = Jinja2Templates(directory="app/templates")


@router.post(
    "/api/prospects/{prospect_id}/events",
    response_model=EventOut,
    status_code=status.HTTP_201_CREATED,
)
async def api_log_event(
    prospect_id: str,
    data: EventCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    try:
        event = await services.log_event(db, prospect, data)
    except services.ComplianceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return event


@router.get("/api/prospects/{prospect_id}/events", response_model=list[EventOut])
async def api_list_events(
    prospect_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    return list(prospect.outreach_events or [])


@router.post("/prospects/{prospect_id}/events", response_class=HTMLResponse)
async def form_log_event(
    prospect_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    channel: Annotated[str, Form()],
    event_type: Annotated[str, Form()],
    notes: Annotated[Optional[str], Form()] = None,
    next_action: Annotated[Optional[str], Form()] = None,
    next_action_date: Annotated[Optional[str], Form()] = None,
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    nad = None
    if next_action_date:
        try:
            nad = datetime.fromisoformat(next_action_date)
        except ValueError:
            nad = None

    try:
        await services.log_event(
            db,
            prospect,
            EventCreate(
                channel=channel,
                event_type=event_type,
                notes=notes or None,
                next_action=next_action or None,
                next_action_date=nad,
            ),
        )
    except services.ComplianceError as exc:
        # Re-fetch and show error
        prospect = await services.get_prospect(db, prospect_id)
        return templates.TemplateResponse(
            request,
            "partials/event_timeline.html",
            {
                "user": user,
                "prospect": prospect,
                "event_types": EVENT_TYPES,
                "channels": CHANNELS,
                "error": str(exc),
            },
            status_code=400,
        )

    prospect = await services.get_prospect(db, prospect_id)

    # HTMX: return refreshed timeline + status badge
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            request,
            "partials/event_timeline.html",
            {
                "user": user,
                "prospect": prospect,
                "event_types": EVENT_TYPES,
                "channels": CHANNELS,
                "error": None,
            },
        )

    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=f"/prospects/{prospect_id}", status_code=303)


@router.post("/prospects/{prospect_id}/quick-event", response_class=HTMLResponse)
async def quick_event(
    prospect_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    event_type: Annotated[str, Form()],
    channel: Annotated[str, Form()] = "Email",
):
    """One-click event from list view (HTMX)."""
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    error = None
    try:
        await services.log_event(
            db,
            prospect,
            EventCreate(channel=channel, event_type=event_type),
        )
    except services.ComplianceError as exc:
        error = str(exc)

    prospect = await services.get_prospect(db, prospect_id)
    return templates.TemplateResponse(
        request,
        "partials/prospect_row.html",
        {
            "user": user,
            "prospect": prospect,
            "event_types": EVENT_TYPES,
            "channels": CHANNELS,
            "error": error,
        },
    )


@router.post("/kanban/move", response_class=HTMLResponse)
async def kanban_move(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    opportunity_id: Annotated[str, Form()],
    column: Annotated[str, Form()],
):
    """Drag-and-drop Kanban column change → update opportunity status."""
    from app.models import KANBAN_COLUMNS, Opportunity

    if column not in KANBAN_COLUMNS:
        raise HTTPException(status_code=400, detail=f"Unknown column: {column}")

    target_status = KANBAN_COLUMNS[column][0]

    from sqlalchemy import select
    result = await db.execute(select(Opportunity).where(Opportunity.id == opportunity_id))
    opp = result.scalar_one_or_none()

    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Basic state machine validation could go here
    # For now, update the status directly
    opp.status = target_status
    await db.commit()

    columns = await services.get_kanban_columns(db)
    return templates.TemplateResponse(
        request,
        "partials/kanban_board.html",
        {"user": user, "columns": columns, "channels": CHANNELS},
    )
