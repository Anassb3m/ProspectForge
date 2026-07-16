"""Reacher (check-if-email-exists) HTTP client — local SMTP verification."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


async def check_email(email: str, base_url: str | None = None) -> dict[str, Any]:
    """
    Verify a single email via Reacher backend.

    Returns normalized dict:
      email, is_reachable, is_deliverable, is_catch_all, confidence, raw
    confidence: verified | likely | invalid | unknown
    """
    settings = get_settings()
    base = (base_url or settings.reacher_url).rstrip("/")
    if not base or not settings.reacher_enabled:
        return {
            "email": email,
            "is_reachable": "unknown",
            "is_deliverable": None,
            "is_catch_all": None,
            "confidence": "unknown",
            "raw": {"skipped": True, "reason": "reacher_disabled"},
        }

    url = f"{base}/v0/check_email"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, json={"to_email": email})
            r.raise_for_status()
            raw = r.json()
    except httpx.HTTPError as exc:
        logger.warning("Reacher check failed for %s: %s", email, exc)
        return {
            "email": email,
            "is_reachable": "unknown",
            "is_deliverable": None,
            "is_catch_all": None,
            "confidence": "unknown",
            "raw": {"error": str(exc)},
        }

    return _normalize(email, raw)


def _normalize(email: str, raw: dict) -> dict[str, Any]:
    reachable = (raw.get("is_reachable") or "unknown").lower()
    smtp = raw.get("smtp") or {}
    is_deliverable = smtp.get("is_deliverable")
    is_catch_all = smtp.get("is_catch_all")

    # V3: never treat catch-all as fully verified
    if is_catch_all:
        confidence = "catch_all"
    elif reachable == "safe" and is_deliverable is True:
        confidence = "deliverable"
    elif reachable == "safe":
        confidence = "deliverable"
    elif reachable == "risky":
        confidence = "risky"
    elif reachable == "invalid":
        confidence = "invalid"
    else:
        confidence = "indeterminate"

    return {
        "email": email,
        "is_reachable": reachable,
        "is_deliverable": is_deliverable,
        "is_catch_all": is_catch_all,
        "confidence": confidence,
        "verification_state": confidence,
        "raw": raw,
    }


async def check_emails_batch(
    emails: list[str],
    *,
    base_url: str | None = None,
    concurrency: int = 3,
    stop_on_verified: bool = True,
) -> list[dict[str, Any]]:
    """
    Verify candidates with limited concurrency.
    Stops early when a verified (safe) address is found if stop_on_verified.
    """
    results: list[dict[str, Any]] = []
    sem = asyncio.Semaphore(concurrency)

    async def one(em: str) -> dict[str, Any]:
        async with sem:
            return await check_email(em, base_url=base_url)

    for em in emails:
        result = await one(em)
        results.append(result)
        if stop_on_verified and result.get("confidence") == "verified":
            break
    return results


def pick_best_email(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Prefer deliverable non-catch-all; never auto-pick invalid/bounced."""
    order = {
        "deliverable": 0,
        "verified": 0,
        "likely": 1,
        "catch_all": 3,
        "indeterminate": 4,
        "unknown": 4,
        "risky": 5,
        "invalid": 9,
    }
    usable = [r for r in results if r.get("confidence") not in ("invalid", "bounced")]
    if not usable:
        return None
    usable.sort(key=lambda r: order.get(r.get("confidence") or "unknown", 5))
    return usable[0]
