"""Week 9 Phase 1.20 — acquisition search for M3, with a development/confirmation split.

Phases 1.14-1.18B and the R&D packages tried to beat M3's probability margin by re-scoring
the same information (revealed binary labels + M3's posterior).  Under M3 that information
collapses every uncertainty-aware score onto margin.  This phase screens acquisition rules
that bring in structurally different, deployable information, while keeping the predictive
model M3 exactly as in Phase 1.14.

Protocol
    evaluator     M3 (Phase 1.13/1.14), refit on the revealed prefix at every budget
    initial seed  the frozen Week 8.5 16-point design of each outer run
    endpoint      Fold-B1-q20 accuracy AULC over budgets 16-80 (thesis primary) and 16-40
    development   repeats 1-10  (50 runs)  - all screening and design choices
    confirmation  repeats 11-20 (50 runs)  - untouched until the finalists are frozen

Information guard (structural, not by convention)
    A policy receives a State object whose label and depth arrays are MASKED: entries of rows
    that have not been queried are -1 / NaN.  Labels, depths and B1 distances of unqueried or
    held-out rows are never reachable from inside a policy.  Pool INPUTS are label-free and
    available, as in every earlier phase.

Local-only analysis phase; it writes nothing outside its own output directory.
"""
from __future__ import annotations

import argparse
import gzip
import json
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, DotProduct, Matern, WhiteKernel
from sklearn.preprocessing import StandardScaler

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_7_physics_ridge_residual_gp as p17
from src import week9_phase1_8_model_path_decomposition as p18
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase1_20_acquisition_search"
CHECKPOINTS = OUTPUT / "checkpoints"
PHASE18 = ROOT / "outputs" / "week9_phase1_8_model_path_decomposition"

FEATURES = ("P", "VX", "LS", "ST")
BUDGETS = tuple(range(16, 81))
SUBSETS = ("B1_q20", "B1_q30", "full81")
DEV_REPEATS = tuple(range(1, 11))
CONF_REPEATS = tuple(range(11, 21))
EXT_REPEATS = tuple(range(21, 61))          # Protocol amendment 1
CONFIRMATION = CONF_REPEATS + EXT_REPEATS
BOOTSTRAP_DRAWS = 10_000
LENGTH_UPPER = 100.0


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


# ---------------------------------------------------------------- inputs


def load_inputs() -> tuple[pd.DataFrame, list[Any], dict[str, list[int]]]:
    population, specs = p18.load_population_specs()
    table = pd.read_csv(PHASE18 / "tables" / "query_paths.csv.gz")
    a0 = table[table.path.eq("A0")]
    paths = {str(r): g.sort_values("query_order").population_row_index.astype(int).tolist()
             for r, g in a0.groupby("run_id", sort=True)}
    require(len(population) == 405 and int(population.has_keyhole.sum()) == 73, "population gate")
    require(len(specs) == 100, "split gate")
    for spec in specs:
        require(paths[spec.run_id][:16] == w85.initial_design(spec, population), "seed drift")
    extended = w85.build_splits(population, repeats=max(EXT_REPEATS), folds=5)
    for frozen, rebuilt in zip(specs, extended[:100]):
        require(frozen.run_id == rebuilt.run_id and list(frozen.test_indices) == list(rebuilt.test_indices),
                "extended generator does not reproduce the frozen splits")
    specs = list(specs) + extended[100:]
    for spec in extended[100:]:
        paths[spec.run_id] = w85.initial_design(spec, population)   # only the frozen B16 seed is used
    return population, specs, paths


@dataclass
class Arrays:
    x4: np.ndarray          # raw inputs
    logh: np.ndarray
    labels: np.ndarray      # TRUE labels - evaluator only, never handed to a policy
    logdepth: np.ndarray    # TRUE log max depth - masked before reaching a policy
    orth: np.ndarray        # label-free coordinates: log P, log VX, log LS, ST


def build_arrays(population: pd.DataFrame) -> Arrays:
    return Arrays(
        x4=population.loc[:, FEATURES].to_numpy(float),
        logh=p11.log_h_values(population),
        labels=population.has_keyhole.astype(int).to_numpy(),
        logdepth=np.log(pd.to_numeric(population.max_depth_um).to_numpy(float)),
        orth=np.column_stack([np.log(population.P), np.log(population.VX),
                              np.log(population.LS), population.ST.to_numpy(float)]),
    )


# ---------------------------------------------------------------- policy state


@dataclass
class State:
    run_id: str
    budget: int
    revealed: np.ndarray            # queried population rows, in order
    candidates: np.ndarray          # outer training pool minus revealed
    seen_label: np.ndarray          # -1 for unqueried rows
    seen_logdepth: np.ndarray       # NaN for unqueried rows
    x_scaled: np.ndarray            # all rows, scaled on the outer training pool (label-free)
    z_scaled: np.ndarray            # log-input coordinates, scaled on the training pool
    logh: np.ndarray                # label-free
    p_cand: np.ndarray              # M3 probability at candidates
    mean_cand: np.ndarray           # M3 latent mean at candidates
    var_cand: np.ndarray            # M3 latent variance at candidates
    fit: Any                        # the evaluator's M3 fit (revealed labels only)
    rng: np.random.Generator
    x4: np.ndarray = None           # raw inputs (label-free)
    train: np.ndarray = None        # outer training pool (label-free)
    cache: dict = None              # per-run scratch space for label-free precomputation
    leaky_rank: np.ndarray = None   # ONLY populated for LEAKY_ diagnostic policies


