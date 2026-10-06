"""Production routing/cookie/header boundaries without a live database."""
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.config import ROOT, Settings
from backend.db import Base, make_engine


@pytest.fixture
def deployed():
    assert (ROOT / "frontend/dist/index.html").is_file(), "Run npm run build in frontend first"
    settings = Settings(_env_file=None, database_url="sqlite+pysqlite:///:memory:",
                        app_secret="deployment-test-only-" * 3, app_env="test",
                        allowed_hosts=["testserver"], allowed_origins=["https://testserver"],
                        frontend_dist=ROOT / "frontend/dist", carsxe_api_key="", free_vehicle_photos=False)
    engine = make_engine(settings)
    Base.metadata.create_all(engine)
    production = settings.model_copy(update={"app_env": "production"})
    with TestClient(create_app(production, engine=engine), base_url="https://testserver") as client:
        yield client


def test_spa_deep_links_and_static_cache(deployed):
    index = deployed.get("/")
    assert index.status_code == 200 and 'id="root"' in index.text
    assert deployed.get("/history?type=Bike").text == index.text
    assert deployed.get("/predictions/123").text == index.text
    assert index.headers["cache-control"] == "no-cache"
    asset = next((ROOT / "frontend/dist/assets").glob("index-*.js")).name
    response = deployed.get("/assets/" + asset, headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert "immutable" in response.headers["cache-control"]
    assert deployed.get("/images/nepal-rides-hero.webp").headers["content-type"] == "image/webp"
    for path in ["/api/unknown", "/api/v1/no-such-route", "/docs", "/openapi.json", "/.env", "/backend/config.py", "/assets/..%2f..%2f.env", "/assets/missing.js"]:
        response = deployed.get(path)
        assert response.status_code == 404, path
        assert 'id="root"' not in response.text, path


def test_production_security_headers_and_session_cookie(deployed):
    response = deployed.get("/")
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert "max-age=31536000" in response.headers["strict-transport-security"]
    payload = {"email": "deployment@example.com", "display_name": "Deployment Check", "password": "deployment-test-password!"}
    assert deployed.post("/api/v1/auth/register", json=payload).status_code == 201
    response = deployed.post("/api/v1/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "__Host-smartsauda_session=" in cookie
    assert "HttpOnly" in cookie and "Secure" in cookie and "Path=/" in cookie
    assert "Domain=" not in cookie
    assert response.headers["cache-control"] == "no-store"
    assert deployed.get("/api/v1/auth/me").status_code == 200
    assert deployed.patch("/api/v1/profile", json={"display_name": "Rejected"}).status_code == 403
    assert deployed.patch("/api/v1/profile", json={"display_name": "Rejected"}, headers={"Origin": "https://evil.example"}).status_code == 403
    assert deployed.get("/api/v1/health/live", headers={"Host": "evil.example"}).status_code == 400
