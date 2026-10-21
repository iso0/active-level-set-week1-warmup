"""RC24 Stage B prototype P1 - PAC: physics-anchored composite classifier with an errors-in-variables depth covariate.

Observation contract: a query at x returns (y, a, q) from ONE simulation record: the label y, the log active maximum depth a (missing
for some records) and the record-quality flag q (record ended before 95 % of its planned end -> short). Public before the query: x and
z_h(x) = standardised log h, h = P / sqrt(VX LS^3).

Joint probability model (conditional on hyperparameters; every source of variance appears once):
  depth   a(x) = a*(x) + e(x),  a*(x) = mu + theta z_h(x) + g(x)        (standardised-target scale of the paid good records)
            g ~ GP(0, sf2 Matern-3/2 ARD on standardised log inputs)  - local deviations from the physics scaling law
            theta ~ N(0, b^2), b = 3 (FIXED, pre-registered)            - normalised-enthalpy scaling of melt depth; integrated out
                                                                          exactly (kernel term b^2 z_h z_h'), so trend uncertainty is
                                                                          part of the predictive variance
            e ~ N(0, sn2 w(q)), w = 1e4 for a short record              - measurement / record-quality noise (RC18 Q rule)
          hyperparameters (sf2, ARD lengthscales, sn2) by ML-II (src.rc18_gp.GP with H_cols = 1)
  label   P(y = 1 | x, a*) = sigmoid(eta),  eta = b0 + beta_h z~_h + beta_a a~*   (features standardised on the paid rows)
            the label responds to the PHYSICAL depth a* of the run, not to a prediction of it (structural model);
            b0 ~ N(0, 10^2), beta_h ~ N(0, tau_h^2), beta_a ~ N(0, tau_a^2), (tau_a, tau_h) on {0.5, 1, 2, 4}^2 weighted by the Laplace
            marginal likelihood; each configuration's weights are plugged in (MAP), as HA_LEAN / PHR_NRMAP
  independence  given a*(x), the label's logistic noise is independent of the depth noise e (stated assumption); h is exact.
Training covariate (paid run i): a~_i = E[a*(x_i) | all paid depths] - the posterior smoothing of the measured depths (~ the measured
  value for a complete record; a short record or a missing depth is estimated from the other runs through the GP). The covariate is a
  measurement, not a prediction, so no cross-fitting is needed and no prediction error enters the training covariate.
Prediction at an unqueried x: a*(x) | paid data ~ N(m(x), v(x)) (latent predictive including trend uncertainty);
  p_g(x) = E[sigmoid(m_g(z_h(x), a*))] over that Gaussian (m_g is affine in a*: exact 1-D integral, 32-node Gauss-Hermite);
  p(x) = sum_g w_g p_g(x).  For one configuration the 0.5 decision is the sign of m_g at m(x): the integration changes calibration and
  the margin ranking (an uncertainty-scaled margin), not the 0.5 decision.
Nesting: beta_a = 0 is the h-only classifier; beta_h = 0 with a sharp link is E1 (depth threshold integrated over the depth GP); stacking
  on honest out-of-fold predictions of a constant-mean emulator without integration is HA_LEAN (src.rc23_common).
Ablations on the same paid states:
  PAC_PLUG  PAC without integration (a* = m(x) plugged in)                         -> errors-in-variables integration
  PAC_FLAT  PAC with a constant-mean emulator (b = 0)                              -> the physics anchor
  PAC_GEN   PAC with a generic linear trend in all four standardised log inputs (b = 3 each) -> physics anchor vs any linear trend
  HA_TREND  HA_LEAN's honest K = 10 stacking with the physics-anchored emulator (plug-in) -> structural vs stacked training
  HA_TREND_B1 / HA_TREND_B10  HA_TREND with trend-prior SD b = 1 / 10 (prior-sensitivity controls; never candidates)
"""
from __future__ import annotations

import warnings

import numpy as np
from scipy.linalg import solve_triangular
from scipy.special import expit

import src.rc18_campaign as C18
import src.rc18_gp as G
import src.rc19_learn as LN
import src.rc19b_keyhole as K
import src.rc20_attr as A
import src.rc21_phr as PH
import src.rc22_common as C22

B_TREND = 3.0
GH_X, GH_W = np.polynomial.hermite_e.hermegauss(32)
GH_W = GH_W / GH_W.sum()
DEPTH_COL = LN.TI["log_A_um"]
PAC_CONS = ("PAC", "PAC_PLUG", "PAC_FLAT", "PAC_GEN", "HA_TREND")


def _basis(task, Z, kind):
    if kind == "phys":
        return A.hcol(task)[:, None]
    if kind == "gen":
        return np.asarray(Z, float)
    return None


def depth_fit(task, rev, Z, kind="phys", rows=None, b=None):
    """Depth GP on the paid depths (rows `rows` of the paid set, default all) with basis kind in {phys, gen, flat}; b = prior SD of the
    trend coefficient (default B_TREND = 3; 1 and 10 are sensitivity controls). None if < 3 good rows."""
    L = rev.paid if rows is None else np.asarray(rows); Y = rev.paid_Y()[:, DEPTH_COL]; W = np.where(rev.paid_short(), C18.W_SHORT, 1.0)
    Lu = L[np.isfinite(Y[L])]
    if (W[Lu] <= 100).sum() < 3:
        return None
    H = _basis(task, Z, kind)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        g = G.GP(H_cols=0 if H is None else H.shape[1], b=B_TREND if b is None else b).fit(Z[Lu], Y[Lu], H=None if H is None else H[Lu], w=W[Lu])
    return {"g": g, "H": H, "rows": Lu}


def depth_predict(fit, Z, idx):
    g, H = fit["g"], fit["H"]; m, lat, obs = g.predict(Z[idx], Hs=None if H is None else H[idx]); return m, lat


