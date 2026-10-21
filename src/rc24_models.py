"""RC24 Stage A constructions on one paid state (public inputs and PAID outcomes only; test outcomes evaluator-only).

M3        faithful port of the historical Week 9 Phase 1.13 model M3 (sibling repo thesis-week9-phase1-18b..., commit 25520785,
          src/week9_phase1_13_fixed_physics_ard_discrepancy.py + src/week9_phase1_11_fixed_mean_discrepancy_gp.py):
            physics mean  m(x) = a + b z(x), z = log h standardised on the PAID rows, (a, b) = sklearn LogisticRegression
                          (C = 1e6, lbfgs, max_iter 3000) on the paid labels, then FROZEN;
            residual      Laplace GP classification (GPML Alg. 3.1 / 5.1, logistic likelihood) with the fixed mean m(x) and kernel
                          ConstantKernel(0.09, bounds (0.05^2, 1.0^2)) x Matern(nu = 1.5, ARD lengthscales init 1, bounds (0.01, 100))
                          on StandardScaler(raw P, VX, LS, ST) fitted on the task's candidate-pool inputs (public; historical:
                          the outer training pool); L-BFGS-B on the Laplace log marginal likelihood (maxiter 150, ftol 1e-12,
                          gtol 1e-7, no restart; deterministic fallback to the initial kernel on an exception);
            prediction    Williams-Barber five-erf approximation of E[sigmoid(f)], f ~ N(latent mean, latent variance) (sklearn GPC).
          Known historical properties (disclosed, NOT corrected in M3): the h mean is practically unregularised (C = 1e6), so on
          (nearly) separable paid labels its slope becomes very large; the residual amplitude is capped (SD <= 1), so the residual
          cannot overrule a large physics latent. One-class rule: the paid class rate until both classes are paid (RC19 rule).
M3_C1     renamed corrected control (matched evaluation only): identical to M3 except the physics-mean logistic regression uses
          C = 1 (sklearn default L2), i.e. the saturated h mean is regularised. It is a different model, never called M3.
HA_LEAN   RC23 construction (src.rc23_common.state, unchanged).
HA_LEAN straddle (pre-registered latent score, boundary, uncertainty):
          eta(x) = logit p_bar(x), p_bar = sum_g w_g sigmoid(m_g(x)) the HA_LEAN probability -> boundary eta = 0 is exactly the
          HA_LEAN decision boundary p_bar = 0.5;
          s^2(x) = sum_g w_g [ v_g(x) + sigma2(x) E_g[w_A^2] ] + sum_g w_g (m_g(x) - m_bar(x))^2,  m_bar = sum_g w_g m_g
            v_g        Laplace latent variance of grid configuration g given the plug-in depth feature (classifier uncertainty);
            E_g[w_A^2] posterior second moment of the standardised-depth coefficient in configuration g (mean^2 + variance, exact for
                       the linear kernel); sigma2(x) = EXCESS depth-predictive variance of the standardised feature,
                       max(0, v_A(x) + q - mse_oof) / sd_F^2, v_A = latent predictive variance of the full depth fit at x, q = the
                       fit's homoskedastic noise variance, mse_oof = mean squared honest out-of-fold error of the paid
                       quality-complete depths (the error level the reduced-form classifier was trained under, so in-distribution
                       uncertainty is not counted twice), sd_F = the classifier's feature scale;
            mixture    spread of the grid configurations' latent means.
          The formula is exact for a Gaussian feature (m_g affine and v_g quadratic in the feature); validated by Monte Carlo in
          src/rc24_validate.py. Straddle score 1.96 s(x) - |eta(x)| (Bryan et al. 2005), first index on ties.
"""
from __future__ import annotations

import math
import warnings

import numpy as np
import scipy.optimize
from scipy.linalg import cho_solve, cholesky, solve, solve_triangular
from scipy.special import erf, expit, logit
from sklearn.base import clone
from sklearn.gaussian_process.kernels import ConstantKernel, Matern
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

import src.rc19_learn as LN
import src.rc20_attr as A
import src.rc21_phr as PH
import src.rc22_common as C22
import src.rc23_common as C23