def argbest(candidates: np.ndarray, score: np.ndarray) -> int:
    """Maximise score; ties on smallest population row index (Phase 1.14 convention)."""
    order = np.lexsort((np.asarray(candidates, dtype=int), -np.asarray(score, float)))
    return int(np.asarray(candidates, dtype=int)[order[0]])


def revealed_depth_gp(state: State) -> tuple[Any, float, float]:
    """GP regression of log max depth fitted ONLY on queried simulations, plus the depth
    threshold implied by queried labels.  Returns (gp, tau, tau_half_width)."""
    rev = state.revealed
    depth = state.seen_logdepth[rev]
    labels = state.seen_label[rev]
    require(np.isfinite(depth).all() and (labels >= 0).all(), "depth/label mask violated")
    kernel = (ConstantKernel(1.0, (1e-3, 1e3)) * DotProduct(sigma_0=1.0, sigma_0_bounds="fixed")
              + ConstantKernel(0.1, (1e-4, 1e2)) * Matern(length_scale=np.ones(4),
                                                         length_scale_bounds=(0.05, 50.0), nu=2.5)
              + WhiteKernel(1e-3, (1e-6, 1e-1)))
    gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True, n_restarts_optimizer=0,
                                  random_state=p13.seed_u32("depthgp", state.run_id, state.budget))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        gp.fit(state.z_scaled[rev], depth)
    conduction, keyhole = depth[labels == 0], depth[labels == 1]
    low, high = float(conduction.max()), float(keyhole.min())
    return gp, 0.5 * (low + high), 0.5 * abs(high - low)


# ---------------------------------------------------------------- policies


def pol_margin(s: State) -> int:
    return argbest(s.candidates, -np.abs(s.p_cand - 0.5))


def pol_random(s: State) -> int:
    return int(s.rng.choice(s.candidates))


def make_asymmetric(target: float) -> Callable[[State], int]:
    def policy(s: State) -> int:
        return argbest(s.candidates, -np.abs(s.p_cand - target))
    return policy


def pol_band_fill(s: State) -> int:
    """Cover the boundary manifold: among the most uncertain candidates, take the one
    farthest from every revealed point (standardised inputs)."""
    k = max(8, int(np.ceil(0.10 * len(s.candidates))))
    uncertainty = -np.abs(s.p_cand - 0.5)
    band = np.argsort(-uncertainty, kind="stable")[:k]
    xs = s.x_scaled
    dist = np.sqrt(((xs[s.candidates[band]][:, None, :] - xs[s.revealed][None, :, :]) ** 2).sum(-1))
    return argbest(s.candidates[band], dist.min(axis=1))


def pol_depth_straddle(s: State) -> int:
    gp, tau, half = revealed_depth_gp(s)
    mu, sd = gp.predict(s.z_scaled[s.candidates], return_std=True)
    return argbest(s.candidates, 1.96 * np.sqrt(sd ** 2 + half ** 2 / 3) - np.abs(mu - tau))


def pol_depth_x_margin(s: State) -> int:
    gp, tau, half = revealed_depth_gp(s)
    mu, sd = gp.predict(s.z_scaled[s.candidates], return_std=True)
    spread = np.sqrt(sd ** 2 + half ** 2 / 3 + 1e-12)
    depth_near = np.exp(-0.5 * ((mu - tau) / spread) ** 2)
    m3_unc = 1.0 - 2.0 * np.abs(s.p_cand - 0.5)
    return argbest(s.candidates, m3_unc * depth_near + 1e-9 * m3_unc)


def pol_depth_disagree(s: State) -> int:
    gp, tau, half = revealed_depth_gp(s)
    mu, sd = gp.predict(s.z_scaled[s.candidates], return_std=True)
    q = norm.cdf((mu - tau) / np.sqrt(sd ** 2 + half ** 2 / 3 + 1e-12))
    m3_unc = 1.0 - 2.0 * np.abs(s.p_cand - 0.5)
    return argbest(s.candidates, m3_unc * (0.25 + np.abs(q - s.p_cand)))


