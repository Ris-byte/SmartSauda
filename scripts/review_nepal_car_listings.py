"""Screen captured listing evidence and diagnose the frozen model without retraining."""
import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.predict import PricePredictor, PredictionInputError
from scripts.collect_nepal_car_listings import parse_listing, plain, verify_snapshots

SOURCE = ROOT / 'data/external/nepal_car_listings_2026-10-04/listings.csv'
OUTPUT = ROOT / 'data/processed/car-listing-review-v3'
MODEL_PATTERNS = [
    ('Hyundai', r'grand\s*i\s*10\s+nios\b', 'Grand i10 Nios'),
    ('Hyundai', r'grand\s*i\s*10\b', 'Grand i10'),
    ('Hyundai', r'i\s*20\s+active\b', 'i20 Active'),
    ('Hyundai', r'i\s*20\b', 'i20'),
    ('Hyundai', r'i\s*10\b', 'i10'),
    *[('Hyundai', model.casefold() + r'\b', model) for model in
      ('Creta', 'Santro', 'Verna', 'Kona', 'Venue', 'Tucson', 'Xcent', 'Accent')],
    ('Suzuki', r'celerio\b', 'Celerio'),
    ('Renault', r'kwid\b', 'Kwid'),
    ('Tata', r'nexon\b', 'Nexon'),
]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize_model(brand, raw):
    for expected_brand, pattern, model in MODEL_PATTERNS:
        match = re.match(pattern, raw, re.I) if brand == expected_brand else None
        if match:
            return model, raw[match.end():].strip()
    return '', raw


def description_text(document):
    match = re.search(r'<h2\b[^>]*>\s*Description\s*</h2>(.*?)(?:<h2\b|$)', document, re.I | re.S)
    return plain(match[1]) if match else ''


def description_prices(description):
    prices = []
    pattern = r'(?:price\s*[:=\-]?\s*(?:NPR|Rs\.?)?\s*|(?:NPR|Rs\.?)\s*)(\d[\d,]*(?:\.\d+)?)\s*(?:/-\s*)?(lakhs?|lacs?|crores?)?\b'
    for match in re.finditer(pattern, description, re.I):
        amount = float(match[1].replace(',', ''))
        unit = (match[2] or '').casefold()
        multiplier = 10000000 if unit.startswith('crore') else 100000 if unit else 1
        prices.append(amount * multiplier)
    return sorted(set(prices))


def screen(row, document, rules):
    result = dict(row)
    flags = [flag for flag in str(row['quality_flags']).split('|')
             if flag not in ('listing_date_missing', 'asking_not_transaction_price')]
    model, variant = normalize_model(row['brand'], row['model_variant_raw'])
    result.update(model=model, variant=variant)
    if not model:
        flags.append('model_identity_ambiguous')
    description = description_text(document)
    prices = description_prices(description)
    result['description_prices_npr'] = json.dumps(prices)
    if not prices:
        flags.append('description_price_not_available_for_crosscheck')
    elif any(not math.isclose(price, row['price'], abs_tol=1, rel_tol=0) for price in prices):
        flags.append('title_description_price_conflict')
    fuel = str(row['fuel_type']).casefold()
    engine = row['engine_capacity_cc']
    if fuel in ('petrol', 'diesel') and (pd.isna(engine) or not 500 <= engine <= 7000):
        flags.append('combustion_engine_capacity_requires_review')
    if fuel in ('ev', 'electric') and pd.notna(engine) and engine != 0:
        flags.append('electric_displacement_requires_review')
    for candidate in ('petrol', 'diesel'):
        if candidate != fuel and re.search(r'\b' + candidate + r'\b', description, re.I):
            flags.append('description_fuel_requires_review')
    if re.search(r'\b(?:auto|amt|cvt|automatic)\b', variant, re.I) and str(row['transmission']).casefold() == 'manual':
        flags.append('variant_transmission_conflict')
    if str(row['transmission']).casefold() == 'manual' and re.search(
            r'\bautomatic\b(?!\s+(?:ac\b|air\b|mirror\b|climate\b|headlights?\b))', description[:180], re.I):
        flags.append('description_transmission_requires_review')
    for rule in rules:
        if row['brand'] == rule['brand'] and model == rule['model'] and row['manufacture_year'] < rule['year']:
            flags.append('predates_documented_model_introduction')
    result['review_flags'] = '|'.join(sorted(set(flags)))
    result['screening_status'] = 'needs_review' if flags else 'passed_consistency_screen'
    result['review_status'] = 'pending_human_verification'
    result['training_eligible'] = False
    result['reviewer'] = ''
    result['reviewed_at_utc'] = ''
    result['review_notes'] = ''
    return result


def equivalent(left, right):
    if pd.isna(left) and (right is None or right == ''):
        return True
    return left == right


def prediction_payload(row):
    payload = {field: row[field] for field in ('vehicle_type', 'brand', 'model', 'manufacture_year', 'km_driven')}
    for field in ('engine_capacity_cc', 'owner_count', 'fuel_type', 'transmission'):
        if pd.notna(row[field]) and row[field] != '':
            payload[field] = 'Electric' if field == 'fuel_type' and row[field] == 'EV' else row[field]
    owners = payload.get('owner_count')
    if isinstance(owners, float) and owners.is_integer():
        payload['owner_count'] = int(owners)
    return payload


