import hmac
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyCookie
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.gzip import GZipMiddleware

from backend.config import Settings
from backend.db import AuthSession, CatalogEntry, Prediction, User, aware, make_engine, now, sessions
from backend.images import ImageService
from backend.reports import prediction_pdf
from backend.vehicle_photos import generic_photo, local_photo_bytes
from backend.schemas import AccountStatus, Login, PasswordChange, PredictionRequest, Profile, Register, VehicleType
from backend.security import DUMMY_HASH, csrf_token, digest, fail, passwords, throttle
from ml.features import FEATURES, TYPE_NAMES
from ml.predict import PredictionInputError, PricePredictor
from ml.market_support import public_market_status, require_public_market_support
from ml.multisite_car import MultiSiteCarPredictor


def user_view(user):
    return {"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role,
            "active": user.active, "created_at": aware(user.created_at).isoformat()}


def image_view(metadata, identifier):
    if metadata.get("provider") == "carimages":
        return dict(metadata, url=f"/api/v1/predictions/{identifier}/photo")
    return metadata


def prediction_view(row):
    visible_result_fields = {"schema_version", "model_version", "vehicle_type", "market", "currency",
                             "predicted_price", "valuation_year", "vehicle_age", "brand_model_fit_rows",
                             "is_extrapolation", "ignored_input_fields", "warnings", "inference_ms", "reference_year"}
    result = {key: value for key, value in row.result.items() if key in visible_result_fields}
    return {"id": row.id, "created_at": aware(row.created_at).isoformat(), "specifications": row.specifications,
            "result": result, "image": image_view(row.image, row.id)}


