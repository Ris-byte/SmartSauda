"""On-demand representative photos, bounded fetching, and explicit local fallbacks."""
import hashlib
import http.client
import ipaddress
import json
import socket
import ssl
from datetime import timedelta
from io import BytesIO
from time import monotonic
from threading import Lock
from urllib.parse import urlsplit

import httpx
from PIL import Image
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.db import ImageCache, aware, now
from backend.vehicle_photos import resolve_photo, reviewed_photo, generic_photo, local_photo_bytes
from backend.carimages import fetch_render, resolve_catalog_model


def placeholder(kind, reason="not_configured"):
    return {"provider": "local", "is_placeholder": True, "url": f"/api/v1/assets/vehicles/{kind.lower()}.jpg",
            "attribution_url": None, "reason": reason}


def safe_url(value):
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c) < 33 for c in value):
        return False
    try:
        part = urlsplit(value)
        return part.scheme == "https" and bool(part.hostname) and not part.username and not part.password and part.port in (None, 443)
    except ValueError:
        return False


class ImageService:
    def __init__(self, settings, factory, client=None):
        self.settings, self.factory = settings, factory
        self.client = client or httpx.Client(timeout=4, follow_redirects=False, trust_env=False)
        self._renders = {}
        self._render_lock = Lock()

    def close(self):
        self.client.close()

    def resolve(self, specs):
        kind = specs["vehicle_type"]
        if (self.settings.carimages_api_key.get_secret_value()
                and self.settings.carimages_api_secret.get_secret_value()):
            return {"provider": "carimages", "is_placeholder": False, "url": "",
                    "match_kind": "render", "depicted_model": f"{specs['brand']} {specs['model']}",
                    "title": "Representative studio render", "author": "CarImages",
                    "attribution_url": "https://carimagesapi.com/", "license": "Free tier (watermarked)",
                    "license_url": "https://carimagesapi.com/docs", "fallback_photo": resolve_photo(specs)}
        secret = self.settings.carsxe_api_key.get_secret_value()
        if not secret:
            if self.settings.free_vehicle_photos:
                return resolve_photo(specs)
            return placeholder(kind)
        signature = ["carsxe-v1-ShareCommercially", hashlib.sha256(secret.encode()).hexdigest(), kind,
                     specs["brand"].casefold(), specs["model"].casefold(), specs["manufacture_year"]]
        key = hashlib.sha256(json.dumps(signature).encode()).hexdigest()
        with self.factory() as db:
            hit = db.get(ImageCache, key)
            if hit and aware(hit.expires_at) > now():
                return hit.value
        try:
            with self.client.stream("GET", "https://api.carsxe.com/images", params={
                "key": secret, "make": specs["brand"], "model": specs["model"],
                "year": specs["manufacture_year"], "license": "ShareCommercially", "transparent": "false",
            }) as response:
                if response.status_code != 200:
                    return placeholder(kind, "provider_unavailable")
                raw = bytearray()
                start = monotonic()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 256_000 or monotonic() - start > 5:
                        return placeholder(kind, "invalid_response")
                data = json.loads(raw)
            if not isinstance(data, dict) or data.get("success") is not True or not isinstance(data.get("images"), list):
                return placeholder(kind, "invalid_response")
            for item in data["images"][:30]:
                if not isinstance(item, dict):
                    continue
                link, source = item.get("link"), item.get("contextLink")
                if safe_url(link) and safe_url(source) and secret not in link and secret not in source:
                    value = {"provider": "carsxe", "is_placeholder": False, "url": link,
                             "attribution_url": source, "license_filter": "ShareCommercially",
                             "note": "Representative image; check the linked source's license and attribution."}
                    with self.factory.begin() as db:
                        insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
                        stmt = insert(ImageCache).values(key=key, value=value, expires_at=now() + timedelta(hours=6))
                        db.execute(stmt.on_conflict_do_update(index_elements=[ImageCache.key],
                                   set_={"value": stmt.excluded.value, "expires_at": stmt.excluded.expires_at}))
                    return value
            return placeholder(kind, "no_match")
        except (httpx.HTTPError, ValueError, TypeError):
            return placeholder(kind, "provider_unavailable")

    def render(self, specs):
        # A bounded five-minute memory cache avoids repeat quota usage. No blobs in DB.
        key = tuple(specs.get(k) for k in ("vehicle_type", "brand", "model", "manufacture_year"))
        with self._render_lock:
            hit = self._renders.get(key)
            if hit and hit[0] > monotonic():
                return hit[1]
            api_key = self.settings.carimages_api_key.get_secret_value()
            api_secret = self.settings.carimages_api_secret.get_secret_value()
            catalog = resolve_catalog_model(specs, api_key, api_secret, self.client)
            blob = None
            if catalog:
                exact_specs = {**specs, "brand": catalog["make"], "model": catalog["model"]}
                blob = fetch_render(exact_specs, api_key, self.client, expected_slug=catalog["slug"])
            if len(self._renders) >= 32:
                self._renders.pop(next(iter(self._renders)))
            self._renders[key] = (monotonic() + (300 if blob else 30), blob)
            return blob


def fetch_report_image(metadata, allowed_hosts):
    """Only reviewed hosts; pin the public IP while preserving TLS hostname validation."""
    local = local_photo_bytes(metadata)
    if local:
        return local
    url = metadata.get("url")
    if metadata.get("is_placeholder") or not safe_url(url):
        return None
    part = urlsplit(url)
    if part.hostname not in allowed_hosts and not reviewed_photo(metadata):
        return None
    connection = None
    try:
        addresses = {row[4][0] for row in socket.getaddrinfo(part.hostname, 443, type=socket.SOCK_STREAM)}
        if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
            return None
        # DNS is not consulted again during the connection (prevents rebinding).
        address = sorted(addresses)[0]
        connection = http.client.HTTPSConnection(part.hostname, timeout=4, context=ssl.create_default_context())
        plain = socket.create_connection((address, 443), timeout=4)
        try:
            connection.sock = ssl.create_default_context().wrap_socket(plain, server_hostname=part.hostname)
        except Exception:
            plain.close()
            raise
        path = part.path or "/"
        if part.query:
            path += "?" + part.query
        connection.request("GET", path, headers={"User-Agent": "SmartSauda-report/1.0", "Accept": "image/jpeg,image/png"})
        response = connection.getresponse()
        if response.status != 200 or response.getheader("Content-Type", "").split(";")[0].lower() not in {"image/jpeg", "image/png"}:
            return None
        if int(response.getheader("Content-Length", "0")) > 2_000_000:
            return None
        chunks, total, start = [], 0, monotonic()
        while chunk := response.read1(65536):
            chunks.append(chunk)
            total += len(chunk)
            if total > 2_000_000 or monotonic() - start > 5:
                return None
        blob = b"".join(chunks)
        with Image.open(BytesIO(blob)) as photo:
            if photo.format not in {"PNG", "JPEG"} or photo.width * photo.height > 8_000_000:
                return None
            photo.verify()
        return blob
    except (OSError, ValueError, http.client.HTTPException, Image.DecompressionBombError):
        return None
    finally:
        if connection is not None:
            connection.close()

