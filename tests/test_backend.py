"""API integration checks use isolated SQLite ONLY; Supabase is a separate check."""
import json
from datetime import timedelta
from io import BytesIO
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import select

from backend.app import create_app
from backend.config import ROOT, Settings
from backend.db import AuthSession, Base, ImageCache, Prediction, User, make_engine, now, sessions
from backend.images import ImageService, fetch_report_image
from backend.migrations import seed_catalog
from backend.security import digest, passwords
from ml.predict import PricePredictor

PASSWORD = "A-test-password-only-924!"


@pytest.fixture(scope="session")
def predictor():
    model = PricePredictor()
    for kind in ("Car", "Bike", "Scooter"):
        model.catalog(kind)
    return model


@pytest.fixture
def api(predictor):
    settings = Settings(_env_file=None, database_url="sqlite+pysqlite:///:memory:",
                        app_secret="test-only-secret-" * 4, app_env="test", carsxe_api_key="", free_vehicle_photos=False,
                        allowed_hosts=["testserver"], allowed_origins=["http://testserver"])
    engine = make_engine(settings)
    Base.metadata.create_all(engine)
    seed_catalog(sessions(engine), predictor)
    app = create_app(settings, engine, predictor)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, app


def sign_in(client, email="first@example.com"):
    response = client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD, "display_name": "Test User"})
    assert response.status_code == 201, response.text
    user_id = response.json()["data"]["id"]
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return user_id, {"X-CSRF-Token": response.json()["data"]["csrf_token"]}


def specs(kind="bike"):
    return json.loads((ROOT / f"examples/predict-{kind}.json").read_text(encoding="utf-8"))


def test_health_catalog_and_openapi(api):
    client, app = api
    assert client.get("/api/v1/health/ready").json()["data"]["status"] == "ready"
    assert client.get("/api/v1/catalog/brands?vehicle_type=Bike").json()["data"]
    assert client.get("/api/v1/catalog/models?vehicle_type=Bike&brand=Bajaj").json()["data"]
    assert client.get("/api/v1/catalog/brands?vehicle_type=Truck").status_code == 422
    assert "/api/v1/predictions" in client.get("/openapi.json").json()["paths"]
    seed_catalog(app.state.sessions, app.state.predictor)
    assert client.get("/api/v1/assets/vehicles/scooter.jpg").headers["content-type"].startswith("image/jpeg")
    assert client.get("/api/v1/assets/vehicles/scooter.svg").status_code == 404


def test_private_model_photo_and_old_snapshot_refresh(api):
    client, app = api
    _, headers = sign_in(client)
    saved = client.post('/api/v1/predictions', json=specs(), headers=headers).json()['data']
    app.state.settings.carimages_api_key = __import__('pydantic').SecretStr('private-test-key')
    app.state.settings.carimages_api_secret = __import__('pydantic').SecretStr('private-test-secret')
    detail = client.get(f"/api/v1/predictions/{saved['id']}").json()['data']
    assert detail['image']['provider'] == 'carimages'
    assert 'private-test-key' not in json.dumps(detail)
    assert detail['result'] == saved['result']
    with app.state.sessions() as db:
        assert db.get(Prediction, saved['id']).image == saved['image']
    with patch.object(app.state.images, 'render', return_value=b'webp-test'):
        response = client.get(detail['image']['url'])
        assert response.status_code == 200 and response.content == b'webp-test'
        assert response.headers['content-type'] == 'image/webp'
    client.cookies.clear()
    assert client.get(detail['image']['url']).status_code == 401
    sign_in(client, 'different-photo-owner@example.com')
    assert client.get(detail['image']['url']).status_code == 404
    for kind in ('car', 'bike', 'scooter'):
        response = client.get(f'/api/v1/assets/vehicles/{kind}.jpg')
        assert response.headers['content-type'] == 'image/jpeg'
        assert response.content.startswith(b'\xff\xd8')


