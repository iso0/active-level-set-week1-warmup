"""Tests for alse.benchmarks: fast unit checks plus archive-equality gates."""

from __future__ import annotations

import json

import numpy as np
import pytest

from alse import benchmarks as bm
from alse.config import ARCHIVE_OUTPUTS

# Frozen thresholds (archive summary.json files, verbatim).
FROZEN_THRESHOLDS = {
    "branin": 29.121261109594627,
    "ackley4": 10.3322025066197,
    "hartmann4": -0.9779783322256355,
    "controlled_4d": -0.00010735189280212856,
}
ALL = (bm.BRANIN, bm.ACKLEY4, bm.HARTMANN4, bm.CONTROLLED_4D)


# --- fast unit tests ----------------------------------------------------------


def test_oracle_landmarks():
    # Branin global minimum 0.397887 at (pi, 2.275); Ackley(0) = 0; Hartmann4 < 0 everywhere.
    assert np.isclose(bm.branin(np.array([[np.pi, 2.275]]))[0], 0.397887, atol=1e-5)
    assert np.isclose(bm.ackley4(np.zeros((1, 4)))[0], 0.0, atol=1e-12)
    assert (bm.hartmann4(np.random.default_rng(0).uniform(size=(50, 4))) < 0).all()
    assert np.isfinite(bm.controlled_4d(np.random.default_rng(0).uniform(size=(50, 4)))).all()
    with pytest.raises(ValueError):
        bm.ackley4(np.zeros((3, 3)))
    with pytest.raises(ValueError):
        bm.hartmann4(np.zeros((3, 5)))


def test_scale_round_trip():
    X = np.random.default_rng(1).uniform(-5, 10, size=(20, 2))
    U = bm.scale_to_unit(X, bm.BRANIN.lower, bm.BRANIN.upper)
    assert np.allclose(bm.unscale_from_unit(U, bm.BRANIN.lower, bm.BRANIN.upper), X)
    assert (bm.scale_to_unit(bm.BRANIN.lower_array[None], bm.BRANIN.lower, bm.BRANIN.upper) == 0).all()
    assert (bm.scale_to_unit(bm.BRANIN.upper_array[None], bm.BRANIN.lower, bm.BRANIN.upper) == 1).all()


def test_benchmark_table_settings():
    assert list(bm.BENCHMARKS) == ["branin", "ackley4", "hartmann4"]
    assert (bm.BRANIN.init_size, bm.BRANIN.budget, bm.BRANIN.seed_offset) == (6, 50, 100_000)
    assert (bm.ACKLEY4.init_size, bm.ACKLEY4.budget, bm.ACKLEY4.seed_offset) == (12, 80, 300_000)
    assert (bm.HARTMANN4.init_size, bm.HARTMANN4.budget, bm.HARTMANN4.seed_offset) == (12, 80, 700_000)
    assert [b.rng_salt for b in ALL] == ["week2", "week3_4d_ackley", "week7", "week3_4d"]
    assert [b.threshold_seed for b in ALL] == [2026, 3027, 2026, 3026]
    with pytest.raises(Exception):
        bm.BRANIN.init_size = 7  # frozen dataclass


@pytest.mark.parametrize("benchmark", ALL, ids=lambda b: b.name)
def test_frozen_threshold_literal(benchmark):
    assert bm.compute_threshold(benchmark) == FROZEN_THRESHOLDS[benchmark.name]


def test_labels_and_dataset_shapes():
    ds = bm.make_dataset(bm.BRANIN, 0, threshold=FROZEN_THRESHOLDS["branin"])
    assert ds.pool.shape == (1_500, 2) and ds.test.shape == (4_000, 2)
    assert set(np.unique(ds.pool_labels)) == {-1.0, 1.0}
    assert (ds.pool_scaled >= 0).all() and (ds.pool_scaled <= 1).all()
    assert np.array_equal(ds.pool_labels, np.where(ds.pool_values >= ds.threshold, 1.0, -1.0))
    assert ds.seed == 0 and ds.threshold == FROZEN_THRESHOLDS["branin"]
    # default threshold path equals explicit
    ds2 = bm.make_dataset(bm.BRANIN, 0)
    assert np.array_equal(ds2.pool_labels, ds.pool_labels)
    assert np.array_equal(bm.labels_from_threshold([1.0, 2.0, 3.0], 2.0), [-1.0, 1.0, 1.0])


def test_initial_design_two_classes_and_deterministic():
    ds = bm.make_dataset(bm.HARTMANN4, 3, threshold=FROZEN_THRESHOLDS["hartmann4"])
    idx = bm.initial_design(bm.HARTMANN4, ds, 3)
    assert idx.shape == (12,) and idx.dtype.kind == "i" and len(set(idx.tolist())) == 12
    assert set(np.unique(ds.pool_labels[idx])) == {-1.0, 1.0}
    assert np.array_equal(idx, bm.initial_design(bm.HARTMANN4, ds, 3))
    with pytest.raises(RuntimeError):
        bm.initial_design(bm.HARTMANN4, ds, 4)  # seed mismatch


def test_random_two_class_initial_design_retries():
    labels = np.array([-1.0] * 50 + [1.0])
    rng = np.random.default_rng(0)
    idx, attempts = bm.random_two_class_initial_design(rng, labels, 3)
    assert attempts >= 1 and 50 in idx.tolist()
    with pytest.raises(RuntimeError):
        bm.random_two_class_initial_design(np.random.default_rng(0), np.ones(10), 2, max_attempts=3)


