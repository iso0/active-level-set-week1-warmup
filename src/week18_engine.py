"""Week 18 active-learning engine for real and semi-synthetic tasks (one code path for every arm).

Task (dict): X raw inputs (n×4: P, VX, LS, ST), y binary labels, depth (max depth µm or NaN), pool (paid
candidates), test (evaluation rows), prior (rows whose labels are free prior data, e.g. OLD in transfer; [] if
none), q20 (bool over test or None), seed (list).  Startup: 8 maximin points of the pool + maximin continuation
until both classes are revealed among paid queries (or among prior ∪ paid when a prior exists); every paid query
counts.  Learners (`learner` = (model, hyper)):
  ("G3"|"LT"|"M3", "mlii")   per-step ML-II (week17_models, safeguarded Laplace)
  ("G3", "fixed:<name>")      kernel fixed at a supplied hyperparameter set
  ("GPR_depth", "mlii")       exact GP regression on log max-depth (ARD Matérn-3/2 + white noise, ML-II); class
                              probability P(log depth ≥ log u) = Φ((μ − log u)/σ), u learned from revealed
                              (depth, label) pairs: midpoint of the gap if separable, else 1-D logistic on log depth.
Rules: margin (argmin |p − ½|), random, candB (historical Candidate-B selector), straddle (GPR only:
argmax 1.96σ − |μ − log u|; for GPCs: argmax 1.96 s − |μ|).
"""
from __future__ import annotations

import warnings

import numpy as np
from scipy.special import ndtr
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

import src.week17_models as M
from src.week13_synthetic_al import maximin_order

warnings.filterwarnings("ignore")
RULE_ID = {"random": 1, "margin": 2, "straddle": 3, "candB": 4, "mix": 5}


def logh(X):
    return np.log(X[:, 0]) - .5 * np.log(X[:, 1]) - 1.5 * np.log(X[:, 2])


class DepthGPR:
    """GP regression on log depth with an online depth threshold from revealed (depth, label) pairs."""

    def __init__(self, pool_X):
        self.xs = StandardScaler().fit(np.log(pool_X))

    def fit(self, X, depth, y):
        Z = self.xs.transform(np.log(X)); t = np.log(depth)
        self.mu_t, self.sd_t = t.mean(), t.std() + 1e-9
        k = ConstantKernel(1.0, (1e-3, 1e3)) * Matern(np.ones(4), (1e-2, 1e2), nu=1.5) + WhiteKernel(1e-2, (1e-6, 1.0))
        self.gp = GaussianProcessRegressor(k, normalize_y=False, n_restarts_optimizer=0, random_state=0).fit(Z, (t - self.mu_t) / self.sd_t)
        kh, nk = t[y == 1], t[y == 0]
        if len(kh) and len(nk) and nk.max() < kh.min():
            self.u = .5 * (nk.max() + kh.min())
        elif len(kh) and len(nk):
            lr = LogisticRegression(C=1e6, max_iter=5000).fit(t[:, None], y); self.u = float(-lr.intercept_[0] / lr.coef_[0, 0])
        else:
            self.u = np.log(111.0)
        return self

    def latent(self, X):
        m, s = self.gp.predict(self.xs.transform(np.log(X)), return_std=True)
        mu = m * self.sd_t + self.mu_t
        # remove the white-noise part from the latent sd
        noise = np.exp(self.gp.kernel_.theta[-1]) * self.sd_t ** 2
        var = np.maximum((s * self.sd_t) ** 2 - noise, 1e-12)
        return mu - self.u, var

    def proba(self, X):
        mu, var = self.latent(X)
        return ndtr(mu / np.sqrt(var))


def fit_learner(learner, task, L, fixed=None):
    model, hyper = learner
    X, y = task["X"], task["y"]
    rows = np.r_[task["prior"], L].astype(int)
    if model == "GPR_depth":
        return DepthGPR(X[task["pool"]]).fit(X[rows], task["depth"][rows], y[rows])
    lh = logh(X)
    if hyper == "mlii":
        return M.fit(model, X, lh, y, task["pool"], rows)
    return M.fit(model, X, lh, y, task["pool"], rows, kernel=fixed[hyper.split(":", 1)[1]], scalers=fixed.get("scalers"))


def proba(f, X):
    if isinstance(f, DepthGPR):
        return f.proba(X)
    return f.proba(X, logh(X))


def latent(f, X):
    if isinstance(f, DepthGPR):
        return f.latent(X)
    return f.latent(X, logh(X))


def startup(task):
    X, y, pool = task["X"], task["y"], task["pool"]
    order = pool[maximin_order(X[pool], np.random.default_rng(list(task["seed"]) + [2]))]
    L = list(order[:8]); k = 8
    seen = set(y[task["prior"]]) if len(task["prior"]) else set()
    while len(seen | set(y[L])) < 2:
        L.append(int(order[k])); k += 1
    return L


def choose(rule, f, task, L, rng, b):
    X, y, pool = task["X"], task["y"], task["pool"]
    cands = np.setdiff1d(pool, L)
    if rule == "random":
        return int(rng.choice(cands))
    if rule == "margin":
        return int(cands[np.argmin(np.abs(proba(f, X[cands]) - .5))])
    if rule == "straddle":
        mu, var = latent(f, X[cands])
        return int(cands[np.argmax(1.96 * np.sqrt(var) - np.abs(mu))])
    if rule == "candB":
        from src.external_validation.runner import _select
        nxt, _ = _select("Candidate_B__early8", b, X, logh(X), pool, L, y[L], cands, proba(f, X[cands]), None, f"w18_{task['seed']}")
        return int(nxt)
    raise ValueError(rule)


def run(task, learner, rule, budgets, fixed=None, horizon=None):
    horizon = horizon or max(budgets)
    rng = np.random.default_rng(list(task["seed"]) + [RULE_ID[rule], 11])
    L = startup(task); out = []
    while True:
        b = len(L)
        f = fit_learner(learner, task, L, fixed)
        if b in budgets:
            p = proba(f, task["X"][task["test"]])
            out.append({"budget": b, "startup": None, "p": p, "fp": float(getattr(getattr(f, "gp", None), "mode_fp_", np.nan)) if not isinstance(f, DepthGPR) else 0.0,
                        "u": float(np.exp(f.u)) if isinstance(f, DepthGPR) else np.nan})
        if b >= horizon or len(np.setdiff1d(task["pool"], L)) == 0:
            return out, L
        L.append(choose(rule, f, task, L, rng, b))
