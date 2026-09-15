from __future__ import annotations

import json
import subprocess

import nbformat
import numpy as np
import pandas as pd
from sklearn.base import clone

from src import week9_phase1_7_physics_ridge_residual_gp as p17


def test_frozen_baseline_split_and_initial_design_gate() -> None:
    gate = p17.baseline_gate()
    assert gate["status"] == "PASS"
    assert gate["outer_runs"] == 100
    assert gate["split_exact_matches"] == 100
    assert gate["initial_design_exact_matches"] == 100
    assert abs(gate["margin_q20_AULC_16_80"] - 0.8135202205882354) < 1e-12
    assert abs(gate["matched_random_q20_AULC_16_80"] - 0.7762204350490195) < 1e-12


def test_canonical_identity_units_and_h() -> None:
    population, specs = p17.load_population_and_specs()
    assert len(population) == 405
    assert int(population.has_keyhole.sum()) == 73
    assert int((1 - population.has_keyhole.astype(int)).sum()) == 332
    assert len(specs) == 100
    assert population.LS.between(40e-6, 90e-6).all()
    phase15_audit = json.loads((p17.PHASE15 / "data_and_protocol_audit.json").read_text())
    assert phase15_audit["LS_definition"] == "Gaussian laser spot radius r0; stored in metres"
    assert phase15_audit["ST_definition"] == "substrate temperature"
    expected = np.log(population.P / np.sqrt(population.VX * population.LS**3))
    assert np.array_equal(p17.log_h(population), expected.to_numpy(float))


def test_custom_additive_kernel_psd_symmetry_and_gradients() -> None:
    rng = np.random.default_rng(107)
    x = rng.normal(size=(12, 5))
    kernel = p17.PhysicsRidgeResidualKernel(residual_variance=0.18, length_scale=1.2)
    covariance, gradient = kernel(x, eval_gradient=True)
    assert np.allclose(covariance, covariance.T, atol=1e-12)
    assert np.linalg.eigvalsh(covariance).min() > -1e-9
    assert gradient.shape == (12, 12, 2)
    theta = kernel.theta.copy()
    epsilon = 1e-6
    for column in range(2):
        plus, minus = clone(kernel), clone(kernel)
        theta_plus, theta_minus = theta.copy(), theta.copy()
        theta_plus[column] += epsilon
        theta_minus[column] -= epsilon
        plus.theta, minus.theta = theta_plus, theta_minus
        finite_difference = (plus(x) - minus(x)) / (2 * epsilon)
        assert np.allclose(finite_difference, gradient[:, :, column], rtol=2e-5, atol=2e-7)


def test_additive_decomposition_and_residual_excludes_logh() -> None:
    population, specs = p17.load_population_and_specs()
    spec = specs[0]
    x4 = population.loc[:, p17.FEATURES].to_numpy(float)
    logh = p17.log_h(population)
    labels = population.has_keyhole.astype(int).to_numpy()
    queried = p17.w85.initial_design(spec, population)
    fit = p17.fit_additive(x4, logh, labels, queried, spec.train_indices, 17)
    test = np.asarray(spec.test_indices, dtype=int)[:10]
    components = p17.additive_components(fit, x4[test], logh[test])
    assert np.allclose(
        components["combined_latent"],
        components["physics_latent"] + components["residual_latent"],
        atol=2e-6,
    )
    shifted = p17.additive_components(fit, x4[test], logh[test] + 0.3)
    assert np.allclose(components["residual_latent"], shifted["residual_latent"], atol=1e-10)
    assert not np.allclose(components["physics_latent"], shifted["physics_latent"])
    assert p17.RESIDUAL_SD_BOUNDS[0] - 1e-8 <= fit.residual_sd <= p17.RESIDUAL_SD_BOUNDS[1] + 1e-8

    hidden_labels_changed = labels.copy()
    hidden = np.setdiff1d(np.arange(len(labels)), np.asarray(queried, dtype=int))
    hidden_labels_changed[hidden] = 1 - hidden_labels_changed[hidden]
    invariant_fit = p17.fit_additive(x4, logh, hidden_labels_changed, queried, spec.train_indices, 17)
    invariant_components = p17.additive_components(invariant_fit, x4[test], logh[test])
    assert np.allclose(components["probability"], invariant_components["probability"], atol=1e-12)


def test_active_information_flow_and_exact_paths() -> None:
    metrics = pd.read_csv(p17.TABLES / "active_per_budget_metrics.csv.gz")
    acquisition = pd.read_csv(p17.TABLES / "active_information_flow.csv.gz")
    assert metrics.run_id.nunique() == 100
    assert len(acquisition) == 100 * 64
    assert not acquisition.test_rows_available_to_acquisition.astype(bool).any()
    assert not acquisition.hidden_pool_labels_available_to_acquisition.astype(bool).any()
    assert not acquisition.B1_q20_q30_available_to_acquisition.astype(bool).any()
    assert not acquisition.external_h_threshold_used.astype(bool).any()
    for (_, subset), group in metrics.groupby(["run_id", "subset"]):
        assert group.sort_values("budget").budget.tolist() == list(range(16, 81))


def test_primary_grouped_inference_and_predeclared_decision() -> None:
    summary = pd.read_csv(p17.TABLES / "primary_AULC_summary.csv")
    primary = summary[summary.endpoint.eq("B1_q20_AULC_16_80")].iloc[0]
    repeat_delta = pd.read_csv(p17.TABLES / "repeat_level_delta_AULC.csv")
    q20_repeat = repeat_delta[repeat_delta.endpoint.eq("B1_q20_AULC_16_80")]
    assert len(q20_repeat) == 20
    expected = "PASS" if primary.delta >= 0.010 and primary.ci_lower > 0 else ("QUALIFY" if primary.delta > 0 else "FAIL")
    assert primary.decision == expected
    assert np.isclose(q20_repeat.delta_AULC.mean(), primary.delta)


def test_historical_outputs_unchanged_and_artifact_hashes() -> None:
    changed = subprocess.check_output(
        [
            "git",
            "diff",
            "--name-only",
            p17.STARTING_SHA,
            "--",
            "outputs/week8_5_frozen_confirmation",
            "outputs/week9_phase1_close_week8",
            "outputs/week9_phase1_5_h_physics_confirmation",
            "notebooks/week_09/02_week9_phase1_5_h_physics_confirmation.ipynb",
        ],
        cwd=p17.ROOT,
        text=True,
    ).strip()
    assert changed == ""
    figures = pd.read_csv(p17.OUTPUT / "figure_manifest.csv")
    assert len(figures) == 4
    for row in figures.itertuples(index=False):
        path = p17.FIGURES / row.figure
        assert path.is_file()
        assert p17.sha256_file(path) == row.sha256
    notebook = nbformat.read(p17.NOTEBOOK, as_version=4)
    code = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert code
    assert all(cell.execution_count is not None for cell in code)
    assert not [output for cell in code for output in cell.get("outputs", []) if output.get("output_type") == "error"]
