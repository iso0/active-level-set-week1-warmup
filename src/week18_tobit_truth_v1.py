"""FROZEN copy of src/week18_tobit.py at commit e351cb4f, used only to build the T_TOBIT digital-twin truth.

The twin truth must not change when the candidate model code changes (the E2/E3 solver was rewritten in 1ded7f43);
Phase 2 baselines and E2-dev1 were run against this truth.  Do not edit."""
from __future__ import annotations

import numpy as np
from scipy.linalg import cho_solve, cholesky, solve_triangular
from scipy.optimize import minimize
from scipy.special import log_ndtr, ndtr
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

LOG_BOUNDS = np.log(np.array([[1e-3, 1e3], [1e-3, 1e3], [1e-2, 1e2], [1e-2, 1e2], [1e-2, 1e2], [1e-2, 1e2], [1e-4, 1.0]]))


def matern32(A, B, ls):
    d = np.sqrt(np.maximum(((A[:, None, :] - B[None, :, :]) / ls) ** 2, 0).sum(-1)) * np.sqrt(3)
    return (1 + d) * np.exp(-d)


def kern(A, B, th):
    s0, a, ls = np.exp(th[0]), np.exp(th[1]), np.exp(th[2:6])
    return s0 + a * matern32(A, B, ls)


def lik(f, t, kh, u, sig, below=None):
    """log-likelihood, gradient and W = −Hessian (diagonal) for mixed observations:
    exact conduction depth (Gaussian), Keyhole (censored above: g ≥ u), and — if `below` marks them —
    non-Keyhole rows without a depth value (censored below: g < u)."""
    below = np.zeros(len(f), bool) if below is None else below
    g = np.empty_like(f); W = np.empty_like(f); ll = 0.0
    c = ~kh & ~below
    r = t[c] - f[c]
    ll += float(np.sum(-.5 * r ** 2 / sig ** 2 - .5 * np.log(2 * np.pi * sig ** 2)))
    g[c] = r / sig ** 2; W[c] = 1 / sig ** 2
    for mask, sgn in ((kh, 1.0), (below, -1.0)):
        if not mask.any():
            continue
        z = sgn * (f[mask] - u) / sig
        lp = log_ndtr(z); ll += float(lp.sum())
        lam = np.exp(-.5 * z ** 2 - .5 * np.log(2 * np.pi) - lp)            # φ/Φ, stable
        g[mask] = sgn * lam / sig; W[mask] = lam * (z + lam) / sig ** 2
    return ll, g, np.maximum(W, 1e-12)


def mode(K, t, kh, u, sig, iters=200, below=None):
    n = len(t); a = np.zeros(n)
    def psi(a):
        f = K @ a; return lik(f, t, kh, u, sig, below)[0] - .5 * a @ f
    cur = psi(a)
    for _ in range(iters):
        f = K @ a; _, g, W = lik(f, t, kh, u, sig, below); sw = np.sqrt(W)
        L = cholesky(np.eye(n) + sw[:, None] * K * sw[None, :], lower=True)
        b = W * f + g
        d = b - sw * cho_solve((L, True), sw * (K @ b)) - a
        step = 1.0
        while step > 1e-10 and psi(a + step * d) < cur - 1e-12:
            step *= .5
        a = a + step * d; new = psi(a)
        if abs(new - cur) < 1e-11 and step * np.abs(K @ d).max() < 1e-9:
            cur = new; break
        cur = new
    f = K @ a; ll, g, W = lik(f, t, kh, u, sig, below); sw = np.sqrt(W)
    L = cholesky(np.eye(n) + sw[:, None] * K * sw[None, :], lower=True)
    return {"a": a, "f": f, "g": g, "sw": sw, "L": L, "lml": float(cur - np.log(np.diag(L)).sum()),
            "fp": float(np.abs(K @ g - f).max())}


def estimate_u(t, y):
    kh, nk = t[y == 1], t[y == 0]
    if len(kh) and len(nk) and nk.max() < kh.min():
        return .5 * (nk.max() + kh.min())
    if len(kh) and len(nk):
        lr = LogisticRegression(C=1e6, max_iter=5000).fit(t[:, None], y)
        return float(-lr.intercept_[0] / lr.coef_[0, 0])
    return float(np.log(111.0))


class TobitGP:
    def __init__(self, pool_X):
        self.xs = StandardScaler().fit(np.log(pool_X))

    def _z(self, X):
        return self.xs.transform(np.log(X))

    def fit(self, X, depth, y, theta=None, optimize=True):
        y = np.asarray(y).astype(int); has = np.isfinite(depth)
        self.Z = self._z(X); t = np.log(np.where(has, depth, 1.0))
        self.u = estimate_u(t[has], y[has]) if has.any() and len(set(y[has])) == 2 else float(np.log(111.0))
        self.kh = y == 1
        self.below = (y == 0) & ~has                                  # non-Keyhole label without depth: g < u
        self.tc = np.where(self.kh | self.below, np.nan, t - self.u)  # centre at the threshold: boundary is g = 0
        th0 = np.array([0., 0., 0., 0., 0., 0., np.log(.05)]) if theta is None else np.asarray(theta, float)
        def nlml(th):
            th = np.clip(th, LOG_BOUNDS[:, 0], LOG_BOUNDS[:, 1])
            K = kern(self.Z, self.Z, th) + 1e-8 * np.eye(len(t))
            try:
                return -mode(K, np.nan_to_num(self.tc), self.kh, 0.0, np.exp(.5 * th[6]), below=self.below)["lml"]
            except np.linalg.LinAlgError:
                return 1e10
        if optimize:
            r = minimize(nlml, th0, method="L-BFGS-B", bounds=LOG_BOUNDS, options={"maxiter": 100})
            self.theta = r.x
        else:
            self.theta = th0
        self.sig = np.exp(.5 * self.theta[6])
        self.K = kern(self.Z, self.Z, self.theta) + 1e-8 * np.eye(len(t))
        self.m = mode(self.K, np.nan_to_num(self.tc), self.kh, 0.0, self.sig, below=self.below)
        self.mode_fp_ = self.m["fp"]
        return self

    def latent(self, X):
        Zs = self._z(X); Ks = kern(self.Z, Zs, self.theta)
        mu = Ks.T @ self.m["g"]
        V = solve_triangular(self.m["L"], self.m["sw"][:, None] * Ks, lower=True)
        kss = np.exp(self.theta[0]) + np.exp(self.theta[1])
        return mu, np.maximum(kss - (V * V).sum(0), 1e-12)

    def proba(self, X):
        mu, v = self.latent(X)
        return ndtr(mu / np.sqrt(v + self.sig ** 2))
