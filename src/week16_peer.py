"""Week 16 — PEER: exact one-step query value for weighted Hamming targets under a Gaussian latent posterior.

Lemma (user-supplied, proved in WEEK16_REPORT.md §0).  For a binary target T ∈ {±1} and a binary
observation O ∈ {±1}, the Bayes error for T after observing O is
        e(T | O) = (1 − max(|E T|, |E[T O]|)) / 2,
because the four decision rules (always +, always −, T = O, T = −O) have errors (1 ∓ E T)/2 and
(1 ∓ E[T O])/2 and the Bayes rule picks the best one per value of O, which is the best of the four.
Hence the exact one-step value of querying j for the target set {T_i} with weights w_i is
        V(j) = ½ Σ_i w_i (|E[T_i O_j]| − |E T_i|)_+ .

Model.  Laplace GPC posterior f ~ N(μ, Σ); targets T_i = sign f_i; observation O_j = sign(f_j + η_j) with
η_j ~ N(0, 8/π) (logistic link ≈ probit).  Then E T_i = 2Φ(μ_i/s_i) − 1 and
E[T_i O_j] = 4 P(f_i > 0, g_j > 0) − (1 + E T_i) − (1 + E O_j) + 1, g_j = f_j + η_j, a bivariate-normal
orthant.  No refits.
"""
from __future__ import annotations

import numpy as np
from scipy.linalg import cho_solve, cholesky, solve_triangular
from scipy.special import expit, ndtr

from src.week13_synthetic import LaplaceGPC, matern32
from src.week15_ebr import bvn_lower

NOISE_VAR = 8.0 / np.pi


def bayes_error_after(ET, ETO):
    return (1 - np.maximum(np.abs(ET), np.abs(ETO))) / 2


class GaussPost:
    """Latent Gaussian posterior of a fitted LaplaceGPC (optionally with a pointwise prior-mean function)."""

    def __init__(self, gp: LaplaceGPC, mean_fn=None):
        self.gp = gp
        self.mean_fn = mean_fn if mean_fn is not None else (lambda Z: np.full(len(Z), getattr(gp, "m0", 0.0)))

    def _V(self, Z):
        ks = matern32(self.gp.x, Z, self.gp.ls, self.gp.var)
        return ks, solve_triangular(self.gp.L, self.gp.sw[:, None] * ks, lower=True)

    def mean_var(self, Z):
        ks, V = self._V(Z)
        mu = ks.T @ self.gp.resid + self.mean_fn(Z)
        return mu, np.maximum(self.gp.var - (V * V).sum(0), 1e-12)

    def cross_cov(self, Z1, Z2):
        _, V1 = self._V(Z1); _, V2 = self._V(Z2)
        return matern32(Z1, Z2, self.gp.ls, self.gp.var) - V1.T @ V2

    def latent_mean(self, Z):
        return matern32(self.gp.x, Z, self.gp.ls, self.gp.var).T @ self.gp.resid + self.mean_fn(Z)

    def proba(self, Z):
        mu, var = self.mean_var(Z)
        return expit(mu / np.sqrt(1 + np.pi * var / 8))


class RobustLaplaceGPC(LaplaceGPC):
    """LaplaceGPC whose Newton iteration (GPML Alg. 3.1) is safeguarded by backtracking on the Laplace objective
    Psi(a) = -1/2 a'Ka + sum log sigma((2y-1)(m + Ka)).  Week 16 found that the undamped Week 13 iteration can
    oscillate and then stops at an overshoot (e.g. gpworld m0 = -4, var 25); where the old iteration converged,
    both reach the same mode.  Attributes are identical to LaplaceGPC, plus `converged` and `fp_err`."""

    def fit(self, x, y, mean=None, iters=200, tol=1e-10):
        self.x = np.asarray(x, float); self.y = np.asarray(y, int)
        self.m = np.zeros(len(y)) if mean is None else np.asarray(mean, float)
        K = matern32(self.x, self.x, self.ls, self.var)
        s = 2 * self.y - 1
        psi = lambda a: -.5 * a @ K @ a - np.logaddexp(0, -s * (self.m + K @ a)).sum()
        a = np.zeros(len(y)); cur = psi(a)
        for _ in range(iters):
            g = K @ a
            pi = expit(self.m + g); W = pi * (1 - pi); sw = np.sqrt(W)
            Lc = cholesky(np.eye(len(y)) + sw[:, None] * K * sw[None, :], lower=True)
            b = W * g + (self.y - pi)
            a_new = b - sw * cho_solve((Lc, True), sw * (K @ b))
            d, t = a_new - a, 1.0
            while t > 1e-8:
                cand = psi(a + t * d)
                if cand >= cur - 1e-12:
                    break
                t *= .5
            a = a + t * d
            new = psi(a)
            if abs(new - cur) < tol and t * np.abs(K @ d).max() < 1e-8:
                cur = new
                break
            cur = new
        g = K @ a
        self.pi = expit(self.m + g)
        self.sw = np.sqrt(self.pi * (1 - self.pi))
        self.L = cholesky(np.eye(len(y)) + self.sw[:, None] * K * self.sw[None, :], lower=True)
        self.resid = self.y - self.pi
        self.fp_err = float(np.abs(K @ self.resid - g).max())
        self.converged = self.fp_err < 1e-6
        return self


def mode_gap(gp: LaplaceGPC):
    """max over training inputs of |latent deviation of `gp` - latent deviation at the safeguarded mode|.
    (A logit-based fixed-point check is unusable when the prior mean saturates pi to 0/1 in floating point.)"""
    ref = RobustLaplaceGPC(gp.ls, gp.var).fit(gp.x, gp.y, mean=gp.m)
    K = matern32(gp.x, gp.x, gp.ls, gp.var)
    return float(np.abs(K @ gp.resid - K @ ref.resid).max())


