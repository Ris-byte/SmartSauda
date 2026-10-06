"""Validated local inference contract for later backend integration."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import unicodedata
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import joblib
import pandas as pd
import sklearn

from ml.features import FEATURES, FEATURE_VERSION, TYPE_NAMES, feature_frame
from ml.catalog import PROVINCES, CONDITIONS, body_types

ROOT = Path(__file__).resolve().parents[1]
NUMERIC_FIELDS = {"manufacture_year", "km_driven", "engine_capacity_cc", "owner_count", "motor_power_kw",
                  "power_bhp", "mileage_kmpl", "seats", "gears"}
TEXT_FIELDS = {"brand", "model", "region", "city", "location_raw", "fuel_type", "transmission", "condition",
               "body_type", "insurance_status", "color", "listing_condition"}
ALLOWED_FIELDS = NUMERIC_FIELDS | TEXT_FIELDS | {"vehicle_type"}
REQUIRED_FIELDS = {"vehicle_type", "brand", "model", "manufacture_year", "km_driven"}


class PredictionInputError(ValueError):
    """One validation channel shared by HTTP and local inference."""
    def __init__(self, message, code="invalid_prediction", field=None):
        super().__init__(message)
        self.code, self.field = code, field


def clean_text(value):
    return " ".join("".join(c for c in unicodedata.normalize("NFKC", value)
                           if unicodedata.category(c) != "Cf").split())


def validate_feasibility(cleaned, catalogs, valuation_year):
    """Ordered support rules. Dataset coverage is not a production-history claim."""
    kind = cleaned["vehicle_type"]
    def reject(field, legal, code="unsupported_specification"):
        raise PredictionInputError(
            f"{field}={cleaned.get(field)!r} is not supported for {cleaned['brand']} {cleaned['model']} ({kind}). {legal}", code, field)
    pair = (cleaned["brand"].casefold(), cleaned["model"].casefold())
    entry = next((e for e in catalogs[kind] if (e['brand'].casefold(), e['model'].casefold()) == pair), None)
    # R5/R19/R20: identity first, so no arbitrary category reaches an estimator.
    if entry is None:
        alternatives = [f"{e['brand']} {e['model']} ({t})" for t, entries in catalogs.items() for e in entries
                        if e['model'].casefold() == pair[1]]
        reject("model", "Choose a catalogued brand/model. " + ("Known matches: " + ", ".join(alternatives) if alternatives else
               "This vehicle needs a catalog review before it can be estimated."), "unknown_vehicle")
    if entry.get("min_year") is None or not entry.get("constraints"):
        reject("model", "This model version has no support catalog. Update the model release.", "catalog_unavailable")
    cleaned.update(brand=entry['brand'], model=entry['model'])
    rules = entry['constraints']
    # R1: singleton padding is already encoded in the versioned catalog.
    low, high = entry['min_year'], min(entry['max_year'], valuation_year)
    if not low <= cleaned['manufacture_year'] <= high:
        reject("manufacture_year", f"Supported manufacture_year range: {low}–{high} AD (dataset coverage).", "unsupported_year")
    # R2: includes omitted/empty fuel; infer the only supported fuel for validation only.
    fuels = rules['fuel_types']
    if cleaned.get('fuel_type') is not None and cleaned['fuel_type'].casefold() not in {f.casefold() for f in fuels}:
        reject("fuel_type", "Supported fuel_type values: " + ", ".join(fuels) + ".", "unsupported_fuel")
    fuel = fuels[0]
    if fuel == 'Electric' and cleaned.get('engine_capacity_cc') is None:
        cleaned['engine_capacity_cc'] = 0
    if cleaned.get('fuel_type') is not None:
        cleaned['fuel_type'] = fuel
    # R3/R4: electric displacement and motor power are checked even with omitted fuel.
    cc = cleaned.get('engine_capacity_cc')
    cc_low, cc_high = rules['engine_capacity_cc']
    if cc is not None and not cc_low <= cc <= cc_high:
        reject("engine_capacity_cc", f"Supported engine_capacity_cc: {cc_low}–{cc_high} cc for {fuel}.", "unsupported_engine")
    power = cleaned.get('motor_power_kw')
    power_band = rules['motor_power_kw']
    if power is not None and (power_band is None or not power_band[0] <= power <= power_band[1]):
        reject("motor_power_kw", "Only catalogued electric scooters support motor_power_kw, in the range 0.35–3.0 kW.", "unsupported_motor_power")
    # R13–R16: explicit supported vocabularies; names are canonicalized.
    for field, choices in [('transmission', rules['transmissions']), ('body_type', rules['body_types']),
                           ('region', PROVINCES), ('condition', CONDITIONS)]:
        value = cleaned.get(field)
        if value is not None:
            canonical = next((s for s in choices if s.casefold() == value.casefold()), None)
            if canonical is None:
                reject(field, f"Supported {field}: {', '.join(choices) or 'omit this field for this vehicle type'}.")
            cleaned[field] = canonical
    # R7: operational support caps, not a claim about every physically possible vehicle.
    age = rules['reference_year'] - cleaned['manufacture_year']
    km_max = min(rules['km_driven_max'], 1000 if age == 0 else age * rules['km_per_year_max'])
    if cleaned['km_driven'] > km_max:
        reject('km_driven', f"Supported km_driven: 0–{km_max:g} km for this age (up to 44,000 km/year).", 'unsupported_odometer')
    # R17/R18/R22: bounds for optional fields supplied by API clients.
    owners = cleaned.get('owner_count')
    owner_max = min(4, age + 1)
    if owners is not None and not 1 <= owners <= owner_max:
        reject('owner_count', f"Supported owner_count: 1–{owner_max} for this age.")
    if cleaned.get('seats') is not None and (kind != 'Car' or not 1 <= cleaned['seats'] <= 9):
        reject('seats', 'Seats are supported only for Car, from 1 to 9, and do not affect this estimate.')
    if cleaned.get('gears') is not None and (kind != 'Bike' or not 0 <= cleaned['gears'] <= 6):
        reject('gears', 'Gears are supported only for Bike, from 0 to 6, and do not affect this estimate.')
    if age == 0 and cleaned['km_driven'] == 0 and cleaned.get('condition') == 'Poor':
        reject('condition', 'A new, zero-kilometre vehicle in Poor condition needs a manual damage appraisal.', 'unsupported_condition_combination')
    return entry


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(payload, valuation_year):
    if not isinstance(payload, dict):
        raise PredictionInputError("Input must be an object")
    unknown = set(payload) - ALLOWED_FIELDS
    if unknown:
        raise PredictionInputError("Unknown input fields: " + ", ".join(sorted(str(k) for k in unknown)))
    missing = [field for field in sorted(REQUIRED_FIELDS) if payload.get(field) is None]
    if missing:
        raise PredictionInputError("Missing required fields: " + ", ".join(missing))
    kind = payload["vehicle_type"]
    if not isinstance(kind, str) or kind.strip().casefold() not in {name.casefold() for name in TYPE_NAMES}:
        raise PredictionInputError("vehicle_type must be Car, Bike or Scooter")
    result = {"vehicle_type": kind.strip().title()}
    for field in TEXT_FIELDS:
        value = payload.get(field)
        if value is None:
            result[field] = None
        elif not isinstance(value, str) or len(value) > 160:
            raise PredictionInputError(f"{field} must be a nonempty string of at most 160 characters")
        else:
            result[field] = clean_text(value) or None
            if field in ('brand', 'model') and (not result[field] or not any(c.isalnum() for c in result[field])):
                raise PredictionInputError(f"{field}={value!r} must contain a catalogued name with letters or numbers.", 'invalid_identity', field)
    for field in NUMERIC_FIELDS:
        value = payload.get(field)
        if value is None:
            result[field] = None
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise PredictionInputError(f"{field} must be a finite number")
        if field in {"manufacture_year", "owner_count", "seats", "gears"} and not isinstance(value, int):
            raise PredictionInputError(f"{field} must be an integer")
        lower = 1 if field in {"owner_count", "seats", "motor_power_kw", "power_bhp", "mileage_kmpl"} else 0
        if (lower == 1 and value <= 0) or (lower == 0 and value < 0):
            raise PredictionInputError(f"{field} must be {'positive' if lower else 'nonnegative'}")
        result[field] = value
    if not 1900 <= result["manufacture_year"] <= valuation_year:
        raise PredictionInputError(f"manufacture_year must be between 1900 and {valuation_year}")
    fuel = (result.get("fuel_type") or "").casefold()
    if fuel == "electric" and result["engine_capacity_cc"] not in (None, 0):
        raise PredictionInputError("Electric fuel conflicts with nonzero engine_capacity_cc")
    if fuel in {"petrol", "diesel", "hybrid", "cng", "lpg"} and result["engine_capacity_cc"] == 0:
        raise PredictionInputError("Combustion-engine fuel conflicts with zero engine_capacity_cc")
    result["reference_year"] = valuation_year
    return result


class PricePredictor:
    """Load only project-generated, checksummed model artifacts from a trusted directory."""
    def __init__(self, model_dir=None, version=None):
        base = Path(model_dir) if model_dir else ROOT / "models"
        if version is None:
            version = read_json(base / "current.json")["model_version"]
        if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", version):
            raise ValueError("Invalid model version")
        self.directory = base / version
        self.version = version
        self.manifest = read_json(self.directory / "manifest.json")
        if self.manifest["model_version"] != version or self.manifest["feature_version"] != FEATURE_VERSION:
            raise RuntimeError("Artifact and feature-contract versions do not match")
        if self.manifest["environment"]["scikit_learn"] != sklearn.__version__:
            raise RuntimeError("scikit-learn version differs from training; use requirements-ml.txt")
        self.loaded = {}

    def _load(self, kind):
        if kind not in self.loaded:
            entry = self.manifest["artifacts"][kind]
            model_path = self.directory / f"{kind.lower()}.joblib"
            metadata_path = self.directory / f"{kind.lower()}.json"
            if file_hash(metadata_path) != entry["metadata_sha256"] or file_hash(model_path) != entry["sha256"]:
                raise RuntimeError("Model or metadata checksum mismatch")
            metadata = read_json(metadata_path)
            if metadata["vehicle_type"] != kind or metadata["model_version"] != self.version:
                raise RuntimeError("Model metadata mismatch")
            self.loaded[kind] = (joblib.load(model_path), metadata)
        return self.loaded[kind]

    def catalog(self, vehicle_type):
        if vehicle_type not in TYPE_NAMES:
            raise PredictionInputError("vehicle_type must be Car, Bike or Scooter")
        entries = deepcopy(self._load(vehicle_type)[1]["catalog"])
        if vehicle_type == 'Car':
            for entry in entries:
                entry['constraints']['body_types'] = body_types(entry['brand'], entry['model'])
        return entries

    def predict(self, payload, *, valuation_year=None):
        current_year = datetime.now(timezone.utc).year
        valuation_year = current_year if valuation_year is None else valuation_year
        if isinstance(valuation_year, bool) or not isinstance(valuation_year, int) or not 1900 <= valuation_year <= current_year:
            raise PredictionInputError("valuation_year must be a past or current Gregorian year")
        cleaned = validate(payload, valuation_year)
        kind = cleaned["vehicle_type"]
        estimator, metadata = self._load(kind)
        entry = validate_feasibility(cleaned, {t: self.catalog(t) for t in TYPE_NAMES}, valuation_year)
        cleaned['reference_year'] = metadata['reference_year']
        inference_inputs = dict(cleaned)
        legacy_body = kind == 'Car' and self.version == 'v1.1.0'
        if legacy_body:
            inference_inputs['body_type'] = 'SUV' if entry['constraints']['body_types'] == ['SUV'] else None
        frame = feature_frame(pd.DataFrame([inference_inputs]), kind)
        warnings = [
            {"code": "historical_prices", "message": "Estimate uses historical source prices with no adjustment to today's market."},
            {"code": "unverified_source", "message": "Training includes the user-supplied CSV whose collection/calibration method is unverified."},
            {"code": "approximate_age_basis", "message": f"Training and inference ages both use the fixed {metadata['reference_year']} reference year; listing dates and current-market calibration are unavailable."},
        ]
        if kind == "Car":
            warnings.append({"code": "unverified_car_cohort", "message": "All car training data come from the unverified user CSV; market accuracy is unproven."})
        if legacy_body:
            warnings.append({'code': 'derived_body_type', 'message': 'Body type follows the selected model. The historical estimator retains its original SUV/missing encoding; changing this field does not adjust the price.'})
        pair = (cleaned["brand"].casefold(), cleaned["model"].casefold())
        known_pairs = {(item["brand"].strip().casefold(), item["model"].strip().casefold()): item["training_rows"] for item in metadata["catalog"]}
        support = known_pairs.get(pair, 0)
        if support == 0:
            warnings.append({"code": "unseen_brand_model", "message": "This brand/model combination was absent from fitting data; the estimate is extrapolated."})
        elif support < 5:
            warnings.append({"code": "sparse_brand_model", "message": f"Only {support} fitting records support this brand/model combination."})
        missing_inputs = [field for field in FEATURES[kind]["numeric"] if pd.isna(frame.iloc[0][field])]
        missing_inputs += [field for field in FEATURES[kind]["categorical"] if pd.isna(frame.iloc[0][field])]
        if legacy_body:
            missing_inputs = [field for field in missing_inputs if field != 'body_type']
        if missing_inputs:
            warnings.append({"code": "imputed_features", "message": "Missing model features use fitted defaults: " + ", ".join(missing_inputs)})
        for field, limits in metadata["numeric_training_ranges"].items():
            value = frame.iloc[0][field]
            if pd.notna(value) and not limits["min"] <= value <= limits["max"]:
                shown = 'manufacture_year' if field == 'vehicle_age' else field
                warnings.append({"code": "outside_training_range", "field": shown,
                                 "message": f"{shown} is within the supported catalog but outside the estimator's fitting range."})
        for field, known_values in metadata["categorical_values"].items():
            value = frame.iloc[0][field]
            if pd.notna(value) and value not in known_values:
                warnings.append({"code": "unseen_category", "field": field, "message": f"{field} value was absent from fitting data."})
        supported = {"vehicle_type", "manufacture_year", "km_driven", *FEATURES[kind]["numeric"], *FEATURES[kind]["categorical"]}
        ignored = sorted(field for field in payload if field not in supported and cleaned.get(field) is not None)
        if ignored:
            warnings.append({"code": "unused_input_fields", "message": "These supplied fields do not influence this model: " + ", ".join(ignored)})
        if entry['constraints']['year_basis'] == 'observed_single_year_padded':
            warnings.append({'code': 'padded_year_coverage', 'message': 'This model has one observed year. The supported window extends by at most one year each side; production dates are not verified.'})
        age = valuation_year - cleaned['manufacture_year']
        if age >= 10 and cleaned['km_driven'] / age < 100:
            warnings.append({'code': 'low_odometer', 'field': 'km_driven', 'message': 'This mileage is unusually low for the vehicle age. Check the odometer and service history.'})
        start = perf_counter()
        predicted = float(estimator.predict(frame)[0])
        elapsed_ms = (perf_counter() - start) * 1000
        if not math.isfinite(predicted) or round(predicted, 2) <= 0 or round(predicted, 2) >= 10**22:
            raise PredictionInputError("The model cannot return a valid positive price for these specifications. Request a manual appraisal.", 'invalid_price', 'predicted_price')
        return {
            "schema_version": "1.0", "model_version": self.version, "vehicle_type": kind,
            "market": "Nepal", "currency": "NPR", "predicted_price": round(predicted, 2),
            "valuation_year": valuation_year, "vehicle_age": int(frame.iloc[0]["vehicle_age"]),
            "reference_year": metadata['reference_year'],
            "brand_model_fit_rows": support, "is_extrapolation": any(w["code"] in {"unseen_brand_model", "outside_training_range", "unseen_category"} for w in warnings),
            "ignored_input_fields": ignored, "warnings": warnings,
            "inference_ms": round(elapsed_ms, 3),
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Path to a JSON specification object")
    parser.add_argument("--version")
    parser.add_argument("--valuation-year", type=int)
    args = parser.parse_args()
    try:
        result = PricePredictor(version=args.version).predict(read_json(args.input), valuation_year=args.valuation_year)
    except PredictionInputError as error:
        parser.exit(2, f"Invalid prediction input: {error}\n")
    print(json.dumps(result, indent=2, allow_nan=False))
