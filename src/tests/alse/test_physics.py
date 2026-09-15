"""Tests for alse.physics: h coordinate, physics logistic mean, fixed-mean Laplace GPC."""

from __future__ import annotations

import dataclasses
import warnings

import numpy as np
import pandas as pd
import pytest
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.gaussian_process.kernels import ConstantKernel, Matern
from sklearn.preprocessing import StandardScaler

from alse import physics
from alse.config import ARCHIVE_OUTPUTS, POPULATION_CSV

P11_OUTPUT = ARCHIVE_OUTPUTS / "week9_phase1_11_fixed_mean_discrepancy_gp"
P15_OUTPUT = ARCHIVE_OUTPUTS / "week9_phase1_5_h_physics_confirmation"
FEATURES = ("P", "VX", "LS", "ST")


def m2_kernel(variance: float = 0.09, length: float = 1.5):
    """Old M2 residual kernel: C(0.09,(0.0025,1))*Matern32(1.5,(0.25,4))."""
    return ConstantKernel(variance, (0.0025, 1.0)) * Matern(length_scale=length, length_scale_bounds=(0.25, 4.0), nu=1.5)


def toy_problem():
    """Archive parity toy: two Gaussian blobs, 25 test points (rng 41)."""
    rng = np.random.default_rng(41)
    x = np.r_[rng.normal([-1, -1], 0.35, (8, 2)), rng.normal([1, 1], 0.35, (8, 2))]
    y = np.r_[np.zeros(8, dtype=int), np.ones(8, dtype=int)]
    return x, y, rng.normal(0, 1.2, (25, 2))


@pytest.fixture(scope="module")
def population() -> pd.DataFrame:
    frame = pd.read_csv(POPULATION_CSV, low_memory=False)
    assert len(frame) == 405
    return frame


@pytest.fixture
def small_frame() -> pd.DataFrame:
    rng = np.random.default_rng(3)
    return pd.DataFrame(
        {
            "P": rng.uniform(50, 400, 12),
            "VX": rng.uniform(0.2, 2.0, 12),
            "LS": rng.uniform(2e-5, 1e-4, 12),
            "ST": rng.uniform(300, 900, 12),
        }
    )


# --- h coordinate ------------------------------------------------------------


def test_log_h_formula_and_positivity(small_frame):
    expected = np.log(small_frame.P / np.sqrt(small_frame.VX * small_frame.LS**3))
    np.testing.assert_array_equal(physics.log_h(small_frame.P, small_frame.VX, small_frame.LS), expected)
    with pytest.raises(RuntimeError, match="positive"):
        physics.log_h([1.0, -1.0], [1.0, 1.0], [1.0, 1.0])


def test_h_coordinates_columns_and_values(small_frame):
    frame = physics.h_coordinates(small_frame)
    assert list(frame.columns) == [
        "population_row_index",
        "h_SI",
        "log_h_SI_reference",
        "delta_T_liquidus_minus_ST_K",
        "h_over_deltaT",
        "log_h_over_deltaT",
    ]
    np.testing.assert_array_equal(frame.log_h_SI_reference, physics.log_h(small_frame.P, small_frame.VX, small_frame.LS))
    np.testing.assert_allclose(frame.h_over_deltaT, frame.h_SI / (physics.TI64_LIQUIDUS_K - small_frame.ST), rtol=1e-15)
    assert physics.TI64_LIQUIDUS_K == 1933.0
    hot = small_frame.copy()
    hot.loc[0, "ST"] = 1933.0
    with pytest.raises(RuntimeError, match="liquidus"):
        physics.h_coordinates(hot)


def test_h_coordinates_carries_identity_columns(small_frame):
    named = small_frame.assign(experiment_name=[f"e{i}" for i in range(12)], has_keyhole=[True, False] * 6)
    frame = physics.h_coordinates(named)
    assert frame.columns[1:3].tolist() == ["experiment_name", "manual_has_keyhole"]
    assert frame.manual_has_keyhole.tolist() == [1, 0] * 6


