"""RC21 constructions on one paid state. ONE honest cross-fitted SHQ upstream fit per state (src.rc20_attr.cf, unchanged, K = 10)
feeds every classifier, so all constructions share identical upstream fits, folds, normalisation, quality weights and paths:
  SHQ_ATS_H  RC20 candidate: L2 logistic (C = 1) on out-of-fold (log A, T, S) + exact log h (src.rc20_attr.clf, unchanged);
  SHQ_ATS_X  RC20 generic-input control: the same classifier with the 4 exact standardised log inputs instead of log h;
  PHR, PHR_NR, PHR_FX, PHR_FXMAP, PHR_NRMAP  the RC21 hierarchical Laplace construction and its by-products (src.rc21_phr).
One-class rule of RC19: the paid class rate until both classes are revealed among the usable paid runs.
"""
from __future__ import annotations

import warnings

import numpy as np

import src.rc20_attr as A
import src.rc21_phr as PH

ALL = ("SHQ_ATS_H", "SHQ_ATS_X", "PHR", "PHR_NR", "PHR_FX", "PHR_FXMAP", "PHR_NRMAP")


def state(task, rev, Z, rows, which=ALL):
    """Probabilities at `rows` for every requested construction, plus diagnostics. Learned from paid runs only."""
    y_p = rev.paid_y(); A_p = rev.paid_A(); L = rev.paid; y = y_p[L]; usable = np.isfinite(A_p[L])
    if len(set(y_p[L][usable].tolist())) < 2:
        return {k: np.full(len(rows), float(np.mean(y))) for k in which}, {"one_class": True}
    h = A.hcol(task); out = {}; info = {"one_class": False}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        R = A.cf(Z, rev, A.ATS, "SHQ", rows, A.KF); info["K"] = R["K"]; info["fallbacks"] = R["fallbacks"]
        if "SHQ_ATS_H" in which:
            p, g, _, _ = A.clf(R["F"], y, R["E"], h[L][:, None], h[rows][:, None]); out["SHQ_ATS_H"] = p; info["coef_H"] = g.coef_[0].tolist()
        if "SHQ_ATS_X" in which:
            out["SHQ_ATS_X"] = A.clf(R["F"], y, R["E"], Z[L], Z[rows])[0]
        if set(which) & {"PHR", "PHR_NR", "PHR_FX", "PHR_FXMAP", "PHR_NRMAP"}:
            U, _ = PH.transverse(task, Z)
            ph, info["phr"] = PH.fit_predict(R["F"], h[L], U[L], y, R["E"], h[rows], U[rows])
            out.update({k: v for k, v in ph.items() if k in which})
    return out, info
