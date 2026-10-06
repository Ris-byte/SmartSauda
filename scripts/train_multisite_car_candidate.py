"""Fit and group-cross-validate an inactive candidate on scraped asking prices."""
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/processed/nepal_used_cars_multisite.json'
OUTPUT = ROOT / 'models/car-market-candidate-multisite-v3'
NUMERIC = ['model_year', 'odometer_km', 'engine_cc']
CATEGORICAL = ['brand', 'model', 'variant', 'fuel_type', 'transmission', 'drivetrain', 'condition_claim', 'body_type']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def metric(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    error = predicted - actual
    percentage = error / actual * 100
    return {'rows': len(actual), 'mae_npr': float(np.abs(error).mean()),
            'median_absolute_percentage_error': float(np.median(np.abs(percentage))),
            'mean_signed_percentage_error': float(percentage.mean()),
            'fraction_within_30_percent': float((np.abs(percentage) <= 30).mean())}


def feature_frame(rows):
    values = pd.DataFrame(index=rows.index)
    for field in NUMERIC:
        values[field] = pd.to_numeric(rows[field], errors='coerce')
    for field in CATEGORICAL:
        values[field] = rows[field].map(lambda value: str(value).strip().casefold() if value is not None and pd.notna(value) and str(value).strip() else np.nan)
    return values


def estimator(model):
    numeric = Pipeline([('impute', SimpleImputer(strategy='median', keep_empty_features=True)), ('scale', StandardScaler())])
    categorical = Pipeline([('impute', SimpleImputer(strategy='constant', fill_value='unknown', keep_empty_features=True)),
                            ('encode', OneHotEncoder(handle_unknown='ignore', sparse_output=False))])
    preprocess = ColumnTransformer([('numeric', numeric, NUMERIC), ('categories', categorical, CATEGORICAL)])
    return TransformedTargetRegressor(regressor=Pipeline([('preprocess', preprocess), ('model', model)]), func=np.log, inverse_func=np.exp)


def group_id(row):
    if pd.notna(row['possible_duplicate_group']) and str(row['possible_duplicate_group']).strip():
        return str(row['possible_duplicate_group'])
    return str(row['record_id'])


def run():
    if OUTPUT.exists():
        raise FileExistsError(f'{OUTPUT} already exists; preserve it and choose a new candidate version')
    pointer_path = ROOT / 'models/current.json'
    pointer_hash = digest(pointer_path)
    dataset = json.loads(DATA.read_text(encoding='utf-8'))
    rows = pd.DataFrame(dataset['records'])
    if rows['record_id'].duplicated().any():
        raise ValueError('Duplicate record IDs')
    for field in ('market_country', 'currency', 'price_basis'):
        if field not in rows:
            raise ValueError(f'Missing dataset field {field}')
    rows = rows[(rows['market_country'] == 'Nepal') & (rows['currency'] == 'NPR') &
                (rows['price_basis'] == 'advertised_asking')].copy()
    rows['target_npr'] = pd.to_numeric(rows['asking_price_npr'], errors='coerce')
    rows = rows[np.isfinite(rows['target_npr']) & (rows['target_npr'] > 0)].copy().reset_index(drop=True)
    if len(rows) < 50:
        raise ValueError(f'Insufficient priced records: {len(rows)}')
    rows['cv_group'] = rows.apply(group_id, axis=1)
    group_count = rows['cv_group'].nunique()
    fold_count = min(5, group_count)
    if fold_count < 3:
        raise ValueError('Need at least three independent groups for grouped cross-validation')
    X = feature_frame(rows)
    y = rows['target_npr'].to_numpy(dtype=float)
    groups = rows['cv_group'].to_numpy()
    seed = 42
    models = {
        'median_baseline': estimator(DummyRegressor(strategy='median')),
        'ridge_log_price': estimator(Ridge(alpha=10)),
        'random_forest_log_price': estimator(RandomForestRegressor(n_estimators=250, min_samples_leaf=3, random_state=seed, n_jobs=1)),
    }
    splitter = GroupKFold(n_splits=fold_count, shuffle=True, random_state=seed)
    fold_assignments = np.full(len(rows), -1, dtype=int)
    candidate_oof = {}
    details = {}
    with threadpool_limits(limits=2):
        folds = list(splitter.split(X, y, groups))
        for fold_number, (_, validation) in enumerate(folds):
            fold_assignments[validation] = fold_number
        for name, model in models.items():
            predictions = np.full(len(rows), np.nan)
            fold_metrics = []
            for fold_number, (train, validation) in enumerate(folds):
                model.fit(X.iloc[train], y[train])
                prediction = model.predict(X.iloc[validation])
                predictions[validation] = prediction
                fold_metrics.append({'fold': fold_number, 'train_rows': len(train), 'validation_rows': len(validation), **metric(y[validation], prediction)})
            candidate_oof[name] = predictions
            details[name] = {'grouped_oof': metric(y, predictions), 'folds': fold_metrics}
        selected_name = min(details, key=lambda name: details[name]['grouped_oof']['mae_npr'])
        selected = models[selected_name].fit(X, y)
    OUTPUT.mkdir(parents=True)
    artifact = OUTPUT / 'car.joblib'
    joblib.dump(selected, artifact, compress=3)
    oof = pd.DataFrame({'record_id': rows['record_id'], 'source_site': rows['source_site'], 'group_id': groups,
                        'fold': fold_assignments, 'actual_asking_price_npr': y,
                        'predicted_asking_price_npr': candidate_oof[selected_name]})
    oof['absolute_percentage_error'] = np.abs(oof['predicted_asking_price_npr'] - y) / y * 100
    oof.to_csv(OUTPUT / 'grouped_oof_predictions.csv', index=False)
    by_source = {}
    for source, indexes in rows.groupby('source_site').groups.items():
        loc = np.asarray(list(indexes), dtype=int)
        by_source[source] = metric(y[loc], candidate_oof[selected_name][loc])
    report = {
        'candidate_version': OUTPUT.name,
        'trained_at_utc': datetime.now(timezone.utc).isoformat(),
        'training_scope': 'exploratory_only_unreviewed_public_listings',
        'target': 'advertised asking price NPR; listed prices on sold and expired ads remain asking prices',
        'eligible_priced_rows_used': len(rows), 'dataset_records': len(dataset['records']),
        'records_without_valid_positive_asking_price_excluded': len(dataset['records']) - len(rows),
        'duplicate_reposts_consolidated_before_fit': dataset.get('consolidated_repost_count', 0),
        'grouping': 'photo-confirmed consolidated reposts and matching vehicle-suspicion groups retained together; remaining listings treated as separate ads',
        'cv_method': f'{fold_count}-fold shuffled GroupKFold; each candidate scored out of fold; no independent external dataset used',
        'group_count': int(group_count), 'selected_family': selected_name,
        'candidates': details, 'selected_oof_by_source': by_source,
        'features': {'numeric': NUMERIC, 'categorical': CATEGORICAL},
        'quality_caveats': [
            'Records were not manually reviewed; contradictory and stale source claims remain.',
            'The model has no independently collected final evaluation. Grouped cross-validation on this dataset is exploratory and may still be optimistic.',
            'Prices are seller/dealer advertised amounts; no transaction price labels exist.',
            'Prediction error metrics do not establish market accuracy or validated vehicle segments.'
        ],
        'deployment_approved': False, 'validated_segments': [],
        'active_pointer_unchanged': digest(pointer_path) == pointer_hash,
        'input_sha256': digest(DATA), 'artifact_sha256': digest(artifact),
        'oof_predictions_sha256': digest(OUTPUT / 'grouped_oof_predictions.csv'),
        'environment': {'python': platform.python_version(), 'scikit_learn': sklearn.__version__}
    }
    if not report['active_pointer_unchanged']:
        raise RuntimeError('Active model pointer changed during research training')
    (OUTPUT / 'evaluation.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    run()
