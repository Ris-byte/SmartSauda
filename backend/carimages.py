"""Server-only CarImages integration. Never expose key-bearing signed URLs."""
from io import BytesIO
from urllib.parse import urlsplit
from time import monotonic
import re
import json
from time import monotonic
from urllib.parse import quote

import httpx
from PIL import Image

_CATALOG_CACHE = {}


def resolve_catalog_model(specs, key, secret, client):
    """Resolve exact catalog metadata; reject wrong engine size or vehicle class."""
    if not key or not secret:
        return None
    car = specs['vehicle_type'] == 'Car'
    collection = 'vehicles' if car else 'motos'
    make_path = '/api/v1/makes' if car else '/api/v1/motos/makes'
    cache_key = (collection, specs['brand'].casefold())
    hit = _CATALOG_CACHE.get(cache_key)
    if hit and hit[0] > monotonic():
        make, models = hit[1], hit[2]
    else:
        headers = {'X-Api-Secret': secret}
        status, _, body = bounded_get(client, 'https://carimagesapi.com'+make_path, 320_000,
                                      params={'api_key': key}, headers=headers)
        data = json.loads(body) if status == 200 else {}
        makes = data.get('data', []) if isinstance(data, dict) else []
        make = next((m for m in makes if _compact(m.get('name','')) == _compact(specs['brand']) or
                     (specs['brand'].casefold() == 'royal enfield' and m.get('slug') == 'enfield') or
                     (specs['brand'].casefold() == 'maruti suzuki' and _compact(m.get('name','')) == 'suzuki')), None)
        if not make:
            return None
        models_path = (f"/api/v1/makes/{quote(make['slug'],safe='')}/models" if car else
                       f"/api/v1/motos/makes/{quote(make['slug'],safe='')}/models")
        status, _, body = bounded_get(client, 'https://carimagesapi.com'+models_path, 1_000_000,
                                      params={'api_key':key,'limit':500}, headers=headers)
        data = json.loads(body) if status == 200 else {}
        models = data.get('data',[]) if isinstance(data,dict) else []
        _CATALOG_CACHE[cache_key]=(monotonic()+21600,make,models)
        if len(_CATALOG_CACHE)>32:
            _CATALOG_CACHE.pop(next(iter(_CATALOG_CACHE)))
    requested=_compact(specs['model'])
    candidates=[item for item in models if requested and requested == _compact(item.get('name',''))]
    if not candidates:
        return None
    engine=specs.get('engine_capacity_cc')
    if not car and engine:
        candidates=[item for item in candidates if item.get('displacement') and
                    abs(int(item['displacement'])-float(engine)) <= max(12,float(engine)*0.08)]
    wanted_category='Scooter' if specs['vehicle_type']=='Scooter' else None
    if wanted_category:
        candidates=[item for item in candidates if item.get('category')=='Scooter']
    if not candidates:
        return None
    return {'make':make['name'],'model':candidates[0]['name'],'slug':candidates[0]['slug'],
            'library':collection,'candidate':candidates[0]}


def _compact(value):
    return re.sub(r'[^a-z0-9]','',str(value).casefold())


def valid_provider_url(url):
    if not isinstance(url, str) or len(url) > 4096 or any(ord(c) < 33 for c in url):
        return False
    try:
        part = urlsplit(url)
        return (part.scheme == 'https' and part.hostname in {'carimagesapi.com', 'cdn.carimagesapi.com'}
                and part.port in (None, 443) and not part.username and not part.password)
    except ValueError:
        return False


def matches_requested_model(url, specs):
    """Reject fuzzy substitutions using the CDN's explicit make/model identifiers."""
    parts = urlsplit(url).path.strip('/').split('/')
    library = 'vehicles' if specs['vehicle_type'] == 'Car' else 'motos'
    if len(parts) != 4 or parts[0] != library:
        return False
    compact = _compact
    make = 'Suzuki' if specs['brand'] == 'Maruti Suzuki' else specs['brand']
    expected_make = 'enfield' if compact(make) == 'royalenfield' else compact(make)
    if compact(parts[1]) != expected_make:
        return False
    requested = re.sub(r'\b(?:ABS|FI|BS[456]|Dual)\b', '', specs['model'], flags=re.I).strip()
    wanted, actual = compact(requested), compact(parts[2])
    # Ignore spacing and allow a supplied base model to match its named variant.
    # Word boundaries are supplied by numeric/letter tokenization (150 != 1500).
    wanted_tokens = re.findall(r'[a-z]+|[0-9]+', requested.casefold())
    actual_tokens = re.findall(r'[a-z]+|[0-9]+', parts[2].casefold())
    return bool(wanted) and (wanted == actual or
        set(wanted_tokens).issubset(actual_tokens))


def bounded_get(client, url, limit, **kwargs):
    with client.stream('GET', url, **kwargs) as response:
        if response.status_code in (301, 302, 303, 307, 308):
            return response.status_code, response.headers, b''
        if response.status_code != 200:
            return response.status_code, response.headers, b''
        payload = bytearray()
        start = monotonic()
        for chunk in response.iter_bytes():
            payload.extend(chunk)
            if len(payload) > limit or monotonic() - start > 8:
                raise ValueError('Provider response too large')
        return response.status_code, response.headers, bytes(payload)


def fetch_render(specs, key, client, expected_slug=None):
    if not key or not expected_slug:
        return None
    try:
        import json
        make = 'Suzuki' if specs['brand'] == 'Maruti Suzuki' else specs['brand']
        status, _, body = bounded_get(client, 'https://carimagesapi.com/api/v1/signed-url', 32000, params={
            'api_key': key, 'type': 'car' if specs['vehicle_type'] == 'Car' else 'moto',
            'make': make, 'model': specs['model'], 'year': specs['manufacture_year'],
            'format': 'webp', 'width': 800,
        })
        if status != 200:
            return None
        data = json.loads(body)
        if not isinstance(data, dict):
            return None
        url = data.get('url')
        for _ in range(3):
            if not valid_provider_url(url):
                return None
            if urlsplit(url).hostname == 'cdn.carimagesapi.com':
                parts = urlsplit(url).path.strip('/').split('/')
                if (len(parts) != 4 or _compact(parts[2]) != _compact(expected_slug)
                        or not matches_requested_model(url, specs)):
                    return None
            elif urlsplit(url).hostname != 'carimagesapi.com':
                return None
            status, headers, body = bounded_get(client, url, 2_000_000)
            if status in (301, 302, 303, 307, 308):
                url = headers.get('location')
                continue
            if status != 200 or headers.get('content-type', '').split(';')[0] != 'image/webp':
                return None  # Includes the provider's SVG placeholders: never display these.
            with Image.open(BytesIO(body)) as photo:
                if photo.format != 'WEBP' or photo.width * photo.height > 8_000_000:
                    return None
                photo.verify()
            return body
    except (httpx.HTTPError, ValueError, TypeError, OSError, Image.DecompressionBombError):
        return None
    return None
