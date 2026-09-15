"""Tests for alse.hybrid_gpc: fixed-mean residual GPCs (M2/M2W/M3) and trend+residual GPCs."""

from __future__ import annotations

import dataclasses
import json
import warnings

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.gaussian_process.kernels import ConstantKernel, Matern
from sklearn.preprocessing import StandardScaler

from alse import hybrid_gpc as hg
from alse import physics
from alse.config import ARCHIVE_OUTPUTS, POPULATION_CSV

P13_OUTPUT = ARCHIVE_OUTPUTS / "week9_phase1_13_fixed_physics_ard_discrepancy"
FEATURES = ("P", "VX", "LS", "ST")
# (run_id, budget) cases of the archived ARD parity gate; their M2W/M3 fits are frozen in
# m2w_fit_diagnostics / m3_fit_diagnostics / new_predictions.
PARITY_CASES = [("w85__r01_f01", 16), ("w85__r10_f05", 40), ("w85__r20_f05", 80)]


def frame_arrays(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x4 = frame.loc[:, list(FEATURES)].to_numpy(float)
    labels = frame.has_keyhole.astype(int).to_numpy()
    return x4, labels, physics.log_h(frame.P, frame.VX, frame.LS)


def toy_hybrid_problem():
    """45 rows of 4D blobs with a noisy log-h style coordinate; the first 20 rows are revealed."""
    rng = np.random.default_rng(113)
    x = np.r_[rng.normal(-0.8, 0.35, (10, 4)), rng.normal(0.8, 0.35, (10, 4)), rng.normal(0, 1, (25, 4))]
    logh = x[:, 0] + 0.3 * x[:, 3] + rng.normal(0, 0.3, len(x))
    labels = (logh + rng.normal(0, 1.0, len(x)) > 0).astype(int)
    labels[:10], labels[10:20] = 0, 1
    return x, logh, labels, np.arange(20), np.arange(len(x))


@pytest.fixture(scope="module")
def population() -> pd.DataFrame:
    frame = pd.read_csv(POPULATION_CSV, low_memory=False)
    assert len(frame) == 405
    return frame


@pytest.fixture(scope="module")
def subset(population):
    """60 training rows (scaler pool) and the remaining test rows, fixed permutation."""
    order = np.random.default_rng(0).permutation(len(population))
    return order[:60], order[60:]


# --- residual kernel and fixed-mean hybrids --------------------------------------


def test_residual_kernel_frozen_definitions():
    m2 = hg.residual_kernel("M2")
    old = ConstantKernel(0.09, (0.0025, 1.0)) * Matern(length_scale=1.5, length_scale_bounds=(0.25, 4.0), nu=1.5)
    assert repr(m2) == repr(old) and np.array_equal(m2.bounds, old.bounds)
    assert hg.RESIDUAL_VARIANCE_BOUNDS == (0.05**2, 1.0) and hg.INITIAL_RESIDUAL_VARIANCE == 0.09
    m2w, m3 = hg.residual_kernel("M2W"), hg.residual_kernel("M3")
    assert m2w.k2.length_scale == 1.0 and m2w.k2.length_scale_bounds == (0.01, 100.0) and m2w.n_dims == 2
    np.testing.assert_array_equal(m3.k2.length_scale, np.ones(4))
    assert m3.k2.length_scale_bounds == (0.01, 100.0) and m3.n_dims == 5 and m3.k2.nu == 1.5
    for kernel in (m2, m2w, m3):
        assert kernel.k1.constant_value == 0.09 and kernel.k1.constant_value_bounds == hg.RESIDUAL_VARIANCE_BOUNDS
    assert hg.residual_kernel("M3", upper=1000.0).k2.length_scale_bounds == (0.01, 1000.0)
    assert hg.residual_kernel("M3", fixed=True).n_dims == 0
    with pytest.raises(RuntimeError, match="unknown residual model"):
        hg.residual_kernel("M4")


def test_fit_hybrid_toy_components_and_diagnostic():
    x4, logh, labels, revealed, pool = toy_hybrid_problem()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = hg.fit_hybrid(x4, logh, labels, revealed, pool, "M3")
        same = hg.fit_hybrid(x4, logh, labels, revealed, pool, "M3", physics=fit.physics)
    assert fit.model == "M3" and fit.length_bounds == (0.01, 100.0) and fit.length_upper == 100.0
    np.testing.assert_array_equal(fit.revealed_indices, revealed)
    np.testing.assert_array_equal(same.gp.kernel_.theta, fit.gp.kernel_.theta)
    # the input scaler is fitted on the training pool, not on the revealed rows
    np.testing.assert_allclose(fit.x_scaler.mean_, x4[pool].mean(axis=0), rtol=1e-12)
    comp = hg.components(fit, x4, logh)
    assert set(comp) == {"physics_latent", "residual_latent", "final_latent", "latent_variance", "probability"}
    np.testing.assert_array_equal(comp["physics_latent"], fit.physics.latent(logh))
    np.testing.assert_allclose(comp["final_latent"], comp["physics_latent"] + comp["residual_latent"], atol=1e-12)
    assert (comp["latent_variance"] >= physics.EPS).all()
    assert (comp["probability"] > 0).all() and (comp["probability"] < 1).all()
    assert fit.residual_sd == np.sqrt(fit.gp.kernel_.k1.constant_value) and fit.length_scales.shape == (4,)
    row = hg.fit_diagnostic(fit)
    assert len(row) == 28 and {"l_P", "l_VX", "l_LS", "l_ST", "anisotropy_ratio", "objective_value"} <= set(row)
    assert row["length_upper_bound"] == 100.0 and row["fallback_status"] == "none"
    assert row["residual_sd_any_bound_hit"] == (row["residual_sd_lower_bound_hit"] or row["residual_sd_upper_bound_hit"])
    assert row["any_length_bound_hit"] == (row["any_length_lower_bound_hit"] or row["any_length_upper_bound_hit"])
    assert row["anisotropy_ratio"] == pytest.approx(fit.length_scales.max() / fit.length_scales.min())


def test_fit_hybrid_scalar_models_repeat_length_and_honour_bounds():
    x4, logh, labels, revealed, pool = toy_hybrid_problem()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m2 = hg.fit_hybrid(x4, logh, labels, revealed, pool, "M2")
        m2w = hg.fit_hybrid(x4, logh, labels, revealed, pool, "M2W", upper=50.0)
    assert m2.length_bounds == (0.25, 4.0) and m2w.length_bounds == (0.01, 50.0)
    for fit in (m2, m2w):
        assert fit.length_scales.shape == (4,) and len(set(fit.length_scales.tolist())) == 1
        assert hg.fit_diagnostic(fit)["anisotropy_ratio"] == 1.0
        assert fit.length_bounds[0] - 1e-9 <= fit.length_scales[0] <= fit.length_bounds[1] + 1e-9
    assert hg.fit_diagnostic(m2w)["length_upper_bound"] == 50.0


def test_fit_diagnostic_flags_bound_hits():
    x4, logh, labels, revealed, pool = toy_hybrid_problem()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = hg.fit_hybrid(x4, logh, labels, revealed, pool, "M3")
    fit.gp.kernel_.theta = np.log([1.0, 0.01, 0.01, 100.0, 100.0])
    row = hg.fit_diagnostic(fit)
    assert row["residual_sd"] == 1.0 and row["residual_sd_upper_bound_hit"] and not row["residual_sd_lower_bound_hit"]
    assert row["residual_sd_any_bound_hit"] and row["any_length_lower_bound_hit"] and row["any_length_upper_bound_hit"]
    assert (row["l_P_lower_bound_hit"], row["l_VX_lower_bound_hit"], row["l_LS_upper_bound_hit"], row["l_ST_upper_bound_hit"]) == (True,) * 4
    assert not row["l_P_upper_bound_hit"] and not row["l_LS_lower_bound_hit"]
    assert row["anisotropy_ratio"] == pytest.approx(1e4)


# --- trend + residual kernel ----------------------------------------------------------


def test_matern32_equals_sklearn_matern():
    rng = np.random.default_rng(1)
    xa, xb = rng.normal(size=(7, 4)), rng.normal(size=(5, 4))
    np.testing.assert_allclose(hg.matern32(xa, xb, 1.5), Matern(length_scale=1.5, nu=1.5)(xa, xb), atol=1e-12)
    np.testing.assert_allclose(hg.matern32(xa, xa, 0.7), Matern(length_scale=0.7, nu=1.5)(xa), atol=1e-12)


@pytest.mark.parametrize("n_trend", [1, 4])
def test_trend_residual_kernel_theta_gradient_and_diag(n_trend):
    rng = np.random.default_rng(2)
    X = rng.normal(size=(9, 4 + n_trend))
    kernel = hg.TrendResidualKernel(n_trend=n_trend)
    assert [h.name for h in kernel.hyperparameters] == ["length_scale", "residual_variance"]
    np.testing.assert_allclose(np.exp(kernel.theta), [1.5, 0.09], rtol=1e-12)
    np.testing.assert_allclose(np.exp(kernel.bounds), [[0.25, 4.0], [0.0025, 1.0]], rtol=1e-12)
    assert not kernel.is_stationary() and f"n_trend={n_trend}" in repr(kernel)
    K, grad = kernel(X, eval_gradient=True)
    np.testing.assert_allclose(K, K.T, atol=1e-12)
    np.testing.assert_allclose(np.diag(K), kernel.diag(X), atol=1e-12)
    assert kernel(X, X[:3]).shape == (9, 3) and grad.shape == (9, 9, 2)
    for j in range(2):
        step = np.zeros(2)
        step[j] = 1e-6
        numeric = (kernel.clone_with_theta(kernel.theta + step)(X) - kernel.clone_with_theta(kernel.theta - step)(X)) / 2e-6
        np.testing.assert_allclose(grad[:, :, j], numeric, atol=1e-6)
    with pytest.raises(ValueError, match="Gradient"):
        kernel(X, X, eval_gradient=True)
    with pytest.raises(RuntimeError, match="trend columns"):
        kernel(X[:, :4])
    moved = kernel.clone_with_theta(np.log([0.5, 0.2]))
    assert moved.length_scale == pytest.approx(0.5) and moved.residual_variance == pytest.approx(0.2)
    assert moved.n_trend == n_trend and moved.trend_prior_variance == 25.0


def test_trend_residual_kernel_one_column_equals_physics_ridge_formula():
    rng = np.random.default_rng(3)
    X, Y = rng.normal(size=(6, 5)), rng.normal(size=(4, 5))
    kernel = hg.TrendResidualKernel(residual_variance=0.2, length_scale=0.9)
    expected = 25.0 * (1.0 + X[:, 4][:, None] * Y[:, 4][None, :]) + 0.2 * hg.matern32(X[:, :4], Y[:, :4], 0.9)
    np.testing.assert_array_equal(kernel(X, Y), expected)
    np.testing.assert_array_equal(kernel.diag(X), 25.0 * (1.0 + X[:, 4] ** 2) + 0.2)


# --- additive fits -----------------------------------------------------------------------


def test_fit_additive_physics_trend_on_population_subset(population, subset):
    train, test = subset
    x4, labels, logh = frame_arrays(population)
    fit = hg.fit_additive(x4, logh, labels, train, train, 7)
    assert fit.fit_status == "optimized_additive_laplace" and fit.kernel.n_trend == 1
    assert fit.x_train_transformed.shape == (60, 5) and fit.y_train.dtype.kind == "i"
    assert 0.05 - 1e-9 <= fit.residual_sd <= 1.0 + 1e-9 and 0.25 - 1e-9 <= fit.length_scale <= 4.0 + 1e-9
    comp = hg.additive_components(fit, x4[test], logh[test])
    assert set(comp) == {"trend_latent", "residual_latent", "combined_latent", "latent_variance", "probability", "trend_probability", "beta_0", "beta"}
    np.testing.assert_allclose(comp["combined_latent"], comp["trend_latent"] + comp["residual_latent"], atol=1e-12)
    np.testing.assert_array_equal(comp["trend_probability"], expit(comp["trend_latent"]))
    np.testing.assert_allclose(comp["probability"], fit.model.predict_proba(hg.transform_additive_inputs(x4[test], logh[test], fit.x_scaler, fit.trend_scaler))[:, 1])
    assert comp["beta"].shape == (1,) and isinstance(comp["beta_0"], float) and comp["beta"][0] > 0
    row = hg.additive_diagnostic(fit)
    assert row["fit_status"] == fit.fit_status and row["kernel"].startswith("TrendResidualKernel(")
    assert row["convergence_warning"] == bool(fit.warnings) and row["warning_text"] == fit.warnings
    # 1-D and (n, 1) trend inputs are the same design
    np.testing.assert_array_equal(
        hg.transform_additive_inputs(x4[:5], logh[:5], fit.x_scaler, fit.trend_scaler),
        hg.transform_additive_inputs(x4[:5], logh[:5, None], fit.x_scaler, fit.trend_scaler),
    )
    # sklearn's random_state is inert without optimizer restarts
    np.testing.assert_array_equal(hg.fit_additive(x4, logh, labels, train, train, 99).kernel.theta, fit.kernel.theta)


def test_fit_additive_residual_sd_upper_changes_only_the_cap(population, subset):
    train, _ = subset
    x4, labels, logh = frame_arrays(population)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        capped = hg.fit_additive(x4, logh, labels, train, train, 7, residual_sd_upper=0.5)
    assert capped.kernel.residual_variance_bounds == (0.05**2, 0.25) and capped.kernel.length_scale_bounds == (0.25, 4.0)
    assert capped.residual_sd <= 0.5 + 1e-9
    row = hg.additive_diagnostic(capped)
    assert row["residual_sd_upper_bound_hit"] == bool(np.isclose(capped.residual_sd, 0.5, atol=5e-4, rtol=0))


def test_fit_additive_fallback_uses_fixed_kernel(monkeypatch, population, subset):
    train, test = subset
    x4, labels, logh = frame_arrays(population)

    class Flaky(GaussianProcessClassifier):
        def fit(self, X, y):
            if self.optimizer is not None:
                raise ValueError("boom")
            return super().fit(X, y)

    monkeypatch.setattr(hg, "GaussianProcessClassifier", Flaky)
    fit = hg.fit_additive(x4, logh, labels, train, train, 7)
    assert fit.fit_status == "fixed_additive_laplace_fallback" and fit.warnings == ""
    assert fit.residual_sd == pytest.approx(0.35) and fit.length_scale == 1.5 and fit.model.optimizer is None
    comp = hg.additive_components(fit, x4[test], logh[test])
    assert np.isfinite(comp["probability"]).all()


def test_generic_trend_matrix_and_fit_generic(population, subset):
    train, test = subset
    x4, labels, logh = frame_arrays(population)
    trend = hg.generic_trend_matrix(x4)
    np.testing.assert_array_equal(trend[:, :3], np.log(x4[:, :3]))
    np.testing.assert_array_equal(trend[:, 3], x4[:, 3])
    with pytest.raises(RuntimeError, match="positive"):
        hg.generic_trend_matrix(np.array([[1.0, -1.0, 1.0, 300.0]]))
    fit = hg.fit_generic(x4, labels, train, train, 3)
    assert fit.kernel.n_trend == 4 and fit.x_train_transformed.shape == (60, 8)
    same = hg.fit_additive(x4, trend, labels, train, train, 3)
    np.testing.assert_array_equal(same.kernel.theta, fit.kernel.theta)
    comp = hg.additive_components(fit, x4[test], trend[test])
    assert comp["beta"].shape == (4,)
    np.testing.assert_allclose(comp["combined_latent"], comp["trend_latent"] + comp["residual_latent"], atol=1e-12)
    with pytest.raises(ValueError, match="features"):  # a 1-column trend cannot feed the 4-column scaler
        hg.additive_components(fit, x4[test], logh[test])


# --- archive comparisons ------------------------------------------------------------------


@pytest.fixture(scope="module")
def a0_inputs(archive_src):
    """Population, frozen SplitSpecs and A0 query paths via the Phase 1.13 loader (~7 s)."""
    import src.week9_phase1_13_fixed_physics_ard_discrepancy as p13

    population, specs, paths = p13.load_inputs()
    return population, {spec.run_id: spec for spec in specs}, paths


@pytest.fixture(scope="module")
def frozen_p13():
    predictions = pd.read_csv(P13_OUTPUT / "new_predictions.csv.gz")
    diagnostics = {model: pd.read_csv(P13_OUTPUT / f"{model.lower()}_fit_diagnostics.csv.gz") for model in ("M2W", "M3")}
    return predictions, diagnostics


def a0_case(a0_inputs, run_id: str, budget: int):
    population, specs, paths = a0_inputs
    spec = specs[run_id]
    x4, labels, logh = frame_arrays(population)
    revealed = np.asarray(paths[run_id][:budget], dtype=int)
    return spec, x4, labels, logh, revealed, np.asarray(spec.test_indices, dtype=int)


@pytest.mark.archive
def test_fixed_ard_parity_cases_equal_frozen_report(a0_inputs):
    """Phase 1.13 ARD parity gate: fixed ARD kernel, zero mean, custom Laplace == sklearn."""
    report = json.loads((P13_OUTPUT / "ard_parity_report.json").read_text(encoding="utf-8"))
    frozen = pd.read_csv(P13_OUTPUT / "ard_zero_mean_parity_predictions.csv")
    assert report["status"] == "PASS" and report["maximum_probability_difference"] == 0.0
    rng = np.random.default_rng(113)
    toy_x = np.r_[rng.normal(-0.8, 0.35, (10, 4)), rng.normal(0.8, 0.35, (10, 4))]
    toy_y = np.r_[np.zeros(10, dtype=int), np.ones(10, dtype=int)]
    cases = {"toy_4d": (toy_x, toy_y, rng.normal(0, 1, (25, 4)))}
    for run_id, budget in PARITY_CASES:
        spec, x4, labels, _, revealed, test = a0_case(a0_inputs, run_id, budget)
        scaler = StandardScaler().fit(x4[np.asarray(spec.train_indices, dtype=int)])
        cases[f"{run_id}_B{budget}"] = (scaler.transform(x4[revealed]), labels[revealed], scaler.transform(x4[test]))
    assert [case["case"] for case in report["cases"]] == list(cases)
    for name, (x, y, x_test) in cases.items():
        kernel = hg.residual_kernel("M3", fixed=True).clone_with_theta(np.array([]))
        kernel.k1.constant_value, kernel.k2.length_scale = 0.27, np.array([0.8, 1.1, 1.4, 1.8])
        reference = GaussianProcessClassifier(kernel=kernel, optimizer=None, max_iter_predict=100, random_state=17).fit(x, y)
        custom = physics.FixedMeanLaplaceGPC(kernel, optimize=False).fit(x, y, np.zeros(len(y)))
        prob = custom.predict_proba(x_test, np.zeros(len(x_test)))[:, 1]
        np.testing.assert_allclose(prob, reference.predict_proba(x_test)[:, 1], atol=1e-12, rtol=0)
        rows = frozen[frozen.case.eq(name)].sort_values("row")
        np.testing.assert_allclose(prob, rows.custom_probability.to_numpy(), rtol=1e-12, atol=0)


@pytest.mark.archive
@pytest.mark.parametrize("run_id,budget", PARITY_CASES)
def test_fit_hybrid_reproduces_frozen_m2w_and_m3(a0_inputs, frozen_p13, run_id, budget):
    predictions, diagnostics = frozen_p13
    spec, x4, labels, logh, revealed, test = a0_case(a0_inputs, run_id, budget)
    physics_fit = physics.fit_physics_mean(logh, labels, revealed)
    for model in ("M2W", "M3"):
        fit = hg.fit_hybrid(x4, logh, labels, revealed, spec.train_indices, model, physics_fit)
        row = hg.fit_diagnostic(fit)
        table = diagnostics[model]
        frozen = table[table.run_id.eq(run_id) & table.budget.eq(budget)].iloc[0]
        for key, value in row.items():
            if isinstance(value, float):
                assert value == pytest.approx(float(frozen[key]), abs=1e-9), key
            else:
                assert value == frozen[key], key
        comp = hg.components(fit, x4[test], logh[test])
        mask = predictions.run_id.eq(run_id) & predictions.budget.eq(budget) & predictions.model.eq(model)
        frozen_rows = predictions[mask].set_index("population_row_index").loc[test]
        assert len(frozen_rows) == 81 and (frozen_rows.truth.to_numpy() == labels[test]).all()
        for column in ("probability", "physics_latent", "residual_latent", "final_latent"):
            np.testing.assert_allclose(comp[column], frozen_rows[column].to_numpy(), atol=1e-12, rtol=0)


@pytest.mark.archive
@pytest.mark.parametrize("run_id,budget", PARITY_CASES + [("w85__r13_f02", 57)])
def test_fit_hybrid_equals_archive_functions(a0_inputs, run_id, budget):
    import src.week9_phase1_11_fixed_mean_discrepancy_gp as p11
    import src.week9_phase1_13_fixed_physics_ard_discrepancy as p13

    spec, x4, labels, logh, revealed, test = a0_case(a0_inputs, run_id, budget)
    physics_fit = physics.fit_physics_mean(logh, labels, revealed)
    for model, upper in (("M2W", None), ("M3", None), ("M3", 1000.0)):
        mine = hg.fit_hybrid(x4, logh, labels, revealed, spec.train_indices, model, physics_fit, upper)
        theirs = p13.fit_hybrid(x4, logh, labels, revealed, spec.train_indices, physics_fit, model, upper or 100.0)
        np.testing.assert_allclose(mine.gp.kernel_.theta, theirs.gp.kernel_.theta, atol=1e-12, rtol=0)
        assert mine.gp.log_marginal_likelihood_value_ == pytest.approx(theirs.gp.log_marginal_likelihood_value_, abs=1e-12)
        assert dataclasses.asdict(mine.gp.diagnostics_) == dataclasses.asdict(theirs.gp.diagnostics_)
        assert hg.fit_diagnostic(mine) == p13.fit_diagnostic(theirs)
        ours, ref = hg.components(mine, x4[test], logh[test]), p13.components(theirs, x4[test], logh[test])
        assert set(ours) == set(ref)
        for key in ours:
            np.testing.assert_allclose(ours[key], ref[key], atol=1e-12, rtol=0)
    # M2: the Phase 1.11 residual (length 1.5, bounds (0.25, 4)) through the same class
    mine = hg.fit_hybrid(x4, logh, labels, revealed, spec.train_indices, "M2", physics_fit)
    theirs = p11.fit_fixed_mean(x4, logh, labels, revealed, spec.train_indices, 5)
    np.testing.assert_allclose(mine.gp.kernel_.theta, theirs.gp.kernel_.theta, atol=1e-12, rtol=0)
    assert dataclasses.asdict(mine.gp.diagnostics_) == dataclasses.asdict(theirs.gp.diagnostics_)
    row, ref_row = hg.fit_diagnostic(mine), p11.fit_diagnostic(theirs)
    assert row["residual_sd"] == ref_row["residual_sd"] and row["l_P"] == ref_row["residual_length_scale"]
    assert row["any_length_lower_bound_hit"] == ref_row["length_scale_lower_bound_hit"]
    assert row["any_length_upper_bound_hit"] == ref_row["length_scale_upper_bound_hit"]
    np.testing.assert_allclose(
        hg.components(mine, x4[test], logh[test])["probability"],
        p11.fixed_mean_components(theirs, x4[test], logh[test])["probability"],
        atol=1e-12,
        rtol=0,
    )


@pytest.mark.archive
def test_fit_additive_equals_p17_on_60_rows(archive_src, population, subset):
    import src.week9_phase1_7_physics_ridge_residual_gp as p17

    train, test = subset
    x4, labels, logh = frame_arrays(population)
    for revealed in (train, train[:40]):
        mine = hg.fit_additive(x4, logh, labels, revealed, train, 7)
        theirs = p17.fit_additive(x4, logh, labels, revealed, train, 7)
        np.testing.assert_array_equal(mine.x_train_transformed, theirs.x_train_transformed)
        np.testing.assert_array_equal(mine.kernel.theta, theirs.kernel.theta)
        np.testing.assert_array_equal(mine.kernel.bounds, theirs.kernel.bounds)
        assert mine.model.log_marginal_likelihood_value_ == theirs.model.log_marginal_likelihood_value_
        assert (mine.fit_status, mine.warnings) == (theirs.fit_status, theirs.warnings)
        X = mine.x_train_transformed
        np.testing.assert_array_equal(mine.kernel(X, eval_gradient=True)[1], theirs.kernel(X, eval_gradient=True)[1])
        ours = hg.additive_components(mine, x4[test], logh[test])
        ref = p17.additive_components(theirs, x4[test], logh[test])
        np.testing.assert_allclose(ours["probability"], ref["probability"], atol=1e-12, rtol=0)
        np.testing.assert_allclose(ours["trend_probability"], ref["physics_probability"], atol=1e-12, rtol=0)
        for key, ref_key in (("trend_latent", "physics_latent"), ("residual_latent", "residual_latent"), ("combined_latent", "combined_latent"), ("latent_variance", "latent_variance")):
            np.testing.assert_allclose(ours[key], ref[ref_key], atol=1e-12, rtol=1e-12)
        assert ours["beta_0"] == pytest.approx(ref["beta_0"][0], rel=1e-12) and ours["beta"][0] == pytest.approx(ref["beta_h"][0], rel=1e-12)
        row, ref_row = hg.additive_diagnostic(mine), p17.fit_diagnostic_row(theirs)
        assert {k: v for k, v in row.items() if k != "kernel"} == {k: v for k, v in ref_row.items() if k != "kernel"}
        assert row["kernel"].split("(", 1)[1].startswith(ref_row["kernel"].split("(", 1)[1].split(", physics")[0])


@pytest.mark.archive
def test_fit_generic_equals_p19_on_60_rows(archive_src, population, subset):
    import src.week9_phase1_9_physics_specificity_control as p19

    train, test = subset
    x4, labels, logh = frame_arrays(population)
    trend = p19.generic_trend_matrix(population)
    np.testing.assert_array_equal(hg.generic_trend_matrix(x4), trend)
    mine = hg.fit_generic(x4, labels, train, train, 3)
    theirs = p19.fit_generic(x4, trend, labels, train, train, 3)
    np.testing.assert_array_equal(mine.x_train_transformed, theirs.x_train_transformed)
    np.testing.assert_array_equal(mine.kernel.theta, theirs.kernel.theta)
    assert mine.model.log_marginal_likelihood_value_ == theirs.model.log_marginal_likelihood_value_
    assert mine.warnings == theirs.warnings
    assert (mine.fit_status, theirs.fit_status) == ("optimized_additive_laplace", "optimized_generic_additive_laplace")
    ours = hg.additive_components(mine, x4[test], trend[test])
    ref = p19.generic_components(theirs, x4[test], trend[test])
    for key in ("probability", "trend_latent", "residual_latent", "combined_latent", "latent_variance"):
        np.testing.assert_allclose(ours[key], ref[key], atol=1e-12, rtol=1e-12)
    ref_beta = [ref[f"beta_{name}"][0] for name in ("log_P", "log_VX", "log_LS", "ST")]
    np.testing.assert_allclose(ours["beta"], ref_beta, atol=1e-12, rtol=1e-12)
    assert ours["beta_0"] == pytest.approx(ref["beta_0"][0], rel=1e-12)


@pytest.mark.archive
@pytest.mark.parametrize("upper", [0.5, 2.0])
def test_fit_additive_residual_sd_upper_equals_p18(a0_inputs, upper):
    import src.week9_phase1_7_physics_ridge_residual_gp as p17
    import src.week9_phase1_8_model_path_decomposition as p18

    population, _, _ = a0_inputs
    spec, x4, labels, logh, revealed, test = a0_case(a0_inputs, "w85__r01_f01", 40)
    seed = p17.seed_u32("active", spec.run_id, 40)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        theirs = p18.fit_additive_with_bound(population, spec, revealed, 40, upper)
        mine = hg.fit_additive(x4, logh, labels, revealed, spec.train_indices, seed, residual_sd_upper=upper)
    np.testing.assert_array_equal(mine.kernel.bounds, theirs.kernel.bounds)
    np.testing.assert_array_equal(mine.kernel.theta, theirs.kernel.theta)
    assert mine.residual_sd == theirs.residual_sd and mine.warnings == theirs.warnings
    np.testing.assert_allclose(
        hg.additive_components(mine, x4[test], logh[test])["probability"],
        p17.additive_components(theirs, x4[test], logh[test])["probability"],
        atol=1e-12,
        rtol=0,
    )
