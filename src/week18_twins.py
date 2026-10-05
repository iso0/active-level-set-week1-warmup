"""Week 18 semi-synthetic digital twins (S1) and stress worlds (S2).

Twin space: z = (g(x) − lo)/(hi − lo), g(x) = (log P, log VX, log LS, ST), lo/hi = pooled real min/max.
Truth surfaces fitted once to all 541 pooled real labels (SEMI-SYNTHETIC):
  T_GP   latent mean of a G3-type GPC (safeguarded Laplace, ML-II) on z
  T_GBT  gradient-boosted trees (300 × depth 3, lr 0.05) decision function on z (piecewise constant)
  T_NW   Nadaraya–Watson Gaussian smoother of labels on z, bandwidth by leave-one-out log loss; f = logit p̂
  T_QL   L2 logistic regression on degree-2 polynomial features of z (C = 1) (smooth global, physics-like)
  T_DEPTH GP regression of log max depth on OLD (z), f = μ − log 111 µm; continuous depth exp(μ) observable
Input distributions: Gaussian KDE (bandwidth 0.04 in z) around the pooled / OLD-only / NEW-only real points,
clipped to [0, 1].  Labels y = 1[f(z) > 0] (deterministic).  Truth for NSD/ASSD: 6,000 points of the task's
input distribution.  Seeds: truths fixed; pools [1823, twin, dist, size, rep]; dense [1823, twin, dist, 999].
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.special import expit, logit

from src.week15_al import DenseEval

ROOT = Path(__file__).resolve().parents[1]
TWINS = ("T_GP", "T_GBT", "T_NW", "T_QL", "T_DEPTH")
DISTS = ("pooled", "OLD", "NEW")


@lru_cache(None)
def real():
    from src.week18_tasks import pooled_frame
    D = pooled_frame()
    G = np.c_[np.log(D.P), np.log(D.VX), np.log(D.LS), D.ST]
    lo, hi = G.min(0), G.max(0)
    return D, G, lo, hi


def to_z(X):
    _, _, lo, hi = real()
    G = np.c_[np.log(X[:, 0]), np.log(X[:, 1]), np.log(X[:, 2]), X[:, 3]]
    return (G - lo) / (hi - lo)


def to_x(Z):
    _, _, lo, hi = real()
    G = lo + np.asarray(Z) * (hi - lo)
    return np.c_[np.exp(G[:, 0]), np.exp(G[:, 1]), np.exp(G[:, 2]), G[:, 3]]


@lru_cache(None)
def truth(name):
    D, G, lo, hi = real()
    Z = (G - lo) / (hi - lo); y = D.y.to_numpy(int)
    if name == "T_GP":
        import src.week17_models as M
        from src.week17_audit_impact import SafeguardedFixedMeanLaplaceGPC
        gp = SafeguardedFixedMeanLaplaceGPC(M.matern_ard(M.AMP), optimize=True).fit(Z, y, np.zeros(len(y)))
        return lambda z: gp.latent_mean_and_variance(np.asarray(z), np.zeros(len(z)))[0]
    if name == "T_GBT":
        from sklearn.ensemble import GradientBoostingClassifier
        g = GradientBoostingClassifier(n_estimators=300, max_depth=3, learning_rate=.05, random_state=0).fit(Z, y)
        return lambda z: g.decision_function(np.asarray(z))
    if name == "T_NW":
        from scipy.spatial.distance import cdist
        best = None
        for h in (.02, .03, .04, .06, .08, .12):
            K = np.exp(-cdist(Z, Z, "sqeuclidean") / (2 * h * h)); np.fill_diagonal(K, 0)
            p = np.clip((K @ y + .5) / (K.sum(1) + 1), 1e-4, 1 - 1e-4)
            ll = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
            if best is None or ll < best[0]:
                best = (ll, h)
        h = best[1]
        def f(z):
            K = np.exp(-cdist(np.asarray(z), Z, "sqeuclidean") / (2 * h * h))
            return logit(np.clip((K @ y + .5) / (K.sum(1) + 1), 1e-6, 1 - 1e-6))
        f.bandwidth = h
        return f
    if name == "T_QL":
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import PolynomialFeatures
        pf = PolynomialFeatures(2); lr = LogisticRegression(C=1.0, max_iter=5000).fit(pf.fit_transform(Z), y)
        return lambda z: lr.decision_function(pf.transform(np.asarray(z)))
    if name == "T_DEPTH":
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
        import pandas as pd
        pop = pd.read_csv(ROOT / "outputs/week7_06_real_data_boundary_active_level_set/primary_common_population.csv", usecols=["experiment_name", "max_depth_um"])
        o = D[D.campaign == 0]; dep = o.sim_id.map(dict(zip(pop.experiment_name, pop.max_depth_um))).to_numpy(float)
        Zo = Z[D.campaign.to_numpy() == 0]; t = np.log(dep)
        k = ConstantKernel(1.0, (1e-3, 1e3)) * Matern(np.ones(4), (1e-2, 1e2), nu=1.5) + WhiteKernel(1e-2, (1e-6, 1))
        g = GaussianProcessRegressor(k, n_restarts_optimizer=0, random_state=0).fit(Zo, t - t.mean()); m0 = t.mean()
        def f(z):
            return g.predict(np.asarray(z)) + m0 - np.log(111.0)
        f.depth = lambda z: np.exp(g.predict(np.asarray(z)) + m0)
        return f
    raise ValueError(name)


def sample(dist, n, rng, h=.04):
    D, G, lo, hi = real()
    Z = (G - lo) / (hi - lo)
    base = Z if dist == "pooled" else Z[D.campaign.to_numpy() == (0 if dist == "OLD" else 1)]
    pick = base[rng.integers(len(base), size=n)]
    return np.clip(pick + h * rng.standard_normal(pick.shape), 0, 1)


def twin_task(twin, dist, pool_size, rep, test_size=None):
    f = truth(twin)
    ti, di = TWINS.index(twin), DISTS.index(dist)
    rng = np.random.default_rng([1823, ti, di, pool_size, rep])
    test_size = test_size or max(28, pool_size // 4)
    zp, zt = sample(dist, pool_size, rng), sample(dist, test_size, rng)
    zd = sample(dist, 6000, np.random.default_rng([1823, ti, di, 999]))
    Z = np.r_[zp, zt]; y = (f(Z) > 0).astype(int)
    X = to_x(Z)
    depth = f.depth(Z) if twin == "T_DEPTH" else np.full(len(Z), np.nan)
    from src.external_validation.analysis import boundary_flags
    te = np.arange(pool_size, pool_size + test_size)
    q = boundary_flags(X, y, te, np.array([f"t{i:05d}" for i in range(len(y))]), "entire_evaluation_batch")[20] if len(set(y[te])) == 2 else None
    yd = (f(zd) > 0).astype(int)
    return {"task": f"S1_{twin}_{dist}_{pool_size}", "repeat": rep, "fold": 0, "block": "DEV" if rep < 8 else f"C{(rep - 8) // 4 + 1}",
            "X": X, "y": y, "depth": depth, "pool": np.arange(pool_size), "test": te, "prior": np.array([], int), "q20": q,
            "seed": [1824, ti, di, pool_size, rep], "dense_X": to_x(zd), "dense": DenseEval(zd, yd), "z_of": to_z}


def twin_fidelity():
    """Agreement of each truth with the real labels and its prevalence under each input distribution."""
    D, G, lo, hi = real()
    Z = (G - lo) / (hi - lo); y = D.y.to_numpy(int)
    out = {}
    for t in TWINS:
        f = truth(t)
        if t == "T_DEPTH":
            m = D.campaign.to_numpy() == 0
            out[t] = {"agree_real": float(np.mean((f(Z[m]) > 0) == y[m])), "scope": "OLD"}
        else:
            out[t] = {"agree_real": float(np.mean((f(Z) > 0) == y)), "scope": "pooled"}
        for d in DISTS:
            out[t][f"prev_{d}"] = float(np.mean(f(sample(d, 4000, np.random.default_rng(5))) > 0))
    return out
