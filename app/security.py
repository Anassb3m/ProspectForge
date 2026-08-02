"""Production security helpers: CSRF (double-submit cookie) + login rate limit."""

from __future__ import annotations

import secrets
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import HTTPException, Request, status
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import get_settings

CSRF_COOKIE = "pf_csrf"
CSRF_HEADER = "x-csrf-token"

_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}

_CSRF_EXEMPT_PREFIXES = (
    "/auth/login",
    "/health",
    "/ready",
    "/static/",
    "/docs",
    "/openapi.json",
    "/redoc",
)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


class CSRFMiddleware:
    """
    Double-submit CSRF for browser form posts.
    Expects X-CSRF-Token or a native form ``_csrf`` field matching cookie
    ``pf_csrf``. Bearer-authenticated API requests remain exempt.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        replay_body: bytes | None = None
        if request.method in _MUTATING:
            path = request.url.path
            exempt = any(path.startswith(p) for p in _CSRF_EXEMPT_PREFIXES)
            auth = (request.headers.get("authorization") or "").lower()
            if auth.startswith("bearer "):
                exempt = True
            if not exempt:
                cookie = request.cookies.get(CSRF_COOKIE)
                submitted = request.headers.get(CSRF_HEADER)
                if not submitted:
                    content_type = request.headers.get("content-type", "")
                    if content_type.startswith(("application/x-www-form-urlencoded", "multipart/form-data")):
                        # Reading the form consumes the ASGI body. Cache and replay it
                        # so FastAPI can still bind the endpoint's Form parameters.
                        replay_body = await request.body()
                        form = await request.form()
                        candidate = form.get("_csrf")
                        if isinstance(candidate, str):
                            submitted = candidate
                if cookie and submitted and secrets.compare_digest(str(cookie), str(submitted)):
                    pass
                else:
                    if "text/html" in request.headers.get("accept", ""):
                        from app.main import templates
                        response = templates.TemplateResponse(
                            request, "errors/403.html", {"detail": "CSRF validation failed — refresh the page and retry"}, status_code=status.HTTP_403_FORBIDDEN
                        )
                    else:
                        response = JSONResponse(
                            status_code=status.HTTP_403_FORBIDDEN,
                            content={
                                "detail": "CSRF validation failed — refresh the page and retry"
                            },
                        )
                    await response(scope, receive, send)
                    return

        set_cookie_header: tuple[bytes, bytes] | None = None
        if CSRF_COOKIE not in request.cookies:
            cookie_response = Response()
            cookie_response.set_cookie(
                key=CSRF_COOKIE,
                value=generate_csrf_token(),
                httponly=False,
                samesite="lax",
                secure=get_settings().cookie_secure,
                max_age=86400 * 7,
            )
            set_cookie_header = next(
                (header for header in cookie_response.raw_headers if header[0] == b"set-cookie"),
                None,
            )

        async def send_with_csrf_cookie(message: Message) -> None:
            if message["type"] == "http.response.start" and set_cookie_header:
                message.setdefault("headers", []).append(set_cookie_header)
            await send(message)

        if replay_body is None:
            downstream_receive = receive
        else:
            body_sent = False

            async def downstream_receive() -> Message:
                nonlocal body_sent
                if not body_sent:
                    body_sent = True
                    return {
                        "type": "http.request",
                        "body": replay_body,
                        "more_body": False,
                    }
                return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, downstream_receive, send_with_csrf_cookie)


_login_hits: dict[str, Deque[float]] = defaultdict(deque)
_MAX_ATTEMPTS = 10
_WINDOW_SEC = 300

try:
    import redis.asyncio as aioredis
    _redis_pool = aioredis.from_url(get_settings().redis_url, decode_responses=True)
except ImportError:
    _redis_pool = None


async def check_login_rate_limit(client_key: str) -> None:
    if _redis_pool:
        try:
            now = time.time()
            pipeline = _redis_pool.pipeline()
            pipeline.zremrangebyscore(client_key, "-inf", now - _WINDOW_SEC)
            pipeline.zadd(client_key, {str(now): now})
            pipeline.zcard(client_key)
            pipeline.expire(client_key, _WINDOW_SEC)
            results = await pipeline.execute()
            count = results[2]
            if count > _MAX_ATTEMPTS:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many login attempts. Try again in a few minutes.",
                )
            return
        except Exception:
            # Fallback to local if Redis fails (e.g. during tests without Redis running)
            pass

    # Local fallback
    now = time.time()
    q = _login_hits[client_key]
    while q and now - q[0] > _WINDOW_SEC:
        q.popleft()
    if len(q) >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again in a few minutes.",
        )
    q.append(now)


async def clear_login_rate_limit(client_key: str) -> None:
    if _redis_pool:
        try:
            await _redis_pool.delete(client_key)
            return
        except Exception:
            pass
    _login_hits.pop(client_key, None)
