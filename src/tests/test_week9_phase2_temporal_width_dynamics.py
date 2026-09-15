"""Executable correction guards for Week 9 Phase 2."""
from __future__ import annotations
import json, subprocess
from pathlib import Path
import nbformat
import numpy as np
import pandas as pd
from nbconvert.preprocessors import ExecutePreprocessor
from src import week9_phase2_temporal_width_dynamics as p2

def out(name: str) -> Path:
    path=p2.OUTPUT/name; assert path.is_file(),path; return path

def test_population_labels_ids_ls_st_and_h() -> None:
    pop=p2.load_population()
    assert len(pop)==405 and int(pop.has_keyhole.sum())==73 and pop.experiment_name.is_unique
    assert np.allclose(pop.LS,pop.LS_m) and np.allclose(pop.ST,pop.ST_K)
    assert np.allclose(p2.log_h(pop),np.log(pop.P/np.sqrt(pop.VX*pop.LS**3)))

def test_authoritative_axis_semantics_and_machine_audit() -> None:
    audit=pd.read_csv(out("axis_semantics_audit.csv")).set_index("quantity")
    assert audit.loc["longitudinal_length","formula"]=="x_max - x_min"
    assert audit.loc["transverse_width","formula"]=="y_max - y_min"
    assert audit.status.eq("PASS").all() and audit.numeric_mapping_verified.all()
    source=(p2.ROOT/"src"/"week7_phase2_sph_v2_physical_target_extraction.py").read_text()
    assert "length_m = extents[:, 0]" in source and "width_m = extents[:, 1]" in source

def test_actual_width_and_length_equal_correct_bounds_columns() -> None:
    pop=p2.load_population().reset_index(drop=True); pop["population_row_index"]=np.arange(len(pop)); pop["log_h"]=p2.log_h(pop)
    merged=pop.merge(p2.source_paths(),on="experiment_name",how="left")
    for _,row in merged[merged.bounds_path.map(p2._existing)&merged.time_path.map(p2._existing)].head(3).iterrows():
        bounds,_=p2.p2.load_numeric(Path(row.bounds_path),"position-bounds_melt.dat")
        _,profile,_=p2._parse_trace(row)
        assert np.isfinite(bounds[:,3]-bounds[:,2]).any() and np.isfinite(bounds[:,1]-bounds[:,0]).any()
        assert profile.transverse_width_um.min()>=0 and profile.longitudinal_length_um.min()>=0

def test_time_active_derivative_tau_and_synthetic_guards() -> None:
    audit=pd.read_csv(out("width_timeseries_audit.csv")); profiles=pd.read_csv(out("temporal_profiles.csv.gz"))
    assert (audit.nonpositive_dt_count_raw==0).all() and (audit.duplicate_timestamp_count==0).all() and (audit.cooling_rows_in_primary==0).all()
    endpoints=profiles.groupby("experiment_name").tau.agg(["min","max"])
    assert np.allclose(endpoints["min"],0) and np.allclose(endpoints["max"],1)
    assert p2.synthetic_derivative_error()<1e-8 and np.isfinite(profiles.transverse_dWdt_raw_um_per_ms).all()

def test_prefix_has_no_future_and_uses_robust_derivatives() -> None:
    prefix=pd.read_csv(out("prefix_temporal_features.csv")); pred=pd.read_csv(out("prefix_oof_predictions.csv.gz"))
    assert (prefix.latest_source_tau<=prefix.prefix_tau+1e-12).all() and (pred.latest_source_tau<=pred.prefix_tau+1e-12).all()
    assert "robust_max_positive_dWdt_so_far_um_per_ms" in prefix and "max_positive_dWdt_so_far_um_per_ms" not in prefix

def test_model_information_flow_and_grouped_inference() -> None:
    repeat=pd.read_csv(out("model_repeat_level_metrics.csv")); pred=pd.read_csv(out("model_oof_predictions.csv.gz"))
    assert repeat.repeat.nunique()==20 and pred.run_id.nunique()==100
    forbidden={"truth","has_keyhole","B1","q20","q30","is_q20","is_q30"}; used=set(p2.STATIC_FEATURES)|set(p2.TEMPORAL_FEATURES)|set(p2.PREFIX_FEATURES)|{"log_h"}
    assert not (forbidden&used) and not (set(p2.RAW_DERIVATIVE_FEATURES)&set(p2.TEMPORAL_FEATURES))
    assert set(pred.model)=={"h_only","static_width","width_dynamics","h_plus_width_dynamics","h_plus_width_shape_only"}

