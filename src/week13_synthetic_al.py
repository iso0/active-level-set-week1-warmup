"""Week 13 synthetic active level-set paths (CONTROLLED METHODOLOGICAL EVIDENCE).

Design fixed before execution (see outputs/.../synthetic/DESIGN.md):
  scenarios  BAL (50/50, whole box), OLD (18% class 1, OLD box), NEW (9% class 0, corner box)
  pool sizes 108 and 324 (evaluation pool 136 and 405, independent draw)
  policies   random, margin, coverage (Candidate-B-like band rule until B40, then margin), maximin
  models     G (zero-mean GPC) and P (physics trend + capped GPC discrepancy), oracle fixed hyperparameters
  startup    8 maximin points, then maximin continuation until both classes are observed (all paid)
  horizon    80; replicates are independent pool/evaluation draws
  noise      observed labels y = 1[f(u) + sigma*eps > 0], eps iid N(0,1) per simulated case,
             sigma in {0.5, 1.0}; the estimand is the noise-free level set {f = 0}
             (dense surface metrics use it), finite-pool metrics use observed labels
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.spatial.distance import cdist
from sklearn.preprocessing import StandardScaler

from src.week13_boundary_metrics import edge_metrics, gabriel_edges, nearest_opposite
from src.week13_synthetic import (DenseTruth, LaplaceGPC, PhysicsTrend, Scenario, labels, latent, physics_score)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week13_boundary_evaluation_and_mechanisms/synthetic"
A_REAL = 1.5
C_OLD = 0.818  # calibrated: 18% class 1 in the OLD box at A = 1.5
SCENARIOS = {
    "BAL": Scenario("BAL", (0, 0, 0, 0), (1, 1, 1, 1), None, A_REAL),
    "OLD": Scenario("OLD", (0, 0, 0, 0), (1, 1, 1, .5), C_OLD, A_REAL),
    "NEW": Scenario("NEW", (.8, 0, 0, 0), (1, 1, .2, 1), C_OLD, A_REAL),
}
POLICIES = ("random", "margin", "coverage", "maximin")
MODELS = ("G", "P")
HORIZON = 80
DENSE_BUDGETS = tuple(range(8, 81, 4))
SIGMAS = (0.5, 1.0)


def noisy_labels(u, sc, sigma, rng):
    return (latent(u, sc) + sigma * rng.standard_normal(len(u)) > 0).astype(int)


def calibrated(name):
    sc = SCENARIOS[name]
    if sc.offset is None:  # choose c for 50% prevalence in the whole box
        from scipy.optimize import brentq
        u = Scenario("x", sc.lo, sc.hi, 0, 0).sample(200000, np.random.default_rng(99))
        c = brentq(lambda c: labels(u, Scenario("x", sc.lo, sc.hi, c, sc.amp)).mean() - .5, -3, 3)
        sc = Scenario(sc.name, sc.lo, sc.hi, float(c), sc.amp)
    return sc


def to_box(u, sc):
    return (np.asarray(u) - np.asarray(sc.lo)) / (np.asarray(sc.hi) - np.asarray(sc.lo))


def oracle_hypers(sc, sigma, n=500, seed=7):
    """Fit Matern-3/2 ARD hyperparameters once on a large labelled sample (oracle, not part of AL)."""
    from sklearn.gaussian_process import GaussianProcessClassifier
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern
    rng = np.random.default_rng(seed)
    u = sc.sample(n, rng)
    z = to_box(u, sc)
    y = noisy_labels(u, sc, sigma, rng)
    k = ConstantKernel(4.0, (0.05, 400)) * Matern([0.3] * 4, (0.02, 50), nu=1.5)
    g = GaussianProcessClassifier(k, n_restarts_optimizer=2, random_state=0).fit(z, y)
    return {"var": float(g.kernel_.k1.constant_value), "ls": np.asarray(g.kernel_.k2.length_scale, float).tolist()}


def maximin_order(z, rng):
    zs = StandardScaler().fit_transform(z)
    n = len(z)
    order = [int(rng.integers(n))]
    nearest = np.linalg.norm(zs - zs[order[0]], axis=1)
    nearest[order[0]] = -1
    for _ in range(n - 1):
        j = int(np.argmax(nearest))
        order.append(j)
        nearest = np.minimum(nearest, np.linalg.norm(zs - zs[j], axis=1))
        nearest[order] = -1
    return np.asarray(order)


def q20_flags(z_eval, y_eval):
    zs = StandardScaler().fit_transform(z_eval)
    d, _ = nearest_opposite(zs, y_eval)
    order = np.argsort(d, kind="stable")
    flag = np.zeros(len(y_eval), bool)
    flag[order[:math.ceil(.2 * len(y_eval))]] = True
    return flag


def finite_metrics(y, yhat, q, edges, minority):
    r = {}
    for tag, m in (("q20", q), ("full", np.ones(len(y), bool))):
        yy, hh = y[m], yhat[m]
        r[f"{tag}_accuracy"] = float(np.mean(yy == hh))
        rec = [np.mean(hh[yy == c] == c) if (yy == c).any() else np.nan for c in (0, 1)]
        r[f"{tag}_balanced_accuracy"] = float(np.nanmean(rec))
        r[f"{tag}_minority_recall"] = float(rec[minority])
    calls = yhat[q] == minority
    r["q20_correct_minority_calls"] = int((calls & (y[q] == minority)).sum())
    r["q20_wrong_minority_calls"] = int((calls & (y[q] != minority)).sum())
    em = edge_metrics(edges, y, yhat)
    r.update({k: em[k] for k in ("BER", "BEBA", "BEF1", "n_pred_cut", "spurious_cut")})
    return r


class Model:
    def __init__(self, kind, hyp, sc):
        self.kind, self.hyp, self.sc = kind, hyp, sc

    def fit(self, z, u, y):
        if self.kind == "G":
            self.gp = LaplaceGPC(self.hyp["ls"], self.hyp["var"]).fit(z, y)
            self.trend = None
        else:
            self.trend = PhysicsTrend().fit(physics_score(u), y)
            self.gp = LaplaceGPC(self.hyp["ls"], 1.0).fit(z, y, mean=self.trend.latent(physics_score(u)))
        return self

    def _mean(self, u):
        return None if self.trend is None else self.trend.latent(physics_score(u))

    def latent(self, z, u):
        return self.gp.latent_mean(z, self._mean(u))

    def proba(self, z, u):
        return self.gp.proba(z, self._mean(u))


def coverage_choice(cands, p, s_pool, s_rev, y_rev, z_pool_std, rev):
    kh = s_rev[y_rev == 1]
    co = s_rev[y_rev == 0]
    lo, hi = sorted((kh.min(), co.max()))
    width = hi - lo
    pad = max(0.02, 0.25 * width)
    band = cands[(s_pool[cands] >= lo - pad) & (s_pool[cands] <= hi + pad)]
    if len(band) == 0:
        return None
    unc = 1 - 2 * np.abs(p[band] - .5)
    d4 = cdist(z_pool_std[band], z_pool_std[rev]).min(axis=1)
    score = pd.Series(unc).rank().to_numpy() + pd.Series(d4).rank().to_numpy()
    best = np.flatnonzero(score == score.max())
    return int(band[best[0]])


def run_path(scn, sigma, n_pool, rep, policy, model_kind, hyp, out_dir):
    dest = out_dir / f"{scn}_s{sigma}_n{n_pool}_r{rep:03d}_{policy}_{model_kind}.parquet"
    if dest.exists():
        return str(dest)
    sc = calibrated(scn)
    rng = np.random.default_rng([13, int(sigma * 10), n_pool, rep, 1])
    u_pool = sc.sample(n_pool, rng)
    u_eval = sc.sample(int(round(n_pool / .8)), rng)
    y_pool, y_eval = noisy_labels(u_pool, sc, sigma, rng), noisy_labels(u_eval, sc, sigma, rng)
    z_pool, z_eval = to_box(u_pool, sc), to_box(u_eval, sc)
    minority = int(np.mean(y_pool) > .5) ^ 1  # class with smaller pool share
    q = q20_flags(z_eval, y_eval)
    edges = gabriel_edges(StandardScaler().fit_transform(z_eval))
    dense = DENSE_CACHE.setdefault(scn, DenseTruth(sc, seed=5))
    s_pool = physics_score(u_pool)
    z_pool_std = StandardScaler().fit_transform(z_pool)
    order = maximin_order(z_pool, np.random.default_rng([13, int(sigma * 10), n_pool, rep, 2]))
    prng = np.random.default_rng([13, int(sigma * 10), n_pool, rep, 3, POLICIES.index(policy)])
    revealed = list(order[:8])
    k = 8
    while len(set(y_pool[revealed])) < 2 and k < n_pool:
        revealed.append(int(order[k]))
        k += 1
    discovery = len(revealed)
    rows = []
    model = Model(model_kind, hyp, sc)
    base = {"scenario": scn, "sigma": sigma, "n_pool": n_pool, "rep": rep, "policy": policy, "model": model_kind,
            "discovery_cost": discovery, "pool_minority": int((y_pool == minority).sum()), "minority": minority}
    # paid startup budgets before both classes are observed: constant prediction of the observed class
    for b in range(8, min(discovery, HORIZON + 1)):
        obs = int(y_pool[revealed[0]])
        r = {**base, "budget": b, "labeled_minority": int((y_pool[revealed[:b]] == minority).sum()), "startup_constant": True}
        r.update(finite_metrics(y_eval, np.full(len(y_eval), obs), q, edges, minority))
        if b in DENSE_BUDGETS:
            r.update(dense.metrics(np.full(len(dense.y), obs)))
        rows.append(r)
    for b in range(discovery, HORIZON + 1):
        if b > len(revealed):
            cands = np.setdiff1d(np.arange(n_pool), revealed)
            if policy == "random":
                nxt = int(prng.choice(cands))
            elif policy == "maximin":
                nxt = int([o for o in order if o not in set(revealed)][0])
            else:
                p = model.proba(z_pool, u_pool)
                nxt = None
                if policy == "coverage" and len(revealed) < 40:
                    nxt = coverage_choice(cands, p, s_pool, s_pool[revealed], y_pool[revealed], z_pool_std, revealed)
                if nxt is None:
                    m = np.abs(p[cands] - .5)
                    nxt = int(cands[np.flatnonzero(m == m.min())[0]])
            revealed.append(nxt)
        rev = np.asarray(revealed[:b])
        model.fit(z_pool[rev], u_pool[rev], y_pool[rev])
        yhat = (model.latent(z_eval, u_eval) > 0).astype(int)
        r = {**base, "budget": b, "labeled_minority": int((y_pool[rev] == minority).sum()), "startup_constant": False}
        r.update(finite_metrics(y_eval, yhat, q, edges, minority))
        if b in DENSE_BUDGETS:
            r.update(dense.metrics((model.latent(dense.z, dense.u) > 0).astype(int)))
        rows.append(r)
    # ceiling: same model on the entire labelled pool (once per rep/model; stored with policy tag)
    if policy == "random":
        model.fit(z_pool, u_pool, y_pool)
        yhat = (model.latent(z_eval, u_eval) > 0).astype(int)
        r = {"scenario": scn, "sigma": sigma, "n_pool": n_pool, "rep": rep, "policy": "CEILING_full_pool", "model": model_kind,
             "budget": n_pool, "discovery_cost": 0, "labeled_minority": int((y_pool == minority).sum()),
             "pool_minority": int((y_pool == minority).sum()), "minority": minority}
        r.update(finite_metrics(y_eval, yhat, q, edges, minority))
        r.update(dense.metrics((model.latent(dense.z, dense.u) > 0).astype(int)))
        rows.append(r)
        # constant-majority reference on the same evaluation pool
        maj = 1 - minority
        r = {"scenario": scn, "sigma": sigma, "n_pool": n_pool, "rep": rep, "policy": "CONSTANT_majority", "model": "none",
             "budget": 0, "minority": minority}
        r.update(finite_metrics(y_eval, np.full(len(y_eval), maj), q, edges, minority))
        r.update(dense.metrics(np.full(len(dense.y), maj)))
        rows.append(r)
    pd.DataFrame(rows).to_parquet(dest, index=False)
    return str(dest)


DENSE_CACHE: dict = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=30)
    ap.add_argument("--jobs", type=int, default=7)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    paths_dir = OUT / ("paths_smoke" if a.smoke else "paths")
    paths_dir.mkdir(exist_ok=True)
    hyp_file = OUT / "oracle_hyperparameters.json"
    if hyp_file.exists():
        hyp = json.loads(hyp_file.read_text())
    else:
        hyp = {f"{s}_s{g}": oracle_hypers(calibrated(s), g) for s in SCENARIOS for g in SIGMAS}
        hyp_file.write_text(json.dumps(hyp, indent=2))
    jobs = [(s, g, n, r, p, m) for r in range(a.reps) for s in SCENARIOS for g in SIGMAS for n in (108, 324) for p in POLICIES for m in MODELS]
    if a.smoke:
        jobs = [j for j in jobs if j[3] == 0 and j[2] == 108]
    Parallel(n_jobs=a.jobs, verbose=5)(delayed(run_path)(s, g, n, r, p, m, hyp[f"{s}_s{g}"], paths_dir) for s, g, n, r, p, m in jobs)


if __name__ == "__main__":
    main()
