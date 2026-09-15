"""Tests for alse.surrogates: fast unit checks plus archive-equality gates."""

from __future__ import annotations

import importlib
import math

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm
from sklearn.gaussian_process import GaussianProcessClassifier, GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, Matern, WhiteKernel
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from alse import benchmarks as bm
from alse import surrogates as sg
from alse.config import POPULATION_CSV

FEATURES = ("P", "VX", "LS", "ST")
SUBSET_SEED = 12345  # fixed 60-row population subset used by every archive gate
SUBSET_SIZE = 60
PHASE6_FIELDS = ("fit_status", "kernel", "constant_value", "length_scale", "bound_hit", "warnings", "alpha", "y_mean", "y_scale")


def _archive(archive_src, name: str):
    """Import ``src.<name>`` from the archive (the fixture only exposes the package)."""
    return importlib.import_module(f"{archive_src.__name__}.{name}")


def _equal(a, b, tol: float = 1e-12) -> bool:
    return np.allclose(np.asarray(a, dtype=float), np.asarray(b, dtype=float), rtol=tol, atol=tol)


def _same_fields(ours: sg.FitResult, theirs, fields=PHASE6_FIELDS) -> None:
    for name in fields:
        assert getattr(ours, name) == getattr(theirs, name), name
    assert type(ours.model).__name__ == type(theirs.model).__name__


def _same_diag(ours: dict, theirs: dict) -> None:
    assert set(ours) == set(theirs)
    for key, value in theirs.items():
        mine = ours[key]
        if isinstance(value, float):
            assert (math.isnan(value) and math.isnan(mine)) or _equal(mine, value), key
        else:
            assert mine == value, key


@pytest.fixture(scope="module")
def population():
    frame = pd.read_csv(POPULATION_CSV)
    x = frame[list(FEATURES)].to_numpy(dtype=float)
    labels = frame["has_keyhole"].astype(int).to_numpy()
    depth = frame["value__max_depth"].to_numpy(dtype=float)
    idx = np.sort(np.random.default_rng(SUBSET_SEED).choice(len(frame), SUBSET_SIZE, replace=False))
    assert np.unique(labels[idx]).size == 2
    scaler = StandardScaler().fit(x)  # label-free pool scaler, as in the archive
    return x, labels, depth, idx, scaler


@pytest.fixture(scope="module")
def branin_design():
    ds = bm.make_dataset(bm.BRANIN, 0)
    labelled = np.arange(40)
    return ds, ds.pool_scaled[labelled], ds.pool_labels[labelled]


@pytest.fixture(scope="module")
def small_4d():
    ds = bm.make_dataset(bm.HARTMANN4, 1)
    idx = np.arange(50)
    return ds.pool_scaled[idx], (ds.pool_labels[idx] > 0).astype(int)


# --- fast unit tests ----------------------------------------------------------


def test_gpr_standin_settings_and_fit():
    gp = sg.make_gpr_standin(7)
    signal, white = gp.kernel.k1, gp.kernel.k2
    assert isinstance(signal.k1, ConstantKernel) and signal.k1.constant_value_bounds == (0.1, 10.0)
    assert isinstance(signal.k2, RBF) and signal.k2.length_scale == 0.20 and signal.k2.length_scale_bounds == (0.08, 1.0)
    assert isinstance(white, WhiteKernel) and white.noise_level == 1e-4 and white.noise_level_bounds == "fixed"
    assert (gp.alpha, gp.normalize_y, gp.n_restarts_optimizer, gp.random_state) == (1e-6, False, 0, 7)
    X = np.random.default_rng(0).uniform(size=(25, 2))
    y = np.sin(6 * X[:, 0]) + X[:, 1]
    fit = sg.fit_gpr_standin(X, y, 7)
    mu, sd = fit.predict(X, return_std=True)
    assert np.allclose(mu, y, atol=0.05) and (sd >= 0).all()


