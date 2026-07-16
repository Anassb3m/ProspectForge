"""V3 daily action queue + enforced human qualification gate."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.commercial import recompute_commercial_state
from app.database import get_db
from app.discovery.annuaire import linkedin_people_url
from app.models import QualificationReview, Task, User, Prospect
from app.plays import DEFAULT_PLAY_CODE, get_play
from app import services

router = APIRouter(tags=["queue"])
templates = Jinja2Templates(directory="app/templates")

ACCEPT_REQUIRED = (
    "fit_confirmed",
    "pain_confirmed",
    "trigger_confirmed",
    "buyer_confirmed",
    "contact_confirmed",
    "offer_match_confirmed",
)


async def _daily_queue(
    db: AsyncSession,
    *,
    readiness: str | None = None,
    min_score: int | None = 55,
    review_state: str | None = None,
    limit: int = 40,
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
    if readiness:
        q = q.where(Prospect.readiness_state == readiness)
    if review_state:
        q = q.where(Prospect.manual_review_state == review_state)
    if min_score is not None:
        q = q.where(
            or_(
                Prospect.opportunity_score >= min_score,
                Prospect.acquisition_score >= min_score,
            )
        )
    result = await db.execute(q.limit(500))
    items = list(result.scalars().unique().all())

    def sort_key(p: Prospect) -> tuple:
        stage_rank = {
            "contact_ready": 0,
            "human_review_required": 1,
            "contact_required": 2,
            "research_required": 3,
            "buyer_required": 4,
            "insufficient_identity": 5,
            "suppressed": 9,
        }.get(p.readiness_state or "", 6)
        unreviewed = 0 if (p.manual_review_state or "unreviewed") == "unreviewed" else 1
        return (unreviewed, stage_rank, -(p.opportunity_score or p.acquisition_score or 0))

    items.sort(key=sort_key)
    return items[:limit]


@router.get("/queue", response_class=HTMLResponse)
async def page_daily_queue(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    readiness: Optional[str] = None,
    min_score: Optional[int] = Query(50),
    review: Optional[str] = None,
):
    items = await _daily_queue(
        db, readiness=readiness, min_score=min_score, review_state=review, limit=40
    )
    play = get_play(DEFAULT_PLAY_CODE)
    stats = {
        "total": len(items),
        "need_review": sum(1 for p in items if (p.manual_review_state or "") == "unreviewed"),
        "ready": sum(1 for p in items if p.readiness_state == "contact_ready"),
        "high": sum(1 for p in items if (p.opportunity_score or 0) >= 65),
    }
    return templates.TemplateResponse(
        request,
        "queue.html",
        {
            "user": user,
            "prospects": items,
            "play": play,
            "stats": stats,
            "filters": {
                "readiness": readiness or "",
                "min_score": min_score or "",
                "review": review or "",
            },
            "linkedin_people_url": linkedin_people_url,
            "error": None,
        },
    )


@router.get("/queue/{prospect_id}/qualify", response_class=HTMLResponse)
async def page_qualify(
    prospect_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    error: Optional[str] = None,
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Not found")
    await recompute_commercial_state(db, prospect)
    play = get_play(prospect.market_play_code or DEFAULT_PLAY_CODE)
    return templates.TemplateResponse(
        request,
        "qualify.html",
        {
            "user": user,
            "prospect": prospect,
            "play": play,
            "error": error,
            "linkedin_url": linkedin_people_url(
                prospect.company_name,
                prospect.decision_maker_name,
                prospect.decision_maker_title,
            ),
        },
    )


@router.post("/queue/{prospect_id}/qualify")
async def form_qualify(
    prospect_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    decision: Annotated[str, Form()],
    notes: Annotated[Optional[str], Form()] = None,
    fit_confirmed: Annotated[Optional[str], Form()] = None,
    pain_confirmed: Annotated[Optional[str], Form()] = None,
    trigger_confirmed: Annotated[Optional[str], Form()] = None,
    buyer_confirmed: Annotated[Optional[str], Form()] = None,
    contact_confirmed: Annotated[Optional[str], Form()] = None,
    offer_match_confirmed: Annotated[Optional[str], Form()] = None,
):
    prospect = await services.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Not found")

    if decision not in ("accept", "reject", "research_more", "park"):
        raise HTTPException(status_code=400, detail="Invalid decision")

    flags = {
        "fit_confirmed": bool(fit_confirmed),
        "pain_confirmed": bool(pain_confirmed),
        "trigger_confirmed": bool(trigger_confirmed),
        "buyer_confirmed": bool(buyer_confirmed),
        "contact_confirmed": bool(contact_confirmed),
        "offer_match_confirmed": bool(offer_match_confirmed),
    }

    # P0: Accept requires ALL mandatory confirmations
    if decision == "accept":
        missing = [name for name, value in flags.items() if not value]
        if missing:
            play = get_play(prospect.market_play_code or DEFAULT_PLAY_CODE)
            return templates.TemplateResponse(
                request,
                "qualify.html",
                {
                    "user": user,
                    "prospect": prospect,
                    "play": play,
                    "error": (
                        "Cannot accept. Missing required confirmations: "
                        + ", ".join(missing)
                        + ". Do not accept on award alone without verified pain."
                    ),
                    "linkedin_url": linkedin_people_url(
                        prospect.company_name,
                        prospect.decision_maker_name,
                        prospect.decision_maker_title,
                    ),
                },
                status_code=400,
            )

    review = QualificationReview(
        prospect_id=prospect.id,
        reviewer_email=user.email,
        decision=decision,
        fit_confirmed=flags["fit_confirmed"],
        pain_confirmed=flags["pain_confirmed"],
        trigger_confirmed=flags["trigger_confirmed"],
        buyer_confirmed=flags["buyer_confirmed"],
        contact_confirmed=flags["contact_confirmed"],
        offer_match_confirmed=flags["offer_match_confirmed"],
        notes=notes,
        reason_codes=list(flags.keys()) if decision == "accept" else None,
    )
    db.add(review)

    prospect.qualification_decision = decision
    prospect.qualification_notes = notes
    prospect.reviewed_at = datetime.now(timezone.utc)
    prospect.qualification_flags = flags  # type: ignore[attr-defined]

    if decision == "accept":
        prospect.manual_review_state = "accepted"
        prospect.needs_manual_review = False
        db.add(
            Task(
                prospect_id=prospect.id,
                task_type="first_outreach",
                title=f"Send first outreach — {prospect.company_name}",
                due_date=datetime.now(timezone.utc),
                priority=80,
                origin="qualification",
            )
        )
    elif decision == "reject":
        prospect.manual_review_state = "rejected"
        prospect.needs_manual_review = False
        prospect.acquisition_stage = "parked"
    elif decision == "park":
        prospect.manual_review_state = "parked"
        prospect.acquisition_stage = "parked"
    else:
        prospect.manual_review_state = "research_more"
        prospect.needs_manual_review = True
        db.add(
            Task(
                prospect_id=prospect.id,
                task_type="research",
                title=f"Research more evidence — {prospect.company_name}",
                due_date=datetime.now(timezone.utc),
                priority=60,
                origin="qualification",
                notes=notes,
            )
        )

    await db.flush()
    # Attach review for scorer source-of-truth
    prospect.latest_qualification = review  # type: ignore[attr-defined]
    await recompute_commercial_state(db, prospect)
    await db.flush()
    return RedirectResponse(url="/queue", status_code=303)


@router.get("/api/queue")
async def api_queue(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    min_score: int = 50,
    limit: int = 40,
):
    items = await _daily_queue(db, min_score=min_score, limit=limit)
    from app.routers.prospects import _to_out

    return {
        "play": DEFAULT_PLAY_CODE,
        "items": [_to_out(p) for p in items],
        "total": len(items),
    }
