import asyncio
import logging
from sqlalchemy import select
from app.database import async_session_factory
from app.models import (
    Prospect,
    Company,
    CompanyIdentifier,
    CompanyDomain,
    CompanyLocation,
    CompanyClassification,
    Opportunity,
    MarketPlayVersion
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def backfill():
    async with async_session_factory() as session:
        # 1. Get or create a default MarketPlayVersion
        result = await session.execute(select(MarketPlayVersion).limit(1))
        play = result.scalars().first()
        if not play:
            play = MarketPlayVersion(
                play_code="MIGRATION_PLAY",
                version="1.0.0",
                status="active"
            )
            session.add(play)
            await session.commit()
            await session.refresh(play)

        # 2. Get all prospects
        result = await session.execute(select(Prospect))
        prospects = result.scalars().all()
        logger.info(f"Found {len(prospects)} prospects to migrate")

        for prospect in prospects:
            # Create Company
            company = Company(
                canonical_name=prospect.company_name,
                country_code="FR", # default based on context
            )
            session.add(company)
            await session.flush()

            # Add Identifiers (SIREN/SIRET)
            if prospect.siren:
                session.add(CompanyIdentifier(
                    company_id=company.id,
                    scheme="FR_SIREN",
                    value_normalized=prospect.siren,
                    is_primary=True
                ))
            if prospect.siret:
                session.add(CompanyIdentifier(
                    company_id=company.id,
                    scheme="FR_SIRET",
                    value_normalized=prospect.siret,
                    is_primary=False
                ))

            # Add Domain
            if prospect.website:
                session.add(CompanyDomain(
                    company_id=company.id,
                    domain_normalized=prospect.website.replace("https://", "").replace("http://", "").split("/")[0],
                    domain_role="primary"
                ))

            # Add Location
            if prospect.city or prospect.region or prospect.department:
                session.add(CompanyLocation(
                    company_id=company.id,
                    location_type="registered",
                    locality=prospect.city,
                    region=prospect.region,
                    postal_code=prospect.department, # approximation
                    country_code="FR"
                ))

            # Add Classification
            if prospect.sector:
                session.add(CompanyClassification(
                    company_id=company.id,
                    scheme="SECTOR",
                    code=prospect.sector,
                    label=prospect.sector
                ))
            if prospect.company_size:
                session.add(CompanyClassification(
                    company_id=company.id,
                    scheme="SIZE",
                    code=prospect.company_size,
                    label=prospect.company_size
                ))

            # Add Opportunity
            opp = Opportunity(
                company_id=company.id,
                play_version_id=play.id,
                status=prospect.acquisition_stage,
                priority=prospect.priority_level,
                latest_score=float(prospect.opportunity_score)
            )
            session.add(opp)

            # Map back to Prospect (optional tracking)
            # Not adding columns to Prospect just yet unless required, we can rely on SIREN/SIRET to link them if needed.

        await session.commit()
        logger.info("Backfill complete!")

if __name__ == "__main__":
    asyncio.run(backfill())
