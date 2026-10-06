from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, SmallInteger, MetaData, Numeric, String, UniqueConstraint, create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

SCHEMA = "smartsauda"
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


def now():
    return datetime.now(timezone.utc)


def identifier():
    return str(uuid4())


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class Base(DeclarativeBase):
    metadata = MetaData(schema=SCHEMA)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('User', 'Admin')", name="user_role"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(512))
    role: Mapped[str] = mapped_column(String(10), default="User")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuthSession(Base):
    __tablename__ = "sessions"
    token_digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (Index("ix_prediction_owner_time", "user_id", "created_at"), CheckConstraint("price > 0", name="positive_price"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey(f"{SCHEMA}.users.id"))
    vehicle_type: Mapped[str] = mapped_column(String(10))
    brand: Mapped[str] = mapped_column(String(160))
    model: Mapped[str] = mapped_column(String(160))
    model_version: Mapped[str] = mapped_column(String(40))
    price: Mapped[Decimal] = mapped_column(Numeric(24, 2))
    specifications: Mapped[dict] = mapped_column(JSON_TYPE)
    result: Mapped[dict] = mapped_column(JSON_TYPE)
    image: Mapped[dict] = mapped_column(JSON_TYPE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CatalogEntry(Base):
    __tablename__ = "catalog"
    __table_args__ = (UniqueConstraint("vehicle_type", "brand", "model", "model_version", name="catalog_identity"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vehicle_type: Mapped[str] = mapped_column(String(10))
    brand: Mapped[str] = mapped_column(String(160))
    model: Mapped[str] = mapped_column(String(160))
    model_version: Mapped[str] = mapped_column(String(40))
    training_rows: Mapped[int] = mapped_column(Integer)
    min_year: Mapped[int | None] = mapped_column(SmallInteger)
    max_year: Mapped[int | None] = mapped_column(SmallInteger)
    constraints: Mapped[dict | None] = mapped_column(JSON_TYPE)


class RateBucket(Base):
    __tablename__ = "rate_buckets"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ImageCache(Base):
    __tablename__ = "image_cache"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON_TYPE)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


def make_engine(settings):
    url = make_url(settings.database_url.get_secret_value())
    if url.get_backend_name() == "sqlite" and settings.app_env == "test":
        engine = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool,
                               execution_options={"schema_translate_map": {SCHEMA: None}})
        @event.listens_for(engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
        return engine
    url = url.set(drivername="postgresql+psycopg")
    return create_engine(url, pool_pre_ping=True, pool_size=3, max_overflow=2, pool_timeout=10,
                         hide_parameters=True, connect_args={"connect_timeout": 10, "prepare_threshold": None})


def sessions(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)
