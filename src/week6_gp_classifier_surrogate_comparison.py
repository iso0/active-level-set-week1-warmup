"""Week 6 GP-classifier surrogate comparison.

This experiment switches the warm-up surrogate from GaussianProcessRegressor on
{-1,+1} labels to sklearn's GaussianProcessClassifier. Acquisitions are
classifier-native and use predicted class probabilities rather than regressor
latent mean/std.

The goal is a surrogate-family benchmark, not a claim that GP classification is
automatically better. Previous GP-regressor outputs are preserved and used only
as labelled reference data in the combined summary.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.gaussian_process.kernels import ConstantKernel, RBF

from src.branin_week1 import branin, compute_threshold as compute_branin_threshold
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
    threshold_sample_values,
)


OUTPUT_DIR = (
    Path(__file__).resolve().parents[1]
    / "outputs"
    / "week6_gp_classifier_surrogate_comparison"
)
SEEDS = (0, 1, 2, 3, 4)
CLASSIFIER_METHODS = (
    "random",
    "classifier_margin",
    "classifier_entropy",
    "classifier_gated_diversity",
    "classifier_uncertainty_repulsion",
)
CLASSIFIER_GATE_FRACTION = 0.10
CLASSIFIER_MIN_SHORTLIST_SIZE = 25
CLASSIFIER_DIVERSITY_BETA = 0.50
CLASSIFIER_REPULSION_BANDWIDTH = 0.15
UNCERTAINTY_EPSILONS = (0.05, 0.10)
PRIMARY_UNCERTAINTY_EPSILON = 0.10
BOUNDARY_QUANTILES = (10, 20, 30)
GPC_LENGTH_SCALE = 0.25
GPC_MAX_ITER_PREDICT = 100
GPC_OPTIMIZER = None
QUICK_MODE_DEFAULT = False

METHOD_DESCRIPTIONS = {
    "random": "Uniformly random unlabelled pool point.",
    "classifier_margin": "Choose largest 1 - 2*abs(p_plus - 0.5).",
    "classifier_entropy": "Choose maximum binary predictive entropy from p_plus.",
    "classifier_gated_diversity": (
        "Gate to top classifier-margin candidates, then mix normalized "
        "uncertainty and nearest-labelled-point diversity with beta=0.50."
    ),
    "classifier_uncertainty_repulsion": (
        "Gate to top classifier-margin candidates, then choose largest "
        "normalized uncertainty times labelled-set repulsion."
    ),
}

METHOD_COLORS = {
    "random": "#8c8c8c",
    "classifier_margin": "#2b6cb0",
    "classifier_entropy": "#0f8b61",
    "classifier_gated_diversity": "#d95f02",
    "classifier_uncertainty_repulsion": "#6a3d9a",
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


def rng_for_week6_method(seed: int, method: str, benchmark: str) -> np.random.Generator:
    digest = hashlib.sha256(f"{seed}:{benchmark}:{method}:week6_classifier".encode("utf-8")).digest()
    offset = int.from_bytes(digest[:8], "little") % (2**32)
    return np.random.default_rng(offset)


def make_gp_classifier(seed: int) -> GaussianProcessClassifier:
    kernel = ConstantKernel(1.0, constant_value_bounds="fixed") * RBF(
        length_scale=GPC_LENGTH_SCALE,
        length_scale_bounds="fixed",
    )
    return GaussianProcessClassifier(
        kernel=kernel,
        optimizer=GPC_OPTIMIZER,
        n_restarts_optimizer=0,
        max_iter_predict=GPC_MAX_ITER_PREDICT,
        random_state=seed,
    )


def fit_classifier(X: np.ndarray, y: np.ndarray, seed: int) -> GaussianProcessClassifier:
    if np.unique(y).size < 2:
        raise RuntimeError("GaussianProcessClassifier requires both classes in the labelled set")
    gp = make_gp_classifier(seed)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        gp.fit(X, y)
    return gp


def predict_p_plus(gp: GaussianProcessClassifier, X: np.ndarray) -> np.ndarray:
    probabilities = gp.predict_proba(X)
    matches = np.flatnonzero(gp.classes_ == 1.0)
    if len(matches) != 1:
        raise RuntimeError(f"Expected class +1 in classifier classes, got {gp.classes_}")
    return probabilities[:, int(matches[0])]


def classifier_uncertainty_score(p_plus: np.ndarray) -> np.ndarray:
    return np.clip(1.0 - 2.0 * np.abs(np.asarray(p_plus) - 0.5), 0.0, 1.0)


def binary_entropy(p_plus: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p_plus, dtype=float), 1e-12, 1.0 - 1e-12)
    return -(p * np.log(p) + (1.0 - p) * np.log(1.0 - p))


def shortlist_by_uncertainty(
    unlabelled_indices: np.ndarray,
    uncertainty: np.ndarray,
    gate_fraction: float,
    min_shortlist_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    shortlist_size = int(np.ceil(len(unlabelled_indices) * gate_fraction))
    shortlist_size = max(shortlist_size, min(min_shortlist_size, len(unlabelled_indices)))
    shortlist_size = min(shortlist_size, len(unlabelled_indices))
    order = np.lexsort((unlabelled_indices, -uncertainty))
    positions = order[:shortlist_size]
    return positions, unlabelled_indices[positions]


def nearest_labelled_distance(
    pool_scaled: np.ndarray,
    candidate_indices: np.ndarray,
    labelled_indices: list[int],
) -> np.ndarray:
    candidates = pool_scaled[candidate_indices]
    labelled = pool_scaled[np.asarray(labelled_indices, dtype=int)]
    diffs = candidates[:, None, :] - labelled[None, :, :]
    return np.sqrt(np.sum(diffs**2, axis=2)).min(axis=1)


def deterministic_argmax(indices: np.ndarray, scores: np.ndarray) -> int:
    order = np.lexsort((indices, -scores))
    return int(order[0])


def choose_classifier_candidate(
    *,
    method: str,
    unlabelled_indices: np.ndarray,
    p_plus: np.ndarray,
    pool_scaled: np.ndarray,
    labelled_indices: list[int],
    rng: np.random.Generator,
) -> tuple[int, dict[str, object]]:
    uncertainty = classifier_uncertainty_score(p_plus)
    entropy = binary_entropy(p_plus)
    if method == "random":
        position = int(rng.integers(0, len(unlabelled_indices)))
        return int(unlabelled_indices[position]), {
            "selected_position": position,
            "selected_p_plus": float(p_plus[position]),
            "selected_uncertainty_score": float(uncertainty[position]),
            "selected_entropy": float(entropy[position]),
        }
    if method == "classifier_margin":
        position = deterministic_argmax(unlabelled_indices, uncertainty)
        return int(unlabelled_indices[position]), {
            "selected_position": position,
            "selected_p_plus": float(p_plus[position]),
            "selected_uncertainty_score": float(uncertainty[position]),
            "selected_entropy": float(entropy[position]),
        }
    if method == "classifier_entropy":
        position = deterministic_argmax(unlabelled_indices, entropy)
        return int(unlabelled_indices[position]), {
            "selected_position": position,
            "selected_p_plus": float(p_plus[position]),
            "selected_uncertainty_score": float(uncertainty[position]),
            "selected_entropy": float(entropy[position]),
            "binary_entropy_margin_note": "Binary entropy is monotone-equivalent to classifier margin.",
        }
    shortlist_positions, shortlist_indices = shortlist_by_uncertainty(
        unlabelled_indices,
        uncertainty,
        CLASSIFIER_GATE_FRACTION,
        CLASSIFIER_MIN_SHORTLIST_SIZE,
    )
    shortlist_uncertainty = uncertainty[shortlist_positions]
    distances = nearest_labelled_distance(pool_scaled, shortlist_indices, labelled_indices)
    norm_uncertainty = normalize_scores(shortlist_uncertainty)
    if method == "classifier_gated_diversity":
        norm_diversity = normalize_scores(distances)
        score = (1.0 - CLASSIFIER_DIVERSITY_BETA) * norm_uncertainty + CLASSIFIER_DIVERSITY_BETA * norm_diversity
        shortlist_choice = deterministic_argmax(shortlist_indices, score)
        original_position = int(shortlist_positions[shortlist_choice])
        return int(shortlist_indices[shortlist_choice]), {
            "gate_fraction": CLASSIFIER_GATE_FRACTION,
            "min_shortlist_size": CLASSIFIER_MIN_SHORTLIST_SIZE,
            "shortlist_size": len(shortlist_indices),
            "beta": CLASSIFIER_DIVERSITY_BETA,
            "selected_position": original_position,
            "selected_shortlist_position": shortlist_choice,
            "selected_p_plus": float(p_plus[original_position]),
            "selected_uncertainty_score": float(uncertainty[original_position]),
            "selected_entropy": float(entropy[original_position]),
            "selected_normalized_uncertainty": float(norm_uncertainty[shortlist_choice]),
            "selected_raw_diversity": float(distances[shortlist_choice]),
            "selected_normalized_diversity": float(norm_diversity[shortlist_choice]),
            "selected_score": float(score[shortlist_choice]),
        }
    if method == "classifier_uncertainty_repulsion":
        repulsion = 1.0 - np.exp(-(distances**2) / (2.0 * CLASSIFIER_REPULSION_BANDWIDTH**2 + 1e-12))
        score = norm_uncertainty * repulsion
        shortlist_choice = deterministic_argmax(shortlist_indices, score)
        original_position = int(shortlist_positions[shortlist_choice])
        return int(shortlist_indices[shortlist_choice]), {
            "gate_fraction": CLASSIFIER_GATE_FRACTION,
            "min_shortlist_size": CLASSIFIER_MIN_SHORTLIST_SIZE,
            "shortlist_size": len(shortlist_indices),
            "repulsion_bandwidth": CLASSIFIER_REPULSION_BANDWIDTH,
            "selected_position": original_position,
            "selected_shortlist_position": shortlist_choice,
            "selected_p_plus": float(p_plus[original_position]),
            "selected_uncertainty_score": float(uncertainty[original_position]),
            "selected_entropy": float(entropy[original_position]),
            "selected_normalized_uncertainty": float(norm_uncertainty[shortlist_choice]),
            "selected_raw_distance_to_labelled": float(distances[shortlist_choice]),
            "selected_repulsion": float(repulsion[shortlist_choice]),
            "selected_score": float(score[shortlist_choice]),
        }
    raise ValueError(f"Unknown Week 6 method: {method}")


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
    gp: GaussianProcessClassifier,
    dataset: object,
    test_masks: dict[int, np.ndarray],
) -> dict[str, object]:
    p_plus = predict_p_plus(gp, dataset.test_scaled)
    prediction = np.where(p_plus >= 0.5, 1.0, -1.0)
    errors = prediction != dataset.test_labels
    row: dict[str, object] = {
        "benchmark": benchmark,
        "method": method,
        "seed": seed,
        "budget": budget,
        "global_error": float(np.mean(errors)),
    }
    for epsilon in UNCERTAINTY_EPSILONS:
        suffix = f"eps{int(round(epsilon * 100)):02d}"
        uncertain = np.abs(p_plus - 0.5) <= epsilon
        row[f"classifier_uncertainty_region_fraction_{suffix}"] = float(np.mean(uncertain))
    for quantile, mask in test_masks.items():
        row[f"near_boundary_error_q{quantile}"] = float(np.mean(errors[mask]))
        row[f"near_boundary_test_size_q{quantile}"] = int(mask.sum())
        for epsilon in UNCERTAINTY_EPSILONS:
            suffix = f"eps{int(round(epsilon * 100)):02d}"
            uncertain = np.abs(p_plus - 0.5) <= epsilon
            row[f"classifier_uncertainty_region_fraction_q{quantile}_{suffix}"] = float(np.mean(uncertain[mask]))
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
    rng = rng_for_week6_method(design.seed, method, config.name)
    budgets: list[int] = []
    metric_rows: list[dict[str, object]] = []
    query_rows: list[dict[str, object]] = []

    while True:
        gp = fit_classifier(dataset.pool_scaled[labelled], dataset.pool_labels[labelled], design.seed)
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
                test_masks=test_masks,
            )
        )
        if budget == config.total_budget:
            break

        mask = np.ones(len(dataset.pool_labels), dtype=bool)
        mask[labelled] = False
        unlabelled = np.flatnonzero(mask)
        p_unlabelled = predict_p_plus(gp, dataset.pool_scaled[unlabelled])
        next_index, metadata = choose_classifier_candidate(
            method=method,
            unlabelled_indices=unlabelled,
            p_plus=p_unlabelled,
            pool_scaled=dataset.pool_scaled,
            labelled_indices=labelled,
            rng=rng,
        )
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
        "same_surrogate_model_family": True,
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
        "classifier_uncertainty_region_fraction_eps10",
        "classifier_uncertainty_region_fraction_q20_eps10",
        "classifier_uncertainty_region_fraction_q30_eps10",
    ]
    for method in CLASSIFIER_METHODS:
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
        "classifier_uncertainty_region_fraction_eps05",
        "classifier_uncertainty_region_fraction_eps10",
        "classifier_uncertainty_region_fraction_q20_eps10",
        "classifier_uncertainty_region_fraction_q30_eps10",
    ]
    raw_means: dict[str, dict[str, float]] = {}
    for method in CLASSIFIER_METHODS:
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

    for method in CLASSIFIER_METHODS:
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


def best_method(rows: list[dict[str, object]], field: str) -> str:
    return min(rows, key=lambda row: float(row[field]))["method"]


def plot_metric_curves(
    raw_rows: list[dict[str, object]],
    metric: str,
    config: BenchmarkConfig,
    output_path: Path,
    title: str,
    ylabel: str,
) -> None:
    fig, ax = plt.subplots(figsize=(10.8, 6.4))
    for method in CLASSIFIER_METHODS:
        method_rows = [row for row in raw_rows if row["method"] == method]
        budgets = sorted({int(row["budget"]) for row in method_rows})
        seeds = sorted({int(row["seed"]) for row in method_rows})
        values_by_seed = []
        for seed in seeds:
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
    ax.legend(title="Classifier acquisition rule", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_final_global_vs_near(final_rows: list[dict[str, object]], config: BenchmarkConfig, output_path: Path) -> None:
    metrics = [
        ("mean_final_global_error", "global"),
        ("mean_final_near_boundary_error_q20", "q20"),
        ("mean_final_near_boundary_error_q30", "q30"),
    ]
    positions = np.arange(len(CLASSIFIER_METHODS))
    width = 0.22
    fig, ax = plt.subplots(figsize=(11.2, 6.2))
    for offset, (field, label) in enumerate(metrics):
        values = [float(next(row for row in final_rows if row["method"] == method)[field]) for method in CLASSIFIER_METHODS]
        ax.bar(positions + (offset - 1) * width, values, width=width, label=label, alpha=0.88)
    ax.set_xticks(positions)
    ax.set_xticklabels([method.replace("classifier_", "").replace("_", "\n") for method in CLASSIFIER_METHODS], fontsize=9)
    ax.set(title=f"{config.display_name}: final classifier global vs near-boundary error", ylabel="Mean final error over seeds")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(title="Metric")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_query_distance_boxplot(query_rows: list[dict[str, object]], config: BenchmarkConfig, output_path: Path) -> None:
    data = []
    for method in CLASSIFIER_METHODS:
        data.append([max(float(row["true_boundary_distance"]), 1e-12) for row in query_rows if row["method"] == method])
    fig, ax = plt.subplots(figsize=(10.8, 6.2))
    ax.boxplot(data, tick_labels=[method.replace("classifier_", "").replace("_", "\n") for method in CLASSIFIER_METHODS], showfliers=False)
    ax.set_yscale("log")
    ax.set(title=f"{config.display_name}: classifier query distance to true boundary", ylabel="abs(f(x_query)-threshold), log scale")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_query_distance_median_iqr(query_rows: list[dict[str, object]], config: BenchmarkConfig, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.8, 6.3))
    for method in CLASSIFIER_METHODS:
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
        title=f"{config.display_name}: classifier median query distance over budget",
        xlabel="Labelled evaluations after query",
        ylabel="median abs(f(x_query)-threshold), q25-q75 band, log scale",
        xlim=(config.initial_size + 1, config.total_budget),
    )
    ax.grid(alpha=0.25)
    ax.legend(title="Classifier acquisition rule", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def load_gp_regressor_reference(benchmark: str) -> tuple[str, list[dict[str, str]]]:
    repo_root = Path(__file__).resolve().parents[1]
    candidates = [
        ("week5_3_gated_geometric_boundary_contraction", repo_root / "outputs" / "week5_3_gated_geometric_boundary_contraction" / benchmark / "final_metrics_table.csv"),
        ("week5_boundary_gated_diversified_straddle_comparison", repo_root / "outputs" / "week5_boundary_gated_diversified_straddle_comparison" / benchmark / "final_metrics_table.csv"),
        ("week5_diversified_straddle_comparison", repo_root / "outputs" / "week5_diversified_straddle_comparison" / benchmark / "final_metrics_table.csv"),
    ]
    for source, path in candidates:
        if path.exists():
            with path.open(newline="", encoding="utf-8") as handle:
                return source, list(csv.DictReader(handle))
    return "not_available", []


def combined_row_for_benchmark(result: BenchmarkResult) -> dict[str, object]:
    final_rows = result.final_rows
    best_global = best_method(final_rows, "mean_final_global_error")
    best_q20 = best_method(final_rows, "mean_final_near_boundary_error_q20")
    best_q30 = best_method(final_rows, "mean_final_near_boundary_error_q30")
    best_global_row = next(row for row in final_rows if row["method"] == best_global)
    best_q20_row = next(row for row in final_rows if row["method"] == best_q20)
    best_q30_row = next(row for row in final_rows if row["method"] == best_q30)
    reference_source, reference_rows = load_gp_regressor_reference(result.config.output_name)
    row: dict[str, object] = {
        "benchmark": result.config.name,
        "display_name": result.config.display_name,
        "best_classifier_global_method": best_global,
        "best_classifier_global_error": best_global_row["mean_final_global_error"],
        "best_classifier_q20_method": best_q20,
        "best_classifier_q20_error": best_q20_row["mean_final_near_boundary_error_q20"],
        "best_classifier_q30_method": best_q30,
        "best_classifier_q30_error": best_q30_row["mean_final_near_boundary_error_q30"],
        "gp_regressor_reference_source": reference_source,
        "surrogate_family_comparison_caveat": "Classifier and regressor rows use different surrogate outputs; this is not an acquisition-only comparison.",
    }
    if reference_rows:
        ref_best_global = min(reference_rows, key=lambda item: float(item["mean_final_global_error"]))
        ref_best_q20 = min(reference_rows, key=lambda item: float(item["mean_final_near_boundary_error_q20"]))
        ref_best_q30 = min(reference_rows, key=lambda item: float(item["mean_final_near_boundary_error_q30"]))
        row.update(
            {
                "best_gp_regressor_global_method": ref_best_global["method"],
                "best_gp_regressor_global_error": ref_best_global["mean_final_global_error"],
                "classifier_beats_gp_regressor_global": float(best_global_row["mean_final_global_error"]) < float(ref_best_global["mean_final_global_error"]),
                "best_gp_regressor_q20_method": ref_best_q20["method"],
                "best_gp_regressor_q20_error": ref_best_q20["mean_final_near_boundary_error_q20"],
                "classifier_beats_gp_regressor_q20": float(best_q20_row["mean_final_near_boundary_error_q20"]) < float(ref_best_q20["mean_final_near_boundary_error_q20"]),
                "best_gp_regressor_q30_method": ref_best_q30["method"],
                "best_gp_regressor_q30_error": ref_best_q30["mean_final_near_boundary_error_q30"],
                "classifier_beats_gp_regressor_q30": float(best_q30_row["mean_final_near_boundary_error_q30"]) < float(ref_best_q30["mean_final_near_boundary_error_q30"]),
            }
        )
    else:
        row.update(
            {
                "best_gp_regressor_global_method": "not_available",
                "best_gp_regressor_global_error": "not_available",
                "classifier_beats_gp_regressor_global": "not_available",
                "best_gp_regressor_q20_method": "not_available",
                "best_gp_regressor_q20_error": "not_available",
                "classifier_beats_gp_regressor_q20": "not_available",
                "best_gp_regressor_q30_method": "not_available",
                "best_gp_regressor_q30_error": "not_available",
                "classifier_beats_gp_regressor_q30": "not_available",
            }
        )
    return row


def write_notes(result: BenchmarkResult, output_path: Path) -> None:
    row = result.combined_row
    improved_any = (
        row.get("classifier_beats_gp_regressor_global") is True
        or row.get("classifier_beats_gp_regressor_q20") is True
        or row.get("classifier_beats_gp_regressor_q30") is True
    )
    if improved_any:
        interpretation = (
            "The GP-classifier surrogate improves at least one boundary-focused "
            "reference metric compared with the previous GP-regression surrogate, "
            "suggesting that modelling the binary observation process directly "
            "can matter for this active level-set task."
        )
    else:
        interpretation = (
            "The GP-classifier surrogate did not clearly improve the boundary "
            "metrics under this implementation. This suggests that surrogate "
            "choice alone is not sufficient; kernel choice, calibration, pool "
            "geometry, and acquisition design remain important."
        )
    text = f"""# Week 6 GP-Classifier Notes: {result.config.display_name}