def test_make_plot_grid():
    xx, yy, original, scaled = bm.make_plot_grid(size=10)
    assert xx.shape == (10, 10) and original.shape == (100, 2) and scaled.shape == (100, 2)
    assert np.allclose(scaled.min(axis=0), 0) and np.allclose(scaled.max(axis=0), 1)
    with pytest.raises(RuntimeError):
        bm.make_plot_grid(bm.ACKLEY4)


# --- archive comparisons ------------------------------------------------------


@pytest.mark.archive
def test_thresholds_match_archive_functions(archive_src):
    from src import branin_week1 as w1
    from src import week3_4d_named_benchmark_comparison as w3
    from src import week4_08_boundary_weighted_sur as w48

    assert abs(bm.compute_threshold(bm.BRANIN) - w1.compute_threshold()) < 1e-12
    assert abs(bm.compute_threshold(bm.ACKLEY4) - w3.compute_threshold()) < 1e-12
    assert abs(bm.compute_threshold(bm.HARTMANN4) - w48.compute_hartmann_threshold()[0]) < 1e-12


@pytest.mark.archive
def test_oracles_match_archive(archive_src):
    from src import branin_week1 as w1
    from src import week3_4d_named_benchmark_comparison as w3
    from src import week4_08_boundary_weighted_sur as w48

    rng = np.random.default_rng(7)
    X2 = rng.uniform(-5, 15, size=(200, 2))
    X4 = rng.uniform(-5, 5, size=(200, 4))
    U4 = rng.uniform(size=(200, 4))
    assert np.array_equal(bm.branin(X2), w1.branin(X2))
    assert np.array_equal(bm.ackley4(X4), w3.ackley_4d(X4))
    assert np.array_equal(bm.hartmann4(U4), w48.hartmann4(U4))
    assert np.array_equal(bm.scale_to_unit(X2, bm.BRANIN.lower, bm.BRANIN.upper), w1.scale_to_unit_square(X2))
    assert np.array_equal(bm.scale_to_unit(X4, bm.ACKLEY4.lower, bm.ACKLEY4.upper), w3.scale_to_unit_hypercube(X4))
    assert np.array_equal(bm.unscale_from_unit(U4, bm.ACKLEY4.lower, bm.ACKLEY4.upper), w3.unscale_from_unit_hypercube(U4))


@pytest.mark.archive
@pytest.mark.parametrize("seed", [0, 1])
def test_datasets_and_designs_match_archive(archive_src, seed):
    from src import week2_acquisition_comparison as w2
    from src import week3_4d_named_benchmark_comparison as w3
    from src import week4_08_boundary_weighted_sur as w48

    checks = (
        (bm.BRANIN, lambda t: w2.create_seed_design(seed, t)),
        (bm.ACKLEY4, lambda t: w3.create_seed_design(seed, t)),
        (bm.HARTMANN4, lambda t: w48.create_hartmann_seed_design(seed, t, 12, 4_000, 10_000)),
    )
    for benchmark, make_archive in checks:
        threshold = FROZEN_THRESHOLDS[benchmark.name]
        ours = bm.make_dataset(benchmark, seed, threshold=threshold)
        design = make_archive(threshold)
        theirs = design.dataset
        assert np.array_equal(ours.pool, theirs.pool_original), benchmark.name
        assert np.array_equal(ours.pool_scaled, theirs.pool_scaled), benchmark.name
        assert np.array_equal(ours.pool_labels, theirs.pool_labels), benchmark.name
        assert np.array_equal(ours.test, theirs.test_original), benchmark.name
        assert np.array_equal(ours.test_scaled, theirs.test_scaled), benchmark.name
        assert np.array_equal(ours.test_labels, theirs.test_labels), benchmark.name
        if hasattr(theirs, "pool_values"):
            assert np.array_equal(ours.pool_values, theirs.pool_values), benchmark.name
            assert np.array_equal(ours.test_values, theirs.test_values), benchmark.name
        assert bm.initial_design(benchmark, ours, seed).tolist() == list(design.initial_indices), benchmark.name
        _, attempts = bm.random_two_class_initial_design(
            np.random.default_rng(seed + benchmark.seed_offset), ours.pool_labels, benchmark.init_size
        )
        assert attempts == design.initial_resampling_attempts, benchmark.name


@pytest.mark.archive
def test_initial_indices_match_frozen_summaries():
    cases = (
        (bm.BRANIN, ARCHIVE_OUTPUTS / "week2_acquisition_comparison" / "summary.json"),
        (bm.ACKLEY4, ARCHIVE_OUTPUTS / "week3_4d_named_benchmark_comparison" / "summary.json"),
    )
    for benchmark, path in cases:
        summary = json.loads(path.read_text(encoding="utf-8"))
        assert summary["threshold"] == FROZEN_THRESHOLDS[benchmark.name]
        for seed_text, expected in summary["initial_indices_by_seed"].items():
            seed = int(seed_text)
            dataset = bm.make_dataset(benchmark, seed, threshold=summary["threshold"])
            assert bm.initial_design(benchmark, dataset, seed).tolist() == expected, (benchmark.name, seed)
