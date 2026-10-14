"""Prepare a fresh, self-contained Windows reproduction without overwriting data.

No calculations run with --prepare-only. Otherwise the same frozen numerical
gate and host queue precede comparisons. Historical identity files are copied
only to satisfy the original-package preservation audit; they are not inputs
to the learner or generators. Existing experiment caches are never copied.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError('Destination must be new; never overwrite or reuse a prior run')
    if destination == ROOT or ROOT/'evidence' in destination.parents or ROOT/'preserved_v2_identity' in destination.parents:
        raise ValueError('Destination cannot overlap a directory that is recursively copied')
    manifest = json.loads((ROOT/'MANIFEST.json').read_text(encoding='utf-8'))
    files = dict(manifest['source_sha256'])
    files.update(manifest.get('operational_sha256', {}))
    for name, expected in files.items():
        if sha(ROOT/name) != expected:
            raise RuntimeError(f'Frozen source identity mismatch: {name}')
    originals = ROOT/'preserved_v2_identity'
    for name, expected in manifest['v2_original_hashes'].items():
        if sha(originals/name) != expected:
            raise RuntimeError(f'Bundled historical identity mismatch: {name}')
    out = destination/'astra_balanced_decision_acquisition'
    old = destination/'astra_joint_model_v2'
    out.mkdir(parents=True); old.mkdir()
    extra = ('MANIFEST.json', 'summarize_results.py', 'DECISION_ACQUISITION_DESIGN.md',
             'OPUS_DECISION_ACQUISITION_REQUEST.md', 'README.md')
    for name in set(files).union(extra):
        shutil.copy2(ROOT/name, out/name)
    for name in manifest['v2_original_hashes']:
        shutil.copy2(originals/name, old/name)
    # Evidence is provenance, not a lookup table available to any selector.
    shutil.copytree(ROOT/'evidence', out/'evidence')
    event = {'utc':dt.datetime.now(dt.timezone.utc).isoformat(), 'event':'MANIFEST_IMPORT',
             'manifest_sha256':sha(out/'MANIFEST.json'), 'reproducer_sha256':sha(__file__),
             'historical_identity_only':True, 'new_fits_executed':0}
    (out/'ledger.jsonl').write_text(json.dumps(event)+'\n', encoding='utf-8')
    for name, expected in files.items():
        if sha(out/name) != expected:
            raise RuntimeError(f'Copy integrity failure: {name}')
    (destination/'REPRODUCTION_PREPARATION.json').write_text(json.dumps(event, indent=2)+'\n', encoding='utf-8')
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True, help='A new directory; existing paths are refused')
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    if not args.prepare_only and os.name != 'nt':
        raise RuntimeError('This host-aware runner requires Windows/PowerShell; the mathematical modules are portable')
    out = prepare(args.destination)
    print(f'Fresh frozen package prepared: {out}', flush=True)
    if args.prepare_only:
        print('No numerical reference, fit, or comparison launched.', flush=True)
        return
    for action in ('freeze', 'checks'):
        subprocess.run([sys.executable, '-u', 'run_controlled.py', action], cwd=out, check=True)
    checks = json.loads((out/'INDEPENDENT_CHECKS.json').read_text(encoding='utf-8'))
    if not checks['acceptance_pass']:
        raise RuntimeError('Preserved reference gate failure; comparisons not launched')
    subprocess.run([sys.executable, '-u', 'run_controlled.py', 'run'], cwd=out, check=True)
    subprocess.run([sys.executable, '-u', 'summarize_results.py'], cwd=out, check=True)
    print('Computation complete; inspect all stops and numerical/scientific limitations.', flush=True)


if __name__ == '__main__':
    main()
