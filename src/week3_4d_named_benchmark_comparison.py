"""Week 3 named 4D benchmark comparison using thresholded Ackley.

This module corrects the main Week 3 benchmark from a custom synthetic
function to a named analytic benchmark. The active-learning setup remains the
same as Week 2: deterministic oracle labels, a fixed pool, a fixed test set,
shared initial labels per seed, and the same five acquisition rules.

The model is still GaussianProcessRegressor on {-1, +1} labels. That is the
same plumbing stand-in used in Weeks 1 and 2, not the final GP classifier.
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
from matplotlib.lines import Line2D

from src.acquisition_rules import METHOD_DESCRIPTIONS, METHOD_ORDER, choose_next_index
from src.branin_week1 import fit_gp, random_two_class_initial_design


OUTPUT_DIR = (
    Path(__file__).resolve().parents[1]
    / "outputs"
    / "week3_4d_named_benchmark_comparison"
)
BENCHMARK_NAME = "thresholded_4d_ackley"
DOMAIN_LOWER = np.full(4, -5.0)
DOMAIN_UPPER = np.full(4, 5.0)
DOMAIN_WORDS = "[-5, 5]^4"
THRESHOLD_PERCENTILE = 50.0
THRESHOLD_SEED = 3027
THRESHOLD_SAMPLE_SIZE = 100_000
POOL_SIZE = 4_000
TEST_SIZE = 10_000
INITIAL_LABELLED_SIZE = 12
TOTAL_BUDGET = 80
SELECTED_BUDGETS = (INITIAL_LABELLED_SIZE, 40, TOTAL_BUDGET)
TOLERANCES = (0.28, 0.24, 0.20, 0.18, 0.17, 0.16, 0.15, 0.14, 0.13, 0.12)
SNAPSHOT_BUDGETS = SELECTED_BUDGETS


BENCHMARK_SELECTION_REASON = (
    "Thresholded 4D Ackley is a named deterministic analytic benchmark that can "
    "be evaluated exactly in four dimensions. After thresholding, it preserves "
    "the active level-set setting while being more defensible for Ioan's "
    "request to find or select 4D benchmarks than a custom-made function."
)

FUNCTION_DEFINITION_WORDS = (
    "Ackley in 4D: f(x) = -20 exp(-0.2 sqrt(mean_i x_i^2)) - "
    "exp(mean_i cos(2*pi*x_i)) + 20 + e. Labels are +1 when f(x) is at or "
    "above the fixed percentile threshold and -1 otherwise."
)

DOMAIN_SELECTION_NOTE = (
    "The script uses [-5,5]^4 rather than the very wide global-optimization "
    "domain [-32.768,32.768]^4. The narrower named Ackley domain keeps the "
    "central basin and threshold boundary visible with a finite pool and an "
    "80-query laptop-scale active-learning budget."
)

TOLERANCE_SELECTION_NOTE = (
    "Ackley on [-5,5]^4 is harder for the current GP-regression stand-in than "
    "the previous controlled synthetic benchmark. The table therefore includes "
    "Ackley-appropriate tolerances from 0.28 down to 0.16, while still retaining "
    "0.15, 0.14, 0.13, and 0.12 for comparison with the originally requested "
    "strict tolerances."
)

VISUAL_DIAGNOSTICS = [
    "dataset_value_distribution.png",
    "pairwise_label_projections_seed0.png",
    "exact_boundary_2d_slices.png",
    "query_locations_projection_seed0.png",
    "straddle_slice_snapshots_seed0.png",
    "randomized_straddle_slice_snapshots_seed0.png",
]


@dataclass
class Ackley4DDataset:
    """Pool and test data in both original and scaled coordinates."""

    seed: int
    threshold: float
    pool_original: np.ndarray
    pool_scaled: np.ndarray
    pool_values: np.ndarray
    pool_labels: np.ndarray
    test_original: np.ndarray
    test_scaled: np.ndarray
    test_values: np.ndarray
    test_labels: np.ndarray


@dataclass
class SeedDesign:
    """Shared data and starting labels for all methods in one seed."""

    seed: int
    dataset: Ackley4DDataset
    initial_indices: list[int]
    initial_resampling_attempts: int


@dataclass
class MethodRun:
    """One acquisition method on one fixed seed-specific 4D Ackley problem."""

    method: str
    seed: int
    dataset: Ackley4DDataset
    initial_indices: list[int]
    labelled_indices: list[int]
    budgets: list[int]
    error_history: list[float]
    acquisition_metadata: list[dict[str, float | int | str]]


def ackley_4d(X: np.ndarray) -> np.ndarray:
    """Evaluate the standard Ackley function for rows with four coordinates."""
    X = np.asarray(X, dtype=float)
    if X.ndim != 2 or X.shape[1] != 4:
        raise ValueError("Ackley benchmark expects an array with shape (n, 4)")
    a = 20.0
    b = 0.2
    c = 2.0 * np.pi
    mean_square = np.mean(X**2, axis=1)
    mean_cosine = np.mean(np.cos(c * X), axis=1)
    return -a * np.exp(-b * np.sqrt(mean_square)) - np.exp(mean_cosine) + a + np.e


def sample_domain(rng: np.random.Generator, size: int) -> np.ndarray:
    """Draw uniformly from the original Ackley domain."""
    return rng.uniform(DOMAIN_LOWER, DOMAIN_UPPER, size=(size, 4))


def scale_to_unit_hypercube(X_original: np.ndarray) -> np.ndarray:
    """Map the original Ackley domain to [0, 1]^4 for the GP model."""
    return (np.asarray(X_original) - DOMAIN_LOWER) / (DOMAIN_UPPER - DOMAIN_LOWER)


def unscale_from_unit_hypercube(X_scaled: np.ndarray) -> np.ndarray:
    """Map [0, 1]^4 model coordinates back to the original Ackley domain."""
    return DOMAIN_LOWER + np.asarray(X_scaled) * (DOMAIN_UPPER - DOMAIN_LOWER)


def threshold_sample_values(
    sample_size: int = THRESHOLD_SAMPLE_SIZE,
    seed: int = THRESHOLD_SEED,
) -> np.ndarray:
    """Evaluate a reproducible large sample for thresholding and diagnostics."""
    rng = np.random.default_rng(seed)
    return ackley_4d(sample_domain(rng, sample_size))


def compute_threshold(
    values: np.ndarray | None = None,
    percentile: float = THRESHOLD_PERCENTILE,
) -> float:
    """Compute the fixed percentile threshold."""
    if values is None:
        values = threshold_sample_values()
    return float(np.percentile(values, percentile))


def labels_from_values(values: np.ndarray, threshold: float) -> np.ndarray:
    """Return +1 at or above the threshold and -1 below it."""
    return np.where(np.asarray(values) >= threshold, 1.0, -1.0)


def make_dataset(
    seed: int,
    threshold: float,
    pool_size: int = POOL_SIZE,
    test_size: int = TEST_SIZE,
) -> Ackley4DDataset:
    """Create a reproducible pool and independent test set."""
    rng = np.random.default_rng(seed)
    pool_original = sample_domain(rng, pool_size)
    test_original = sample_domain(rng, test_size)
    pool_values = ackley_4d(pool_original)
    test_values = ackley_4d(test_original)
    return Ackley4DDataset(
        seed=seed,
        threshold=threshold,
        pool_original=pool_original,
        pool_scaled=scale_to_unit_hypercube(pool_original),
        pool_values=pool_values,
        pool_labels=labels_from_values(pool_values, threshold),
        test_original=test_original,
        test_scaled=scale_to_unit_hypercube(test_original),
        test_values=test_values,
        test_labels=labels_from_values(test_values, threshold),
    )


def rng_for_week3_named_method(seed: int, method: str) -> np.random.Generator:
    """Create a deterministic RNG tied to the Week 3 named benchmark."""
    digest = hashlib.sha256(f"{seed}:{method}:week3_4d_ackley".encode("utf-8")).digest()
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
    rng = np.random.default_rng(seed + 300_000)
    initial_indices, attempts = random_two_class_initial_design(
        dataset.pool_labels, initial_size, rng
    )
    return SeedDesign(seed, dataset, initial_indices, attempts)


def predict_error(gp, dataset: Ackley4DDataset) -> float:
    """Test-set misclassification error against exact threshold labels."""
    test_mean = gp.predict(dataset.test_scaled)
    prediction = np.where(test_mean >= 0.0, 1.0, -1.0)
    return float(np.mean(prediction != dataset.test_labels))


def run_method(design: SeedDesign, method: str, total_budget: int = TOTAL_BUDGET) -> MethodRun:
    """Run one acquisition method from the shared seed design."""
    dataset = design.dataset
    labelled = list(design.initial_indices)
    initial_copy = list(design.initial_indices)
    rng = rng_for_week3_named_method(design.seed, method)
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
            np.array_equal(run.dataset.pool_original, first.dataset.pool_original)
            and np.array_equal(run.dataset.pool_labels, first.dataset.pool_labels)
            for run in seed_runs
        )
        per_seed_test[str(seed)] = all(
            np.array_equal(run.dataset.test_original, first.dataset.test_original)
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


def tolerance_analysis_rows(
    runs_by_method: dict[str, list[MethodRun]],
    tolerances: tuple[float, ...] = TOLERANCES,
) -> list[dict[str, object]]:
    """Report tolerance reach budgets for each method and each tolerance."""
    rows: list[dict[str, object]] = []
    for tolerance in tolerances:
        for method in METHOD_ORDER:
            runs = sorted(runs_by_method[method], key=lambda run: run.seed)
            errors = method_errors(runs)
            mean_errors = errors.mean(axis=0)
            row: dict[str, object] = {
                "tolerance": tolerance,
                "method": method,
                "mean_curve_first_budget": first_budget_at_or_below(
                    runs[0].budgets, mean_errors, tolerance
                ),
            }
            for run in runs:
                row[f"seed_{run.seed}_first_budget"] = first_budget_at_or_below(
                    run.budgets,
                    np.asarray(run.error_history, dtype=float),
                    tolerance,
                )
            rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    """Write a list of dictionaries as a CSV file."""
    if not rows:
        raise ValueError(f"No rows to write for {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: ("null" if value is None else value)
                    for key, value in row.items()
                }
            )


def write_tolerance_markdown(path: Path, rows: list[dict[str, object]]) -> None:
    """Write tolerance reach rows as a readable Markdown table."""
    lines = [
        "# Week 3 Ackley Tolerance-Reach Table",
        "",
        "Budgets are the first labelled-evaluation counts where the error curve",
        "is at or below the listed test-label misclassification tolerance.",
        "`not reached` means the curve did not reach that tolerance by the final budget.",
        "",
        "| Tolerance | Method | Mean curve | Seed 0 | Seed 1 | Seed 2 | Seed 3 | Seed 4 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        def show(value: object) -> str:
            return "not reached" if value is None else str(value)

        lines.append(
            "| "
            + " | ".join(
                [
                    f"{float(row['tolerance']):.2f}",
                    str(row["method"]),
                    show(row["mean_curve_first_budget"]),
                    show(row.get("seed_0_first_budget")),
                    show(row.get("seed_1_first_budget")),
                    show(row.get("seed_2_first_budget")),
                    show(row.get("seed_3_first_budget")),
                    show(row.get("seed_4_first_budget")),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def class_balance(labels: np.ndarray) -> dict[str, float]:
    """Return class fractions for JSON summaries."""
    labels = np.asarray(labels)
    return {
        "negative_fraction": float(np.mean(labels == -1.0)),
        "positive_fraction": float(np.mean(labels == 1.0)),
    }


def plot_dataset_value_distribution(
    threshold_values: np.ndarray,
    threshold: float,
    output_path: Path,
) -> None:
    """Show the function-value distribution used to choose the threshold."""
    labels = labels_from_values(threshold_values, threshold)
    balance = class_balance(labels)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.hist(threshold_values, bins=70, color="#4c78a8", alpha=0.82, edgecolor="white")
    ax.axvline(threshold, color="#d55e00", linewidth=2.8, label=f"threshold = {threshold:.3f}")
    ax.set(
        title="4D Ackley value distribution used for thresholding",
        xlabel="Ackley function value",
        ylabel="Number of random domain points",
    )
    ax.text(
        0.98,
        0.95,
        (
            f"Threshold percentile: {THRESHOLD_PERCENTILE:.0f}%\n"
            f"-1 fraction: {balance['negative_fraction']:.3f}\n"
            f"+1 fraction: {balance['positive_fraction']:.3f}"
        ),
        transform=ax.transAxes,
        ha="right",
        va="top",
        bbox={"boxstyle": "round,pad=0.4", "facecolor": "white", "edgecolor": "#cccccc"},
    )
    ax.legend()
    ax.grid(alpha=0.20)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_pairwise_label_projections(dataset: Ackley4DDataset, output_path: Path) -> None:
    """Plot all six pairwise projections of seed-0 pool labels."""
    pairs = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    fig, axes = plt.subplots(2, 3, figsize=(14, 8.4), sharex=True, sharey=True)
    for ax, (i, j) in zip(axes.ravel(), pairs):
        ax.scatter(
            dataset.pool_original[:, i],
            dataset.pool_original[:, j],
            c=dataset.pool_labels,
            cmap="coolwarm",
            vmin=-1,
            vmax=1,
            s=9,
            alpha=0.42,
            linewidths=0,
        )
        ax.set_title(f"x{i} vs x{j}")
        ax.set_xlabel(f"x{i}")
        ax.set_ylabel(f"x{j}")
        ax.set_xlim(DOMAIN_LOWER[i], DOMAIN_UPPER[i])
        ax.set_ylim(DOMAIN_LOWER[j], DOMAIN_UPPER[j])
        ax.grid(alpha=0.15)

    balance = class_balance(dataset.pool_labels)
    fig.suptitle(
        (
            "Seed 0 pairwise projections of exact threshold labels "
            f"(-1={balance['negative_fraction']:.3f}, +1={balance['positive_fraction']:.3f})"
        ),
        fontsize=14,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def make_slice_grid(
    vary_dims: tuple[int, int],
    fixed_value: float,
    grid_size: int = 180,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Build a 2D original/scaled grid while fixing the other two dimensions."""
    a, b = vary_dims
    xs = np.linspace(DOMAIN_LOWER[a], DOMAIN_UPPER[a], grid_size)
    ys = np.linspace(DOMAIN_LOWER[b], DOMAIN_UPPER[b], grid_size)
    xx, yy = np.meshgrid(xs, ys)
    original = np.full((xx.size, 4), fixed_value, dtype=float)
    original[:, a] = xx.ravel()
    original[:, b] = yy.ravel()
    return xx, yy, original, scale_to_unit_hypercube(original)


