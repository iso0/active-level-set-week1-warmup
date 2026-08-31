from __future__ import annotations

import ast
import json
import subprocess

import nbformat
import numpy as np
import pandas as pd

from src import week9_phase1_8_model_path_decomposition as p18


def test_population_outer_runs_and_exact_paths() -> None:
    population, specs = p18.load_population_specs()
    paths, audit = p18.load_query_paths()
    assert len(population) == 405
    assert int(population.has_keyhole.sum()) == 73
    assert len(specs) == 100
    assert audit["status"] == "PASS"
    assert audit["outer_run_ids_matched"] == 100
    assert audit["initial_design_exact_matches"] == 100
    assert audit["budgets_per_run"] == 65
    for spec in specs:
        train, test = set(spec.train_indices), set(spec.test_indices)
        assert paths[spec.run_id]["A0"][:16] == paths[spec.run_id]["A1"][:16]
        for path in paths[spec.run_id].values():
            assert len(path) == len(set(path)) == 80
            assert set(path).issubset(train)
            assert set(path).isdisjoint(test)


def test_baseline_gate_and_budget16_same_model_identities() -> None:
    gate = json.loads((p18.OUTPUT / "baseline_gate.json").read_text(encoding="utf-8"))
    assert gate["status"] == "PASS"
    assert abs(gate["Y00_q20_AULC"] - 0.8135202205882354) < 1e-12
    assert abs(gate["Y11_q20_AULC"] - 0.8335386029411765) < 1e-12
    assert abs(gate["Y00_budget16_q20_accuracy"] - 0.7317647059) < 1e-9
    assert abs(gate["Y11_budget16_q20_accuracy"] - 0.7847058824) < 1e-9
    assert gate["Y00_Y01_budget16_max_accuracy_error"] < 1e-12
    assert gate["Y10_Y11_budget16_max_accuracy_error"] < 1e-12
    assert gate["Y00_checkpoint_refit_max_accuracy_error"] < 1e-12


def test_decomposition_identity_and_grouped_inference() -> None:
    repeat = pd.read_csv(p18.OUTPUT / "repeat_level_decomposition.csv")
    summary = pd.read_csv(p18.OUTPUT / "primary_decomposition.csv")
    assert repeat.repeat.nunique() == 20
    assert np.allclose(repeat.MODEL + repeat.PATH, repeat.TOTAL, atol=1e-14, rtol=0)
    assert np.allclose(
        repeat.INT,
        repeat.Y11 - repeat.Y10 - repeat.Y01 + repeat.Y00,
        atol=1e-14,
        rtol=0,
    )
    assert summary.bootstrap_draws.eq(p18.BOOTSTRAP_DRAWS).all()
    contrast = summary[summary.effect.eq("MODEL_minus_PATH")].iloc[0]
    expected = "MODEL_DOMINANT" if contrast.ci_lower > 0 else (
        "PATH_DOMINANT" if contrast.ci_upper < 0 else "MIXED_OR_UNRESOLVED"
    )
    assert summary.decision.eq(expected).all()


def test_residual_kernel_excludes_logh_and_primary_model_is_frozen() -> None:
    kernel = p18.p17.PhysicsRidgeResidualKernel()
    rng = np.random.default_rng(18)
    x = rng.normal(size=(8, 5))
    shifted = x.copy()
    shifted[:, 4] += 0.7
    # Subtract the known physics covariance; the remainder must depend on x4 only.
    residual = kernel(x) - p18.p17.PHYSICS_PRIOR_VARIANCE * (1 + np.outer(x[:, 4], x[:, 4]))
    shifted_residual = kernel(shifted) - p18.p17.PHYSICS_PRIOR_VARIANCE * (1 + np.outer(shifted[:, 4], shifted[:, 4]))
    assert np.allclose(residual, shifted_residual, atol=1e-12)
    assert p18.p17.RESIDUAL_SD_BOUNDS == (0.05, 1.0)
    assert p18.p17.LENGTH_SCALE_BOUNDS == (0.25, 4.0)
    assert p18.p17.PHYSICS_PRIOR_VARIANCE == 25.0


