from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi.templating import Jinja2Templates

from app.auth import get_current_user
from app.database import get_db
from app.models import FailedWorkItem, PipelineRun, User

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(tags=["Operations"])

@router.get("/operations", response_class=HTMLResponse)
async def operations_dashboard(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    # Get latest pipeline runs
    runs_result = await db.execute(
        select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(10)
    )
    pipeline_runs = runs_result.scalars().all()

    # Get latest failed work items (DLQ)
    failed_result = await db.execute(
        select(FailedWorkItem).order_by(FailedWorkItem.failed_at.desc()).limit(20)
    )
    failed_items = failed_result.scalars().all()

    return templates.TemplateResponse(
        request,
        "operations/index.html",
        {
            "user": user,
            "pipeline_runs": pipeline_runs,
            "failed_items": failed_items,
        },
    )
