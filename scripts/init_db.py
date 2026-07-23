import asyncio
from app.database import engine, Base

from app.main import bootstrap_admin, seed_market_plays

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await bootstrap_admin()
    await seed_market_plays()

if __name__ == "__main__":
    asyncio.run(init_db())
