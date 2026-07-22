import asyncio
import logging
from sqlalchemy import select
from app.database import async_session_factory, init_db
from app.models import Prospect
from app.repositories.company_repo import CompanyRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def backfill():
    await init_db()
    async with async_session_factory() as session:
        repo = CompanyRepository(session)
        result = await session.execute(select(Prospect))
        prospects = result.scalars().all()
        logger.info(f"Found {len(prospects)} prospects to backfill.")
        
        count = 0
        for p in prospects:
            await repo.upsert_company(
                prospect_id=p.id,
                name=p.company_name or f"SIREN {p.siren}",
                siren=p.siren,
                siret=p.siret,
                city=p.city
            )
            count += 1
            if count % 100 == 0:
                await session.commit()
                logger.info(f"Backfilled {count}/{len(prospects)}")
                
        await session.commit()
        logger.info(f"Successfully backfilled {count} prospects into normalized tables.")

if __name__ == "__main__":
    asyncio.run(backfill())