# ======================================================================================== historical constants (Phase 1.11 / 1.13)
RESIDUAL_SD_BOUNDS = (0.05, 1.0)
RESIDUAL_VARIANCE_BOUNDS = tuple(v ** 2 for v in RESIDUAL_SD_BOUNDS)
INITIAL_RESIDUAL_VARIANCE = 0.09
PRIMARY_LENGTH_BOUNDS = (0.01, 100.0)
EPS = 1e-12
WB_COEFS = np.array([-1854.8214151, 3516.89893646, 221.29346712, 128.12323805, -2010.49422654])[:, None]
WB_LAMBDAS = np.array([0.41, 0.40, 0.37, 0.44, 0.39])[:, None]


def m3_kernel():
    return ConstantKernel(INITIAL_RESIDUAL_VARIANCE, RESIDUAL_VARIANCE_BOUNDS) * Matern(length_scale=np.ones(4), length_scale_bounds=PRIMARY_LENGTH_BOUNDS, nu=1.5)


class FixedMeanLaplaceGPC:
    """Verbatim port of week9_phase1_11_fixed_mean_discrepancy_gp.FixedMeanLaplaceGPC (GPML Alg. 3.1, 3.2, 5.1)."""

    def __init__(self, kernel, optimize=True, max_iter_predict=100):
        self.kernel = kernel; self.optimize = bool(optimize); self.max_iter_predict = int(max_iter_predict)

    def _posterior_mode(self, kernel, return_temporaries=False):
        K = kernel(self.X_train_); g = np.zeros(len(self.y_train_), dtype=float); old_lml = -np.inf; iteration = 0
        for iteration in range(1, self.max_iter_predict + 1):
            f = self.mean_train_ + g; pi = expit(f); W = pi * (1.0 - pi); W_sr = np.sqrt(W); W_sr_K = W_sr[:, None] * K
            B = np.eye(len(W)) + W_sr_K * W_sr; L = cholesky(B, lower=True); b = W * g + (self.y_train_ - pi)
            a = b - W_sr * cho_solve((L, True), W_sr_K.dot(b)); g = K.dot(a); f_new = self.mean_train_ + g; sign = self.y_train_ * 2.0 - 1.0
            lml = -0.5 * a.T.dot(g) - np.logaddexp(0.0, -sign * f_new).sum() - np.log(np.diag(L)).sum()
            if lml - old_lml < 1e-10:
                break
            old_lml = float(lml)
        if return_temporaries:
            return float(old_lml), (pi, W_sr, L, b, a, iteration)
        return float(old_lml)

    def _lml_and_gradient(self, theta):
        kernel = self.kernel_.clone_with_theta(theta); K, K_gradient = kernel(self.X_train_, eval_gradient=True)
        Z, (pi, W_sr, L, _, a, _) = self._posterior_mode(kernel, return_temporaries=True)
        R = W_sr[:, None] * cho_solve((L, True), np.diag(W_sr)); Cm = solve(L, W_sr[:, None] * K)
        s_2 = -0.5 * (np.diag(K) - np.einsum("ij,ij->j", Cm, Cm)) * (pi * (1 - pi) * (1 - 2 * pi)); gradient = np.empty(len(theta), dtype=float)
        for j in range(len(theta)):
            Cj = K_gradient[:, :, j]; s_1 = 0.5 * a.T.dot(Cj).dot(a) - 0.5 * R.T.ravel().dot(Cj.ravel()); bj = Cj.dot(self.y_train_ - pi)
            s_3 = bj - K.dot(R.dot(bj)); gradient[j] = s_1 + s_2.T.dot(s_3)
        return -float(Z), -gradient

    def fit(self, X, y, mean_train):
        self.X_train_ = np.asarray(X, dtype=float).copy(); self.y_train_ = np.asarray(y, dtype=int).copy(); self.mean_train_ = np.asarray(mean_train, dtype=float).copy()
        if not (self.X_train_.shape[0] == len(self.y_train_) == len(self.mean_train_)) or set(np.unique(self.y_train_)) != {0, 1}:
            raise RuntimeError("binary classes and matching lengths required")
        self.kernel_ = clone(self.kernel); fallback = "none"; result = None
        if self.optimize and self.kernel_.n_dims:
            try:
                result = scipy.optimize.minimize(self._lml_and_gradient, self.kernel_.theta, method="L-BFGS-B", jac=True, bounds=self.kernel_.bounds,
                                                 options={"maxiter": 150, "ftol": 1e-12, "gtol": 1e-7})
                if not (np.isfinite(result.fun) and np.isfinite(result.x).all()):
                    raise RuntimeError("non-finite optimizer result")
                self.kernel_.theta = result.x
            except Exception as exc:                                         # deterministic initial-kernel fallback (historical)
                fallback = f"initial_kernel_after_{type(exc).__name__}"; result = None; self.kernel_ = clone(self.kernel)
        lml, (self.pi_, self.W_sr_, self.L_, _, self.a_, iterations) = self._posterior_mode(self.kernel_, return_temporaries=True)
        self.diag_ = {"fallback": fallback, "converged": bool(result.success) if result is not None else False, "lml": float(lml), "posterior_iterations": int(iterations),
                      "residual_sd": math.sqrt(float(self.kernel_.k1.constant_value)), "lengthscales": [float(v) for v in np.ravel(self.kernel_.k2.length_scale)]}
        return self

    def latent_mean_and_variance(self, X, mean_test):
        X = np.asarray(X, dtype=float); mean_test = np.asarray(mean_test, dtype=float); K_star = self.kernel_(self.X_train_, X)
        latent_mean = mean_test + K_star.T.dot(self.y_train_ - self.pi_); v = solve(self.L_, self.W_sr_[:, None] * K_star)
        return latent_mean, np.maximum(self.kernel_.diag(X) - np.einsum("ij,ij->j", v, v), EPS)

    def predict_proba(self, X, mean_test):
        latent_mean, latent_var = self.latent_mean_and_variance(X, mean_test); alpha = 1.0 / (2.0 * latent_var); gamma = WB_LAMBDAS * latent_mean
        integrals = np.sqrt(np.pi / alpha) * erf(gamma * np.sqrt(alpha / (alpha + WB_LAMBDAS ** 2))) / (2.0 * np.sqrt(latent_var * 2.0 * np.pi))
        positive = np.clip((WB_COEFS * integrals).sum(axis=0) + 0.5 * WB_COEFS.sum(), EPS, 1.0 - EPS)
        return np.column_stack([1.0 - positive, positive])


