"""ProspectForge FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import __version__
from app.auth import hash_password
from app.config import get_settings
from app.database import async_session_factory, engine, init_db
from app.models import User
from app.routers import auth, contact_intelligence, dashboard, events, market_plays, prospects, queue, sourcing
from app.security import CSRFMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()
templates = Jinja2Templates(directory="app/templates")


async def bootstrap_admin() -> None:
    """Create the admin user from env if the users table is empty."""
    async with async_session_factory() as session:
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none() is not None:
            return
        admin = User(
            email=settings.admin_email,
            hashed_password=hash_password(settings.admin_password),
        )
        session.add(admin)
        await session.commit()
        logger.info("Bootstrap admin created: %s", settings.admin_email)


async def seed_market_plays() -> None:
    """Ensure V3 default market play exists in DB."""
    from app.models import MarketPlay
    from app.plays import ACTIVE_PLAYS

    async with async_session_factory() as session:
        for code, cfg in ACTIVE_PLAYS.items():
            existing = await session.execute(select(MarketPlay).where(MarketPlay.code == code))
            if existing.scalar_one_or_none():
                continue
            raw_ver = cfg.get("version")
            try:
                ver_int = int(str(raw_ver).split(".")[0])
            except (ValueError, TypeError):
                ver_int = 1

            session.add(
                MarketPlay(
                    code=code,
                    name=cfg["name"],
                    version=ver_int,
                    is_active=bool(cfg.get("is_active", True)),
                    config_json=cfg,
                    offer_name=cfg.get("offer_name"),
                    offer_summary=cfg.get("offer_summary"),
                )
            )
            logger.info("Seeded market play %s", code)
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    production_errors = settings.production_validation_errors()
    if production_errors:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(production_errors))
    await init_db()
    await bootstrap_admin()
    await seed_market_plays()

    if settings.enable_scheduler:
        from app.jobs.scheduler import start_scheduler, stop_scheduler

        start_scheduler()
        yield
        stop_scheduler()
    else:
        yield


_docs_url = None if settings.is_production and not settings.debug else "/docs"
_redoc_url = None if settings.is_production and not settings.debug else "/redoc"

app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="Client Acquisition OS — prospect scoring, outreach tracking, pipeline",
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url="/openapi.json" if _docs_url else None,
)

if settings.is_production and settings.trusted_host_list != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)

# CSRF on HTML form mutations (Bearer API exempt)
app.add_middleware(CSRFMiddleware)

static_dir = Path("app/static")
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(auth.router)
app.include_router(prospects.router)
app.include_router(events.router)
app.include_router(dashboard.router)
app.include_router(sourcing.router)
app.include_router(queue.router)
app.include_router(contact_intelligence.router)
app.include_router(market_plays.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": __version__}


@app.get("/ready")
async def ready():
    """Readiness: app process + database connectivity (for deploy checks)."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception as exc:
        logger.warning("Readiness check failed: %s", exc)
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "error"},
        )


@app.get("/login")
async def login_page(request: Request):
    from app.auth import COOKIE_NAME, decode_token, get_user_by_email

    token = request.cookies.get(COOKIE_NAME)
    if token:
        data = decode_token(token)
        if data and data.email:
            async with async_session_factory() as session:
                user = await get_user_by_email(session, data.email)
                if user:
                    return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(request, "login.html", {"error": None, "email": ""})


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Redirect unauthenticated browser navigations to login
    if exc.status_code in (401, 303) and "text/html" in request.headers.get("accept", ""):
        location = exc.headers.get("Location") if exc.headers else None
        if location:
            return RedirectResponse(url=location, status_code=303)
        if exc.status_code == 401:
            return RedirectResponse(url="/login", status_code=303)
    if exc.status_code == 303 and exc.headers and "Location" in exc.headers:
        return RedirectResponse(url=exc.headers["Location"], status_code=303)
    return await http_exception_handler(request, exc)