def test_fixed_gpc_variants(branin_design):
    _, X, y = branin_design
    gp = sg.make_fixed_gpc()
    assert gp.kernel.n_dims == 0 and gp.kernel.k2.length_scale == 0.25  # every hyperparameter fixed
    assert (gp.optimizer, gp.n_restarts_optimizer, gp.max_iter_predict) == (None, 0, 100)
    iso = sg.make_fixed_gpc("optimized_iso", seed=3, restarts=2)
    assert iso.kernel.k1.constant_value_bounds == (0.1, 10.0) and iso.kernel.k2.length_scale_bounds == (0.03, 3.0)
    assert (iso.optimizer, iso.n_restarts_optimizer, iso.random_state) == ("fmin_l_bfgs_b", 2, 3)
    ard = sg.make_synthetic_gpc_kernel("optimized_ard_gpc", dimension=4)
    assert np.array_equal(ard.k2.length_scale, np.full(4, 0.25))
    with pytest.raises(ValueError):
        sg.make_fixed_gpc("gbc")
    with pytest.raises(RuntimeError):
        sg.fit_fixed_gpc(X, np.ones_like(y))
    model = sg.fit_fixed_gpc(X, y)
    p = sg.predict_p_plus(model, X)
    assert p.shape == (40,) and (p >= 0).all() and (p <= 1).all()
    assert np.array_equal(p, model.predict_proba(X)[:, list(model.classes_).index(1.0)])
    opt = sg.fit_fixed_gpc(X, y, variant="optimized_ard", seed=1)
    assert opt.kernel_.k2.length_scale.shape == (2,) and opt.kernel_.theta.size == 3


def test_signal_kernel_and_diagnostics():
    k = sg.make_signal_kernel()
    assert isinstance(k.k2, Matern) and k.k2.nu == 1.5 and k.k2.length_scale_bounds == (1e-2, 1e2)
    assert k.k1.constant_value_bounds == (1e-3, 1e3)
    assert sg.make_signal_kernel("matern52").k2.nu == 2.5 and isinstance(sg.make_signal_kernel("rbf").k2, RBF)
    with pytest.raises(ValueError):
        sg.make_signal_kernel("periodic")
    assert sg.extract_kernel_diagnostics(k) == (1.0, 1.0, False)
    at_bound = ConstantKernel(1e3) * Matern(length_scale=0.5, nu=1.5)
    assert sg.extract_kernel_diagnostics(at_bound) == (1e3, 0.5, True)
    ard = ConstantKernel(2.0) * RBF(length_scale=[0.02, 5.0, 1.0, 1.0])
    assert sg.extract_kernel_diagnostics(ard) == (2.0, 0.02, False)
    assert sg.extract_kernel_diagnostics(RBF()) == (None, None, False)


def test_fit_gpr_fields_and_prediction(small_4d):
    X, _ = small_4d
    y = 100.0 * np.sin(3 * X[:, 0]) + 20.0 * X[:, 1] + 50.0
    fit = sg.fit_gpr(X, y, 0)
    assert isinstance(fit.model, GaussianProcessRegressor) and fit.fit_status == "optimized_primary"
    assert fit.alpha == 1e-8 and fit.y_mean == float(np.mean(y)) and fit.y_scale == float(np.std(y))
    assert fit.kernel == str(fit.model.kernel_) and fit.constant_value == fit.model.kernel_.k1.constant_value
    mu, sigma = sg.predict_gpr(fit, X)
    assert np.allclose(mu, y, atol=1e-3 * np.ptp(y)) and (sigma >= 1e-12).all()
    # explicit scaler is honoured; constant targets fall back to unit scale
    scaler = StandardScaler().fit(X[:10])
    assert sg.fit_gpr(X, y, 0, scaler=scaler).scaler is scaler
    assert sg.fit_gpr(X, np.full(len(X), 3.0), 0).y_scale == 1.0


def test_fit_gpc_fields_and_prediction(small_4d):
    X, labels = small_4d
    fit = sg.fit_gpc(X, labels, 0)
    assert isinstance(fit.model, GaussianProcessClassifier) and fit.fit_status == "optimized_primary"
    assert (fit.y_mean, fit.y_scale, fit.alpha, fit.diagnostics) == (None, None, None, None)
    assert "Matern" in fit.kernel and fit.length_scale == float(fit.model.kernel_.k2.length_scale)
    assert fit.model.max_iter_predict == 100 and fit.model.n_restarts_optimizer == 0
    p = sg.predict_gpc(fit, X)
    assert p.shape == (50,) and (p > 0).all() and (p < 1).all()
    assert ((p >= 0.5).astype(int) == labels).mean() > 0.8


