"""Week 15 checks of the corrected discovery laws (erratum E15-1, E15-2)."""
from fractions import Fraction
from math import comb

import numpy as np

from src.week14_order import first_both


def p_tboth_gt(N, K, t):
    if t == 0:
        return 1.0
    return (comb(K, t) + comb(N - K, t)) / comb(N, t)


def test_expected_tboth_closed_form_exact():
    for N in range(2, 40):
        for K in range(1, N):
            e = 1 + sum(Fraction(comb(K, t) + comb(N - K, t), comb(N, t)) for t in range(1, N + 1))
            assert e == Fraction(N + 1, K + 1) + Fraction(N + 1, N - K + 1) - 1


def test_tboth_law_for_an_adaptive_rule():
    """A rule whose continuation depends on the first label still has the random-sampling law."""
    rng = np.random.default_rng(0)
    N, K, sims = 30, 4, 40000
    x = rng.random(N)
    up, down = np.argsort(x), np.argsort(-x)
    T = []
    for _ in range(sims):
        y = np.ones(N, int)
        y[rng.choice(N, K, replace=False)] = 0
        q1 = int(rng.integers(N))
        # adaptive: after a majority first label go up the feature, after a minority go down
        rest = [i for i in (up if y[q1] == 1 else down) if i != q1]
        T.append(first_both(np.r_[q1, rest], y))
    T = np.asarray(T)
    for t in (1, 2, 3, 5, 8, 12):
        assert abs(np.mean(T > t) - p_tboth_gt(N, K, t)) < 0.01
    assert abs(T.mean() - ((N + 1) / (K + 1) + (N + 1) / (N - K + 1) - 1)) < 0.08


def test_week14_wrong_formula_is_indeed_wrong():
    N, K = 30, 4
    wrong = comb(N - 1, K) / comb(N, K)          # T_m law at t = 1
    right = p_tboth_gt(N, K, 1)                    # = 1 for t = 1 (one label is always one class)
    assert right == 1.0 and wrong < 1.0


def test_front_size_numeric_e15_2():
    from functools import lru_cache

    @lru_cache(None)
    def H(n, k):
        return 1.0 if k == 0 else sum(H(i, k - 1) / i for i in range(1, n + 1))
    assert abs(H(108, 2) - 14.67) < 0.01
