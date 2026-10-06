"""Evidence screening must preserve prices and never silently grant training approval."""
import json

import pandas as pd
import pytest

from scripts.review_nepal_car_listings import ROOT, OUTPUT, description_prices, normalize_model, prediction_payload, screen


@pytest.mark.parametrize('text,expected', [
    ('Price: Rs. 44 Lakhs (Negotiable)', [4400000]),
    ('Price: NPR 45.50 Lakhs', [4550000]),
    ('Rs. 45,50,000', [4550000]),
    ('Price: NPR 1.2 crore', [12000000]),
    ('Price = 14,25,000', [1425000]),
    ('Price = 13.75 /- Lakhs', [1375000]),
    ('Price , contact us', []),
    ('Odometer: 38,000 km. Call 9800000000', []),
])
def test_price_units(text, expected):
    assert description_prices(text) == expected


@pytest.mark.parametrize('raw,model,variant', [
    ('Grand I 10 Magna', 'Grand i10', 'Magna'),
    ('Grand i10 Nios Sportz', 'Grand i10 Nios', 'Sportz'),
    ('I 20 Active S', 'i20 Active', 'S'),
    ('I 20 Elite Asta', 'i20', 'Elite Asta'),
    ('Grand Magna', '', 'Grand Magna'),
])
def test_model_variants_remain_distinct(raw, model, variant):
    assert normalize_model('Hyundai', raw) == (model, variant)


def listing(**updates):
    return dict(brand='Hyundai', model_variant_raw='Creta S', manufacture_year=2021,
                price=440000, fuel_type='Petrol', engine_capacity_cc=1497, transmission='Manual',
                quality_flags='listing_date_missing|asking_not_transaction_price', **updates)


def test_conflicting_prices_remain_unchanged_and_unapproved():
    document = '<h2>Description</h2><p>Price: Rs. 44 Lakhs</p><h2>Features</h2>'
    result = screen(listing(), document, [])
    assert result['price'] == 440000
    assert 'title_description_price_conflict' in result['review_flags']
    assert result['training_eligible'] is False
    assert result['reviewer'] == ''


def test_passing_screen_is_not_human_approval():
    document = '<h2>Description</h2><p>Price: Rs. 4.4 Lakhs</p><h2>Features</h2>'
    result = screen(listing(), document, [])
    assert result['screening_status'] == 'passed_consistency_screen'
    assert result['review_status'] == 'pending_human_verification'
    assert result['training_eligible'] is False


def test_ambiguous_engine_and_transmission_are_not_corrected():
    row = listing()
    row.update(engine_capacity_cc=16000, model_variant_raw='Creta AMT')
    result = screen(row, '<h2>Description</h2><p>Price: Rs. 4.4 Lakhs</p>', [])
    assert 'combustion_engine_capacity_requires_review' in result['review_flags']
    assert 'variant_transmission_conflict' in result['review_flags']
    assert result['engine_capacity_cc'] == 16000 and result['transmission'] == 'Manual'


def test_description_transmission_conflict_does_not_confuse_auto_ac():
    result = screen(listing(), '<h2>Description</h2>Creta SX Automatic. Price: Rs. 4.4 Lakhs', [])
    assert 'description_transmission_requires_review' in result['review_flags']
    result = screen(listing(), '<h2>Description</h2>Creta with automatic air conditioning. Price: Rs. 4.4 Lakhs', [])
    assert 'description_transmission_requires_review' not in result['review_flags']


def test_generated_review_accounts_for_every_original_price():
    source = pd.read_csv(ROOT / 'data/external/nepal_car_listings_2026-10-04/listings.csv').set_index('record_id')
    reviewed = pd.read_csv(OUTPUT / 'review_queue.csv').set_index('record_id')
    pd.testing.assert_series_equal(source.price.sort_index(), reviewed.price.sort_index())
    assert len(reviewed) == 79 and reviewed.index.is_unique
    assert not reviewed.training_eligible.any()
    assert reviewed.reviewer.isna().all()
    manifest = json.loads((OUTPUT / 'manifest.json').read_text())
    assert sum(manifest['screening_counts'].values()) == 79
    assert not manifest['training_approved'] and not manifest['deployment_approved']


def test_csv_owner_counts_are_losslessly_converted_to_api_integers():
    row = dict(vehicle_type='Car', brand='Hyundai', model='Creta', manufacture_year=2021,
               km_driven=38000, engine_capacity_cc=1498, owner_count=1.0, fuel_type='Petrol', transmission='Manual')
    assert type(prediction_payload(row)['owner_count']) is int
    row['owner_count'] = 1.5
    assert prediction_payload(row)['owner_count'] == 1.5


def test_diagnostic_evaluates_supported_rows_without_bypassing_validation():
    results = pd.read_csv(OUTPUT / 'legacy_model_diagnostic.csv')
    assert results.diagnostic_status.eq('predicted').any()
    assert results.diagnostic_status.str.startswith('unsupported:').any()
    assert not results.diagnostic_status.eq('unsupported:invalid_prediction').any()
