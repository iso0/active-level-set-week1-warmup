"""Resolve a historical thesis path, optionally selecting exact frozen bytes."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def resolve(old_path: str, sha256: str | None = None) -> list[Path]:
    old_path = old_path.replace('\\', '/').removeprefix('./')
    direct = (ROOT / old_path).resolve()
    if not direct.is_relative_to(ROOT):
        raise ValueError('Path must stay inside the repository')
    found = []
    if direct.is_file() and (sha256 is None or hashlib.sha256(direct.read_bytes()).hexdigest() == sha256):
        found.append(direct)
    with gzip.open(ROOT / 'outputs/project_consolidation/source_manifest.json.gz', 'rt', encoding='utf-8') as stream:
        manifest = json.load(stream)
    for item in manifest['files']:
        if old_path != item['canonical_path'] and not any(old_path == p for _, p in item['sources']):
            continue
        if sha256 is not None and item['sha256'] != sha256:
            continue
        dest = ROOT / item['destination']
        if dest not in found:
            found.append(dest)
    return found

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path')
    parser.add_argument('--sha256')
    args = parser.parse_args()
    paths = resolve(args.path, args.sha256)
    for path in paths:
        print(path)
    return 0 if paths else 1

if __name__ == '__main__':
    raise SystemExit(main())
