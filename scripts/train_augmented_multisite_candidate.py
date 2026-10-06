"""Create a labeled synthetic augmentation and train a separate research candidate."""
import hashlib
import json
import math
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
sys.path.insert(0, str(ROOT))
from scripts.train_multisite_car_candidate import CATEGORICAL, DATA, NUMERIC, ROOT, feature_frame, group_id, metric

AUGMENTED_DATA = ROOT / 'data/processed/nepal_used_cars_augmented_3000.json'
OUTPUT = ROOT / 'models/car-market-candidate-augmented-v1'
SEED = 42026
SYNTHETIC_WEIGHT = 0.25
SYNTHETIC_FIELDS = ['brand', 'model', 'variant', 'model_year', 'odometer_km', 'engine_cc',
                    'fuel_type', 'transmission', 'drivetrain', 'condition_claim', 'body_type']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def estimator(model):
    numeric = Pipeline([('impute', SimpleImputer(strategy='median', keep_empty_features=True)), ('scale', StandardScaler())])
    categorical = Pipeline([('impute', SimpleImputer(strategy='constant', fill_value='unknown', keep_empty_features=True)),
                            ('encode', OneHotEncoder(handle_unknown='ignore', sparse_output=False))])
    preprocess = ColumnTransformer([('numeric', numeric, NUMERIC), ('categories', categorical, CATEGORICAL)])
    return TransformedTargetRegressor(regressor=Pipeline([('preprocess', preprocess), ('model', model)]), func=np.log, inverse_func=np.exp)


def compatible(first, second):
    if (str(first['brand']).casefold(), str(first['model']).casefold()) != (str(second['brand']).casefold(), str(second['model']).casefold()):
        return False
    for field in ('fuel_type', 'transmission', 'drivetrain', 'variant', 'body_type'):
        left, right = first.get(field), second.get(field)
        if pd.notna(left) and pd.notna(right) and str(left).strip().casefold() != str(right).strip().casefold():
            return False
    years = (first.get('model_year'), second.get('model_year'))
    if not all(pd.notna(value) for value in years) or abs(float(years[0]) - float(years[1])) > 3:
        return False
    distances = (first.get('odometer_km'), second.get('odometer_km'))
    if all(pd.notna(value) for value in distances) and abs(float(distances[0]) - float(distances[1])) > 60000:
        return False
    engines = (first.get('engine_cc'), second.get('engine_cc'))
    if all(pd.notna(value) for value in engines) and abs(float(engines[0]) - float(engines[1])) > 500:
        return False
    left_group, right_group = first.get('possible_duplicate_group'), second.get('possible_duplicate_group')
    if pd.notna(left_group) and pd.notna(right_group) and left_group == right_group:
        return False
    return True


def interpolate(first, second, weight):
    row = {field: first.get(field) if first.get(field) is not None else second.get(field) for field in SYNTHETIC_FIELDS}
    for field in ('model_year', 'odometer_km', 'engine_cc'):
        left, right = first.get(field), second.get(field)
        if pd.notna(left) and pd.notna(right):
            value = float(left) * (1 - weight) + float(right) * weight
            row[field] = int(round(value)) if field in ('model_year', 'engine_cc') else round(value, 1)
    left_price, right_price = float(first['asking_price_npr']), float(second['asking_price_npr'])
    row['asking_price_npr'] = left_price * (1 - weight) + right_price * weight
    return row


