"""Threshold-surface probit model T (development implementation).

Physics coordinate  l = log h = log P - 0.5 log VX - 1.5 log LS.
Context             z = (log VX, log LS, ST), standardized on the outer training pool (label-free).

Boundary            tau(z) = mu + beta^T z + u(z),
                    mu ~ N(mu0, s_mu^2), beta ~ N(0, s_beta^2 I), u ~ GP(0, s_u^2 Matern32_ARD(z; ls))
Observation         P(Y=1 | tau) = Phi( c (l - tau(z)) ),   c = 1/s  (label softness s in log-h units)

For fixed hyperparameters (c, s_u, ls) this is a probit GPC on the latent
    g(x) = c (l - tau(z)) ~ GP( c (l - mu0),  c^2 [s_mu^2 + s_beta^2 z.z' + s_u^2 k(z,z')] ).
Laplace inference; type-II ML over (log c, log s_u, log ls) within frozen bounds.

Posterior objects at a location x=(l,z):
    latent g ~ N(m, v)            (Laplace)
    pi(x)  = Phi(m / sqrt(v))                 posterior latent-set membership  P(l > tau(z) | D)
    p(x)   = Phi(m / sqrt(1 + v))             predictive label probability     E[Phi(g) | D]
    tau(z) ~ N( l - m/c , v/c^2 )             boundary location in log-h units
"""
from __future__ import annotations
import math
import numpy as np
from scipy.linalg import cholesky, cho_solve, solve_triangular
from scipy.optimize import minimize
from scipy.special import log_ndtr, ndtr
from scipy.stats import norm
from cdl import matern32_ard


class TModel:
    def __init__(self, mu0: float = 0.0, s_mu: float = 3.0, s_beta: float = 1.0,
                 c_bounds=(1.0, 10.0), su_bounds=(0.02, 1.0), ls_bounds=(0.3, 10.0),
                 init=(4.0, 0.2, 1.5), optimize=True, maxiter=200, jitter=1e-8):
        self.mu0, self.s_mu, self.s_beta = float(mu0), float(s_mu), float(s_beta)
        self.c_bounds, self.su_bounds, self.ls_bounds = c_bounds, su_bounds, ls_bounds
        self.init, self.optimize, self.maxiter, self.jitter = init, optimize, maxiter, jitter

    # tau-covariance over contexts
    def _ktau(self, ZA, ZB, theta):
        su = math.exp(theta[1]); ls = np.exp(theta[2:])
        return self.s_mu ** 2 + self.s_beta ** 2 * (ZA @ ZB.T) + matern32_ard(ZA, ZB, ls, su ** 2)

    def _lik(self, f, y):
        s = 2.0 * y - 1.0
        z = s * f
        ll = log_ndtr(z)
        ratio = np.exp(norm.logpdf(z) - log_ndtr(z))
        g = s * ratio
        w = ratio * (ratio + z)
        return ll, g, np.maximum(w, 1e-12)

    def _mode(self, K, mean, y, return_all=False):
        n = len(y); f = mean.copy(); a = np.zeros(n)
        for it in range(200):
            ll, g, w = self._lik(f, y); sw = np.sqrt(w)
            B = np.eye(n) + sw[:, None] * K * sw[None, :]; L = cholesky(B, lower=True)
            b = w * (f - mean) + g
            a = b - sw * cho_solve((L, True), sw * (K @ b))
            f_new = mean + K @ a
            done = np.max(np.abs(f_new - f)) < 1e-9; f = f_new
            if done: break
        ll, g, w = self._lik(f, y); sw = np.sqrt(w)
        B = np.eye(n) + sw[:, None] * K * sw[None, :]; L = cholesky(B, lower=True)
        lml = ll.sum() - 0.5 * a @ (f - mean) - np.log(np.diag(L)).sum()
        return (f, a, w, sw, L, lml) if return_all else lml

    def _build(self, theta, l, Z):
        c = math.exp(theta[0])
        mean = c * (l - self.mu0)
        K = c * c * self._ktau(Z, Z, theta) + self.jitter * np.eye(len(l))
        return mean, K

    def _objective(self, theta, l, Z, y):
        mean, K = self._build(theta, l, Z)
        try:
            return -self._mode(K, mean, y)
        except np.linalg.LinAlgError:
            return 1e10

    def fit(self, l, Z, y):
        l = np.asarray(l, float); Z = np.asarray(Z, float); y = np.asarray(y, int)
        self.l, self.Z, self.y = l, Z, y; self.dim = Z.shape[1]
        th0 = np.r_[math.log(self.init[0]), math.log(self.init[1]), np.log(np.full(self.dim, self.init[2]))]
        bounds = [tuple(np.log(self.c_bounds)), tuple(np.log(self.su_bounds))] + [tuple(np.log(self.ls_bounds))] * self.dim
        if self.optimize:
            res = minimize(self._objective, th0, args=(l, Z, y), method="L-BFGS-B", bounds=bounds, options={"maxiter": self.maxiter})
            self.theta = res.x; self.converged = bool(res.success); self.nfev = int(res.nfev)
        else:
            self.theta = th0; self.converged = True; self.nfev = 0
        self.mean_, self.K = self._build(self.theta, l, Z)
        self.f, self.alpha, self.w, self.sw, self.L, self.lml = self._mode(self.K, self.mean_, y, return_all=True)
        self.c = math.exp(self.theta[0])
        return self

    # ---- posterior over the latent g at new locations, with cross-covariance
    def latent(self, ls_, Zs, return_cov=False):
        c = self.c
        Ks = c * c * self._ktau(self.Z, np.asarray(Zs, float), self.theta)
        m = c * (np.asarray(ls_, float) - self.mu0) + Ks.T @ self.alpha
        V = solve_triangular(self.L, self.sw[:, None] * Ks, lower=True)
        Kss = c * c * self._ktau(np.asarray(Zs, float), np.asarray(Zs, float), self.theta)
        if return_cov:
            C = Kss - V.T @ V
            return m, np.maximum(np.diag(C), 1e-12), C
        var = np.maximum(np.diag(Kss) - (V * V).sum(0), 1e-12)
        return m, var

    def pi(self, ls_, Zs):
        m, v = self.latent(ls_, Zs); return ndtr(m / np.sqrt(v))

    def p(self, ls_, Zs):
        m, v = self.latent(ls_, Zs); return ndtr(m / np.sqrt(1.0 + v))

    def tau(self, Zs):
        """Posterior mean and sd of the boundary location (log-h units) at contexts Zs."""
        m, v = self.latent(np.zeros(len(Zs)), Zs)  # m = c(0 - mu0) + ... -> tau = -m/c
        return -m / self.c, np.sqrt(v) / self.c

    @property
    def hyper(self):
        return {"c": self.c, "s": 1.0 / self.c, "s_u": math.exp(self.theta[1]), "ls": np.exp(self.theta[2:]).tolist()}


