"""Hash public photos only for suspected duplicate ads; do not infer identity from specs."""
import hashlib
import json
import sys
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.scrape_multisite_cars import AGENT, HOSTS, OUTPUT, ROOT, Capture


def run():
    dataset = json.loads((ROOT / 'data/processed/nepal_used_cars_multisite.json').read_text(encoding='utf-8'))
    by_host = defaultdict(set)
    for row in dataset['records']:
        if row['possible_duplicate_group']:
            for url in row['image_urls'][:3]:
                parts = urlsplit(url)
                if parts.hostname in HOSTS:
                    by_host[parts.hostname].add(url)
    output = OUTPUT / 'duplicate-image-hashes.json'
    existing = json.loads(output.read_text()) if output.exists() else {}

    def host_images(host):
        capture = Capture(host)
        records = {}
        for original_url in sorted(by_host[host]):
            if original_url in existing:
                records[original_url] = existing[original_url]
                continue
            parts = urlsplit(original_url)
            url = urlunsplit(('https', parts.netloc, quote(parts.path, safe='/%'), parts.query, ''))
            try:
                if not capture.robot.can_fetch(AGENT, url):
                    raise ValueError('robots.txt disallows image')
                time.sleep(0.65)
                with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': AGENT}), timeout=30) as response:
                    if urlsplit(response.url).hostname != host or not response.headers.get('Content-Type', '').startswith('image/'):
                        raise ValueError('Unexpected image response')
                    data = response.read(8_000_001)
                    if len(data) > 8_000_000:
                        raise ValueError('Oversized image')
                records[original_url] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'resolved_url': url}
            except Exception as error:
                records[original_url] = {'error': str(error)}
        print(host, 'photo hashes', len(records), flush=True)
        return records

    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(host_images, by_host):
            existing.update(result)
    output.write_text(json.dumps(existing, indent=2), encoding='utf-8')
    print('Saved', len(existing), 'photo hash results')


if __name__ == '__main__':
    run()
