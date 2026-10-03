"""Week 14 Study 2 model zoo: how should physics enter a rare-regime level-set classifier?

All models take raw inputs X (rows = cases, columns ordered like (P-like, VX-like, LS-like, ST-like)
in a monotone-transformed space), labels y in {0,1}, the physics score s(X) and a sign vector.
They return P(class 1) and hard labels on query inputs.  Inputs are standardized with the
training rows only (signs are preserved by standardization).
"""
from __future__ import annotations

import warnings

import numpy as np
from scipy.special import expit
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, Matern
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src.week14_monotone_gp import MonotoneGPC, virtual_design
from src.week14_order import closure_labels, dominance

MODEL_NAMES = ("H", "M3", "G3", "G3S", "G3C", "GR", "GRS", "MG", "GRC")
CLOSURE_P = (0.001, 0.999)   # probabilities assigned to dominance-implied labels (class 0, class 1)


def closure_override(p, X_train, y_train, X_query, signs):
    """Replace predictions by labels implied by the dominance closure of the training labels.

    Implied 1: some training case with y = 1 is dominated by the query (query is 'higher').
    Implied 0: some training case with y = 0 dominates the query.  Conflicts keep the base model.
    """
    Xall = np.vstack([X_train, X_query])
    D = dominance(Xall, signs)
    lab = closure_labels(D, np.arange(len(X_train)), y_train)[len(X_train):]
    p = np.asarray(p, float).copy()
    p[lab == 1] = np.maximum(p[lab == 1], CLOSURE_P[1])
    p[lab == 0] = np.minimum(p[lab == 0], CLOSURE_P[0])
    return p, lab
NU_FACTOR = 0.1          # probit scale of virtual derivative observations, relative to prior sd of the derivative
MAX_VIRTUAL_POINTS = 150


def _fit_sklearn(kernel, Z, y, seed=0):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return GaussianProcessClassifier(kernel, n_restarts_optimizer=0, random_state=seed).fit(Z, y)


class Fitted:
    def __init__(self, name, predict, info=None):
        self.name, self.predict, self.info = name, predict, info or {}


def fit_model(name, X, y, s, signs, virtual_points=None, seed=0):
    """``name`` may carry variant suffixes: '@O4' uses (P+,VX-,LS-,ST+); '@nu=<f>' sets NU_FACTOR."""
    nu_factor = NU_FACTOR
    if "@" in name:
        base, *mods = name.split("@")
        for mod in mods:
            if mod == "O4":
                signs = np.array([1, -1, -1, 1])
            elif mod.startswith("nu="):
                nu_factor = float(mod[3:])
            else:
                raise ValueError(name)
        out = fit_model_core(base, X, y, s, signs, virtual_points, seed, nu_factor)
        out.name = name
        return out
    return fit_model_core(name, X, y, s, signs, virtual_points, seed, nu_factor)


