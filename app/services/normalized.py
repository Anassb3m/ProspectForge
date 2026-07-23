from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import (
    Company,
    CompanyIdentifier,
    CompanyDomain,
    CompanyLocation,
    Opportunity,
    MarketPlayVersion,
    SourceRecord
)
import logging

logger = logging.getLogger(__name__)

async def upsert_normalized_company(
    session: AsyncSession,
    company_name: str,
    siren: Optional[str] = None,
    siret: Optional[str] = None,
    website: Optional[str] = None,
    city: Optional[str] = None,
    department: Optional[str] = None,
    source_run_id: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
    play_code: str = "DEFAULT"
) -> Opportunity:
    # 1. Identify or Create Company
    company = None
    if siret:
        result = await session.execute(
            select(Company).join(CompanyIdentifier).where(
                CompanyIdentifier.scheme == "FR_SIRET",
                CompanyIdentifier.value_normalized == siret
            )
        )
        company = result.scalars().first()
    
    if not company and siren:
        result = await session.execute(
            select(Company).join(CompanyIdentifier).where(
                CompanyIdentifier.scheme == "FR_SIREN",
                CompanyIdentifier.value_normalized == siren
            )
        )
        company = result.scalars().first()

    if not company:
        company = Company(
            canonical_name=company_name,
            country_code="FR"
        )
        session.add(company)
        await session.flush()
        
        if siren:
            session.add(CompanyIdentifier(
                company_id=company.id,
                scheme="FR_SIREN",
                value_normalized=siren,
                is_primary=True
            ))
        if siret:
            session.add(CompanyIdentifier(
                company_id=company.id,
                scheme="FR_SIRET",
                value_normalized=siret,
                is_primary=False
            ))
            
    # Add domain if provided
    if website:
        domain_norm = website.replace("https://", "").replace("http://", "").split("/")[0]
        result = await session.execute(
            select(CompanyDomain).where(
                CompanyDomain.company_id == company.id,
                CompanyDomain.domain_normalized == domain_norm
            )
        )
        if not result.scalars().first():
            session.add(CompanyDomain(
                company_id=company.id,
                domain_normalized=domain_norm,
                domain_role="primary"
            ))

    # Add location
    if city or department:
        result = await session.execute(
            select(CompanyLocation).where(
                CompanyLocation.company_id == company.id,
                CompanyLocation.postal_code == department
            )
        )
        if not result.scalars().first():
            session.add(CompanyLocation(
                company_id=company.id,
                location_type="registered",
                locality=city,
                postal_code=department,
                country_code="FR"
            ))

    # Add SourceRecord
    if source_run_id:
        source_record = SourceRecord(
            source_run_id=source_run_id,
            external_id=siret or siren,
            payload_json=payload
        )
        session.add(source_record)

    # Add or update Opportunity
    result = await session.execute(select(MarketPlayVersion).where(MarketPlayVersion.play_code == play_code).limit(1))
    play = result.scalars().first()
    if not play:
        play = MarketPlayVersion(play_code=play_code, version="1.0.0", status="active")
        session.add(play)
        await session.flush()

    result = await session.execute(
        select(Opportunity).where(
            Opportunity.company_id == company.id,
            Opportunity.play_version_id == play.id
        )
    )
    opp = result.scalars().first()
    if not opp:
        opp = Opportunity(
            company_id=company.id,
            play_version_id=play.id,
            status="discovered",
            priority="Medium",
            latest_score=50.0
        )
        session.add(opp)

    await session.flush()
    return opp
