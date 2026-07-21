"""Tests for Official Company Domain Verification."""

import pytest
from app.services.domain_verification import normalize_domain_name, verify_company_domain


def test_normalize_domain_name():
    assert normalize_domain_name("https://www.apexrefrigeration.co.uk/about") == "apexrefrigeration.co.uk"
    assert normalize_domain_name("http://acme-services.com") == "acme-services.com"


@pytest.mark.asyncio
async def test_domain_verification_ssrf_safety():
    # Attempting localhost / internal IP should fail SSRF check
    res = await verify_company_domain("http://127.0.0.1", legal_name="Localhost Ltd")
    assert res.verification_state == "rejected"
    assert "SSRF" in res.match_reasons[0]
