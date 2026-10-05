"""Week 18 T18-1 checks: bisection optimality bound and exact 2-query localization for affine censored branches."""
import math

import numpy as np

from src.week18_theory import affine_censored_queries, bisection_queries, censored_quadratic_queries


def test_bisection_worst_case_equals_information_bound():
    for N in (1, 2, 7, 16, 100):
        worst = 0
        for k in range(1, N + 2):
            y = np.r_[np.zeros(k - 1), np.ones(N - k + 1)].astype(int)
            q, kk = bisection_queries(y)
            assert kk == k
            worst = max(worst, q)
        assert worst == math.ceil(math.log2(N + 1))


def test_affine_censored_two_queries_exact():
    rng = np.random.default_rng(0)
    for _ in range(300):
        N = int(rng.integers(3, 500)); x = np.sort(rng.random(N))
        a, b = rng.uniform(-3, -.01), rng.uniform(.5, 6); c = a + b * x
        q, k = affine_censored_queries(x, c, 0.0)
        assert q <= 2 and k == next((i + 1 for i in range(N) if c[i] >= 0), N + 1)


def test_censored_quadratic_is_correct():
    rng = np.random.default_rng(1)
    for _ in range(200):
        N = 256; x = np.sort(rng.random(N)); c = rng.uniform(-3, -.05) + rng.uniform(.5, 6) * x + rng.uniform(0, 3) * x ** 2
        q, k = censored_quadratic_queries(x, c, 0.0)
        assert k == next((i + 1 for i in range(N) if c[i] >= 0), N + 1)
