"""Campaign and Outreach Operations."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Campaign, Touch, User, MarketPlayVersion

router = APIRouter(tags=["campaigns"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/campaigns", response_class=HTMLResponse)
async def page_campaigns_index(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(Campaign)
        .options(selectinload(Campaign.touches))
        .order_by(Campaign.created_at.desc())
    )
    campaigns = list(result.scalars().all())

    return templates.TemplateResponse(
        request,
        "campaigns/index.html",
        {"user": user, "campaigns": campaigns},
    )


@router.get("/campaigns/new", response_class=HTMLResponse)
async def page_campaigns_builder(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(MarketPlayVersion))
    plays = list(result.scalars().all())
    return templates.TemplateResponse(
        request,
        "campaigns/builder.html",
        {"user": user, "plays": plays},
    )


@router.post("/campaigns/new", response_class=RedirectResponse)
async def create_campaign(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    name: Annotated[str, Form()],
    play_version_id: Annotated[str, Form()],
    daily_send_cap: Annotated[int, Form()] = 10,
):
    campaign = Campaign(
        name=name,
        play_version_id=play_version_id,
        daily_send_cap=daily_send_cap,
        status="draft",
    )
    db.add(campaign)
    await db.commit()
    return RedirectResponse(url=f"/campaigns/{campaign.id}", status_code=303)


@router.get("/campaigns/{campaign_id}", response_class=HTMLResponse)
async def page_campaign_detail(
    request: Request,
    campaign_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(Campaign)
        .where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return templates.TemplateResponse(
        request,
        "campaigns/detail.html",
        {"user": user, "campaign": campaign, "tab": "overview"},
    )


@router.get("/drafts", response_class=HTMLResponse)
async def page_draft_queue(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(Touch)
        .options(
            selectinload(Touch.campaign),
            selectinload(Touch.opportunity)
        )
        .where(Touch.status == "draft")
        .order_by(Touch.created_at.asc())
    )
    drafts = list(result.scalars().all())

    return templates.TemplateResponse(
        request,
        "campaigns/drafts.html",
        {"user": user, "drafts": drafts},
    )


@router.post("/drafts/{touch_id}/approve", response_class=RedirectResponse)
async def approve_draft(
    request: Request,
    touch_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(Touch).where(Touch.id == touch_id))
    touch = result.scalar_one_or_none()
    if not touch:
        raise HTTPException(status_code=404, detail="Draft not found")

    from app.config import get_settings

    settings = get_settings()
    if not settings.outreach_enabled:
        touch.status = "paused_production"
    else:
        touch.status = "approved"
        
    await db.commit()
    return RedirectResponse(url="/drafts", status_code=303)
