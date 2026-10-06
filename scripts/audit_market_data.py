"""Separate unverified and suspicious records without modifying historical evidence."""
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'data/processed/feasibility-v1/vehicles.csv'
OUTPUT = ROOT / 'data/processed/market-audit-v1'


def review_reasons(row, rules):
    reasons = []
    if row['source_id'] == 'nepal_user_2000':
        reasons.append('unverified_local_source_excluded')
    if row['vehicle_type'] in ('Bike', 'Scooter') and row['price'] < 20000:
        reasons.append('low_asking_price_manual_review_not_automatic_correction')
    if str(row.get('listing_condition', '')).strip().casefold() not in ('used', 'like new'):
        reasons.append('used_status_unconfirmed')
    for rule in rules:
        if row['brand'] == rule['brand'] and row['model'] == rule['model'] and row['manufacture_year'] < rule['year']:
            reasons.append('predates_documented_model_introduction')
    return '|'.join(reasons)


def run():
    if (OUTPUT / 'manifest.json').exists():
        raise FileExistsError('Completed audit is immutable; use a new output version')
    rows = pd.read_csv(INPUT)
    rules_path = ROOT / 'data/model_year_rules.json'
    rules = json.loads(rules_path.read_text(encoding='utf-8'))['rules']
    rows['market_review_reasons'] = rows.apply(review_reasons, axis=1, rules=rules)
    rows['training_eligible'] = False
    rows['research_candidate'] = rows.market_review_reasons.eq('')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for name, subset in [('quarantine.csv', rows.loc[~rows.research_candidate]),
                         ('public_research_candidates.csv', rows.loc[rows.research_candidate])]:
        path = OUTPUT / name
        subset.to_csv(path, index=False)
        outputs[name] = {'rows': len(subset), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                         'vehicle_types': subset.vehicle_type.value_counts().to_dict()}
    manifest = {'input': str(INPUT.relative_to(ROOT)), 'input_sha256': hashlib.sha256(INPUT.read_bytes()).hexdigest(),
                'rules_sha256': hashlib.sha256(rules_path.read_bytes()).hexdigest(),
                'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'outputs': outputs, 'training_approved': False, 'deployment_approved': False,
                'reason_counts': rows.market_review_reasons.str.split('|').explode().value_counts().drop('', errors='ignore').to_dict(),
                'policy': ['Original prices and frozen source files remain unchanged.',
                           'Below NPR 20,000 is a conservative review trigger, not proof of an incorrect price.',
                           'Public research candidates still lack verified listing dates and per-row provenance.',
                           'Candidate status does not grant training admission or establish current Nepal market accuracy.']}
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    run()
