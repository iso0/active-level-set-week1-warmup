"""Week 17 — one code path for every model compared in Weeks 17 (safeguarded Laplace, ML-II, analytic gradients).

All models are logistic GP classifiers  f = m(x) + g(x),  g ~ GP(0, k),  fitted by
`SafeguardedFixedMeanLaplaceGPC` (week9 FixedMeanLaplaceGPC with a backtracking Newton mode, so the ML-II
objective and its GPML-5.1 gradient are evaluated at the true Laplace mode).  Inputs: x4 = [P, VX, LS, ST]
standardized on the (label-free) training pool; h = log P − ½ log VX − 3/2 log LS standardized on the pool.

  G3      m = 0;  k = a² Matérn-3/2 ARD(x4)                       a² ∈ [1e-3, 1e3], ℓ ∈ [1e-2, 1e2]  (historical G3)
  M3      m = H_C(h), C = 1e6 (logistic on revealed rows);  k = r² Matérn ARD(x4), r² ∈ [0.0025, 1]   (historical M3)
  M3_C    as M3 with C = 1 (shrunk plug-in mean)                         [diagnostic]
  M3_free as M3 with r² ∈ [1e-3, 1e3]                                      [diagnostic]
  M3_Cfree C = 1 and r² ∈ [1e-3, 1e3]                                       [diagnostic]
  LT      m = 0;  k = s0² + s1² h h' + a² Matérn ARD(x4): the physics trend is a *Gaussian-prior* linear basis in h
          whose intercept and slope are integrated out and whose prior strength s1² is learned by ML-II
          (explicit basis functions, Rasmussen & Williams §2.7, O'Hagan 1978)   [candidate]
  H       logistic regression on h, C = 1e6 (historical);  H_C1 with C = 1.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
from scipy.special import expit
from sklearn.base import clone
from sklearn.gaussian_process.kernels import ConstantKernel, DotProduct, Hyperparameter, Kernel, Matern
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from src.week17_audit import predictive, safeguarded_mode
from src.week17_audit_impact import SafeguardedFixedMeanLaplaceGPC

warnings.filterwarnings("ignore")
AMP = (1e-3, 1e3)
LEN = (1e-2, 1e2)
RES_CAP = (0.05 ** 2, 1.0)


class Proj(Kernel):
    """Apply `kernel` to the columns `dims` of the input (hyperparameters delegated, gradients exact)."""

    def __init__(self, kernel, dims):
        self.kernel = kernel
        self.dims = dims

    @property
    def hyperparameters(self):
        return [Hyperparameter("kernel__" + h.name, h.value_type, h.bounds, h.n_elements) for h in self.kernel.hyperparameters]

    @property
    def theta(self):
        return self.kernel.theta

    @theta.setter
    def theta(self, theta):
        self.kernel.theta = theta

    @property
    def bounds(self):
        return self.kernel.bounds

    def get_params(self, deep=True):
        p = {"kernel": self.kernel, "dims": self.dims}
        if deep:
            p.update({"kernel__" + k: v for k, v in self.kernel.get_params(deep=True).items()})
        return p

    def __call__(self, X, Y=None, eval_gradient=False):
        X = np.asarray(X)[:, self.dims]
        Y = None if Y is None else np.asarray(Y)[:, self.dims]
        return self.kernel(X, Y, eval_gradient=eval_gradient)

    def diag(self, X):
        return self.kernel.diag(np.asarray(X)[:, self.dims])

    def is_stationary(self):
        return self.kernel.is_stationary()

    def __eq__(self, b):
        return type(self) == type(b) and self.dims == b.dims and self.kernel == b.kernel

    def __repr__(self):
        return f"Proj({self.kernel!r}, {self.dims})"


def matern_ard(var_bounds, init_var=1.0, dims=(0, 1, 2, 3)):
    return ConstantKernel(init_var, var_bounds) * Proj(Matern(np.ones(len(dims)), LEN, nu=1.5), list(dims))


def kernel_for(name):
    if name == "G3":
        return matern_ard(AMP)
    if name in ("M3", "M3_C"):
        return matern_ard(RES_CAP, init_var=1.0)
    if name in ("M3_free", "M3_Cfree"):
        return matern_ard(AMP)
    if name == "LT":
        lin = ConstantKernel(1.0, AMP) * Proj(DotProduct(sigma_0=0.0, sigma_0_bounds="fixed"), [4])
        return ConstantKernel(1.0, AMP) + lin + matern_ard(AMP)
    raise ValueError(name)


PHYS_C = {"M3": 1e6, "M3_free": 1e6, "M3_C": 1.0, "M3_Cfree": 1.0}


@dataclass
class Fitted:
    name: str
    gp: object
    xs: StandardScaler
    hs: StandardScaler
    phys: object        # (scaler, logistic) or None

    def inputs(self, x4, logh):
        return np.c_[self.xs.transform(x4), self.hs.transform(np.asarray(logh)[:, None])]

    def mean(self, logh):
        if self.phys is None:
            return np.zeros(len(logh))
        sc, lr = self.phys
        return lr.decision_function(sc.transform(np.asarray(logh)[:, None]))

    def latent(self, x4, logh):
        X = self.inputs(x4, logh)
        return self.gp.latent_mean_and_variance(X, self.mean(logh))

    def proba(self, x4, logh):
        return self.gp.predict_proba(self.inputs(x4, logh), self.mean(logh))[:, 1]

    def converged(self):
        """Fixed-point error |K(y - pi) - g| of the final (safeguarded) Laplace mode."""
        return float(getattr(self.gp, "mode_fp_", np.nan))


class FittedH:
    def __init__(self, name, sc, lr):
        self.name, self.sc, self.lr = name, sc, lr

    def latent(self, x4, logh):
        return self.lr.decision_function(self.sc.transform(np.asarray(logh)[:, None])), np.zeros(len(logh))

    def proba(self, x4, logh):
        return expit(self.latent(x4, logh)[0])


def fit_physics(logh, y, rev, C):
    sc = StandardScaler().fit(np.asarray(logh)[rev, None])
    lr = LogisticRegression(C=C, solver="lbfgs", max_iter=3000).fit(sc.transform(np.asarray(logh)[rev, None]), np.asarray(y)[rev])
    return sc, lr


def fit(name, x4, logh, y, pool, rev, kernel=None, scalers=None):
    """Fit model `name` on revealed rows `rev`; scalers use the label-free training pool `pool`.
    With `kernel` given, hyperparameters are held fixed at that kernel (used for oracle/look-ahead refits)."""
    x4, logh, y = np.asarray(x4, float), np.asarray(logh, float), np.asarray(y, int)
    rev = np.asarray(rev, int)
    if name in ("H", "H_C1"):
        sc, lr = fit_physics(logh, y, rev, 1e6 if name == "H" else 1.0)
        return FittedH(name, sc, lr)
    xs, hs = scalers if scalers is not None else (StandardScaler().fit(x4[pool]), StandardScaler().fit(logh[pool, None]))
    phys = fit_physics(logh, y, rev, PHYS_C[name]) if name in PHYS_C else None
    f = Fitted(name, None, xs, hs, phys)
    k = kernel_for(name) if kernel is None else kernel
    gp = SafeguardedFixedMeanLaplaceGPC(k, optimize=kernel is None).fit(f.inputs(x4[rev], logh[rev]), y[rev], f.mean(logh[rev]))
    f.gp = gp
    return f


def hyper_summary(f):
    if not isinstance(f, Fitted):
        sc, lr = f.sc, f.lr
        return {"phys_coef": float(lr.coef_[0, 0]), "phys_intercept": float(lr.intercept_[0])}
    out = {"lml": float(f.gp.log_marginal_likelihood_value_)}
    theta = np.exp(f.gp.kernel_.theta); i = 0
    for h in f.gp.kernel_.hyperparameters:
        if h.fixed:
            continue
        vals = theta[i:i + h.n_elements]; i += h.n_elements
        key = "hp_" + h.name.replace("__", ".")
        if h.n_elements == 1:
            out[key] = float(vals[0])
        else:
            for j, v in enumerate(vals):
                out[f"{key}[{j}]"] = float(v)
    if f.phys is not None:
        out.update({"phys_coef": float(f.phys[1].coef_[0, 0]), "phys_intercept": float(f.phys[1].intercept_[0])})
    return out


MODELS = ("G3", "M3", "M3_C", "M3_free", "M3_Cfree", "LT", "H", "H_C1")


def post_moments(f, x4a, ha, x4b=None, hb=None):
    """Latent mean/variance at a, and (optionally) cross-covariance between a and b, under the Laplace posterior."""
    g = f.gp
    Xa = f.inputs(x4a, ha)
    Ka = g.kernel_(g.X_train_, Xa)
    mu = f.mean(ha) + Ka.T @ (g.y_train_ - g.pi_)
    from scipy.linalg import solve_triangular
    Va = solve_triangular(g.L_, g.W_sr_[:, None] * Ka, lower=True)
    var = np.maximum(g.kernel_.diag(Xa) - (Va * Va).sum(0), 1e-12)
    if x4b is None:
        return mu, var
    Xb = f.inputs(x4b, hb); Kb = g.kernel_(g.X_train_, Xb)
    Vb = solve_triangular(g.L_, g.W_sr_[:, None] * Kb, lower=True)
    return mu, var, g.kernel_(Xa, Xb) - Va.T @ Vb


def peer_values(f, x4t, ht, x4c, hc, noise=8 / np.pi):
    """Week 16 PEER (one-step Hamming value on targets t of querying each candidate c) for a Week 17 model."""
    from scipy.special import ndtr
    from src.week15_ebr import bvn_lower
    mt, vt, Ctc = post_moments(f, x4t, ht, x4c, hc)
    mc, vc = post_moments(f, x4c, hc)
    st, sg = np.sqrt(vt), np.sqrt(vc + noise)
    rho = np.clip(Ctc / (st[:, None] * sg[None, :]), -.999999, .999999)
    at, ac = mt / st, mc / sg
    pT, pO = ndtr(at), ndtr(ac)
    A, B = np.broadcast_to(at[:, None], rho.shape), np.broadcast_to(ac[None, :], rho.shape)
    p11 = bvn_lower(A.ravel(), B.ravel(), rho.ravel()).reshape(rho.shape)
    ET = 2 * pT - 1; ETO = 4 * p11 - 2 * pT[:, None] - 2 * pO[None, :] + 1
    return .5 * np.maximum(np.abs(ETO) - np.abs(ET)[:, None], 0).sum(0)
