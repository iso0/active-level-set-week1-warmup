"""Week 18 S2 stress worlds (HELD-OUT-SYNTHETIC; seeds by round).

  W17cells  the 12 Week 17 held-out cells (src/week17_heldout.py) re-seeded: pool/eval seed [base, cell, rep]
  POCKET    NEW-like rare pocket: unit box; rare class (label 0) inside one ellipsoidal pocket centred at
            high VX-like coordinate, volume ≈ 9%; pool 108; majority elsewhere; deterministic labels
  TWO_CAMP  two campaigns with a shared boundary shape f(u) = 3[cos30° ŝ + sin30° t̂ + 0.3(r̂² − 1)] − c:
            campaign A pool in u₁ ≤ 0.65 (prior labels, 300 runs, free), campaign B pool in u₁ ≥ 0.45 with level
            shift δ = 0.6 (f_B = f_A + δ), paid pool 108; evaluation on campaign B's region
Base seeds: round 0 (development) 1840, confirmation round k: 1840 + 10k.  Reps 0–7 per round.
"""
from __future__ import annotations

import numpy as np

import src.week17_heldout as HW
from src.week15_al import DenseEval, start_design

W17_CELLS = [name for name, _ in HW.CELLS]


def _task(name, rep, zp, yp, ze, ye, zd, yd, prior=None, yprior=None, seed=None, phys=True):
    X = zp if prior is None else np.r_[prior, zp]
    y = yp if prior is None else np.r_[yprior, yp]
    off = 0 if prior is None else len(prior)
    n = len(zp)
    Xall = np.r_[X, ze]; yall = np.r_[y, ye]
    # engine expects physical-like positive inputs: shift unit box to [1, 2] (log-safe), physics score unaffected
    return {"task": name, "repeat": rep, "fold": 0, "block": "S2", "X": 1.0 + Xall, "y": yall.astype(int), "depth": np.full(len(yall), np.nan),
            "pool": np.arange(off, off + n), "test": np.arange(len(X), len(Xall)), "prior": np.arange(off) if off else np.array([], int),
            "q20": None, "seed": seed, "dense_X": 1.0 + zd, "dense": DenseEval(zd, yd),
            "phys_fn": (lambda X: (np.asarray(X) - 1.0) @ HW.W_P) if phys else None}


def w17_cell(name, rep, base):
    cfg = dict(HW.CELLS)[name]; ci = HW.CELL_INDEX[name]
    c0 = HW.offset(cfg); f = lambda u: HW.raw_latent(u, cfg) - c0
    rng = np.random.default_rng([base, ci, rep]); n = cfg["pool"]; ne = int(round(n / .8))
    up, ue = HW.sample(n, cfg, rng), HW.sample(ne, cfg, rng)
    fp, fe = f(up), f(ue)
    if cfg["noise"] == "local":
        sp_ = np.where(HW.proj(up, "t") > .5, 3.0, 0.0); se_ = np.where(HW.proj(ue, "t") > .5, 3.0, 0.0)
        yp = (fp + sp_ * rng.standard_normal(n) > 0).astype(int); ye = (fe + se_ * rng.standard_normal(ne) > 0).astype(int)
    else:
        yp, ye = (fp > 0).astype(int), (fe > 0).astype(int)
    ud = np.random.default_rng([base, 999]).random((6000, 4))
    return _task(f"S2_{name}", rep, up, yp, ue, ye, ud, (f(ud) > 0).astype(int), seed=[base, ci, rep, 3])


def pocket(rep, base):
    c = np.array([.5, .85, .4, .5]); w = np.array([.35, .18, .35, .45]) * (9 / 5) ** .25
    vol = lambda u: (((u - c) / w) ** 2).sum(1)
    f = lambda u: vol(u) - 1.0            # > 0 outside the pocket → majority class 1 (Keyhole-like)
    rng = np.random.default_rng([base, 50, rep])
    up, ue = rng.random((108, 4)), rng.random((135, 4)); ud = np.random.default_rng([base, 998]).random((6000, 4))
    return _task("S2_POCKET", rep, up, (f(up) > 0).astype(int), ue, (f(ue) > 0).astype(int), ud, (f(ud) > 0).astype(int), seed=[base, 50, rep, 3], phys=False)


def two_campaign(rep, base, delta=.6):
    cfg = dict(kind="angle", theta=30, a=.3, prev=.5, pool=108, noise="clean", support="uniform")
    c0 = HW.offset(cfg); fA = lambda u: HW.raw_latent(u, cfg) - c0; fB = lambda u: fA(u) + delta
    rng = np.random.default_rng([base, 60, rep])
    def box(n, lo, hi):
        u = rng.random((n, 4)); u[:, 0] = lo + (hi - lo) * u[:, 0]; return u
    ua, ub, ue = box(300, 0, .65), box(108, .45, 1), box(135, .45, 1)
    udr = np.random.default_rng([base, 997]).random((6000, 4)); udr[:, 0] = .45 + .55 * udr[:, 0]
    return _task("S2_TWO_CAMP", rep, ub, (fB(ub) > 0).astype(int), ue, (fB(ue) > 0).astype(int), udr, (fB(udr) > 0).astype(int),
                 prior=ua, yprior=(fA(ua) > 0).astype(int), seed=[base, 60, rep, 3])


def two_campaign_noprior(rep, base, delta=.6):
    """Same draws as two_campaign (identical seeds) with the campaign-A prior removed: P-T18-3 check (the binary
    prior should lift ranking quality (AUC) far more than the decision threshold (BA))."""
    t = two_campaign(rep, base, delta)
    off = len(t["prior"])
    keep = np.r_[t["pool"], t["test"]]
    X, y = t["X"][keep], t["y"][keep]; n = len(t["pool"])
    return {**t, "task": "S2_TWO_CAMP_NOPRIOR", "X": X, "y": y, "depth": np.full(len(y), np.nan), "pool": np.arange(n),
            "test": np.arange(n, len(y)), "prior": np.array([], int)}


def all_stress(round_k=0, reps=range(8)):
    base = 1840 + 10 * round_k
    T = [w17_cell(n, r, base) for n in W17_CELLS for r in reps]
    T += [pocket(r, base) for r in reps] + [two_campaign(r, base) for r in reps]
    return T
