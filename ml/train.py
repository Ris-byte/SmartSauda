"""Compare models, tune on development data, and export untouched-test evaluations."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.base import clone
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, GroupKFold, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from ml.features import FEATURES, FEATURE_VERSION, TYPE_NAMES, duplicate_group, feature_frame
from ml.catalog import build_catalog, REFERENCE_YEAR

ROOT = Path(__file__).resolve().parents[1]



def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")

def metrics(actual, predicted):
    actual, predicted = np.asarray(actual), np.asarray(predicted)
    if not np.all(np.isfinite(predicted)) or np.any(predicted <= 0):
        raise ValueError("Model generated an invalid price")
    return {"n": len(actual), "mae_npr": float(mean_absolute_error(actual, predicted)),
            "rmse_npr": float(np.sqrt(mean_squared_error(actual, predicted))),
            "r2": float(r2_score(actual, predicted)) if len(actual) > 1 and np.var(actual) > 0 else None,
            "median_absolute_percentage_error": float(np.median(np.abs(actual - predicted) / actual) * 100),
            "within_20_percent": float(np.mean(np.abs(actual - predicted) / actual <= .2))}


def by_source(rows, predicted):
    predicted = np.asarray(predicted)
    return {source: metrics(rows.loc[mask, "price"], predicted[mask])
            for source in sorted(rows.source_id.unique())
            for mask in [rows.source_id.to_numpy() == source]}


def split_rows(rows, seed=42):
    """Fixed group-aware source-balanced split; never inspect target values."""
    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    dev, test = next(outer.split(rows, rows.source_id, groups=rows.group_id))
    development = rows.iloc[dev]
    inner = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=seed + 1)
    train_local, val_local = next(inner.split(development, development.source_id, groups=development.group_id))
    assignment = np.full(len(rows), "test", dtype=object)
    assignment[dev[train_local]] = "train"
    assignment[dev[val_local]] = "validation"
    group_sets = {part: set(rows.loc[assignment == part, "group_id"]) for part in ("train", "validation", "test")}
    if (group_sets["train"] & group_sets["validation"] or group_sets["train"] & group_sets["test"]
            or group_sets["validation"] & group_sets["test"]):
        raise AssertionError("Duplicate groups crossed partitions")
    return assignment


def pipeline(vehicle_type, estimator):
    spec = FEATURES[vehicle_type]
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                        ("scale", StandardScaler())])
    categorical = Pipeline([("imputer", SimpleImputer(strategy="constant", fill_value="unknown", keep_empty_features=True)),
                            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))])
    preprocessing = ColumnTransformer([("numeric", numeric, spec["numeric"]),
                                       ("categorical", categorical, spec["categorical"])], remainder="drop")
    # The output inversion is bundled with the estimator; metrics always use NPR.
    return TransformedTargetRegressor(
        regressor=Pipeline([("preprocess", preprocessing), ("model", estimator)]),
        func=np.log, inverse_func=np.exp, check_inverse=True)


def candidates(vehicle_type, seed):
    return {
        "median_baseline": pipeline(vehicle_type, DummyRegressor(strategy="median")),
        "ridge_log_price": pipeline(vehicle_type, Ridge(alpha=10.0)),
        "random_forest_log_price": pipeline(vehicle_type, RandomForestRegressor(
            n_estimators=200, min_samples_leaf=2, max_features=1.0, random_state=seed, n_jobs=1)),
        "gradient_boosting_log_price": pipeline(vehicle_type, GradientBoostingRegressor(
            n_estimators=200, learning_rate=.05, max_depth=2, loss="huber", random_state=seed)),
    }


def tuning_grid(family):
    prefix = "regressor__model__"
    params = {
        "ridge_log_price": {"alpha": [.1, 1.0, 10.0, 50.0, 100.0]},
        "random_forest_log_price": {"min_samples_leaf": [1, 2, 4], "max_features": [.7, 1.0]},
        "gradient_boosting_log_price": {"n_estimators": [150, 300], "max_depth": [2, 3], "loss": ["squared_error", "huber"]},
        "median_baseline": {},
    }[family]
    return {prefix + key: value for key, value in params.items()}


def grouped_mae_interval(rows, predicted, seed):
    """Descriptive group bootstrap for the MAE estimate, not a per-vehicle price interval."""
    errors = pd.DataFrame({"group": rows.group_id.to_numpy(), "error": np.abs(rows.price.to_numpy() - predicted)})
    sums = errors.groupby("group").error.agg(["sum", "count"]).to_numpy()
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(1000):
        sample = sums[rng.integers(0, len(sums), len(sums))]
        values.append(sample[:, 0].sum() / sample[:, 1].sum())
    return {"lower_npr": float(np.quantile(values, .025)), "upper_npr": float(np.quantile(values, .975)),
            "method": "1000 group bootstrap resamples; interval for mean absolute error, not individual prices"}


def load_data(config):
    if not config["approval"]["training_enabled"]:
        raise ValueError("Training is disabled in the selected configuration")
    inputs = [ROOT / name for name in config["datasets"]]
    frames = [pd.read_csv(path) for path in inputs]
    rows = pd.concat(frames, ignore_index=True).sort_values("record_id").reset_index(drop=True)
    if not rows.training_eligible.eq(True).all():
        raise ValueError("Dataset contains records not approved for training; complete provenance and price review first")
    if rows.record_id.duplicated().any():
        raise ValueError("Repeated record IDs across source inputs")
    if rows.groupby("vehicle_type").size().to_dict() != config["expected_rows"]:
        raise ValueError("Cohort changed; review the source data before retraining")
    if not rows.currency.eq("NPR").all() or not rows.market.eq("Nepal").all():
        raise ValueError("This approved run accepts Nepal/NPR only")
    for field in ("price", "manufacture_year", "reference_year", "km_driven"):
        if not np.isfinite(rows[field]).all():
            raise ValueError(f"Non-finite required input: {field}")
    if (rows.price <= 0).any() or (rows.km_driven < 0).any() or (rows.manufacture_year > rows.reference_year).any():
        raise ValueError("Invalid approved cohort values")
    rows["group_id"] = rows.apply(duplicate_group, axis=1, km_bucket=config["split"]["group_km_bucket"])
    return rows, {str(path.relative_to(ROOT)): sha256(path) for path in inputs}


def fit_type(rows, vehicle_type, config):
    seed = config["random_seed"]
    rows = rows.reset_index(drop=True).copy()
    rows["partition"] = split_rows(rows, seed)
    groups = {part: rows.loc[rows.partition == part].copy() for part in ("train", "validation", "test")}
    train, validation, test = (groups[part] for part in ("train", "validation", "test"))
    X_train, X_val = feature_frame(train, vehicle_type), feature_frame(validation, vehicle_type)
    options = candidates(vehicle_type, seed)
    results = {}
    print(f"{vehicle_type}: {len(train)} train / {len(validation)} validation / {len(test)} test", flush=True)
    for name, estimator in options.items():
        start = perf_counter()
        estimator.fit(X_train, train.price)
        predicted = estimator.predict(X_val)
        results[name] = {"validation": metrics(validation.price, predicted),
                         "validation_by_source": by_source(validation, predicted),
                         "fit_seconds": round(perf_counter() - start, 3)}
        print(f"  {name}: validation MAE NPR {results[name]['validation']['mae_npr']:,.0f}", flush=True)
    family = min(results, key=lambda name: results[name]["validation"]["mae_npr"])
    selected = clone(options[family])
    tuning = {"family": family, "adopted": False, "best_params": {}, "cv_results": []}
    grid = tuning_grid(family)
    if grid:
        cv = GroupKFold(n_splits=3, shuffle=True, random_state=seed + 2)
        search = GridSearchCV(clone(options[family]), grid, scoring="neg_mean_absolute_error", cv=cv,
                              n_jobs=config["selection"]["n_jobs"], error_score="raise", refit=True)
        search.fit(X_train, train.price, groups=train.group_id)
        val_pred = search.predict(X_val)
        tuned_metrics = metrics(validation.price, val_pred)
        tuning.update({"best_params": search.best_params_, "validation": tuned_metrics,
                       "validation_by_source": by_source(validation, val_pred),
                       "cv_results": [{"params": params, "mean_mae_npr": float(-score), "std_mae_npr": float(std)}
                                      for params, score, std in zip(search.cv_results_["params"], search.cv_results_["mean_test_score"], search.cv_results_["std_test_score"])]})
        if tuned_metrics["mae_npr"] < results[family]["validation"]["mae_npr"]:
            selected = clone(search.best_estimator_)
            tuning["adopted"] = True
        print(f"  tuned {family}: validation MAE NPR {tuned_metrics['mae_npr']:,.0f}; adopted={tuning['adopted']}", flush=True)
    # No test metric is read until selection and final fitting are complete.
    development = rows.loc[rows.partition != "test"].copy()
    selected.fit(feature_frame(development, vehicle_type), development.price)
    X_test = feature_frame(test, vehicle_type)
    start = perf_counter()
    predicted = selected.predict(X_test)
    batch_ms = (perf_counter() - start) * 1000
    median_model = clone(options["median_baseline"]).fit(feature_frame(development, vehicle_type), development.price)
    baseline_test = metrics(test.price, median_model.predict(X_test))
    known = {(str(r.brand).strip().casefold(), str(r.model).strip().casefold()) for r in development.itertuples()}
    seen_mask = np.array([(str(r.brand).strip().casefold(), str(r.model).strip().casefold()) in known for r in test.itertuples()])
    predictions = test[["record_id", "source_id", "vehicle_type", "group_id", "brand", "model", "price"]].copy()
    predictions["predicted_price_npr"] = predicted
    predictions["absolute_error_npr"] = np.abs(test.price.to_numpy() - predicted)
    predictions["brand_model_seen_in_development"] = seen_mask
    result = {
        "vehicle_type": vehicle_type, "selected_family": family, "features": FEATURES[vehicle_type],
        "partition_counts": {part: len(subset) for part, subset in groups.items()},
        "source_partition_counts": rows.groupby(["source_id", "partition"]).size().unstack(fill_value=0).to_dict(orient="index"),
        "unique_groups": int(rows.group_id.nunique()),
        "selection_candidates": results, "tuning": tuning,
        "test": metrics(test.price, predicted), "test_by_source": by_source(test, predicted),
        "test_median_baseline": baseline_test, "mae_bootstrap_95_percent": grouped_mae_interval(test, predicted, seed),
        "test_unseen_brand_model_rows": int((~seen_mask).sum()),
        "test_seen_brand_model": metrics(test.price.to_numpy()[seen_mask], predicted[seen_mask]) if seen_mask.any() else None,
        "test_unseen_brand_model": metrics(test.price.to_numpy()[~seen_mask], predicted[~seen_mask]) if (~seen_mask).any() else None,
        "batch_inference_ms": batch_ms, "batch_inference_rows": len(test),
        "export_fit_rows": len(development), "export_does_not_fit_test": True,
    }
    print(f"  FINAL TEST: R2={result['test']['r2']:.4f}, MAE=NPR {result['test']['mae_npr']:,.0f}, RMSE=NPR {result['test']['rmse_npr']:,.0f}", flush=True)
    return selected, result, rows, predictions


def model_metadata(vehicle_type, rows, result, version):
    development = rows.loc[rows.partition != "test"]
    categorical_values = {}
    frame = feature_frame(development, vehicle_type)
    for field in FEATURES[vehicle_type]["categorical"]:
        categorical_values[field] = sorted(frame[field].dropna().unique().tolist())
    catalog = build_catalog(rows, vehicle_type)
    numeric_ranges = {field: {"min": float(frame[field].min()), "max": float(frame[field].max())}
                      for field in FEATURES[vehicle_type]["numeric"] if frame[field].notna().any()}
    return {"model_version": version, "vehicle_type": vehicle_type, "currency": "NPR", "market": "Nepal",
            "feature_version": FEATURE_VERSION, "features": FEATURES[vehicle_type], "reference_year": REFERENCE_YEAR,
            "catalog": catalog, "categorical_values": categorical_values, "numeric_training_ranges": numeric_ranges,
            "fit_rows": len(development), "fit_sources": development.source_id.value_counts().to_dict(),
            "source_reference_years": {source: sorted(int(v) for v in subset.reference_year.unique()) for source, subset in development.groupby("source_id")},
            "test_metrics": result["test"], "test_metrics_by_source": result["test_by_source"],
            "limitations": ["Historical data; not adjusted to today's market prices.",
                            "User CSV provenance remains unverified; car data comes exclusively from that source.",
                            f"Training and inference both use fixed reference year {REFERENCE_YEAR}; historical prices are not time-adjusted.",
                            "Catalog years describe observed support, not verified production dates; single observed years have a one-year padded window.",
                            "Missing form fields are not all supported as model inputs.",
                            "No calibrated per-vehicle prediction interval is provided."]}


def run(version, config_path=None, activate=False):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", version):
        raise ValueError("Invalid version identifier")
    model_dir = ROOT / "models" / version
    if (model_dir / "manifest.json").exists():
        raise FileExistsError("Completed model versions are immutable; select a new --version")
    config_path = Path(config_path) if config_path else ROOT / 'ml/config.json'
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if activate and not config['approval'].get('deployment_approved', False):
        raise ValueError('Deployment is not approved; candidates must remain inactive')
    rows, inputs = load_data(config)
    fitted = {}
    with threadpool_limits(limits=2):
        for vehicle_type in TYPE_NAMES:
            fitted[vehicle_type] = fit_type(rows.loc[rows.vehicle_type == vehicle_type], vehicle_type, config)
    report_dir = ROOT / "reports/phase2" / version
    model_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    evaluation = {"model_version": version, "selection_protocol": config,
                  "models": {kind: value[1] for kind, value in fitted.items()}}
    splits, predictions, artifacts = [], [], {}
    for kind, (estimator, result, assigned, predicted) in fitted.items():
        path = model_dir / f"{kind.lower()}.joblib"
        joblib.dump(estimator, path, compress=3)
        metadata = model_metadata(kind, assigned, result, version)
        metadata["artifact_sha256"] = sha256(path)
        metadata["artifact_file"] = path.name
        write_json(model_dir / f"{kind.lower()}.json", metadata)
        # A reload must reproduce exactly the reported estimator's output.
        reloaded = joblib.load(path)
        expected = predicted.predicted_price_npr.to_numpy()
        test_rows = assigned.loc[assigned.partition == "test"]
        np.testing.assert_allclose(reloaded.predict(feature_frame(test_rows, kind)), expected, rtol=1e-12)
        artifacts[kind] = {"file": path.name, "sha256": sha256(path), "metadata_file": f"{kind.lower()}.json",
                           "metadata_sha256": sha256(model_dir / f"{kind.lower()}.json")}
        splits.append(assigned[["record_id", "source_id", "vehicle_type", "group_id", "partition", "source_sha256"]])
        predictions.append(predicted)
    pd.concat(splits, ignore_index=True).to_csv(report_dir / "split_assignments.csv", index=False)
    pd.concat(predictions, ignore_index=True).to_csv(report_dir / "test_predictions.csv", index=False)
    write_json(report_dir / "evaluation.json", evaluation)
    manifest = {
        "model_version": version, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "feature_version": FEATURE_VERSION, "approval": config["approval"], "input_sha256": inputs,
        "source_code_sha256": {str(path.relative_to(ROOT)): sha256(path) for path in [ROOT / "ml/train.py", ROOT / "ml/features.py", ROOT / "ml/catalog.py"]},
        "configuration_sha256": sha256(config_path),
        "environment": {"python": platform.python_version(), "scikit_learn": sklearn.__version__,
                        "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__, "joblib": joblib.__version__},
        "artifacts": artifacts, "fit_includes_test": False,
        "split_assignments_sha256": sha256(report_dir / "split_assignments.csv"),
        "test_predictions_sha256": sha256(report_dir / "test_predictions.csv"),
        "evaluation_sha256": sha256(report_dir / "evaluation.json"),
    }
    write_json(model_dir / "manifest.json", manifest)
    if activate:
        write_json(ROOT / "models/current.json", {"model_version": version})
    print(f"Saved {version}: models/{version} and reports/phase2/{version}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="v1.0.0")
    parser.add_argument('--config', type=Path)
    parser.add_argument('--activate', action='store_true', help='Requires explicit deployment approval in the configuration')
    args = parser.parse_args()
    run(args.version, args.config, args.activate)