def test_physical_scores_six_fixed_forms(small_frame):
    scores = physics.physical_scores(small_frame)
    assert len(physics.PHYSICAL_SCORES) == 6 and scores.shape == (12, 12)
    np.testing.assert_array_equal(
        scores.keyhole_process_score_h__log, physics.log_h(small_frame.P, small_frame.VX, small_frame.LS)
    )
    np.testing.assert_allclose(scores.linear_energy_P_over_VX__raw, small_frame.P / small_frame.VX, rtol=1e-15)
    np.testing.assert_allclose(np.exp(scores.irradiance_P_over_LS2__log), scores.irradiance_P_over_LS2__raw, rtol=1e-12)
    bad = small_frame.copy()
    bad.loc[1, "P"] = 0.0
    with pytest.raises(RuntimeError, match="Invalid physical score"):
        physics.physical_scores(bad)


# --- physics mean --------------------------------------------------------------


def test_fit_physics_mean_uses_revealed_rows_only():
    rng = np.random.default_rng(5)
    logh = rng.normal(20, 1, 60)
    labels = (logh + rng.normal(0, 0.3, 60) > 20).astype(int)
    revealed = np.arange(0, 60, 2)
    fit = physics.fit_physics_mean(logh, labels, revealed)
    np.testing.assert_array_equal(fit.revealed_indices, revealed)
    assert fit.scaler.mean_[0] == pytest.approx(logh[revealed].mean())
    assert fit.model.C == 1e6 and fit.model.coef_[0, 0] > 0
    z = fit.scaler.transform(logh[:, None])
    np.testing.assert_array_equal(fit.latent(logh), fit.model.decision_function(z))
    # a mean of the latent logistic is invariant to the (inert) seed
    other = physics.fit_physics_mean(logh, labels, revealed, seed=123)
    np.testing.assert_array_equal(other.latent(logh), fit.latent(logh))


# --- fixed-mean Laplace GPC ------------------------------------------------------


def test_zero_mean_fixed_kernel_matches_sklearn_exactly():
    x, y, x_test = toy_problem()
    kernel = m2_kernel(0.27, 1.1)
    reference = GaussianProcessClassifier(kernel=kernel, optimizer=None, max_iter_predict=100, random_state=11).fit(x, y)
    custom = physics.FixedMeanLaplaceGPC(kernel, optimize=False).fit(x, y, np.zeros(len(y)))
    np.testing.assert_allclose(
        custom.predict_proba(x_test, np.zeros(len(x_test)))[:, 1], reference.predict_proba(x_test)[:, 1], atol=1e-12, rtol=0
    )
    assert custom.log_marginal_likelihood_value_ == pytest.approx(reference.log_marginal_likelihood_value_, abs=1e-10)
    d = custom.diagnostics_
    # archive semantics: no optimizer ran, so optimizer_converged = not optimize (True)
    assert (d.optimized, d.optimizer_converged, d.optimizer_message, d.fallback_status) == (False, True, "optimizer_disabled", "none")
    assert d.optimizer_iterations == 0 and d.posterior_iterations >= 1 and d.objective_value == -custom.log_marginal_likelihood_value_


def test_zero_mean_optimized_matches_sklearn_lbfgs():
    x, y, x_test = toy_problem()
    kernel = m2_kernel()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        reference = GaussianProcessClassifier(
            kernel=kernel, optimizer="fmin_l_bfgs_b", n_restarts_optimizer=0, max_iter_predict=100, random_state=13
        ).fit(x, y)
    custom = physics.FixedMeanLaplaceGPC(kernel, optimize=True).fit(x, y, np.zeros(len(y)))
    np.testing.assert_allclose(custom.kernel_.theta, reference.kernel_.theta, atol=1e-4)
    np.testing.assert_allclose(
        custom.predict_proba(x_test, np.zeros(len(x_test)))[:, 1], reference.predict_proba(x_test)[:, 1], atol=1e-5
    )
    assert custom.diagnostics_.optimizer_converged and custom.diagnostics_.optimizer_iterations > 0


def test_fixed_mean_shifts_latent_and_probabilities():
    x, y, x_test = toy_problem()
    gp = physics.FixedMeanLaplaceGPC(m2_kernel(0.27, 1.1), optimize=False)
    zero = gp.fit(x, y, np.zeros(len(y))).predict_proba(x_test, np.zeros(len(x_test)))
    np.testing.assert_allclose(zero.sum(axis=1), 1.0, atol=1e-12)
    shifted = physics.FixedMeanLaplaceGPC(m2_kernel(0.27, 1.1), optimize=False).fit(x, y, np.full(len(y), 8.0))
    mean, var = shifted.latent_mean_and_variance(x_test, np.full(len(x_test), 8.0))
    assert (var >= physics.EPS).all()
    high = shifted.predict_proba(x_test, np.full(len(x_test), 8.0))[:, 1]
    assert (high > zero[:, 1]).all() and high.max() <= 1.0 - physics.EPS
    # fixed mean is a pure offset of the latent when the residual mode is unchanged
    mode_shift = mean - gp.latent_mean_and_variance(x_test, np.zeros(len(x_test)))[0]
    assert np.isfinite(mode_shift).all()