def test_continuous_probability():
    mu = np.array([0.0, 1.0, -50.0, 50.0])
    sigma = np.array([1.0, 2.0, 0.0, 1.0])
    p = sg.continuous_probability(mu, sigma, 0.5)
    assert np.allclose(p[:2], norm.cdf([-0.5, 0.25]))
    assert p[2] == 1e-12 and p[3] == 1 - 1e-12  # sigma floor + clipping


def test_fallback_chains(monkeypatch, small_4d):
    X, labels = small_4d
    y = X[:, 0] * 10

    class OptimizerFails(GaussianProcessClassifier):
        def fit(self, X, y):
            if self.optimizer is not None:
                raise ValueError("optimizer failed")
            return super().fit(X, y)

    class AlwaysFails(GaussianProcessClassifier):
        def fit(self, X, y):
            raise np.linalg.LinAlgError("singular")

    monkeypatch.setattr(sg, "GaussianProcessClassifier", OptimizerFails)
    fixed = sg.fit_gpc(X, labels, 0)
    assert fixed.fit_status == "fixed_kernel_fallback" and fixed.model.optimizer is None
    assert fixed.model.max_iter_predict == 200 and fixed.warnings[0] == "ValueError: optimizer failed"
    assert (fixed.constant_value, fixed.length_scale, fixed.bound_hit) == (1.0, 1.0, False)
    family = sg.fit_gpc_kernel("G2", X, labels, 0)
    assert family.fit_status == "fixed_kernel_fallback"
    assert family.diagnostics["fallback_status"] == "fixed_kernel_after_ValueError"
    assert family.warnings[0] == "optimizer failed" and math.isnan(family.diagnostics["length_scale"])

    monkeypatch.setattr(sg, "GaussianProcessClassifier", AlwaysFails)
    logistic = sg.fit_gpc(X, labels, 0)
    assert logistic.fit_status == "logistic_numerical_fallback" and isinstance(logistic.model, LogisticRegression)
    assert (logistic.kernel, logistic.constant_value, logistic.bound_hit) == ("NA_logistic_fallback", None, False)
    assert logistic.warnings == ["LinAlgError: singular"] * 2 and logistic.model.C == 1.0
    family = sg.fit_gpc_kernel("G0", X, labels, 0)
    assert family.fit_status == "logistic_fallback" and family.kernel == "NA_logistic_fallback"
    assert family.diagnostics["fallback_status"] == "logistic_after_LinAlgError_LinAlgError"
    assert math.isnan(family.diagnostics["amplitude"]) and family.diagnostics["optimizer_warning"] is True
    assert 0 < sg.predict_gpc(family, X).mean() < 1

    class PrimaryAlphaFails(GaussianProcessRegressor):
        def fit(self, X, y):
            if self.alpha == 1e-8:
                raise ValueError("alpha too small")
            return super().fit(X, y)

    class RegressorOptimizerFails(GaussianProcessRegressor):
        def fit(self, X, y):
            if self.optimizer is not None:
                raise ValueError("optimizer failed")
            return super().fit(X, y)

    monkeypatch.setattr(sg, "GaussianProcessRegressor", PrimaryAlphaFails)
    retry = sg.fit_gpr(X, y, 0)
    assert retry.fit_status == "optimized_jitter_retry" and retry.alpha == 1e-6
    assert retry.warnings[0] == "ValueError: alpha too small"
    monkeypatch.setattr(sg, "GaussianProcessRegressor", RegressorOptimizerFails)
    fallback = sg.fit_gpr(X, y, 0)
    assert fallback.fit_status == "fixed_kernel_fallback_after:ValueError: optimizer failed"
    assert fallback.alpha == 1e-6 and fallback.model.optimizer is None and fallback.kernel == str(sg.make_signal_kernel())
    assert np.isfinite(sg.predict_gpr(fallback, X)[0]).all()


