"""Semantic rejection, catalog coverage, and persistence boundaries."""
import json
from io import BytesIO
from unittest.mock import patch

import pandas as pd
import pytest
from pypdf import PdfReader
from ml.predict import PricePredictor, PredictionInputError, validate, validate_feasibility
from ml.train import ROOT
from test_backend import api, predictor, sign_in


def spec(kind='Car', brand='Tata', model='Nexon', year=2023, **fields):
    return dict(vehicle_type=kind, brand=brand, model=model, manufacture_year=year, km_driven=20000, **fields)


REJECT = [
    spec('Bike', 'Bajaj', 'Pulsar 150', 2020, fuel_type='Diesel'),
    *[spec('Bike', 'Yamaha', 'FZ V3', 2022, fuel_type=f) for f in ['Electric','CNG','LPG','Hybrid']],
    spec('Scooter','Honda','Dio',2022,fuel_type='Diesel'),
    spec('Scooter','Yadea','C1S',2019,fuel_type='LPG'),
    spec('Car','Maruti Suzuki','Alto',2020,fuel_type='Diesel'),
    spec('Car','Mahindra','Scorpio',2020,fuel_type='Petrol'),
    spec('Car','BYD','Atto 3',2024,fuel_type='Diesel'),
    *[spec('Car','Toyota','Corolla',2020,fuel_type=f) for f in ['CNG','Hybrid','LPG','Dsl']],
    spec('Car','BYD','Dolphin',2023,fuel_type='Petrol',engine_capacity_cc=0),
    spec('Car','Toyota','Corolla',2020,fuel_type='Petrol',engine_capacity_cc=2755),
    spec('Car','Mahindra','Scorpio',2020,engine_capacity_cc=500),
    spec('Bike','KTM','Duke 390',2022,engine_capacity_cc=5000),
    spec('Bike','Hero','Splendor',2020,engine_capacity_cc=50),
    *[spec('Scooter','Honda','Activa',2022,engine_capacity_cc=c) for c in [1500,0]],
    spec(motor_power_kw=50), spec('Bike','Yamaha','FZ V3',2022,motor_power_kw=1.5),
    spec('Scooter','Honda','Dio',2022,fuel_type='Petrol',motor_power_kw=2),
    *[spec('Scooter','Yadea','C1S',2019,motor_power_kw=p) for p in [0.01,9500]],
    spec('Bike','Yamaha','FZ V3',2022,transmission='Automatic'),
    spec('Scooter','TVS','NTorq 125',2022,transmission='Manual'),
    *[spec('Car','Maruti Suzuki','Alto',2020,body_type=b) for b in ['Sedan','SUV','MPV','Pickup','Coupe']],
    spec('Bike','TVS','Apache RTR 160',2021,body_type='SUV'),
    spec(region='Delhi'), spec(condition='Mint'), spec(owner_count=99), spec(seats=100), spec(gears=6),
    spec('Bike','Bajaj','Splendor',2021), spec('Bike','Toyota','Corolla',2020),
    spec('Car','TVS','Apache RTR 160',2021), spec('Bike','Honda','Dio',2022),
    dict(spec(year=2025),km_driven=5000000), dict(spec('Bike','Yamaha','FZ V3',2022),km_driven=9999999),
    dict(spec('Car','BYD','Atto 3',2026),km_driven=800000),
    spec(year=2026,owner_count=5), dict(spec(year=2026,condition='Poor'),km_driven=0),
    spec('Bike','KTM','Adventure 250',2014), spec('Bike','KTM','Adventure 250',2024),
    spec('Scooter','Hero','Pleasure',2025), spec('Bike','Yamaha','FZ V3',2026),
    spec('Car','Toyota','Corolla',2010), spec('Bike','Royal Enfield','Standard 350',1950),
    spec(year=1950), spec('Bike','Yamaha','FZ V3',1950), spec('Scooter','TVS','NTorq 125',1950),
    spec('Bike','Yamaha','\u200b---',2022), spec('Car','Tesla','Cybertruck',2024),
]


@pytest.mark.parametrize('payload', REJECT)
def test_reject_before_estimation(predictor, payload):
    with patch.object(predictor._load(payload['vehicle_type'])[0], 'predict', side_effect=AssertionError('estimator must not run')):
        with pytest.raises(PredictionInputError) as error:
            predictor.predict(payload, valuation_year=2026)
    assert error.value.code and str(error.value)


@pytest.mark.parametrize('payload', REJECT)
def test_http_rejections_never_persist(api, payload):
    client, app = api
    _, headers = sign_in(client)
    response = client.post('/api/v1/predictions', json=payload, headers=headers)
    assert response.status_code == 422, response.text
    error = response.json()['error']
    assert error['code'] and error['message']
    assert client.get('/api/v1/predictions').json()['data']['total'] == 0


ACCEPT = [
    *[spec('Car','Toyota','Corolla',y,fuel_type='Petrol',engine_capacity_cc=1798,transmission='Manual',body_type='Sedan',region='Bagmati') for y in range(2011,2026)],
    *[spec('Car','Mahindra','Scorpio',y,fuel_type='Diesel',engine_capacity_cc=2179,body_type='SUV') for y in range(2011,2026)],
    *[spec('Car','BYD','Atto 3',y,fuel_type='Electric',engine_capacity_cc=0) for y in range(2022,2026)],
    *[spec('Bike','Yamaha','FZ V3',y,fuel_type='Petrol',engine_capacity_cc=149) for y in range(2019,2026)],
    *[spec('Scooter','TVS','NTorq 125',y,transmission='Automatic') for y in range(2018,2026)],
    dict(spec(year=2025,owner_count=1,condition='Excellent'),km_driven=0),
    spec('Bike','Bajaj','Pulsar 150',2020), spec('Scooter','Yadea','C1S',2019,motor_power_kw=1.5),
    spec('Bike','Royal Enfield','Scram 411',2024), spec('Car','Toyota','Fortuner',2020,fuel_type=''),
    spec('Bike','Yamaha\u200b','fz v3',2022),
]


