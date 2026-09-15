"""Week 5.3 gated geometric boundary contraction acquisition.

This script preserves the Week 5.1 diversity methods and adds:

    gated_geometric_boundary_contraction

The new method gates to boundary-relevant candidates using straddle, then scores
the shortlist with a product of local GP-posterior geometric factors:

    normalized_curvature * normalized_uncertainty * boundary_weight * repulsion

Curvature is a finite-difference proxy from the GP-regression posterior mean,
not the true boundary curvature. This is a heuristic acquisition rule, not a
theoretically proven method.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from src.acquisition_rules import METHOD_DESCRIPTIONS, METHOD_ORDER, choose_next_index
from src.acquisition_rules import rng_for_method as branin_rng_for_method
from src.branin_week1 import branin, compute_threshold as compute_branin_threshold
from src.branin_week1 import fit_gp
from src.week2_acquisition_comparison import create_seed_design as create_branin_design
from src.week3_4d_named_benchmark_comparison import (
    POOL_SIZE as ACKLEY_POOL_SIZE,
)
from src.week3_4d_named_benchmark_comparison import (
    TEST_SIZE as ACKLEY_TEST_SIZE,
)
from src.week3_4d_named_benchmark_comparison import (
    THRESHOLD_SAMPLE_SIZE as ACKLEY_THRESHOLD_SAMPLE_SIZE,
)
from src.week3_4d_named_benchmark_comparison import (
    THRESHOLD_SEED as ACKLEY_THRESHOLD_SEED,
)
from src.week3_4d_named_benchmark_comparison import (
    ackley_4d,
    compute_threshold as compute_ackley_threshold,
    create_seed_design as create_ackley_design,
    rng_for_week3_named_method,
    threshold_sample_values,
)


OUTPUT_DIR = (
    Path(__file__).resolve().parents[1]
    / "outputs"
    / "week5_3_gated_geometric_boundary_contraction"
)
SEEDS = (0, 1, 2, 3, 4)
ORIGINAL_METHODS = tuple(METHOD_ORDER)
WEEK5_METHODS = ORIGINAL_METHODS + (
    "diversified_straddle",
    "boundary_gated_diversified_straddle",
    "gated_geometric_boundary_contraction",
)
DIVERSIFIED_ALPHA = 0.25
BOUNDARY_GATED_BETA = 0.50
BOUNDARY_GATED_GATE_FRACTION = 0.10
BOUNDARY_GATED_MIN_SHORTLIST_SIZE = 25
GBC_SHORTLIST_SIZE = 200
GBC_FINITE_DIFFERENCE_H = 1e-3
GBC_CURVATURE_CLIP = 10.0
GBC_REPULSION_BANDWIDTH = 0.15
GBC_BOUNDARY_WEIGHT_POWER = 1.0
GBC_NORMALIZATION_EPS = 1e-12
BOUNDARY_QUANTILES = (10, 20, 30)
UNCERTAINTY_MULTIPLIER = 1.96

METHOD_DESCRIPTIONS_WEEK5 = {
    **METHOD_DESCRIPTIONS,
    "diversified_straddle": (
        "Normalize straddle and minimum distance to the labelled set over the "
        "unlabelled pool, then choose largest (1-alpha)*straddle + alpha*diversity."
    ),
    "boundary_gated_diversified_straddle": (
        "Keep the top gate_fraction unlabelled candidates by straddle score, "
        "then normalize straddle and diversity inside that shortlist and choose "
        "largest (1-beta)*straddle + beta*diversity."
    ),
    "gated_geometric_boundary_contraction": (
        "Keep the top straddle candidates, then score them by normalized "
        "finite-difference curvature times normalized uncertainty times a "
        "boundary-weight factor times labelled-set repulsion."
    ),
}

METHOD_COLORS = {
    "random": "#8c8c8c",
    "smallest_abs_mu": "#2b6cb0",
    "straddle": "#0f8b61",
    "randomized_straddle": "#b7791f",
    "expected_feasibility": "#9f1239",
    "diversified_straddle": "#6a3d9a",
    "boundary_gated_diversified_straddle": "#d95f02",
    "gated_geometric_boundary_contraction": "#1f9eaa",
}


@dataclass
class BenchmarkConfig:
    name: str
    display_name: str
    output_name: str
    domain: str
    threshold: float
    threshold_percentile: float
    threshold_seed: int
    threshold_sample_size: int
    pool_size: int
    test_size: int
    initial_size: int
    total_budget: int
    selected_budgets: tuple[int, ...]
    create_design: Callable
    value_function: Callable[[np.ndarray], np.ndarray]
    scaling_rule: str


@dataclass
class MethodRun:
    benchmark: str
    method: str
    seed: int
    initial_indices: list[int]
    labelled_indices: list[int]
    budgets: list[int]
    metric_rows: list[dict[str, object]]
    query_rows: list[dict[str, object]]
    threshold: float
    pool_signature: str
    test_signature: str


@dataclass
class BenchmarkResult:
    config: BenchmarkConfig
    runs_by_method: dict[str, list[MethodRun]]
    fairness_checks: dict[str, object]
    raw_metric_rows: list[dict[str, object]]
    query_rows: list[dict[str, object]]
    selected_budget_rows: list[dict[str, object]]
    final_rows: list[dict[str, object]]
    combined_row: dict[str, object]
    comparison_rows: list[dict[str, object]]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                fieldnames.append(key)
                seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: "null" if row.get(key) is None else row.get(key)
                    for key in fieldnames
                }
            )


def json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [json_ready(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


def array_signature(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for array in arrays:
        contiguous = np.ascontiguousarray(array)
        digest.update(str(contiguous.shape).encode("utf-8"))
        digest.update(str(contiguous.dtype).encode("utf-8"))
        digest.update(contiguous.view(np.uint8))
    return digest.hexdigest()


def mean_std(values: list[float]) -> tuple[float, float]:
    array = np.asarray(values, dtype=float)
    return float(array.mean()), float(array.std())


def normalize_scores(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    low = float(values.min())
    high = float(values.max())
    if high <= low + 1e-12:
        return np.zeros_like(values)
    return (values - low) / (high - low)


def robust_normalize(values: np.ndarray) -> np.ndarray:
    values = np.nan_to_num(np.asarray(values, dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    low = float(values.min())
    high = float(values.max())
    return (values - low) / (high - low + GBC_NORMALIZATION_EPS)


def normal_cdf_array(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    return 0.5 * (1.0 + np.vectorize(math.erf)(values / math.sqrt(2.0)))


def rng_for_week5_method(seed: int, method: str, benchmark: str) -> np.random.Generator:
    if benchmark == "branin" and method in ORIGINAL_METHODS:
        return branin_rng_for_method(seed, method)
    if benchmark == "ackley" and method in ORIGINAL_METHODS:
        return rng_for_week3_named_method(seed, method)
    digest = hashlib.sha256(f"{seed}:{benchmark}:{method}:week5".encode("utf-8")).digest()
    offset = int.from_bytes(digest[:8], "little") % (2**32)
    return np.random.default_rng(offset)


def choose_diversified_straddle(
    *,
    unlabelled_indices: np.ndarray,
    mu: np.ndarray,
    sigma: np.ndarray,
    pool_scaled: np.ndarray,
    labelled_indices: list[int],
    alpha: float,
) -> tuple[int, dict[str, object]]:
    straddle = UNCERTAINTY_MULTIPLIER * sigma - np.abs(mu)
    candidates = pool_scaled[unlabelled_indices]
    labelled = pool_scaled[np.asarray(labelled_indices, dtype=int)]
    diffs = candidates[:, None, :] - labelled[None, :, :]
    diversity = np.sqrt(np.sum(diffs**2, axis=2)).min(axis=1)
    norm_straddle = normalize_scores(straddle)
    norm_diversity = normalize_scores(diversity)
    score = (1.0 - alpha) * norm_straddle + alpha * norm_diversity
    position = int(np.argmax(score))
    metadata: dict[str, object] = {
        "alpha": alpha,
        "selected_position": position,
        "selected_score": float(score[position]),
        "selected_normalized_straddle": float(norm_straddle[position]),
        "selected_normalized_diversity": float(norm_diversity[position]),
        "selected_raw_straddle": float(straddle[position]),
        "selected_raw_diversity": float(diversity[position]),
    }
    return int(unlabelled_indices[position]), metadata


def choose_boundary_gated_diversified_straddle(
    *,
    unlabelled_indices: np.ndarray,
    mu: np.ndarray,
    sigma: np.ndarray,
    pool_scaled: np.ndarray,
    labelled_indices: list[int],
    gate_fraction: float,
    beta: float,
    min_shortlist_size: int,
) -> tuple[int, dict[str, object]]:
    straddle = UNCERTAINTY_MULTIPLIER * sigma - np.abs(mu)
    candidate_count = len(unlabelled_indices)
    shortlist_size = int(np.ceil(candidate_count * gate_fraction))
    shortlist_size = max(shortlist_size, min(min_shortlist_size, candidate_count))
    shortlist_size = min(shortlist_size, candidate_count)

    order = np.lexsort((unlabelled_indices, -straddle))
    shortlist_positions = order[:shortlist_size]
    shortlist_indices = unlabelled_indices[shortlist_positions]
    shortlist_straddle = straddle[shortlist_positions]

    candidates = pool_scaled[shortlist_indices]
    labelled = pool_scaled[np.asarray(labelled_indices, dtype=int)]
    diffs = candidates[:, None, :] - labelled[None, :, :]
    diversity = np.sqrt(np.sum(diffs**2, axis=2)).min(axis=1)

    norm_straddle = normalize_scores(shortlist_straddle)
    norm_diversity = normalize_scores(diversity)
    score = (1.0 - beta) * norm_straddle + beta * norm_diversity
    score_order = np.lexsort((shortlist_indices, -score))
    best_shortlist_position = int(score_order[0])
    original_position = int(shortlist_positions[best_shortlist_position])
    metadata: dict[str, object] = {
        "gate_fraction": gate_fraction,
        "beta": beta,
        "min_shortlist_size": min_shortlist_size,
        "shortlist_size": shortlist_size,
        "shortlist_fraction_actual": float(shortlist_size / candidate_count),
        "selected_position": original_position,
        "selected_shortlist_position": best_shortlist_position,
        "selected_gated_score": float(score[best_shortlist_position]),
        "selected_normalized_straddle": float(norm_straddle[best_shortlist_position]),
        "selected_normalized_diversity": float(norm_diversity[best_shortlist_position]),
        "selected_raw_straddle": float(shortlist_straddle[best_shortlist_position]),
        "selected_raw_diversity": float(diversity[best_shortlist_position]),
    }
    return int(shortlist_indices[best_shortlist_position]), metadata


def choose_gated_geometric_boundary_contraction(
    *,
    unlabelled_indices: np.ndarray,
    mu: np.ndarray,
    sigma: np.ndarray,
    gp,
    pool_scaled: np.ndarray,
    labelled_indices: list[int],
    shortlist_size: int,
    finite_difference_h: float,
    curvature_clip: float,
    repulsion_bandwidth: float,
    boundary_weight_power: float,
) -> tuple[int, dict[str, object]]:
    straddle = UNCERTAINTY_MULTIPLIER * sigma - np.abs(mu)
    shortlist_size_actual = min(shortlist_size, len(unlabelled_indices))
    order = np.lexsort((unlabelled_indices, -straddle))
    shortlist_positions = order[:shortlist_size_actual]
    shortlist_indices = unlabelled_indices[shortlist_positions]
    shortlist_x = pool_scaled[shortlist_indices]
    shortlist_mu = mu[shortlist_positions]
    shortlist_sigma = sigma[shortlist_positions]
    shortlist_straddle = straddle[shortlist_positions]

    uncertainty_norm = robust_normalize(shortlist_sigma)
    probit_probability = normal_cdf_array(shortlist_mu / np.sqrt(1.0 + shortlist_sigma**2))
    boundary_weight = 1.0 - 2.0 * np.abs(probit_probability - 0.5)
    boundary_weight = np.clip(boundary_weight, 0.0, 1.0) ** boundary_weight_power

    n_candidates, n_dim = shortlist_x.shape
    gradients = np.zeros((n_candidates, n_dim), dtype=float)
    hess_diag = np.zeros((n_candidates, n_dim), dtype=float)
    for dim in range(n_dim):
        offset = np.zeros(n_dim, dtype=float)
        offset[dim] = finite_difference_h
        x_plus = np.clip(shortlist_x + offset[None, :], 0.0, 1.0)
        x_minus = np.clip(shortlist_x - offset[None, :], 0.0, 1.0)
        mu_plus = gp.predict(x_plus)
        mu_minus = gp.predict(x_minus)
        gradients[:, dim] = (mu_plus - mu_minus) / (2.0 * finite_difference_h)
        hess_diag[:, dim] = (mu_plus - 2.0 * shortlist_mu + mu_minus) / (finite_difference_h**2)

    grad_norm = np.linalg.norm(gradients, axis=1) + GBC_NORMALIZATION_EPS
    g_hat = gradients / grad_norm[:, None]
    projected_hess_diag = hess_diag - (
        np.einsum("nd,nd->n", g_hat, hess_diag)[:, None] * g_hat
    )
    curvature_raw = np.linalg.norm(projected_hess_diag, axis=1) / (1.0 + grad_norm)
    curvature_raw = np.clip(np.nan_to_num(curvature_raw, nan=0.0, posinf=curvature_clip), 0.0, curvature_clip)
    curvature_norm = robust_normalize(curvature_raw)

    labelled = pool_scaled[np.asarray(labelled_indices, dtype=int)]
    diffs = shortlist_x[:, None, :] - labelled[None, :, :]
    min_dist = np.sqrt(np.sum(diffs**2, axis=2)).min(axis=1)
    repulsion = 1.0 - np.exp(-(min_dist**2) / (2.0 * repulsion_bandwidth**2 + GBC_NORMALIZATION_EPS))
    repulsion = np.clip(np.nan_to_num(repulsion, nan=0.0), 0.0, 1.0)

    gbc_score = curvature_norm * uncertainty_norm * boundary_weight * repulsion
    gbc_score = np.nan_to_num(gbc_score, nan=0.0, posinf=0.0, neginf=0.0)
    fallback_used = bool(np.all(gbc_score <= GBC_NORMALIZATION_EPS))
    if fallback_used:
        score_for_choice = shortlist_straddle
    else:
        score_for_choice = gbc_score
    tie_order = np.lexsort((shortlist_indices, -score_for_choice))
    best_shortlist_position = int(tie_order[0])
    metadata: dict[str, object] = {
        "shortlist_size": shortlist_size_actual,
        "requested_shortlist_size": shortlist_size,
        "finite_difference_h": finite_difference_h,
        "curvature_clip": curvature_clip,
        "repulsion_bandwidth": repulsion_bandwidth,
        "boundary_weight_power": boundary_weight_power,
        "selected_position": int(shortlist_positions[best_shortlist_position]),
        "selected_shortlist_position": best_shortlist_position,
        "selected_raw_straddle": float(shortlist_straddle[best_shortlist_position]),
        "selected_normalized_uncertainty": float(uncertainty_norm[best_shortlist_position]),
        "selected_boundary_weight": float(boundary_weight[best_shortlist_position]),
        "selected_raw_curvature": float(curvature_raw[best_shortlist_position]),
        "selected_normalized_curvature": float(curvature_norm[best_shortlist_position]),
        "selected_repulsion": float(repulsion[best_shortlist_position]),
        "selected_gbc_score": float(gbc_score[best_shortlist_position]),
        "fallback_used": fallback_used,
    }
    return int(shortlist_indices[best_shortlist_position]), metadata


def get_dataset_values(dataset: object, config: BenchmarkConfig) -> tuple[np.ndarray, np.ndarray]:
    if hasattr(dataset, "pool_values") and hasattr(dataset, "test_values"):
        return np.asarray(dataset.pool_values), np.asarray(dataset.test_values)
    return config.value_function(dataset.pool_original), config.value_function(dataset.test_original)


def boundary_masks(distances: np.ndarray) -> dict[int, np.ndarray]:
    return {
        quantile: distances <= float(np.percentile(distances, quantile))
        for quantile in BOUNDARY_QUANTILES
    }


def evaluate_budget(
    *,
    benchmark: str,
    method: str,
    seed: int,
    budget: int,
    gp,
    dataset: object,
    test_distances: np.ndarray,
    test_masks: dict[int, np.ndarray],
) -> dict[str, object]:
    test_mean, test_std = gp.predict(dataset.test_scaled, return_std=True)
    prediction = np.where(test_mean >= 0.0, 1.0, -1.0)
    errors = prediction != dataset.test_labels
    uncertainty = np.abs(test_mean) <= UNCERTAINTY_MULTIPLIER * test_std
    row: dict[str, object] = {
        "benchmark": benchmark,
        "method": method,
        "seed": seed,
        "budget": budget,
        "global_error": float(np.mean(errors)),
        "latent_uncertainty_region_fraction": float(np.mean(uncertainty)),
    }
    for quantile, mask in test_masks.items():
        row[f"near_boundary_error_q{quantile}"] = float(np.mean(errors[mask]))
        row[f"latent_uncertainty_region_fraction_q{quantile}"] = float(np.mean(uncertainty[mask]))
        row[f"near_boundary_test_size_q{quantile}"] = int(mask.sum())
    return row


def run_method(config: BenchmarkConfig, design: object, method: str) -> MethodRun:
    dataset = design.dataset
    pool_values, test_values = get_dataset_values(dataset, config)
    pool_distances = np.abs(pool_values - config.threshold)
    test_distances = np.abs(test_values - config.threshold)
    pool_masks = boundary_masks(pool_distances)
    test_masks = boundary_masks(test_distances)
    labelled = list(design.initial_indices)
    initial_copy = list(design.initial_indices)
    rng = rng_for_week5_method(design.seed, method, config.name)
    budgets: list[int] = []
    metric_rows: list[dict[str, object]] = []
    query_rows: list[dict[str, object]] = []

    while True:
        gp = fit_gp(dataset.pool_scaled[labelled], dataset.pool_labels[labelled], design.seed)
        budget = len(labelled)
        budgets.append(budget)
        metric_rows.append(
            evaluate_budget(
                benchmark=config.name,
                method=method,
                seed=design.seed,
                budget=budget,
                gp=gp,
                dataset=dataset,
                test_distances=test_distances,
                test_masks=test_masks,
            )
        )
        if budget == config.total_budget:
            break

        mask = np.ones(len(dataset.pool_labels), dtype=bool)
        mask[labelled] = False
        unlabelled = np.flatnonzero(mask)
        metadata: dict[str, object]
        if method == "random":
            choice = choose_next_index(method, unlabelled, None, None, rng)
            next_index = choice.index
            metadata = dict(choice.metadata)
        else:
            pool_mean, pool_std = gp.predict(dataset.pool_scaled[unlabelled], return_std=True)
            if method == "diversified_straddle":
                next_index, metadata = choose_diversified_straddle(
                    unlabelled_indices=unlabelled,
                    mu=pool_mean,
                    sigma=pool_std,
                    pool_scaled=dataset.pool_scaled,
                    labelled_indices=labelled,
                    alpha=DIVERSIFIED_ALPHA,
                )
            elif method == "boundary_gated_diversified_straddle":
                next_index, metadata = choose_boundary_gated_diversified_straddle(
                    unlabelled_indices=unlabelled,
                    mu=pool_mean,
                    sigma=pool_std,
                    pool_scaled=dataset.pool_scaled,
                    labelled_indices=labelled,
                    gate_fraction=BOUNDARY_GATED_GATE_FRACTION,
                    beta=BOUNDARY_GATED_BETA,
                    min_shortlist_size=BOUNDARY_GATED_MIN_SHORTLIST_SIZE,
                )
            elif method == "gated_geometric_boundary_contraction":
                next_index, metadata = choose_gated_geometric_boundary_contraction(
                    unlabelled_indices=unlabelled,
                    mu=pool_mean,
                    sigma=pool_std,
                    gp=gp,
                    pool_scaled=dataset.pool_scaled,
                    labelled_indices=labelled,
                    shortlist_size=GBC_SHORTLIST_SIZE,
                    finite_difference_h=GBC_FINITE_DIFFERENCE_H,
                    curvature_clip=GBC_CURVATURE_CLIP,
                    repulsion_bandwidth=GBC_REPULSION_BANDWIDTH,
                    boundary_weight_power=GBC_BOUNDARY_WEIGHT_POWER,
                )
            else:
                choice = choose_next_index(method, unlabelled, pool_mean, pool_std, rng)
                next_index = choice.index
                metadata = dict(choice.metadata)

        query_row: dict[str, object] = {
            "benchmark": config.name,
            "method": method,
            "seed": design.seed,
            "query_number": len(query_rows) + 1,
            "budget_before_query": budget,
            "budget_after_query": budget + 1,
            "selected_pool_index": next_index,
            "true_boundary_distance": float(pool_distances[next_index]),
        }
        for quantile, band_mask in pool_masks.items():
            query_row[f"in_pool_boundary_band_q{quantile}"] = bool(band_mask[next_index])
        for key, value in metadata.items():
            query_row[f"acquisition_{key}"] = value
        query_rows.append(query_row)
        labelled.append(next_index)

    if labelled[: len(initial_copy)] != initial_copy:
        raise RuntimeError("Initial labelled indices were mutated")
    return MethodRun(
        benchmark=config.name,
        method=method,
        seed=design.seed,
        initial_indices=initial_copy,
        labelled_indices=labelled,
        budgets=budgets,
        metric_rows=metric_rows,
        query_rows=query_rows,
        threshold=config.threshold,
        pool_signature=array_signature(dataset.pool_scaled, dataset.pool_labels),
        test_signature=array_signature(dataset.test_scaled, dataset.test_labels),
    )


def verify_fairness(runs_by_method: dict[str, list[MethodRun]]) -> dict[str, object]:
    seeds = sorted({run.seed for runs in runs_by_method.values() for run in runs})
    checks: dict[str, object] = {
        "same_initial_indices_per_seed": {},
        "same_threshold_per_seed": {},
        "same_pool_per_seed": {},
        "same_test_per_seed": {},
        "same_budget_grid_per_seed": {},
        "same_gp_model_function": True,
        "only_acquisition_rule_changes": True,
    }
    for seed in seeds:
        seed_runs = [run for runs in runs_by_method.values() for run in runs if run.seed == seed]
        first = seed_runs[0]
        checks["same_initial_indices_per_seed"][str(seed)] = all(
            run.initial_indices == first.initial_indices for run in seed_runs
        )
        checks["same_threshold_per_seed"][str(seed)] = all(
            run.threshold == first.threshold for run in seed_runs
        )
        checks["same_pool_per_seed"][str(seed)] = all(
            run.pool_signature == first.pool_signature for run in seed_runs
        )
        checks["same_test_per_seed"][str(seed)] = all(
            run.test_signature == first.test_signature for run in seed_runs
        )
        checks["same_budget_grid_per_seed"][str(seed)] = all(
            run.budgets == first.budgets for run in seed_runs
        )
    leaf_values = []
    for value in checks.values():
        if isinstance(value, dict):
            leaf_values.extend(bool(item) for item in value.values())
        else:
            leaf_values.append(bool(value))
    checks["all_checks_passed"] = all(leaf_values)
    return checks


def summarize_selected_budgets(config: BenchmarkConfig, raw_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    metrics = [
        "global_error",
        "near_boundary_error_q10",
        "near_boundary_error_q20",
        "near_boundary_error_q30",
        "latent_uncertainty_region_fraction",
        "latent_uncertainty_region_fraction_q20",
        "latent_uncertainty_region_fraction_q30",
    ]
    for method in WEEK5_METHODS:
        for budget in config.selected_budgets:
            subset = [row for row in raw_rows if row["method"] == method and row["budget"] == budget]
            row: dict[str, object] = {"benchmark": config.name, "method": method, "budget": budget}
            for metric in metrics:
                mean, std = mean_std([float(item[metric]) for item in subset])
                row[f"mean_{metric}"] = f"{mean:.6f}"
                row[f"std_{metric}"] = f"{std:.6f}"
            rows.append(row)
    return rows


def summarize_final_metrics(config: BenchmarkConfig, raw_rows: list[dict[str, object]], query_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    final_metric_fields = [
        "global_error",
        "near_boundary_error_q10",
        "near_boundary_error_q20",
        "near_boundary_error_q30",
        "latent_uncertainty_region_fraction",
        "latent_uncertainty_region_fraction_q20",
        "latent_uncertainty_region_fraction_q30",
    ]
    raw_means: dict[str, dict[str, float]] = {}
    for method in WEEK5_METHODS:
        subset = [row for row in raw_rows if row["method"] == method and row["budget"] == config.total_budget]
        raw_means[method] = {
            metric: mean_std([float(item[metric]) for item in subset])[0]
            for metric in final_metric_fields
        }
        method_queries = [row for row in query_rows if row["method"] == method]
        distances = np.asarray([float(row["true_boundary_distance"]) for row in method_queries])
        raw_means[method]["median_query_distance"] = float(np.median(distances))

    ranks = {
        metric: {
            method: rank + 1
            for rank, (method, _) in enumerate(
                sorted(
                    ((method, values[metric]) for method, values in raw_means.items()),
                    key=lambda item: item[1],
                )
            )
        }
        for metric in [*final_metric_fields, "median_query_distance"]
    }

    for method in WEEK5_METHODS:
        subset = [row for row in raw_rows if row["method"] == method and row["budget"] == config.total_budget]
        method_queries = [row for row in query_rows if row["method"] == method]
        distances = np.asarray([float(row["true_boundary_distance"]) for row in method_queries])
        row: dict[str, object] = {"benchmark": config.name, "method": method}
        for metric in final_metric_fields:
            mean, std = mean_std([float(item[metric]) for item in subset])
            row[f"mean_final_{metric}"] = f"{mean:.6f}"
            row[f"std_final_{metric}"] = f"{std:.6f}"
            row[f"rank_final_{metric}"] = ranks[metric][method]
        row.update(
            {
                "mean_query_distance": f"{float(distances.mean()):.6f}",
                "median_query_distance": f"{float(np.median(distances)):.6f}",
                "query_distance_q25": f"{float(np.percentile(distances, 25)):.6f}",
                "query_distance_q75": f"{float(np.percentile(distances, 75)):.6f}",
                "fraction_queries_in_pool_boundary_band_q10": f"{np.mean([bool(item['in_pool_boundary_band_q10']) for item in method_queries]):.6f}",
                "fraction_queries_in_pool_boundary_band_q20": f"{np.mean([bool(item['in_pool_boundary_band_q20']) for item in method_queries]):.6f}",
                "fraction_queries_in_pool_boundary_band_q30": f"{np.mean([bool(item['in_pool_boundary_band_q30']) for item in method_queries]):.6f}",
                "rank_median_query_distance": ranks["median_query_distance"][method],
            }
        )
        rows.append(row)
    return rows


def best_method(rows: list[dict[str, object]], field: str, methods: tuple[str, ...] = WEEK5_METHODS) -> str:
    return min((row for row in rows if row["method"] in methods), key=lambda row: float(row[field]))["method"]


def plot_metric_curves(
    raw_rows: list[dict[str, object]],
    metric: str,
    config: BenchmarkConfig,
    output_path: Path,
    title: str,
    ylabel: str,
) -> None:
    fig, ax = plt.subplots(figsize=(10.8, 6.4))
    for method in WEEK5_METHODS:
        method_rows = [row for row in raw_rows if row["method"] == method]
        budgets = sorted({int(row["budget"]) for row in method_rows})
        values_by_seed = []
        for seed in SEEDS:
            seed_rows = sorted(
                [row for row in method_rows if row["seed"] == seed],
                key=lambda row: int(row["budget"]),
            )
            values_by_seed.append([float(row[metric]) for row in seed_rows])
        values = np.asarray(values_by_seed, dtype=float)
        mean = values.mean(axis=0)
        std = values.std(axis=0)
        ax.plot(budgets, mean, color=METHOD_COLORS[method], label=method, linewidth=2.3)
        ax.fill_between(
            budgets,
            np.maximum(0.0, mean - std),
            np.minimum(1.0, mean + std),
            color=METHOD_COLORS[method],
            alpha=0.10,
            linewidth=0,
        )
    ax.set(title=title, xlabel="Labelled evaluations", ylabel=ylabel, xlim=(config.initial_size, config.total_budget))
    ax.grid(alpha=0.25)
    ax.legend(title="Acquisition rule", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_final_global_vs_near(final_rows: list[dict[str, object]], config: BenchmarkConfig, output_path: Path) -> None:
    metrics = [
        ("mean_final_global_error", "global"),
        ("mean_final_near_boundary_error_q20", "q20"),
        ("mean_final_near_boundary_error_q30", "q30"),
    ]
    positions = np.arange(len(WEEK5_METHODS))
    width = 0.22
    fig, ax = plt.subplots(figsize=(12, 6.3))
    for offset, (field, label) in enumerate(metrics):
        values = [float(next(row for row in final_rows if row["method"] == method)[field]) for method in WEEK5_METHODS]
        ax.bar(positions + (offset - 1) * width, values, width=width, label=label, alpha=0.88)
    ax.set_xticks(positions)
    ax.set_xticklabels([method.replace("_", "\n") for method in WEEK5_METHODS], fontsize=9)
    ax.set(title=f"{config.display_name}: final global vs near-boundary error", ylabel="Mean final error over seeds")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(title="Metric")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_query_distance_boxplot(query_rows: list[dict[str, object]], config: BenchmarkConfig, output_path: Path) -> None:
    data = []
    for method in WEEK5_METHODS:
        data.append([max(float(row["true_boundary_distance"]), 1e-12) for row in query_rows if row["method"] == method])
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.boxplot(data, tick_labels=[method.replace("_", "\n") for method in WEEK5_METHODS], showfliers=False)
    ax.set_yscale("log")
    ax.set(title=f"{config.display_name}: query distance to true boundary", ylabel="abs(f(x_query)-threshold), log scale")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_query_distance_median_iqr(query_rows: list[dict[str, object]], config: BenchmarkConfig, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.8, 6.3))
    for method in WEEK5_METHODS:
        method_rows = [row for row in query_rows if row["method"] == method]
        query_numbers = sorted({int(row["query_number"]) for row in method_rows})
        medians = []
        q25_values = []
        q75_values = []
        budgets_after = []
        for query_number in query_numbers:
            subset = [row for row in method_rows if row["query_number"] == query_number]
            values = np.asarray([max(float(row["true_boundary_distance"]), 1e-12) for row in subset])
            medians.append(float(np.median(values)))
            q25_values.append(float(np.percentile(values, 25)))
            q75_values.append(float(np.percentile(values, 75)))
            budgets_after.append(int(subset[0]["budget_after_query"]))
        ax.plot(budgets_after, medians, color=METHOD_COLORS[method], label=method, linewidth=2.2)
        ax.fill_between(budgets_after, np.maximum(1e-12, q25_values), q75_values, color=METHOD_COLORS[method], alpha=0.11, linewidth=0)
    ax.set_yscale("log")
    ax.set(
        title=f"{config.display_name}: median query distance over budget",
        xlabel="Labelled evaluations after query",
        ylabel="median abs(f(x_query)-threshold), q25-q75 band, log scale",
        xlim=(config.initial_size + 1, config.total_budget),
    )
    ax.grid(alpha=0.25)
    ax.legend(title="Acquisition rule", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_gbc_factor_distributions(gbc_rows: list[dict[str, object]], config: BenchmarkConfig, output_path: Path) -> None:
    factors = [
        ("acquisition_selected_normalized_curvature", "curvature"),
        ("acquisition_selected_normalized_uncertainty", "uncertainty"),
        ("acquisition_selected_boundary_weight", "boundary weight"),
        ("acquisition_selected_repulsion", "repulsion"),
        ("acquisition_selected_gbc_score", "GBC score"),
    ]
    data = [
        [float(row[field]) for row in gbc_rows if row.get(field) not in (None, "")]
        for field, _ in factors
    ]
    fig, ax = plt.subplots(figsize=(9.8, 5.8))
    ax.boxplot(data, tick_labels=[label for _, label in factors], showfliers=False)
    ax.set(
        title=f"{config.display_name}: selected GBC factor distributions",
        ylabel="Selected-point factor value",
    )
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def comparison_rows_for_benchmark(final_rows: list[dict[str, object]], config: BenchmarkConfig) -> list[dict[str, object]]:
    gbc = next(row for row in final_rows if row["method"] == "gated_geometric_boundary_contraction")
    comparators = [
        ("straddle", "straddle"),
        ("randomized_straddle", "randomized_straddle"),
        ("diversified_straddle", "diversified_straddle"),
        ("boundary_gated_diversified_straddle", "boundary_gated_diversified_straddle"),
        ("best_original_global", best_method(final_rows, "mean_final_global_error", ORIGINAL_METHODS)),
        ("best_original_q20", best_method(final_rows, "mean_final_near_boundary_error_q20", ORIGINAL_METHODS)),
        ("best_original_q30", best_method(final_rows, "mean_final_near_boundary_error_q30", ORIGINAL_METHODS)),
    ]
    rows: list[dict[str, object]] = []
    for role, method in comparators:
        comparator = next(row for row in final_rows if row["method"] == method)
        rows.append(
            {
                "benchmark": config.name,
                "comparator_role": role,
                "comparator_method": method,
                "gbc_global_error": gbc["mean_final_global_error"],
                "comparator_global_error": comparator["mean_final_global_error"],
                "global_error_diff": f"{float(gbc['mean_final_global_error']) - float(comparator['mean_final_global_error']):.6f}",
                "gbc_q20_error": gbc["mean_final_near_boundary_error_q20"],
                "comparator_q20_error": comparator["mean_final_near_boundary_error_q20"],
                "q20_error_diff": f"{float(gbc['mean_final_near_boundary_error_q20']) - float(comparator['mean_final_near_boundary_error_q20']):.6f}",
                "gbc_q30_error": gbc["mean_final_near_boundary_error_q30"],
                "comparator_q30_error": comparator["mean_final_near_boundary_error_q30"],
                "q30_error_diff": f"{float(gbc['mean_final_near_boundary_error_q30']) - float(comparator['mean_final_near_boundary_error_q30']):.6f}",
                "gbc_median_query_distance": gbc["median_query_distance"],
                "comparator_median_query_distance": comparator["median_query_distance"],
                "median_query_distance_diff": f"{float(gbc['median_query_distance']) - float(comparator['median_query_distance']):.6f}",
                "gbc_global_uncertainty_fraction": gbc["mean_final_latent_uncertainty_region_fraction"],
                "comparator_global_uncertainty_fraction": comparator["mean_final_latent_uncertainty_region_fraction"],
                "global_uncertainty_fraction_diff": f"{float(gbc['mean_final_latent_uncertainty_region_fraction']) - float(comparator['mean_final_latent_uncertainty_region_fraction']):.6f}",
                "gbc_q20_uncertainty_fraction": gbc["mean_final_latent_uncertainty_region_fraction_q20"],
                "comparator_q20_uncertainty_fraction": comparator["mean_final_latent_uncertainty_region_fraction_q20"],
                "q20_uncertainty_fraction_diff": f"{float(gbc['mean_final_latent_uncertainty_region_fraction_q20']) - float(comparator['mean_final_latent_uncertainty_region_fraction_q20']):.6f}",
                "gbc_q30_uncertainty_fraction": gbc["mean_final_latent_uncertainty_region_fraction_q30"],
                "comparator_q30_uncertainty_fraction": comparator["mean_final_latent_uncertainty_region_fraction_q30"],
                "q30_uncertainty_fraction_diff": f"{float(gbc['mean_final_latent_uncertainty_region_fraction_q30']) - float(comparator['mean_final_latent_uncertainty_region_fraction_q30']):.6f}",
                "negative_is_better_for_all_differences": True,
            }
        )
    return rows


def combined_row_for_benchmark(result: BenchmarkResult) -> dict[str, object]:
    final_rows = result.final_rows
    gbc = next(row for row in final_rows if row["method"] == "gated_geometric_boundary_contraction")
    gated = next(row for row in final_rows if row["method"] == "boundary_gated_diversified_straddle")
    diversified = next(row for row in final_rows if row["method"] == "diversified_straddle")
    best_original_global = best_method(final_rows, "mean_final_global_error", ORIGINAL_METHODS)
    best_original_q20 = best_method(final_rows, "mean_final_near_boundary_error_q20", ORIGINAL_METHODS)
    best_original_q30 = best_method(final_rows, "mean_final_near_boundary_error_q30", ORIGINAL_METHODS)
    best_original_global_row = next(row for row in final_rows if row["method"] == best_original_global)
    best_original_q20_row = next(row for row in final_rows if row["method"] == best_original_q20)
    best_original_q30_row = next(row for row in final_rows if row["method"] == best_original_q30)
    straddle = next(row for row in final_rows if row["method"] == "straddle")
    randomized = next(row for row in final_rows if row["method"] == "randomized_straddle")
    smallest_abs_mu = next(row for row in final_rows if row["method"] == "smallest_abs_mu")
    expected_feasibility = next(row for row in final_rows if row["method"] == "expected_feasibility")
    return {
        "benchmark": result.config.name,
        "display_name": result.config.display_name,
        "diversified_alpha": DIVERSIFIED_ALPHA,
        "boundary_gated_gate_fraction": BOUNDARY_GATED_GATE_FRACTION,
        "boundary_gated_beta": BOUNDARY_GATED_BETA,
        "boundary_gated_min_shortlist_size": BOUNDARY_GATED_MIN_SHORTLIST_SIZE,
        "gbc_shortlist_size": GBC_SHORTLIST_SIZE,
        "gbc_finite_difference_h": GBC_FINITE_DIFFERENCE_H,
        "gbc_curvature_clip": GBC_CURVATURE_CLIP,
        "gbc_repulsion_bandwidth": GBC_REPULSION_BANDWIDTH,
        "gbc_boundary_weight_power": GBC_BOUNDARY_WEIGHT_POWER,
        "gbc_global_error": gbc["mean_final_global_error"],
        "gbc_q20_error": gbc["mean_final_near_boundary_error_q20"],
        "gbc_q30_error": gbc["mean_final_near_boundary_error_q30"],
        "gbc_median_query_distance": gbc["median_query_distance"],
        "gbc_global_uncertainty_fraction": gbc["mean_final_latent_uncertainty_region_fraction"],
        "gbc_q20_uncertainty_fraction": gbc["mean_final_latent_uncertainty_region_fraction_q20"],
        "gbc_q30_uncertainty_fraction": gbc["mean_final_latent_uncertainty_region_fraction_q30"],
        "boundary_gated_global_error": gated["mean_final_global_error"],
        "boundary_gated_q20_error": gated["mean_final_near_boundary_error_q20"],
        "boundary_gated_q30_error": gated["mean_final_near_boundary_error_q30"],
        "boundary_gated_median_query_distance": gated["median_query_distance"],
        "boundary_gated_q20_uncertainty_fraction": gated["mean_final_latent_uncertainty_region_fraction_q20"],
        "boundary_gated_q30_uncertainty_fraction": gated["mean_final_latent_uncertainty_region_fraction_q30"],
        "diversified_global_error": diversified["mean_final_global_error"],
        "diversified_q20_error": diversified["mean_final_near_boundary_error_q20"],
        "diversified_q30_error": diversified["mean_final_near_boundary_error_q30"],
        "diversified_median_query_distance": diversified["median_query_distance"],
        "best_original_global_method": best_original_global,
        "best_original_global_error": best_original_global_row["mean_final_global_error"],
        "improves_global_over_best_original": float(gbc["mean_final_global_error"]) < float(best_original_global_row["mean_final_global_error"]),
        "improves_global_over_straddle": float(gbc["mean_final_global_error"]) < float(straddle["mean_final_global_error"]),
        "improves_global_over_randomized_straddle": float(gbc["mean_final_global_error"]) < float(randomized["mean_final_global_error"]),
        "improves_global_over_diversified_straddle": float(gbc["mean_final_global_error"]) < float(diversified["mean_final_global_error"]),
        "improves_global_over_boundary_gated_diversified_straddle": float(gbc["mean_final_global_error"]) < float(gated["mean_final_global_error"]),
        "best_original_q20_method": best_original_q20,
        "best_original_q20_error": best_original_q20_row["mean_final_near_boundary_error_q20"],
        "improves_q20_over_best_original": float(gbc["mean_final_near_boundary_error_q20"]) < float(best_original_q20_row["mean_final_near_boundary_error_q20"]),
        "improves_q20_over_straddle": float(gbc["mean_final_near_boundary_error_q20"]) < float(straddle["mean_final_near_boundary_error_q20"]),
        "improves_q20_over_randomized_straddle": float(gbc["mean_final_near_boundary_error_q20"]) < float(randomized["mean_final_near_boundary_error_q20"]),
        "improves_q20_over_diversified_straddle": float(gbc["mean_final_near_boundary_error_q20"]) < float(diversified["mean_final_near_boundary_error_q20"]),
        "improves_q20_over_boundary_gated_diversified_straddle": float(gbc["mean_final_near_boundary_error_q20"]) < float(gated["mean_final_near_boundary_error_q20"]),
        "best_original_q30_method": best_original_q30,
        "best_original_q30_error": best_original_q30_row["mean_final_near_boundary_error_q30"],
        "improves_q30_over_best_original": float(gbc["mean_final_near_boundary_error_q30"]) < float(best_original_q30_row["mean_final_near_boundary_error_q30"]),
        "improves_q30_over_straddle": float(gbc["mean_final_near_boundary_error_q30"]) < float(straddle["mean_final_near_boundary_error_q30"]),
        "improves_q30_over_randomized_straddle": float(gbc["mean_final_near_boundary_error_q30"]) < float(randomized["mean_final_near_boundary_error_q30"]),
        "improves_q30_over_diversified_straddle": float(gbc["mean_final_near_boundary_error_q30"]) < float(diversified["mean_final_near_boundary_error_q30"]),
        "improves_q30_over_boundary_gated_diversified_straddle": float(gbc["mean_final_near_boundary_error_q30"]) < float(gated["mean_final_near_boundary_error_q30"]),
        "queries_closer_than_diversified_straddle": float(gbc["median_query_distance"]) < float(diversified["median_query_distance"]),
        "queries_closer_than_straddle": float(gbc["median_query_distance"]) < float(straddle["median_query_distance"]),
        "queries_closer_than_randomized_straddle": float(gbc["median_query_distance"]) < float(randomized["median_query_distance"]),
        "queries_closer_than_boundary_gated_diversified_straddle": float(gbc["median_query_distance"]) < float(gated["median_query_distance"]),
        "queries_closer_than_smallest_abs_mu": float(gbc["median_query_distance"]) < float(smallest_abs_mu["median_query_distance"]),
        "reduces_global_uncertainty_vs_straddle": float(gbc["mean_final_latent_uncertainty_region_fraction"]) < float(straddle["mean_final_latent_uncertainty_region_fraction"]),
        "reduces_global_uncertainty_vs_randomized_straddle": float(gbc["mean_final_latent_uncertainty_region_fraction"]) < float(randomized["mean_final_latent_uncertainty_region_fraction"]),
        "reduces_global_uncertainty_vs_boundary_gated_diversified_straddle": float(gbc["mean_final_latent_uncertainty_region_fraction"]) < float(gated["mean_final_latent_uncertainty_region_fraction"]),
        "reduces_q20_uncertainty_vs_diversified_straddle": float(gbc["mean_final_latent_uncertainty_region_fraction_q20"]) < float(diversified["mean_final_latent_uncertainty_region_fraction_q20"]),
        "reduces_q20_uncertainty_vs_straddle": float(gbc["mean_final_latent_uncertainty_region_fraction_q20"]) < float(straddle["mean_final_latent_uncertainty_region_fraction_q20"]),
        "reduces_q20_uncertainty_vs_randomized_straddle": float(gbc["mean_final_latent_uncertainty_region_fraction_q20"]) < float(randomized["mean_final_latent_uncertainty_region_fraction_q20"]),
        "reduces_q20_uncertainty_vs_boundary_gated_diversified_straddle": float(gbc["mean_final_latent_uncertainty_region_fraction_q20"]) < float(gated["mean_final_latent_uncertainty_region_fraction_q20"]),
        "reduces_q20_uncertainty_vs_expected_feasibility": float(gbc["mean_final_latent_uncertainty_region_fraction_q20"]) < float(expected_feasibility["mean_final_latent_uncertainty_region_fraction_q20"]),
        "reduces_q30_uncertainty_vs_diversified_straddle": float(gbc["mean_final_latent_uncertainty_region_fraction_q30"]) < float(diversified["mean_final_latent_uncertainty_region_fraction_q30"]),
        "reduces_q30_uncertainty_vs_straddle": float(gbc["mean_final_latent_uncertainty_region_fraction_q30"]) < float(straddle["mean_final_latent_uncertainty_region_fraction_q30"]),
        "reduces_q30_uncertainty_vs_randomized_straddle": float(gbc["mean_final_latent_uncertainty_region_fraction_q30"]) < float(randomized["mean_final_latent_uncertainty_region_fraction_q30"]),
        "reduces_q30_uncertainty_vs_boundary_gated_diversified_straddle": float(gbc["mean_final_latent_uncertainty_region_fraction_q30"]) < float(gated["mean_final_latent_uncertainty_region_fraction_q30"]),
        "reduces_q30_uncertainty_vs_expected_feasibility": float(gbc["mean_final_latent_uncertainty_region_fraction_q30"]) < float(expected_feasibility["mean_final_latent_uncertainty_region_fraction_q30"]),
    }


def write_notes(result: BenchmarkResult, output_path: Path) -> None:
    row = result.combined_row
    final_rows = result.final_rows
    gbc = next(item for item in final_rows if item["method"] == "gated_geometric_boundary_contraction")
    gated = next(item for item in final_rows if item["method"] == "boundary_gated_diversified_straddle")
    diversified = next(item for item in final_rows if item["method"] == "diversified_straddle")
    improved_core = (
        row["improves_global_over_best_original"]
        or row["improves_q20_over_best_original"]
        or row["improves_q30_over_best_original"]
    )
    if improved_core:
        interpretation = (
            "The result suggests that adding local geometric information from "
            "the GP posterior boundary can help sample-efficient boundary "
            "learning. The curvature factor may help prioritize geometrically "
            "difficult parts of the predicted boundary. The method is still "
            "heuristic because curvature is estimated from the GP-regression "
            "posterior mean, not the true boundary."
        )
    else:
        interpretation = (
            "The result suggests that finite-difference curvature under the "
            "current GP-regression surrogate is not reliably aligned with true "
            "boundary classification accuracy. Possible reasons are noisy "
            "curvature estimates, a crude diagonal Hessian approximation, a GP "
            "regressor surrogate that does not represent the boundary well "
            "enough, input-space curvature that does not match useful boundary "
            "information, or the need to transition to a GP classifier."
        )
    text = f"""# Week 5.3 Gated GBC Notes: {result.config.display_name}

