"""Ordered, checksummed PostgreSQL migrations; no automatic destructive downgrade."""
import hashlib
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.db import CatalogEntry

MIGRATIONS = Path(__file__).parent / "sql"


def migrate(engine):
    if engine.dialect.name != "postgresql":
        raise ValueError("Production migrations require PostgreSQL")
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(746281900)"))
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS smartsauda"))
        connection.execute(text("REVOKE ALL ON SCHEMA smartsauda FROM PUBLIC"))
        connection.execute(text("CREATE TABLE IF NOT EXISTS smartsauda.schema_migrations (version varchar(80) PRIMARY KEY, sha256 varchar(64) NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())"))
        known = dict(connection.execute(text("SELECT version, sha256 FROM smartsauda.schema_migrations")).all())
        files = sorted(MIGRATIONS.glob("*.sql"))
        if set(known) - {path.stem for path in files}:
            raise RuntimeError("Database contains a newer migration; update the application")
        for path in files:
            sql = path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode()).hexdigest()
            if path.stem in known:
                if known[path.stem] != checksum:
                    raise RuntimeError("An applied migration has changed; restore it and add a new migration")
                continue
            with connection.connection.driver_connection.cursor() as cursor:
                cursor.execute(sql, prepare=False)
            connection.execute(text("INSERT INTO smartsauda.schema_migrations(version, sha256) VALUES (:version, :sha)"),
                               {"version": path.stem, "sha": checksum})


def seed_catalog(factory, predictor):
    with factory.begin() as db:
        if db.bind.dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(746281900)"))
        insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
        for kind in ("Car", "Bike", "Scooter"):
            rows = [dict(vehicle_type=kind, model_version=predictor.version, **entry) for entry in predictor.catalog(kind)]
            if rows:
                stmt = insert(CatalogEntry).values(rows)
                db.execute(stmt.on_conflict_do_update(
                    index_elements=["vehicle_type", "brand", "model", "model_version"],
                    set_={field: getattr(stmt.excluded, field) for field in ('training_rows', 'min_year', 'max_year', 'constraints')}))
