from __future__ import annotations

import hashlib
import json
from pathlib import Path

import nbformat as nbf
import numpy as np
import pandas as pd

from src import week9_phase1_17a_physics_contour_geometry_audit as p17a


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "week9_phase1_17a_physics_contour_geometry_audit"


def test_frozen_parent_population_and_paths() -> None:
    gate = json.loads((OUT / "baseline_gate.json").read_text())
    assert gate["exact_branch_base"] == p17a.PARENT_SHA
    assert (gate["population"], gate["keyholes"], gate["conduction"]) == (405, 73, 332)
    assert gate["outer_runs"] == 100
    assert gate["paths"] == 600 and gate["path_rows"] == 48_000
    assert gate["shared_initial_designs"] == 100
    assert gate["all_paths_length_80"] and gate["all_paths_unique"]
    assert set(gate["arms"]) == set(p17a.ARMS)


def test_geometry_is_frozen_before_truth_join() -> None:
    geometry = pd.read_csv(OUT / "query_geometry_components.csv.gz")
    freeze = json.loads((OUT / "geometry_freeze.json").read_text())
    forbidden = {"true_label", "B1_distance", "is_q20_like", "is_q30_like"}
    assert len(geometry) == 38_400
    assert set(geometry.arm) == set(p17a.ARMS)
    assert set(geometry.selection_budget) == set(range(17, 81))
    assert forbidden.isdisjoint(geometry.columns)
    assert freeze["status"] == "FROZEN_BEFORE_RETROSPECTIVE_JOIN"
    assert freeze["truth_columns_absent"]
    assert freeze["sha256"] == p17a.sha256_file(OUT / "query_geometry_components.csv.gz")


def test_local_gradient_and_orthogonal_energy_decomposition() -> None:
    geometry = pd.read_csv(OUT / "query_geometry_components.csv.gz")
    assert geometry.normal_ST.abs().max() == 0
    assert geometry[["orthogonality_N_T", "orthogonality_N_ST", "orthogonality_T_ST"]].to_numpy().max() < 1e-12
    assert geometry.reconstruction_error.max() < 1e-12
    assert geometry.energy_error.max() < 1e-12
    assert geometry.fraction_sum_error.max() < 1e-12
    assert not geometry.zero_distance.astype(bool).any()
    assert np.allclose(geometry[["r_N", "r_T", "r_ST"]].sum(axis=1), 1.0, atol=1e-12, rtol=0)


def test_exact_phase16_distance_recovery() -> None:
    recovery = pd.read_csv(OUT / "scaler_recovery_audit.csv")
    assert len(recovery) == len(p17a.ARMS) * 64
    assert recovery.absolute_difference.max() < 1e-12


def test_repeat_block_inference_is_paired_and_predeclared() -> None:
    inference = pd.read_csv(OUT / "repeat_block_inference.csv")
    assert set(inference.bootstrap_draws) == {10_000}
    assert set(inference.scope) == set(p17a.REGIONS)
    assert set(inference.arm) == set(p17a.ARMS[1:])
    counts = inference[["positive_repeat_blocks", "zero_repeat_blocks", "negative_repeat_blocks"]].sum(axis=1)
    assert counts.eq(20).all()


def test_no_new_acquisition_or_ard_geometry() -> None:
    spec = json.loads((OUT / "analysis_specification.json").read_text())
    source = Path(p17a.__file__).read_text(encoding="utf-8")
    geometry_source = source[
        source.index("def decompose_displacement"):
        source.index('write_csv(OUTPUT / "query_geometry_components.csv.gz"')
    ]
    assert spec["diagnostic_only"] and not spec["new_trajectory"] and not spec["new_acquisition"]
    assert "choose_" not in geometry_source
    assert "ARD" not in geometry_source and "Lambda" not in geometry_source
    assert not any(token in geometry_source for token in ("B1", "q20", "q30", "true_label"))


def test_notebook_and_figure_hashes() -> None:
    notebook = nbf.read(p17a.NOTEBOOK, as_version=4)
    code = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert code and all(cell.execution_count is not None for cell in code)
    assert not [o for cell in code for o in cell.get("outputs", []) if o.get("output_type") == "error"]
    figures = pd.read_csv(OUT / "figure_manifest.csv")
    assert len(figures) == 5
    assert all(p17a.sha256_file(p17a.FIGURES / row.figure) == row.sha256 for row in figures.itertuples(index=False))


def test_validation_manifest_history_and_artifact_hashes() -> None:
    validation = json.loads((OUT / "validation_report.json").read_text())
    manifest = json.loads((OUT / "run_manifest.json").read_text())
    assert validation["status"] == "PASS"
    assert validation["passed"] == validation["check_count"] == 27
    assert manifest["validation"] == validation
    assert manifest["decision"] == "MIXED_GEOMETRIC_MECHANISM"
    assert manifest["historical_changes"] == []
    for item in manifest["files"]:
        payload = p17a.artifact_bytes(ROOT / item["path"])
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]


def test_historical_phase_outputs_unchanged() -> None:
    assert p17a.historical_changes() == []
