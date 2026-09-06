"""Frozen challenger: M3 (incumbent predictive model) + threshold-variance-reduction
acquisition computed under a frozen auxiliary threshold-surface posterior ("M3 + TV").

Frozen constants (development on the 405 old cases; do not change after the protocol commit):
  T posterior: c = 7.0 (label softness s = 1/c = 0.143 log-h units), s_u = 0.41, ARD Matern-3/2
  length scales (1.7, 30, 30) in standardised (log VX, log LS, ST), s_mu = 3.0, s_beta = 1.0,
  mu0 = mean log h of the revealed rows (label-free).
  Acquisition: A_TV(x) = phi(t)^2 / (Phi(t)(1-Phi(t))(1+v_x)) * sum_{u in R} Cov(g_u, g_x)^2,
  t = m_x / sqrt(1+v_x), R = the whole outer training pool (fixed reference set).
  Selection: argmax over unrevealed training-pool rows; tie-break smallest row index.
Incumbent acquisition: M3 probability margin 1-2|p-0.5| (Phase 1.14 definition).
"""
from __future__ import annotations
import math, sys
from pathlib import Path
import numpy as np
from scipy.special import ndtr
from scipy.stats import norm
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
for p in (HERE, HERE.parent.parent):        # deliverables/code, rnd (for tmodel/core)
    if str(p) not in sys.path: sys.path.insert(0, str(p))
from tmodel import TModel, acq_threshold_variance   # noqa: E402

T_HYPER = dict(c=7.0, s_u=0.41, ls=(1.7, 30.0, 30.0), s_mu=3.0, s_beta=1.0)


def physics_coordinate(P, VX, LS):
    return np.log(P / np.sqrt(VX * LS ** 3))


def context(VX, LS, ST):
    return np.c_[np.log(VX), np.log(LS), np.asarray(ST, float)]


class FrozenThresholdPosterior:
    """T posterior with frozen hyperparameters; used ONLY to score candidates."""

    def __init__(self, logh: np.ndarray, Zraw: np.ndarray, train_pool: np.ndarray):
        self.logh = np.asarray(logh, float); self.train = np.asarray(train_pool, int)
        self.scaler = StandardScaler().fit(Zraw[self.train]); self.Z = self.scaler.transform(Zraw)

    def fit(self, revealed: np.ndarray, labels_revealed: np.ndarray):
        h = T_HYPER; rev = np.asarray(revealed, int)
        m = TModel(mu0=float(self.logh[rev].mean()), s_mu=h["s_mu"], s_beta=h["s_beta"], optimize=False); m.dim = 3
        m.theta = np.r_[math.log(h["c"]), math.log(h["s_u"]), np.log(h["ls"])]
        m.l, m.Z, m.y = self.logh[rev], self.Z[rev], np.asarray(labels_revealed, int)
        m.mean_, m.K = m._build(m.theta, m.l, m.Z)
        m.f, m.alpha, m.w, m.sw, m.L, m.lml = m._mode(m.K, m.mean_, m.y, return_all=True); m.c = h["c"]
        self.model = m; return self

    def tv_scores(self, candidates: np.ndarray) -> np.ndarray:
        ref = self.train; cand = np.asarray(candidates, int); idx = np.r_[ref, cand]
        mm, vv, CC = self.model.latent(self.logh[idx], self.Z[idx], return_cov=True)
        nr = len(ref); C = CC[nr:, :nr]
        return acq_threshold_variance(mm[nr:], vv[nr:], C)

    def margin_scores(self, candidates: np.ndarray) -> np.ndarray:
        cand = np.asarray(candidates, int); p = self.model.p(self.logh[cand], self.Z[cand]); return 1 - 2 * np.abs(p - .5)


def select(candidates: np.ndarray, scores: np.ndarray) -> int:
    """argmax with deterministic tie-break on the smallest row index (repository rule)."""
    cand = np.asarray(candidates, int); order = np.lexsort((cand, -np.asarray(scores, float))); return int(cand[order[0]])


class M3Incumbent:
    """Repository M3 (Phase 1.13/1.14 code) on arrays; labels are supplied for revealed rows only."""

    def __init__(self, x4: np.ndarray, logh: np.ndarray, train_pool: np.ndarray, seed_fn):
        from core import p11, p13   # repository modules
        self.p11, self.p13 = p11, p13
        self.x4, self.logh, self.train = np.asarray(x4, float), np.asarray(logh, float), np.asarray(train_pool, int); self.seed_fn = seed_fn

    def fit(self, revealed: np.ndarray, labels_revealed: np.ndarray, budget: int):
        rev = np.asarray(revealed, int); lab = np.full(len(self.logh), -1, int); lab[rev] = np.asarray(labels_revealed, int)
        assert (lab[rev] >= 0).all() and len(np.unique(lab[rev])) == 2, "M3 needs both classes among revealed rows"
        physics = self.p11.fit_physics_mean(self.logh, lab, rev, self.seed_fn(budget))
        self.fit_ = self.p13.fit_hybrid(self.x4, self.logh, lab, rev, self.train, physics, "M3", 100.0); return self

    def proba(self, rows: np.ndarray) -> np.ndarray:
        rows = np.asarray(rows, int); return self.p13.components(self.fit_, self.x4[rows], self.logh[rows])["probability"]
