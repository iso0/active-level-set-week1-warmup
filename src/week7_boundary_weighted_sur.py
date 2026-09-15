"""Week 7 boundary-weighted IVR / Bernoulli SUR benchmark.

This experiment adds a third deterministic benchmark, thresholded 4D Hartmann,
and tests boundary-weighted integrated variance reduction plus Bernoulli
stepwise uncertainty reduction against the strongest existing pointwise rules.

The main SUR/IVR methods use the existing GaussianProcessRegressor stand-in.
The GP-regressor SUR fantasy step uses the exact fixed-kernel Gaussian posterior
rank-one update. That is algebraically equivalent to refitting the posterior
with the current kernel hyperparameters held fixed, and is much faster than
calling sklearn for every fantasy label.
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
from scipy.linalg import solve_triangular
from scipy.special import ndtr
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.gaussian_process.kernels import ConstantKernel, RBF

from src.acquisition_rules import METHOD_ORDER, choose_next_index
from src.acquisition_rules import rng_for_method as branin_rng_for_method
from src.branin_week1 import branin, compute_threshold as compute_branin_threshold
from src.branin_week1 import fit_gp, random_two_class_initial_design
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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "week7_boundary_weighted_sur"
SEEDS = (0, 1, 2, 3, 4)
BOUNDARY_QUANTILES = (10, 20, 30)
UNCERTAINTY_MULTIPLIER = 1.96
PRIMARY_CLASSIFIER_EPSILON = 0.10
GPR_PROBABILITY_EPS = 1e-9
POSTERIOR_NOISE_EPS = 1e-9

GPR_BASELINE_METHODS = (
    "random",
    "smallest_abs_mu",
    "straddle",
    "randomized_straddle",
    "expected_feasibility",
    "boundary_gated_diversified_straddle",
)
GPR_NEW_METHODS = (
    "gpr_boundary_weighted_ivr",
    "gpr_bernoulli_sur_refit",
)
GPC_BASELINE_METHODS = (
    "classifier_margin",
    "classifier_entropy",
    "classifier_uncertainty_repulsion",
)
GPC_SUR_METHODS = ("gpc_bernoulli_sur_refit",)

GPC_LENGTH_SCALE = 0.25
GPC_MAX_ITER_PREDICT = 100
CLASSIFIER_GATE_FRACTION = 0.10
CLASSIFIER_MIN_SHORTLIST_SIZE = 25
CLASSIFIER_REPULSION_BANDWIDTH = 0.15

BOUNDARY_GATED_BETA = 0.50
BOUNDARY_GATED_GATE_FRACTION = 0.10
BOUNDARY_GATED_MIN_SHORTLIST_SIZE = 25
IVR_GATE_FRACTION = 0.30
IVR_MIN_GATE_SIZE = 1000

HARTMANN_THRESHOLD_SEED = 2026
HARTMANN_THRESHOLD_SAMPLE_SIZE = 100_000
HARTMANN_THRESHOLD_PERCENTILE = 50.0

METHOD_COLORS = {
    "random": "#7a7a7a",
    "smallest_abs_mu": "#2b6cb0",
    "straddle": "#0f8b61",
    "randomized_straddle": "#b7791f",
    "expected_feasibility": "#9f1239",
    "boundary_gated_diversified_straddle": "#d95f02",
    "gpr_boundary_weighted_ivr": "#1f9eaa",
    "gpr_bernoulli_sur_refit": "#005f73",
    "classifier_margin": "#6a3d9a",
    "classifier_entropy": "#b279a2",
    "classifier_uncertainty_repulsion": "#cc6677",
    "gpc_bernoulli_sur_refit": "#332288",
}

SURROGATE_STYLES = {
    "gpr_fixed_or_existing": "-",
    "gpc_fixed_iso": "--",
}


@dataclass
class DatasetBundle:
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
    seed: int
    dataset: DatasetBundle
    initial_indices: list[int]
    initial_resampling_attempts: int


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
    create_design: Callable[[int, float], SeedDesign]
    value_function: Callable[[np.ndarray], np.ndarray]
    scaling_rule: str
    threshold_sample_values: np.ndarray | None = None


@dataclass
class RunOptions:
    quick: bool
    full: bool
    max_seeds: int | None
    skip_gpc_sur: bool
    sur_shortlist_size: int
    reference_size: int
    output_dir: Path
    gpc_sur_benchmarks: tuple[str, ...]
    gpc_sur_max_seeds: int | None
    gpc_sur_shortlist_size: int
    gpc_sur_limit_note: str
    summarize_existing: bool = False


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


def parse_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in {"", "null", "nan"}:
        return None
    return float(value)


def mean_std(values: list[float]) -> tuple[float, float]:
    array = np.asarray(values, dtype=float)
    return float(array.mean()), float(array.std())


def stable_seed(*items: object) -> int:
    digest = hashlib.sha256(":".join(str(item) for item in items).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little") % (2**32)


def array_signature(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for array in arrays:
        contiguous = np.ascontiguousarray(array)
        digest.update(str(contiguous.shape).encode("utf-8"))
        digest.update(str(contiguous.dtype).encode("utf-8"))
        digest.update(contiguous.view(np.uint8))
    return digest.hexdigest()


def normalize_scores(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    low = float(values.min())
    high = float(values.max())
    if high <= low + 1e-12:
        return np.zeros_like(values)
    return (values - low) / (high - low)


def deterministic_argmax(indices: np.ndarray, scores: np.ndarray) -> int:
    order = np.lexsort((indices, -scores))
    return int(order[0])


def rank_methods(values: dict[tuple[str, str], float]) -> dict[tuple[str, str], int]:
    ordered = sorted(values, key=lambda key: (values[key], key[0], key[1]))
    return {key: rank + 1 for rank, key in enumerate(ordered)}


def rng_for_method(seed: int, method: str, benchmark: str) -> np.random.Generator:
    if benchmark == "branin" and method in METHOD_ORDER:
        return branin_rng_for_method(seed, method)
    if benchmark == "ackley" and method in METHOD_ORDER:
        return rng_for_week3_named_method(seed, method)
    return np.random.default_rng(stable_seed(seed, benchmark, method, "week7"))


def hartmann4(X: np.ndarray) -> np.ndarray:
    """Standard 4D Hartmann function on [0, 1]^4."""
    X = np.asarray(X, dtype=float)
    if X.ndim != 2 or X.shape[1] != 4:
        raise ValueError("Hartmann4 expects an array with shape (n, 4)")
    alpha = np.asarray([1.0, 1.2, 3.0, 3.2], dtype=float)
    a = np.asarray(
        [
            [10.0, 3.0, 17.0, 3.5],
            [0.05, 10.0, 17.0, 0.1],
            [3.0, 3.5, 1.7, 10.0],
            [17.0, 8.0, 0.05, 10.0],
        ],
        dtype=float,
    )
    p = 1e-4 * np.asarray(
        [
            [1312.0, 1696.0, 5569.0, 124.0],
            [2329.0, 4135.0, 8307.0, 3736.0],
            [2348.0, 1451.0, 3522.0, 2883.0],
            [4047.0, 8828.0, 8732.0, 5743.0],
        ],
        dtype=float,
    )
    inner = np.sum(a[None, :, :] * (X[:, None, :] - p[None, :, :]) ** 2, axis=2)
    return -np.sum(alpha[None, :] * np.exp(-inner), axis=1)


def sample_hartmann_domain(rng: np.random.Generator, size: int) -> np.ndarray:
    return rng.uniform(0.0, 1.0, size=(size, 4))


def compute_hartmann_threshold(
    sample_size: int = HARTMANN_THRESHOLD_SAMPLE_SIZE,
    seed: int = HARTMANN_THRESHOLD_SEED,
) -> tuple[float, np.ndarray]:
    rng = np.random.default_rng(seed)
    values = hartmann4(sample_hartmann_domain(rng, sample_size))
    return float(np.percentile(values, HARTMANN_THRESHOLD_PERCENTILE)), values


def labels_from_values(values: np.ndarray, threshold: float) -> np.ndarray:
    return np.where(np.asarray(values) >= threshold, 1.0, -1.0)


def make_hartmann_dataset(
    seed: int,
    threshold: float,
    pool_size: int,
    test_size: int,
) -> DatasetBundle:
    rng = np.random.default_rng(seed)
    pool_original = sample_hartmann_domain(rng, pool_size)
    test_original = sample_hartmann_domain(rng, test_size)
    pool_values = hartmann4(pool_original)
    test_values = hartmann4(test_original)
    return DatasetBundle(
        seed=seed,
        threshold=threshold,
        pool_original=pool_original,
        pool_scaled=pool_original.copy(),
        pool_values=pool_values,
        pool_labels=labels_from_values(pool_values, threshold),
        test_original=test_original,
        test_scaled=test_original.copy(),
        test_values=test_values,
        test_labels=labels_from_values(test_values, threshold),
    )


def create_hartmann_seed_design(
    seed: int,
    threshold: float,
    initial_size: int,
    pool_size: int,
    test_size: int,
) -> SeedDesign:
    dataset = make_hartmann_dataset(seed, threshold, pool_size, test_size)
    rng = np.random.default_rng(seed + 700_000)
    initial_indices, attempts = random_two_class_initial_design(
        dataset.pool_labels,
        initial_size,
        rng,
    )
    return SeedDesign(seed, dataset, initial_indices, attempts)


def create_branin_bundle_design(
    seed: int,
    threshold: float,
    initial_size: int,
    pool_size: int,
    test_size: int,
) -> SeedDesign:
    design = create_branin_design(seed, threshold, initial_size, pool_size, test_size)
    dataset = design.dataset
    pool_values = branin(dataset.pool_original)
    test_values = branin(dataset.test_original)
    bundle = DatasetBundle(
        seed=seed,
        threshold=threshold,
        pool_original=dataset.pool_original,
        pool_scaled=dataset.pool_scaled,
        pool_values=pool_values,
        pool_labels=dataset.pool_labels,
        test_original=dataset.test_original,
        test_scaled=dataset.test_scaled,
        test_values=test_values,
        test_labels=dataset.test_labels,
    )
    return SeedDesign(seed, bundle, list(design.initial_indices), design.initial_resampling_attempts)


def create_ackley_bundle_design(
    seed: int,
    threshold: float,
    initial_size: int,
    pool_size: int,
    test_size: int,
) -> SeedDesign:
    design = create_ackley_design(seed, threshold, initial_size, pool_size, test_size)
    dataset = design.dataset
    bundle = DatasetBundle(
        seed=seed,
        threshold=threshold,
        pool_original=dataset.pool_original,
        pool_scaled=dataset.pool_scaled,
        pool_values=dataset.pool_values,
        pool_labels=dataset.pool_labels,
        test_original=dataset.test_original,
        test_scaled=dataset.test_scaled,
        test_values=dataset.test_values,
        test_labels=dataset.test_labels,
    )
    return SeedDesign(seed, bundle, list(design.initial_indices), design.initial_resampling_attempts)


def build_configs(quick: bool) -> list[BenchmarkConfig]:
    branin_threshold_seed = 2026
    branin_threshold_sample_size = 20_000
    branin_threshold = compute_branin_threshold(branin_threshold_sample_size, branin_threshold_seed)
    ackley_values = threshold_sample_values()
    ackley_threshold = compute_ackley_threshold(ackley_values)
    hartmann_threshold, hartmann_values = compute_hartmann_threshold()
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
                pool_size=260,
                test_size=600,
                initial_size=6,
                total_budget=10,
                selected_budgets=(6, 8, 10),
                create_design=lambda seed, threshold: create_branin_bundle_design(seed, threshold, 6, 260, 600),
                value_function=branin,
                scaling_rule="Branin original coordinates are linearly scaled to [0,1]^2 for the surrogate.",
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
                pool_size=360,
                test_size=800,
                initial_size=12,
                total_budget=16,
                selected_budgets=(12, 14, 16),
                create_design=lambda seed, threshold: create_ackley_bundle_design(seed, threshold, 12, 360, 800),
                value_function=ackley_4d,
                scaling_rule="Ackley original coordinates are linearly scaled to [0,1]^4 for the surrogate.",
            ),
            BenchmarkConfig(
                name="hartmann4",
                display_name="Thresholded 4D Hartmann",
                output_name="hartmann4",
                domain="[0,1]^4",
                threshold=hartmann_threshold,
                threshold_percentile=HARTMANN_THRESHOLD_PERCENTILE,
                threshold_seed=HARTMANN_THRESHOLD_SEED,
                threshold_sample_size=HARTMANN_THRESHOLD_SAMPLE_SIZE,
                pool_size=360,
                test_size=800,
                initial_size=12,
                total_budget=16,
                selected_budgets=(12, 14, 16),
                create_design=lambda seed, threshold: create_hartmann_seed_design(seed, threshold, 12, 360, 800),
                value_function=hartmann4,
                scaling_rule="Hartmann4 already lives on [0,1]^4.",
                threshold_sample_values=hartmann_values,
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
            create_design=lambda seed, threshold: create_branin_bundle_design(seed, threshold, 6, 1_500, 4_000),
            value_function=branin,
            scaling_rule="Branin original coordinates are linearly scaled to [0,1]^2 for the surrogate.",
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
            create_design=lambda seed, threshold: create_ackley_bundle_design(seed, threshold, 12, ACKLEY_POOL_SIZE, ACKLEY_TEST_SIZE),
            value_function=ackley_4d,
            scaling_rule="Ackley original coordinates are linearly scaled to [0,1]^4 for the surrogate.",
        ),
        BenchmarkConfig(
            name="hartmann4",
            display_name="Thresholded 4D Hartmann",
            output_name="hartmann4",
            domain="[0,1]^4",
            threshold=hartmann_threshold,
            threshold_percentile=HARTMANN_THRESHOLD_PERCENTILE,
            threshold_seed=HARTMANN_THRESHOLD_SEED,
            threshold_sample_size=HARTMANN_THRESHOLD_SAMPLE_SIZE,
            pool_size=4_000,
            test_size=10_000,
            initial_size=12,
            total_budget=80,
            selected_budgets=(12, 40, 80),
            create_design=lambda seed, threshold: create_hartmann_seed_design(seed, threshold, 12, 4_000, 10_000),
            value_function=hartmann4,
            scaling_rule="Hartmann4 already lives on [0,1]^4.",
            threshold_sample_values=hartmann_values,
        ),
    ]


def make_gp_classifier(seed: int) -> GaussianProcessClassifier:
    kernel = ConstantKernel(1.0, constant_value_bounds="fixed") * RBF(
        length_scale=GPC_LENGTH_SCALE,
        length_scale_bounds="fixed",
    )
    return GaussianProcessClassifier(
        kernel=kernel,
        optimizer=None,
        n_restarts_optimizer=0,
        max_iter_predict=GPC_MAX_ITER_PREDICT,
        random_state=seed,
    )


def fit_classifier(X: np.ndarray, y: np.ndarray, seed: int) -> GaussianProcessClassifier:
    if np.unique(y).size < 2:
        raise RuntimeError("GaussianProcessClassifier requires both classes")
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


def gpr_p_plus(mu: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    sigma_safe = np.maximum(np.asarray(sigma, dtype=float), GPR_PROBABILITY_EPS)
    return ndtr(np.asarray(mu, dtype=float) / sigma_safe)


def bernoulli_uncertainty_from_p(p_plus: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p_plus, dtype=float), 0.0, 1.0)
    return p * (1.0 - p)


def classifier_uncertainty_score(p_plus: np.ndarray) -> np.ndarray:
    return np.clip(1.0 - 2.0 * np.abs(np.asarray(p_plus) - 0.5), 0.0, 1.0)


def binary_entropy(p_plus: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p_plus, dtype=float), 1e-12, 1.0 - 1e-12)
    return -(p * np.log(p) + (1.0 - p) * np.log(1.0 - p))


def nearest_labelled_distance(
    pool_scaled: np.ndarray,
    candidate_indices: np.ndarray,
    labelled_indices: list[int],
) -> np.ndarray:
    candidates = pool_scaled[candidate_indices]
    labelled = pool_scaled[np.asarray(labelled_indices, dtype=int)]
    diffs = candidates[:, None, :] - labelled[None, :, :]
    return np.sqrt(np.sum(diffs**2, axis=2)).min(axis=1)


def choose_boundary_gated_diversified_straddle(
    *,
    unlabelled_indices: np.ndarray,
    mu: np.ndarray,
    sigma: np.ndarray,
    pool_scaled: np.ndarray,
    labelled_indices: list[int],
) -> tuple[int, dict[str, object]]:
    straddle = UNCERTAINTY_MULTIPLIER * sigma - np.abs(mu)
    candidate_count = len(unlabelled_indices)
    shortlist_size = int(np.ceil(candidate_count * BOUNDARY_GATED_GATE_FRACTION))
    shortlist_size = max(shortlist_size, min(BOUNDARY_GATED_MIN_SHORTLIST_SIZE, candidate_count))
    shortlist_size = min(shortlist_size, candidate_count)
    order = np.lexsort((unlabelled_indices, -straddle))
    shortlist_positions = order[:shortlist_size]
    shortlist_indices = unlabelled_indices[shortlist_positions]
    shortlist_straddle = straddle[shortlist_positions]
    distances = nearest_labelled_distance(pool_scaled, shortlist_indices, labelled_indices)
    norm_straddle = normalize_scores(shortlist_straddle)
    norm_diversity = normalize_scores(distances)
    score = (1.0 - BOUNDARY_GATED_BETA) * norm_straddle + BOUNDARY_GATED_BETA * norm_diversity
    shortlist_choice = deterministic_argmax(shortlist_indices, score)
    original_position = int(shortlist_positions[shortlist_choice])
    return int(shortlist_indices[shortlist_choice]), {
        "gate_fraction": BOUNDARY_GATED_GATE_FRACTION,
        "beta": BOUNDARY_GATED_BETA,
        "min_shortlist_size": BOUNDARY_GATED_MIN_SHORTLIST_SIZE,
        "shortlist_size": shortlist_size,
        "selected_position": original_position,
        "selected_shortlist_position": shortlist_choice,
        "selected_score": float(score[shortlist_choice]),
        "selected_raw_straddle": float(shortlist_straddle[shortlist_choice]),
        "selected_raw_diversity": float(distances[shortlist_choice]),
    }


def posterior_covariance(gp, X_ref: np.ndarray, X_candidate: np.ndarray) -> np.ndarray:
    k_ref_candidate = gp.kernel_(X_ref, X_candidate)
    k_ref_train = gp.kernel_(X_ref, gp.X_train_)
    k_candidate_train = gp.kernel_(X_candidate, gp.X_train_)
    v_ref = solve_triangular(gp.L_, k_ref_train.T, lower=True, check_finite=False)
    v_candidate = solve_triangular(gp.L_, k_candidate_train.T, lower=True, check_finite=False)
    covariance = k_ref_candidate - v_ref.T @ v_candidate
    return np.nan_to_num(covariance, nan=0.0, posinf=0.0, neginf=0.0)


def reference_positions(
    *,
    unlabelled_indices: np.ndarray,
    membership_uncertainty: np.ndarray,
    reference_size: int,
    seed_items: tuple[object, ...],
) -> np.ndarray:
    n = len(unlabelled_indices)
    if n <= reference_size:
        return np.arange(n, dtype=int)
    ordered = np.lexsort((unlabelled_indices, -membership_uncertainty))
    top_count = min(reference_size, max(1, reference_size // 2))
    top_positions = ordered[:top_count]
    remaining = ordered[top_count:]
    fill_count = reference_size - len(top_positions)
    if fill_count <= 0:
        return np.sort(top_positions)
    rng = np.random.default_rng(stable_seed(*seed_items))
    fill_positions = rng.choice(remaining, size=fill_count, replace=False)
    return np.sort(np.concatenate([top_positions, fill_positions]).astype(int))


def candidate_gate_positions(
    unlabelled_indices: np.ndarray,
    straddle: np.ndarray,
) -> np.ndarray:
    n = len(unlabelled_indices)
    gate_size = int(np.ceil(n * IVR_GATE_FRACTION))
    gate_size = max(gate_size, min(IVR_MIN_GATE_SIZE, n))
    gate_size = min(gate_size, n)
    order = np.lexsort((unlabelled_indices, -straddle))
    return order[:gate_size]


def compute_gpr_ivr_state(
    *,
    gp,
    dataset: DatasetBundle,
    unlabelled_indices: np.ndarray,
    mu: np.ndarray,
    sigma: np.ndarray,
    reference_size: int,
    seed_items: tuple[object, ...],
) -> dict[str, object]:
    p_plus = gpr_p_plus(mu, sigma)
    membership_uncertainty = bernoulli_uncertainty_from_p(p_plus)
    straddle = UNCERTAINTY_MULTIPLIER * sigma - np.abs(mu)
    ref_pos = reference_positions(
        unlabelled_indices=unlabelled_indices,
        membership_uncertainty=membership_uncertainty,
        reference_size=reference_size,
        seed_items=seed_items,
    )
    gate_pos = candidate_gate_positions(unlabelled_indices, straddle)
    weights = membership_uncertainty[ref_pos].astype(float)
    if float(weights.sum()) <= 1e-12:
        weights = np.full_like(weights, 1.0 / len(weights), dtype=float)
    else:
        weights = weights / float(weights.sum())
    covariance = posterior_covariance(
        gp,
        dataset.pool_scaled[unlabelled_indices[ref_pos]],
        dataset.pool_scaled[unlabelled_indices[gate_pos]],
    )
    gate_var = np.maximum(sigma[gate_pos] ** 2, POSTERIOR_NOISE_EPS)
    delta_var = (covariance**2) / gate_var[None, :]
    gate_scores = weights @ delta_var
    scores = np.full(len(unlabelled_indices), -np.inf, dtype=float)
    scores[gate_pos] = gate_scores
    return {
        "scores": scores,
        "ref_pos": ref_pos,
        "gate_pos": gate_pos,
        "covariance_ref_gate": covariance,
        "p_plus": p_plus,
        "membership_uncertainty": membership_uncertainty,
        "straddle": straddle,
        "reference_weights": weights,
    }


def choose_gpr_boundary_weighted_ivr(
    *,
    gp,
    dataset: DatasetBundle,
    unlabelled_indices: np.ndarray,
    mu: np.ndarray,
    sigma: np.ndarray,
    reference_size: int,
    seed_items: tuple[object, ...],
) -> tuple[int, dict[str, object]]:
    state = compute_gpr_ivr_state(
        gp=gp,
        dataset=dataset,
        unlabelled_indices=unlabelled_indices,
        mu=mu,
        sigma=sigma,
        reference_size=reference_size,
        seed_items=seed_items,
    )
    scores = state["scores"]
    position = deterministic_argmax(unlabelled_indices, scores)
    metadata = {
        "selected_position": position,
        "selected_score": float(scores[position]),
        "selected_p_plus": float(state["p_plus"][position]),
        "selected_membership_uncertainty": float(state["membership_uncertainty"][position]),
        "selected_straddle_score": float(state["straddle"][position]),
        "weighted_variance_reduction": float(scores[position]),
        "reference_set_size": int(len(state["ref_pos"])),
        "candidate_gate_size": int(len(state["gate_pos"])),
        "candidate_gate_fraction": IVR_GATE_FRACTION,
        "posterior_covariance_used": True,
    }
    return int(unlabelled_indices[position]), metadata


def choose_gpr_bernoulli_sur_refit(
    *,
    gp,
    dataset: DatasetBundle,
    unlabelled_indices: np.ndarray,
    mu: np.ndarray,
    sigma: np.ndarray,
    reference_size: int,
    shortlist_size: int,
    seed_items: tuple[object, ...],
) -> tuple[int, dict[str, object]]:
    start = time.perf_counter()
    state = compute_gpr_ivr_state(
        gp=gp,
        dataset=dataset,
        unlabelled_indices=unlabelled_indices,
        mu=mu,
        sigma=sigma,
        reference_size=reference_size,
        seed_items=seed_items,
    )
    scores = np.asarray(state["scores"], dtype=float)
    valid_positions = np.flatnonzero(np.isfinite(scores))
    if valid_positions.size == 0:
        order = np.lexsort((unlabelled_indices, -np.asarray(state["straddle"], dtype=float)))
    else:
        order = valid_positions[np.lexsort((unlabelled_indices[valid_positions], -scores[valid_positions]))]
    shortlist_positions = order[: min(shortlist_size, len(order))]
    ref_pos = np.asarray(state["ref_pos"], dtype=int)
    gate_pos = np.asarray(state["gate_pos"], dtype=int)
    gate_position_to_column = {int(pos): column for column, pos in enumerate(gate_pos)}
    missing = [pos for pos in shortlist_positions if int(pos) not in gate_position_to_column]
    if missing:
        covariance = posterior_covariance(
            gp,
            dataset.pool_scaled[unlabelled_indices[ref_pos]],
            dataset.pool_scaled[unlabelled_indices[shortlist_positions]],
        )
    else:
        covariance = np.column_stack(
            [
                np.asarray(state["covariance_ref_gate"])[:, gate_position_to_column[int(pos)]]
                for pos in shortlist_positions
            ]
        )
    mu_ref = mu[ref_pos]
    var_ref = np.maximum(sigma[ref_pos] ** 2, POSTERIOR_NOISE_EPS)
    p_ref = gpr_p_plus(mu_ref, np.sqrt(var_ref))
    current_uncertainty = bernoulli_uncertainty_from_p(p_ref)
    u_current = float(current_uncertainty.sum())
    mu_star = mu[shortlist_positions]
    var_star = np.maximum(sigma[shortlist_positions] ** 2, POSTERIOR_NOISE_EPS)
    p_star = gpr_p_plus(mu_star, np.sqrt(var_star))
    gain = covariance / var_star[None, :]
    var_new = np.maximum(var_ref[:, None] - (covariance**2) / var_star[None, :], POSTERIOR_NOISE_EPS)
    std_new = np.sqrt(var_new)
    mu_plus = mu_ref[:, None] + gain * (1.0 - mu_star[None, :])
    mu_minus = mu_ref[:, None] + gain * (-1.0 - mu_star[None, :])
    p_plus_new = gpr_p_plus(mu_plus, std_new)
    p_minus_new = gpr_p_plus(mu_minus, std_new)
    u_plus = bernoulli_uncertainty_from_p(p_plus_new).sum(axis=0)
    u_minus = bernoulli_uncertainty_from_p(p_minus_new).sum(axis=0)
    expected_future = p_star * u_plus + (1.0 - p_star) * u_minus
    reduction = u_current - expected_future
    shortlist_indices = unlabelled_indices[shortlist_positions]
    best_shortlist_position = deterministic_argmax(shortlist_indices, reduction)
    original_position = int(shortlist_positions[best_shortlist_position])
    elapsed = time.perf_counter() - start
    metadata = {
        "selected_position": original_position,
        "selected_score": float(reduction[best_shortlist_position]),
        "p_star": float(p_star[best_shortlist_position]),
        "U_current": u_current,
        "U_plus": float(u_plus[best_shortlist_position]),
        "U_minus": float(u_minus[best_shortlist_position]),
        "expected_future_uncertainty": float(expected_future[best_shortlist_position]),
        "expected_uncertainty_reduction": float(reduction[best_shortlist_position]),
        "shortlist_size": int(len(shortlist_positions)),
        "reference_set_size": int(len(ref_pos)),
        "candidate_gate_size": int(len(gate_pos)),
        "fantasy_refit_time_seconds": float(elapsed),
        "fantasy_refit_mode": "exact_fixed_kernel_rank_one_update_equivalent_to_refit",
        "shortlist_source": "gpr_boundary_weighted_ivr_score",
    }
    return int(shortlist_indices[best_shortlist_position]), metadata


def classifier_repulsion_scores(
    *,
    p_plus: np.ndarray,
    unlabelled_indices: np.ndarray,
    pool_scaled: np.ndarray,
    labelled_indices: list[int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    uncertainty = classifier_uncertainty_score(p_plus)
    distances = nearest_labelled_distance(pool_scaled, unlabelled_indices, labelled_indices)
    repulsion = 1.0 - np.exp(-(distances**2) / (2.0 * CLASSIFIER_REPULSION_BANDWIDTH**2 + 1e-12))
    return normalize_scores(uncertainty) * repulsion, uncertainty, repulsion


def choose_classifier_candidate(
    *,
    method: str,
    unlabelled_indices: np.ndarray,
    p_plus: np.ndarray,
    pool_scaled: np.ndarray,
    labelled_indices: list[int],
) -> tuple[int, dict[str, object]]:
    uncertainty = classifier_uncertainty_score(p_plus)
    entropy = binary_entropy(p_plus)
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
            "binary_entropy_margin_note": "Binary entropy is monotone-equivalent to margin.",
        }
    if method == "classifier_uncertainty_repulsion":
        score, uncertainty, repulsion = classifier_repulsion_scores(
            p_plus=p_plus,
            unlabelled_indices=unlabelled_indices,
            pool_scaled=pool_scaled,
            labelled_indices=labelled_indices,
        )
        gate_size = int(np.ceil(len(unlabelled_indices) * CLASSIFIER_GATE_FRACTION))
        gate_size = max(gate_size, min(CLASSIFIER_MIN_SHORTLIST_SIZE, len(unlabelled_indices)))
        gate_size = min(gate_size, len(unlabelled_indices))
        order = np.lexsort((unlabelled_indices, -uncertainty))
        gate_positions = order[:gate_size]
        gated_choice = deterministic_argmax(unlabelled_indices[gate_positions], score[gate_positions])
        position = int(gate_positions[gated_choice])
        return int(unlabelled_indices[position]), {
            "gate_fraction": CLASSIFIER_GATE_FRACTION,
            "min_shortlist_size": CLASSIFIER_MIN_SHORTLIST_SIZE,
            "shortlist_size": gate_size,
            "repulsion_bandwidth": CLASSIFIER_REPULSION_BANDWIDTH,
            "selected_position": position,
            "selected_shortlist_position": int(gated_choice),
            "selected_p_plus": float(p_plus[position]),
            "selected_uncertainty_score": float(uncertainty[position]),
            "selected_entropy": float(entropy[position]),
            "selected_repulsion": float(repulsion[position]),
            "selected_score": float(score[position]),
        }
    raise ValueError(f"Unknown classifier method: {method}")


def choose_gpc_bernoulli_sur_refit(
    *,
    gp: GaussianProcessClassifier,
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
    uncertainty = bernoulli_uncertainty_from_p(p_plus)
    ref_pos = reference_positions(
        unlabelled_indices=unlabelled_indices,
        membership_uncertainty=uncertainty,
        reference_size=reference_size,
        seed_items=seed_items,
    )
    score, uncertainty_score, repulsion = classifier_repulsion_scores(
        p_plus=p_plus,
        unlabelled_indices=unlabelled_indices,
        pool_scaled=dataset.pool_scaled,
        labelled_indices=labelled_indices,
    )
    order = np.lexsort((unlabelled_indices, -score))
    shortlist_positions = order[: min(shortlist_size, len(order))]
    shortlist_indices = unlabelled_indices[shortlist_positions]
    reference_scaled = dataset.pool_scaled[unlabelled_indices[ref_pos]]
    current_p_ref = p_plus[ref_pos]
    u_current = float(bernoulli_uncertainty_from_p(current_p_ref).sum())
    x_labelled = dataset.pool_scaled[np.asarray(labelled_indices, dtype=int)]
    y_labelled = dataset.pool_labels[np.asarray(labelled_indices, dtype=int)]
    reductions: list[float] = []
    u_plus_values: list[float] = []
    u_minus_values: list[float] = []
    expected_values: list[float] = []
    for candidate_index, candidate_position in zip(shortlist_indices, shortlist_positions):
        candidate_x = dataset.pool_scaled[int(candidate_index)][None, :]
        x_fantasy = np.vstack([x_labelled, candidate_x])
        gp_plus = fit_classifier(x_fantasy, np.concatenate([y_labelled, [1.0]]), seed)
        p_ref_plus = predict_p_plus(gp_plus, reference_scaled)
        u_plus = float(bernoulli_uncertainty_from_p(p_ref_plus).sum())
        gp_minus = fit_classifier(x_fantasy, np.concatenate([y_labelled, [-1.0]]), seed)
        p_ref_minus = predict_p_plus(gp_minus, reference_scaled)
        u_minus = float(bernoulli_uncertainty_from_p(p_ref_minus).sum())
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
        "reference_set_size": int(len(ref_pos)),
        "fantasy_refit_time_seconds": float(elapsed),
        "shortlist_source": "classifier_uncertainty_repulsion",
        "selected_uncertainty_score": float(uncertainty_score[original_position]),
        "selected_repulsion": float(repulsion[original_position]),
    }
    return int(shortlist_indices[best_shortlist_position]), metadata


def boundary_masks(distances: np.ndarray) -> dict[int, np.ndarray]:
    return {
        quantile: distances <= float(np.percentile(distances, quantile))
        for quantile in BOUNDARY_QUANTILES
    }


def evaluate_budget(
    *,
    config: BenchmarkConfig,
    surrogate_variant: str,
    acquisition_rule: str,
    seed: int,
    budget: int,
    model,
    dataset: DatasetBundle,
    test_masks: dict[int, np.ndarray],
    fit_time_seconds: float,
) -> dict[str, object]:
    if surrogate_variant == "gpr_fixed_or_existing":
        mu, sigma = model.predict(dataset.test_scaled, return_std=True)
        p_plus = gpr_p_plus(mu, sigma)
        prediction = np.where(mu >= 0.0, 1.0, -1.0)
        uncertainty_region = np.abs(mu) <= UNCERTAINTY_MULTIPLIER * sigma
    elif surrogate_variant == "gpc_fixed_iso":
        p_plus = predict_p_plus(model, dataset.test_scaled)
        prediction = np.where(p_plus >= 0.5, 1.0, -1.0)
        uncertainty_region = np.abs(p_plus - 0.5) <= PRIMARY_CLASSIFIER_EPSILON
    else:
        raise ValueError(f"Unknown surrogate variant: {surrogate_variant}")
    errors = prediction != dataset.test_labels
    bernoulli_u = bernoulli_uncertainty_from_p(p_plus)
    row: dict[str, object] = {
        "benchmark": config.name,
        "display_name": config.display_name,
        "surrogate_variant": surrogate_variant,
        "acquisition_rule": acquisition_rule,
        "method": acquisition_rule,
        "seed": seed,
        "budget": budget,
        "global_error": float(np.mean(errors)),
        "uncertainty_region_fraction": float(np.mean(uncertainty_region)),
        "integrated_bernoulli_uncertainty": float(np.mean(bernoulli_u)),
        "fit_time_seconds": float(fit_time_seconds),
    }
    for quantile, mask in test_masks.items():
        row[f"near_boundary_error_q{quantile}"] = float(np.mean(errors[mask]))
        row[f"near_boundary_test_size_q{quantile}"] = int(mask.sum())
        row[f"uncertainty_region_fraction_q{quantile}"] = float(np.mean(uncertainty_region[mask]))
        row[f"integrated_bernoulli_uncertainty_q{quantile}"] = float(np.mean(bernoulli_u[mask]))
    return row


def choose_next(
    *,
    config: BenchmarkConfig,
    method: str,
    surrogate_variant: str,
    model,
    dataset: DatasetBundle,
    labelled: list[int],
    unlabelled: np.ndarray,
    seed: int,
    budget: int,
    rng: np.random.Generator,
    options: RunOptions,
) -> tuple[int, dict[str, object]]:
    if surrogate_variant == "gpr_fixed_or_existing":
        if method == "random":
            choice = choose_next_index(method, unlabelled, None, None, rng)
            return choice.index, dict(choice.metadata)
        mu, sigma = model.predict(dataset.pool_scaled[unlabelled], return_std=True)
        if method in {"smallest_abs_mu", "straddle", "randomized_straddle", "expected_feasibility"}:
            choice = choose_next_index(method, unlabelled, mu, sigma, rng)
            return choice.index, dict(choice.metadata)
        if method == "boundary_gated_diversified_straddle":
            return choose_boundary_gated_diversified_straddle(
                unlabelled_indices=unlabelled,
                mu=mu,
                sigma=sigma,
                pool_scaled=dataset.pool_scaled,
                labelled_indices=labelled,
            )
        if method == "gpr_boundary_weighted_ivr":
            return choose_gpr_boundary_weighted_ivr(
                gp=model,
                dataset=dataset,
                unlabelled_indices=unlabelled,
                mu=mu,
                sigma=sigma,
                reference_size=options.reference_size,
                seed_items=(config.name, seed, budget, method, "reference"),
            )
        if method == "gpr_bernoulli_sur_refit":
            return choose_gpr_bernoulli_sur_refit(
                gp=model,
                dataset=dataset,
                unlabelled_indices=unlabelled,
                mu=mu,
                sigma=sigma,
                reference_size=options.reference_size,
                shortlist_size=options.sur_shortlist_size,
                seed_items=(config.name, seed, budget, method, "reference"),
            )
    if surrogate_variant == "gpc_fixed_iso":
        p_plus = predict_p_plus(model, dataset.pool_scaled[unlabelled])
        if method in GPC_BASELINE_METHODS:
            return choose_classifier_candidate(
                method=method,
                unlabelled_indices=unlabelled,
                p_plus=p_plus,
                pool_scaled=dataset.pool_scaled,
                labelled_indices=labelled,
            )
        if method == "gpc_bernoulli_sur_refit":
            return choose_gpc_bernoulli_sur_refit(
                gp=model,
                dataset=dataset,
                labelled_indices=labelled,
                unlabelled_indices=unlabelled,
                p_plus=p_plus,
                seed=seed,
                reference_size=options.reference_size,
                shortlist_size=options.gpc_sur_shortlist_size,
                seed_items=(config.name, seed, budget, method, "reference"),
            )
    raise ValueError(f"Unsupported method/surrogate combination: {surrogate_variant}/{method}")


def method_surrogate(method: str) -> str:
    if method in GPR_BASELINE_METHODS or method in GPR_NEW_METHODS:
        return "gpr_fixed_or_existing"
    if method in GPC_BASELINE_METHODS or method in GPC_SUR_METHODS:
        return "gpc_fixed_iso"
    raise ValueError(f"Unknown method: {method}")


def run_method(
    config: BenchmarkConfig,
    design: SeedDesign,
    method: str,
    options: RunOptions,
) -> MethodRun:
    dataset = design.dataset
    surrogate_variant = method_surrogate(method)
    pool_distances = np.abs(dataset.pool_values - config.threshold)
    test_distances = np.abs(dataset.test_values - config.threshold)
    pool_masks = boundary_masks(pool_distances)
    test_masks = boundary_masks(test_distances)
    labelled = list(design.initial_indices)
    initial_copy = list(design.initial_indices)
    rng = rng_for_method(design.seed, method, config.name)
    metric_rows: list[dict[str, object]] = []
    query_rows: list[dict[str, object]] = []
    budgets: list[int] = []
    fit_times: list[float] = []
    acquisition_times: list[float] = []
    run_start = time.perf_counter()
    print(
        f"  seed={design.seed} surrogate={surrogate_variant} method={method}",
        flush=True,
    )
    while True:
        fit_start = time.perf_counter()
        if surrogate_variant == "gpr_fixed_or_existing":
            model = fit_gp(dataset.pool_scaled[labelled], dataset.pool_labels[labelled], design.seed)
        else:
            model = fit_classifier(dataset.pool_scaled[labelled], dataset.pool_labels[labelled], design.seed)
        fit_time = time.perf_counter() - fit_start
        fit_times.append(fit_time)
        budget = len(labelled)
        budgets.append(budget)
        metric_rows.append(
            evaluate_budget(
                config=config,
                surrogate_variant=surrogate_variant,
                acquisition_rule=method,
                seed=design.seed,
                budget=budget,
                model=model,
                dataset=dataset,
                test_masks=test_masks,
                fit_time_seconds=fit_time,
            )
        )
        if budget == config.total_budget:
            break
        mask = np.ones(len(dataset.pool_labels), dtype=bool)
        mask[labelled] = False
        unlabelled = np.flatnonzero(mask)
        acquisition_start = time.perf_counter()
        next_index, metadata = choose_next(
            config=config,
            method=method,
            surrogate_variant=surrogate_variant,
            model=model,
            dataset=dataset,
            labelled=labelled,
            unlabelled=unlabelled,
            seed=design.seed,
            budget=budget,
            rng=rng,
            options=options,
        )
        acquisition_time = time.perf_counter() - acquisition_start
        acquisition_times.append(acquisition_time)
        query_row: dict[str, object] = {
            "benchmark": config.name,
            "display_name": config.display_name,
            "surrogate_variant": surrogate_variant,
            "acquisition_rule": method,
            "method": method,
            "seed": design.seed,
            "query_number": len(query_rows) + 1,
            "budget_before_query": budget,
            "budget_after_query": budget + 1,
            "selected_pool_index": int(next_index),
            "true_boundary_distance": float(pool_distances[int(next_index)]),
            "acquisition_time_seconds": float(acquisition_time),
        }
        for quantile, band_mask in pool_masks.items():
            query_row[f"in_pool_boundary_band_q{quantile}"] = bool(band_mask[int(next_index)])
        for key, value in metadata.items():
            query_row[f"acquisition_{key}"] = value
        query_rows.append(query_row)
        labelled.append(int(next_index))
    if labelled[: len(initial_copy)] != initial_copy:
        raise RuntimeError("Initial labelled indices were mutated")
    total_runtime = time.perf_counter() - run_start
    runtime_row = {
        "benchmark": config.name,
        "surrogate_variant": surrogate_variant,
        "acquisition_rule": method,
        "method": method,
        "seed": design.seed,
        "total_runtime_seconds": float(total_runtime),
        "fit_count": len(fit_times),
        "mean_fit_time_seconds": float(np.mean(fit_times)),
        "total_fit_time_seconds": float(np.sum(fit_times)),
        "acquisition_count": len(acquisition_times),
        "mean_acquisition_time_seconds": float(np.mean(acquisition_times)) if acquisition_times else 0.0,
        "total_acquisition_time_seconds": float(np.sum(acquisition_times)) if acquisition_times else 0.0,
    }
    return MethodRun(
        benchmark=config.name,
        surrogate_variant=surrogate_variant,
        acquisition_rule=method,
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
        "same_pool_and_test_across_surrogates": True,
        "only_acquisition_or_surrogate_rule_changes": True,
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


def summarize_final_metrics(
    config: BenchmarkConfig,
    metric_rows: list[dict[str, object]],
    query_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    keys = sorted({(str(row["surrogate_variant"]), str(row["acquisition_rule"])) for row in metric_rows})
    rows: list[dict[str, object]] = []
    raw_rank_values: dict[tuple[str, str], dict[str, float]] = {}
    metric_fields = [
        "global_error",
        "near_boundary_error_q10",
        "near_boundary_error_q20",
        "near_boundary_error_q30",
        "uncertainty_region_fraction",
        "uncertainty_region_fraction_q20",
        "uncertainty_region_fraction_q30",
        "integrated_bernoulli_uncertainty",
    ]
    for surrogate_variant, acquisition_rule in keys:
        final_subset = [
            row
            for row in metric_rows
            if row["surrogate_variant"] == surrogate_variant
            and row["acquisition_rule"] == acquisition_rule
            and int(row["budget"]) == config.total_budget
        ]
        query_subset = [
            row
            for row in query_rows
            if row["surrogate_variant"] == surrogate_variant
            and row["acquisition_rule"] == acquisition_rule
        ]
        row: dict[str, object] = {
            "benchmark": config.name,
            "display_name": config.display_name,
            "surrogate_variant": surrogate_variant,
            "acquisition_rule": acquisition_rule,
            "method": acquisition_rule,
            "final_budget": config.total_budget,
            "seed_count": len({item["seed"] for item in final_subset}),
        }
        for field in metric_fields:
            mean, std = mean_std([float(item[field]) for item in final_subset])
            row[f"mean_final_{field}"] = f"{mean:.6f}"
            row[f"std_final_{field}"] = f"{std:.6f}"
        distances = np.asarray([float(item["true_boundary_distance"]) for item in query_subset], dtype=float)
        if distances.size:
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
        else:
            row.update(
                {
                    "mean_query_distance": "nan",
                    "median_query_distance": "nan",
                    "query_distance_q25": "nan",
                    "query_distance_q75": "nan",
                    "fraction_queries_in_pool_boundary_band_q10": "nan",
                    "fraction_queries_in_pool_boundary_band_q20": "nan",
                    "fraction_queries_in_pool_boundary_band_q30": "nan",
                    "mean_acquisition_time_seconds": "nan",
                }
            )
        key = (surrogate_variant, acquisition_rule)
        raw_rank_values[key] = {
            "global_error": float(row["mean_final_global_error"]),
            "near_boundary_error_q20": float(row["mean_final_near_boundary_error_q20"]),
            "near_boundary_error_q30": float(row["mean_final_near_boundary_error_q30"]),
            "median_query_distance": parse_float(row["median_query_distance"]) or float("inf"),
            "integrated_bernoulli_uncertainty": float(row["mean_final_integrated_bernoulli_uncertainty"]),
        }
        rows.append(row)
    max_seed_count = max(int(row["seed_count"]) for row in rows) if rows else 0
    for row in rows:
        row["full_seed_count_for_benchmark"] = max_seed_count
        row["is_limited_seed_count"] = int(row["seed_count"]) < max_seed_count
    for rank_field, metric in {
        "rank_global_error": "global_error",
        "rank_near_boundary_error_q20": "near_boundary_error_q20",
        "rank_near_boundary_error_q30": "near_boundary_error_q30",
        "rank_median_query_distance": "median_query_distance",
        "rank_integrated_bernoulli_uncertainty": "integrated_bernoulli_uncertainty",
    }.items():
        ranks = rank_methods({key: values[metric] for key, values in raw_rank_values.items()})
        for row in rows:
            row[rank_field] = ranks[(str(row["surrogate_variant"]), str(row["acquisition_rule"]))]
    return rows


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
                "seed_count": len(subset),
                "total_runtime_seconds_sum_over_seeds": f"{sum(float(row['total_runtime_seconds']) for row in subset):.6f}",
                "mean_runtime_seconds_per_seed": f"{np.mean([float(row['total_runtime_seconds']) for row in subset]):.6f}",
                "mean_fit_time_seconds": f"{np.mean([float(row['mean_fit_time_seconds']) for row in subset]):.6f}",
                "mean_acquisition_time_seconds": f"{np.mean([float(row['mean_acquisition_time_seconds']) for row in subset]):.6f}",
                "fit_count_sum": int(sum(int(row["fit_count"]) for row in subset)),
                "acquisition_count_sum": int(sum(int(row["acquisition_count"]) for row in subset)),
            }
        )
    rows.append(
        {
            "benchmark": benchmark,
            "surrogate_variant": "all",
            "acquisition_rule": "all",
            "method": "all",
            "seed_count": len({(row["surrogate_variant"], row["acquisition_rule"], row["seed"]) for row in runtime_rows}),
            "total_runtime_seconds_sum_over_seeds": f"{sum(float(row['total_runtime_seconds']) for row in runtime_rows):.6f}",
            "mean_runtime_seconds_per_seed": f"{np.mean([float(row['total_runtime_seconds']) for row in runtime_rows]):.6f}",
            "mean_fit_time_seconds": f"{np.mean([float(row['mean_fit_time_seconds']) for row in runtime_rows]):.6f}",
            "mean_acquisition_time_seconds": f"{np.mean([float(row['mean_acquisition_time_seconds']) for row in runtime_rows]):.6f}",
            "fit_count_sum": int(sum(int(row["fit_count"]) for row in runtime_rows)),
            "acquisition_count_sum": int(sum(int(row["acquisition_count"]) for row in runtime_rows)),
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
    max_seed_count = max(int(row["seed_count"]) for row in final_rows) if final_rows else 0
    comparable_rows = [row for row in final_rows if int(row["seed_count"]) == max_seed_count]
    if not comparable_rows:
        comparable_rows = final_rows
    for metric, field in mapping.items():
        best = min(comparable_rows, key=lambda row: float(row[field]))
        rows.append(
            {
                "benchmark": best["benchmark"],
                "display_name": best["display_name"],
                "metric": metric,
                "surrogate_variant": best["surrogate_variant"],
                "acquisition_rule": best["acquisition_rule"],
                "method": best["acquisition_rule"],
                "value": best[field],
                "field": field,
                "seed_count": best["seed_count"],
                "comparable_full_seed_only": True,
            }
        )
    return rows


def curve_groups(rows: list[dict[str, object]], metric: str) -> dict[tuple[str, str], dict[str, np.ndarray]]:
    groups: dict[tuple[str, str], dict[str, np.ndarray]] = {}
    keys = sorted({(str(row["surrogate_variant"]), str(row["acquisition_rule"])) for row in rows})
    for key in keys:
        subset = [row for row in rows if (row["surrogate_variant"], row["acquisition_rule"]) == key]
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
    for (surrogate_variant, acquisition_rule), series in curve_groups(rows, metric).items():
        color = METHOD_COLORS.get(acquisition_rule, "#333333")
        linestyle = SURROGATE_STYLES.get(surrogate_variant, "-")
        label = f"{surrogate_variant} / {acquisition_rule}"
        ax.plot(series["budgets"], series["mean"], color=color, linestyle=linestyle, linewidth=2.1, label=label)
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
    ax.legend(fontsize=7, ncol=2, loc="best")
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
        linestyle = SURROGATE_STYLES.get(surrogate_variant, "-")
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


def plot_hartmann_value_distribution(config: BenchmarkConfig, output_path: Path) -> None:
    if config.threshold_sample_values is None:
        return
    values = np.asarray(config.threshold_sample_values, dtype=float)
    labels = labels_from_values(values, config.threshold)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.hist(values, bins=70, color="#4c78a8", alpha=0.82, edgecolor="white")
    ax.axvline(config.threshold, color="#d55e00", linewidth=2.8, label=f"threshold = {config.threshold:.4f}")
    ax.set(title="4D Hartmann value distribution used for thresholding", xlabel="Hartmann4 value", ylabel="Count")
    ax.text(
        0.98,
        0.95,
        f"Threshold percentile: {config.threshold_percentile:.0f}%\n-1 fraction: {np.mean(labels == -1.0):.3f}\n+1 fraction: {np.mean(labels == 1.0):.3f}",
        transform=ax.transAxes,
        ha="right",
        va="top",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "edgecolor": "#cccccc"},
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_pairwise_label_projections(dataset: DatasetBundle, config: BenchmarkConfig, output_path: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 8.2))
    pairs = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    for ax, (i, j) in zip(axes.ravel(), pairs):
        ax.scatter(
            dataset.pool_original[:, i],
            dataset.pool_original[:, j],
            c=dataset.pool_labels,
            cmap="coolwarm",
            vmin=-1,
            vmax=1,
            s=8,
            alpha=0.42,
            linewidths=0,
        )
        ax.set_xlabel(f"x{i}")
        ax.set_ylabel(f"x{j}")
        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(0.0, 1.0)
        ax.grid(alpha=0.18)
    fig.suptitle(f"{config.display_name}: seed 0 pairwise exact label projections", fontsize=14)
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_hartmann_slices(config: BenchmarkConfig, output_path: Path) -> None:
    pairs = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    grid = np.linspace(0.0, 1.0, 170)
    xx, yy = np.meshgrid(grid, grid)
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 8.2))
    for ax, (i, j) in zip(axes.ravel(), pairs):
        original = np.full((grid.size * grid.size, 4), 0.5, dtype=float)
        original[:, i] = xx.ravel()
        original[:, j] = yy.ravel()
        values = hartmann4(original).reshape(xx.shape)
        labels = np.where(values >= config.threshold, 1.0, -1.0)
        ax.contourf(xx, yy, labels, levels=[-1.5, 0.0, 1.5], colors=["#dbeafe", "#fee2e2"], alpha=0.8)
        ax.contour(xx, yy, values, levels=[config.threshold], colors="black", linewidths=1.8)
        ax.set_xlabel(f"x{i}")
        ax.set_ylabel(f"x{j}")
        ax.set_title(f"x{i} vs x{j}; other dims = 0.5")
        ax.grid(alpha=0.15)
    fig.suptitle(f"{config.display_name}: exact threshold slices", fontsize=14)
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def write_benchmark_notes(result: BenchmarkResult, output_path: Path, options: RunOptions) -> None:
    best_global = next(row for row in result.best_rows if row["metric"] == "global_error")
    best_q20 = next(row for row in result.best_rows if row["metric"] == "near_boundary_error_q20")
    best_q30 = next(row for row in result.best_rows if row["metric"] == "near_boundary_error_q30")
    ivr = next((row for row in result.final_rows if row["acquisition_rule"] == "gpr_boundary_weighted_ivr"), None)
    sur = next((row for row in result.final_rows if row["acquisition_rule"] == "gpr_bernoulli_sur_refit"), None)
    randomized = next((row for row in result.final_rows if row["acquisition_rule"] == "randomized_straddle"), None)
    lines = [
        f"# Week 7 Notes: {result.config.display_name}",
        "",
        "## Setup",
        "",
        f"- Domain: `{result.config.domain}`.",
        f"- Threshold: `{result.config.threshold:.8f}` ({result.config.threshold_percentile:.0f}th percentile, seed `{result.config.threshold_seed}`, sample size `{result.config.threshold_sample_size}`).",
        f"- Pool/test/initial/budget: `{result.config.pool_size}` / `{result.config.test_size}` / `{result.config.initial_size}` / `{result.config.total_budget}`.",
        f"- Reference size requested for IVR/SUR: `{options.reference_size}`.",
        f"- SUR shortlist size requested: `{options.sur_shortlist_size}`.",
        "",
        "## Best final methods",
        "",
        f"- Global: `{best_global['surrogate_variant']}` / `{best_global['acquisition_rule']}` = `{float(best_global['value']):.3f}`.",
        f"- q20: `{best_q20['surrogate_variant']}` / `{best_q20['acquisition_rule']}` = `{float(best_q20['value']):.3f}`.",
        f"- q30: `{best_q30['surrogate_variant']}` / `{best_q30['acquisition_rule']}` = `{float(best_q30['value']):.3f}`.",
        "",
        "## New GP-regressor methods",
        "",
    ]
    if ivr is not None:
        lines.append(
            f"- `gpr_boundary_weighted_ivr`: global/q20/q30 = `{float(ivr['mean_final_global_error']):.3f}` / `{float(ivr['mean_final_near_boundary_error_q20']):.3f}` / `{float(ivr['mean_final_near_boundary_error_q30']):.3f}`."
        )
    if sur is not None:
        lines.append(
            f"- `gpr_bernoulli_sur_refit`: global/q20/q30 = `{float(sur['mean_final_global_error']):.3f}` / `{float(sur['mean_final_near_boundary_error_q20']):.3f}` / `{float(sur['mean_final_near_boundary_error_q30']):.3f}`."
        )
    if randomized is not None and ivr is not None and sur is not None:
        new_q20 = min(float(ivr["mean_final_near_boundary_error_q20"]), float(sur["mean_final_near_boundary_error_q20"]))
        new_q30 = min(float(ivr["mean_final_near_boundary_error_q30"]), float(sur["mean_final_near_boundary_error_q30"]))
        lines.append(
            f"- Best new GP-regressor method beats `randomized_straddle` on q20: `{new_q20 < float(randomized['mean_final_near_boundary_error_q20'])}`."
        )
        lines.append(
            f"- Best new GP-regressor method beats `randomized_straddle` on q30: `{new_q30 < float(randomized['mean_final_near_boundary_error_q30'])}`."
        )
    lines.extend(
        [
            "",
            "## Caveats",
            "",
            "- The GP-regressor membership probability is `Phi(mu / sigma)`, a heuristic latent probability rather than calibrated class probability.",
            "- The GP-regressor SUR fantasy update keeps the current kernel hyperparameters fixed and uses an exact rank-one posterior update.",
            "- q20/q30 are the primary boundary metrics; q10 is retained as a noisy diagnostic.",
            "- Query distance and uncertainty-region fraction are diagnostics, not success criteria.",
            "- Lower integrated Bernoulli uncertainty can still mean confident wrongness if the surrogate is miscalibrated.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_benchmark_outputs(result: BenchmarkResult, options: RunOptions) -> None:
    benchmark_dir = options.output_dir / result.config.output_name
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    new_metadata_rows = [
        row
        for row in result.query_rows
        if row["acquisition_rule"] in set(GPR_NEW_METHODS + GPC_SUR_METHODS)
    ]
    write_csv(benchmark_dir / "raw_metric_curves.csv", result.metric_rows)
    write_csv(benchmark_dir / "query_distance_table.csv", result.query_rows)
    write_csv(benchmark_dir / "new_method_metadata.csv", new_metadata_rows)
    write_csv(benchmark_dir / "final_metrics_table.csv", result.final_rows)
    write_csv(benchmark_dir / "runtime_summary.csv", runtime_summary_rows(result.runtime_rows, result.config.name))
    (benchmark_dir / "summary.json").write_text(json.dumps(json_ready(result.summary), indent=2), encoding="utf-8")
    plot_metric_curves(result.metric_rows, "global_error", result.config, benchmark_dir / "global_error_curves.png", f"{result.config.display_name}: global error", "Global test-label error")
    plot_metric_curves(result.metric_rows, "near_boundary_error_q20", result.config, benchmark_dir / "q20_error_curves.png", f"{result.config.display_name}: q20 near-boundary error", "Error on closest 20% test points")
    plot_metric_curves(result.metric_rows, "near_boundary_error_q30", result.config, benchmark_dir / "q30_error_curves.png", f"{result.config.display_name}: q30 near-boundary error", "Error on closest 30% test points")
    plot_final_bar(result.final_rows, result.config, benchmark_dir / "final_global_q20_q30_bar.png")
    plot_query_distance_boxplot(result.query_rows, result.config, benchmark_dir / "query_distance_boxplot.png")
    plot_query_distance_over_budget(result.query_rows, result.config, benchmark_dir / "median_query_distance_over_budget.png")
    plot_metric_curves(result.metric_rows, "uncertainty_region_fraction", result.config, benchmark_dir / "uncertainty_region_curves.png", f"{result.config.display_name}: uncertainty-region fraction", "Fraction in surrogate uncertainty region")
    plot_metric_curves(result.metric_rows, "integrated_bernoulli_uncertainty", result.config, benchmark_dir / "integrated_bernoulli_uncertainty_curves.png", f"{result.config.display_name}: integrated Bernoulli uncertainty", "Mean p(+1)(1-p(+1)) on test coordinates")
    if result.config.name == "hartmann4":
        plot_hartmann_value_distribution(result.config, benchmark_dir / "hartmann4_value_distribution.png")
        seed0_run = next(run for run in result.runs if run.seed == 0)
        seed0_design = result.config.create_design(0, result.config.threshold)
        plot_pairwise_label_projections(seed0_design.dataset, result.config, benchmark_dir / "hartmann4_pairwise_label_projections_seed0.png")
        plot_hartmann_slices(result.config, benchmark_dir / "hartmann4_exact_2d_slices.png")
    write_benchmark_notes(result, benchmark_dir / "week7_notes.md", options)


def build_summary(
    config: BenchmarkConfig,
    options: RunOptions,
    seeds: tuple[int, ...],
    final_rows: list[dict[str, object]],
    fairness: dict[str, object],
    total_runtime_seconds: float,
) -> dict[str, object]:
    return {
        "experiment": f"week7_boundary_weighted_sur_{config.name}",
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
        "reference_size": options.reference_size,
        "sur_shortlist_size": options.sur_shortlist_size,
        "gpc_sur_limit_note": options.gpc_sur_limit_note,
        "methods": [
            {
                "surrogate_variant": row["surrogate_variant"],
                "acquisition_rule": row["acquisition_rule"],
                "seed_count": row["seed_count"],
            }
            for row in final_rows
        ],
        "best_method_by_metric": best_rows_for_benchmark(final_rows),
        "final_metrics": final_rows,
        "fairness_checks": fairness,
        "total_runtime_seconds": total_runtime_seconds,
        "method_definitions": {
            "gpr_boundary_weighted_ivr": "straddle-gated weighted posterior variance reduction with weights p(1-p)",
            "gpr_bernoulli_sur_refit": "expected one-step reduction in Bernoulli p(1-p) uncertainty using fixed-kernel fantasy posterior updates",
            "gpc_bernoulli_sur_refit": "classifier probability fantasy-refit SUR, limited by default for runtime",
        },
        "caveats": [
            "GP-regressor p(+1)=Phi(mu/sigma) is heuristic, not calibrated.",
            "The GP-regressor SUR fantasy update keeps kernel hyperparameters fixed.",
            "q20/q30 are primary; q10 is noisy.",
            "Integrated uncertainty is diagnostic and can be misaligned with true boundary error.",
        ],
    }


def run_benchmark(
    config: BenchmarkConfig,
    options: RunOptions,
    methods_by_seed: dict[int, tuple[str, ...]],
) -> BenchmarkResult:
    seeds = tuple(sorted(methods_by_seed))
    print(
        f"Running {config.display_name}: {len(seeds)} seed(s), "
        f"{len(set(method for methods in methods_by_seed.values() for method in methods))} method(s).",
        flush=True,
    )
    start = time.perf_counter()
    designs = {seed: config.create_design(seed, config.threshold) for seed in seeds}
    runs: list[MethodRun] = []
    for seed in seeds:
        for method in methods_by_seed[seed]:
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
    summary = build_summary(config, options, seeds, final_rows, fairness, elapsed)
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


def prior_regressor_candidate_paths(benchmark: str) -> list[Path]:
    return [
        PROJECT_ROOT / "outputs" / "week5_3_gated_geometric_boundary_contraction" / benchmark / "final_metrics_table.csv",
        PROJECT_ROOT / "outputs" / "week5_2_lookahead_boundary_uncertainty" / benchmark / "final_metrics_table.csv",
        PROJECT_ROOT / "outputs" / "week5_boundary_gated_diversified_straddle_comparison" / benchmark / "final_metrics_table.csv",
        PROJECT_ROOT / "outputs" / "week5_diversified_straddle_comparison" / benchmark / "final_metrics_table.csv",
        PROJECT_ROOT / "outputs" / "week4_boundary_metrics" / benchmark / "final_boundary_metrics_table.csv",
    ]


def load_previous_best_rows(benchmark: str) -> list[dict[str, object]]:
    fields = {
        "global_error": "mean_final_global_error",
        "near_boundary_error_q20": "mean_final_near_boundary_error_q20",
        "near_boundary_error_q30": "mean_final_near_boundary_error_q30",
    }
    candidates: list[dict[str, object]] = []
    for path in prior_regressor_candidate_paths(benchmark):
        for row in read_csv_rows(path):
            if "method" in row:
                item = dict(row)
                item["source_file"] = str(path.relative_to(PROJECT_ROOT))
                item["reference_family"] = "previous_gp_regressor"
                candidates.append(item)
    week6_path = PROJECT_ROOT / "outputs" / "week6_gp_classifier_surrogate_comparison" / benchmark / "final_metrics_table.csv"
    for row in read_csv_rows(week6_path):
        if "method" in row:
            item = dict(row)
            item["source_file"] = str(week6_path.relative_to(PROJECT_ROOT))
            item["reference_family"] = "previous_fixed_gpc"
            candidates.append(item)
    week61_path = PROJECT_ROOT / "outputs" / "week6_1_optimized_gp_classifier_surrogate_comparison" / benchmark / "final_metrics_table.csv"
    for row in read_csv_rows(week61_path):
        if "acquisition_rule" in row:
            item = dict(row)
            item["method"] = row.get("acquisition_rule", row.get("method", ""))
            item["source_file"] = str(week61_path.relative_to(PROJECT_ROOT))
            item["reference_family"] = f"previous_{row.get('surrogate_variant', 'optimized_gpc')}"
            candidates.append(item)
    rows: list[dict[str, object]] = []
    for metric, field in fields.items():
        metric_candidates = [row for row in candidates if parse_float(row.get(field)) is not None]
        if not metric_candidates:
            rows.append({"benchmark": benchmark, "metric": metric, "reference_available": False})
            continue
        best = min(metric_candidates, key=lambda row: float(row[field]))
        rows.append(
            {
                "benchmark": benchmark,
                "metric": metric,
                "reference_available": True,
                "reference_family": best["reference_family"],
                "reference_source": best["source_file"],
                "reference_method": best["method"],
                "reference_value": best[field],
            }
        )
    return rows


def metric_field(metric: str) -> str:
    return {
        "global_error": "mean_final_global_error",
        "near_boundary_error_q20": "mean_final_near_boundary_error_q20",
        "near_boundary_error_q30": "mean_final_near_boundary_error_q30",
    }[metric]


def find_final_row(final_rows: list[dict[str, object]], method: str) -> dict[str, object] | None:
    return next((row for row in final_rows if row["acquisition_rule"] == method), None)


def new_methods_vs_baselines_rows(results: list[BenchmarkResult]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for result in results:
        final_rows = result.final_rows
        for metric in ("global_error", "near_boundary_error_q20", "near_boundary_error_q30"):
            field = metric_field(metric)
            baseline_methods = ["straddle", "randomized_straddle", "classifier_uncertainty_repulsion"]
            for new_method in GPR_NEW_METHODS + GPC_SUR_METHODS:
                new_row = find_final_row(final_rows, new_method)
                if new_row is None:
                    continue
                for baseline in baseline_methods:
                    base_row = find_final_row(final_rows, baseline)
                    if base_row is None:
                        continue
                    new_value = float(new_row[field])
                    base_value = float(base_row[field])
                    rows.append(
                        {
                            "benchmark": result.config.name,
                            "metric": metric,
                            "new_method": new_method,
                            "new_surrogate_variant": new_row["surrogate_variant"],
                            "new_value": f"{new_value:.6f}",
                            "new_seed_count": new_row["seed_count"],
                            "baseline_method": baseline,
                            "baseline_surrogate_variant": base_row["surrogate_variant"],
                            "baseline_value": f"{base_value:.6f}",
                            "baseline_seed_count": base_row["seed_count"],
                            "new_beats_baseline": new_value < base_value,
                            "comparison_limited_by_seed_count": int(new_row["seed_count"]) != int(base_row["seed_count"]),
                            "difference_new_minus_baseline": f"{new_value - base_value:.6f}",
                        }
                    )
    return rows


def surrogate_comparison_rows(results: list[BenchmarkResult]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for result in results:
        for metric in ("global_error", "near_boundary_error_q20", "near_boundary_error_q30"):
            field = metric_field(metric)
            gpr_rows = [row for row in result.final_rows if row["surrogate_variant"] == "gpr_fixed_or_existing"]
            gpc_rows = [row for row in result.final_rows if row["surrogate_variant"] == "gpc_fixed_iso"]
            best_gpr = min(gpr_rows, key=lambda row: float(row[field])) if gpr_rows else None
            best_gpc = min(gpc_rows, key=lambda row: float(row[field])) if gpc_rows else None
            row: dict[str, object] = {"benchmark": result.config.name, "metric": metric}
            if best_gpr is not None:
                row["best_current_gpr_method"] = best_gpr["acquisition_rule"]
                row["best_current_gpr_value"] = best_gpr[field]
            if best_gpc is not None:
                row["best_current_gpc_method"] = best_gpc["acquisition_rule"]
                row["best_current_gpc_value"] = best_gpc[field]
                if best_gpr is not None:
                    row["current_gpc_beats_current_gpr"] = float(best_gpc[field]) < float(best_gpr[field])
            for previous in load_previous_best_rows(result.config.name):
                if previous["metric"] == metric and previous.get("reference_available"):
                    row["best_previous_reference_family"] = previous["reference_family"]
                    row["best_previous_reference_method"] = previous["reference_method"]
                    row["best_previous_reference_value"] = previous["reference_value"]
                    if best_gpr is not None:
                        row["current_gpr_beats_best_previous_reference"] = float(best_gpr[field]) < float(previous["reference_value"])
                    if best_gpc is not None:
                        row["current_gpc_beats_best_previous_reference"] = float(best_gpc[field]) < float(previous["reference_value"])
            rows.append(row)
    return rows


def uncertainty_error_correlation_rows(results: list[BenchmarkResult]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for result in results:
        for metric in ("near_boundary_error_q20", "near_boundary_error_q30"):
            values = np.asarray([float(row[metric]) for row in result.metric_rows], dtype=float)
            uncertainty = np.asarray([float(row["integrated_bernoulli_uncertainty"]) for row in result.metric_rows], dtype=float)
            if len(values) > 1 and float(np.std(values)) > 1e-12 and float(np.std(uncertainty)) > 1e-12:
                corr = float(np.corrcoef(uncertainty, values)[0, 1])
            else:
                corr = float("nan")
            rows.append(
                {
                    "benchmark": result.config.name,
                    "metric": metric,
                    "pearson_corr_integrated_uncertainty_vs_error_over_all_curves": f"{corr:.6f}",
                    "row_count": len(values),
                }
            )
    return rows


def write_combined_summary(
    results: list[BenchmarkResult],
    options: RunOptions,
    combined_dir: Path,
    total_elapsed: float,
) -> None:
    best_rows = [row for result in results for row in result.best_rows]
    new_vs_base = new_methods_vs_baselines_rows(results)
    surrogate_rows = surrogate_comparison_rows(results)
    corr_rows = uncertainty_error_correlation_rows(results)
    write_csv(combined_dir / "week7_summary.csv", [result.summary for result in results])
    write_csv(combined_dir / "best_method_by_metric.csv", best_rows)
    write_csv(combined_dir / "new_methods_vs_baselines.csv", new_vs_base)
    write_csv(combined_dir / "surrogate_comparison.csv", surrogate_rows)
    write_csv(combined_dir / "uncertainty_error_correlation.csv", corr_rows)
    lines = [
        "# Week 7 Boundary-Weighted SUR Summary",
        "",
        "Week 7 tests boundary-weighted integrated variance reduction and Bernoulli stepwise uncertainty reduction on Branin, 4D Ackley, and 4D Hartmann.",
        "",
        "## Run settings",
        "",
        f"- Quick mode: `{options.quick}`.",
        f"- Reference size: `{options.reference_size}`.",
        f"- SUR shortlist size: `{options.sur_shortlist_size}`.",
        f"- GPC SUR shortlist size: `{options.gpc_sur_shortlist_size}`.",
        f"- GPC SUR limitation: {options.gpc_sur_limit_note}",
        f"- Total elapsed runtime for this script invocation: `{total_elapsed:.1f}` seconds.",
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
            f"| {result.config.display_name} | `{best_global['surrogate_variant']}` / `{best_global['acquisition_rule']}` ({float(best_global['value']):.3f}) | "
            f"`{best_q20['surrogate_variant']}` / `{best_q20['acquisition_rule']}` ({float(best_q20['value']):.3f}) | "
            f"`{best_q30['surrogate_variant']}` / `{best_q30['acquisition_rule']}` ({float(best_q30['value']):.3f}) |"
        )
    lines.extend(["", "## Interpretation Questions", ""])
    for result in results:
        randomized = find_final_row(result.final_rows, "randomized_straddle")
        ivr = find_final_row(result.final_rows, "gpr_boundary_weighted_ivr")
        sur = find_final_row(result.final_rows, "gpr_bernoulli_sur_refit")
        repulsion = find_final_row(result.final_rows, "classifier_uncertainty_repulsion")
        gpc_sur = find_final_row(result.final_rows, "gpc_bernoulli_sur_refit")
        lines.append(f"### {result.config.display_name}")
        if randomized and ivr and sur:
            new_q20 = min(float(ivr["mean_final_near_boundary_error_q20"]), float(sur["mean_final_near_boundary_error_q20"]))
            new_q30 = min(float(ivr["mean_final_near_boundary_error_q30"]), float(sur["mean_final_near_boundary_error_q30"]))
            lines.append(
                f"1. Best new GPR SUR/IVR beats `randomized_straddle` on q20/q30: `{new_q20 < float(randomized['mean_final_near_boundary_error_q20'])}` / `{new_q30 < float(randomized['mean_final_near_boundary_error_q30'])}`."
            )
            sur_better_ivr_q20 = float(sur["mean_final_near_boundary_error_q20"]) < float(ivr["mean_final_near_boundary_error_q20"])
            sur_better_ivr_q30 = float(sur["mean_final_near_boundary_error_q30"]) < float(ivr["mean_final_near_boundary_error_q30"])
            lines.append(f"2. `gpr_bernoulli_sur_refit` improves over cheap IVR on q20/q30: `{sur_better_ivr_q20}` / `{sur_better_ivr_q30}`.")
        if gpc_sur and repulsion:
            lines.append(
                f"3. Classifier SUR beats `classifier_uncertainty_repulsion` on q20/q30: `{float(gpc_sur['mean_final_near_boundary_error_q20']) < float(repulsion['mean_final_near_boundary_error_q20'])}` / `{float(gpc_sur['mean_final_near_boundary_error_q30']) < float(repulsion['mean_final_near_boundary_error_q30'])}`."
            )
        elif repulsion:
            lines.append("3. Classifier SUR was not run for this benchmark in the configured limited mode.")
        corr_q20 = next(row for row in corr_rows if row["benchmark"] == result.config.name and row["metric"] == "near_boundary_error_q20")
        corr_q30 = next(row for row in corr_rows if row["benchmark"] == result.config.name and row["metric"] == "near_boundary_error_q30")
        lines.append(
            f"6. Integrated Bernoulli uncertainty correlation with q20/q30 error over all curves: `{corr_q20['pearson_corr_integrated_uncertainty_vs_error_over_all_curves']}` / `{corr_q30['pearson_corr_integrated_uncertainty_vs_error_over_all_curves']}`."
        )
        if ivr and randomized:
            confidently_wrong = (
                float(ivr["mean_final_integrated_bernoulli_uncertainty"]) < float(randomized["mean_final_integrated_bernoulli_uncertainty"])
                and float(ivr["mean_final_near_boundary_error_q20"]) > float(randomized["mean_final_near_boundary_error_q20"])
            )
            lines.append(f"7. Cheap IVR reduces integrated uncertainty while worsening q20 versus randomized straddle: `{confidently_wrong}`.")
        lines.append("")
    lines.extend(
        [
            "## Cross-benchmark answer",
            "",
            "Do not overclaim: this is a benchmark result for the current sklearn GP surrogates. If the new methods win on Branin/Hartmann but fail on Ackley, the correct thesis interpretation is that the acquisition objective may be useful but the harder Ackley geometry or surrogate calibration remains the bottleneck. If they reduce integrated uncertainty without improving q20/q30, the objective is misaligned under this surrogate.",
            "",
            "q20/q30 remain the primary thesis metrics. Query distance, uncertainty-region fraction, and integrated Bernoulli uncertainty are diagnostics for explaining behavior, not standalone success criteria.",
        ]
    )
    (combined_dir / "week7_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_hartmann_notes(results, combined_dir / "hartmann4_benchmark_notes.md")
    write_slide_notes(results, combined_dir / "week7_slide_notes.md")
    write_run_report(results, options, total_elapsed, combined_dir / "codex_run_report.md")


def write_hartmann_notes(results: list[BenchmarkResult], output_path: Path) -> None:
    hartmann = next((result for result in results if result.config.name == "hartmann4"), None)
    ackley = next((result for result in results if result.config.name == "ackley"), None)
    lines = [
        "# Hartmann4 Benchmark Notes",
        "",
        "Hartmann4 is a standard deterministic 4D function on `[0,1]^4`. Week 7 thresholds it at the 50th percentile and uses exact labels `+1` if `f(x) >= threshold`, else `-1`.",
    ]
    if hartmann:
        lines.extend(
            [
                "",
                f"- Threshold: `{hartmann.config.threshold:.8f}` from `{hartmann.config.threshold_sample_size}` samples with seed `{hartmann.config.threshold_seed}`.",
                "- Saved diagnostics: `hartmann4_value_distribution.png`, `hartmann4_pairwise_label_projections_seed0.png`, and `hartmann4_exact_2d_slices.png`.",
            ]
        )
        best_q20 = next(row for row in hartmann.best_rows if row["metric"] == "near_boundary_error_q20")
        best_q30 = next(row for row in hartmann.best_rows if row["metric"] == "near_boundary_error_q30")
        lines.append(f"- Best Hartmann q20/q30: `{best_q20['acquisition_rule']}` / `{best_q30['acquisition_rule']}`.")
    if hartmann and ackley:
        h_best = next(row for row in hartmann.best_rows if row["metric"] == "near_boundary_error_q20")
        a_best = next(row for row in ackley.best_rows if row["metric"] == "near_boundary_error_q20")
        lines.append(
            f"- Ackley q20 best method is `{a_best['acquisition_rule']}`; Hartmann q20 best method is `{h_best['acquisition_rule']}`. Agreement should be judged by method family and q20/q30 behavior, not by global error alone."
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_slide_notes(results: list[BenchmarkResult], output_path: Path) -> None:
    lines = [
        "# Week 7 Slide Notes",
        "",
        "## Question",
        "",
        "Can a boundary-weighted global uncertainty-reduction rule beat pointwise rules such as straddle and randomized straddle?",
        "",
        "## Methods",
        "",
        "- `gpr_boundary_weighted_ivr`: straddle-gated posterior variance reduction weighted by Bernoulli membership uncertainty.",
        "- `gpr_bernoulli_sur_refit`: expected reduction in integrated `p(1-p)` after fantasy `+1/-1` updates.",
        "- `gpc_bernoulli_sur_refit`: same idea with fixed GP-classifier probabilities, run in limited mode if needed.",
        "",
        "## Best final rows",
        "",
    ]
    for result in results:
        for metric in ("global_error", "near_boundary_error_q20", "near_boundary_error_q30"):
            best = next(row for row in result.best_rows if row["metric"] == metric)
            lines.append(
                f"- {result.config.name} {metric}: `{best['surrogate_variant']}` / `{best['acquisition_rule']}` = `{float(best['value']):.3f}`."
            )
    lines.extend(
        [
            "",
            "## Message",
            "",
            "Use q20/q30 as the main boundary-estimation metrics. Do not claim novelty beyond a literature-inspired SUR/IVR benchmark. If uncertainty falls without q20/q30 improvement, describe objective-surrogate misalignment rather than success.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_run_report(
    results: list[BenchmarkResult],
    options: RunOptions,
    total_elapsed: float,
    output_path: Path,
) -> None:
    lines = [
        "# Codex Run Report",
        "",
        f"- Script elapsed time: `{total_elapsed:.1f}` seconds.",
        f"- Output directory: `{options.output_dir}`.",
        f"- Quick mode: `{options.quick}`.",
        f"- Max seeds: `{options.max_seeds}`.",
        f"- Reference size: `{options.reference_size}`.",
        f"- SUR shortlist size: `{options.sur_shortlist_size}`.",
        f"- GPC SUR shortlist size: `{options.gpc_sur_shortlist_size}`.",
        f"- Skip GPC SUR: `{options.skip_gpc_sur}`.",
        f"- GPC SUR limit note: {options.gpc_sur_limit_note}",
        "",
        "## Benchmarks",
        "",
    ]
    for result in results:
        seed_count = len({run.seed for run in result.runs})
        if seed_count == 0:
            seed_count = len({int(row["seed"]) for row in result.metric_rows})
        lines.append(
            f"- {result.config.name}: `{seed_count}` seeds, `{len(result.final_rows)}` method rows, fairness passed `{result.fairness_checks.get('all_checks_passed')}`."
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def methods_by_seed_for_config(
    config: BenchmarkConfig,
    seeds: tuple[int, ...],
    options: RunOptions,
) -> dict[int, tuple[str, ...]]:
    main_methods = GPR_BASELINE_METHODS + GPR_NEW_METHODS + GPC_BASELINE_METHODS
    methods_by_seed: dict[int, tuple[str, ...]] = {}
    for seed in seeds:
        methods = list(main_methods)
        include_gpc_sur = False
        if not options.skip_gpc_sur and config.name in options.gpc_sur_benchmarks:
            if options.gpc_sur_max_seeds is None:
                include_gpc_sur = True
            else:
                include_gpc_sur = seed in seeds[: options.gpc_sur_max_seeds]
        if include_gpc_sur:
            methods.extend(GPC_SUR_METHODS)
        methods_by_seed[seed] = tuple(methods)
    return methods_by_seed


def run_experiment(options: RunOptions) -> list[BenchmarkResult]:
    options.output_dir.mkdir(parents=True, exist_ok=True)
    configs = build_configs(options.quick)
    seeds = SEEDS if not options.quick else (0,)
    if options.max_seeds is not None:
        seeds = tuple(seeds[: options.max_seeds])
    results: list[BenchmarkResult] = []
    start = time.perf_counter()
    for config in configs:
        result = run_benchmark(
            config,
            options,
            methods_by_seed=methods_by_seed_for_config(config, seeds, options),
        )
        results.append(result)
    total_elapsed = time.perf_counter() - start
    combined_dir = options.output_dir / "combined"
    combined_dir.mkdir(parents=True, exist_ok=True)
    write_combined_summary(results, options, combined_dir, total_elapsed)
    return results


def refresh_existing_summaries(options: RunOptions) -> list[BenchmarkResult]:
    """Rebuild summary CSV/Markdown files from existing raw Week 7 outputs."""
    configs = build_configs(quick=False)
    results: list[BenchmarkResult] = []
    for config in configs:
        benchmark_dir = options.output_dir / config.output_name
        metric_rows = read_csv_rows(benchmark_dir / "raw_metric_curves.csv")
        query_rows = read_csv_rows(benchmark_dir / "query_distance_table.csv")
        if not metric_rows or not query_rows:
            raise FileNotFoundError(f"Missing existing raw outputs for {config.name} in {benchmark_dir}")
        final_rows = summarize_final_metrics(config, metric_rows, query_rows)
        best_rows = best_rows_for_benchmark(final_rows)
        prior_summary_path = benchmark_dir / "summary.json"
        prior_summary: dict[str, object] = {}
        if prior_summary_path.exists():
            prior_summary = json.loads(prior_summary_path.read_text(encoding="utf-8"))
            fairness = prior_summary.get("fairness_checks", {"all_checks_passed": "unknown"})
        else:
            fairness = {"all_checks_passed": "unknown"}
        summary = {
            **(prior_summary if prior_summary_path.exists() else {}),
            "best_method_by_metric": best_rows,
            "final_metrics": final_rows,
            "summary_refreshed_from_existing_outputs": True,
            "best_method_note": "Best rows exclude limited-seed methods so full-seed methods are compared fairly.",
        }
        result = BenchmarkResult(
            config=config,
            runs=[],
            fairness_checks=fairness,
            metric_rows=metric_rows,
            query_rows=query_rows,
            final_rows=final_rows,
            runtime_rows=[],
            best_rows=best_rows,
            summary=summary,
        )
        write_csv(benchmark_dir / "final_metrics_table.csv", final_rows)
        (benchmark_dir / "summary.json").write_text(json.dumps(json_ready(summary), indent=2), encoding="utf-8")
        write_benchmark_notes(result, benchmark_dir / "week7_notes.md", options)
        results.append(result)
    combined_dir = options.output_dir / "combined"
    combined_dir.mkdir(parents=True, exist_ok=True)
    elapsed = elapsed_from_full_run_log(options.output_dir / "full_run_stdout.log")
    write_combined_summary(results, options, combined_dir, total_elapsed=elapsed)
    return results


def elapsed_from_full_run_log(path: Path) -> float:
    if not path.exists():
        return 0.0
    for line in reversed(path.read_text(encoding="utf-8", errors="ignore").splitlines()):
        marker = "Week 7 boundary-weighted SUR benchmark complete in "
        if marker in line:
            try:
                return float(line.split(marker, 1)[1].split("s", 1)[0])
            except (IndexError, ValueError):
                return 0.0
    return 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Week 7 boundary-weighted IVR / Bernoulli SUR benchmark")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true", help="Run a reduced smoke benchmark")
    mode.add_argument("--full", action="store_true", help="Run the full Week 7 benchmark")
    parser.add_argument("--max-seeds", type=int, default=None, help="Limit the number of main-run seeds")
    parser.add_argument("--skip-gpc-sur", action="store_true", help="Skip the expensive GPC Bernoulli SUR method")
    parser.add_argument("--sur-shortlist-size", type=int, default=40, help="SUR fantasy shortlist size")
    parser.add_argument("--reference-size", type=int, default=1500, help="Reference subset size for IVR/SUR")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory override")
    parser.add_argument("--summarize-existing", action="store_true", help="Refresh summary files from existing Week 7 raw outputs without rerunning models")
    return parser.parse_args()


def options_from_args(args: argparse.Namespace) -> RunOptions:
    if args.sur_shortlist_size < 1:
        raise ValueError("--sur-shortlist-size must be positive")
    if args.reference_size < 1:
        raise ValueError("--reference-size must be positive")
    quick = bool(args.quick)
    full = bool(args.full or not args.quick)
    if args.output_dir is not None:
        output_dir = args.output_dir
    elif quick:
        output_dir = OUTPUT_DIR / "quick"
    else:
        output_dir = OUTPUT_DIR
    if args.skip_gpc_sur:
        gpc_sur_benchmarks: tuple[str, ...] = ()
        gpc_sur_max_seeds: int | None = 0
        gpc_sur_shortlist_size = 0
        note = "GPC SUR skipped by --skip-gpc-sur."
    elif quick:
        gpc_sur_benchmarks = ("branin", "ackley", "hartmann4")
        gpc_sur_max_seeds = None
        gpc_sur_shortlist_size = min(int(args.sur_shortlist_size), 10)
        note = (
            "Quick mode runs GPC SUR on all quick benchmarks with classifier "
            f"SUR shortlist capped at {gpc_sur_shortlist_size}."
        )
    else:
        gpc_sur_benchmarks = ("branin", "hartmann4")
        gpc_sur_max_seeds = 1
        gpc_sur_shortlist_size = min(int(args.sur_shortlist_size), 15)
        note = (
            "Full mode limits expensive GPC SUR to Branin and Hartmann4 for "
            f"seed 0 only, with classifier SUR shortlist capped at {gpc_sur_shortlist_size}; "
            "GPR methods and GPC baselines run fully."
        )
    return RunOptions(
        quick=quick,
        full=full,
        max_seeds=args.max_seeds,
        skip_gpc_sur=bool(args.skip_gpc_sur),
        sur_shortlist_size=int(args.sur_shortlist_size),
        reference_size=int(args.reference_size),
        output_dir=output_dir,
        gpc_sur_benchmarks=gpc_sur_benchmarks,
        gpc_sur_max_seeds=gpc_sur_max_seeds,
        gpc_sur_shortlist_size=gpc_sur_shortlist_size,
        gpc_sur_limit_note=note,
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
    print(f"Week 7 boundary-weighted SUR benchmark complete in {elapsed:.1f}s ({mode} mode).")
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
