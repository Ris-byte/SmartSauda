import copy
import json

import pytest

from scripts.build_multisite_car_dataset import (
    ROOT, condition, date_only, deduplicate, drivetrain, empty_row,
    match_identity, numeric, parse_hamro, parse_usedcar, price, review,
)
from bs4 import BeautifulSoup


@pytest.mark.parametrize('raw,expected', [
    ('Rs 1,55,00,000', 15500000), ('NRs 6,000,000.00', 6000000),
    ('29,.50', None), ('Rs. 29,50', None), ('', None), ('1550000', 1550000),
])
def test_unambiguous_price_only(raw, expected):
    assert price(raw) == expected


def test_distance_is_not_fuel_economy():
    assert numeric('42000 km') == 42000
    assert numeric('18 km/l') is None
    assert numeric('KM') is None


def test_claims_are_not_marketing_boilerplate():
    assert condition('Excellence Condition Car. Excellent driving dynamics.') is None
    assert condition('well-maintained vehicle') == 'well-maintained'
    assert drivetrain('Manual 4x4') == '4WD'
    assert date_only('Sep 26, 2026') == '2026-09-26'


def test_identity_keeps_model_families_separate():
    assert match_identity('Hyundai Grand i10 Nios magna 2022') == ('Hyundai', 'Grand i10 Nios', 'magna')
    assert match_identity('Toyota Fortuner 2011') == ('Toyota', 'Fortuner', None)
    assert match_identity('Honda City 2013')[:2] == ('Honda', 'City')
    assert match_identity('Kia Sonet HTE', 'KIA') == ('Kia', 'Sonet', 'HTE')
    assert match_identity('SKODA Rapid(VOLKSWAGEN GROUP COMPANY) 2014')[:2] == ('Skoda', 'Rapid')


def test_dedup_does_not_merge_different_cars_with_generic_specs():
    first = empty_row('example.com', 'https://example.com/1', {'captured_at_utc': '2026-10-05'}, [])
    first.update(brand='Toyota', model='Fortuner', model_year=2011, odometer_km=100000, listing_id='1')
    second = copy.deepcopy(first)
    second.update(source_url='https://example.com/2', listing_id='2', record_id='second')
    rows = deduplicate([first, copy.deepcopy(first), second])
    assert len(rows) == 2
    assert rows[0]['possible_duplicate_group'] == rows[1]['possible_duplicate_group']


def test_conflicts_do_not_rewrite_prices():
    row = empty_row('example.com', 'https://example.com/1', {'captured_at_utc': '2026-10-05'}, [])
    row.update(title='Toyota Fortuner 2011 Automatic', model_year=2014, transmission='Manual', asking_price_npr=1000000)
    review(row, 'Asking price Rs 50,00,000')
    assert row['asking_price_npr'] == 1000000
    assert 'title_specification_year_conflict' in row['quality_flags']
    assert 'title_transmission_conflict' in row['quality_flags']
    assert 'description_price_differs_requires_context_review' in row['quality_flags']
    assert row['actual_sale_price_npr'] is None
    assert not row['training_eligible']


def test_description_odometer_excludes_ev_range_and_warranty():
    row = empty_row('example.com', 'https://example.com/1', {'captured_at_utc': '2026-10-05'}, [])
    row.update(title='BYD Dolphin 2024', model_year=2024, fuel_type='Electric')
    review(row, 'Range: 340 km. Warranty 150000 km. Only 2000 km driven.')
    assert row['odometer_km'] == 2000
    assert row['raw_fields']['description_odometer_claims_km'] == [2000]


def test_two_exact_photos_consolidate_repost_without_losing_price_history():
    first = empty_row('example.com', 'https://example.com/1', {'captured_at_utc': '2026-10-05'}, [])
    first.update(brand='Toyota', model='Fortuner', model_year=2011, odometer_km=100000,
                 listing_id='1', image_urls=['photo1', 'photo2'], asking_price_npr=5000000)
    second = copy.deepcopy(first)
    second.update(source_url='https://example.com/2', listing_id='2', record_id='second', asking_price_npr=5500000)
    rows = deduplicate([first, second], {'photo1': {'sha256': 'aaa'}, 'photo2': {'sha256': 'bbb'}})
    assert len(rows) == 1
    assert {entry['asking_price_npr'] for entry in rows[0]['duplicate_observations']} == {5000000, 5500000}
    assert len(rows[0]['duplicate_listing_urls']) == 2
    assert rows[0]['actual_sale_price_npr'] is None


def test_shared_photos_do_not_override_specification_conflicts():
    first = empty_row('example.com', 'https://example.com/1', {'captured_at_utc': '2026-10-05'}, [])
    first.update(brand='Toyota', model='Fortuner', model_year=2011, odometer_km=100000,
                 listing_id='1', image_urls=['photo1', 'photo2'], transmission='Manual')
    second = copy.deepcopy(first)
    second.update(source_url='https://example.com/2', listing_id='2', record_id='second', transmission='Automatic')
    rows = deduplicate([first, second], {'photo1': {'sha256': 'aaa'}, 'photo2': {'sha256': 'bbb'}})
    assert len(rows) == 2


def test_saved_dataset_invariants():
    path = ROOT / 'data/processed/nepal_used_cars_multisite.json'
    if not path.exists():
        pytest.skip('Run the documented public capture and normalization first')
    dataset = json.loads(path.read_text(encoding='utf-8'))
    rows = dataset['records']
    assert dataset['record_count'] == len(rows)
    assert len({row['record_id'] for row in rows}) == len(rows)
    assert not dataset['parse_errors']
    assert set(dataset['counts_by_source']) == {'www.usedcarnepal.com', 'www.ktmcarsales.com', 'www.hamroautomobiles.com.np', 'seecar.com'}
    assert all(not row['training_eligible'] and row['actual_sale_price_npr'] is None for row in rows)
    assert all(row['source_url'] and row['evidence'][0]['sha256'] for row in rows)
    assert any(row['listing_status'] == 'sold' for row in rows)
    if 'captured_advertisement_count' in dataset:
        assert dataset['captured_advertisement_count'] == len(rows) + sum(len(row.get('duplicate_observations', [])) - 1 for row in rows if row.get('duplicate_observations'))
