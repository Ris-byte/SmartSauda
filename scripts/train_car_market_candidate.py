"""Fit a research candidate, evaluate a separate publisher once, and never activate it."""
import hashlib
import json
import platform
import sys
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
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA = ROOT / 'data/processed/nepal-car-market-v2'
OUTPUT = ROOT / 'models/car-market-candidate-v2'
NUMERIC = ['manufacture_year', 'km_driven', 'engine_capacity_cc']
CATEGORICAL = ['brand', 'model', 'variant', 'drivetrain', 'fuel_type', 'transmission', 'condition_claim']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frame(rows):
    values = rows[NUMERIC + CATEGORICAL].copy()
    for field in CATEGORICAL:
        values[field] = values[field].map(lambda value: str(value).strip().casefold() if pd.notna(value) else np.nan)
    return values


def estimator(model):
    numeric = Pipeline([('impute', SimpleImputer(strategy='median', keep_empty_features=True)), ('scale', StandardScaler())])
    categories = Pipeline([('impute', SimpleImputer(strategy='constant', fill_value='unknown', keep_empty_features=True)),
                           ('encode', OneHotEncoder(handle_unknown='ignore', sparse_output=False))])
    preprocess = ColumnTransformer([('numeric', numeric, NUMERIC), ('categories', categories, CATEGORICAL)])
    return TransformedTargetRegressor(regressor=Pipeline([('preprocess', preprocess), ('model', model)]), func=np.log, inverse_func=np.exp)


def evaluate(actual, predicted):
    actual, predicted = np.asarray(actual), np.asarray(predicted)
    if not np.isfinite(predicted).all() or (predicted <= 0).any():
        raise ValueError('Invalid prediction')
    errors = predicted - actual
    percentages = errors / actual * 100
    return {'rows': len(actual), 'mae_npr': float(np.abs(errors).mean()),
            'mean_signed_error_npr': float(errors.mean()), 'median_absolute_percentage_error': float(np.median(np.abs(percentages))),
            'mean_signed_percentage_error': float(percentages.mean()), 'fraction_within_30_percent': float((np.abs(percentages) <= 30).mean())}


