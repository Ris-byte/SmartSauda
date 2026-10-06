"""Normalize the separately sourced Nepal two-wheeler data without inventing fields."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from prepare_data import ROOT, COLUMNS, describe, digest, number, read_json, text, write_csv, write_json, feasibility_quarantine_reason
import math

SOURCE_ID = "nepal_bikebazar_2025"
RAW_COLUMNS = ["ID", "Bike_Name", "bike_model_year", "Bike_Currency", "Bike_Price",
               "bike_power_cc", "bike_power_watt", "bike_type", "bike_distance", "condition", "bike_location"]
BIKE_TYPES = {"sports", "commuter", "cruiser", "sports naked", "dirt", "scrambler", "touring"}
# Exact brand prefixes observed in this source; this is parsing, not a production vehicle catalog.
BRANDS = ["Royal Enfield", "Asian Beast", "Super Soco", "Cross X", "Jawa Yezdi",
          "AIMA", "Aprilia", "Ather", "BMW", "Bajaj", "Benelli", "CFMoto", "Cosmic",
          "Crossfire", "Ducati", "Hartford", "Hero", "Honda", "Husqvarna", "ItalicaMoto",
          "KTM", "Kayo", "Komaki", "Lvneng", "Mitsuzu", "Motorhead", "NIU", "Runner",
          "SYM", "Segway", "Suzuki", "TAILG", "TARO", "TVS", "UM", "Vespa", "Yadea",
          "Yamaha", "Zongshen", "Zontes"]


def normalize_external(raw, line, source_hash, reference_year, rules):
    row = dict.fromkeys(COLUMNS)
    name = text(raw["Bike_Name"])
    brand = next((b for b in sorted(BRANDS, key=len, reverse=True) if name.casefold().startswith(b.casefold() + " ")), None)
    raw_type = text(raw["bike_type"]).casefold()
    kind = "Scooter" if raw_type == "scooter" else ("Bike" if raw_type in BIKE_TYPES else None)
    model = name[len(brand):].strip() if brand else name
    row.update({
        "record_id": f"{SOURCE_ID}:{line}", "source_id": SOURCE_ID, "source_row": line,
        "source_record_key": text(raw["ID"]), "source_sha256": source_hash,
        "market": "Nepal", "currency": "NPR", "provenance": "publisher_reported_scraped_listings",
        "price_basis": "asking", "reference_year": reference_year,
        "brand": brand, "model": model, "vehicle_type": kind,
        "manufacture_year": number(raw["bike_model_year"], integer=True),
        "price": number(raw["Bike_Price"]), "km_driven": number(raw["bike_distance"]),
        "engine_capacity_cc": number(raw["bike_power_cc"]),
        "location_raw": text(raw["bike_location"]) or None,
        # Used/brand-new is not the same concept as Good/Fair physical condition.
        "listing_condition": text(raw["condition"]).casefold() or None,
        "training_eligible": False,
    })
    watts = number(raw["bike_power_watt"])
    if watts is not None:
        row["motor_power_kw"] = watts / 1000
    errors = []
    if kind is None:
        errors.append("missing_or_unknown_vehicle_type")
    if not brand or not model:
        errors.append("unresolved_brand_or_model")
    if text(raw["Bike_Currency"]) != "Rs.":
        errors.append("unexpected_currency_marker")
    for field in ("manufacture_year", "price", "km_driven"):
        if row[field] is None:
            errors.append(f"invalid_{field}")
    year = row["manufacture_year"]
    if year is not None and not 1900 <= year <= reference_year:
        errors.append("year_out_of_range_or_calendar_ambiguous")
    if row["price"] is not None and row["price"] <= 0:
        errors.append("nonpositive_price")
    if row["km_driven"] is not None and row["km_driven"] < 0:
        errors.append("negative_km_driven")
    for field, raw_field in (("engine_capacity_cc", "bike_power_cc"), ("motor_power_kw", "bike_power_watt")):
        if text(raw[raw_field]) and (row[field] is None or row[field] <= 0):
            errors.append(f"invalid_{field}")
    if row["listing_condition"] == "brand new":
        errors.append("brand_new_not_resale")
    elif row["listing_condition"] not in (None, "used", "like new"):
        errors.append("unknown_listing_condition")
    flags = ["listing_url_missing", "observation_date_missing", "currency_from_publisher_description",
             "location_granularity_unknown", "condition_grade_not_supplied"]
    rule = rules.get(((brand or "").casefold(), model.casefold()))
    if rule and year is not None:
        if year < rule["year"]:
            errors.append("year_before_documented_model_introduction")
    else:
        flags.append("model_chronology_not_checked")
    if row["listing_condition"] is None:
        flags.append("used_status_not_supplied")
    if year is not None and 1900 <= year <= reference_year:
        row["vehicle_age"] = reference_year - year
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


def build(root=ROOT):
    config = read_json(root / "data/sources.json")
    source = next(s for s in config["public_sources"] if s["id"] == SOURCE_ID)
    folder = root / "data/external" / SOURCE_ID
    path = folder / "bike_data.csv"
    source_hash = digest(path.read_bytes())
    inventory = read_json(folder / "inventory.json")
    if source_hash != next(i["sha256"] for i in inventory if i["filename"] == path.name):
        raise ValueError("Source file checksum does not match downloaded inventory")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != RAW_COLUMNS:
            raise ValueError(f"Unexpected source schema: {reader.fieldnames}")
        rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError("Malformed CSV row")
    rules = {(r["brand"].casefold(), r["model"].casefold()): r for r in read_json(root / "data/model_year_rules.json")["rules"]}
    kept, quarantine, duplicates, ledger = [], [], [], []
    seen = {}
    reasons = Counter()
    for line, raw in enumerate(rows, 2):
        row, errors = normalize_external(raw, line, source_hash, source["reference_year"], rules)
        key = tuple(text(raw[k]).casefold() for k in RAW_COLUMNS if k != "ID")
        if key in seen:
            status, notes = "duplicate", [f"duplicate_of_source_row_{seen[key]}"]
            duplicates.append({"source_row": line, "duplicate_of_source_row": seen[key], **raw})
        else:
            seen[key] = line
            if errors:
                status, notes = "quarantine", errors
                reasons.update(errors)
                quarantine.append({"source_row": line, "reasons": "|".join(errors), **raw})
            else:
                status, notes = "retained_for_research", []
                kept.append(row)
        ledger.append({"record_id": row["record_id"], "source_row": line, "status": status,
                       "reasons": "|".join(notes), "source_sha256": source_hash})
    assert len(kept) + len(quarantine) + len(duplicates) == len(rows)
    output = root / "data/processed" / SOURCE_ID
    write_csv(output / "vehicles.csv", kept, COLUMNS)
    for kind, filename in (("Bike", "bikes.csv"), ("Scooter", "scooters.csv")):
        write_csv(output / filename, [r for r in kept if r["vehicle_type"] == kind], COLUMNS)
    write_csv(root / f"data/quarantine/{SOURCE_ID}.csv", quarantine, ["source_row", "reasons", *RAW_COLUMNS])
    write_csv(root / f"data/quarantine/{SOURCE_ID}_duplicates.csv", duplicates, ["source_row", "duplicate_of_source_row", *RAW_COLUMNS])
    write_csv(root / f"reports/{SOURCE_ID}_row_audit.csv", ledger, ["record_id", "source_row", "status", "reasons", "source_sha256"])
    summary = {
        "source": source, "sha256": source_hash, "raw_rows": len(rows),
        "duplicates": len(duplicates), "quarantined": len(quarantine), "retained": len(kept),
        "quarantine_reasons": dict(reasons), "training_eligible_rows": 0,
        "raw_missing": {k: sum(not text(row[k]) for row in rows) for k in RAW_COLUMNS},
        "types": {kind: describe([r for r in kept if r["vehicle_type"] == kind]) for kind in ("Bike", "Scooter")},
        "notes": [
            "Publisher reports scraped asking-price listings; listing URLs and observation dates are absent from the CSV.",
            "Reference year 2025 is the upload year, not a known observation date. Source year 2076 is quarantined, not guessed as a Bikram Sambat conversion.",
            "Brands are extracted by explicit prefixes; variants remain distinct and unrecognised names require review.",
            "No fuel, owner count, insurance, transmission, efficiency, or condition grade is invented. Electric watts are converted to kW, never to engine cc.",
            "Source ID column is retained for tracing, but is not assumed to be a marketplace listing identifier.",
            "Price scale is preserved exactly. Suspicious prices and unverified model chronology need further review.",
            "This source is kept separate from the market-calibrated CSV. Neither source is approved for training yet.",
        ],
    }
    write_json(root / f"reports/{SOURCE_ID}_summary.json", summary)
    write_json(root / f"reports/{SOURCE_ID}_manifest.json", {
        "source": source, "sha256": source_hash,
        "pipeline_sha256": digest(Path(__file__).read_bytes()),
        "shared_pipeline_sha256": digest((root / "scripts/prepare_data.py").read_bytes()),
        "rules_sha256": digest((root / "data/model_year_rules.json").read_bytes()),
    })
    return summary


if __name__ == "__main__":
    report = build()
    print(json.dumps({k: report[k] for k in ("raw_rows", "duplicates", "quarantined", "retained", "training_eligible_rows")}, indent=2))
