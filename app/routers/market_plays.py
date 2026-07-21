"""Market Plays API Router."""

from typing import Any
from fastapi import APIRouter, HTTPException, Depends
from app.auth import get_current_user
from app.models import User
from app.plays import list_active_plays, get_play

router = APIRouter(prefix="/api/v1/market-plays", tags=["market_plays"])


@router.get("", response_model=list[dict[str, Any]])
async def get_market_plays(
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all registered UK and France market plays."""
    return list_active_plays()


@router.get("/{play_code}", response_model=dict[str, Any])
async def get_market_play_detail(
    play_code: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve detailed market play configuration."""
    try:
        return get_play(play_code)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Market play '{play_code}' not found.")
