"""Dashboard metrics, follow-ups, Kanban — API + HTML."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import CHANNELS, User
from app.schemas import DashboardMetrics, FollowUpItem
from app import services

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/api/dashboard/metrics", response_model=DashboardMetrics)
async def api_metrics(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return await services.compute_metrics(db)


@router.get("/api/dashboard/follow-ups-due", response_model=list[FollowUpItem])
async def api_follow_ups(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return await services.get_follow_ups_due(db)


@router.get("/", response_class=HTMLResponse)
async def page_dashboard(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    metrics = await services.compute_metrics(db)
    follow_ups = await services.get_follow_ups_due(db)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "user": user,
            "metrics": metrics,
            "follow_ups": follow_ups[:10],
        },
    )


@router.get("/follow-ups", response_class=HTMLResponse)
async def page_follow_ups(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    items = await services.get_follow_ups_due(db)
    return templates.TemplateResponse(
        request,
        "follow_ups.html",
        {"user": user, "items": items},
    )


@router.get("/kanban", response_class=HTMLResponse)
async def page_kanban(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    columns = await services.get_kanban_columns(db)
    return templates.TemplateResponse(
        request,
        "kanban.html",
        {"user": user, "columns": columns, "channels": CHANNELS},
    )
