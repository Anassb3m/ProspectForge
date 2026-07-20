"""Bounded DNS/MX validation with short-lived in-process caching."""

from __future__ import annotations

import asyncio
import socket
import time
from dataclasses import dataclass

from app.contact_intelligence.extractors import normalize_email


@dataclass(frozen=True, slots=True)
class MXResult:
    state: str
    has_mx: bool
    null_mx: bool = False
    error: str | None = None


_CACHE: dict[str, tuple[float, MXResult]] = {}


async def validate_email_domain(email: str, *, ttl_seconds: int = 86400) -> MXResult:
    normalized = normalize_email(email)
    if not normalized:
        return MXResult("invalid_syntax", False)
    domain = normalized.rsplit("@", 1)[1]
    cached = _CACHE.get(domain)
    now = time.monotonic()
    if cached and now - cached[0] < ttl_seconds:
        return cached[1]
    try:
        import dns.asyncresolver  # type: ignore[import-not-found]

        answer = await dns.asyncresolver.resolve(domain, "MX", lifetime=5.0)
        exchanges = [str(record.exchange).rstrip(".") for record in answer]
        result = MXResult(
            "null_mx" if exchanges == [""] else "mx_valid",
            has_mx=bool(exchanges and exchanges != [""]),
            null_mx=exchanges == [""],
        )
    except ImportError:
        try:
            await asyncio.wait_for(asyncio.to_thread(socket.getaddrinfo, domain, 25), timeout=5.0)
            result = MXResult("domain_resolves_mx_unchecked", True)
        except (OSError, TimeoutError):
            result = MXResult("dns_error", False, error="resolution_failed")
    except Exception as exc:
        name = exc.__class__.__name__.lower()
        permanent = any(marker in name for marker in ("nxdomain", "noanswer"))
        result = MXResult("no_mx" if permanent else "temporary_error", False, error=name[:60])
    _CACHE[domain] = (now, result)
    return result
