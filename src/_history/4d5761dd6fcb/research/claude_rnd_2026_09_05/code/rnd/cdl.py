"""Censored-Depth Level-set model (CDL).

Latent: y*(u) = log of the *conduction-side* maximum melt depth, modelled as a
GP with an explicit linear mean in u=(log h, log VX, log LS, ST) (standardized on
the outer training pool, label-free) plus an ARD Matern-3/2 residual and
Gaussian observation noise.

Observations at a queried simulation i (label Y_i, extracted max depth D_i):
    Y_i = 0 (Conduction):  log D_i = y*(u_i) + eps_i,      eps ~ N(0, sn^2)
    Y_i = 1 (Keyhole):     y*(u_i) >= log D*   (right-censored; soft probit scale sc)
Keyhole-side depth values are never used as regression targets (the depth
response jumps and is floor-censored on that side).

Regime posterior (set membership, no Bernoulli link noise):
    pi(u) = P(y*(u) >= log D* | data) = Phi((m(u) - log D*) / sqrt(v(u) + sc^2)).

Inference: Laplace approximation with a mixed likelihood (Gaussian + probit
censoring); hyperparameters by type-II ML (Laplace marginal) with bounds.
"""
from __future__ import annotations
import math
import numpy as np
from scipy.linalg import cholesky, cho_solve, solve_triangular
from scipy.optimize import minimize
from scipy.special import log_ndtr, ndtr
from scipy.stats import norm

LOG2PI = math.log(2 * math.pi)


def matern32_ard(A, B, ls, var, grad=False):
    d = (A[:, None, :] - B[None, :, :]) / ls
    r = np.sqrt(np.maximum((d * d).sum(-1), 1e-300))
    sq3 = math.sqrt(3.0)
    e = np.exp(-sq3 * r)
    K = var * (1 + sq3 * r) * e
    if not grad:
        return K
    # d/d log ls_j : var * 3 r * e * (d_j^2 / r)/r ... = var*3*e*d_j^2
    grads = [var * 3.0 * e * (d[:, :, j] ** 2) for j in range(A.shape[1])]
    return K, grads  # grads are wrt log-lengthscale j; d/d log var = K


class CDL:
    """Mixed-likelihood Laplace GP for one-sided censored depth level sets."""

    def __init__(self, log_dstar: float, sc: float = 0.05, basis_sd: float = 3.0,
                 ls_bounds=(0.05, 20.0), var_bounds=(1e-4, 1.0), noise_bounds=(0.03, 0.3),
                 init=(0.5, 0.05, 0.08), optimize=True, maxiter=150):
        self.log_dstar = float(log_dstar)
        self.sc = float(sc)
        self.basis_sd = float(basis_sd)
        self.ls_bounds = ls_bounds
        self.var_bounds = var_bounds
        self.noise_bounds = noise_bounds
        self.init = init
        self.optimize = optimize
        self.maxiter = maxiter

    # ----- likelihood pieces (log lik, first, second derivative wrt f) -----
    def _lik(self, f, y, t):
        """y: label (1 = censored/KH), t: observed log depth for y==0."""
        ll = np.empty_like(f); g = np.empty_like(f); w = np.empty_like(f)
        c = y == 0
        r = t[c] - f[c]
        ll[c] = -0.5 * r * r / self.sn2 - 0.5 * math.log(2 * math.pi * self.sn2)
        g[c] = r / self.sn2
        w[c] = 1.0 / self.sn2
        k = ~c
        zc = (f[k] - self.log_dstar) / self.sc
        ll[k] = log_ndtr(zc)
        ratio = np.exp(norm.logpdf(zc) - log_ndtr(zc))
        g[k] = ratio / self.sc
        w[k] = (ratio * (zc + ratio)) / (self.sc ** 2)
        return ll, g, np.maximum(w, 1e-12)

    def _kernel(self, A, B, theta, grad=False):
        ls = np.exp(theta[:self.dim]); var = math.exp(theta[self.dim])
        Klin = self.basis_sd ** 2 * (A @ B.T + 1.0)
        if not grad:
            return matern32_ard(A, B, ls, var) + Klin
        K, grads = matern32_ard(A, B, ls, var, grad=True)
        return K + Klin, grads + [K]

    def _mode(self, K, y, t, return_all=False):
        n = len(y); f = np.where(y == 0, t, self.log_dstar + 0.1)  # warm start
        a = np.zeros(n)
        for it in range(200):
            ll, g, w = self._lik(f, y, t)
            sw = np.sqrt(w)
            B = np.eye(n) + sw[:, None] * K * sw[None, :]
            L = cholesky(B, lower=True)
            b = w * f + g
            a = b - sw * cho_solve((L, True), sw * (K @ b))
            f_new = K @ a
            done = np.max(np.abs(f_new - f)) < 1e-8
            f = f_new
            if done:
                break
        ll, g, w = self._lik(f, y, t); sw = np.sqrt(w)
        B = np.eye(n) + sw[:, None] * K * sw[None, :]; L = cholesky(B, lower=True)
        lml = ll.sum() - 0.5 * a @ f - np.log(np.diag(L)).sum()
        if return_all:
            return f, a, w, sw, L, lml
        return lml

    def _objective(self, theta, X, y, t):
        self.sn2 = math.exp(2 * theta[self.dim + 1])
        K = self._kernel(X, X, theta)
        try:
            return -self._mode(K, y, t)
        except np.linalg.LinAlgError:
            return 1e10

    def fit(self, X, y, t):
        X = np.asarray(X, float); y = np.asarray(y, int); t = np.asarray(t, float)
        self.X = X; self.y = y; self.t = t; self.dim = X.shape[1]
        th0 = np.r_[np.log(np.full(self.dim, self.init[0])), math.log(self.init[1]), math.log(self.init[2])]
        bounds = [(math.log(self.ls_bounds[0]), math.log(self.ls_bounds[1]))] * self.dim + \
                 [(math.log(self.var_bounds[0]), math.log(self.var_bounds[1]))] + \
                 [(math.log(self.noise_bounds[0]), math.log(self.noise_bounds[1]))]
        if self.optimize:
            res = minimize(self._objective, th0, args=(X, y, t), method="L-BFGS-B", bounds=bounds,
                           options={"maxiter": self.maxiter})
            self.theta = res.x; self.converged = bool(res.success); self.nfev = res.nfev
        else:
            self.theta = th0; self.converged = True; self.nfev = 0
        self.sn2 = math.exp(2 * self.theta[self.dim + 1])
        self.K = self._kernel(X, X, self.theta)
        self.f, self.alpha, self.w, self.sw, self.L, self.lml = self._mode(self.K, y, t, return_all=True)
        return self

    def latent(self, Xs):
        Xs = np.asarray(Xs, float)
        Ks = self._kernel(self.X, Xs, self.theta)
        m = Ks.T @ self.alpha
        v = solve_triangular(self.L, self.sw[:, None] * Ks, lower=True)
        kss = np.diag(self._kernel(Xs, Xs, self.theta)) if len(Xs) < 400 else np.array([self._kernel(x[None], x[None], self.theta)[0, 0] for x in Xs])
        var = np.maximum(kss - (v * v).sum(0), 1e-12)
        return m, var

    def pi(self, Xs):
        m, v = self.latent(Xs)
        return ndtr((m - self.log_dstar) / np.sqrt(v + self.sc ** 2))

    @property
    def hyper(self):
        return {"ls": np.exp(self.theta[:self.dim]).tolist(), "var": math.exp(self.theta[self.dim]), "sn": math.sqrt(self.sn2)}
