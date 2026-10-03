"""Week 13 finite-pool boundary metrics (EXPLORATORY / METHODOLOGICAL).

Definitions are fixed here before they are applied to any real active-learning
predictions.  They complement, and never replace, the historical q20 endpoint.

Graph-based boundary metrics
----------------------------
Let X be an evaluation pool (standardized over the whole evaluation batch, the
same scaling scope as the historical q20 construction) and let G be its Gabriel
graph: (i, j) is an edge iff no other pool point lies strictly inside the ball
with diameter [x_i, x_j], i.e. iff d_ik^2 + d_jk^2 >= d_ij^2 for every k.  The
Gabriel graph is parameter free and contains the Euclidean minimum spanning
tree, so it is connected.

The *true cut set* is E* = {(i, j) in G : y_i != y_j}; the true level set
crosses every such edge an odd number of times.  For hard predictions yhat the
*predicted cut set* is Ehat = {(i, j) in G : yhat_i != yhat_j}.

* BER  (boundary-edge recovery)      = |{e in E*: yhat agrees with y at both ends}| / |E*|
* BEBA (boundary-edge balanced acc.) = mean over e in E* of the average endpoint correctness
* BEF1 (boundary-edge F1)            = 2 |E* ∩_oriented Ehat| / (|E*| + |Ehat|)

A constant predictor has BER = 0, BEBA = 0.5 and BEF1 = 0, whatever the class
prevalence: every cut edge has exactly one endpoint of each class.  BEF1 also
penalises spurious predicted boundaries anywhere in the pool, which no
band-restricted accuracy can do.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import distance
from sklearn.preprocessing import StandardScaler


def standardize(x):
    return StandardScaler().fit_transform(np.asarray(x, float))


def gabriel_edges(z, chunk=64):
    """Return an (m, 2) int array of Gabriel-graph edges (i < j)."""
    z = np.asarray(z, float)
    d2 = distance.cdist(z, z, "sqeuclidean")
    n = len(z)
    edges = []
    for start in range(0, n, chunk):
        rows = np.arange(start, min(n, start + chunk))
        # s[a, j, k] = d2[i_a, k] + d2[j, k]; edge iff s >= d2[i_a, j] for all k != i, j
        s = d2[rows][:, None, :] + d2[None, :, :]
        lhs = s >= d2[rows][:, :, None] - 1e-12
        # k == i or k == j trivially satisfy the inequality (equality), so no masking is needed
        ok = lhs.all(axis=2)
        for a, i in enumerate(rows):
            js = np.nonzero(ok[a])[0]
            js = js[js > i]
            edges.extend((int(i), int(j)) for j in js)
    return np.asarray(edges, int).reshape(-1, 2)


def knn_edges(z, k):
    """Symmetrised k-nearest-neighbour graph (union), sensitivity analysis only."""
    d = distance.cdist(z, z)
    np.fill_diagonal(d, np.inf)
    nn = np.argsort(d, axis=1)[:, :k]
    e = {(min(i, j), max(i, j)) for i in range(len(z)) for j in nn[i]}
    return np.asarray(sorted(e), int).reshape(-1, 2)


def cut_edges(edges, y):
    y = np.asarray(y, int)
    return edges[y[edges[:, 0]] != y[edges[:, 1]]]


def edge_metrics(edges, y, yhat):
    """Graph boundary metrics for hard predictions on the full pool."""
    y = np.asarray(y, int)
    yhat = np.asarray(yhat, int)
    true_cut = y[edges[:, 0]] != y[edges[:, 1]]
    pred_cut = yhat[edges[:, 0]] != yhat[edges[:, 1]]
    ok0 = yhat[edges[:, 0]] == y[edges[:, 0]]
    ok1 = yhat[edges[:, 1]] == y[edges[:, 1]]
    n_true = int(true_cut.sum())
    resolved = true_cut & ok0 & ok1
    out = {"n_true_cut": n_true, "n_pred_cut": int(pred_cut.sum()),
           "BER": float(resolved.sum() / n_true) if n_true else np.nan,
           "BEBA": float(((ok0 + ok1.astype(float)) / 2)[true_cut].mean()) if n_true else np.nan}
    denom = n_true + int(pred_cut.sum())
    out["BEF1"] = float(2 * resolved.sum() / denom) if denom else np.nan
    out["spurious_cut"] = int((pred_cut & ~true_cut).sum())
    return out


def band_decomposition(y, yhat, minority):
    """Counts behind the identity acc - acc(always-majority) = (correct minority - wrong minority calls)/n."""
    y = np.asarray(y, int)
    yhat = np.asarray(yhat, int)
    call = yhat == minority
    return {"n": len(y), "n_minority": int((y == minority).sum()),
            "minority_calls": int(call.sum()),
            "correct_minority_calls": int((call & (y == minority)).sum()),
            "wrong_minority_calls": int((call & (y != minority)).sum())}


def nearest_opposite(z, y):
    d = distance.cdist(z, z)
    opp = np.asarray(y)[:, None] != np.asarray(y)[None, :]
    dm = np.where(opp, d, np.inf)
    return dm.min(axis=1), dm.argmin(axis=1)