## What changed

Weeks 1-5 used `GaussianProcessRegressor` on `{{-1,+1}}` labels as a warm-up
surrogate. Week 6 uses `GaussianProcessClassifier` and classifier-native
acquisition rules based on `predict_proba`.

The GP classifier uses a fixed RBF kernel with length scale `{GPC_LENGTH_SCALE}`
and `optimizer=None` for runtime stability and reproducibility. This is a
practical approximation, not a final modelling choice.

## Classifier acquisitions

- `random`: random pool point.
- `classifier_margin`: largest `1 - 2*abs(p_plus - 0.5)`.
- `classifier_entropy`: largest binary entropy. For binary classification this
  is monotone-equivalent to margin, so it may select the same points.
- `classifier_gated_diversity`: top classifier-margin shortlist, then
  uncertainty/diversity mixture.
- `classifier_uncertainty_repulsion`: top classifier-margin shortlist, then
  uncertainty times repulsion from labelled points.

## Main result

- Best classifier global method: `{row['best_classifier_global_method']}` with error `{float(row['best_classifier_global_error']):.3f}`.
- Best classifier q20 method: `{row['best_classifier_q20_method']}` with error `{float(row['best_classifier_q20_error']):.3f}`.
- Best classifier q30 method: `{row['best_classifier_q30_method']}` with error `{float(row['best_classifier_q30_error']):.3f}`.
- GP-regressor reference source: `{row['gp_regressor_reference_source']}`.
- Classifier beats GP-regressor global reference: `{row['classifier_beats_gp_regressor_global']}`.
- Classifier beats GP-regressor q20 reference: `{row['classifier_beats_gp_regressor_q20']}`.
- Classifier beats GP-regressor q30 reference: `{row['classifier_beats_gp_regressor_q30']}`.

