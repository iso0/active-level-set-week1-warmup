from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import nbformat
import numpy as np
import pandas as pd

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_14_m3_margin_acquisition as p14


ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs"/"week9_phase1_14_m3_margin_acquisition"


def test_parent_baseline_population_and_protocol() -> None:
    gate=json.loads((OUT/"baseline_gate.json").read_text()); protocol=json.loads((OUT/"protocol_reconstruction.json").read_text()); population,specs,a0=p14.load_inputs()
    assert subprocess.check_output(["git","merge-base","HEAD",p14.PHASE113_SHA],cwd=ROOT,text=True).strip()==p14.PHASE113_SHA
    assert gate["phase113_decision"]=="HYBRID_GAIN_SUPPORTED"
    assert abs(gate["P0_q20_AULC"]-.8424908088235293)<1e-12
    assert (len(population),int(population.has_keyhole.sum()))==(405,73)
    assert len(specs)==len(a0)==100 and protocol["margin"]["uncertainty"]=="1 - 2*abs(p-0.5)"


def test_initial_designs_paths_and_candidate_safety() -> None:
    population,specs,a0=p14.load_inputs(); paths=pd.read_csv(OUT/"m3_margin_paths.csv.gz"); by_run={run:g.sort_values("query_order").population_row_index.astype(int).tolist() for run,g in paths.groupby("run_id")}
    for spec in specs:
        path=by_run[spec.run_id]
        assert path[:16]==a0[spec.run_id][:16]==w85.initial_design(spec,population)
        assert len(path)==len(set(path))==80
        assert set(path).issubset(spec.train_indices) and set(path).isdisjoint(spec.test_indices)


def test_margin_orientation_tie_break_and_no_label_input() -> None:
    candidate=np.array([9,3,7,5]); probability=np.array([.6,.4,.49,.51]); pool=np.zeros((10,4)); chosen,info=p14.choose_m3_margin(candidate,probability,pool,[0,1])
    assert chosen==5
    assert info["acquisition_definition"]=="classifier_margin"
    source=(ROOT/"src/week9_phase1_14_m3_margin_acquisition.py").read_text(); selector=source[source.index("def choose_m3_margin"):source.index("def run_one_spec")]
    assert all(token not in selector for token in ("labels","is_q20","is_q30","B1"))


def test_model_spec_and_no_residual_logh() -> None:
    spec=json.loads((OUT/"acquisition_specification.json").read_text()); source=(ROOT/"src/week9_phase1_14_m3_margin_acquisition.py").read_text(); fit=source[source.index("def run_one_spec"):source.index("def run_main")]
    assert spec["model"]["stage2_inputs"]==["P","VX","LS","ST"]
    assert spec["model"]["length_bounds"]==[.01,100.0] and spec["model"]["residual_sd_bounds"]==[.05,1.0]
    assert spec["model"]["restarts"]==0 and spec["model"]["log_h_residual_coordinate"] is False
    assert "x4=population.loc[:,FEATURES]" in fit and "p11.fit_physics_mean(logh,labels,revealed" in fit


def test_trajectory_prediction_and_query_completeness() -> None:
    predictions=pd.read_csv(OUT/"new_predictions.csv.gz",usecols=["run_id","budget","model"]); queries=pd.read_csv(OUT/"m3_margin_queries.csv.gz")
    assert len(predictions)==100*65*81 and predictions.model.eq("P1").all()
    assert predictions.run_id.nunique()==100 and set(predictions.budget)==set(p14.BUDGETS)
    assert len(queries)==100*64 and queries.groupby("run_id").size().eq(64).all()
    assert queries[["test_rows_available_to_acquisition","unrevealed_labels_available_to_acquisition","B1_q20_q30_available_to_acquisition"]].eq(False).all().all()


def test_same_model_b16_and_paired_inference() -> None:
    p1=pd.read_csv(OUT/"new_predictions.csv.gz"); chunks=[]
    for chunk in pd.read_csv(p14.PHASE13/"new_predictions.csv.gz",chunksize=200_000):
        x=chunk[chunk.model.eq("M3")]
        if len(x): chunks.append(x)
    p0=pd.concat(chunks,ignore_index=True); keys=["run_id","budget","population_row_index"]
    merged=p0[p0.budget.eq(16)].merge(p1[p1.budget.eq(16)],on=keys,suffixes=("_P0","_P1"),validate="one_to_one")
    assert np.allclose(merged.probability_P0,merged.probability_P1,rtol=0,atol=1e-12)
    contrasts=pd.read_csv(OUT/"paired_contrasts.csv"); q20=contrasts[contrasts.subset.eq("B1_q20")].iloc[0]
    assert q20.bootstrap_draws>=10_000 and q20.positive_repeat_blocks+q20.zero_repeat_blocks+q20.negative_repeat_blocks==20


def test_regions_thresholds_q30_and_full81() -> None:
    regions=pd.read_csv(OUT/"early_late_contrasts.csv"); thresholds=pd.read_csv(OUT/"sample_efficiency_thresholds.csv"); contrasts=pd.read_csv(OUT/"paired_contrasts.csv"); full=pd.read_csv(OUT/"full81_checkpoint_summary.csv")
    assert set(regions.region)=={"EARLY_B16_40","LATE_B41_80"}
    assert set(thresholds.threshold)==set(p14.THRESHOLDS) and thresholds.missing_crossings_not_imputed.all()
    assert len(contrasts[contrasts.subset.eq("B1_q30")])==1
    assert len(full)==3*3*7


def test_path_and_bound_sensitivity() -> None:
    detail=pd.read_csv(OUT/"path_overlap_detail.csv"); sensitivity=pd.read_csv(OUT/"acquisition_bound_sensitivity.csv"); diagnostics=pd.read_csv(OUT/"m3_active_fit_diagnostics.csv.gz",low_memory=False)
    assert len(detail)==100 and detail.paths_identical_through_B16.all()
    assert set(sensitivity.run_id)==set(p14.SENSITIVITY_RUN_IDS) and len(sensitivity)==20
    assert len(diagnostics)==6500 and diagnostics[["residual_sd","l_P","l_VX","l_LS","l_ST","optimizer_converged"]].notna().all().all()


def test_claim_discipline_and_historical_immutability() -> None:
    report=(OUT/"FINAL_PHASE1_14_REPORT.md").read_text().lower(); red=(OUT/"FINAL_RED_TEAM_REPORT.md").read_text().lower()
    assert p14.historical_changes()==[]
    assert all(token not in report for token in ("todo","tbd","universal acquisition superiority is demonstrated","theoretical sample complexity is proven"))
    assert "path divergence is described, not assumed beneficial" in red


def test_notebook_figures_validation_and_manifest() -> None:
    notebook=nbformat.read(p14.NOTEBOOK,as_version=4); code=[c for c in notebook.cells if c.cell_type=="code"]
    assert code and all(c.execution_count is not None for c in code)
    assert not [o for c in code for o in c.get("outputs",[]) if o.get("output_type")=="error"]
    figures=pd.read_csv(OUT/"figure_manifest.csv"); assert len(figures)<=5 and all(p14.sha256_file(p14.FIGURES/r.figure)==r.sha256 for r in figures.itertuples(index=False))
    validation=json.loads((OUT/"validation_report.json").read_text()); assert validation["status"]=="PASS" and validation["passed"]==validation["check_count"] and validation["check_count"]>=48
    manifest=json.loads((OUT/"run_manifest.json").read_text())
    for item in manifest["files"]: assert hashlib.sha256(p14.artifact_bytes(ROOT/item["path"])).hexdigest()==item["sha256"]
