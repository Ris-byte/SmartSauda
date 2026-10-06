"""Disposable local browser fixture: real API/models, temporary SQLite, no .env."""
import sys
import os
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import uvicorn
from backend.app import create_app
from backend.config import Settings
from backend.db import Base, User, sessions
from sqlalchemy import create_engine, event
from backend.migrations import seed_catalog
from backend.security import passwords
from ml.predict import PricePredictor

port = int(os.environ.get("TEST_PORT", "8001"))
settings = Settings(_env_file=None, database_url="sqlite+pysqlite:///:memory:",
                    app_secret="browser-fixture-only-" * 3, app_env="test",
                    carsxe_api_key="", free_vehicle_photos=False, allowed_hosts=["127.0.0.1", "localhost"],
                    allowed_origins=["http://127.0.0.1:5174", f"http://127.0.0.1:{port}"],
                    frontend_dist=Path(__file__).resolve().parents[1] / "frontend/dist" if os.environ.get("TEST_SERVE_BUILD") else None)
temporary = TemporaryDirectory(prefix="smartsauda-browser-")
engine = create_engine("sqlite+pysqlite:///" + str(Path(temporary.name) / "browser.sqlite"),
                       connect_args={"check_same_thread": False},
                       execution_options={"schema_translate_map": {"smartsauda": None}})
@event.listens_for(engine, "connect")
def sqlite_setup(connection, _):
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA journal_mode=WAL")
Base.metadata.create_all(engine)
factory = sessions(engine)
predictor = PricePredictor()
seed_catalog(factory, predictor)
with factory.begin() as db:
    for email, name, role in [("admin@example.com", "Browser Admin", "Admin"),
                               ("viewer@example.com", "Browser Viewer", "User")]:
        db.add(User(email=email, display_name=name, role=role,
                    password_hash=passwords.hash("Browser-test-only-2026!")))
app = create_app(settings, engine, predictor)

if __name__ == "__main__":
    try:
        uvicorn.run(app, host="127.0.0.1", port=port, proxy_headers=False)
    finally:
        engine.dispose()
        temporary.cleanup()
