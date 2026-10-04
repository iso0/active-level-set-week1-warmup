"""Week 17 held-out synthetic worlds (HELD-OUT-SYNTHETIC; generator and seeds frozen in PREDICTIONS_AND_FREEZE.md).

Domain: unit box u ∈ [0,1]^4 (P, VX, LS, ST analogue; model coordinates z = u).
Physics score s(u) = u·w_p, w_p = (2.2, −0.8, −1.2, 0) (the Week 13 log-h analogue).  A second direction t
(VX/ST-like, orthogonal to w_p) and a third r (LS-like, orthogonal to both) carry what physics misses.
Standardized projections ŝ, t̂, r̂ (mean 0, sd 1 under the uniform box).  Latent (κ = 3):
  angle θ        f = κ[cos θ ŝ + sin θ t̂ + a(r̂² − 1)] − c          (θ = 0: physics direction exact)
  order-pres.    f = κ[exp(0.8 ŝ)·1.5 + a(r̂² − 1)] − c              (monotone distortion of physics)
  order-viol.    f = κ[|ŝ − 0.5| + a(r̂² − 1)] − c                    (physics order violated: two boundaries)
c is set so that P_u(f > 0) equals the target prevalence.  Labels: clean y = 1[f > 0]; 'local' noise
y = 1[f + κ·1.0·ε > 0] only where t̂ > 0.5; support shift samples the pool (and finite eval set) with
u_1 ~ Beta(2, 5) (dense truth stays uniform).  Truth for NSD/ASSD: noise-free {f = 0} on 8,000 uniform points.
Seeds: [1717, cell index, rep] (pool/eval), dense [1717, 999], reference cloud [15, 99] (Week 15/16 cloud).
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq
from scipy.special import ndtr

from src.week15_al import DenseEval, start_design

W_P = np.array([2.2, -.8, -1.2, 0.])
_t0 = np.array([0., -1., 0., .6])
W_T = _t0 - (_t0 @ W_P) / (W_P @ W_P) * W_P
_r0 = np.array([0., 0., 1., 0.])
W_R = _r0 - (_r0 @ W_P) / (W_P @ W_P) * W_P - (_r0 @ W_T) / (W_T @ W_T) * W_T
KAPPA = 3.0
U_REF = np.random.default_rng([1717, 12345]).random((200000, 4))
STATS = {k: (float((U_REF @ w).mean()), float((U_REF @ w).std())) for k, w in (("s", W_P), ("t", W_T), ("r", W_R))}

CELLS = [
    ("H01_theta0_prev50", dict(kind="angle", theta=0, a=.3, prev=.5, pool=108, noise="clean", support="uniform")),
    ("H02_theta0_prev10", dict(kind="angle", theta=0, a=.3, prev=.1, pool=108, noise="clean", support="uniform")),
    ("H03_theta30_prev50", dict(kind="angle", theta=30, a=.3, prev=.5, pool=108, noise="clean", support="uniform")),
    ("H04_theta30_prev10", dict(kind="angle", theta=30, a=.3, prev=.1, pool=108, noise="clean", support="uniform")),
    ("H05_theta30_prev10_pool324", dict(kind="angle", theta=30, a=.3, prev=.1, pool=324, noise="clean", support="uniform")),
    ("H06_theta30_curved", dict(kind="angle", theta=30, a=1.0, prev=.5, pool=108, noise="clean", support="uniform")),
    ("H07_theta60", dict(kind="angle", theta=60, a=.3, prev=.5, pool=108, noise="clean", support="uniform")),
    ("H08_theta90_physics_useless", dict(kind="angle", theta=90, a=.3, prev=.5, pool=108, noise="clean", support="uniform")),
    ("H09_order_violation", dict(kind="violate", a=.3, prev=.5, pool=108, noise="clean", support="uniform")),
    ("H10_order_preserving", dict(kind="preserve", a=.3, prev=.3, pool=108, noise="clean", support="uniform")),
    ("H11_theta30_local_noise", dict(kind="angle", theta=30, a=.3, prev=.5, pool=108, noise="local", support="uniform")),
    ("H12_theta30_support_shift", dict(kind="angle", theta=30, a=.3, prev=.5, pool=108, noise="clean", support="shift")),
]
CELL_INDEX = {name: i for i, (name, _) in enumerate(CELLS)}


def proj(u, k):
    w = {"s": W_P, "t": W_T, "r": W_R}[k]; m, sd = STATS[k]
    return (np.asarray(u) @ w - m) / sd


def raw_latent(u, cfg):
    s, t, r = proj(u, "s"), proj(u, "t"), proj(u, "r")
    curv = cfg["a"] * (r ** 2 - 1)
    if cfg["kind"] == "angle":
        th = np.deg2rad(cfg["theta"])
        return KAPPA * (np.cos(th) * s + np.sin(th) * t + curv)
    if cfg["kind"] == "preserve":
        return KAPPA * (1.5 * np.exp(.8 * s) + curv)
    if cfg["kind"] == "violate":
        return KAPPA * (np.abs(s - .5) + curv)
    raise ValueError(cfg["kind"])


def offset(cfg):
    g = raw_latent(U_REF[:50000], cfg)
    return float(brentq(lambda c: np.mean(g - c > 0) - cfg["prev"], g.min() - 1, g.max() + 1))


def sample(n, cfg, rng):
    u = rng.random((n, 4))
    if cfg["support"] == "shift":
        u[:, 0] = rng.beta(2, 5, n)
    return u


def build(name, rep):
    cfg = dict(CELLS)[name]; ci = CELL_INDEX[name]
    c0 = offset(cfg)
    f = lambda u: raw_latent(u, cfg) - c0
    rng = np.random.default_rng([1717, ci, rep])
    n = cfg["pool"]; ne = int(round(n / .8))
    up, ue = sample(n, cfg, rng), sample(ne, cfg, rng)
    fp, fe = f(up), f(ue)
    if cfg["noise"] == "local":
        sp_ = np.where(proj(up, "t") > .5, KAPPA * 1.0, 0.0); se_ = np.where(proj(ue, "t") > .5, KAPPA * 1.0, 0.0)
        yp = (fp + sp_ * rng.standard_normal(n) > 0).astype(int); ye = (fe + se_ * rng.standard_normal(ne) > 0).astype(int)
        p_true = np.where(sp_ > 0, ndtr(fp / np.maximum(sp_, 1e-12)), (fp > 0).astype(float))
    else:
        yp, ye = (fp > 0).astype(int), (fe > 0).astype(int); p_true = yp.astype(float)
    ud = np.random.default_rng([1717, 999]).random((8000, 4))
    zref = np.random.default_rng([15, 99]).random((400, 4))
    c = dict(z_pool=up, y_pool=yp, f_pool=fp, z_eval=ue, y_eval=ye, dense=DenseEval(ud, (f(ud) > 0).astype(int)),
             zref=zref, tref=(f(zref) > 0).astype(int), p_true=p_true, phys=lambda z: np.asarray(z) @ W_P,
             start=start_design(up, yp, [1717, rep, 2]), pool=n, cfg=cfg, name=name)
    c["s_pool"] = c["phys"](up)
    return c
