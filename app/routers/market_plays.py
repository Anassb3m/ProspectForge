"""Market Plays API Router."""

from typing import Any, Annotated
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.plays import get_play

router = APIRouter(tags=["market_plays"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/market-plays", response_class=HTMLResponse)
async def page_market_plays(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
):
    """Render Market Plays Management Operating System page."""
    from sqlalchemy import select, func
    from app.models import MarketPlay, Prospect

    result = await db.execute(select(MarketPlay).order_by(MarketPlay.code))
    plays_db = result.scalars().all()

    # Calculate stats per play
    enriched_plays = []
    for play in plays_db:
        # Eligible count
        eligible = await db.scalar(
            select(func.count(Prospect.id)).where(Prospect.market_play_code == play.code)
        )
        # Contact ready count
        contact_ready = await db.scalar(
            select(func.count(Prospect.id)).where(
                Prospect.market_play_code == play.code,
                Prospect.acquisition_stage == "contact_ready"
            )
        )

        play_dict = {
            "code": play.code,
            "name": play.name,
            "jurisdiction": play.config_json.get("jurisdiction", "FR"),
            "locale": play.config_json.get("locale", "fr-FR"),
            "operational_size": play.config_json.get("operational_size", {}),
            "target_sizes": play.config_json.get("target_sizes", []),
            "offer_summary": play.offer_summary,
            "eligible_count": eligible or 0,
            "contact_ready_count": contact_ready or 0,
            "version": play.version,
            "is_active": play.is_active,
        }
        enriched_plays.append(play_dict)

    return templates.TemplateResponse(
        request,
        "market_plays.html",
        {"request": request, "user": current_user, "plays": enriched_plays},
    )

@router.get("/api/v1/market-plays", response_model=list[dict[str, Any]])
async def get_market_plays(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    from sqlalchemy import select
    from app.models import MarketPlay
    result = await db.execute(select(MarketPlay).where(MarketPlay.is_active.is_(True)))
    plays_db = result.scalars().all()
    return [{"code": p.code, "name": p.name} for p in plays_db]


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
