from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import nbformat
import pandas as pd

from src import week9_phase1_12_gpc_kernel_adequacy as p12


ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs"/"week9_phase1_12_gpc_kernel_adequacy"


def test_start_population_and_frozen_gate() -> None:
    gate=json.loads((OUT/"baseline_gate.json").read_text())
    assert subprocess.check_output(["git","rev-parse",p12.START_SHA],cwd=ROOT,text=True).strip()==p12.START_SHA
    assert (gate["population"],gate["keyholes"],gate["conduction"])==(405,73,332)
    assert gate["outer_runs"]==100 and gate["repeat_blocks"]==20 and gate["folds_per_repeat"]==5
    assert abs(gate["H_q20_AULC"]-0.8308134191176471)<1e-12
    assert abs(gate["G0_q20_AULC"]-0.8135202205882353)<1e-12


def test_paths_initial_design_and_budget_grid() -> None:
    _,specs,paths=p12.load_inputs()
    assert len(specs)==len(paths)==100
    assert all(len(path)==80 and len(set(path))==80 for path in paths.values())
    assert p12.BUDGETS==tuple(range(16,81))
    assert json.loads((OUT/"baseline_gate.json").read_text())["initial_B16_matches"]==100


def test_kernel_definitions_and_fairness() -> None:
    specs=json.loads((OUT/"kernel_specification.json").read_text())["models"]
    assert specs["G0"]["family"]=="Matern" and specs["G0"]["nu"]==1.5 and not specs["G0"]["ard"]
    assert specs["G1"]["family"]=="RBF" and not specs["G1"]["ard"]
    assert specs["G2"]["family"]=="RBF" and specs["G2"]["ard"]
    assert specs["G3"]["family"]=="Matern" and specs["G3"]["nu"]==1.5 and specs["G3"]["ard"]
    assert specs["G4"]["family"]=="Matern" and specs["G4"]["nu"]==2.5 and not specs["G4"]["ard"]
    assert len({tuple(v["amplitude_bounds"]) for v in specs.values()})==1
    assert len({tuple(v["length_scale_bounds"]) for v in specs.values()})==1
    assert all(v["optimizer"]=="fmin_l_bfgs_b" and v["n_restarts_optimizer"]==0 for v in specs.values())


def test_inputs_and_information_flow_are_frozen() -> None:
    source=(ROOT/"src"/"week9_phase1_12_gpc_kernel_adequacy.py").read_text()
    fit_source=source[source.index("def make_kernel"):source.index("def checkpoint_path")]+source[source.index("def run_one("):source.index("def run_new_kernels")]
    assert p12.FEATURES==("P","VX","LS","ST")
    assert "scaler.transform(x4[revealed]),labels[revealed]" in source
    assert "revealed=np.asarray(path[:budget]" in source
    assert "log_h" not in "|".join(p12.FEATURES)
    assert all(token not in fit_source for token in ("-1.713","-1.219","first_conduction"))


def test_new_predictions_and_diagnostics_complete() -> None:
    predictions=pd.read_csv(OUT/"new_kernel_predictions.csv.gz")
    diagnostics=pd.read_csv(OUT/"kernel_fit_diagnostics.csv.gz",low_memory=False)
    assert len(predictions)==100*4*65*81
    assert set(predictions.model)==set(p12.NEW_MODELS)
    assert predictions.groupby(["run_id","model","budget"]).size().eq(81).all()
    assert len(diagnostics)==100*4*65
    assert diagnostics[diagnostics.model.isin(("G2","G3"))][["l_P","l_VX","l_LS","l_ST","anisotropy_ratio"]].notna().all().all()


def test_repeat_inference_and_predeclared_contrasts() -> None:
    repeat=pd.read_csv(OUT/"repeat_metrics.csv"); contrasts=pd.read_csv(OUT/"paired_contrasts.csv")
    assert repeat.repeat.nunique()==20
    assert contrasts.bootstrap_draws.min()>=10_000
    expected={"G3-G0","G3-H","G1-G0","G2-G1","G4-G0","G2-H","G1-H","G4-H"}
    assert expected.issubset(set(contrasts[contrasts.subset.eq("B1_q20")].contrast))


def test_descriptive_best_and_oracle_claim_discipline() -> None:
    report=(OUT/"FINAL_PHASE1_12_REPORT.md").read_text()
    oracle=pd.read_csv(OUT/"oracle_gpc_diagnostic.csv")
    assert "not treated as predeclared winner inference" in report
    assert oracle.diagnostic_status.eq("NON_DEPLOYABLE_REPEATWISE_ORACLE").all()
    assert "equivalent to h" not in report.lower()


def test_notebook_executed_and_figures_hashed() -> None:
    notebook=nbformat.read(ROOT/"notebooks"/"week_09"/"10_week9_phase1_12_gpc_kernel_adequacy.ipynb",as_version=4)
    code=[cell for cell in notebook.cells if cell.cell_type=="code"]
    assert code and all(cell.execution_count is not None for cell in code)
    assert not [o for cell in code for o in cell.get("outputs",[]) if o.get("output_type")=="error"]
    figures=pd.read_csv(OUT/"figure_manifest.csv"); assert len(figures)==4
    assert all(p12.sha256_file(OUT/"figures"/r.figure)==r.sha256 for r in figures.itertuples(index=False))


def test_validation_has_at_least_forty_real_checks() -> None:
    validation=json.loads((OUT/"validation_report.json").read_text())
    assert validation["status"]=="PASS"
    assert validation["check_count"]>=40
    assert validation["passed"]==validation["check_count"]


def test_historical_outputs_unchanged() -> None:
    assert p12.historical_changes()==[]


def test_manifest_hashes_and_red_team_language() -> None:
    manifest=json.loads((OUT/"run_manifest.json").read_text())
    for item in manifest["files"]:
        data=p12.artifact_bytes(ROOT/item["path"])
        assert hashlib.sha256(data).hexdigest()==item["sha256"]
    report=(OUT/"FINAL_RED_TEAM_REPORT.md").read_text().lower()
    assert "unresolved g3-h interval is not called equivalence" in report
    assert "no acquisition claim" in report or "new acquisition" in report
