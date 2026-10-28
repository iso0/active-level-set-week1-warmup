"""Read-only full-path and frozen-source audit; no model fits."""
import gzip
import hashlib
import json
import time
from collections import defaultdict
from coordination import HERE, Slot, now
import ledger


def main():
    with Slot() as slot:
        errors = []
        hashes_checked = 0
        started = time.perf_counter()
        for name in ('FROZEN_MANIFEST_V2.json', 'FROZEN_QUOTA_CONTROL_V1.json',
                     'FROZEN_ACQUISITION_AUDIT.json', 'FROZEN_FINISHING_AUDITS_V1_1.json'):
            manifest = json.loads((HERE/name).read_text())
            for file, expected in manifest['source_hashes'].items():
                hashes_checked += 1
                actual = hashlib.sha256((HERE/file).read_bytes()).hexdigest()
                if actual != expected:
                    errors.append({'kind': 'source_hash', 'manifest': name, 'file': file})
        phase_reports = {}
        for phase, prefix, target_count, budget in (
            ('DEV', 'v2__', 1278, 40), ('TEST', 'v2__', 10224, 64),
            ('EXTRADEV', 'quota__', 84, 40), ('EXTRATEST', 'quota__', 672, 64),
        ):
            with ledger.database() as c:
                units = [dict(r) for r in c.execute(
                    'SELECT id,status,spec FROM units WHERE phase=? AND id LIKE ?',
                    (phase, prefix+'%'))]
            if len(units) != target_count or any(u['status'] != 'COMPLETE' for u in units):
                errors.append({'kind': 'unit_completion', 'phase': phase, 'expected': target_count,
                               'actual': len(units), 'incomplete': [u['id'] for u in units if u['status'] != 'COMPLETE']})
            groups = defaultdict(list)
            for j, unit in enumerate(units):
                if j % 50 == 0:
                    slot.check()
                path = HERE/'results'/phase/(unit['id']+'.json.gz')
                if not path.exists():
                    errors.append({'kind': 'missing_result', 'unit': unit['id']})
                    continue
                with gzip.open(path, 'rt', encoding='utf-8') as handle:
                    row = json.load(handle)
                spec = row['unit']
                ids, events = row['paid_ids'], row['events']
                conditions = {
                    'matching_spec': spec == json.loads(unit['spec']),
                    'complete_paid_path': len(ids) == budget and len(set(ids)) == budget,
                    'startup': ids[:8] == [s['paid_id'] for s in row['startup']],
                    'events': len(events) == budget-8 and all(
                        e['paid_id'] == ids[8+i] and e['paid_before'] == 8+i
                        and len(e['prequery_hash']) == 64 and e['cost'] > 0
                        for i, e in enumerate(events)),
                    'terminal_metric': row['metrics'][-1]['budget'] == budget,
                }
                if phase.startswith('EXTRA'):
                    conditions['fixed_share'] = row['local_queries'] == (budget-8)//2 and all(
                        e['reason'].startswith('local') == (i % 2 == 1)
                        for i, e in enumerate(events))
                for key, ok in conditions.items():
                    if not ok:
                        errors.append({'kind': key, 'unit': unit['id']})
                groups[(spec['family'], spec['seed'])].append({
                    'unit': unit['id'], 'model': spec['model'], 'selector': spec['selector'],
                    'world': row['evaluator']['hash'], 'ids': ids})
            full_path_pairs = 0
            for key, members in groups.items():
                if len({(r['world'], tuple(r['ids'][:8])) for r in members}) != 1:
                    errors.append({'kind': 'matched_world_startup', 'world': key, 'phase': phase})
                if not phase.startswith('EXTRA'):
                    for arm in ('random', 'maximin'):
                        subset = [r for r in members if r['selector'] == arm]
                        if len(subset) != 3 or len({tuple(r['ids']) for r in subset}) != 1:
                            errors.append({'kind': 'full_feature_only_model_path',
                                           'world': key, 'phase': phase, 'arm': arm})
                        full_path_pairs += max(0, len(subset)-1)
            phase_reports[phase] = {'registered_units': len(units), 'worlds': len(groups),
                                    'full_feature_only_model_pairs': full_path_pairs}
        result = {'utc': now().isoformat(), 'status': 'PASS' if not errors else 'FAIL',
                  'errors': errors, 'phases': phase_reports, 'hashes_checked': hashes_checked,
                  'GP_fits': 0, 'component_solves': 0, 'wall_seconds': time.perf_counter()-started,
                  'scope': 'All saved paths and frozen hashes; numerical replay is a separate artifact.'}
        ledger.atomic_json(HERE/'results'/'COMPLETION_INTEGRITY.json', result)
        ledger.event('COMPLETION_INTEGRITY', None, 'ARTIFACT_INTEGRITY_CHECK',
                     {'errors': len(errors), 'GP_fits': 0})
        print(json.dumps({'status': result['status'], 'errors': len(errors)}))
        if errors:
            raise SystemExit(1)


if __name__ == '__main__':
    main()
