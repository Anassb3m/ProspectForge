"""French professional email candidate generation (no external deps)."""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable
from urllib.parse import urlparse

# Role-based mailboxes common on French SME sites / public tenders
ROLE_LOCAL_PARTS = (
    "contact",
    "info",
    "commercial",
    "direction",
    "admin",
    "accueil",
    "hello",
    "office",
    "marchespublics",
    "marches",
    "tenders",
    "achats",
    "sales",
)


def strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_token(token: str) -> str:
    token = strip_accents(token.lower().strip())
    token = re.sub(r"[^a-z0-9]", "", token)
    return token


def parse_person_name(full_name: str) -> tuple[str, str]:
    """
    Split a French full name into (first, last).
    Heuristic: last token = family name, rest = given name(s).
    """
    parts = [p for p in re.split(r"\s+", full_name.strip()) if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], parts[0]
    return " ".join(parts[:-1]), parts[-1]


def extract_domain(website: str | None, email_hint: str | None = None) -> str | None:
    if email_hint and "@" in email_hint:
        return email_hint.split("@", 1)[1].lower().strip()
    if not website:
        return None
    url = website.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return None
    host = host.lower().removeprefix("www.")
    if not host or "." not in host:
        return None
    return host


def generate_email_candidates(
    domain: str,
    first_name: str | None = None,
    last_name: str | None = None,
    *,
    include_roles: bool = True,
    harvester_emails: Iterable[str] | None = None,
    max_candidates: int = 24,
) -> list[dict]:
    """
    Build ordered email candidates for a company domain.

    Each item: {email, pattern, priority} — lower priority = try first.
    """
    domain = domain.lower().strip()
    seen: set[str] = set()
    candidates: list[dict] = []

    def add(email_or_local: str, pattern: str, priority: int, *, full_email: bool = False) -> None:
        if full_email or pattern == "raw":
            email = email_or_local.lower().strip()
        else:
            # Keep dots/underscores in local part; only strip accents/case
            local = strip_accents(email_or_local.lower().strip())
            local = re.sub(r"[^a-z0-9._+\-]", "", local)
            if not local:
                return
            email = f"{local}@{domain}"
        if email in seen or "@" not in email:
            return
        seen.add(email)
        candidates.append({"email": email, "pattern": pattern, "priority": priority})

    # 1) Public emails from OSINT first
    for em in harvester_emails or []:
        em = (em or "").strip().lower()
        if em.endswith(f"@{domain}"):
            add(em, "raw", 0, full_email=True)

    # 2) Named person permutations (French B2B conventions)
    if first_name and last_name:
        f = normalize_token(first_name.split()[0])
        l = normalize_token(last_name)
        if f and l:
            named = [
                (f"{f}.{l}", "prenom.nom", 1),
                (f"{f[0]}.{l}", "p.nom", 2),
                (f"{f}{l}", "prenomnom", 3),
                (f"{l}.{f}", "nom.prenom", 4),
                (f"{f}_{l}", "prenom_nom", 5),
                (f"{f[0]}{l}", "pnom", 6),
                (f"{l}{f[0]}", "nomp", 7),
                (f"{l}", "nom", 8),
                (f"{f}", "prenom", 9),
            ]
            for local, pattern, prio in named:
                add(local, pattern, prio)

    # 3) Role-based
    if include_roles:
        for i, role in enumerate(ROLE_LOCAL_PARTS):
            add(role, f"role:{role}", 20 + i)

    candidates.sort(key=lambda c: c["priority"])
    return candidates[:max_candidates]


def linkedin_search_url(company_name: str, person_name: str | None = None) -> str:
    """Pre-filled Google/LinkedIn people search (manual last-mile)."""
    q = f'site:linkedin.com/in "{company_name}"'
    if person_name:
        q += f' "{person_name}"'
    from urllib.parse import quote_plus

    return f"https://www.google.com/search?q={quote_plus(q)}"
