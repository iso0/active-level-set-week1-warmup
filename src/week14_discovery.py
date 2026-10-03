"""Week 14 Study 1 — label-blind discovery of both classes in rare-regime finite pools.

CONTROLLED SYNTHETIC evidence for Theorems D1-D5 (see outputs/week14_research_program/THEORY.md).
Each benchmark cell draws a pool, a labelling from a structural family, and evaluates
query orders that may use labels only to decide *when* both classes have been seen
(ADAPT8 additionally uses the class of the first observed labels, as in Week 12).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.preprocessing import StandardScaler

from src.week14_order import dominance, first_both, front_discovery_order, interleave

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week14_research_program/synthetic/discovery"
FAMILIES = ("mono", "mono_noise", "mono_tworegime", "islands", "bump", "slab",
            "heldout_branin", "heldout_hartmann", "heldout_rotated_mono", "heldout_twoislands_skew")
DESIGNS = ("uniform", "skewed", "clustered")


# ----------------------------------------------------------------------------- input pools
def sample_pool(n, d, design, rng):
    if design == "uniform":
        return rng.random((n, d))
    if design == "skewed":       # campaign-like: concentrated, correlated, heavy in one corner
        z = rng.multivariate_normal(np.zeros(d), .5 * np.eye(d) + .5, size=n)
        return 1 / (1 + np.exp(-(z * .9 + .6)))
    if design == "clustered":    # three operating windows
        c = rng.random((3, d))
        k = rng.integers(3, size=n)
        return np.clip(c[k] + .12 * rng.standard_normal((n, d)), 0, 1)
    raise ValueError(design)


def signs_for(d):
    s = np.zeros(d, int)
    s[0] = 1
    s[1:min(3, d)] = -1
    return s


def nominal_score(u, signs):
    return u @ signs


# ----------------------------------------------------------------------------- labellings
def labelling(family, u, prevalence, rng, signs):
    n, d = u.shape
    if family in ("mono", "mono_noise", "mono_tworegime"):
        w = (rng.random(d) + .25) * (signs != 0)
        f = u @ (w * signs)
        if family == "mono_tworegime":   # boundary rotates to a single-coordinate threshold in a corner
            f = np.minimum(f, 2.0 * (np.quantile(u[:, 1], .8) - u[:, 1]) + f.mean())
        if family == "mono_noise":
            f = f + .08 * rng.standard_normal(n)
        low_rare = rng.random() < .5
        t = np.quantile(f, prevalence if low_rare else 1 - prevalence)
        return (f > t).astype(int)
    if family == "islands":
        m = rng.integers(1, 4)
        cen = u[rng.choice(n, m, replace=False)]
        dist = np.min(np.linalg.norm(u[:, None, :] - cen[None], axis=2), axis=1)
        rare = dist <= np.quantile(dist, prevalence)
        return (~rare).astype(int)
    if family == "bump":
        c = np.ones(d) * .5
        c[0], c[1] = .9, .95
        if d > 2:
            c[2] = .1
        sc = np.full(d, .35)
        sc[1] = .12
        f = 4 * (u @ signs) - 1.5 * np.exp(-.5 * (((u - c) / sc) ** 2).sum(1)) * 4
        t = np.quantile(f, prevalence)
        return (f > t).astype(int)
    if family == "heldout_mono_curved":      # monotone, exponent on the VX-like axis grows with P
        f = 2.2 * u[:, 0] - .8 * (1 + 1.5 * u[:, 0]) * u[:, 1] - (1.2 * u[:, 2] if d > 2 else 0)
        low_rare = rng.random() < .5
        t = np.quantile(f, prevalence if low_rare else 1 - prevalence)
        return (f > t).astype(int)
    if family == "heldout_branin":            # 2-D Branin on the first two coordinates (3 basins)
        x1, x2 = 15 * u[:, 0] - 5, 15 * u[:, 1]
        f = (x2 - 5.1 / (4 * np.pi ** 2) * x1 ** 2 + 5 / np.pi * x1 - 6) ** 2 + 10 * (1 - 1 / (8 * np.pi)) * np.cos(x1) + 10
        low_rare = rng.random() < .5
        t = np.quantile(f, prevalence if low_rare else 1 - prevalence)
        return (f > t).astype(int)
    if family == "heldout_hartmann":          # Hartmann-3 on the first three coordinates (d >= 3)
        A = np.array([[3, 10, 30], [.1, 10, 35], [3, 10, 30], [.1, 10, 35.]])
        Pm = 1e-4 * np.array([[3689, 1170, 2673], [4699, 4387, 7470], [1091, 8732, 5547], [381, 5743, 8828.]])
        al = np.array([1, 1.2, 3, 3.2])
        x = u[:, :3]
        f = -(al * np.exp(-((A[None] * (x[:, None, :] - Pm[None]) ** 2).sum(2)))).sum(1)
        low_rare = rng.random() < .5
        t = np.quantile(f, prevalence if low_rare else 1 - prevalence)
        return (f > t).astype(int)
    if family == "heldout_rotated_mono":      # monotone in a rotated frame: the known signs are partly wrong
        th = rng.uniform(np.deg2rad(20), np.deg2rad(60))
        R = np.eye(d)
        R[0, 0], R[0, 1], R[1, 0], R[1, 1] = np.cos(th), -np.sin(th), np.sin(th), np.cos(th)
        f = (u @ R.T) @ (np.abs(signs) * signs * (rng.random(d) + .25))
        low_rare = rng.random() < .5
        t = np.quantile(f, prevalence if low_rare else 1 - prevalence)
        return (f > t).astype(int)
    if family == "heldout_twoislands_skew":   # one island at the order-minimal corner, one in the bulk
        corner = np.where(signs > 0, 0.0, np.where(signs < 0, 1.0, .5))
        cen = np.vstack([corner, u[rng.integers(n)]])
        dist = np.min(np.linalg.norm(u[:, None, :] - cen[None], axis=2), axis=1)
        rare = dist <= np.quantile(dist, prevalence)
        return (~rare).astype(int)
    if family == "slab":
        a = rng.standard_normal(d)
        g = u @ a
        c = np.quantile(g, rng.uniform(.3, .7))
        dev = np.abs(g - c)
        rare = dev <= np.quantile(dev, prevalence)
        return (~rare).astype(int)
    raise ValueError(family)


# ----------------------------------------------------------------------------- strategies
def maximin(z, start):
    order = [start]
    near = np.linalg.norm(z - z[start], axis=1)
    near[start] = -1
    for _ in range(len(z) - 1):
        j = int(np.argmax(near))
        order.append(j)
        near = np.minimum(near, np.linalg.norm(z - z[j], axis=1))
        near[order] = -1
    return np.asarray(order)


def score_extremes(score):
    lo = np.argsort(score, kind="stable")
    hi = lo[::-1]
    return interleave(lo, hi)


def strategies(u, signs, rng, y=None):
    """Return dict name -> query order.  Only ADAPT8 depends on labels (direction after 8 seeds)."""
    z = StandardScaler().fit_transform(u)
    start = int(rng.integers(len(u)))
    mm = maximin(z, start)
    s = nominal_score(u, signs)
    D = dominance(u, signs)
    fr, mn, mx = front_discovery_order(D, np.arange(len(u)), score=s)
    front_then = np.r_[fr, [i for i in mm if i not in set(fr)]]
    rand = rng.permutation(len(u))
    out = {"RAND": rand, "MAXI": mm, "SCORE": score_extremes(s),
           "FRONT": front_then.astype(int), "HEDGE": interleave(mm, front_then, score_extremes(s)),
           "HEDGE_FR": interleave(front_then.astype(int), rand)}
    if y is not None:
        seeds = list(mm[:8])
        seen = set(y[seeds])
        if len(seen) == 2:
            out["ADAPT8"] = mm
        else:
            rest = [i for i in np.argsort(s * (1 if 1 in seen else -1), kind="stable") if i not in set(seeds)]
            out["ADAPT8"] = np.asarray(seeds + rest, int)
    return out, {"n_min_front": len(mn), "n_max_front": len(mx)}


def run_cell(family, d, n, prevalence, design, rep):
    rng = np.random.default_rng([14, FAMILIES.index(family), d, n, int(prevalence * 1000), DESIGNS.index(design), rep])
    signs = signs_for(d)
    u = sample_pool(n, d, design, rng)
    y = labelling(family, u, prevalence, rng, signs)
    if y.min() == y.max():
        return []
    orders, info = strategies(u, signs, rng, y)
    D = dominance(u, signs)
    viol = int((D & (y[:, None] == 1) & (y[None, :] == 0)).sum())
    rows = []
    for name, o in orders.items():
        rows.append({"family": family, "d": d, "n": n, "prevalence": prevalence, "design": design, "rep": rep,
                     "strategy": name, "T_both": first_both(o, y), "K_minority": int(min(y.sum(), n - y.sum())),
                     "monotone_violations": viol, **info})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=100)
    ap.add_argument("--families", default="mono,mono_noise,mono_tworegime,islands,bump,slab")
    ap.add_argument("--tag", default="development")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    cells = [(f, d, n, p, des, r) for f in a.families.split(",") for d in (2, 4, 6) for n in (108, 324)
             for p in (.03, .08, .15) for des in ("uniform", "skewed", "clustered") for r in range(a.reps)
             if not (f == "heldout_hartmann" and d < 3)]
    res = Parallel(n_jobs=7, batch_size=64)(delayed(run_cell)(*c) for c in cells)
    df = pd.DataFrame([row for rows in res for row in rows])
    df.to_parquet(OUT / f"discovery_{a.tag}.parquet", index=False)
    s = df.groupby(["family", "strategy"]).T_both.agg(mean="mean", q90=lambda v: v.quantile(.9), mx="max",
                                                      p16=lambda v: (v <= 16).mean())
    print(s.round(2).unstack("strategy").to_string())


if __name__ == "__main__":
    main()
