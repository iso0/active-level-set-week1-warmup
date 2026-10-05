"""Week 18 candidate E2 — censored ("Tobit") GP for the conduction-depth branch.

Mechanism. has_keyhole = 1[max depth ≥ u], u ≈ 111 µm, and max depth jumps at the regime change.  A conduction
run reveals the conduction-branch depth g(x) exactly (up to numerical noise σ); a Keyhole run reveals only that
the conduction branch has crossed the threshold, g(x) ≥ log u (its own depth belongs to the Keyhole regime).
Model: g ~ GP(0, s0² + a² Matérn-3/2 ARD) on standardized log inputs;
  conduction i:  t_i = log depth_i ~ N(g_i, σ²)
  Keyhole i:     P(g_i + ε ≥ log u) = Φ((g_i − log u)/σ)
Both likelihoods are log-concave, so the Laplace mode is unique; it is found with the safeguarded Newton
(GPML Alg. 3.1 direction + backtracking).  Hyperparameters (s0², a², ℓ1..4, σ²) by ML-II on the Laplace evidence
(L-BFGS-B, numerical gradients).  u is estimated from the revealed (depth, label) pairs: the midpoint of the gap
between the deepest conduction run and the shallowest Keyhole run (log scale), or a 1-D logistic fit if they
overlap.  Classification: P(Keyhole | x) = Φ((μ(x) − log u)/√(v(x) + σ²)).
"""
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


def lik3(f, t, kh, u, sig, below=None):
    """Third derivative of the log-likelihood (diagonal); zero for the Gaussian rows."""
    below = np.zeros(len(f), bool) if below is None else below
    d3 = np.zeros_like(f)
    for mask, sgn in ((kh, 1.0), (below, -1.0)):
        if not mask.any():
            continue
        z = sgn * (f[mask] - u) / sig
        lam = np.exp(-.5 * z ** 2 - .5 * np.log(2 * np.pi) - log_ndtr(z))
        d3[mask] = sgn * lam * ((z + lam) * (z + 2 * lam) - 1) / sig ** 3
    return d3


def mode(K, t, kh, u, sig, iters=200, below=None, a0=None, fp_tol=1e-10):
    """Safeguarded Newton for the Laplace mode (GPML Alg. 3.1 direction + backtracking on Psi(a)).
    Stops when the fixed-point error max|K grad log p(f) - f|, relative to max(1, max(|K| |grad log p|)) (the
    round-off scale: with exact depths grad log p = r / sigma^2 is large), is <= fp_tol, or when it has stopped
    decreasing for 5 iterations (round-off floor, ~1e-9 at n ~ 500; recorded); when backtracking stalls
    on round-off and the full step lowers that error, the full step is taken (Week 18 rule, as for the GPC)."""
    n = len(t); a = np.zeros(n) if a0 is None else np.array(a0, float)
    def psi(a):
        f = K @ a; return lik(f, t, kh, u, sig, below)[0] - .5 * a @ f
    absK = np.abs(K)
    def fperr(a):
        """fixed-point error relative to the magnitude of the terms of K grad log p (round-off scale)"""
        f = K @ a; g = lik(f, t, kh, u, sig, below)[1]
        return float(np.abs(K @ g - f).max() / max(1.0, (absK @ np.abs(g)).max()))
    cur = psi(a)
    if a0 is not None and not np.isfinite(cur):
        a = np.zeros(n); cur = psi(a)
    best, stall = np.inf, 0
    for _ in range(iters):
        e = fperr(a)
        if e <= fp_tol:
            break
        stall = stall + 1 if (e > .9 * best and e < 1e-7) else 0; best = min(best, e)
        if stall >= 5:                     # at the round-off floor: no further progress possible
            break
        f = K @ a; _, g, W = lik(f, t, kh, u, sig, below); sw = np.sqrt(W)
        L = cholesky(np.eye(n) + sw[:, None] * K * sw[None, :], lower=True)
        b = W * f + g
        d = b - sw * cho_solve((L, True), sw * (K @ b)) - a
        step = 1.0
        while step > 1e-10 and psi(a + step * d) < cur - 1e-12:
            step *= .5
        if step <= 1e-10:
            if fperr(a + d) < fperr(a):
                a = a + d; cur = psi(a); continue
            break
        a = a + step * d; cur = psi(a)
    f = K @ a; ll, g, W = lik(f, t, kh, u, sig, below); sw = np.sqrt(W)
    L = cholesky(np.eye(n) + sw[:, None] * K * sw[None, :], lower=True)
    return {"a": a, "f": f, "g": g, "W": W, "sw": sw, "L": L, "lml": float(cur - np.log(np.diag(L)).sum()),
            "fp": fperr(a), "fp_abs": float(np.abs(K @ g - f).max())}


def dkern(Z, th):
    """dK/dtheta_j for the six kernel log-parameters (s0, a, l1..l4)."""
    s0, a, ls = np.exp(th[0]), np.exp(th[1]), np.exp(th[2:6])
    D2 = ((Z[:, None, :] - Z[None, :, :]) / ls) ** 2
    r = np.sqrt(D2.sum(-1)); e = np.exp(-np.sqrt(3) * r)
    out = [np.full((len(Z), len(Z)), s0), a * (1 + np.sqrt(3) * r) * e]
    out += [a * 3 * D2[:, :, k] * e for k in range(4)]
    return out


