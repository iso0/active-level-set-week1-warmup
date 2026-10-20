"""RC20 constructions on one paid state: attribution (upstream emulator x classifier features), log-h variants and the
honest cross-fit remedy candidates. Everything is learned from the PAID runs only (rc19_pool.Reveal); log h is a public input.

Upstream emulators (predicted physical features as functions of x; inputs = standardised log (P, VX, LS, ST)):
  M0Q   one GP per output with its own ARD lengthscales + record-quality noise multiplier (Q)          [rc18_campaign]
  SHQ   ARD lengthscales shared by the chosen outputs (fitted on paid rows that have all of them) + Q [rc18_campaign]
  SHQT  SHQ + per-output Gaussian-prior linear basis in standardised log h with a LEARNED strength b2 (src.rc20_gp):
        the trend coefficient is integrated out, b2 is fitted (ML-II) inside the training subset and can shrink to 1e-8
  SHQM  SHQ with MAP lengthscales, prior log ell ~ N(0, 1^2) on standardised inputs (regularisation remedy candidate)
Features A = log active maximum depth (um), T = T0-window median maximum temperature (K), S = velocity-spike log ratio.
Honest cross-fitting: fold of the j-th paid run = j mod K, K = min(10, n); each fold's upstream fit (hyperparameters, shared
lengthscales, trend strength, target normalisation, Q weights) uses only the paid runs outside the fold.
Classifier g: L2 logistic (C = 1) on the standardised out-of-fold features (scaling from the out-of-fold features), +H adds
the exact public column log h~ (standardised on the pool) to the SAME classifier; deployment:
  standard  g applied to the full-paid upstream fit's predictive means at x;
  FD        fold-deployed (training-construction remedy candidate): p(x) = mean_k g(F_k(x)) over the K fold models, so the
            classifier is trained and deployed on features from the same fold models (no full-fit / fold mismatch).
HONLY = g on log h~ alone (no emulator). APPROX = RC19's closed-form leave-one-out features of the full fit (diagnostic).
Every construction predicts the paid class rate until both classes are revealed (RC19 rule).
"""
from __future__ import annotations

import warnings

import numpy as np

import src.rc18_campaign as C
import src.rc18_gp as G
import src.rc19_learn as LN
import src.rc19b_keyhole as K
import src.rc20_gp as HG

KF = 10
ATS = ("log_A_um", "tmax_T0_K", "vmax_spike_logratio")
MAP_PRIOR = (0.0, 1.0)                     # log ell ~ N(0, 1^2) on standardised inputs (fixed before any RC20 outcome)


def hcol(task):
    """Standardised log h = log P - 0.5 log VX - 1.5 log LS (LS = Gaussian spot radius, m), pool statistics only."""
    lx = np.log(task["X"]); h = lx[:, 0] - 0.5 * lx[:, 1] - 1.5 * lx[:, 2]; p = task["pool"]
    return (h - h[p].mean()) / h[p].std()


def _fit_shq_variant(Z, Y, rows, cols, short, Hc=None, hyperprior=None):
    """SHQ with an optional learned log-h basis (Hc) or an optional lengthscale hyperprior; mirrors rc18_campaign.fit_model's
    SH branch (shared fit on the common rows, per-output refit at the shared optimum on all of that output's rows)."""
    W = np.where(short, C.W_SHORT, 1.0) if short is not None else np.ones(len(Z)); out = {}; shared = {}
    common = rows[np.all(np.isfinite(Y[np.ix_(rows, range(len(cols)))]), axis=1)]
    if (W[common] <= 100).sum() >= 5:
        if Hc is None:
            gs, _ = G.fit_shared(Z[common], Y[np.ix_(common, range(len(cols)))], w=W[common],
                                 hyperprior=None if hyperprior is None else (np.full(Z.shape[1], hyperprior[0]), hyperprior[1]))
            shared = {c: gs[k].theta for k, c in enumerate(cols)}
        else:
            gs, _ = HG.fit_shared_h(Z[common], Y[np.ix_(common, range(len(cols)))], Hc[common], w=W[common])
            shared = {c: gs[k].theta_ext for k, c in enumerate(cols)}
    for k, c in enumerate(cols):
        L = rows[np.isfinite(Y[rows, k])]; good = L[W[L] <= 100]
        if len(good) < 3:
            out[c] = None; continue
        th = shared.get(c)
        if Hc is None:
            hp = None if hyperprior is None else (np.full(Z.shape[1], hyperprior[0]), hyperprior[1])
            g = G.GP(hyperprior=hp).fit(Z[L], Y[L, k], w=W[L], theta0=th, optimize=th is None); f = C.Fitted(g, Z)
        else:
            g = HG.HGP().fit(Z[L], Y[L, k], H=Hc[L][:, None], w=W[L], theta0=th, optimize=th is None); f = C.Fitted(g, Z, {"H": Hc[:, None]})
        f.choice = "shared" if th is not None else "own"; out[c] = f
    return out


