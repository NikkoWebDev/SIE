import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_login_invalid():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/auth/login", json={
            "login_credential": "nonexistent",
            "password": "wrong",
        })
    assert r.status_code == 401
    assert "Credenciales" in r.json().get("detail", "")


@pytest.mark.asyncio
async def test_login_missing_fields():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/auth/login", json={})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_notices_public():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/notices")
    assert r.status_code in (200, 404)


@pytest.mark.asyncio
async def test_risk_alerts_endpoint_no_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/risk-alerts")
    assert r.status_code in (401, 403)  # 401 from global auth middleware, 403 if token present but wrong role