fixed_point_error = mode_gap


def laplace_lml(gp: LaplaceGPC):
    """Laplace approximation to log p(y | X) at the fitted mode (GPML eq. 3.32)."""
    K = matern32(gp.x, gp.x, gp.ls, gp.var)
    a = gp.resid
    f = gp.m + K @ a
    return float(-.5 * a @ K @ a - np.logaddexp(0, -(2 * gp.y - 1) * f).sum() - np.log(np.diag(gp.L)).sum())


class Model:
    """Fixed-kernel Laplace GPC with a prior-mean rule.

    mean="const"  : constant m0 (0 unless given; reproduces week15 make_gp exactly)
    mean="ml2"    : constant m0 chosen per fit by maximizing the Laplace marginal likelihood (kernel fixed)
    mean="physics": m(z) = b0 + b1 * s(z), s a physics score, (b0, b1) by L2-logistic regression (C = 1) of the
                    labelled set on standardized s (M3-type: physics trend plus GP discrepancy)
    """

    def __init__(self, ls, var, mean="const", m0=0.0, phys=None, name=None, robust=True):
        self.ls, self.var, self.mean, self.m0, self.phys = np.asarray(ls, float), float(var), mean, float(m0), phys
        self.name = name or mean
        self.gpc = RobustLaplaceGPC if robust else LaplaceGPC

    @classmethod
    def from_hyp(cls, hyp, **kw):
        return cls(hyp["ls"], hyp["var"], m0=hyp.get("m0", 0.0), **kw)

    def fit(self, x, y):
        x = np.asarray(x, float); y = np.asarray(y, int)
        if self.mean == "const":
            mf = (lambda m: lambda Z: np.full(len(Z), m))(self.m0)
        elif self.mean == "ml2":
            from scipy.optimize import minimize_scalar
            nl = lambda m: -laplace_lml(self.gpc(self.ls, self.var).fit(x, y, mean=np.full(len(y), m)))
            m = float(minimize_scalar(nl, bounds=(-10, 10), method="bounded", options={"xatol": .02}).x)
            mf = (lambda m: lambda Z: np.full(len(Z), m))(m)
        elif self.mean == "physics":
            from sklearn.linear_model import LogisticRegression
            s = self.phys(x); mu_s, sd_s = s.mean(), s.std() + 1e-12
            if len(set(y)) < 2:
                mf = lambda Z: np.zeros(len(Z))
            else:
                lr = LogisticRegression(C=1.0, max_iter=2000).fit(((s - mu_s) / sd_s)[:, None], y)
                b0, b1 = float(lr.intercept_[0]), float(lr.coef_[0, 0])
                mf = lambda Z: b0 + b1 * (self.phys(Z) - mu_s) / sd_s
        else:
            raise ValueError(self.mean)
        gp = self.gpc(self.ls, self.var).fit(x, y, mean=mf(x))
        return GaussPost(gp, mf)


def expectations(post: GaussPost, Zt, Zc):
    """E T_i (targets), E O_j (candidates) and E[T_i O_j] matrix (targets x candidates)."""
    mt, vt = post.mean_var(Zt)
    mc, vc = post.mean_var(Zc)
    C = post.cross_cov(Zt, Zc)
    st, sg = np.sqrt(vt), np.sqrt(vc + NOISE_VAR)
    rho = C / (st[:, None] * sg[None, :])
    at, ac = mt / st, mc / sg
    pT, pO = ndtr(at), ndtr(ac)
    # P(f_i > 0, g_j > 0) = P(-f_i < 0, -g_j < 0) = Phi2(a_t, a_c; rho)
    A, B = np.broadcast_to(at[:, None], C.shape), np.broadcast_to(ac[None, :], C.shape)
    p11 = bvn_lower(A.ravel(), B.ravel(), rho.ravel()).reshape(C.shape)
    ET = 2 * pT - 1
    EO = 2 * pO - 1
    ETO = 4 * p11 - 2 * pT[:, None] - 2 * pO[None, :] + 1
    return ET, EO, ETO


def peer_values(post: GaussPost, Zt, Zc, w=None):
    ET, _, ETO = expectations(post, Zt, Zc)
    w = np.ones(len(Zt)) if w is None else np.asarray(w, float)
    return .5 * (w[:, None] * np.maximum(np.abs(ETO) - np.abs(ET)[:, None], 0)).sum(0)


def peer_values_mc(post: GaussPost, Zt, Zc, n=40000, seed=0):
    """Monte Carlo check: sample (f_targets, f_c, eta_c) jointly and compute Bayes errors before/after."""
    rng = np.random.default_rng(seed)
    Z = np.vstack([Zt, Zc])
    mu, _ = post.mean_var(Z)
    S = post.cross_cov(Z, Z) + 1e-9 * np.eye(len(Z))
    F = mu + rng.standard_normal((n, len(Z))) @ np.linalg.cholesky(S).T
    T = np.sign(F[:, :len(Zt)])
    out = []
    for j in range(len(Zc)):
        O = np.sign(F[:, len(Zt) + j] + np.sqrt(NOISE_VAR) * rng.standard_normal(n))
        before = (1 - np.abs(T.mean(0))) / 2
        after = np.zeros(len(Zt))
        for o in (-1, 1):
            m = O == o
            if m.any():
                after += m.mean() * (1 - np.abs(T[m].mean(0))) / 2
        out.append(float((before - after).sum()))
    return np.asarray(out)
