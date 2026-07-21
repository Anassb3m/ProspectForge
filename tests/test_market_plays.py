"""Tests for Market Play Configurations."""

from app.plays import list_active_plays, get_uk_play_config, get_fr_play_config


def test_list_active_plays():
    plays = list_active_plays()
    codes = [p["code"] for p in plays]
    assert "FIELD_OPERATIONS_UK_V1" in codes
    assert "FIELD_OPERATIONS_FR_V2" in codes


def test_uk_play_config_validation():
    cfg = get_uk_play_config()
    assert cfg.code == "FIELD_OPERATIONS_UK_V1"
    assert cfg.jurisdiction == "GB"
    assert cfg.locale == "en-GB"
    assert cfg.status == "pilot"
    assert "ltd" in cfg.entity_policy["allowed_legal_forms"]
    assert "sole_trader" in cfg.entity_policy["excluded_legal_forms"]


def test_fr_play_config_validation():
    cfg = get_fr_play_config()
    assert cfg.code == "FIELD_OPERATIONS_FR_V2"
    assert cfg.jurisdiction == "FR"
    assert cfg.locale == "fr-FR"
    assert cfg.status == "pilot"
    assert "sas" in cfg.entity_policy["allowed_legal_forms"]
    assert "auto_entrepreneur" in cfg.entity_policy["excluded_legal_forms"]