## Interpretation

{interpretation}

## Caveats

GaussianProcessClassifier probabilities are not the same as GP-regressor latent
mean/std. Binary entropy and margin are monotone-equivalent in theory. Fixed
kernel GP classification is a runtime-stable approximation. Lower classifier
uncertainty-region fraction does not automatically prove correctness. The q10,
q20, and q30 near-boundary subsets use true function-value distances only for
evaluation, never acquisition.
"""
    output_path.write_text(text, encoding="utf-8")


def save_benchmark_outputs(result: BenchmarkResult, base_output_dir: Path = OUTPUT_DIR) -> None:
    output_dir = base_output_dir / result.config.output_name
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_rows = list(result.query_rows)
    write_csv(output_dir / "raw_metrics.csv", result.raw_metric_rows)
    write_csv(output_dir / "query_distance_table.csv", result.query_rows)
    write_csv(output_dir / "classifier_query_metadata_table.csv", metadata_rows)
    write_csv(output_dir / "final_metrics_table.csv", result.final_rows)
    write_csv(output_dir / "selected_budget_metrics_table.csv", result.selected_budget_rows)
    plot_metric_curves(result.raw_metric_rows, "global_error", result.config, output_dir / "global_error_curves.png", f"{result.config.display_name}: GP-classifier global error", "Global test-label error")
    plot_metric_curves(result.raw_metric_rows, "near_boundary_error_q20", result.config, output_dir / "near_boundary_error_curves_q20.png", f"{result.config.display_name}: GP-classifier q20 near-boundary error", "Error on closest 20% test points")
    plot_metric_curves(result.raw_metric_rows, "near_boundary_error_q30", result.config, output_dir / "near_boundary_error_curves_q30.png", f"{result.config.display_name}: GP-classifier q30 near-boundary error", "Error on closest 30% test points")
    plot_final_global_vs_near(result.final_rows, result.config, output_dir / "final_global_vs_near_boundary_error.png")
    plot_query_distance_boxplot(result.query_rows, result.config, output_dir / "query_distance_to_boundary_boxplot.png")
    plot_query_distance_median_iqr(result.query_rows, result.config, output_dir / "query_distance_to_boundary_over_budget_median_iqr.png")
    plot_metric_curves(result.raw_metric_rows, "classifier_uncertainty_region_fraction_eps10", result.config, output_dir / "classifier_uncertainty_region_fraction_curves_global_eps10.png", f"{result.config.display_name}: classifier uncertainty region eps=0.10", "Fraction abs(p_plus-0.5)<=0.10")
    plot_metric_curves(result.raw_metric_rows, "classifier_uncertainty_region_fraction_q20_eps10", result.config, output_dir / "classifier_uncertainty_region_fraction_curves_q20_eps10.png", f"{result.config.display_name}: q20 classifier uncertainty region eps=0.10", "Closest 20% fraction abs(p_plus-0.5)<=0.10")
    plot_metric_curves(result.raw_metric_rows, "classifier_uncertainty_region_fraction_q30_eps10", result.config, output_dir / "classifier_uncertainty_region_fraction_curves_q30_eps10.png", f"{result.config.display_name}: q30 classifier uncertainty region eps=0.10", "Closest 30% fraction abs(p_plus-0.5)<=0.10")
    write_notes(result, output_dir / "week6_gp_classifier_notes.md")
    summary = {
        "experiment": f"week6_gp_classifier_surrogate_comparison_{result.config.name}",
        "benchmark": result.config.name,
        "display_name": result.config.display_name,
        "domain": result.config.domain,
        "threshold": result.config.threshold,
        "threshold_percentile": result.config.threshold_percentile,
        "seeds": sorted({run.seed for runs in result.runs_by_method.values() for run in runs}),
        "pool_size": result.config.pool_size,
        "test_size": result.config.test_size,
        "initial_labelled_size": result.config.initial_size,
        "total_budget": result.config.total_budget,
        "methods": list(CLASSIFIER_METHODS),
        "surrogate_model": "sklearn.gaussian_process.GaussianProcessClassifier",
        "surrogate_model_family": "GP classifier",
        "kernel": f"ConstantKernel(1.0 fixed) * RBF(length_scale={GPC_LENGTH_SCALE} fixed)",
        "optimizer": "None",
        "max_iter_predict": GPC_MAX_ITER_PREDICT,
        "model_note": "Fixed-kernel GP classifier is used for runtime stability and reproducibility.",
        "prediction_rule": "+1 if p_plus >= 0.5, else -1",
        "acquisition_note": "Acquisitions use classifier probabilities, not GP-regressor latent mu/sigma.",
        "fairness_checks": result.fairness_checks,
        "final_metrics": result.final_rows,
        "selected_budget_metrics": result.selected_budget_rows,
        "combined_summary_row": result.combined_row,
        "caveats": [
            "GaussianProcessClassifier probabilities are not the same as latent GP-regressor mean/std.",
            "Binary entropy and margin are monotone-equivalent for binary classification.",
            "Fixed-kernel GP classifier is a practical runtime approximation.",
            "Lower classifier uncertainty-region fraction does not automatically prove correctness.",
            "q10/q20/q30 true-boundary masks are evaluation subsets only, not acquisition information.",
            "The combined GP-regressor reference comparison is a surrogate-family comparison, not an acquisition-only comparison.",
        ],
    }
    (output_dir / "summary.json").write_text(json.dumps(json_ready(summary), indent=2), encoding="utf-8")


def write_combined_outputs(results: list[BenchmarkResult], base_output_dir: Path = OUTPUT_DIR) -> None:
    combined_dir = base_output_dir / "combined"
    combined_dir.mkdir(parents=True, exist_ok=True)
    combined_rows = [result.combined_row for result in results]
    write_csv(combined_dir / "week6_gp_classifier_summary.csv", combined_rows)
    reference_rows = []
    for row in combined_rows:
        reference_rows.append(
            {
                "benchmark": row["benchmark"],
                "display_name": row["display_name"],
                "gp_classifier_best_global_method": row["best_classifier_global_method"],
                "gp_classifier_best_global_error": row["best_classifier_global_error"],
                "gp_classifier_best_q20_method": row["best_classifier_q20_method"],
                "gp_classifier_best_q20_error": row["best_classifier_q20_error"],
                "gp_classifier_best_q30_method": row["best_classifier_q30_method"],
                "gp_classifier_best_q30_error": row["best_classifier_q30_error"],
                "gp_regressor_reference_source": row["gp_regressor_reference_source"],
                "gp_regressor_best_global_method": row["best_gp_regressor_global_method"],
                "gp_regressor_best_global_error": row["best_gp_regressor_global_error"],
                "classifier_beats_gp_regressor_global": row["classifier_beats_gp_regressor_global"],
                "gp_regressor_best_q20_method": row["best_gp_regressor_q20_method"],
                "gp_regressor_best_q20_error": row["best_gp_regressor_q20_error"],
                "classifier_beats_gp_regressor_q20": row["classifier_beats_gp_regressor_q20"],
                "gp_regressor_best_q30_method": row["best_gp_regressor_q30_method"],
                "gp_regressor_best_q30_error": row["best_gp_regressor_q30_error"],
                "classifier_beats_gp_regressor_q30": row["classifier_beats_gp_regressor_q30"],
                "comparison_caveat": row["surrogate_family_comparison_caveat"],
            }
        )
    write_csv(combined_dir / "gp_classifier_vs_gp_regressor_reference.csv", reference_rows)
    lines = [
        "# Week 6 GP-Classifier Surrogate Summary",
        "",
        "Week 6 switches from GP regression on {-1,+1} labels to `GaussianProcessClassifier` with classifier-native probability acquisitions.",
        "The GP-regressor rows are reference rows from existing outputs, not methods rerun inside this Week 6 script.",
        "",
        "| Benchmark | Best classifier global | Best classifier q20 | Best classifier q30 | Beats regressor global | Beats regressor q20 | Beats regressor q30 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in combined_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["display_name"]),
                    f"{row['best_classifier_global_method']} ({float(row['best_classifier_global_error']):.3f})",
                    f"{row['best_classifier_q20_method']} ({float(row['best_classifier_q20_error']):.3f})",
                    f"{row['best_classifier_q30_method']} ({float(row['best_classifier_q30_error']):.3f})",
                    str(row["classifier_beats_gp_regressor_global"]),
                    str(row["classifier_beats_gp_regressor_q20"]),
                    str(row["classifier_beats_gp_regressor_q30"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "A GP classifier is more appropriate for binary observations because it models class probabilities directly instead of regressing on {-1,+1} labels.",
            "This run does not prove that classifier surrogates are automatically better; kernel choice, probability calibration, pool geometry, and acquisition design still matter.",
            "Binary entropy and margin are monotone-equivalent in binary classification, so they may be redundant.",
            "Fixed-kernel GP classification is used as a practical approximation for runtime stability.",
            "Lower classifier uncertainty-region fraction does not automatically imply correct boundary learning.",
            "q10/q20/q30 subsets are evaluation diagnostics only and are not used by acquisition rules.",
        ]
    )
    (combined_dir / "week6_gp_classifier_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_benchmark(config: BenchmarkConfig, methods: tuple[str, ...] = CLASSIFIER_METHODS, seeds: tuple[int, ...] = SEEDS) -> BenchmarkResult:
    designs = [config.create_design(seed, config.threshold) for seed in seeds]
    runs_by_method: dict[str, list[MethodRun]] = {method: [] for method in methods}
    for design in designs:
        for method in methods:
            runs_by_method[method].append(run_method(config, design, method))
    fairness = verify_fairness(runs_by_method)
    if not fairness["all_checks_passed"]:
        raise RuntimeError(f"Fairness check failed for {config.name}: {fairness}")
    raw_rows = [row for method in methods for run in runs_by_method[method] for row in run.metric_rows]
    query_rows = [row for method in methods for run in runs_by_method[method] for row in run.query_rows]
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
    )
    result.combined_row = combined_row_for_benchmark(result)
    return result


def build_configs(quick_mode: bool = QUICK_MODE_DEFAULT) -> list[BenchmarkConfig]:
    branin_threshold_seed = 2026
    branin_threshold_sample_size = 20_000
    branin_threshold = compute_branin_threshold(branin_threshold_sample_size, branin_threshold_seed)
    ackley_values = threshold_sample_values()
    ackley_threshold = compute_ackley_threshold(ackley_values)
    if quick_mode:
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
                pool_size=400,
                test_size=1_000,
                initial_size=6,
                total_budget=15,
                selected_budgets=(6, 10, 15),
                create_design=lambda seed, threshold: create_branin_design(seed, threshold, initial_size=6, pool_size=400, test_size=1_000),
                value_function=branin,
                scaling_rule="Branin original coordinates are linearly scaled to [0,1]^2 for the GP classifier.",
            )
        ]
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
            scaling_rule="Branin original coordinates are linearly scaled to [0,1]^2 for the GP classifier.",
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
            scaling_rule="Ackley original coordinates are linearly scaled to [0,1]^4 for the GP classifier.",
        ),
    ]


def smoke_test() -> None:
    config = build_configs(quick_mode=True)[0]
    design = config.create_design(SEEDS[0], config.threshold)
    original_total_budget = config.total_budget
    config.total_budget = config.initial_size + 2
    config.selected_budgets = (config.initial_size, config.total_budget)
    try:
        for method in ("random", "classifier_margin"):
            run = run_method(config, design, method)
            if not run.metric_rows:
                raise RuntimeError("Smoke test produced no metrics")
            if not np.isfinite(float(run.metric_rows[-1]["global_error"])):
                raise RuntimeError("Smoke test produced invalid global error")
    finally:
        config.total_budget = original_total_budget


def run_experiment(output_dir: Path = OUTPUT_DIR, quick_mode: bool = QUICK_MODE_DEFAULT) -> list[BenchmarkResult]:
    output_dir.mkdir(parents=True, exist_ok=True)
    configs = build_configs(quick_mode=quick_mode)
    methods = CLASSIFIER_METHODS
    seeds = SEEDS if not quick_mode else (0,)
    results = [run_benchmark(config, methods=methods, seeds=seeds) for config in configs]
    for result in results:
        save_benchmark_outputs(result, output_dir)
    write_combined_outputs(results, output_dir)
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Week 6 GP-classifier surrogate comparison")
    parser.add_argument("--quick", action="store_true", help="Run a small quick-mode experiment instead of the full Week 6 benchmark")
    parser.add_argument("--skip-smoke", action="store_true", help="Skip the pre-run GP-classifier smoke test")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start = time.perf_counter()
    if not args.skip_smoke:
        smoke_test()
        print("Week 6 GP-classifier smoke test passed.")
    results = run_experiment(quick_mode=args.quick)
    elapsed = time.perf_counter() - start
    mode = "quick" if args.quick else "full"
    print(f"Week 6 GP-classifier surrogate comparison complete in {elapsed:.1f}s ({mode} mode).")
    for result in results:
        row = result.combined_row
        print(
            f"{row['display_name']}: best global={row['best_classifier_global_method']} "
            f"({float(row['best_classifier_global_error']):.4f}), "
            f"best q20={row['best_classifier_q20_method']} "
            f"({float(row['best_classifier_q20_error']):.4f}), "
            f"best q30={row['best_classifier_q30_method']} "
            f"({float(row['best_classifier_q30_error']):.4f})"
        )
    print(f"Saved outputs to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
