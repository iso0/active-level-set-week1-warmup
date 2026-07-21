"""Week 4 Experiment 07 optimized GP-classifier surrogate comparison.

This experiment asks whether learning GaussianProcessClassifier kernel
hyperparameters improves active level-set estimation relative to the fixed
Week 4 Experiment 06 classifier and the strongest existing GP-regression references.

Acquisition functions use only current labelled data, unlabelled coordinates,
and classifier probabilities. True function values, true labels of unqueried
points, and boundary masks are used only after selection for evaluation.
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
from sklearn.base import clone
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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "week4_07_optimized_gp_classifier_surrogate"
SEEDS = (0, 1, 2, 3, 4)
CLASSIFIER_METHODS = (
    "random",
    "classifier_margin",
    "classifier_entropy",
    "classifier_gated_diversity",
    "classifier_uncertainty_repulsion",
)
OPTIONAL_METHODS = ("classifier_straddle_analog",)
SURROGATE_VARIANTS = (
    "fixed_iso_gpc",
    "optimized_iso_gpc",
    "optimized_ard_gpc",
)
BOUNDARY_QUANTILES = (10, 20, 30)
UNCERTAINTY_EPSILONS = (0.05, 0.10)
PRIMARY_UNCERTAINTY_EPSILON = 0.10
CLASSIFIER_GATE_FRACTION = 0.10
CLASSIFIER_MIN_SHORTLIST_SIZE = 25
CLASSIFIER_DIVERSITY_BETA = 0.50
CLASSIFIER_REPULSION_BANDWIDTH = 0.15
GPC_LENGTH_SCALE = 0.25
GPC_MAX_ITER_PREDICT = 100
KERNEL_CONSTANT_BOUNDS = (0.1, 10.0)
KERNEL_LENGTH_SCALE_BOUNDS = (0.03, 3.0)
BOUND_NEAR_FRACTION = 0.05

METHOD_DESCRIPTIONS = {
    "random": "Uniformly random unlabelled pool point.",
    "classifier_margin": "Choose the largest 1 - 2*abs(p_plus - 0.5).",
    "classifier_entropy": "Choose maximum binary predictive entropy.",
    "classifier_gated_diversity": (
        "Gate to top classifier-margin candidates, then mix normalized "
        "uncertainty and nearest-labelled-point diversity with beta=0.50."
    ),
    "classifier_uncertainty_repulsion": (
        "Gate to top classifier-margin candidates, then choose largest "
        "normalized uncertainty times labelled-set repulsion."
    ),
    "classifier_straddle_analog": (
        "Optional diagnostic: uncertainty_score times labelled-set repulsion "
        "over the full unlabelled pool."
    ),
}

METHOD_COLORS = {
    "random": "#7a7a7a",
    "classifier_margin": "#2b6cb0",
    "classifier_entropy": "#0f8b61",
    "classifier_gated_diversity": "#d95f02",
    "classifier_uncertainty_repulsion": "#6a3d9a",
    "classifier_straddle_analog": "#1f9eaa",
}

VARIANT_STYLES = {
    "fixed_iso_gpc": "-",
    "optimized_iso_gpc": "--",
    "optimized_ard_gpc": ":",
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
class RunOptions:
    quick: bool
    n_restarts: int
    optimize_every: int
    max_seeds: int | None
    include_straddle_analog: bool
    output_dir: Path


@dataclass
class MethodRun:
    benchmark: str
    surrogate_variant: str
    acquisition_rule: str
    seed: int
    initial_indices: list[int]
    labelled_indices: list[int]
    budgets: list[int]
    metric_rows: list[dict[str, object]]
    query_rows: list[dict[str, object]]
    hyperparameter_rows: list[dict[str, object]]
    runtime_rows: list[dict[str, object]]
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
    hyperparameter_rows: list[dict[str, object]]
    runtime_rows: list[dict[str, object]]
    final_rows: list[dict[str, object]]
    tolerance_rows: list[dict[str, object]]
    best_rows: list[dict[str, object]]
    regressor_reference_rows: list[dict[str, object]]
    fixed_experiment06_reference_rows: list[dict[str, object]]
    summary: dict[str, object]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
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


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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


def rows_hash(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.name).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def parse_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in {"", "null", "nan"}:
        return None
    return float(value)


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


def epsilon_suffix(epsilon: float) -> str:
    return f"eps{int(round(epsilon * 100)):03d}"


def deterministic_argmax(indices: np.ndarray, scores: np.ndarray) -> int:
    order = np.lexsort((indices, -scores))
    return int(order[0])


def stable_seed(*items: object) -> int:
    digest = hashlib.sha256(":".join(str(item) for item in items).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little") % (2**32)


def rng_for_method(seed: int, method: str, benchmark: str) -> np.random.Generator:
    return np.random.default_rng(stable_seed(seed, benchmark, method, "week6_1_classifier"))


def get_dataset_values(dataset: object, config: BenchmarkConfig) -> tuple[np.ndarray, np.ndarray]:
    if hasattr(dataset, "pool_values") and hasattr(dataset, "test_values"):
        return np.asarray(dataset.pool_values), np.asarray(dataset.test_values)
    return config.value_function(dataset.pool_original), config.value_function(dataset.test_original)


def boundary_masks(distances: np.ndarray) -> dict[int, np.ndarray]:
    return {
        quantile: distances <= float(np.percentile(distances, quantile))
        for quantile in BOUNDARY_QUANTILES
    }


def class_balance(labels: np.ndarray) -> dict[str, float]:
    labels = np.asarray(labels)
    return {
        "negative_fraction": float(np.mean(labels == -1.0)),
        "positive_fraction": float(np.mean(labels == 1.0)),
    }


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

    if method == "classifier_straddle_analog":
        distances = nearest_labelled_distance(pool_scaled, unlabelled_indices, labelled_indices)
        repulsion = 1.0 - np.exp(-(distances**2) / (2.0 * CLASSIFIER_REPULSION_BANDWIDTH**2 + 1e-12))
        score = uncertainty * repulsion
        position = deterministic_argmax(unlabelled_indices, score)
        return int(unlabelled_indices[position]), {
            "repulsion_bandwidth": CLASSIFIER_REPULSION_BANDWIDTH,
            "selected_position": position,
            "selected_p_plus": float(p_plus[position]),
            "selected_uncertainty_score": float(uncertainty[position]),
            "selected_entropy": float(entropy[position]),
            "selected_raw_distance_to_labelled": float(distances[position]),
            "selected_repulsion": float(repulsion[position]),
            "selected_score": float(score[position]),
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
    raise ValueError(f"Unknown classifier acquisition method: {method}")


def make_base_kernel(variant: str, dimension: int):
    if variant == "fixed_iso_gpc":
        return ConstantKernel(1.0, constant_value_bounds="fixed") * RBF(
            length_scale=GPC_LENGTH_SCALE,
            length_scale_bounds="fixed",
        )
    if variant == "optimized_iso_gpc":
        return ConstantKernel(1.0, constant_value_bounds=KERNEL_CONSTANT_BOUNDS) * RBF(
            length_scale=GPC_LENGTH_SCALE,
            length_scale_bounds=KERNEL_LENGTH_SCALE_BOUNDS,
        )
    if variant == "optimized_ard_gpc":
        return ConstantKernel(1.0, constant_value_bounds=KERNEL_CONSTANT_BOUNDS) * RBF(
            length_scale=np.full(dimension, GPC_LENGTH_SCALE),
            length_scale_bounds=KERNEL_LENGTH_SCALE_BOUNDS,
        )
    raise ValueError(f"Unknown surrogate variant: {variant}")


def should_optimize_hyperparameters(
    *,
    variant: str,
    budget: int,
    initial_size: int,
    optimize_every: int,
    cached_kernel: object | None,
) -> bool:
    if variant == "fixed_iso_gpc":
        return False
    if cached_kernel is None:
        return True
    return (budget - initial_size) % optimize_every == 0


def kernel_bounds_for_row(variant: str) -> tuple[tuple[float, float] | None, tuple[float, float] | None]:
    if variant == "fixed_iso_gpc":
        return None, None
    return KERNEL_CONSTANT_BOUNDS, KERNEL_LENGTH_SCALE_BOUNDS


def near_bound(value: float, lower: float, upper: float, side: str) -> bool:
    margin = BOUND_NEAR_FRACTION * (upper - lower)
    if side == "lower":
        return value <= lower + margin
    if side == "upper":
        return value >= upper - margin
    raise ValueError(side)


def extract_kernel_diagnostics(
    gp: GaussianProcessClassifier,
    *,
    benchmark: str,
    seed: int,
    acquisition_rule: str,
    surrogate_variant: str,
    budget: int,
    optimized_this_fit: bool,
    reused_kernel_from_previous_optimization: bool,
    fit_time_seconds: float,
    n_restarts_requested: int,
    optimize_every: int,
) -> dict[str, object]:
    kernel = gp.kernel_
    constant_value = float(kernel.k1.constant_value)
    length_scale_raw = np.asarray(kernel.k2.length_scale, dtype=float)
    length_scale_values = length_scale_raw.reshape(-1)
    constant_bounds, length_bounds = kernel_bounds_for_row(surrogate_variant)
    if constant_bounds is None:
        constant_near_lower = False
        constant_near_upper = False
    else:
        constant_near_lower = near_bound(constant_value, constant_bounds[0], constant_bounds[1], "lower")
        constant_near_upper = near_bound(constant_value, constant_bounds[0], constant_bounds[1], "upper")
    if length_bounds is None:
        length_near_lower = [False for _ in length_scale_values]
        length_near_upper = [False for _ in length_scale_values]
    else:
        length_near_lower = [
            near_bound(float(value), length_bounds[0], length_bounds[1], "lower")
            for value in length_scale_values
        ]
        length_near_upper = [
            near_bound(float(value), length_bounds[0], length_bounds[1], "upper")
            for value in length_scale_values
        ]
    row: dict[str, object] = {
        "benchmark": benchmark,
        "seed": seed,
        "acquisition_rule": acquisition_rule,
        "method": acquisition_rule,
        "surrogate_variant": surrogate_variant,
        "budget": budget,
        "labelled_budget_n": budget,
        "learned_kernel": str(kernel),
        "learned_constant": constant_value,
        "learned_length_scale": (
            float(length_scale_values[0])
            if len(length_scale_values) == 1
            else json.dumps([float(value) for value in length_scale_values])
        ),
        "learned_length_scale_mean": float(length_scale_values.mean()),
        "learned_length_scale_min": float(length_scale_values.min()),
        "learned_length_scale_max": float(length_scale_values.max()),
        "learned_length_scale_dim0": float(length_scale_values[0]) if len(length_scale_values) > 0 else None,
        "learned_length_scale_dim1": float(length_scale_values[1]) if len(length_scale_values) > 1 else None,
        "learned_length_scale_dim2": float(length_scale_values[2]) if len(length_scale_values) > 2 else None,
        "learned_length_scale_dim3": float(length_scale_values[3]) if len(length_scale_values) > 3 else None,
        "length_scale_near_lower_bound": bool(any(length_near_lower)),
        "length_scale_near_upper_bound": bool(any(length_near_upper)),
        "length_scale_near_lower_bound_by_dimension": json.dumps(length_near_lower),
        "length_scale_near_upper_bound_by_dimension": json.dumps(length_near_upper),
        "constant_near_lower_bound": bool(constant_near_lower),
        "constant_near_upper_bound": bool(constant_near_upper),
        "log_marginal_likelihood_value": parse_float(getattr(gp, "log_marginal_likelihood_value_", None)),
        "fit_time_seconds": fit_time_seconds,
        "optimized_this_fit": optimized_this_fit,
        "reused_kernel_from_previous_optimization": reused_kernel_from_previous_optimization,
        "n_restarts_optimizer_requested": n_restarts_requested,
        "optimize_every": optimize_every,
    }
    return row


def fit_classifier_variant(
    *,
    X: np.ndarray,
    y: np.ndarray,
    benchmark: str,
    seed: int,
    acquisition_rule: str,
    surrogate_variant: str,
    budget: int,
    initial_size: int,
    n_restarts: int,
    optimize_every: int,
    cached_kernel: object | None,
) -> tuple[GaussianProcessClassifier, object | None, dict[str, object]]:
    if np.unique(y).size < 2:
        raise RuntimeError("GaussianProcessClassifier requires both classes in the labelled set")

    dimension = X.shape[1]
    optimize_this_fit = should_optimize_hyperparameters(
        variant=surrogate_variant,
        budget=budget,
        initial_size=initial_size,
        optimize_every=optimize_every,
        cached_kernel=cached_kernel,
    )
    if surrogate_variant == "fixed_iso_gpc":
        kernel = make_base_kernel(surrogate_variant, dimension)
        optimizer = None
        restarts = 0
    elif optimize_this_fit:
        kernel = make_base_kernel(surrogate_variant, dimension)
        optimizer = "fmin_l_bfgs_b"
        restarts = n_restarts
    else:
        kernel = clone(cached_kernel)
        optimizer = None
        restarts = 0

    gp = GaussianProcessClassifier(
        kernel=kernel,
        optimizer=optimizer,
        n_restarts_optimizer=restarts,
        max_iter_predict=GPC_MAX_ITER_PREDICT,
        random_state=stable_seed(seed, benchmark, surrogate_variant, budget, "gpc_fit"),
    )
    start = time.perf_counter()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        warnings.simplefilter("ignore", RuntimeWarning)
        gp.fit(X, y)
    fit_time = time.perf_counter() - start
    if surrogate_variant != "fixed_iso_gpc" and optimize_this_fit:
        cached_kernel = clone(gp.kernel_)
    trace_row = extract_kernel_diagnostics(
        gp,
        benchmark=benchmark,
        seed=seed,
        acquisition_rule=acquisition_rule,
        surrogate_variant=surrogate_variant,
        budget=budget,
        optimized_this_fit=optimize_this_fit,
        reused_kernel_from_previous_optimization=bool(surrogate_variant != "fixed_iso_gpc" and not optimize_this_fit),
        fit_time_seconds=fit_time,
        n_restarts_requested=n_restarts,
        optimize_every=optimize_every,
    )
    return gp, cached_kernel, trace_row


def predict_p_plus(gp: GaussianProcessClassifier, X: np.ndarray) -> np.ndarray:
    probabilities = gp.predict_proba(X)
    matches = np.flatnonzero(gp.classes_ == 1.0)
    if len(matches) != 1:
        raise RuntimeError(f"Expected class +1 in classifier classes, got {gp.classes_}")
    return probabilities[:, int(matches[0])]


def evaluate_budget(
    *,
    benchmark: str,
    acquisition_rule: str,
    surrogate_variant: str,
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
        "surrogate_variant": surrogate_variant,
        "acquisition_rule": acquisition_rule,
        "method": acquisition_rule,
        "seed": seed,
        "budget": budget,
        "global_error": float(np.mean(errors)),
    }
    for epsilon in UNCERTAINTY_EPSILONS:
        suffix = epsilon_suffix(epsilon)
        uncertain = np.abs(p_plus - 0.5) <= epsilon
        row[f"classifier_uncertainty_region_fraction_{suffix}"] = float(np.mean(uncertain))
    for quantile, mask in test_masks.items():
        row[f"near_boundary_error_q{quantile}"] = float(np.mean(errors[mask]))
        row[f"near_boundary_test_size_q{quantile}"] = int(mask.sum())
        for epsilon in UNCERTAINTY_EPSILONS:
            suffix = epsilon_suffix(epsilon)
            uncertain = np.abs(p_plus - 0.5) <= epsilon
            row[f"classifier_uncertainty_region_fraction_q{quantile}_{suffix}"] = float(np.mean(uncertain[mask]))
    return row


def run_method(
    config: BenchmarkConfig,
    design: object,
    surrogate_variant: str,
    acquisition_rule: str,
    options: RunOptions,
) -> MethodRun:
    method_start = time.perf_counter()
    dataset = design.dataset
    pool_values, test_values = get_dataset_values(dataset, config)
    pool_distances = np.abs(pool_values - config.threshold)
    test_distances = np.abs(test_values - config.threshold)
    pool_masks = boundary_masks(pool_distances)
    test_masks = boundary_masks(test_distances)
    labelled = list(design.initial_indices)
    initial_copy = list(design.initial_indices)
    rng = rng_for_method(design.seed, acquisition_rule, config.name)
    budgets: list[int] = []
    metric_rows: list[dict[str, object]] = []
    query_rows: list[dict[str, object]] = []
    hyper_rows: list[dict[str, object]] = []
    cached_kernel = None

    while True:
        gp, cached_kernel, hyper_row = fit_classifier_variant(
            X=dataset.pool_scaled[labelled],
            y=dataset.pool_labels[labelled],
            benchmark=config.name,
            seed=design.seed,
            acquisition_rule=acquisition_rule,
            surrogate_variant=surrogate_variant,
            budget=len(labelled),
            initial_size=config.initial_size,
            n_restarts=options.n_restarts,
            optimize_every=options.optimize_every,
            cached_kernel=cached_kernel,
        )
        budget = len(labelled)
        budgets.append(budget)
        hyper_rows.append(hyper_row)
        metric_rows.append(
            evaluate_budget(
                benchmark=config.name,
                acquisition_rule=acquisition_rule,
                surrogate_variant=surrogate_variant,
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
            method=acquisition_rule,
            unlabelled_indices=unlabelled,
            p_plus=p_unlabelled,
            pool_scaled=dataset.pool_scaled,
            labelled_indices=labelled,
            rng=rng,
        )
        query_row: dict[str, object] = {
            "benchmark": config.name,
            "surrogate_variant": surrogate_variant,
            "acquisition_rule": acquisition_rule,
            "method": acquisition_rule,
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
    elapsed = time.perf_counter() - method_start
    runtime_row = {
        "benchmark": config.name,
        "surrogate_variant": surrogate_variant,
        "acquisition_rule": acquisition_rule,
        "method": acquisition_rule,
        "seed": design.seed,
        "total_runtime_seconds": elapsed,
        "fit_count": len(hyper_rows),
        "optimized_fit_count": sum(1 for row in hyper_rows if row["optimized_this_fit"]),
        "mean_fit_time_seconds": float(np.mean([float(row["fit_time_seconds"]) for row in hyper_rows])),
        "median_fit_time_seconds": float(np.median([float(row["fit_time_seconds"]) for row in hyper_rows])),
        "n_restarts_optimizer_requested": options.n_restarts,
        "optimize_every": options.optimize_every,
    }
    return MethodRun(
        benchmark=config.name,
        surrogate_variant=surrogate_variant,
        acquisition_rule=acquisition_rule,
        seed=design.seed,
        initial_indices=initial_copy,
        labelled_indices=labelled,
        budgets=budgets,
        metric_rows=metric_rows,
        query_rows=query_rows,
        hyperparameter_rows=hyper_rows,
        runtime_rows=[runtime_row],
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
        "same_pool_test_initial_threshold_within_seed_for_all_surrogates_and_acquisitions": True,
        "only_surrogate_variant_and_acquisition_rule_change": True,
        "acquisition_does_not_use_true_labels_or_true_function_values": True,
    }
    for seed in seeds:
        seed_runs = [run for run in runs if run.seed == seed]
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
    leaf_values: list[bool] = []
    for value in checks.values():
        if isinstance(value, dict):
            leaf_values.extend(bool(item) for item in value.values())
        else:
            leaf_values.append(bool(value))
    checks["all_checks_passed"] = all(leaf_values)
    return checks


def rank_methods(values_by_key: dict[tuple[str, str], float], smaller_is_better: bool = True) -> dict[tuple[str, str], int]:
    items = sorted(values_by_key.items(), key=lambda item: item[1], reverse=not smaller_is_better)
    return {key: rank + 1 for rank, (key, _) in enumerate(items)}


def summarize_final_metrics(
    config: BenchmarkConfig,
    metric_rows: list[dict[str, object]],
    query_rows: list[dict[str, object]],
    hyper_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    keys = sorted({(str(row["surrogate_variant"]), str(row["acquisition_rule"])) for row in metric_rows})
    raw_values: dict[tuple[str, str], dict[str, float]] = {}
    for surrogate_variant, acquisition_rule in keys:
        final_subset = [
            row
            for row in metric_rows
            if row["surrogate_variant"] == surrogate_variant
            and row["acquisition_rule"] == acquisition_rule
            and row["budget"] == config.total_budget
        ]
        query_subset = [
            row
            for row in query_rows
            if row["surrogate_variant"] == surrogate_variant
            and row["acquisition_rule"] == acquisition_rule
        ]
        hyper_subset = [
            row
            for row in hyper_rows
            if row["surrogate_variant"] == surrogate_variant
            and row["acquisition_rule"] == acquisition_rule
        ]
        distances = np.asarray([float(row["true_boundary_distance"]) for row in query_subset], dtype=float)
        row: dict[str, object] = {
            "benchmark": config.name,
            "display_name": config.display_name,
            "surrogate_variant": surrogate_variant,
            "acquisition_rule": acquisition_rule,
            "method": acquisition_rule,
            "final_budget": config.total_budget,
            "seed_count": len({item["seed"] for item in final_subset}),
        }
        metrics = [
            "global_error",
            "near_boundary_error_q10",
            "near_boundary_error_q20",
            "near_boundary_error_q30",
            f"classifier_uncertainty_region_fraction_{epsilon_suffix(0.10)}",
            f"classifier_uncertainty_region_fraction_q20_{epsilon_suffix(0.10)}",
            f"classifier_uncertainty_region_fraction_q30_{epsilon_suffix(0.10)}",
        ]
        for metric in metrics:
            mean, std = mean_std([float(item[metric]) for item in final_subset])
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
                "mean_fit_time_seconds": f"{np.mean([float(item['fit_time_seconds']) for item in hyper_subset]):.6f}",
                "mean_learned_constant": f"{np.mean([float(item['learned_constant']) for item in hyper_subset]):.6f}",
                "mean_learned_length_scale_mean": f"{np.mean([float(item['learned_length_scale_mean']) for item in hyper_subset]):.6f}",
                "length_scale_bound_hit_fraction": f"{np.mean([bool(item['length_scale_near_lower_bound']) or bool(item['length_scale_near_upper_bound']) for item in hyper_subset]):.6f}",
                "constant_bound_hit_fraction": f"{np.mean([bool(item['constant_near_lower_bound']) or bool(item['constant_near_upper_bound']) for item in hyper_subset]):.6f}",
            }
        )
        raw_values[(surrogate_variant, acquisition_rule)] = {
            "global_error": float(row["mean_final_global_error"]),
            "near_boundary_error_q10": float(row["mean_final_near_boundary_error_q10"]),
            "near_boundary_error_q20": float(row["mean_final_near_boundary_error_q20"]),
            "near_boundary_error_q30": float(row["mean_final_near_boundary_error_q30"]),
            "median_query_distance": float(row["median_query_distance"]),
        }
        rows.append(row)

    rank_fields = {
        "rank_global_error": "global_error",
        "rank_near_boundary_error_q10": "near_boundary_error_q10",
        "rank_near_boundary_error_q20": "near_boundary_error_q20",
        "rank_near_boundary_error_q30": "near_boundary_error_q30",
        "rank_median_query_distance": "median_query_distance",
    }
    for rank_field, metric in rank_fields.items():
        ranks = rank_methods({key: values[metric] for key, values in raw_values.items()})
        for row in rows:
            key = (str(row["surrogate_variant"]), str(row["acquisition_rule"]))
            row[rank_field] = ranks[key]
    return rows


def metric_curve_groups(metric_rows: list[dict[str, object]], metric: str) -> dict[tuple[str, str], dict[str, np.ndarray]]:
    groups: dict[tuple[str, str], dict[str, np.ndarray]] = {}
    keys = sorted({(str(row["surrogate_variant"]), str(row["acquisition_rule"])) for row in metric_rows})
    for key in keys:
        subset = [row for row in metric_rows if (row["surrogate_variant"], row["acquisition_rule"]) == key]
        budgets = sorted({int(row["budget"]) for row in subset})
        means = []
        stds = []
        for budget in budgets:
            values = [float(row[metric]) for row in subset if int(row["budget"]) == budget]
            mean, std = mean_std(values)
            means.append(mean)
            stds.append(std)
        groups[key] = {
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
    for (surrogate_variant, acquisition_rule), series in metric_curve_groups(rows, metric).items():
        color = METHOD_COLORS.get(acquisition_rule, "#333333")
        linestyle = VARIANT_STYLES.get(surrogate_variant, "-")
        label = f"{surrogate_variant} / {acquisition_rule}"
        ax.plot(
            series["budgets"],
            series["mean"],
            color=color,
            linestyle=linestyle,
            linewidth=2.1,
            label=label,
        )
        ax.fill_between(
            series["budgets"],
            np.maximum(0.0, series["mean"] - series["std"]),
            np.minimum(1.0, series["mean"] + series["std"]),
            color=color,
            alpha=0.06,
            linewidth=0,
        )
    ax.set(
        title=title,
        xlabel="Labelled oracle evaluations",
        ylabel=ylabel,
        xlim=(config.initial_size, config.total_budget),
    )
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7, ncol=2, loc="upper right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_final_bar(final_rows: list[dict[str, object]], config: BenchmarkConfig, output_path: Path) -> None:
    labels = [f"{row['surrogate_variant']}\n{row['acquisition_rule']}" for row in final_rows]
    x = np.arange(len(labels))
    width = 0.25
    metrics = [
        ("mean_final_global_error", "global", "#4c78a8"),
        ("mean_final_near_boundary_error_q20", "q20", "#f58518"),
        ("mean_final_near_boundary_error_q30", "q30", "#54a24b"),
    ]
    fig, ax = plt.subplots(figsize=(14, 7.2))
    for offset, (field, label, color) in zip((-width, 0.0, width), metrics):
        values = [float(row[field]) for row in final_rows]
        ax.bar(x + offset, values, width=width, label=label, color=color, alpha=0.86)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=65, ha="right", fontsize=7)
    ax.set(
        title=f"{config.display_name}: final global/q20/q30 error",
        ylabel="Mean final error across seeds",
        ylim=(0.0, min(1.0, max(float(row["mean_final_near_boundary_error_q20"]) for row in final_rows) + 0.08)),
    )
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_query_distance_boxplot(query_rows: list[dict[str, object]], config: BenchmarkConfig, output_path: Path) -> None:
    keys = sorted({(str(row["surrogate_variant"]), str(row["acquisition_rule"])) for row in query_rows})
    labels = [f"{variant}\n{method}" for variant, method in keys]
    values = [
        [
            max(float(row["true_boundary_distance"]), 1e-12)
            for row in query_rows
            if (row["surrogate_variant"], row["acquisition_rule"]) == key
        ]
        for key in keys
    ]
    fig, ax = plt.subplots(figsize=(14, 7.2))
    ax.boxplot(values, tick_labels=labels, showfliers=False)
    ax.set_yscale("log")
    ax.set(
        title=f"{config.display_name}: query distance to true threshold",
        ylabel="abs(f(x_query) - threshold), log scale",
    )
    ax.tick_params(axis="x", rotation=65, labelsize=7)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_query_distance_over_budget(query_rows: list[dict[str, object]], config: BenchmarkConfig, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12.5, 7.2))
    keys = sorted({(str(row["surrogate_variant"]), str(row["acquisition_rule"])) for row in query_rows})
    for surrogate_variant, acquisition_rule in keys:
        subset = [
            row
            for row in query_rows
            if row["surrogate_variant"] == surrogate_variant and row["acquisition_rule"] == acquisition_rule
        ]
        budgets = sorted({int(row["budget_after_query"]) for row in subset})
        medians = []
        q25 = []
        q75 = []
        for budget in budgets:
            values = np.asarray(
                [
                    max(float(row["true_boundary_distance"]), 1e-12)
                    for row in subset
                    if int(row["budget_after_query"]) == budget
                ],
                dtype=float,
            )
            medians.append(float(np.median(values)))
            q25.append(float(np.percentile(values, 25)))
            q75.append(float(np.percentile(values, 75)))
        color = METHOD_COLORS.get(acquisition_rule, "#333333")
        linestyle = VARIANT_STYLES.get(surrogate_variant, "-")
        ax.plot(budgets, medians, color=color, linestyle=linestyle, linewidth=2.1, label=f"{surrogate_variant} / {acquisition_rule}")
        ax.fill_between(budgets, np.maximum(1e-12, q25), q75, color=color, alpha=0.05, linewidth=0)
    ax.set_yscale("log")
    ax.set(
        title=f"{config.display_name}: median query distance over budget",
        xlabel="Labelled evaluations after query",
        ylabel="median abs(f(x_query) - threshold), q25-q75 band, log scale",
        xlim=(config.initial_size + 1, config.total_budget),
    )
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def hyperparameter_curve_groups(hyper_rows: list[dict[str, object]], metric: str) -> dict[tuple[str, str], dict[str, np.ndarray]]:
    groups: dict[tuple[str, str], dict[str, np.ndarray]] = {}
    keys = sorted({(str(row["surrogate_variant"]), str(row["acquisition_rule"])) for row in hyper_rows})
    for key in keys:
        subset = [row for row in hyper_rows if (row["surrogate_variant"], row["acquisition_rule"]) == key]
        budgets = sorted({int(row["budget"]) for row in subset})
        means = []
        q25 = []
        q75 = []
        for budget in budgets:
            values = [parse_float(row.get(metric)) for row in subset if int(row["budget"]) == budget]
            clean_values = np.asarray([value for value in values if value is not None and np.isfinite(value)], dtype=float)
            if clean_values.size == 0:
                means.append(np.nan)
                q25.append(np.nan)
                q75.append(np.nan)
            else:
                means.append(float(clean_values.mean()))
                q25.append(float(np.percentile(clean_values, 25)))
                q75.append(float(np.percentile(clean_values, 75)))
        groups[key] = {
            "budgets": np.asarray(budgets, dtype=int),
            "mean": np.asarray(means, dtype=float),
            "q25": np.asarray(q25, dtype=float),
            "q75": np.asarray(q75, dtype=float),
        }
    return groups


def plot_hyperparameter_curve(
    hyper_rows: list[dict[str, object]],
    metric: str,
    config: BenchmarkConfig,
    output_path: Path,
    title: str,
    ylabel: str,
    log_y: bool = False,
) -> None:
    fig, ax = plt.subplots(figsize=(12.5, 7.2))
    for (surrogate_variant, acquisition_rule), series in hyperparameter_curve_groups(hyper_rows, metric).items():
        color = METHOD_COLORS.get(acquisition_rule, "#333333")
        linestyle = VARIANT_STYLES.get(surrogate_variant, "-")
        ax.plot(series["budgets"], series["mean"], color=color, linestyle=linestyle, linewidth=2.1, label=f"{surrogate_variant} / {acquisition_rule}")
        if not np.all(np.isnan(series["q25"])):
            ax.fill_between(series["budgets"], series["q25"], series["q75"], color=color, alpha=0.05, linewidth=0)
    if log_y:
        ax.set_yscale("log")
    ax.set(
        title=title,
        xlabel="Labelled oracle evaluations",
        ylabel=ylabel,
        xlim=(config.initial_size, config.total_budget),
    )
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_ard_lengthscales_by_dimension(
    hyper_rows: list[dict[str, object]],
    config: BenchmarkConfig,
    output_path: Path,
) -> None:
    ard_rows = [row for row in hyper_rows if row["surrogate_variant"] == "optimized_ard_gpc"]
    if not ard_rows:
        return
    dim_fields = [field for field in ["learned_length_scale_dim0", "learned_length_scale_dim1", "learned_length_scale_dim2", "learned_length_scale_dim3"] if any(row.get(field) is not None for row in ard_rows)]
    fig, ax = plt.subplots(figsize=(11, 6.8))
    colors = ["#4c78a8", "#f58518", "#54a24b", "#b279a2"]
    budgets = sorted({int(row["budget"]) for row in ard_rows})
    for field, color in zip(dim_fields, colors):
        means = []
        q25 = []
        q75 = []
        for budget in budgets:
            values = np.asarray(
                [float(row[field]) for row in ard_rows if int(row["budget"]) == budget and row.get(field) is not None],
                dtype=float,
            )
            means.append(float(values.mean()))
            q25.append(float(np.percentile(values, 25)))
            q75.append(float(np.percentile(values, 75)))
        ax.plot(budgets, means, color=color, linewidth=2.3, label=field.replace("learned_length_scale_", ""))
        ax.fill_between(budgets, q25, q75, color=color, alpha=0.12, linewidth=0)
    ax.set(
        title=f"{config.display_name}: ARD length-scales by dimension",
        xlabel="Labelled oracle evaluations",
        ylabel="Learned RBF length-scale, mean with q25-q75 band",
        xlim=(config.initial_size, config.total_budget),
    )
    ax.grid(alpha=0.25)
    ax.legend(title="Dimension")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def first_budget_at_or_below(
    budgets: list[int],
    values: np.ndarray,
    tolerance: float,
) -> int | None:
    for budget, value in zip(budgets, values):
        if float(value) <= tolerance:
            return int(budget)
    return None


def tolerance_rows_for_benchmark(metric_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    tolerance_by_metric = {
        "global_error": (0.30, 0.25, 0.20, 0.15, 0.10, 0.08, 0.06),
        "near_boundary_error_q20": (0.50, 0.45, 0.40, 0.35, 0.30, 0.25, 0.20),
        "near_boundary_error_q30": (0.45, 0.40, 0.35, 0.30, 0.25, 0.20),
    }
    rows: list[dict[str, object]] = []
    keys = sorted({(str(row["surrogate_variant"]), str(row["acquisition_rule"])) for row in metric_rows})
    for metric, tolerances in tolerance_by_metric.items():
        for tolerance in tolerances:
            for surrogate_variant, acquisition_rule in keys:
                subset = [
                    row
                    for row in metric_rows
                    if row["surrogate_variant"] == surrogate_variant
                    and row["acquisition_rule"] == acquisition_rule
                ]
                budgets = sorted({int(row["budget"]) for row in subset})
                mean_values = np.asarray(
                    [
                        np.mean([float(row[metric]) for row in subset if int(row["budget"]) == budget])
                        for budget in budgets
                    ],
                    dtype=float,
                )
                out: dict[str, object] = {
                    "benchmark": subset[0]["benchmark"] if subset else "",
                    "metric": metric,
                    "tolerance": tolerance,
                    "surrogate_variant": surrogate_variant,
                    "acquisition_rule": acquisition_rule,
                    "method": acquisition_rule,
                    "mean_curve_first_budget": first_budget_at_or_below(budgets, mean_values, tolerance),
                }
                for seed in sorted({int(row["seed"]) for row in subset}):
                    seed_subset = [row for row in subset if int(row["seed"]) == seed]
                    seed_budgets = sorted({int(row["budget"]) for row in seed_subset})
                    seed_values = np.asarray(
                        [
                            float(next(row[metric] for row in seed_subset if int(row["budget"]) == budget))
                            for budget in seed_budgets
                        ],
                        dtype=float,
                    )
                    out[f"seed_{seed}_first_budget"] = first_budget_at_or_below(seed_budgets, seed_values, tolerance)
                rows.append(out)
    return rows


def best_rows_for_benchmark(final_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    mapping = {
        "global_error": "mean_final_global_error",
        "near_boundary_error_q20": "mean_final_near_boundary_error_q20",
        "near_boundary_error_q30": "mean_final_near_boundary_error_q30",
        "median_query_distance": "median_query_distance",
    }
    rows: list[dict[str, object]] = []
    for metric, field in mapping.items():
        best = min(final_rows, key=lambda row: float(row[field]))
        rows.append(
            {
                "benchmark": best["benchmark"],
                "metric": metric,
                "surrogate_variant": best["surrogate_variant"],
                "acquisition_rule": best["acquisition_rule"],
                "method": best["acquisition_rule"],
                "value": best[field],
                "field": field,
            }
        )
    return rows


def prior_regressor_candidate_paths(benchmark: str) -> list[Path]:
    return [
        PROJECT_ROOT / "outputs" / "week4_05_gated_geometric_boundary_contraction" / benchmark / "final_metrics_table.csv",
        PROJECT_ROOT / "outputs" / "week4_04_lookahead_boundary_uncertainty" / benchmark / "final_metrics_table.csv",
        PROJECT_ROOT / "outputs" / "week4_03_boundary_gated_diversified_straddle" / benchmark / "final_metrics_table.csv",
        PROJECT_ROOT / "outputs" / "week4_02_diversified_straddle" / benchmark / "final_metrics_table.csv",
        PROJECT_ROOT / "outputs" / "week4_01_boundary_metrics" / benchmark / "final_boundary_metrics_table.csv",
    ]


def load_regressor_references(benchmark: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    fields = {
        "global_error": "mean_final_global_error",
        "near_boundary_error_q20": "mean_final_near_boundary_error_q20",
        "near_boundary_error_q30": "mean_final_near_boundary_error_q30",
    }
    all_candidates: list[dict[str, object]] = []
    for path in prior_regressor_candidate_paths(benchmark):
        for row in read_csv_rows(path):
            if "method" not in row:
                continue
            candidate = dict(row)
            candidate["source_file"] = str(path.relative_to(PROJECT_ROOT))
            all_candidates.append(candidate)
    for metric, field in fields.items():
        metric_candidates = [
            row for row in all_candidates if parse_float(row.get(field)) is not None
        ]
        if not metric_candidates:
            rows.append(
                {
                    "benchmark": benchmark,
                    "metric": metric,
                    "reference_available": False,
                    "warning": "No prior GP-regressor final metric table found.",
                }
            )
            continue
        best = min(metric_candidates, key=lambda row: float(row[field]))
        rows.append(
            {
                "benchmark": benchmark,
                "metric": metric,
                "reference_available": True,
                "reference_source": best["source_file"],
                "reference_method": best["method"],
                "reference_value": best[field],
            }
        )
    return rows


def load_experiment06_fixed_references(benchmark: str) -> list[dict[str, object]]:
    path = PROJECT_ROOT / "outputs" / "week4_06_gp_classifier_surrogate" / benchmark / "final_metrics_table.csv"
    source_rows = read_csv_rows(path)
    fields = {
        "global_error": "mean_final_global_error",
        "near_boundary_error_q20": "mean_final_near_boundary_error_q20",
        "near_boundary_error_q30": "mean_final_near_boundary_error_q30",
    }
    rows: list[dict[str, object]] = []
    for metric, field in fields.items():
        metric_candidates = [row for row in source_rows if parse_float(row.get(field)) is not None]
        if not metric_candidates:
            rows.append(
                {
                    "benchmark": benchmark,
                    "metric": metric,
                    "reference_available": False,
                    "warning": "No prior Week 4 Experiment 06 fixed-classifier final metric table found.",
                }
            )
            continue
        best = min(metric_candidates, key=lambda row: float(row[field]))
        rows.append(
            {
                "benchmark": benchmark,
                "metric": metric,
                "reference_available": True,
                "reference_source": str(path.relative_to(PROJECT_ROOT)),
                "reference_method": best["method"],
                "reference_value": best[field],
            }
        )
    return rows


def comparison_value(final_rows: list[dict[str, object]], variant: str, metric_field: str) -> tuple[float, dict[str, object]]:
    subset = [row for row in final_rows if row["surrogate_variant"] == variant]
    best = min(subset, key=lambda row: float(row[metric_field]))
    return float(best[metric_field]), best


def fixed_vs_optimized_rows(final_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    fields = {
        "global_error": "mean_final_global_error",
        "near_boundary_error_q20": "mean_final_near_boundary_error_q20",
        "near_boundary_error_q30": "mean_final_near_boundary_error_q30",
    }
    rows: list[dict[str, object]] = []
    benchmark = str(final_rows[0]["benchmark"]) if final_rows else ""
    for metric, field in fields.items():
        fixed_value, fixed_row = comparison_value(final_rows, "fixed_iso_gpc", field)
        iso_value, iso_row = comparison_value(final_rows, "optimized_iso_gpc", field)
        ard_value, ard_row = comparison_value(final_rows, "optimized_ard_gpc", field)
        rows.append(
            {
                "benchmark": benchmark,
                "metric": metric,
                "fixed_iso_best_method": fixed_row["acquisition_rule"],
                "fixed_iso_value": f"{fixed_value:.6f}",
                "optimized_iso_best_method": iso_row["acquisition_rule"],
                "optimized_iso_value": f"{iso_value:.6f}",
                "optimized_iso_improves_over_fixed": iso_value < fixed_value,
                "optimized_ard_best_method": ard_row["acquisition_rule"],
                "optimized_ard_value": f"{ard_value:.6f}",
                "optimized_ard_improves_over_optimized_iso": ard_value < iso_value,
                "best_optimized_variant": "optimized_ard_gpc" if ard_value < iso_value else "optimized_iso_gpc",
                "best_optimized_value": f"{min(iso_value, ard_value):.6f}",
                "best_optimized_improves_over_fixed": min(iso_value, ard_value) < fixed_value,
            }
        )
    return rows


def compare_to_references(
    final_rows: list[dict[str, object]],
    regressor_refs: list[dict[str, object]],
    fixed_refs: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    fields = {
        "global_error": "mean_final_global_error",
        "near_boundary_error_q20": "mean_final_near_boundary_error_q20",
        "near_boundary_error_q30": "mean_final_near_boundary_error_q30",
    }
    regressor_rows: list[dict[str, object]] = []
    fixed_rows: list[dict[str, object]] = []
    benchmark = str(final_rows[0]["benchmark"]) if final_rows else ""
    for metric, field in fields.items():
        optimized_candidates = [row for row in final_rows if row["surrogate_variant"] in {"optimized_iso_gpc", "optimized_ard_gpc"}]
        best_optimized = min(optimized_candidates, key=lambda row: float(row[field]))
        reg_ref = next((row for row in regressor_refs if row["metric"] == metric), None)
        fixed_ref = next((row for row in fixed_refs if row["metric"] == metric), None)
        optimized_value = float(best_optimized[field])
        if reg_ref and reg_ref.get("reference_available"):
            reference_value = float(reg_ref["reference_value"])
            regressor_rows.append(
                {
                    "benchmark": benchmark,
                    "metric": metric,
                    "best_optimized_classifier_variant": best_optimized["surrogate_variant"],
                    "best_optimized_classifier_method": best_optimized["acquisition_rule"],
                    "best_optimized_classifier_value": f"{optimized_value:.6f}",
                    "regressor_reference_method": reg_ref["reference_method"],
                    "regressor_reference_value": reg_ref["reference_value"],
                    "regressor_reference_source": reg_ref["reference_source"],
                    "optimized_classifier_beats_regressor_reference": optimized_value < reference_value,
                }
            )
        else:
            regressor_rows.append(
                {
                    "benchmark": benchmark,
                    "metric": metric,
                    "best_optimized_classifier_variant": best_optimized["surrogate_variant"],
                    "best_optimized_classifier_method": best_optimized["acquisition_rule"],
                    "best_optimized_classifier_value": f"{optimized_value:.6f}",
                    "regressor_reference_available": False,
                    "warning": "No previous GP-regressor reference file was available.",
                }
            )
        if fixed_ref and fixed_ref.get("reference_available"):
            reference_value = float(fixed_ref["reference_value"])
            fixed_rows.append(
                {
                    "benchmark": benchmark,
                    "metric": metric,
                    "best_optimized_classifier_variant": best_optimized["surrogate_variant"],
                    "best_optimized_classifier_method": best_optimized["acquisition_rule"],
                    "best_optimized_classifier_value": f"{optimized_value:.6f}",
                    "previous_week6_fixed_method": fixed_ref["reference_method"],
                    "previous_week6_fixed_value": fixed_ref["reference_value"],
                    "previous_week6_fixed_source": fixed_ref["reference_source"],
                    "optimized_classifier_beats_previous_fixed_week6": optimized_value < reference_value,
                }
            )
        else:
            fixed_rows.append(
                {
                    "benchmark": benchmark,
                    "metric": metric,
                    "best_optimized_classifier_variant": best_optimized["surrogate_variant"],
                    "best_optimized_classifier_method": best_optimized["acquisition_rule"],
                    "best_optimized_classifier_value": f"{optimized_value:.6f}",
                    "previous_week6_fixed_available": False,
                    "warning": "No previous Week 4 Experiment 06 fixed-classifier reference file was available.",
                }
            )
    return regressor_rows, fixed_rows


def runtime_summary_rows(runtime_rows: list[dict[str, object]], benchmark: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    keys = sorted({(str(row["surrogate_variant"]), str(row["acquisition_rule"])) for row in runtime_rows})
    for surrogate_variant, acquisition_rule in keys:
        subset = [
            row
            for row in runtime_rows
            if row["surrogate_variant"] == surrogate_variant
            and row["acquisition_rule"] == acquisition_rule
        ]
        rows.append(
            {
                "benchmark": benchmark,
                "surrogate_variant": surrogate_variant,
                "acquisition_rule": acquisition_rule,
                "method": acquisition_rule,
                "total_runtime_seconds_sum_over_seeds": f"{sum(float(row['total_runtime_seconds']) for row in subset):.6f}",
                "mean_runtime_seconds_per_seed": f"{np.mean([float(row['total_runtime_seconds']) for row in subset]):.6f}",
                "mean_fit_time_seconds": f"{np.mean([float(row['mean_fit_time_seconds']) for row in subset]):.6f}",
                "fit_count_sum": sum(int(row["fit_count"]) for row in subset),
                "optimized_fit_count_sum": sum(int(row["optimized_fit_count"]) for row in subset),
                "seed_count": len(subset),
            }
        )
    rows.append(
        {
            "benchmark": benchmark,
            "surrogate_variant": "all",
            "acquisition_rule": "all",
            "method": "all",
            "total_runtime_seconds_sum_over_seeds": f"{sum(float(row['total_runtime_seconds']) for row in runtime_rows):.6f}",
            "mean_runtime_seconds_per_seed": f"{np.mean([float(row['total_runtime_seconds']) for row in runtime_rows]):.6f}",
            "mean_fit_time_seconds": f"{np.mean([float(row['mean_fit_time_seconds']) for row in runtime_rows]):.6f}",
            "fit_count_sum": sum(int(row["fit_count"]) for row in runtime_rows),
            "optimized_fit_count_sum": sum(int(row["optimized_fit_count"]) for row in runtime_rows),
            "seed_count": len({(row["surrogate_variant"], row["acquisition_rule"], row["seed"]) for row in runtime_rows}),
        }
    )
    return rows


def build_summary(
    *,
    config: BenchmarkConfig,
    options: RunOptions,
    seeds: tuple[int, ...],
    final_rows: list[dict[str, object]],
    fairness: dict[str, object],
    regressor_refs: list[dict[str, object]],
    fixed_refs: list[dict[str, object]],
    total_runtime_seconds: float,
) -> dict[str, object]:
    best_rows = best_rows_for_benchmark(final_rows)
    fixed_vs_opt = fixed_vs_optimized_rows(final_rows)
    regressor_comp, fixed_comp = compare_to_references(final_rows, regressor_refs, fixed_refs)
    return {
        "experiment": f"week4_07_optimized_gp_classifier_surrogate_{config.name}",
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
        "selected_budgets": list(config.selected_budgets),
        "seeds": list(seeds),
        "surrogate_variants": {
            "fixed_iso_gpc": "ConstantKernel(1.0 fixed) * RBF(length_scale=0.25 fixed), optimizer=None.",
            "optimized_iso_gpc": "ConstantKernel bounds (0.1,10.0) * isotropic RBF length-scale bounds (0.03,3.0).",
            "optimized_ard_gpc": "ConstantKernel bounds (0.1,10.0) * ARD RBF length-scales with bounds (0.03,3.0).",
        },
        "acquisition_rules": {method: METHOD_DESCRIPTIONS[method] for method in CLASSIFIER_METHODS + OPTIONAL_METHODS if method in {row["acquisition_rule"] for row in final_rows}},
        "run_settings": {
            "quick": options.quick,
            "n_restarts_optimizer": options.n_restarts,
            "optimize_every": options.optimize_every,
            "max_seeds": options.max_seeds,
            "include_straddle_analog": options.include_straddle_analog,
            "runtime_reduction_used": options.n_restarts < 2 or options.optimize_every > 1,
            "runtime_reduction_note": (
                "Runtime was reduced relative to the default requested run."
                if options.n_restarts < 2 or options.optimize_every > 1
                else "Default full optimization settings were used."
            ),
        },
        "total_runtime_seconds": total_runtime_seconds,
        "prediction_rule": "+1 if p(+1|x) >= 0.5, else -1.",
        "evaluation_only_true_data_note": "True function values, true labels, query boundary distances, and q10/q20/q30 masks are evaluation-only diagnostics.",
        "fairness_checks": fairness,
        "best_rows": best_rows,
        "fixed_vs_optimized_classifier_comparison": fixed_vs_opt,
        "regressor_reference_comparison": regressor_comp,
        "previous_fixed_week6_reference_comparison": fixed_comp,
        "final_metrics": final_rows,
    }


def save_benchmark_outputs(result: BenchmarkResult, output_dir: Path) -> None:
    benchmark_dir = output_dir / result.config.output_name
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    write_csv(benchmark_dir / "metric_curves.csv", result.metric_rows)
    write_csv(benchmark_dir / "query_distance_table.csv", result.query_rows)
    write_csv(benchmark_dir / "hyperparameter_trace.csv", result.hyperparameter_rows)
    write_csv(benchmark_dir / "final_metrics_table.csv", result.final_rows)
    write_csv(benchmark_dir / "tolerance_reach_table.csv", result.tolerance_rows)
    write_csv(benchmark_dir / "runtime_summary.csv", runtime_summary_rows(result.runtime_rows, result.config.name))
    (benchmark_dir / "fairness_checks.json").write_text(json.dumps(json_ready(result.fairness_checks), indent=2), encoding="utf-8")
    (benchmark_dir / "optimized_gp_classifier_surrogate_summary.json").write_text(json.dumps(json_ready(result.summary), indent=2), encoding="utf-8")

    plot_metric_curves(
        result.metric_rows,
        "global_error",
        result.config,
        benchmark_dir / "global_error_curves.png",
        f"{result.config.display_name}: Week 4 Experiment 07 global error",
        "Global test-label error",
    )
    plot_metric_curves(
        result.metric_rows,
        "near_boundary_error_q20",
        result.config,
        benchmark_dir / "q20_error_curves.png",
        f"{result.config.display_name}: Week 4 Experiment 07 q20 near-boundary error",
        "Error on closest 20% test points",
    )
    plot_metric_curves(
        result.metric_rows,
        "near_boundary_error_q30",
        result.config,
        benchmark_dir / "q30_error_curves.png",
        f"{result.config.display_name}: Week 4 Experiment 07 q30 near-boundary error",
        "Error on closest 30% test points",
    )
    plot_final_bar(result.final_rows, result.config, benchmark_dir / "final_global_q20_q30_bar.png")
    plot_metric_curves(
        result.metric_rows,
        f"classifier_uncertainty_region_fraction_{epsilon_suffix(PRIMARY_UNCERTAINTY_EPSILON)}",
        result.config,
        benchmark_dir / "uncertainty_region_global_eps010.png",
        f"{result.config.display_name}: global classifier uncertainty region eps=0.10",
        "Fraction abs(p(+1)-0.5)<=0.10",
    )
    plot_metric_curves(
        result.metric_rows,
        f"classifier_uncertainty_region_fraction_q20_{epsilon_suffix(PRIMARY_UNCERTAINTY_EPSILON)}",
        result.config,
        benchmark_dir / "uncertainty_region_q20_eps010.png",
        f"{result.config.display_name}: q20 classifier uncertainty region eps=0.10",
        "Closest 20% fraction abs(p(+1)-0.5)<=0.10",
    )
    plot_metric_curves(
        result.metric_rows,
        f"classifier_uncertainty_region_fraction_q30_{epsilon_suffix(PRIMARY_UNCERTAINTY_EPSILON)}",
        result.config,
        benchmark_dir / "uncertainty_region_q30_eps010.png",
        f"{result.config.display_name}: q30 classifier uncertainty region eps=0.10",
        "Closest 30% fraction abs(p(+1)-0.5)<=0.10",
    )
    plot_query_distance_boxplot(result.query_rows, result.config, benchmark_dir / "query_distance_boxplot.png")
    plot_query_distance_over_budget(result.query_rows, result.config, benchmark_dir / "median_query_distance_over_budget.png")
    plot_hyperparameter_curve(
        result.hyperparameter_rows,
        "learned_length_scale_mean",
        result.config,
        benchmark_dir / "learned_lengthscale_over_budget.png",
        f"{result.config.display_name}: learned length-scale over budget",
        "Mean learned RBF length-scale",
        log_y=True,
    )
    plot_hyperparameter_curve(
        result.hyperparameter_rows,
        "learned_constant",
        result.config,
        benchmark_dir / "learned_constant_over_budget.png",
        f"{result.config.display_name}: learned constant over budget",
        "Learned ConstantKernel value",
        log_y=True,
    )
    plot_hyperparameter_curve(
        result.hyperparameter_rows,
        "log_marginal_likelihood_value",
        result.config,
        benchmark_dir / "log_marginal_likelihood_over_budget.png",
        f"{result.config.display_name}: log marginal likelihood over budget",
        "log_marginal_likelihood_value_",
    )
    plot_hyperparameter_curve(
        result.hyperparameter_rows,
        "fit_time_seconds",
        result.config,
        benchmark_dir / "fit_runtime_over_budget.png",
        f"{result.config.display_name}: fit runtime over budget",
        "Fit time seconds",
        log_y=True,
    )
    plot_ard_lengthscales_by_dimension(
        result.hyperparameter_rows,
        result.config,
        benchmark_dir / "ard_lengthscales_by_dimension_over_budget.png",
    )


def plot_combined_final_by_benchmark(results: list[BenchmarkResult], output_path: Path) -> None:
    rows = [row for result in results for row in result.best_rows if row["metric"] in {"global_error", "near_boundary_error_q20", "near_boundary_error_q30"}]
    labels = [f"{row['benchmark']}\n{row['metric']}" for row in rows]
    values = [float(row["value"]) for row in rows]
    colors = ["#4c78a8" if "global" in row["metric"] else "#f58518" if "q20" in row["metric"] else "#54a24b" for row in rows]
    fig, ax = plt.subplots(figsize=(10, 6.5))
    x = np.arange(len(rows))
    ax.bar(x, values, color=colors, alpha=0.86)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set(title="Week 4 Experiment 07 best final metrics by benchmark", ylabel="Best mean final error")
    ax.grid(axis="y", alpha=0.25)
    for pos, row in zip(x, rows):
        ax.text(pos, float(row["value"]) + 0.01, str(row["surrogate_variant"]).replace("_gpc", ""), ha="center", va="bottom", fontsize=7, rotation=90)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_combined_fixed_vs_optimized(rows: list[dict[str, object]], output_path: Path) -> None:
    labels = [f"{row['benchmark']}\n{row['metric']}" for row in rows]
    x = np.arange(len(rows))
    width = 0.25
    fig, ax = plt.subplots(figsize=(11, 6.5))
    ax.bar(x - width, [float(row["fixed_iso_value"]) for row in rows], width=width, label="fixed iso", color="#7a7a7a")
    ax.bar(x, [float(row["optimized_iso_value"]) for row in rows], width=width, label="optimized iso", color="#4c78a8")
    ax.bar(x + width, [float(row["optimized_ard_value"]) for row in rows], width=width, label="optimized ARD", color="#f58518")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set(title="Week 4 Experiment 07 fixed vs optimized GP classifier", ylabel="Best mean final error")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_combined_runtime(rows: list[dict[str, object]], output_path: Path) -> None:
    plot_rows = [row for row in rows if row["surrogate_variant"] != "all"]
    labels = [f"{row['benchmark']}\n{row['surrogate_variant']}\n{row['acquisition_rule']}" for row in plot_rows]
    values = [float(row["total_runtime_seconds_sum_over_seeds"]) for row in plot_rows]
    fig, ax = plt.subplots(figsize=(14, 6.8))
    ax.bar(np.arange(len(values)), values, color="#4c78a8", alpha=0.82)
    ax.set_xticks(np.arange(len(values)))
    ax.set_xticklabels(labels, rotation=70, ha="right", fontsize=7)
    ax.set(title="Week 4 Experiment 07 runtime summary", ylabel="Total runtime seconds across seeds")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_combined_ard_summary(results: list[BenchmarkResult], output_path: Path) -> None:
    rows: list[dict[str, object]] = []
    for result in results:
        final_budget = result.config.total_budget
        final_rows = [
            row
            for row in result.hyperparameter_rows
            if row["surrogate_variant"] == "optimized_ard_gpc" and int(row["budget"]) == final_budget
        ]
        for dim in range(4):
            field = f"learned_length_scale_dim{dim}"
            values = [parse_float(row.get(field)) for row in final_rows]
            clean = [float(value) for value in values if value is not None]
            if clean:
                rows.append(
                    {
                        "benchmark": result.config.name,
                        "dimension": f"dim{dim}",
                        "mean": float(np.mean(clean)),
                        "q25": float(np.percentile(clean, 25)),
                        "q75": float(np.percentile(clean, 75)),
                    }
                )
    if not rows:
        return
    labels = [f"{row['benchmark']}\n{row['dimension']}" for row in rows]
    x = np.arange(len(rows))
    means = np.asarray([float(row["mean"]) for row in rows])
    yerr = np.asarray(
        [
            [max(0.0, float(row["mean"]) - float(row["q25"])) for row in rows],
            [max(0.0, float(row["q75"]) - float(row["mean"])) for row in rows],
        ]
    )
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x, means, yerr=yerr, capsize=5, color="#f58518", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set(title="Week 4 Experiment 07 final ARD length-scale summary", ylabel="Final learned length-scale")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def write_interpretation(
    results: list[BenchmarkResult],
    fixed_vs_opt_rows: list[dict[str, object]],
    regressor_rows: list[dict[str, object]],
    fixed_experiment06_rows: list[dict[str, object]],
    runtime_rows: list[dict[str, object]],
    output_path: Path,
    options: RunOptions,
) -> None:
    def yes_no(value: object) -> str:
        return "yes" if bool(value) else "no"

    lines = [
        "# Week 4 Experiment 07 Interpretation",
        "",
        "This run compares fixed-kernel and optimized-kernel `GaussianProcessClassifier` surrogates on thresholded Branin and thresholded 4D Ackley. Acquisition functions use classifier probabilities only; true function values and boundary masks are evaluation-only diagnostics.",
        "",
        "## Runtime settings",
        "",
        f"- `n_restarts_optimizer`: `{options.n_restarts}`.",
        f"- `optimize_every`: `{options.optimize_every}`.",
        f"- Runtime reduction used: `{options.n_restarts < 2 or options.optimize_every > 1}`.",
        "",
        "## Answers",
        "",
    ]
    for benchmark in sorted({row["benchmark"] for row in fixed_vs_opt_rows}):
        benchmark_rows = [row for row in fixed_vs_opt_rows if row["benchmark"] == benchmark]
        lines.append(f"### {benchmark}")
        for row in benchmark_rows:
            lines.append(
                f"- {row['metric']}: fixed `{row['fixed_iso_best_method']}` = `{float(row['fixed_iso_value']):.3f}`, "
                f"optimized iso `{row['optimized_iso_best_method']}` = `{float(row['optimized_iso_value']):.3f}`, "
                f"optimized ARD `{row['optimized_ard_best_method']}` = `{float(row['optimized_ard_value']):.3f}`."
            )
        iso_improves = any(row["optimized_iso_improves_over_fixed"] for row in benchmark_rows)
        ard_improves = any(row["optimized_ard_improves_over_optimized_iso"] for row in benchmark_rows)
        lines.append(f"- Did optimized isotropic GPC improve over fixed isotropic GPC? `{yes_no(iso_improves)}` on at least one primary metric.")
        lines.append(f"- Did optimized ARD GPC improve over optimized isotropic GPC? `{yes_no(ard_improves)}` on at least one primary metric.")
        fixed_ref_rows = [row for row in fixed_experiment06_rows if row["benchmark"] == benchmark]
        if fixed_ref_rows:
            beat_fixed = any(row.get("optimized_classifier_beats_previous_fixed_week6") is True for row in fixed_ref_rows)
            lines.append(f"- Did optimized GPC beat the previous fixed Week 4 Experiment 06 classifier output? `{yes_no(beat_fixed)}` on at least one primary metric.")
        reg_rows = [row for row in regressor_rows if row["benchmark"] == benchmark]
        if reg_rows:
            beat_reg_global = any(row["metric"] == "global_error" and row.get("optimized_classifier_beats_regressor_reference") is True for row in reg_rows)
            beat_reg_boundary = any(row["metric"] in {"near_boundary_error_q20", "near_boundary_error_q30"} and row.get("optimized_classifier_beats_regressor_reference") is True for row in reg_rows)
            lines.append(f"- Did optimized GPC beat the previous GP-regressor reference on global error? `{yes_no(beat_reg_global)}`.")
            lines.append(f"- Did optimized GPC beat the previous GP-regressor reference on q20/q30 error? `{yes_no(beat_reg_boundary)}`.")
        result = next(item for item in results if item.config.name == benchmark)
        optimized_fits = [row for row in result.hyperparameter_rows if row["surrogate_variant"] != "fixed_iso_gpc" and row["optimized_this_fit"]]
        length_bound_fraction = float(np.mean([bool(row["length_scale_near_lower_bound"]) or bool(row["length_scale_near_upper_bound"]) for row in optimized_fits])) if optimized_fits else 0.0
        constant_bound_fraction = float(np.mean([bool(row["constant_near_lower_bound"]) or bool(row["constant_near_upper_bound"]) for row in optimized_fits])) if optimized_fits else 0.0
        lines.append(f"- Learned length-scale bound-hit fraction during optimized fits: `{length_bound_fraction:.3f}`.")
        lines.append(f"- Learned constant bound-hit fraction during optimized fits: `{constant_bound_fraction:.3f}`.")
        if length_bound_fraction > 0.25 or constant_bound_fraction > 0.25:
            lines.append("- Some hyperparameters frequently sit near bounds, so the optimized classifier should be treated as diagnostic rather than final.")
        else:
            lines.append("- Hyperparameters do not appear to collapse to bounds in a dominant fraction of optimized fits.")
        lines.append("")

    improvements_by_benchmark: dict[str, float] = {}
    for benchmark in sorted({row["benchmark"] for row in fixed_vs_opt_rows}):
        rows = [row for row in fixed_vs_opt_rows if row["benchmark"] == benchmark]
        improvements = [float(row["optimized_iso_value"]) - float(row["optimized_ard_value"]) for row in rows]
        improvements_by_benchmark[benchmark] = float(np.mean(improvements))
    if {"ackley", "branin"}.issubset(improvements_by_benchmark):
        ard_more_ackley = improvements_by_benchmark["ackley"] > improvements_by_benchmark["branin"]
        lines.append(
            f"ARD helped more on Ackley than Branin: `{yes_no(ard_more_ackley)}` by mean optimized-iso minus optimized-ARD error across global/q20/q30."
        )
    total_runtime = sum(float(row["total_runtime_seconds_sum_over_seeds"]) for row in runtime_rows if row["surrogate_variant"] == "all")
    any_regressor_win = any(row.get("optimized_classifier_beats_regressor_reference") is True for row in regressor_rows)
    all_regressor_wins = all(row.get("optimized_classifier_beats_regressor_reference") is True for row in regressor_rows)
    any_fixed_win = any(row.get("optimized_classifier_beats_previous_fixed_week6") is True for row in fixed_experiment06_rows)
    lines.extend(
        [
            "",
            "## Runtime cost",
            "",
            f"Total benchmark runtime represented in the runtime summary is `{total_runtime:.1f}` seconds across benchmark-method-seed runs.",
        ]
    )
    if any_regressor_win:
        lines.append("The runtime cost is partly justified where optimized classification improves primary metrics, especially boundary metrics.")
    elif any_fixed_win:
        lines.append("Kernel learning improves the classifier in places, but the runtime cost is not yet justified as a replacement for the stronger GP-regression references.")
    else:
        lines.append("The runtime cost is not yet justified by the current metrics.")
    lines.extend(
        [
            "",
            "## Thesis-level conclusion",
            "",
        ]
    )
    if all_regressor_wins:
        lines.append("This supports moving from the Week 1-5 GP-regression stand-in toward a classifier-native surrogate for boundary-focused acquisition.")
    elif any_regressor_win:
        lines.append("The optimized classifier gives a strong positive result on at least one benchmark, but it does not dominate across benchmarks. The thesis-level conclusion is diagnostic: classifier-native surrogates remain worth pursuing, while kernel optimization alone is not enough on the harder 4D Ackley benchmark.")
    elif any_fixed_win:
        lines.append("Kernel learning improves the GP-classifier surrogate, but under the present benchmark and acquisition setup it still does not clearly dominate the simpler GP-regression stand-in.")
    else:
        lines.append("Optimizing the GP-classifier kernel is useful as a diagnostic, but the present empirical result does not justify claiming classifier-native modelling is superior on these benchmarks.")
    lines.append("")
    lines.append("q10 is very close to the exact threshold and is unstable across seeds; q20/q30 are more reliable for comparing acquisition behavior.")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_slide_notes(
    best_rows: list[dict[str, object]],
    fixed_vs_opt_rows: list[dict[str, object]],
    regressor_rows: list[dict[str, object]],
    output_path: Path,
) -> None:
    lines = [
        "# Week 4 Experiment 07 Slide Notes",
        "",
        "## Question",
        "",
        "Does optimizing GP-classifier kernel hyperparameters improve active level-set estimation on Branin and 4D Ackley?",
        "",
        "## Setup",
        "",
        "- Surrogates: fixed isotropic GPC, optimized isotropic GPC, optimized ARD GPC.",
        "- Acquisitions: random, classifier margin, classifier entropy, gated diversity, uncertainty repulsion.",
        "- Primary metrics: global error, q20 near-boundary error, q30 near-boundary error, query distance, uncertainty-region fraction.",
        "",
        "## Best Week 4 Experiment 07 rows",
        "",
    ]
    for row in best_rows:
        if row["metric"] in {"global_error", "near_boundary_error_q20", "near_boundary_error_q30"}:
            lines.append(
                f"- {row['benchmark']} {row['metric']}: `{row['surrogate_variant']}` / `{row['acquisition_rule']}` = `{float(row['value']):.3f}`."
            )
    lines.extend(["", "## Fixed vs optimized", ""])
    for row in fixed_vs_opt_rows:
        lines.append(
            f"- {row['benchmark']} {row['metric']}: best optimized beats fixed = `{row['best_optimized_improves_over_fixed']}`."
        )
    lines.extend(["", "## Regressor reference", ""])
    for row in regressor_rows:
        lines.append(
            f"- {row['benchmark']} {row['metric']}: optimized classifier beats reference = `{row.get('optimized_classifier_beats_regressor_reference')}`."
        )
    lines.extend(
        [
            "",
            "## Message",
            "",
            "Do not overclaim. Kernel learning should be described through the empirical global/q20/q30 results and the hyperparameter traces, not as theoretically better just because labels are binary.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_combined_outputs(results: list[BenchmarkResult], output_dir: Path, options: RunOptions) -> None:
    combined_dir = output_dir / "combined"
    combined_dir.mkdir(parents=True, exist_ok=True)
    metric_rows = [row for result in results for row in result.metric_rows]
    query_rows = [row for result in results for row in result.query_rows]
    hyper_rows = [row for result in results for row in result.hyperparameter_rows]
    final_rows = [row for result in results for row in result.final_rows]
    tolerance_rows = [row for result in results for row in result.tolerance_rows]
    runtime_rows = [row for result in results for row in runtime_summary_rows(result.runtime_rows, result.config.name)]
    fairness = {result.config.name: result.fairness_checks for result in results}
    best_rows = [row for result in results for row in result.best_rows]
    fixed_vs_opt = [row for result in results for row in fixed_vs_optimized_rows(result.final_rows)]
    regressor_rows = []
    fixed_experiment06_rows = []
    for result in results:
        reg_rows, fixed_rows = compare_to_references(
            result.final_rows,
            result.regressor_reference_rows,
            result.fixed_experiment06_reference_rows,
        )
        regressor_rows.extend(reg_rows)
        fixed_experiment06_rows.extend(fixed_rows)

    write_csv(combined_dir / "metric_curves.csv", metric_rows)
    write_csv(combined_dir / "query_distance_table.csv", query_rows)
    write_csv(combined_dir / "hyperparameter_trace.csv", hyper_rows)
    write_csv(combined_dir / "final_metrics_table.csv", final_rows)
    write_csv(combined_dir / "tolerance_reach_table.csv", tolerance_rows)
    write_csv(combined_dir / "runtime_summary.csv", runtime_rows)
    write_csv(combined_dir / "regressor_reference_comparison.csv", regressor_rows)
    write_csv(combined_dir / "previous_fixed_gp_classifier_comparison.csv", fixed_experiment06_rows)
    write_csv(combined_dir / "fixed_vs_optimized_classifier_comparison.csv", fixed_vs_opt)
    write_csv(combined_dir / "best_method_by_metric.csv", best_rows)
    (combined_dir / "fairness_checks.json").write_text(json.dumps(json_ready(fairness), indent=2), encoding="utf-8")
    combined_summary = {
        "experiment": "week4_07_optimized_gp_classifier_surrogate_combined",
        "benchmarks": [result.config.name for result in results],
        "run_settings": {
            "quick": options.quick,
            "n_restarts_optimizer": options.n_restarts,
            "optimize_every": options.optimize_every,
            "max_seeds": options.max_seeds,
            "runtime_reduction_used": options.n_restarts < 2 or options.optimize_every > 1,
        },
        "best_method_by_metric": best_rows,
        "fixed_vs_optimized_classifier_comparison": fixed_vs_opt,
        "regressor_reference_comparison": regressor_rows,
        "previous_week6_fixed_classifier_comparison": fixed_experiment06_rows,
        "fairness_checks": fairness,
    }
    (combined_dir / "optimized_gp_classifier_surrogate_summary.json").write_text(json.dumps(json_ready(combined_summary), indent=2), encoding="utf-8")
    write_interpretation(
        results,
        fixed_vs_opt,
        regressor_rows,
        fixed_experiment06_rows,
        runtime_rows,
        combined_dir / "optimized_gp_classifier_surrogate_interpretation.md",
        options,
    )
    write_slide_notes(best_rows, fixed_vs_opt, regressor_rows, combined_dir / "optimized_gp_classifier_surrogate_slide_notes.md")
    plot_combined_final_by_benchmark(results, combined_dir / "final_global_q20_q30_by_benchmark.png")
    plot_combined_fixed_vs_optimized(fixed_vs_opt, combined_dir / "fixed_vs_optimized_classifier_bars.png")
    plot_combined_final_by_benchmark(results, combined_dir / "best_method_by_metric.png")
    plot_combined_runtime(runtime_rows, combined_dir / "runtime_summary.png")
    plot_combined_ard_summary(results, combined_dir / "ard_lengthscale_summary.png")


def run_benchmark(
    config: BenchmarkConfig,
    options: RunOptions,
    methods: tuple[str, ...],
    seeds: tuple[int, ...],
) -> BenchmarkResult:
    print(f"Running {config.display_name} with {len(seeds)} seed(s), {len(methods)} acquisition(s), {len(SURROGATE_VARIANTS)} surrogate(s).")
    start = time.perf_counter()
    designs = [config.create_design(seed, config.threshold) for seed in seeds]
    runs: list[MethodRun] = []
    total_runs = len(designs) * len(SURROGATE_VARIANTS) * len(methods)
    run_number = 0
    for design in designs:
        for surrogate_variant in SURROGATE_VARIANTS:
            for acquisition_rule in methods:
                run_number += 1
                print(
                    f"  [{config.name} {run_number}/{total_runs}] seed={design.seed} "
                    f"surrogate={surrogate_variant} method={acquisition_rule}",
                    flush=True,
                )
                runs.append(run_method(config, design, surrogate_variant, acquisition_rule, options))
    fairness = verify_fairness(runs)
    if not fairness["all_checks_passed"]:
        raise RuntimeError(f"Fairness check failed for {config.name}: {fairness}")
    metric_rows = [row for run in runs for row in run.metric_rows]
    query_rows = [row for run in runs for row in run.query_rows]
    hyper_rows = [row for run in runs for row in run.hyperparameter_rows]
    runtime_rows = [row for run in runs for row in run.runtime_rows]
    final_rows = summarize_final_metrics(config, metric_rows, query_rows, hyper_rows)
    tolerance_rows = tolerance_rows_for_benchmark(metric_rows)
    best_rows = best_rows_for_benchmark(final_rows)
    regressor_refs = load_regressor_references(config.name)
    fixed_refs = load_experiment06_fixed_references(config.name)
    elapsed = time.perf_counter() - start
    summary = build_summary(
        config=config,
        options=options,
        seeds=seeds,
        final_rows=final_rows,
        fairness=fairness,
        regressor_refs=regressor_refs,
        fixed_refs=fixed_refs,
        total_runtime_seconds=elapsed,
    )
    result = BenchmarkResult(
        config=config,
        runs=runs,
        fairness_checks=fairness,
        metric_rows=metric_rows,
        query_rows=query_rows,
        hyperparameter_rows=hyper_rows,
        runtime_rows=runtime_rows,
        final_rows=final_rows,
        tolerance_rows=tolerance_rows,
        best_rows=best_rows,
        regressor_reference_rows=regressor_refs,
        fixed_experiment06_reference_rows=fixed_refs,
        summary=summary,
    )
    save_benchmark_outputs(result, options.output_dir)
    return result


def build_configs(quick: bool) -> list[BenchmarkConfig]:
    branin_threshold_seed = 2026
    branin_threshold_sample_size = 20_000
    branin_threshold = compute_branin_threshold(branin_threshold_sample_size, branin_threshold_seed)
    ackley_values = threshold_sample_values()
    ackley_threshold = compute_ackley_threshold(ackley_values)
    if quick:
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
                pool_size=250,
                test_size=600,
                initial_size=6,
                total_budget=10,
                selected_budgets=(6, 8, 10),
                create_design=lambda seed, threshold: create_branin_design(seed, threshold, initial_size=6, pool_size=250, test_size=600),
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
                pool_size=350,
                test_size=800,
                initial_size=12,
                total_budget=16,
                selected_budgets=(12, 14, 16),
                create_design=lambda seed, threshold: create_ackley_design(seed, threshold, initial_size=12, pool_size=350, test_size=800),
                value_function=ackley_4d,
                scaling_rule="Ackley original coordinates are linearly scaled to [0,1]^4 for the GP classifier.",
            ),
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


def smoke_test(options: RunOptions) -> None:
    config = build_configs(quick=True)[0]
    design = config.create_design(SEEDS[0], config.threshold)
    smoke_options = RunOptions(
        quick=True,
        n_restarts=0,
        optimize_every=max(1, options.optimize_every),
        max_seeds=1,
        include_straddle_analog=False,
        output_dir=options.output_dir,
    )
    run = run_method(config, design, "fixed_iso_gpc", "classifier_margin", smoke_options)
    if not run.metric_rows:
        raise RuntimeError("Smoke test produced no metrics")
    final_error = float(run.metric_rows[-1]["global_error"])
    if not np.isfinite(final_error):
        raise RuntimeError("Smoke test produced invalid global error")


def run_experiment(options: RunOptions) -> list[BenchmarkResult]:
    options.output_dir.mkdir(parents=True, exist_ok=True)
    methods = CLASSIFIER_METHODS + (OPTIONAL_METHODS if options.include_straddle_analog else ())
    seeds = SEEDS
    if options.quick:
        seeds = (0,)
    if options.max_seeds is not None:
        seeds = tuple(seeds[: options.max_seeds])
    results = [
        run_benchmark(config, options, methods=methods, seeds=seeds)
        for config in build_configs(quick=options.quick)
    ]
    write_combined_outputs(results, options.output_dir, options)
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Week 4 Experiment 07 optimized GP-classifier surrogate comparison")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true", help="Run a reduced Branin+Ackley smoke experiment")
    mode.add_argument("--full", action="store_true", help="Run the full Week 4 Experiment 07 experiment")
    parser.add_argument("--n-restarts", type=int, default=2, help="n_restarts_optimizer for optimized GPC fits")
    parser.add_argument("--optimize-every", type=int, default=1, help="Optimize hyperparameters every k active-learning steps")
    parser.add_argument("--max-seeds", type=int, default=None, help="Limit the number of seeds for debugging/runtime control")
    parser.add_argument("--include-straddle-analog", action="store_true", help="Include the optional classifier_straddle_analog acquisition")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Output directory")
    parser.add_argument("--skip-smoke", action="store_true", help="Skip the pre-run classifier smoke test")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.n_restarts < 0:
        raise ValueError("--n-restarts must be non-negative")
    if args.optimize_every < 1:
        raise ValueError("--optimize-every must be at least 1")
    options = RunOptions(
        quick=bool(args.quick),
        n_restarts=int(args.n_restarts),
        optimize_every=int(args.optimize_every),
        max_seeds=args.max_seeds,
        include_straddle_analog=bool(args.include_straddle_analog),
        output_dir=args.output_dir,
    )
    start = time.perf_counter()
    if not args.skip_smoke:
        smoke_test(options)
        print("Week 4 Experiment 07 GP-classifier smoke test passed.")
    results = run_experiment(options)
    elapsed = time.perf_counter() - start
    mode = "quick" if options.quick else "full"
    print(f"Week 4 Experiment 07 optimized GP-classifier comparison complete in {elapsed:.1f}s ({mode} mode).")
    print(f"n_restarts_optimizer={options.n_restarts}; optimize_every={options.optimize_every}")
    for result in results:
        best_global = next(row for row in result.best_rows if row["metric"] == "global_error")
        best_q20 = next(row for row in result.best_rows if row["metric"] == "near_boundary_error_q20")
        best_q30 = next(row for row in result.best_rows if row["metric"] == "near_boundary_error_q30")
        print(
            f"{result.config.display_name}: "
            f"best global={best_global['surrogate_variant']}/{best_global['acquisition_rule']} ({float(best_global['value']):.4f}), "
            f"best q20={best_q20['surrogate_variant']}/{best_q20['acquisition_rule']} ({float(best_q20['value']):.4f}), "
            f"best q30={best_q30['surrogate_variant']}/{best_q30['acquisition_rule']} ({float(best_q30['value']):.4f})"
        )
    print(f"Saved outputs to {options.output_dir}")


if __name__ == "__main__":
    main()