def log_h_raw(X):
    return np.log(X[:, 0] / np.sqrt(X[:, 1] * X[:, 2] ** 3))


def m3_fit_predict(X4, logh, y, L, pool, rows, C=1e6):
    """Physics mean (paid log h only, logistic C) + fixed-mean ARD residual GPC; returns P(y = 1) at rows and diagnostics."""
    sc_h = StandardScaler().fit(logh[L, None]); lr = LogisticRegression(C=C, solver="lbfgs", max_iter=3000, random_state=0)
    lr.fit(sc_h.transform(logh[L, None]), y)
    lat = lambda r: lr.decision_function(sc_h.transform(logh[r, None]))
    sx = StandardScaler().fit(X4[pool]); gp = FixedMeanLaplaceGPC(m3_kernel(), optimize=True).fit(sx.transform(X4[L]), y, lat(L))
    p = gp.predict_proba(sx.transform(X4[rows]), lat(rows))[:, 1]
    return p, {**gp.diag_, "physics_intercept": float(lr.intercept_[0]), "physics_slope": float(lr.coef_[0, 0]), "C": C}


# ======================================================================================== HA_LEAN with straddle moments
def ha_lean_moments(task, rev, Z, rows):
    """HA_LEAN probability at rows plus the pre-registered straddle moments (eta, s2) and their components."""
    y_p = rev.paid_y(); A_p = rev.paid_A(); L = rev.paid; y = y_p[L]; usable = np.isfinite(A_p[L])
    if len(set(y_p[L][usable].tolist())) < 2:
        r = float(np.mean(y)); return {"p": np.full(len(rows), r), "one_class": True}
    h = A.hcol(task)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        R1 = A.cf(Z, rev, C23.DEPTH, "SHQ", rows, A.KF)
        Ftr, Fev = R1["F"][:, [0]], R1["E"][:, [0]]
        p, fam = C22.phr_family(R1["F"], h[L], y, R1["E"], h[rows], feats=(0,))
        Xtr = np.c_[h[L], Ftr]; mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-12; Htr = (Xtr - mu) / sd; Hev = (np.c_[h[rows], Fev] - mu) / sd; yf = np.asarray(y, float)
        Gtt = PH.Gram(Htr, Htr, np.zeros((len(L), 1)), np.zeros((len(L), 1)))
        Ew2 = np.empty(len(fam["cfg"]))
        for g, (tf, th) in enumerate(fam["cfg"]):
            mode = PH.laplace(Gtt.K(tf, th, 0.0, None), yf); Fv = Htr[:, 1]
            mean_w = tf ** 2 * float(Fv @ mode["grad"])                                     # E[w_A] = tau_F^2 F~' (y - pi)
            u = solve_triangular(mode["L"], mode["sW"] * Fv, lower=True); var_w = tf ** 2 - tf ** 4 * float(u @ u)  # tau_F^2 - tau_F^4 F~' S F~
            Ew2[g] = mean_w ** 2 + max(var_w, 0.0)
        # excess depth-predictive variance of the standardised feature (full fit at rows vs the honest OOF error level)
        full = R1["full"].get(C23.DEPTH[0]); Yd = R1["Yall"][:, 0]; good = np.isfinite(Yd[L]) & ~rev.paid_short()[L]
        mse = float(np.mean((Ftr[good, 0] - Yd[L][good]) ** 2)) if good.sum() >= 2 else 0.0
        q = _noise_var(full); vA = R1["V"][:, 0]; sig2 = np.maximum(0.0, vA + q - mse) / sd[1] ** 2
    w, Mm, Vv = fam["w"], fam["m"], fam["v"]; mbar = w @ Mm
    s2 = w @ (Vv + sig2[None, :] * Ew2[:, None]) + w @ (Mm - mbar[None, :]) ** 2
    eta = logit(np.clip(p, 1e-12, 1 - 1e-12))
    return {"p": p, "eta": eta, "s2": s2, "one_class": False, "w": w, "m": Mm, "v": Vv, "Ew2": Ew2, "sig2": sig2, "mse_oof": mse, "q": q, "sd_F": float(sd[1]),
            "Fbar_std": Hev[:, 1], "fallbacks": R1["fallbacks"], "_R1": R1, "_H": (Htr, Hev, yf)}


