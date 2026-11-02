"""RC24 post-audit: CLEAN trend control for the stacked h + depth classifier (owner instruction 2026-10-22, section 3).

One architecture, one code path; ONLY the depth emulator's trend term changes:
  TR_NONE   a*(x) = mu + g(x)                                   (no trend)
  TR_PHYS   a*(x) = mu + theta z_h(x) + g(x),   theta ~ N(0, 3^2)               (physics direction; = RC24 HA_TREND exactly)
  TR_GEN3   a*(x) = mu + theta' z(x) + g(x),    theta_k ~ N(0, 3^2), k = 1..4   (generic log-input trend, same per-coefficient scale)
  TR_GEN15  as TR_GEN3 with theta_k ~ N(0, 1.5^2): the prior variance of the trend FUNCTION averaged over the pool equals TR_PHYS's
            (z = standardised log inputs, E||z||^2 = 4; z_h standardised, E z_h^2 = 1; 4 x 1.5^2 = 3^2)
Common to all four: the paid depth target log A with the RC18 record-quality noise (x 1e4 for short records), the Matern-3/2 ARD GP part
g with ML-II hyperparameters (src.rc18_gp via src.rc24_pac.depth_fit, unchanged), honest K = 10 out-of-fold features (fold = j mod K,
each fold fit without the fold), the full-fit mean at unpaid rows, the learned-regularisation Laplace classifier on [z_h, A_hat]
(src.rc22_common.phr_family, unchanged), the same normalisation, budgets and selector.
log h = log P - log VX / 2 - 3 log LS / 2 is a LINEAR combination of the log inputs, so TR_GEN contains TR_PHYS as the special case
theta = c d_h: the physics trend adds no information the inputs do not have; it is a structural constraint (one coefficient in one
fixed direction instead of four free ones).
HA_LEAN (src.rc23_common, RC23 D1) uses the SHQ fitting route (rc18_campaign.fit_model) for the same constant-mean model; TR_NONE is
its same-code-path twin here, and the difference between the two is reported as an implementation effect.
"""
from __future__ import annotations

import warnings

import numpy as np

import src.rc19b_keyhole as K
import src.rc20_attr as A
import src.rc22_common as C22
import src.rc24_pac as PC

TREND = {"TR_NONE": ("flat", None), "TR_PHYS": ("phys", 3.0), "TR_GEN3": ("gen", 3.0), "TR_GEN15": ("gen", 1.5)}


def cf_trend(task, rev, Z, rows, kind, b, Kf=A.KF):
    paid = rev.paid; Y = rev.paid_Y()[:, PC.DEPTH_COL]; fold, k = K.folds(len(paid), Kf); F = np.full((len(paid), 1), np.nan); fb = 0
    for j in range(k):
        tr = paid[fold != j]; f = PC.depth_fit(task, rev, Z, kind, rows=tr, b=b)
        if f is None:
            v = Y[tr]; v = v[np.isfinite(v)]; F[fold == j, 0] = float(np.mean(v)) if len(v) else 0.0; fb += 1
        else:
            F[fold == j, 0] = PC.depth_predict(f, Z, paid[fold == j])[0]
    full = PC.depth_fit(task, rev, Z, kind, b=b)
    E = PC.depth_predict(full, Z, rows)[0][:, None] if full is not None else np.full((len(rows), 1), np.nanmean(Y[paid]))
    return F, E, fb


def state(task, rev, Z, rows, which=tuple(TREND)):
    y_p = rev.paid_y(); A_p = rev.paid_A(); L = rev.paid; y = y_p[L]; usable = np.isfinite(A_p[L])
    if len(set(y_p[L][usable].tolist())) < 2:
        r = float(np.mean(y)); return {k: np.full(len(rows), r) for k in which}, {"one_class": True}
    h = A.hcol(task); out = {}; info = {"one_class": False}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for nm in which:
            kind, b = TREND[nm]; F, E, fb = cf_trend(task, rev, Z, rows, kind, b)
            out[nm] = C22.phr_family(F, h[L], y, E, h[rows], feats=(0,))[0]; info[f"{nm}_fallbacks"] = fb
    return out, info
