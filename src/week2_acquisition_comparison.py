"""Week 2 acquisition-rule comparison on thresholded Branin.

The loop, data, GP regressor, initial labelled points, and test sets are held
fixed within each seed. Only the acquisition rule changes.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from src.acquisition_rules import (
    METHOD_DESCRIPTIONS,
    METHOD_ORDER,
    choose_next_index,
    rng_for_method,
)
from src.branin_week1 import (
    DOMAIN_LOWER,
    DOMAIN_UPPER,
    BraninDataset,
    branin,
    compute_threshold,
    fit_gp,
    make_dataset,
    make_plot_grid,
    random_two_class_initial_design,
)


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs" / "week2_acquisition_comparison"
SNAPSHOT_BUDGETS = (6, 20, 50)
ERROR_TOLERANCE = 0.08


@dataclass
class MethodRun:
    """One method on one fixed seed-specific Branin problem."""

    method: str
    seed: int
    dataset: BraninDataset
    initial_indices: list[int]
    labelled_indices: list[int]
    budgets: list[int]
    error_history: list[float]
    acquisition_metadata: list[dict[str, float | int | str]]
    snapshots: dict[int, dict[str, np.ndarray]]


@dataclass
class SeedDesign:
    """Shared data and starting labels for all methods in one seed."""

    seed: int
    dataset: BraninDataset
    initial_indices: list[int]
    initial_resampling_attempts: int


def create_seed_design(
    seed: int,
    threshold: float,
    initial_size: int = 6,
    pool_size: int = 1_500,
    test_size: int = 4_000,
) -> SeedDesign:
    """Generate one dataset and one shared initial design for a seed."""
    dataset = make_dataset(seed, threshold, pool_size, test_size)
    rng = np.random.default_rng(seed + 100_000)
    initial_indices, attempts = random_two_class_initial_design(
        dataset.pool_labels, initial_size, rng
    )
    return SeedDesign(seed, dataset, initial_indices, attempts)


def predict_error(gp, dataset: BraninDataset) -> float:
    """Test-set misclassification error against exact thresholded labels."""
    test_mean = gp.predict(dataset.test_scaled)
    prediction = np.where(test_mean >= 0.0, 1.0, -1.0)
    return float(np.mean(prediction != dataset.test_labels))


def run_method(
    design: SeedDesign,
    method: str,
    total_budget: int = 50,
    snapshot_budgets: tuple[int, ...] = SNAPSHOT_BUDGETS,
) -> MethodRun:
    """Run one acquisition method from the shared seed design."""
    dataset = design.dataset
    labelled = list(design.initial_indices)
    initial_copy = list(design.initial_indices)
    rng = rng_for_method(design.seed, method)

    _, _, _, plot_grid_scaled = make_plot_grid()
    budgets: list[int] = []
    errors: list[float] = []
    metadata: list[dict[str, float | int | str]] = []
    snapshots: dict[int, dict[str, np.ndarray]] = {}

    while True:
        gp = fit_gp(dataset.pool_scaled[labelled], dataset.pool_labels[labelled], design.seed)
        budgets.append(len(labelled))
        errors.append(predict_error(gp, dataset))

        if len(labelled) in snapshot_budgets:
            grid_mean, grid_std = gp.predict(plot_grid_scaled, return_std=True)
            snapshots[len(labelled)] = {
                "mean": grid_mean,
                "std": grid_std,
                "labelled_indices": np.asarray(labelled, dtype=int),
            }

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
        snapshots=snapshots,
    )


def verify_fairness(runs_by_method: dict[str, list[MethodRun]]) -> dict[str, bool]:
    """Check that all methods share the same starting point within each seed."""
    checks: dict[str, bool] = {}
    seeds = sorted({run.seed for runs in runs_by_method.values() for run in runs})
    for seed in seeds:
        initial_sets = [
            tuple(run.initial_indices)
            for runs in runs_by_method.values()
            for run in runs
            if run.seed == seed
        ]
        checks[str(seed)] = all(indices == initial_sets[0] for indices in initial_sets)
    return checks


def method_errors(runs: list[MethodRun]) -> np.ndarray:
    """Stack error histories for one method."""
    return np.asarray([run.error_history for run in runs], dtype=float)


def selected_budget_rows(
    runs_by_method: dict[str, list[MethodRun]],
    budgets: tuple[int, ...] = SNAPSHOT_BUDGETS,
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
        "metric": "fraction of exact Branin test labels misclassified",
        "tolerance": tolerance,
        "note": (
            "This is a test-error tolerance proxy for Ioan's fixed-tolerance "
            "DONE WHEN note, not a separate geometric contour-distance metric."
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
    for method in METHOD_ORDER:
        runs = runs_by_method[method]
        budgets = np.asarray(runs[0].budgets)
        errors = method_errors(runs)
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
        title="Week 2 Branin acquisition comparison",
        xlabel="Labelled Branin evaluations",
        ylabel="Fraction of 4,000 test points mislabelled",
        xlim=(6, 50),
        ylim=(0.0, 0.45),
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
    """Bar chart of mean final error at budget 50."""
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
        ["random", "smallest\n|mu|", "straddle", "randomized\nstraddle", "expected\nfeasibility"],
        fontsize=10,
    )
    ax.set(
        title="Mean final Branin test error at budget 50",
        ylabel="Mean final error (+/- 1 std)",
        ylim=(0.0, max(means) + max(stds) + 0.04),
    )
    ax.grid(axis="y", alpha=0.25)
    for pos, mean in zip(positions, means):
        ax.text(pos, mean + 0.008, f"{100*mean:.1f}%", ha="center", va="bottom", fontsize=10)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_query_locations_seed0(
    runs_by_method: dict[str, list[MethodRun]],
    output_path: Path,
) -> None:
    """Show where each method queried on seed 0."""
    seed0_runs = {method: runs_by_method[method][0] for method in METHOD_ORDER}
    xx, yy, grid_original, _ = make_plot_grid(size=240)
    values = branin(grid_original).reshape(xx.shape)

    fig, axes = plt.subplots(1, len(METHOD_ORDER), figsize=(20, 5.2), sharex=True, sharey=True)
    scatter = None
    for ax, method in zip(axes, METHOD_ORDER):
        run = seed0_runs[method]
        initial = np.asarray(run.initial_indices, dtype=int)
        acquired = np.asarray(run.labelled_indices[len(initial) :], dtype=int)
        ax.contourf(
            xx,
            yy,
            np.where(values >= run.dataset.threshold, 1.0, -1.0),
            levels=[-1.5, 0.0, 1.5],
            colors=["#dbeafe", "#fee2e2"],
            alpha=0.65,
        )
        ax.contour(
            xx,
            yy,
            values,
            levels=[run.dataset.threshold],
            colors="black",
            linewidths=2.0,
        )
        if len(acquired):
            order = np.arange(1, len(acquired) + 1)
            scatter = ax.scatter(
                run.dataset.pool_original[acquired, 0],
                run.dataset.pool_original[acquired, 1],
                c=order,
                cmap="viridis",
                s=26,
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
        ax.set_xlim(DOMAIN_LOWER[0], DOMAIN_UPPER[0])
        ax.set_ylim(DOMAIN_LOWER[1], DOMAIN_UPPER[1])
        ax.set_xlabel("x1")
    axes[0].set_ylabel("x2")
    legend = [
        Line2D([0], [0], color="black", lw=2.0, label="Exact Branin boundary"),
        Line2D([0], [0], marker="*", color="white", markeredgecolor="black", lw=0, label="Shared initial 6"),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=2, frameon=False)
    if scatter is not None:
        cbar_ax = fig.add_axes([0.905, 0.27, 0.012, 0.48])
        cbar = fig.colorbar(scatter, cax=cbar_ax)
        cbar.set_label("Acquisition order after initial design")
    fig.suptitle("Seed 0 query locations by acquisition rule", fontsize=15)
    fig.subplots_adjust(bottom=0.22, top=0.80, right=0.88, wspace=0.16)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_method_snapshots(run: MethodRun, output_path: Path) -> None:
    """Plot n=6, n=20, and n=50 snapshots for one method."""
    xx, yy, grid_original, _ = make_plot_grid()
    values = branin(grid_original).reshape(xx.shape)
    budgets = sorted(run.snapshots)
    fig, axes = plt.subplots(1, len(budgets), figsize=(17, 5.4), sharex=True, sharey=True)
    for ax, budget in zip(axes, budgets):
        snapshot = run.snapshots[budget]
        mean = snapshot["mean"].reshape(xx.shape)
        indices = snapshot["labelled_indices"].astype(int)
        image = ax.contourf(
            xx,
            yy,
            mean,
            levels=np.linspace(-1.2, 1.2, 25),
            cmap="coolwarm",
            vmin=-1.2,
            vmax=1.2,
            extend="both",
        )
        ax.contour(xx, yy, mean, levels=[0.0], colors="black", linewidths=2.2)
        ax.contour(
            xx,
            yy,
            values,
            levels=[run.dataset.threshold],
            colors="#f4e04d",
            linestyles="--",
            linewidths=2.2,
        )
        ax.scatter(
            run.dataset.pool_original[indices, 0],
            run.dataset.pool_original[indices, 1],
            c=run.dataset.pool_labels[indices],
            cmap="coolwarm",
            vmin=-1,
            vmax=1,
            edgecolors="white",
            linewidths=0.7,
            s=38,
        )
        error = run.error_history[run.budgets.index(budget)]
        ax.set_title(f"n={budget}; error={error:.3f}")
        ax.set_xlabel("x1")
    axes[0].set_ylabel("x2")
    fig.suptitle(f"{run.method} snapshots on seed {run.seed}", fontsize=15)
    fig.legend(
        handles=[
            Line2D([0], [0], color="black", lw=2.2, label="GP boundary: mu=0"),
            Line2D([0], [0], color="#f4e04d", lw=2.2, ls="--", label="Exact boundary"),
        ],
        loc="lower center",
        ncol=2,
        frameon=False,
    )
    fig.subplots_adjust(bottom=0.20, top=0.82, right=0.88, wspace=0.14)
    cbar_ax = fig.add_axes([0.91, 0.24, 0.015, 0.52])
    fig.colorbar(image, cax=cbar_ax, label="GP latent mean mu(x)")
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


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
            tolerance_lines.append(f"- {method}: did not reach {100*tolerance:.0f}% mean test error.")
        else:
            tolerance_lines.append(f"- {method}: reached {100*tolerance:.0f}% mean test error at n={budget}.")
    tolerance_text = "\n".join(tolerance_lines)
    text = f"""# Week 2 Slide Notes

