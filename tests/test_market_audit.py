"""Market audit boundaries and regression coverage for derived car body types."""
import json

import pandas as pd
import pytest
from sqlalchemy import select

from backend.db import CatalogEntry
from ml.predict import PricePredictor
from ml.train import ROOT, load_data, run
from scripts.audit_market_data import review_reasons
from scripts.collect_nepal_car_listings import parse_listing, verify_snapshots
from test_backend import api


@pytest.fixture(scope='module')
def predictor():
    return PricePredictor()


@pytest.mark.parametrize('brand,model,body', [
    ('Hyundai', 'Creta', 'SUV'), ('Maruti Suzuki', 'Alto', 'Hatchback'), ('Toyota', 'Corolla', 'Sedan'),
])
def test_legacy_price_does_not_depend_on_optional_body(predictor, brand, model, body):
    payload = dict(vehicle_type='Car', brand=brand, model=model, manufacture_year=2021, km_driven=38000)
    omitted = predictor.predict(payload, valuation_year=2026)
    supplied = predictor.predict(dict(payload, body_type=body), valuation_year=2026)
    assert omitted['predicted_price'] == supplied['predicted_price']
    assert 'derived_body_type' in {warning['code'] for warning in omitted['warnings']}
    entry = next(entry for entry in predictor.catalog('Car') if entry['brand'] == brand and entry['model'] == model)
    assert entry['constraints']['body_types'] == [body]


def test_catalog_overlay_does_not_mutate_frozen_metadata(predictor):
    original = json.dumps(predictor._load('Car')[1], sort_keys=True)
    catalog = predictor.catalog('Car')
    catalog[0]['constraints']['body_types'] = ['invalid']
    assert json.dumps(predictor._load('Car')[1], sort_keys=True) == original
    assert predictor.catalog('Car')[0]['constraints']['body_types'] != ['invalid']


def test_catalog_api_overrides_stale_database_body_constraint(api):
    client, app = api
    with app.state.sessions() as database:
        entry = database.scalar(select(CatalogEntry).where(CatalogEntry.brand == 'Toyota', CatalogEntry.model == 'Corolla'))
        entry.constraints = dict(entry.constraints, body_types=['SUV'])
        database.commit()
    response = client.get('/api/v1/catalog/models?vehicle_type=Car&brand=Toyota')
    assert response.status_code == 200
    corolla = next(entry for entry in response.json()['data'] if entry['model'] == 'Corolla')
    assert corolla['constraints']['body_types'] == ['Sedan']


def test_training_cannot_admit_historical_unreviewed_rows():
    config = json.loads((ROOT / 'ml/config.json').read_text())
    with pytest.raises(ValueError, match='disabled'):
        load_data(config)
    config['approval']['training_enabled'] = True
    with pytest.raises(ValueError, match='not approved for training'):
        load_data(config)
    with pytest.raises(ValueError, match='Deployment is not approved'):
        run('test-market-approval-guard', activate=True)


def test_quarantine_preserves_prices_and_partitions_all_input_rows():
    original = pd.read_csv(ROOT / 'data/processed/feasibility-v1/vehicles.csv').set_index('record_id')
    directory = ROOT / 'data/processed/market-audit-v1'
    quarantine = pd.read_csv(directory / 'quarantine.csv')
    candidates = pd.read_csv(directory / 'public_research_candidates.csv')
    combined = pd.concat([quarantine, candidates]).set_index('record_id').sort_index()
    pd.testing.assert_series_equal(combined.price, original.price.sort_index())
    assert combined.index.is_unique and len(combined) == len(original)
    assert not combined.training_eligible.any()
    assert set(candidates.source_id) == {'nepal_bikebazar_2025'}
    assert not candidates.vehicle_type.eq('Car').any()
    assert len(quarantine.loc[quarantine.source_id.eq('nepal_user_2000')]) == 1610


def test_low_price_is_reviewed_not_corrected():
    row = dict(source_id='nepal_bikebazar_2025', vehicle_type='Bike', price=13500,
               brand='TVS', model='Apache', manufacture_year=2020, listing_condition='used')
    assert 'low_asking_price' in review_reasons(row, [])
    assert row['price'] == 13500
    row.update(price=135000, listing_condition='like new')
    assert review_reasons(row, []) == ''


def test_listing_parser_does_not_invent_dates_or_approve_training():
    document = '''<title>Buy Hyundai Creta S 2021 in Nepal,Rs.4550000</title>
    <span class="listing-info-title">Status:</span><p>available</p>
    <span class="listing-info-title">Odometer:</span><p>38,000 KMs</p>'''
    row = parse_listing(document, 'https://www.atalauto.com/used-cars/example', '2026-10-04T00:00:00Z')
    assert row['price'] == 4550000 and row['km_driven'] == 38000
    assert row['listing_date'] == '' and row['training_eligible'] is False
    assert row['price_basis'] == 'asking' and row['engine_capacity_cc'] is None


def test_collected_listing_snapshots_match_recorded_hashes():
    verify_snapshots(ROOT / 'data/external/nepal_car_listings_2026-10-04/listings.csv')