class RequestLimits:
    """Bound actual body bytes, including chunked requests, before JSON parsing."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        chunks, total = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            total += len(message.get("body", b""))
            if total > 32768:
                return await JSONResponse({"error": {"code": "body_too_large", "message": "Request exceeds 32 KB."}}, 413)(scope, receive, send)
            chunks.append(message.get("body", b""))
            if not message.get("more_body"):
                break
        consumed = False
        async def replay():
            nonlocal consumed
            if consumed:
                return await receive()
            consumed = True
            return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
        await self.app(scope, replay, send)


def create_app(settings=None, engine=None, predictor=None, image_client=None):
    settings = settings or Settings()
    engine = engine or make_engine(settings)
    factory = sessions(engine)
    predictor = predictor or PricePredictor()
    car_predictor = MultiSiteCarPredictor()
    images = ImageService(settings, factory, image_client)
    # HTTPX's INFO request logging would include CarsXE's query-string API key.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    @asynccontextmanager
    async def lifespan(app):
        for kind in TYPE_NAMES:
            predictor.catalog(kind)
        yield
        images.close()
        engine.dispose()

    app = FastAPI(title="SmartSauda API", version="1.0.0", lifespan=lifespan,
                  docs_url=None if settings.app_env == "production" else "/docs",
                  redoc_url=None if settings.app_env == "production" else "/redoc",
                  openapi_url=None if settings.app_env == "production" else "/openapi.json",
                  description="Nepal vehicle valuations. Cookie sessions; obtain csrf_token from login or /auth/me and send X-CSRF-Token on authenticated mutations.")
    app.state.settings, app.state.engine, app.state.sessions = settings, engine, factory
    app.state.predictor, app.state.car_predictor, app.state.images = predictor, car_predictor, images
    app.add_middleware(RequestLimits)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True,
                       allow_methods=["GET", "POST", "PATCH"], allow_headers=["Content-Type", "X-CSRF-Token"])

    @app.middleware("http")
    async def browser_security(request, call_next):
        if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
            origin = request.headers.get("origin")
            if origin and origin not in settings.allowed_origins:
                return JSONResponse({"error": {"code": "origin_rejected", "message": "Origin is not allowed."}}, 403)
            if request.headers.get("content-type", "").split(";")[0] != "application/json":
                return JSONResponse({"error": {"code": "content_type", "message": "Use application/json."}}, 415)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        elif request.url.path.startswith("/assets/") and response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif request.url.path.startswith("/images/") and response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=3600"
        else:
            response.headers.setdefault("Cache-Control", "no-cache")
        response.headers["X-Frame-Options"] = "DENY"
        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' https:; font-src 'self'; connect-src 'self'; "
                "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
            )
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": "request_error", "message": str(exc.detail)}
        return JSONResponse({"error": detail}, exc.status_code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        if request.url.path == '/api/v1/predictions':
            issues = [{'field': str(e['loc'][-1]), 'type': e['type'], 'message': e['msg']} for e in exc.errors()]
            first = exc.errors()[0]
            message = f"{first['loc'][-1]}={str(first.get('input', ''))[:160]!r}: {first['msg']}"
            return JSONResponse({'error': {'code': 'validation_error', 'message': message, 'fields': issues}}, 422)
        return JSONResponse({"error": {"code": "validation_error", "message": "Check the submitted fields.",
                             "fields": [{"field": ".".join(map(str, item["loc"])), "type": item["type"]} for item in exc.errors()]}}, 422)

    @app.exception_handler(PredictionInputError)
    async def prediction_error(request, exc):
        return JSONResponse({"error": {"code": exc.code, "message": str(exc),
                             "fields": [{"field": exc.field, "type": exc.code, "message": str(exc)}] if exc.field else []}}, 422)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        # Do not log exception strings: connection URLs and SQL data may contain secrets.
        return JSONResponse({"error": {"code": "database_unavailable", "message": "Database operation unavailable."}}, 503)

    @app.exception_handler(Exception)
    async def unexpected_error(request, exc):
        return JSONResponse({"error": {"code": "internal_error", "message": "The request could not be completed."}}, 500)

    def database():
        with factory() as db:
            yield db
    DB = Annotated[Session, Depends(database)]

    session_cookie = APIKeyCookie(name=settings.cookie_name, auto_error=False)

    def current_user(request: Request, db: DB, token: Annotated[str | None, Depends(session_cookie)]):
        if not token or len(token) > 200:
            fail(401, "unauthenticated", "Sign in to continue.")
        session = db.get(AuthSession, digest(token))
        if not session or aware(session.expires_at) <= now():
            fail(401, "unauthenticated", "Sign in to continue.")
        user = db.get(User, session.user_id)
        if not user or not user.active:
            fail(401, "unauthenticated", "Sign in to continue.")
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if not hmac.compare_digest(request.headers.get("x-csrf-token", "").encode(), csrf_token(settings, token).encode()):
                fail(403, "csrf_rejected", "A valid CSRF token is required.")
        return user
    CurrentUser = Annotated[User, Depends(current_user)]

    def admin_user(user: CurrentUser):
        if user.role != "Admin":
            fail(403, "forbidden", "Administrator access is required.")
        return user
    Admin = Annotated[User, Depends(admin_user)]

    def rate(request, scope, limit, seconds, subject=None):
        subject = subject or (request.client.host if request.client else "unknown")
        throttle(factory, settings, scope, subject, limit, seconds)

    def own_prediction(db, identifier, user):
        row = db.scalar(select(Prediction).where(Prediction.id == str(identifier), Prediction.user_id == user.id))
        if row is None:
            fail(404, "not_found", "Prediction not found.")
        return row

    router = APIRouter(prefix="/api/v1")

    @router.get("/health/live", tags=["Health"])
    def live():
        return {"data": {"status": "alive"}}

    @router.get("/health/ready", tags=["Health"])
    def ready(db: DB):
        db.execute(select(User.id).limit(1))
        for kind in TYPE_NAMES:
            predictor.catalog(kind)
            if not db.scalar(select(func.count()).select_from(CatalogEntry).where(
                CatalogEntry.vehicle_type == kind, CatalogEntry.model_version == predictor.version)):
                fail(503, "catalog_unavailable", "Run the database migration and catalog seed.")
        return {"data": {"status": "ready", "model_version": predictor.version}}

    @router.post("/auth/register", status_code=201, tags=["Auth"])
    def register(payload: Register, request: Request, db: DB):
        rate(request, "register", 5, 3600)
        row = User(email=payload.email, display_name=payload.display_name, password_hash=passwords.hash(payload.password), role="User")
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            fail(409, "registration_unavailable", "Unable to register these details. Try signing in.")
        return {"data": user_view(row)}

    @router.post("/auth/login", tags=["Auth"])
    def login(payload: Login, request: Request, response: Response, db: DB):
        rate(request, "login", 10, 60)
        rate(request, "login_account", 30, 3600, payload.email)
        user = db.scalar(select(User).where(User.email == payload.email).with_for_update())
        valid = passwords.verify(payload.password, user.password_hash if user else DUMMY_HASH)
        if not valid or not user or not user.active:
            fail(401, "invalid_credentials", "Invalid email or password.")
        old_token = request.cookies.get(settings.cookie_name)
        if old_token:
            db.execute(delete(AuthSession).where(AuthSession.token_digest == digest(old_token)))
        db.execute(delete(AuthSession).where(AuthSession.expires_at <= now()))
        token = secrets.token_urlsafe(48)
        db.add(AuthSession(token_digest=digest(token), user_id=user.id, expires_at=now() + timedelta(hours=settings.session_hours)))
        db.commit()
        response.set_cookie(settings.cookie_name, token, httponly=True, secure=settings.app_env == "production",
                            samesite="lax", max_age=settings.session_hours * 3600, path="/")
        return {"data": {"user": user_view(user), "csrf_token": csrf_token(settings, token)}}

    @router.get("/auth/me", tags=["Auth"])
    def me(request: Request, user: CurrentUser):
        return {"data": {"user": user_view(user), "csrf_token": csrf_token(settings, request.cookies[settings.cookie_name])}}

    @router.post("/auth/logout", tags=["Auth"])
    def logout(request: Request, response: Response, user: CurrentUser, db: DB):
        db.execute(delete(AuthSession).where(AuthSession.token_digest == digest(request.cookies[settings.cookie_name])))
        db.commit()
        response.delete_cookie(settings.cookie_name, path="/", secure=settings.app_env == "production", httponly=True, samesite="lax")
        return {"data": {"signed_out": True}}

    @router.patch("/profile", tags=["Profile"])
    def profile(payload: Profile, user: CurrentUser, db: DB):
        user.display_name = payload.display_name
        db.commit()
        return {"data": user_view(user)}

    @router.post("/profile/password", tags=["Profile"])
    def password_change(payload: PasswordChange, request: Request, response: Response, user: CurrentUser, db: DB):
        rate(request, "password", 5, 3600, user.id)
        db.refresh(user, with_for_update=True)
        if not passwords.verify(payload.current_password, user.password_hash):
            fail(400, "invalid_password", "Current password is incorrect.")
        user.password_hash = passwords.hash(payload.new_password)
        db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
        db.commit()
        response.delete_cookie(settings.cookie_name, path="/", secure=settings.app_env == "production", httponly=True, samesite="lax")
        return {"data": {"sign_in_required": True}}

    @router.get("/catalog", tags=["Catalog"])
    def catalog():
        return {"data": {"vehicle_types": TYPE_NAMES, "model_version": predictor.version, "features": FEATURES,
                         "vehicle_model_versions": {"Car": car_predictor.version, "Bike": predictor.version, "Scooter": predictor.version},
                         "market": "Nepal", "currency": "NPR"}}

    @router.get('/market-status', tags=['Catalog'])
    def market_status(vehicle_type: VehicleType):
        return {'data': public_market_status(vehicle_type)}

    @router.get("/catalog/brands", tags=["Catalog"])
    def brands(vehicle_type: VehicleType, db: DB):
        if vehicle_type == "Car":
            return {"data": sorted({entry["brand"] for entry in car_predictor.catalog("Car")}, key=str.casefold)}
        values = db.scalars(select(CatalogEntry.brand).where(CatalogEntry.vehicle_type == vehicle_type,
                            CatalogEntry.model_version == predictor.version).distinct().order_by(CatalogEntry.brand)).all()
        return {"data": values}

    @router.get("/catalog/models", tags=["Catalog"])
    def models(vehicle_type: VehicleType, brand: Annotated[str, Query(min_length=1, max_length=160)], db: DB):
        if vehicle_type == "Car":
            return {"data": [{"model": entry["model"], "training_rows": entry["training_rows"],
                              "min_year": entry["min_year"], "max_year": entry["max_year"],
                              "constraints": entry["constraints"]}
                             for entry in car_predictor.catalog("Car") if entry["brand"].casefold() == brand.casefold()]}
        rows = db.scalars(select(CatalogEntry).where(CatalogEntry.vehicle_type == vehicle_type,
                          func.lower(CatalogEntry.brand) == brand.casefold(), CatalogEntry.model_version == predictor.version).order_by(CatalogEntry.model)).all()
        supported = {entry['model']: entry for entry in predictor.catalog(vehicle_type)
                     if entry['brand'].casefold() == brand.casefold()}
        return {"data": [{"model": row.model, "training_rows": row.training_rows, "min_year": row.min_year,
                          "max_year": row.max_year, "constraints": supported[row.model]['constraints']}
                         for row in rows if row.model in supported]}

    @router.post("/predictions", status_code=201, tags=["Predictions"])
    def predict(payload: PredictionRequest, request: Request, user: CurrentUser, db: DB):
        rate(request, "predict", 20, 60, user.id)
        payload = payload.model_dump(exclude_unset=True)
        require_public_market_support(payload)
        active_predictor = car_predictor if payload["vehicle_type"] == "Car" else predictor
        result = active_predictor.predict(payload)
        specs = dict(payload)
        entry = next(e for e in active_predictor.catalog(result['vehicle_type']) if
                     e['brand'].casefold() == payload['brand'].casefold() and e['model'].casefold() == payload['model'].casefold())
        specs.update(vehicle_type=result["vehicle_type"], brand=entry['brand'], model=entry['model'])
        image = images.resolve(specs)
        row = Prediction(user_id=user.id, vehicle_type=result["vehicle_type"], brand=specs["brand"], model=specs["model"],
                         model_version=result["model_version"], price=Decimal(str(result["predicted_price"])),
                         specifications=specs, result=result, image=image)
        db.add(row)
        db.commit()
        return {"data": prediction_view(row)}

    @router.get("/predictions", tags=["Predictions"])
    def history(user: CurrentUser, db: DB, vehicle_type: VehicleType | None = None,
                search: Annotated[str | None, Query(max_length=160)] = None,
                date_from: datetime | None = None, date_to: datetime | None = None,
                limit: Annotated[int, Query(ge=1, le=100)] = 20, offset: Annotated[int, Query(ge=0, le=100000)] = 0):
        if date_from and date_to and aware(date_from) > aware(date_to):
            fail(422, "invalid_dates", "date_from must precede date_to.")
        filters = [Prediction.user_id == user.id]
        if vehicle_type:
            filters.append(Prediction.vehicle_type == vehicle_type)
        if search:
            filters.append(or_(Prediction.brand.icontains(search, autoescape=True), Prediction.model.icontains(search, autoescape=True)))
        if date_from:
            filters.append(Prediction.created_at >= aware(date_from))
        if date_to:
            filters.append(Prediction.created_at <= aware(date_to))
        count = db.scalar(select(func.count()).select_from(Prediction).where(*filters))
        rows = db.scalars(select(Prediction).where(*filters).order_by(Prediction.created_at.desc(), Prediction.id).limit(limit).offset(offset)).all()
        return {"data": {"items": [prediction_view(row) for row in rows], "total": count, "limit": limit, "offset": offset}}

    @router.get("/predictions/{prediction_id}", tags=["Predictions"])
    def prediction_detail(prediction_id: UUID, user: CurrentUser, db: DB):
        row = own_prediction(db, prediction_id, user)
        view = prediction_view(row)
        if row.image.get("is_placeholder") or row.image.get("provider") == "commons":
            view["image"] = image_view(images.resolve(row.specifications), row.id)
        return {"data": view}

    @router.get("/predictions/{prediction_id}/image", tags=["Images"])
    def prediction_image(prediction_id: UUID, request: Request, user: CurrentUser, db: DB):
        row = own_prediction(db, prediction_id, user)
        rate(request, "image", 20, 60, user.id)
        # A fresh display lookup does not mutate the original saved report snapshot.
        return {"data": image_view(images.resolve(row.specifications), row.id)}

    @router.get("/predictions/{prediction_id}/photo", tags=["Images"])
    def prediction_photo(prediction_id: UUID, request: Request, user: CurrentUser, db: DB):
        row = own_prediction(db, prediction_id, user)
        rate(request, "photo", 30, 60, user.id)
        blob = images.render(row.specifications)
        if blob is None:
            fail(503, "photo_unavailable", "Model image unavailable; use the supplied real-photo alternative.")
        return Response(blob, media_type="image/webp", headers={"Cache-Control": "private, max-age=300"})

    @router.get("/predictions/{prediction_id}/report.pdf", tags=["Reports"])
    def report(prediction_id: UUID, request: Request, user: CurrentUser, db: DB):
        row = own_prediction(db, prediction_id, user)
        require_public_market_support({'vehicle_type': row.vehicle_type})
        rate(request, "report", 10, 60, user.id)
        metadata = images.resolve(row.specifications) if row.image.get("is_placeholder") or row.image.get("provider") == "commons" else row.image
        photo = images.render(row.specifications) if metadata.get("provider") == "carimages" else None
        if metadata.get("provider") == "carimages" and photo is None:
            metadata = metadata.get("fallback_photo", generic_photo(row.vehicle_type))
        return Response(prediction_pdf(row, settings, metadata, photo), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="smartsauda-{row.id}.pdf"'})

    @router.get("/assets/vehicles/{filename}", tags=["Images"])
    def asset(filename: str):
        metadata_kind = {"car.json": "Car", "bike.json": "Bike", "scooter.json": "Scooter"}.get(filename)
        if metadata_kind:
            return {"data": generic_photo(metadata_kind)}
        photo_kind = {"car.jpg": "Car", "bike.jpg": "Bike", "scooter.jpg": "Scooter"}.get(filename)
        if photo_kind:
            return Response(local_photo_bytes(generic_photo(photo_kind)), media_type="image/jpeg",
                            headers={"Cache-Control": "public, max-age=86400"})
        fail(404, "not_found", "Image not found.")

    @router.get("/dashboard", tags=["Dashboard"])
    def dashboard(user: CurrentUser, db: DB):
        counts = dict(db.execute(select(Prediction.vehicle_type, func.count()).where(Prediction.user_id == user.id).group_by(Prediction.vehicle_type)).all())
        average, low, high = db.execute(select(func.avg(Prediction.price), func.min(Prediction.price), func.max(Prediction.price)).where(Prediction.user_id == user.id)).one()
        if counts.get('Car', 0):
            average, low, high = None, None, None
        recent = db.scalars(select(Prediction).where(Prediction.user_id == user.id).order_by(Prediction.created_at.desc(), Prediction.id).limit(5)).all()
        return {"data": {"total_predictions": sum(counts.values()), "by_type": {kind: counts.get(kind, 0) for kind in TYPE_NAMES},
                         "currency": "NPR", "average_price": round(float(average), 2) if average is not None else None,
                         "lowest_price": float(low) if low is not None else None, "highest_price": float(high) if high is not None else None,
                         "recent": [prediction_view(row) for row in recent]}}

    @router.get("/admin/users", tags=["Admin"])
    def users(user: Admin, db: DB, limit: Annotated[int, Query(ge=1, le=100)] = 20, offset: Annotated[int, Query(ge=0, le=100000)] = 0):
        rows = db.scalars(select(User).order_by(User.created_at, User.id).limit(limit).offset(offset)).all()
        return {"data": {"items": [user_view(row) for row in rows], "total": db.scalar(select(func.count()).select_from(User))}}

    @router.patch("/admin/users/{user_id}/status", tags=["Admin"])
    def account_status(user_id: UUID, payload: AccountStatus, user: Admin, db: DB):
        # Serialize changes to the admin set so concurrent requests cannot disable all admins.
        if db.bind.dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(746281901)"))
        row = db.scalar(select(User).where(User.id == str(user_id)).with_for_update())
        if row is None:
            fail(404, "not_found", "User not found.")
        if row.id == user.id and not payload.active:
            fail(409, "self_disable", "You cannot disable your current account.")
        if row.role == "Admin" and not payload.active:
            # Serialize administrator deactivation so concurrent requests cannot
            # both observe two active administrators and disable the last pair.
            db.execute(select(User.id).where(User.role == "Admin").order_by(User.id).with_for_update()).all()
            count = db.scalar(select(func.count()).select_from(User).where(User.role == "Admin", User.active.is_(True)))
            if count <= 1:
                fail(409, "last_admin", "The last active administrator must remain enabled.")
        row.active = payload.active
        if not payload.active:
            db.execute(delete(AuthSession).where(AuthSession.user_id == row.id))
        db.commit()
        return {"data": user_view(row)}

    @router.get("/admin/stats", tags=["Admin"])
    def admin_stats(user: Admin, db: DB):
        return {"data": {"users": db.scalar(select(func.count()).select_from(User)),
                         "active_users": db.scalar(select(func.count()).select_from(User).where(User.active.is_(True))),
                         "predictions": db.scalar(select(func.count()).select_from(Prediction))}}

    app.include_router(router)
    if settings.frontend_dist is not None:
        from backend.frontend import install_frontend
        install_frontend(app, settings.frontend_dist)
    return app
