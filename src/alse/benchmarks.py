"""Synthetic level-set benchmarks: oracles, thresholds, pools/test sets, seed designs.

Ported from the archive's ``branin_week1.py`` (Branin, S1 settings),
``week3_4d_named_benchmark_comparison.py`` (Ackley4, S2 settings),
``week4_08_boundary_weighted_sur.py`` (Hartmann4, Exp 08/09 settings) and the
superseded ``week3_4d_benchmark_comparison.py`` (controlled 4D function,
definition kept for the record). Every benchmark follows the same recipe:

* threshold  = percentile of ``fn`` over ``threshold_sample_size`` uniform draws
  from ``default_rng(threshold_seed)``;
* dataset    = pool then test drawn from ``default_rng(seed)``, labels
  ``+1`` iff ``fn(x) >= threshold`` else ``-1``, inputs scaled to ``[0, 1]^d``;
* initial design = ``init_size`` pool rows drawn without replacement from
  ``default_rng(seed + seed_offset)``, redrawn until both classes occur.

The seed offsets, sample sizes, percentiles and RNG salts are frozen: every
stored synthetic table depends on them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from alse.io import require

Array = np.ndarray


# --- oracles -----------------------------------------------------------------


def branin(X: Array) -> Array:
    """Standard Branin on rows [x1, x2] (a=1, b=5.1/(4 pi^2), c=5/pi, r=6, s=10, t=1/(8 pi)).

    frozen: branin_week1.py::branin
    """
    X = np.asarray(X, dtype=float)
    x1, x2 = X[:, 0], X[:, 1]
    a = 1.0
    b = 5.1 / (4.0 * np.pi**2)
    c = 5.0 / np.pi
    r = 6.0
    s = 10.0
    t = 1.0 / (8.0 * np.pi)
    return a * (x2 - b * x1**2 + c * x1 - r) ** 2 + s * (1.0 - t) * np.cos(x1) + s


def ackley4(X: Array) -> Array:
    """Standard Ackley (a=20, b=0.2, c=2 pi) on rows with four coordinates.

    frozen: week3_4d_named_benchmark_comparison.py::ackley_4d
    """
    X = np.asarray(X, dtype=float)
    if X.ndim != 2 or X.shape[1] != 4:
        raise ValueError("Ackley benchmark expects an array with shape (n, 4)")
    a = 20.0
    b = 0.2
    c = 2.0 * np.pi
    mean_square = np.mean(X**2, axis=1)
    mean_cosine = np.mean(np.cos(c * X), axis=1)
    return -a * np.exp(-b * np.sqrt(mean_square)) - np.exp(mean_cosine) + a + np.e


def hartmann4(X: Array) -> Array:
    """Standard 4D Hartmann on [0, 1]^4 (Hartmann-6 alpha/A/P tables truncated to 4 columns).

    frozen: week4_08_boundary_weighted_sur.py::hartmann4
    """
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


def controlled_4d(X: Array) -> Array:
    """Superseded custom 4D boundary function on [0, 1]^4 (tilted plane + waves + bump).

    Kept for the record only; the thesis uses Ackley4 instead.
    frozen: week3_4d_benchmark_comparison.py::controlled_4d_function
    """
    X = np.asarray(X, dtype=float)
    x0, x1, x2, x3 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
    tilted_plane = 0.95 * (x0 - 0.50) - 0.75 * (x1 - 0.50)
    tilted_plane += 0.65 * (x2 - 0.50) - 0.45 * (x3 - 0.50)
    wave_interactions = 0.30 * np.sin(2.0 * np.pi * (x0 + 0.35 * x3))
    wave_interactions += 0.24 * np.cos(2.0 * np.pi * (x1 - 0.60 * x2))
    curved_term = 0.50 * ((x0 - 0.58) ** 2 - 0.70 * (x1 - 0.42) ** 2)
    local_bump = -0.35 * np.exp(-(((x2 - 0.68) ** 2) / 0.030 + ((x3 - 0.32) ** 2) / 0.045))
    return tilted_plane + wave_interactions + curved_term + local_bump


# --- coordinates -------------------------------------------------------------


def scale_to_unit(X: Array, lower: Array, upper: Array) -> Array:
    """Affine map of the box [lower, upper] onto [0, 1]^d.

    frozen: branin_week1.py::scale_to_unit_square,
    week3_4d_named_benchmark_comparison.py::scale_to_unit_hypercube
    """
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    return (np.asarray(X) - lower) / (upper - lower)


def unscale_from_unit(U: Array, lower: Array, upper: Array) -> Array:
    """Inverse of :func:`scale_to_unit`.

    frozen: week3_4d_named_benchmark_comparison.py::unscale_from_unit_hypercube
    """
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    return lower + np.asarray(U) * (upper - lower)


# --- benchmark settings ------------------------------------------------------


@dataclass(frozen=True)
class Benchmark:
    """Frozen settings of one synthetic benchmark (oracle, box, threshold, sizes, seeds).

    ``seed_offset`` is added to the dataset seed for the initial-design RNG;
    ``rng_salt`` is the acquisition RNG namespace used with this benchmark
    (see ``acquisition.rng_for_method``).
    """

    name: str
    fn: Callable[[Array], Array]
    lower: tuple[float, ...]
    upper: tuple[float, ...]
    threshold_percentile: float
    threshold_sample_size: int
    threshold_seed: int
    pool_size: int
    test_size: int
    init_size: int
    budget: int
    seed_offset: int
    rng_salt: str

    @property
    def dim(self) -> int:
        return len(self.lower)

    @property
    def lower_array(self) -> Array:
        return np.asarray(self.lower, dtype=float)

    @property
    def upper_array(self) -> Array:
        return np.asarray(self.upper, dtype=float)


# frozen: branin_week1.py::DOMAIN_LOWER/DOMAIN_UPPER/compute_threshold/make_dataset,
#         week2_acquisition_comparison.py::create_seed_design (S1: init 6, budget 50)
BRANIN = Benchmark(
    name="branin",
    fn=branin,
    lower=(-5.0, 0.0),
    upper=(10.0, 15.0),
    threshold_percentile=45.0,
    threshold_sample_size=20_000,
    threshold_seed=2026,
    pool_size=1_500,
    test_size=4_000,
    init_size=6,
    budget=50,
    seed_offset=100_000,
    rng_salt="week2",  # seed namespace (acquisition_rules.rng_for_method)
)

# frozen: week3_4d_named_benchmark_comparison.py::DOMAIN_*/THRESHOLD_*/POOL_SIZE/
#         TEST_SIZE/INITIAL_LABELLED_SIZE/TOTAL_BUDGET/create_seed_design (S2)
ACKLEY4 = Benchmark(
    name="ackley4",
    fn=ackley4,
    lower=(-5.0,) * 4,
    upper=(5.0,) * 4,
    threshold_percentile=50.0,
    threshold_sample_size=100_000,
    threshold_seed=3027,
    pool_size=4_000,
    test_size=10_000,
    init_size=12,
    budget=80,
    seed_offset=300_000,
    rng_salt="week3_4d_ackley",  # seed namespace (rng_for_week3_named_method)
)

# frozen: week4_08_boundary_weighted_sur.py::HARTMANN_THRESHOLD_*/build_configs(full)/
#         create_hartmann_seed_design (Exp 08/09)
HARTMANN4 = Benchmark(
    name="hartmann4",
    fn=hartmann4,
    lower=(0.0,) * 4,
    upper=(1.0,) * 4,
    threshold_percentile=50.0,
    threshold_sample_size=100_000,
    threshold_seed=2026,
    pool_size=4_000,
    test_size=10_000,
    init_size=12,
    budget=80,
    seed_offset=700_000,
    rng_salt="week7",  # seed namespace (week4_08 rng_for_method -> stable_seed(seed, bench, method, 'week7'))
)

# frozen: week3_4d_benchmark_comparison.py::THRESHOLD_*/POOL_SIZE/TEST_SIZE/
#         create_seed_design (superseded; not in BENCHMARKS)
CONTROLLED_4D = Benchmark(
    name="controlled_4d",
    fn=controlled_4d,
    lower=(0.0,) * 4,
    upper=(1.0,) * 4,
    threshold_percentile=50.0,
    threshold_sample_size=100_000,
    threshold_seed=3026,
    pool_size=4_000,
    test_size=10_000,
    init_size=12,
    budget=80,
    seed_offset=200_000,
    rng_salt="week3_4d",  # seed namespace (rng_for_week3_method)
)

BENCHMARKS: dict[str, Benchmark] = {b.name: b for b in (BRANIN, ACKLEY4, HARTMANN4)}


# --- thresholds, labels, datasets ---------------------------------------------


def sample_domain(rng: np.random.Generator, benchmark: Benchmark, size: int) -> Array:
    """Uniform draws from the benchmark box, ``size`` rows (one RNG call, row-major).

    frozen: branin_week1.py::sample_domain, week3_4d_named_benchmark_comparison.py::
    sample_domain, week4_08_boundary_weighted_sur.py::sample_hartmann_domain
    """
    return rng.uniform(benchmark.lower_array, benchmark.upper_array, size=(size, benchmark.dim))


def compute_threshold(benchmark: Benchmark) -> float:
    """Percentile of ``fn`` over ``threshold_sample_size`` draws from ``default_rng(threshold_seed)``.

    Exact values: branin 29.121261109594627, ackley4 10.3322025066197,
    hartmann4 -0.9779783322256355, controlled_4d -0.00010735189280212856.
    frozen: branin_week1.py::compute_threshold,
    week3_4d_named_benchmark_comparison.py::threshold_sample_values/compute_threshold,
    week4_08_boundary_weighted_sur.py::compute_hartmann_threshold
    """
    rng = np.random.default_rng(benchmark.threshold_seed)
    values = benchmark.fn(sample_domain(rng, benchmark, benchmark.threshold_sample_size))
    return float(np.percentile(values, benchmark.threshold_percentile))


def labels_from_threshold(values: Array, threshold: float) -> Array:
    """+1.0 at or above the threshold, -1.0 below.

    frozen: branin_week1.py::labels_from_threshold (via values),
    week3_4d_named_benchmark_comparison.py::labels_from_values
    """
    return np.where(np.asarray(values) >= threshold, 1.0, -1.0)


@dataclass
class Dataset:
    """Pool and test set of one seed in original and unit-box coordinates."""

    pool: Array
    pool_scaled: Array
    pool_values: Array
    pool_labels: Array
    test: Array
    test_scaled: Array
    test_values: Array
    test_labels: Array
    threshold: float
    seed: int


def make_dataset(benchmark: Benchmark, seed: int, threshold: float | None = None) -> Dataset:
    """Pool then test from ``default_rng(seed)``; labels from ``threshold`` (default: computed).

    frozen: branin_week1.py::make_dataset, week3_4d_named_benchmark_comparison.py::
    make_dataset, week4_08_boundary_weighted_sur.py::make_hartmann_dataset
    """
    if threshold is None:
        threshold = compute_threshold(benchmark)
    rng = np.random.default_rng(seed)
    pool = sample_domain(rng, benchmark, benchmark.pool_size)
    test = sample_domain(rng, benchmark, benchmark.test_size)
    pool_values = benchmark.fn(pool)
    test_values = benchmark.fn(test)
    lower, upper = benchmark.lower_array, benchmark.upper_array
    return Dataset(
        pool=pool,
        pool_scaled=scale_to_unit(pool, lower, upper),
        pool_values=pool_values,
        pool_labels=labels_from_threshold(pool_values, threshold),
        test=test,
        test_scaled=scale_to_unit(test, lower, upper),
        test_values=test_values,
        test_labels=labels_from_threshold(test_values, threshold),
        threshold=float(threshold),
        seed=int(seed),
    )


# --- initial designs ---------------------------------------------------------


def random_two_class_initial_design(
    rng: np.random.Generator, labels: Array, size: int, max_attempts: int = 10_000
) -> tuple[Array, int]:
    """Draw ``size`` indices without replacement until both labels occur.

    Returns (indices, attempt count). frozen: branin_week1.py::random_two_class_initial_design
    """
    labels = np.asarray(labels)
    for attempt in range(1, max_attempts + 1):
        indices = rng.choice(len(labels), size=size, replace=False)
        if np.unique(labels[indices]).size == 2:
            return np.asarray(indices, dtype=int), attempt
    raise RuntimeError("Could not draw a two-class initial design")


def initial_design(benchmark: Benchmark, dataset: Dataset, seed: int) -> Array:
    """Shared initial labelled pool indices: ``default_rng(seed + seed_offset)`` two-class draw.

    frozen: week2_acquisition_comparison.py::create_seed_design (+100_000),
    week3_4d_named_benchmark_comparison.py::create_seed_design (+300_000),
    week4_08_boundary_weighted_sur.py::create_hartmann_seed_design (+700_000),
    week3_4d_benchmark_comparison.py::create_seed_design (+200_000)
    """
    require(dataset.seed == seed, "initial_design: dataset.seed must equal seed")
    rng = np.random.default_rng(seed + benchmark.seed_offset)
    indices, _ = random_two_class_initial_design(rng, dataset.pool_labels, benchmark.init_size)
    return indices


# --- plotting grid (2D only) -------------------------------------------------


def make_plot_grid(benchmark: Benchmark = BRANIN, size: int = 180) -> tuple[Array, Array, Array, Array]:
    """(xx, yy, original, scaled) meshgrid over a 2D benchmark box.

    frozen: branin_week1.py::make_plot_grid
    """
    require(benchmark.dim == 2, "make_plot_grid needs a 2D benchmark")
    x1 = np.linspace(benchmark.lower[0], benchmark.upper[0], size)
    x2 = np.linspace(benchmark.lower[1], benchmark.upper[1], size)
    xx, yy = np.meshgrid(x1, x2)
    original = np.column_stack([xx.ravel(), yy.ravel()])
    return xx, yy, original, scale_to_unit(original, benchmark.lower_array, benchmark.upper_array)
