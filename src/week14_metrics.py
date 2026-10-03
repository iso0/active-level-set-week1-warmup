"""Week 14 metric additions (kept separate so that Week 13 sources stay byte-identical)."""
import numpy as np


def weighted_edge_metrics(edges, z, y, yhat, power=None):
    """Density-corrected (length-weighted) boundary-edge metrics.

    On scale-adaptive graphs (Gabriel, kNN) a cut edge of length l represents ~ l^(d-1) of boundary
    area, so weighting cut edges by l^(d-1) approximates uniform surface measure instead of the
    sampling-density-weighted measure (Theorem E2).  ``power`` defaults to d - 1.
    """
    z = np.asarray(z, float)
    y = np.asarray(y, int)
    yhat = np.asarray(yhat, int)
    p = z.shape[1] - 1 if power is None else power
    w = np.linalg.norm(z[edges[:, 0]] - z[edges[:, 1]], axis=1) ** p
    true_cut = y[edges[:, 0]] != y[edges[:, 1]]
    pred_cut = yhat[edges[:, 0]] != yhat[edges[:, 1]]
    ok = (yhat[edges[:, 0]] == y[edges[:, 0]]) & (yhat[edges[:, 1]] == y[edges[:, 1]])
    wt = w[true_cut].sum()
    res = w[true_cut & ok].sum()
    denom = wt + w[pred_cut].sum()
    return {"wBER": float(res / wt) if wt > 0 else np.nan, "wBEF1": float(2 * res / denom) if denom > 0 else np.nan}
