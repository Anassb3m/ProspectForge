"""Official Company Domain Verification Engine with SSRF Protection."""

import re
from dataclasses import dataclass
from typing import Any
import httpx
from app.contact_intelligence.safety import validate_public_url


@dataclass
class DomainVerificationResult:
    domain_normalized: str
    verification_state: str  # verified_primary, candidate, rejected
    match_score: float
    match_reasons: list[str]
    metadata: dict[str, Any]


def normalize_domain_name(raw_url_or_domain: str) -> str:
    """Normalize input domain string to punycode lowercase host."""
    d = raw_url_or_domain.lower().strip()
    d = re.sub(r"^https?://", "", d)
    d = d.split("/")[0].split(":")[0]
    if d.startswith("www."):
        d = d[4:]
    return d


async def verify_company_domain(
    domain_candidate: str,
    legal_name: str,
    company_identifier: str | None = None,
    country_code: str = "GB",
) -> DomainVerificationResult:
    """Verify domain belongs to target legal entity with SSRF safety."""
    domain_norm = normalize_domain_name(domain_candidate)
    reasons: list[str] = []
    score = 0.0

    target_url = f"https://{domain_norm}"
    try:
        await validate_public_url(target_url)
    except Exception as exc:
        return DomainVerificationResult(
            domain_normalized=domain_norm,
            verification_state="rejected",
            match_score=0.0,
            match_reasons=[f"SSRF safety check failed: {str(exc)}"],
            metadata={},
        )

    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(target_url, headers={"User-Agent": "ProspectForge/2.0 Official Domain Verifier"})
            if resp.status_code != 200:
                return DomainVerificationResult(
                    domain_normalized=domain_norm,
                    verification_state="candidate",
                    match_score=0.3,
                    match_reasons=[f"HTTP status {resp.status_code} on primary domain root."],
                    metadata={"status_code": resp.status_code},
                )

            body_text = resp.text.lower()
            # 1. Official company number in footer / legal page
            if company_identifier and company_identifier.lower() in body_text:
                score += 0.6
                reasons.append(f"Found official identifier '{company_identifier}' in website content.")

            # 2. Company legal name match
            clean_name = legal_name.lower().replace("limited", "").replace("ltd", "").strip()
            if clean_name and clean_name in body_text:
                score += 0.4
                reasons.append(f"Found company name component '{clean_name}' in website content.")

            state = "verified_primary" if score >= 0.6 else "candidate"
            return DomainVerificationResult(
                domain_normalized=domain_norm,
                verification_state=state,
                match_score=min(score + 0.2, 1.0),
                match_reasons=reasons or ["Domain responded with HTTP 200."],
                metadata={"final_url": str(resp.url)},
            )
    except Exception as exc:
        return DomainVerificationResult(
            domain_normalized=domain_norm,
            verification_state="candidate",
            match_score=0.1,
            match_reasons=[f"Crawl error: {str(exc)}"],
            metadata={},
        )
