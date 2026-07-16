"""NAF/APE code mapping and IT/cyber detection for French SMEs."""

from __future__ import annotations

# Elevya-relevant IT / digital / cyber NAF prefixes and codes
IT_CYBER_NAF_PREFIXES = ("62", "63", "58", "61")
IT_CYBER_NAF_CODES = {
    "6201Z",  # Programmation informatique
    "6202A",  # Conseil en systèmes et logiciels informatiques
    "6202B",  # Tierce maintenance de systèmes et d'applications
    "6203Z",  # Gestion d'installations informatiques
    "6209Z",  # Autres activités informatiques
    "6311Z",  # Traitement de données, hébergement
    "6312Z",  # Portails Internet
    "5821Z",  # Édition de jeux électroniques
    "5829A",  # Édition de logiciels système
    "5829B",  # Édition de logiciels applicatifs
    "6110Z",  # Télécommunications filaires
    "6120Z",  # Télécommunications sans fil
    "6190Z",  # Autres activités de télécommunication
    "7022Z",  # Conseil pour les affaires (often digital transformation)
    "7112B",  # Ingénierie, études techniques
}

# Official INSEE trancheEffectifs → our company_size buckets
TRANCHE_TO_SIZE: dict[str, str] = {
    "NN": "1-10",
    "00": "1-10",
    "01": "1-10",
    "02": "1-10",
    "03": "1-10",
    "11": "1-10",
    "12": "11-50",
    "21": "11-50",
    "22": "11-50",
    "31": "51-200",
    "32": "51-200",
    "41": "51-200",
    "42": "200+",
    "51": "200+",
    "52": "200+",
    "53": "200+",
}


def normalize_naf(code: str | None) -> str | None:
    if not code:
        return None
    # Strip dots: 62.01Z → 6201Z
    return code.replace(".", "").replace(" ", "").upper()


def is_it_cyber_naf(naf_code: str | None) -> bool:
    code = normalize_naf(naf_code)
    if not code:
        return False
    if code in IT_CYBER_NAF_CODES:
        return True
    return code[:2] in IT_CYBER_NAF_PREFIXES


def map_naf_to_sector(naf_code: str | None) -> str:
    """Map NAF to ProspectForge sector label."""
    code = normalize_naf(naf_code)
    if not code:
        return "Other"
    prefix = code[:2]
    if is_it_cyber_naf(code):
        return "IT / Digital"
    if prefix in ("41", "42", "43"):
        return "Construction"
    if prefix in ("10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33"):
        return "Manufacturing"
    if prefix in ("49", "50", "51", "52", "53"):
        return "Logistics"
    if prefix in ("71", "72"):
        return "Engineering"
    if prefix in ("69", "70", "73", "74", "78", "82"):
        return "Professional Services"
    return "Other"


def map_tranche_effectifs(tranche: str | None) -> str:
    if not tranche:
        return "1-10"
    return TRANCHE_TO_SIZE.get(str(tranche).strip().upper(), "1-10")
