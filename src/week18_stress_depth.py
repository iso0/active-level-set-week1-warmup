"""Week 18 Phase 6 depth stress worlds (HELD-OUT-SYNTHETIC; seeds by round) for depth-observing candidates (E1).

Built on the frozen depth twins (src/week18_twins.py): truth log depth t(z) of T_DEPTH (OLD log-depth GPR) on the
OLD input distribution (pool 324, test 81, dense 6,000), labels y = 1[t ≥ log u(z)].
  SD_NOISE10    observed depth = true depth · exp(0.10 ε) (labels from the true depth)
  SD_NOISE25    same with 0.25
  SD_DRIFT      threshold not constant: log u(z) = log 111 µm + 0.15 (2 z_ST − 1) (±15% across ST), so the label is
                not a single depth level set
  SD_MISSING30  30% of pool and test runs (MCAR, per rep) return the label only (no depth)
  SD_NEWLIKE    T_DEPTH on the NEW-like input distribution (pool 108, test 28; Keyhole-majority, extrapolated depth)
  SD_JUMP       T_TOBIT (Keyhole branch separate, jump at the threshold) on the pooled distribution (pool 433)
Base seed: round 0 (development) 1860, round k: 1860 + 10k; reps 0–7.
"""
from __future__ import annotations

import numpy as np

import src.week18_twins as W
from src.week15_al import DenseEval

WORLDS = ("SD_NOISE10", "SD_NOISE25", "SD_DRIFT", "SD_MISSING30", "SD_NEWLIKE", "SD_JUMP")


def world(name, rep, base):
    wi = WORLDS.index(name)
    rng = np.random.default_rng([base, wi, rep])
    twin, dist, n = ("T_TOBIT", "pooled", 433) if name == "SD_JUMP" else ("T_DEPTH", "NEW" if name == "SD_NEWLIKE" else "OLD", 108 if name == "SD_NEWLIKE" else 324)
    f = W.truth(twin)
    m = max(28, n // 4)
    zp, zt = W.sample(dist, n, rng), W.sample(dist, m, rng)
    zd = W.sample(dist, 6000, np.random.default_rng([base, wi, 999]))
    Z = np.r_[zp, zt]
    def latent(z):
        lat = f(z)
        if name == "SD_DRIFT":
            lat = lat - .15 * (2 * np.asarray(z)[:, 3] - 1)
        return lat
    y = (latent(Z) > 0).astype(int)
    depth = f.depth(Z).astype(float)
    if name in ("SD_NOISE10", "SD_NOISE25"):
        depth = depth * np.exp((.10 if name == "SD_NOISE10" else .25) * rng.standard_normal(len(depth)))
    if name == "SD_MISSING30":
        depth[rng.random(len(depth)) < .30] = np.nan
    te = np.arange(n, n + m)
    from src.external_validation.analysis import boundary_flags
    X = W.to_x(Z)
    q = boundary_flags(X, y, te, np.array([f"s{i:05d}" for i in range(len(y))]), "entire_evaluation_batch")[20] if len(set(y[te])) == 2 else None
    return {"task": name, "repeat": rep, "fold": 0, "block": "S3", "X": X, "y": y, "depth": depth, "pool": np.arange(n), "test": te,
            "prior": np.array([], int), "q20": q, "seed": [base, wi, rep, 3], "dense_X": W.to_x(zd), "dense": DenseEval(zd, (latent(zd) > 0).astype(int))}


def all_depth_stress(round_k=0, reps=range(8)):
    base = 1860 + 10 * round_k
    return [world(w, r, base) for w in WORLDS for r in reps]