# ------------------------------------------------------------ acquisitions

def lookahead_terms(m_x, v_x):
    """Probit look-ahead moment updates for observing Y at a location with latent N(m_x, v_x).
    Returns p1, and for y in {0,1}: mean-shift coefficient (multiplies Cov(u,x)) and
    variance-reduction coefficient (multiplies Cov(u,x)^2)."""
    s = np.sqrt(1.0 + v_x); t = m_x / s
    p1 = ndtr(t)
    r1 = np.exp(norm.logpdf(t) - log_ndtr(t))      # phi/Phi at t   (y=1)
    r0 = np.exp(norm.logpdf(-t) - log_ndtr(-t))    # phi/Phi at -t  (y=0)
    a1, a0 = r1 / s, -r0 / s                        # mean shift per unit covariance
    b1, b0 = r1 * (r1 + t) / (1.0 + v_x), r0 * (r0 - t) / (1.0 + v_x)   # variance reduction per cov^2
    return p1, (a0, a1), (b0, b1)


def acq_global_sur_pi(m_ref, v_ref, m_c, v_c, C):
    """Expected reduction of the finite-pool latent-set Bayes risk
       R = sum_u min(pi(u), 1-pi(u)),  pi = Phi(m/sqrt(v)),
    for each candidate (rows of C = Cov(candidate, reference))."""
    cur = np.minimum(ndtr(m_ref / np.sqrt(v_ref)), 1 - ndtr(m_ref / np.sqrt(v_ref))).sum()
    p1, (a0, a1), (b0, b1) = lookahead_terms(m_c, v_c)
    out = np.empty(len(m_c))
    for i in range(len(m_c)):
        c = C[i]
        vals = []
        for a, b in ((a0[i], b0[i]), (a1[i], b1[i])):
            m2 = m_ref + a * c; v2 = np.maximum(v_ref - b * c * c, 1e-12)
            pi2 = ndtr(m2 / np.sqrt(v2)); vals.append(np.minimum(pi2, 1 - pi2).sum())
        out[i] = cur - ((1 - p1[i]) * vals[0] + p1[i] * vals[1])
    return out


def acq_global_sur_p(m_ref, v_ref, m_c, v_c, C):
    """Same as above but with the predictive label probability p = Phi(m/sqrt(1+v))."""
    pr = ndtr(m_ref / np.sqrt(1 + v_ref)); cur = np.minimum(pr, 1 - pr).sum()
    p1, (a0, a1), (b0, b1) = lookahead_terms(m_c, v_c)
    out = np.empty(len(m_c))
    for i in range(len(m_c)):
        c = C[i]; vals = []
        for a, b in ((a0[i], b0[i]), (a1[i], b1[i])):
            m2 = m_ref + a * c; v2 = np.maximum(v_ref - b * c * c, 1e-12)
            p2 = ndtr(m2 / np.sqrt(1 + v2)); vals.append(np.minimum(p2, 1 - p2).sum())
        out[i] = cur - ((1 - p1[i]) * vals[0] + p1[i] * vals[1])
    return out


def acq_threshold_variance(m_c, v_c, C):
    """Expected reduction of sum_u Var[tau(u)] (up to the constant 1/c^2):
       phi(t)^2 / (Phi(t)(1-Phi(t)) (1+v_x)) * sum_u Cov(u,x)^2."""
    s2 = 1.0 + v_c; t = m_c / np.sqrt(s2); P = ndtr(t)
    w = norm.pdf(t) ** 2 / np.maximum(P * (1 - P), 1e-300) / s2
    return w * (C * C).sum(1)
