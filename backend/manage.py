"""Run from the project root: python -m backend.manage --help."""
import argparse
import getpass
import json
import secrets
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from backend.config import ROOT, Settings
from backend.db import User, make_engine, sessions
from backend.migrations import migrate, seed_catalog
from backend.schemas import Register
from backend.security import passwords
from ml.predict import PricePredictor


def init_env():
    path = ROOT / ".env"
    if path.exists():
        print(".env already exists; left unchanged.")
        return
    template = (ROOT / ".env.example").read_text(encoding="utf-8")
    template = template.replace("replace-with-a-random-secret", secrets.token_urlsafe(48))
    with path.open("x", encoding="utf-8") as output:
        output.write(template)
    print("Created ignored .env with a random APP_SECRET. Set DATABASE_URL locally.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init-env", "migrate", "check", "provision-runtime", "create-admin", "export-openapi"])
    args = parser.parse_args()
    if args.command == "init-env":
        init_env()
        return
    try:
        settings = Settings()
    except (ValidationError, ValueError):
        parser.exit(2, "Invalid configuration. Check .env against .env.example; values are intentionally hidden.\n")
    management_settings = settings
    if args.command in {"migrate", "check", "provision-runtime"} and settings.migration_database_url:
        management_settings = settings.model_copy(update={"database_url": settings.migration_database_url})
    engine = make_engine(management_settings)
    factory = sessions(engine)
    try:
        if args.command == "migrate":
            migrate(engine)
            seed_catalog(factory, PricePredictor())
            print("PostgreSQL migrations applied; catalog seeded.")
        elif args.command == "provision-runtime":
            from backend.provision import provision_runtime
            print(provision_runtime(engine, settings))
        elif args.command == "check":
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                versions = connection.execute(text("SELECT version FROM smartsauda.schema_migrations ORDER BY version")).scalars().all()
            print(json.dumps({"database": "connected", "migrations": versions, "credentials": "hidden"}))
        elif args.command == "create-admin":
            email = input("Admin email: ")
            name = input("Display name: ")
            password = getpass.getpass("Password (12+ characters): ")
            if password != getpass.getpass("Confirm password: "):
                parser.exit(2, "Passwords do not match.\n")
            try:
                payload = Register(email=email, display_name=name, password=password)
            except ValidationError:
                parser.exit(2, "Invalid email, name or password length.\n")
            with factory.begin() as db:
                if db.scalar(select(User).where(User.email == payload.email)):
                    parser.exit(2, "Account already exists; no role change made.\n")
                db.add(User(email=payload.email, display_name=payload.display_name, password_hash=passwords.hash(payload.password), role="Admin"))
            print("Admin created. No default credentials were used.")
        elif args.command == "export-openapi":
            from backend.app import create_app
            app = create_app(settings, engine)
            target = ROOT / "docs" / "openapi.json"
            target.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
            app.state.images.close()
            print("Wrote docs/openapi.json")
    except (SQLAlchemyError, RuntimeError):
        parser.exit(2, "Database/model operation failed. Check connectivity, permissions, migration integrity and model versions. Credentials are hidden.\n")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
