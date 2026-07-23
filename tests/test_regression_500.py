import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_find_500(client: AsyncClient, auth_headers: dict):
    routes = [
        "/",
        "/market-plays",
        "/sourcing",
        "/prospects",
        "/kanban",
        "/queue",
        "/follow-ups",
        "/import"
    ]
    for route in routes:
        response = await client.get(route, headers=auth_headers)
        assert response.status_code < 500, f"Regression: 500 on GET {route} - {response.text}"
