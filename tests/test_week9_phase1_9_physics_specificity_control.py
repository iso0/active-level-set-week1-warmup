from __future__ import annotations

import inspect
import json
import subprocess
from pathlib import Path

import nbformat as nbf
import numpy as np
import pandas as pd

from src import week9_phase1_7_physics_ridge_residual_gp as p17
from src import week9_phase1_9_physics_specificity_control as p19


def test_population_labels_and_frozen_a0_paths() -> None:
    population, specs = p19.load_population_specs()
    paths, audit = p19.load_a0_paths()
    assert len(population) == 405
    assert int(population.has_keyhole.sum()) == 73
    assert len(specs) == len(paths) == 100
    assert audit["status"] == "PASS"
    assert audit["initial_design_exact_matches"] == 100
    assert audit["new_query_paths_generated"] == 0
    assert audit["duplicate_query_violations"] == 0
    assert audit["outside_training_pool_violations"] == 0
    assert audit["test_query_violations"] == 0
    assert all(len(path) == 80 and len(set(path)) == 80 for path in paths.values())


def test_generic_trend_definition_has_exact_variables_and_no_h() -> None:
    population, _ = p19.load_population_specs()
    trend = p19.generic_trend_matrix(population)
    expected = np.column_stack([
        np.log(population.P.to_numpy(float)),
        np.log(population.VX.to_numpy(float)),
        np.log(population.LS.to_numpy(float)),
        population.ST.to_numpy(float),
    ])
    assert p19.GENERIC_TREND_FEATURES == ("log_P", "log_VX", "log_LS", "ST")
    assert np.array_equal(trend, expected)
    source = "\n".join(inspect.getsource(function) for function in (p19.generic_trend_matrix, p19.fit_generic, p19.run_one_active))
    assert "log_h" not in source
    matrix_source = inspect.getsource(p19.generic_trend_matrix)
    assert "- 0.5" not in matrix_source and "- 1.5" not in matrix_source
    assert not {"B1", "q20", "q30"}.intersection(p19.GENERIC_TREND_FEATURES)


def test_generic_kernel_matches_frozen_residual_and_prior_settings() -> None:
    assert p19.PRIOR_VARIANCE == p17.PHYSICS_PRIOR_VARIANCE == 25.0
    assert p17.RESIDUAL_SD_BOUNDS == (0.05, 1.0)
    assert p17.LENGTH_SCALE_BOUNDS == (0.25, 4.0)
    rng = np.random.default_rng(19)
    x4 = rng.normal(size=(6, 4))
    generic_x = np.column_stack([x4, np.zeros((6, 4))])
    physics_x = np.column_stack([x4, np.zeros(6)])
    generic = p19.GenericTrendResidualKernel(residual_variance=.2, length_scale=1.3)
    physics = p17.PhysicsRidgeResidualKernel(residual_variance=.2, length_scale=1.3)
    assert np.allclose(generic(generic_x), physics(physics_x))
    kernel_source = inspect.getsource(p19.GenericTrendResidualKernel.__call__)
    assert "x4, trend_x = X[:, :4], X[:, 4:]" in kernel_source


def test_unrevealed_labels_cannot_change_current_budget_fit() -> None:
    population, specs = p19.load_population_specs()
    paths, _ = p19.load_a0_paths()
    spec = specs[0]
    revealed = np.asarray(paths[spec.run_id][:16], dtype=int)
    x4 = population.loc[:, p19.FEATURES].to_numpy(float)
    trend = p19.generic_trend_matrix(population)
    labels = population.has_keyhole.astype(int).to_numpy()
    perturbed = labels.copy()
    hidden = np.setdiff1d(np.arange(len(labels)), revealed)
    perturbed[hidden] = 1 - perturbed[hidden]
    fit_a = p19.fit_generic(x4, trend, labels, revealed, spec.train_indices, 91)
    fit_b = p19.fit_generic(x4, trend, perturbed, revealed, spec.train_indices, 91)
    target = np.asarray(spec.test_indices[:10], dtype=int)
    prob_a = p19.generic_components(fit_a, x4[target], trend[target])["probability"]
    prob_b = p19.generic_components(fit_b, x4[target], trend[target])["probability"]
    assert np.allclose(prob_a, prob_b, atol=1e-12, rtol=0)
    assert np.array_equal(fit_a.y_train, labels[revealed])