def fit_model_core(name, X, y, s, signs, virtual_points, seed, nu_factor):
    X, y, s = np.asarray(X, float), np.asarray(y, int), np.asarray(s, float)
    sc = StandardScaler().fit(X)
    Z = sc.transform(X)
    d = X.shape[1]
    if name == "H":
        m = s.mean(); sd = s.std() + 1e-12
        lr = LogisticRegression(C=1e6, max_iter=5000).fit(((s - m) / sd)[:, None], y)
        return Fitted(name, lambda Xq, sq: lr.predict_proba(((np.asarray(sq) - m) / sd)[:, None])[:, 1])
    if name == "M3":
        m = s.mean(); sd = s.std() + 1e-12
        lr = LogisticRegression(C=1e6, max_iter=5000).fit(((s - m) / sd)[:, None], y)
        mean = lambda sq: lr.decision_function(((np.asarray(sq) - m) / sd)[:, None])
        k = ConstantKernel(0.09, (0.05 ** 2, 1.0)) * Matern(length_scale=np.ones(d), length_scale_bounds=(0.01, 100.0), nu=1.5)
        gp = p11.FixedMeanLaplaceGPC(k, optimize=True).fit(Z, y, mean(s))
        return Fitted(name, lambda Xq, sq: gp.predict_proba(sc.transform(Xq), mean(sq))[:, 1],
                      {"var": float(gp.kernel_.k1.constant_value), "ls": np.ravel(gp.kernel_.k2.length_scale).tolist()})
    if name in ("G3", "G3C"):
        k = ConstantKernel(1.0, (1e-3, 1e3)) * Matern(length_scale=np.ones(d), length_scale_bounds=(1e-2, 1e2), nu=1.5)
        g = _fit_sklearn(k, Z, y, seed)
        info = {"var": float(g.kernel_.k1.constant_value), "ls": np.ravel(g.kernel_.k2.length_scale).tolist()}
        base = lambda Xq, sq: g.predict_proba(sc.transform(Xq))[:, 1]
        if name == "G3":
            return Fitted(name, base, info)
        return Fitted(name, lambda Xq, sq: closure_override(base(Xq, sq), X, y, np.asarray(Xq, float), signs)[0], info)
    if name == "G3S":
        Zs = np.c_[Z, (s - s.mean()) / (s.std() + 1e-12)]
        k = ConstantKernel(1.0, (1e-3, 1e3)) * Matern(length_scale=np.ones(d + 1), length_scale_bounds=(1e-2, 1e2), nu=1.5)
        g = _fit_sklearn(k, Zs, y, seed)
        m, sd = s.mean(), s.std() + 1e-12
        return Fitted(name, lambda Xq, sq: g.predict_proba(np.c_[sc.transform(Xq), (np.asarray(sq) - m) / sd])[:, 1],
                      {"var": float(g.kernel_.k1.constant_value), "ls": np.ravel(g.kernel_.k2.length_scale).tolist()})
    if name in ("GR", "GRC", "MG"):
        k = ConstantKernel(1.0, (1e-3, 1e3)) * RBF(length_scale=np.ones(d), length_scale_bounds=(1e-2, 1e2))
        g = _fit_sklearn(k, Z, y, seed)
        var = float(g.kernel_.k1.constant_value)
        ls = np.ravel(g.kernel_.k2.length_scale)
        info = {"var": var, "ls": ls.tolist()}
        base = lambda Xq, sq: g.predict_proba(sc.transform(Xq))[:, 1]
        if name == "GR":
            return Fitted(name, base, info)
        if name == "GRC":
            return Fitted(name, lambda Xq, sq: closure_override(base(Xq, sq), X, y, np.asarray(Xq, float), signs)[0], info)
        # MG: same hyperparameters, plus virtual derivative-sign observations
        vp = Z if virtual_points is None else np.vstack([Z, sc.transform(virtual_points)])
        rng = np.random.default_rng(seed)
        if len(vp) > MAX_VIRTUAL_POINTS:
            vp = vp[rng.choice(len(vp), MAX_VIRTUAL_POINTS, replace=False)]
        V, vd, vs = virtual_design(vp, signs)
        used = np.asarray(signs) != 0
        nu = nu_factor * np.sqrt(var) / np.exp(np.mean(np.log(ls[used])))
        mg = MonotoneGPC(ls, var, nu=nu).fit(Z, y, V, vd, vs)
        info.update({"nu": float(nu), "n_virtual": int(len(V))})
        return Fitted(name, lambda Xq, sq: mg.proba(sc.transform(Xq)), info)
    if name == "GRS":
        Zs = np.c_[Z, (s - s.mean()) / (s.std() + 1e-12)]
        k = ConstantKernel(1.0, (1e-3, 1e3)) * RBF(length_scale=np.ones(d + 1), length_scale_bounds=(1e-2, 1e2))
        g = _fit_sklearn(k, Zs, y, seed)
        m, sd = s.mean(), s.std() + 1e-12
        return Fitted(name, lambda Xq, sq: g.predict_proba(np.c_[sc.transform(Xq), (np.asarray(sq) - m) / sd])[:, 1],
                      {"var": float(g.kernel_.k1.constant_value), "ls": np.ravel(g.kernel_.k2.length_scale).tolist()})
    raise ValueError(name)
