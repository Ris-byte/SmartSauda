"""Collect a bounded, traceable sample of public asking-price listings for review."""
import argparse
import csv
import hashlib
import html
import json
import re
import time
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
HOST = 'www.atalauto.com'
AGENT = 'SmartSauda-Research/1.0'
INDEXES = ['https://www.atalauto.com/used-car/brand/hyundai', 'https://www.atalauto.com/used-cars']


def plain(value):
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', value)).split())


def number(value):
    match = re.fullmatch(r'([\d,]+(?:\.\d+)?)\s*(?:CC|KMs|kms)?', value.strip())
    return float(match[1].replace(',', '')) if match else None


def available_urls(document):
    found = []
    for part in re.split(r'<li\b[^>]*class="flag-tag[^\"]*"[^>]*>', document)[1:]:
        if plain(part.split('</li>', 1)[0]).casefold() != 'available':
            continue
        match = re.search(r'href="(https://www\.atalauto\.com/used-cars/[^\"?#]+)"', part)
        if match and match[1] not in found:
            found.append(match[1])
    return found


def parse_listing(document, url, captured_at):
    title_match = re.search(r'<title[^>]*>(.*?)</title>', document, re.S)
    title = plain(title_match[1]) if title_match else ''
    title_fields = re.fullmatch(r'Buy (.+) (\d{4}) in Nepal,\s*Rs\.([\d,.]+)', title, re.I)
    if not title_fields:
        raise ValueError('Unrecognised listing title or price')
    values = {plain(label).rstrip(':').strip().casefold(): plain(value)
              for label, value in re.findall(r'<span[^>]*class="listing-info-title"[^>]*>(.*?)</span>\s*<p[^>]*>(.*?)</p>', document, re.S)}
    model_raw, year, price_raw = title_fields.groups()
    brands = ['Maruti Suzuki', 'Volkswagen', 'Mahindra', 'Hyundai', 'Toyota', 'Nissan', 'Suzuki', 'Honda', 'Tata', 'Kia', 'BYD', 'Ford', 'Renault', 'Datsun', 'Skoda', 'MG', 'Jeep']
    brand = next((item for item in brands if model_raw.casefold().startswith(item.casefold() + ' ')), '')
    flags = []
    if not brand:
        flags.append('brand_needs_review')
    row = {'record_id': 'atalauto:' + hashlib.sha256(url.encode()).hexdigest()[:20],
           'source_url': url, 'source_id': 'atalauto_public_asking_prices', 'captured_at_utc': captured_at,
           'listing_date': '', 'market': 'Nepal', 'currency': 'NPR', 'price_basis': 'asking',
           'vehicle_type': 'Car', 'brand': brand, 'model_variant_raw': model_raw[len(brand):].strip(),
           'manufacture_year': int(year), 'km_driven': number(values.get('odometer', '')),
           'engine_capacity_cc': number(values.get('engine size', '')),
           'owner_count': number(values.get('owners', '')), 'fuel_type': values.get('fuel type', ''),
           'transmission': values.get('transmission', ''), 'listing_status': values.get('status', '').lower(),
           'price': float(price_raw.replace(',', '')), 'snapshot_sha256': hashlib.sha256(document.encode()).hexdigest(),
           'review_status': 'pending', 'training_eligible': False}
    if row['listing_status'] != 'available':
        flags.append('not_currently_available')
    if row['price'] <= 0:
        flags.append('nonpositive_price')
    if row['price'] < 300000 or row['price'] > 30000000:
        flags.append('price_requires_manual_review')
    if not 1980 <= row['manufacture_year'] <= int(captured_at[:4]):
        flags.append('year_requires_manual_review')
    if row['km_driven'] is None or row['km_driven'] <= 0:
        flags.append('odometer_requires_manual_review')
    listed_year = values.get('year')
    if listed_year and listed_year != year:
        flags.append('conflicting_year_fields')
    row['quality_flags'] = '|'.join(['listing_date_missing', 'asking_not_transaction_price', *flags])
    return row


