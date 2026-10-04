"""Week 15 active level-set paths: random, margin, coverage (Candidate-B-like), BALD, EBR, VSUR.

All policies share the same paid startup (8 maximin points, maximin continuation until both classes) and
the same fixed-hyperparameter Laplace GPC, so differences are attributable to refinement only.
Generators are pluggable so that development (Week 13 generator) and held-out families use one code path.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.spatial import cKDTree
from scipy.spatial.distance import cdist
from sklearn.preprocessing import StandardScaler

from src.week13_synthetic import LaplaceGPC
from src.week13_synthetic_al import maximin_order, q20_flags
from src.week14_noise_acquisition import bald
from src.week15_ebr import knn_graph, latent_mv, lookahead_scores, make_gp

ROOT = Path(__file__).resolve().parents[1]
POLICIES = ("random", "margin", "coverage", "bald", "ebr", "vsur", "ebrd")
BUDGETS = tuple(range(16, 81, 4))
N_REF, K_REF = 400, 8


class DenseEval:
    """Noise-free truth on a uniform dense cloud in unit-box coordinates; NSD/ASSD of predicted boundaries."""

    def __init__(self, z, y, k=8):
        self.z, self.y = z, y
        _, nn = cKDTree(z).query(z, k=k + 1)
        self.nn = nn[:, 1:]
        self.tb = (y[self.nn] != y[:, None]).any(1)
        self.tree = cKDTree(z[self.tb])

    def metrics(self, yhat):
        pb = (yhat[self.nn] != yhat[:, None]).any(1)
        out = {"dense_BA": float((np.mean(yhat[self.y == 1] == 1) + np.mean(yhat[self.y == 0] == 0)) / 2)}
        if not pb.any():
            out.update({"NSD_0.1": 0.0, "NSD_0.05": 0.0, "ASSD": float(np.sqrt(self.z.shape[1]))})
            return out
        a = cKDTree(self.z[pb]).query(self.z[self.tb])[0]
        b = self.tree.query(self.z[pb])[0]
        for t in (.05, .1):
            out[f"NSD_{t}"] = float(((a <= t).sum() + (b <= t).sum()) / (len(a) + len(b)))
        out["ASSD"] = float((a.sum() + b.sum()) / (len(a) + len(b)))
        return out


def coverage_choice(cands, p, s_pool, L, y_pool, zstd):
    """Candidate-B-like rule: rank(uncertainty) + rank(nearest-labelled distance) inside the physics-score band
    from revealed labels (Week 13); without a physics score (s_pool is None) the band is the whole pool."""
    if s_pool is None:
        unc = 1 - 2 * np.abs(p - .5)
        d4 = cdist(zstd[cands], zstd[L]).min(1)
        sc = pd.Series(unc).rank().to_numpy() + pd.Series(d4).rank().to_numpy()
        return int(cands[np.flatnonzero(sc == sc.max())[0]])
    s_rev, y_rev = s_pool[L], y_pool[L]
    lo, hi = sorted((s_rev[y_rev == 1].min(), s_rev[y_rev == 0].max()))
    pad = max(.02, .25 * (hi - lo))
    band = cands[(s_pool[cands] >= lo - pad) & (s_pool[cands] <= hi + pad)]
    if len(band) == 0:
        return None
    unc = 1 - 2 * np.abs(p[np.searchsorted(cands, band)] - .5)
    d4 = cdist(zstd[band], zstd[L]).min(1)
    sc = pd.Series(unc).rank().to_numpy() + pd.Series(d4).rank().to_numpy()
    return int(band[np.flatnonzero(sc == sc.max())[0]])


def run_path(gen, policy, z_pool, u_pool, y_pool, f_pool, s_pool, z_eval, y_eval, dense, Zref, Eref, hyp, start, seed):
    prng = np.random.default_rng(seed)
    q = q20_flags(z_eval, y_eval)
    zstd = StandardScaler().fit_transform(z_pool)
    L = list(start)
    rows = []
    while True:
        b = len(L)
        gp = make_gp(hyp).fit(z_pool[L], y_pool[L])
        if b in BUDGETS:
            yh = (gp.latent_mean(z_eval) > 0).astype(int)
            acq = np.asarray(L[len(start):], int)
            r = {**gen, "policy": policy, "budget": b, "startup_hash": hash(tuple(start)) % 10 ** 9,
                 "q20_accuracy": float(np.mean(yh[q] == y_eval[q])),
                 "BA": float((np.mean(yh[y_eval == 1] == 1) + np.mean(yh[y_eval == 0] == 0)) / 2),
                 "flipped_acquired": float(np.mean(y_pool[acq] != (f_pool[acq] > 0))) if len(acq) else np.nan,
                 "median_abs_latent_acquired": float(np.median(np.abs(f_pool[acq]))) if len(acq) else np.nan}
            r.update(dense.metrics((gp.latent_mean(dense.z) > 0).astype(int)))
            rows.append(r)
        if b >= 80:
            return rows
        cands = np.setdiff1d(np.arange(len(z_pool)), L)
        if policy == "random":
            L.append(int(prng.choice(cands))); continue
        mu, var = latent_mv(gp, z_pool[cands])
        p = 1 / (1 + np.exp(-mu / np.sqrt(1 + np.pi * var / 8)))
        if policy == "margin":
            L.append(int(cands[np.argmin(np.abs(p - .5))]))
        elif policy == "coverage":
            nxt = coverage_choice(cands, p, s_pool, L, y_pool, zstd) if b < 40 else None
            L.append(int(cands[np.argmin(np.abs(p - .5))]) if nxt is None else nxt)
        elif policy == "bald":
            L.append(int(cands[np.argmax(bald(mu, var))]))
        elif policy in ("ebr", "vsur", "ebrd"):
            sc, _ = lookahead_scores(z_pool, y_pool, L, cands, hyp, Zref, Eref, kind={"ebr": "EBR", "vsur": "VSUR", "ebrd": "EBRD"}[policy])
            L.append(int(cands[np.argmax(sc)]))
        else:
            raise ValueError(policy)


def start_design(z_pool, y_pool, seed):
    order = maximin_order(z_pool, np.random.default_rng(seed))
    L = list(order[:8]); k = 8
    while len(set(y_pool[L])) < 2:
        L.append(int(order[k])); k += 1
    return L
