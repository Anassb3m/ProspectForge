"""Company Identity Resolution and Deduplication Engine."""

import re
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Company, CompanyIdentifier


@dataclass
class ResolutionResult:
    resolution_type: str  # resolved_exact, resolved_high_confidence, candidate_review, unresolved
    company_id: str | None
    match_score: float
    match_reasons: list[str]


def normalize_company_name(name: str) -> str:
    """Normalize company name for comparison without destructive token removal."""
    n = name.lower().strip()
    n = re.sub(r"[^\w\s]", "", n)
    # Remove common UK/FR legal suffixes for comparison string
    suffixes = [
        "limited", "ltd", "public limited company", "plc", "llp",
        "societe par actions simplifiee", "sas", "sasu", "sarl", "sa", "gmbh"
    ]
    for s in suffixes:
        n = re.sub(rf"\b{s}\b", "", n)
    return " ".join(n.split())


async def resolve_company_identity(
    db: AsyncSession,
    company_name: str,
    country_code: str = "GB",
    identifier_scheme: str | None = None,
    identifier_value: str | None = None,
    domain: str | None = None,
) -> ResolutionResult:
    """Resolve raw observation to existing canonical company or signal creation."""
    reasons: list[str] = []

    # 1. Exact official identifier match
    if identifier_scheme and identifier_value:
        norm_val = identifier_value.strip().upper()
        stmt = select(CompanyIdentifier).where(
            CompanyIdentifier.scheme == identifier_scheme,
            CompanyIdentifier.value_normalized == norm_val,
        )
        res = await db.execute(stmt)
        ident = res.scalar_one_or_none()
        if ident:
            reasons.append(f"Exact match on identifier scheme '{identifier_scheme}': '{norm_val}'")
            return ResolutionResult(
                resolution_type="resolved_exact",
                company_id=ident.company_id,
                match_score=1.0,
                match_reasons=reasons,
            )

    # 2. Canonical or alternate legal name match
    norm_input_name = normalize_company_name(company_name)
    stmt_co = select(Company).where(Company.country_code == country_code)
    res_co = await db.execute(stmt_co)
    companies = res_co.scalars().all()

    for comp in companies:
        if normalize_company_name(comp.canonical_name) == norm_input_name:
            reasons.append(f"Exact normalized name match: '{comp.canonical_name}'")
            return ResolutionResult(
                resolution_type="resolved_high_confidence",
                company_id=comp.id,
                match_score=0.95,
                match_reasons=reasons,
            )

    return ResolutionResult(
        resolution_type="unresolved",
        company_id=None,
        match_score=0.0,
        match_reasons=["No matching identifier or canonical company name found."],
    )
