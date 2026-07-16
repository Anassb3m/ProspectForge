"""NAF/APE mapping for field-service / technical SMEs (V3)."""

from __future__ import annotations

# Field service / installation / maintenance NAF
FIELD_NAF_PREFIXES = ("33", "43", "81")
FIELD_NAF_CODES = {
    "4321A", "4321B", "4322A", "4322B", "4329A", "4329B",
    "3312Z", "3320A", "3320B", "3320C", "3320D", "3313Z", "3314Z",
    "8110Z", "8121Z", "8122Z", "7112B",
}

# Software / digital — excluded as *buyers* of custom ops software (they build)
IT_EXCLUDED_PREFIXES = ("62", "63", "58", "61")

TRANCHE_TO_SIZE: dict[str, str] = {
    "NN": "unknown",
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
    return code.replace(".", "").replace(" ", "").upper()


def is_field_service_naf(naf_code: str | None) -> bool:
    code = normalize_naf(naf_code)
    if not code:
        return False
    if code in FIELD_NAF_CODES:
        return True
    return code[:2] in FIELD_NAF_PREFIXES


def is_it_cyber_naf(naf_code: str | None) -> bool:
    """True if software/digital NAF — typically excluded as software *buyers*."""
    code = normalize_naf(naf_code)
    if not code:
        return False
    return code[:2] in IT_EXCLUDED_PREFIXES


def map_naf_to_sector(naf_code: str | None) -> str:
    code = normalize_naf(naf_code)
    if not code:
        return "Other"
    prefix = code[:2]
    if is_field_service_naf(code):
        if prefix == "81":
            return "Facilities / Maintenance"
        if prefix in ("33", "43"):
            return "Field Services"
        return "Field Services"
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
        return "unknown"
    return TRANCHE_TO_SIZE.get(str(tranche).strip().upper(), "unknown")
