#!/usr/bin/env python3
"""Seed database with 10,000 companies and opportunities for benchmarking."""

import asyncio
import logging
import uuid
import random
from datetime import datetime, timezone

from sqlalchemy import text
from app.database import async_session_factory
from app.models import Company, Opportunity, MarketPlayVersion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_10k() -> None:
    logger.info("Starting 10,000 record benchmark seed...")
    async with async_session_factory() as session:
        # Check if we already seeded
        result = await session.execute(text("SELECT COUNT(id) FROM companies"))
        count = result.scalar()
        if count and count >= 10000:
            logger.info("Database already contains >= 10,000 companies. Skipping seed.")
            return

        # Ensure at least one market play version exists
        result = await session.execute(text("SELECT id FROM market_play_versions LIMIT 1"))
        play_id = result.scalar()
        if not play_id:
            logger.info("No MarketPlayVersion found. Creating a dummy one for benchmark.")
            play_id = str(uuid.uuid4())
            session.add(MarketPlayVersion(
                id=play_id,
                play_code="BENCHMARK_PLAY",
                version="1.0.0",
                status="active"
            ))
            await session.commit()

        logger.info(f"Using MarketPlayVersion ID: {play_id}")
        
        chunk_size = 1000
        total = 10000
        
        for chunk in range(0, total, chunk_size):
            logger.info(f"Seeding chunk {chunk} to {chunk + chunk_size}...")
            
            companies = []
            opportunities = []
            
            for i in range(chunk_size):
                company_id = str(uuid.uuid4())
                companies.append(
                    Company(
                        id=company_id,
                        canonical_name=f"Benchmark Corp {chunk + i}",
                        legal_name=f"Benchmark Corp {chunk + i} Ltd",
                        country_code=random.choice(["GB", "FR"]),
                        entity_status="active",
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                )
                
                opportunities.append(
                    Opportunity(
                        id=str(uuid.uuid4()),
                        company_id=company_id,
                        play_version_id=play_id,
                        status=random.choice(["qualified", "draft_ready", "in_outreach"]),
                        priority=random.choice(["High", "Medium", "Low"]),
                        latest_score=random.uniform(20.0, 100.0),
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                )
            
            session.add_all(companies)
            await session.commit()  # Commit companies first to satisfy FK
            
            session.add_all(opportunities)
            await session.commit()
            
            logger.info(f"Committed {chunk + chunk_size} records.")
            
        logger.info("Seed complete!")

if __name__ == "__main__":
    asyncio.run(seed_10k())