@pytest.mark.parametrize('payload', ACCEPT)
def test_supported_examples(predictor, payload):
    result = predictor.predict(payload, valuation_year=2026)
    assert result['predicted_price'] > 0
    assert result['reference_year'] == 2026


def test_catalog_uses_all_clean_descriptions_with_true_fitting_counts(predictor):
    data = pd.concat([pd.read_csv(ROOT / p) for p in predictor.manifest['input_sha256']])
    for kind in ('Car','Bike','Scooter'):
        catalog = predictor.catalog(kind)
        assert {(r['brand'], r['model']) for r in catalog} == set(zip(data[data.vehicle_type == kind].brand, data[data.vehicle_type == kind].model))
        assert sum(r['training_rows'] for r in catalog) == predictor._load(kind)[1]['fit_rows']
        assert all(r['min_year'] <= r['max_year'] for r in catalog)
    quarantine = pd.read_csv(ROOT / 'data/processed/feasibility-v1/quarantine.csv')
    assert len(quarantine) == 4
    assert not data.manufacture_year.eq(1980).any()
    assert set(data.reference_year) == {2026}
    assert set(data.source_reference_year) == {2025,2026}


def test_rounding_and_nonfinite_outputs_fail_before_db(api):
    client, app = api
    _, headers = sign_in(client)
    for value in [0.003, 0, -1, float('nan'), float('inf'), 1e30]:
        with patch.object(app.state.predictor._load('Bike')[0], 'predict', return_value=[value]):
            response = client.post('/api/v1/predictions', json=spec('Bike', 'Yamaha', 'FZ V3', 2022), headers=headers)
        assert response.status_code == 422 and response.json()['error']['code'] == 'invalid_price'
    assert client.get('/api/v1/predictions').json()['data']['total'] == 0


def test_new_vehicle_coherence_and_low_odometer(predictor):
    from copy import deepcopy
    catalogs = {kind: deepcopy(predictor.catalog(kind)) for kind in ('Car','Bike','Scooter')}
    next(e for e in catalogs['Car'] if e['model'] == 'Nexon')['max_year'] = 2026
    for fields in [dict(km_driven=1001),dict(km_driven=0,owner_count=2),dict(km_driven=0,condition='Poor')]:
        with pytest.raises(PredictionInputError):
            validate_feasibility(validate(dict(spec(year=2026),**fields),2026), catalogs, 2026)
    result = predictor.predict(dict(spec('Car','Toyota','Corolla',2011),km_driven=500), valuation_year=2026)
    assert 'low_odometer' in {w['code'] for w in result['warnings']}


def test_unicode_canonicalization_and_blank_fuel(api):
    client, app = api
    _, headers = sign_in(client)
    payload = spec('Bike',' Yamaha\u200b ', 'fz\u200c v3', 2022, fuel_type='', city='Kath\ufeffmandu')
    response = client.post('/api/v1/predictions',json=payload,headers=headers)
    assert response.status_code == 201
    saved = response.json()['data']['specifications']
    assert (saved['brand'],saved['model'],saved['city'],saved['fuel_type']) == ('Yamaha','FZ V3','Kathmandu',None)


def test_age_warning_names_the_input_field():
    model = PricePredictor()
    metadata = model._load('Car')[1]
    metadata['numeric_training_ranges']['vehicle_age'] = {'min':0,'max':1}
    warnings = model.predict(spec())['warnings']
    assert any(w.get('field') == 'manufacture_year' for w in warnings)
    assert not any(w.get('field') == 'vehicle_age' for w in warnings)


def test_electric_displacement_is_zero_even_when_omitted(predictor):
    estimator = predictor._load('Scooter')[0]
    with patch.object(estimator,'predict',wraps=estimator.predict) as estimate:
        predictor.predict(spec('Scooter','Yadea','C1S',2019,motor_power_kw=1.5))
    assert estimate.call_args.args[0].iloc[0]['engine_capacity_cc'] == 0


def test_unused_fields_prominent_in_pdf_and_not_specifications(api):
    client, app = api
    _, headers = sign_in(client)
    response = client.post('/api/v1/predictions', json=spec('Bike', 'Yamaha', 'FZ V3', 2022, color='UniquePaint123',city='UniqueCity123'), headers=headers)
    assert response.status_code == 201
    row = response.json()['data']
    assert set(row['result']['ignored_input_fields']) == {'city','color'}
    report = client.get(f"/api/v1/predictions/{row['id']}/report.pdf")
    text = '\n'.join(p.extract_text() for p in PdfReader(BytesIO(report.content)).pages)
    assert 'Inputs not used for this price' in text
    assert 'UniquePaint123' not in text and 'UniqueCity123' not in text


def test_year_catalog_api_and_reseed(api):
    client, app = api
    from backend.migrations import seed_catalog
    seed_catalog(app.state.sessions, app.state.predictor)
    for kind,brand,model,low,high in [('Car','Toyota','Corolla',2011,2025),('Scooter','Hero','Pleasure',2004,2012)]:
        rows = client.get('/api/v1/catalog/models', params={'vehicle_type':kind,'brand':brand}).json()['data']
        entry = next(r for r in rows if r['model'] == model)
        assert (entry['min_year'],entry['max_year']) == (low,high)
        assert entry['constraints']['reference_year'] == 2026