## What Week 2 tests

Week 2 keeps the Week 1 Branin active-learning loop fixed and changes only the
acquisition rule. The question is: if the same GP, same pool, same test set,
same initial labels, and same budget are used, which rule chooses the most useful
next labels?

## Why only the acquisition changes

Ioan's instruction is to make the comparison fair. For each seed, all five
methods start from the exact same six labelled Branin points and evaluate on the
same 4,000-point test set. Any difference in the error curves should therefore
come from the rule used to choose the next point.

## The five rules in plain English

- Random: choose any unlabelled point uniformly at random. This is the floor
  baseline.
- Smallest |mu|: choose the point closest to the current GP boundary. This is
  the Week 1 rule and a noiseless label-uncertainty stand-in.
- Straddle: choose points that are both close to the boundary and uncertain,
  using 1.96*sigma - |mu|.
- Randomized straddle: same idea as straddle, but the uncertainty weight changes
  each step using one reproducible chi-square random draw.
- Expected feasibility: a contour-focused expected-improvement-style heuristic.
  It scores points by how plausible it is that the latent GP value lies near the
  zero contour.

## How to read the error curves

The y-axis is the fraction of 4,000 independent Branin test points whose exact
threshold label is predicted incorrectly. Lower is better. The curve can move
up at individual steps because refitting the GP moves the whole boundary.
Compare the overall trend and the final error at budget 50.

