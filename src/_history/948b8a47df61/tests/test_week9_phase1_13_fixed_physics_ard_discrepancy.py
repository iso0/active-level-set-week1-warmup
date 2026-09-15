from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import nbformat
import numpy as np
import pandas as pd

from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13


ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs"/"week9_phase1_13_fixed_physics_ard_discrepancy"


def test_parent_placeholder_and_historical_gate() -> None:
    gate=json.loads((OUT/"baseline_gate.json").read_text())
    assert subprocess.run(["git","merge-base","--is-ancestor",p13.PHASE112_SHA,"HEAD"],cwd=ROOT).returncode==0
    assert gate["phase112_placeholder_absent"]
    assert "{future}" not in (ROOT/"outputs/week9_phase1_12_gpc_kernel_adequacy/FINAL_PHASE1_12_REPORT.md").read_text()
    assert p13.historical_changes()==[]


def test_population_paths_budgets_and_frozen_values() -> None:
    population,specs,paths=p13.load_inputs(); gate=json.loads((OUT/"baseline_gate.json").read_text())
    assert (len(population),int(population.has_keyhole.sum()))==(405,73)
    assert len(specs)==len(paths)==100 and all(len(v)==80 and len(set(v))==80 for v in paths.values())
    assert p13.BUDGETS==tuple(range(16,81))
    assert abs(gate["H_q20_AULC"]-.8308134191176471)<1e-12
    assert abs(gate["G0_q20_AULC"]-.8135202205882353)<1e-12
    assert abs(gate["G3_q20_AULC"]-.826594669117647)<1e-12
    assert abs(gate["M2_q20_AULC"]-.8302297794117648)<1e-12


def test_kernel_and_bound_matched_control() -> None:
    spec=json.loads((OUT/"kernel_specification.json").read_text())
    assert spec["models"]["M2W"]["ard"] is False and spec["models"]["M3"]["ard"] is True
    assert spec["shared"]["primary_length_bounds"]==[.01,100.0]
    assert spec["shared"]["amplitude_bounds_identical"]
    assert spec["shared"]["matern_nu"]==1.5 and spec["shared"]["restarts"]==0
    assert p13.RESIDUAL_SD_BOUNDS==(.05,1.0)
    assert len(np.ravel(p13.residual_kernel("M3").k2.length_scale))==4
    assert len(np.ravel(p13.residual_kernel("M2W").k2.length_scale))==1


def test_stage1_stage2_information_flow() -> None:
    source=(ROOT/"src/week9_phase1_13_fixed_physics_ard_discrepancy.py").read_text()
    fit=source[source.index("def residual_kernel"):source.index("def kernel_specification")]+source[source.index("def fit_hybrid"):source.index("def components")]
    assert "p11.fit_physics_mean(logh,labels,revealed" in source
    assert "mean_train=physics.latent" in source
    assert p13.FEATURES==("P","VX","LS","ST")
    assert all(token not in fit for token in ("B1_q20","B1_q30","Masinelli","-1.713","-1.219"))
    assert "path[:budget]" in source


def test_ard_zero_mean_parity() -> None:
    parity=json.loads((OUT/"ard_parity_report.json").read_text())
    assert parity["status"]=="PASS"
    assert parity["maximum_probability_difference"]<=1e-5
    assert len(parity["cases"])==4


def test_new_main_and_sensitivity_predictions_complete() -> None:
    predictions=pd.read_csv(OUT/"new_predictions.csv.gz",usecols=["model","run_id","budget"])
    assert len(predictions[predictions.model.eq("M2W")])==100*65*81
    assert len(predictions[predictions.model.eq("M3")])==100*65*81
    sensitivity=pd.read_csv(OUT/"upper_bound_sensitivity.csv")
    assert sensitivity.budget.tolist()==[16,40,80]


def test_predeclared_contrasts_regions_and_repeat_blocks() -> None:
    contrasts=pd.read_csv(OUT/"paired_contrasts.csv"); regions=pd.read_csv(OUT/"early_late_contrasts.csv"); repeat=pd.read_csv(OUT/"repeat_metrics.csv")
    expected={"M3-H","M3-M2","M3-M2W","M3-G3","M3-G0"}
    assert expected==set(contrasts[contrasts.subset.eq("B1_q20")].contrast)
    assert {"M3-H","M3-G3"}==set(regions.contrast)
    assert set(regions.region)=={"EARLY_B16_40","LATE_B41_80"}
    assert repeat.repeat.nunique()==20 and contrasts.bootstrap_draws.min()>=10_000


def test_checkpoint_q30_full_and_diagnostics() -> None:
    checkpoint=pd.read_csv(OUT/"checkpoint16_40_80_summary.csv"); full=pd.read_csv(OUT/"full81_checkpoint_summary.csv"); contrasts=pd.read_csv(OUT/"paired_contrasts.csv"); ard=pd.read_csv(OUT/"ard_lengthscale_summary.csv"); role=pd.read_csv(OUT/"residual_role_summary.csv")
    assert set(checkpoint.budget)==set(p13.CHECKPOINT_BUDGETS)
    assert len(full)==5*3*7
    assert {"M3-H","M3-M2W","M3-G3"}.issubset(set(contrasts[contrasts.subset.eq("B1_q30")].contrast))
    assert {"l_P","l_VX","l_LS","l_ST"}.issubset(set(ard.parameter))
    assert set(role.budget)==set(p13.CHECKPOINT_BUDGETS)


def test_claim_discipline_and_no_placeholders() -> None:
    report=(OUT/"FINAL_PHASE1_13_REPORT.md").read_text().lower(); red=(OUT/"FINAL_RED_TEAM_REPORT.md").read_text()
    assert all(token not in report for token in ("{future}","{decision}","todo","tbd","acquisition superiority","causal feature importance"))
    assert "100 folds are not called independent" in red
    assert "no new acquisition" in red.lower()


def test_notebook_figures_validation_and_manifest() -> None:
    notebook=nbformat.read(ROOT/"notebooks/week_09/11_week9_phase1_13_fixed_physics_ard_discrepancy.ipynb",as_version=4); code=[c for c in notebook.cells if c.cell_type=="code"]
    assert code and all(c.execution_count is not None for c in code)
    assert not [o for c in code for o in c.get("outputs",[]) if o.get("output_type")=="error"]
    figures=pd.read_csv(OUT/"figure_manifest.csv"); assert len(figures)<=5 and all(p13.sha256_file(OUT/"figures"/r.figure)==r.sha256 for r in figures.itertuples(index=False))
    validation=json.loads((OUT/"validation_report.json").read_text()); assert validation["status"]=="PASS" and validation["check_count"]>=56 and validation["passed"]==validation["check_count"]
    manifest=json.loads((OUT/"run_manifest.json").read_text())
    for item in manifest["files"]: assert hashlib.sha256(p13.artifact_bytes(ROOT/item["path"])).hexdigest()==item["sha256"]
