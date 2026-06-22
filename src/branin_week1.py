"""Week 1 thresholded-Branin active level-set estimation experiment.

This module deliberately uses a GaussianProcessRegressor on labels in {-1, +1}.
It is the simple Week 1 plumbing model from the working brief, not the final GP
classifier planned for the thesis.
"""

from __future__ import annotations

from email.mime import image
import json
import warnings
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, RBF, WhiteKernel


DOMAIN_LOWER = np.array([-5.0, 0.0])
DOMAIN_UPPER = np.array([10.0, 15.0])


@dataclass
class BraninDataset:
    """Pool and test data in both physical and model coordinates."""

    seed: int
    threshold: float
    pool_original: np.ndarray
    pool_scaled: np.ndarray
    pool_labels: np.ndarray
    test_original: np.ndarray
    test_scaled: np.ndarray
    test_labels: np.ndarray


@dataclass
class BraninRun:
    """Results from one active-learning seed."""

    seed: int
    dataset: BraninDataset
    labelled_indices: list[int]
    initial_resampling_attempts: int
    budgets: list[int]
    error_history: list[float]
    snapshots: dict[int, dict[str, np.ndarray]]


def branin(X: np.ndarray) -> np.ndarray:
    """Evaluate the standard Branin function at rows [x1, x2]."""
    X = np.asarray(X, dtype=float)
    x1, x2 = X[:, 0], X[:, 1]
    a = 1.0
    b = 5.1 / (4.0 * np.pi**2)
    c = 5.0 / np.pi
    r = 6.0
    s = 10.0
    t = 1.0 / (8.0 * np.pi)
    return a * (x2 - b * x1**2 + c * x1 - r) ** 2 + s * (1.0 - t) * np.cos(x1) + s


def scale_to_unit_square(X: np.ndarray) -> np.ndarray:
    """Map the fixed Branin domain to [0, 1]^2."""
    return (np.asarray(X) - DOMAIN_LOWER) / (DOMAIN_UPPER - DOMAIN_LOWER)


def sample_domain(rng: np.random.Generator, size: int) -> np.ndarray:
    """Draw uniformly from the physical Branin domain."""
    return rng.uniform(DOMAIN_LOWER, DOMAIN_UPPER, size=(size, 2))


def compute_threshold(sample_size: int = 20_000, seed: int = 2026) -> float:
    """Estimate the fixed 45th-percentile threshold reproducibly."""
    rng = np.random.default_rng(seed)
    points = sample_domain(rng, sample_size)
    return float(np.percentile(branin(points), 45.0))


def labels_from_threshold(X_original: np.ndarray, threshold: float) -> np.ndarray:
    """Return +1 at or above the threshold and -1 below it."""
    return np.where(branin(X_original) >= threshold, 1.0, -1.0)


def make_dataset(
    seed: int,
    threshold: float,
    pool_size: int = 1_500,
    test_size: int = 4_000,
) -> BraninDataset:
    """Create a reproducible pool and independent test set."""
    rng = np.random.default_rng(seed)
    pool_original = sample_domain(rng, pool_size)
    test_original = sample_domain(rng, test_size)
    return BraninDataset(
        seed=seed,
        threshold=threshold,
        pool_original=pool_original,
        pool_scaled=scale_to_unit_square(pool_original),
        pool_labels=labels_from_threshold(pool_original, threshold),
        test_original=test_original,
        test_scaled=scale_to_unit_square(test_original),
        test_labels=labels_from_threshold(test_original, threshold),
    )


def make_gp(seed: int) -> GaussianProcessRegressor:
    """Create the Week 1 GP-regression stand-in."""
    kernel = (
        ConstantKernel(1.0, (0.1, 10.0))
        # The lower bound prevents the regression stand-in from drawing a tiny
        # island around every observed label instead of a smooth regime boundary.
        * RBF(length_scale=0.20, length_scale_bounds=(0.08, 1.0))
        + WhiteKernel(noise_level=1e-4, noise_level_bounds="fixed")
    )
    return GaussianProcessRegressor(
        kernel=kernel,
        alpha=1e-6,
        normalize_y=False,
        n_restarts_optimizer=0,
        random_state=seed,
    )


