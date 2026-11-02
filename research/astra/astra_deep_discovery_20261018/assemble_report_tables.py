"""Bounded descriptive report assembly from finished artifacts; no model fitting."""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import csv
import gzip
import hashlib
import json
import statistics
import time
import traceback
from collections import defaultdict
from pathlib import Path
from coordination import HERE, Slot, now
import ledger


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def average(values):
    clean = [v for v in values if v is not None]
    return statistics.mean(clean) if clean else None


def write_csv(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    temp = path.with_suffix('.tmp')
    with temp.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temp, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--threads', type=int, choices=[1], required=True)
    parser.parse_args()
    manifest_path = HERE / 'REPORT_ASSEMBLY_MANIFEST.json'
    manifest = read_json(manifest_path)
    for name, expected in manifest['source_hashes'].items():
        if sha(HERE / name) != expected:
            raise RuntimeError('report source changed: ' + name)
    dst = HERE / 'results' / 'final_tables'
    marker = dst / 'COMPLETE.json'
    if marker.exists():
        old = read_json(marker)
        if old['manifest_sha256'] != sha(manifest_path):
            raise RuntimeError('completed report belongs to another source manifest')
        for name, expected in old['output_hashes'].items():
            if sha(dst / name) != expected:
                raise RuntimeError('completed report artifact changed: ' + name)
        print('Report already complete; no repeated analysis')
        return
    if (dst / 'FAILURE.json').exists():
        raise RuntimeError('saved report failure requires an explicit technical review')
    state = read_json(HERE / 'runtime' / 'completion_audits.json')
    if state['stage'] != 'READY_FOR_SCIENTIFIC_REVIEW':
        raise RuntimeError('existing finishing audits are not ready; do not duplicate them')
    dst.mkdir(parents=True, exist_ok=True)
    attempt = 'REPORT__' + now().strftime('%Y%m%dT%H%M%S%fZ')
    start = time.monotonic()
    with Slot() as slot:
        ledger.event(None, attempt, 'DESCRIPTIVE_REPORT_START', {'fits': 0, 'components': 0,
                     'manifest_sha256': sha(manifest_path), 'maximum_seconds': 600})
        try:
            grouped = defaultdict(list)
            index = {}
            inputs = {}
            counts = {}
            for phase, prefix, expected_count in (('TEST', 'v2__', 10224), ('EXTRATEST', 'quota__', 672)):
                paths = sorted((HERE / 'results' / phase).glob(prefix + '*.json.gz'))
                if len(paths) != expected_count:
                    raise RuntimeError('incomplete phase: ' + phase)
                counts[phase] = len(paths)
                for k, path in enumerate(paths):
                    if k % 64 == 0:
                        slot.check()
                        if time.monotonic() - start > 600:
                            raise TimeoutError('report-assembly elapsed limit')
                    raw = path.read_bytes()
                    inputs[str(path.relative_to(HERE))] = hashlib.sha256(raw).hexdigest()
                    row = json.loads(gzip.decompress(raw))
                    s, last = row['unit'], row['metrics'][-1]
                    hit = last['first_island_query']
                    item = {**last, **{n: row[n] for n in ('target_event', 'target_confirmed_budget',
                            'restricted_query_burden', 'triggers', 'local_queries', 'near_ties',
                            'wall_seconds', 'cpu_seconds', 'fit_seconds', 'selection_seconds',
                            'evaluation_seconds', 'peak_process_working_set_bytes')},
                            'paid_ids': row['paid_ids'], 'seed': s['seed'], 'horizon': s['budget'],
                            'corroborations': sum(bool(e.get('confirmed_now')) for e in row['events']),
                            'has_hit': hit is not None, 'hit_by_startup': hit is not None and hit <= len(row['startup']),
                            'has_three_hits': last['third_island_query'] is not None,
                            'pool_island_n': row['evaluator']['pool_island_n'],
                            'eval_island_n': row['evaluator']['eval_island_n']}
                    grouped[(phase, s['family'], s['model'], s['selector'])].append(item)
                    index[(phase, s['family'], s['seed'], s['model'], s['selector'])] = item
            science, cost = [], []
            metrics = ('error', 'boundary_error', 'island_recall', 'recall_positive', 'recall_negative',
                       'BA', 'brier', 'log_loss', 'RMSE', 'reported_channel_RMSE', 'coverage90',
                       'aux_RMSE', 'aux_coverage90', 'mixture_effective_components', 'positive_paid_count',
                       'paid_island_count', 'triggers', 'corroborations', 'local_queries', 'near_ties')
            for (phase, family, model, selector), rows in sorted(grouped.items()):
                base = dict(phase=phase, family=family, model=model, selector=selector, n=len(rows), horizon=64)
                if len(rows) != 24 or any(r['horizon'] != 64 for r in rows):
                    raise RuntimeError('unexpected replication or horizon')
                a = dict(base)
                for metric in metrics:
                    values = [r.get(metric) for r in rows]
                    a[metric + '_mean'] = average(values)
                    a[metric + '_defined_n'] = sum(v is not None for v in values)
                a.update(gate_active_worlds=sum(r['triggers'] > 0 for r in rows),
                         first_hit_worlds=sum(r['has_hit'] for r in rows),
                         first_hit_by_startup_worlds=sum(r['hit_by_startup'] for r in rows),
                         third_hit_worlds=sum(r['has_three_hits'] for r in rows),
                         no_pool_island_worlds=sum(r['pool_island_n'] == 0 for r in rows),
                         no_eval_island_worlds=sum(r['eval_island_n'] == 0 for r in rows))
                for label, hit_state in (('hit', True), ('no_hit', False)):
                    values = [r['island_recall'] for r in rows if r['has_hit'] == hit_state and r['island_recall'] is not None]
                    a['island_recall_given_' + label] = average(values)
                    a['island_recall_given_' + label + '_n'] = len(values)
                science.append(a)
                event_times = [r['target_confirmed_budget'] for r in rows if r['target_event']]
                c = dict(base, confirmed_n=len(event_times), censored_n=len(rows)-len(event_times),
                         confirmation_queries_among_successes_mean=average(event_times),
                         horizon_restricted_query_burden_mean=average([r['restricted_query_burden'] for r in rows]))
                for metric in ('wall_seconds', 'cpu_seconds', 'fit_seconds', 'selection_seconds', 'evaluation_seconds'):
                    c['full_horizon_' + metric + '_mean'] = average([r[metric] for r in rows])
                    c['full_horizon_' + metric + '_median'] = statistics.median(r[metric] for r in rows)
                c['worker_lifetime_peak_RSS_max_bytes'] = max(r['peak_process_working_set_bytes'] for r in rows)
                c['compute_time_to_target_available'] = False
                cost.append(c)
            analysis_path = HERE / 'results/analysis/v2__TEST/CONTROLLED_RESULTS.json'
            analysis = read_json(analysis_path)
            if not analysis['complete'] or analysis['path_audit_errors']:
                raise RuntimeError('main analysis incomplete or path errors present')
            inputs[str(analysis_path.relative_to(HERE))] = sha(analysis_path)
            pair_defs = {r['contrast']: ('TEST', r['A'], r['B']) for r in analysis['contrasts']}
            pair_defs['equal_share_anchor_choice'] = ('EXTRATEST', ['structure', 'quota_surprise'], ['structure', 'quota_no_surprise'])
            pairs = []
            for name, (phase, arm_a, arm_b) in pair_defs.items():
                for (p, family, seed, model, selector), a in sorted(index.items()):
                    if p != phase or [model, selector] != arm_a:
                        continue
                    b = index.get((phase, family, seed, *arm_b))
                    if b is None:
                        continue
                    pairs.append(dict(contrast=name, phase=phase, family=family, seed=seed,
                        identical_full_paid_path=a['paid_ids'] == b['paid_ids'],
                        A_triggers=a['triggers'], B_triggers=b['triggers'],
                        A_local_queries=a['local_queries'], B_local_queries=b['local_queries'],
                        A_first_island_query=a['first_island_query'], B_first_island_query=b['first_island_query'],
                        A_error=a['error'], B_error=b['error'], A_minus_B_error=a['error']-b['error'],
                        A_island_recall=a['island_recall'], B_island_recall=b['island_recall']))
            write_csv(dst/'all_family_metrics_and_mechanisms.csv', science)
            write_csv(dst/'same_target_queries_and_full_horizon_cost.csv', cost)
            write_csv(dst/'per_world_matched_paths_and_gates.csv', pairs)
            burden = [{**r, 'A': '/'.join(r['A']), 'B': '/'.join(r['B']),
                       'ci95_low': r['ci95'][0], 'ci95_high': r['ci95'][1]}
                      for r in analysis['contrasts'] if r['metric'] == 'restricted_query_burden']
            write_csv(dst/'existing_paired_query_burden_contrasts.csv', burden)
            readme = ('# Descriptive final tables\n\nAll registered TEST groups are retained. No new fits or tests.\n'
                'Conditional metrics include defined denominators; hit-conditioned means are post-treatment descriptions.\n'
                'Costs are saved B64 trajectory accumulators, excluding setup and separate audits; they are not total campaign billing.\n'
                'Time to target is not recorded. Peak RSS is worker-lifetime, not isolated path memory.\n'
                'Confirmation means among successes exclude censored times explicitly; restricted burden and event counts retain them.\n'
                'The paired intervals/flags are copied from the frozen analysis, with its symmetry and multiplicity limitations.\n'
                'No synthetic result is SPH confirmation; no physical-simulator hours were measured.\n')
            (dst/'README.md').write_text(readme, encoding='utf-8')
            audit_names = ('results/ACTUAL_PREFIX_ACQUISITION_AUDIT.json', 'results/LOCAL_VALUE_EXACT_REFERENCE.json',
                           'results/COMPLETION_INTEGRITY.json', 'results/analysis/v2__TEST/PATH_REPLAY.json')
            audits = {name: read_json(HERE/name) for name in audit_names}
            for name in audit_names:
                inputs[name] = sha(HERE/name)
            result = dict(status='COMPLETE', utc=now().isoformat(), attempt=attempt,
                manifest_sha256=sha(manifest_path), counts=counts, family_groups=len(science), paired_world_rows=len(pairs),
                fits=0, components=0, new_inferential_tests=0, elapsed_seconds=time.monotonic()-start,
                input_hashes=inputs, output_hashes={p.name: sha(p) for p in sorted(dst.glob('*.csv'))},
                audit_statuses={n: {'status': v.get('status'),
                                   'all_references_accepted': v.get('all_references_accepted')}
                                for n, v in audits.items()})
            result['output_hashes']['README.md'] = sha(dst/'README.md')
            slot.check()
            if time.monotonic()-start > 600:
                raise TimeoutError('report-assembly elapsed limit')
            ledger.atomic_json(marker, result)
            ledger.event(None, attempt, 'DESCRIPTIVE_REPORT_COMPLETE', {'fits': 0, 'components': 0,
                         'family_groups': len(science), 'elapsed_seconds': result['elapsed_seconds']})
            print('Final descriptive tables complete; no fits or new tests')
        except Exception:
            detail = traceback.format_exc()
            ledger.atomic_json(dst/'FAILURE.json', {'attempt': attempt, 'utc': now().isoformat(), 'traceback': detail})
            ledger.event(None, attempt, 'DESCRIPTIVE_REPORT_FAILED', {'traceback': detail, 'fits': 0, 'components': 0})
            raise


if __name__ == '__main__':
    main()
