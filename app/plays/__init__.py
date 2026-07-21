"""Market play configurations, registry, and loaders."""

from typing import Any
from app.plays.field_service import FIELD_SERVICE_PLAY
from app.plays.field_operations_uk import FIELD_OPERATIONS_UK_DICT, get_uk_play_config
from app.plays.field_operations_fr import FIELD_OPERATIONS_FR_DICT, get_fr_play_config

ACTIVE_PLAYS: dict[str, dict[str, Any]] = {
    FIELD_OPERATIONS_UK_DICT["code"]: FIELD_OPERATIONS_UK_DICT,
    FIELD_OPERATIONS_FR_DICT["code"]: FIELD_OPERATIONS_FR_DICT,
    FIELD_SERVICE_PLAY["code"]: FIELD_SERVICE_PLAY,
}

DEFAULT_PLAY_CODE = "FIELD_OPERATIONS_UK_V1"


def get_play(code: str | None = None) -> dict[str, Any]:
    """Retrieve market play configuration dictionary."""
    selected_code = code or DEFAULT_PLAY_CODE
    if selected_code not in ACTIVE_PLAYS:
        raise KeyError(f"Unknown or unsupported market play: {selected_code}")
    return ACTIVE_PLAYS[selected_code]


def list_active_plays() -> list[dict[str, Any]]:
    """List all registered active and pilot market plays."""
    return [
        {
            "code": p.get("code"),
            "name": p.get("name"),
            "version": p.get("version"),
            "jurisdiction": p.get("jurisdiction", "FR"),
            "locale": p.get("locale", "fr-FR" if p.get("jurisdiction") == "FR" else "en-GB"),
            "status": p.get("status", "active"),
        }
        for p in ACTIVE_PLAYS.values()
    ]


__all__ = [
    "ACTIVE_PLAYS",
    "DEFAULT_PLAY_CODE",
    "get_play",
    "list_active_plays",
    "get_uk_play_config",
    "get_fr_play_config",
]
