"""Property tests for the Week 14 discovery theorems (D1-D5)."""
import math

import numpy as np
from scipy.spatial.distance import cdist

from src.week14_order import (SIGNS_O3, dominance, first_both, first_hit, front_discovery_order,
                              interleave, maximal, minimal)


def _maximin(z, start):
    order = [start]
    near = np.linalg.norm(z - z[start], axis=1)
    near[start] = -1
    for _ in range(len(z) - 1):
        j = int(np.argmax(near))
        order.append(j)
        near = np.minimum(near, np.linalg.norm(z - z[j], axis=1))
        near[order] = -1
    return np.asarray(order)


def test_D1_exchangeable_prior_makes_every_algorithm_random():
    """Under a uniformly random rare set, an adaptive geometric rule has the hypergeometric law."""
    rng = np.random.default_rng(0)
    n, K, sims = 40, 3, 6000
    z = rng.random((n, 2))
    orders = [_maximin(z, s) for s in range(n)]
    T = []
    for _ in range(sims):
        R = rng.choice(n, K, replace=False)
        y = np.ones(n, int)
        y[R] = 0
        T.append(first_hit(orders[rng.integers(n)], y, 0))
    T = np.asarray(T)
    for t in (1, 5, 10, 20):
        exact = math.comb(n - t, K) / math.comb(n, K)
        assert abs(np.mean(T > t) - exact) < 0.02
    assert abs(T.mean() - (n + 1) / (K + 1)) < 0.4


def test_D2_certificate_is_sharp():
    """If h(S) > r a labelling with rho* >= h(S) > r is missed by S (the ball construction)."""
    rng = np.random.default_rng(1)
    for _ in range(30):
        U = rng.random((80, 3))
        S = rng.choice(80, 6, replace=False)
        dS = cdist(U, U[S]).min(axis=1)
        h = dS.max()
        u = int(np.argmax(dS))
        R = np.nonzero(np.linalg.norm(U - U[u], axis=1) < h)[0]
        assert not set(S) & set(R)
        maj = np.setdiff1d(np.arange(80), R)
        assert np.linalg.norm(U[maj] - U[u], axis=1).min() >= h - 1e-12


def test_D3_fronts_contain_both_classes_for_monotone_labels():
    rng = np.random.default_rng(2)
    for _ in range(200):
        x = rng.random((60, 4))
        w = rng.random(3) + .1
        score = w[0] * x[:, 0] - w[1] * x[:, 1] - w[2] * x[:, 2] + rng.normal(0, .05) * 0
        thr = np.quantile(score, rng.uniform(.02, .98))
        y = (score > thr).astype(int)
        D = dominance(x, SIGNS_O3)
        order, mn, mx = front_discovery_order(D, np.arange(60))
        if y.min() == 0:
            assert (y[mn] == 0).any()
        if y.max() == 1:
            assert (y[mx] == 1).any()
        if 0 < y.mean() < 1:
            assert first_both(order, y) <= len(set(mn) | set(mx))


def test_D3_lower_bound_singleton_minimal_is_monotone():
    rng = np.random.default_rng(3)
    x = rng.random((50, 3))
    D = dominance(np.c_[x, np.zeros(50)], SIGNS_O3)
    for m in minimal(D):
        y = np.ones(50, int)
        y[m] = 0
        assert not (D & (y[:, None] == 1) & (y[None, :] == 0)).any()


def test_D5_interleaving_is_within_factor_J():
    rng = np.random.default_rng(4)
    for _ in range(300):
        n = 30
        y = (rng.random(n) < .1).astype(int)
        if y.sum() == 0:
            continue
        orders = [rng.permutation(n) for _ in range(3)]
        h = interleave(*orders)
        assert first_hit(h, y, 1) <= 3 * min(first_hit(o, y, 1) for o in orders)


def test_expected_maxima_harmonic_numbers():
    """E|Max| for iid product samples equals the generalized harmonic number H_n^(d-1)."""
    def H(n, k):
        if k == 0:
            return 1.0
        return sum(H(i, k - 1) / i for i in range(1, n + 1))
    rng = np.random.default_rng(5)
    n = 30
    for d in (2, 3):
        counts = [len(maximal(dominance(np.c_[rng.random((n, d)), np.zeros((n, 4 - d))][:, :4], np.r_[np.ones(d), np.zeros(4 - d)])))
                  for _ in range(2000)]
        assert abs(np.mean(counts) - H(n, d - 1)) < 0.15
