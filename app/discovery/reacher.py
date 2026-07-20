"""Private Reacher client used only as a mailbox-verification layer."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
_FAILURES = 0
_OPEN_UNTIL = 0.0


def _address_id(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()[:12]


def _error_result(email: str, category: str, retryable: bool) -> dict[str, Any]:
    return {
        "email": email,
        "is_reachable": "unknown",
        "is_deliverable": None,
        "is_catch_all": None,
        "confidence": "error",
        "deliverability_state": "error",
        "error_code": category,
        "summary": {"provider": "reacher", "category": category, "retryable": retryable},
    }


async def check_email(email: str, base_url: str | None = None) -> dict[str, Any]:
    """Return a minimal normalized summary; never persist or log the raw provider body."""
    global _FAILURES, _OPEN_UNTIL
    settings = get_settings()
    base = (base_url or settings.reacher_url).rstrip("/")
    if not base or not settings.reacher_enabled:
        result = _error_result(email, "reacher_disabled", False)
        result["confidence"] = "indeterminate"
        result["deliverability_state"] = "indeterminate"
        return result
    if time.monotonic() < _OPEN_UNTIL:
        return _error_result(email, "circuit_open", True)

    url = f"{base}/v0/check_email"
    timeout = httpx.Timeout(settings.reacher_timeout_seconds)
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json={"to_email": email})
                response.raise_for_status()
                raw = response.json()
            _FAILURES = 0
            return _normalize(email, raw)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            if attempt == 0:
                await asyncio.sleep(0.2)
                continue
            category = "timeout" if isinstance(exc, httpx.TimeoutException) else "network"
            retryable = True
        except httpx.HTTPStatusError as exc:
            category = f"http_{exc.response.status_code}"
            retryable = exc.response.status_code >= 500 or exc.response.status_code == 429
        except (ValueError, TypeError):
            category = "invalid_response"
            retryable = False
        _FAILURES += 1
        if _FAILURES >= 3:
            _OPEN_UNTIL = time.monotonic() + 60
        logger.warning(
            "Reacher failure provider=reacher category=%s address_id=%s retryable=%s",
            category,
            _address_id(email),
            retryable,
        )
        return _error_result(email, category, retryable)
    return _error_result(email, "unknown", False)


def _normalize(email: str, raw: dict[str, Any]) -> dict[str, Any]:
    reachable = str(raw.get("is_reachable") or "unknown").lower()
    smtp = raw.get("smtp") if isinstance(raw.get("smtp"), dict) else {}
    mx = raw.get("mx") if isinstance(raw.get("mx"), dict) else {}
    syntax = raw.get("syntax") if isinstance(raw.get("syntax"), dict) else {}
    is_deliverable = smtp.get("is_deliverable")
    is_catch_all = smtp.get("is_catch_all")
    if is_catch_all:
        state = "catch_all"
    elif reachable == "safe" and is_deliverable is True:
        state = "deliverable"
    elif reachable == "risky":
        state = "risky"
    elif reachable == "invalid" or syntax.get("is_valid_syntax") is False:
        state = "invalid"
    else:
        state = "indeterminate"
    return {
        "email": email,
        "is_reachable": reachable,
        "is_deliverable": is_deliverable,
        "is_catch_all": is_catch_all,
        "confidence": state,
        "deliverability_state": state,
        "summary": {
            "provider": "reacher",
            "smtp_state": "deliverable" if is_deliverable is True else "not_deliverable" if is_deliverable is False else "unknown",
            "mx_state": "valid" if mx.get("accepts_mail") is True else "unknown",
            "syntax_valid": syntax.get("is_valid_syntax"),
        },
    }


async def check_emails_batch(
    emails: list[str],
    *,
    base_url: str | None = None,
    concurrency: int | None = None,
    stop_on_verified: bool = True,
) -> list[dict[str, Any]]:
    settings = get_settings()
    limit = max(1, min(concurrency or settings.contact_reacher_concurrency, 5))
    results: list[dict[str, Any]] = []
    # Small ordered windows preserve candidate priority while still bounding concurrency.
    for start in range(0, len(emails), limit):
        window = emails[start:start + limit]
        batch = await asyncio.gather(*(check_email(email, base_url=base_url) for email in window))
        results.extend(batch)
        if stop_on_verified and any(
            result.get("deliverability_state") == "deliverable" and not result.get("is_catch_all")
            for result in batch
        ):
            break
    return results


def pick_best_email(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Rank technical verdicts only; the caller must separately prove person ownership."""
    order = {
        "deliverable": 0, "verified": 0, "likely": 1, "catch_all": 3,
        "indeterminate": 4, "unknown": 4, "error": 5, "risky": 6, "invalid": 9,
    }
    usable = [result for result in results if result.get("confidence") not in {"invalid", "bounced"}]
    return min(usable, key=lambda result: order.get(str(result.get("confidence") or "unknown"), 7)) if usable else None
