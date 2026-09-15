"""Acquisition rules: which unlabelled pool point to query next.

Every rule works on arrays the caller computed from a surrogate (latent
``mu``/``sigma`` of a regressor, ``p_plus`` = P(label = +1) of a classifier,
scaled or standardised coordinates for distances) and returns a pool index plus
a metadata dict.  Families: GPR pool rules (Weeks 1-3, boundary ``mu = 0``),
Week-4 GPR heuristics, classifier rules (margin, entropy, gated diversity,
uncertainty x repulsion shortlist- or pool-normalised, the Phase 6 thesis rule,
Week 9 variants), continuous max-depth rules with an online threshold and the
Phase 7 hybrids.  Tie-breaks are frozen: ``np.lexsort((indices, -scores))[0]``
(largest score, then smallest row index) where the archive used it, plain
``np.argmax`` (first position) where the archive used that.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np
from scipy.spatial import distance as _distance
from sklearn.gaussian_process import GaussianProcessRegressor

from alse.io import require, stable_seed

Array = np.ndarray

# --- frozen constants ----------------------------------------------------------

STRADDLE_KAPPA = 1.96  # frozen: acquisition_rules.py::straddle_scores, week7_phase6::STRADDLE_KAPPA
QUADRATURE_NODES = 24  # frozen: acquisition_rules.py::expected_feasibility_scores
SIGMA_FLOOR = 1e-12  # frozen: acquisition_rules.py::expected_feasibility_scores
DIVERSIFIED_ALPHA = 0.25  # frozen: week4_02_diversified_straddle.py::DIVERSIFIED_ALPHA
GATE_FRACTION = 0.10  # frozen: week4_03 / week4_06 / week7_phase6 *_GATE_FRACTION
MIN_SHORTLIST_SIZE = 25  # frozen: week4_03 / week4_06 / week7_phase6 *_MIN_SHORTLIST_SIZE
DIVERSITY_BETA = 0.50  # frozen: week4_03::BOUNDARY_GATED_BETA, week4_06::CLASSIFIER_DIVERSITY_BETA
REPULSION_BANDWIDTH = 0.15  # frozen: week4_06 / week4_08 / week7_phase6::CLASSIFIER_REPULSION_BANDWIDTH
LOOKAHEAD_SHORTLIST_SIZE = 30  # frozen: week4_04::LOOKAHEAD_SHORTLIST_SIZE
LOOKAHEAD_PROBABILITY_EPS = 1e-9  # frozen: week4_04::LOOKAHEAD_PROBABILITY_EPS
HYBRID_GATE_FRACTION = 0.20  # frozen: week7_phase7::GATE_FRACTION
RANK_BINARY_WEIGHT = 0.50  # frozen: week7_phase7::RANK_BINARY_WEIGHT
RANK_DEPTH_WEIGHT = 0.50  # frozen: week7_phase7::RANK_DEPTH_WEIGHT
REPULSION_SCALE_GRID = (0.25, 0.5, 1.0, 2.0, 4.0)  # frozen: week9_phase1_16::C_GRID
HYBRID_GATE = "hybrid_binary_gate20_max_depth_straddle"  # frozen: week7_phase7::M3_GATE
HYBRID_FUSION = "hybrid_equal_rank_fusion"  # frozen: week7_phase7::M4_FUSION

# Seed namespaces.  These literals are RNG salts baked into every archived
# randomized-straddle draw and random-baseline path; never rename them.  The
# value says whether the key carries a benchmark part:
#   False -> sha256(f"{seed}:{method}:{salt}")            = stable_seed(seed, method, salt)
#   True  -> sha256(f"{seed}:{benchmark}:{method}:{salt}") = stable_seed(seed, benchmark, method, salt)
RNG_SALTS: dict[str, bool] = {
    "week2": False,  # frozen: acquisition_rules.py::rng_for_method (Branin S1)
    "week3_4d": False,  # frozen: week3_4d_benchmark_comparison.py::rng_for_week3_method (superseded)
    "week3_4d_ackley": False,  # frozen: week3_4d_named_benchmark_comparison.py::rng_for_week3_named_method
    "week5": True,  # frozen: week4_02/03/04/05::rng_for_experiment_method (new Week-4 GPR rules)
    "week6_classifier": True,  # frozen: week4_06::rng_for_experiment_method (all classifier rules)
    "week7": True,  # frozen: week4_08::rng_for_method (Hartmann4 / SUR arms)
    "week7_1": True,  # frozen: week4_09::stable_rng (Bernoulli SUR validation)
}

# frozen: acquisition_rules.py::METHOD_ORDER / METHOD_DESCRIPTIONS
METHOD_ORDER = ("random", "smallest_abs_mu", "straddle", "randomized_straddle", "expected_feasibility")
METHOD_DESCRIPTIONS = {
    "random": "Uniformly random unlabelled pool point; floor baseline.",
    "smallest_abs_mu": "Choose the point closest to the current boundary: argmin |mu|.",
    "straddle": "Choose largest 1.96*sigma - |mu|: near boundary and uncertain.",
    "randomized_straddle": "Draw one beta ~ chi-square(df=2) per step and choose largest sqrt(beta)*sigma - |mu|.",
    "expected_feasibility": (
        "Contour-focused expected-improvement-style score "
        "E[max((1.96*sigma)^2 - Y^2, 0)] for Y ~ Normal(mu, sigma^2)."
    ),
}


@dataclass
class AcquisitionChoice:
    """One selected pool index plus metadata (acquisition_rules.py::AcquisitionChoice)."""

    index: int
    metadata: dict[str, Any]


# --- shared helpers ----------------------------------------------------------------


def rng_for_method(
    seed: int, method: str, salt: str = "week2", benchmark: str | None = None
) -> np.random.Generator:
    """``default_rng(sha256(':'-joined key)[:8] LE mod 2**32)``; key grammar per ``RNG_SALTS``.
    frozen: acquisition_rules.py::rng_for_method and the salted variants in ``RNG_SALTS``"""
    require(salt in RNG_SALTS, f"Unknown RNG salt: {salt}")
    if RNG_SALTS[salt]:
        require(benchmark is not None, f"RNG salt {salt!r} needs a benchmark name")
        return np.random.default_rng(stable_seed(seed, benchmark, method, salt))
    return np.random.default_rng(stable_seed(seed, method, salt))


def rng_for_benchmark_method(seed: int, method: str, benchmark: str, salt: str) -> np.random.Generator:
    """Week-4 GPR dispatch: the five original rules keep their Week 2 ('branin') /
    Week 3 ('ackley') streams; every other rule uses the benchmark-bearing ``salt``.
    frozen: week4_02/03/04/05::rng_for_experiment_method ('week5'), week4_08::rng_for_method ('week7')"""
    if benchmark == "branin" and method in METHOD_ORDER:
        return rng_for_method(seed, method, "week2")
    if benchmark == "ackley" and method in METHOD_ORDER:
        return rng_for_method(seed, method, "week3_4d_ackley")
    return rng_for_method(seed, method, salt, benchmark)


def argmax_position(candidates: Array, scores: Array) -> int:
    """Position of the largest score; ties -> smallest candidate index.
    frozen: week4_06::deterministic_argmax, week7_phase6::deterministic_argmax"""
    order = np.lexsort((np.asarray(candidates, dtype=int), -np.asarray(scores, dtype=float)))
    return int(order[0])


def argmax_index(candidates: Array, scores: Array) -> int:
    """Candidate *value* at the largest finite score; ties -> smallest candidate.
    frozen: week9_phase1_5_h_physics_confirmation.py::deterministic_argmax"""
    candidates = np.asarray(candidates, dtype=int)
    scores = np.asarray(scores, dtype=float)
    require(len(candidates) == len(scores) and len(scores) > 0, "invalid acquisition score vector")
    require(np.isfinite(scores).all(), "non-finite acquisition scores")
    return int(candidates[np.lexsort((candidates, -scores))[0]])


def normalize_scores_week4(values: Array) -> Array:
    """Min-max to [0, 1]; all zeros when ``max <= min + 1e-12``.
    frozen: week4_02/03/04/06/08::normalize_scores (synthetic lineage)"""
    values = np.asarray(values, dtype=float)
    low, high = float(values.min()), float(values.max())
    if high <= low + 1e-12:
        return np.zeros_like(values)
    return (values - low) / (high - low)


def normalize_scores(scores: Array) -> Array:
    """Min-max to [0, 1]; all zeros when the span is ``<= 1e-15``.
    frozen: week7_phase6_real_data_boundary_active_level_set.py::normalize_scores"""
    scores = np.asarray(scores, dtype=float)
    span = float(np.ptp(scores))
    return np.zeros_like(scores) if span <= 1e-15 else (scores - scores.min()) / span


def nearest_labelled_distance(pool_scaled: Array, candidate_indices: Array, labelled_indices: Sequence[int]) -> Array:
    """Euclidean distance from each candidate to its nearest labelled point (broadcast form).
    frozen: week4_02/03 inline form, week4_06/week4_08::nearest_labelled_distance"""
    candidates = pool_scaled[np.asarray(candidate_indices, dtype=int)]
    labelled = pool_scaled[np.asarray(labelled_indices, dtype=int)]
    diffs = candidates[:, None, :] - labelled[None, :, :]
    return np.sqrt(np.sum(diffs**2, axis=2)).min(axis=1)


def shortlist_size(candidate_count: int, gate_fraction: float, min_size: int) -> int:
    """``min(n, max(ceil(fraction n), min(min_size, n)))`` (== Phase 6's ``min(n, max(25, ceil))``).
    frozen: week4_03 / week4_06::shortlist_by_uncertainty arithmetic"""
    size = int(np.ceil(candidate_count * gate_fraction))
    size = max(size, min(min_size, candidate_count))
    return min(size, candidate_count)


def repulsion_factor(distances: Array, bandwidth: float = REPULSION_BANDWIDTH) -> Array:
    """``1 - exp(-d^2 / (2 h^2 + 1e-12))``. frozen: week4_06/08/09, week7_phase6/7 repulsion term"""
    return 1.0 - np.exp(-(np.asarray(distances, dtype=float) ** 2) / (2.0 * bandwidth**2 + 1e-12))


# --- GPR pool rules (acquisition_rules.py) --------------------------------------


def smallest_abs_mu_scores(mu: Array) -> Array:
    """``-|mu|``. frozen: acquisition_rules.py::smallest_abs_mu_scores"""
    return -np.abs(mu)


def straddle_scores(mu: Array, sigma: Array, kappa: float = STRADDLE_KAPPA) -> Array:
    """``kappa sigma - |mu|``. frozen: acquisition_rules.py::straddle_scores"""
    return kappa * sigma - np.abs(mu)


def randomized_straddle_scores(mu: Array, sigma: Array, beta: float) -> Array:
    """``sqrt(beta) sigma - |mu|``, one ``beta ~ chi2(2)`` per step.
    frozen: acquisition_rules.py::randomized_straddle_scores"""
    return np.sqrt(beta) * sigma - np.abs(mu)


def expected_feasibility_scores(
    mu: Array, sigma: Array, threshold: float = 0.0, nodes: int = QUADRATURE_NODES
) -> Array:
    """``E[max(eps^2 - (Y - threshold)^2, 0)]``, ``Y ~ N(mu, sigma^2)``, ``eps = 1.96 sigma``,
    24-node Gauss-Hermite, sigma floored at 1e-12.

    frozen: acquisition_rules.py::expected_feasibility_scores (threshold 0),
    week7_phase6::expected_feasibility_scores (translated by ``threshold``)
    """
    sigma = np.maximum(np.asarray(sigma, dtype=float), SIGMA_FLOOR)
    centered_mu = np.asarray(mu, dtype=float) - float(threshold)
    epsilon = STRADDLE_KAPPA * sigma
    quadrature_x, quadrature_w = np.polynomial.hermite.hermgauss(nodes)
    samples = centered_mu[None, :] + np.sqrt(2.0) * sigma[None, :] * quadrature_x[:, None]
    improvement = np.maximum(epsilon[None, :] ** 2 - samples**2, 0.0)
    return (quadrature_w[:, None] * improvement).sum(axis=0) / np.sqrt(np.pi)


def choose_next_index(
    method: str, unlabelled_indices: Array, mu: Array | None, sigma: Array | None, rng: np.random.Generator
) -> AcquisitionChoice:
    """Synthetic GPR pool rule (``METHOD_ORDER``); ties by first position (plain argmax).
    frozen: acquisition_rules.py::choose_next_index"""
    if method not in METHOD_ORDER:
        raise ValueError(f"Unknown acquisition method: {method}")
    if len(unlabelled_indices) == 0:
        raise ValueError("No unlabelled candidates left")
    if method == "random":
        position = int(rng.integers(len(unlabelled_indices)))
        return AcquisitionChoice(int(unlabelled_indices[position]), {"selected_position": position})
    if mu is None or sigma is None:
        raise ValueError(f"{method} requires both mu and sigma")
    metadata: dict[str, Any] = {}
    if method == "smallest_abs_mu":
        scores = smallest_abs_mu_scores(mu)
    elif method == "straddle":
        scores = straddle_scores(mu, sigma)
    elif method == "randomized_straddle":
        beta = float(rng.chisquare(df=2.0))
        scores = randomized_straddle_scores(mu, sigma, beta)
        metadata["beta"] = beta
    else:
        scores = expected_feasibility_scores(mu, sigma)
        metadata["quadrature_nodes"] = QUADRATURE_NODES
    best_position = int(np.argmax(scores))
    metadata["selected_position"] = best_position
    metadata["selected_score"] = float(scores[best_position])
    return AcquisitionChoice(int(unlabelled_indices[best_position]), metadata)


# --- Week-4 GPR heuristics -----------------------------------------------------------


def choose_diversified_straddle(
    unlabelled_indices: Array,
    mu: Array,
    sigma: Array,
    pool_scaled: Array,
    labelled_indices: Sequence[int],
    alpha: float = DIVERSIFIED_ALPHA,
) -> tuple[int, dict[str, Any]]:
    """``(1-alpha) minmax(straddle) + alpha minmax(nearest labelled distance)`` over the
    whole unlabelled pool; plain argmax.
    frozen: week4_02_diversified_straddle.py::choose_diversified_straddle"""
    straddle = straddle_scores(mu, sigma)
    diversity = nearest_labelled_distance(pool_scaled, unlabelled_indices, labelled_indices)
    norm_straddle = normalize_scores_week4(straddle)
    norm_diversity = normalize_scores_week4(diversity)
    score = (1.0 - alpha) * norm_straddle + alpha * norm_diversity
    position = int(np.argmax(score))
    return int(unlabelled_indices[position]), {
        "alpha": alpha,
        "selected_position": position,
        "selected_score": float(score[position]),
        "selected_raw_straddle": float(straddle[position]),
        "selected_raw_diversity": float(diversity[position]),
    }


def choose_boundary_gated_diversified_straddle(
    unlabelled_indices: Array,
    mu: Array,
    sigma: Array,
    pool_scaled: Array,
    labelled_indices: Sequence[int],
    gate_fraction: float = GATE_FRACTION,
    beta: float = DIVERSITY_BETA,
    min_shortlist_size: int = MIN_SHORTLIST_SIZE,
) -> tuple[int, dict[str, Any]]:
    """Top-10% (min 25) straddle shortlist, then ``(1-beta) minmax(straddle) + beta
    minmax(distance)`` normalised over the shortlist; lexsort ties.
    frozen: week4_03_boundary_gated_diversified_straddle.py::choose_boundary_gated_diversified_straddle"""
    straddle = straddle_scores(mu, sigma)
    size = shortlist_size(len(unlabelled_indices), gate_fraction, min_shortlist_size)
    shortlist_positions = np.lexsort((unlabelled_indices, -straddle))[:size]
    shortlist_indices = unlabelled_indices[shortlist_positions]
    diversity = nearest_labelled_distance(pool_scaled, shortlist_indices, labelled_indices)
    norm_straddle = normalize_scores_week4(straddle[shortlist_positions])
    norm_diversity = normalize_scores_week4(diversity)
    score = (1.0 - beta) * norm_straddle + beta * norm_diversity
    best = argmax_position(shortlist_indices, score)
    return int(shortlist_indices[best]), {
        "gate_fraction": gate_fraction,
        "beta": beta,
        "shortlist_size": size,
        "selected_position": int(shortlist_positions[best]),
        "selected_shortlist_position": best,
        "selected_gated_score": float(score[best]),
        "selected_raw_straddle": float(straddle[shortlist_positions][best]),
        "selected_raw_diversity": float(diversity[best]),
    }


def boundary_uncertainty_values(mu: Array, sigma: Array) -> Array:
    """``max(0, 1.96 sigma - |mu|)``. frozen: week4_04::boundary_uncertainty_values"""
    return np.maximum(0.0, straddle_scores(mu, sigma))


def fit_fantasy_gp(current_gp: GaussianProcessRegressor, X: Array, y: Array, seed: int) -> GaussianProcessRegressor:
    """Posterior-only refit with the current fitted kernel (``optimizer=None``).
    frozen: week4_04_lookahead_boundary_uncertainty.py::fit_fantasy_gp"""
    fantasy = GaussianProcessRegressor(
        kernel=current_gp.kernel_,
        alpha=current_gp.alpha,
        optimizer=None,
        normalize_y=current_gp.normalize_y,
        random_state=seed,
    )
    fantasy.fit(X, y)
    return fantasy


def choose_lookahead_boundary_uncertainty_reduction(
    unlabelled_indices: Array,
    mu: Array,
    sigma: Array,
    pool_scaled: Array,
    pool_labels: Array,
    labelled_indices: Sequence[int],
    current_gp: GaussianProcessRegressor,
    seed: int,
    shortlist_size_requested: int = LOOKAHEAD_SHORTLIST_SIZE,
) -> tuple[int, dict[str, Any]]:
    """One-step lookahead over the top-30 straddle shortlist: fantasise y = +1 / -1
    (posterior refit), weight by ``Phi(mu / max(sigma, 1e-9))`` and maximise the expected
    drop of mean ``max(0, 1.96 sigma - |mu|)`` over the current unlabelled pool
    (candidate included); lexsort ties.
    frozen: week4_04_lookahead_boundary_uncertainty.py::choose_lookahead_boundary_uncertainty_reduction"""
    straddle = straddle_scores(mu, sigma)
    size = min(shortlist_size_requested, len(unlabelled_indices))
    shortlist_positions = np.lexsort((unlabelled_indices, -straddle))[:size]
    shortlist_indices = unlabelled_indices[shortlist_positions]
    reference_scaled = pool_scaled[unlabelled_indices]
    u_current = float(np.mean(boundary_uncertainty_values(mu, sigma)))
    labelled = np.asarray(labelled_indices, dtype=int)
    X_labelled, y_labelled = pool_scaled[labelled], pool_labels[labelled]
    rows: list[dict[str, Any]] = []
    for position, index in zip(shortlist_positions, shortlist_indices):
        X_fantasy = np.vstack([X_labelled, pool_scaled[int(index)][None, :]])
        futures = []
        for label in (1.0, -1.0):
            gp = fit_fantasy_gp(current_gp, X_fantasy, np.concatenate([y_labelled, [label]]), seed)
            mu_f, sigma_f = gp.predict(reference_scaled, return_std=True)
            futures.append(float(np.mean(boundary_uncertainty_values(mu_f, sigma_f))))
        u_plus, u_minus = futures
        sigma_c = max(float(sigma[int(position)]), LOOKAHEAD_PROBABILITY_EPS)
        p_plus = 0.5 * (1.0 + math.erf(float(mu[int(position)]) / sigma_c / math.sqrt(2.0)))
        expected_future = p_plus * u_plus + (1.0 - p_plus) * u_minus
        rows.append(
            {
                "selected_position": int(position),
                "selected_raw_straddle": float(straddle[int(position)]),
                "selected_p_plus": float(p_plus),
                "selected_u_plus": u_plus,
                "selected_u_minus": u_minus,
                "selected_expected_uncertainty_reduction": float(u_current - expected_future),
            }
        )
    scores = np.asarray([row["selected_expected_uncertainty_reduction"] for row in rows])
    best = argmax_position(shortlist_indices, scores)
    metadata = {"shortlist_size": size, "current_aggregate_uncertainty": u_current, **rows[best]}
    return int(shortlist_indices[best]), metadata


# --- classifier rules (week4_06 / week4_08 / week4_09) ----------------------------------


def classifier_uncertainty_score(p_plus: Array) -> Array:
    """``clip(1 - 2|p - 0.5|, 0, 1)``. frozen: week4_06::classifier_uncertainty_score"""
    return np.clip(1.0 - 2.0 * np.abs(np.asarray(p_plus) - 0.5), 0.0, 1.0)


def binary_entropy(p_plus: Array) -> Array:
    """Natural-log binary entropy, p clipped to [1e-12, 1 - 1e-12]. frozen: week4_06::binary_entropy"""
    p = np.clip(np.asarray(p_plus, dtype=float), 1e-12, 1.0 - 1e-12)
    return -(p * np.log(p) + (1.0 - p) * np.log(1.0 - p))


def shortlist_by_uncertainty(
    unlabelled_indices: Array,
    uncertainty: Array,
    gate_fraction: float = GATE_FRACTION,
    min_shortlist_size: int = MIN_SHORTLIST_SIZE,
) -> tuple[Array, Array]:
    """(positions, indices) of the top-uncertainty shortlist in lexsort order.
    frozen: week4_06_gp_classifier_surrogate.py::shortlist_by_uncertainty"""
    size = shortlist_size(len(unlabelled_indices), gate_fraction, min_shortlist_size)
    positions = np.lexsort((unlabelled_indices, -uncertainty))[:size]
    return positions, unlabelled_indices[positions]


def classifier_repulsion_scores(
    p_plus: Array,
    unlabelled_indices: Array,
    pool_scaled: Array,
    labelled_indices: Sequence[int],
    bandwidth: float = REPULSION_BANDWIDTH,
) -> tuple[Array, Array, Array]:
    """POOL-normalised ``minmax(uncertainty) * repulsion`` over the whole unlabelled pool;
    returns (scores, uncertainty, repulsion).  Behind the C10 numbers and the SUR shortlist.
    frozen: week4_08::classifier_repulsion_scores == week4_09::classifier_repulsion_scores"""
    uncertainty = classifier_uncertainty_score(p_plus)
    distances = nearest_labelled_distance(pool_scaled, unlabelled_indices, labelled_indices)
    repulsion = repulsion_factor(distances, bandwidth)
    return normalize_scores_week4(uncertainty) * repulsion, uncertainty, repulsion


def uncertainty_repulsion_scores(
    p_plus: Array,
    unlabelled_indices: Array,
    pool_scaled: Array,
    labelled_indices: Sequence[int],
    *,
    normalise: str = "shortlist",
    gate_fraction: float = GATE_FRACTION,
    min_shortlist_size: int = MIN_SHORTLIST_SIZE,
    bandwidth: float = REPULSION_BANDWIDTH,
) -> dict[str, Array]:
    """``minmax(uncertainty) * repulsion`` on the uncertainty shortlist.  ``'shortlist'``
    min-maxes over the shortlist (week4_06, the Phase 6 rule); ``'pool'`` over the whole
    unlabelled pool (week4_08/09).  Arrays are aligned with ``positions``.

    frozen: week4_06::choose_classifier_candidate['classifier_uncertainty_repulsion'];
    week4_08::choose_classifier_candidate / week4_09::choose_classifier_baseline gate
    """
    require(normalise in ("shortlist", "pool"), f"Unknown normalisation: {normalise}")
    uncertainty = classifier_uncertainty_score(p_plus)
    positions, indices = shortlist_by_uncertainty(unlabelled_indices, uncertainty, gate_fraction, min_shortlist_size)
    if normalise == "shortlist":
        normalized = normalize_scores_week4(uncertainty[positions])
    else:
        normalized = normalize_scores_week4(uncertainty)[positions]
    distances = nearest_labelled_distance(pool_scaled, indices, labelled_indices)
    repulsion = repulsion_factor(distances, bandwidth)
    return {
        "positions": positions,
        "indices": indices,
        "uncertainty": uncertainty[positions],
        "normalized_uncertainty": normalized,
        "distances": distances,
        "repulsion": repulsion,
        "scores": normalized * repulsion,
    }


def choose_classifier_candidate(
    method: str,
    unlabelled_indices: Array,
    p_plus: Array,
    pool_scaled: Array,
    labelled_indices: Sequence[int],
    rng: np.random.Generator | None = None,
    *,
    normalise: str = "shortlist",
) -> tuple[int, dict[str, Any]]:
    """Synthetic fixed-GPC rules 'random', 'margin', 'entropy', 'gated_diversity' (beta 0.5)
    and 'uncertainty_repulsion' (bandwidth 0.15); legacy names ('classifier_margin',
    'random_classifier', ...) match by suffix.

    frozen: week4_06::choose_classifier_candidate (normalise='shortlist');
    week4_08::choose_classifier_candidate / week4_09::choose_classifier_baseline ('pool')
    """
    uncertainty = classifier_uncertainty_score(p_plus)
    entropy = binary_entropy(p_plus)

    def base(position: int) -> dict[str, Any]:
        return {
            "selected_position": position,
            "selected_p_plus": float(p_plus[position]),
            "selected_uncertainty_score": float(uncertainty[position]),
            "selected_entropy": float(entropy[position]),
        }

    if method in ("random", "random_classifier"):
        require(rng is not None, "the random classifier rule needs an rng")
        position = int(rng.integers(0, len(unlabelled_indices)))
        return int(unlabelled_indices[position]), base(position)
    if method.endswith("margin"):
        position = argmax_position(unlabelled_indices, uncertainty)
        return int(unlabelled_indices[position]), base(position)
    if method.endswith("entropy"):
        position = argmax_position(unlabelled_indices, entropy)
        return int(unlabelled_indices[position]), base(position)
    if method.endswith("gated_diversity"):
        positions, indices = shortlist_by_uncertainty(unlabelled_indices, uncertainty)
        distances = nearest_labelled_distance(pool_scaled, indices, labelled_indices)
        norm_uncertainty = normalize_scores_week4(uncertainty[positions])
        norm_diversity = normalize_scores_week4(distances)
        score = (1.0 - DIVERSITY_BETA) * norm_uncertainty + DIVERSITY_BETA * norm_diversity
        choice = argmax_position(indices, score)
        return int(indices[choice]), {
            "shortlist_size": len(indices),
            "beta": DIVERSITY_BETA,
            **base(int(positions[choice])),
            "selected_shortlist_position": choice,
            "selected_raw_diversity": float(distances[choice]),
            "selected_score": float(score[choice]),
        }
    if method.endswith("uncertainty_repulsion"):
        parts = uncertainty_repulsion_scores(
            p_plus, unlabelled_indices, pool_scaled, labelled_indices, normalise=normalise
        )
        choice = argmax_position(parts["indices"], parts["scores"])
        return int(parts["indices"][choice]), {
            "shortlist_size": len(parts["indices"]),
            "repulsion_bandwidth": REPULSION_BANDWIDTH,
            "normalisation": normalise,
            **base(int(parts["positions"][choice])),
            "selected_shortlist_position": choice,
            "selected_raw_distance_to_labelled": float(parts["distances"][choice]),
            "selected_repulsion": float(parts["repulsion"][choice]),
            "selected_score": float(parts["scores"][choice]),
        }
    raise ValueError(f"Unknown classifier method: {method}")


# --- real-data rules (week7_phase6) ----------------------------------------------------


def choose_continuous_candidate(
    method: str,
    candidate_indices: Array,
    mu: Array,
    sigma: Array,
    threshold: float,
    rng: np.random.Generator | None = None,
) -> tuple[int, dict[str, Any]]:
    """Regression-surrogate rules on ``|mu - threshold|`` (``threshold`` = the caller's
    online tau).  Method suffix 'boundary_proximity' (``-|mu - tau|``), 'randomized_straddle'
    (``sqrt(chi2_2) sigma - |mu - tau|``), 'expected_feasibility' (translated 24-node GH)
    or 'straddle' (``1.96 sigma - |mu - tau|``); lexsort ties.
    frozen: week7_phase6_real_data_boundary_active_level_set.py::choose_continuous_candidate"""
    centered = np.abs(mu - threshold)
    metadata: dict[str, Any] = {}
    if method.endswith("boundary_proximity"):
        scores = -centered
        acquisition = "minimum_abs_mean_minus_threshold"
    elif method.endswith("randomized_straddle"):
        require(rng is not None, "randomized_straddle needs an rng")
        chi_square_draw = float(rng.chisquare(df=2.0))
        scores = math.sqrt(chi_square_draw) * sigma - centered
        metadata["chi_square_df2_draw"] = chi_square_draw
        acquisition = "historical_randomized_straddle"
    elif method.endswith("expected_feasibility"):
        scores = expected_feasibility_scores(mu, sigma, threshold)
        acquisition = "translated_expected_feasibility"
    elif method.endswith("straddle"):
        scores = STRADDLE_KAPPA * sigma - centered
        acquisition = "fixed_straddle"
    else:
        raise ValueError(f"Unknown continuous method: {method}")
    position = argmax_position(candidate_indices, scores)
    metadata.update(
        {
            "acquisition_definition": acquisition,
            "selected_position": position,
            "selected_score": float(scores[position]),
            "selected_mu": float(mu[position]),
            "selected_sigma_latent": float(sigma[position]),
            "selected_abs_mean_minus_threshold": float(centered[position]),
        }
    )
    return int(candidate_indices[position]), metadata


def choose_binary_candidate(
    method: str, candidate_indices: Array, probabilities: Array, pool_scaled: Array, queried_indices: Sequence[int]
) -> tuple[int, dict[str, Any]]:
    """The thesis rule.  Suffix 'margin': argmax ``1 - 2|p - 0.5|``, ties by lowest row
    index.  Suffix 'uncertainty_repulsion': top-10% (min 25) uncertainty shortlist;
    ``minmax_shortlist(uncertainty) * (1 - exp(-d^2 / (2 0.15^2 + 1e-12)))`` with ``d`` =
    cdist distance (standardised coordinates) to the nearest queried point.
    frozen: week7_phase6_real_data_boundary_active_level_set.py::choose_binary_candidate"""
    uncertainty = 1.0 - 2.0 * np.abs(probabilities - 0.5)
    if method.endswith("margin"):
        position = argmax_position(candidate_indices, uncertainty)
        return int(candidate_indices[position]), {
            "acquisition_definition": "classifier_margin",
            "selected_position": position,
            "selected_probability": float(probabilities[position]),
            "selected_uncertainty_score": float(uncertainty[position]),
        }
    if not method.endswith("uncertainty_repulsion"):
        raise ValueError(f"Unknown binary method: {method}")
    n = len(candidate_indices)
    size = min(n, max(MIN_SHORTLIST_SIZE, int(math.ceil(GATE_FRACTION * n))))
    shortlist_order = np.lexsort((candidate_indices, -uncertainty))[:size]
    shortlist_indices = candidate_indices[shortlist_order]
    queried_x = pool_scaled[np.asarray(queried_indices, dtype=int)]
    distances = _distance.cdist(pool_scaled[shortlist_indices], queried_x).min(axis=1)
    normalized = normalize_scores(uncertainty[shortlist_order])
    repulsion = repulsion_factor(distances)
    scores = normalized * repulsion
    choice = argmax_position(shortlist_indices, scores)
    original_position = int(shortlist_order[choice])
    return int(shortlist_indices[choice]), {
        "acquisition_definition": "historical_classifier_uncertainty_repulsion",
        "shortlist_size": size,
        "selected_position": original_position,
        "selected_probability": float(probabilities[original_position]),
        "selected_uncertainty_score": float(uncertainty[original_position]),
        "selected_normalized_uncertainty": float(normalized[choice]),
        "selected_distance_to_queried": float(distances[choice]),
        "selected_repulsion": float(repulsion[choice]),
        "selected_score": float(scores[choice]),
    }


# --- Phase 7 hybrids (week7_phase7) --------------------------------------------------------


def phase6_binary_priority(
    candidate_indices: Array, probabilities: Array, pool_scaled: Array, queried_indices: Sequence[int]
) -> dict[str, Any]:
    """Total order over the pool: the exact Phase 6 uncertainty-repulsion shortlist first
    (by its score), then the tail by the full-pool ``minmax(uncertainty) * repulsion``;
    percentile ``1 - rank / (n - 1)``.
    frozen: week7_phase7_final_boundary_hybrid_benchmark.py::phase6_binary_priority"""
    candidate_indices = np.asarray(candidate_indices, dtype=int)
    probabilities = np.asarray(probabilities, dtype=float)
    require(len(candidate_indices) == len(probabilities), "Candidate/probability length mismatch")
    n = len(candidate_indices)
    uncertainty = 1.0 - 2.0 * np.abs(probabilities - 0.5)
    size = min(n, max(MIN_SHORTLIST_SIZE, int(math.ceil(GATE_FRACTION * n))))
    shortlist_positions = np.lexsort((candidate_indices, -uncertainty))[:size]
    queried_x = pool_scaled[np.asarray(queried_indices, dtype=int)]
    all_distances = _distance.cdist(pool_scaled[candidate_indices], queried_x).min(axis=1)
    all_repulsion = repulsion_factor(all_distances)
    shortlist_scores = normalize_scores(uncertainty[shortlist_positions]) * all_repulsion[shortlist_positions]
    ordered_shortlist = shortlist_positions[np.lexsort((candidate_indices[shortlist_positions], -shortlist_scores))]
    outside_mask = np.ones(n, dtype=bool)
    outside_mask[shortlist_positions] = False
    outside_positions = np.flatnonzero(outside_mask)
    full_fallback_scores = normalize_scores(uncertainty) * all_repulsion
    ordered_outside = outside_positions[
        np.lexsort((candidate_indices[outside_positions], -full_fallback_scores[outside_positions]))
    ]
    total_positions = np.concatenate([ordered_shortlist, ordered_outside])
    total_indices = candidate_indices[total_positions]
    require(len(np.unique(total_indices)) == n, "Binary priority order is not a permutation")
    exact_choice, exact_metadata = choose_binary_candidate(
        "binary_uncertainty_repulsion", candidate_indices, probabilities, pool_scaled, queried_indices
    )
    require(int(total_indices[0]) == int(exact_choice), "Full-pool priority failed to preserve exact Phase 6 choice")
    percentile = np.empty(n, dtype=float)
    percentile[total_positions] = 1.0 if n == 1 else 1.0 - np.arange(n) / (n - 1)
    shortlist_flag = np.zeros(n, dtype=bool)
    shortlist_flag[shortlist_positions] = True
    phase6_scores = np.full(n, np.nan)
    phase6_scores[shortlist_positions] = shortlist_scores
    return {
        "candidate_indices": candidate_indices,
        "uncertainty": uncertainty,
        "distance_to_queried": all_distances,
        "repulsion": all_repulsion,
        "phase6_shortlist_flag": shortlist_flag,
        "phase6_shortlist_score": phase6_scores,
        "fallback_full_score": full_fallback_scores,
        "ordered_positions": total_positions,
        "ordered_indices": total_indices,
        "percentile_rank": percentile,
        "phase6_exact_choice": int(exact_choice),
        "phase6_exact_metadata": exact_metadata,
        "shortlist_size": int(size),
    }


def deterministic_percentile_rank(candidate_indices: Array, scores: Array) -> tuple[Array, Array]:
    """Percentile ``1 - rank / (n - 1)`` under the lexsort order; returns (percentile, order).
    frozen: week7_phase7_final_boundary_hybrid_benchmark.py::deterministic_percentile_rank"""
    candidate_indices = np.asarray(candidate_indices, dtype=int)
    scores = np.asarray(scores, dtype=float)
    order = np.lexsort((candidate_indices, -scores))
    n = len(scores)
    percentile = np.empty(n, dtype=float)
    percentile[order] = 1.0 if n == 1 else 1.0 - np.arange(n) / (n - 1)
    return percentile, order


def max_depth_straddle_scores(mu: Array, sigma: Array, threshold: float) -> Array:
    """``1.96 sigma - |mu - threshold|``. frozen: week7_phase7::max_depth_straddle_scores"""
    return STRADDLE_KAPPA * np.asarray(sigma, dtype=float) - np.abs(np.asarray(mu, dtype=float) - float(threshold))


def choose_hybrid_candidate(
    method: str,
    candidate_indices: Array,
    binary_probabilities: Array,
    depth_mu: Array,
    depth_sigma: Array,
    threshold: float,
    pool_scaled: Array,
    queried_indices: Sequence[int],
) -> tuple[int, dict[str, Any]]:
    """'gate' (``HYBRID_GATE``): top ``ceil(20%)`` of the binary priority order, then max-depth
    straddle with lexsort ties.  'rank_fusion' (``HYBRID_FUSION``): argmax of
    ``0.5 binary percentile + 0.5 depth-straddle percentile``.
    frozen: week7_phase7_final_boundary_hybrid_benchmark.py::choose_hybrid_candidate"""
    binary = phase6_binary_priority(candidate_indices, binary_probabilities, pool_scaled, queried_indices)
    depth_scores = max_depth_straddle_scores(depth_mu, depth_sigma, threshold)
    depth_percentile, _ = deterministic_percentile_rank(candidate_indices, depth_scores)
    n = len(candidate_indices)
    if method in ("gate", HYBRID_GATE):
        gate_count = max(1, int(math.ceil(HYBRID_GATE_FRACTION * n)))
        gate_positions = binary["ordered_positions"][:gate_count]
        local = argmax_position(candidate_indices[gate_positions], depth_scores[gate_positions])
        chosen = int(gate_positions[local])
        metadata = {
            "acquisition_definition": "preregistered_binary_gate20_then_exact_max_depth_straddle",
            "gate_count": gate_count,
            "selected_binary_priority_percentile": float(binary["percentile_rank"][chosen]),
        }
    elif method in ("rank_fusion", HYBRID_FUSION):
        fusion = RANK_BINARY_WEIGHT * binary["percentile_rank"] + RANK_DEPTH_WEIGHT * depth_percentile
        chosen = argmax_position(candidate_indices, fusion)
        metadata = {
            "acquisition_definition": "preregistered_equal_percentile_rank_fusion",
            "selected_binary_percentile_rank": float(binary["percentile_rank"][chosen]),
            "selected_depth_percentile_rank": float(depth_percentile[chosen]),
            "selected_fusion_score": float(fusion[chosen]),
        }
    else:
        raise ValueError(f"Unknown Hybrid method: {method}")
    selected = int(candidate_indices[chosen])
    metadata.update(
        {
            "candidate_count": n,
            "binary_phase6_exact_choice_population_row_index": binary["phase6_exact_choice"],
            "selected_equals_binary_phase6_choice": selected == binary["phase6_exact_choice"],
            "selected_binary_probability": float(binary_probabilities[chosen]),
            "selected_depth_straddle_score": float(depth_scores[chosen]),
            "selected_inside_phase6_binary_shortlist": bool(binary["phase6_shortlist_flag"][chosen]),
        }
    )
    return selected, metadata


# --- Week 9 rules ------------------------------------------------------------------------------


def choose_gpc_margin(candidate_indices: Array, candidate_probability: Array) -> int:
    """argmax ``1 - 2|p - 0.5|``; returns the population row index (ties -> smallest).
    frozen: week9_phase1_5_h_physics_confirmation.py::choose_gpc_margin (== choose_h_margin)"""
    uncertainty = 1.0 - 2.0 * np.abs(np.asarray(candidate_probability, dtype=float) - 0.5)
    return argmax_index(candidate_indices, uncertainty)


choose_h_margin = choose_gpc_margin  # frozen: week9_phase1_5::choose_h_margin (identical body)


def choose_assisted_product(candidate_indices: Array, gpc_probability: Array, h_probability: Array) -> int:
    """argmax ``4p(1-p) [GPC] * 4q(1-q) [h-logistic]``; returns the row index.
    frozen: week9_phase1_5_h_physics_confirmation.py::choose_assisted_product"""
    gpc = np.asarray(gpc_probability, dtype=float)
    h = np.asarray(h_probability, dtype=float)
    return argmax_index(candidate_indices, (4.0 * gpc * (1.0 - gpc)) * (4.0 * h * (1.0 - h)))


def choose_m3_margin(
    candidate_indices: Array, probabilities: Array, pool_scaled: Array, queried_indices: Sequence[int]
) -> tuple[int, dict[str, Any]]:
    """Phase 6 margin rule on M3 probabilities with the archive's tie-break audit
    (``candidate[lexsort((candidate, -(1 - 2|p - 0.5|)))[0]]``).
    frozen: week9_phase1_14_m3_margin_acquisition.py::choose_m3_margin"""
    candidate_indices = np.asarray(candidate_indices, dtype=int)
    probabilities = np.asarray(probabilities, dtype=float)
    chosen, info = choose_binary_candidate(
        "binary_margin", candidate_indices, probabilities, np.asarray(pool_scaled, dtype=float), list(queried_indices)
    )
    require(info["acquisition_definition"] == "classifier_margin", "historical margin semantic drift")
    audit = candidate_indices[np.lexsort((candidate_indices, -(1 - 2 * np.abs(probabilities - 0.5))))[0]]
    require(chosen == int(audit), "tie-break drift")
    return chosen, info


def choose_repulsion(
    candidate: Array, probability: Array, pool_scaled: Array, queried: Sequence[int], c: float
) -> tuple[int, dict[str, float]]:
    """Geometry-scaled repulsion: ``lambda_B = c * median(d_min)`` over the candidates,
    ``score = (1 - 2|p - 0.5|) * (1 - exp(-d_min^2 / (2 lambda_B^2)))`` (raw uncertainty, no
    gate, no 1e-12 term); ``c`` must be in ``REPULSION_SCALE_GRID``; lexsort ties.
    frozen: week9_phase1_16_m3_repulsion_scale_audit.py::choose_repulsion"""
    candidate = np.asarray(candidate, int)
    probability = np.asarray(probability, float)
    queried_array = np.asarray(queried, int)
    require(c in REPULSION_SCALE_GRID and len(candidate) and len(queried_array), "invalid repulsion selector inputs")
    distances = np.sqrt(((pool_scaled[candidate, None, :] - pool_scaled[queried_array][None, :, :]) ** 2).sum(axis=2))
    d_min = distances.min(axis=1)
    s_b = float(np.median(d_min))
    require(s_b > 0 and np.isfinite(s_b), "invalid geometry scale")
    lambda_b = c * s_b
    repulsion = 1.0 - np.exp(-(d_min**2) / (2.0 * lambda_b**2))
    uncertainty = 1.0 - 2.0 * np.abs(probability - 0.5)
    score = uncertainty * repulsion
    position = int(np.lexsort((candidate, -score))[0])
    return int(candidate[position]), {
        "uncertainty_score": float(uncertainty[position]),
        "d_min": float(d_min[position]),
        "s_B": s_b,
        "lambda_B": float(lambda_b),
        "repulsion_factor": float(repulsion[position]),
        "acquisition_score": float(score[position]),
        "candidate_median_d_min": s_b,
    }