def pol_local_bracket(s: State) -> int:
    """Contextual bisection in log h.  For each candidate, the k nearest revealed points in
    the context coordinates (log VX, log LS, ST) define a local log-h bracket between the
    highest revealed Conduction and the lowest revealed Keyhole.  Prefer candidates that sit
    inside a wide local bracket, near its midpoint."""
    context = s.z_scaled[:, 1:]
    rev = s.revealed
    labels = s.seen_label[rev]
    k = min(8, len(rev))
    d = np.sqrt(((context[s.candidates][:, None, :] - context[rev][None, :, :]) ** 2).sum(-1))
    nearest = np.argsort(d, axis=1, kind="stable")[:, :k]
    lh = s.logh
    scores = np.empty(len(s.candidates))
    for i, c in enumerate(s.candidates):
        idx = rev[nearest[i]]
        lab = labels[nearest[i]]
        c_top = lh[idx][lab == 0].max() if (lab == 0).any() else lh[rev][labels == 0].max()
        k_bot = lh[idx][lab == 1].min() if (lab == 1).any() else lh[rev][labels == 1].min()
        mid, width = 0.5 * (c_top + k_bot), abs(k_bot - c_top) + 1e-3
        scores[i] = width * np.exp(-np.abs(lh[c] - mid) / width)
    return argbest(s.candidates, scores)


def estimated_band(s: State, pad_fraction: float = 0.25, pad_floor: float = 0.05) -> np.ndarray:
    """Physical log-h band estimated from QUERIED labels only.

    With overlapping revealed classes the band is [lowest revealed Keyhole log h, highest
    revealed Conduction log h]; when they are still separable it is the bracket between them.
    A pad lets the band discover edges it has not yet seen.  Returns a boolean mask over
    s.candidates."""
    rev = s.revealed
    labels = s.seen_label[rev]
    require((labels >= 0).all(), "label mask violated")
    lowest_keyhole = s.logh[rev][labels == 1].min()
    highest_conduction = s.logh[rev][labels == 0].max()
    lo, hi = sorted((lowest_keyhole, highest_conduction))
    pad = max(pad_floor, pad_fraction * (hi - lo))
    lh = s.logh[s.candidates]
    return (lh >= lo - pad) & (lh <= hi + pad)


def make_band_policy(kind: str, pad_fraction: float = 0.25) -> Callable[[State], int]:
    def policy(s: State) -> int:
        mask = estimated_band(s, pad_fraction)
        if mask.sum() == 0:
            return pol_margin(s)
        cand = s.candidates[mask]
        if kind == "random":
            return int(s.rng.choice(cand))
        if kind in ("maximin", "maximin_ctx", "margin_maximin"):
            coords = s.x_scaled if kind != "maximin_ctx" else s.z_scaled[:, 1:]
            d = np.sqrt(((coords[cand][:, None, :] - coords[s.revealed][None, :, :]) ** 2).sum(-1)).min(1)
            if kind == "margin_maximin":
                unc = 1.0 - 2.0 * np.abs(s.p_cand[mask] - 0.5)
                rank = lambda v: np.argsort(np.argsort(v, kind="stable"), kind="stable") / max(1, len(v) - 1)
                return argbest(cand, rank(unc) + rank(d))
            return argbest(cand, d)
        raise ValueError(kind)
    return policy



def _rank01(values: np.ndarray) -> np.ndarray:
    order = np.argsort(np.argsort(np.asarray(values, float), kind="stable"), kind="stable")
    return order / max(1, len(values) - 1)


def acquisition_probability(s: State, length_upper: float) -> np.ndarray:
    """Scoring-only M3-architecture posterior: identical revealed labels, frozen physics mean and
    input scaling, but residual length-scales capped at `length_upper` so no context dimension
    can be switched off.  The evaluator is untouched."""
    rev = s.revealed
    require((s.seen_label[rev] >= 0).all(), "label mask violated")
    kernel = ConstantKernel(p13.INITIAL_RESIDUAL_VARIANCE, p13.RESIDUAL_VARIANCE_BOUNDS) * Matern(
        length_scale=np.ones(4), length_scale_bounds=(p13.PRIMARY_LENGTH_BOUNDS[0], float(length_upper)),
        nu=1.5)
    gp = p11.FixedMeanLaplaceGPC(kernel, optimize=True).fit(
        s.fit.x_scaler.transform(s.x4[rev]), s.seen_label[rev], s.fit.physics.latent(s.logh[rev]))
    cand = s.candidates
    return gp.predict_proba(s.fit.x_scaler.transform(s.x4[cand]), s.fit.physics.latent(s.logh[cand]))[:, 1]


def make_margin_capped(length_upper: float) -> Callable[[State], int]:
    def policy(s: State) -> int:
        return argbest(s.candidates, -np.abs(acquisition_probability(s, length_upper) - 0.5))
    return policy


def pol_info_density(s: State) -> int:
    xs = s.x_scaled[s.candidates]
    density = np.exp(-0.5 * ((xs[:, None, :] - xs[None, :, :]) ** 2).sum(-1)).mean(axis=1)
    return argbest(s.candidates, (1.0 - 2.0 * np.abs(s.p_cand - 0.5)) * density)


