"""Validate the frozen consolidation inventory without rerunning experiments."""
from __future__ import annotations
import ast
import gzip
import hashlib
import json
import os
import platform
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/project_consolidation'

def native(path):
    return '\\\\?\\' + str(path.resolve()) if os.name == 'nt' else str(path)

def digest(path):
    h = hashlib.sha256()
    with open(native(path), 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    with gzip.open(OUT / 'source_manifest.json.gz', 'rt', encoding='utf-8') as stream:
        manifest = json.load(stream)
    errors = []
    for n, item in enumerate(manifest['files']):
        path = ROOT / item['destination']
        if not path.is_file() or digest(path) != item['sha256']:
            errors.append({'kind': 'preserved_hash', 'path': item['destination']})
        if n and n % 4000 == 0:
            print(f'Checked {n} preserved files', flush=True)
    records = sorted({(origin, path, item['blob']) for item in manifest['files'] for origin, path in item['sources']})
    expected = json.loads((OUT / 'input_coverage.json').read_text(encoding='utf-8'))
    actual_digest = hashlib.sha256(json.dumps(records, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    if actual_digest != expected['source_records_sha256']:
        errors.append({'kind': 'source_coverage'})
    py_count = nb_count = 0
    notebook_errors = []
    exclusions = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache', '.ruff_cache', '.ipynb_checkpoints'}
    for directory, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in exclusions]
        for name in files:
            path = Path(directory) / name
            rel = path.relative_to(ROOT)
            if path.suffix == '.py':
                py_count += 1
                if rel.parts[0] != 'src':
                    errors.append({'kind': 'python_location', 'path': str(rel)})
                try:
                    ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(rel))
                except SyntaxError as exc:
                    errors.append({'kind': 'python_syntax', 'path': str(rel), 'error': str(exc)})
            if path.suffix == '.ipynb':
                nb_count += 1
                if rel.parts[0] != 'notebooks':
                    errors.append({'kind': 'notebook_location', 'path': str(rel)})
                try:
                    nb = json.loads(path.read_text(encoding='utf-8-sig'))
                    assert nb['nbformat'] == 4 and isinstance(nb['cells'], list)
                    if '_history' not in rel.parts:
                        for i, cell in enumerate(nb['cells']):
                            for result in cell.get('outputs', []):
                                if result.get('output_type') == 'error':
                                    notebook_errors.append({'path': str(rel), 'cell': i, 'ename': result.get('ename')})
                except Exception as exc:
                    errors.append({'kind': 'notebook_parse', 'path': str(rel), 'error': str(exc)})
    catalog = json.loads((OUT / 'phase_catalog.json').read_text(encoding='utf-8'))
    for phase in catalog:
        for rel in [phase['output'], *phase['code'], *phase['notebooks'], *phase['reports']]:
            if not (ROOT / rel).exists():
                errors.append({'kind': 'phase_link', 'path': rel})
    docs = [ROOT / 'README.md', ROOT / 'docs/PROJECT_INDEX.md', ROOT / 'docs/CONSOLIDATION_GUIDE.md', ROOT / 'docs/CODE_INDEX.md', ROOT / 'docs/NOTEBOOKS_AND_PRESENTATIONS.md', *list((ROOT/'docs/phases').glob('*.md'))]
    for doc in docs:
        for url in re.findall(r'\]\(([^)]+)\)', doc.read_text(encoding='utf-8')):
            if '://' in url or url.startswith('#'):
                continue
            target = (doc.parent / unquote(url.split('#')[0])).resolve()
            if not target.exists():
                errors.append({'kind': 'navigation_link', 'document': str(doc.relative_to(ROOT)), 'target': url})
    from src.tools.resolve_thesis_path import resolve
    frozen = json.loads((ROOT/'outputs/week9_phase1_20_m3_g3_margin_acquisition/run_manifest.json').read_text(encoding='utf-8'))
    frozen_failures = []
    for item in frozen['files']:
        matches = resolve(item['path'], item['sha256'])
        if not matches or not any(digest(p) == item['sha256'] for p in matches):
            frozen_failures.append(item['path'])
    if frozen_failures:
        errors.append({'kind': 'phase120_frozen_manifest', 'paths': frozen_failures})
    recovery = json.loads((OUT/'frozen_newline_recovery.json').read_text(encoding='utf-8'))
    legacy_issues = [r for r in recovery if r['operation'].startswith('UNRESOLVED')]
    for row in recovery:
        wanted = row.get('sha256', row.get('actual_sha256'))
        if digest(ROOT/row['path']) != wanted:
            errors.append({'kind': 'phase2_recovery_drift', 'path': row['path']})
    report = {'status': 'PASS' if not errors else 'FAIL', 'python': platform.python_version(),
              'manifest_files_verified': len(manifest['files']), 'unique_input_blobs': len({i['blob'] for i in manifest['files']}),
              'source_records': len(records), 'source_coverage_digest_matches': actual_digest == expected['source_records_sha256'],
              'phase_families': len(catalog), 'python_files_parsed': py_count, 'notebooks_parsed': nb_count,
              'canonical_notebook_stored_errors': notebook_errors,
              'phase120_frozen_manifest_files': len(frozen['files']), 'phase120_missing_frozen_files': frozen_failures,
              'scientific_experiments_rerun': False, 'legacy_phase2_manifest_issues': legacy_issues,
              'status_scope': 'Consolidation integrity only; legacy Phase 2 manifest exceptions are not cleared by this PASS.', 'errors': errors}
    (OUT/'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return int(bool(errors))

if __name__ == '__main__':
    raise SystemExit(main())
