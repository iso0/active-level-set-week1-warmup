"""Week 16 item 0 — exact verification of the Astra round-1 statements (outputs/astra_round1/ASTRA_ROUND1.md)
and of the generalized binary-observation lemma used by PEER."""
import itertools
import math
import random
from fractions import Fraction

import numpy as np
import pytest

from src.week16_astra import (E_T, bayes_error_pair, decoy_cluster_law, delta_brute, delta_eq1, discovery_budget,
                              first_hit_survival, kappa, kappa_params, margin_choices, moments, p_T_greater,
                              root_leaf_law, tail_dominates, uniform_ratio)


def random_law(n, rng, sparse=False, symmetric=False):
    worlds = list(itertools.product((-1, 1), repeat=n))
    w = [rng.randint(0, 6) if not sparse else (rng.randint(1, 9) if rng.random() < .25 else 0) for _ in worlds]
    if sum(w) == 0:
        w[rng.randrange(len(w))] = 1
    if symmetric:  # mixture with the global flip: every marginal equals 1/2
        idx = {x: k for k, x in enumerate(worlds)}
        w = [w[k] + w[idx[tuple(-s for s in x)]] for k, x in enumerate(worlds)]
    tot = sum(w)
    keep = [(x, Fraction(v, tot)) for x, v in zip(worlds, w) if v]
    return [x for x, _ in keep], [p for _, p in keep]


# --------------------------------------------------------------------------- generalized lemma
def test_binary_observation_lemma_exact():
    rng = random.Random(0)
    for _ in range(3000):
        w = [rng.randint(0, 9) for _ in range(4)]
        if sum(w) == 0:
            continue
        cells = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        table = {c: Fraction(v, sum(w)) for c, v in zip(cells, w)}
        err, ET, ETO = bayes_error_pair(table)
        assert err == (1 - max(abs(ET), abs(ETO))) / 2


# --------------------------------------------------------------------------- eq. (1)
@pytest.mark.parametrize("n", [2, 3, 4, 5])
def test_eq1_matches_definition(n):
    rng = random.Random(n)
    for t in range(60 if n < 5 else 15):
        worlds, probs = random_law(n, rng, sparse=t % 2 == 1)
        assert delta_eq1(*moments(worlds, probs)) == delta_brute(worlds, probs)


def test_eq1_degenerate_point_mass():
    worlds, probs = [(1, -1, 1)], [Fraction(1)]
    assert delta_eq1(*moments(worlds, probs)) == [0, 0, 0] == delta_brute(worlds, probs)


def test_pairwise_independence_makes_margin_optimal():
    rng = random.Random(3)
    for _ in range(30):
        q = [Fraction(rng.randint(1, 9), 10) for _ in range(4)]
        worlds = list(itertools.product((-1, 1), repeat=4))
        probs = [math.prod(qi if s == 1 else 1 - qi for qi, s in zip(q, w)) for w in worlds]
        d = delta_eq1(*moments(worlds, probs))
        assert d == [min(qi, 1 - qi) / 4 for qi in q]


# --------------------------------------------------------------------------- eq. (2) and sharpness
@pytest.mark.parametrize("n", [2, 3, 4, 5, 6])
def test_margin_bound(n):
    rng = random.Random(10 + n)
    for t in range(80 if n < 6 else 20):
        worlds, probs = random_law(n, rng, sparse=t % 3 != 0)
        d = delta_eq1(*moments(worlds, probs))
        for a in margin_choices(worlds, probs):
            assert d[a] * (n - 1) >= max(d)
            if n == 2:
                assert d[a] == max(d)


@pytest.mark.parametrize("M", [2, 3, 5, 9])
def test_margin_bound_sharpness(M):
    N = M + 1
    for eta in (Fraction(1, 10), Fraction(1, 100), Fraction(1, 1000)):
        worlds, probs = decoy_cluster_law(M, eta)
        d = delta_eq1(*moments(worlds, probs))
        assert margin_choices(worlds, probs) == [0]
        assert d[0] == Fraction(1, 2 * N)
        assert all(x == M * (Fraction(1, 2) - eta) / N for x in d[1:])
        assert d[0] / max(d) == 1 / (M * (1 - 2 * eta))
    assert abs(float(1 / (M * (1 - 2 * Fraction(1, 10 ** 9)))) - 1 / (N - 1)) < 1e-6


# --------------------------------------------------------------------------- Theorem 2 / kappa_N
def test_kappa_table():
    table = {2: Fraction(1), 3: Fraction(5, 6), 4: Fraction(7, 10), 5: Fraction(3, 5), 6: Fraction(5, 9),
             7: Fraction(1, 2), 10: Fraction(2, 5), 17: Fraction(5, 17)}
    for N, v in table.items():
        assert kappa(N) == v


