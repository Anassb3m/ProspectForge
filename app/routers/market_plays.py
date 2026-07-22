"""Market Plays API Router."""

from typing import Any
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.auth import get_current_user
from app.models import User
from app.plays import list_active_plays, get_play

router = APIRouter(tags=["market_plays"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/market-plays", response_class=HTMLResponse)
async def page_market_plays(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Render Market Plays Management Operating System page."""
    plays = list_active_plays()
    return templates.TemplateResponse(
        request,
        "market_plays.html",
        {"request": request, "user": current_user, "plays": plays},
    )


@router.get("/api/v1/market-plays", response_model=list[dict[str, Any]])
async def get_market_plays(
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all registered UK and France market plays."""
    return list_active_plays()


@router.get("/api/v1/market-plays/{play_code}", response_model=dict[str, Any])
async def get_market_play_detail(
    play_code: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve detailed market play configuration."""
    try:
        return get_play(play_code)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Market play '{play_code}' not found.")
