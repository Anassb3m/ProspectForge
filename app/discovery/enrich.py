"""
Deep enrichment waterfall for a single company.

Order (free → precise):
1. Recherche Entreprises (dirigeants, siège, NAF)
2. Sirene INSEE (compliance diffusion + official fields)
3. Domain inference from company name patterns
4. Contact discovery (permutations + optional Reacher)
5. ICP / acquisition scoring
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
import httpx

from app.config import get_settings
from app.discovery.annuaire import enrich_from_annuaire
from app.discovery.contacts import discover_contacts
from app.discovery.emails import extract_domain
from app.discovery.icp import format_dirigeant_name, pick_best_dirigeant
from app.discovery.sirene import enrich_sirene

logger = logging.getLogger(__name__)


async def infer_website(company_name: str, siren: str | None = None) -> str | None:
    """
    Lightweight domain inference — tries common .fr patterns.
    Does NOT scrape LinkedIn. HEAD-check only.
    """
    if not company_name:
        return None
    base = company_name.lower()
    base = re.sub(r"\b(sas|sarl|sa|eurl|sci|sasu|snc|ste|société|societe)\b", "", base)
    base = re.sub(r"[^a-z0-9]+", "", base)
    if len(base) < 3:
        return None
    candidates = [
        f"https://www.{base}.fr",
        f"https://{base}.fr",
        f"https://www.{base}.com",
        f"https://{base}.com",
    ]
    async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
        for url in candidates:
            try:
                r = await client.head(url)
                if r.status_code < 400:
                    return str(r.url)
            except httpx.HTTPError:
                continue
    return None


async def deep_enrich(
    *,
    siren: str | None = None,
    siret: str | None = None,
    company_name: str | None = None,
    existing: dict[str, Any] | None = None,
    run_contacts: bool = True,
    verify_email: bool = False,
    infer_web: bool = True,
) -> dict[str, Any]:
    """
    Return a merged enrichment payload ready to apply onto a Prospect.
    """
    settings = get_settings()
    out: dict[str, Any] = dict(existing or {})
    out.setdefault("enrichment_log", [])

    # 1) Annuaire (dirigeants goldmine)
    if siren or out.get("siren"):
        s = siren or out.get("siren")
        try:
            ann = await enrich_from_annuaire(str(s))
            if ann:
                _merge(out, ann, prefer_new=("dirigeants", "decision_maker_name", "decision_maker_title", "city", "department", "address"))
                out["enrichment_log"].append("annuaire:ok")
            else:
                out["enrichment_log"].append("annuaire:miss")
        except Exception as exc:
            logger.warning("Annuaire enrich failed: %s", exc)
            out["enrichment_log"].append(f"annuaire:err:{exc}")

    # 2) Sirene compliance + official
    key = siret or out.get("siret") or siren or out.get("siren")
    if key and settings.insee_api_key:
        try:
            sir = await enrich_sirene(str(key))
            if sir is None:
                out["enrichment_log"].append("sirene:filtered_or_miss")
                out["sirene_blocked"] = True
            else:
                _merge(out, sir, prefer_new=("naf_code", "company_size", "diffusion_status", "siret", "siren"))
                out["enrichment_log"].append("sirene:ok")
                out["sirene_blocked"] = False
        except Exception as exc:
            logger.warning("Sirene enrich failed: %s", exc)
            out["enrichment_log"].append(f"sirene:err:{exc}")

    if not out.get("company_name") and company_name:
        out["company_name"] = company_name

    # 3) Best dirigeant → DM fields
    best = pick_best_dirigeant(out.get("dirigeants"))
    if best and not out.get("decision_maker_name"):
        out["decision_maker_name"] = format_dirigeant_name(best)
        out["decision_maker_title"] = best.get("qualite")

    # 4) Website inference
    if infer_web and not out.get("website") and out.get("company_name"):
        web = await infer_website(out["company_name"], out.get("siren"))
        if web:
            out["website"] = web
            out["enrichment_log"].append("website:inferred")

    # 5) Contact waterfall using dirigeant name
    if run_contacts and not out.get("email"):
        domain = extract_domain(out.get("website"))
        person = out.get("decision_maker_name")
        if domain or person:
            try:
                contacts = await discover_contacts(
                    website=out.get("website"),
                    domain=domain,
                    person_name=person,
                    run_harvester=settings.harvester_enabled,
                    verify=verify_email and settings.reacher_enabled,
                )
                out["contact_candidates"] = contacts.get("candidates")
                out["contact_source"] = contacts.get("contact_source")
                out["contact_confidence"] = contacts.get("contact_confidence")
                out["needs_manual_review"] = contacts.get("needs_manual_review", True)
                if contacts.get("best_email") and contacts.get("usable_for_send"):
                    out["email"] = contacts["best_email"]
                out["enrichment_log"].append("contacts:ok")
            except Exception as exc:
                logger.warning("Contact discovery failed: %s", exc)
                out["needs_manual_review"] = True
                out["enrichment_log"].append(f"contacts:err:{exc}")
        else:
            out["needs_manual_review"] = True
            out["contact_confidence"] = "needs_review"

    out["last_enriched_at"] = datetime.now(timezone.utc).isoformat()
    return out


def _merge(base: dict, new: dict, prefer_new: tuple[str, ...] = ()) -> None:
    for k, v in new.items():
        if v is None or v == "" or v == []:
            continue
        if k in prefer_new or not base.get(k):
            base[k] = v


def _loaded_events(prospect) -> list:
    """Return outreach_events only if already loaded — never trigger lazy IO."""
    try:
        from sqlalchemy import inspect as sa_inspect

        state = sa_inspect(prospect)
        if "outreach_events" in state.dict:
            return list(state.dict["outreach_events"] or [])
    except Exception:
        pass
    return []


def apply_enrichment_to_prospect(prospect, data: dict[str, Any]) -> None:
    """Mutate Prospect with enrichment dict + V3 opportunity score + readiness."""
    field_map = (
        "company_name", "sector", "company_size", "naf_code", "siren", "siret",
        "website", "phone", "email", "decision_maker_name", "decision_maker_title",
        "dirigeants", "city", "department", "region", "diffusion_status",
        "contact_source", "contact_confidence", "contact_candidates",
        "needs_manual_review", "contact_discovery_state", "evidence_json",
        "award_history", "signal_type", "signal_details",
    )
    for f in field_map:
        if f in data and data[f] is not None:
            if hasattr(prospect, f):
                setattr(prospect, f, data[f])

    # Merge evidence list (deduped fingerprints)
    if data.get("evidence"):
        from app.commercial import merge_evidence_json as _merge_ev

        prospect.evidence_json = _merge_ev(prospect.evidence_json, data["evidence"])

    # Guessed emails are never "verified"
    conf = (prospect.contact_confidence or "").lower()
    if prospect.email and conf in ("", "none", "unverified") and not prospect.contact_discovery_state:
        prospect.contact_discovery_state = "guessed"
        prospect.contact_confidence = "domain_and_pattern_only"

    prospect.last_enriched_at = datetime.now(timezone.utc)
