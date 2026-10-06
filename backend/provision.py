"""Provision a restricted runtime login; keep owner credentials for migrations only."""
import secrets

from dotenv import set_key
from psycopg import sql
from sqlalchemy import text
from sqlalchemy.engine import make_url

from backend.config import ROOT

ROLE = "smartsauda_app"


def provision_runtime(engine, settings):
    current = make_url(settings.database_url.get_secret_value())
    if current.username.split(".")[0] == ROLE:
        return "Restricted runtime login is already configured; credentials unchanged."
    password = secrets.token_urlsafe(48)
    with engine.begin() as db:
        db.execute(text("SELECT pg_advisory_xact_lock(746281902)"))
        if db.scalar(text("SELECT EXISTS(SELECT FROM pg_roles WHERE rolname=:role)"), {"role": ROLE}):
            raise RuntimeError("Runtime role already exists; credentials were not overwritten")
        with db.connection.driver_connection.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS CONNECTION LIMIT 8 PASSWORD {}").format(
                sql.Identifier(ROLE), sql.Literal(password)))
            cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA smartsauda TO {}").format(sql.Identifier(ROLE)))
            for table, privileges in {
                "users": "SELECT, INSERT, UPDATE",
                "sessions": "SELECT, INSERT, DELETE",
                "predictions": "SELECT, INSERT",
                "catalog": "SELECT",
                "rate_buckets": "SELECT, INSERT, UPDATE, DELETE",
                "image_cache": "SELECT, INSERT, UPDATE",
            }.items():
                cursor.execute(sql.SQL("GRANT {} ON TABLE smartsauda.{} TO {}").format(
                    sql.SQL(privileges), sql.Identifier(table), sql.Identifier(ROLE)))
    username = ROLE + ("." + current.username.split(".", 1)[1] if "." in current.username else "")
    runtime = current.set(username=username, password=password)
    # Keep the owner connection only in the ignored local environment file.
    path = ROOT / ".env"
    owner = settings.migration_database_url or settings.database_url
    set_key(path, "MIGRATION_DATABASE_URL", owner.get_secret_value(), quote_mode="always")
    set_key(path, "DATABASE_URL", runtime.render_as_string(hide_password=False), quote_mode="always")
    return "Restricted runtime login created. Local credentials updated; values hidden."