def make_cluster_margin(n_clusters: int = 12, top: int = 20) -> Callable[[State], int]:
    def policy(s: State) -> int:
        from sklearn.cluster import KMeans
        key = ("kmeans", n_clusters)
        if key not in s.cache:
            model = KMeans(n_clusters=n_clusters, n_init=10, random_state=p13.seed_u32("kmeans", s.run_id))
            s.cache[key] = dict(zip(s.train.tolist(), model.fit_predict(s.x_scaled[s.train]).tolist()))
        cluster = s.cache[key]
        order = np.argsort(np.abs(s.p_cand - 0.5), kind="stable")[:top]
        counts = np.bincount([cluster[int(r)] for r in s.revealed], minlength=n_clusters)
        cand = s.candidates[order]
        occupancy = np.array([counts[cluster[int(c)]] for c in cand], float)
        return argbest(cand, -occupancy + 1e-3 * (1.0 - 2.0 * np.abs(s.p_cand[order] - 0.5)))
    return policy


def make_schedule(early: Callable[[State], int], switch_budget: int) -> Callable[[State], int]:
    def policy(s: State) -> int:
        return early(s) if s.budget < switch_budget else pol_margin(s)
    return policy



def pol_density_bisect(s: State) -> int:
    """While queried labels are still separable in log h, bisect the (max Conduction, min Keyhole)
    gap at the MEDIAN log h of the candidates inside it rather than at its geometric middle:
    early M3 is a log-h step, so accuracy is gained per candidate mass, not per log-h width.
    Once the classes overlap, fall back to margin."""
    rev = s.revealed
    lab = s.seen_label[rev]
    require((lab >= 0).all(), "label mask violated")
    lh = s.logh
    top_c, low_k = lh[rev][lab == 0].max(), lh[rev][lab == 1].min()
    if top_c < low_k:
        inside = (lh[s.candidates] > top_c) & (lh[s.candidates] < low_k)
        if inside.sum() >= 2:
            cand = s.candidates[inside]
            return argbest(cand, -np.abs(lh[cand] - np.median(lh[cand])))
    return pol_margin(s)

def pol_margin_tempered(s: State) -> int:
    """Scoring-only posterior whose Stage-1 physics logistic is regularised (C=1) instead of the
    near-unregularised C=1e6 of the evaluator, so that the early separable fit does not collapse
    into a hard step; the residual kernel, bounds and input scaling are the evaluator's."""
    rev = s.revealed
    lab = s.seen_label[rev]
    require((lab >= 0).all(), "label mask violated")
    from sklearn.linear_model import LogisticRegression
    scaler = StandardScaler().fit(s.logh[rev, None])
    logistic = LogisticRegression(C=1.0, solver="lbfgs", max_iter=3000).fit(scaler.transform(s.logh[rev, None]), lab)
    latent = lambda rows: logistic.decision_function(scaler.transform(s.logh[rows, None]))
    gp = p11.FixedMeanLaplaceGPC(p13.residual_kernel("M3", LENGTH_UPPER), optimize=True).fit(
        s.fit.x_scaler.transform(s.x4[rev]), lab, latent(rev))
    cand = s.candidates
    p = gp.predict_proba(s.fit.x_scaler.transform(s.x4[cand]), latent(cand))[:, 1]
    return argbest(cand, -np.abs(p - 0.5))


def pol_qbc_bootstrap(s: State, members: int = 15) -> int:
    """Query-by-bagging on the Stage-1 physics logistic: disagreement (variance of P(Keyhole))
    across bootstrap refits on the revealed labels, which spreads over the plausible threshold
    interval when a single separable fit would be a hard step; ties broken by M3 margin."""
    rev = s.revealed
    lab = s.seen_label[rev]
    require((lab >= 0).all(), "label mask violated")
    from sklearn.linear_model import LogisticRegression
    rng = np.random.default_rng(p13.seed_u32("qbc", s.run_id, s.budget))
    cand = s.candidates
    votes = []
    for _ in range(members):
        idx = rng.integers(0, len(rev), len(rev))
        if len(np.unique(lab[idx])) < 2:
            continue
        scaler = StandardScaler().fit(s.logh[rev][idx, None])
        model = LogisticRegression(C=1e6, solver="lbfgs", max_iter=3000).fit(
            scaler.transform(s.logh[rev][idx, None]), lab[idx])
        votes.append(model.predict_proba(scaler.transform(s.logh[cand, None]))[:, 1])
    if len(votes) < 3:
        return pol_margin(s)
    spread = np.var(np.vstack(votes), axis=0)
    return argbest(cand, spread + 1e-6 * (1.0 - 2.0 * np.abs(s.p_cand - 0.5)))



def revealed_misfits(s: State) -> np.ndarray:
    """Queried rows that the CURRENT evaluator fit does not reproduce: the in-sample Laplace
    posterior puts them on the wrong side of 0.5.  Uses only queried labels and the M3 fit."""
    rev = s.revealed
    lab = s.seen_label[rev]
    require((lab >= 0).all(), "label mask violated")
    fitted = s.fit.gp.predict_proba(s.fit.x_scaler.transform(s.x4[rev]),
                                    s.fit.physics.latent(s.logh[rev]))[:, 1]
    return rev[(fitted >= 0.5) != (lab == 1)]