## New method

The previous Week 5.1 methods are preserved:

- `diversified_straddle`
- `boundary_gated_diversified_straddle`

The new `gated_geometric_boundary_contraction` first keeps the top
`{GBC_SHORTLIST_SIZE}` unlabelled candidates by straddle score:

`1.96 * sigma(x) - abs(mu(x))`

Inside this boundary-relevant shortlist it computes:

`normalized_curvature * normalized_uncertainty * boundary_weight * repulsion`

Curvature is a finite-difference diagonal-Hessian proxy of the GP posterior
mean in scaled coordinates. The boundary weight uses
`Phi(mu / sqrt(1 + sigma^2))` as a GP-regression latent probability heuristic,
then maps it to `1 - 2 * abs(p - 0.5)`. Repulsion uses distance to the nearest
currently labelled point with fixed bandwidth `{GBC_REPULSION_BANDWIDTH}`.

## Main result

- GBC final global error: `{float(gbc['mean_final_global_error']):.3f}`.
- GBC final q20 near-boundary error: `{float(gbc['mean_final_near_boundary_error_q20']):.3f}`.
- GBC final q30 near-boundary error: `{float(gbc['mean_final_near_boundary_error_q30']):.3f}`.
- GBC median query distance: `{float(gbc['median_query_distance']):.6f}`.
- GBC global uncertainty-region fraction: `{float(gbc['mean_final_latent_uncertainty_region_fraction']):.3f}`.
- GBC q20 uncertainty-region fraction: `{float(gbc['mean_final_latent_uncertainty_region_fraction_q20']):.3f}`.
- GBC q30 uncertainty-region fraction: `{float(gbc['mean_final_latent_uncertainty_region_fraction_q30']):.3f}`.
- Boundary-gated global error: `{float(gated['mean_final_global_error']):.3f}`.
- Diversified global error: `{float(diversified['mean_final_global_error']):.3f}`.

