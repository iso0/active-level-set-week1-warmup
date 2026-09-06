"""M3R: M3 with a label-noise-robust Stage-2 likelihood  p(y=1|f) = eps + (1-2 eps) sigma(f).
Stage 1 (near-unregularised logistic on standardised log h, frozen) is identical to M3.
Stage 2: ARD Matern-3/2 GP discrepancy on standardised (P,VX,LS,ST), Laplace, ML-II with the
same bounds as M3 (residual sd in [0.05,1], length scales in [0.01,100])."""
import math, numpy as np
from scipy.linalg import cholesky, cho_solve, solve_triangular
from scipy.optimize import minimize
from scipy.special import expit
from cdl import matern32_ard
from core import p11


class M3R:
    def __init__(self, eps=0.05, sd_bounds=(0.05, 1.0), ls_bounds=(0.01, 100.0), init_sd=0.3, init_ls=1.0, optimize=True):
        self.eps = eps; self.sd_bounds = sd_bounds; self.ls_bounds = ls_bounds; self.init = (init_sd, init_ls); self.optimize = optimize

    def _lik(self, f, y):
        s = expit(f); e = self.eps
        p1 = e + (1 - 2 * e) * s; p0 = 1 - p1
        p = np.where(y == 1, p1, p0)
        ll = np.log(p)
        ds = s * (1 - s)                          # d sigma / d f
        dp = (1 - 2 * e) * ds * np.where(y == 1, 1.0, -1.0)
        d2s = ds * (1 - 2 * s)
        d2p = (1 - 2 * e) * d2s * np.where(y == 1, 1.0, -1.0)
        g = dp / p
        w = -(d2p / p - (dp / p) ** 2)
        return ll, g, np.maximum(w, 1e-9)

    def _K(self, A, B, theta):
        return matern32_ard(A, B, np.exp(theta[1:]), math.exp(2 * theta[0]))

    def _mode(self, K, mean, y, return_all=False):
        n = len(y); f = mean.copy(); a = np.zeros(n)
        for it in range(200):
            ll, g, w = self._lik(f, y); sw = np.sqrt(w)
            B = np.eye(n) + sw[:, None] * K * sw[None, :]; L = cholesky(B, lower=True)
            b = w * (f - mean) + g
            a = b - sw * cho_solve((L, True), sw * (K @ b))
            f_new = mean + K @ a; done = np.max(np.abs(f_new - f)) < 1e-8; f = f_new
            if done: break
        ll, g, w = self._lik(f, y); sw = np.sqrt(w)
        B = np.eye(n) + sw[:, None] * K * sw[None, :]; L = cholesky(B, lower=True)
        lml = ll.sum() - 0.5 * a @ (f - mean) - np.log(np.diag(L)).sum()
        return (f, a, w, sw, L, lml) if return_all else lml

    def fit(self, X, mean, y):
        X = np.asarray(X, float); mean = np.asarray(mean, float); y = np.asarray(y, int)
        self.X, self.mean_, self.y = X, mean, y
        th0 = np.r_[math.log(self.init[0]), np.log(np.full(X.shape[1], self.init[1]))]
        bounds = [tuple(np.log(self.sd_bounds))] + [tuple(np.log(self.ls_bounds))] * X.shape[1]
        obj = lambda th: -self._mode(self._K(X, X, th) + 1e-8 * np.eye(len(y)), mean, y)
        if self.optimize:
            res = minimize(obj, th0, method="L-BFGS-B", bounds=bounds, options={"maxiter": 150}); self.theta = res.x
        else:
            self.theta = th0
        self.K = self._K(X, X, self.theta) + 1e-8 * np.eye(len(y))
        self.f, self.alpha, self.w, self.sw, self.L, self.lml = self._mode(self.K, mean, y, return_all=True)
        return self

    def latent(self, Xs, mean_s):
        Ks = self._K(self.X, np.asarray(Xs, float), self.theta)
        m = np.asarray(mean_s, float) + Ks.T @ self.alpha
        V = solve_triangular(self.L, self.sw[:, None] * Ks, lower=True)
        var = np.maximum(math.exp(2 * self.theta[0]) - (V * V).sum(0), 1e-12)
        return m, var

    def proba(self, Xs, mean_s):
        m, v = self.latent(Xs, mean_s)
        # probit-approx integral of logistic (same MacKay-style approximation as sklearn/M3 up to <1e-3)
        return self.eps + (1 - 2 * self.eps) * expit(m / np.sqrt(1 + math.pi * v / 8))
