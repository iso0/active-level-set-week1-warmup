"""Week 3 acquisition-rule comparison on a controlled 4D benchmark.

This is a first 4D synthetic benchmark for the thesis plumbing. It keeps the
Week 2 pool-based active-learning comparison, but replaces 2D thresholded
Branin with a deterministic 4D continuous function on [0, 1]^4.

The model is still GaussianProcessRegressor on {-1, +1} labels. That is the
same stand-in used in Weeks 1 and 2, not the final GP classifier.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from src.acquisition_rules import METHOD_DESCRIPTIONS, METHOD_ORDER, choose_next_index
from src.branin_week1 import fit_gp, random_two_class_initial_design


OUTPUT_DIR = (
    Path(__file__).resolve().parents[1] / "outputs" / "week3_4d_benchmark_comparison"
)
BENCHMARK_NAME = "controlled_synthetic_4d_boundary"
DOMAIN = "[0, 1]^4"
THRESHOLD_PERCENTILE = 50.0
THRESHOLD_SEED = 3026
THRESHOLD_SAMPLE_SIZE = 100_000
POOL_SIZE = 4_000
TEST_SIZE = 10_000
INITIAL_LABELLED_SIZE = 12
TOTAL_BUDGET = 80
SELECTED_BUDGETS = (INITIAL_LABELLED_SIZE, 40, TOTAL_BUDGET)
ERROR_TOLERANCE = 0.12


FUNCTION_DEFINITION_WORDS = (
    "A smooth deterministic function on scaled inputs x in [0,1]^4. It combines "
    "a tilted four-dimensional plane, two sinusoidal interaction terms, and a "
    "localized Gaussian bump. Labels are +1 when the function value is at or "
    "above the fixed median threshold and -1 otherwise."
)


@dataclass
class Benchmark4DDataset:
    """Pool and test data for the controlled 4D level-set benchmark."""

    seed: int
    threshold: float
    pool_scaled: np.ndarray
    pool_values: np.ndarray
    pool_labels: np.ndarray
    test_scaled: np.ndarray
    test_values: np.ndarray
    test_labels: np.ndarray


@dataclass
class SeedDesign:
    """Shared data and starting labels for all methods in one seed."""

    seed: int
    dataset: Benchmark4DDataset
    initial_indices: list[int]
    initial_resampling_attempts: int


@dataclass
class MethodRun:
    """One acquisition method on one fixed seed-specific 4D problem."""

    method: str
    seed: int
    dataset: Benchmark4DDataset
    initial_indices: list[int]
    labelled_indices: list[int]
    budgets: list[int]
    error_history: list[float]
    acquisition_metadata: list[dict[str, float | int | str]]


def controlled_4d_function(X: np.ndarray) -> np.ndarray:
    """Evaluate the selected deterministic 4D benchmark function.

    The custom function is chosen over Ackley for the first Week 3 run because
    it is designed as a level-set boundary benchmark rather than as an
    optimization landscape. The terms below keep the boundary nonlinear and
    four-dimensional while remaining interpretable and cheap to evaluate.
    """
    X = np.asarray(X, dtype=float)
    x0, x1, x2, x3 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
    tilted_plane = 0.95 * (x0 - 0.50) - 0.75 * (x1 - 0.50)
    tilted_plane += 0.65 * (x2 - 0.50) - 0.45 * (x3 - 0.50)
    wave_interactions = 0.30 * np.sin(2.0 * np.pi * (x0 + 0.35 * x3))
    wave_interactions += 0.24 * np.cos(2.0 * np.pi * (x1 - 0.60 * x2))
    curved_term = 0.50 * ((x0 - 0.58) ** 2 - 0.70 * (x1 - 0.42) ** 2)
    local_bump = -0.35 * np.exp(
        -(((x2 - 0.68) ** 2) / 0.030 + ((x3 - 0.32) ** 2) / 0.045)
    )
    return tilted_plane + wave_interactions + curved_term + local_bump


def sample_unit_hypercube(rng: np.random.Generator, size: int) -> np.ndarray:
    """Draw uniformly from [0, 1]^4."""
    return rng.uniform(0.0, 1.0, size=(size, 4))


def compute_threshold(
    sample_size: int = THRESHOLD_SAMPLE_SIZE,
    seed: int = THRESHOLD_SEED,
    percentile: float = THRESHOLD_PERCENTILE,
) -> float:
    """Estimate a fixed percentile threshold reproducibly."""
    rng = np.random.default_rng(seed)
    points = sample_unit_hypercube(rng, sample_size)
    return float(np.percentile(controlled_4d_function(points), percentile))


def labels_from_threshold(values: np.ndarray, threshold: float) -> np.ndarray:
    """Return +1 at or above the threshold and -1 below it."""
    return np.where(np.asarray(values) >= threshold, 1.0, -1.0)


def make_dataset(
    seed: int,
    threshold: float,
    pool_size: int = POOL_SIZE,
    test_size: int = TEST_SIZE,
) -> Benchmark4DDataset:
    """Create a reproducible 4D pool and independent 4D test set."""
    rng = np.random.default_rng(seed)
    pool_scaled = sample_unit_hypercube(rng, pool_size)
    test_scaled = sample_unit_hypercube(rng, test_size)
    pool_values = controlled_4d_function(pool_scaled)
    test_values = controlled_4d_function(test_scaled)
    return Benchmark4DDataset(
        seed=seed,
        threshold=threshold,
        pool_scaled=pool_scaled,
        pool_values=pool_values,
        pool_labels=labels_from_threshold(pool_values, threshold),
        test_scaled=test_scaled,
        test_values=test_values,
        test_labels=labels_from_threshold(test_values, threshold),
    )


def rng_for_week3_method(seed: int, method: str) -> np.random.Generator:
    """Create a deterministic RNG tied to the Week 3 seed and method name."""
    digest = hashlib.sha256(f"{seed}:{method}:week3_4d".encode("utf-8")).digest()
    method_offset = int.from_bytes(digest[:8], "little") % (2**32)
    return np.random.default_rng(method_offset)


def create_seed_design(
    seed: int,
    threshold: float,
    initial_size: int = INITIAL_LABELLED_SIZE,
    pool_size: int = POOL_SIZE,
    test_size: int = TEST_SIZE,
) -> SeedDesign:
    """Generate one dataset and one shared initial design for a seed."""
    dataset = make_dataset(seed, threshold, pool_size, test_size)
    rng = np.random.default_rng(seed + 200_000)
    initial_indices, attempts = random_two_class_initial_design(
        dataset.pool_labels, initial_size, rng
    )
    return SeedDesign(seed, dataset, initial_indices, attempts)


def predict_error(gp, dataset: Benchmark4DDataset) -> float:
    """Test-set misclassification error against exact threshold labels."""
    test_mean = gp.predict(dataset.test_scaled)
    prediction = np.where(test_mean >= 0.0, 1.0, -1.0)
    return float(np.mean(prediction != dataset.test_labels))


def run_method(design: SeedDesign, method: str, total_budget: int = TOTAL_BUDGET) -> MethodRun:
    """Run one acquisition method from the shared seed design."""
    dataset = design.dataset
    labelled = list(design.initial_indices)
    initial_copy = list(design.initial_indices)
    rng = rng_for_week3_method(design.seed, method)
    budgets: list[int] = []
    errors: list[float] = []
    metadata: list[dict[str, float | int | str]] = []

    while True:
        gp = fit_gp(dataset.pool_scaled[labelled], dataset.pool_labels[labelled], design.seed)
        budgets.append(len(labelled))
        errors.append(predict_error(gp, dataset))

        if len(labelled) == total_budget:
            break

        mask = np.ones(len(dataset.pool_labels), dtype=bool)
        mask[labelled] = False
        unlabelled = np.flatnonzero(mask)

        if method == "random":
            choice = choose_next_index(method, unlabelled, None, None, rng)
        else:
            pool_mean, pool_std = gp.predict(dataset.pool_scaled[unlabelled], return_std=True)
            choice = choose_next_index(method, unlabelled, pool_mean, pool_std, rng)

        choice.metadata["budget_before_query"] = len(labelled)
        choice.metadata["selected_pool_index"] = choice.index
        metadata.append(choice.metadata)
        labelled.append(choice.index)

    if labelled[: len(initial_copy)] != initial_copy:
        raise RuntimeError("Initial labelled indices were mutated")

    return MethodRun(
        method=method,
        seed=design.seed,
        dataset=dataset,
        initial_indices=initial_copy,
        labelled_indices=labelled,
        budgets=budgets,
        error_history=errors,
        acquisition_metadata=metadata,
    )


def verify_fairness(runs_by_method: dict[str, list[MethodRun]]) -> dict[str, object]:
    """Check that all methods share the same fixed problem within each seed."""
    per_seed_initial: dict[str, bool] = {}
    per_seed_threshold: dict[str, bool] = {}
    per_seed_pool: dict[str, bool] = {}
    per_seed_test: dict[str, bool] = {}
    per_seed_budget: dict[str, bool] = {}
    seeds = sorted({run.seed for runs in runs_by_method.values() for run in runs})

    for seed in seeds:
        seed_runs = [
            run for runs in runs_by_method.values() for run in runs if run.seed == seed
        ]
        first = seed_runs[0]
        per_seed_initial[str(seed)] = all(
            run.initial_indices == first.initial_indices for run in seed_runs
        )
        per_seed_threshold[str(seed)] = all(
            run.dataset.threshold == first.dataset.threshold for run in seed_runs
        )
        per_seed_pool[str(seed)] = all(
            np.array_equal(run.dataset.pool_scaled, first.dataset.pool_scaled)
            and np.array_equal(run.dataset.pool_labels, first.dataset.pool_labels)
            for run in seed_runs
        )
        per_seed_test[str(seed)] = all(
            np.array_equal(run.dataset.test_scaled, first.dataset.test_scaled)
            and np.array_equal(run.dataset.test_labels, first.dataset.test_labels)
            for run in seed_runs
        )
        per_seed_budget[str(seed)] = all(run.budgets == first.budgets for run in seed_runs)

    checks: dict[str, object] = {
        "same_initial_indices_per_seed": per_seed_initial,
        "same_threshold_per_seed": per_seed_threshold,
        "same_pool_and_pool_labels_per_seed": per_seed_pool,
        "same_test_and_test_labels_per_seed": per_seed_test,
        "same_budget_grid_per_seed": per_seed_budget,
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


def method_errors(runs: list[MethodRun]) -> np.ndarray:
    """Stack error histories for one method."""
    return np.asarray([run.error_history for run in runs], dtype=float)


def selected_budget_rows(
    runs_by_method: dict[str, list[MethodRun]],
    budgets: tuple[int, ...] = SELECTED_BUDGETS,
) -> list[dict[str, str]]:
    """Rows for the selected-budget CSV table."""
    rows: list[dict[str, str]] = []
    for method in METHOD_ORDER:
        runs = sorted(runs_by_method[method], key=lambda run: run.seed)
        for budget in budgets:
            values = []
            row: dict[str, str] = {"method": method, "budget": str(budget)}
            for run in runs:
                index = run.budgets.index(budget)
                error = run.error_history[index]
                row[f"seed_{run.seed}_error"] = f"{error:.6f}"
                values.append(error)
            row["mean_error"] = f"{np.mean(values):.6f}"
            row["std_error"] = f"{np.std(values):.6f}"
            rows.append(row)
    return rows


def method_summary_rows(runs_by_method: dict[str, list[MethodRun]]) -> list[dict[str, str]]:
    """One summary row per acquisition rule."""
    raw_rows = []
    for method in METHOD_ORDER:
        errors = method_errors(runs_by_method[method])
        initial = errors[:, 0]
        final = errors[:, -1]
        mean_initial = float(initial.mean())
        mean_final = float(final.mean())
        absolute = mean_initial - mean_final
        relative = 100.0 * absolute / mean_initial if mean_initial else 0.0
        raw_rows.append(
            {
                "method": method,
                "mean_initial_error": mean_initial,
                "mean_final_error": mean_final,
                "absolute_improvement": absolute,
                "relative_improvement_percent": relative,
                "final_error_std": float(final.std()),
            }
        )

    ranked = sorted(raw_rows, key=lambda row: row["mean_final_error"])
    ranks = {row["method"]: rank + 1 for rank, row in enumerate(ranked)}
    rows = []
    for row in raw_rows:
        rows.append(
            {
                "method": row["method"],
                "mean_initial_error": f"{row['mean_initial_error']:.6f}",
                "mean_final_error": f"{row['mean_final_error']:.6f}",
                "absolute_improvement": f"{row['absolute_improvement']:.6f}",
                "relative_improvement_percent": f"{row['relative_improvement_percent']:.2f}",
                "final_error_std": f"{row['final_error_std']:.6f}",
                "rank_by_mean_final_error": str(ranks[row["method"]]),
            }
        )
    return rows


def first_budget_at_or_below(
    budgets: list[int],
    errors: np.ndarray,
    tolerance: float,
) -> int | None:
    """First labelled budget where an error curve reaches a fixed tolerance."""
    for budget, error in zip(budgets, errors):
        if float(error) <= tolerance:
            return int(budget)
    return None


def tolerance_reach_summary(
    runs_by_method: dict[str, list[MethodRun]],
    tolerance: float = ERROR_TOLERANCE,
) -> dict[str, object]:
    """Summarize when each method reaches a fixed test-error tolerance."""
    method_reach: dict[str, object] = {}
    for method in METHOD_ORDER:
        runs = sorted(runs_by_method[method], key=lambda run: run.seed)
        errors = method_errors(runs)
        mean_errors = errors.mean(axis=0)
        mean_budget = first_budget_at_or_below(runs[0].budgets, mean_errors, tolerance)
        per_seed = {
            str(run.seed): first_budget_at_or_below(
                run.budgets,
                np.asarray(run.error_history, dtype=float),
                tolerance,
            )
            for run in runs
        }
        method_reach[method] = {
            "mean_curve_first_budget": mean_budget,
            "per_seed_first_budget": per_seed,
        }

    reference = method_reach["smallest_abs_mu"]["mean_curve_first_budget"]
    no_later_than_smallest_abs_mu = {}
    for method, details in method_reach.items():
        budget = details["mean_curve_first_budget"]
        no_later_than_smallest_abs_mu[method] = (
            budget is not None and reference is not None and budget <= reference
        )

    return {
        "metric": "fraction of exact controlled-4D test labels misclassified",
        "tolerance": tolerance,
        "note": (
            "This is a test-label misclassification tolerance proxy, not a "
            "separate geometric boundary-distance metric."
        ),
        "smallest_abs_mu_reference_budget": reference,
        "per_method": method_reach,
        "mean_curve_reaches_no_later_than_smallest_abs_mu": no_later_than_smallest_abs_mu,
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write a list of dictionaries as a CSV file."""
    if not rows:
        raise ValueError(f"No rows to write for {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_error_curves_all_methods(
    runs_by_method: dict[str, list[MethodRun]],
    output_path: Path,
) -> None:
    """Mean error curves with light spread bands for all methods."""
    colors = {
        "random": "#8c8c8c",
        "smallest_abs_mu": "#2b6cb0",
        "straddle": "#0f8b61",
        "randomized_straddle": "#b7791f",
        "expected_feasibility": "#9f1239",
    }
    fig, ax = plt.subplots(figsize=(10.5, 6.5))
    max_error = 0.0
    for method in METHOD_ORDER:
        runs = runs_by_method[method]
        budgets = np.asarray(runs[0].budgets)
        errors = method_errors(runs)
        max_error = max(max_error, float(errors.max()))
        mean = errors.mean(axis=0)
        std = errors.std(axis=0)
        ax.plot(budgets, mean, label=method, color=colors[method], linewidth=2.6)
        ax.fill_between(
            budgets,
            np.maximum(0.0, mean - std),
            np.minimum(1.0, mean + std),
            color=colors[method],
            alpha=0.10,
            linewidth=0,
        )

    ax.set(
        title="Week 3 controlled 4D benchmark acquisition comparison",
        xlabel="Labelled oracle evaluations",
        ylabel=f"Fraction of {TEST_SIZE:,} exact test labels mislabelled",
        xlim=(INITIAL_LABELLED_SIZE, TOTAL_BUDGET),
        ylim=(0.0, min(1.0, max(0.25, max_error + 0.04))),
    )
    ax.grid(alpha=0.25)
    ax.legend(title="Acquisition rule", fontsize=9)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_final_error_bar_chart(
    runs_by_method: dict[str, list[MethodRun]],
    output_path: Path,
) -> None:
    """Bar chart of mean final error at the Week 3 budget."""
    methods = list(METHOD_ORDER)
    means = []
    stds = []
    for method in methods:
        final = method_errors(runs_by_method[method])[:, -1]
        means.append(float(final.mean()))
        stds.append(float(final.std()))

    fig, ax = plt.subplots(figsize=(10, 6))
    positions = np.arange(len(methods))
    colors = ["#8c8c8c", "#2b6cb0", "#0f8b61", "#b7791f", "#9f1239"]
    ax.bar(positions, means, yerr=stds, capsize=6, color=colors, alpha=0.88)
    ax.set_xticks(positions)
    ax.set_xticklabels(
        [
            "random",
            "smallest\n|mu|",
            "straddle",
            "randomized\nstraddle",
            "expected\nfeasibility",
        ],
        fontsize=10,
    )
    ax.set(
        title=f"Mean final controlled-4D test error at budget {TOTAL_BUDGET}",
        ylabel="Mean final error (+/- 1 std)",
        ylim=(0.0, max(means) + max(stds) + 0.04),
    )
    ax.grid(axis="y", alpha=0.25)
    for pos, mean in zip(positions, means):
        ax.text(pos, mean + 0.008, f"{100 * mean:.1f}%", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def class_balance(labels: np.ndarray) -> dict[str, float]:
    """Return class fractions for JSON summaries."""
    labels = np.asarray(labels)
    return {
        "negative_fraction": float(np.mean(labels == -1.0)),
        "positive_fraction": float(np.mean(labels == 1.0)),
    }


def save_slide_notes(
    summary_rows: list[dict[str, str]],
    best_method: str,
    tolerance_check: dict[str, object],
    output_path: Path,
) -> None:
    """Write beginner-friendly notes for Google Slides."""
    best_row = next(row for row in summary_rows if row["method"] == best_method)
    tolerance = float(tolerance_check["tolerance"])
    tolerance_rows = tolerance_check["per_method"]
    tolerance_lines = []
    for method in METHOD_ORDER:
        budget = tolerance_rows[method]["mean_curve_first_budget"]
        if budget is None:
            tolerance_lines.append(
                f"- {method}: did not reach {100 * tolerance:.0f}% mean test error."
            )
        else:
            tolerance_lines.append(
                f"- {method}: reached {100 * tolerance:.0f}% mean test error at n={budget}."
            )
    tolerance_text = "\n".join(tolerance_lines)
    text = f"""# Week 3 Slide Notes

## Why move from 2D Branin to 4D

The Week 1 and Week 2 Branin experiments were useful because they made the
active-learning loop visible and testable in two dimensions. The real
laser-metal process-parameter space is four-dimensional, so Week 3 adds a first
4D synthetic benchmark before using the real melt-pool data.

## Selected benchmark

The benchmark is a controlled synthetic 4D boundary function on `[0, 1]^4`.
It is deterministic and continuous. We label a point +1 when the function value
is above a fixed median threshold and -1 otherwise.

I chose this over Ackley for the first Week 3 run because the boundary can be
designed for level-set estimation directly. Ackley is still a good named
benchmark to try later, but it is primarily an optimization test function.

## How the comparison is kept fair

For each seed, all five acquisition rules use the same threshold, same pool,
same test set, same initial labelled points, same GP-regression stand-in, and
same budget. Only the rule for choosing the next pool point changes.

The five rules are the same as Week 2: random, smallest |mu|, straddle,
randomized straddle, and expected feasibility.

## What the results show

The y-axis is test-label misclassification error against exact threshold labels.
Lower is better. In this run the best mean final method is `{best_method}`, with
mean final error `{float(best_row['mean_final_error']):.3f}` at budget {TOTAL_BUDGET}.

Using a fixed {100 * tolerance:.0f}% test-error tolerance as a lightweight
progress check:

{tolerance_text}

## Caveats

This is a first 4D synthetic benchmark. The GP regressor is still a stand-in,
not the final GP classifier. The metric is test-label misclassification error,
not a geometric boundary-distance metric. The result is preliminary and should
be discussed with Ioan before treating it as a final thesis direction.

## Suggested next step for Ioan

Ask Ioan whether this controlled 4D boundary is a good first Week 3 bridge, or
whether he would prefer the next run to use thresholded 4D Ackley as a named
benchmark. Also ask whether the next metric should include a boundary-distance
or contour-quality measure in addition to test misclassification error.
"""
    output_path.write_text(text, encoding="utf-8")


def save_summary(
    runs_by_method: dict[str, list[MethodRun]],
    designs: list[SeedDesign],
    output_path: Path,
    threshold: float,
) -> tuple[list[dict[str, str]], str, dict[str, object]]:
    """Save the requested JSON summary and return table rows plus winner."""
    fairness = verify_fairness(runs_by_method)
    if not fairness["all_checks_passed"]:
        raise RuntimeError(f"Fairness check failed: {fairness}")

    summary_rows = method_summary_rows(runs_by_method)
    best_method = min(summary_rows, key=lambda row: float(row["mean_final_error"]))["method"]
    tolerance_check = tolerance_reach_summary(runs_by_method)

    per_method: dict[str, dict[str, object]] = {}
    for method in METHOD_ORDER:
        per_seed: dict[str, object] = {}
        for run in sorted(runs_by_method[method], key=lambda item: item.seed):
            per_seed[str(run.seed)] = {
                "initial_indices": run.initial_indices,
                "initial_error": run.error_history[0],
                "final_error": run.error_history[-1],
                "budgets": run.budgets,
                "error_history": run.error_history,
                "selected_indices": run.labelled_indices[len(run.initial_indices) :],
                "acquisition_metadata": run.acquisition_metadata,
            }
        per_method[method] = {
            "description": METHOD_DESCRIPTIONS[method],
            "per_seed": per_seed,
        }

    summary = {
        "experiment": "week3_4d_benchmark_comparison",
        "benchmark_name": BENCHMARK_NAME,
        "function_definition_words": FUNCTION_DEFINITION_WORDS,
        "threshold": threshold,
        "threshold_percentile": THRESHOLD_PERCENTILE,
        "threshold_rule": (
            "Fixed once as the median over a reproducible uniform sample from [0,1]^4."
        ),
        "threshold_estimation_seed": THRESHOLD_SEED,
        "threshold_estimation_sample_size": THRESHOLD_SAMPLE_SIZE,
        "domain": DOMAIN,
        "pool_size_per_seed": POOL_SIZE,
        "test_size_per_seed": TEST_SIZE,
        "seeds": [design.seed for design in designs],
        "acquisition_rules": list(METHOD_ORDER),
        "initial_labelled_size": INITIAL_LABELLED_SIZE,
        "total_budget": TOTAL_BUDGET,
        "selected_budget_table_budgets": list(SELECTED_BUDGETS),
        "gp_model_note": (
            "GaussianProcessRegressor on {-1,+1} labels is still a stand-in, "
            "not the final GP classifier."
        ),
        "error_definition": "fraction of exact threshold test labels predicted incorrectly",
        "prediction_rule": "+1 if GP latent mean mu >= 0, else -1",
        "fairness_note": (
            "For each seed, all acquisition rules use the same threshold, pool, "
            "test set, GP regressor, initial labelled indices, and budget. Only "
            "the acquisition rule changes."
        ),
        "fairness_checks": fairness,
        "initial_indices_by_seed": {
            str(design.seed): design.initial_indices for design in designs
        },
        "initial_resampling_attempts_by_seed": {
            str(design.seed): design.initial_resampling_attempts for design in designs
        },
        "class_balance_by_seed": {
            str(design.seed): {
                "pool": class_balance(design.dataset.pool_labels),
                "test": class_balance(design.dataset.test_labels),
            }
            for design in designs
        },
        "method_summary": summary_rows,
        "fixed_error_tolerance_check": tolerance_check,
        "best_final_method_by_mean_final_error": best_method,
        "runtime_settings_note": (
            "The first 4D run uses 5 seeds, pool size 4000, test size 10000, "
            "initial labelled size 12, and total budget 80 to keep runtime "
            "reasonable on a laptop while staying larger than the 2D Branin setup."
        ),
        "caveats": [
            "This is a first 4D synthetic benchmark.",
            "The GP regressor is still a stand-in, not the final GP classifier.",
            "The metric is test-label misclassification error, not a geometric boundary-distance metric.",
            "The result is preliminary and should be discussed with Ioan before treating it as a final thesis direction.",
        ],
        "per_method": per_method,
    }
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary_rows, best_method, tolerance_check


def run_experiment(
    seeds: tuple[int, ...] = (0, 1, 2, 3, 4),
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, list[MethodRun]]:
    """Run Week 3 and save all requested artifacts."""
    threshold = compute_threshold()
    designs = [create_seed_design(seed, threshold) for seed in seeds]

    runs_by_method: dict[str, list[MethodRun]] = {method: [] for method in METHOD_ORDER}
    for design in designs:
        for method in METHOD_ORDER:
            runs_by_method[method].append(run_method(design, method))

    output_dir.mkdir(parents=True, exist_ok=True)
    plot_error_curves_all_methods(runs_by_method, output_dir / "error_curves_all_methods.png")
    plot_final_error_bar_chart(runs_by_method, output_dir / "final_error_bar_chart.png")

    selected_rows = selected_budget_rows(runs_by_method)
    write_csv(output_dir / "selected_budget_table.csv", selected_rows)
    summary_rows, best_method, tolerance_check = save_summary(
        runs_by_method,
        designs,
        output_dir / "summary.json",
        threshold,
    )
    write_csv(output_dir / "method_summary_table.csv", summary_rows)
    save_slide_notes(
        summary_rows,
        best_method,
        tolerance_check,
        output_dir / "week3_slide_notes.md",
    )
    return runs_by_method


def main() -> None:
    runs_by_method = run_experiment()
    rows = method_summary_rows(runs_by_method)
    best = min(rows, key=lambda row: float(row["mean_final_error"]))
    print("Week 3 controlled 4D benchmark comparison complete.")
    for row in rows:
        print(
            f"{row['method']}: initial={float(row['mean_initial_error']):.4f}, "
            f"final={float(row['mean_final_error']):.4f}, "
            f"rank={row['rank_by_mean_final_error']}"
        )
    print(f"Best mean final method: {best['method']}")
    print(f"Saved outputs to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
