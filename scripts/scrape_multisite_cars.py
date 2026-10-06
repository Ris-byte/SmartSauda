"""Resumable public Nepal car inventory capture; never activates model training."""
import argparse
import hashlib
import json
import re
import time
import sys
import urllib.error
import urllib.request
import urllib.robotparser
from collections import Counter, defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from xml.etree import ElementTree

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/external/multisite-used-cars-2026-10-05'
AGENT = 'SmartSauda-Research/1.0'
HOSTS = ['www.usedcarnepal.com', 'www.ktmcarsales.com', 'www.hamroautomobiles.com.np', 'seecar.com']


def plain(value):
    return BeautifulSoup(value, 'html.parser').get_text(' ', strip=True) if value else ''


def canonical(url):
    parts = urlsplit(url)
    return urlunsplit(('https', parts.netloc.lower(), parts.path or '/', parts.query, ''))


class Capture:
    def __init__(self, host):
        self.host = host
        self.root = OUTPUT / host
        self.root.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.root / 'manifest.json'
        self.manifest = json.loads(self.manifest_path.read_text()) if self.manifest_path.exists() else {}
        self.errors = {}
        self.last = 0
        self.robot = urllib.robotparser.RobotFileParser()
        data = self.get('https://' + host + '/robots.txt', check=False)
        self.robot.parse(data.splitlines())

    def get(self, url, check=True, payload=None):
        url = canonical(url)
        if urlsplit(url).hostname != self.host:
            raise ValueError('Cross-host request rejected: ' + url)
        if check and not self.robot.can_fetch(AGENT, url):
            raise ValueError('robots.txt disallows ' + url)
        key = url if payload is None else url + '#' + json.dumps(payload, sort_keys=True)
        if key in self.manifest:
            item = self.manifest[key]
            data = (ROOT / item['snapshot_path']).read_bytes()
            if hashlib.sha256(data).hexdigest() != item['sha256']:
                raise ValueError('Snapshot checksum mismatch')
            return data.decode('utf-8', errors='replace')
        time.sleep(max(0, 0.65 - (time.monotonic() - self.last)))
        self.last = time.monotonic()
        try:
            headers = {'User-Agent': AGENT}
            if payload is not None:
                headers.update({'Accept': 'application/json', 'Content-Type': 'application/json', 'App-Authorizer': '647061697361'})
            request = urllib.request.Request(url, headers=headers, data=None if payload is None else json.dumps(payload).encode())
            with urllib.request.urlopen(request, timeout=35) as response:
                if urlsplit(response.url).hostname != self.host:
                    raise ValueError('Unexpected cross-host redirect')
                data = response.read(12_000_001)
                if len(data) > 12_000_000:
                    raise ValueError('Oversized response')
            path = self.root / (hashlib.sha256(key.encode()).hexdigest()[:24] + '.html')
            path.write_bytes(data)
            self.manifest[key] = {'url': url, 'method': 'GET' if payload is None else 'POST', 'request_body': payload, 'captured_at_utc': datetime.now(timezone.utc).isoformat(),
                                  'snapshot_path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(data).hexdigest()}
            self.manifest_path.write_text(json.dumps(self.manifest, indent=2), encoding='utf-8')
            return data.decode('utf-8', errors='replace')
        except Exception as error:
            self.errors[key] = str(error)
            raise


def inspect():
    targets = {
        HOSTS[0]: ['/cars/', '/sitemap.xml', '/car/2021-renault-kwid-426023504/'],
        HOSTS[1]: ['/wp-sitemap.xml', '/buy-cars-kathmandu-nepal/?paged=2', '/buy-cars-kathmandu-nepal/for-sale-mahindra-scorpio-s11-2021/'],
        HOSTS[2]: ['/car', '/sold-car', '/cardetails/204'],
        HOSTS[3]: ['/search-cars?is_used=true', '/sitemap.xml', '/dynamic/about-us'],
    }
    def site(host):
        capture = Capture(host)
        for path in targets[host]:
            try:
                doc = capture.get('https://' + host + path)
                soup = BeautifulSoup(doc, 'html.parser')
                print('\nURL', host + path, '\n', soup.get_text(' ', strip=True)[:18000], flush=True)
                print('LINKS', [tag.get('href') for tag in soup.select('a[href]')][-35:], flush=True)
            except Exception as error:
                print(host, path, str(error), flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(site, HOSTS))


def crawl_site(host):
    capture = Capture(host)
    base = 'https://' + host
    seeds = {
        HOSTS[0]: ['/', '/cars/', '/sitemap-listings.xml'],
        HOSTS[1]: ['/', '/buy-cars-kathmandu-nepal/', '/wp-sitemap-posts-ad_listing-1.xml'],
        HOSTS[2]: ['/car', '/sold-car'],
    }[host]
    queue = deque((base + path, 'index') for path in seeds)
    visited = set()
    details = defaultdict(set)
    while queue:
        url, role = queue.popleft()
        url = canonical(url)
        if url in visited:
            continue
        visited.add(url)
        try:
            document = capture.get(url)
            if urlsplit(url).path.endswith('.xml'):
                links = [tag.text for tag in ElementTree.fromstring(document).iter() if tag.tag.endswith('}loc')]
            else:
                soup = BeautifulSoup(document, 'html.parser')
                links = [urljoin(url, tag['href']) for tag in soup.select('a[href]')]
            for target in links:
                target = canonical(target)
                if urlsplit(target).hostname != host:
                    continue
                path = urlsplit(target).path
                is_detail = ((host == HOSTS[0] and path.startswith('/car/')) or
                             (host == HOSTS[1] and bool(re.fullmatch('/buy-cars-kathmandu-nepal/[^/]+/', path))) or
                             (host == HOSTS[2] and path.startswith('/cardetails/')))
                if is_detail:
                    if role == 'index':
                        details[target].add(url)
                    else:
                        details[target].add('related_listing:' + url)
                    queue.append((target, 'detail'))
                elif role == 'index' and (('page=' in target and path in ('/cars/', '/car', '/sold-car')) or
                                        (host == HOSTS[1] and re.fullmatch(r'/buy-cars-kathmandu-nepal/page/\d+/', path))):
                    queue.append((target, 'index'))
            if len(visited) % 25 == 0:
                print(host, 'pages', len(visited), 'listings', len(details), flush=True)
        except Exception as error:
            print('ERROR', url, str(error), flush=True)
    report = {'host': host, 'discovered_listings': {key: sorted(value) for key, value in details.items()},
              'visited_pages': len(visited), 'errors': capture.errors,
              'coverage': 'all_discovered_public_links_attempted; not a guarantee of unpublished inventory'}
    (capture.root / 'discovery.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('DONE', host, len(details), 'errors', len(capture.errors), flush=True)


def crawl_seecar():
    capture = Capture('admin.seecar.com')
    public = Capture('seecar.com')
    capture.get('https://admin.seecar.com/api/get/all-manufacturer', payload={})
    page = 1
    records = []
    while True:
        payload = {'is_used': 'true', 'page': page, 'perPage': 12}
        response = json.loads(capture.get('https://admin.seecar.com/api/filter/vehicle', payload=payload))
        if response.get('status') != 'success':
            raise ValueError('SeeCar search failed: ' + str(response))
        entries = response['data']
        for record in entries['data']:
            if record.get('is_used') is not True:
                raise ValueError('New vehicle returned for used filter')
            records.append(record['id'])
            public.get('https://seecar.com/car-detail/' + record['slug'])
            capture.get('https://admin.seecar.com/api/get/vehicle-by-id', payload={'slug': record['slug']})
        print('SeeCar page', page, 'of', entries['last_page'], 'total', entries['total'], flush=True)
        if page >= entries['last_page']:
            break
        page += 1
    (public.root / 'discovery.json').write_text(json.dumps({'host': 'seecar.com', 'listing_ids': records,
        'reported_total': entries['total'], 'pages': page, 'errors': capture.errors,
        'coverage': 'all pages of public used-car filter, including sale_status true and false'}, indent=2))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--crawl', action='store_true')
    parser.add_argument('--seecar', action='store_true')
    args = parser.parse_args()
    if args.seecar:
        crawl_seecar()
    elif args.crawl:
        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(crawl_site, HOSTS[:3]))
    else:
        inspect()