def make_misfit_avoiding_margin(length: float = 0.5, strength: float = 0.8) -> Callable[[State], int]:
    """Margin, down-weighted near queried rows that M3 cannot fit.  Those rows mark local label
    structure a smooth, amplitude-capped discrepancy cannot represent; querying their neighbours
    adds labels M3 cannot use and that pull its global fit (cf. LEAKY_b1_nearest)."""
    def policy(s: State) -> int:
        misfit = revealed_misfits(s)
        unc = 1.0 - 2.0 * np.abs(s.p_cand - 0.5)
        if len(misfit) == 0:
            return argbest(s.candidates, unc)
        xs = s.x_scaled
        d2 = ((xs[s.candidates][:, None, :] - xs[misfit][None, :, :]) ** 2).sum(-1).min(axis=1)
        return argbest(s.candidates, unc * (1.0 - strength * np.exp(-0.5 * d2 / length ** 2)))
    return policy


def make_conflict_avoiding_margin(radius: float = 0.6, strength: float = 0.8) -> Callable[[State], int]:
    """Model-free variant: down-weight candidates near queried rows that already have a queried
    row of the opposite label within `radius` (standardised inputs)."""
    def policy(s: State) -> int:
        rev = s.revealed
        lab = s.seen_label[rev]
        xs = s.x_scaled
        d = np.sqrt(((xs[rev][:, None, :] - xs[rev][None, :, :]) ** 2).sum(-1))
        conflict = rev[((lab[:, None] != lab[None, :]) & (d < radius)).any(axis=1)]
        unc = 1.0 - 2.0 * np.abs(s.p_cand - 0.5)
        if len(conflict) == 0:
            return argbest(s.candidates, unc)
        d2 = ((xs[s.candidates][:, None, :] - xs[conflict][None, :, :]) ** 2).sum(-1).min(axis=1)
        return argbest(s.candidates, unc * (1.0 - strength * np.exp(-0.5 * d2 / (0.5 * radius) ** 2)))
    return policy


def make_band_coverage(coords: str, weight_unc: float = 1.0, pad_fraction: float = 0.25,
                       switch_budget: int = 40) -> Callable[[State], int]:
    """Uncertainty + coverage inside the queried-label band until `switch_budget`, margin after.
    coords: 'x' standardised (P,VX,LS,ST); 'hvx' = (log h, VX), the two directions M3 uses."""
    def policy(s: State) -> int:
        if s.budget >= switch_budget:
            return pol_margin(s)
        mask = estimated_band(s, pad_fraction)
        if mask.sum() == 0:
            return pol_margin(s)
        cand = s.candidates[mask]
        if coords == "x":
            c = s.x_scaled
        else:
            key = ("hvx",)
            if key not in s.cache:
                raw = np.column_stack([s.logh, s.x4[:, 1]])
                s.cache[key] = StandardScaler().fit(raw[s.train]).transform(raw)
            c = s.cache[key]
        dist = np.sqrt(((c[cand][:, None, :] - c[s.revealed][None, :, :]) ** 2).sum(-1)).min(axis=1)
        unc = 1.0 - 2.0 * np.abs(s.p_cand[mask] - 0.5)
        return argbest(cand, weight_unc * _rank01(unc) + _rank01(dist))
    return policy


def make_bisect_then_coverage(switch_budget: int = 40) -> Callable[[State], int]:
    """Three phases of the same rule: while queried labels are separable in log h, density-weighted
    bisection of the gap; once they overlap, uncertainty + coverage inside the band; from
    `switch_budget`, plain margin."""
    coverage = make_band_coverage("x", switch_budget=switch_budget)
    def policy(s: State) -> int:
        rev = s.revealed
        lab = s.seen_label[rev]
        if s.logh[rev][lab == 0].max() < s.logh[rev][lab == 1].min():
            return pol_density_bisect(s)
        return coverage(s)
    return policy


def make_band_strata(bins: int = 5, switch_budget: int = 40) -> Callable[[State], int]:
    """Stratified overlap profiling: split the queried-label band into equal-count log-h bins of the
    candidates, take the bin holding the fewest queried rows, and inside it the most uncertain
    candidate; plain margin from `switch_budget`."""
    def policy(s: State) -> int:
        if s.budget >= switch_budget:
            return pol_margin(s)
        mask = estimated_band(s)
        if mask.sum() < bins:
            return pol_margin(s)
        cand = s.candidates[mask]
        lh = s.logh[cand]
        edges = np.quantile(lh, np.linspace(0, 1, bins + 1))
        cand_bin = np.clip(np.searchsorted(edges, lh, side="right") - 1, 0, bins - 1)
        rev_lh = s.logh[s.revealed]
        inside = (rev_lh >= edges[0]) & (rev_lh <= edges[-1])
        rev_bin = np.clip(np.searchsorted(edges, rev_lh[inside], side="right") - 1, 0, bins - 1)
        occupancy = np.bincount(rev_bin, minlength=bins)
        unc = 1.0 - 2.0 * np.abs(s.p_cand[mask] - 0.5)
        return argbest(cand, -occupancy[cand_bin] + 1e-3 * unc)
    return policy


