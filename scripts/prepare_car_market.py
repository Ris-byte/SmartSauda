"""Create source-separated research data with field evidence and explicit admission limits."""
import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.collect_nepal_car_listings import parse_listing, plain, verify_snapshots
from scripts.review_nepal_car_listings import description_text, normalize_model, screen

OUTPUT = ROOT / 'data/processed/nepal-car-market-v2'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def claim_fields(description):
    drive = re.search(r'\b(4\s*[xX]\s*4|4\s*WD|2\s*WD|AWD|FWD|RWD)\b', description, re.I)
    drivetrain = re.sub(r'\s+', '', drive[1]).upper() if drive else ''
    if drivetrain == '4X4':
        drivetrain = '4WD'
    condition = re.search(r'\b(?:excellent|good|fresh|fair|poor)\s+condition\b|\bwell[- ]maintained\b|\bcondition\s*[:=-]\s*(?:excellent|good|fresh|fair|poor)\b', description, re.I)
    return drivetrain, condition[0] if condition else ''


def enrich(row, description, role):
    drive, condition = claim_fields(description)
    row.update(drivetrain=drive, condition_claim=condition, condition_basis='seller_description_unverified',
               acquisition_role=role, price_basis='asking', actual_sale_price_npr=None,
               listing_date=row.get('listing_date', ''), review_method='automated_saved_page_crosscheck',
               independently_verified=False, market='Nepal', currency='NPR', reference_year=2026)
    row['missing_evidence'] = '|'.join(field for field in ('listing_date', 'variant', 'drivetrain', 'condition_claim') if not row.get(field))
    row['source_sha256'] = row['snapshot_sha256']
    row['description_evidence'] = description[:220]
    return row


def atal_row(record, document, rules):
    parsed = parse_listing(document, record['url'], record['captured_at_utc'])
    parsed['snapshot_path'] = record['path']
    row = screen(parsed, document, rules)
    if parsed['brand'] == 'Toyota' and re.match(r'Fortuner\b', parsed['model_variant_raw'], re.I):
        row['model'] = 'Fortuner'
        row['variant'] = ''
        row['review_flags'] = '|'.join(flag for flag in row['review_flags'].split('|') if flag != 'model_identity_ambiguous')
        row['screening_status'] = 'needs_review' if row['review_flags'] else 'passed_consistency_screen'
    return enrich(row, description_text(document), record['role'])


def hamro_row(record, document):
    title = plain(re.search(r'<title[^>]*>(.*?)</title>', document, re.S)[1]).split(' | ')[0]
    about = re.search(r'<h2[^>]*>About This Car</h2>(.*?)(?:<h[23][^>]*>Description|Description)', document, re.S | re.I)
    if not about:
        raise ValueError('Missing vehicle specification section')
    fields = [plain(value) for value in re.findall(r'<p[^>]*>(.*?)</p>', about[1], re.S)]
    if len(fields) != 6:
        raise ValueError(f'Unexpected specification fields: {fields}')
    fuel, mileage, transmission_raw, body, color, year = fields
    price_match = re.search(r'<h2[^>]*>\s*Rs\.?\s*([\d,]+)\s*</h2>', document, re.I)
    if not price_match or not year.isdigit():
        raise ValueError('Price or year is not an unambiguous numeric value')
    price = float(price_match[1].replace(',', ''))
    distance = re.fullmatch(r'([\d,]+)\s*KM', mileage, re.I)
    km = float(distance[1].replace(',', '')) if distance else None
    variant_raw = re.sub(r'^Hyundai\s+', '', title, flags=re.I)
    variant_raw = re.sub(r'\b\d{4}\b.*$', '', variant_raw).strip(' .')
    model, variant = normalize_model('Hyundai', variant_raw)
    description_match = re.search(r'>\s*Description\s*</h[23]>(.*?)(?:<h[23]|Enquiry)', document, re.S | re.I)
    description = plain(description_match[1]) if description_match else ''
    flags = []
    title_years = re.findall(r'\b(?:19|20)\d{2}\b', title)
    if title_years and any(value != year for value in title_years):
        flags.append('title_specification_year_conflict')
    if not model:
        flags.append('model_identity_ambiguous')
    if not 300000 <= price <= 30000000:
        flags.append('price_requires_review')
    if km is None or not 0 < km <= 300000:
        flags.append('odometer_requires_review')
    transmission = 'Automatic' if re.search(r'Automatic|AMT|CVT', transmission_raw, re.I) else 'Manual' if 'manual' in transmission_raw.lower() else ''
    if re.search(r'\b(?:AMT|CVT|Automatic|Auto)\b', title, re.I) and transmission == 'Manual':
        flags.append('title_transmission_conflict')
    if not transmission or fuel not in ('Petrol', 'Diesel', 'Electric'):
        flags.append('unrecognized_fuel_or_transmission')
    row = {'record_id': 'hamroauto:' + hashlib.sha256(record['url'].encode()).hexdigest()[:20],
           'source_url': record['url'], 'source_id': 'hamroautomobiles_public_asking_prices',
           'captured_at_utc': record['captured_at_utc'], 'snapshot_path': record['path'],
           'snapshot_sha256': record['sha256'], 'vehicle_type': 'Car', 'brand': 'Hyundai',
           'model': model, 'variant': variant, 'model_variant_raw': variant_raw,
           'manufacture_year': int(year), 'km_driven': km, 'price': price,
           'engine_capacity_cc': None, 'owner_count': None, 'fuel_type': fuel, 'transmission': transmission,
           'body_type': body, 'listing_status': 'not_confirmed', 'review_flags': '|'.join(flags),
           'screening_status': 'needs_review' if flags else 'passed_consistency_screen',
           'review_status': 'research_evidence_screen_only', 'training_eligible': False}
    row = enrich(row, description, 'external_evaluation')
    row['drivetrain'] = claim_fields(transmission_raw)[0]
    row['missing_evidence'] = '|'.join(field for field in ('listing_date', 'variant', 'drivetrain', 'condition_claim') if not row.get(field))
    return row