def test_hidden_unrevealed_labels_do_not_change_current_budget_predictions() -> None:
    population, specs = p18.load_population_specs()
    paths, _ = p18.load_query_paths()
    spec = specs[0]
    revealed = paths[spec.run_id]["A0"][:16]
    test = np.asarray(spec.test_indices, dtype=int)[:12]
    x4 = population.loc[:, p18.FEATURES].to_numpy(float)
    lh = p18.p17.log_h(population)

    original_m0 = p18._fit_m0(spec, population, revealed, 16)
    original_m1 = p18._fit_m1(spec, population, revealed, 16)
    changed = population.copy()
    changed["has_keyhole"] = changed["has_keyhole"].astype(int)
    hidden = np.setdiff1d(np.arange(len(changed)), np.asarray(revealed, dtype=int))
    changed.loc[hidden, "has_keyhole"] = 1 - changed.loc[hidden, "has_keyhole"].astype(int)
    changed_m0 = p18._fit_m0(spec, changed, revealed, 16)
    changed_m1 = p18._fit_m1(spec, changed, revealed, 16)
    assert np.allclose(p18.p6.predict_gpc(original_m0, x4[test]), p18.p6.predict_gpc(changed_m0, x4[test]), atol=1e-12)
    assert np.allclose(
        p18.p17.additive_components(original_m1, x4[test], lh[test])["probability"],
        p18.p17.additive_components(changed_m1, x4[test], lh[test])["probability"],
        atol=1e-12,
    )


def test_q20_q30_are_evaluation_only_in_replay_source() -> None:
    tree = ast.parse((p18.ROOT / "src" / "week9_phase1_8_model_path_decomposition.py").read_text(encoding="utf-8"))
    functions = {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for name in ("_fit_m0", "_fit_m1", "run_cross_arm", "fit_additive_with_bound"):
        source = ast.unparse(functions[name]).lower()
        assert "b1_q20" not in source
        assert "b1_q30" not in source
        assert "boundary_flags" not in source
    assert "only current query-path prefix" in (p18.OUTPUT / "cross_execution_report.json").read_text(encoding="utf-8") or p18.CHECKPOINTS.exists()


def test_regularization_sensitivity_is_fixed_path_not_selection() -> None:
    sensitivity = pd.read_csv(p18.OUTPUT / "regularization_sensitivity.csv")
    assert set(sensitivity.path) == {"A0", "A1"}
    assert set(sensitivity.budget) == {16, 40, 80}
    assert set(sensitivity.residual_sd_upper_bound) == {0.5, 1.0, 2.0}
    report = json.loads((p18.OUTPUT / "sensitivity_execution_report.json").read_text(encoding="utf-8"))
    assert report["new_query_trajectories"] == 0
    assert report["post_hoc_selection"] is False


def test_historical_outputs_unchanged_notebook_and_figure_hashes() -> None:
    changed = subprocess.check_output(
        [
            "git",
            "diff",
            "--name-only",
            p18.STARTING_SHA,
            "--",
            "outputs/week8_5_frozen_confirmation",
            "outputs/week9_phase1_close_week8",
            "outputs/week9_phase1_5_h_physics_confirmation",
            "outputs/week9_phase1_7_physics_ridge_residual_gp",
            "notebooks/week_09/03_week9_phase1_7_physics_ridge_residual_gp.ipynb",
        ],
        cwd=p18.ROOT,
        text=True,
    ).strip()
    assert changed == ""
    figures = pd.read_csv(p18.OUTPUT / "figure_manifest.csv")
    assert len(figures) == 4
    for row in figures.itertuples(index=False):
        path = p18.FIGURES / row.figure
        assert path.is_file()
        assert p18.sha256_file(path) == row.sha256
    notebook = nbformat.read(p18.NOTEBOOK, as_version=4)
    code = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert code and all(cell.execution_count is not None for cell in code)
    assert not [output for cell in code for output in cell.get("outputs", []) if output.get("output_type") == "error"]


def test_manifest_hashes_and_red_team_pass() -> None:
    manifest = json.loads((p18.OUTPUT / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["new_query_trajectories"] == 0
    assert manifest["primary_models_frozen"] is True
    assert all("checkpoints" not in row["path"] for row in manifest["files"])
    for row in manifest["files"]:
        path = p18.ROOT / row["path"]
        assert path.is_file()
        assert p18.sha256_file(path) == row["sha256"]
    red_team = json.loads((p18.OUTPUT / "red_team_report.json").read_text(encoding="utf-8"))
    assert red_team["status"] == "PASS"
