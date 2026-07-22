"""Tests for UK Companies House Source Adapter."""

import pytest
from app.sources.companies_house import CompaniesHouseAdapter


@pytest.mark.asyncio
async def test_companies_house_discover_fixture():
    adapter = CompaniesHouseAdapter(api_key="")
    with pytest.raises(RuntimeError, match="Companies House API key missing"):
        await adapter.discover({"query": "Apex Commercial Refrigeration & HVAC Ltd"})
def test_companies_house_normalize():
    adapter = CompaniesHouseAdapter(api_key="")
    from app.sources.base import RawSourceRecord
    raw = RawSourceRecord(
        connector_code="companies_house",
        external_id="12984570",
        record_type="company",
        payload={
            "company_number": "12984570",
            "company_name": "Apex Commercial Refrigeration & HVAC Ltd",
            "company_status": "active",
            "sic_codes": ["43220"],
            "registered_office_address": {"locality": "Manchester", "postal_code": "M1 2AB"},
        },
    )
    obs_list = adapter.normalize(raw)
    assert len(obs_list) == 1
    obs = obs_list[0]
    assert obs.company_name == "Apex Commercial Refrigeration & HVAC Ltd"
    assert obs.country_code == "GB"
    assert obs.identifier_scheme == "companies_house_number"
    assert obs.identifier_value == "12984570"
    assert obs.classification_code == "43220"
