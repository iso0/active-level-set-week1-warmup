"""Reproducible make_moons sanity check for the active-learning loop."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_moons
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, RBF, WhiteKernel
from sklearn.preprocessing import MinMaxScaler


@dataclass
class ExperimentResult:
    seed: int
    X: np.ndarray
    y: np.ndarray
    labelled_indices: list[int]
    snapshots: dict[int, dict[str, np.ndarray | float]]
    uncertainty_history: list[float]


def make_dataset(seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Create the deterministic, unit-square make_moons pool."""
    X, y01 = make_moons(n_samples=600, noise=0.05, random_state=seed)
    X = MinMaxScaler().fit_transform(X)
    y = np.where(y01 == 1, 1.0, -1.0)
    return X, y


def make_gp(seed: int = 0) -> GaussianProcessRegressor:
    """Return a GP exposing latent posterior mean and standard deviation."""
    kernel = (
        ConstantKernel(1.0, (0.1, 10.0))
        * RBF(length_scale=0.18, length_scale_bounds=(0.03, 1.0))
        + WhiteKernel(noise_level=1e-4, noise_level_bounds="fixed")
    )
    return GaussianProcessRegressor(
        kernel=kernel,
        alpha=1e-6,
        normalize_y=False,
        n_restarts_optimizer=1,
        random_state=seed,
    )


def make_grid(size: int = 160) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    axis = np.linspace(0.0, 1.0, size)
    xx, yy = np.meshgrid(axis, axis)
    return xx, yy, np.column_stack([xx.ravel(), yy.ravel()])


def run_experiment(
    seed: int = 0,
    initial_size: int = 6,
    total_budget: int = 50,
    snapshot_sizes: tuple[int, ...] = (6, 20, 50),
) -> ExperimentResult:
    """Run pool-based active learning using the smallest-|mu| rule."""
    if not 2 <= initial_size < total_budget <= 600:
        raise ValueError("Require 2 <= initial_size < total_budget <= 600")

    X, y = make_dataset(seed)
    rng = np.random.default_rng(seed)

    # Guarantee both regimes are represented in the tiny initial design.
    negative = rng.choice(np.flatnonzero(y == -1), initial_size // 2, replace=False)
    positive = rng.choice(
        np.flatnonzero(y == 1), initial_size - len(negative), replace=False
    )
    labelled = [int(i) for i in np.concatenate([negative, positive])]
    rng.shuffle(labelled)

    xx, yy, grid = make_grid()
    snapshots: dict[int, dict[str, np.ndarray | float]] = {}
    uncertainty_history: list[float] = []

    while True:
        gp = make_gp(seed)
        gp.fit(X[labelled], y[labelled])
        grid_mean, grid_std = gp.predict(grid, return_std=True)
        uncertain_fraction = float(np.mean(np.abs(grid_mean) <= 1.96 * grid_std))
        uncertainty_history.append(uncertain_fraction)

        if len(labelled) in snapshot_sizes:
            snapshots[len(labelled)] = {
                "mean": grid_mean.reshape(xx.shape),
                "std": grid_std.reshape(xx.shape),
                "uncertain_fraction": uncertain_fraction,
                "labelled_indices": np.asarray(labelled, dtype=int),
            }

        if len(labelled) == total_budget:
            break

        unlabelled = np.setdiff1d(np.arange(len(X)), labelled, assume_unique=False)
        pool_mean = gp.predict(X[unlabelled])
        next_index = int(unlabelled[np.argmin(np.abs(pool_mean))])
        labelled.append(next_index)

    return ExperimentResult(seed, X, y, labelled, snapshots, uncertainty_history)


def plot_snapshots(result: ExperimentResult, output_path: Path) -> None:
    """Plot the learned boundary and uncertainty at selected budgets."""
    xx, yy, _ = make_grid()
    budgets = sorted(result.snapshots)
    fig, axes = plt.subplots(2, len(budgets), figsize=(5 * len(budgets), 8))

    for column, budget in enumerate(budgets):
        snapshot = result.snapshots[budget]
        mean = np.asarray(snapshot["mean"])
        std = np.asarray(snapshot["std"])
        indices = np.asarray(snapshot["labelled_indices"], dtype=int)

        ax = axes[0, column]
        score_proxy = 0.5 * (np.tanh(mean) + 1.0)
        image = ax.contourf(xx, yy, score_proxy, levels=20, cmap="coolwarm")
        ax.contour(xx, yy, mean, levels=[0.0], colors="black", linewidths=2)
        ax.scatter(
            result.X[indices, 0],
            result.X[indices, 1],
            c=result.y[indices],
            cmap="coolwarm",
            edgecolors="white",
            linewidths=0.7,
            s=38,
        )
        ax.set_title(f"n={budget}: believed boundary")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        fig.colorbar(image, ax=ax, label="display score (not calibrated probability)")

        ax = axes[1, column]
        uncertainty = 1.96 * std
        image = ax.contourf(xx, yy, uncertainty, levels=20, cmap="viridis")
        ax.contour(xx, yy, mean, levels=[0.0], colors="white", linewidths=2)
        ax.set_title(
            f"95% latent uncertainty\n"
            f"credible-region area={snapshot['uncertain_fraction']:.3f}"
        )
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        fig.colorbar(image, ax=ax, label="1.96 sigma")

    for ax in axes.ravel():
        ax.set_xlabel("scaled x1")
        ax.set_ylabel("scaled x2")

    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def save_results(result: ExperimentResult, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_snapshots(result, output_dir / "boundary_contraction.png")
    summary = {
        "seed": result.seed,
        "pool_size": len(result.X),
        "initial_size": min(result.snapshots),
        "total_budget": len(result.labelled_indices),
        "selection_rule": "argmin_abs_posterior_mean",
        "initial_design": "stratified random: three points from each class",
        "model_note": (
            "GaussianProcessRegressor on {-1,+1} labels is a Week 1 stand-in; "
            "the displayed score is not a calibrated class probability."
        ),
        "snapshot_uncertain_fractions": {
            str(n): float(snapshot["uncertain_fraction"])
            for n, snapshot in result.snapshots.items()
        },
        "uncertainty_history": result.uncertainty_history,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )


def main() -> None:
    output_dir = Path(__file__).resolve().parents[1] / "outputs" / "make_moons"
    results = [run_experiment(seed=seed) for seed in range(3)]
    save_results(results[0], output_dir)

    seed_summary = {}
    for result in results:
        fractions = {
            str(budget): float(snapshot["uncertain_fraction"])
            for budget, snapshot in sorted(result.snapshots.items())
        }
        contracts = fractions["50"] < fractions["6"]
        seed_summary[str(result.seed)] = {
            "snapshot_uncertain_fractions": fractions,
            "contracts_from_6_to_50": contracts,
        }
        print(
            f"seed={result.seed}: n=6 {fractions['6']:.4f}, "
            f"n=20 {fractions['20']:.4f}, n=50 {fractions['50']:.4f}, "
            f"contracts={contracts}"
        )

    (output_dir / "three_seed_check.json").write_text(
        json.dumps(seed_summary, indent=2), encoding="utf-8"
    )
    if not all(item["contracts_from_6_to_50"] for item in seed_summary.values()):
        raise RuntimeError("Posterior uncertainty did not contract for every seed")

    print(f"Completed {len(results[0].labelled_indices)} evaluations per seed.")
    print(f"Saved results to {output_dir}")


if __name__ == "__main__":
    main()
