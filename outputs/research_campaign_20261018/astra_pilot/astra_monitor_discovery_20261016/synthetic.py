"""Evaluator/oracle module. Never import this module from discovery.py.

Generated truths and memberships are private to this harness, not policy inputs.
No simulator, real monitor cache, held-out label file or network access is used.
"""
from __future__ import annotations
import hashlib
import math
import numpy as np
from scipy.linalg import cho_factor, cho_solve, solve_triangular
from scipy.special import ndtr
from discovery import Observation


class FixedGP:
    """Exact Gaussian conditioning with FIXED Matérn-3/2 covariance.

    Exact means conditional on these specified hyperparameters/likelihood only;
    neither the scientific world nor hyperparameter uncertainty is exact here.
    """
    def __init__(self, length=.28, amplitude=.8, noise=.08, mean=-.4):
        self.length, self.amplitude, self.noise, self.mean = length, amplitude, noise, mean

    def kernel(self, a, b):
        r = np.sqrt(np.maximum(((a[:, None, :]-b[None, :, :])**2).sum(2), 0))
        z = math.sqrt(3)*r/self.length
        return self.amplitude**2*(1+z)*np.exp(-z)

    def fit(self, x, y):
        self.x = np.asarray(x, float).reshape(-1, 4)
        self.y = np.asarray(y, float)
        if not len(y) or not np.isfinite(self.y).all():
            raise ValueError("no valid training response")
        a = self.kernel(self.x, self.x) + np.eye(len(y))*(self.noise**2 + 1e-10)
        self.factor = cho_factor(a, lower=True)
        self.alpha = cho_solve(self.factor, self.y-self.mean)
        return self

    def predict(self, x):
        x = np.asarray(x, float)
        k = self.kernel(self.x, x)
        mu = self.mean+k.T@self.alpha
        v = solve_triangular(self.factor[0], k, lower=True)
        variance = self.amplitude**2-(v*v).sum(0)
        if variance.min() < -1e-7:
            raise ArithmeticError("negative GP variance")
        return mu, np.sqrt(np.maximum(variance, 0))


class SyntheticWorld:
    NAMES = ("island", "null_bad_scale", "island_bad_monitor")
    center = np.array([.72, .65, .35, .65])
    radius = .30

    def __init__(self, name, seed, pool_size=512, eval_size=2048):
        if name not in self.NAMES:
            raise ValueError(name)
        self.name, self.seed = name, seed
        # Feature locations/noise are matched across worlds, and across every arm.
        rng = np.random.default_rng(seed)
        self.x = rng.uniform(size=(pool_size, 4))
        self.eval_x = rng.uniform(size=(eval_size, 4))
        self._f, self._g, self._island, self._boundary = self._truth(self.x)
        self._eval_f, self._eval_g, self._eval_island, self._eval_boundary = self._truth(self.eval_x)
        self._q = self._f + rng.normal(0, .08, pool_size)
        self._aux = self._g + rng.normal(0, .08, pool_size)
        self._eval_q = self._eval_f+rng.normal(0, .08, eval_size)
        self._quality = np.ones(pool_size, bool)
        if name == "island_bad_monitor":
            self._quality[np.arange(pool_size) % 37 == 0] = False
            self._q[~self._quality] = np.nan
        self.reported_sd_multiplier = .15 if name == "null_bad_scale" else 1.0

    def _truth(self, x):
        d = np.linalg.norm(x-self.center, axis=1)
        plane = .18-x[:, 0]
        f = 3*np.maximum(plane, self.radius-d) if self.name != "null_bad_scale" else 3*plane
        island = (d < self.radius) if self.name != "null_bad_scale" else np.zeros(len(x), bool)
        boundary = (np.abs(d-self.radius) <= .04) if self.name != "null_bad_scale" else np.zeros(len(x), bool)
        # Independent-output channel with a different geometry, not a class oracle.
        g = .8*np.sin(2*np.pi*x[:, 1])+.6*(x[:, 2]-.5)+.3*np.cos(2*np.pi*x[:, 3])
        return f, g, island, boundary

    def pay(self, i):
        return Observation(int(i), float(self._q[i]) if self._quality[i] else None,
                           bool(self._quality[i]), "verified" if self._quality[i] else
                           "synthetic nonfinite monitor; paid run retained", int(self._f[i] > 0)), float(self._aux[i])

    def feature_hash(self):
        return hashlib.sha256(self.x.tobytes()+self.eval_x.tobytes()).hexdigest()

    def evaluate(self, mu, sd, paid, aux_mu=None):
        y = self._eval_f > 0
        pred = mu > 0
        p = ndtr(mu/np.maximum(sd, 1e-12))
        recall1 = float(pred[y].mean()) if y.any() else None
        recall0 = float((~pred[~y]).mean()) if (~y).any() else None
        near = np.linalg.norm(self.eval_x[:, None, :]-self.x[list(paid)][None, :, :], axis=2).min(1)
        good_island = [k+1 for k, i in enumerate(paid) if self._island[i] and self._quality[i]]
        err = mu-self._eval_f
        out = {"BA": .5*(recall1+recall0) if recall1 is not None and recall0 is not None else None,
               "recall_positive": recall1, "recall_negative": recall0,
               "error": float((pred != y).mean()), "MAE": float(np.abs(err).mean()),
               "RMSE": float(np.sqrt((err**2).mean())),
               "brier": float(((p-y)**2).mean()),
               "log_loss": float(-np.mean(y*np.log(np.clip(p, 1e-12, 1))+(1-y)*np.log(np.clip(1-p, 1e-12, 1)))),
               "latent_90_coverage": float((np.abs(err) <= 1.6448536269514722*sd).mean()),
               "observation_90_coverage": float((np.abs(mu-self._eval_q) <= 1.6448536269514722*np.hypot(sd, .08*self.reported_sd_multiplier)).mean()),
               "feature_coverage_radius_0.20": float((near <= .20).mean()),
               "first_discovery_query": good_island[0] if good_island else None,
               "third_island_query": good_island[2] if len(good_island) >= 3 else None,
               "paid_island_count": len(good_island),
               "island_recall": float(pred[self._eval_island].mean()) if self._eval_island.any() else None,
               "island_boundary_error": float((pred[self._eval_boundary] != y[self._eval_boundary]).mean()) if self._eval_boundary.any() else None,
               "invalid_paid_count": int(sum(not self._quality[i] for i in paid)),
               "eval_island_n": int(self._eval_island.sum()), "eval_boundary_n": int(self._eval_boundary.sum())}
        out["discovery_target_met"] = bool(self._eval_island.any() and out["error"] <= .10
                                          and out["island_recall"] >= .75
                                          and out["island_boundary_error"] <= .20)
        if aux_mu is not None:
            out["aux_MAE"] = float(np.abs(aux_mu-self._eval_g).mean())
            out["aux_RMSE"] = float(np.sqrt(((aux_mu-self._eval_g)**2).mean()))
            out["regression_target_met"] = bool(out["RMSE"] <= .30 and out["aux_RMSE"] <= .30)
        return out
