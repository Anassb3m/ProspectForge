"""DECP discovery: download consolidated Parquet, filter Elevya-relevant awards."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import polars as pl

from app.config import get_settings

logger = logging.getLogger(__name__)

# data.gouv.fr dataset for ColinMaudry-style consolidated DECP (tabular)
DECP_DATASET_SLUG = (
    "donnees-essentielles-de-la-commande-publique-consolidees-format-tabulaire"
)
DATA_GOUV_DATASET_API = f"https://www.data.gouv.fr/api/1/datasets/{DECP_DATASET_SLUG}/"

# CPV prefixes: IT services, software packages, programming
DEFAULT_CPV_PREFIXES = ("72", "48", "62")

# Keywords in marché object (French public IT / digital / cyber)
DEFAULT_KEYWORDS = (
    "cybersécurité",
    "cybersecurite",
    "sécurité informatique",
    "securite informatique",
    "développement logiciel",
    "developpement logiciel",
    "système d'information",
    "systeme d'information",
    "systèmes d'information",
    "transformation numérique",
    "transformation numerique",
    "cloud",
    "data",
    "infogérance",
    "infogerance",
    "hébergement",
    "hebergement",
    "maintenance applicative",
    "tierce maintenance",
    "logiciel",
    "si ",
    " dsi",
    "réseau informatique",
    "reseau informatique",
)

# Column name aliases across DECP consolidations
COL_ALIASES = {
    "dateAttribution": [
        "dateAttribution",
        "dateNotification",
        "dateattribution",
        "datenotification",
        "date_notification",
        "date_attribution",
    ],
    "codeCPV": ["codeCPV", "codecpv", "code_cpv", "cpv", "CPV"],
    "objetMarche": [
        "objetMarche",
        "objet",
        "objetmarche",
        "objet_marche",
        "intitule",
        "titre",
    ],
    "titulaire_siret": [
        "titulaire_siret",
        "titulaireSiret",
        "siretTitulaire",
        "siret_titulaire",
        "titulaire_id",
        "idTitulaire",
    ],
    "titulaire_nom": [
        "titulaire_nom",
        "titulaireNom",
        "nomTitulaire",
        "nom_titulaire",
        "titulaire",
    ],
    "montant": ["montant", "montantHT", "montant_ht", "amount"],
    "acheteur_nom": [
        "acheteur_nom",
        "acheteurNom",
        "nomAcheteur",
        "nom_acheteur",
        "acheteur",
    ],
    "id": ["id", "idMarche", "id_marche", "uid"],
}


def _resolve_col(df: pl.DataFrame, logical: str) -> str | None:
    cols = {c.lower(): c for c in df.columns}
    for alias in COL_ALIASES.get(logical, [logical]):
        if alias in df.columns:
            return alias
        if alias.lower() in cols:
            return cols[alias.lower()]
    return None


def _normalize_columns(df: pl.DataFrame) -> pl.DataFrame:
    """Rename known columns to canonical names used by the filter."""
    rename: dict[str, str] = {}
    for logical in COL_ALIASES:
        actual = _resolve_col(df, logical)
        if actual and actual != logical:
            rename[actual] = logical
        elif actual == logical:
            pass
    if rename:
        df = df.rename(rename)
    return df


async def discover_decp_parquet_url() -> str:
    """Resolve the latest Parquet resource URL from data.gouv.fr API."""
    settings = get_settings()
    if settings.decp_parquet_url:
        return settings.decp_parquet_url

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        r = await client.get(DATA_GOUV_DATASET_API)
        r.raise_for_status()
        data = r.json()

    resources = data.get("resources") or []
    parquet_resources = [
        res
        for res in resources
        if (res.get("format") or "").lower() == "parquet"
        or (res.get("url") or "").endswith(".parquet")
        or "parquet" in (res.get("title") or "").lower()
    ]
    if not parquet_resources:
        # Fallback: any resource with parquet in url
        parquet_resources = [
            res for res in resources if "parquet" in (res.get("url") or "").lower()
        ]
    if not parquet_resources:
        raise RuntimeError(
            f"No Parquet resource found on dataset {DECP_DATASET_SLUG}. "
            "Set DECP_PARQUET_URL in .env"
        )

    # Prefer largest / most recently modified
    def sort_key(res: dict) -> tuple:
        return (
            res.get("last_modified") or res.get("created_at") or "",
            res.get("filesize") or 0,
        )

    parquet_resources.sort(key=sort_key, reverse=True)
    url = parquet_resources[0]["url"]
    logger.info("DECP Parquet URL: %s", url)
    return url


def download_decp_parquet(url: str | None = None, cache_path: Path | None = None) -> pl.DataFrame:
    """
    Download (or load cached) DECP Parquet.
    Uses polars scan/read — handles remote URLs when supported; else httpx + local file.
    """
    settings = get_settings()
    cache_path = cache_path or Path(settings.decp_cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if url is None:
        # Sync wrapper expects URL already resolved for pure sync path
        raise ValueError("url is required — call discover_decp_parquet_url first")

    # Reuse cache if fresh (< 20h)
    if cache_path.exists():
        age = datetime.now(timezone.utc) - datetime.fromtimestamp(
            cache_path.stat().st_mtime, tz=timezone.utc
        )
        if age < timedelta(hours=settings.decp_cache_hours):
            logger.info("Loading DECP from cache %s (age %s)", cache_path, age)
            return pl.read_parquet(cache_path)

    logger.info("Downloading DECP Parquet from %s", url)
    with httpx.stream("GET", url, follow_redirects=True, timeout=300.0) as resp:
        resp.raise_for_status()
        with open(cache_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                f.write(chunk)

    df = pl.read_parquet(cache_path)
    logger.info("DECP loaded: %d rows, %d cols", df.height, len(df.columns))
    return df


async def load_decp() -> pl.DataFrame:
    url = await discover_decp_parquet_url()
    return download_decp_parquet(url)


def filter_relevant(
    df: pl.DataFrame,
    *,
    days_back: int = 90,
    min_montant: float | None = None,
    cpv_prefixes: tuple[str, ...] = DEFAULT_CPV_PREFIXES,
    keywords: tuple[str, ...] = DEFAULT_KEYWORDS,
    max_rows: int | None = None,
) -> pl.DataFrame:
    """
    Aggressive filter for Elevya-relevant IT/cyber/digital public awards.
    Returns canonical columns + siren derived from siret.
    """
    df = _normalize_columns(df)
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_back)

    # Ensure required columns exist (fill null if missing so filter doesn't crash)
    for col, dtype in (
        ("dateAttribution", pl.Utf8),
        ("codeCPV", pl.Utf8),
        ("objetMarche", pl.Utf8),
        ("titulaire_siret", pl.Utf8),
        ("titulaire_nom", pl.Utf8),
        ("montant", pl.Float64),
        ("acheteur_nom", pl.Utf8),
        ("id", pl.Utf8),
    ):
        if col not in df.columns:
            df = df.with_columns(pl.lit(None).cast(dtype).alias(col))

    # Coerce types
    df = df.with_columns(
        [
            pl.col("titulaire_siret").cast(pl.Utf8, strict=False),
            pl.col("codeCPV").cast(pl.Utf8, strict=False),
            pl.col("objetMarche").cast(pl.Utf8, strict=False),
            pl.col("titulaire_nom").cast(pl.Utf8, strict=False),
            pl.col("acheteur_nom").cast(pl.Utf8, strict=False),
            pl.col("montant").cast(pl.Float64, strict=False),
            pl.col("id").cast(pl.Utf8, strict=False),
        ]
    )

    # Parse dates flexibly
    date_col = pl.col("dateAttribution")
    parsed_date = (
        date_col.str.to_datetime(strict=False, time_unit="us")
        .fill_null(date_col.str.strptime(pl.Datetime, format="%Y-%m-%d", strict=False))
        .fill_null(date_col.str.strptime(pl.Datetime, format="%Y-%m-%dT%H:%M:%S", strict=False))
        .fill_null(date_col.str.strptime(pl.Date, format="%Y-%m-%d", strict=False).cast(pl.Datetime))
    )
    df = df.with_columns(parsed_date.alias("_date"))

    # CPV match
    cpv_expr = pl.lit(False)
    for prefix in cpv_prefixes:
        cpv_expr = cpv_expr | pl.col("codeCPV").fill_null("").str.starts_with(prefix)

    # Keyword match on objet
    kw_pattern = "|".join(re.escape(k) for k in keywords)
    objet_lower = pl.col("objetMarche").fill_null("").str.to_lowercase()
    kw_expr = objet_lower.str.contains(kw_pattern)

    filtered = df.filter(
        (pl.col("_date").is_not_null())
        & (pl.col("_date") >= pl.lit(cutoff))
        & (cpv_expr | kw_expr)
        & (pl.col("titulaire_siret").is_not_null())
        & (pl.col("titulaire_siret").str.replace_all(r"\D", "").str.len_chars() >= 9)
    )

    if min_montant is not None:
        filtered = filtered.filter(
            pl.col("montant").is_null() | (pl.col("montant") >= min_montant)
        )

    filtered = filtered.with_columns(
        [
            pl.col("titulaire_siret")
            .str.replace_all(r"\D", "")
            .alias("titulaire_siret"),
            pl.col("titulaire_siret")
            .str.replace_all(r"\D", "")
            .str.slice(0, 9)
            .alias("siren"),
        ]
    )

    # Select stable projection
    keep = [
        c
        for c in (
            "id",
            "dateAttribution",
            "_date",
            "codeCPV",
            "objetMarche",
            "titulaire_siret",
            "titulaire_nom",
            "montant",
            "acheteur_nom",
            "siren",
        )
        if c in filtered.columns
    ]
    filtered = filtered.select(keep).sort("_date", descending=True)

    if max_rows:
        filtered = filtered.head(max_rows)

    logger.info(
        "DECP filter: %d awards (days_back=%d, cpv=%s)",
        filtered.height,
        days_back,
        cpv_prefixes,
    )
    return filtered


def aggregate_by_siret(df: pl.DataFrame) -> list[dict[str, Any]]:
    """
    Collapse awards into one record per SIRET with award_history list.
    Winning streak (multiple awards) is a capacity signal.
    """
    if df.is_empty():
        return []

    rows = df.to_dicts()
    by_siret: dict[str, dict[str, Any]] = {}

    for row in rows:
        siret = re.sub(r"\D", "", str(row.get("titulaire_siret") or ""))
        if len(siret) == 9:
            # pad not possible without NIC — keep as siren-only key
            key = siret
        elif len(siret) >= 14:
            siret = siret[:14]
            key = siret
        else:
            continue

        award = {
            "id": row.get("id"),
            "date": _date_iso(row.get("_date") or row.get("dateAttribution")),
            "objet": (row.get("objetMarche") or "")[:500],
            "cpv": row.get("codeCPV"),
            "montant": row.get("montant"),
            "acheteur": row.get("acheteur_nom"),
        }

        if key not in by_siret:
            by_siret[key] = {
                "siret": siret if len(siret) == 14 else None,
                "siren": siret[:9],
                "company_name": row.get("titulaire_nom") or f"SIRET {siret}",
                "award_history": [award],
                "last_tender_date": award["date"],
                "total_montant": float(award["montant"] or 0),
            }
        else:
            entry = by_siret[key]
            entry["award_history"].append(award)
            entry["total_montant"] += float(award["montant"] or 0)
            if award["date"] and (
                not entry["last_tender_date"] or award["date"] > entry["last_tender_date"]
            ):
                entry["last_tender_date"] = award["date"]
            if not entry.get("company_name") and row.get("titulaire_nom"):
                entry["company_name"] = row.get("titulaire_nom")
            if not entry.get("siret") and len(siret) == 14:
                entry["siret"] = siret

    # Sort history newest first; mark multi-win
    results = []
    for entry in by_siret.values():
        entry["award_history"].sort(key=lambda a: a.get("date") or "", reverse=True)
        entry["award_count"] = len(entry["award_history"])
        entry["has_multiple"] = entry["award_count"] >= 2
        # Build signal details from top awards
        objets = [a.get("objet") or "" for a in entry["award_history"][:3]]
        cyber = any("cyber" in (o or "").lower() for o in objets)
        details_parts = [
            f"{entry['award_count']} award(s)",
            f"total≈{entry['total_montant']:.0f}€" if entry["total_montant"] else None,
            "multiple wins" if entry["has_multiple"] else None,
            "cybersécurité" if cyber else None,
        ]
        entry["signal_details"] = " · ".join(p for p in details_parts if p)
        entry["objets_joined"] = " | ".join(objets)
        results.append(entry)

    results.sort(key=lambda e: (e["award_count"], e["total_montant"]), reverse=True)
    return results


def _date_iso(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date().isoformat()
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)[:10]


import re  # noqa: E402
