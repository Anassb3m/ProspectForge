import asyncio
import logging
from app.sources.decp_adapter import DecpAdapter

logging.basicConfig(level=logging.INFO)

async def run_validation():
    adapter = DecpAdapter()
    print("Running DECP validation...")
    results, checkpoint, has_more = await adapter.discover(checkpoint=None, limit=5, query_params={})
    print(f"Discovered {len(results)} records.")
    for r in results:
        print(f"- {r.external_id}: {r.payload.get('acheteur', {}).get('nom')}")

if __name__ == "__main__":
    asyncio.run(run_validation())
