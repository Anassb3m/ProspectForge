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

# Compatibility-only default for read paths. Commands and persisted runs must
# always provide an explicit play code.
DEFAULT_PLAY_CODE = "FIELD_OPERATIONS_FR_V2"


def get_play(code: str | None = None) -> dict[str, Any]:
    """Retrieve market play configuration dictionary."""
    selected_code = code or DEFAULT_PLAY_CODE
    if selected_code not in ACTIVE_PLAYS:
        raise KeyError(f"Unknown or unsupported market play: {selected_code}")
    return ACTIVE_PLAYS[selected_code]


def require_play(code: str) -> dict[str, Any]:
    """Validate an explicit play code for mutation/orchestration paths."""
    if not code or code in {"DEFAULT", "default"}:
        raise ValueError("An explicit registered market play code is required")
    try:
        return get_play(code)
    except KeyError as exc:
        raise ValueError(str(exc)) from exc


def validate_ingestion_request(code: str, mode: str) -> dict[str, Any]:
    """Reject play/connector combinations not implemented end to end."""
    play = require_play(code)
    if code == "FIELD_OPERATIONS_UK_V1":
        raise ValueError(
            "FIELD_OPERATIONS_UK_V1 sourcing is disabled: Companies House is "
            "not wired to canonical pagination/checkpoints"
        )
    if play.get("jurisdiction") not in {None, "FR"}:
        raise ValueError(f"No enabled source connector for jurisdiction {play.get('jurisdiction')}")
    if mode not in {"full", "decp", "registry"}:
        raise ValueError(f"Connector mode {mode!r} is not enabled for {code}")
    return play


def list_active_plays() -> list[dict[str, Any]]:
    """List all registered active and pilot market plays."""
    return list(ACTIVE_PLAYS.values())


__all__ = [
    "ACTIVE_PLAYS",
    "DEFAULT_PLAY_CODE",
    "get_play",
    "require_play",
    "validate_ingestion_request",
    "list_active_plays",
    "get_uk_play_config",
    "get_fr_play_config",
]
