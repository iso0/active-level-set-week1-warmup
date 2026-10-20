"""RC21 PHR classifier: physical-summary predictions + h trend + a shrinkable transverse residual, one hierarchical Laplace GP
classification layer with Bayesian model averaging over a FIXED hyperparameter grid. Learned from the paid labels only.

Latent Keyhole score (all terms in ONE discriminative layer; h enters once, never as a second observation):
    eta(x) = b0 + beta_h z_h(x) + sum_t w_t F~_t(x) + r(U(x))
  F~_t   standardised honest out-of-fold SHQ predictions of (log A, T0 max temperature, spike log-ratio) for the paid runs
         (training) and the full-paid fit's predictive means (deployment) - exactly the SHQ_ATS_H features (src.rc20_attr);
  z_h    exact standardised log h (log P - 0.5 log VX - 1.5 log LS, LS = Gaussian spot radius in m), the physical trend;
  U(x)   coordinates of the standardised log inputs Z in the 3-dimensional subspace ORTHOGONAL to the h direction d
         (d = a * s / |a * s|, a = (1, -1/2, -3/2, 0), s = pool SD of the log inputs, so Z . d is exactly proportional to z_h);
         r(U) is therefore constant along h and cannot re-learn or double the h trend (beta_h stays identified); it can only
         express deviations transverse to the h scaling law (other exponents, ST, local structure).
Priors: b0 ~ N(0, 10^2) (effectively free, as sklearn's unpenalised intercept); beta_h ~ N(0, tau_h^2); w_t ~ N(0, tau_F^2);
  r ~ GP(0, sigma_r^2 exp(-|U - U'|^2 / (2 ell^2))). Integrating the coefficients out gives one GP prior with kernel
  K = 10^2 + tau_h^2 z_h z_h' + tau_F^2 F~ F~' + sigma_r^2 k_ell(U, U').
Hyperparameters theta = (tau_F, tau_h, sigma_r, ell) on a fixed grid, hyperprior: tau_F, tau_h log-uniform on {0.5, 1, 2, 4};
  P(sigma_r = 0) = 1/2 (no residual), 1/6 each for {0.5, 1, 2}; ell uniform on {0.75, 1.5} when sigma_r > 0. Posterior weights
  from the Laplace marginal likelihood (Rasmussen & Williams 2006, Alg. 3.1/3.2, logistic likelihood); predictions are the
  posterior-weighted Laplace predictive probabilities, each integrated over its latent predictive N(m, v) by 32-node
  Gauss-Hermite quadrature (no plug-in). theta = (1, 1, 0, -) with the plug-in sigma(m) is the RC20 SHQ_ATS_H classifier
  (L2 logistic, C = 1) up to the intercept prior (nesting; validated in src.rc21_validate).
By-products of the same fits (decomposition, not separate candidates):
  PHR       full posterior average (the RC21 construction);
  PHR_NR    the same restricted to sigma_r = 0 (learned regularisation, no residual);
  PHR_FX    fixed theta = (1, 1, 0), Laplace predictive (integration only);
  PHR_FXMAP fixed theta = (1, 1, 0), plug-in sigma(m) (nesting check against SHQ_ATS_H).
"""
from __future__ import annotations

import numpy as np
from scipy.linalg import solve_triangular
from scipy.special import expit

V0 = 10.0 ** 2
TAU_F = (0.5, 1.0, 2.0, 4.0)
TAU_H = (0.5, 1.0, 2.0, 4.0)
SIG_R = (0.0, 0.5, 1.0, 2.0)
ELL = (0.75, 1.5)
P_NORES = 0.5
H_DIR = np.array([1.0, -0.5, -1.5, 0.0])
_GHX, _GHW = np.polynomial.hermite_e.hermegauss(64)
_GHW = _GHW / _GHW.sum()


def grid():
    """[(tau_F, tau_h, sigma_r, ell, log prior)] - 16 x (1 + 3 x 2) = 112 configurations."""
    out = []
    for tf in TAU_F:
        for th in TAU_H:
            base = -np.log(len(TAU_F) * len(TAU_H))
            out.append((tf, th, 0.0, None, base + np.log(P_NORES)))
            for sr in SIG_R[1:]:
                for el in ELL:
                    out.append((tf, th, sr, el, base + np.log((1 - P_NORES) / (len(SIG_R) - 1) / len(ELL))))
    return out


def transverse(task, Z):
    """U = Z B with B an orthonormal basis of the complement of the h direction in standardised log-input space; also d."""
    s = np.log(task["X"])[task["pool"]].std(0); d = H_DIR * s; d = d / np.linalg.norm(d)
    Q, _ = np.linalg.qr(np.c_[d, np.eye(len(d))]); B = Q[:, 1:len(d)]
    return Z @ B, d


def _loglik(f, y):
    return float(np.sum(y * f - np.logaddexp(0.0, f)))