def lml_grad(Z, th, t, kh, below, a0=None, fix_sig=False, h=1e-4):
    """Laplace log evidence and its gradient (GPML Alg. 5.1 for the kernel parameters, with the implicit term
    +1/2 diag((K^-1 + W)^-1) * d3 log p, sign verified against finite differences in the tests; central difference
    in log sigma^2 for the likelihood scale, warm-started)."""
    K = kern(Z, Z, th) + 1e-8 * np.eye(len(t)); sig = np.exp(.5 * th[6])
    m = mode(K, t, kh, 0.0, sig, below=below, a0=a0)
    sw, L = m["sw"], m["L"]
    R = sw[:, None] * cho_solve((L, True), np.diag(sw))
    C = solve_triangular(L, sw[:, None] * K, lower=True)
    s2 = .5 * (np.diag(K) - (C * C).sum(0)) * lik3(m["f"], t, kh, 0.0, sig, below)
    grad = np.zeros(7)
    for j, Cj in enumerate(dkern(Z, th)):
        s1 = .5 * m["a"] @ Cj @ m["a"] - .5 * np.sum(R * Cj)
        b = Cj @ m["g"]; s3 = b - K @ (R @ b)
        grad[j] = s1 + s2 @ s3
    if not fix_sig:
        vals = []
        for dlt in (h, -h):
            th2 = th.copy(); th2[6] += dlt
            vals.append(mode(K, t, kh, 0.0, np.exp(.5 * th2[6]), below=below, a0=m["a"])["lml"])
        grad[6] = (vals[0] - vals[1]) / (2 * h)
    return m, grad


def estimate_u(t, y):
    kh, nk = t[y == 1], t[y == 0]
    if len(kh) and len(nk) and nk.max() < kh.min():
        return .5 * (nk.max() + kh.min())
    if len(kh) and len(nk):
        lr = LogisticRegression(C=1e6, max_iter=5000).fit(t[:, None], y)
        return float(-lr.intercept_[0] / lr.coef_[0, 0])
    return float(np.log(111.0))


class TobitGP:
    """censor_kh=True: E2 (Keyhole depth censored above the threshold); censor_kh=False: E3 mixed-likelihood depth
    GP (every observed depth exact, both regimes; label-only rows censored on the side given by their label).
    ML-II with analytic kernel gradients (GPML Alg. 5.1) since Week 18 Phase 3 (E2 development runs used the
    earlier numerical-gradient optimizer; same objective)."""

    def __init__(self, pool_X, censor_kh=True):
        self.xs = StandardScaler().fit(np.log(pool_X)); self.censor_kh = censor_kh

    def _z(self, X):
        return self.xs.transform(np.log(X))

    def fit(self, X, depth, y, theta=None, optimize=True):
        y = np.asarray(y).astype(int); has = np.isfinite(depth)
        self.Z = self._z(X); t = np.log(np.where(has, depth, 1.0))
        self.u = estimate_u(t[has], y[has]) if has.any() and len(set(y[has])) == 2 else float(np.log(111.0))
        self.kh = (y == 1) if self.censor_kh else ((y == 1) & ~has)
        self.below = (y == 0) & ~has                                  # non-Keyhole label without depth: g < u
        self.tc = np.where(self.kh | self.below, np.nan, t - self.u)  # centre at the threshold: boundary is g = 0
        exact = ~(self.kh | self.below)
        th0 = np.array([0., 0., 0., 0., 0., 0., np.log(.05)]) if theta is None else np.asarray(theta, float).copy()
        tt = np.nan_to_num(self.tc); fix_sig = not exact.any()        # label-only: sigma and amplitude are confounded
        cache = {"a": None}
        def obj(th):
            th = np.clip(th, LOG_BOUNDS[:, 0], LOG_BOUNDS[:, 1]).copy()
            if fix_sig:
                th[6] = th0[6]
            try:
                m, g = lml_grad(self.Z, th, tt, self.kh, self.below, a0=cache["a"], fix_sig=fix_sig)
            except np.linalg.LinAlgError:
                return 1e10, np.zeros(7)
            cache["a"] = m["a"]
            return -m["lml"], -g
        if optimize:
            r = minimize(obj, th0, jac=True, method="L-BFGS-B", bounds=LOG_BOUNDS, options={"maxiter": 200})
            self.theta = np.clip(r.x, LOG_BOUNDS[:, 0], LOG_BOUNDS[:, 1])
            if fix_sig:
                self.theta[6] = th0[6]
        else:
            self.theta = th0
        self.sig = np.exp(.5 * self.theta[6])
        self.K = kern(self.Z, self.Z, self.theta) + 1e-8 * np.eye(len(t))
        self.m = mode(self.K, tt, self.kh, 0.0, self.sig, below=self.below)
        self.mode_fp_ = self.m["fp"]          # relative fixed-point error (see mode); absolute in mode_fp_abs_
        self.mode_fp_abs_ = self.m["fp_abs"]
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
