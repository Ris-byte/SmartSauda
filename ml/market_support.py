"""Fail-closed public car valuation policy; offline historical diagnostics are separate."""
from ml.predict import PredictionInputError

CAR_MARKET_MESSAGE = 'Car estimates use advertised asking prices from Nepal listings; advertised prices may differ from final sale prices.'


def public_market_status(vehicle_type):
    if vehicle_type == 'Car':
        return {'vehicle_type': 'Car', 'available': True, 'price_basis': 'advertised_asking',
                'code': 'asking_price_estimate', 'message': CAR_MARKET_MESSAGE,
                'validated_segments': [], 'validated_model_version': None}
    return {'vehicle_type': vehicle_type, 'available': True, 'price_basis': 'historical_source_labels',
            'message': 'Historical research estimates; current Nepal market accuracy is not verified.'}


def require_public_market_support(payload):
    kind = str(payload.get('vehicle_type', '')).strip().title()
    status = public_market_status(kind)
    if not status['available']:
        raise PredictionInputError(status['message'], status['code'], 'vehicle_type')
