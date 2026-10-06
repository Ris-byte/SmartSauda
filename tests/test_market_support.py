"""Unvalidated car prices must not escape through the public prediction endpoint."""
from unittest.mock import patch
from sqlalchemy import select

from backend.db import Prediction
from test_backend import api, predictor, sign_in, specs


def test_fortuner_is_blocked_before_inference_and_persistence(api):
    client, app = api
    _, headers = sign_in(client)
    payload = dict(vehicle_type='Car', brand='Toyota', model='Fortuner', manufacture_year=2011, km_driven=130000)
    with patch.object(app.state.predictor, 'predict', side_effect=AssertionError('No unsupported price may be calculated')):
        response = client.post('/api/v1/predictions', json=payload, headers=headers)
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'insufficient_verified_market_data'
    assert 'Insufficient verified market data' in response.json()['error']['message']
    assert 'predicted_price' not in response.text
    assert client.get('/api/v1/predictions').json()['data']['total'] == 0


def test_public_car_status_is_explicitly_asking_price_and_unavailable(api):
    client, _ = api
    result = client.get('/api/v1/market-status?vehicle_type=Car').json()['data']
    assert result['available'] is False
    assert result['price_basis'] == 'asking'
    assert result['validated_segments'] == []
    assert client.get('/api/v1/market-status?vehicle_type=Bike').json()['data']['available'] is True


def test_historical_car_reports_and_aggregates_do_not_present_unverified_values(api):
    client, app = api
    _, headers = sign_in(client)
    saved = client.post('/api/v1/predictions', json=specs(), headers=headers).json()['data']
    with app.state.sessions() as database:
        row = database.scalar(select(Prediction))
        original_price = row.price
        row.vehicle_type = 'Car'
        row.specifications = dict(row.specifications, vehicle_type='Car')
        database.commit()
    response = client.get(f"/api/v1/predictions/{saved['id']}/report.pdf")
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'insufficient_verified_market_data'
    assert client.get('/api/v1/dashboard').json()['data']['average_price'] is None
    with app.state.sessions() as database:
        assert database.scalar(select(Prediction)).price == original_price