def diagnose(rows):
    predictor = PricePredictor(version='v1.1.0')
    results = []
    for row in rows.to_dict('records'):
        result = {field: row[field] for field in ('record_id', 'source_url', 'brand', 'model', 'variant', 'manufacture_year', 'price')}
        result.update(diagnostic_status='excluded_screening', predicted_price_npr=None,
                      signed_error_npr=None, absolute_percentage_error=None, warning_codes='', input_json='', exclusion_reason='')
        if row['screening_status'] == 'passed_consistency_screen':
            payload = prediction_payload(row)
            result['input_json'] = json.dumps(payload, sort_keys=True)
            try:
                prediction = predictor.predict(payload, valuation_year=2026)
                error = prediction['predicted_price'] - row['price']
                result.update(diagnostic_status='predicted', predicted_price_npr=prediction['predicted_price'],
                              signed_error_npr=error, absolute_percentage_error=abs(error) / row['price'] * 100,
                              warning_codes='|'.join(sorted({item['code'] for item in prediction['warnings']})))
            except PredictionInputError as error:
                result.update(diagnostic_status='unsupported:' + error.code, exclusion_reason=str(error))
        results.append(result)
    diagnostics = pd.DataFrame(results)
    accepted = diagnostics.loc[diagnostics.diagnostic_status.eq('predicted')]
    summary = {'attempted_rows': int(rows.screening_status.eq('passed_consistency_screen').sum()),
               'predicted_rows': len(accepted), 'status_counts': diagnostics.diagnostic_status.value_counts().to_dict(),
               'model_version': predictor.version,
               'interpretation': 'Exploratory asking-price comparison only; not an independent verified market test. Missing region and condition use estimator defaults. No tuning or correction factors are fitted.'}
    if not accepted.empty:
        summary.update(mae_npr=float(accepted.signed_error_npr.abs().mean()),
                       mean_signed_error_npr=float(accepted.signed_error_npr.mean()),
                       median_absolute_percentage_error=float(accepted.absolute_percentage_error.median()),
                       below_asking_price_rows=int(accepted.signed_error_npr.lt(0).sum()),
                       predicted_brand_counts=accepted.brand.value_counts().to_dict(),
                       predicted_model_counts=accepted.model.value_counts().to_dict())
    return diagnostics, summary


def run(source=SOURCE, output=OUTPUT):
    if output.exists():
        raise FileExistsError('Review output already exists; select a new version directory')
    source_manifest = json.loads(source.with_name('manifest.json').read_text(encoding='utf-8'))
    if digest(source) != source_manifest['csv_sha256']:
        raise ValueError('Collected CSV checksum mismatch')
    verify_snapshots(source)
    source_rows = pd.read_csv(source)
    rules_path = ROOT / 'data/model_year_rules.json'
    rules = json.loads(rules_path.read_text(encoding='utf-8'))['rules']
    reviewed = []
    for row in source_rows.to_dict('records'):
        document = (ROOT / row['snapshot_path']).read_bytes().decode('utf-8')
        parsed = parse_listing(document, row['source_url'], row['captured_at_utc'])
        for field, value in parsed.items():
            if not equivalent(row[field], value):
                raise ValueError(f"Extraction mismatch for {row['record_id']}: {field}")
        reviewed.append(screen(row, document, rules))
    rows = pd.DataFrame(reviewed)
    duplicate_columns = ['brand', 'model', 'variant', 'manufacture_year', 'km_driven', 'engine_capacity_cc', 'fuel_type', 'transmission']
    duplicate_mask = rows.duplicated(duplicate_columns, keep=False)
    for index in rows.index[duplicate_mask]:
        rows.at[index, 'review_flags'] = '|'.join(filter(None, [rows.at[index, 'review_flags'], 'possible_repost_same_specifications']))
        rows.at[index, 'screening_status'] = 'needs_review'
    diagnostics, diagnostic_summary = diagnose(rows)
    output.mkdir(parents=True)
    rows.to_csv(output / 'review_queue.csv', index=False)
    diagnostics.to_csv(output / 'legacy_model_diagnostic.csv', index=False)
    summary = {'source': str(source.relative_to(ROOT)), 'source_sha256': digest(source),
               'script_sha256': digest(__file__), 'rules_sha256': digest(rules_path),
               'model_manifest_sha256': digest(ROOT / 'models/v1.1.0/manifest.json'),
               'inference_source_sha256': {name: digest(ROOT / name) for name in ['ml/predict.py', 'ml/catalog.py', 'ml/features.py']},
               'rows': len(rows), 'screening_counts': rows.screening_status.value_counts().to_dict(),
               'flag_counts': rows.review_flags.str.split('|').explode().value_counts().drop('', errors='ignore').to_dict(),
               'training_approved': False, 'deployment_approved': False, 'diagnostic': diagnostic_summary,
               'limitations': ['Consistency with a saved page does not independently verify its claims.',
                               'Listing dates, transaction prices and representative market coverage remain unavailable.',
                               'Blank reviewer fields must be completed after evidence-based human review.',
                               'Screening and model coverage determine the diagnostic subset; it is not representative.',
                               'Normalization preserves distinct i20 Active and Grand i10 Nios identities.',
                               'Price labels are unchanged, including zero and conflicting prices in the review queue.'],
               'output_sha256': {name: digest(output / name) for name in ['review_queue.csv', 'legacy_model_diagnostic.csv']}}
    (output / 'manifest.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    run(output=args.output.resolve())