def fit_up(model, Z, Y, rows, cols, short, Hc=None):
    if model in ("M0Q", "SHQ"):
        return C.fit_model(model, Z, Y, rows, list(cols), emu=None, short=short)
    if model == "SHQT":
        return _fit_shq_variant(Z, Y, rows, cols, short, Hc=Hc)
    if model == "SHQM":
        return _fit_shq_variant(Z, Y, rows, cols, short, hyperprior=MAP_PRIOR)
    raise ValueError(model)


def _theta_of(f):
    return None if f is None else np.asarray(f.g.theta, float)


def cf(Z, rev, cols, model, rows_eval, Kf=KF, Hc=None, fold_eval=False):
    """Honest K-fold out-of-fold features of the paid runs, full-fit features (means, latent variances) at rows_eval and,
    with fold_eval, every fold model's predictions at rows_eval. Mirrors rc19b_keyhole.cf_features exactly for SHQ / M0Q."""
    cols = list(cols); paid = rev.paid; Yall = rev.paid_Y()[:, [LN.TI[c] for c in cols]]; short = rev.paid_short()
    fold, k = K.folds(len(paid), Kf); F = np.full((len(paid), len(cols)), np.nan); fb = 0
    FE = np.full((k, len(rows_eval), len(cols)), np.nan) if fold_eval else None; th_f = []
    for j in range(k):
        tr, te = paid[fold != j], paid[fold == j]
        Ytr = np.full_like(Yall, np.nan); Ytr[tr] = Yall[tr]
        fits = fit_up(model, Z, Ytr, tr, cols, short, Hc)
        for kk, c in enumerate(cols):
            f = fits.get(c)
            if f is None:
                v = Yall[tr, kk]; v = v[np.isfinite(v)]; mv = float(np.mean(v)) if len(v) else 0.0
                F[fold == j, kk] = mv; fb += 1
                if FE is not None:
                    FE[j, :, kk] = mv
            else:
                F[fold == j, kk] = f.predict(te)[0]
                if FE is not None:
                    FE[j, :, kk] = f.predict(rows_eval)[0]
        th_f.append(_theta_of(fits.get(cols[0])))
    full = fit_up(model, Z, Yall, paid, cols, short, Hc)
    E = np.column_stack([(full[c].predict(rows_eval)[0] if full.get(c) is not None else np.full(len(rows_eval), np.nanmean(Yall[paid, kk])))
                         for kk, c in enumerate(cols)])
    V = np.column_stack([(full[c].predict(rows_eval)[1] if full.get(c) is not None else np.full(len(rows_eval), np.nanvar(Yall[paid, kk])))
                         for kk, c in enumerate(cols)])
    return {"F": F, "E": E, "V": V, "FE": FE, "full": full, "K": k, "fallbacks": fb, "theta_folds": th_f, "theta_full": _theta_of(full.get(cols[0])),
            "Yall": Yall, "paid": paid}


def clf(F, y, E, xtr=None, xev=None):
    """g = L2 logistic (C = 1) on standardised training features (+ exact extra columns); returns (proba at E, g, mu, sd)."""
    from sklearn.linear_model import LogisticRegression
    Xtr = F if xtr is None else np.c_[F, xtr]; Xev = E if xev is None else np.c_[E, xev]
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-12
    g = LogisticRegression(C=1.0, max_iter=5000).fit((Xtr - mu) / sd, y)
    return g.predict_proba((Xev - mu) / sd)[:, 1], g, mu, sd


