"""Shared deterministic feature construction for fitting and inference."""
from __future__ import annotations

import hashlib
import re

import numpy as np
import pandas as pd

FEATURE_VERSION = "1.0"
TYPE_NAMES = ("Car", "Bike", "Scooter")
COMMON_NUMERIC = ["vehicle_age", "km_driven", "km_per_year", "engine_capacity_cc"]
FEATURES = {
    "Car": {"numeric": [*COMMON_NUMERIC, "owner_count"],
            "categorical": ["brand", "model", "region", "fuel_type", "transmission", "condition", "body_type"]},
    "Bike": {"numeric": COMMON_NUMERIC.copy(), "categorical": ["brand", "model"]},
    "Scooter": {"numeric": [*COMMON_NUMERIC, "motor_power_kw"], "categorical": ["brand", "model"]},
}
FORBIDDEN_FEATURES = {"price", "log_price", "record_id", "source_id", "source_row", "source_sha256",
                      "provenance", "price_basis", "reference_year", "training_eligible", "quality_flags"}


def canonical_text(value):
    if value is None or pd.isna(value):
        return np.nan
    result = " ".join(str(value).strip().casefold().split())
    return result or np.nan


def feature_frame(rows: pd.DataFrame, vehicle_type: str) -> pd.DataFrame:
    """Derive age from each row's explicit audit year, never from cached target columns."""
    spec = FEATURES[vehicle_type]
    frame = rows.copy()
    for field in ("manufacture_year", "reference_year", "km_driven", "engine_capacity_cc", "owner_count", "motor_power_kw"):
        frame[field] = pd.to_numeric(frame[field], errors="raise") if field in frame else np.nan
    frame["vehicle_age"] = frame["reference_year"] - frame["manufacture_year"]
    frame["km_per_year"] = frame["km_driven"].div(frame["vehicle_age"].where(frame["vehicle_age"] > 0))
    for field in spec["categorical"]:
        frame[field] = frame[field].map(canonical_text) if field in frame else np.nan
    selected = [*spec["numeric"], *spec["categorical"]]
    if FORBIDDEN_FEATURES.intersection(selected):
        raise AssertionError("Target or audit metadata leaked into feature specification")
    return frame[selected]


def duplicate_group(row, km_bucket=1000):
    """Keep likely repeats together even if price, source or optional specs differ."""
    clean = lambda value: re.sub(r"[^a-z0-9]", "", str(value).casefold())
    distance_bucket = int(np.floor(float(row["km_driven"]) / km_bucket + .5))
    key = "|".join([row["vehicle_type"], clean(row["brand"]), clean(row["model"]),
                    str(int(row["manufacture_year"])), str(distance_bucket)])
    return hashlib.sha256(key.encode()).hexdigest()[:24]
