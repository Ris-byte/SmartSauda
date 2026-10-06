"""Verify the configured Supabase database with temporary, uniquely named accounts.

Writes real API records, exports non-secret evidence, and removes ONLY the accounts
and predictions created by this invocation. Requires the local migration URL for
cleanup and privilege inspection. Does not call CarsXE or reset any credentials.
"""
import json
import argparse
import secrets
import sys
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from pydantic import SecretStr
from pypdf import PdfReader
from sqlalchemy import delete, func, select, text

from backend.app import create_app
from backend.config import Settings
from backend.db import AuthSession, CatalogEntry, Prediction, User, make_engine, sessions
from backend.migrations import migrate, seed_catalog
from ml.predict import PricePredictor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/phase3/supabase")
    args = parser.parse_args()
    settings = Settings()
    if not settings.migration_database_url:
        raise RuntimeError("Set MIGRATION_DATABASE_URL for scoped smoke-test cleanup")
    settings = settings.model_copy(update={"carsxe_api_key": SecretStr(""), "free_vehicle_photos": False, "carimages_api_key": SecretStr("")})
    owner_engine = make_engine(settings.model_copy(update={"database_url": settings.migration_database_url}))
    owner_sessions = sessions(owner_engine)
    run_id = uuid4().hex
    emails = [f"phase3-{run_id}-{index}@example.com" for index in range(2)]
    password = secrets.token_urlsafe(32)
    checks, examples, saved_rows = [], [], []
    output = args.output
    output.mkdir(parents=True, exist_ok=True)

    def checked(name, condition):
        if not condition:
            raise RuntimeError(f"Check failed: {name}")
        checks.append(name)
        print("PASS:", name, flush=True)

    def record(response, method, path, body=None):
        item = {"method": method, "path": path, "status": response.status_code, "response": response.json()}
        if body is not None:
            item["body"] = body
        examples.append(item)
        return response.json()["data"]

    try:
        model = PricePredictor()
        with owner_sessions() as db:
            before = db.scalar(select(func.count()).select_from(CatalogEntry))
        migrate(owner_engine)
        seed_catalog(owner_sessions, model)
        with owner_sessions() as db:
            after = db.scalar(select(func.count()).select_from(CatalogEntry))
            checked("migration_and_seed_idempotent", before == after == 241)
            protected = db.execute(text("""SELECT role_name,
                has_schema_privilege(role_name, 'smartsauda', 'USAGE') AS schema_access
                FROM (VALUES ('anon'), ('authenticated')) AS roles(role_name)""")).mappings().all()
            checked("supabase_public_api_roles_excluded", all(not row["schema_access"] for row in protected))
            role = db.execute(text("SELECT rolsuper, rolbypassrls, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname='smartsauda_app'")).mappings().one()
            checked("runtime_role_not_privileged", not any(role.values()))
            forbidden = db.execute(text("""SELECT
                has_schema_privilege('smartsauda_app', 'smartsauda', 'CREATE'),
                has_table_privilege('smartsauda_app', 'smartsauda.predictions', 'UPDATE'),
                has_table_privilege('smartsauda_app', 'smartsauda.predictions', 'DELETE'),
                has_table_privilege('smartsauda_app', 'smartsauda.catalog', 'INSERT'),
                has_table_privilege('smartsauda_app', 'auth.users', 'SELECT')""")).one()
            checked("runtime_privileges_limited_to_required_operations", not any(forbidden))
        app = create_app(settings, predictor=model)
        with TestClient(app, base_url="http://localhost:8000", client=(f"smoke-{run_id}", 50000)) as client:
            response = client.get("/api/v1/health/ready")
            checked("postgres_readiness", response.status_code == 200)
            record(response, "GET", "/api/v1/health/ready")
            response = client.post("/api/v1/auth/register", json={"email": emails[0], "password": password, "display_name": "Temporary integration check"})
            checked("registration_postgres", response.status_code == 201)
            response = client.post("/api/v1/auth/login", json={"email": emails[0], "password": password})
            checked("login_postgres", response.status_code == 200)
            headers = {"X-CSRF-Token": response.json()["data"]["csrf_token"]}
            first_cookie = client.cookies.get(settings.cookie_name)
            checked("csrf_rejected_postgres", client.post("/api/v1/predictions", json={}).status_code == 403)
            for kind in ("car", "bike", "scooter"):
                payload = json.loads((ROOT / f"examples/predict-{kind}.json").read_text(encoding="utf-8"))
                response = client.post("/api/v1/predictions", json=payload, headers=headers)
                checked(f"{kind}_prediction_created", response.status_code == 201)
                saved = record(response, "POST", "/api/v1/predictions", payload)
                saved_rows.append(saved)
                checked(f"{kind}_price_matches_model", saved["result"]["predicted_price"] == model.predict(payload)["predicted_price"])
                report = client.get(f"/api/v1/predictions/{saved['id']}/report.pdf")
                checked(f"{kind}_pdf_download", report.status_code == 200 and report.content.startswith(b"%PDF"))
                contents = "\n".join(page.extract_text() for page in PdfReader(BytesIO(report.content)).pages)
                checked(f"{kind}_pdf_saved_price_and_warning", f"{saved['result']['predicted_price']:,.2f}" in contents and "unverified" in contents)
                (output / f"sample-{kind}.pdf").write_bytes(report.content)
            response = client.get("/api/v1/predictions")
            checked("postgres_history_three_predictions", response.json()["data"]["total"] == 3)
            record(response, "GET", "/api/v1/predictions")
            response = client.get("/api/v1/dashboard")
            checked("postgres_dashboard_by_type", response.json()["data"]["by_type"] == {"Car": 1, "Bike": 1, "Scooter": 1})
            record(response, "GET", "/api/v1/dashboard")
            checked("ordinary_user_admin_forbidden", client.get("/api/v1/admin/stats").status_code == 403)
            client.cookies.clear()
            response = client.post("/api/v1/auth/register", json={"email": emails[1], "password": password, "display_name": "Temporary second account"})
            checked("second_account_registration", response.status_code == 201)
            second_id = response.json()["data"]["id"]
            response = client.post("/api/v1/auth/login", json={"email": emails[1], "password": password})
            checked("second_account_login", response.status_code == 200)
            for suffix in ("", "/image", "/report.pdf"):
                checked("owner_isolation" + (suffix or "/detail"), client.get(f"/api/v1/predictions/{saved_rows[0]['id']}{suffix}").status_code == 404)
            checked("second_account_empty_dashboard", client.get("/api/v1/dashboard").json()["data"]["total_predictions"] == 0)
            with owner_sessions.begin() as db:
                db.get(User, second_id).role = "Admin"
            checked("admin_aggregate_access", client.get("/api/v1/admin/stats").status_code == 200)
            checked("admin_has_no_other_owner_pdf_access", client.get(f"/api/v1/predictions/{saved_rows[0]['id']}/report.pdf").status_code == 404)
        # New engine and app instance: prove records/sessions outlive a server instance.
        with TestClient(create_app(settings, predictor=model), base_url="http://localhost:8000") as restarted:
            restarted.cookies.set(settings.cookie_name, first_cookie)
            response = restarted.get("/api/v1/predictions")
            checked("persistence_across_app_instances", response.status_code == 200 and response.json()["data"]["total"] == 3)
            response = restarted.get("/api/v1/auth/me")
            csrf = response.json()["data"]["csrf_token"]
            response = restarted.post("/api/v1/auth/logout", json={}, headers={"X-CSRF-Token": csrf})
            checked("logout_postgres", response.status_code == 200)
            restarted.cookies.set(settings.cookie_name, first_cookie)
            checked("revoked_cookie_rejected", restarted.get("/api/v1/auth/me").status_code == 401)
    finally:
        # No broad reset/drop/truncate: select only this run's two random addresses.
        with owner_sessions.begin() as db:
            identifiers = list(db.scalars(select(User.id).where(User.email.in_(emails))))
            if identifiers:
                db.execute(delete(Prediction).where(Prediction.user_id.in_(identifiers)))
                db.execute(delete(AuthSession).where(AuthSession.user_id.in_(identifiers)))
                db.execute(delete(User).where(User.id.in_(identifiers), User.email.in_(emails)))
        with owner_sessions() as db:
            checked("temporary_accounts_cleaned_up", db.scalar(select(func.count()).select_from(User).where(User.email.in_(emails))) == 0)
        owner_engine.dispose()
    result = {"checked_at": datetime.now(timezone.utc).isoformat(), "database": "Supabase PostgreSQL",
              "connection_mode": "session pooler", "runtime_role": "smartsauda_app", "passed": len(checks),
              "checks": checks, "temporary_accounts_removed": True, "carsxe_live_verified": False,
              "requests": examples}
    (output / "integration.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Supabase integration complete: {len(checks)} checks passed. Credentials and session tokens were not exported.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Do not expose database exceptions, URLs, bind values or credentials.
        print("Supabase integration failed; exception type:", type(error).__name__)
        raise SystemExit(1)