def test_fit_validation_and_optimizer_fallback(monkeypatch):
    x, y, _ = toy_problem()
    with pytest.raises(RuntimeError, match="binary classes"):
        physics.FixedMeanLaplaceGPC(m2_kernel(), optimize=False).fit(x, y + 1, np.zeros(len(y)))
    with pytest.raises(RuntimeError, match="length mismatch"):
        physics.FixedMeanLaplaceGPC(m2_kernel(), optimize=False).fit(x, y, np.zeros(3))

    def explode(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(physics.scipy.optimize, "minimize", explode)
    gp = physics.FixedMeanLaplaceGPC(m2_kernel(), optimize=True).fit(x, y, np.zeros(len(y)))
    assert gp.diagnostics_.fallback_status == "initial_kernel_after_ValueError"
    assert gp.diagnostics_.optimizer_message == "initial_kernel_after_ValueError"
    assert not gp.diagnostics_.optimizer_converged and gp.diagnostics_.optimizer_iterations == 0
    np.testing.assert_array_equal(gp.kernel_.theta, m2_kernel().theta)


# --- archive comparisons -----------------------------------------------------------


@pytest.mark.archive
def test_log_h_and_h_coordinates_equal_archive(archive_src, population):
    import src.week9_phase1_5_h_physics_confirmation as p15
    import src.week9_phase1_7_physics_ridge_residual_gp as p17

    np.testing.assert_array_equal(physics.log_h(population.P, population.VX, population.LS), p17.log_h(population))
    ours = physics.h_coordinates(population)
    theirs = p15.h_coordinates(population)
    assert list(ours.columns) == list(theirs.columns)
    pd.testing.assert_frame_equal(ours, theirs, check_dtype=False)
    frozen = pd.read_csv(P15_OUTPUT / "h_coordinates.csv")
    for column in ("h_SI", "log_h_SI_reference", "h_over_deltaT", "log_h_over_deltaT"):
        np.testing.assert_allclose(ours[column], frozen[column], rtol=1e-14, atol=0)


@pytest.mark.archive
def test_physical_scores_equal_archive(archive_src, population):
    import src.week9_phase1_discriminative_update as du

    values, definitions = du.physical_scores(population)
    ours = physics.physical_scores(population)
    assert list(ours.columns) == list(values)
    assert [row[0] for row in physics.PHYSICAL_SCORES] == definitions.score.tolist()
    assert [row[1] for row in physics.PHYSICAL_SCORES] == definitions.formula.tolist()
    for column, expected in values.items():
        np.testing.assert_array_equal(ours[column].to_numpy(), expected)


@pytest.mark.archive
def test_zero_mean_parity_toy_predictions_equal_frozen_csv():
    frozen = pd.read_csv(P11_OUTPUT / "zero_mean_parity_predictions.csv")
    toy = frozen[frozen.case.eq("toy")].sort_values("row")
    x, y, x_test = toy_problem()
    custom = physics.FixedMeanLaplaceGPC(m2_kernel(0.27, 1.1), optimize=False).fit(x, y, np.zeros(len(y)))
    prob = custom.predict_proba(x_test, np.zeros(len(x_test)))[:, 1]
    np.testing.assert_allclose(prob, toy.custom_probability.to_numpy(), rtol=1e-12, atol=0)
    np.testing.assert_allclose(prob, toy.sklearn_probability.to_numpy(), rtol=1e-12, atol=0)


@pytest.fixture(scope="module")
def a0_inputs(archive_src):
    """Population, frozen SplitSpecs and A0 query paths via the archive loader (~10 s)."""
    import src.week9_phase1_11_fixed_mean_discrepancy_gp as p11

    population, specs, paths, _ = p11.load_inputs()
    return population, {spec.run_id: spec for spec in specs}, paths


def parity_case(a0_inputs, run_id: str, budget: int):
    population, specs, paths = a0_inputs
    spec = specs[run_id]
    x4 = population.loc[:, FEATURES].to_numpy(float)
    labels = population.has_keyhole.astype(int).to_numpy()
    revealed = np.asarray(paths[run_id][:budget], dtype=int)
    scaler = StandardScaler().fit(x4[np.asarray(spec.train_indices, dtype=int)])
    return scaler.transform(x4[revealed]), labels[revealed], scaler.transform(x4[np.asarray(spec.test_indices, dtype=int)])


@pytest.mark.archive
def test_run_parity_gate_real_data_cases(a0_inputs):
    """run_parity_gate re-expressed: fixed-kernel parity exact, optimized parity per the frozen report."""
    import json

    report = json.loads((P11_OUTPUT / "implementation_parity_report.json").read_text(encoding="utf-8"))
    predictions = pd.read_csv(P11_OUTPUT / "zero_mean_parity_predictions.csv")
    assert report["status"] == "PASS"
    for case in report["optimization_parity"]:
        run_id, budget = case["case"].rsplit("_B", 1)
        x, y, x_test = parity_case(a0_inputs, run_id, int(budget))
        kernel = m2_kernel(0.27, 1.1)
        reference = GaussianProcessClassifier(kernel=kernel, optimizer=None, max_iter_predict=100, random_state=11).fit(x, y)
        custom = physics.FixedMeanLaplaceGPC(kernel, optimize=False).fit(x, y, np.zeros(len(y)))
        prob = custom.predict_proba(x_test, np.zeros(len(x_test)))[:, 1]
        np.testing.assert_allclose(prob, reference.predict_proba(x_test)[:, 1], atol=1e-12, rtol=0)
        frozen = predictions[predictions.case.eq(case["case"])].sort_values("row").custom_probability.to_numpy()
        np.testing.assert_allclose(prob, frozen, rtol=1e-12, atol=0)

        optimized = physics.FixedMeanLaplaceGPC(m2_kernel(), optimize=True).fit(x, y, np.zeros(len(y)))
        assert optimized.diagnostics_.optimizer_iterations == case["custom_iterations"]
        assert optimized.diagnostics_.optimizer_converged == case["custom_converged"]
        assert np.sqrt(optimized.kernel_.k1.constant_value) == pytest.approx(case["custom_residual_sd"], abs=1e-9)
        assert optimized.kernel_.k2.length_scale == pytest.approx(case["custom_length_scale"], abs=1e-9)
        assert optimized.log_marginal_likelihood_value_ == pytest.approx(case["custom_log_marginal_likelihood"], abs=1e-9)


@pytest.mark.archive
@pytest.mark.parametrize("run_id,budget", [("w85__r01_f01", 16), ("w85__r07_f03", 40), ("w85__r20_f05", 80), ("w85__r13_f02", 57)])
def test_physics_mean_and_m2_fit_equal_frozen_diagnostics(a0_inputs, run_id, budget):
    population, specs, paths = a0_inputs
    spec = specs[run_id]
    x4 = population.loc[:, FEATURES].to_numpy(float)
    labels = population.has_keyhole.astype(int).to_numpy()
    logh = physics.log_h(population.P, population.VX, population.LS)
    revealed = np.asarray(paths[run_id][:budget], dtype=int)

    physics_fit = physics.fit_physics_mean(logh, labels, revealed)
    mean_rows = pd.read_csv(P11_OUTPUT / "physics_mean_fit_diagnostics.csv.gz")
    row = mean_rows[mean_rows.run_id.eq(run_id) & mean_rows.budget.eq(budget)].iloc[0]
    assert physics_fit.scaler.mean_[0] == pytest.approx(row.h_scaler_mean, abs=1e-12)
    assert physics_fit.scaler.scale_[0] == pytest.approx(row.h_scaler_scale, abs=1e-12)
    assert physics_fit.model.intercept_[0] == pytest.approx(row.physics_intercept, abs=1e-9)
    assert physics_fit.model.coef_[0, 0] == pytest.approx(row.physics_log_h_coefficient, abs=1e-9)

    x_scaler = StandardScaler().fit(x4[np.asarray(spec.train_indices, dtype=int)])
    gp = physics.FixedMeanLaplaceGPC(m2_kernel(), optimize=True).fit(
        x_scaler.transform(x4[revealed]), labels[revealed], physics_fit.latent(logh[revealed])
    )
    residual_rows = pd.read_csv(P11_OUTPUT / "residual_fit_diagnostics.csv.gz")
    row = residual_rows[residual_rows.run_id.eq(run_id) & residual_rows.budget.eq(budget) & residual_rows.subset.eq("full81")].iloc[0]
    d = gp.diagnostics_
    assert np.sqrt(gp.kernel_.k1.constant_value) == pytest.approx(row.residual_sd, abs=1e-9)
    assert gp.kernel_.k2.length_scale == pytest.approx(row.residual_length_scale, abs=1e-9)
    assert d.objective_value == pytest.approx(row.objective_value, abs=1e-9)
    assert (d.optimizer_iterations, d.optimizer_evaluations, d.posterior_iterations) == (
        row.optimizer_iterations,
        row.optimizer_evaluations,
        row.posterior_iterations,
    )
    assert d.optimizer_message == row.optimizer_message and d.fallback_status == row.fallback_status
    test_idx = np.asarray(spec.test_indices, dtype=int)
    final_latent, _ = gp.latent_mean_and_variance(x_scaler.transform(x4[test_idx]), physics_fit.latent(logh[test_idx]))
    assert float(np.std(final_latent)) == pytest.approx(row.final_latent_sd, rel=1e-6)


@pytest.mark.archive
def test_physics_mean_and_fixed_mean_gpc_equal_archive_class(archive_src, population):
    """Same 60 population rows: log_h, fit_physics_mean and FixedMeanLaplaceGPC equal the archive's own."""
    import src.week9_phase1_7_physics_ridge_residual_gp as p17
    import src.week9_phase1_11_fixed_mean_discrepancy_gp as p11

    x4 = population.loc[:, list(FEATURES)].to_numpy(float)
    labels = population.has_keyhole.astype(int).to_numpy()
    logh = physics.log_h(population.P, population.VX, population.LS)
    np.testing.assert_array_equal(logh, p17.log_h(population))
    order = np.random.default_rng(0).permutation(len(population))
    train, test = order[:60], order[60:]
    assert set(labels[train]) == {0, 1}

    ours = physics.fit_physics_mean(logh, labels, train)
    theirs = p11.fit_physics_mean(logh, labels, train, p11.seed_u32("physics", 7))
    np.testing.assert_array_equal(ours.scaler.mean_, theirs.scaler.mean_)
    np.testing.assert_array_equal(ours.scaler.scale_, theirs.scaler.scale_)
    np.testing.assert_array_equal(ours.model.coef_, theirs.model.coef_)
    np.testing.assert_array_equal(ours.model.intercept_, theirs.model.intercept_)
    np.testing.assert_array_equal(ours.latent(logh), theirs.latent(logh))

    assert repr(m2_kernel()) == repr(p11.residual_kernel())
    np.testing.assert_array_equal(m2_kernel().bounds, p11.residual_kernel().bounds)
    scaler = StandardScaler().fit(x4[train])
    x_train, x_test = scaler.transform(x4[train]), scaler.transform(x4[test])
    mean_train, mean_test = ours.latent(logh[train]), ours.latent(logh[test])
    for optimize in (False, True):
        mine = physics.FixedMeanLaplaceGPC(m2_kernel(), optimize=optimize).fit(x_train, labels[train], mean_train)
        ref = p11.FixedMeanLaplaceGPC(p11.residual_kernel(), optimize=optimize).fit(x_train, labels[train], mean_train)
        np.testing.assert_allclose(mine.kernel_.theta, ref.kernel_.theta, atol=1e-12, rtol=0)
        assert mine.log_marginal_likelihood_value_ == pytest.approx(ref.log_marginal_likelihood_value_, abs=1e-12)
        assert dataclasses.asdict(mine.diagnostics_) == dataclasses.asdict(ref.diagnostics_)
        assert mine.diagnostics_.optimized is optimize and mine.diagnostics_.fallback_status == "none"
        np.testing.assert_allclose(
            mine.predict_proba(x_test, mean_test), ref.predict_proba(x_test, mean_test), atol=1e-12, rtol=0
        )
        for got, want in zip(mine.latent_mean_and_variance(x_test, mean_test), ref.latent_mean_and_variance(x_test, mean_test)):
            np.testing.assert_allclose(got, want, atol=1e-12, rtol=0)
    assert not mine.diagnostics_.optimizer_message == "optimizer_disabled" and mine.diagnostics_.optimizer_iterations > 0