def run():
    if OUTPUT.exists():
        raise FileExistsError('Candidate output exists; use a new version')
    pointer_before = digest(ROOT / 'models/current.json')
    protocol_path = ROOT / 'ml/car_market_protocol.json'
    protocol = json.loads(protocol_path.read_text())
    manifest = json.loads((DATA / 'manifest.json').read_text())
    if manifest['training_scope'] != 'research_only' or manifest['deployment_approved']:
        raise ValueError('Unexpected research admission policy')
    for name in ('research_development.csv', 'external_evaluation.csv'):
        if digest(DATA / name) != manifest['outputs'][name]['sha256']:
            raise ValueError('Frozen input changed')
    development = pd.read_csv(DATA / 'research_development.csv')
    external = pd.read_csv(DATA / 'external_evaluation.csv')
    if not development.research_training_eligible.eq(True).all() or not external.external_evaluation_eligible.eq(True).all():
        raise ValueError('Unreviewed research input')
    if set(development.source_id) & set(external.source_id) or set(development.group_id) & set(external.group_id):
        raise ValueError('External evaluation overlaps development sources or duplicate groups')
    for rows in (development, external):
        if not rows.market.eq('Nepal').all() or not rows.currency.eq('NPR').all() or not rows.price_basis.eq('asking').all():
            raise ValueError('Mixed market, currency or target')
        if not np.isfinite(rows[['price', 'manufacture_year', 'km_driven']]).all().all() or (rows.price <= 0).any():
            raise ValueError('Invalid required values')
    seed = protocol['random_seed']
    candidates = {'median_baseline': estimator(DummyRegressor(strategy='median')),
                  'ridge_log_price': estimator(Ridge(alpha=10)),
                  'random_forest_log_price': estimator(RandomForestRegressor(n_estimators=200, min_samples_leaf=2, random_state=seed, n_jobs=1))}
    folds = list(GroupKFold(n_splits=protocol['development_folds'], shuffle=True, random_state=seed).split(development, groups=development.group_id))
    cv_scores = {}
    with threadpool_limits(limits=2):
        for name, model in candidates.items():
            scores = -cross_val_score(model, frame(development), development.price, cv=folds, scoring='neg_mean_absolute_error', n_jobs=1, error_score='raise')
            cv_scores[name] = {'mean_mae_npr': float(scores.mean()), 'fold_mae_npr': scores.tolist()}
        selected_name = min(cv_scores, key=lambda name: cv_scores[name]['mean_mae_npr'])
        selected = candidates[selected_name].fit(frame(development), development.price)
        baseline = estimator(DummyRegressor(strategy='median')).fit(frame(development), development.price)
        predicted = selected.predict(frame(external))
        baseline_predictions = baseline.predict(frame(external))
    results = external[['record_id', 'source_url', 'source_id', 'brand', 'model', 'variant', 'manufacture_year', 'price']].copy()
    results['predicted_price_npr'] = predicted
    results['baseline_price_npr'] = baseline_predictions
    results['signed_error_npr'] = predicted - external.price.to_numpy()
    results['absolute_percentage_error'] = np.abs(results.signed_error_npr) / results.price * 100
    overall = evaluate(external.price, predicted)
    baseline_metrics = evaluate(external.price, baseline_predictions)
    numerical_checks = {
        'external_sample_size': len(external) >= protocol['minimum_external_rows'],
        'median_percentage_error': overall['median_absolute_percentage_error'] <= protocol['maximum_median_absolute_percentage_error'],
        'within_30_percent': overall['fraction_within_30_percent'] >= protocol['minimum_fraction_within_30_percent'],
        'signed_percentage_bias': abs(overall['mean_signed_percentage_error']) <= protocol['maximum_absolute_mean_signed_percentage_error'],
        'baseline_improvement': overall['mae_npr'] < baseline_metrics['mae_npr']}
    by_model = {}
    for (brand, model), subset in results.groupby(['brand', 'model']):
        count = int((development.brand.eq(brand) & development.model.eq(model)).sum())
        by_model[brand + ' ' + model] = dict(evaluate(subset.price, subset.predicted_price_npr), development_rows=count,
                                           minimum_sample_counts_met=count >= 10 and len(subset) >= 5)
    OUTPUT.mkdir(parents=True)
    artifact = OUTPUT / 'car.joblib'
    joblib.dump(selected, artifact, compress=3)
    np.testing.assert_allclose(joblib.load(artifact).predict(frame(external)), predicted, rtol=1e-12)
    results.to_csv(OUTPUT / 'external_predictions.csv', index=False)
    assignments = development[['record_id', 'group_id']].copy()
    assignments['development_validation_fold'] = -1
    for index, (_, validation) in enumerate(folds):
        assignments.loc[validation, 'development_validation_fold'] = index
    assignments.to_csv(OUTPUT / 'development_folds.csv', index=False)
    report = {'candidate_version': OUTPUT.name, 'selected_family': selected_name, 'price_basis': 'asking',
              'development_rows': len(development), 'external_rows': len(external), 'development_cv': cv_scores,
              'external_metrics': overall, 'external_baseline_metrics': baseline_metrics, 'external_by_model': by_model,
              'numerical_checks': numerical_checks, 'deployment_approved': False, 'validated_segments': [],
              'deployment_blockers': ['Original listing dates and freshness are not verified.',
                                      'Vehicle independence is not independently verified; duplicate heuristics only.',
                                      'Variant/generation, drivetrain and condition evidence is incomplete.',
                                      'No external Fortuner examples qualify; older Fortuner coverage is insufficient.'],
              'notes': ['Candidate selection uses development-only grouped cross-validation.',
                        'The external set was reused after correcting condition-phrase extraction; results are exploratory, not a fresh final holdout.',
                        'Separate-publisher evaluation is provisional, not a verified representative Nepal market test.',
                        'The external set is never used for fitting or hyperparameter selection.',
                        'Seller claims and listing consistency are not mechanical inspections.',
                        'Missing engine and categorical inputs use development-fitted imputation.'],
              'protocol': protocol, 'features': {'numeric': NUMERIC, 'categorical': CATEGORICAL},
              'input_sha256': {name: digest(DATA / name) for name in ['manifest.json', 'research_development.csv', 'external_evaluation.csv']},
              'protocol_sha256': digest(protocol_path), 'script_sha256': digest(__file__),
              'artifact_sha256': digest(artifact), 'external_predictions_sha256': digest(OUTPUT / 'external_predictions.csv'),
              'development_folds_sha256': digest(OUTPUT / 'development_folds.csv'),
              'environment': {'python': platform.python_version(), 'scikit_learn': sklearn.__version__},
              'active_pointer_unchanged': digest(ROOT / 'models/current.json') == pointer_before}
    if not all(numerical_checks.values()):
        report['deployment_blockers'].append('One or more predeclared numerical thresholds failed.')
    (OUTPUT / 'evaluation.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    run()
