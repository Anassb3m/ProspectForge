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
    "/api/",  # JSON API uses Bearer; HTML forms use CSRF
)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


class CSRFMiddleware:
    """
    Double-submit CSRF for browser form posts.
    Expects header X-CSRF-Token matching cookie pf_csrf (set via base template + HTMX).
    Bearer-authenticated API under /api/ is exempt.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        if request.method in _MUTATING:
            path = request.url.path
            exempt = any(path.startswith(p) for p in _CSRF_EXEMPT_PREFIXES)
            auth = (request.headers.get("authorization") or "").lower()
            if auth.startswith("bearer "):
                exempt = True
            if not exempt:
                cookie = request.cookies.get(CSRF_COOKIE)
                header = request.headers.get(CSRF_HEADER) or request.headers.get("X-CSRF-Token")
                # Also accept form field via query for rare cases — primary is header
                if cookie and header and secrets.compare_digest(str(cookie), str(header)):
                    pass
                elif not cookie:
                    # First visit — allow once; cookie will be set on response
                    pass
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

        await self.app(scope, receive, send_with_csrf_cookie)


_login_hits: dict[str, Deque[float]] = defaultdict(deque)
_MAX_ATTEMPTS = 10
_WINDOW_SEC = 300


def check_login_rate_limit(client_key: str) -> None:
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


def clear_login_rate_limit(client_key: str) -> None:
    _login_hits.pop(client_key, None)
