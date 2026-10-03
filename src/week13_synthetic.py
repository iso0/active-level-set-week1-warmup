"""Week 13 controlled synthetic level-set benchmark (CONTROLLED METHODOLOGICAL EVIDENCE).

This is not real-data validation.  It isolates mechanisms observed on the
SPH campaigns with a known deterministic boundary:

* a dominant physics-like linear coordinate s(u) (analogue of log h),
* a localized corner deviation where the physics law is locally wrong
  (analogue of the high-P / small-LS / high-VX NEW region),
* campaign shift: an OLD-like campaign over the whole box and a NEW-like
  campaign concentrated in the corner, with severe imbalance.

Coordinates u in [0,1]^4 play the roles (log P, log VX, log LS, ST).
Class 1 ("Keyhole") iff f(u) > 0, deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import cho_solve, cholesky, solve_triangular
from scipy.spatial import cKDTree
from scipy.special import expit

# physics weights mimic the spread of (log P, -0.5 log VX, -1.5 log LS) over the OLD box
W_PHYS = np.array([2.2, -0.8, -1.2, 0.0])
KAPPA = 4.0                                 # latent steepness along s
CORNER = np.array([0.9, 0.95, 0.1, 0.5])    # high P, high VX, small LS
CORNER_SCALE = np.array([0.35, 0.12, 0.35, 10.0])  # sharp along VX, broad elsewhere, ST-free


@dataclass(frozen=True)
class Scenario:
    name: str
    lo: tuple
    hi: tuple
    offset: float          # c in f = KAPPA * (s - c) + r
    amp: float             # corner deviation amplitude A (latent units)

    def sample(self, n, rng):
        lo, hi = np.asarray(self.lo), np.asarray(self.hi)
        return lo + (hi - lo) * rng.random((n, 4))


def physics_score(u):
    return np.asarray(u) @ W_PHYS


def latent(u, sc: Scenario):
    u = np.asarray(u)
    bump = np.exp(-0.5 * (((u - CORNER) / CORNER_SCALE) ** 2).sum(axis=1))
    return KAPPA * (physics_score(u) - sc.offset) - sc.amp * bump


def labels(u, sc):
    return (latent(u, sc) > 0).astype(int)


# --------------------------------------------------------------------------- kernels & GPC
def matern32(a, b, ls, var):
    d = np.sqrt(np.maximum(((a[:, None, :] - b[None, :, :]) / ls) ** 2, 0).sum(-1)) * np.sqrt(3.0)
    return var * (1.0 + d) * np.exp(-d)


class LaplaceGPC:
    """Fixed-hyperparameter logistic Laplace GPC with optional fixed latent mean (GPML Alg. 3.1/3.2)."""

    def __init__(self, ls, var):
        self.ls = np.asarray(ls, float)
        self.var = float(var)

    def fit(self, x, y, mean=None, iters=60):
        self.x = np.asarray(x, float)
        self.y = np.asarray(y, int)
        self.m = np.zeros(len(y)) if mean is None else np.asarray(mean, float)
        K = matern32(self.x, self.x, self.ls, self.var)
        g = np.zeros(len(y))
        old = -np.inf
        for _ in range(iters):
            pi = expit(self.m + g)
            W = pi * (1 - pi)
            sw = np.sqrt(W)
            B = np.eye(len(y)) + sw[:, None] * K * sw[None, :]
            L = cholesky(B, lower=True)
            b = W * g + (self.y - pi)
            a = b - sw * cho_solve((L, True), sw * (K @ b))
            g = K @ a
            lml = -0.5 * a @ g - np.logaddexp(0, -(2 * self.y - 1) * (self.m + g)).sum() - np.log(np.diag(L)).sum()
            if lml - old < 1e-10:
                break
            old = lml
        self.pi = expit(self.m + g)
        self.sw = np.sqrt(self.pi * (1 - self.pi))
        self.L = cholesky(np.eye(len(y)) + self.sw[:, None] * K * self.sw[None, :], lower=True)
        self.resid = self.y - self.pi
        return self

    def latent_mean(self, xs, mean=None):
        ks = matern32(self.x, np.asarray(xs, float), self.ls, self.var)
        mu = ks.T @ self.resid
        return mu if mean is None else mu + mean

    def proba(self, xs, mean=None):
        xs = np.asarray(xs, float)
        ks = matern32(self.x, xs, self.ls, self.var)
        mu = ks.T @ self.resid + (0 if mean is None else mean)
        v = solve_triangular(self.L, self.sw[:, None] * ks, lower=True)
        var = np.maximum(self.var - (v * v).sum(0), 1e-12)
        return expit(mu / np.sqrt(1 + np.pi * var / 8))  # probit-approximation of the averaged predictive


class PhysicsTrend:
    """1-D logistic trend in the physics score fitted to revealed labels (H analogue)."""

    def fit(self, s, y, C=1e6):
        from sklearn.linear_model import LogisticRegression
        self.mu, self.sd = float(np.mean(s)), float(np.std(s) + 1e-12)
        self.lr = LogisticRegression(C=C, max_iter=3000).fit(((s - self.mu) / self.sd)[:, None], y)
        return self

    def latent(self, s):
        return self.lr.decision_function(((np.asarray(s) - self.mu) / self.sd)[:, None])


# --------------------------------------------------------------------------- true boundary geometry
class DenseTruth:
    """Dense uniform reference sample of a scenario's box for surface-type boundary metrics."""

    def __init__(self, sc, n=20000, k=8, seed=0):
        rng = np.random.default_rng(seed)
        self.u = sc.sample(n, rng)
        self.scale = np.asarray(sc.hi) - np.asarray(sc.lo)
        self.z = (self.u - np.asarray(sc.lo)) / self.scale  # unit box for distances
        self.y = labels(self.u, sc)
        tree = cKDTree(self.z)
        _, self.nn = tree.query(self.z, k=k + 1)
        self.nn = self.nn[:, 1:]
        self.true_boundary = self.boundary_points(self.y)
        self.true_tree = cKDTree(self.z[self.true_boundary]) if self.true_boundary.any() else None
        self.diam = float(np.sqrt(4.0))

    def boundary_points(self, yhat):
        return (yhat[self.nn] != yhat[:, None]).any(axis=1)

    def metrics(self, yhat, taus=(0.05, 0.1, 0.2)):
        yhat = np.asarray(yhat, int)
        pb = self.boundary_points(yhat)
        out = {"dense_accuracy": float(np.mean(yhat == self.y)),
               "dense_balanced_accuracy": float((np.mean(yhat[self.y == 1] == 1) + np.mean(yhat[self.y == 0] == 0)) / 2)}
        if not pb.any() or self.true_tree is None:
            out["ASSD"] = self.diam
            for t in taus:
                out[f"NSD_{t}"] = 0.0
            return out
        d_true_to_pred = cKDTree(self.z[pb]).query(self.z[self.true_boundary])[0]
        d_pred_to_true = self.true_tree.query(self.z[pb])[0]
        out["ASSD"] = float((d_true_to_pred.sum() + d_pred_to_true.sum()) / (len(d_true_to_pred) + len(d_pred_to_true)))
        for t in taus:
            out[f"NSD_{t}"] = float(((d_true_to_pred <= t).sum() + (d_pred_to_true <= t).sum()) / (len(d_true_to_pred) + len(d_pred_to_true)))
        return out
