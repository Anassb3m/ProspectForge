"""INSEE Sirene API enrichment + compliance diffusion gate."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import get_settings
from app.discovery.naf import map_naf_to_sector, map_tranche_effectifs, normalize_naf

logger = logging.getLogger(__name__)

# Current public Sirene API (INSEE portail)
SIRENE_SIRET_URL = "https://api.insee.fr/api-sirene/3.11/siret/{siret}"
SIRENE_SIREN_URL = "https://api.insee.fr/api-sirene/3.11/siren/{siren}"
# Legacy header name from older docs; also try Authorization Bearer if needed
SIRENE_KEY_HEADER = "X-INSEE-Api-Key-Integration"


class SireneError(Exception):
    pass


async def enrich_sirene(siret: str, api_key: str | None = None) -> dict[str, Any] | None:
    """
    Fetch establishment + legal unit from Sirene.

    Returns None when:
    - partial diffusion (GDPR hard filter — do not prospect)
    - establishment not administratively active
    - API error / missing key
    """
    settings = get_settings()
    api_key = api_key or settings.insee_api_key
    if not api_key:
        logger.warning("Sirene skipped — INSEE_API_KEY not configured")
        return None

    siret = re.sub(r"\D", "", siret or "")
    if len(siret) not in (9, 14):
        return None

    # Accept SIREN (9) by looking up first establishment later via siren endpoint
    if len(siret) == 9:
        return await _enrich_by_siren(siret, api_key)

    url = SIRENE_SIRET_URL.format(siret=siret)
    headers = {SIRENE_KEY_HEADER: api_key, "Accept": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 404:
                return None
            if r.status_code == 401:
                logger.error("Sirene auth failed — check INSEE_API_KEY")
                return None
            if r.status_code == 429:
                logger.warning("Sirene rate limited")
                raise SireneError("rate_limited")
            r.raise_for_status()
            payload = r.json()
    except httpx.HTTPError as exc:
        logger.warning("Sirene request failed for %s: %s", siret, exc)
        return None

    return _parse_siret_response(payload, siret)


async def _enrich_by_siren(siren: str, api_key: str) -> dict[str, Any] | None:
    url = SIRENE_SIREN_URL.format(siren=siren)
    headers = {SIRENE_KEY_HEADER: api_key, "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=headers)
            if r.status_code != 200:
                return None
            data = r.json()
    except httpx.HTTPError as exc:
        logger.warning("Sirene SIREN lookup failed for %s: %s", siren, exc)
        return None

    # Unite legale path
    ul = data.get("uniteLegale") or data.get("periodesUniteLegale", [{}])
    if isinstance(ul, list):
        ul = ul[0] if ul else {}
    # Some API versions nest differently
    if "uniteLegale" not in data and "periodesUniteLegale" in data:
        periods = data.get("periodesUniteLegale") or []
        ul = {**(data if isinstance(data, dict) else {}), **(periods[0] if periods else {})}

    diffusion = (
        data.get("statutDiffusionUniteLegale")
        or (ul.get("statutDiffusionUniteLegale") if isinstance(ul, dict) else None)
    )
    # O = open/diffusible; P/N = partial/non-diffusible (do not prospect)
    if diffusion and (
        str(diffusion).upper() in ("P", "N") or "partiel" in str(diffusion).lower()
    ):
        logger.info("Skipping non-diffusible SIREN %s (status=%s)", siren, diffusion)
        return None

    # Without a SIRET we still return legal-unit level data
    name = None
    naf = None
    tranche = None
    if isinstance(ul, dict):
        name = ul.get("denominationUniteLegale") or ul.get("nomUniteLegale")
        naf = ul.get("activitePrincipaleUniteLegale")
        tranche = ul.get("trancheEffectifsUniteLegale")
    name = name or data.get("denominationUniteLegale")
    naf = naf or data.get("activitePrincipaleUniteLegale")
    tranche = tranche or data.get("trancheEffectifsUniteLegale")

    naf_n = normalize_naf(naf)
    return {
        "siren": siren,
        "siret": None,
        "company_name": name,
        "naf_code": naf_n,
        "sector": map_naf_to_sector(naf_n),
        "company_size": map_tranche_effectifs(tranche),
        "tranche_effectifs": tranche,
        "website": None,
        "diffusion_status": diffusion or "diffusible",
        "phone": None,
        "raw": data,
    }


def _parse_siret_response(payload: dict, siret: str) -> dict[str, Any] | None:
    """Normalize across Sirene API response shapes."""
    etab = payload.get("etablissement") or payload
    ul = etab.get("uniteLegale") or {}
    periodes = etab.get("periodesEtablissement") or []
    periode = periodes[0] if periodes else {}

    diffusion_ul = ul.get("statutDiffusionUniteLegale") or etab.get("statutDiffusionUniteLegale")
    diffusion_et = etab.get("statutDiffusionEtablissement")
    for d in (diffusion_ul, diffusion_et):
        if not d:
            continue
        ds = str(d).upper()
        if ds in ("P", "N") or "partiel" in str(d).lower():
            logger.info("Skipping non-diffusible SIRET %s (status=%s)", siret, d)
            return None

    etat = (
        periode.get("etatAdministratifEtablissement")
        or etab.get("etatAdministratifEtablissement")
        or ul.get("etatAdministratifUniteLegale")
    )
    if etat and etat != "A":
        logger.info("Skipping inactive establishment SIRET %s (etat=%s)", siret, etat)
        return None

    name = (
        periode.get("denominationUsuelleEtablissement")
        or ul.get("denominationUniteLegale")
        or ul.get("nomUniteLegale")
        or etab.get("denominationUsuelleEtablissement")
    )
    # Fallback: first name + last for persons
    if not name:
        prenom = ul.get("prenom1UniteLegale") or ""
        nom = ul.get("nomUniteLegale") or ""
        name = f"{prenom} {nom}".strip() or None

    naf = (
        periode.get("activitePrincipaleEtablissement")
        or ul.get("activitePrincipaleUniteLegale")
        or etab.get("activitePrincipaleEtablissement")
    )
    tranche = (
        etab.get("trancheEffectifsEtablissement")
        or ul.get("trancheEffectifsUniteLegale")
        or periode.get("trancheEffectifsEtablissement")
    )
    website = etab.get("siteWeb") or ul.get("siteWeb")
    phone = None
    # Address phone rarely present; leave None

    siren = siret[:9]
    naf_n = normalize_naf(naf)

    return {
        "siren": siren,
        "siret": siret,
        "company_name": name,
        "naf_code": naf_n,
        "sector": map_naf_to_sector(naf_n),
        "company_size": map_tranche_effectifs(tranche),
        "tranche_effectifs": tranche,
        "website": website,
        "diffusion_status": diffusion_ul or diffusion_et or "diffusible",
        "phone": phone,
        "raw": payload,
    }


# late import for siret cleaning without top-level re dependency clutter
import re  # noqa: E402
