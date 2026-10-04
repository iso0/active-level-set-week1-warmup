"""Week 15 density-corrected boundary Dice (DC-BD) for finite evaluation pools.

Definition.  Evaluation pool X_1..X_n with observed labels y and predicted labels ŷ.  r-graph
G_r = {(i,j): |X_i − X_j| < r}.  Importance weights w_ij = 1/(p̂(X_i) p̂(X_j)), p̂ a k-NN density
estimate.  With W_T = Σ_{cut by y} w, W_P = Σ_{cut by ŷ} w and W_B = Σ_{cut by both} w,

    DC-BD = 2 W_B / (W_T + W_P)          (0 for a constant predictor, 1 for ŷ = y or ŷ = 1 − y).

Equivalently 1 − DC-BD = W_err / (W_T + W_P) with W_err the weighted graph perimeter of the error set
{y ≠ ŷ} (Proposition B1).  Orientation-free, like NSD.

Proposition M1 (THEORY_WEEK15.md): with the true density in the weights, each W/n² is a U-statistic
converging a.s. to the corresponding pair integral under *Lebesgue* measure on the support, so DC-BD
estimates the boundary Dice of a uniform cloud at resolution r — the quantity the EBR acquisition
targets — independently of the sampling density; with a uniformly consistent p̂ bounded below the
plug-in estimator is consistent.  Weights are trimmed at their 95th percentile (fixed in development).
"""
from __future__ import annotations

import math

import numpy as np
from scipy.spatial import cKDTree
from scipy.special import gamma


def knn_density(z, k=None):
    n, d = z.shape
    k = k or max(5, int(round(math.sqrt(n))))
    r = cKDTree(z).query(z, k=k + 1)[0][:, k]
    vd = math.pi ** (d / 2) / gamma(d / 2 + 1)
    return k / (n * vd * np.maximum(r, 1e-12) ** d)


def r_graph_edges(z, r):
    pairs = cKDTree(z).query_pairs(r, output_type="ndarray")
    return pairs.astype(int).reshape(-1, 2)


def default_radius(z):
    """Twice the median 5-NN distance (fixed in development)."""
    return float(2 * np.median(cKDTree(z).query(z, k=6)[0][:, 5]))


def dc_boundary_dice(z, y, yhat, r=None, density=None, trim=.95, weighted=True):
    z = np.asarray(z, float)
    y, yhat = np.asarray(y, int), np.asarray(yhat, int)
    r = default_radius(z) if r is None else r
    e = r_graph_edges(z, r)
    if len(e) == 0:
        return {"DC_BD": np.nan, "W_T": 0.0}
    if weighted:
        p = knn_density(z) if density is None else np.asarray(density, float)
        w = 1.0 / (p[e[:, 0]] * p[e[:, 1]])
        if trim is not None:
            w = np.minimum(w, np.quantile(w, trim))
    else:
        w = np.ones(len(e))
    ct = y[e[:, 0]] != y[e[:, 1]]
    cp = yhat[e[:, 0]] != yhat[e[:, 1]]
    WT, WP, WB = w[ct].sum(), w[cp].sum(), w[ct & cp].sum()
    return {"DC_BD": float(2 * WB / (WT + WP)) if WT + WP > 0 else np.nan, "W_T": float(WT), "W_P": float(WP), "r": r}