def test_scaler_is_train_only_executable() -> None:
    model=p2._model(1.0).fit(np.array([[0.],[2.],[4.]]),np.array([0,0,1])); assert np.allclose(model.named_steps["scale"].mean_,[2.0])

def test_pca_is_label_free_and_uses_primary_robust_representation() -> None:
    loadings=pd.read_csv(out("pca_loadings.csv")); scores=pd.read_csv(out("pca_scores.csv"))
    assert set(loadings.feature)==set(p2.TEMPORAL_FEATURES) and not (set(p2.RAW_DERIVATIVE_FEATURES)&set(loadings.feature))
    assert "has_keyhole" not in set(loadings.feature) and np.isfinite(scores[["PC1","PC2"]]).all().all()

def test_robust_derivative_rule_is_fixed_and_claims_are_gated() -> None:
    source=Path(p2.__file__).read_text(); block=source[source.index("def local_linear_grid_derivative"):source.index("def synthetic_derivative_error")]
    assert "half_window: int = 2" in block and "has_keyhole" not in block
    gate=pd.read_csv(out("derivative_robustness_gate.csv")); assert set(gate.status)<={"ROBUST","QUALIFIED","UNSTABLE"} and len(gate)==5

def test_onset_and_warning_language_guards() -> None:
    onset=pd.read_csv(out("keyhole_onset_audit.csv")); valid=onset[onset.onset_available.astype(bool)]
    assert valid.has_keyhole.eq(1).all() and valid.first_keyhole_monitor_row_index.notna().all() and ((valid.first_keyhole_tau>=0)&(valid.first_keyhole_tau<=1)).all()
    assert not pd.read_csv(out("keyhole_lead_time_results.csv")).warning_threshold_fitted.any()
    text=out("SUPERVISOR_PHASE2_ONE_PAGE.md").read_text(); assert "NOT SUPPORTED" in text and "first-observed" in text.lower()

def test_longitudinal_is_preserved_but_separate() -> None:
    comparison=pd.read_csv(out("longitudinal_vs_transverse_summary.csv"))
    assert set(comparison.axis_quantity)=={"longitudinal_length_delta_X","transverse_width_delta_Y"}
    assert (p2.OUTPUT/"longitudinal_length_diagnostic"/"published_delta_x_summary.csv").is_file()

def test_committed_notebook_has_stored_outputs_and_reexecutes() -> None:
    notebook=nbformat.read(p2.NOTEBOOK,as_version=4); executed=[c for c in notebook.cells if c.cell_type=="code" and c.execution_count is not None and c.outputs]
    assert len(executed)>=10
    ExecutePreprocessor(timeout=300,kernel_name="python3").preprocess(notebook,{"metadata":{"path":str(p2.ROOT)}})

def test_figures_and_hashes() -> None:
    manifest=pd.read_csv(out("figure_manifest.csv")); assert len(manifest)==8
    for row in manifest.itertuples(index=False): assert p2.sha256_file(p2.FIGURES/row.figure)==row.sha256

def test_manifest_artifact_hashes_and_validation_snapshot_match() -> None:
    run=json.loads(out("run_manifest.json").read_text()); validation=json.loads(out("validation_report.json").read_text())
    assert run["validation"]==validation and run["notebook_sha256"]==p2.sha256_file(p2.NOTEBOOK)
    for relative,digest in run["artifact_hashes"].items(): assert p2.sha256_file(p2.OUTPUT/relative)==digest

def test_reports_share_canonical_numbers_and_claims() -> None:
    texts=[out(name).read_text() for name in ("FINAL_PHASE2_REPORT.md","SUPERVISOR_PHASE2_ONE_PAGE.md","claim_ledger.md")]
    for token in ("350/405","70","q20 balanced accuracy","Final Phase 2 claim"): assert all(token in text for text in texts)

def test_historical_phase1_outputs_unchanged() -> None:
    changed=subprocess.run(["git","diff","--name-only",p2.STARTING_SHA,"--","outputs/week8_5_frozen_confirmation","outputs/week9_phase1_close_week8","outputs/week9_phase1_5_h_physics_confirmation","outputs/week9_phase1_7_physics_ridge_residual_gp","outputs/week9_phase1_8_model_path_decomposition"],cwd=p2.ROOT,text=True,capture_output=True,check=True).stdout.strip()
    assert changed==""