def test_gpc_kernel_family_specs():
    assert list(sg.GPC_KERNELS) == ["G0", "G1", "G2", "G3", "G4"]
    assert sg.GPC_KERNELS["G3"]["primary"] and not any(sg.GPC_KERNELS[n]["primary"] for n in ("G0", "G1", "G2", "G4"))
    g0 = sg.make_gpc_kernel("G0")
    assert str(g0) == str(sg.make_signal_kernel()) and g0.bounds.tolist() == sg.make_signal_kernel().bounds.tolist()
    assert isinstance(sg.make_gpc_kernel("G1").k2, RBF) and np.ndim(sg.make_gpc_kernel("G1").k2.length_scale) == 0
    assert sg.make_gpc_kernel("G2").k2.length_scale.shape == (4,)
    g3, g4 = sg.make_gpc_kernel("G3"), sg.make_gpc_kernel("G4")
    assert g3.k2.nu == 1.5 and g3.k2.length_scale.shape == (4,) and g4.k2.nu == 2.5
    for name in sg.GPC_KERNELS:
        kernel = sg.make_gpc_kernel(name)
        assert kernel.k1.constant_value_bounds == (0.001, 1000.0) and kernel.k2.length_scale_bounds == (0.01, 100.0)
    with pytest.raises(RuntimeError):
        sg.make_gpc_kernel("G5")


def test_fit_gpc_kernel_diagnostics(small_4d):
    X, labels = small_4d
    iso = sg.fit_gpc_kernel("G4", X, labels, 0)
    d = iso.diagnostics
    assert d["fit_status"] == "optimized_primary" and d["fallback_status"] == "none"
    assert d["length_scale"] == iso.length_scale == d["l_P"] == d["l_ST"] and d["anisotropy_ratio"] == 1.0
    assert d["amplitude"] == iso.constant_value and d["objective_value"] == -iso.model.log_marginal_likelihood_value_
    assert set(f"l_{f}_{side}_bound_hit" for f in FEATURES for side in ("lower", "upper")) <= set(d)
    ard = sg.fit_gpc_kernel("G3", X, labels, 0)
    lengths = ard.model.kernel_.k2.length_scale
    assert math.isnan(ard.diagnostics["length_scale"]) and ard.length_scale == lengths[0]
    assert [ard.diagnostics[f"l_{f}"] for f in FEATURES] == lengths.tolist()
    assert ard.diagnostics["anisotropy_ratio"] == lengths.max() / lengths.min()
    assert ard.diagnostics["any_length_bound_hit"] == any(
        np.isclose(lengths, b, rtol=1e-5, atol=0).any() for b in (0.01, 100.0)
    )


def test_g0_equals_phase6_gpc(population):
    x, labels, _, idx, scaler = population
    for seed in (0, 1):
        ours = sg.fit_gpc_kernel("G0", x[idx], labels[idx], seed, scaler=scaler)
        base = sg.fit_gpc(x[idx], labels[idx], seed, scaler=scaler)
        assert ours.fit_status == base.fit_status == "optimized_primary" and ours.kernel == base.kernel
        assert _equal(sg.predict_gpc(ours, x), sg.predict_gpc(base, x))
        assert (ours.constant_value, ours.length_scale, ours.bound_hit) == (base.constant_value, base.length_scale, base.bound_hit)


# --- archive gates -------------------------------------------------------------


@pytest.mark.archive
@pytest.mark.parametrize("seed", [0, 1])
def test_phase6_gpc_matches_archive(archive_src, population, seed):
    p6 = _archive(archive_src, "week7_phase6_real_data_boundary_active_level_set")
    x, labels, _, idx, scaler = population
    theirs = p6.fit_gpc(x[idx], labels[idx], scaler=scaler, seed=seed)
    ours = sg.fit_gpc(x[idx], labels[idx], seed, scaler=scaler)
    _same_fields(ours, theirs)
    assert _equal(sg.predict_gpc(ours, x), p6.predict_gpc(theirs, x))
    assert _equal(p6.predict_gpc(ours, x), sg.predict_gpc(theirs, x))  # FitResult is interchangeable
    assert sg.KERNEL_CONSTANT_BOUNDS == p6.KERNEL_CONSTANT_BOUNDS and sg.KERNEL_LENGTH_BOUNDS == p6.KERNEL_LENGTH_BOUNDS
    assert (sg.GPR_ALPHA_PRIMARY, sg.GPR_ALPHA_RETRY, sg.ACTIVE_OPTIMIZER_RESTARTS) == (
        p6.GPR_ALPHA_PRIMARY, p6.GPR_ALPHA_RETRY, p6.ACTIVE_OPTIMIZER_RESTARTS)


