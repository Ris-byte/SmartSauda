"""Download one registered public CSV archive for inspection, never auto-merge it."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 100 * 1024 * 1024


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "SmartSauda-Phase1-Research/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("Source exceeds the 100 MiB inspection limit")
    return payload


def acquire(source_id, root=ROOT):
    config = json.loads((root / "data/sources.json").read_text(encoding="utf-8"))
    source = next(s for s in config["public_sources"] if s["id"] == source_id)
    if source["status"] not in {"inspect_before_admission", "catalog_only_not_resale_training",
                                "research_candidates_with_missing_provenance_fields"}:
        raise ValueError("Source is not part of the selected acquisition scope")
    if source["provider"] != "kaggle":
        raise ValueError("Only registered Kaggle archives are supported")
    destination = root / "data/external" / source_id
    archive_path = destination / "source.zip"
    metadata_url = "https://www.kaggle.com/api/v1/datasets/view/" + source["ref"]
    download_url = ("https://www.kaggle.com/api/v1/datasets/download/" + source["ref"]
                    + "?datasetVersionNumber=" + str(source["version"]))
    if archive_path.exists():
        payload = archive_path.read_bytes()
        evidence = json.loads((destination / "acquisition.json").read_text(encoding="utf-8"))
        if hashlib.sha256(payload).hexdigest() != evidence["archive_sha256"]:
            raise ValueError("Downloaded archive differs from its recorded checksum")
    else:
        metadata_bytes = fetch(metadata_url)
        metadata = json.loads(metadata_bytes)
        if metadata.get("licenseName") != source["publisher_license"]:
            raise ValueError("Publisher license changed; review source registration before downloading")
        if metadata.get("currentVersionNumber") != source["version"]:
            raise ValueError("Publisher version changed; review metadata before downloading")
        payload = fetch(download_url)
        if not zipfile.is_zipfile(io.BytesIO(payload)):
            raise ValueError("Expected a ZIP archive; provider may require authentication")
        destination.mkdir(parents=True, exist_ok=True)
        archive_path.write_bytes(payload)
        (destination / "publisher_metadata.json").write_bytes(metadata_bytes)
        evidence = {
            "source": source, "metadata_url": metadata_url, "download_url": download_url,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "archive_sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload),
        }
        (destination / "acquisition.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    inventory = []
    names = set()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        if sum(item.file_size for item in archive.infolist()) > MAX_BYTES:
            raise ValueError("Uncompressed source exceeds the 100 MiB inspection limit")
        for item in archive.infolist():
            if item.is_dir() or not item.filename.lower().endswith(".csv"):
                continue
            # Never extract archive paths. Only a basename under this source directory is written.
            name = Path(item.filename.replace("\\", "/")).name
            if name in names or ":" in name:
                raise ValueError("Ambiguous or invalid CSV filename in archive")
            names.add(name)
            body = archive.read(item)
            encoding = source.get("encoding", "utf-8-sig")
            content = body.decode(encoding)
            reader = csv.DictReader(io.StringIO(content))
            rows = list(reader)
            (destination / name).write_bytes(body)
            inventory.append({
                "filename": name, "sha256": hashlib.sha256(body).hexdigest(),
                "rows": len(rows), "columns": reader.fieldnames, "encoding": encoding,
                "exact_unique_rows": len({tuple(r.values()) for r in rows}),
            })
    (destination / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    return inventory


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_id")
    args = parser.parse_args()
    print(json.dumps(acquire(args.source_id), indent=2))