def fit_gp(X: np.ndarray, y: np.ndarray, seed: int) -> GaussianProcessRegressor:
    """Fit while keeping harmless optimizer-bound warnings out of the report."""
    gp = make_gp(seed)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        gp.fit(X, y)
    return gp


def random_two_class_initial_design(
    labels: np.ndarray,
    size: int,
    rng: np.random.Generator,
    max_attempts: int = 10_000,
) -> tuple[list[int], int]:
    """Draw random sets until both labels occur.

    This preserves the brief's "6 random labelled points" instruction while
    avoiding the degenerate one-class GP fit that a very small random design can
    occasionally produce.
    """
    for attempt in range(1, max_attempts + 1):
        indices = rng.choice(len(labels), size=size, replace=False)
        if np.unique(labels[indices]).size == 2:
            return [int(index) for index in indices], attempt
    raise RuntimeError("Could not draw a two-class initial design")


def make_plot_grid(size: int = 180) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return physical and scaled versions of a regular plotting grid."""
    x1 = np.linspace(DOMAIN_LOWER[0], DOMAIN_UPPER[0], size)
    x2 = np.linspace(DOMAIN_LOWER[1], DOMAIN_UPPER[1], size)
    xx, yy = np.meshgrid(x1, x2)
    original = np.column_stack([xx.ravel(), yy.ravel()])
    return xx, yy, original, scale_to_unit_square(original)


def run_seed(
    seed: int,
    threshold: float,
    initial_size: int = 6,
    total_budget: int = 50,
    pool_size: int = 1_500,
    test_size: int = 4_000,
    snapshot_sizes: tuple[int, ...] = (6, 20, 50),
) -> BraninRun:
    """Run one smallest-|mu| active-learning experiment."""
    if not 2 <= initial_size < total_budget <= pool_size:
        raise ValueError("Require 2 <= initial_size < total_budget <= pool_size")

    dataset = make_dataset(seed, threshold, pool_size, test_size)
    rng = np.random.default_rng(seed + 100_000)
    labelled, attempts = random_two_class_initial_design(
        dataset.pool_labels, initial_size, rng
    )

    _, _, _, plot_grid_scaled = make_plot_grid()
    budgets: list[int] = []
    errors: list[float] = []
    snapshots: dict[int, dict[str, np.ndarray]] = {}

    while True:
        gp = fit_gp(
            dataset.pool_scaled[labelled], dataset.pool_labels[labelled], seed
        )

        test_mean = gp.predict(dataset.test_scaled)
        test_prediction = np.where(test_mean >= 0.0, 1.0, -1.0)
        error = float(np.mean(test_prediction != dataset.test_labels))
        budgets.append(len(labelled))
        errors.append(error)

        if len(labelled) in snapshot_sizes:
            grid_mean, grid_std = gp.predict(plot_grid_scaled, return_std=True)
            snapshots[len(labelled)] = {
                "mean": grid_mean,
                "std": grid_std,
                "labelled_indices": np.asarray(labelled, dtype=int),
            }

        if len(labelled) == total_budget:
            break

        mask = np.ones(pool_size, dtype=bool)
        mask[labelled] = False
        unlabelled = np.flatnonzero(mask)
        pool_mean = gp.predict(dataset.pool_scaled[unlabelled])
        next_index = int(unlabelled[np.argmin(np.abs(pool_mean))])
        labelled.append(next_index)

    return BraninRun(
        seed=seed,
        dataset=dataset,
        labelled_indices=labelled,
        initial_resampling_attempts=attempts,
        budgets=budgets,
        error_history=errors,
        snapshots=snapshots,
    )


def plot_dataset_overview(run: BraninRun, output_path: Path) -> None:
    """Show the exact thresholded labels and analytic Branin contour."""
    xx, yy, grid_original, _ = make_plot_grid(size=260)
    values = branin(grid_original).reshape(xx.shape)
    exact_labels = np.where(values >= run.dataset.threshold, 1.0, -1.0)

    fig, ax = plt.subplots(figsize=(9, 7))
    ax.contourf(
        xx,
        yy,
        exact_labels,
        levels=[-1.5, 0.0, 1.5],
        colors=["#3b6fb6", "#d95f4f"],
        alpha=0.78,
    )
    boundary = ax.contour(
        xx,
        yy,
        values,
        levels=[run.dataset.threshold],
        colors="black",
        linewidths=2.5,
    )
    ax.scatter(
        run.dataset.pool_original[:, 0],
        run.dataset.pool_original[:, 1],
        c=run.dataset.pool_labels,
        cmap="coolwarm",
        vmin=-1,
        vmax=1,
        s=8,
        alpha=0.28,
        linewidths=0,
    )
    ax.clabel(boundary, fmt={run.dataset.threshold: f"threshold = {run.dataset.threshold:.3f}"})
    ax.set(
        title="Thresholded Branin: exact analytic regime boundary",
        xlabel="x1 (original Branin domain)",
        ylabel="x2 (original Branin domain)",
        xlim=(DOMAIN_LOWER[0], DOMAIN_UPPER[0]),
        ylim=(DOMAIN_LOWER[1], DOMAIN_UPPER[1]),
    )
    ax.text(
        0.01,
        -0.13,
        "Blue: Branin < threshold (-1)    Red: Branin >= threshold (+1)",
        transform=ax.transAxes,
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_snapshots(run: BraninRun, output_path: Path) -> None:
    """Compare GP boundary estimates with the exact Branin boundary."""
    xx, yy, grid_original, _ = make_plot_grid()
    values = branin(grid_original).reshape(xx.shape)
    budgets = sorted(run.snapshots)
    fig, axes = plt.subplots(1, len(budgets), figsize=(17, 5.6), sharex=True, sharey=True)

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
        ax.contour(xx, yy, mean, levels=[0.0], colors="black", linewidths=2.4)
        ax.contour(
            xx,
            yy,
            values,
            levels=[run.dataset.threshold],
            colors="#f4e04d",
            linestyles="--",
            linewidths=2.4,
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
            s=42,
            zorder=3,
        )
        error = run.error_history[run.budgets.index(budget)]
        ax.set_title(f"n={budget} labelled points\ntest error={error:.3f}")
        ax.set_xlabel("x1")
        ax.set_xlim(DOMAIN_LOWER[0], DOMAIN_UPPER[0])
        ax.set_ylim(DOMAIN_LOWER[1], DOMAIN_UPPER[1])

    axes[0].set_ylabel("x2")
    legend = [
        Line2D([0], [0], color="black", lw=2.4, label="GP believed boundary: mu=0"),
        Line2D([0], [0], color="#f4e04d", lw=2.4, ls="--", label="Exact Branin boundary"),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=2, frameon=False)
    fig.suptitle(
    f"Week 1 active learning on thresholded Branin (seed {run.seed})",
    fontsize=15,
    )
    # Leave explicit space on the right for the colorbar.
    fig.subplots_adjust(bottom=0.20, top=0.82, right=0.84, wspace=0.18)
    # Put the colorbar in its own dedicated axis so it cannot overlap the third plot.
    cbar_ax = fig.add_axes([0.87, 0.24, 0.015, 0.52])
    fig.colorbar(image, cax=cbar_ax, label="GP latent mean μ(x)")
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_error_curves(runs: list[BraninRun], output_path: Path) -> None:
    """Plot per-seed and mean test misclassification error."""
    budgets = np.asarray(runs[0].budgets)
    errors = np.asarray([run.error_history for run in runs])
    mean = errors.mean(axis=0)
    std = errors.std(axis=0)

    fig, ax = plt.subplots(figsize=(9, 6))
    colors = ["#3572A5", "#D55E00", "#009E73"]
    for run, color in zip(runs, colors):
        ax.plot(
            budgets,
            run.error_history,
            color=color,
            alpha=0.62,
            linewidth=1.5,
            label=f"seed {run.seed}",
        )
    ax.plot(budgets, mean, color="black", linewidth=3.0, label="mean over 3 seeds")
    ax.fill_between(
        budgets,
        np.maximum(0.0, mean - std),
        np.minimum(1.0, mean + std),
        color="black",
        alpha=0.12,
        label="mean +/- 1 std",
    )
    ax.set(
        title="Thresholded Branin: test error vs labelled evaluations",
        xlabel="Number of labelled Branin evaluations",
        ylabel="Fraction of 4,000 test points mislabelled",
        xlim=(budgets.min(), budgets.max()),
        ylim=(0.0, max(0.5, float(errors.max()) + 0.03)),
    )
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_summary(
    runs: list[BraninRun],
    output_path: Path,
    threshold_seed: int,
    threshold_sample_size: int,
) -> None:
    """Write all numeric results needed to reproduce and explain the run."""
    per_seed = {}
    for run in runs:
        per_seed[str(run.seed)] = {
            "initial_error": run.error_history[0],
            "final_error": run.error_history[-1],
            "final_error_lower_than_initial": run.error_history[-1]
            < run.error_history[0],
            "initial_design_resampling_attempts": run.initial_resampling_attempts,
            "budgets": run.budgets,
            "error_history": run.error_history,
        }

    errors = np.asarray([run.error_history for run in runs])
    summary = {
        "experiment": "thresholded_branin_week1",
        "threshold": runs[0].dataset.threshold,
        "threshold_percentile": 45.0,
        "threshold_estimation_seed": threshold_seed,
        "threshold_estimation_sample_size": threshold_sample_size,
        "domain": {"x1": [-5.0, 10.0], "x2": [0.0, 15.0]},
        "pool_size_per_seed": len(runs[0].dataset.pool_labels),
        "test_size_per_seed": len(runs[0].dataset.test_labels),
        "initial_labelled_size": runs[0].budgets[0],
        "total_budget": runs[0].budgets[-1],
        "seeds": [run.seed for run in runs],
        "selection_rule": "choose unlabelled pool point with smallest abs(mu)",
        "prediction_rule": "+1 if GP latent mean mu >= 0, else -1",
        "error_definition": "fraction of exact test labels predicted incorrectly",
        "initial_design": (
            "Six points are sampled uniformly without replacement. If all six "
            "have one class, the six-point draw is repeated until both classes occur."
        ),
        "model_note": (
            "GaussianProcessRegressor on {-1,+1} labels is a Week 1 stand-in, "
            "not a calibrated GP classifier."
        ),
        "kernel_note": (
            "RBF length scale is optimized with a lower bound of 0.08 in scaled "
            "coordinates to preserve a smooth Week 1 boundary estimate."
        ),
        "per_seed": per_seed,
        "mean_initial_error": float(errors[:, 0].mean()),
        "mean_final_error": float(errors[:, -1].mean()),
        "all_seeds_finish_below_initial_error": bool(
            np.all(errors[:, -1] < errors[:, 0])
        ),
    }
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def run_experiment(
    seeds: tuple[int, ...] = (0, 1, 2),
    output_dir: Path | None = None,
) -> list[BraninRun]:
    """Run all Week 1 Branin seeds and save slide-ready outputs."""
    threshold_seed = 2026
    threshold_sample_size = 20_000
    threshold = compute_threshold(threshold_sample_size, threshold_seed)
    runs = [run_seed(seed, threshold) for seed in seeds]

    if output_dir is None:
        output_dir = Path(__file__).resolve().parents[1] / "outputs" / "branin_week1"
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_dataset_overview(runs[0], output_dir / "dataset_overview.png")
    plot_snapshots(runs[0], output_dir / "active_learning_snapshots_seed0.png")
    plot_error_curves(runs, output_dir / "error_vs_evaluations.png")
    save_summary(
        runs,
        output_dir / "summary.json",
        threshold_seed,
        threshold_sample_size,
    )
    return runs


def main() -> None:
    output_dir = Path(__file__).resolve().parents[1] / "outputs" / "branin_week1"
    runs = run_experiment(output_dir=output_dir)
    print(f"Threshold (45th percentile): {runs[0].dataset.threshold:.8f}")
    for run in runs:
        print(
            f"seed={run.seed}: initial error={run.error_history[0]:.4f}, "
            f"final error={run.error_history[-1]:.4f}, "
            f"initial-draw attempts={run.initial_resampling_attempts}"
        )
    print(f"Saved Week 1 Branin outputs to {output_dir}")


if __name__ == "__main__":
    main()
