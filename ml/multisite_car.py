"""Runtime adapter for the exploratory scraped-Nepal car asking-price model."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import joblib
import numpy as np
import pandas as pd
import sklearn

from ml.predict import PredictionInputError, clean_text, validate

ROOT = Path(__file__).resolve().parents[1]
VERSION = "car-market-candidate-multisite-v3"
NUMERIC = ["model_year", "odometer_km", "engine_cc"]
CATEGORICAL = ["brand", "model", "variant", "fuel_type", "transmission", "drivetrain", "condition_claim", "body_type"]


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _feature_frame(row):
    values = {field: pd.to_numeric(pd.Series([row[field]]), errors="coerce").iloc[0] for field in NUMERIC}
    values.update({field: str(row[field]).strip().casefold() if row.get(field) is not None and str(row[field]).strip() else np.nan
                   for field in CATEGORICAL})
    return pd.DataFrame([values], columns=NUMERIC + CATEGORICAL)


class MultiSiteCarPredictor:
    def __init__(self, model_dir=None, data_path=None):
        self.directory = Path(model_dir) if model_dir else ROOT / "models" / VERSION
        self.version = VERSION
        report = json.loads((self.directory / "evaluation.json").read_text(encoding="utf-8"))
        model_path = self.directory / "car.joblib"
        if report.get("candidate_version") != VERSION or report.get("artifact_sha256") != _sha256(model_path):
            raise RuntimeError("Exploratory car model checksum/version mismatch")
        if report.get("environment", {}).get("scikit_learn") != sklearn.__version__:
            raise RuntimeError("scikit-learn version differs from the exploratory car model")
        self.estimator = joblib.load(model_path)
        data_path = Path(data_path) if data_path else ROOT / "data" / "processed" / "nepal_used_cars_multisite.json"
        if report.get("input_sha256") != _sha256(data_path):
            raise RuntimeError("Exploratory car training-data checksum mismatch")
        records = json.loads(data_path.read_text(encoding="utf-8"))["records"]
        self.rows = [r for r in records if r.get("market_country") == "Nepal" and r.get("currency") == "NPR"
                     and r.get("price_basis") == "advertised_asking" and isinstance(r.get("asking_price_npr"), (int, float))
                     and r["asking_price_npr"] > 0 and r.get("brand") and r.get("model") and r.get("model_year")]
        self._catalog = self._build_catalog()

    def _build_catalog(self):
        grouped = {}
        for row in self.rows:
            key = (row["brand"].strip(), row["model"].strip())
            grouped.setdefault(key, []).append(row)
        catalog = []
        for (brand, model), rows in sorted(grouped.items(), key=lambda item: (item[0][0].casefold(), item[0][1].casefold())):
            years = [int(row["model_year"]) for row in rows]
            fuels = sorted({clean_text(str(row["fuel_type"])).title() for row in rows if row.get("fuel_type")}) or ["Petrol", "Diesel"]
            engines = [float(row["engine_cc"]) for row in rows if isinstance(row.get("engine_cc"), (int, float)) and row["engine_cc"] > 0]
            transmissions = sorted({clean_text(str(row["transmission"])).title() for row in rows if row.get("transmission")}) or ["Manual", "Automatic"]
            body_types = sorted({clean_text(str(row["body_type"])).title() for row in rows if row.get("body_type")})
            catalog.append({"brand": brand, "model": model, "training_rows": len(rows), "min_year": min(years), "max_year": max(years),
                "constraints": {"observed_min_year": min(years), "observed_max_year": max(years), "year_basis": "observed_range",
                    "catalog_rows": len(rows), "fuel_types": fuels,
                    "engine_capacity_cc": [max(0, int(min(engines))) if engines and len(rows) >= 5 else 0,
                                           int(max(engines)) if engines and len(rows) >= 5 else 10000],
                    "motor_power_kw": None, "transmissions": transmissions, "body_types": body_types or ["SUV", "Sedan", "Hatchback"],
                    "km_driven_max": 1000000, "km_per_year_max": 100000, "reference_year": datetime.now(timezone.utc).year}})
        return catalog

    def catalog(self, vehicle_type):
        if vehicle_type != "Car":
            raise PredictionInputError("vehicle_type must be Car")
        return self._catalog

    def predict(self, payload, *, valuation_year=None):
        current_year = datetime.now(timezone.utc).year
        valuation_year = current_year if valuation_year is None else valuation_year
        cleaned = validate(payload, valuation_year)
        if cleaned["vehicle_type"] != "Car":
            raise PredictionInputError("This predictor supports cars only")
        pair = (cleaned["brand"].casefold(), cleaned["model"].casefold())
        entry = next((item for item in self._catalog if (item["brand"].casefold(), item["model"].casefold()) == pair), None)
        if entry is None:
            raise PredictionInputError("This car is not present in the Nepal scraped-data catalog.", "unknown_vehicle", "model")
        if not entry["min_year"] <= cleaned["manufacture_year"] <= entry["max_year"]:
            raise PredictionInputError(f"Scraped data year coverage is {entry['min_year']}–{entry['max_year']} AD.", "unsupported_year", "manufacture_year")
        cleaned["brand"], cleaned["model"] = entry["brand"], entry["model"]
        row = {"model_year": cleaned["manufacture_year"], "odometer_km": cleaned["km_driven"],
               "engine_cc": cleaned.get("engine_capacity_cc"), "brand": cleaned["brand"], "model": cleaned["model"],
               "variant": None, "fuel_type": cleaned.get("fuel_type"), "transmission": cleaned.get("transmission"),
               "drivetrain": None, "condition_claim": cleaned.get("listing_condition"),
               "body_type": cleaned.get("body_type")}
        frame = _feature_frame(row)
        start = perf_counter()
        predicted = float(self.estimator.predict(frame)[0])
        elapsed = (perf_counter() - start) * 1000
        if not math.isfinite(predicted) or predicted <= 0 or predicted >= 10**22:
            raise PredictionInputError("The model cannot return a valid positive price. Request a local appraisal.", "invalid_price", "predicted_price")
        model_inputs = {"vehicle_type", "brand", "model", "manufacture_year", "km_driven", "engine_capacity_cc",
                        "fuel_type", "transmission", "body_type", "listing_condition"}
        ignored = sorted(field for field in payload if field not in model_inputs and cleaned.get(field) is not None)
        if ignored:
            warnings.append({"code": "unused_input_fields", "message": "These supplied fields do not influence this car estimate: " + ", ".join(ignored) + "."})
        warnings = [{"code": "asking_price_basis", "message": "Estimate is based on advertised Nepal listing prices; final sale prices may differ."}]
        if cleaned["manufacture_year"] < 2000 or cleaned["km_driven"] > 400000:
            warnings.append({"code": "outside_observed_range", "message": "Vehicle details are far from the model's general observed data range."})
        missing = [field for field in NUMERIC + CATEGORICAL if pd.isna(frame.iloc[0][field])]
        if missing:
            warnings.append({"code": "imputed_features", "message": "Missing model inputs use fitted defaults: " + ", ".join(missing) + "."})
        return {"schema_version": "1.0", "model_version": self.version, "vehicle_type": "Car", "market": "Nepal",
            "currency": "NPR", "predicted_price": round(predicted, 2), "valuation_year": valuation_year,
            "vehicle_age": valuation_year - cleaned["manufacture_year"], "reference_year": valuation_year,
            "brand_model_fit_rows": entry["training_rows"], "is_extrapolation": entry["training_rows"] < 5,
            "ignored_input_fields": ignored, "warnings": warnings, "inference_ms": round(elapsed, 3)}
