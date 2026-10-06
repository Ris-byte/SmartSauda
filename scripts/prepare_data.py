"""Reproducible Phase 1 audit. Standard library only; never trains a model."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_COLUMNS = [
    "region", "vehicle_type", "brand", "model", "year", "km_driven",
    "engine_capacity", "owners", "fuel_type", "transmission", "condition", "price",
]
SPEC_COLUMNS = [
    "vehicle_type", "brand", "model", "manufacture_year", "km_driven",
    "engine_capacity_cc", "owner_count", "fuel_type", "transmission", "condition",
    "region", "city", "insurance_status", "color", "body_type", "seats",
    "power_bhp", "motor_power_kw", "mileage_kmpl", "gears", "location_raw", "listing_condition",
]
COLUMNS = [
    "record_id", "source_id", "source_row", "source_sha256", "market", "currency",
    "provenance", "price_basis", "observation_date", "reference_year", "source_record_key",
    *SPEC_COLUMNS, "price", "vehicle_age", "km_per_year", "log_price",
    "quality_flags", "training_eligible",
]
TYPES = {"car": "Car", "suv": "Car", "bike": "Bike", "scooter": "Scooter"}
ENUMS = {
    "fuel_type": {s.casefold(): s for s in ("Petrol", "Diesel", "Electric", "Hybrid", "CNG", "LPG")},
    "transmission": {s.casefold(): s for s in ("Manual", "Automatic")},
    "condition": {s.casefold(): s for s in ("Excellent", "Good", "Fair", "Poor")},
}
NUMERIC = ["manufacture_year", "km_driven", "engine_capacity_cc", "owner_count", "price"]


def feasibility_quarantine_reason(row):
    suspect = {('bajaj', 'avenger 220 cruise'), ('yamaha', 'fz v1'), ('tvs', 'raider 125')}
    if row.get('manufacture_year') == 1980 and (str(row.get('brand', '')).casefold(), str(row.get('model', '')).casefold()) in suspect:
        return 'suspect_model_year_1980_requires_review'
    return None


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict], columns: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def text(value) -> str:
    return " ".join(str(value or "").split())


def number(value, integer=False):
    # Source declares bare numeric cells, so fail on unrecognised units instead of guessing.
    try:
        result = float(text(value))
    except (ValueError, TypeError):
        return None
    if not math.isfinite(result) or (integer and not result.is_integer()):
        return None
    return int(result) if integer else result


def normalize(raw: dict, row_number: int, source: dict, source_hash: str,
              year: int, rules: dict) -> tuple[dict, list[str]]:
    row = dict.fromkeys(COLUMNS)
    row.update({
        "record_id": f"{source['id']}:{row_number}", "source_id": source["id"],
        "source_row": row_number, "source_sha256": source_hash,
        "market": source["market"], "currency": source["currency"],
        "provenance": source["provenance"], "price_basis": source["price_basis"],
        "observation_date": source["observation_date"], "reference_year": year,
        "brand": text(raw.get("brand")), "model": text(raw.get("model")),
        "region": text(raw.get("region")),
        "vehicle_type": TYPES.get(text(raw.get("vehicle_type")).casefold()),
        "manufacture_year": number(raw.get("year"), integer=True),
        "km_driven": number(raw.get("km_driven")),
        "engine_capacity_cc": number(raw.get("engine_capacity")),
        "owner_count": number(raw.get("owners"), integer=True),
        "price": number(raw.get("price")),
        # This source has no listing provenance, dates, or price-basis evidence.
        "training_eligible": False,
    })
    for field, mapping in ENUMS.items():
        row[field] = mapping.get(text(raw.get(field)).casefold())
    if text(raw.get("vehicle_type")).casefold() == "suv":
        row["body_type"] = "SUV"
    errors = []
    for field in ("vehicle_type", "brand", "model", "region", *ENUMS):
        if not row[field]:
            errors.append(f"missing_or_unknown_{field}")
    for field in NUMERIC:
        if row[field] is None:
            errors.append(f"invalid_{field}")
    bounds = {
        "manufacture_year": (1900, year), "km_driven": (0, None),
        "engine_capacity_cc": (0, None), "owner_count": (1, None),
        "price": (0, None),
    }
    for field, (low, high) in bounds.items():
        value = row[field]
        if value is not None and (value < low or (high is not None and value > high)
                                  or (field == "price" and value == 0)):
            errors.append(f"out_of_range_{field}")
    if row["fuel_type"] == "Electric" and row["engine_capacity_cc"] not in (None, 0):
        errors.append("electric_engine_displacement_conflict")
    if row["fuel_type"] in ("Petrol", "Diesel", "CNG", "LPG", "Hybrid") and row["engine_capacity_cc"] == 0:
        errors.append("combustion_engine_displacement_zero")
    rule = rules.get((row["brand"].casefold(), row["model"].casefold()))
    flags = ["source_provenance_unverified", "price_basis_unknown", "observation_date_missing"]
    if rule and row["manufacture_year"] is not None:
        if row["manufacture_year"] < rule["year"]:
            errors.append("year_before_documented_model_introduction")
    elif row["brand"] and row["model"]:
        flags.append("model_chronology_not_checked")
    if row["manufacture_year"] is not None and 1900 <= row["manufacture_year"] <= year:
        row["vehicle_age"] = year - row["manufacture_year"]
        if row["vehicle_age"] > 0 and row["km_driven"] is not None and row["km_driven"] >= 0:
            row["km_per_year"] = round(row["km_driven"] / row["vehicle_age"], 6)
        elif row["vehicle_age"] == 0:
            flags.append("km_per_year_undefined_age_zero")
    if row["price"] is not None and row["price"] > 0:
        row["log_price"] = round(math.log(row["price"]), 10)
    if reason := feasibility_quarantine_reason(row):
        errors.append(reason)
    row["quality_flags"] = "|".join(flags)
    return row, errors


def quantile(values: list[float], q: float):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def describe(rows: list[dict]):
    prices = [r["price"] for r in rows]
    correlations = {}
    for feature in ("vehicle_age", "km_driven", "km_per_year", "engine_capacity_cc", "owner_count"):
        pairs = [(r[feature], r["price"]) for r in rows if r[feature] is not None]
        try:
            correlation = statistics.correlation([a for a, _ in pairs], [b for _, b in pairs])
        except statistics.StatisticsError:
            correlation = None
        correlations[feature] = {"pearson_r": round(correlation, 6) if correlation is not None else None, "n": len(pairs)}
    return {
        "rows": len(rows), "brands": len({r["brand"] for r in rows}),
        "models": len({(r["brand"], r["model"]) for r in rows}),
        "price_npr": {"min": min(prices) if prices else None,
                      "p25": quantile(prices, .25), "median": quantile(prices, .5),
                      "p75": quantile(prices, .75), "p95": quantile(prices, .95),
                      "max": max(prices) if prices else None},
        "missing_fields": {k: sum(r[k] in (None, "") for r in rows) for k in SPEC_COLUMNS},
        "price_correlations": correlations,
    }


def build(root=ROOT, reference_year=None):
    config = read_json(root / "data/sources.json")
    source = config["local_source"]
    year = reference_year if reference_year is not None else config["reference_year"]
    if not 1900 <= year <= 2100:
        raise ValueError("Reference year must be between 1900 and 2100")
    snapshot = root / source["snapshot_path"]
    origin = root / source["input_path"]
    if not snapshot.exists():
        payload = origin.read_bytes()
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(payload)
    else:
        payload = snapshot.read_bytes()
        if origin.exists() and origin.read_bytes() != payload:
            raise ValueError("Original data differs from the immutable snapshot. Register a new source version.")
    source_hash = digest(payload)
    rule_document = read_json(root / "data/model_year_rules.json")
    rules = {(r["brand"].casefold(), r["model"].casefold()): r for r in rule_document["rules"]}
    with snapshot.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=source["delimiter"])
        if reader.fieldnames != RAW_COLUMNS:
            raise ValueError(f"Unexpected source schema: {reader.fieldnames}")
        raw_rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in raw_rows):
        raise ValueError("Malformed source: row length does not match header")
    kept, quarantine, duplicates, ledger = [], [], [], []
    seen = {}
    reason_counts = Counter()
    for index, raw in enumerate(raw_rows, start=2):
        row, errors = normalize(raw, index, source, source_hash, year, rules)
        # Include all source content, excluding identity metadata; never dedupe by price alone.
        key = tuple(text(raw[k]).casefold() for k in RAW_COLUMNS)
        if key in seen:
            status = "duplicate"
            reasons = [f"duplicate_of_source_row_{seen[key]}"]
            duplicates.append({"source_row": index, "duplicate_of_source_row": seen[key], **raw})
        else:
            seen[key] = index
            if errors:
                status, reasons = "quarantine", errors
                reason_counts.update(errors)
                quarantine.append({"source_row": index, "reasons": "|".join(errors), **raw})
            else:
                status, reasons = "retained_for_research", []
                kept.append(row)
        ledger.append({"record_id": row["record_id"], "source_row": index, "status": status,
                       "reasons": "|".join(reasons), "source_sha256": source_hash})
    if len(kept) + len(quarantine) + len(duplicates) != len(raw_rows):
        raise AssertionError("Row accounting failed")
    output = root / "data/processed/nepal"
    write_csv(output / "vehicles.csv", kept, COLUMNS)
    for kind, filename in (("Car", "cars.csv"), ("Bike", "bikes.csv"), ("Scooter", "scooters.csv")):
        write_csv(output / filename, [r for r in kept if r["vehicle_type"] == kind], COLUMNS)
    write_csv(root / "data/quarantine/nepal_user_2000.csv", quarantine, ["source_row", "reasons", *RAW_COLUMNS])
    write_csv(root / "data/quarantine/nepal_user_duplicates.csv", duplicates, ["source_row", "duplicate_of_source_row", *RAW_COLUMNS])
    write_csv(root / "reports/row_audit.csv", ledger, ["record_id", "source_row", "status", "reasons", "source_sha256"])
    write_json(root / "reports/source_manifest.json", {
        "source": source, "sha256": source_hash, "bytes": len(payload), "raw_rows": len(raw_rows),
        "rules_sha256": digest((root / "data/model_year_rules.json").read_bytes()),
        "config_sha256": digest((root / "data/sources.json").read_bytes()),
        "pipeline_sha256": digest(Path(__file__).read_bytes()), "reference_year": year,
    })
    summary = {
        "status": "prepared", "reference_year": year,
        "market": "Nepal", "currency": "NPR", "raw_rows": len(raw_rows),
        "raw_types": dict(Counter(r["vehicle_type"] for r in raw_rows)),
        "duplicates": len(duplicates), "quarantined": len(quarantine), "retained": len(kept),
        "quarantine_reasons": dict(reason_counts),
        "verified_real_listing_rows": 0, "training_eligible_rows": 0,
        "types": {kind: describe([r for r in kept if r["vehicle_type"] == kind]) for kind in ("Car", "Bike", "Scooter")},
        "regions": dict(Counter(r["region"] for r in kept)),
        "limitations": [
            "Origin and price calibration of the user CSV are unverified; plausible rows are research candidates only.",
            "No observation dates: age and km/year use the explicit audit reference year, not known age at sale.",
            "Introduction rules cover selected models only and flag review candidates, not certified impossibilities.",
            "No listing IDs: content duplicates are removed but unique vehicles cannot be guaranteed.",
            "City, insurance, color, seats, power, mileage and gear count were not supplied; they remain null.",
            "SUV maps to Car with body_type SUV; remaining body types are not guessed.",
            "Prices are never altered, synthesized, inflated, or converted from another market.",
            "EDA correlations are descriptive; log_price and price must never be input predictors.",
        ],
    }
    write_json(root / "reports/eda_summary.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-year", type=int, help="Explicit audit year; does not change raw data")
    args = parser.parse_args()
    report = build(reference_year=args.reference_year)
    print(json.dumps({k: report[k] for k in ("status", "raw_rows", "duplicates", "quarantined", "retained", "training_eligible_rows")}, indent=2))
