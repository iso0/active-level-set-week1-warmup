"""Stepwise uncertainty reduction (SUR) rules and Laplace-GPC lookahead utilities.

Three frozen families, ported verbatim from the archive:

* **synthetic Bernoulli SUR** on the fixed-kernel GPC (Week 4 Exp 08/09, the
  C10 source): deterministic reference set ``R`` (top half by ``p(1-p)`` plus a
  seeded random fill), shortlist of ``k`` candidates by the pool-normalised
  uncertainty-repulsion score, two fantasy refits per candidate.  Exp 09
  (``choose_gpc_bernoulli_sur``) uses ``U = mean_R p(1-p)``; Exp 08's
  ``choose_gpc_bernoulli_sur_refit`` summed over ``R`` (same argmax, logged ``U``
  differs by ``|R|``) and is archive-only, as is its GPR rank-one SUR
  ``choose_gpr_bernoulli_sur_refit``; the GPR boundary-weighted IVR is short
  and kept (negative result);
* **exact finite-pool GPC-SUR** on the fixed-mean Laplace GPC (Phase 1.18B):
  every unqueried training candidate is scored by two hypothetical Laplace
  fits with the physics mean fixed (P1) or refit (P2); ``U`` = mean ``p(1-p)``
  over the unqueried pool; tie-break max score then smallest population row
  index; plus the Phase 1.18B0 ``exact_update`` fidelity levels;
* **Laplace-GPC utilities** of the Phase 1.18A audit (expected logistic
  curvature, Williams-Barber probability, posterior covariance, EMI).

Archive-only, not ported: ``week9_phase1_18a::fast_global_scores`` (rank-one
logistic-Laplace SMOCU/SUR approximation, falsified by Phase 1.18B0: Spearman
0.481 against the exact update) and ``physics_gradient_and_S`` (PA-TVR, rejected).
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.linalg import solve, solve_triangular
from scipy.special import erf, expit, ndtr
from scipy.stats import norm

from alse.io import require, seed_key, seed_u32, stable_seed
from alse.physics import EPS, WB_COEFS, WB_LAMBDAS, FixedMeanLaplaceGPC, fit_physics_mean
from alse.surrogates import fit_fixed_gpc, predict_p_plus

Array = np.ndarray

# frozen: week4_08_boundary_weighted_sur.py module constants
GPR_PROBABILITY_EPS = 1e-9
POSTERIOR_NOISE_EPS = 1e-9
IVR_GATE_FRACTION = 0.30
IVR_MIN_GATE_SIZE = 1000
UNCERTAINTY_MULTIPLIER = 1.96
# frozen: week4_09_gpc_bernoulli_sur_validation.py module constants / CLI default
CLASSIFIER_REPULSION_BANDWIDTH = 0.15
SUR_SHORTLIST_SIZES = (15, 25)
DEFAULT_REFERENCE_SIZE = 1500  # 750 most uncertain + 750 random
# seed namespaces: last item of the week4_08/09 ``seed_items = (benchmark, seed,
# method, budget, salt)`` tuples hashed by stable_seed for the reference fill.
SUR_REFERENCE_SALT = "sur_reference"
METRIC_REFERENCE_SALT = "metric_reference"

# frozen: week9_phase1_18a::GH_NODES; week9_phase1_18b::ARMS, NEAR_TIE_RELATIVE_TOLERANCE,
# hypothetical_update iteration limits; week9_phase1_18b0::LEVELS (exact ones)
GH_NODES = 24
EXACT_FIXED_SUR = "P1_EXACT_FIXED_SUR"
PHYSICS_REFIT_SUR = "P2_PHYSICS_REFIT_SUR"
SUR_ARMS = (EXACT_FIXED_SUR, PHYSICS_REFIT_SUR)
NEAR_TIE_RELATIVE_TOLERANCE = 1e-6
HYPOTHETICAL_MAX_ITER_PREDICT = 100
FALLBACK_MAX_ITER_PREDICT = 300
UPDATE_LEVELS = ("EXACT_LAPLACE_FIXED_MODEL", "EXACT_LAPLACE_REFIT_PHYSICS", "FULL_M3_REFIT")
# seed namespaces (SEED_ROOT literals of the Phase 1.18B/1.18B0 scripts); they only
# feed LogisticRegression.random_state (inert for lbfgs) but are kept verbatim.
SEED_ROOT_18B = "week9_phase1_18b_prospective_global_gpc_sur_benchmark|v1"
SEED_ROOT_18B0 = "week9_phase1_18b0|validation-gate|v1"


def sur_method_name(shortlist_size: int) -> str:
    """``'gpc_bernoulli_sur_refit_k<size>'`` -- itself a seed component of the S6 RNGs.

    frozen: week4_09_gpc_bernoulli_sur_validation.py::method_for_shortlist
    """
    return f"gpc_bernoulli_sur_refit_k{int(shortlist_size)}"


# --- Bernoulli uncertainty and reference sets (Week 4 Exp 08/09) -----------------


def bernoulli_uncertainty_from_p(p_plus: Array) -> Array:
    """``p(1-p)`` with ``p`` clipped to [0, 1].  frozen: week4_08_boundary_weighted_sur.py::bernoulli_uncertainty_from_p"""
    p = np.clip(np.asarray(p_plus, dtype=float), 0.0, 1.0)
    return p * (1.0 - p)


def gpr_p_plus(mu: Array, sigma: Array) -> Array:
    """``Phi(mu / max(sigma, 1e-9))`` of the GPR stand-in.  frozen: week4_08_boundary_weighted_sur.py::gpr_p_plus"""
    sigma_safe = np.maximum(np.asarray(sigma, dtype=float), GPR_PROBABILITY_EPS)
    return ndtr(np.asarray(mu, dtype=float) / sigma_safe)


def reference_positions(
    *, unlabelled_indices: Array, membership_uncertainty: Array, reference_size: int, seed_items: tuple[object, ...]
) -> Array:
    """Positions (into ``unlabelled_indices``) of the SUR reference set ``R``, sorted.

    All positions when ``n <= reference_size``; otherwise the ``reference_size // 2``
    most uncertain (lexsort by ``-u`` then pool index) plus a fill drawn without
    replacement from ``default_rng(stable_seed(*seed_items))``.
    frozen: week4_08_boundary_weighted_sur.py::reference_positions
    """
    n = len(unlabelled_indices)
    if n <= reference_size:
        return np.arange(n, dtype=int)
    ordered = np.lexsort((unlabelled_indices, -membership_uncertainty))
    top_count = min(reference_size, max(1, reference_size // 2))
    top_positions = ordered[:top_count]
    remaining = ordered[top_count:]
    fill_count = reference_size - len(top_positions)
    if fill_count <= 0:
        return np.sort(top_positions)
    rng = np.random.default_rng(stable_seed(*seed_items))
    fill_positions = rng.choice(remaining, size=fill_count, replace=False)
    return np.sort(np.concatenate([top_positions, fill_positions]).astype(int))


def reference_integrated_uncertainty(
    *, p_unlabelled: Array, unlabelled_indices: Array, reference_size: int, seed_items: tuple[object, ...]
) -> tuple[float, int]:
    """``(mean_R p(1-p), |R|)`` -- the S6 ``integrated_bernoulli_uncertainty`` metric.

    frozen: week4_09_gpc_bernoulli_sur_validation.py::reference_integrated_uncertainty_metric
    """
    membership_uncertainty = bernoulli_uncertainty_from_p(p_unlabelled)
    ref_pos = reference_positions(
        unlabelled_indices=unlabelled_indices, membership_uncertainty=membership_uncertainty,
        reference_size=reference_size, seed_items=seed_items,
    )
    return float(np.mean(membership_uncertainty[ref_pos])), int(len(ref_pos))


# --- shortlist helpers (private copies; acquisition.py owns the public rules) --------


def _normalize_scores(values: Array) -> Array:
    """frozen: week4_08_boundary_weighted_sur.py::normalize_scores"""
    values = np.asarray(values, dtype=float)
    low, high = float(values.min()), float(values.max())
    if high <= low + 1e-12:
        return np.zeros_like(values)
    return (values - low) / (high - low)


def _argmax_position(indices: Array, scores: Array) -> int:
    """Position of the max score, ties to the smallest index.  frozen: week4_08::deterministic_argmax"""
    return int(np.lexsort((indices, -scores))[0])


def _nearest_labelled_distance(pool_scaled: Array, candidate_indices: Array, labelled_indices: Sequence[int]) -> Array:
    """frozen: week4_08_boundary_weighted_sur.py::nearest_labelled_distance"""
    diffs = pool_scaled[candidate_indices][:, None, :] - pool_scaled[np.asarray(labelled_indices, dtype=int)][None, :, :]
    return np.sqrt(np.sum(diffs**2, axis=2)).min(axis=1)


def _shortlist_scores(
    p_plus: Array, unlabelled_indices: Array, pool_scaled: Array, labelled_indices: Sequence[int]
) -> tuple[Array, Array, Array]:
    """POOL-normalised uncertainty-repulsion score ``minmax(1-2|p-.5|) * (1 - exp(-d^2/(2*0.15^2+1e-12)))``.

    frozen: week4_09_gpc_bernoulli_sur_validation.py::classifier_repulsion_scores (== week4_08's)
    """
    uncertainty = np.clip(1.0 - 2.0 * np.abs(np.asarray(p_plus) - 0.5), 0.0, 1.0)
    distances = _nearest_labelled_distance(pool_scaled, unlabelled_indices, labelled_indices)
    repulsion = 1.0 - np.exp(-(distances**2) / (2.0 * CLASSIFIER_REPULSION_BANDWIDTH**2 + 1e-12))
    return _normalize_scores(uncertainty) * repulsion, uncertainty, repulsion


# --- GPC Bernoulli SUR (Week 4 Exp 09; C10) ---------------------------------------------


def choose_gpc_bernoulli_sur(
    *,
    pool_scaled: Array,
    pool_labels: Array,
    labelled_indices: Sequence[int],
    unlabelled_indices: Array,
    p_plus: Array,
    seed: int,
    reference_size: int,
    shortlist_size: int,
    seed_items: tuple[object, ...],
) -> tuple[int, dict[str, object]]:
    """Fantasy-refit Bernoulli SUR on the fixed synthetic GPC; returns (pool index, metadata).

    ``U = mean_R p(1-p)``; for each of the ``k`` shortlisted candidates (ties to the
    smallest pool index) refit with label +1 and -1, ``E[U'] = p* U+ + (1-p*) U-``,
    pick the largest ``U - E[U']`` (ties to the smallest pool index).  In S6
    ``seed_items = (benchmark, seed, method, budget, SUR_REFERENCE_SALT)``.
    frozen: week4_09_gpc_bernoulli_sur_validation.py::choose_gpc_bernoulli_sur
    """
    start = time.perf_counter()
    membership_uncertainty = bernoulli_uncertainty_from_p(p_plus)
    ref_pos = reference_positions(
        unlabelled_indices=unlabelled_indices, membership_uncertainty=membership_uncertainty,
        reference_size=reference_size, seed_items=seed_items,
    )
    reference_scaled = pool_scaled[unlabelled_indices[ref_pos]]
    u_current = float(np.mean(membership_uncertainty[ref_pos]))
    candidate_score, uncertainty_score, repulsion = _shortlist_scores(p_plus, unlabelled_indices, pool_scaled, labelled_indices)
    order = np.lexsort((unlabelled_indices, -candidate_score))
    shortlist_positions = order[: min(shortlist_size, len(order))]
    shortlist_indices = unlabelled_indices[shortlist_positions]
    x_labelled = pool_scaled[np.asarray(labelled_indices, dtype=int)]
    y_labelled = pool_labels[np.asarray(labelled_indices, dtype=int)]
    reductions: list[float] = []
    u_plus_values: list[float] = []
    u_minus_values: list[float] = []
    expected_values: list[float] = []
    refit_times: list[float] = []
    for candidate_index, candidate_position in zip(shortlist_indices, shortlist_positions):
        x_fantasy = np.vstack([x_labelled, pool_scaled[int(candidate_index)][None, :]])
        fit_start = time.perf_counter()
        gp_plus = fit_fixed_gpc(x_fantasy, np.concatenate([y_labelled, [1.0]]), seed=seed)
        p_ref_plus = predict_p_plus(gp_plus, reference_scaled)
        gp_minus = fit_fixed_gpc(x_fantasy, np.concatenate([y_labelled, [-1.0]]), seed=seed)
        p_ref_minus = predict_p_plus(gp_minus, reference_scaled)
        refit_times.append(time.perf_counter() - fit_start)
        u_plus = float(np.mean(bernoulli_uncertainty_from_p(p_ref_plus)))
        u_minus = float(np.mean(bernoulli_uncertainty_from_p(p_ref_minus)))
        p_star = float(p_plus[int(candidate_position)])
        expected_future = p_star * u_plus + (1.0 - p_star) * u_minus
        reductions.append(float(u_current - expected_future))
        u_plus_values.append(u_plus)
        u_minus_values.append(u_minus)
        expected_values.append(float(expected_future))
    reduction_array = np.asarray(reductions, dtype=float)
    best = _argmax_position(shortlist_indices, reduction_array)
    original_position = int(shortlist_positions[best])
    metadata = {
        "selected_position": original_position,
        "selected_score": float(reduction_array[best]),
        "p_star": float(p_plus[original_position]),
        "U_current": u_current,
        "U_plus": float(u_plus_values[best]),
        "U_minus": float(u_minus_values[best]),
        "expected_future_uncertainty": float(expected_values[best]),
        "expected_uncertainty_reduction": float(reduction_array[best]),
        "shortlist_size": int(len(shortlist_positions)),
        "requested_shortlist_size": int(shortlist_size),
        "reference_set_size": int(len(ref_pos)),
        "reference_uncertainty_definition": "mean_R p(+1)(1-p(+1))",
        "fantasy_refit_time_seconds": float(time.perf_counter() - start),
        "fantasy_refit_count": int(2 * len(shortlist_positions)),
        "mean_pair_fantasy_refit_time_seconds": float(np.mean(refit_times)) if refit_times else 0.0,
        "shortlist_source": "classifier_uncertainty_repulsion_score_over_unlabelled_pool",
        "selected_uncertainty_score": float(uncertainty_score[original_position]),
        "selected_repulsion": float(repulsion[original_position]),
    }
    return int(shortlist_indices[best]), metadata


# --- GPR boundary-weighted IVR (Week 4 Exp 08; negative result) ----------------------------


def gpr_posterior_covariance(gp: Any, X_ref: Array, X_candidate: Array) -> Array:
    """``k(R,C) - v_R^T v_C``, ``v = L^{-1} k(., X_train)`` of a fitted sklearn GPR; non-finite -> 0.

    frozen: week4_08_boundary_weighted_sur.py::posterior_covariance
    """
    k_ref_candidate = gp.kernel_(X_ref, X_candidate)
    k_ref_train = gp.kernel_(X_ref, gp.X_train_)
    k_candidate_train = gp.kernel_(X_candidate, gp.X_train_)
    v_ref = solve_triangular(gp.L_, k_ref_train.T, lower=True, check_finite=False)
    v_candidate = solve_triangular(gp.L_, k_candidate_train.T, lower=True, check_finite=False)
    covariance = k_ref_candidate - v_ref.T @ v_candidate
    return np.nan_to_num(covariance, nan=0.0, posinf=0.0, neginf=0.0)


def candidate_gate_positions(unlabelled_indices: Array, straddle: Array) -> Array:
    """Top ``max(ceil(0.30 n), min(1000, n))`` positions by straddle (ties to smallest index).

    frozen: week4_08_boundary_weighted_sur.py::candidate_gate_positions
    """
    n = len(unlabelled_indices)
    gate_size = min(max(int(np.ceil(n * IVR_GATE_FRACTION)), min(IVR_MIN_GATE_SIZE, n)), n)
    return np.lexsort((unlabelled_indices, -straddle))[:gate_size]


def compute_gpr_ivr_state(
    *, gp: Any, pool_scaled: Array, unlabelled_indices: Array, mu: Array, sigma: Array,
    reference_size: int, seed_items: tuple[object, ...],
) -> dict[str, object]:
    """Boundary-weighted integrated variance reduction of the GPR stand-in over ``R``.

    ``score_c = sum_r w_r cov(r,c)^2 / max(sigma_c^2, 1e-9)``, ``w ~ p(1-p)`` on ``R``
    (uniform if it vanishes); ``-inf`` outside the straddle gate.
    frozen: week4_08_boundary_weighted_sur.py::compute_gpr_ivr_state
    """
    p_plus = gpr_p_plus(mu, sigma)
    membership_uncertainty = bernoulli_uncertainty_from_p(p_plus)
    straddle = UNCERTAINTY_MULTIPLIER * sigma - np.abs(mu)
    ref_pos = reference_positions(
        unlabelled_indices=unlabelled_indices, membership_uncertainty=membership_uncertainty,
        reference_size=reference_size, seed_items=seed_items,
    )
    gate_pos = candidate_gate_positions(unlabelled_indices, straddle)
    weights = membership_uncertainty[ref_pos].astype(float)
    if float(weights.sum()) <= 1e-12:
        weights = np.full_like(weights, 1.0 / len(weights), dtype=float)
    else:
        weights = weights / float(weights.sum())
    covariance = gpr_posterior_covariance(gp, pool_scaled[unlabelled_indices[ref_pos]], pool_scaled[unlabelled_indices[gate_pos]])
    gate_var = np.maximum(sigma[gate_pos] ** 2, POSTERIOR_NOISE_EPS)
    scores = np.full(len(unlabelled_indices), -np.inf, dtype=float)
    scores[gate_pos] = weights @ ((covariance**2) / gate_var[None, :])
    return {
        "scores": scores, "ref_pos": ref_pos, "gate_pos": gate_pos, "covariance_ref_gate": covariance,
        "p_plus": p_plus, "membership_uncertainty": membership_uncertainty, "straddle": straddle, "reference_weights": weights,
    }


def choose_gpr_boundary_weighted_ivr(
    *, gp: Any, pool_scaled: Array, unlabelled_indices: Array, mu: Array, sigma: Array,
    reference_size: int, seed_items: tuple[object, ...],
) -> tuple[int, dict[str, object]]:
    """Argmax of :func:`compute_gpr_ivr_state` scores (ties to the smallest pool index).

    frozen: week4_08_boundary_weighted_sur.py::choose_gpr_boundary_weighted_ivr
    """
    state = compute_gpr_ivr_state(
        gp=gp, pool_scaled=pool_scaled, unlabelled_indices=unlabelled_indices, mu=mu, sigma=sigma,
        reference_size=reference_size, seed_items=seed_items,
    )
    scores = state["scores"]
    position = _argmax_position(unlabelled_indices, scores)
    metadata = {
        "selected_position": position, "selected_score": float(scores[position]),
        "selected_p_plus": float(state["p_plus"][position]),
        "selected_membership_uncertainty": float(state["membership_uncertainty"][position]),
        "selected_straddle_score": float(state["straddle"][position]),
        "weighted_variance_reduction": float(scores[position]),
        "reference_set_size": int(len(state["ref_pos"])), "candidate_gate_size": int(len(state["gate_pos"])),
        "candidate_gate_fraction": IVR_GATE_FRACTION, "posterior_covariance_used": True,
    }
    return int(unlabelled_indices[position]), metadata


# --- Laplace-GPC utilities (Phase 1.18A) ------------------------------------------------------


def expected_logistic_curvature(mu: Array, var: Array) -> Array:
    """``E[sigma(f)(1-sigma(f))]``, ``f ~ N(mu, var)``, by 24-node Gauss-Hermite quadrature.

    frozen: week9_phase1_18a_level_set_acquisition_compatibility_audit.py::expected_logistic_curvature
    """
    nodes, weights = np.polynomial.hermite.hermgauss(GH_NODES)
    latent = np.asarray(mu)[..., None] + np.sqrt(2.0 * np.asarray(var))[..., None] * nodes
    prob = expit(latent)
    return np.sum(weights * prob * (1.0 - prob), axis=-1) / math.sqrt(math.pi)


def logistic_gaussian_probability(mu: Array, var: Array) -> Array:
    """Williams-Barber ``E[sigma(f)]``, ``f ~ N(mu, max(var, EPS))``, any shape, clipped to ``[EPS, 1-EPS]``.

    Same constants as :meth:`FixedMeanLaplaceGPC.predict_proba`.
    frozen: week9_phase1_18a_level_set_acquisition_compatibility_audit.py::logistic_gaussian_probability
    """
    mu = np.asarray(mu, float)
    var = np.maximum(np.asarray(var, float), EPS)
    flat_mu, flat_var = mu.reshape(-1), var.reshape(-1)
    alpha = 1.0 / (2.0 * flat_var)
    gamma = WB_LAMBDAS * flat_mu
    integrals = np.sqrt(np.pi / alpha) * erf(gamma * np.sqrt(alpha / (alpha + WB_LAMBDAS**2))) / (2.0 * np.sqrt(flat_var * 2.0 * np.pi))
    positive = (WB_COEFS * integrals).sum(axis=0) + 0.5 * WB_COEFS.sum()
    return np.clip(positive, EPS, 1.0 - EPS).reshape(mu.shape)


def emi_score(mu: Array, sd: Array) -> Array:
    """Expected misclassification improvement ``sd phi(z) - |mu| Phi(-z)``, ``z = |mu|/max(sd, 1e-15)``.

    frozen: week9_phase1_18a_level_set_acquisition_compatibility_audit.py::emi_score
    """
    sd = np.maximum(np.asarray(sd, float), 1e-15)
    absolute = np.abs(np.asarray(mu, float))
    z = absolute / sd
    return sd * norm.pdf(z) - absolute * norm.cdf(-z)


def posterior_covariance(gp: FixedMeanLaplaceGPC, x_scaled: Array) -> Array:
    """Laplace latent covariance ``k(X,X) - v^T v``, ``v = L^{-1} W^{1/2} k(X_train, X)``; symmetrised, diag >= EPS.

    ``gp`` is a fitted :class:`FixedMeanLaplaceGPC` (the archive took the hybrid fit and used ``fit.gp``).
    frozen: week9_phase1_18a_level_set_acquisition_compatibility_audit.py::posterior_covariance
    """
    cross = gp.kernel_(gp.X_train_, x_scaled)
    v = solve(gp.L_, gp.W_sr_[:, None] * cross)
    covariance = gp.kernel_(x_scaled) - v.T.dot(v)
    covariance = (covariance + covariance.T) / 2.0
    np.fill_diagonal(covariance, np.maximum(np.diag(covariance), EPS))
    return covariance


# --- exact finite-pool GPC-SUR (Phase 1.18B / 1.18B0) ------------------------------------------
#
# ``current`` is a fitted hybrid state with attributes ``physics`` (PhysicsMeanFit),
# ``x_scaler`` (StandardScaler on the training pool) and ``gp`` (FixedMeanLaplaceGPC),
# i.e. ``alse.hybrid_gpc.HybridFit`` or the archive's ``HybridFit``.


def _hybrid_components(current: Any, x4_rows: Array, logh_rows: Array) -> tuple[Array, Array, Array]:
    """(final latent mean, latent variance, P(y=1)) of the hybrid at raw rows.  frozen: week9_phase1_13::components"""
    transformed = current.x_scaler.transform(np.asarray(x4_rows, float))
    phys = current.physics.latent(np.asarray(logh_rows, float))
    final, var = current.gp.latent_mean_and_variance(transformed, phys)
    return final, var, current.gp.predict_proba(transformed, phys)[:, 1]


@dataclass
class Hypothetical:
    """One hypothetical-label refit: P(y=1) on the reference rows plus fit bookkeeping."""

    probability: Array
    seconds: float
    fallback: bool
    posterior_iterations: int
    intercept: float
    slope: float


def hypothetical_update(
    current: Any, x4: Array, logh: Array, labels: Array, revealed: Array, candidate: int, outcome: int,
    arm: str, reference: Array, run_id: str, budget: int,
) -> Hypothetical:
    """Exact Laplace refit on ``revealed + [candidate]`` with ``labels[candidate] = outcome``.

    ``EXACT_FIXED_SUR`` keeps the physics mean, ``PHYSICS_REFIT_SUR`` refits it on the
    enlarged set; scaler and Stage-2 kernel are always fixed.  A fit that hits the
    100-iteration Laplace limit (or fails) is retried once with ``max_iter_predict=300``.
    frozen: week9_phase1_18b_prospective_global_gpc_sur_benchmark.py::hypothetical_update
    """
    candidate = int(candidate)
    lab = labels.copy()
    lab[candidate] = outcome
    enlarged = np.append(revealed, candidate)
    if arm == EXACT_FIXED_SUR:
        physics = current.physics
    elif arm == PHYSICS_REFIT_SUR:
        physics = fit_physics_mean(logh, lab, enlarged, seed_u32(seed_key(SEED_ROOT_18B, "physics_refit", run_id, budget, candidate, outcome)))
    else:
        raise ValueError(arm)
    started = time.perf_counter()
    fallback = False
    x_enlarged, mean_enlarged = current.x_scaler.transform(x4[enlarged]), physics.latent(logh[enlarged])
    try:
        gp = FixedMeanLaplaceGPC(current.gp.kernel_, optimize=False, max_iter_predict=HYPOTHETICAL_MAX_ITER_PREDICT)
        gp.fit(x_enlarged, lab[enlarged], mean_enlarged)
        require(np.array_equal(gp.kernel_.theta, current.gp.kernel_.theta), "hypothetical kernel drift")
        require(gp.diagnostics_.posterior_iterations < HYPOTHETICAL_MAX_ITER_PREDICT, "Laplace iteration limit")
    except Exception:
        fallback = True
        gp = FixedMeanLaplaceGPC(current.gp.kernel_, optimize=False, max_iter_predict=FALLBACK_MAX_ITER_PREDICT)
        gp.fit(x_enlarged, lab[enlarged], mean_enlarged)
        require(np.array_equal(gp.kernel_.theta, current.gp.kernel_.theta), "fallback kernel drift")
    probability = gp.predict_proba(current.x_scaler.transform(x4[reference]), physics.latent(logh[reference]))[:, 1]
    return Hypothetical(
        probability, time.perf_counter() - started, fallback, int(gp.diagnostics_.posterior_iterations),
        float(physics.model.intercept_[0]), float(physics.model.coef_[0, 0]),
    )


def score_candidates(
    current: Any, x4: Array, logh: Array, labels: Array, revealed: Array, candidates: Array, arm: str, run_id: str, budget: int
) -> tuple[int, list[dict[str, Any]], dict[str, Any]]:
    """Finite-pool SUR over ``candidates``: (chosen row index, per-candidate records, diagnostic).

    ``U_n = mean_C p(1-p)``; for candidate ``x`` the future ``U_{n+1}`` is the mean over
    ``C \\ {x}`` under each outcome weighted by ``p(x)``; ``score = U_n - E[U_{n+1}]``.
    Chosen = max score, ties to the smallest population row index;
    ``near_tie_tolerance = max(1e-14, 1e-6 * max(max|score|, range))``; non-finite scores abort.
    frozen: week9_phase1_18b_prospective_global_gpc_sur_benchmark.py::score_candidates
    """
    latent_mean, latent_var, current_p = _hybrid_components(current, x4[candidates], logh[candidates])
    current_p = np.asarray(current_p, float)
    records: list[dict[str, Any]] = []
    failures = fallbacks = 0
    started = time.perf_counter()
    current_intercept = float(current.physics.model.intercept_[0])
    current_slope = float(current.physics.model.coef_[0, 0])
    current_u_global = float(np.mean(current_p * (1.0 - current_p)))
    for j, candidate in enumerate(candidates):
        reference = np.delete(candidates, j)
        outcomes: dict[int, Hypothetical] = {}
        for outcome in (0, 1):
            try:
                outcomes[outcome] = hypothetical_update(current, x4, logh, labels, revealed, int(candidate), outcome, arm, reference, run_id, budget)
                fallbacks += int(outcomes[outcome].fallback)
            except Exception:
                failures += 1
        if len(outcomes) != 2:
            score = u0 = u1 = expected = i0 = i1 = s0 = s1 = seconds = np.nan
            it0 = it1 = 0
        else:
            u0 = float(np.mean(outcomes[0].probability * (1.0 - outcomes[0].probability)))
            u1 = float(np.mean(outcomes[1].probability * (1.0 - outcomes[1].probability)))
            expected = (1.0 - current_p[j]) * u0 + current_p[j] * u1
            score = current_u_global - expected
            i0, i1 = outcomes[0].intercept, outcomes[1].intercept
            s0, s1 = outcomes[0].slope, outcomes[1].slope
            it0, it1 = outcomes[0].posterior_iterations, outcomes[1].posterior_iterations
            seconds = outcomes[0].seconds + outcomes[1].seconds
        records.append({
            "run_id": run_id, "budget": budget, "arm": arm,
            "candidate_population_row_index": int(candidate), "candidate_probability": float(current_p[j]),
            "candidate_latent_mean": float(latent_mean[j]), "candidate_latent_variance": float(latent_var[j]),
            "current_global_uncertainty": current_u_global, "future_uncertainty_y0": u0,
            "future_uncertainty_y1": u1, "expected_future_uncertainty": expected, "sur_score": score,
            "current_physics_intercept": current_intercept, "current_physics_slope": current_slope,
            "physics_intercept_y0": i0, "physics_intercept_y1": i1, "physics_slope_y0": s0, "physics_slope_y1": s1,
            "posterior_iterations_y0": it0, "posterior_iterations_y1": it1, "candidate_scoring_seconds": seconds,
        })
    scores = np.asarray([r["sur_score"] for r in records], float)
    require(np.isfinite(scores).all(), f"nonfinite SUR scores {run_id}/B{budget}/{arm}")
    order = np.lexsort((candidates, -scores))
    chosen = int(candidates[order[0]])
    max_abs = float(np.max(np.abs(scores)))
    score_range = float(np.ptp(scores))
    tolerance = max(1e-14, NEAR_TIE_RELATIVE_TOLERANCE * max(max_abs, score_range))
    sorted_scores = scores[order]
    diagnostic = {
        "run_id": run_id, "budget": budget, "arm": arm, "candidate_count": len(candidates),
        "hypothetical_failures": failures, "fallback_count": fallbacks, "nonfinite_scores": int((~np.isfinite(scores)).sum()),
        "constant_score_event": bool(score_range <= tolerance), "score_min": float(scores.min()), "score_max": float(scores.max()),
        "score_range": score_range, "top1_top2_gap": float(sorted_scores[0] - sorted_scores[1]),
        "near_tie_tolerance": tolerance, "near_tied_fraction": float(np.mean(sorted_scores[0] - scores <= tolerance)),
        "candidate_scoring_seconds": time.perf_counter() - started,
    }
    return chosen, records, diagnostic


@dataclass
class UpdatedFit:
    """One Phase 1.18B0 exact update (physics / scaler / GP) at a fidelity ``level``."""

    level: str
    physics: Any
    scaler: Any
    gp: Any
    seconds: float


def exact_update(
    current: Any, x4: Array, logh: Array, labels: Array, revealed: Sequence[int], training_pool: Sequence[int],
    candidate: int, y: int, level: str, refit: Callable[..., Any] | None = None,
) -> UpdatedFit:
    """Exact posterior update after revealing ``labels[candidate] = y`` at one of ``UPDATE_LEVELS``.

    ``EXACT_LAPLACE_FIXED_MODEL``: physics, scaler, kernel fixed; ``EXACT_LAPLACE_REFIT_PHYSICS``:
    physics refit, scaler and kernel fixed; ``FULL_M3_REFIT``: physics refit then
    ``refit(x4, logh, labels, revealed, training_pool, physics, 'M3', 100.0)`` -- pass
    ``alse.hybrid_gpc.fit_hybrid`` (a parameter to avoid a module cycle).
    frozen: week9_phase1_18b0_fast_gpc_sur_update_validation.py::exact_update
    """
    lab = labels.copy()
    lab[candidate] = int(y)
    enlarged = np.asarray([*revealed, candidate], int)
    started = time.perf_counter()
    if level == "EXACT_LAPLACE_FIXED_MODEL":
        physics, scaler = current.physics, current.x_scaler
        gp = FixedMeanLaplaceGPC(current.gp.kernel_, optimize=False)
        gp.fit(scaler.transform(x4[enlarged]), lab[enlarged], physics.latent(logh[enlarged]))
        require(np.array_equal(gp.kernel_.theta, current.gp.kernel_.theta), "fixed kernel drift")
    elif level == "EXACT_LAPLACE_REFIT_PHYSICS":
        physics = fit_physics_mean(logh, lab, enlarged, seed_u32(seed_key(SEED_ROOT_18B0, "physics_refit", candidate, y, *revealed)))
        scaler = current.x_scaler
        gp = FixedMeanLaplaceGPC(current.gp.kernel_, optimize=False)
        gp.fit(scaler.transform(x4[enlarged]), lab[enlarged], physics.latent(logh[enlarged]))
        require(np.array_equal(gp.kernel_.theta, current.gp.kernel_.theta), "physics-refit kernel drift")
    elif level == "FULL_M3_REFIT":
        require(refit is not None, "FULL_M3_REFIT needs refit=alse.hybrid_gpc.fit_hybrid")
        physics = fit_physics_mean(logh, lab, enlarged, seed_u32(seed_key(SEED_ROOT_18B0, "full", candidate, y, *revealed)))
        fit = refit(x4, logh, lab, enlarged, training_pool, physics, "M3", 100.0)
        return UpdatedFit(level, fit.physics, fit.x_scaler, fit.gp, time.perf_counter() - started)
    else:
        raise ValueError(level)
    return UpdatedFit(level, physics, scaler, gp, time.perf_counter() - started)


def updated_components(fit: UpdatedFit, x4: Array, logh: Array, reference: Array) -> tuple[Array, Array, Array]:
    """(latent mean, latent variance, P(y=1)) of an :class:`UpdatedFit` on ``reference`` rows.

    frozen: week9_phase1_18b0_fast_gpc_sur_update_validation.py::updated_components
    """
    xs = fit.scaler.transform(x4[reference])
    mean = fit.physics.latent(logh[reference])
    mu, var = fit.gp.latent_mean_and_variance(xs, mean)
    return mu, var, fit.gp.predict_proba(xs, mean)[:, 1]