def generate(real_rows, synthetic_count):
    rng = np.random.default_rng(SEED)
    neighbors = {row['record_id']: [other for other in real_rows if other['record_id'] != row['record_id'] and compatible(row, other)]
                 for row in real_rows}
    result = []
    for index in range(synthetic_count):
        parent = real_rows[int(rng.integers(len(real_rows)))]
        options = neighbors[parent['record_id']]
        if options:
            partner = options[int(rng.integers(len(options)))]
            weight = float(rng.uniform(0.2, 0.8))
            values = interpolate(parent, partner, weight)
            parent_ids = [parent['record_id'], partner['record_id']]
            method = 'interpolate_similar_same_model_listings_within_3_years_60000km_500cc_and_compatible_known_specs'
            noise = float(rng.uniform(-0.015, 0.015))
        else:
            values = {field: parent.get(field) for field in SYNTHETIC_FIELDS}
            values['asking_price_npr'] = parent['asking_price_npr']
            parent_ids = [parent['record_id']]
            method = 'bootstrap_sparse_vehicle_with_bounded_asking_price_perturbation_only'
            noise = float(np.clip(rng.normal(0, 0.025), -0.05, 0.05))
        values['asking_price_npr'] = round(float(values['asking_price_npr']) * math.exp(noise), 2)
        synthetic = {field: values.get(field) for field in SYNTHETIC_FIELDS}
        synthetic.update({
            'record_id': f'synthetic:{SEED}:{index + 1:04d}', 'record_type': 'synthetic',
            'source_site': 'synthetic_augmentation', 'source_url': None,
            'market_country': 'Nepal', 'currency': 'NPR', 'price_basis': 'synthetic_asking_price',
            'asking_price_npr': values['asking_price_npr'], 'actual_sale_price_npr': None,
            'listing_status': 'synthetic', 'training_eligible': False, 'independently_verified': False,
            'review_status': 'synthetic_label_unverified', 'parent_record_ids': parent_ids,
            'generation_method': method, 'asking_price_noise_fraction': round(math.exp(noise) - 1, 6),
            'quality_flags': ['SYNTHETIC_NOT_OBSERVED_MARKET_DATA', 'synthetic_price_derived_from_public_asking_prices'],
        })
        result.append(synthetic)
    return result


def fit_weighted(model, X, y, weights):
    return model.fit(X, y, model__sample_weight=weights)


