"""Tests for Company Identity Resolution Engine."""

from app.services.identity_resolution import normalize_company_name


def test_normalize_company_name():
    assert normalize_company_name("Apex Refrigeration Limited") == "apex refrigeration"
    assert normalize_company_name("Acme HVAC & Cooling Services PLC") == "acme hvac cooling services"
    assert normalize_company_name("Société Maintenance SAS") == "société maintenance"