## Comparison

- Improves global error over best original method: `{row['improves_global_over_best_original']}`.
- Improves global error over `straddle`: `{row['improves_global_over_straddle']}`.
- Improves global error over `randomized_straddle`: `{row['improves_global_over_randomized_straddle']}`.
- Improves global error over `diversified_straddle`: `{row['improves_global_over_diversified_straddle']}`.
- Improves global error over `boundary_gated_diversified_straddle`: `{row['improves_global_over_boundary_gated_diversified_straddle']}`.
- Improves q20 error over best original method: `{row['improves_q20_over_best_original']}`.
- Improves q20 error over `straddle`: `{row['improves_q20_over_straddle']}`.
- Improves q20 error over `randomized_straddle`: `{row['improves_q20_over_randomized_straddle']}`.
- Improves q20 error over `diversified_straddle`: `{row['improves_q20_over_diversified_straddle']}`.
- Improves q20 error over `boundary_gated_diversified_straddle`: `{row['improves_q20_over_boundary_gated_diversified_straddle']}`.
- Improves q30 error over best original method: `{row['improves_q30_over_best_original']}`.
- Improves q30 error over `straddle`: `{row['improves_q30_over_straddle']}`.
- Improves q30 error over `randomized_straddle`: `{row['improves_q30_over_randomized_straddle']}`.
- Improves q30 error over `diversified_straddle`: `{row['improves_q30_over_diversified_straddle']}`.
- Improves q30 error over `boundary_gated_diversified_straddle`: `{row['improves_q30_over_boundary_gated_diversified_straddle']}`.
- Queries closer than `diversified_straddle`: `{row['queries_closer_than_diversified_straddle']}`.
- Queries closer than `straddle`: `{row['queries_closer_than_straddle']}`.
- Queries closer than `randomized_straddle`: `{row['queries_closer_than_randomized_straddle']}`.
- Queries closer than `boundary_gated_diversified_straddle`: `{row['queries_closer_than_boundary_gated_diversified_straddle']}`.
- Reduces q20 uncertainty-region fraction versus `diversified_straddle`: `{row['reduces_q20_uncertainty_vs_diversified_straddle']}`.
- Reduces q30 uncertainty-region fraction versus `diversified_straddle`: `{row['reduces_q30_uncertainty_vs_diversified_straddle']}`.

