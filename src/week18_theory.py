"""Week 18 theory checks (THEORY_WEEK18.md, T18-1).

Threshold localization on a 1-D finite pool x_1 < … < x_N with a monotone increasing conduction branch c and
boundary index k* = min{i : c(x_i) ≥ u} (k* = N + 1 if none).
  (a) binary labels y_i = 1[c(x_i) ≥ u]: bisection needs ⌈log2(N + 1)⌉ queries in the worst case and no
      algorithm needs fewer (N + 1 possible outcomes, one bit per query);
  (b) censored observations (y_i always; c(x_i) only when y_i = 0) with affine c: 2 queries always suffice;
  (c) smooth c: a safeguarded censored secant (extrapolate the crossing from the two most recent conduction
      values; bisect when the extrapolation leaves the bracket or fails to shrink it by half on two consecutive
      steps) localizes k* with far fewer queries than bisection.
"""
from __future__ import annotations

import math

import numpy as np


def bisection_queries(y):
    lo, hi, q = 0, len(y) + 1, 0          # k* ∈ (lo, hi]; positions 1-based
    while hi - lo > 1:
        mid = (lo + hi) // 2; q += 1
        if y[mid - 1] == 1:
            hi = mid
        else:
            lo = mid
    return q, hi


def affine_censored_queries(x, c, u):
    q = 0
    for i in (0, 1):
        q += 1
        if c[i] >= u:
            return q, i + 1
    beta = (c[1] - c[0]) / (x[1] - x[0]); alpha = c[0] - beta * x[0]
    return q, next((i + 1 for i in range(len(x)) if alpha + beta * x[i] >= u), len(x) + 1)


def censored_secant_queries(x, c, u):
    N = len(x); q = 0
    def ask(i):                                   # 1-based index
        nonlocal q
        q += 1
        return c[i - 1] >= u
    if ask(1):
        return q, 1
    if not ask(N):
        return q, N + 1
    lo, hi = 1, N; cond = [(x[0], c[0])]; slow = 0
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if len(cond) >= 2 and slow < 2:
            (x1, c1), (x2, c2) = cond[-2], cond[-1]
            s = (c2 - c1) / (x2 - x1)
            t = x2 + (u - c2) / s if s > 0 else None
            if t is None or not (x[lo - 1] < t < x[hi - 1]):
                j = mid
            else:
                j = min(range(lo + 1, hi), key=lambda i: abs(x[i - 1] - t))
        else:
            j = mid; slow = 0
        width = hi - lo
        if ask(j):
            hi = j
        else:
            lo = j; cond.append((x[j - 1], c[j - 1]))
        slow = slow + 1 if (hi - lo) > width / 2 else 0
    return q, hi


def censored_quadratic_queries(x, c, u):
    """As censored_secant_queries but extrapolating with the quadratic through the last three conduction values
    (root nearest to the bracket), secant with two, bisection with one."""
    N = len(x); q = 0
    def ask(i):
        nonlocal q
        q += 1
        return c[i - 1] >= u
    if ask(1):
        return q, 1
    if not ask(N):
        return q, N + 1
    lo, hi = 1, N; cond = [(x[0], c[0])]; slow = 0
    while hi - lo > 1:
        mid = (lo + hi) // 2; t = None
        if slow < 2 and len(cond) >= 2:
            pts = cond[-3:] if len(cond) >= 3 else cond[-2:]
            xs = np.array([p[0] for p in pts]); cs = np.array([p[1] for p in pts]) - u
            coef = np.polyfit(xs, cs, len(pts) - 1)
            roots = np.roots(coef); roots = roots[np.isreal(roots)].real
            roots = roots[(roots > x[lo - 1]) & (roots < x[hi - 1])]
            if len(roots):
                t = float(roots.min())
        j = mid if t is None else min(range(lo + 1, hi), key=lambda i: abs(x[i - 1] - t))
        if t is None:
            slow = 0
        width = hi - lo
        if ask(j):
            hi = j
        else:
            lo = j; cond.append((x[j - 1], c[j - 1]))
        slow = slow + 1 if (hi - lo) > width / 2 else 0
    return q, hi


def check(n_trials=400, seed=0):
    rng = np.random.default_rng(seed); out = []
    for N in (16, 64, 256, 1024, 4096):
        x = np.sort(rng.random(N)); rows = {"bisection": [], "affine": [], "secant_smooth": [], "bisection_smooth": []}
        for _ in range(n_trials):
            alpha, beta = rng.uniform(-3, -.05), rng.uniform(.5, 6)
            c = alpha + beta * x
            kt = next((i + 1 for i in range(N) if c[i] >= 0), N + 1)
            qb, kb = bisection_queries((c >= 0).astype(int)); qa, ka = affine_censored_queries(x, c, 0.0)
            assert kb == kt and ka == kt
            rows["bisection"].append(qb); rows["affine"].append(qa)
            # smooth nonlinear branch: c = alpha + beta x + gamma x^2 + delta sin(4x), monotone by construction
            g, d = rng.uniform(0, 3), rng.uniform(0, .1)
            cs = alpha + beta * x + g * x ** 2 + d * np.sin(4 * x)
            if np.any(np.diff(cs) <= 0):
                continue
            kt = next((i + 1 for i in range(N) if cs[i] >= 0), N + 1)
            qs, ks = censored_secant_queries(x, cs, 0.0); qb2, kb2 = bisection_queries((cs >= 0).astype(int))
            qq, kq = censored_quadratic_queries(x, cs, 0.0)
            assert ks == kt and kb2 == kt and kq == kt
            rows["secant_smooth"].append(qs); rows["bisection_smooth"].append(qb2); rows.setdefault("quad_smooth", []).append(qq)
        out.append({"N": N, "log2_bound": math.ceil(math.log2(N + 1)), "bisection_max": max(rows["bisection"]),
                    "affine_censored_max": max(rows["affine"]), "smooth_bisection_mean": float(np.mean(rows["bisection_smooth"])),
                    "smooth_secant_mean": float(np.mean(rows["secant_smooth"])), "smooth_secant_max": int(max(rows["secant_smooth"])),
                    "smooth_quadratic_mean": float(np.mean(rows["quad_smooth"])), "smooth_quadratic_max": int(max(rows["quad_smooth"]))})
    return out
