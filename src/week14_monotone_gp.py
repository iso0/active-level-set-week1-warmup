"""Monotone GP classification with virtual derivative observations (Laplace approximation).

Follows the construction of Riihimaki & Vehtari (AISTATS 2010) — virtual observations of the
sign of partial derivatives with a probit likelihood — but uses a Laplace approximation (both
likelihoods are log-concave, so the joint mode is unique) instead of EP.  Kernel: RBF ARD.

Latent vector theta = [f(X) ; df/dx_{d_v}(V)], zero prior mean.
  labels:   p(y_i | f_i) = sigmoid((2y_i - 1) f_i)
  virtual:  p(s_v | g_v) = Phi(s_v g_v / nu)
"""
from __future__ import annotations

import numpy as np
from scipy.linalg import cho_solve, cholesky, solve_triangular
from scipy.special import expit, log_ndtr, ndtr

SQRT2PI = np.sqrt(2 * np.pi)


def rbf(a, b, ls, var):
    d = (a[:, None, :] - b[None, :, :]) / ls
    return var * np.exp(-.5 * (d ** 2).sum(-1))


def joint_cov(X, V, vdims, ls, var):
    """Covariance of [f(X), g(V)] where g_v = d f / d x_{vdims[v]} at V[v]."""
    ls = np.asarray(ls, float)
    Kff = rbf(X, X, ls, var)
    Kfv = rbf(X, V, ls, var)  # k(x_i, v)
    # d k(x, v) / d v_d = k * (x_d - v_d) / l_d^2
    diff_xv = X[:, None, :] - V[None, :, :]
    Kfg = Kfv * diff_xv[:, np.arange(len(V)), vdims] / ls[vdims] ** 2
    Kvv = rbf(V, V, ls, var)
    dvv = V[:, None, :] - V[None, :, :]          # v - w
    de = dvv[:, :, :][np.arange(len(V))[:, None], np.arange(len(V))[None, :], vdims[:, None]]
    dd = dvv[np.arange(len(V))[:, None], np.arange(len(V))[None, :], vdims[None, :]]
    same = (vdims[:, None] == vdims[None, :]).astype(float)
    Kgg = Kvv * (same / ls[vdims][None, :] ** 2 - de * dd / (ls[vdims][:, None] ** 2 * ls[vdims][None, :] ** 2))
    top = np.hstack([Kff, Kfg])
    bot = np.hstack([Kfg.T, Kgg])
    return np.vstack([top, bot])


def cross_cov(Xs, X, V, vdims, ls, var):
    ls = np.asarray(ls, float)
    k_f = rbf(Xs, X, ls, var)
    kv = rbf(Xs, V, ls, var)
    diff = Xs[:, None, :] - V[None, :, :]
    k_g = kv * diff[:, np.arange(len(V)), vdims] / ls[vdims] ** 2
    return np.hstack([k_f, k_g])


class MonotoneGPC:
    def __init__(self, ls, var, nu=1.0, jitter=1e-6):
        self.ls, self.var, self.nu, self.jitter = np.asarray(ls, float), float(var), float(nu), jitter

    def fit(self, X, y, V=None, vdims=None, vsigns=None, iters=100):
        self.X = np.asarray(X, float)
        self.y = np.asarray(y, int)
        n = len(self.y)
        if V is None or len(V) == 0:
            self.V = np.zeros((0, self.X.shape[1]))
            self.vdims = np.zeros(0, int)
            self.vsigns = np.zeros(0)
        else:
            self.V, self.vdims, self.vsigns = np.asarray(V, float), np.asarray(vdims, int), np.asarray(vsigns, float)
        K = joint_cov(self.X, self.V, self.vdims, self.ls, self.var) if len(self.V) else rbf(self.X, self.X, self.ls, self.var)
        K = K + self.jitter * np.eye(len(K))
        m = len(K)
        theta = np.zeros(m)
        a = np.zeros(m)
        t = 2 * self.y - 1
        obj_old = -np.inf
        for _ in range(iters):
            grad, W = self._lik(theta, n, t)
            sw = np.sqrt(W)
            B = np.eye(m) + sw[:, None] * K * sw[None, :]
            L = cholesky(B, lower=True)
            b = W * theta + grad
            a = b - sw * cho_solve((L, True), sw * (K @ b))
            theta = K @ a
            obj = self._loglik(theta, n, t) - .5 * a @ theta
            if obj - obj_old < 1e-9:
                break
            obj_old = obj
        self.K, self.theta, self.n = K, theta, n
        grad, W = self._lik(theta, n, t)
        self.grad, self.sw = grad, np.sqrt(W)
        self.L = cholesky(np.eye(m) + self.sw[:, None] * K * self.sw[None, :], lower=True)
        self.objective = obj
        return self

    def _loglik(self, theta, n, t):
        f, g = theta[:n], theta[n:]
        return -np.logaddexp(0, -t * f).sum() + log_ndtr(self.vsigns * g / self.nu).sum()

    def _lik(self, theta, n, t):
        f, g = theta[:n], theta[n:]
        pi = expit(f)
        gf = (self.y - pi)
        Wf = pi * (1 - pi)
        z = self.vsigns * g / self.nu
        ratio = np.exp(-.5 * z ** 2 - log_ndtr(z)) / SQRT2PI       # phi(z)/Phi(z)
        gg = self.vsigns * ratio / self.nu
        Wg = (ratio * (z + ratio)) / self.nu ** 2
        return np.r_[gf, gg], np.r_[Wf, Wg]

    def latent(self, Xs):
        ks = cross_cov(np.asarray(Xs, float), self.X, self.V, self.vdims, self.ls, self.var) if len(self.V) else rbf(np.asarray(Xs, float), self.X, self.ls, self.var)
        mu = ks @ self.grad
        v = solve_triangular(self.L, self.sw[:, None] * ks.T, lower=True)
        var = np.maximum(self.var - (v * v).sum(0), 1e-12)
        return mu, var

    def proba(self, Xs):
        mu, var = self.latent(Xs)
        return expit(mu / np.sqrt(1 + np.pi * var / 8))


def virtual_design(points, signs):
    """Virtual derivative observations at ``points`` for every signed coordinate."""
    points = np.asarray(points, float)
    dims = np.nonzero(np.asarray(signs) != 0)[0]
    V = np.repeat(points, len(dims), axis=0)
    vd = np.tile(dims, len(points))
    vs = np.tile(np.asarray(signs)[dims], len(points)).astype(float)
    return V, vd, vs
