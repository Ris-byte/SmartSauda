from copy import deepcopy
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image
from pypdf import PdfReader

from backend.db import now
from backend.images import fetch_report_image
from backend.reports import prediction_pdf
from backend.vehicle_photos import PHOTOS, resolve_photo, reviewed_photo, generic_photo


def test_model_and_category_labels_and_reviewed_metadata():
    for photo in PHOTOS:
        kind = photo["vehicle_type"]
        if not photo["models"]:
            continue
        specs = dict(vehicle_type=kind, brand=photo['brand'], model=photo['models'][0])
        exact = resolve_photo(specs)
        assert exact['match_kind'] == 'model' and reviewed_photo(exact)
        generic = resolve_photo(dict(specs, model='Unreviewed model'))
        assert generic['match_kind'] == 'category'
        assert generic['depicted_model'] == generic_photo(kind)['depicted_model']
        assert resolve_photo(dict(specs, brand='Wrong brand'))['match_kind'] == 'category'
        assert not reviewed_photo(dict(exact, url='https://upload.wikimedia.org/unreviewed.jpg'))
        assert not reviewed_photo(dict(exact, author='Wrong credit'))
        exact['author'] = 'Modified'
        assert photo['author'] != 'Modified'


def test_unreviewed_url_does_not_gain_download_permission():
    metadata = resolve_photo(dict(vehicle_type='Car', brand='Other', model='Other'))
    metadata['url'] = 'https://upload.wikimedia.org/unreviewed.jpg'
    with patch('backend.images.socket.getaddrinfo', side_effect=AssertionError('Must not connect')):
        assert fetch_report_image(metadata, []) is None


def test_pdf_credits_generic_label_and_network_failure():
    metadata = resolve_photo(dict(vehicle_type='Scooter', brand='Other', model='Other'))
    row = SimpleNamespace(id='test-report', created_at=now(), model_version='test', price=123456,
                          image=metadata, vehicle_type='Scooter', specifications={'model': 'Other'},
                          result={'warnings': [{'message': 'Unverified provenance'}]})
    original = deepcopy(row.image)
    blob = BytesIO()
    Image.new('RGB', (100, 60), 'blue').save(blob, format='JPEG')
    for payload in [blob.getvalue(), None]:
        with patch('backend.reports.fetch_report_image', return_value=payload):
            pdf = prediction_pdf(row, SimpleNamespace(image_download_hosts=[]))
        text = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
        assert '123,456' in text and 'Unverified provenance' in text
        if payload:
            assert 'Generic scooter photo' in text and 'Selected model is not pictured' in text
            assert metadata['author'] in text and metadata['license_url'] in text
        else:
            assert 'Photo temporarily unavailable' in text
    assert row.image == original