## Which method performed best

By mean final error over the seeds, the best method in this run is
`{best_method}` with mean final error `{float(best_row['mean_final_error']):.3f}`.

Using a fixed {100*tolerance:.0f}% test-error tolerance as a lightweight proxy
for the brief's tolerance check:

{tolerance_text}

## Caveats

The GP regressor on -1/+1 labels is still a stand-in. The final thesis method
should use a proper GP classifier or a more suitable surrogate. Smallest |mu|,
straddle, randomized straddle, and expected feasibility are heuristic rules in
this plumbing stage. The tolerance check above is based on test
misclassification error, not a separate geometric contour-distance metric.

## Suggested next step

Discuss with Ioan whether the current Branin comparison is enough for Week 2 or
whether the same comparison should be repeated over more initial designs, larger
budgets, or a controlled boundary-width sweep.
"""
    output_path.write_text(text, encoding="utf-8")


def save_summary(
    runs_by_method: dict[str, list[MethodRun]],
    designs: list[SeedDesign],
    output_path: Path,
    threshold_seed: int,
    threshold_sample_size: int,
) -> tuple[list[dict[str, str]], str, dict[str, object]]:
    """Save the requested JSON summary and return table rows plus winner."""
    fairness = verify_fairness(runs_by_method)
    if not all(fairness.values()):
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
        "experiment": "week2_acquisition_comparison_thresholded_branin",
        "source_brief": "Ioan Week 2: hold the loop fixed and change only how the next point is chosen.",
        "threshold": designs[0].dataset.threshold,
        "threshold_percentile": 45.0,
        "threshold_estimation_seed": threshold_seed,
        "threshold_estimation_sample_size": threshold_sample_size,
        "domain": {"x1": [-5.0, 10.0], "x2": [0.0, 15.0]},
        "pool_size_per_seed": len(designs[0].dataset.pool_labels),
        "test_size_per_seed": len(designs[0].dataset.test_labels),
        "seeds": [design.seed for design in designs],
        "acquisition_rules": list(METHOD_ORDER),
        "initial_labelled_size": 6,
        "total_budget": 50,
        "gp_model_note": (
            "GaussianProcessRegressor on {-1,+1} labels is a Week 2 stand-in, "
            "not the final GP classifier."
        ),
        "fairness_note": (
            "For each seed, all acquisition rules use the same Branin threshold, "
            "pool, test set, GP regressor, budget, and initial labelled indices. "
            "Only the acquisition rule changes."
        ),
        "fairness_checks_same_initial_indices_per_seed": fairness,
        "initial_indices_by_seed": {
            str(design.seed): design.initial_indices for design in designs
        },
        "initial_resampling_attempts_by_seed": {
            str(design.seed): design.initial_resampling_attempts for design in designs
        },
        "method_summary": summary_rows,
        "fixed_error_tolerance_check": tolerance_check,
        "best_final_method_by_mean_final_error": best_method,
        "per_method": per_method,
    }
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary_rows, best_method, tolerance_check


def run_experiment(
    seeds: tuple[int, ...] = (0, 1, 2, 3, 4),
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, list[MethodRun]]:
    """Run Week 2 and save all requested artifacts."""
    threshold_seed = 2026
    threshold_sample_size = 20_000
    threshold = compute_threshold(threshold_sample_size, threshold_seed)
    designs = [create_seed_design(seed, threshold) for seed in seeds]

    runs_by_method: dict[str, list[MethodRun]] = {method: [] for method in METHOD_ORDER}
    for design in designs:
        for method in METHOD_ORDER:
            runs_by_method[method].append(run_method(design, method))

    output_dir.mkdir(parents=True, exist_ok=True)
    plot_error_curves_all_methods(runs_by_method, output_dir / "error_curves_all_methods.png")
    plot_final_error_bar_chart(runs_by_method, output_dir / "final_error_bar_chart.png")
    plot_query_locations_seed0(runs_by_method, output_dir / "query_locations_seed0.png")

    selected_rows = selected_budget_rows(runs_by_method)
    write_csv(output_dir / "selected_budget_table.csv", selected_rows)
    summary_rows, best_method, tolerance_check = save_summary(
        runs_by_method,
        designs,
        output_dir / "summary.json",
        threshold_seed,
        threshold_sample_size,
    )
    write_csv(output_dir / "method_summary_table.csv", summary_rows)
    save_slide_notes(
        summary_rows,
        best_method,
        tolerance_check,
        output_dir / "week2_slide_notes.md",
    )

    seed0_best = next(run for run in runs_by_method[best_method] if run.seed == 0)
    seed0_straddle = next(run for run in runs_by_method["straddle"] if run.seed == 0)
    plot_method_snapshots(
        seed0_best,
        output_dir / f"snapshots_best_{best_method}_seed0.png",
    )
    plot_method_snapshots(
        seed0_straddle,
        output_dir / "snapshots_straddle_seed0.png",
    )
    return runs_by_method


def main() -> None:
    runs_by_method = run_experiment()
    rows = method_summary_rows(runs_by_method)
    best = min(rows, key=lambda row: float(row["mean_final_error"]))
    print("Week 2 acquisition comparison complete.")
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