def test_auth_csrf_roles_logout_and_redaction(api):
    client, app = api
    assert client.get("/api/v1/predictions").status_code == 401
    bad = client.post("/api/v1/auth/register", json={"email": "secret@example.com", "password": "secret", "display_name": "A", "role": "Admin"})
    assert bad.status_code == 422 and "secret" not in bad.text and "Admin" not in bad.text
    identifier, headers = sign_in(client)
    assert client.get("/api/v1/admin/users").status_code == 403
    assert client.patch("/api/v1/profile", json={"display_name": "Changed"}).status_code == 403
    assert client.patch("/api/v1/profile", json={"display_name": "Changed"}, headers=headers).status_code == 200
    evil = {**headers, "Origin": "https://evil.example"}
    assert client.post("/api/v1/auth/logout", json={}, headers=evil).status_code == 403
    token = client.cookies.get(app.state.settings.cookie_name)
    with app.state.sessions() as db:
        assert db.get(AuthSession, digest(token))
        assert db.get(User, identifier).password_hash.startswith("$argon2id$")
    assert client.post("/api/v1/auth/logout", json={}, headers=headers).status_code == 200
    client.cookies.set(app.state.settings.cookie_name, token)
    assert client.get("/api/v1/auth/me").status_code == 401


@pytest.mark.parametrize("kind", ["car", "bike", "scooter"])
def test_real_model_persistence_and_pdf(api, kind):
    client, app = api
    _, headers = sign_in(client)
    payload = specs(kind)
    response = client.post("/api/v1/predictions", json=payload, headers=headers)
    if kind == 'car':
        assert response.status_code == 422
        assert response.json()['error']['code'] == 'insufficient_verified_market_data'
        assert client.get('/api/v1/predictions').json()['data']['total'] == 0
        return
    assert response.status_code == 201, response.text
    saved = response.json()["data"]
    expected = app.state.predictor.predict(payload)["predicted_price"]
    assert saved["result"]["predicted_price"] == expected
    assert saved["image"]["is_placeholder"] is True
    assert any(item["code"] == "unverified_source" for item in saved["result"]["warnings"])
    assert client.get(f"/api/v1/predictions/{saved['id']}").json()["data"] == saved
    with patch.object(app.state.predictor, "predict", side_effect=AssertionError("PDF must not re-infer")):
        report = client.get(f"/api/v1/predictions/{saved['id']}/report.pdf")
    assert report.status_code == 200, report.text[:100]
    assert report.content.startswith(b"%PDF")
    text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(report.content)).pages)
    assert f"{expected:,.2f}" in text and saved["id"] in text and "unverified" in text
    assert client.get("/api/v1/dashboard").json()["data"]["total_predictions"] == 1


def test_owner_isolation_including_admin(api):
    client, app = api
    owner, headers = sign_in(client)
    row = client.post("/api/v1/predictions", json=specs(), headers=headers).json()["data"]
    client.cookies.clear()
    other, _ = sign_in(client, "second@example.com")
    for suffix in ("", "/image", "/report.pdf"):
        assert client.get(f"/api/v1/predictions/{row['id']}{suffix}").status_code == 404
    assert client.get("/api/v1/predictions").json()["data"]["total"] == 0
    assert client.get("/api/v1/dashboard").json()["data"]["total_predictions"] == 0
    with app.state.sessions.begin() as db:
        db.get(User, other).role = "Admin"
    assert client.get("/api/v1/admin/stats").json()["data"]["predictions"] == 1
    assert client.get(f"/api/v1/predictions/{row['id']}/report.pdf").status_code == 404


def test_password_change_expiry_and_disable(api):
    client, app = api
    identifier, headers = sign_in(client)
    response = client.post("/api/v1/profile/password", json={"current_password": PASSWORD, "new_password": PASSWORD + "new"}, headers=headers)
    assert response.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "first@example.com", "password": PASSWORD}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "first@example.com", "password": PASSWORD + "new"}).status_code == 200
    with app.state.sessions.begin() as db:
        session = db.scalar(select(AuthSession))
        session.expires_at = now() - timedelta(seconds=1)
    assert client.get("/api/v1/auth/me").status_code == 401
    with app.state.sessions.begin() as db:
        db.get(User, identifier).active = False
    assert client.post("/api/v1/auth/login", json={"email": "first@example.com", "password": PASSWORD + "new"}).status_code == 401


def test_admin_disables_account_and_revokes_sessions(api):
    client, app = api
    target, _ = sign_in(client)
    target_token = client.cookies.get(app.state.settings.cookie_name)
    client.cookies.clear()
    admin, headers = sign_in(client, "admin@example.com")
    with app.state.sessions.begin() as db:
        db.get(User, admin).role = "Admin"
    assert client.patch(f"/api/v1/admin/users/{admin}/status", json={"active": False}, headers=headers).status_code == 409
    assert client.patch(f"/api/v1/admin/users/{target}/status", json={"active": False}, headers=headers).status_code == 200
    assert client.get("/api/v1/admin/stats").json()["data"]["active_users"] == 1
    with app.state.sessions() as db:
        assert db.get(AuthSession, digest(target_token)) is None


