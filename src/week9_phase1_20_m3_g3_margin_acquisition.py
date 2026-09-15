"""Frozen Phase 1.20: standalone G3 acquisition, exact M3 evaluation."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import inspect
import json
import os
import platform
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed, parallel_config
from sklearn.preprocessing import StandardScaler
from src import week9_phase1_14_m3_margin_acquisition as p14

p12, p13, p11, p17, w85 = p14.p12, p14.p13, p14.p11, p14.p17, p14.w85
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/week9_phase1_20_m3_g3_margin_acquisition'
PARENT = '5a7a6c0'
FEATURES = p14.FEATURES
require = p14.require
write_json, write_csv = p14.write_json, p14.write_csv
PRACTICAL = .01


def atomic_checkpoint(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_bytes(gzip.compress(json.dumps(p14.json_safe(data), sort_keys=True).encode(), mtime=0))
    os.replace(temporary, path)


def load():
    population, specs, a0 = p14.load_inputs()
    table = pd.read_csv(p14.OUTPUT / 'm3_margin_paths.csv.gz')
    p1 = {run: g.sort_values('query_order').population_row_index.astype(int).tolist()
          for run, g in table.groupby('run_id')}
    return population, specs, a0, p1


def select_g3(pool_features, pool_indices, revealed_indices, revealed_labels, run_id, budget):
    """Label-blinded boundary: no population, oracle, test data or subset flags."""
    ids = np.asarray(pool_indices, int)
    revealed = np.asarray(revealed_indices, int)
    require(len(ids) == 324 and len(revealed) == budget, 'selector input shape')
    require(len(revealed_labels) == budget, 'selector labels must be revealed only')
    positions = {int(idx): pos for pos, idx in enumerate(ids)}
    scaler = StandardScaler().fit(pool_features)
    scaled = scaler.transform(pool_features)
    train_pos = [positions[int(idx)] for idx in revealed]
    model, diagnostic = p12.fit_gpc_model('G3', scaled[train_pos], np.asarray(revealed_labels),
                                         p12.seed_u32('G3', run_id, budget))
    candidate = np.setdiff1d(ids, revealed)
    probability = p12.predict_positive(model, scaled[[positions[int(idx)] for idx in candidate]])
    require(np.isfinite(probability).all(), 'nonfinite G3 candidate probability')
    chosen, _ = p14.choose_m3_margin(candidate, probability, scaled, train_pos)
    # Independently check the ordinary minimum margin, then population-index tie break.
    order = np.lexsort((candidate, np.abs(probability - .5)))
    require(chosen == int(candidate[order[0]]), 'G3 argmin parity failure')
    return chosen, candidate, probability, diagnostic


def m3_fit(population, spec, revealed, budget):
    x = population.loc[:, FEATURES].to_numpy(float)
    logh = p11.log_h_values(population)
    labels = population.has_keyhole.astype(int).to_numpy()
    physics = p11.fit_physics_mean(logh, labels, revealed,
                                  p13.seed_u32('shared_physics', spec.run_id, budget))
    return p13.fit_hybrid(x, logh, labels, revealed, spec.train_indices, physics, 'M3', 100.), x, logh


def reference_rows(path, run_id, model, budget):
    parts = []
    for frame in pd.read_csv(path, chunksize=200000):
        part = frame[frame.run_id.eq(run_id) & frame.model.eq(model) & frame.budget.eq(budget)]
        if len(part): parts.append(part)
    return pd.concat(parts).sort_values('population_row_index')


def preflight():
    OUT.mkdir(parents=True, exist_ok=True)
    population, specs, a0, p1 = load()
    sources = [Path(inspect.getfile(module)) for module in (p12, p13, p11, p14, w85, p14.p6)]
    audit = {
        'status': 'PASS', 'identical': False,
        'Week8.5': {'kernel': repr(p14.p6.make_signal_kernel()), 'lengthscales': 1,
                     'fit': 'p6.fit_gpc; w85.run_trajectory', 'seed': 'w85.fit_seed_key / seed_u32'},
        'G3': {'kernel': repr(p12.make_kernel('G3')), 'lengthscales': 4,
               'fit': 'p12.fit_gpc_model / predict_positive', 'seed': 'p12.seed_u32(G3, run_id, budget)'},
        'shared': {'amplitude_bounds': list(p12.AMPLITUDE_BOUNDS), 'length_bounds': list(p12.LENGTH_BOUNDS),
                   'optimizer': 'fmin_l_bfgs_b', 'restarts': 0, 'max_iter_predict': 100,
                   'warm_start': False, 'scaler': 'StandardScaler on outer training pool features',
                   'fallback': 'exact imported historical fitting functions; diagnostics retained'},
        'evidence': {str(path.relative_to(ROOT)): {'sha256': p14.sha256_file(path)} for path in sources},
        'source_excerpt_week85_kernel': inspect.getsource(p14.p6.make_signal_kernel),
        'source_excerpt_g3_kernel': inspect.getsource(p12.make_kernel),
        'source_excerpt_week85_fit': inspect.getsource(p14.p6.fit_gpc),
        'source_excerpt_g3_fit': inspect.getsource(p12.fit_gpc_model),
    }
    require(np.size(p14.p6.make_signal_kernel().k2.length_scale) == 1 and
            np.size(p12.make_kernel('G3').k2.length_scale) == 4, 'selectors identical or specification drift')
    write_json(OUT / 'selector_specification_audit.json', audit)
    protocol = {'status': 'FROZEN_BEFORE_P2', 'parent': PARENT, 'primary': 'B1_q20 balanced_accuracy AULC B16-B40 P2-P1',
                'secondary': ['P2-P0', 'q20 B16-B80', 'q30 B16-B40', 'q30 B16-B80'],
                'integration': 'normalized trapezoidal, divide by last minus first budget; larger is better',
                'historical_numbers_are': 'accuracy AULC, not balanced accuracy AULC',
                'bootstrap': 'exact p14.bootstrap_interval: 10000 percentile draws, p14 seed namespace and key convention',
                'unit': '20 repeat means, each retaining all five folds', 'sign_flip': 'not present in Phase 1.14',
                'practical_threshold': PRACTICAL,
                'decision': 'SUPPORTED if mean >= .01 and lower > 0; NOT_SUPPORTED if mean <= -.01 and upper < 0; otherwise SMALL_OR_UNRESOLVED',
                'P0': 'stored A0', 'P1': 'stored validated Phase 1.14 path', 'P2': 'live sequential standalone G3',
                'evaluator': 'exact Phase 1.13 M3 at all integer budgets 16 through 80',
                'selector_interface': list(inspect.signature(select_g3).parameters),
                'parity_probability_tolerance': 1e-8}
    path = OUT / 'frozen_protocol.json'
    if path.exists(): require(json.loads(path.read_text()) == protocol, 'frozen protocol changed')
    else: write_json(path, protocol)
    checks = {}
    checks['gate1_population'] = len(population) == 405 and int(population.has_keyhole.sum()) == 73
    checks['gate2_splits'] = len(specs) == 100 and len({s.repeat for s in specs}) == 20 and all(
        len([s for s in specs if s.repeat == r]) == 5 for r in {s.repeat for s in specs})
    checks['gate3_A0'] = len(a0) == 100  # imported loader checks all stored paths and initialization
    checks['gate4_P1'] = len(p1) == 100 and all(len(v) == len(set(v)) == 80 for v in p1.values())
    checks['gate5_initial'] = all(a0[s.run_id][:16] == p1[s.run_id][:16] == w85.initial_design(s, population) for s in specs)
    checks['split_sizes_and_group_protection'] = all(len(s.train_indices) == 324 and len(s.test_indices) == 81 and
        set(population.iloc[list(s.train_indices)].input_tuple_sha256).isdisjoint(
            population.iloc[list(s.test_indices)].input_tuple_sha256) for s in specs)
    for phase in (p12.OUTPUT, p13.OUTPUT, p14.OUTPUT):
        validation = json.loads((phase / 'validation_report.json').read_text())
        checks['stored_validation_' + phase.name] = validation.get('status') == 'PASS'
    require(all(checks.values()), f'baseline structural gate failed: {checks}')
    spec = specs[0]
    x = population.loc[:, FEATURES].to_numpy(float)
    y = population.has_keyhole.astype(int).to_numpy()
    scaler = StandardScaler().fit(x[list(spec.train_indices)])
    revealed = a0[spec.run_id][:16]
    g3, _ = p12.fit_gpc_model('G3', scaler.transform(x[revealed]), y[revealed], p12.seed_u32('G3', spec.run_id, 16))
    ref = reference_rows(p12.OUTPUT / 'new_kernel_predictions.csv.gz', spec.run_id, 'G3', 16)
    g3_error = float(np.max(np.abs(p12.predict_positive(g3, scaler.transform(x[ref.population_row_index])) - ref.probability)))
    checks['gate10_G3_prediction_parity'] = len(ref) == 81 and g3_error <= 1e-8
    fit, x, logh = m3_fit(population, spec, p1[spec.run_id][:24], 24)
    ref = reference_rows(p14.OUTPUT / 'new_predictions.csv.gz', spec.run_id, 'P1', 24)
    ids = ref.population_row_index.to_numpy(int)
    m3_error = float(np.max(np.abs(p13.components(fit, x[ids], logh[ids])['probability'] - ref.probability)))
    queries = pd.read_csv(p14.OUTPUT / 'm3_margin_queries.csv.gz')
    candidates = np.setdiff1d(spec.train_indices, p1[spec.run_id][:24])
    probs = p13.components(fit, x[candidates], logh[candidates])['probability']
    chosen, _ = p14.choose_m3_margin(candidates, probs, fit.x_scaler.transform(x), p1[spec.run_id][:24])
    checks['gate11_M3_prediction_and_path_parity'] = len(ref) == 81 and m3_error <= 1e-8 and chosen == p1[spec.run_id][24]
    result = {'status': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks,
              'G3_max_probability_error': g3_error, 'M3_max_probability_error': m3_error,
              'parity_run': spec.run_id, 'G3_budget': 16, 'M3_budget': 24}
    write_json(OUT / 'baseline_gate.json', result)
    require(all(checks.values()), f'PARITY GATE FAILED: {result}')
    return result


def fingerprint():
    paths = [Path(__file__), OUT / 'frozen_protocol.json'] + [Path(inspect.getfile(m)) for m in (p12, p13, p11, p14, w85)]
    return hashlib.sha256(''.join(p14.sha256_file(p) for p in paths).encode()).hexdigest()


def run_one(spec, population, a0, distances, stop=80, cache='checkpoints'):
    dest = OUT / cache / (spec.run_id + '.json.gz')
    token = fingerprint()
    if dest.exists():
        data = p14.read_checkpoint(dest)
        require(data['fingerprint'] == token, 'checkpoint provenance mismatch')
    else:
        data = {'fingerprint': token, 'run_id': spec.run_id, 'queried_indices': list(a0[:16]),
                'predictions': [], 'queries': [], 'diagnostics': [], 'complete': False}
    if data['complete']: return {'run_id': spec.run_id, 'reused': True}
    x = population.loc[:, FEATURES].to_numpy(float)
    y = population.has_keyhole.astype(int).to_numpy()
    train, test = np.asarray(spec.train_indices, int), np.asarray(spec.test_indices, int)
    flags = p17.subset_flags(spec, population, distances)
    evaluated = {r['budget'] for r in data['predictions']}
    for budget in range(len(data['queried_indices']), stop + 1):
        queried = data['queried_indices']
        require(len(queried) == len(set(queried)) == budget, 'duplicate or incorrect prefix')
        require(set(queried).issubset(train) and set(queried).isdisjoint(test), 'pool leakage')
        # Only training-pool features and currently revealed labels cross this boundary.
        if budget < 80:
            chosen, candidate, probability, diag = select_g3(x[train], train, queried, y[queried], spec.run_id, budget)
        if budget not in evaluated:
            fit, _, logh = m3_fit(population, spec, queried, budget)
            prob = p13.components(fit, x[test], logh[test])['probability']
            for j, idx in enumerate(test):
                data['predictions'].append({'run_id': spec.run_id, 'repeat': spec.repeat, 'fold': spec.fold,
                    'budget': budget, 'model': 'P2', 'population_row_index': int(idx), 'truth': int(y[idx]),
                    'probability': float(prob[j]), 'is_q20': bool(flags['B1_q20'][j]), 'is_q30': bool(flags['B1_q30'][j])})
            data['diagnostics'].append({'budget': budget, 'M3': p13.fit_diagnostic(fit), 'G3': diag if budget < 80 else None})
        if budget < 80:
            data['queries'].append({'budget': budget, 'selected': chosen, 'candidate_indices': candidate.tolist(),
                'candidate_probabilities': probability.tolist(), 'selected_margin': float(abs(probability[np.flatnonzero(candidate == chosen)[0]] - .5))})
            queried.append(int(chosen))  # oracle label becomes available only at the next fit
        data['complete'] = budget == 80
        atomic_checkpoint(dest, data)
    return {'run_id': spec.run_id, 'reused': False, 'complete': data['complete']}


def run(workers=4, smoke=False):
    require(json.loads((OUT / 'baseline_gate.json').read_text())['status'] == 'PASS', 'parity gate not passed')
    pop, specs, a0, _ = load()
    distances = w85.b1_distance(pop)
    chosen = specs[:1] if smoke else specs
    start = time.time()
    with parallel_config(backend='loky', inner_max_num_threads=1):
        results = Parallel(n_jobs=workers, verbose=10)(delayed(run_one)(s, pop, a0[s.run_id], distances,
                      17 if smoke else 80, 'smoke' if smoke else 'checkpoints') for s in chosen)
    report = {'status': 'PASS', 'runs': len(results), 'elapsed_seconds': time.time()-start, 'workers': workers, 'smoke': smoke}
    write_json(OUT / ('smoke_report.json' if smoke else 'execution_report.json'), report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['preflight', 'smoke', 'run'])
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    print(preflight() if args.command == 'preflight' else run(args.workers, args.command == 'smoke'))
