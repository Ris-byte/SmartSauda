import hashlib
import hmac
from datetime import timedelta
from time import time

from fastapi import HTTPException
from pwdlib import PasswordHash
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.db import RateBucket, now

passwords = PasswordHash.recommended()
DUMMY_HASH = passwords.hash("constant-timing-placeholder-password")


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def keyed(settings, value):
    return hmac.new(settings.app_secret.get_secret_value().encode(), value.encode(), hashlib.sha256).hexdigest()


def csrf_token(settings, session_token):
    return keyed(settings, "csrf:" + session_token)


def fail(status, code, message):
    raise HTTPException(status, detail={"code": code, "message": message})


def throttle(factory, settings, scope, subject, limit, seconds):
    window = int(time()) // seconds
    key = keyed(settings, f"rate:{scope}:{subject}:{window}")
    with factory.begin() as db:
        # One atomic UPSERT across all API workers, using its own transaction.
        insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
        stmt = insert(RateBucket).values(key=key, count=1, expires_at=now() + timedelta(seconds=seconds * 2))
        count = db.execute(stmt.on_conflict_do_update(index_elements=[RateBucket.key],
                          set_={"count": RateBucket.count + 1}).returning(RateBucket.count)).scalar_one()
        db.execute(delete(RateBucket).where(RateBucket.expires_at < now()))
    if count > limit:
        raise HTTPException(429, detail={"code": "rate_limited", "message": "Too many requests. Try again later."},
                            headers={"Retry-After": str(seconds - int(time()) % seconds)})
