"""Exact rational, finite two-step decision check; no GP or numerical libraries."""
import hashlib
import itertools
import json
import time
import traceback
from fractions import Fraction as F
from pathlib import Path

from coordination import HERE, Slot, now
import ledger


def encoded(value):
    return {'rational': str(value), 'decimal': float(value)}


def binary_risk(q, eta, observations):
    # Independent analytic likelihood calculation, not posterior atom filtering.
    from math import comb
    return sum((F(comb(observations, k)) * min(
        q * (1-eta)**k * eta**(observations-k),
        (1-q) * eta**k * (1-eta)**(observations-k))
        for k in range(observations+1)), F(0))


def solve_case(name, q, w, eta, g, expected_optimal, expected_first):
    weights = (w, g, g)
    assert sum(weights) <= 1
    atoms = []
    for h, a, b, e1, e2 in itertools.product((0, 1), repeat=5):
        mass = (q if h else 1-q) * F(1, 4)
        mass *= (eta if e1 else 1-eta) * (eta if e2 else 1-eta)
        atoms.append(((h, a, b), (h ^ e1, h ^ e2, a, b), mass))
    assert sum(s[2] for s in atoms) == 1
    nodes = 0

    def risk(states):
        total = sum(s[2] for s in states)
        return sum((weight * min(sum(s[2] for s in states if s[0][j]),
                                 sum(s[2] for s in states if not s[0][j]))
                    for j, weight in enumerate(weights)), F(0)) / total

    def branches(states, action):
        total = sum(s[2] for s in states)
        return [(sum(s[2] for s in child)/total, child) for answer in (0, 1)
                if (child := [s for s in states if s[1][action] == answer])]

    def recurse(states, available, horizon, greedy=False):
        nonlocal nodes
        nodes += 1
        if horizon == 0:
            return risk(states), ()
        losses = {}
        for action in available:
            rest = tuple(a for a in available if a != action)
            losses[action] = sum((p * (risk(child) if greedy else
                recurse(child, rest, horizon-1)[0])
                for p, child in branches(states, action)), F(0))
        best = min(losses.values())
        winners = tuple(a for a in available if losses[a] == best)
        if greedy:
            action = winners[0]
            rest = tuple(a for a in available if a != action)
            best = sum((p * recurse(child, rest, horizon-1, True)[0]
                        for p, child in branches(states, action)), F(0))
        return best, winners

    available = (0, 1, 2, 3)  # two local IDs, two global IDs; no repeat query
    before = risk(atoms)
    one_local = sum((p*risk(c) for p, c in branches(atoms, 0)), F(0))
    two_local = sum((p1*p2*risk(c2) for p1, c1 in branches(atoms, 0)
                    for p2, c2 in branches(c1, 1)), F(0))
    assert before == w*min(q, 1-q) + g
    assert one_local == w*binary_risk(q, eta, 1) + g
    assert two_local == w*binary_risk(q, eta, 2) + g
    assert binary_risk(q, eta, 1) == min(q, 1-q, eta)
    optimal, first = recurse(atoms, available, 2)
    greedy, greedy_first = recurse(atoms, available, 2, True)
    assert optimal == expected_optimal, (name, optimal, expected_optimal)
    assert all(('local' if a < 2 else 'global') == expected_first for a in first)
    assert optimal <= greedy
    assert nodes < 1000
    if name == 'rare_coherent_two_step':
        assert greedy == F(1, 200)
        assert before-one_local == 0
        assert greedy_first == (2, 3)
    return {'name': name, 'inputs': {k: encoded(v) for k, v in
            {'q': q, 'w': w, 'eta': eta, 'g': g}.items()},
            'prior_atoms': len(atoms), 'recursion_nodes': nodes,
            'initial_risk': encoded(before), 'one_local_risk': encoded(one_local),
            'two_local_risk': encoded(two_local), 'optimal_two_step_risk': encoded(optimal),
            'greedy_two_step_risk': encoded(greedy), 'optimal_first_actions': first,
            'greedy_first_actions': greedy_first}


def main():
    output = HERE/'results'/'LOCAL_VALUE_EXACT_REFERENCE.json'
    if output.exists():
        print('Existing exact reference retained; no duplicate execution.')
        return
    with Slot() as slot:
        manifest = json.loads((HERE/'FROZEN_FINISHING_AUDITS_V1_1.json').read_text())
        for file, digest in manifest['source_hashes'].items():
            assert hashlib.sha256((HERE/file).read_bytes()).hexdigest() == digest, file
        started = time.perf_counter()
        ledger.event('LOCAL_VALUE_EXACT_REFERENCE', None, 'NON_GP_REFERENCE_STARTED',
                     {'prior_atoms': 128, 'horizon': 2, 'GP_fits': 0})
        try:
            cases = []
            for args in (
                ('rare_coherent_two_step', F(1,100), F(1,2), F(1,20), F(3,1000), F(6627,2000000), 'local'),
                ('unreliable_local', F(1,100), F(1,2), F(3,10), F(3,1000), F(1,200), 'global'),
                ('small_mass', F(1,100), F(1,100), F(1,20), F(3,1000), F(1,10000), 'global'),
                ('uncertain_coherent', F(1,2), F(1,10), F(1,20), F(3,50), F(7,200), 'local'),
            ):
                slot.check()
                cases.append(solve_case(*args))
            result = {'status': 'PASS', 'utc': now().isoformat(), 'cases': cases,
                      'arithmetic': 'exact rational', 'GP_fits': 0, 'component_solves': 0,
                      'wall_seconds': time.perf_counter()-started,
                      'scope': 'Four analytic examples; not additional campaign-world evidence.'}
            ledger.atomic_json(output, result)
            ledger.event('LOCAL_VALUE_EXACT_REFERENCE', None, 'NON_GP_REFERENCE_COMPLETED',
                         {'cases': len(cases), 'GP_fits': 0})
            print(json.dumps({'status': result['status'], 'cases': len(cases)}))
        except Exception:
            ledger.atomic_json(HERE/'results'/'failures'/('LOCAL_VALUE_REFERENCE_'+str(time.time_ns())+'.json'),
                               {'utc': now().isoformat(), 'traceback': traceback.format_exc()})
            raise


if __name__ == '__main__':
    main()
