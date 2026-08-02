#!/usr/bin/env python3
"""Seed database with production-shaped data for rehearsal testing."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone


from app.database import async_session_factory
from app.models import Company, Opportunity, MarketPlayVersion, Prospect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_production_shape() -> None:
    logger.info("Starting production-shaped seed...")
    async with async_session_factory() as session:
        play_id = str(uuid.uuid4())
        session.add(MarketPlayVersion(
            id=play_id,
            play_code="FIELD_OPERATIONS_FR_V2",
            version="2.0.0",
            status="active"
        ))
        await session.commit()
        
        companies = []
        opportunities = []
        prospects = []
        
        # Create realistic volume (1000 records)
        for i in range(1000):
            company_id = str(uuid.uuid4())
            opp_id = str(uuid.uuid4())
            
            companies.append(
                Company(
                    id=company_id,
                    canonical_name=f"Synth Company {i}",
                    legal_name=f"Synth Company {i} SAS",
                    country_code="FR",
                    entity_status="active",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )
            
            opportunities.append(
                Opportunity(
                    id=opp_id,
                    company_id=company_id,
                    play_version_id=play_id,
                    status="draft_ready" if i % 10 == 0 else "discovered",
                    priority="High" if i % 5 == 0 else "Low",
                    latest_score=float(10 + (i * 37) % 81),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )

            prospects.append(
                Prospect(
                    company_name=f"Synth Company {i}",
                    siren=f"{100000000 + i}",
                    company_id=company_id,
                    opportunity_id=opp_id,
                    sector="Field Services",
                    company_size="11-50",
                    signal_type="DECP_WIN",
                    email=f"contact{i}@example.com",
                    website=f"https://synth{i}.fr",
                    source="DECP",
                    data_source="synthetic",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )
            
        session.add_all(companies)
        await session.commit()
        
        session.add_all(opportunities)
        session.add_all(prospects)
        await session.commit()
        logger.info("Seed complete!")

if __name__ == "__main__":
    asyncio.run(seed_production_shape())
