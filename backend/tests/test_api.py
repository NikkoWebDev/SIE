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


@pytest.mark.asyncio
async def test_student_schedule():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/auth/login", json={"login_credential": "101", "password": "alumno"})
        assert r.status_code == 200
        token = r.json().get("access_token")
        assert token
        r = await ac.get("/api/schedule?student_id=101", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert "days" in data
        assert "hours" in data
        assert isinstance(data["hours"], list)
        assert isinstance(data["days"], dict)


@pytest.mark.asyncio
async def test_teacher_schedule():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/auth/login", json={"login_credential": "11", "password": "profe"})
        assert r.status_code == 200
        token = r.json().get("access_token")
        assert token
        r = await ac.get("/api/teacher/schedule?teacher_id=11", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert "grado" in data
        assert "days" in data
        assert "hours" in data
        assert isinstance(data["hours"], list)


@pytest.mark.asyncio
async def test_schedule_student_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/auth/login", json={"login_credential": "101", "password": "alumno"})
        assert r.status_code == 200
        token = r.json().get("access_token")
        r = await ac.get("/api/schedule?student_id=99999", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert data["days"] == {}
        assert data["hours"] == []
