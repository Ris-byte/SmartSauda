from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'


def compact(text):
    return re.sub(r'[\s.\u2022]+', '', text)


def main():
    reference = PdfReader(DOCS / 'SmartSauda_Final_Report.pdf')
    rendered = PdfReader(DOCS / 'report-assets/word-render.pdf')
    layout = json.loads((DOCS / 'report-assets/layout-check.json').read_text())
    assert len(reference.pages) == len(rendered.pages) == layout['pages']
    for index, (expected, actual) in enumerate(zip(reference.pages, rendered.pages)):
        expected_text = expected.extract_text().strip()
        actual_text = actual.extract_text().strip()
        if index:
            footer = expected_text.splitlines()[-1].strip()
            expected_text = expected_text[:expected_text.rfind(footer)].strip()
            assert actual_text.startswith(footer), (index + 1, 'Missing footer')
            actual_text = actual_text[len(footer):].strip()
        assert compact(expected_text) == compact(actual_text), (index + 1, 'Content mismatch')
    all_text = '\n'.join(page.extract_text() for page in rendered.pages)
    for old_name in ['Aayush', 'Sugham', 'Kamal', 'Dipendra', 'JobHub', 'Oxford', '23530039', '23530099', '23530057']:
        assert old_name not in all_text, old_name
    for name in ['Prabin Thanet', 'Rishab Magar', 'Rajan Shah']:
        assert name in all_text
    for value in ['81,801.91', '41,948.30', '26,932.60', '0.9866', '0.7809', '0.6104']:
        assert value in all_text, value
    with ZipFile(DOCS / 'SmartSauda_Final_Report.docx') as archive:
        image_hashes = {hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist() if name.startswith('word/media/')}
        assert len(image_hashes) == 13
        for screenshot in ROOT.glob('Screenshot 2026-10-01 *.png'):
            assert hashlib.sha256(screenshot.read_bytes()).hexdigest() in image_hashes, screenshot.name
    observed_fonts = set()
    for page in rendered.pages:
        for reference_font in page['/Resources']['/Font'].values():
            observed_fonts.add(str(reference_font.get_object().get('/BaseFont')))
    assert not any('Calibri' in font or 'Arial' in font for font in observed_fonts), observed_fonts
    writer = PdfWriter(clone_from=rendered)
    writer.add_metadata({'/Title': 'SmartSauda: Vehicle Valuation and Resale Estimation System',
                         '/Author': 'Prabin Thanet; Rishab Magar; Rajan Shah', '/Subject': 'Project Report'})
    with (DOCS / 'SmartSauda_Final_Report.pdf').open('wb') as output:
        writer.write(output)
    print(f'Validated {len(rendered.pages)} pages, all report text, all seven original screenshots and all supplied member names.')
    print('PDF now uses the verified Word export. Fonts:', ', '.join(sorted(observed_fonts)))


if __name__ == '__main__':
    main()