@pytest.mark.parametrize("N", range(2, 13))
def test_kappa_construction_attains(N):
    worlds, probs = root_leaf_law(N)
    assert sum(probs) == 1
    m, c = moments(worlds, probs)
    assert all(x == 0 for x in m)                              # fair marginals
    assert all((1 in w) and (-1 in w) for w in worlds)          # every world has both labels
    M, a, b, tau = kappa_params(N)
    d = delta_eq1(m, c)
    assert d[0] == (1 + tau) / (2 * N)                          # root
    assert all(x == (1 + tau / M) / (2 * N) for x in d[1:])     # leaves
    assert uniform_ratio(worlds, probs) == kappa(N)
    # minimax: any selector putting mass p <= 1/N on the root attains at most kappa_N; deterministic leaf choice
    leaf_ratio = d[1] / max(d)
    assert leaf_ratio <= kappa(N)
    if N <= 8:
        assert d == delta_brute(worlds, probs)


def test_kappa_lower_bound_and_sqrt_form():
    for N in range(2, 200):
        M = N - 1
        lhs = kappa(N) * N - 1                                  # kappa_N >= (1 + sqrt M)/N  <=>  lhs^2 >= M
        assert lhs >= 0 and lhs * lhs >= M
        if math.isqrt(M) ** 2 == M:
            assert lhs * lhs == M


@pytest.mark.parametrize("n", [3, 4, 5, 6])
def test_uniform_guarantee_on_random_fair_laws(n):
    rng = random.Random(100 + n)
    for t in range(60 if n < 6 else 15):
        worlds, probs = random_law(n, rng, sparse=t % 2 == 0, symmetric=True)
        assert uniform_ratio(worlds, probs) >= kappa(n)


# --------------------------------------------------------------------------- Proposition 5.1
def test_prop51_better_predictor_worse_query():
    M, eta = 100, Fraction(1, 100)
    N = M + 1
    worlds, probs = decoy_cluster_law(M, eta)
    true_p = [Fraction(1, 2)] + [Fraction(1, 2) + eta] * M
    pA = list(true_p)
    pB = [Fraction(1, 2) + 2 * eta, Fraction(1, 2) - eta / 2] + [Fraction(1, 2) + 3 * eta / 2] * (M - 1)
    choose = lambda p: [j for j, x in enumerate(p) if abs(x - Fraction(1, 2)) == min(abs(y - Fraction(1, 2)) for y in p)]
    assert choose(pA) == [0] and choose(pB) == [1]
    brier = lambda p, q: (p - q) ** 2 + q * (1 - q)
    assert all(brier(a, q) < brier(b, q) for a, b, q in zip(pA, pB, true_p) if a != b)
    logloss = lambda p, q: -(float(q) * math.log(float(p)) + (1 - float(q)) * math.log(1 - float(p)))
    assert all(logloss(a, q) < logloss(b, q) for a, b, q in zip(pA, pB, true_p) if a != b)
    dBr = sum(brier(b, q) - brier(a, q) for a, b, q in zip(pA, pB, true_p)) / N
    assert dBr == eta ** 2 * (M + 24) / (4 * (M + 1))
    err = lambda p, q: (1 - q) if p >= Fraction(1, 2) else q
    d01 = sum(err(b, q) - err(a, q) for a, b, q in zip(pA, pB, true_p)) / N
    assert d01 == 2 * eta / (M + 1)
    d = delta_eq1(*moments(worlds, probs))
    assert d[0] / d[1] == 1 / (M * (1 - 2 * eta))
    assert round(float(dBr), 10) == 0.0000306931 and round(float(d01), 9) == 0.000198020
    assert round(float(d[0]), 8) == 0.00495050 and round(float(d[1]), 6) == 0.485149


# --------------------------------------------------------------------------- eqs. (9)-(10), first hit, eq. (11)
@pytest.mark.parametrize("n0,n1", [(1, 1), (1, 3), (2, 2), (2, 5), (3, 4)])
def test_discovery_law_bruteforce(n0, n1):
    labels = [0] * n0 + [1] * n1
    perms = list(itertools.permutations(range(n0 + n1)))
    T = [next(t for t in range(2, len(labels) + 1) if len({labels[i] for i in p[:t]}) == 2) for p in perms]
    for k in range(0, n0 + n1 + 1):
        assert Fraction(sum(t > k for t in T), len(T)) == p_T_greater(k, n0, n1)
    assert Fraction(sum(T), len(T)) == E_T(n0, n1)


