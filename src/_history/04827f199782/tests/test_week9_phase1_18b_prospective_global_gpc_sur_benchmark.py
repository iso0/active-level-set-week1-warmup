import json
from pathlib import Path

import nbformat as nbf
import numpy as np
import pandas as pd

from src import week9_phase1_18b_prospective_global_gpc_sur_benchmark as phase


OUT = phase.OUTPUT


def test_frozen_population_and_protocol():
    population, specs, a0 = phase.load_inputs()
    assert (len(population), int(population.has_keyhole.sum())) == (405, 73)
    assert len(specs) == len(a0) == 100
    assert len({s.repeat for s in specs}) == 20
    assert all(sum(x.repeat == repeat for x in specs) == 5 for repeat in range(1, 21))


def test_published_margin_gate_and_paths():
    gate = json.loads((OUT / "baseline_gate.json").read_text())
    assert gate["status"] == "PASS"
    assert abs(gate["published_P0_q20_AULC"] - 0.8446231617647059) < 1e-12
    assert gate["p0_complete_paths"] == gate["p0_paths_length_80"] == 100
    assert gate["initial_design_matches"] == 100


def test_all_paths_are_valid_and_share_b16():
    predictions = pd.read_csv(OUT / "sequential_predictions.csv.gz", usecols=["run_id", "model", "budget"])
    assert predictions.groupby("model").run_id.nunique().eq(100).all()
    selected = pd.read_csv(OUT / "selected_queries.csv.gz")
    assert selected[selected.arm.str.startswith("P")].test_rows_available_to_acquisition.eq(False).all()
    assert selected[selected.arm.str.startswith("P")].unrevealed_labels_available_to_acquisition.eq(False).all()
    audit = json.loads((OUT / "initial_design_audit.json").read_text())
    assert audit["all_arms_identical"] and audit["size"] == 16


def test_sur_information_flow_and_numerics():
    steps = pd.read_csv(OUT / "sur_step_diagnostics.csv.gz")
    assert set(steps.arm) == set(phase.ARMS)
    expected = (1 - steps.candidate_probability) * steps.future_uncertainty_y0 + steps.candidate_probability * steps.future_uncertainty_y1
    assert np.allclose(expected, steps.expected_future_uncertainty, atol=1e-13, rtol=1e-11)
    assert np.isfinite(steps.sur_score).all()
    p2 = pd.read_csv(OUT / "physics_refit_step_diagnostics.csv.gz")
    assert ((p2.physics_slope_y0 - p2.current_physics_slope).abs() > 1e-12).any()
    assert ((p2.physics_slope_y1 - p2.current_physics_slope).abs() > 1e-12).any()
    numerical = pd.read_csv(OUT / "sur_numerical_diagnostics.csv")
    assert numerical.hypothetical_failures.sum() == 0


def test_primary_endpoint_and_multiplicity():
    primary = pd.read_csv(OUT / "q20_primary_contrasts.csv")
    assert set(primary.contrast) == {
        "P1_EXACT_FIXED_SUR-P0_M3_MARGIN",
        "P2_PHYSICS_REFIT_SUR-P0_M3_MARGIN",
        "P2_PHYSICS_REFIT_SUR-P1_EXACT_FIXED_SUR",
    }
    assert primary.bootstrap_draws.min() >= 10_000
    holm = pd.read_csv(OUT / "multiplicity_adjustment.csv")
    assert len(holm) == 2 and holm.family_size.eq(2).all()


def test_sample_efficiency_sign_and_decision():
    contrasts = pd.read_csv(OUT / "sample_efficiency_contrasts.csv")
    assert contrasts.sign_convention.str.contains("negative means fewer labels").all()
    decision = json.loads((OUT / "sample_efficiency_decision.json").read_text())
    assert decision["decision"] in {"LABEL_SAVING_SUPPORTED", "LABEL_SAVING_NOT_SUPPORTED"}


def test_notebook_executed_and_figures_hashed():
    notebook = nbf.read(phase.ROOT / "notebooks/week_09/18_week9_phase1_18b_prospective_global_gpc_sur_benchmark.ipynb", as_version=4)
    code = [c for c in notebook.cells if c.cell_type == "code"]
    assert code and all(c.execution_count is not None for c in code)
    assert not [o for c in code for o in c.get("outputs", []) if o.get("output_type") == "error"]
    figures = pd.read_csv(OUT / "figure_manifest.csv")
    assert len(figures) <= 7
    assert all(phase.sha256_file(OUT / "figures" / row.figure) == row.sha256 for row in figures.itertuples())


def test_validation_and_manifest_are_consistent():
    validation = json.loads((OUT / "validation_report.json").read_text())
    manifest = json.loads((OUT / "run_manifest.json").read_text())
    assert validation["status"] == "PASS"
    assert manifest["validation"] == validation
    assert manifest["historical_changes"] == []
    for item in manifest["files"]:
        path = phase.ROOT / item["path"]
        assert path.is_file()
        assert phase.sha256_file(path) == item["sha256"]