def run():
    if OUTPUT.exists():
        raise FileExistsError('Model output already exists; preserve existing artifacts and select a new version')
    pointer_path = ROOT / 'models/current.json'
    pointer_before = digest(pointer_path)
    dataset = json.loads(DATA.read_text(encoding='utf-8'))
    scraped = dataset['records']
    real_rows = [row for row in scraped if isinstance(row.get('asking_price_npr'), (int, float)) and
                 math.isfinite(row['asking_price_npr']) and row['asking_price_npr'] > 0]
    missing_price = len(scraped) - len(real_rows)
    synthetic_count = 3000 - len(scraped)
    if AUGMENTED_DATA.exists():
        combined = json.loads(AUGMENTED_DATA.read_text(encoding='utf-8'))
        if combined.get('scraped_record_count') != len(scraped) or combined.get('synthetic_record_count') != synthetic_count or len(combined.get('records', [])) != 3000:
            raise ValueError('Existing augmented file has an unexpected cohort; refusing to continue')
        synthetic = [row for row in combined['records'] if row.get('record_type') == 'synthetic']
    else:
        synthetic = generate(real_rows, synthetic_count)
        combined = {key: value for key, value in dataset.items() if key != 'records'}
        combined.update({
            'purpose': 'Exploratory training experiment; synthetic examples are simulations and must never be represented as observed listings.',
            'record_count': len(scraped) + len(synthetic),
            'scraped_record_count': len(scraped), 'scraped_priced_record_count': len(real_rows),
            'synthetic_record_count': len(synthetic), 'synthetic_generation_seed': SEED,
            'synthetic_price_rule': 'Compatible same-model listings: interpolate numeric attributes and asking prices between two parents within 3 model years, 60000 km and 500 cc, then perturb price by at most 1.5%; sparse groups: keep features unchanged and perturb asking price by a clipped normal noise with standard deviation 2.5% and maximum absolute 5%.',
            'synthetic_price_is_sale_label': False,
            'records': scraped + synthetic,
        })
        AUGMENTED_DATA.parent.mkdir(parents=True, exist_ok=True)
        AUGMENTED_DATA.write_text(json.dumps(combined, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    rows = pd.DataFrame(real_rows).reset_index(drop=True)
    rows['target_npr'] = pd.to_numeric(rows['asking_price_npr'], errors='raise')
    rows['cv_group'] = rows.apply(group_id, axis=1)
    folds = list(GroupKFold(n_splits=5, shuffle=True, random_state=SEED).split(rows, rows.target_npr, rows.cv_group))
    synthetic_frame = pd.DataFrame(synthetic)
    candidates = {
        'real_only_ridge': estimator(Ridge(alpha=10)),
        'real_only_random_forest': estimator(RandomForestRegressor(n_estimators=250, min_samples_leaf=3, random_state=SEED, n_jobs=1)),
        'augmented_ridge': estimator(Ridge(alpha=10)),
        'augmented_random_forest': estimator(RandomForestRegressor(n_estimators=250, min_samples_leaf=3, random_state=SEED, n_jobs=1)),
        'real_only_median_baseline': estimator(DummyRegressor(strategy='median')),
    }
    predictions = {name: np.full(len(rows), np.nan) for name in candidates}
    fold_reports = {name: [] for name in candidates}
    fold_ids = np.full(len(rows), -1, dtype=int)
    with threadpool_limits(limits=2):
        for fold, (train_indexes, validation_indexes) in enumerate(folds):
            train_rows = rows.iloc[train_indexes].copy()
            validation_rows = rows.iloc[validation_indexes].copy()
            training_groups = set(train_rows.cv_group)
            valid_synthetic = synthetic_frame[synthetic_frame.parent_record_ids.map(
                lambda parents: all(rows.loc[rows.record_id.eq(parent), 'cv_group'].iloc[0] in training_groups for parent in parents))].copy()
            X_real = feature_frame(train_rows)
            y_real = train_rows.target_npr.to_numpy(float)
            X_augmented = pd.concat([X_real, feature_frame(valid_synthetic)], ignore_index=True)
            y_augmented = np.concatenate([y_real, valid_synthetic.asking_price_npr.to_numpy(float)])
            weights_augmented = np.concatenate([np.ones(len(y_real)), np.full(len(valid_synthetic), SYNTHETIC_WEIGHT)])
            X_validation = feature_frame(validation_rows)
            y_validation = validation_rows.target_npr.to_numpy(float)
            fold_ids[validation_indexes] = fold
            for name, prototype in candidates.items():
                model = estimator(Ridge(alpha=10)) if 'ridge' in name else estimator(RandomForestRegressor(
                    n_estimators=250, min_samples_leaf=3, random_state=SEED, n_jobs=1)) if 'forest' in name else estimator(DummyRegressor(strategy='median'))
                if name.startswith('augmented'):
                    fit_weighted(model, X_augmented, y_augmented, weights_augmented)
                    fit_size = len(y_augmented)
                else:
                    model.fit(X_real, y_real)
                    fit_size = len(y_real)
                prediction = model.predict(X_validation)
                predictions[name][validation_indexes] = prediction
                fold_reports[name].append({'fold': fold, 'real_training_rows': len(y_real),
                    'synthetic_training_rows': len(valid_synthetic) if name.startswith('augmented') else 0,
                    'fit_rows': fit_size, 'validation_rows': len(validation_rows), **metric(y_validation, prediction)})
    overall = {name: {'real_only_or_augmented_oof': metric(rows.target_npr, values), 'folds': fold_reports[name]}
               for name, values in predictions.items()}
    selected_name = min((name for name in overall if name.startswith('augmented_')),
                        key=lambda name: overall[name]['real_only_or_augmented_oof']['mae_npr'])
    best_real_only = min((name for name in overall if name.startswith('real_only_')),
                         key=lambda name: overall[name]['real_only_or_augmented_oof']['mae_npr'])
    selected = estimator(Ridge(alpha=10)) if 'ridge' in selected_name else estimator(RandomForestRegressor(
        n_estimators=250, min_samples_leaf=3, random_state=SEED, n_jobs=1)) if 'forest' in selected_name else estimator(DummyRegressor(strategy='median'))
    all_real_features = feature_frame(rows)
    all_y = rows.target_npr.to_numpy(float)
    all_features = pd.concat([all_real_features, feature_frame(synthetic_frame)], ignore_index=True)
    all_targets = np.concatenate([all_y, synthetic_frame.asking_price_npr.to_numpy(float)])
    all_weights = np.concatenate([np.ones(len(all_y)), np.full(len(synthetic_frame), SYNTHETIC_WEIGHT)])
    fit_weighted(selected, all_features, all_targets, all_weights)
    OUTPUT.mkdir(parents=True)
    artifact = OUTPUT / 'car.joblib'
    joblib.dump(selected, artifact, compress=3)
    oof = pd.DataFrame({'record_id': rows.record_id, 'source_site': rows.source_site, 'group_id': rows.cv_group,
                        'fold': fold_ids, 'actual_scraped_asking_price_npr': all_y,
                        'selected_candidate_oof_prediction_npr': predictions[selected_name]})
    oof.to_csv(OUTPUT / 'real_only_oof_predictions.csv', index=False)
    selected_by_source = {}
    for source, indexes in rows.groupby('source_site').groups.items():
        positions = np.asarray(list(indexes), dtype=int)
        selected_by_source[source] = metric(all_y[positions], predictions[selected_name][positions])
    report = {
        'candidate_version': OUTPUT.name,
        'trained_at_utc': datetime.now(timezone.utc).isoformat(),
        'training_scope': 'exploratory_unreviewed_scraped_asking_prices_plus_explicitly_simulated_records',
        'selected_candidate': selected_name,
        'best_real_only_candidate': best_real_only,
        'best_real_only_oof_metrics': overall[best_real_only]['real_only_or_augmented_oof'],
        'selected_oof_real_scraped_metrics': metric(all_y, predictions[selected_name]),
        'selected_oof_real_scraped_by_source': selected_by_source,
        'candidates': overall,
        'fit_rows_final': int(len(all_targets)), 'scraped_priced_rows': len(rows),
        'synthetic_rows': len(synthetic_frame), 'synthetic_sample_weight': SYNTHETIC_WEIGHT,
        'real_rows_without_valid_asking_price_excluded_from_fit': missing_price,
        'real_validation_rows_are_synthetic_free': True,
        'cross_validation': '5-fold group-aware cross-validation evaluates only held-out scraped listings; synthetic examples are generated once using source and group links, and only training-fold-parent synthetics enter each fold fit.',
        'synthetic_rule': combined['synthetic_price_rule'],
        'limitations': [
            'All synthetic target values are simulated from observed asking prices. They are not new market observations or verified labels.',
            'Real scraped prices remain unreviewed and source claims may be stale, contradictory or incorrect.',
            'Grouped cross-validation uses this same scrape, not a fresh independent Nepal holdout.',
            'The 2011 Fortuner segment has no direct training observations; the two available Fortuner records have material evidence gaps.',
            'This model estimates advertised asking prices and does not estimate completed transaction prices.'
        ],
        'deployment_approved': False, 'validated_segments': [],
        'active_pointer_unchanged': digest(pointer_path) == pointer_before,
        'input_scrape_sha256': digest(DATA), 'augmented_dataset_sha256': digest(AUGMENTED_DATA),
        'model_sha256': digest(artifact), 'real_oof_predictions_sha256': digest(OUTPUT / 'real_only_oof_predictions.csv'),
        'environment': {'python': platform.python_version(), 'scikit_learn': sklearn.__version__}
    }
    if not report['active_pointer_unchanged']:
        raise RuntimeError('The active model pointer changed during candidate training')
    (OUTPUT / 'evaluation.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('candidate_version', 'selected_candidate', 'fit_rows_final',
        'scraped_priced_rows', 'synthetic_rows', 'selected_oof_real_scraped_metrics',
        'selected_oof_real_scraped_by_source', 'deployment_approved', 'active_pointer_unchanged')}, indent=2))


if __name__ == '__main__':
    run()