def test_baseline_gate_reproduces_y00_and_y10() -> None:
    gate = p19.baseline_gate()
    assert gate["status"] == "PASS"
    assert abs(gate["Y00_q20_AULC_16_80"] - 0.8135202205882354) < 1e-12
    assert abs(gate["Y10_q20_AULC_16_80"] - 0.8299724264705881) < 1e-12


def test_completed_primary_outputs_and_grouped_inference() -> None:
    primary = pd.read_csv(p19.OUTPUT / "primary_AULC_summary.csv")
    repeat = pd.read_csv(p19.OUTPUT / "repeat_level_AULC_contrasts.csv")
    assert set(primary.estimand) == {"Y00", "G10", "Y10", "physics_minus_generic", "generic_minus_4D"}
    assert repeat.repeat.nunique() == 20
    assert p19.BOOTSTRAP_DRAWS >= 5000
    assert abs(float(primary[primary.estimand.eq("Y00")]["mean"].iloc[0]) - 0.8135202205882354) < 1e-12
    assert abs(float(primary[primary.estimand.eq("Y10")]["mean"].iloc[0]) - 0.8299724264705881) < 1e-12


def test_generic_execution_is_fixed_path_and_complete() -> None:
    report = json.loads((p19.OUTPUT / "generic_execution_report.json").read_text(encoding="utf-8"))
    metrics = pd.read_csv(p19.TABLES / "generic_fixed_path_metrics.csv.gz", low_memory=False)
    assert report["status"] == "PASS"
    assert report["new_query_paths"] == 0
    assert report["outer_runs"] == 100 and report["fits"] == 6500
    assert metrics.run_id.nunique() == 100
    assert len(metrics) == 100 * 65 * 3
    assert set(metrics.path) == {"A0"}
    assert set(metrics.arm) == {"G10"}


def test_notebook_is_executed_and_figures_validate() -> None:
    notebook = nbf.read(p19.NOTEBOOK, as_version=4)
    code = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert code and all(cell.execution_count is not None for cell in code)
    assert not [output for cell in code for output in cell.get("outputs", []) if output.get("output_type") == "error"]
    figures = pd.read_csv(p19.OUTPUT / "figure_manifest.csv")
    assert len(figures) == 3
    assert all(p19.sha256_file(p19.FIGURES / row.figure) == row.sha256 for row in figures.itertuples(index=False))


def test_manifest_hashes_and_validation() -> None:
    manifest = json.loads((p19.OUTPUT / "run_manifest.json").read_text(encoding="utf-8"))
    validation = json.loads((p19.OUTPUT / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["status"] == "PASS"
    assert manifest["validation"] == validation
    assert manifest["new_query_paths"] == 0
    for row in manifest["files"]:
        path = p19.ROOT / row["path"]
        assert path.is_file()
        assert p19.sha256_file(path) == row["sha256"]


def test_historical_phase1_outputs_unchanged() -> None:
    assert p19.historical_changes() == ""
    changed = subprocess.check_output(["git", "diff", "--name-only", p19.STARTING_SHA], cwd=p19.ROOT, text=True).splitlines()
    allowed = (
        ".gitattributes",
        ".gitignore",
        "src/week9_phase1_9_physics_specificity_control.py",
        "tests/test_week9_phase1_9_physics_specificity_control.py",
        "notebooks/week_09/06_week9_phase1_9_physics_specificity_control.ipynb",
        "outputs/week9_phase1_9_physics_specificity_control/",
    )
    assert all(any(path == prefix or path.startswith(prefix) for prefix in allowed) for path in changed)