def depth_false_position(s: State, guard: float = 0.15) -> int | None:
    """Regula-falsi step on the log-h bracket, using the continuous depth of QUERIED simulations.

    While queried labels are separable in log h, the threshold lies in (highest Conduction, lowest
    Keyhole).  Bisection uses only the signs at the bracket ends; false position also uses how deep
    the melt pools there were.  log(max depth) is close to linear in log h, so a least-squares line
    through the queried simulations locates where depth crosses the queried-label depth threshold.
    The step is kept a `guard` fraction away from either end (Illinois-style anti-stalling).
    Returns None when the queried labels already overlap in log h."""
    rev = s.revealed
    lab = s.seen_label[rev]
    depth = s.seen_logdepth[rev]
    require((lab >= 0).all() and np.isfinite(depth).all(), "label/depth mask violated")
    lh = s.logh
    top_c, low_k = lh[rev][lab == 0].max(), lh[rev][lab == 1].min()
    if top_c >= low_k:
        return None
    inside = (lh[s.candidates] > top_c) & (lh[s.candidates] < low_k)
    if inside.sum() < 1:
        return None
    tau = 0.5 * (depth[lab == 0].max() + depth[lab == 1].min())
    slope, intercept = np.polyfit(lh[rev], depth, 1)
    width = low_k - top_c
    target = (tau - intercept) / slope if slope > 1e-9 else top_c + 0.5 * width
    target = float(np.clip(target, top_c + guard * width, low_k - guard * width))
    cand = s.candidates[inside]
    return argbest(cand, -np.abs(lh[cand] - target))


def make_falsi(then: str, switch_budget: int = 40) -> Callable[[State], int]:
    coverage = make_band_coverage("x", switch_budget=switch_budget)
    def policy(s: State) -> int:
        chosen = depth_false_position(s)
        if chosen is not None:
            return chosen
        return coverage(s) if then == "coverage" else pol_margin(s)
    return policy


def make_coverage_then_misfit(switch_budget: int = 40, coords: str = "x",
                              pad_fraction: float = 0.25) -> Callable[[State], int]:
    early = make_band_coverage(coords, pad_fraction=pad_fraction, switch_budget=switch_budget)
    late = make_misfit_avoiding_margin()
    def policy(s: State) -> int:
        return early(s) if s.budget < switch_budget else late(s)
    return policy


def pol_leaky_rank(s: State) -> int:
    """DIAGNOSTIC ONLY - uses labels of unqueried rows through s.leaky_rank. Never a finalist."""
    require(s.leaky_rank is not None, "leaky rank missing")
    return argbest(s.candidates, -s.leaky_rank[s.candidates])


POLICIES: dict[str, Callable[[State], int]] = {
    "band_random": make_band_policy("random"),
    "band_maximin": make_band_policy("maximin"),
    "band_maximin_ctx": make_band_policy("maximin_ctx"),
    "band_margin_maximin": make_band_policy("margin_maximin"),
    "band_random_pad0": make_band_policy("random", 0.0),
    "margin": pol_margin,
    "random": pol_random,
    "asym35": make_asymmetric(0.35),
    "asym25": make_asymmetric(0.25),
    "asym65": make_asymmetric(0.65),
    "band_fill": pol_band_fill,
    "depth_straddle": pol_depth_straddle,
    "depth_x_margin": pol_depth_x_margin,
    "depth_disagree": pol_depth_disagree,
    "local_bracket": pol_local_bracket,
    "margin_cap3": make_margin_capped(3.0),
    "margin_cap10": make_margin_capped(10.0),
    "info_density": pol_info_density,
    "cluster_margin": make_cluster_margin(),
    "sched_bmm_B32": make_schedule(make_band_policy("margin_maximin"), 32),
    "sched_bmm_B40": make_schedule(make_band_policy("margin_maximin"), 40),
    "sched_bmaximin_B40": make_schedule(make_band_policy("maximin"), 40),
    "density_bisect": pol_density_bisect,
    "margin_tempered": pol_margin_tempered,
    "qbc_bootstrap": pol_qbc_bootstrap,
    "misfit_margin": make_misfit_avoiding_margin(),
    "misfit_margin_l1": make_misfit_avoiding_margin(length=1.0),
    "conflict_margin": make_conflict_avoiding_margin(),
    "cov_hvx_B40": make_band_coverage("hvx"),
    "cov_x_w2_B40": make_band_coverage("x", weight_unc=2.0),
    "cov_x_pad50_B40": make_band_coverage("x", pad_fraction=0.5),
    "cov_x_B32": make_band_coverage("x", switch_budget=32),
    "cov_then_misfit_B40": make_coverage_then_misfit(40),
    "cov_pad50_then_misfit_B40": make_coverage_then_misfit(40, pad_fraction=0.5),
    "cov_hvx_then_misfit_B40": make_coverage_then_misfit(40, coords="hvx"),
    "bisect_cov_B40": make_bisect_then_coverage(40),
    "strata_B40": make_band_strata(),
    "falsi_margin": make_falsi("margin"),
    "falsi_cov_B40": make_falsi("coverage"),
    "sched_qbc_B40": make_schedule(pol_qbc_bootstrap, 40),
    "LEAKY_b1_nearest": pol_leaky_rank,
    "LEAKY_trueband_random": pol_leaky_rank,
}


