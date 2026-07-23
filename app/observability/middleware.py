import uuid
import logging
from typing import Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

class RequestIDMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        
        # We could set the request_id in a context variable for structlog, but for now we just attach it
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.exception(f"Unhandled exception for request {request_id}: {exc}")
            raise
        
        response.headers["X-Request-ID"] = request_id
        return response
