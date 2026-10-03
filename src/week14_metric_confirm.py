"""Week 14 Study 3 confirmatory (held-out shapes/densities) — run only after the freeze.

Shapes never used in development: sphere boundary (d = 3, 6) and a two-component boundary (d = 3).
Densities: uniform, side-concentrated (two mirror versions), clustered operating windows.
Predictors: radial displacement, sector-localized displacement (two mirror sectors with equal
geometry), spurious island, smooth random perturbation, constant.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.spatial import cKDTree
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler

from src.week13_boundary_metrics import edge_metrics, gabriel_edges, knn_edges, nearest_opposite
from src.week14_metrics import weighted_edge_metrics

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week14_research_program/benchmarks/metrics_confirm"
C = .5


_RADIUS = {}


def sphere_radius(d):
    """Radius giving a 10% uniform-volume minority ball centred in the unit cube (fixed before results)."""
    if d not in _RADIUS:
        u = np.random.default_rng(123).random((200000, d))
        _RADIUS[d] = float(np.quantile(np.linalg.norm(u - C, axis=1), .10))
    return _RADIUS[d]


def f_true(u, shape):
    if shape == "sphere":
        return np.linalg.norm(u - C, axis=1) - sphere_radius(u.shape[1])   # minority (class 0) inside
    if shape == "twocomp":
        a = np.linalg.norm(u - np.r_[.3, .3, np.full(u.shape[1] - 2, .5)], axis=1) - .18
        b = np.linalg.norm(u - np.r_[.7, .65, np.full(u.shape[1] - 2, .5)], axis=1) - .15
        return np.minimum(a, b)
    raise ValueError(shape)


def predictor(u, shape, kind, amt, rng_seed=0):
    f = f_true(u, shape)
    if kind == "displace":
        return (f + amt > 0).astype(int)
    if kind == "sectorA":
        return (f + amt * (u[:, 0] < C) > 0).astype(int)
    if kind == "sectorB":
        return (f + amt * (u[:, 0] >= C) > 0).astype(int)
    if kind == "island":
        return ((f > 0) & ~(np.linalg.norm(u - np.r_[.92, .08, np.full(u.shape[1] - 2, .5)], axis=1) < amt)).astype(int)
    if kind == "perturb":
        r = np.random.default_rng(rng_seed)
        W = r.standard_normal((u.shape[1], 6)) * 6
        b = r.uniform(0, 2 * np.pi, 6)
        return (f + amt * np.sin(u @ W + b).mean(1) > 0).astype(int)
    if kind == "constant":
        return np.ones(len(u), int)
    raise ValueError(kind)


def sample(n, d, shape, density, rng):
    u = rng.random((n, d))
    if density == "uniform":
        return u
    if density == "clustered":
        c = rng.random((3, d))
        k = rng.integers(3, size=n)
        return np.clip(c[k] + .15 * rng.standard_normal((n, d)), 0, 1)
    # side-concentrated: half the points near the boundary on one side of u0 = C
    m = n // 2
    cand = rng.random((20 * m, d))
    side = cand[:, 0] < C if density == "denseA" else cand[:, 0] >= C
    near = np.abs(f_true(cand, shape)) < .05
    pick = cand[side & near][:m]
    u[:len(pick)] = pick
    return u


class Truth:
    def __init__(self, d, shape, n=40000, k=10):
        r = np.random.default_rng(3)
        self.u = r.random((n, d))
        self.y = (f_true(self.u, shape) > 0).astype(int)
        _, nn = cKDTree(self.u).query(self.u, k=k + 1)
        self.nn = nn[:, 1:]
        self.tb = (self.y[self.nn] != self.y[:, None]).any(1)
        self.tree = cKDTree(self.u[self.tb])
        self.tau = .03 * math.sqrt(d)

    def metrics(self, yhat):
        pb = (yhat[self.nn] != yhat[:, None]).any(1)
        if not pb.any():
            return {"NSD": 0.0, "ASSD": math.sqrt(self.u.shape[1])}
        a = cKDTree(self.u[pb]).query(self.u[self.tb])[0]
        b = self.tree.query(self.u[pb])[0]
        return {"NSD": float(((a <= self.tau).sum() + (b <= self.tau).sum()) / (len(a) + len(b))),
                "ASSD": float((a.sum() + b.sum()) / (len(a) + len(b)))}


PREDS = ([("displace", a) for a in (-.06, -.03, -.015, 0, .015, .03, .06)] + [("sectorA", a) for a in (.03, .06)] +
         [("sectorB", a) for a in (.03, .06)] + [("island", a) for a in (.05, .1)] +
         [("perturb", a) for a in (.02, .05, .1)] + [("constant", 0)])


def cell(d, shape, density, noise, n, rep, tm):
    rng = np.random.default_rng([15, d, ("sphere", "twocomp").index(shape), ("uniform", "denseA", "denseB", "clustered").index(density), int(noise * 100), n, rep])
    u = sample(n, d, shape, density, rng)
    y = (f_true(u, shape) + noise * rng.standard_normal(n) > 0).astype(int)
    if y.min() == y.max():
        return [{"d": d, "shape": shape, "density": density, "noise": noise, "n": n, "rep": rep, "pred": "SKIPPED_single_class"}]
    z = StandardScaler().fit_transform(u)
    dist, _ = nearest_opposite(z, y)
    q = np.zeros(n, bool); q[np.argsort(dist, kind="stable")[:math.ceil(.2 * n)]] = True
    graphs = {"gabriel": gabriel_edges(z), "knn5": knn_edges(z, 5)}
    rows = []
    for k, a in PREDS:
        yh = predictor(u, shape, k, a)
        r = {"d": d, "shape": shape, "density": density, "noise": noise, "n": n, "rep": rep, "pred": k, "amount": a,
             "minority_share": float(min(y.mean(), 1 - y.mean())),
             "q20_accuracy": float(np.mean(yh[q] == y[q])),
             "q20_BA": float(np.nanmean([np.mean(yh[q & (y == c)] == c) if (q & (y == c)).any() else np.nan for c in (0, 1)])),
             "full_BA": float((np.mean(yh[y == 1] == 1) + np.mean(yh[y == 0] == 0)) / 2), **tm[(k, a)]}
        for g, e in graphs.items():
            m = edge_metrics(e, y, yh)
            w = weighted_edge_metrics(e, z, y, yh)
            r.update({f"{g}_BER": m["BER"], f"{g}_BEF1": m["BEF1"], f"{g}_wBER": w["wBER"], f"{g}_wBEF1": w["wBEF1"]})
        rows.append(r)
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    configs = [(3, "sphere"), (6, "sphere"), (3, "twocomp")]
    allrows = []
    for d, shape in configs:
        truth = Truth(d, shape)
        tm = {(k, a): truth.metrics(predictor(truth.u, shape, k, a)) for k, a in PREDS}
        jobs = [(d, shape, den, noise, n, rep) for den in ("uniform", "denseA", "denseB", "clustered")
                for noise in (0.0, .02) for n in (136, 405) for rep in range(30)]
        res = Parallel(n_jobs=7)(delayed(cell)(*j, tm) for j in jobs)
        allrows += [x for rows in res for x in rows]
    df = pd.DataFrame(allrows)
    df.to_csv(OUT / "metric_confirm.csv.gz", index=False)
    fin = ["q20_accuracy", "q20_BA", "full_BA", "gabriel_BER", "gabriel_BEF1", "gabriel_wBER", "gabriel_wBEF1",
           "knn5_BER", "knn5_BEF1", "knn5_wBER", "knn5_wBEF1"]
    # (1) density sensitivity for equal-geometry sector errors
    sec = df[df.pred.isin(["sectorA", "sectorB"]) & df.density.isin(["denseA", "denseB"])]
    piv = sec.groupby(["d", "shape", "density", "noise", "n", "amount", "pred"])[fin + ["NSD"]].mean()
    sens = (piv.xs("sectorA", level="pred") - piv.xs("sectorB", level="pred")).abs()
    sens.to_csv(OUT / "density_sensitivity.csv")
    # (2) Spearman agreement with NSD and ASSD across all predictors within each pool
    agree = []
    for key, g in df.groupby(["d", "shape", "density", "noise", "n", "rep"]):
        for c in fin:
            agree.append({**dict(zip(["d", "shape", "density", "noise", "n", "rep"], key)), "metric": c,
                          "rho_NSD": spearmanr(g[c], g.NSD).statistic, "rho_negASSD": spearmanr(g[c], -g.ASSD).statistic})
    A = pd.DataFrame(agree)
    A.to_csv(OUT / "rank_agreement.csv", index=False)
    pd.set_option("display.width", 250)
    print(sens.groupby(["d", "shape", "density"]).mean().round(3).to_string())
    print(A.groupby(["shape", "d", "density", "metric"]).rho_negASSD.mean().unstack().round(3).to_string())


if __name__ == "__main__":
    main()