def eta_moments(g, mu, sd, E, V, xev=None):
    """Linear predictor eta(x) = g's decision function at the full-fit feature means (+ exact extra columns) and its variance
    from the upstream latent variances: Var eta = sum_t (w_t / sd_t)^2 v_t(x) (outputs independent given hyperparameters;
    classifier weights held fixed, i.e. a plug-in for the weights)."""
    X = E if xev is None else np.c_[E, xev]; nf = E.shape[1]
    eta = g.decision_function((X - mu) / sd); w = g.coef_[0][:nf] / sd[:nf]
    return eta, np.sum((w ** 2)[None, :] * V, axis=1)


def approx_loo_features(full, Yall, paid, cols):
    """RC19's ATSAPPROX training features: closed-form LOO means of the FULL fit (full-fit hyperparameters/normalisation)."""
    F = np.full((len(paid), len(cols)), np.nan); pos = {int(i): j for j, i in enumerate(paid)}
    for k, c in enumerate(cols):
        f = full.get(c)
        if f is None or not isinstance(f, C.Fitted):
            continue
        L = paid[np.isfinite(Yall[paid, k])]
        if len(L) != len(f.g.alpha):
            continue
        m_loo, _ = LN._loo(f.g, Yall[L, k]); F[[pos[int(i)] for i in L], k] = m_loo
        miss = ~np.isfinite(F[:, k])
        if miss.any():
            F[miss, k] = f.predict(paid[miss])[0]
    return F


ATTR = ("M0Q_A", "M0Q_ATS", "SHQ_A", "SHQ_ATS", "SHQ_A_H", "SHQ_ATS_H", "SHQT_A", "SHQT_ATS", "HONLY")