# ---------------------------------------------------------------- one run of one policy


def checkpoint_path(policy: str, run_id: str) -> Path:
    return CHECKPOINTS / policy / f"{run_id}.json.gz"



def leaky_ordering(policy: str, spec: Any, population: pd.DataFrame, arrays: Arrays,
                   distances: np.ndarray) -> np.ndarray:
    """DIAGNOSTIC orderings that deliberately use labels of unqueried rows (never finalists).

    LEAKY_b1_nearest       training-pool rows by B1 distance computed from the TRAINING-pool labels
                           only (the training-pool analogue of q20; test labels are not used)
    LEAKY_trueband_random  rows inside the physical log-h band implied by all training-pool labels,
                           in a seeded random order (the Phase 1.20-follow-up NESTED 'BAND' sequence)
    Lower value = queried earlier."""
    from scipy.spatial import distance as sdist
    train = np.asarray(spec.train_indices, dtype=int)
    labels = arrays.labels
    rank = np.full(len(population), np.inf)
    if policy == "LEAKY_b1_nearest":
        z = StandardScaler().fit(arrays.x4[train]).transform(arrays.x4[train])
        d = sdist.cdist(z, z)
        opposite = labels[train][:, None] != labels[train][None, :]
        rank[train] = np.where(opposite, d, np.inf).min(axis=1)
    elif policy == "LEAKY_trueband_random":
        lh = arrays.logh[train]
        lo = lh[labels[train] == 1].min()
        hi = lh[labels[train] == 0].max()
        inside = (lh >= lo) & (lh <= hi)
        rng = np.random.default_rng(p13.seed_u32("trueband", spec.run_id))
        rank[train] = np.where(inside, rng.random(len(train)), 1.0 + rng.random(len(train)))
    else:
        raise ValueError(policy)
    return rank

def run_policy_spec(policy: str, spec: Any, seed_path: Sequence[int], population: pd.DataFrame,
                    arrays: Arrays, distances: np.ndarray) -> dict[str, Any]:
    destination = checkpoint_path(policy, spec.run_id)
    if destination.is_file():
        payload = json.loads(gzip.decompress(destination.read_bytes()).decode())
        if payload.get("complete") and payload.get("policy") == policy:
            return {"run_id": spec.run_id, "reused": True}

    select = POLICIES[policy]
    train = np.asarray(spec.train_indices, dtype=int)
    test = np.asarray(spec.test_indices, dtype=int)
    flags = p17.subset_flags(spec, population, distances)
    x_scaler = StandardScaler().fit(arrays.x4[train])
    z_scaler = StandardScaler().fit(arrays.orth[train])
    x_scaled = x_scaler.transform(arrays.x4)
    z_scaled = z_scaler.transform(arrays.orth)
    n = len(population)

    queried = list(map(int, seed_path[:16]))
    metrics: list[dict[str, Any]] = []
    cache: dict = {}
    leaky_rank = None
    if policy.startswith("LEAKY_"):
        leaky_rank = leaky_ordering(policy, spec, population, arrays, distances)
    for budget in BUDGETS:
        require(len(queried) == budget and len(set(queried)) == budget, f"prefix drift {policy}")
        revealed = np.asarray(queried, dtype=int)
        physics = p11.fit_physics_mean(arrays.logh, arrays.labels, revealed,
                                       p13.seed_u32("shared_physics", spec.run_id, budget))
        fit = p13.fit_hybrid(arrays.x4, arrays.logh, arrays.labels, revealed, train, physics,
                             "M3", LENGTH_UPPER)
        probability = p13.components(fit, arrays.x4[test], arrays.logh[test])["probability"]
        for subset in SUBSETS:
            flag = flags[subset]
            metrics.append({"policy": policy, "run_id": spec.run_id, "repeat": spec.repeat,
                            "fold": spec.fold, "budget": budget, "subset": subset,
                            **p17.metric_values(arrays.labels[test][flag], probability[flag])})
        if budget == 80:
            break

        candidates = np.setdiff1d(train, revealed, assume_unique=False)
        comp = p13.components(fit, arrays.x4[candidates], arrays.logh[candidates])
        seen_label = np.full(n, -1, dtype=int)
        seen_label[revealed] = arrays.labels[revealed]
        seen_depth = np.full(n, np.nan)
        seen_depth[revealed] = arrays.logdepth[revealed]
        state = State(run_id=spec.run_id, budget=budget, revealed=revealed, candidates=candidates,
                      seen_label=seen_label, seen_logdepth=seen_depth, x_scaled=x_scaled,
                      z_scaled=z_scaled, logh=arrays.logh, p_cand=comp["probability"],
                      mean_cand=comp["final_latent"], var_cand=comp["latent_variance"], fit=fit,
                      rng=np.random.default_rng(p13.seed_u32("random", spec.run_id, budget)),
                      x4=arrays.x4, train=train, cache=cache,
                      leaky_rank=leaky_rank if policy.startswith("LEAKY_") else None)
        chosen = select(state)
        require(chosen in set(candidates.tolist()), f"invalid acquisition by {policy}")
        queried.append(chosen)

    require(len(queried) == 80, "trajectory completeness")
    destination.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps({"complete": True, "policy": policy, "run_id": spec.run_id,
                       "queried_indices": queried, "metrics": metrics}, default=float).encode()
    destination.write_bytes(gzip.compress(blob, compresslevel=6, mtime=0))
    return {"run_id": spec.run_id, "reused": False}