## Interpretation

{interpretation}

## Caveats

Query distance measures sampling behavior, not predictive correctness. Near-boundary
distance is a function-value proxy, not Euclidean contour distance. The
uncertainty-region fractions use GP-regression latent uncertainty, not calibrated
class probability. GBC is heuristic; curvature is estimated from the GP
posterior mean, not from the true function. The finite-difference Hessian uses
only diagonal terms for speed. Curvature is evaluated only inside a
straddle-gated shortlist. A lower uncertainty-region fraction does not
necessarily imply correctness.
"""
    output_path.write_text(text, encoding="utf-8")


def save_benchmark_outputs(result: BenchmarkResult, base_output_dir: Path = OUTPUT_DIR) -> None:
    output_dir = base_output_dir / result.config.output_name
    output_dir.mkdir(parents=True, exist_ok=True)
    gbc_metadata_rows = [
        row
        for row in result.query_rows
        if row["method"] == "gated_geometric_boundary_contraction"
    ]
    write_csv(output_dir / "raw_metrics.csv", result.raw_metric_rows)
    write_csv(output_dir / "query_distance_table.csv", result.query_rows)
    write_csv(output_dir / "gbc_metadata_table.csv", gbc_metadata_rows)
    write_csv(output_dir / "final_metrics_table.csv", result.final_rows)
    write_csv(output_dir / "selected_budget_metrics_table.csv", result.selected_budget_rows)
    plot_metric_curves(result.raw_metric_rows, "global_error", result.config, output_dir / "global_error_curves.png", f"{result.config.display_name}: global error", "Global test-label error")
    plot_metric_curves(result.raw_metric_rows, "near_boundary_error_q20", result.config, output_dir / "near_boundary_error_curves_q20.png", f"{result.config.display_name}: q20 near-boundary error", "Error on closest 20% test points")
    plot_metric_curves(result.raw_metric_rows, "near_boundary_error_q30", result.config, output_dir / "near_boundary_error_curves_q30.png", f"{result.config.display_name}: q30 near-boundary error", "Error on closest 30% test points")
    plot_final_global_vs_near(result.final_rows, result.config, output_dir / "final_global_vs_near_boundary_error.png")
    plot_query_distance_boxplot(result.query_rows, result.config, output_dir / "query_distance_to_boundary_boxplot.png")
    plot_query_distance_median_iqr(result.query_rows, result.config, output_dir / "query_distance_to_boundary_over_budget_median_iqr.png")
    plot_metric_curves(result.raw_metric_rows, "latent_uncertainty_region_fraction", result.config, output_dir / "uncertainty_region_fraction_curves_global.png", f"{result.config.display_name}: global uncertainty-region fraction", "Global fraction with abs(mu)<=1.96*sigma")
    plot_metric_curves(result.raw_metric_rows, "latent_uncertainty_region_fraction_q20", result.config, output_dir / "uncertainty_region_fraction_curves_q20.png", f"{result.config.display_name}: q20 uncertainty-region fraction", "Closest 20% fraction with abs(mu)<=1.96*sigma")
    plot_metric_curves(result.raw_metric_rows, "latent_uncertainty_region_fraction_q30", result.config, output_dir / "uncertainty_region_fraction_curves_q30.png", f"{result.config.display_name}: q30 uncertainty-region fraction", "Closest 30% fraction with abs(mu)<=1.96*sigma")
    plot_gbc_factor_distributions(gbc_metadata_rows, result.config, output_dir / "gbc_factor_distributions.png")
    write_notes(result, output_dir / "week5_3_gbc_notes.md")
    summary = {
        "experiment": f"week5_3_gated_geometric_boundary_contraction_{result.config.name}",
        "benchmark": result.config.name,
        "display_name": result.config.display_name,
        "domain": result.config.domain,
        "threshold": result.config.threshold,
        "threshold_percentile": result.config.threshold_percentile,
        "seeds": list(SEEDS),
        "pool_size": result.config.pool_size,
        "test_size": result.config.test_size,
        "initial_labelled_size": result.config.initial_size,
        "total_budget": result.config.total_budget,
        "methods": list(WEEK5_METHODS),
        "diversified_straddle_alpha": DIVERSIFIED_ALPHA,
        "diversified_straddle_definition": METHOD_DESCRIPTIONS_WEEK5["diversified_straddle"],
        "boundary_gated_diversified_straddle_gate_fraction": BOUNDARY_GATED_GATE_FRACTION,
        "boundary_gated_diversified_straddle_beta": BOUNDARY_GATED_BETA,
        "boundary_gated_diversified_straddle_min_shortlist_size": BOUNDARY_GATED_MIN_SHORTLIST_SIZE,
        "boundary_gated_diversified_straddle_definition": METHOD_DESCRIPTIONS_WEEK5["boundary_gated_diversified_straddle"],
        "gated_geometric_boundary_contraction_definition": METHOD_DESCRIPTIONS_WEEK5["gated_geometric_boundary_contraction"],
        "gbc_shortlist_size": GBC_SHORTLIST_SIZE,
        "gbc_finite_difference_h": GBC_FINITE_DIFFERENCE_H,
        "gbc_curvature_clip": GBC_CURVATURE_CLIP,
        "gbc_repulsion_bandwidth": GBC_REPULSION_BANDWIDTH,
        "gbc_boundary_weight_power": GBC_BOUNDARY_WEIGHT_POWER,
        "gbc_boundary_weight_rule": "p = Phi(mu / sqrt(1 + sigma^2)); boundary_weight = clip(1 - 2*abs(p - 0.5), 0, 1)^power",
        "gbc_curvature_rule": "finite-difference diagonal-Hessian proxy of GP posterior mean in scaled coordinates, tangent-projected and clipped",
        "gbc_no_cheating": [
            "Acquisition uses current labelled data, unlabelled coordinates, GP latent mean and standard deviation, finite-difference derivatives of the GP posterior mean, and distances to labelled points.",
            "Acquisition does not use true unlabelled labels, true function values, true boundary distances, test labels, or q10/q20/q30 masks.",
        ],
        "fairness_checks": result.fairness_checks,
        "final_metrics": result.final_rows,
        "selected_budget_metrics": result.selected_budget_rows,
        "combined_summary_row": result.combined_row,
        "comparison_rows": result.comparison_rows,
        "caveats": [
            "gated_geometric_boundary_contraction is a heuristic acquisition rule.",
            "Curvature is estimated from the GP posterior mean, not from the true function.",
            "The finite-difference Hessian uses only diagonal terms for speed.",
            "The boundary weight uses a GP-regression latent probability heuristic, not calibrated GP-classifier probabilities.",
            "Curvature is evaluated only within a straddle-gated shortlist.",
            "The previous Week 5.1 methods are preserved as separate baselines.",
            "Near-boundary distance is a function-value proxy, not Euclidean contour distance.",
            "A good query-distance score does not necessarily imply good boundary classification.",
            "Uncertainty metrics use GP-regression latent uncertainty, not calibrated class probability.",
            "Lower uncertainty-region fraction does not necessarily imply correctness.",
        ],
    }
    (output_dir / "summary.json").write_text(json.dumps(json_ready(summary), indent=2), encoding="utf-8")


def load_lookahead_reference_rows() -> dict[str, dict[str, object]]:
    reference_base = Path(__file__).resolve().parents[1] / "outputs" / "week5_2_lookahead_boundary_uncertainty"
    rows: dict[str, dict[str, object]] = {}
    for benchmark in ("branin", "ackley"):
        path = reference_base / benchmark / "final_metrics_table.csv"
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row["method"] == "lookahead_boundary_uncertainty_reduction":
                    rows[benchmark] = row
                    break
    return rows


def write_combined_outputs(results: list[BenchmarkResult], base_output_dir: Path = OUTPUT_DIR) -> None:
    combined_dir = base_output_dir / "combined"
    combined_dir.mkdir(parents=True, exist_ok=True)
    combined_rows = [result.combined_row for result in results]
    lookahead_reference = load_lookahead_reference_rows()
    for row in combined_rows:
        reference = lookahead_reference.get(str(row["benchmark"]))
        if reference is None:
            row["lookahead_boundary_uncertainty_reduction_reference_available"] = False
        else:
            row["lookahead_boundary_uncertainty_reduction_reference_available"] = True
            row["lookahead_reference_global_error"] = reference["mean_final_global_error"]
            row["lookahead_reference_q20_error"] = reference["mean_final_near_boundary_error_q20"]
            row["lookahead_reference_q30_error"] = reference["mean_final_near_boundary_error_q30"]
            row["lookahead_reference_median_query_distance"] = reference["median_query_distance"]
            row["lookahead_reference_global_uncertainty_fraction"] = reference["mean_final_latent_uncertainty_region_fraction"]
            row["lookahead_reference_q20_uncertainty_fraction"] = reference["mean_final_latent_uncertainty_region_fraction_q20"]
            row["lookahead_reference_q30_uncertainty_fraction"] = reference["mean_final_latent_uncertainty_region_fraction_q30"]
    comparison_rows = [row for result in results for row in result.comparison_rows]
    write_csv(combined_dir / "week5_3_gbc_summary.csv", combined_rows)
    write_csv(combined_dir / "gbc_vs_baselines_table.csv", comparison_rows)
    lines = [
        "# Week 5.3 Gated Geometric Boundary Contraction Summary",
        "",
        f"`gated_geometric_boundary_contraction` uses straddle-gated shortlist size `{GBC_SHORTLIST_SIZE}`.",
        f"Finite-difference h: `{GBC_FINITE_DIFFERENCE_H}`; curvature clip: `{GBC_CURVATURE_CLIP}`; repulsion bandwidth: `{GBC_REPULSION_BANDWIDTH}`.",
        "Week 5.2 lookahead numbers are included only as reference if existing outputs are available; they are not rerun in this Week 5.3 experiment.",
        "",
        "| Benchmark | Global vs best original | Global vs straddle | Global vs gated diversity | q20 vs best original | q20 vs straddle | q20 vs gated diversity | q30 vs best original | q30 vs randomized | q30 vs gated diversity |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in combined_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["display_name"]),
                    str(row["improves_global_over_best_original"]),
                    str(row["improves_global_over_straddle"]),
                    str(row["improves_global_over_boundary_gated_diversified_straddle"]),
                    str(row["improves_q20_over_best_original"]),
                    str(row["improves_q20_over_straddle"]),
                    str(row["improves_q20_over_boundary_gated_diversified_straddle"]),
                    str(row["improves_q30_over_best_original"]),
                    str(row["improves_q30_over_randomized_straddle"]),
                    str(row["improves_q30_over_boundary_gated_diversified_straddle"]),
                ]
            )
            + " |"
        )
    if lookahead_reference:
        lines.extend(["", "## Lookahead Reference", ""])
        for row in combined_rows:
            if not row.get("lookahead_boundary_uncertainty_reduction_reference_available"):
                continue
            lines.append(
                "- "
                + f"{row['display_name']}: lookahead reference global `{row['lookahead_reference_global_error']}`, "
                + f"q20 `{row['lookahead_reference_q20_error']}`, "
                + f"q30 `{row['lookahead_reference_q30_error']}`."
            )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Negative differences in `gbc_vs_baselines_table.csv` are better for error, uncertainty, and query-distance metrics.",
            "For query distance, smaller means closer to the true threshold in function-value space, but this is sampling behavior rather than predictive correctness.",
            "If GBC improves, this suggests local geometric information from the GP posterior boundary can help sample-efficient boundary learning.",
            "If GBC does not improve, finite-difference curvature under the current GP-regression surrogate may not be reliably aligned with true boundary classification accuracy.",
            "Caveats: GBC is heuristic; curvature comes from the GP posterior mean, not the true function; the Hessian is diagonal-only; the boundary weight uses a latent GP-regression probability heuristic; lower uncertainty does not prove correctness.",
        ]
    )
    (combined_dir / "week5_3_gbc_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_benchmark(config: BenchmarkConfig) -> BenchmarkResult:
    designs = [config.create_design(seed, config.threshold) for seed in SEEDS]
    runs_by_method: dict[str, list[MethodRun]] = {method: [] for method in WEEK5_METHODS}
    for design in designs:
        for method in WEEK5_METHODS:
            runs_by_method[method].append(run_method(config, design, method))
    fairness = verify_fairness(runs_by_method)
    if not fairness["all_checks_passed"]:
        raise RuntimeError(f"Fairness check failed for {config.name}: {fairness}")
    raw_rows = [row for method in WEEK5_METHODS for run in runs_by_method[method] for row in run.metric_rows]
    query_rows = [row for method in WEEK5_METHODS for run in runs_by_method[method] for row in run.query_rows]
    selected_rows = summarize_selected_budgets(config, raw_rows)
    final_rows = summarize_final_metrics(config, raw_rows, query_rows)
    result = BenchmarkResult(
        config=config,
        runs_by_method=runs_by_method,
        fairness_checks=fairness,
        raw_metric_rows=raw_rows,
        query_rows=query_rows,
        selected_budget_rows=selected_rows,
        final_rows=final_rows,
        combined_row={},
        comparison_rows=[],
    )
    result.comparison_rows = comparison_rows_for_benchmark(final_rows, config)
    result.combined_row = combined_row_for_benchmark(result)
    return result


def build_configs() -> list[BenchmarkConfig]:
    branin_threshold_seed = 2026
    branin_threshold_sample_size = 20_000
    branin_threshold = compute_branin_threshold(branin_threshold_sample_size, branin_threshold_seed)
    ackley_values = threshold_sample_values()
    ackley_threshold = compute_ackley_threshold(ackley_values)
    return [
        BenchmarkConfig(
            name="branin",
            display_name="Thresholded Branin",
            output_name="branin",
            domain="x1 in [-5,10], x2 in [0,15]",
            threshold=branin_threshold,
            threshold_percentile=45.0,
            threshold_seed=branin_threshold_seed,
            threshold_sample_size=branin_threshold_sample_size,
            pool_size=1_500,
            test_size=4_000,
            initial_size=6,
            total_budget=50,
            selected_budgets=(6, 20, 50),
            create_design=lambda seed, threshold: create_branin_design(seed, threshold, initial_size=6, pool_size=1_500, test_size=4_000),
            value_function=branin,
            scaling_rule="Branin original coordinates are linearly scaled to [0,1]^2 for the GP.",
        ),
        BenchmarkConfig(
            name="ackley",
            display_name="Thresholded 4D Ackley",
            output_name="ackley",
            domain="[-5,5]^4",
            threshold=ackley_threshold,
            threshold_percentile=50.0,
            threshold_seed=ACKLEY_THRESHOLD_SEED,
            threshold_sample_size=ACKLEY_THRESHOLD_SAMPLE_SIZE,
            pool_size=ACKLEY_POOL_SIZE,
            test_size=ACKLEY_TEST_SIZE,
            initial_size=12,
            total_budget=80,
            selected_budgets=(12, 40, 80),
            create_design=lambda seed, threshold: create_ackley_design(seed, threshold, initial_size=12, pool_size=ACKLEY_POOL_SIZE, test_size=ACKLEY_TEST_SIZE),
            value_function=ackley_4d,
            scaling_rule="Ackley original coordinates are linearly scaled to [0,1]^4 for the GP.",
        ),
    ]


def run_experiment(output_dir: Path = OUTPUT_DIR) -> list[BenchmarkResult]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results = [run_benchmark(config) for config in build_configs()]
    for result in results:
        save_benchmark_outputs(result, output_dir)
    write_combined_outputs(results, output_dir)
    return results


def main() -> None:
    results = run_experiment()
    print("Week 5.3 gated geometric boundary contraction comparison complete.")
    for result in results:
        row = result.combined_row
        print(
            f"{row['display_name']}: GBC improves global over best original="
            f"{row['improves_global_over_best_original']}, "
            f"q20 over best original={row['improves_q20_over_best_original']}, "
            f"q30 over best original={row['improves_q30_over_best_original']}, "
            f"global over gated diversity={row['improves_global_over_boundary_gated_diversified_straddle']}"
        )
    print(f"Saved outputs to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
