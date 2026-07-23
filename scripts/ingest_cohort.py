import asyncio
import logging

from app.database import engine, Base
from app.jobs.ingestion import run_ingestion
import os
os.environ["DECP_CACHE_PATH"] = "./data/decp_cache.parquet"
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Initializing DB connection for bounded cohort ingestion...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    settings = get_settings()
    cohort_size = settings.max_cohort_size
    logger.info(f"Starting ingestion with a bounded cohort of {cohort_size} records...")
    
    # Run DECP ingestion limited by our Phase 9 safeguards
    results = await run_ingestion(
        mode="decp",
        play_code="FIELD_OPERATIONS_FR_V2",
        max_companies=cohort_size,
        run_contact_discovery=False,
        days_back=3650,
    )
    
    logger.info("Bounded cohort ingestion complete.")
    logger.info(f"Results: {results}")

if __name__ == "__main__":
    asyncio.run(main())
