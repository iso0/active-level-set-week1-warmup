"""Week 16 — exact (rational) implementations of the Astra round-1 statements used for verification.

Equation numbers refer to outputs/astra_round1/ASTRA_ROUND1.md.  Joint laws are given as a list of worlds
(tuples of spins S_i ∈ {−1, +1}) with Fraction probabilities.  Everything here is exact arithmetic; floats
appear only in the tests that compare with Astra's printed decimals.
"""
from __future__ import annotations

import itertools
from fractions import Fraction
from math import comb, isqrt


# ----------------------------------------------------------------------------- one-query Hamming value
def moments(worlds, probs):
    n = len(worlds[0])
    m = [sum(p * w[i] for w, p in zip(worlds, probs)) for i in range(n)]
    c = [[sum(p * w[i] * w[j] for w, p in zip(worlds, probs)) for j in range(n)] for i in range(n)]
    return m, c


def delta_eq1(m, c):
    """Astra eq. (1): Δ_j = (1/2N) Σ_i (|c_ij| − |m_i|)_+."""
    n = len(m)
    return [sum(max(abs(c[i][j]) - abs(m[i]), 0) for i in range(n)) / (2 * n) for j in range(n)]


def delta_brute(worlds, probs):
    """Δ_j by definition: current Bayes Hamming risk minus expected Bayes risk after revealing S_j."""
    n = len(worlds[0])
    def joint(i, si, j, sj):
        return sum(p for w, p in zip(worlds, probs) if w[i] == si and w[j] == sj)
    u = [min(sum(p for w, p in zip(worlds, probs) if w[i] == 1), sum(p for w, p in zip(worlds, probs) if w[i] == -1)) for i in range(n)]
    out = []
    for j in range(n):
        after = sum(min(joint(i, 1, j, s), joint(i, -1, j, s)) for i in range(n) for s in (-1, 1))
        out.append((sum(u) - after) / n)
    return out


def margin_choices(worlds, probs):
    """All maximizers of u_j = min(p_j, 1 − p_j) (exact margin, every tie)."""
    m, _ = moments(worlds, probs)
    best = min(abs(x) for x in m)
    return [j for j, x in enumerate(m) if abs(x) == best]


def bayes_error_pair(table):
    """table[(t, o)] = P(T = t, O = o) for t, o ∈ {−1, +1}; returns (Bayes error after O, E T, E[T O])."""
    err = sum(min(table[(1, o)], table[(-1, o)]) for o in (-1, 1))
    ET = sum(t * p for (t, o), p in table.items())
    ETO = sum(t * o * p for (t, o), p in table.items())
    return err, ET, ETO


# ----------------------------------------------------------------------------- constructions
def decoy_cluster_law(M, eta):
    """Coordinate 0 = fair decoy D; coordinates 1..M equal to Z ~ Bernoulli(1/2 + η) (spins)."""
    worlds, probs = [], []
    for d in (-1, 1):
        for z in (-1, 1):
            worlds.append((d,) + (z,) * M)
            probs.append(Fraction(1, 2) * (Fraction(1, 2) + eta if z == 1 else Fraction(1, 2) - eta))
    return worlds, probs


def kappa_params(N):
    M = N - 1
    r = isqrt(M)
    a = r if (r - M) % 2 == 0 else r - 1
    b = a + 2
    tau = Fraction(M + a * b, a + b)
    return M, a, b, tau


def kappa(N):
    M, a, b, tau = kappa_params(N)
    return (N + 2 * tau) / (N * (1 + tau))


def root_leaf_law(N):
    """Astra §4.5 equality distribution: root S_0 = R, leaves S_i = −R V_i, Σ V_i = W ∈ {a, b}."""
    M, a, b, tau = kappa_params(N)
    pb = Fraction(M - a * a, b * b - a * a)
    worlds, probs = [], []
    for R in (-1, 1):
        for W, pw in ((a, 1 - pb), (b, pb)):
            if pw == 0 or W > M:
                continue
            k = (M + W) // 2                      # number of +1 entries in V
            n_vec = comb(M, k)
            for plus in itertools.combinations(range(M), k):
                V = [-1] * M
                for i in plus:
                    V[i] = 1
                worlds.append((R,) + tuple(-R * v for v in V))
                probs.append(Fraction(1, 2) * pw / n_vec)
    return worlds, probs


def uniform_ratio(worlds, probs):
    d = delta_eq1(*moments(worlds, probs))
    return sum(d) / (len(d) * max(d))


# ----------------------------------------------------------------------------- discovery (eqs. 9-11)
def p_T_greater(k, n0, n1):
    """Eq. (9): P(T_both > k) under uniform order, k ≥ 1 (P(T > 0) = 1)."""
    N = n0 + n1
    if k == 0:
        return Fraction(1)
    return Fraction(comb(n0, k) + comb(n1, k), comb(N, k))


def E_T(n0, n1):
    """Eq. (10)."""
    N = n0 + n1
    return Fraction(N + 1, n0 + 1) + Fraction(N + 1, n1 + 1) - 1


def discovery_budget(delta, n0, n1):
    k = 1
    while p_T_greater(k, n0, n1) > delta:
        k += 1
    return k


def first_hit_survival(k, N, r):
    """P(D > k) for the first rare hit, uniform order without replacement."""
    return Fraction(comb(N - r, k), comb(N, k)) if k <= N else Fraction(0)


def tail_dominates(M, s, N, r):
    """D_A ≤_st D_X (uniform within a tail of size M holding s rare vs whole pool N holding r rare)."""
    return all(first_hit_survival(k, M, s) <= first_hit_survival(k, N, r) for k in range(0, M + 1))