def _noise_var(fit):
    """Homoskedastic noise variance sn2 (original units; rc18_gp.GP.noise) of the fitted depth model; 0 for a fallback fit."""
    g = getattr(fit, "g", None)
    return float(g.noise) if g is not None else 0.0


def straddle_score(mom):
    return 1.96 * np.sqrt(np.maximum(mom["s2"], 0.0)) - np.abs(mom["eta"])


# ======================================================================================== one paid state -> requested constructions
STAGEA_CONS = ("HA_LEAN", "HONLY_LR", "M3", "M3_C1", "E1RAW", "E1CAL", "G3")


def state(task, rev, Z, rows, which, rng=None):
    """Probabilities at rows for the requested constructions; each one-class rule as in its source (HA_LEAN / HONLY_LR: usable
    depth labels, RC23; M3 / M3_C1 / G3: all paid labels, RC19B G3 rule; E1RAW / E1CAL: usable depth labels, RC19B)."""
    import src.rc19b_keyhole as K
    out, info = {}, {}
    lean = [c for c in which if c in ("HA_LEAN", "HONLY_LR")]
    if lean:
        o, inf = C23.state(task, rev, Z, rows, which=tuple(lean)); out.update(o); info["lean"] = inf
    y_p = rev.paid_y(); L = rev.paid; rate = float(np.mean(y_p[L])); two_all = len(set(y_p[L].tolist())) == 2
    X4 = task["X"]; logh = log_h_raw(X4)
    for nm, Cc in (("M3", 1e6), ("M3_C1", 1.0)):
        if nm in which:
            if not two_all:
                out[nm] = np.full(len(rows), rate); info[nm] = {"one_class": True}; continue
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                out[nm], info[nm] = m3_fit_predict(X4, logh, y_p[L], L, task["pool"], rows, C=Cc)
    if any(c in which for c in ("E1RAW", "E1CAL")):
        A_p = rev.paid_A(); usable = np.isfinite(A_p[L])
        if len(set(y_p[L][usable].tolist())) == 2:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pr, pc, _, inf = K.e1_constructions(X4, rev, rows, rows[:1], 10)
            out["E1RAW"], out["E1CAL"] = pr, pc; info["E1"] = inf
        else:
            out["E1RAW"] = out["E1CAL"] = np.full(len(rows), rate)
    if "G3" in which:
        if two_all:
            import src.week18_engine as E
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                tk = {"X": X4, "y": y_p, "pool": task["pool"], "prior": np.array([], int), "depth": rev.paid_A()}
                f = E.fit_learner(("G3", "mlii"), tk, list(L), None, {"kernel": None, "b0": len(L)}); out["G3"] = np.asarray(E.proba(f, X4[rows]), float)
        else:
            out["G3"] = np.full(len(rows), rate)
    return {k: out[k] for k in which}, info