def draw_exact_slice_background(
    ax,
    xx: np.ndarray,
    yy: np.ndarray,
    values: np.ndarray,
    threshold: float,
) -> None:
    """Draw exact threshold labels and contour on a 2D slice axis."""
    labels = np.where(values >= threshold, 1.0, -1.0)
    ax.contourf(
        xx,
        yy,
        labels.reshape(xx.shape),
        levels=[-1.5, 0.0, 1.5],
        colors=["#dbeafe", "#fee2e2"],
        alpha=0.70,
    )
    if float(values.min()) <= threshold <= float(values.max()):
        ax.contour(
            xx,
            yy,
            values.reshape(xx.shape),
            levels=[threshold],
            colors="black",
            linewidths=2.0,
        )
    else:
        ax.text(
            0.5,
            0.5,
            "no threshold crossing\nin this slice",
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=9,
            bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#cccccc"},
        )


def plot_exact_boundary_2d_slices(threshold: float, output_path: Path) -> None:
    """Show exact Ackley threshold regions on several 2D slices."""
    slice_specs = [
        ((0, 1), "vary x0,x1; fix x2,x3"),
        ((0, 2), "vary x0,x2; fix x1,x3"),
        ((1, 3), "vary x1,x3; fix x0,x2"),
    ]
    fixed_values = (0.0, 2.0)
    fig, axes = plt.subplots(len(slice_specs), len(fixed_values), figsize=(11, 13), sharex=False)
    for row, (vary_dims, label) in enumerate(slice_specs):
        for col, fixed_value in enumerate(fixed_values):
            ax = axes[row, col]
            xx, yy, original, _ = make_slice_grid(vary_dims, fixed_value)
            values = ackley_4d(original)
            draw_exact_slice_background(ax, xx, yy, values, threshold)
            ax.set_title(f"{label} at {fixed_value:g}")
            ax.set_xlabel(f"x{vary_dims[0]}")
            ax.set_ylabel(f"x{vary_dims[1]}")
            ax.set_xlim(DOMAIN_LOWER[vary_dims[0]], DOMAIN_UPPER[vary_dims[0]])
            ax.set_ylim(DOMAIN_LOWER[vary_dims[1]], DOMAIN_UPPER[vary_dims[1]])
            ax.grid(alpha=0.15)

    fig.suptitle("Exact 2D slices of the thresholded 4D Ackley boundary", fontsize=14)
    fig.legend(
        handles=[
            Line2D([0], [0], color="black", lw=2.0, label="exact f(x)=threshold"),
            Line2D([0], [0], marker="s", color="#dbeafe", lw=0, label="-1 region"),
            Line2D([0], [0], marker="s", color="#fee2e2", lw=0, label="+1 region"),
        ],
        loc="lower center",
        ncol=3,
        frameon=False,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_query_locations_projection_seed0(
    runs_by_method: dict[str, list[MethodRun]],
    output_path: Path,
) -> None:
    """Show seed-0 query locations in an x0-vs-x1 projection."""
    seed0_runs = {method: next(run for run in runs_by_method[method] if run.seed == 0) for method in METHOD_ORDER}
    fig, axes = plt.subplots(1, len(METHOD_ORDER), figsize=(20, 5.0), sharex=True, sharey=True)
    scatter = None
    for ax, method in zip(axes, METHOD_ORDER):
        run = seed0_runs[method]
        initial = np.asarray(run.initial_indices, dtype=int)
        acquired = np.asarray(run.labelled_indices[len(initial) :], dtype=int)
        ax.scatter(
            run.dataset.pool_original[:, 0],
            run.dataset.pool_original[:, 1],
            c=run.dataset.pool_labels,
            cmap="coolwarm",
            vmin=-1,
            vmax=1,
            s=5,
            alpha=0.12,
            linewidths=0,
        )
        if len(acquired):
            order = np.arange(1, len(acquired) + 1)
            scatter = ax.scatter(
                run.dataset.pool_original[acquired, 0],
                run.dataset.pool_original[acquired, 1],
                c=order,
                cmap="viridis",
                s=28,
                alpha=0.88,
                linewidths=0,
            )
        ax.scatter(
            run.dataset.pool_original[initial, 0],
            run.dataset.pool_original[initial, 1],
            marker="*",
            s=115,
            c="white",
            edgecolors="black",
            linewidths=1.1,
            zorder=3,
        )
        ax.set_title(method.replace("_", "\n"), fontsize=10)
        ax.set_xlabel("x0")
        ax.set_xlim(DOMAIN_LOWER[0], DOMAIN_UPPER[0])
        ax.set_ylim(DOMAIN_LOWER[1], DOMAIN_UPPER[1])
        ax.grid(alpha=0.15)
    axes[0].set_ylabel("x1")
    fig.suptitle("Seed 0 query locations projected to x0 vs x1", fontsize=14)
    fig.legend(
        handles=[
            Line2D([0], [0], marker="*", color="white", markeredgecolor="black", lw=0, label="shared initial 12"),
            Line2D([0], [0], marker="o", color="#999999", lw=0, label="faint exact pool-label projection"),
        ],
        loc="lower center",
        ncol=2,
        frameon=False,
    )
    if scatter is not None:
        cbar_ax = fig.add_axes([0.905, 0.27, 0.012, 0.46])
        cbar = fig.colorbar(scatter, cax=cbar_ax)
        cbar.set_label("Acquisition order after initial design")
    fig.subplots_adjust(bottom=0.22, top=0.78, right=0.88, wspace=0.16)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_method_slice_snapshots(run: MethodRun, output_path: Path) -> None:
    """Plot GP boundary snapshots on a fixed x0-vs-x1 slice."""
    vary_dims = (0, 1)
    fixed_value = 0.0
    xx, yy, original, scaled = make_slice_grid(vary_dims, fixed_value, grid_size=170)
    exact_values = ackley_4d(original)
    budgets = list(SNAPSHOT_BUDGETS)
    fig, axes = plt.subplots(1, len(budgets), figsize=(17, 5.4), sharex=True, sharey=True)
    for ax, budget in zip(axes, budgets):
        labelled = run.labelled_indices[:budget]
        gp = fit_gp(run.dataset.pool_scaled[labelled], run.dataset.pool_labels[labelled], run.seed)
        mean = gp.predict(scaled)
        draw_exact_slice_background(ax, xx, yy, exact_values, run.dataset.threshold)
        if float(mean.min()) <= 0.0 <= float(mean.max()):
            ax.contour(
                xx,
                yy,
                mean.reshape(xx.shape),
                levels=[0.0],
                colors="#6a3d9a",
                linewidths=2.2,
                linestyles="-",
            )
        else:
            ax.text(
                0.02,
                0.05,
                "GP mu=0 not in slice",
                transform=ax.transAxes,
                fontsize=9,
                bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#cccccc"},
            )
        labelled_array = np.asarray(labelled, dtype=int)
        ax.scatter(
            run.dataset.pool_original[labelled_array, 0],
            run.dataset.pool_original[labelled_array, 1],
            c=run.dataset.pool_labels[labelled_array],
            cmap="coolwarm",
            vmin=-1,
            vmax=1,
            edgecolors="white",
            linewidths=0.7,
            s=38,
            alpha=0.92,
            zorder=3,
        )
        error = run.error_history[run.budgets.index(budget)]
        ax.set_title(f"n={budget}; test error={error:.3f}")
        ax.set_xlabel("x0")
        ax.set_xlim(DOMAIN_LOWER[0], DOMAIN_UPPER[0])
        ax.set_ylim(DOMAIN_LOWER[1], DOMAIN_UPPER[1])
        ax.grid(alpha=0.15)
    axes[0].set_ylabel("x1")
    fig.suptitle(
        f"{run.method} on x0-vs-x1 slice with x2=x3={fixed_value:g} (seed {run.seed})",
        fontsize=14,
    )
    fig.legend(
        handles=[
            Line2D([0], [0], color="black", lw=2.0, label="exact Ackley threshold"),
            Line2D([0], [0], color="#6a3d9a", lw=2.2, label="GP believed boundary mu=0"),
        ],
        loc="lower center",
        ncol=2,
        frameon=False,
    )
    fig.tight_layout(rect=(0, 0.12, 1, 0.86))
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


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
        title="Week 3 thresholded 4D Ackley acquisition comparison",
        xlabel="Labelled Ackley oracle evaluations",
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
        title=f"Mean final thresholded-Ackley test error at budget {TOTAL_BUDGET}",
        ylabel="Mean final error (+/- 1 std)",
        ylim=(0.0, max(means) + max(stds) + 0.04),
    )
    ax.grid(axis="y", alpha=0.25)
    for pos, mean in zip(positions, means):
        ax.text(pos, mean + 0.008, f"{100 * mean:.1f}%", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_slide_notes(
    summary_rows: list[dict[str, str]],
    best_method: str,
    tolerance_rows: list[dict[str, object]],
    output_path: Path,
) -> None:
    """Write beginner-friendly notes for Google Slides."""
    best_row = next(row for row in summary_rows if row["method"] == best_method)
    tolerance_text_lines = []
    for tolerance in TOLERANCES:
        tol_rows = [row for row in tolerance_rows if row["tolerance"] == tolerance]
        reached = [
            f"{row['method']} at n={row['mean_curve_first_budget']}"
            for row in tol_rows
            if row["mean_curve_first_budget"] is not None
        ]
        if reached:
            tolerance_text_lines.append(
                f"- {tolerance:.2f}: " + "; ".join(reached) + "."
            )
        else:
            tolerance_text_lines.append(f"- {tolerance:.2f}: no mean curve reached it.")
    tolerance_text = "\n".join(tolerance_text_lines)

    text = f"""# Week 3 Slide Notes: Thresholded 4D Ackley

## Why change the Week 3 benchmark

The earlier controlled 4D boundary was useful for software plumbing, but it was
custom-made. Ioan asked for new 4D datasets or benchmarks, so the main Week 3
result now uses a named analytic benchmark: thresholded 4D Ackley.

## Why Ackley

Ackley is deterministic, four-dimensional, nonlinear, and standard enough to
defend in a meeting. After thresholding the continuous function, every pool and
test point has an exact label. This keeps the active level-set setting while
moving beyond 2D Branin.

The domain is `{DOMAIN_WORDS}`. The GP receives scaled coordinates in
`[0,1]^4`, but plots use the original Ackley coordinates. The threshold is the
{THRESHOLD_PERCENTILE:.0f}th percentile of a reproducible random domain sample.

## How to understand a 4D boundary

We cannot draw the full boundary in one plot. Instead, the output folder
contains a value histogram, pairwise label projections, exact 2D slices, query
location projections, and model slice snapshots. These are diagnostic views,
not complete pictures of the 4D boundary.

## Fair comparison

For each seed, all five acquisition rules use the same threshold, pool, test
set, initial labelled points, GP-regression stand-in, and budget. Only the
acquisition rule changes.

## Main result

By mean final test-label misclassification error, the best method is
`{best_method}` with mean final error `{float(best_row['mean_final_error']):.3f}`
at budget {TOTAL_BUDGET}.

Tolerance reach summary for the mean curves:

{tolerance_text}

## Caveats

This is still a first named 4D synthetic benchmark. The GP regressor is still a
stand-in, not the final GP classifier. The metric is test-label
misclassification error, not a geometric boundary-distance metric. The result
is preliminary and should be discussed with Ioan before treating it as a final
thesis direction.

## Suggested next step for Ioan

Show Ioan the Ackley diagnostics first, then the acquisition curves. Ask whether
he agrees that thresholded 4D Ackley is a reasonable named benchmark bridge, and
whether the next step should add thresholded 4D Rosenbrock/Rastrigin or move
toward the real laser data.
"""
    output_path.write_text(text, encoding="utf-8")


def save_summary(
    runs_by_method: dict[str, list[MethodRun]],
    designs: list[SeedDesign],
    output_path: Path,
    threshold_values: np.ndarray,
    threshold: float,
    tolerance_rows: list[dict[str, object]],
) -> tuple[list[dict[str, str]], str]:
    """Save the requested JSON summary and return table rows plus winner."""
    fairness = verify_fairness(runs_by_method)
    if not fairness["all_checks_passed"]:
        raise RuntimeError(f"Fairness check failed: {fairness}")

    summary_rows = method_summary_rows(runs_by_method)
    best_method = min(summary_rows, key=lambda row: float(row["mean_final_error"]))["method"]

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

    threshold_labels = labels_from_values(threshold_values, threshold)
    summary = {
        "experiment": "week3_4d_named_benchmark_comparison",
        "benchmark_name": BENCHMARK_NAME,
        "why_this_benchmark_was_selected": BENCHMARK_SELECTION_REASON,
        "function_definition_words": FUNCTION_DEFINITION_WORDS,
        "domain": DOMAIN_WORDS,
        "domain_selection_note": DOMAIN_SELECTION_NOTE,
        "scaling_rule": "Original Ackley inputs are linearly scaled to [0,1]^4 for the GP.",
        "threshold": threshold,
        "threshold_percentile": THRESHOLD_PERCENTILE,
        "threshold_rule": (
            "Fixed once as the percentile over a reproducible uniform sample from the Ackley domain."
        ),
        "threshold_estimation_seed": THRESHOLD_SEED,
        "threshold_estimation_sample_size": THRESHOLD_SAMPLE_SIZE,
        "threshold_sample_class_balance": class_balance(threshold_labels),
        "pool_size_per_seed": POOL_SIZE,
        "test_size_per_seed": TEST_SIZE,
        "seeds": [design.seed for design in designs],
        "initial_labelled_size": INITIAL_LABELLED_SIZE,
        "total_budget": TOTAL_BUDGET,
        "acquisition_rules": list(METHOD_ORDER),
        "selected_budget_table_budgets": list(SELECTED_BUDGETS),
        "gp_model_note": (
            "GaussianProcessRegressor on {-1,+1} labels is still a stand-in, "
            "not the final GP classifier."
        ),
        "error_definition": "fraction of exact threshold test labels predicted incorrectly",
        "prediction_rule": "+1 if GP latent mean mu >= 0, else -1",
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
        "richer_tolerance_analysis": {
            "metric": "fraction of exact thresholded-Ackley test labels misclassified",
            "tolerances": list(TOLERANCES),
            "tolerance_selection_note": TOLERANCE_SELECTION_NOTE,
            "rows": tolerance_rows,
            "note": (
                "Budgets are first labelled-evaluation counts where the mean "
                "curve or per-seed curve is at or below the listed tolerance. "
                "Null means not reached by the final budget."
            ),
        },
        "best_final_method_by_mean_final_error": best_method,
        "generated_visual_diagnostics": VISUAL_DIAGNOSTICS,
        "generated_tables": [
            "method_summary_table.csv",
            "selected_budget_table.csv",
            "tolerance_reach_table.csv",
            "tolerance_reach_table.md",
        ],
        "runtime_settings_note": (
            "The run uses 5 seeds, pool size 4000, test size 10000, initial "
            "labelled size 12, and total budget 80 to keep runtime reasonable "
            "on a laptop while staying larger than the 2D Branin setup."
        ),
        "caveats": [
            "This is a first named 4D synthetic benchmark.",
            "The GP regressor is still a stand-in, not the final GP classifier.",
            "The metric is test-label misclassification error, not a geometric boundary-distance metric.",
            "2D projections and slices are diagnostics; they do not show the full 4D boundary.",
            "The result is preliminary and should be discussed with Ioan before treating it as a final thesis direction.",
        ],
        "per_method": per_method,
    }
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary_rows, best_method


def run_experiment(
    seeds: tuple[int, ...] = (0, 1, 2, 3, 4),
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, list[MethodRun]]:
    """Run Week 3 named Ackley benchmark and save all requested artifacts."""
    threshold_values = threshold_sample_values()
    threshold = compute_threshold(threshold_values)
    designs = [create_seed_design(seed, threshold) for seed in seeds]

    runs_by_method: dict[str, list[MethodRun]] = {method: [] for method in METHOD_ORDER}
    for design in designs:
        for method in METHOD_ORDER:
            runs_by_method[method].append(run_method(design, method))

    output_dir.mkdir(parents=True, exist_ok=True)
    plot_dataset_value_distribution(
        threshold_values,
        threshold,
        output_dir / "dataset_value_distribution.png",
    )
    plot_pairwise_label_projections(
        designs[0].dataset,
        output_dir / "pairwise_label_projections_seed0.png",
    )
    plot_exact_boundary_2d_slices(
        threshold,
        output_dir / "exact_boundary_2d_slices.png",
    )
    plot_query_locations_projection_seed0(
        runs_by_method,
        output_dir / "query_locations_projection_seed0.png",
    )

    seed0_straddle = next(run for run in runs_by_method["straddle"] if run.seed == 0)
    seed0_randomized = next(
        run for run in runs_by_method["randomized_straddle"] if run.seed == 0
    )
    plot_method_slice_snapshots(
        seed0_straddle,
        output_dir / "straddle_slice_snapshots_seed0.png",
    )
    plot_method_slice_snapshots(
        seed0_randomized,
        output_dir / "randomized_straddle_slice_snapshots_seed0.png",
    )
    plot_error_curves_all_methods(runs_by_method, output_dir / "error_curves_all_methods.png")
    plot_final_error_bar_chart(runs_by_method, output_dir / "final_error_bar_chart.png")

    selected_rows = selected_budget_rows(runs_by_method)
    write_csv(output_dir / "selected_budget_table.csv", selected_rows)
    tolerance_rows = tolerance_analysis_rows(runs_by_method)
    write_csv(output_dir / "tolerance_reach_table.csv", tolerance_rows)
    write_tolerance_markdown(output_dir / "tolerance_reach_table.md", tolerance_rows)
    summary_rows, best_method = save_summary(
        runs_by_method,
        designs,
        output_dir / "summary.json",
        threshold_values,
        threshold,
        tolerance_rows,
    )
    write_csv(output_dir / "method_summary_table.csv", summary_rows)
    save_slide_notes(
        summary_rows,
        best_method,
        tolerance_rows,
        output_dir / "week3_slide_notes.md",
    )
    return runs_by_method


def main() -> None:
    runs_by_method = run_experiment()
    rows = method_summary_rows(runs_by_method)
    best = min(rows, key=lambda row: float(row["mean_final_error"]))
    print("Week 3 thresholded 4D Ackley comparison complete.")
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
