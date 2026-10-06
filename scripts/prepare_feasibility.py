"""Prepare the fixed-year training cohort from checksummed source datasets."""
import json
from pathlib import Path
import pandas as pd
from ml.catalog import REFERENCE_YEAR
from scripts.prepare_data import feasibility_quarantine_reason, digest, write_json

ROOT = Path(__file__).resolve().parents[1]


def build():
    manifest = json.loads((ROOT / 'data/processed/feasibility-v1/manifest.json').read_text())
    source_inputs = manifest['source_inputs']
    frames = []
    for filename, expected in source_inputs.items():
        path = ROOT / filename
        if digest(path.read_bytes()) != expected:
            raise ValueError('Frozen training input checksum mismatch')
        frames.append(pd.read_csv(path))
    rows = pd.concat(frames, ignore_index=True)
    reasons = rows.apply(lambda row: feasibility_quarantine_reason(row.to_dict()), axis=1)
    quarantine = rows.loc[reasons.notna()].copy()
    quarantine['reason'] = reasons[reasons.notna()]
    clean = rows.loc[reasons.isna()].copy()
    clean['source_reference_year'] = clean.reference_year
    clean['reference_year'] = REFERENCE_YEAR
    clean['vehicle_age'] = REFERENCE_YEAR - clean.manufacture_year
    clean['km_per_year'] = clean.km_driven.div(clean.vehicle_age.where(clean.vehicle_age > 0))
    # Watts evidence identifies these 11 electric records; never impute a petrol engine into them.
    electric = clean.motor_power_kw.notna()
    clean.loc[electric, 'engine_capacity_cc'] = 0
    clean.loc[electric, 'fuel_type'] = 'Electric'
    folder = ROOT / 'data/processed/feasibility-v1'
    folder.mkdir(parents=True, exist_ok=True)
    for filename, frame in [('vehicles.csv', clean), ('quarantine.csv', quarantine)]:
        output = frame.to_csv(index=False).encode('utf-8')
        target = folder / filename
        if target.exists() and target.read_bytes() != output:
            raise FileExistsError('Derived cohort changed; choose a new cohort version')
        target.write_bytes(output)
    write_json(folder / 'manifest.json', {'source_inputs': source_inputs, 'reference_year': REFERENCE_YEAR,
               'rows': len(clean), 'quarantined': len(quarantine), 'electric_engine_corrections': int(electric.sum()),
               'source_reference_years_preserved': True, 'vehicles_sha256': digest((folder / 'vehicles.csv').read_bytes())})
    print(f'Prepared {len(clean)} records; quarantined {len(quarantine)}; reference year {REFERENCE_YEAR}.')


if __name__ == '__main__':
    build()
