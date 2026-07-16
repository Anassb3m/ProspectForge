"""
Recherche Entreprises — market-play driven company discovery (V3).

No longer defaults to Section J / IT SMEs.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import httpx

from app.discovery.icp import format_dirigeant_name, pick_best_dirigeant
from app.discovery.naf import is_it_cyber_naf, map_naf_to_sector, map_tranche_effectifs, normalize_naf
from app.plays import DEFAULT_PLAY_CODE, get_play

logger = logging.getLogger(__name__)
BASE = "https://recherche-entreprises.api.gouv.fr"
SME_TRANCHES = "11,12,21,22,31,32"


async def search_companies(
    *,
    q: str = "",
    activite_principale: str | None = None,
    section_activite_principale: str | None = None,
    tranche_effectif_salarie: str = SME_TRANCHES,
    page: int = 1,
    per_page: int = 25,
    etat_administratif: str = "A",
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "page": page,
        "per_page": min(per_page, 25),
        "etat_administratif": etat_administratif,
    }
    if q:
        params["q"] = q
    if activite_principale:
        params["activite_principale"] = activite_principale
    if section_activite_principale:
        params["section_activite_principale"] = section_activite_principale
    if tranche_effectif_salarie:
        params["tranche_effectif_salarie"] = tranche_effectif_salarie
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(f"{BASE}/search", params=params)
        r.raise_for_status()
        return r.json()


async def get_by_siren(siren: str) -> dict[str, Any] | None:
    siren = "".join(c for c in siren if c.isdigit())
    if len(siren) != 9:
        return None
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(f"{BASE}/search", params={"q": siren, "per_page": 1})
        if r.status_code != 200:
            return None
        results = r.json().get("results") or []
        for item in results:
            if item.get("siren") == siren:
                return item
        return results[0] if results else None


def normalize_company(item: dict[str, Any], *, signal_hint: str = "REGISTRY_FIELD") -> dict[str, Any]:
    siege = item.get("siege") or {}
    naf = normalize_naf(item.get("activite_principale") or siege.get("activite_principale"))
    tranche = item.get("tranche_effectif_salarie") or siege.get("tranche_effectif_salarie")
    dirigeants_raw = item.get("dirigeants") or []
    dirigeants = []
    for d in dirigeants_raw:
        if not isinstance(d, dict):
            continue
        dirigeants.append({
            "nom": d.get("nom"),
            "prenoms": d.get("prenoms"),
            "qualite": d.get("qualite"),
            "type_dirigeant": d.get("type_dirigeant"),
            "denomination": d.get("denomination"),
        })
    best = pick_best_dirigeant(dirigeants)
    dm_name = format_dirigeant_name(best) if best else None
    dm_title = (best.get("qualite") if best else None) or None
    siret = siege.get("siret")
    return {
        "siren": item.get("siren"),
        "siret": siret,
        "company_name": item.get("nom_complet") or item.get("nom_raison_sociale") or item.get("sigle"),
        "naf_code": naf,
        "sector": map_naf_to_sector(naf),
        "company_size": map_tranche_effectifs(tranche),
        "tranche_effectifs": tranche,
        "dirigeants": dirigeants,
        "decision_maker_name": dm_name,
        "decision_maker_title": dm_title,
        "city": siege.get("libelle_commune") or siege.get("commune"),
        "department": (siege.get("departement") or "")[:3] or None,
        "region": siege.get("region"),
        "address": siege.get("adresse") or siege.get("geo_adresse"),
        "website": None,
        "phone": None,
        "diffusion_status": "diffusible",
        "signal_hint": signal_hint,
        "nombre_etablissements": item.get("nombre_etablissements_ouverts"),
    }


def _passes_play_filter(n: dict[str, Any], play: dict) -> bool:
    naf = normalize_naf(n.get("naf_code"))
    if not naf:
        return False
    if is_it_cyber_naf(naf):
        return False
    excluded = {c.replace(".", "").upper() for c in (play.get("excluded_naf_codes") or [])}
    excl_pref = play.get("excluded_naf_prefixes") or []
    if naf in excluded or naf[:2] in excl_pref:
        return False
    targets = {c.replace(".", "").upper() for c in (play.get("target_naf_codes") or [])}
    prefs = play.get("target_naf_prefixes") or []
    if targets or prefs:
        if naf in targets or naf[:2] in prefs:
            return True
        return False
    return True


async def discover_companies_for_play(
    play_code: str | None = None,
    *,
    max_results: int = 80,
    pages_per_query: int = 3,
) -> list[dict[str, Any]]:
    """Play-driven registry hunt — structural candidates, not contact-ready."""
    play = get_play(play_code or DEFAULT_PLAY_CODE)
    queries = play.get("registry_queries") or ["maintenance", "installation technique"]
    naf_codes = play.get("target_naf_codes") or []
    by_siren: dict[str, dict] = {}

    def _ingest(item: dict, *, force: bool = False) -> None:
        n = normalize_company(item, signal_hint="REGISTRY_FIELD")
        if not n.get("siren"):
            return
        if not force and not _passes_play_filter(n, play):
            return
        if is_it_cyber_naf(n.get("naf_code")):
            return
        if n["siren"] not in by_siren:
            # Structural evidence only — no automatic pain
            n["evidence"] = [
                {
                    "category": "structural_fit",
                    "signal_type": "REGISTRY_ACTIVITY",
                    "label": f"Registry NAF {n.get('naf_code')}",
                    "evidence_text": f"{n.get('company_name')} — {n.get('sector')} — size {n.get('company_size')}",
                    "source_type": "annuaire",
                    "confidence": 70,
                    "strength": 45,
                }
            ]
            if n.get("nombre_etablissements") and int(n["nombre_etablissements"] or 0) >= 2:
                n["evidence"].append({
                    "category": "structural_fit",
                    "signal_type": "MULTI_SITE_OPERATIONS",
                    "label": "Multiple establishments",
                    "evidence_text": f"{n['nombre_etablissements']} establishments ouverts",
                    "source_type": "annuaire",
                    "confidence": 65,
                    "strength": 55,
                })
            by_siren[n["siren"]] = n

    # 1) Target NAF codes first
    for naf in naf_codes:
        if len(by_siren) >= max_results:
            break
        for page in range(1, pages_per_query + 1):
            if len(by_siren) >= max_results:
                break
            try:
                # API expects dotted NAF sometimes
                naf_q = naf if "." in naf else f"{naf[:2]}.{naf[2:]}" if len(naf) >= 4 else naf
                data = await search_companies(
                    q="",
                    activite_principale=naf_q,
                    section_activite_principale=None,
                    page=page,
                    per_page=25,
                )
            except httpx.HTTPError as exc:
                logger.warning("Annuaire NAF %s failed: %s", naf, exc)
                break
            for item in data.get("results") or []:
                _ingest(item, force=True)
            if page >= (data.get("total_pages") or 1):
                break

    # 2) Keyword queries (field service language)
    for q in queries:
        if len(by_siren) >= max_results:
            break
        try:
            data = await search_companies(q=q, section_activite_principale=None, page=1, per_page=25)
        except httpx.HTTPError as exc:
            logger.warning("Annuaire query %r failed: %s", q, exc)
            continue
        for item in data.get("results") or []:
            _ingest(item)

    results = list(by_siren.values())

    def rank_key(c: dict) -> tuple:
        naf = normalize_naf(c.get("naf_code")) or ""
        core = 0 if naf[:2] in (play.get("target_naf_prefixes") or []) else 1
        size = 0 if c.get("company_size") in ("11-50", "51-200") else 1
        dm = 0 if c.get("decision_maker_name") else 1
        return (core, size, dm)

    results.sort(key=rank_key)
    results = results[:max_results]
    logger.info("Annuaire play=%s: %d companies", play.get("code"), len(results))
    return results


# Back-compat alias — redirects to field play discovery
async def discover_it_smes(**kwargs) -> list[dict[str, Any]]:
    logger.warning("discover_it_smes is deprecated; using discover_companies_for_play")
    return await discover_companies_for_play(**kwargs)


async def enrich_from_annuaire(siren: str) -> dict[str, Any] | None:
    item = await get_by_siren(siren)
    if not item:
        return None
    return normalize_company(item)


def linkedin_people_url(company: str, person: str | None = None, title: str | None = None) -> str:
    parts = [f'"{company}"']
    if person:
        parts.append(f'"{person}"')
    if title:
        parts.append(title)
    q = "site:linkedin.com/in " + " ".join(parts)
    return f"https://www.google.com/search?q={quote(q)}"
