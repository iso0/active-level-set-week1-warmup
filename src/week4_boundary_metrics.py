"""Week 4 boundary-focused metrics for Branin and 4D Ackley.

This script evaluates the existing acquisition rules without adding a new
rule. It keeps the Week 2 Branin and Week 3 Ackley setups fixed, then adds
boundary-focused diagnostics:

- global test-label error,
- near-boundary test-label error on closest q10/q20/q30 test points,
- true function-value distance of acquired queries to the threshold,
- GP latent uncertainty-region fraction abs(mu) <= 1.96*sigma.

The distance-to-boundary metric is a function-value distance proxy, not
Euclidean distance to the geometric contour.
"""

from __future__ import annotations

import csv
import hashlib
import json
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


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs" / "week4_boundary_metrics"
DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
SEEDS = (0, 1, 2, 3, 4)
BOUNDARY_QUANTILES = (10, 20, 30)
UNCERTAINTY_MULTIPLIER = 1.96

METHOD_COLORS = {
    "random": "#8c8c8c",
    "smallest_abs_mu": "#2b6cb0",
    "straddle": "#0f8b61",
    "randomized_straddle": "#b7791f",
    "expected_feasibility": "#9f1239",
}


@dataclass
class BenchmarkConfig:
    """Settings and callables needed to run one benchmark."""

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
    rng_for_method: Callable[[int, str], np.random.Generator]
    value_function: Callable[[np.ndarray], np.ndarray]
    scaling_rule: str


@dataclass
class BoundaryRun:
    """All boundary-metric outputs for one method and seed."""

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
    """Saved result tables and summaries for one benchmark."""

    config: BenchmarkConfig
    runs_by_method: dict[str, list[BoundaryRun]]
    fairness_checks: dict[str, object]
    raw_metric_rows: list[dict[str, object]]
    query_rows: list[dict[str, object]]
    selected_budget_rows: list[dict[str, object]]
    final_rows: list[dict[str, object]]
    combined_row: dict[str, object]


def array_signature(*arrays: np.ndarray) -> str:
    """Return a deterministic signature for equality checks in summaries."""
    digest = hashlib.sha256()
    for array in arrays:
        contiguous = np.ascontiguousarray(array)
        digest.update(str(contiguous.shape).encode("utf-8"))
        digest.update(str(contiguous.dtype).encode("utf-8"))
        digest.update(contiguous.view(np.uint8))
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    """Write dict rows as CSV, using 'null' for missing values."""
    if not rows:
        raise ValueError(f"No rows to write for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {key: ("null" if value is None else value) for key, value in row.items()}
            )


def json_ready(value: object) -> object:
    """Convert numpy scalar containers into JSON-serializable values."""
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


def mean_std(values: list[float]) -> tuple[float, float]:
    """Return mean and population standard deviation."""
    array = np.asarray(values, dtype=float)
    return float(array.mean()), float(array.std())


def rank_methods(values_by_method: dict[str, float], smaller_is_better: bool = True) -> dict[str, int]:
    """Rank methods by a scalar value."""
    items = sorted(
        values_by_method.items(),
        key=lambda item: item[1],
        reverse=not smaller_is_better,
    )
    return {method: rank + 1 for rank, (method, _) in enumerate(items)}


def get_dataset_values(dataset: object, config: BenchmarkConfig) -> tuple[np.ndarray, np.ndarray]:
    """Return exact continuous function values for pool and test data."""
    if hasattr(dataset, "pool_values") and hasattr(dataset, "test_values"):
        return np.asarray(dataset.pool_values), np.asarray(dataset.test_values)
    return config.value_function(dataset.pool_original), config.value_function(dataset.test_original)