def older_fortuner_reference(record, document):
    text = plain(re.sub(r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>', '', document, flags=re.S | re.I))
    attributes = re.search(r'Attributes(.*?)(?:profile|Contact)', text, re.I)
    if not attributes:
        raise ValueError('Missing reference attributes')
    values = attributes[1]
    def field(pattern):
        match = re.search(pattern, values, re.I)
        return match[1] if match else ''
    price = re.search(r'रु\s*([\d,]+)', text)
    if not price:
        raise ValueError('No NPR asking price found')
    year, km, engine = field(r'Make Year:\s*(\d{4})'), field(r'Kilometers:\s*([\d,]+)'), field(r'Engine\(CC\):\s*(\d+)')
    row = {'record_id': 'nepalbuysell:3578', 'source_url': record['url'], 'source_id': 'nepalbuysell_reference',
           'captured_at_utc': record['captured_at_utc'], 'snapshot_path': record['path'], 'snapshot_sha256': record['sha256'],
           'vehicle_type': 'Car', 'brand': 'Toyota', 'model': 'Fortuner', 'variant': '',
           'model_variant_raw': 'Fortuner', 'manufacture_year': int(year) if year else None,
           'km_driven': float(km.replace(',', '')) if km else None, 'engine_capacity_cc': float(engine) if engine else None,
           'price': float(price[1].replace(',', '')), 'fuel_type': field(r'Energy:\s*(\w+)'),
           'transmission': 'Manual' if 'Manual' in values else '', 'owner_count': None,
           'review_flags': 'old_listing_reference_only|listing_date_unverified', 'screening_status': 'needs_review',
           'review_status': 'reference_only', 'training_eligible': False, 'listing_status': 'not_confirmed'}
    row = enrich(row, 'In good condition' if 'In good condition' in text else '', 'fortuner_reference')
    row['drivetrain'] = claim_fields(values)[0]
    row['listing_date_text'] = next(iter(re.findall(r'Posted\s+\d+\s+years?\s+ago', text, re.I)), '')
    return row


def group_key(row):
    distance = row['km_driven']
    bucket = int(float(distance) // 2000) if pd.notna(distance) else 'unknown'
    return '|'.join([str(row['brand']).casefold(), str(row['model']).casefold(), str(row['manufacture_year']), str(bucket)])


def run():
    if OUTPUT.exists():
        raise FileExistsError('Dataset versions are immutable')
    rules = json.loads((ROOT / 'data/model_year_rules.json').read_text())['rules']
    original = ROOT / 'data/external/nepal_car_listings_2026-10-04/listings.csv'
    verify_snapshots(original)
    review_manifest = json.loads((ROOT / 'data/processed/car-listing-review-v3/manifest.json').read_text())
    if sha256(original) != review_manifest['source_sha256']:
        raise ValueError('Original capture hash mismatch')
    rows, failures = [], []
    for row in pd.read_csv(original).to_dict('records'):
        document = (ROOT / row['snapshot_path']).read_bytes().decode('utf-8')
        rows.append(enrich(screen(row, document, rules), description_text(document), 'development'))
    manifest_path = ROOT / 'data/external/car-market-2026-10-05-external/manifest.json'
    for record in json.loads(manifest_path.read_text())['records']:
        if record['role'] == 'index':
            continue
        path = ROOT / record['path']
        if sha256(path) != record['sha256']:
            raise ValueError('Captured evidence hash mismatch')
        document = path.read_bytes().decode('utf-8')
        try:
            row = hamro_row(record, document) if record['role'] == 'external_evaluation' else atal_row(record, document, rules) if 'atalauto' in record['url'] else older_fortuner_reference(record, document)
            rows.append(row)
        except (ValueError, AttributeError, IndexError) as error:
            failures.append({'url': record['url'], 'reason': str(error), 'snapshot_path': record['path']})
    data = pd.DataFrame(rows)
    data['group_id'] = data.apply(group_key, axis=1)
    passed = data.screening_status.eq('passed_consistency_screen')
    development = passed & data.source_id.eq('atalauto_public_asking_prices')
    duplicates = data.loc[development].group_id.duplicated(keep=False)
    for index in duplicates.index[duplicates]:
        data.at[index, 'review_flags'] = 'possible_repost_same_model_year_mileage'
        data.at[index, 'screening_status'] = 'needs_review'
    development &= data.screening_status.eq('passed_consistency_screen')
    development_groups = set(data.loc[development, 'group_id'])
    external = passed & data.acquisition_role.eq('external_evaluation')
    overlap = external & data.group_id.isin(development_groups)
    external_duplicates = data.loc[external].group_id.duplicated(keep=False)
    for index in set(data.index[overlap]) | set(external_duplicates.index[external_duplicates]):
        data.at[index, 'review_flags'] = 'possible_repost_within_or_across_sources'
        data.at[index, 'screening_status'] = 'needs_review'
    external &= data.screening_status.eq('passed_consistency_screen')
    data['research_training_eligible'] = development
    data['external_evaluation_eligible'] = external
    data['training_eligible'] = False
    data['review_status'] = 'automated_evidence_review_not_market_verification'
    OUTPUT.mkdir(parents=True)
    files = {'reviewed_records.csv': data, 'research_development.csv': data.loc[development],
             'external_evaluation.csv': data.loc[external], 'quarantine.csv': data.loc[~(development | external)],
             'fortuner_evidence.csv': data.loc[data.model.eq('Fortuner')]}
    for name, subset in files.items():
        subset.to_csv(OUTPUT / name, index=False)
    manifest = {'rows': len(data), 'development_rows': int(development.sum()), 'external_rows': int(external.sum()),
                'quarantine_rows': int((~(development | external)).sum()), 'parse_failures': failures,
                'development_source': 'atalauto_public_asking_prices', 'external_source': 'hamroautomobiles_public_asking_prices',
                'target': 'Nepal seller asking price in NPR; never transaction value', 'training_scope': 'research_only',
                'deployment_approved': False, 'source_capture_sha256': sha256(manifest_path),
                'script_sha256': sha256(__file__), 'research_review_method': 'automated_saved_page_crosscheck',
                'original_listing_dates_verified': False, 'vehicle_independence_verified': False,
                'notes': ['Missing variant, drivetrain, engine or seller condition remain missing.',
                          'Source separation and duplicate heuristics do not establish independent vehicle identity.',
                          'Sold advertised amounts are not completed-sale prices and are excluded.',
                          'No unverified local-source price labels are admitted.'],
                'outputs': {name: {'rows': len(subset), 'sha256': sha256(OUTPUT / name)} for name, subset in files.items()}}
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    run()
