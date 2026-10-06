"""Reviewed real-photo registry; no catalog-wide image download at runtime."""
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PHOTOS = json.loads((ROOT / "vehicle_photos.json").read_text(encoding="utf-8"))
GENERIC_IDS = {"Car": "pexels-5613885", "Bike": "pexels-10327107", "Scooter": "pexels-17752702"}


def metadata(photo, match_kind):
    return dict({k: deepcopy(v) for k, v in photo.items() if k not in {"brand", "models", "vehicle_type"}},
                is_placeholder=False, match_kind=match_kind,
                note="Representative image; year, variant and condition may differ.")


def generic_photo(kind):
    photo = next(p for p in PHOTOS if p["id"] == GENERIC_IDS[kind])
    result = metadata(photo, "category")
    result["url"] = f"/api/v1/assets/vehicles/{kind.lower()}.jpg"
    return result


def resolve_photo(specs):
    for photo in PHOTOS:
        if (photo["vehicle_type"] == specs["vehicle_type"] and
            photo["brand"].casefold() == specs["brand"].strip().casefold() and
            specs["model"].strip().casefold() in [m.casefold() for m in photo["models"]]):
            return dict(metadata(photo, "model"), fallback_photo=generic_photo(specs["vehicle_type"]))
    return generic_photo(specs["vehicle_type"])


def reviewed_photo(value):
    fields = ("url", "attribution_url", "author", "license", "license_url", "title", "depicted_model", "provider")
    return any(all(value.get(field) == photo[field] for field in fields) for photo in PHOTOS)


def local_photo_bytes(value):
    for kind in GENERIC_IDS:
        expected = generic_photo(kind)
        if all(value.get(k) == expected[k] for k in ("url", "id", "author", "license", "attribution_url")):
            return (ROOT / "assets" / "photos" / (kind.lower()+".jpg")).read_bytes()
    return None