def boundary_masks(distances: np.ndarray) -> dict[int, np.ndarray]:
    """Masks for closest q% points to the true threshold in function-value space."""
    masks = {}
    for quantile in BOUNDARY_QUANTILES:
        cutoff = float(np.percentile(distances, quantile))
        masks[quantile] = distances <= cutoff
    return masks


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
    """Compute all per-budget evaluation metrics."""
    test_mean, test_std = gp.predict(dataset.test_scaled, return_std=True)
    prediction = np.where(test_mean >= 0.0, 1.0, -1.0)
    errors = prediction != dataset.test_labels
    row: dict[str, object] = {
        "benchmark": benchmark,
        "method": method,
        "seed": seed,
        "budget": budget,
        "global_error": float(np.mean(errors)),
        "latent_uncertainty_region_fraction": float(
            np.mean(np.abs(test_mean) <= UNCERTAINTY_MULTIPLIER * test_std)
        ),
        "mean_true_boundary_distance_test": float(test_distances.mean()),
    }
    for quantile, mask in test_masks.items():
        row[f"near_boundary_error_q{quantile}"] = float(np.mean(errors[mask]))
        row[f"near_boundary_test_size_q{quantile}"] = int(mask.sum())
    return row


def run_boundary_method(config: BenchmarkConfig, design: object, method: str) -> BoundaryRun:
    """Run one acquisition method and compute boundary-focused metrics."""
    dataset = design.dataset
    pool_values, test_values = get_dataset_values(dataset, config)
    pool_distances = np.abs(pool_values - config.threshold)
    test_distances = np.abs(test_values - config.threshold)
    pool_masks = boundary_masks(pool_distances)
    test_masks = boundary_masks(test_distances)
    labelled = list(design.initial_indices)
    initial_copy = list(design.initial_indices)
    rng = config.rng_for_method(design.seed, method)

    metric_rows: list[dict[str, object]] = []
    query_rows: list[dict[str, object]] = []
    budgets: list[int] = []

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
        if method == "random":
            choice = choose_next_index(method, unlabelled, None, None, rng)
        else:
            pool_mean, pool_std = gp.predict(dataset.pool_scaled[unlabelled], return_std=True)
            choice = choose_next_index(method, unlabelled, pool_mean, pool_std, rng)

        query_distance = float(pool_distances[choice.index])
        query_number = len(query_rows) + 1
        query_row: dict[str, object] = {
            "benchmark": config.name,
            "method": method,
            "seed": design.seed,
            "query_number": query_number,
            "budget_before_query": budget,
            "budget_after_query": budget + 1,
            "selected_pool_index": choice.index,
            "true_boundary_distance": query_distance,
        }
        for quantile, band_mask in pool_masks.items():
            query_row[f"in_pool_boundary_band_q{quantile}"] = bool(band_mask[choice.index])
        query_rows.append(query_row)
        labelled.append(choice.index)

    if labelled[: len(initial_copy)] != initial_copy:
        raise RuntimeError("Initial labelled indices were mutated")

    return BoundaryRun(
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


def verify_fairness(runs_by_method: dict[str, list[BoundaryRun]]) -> dict[str, object]:
    """Check that only the acquisition rule changes within each seed."""
    seeds = sorted({run.seed for runs in runs_by_method.values() for run in runs})
    same_initial: dict[str, bool] = {}
    same_threshold: dict[str, bool] = {}
    same_pool: dict[str, bool] = {}
    same_test: dict[str, bool] = {}
    same_budget: dict[str, bool] = {}
    for seed in seeds:
        seed_runs = [
            run for runs in runs_by_method.values() for run in runs if run.seed == seed
        ]
        first = seed_runs[0]
        same_initial[str(seed)] = all(
            run.initial_indices == first.initial_indices for run in seed_runs
        )
        same_threshold[str(seed)] = all(run.threshold == first.threshold for run in seed_runs)
        same_pool[str(seed)] = all(run.pool_signature == first.pool_signature for run in seed_runs)
        same_test[str(seed)] = all(run.test_signature == first.test_signature for run in seed_runs)
        same_budget[str(seed)] = all(run.budgets == first.budgets for run in seed_runs)

    checks: dict[str, object] = {
        "same_initial_indices_per_seed": same_initial,
        "same_threshold_per_seed": same_threshold,
        "same_pool_per_seed": same_pool,
        "same_test_per_seed": same_test,
        "same_budget_grid_per_seed": same_budget,
        "same_gp_model_function": True,
        "only_acquisition_rule_changes": True,
    }
    leaf_values: list[bool] = []
    for value in checks.values():
        if isinstance(value, dict):
            leaf_values.extend(bool(item) for item in value.values())
        else:
            leaf_values.append(bool(value))
    checks["all_checks_passed"] = all(leaf_values)
    return checks


def summarize_selected_budgets(
    config: BenchmarkConfig,
    raw_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Aggregate selected-budget metric rows across seeds."""
    rows: list[dict[str, object]] = []
    for method in METHOD_ORDER:
        for budget in config.selected_budgets:
            subset = [
                row for row in raw_rows if row["method"] == method and row["budget"] == budget
            ]
            row: dict[str, object] = {
                "benchmark": config.name,
                "method": method,
                "budget": budget,
            }
            for metric in [
                "global_error",
                "near_boundary_error_q10",
                "near_boundary_error_q20",
                "near_boundary_error_q30",
                "latent_uncertainty_region_fraction",
            ]:
                mean, std = mean_std([float(item[metric]) for item in subset])
                row[f"mean_{metric}"] = f"{mean:.6f}"
                row[f"std_{metric}"] = f"{std:.6f}"
            rows.append(row)
    return rows


def summarize_final_metrics(
    config: BenchmarkConfig,
    raw_rows: list[dict[str, object]],
    query_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Aggregate final metrics and query-distance summaries by method."""
    raw_final: dict[str, dict[str, float]] = {}
    for method in METHOD_ORDER:
        subset = [
            row
            for row in raw_rows
            if row["method"] == method and row["budget"] == config.total_budget
        ]
        query_subset = [row for row in query_rows if row["method"] == method]
        distances = np.asarray(
            [float(row["true_boundary_distance"]) for row in query_subset],
            dtype=float,
        )
        raw_final[method] = {
            "mean_global_error": mean_std([float(item["global_error"]) for item in subset])[0],
            "mean_near_boundary_error_q10": mean_std(
                [float(item["near_boundary_error_q10"]) for item in subset]
            )[0],
            "mean_near_boundary_error_q20": mean_std(
                [float(item["near_boundary_error_q20"]) for item in subset]
            )[0],
            "mean_near_boundary_error_q30": mean_std(
                [float(item["near_boundary_error_q30"]) for item in subset]
            )[0],
            "mean_latent_uncertainty_region_fraction": mean_std(
                [float(item["latent_uncertainty_region_fraction"]) for item in subset]
            )[0],
            "median_query_distance": float(np.median(distances)),
        }

    ranks = {
        "rank_global_error": rank_methods(
            {method: values["mean_global_error"] for method, values in raw_final.items()}
        ),
        "rank_near_boundary_error_q10": rank_methods(
            {
                method: values["mean_near_boundary_error_q10"]
                for method, values in raw_final.items()
            }
        ),
        "rank_near_boundary_error_q20": rank_methods(
            {
                method: values["mean_near_boundary_error_q20"]
                for method, values in raw_final.items()
            }
        ),
        "rank_near_boundary_error_q30": rank_methods(
            {
                method: values["mean_near_boundary_error_q30"]
                for method, values in raw_final.items()
            }
        ),
        "rank_median_query_distance": rank_methods(
            {method: values["median_query_distance"] for method, values in raw_final.items()}
        ),
    }

    rows: list[dict[str, object]] = []
    for method in METHOD_ORDER:
        subset = [
            row
            for row in raw_rows
            if row["method"] == method and row["budget"] == config.total_budget
        ]
        query_subset = [row for row in query_rows if row["method"] == method]
        distances = np.asarray(
            [float(row["true_boundary_distance"]) for row in query_subset],
            dtype=float,
        )
        row: dict[str, object] = {
            "benchmark": config.name,
            "method": method,
        }
        for metric in [
            "global_error",
            "near_boundary_error_q10",
            "near_boundary_error_q20",
            "near_boundary_error_q30",
            "latent_uncertainty_region_fraction",
        ]:
            mean, std = mean_std([float(item[metric]) for item in subset])
            row[f"mean_final_{metric}"] = f"{mean:.6f}"
            row[f"std_final_{metric}"] = f"{std:.6f}"

        row.update(
            {
                "mean_query_distance": f"{float(distances.mean()):.6f}",
                "median_query_distance": f"{float(np.median(distances)):.6f}",
                "query_distance_q25": f"{float(np.percentile(distances, 25)):.6f}",
                "query_distance_q75": f"{float(np.percentile(distances, 75)):.6f}",
                "fraction_queries_in_pool_boundary_band_q10": f"{np.mean([bool(item['in_pool_boundary_band_q10']) for item in query_subset]):.6f}",
                "fraction_queries_in_pool_boundary_band_q20": f"{np.mean([bool(item['in_pool_boundary_band_q20']) for item in query_subset]):.6f}",
                "fraction_queries_in_pool_boundary_band_q30": f"{np.mean([bool(item['in_pool_boundary_band_q30']) for item in query_subset]):.6f}",
                "rank_global_error": ranks["rank_global_error"][method],
                "rank_near_boundary_error_q10": ranks["rank_near_boundary_error_q10"][method],
                "rank_near_boundary_error_q20": ranks["rank_near_boundary_error_q20"][method],
                "rank_near_boundary_error_q30": ranks["rank_near_boundary_error_q30"][method],
                "rank_median_query_distance": ranks["rank_median_query_distance"][method],
            }
        )
        rows.append(row)
    return rows


def best_method_from_final_rows(rows: list[dict[str, object]], field: str) -> str:
    """Find the method with the smallest numeric value for a final-row field."""
    return min(rows, key=lambda row: float(row[field]))["method"]


def plot_metric_curves(
    *,
    raw_rows: list[dict[str, object]],
    metric: str,
    config: BenchmarkConfig,
    output_path: Path,
    title: str,
    ylabel: str,
) -> None:
    """Plot mean metric curves with light seed-spread bands."""
    fig, ax = plt.subplots(figsize=(10.5, 6.4))
    for method in METHOD_ORDER:
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
        ax.plot(
            budgets,
            mean,
            color=METHOD_COLORS[method],
            label=method,
            linewidth=2.5,
        )
        ax.fill_between(
            budgets,
            np.maximum(0.0, mean - std),
            np.minimum(1.0, mean + std),
            color=METHOD_COLORS[method],
            alpha=0.10,
            linewidth=0,
        )
    ax.set(
        title=title,
        xlabel="Labelled evaluations",
        ylabel=ylabel,
        xlim=(config.initial_size, config.total_budget),
    )
    ax.grid(alpha=0.25)
    ax.legend(title="Acquisition rule", fontsize=9)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_final_global_vs_near(
    final_rows: list[dict[str, object]],
    config: BenchmarkConfig,
    output_path: Path,
) -> None:
    """Grouped bars comparing global and near-boundary final errors."""
    metrics = [
        ("mean_final_global_error", "global"),
        ("mean_final_near_boundary_error_q10", "q10"),
        ("mean_final_near_boundary_error_q20", "q20"),
        ("mean_final_near_boundary_error_q30", "q30"),
    ]
    positions = np.arange(len(METHOD_ORDER))
    width = 0.18
    fig, ax = plt.subplots(figsize=(11, 6.4))
    for offset, (field, label) in enumerate(metrics):
        values = [
            float(next(row for row in final_rows if row["method"] == method)[field])
            for method in METHOD_ORDER
        ]
        ax.bar(
            positions + (offset - 1.5) * width,
            values,
            width=width,
            label=label,
            alpha=0.88,
        )
    ax.set_xticks(positions)
    ax.set_xticklabels(
        ["random", "smallest\n|mu|", "straddle", "randomized\nstraddle", "expected\nfeasibility"],
        fontsize=10,
    )
    ax.set(
        title=f"{config.display_name}: final global vs near-boundary error",
        ylabel="Mean final error over seeds",
    )
    ax.grid(axis="y", alpha=0.25)
    ax.legend(title="Test subset")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_query_distance_boxplot(
    query_rows: list[dict[str, object]],
    config: BenchmarkConfig,
    output_path: Path,
) -> None:
    """Boxplot of true query distance to the threshold by method."""
    data = []
    for method in METHOD_ORDER:
        values = [
            max(float(row["true_boundary_distance"]), 1e-12)
            for row in query_rows
            if row["method"] == method
        ]
        data.append(values)
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    ax.boxplot(
        data,
        tick_labels=[method.replace("_", "\n") for method in METHOD_ORDER],
        showfliers=False,
    )
    ax.set_yscale("log")
    ax.set(
        title=f"{config.display_name}: query distance to true boundary",
        ylabel="abs(f(x_query) - threshold), log scale",
    )
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_query_distance_over_budget(
    query_rows: list[dict[str, object]],
    config: BenchmarkConfig,
    output_path: Path,
) -> None:
    """Mean query distance over acquisition steps by method."""
    fig, ax = plt.subplots(figsize=(10.5, 6.3))
    for method in METHOD_ORDER:
        method_rows = [row for row in query_rows if row["method"] == method]
        query_numbers = sorted({int(row["query_number"]) for row in method_rows})
        mean_values = []
        std_values = []
        budgets_after_query = []
        for query_number in query_numbers:
            subset = [row for row in method_rows if row["query_number"] == query_number]
            values = np.asarray(
                [max(float(row["true_boundary_distance"]), 1e-12) for row in subset],
                dtype=float,
            )
            mean_values.append(float(values.mean()))
            std_values.append(float(values.std()))
            budgets_after_query.append(int(subset[0]["budget_after_query"]))
        mean_array = np.asarray(mean_values)
        std_array = np.asarray(std_values)
        ax.plot(
            budgets_after_query,
            mean_array,
            color=METHOD_COLORS[method],
            label=method,
            linewidth=2.3,
        )
        ax.fill_between(
            budgets_after_query,
            np.maximum(1e-12, mean_array - std_array),
            mean_array + std_array,
            color=METHOD_COLORS[method],
            alpha=0.10,
            linewidth=0,
        )
    ax.set_yscale("log")
    ax.set(
        title=f"{config.display_name}: query distance over budget",
        xlabel="Labelled evaluations after query",
        ylabel="mean abs(f(x_query) - threshold), log scale",
        xlim=(config.initial_size + 1, config.total_budget),
    )
    ax.grid(alpha=0.25)
    ax.legend(title="Acquisition rule", fontsize=9)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def write_benchmark_notes(result: BenchmarkResult, output_path: Path) -> None:
    """Write benchmark-specific Week 4 notes."""
    final_rows = result.final_rows
    config = result.config
    best_global = best_method_from_final_rows(final_rows, "mean_final_global_error")
    best_q10 = best_method_from_final_rows(final_rows, "mean_final_near_boundary_error_q10")
    best_q20 = best_method_from_final_rows(final_rows, "mean_final_near_boundary_error_q20")
    best_q30 = best_method_from_final_rows(final_rows, "mean_final_near_boundary_error_q30")
    best_query = best_method_from_final_rows(final_rows, "median_query_distance")
    best_global_row = next(row for row in final_rows if row["method"] == best_global)
    best_q10_row = next(row for row in final_rows if row["method"] == best_q10)
    best_query_row = next(row for row in final_rows if row["method"] == best_query)

    text = f"""# Week 4 Boundary Metrics: {config.display_name}

## What changed

This evaluation keeps the same pool-based active-learning runs, GP-regression
stand-in, thresholds, seeds, and acquisition rules. It adds boundary-focused
metrics to complement global test-label misclassification error.

## Metrics

- Global error: fraction of all exact test labels predicted incorrectly.
- Near-boundary error q10/q20/q30: error restricted to the closest 10%, 20%,
  and 30% of test points by `abs(f(x) - threshold)`.
- Query distance: `abs(f(x_query) - threshold)` for each newly acquired point.
- Uncertainty-region fraction: fraction of test points with
  `abs(mu(x)) <= 1.96 * sigma(x)`.

## Main findings

- Best final global error: `{best_global}` with mean `{float(best_global_row['mean_final_global_error']):.3f}`.
- Best final q10 near-boundary error: `{best_q10}` with mean `{float(best_q10_row['mean_final_near_boundary_error_q10']):.3f}`.
- Best final q20 near-boundary error: `{best_q20}`.
- Best final q30 near-boundary error: `{best_q30}`.
- Closest median query distance: `{best_query}` with median `{float(best_query_row['median_query_distance']):.6f}`.

## Caveats

Near-boundary distance is measured in function-value space, not Euclidean
distance to the geometric contour. The uncertainty-region fraction uses the
latent GP-regression mean and standard deviation; it is not calibrated class
probability. These metrics strengthen the evaluation, but they do not replace a
proper GP classifier or a geometric boundary-distance metric.
"""
    output_path.write_text(text, encoding="utf-8")


def save_benchmark_outputs(result: BenchmarkResult, base_output_dir: Path = OUTPUT_DIR) -> None:
    """Save all required outputs for one benchmark."""
    config = result.config
    output_dir = base_output_dir / config.output_name
    output_dir.mkdir(parents=True, exist_ok=True)

    write_csv(output_dir / "raw_boundary_metrics.csv", result.raw_metric_rows)
    write_csv(output_dir / "query_distance_table.csv", result.query_rows)
    write_csv(output_dir / "boundary_metric_summary_table.csv", result.selected_budget_rows)
    write_csv(output_dir / "final_boundary_metrics_table.csv", result.final_rows)

    for quantile in BOUNDARY_QUANTILES:
        plot_metric_curves(
            raw_rows=result.raw_metric_rows,
            metric=f"near_boundary_error_q{quantile}",
            config=config,
            output_path=output_dir / f"near_boundary_error_curves_q{quantile}.png",
            title=f"{config.display_name}: near-boundary q{quantile} error",
            ylabel=f"Error on closest {quantile}% test points",
        )
    plot_final_global_vs_near(
        result.final_rows,
        config,
        output_dir / "final_global_vs_near_boundary_error.png",
    )
    plot_query_distance_boxplot(
        result.query_rows,
        config,
        output_dir / "query_distance_to_boundary_boxplot.png",
    )
    plot_query_distance_over_budget(
        result.query_rows,
        config,
        output_dir / "query_distance_to_boundary_over_budget.png",
    )
    plot_metric_curves(
        raw_rows=result.raw_metric_rows,
        metric="latent_uncertainty_region_fraction",
        config=config,
        output_path=output_dir / "uncertainty_region_fraction_curves.png",
        title=f"{config.display_name}: latent uncertainty-region fraction",
        ylabel="Fraction of test points with abs(mu) <= 1.96*sigma",
    )
    write_benchmark_notes(result, output_dir / "week4_boundary_metric_notes.md")

    summary = {
        "experiment": f"week4_boundary_metrics_{config.name}",
        "benchmark": config.name,
        "display_name": config.display_name,
        "domain": config.domain,
        "threshold": config.threshold,
        "threshold_percentile": config.threshold_percentile,
        "threshold_seed": config.threshold_seed,
        "threshold_sample_size": config.threshold_sample_size,
        "pool_size": config.pool_size,
        "test_size": config.test_size,
        "seeds": list(SEEDS),
        "initial_labelled_size": config.initial_size,
        "total_budget": config.total_budget,
        "selected_budgets": list(config.selected_budgets),
        "acquisition_rules": list(METHOD_ORDER),
        "method_descriptions": METHOD_DESCRIPTIONS,
        "scaling_rule": config.scaling_rule,
        "metrics": {
            "global_error": "fraction of all exact test labels predicted incorrectly",
            "near_boundary_error_q10": "error on closest 10% test points by abs(f(x)-threshold)",
            "near_boundary_error_q20": "error on closest 20% test points by abs(f(x)-threshold)",
            "near_boundary_error_q30": "error on closest 30% test points by abs(f(x)-threshold)",
            "query_distance": "abs(f(x_query)-threshold) for newly acquired points",
            "latent_uncertainty_region_fraction": "fraction of test points with abs(mu)<=1.96*sigma",
        },
        "fairness_checks": result.fairness_checks,
        "final_boundary_metrics": result.final_rows,
        "selected_budget_metric_summary": result.selected_budget_rows,
        "combined_summary_row": result.combined_row,
        "output_files": [
            "summary.json",
            "raw_boundary_metrics.csv",
            "query_distance_table.csv",
            "boundary_metric_summary_table.csv",
            "final_boundary_metrics_table.csv",
            "near_boundary_error_curves_q10.png",
            "near_boundary_error_curves_q20.png",
            "near_boundary_error_curves_q30.png",
            "final_global_vs_near_boundary_error.png",
            "query_distance_to_boundary_boxplot.png",
            "query_distance_to_boundary_over_budget.png",
            "uncertainty_region_fraction_curves.png",
            "week4_boundary_metric_notes.md",
        ],
        "caveats": [
            "Near-boundary distance is a function-value distance proxy, not Euclidean distance to the geometric contour.",
            "The uncertainty-region fraction uses the GP-regression latent mean and standard deviation, not calibrated class probability.",
            "The model is still GaussianProcessRegressor on {-1,+1} labels, not the final GP classifier.",
        ],
    }
    (output_dir / "summary.json").write_text(
        json.dumps(json_ready(summary), indent=2),
        encoding="utf-8",
    )


def build_combined_row(result: BenchmarkResult) -> dict[str, object]:
    """Create one high-level comparison row for the combined output."""
    final_rows = result.final_rows
    best_global = best_method_from_final_rows(final_rows, "mean_final_global_error")
    best_q10 = best_method_from_final_rows(final_rows, "mean_final_near_boundary_error_q10")
    best_q20 = best_method_from_final_rows(final_rows, "mean_final_near_boundary_error_q20")
    best_q30 = best_method_from_final_rows(final_rows, "mean_final_near_boundary_error_q30")
    best_query = best_method_from_final_rows(final_rows, "median_query_distance")
    boundary_consistent = best_global == best_q10 == best_q20 == best_q30
    return {
        "benchmark": result.config.name,
        "display_name": result.config.display_name,
        "best_global_error_method": best_global,
        "best_near_boundary_q10_method": best_q10,
        "best_near_boundary_q20_method": best_q20,
        "best_near_boundary_q30_method": best_q30,
        "closest_median_query_distance_method": best_query,
        "global_and_boundary_conclusion_consistent": boundary_consistent,
        "interpretation": (
            "The same method is best for global and all near-boundary errors."
            if boundary_consistent
            else "At least one near-boundary ranking differs from the global-error ranking."
        ),
    }


def write_combined_outputs(
    results: list[BenchmarkResult],
    base_output_dir: Path = OUTPUT_DIR,
) -> None:
    """Write combined Branin/Ackley summary outputs."""
    combined_dir = base_output_dir / "combined"
    combined_dir.mkdir(parents=True, exist_ok=True)
    combined_rows = [result.combined_row for result in results]
    write_csv(combined_dir / "week4_boundary_metric_summary.csv", combined_rows)
    lines = [
        "# Week 4 Boundary Metric Summary",
        "",
        "This summary compares the Week 2 Branin and Week 3 Ackley evaluations",
        "using boundary-focused metrics in addition to global test error.",
        "",
        "| Benchmark | Best global | Best q10 boundary | Best q20 boundary | Best q30 boundary | Closest median query distance | Conclusion |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in combined_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["display_name"]),
                    str(row["best_global_error_method"]),
                    str(row["best_near_boundary_q10_method"]),
                    str(row["best_near_boundary_q20_method"]),
                    str(row["best_near_boundary_q30_method"]),
                    str(row["closest_median_query_distance_method"]),
                    str(row["interpretation"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Caveats",
            "",
            "- Near-boundary subsets use `abs(f(x)-threshold)` percentiles, not Euclidean contour distance.",
            "- Query-distance plots use a log y-axis because function-value distances are skewed.",
            "- The GP uncertainty-region metric is latent-regression uncertainty, not calibrated class probability.",
        ]
    )
    (combined_dir / "week4_boundary_metric_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def run_benchmark(config: BenchmarkConfig) -> BenchmarkResult:
    """Run all methods/seeds for one benchmark and build output tables."""
    designs = [config.create_design(seed, config.threshold) for seed in SEEDS]
    runs_by_method: dict[str, list[BoundaryRun]] = {method: [] for method in METHOD_ORDER}
    for design in designs:
        for method in METHOD_ORDER:
            runs_by_method[method].append(run_boundary_method(config, design, method))

    fairness = verify_fairness(runs_by_method)
    if not fairness["all_checks_passed"]:
        raise RuntimeError(f"Fairness check failed for {config.name}: {fairness}")

    raw_rows = [
        row for method in METHOD_ORDER for run in runs_by_method[method] for row in run.metric_rows
    ]
    query_rows = [
        row for method in METHOD_ORDER for run in runs_by_method[method] for row in run.query_rows
    ]
    selected_rows = summarize_selected_budgets(config, raw_rows)
    final_rows = summarize_final_metrics(config, raw_rows, query_rows)
    placeholder = BenchmarkResult(
        config=config,
        runs_by_method=runs_by_method,
        fairness_checks=fairness,
        raw_metric_rows=raw_rows,
        query_rows=query_rows,
        selected_budget_rows=selected_rows,
        final_rows=final_rows,
        combined_row={},
    )
    placeholder.combined_row = build_combined_row(placeholder)
    return placeholder


def build_configs() -> list[BenchmarkConfig]:
    """Build Branin and Ackley benchmark configs matching prior weeks."""
    branin_threshold_seed = 2026
    branin_threshold_sample_size = 20_000
    branin_threshold = compute_branin_threshold(
        branin_threshold_sample_size,
        branin_threshold_seed,
    )
    ackley_threshold_values = threshold_sample_values()
    ackley_threshold = compute_ackley_threshold(ackley_threshold_values)
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
            create_design=lambda seed, threshold: create_branin_design(
                seed,
                threshold,
                initial_size=6,
                pool_size=1_500,
                test_size=4_000,
            ),
            rng_for_method=branin_rng_for_method,
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
            create_design=lambda seed, threshold: create_ackley_design(
                seed,
                threshold,
                initial_size=12,
                pool_size=ACKLEY_POOL_SIZE,
                test_size=ACKLEY_TEST_SIZE,
            ),
            rng_for_method=rng_for_week3_named_method,
            value_function=ackley_4d,
            scaling_rule="Ackley original coordinates are linearly scaled to [0,1]^4 for the GP.",
        ),
    ]


def run_experiment(output_dir: Path = OUTPUT_DIR) -> list[BenchmarkResult]:
    """Run both Week 4 boundary-metric evaluations and save outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results = [run_benchmark(config) for config in build_configs()]
    for result in results:
        save_benchmark_outputs(result, output_dir)
    write_combined_outputs(results, output_dir)
    return results


def main() -> None:
    results = run_experiment()
    print("Week 4 boundary-focused metrics complete.")
    for result in results:
        row = result.combined_row
        print(
            f"{row['display_name']}: best global={row['best_global_error_method']}, "
            f"best q10={row['best_near_boundary_q10_method']}, "
            f"closest queries={row['closest_median_query_distance_method']}"
        )
    print(f"Saved outputs to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
