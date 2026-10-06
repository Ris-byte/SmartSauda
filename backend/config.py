from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    database_url: SecretStr
    migration_database_url: SecretStr | None = None
    app_secret: SecretStr
    app_env: Literal["development", "production", "test"] = "development"
    allowed_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://127.0.0.1:8000", "http://localhost:8000"]
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "testserver"]
    carsxe_api_key: SecretStr = SecretStr("")
    free_vehicle_photos: bool = True
    carimages_api_key: SecretStr = SecretStr("")
    carimages_api_secret: SecretStr = SecretStr("")
    image_download_hosts: list[str] = []
    session_hours: int = 8
    frontend_dist: Path | None = None

    @model_validator(mode="after")
    def secure_configuration(self):
        if len(self.app_secret.get_secret_value()) < 32:
            raise ValueError("APP_SECRET must contain at least 32 random characters")
        url = make_url(self.database_url.get_secret_value())
        if self.app_env == "test" and url.get_backend_name() == "sqlite":
            return self
        if url.get_backend_name() not in {"postgres", "postgresql"}:
            raise ValueError("DATABASE_URL must use PostgreSQL")
        if not url.host or not url.password:
            raise ValueError("DATABASE_URL needs a host and password")
        if url.host not in {"localhost", "127.0.0.1", "::1"} and url.query.get("sslmode") not in {"require", "verify-ca", "verify-full"}:
            raise ValueError("Remote PostgreSQL requires sslmode=require or certificate verification")
        if not 1 <= self.session_hours <= 24:
            raise ValueError("SESSION_HOURS must be between 1 and 24")
        if self.app_env == "production":
            if not self.allowed_origins or any(not item.startswith("https://") for item in self.allowed_origins):
                raise ValueError("Production requires explicit HTTPS ALLOWED_ORIGINS")
            if "*" in self.allowed_hosts or "*" in self.allowed_origins:
                raise ValueError("Production must not use wildcard origins/hosts")
        return self

    @property
    def cookie_name(self):
        return "__Host-smartsauda_session" if self.app_env == "production" else "smartsauda_session"
