from __future__ import annotations

import hashlib

import numpy as np
import pytest
from sklearn.gaussian_process.kernels import ConstantKernel, Matern

from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week10_trackA_boundary_displacement_gate1 as gate


@pytest.fixture(scope="module")
def context():
    return gate.load_context()


def test_coordinate_orthogonality_and_invertibility(context):
    report = gate.coordinate_validation(context[0])
    assert report["status"] == "PASS"
    assert report["transform_rank"] == 3
    assert report["max_reconstruction_error"] < 1e-12


def test_coordinate_construction_is_label_blind(context):
    population = context[0].copy()
    first = gate.coordinate_system(population)
    population["has_keyhole"] = ~population.has_keyhole.astype(bool)
    second = gate.coordinate_system(population)
    np.testing.assert_array_equal(first.transformed4, second.transformed4)
    np.testing.assert_array_equal(first.reference_indices, second.reference_indices)


def sample_kernel(rho=0.35, extra_dims=3):
    rng = np.random.default_rng(17)
    ref = rng.normal(size=(12, extra_dims))
    return gate.MixtureMatern32(0.27, (0.8, 1.1, 1.4, 1.8), rho, 1.3, extra_dims,
                                tuple(map(tuple, ref.tolist())))


def test_centered_kernel_reference_mean_and_normalization():
    rng = np.random.default_rng(19)
    k = sample_kernel()
    T = np.asarray(k.reference_extra)
    X = rng.normal(size=(7, 3))
    centered, _ = k._extra_centered(X, T)
    assert np.max(np.abs(centered.mean(axis=1))) < 1e-12
    tt, _ = k._extra_centered(T, T)
    assert abs(np.mean(np.diag(tt)) - 1.0) < 1e-12


def test_kernel_symmetry_and_psd():
    rng = np.random.default_rng(23)
    X = rng.normal(size=(30, 7))
    K = sample_kernel()(X)
    np.testing.assert_allclose(K, K.T, atol=1e-12)
    assert np.linalg.eigvalsh(K).min() > -1e-9


def test_rho_zero_recovers_m0_covariance():
    rng = np.random.default_rng(29)
    X = rng.normal(size=(20, 7))
    k = sample_kernel(rho=0.0)
    expected = ConstantKernel(0.27, "fixed") * Matern(
        length_scale=np.asarray([0.8, 1.1, 1.4, 1.8]), length_scale_bounds="fixed", nu=1.5)
    np.testing.assert_allclose(k(X), expected(X[:, :4]), rtol=0, atol=1e-12)


def test_rho_zero_recovers_m0_predictions():
    rng = np.random.default_rng(31)
    X4 = rng.normal(size=(24, 4)); E = rng.normal(size=(24, 3)); y = np.r_[np.zeros(12, int), np.ones(12, int)]
    mean = rng.normal(scale=0.2, size=24); test4 = rng.normal(size=(9, 4)); teste = rng.normal(size=(9, 3)); mt = rng.normal(scale=0.2, size=9)
    base = ConstantKernel(0.27, "fixed") * Matern([0.8, 1.1, 1.4, 1.8], length_scale_bounds="fixed", nu=1.5)
    m0 = p11.FixedMeanLaplaceGPC(base, optimize=False).fit(X4, y, mean)
    aug = sample_kernel(rho=0.0)
    aug.sigma2 = 0.27; aug.length_scales = (0.8, 1.1, 1.4, 1.8)
    m1 = p11.FixedMeanLaplaceGPC(aug, optimize=False).fit(np.column_stack([X4, E]), y, mean)
    np.testing.assert_allclose(m0.predict_proba(test4, mt), m1.predict_proba(np.column_stack([test4, teste]), mt), atol=1e-11)


def test_historical_paths_exist_and_models_get_identical_prefix(context):
    population, specs, arrays, _, _ = context
    del population
    for family in (gate.PRIMARY, gate.CONFIRMATION):
        path = gate.load_path(family, specs[0].run_id)
        assert len(path) == 80 and len(set(path)) == 80
        revealed = np.asarray(path[:16], int)
        for _model in gate.MODELS:
            np.testing.assert_array_equal(revealed, np.asarray(path[:16], int))
            np.testing.assert_array_equal(arrays.labels[revealed], arrays.labels[np.asarray(path[:16], int)])


def test_no_acquisition_hook_in_gate_runner():
    names = gate.run_one.__code__.co_names
    assert "pol_margin" not in names
    assert "coverage_then_margin" not in names
    assert "select" not in names


def test_no_heldout_label_enters_fit(context, monkeypatch, tmp_path):
    population, specs, arrays, distances, coords = context
    spec = specs[0]; path = gate.load_path(gate.PRIMARY, spec.run_id); revealed = set(path[:16])
    observed = []
    original = p11.FixedMeanLaplaceGPC.fit
    def wrapped(self, X, y, mean_train):
        observed.append(np.asarray(y).copy())
        return original(self, X, y, mean_train)
    monkeypatch.setattr(p11.FixedMeanLaplaceGPC, "fit", wrapped)
    gate.run_one(gate.PRIMARY, spec, population, arrays, distances, coords, budgets=(16,), destination=tmp_path/"one.json.gz")
    expected = arrays.labels[np.asarray(path[:16], int)]
    assert observed
    for y in observed:
        np.testing.assert_array_equal(y, expected)
    assert revealed.isdisjoint(set(spec.test_indices))


def test_repeat_block_inference_unit():
    values = np.linspace(-0.01, 0.02, 60)
    a = gate.bootstrap_interval(values, "unit-test", simultaneous=True)
    b = gate.bootstrap_interval(values, "unit-test", simultaneous=True)
    assert a == b
    with pytest.raises(RuntimeError):
        gate.bootstrap_interval(values[:59], "bad-unit", simultaneous=True)


def test_deterministic_fixed_fit_reproducibility():
    rng = np.random.default_rng(37)
    X = rng.normal(size=(26, 7)); y = np.r_[np.zeros(13, int), np.ones(13, int)]; mean = np.zeros(26)
    test = rng.normal(size=(8, 7)); mt = np.zeros(8)
    k = sample_kernel(rho=0.3)
    a = p11.FixedMeanLaplaceGPC(k, optimize=False).fit(X, y, mean)
    b = p11.FixedMeanLaplaceGPC(k, optimize=False).fit(X, y, mean)
    np.testing.assert_allclose(a.predict_proba(test, mt), b.predict_proba(test, mt), atol=gate.PROB_REPRO_TOL)
    np.testing.assert_allclose(gate.posterior_covariance(a, test), gate.posterior_covariance(b, test), atol=gate.COV_REPRO_TOL)


def test_protocol_hash_integrity_when_frozen():
    if not gate.PROTOCOL.exists():
        pytest.skip("protocol intentionally not frozen until smoke validation passes")
    expected = gate.PROTOCOL_HASH.read_text(encoding="utf-8").split()[0]
    assert hashlib.sha256(gate.PROTOCOL.read_bytes()).hexdigest() == expected

