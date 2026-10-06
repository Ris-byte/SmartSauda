"""Capture bounded public car pages, honoring robots rules and preserving evidence."""
import argparse
import hashlib
import json
import re
import time
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urljoin

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/external/car-market-2026-10-05'
AGENT = 'SmartSauda-Research/1.0'
INDEXES = ['https://www.atalauto.com/used-car/brand/toyota',
           'https://www.hamroautomobiles.com.np/brand/2']
EXAMPLES = ['https://www.nepalbuysell.com/cars/cars_1/toyota-fortuner-2010_i3578',
            'https://www.admandu.com/toyota-fortuner-2010']
HOSTS = {urlparse(url).hostname for url in INDEXES + EXAMPLES}


def run(output=OUTPUT):
    global OUTPUT
    OUTPUT = output
    if (OUTPUT / 'manifest.json').exists():
        previous = json.loads((OUTPUT / 'manifest.json').read_text(encoding='utf-8'))
        if previous['records']:
            raise FileExistsError('Completed capture is immutable')
        (OUTPUT / ('failed-attempt-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S') + '.json')).write_text(
            json.dumps(previous, indent=2), encoding='utf-8')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    robots, records, failures = {}, [], []
    for host in sorted(HOSTS):
        parser = urllib.robotparser.RobotFileParser()
        try:
            request = urllib.request.Request('https://' + host + '/robots.txt', headers={'User-Agent': AGENT})
            with urllib.request.urlopen(request, timeout=25) as response:
                policy = response.read(100000).decode('utf-8')
            (OUTPUT / (host + '-robots.txt')).write_bytes(policy.encode('utf-8'))
            parser.parse(policy.splitlines())
            robots[host] = parser
        except Exception as error:
            failures.append({'url': 'https://' + host + '/robots.txt', 'error': str(error)})
    def capture(url, role):
        host = urlparse(url).hostname
        if host not in HOSTS or host not in robots or not robots[host].can_fetch(AGENT, url):
            raise ValueError('Public robots policy does not permit this capture')
        request = urllib.request.Request(url, headers={'User-Agent': AGENT})
        with urllib.request.urlopen(request, timeout=25) as response:
            if urlparse(response.url).hostname not in HOSTS:
                raise ValueError('Unexpected redirect')
            content = response.read(10000001)
        if len(content) > 10000000:
            raise ValueError('Page too large')
        path = OUTPUT / (hashlib.sha256(url.encode()).hexdigest()[:24] + '.html')
        path.write_bytes(content)
        records.append({'url': url, 'role': role, 'captured_at_utc': datetime.now(timezone.utc).isoformat(),
                        'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(content).hexdigest()})
        print(role, url, flush=True)
        time.sleep(.5)
        return content.decode('utf-8')
    urls = [(url, 'index') for url in INDEXES] + [(url, 'fortuner_reference') for url in EXAMPLES]
    seen = set()
    for url, role in urls:
        if url in seen or len(seen) >= 65:
            continue
        seen.add(url)
        try:
            document = capture(url, role)
            if role == 'index':
                links = [urljoin(url, link) for link in re.findall(r'href=[\"\x27]([^\"\x27]+)', document)]
                if 'atalauto' in url:
                    candidates = [link for link in links if '/used-cars/' in link and 'fortuner' in link.lower()]
                    target_role = 'fortuner_reference'
                else:
                    candidates = [link for link in links if re.search(r'/(?:cardetails|car|cars|vehicle|vehicles|product|products)/', link)]
                    target_role = 'external_evaluation'
                for candidate in dict.fromkeys(candidates):
                    if urlparse(candidate).hostname in HOSTS:
                        urls.append((candidate, target_role))
        except Exception as error:
            failures.append({'url': url, 'error': str(error)})
    manifest = {'records': records, 'failures': failures, 'training_approved': False,
                'notes': ['Captured dates are not original listing dates.', 'Sold listings do not establish transaction prices.']}
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'captured': len(records), 'failures': failures}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    run(args.output.resolve())
