"""
Recherche Entreprises API (api.gouv.fr) — free, no key.

Richer than raw Sirene for acquisition:
- dirigeants (Président, DG) with names → email permutations
- siège address, NAF, effectifs
- full-text + faceted search (section J = information/communication)
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import httpx

from app.discovery.icp import format_dirigeant_name, pick_best_dirigeant
from app.discovery.naf import map_naf_to_sector, map_tranche_effectifs, normalize_naf

logger = logging.getLogger(__name__)

BASE = "https://recherche-entreprises.api.gouv.fr"

# Mid-market headcount codes (INSEE tranches)
SME_TRANCHES = "11,12,21,22,31,32"  # 10 → 199 approx

# Section J = Information et communication (IT/digital core)
SECTION_IT = "J"


async def search_companies(
    *,
    q: str = "",
    activite_principale: str | None = None,
    section_activite_principale: str | None = SECTION_IT,
    tranche_effectif_salarie: str = SME_TRANCHES,
    code_postal: str | None = None,
    page: int = 1,
    per_page: int = 25,
    etat_administratif: str = "A",
) -> dict[str, Any]:
    """Search the national company directory."""
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
    if code_postal:
        params["code_postal"] = code_postal

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


def normalize_company(item: dict[str, Any], *, signal_hint: str = "REGISTRY_IT") -> dict[str, Any]:
    """Map annuaire payload → internal enrichment dict."""
    siege = item.get("siege") or {}
    naf = normalize_naf(item.get("activite_principale") or siege.get("activite_principale"))
    tranche = item.get("tranche_effectif_salarie") or siege.get("tranche_effectif_salarie")
    dirigeants_raw = item.get("dirigeants") or []
    dirigeants = []
    for d in dirigeants_raw:
        if not isinstance(d, dict):
            continue
        dirigeants.append(
            {
                "nom": d.get("nom"),
                "prenoms": d.get("prenoms"),
                "qualite": d.get("qualite"),
                "type_dirigeant": d.get("type_dirigeant"),
                "denomination": d.get("denomination"),
            }
        )

    best = pick_best_dirigeant(dirigeants)
    dm_name = format_dirigeant_name(best) if best else None
    dm_title = (best.get("qualite") if best else None) or None

    siret = siege.get("siret")
    city = siege.get("libelle_commune") or siege.get("commune")
    dept = (siege.get("departement") or "")[:3] or None
    region = siege.get("region")
    # Website rarely in API; leave None — domain inference elsewhere

    return {
        "siren": item.get("siren"),
        "siret": siret,
        "company_name": item.get("nom_complet")
        or item.get("nom_raison_sociale")
        or item.get("sigle"),
        "naf_code": naf,
        "sector": map_naf_to_sector(naf),
        "company_size": map_tranche_effectifs(tranche),
        "tranche_effectifs": tranche,
        "dirigeants": dirigeants,
        "decision_maker_name": dm_name,
        "decision_maker_title": dm_title,
        "city": city,
        "department": dept,
        "region": region,
        "address": siege.get("adresse") or siege.get("geo_adresse"),
        "website": None,
        "phone": None,
        "diffusion_status": "diffusible",
        "signal_hint": signal_hint,
        "nombre_etablissements": item.get("nombre_etablissements_ouverts"),
        "raw_annuaire": {"siren": item.get("siren"), "complements": item.get("complements")},
    }


# Mega brands / non-ICP noise in section J
_BLOCKED_NAME_FRAGMENTS = (
    "sfr ", "orange ", "bouygues telecom", "free mobile", "nrj ",
    "la poste", "edf ", "engie", "sncf", "air france", "totalenergies",
    "microsoft", "amazon", "google", "ibm france", "capgemini",
)


def _is_icp_candidate(n: dict[str, Any]) -> bool:
    name = (n.get("company_name") or "").lower()
    if any(b in name for b in _BLOCKED_NAME_FRAGMENTS):
        return False
    # Prefer mid-market; allow 1-10 for pure software boutiques
    size = n.get("company_size")
    if size == "200+":
        return False
    naf = (n.get("naf_code") or "")[:2]
    # Core software/IT/data; drop pure broadcasting (60), cinema (59) unless cyber keywords
    if naf in ("62", "63", "58", "70", "71", "61"):
        return True
    return False


async def discover_it_smes(
    *,
    queries: list[str] | None = None,
    naf_codes: list[str] | None = None,
    max_results: int = 80,
    pages_per_query: int = 3,
) -> list[dict[str, Any]]:
    """
    Multi-query hunt for Elevya ICP companies via open directory.
    Precision-first: core NAF → intent keywords → broad section J fill.
    Dedupes by SIREN.
    """
    queries = queries or [
        "logiciel",
        "cybersécurité",
        "infogérance",
        "développement informatique",
        "hébergement données",
        "conseil systèmes d'information",
        "transformation numérique",
        "cloud computing",
        "ssii",
        "esn ",
    ]
    naf_codes = naf_codes or [
        "62.01Z", "62.02A", "62.02B", "62.03Z", "62.09Z", "63.11Z", "63.12Z",
    ]

    by_siren: dict[str, dict] = {}

    def _ingest(item: dict, *, force: bool = False) -> None:
        n = normalize_company(item, signal_hint="REGISTRY_IT")
        if not n.get("siren"):
            return
        if not force and not _is_icp_candidate(n):
            return
        if n["siren"] not in by_siren:
            by_siren[n["siren"]] = n

    # 1) Core NAF precision (highest quality for Elevya)
    for naf in naf_codes:
        if len(by_siren) >= max_results:
            break
        for page in range(1, pages_per_query + 1):
            if len(by_siren) >= max_results:
                break
            try:
                data = await search_companies(
                    q="",
                    activite_principale=naf,
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

    # 2) Keyword queries for intent language
    for q in queries:
        if len(by_siren) >= max_results:
            break
        try:
            data = await search_companies(
                q=q,
                section_activite_principale=SECTION_IT,
                page=1,
                per_page=25,
            )
        except httpx.HTTPError as exc:
            logger.warning("Annuaire query %r failed: %s", q, exc)
            continue
        for item in data.get("results") or []:
            _ingest(item)

    # 3) Section J fill only if still under cap
    for page in range(1, min(2, pages_per_query) + 1):
        if len(by_siren) >= max_results:
            break
        try:
            data = await search_companies(
                q="",
                section_activite_principale=SECTION_IT,
                page=page,
                per_page=25,
            )
        except httpx.HTTPError as exc:
            logger.warning("Annuaire section J search failed: %s", exc)
            break
        for item in data.get("results") or []:
            _ingest(item)

    # Rank: core NAF first, then size sweet spot, then has dirigeant
    results = list(by_siren.values())

    def rank_key(c: dict) -> tuple:
        naf = c.get("naf_code") or ""
        core = 0 if naf[:4] in ("6201", "6202", "6203", "6209", "6311", "6312") else 1
        size = 0 if c.get("company_size") in ("11-50", "51-200") else 1
        dm = 0 if c.get("decision_maker_name") else 1
        return (core, size, dm)

    results.sort(key=rank_key)
    results = results[:max_results]
    logger.info("Annuaire discovery: %d unique ICP companies", len(results))
    return results


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
