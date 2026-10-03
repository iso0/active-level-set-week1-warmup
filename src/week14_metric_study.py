"""Week 14 Study 3 — what do finite-pool boundary metrics measure? (CONTROLLED SYNTHETIC)

Tests consequences of Theorem E2 with a known boundary:
  * localized-error predictors (error on boundary part L or part R) scored under three evaluation
    densities (uniform, concentrated near part L, near part R)  -> density-induced rank reversal?
  * graph construction (Gabriel, kNN-5, r-graph with r = median 5-NN distance)
  * label noise attenuation, sub-resolution displacement, spurious far islands
Truth: NSD (uniform surface measure, tolerance tau) and ASSD on a dense grid-free sample.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from scipy.spatial.distance import cdist
from sklearn.preprocessing import StandardScaler

from src.week13_boundary_metrics import edge_metrics, gabriel_edges, knn_edges, nearest_opposite

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week14_research_program/synthetic/metrics"


def f_true(u):
    # curved boundary: class 1 above a parabola-like surface in the first two coordinates
    return u[:, 1] - (.35 + .3 * (u[:, 0] - .5) ** 2 + .05 * np.sin(6 * u[:, 0]))


def predictor(u, kind, amt):
    f = f_true(u)
    if kind == "displace":
        return (f + amt > 0).astype(int)
    if kind == "left_error":       # boundary displaced by amt only where u0 < .5
        return (f + amt * (u[:, 0] < .5) > 0).astype(int)
    if kind == "right_error":
        return (f + amt * (u[:, 0] >= .5) > 0).astype(int)
    if kind == "island":           # spurious class-0 island far from the boundary
        isl = np.linalg.norm(u[:, :2] - np.array([.5, .9]), axis=1) < amt
        return ((f > 0) & ~isl).astype(int)
    if kind == "constant":
        return np.ones(len(u), int)
    raise ValueError(kind)


def sample(n, d, density, rng):
    if density == "uniform":
        return rng.random((n, d))
    # mixture: 50% uniform, 50% concentrated near the boundary on one side of u0
    k = rng.random(n) < .5
    u = rng.random((n, d))
    m = (~k).sum()
    x0 = rng.uniform(0, .5, m) if density == "dense_left" else rng.uniform(.5, 1, m)
    y0 = .35 + .3 * (x0 - .5) ** 2 + .05 * np.sin(6 * x0) + .06 * rng.standard_normal(m)
    u[~k, 0], u[~k, 1] = x0, np.clip(y0, 0, 1)
    return u


class Truth:
    def __init__(self, d, n=40000, k=10):
        rng = np.random.default_rng(3)
        self.u = rng.random((n, d))
        self.y = (f_true(self.u) > 0).astype(int)
        _, nn = cKDTree(self.u).query(self.u, k=k + 1)
        self.nn = nn[:, 1:]
        self.tb = (self.y[self.nn] != self.y[:, None]).any(1)
        self.tree = cKDTree(self.u[self.tb])

    def metrics(self, yhat, tau=.03):
        pb = (yhat[self.nn] != yhat[:, None]).any(1)
        if not pb.any():
            return {"NSD": 0.0, "ASSD": math.sqrt(self.u.shape[1])}
        a = cKDTree(self.u[pb]).query(self.u[self.tb])[0]
        b = self.tree.query(self.u[pb])[0]
        return {"NSD": float(((a <= tau).sum() + (b <= tau).sum()) / (len(a) + len(b))),
                "ASSD": float((a.sum() + b.sum()) / (len(a) + len(b)))}


def r_graph(z, r):
    d = cdist(z, z)
    i, j = np.nonzero(np.triu(d < r, 1))
    return np.c_[i, j]


def pool_structures(u, y):
    z = StandardScaler().fit_transform(u)
    dist, _ = nearest_opposite(z, y)
    q = np.zeros(len(y), bool)
    q[np.argsort(dist, kind="stable")[:math.ceil(.2 * len(y))]] = True
    k5 = cKDTree(z).query(z, k=6)[0][:, 5]
    graphs = {"gabriel": gabriel_edges(z), "knn5": knn_edges(z, 5), "rgraph": r_graph(z, float(np.median(k5)))}
    return q, graphs


def finite(y, yhat, q, graphs):
    out = {"q20_accuracy": float(np.mean(yhat[q] == y[q])),
           "full_BA": float((np.mean(yhat[y == 1] == 1) + np.mean(yhat[y == 0] == 0)) / 2)}
    for g, e in graphs.items():
        m = edge_metrics(e, y, yhat)
        out[f"{g}_BER"], out[f"{g}_BEF1"] = m["BER"], m["BEF1"]
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    preds = [("displace", a) for a in (-.08, -.04, -.02, -.01, 0, .01, .02, .04, .08)] + \
            [("left_error", a) for a in (.02, .05, .1)] + [("right_error", a) for a in (.02, .05, .1)] + \
            [("island", a) for a in (.03, .06, .1)] + [("constant", 0)]
    for d in (2, 4):
        truth = Truth(d)
        tm = {(k, a): truth.metrics(predictor(truth.u, k, a)) for k, a in preds}
        for density in ("uniform", "dense_left", "dense_right"):
            for noise in (0.0, .02):
                for n in (136, 405):
                    for rep in range(30):
                        rng = np.random.default_rng([7, d, ("uniform", "dense_left", "dense_right").index(density), int(noise * 100), n, rep])
                        u = sample(n, d, density, rng)
                        y = (f_true(u) + noise * rng.standard_normal(n) > 0).astype(int)
                        if y.min() == y.max():
                            continue
                        q, graphs = pool_structures(u, y)
                        for k, a in preds:
                            r = {"d": d, "density": density, "noise": noise, "n": n, "rep": rep, "pred": k, "amount": a,
                                 "prevalence_class0": float(1 - y.mean())}
                            r.update(finite(y, predictor(u, k, a), q, graphs))
                            r.update(tm[(k, a)])
                            rows.append(r)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "metric_study.csv.gz", index=False)
    print(df.groupby(["d", "density", "noise", "pred", "amount"])[["q20_accuracy", "full_BA", "gabriel_BER", "knn5_BER", "rgraph_BER", "gabriel_BEF1", "NSD"]].mean().round(3).to_string())


if __name__ == "__main__":
    main()
