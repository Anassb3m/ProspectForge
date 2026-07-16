"""Market-play configurations and loaders."""

from app.plays.field_service import FIELD_SERVICE_PLAY

ACTIVE_PLAYS = {
    FIELD_SERVICE_PLAY["code"]: FIELD_SERVICE_PLAY,
}

DEFAULT_PLAY_CODE = "FIELD_SERVICE_OPERATIONS_FR"


def get_play(code: str | None = None) -> dict:
    code = code or DEFAULT_PLAY_CODE
    if code not in ACTIVE_PLAYS:
        raise KeyError(f"Unknown market play: {code}")
    return ACTIVE_PLAYS[code]