def constructions(task, rev, Z, which=ATTR, Kf=KF, remedy=(), extra=None, diag=False):
    """Probabilities at the test rows (and at `extra` rows if given) for every requested construction at one paid state.
    remedy: subset of {"FD", "MAP"}: FD applies fold-deployment to SHQ_ATS (and to SHQ_ATS_H / SHQT_ATS when computed);
    MAP adds SHQM_ATS (regularised hyperparameters, standard deployment)."""
    test = task["test"]; ex = np.asarray([] if extra is None else extra, int); rows = np.r_[test, ex]; nt = len(test)
    y_p = rev.paid_y(); A_p = rev.paid_A(); L = rev.paid; y = y_p[L]; usable = np.isfinite(A_p[L])
    two_u = len(set(y_p[L][usable].tolist())) == 2; two_all = len(set(y.tolist())) == 2; rate = float(np.mean(y))
    h = hcol(task); out, info = {}, {}
    const = lambda: np.full(len(rows), rate)
    want = set(which)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if "HONLY" in want:
            out["HONLY"] = clf(h[L][:, None], y, h[rows][:, None])[0] if two_all else const()
        need_m0q = bool(want & {"M0Q_A", "M0Q_ATS"}); need_shq = bool(want & {"SHQ_A", "SHQ_ATS", "SHQ_A_H", "SHQ_ATS_H"}) or "FD" in remedy
        need_shqt = bool(want & {"SHQT_A", "SHQT_ATS"})
        if not two_u:
            for nm in list(want - {"HONLY"}) + [r for r in ("SHQ_ATS_FD", "SHQ_ATS_H_FD", "SHQT_ATS_FD") if "FD" in remedy] + (["SHQM_ATS"] if "MAP" in remedy else []):
                out[nm] = const()
        else:
            fe = "FD" in remedy
            if need_m0q:
                R = cf(Z, rev, ATS, "M0Q", rows, Kf)
                if "M0Q_A" in want:
                    out["M0Q_A"] = clf(R["F"][:, :1], y, R["E"][:, :1])[0]
                if "M0Q_ATS" in want:
                    out["M0Q_ATS"] = clf(R["F"], y, R["E"])[0]
                info["M0Q"] = {"K": R["K"], "fallbacks": R["fallbacks"]}
            if need_shq:
                R = cf(Z, rev, ATS, "SHQ", rows, Kf, fold_eval=fe)
                pa, ga, mua, sda = clf(R["F"][:, :1], y, R["E"][:, :1]); p3, g3, mu3, sd3 = clf(R["F"], y, R["E"])
                if "SHQ_A" in want:
                    out["SHQ_A"] = pa
                if "SHQ_ATS" in want:
                    out["SHQ_ATS"] = p3
                if want & {"SHQ_A_H", "SHQ_ATS_H"}:
                    pah = clf(R["F"][:, :1], y, R["E"][:, :1], h[L][:, None], h[rows][:, None])
                    p3h = clf(R["F"], y, R["E"], h[L][:, None], h[rows][:, None])
                    out["SHQ_A_H"], out["SHQ_ATS_H"] = pah[0], p3h[0]
                    info["SHQ_ATS_H_coef"] = p3h[1].coef_[0].tolist()
                if fe:
                    out["SHQ_ATS_FD"] = np.mean([g3.predict_proba((R["FE"][j] - mu3) / sd3)[:, 1] for j in range(R["K"])], axis=0)
                    if "SHQ_ATS_H" in want:
                        out["SHQ_ATS_H_FD"] = np.mean([p3h[1].predict_proba((np.c_[R["FE"][j], h[rows]] - p3h[2]) / p3h[3])[:, 1] for j in range(R["K"])], axis=0)
                info["SHQ"] = {"K": R["K"], "fallbacks": R["fallbacks"], "coef_ATS": g3.coef_[0].tolist(), "coef_A": ga.coef_[0].tolist()}
                if diag:
                    Fa = approx_loo_features(R["full"], R["Yall"], R["paid"], ATS); sdF = np.nanstd(R["F"], axis=0) + 1e-12
                    Ein = np.column_stack([R["full"][c].predict(R["paid"])[0] if R["full"].get(c) is not None else np.full(len(R["paid"]), np.nan) for c in ATS])
                    ok = np.all(np.isfinite(Fa), axis=1)
                    pa_ = clf(Fa[ok], y[ok], R["E"])[1] if ok.sum() > 2 and len(set(y[ok].tolist())) == 2 else None
                    tf = [t for t in R["theta_folds"] if t is not None]; tfull = R["theta_full"]; d = Z.shape[1]
                    info["diag"] = {
                        "rms_oof_minus_approx_over_sd": (np.sqrt(np.nanmean((R["F"] - Fa) ** 2, axis=0)) / sdF).tolist(),
                        "rms_oof_minus_insample_over_sd": (np.sqrt(np.nanmean((R["F"] - Ein) ** 2, axis=0)) / sdF).tolist(),
                        "rms_approx_minus_insample_over_sd": (np.sqrt(np.nanmean((Fa - Ein) ** 2, axis=0)) / sdF).tolist(),
                        "coef_norm_honest": float(np.linalg.norm(g3.coef_[0])), "coef_norm_approx": None if pa_ is None else float(np.linalg.norm(pa_.coef_[0])),
                        "fold_logell_sd": float(np.mean(np.std([t[1:1 + d] for t in tf], axis=0))) if len(tf) > 1 else None,
                        "fold_logell_absdev_from_full": float(np.mean(np.abs(np.array([t[1:1 + d] for t in tf]) - tfull[1:1 + d]))) if (tf and tfull is not None) else None}
            if need_shqt:
                R = cf(Z, rev, ATS, "SHQT", rows, Kf, Hc=h, fold_eval=fe and "SHQT_ATS" in want)
                if "SHQT_A" in want:
                    out["SHQT_A"] = clf(R["F"][:, :1], y, R["E"][:, :1])[0]
                pt, gt, mut, sdt = clf(R["F"], y, R["E"])
                if "SHQT_ATS" in want:
                    out["SHQT_ATS"] = pt
                    if fe:
                        out["SHQT_ATS_FD"] = np.mean([gt.predict_proba((R["FE"][j] - mut) / sdt)[:, 1] for j in range(R["K"])], axis=0)
                full = R["full"]; info["SHQT"] = {"K": R["K"], "fallbacks": R["fallbacks"],
                                                  "b2_full": {c: (None if full.get(c) is None else float(full[c].g.b2)) for c in ATS}}
            if "MAP" in remedy:
                R = cf(Z, rev, ATS, "SHQM", rows, Kf)
                out["SHQM_ATS"] = clf(R["F"], y, R["E"])[0]; info["SHQM"] = {"K": R["K"], "fallbacks": R["fallbacks"]}
    res = {k: np.asarray(v, float)[:nt] for k, v in out.items()}
    if extra is not None:
        info["_extra"] = {k: np.asarray(v, float)[nt:] for k, v in out.items()}
    return res, info