def run(policies: Sequence[str], repeats: Sequence[int], workers: int) -> None:
    population, specs, a0 = load_inputs()
    arrays = build_arrays(population)
    distances = w85.b1_distance(population)
    chosen_specs = [s for s in specs if s.repeat in set(repeats)]
    for policy in policies:
        require(policy in POLICIES, f"unknown policy {policy}")
        started = time.time()
        results = Parallel(n_jobs=workers, verbose=0)(
            delayed(run_policy_spec)(policy, spec, a0[spec.run_id], population, arrays, distances)
            for spec in chosen_specs)
        reused = sum(r["reused"] for r in results)
        print(f"  {policy:<18} runs={len(results)} reused={reused} {time.time() - started:7.1f}s",
              flush=True)


# ---------------------------------------------------------------- analysis


def load_metrics(policy: str, repeats: Sequence[int]) -> pd.DataFrame:
    rows = []
    for path in sorted((CHECKPOINTS / policy).glob("*.json.gz")):
        payload = json.loads(gzip.decompress(path.read_bytes()).decode())
        if payload["metrics"][0]["repeat"] in set(repeats):
            rows.extend(payload["metrics"])
    return pd.DataFrame(rows)


def window_aulc(metrics: pd.DataFrame, lo: int, hi: int, metric: str = "accuracy",
                subset: str = "B1_q20") -> pd.Series:
    frame = metrics[(metrics.subset == subset) & metrics.budget.between(lo, hi)]
    values = {}
    for run_id, group in frame.groupby("run_id"):
        ordered = group.sort_values("budget")
        require(len(ordered) == hi - lo + 1, f"window drift {run_id}")
        values[run_id] = float(np.trapezoid(ordered[metric], ordered.budget) / (hi - lo))
    return pd.Series(values)


def repeat_block_contrast(a: pd.Series, b: pd.Series, repeat_of: dict[str, int], key: str) -> dict:
    shared = a.index.intersection(b.index)
    diff = (a[shared] - b[shared]).groupby(lambda r: repeat_of[r]).mean().sort_index()
    values = diff.to_numpy(float)
    rng = np.random.default_rng(p13.seed_u32("bootstrap", key))
    draws = values[rng.integers(0, len(values), size=(BOOTSTRAP_DRAWS, len(values)))].mean(axis=1)
    return {"mean": float(values.mean()), "lo": float(np.quantile(draws, 0.025)),
            "hi": float(np.quantile(draws, 0.975)), "positive_blocks": int((values > 0).sum()),
            "blocks": int(len(values))}


def summarise(policies: Sequence[str], repeats: Sequence[int], control: str = "margin") -> pd.DataFrame:
    population, specs, _ = load_inputs()
    repeat_of = {s.run_id: s.repeat for s in specs}
    base = load_metrics(control, repeats)
    rows = []
    windows = ((16, 80), (16, 40), (41, 80))
    base_w = {w: window_aulc(base, *w) for w in windows}
    for policy in policies:
        m = load_metrics(policy, repeats)
        if m.empty:
            continue
        rec = {"policy": policy, "runs": m.run_id.nunique()}
        for w in windows:
            series = window_aulc(m, *w)
            rec[f"AULC_{w[0]}_{w[1]}"] = float(series.mean())
            if policy != control:
                c = repeat_block_contrast(series, base_w[w], repeat_of, f"{policy}|{control}|{w}")
                rec[f"d_{w[0]}_{w[1]}"] = c["mean"]
                rec[f"ci_{w[0]}_{w[1]}"] = f"[{c['lo']:+.4f}, {c['hi']:+.4f}]"
                rec[f"pos_{w[0]}_{w[1]}"] = f"{c['positive_blocks']}/{c['blocks']}"
        b40 = m[(m.budget == 40) & (m.subset == "B1_q20")].keyhole_recall.mean()
        rec["B40_q20_KH_recall"] = float(b40)
        rows.append(rec)
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policies", nargs="+", default=["margin"])
    parser.add_argument("--repeats", choices=("dev", "conf", "ext", "confirmation", "all"), default="dev")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    repeats = {"dev": DEV_REPEATS, "conf": CONF_REPEATS, "ext": EXT_REPEATS, "confirmation": CONFIRMATION,
               "all": DEV_REPEATS + CONF_REPEATS}[args.repeats]
    if args.summary:
        pd.set_option("display.width", 250)
        print(summarise(args.policies, repeats).to_string(index=False, float_format=lambda v: f"{v:.4f}"))
        return
    run(args.policies, repeats, args.workers)


if __name__ == "__main__":
    main()