def fetch(url, robots):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname != HOST or not robots.can_fetch(AGENT, url):
        raise ValueError('URL is outside the allowed public collection scope')
    request = urllib.request.Request(url, headers={'User-Agent': AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        if urlparse(response.url).hostname != HOST:
            raise ValueError('Unexpected redirect host')
        payload = response.read(10_000_001)
    if len(payload) > 10_000_000:
        raise ValueError('Page exceeds collection size limit')
    return payload.decode('utf-8')


def collect(limit=80):
    captured_at = datetime.now(timezone.utc).isoformat()
    destination = ROOT / 'data/external' / ('nepal_car_listings_' + captured_at[:10])
    if (destination / 'manifest.json').exists():
        raise FileExistsError('This collection is already complete; preserve its captured evidence')
    snapshots = destination / 'snapshots'
    snapshots.mkdir(parents=True, exist_ok=True)
    robots = urllib.robotparser.RobotFileParser('https://' + HOST + '/robots.txt')
    robots.read()
    urls = []
    for index, url in enumerate(INDEXES):
        document = fetch(url, robots)
        (snapshots / f'index-{index}.html').write_bytes(document.encode('utf-8'))
        discovered = available_urls(document)
        print(f'Index {index}: {len(discovered)} available listing URLs', flush=True)
        for candidate in discovered:
            if candidate not in urls:
                urls.append(candidate)
    rows, failures = [], []
    for index, url in enumerate(urls[:limit]):
        key = hashlib.sha256(url.encode()).hexdigest()[:20]
        target = snapshots / (key + '.html')
        try:
            document = fetch(url, robots)
            target.write_bytes(document.encode('utf-8'))
            row = parse_listing(document, url, datetime.now(timezone.utc).isoformat())
            row['snapshot_path'] = str(target.relative_to(ROOT)).replace('\\', '/')
            rows.append(row)
        except Exception as error:
            failures.append({'url': url, 'error': str(error)})
        if (index + 1) % 10 == 0:
            print(f'Inspected {index + 1}/{min(len(urls), limit)} listings', flush=True)
        time.sleep(.4)
    if not rows:
        raise ValueError('No listings parsed; inspect snapshots before retrying')
    output = destination / 'listings.csv'
    with output.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest = {'captured_at_utc': captured_at, 'indexes': INDEXES, 'rows': len(rows), 'failures': failures,
                'csv_sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'training_approved': False,
                'notes': ['Collection time is not the original listing date.', 'Prices are unverified seller asking prices.',
                          'Manual field review and duplicate review are required.', 'No sale prices or publication rights have been inferred.']}
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Saved {len(rows)} review candidates to {output}; failures: {len(failures)}', flush=True)


def verify_snapshots(csv_path, repair_newlines=False):
    repaired = 0
    with csv_path.open(newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            path = (ROOT / row['snapshot_path']).resolve()
            if not path.is_relative_to((ROOT / 'data/external').resolve()):
                raise ValueError('Snapshot outside public data directory')
            payload = path.read_bytes()
            if hashlib.sha256(payload).hexdigest() == row['snapshot_sha256']:
                continue
            original = payload.replace(b'\r\n', b'\n')
            if not repair_newlines or hashlib.sha256(original).hexdigest() != row['snapshot_sha256']:
                raise ValueError(f'Snapshot checksum mismatch: {path}')
            path.write_bytes(original)
            repaired += 1
    print(f'All snapshot hashes verified; {repaired} Windows newline conversions reversed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=80)
    parser.add_argument('--verify-snapshots', type=Path)
    parser.add_argument('--repair-newlines', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.limit <= 100:
        parser.error('limit must be between 1 and 100')
    if args.verify_snapshots:
        verify_snapshots(args.verify_snapshots, args.repair_newlines)
    else:
        collect(args.limit)