def test_new136_reference_values():
    n0, n1 = 12, 124
    assert round(float(E_T(n0, n1)), 5) == 10.63446
    assert round(float(p_T_greater(9, n0, n1)), 5) == 0.42394
    assert round(float(p_T_greater(16, n0, n1)), 5) == 0.20787
    assert discovery_budget(Fraction(5, 100), n0, n1) == 29
    assert discovery_budget(Fraction(1, 100), n0, n1) == 42


def test_first_hit_identities():
    for N in range(2, 30):
        for r in range(1, N):
            ED = sum(first_hit_survival(k, N, r) for k in range(0, N + 1))
            assert ED == Fraction(N + 1, r + 1)
            assert Fraction(N, r) - ED == Fraction(N - r, r * (r + 1))
            for k in range(0, N - r + 1):
                s = first_hit_survival(k, N, r)
                assert s == Fraction(math.comb(N - k, r), math.comb(N, r))
                assert float(s) <= min((1 - r / N) ** k, (1 - k / N) ** r) + 1e-12


def test_tail_enrichment_iff():
    for N in range(2, 16):
        for r in range(1, N):
            for M in range(1, N + 1):
                for s in range(1, min(M, r) + 1):
                    if M - s > N - r:
                        continue
                    assert tail_dominates(M, s, N, r) == (Fraction(s, M) >= Fraction(r, N))


def test_weak_ranking_tail_example():
    # 3-point tail with one rare and two common labels: E[T_tail] = 7/3
    labels = [1, 0, 0]
    T = [next(t for t in range(2, 4) if len({labels[i] for i in p[:t]}) == 2) for p in itertools.permutations(range(3))]
    assert Fraction(sum(T), len(T)) == Fraction(7, 3)


# --------------------------------------------------------------------------- §5.4 and §7 examples
def test_equal_T_different_refinement_state():
    worlds = [(-1, 1, -1, 1), (-1, 1, 1, -1)]          # (Y_a, Y_b, Θ, 1 − Θ) as spins
    probs = [Fraction(1, 2)] * 2
    def risk_after(observed):
        sub = {}
        for w, p in zip(worlds, probs):
            sub.setdefault(tuple(w[i] for i in observed), []).append((w, p))
        tot = 0
        for grp in sub.values():
            for i in range(4):
                pp = sum(p for w, p in grp if w[i] == 1); pm = sum(p for w, p in grp if w[i] == -1)
                tot += min(pp, pm)
        return tot / 4
    assert risk_after((0, 1)) == Fraction(1, 4) and risk_after((2, 3)) == 0


def test_parity_cut_example():
    edges = [(0, 1), (1, 2), (0, 2)]
    indep = (list(itertools.product((0, 1), repeat=3)), [Fraction(1, 8)] * 8)
    parity = ([(0, 0, 0), (0, 1, 1), (1, 0, 1), (1, 1, 0)], [Fraction(1, 4)] * 4)
    def cut_risk(worlds, probs, observed=None):
        groups = {}
        for w, p in zip(worlds, probs):
            groups.setdefault(None if observed is None else w[observed], []).append((w, p))
        tot = 0
        for grp in groups.values():
            for (i, j) in edges:
                pc = sum(p for w, p in grp if w[i] != w[j]); tot += min(pc, sum(p for _, p in grp) - pc)
        return tot
    for law in (indep, parity):
        assert cut_risk(*law) == Fraction(3, 2)
    assert cut_risk(*indep, observed=0) == Fraction(3, 2) and cut_risk(*parity, observed=0) == 1


# --------------------------------------------------------------------------- §5.3 q20 construction on the real evaluator
def test_q20_construction_on_historical_evaluator():
    from src.external_validation.analysis import boundary_flags
    m = 6; eps = 1 / (100 * m * m)
    xs = np.array([-2, -eps] + [j * eps for j in range(1, 5 * m - 1)])
    assert len(xs) == 5 * m
    y = (xs > 0).astype(int)
    R = 5.0                                              # training points -R, +R join the evaluation batch
    allx = np.r_[xs, -R, R]; ally = np.r_[y, 0, 1]
    feats = np.c_[allx, np.zeros((len(allx), 3)) + [1.0, 2.0, 3.0]]
    flags = boundary_flags(feats, ally, np.arange(len(xs)), [f"s{i:03d}" for i in range(len(allx))], "entire_evaluation_batch")[20]
    chosen = set(np.round(xs[flags] / eps).astype(int))
    assert chosen == {-1} | set(range(1, m))
    yA = (xs > -1).astype(int); yB = (xs > (m - 1.5) * eps).astype(int)
    accA = np.mean(yA[flags] == y[flags]); accB = np.mean(yB[flags] == y[flags])
    assert np.isclose(accA, (m - 1) / m) and np.isclose(accB, 2 / m)
