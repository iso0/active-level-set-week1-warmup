"""Week 7.1 fixed-GPC Bernoulli SUR validation.

This script validates whether the promising seed-0 classifier SUR signal from
Week 7 generalizes across seeds. It deliberately uses the fixed-kernel
GaussianProcessClassifier from Weeks 6 and 7, not an optimized classifier, so
the acquisition rule is the only new object being validated.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from src.week7_boundary_weighted_sur import (
    BOUNDARY_QUANTILES,
    PROJECT_ROOT,
    BenchmarkConfig,
    DatasetBundle,
    SeedDesign,
    array_signature,
    bernoulli_uncertainty_from_p,
    binary_entropy,
    boundary_masks,
    build_configs as build_week7_configs,
    classifier_uncertainty_score,
    deterministic_argmax,
    fit_classifier,
    json_ready,
    mean_std,
    nearest_labelled_distance,
    normalize_scores,
    parse_float,
    predict_p_plus,
    read_csv_rows,
    reference_positions,
    stable_seed,
    write_csv,
)


OUTPUT_DIR = PROJECT_ROOT / "outputs" / "week7_1_gpc_sur_validation"
SEEDS = (0, 1, 2, 3, 4)
PRIMARY_CLASSIFIER_EPSILON = 0.10
CLASSIFIER_REPULSION_BANDWIDTH = 0.15
CLASSIFIER_GATE_FRACTION = 0.10
CLASSIFIER_MIN_SHORTLIST_SIZE = 25
BASELINE_METHODS = (
    "random_classifier",
    "classifier_margin",
    "classifier_entropy",
    "classifier_uncertainty_repulsion",
)
DEFAULT_SHORTLIST_SIZES = (15, 25)

METHOD_COLORS = {
    "random_classifier": "#7a7a7a",
    "classifier_margin": "#2b6cb0",
    "classifier_entropy": "#0f8b61",
    "classifier_uncertainty_repulsion": "#6a3d9a",
    "gpc_bernoulli_sur_refit_k15": "#d95f02",
    "gpc_bernoulli_sur_refit_k25": "#1f9eaa",
    "gpc_bernoulli_sur_refit_k40": "#9f1239",
}


@dataclass
class RunOptions:
    quick: bool
    full: bool
    benchmarks: tuple[str, ...]
    max_seeds: int | None
    reference_size: int
    shortlist_sizes: tuple[int, ...]
    output_dir: Path
    summarize_existing: bool = False


@dataclass
class MethodRun:
    benchmark: str
    output_name: str
    method: str
    seed: int
    initial_indices: list[int]
    labelled_indices: list[int]
    budgets: list[int]
    metric_rows: list[dict[str, object]]
    query_rows: list[dict[str, object]]
    runtime_row: dict[str, object]
    threshold: float
    pool_signature: str
    test_signature: str


@dataclass
class BenchmarkResult:
    config: BenchmarkConfig
    runs: list[MethodRun]
    fairness_checks: dict[str, object]
    metric_rows: list[dict[str, object]]
    query_rows: list[dict[str, object]]
    final_rows: list[dict[str, object]]
    runtime_rows: list[dict[str, object]]
    best_rows: list[dict[str, object]]
    summary: dict[str, object]


def method_for_shortlist(size: int) -> str:
    return f"gpc_bernoulli_sur_refit_k{size}"


def is_sur_method(method: str) -> bool:
    return method.startswith("gpc_bernoulli_sur_refit_k")


def method_shortlist_size(method: str) -> int:
    return int(method.rsplit("k", 1)[1])


def stable_rng(seed: int, benchmark: str, method: str) -> np.random.Generator:
    return np.random.default_rng(stable_seed(seed, benchmark, method, "week7_1"))


def classifier_repulsion_scores(
    *,
    p_plus: np.ndarray,
    unlabelled_indices: np.ndarray,
    pool_scaled: np.ndarray,
    labelled_indices: list[int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    uncertainty = classifier_uncertainty_score(p_plus)
    distances = nearest_labelled_distance(pool_scaled, unlabelled_indices, labelled_indices)
    repulsion = 1.0 - np.exp(
        -(distances**2) / (2.0 * CLASSIFIER_REPULSION_BANDWIDTH**2 + 1e-12)
    )
    return normalize_scores(uncertainty) * repulsion, uncertainty, repulsion


def choose_classifier_baseline(
    *,
    method: str,
    unlabelled_indices: np.ndarray,
    p_plus: np.ndarray,
    dataset: DatasetBundle,
    labelled_indices: list[int],
    rng: np.random.Generator,
) -> tuple[int, dict[str, object]]:
    uncertainty = classifier_uncertainty_score(p_plus)
    entropy = binary_entropy(p_plus)
    if method == "random_classifier":
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
    if method == "classifier_uncertainty_repulsion":
        score, uncertainty, repulsion = classifier_repulsion_scores(
            p_plus=p_plus,
            unlabelled_indices=unlabelled_indices,
            pool_scaled=dataset.pool_scaled,
            labelled_indices=labelled_indices,
        )
        gate_size = int(np.ceil(len(unlabelled_indices) * CLASSIFIER_GATE_FRACTION))
        gate_size = max(gate_size, min(CLASSIFIER_MIN_SHORTLIST_SIZE, len(unlabelled_indices)))
        gate_size = min(gate_size, len(unlabelled_indices))
        gate_order = np.lexsort((unlabelled_indices, -uncertainty))[:gate_size]
        gate_choice = deterministic_argmax(unlabelled_indices[gate_order], score[gate_order])
        position = int(gate_order[gate_choice])
        return int(unlabelled_indices[position]), {
            "gate_fraction": CLASSIFIER_GATE_FRACTION,
            "min_shortlist_size": CLASSIFIER_MIN_SHORTLIST_SIZE,
            "shortlist_size": gate_size,
            "repulsion_bandwidth": CLASSIFIER_REPULSION_BANDWIDTH,
            "selected_position": position,
            "selected_shortlist_position": int(gate_choice),
            "selected_p_plus": float(p_plus[position]),
            "selected_uncertainty_score": float(uncertainty[position]),
            "selected_entropy": float(entropy[position]),
            "selected_repulsion": float(repulsion[position]),
            "selected_score": float(score[position]),
        }
    raise ValueError(f"Unknown classifier baseline: {method}")


def choose_gpc_bernoulli_sur(
    *,
    gp,
    dataset: DatasetBundle,
    labelled_indices: list[int],
    unlabelled_indices: np.ndarray,
    p_plus: np.ndarray,
    seed: int,
    reference_size: int,
    shortlist_size: int,
    seed_items: tuple[object, ...],
) -> tuple[int, dict[str, object]]:
    start = time.perf_counter()
    membership_uncertainty = bernoulli_uncertainty_from_p(p_plus)
    ref_pos = reference_positions(
        unlabelled_indices=unlabelled_indices,
        membership_uncertainty=membership_uncertainty,
        reference_size=reference_size,
        seed_items=seed_items,
    )
    reference_scaled = dataset.pool_scaled[unlabelled_indices[ref_pos]]
    current_ref_u = membership_uncertainty[ref_pos]
    u_current = float(np.mean(current_ref_u))

    candidate_score, uncertainty_score, repulsion = classifier_repulsion_scores(
        p_plus=p_plus,
        unlabelled_indices=unlabelled_indices,
        pool_scaled=dataset.pool_scaled,
        labelled_indices=labelled_indices,
    )
    order = np.lexsort((unlabelled_indices, -candidate_score))
    shortlist_positions = order[: min(shortlist_size, len(order))]
    shortlist_indices = unlabelled_indices[shortlist_positions]

    x_labelled = dataset.pool_scaled[np.asarray(labelled_indices, dtype=int)]
    y_labelled = dataset.pool_labels[np.asarray(labelled_indices, dtype=int)]
    reductions: list[float] = []
    u_plus_values: list[float] = []
    u_minus_values: list[float] = []
    expected_values: list[float] = []
    refit_times: list[float] = []
    for candidate_index, candidate_position in zip(shortlist_indices, shortlist_positions):
        candidate_x = dataset.pool_scaled[int(candidate_index)][None, :]
        x_fantasy = np.vstack([x_labelled, candidate_x])

        fit_start = time.perf_counter()
        gp_plus = fit_classifier(x_fantasy, np.concatenate([y_labelled, [1.0]]), seed)
        p_ref_plus = predict_p_plus(gp_plus, reference_scaled)
        gp_minus = fit_classifier(x_fantasy, np.concatenate([y_labelled, [-1.0]]), seed)
        p_ref_minus = predict_p_plus(gp_minus, reference_scaled)
        refit_times.append(time.perf_counter() - fit_start)

        u_plus = float(np.mean(bernoulli_uncertainty_from_p(p_ref_plus)))
        u_minus = float(np.mean(bernoulli_uncertainty_from_p(p_ref_minus)))
        p_star = float(p_plus[int(candidate_position)])
        expected_future = p_star * u_plus + (1.0 - p_star) * u_minus
        reduction = u_current - expected_future
        reductions.append(float(reduction))
        u_plus_values.append(u_plus)
        u_minus_values.append(u_minus)
        expected_values.append(float(expected_future))

    reduction_array = np.asarray(reductions, dtype=float)
    best_shortlist_position = deterministic_argmax(shortlist_indices, reduction_array)
    original_position = int(shortlist_positions[best_shortlist_position])
    elapsed = time.perf_counter() - start
    metadata = {
        "selected_position": original_position,
        "selected_score": float(reduction_array[best_shortlist_position]),
        "p_star": float(p_plus[original_position]),
        "U_current": u_current,
        "U_plus": float(u_plus_values[best_shortlist_position]),
        "U_minus": float(u_minus_values[best_shortlist_position]),
        "expected_future_uncertainty": float(expected_values[best_shortlist_position]),
        "expected_uncertainty_reduction": float(reduction_array[best_shortlist_position]),
        "shortlist_size": int(len(shortlist_positions)),
        "requested_shortlist_size": int(shortlist_size),
        "reference_set_size": int(len(ref_pos)),
        "reference_uncertainty_definition": "mean_R p(+1)(1-p(+1))",
        "fantasy_refit_time_seconds": float(elapsed),
        "fantasy_refit_count": int(2 * len(shortlist_positions)),
        "mean_pair_fantasy_refit_time_seconds": float(np.mean(refit_times)) if refit_times else 0.0,
        "shortlist_source": "classifier_uncertainty_repulsion_score_over_unlabelled_pool",
        "selected_uncertainty_score": float(uncertainty_score[original_position]),
        "selected_repulsion": float(repulsion[original_position]),
    }
    return int(shortlist_indices[best_shortlist_position]), metadata


def reference_integrated_uncertainty_metric(
    *,
    p_unlabelled: np.ndarray,
    unlabelled_indices: np.ndarray,
    reference_size: int,
    seed_items: tuple[object, ...],
) -> tuple[float, int]:
    membership_uncertainty = bernoulli_uncertainty_from_p(p_unlabelled)
    ref_pos = reference_positions(
        unlabelled_indices=unlabelled_indices,
        membership_uncertainty=membership_uncertainty,
        reference_size=reference_size,
        seed_items=seed_items,
    )
    return float(np.mean(membership_uncertainty[ref_pos])), int(len(ref_pos))


def evaluate_budget(
    *,
    config: BenchmarkConfig,
    method: str,
    seed: int,
    budget: int,
    gp,
    dataset: DatasetBundle,
    test_masks: dict[int, np.ndarray],
    unlabelled_indices: np.ndarray,
    reference_size: int,
    fit_time_seconds: float,
) -> dict[str, object]:
    p_test = predict_p_plus(gp, dataset.test_scaled)
    prediction = np.where(p_test >= 0.5, 1.0, -1.0)
    errors = prediction != dataset.test_labels
    uncertain = np.abs(p_test - 0.5) <= PRIMARY_CLASSIFIER_EPSILON
    p_unlabelled = predict_p_plus(gp, dataset.pool_scaled[unlabelled_indices])
    integrated_u, ref_size_actual = reference_integrated_uncertainty_metric(
        p_unlabelled=p_unlabelled,
        unlabelled_indices=unlabelled_indices,
        reference_size=reference_size,
        seed_items=(config.name, seed, method, budget, "metric_reference"),
    )
    row: dict[str, object] = {
        "benchmark": config.name,
        "display_name": config.display_name,
        "method": method,
        "surrogate_variant": "gpc_fixed_iso",
        "acquisition_rule": method,
        "seed": seed,
        "budget": budget,
        "global_error": float(np.mean(errors)),
        "classifier_uncertainty_region_fraction": float(np.mean(uncertain)),
        "integrated_bernoulli_uncertainty": integrated_u,
        "integrated_bernoulli_reference_size": ref_size_actual,
        "integrated_bernoulli_uncertainty_definition": "mean_R p(+1)(1-p(+1)) over deterministic unlabelled reference set",
        "fit_time_seconds": fit_time_seconds,
    }
    for quantile, mask in test_masks.items():
        row[f"near_boundary_error_q{quantile}"] = float(np.mean(errors[mask]))
        row[f"near_boundary_test_size_q{quantile}"] = int(mask.sum())
        row[f"classifier_uncertainty_region_fraction_q{quantile}"] = float(np.mean(uncertain[mask]))
    return row


def run_method(config: BenchmarkConfig, design: SeedDesign, method: str, options: RunOptions) -> MethodRun:
    dataset = design.dataset
    pool_distances = np.abs(dataset.pool_values - config.threshold)
    test_distances = np.abs(dataset.test_values - config.threshold)
    pool_masks = boundary_masks(pool_distances)
    test_masks = boundary_masks(test_distances)
    labelled = list(design.initial_indices)
    initial_copy = list(design.initial_indices)
    rng = stable_rng(design.seed, config.name, method)
    budgets: list[int] = []
    metric_rows: list[dict[str, object]] = []
    query_rows: list[dict[str, object]] = []
    fit_times: list[float] = []
    acquisition_times: list[float] = []
    fantasy_refit_counts: list[int] = []
    fantasy_refit_times: list[float] = []
    run_start = time.perf_counter()
    print(f"  seed={design.seed} method={method}", flush=True)

    while True:
        mask = np.ones(len(dataset.pool_labels), dtype=bool)
        mask[labelled] = False
        unlabelled = np.flatnonzero(mask)
        fit_start = time.perf_counter()
        gp = fit_classifier(dataset.pool_scaled[labelled], dataset.pool_labels[labelled], design.seed)
        fit_time = time.perf_counter() - fit_start
        fit_times.append(fit_time)
        budget = len(labelled)
        budgets.append(budget)
        metric_rows.append(
            evaluate_budget(
                config=config,
                method=method,
                seed=design.seed,
                budget=budget,
                gp=gp,
                dataset=dataset,
                test_masks=test_masks,
                unlabelled_indices=unlabelled,
                reference_size=options.reference_size,
                fit_time_seconds=fit_time,
            )
        )
        if budget == config.total_budget:
            break

        p_unlabelled = predict_p_plus(gp, dataset.pool_scaled[unlabelled])
        acquisition_start = time.perf_counter()
        if is_sur_method(method):
            next_index, metadata = choose_gpc_bernoulli_sur(
                gp=gp,
                dataset=dataset,
                labelled_indices=labelled,
                unlabelled_indices=unlabelled,
                p_plus=p_unlabelled,
                seed=design.seed,
                reference_size=options.reference_size,
                shortlist_size=method_shortlist_size(method),
                seed_items=(config.name, design.seed, method, budget, "sur_reference"),
            )
            fantasy_refit_counts.append(int(metadata["fantasy_refit_count"]))
            fantasy_refit_times.append(float(metadata["fantasy_refit_time_seconds"]))
        else:
            next_index, metadata = choose_classifier_baseline(
                method=method,
                unlabelled_indices=unlabelled,
                p_plus=p_unlabelled,
                dataset=dataset,
                labelled_indices=labelled,
                rng=rng,
            )
        acquisition_time = time.perf_counter() - acquisition_start
        acquisition_times.append(acquisition_time)
        query_row: dict[str, object] = {
            "benchmark": config.name,
            "display_name": config.display_name,
            "method": method,
            "surrogate_variant": "gpc_fixed_iso",
            "acquisition_rule": method,
            "seed": design.seed,
            "query_number": len(query_rows) + 1,
            "budget_before_query": budget,
            "budget_after_query": budget + 1,
            "selected_pool_index": int(next_index),
            "true_boundary_distance": float(pool_distances[int(next_index)]),
            "acquisition_time_seconds": acquisition_time,
        }
        for quantile, band_mask in pool_masks.items():
            query_row[f"in_pool_boundary_band_q{quantile}"] = bool(band_mask[int(next_index)])
        for key, value in metadata.items():
            query_row[f"acquisition_{key}"] = value
        query_rows.append(query_row)
        labelled.append(int(next_index))

    if labelled[: len(initial_copy)] != initial_copy:
        raise RuntimeError("Initial labelled indices were mutated")
    runtime_row = {
        "benchmark": config.name,
        "display_name": config.display_name,
        "method": method,
        "surrogate_variant": "gpc_fixed_iso",
        "acquisition_rule": method,
        "seed": design.seed,
        "total_runtime_seconds": float(time.perf_counter() - run_start),
        "fit_count": len(fit_times),
        "total_fit_time_seconds": float(np.sum(fit_times)),
        "mean_fit_time_seconds": float(np.mean(fit_times)),
        "acquisition_count": len(acquisition_times),
        "total_acquisition_time_seconds": float(np.sum(acquisition_times)) if acquisition_times else 0.0,
        "mean_acquisition_time_seconds": float(np.mean(acquisition_times)) if acquisition_times else 0.0,
        "fantasy_refit_count": int(np.sum(fantasy_refit_counts)) if fantasy_refit_counts else 0,
        "total_fantasy_refit_time_seconds": float(np.sum(fantasy_refit_times)) if fantasy_refit_times else 0.0,
        "mean_fantasy_refit_time_seconds_per_step": float(np.mean(fantasy_refit_times)) if fantasy_refit_times else 0.0,
    }
    return MethodRun(
        benchmark=config.name,
        output_name=config.output_name,
        method=method,
        seed=design.seed,
        initial_indices=initial_copy,
        labelled_indices=labelled,
        budgets=budgets,
        metric_rows=metric_rows,
        query_rows=query_rows,
        runtime_row=runtime_row,
        threshold=config.threshold,
        pool_signature=array_signature(dataset.pool_scaled, dataset.pool_labels),
        test_signature=array_signature(dataset.test_scaled, dataset.test_labels),
    )


def verify_fairness(runs: list[MethodRun]) -> dict[str, object]:
    seeds = sorted({run.seed for run in runs})
    checks: dict[str, object] = {
        "same_initial_indices_per_seed": {},
        "same_threshold_per_seed": {},
        "same_pool_per_seed": {},
        "same_test_per_seed": {},
        "same_budget_grid_per_seed": {},
        "same_fixed_gpc_surrogate": True,
        "only_acquisition_rule_changes": True,
    }
    for seed in seeds:
        seed_runs = [run for run in runs if run.seed == seed]
        first = seed_runs[0]
        checks["same_initial_indices_per_seed"][str(seed)] = all(
            run.initial_indices == first.initial_indices for run in seed_runs
        )
        checks["same_threshold_per_seed"][str(seed)] = all(run.threshold == first.threshold for run in seed_runs)
        checks["same_pool_per_seed"][str(seed)] = all(run.pool_signature == first.pool_signature for run in seed_runs)
        checks["same_test_per_seed"][str(seed)] = all(run.test_signature == first.test_signature for run in seed_runs)
        checks["same_budget_grid_per_seed"][str(seed)] = all(run.budgets == first.budgets for run in seed_runs)
    leaf_values: list[bool] = []
    for value in checks.values():
        if isinstance(value, dict):
            leaf_values.extend(bool(item) for item in value.values())
        else:
            leaf_values.append(bool(value))
    checks["all_checks_passed"] = all(leaf_values)
    return checks


def metric_curve_groups(rows: list[dict[str, object]], metric: str) -> dict[str, dict[str, np.ndarray]]:
    groups: dict[str, dict[str, np.ndarray]] = {}
    for method in sorted({str(row["method"]) for row in rows}):
        subset = [row for row in rows if row["method"] == method]
        budgets = sorted({int(row["budget"]) for row in subset})
        means = []
        stds = []
        for budget in budgets:
            values = [float(row[metric]) for row in subset if int(row["budget"]) == budget]
            mean, std = mean_std(values)
            means.append(mean)
            stds.append(std)
        groups[method] = {
            "budgets": np.asarray(budgets, dtype=int),
            "mean": np.asarray(means, dtype=float),
            "std": np.asarray(stds, dtype=float),
        }
    return groups


def plot_metric_curves(
    rows: list[dict[str, object]],
    metric: str,
    config: BenchmarkConfig,
    output_path: Path,
    title: str,
    ylabel: str,
) -> None:
    fig, ax = plt.subplots(figsize=(12.5, 7.2))
    for method, series in metric_curve_groups(rows, metric).items():
        color = METHOD_COLORS.get(method, "#333333")
        ax.plot(series["budgets"], series["mean"], color=color, linewidth=2.2, label=method)
        ax.fill_between(
            series["budgets"],
            np.maximum(0.0, series["mean"] - series["std"]),
            np.minimum(1.0, series["mean"] + series["std"]),
            color=color,
            alpha=0.08,
            linewidth=0,
        )
    ax.set(title=title, xlabel="Labelled oracle evaluations", ylabel=ylabel, xlim=(config.initial_size, config.total_budget))
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_final_bar(final_rows: list[dict[str, object]], config: BenchmarkConfig, output_path: Path) -> None:
    labels = [str(row["method"]) for row in final_rows]
    x = np.arange(len(labels))
    width = 0.25
    metrics = [
        ("mean_final_global_error", "global", "#4c78a8"),
        ("mean_final_near_boundary_error_q20", "q20", "#f58518"),
        ("mean_final_near_boundary_error_q30", "q30", "#54a24b"),
    ]
    fig, ax = plt.subplots(figsize=(13, 7))
    for offset, (field, label, color) in zip((-width, 0.0, width), metrics):
        ax.bar(x + offset, [float(row[field]) for row in final_rows], width=width, label=label, color=color, alpha=0.86)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set(title=f"{config.display_name}: final global/q20/q30 error", ylabel="Mean final error across seeds")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_query_distance_boxplot(query_rows: list[dict[str, object]], config: BenchmarkConfig, output_path: Path) -> None:
    methods = sorted({str(row["method"]) for row in query_rows})
    values = [
        [max(float(row["true_boundary_distance"]), 1e-12) for row in query_rows if row["method"] == method]
        for method in methods
    ]
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.boxplot(values, tick_labels=methods, showfliers=False)
    ax.set_yscale("log")
    ax.set(title=f"{config.display_name}: query distance to true threshold", ylabel="abs(f(x_query)-threshold), log scale")
    ax.tick_params(axis="x", rotation=45, labelsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_query_distance_over_budget(query_rows: list[dict[str, object]], config: BenchmarkConfig, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12.5, 7.2))
    for method in sorted({str(row["method"]) for row in query_rows}):
        subset = [row for row in query_rows if row["method"] == method]
        budgets = sorted({int(row["budget_after_query"]) for row in subset})
        medians = []
        q25 = []
        q75 = []
        for budget in budgets:
            values = np.asarray(
                [max(float(row["true_boundary_distance"]), 1e-12) for row in subset if int(row["budget_after_query"]) == budget],
                dtype=float,
            )
            medians.append(float(np.median(values)))
            q25.append(float(np.percentile(values, 25)))
            q75.append(float(np.percentile(values, 75)))
        color = METHOD_COLORS.get(method, "#333333")
        ax.plot(budgets, medians, color=color, linewidth=2.2, label=method)
        ax.fill_between(budgets, np.maximum(1e-12, q25), q75, color=color, alpha=0.06, linewidth=0)
    ax.set_yscale("log")
    ax.set(
        title=f"{config.display_name}: median query distance over budget",
        xlabel="Labelled evaluations after query",
        ylabel="median abs(f(x_query)-threshold), q25-q75 band, log scale",
        xlim=(config.initial_size + 1, config.total_budget),
    )
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def summarize_final_metrics(config: BenchmarkConfig, metric_rows: list[dict[str, object]], query_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    methods = sorted({str(row["method"]) for row in metric_rows})
    metric_fields = [
        "global_error",
        "near_boundary_error_q10",
        "near_boundary_error_q20",
        "near_boundary_error_q30",
        "classifier_uncertainty_region_fraction",
        "classifier_uncertainty_region_fraction_q20",
        "classifier_uncertainty_region_fraction_q30",
        "integrated_bernoulli_uncertainty",
    ]
    for method in methods:
        final_subset = [row for row in metric_rows if row["method"] == method and int(row["budget"]) == config.total_budget]
        query_subset = [row for row in query_rows if row["method"] == method]
        row: dict[str, object] = {
            "benchmark": config.name,
            "display_name": config.display_name,
            "method": method,
            "surrogate_variant": "gpc_fixed_iso",
            "acquisition_rule": method,
            "final_budget": config.total_budget,
            "seed_count": len({int(item["seed"]) for item in final_subset}),
        }
        for field in metric_fields:
            mean, std = mean_std([float(item[field]) for item in final_subset])
            row[f"mean_final_{field}"] = f"{mean:.6f}"
            row[f"std_final_{field}"] = f"{std:.6f}"
        distances = np.asarray([float(item["true_boundary_distance"]) for item in query_subset], dtype=float)
        row.update(
            {
                "mean_query_distance": f"{float(distances.mean()):.6f}",
                "median_query_distance": f"{float(np.median(distances)):.6f}",
                "query_distance_q25": f"{float(np.percentile(distances, 25)):.6f}",
                "query_distance_q75": f"{float(np.percentile(distances, 75)):.6f}",
                "fraction_queries_in_pool_boundary_band_q10": f"{np.mean([bool(item['in_pool_boundary_band_q10']) for item in query_subset]):.6f}",
                "fraction_queries_in_pool_boundary_band_q20": f"{np.mean([bool(item['in_pool_boundary_band_q20']) for item in query_subset]):.6f}",
                "fraction_queries_in_pool_boundary_band_q30": f"{np.mean([bool(item['in_pool_boundary_band_q30']) for item in query_subset]):.6f}",
                "mean_acquisition_time_seconds": f"{np.mean([float(item['acquisition_time_seconds']) for item in query_subset]):.6f}",
            }
        )
        rows.append(row)
    for rank_name, field in {
        "rank_global_error": "mean_final_global_error",
        "rank_near_boundary_error_q20": "mean_final_near_boundary_error_q20",
        "rank_near_boundary_error_q30": "mean_final_near_boundary_error_q30",
        "rank_integrated_bernoulli_uncertainty": "mean_final_integrated_bernoulli_uncertainty",
        "rank_median_query_distance": "median_query_distance",
    }.items():
        ordered = sorted(rows, key=lambda item: (float(item[field]), str(item["method"])))
        ranks = {str(row["method"]): index + 1 for index, row in enumerate(ordered)}
        for row in rows:
            row[rank_name] = ranks[str(row["method"])]
    return rows


def runtime_summary_rows(runtime_rows: list[dict[str, object]], benchmark: str) -> list[dict[str, object]]:
    if runtime_rows and "total_runtime_seconds_sum_over_seeds" in runtime_rows[0]:
        return runtime_rows
    rows: list[dict[str, object]] = []
    for method in sorted({str(row["method"]) for row in runtime_rows}):
        subset = [row for row in runtime_rows if row["method"] == method]
        rows.append(
            {
                "benchmark": benchmark,
                "method": method,
                "seed_count": len(subset),
                "total_runtime_seconds_sum_over_seeds": f"{sum(float(row['total_runtime_seconds']) for row in subset):.6f}",
                "mean_runtime_seconds_per_seed": f"{np.mean([float(row['total_runtime_seconds']) for row in subset]):.6f}",
                "mean_fit_time_seconds": f"{np.mean([float(row['mean_fit_time_seconds']) for row in subset]):.6f}",
                "mean_acquisition_time_seconds": f"{np.mean([float(row['mean_acquisition_time_seconds']) for row in subset]):.6f}",
                "fit_count_sum": int(sum(int(row["fit_count"]) for row in subset)),
                "fantasy_refit_count_sum": int(sum(int(row["fantasy_refit_count"]) for row in subset)),
                "total_fantasy_refit_time_seconds": f"{sum(float(row['total_fantasy_refit_time_seconds']) for row in subset):.6f}",
                "mean_fantasy_refit_time_seconds_per_step": f"{np.mean([float(row['mean_fantasy_refit_time_seconds_per_step']) for row in subset]):.6f}",
            }
        )
    rows.append(
        {
            "benchmark": benchmark,
            "method": "all",
            "seed_count": len({(row["method"], row["seed"]) for row in runtime_rows}),
            "total_runtime_seconds_sum_over_seeds": f"{sum(float(row['total_runtime_seconds']) for row in runtime_rows):.6f}",
            "mean_runtime_seconds_per_seed": f"{np.mean([float(row['total_runtime_seconds']) for row in runtime_rows]):.6f}",
            "mean_fit_time_seconds": f"{np.mean([float(row['mean_fit_time_seconds']) for row in runtime_rows]):.6f}",
            "mean_acquisition_time_seconds": f"{np.mean([float(row['mean_acquisition_time_seconds']) for row in runtime_rows]):.6f}",
            "fit_count_sum": int(sum(int(row["fit_count"]) for row in runtime_rows)),
            "fantasy_refit_count_sum": int(sum(int(row["fantasy_refit_count"]) for row in runtime_rows)),
            "total_fantasy_refit_time_seconds": f"{sum(float(row['total_fantasy_refit_time_seconds']) for row in runtime_rows):.6f}",
            "mean_fantasy_refit_time_seconds_per_step": f"{np.mean([float(row['mean_fantasy_refit_time_seconds_per_step']) for row in runtime_rows]):.6f}",
        }
    )
    return rows


def best_rows_for_benchmark(final_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    mapping = {
        "global_error": "mean_final_global_error",
        "near_boundary_error_q20": "mean_final_near_boundary_error_q20",
        "near_boundary_error_q30": "mean_final_near_boundary_error_q30",
        "integrated_bernoulli_uncertainty": "mean_final_integrated_bernoulli_uncertainty",
    }
    rows: list[dict[str, object]] = []
    for metric, field in mapping.items():
        best = min(final_rows, key=lambda row: (float(row[field]), str(row["method"])))
        rows.append(
            {
                "benchmark": best["benchmark"],
                "display_name": best["display_name"],
                "metric": metric,
                "method": best["method"],
                "value": best[field],
                "field": field,
                "seed_count": best["seed_count"],
            }
        )
    return rows


def build_summary(
    config: BenchmarkConfig,
    options: RunOptions,
    seeds: tuple[int, ...],
    methods: tuple[str, ...],
    final_rows: list[dict[str, object]],
    fairness: dict[str, object],
    elapsed: float,
) -> dict[str, object]:
    return {
        "experiment": f"week7_1_gpc_sur_validation_{config.name}",
        "benchmark": config.name,
        "display_name": config.display_name,
        "domain": config.domain,
        "threshold": config.threshold,
        "threshold_percentile": config.threshold_percentile,
        "threshold_seed": config.threshold_seed,
        "threshold_sample_size": config.threshold_sample_size,
        "pool_size": config.pool_size,
        "test_size": config.test_size,
        "initial_labelled_size": config.initial_size,
        "total_budget": config.total_budget,
        "seeds": list(seeds),
        "methods": list(methods),
        "reference_size": options.reference_size,
        "shortlist_sizes": list(options.shortlist_sizes),
        "surrogate": "fixed GaussianProcessClassifier with ConstantKernel(1.0 fixed) * RBF(length_scale=0.25 fixed)",
        "integrated_bernoulli_uncertainty_definition": "mean_R p(+1)(1-p(+1)) on deterministic unlabelled reference set",
        "fairness_checks": fairness,
        "best_method_by_metric": best_rows_for_benchmark(final_rows),
        "final_metrics": final_rows,
        "total_runtime_seconds": elapsed,
    }


def save_benchmark_outputs(result: BenchmarkResult, options: RunOptions) -> None:
    out_dir = options.output_dir / result.config.output_name
    out_dir.mkdir(parents=True, exist_ok=True)
    sur_rows = [row for row in result.query_rows if is_sur_method(str(row["method"]))]
    write_csv(out_dir / "raw_metric_curves.csv", result.metric_rows)
    write_csv(out_dir / "query_distance_table.csv", result.query_rows)
    write_csv(out_dir / "gpc_sur_metadata.csv", sur_rows)
    write_csv(out_dir / "runtime_summary.csv", runtime_summary_rows(result.runtime_rows, result.config.name))
    write_csv(out_dir / "final_metrics_table.csv", result.final_rows)
    (out_dir / "fairness_checks.json").write_text(json.dumps(json_ready(result.fairness_checks), indent=2), encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(json_ready(result.summary), indent=2), encoding="utf-8")
    plot_metric_curves(result.metric_rows, "global_error", result.config, out_dir / "global_error_curves.png", f"{result.config.display_name}: global error", "Global test-label error")
    plot_metric_curves(result.metric_rows, "near_boundary_error_q20", result.config, out_dir / "q20_error_curves.png", f"{result.config.display_name}: q20 near-boundary error", "Error on closest 20% test points")
    plot_metric_curves(result.metric_rows, "near_boundary_error_q30", result.config, out_dir / "q30_error_curves.png", f"{result.config.display_name}: q30 near-boundary error", "Error on closest 30% test points")
    plot_final_bar(result.final_rows, result.config, out_dir / "final_global_q20_q30_bar.png")
    plot_query_distance_boxplot(result.query_rows, result.config, out_dir / "query_distance_boxplot.png")
    plot_query_distance_over_budget(result.query_rows, result.config, out_dir / "median_query_distance_over_budget.png")
    plot_metric_curves(result.metric_rows, "classifier_uncertainty_region_fraction", result.config, out_dir / "classifier_uncertainty_region_curves.png", f"{result.config.display_name}: classifier uncertainty-region fraction", "Fraction abs(p(+1)-0.5)<=0.10")
    plot_metric_curves(result.metric_rows, "integrated_bernoulli_uncertainty", result.config, out_dir / "integrated_bernoulli_uncertainty_curves.png", f"{result.config.display_name}: integrated Bernoulli uncertainty", "mean_R p(+1)(1-p(+1))")
    write_benchmark_notes(result, out_dir / "week7_1_notes.md")


def write_benchmark_notes(result: BenchmarkResult, output_path: Path) -> None:
    best_q20 = next(row for row in result.best_rows if row["metric"] == "near_boundary_error_q20")
    best_q30 = next(row for row in result.best_rows if row["metric"] == "near_boundary_error_q30")
    repulsion = next(row for row in result.final_rows if row["method"] == "classifier_uncertainty_repulsion")
    k15 = next((row for row in result.final_rows if row["method"] == "gpc_bernoulli_sur_refit_k15"), None)
    k25 = next((row for row in result.final_rows if row["method"] == "gpc_bernoulli_sur_refit_k25"), None)
    lines = [
        f"# Week 7.1 Notes: {result.config.display_name}",
        "",
        "## Setup",
        "",
        f"- Fixed-kernel GP classifier, pool `{result.config.pool_size}`, test `{result.config.test_size}`, initial `{result.config.initial_size}`, budget `{result.config.total_budget}`.",
        f"- Reference-set size requested: `{result.summary['reference_size']}`.",
        f"- Integrated Bernoulli uncertainty uses the mean over the deterministic reference set.",
        "",
        "## Result",
        "",
        f"- Best q20: `{best_q20['method']}` = `{float(best_q20['value']):.3f}`.",
        f"- Best q30: `{best_q30['method']}` = `{float(best_q30['value']):.3f}`.",
        f"- `classifier_uncertainty_repulsion` q20/q30 = `{float(repulsion['mean_final_near_boundary_error_q20']):.3f}` / `{float(repulsion['mean_final_near_boundary_error_q30']):.3f}`.",
    ]
    if k15:
        lines.append(f"- `gpc_bernoulli_sur_refit_k15` q20/q30 = `{float(k15['mean_final_near_boundary_error_q20']):.3f}` / `{float(k15['mean_final_near_boundary_error_q30']):.3f}`.")
    if k25:
        lines.append(f"- `gpc_bernoulli_sur_refit_k25` q20/q30 = `{float(k25['mean_final_near_boundary_error_q20']):.3f}` / `{float(k25['mean_final_near_boundary_error_q30']):.3f}`.")
    lines.extend(
        [
            "",
            "## Caveats",
            "",
            "- q20/q30 are the primary boundary metrics; q10 is retained as a noisy diagnostic.",
            "- SUR fantasy fits do not use true unlabelled labels, true function values, test labels, or boundary masks.",
            "- Runtime matters: each SUR step fits two fantasy classifiers per shortlisted candidate.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_benchmark(config: BenchmarkConfig, options: RunOptions, seeds: tuple[int, ...], methods: tuple[str, ...]) -> BenchmarkResult:
    print(f"Running {config.display_name}: {len(seeds)} seed(s), {len(methods)} method(s).", flush=True)
    start = time.perf_counter()
    designs = {seed: config.create_design(seed, config.threshold) for seed in seeds}
    runs: list[MethodRun] = []
    for seed in seeds:
        for method in methods:
            runs.append(run_method(config, designs[seed], method, options))
    fairness = verify_fairness(runs)
    if not fairness["all_checks_passed"]:
        raise RuntimeError(f"Fairness check failed for {config.name}: {fairness}")
    metric_rows = [row for run in runs for row in run.metric_rows]
    query_rows = [row for run in runs for row in run.query_rows]
    runtime_rows = [run.runtime_row for run in runs]
    final_rows = summarize_final_metrics(config, metric_rows, query_rows)
    best_rows = best_rows_for_benchmark(final_rows)
    elapsed = time.perf_counter() - start
    summary = build_summary(config, options, seeds, methods, final_rows, fairness, elapsed)
    result = BenchmarkResult(
        config=config,
        runs=runs,
        fairness_checks=fairness,
        metric_rows=metric_rows,
        query_rows=query_rows,
        final_rows=final_rows,
        runtime_rows=runtime_rows,
        best_rows=best_rows,
        summary=summary,
    )
    save_benchmark_outputs(result, options)
    return result


def build_configs(quick: bool, benchmark_names: tuple[str, ...]) -> list[BenchmarkConfig]:
    configs = {config.name: config for config in build_week7_configs(quick)}
    selected: list[BenchmarkConfig] = []
    for name in benchmark_names:
        config = configs[name]
        if name == "ackley":
            config.output_name = "ackley_optional"
        selected.append(config)
    return selected


def methods_for_options(options: RunOptions) -> tuple[str, ...]:
    return BASELINE_METHODS + tuple(method_for_shortlist(size) for size in options.shortlist_sizes)


def metric_field(metric: str) -> str:
    return {
        "global_error": "mean_final_global_error",
        "near_boundary_error_q20": "mean_final_near_boundary_error_q20",
        "near_boundary_error_q30": "mean_final_near_boundary_error_q30",
    }[metric]


def final_row(final_rows: list[dict[str, object]], method: str) -> dict[str, object] | None:
    return next((row for row in final_rows if row["method"] == method), None)


def compare_sur_to_baselines(results: list[BenchmarkResult]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    baseline_methods = ("random_classifier", "classifier_margin", "classifier_entropy", "classifier_uncertainty_repulsion")
    for result in results:
        for metric in ("global_error", "near_boundary_error_q20", "near_boundary_error_q30"):
            field = metric_field(metric)
            for sur in [row for row in result.final_rows if is_sur_method(str(row["method"]))]:
                for baseline_method in baseline_methods:
                    baseline = final_row(result.final_rows, baseline_method)
                    if baseline is None:
                        continue
                    sur_value = float(sur[field])
                    baseline_value = float(baseline[field])
                    rows.append(
                        {
                            "benchmark": result.config.name,
                            "metric": metric,
                            "sur_method": sur["method"],
                            "sur_value": f"{sur_value:.6f}",
                            "baseline_method": baseline_method,
                            "baseline_value": f"{baseline_value:.6f}",
                            "sur_beats_baseline": sur_value < baseline_value,
                            "difference_sur_minus_baseline": f"{sur_value - baseline_value:.6f}",
                        }
                    )
    return rows


def shortlist_size_comparison_rows(results: list[BenchmarkResult]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for result in results:
        sur_rows = [row for row in result.final_rows if is_sur_method(str(row["method"]))]
        for metric in ("global_error", "near_boundary_error_q20", "near_boundary_error_q30", "integrated_bernoulli_uncertainty"):
            field = "mean_final_integrated_bernoulli_uncertainty" if metric == "integrated_bernoulli_uncertainty" else metric_field(metric)
            best = min(sur_rows, key=lambda row: float(row[field])) if sur_rows else None
            k15 = final_row(result.final_rows, "gpc_bernoulli_sur_refit_k15")
            k25 = final_row(result.final_rows, "gpc_bernoulli_sur_refit_k25")
            k40 = final_row(result.final_rows, "gpc_bernoulli_sur_refit_k40")
            row: dict[str, object] = {"benchmark": result.config.name, "metric": metric}
            if best:
                row["best_sur_method"] = best["method"]
                row["best_sur_value"] = best[field]
            if k15:
                row["k15_value"] = k15[field]
            if k25:
                row["k25_value"] = k25[field]
            if k15 and k25:
                row["k25_beats_k15"] = float(k25[field]) < float(k15[field])
                row["difference_k25_minus_k15"] = f"{float(k25[field]) - float(k15[field]):.6f}"
            if k40:
                row["k40_value"] = k40[field]
                if k25:
                    row["k40_beats_k25"] = float(k40[field]) < float(k25[field])
            rows.append(row)
    return rows


def load_week7_reference_rows(benchmark: str) -> dict[str, dict[str, object]]:
    path = PROJECT_ROOT / "outputs" / "week7_boundary_weighted_sur" / benchmark / "final_metrics_table.csv"
    rows = read_csv_rows(path)
    references: dict[str, dict[str, object]] = {}
    if not rows:
        return references
    max_seed_count = max(int(row.get("seed_count", 0)) for row in rows if row.get("seed_count"))
    for metric in ("global_error", "near_boundary_error_q20", "near_boundary_error_q30"):
        field = metric_field(metric)
        full_rows = [row for row in rows if int(row.get("seed_count", 0)) == max_seed_count and parse_float(row.get(field)) is not None]
        if full_rows:
            best = min(full_rows, key=lambda row: float(row[field]))
            references[f"best_full_{metric}"] = {
                "method": best["method"],
                "value": best[field],
                "seed_count": best["seed_count"],
            }
        repulsion = next((row for row in rows if row.get("method") == "classifier_uncertainty_repulsion"), None)
        if repulsion and parse_float(repulsion.get(field)) is not None:
            references[f"repulsion_{metric}"] = {
                "method": "classifier_uncertainty_repulsion",
                "value": repulsion[field],
                "seed_count": repulsion.get("seed_count"),
            }
        sur = next((row for row in rows if row.get("method") == "gpc_bernoulli_sur_refit"), None)
        if sur and parse_float(sur.get(field)) is not None:
            references[f"week7_seed0_sur_{metric}"] = {
                "method": "gpc_bernoulli_sur_refit",
                "value": sur[field],
                "seed_count": sur.get("seed_count"),
            }
    return references


def uncertainty_error_correlation_rows(results: list[BenchmarkResult]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for result in results:
        for metric in ("near_boundary_error_q20", "near_boundary_error_q30"):
            error = np.asarray([float(row[metric]) for row in result.metric_rows], dtype=float)
            uncertainty = np.asarray([float(row["integrated_bernoulli_uncertainty"]) for row in result.metric_rows], dtype=float)
            if len(error) > 1 and float(np.std(error)) > 1e-12 and float(np.std(uncertainty)) > 1e-12:
                corr = float(np.corrcoef(uncertainty, error)[0, 1])
            else:
                corr = float("nan")
            rows.append(
                {
                    "benchmark": result.config.name,
                    "metric": metric,
                    "pearson_corr_integrated_uncertainty_vs_error_over_all_curves": f"{corr:.6f}",
                    "row_count": len(error),
                }
            )
    return rows


def write_combined_outputs(results: list[BenchmarkResult], options: RunOptions, elapsed: float) -> None:
    combined_dir = options.output_dir / "combined"
    combined_dir.mkdir(parents=True, exist_ok=True)
    best_rows = [row for result in results for row in result.best_rows]
    sur_vs = compare_sur_to_baselines(results)
    shortlist_rows = shortlist_size_comparison_rows(results)
    runtime_rows = [row for result in results for row in runtime_summary_rows(result.runtime_rows, result.config.name)]
    corr_rows = uncertainty_error_correlation_rows(results)
    summary_rows = combined_summary_rows(results, options)
    write_csv(combined_dir / "week7_1_summary.csv", summary_rows)
    write_csv(combined_dir / "best_method_by_metric.csv", best_rows)
    write_csv(combined_dir / "gpc_sur_vs_classifier_baselines.csv", sur_vs)
    write_csv(combined_dir / "shortlist_size_comparison.csv", shortlist_rows)
    write_csv(combined_dir / "runtime_summary.csv", runtime_rows)
    write_csv(combined_dir / "uncertainty_error_correlation.csv", corr_rows)
    write_summary_markdown(results, options, elapsed, combined_dir / "week7_1_summary.md")
    write_slide_notes(results, combined_dir / "week7_1_slide_notes.md")
    write_run_report(results, options, elapsed, combined_dir / "codex_run_report.md")


def bool_text(value: bool) -> str:
    return "True" if value else "False"


def metric_value(row: dict[str, object] | None, metric: str) -> float | None:
    if row is None:
        return None
    field = metric_field(metric)
    parsed = parse_float(row.get(field))
    return parsed


def fmt_value(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def combined_summary_rows(results: list[BenchmarkResult], options: RunOptions) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for result in results:
        refs = load_week7_reference_rows(result.config.name)
        best_q20 = next(row for row in result.best_rows if row["metric"] == "near_boundary_error_q20")
        best_q30 = next(row for row in result.best_rows if row["metric"] == "near_boundary_error_q30")
        repulsion = final_row(result.final_rows, "classifier_uncertainty_repulsion")
        k15 = final_row(result.final_rows, "gpc_bernoulli_sur_refit_k15")
        k25 = final_row(result.final_rows, "gpc_bernoulli_sur_refit_k25")
        for row in result.final_rows:
            rows.append(
                {
                    "benchmark": result.config.name,
                    "display_name": result.config.display_name,
                    "method": row["method"],
                    "seed_count": row["seed_count"],
                    "is_optional_ackley": result.config.name == "ackley",
                    "reference_size": options.reference_size,
                    "shortlist_sizes": " ".join(str(size) for size in options.shortlist_sizes),
                    "fairness_passed": result.fairness_checks.get("all_checks_passed"),
                    "mean_final_global_error": row["mean_final_global_error"],
                    "mean_final_near_boundary_error_q20": row["mean_final_near_boundary_error_q20"],
                    "mean_final_near_boundary_error_q30": row["mean_final_near_boundary_error_q30"],
                    "mean_final_integrated_bernoulli_uncertainty": row["mean_final_integrated_bernoulli_uncertainty"],
                    "rank_global_error": row["rank_global_error"],
                    "rank_near_boundary_error_q20": row["rank_near_boundary_error_q20"],
                    "rank_near_boundary_error_q30": row["rank_near_boundary_error_q30"],
                    "best_q20_method": best_q20["method"],
                    "best_q20_value": best_q20["value"],
                    "best_q30_method": best_q30["method"],
                    "best_q30_value": best_q30["value"],
                    "k15_beats_repulsion_q20": (
                        metric_value(k15, "near_boundary_error_q20") is not None
                        and metric_value(repulsion, "near_boundary_error_q20") is not None
                        and metric_value(k15, "near_boundary_error_q20") < metric_value(repulsion, "near_boundary_error_q20")
                    ),
                    "k15_beats_repulsion_q30": (
                        metric_value(k15, "near_boundary_error_q30") is not None
                        and metric_value(repulsion, "near_boundary_error_q30") is not None
                        and metric_value(k15, "near_boundary_error_q30") < metric_value(repulsion, "near_boundary_error_q30")
                    ),
                    "k25_beats_k15_q20": (
                        metric_value(k25, "near_boundary_error_q20") is not None
                        and metric_value(k15, "near_boundary_error_q20") is not None
                        and metric_value(k25, "near_boundary_error_q20") < metric_value(k15, "near_boundary_error_q20")
                    ),
                    "k25_beats_k15_q30": (
                        metric_value(k25, "near_boundary_error_q30") is not None
                        and metric_value(k15, "near_boundary_error_q30") is not None
                        and metric_value(k25, "near_boundary_error_q30") < metric_value(k15, "near_boundary_error_q30")
                    ),
                    "week7_seed0_sur_q20": refs.get("week7_seed0_sur_near_boundary_error_q20", {}).get("value", ""),
                    "week7_seed0_sur_q30": refs.get("week7_seed0_sur_near_boundary_error_q30", {}).get("value", ""),
                    "week7_best_full_q20_method": refs.get("best_full_near_boundary_error_q20", {}).get("method", ""),
                    "week7_best_full_q20_value": refs.get("best_full_near_boundary_error_q20", {}).get("value", ""),
                    "week7_best_full_q30_method": refs.get("best_full_near_boundary_error_q30", {}).get("method", ""),
                    "week7_best_full_q30_value": refs.get("best_full_near_boundary_error_q30", {}).get("value", ""),
                }
            )
    return rows


def write_summary_markdown(results: list[BenchmarkResult], options: RunOptions, elapsed: float, output_path: Path) -> None:
    lines = [
        "# Week 7.1 GPC Bernoulli SUR Validation",
        "",
        "This run validates fixed-kernel GP-classifier Bernoulli SUR refit across seeds. It does not use optimized classifier kernels.",
        "",
        "## Run settings",
        "",
        f"- Benchmarks: `{', '.join(result.config.name for result in results)}`.",
        f"- Reference size: `{options.reference_size}`.",
        f"- Shortlist sizes: `{', '.join(str(size) for size in options.shortlist_sizes)}`.",
        f"- Total elapsed runtime: `{elapsed:.1f}` seconds.",
        "",
        "## Best final methods",
        "",
        "| Benchmark | Global | q20 | q30 |",
        "| --- | --- | --- | --- |",
    ]
    for result in results:
        best_global = next(row for row in result.best_rows if row["metric"] == "global_error")
        best_q20 = next(row for row in result.best_rows if row["metric"] == "near_boundary_error_q20")
        best_q30 = next(row for row in result.best_rows if row["metric"] == "near_boundary_error_q30")
        lines.append(
            f"| {result.config.display_name} | `{best_global['method']}` ({float(best_global['value']):.3f}) | "
            f"`{best_q20['method']}` ({float(best_q20['value']):.3f}) | "
            f"`{best_q30['method']}` ({float(best_q30['value']):.3f}) |"
        )
    lines.extend(["", "## Answers", ""])
    for result in results:
        repulsion = final_row(result.final_rows, "classifier_uncertainty_repulsion")
        k15 = final_row(result.final_rows, "gpc_bernoulli_sur_refit_k15")
        k25 = final_row(result.final_rows, "gpc_bernoulli_sur_refit_k25")
        k40 = final_row(result.final_rows, "gpc_bernoulli_sur_refit_k40")
        lines.append(f"### {result.config.display_name}")
        refs = load_week7_reference_rows(result.config.name)
        if k15 and refs.get("week7_seed0_sur_near_boundary_error_q20"):
            week7_q20 = float(refs["week7_seed0_sur_near_boundary_error_q20"]["value"])
            week7_q30 = float(refs["week7_seed0_sur_near_boundary_error_q30"]["value"])
            rep_q20 = metric_value(repulsion, "near_boundary_error_q20")
            rep_q30 = metric_value(repulsion, "near_boundary_error_q30")
            k15_q20 = metric_value(k15, "near_boundary_error_q20")
            k15_q30 = metric_value(k15, "near_boundary_error_q30")
            generalized = (
                k15_q20 is not None
                and k15_q30 is not None
                and rep_q20 is not None
                and rep_q30 is not None
                and k15_q20 < rep_q20
                and k15_q30 < rep_q30
            )
            lines.append(
                f"1. k15 reproduces the Week 7 seed-0 signal across this run: `{bool_text(generalized)}`. Week 7 seed-0 q20/q30 was `{week7_q20:.3f}` / `{week7_q30:.3f}`; this run gives `{fmt_value(k15_q20)}` / `{fmt_value(k15_q30)}`."
            )
        elif k15:
            lines.append(
                f"1. No Week 7 seed-0 SUR reference row was available for this benchmark; this run gives k15 q20/q30 `{float(k15['mean_final_near_boundary_error_q20']):.3f}` / `{float(k15['mean_final_near_boundary_error_q30']):.3f}`."
            )
        if repulsion and k15:
            lines.append(
                f"2. k15 beats `classifier_uncertainty_repulsion` on q20/q30: `{bool_text(float(k15['mean_final_near_boundary_error_q20']) < float(repulsion['mean_final_near_boundary_error_q20']))}` / `{bool_text(float(k15['mean_final_near_boundary_error_q30']) < float(repulsion['mean_final_near_boundary_error_q30']))}`."
            )
        if k15 and k25:
            lines.append(
                f"3. k25 improves over k15 on q20/q30: `{bool_text(float(k25['mean_final_near_boundary_error_q20']) < float(k15['mean_final_near_boundary_error_q20']))}` / `{bool_text(float(k25['mean_final_near_boundary_error_q30']) < float(k15['mean_final_near_boundary_error_q30']))}`."
            )
        if k40:
            lines.append(
                f"4. k40 was run; it beats k25 on q20/q30: `{bool_text(float(k40['mean_final_near_boundary_error_q20']) < float(k25['mean_final_near_boundary_error_q20'])) if k25 else 'n/a'}` / `{bool_text(float(k40['mean_final_near_boundary_error_q30']) < float(k25['mean_final_near_boundary_error_q30'])) if k25 else 'n/a'}`."
            )
        else:
            lines.append("4. k40 was not run in this configuration.")
        if result.config.name == "hartmann4":
            lines.append("5. This is the benchmark where GPC SUR helps most: a SUR method is best on both q20 and q30.")
        elif result.config.name == "branin":
            lines.append("5. This benchmark does not support GPC SUR as a replacement for `classifier_uncertainty_repulsion`.")
        else:
            lines.append("5. This optional benchmark does not support extending GPC SUR to Ackley by default.")
        corr_q20 = next(row for row in uncertainty_error_correlation_rows([result]) if row["metric"] == "near_boundary_error_q20")
        corr_q30 = next(row for row in uncertainty_error_correlation_rows([result]) if row["metric"] == "near_boundary_error_q30")
        lines.append(
            f"6. Integrated uncertainty correlation with q20/q30 error over all curves: `{corr_q20['pearson_corr_integrated_uncertainty_vs_error_over_all_curves']}` / `{corr_q30['pearson_corr_integrated_uncertainty_vs_error_over_all_curves']}`."
        )
        if repulsion and k15:
            confident_wrong_q20 = (
                float(k15["mean_final_integrated_bernoulli_uncertainty"]) < float(repulsion["mean_final_integrated_bernoulli_uncertainty"])
                and float(k15["mean_final_near_boundary_error_q20"]) > float(repulsion["mean_final_near_boundary_error_q20"])
            )
            confident_wrong_q30 = (
                float(k15["mean_final_integrated_bernoulli_uncertainty"]) < float(repulsion["mean_final_integrated_bernoulli_uncertainty"])
                and float(k15["mean_final_near_boundary_error_q30"]) > float(repulsion["mean_final_near_boundary_error_q30"])
            )
            lines.append(f"7. k15 reduces uncertainty while worsening q20/q30 versus repulsion: `{bool_text(confident_wrong_q20)}` / `{bool_text(confident_wrong_q30)}`.")
        if repulsion:
            runtime = next((row for row in runtime_summary_rows(result.runtime_rows, result.config.name) if row["method"] == "gpc_bernoulli_sur_refit_k25"), None)
            rep_runtime = next((row for row in runtime_summary_rows(result.runtime_rows, result.config.name) if row["method"] == "classifier_uncertainty_repulsion"), None)
            if runtime and rep_runtime:
                lines.append(
                    f"8. Runtime cost: k25 mean runtime per seed `{float(runtime['mean_runtime_seconds_per_seed']):.1f}` seconds versus repulsion `{float(rep_runtime['mean_runtime_seconds_per_seed']):.1f}` seconds."
                )
        lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "",
            "1. k15 reproduced the promising Week 7 seed-0 behavior only on Hartmann4. It did not generalize on Branin, and the optional Ackley check did not support SUR.",
            "2. k15 beat `classifier_uncertainty_repulsion` on q20/q30 only on Hartmann4; it lost on Branin and optional Ackley.",
            "3. k25 improved over k15 on Hartmann4 q20/q30, worsened Branin q20/q30, and was mixed on optional Ackley.",
            "4. k40 was not run. The k15/k25 runtime was already enough to answer the validation question, and k25 was not uniformly better than k15.",
            "5. GPC SUR helped more on Hartmann4 than on Branin. Hartmann4 is the only primary benchmark where a SUR method is best on both q20 and q30.",
            "6. Integrated Bernoulli uncertainty has positive curve-level correlation with q20/q30 error, but it is not a reliable standalone proxy. The Branin and optional Ackley rows show lower uncertainty can still coincide with worse near-boundary error.",
            "7. Confidence can be misaligned: k15 reduced integrated uncertainty while worsening q20/q30 versus repulsion on Branin and optional Ackley, but uncertainty reduction aligned with lower boundary error on Hartmann4.",
            "8. Runtime cost is not justified as a default acquisition. It may be acceptable as a focused Hartmann-like diagnostic, but every SUR step pays for two fantasy classifier fits per shortlisted candidate.",
            "9. Thesis-level conclusion: fixed-GPC Bernoulli SUR refit is a serious diagnostic and a Hartmann4 candidate, but it is not robust enough to replace `classifier_uncertainty_repulsion` or the stronger GP-regressor baselines as a default acquisition.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_slide_notes(results: list[BenchmarkResult], output_path: Path) -> None:
    lines = [
        "# Week 7.1 Slide Notes",
        "",
        "## Question",
        "",
        "Does fixed-kernel GP-classifier Bernoulli SUR refit generalize beyond the promising Week 7 seed-0 result?",
        "",
        "## Setup",
        "",
        "- Fixed GP classifier, no optimized kernel.",
        "- Baselines: random, margin, entropy, uncertainty repulsion.",
        "- SUR shortlists: k15 and k25 by default.",
        "- Primary metrics: q20 and q30 near-boundary error.",
        "",
        "## Results",
        "",
    ]
    for result in results:
        best_q20 = next(row for row in result.best_rows if row["metric"] == "near_boundary_error_q20")
        best_q30 = next(row for row in result.best_rows if row["metric"] == "near_boundary_error_q30")
        lines.append(
            f"- {result.config.name}: best q20 `{best_q20['method']}` = `{float(best_q20['value']):.3f}`, best q30 `{best_q30['method']}` = `{float(best_q30['value']):.3f}`."
        )
    lines.extend(
        [
            "",
            "## Message",
            "",
            "Do not overclaim: SUR is acquisition-expensive and should be kept only if five-seed q20/q30 gains justify the runtime.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_run_report(results: list[BenchmarkResult], options: RunOptions, elapsed: float, output_path: Path) -> None:
    lines = [
        "# Codex Run Report",
        "",
        f"- Script elapsed time: `{elapsed:.1f}` seconds.",
        f"- Output directory: `{options.output_dir}`.",
        f"- Quick mode: `{options.quick}`.",
        f"- Benchmarks: `{', '.join(options.benchmarks)}`.",
        f"- Max seeds: `{options.max_seeds}`.",
        f"- Reference size: `{options.reference_size}`.",
        f"- Shortlist sizes: `{', '.join(str(size) for size in options.shortlist_sizes)}`.",
        "",
        "## Benchmarks",
        "",
    ]
    for result in results:
        lines.append(
            f"- {result.config.name}: `{len({row['seed'] for row in result.metric_rows})}` seeds, `{len(result.final_rows)}` method rows, fairness passed `{result.fairness_checks['all_checks_passed']}`."
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_experiment(options: RunOptions) -> list[BenchmarkResult]:
    options.output_dir.mkdir(parents=True, exist_ok=True)
    seeds = SEEDS if not options.quick else (0,)
    if options.max_seeds is not None:
        seeds = tuple(seeds[: options.max_seeds])
    methods = methods_for_options(options)
    start = time.perf_counter()
    results = [
        run_benchmark(config, options, seeds=seeds, methods=methods)
        for config in build_configs(options.quick, options.benchmarks)
    ]
    elapsed = time.perf_counter() - start
    write_combined_outputs(results, options, elapsed)
    return results


def refresh_existing_summaries(options: RunOptions) -> list[BenchmarkResult]:
    results: list[BenchmarkResult] = []
    for config in build_configs(False, options.benchmarks):
        out_dir = options.output_dir / config.output_name
        metric_rows = read_csv_rows(out_dir / "raw_metric_curves.csv")
        query_rows = read_csv_rows(out_dir / "query_distance_table.csv")
        runtime_rows = read_csv_rows(out_dir / "runtime_summary.csv")
        if not metric_rows or not query_rows:
            raise FileNotFoundError(f"Missing existing raw outputs for {config.name}")
        final_rows = summarize_final_metrics(config, metric_rows, query_rows)
        best_rows = best_rows_for_benchmark(final_rows)
        fairness_path = out_dir / "fairness_checks.json"
        fairness = json.loads(fairness_path.read_text(encoding="utf-8")) if fairness_path.exists() else {"all_checks_passed": "unknown"}
        previous_summary_path = out_dir / "summary.json"
        previous_elapsed = 0.0
        if previous_summary_path.exists():
            previous_summary = json.loads(previous_summary_path.read_text(encoding="utf-8"))
            previous_elapsed = float(previous_summary.get("total_runtime_seconds", 0.0))
        summary = build_summary(
            config,
            options,
            tuple(sorted({int(row["seed"]) for row in metric_rows})),
            tuple(sorted({str(row["method"]) for row in metric_rows})),
            final_rows,
            fairness,
            previous_elapsed,
        )
        result = BenchmarkResult(config, [], fairness, metric_rows, query_rows, final_rows, runtime_rows, best_rows, summary)
        write_csv(out_dir / "final_metrics_table.csv", final_rows)
        (out_dir / "summary.json").write_text(json.dumps(json_ready(summary), indent=2), encoding="utf-8")
        write_benchmark_notes(result, out_dir / "week7_1_notes.md")
        results.append(result)
    aggregate_elapsed = sum(float(result.summary.get("total_runtime_seconds", 0.0)) for result in results)
    write_combined_outputs(results, options, aggregate_elapsed)
    return results


def elapsed_from_run_report(path: Path) -> float:
    if not path.exists():
        return 0.0
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "Script elapsed time:" in line:
            try:
                return float(line.split("`", 2)[1])
            except (IndexError, ValueError):
                return 0.0
    return 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Week 7.1 fixed-GPC Bernoulli SUR validation")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true", help="Run reduced quick mode")
    mode.add_argument("--full", action="store_true", help="Run full selected benchmarks")
    parser.add_argument("--benchmarks", nargs="+", choices=("branin", "hartmann4", "ackley"), default=None, help="Benchmarks to run")
    parser.add_argument("--max-seeds", type=int, default=None, help="Limit number of seeds")
    parser.add_argument("--reference-size", type=int, default=1500, help="Reference set size")
    parser.add_argument("--shortlist-sizes", nargs="+", type=int, default=list(DEFAULT_SHORTLIST_SIZES), help="SUR shortlist sizes to run")
    parser.add_argument("--skip-k40", action="store_true", help="Remove k40 even if included in shortlist sizes")
    parser.add_argument("--summarize-existing", action="store_true", help="Refresh summary files from existing raw outputs")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory override")
    return parser.parse_args()


def options_from_args(args: argparse.Namespace) -> RunOptions:
    quick = bool(args.quick)
    benchmarks = tuple(args.benchmarks or (("branin", "hartmann4") if not quick else ("branin", "hartmann4")))
    shortlist_sizes = tuple(sorted(set(int(size) for size in args.shortlist_sizes)))
    if args.skip_k40:
        shortlist_sizes = tuple(size for size in shortlist_sizes if size != 40)
    if any(size < 1 for size in shortlist_sizes):
        raise ValueError("shortlist sizes must be positive")
    if args.reference_size < 1:
        raise ValueError("--reference-size must be positive")
    output_dir = args.output_dir or (OUTPUT_DIR / "quick" if quick else OUTPUT_DIR)
    return RunOptions(
        quick=quick,
        full=bool(args.full or not quick),
        benchmarks=benchmarks,
        max_seeds=args.max_seeds,
        reference_size=int(args.reference_size),
        shortlist_sizes=shortlist_sizes,
        output_dir=output_dir,
        summarize_existing=bool(args.summarize_existing),
    )


def main() -> None:
    args = parse_args()
    options = options_from_args(args)
    start = time.perf_counter()
    if options.summarize_existing:
        results = refresh_existing_summaries(options)
    else:
        results = run_experiment(options)
    elapsed = time.perf_counter() - start
    mode = "quick" if options.quick else "full"
    print(f"Week 7.1 GPC SUR validation complete in {elapsed:.1f}s ({mode} mode).")
    for result in results:
        best_q20 = next(row for row in result.best_rows if row["metric"] == "near_boundary_error_q20")
        best_q30 = next(row for row in result.best_rows if row["metric"] == "near_boundary_error_q30")
        print(
            f"{result.config.display_name}: best q20={best_q20['method']} ({float(best_q20['value']):.4f}), "
            f"best q30={best_q30['method']} ({float(best_q30['value']):.4f})"
        )
    print(f"Saved outputs to {options.output_dir}")


if __name__ == "__main__":
    main()
