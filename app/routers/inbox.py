"""Inbox and Reply Management."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import User, OutreachEvent

router = APIRouter(tags=["inbox"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/inbox", response_class=HTMLResponse)
async def page_inbox(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(OutreachEvent)
        .options(selectinload(OutreachEvent.prospect))
        .where(OutreachEvent.event_type == "Replied")
        .order_by(OutreachEvent.event_date.desc())
        .limit(20)
    )
    replies = list(result.scalars().all())

    return templates.TemplateResponse(
        request,
        "inbox.html",
        {"user": user, "replies": replies},
    )


@router.post("/inbox/{event_id}/classify")
async def classify_reply(
    event_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    classification: Annotated[str, Form()],
):
    allowed = {"positive_interest", "not_now", "opt_out", "referral"}
    if classification not in allowed:
        raise HTTPException(status_code=422, detail="Unsupported reply classification")
    event = await db.scalar(
        select(OutreachEvent)
        .options(selectinload(OutreachEvent.prospect))
        .where(OutreachEvent.id == event_id, OutreachEvent.event_type == "Replied")
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Reply event not found")
    event.event_kind = "reply_classified"
    event.objection_code = classification
    if classification == "positive_interest":
        event.pipeline_stage_after = "positive_reply"
    elif classification == "opt_out":
        from app import services
        from app.schemas import EventCreate

        await services.log_event(
            db,
            event.prospect,
            EventCreate(
                channel=event.channel,
                event_type="OptOut",
                notes="Opt-out classified from reply",
            ),
        )
    await db.commit()
    return RedirectResponse(url="/inbox", status_code=303)


@router.post("/inbox/{event_id}/resolve")
async def resolve_reply(
    event_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    event = await db.scalar(
        select(OutreachEvent).where(
            OutreachEvent.id == event_id,
            OutreachEvent.event_type == "Replied",
        )
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Reply event not found")
    event.event_kind = "reply_resolved"
    await db.commit()
    return RedirectResponse(url="/inbox", status_code=303)
