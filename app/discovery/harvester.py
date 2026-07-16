"""Optional theHarvester wrapper — OSINT emails for a company domain."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
import tempfile
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


async def harvest_emails(domain: str, *, timeout: int = 90) -> list[str]:
    """
    Run theHarvester against domain if available and enabled.
    Returns unique emails on that domain. Never raises — empty on failure.
    """
    settings = get_settings()
    if not settings.harvester_enabled:
        return []

    domain = domain.lower().strip()
    if not domain:
        return []

    binary = shutil.which("theHarvester") or shutil.which("theharvester")
    if not binary:
        # Try python module
        python_mod = True
    else:
        python_mod = False

    with tempfile.TemporaryDirectory(prefix="pf_harvest_") as tmp:
        out_base = Path(tmp) / "result"
        try:
            if binary:
                cmd = [
                    binary,
                    "-d",
                    domain,
                    "-b",
                    settings.harvester_sources,
                    "-f",
                    str(out_base),
                    "-l",
                    "50",
                ]
            else:
                cmd = [
                    "python",
                    "-m",
                    "theHarvester",
                    "-d",
                    domain,
                    "-b",
                    settings.harvester_sources,
                    "-f",
                    str(out_base),
                    "-l",
                    "50",
                ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                logger.warning("theHarvester timed out for %s", domain)
                return []

            emails = _collect_emails(out_base, stdout.decode(errors="ignore"), domain)
            if not emails and stderr:
                logger.debug("theHarvester stderr: %s", stderr.decode(errors="ignore")[:500])
            return emails
        except FileNotFoundError:
            logger.debug("theHarvester not installed — skipping OSINT for %s", domain)
            return []
        except Exception as exc:
            logger.warning("theHarvester failed for %s: %s", domain, exc)
            return []


def _collect_emails(out_base: Path, stdout: str, domain: str) -> list[str]:
    found: set[str] = set()

    # JSON output variants
    for path in (
        Path(f"{out_base}.json"),
        Path(str(out_base) + ".json"),
        out_base.with_suffix(".json"),
    ):
        if path.exists():
            try:
                data = json.loads(path.read_text())
                for key in ("emails", "hosts", "interesting_urls"):
                    vals = data.get(key) or []
                    if isinstance(vals, list):
                        for v in vals:
                            if isinstance(v, str) and "@" in v:
                                found.add(v.lower())
            except Exception:
                pass

    for m in EMAIL_RE.findall(stdout):
        found.add(m.lower())

    # Prefer same domain
    same = sorted(e for e in found if e.endswith(f"@{domain}"))
    others = sorted(e for e in found if not e.endswith(f"@{domain}"))
    return same + others
