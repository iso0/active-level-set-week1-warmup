from __future__ import annotations

import json
import subprocess
from pathlib import Path

import nbformat as nbf
import numpy as np
import pandas as pd

from src import week9_phase1_16_m3_repulsion_scale_audit as p16


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "week9_phase1_16_m3_repulsion_scale_audit"


def test_parent_population_and_frozen_grid() -> None:
    gate = json.loads((OUT / "baseline_gate.json").read_text())
    spec = json.loads((OUT / "analysis_specification.json").read_text())
    assert gate["exact_branch_base"] == p16.PARENT_SHA
    assert (gate["population"], gate["keyholes"], gate["conduction"]) == (405, 73, 332)
    assert gate["outer_runs"] == 100 and gate["initial_design_matches"] == 100
    assert tuple(spec["c_grid"]) == p16.C_GRID == (.25, .5, 1., 2., 4.)


def test_historical_margin_exactly_reproduced() -> None:
    gate = json.loads((OUT / "baseline_gate.json").read_text())
    assert abs(gate["historical_M3_margin_q20_AULC"] - .844623161764706) < 1e-12
    assert gate["phase15a_reconstruction_rows"] == 900
    assert gate["phase15a_all_selection_matches"]
    assert gate["phase15a_max_probability_difference"] < 1e-10


def test_repulsion_selector_formula_and_tie_break() -> None:
    candidate = np.array([8, 3, 5])
    probability = np.array([.5, .5, .5])
    scaled = np.zeros((10, 4)); scaled[8, 0] = 1.; scaled[3, 0] = 1.; scaled[5, 0] = .5
    chosen, info = p16.choose_repulsion(candidate, probability, scaled, [0], 1.0)
    assert chosen == 3
    assert np.isclose(info["s_B"], 1.0)
    assert np.isclose(info["lambda_B"], info["s_B"])
    assert np.isclose(info["repulsion_factor"], 1 - np.exp(-.5))


def test_paths_and_information_flow() -> None:
    paths = pd.read_csv(OUT / "query_paths.csv.gz")
    assert set(paths.arm) == set(p16.ARMS)
    assert paths.groupby(["arm", "run_id"]).size().eq(80).all()
    assert paths.groupby(["arm", "run_id"]).population_row_index.nunique().eq(80).all()
    source = (ROOT / "src" / "week9_phase1_16_m3_repulsion_scale_audit.py").read_text()
    selector = source[source.index("def choose_repulsion"):source.index("def run_one_spec")]
    assert "labels" not in selector
    assert not any(token in selector for token in ("B1", "q20", "q30"))


def test_b16_predictions_identical_and_metrics_complete() -> None:
    checkpoint = pd.read_csv(OUT / "q20_checkpoint_metrics.csv")
    b16 = checkpoint[checkpoint.budget.eq(16)].pivot(index="metric", columns="arm", values="mean")
    assert np.allclose(b16.max(axis=1), b16.min(axis=1), atol=1e-12, rtol=0)
    inference = pd.read_csv(OUT / "repeat_block_inference.csv")
    assert set(inference.bootstrap_draws) == {10_000}
    assert set(inference.subset) == {"B1_q20", "B1_q30"}


def test_required_outputs_and_multiplicity() -> None:
    required = [
        "outer_run_metrics.csv.gz", "query_paths.csv.gz", "query_characteristics.csv",
        "repulsion_scale_response.csv", "q20_checkpoint_metrics.csv", "early_late_summary.csv",
        "q30_robustness.csv", "sample_efficiency_thresholds.csv", "full81_metrics.csv",
        "path_overlap_summary.csv", "diversity_diagnostics.csv", "fit_diagnostics.csv.gz",
        "fit_diagnostics_summary.csv", "repeat_block_inference.csv", "multiplicity_summary.csv",
        "claim_ledger.md", "FINAL_PHASE1_16_REPORT.md", "SUPERVISOR_PHASE1_16_ONE_PAGE.md",
        "FINAL_RED_TEAM_REPORT.md", "validation_report.json", "run_manifest.json", "figure_manifest.csv",
    ]
    assert all((OUT / name).is_file() for name in required)
    multiplicity = pd.read_csv(OUT / "multiplicity_summary.csv")
    assert len(multiplicity) == 5 and multiplicity.holm_adjusted_p.between(0, 1).all()


def test_notebook_figures_manifest_and_history() -> None:
    notebook = nbf.read(p16.NOTEBOOK, as_version=4)
    code = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert code and all(cell.execution_count is not None for cell in code)
    assert not [o for cell in code for o in cell.get("outputs", []) if o.get("output_type") == "error"]
    figures = pd.read_csv(OUT / "figure_manifest.csv")
    assert len(figures) <= 6
    assert all(p16.sha256_file(p16.FIGURES / row.figure) == row.sha256 for row in figures.itertuples(index=False))
    assert p16.historical_changes() == []


def test_validation_manifest_and_decision() -> None:
    validation = json.loads((OUT / "validation_report.json").read_text())
    manifest = json.loads((OUT / "run_manifest.json").read_text())
    spec = json.loads((OUT / "analysis_specification.json").read_text())
    assert validation["status"] == "PASS" and validation["passed"] == validation["check_count"]
    assert manifest["validation"] == validation
    assert manifest["decision"] in spec["decision_categories"]
    assert manifest["historical_changes"] == []


def test_git_diff_has_no_historical_phase_outputs() -> None:
    changed = subprocess.check_output(["git", "diff", "--name-only", p16.PARENT_SHA, "--", "outputs"], cwd=ROOT, text=True).splitlines()
    assert all(path.startswith("outputs/week9_phase1_16_m3_repulsion_scale_audit/") for path in changed)