def lr_family(Xtr, y, Xev):
    """Learned-regularisation Laplace classifier on [z_h, feature] (src.rc22_common.phr_family's math, feats = (0,)), returning
    per-configuration plug-in latent means at Xev, weights, and the posterior mean coefficient of the standardised feature."""
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-12; Htr, Hev = (Xtr - mu) / sd, (Xev - mu) / sd; y = np.asarray(y, float)
    U0, U1 = np.zeros((len(Htr), 1)), np.zeros((len(Hev), 1)); Gtt = PH.Gram(Htr, Htr, U0, U0); Get = PH.Gram(Hev, Htr, U1, U0)
    kss_h = Hev[:, 0] ** 2; kss_F = np.sum(Hev[:, 1:] ** 2, 1); cfg = [(tf, th) for tf in PH.TAU_F for th in PH.TAU_H]
    logw = np.empty(len(cfg)); Mm = np.empty((len(cfg), len(Hev))); cA = np.empty(len(cfg))
    for g, (tf, th) in enumerate(cfg):
        mode = PH.laplace(Gtt.K(tf, th, 0.0, None), y); kss = PH.V0 + th ** 2 * kss_h + tf ** 2 * kss_F
        Mm[g], _, _ = PH.predictive(mode, Get.K(tf, th, 0.0, None), kss, plugin=True); logw[g] = mode["logZ"]; cA[g] = tf ** 2 * float(Htr[:, 1] @ mode["grad"])
    w = np.exp(logw - logw.max()); w /= w.sum()
    return {"w": w, "m": Mm, "cA": cA, "sd_F": float(sd[1]), "cfg": cfg}


def eiv_prob(fam, v):
    """sum_g w_g E[sigmoid(m_g + cA_g (a* - m) / sd_F)], a* ~ N(m, v) (exact affine latent; 32-node Gauss-Hermite)."""
    s = np.sqrt(np.maximum(v, 0.0)) / fam["sd_F"]; P = np.zeros(len(v))
    for g in range(len(fam["w"])):
        P += fam["w"][g] * (expit(fam["m"][g][:, None] + (fam["cA"][g] * s)[:, None] * GH_X[None, :]) @ GH_W)
    return P


def _honly(task, rev, rows):
    h = A.hcol(task); L = rev.paid; y = rev.paid_y()[L]
    return C22.phr_family(np.zeros((len(L), 1)), h[L], y, np.zeros((len(rows), 1)), h[rows], feats=())[0]


def state(task, rev, Z, rows, which=PAC_CONS):
    """Probabilities at rows for the requested PAC-family constructions; one-class rule = HA_LEAN's (usable depth labels)."""
    y_p = rev.paid_y(); A_p = rev.paid_A(); L = rev.paid; y = y_p[L]; usable = np.isfinite(A_p[L]); out, info = {}, {}
    if len(set(y_p[L][usable].tolist())) < 2:
        r = float(np.mean(y)); return {k: np.full(len(rows), r) for k in which}, {"one_class": True}
    h = A.hcol(task); info["one_class"] = False
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for nm, kind in (("PAC", "phys"), ("PAC_PLUG", "phys"), ("PAC_FLAT", "flat"), ("PAC_GEN", "gen")):
            if nm not in which:
                continue
            key = f"fit_{kind}"
            if key not in info:
                f = depth_fit(task, rev, Z, kind); info[key] = f
            f = info[key]
            if f is None:
                out[nm] = _honly(task, rev, rows); info[f"{nm}_fallback"] = "h-only (fewer than 3 good depths)"; continue
            mt, _ = depth_predict(f, Z, L); me, ve = depth_predict(f, Z, rows)
            fam = lr_family(np.c_[h[L], mt], y, np.c_[h[rows], me])
            out[nm] = fam["w"] @ expit(fam["m"]) if nm == "PAC_PLUG" else eiv_prob(fam, ve)
            info[f"{nm}_cA_mean"] = float(fam["w"] @ fam["cA"])
        for nm, bb in (("HA_TREND", None), ("HA_TREND_B1", 1.0), ("HA_TREND_B10", 10.0)):
            if nm in which:
                R = cf_phys(task, rev, Z, rows, b=bb)
                out[nm] = C22.phr_family(R["F"], h[L], y, R["E"], h[rows], feats=(0,))[0]; info[f"{nm}_fallbacks"] = R["fallbacks"]
    for k in [k for k in info if k.startswith("fit_")]:
        info.pop(k)
    return {k: out[k] for k in which}, info


def cf_phys(task, rev, Z, rows, Kf=A.KF, b=None):
    """Honest K-fold out-of-fold predicted log depth of the paid runs from the PHYSICS-ANCHORED emulator (fold of the j-th paid run =
    j mod K, as src.rc20_attr.cf; each fold's fit uses only the paid runs outside the fold) + the full fit's means at rows."""
    paid = rev.paid; Y = rev.paid_Y()[:, DEPTH_COL]; fold, k = K.folds(len(paid), Kf); F = np.full((len(paid), 1), np.nan); fb = 0
    for j in range(k):
        tr = paid[fold != j]; f = depth_fit(task, rev, Z, "phys", rows=tr, b=b)
        if f is None:
            v = Y[tr]; v = v[np.isfinite(v)]; F[fold == j, 0] = float(np.mean(v)) if len(v) else 0.0; fb += 1
        else:
            F[fold == j, 0] = depth_predict(f, Z, paid[fold == j])[0]
    full = depth_fit(task, rev, Z, "phys", b=b); E = depth_predict(full, Z, rows)[0][:, None] if full is not None else np.full((len(rows), 1), np.nanmean(Y[paid]))
    return {"F": F, "E": E, "fallbacks": fb}
