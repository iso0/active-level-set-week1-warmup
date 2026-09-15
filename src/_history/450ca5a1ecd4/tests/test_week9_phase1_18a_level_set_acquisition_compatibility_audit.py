import hashlib
import json
from pathlib import Path

import nbformat
import numpy as np
import pandas as pd

from src import week9_phase1_18a_level_set_acquisition_compatibility_audit as phase


OUT = phase.OUTPUT


def test_frozen_population_and_paths():
    population, specs, paths = phase.load_inputs()
    assert (len(population), int(population.has_keyhole.sum())) == (405, 73)
    assert len(specs) == len(paths) == 100
    assert all(len(paths[s.run_id]) == len(set(paths[s.run_id])) == 80 for s in specs)


def test_pre_reveal_table_has_no_outcome_or_boundary_columns():
    frame = pd.read_csv(OUT / "candidate_scores_pre_reveal.csv.gz")
    forbidden = {"truth", "has_keyhole", "B1", "q20", "q30", "is_q20", "is_q30"}
    assert forbidden.isdisjoint(frame.columns)
    assert len(frame) == 169_200
    assert len(frame[["run_id", "budget"]].drop_duplicates()) == 600


def test_score_table_hash_is_frozen_and_valid():
    record = json.loads((OUT / "candidate_scores_sha256.json").read_text())
    assert record["frozen_before_retrospective_join"] is True
    assert record["sha256"] == phase.sha256_file(OUT / "candidate_scores_pre_reveal.csv.gz")


def test_margin_and_emi_formulas():
    frame = pd.read_csv(OUT / "candidate_scores_pre_reveal.csv.gz", nrows=500)
    assert np.allclose(frame.margin_score, 1 - 2 * np.abs(frame.m3_probability - 0.5))
    expected = phase.emi_score(frame.final_latent_mean.to_numpy(), frame.latent_sd.to_numpy())
    assert np.allclose(frame.emi_score, expected)


def test_m3_final_variance_is_frozen_mean_residual_variance():
    frame = pd.read_csv(OUT / "candidate_scores_pre_reveal.csv.gz", nrows=1000)
    assert np.allclose(frame.final_latent_variance, frame.residual_latent_variance)


def test_all_required_scores_and_pa_terms_are_finite():
    frame = pd.read_csv(OUT / "candidate_scores_pre_reveal.csv.gz")
    columns = list(phase.SCORE_COLUMNS.values()) + ["pa_S", "pa_geometry_gate", "curvature_WA", "curvature_WB", "curvature_WC"]
    assert np.isfinite(frame[columns].to_numpy()).all()


def test_emi_monte_carlo_validation():
    frame = pd.read_csv(OUT / "emi_monte_carlo_validation.csv")
    assert frame.absolute_error.max() < 0.006


def test_smocu_sur_are_explicitly_approximate():
    decisions = pd.read_csv(OUT / "method_decisions.csv").set_index("method")
    assert decisions.loc["M3_SMOCU_APPROX", "decision"] == "REQUIRES_APPROXIMATION"
    assert decisions.loc["M3_SUR_APPROX", "decision"] == "REQUIRES_APPROXIMATION"
    assert len(pd.read_csv(OUT / "exact_approx_small_validation.csv")) == 3


def test_pa_tvr_all_three_curvature_definitions_recorded():
    frame = pd.read_csv(OUT / "pa_tvr_laplace_curvature_audit.csv")
    assert len(frame) == 3
    assert frame.primary_for_PA_TVR.sum() == 1


def test_pa_bound_sensitivity_complete():
    frame = pd.read_csv(OUT / "pa_tvr_bound_sensitivity.csv")
    assert len(frame) == 600
    assert set(frame.budget) == set(phase.BUDGETS)


def test_pa_decision_is_falsification_result():
    record = json.loads((OUT / "pa_tvr_decision.json").read_text())
    assert record["decision"] == "PA_TVR_REJECTED"
    assert record["truly_tangent"] is False
    assert record["global_or_nonmyopic"] is False


def test_no_new_query_trajectory_artifact():
    names = {p.name.lower() for p in OUT.rglob("*") if p.is_file()}
    assert not any("new_path" in name or "new_trajectory" in name for name in names)


def test_notebook_is_executed():
    notebook = nbformat.read(phase.NOTEBOOK, as_version=4)
    assert all(cell.cell_type != "code" or cell.execution_count is not None for cell in notebook.cells)
    assert all(cell.cell_type != "code" or cell.outputs for cell in notebook.cells)


def test_figure_hashes():
    manifest = pd.read_csv(OUT / "figure_manifest.csv")
    assert len(manifest) == 6
    assert all(phase.sha256_file(phase.FIGURES / row.figure) == row.sha256 for row in manifest.itertuples())


def test_validation_and_manifest_snapshots_match():
    validation = json.loads((OUT / "validation_report.json").read_text())
    manifest = json.loads((OUT / "run_manifest.json").read_text())
    assert validation == manifest["validation"]
    assert validation["status"] == "PASS"


def test_historical_outputs_unchanged():
    assert phase.historical_changes() == []
