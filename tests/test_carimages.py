from io import BytesIO

import httpx
from PIL import Image

from backend.carimages import fetch_render, matches_requested_model

SPECS = dict(vehicle_type='Bike', brand='Bajaj', model='Pulsar 150', manufacture_year=2020)


def test_signed_url_redirect_and_webp():
    blob = BytesIO()
    Image.new('RGB', (20, 20)).save(blob, format='WEBP')
    calls = []
    def provider(request):
        calls.append(request)
        if request.url.path.endswith('/signed-url'):
            assert request.url.params['api_key'] == 'test-secret'
            assert request.url.params['type'] == 'moto'
            return httpx.Response(200, json={'url': 'https://carimagesapi.com/image?sig=test'})
        if request.url.host == 'carimagesapi.com':
            return httpx.Response(302, headers={'location': 'https://cdn.carimagesapi.com/motos/bajaj/pulsar_150/2020.webp'})
        return httpx.Response(200, content=blob.getvalue(), headers={'content-type': 'image/webp'})
    with httpx.Client(transport=httpx.MockTransport(provider)) as client:
        assert fetch_render(SPECS, 'test-secret', client, expected_slug='pulsar_150') == blob.getvalue()
    assert len(calls) == 3


def test_reject_foreign_redirects_svg_and_provider_errors():
    for mode in ('foreign', 'svg', 'quota', 'huge'):
        calls = []
        def provider(request):
            calls.append(request)
            if request.url.path.endswith('/signed-url'):
                if mode == 'quota':
                    return httpx.Response(429)
                return httpx.Response(200, json={'url': 'https://carimagesapi.com/image'})
            if mode == 'foreign':
                return httpx.Response(302, headers={'location': 'https://evil.example/image'})
            if mode == 'huge':
                return httpx.Response(200, content=b'x'*2_000_001, headers={'content-type': 'image/webp'})
            return httpx.Response(200, content=b'<svg/>', headers={'content-type': 'image/svg+xml'})
        with httpx.Client(transport=httpx.MockTransport(provider)) as client:
            assert fetch_render(SPECS, 'test-secret', client, expected_slug='pulsar_150') is None
        assert all(r.url.host == 'carimagesapi.com' for r in calls)


def test_reject_wrong_model_and_vehicle_library():
    specs = dict(SPECS, brand='Aprilia', model='SR 150', vehicle_type='Scooter')
    assert not matches_requested_model('https://cdn.carimagesapi.com/motos/aprilia/etx_150/2020.webp', specs)
    assert matches_requested_model('https://cdn.carimagesapi.com/motos/aprilia/sr_150/2020.webp', specs)
    assert not matches_requested_model('https://cdn.carimagesapi.com/motos/aprilia/sr_125/2020.webp', specs)
    assert not matches_requested_model('https://cdn.carimagesapi.com/vehicles/aprilia/sr_150/2020.webp', specs)