def test_input_validation_filters_and_body_limit(api):
    client, app = api
    _, headers = sign_in(client)
    for payload in ({**specs(), "price": 1}, {**specs(), "km_driven": True},
                    {**specs(), "manufacture_year": 2076}, {**specs(), "fuel_type": "Electric", "engine_capacity_cc": 150}):
        assert client.post("/api/v1/predictions", json=payload, headers=headers).status_code == 422
    for kind in ("bike", "scooter"):
        assert client.post("/api/v1/predictions", json=specs(kind), headers=headers).status_code == 201
    assert client.get("/api/v1/predictions?vehicle_type=Bike&limit=1").json()["data"]["total"] == 1
    assert client.get("/api/v1/predictions?search=%25").json()["data"]["total"] == 0
    assert client.get("/api/v1/predictions?limit=101").status_code == 422
    assert client.get("/api/v1/predictions?date_from=2026-09-01&date_to=2025-01-01").status_code == 422
    huge = client.post("/api/v1/predictions", content=b"x" * 40000, headers={**headers, "Content-Type": "application/json"})
    assert huge.status_code == 413
    assert client.post("/api/v1/auth/login", data={"email": "a"}).status_code == 415


def test_login_throttle_and_generic_errors(api):
    client, app = api
    for _ in range(10):
        response = client.post("/api/v1/auth/login", json={"email": "absent@example.com", "password": PASSWORD})
        assert response.status_code == 401
    response = client.post("/api/v1/auth/login", json={"email": "absent@example.com", "password": PASSWORD})
    assert response.status_code == 429 and int(response.headers["retry-after"]) > 0


@pytest.mark.parametrize("case", ["success", "empty", "timeout", "malformed", "oversized", "status"])
def test_image_provider_fallback_and_cache(api, case):
    client, app = api
    calls = []
    def provider(request):
        calls.append(request)
        if case == "timeout":
            raise httpx.ReadTimeout("test timeout")
        if case == "malformed":
            return httpx.Response(200, content=b"no json")
        if case == "oversized":
            return httpx.Response(200, content=b"x" * 300000)
        if case == "status":
            return httpx.Response(503)
        return httpx.Response(200, json={"success": True, "images": [] if case == "empty" else [
            {"link": "https://photos.example/car.png", "contextLink": "https://source.example/car"}]})
    settings = app.state.settings.model_copy(update={"carsxe_api_key": __import__('pydantic').SecretStr("test-provider-key")})
    service = ImageService(settings, app.state.sessions, httpx.Client(transport=httpx.MockTransport(provider)))
    value = service.resolve(specs())
    assert value["is_placeholder"] is (case != "success")
    assert "test-provider-key" not in json.dumps(value)
    if case == "success":
        assert service.resolve(specs()) == value and len(calls) == 1
        with app.state.sessions.begin() as db:
            db.scalar(select(ImageCache)).expires_at = now() - timedelta(seconds=1)
        service.resolve(specs())
        assert len(calls) == 2
    service.close()


def test_report_fetch_blocks_untrusted_and_private_hosts():
    metadata = {"is_placeholder": False, "url": "https://photos.example/photo.png"}
    with patch("backend.images.socket.getaddrinfo") as lookup:
        assert fetch_report_image(metadata, []) is None
        lookup.assert_not_called()
        lookup.return_value = [(2, 1, 6, "", ("127.0.0.1", 443))]
        with patch("backend.images.socket.create_connection") as connect:
            assert fetch_report_image(metadata, ["photos.example"]) is None
            connect.assert_not_called()


def test_production_configuration_requires_postgres_tls_and_https():
    with pytest.raises(ValueError):
        Settings(_env_file=None, database_url="sqlite://", app_secret="x" * 48, app_env="production")
    with pytest.raises(ValueError):
        Settings(_env_file=None, database_url="postgresql://user:password@db.example/postgres", app_secret="x" * 48)
    with pytest.raises(ValueError):
        Settings(_env_file=None, database_url="postgresql://user:password@db.example/postgres?sslmode=require", app_secret="x" * 48, app_env="production")
