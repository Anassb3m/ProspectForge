"""Inbox and Reply Management."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    # This is a stub for the Replies inbox.
    # We would fetch actual reply events (e.g. from IMAP sync) here.
    # Currently just fetching any 'Replied' events.
    result = await db.execute(
        select(OutreachEvent)
        .where(OutreachEvent.event_type == "Replied")
        .order_by(OutreachEvent.occurred_at.desc())
        .limit(20)
    )
    replies = list(result.scalars().all())

    return templates.TemplateResponse(
        request,
        "inbox.html",
        {"user": user, "replies": replies},
    )