@pytest.mark.archive
@pytest.mark.parametrize("seed", [0, 1])
def test_phase6_gpr_matches_archive(archive_src, population, seed):
    p6 = _archive(archive_src, "week7_phase6_real_data_boundary_active_level_set")
    x, _, depth, idx, scaler = population
    theirs = p6.fit_gpr(x[idx], depth[idx], scaler=scaler, seed=seed)
    ours = sg.fit_gpr(x[idx], depth[idx], seed, scaler=scaler)
    _same_fields(ours, theirs)
    mu, sigma = sg.predict_gpr(ours, x)
    mu_ref, sigma_ref = p6.predict_gpr(theirs, x)
    assert _equal(mu, mu_ref) and _equal(sigma, sigma_ref)
    threshold = float(np.median(depth[idx]))
    assert _equal(sg.continuous_probability(mu, sigma, threshold), p6.continuous_probability(mu_ref, sigma_ref, threshold))
    for kind in ("matern32", "matern52", "rbf"):
        assert str(sg.make_signal_kernel(kind)) == str(p6.make_signal_kernel(kind))
    assert sg.extract_kernel_diagnostics(ours.model.kernel_) == p6.extract_kernel_diagnostics(theirs.model.kernel_)


@pytest.mark.archive
def test_gpr_standin_matches_archive(archive_src, branin_design):
    w1 = _archive(archive_src, "branin_week1")
    ds, X, y = branin_design
    theirs = w1.fit_gp(X, y, 0)
    ours = sg.fit_gpr_standin(X, y, 0)
    assert str(ours.kernel_) == str(theirs.kernel_)
    mu, sd = ours.predict(ds.pool_scaled, return_std=True)
    mu_ref, sd_ref = theirs.predict(ds.pool_scaled, return_std=True)
    assert _equal(mu, mu_ref) and _equal(sd, sd_ref)


@pytest.mark.archive
def test_fixed_gpc_matches_week4_06(archive_src, branin_design):
    w46 = _archive(archive_src, "week4_06_gp_classifier_surrogate")
    ds, X, y = branin_design
    theirs = w46.fit_classifier(X, y, 0)
    ours = sg.fit_fixed_gpc(X, y, seed=0)
    assert str(ours.kernel_) == str(theirs.kernel_)
    assert _equal(sg.predict_p_plus(ours, ds.pool_scaled), w46.predict_p_plus(theirs, ds.pool_scaled))
    assert _equal(sg.predict_p_plus(theirs, ds.test_scaled), w46.predict_p_plus(ours, ds.test_scaled))
    assert (sg.GPC_LENGTH_SCALE, sg.GPC_MAX_ITER_PREDICT) == (w46.GPC_LENGTH_SCALE, w46.GPC_MAX_ITER_PREDICT)


@pytest.mark.archive
def test_synthetic_variant_kernels_match_week4_07(archive_src):
    w47 = _archive(archive_src, "week4_07_optimized_gp_classifier_surrogate")
    for ours, theirs in sg.FIXED_GPC_VARIANTS.items():
        assert theirs in w47.SURROGATE_VARIANTS
        assert str(sg.make_synthetic_gpc_kernel(ours, dimension=4)) == str(w47.make_base_kernel(theirs, 4))
    assert sg.SYNTHETIC_CONSTANT_BOUNDS == w47.KERNEL_CONSTANT_BOUNDS
    assert sg.SYNTHETIC_LENGTH_BOUNDS == w47.KERNEL_LENGTH_SCALE_BOUNDS


@pytest.mark.archive
@pytest.mark.parametrize("seed", [0, 1])
@pytest.mark.parametrize("name", ["G0", "G1", "G2", "G3", "G4"])
def test_gpc_kernel_family_matches_archive(archive_src, population, name, seed):
    p12 = _archive(archive_src, "week9_phase1_12_gpc_kernel_adequacy")
    x, labels, _, idx, scaler = population
    assert sg.GPC_KERNELS[name] == p12.MODEL_SPECS[name]
    assert str(sg.make_gpc_kernel(name)) == str(p12.make_kernel(name))
    model, diag = p12.fit_gpc_model(name, scaler.transform(x[idx]), labels[idx], seed)
    ours = sg.fit_gpc_kernel(name, x[idx], labels[idx], seed, scaler=scaler)
    assert ours.fit_status == diag["fit_status"] and ours.kernel == str(model.kernel_)
    _same_diag(ours.diagnostics, diag)
    assert _equal(sg.predict_gpc(ours, x), p12.predict_positive(model, scaler.transform(x)))