def laplace(K, y, tol=1e-10, maxit=200):
    """Mode of p(f | y) under N(0, K) and a logistic likelihood (y in {0, 1}); Newton in the a-parametrisation f = K a with
    step halving (works for singular K). Returns the mode and the Laplace log marginal likelihood."""
    n = len(y); a = np.zeros(n); f = np.zeros(n); obj = _loglik(f, y)
    for _ in range(maxit):
        pi = expit(f); W = pi * (1 - pi); sW = np.sqrt(W)
        L = np.linalg.cholesky(np.eye(n) + sW[:, None] * K * sW[None, :])
        b = W * f + (y - pi); c = solve_triangular(L, sW * (K @ b), lower=True)
        a_new = b - sW * solve_triangular(L.T, c, lower=False); da = a_new - a; step = 1.0
        while True:
            a_try = a + step * da; f_try = K @ a_try; o_try = -0.5 * a_try @ f_try + _loglik(f_try, y)
            if o_try >= obj - 1e-12 or step < 1e-6:
                break
            step *= 0.5
        done = abs(o_try - obj) < tol; a, f, obj = a_try, f_try, o_try
        if done:
            break
    pi = expit(f); W = pi * (1 - pi); sW = np.sqrt(W); L = np.linalg.cholesky(np.eye(n) + sW[:, None] * K * sW[None, :])
    logZ = -0.5 * a @ f + _loglik(f, y) - float(np.sum(np.log(np.diag(L))))
    return {"f": f, "a": a, "obj": obj, "grad": y - pi, "sW": sW, "L": L, "logZ": logZ}


def predictive(mode, Ks, kss, plugin=False):
    """Laplace predictive at evaluation points: latent mean / variance and P(y = 1) (Gauss-Hermite integral or plug-in)."""
    m = Ks @ mode["grad"]
    v = solve_triangular(mode["L"], mode["sW"][:, None] * Ks.T, lower=True); var = np.maximum(kss - np.sum(v ** 2, axis=0), 0.0)
    if plugin:
        return m, var, expit(m)
    return m, var, expit(m[:, None] + np.sqrt(var)[:, None] * _GHX[None, :]) @ _GHW


class Gram:
    """Kernel pieces between two point sets: constant, h, features and squared transverse distances."""

    def __init__(self, Ha, Hb, Ua, Ub):
        self.c = np.ones((len(Ha), len(Hb))); self.h = np.outer(Ha[:, 0], Hb[:, 0]); self.F = Ha[:, 1:] @ Hb[:, 1:].T
        self.d2 = np.maximum(np.sum(Ua ** 2, 1)[:, None] + np.sum(Ub ** 2, 1)[None, :] - 2 * Ua @ Ub.T, 0.0); self._rbf = {}

    def rbf(self, ell):
        if ell not in self._rbf:
            self._rbf[ell] = np.exp(-0.5 * self.d2 / ell ** 2)
        return self._rbf[ell]

    def K(self, tf, th, sr, ell):
        K = V0 * self.c + th ** 2 * self.h + tf ** 2 * self.F
        return K + sr ** 2 * self.rbf(ell) if sr > 0 else K


def fit_predict(Ftr, htr, Utr, y, Fev, hev, Uev):
    """PHR and its by-products at the evaluation rows. Ftr / Fev: training (out-of-fold) and deployment feature matrices;
    htr / hev: exact z_h; Utr / Uev: transverse coordinates; y: paid labels in {0, 1}. Standardisation of [z_h, F] from the
    training rows (as src.rc20_attr.clf)."""
    Xtr = np.c_[htr, Ftr]; Xev = np.c_[hev, Fev]; mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-12
    Htr, Hev = (Xtr - mu) / sd, (Xev - mu) / sd; y = np.asarray(y, float)
    Gtt = Gram(Htr, Htr, Utr, Utr); Get = Gram(Hev, Htr, Uev, Utr)
    kss_c = np.ones(len(Hev)); kss_h = Hev[:, 0] ** 2; kss_F = np.sum(Hev[:, 1:] ** 2, 1)
    G = grid(); logw = np.empty(len(G)); P = np.empty((len(G), len(Hev))); diag = []
    for g, (tf, th, sr, el, lp) in enumerate(G):
        mode = laplace(Gtt.K(tf, th, sr, el), y)
        kss = V0 * kss_c + th ** 2 * kss_h + tf ** 2 * kss_F + (sr ** 2 if sr > 0 else 0.0)
        _, _, P[g] = predictive(mode, Get.K(tf, th, sr, el), kss); logw[g] = mode["logZ"] + lp
        if (tf, th, sr) == (1.0, 1.0, 0.0):
            _, _, p_map = predictive(mode, Get.K(tf, th, sr, el), kss, plugin=True); p_fx = P[g].copy()
    w = np.exp(logw - logw.max()); w /= w.sum()
    nr = np.asarray([c[2] == 0.0 for c in G]); wn = np.where(nr, np.exp(logw - logw[nr].max()), 0.0); wn /= wn.sum()
    arr = np.asarray([(c[0], c[1], c[2], c[3] or 0.0) for c in G])
    info = {"post_residual": float(w[~nr].sum()), "post_mean_tau_F": float(w @ arr[:, 0]), "post_mean_tau_h": float(w @ arr[:, 1]),
            "post_mean_sigma_r": float(w @ arr[:, 2]), "post_mean_ell_given_res": float((w[~nr] @ arr[~nr, 3]) / max(w[~nr].sum(), 1e-300)),
            "map_config": [float(v) for v in arr[int(np.argmax(logw))]], "n_configs": len(G)}
    return {"PHR": w @ P, "PHR_NR": wn @ P, "PHR_FX": p_fx, "PHR_FXMAP": p_map}, info
