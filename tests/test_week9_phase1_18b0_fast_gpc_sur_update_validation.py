import json
import nbformat
import numpy as np
import pandas as pd

from src import week9_phase1_18b0_fast_gpc_sur_update_validation as phase

OUT=phase.OUTPUT

def test_parent_population_paths():
    pop,specs,paths,_,_=phase.load_inputs()
    assert (len(pop),int(pop.has_keyhole.sum()))==(405,73)
    assert len(specs)==len(paths)==100

def test_frozen_design_scale_and_budgets():
    s=pd.read_csv(OUT/'snapshot_validation_design.csv');c=pd.read_csv(OUT/'candidate_validation_design.csv')
    assert len(s)==25 and set(s.budget)==set(phase.BUDGETS)
    assert len(c)==307 and c.groupby('snapshot_id').size().min()>=12

def test_candidate_design_hash_and_no_leakage():
    c=pd.read_csv(OUT/'candidate_validation_design.csv');h=json.loads((OUT/'candidate_validation_design_sha256.json').read_text())
    assert h['sha256']==phase.sha256_file(OUT/'candidate_validation_design.csv')
    assert {'truth','B1','q20','q30','has_keyhole'}.isdisjoint(c.columns)

def test_both_hypothetical_labels_all_levels():
    r=pd.read_csv(OUT/'runtime_benchmark.csv')
    assert len(r)==2456 and set(r.update_level)==set(phase.LEVELS)
    assert r.groupby(['snapshot_id','candidate_population_row_index','update_level']).hypothetical_label.nunique().eq(2).all()

def test_fast_special_cases():
    assert pd.read_csv(OUT/'special_case_validation.csv').status.eq('PASS').all()

def test_probability_integration():
    assert pd.read_csv(OUT/'probability_integration_validation.csv').absolute_error.max()<.001

def test_fast_reproduces_phase18a_scores():
    s=pd.read_csv(OUT/'candidate_sur_scores.csv.gz').query("update_level=='FAST_RANK1'")
    d=pd.read_csv(OUT/'candidate_validation_design.csv')
    m=s.merge(d,on=['snapshot_id','candidate_population_row_index'])
    assert np.max(np.abs(m.sur_score-m.fast_sur_score_pre_reveal))<1e-10

def test_exact_fixed_freezes_model():
    a=pd.read_csv(OUT/'parameter_freeze_audit.csv.gz').query("update_level=='EXACT_LAPLACE_FIXED_MODEL'")
    assert a.kernel_theta_max_abs_change.eq(0).all() and a.scaler_mean_max_abs_change.eq(0).all()
    assert a.physics_intercept_change.eq(0).all() and a.physics_coefficient_change.eq(0).all()

def test_physics_refit_only_stage1():
    a=pd.read_csv(OUT/'parameter_freeze_audit.csv.gz').query("update_level=='EXACT_LAPLACE_REFIT_PHYSICS'")
    assert a.kernel_theta_max_abs_change.eq(0).all() and a.scaler_mean_max_abs_change.eq(0).all()
    assert (a.physics_intercept_change.abs()+a.physics_coefficient_change.abs()).gt(0).all()

def test_all_posterior_quantities_finite():
    d=pd.read_csv(OUT/'candidate_level_update_results.csv.gz')
    cols=['current_latent_mean','current_latent_variance','current_probability','updated_latent_mean','updated_latent_variance','updated_probability','updated_uncertainty']
    assert np.isfinite(d[cols].to_numpy()).all()

def test_primary_decision_is_frozen_gate_result():
    d=json.loads((OUT/'primary_decision.json').read_text());spec=json.loads((OUT/'analysis_specification.json').read_text())
    assert d['gate']==spec['gate']==phase.GATE
    assert d['decision']=='FAST_SUR_REJECTED'

def test_refit_effect_decision():
    assert json.loads((OUT/'refit_effect_decision.json').read_text())['decision']=='PHYSICS_REFIT_MATTERS'

def test_no_new_trajectory_or_performance_claim():
    assert json.loads((OUT/'analysis_specification.json').read_text())['new_trajectory'] is False
    ledger=(OUT/'claim_ledger.md').read_text()
    assert 'SUR beats Margin or saves labels. | NOT TESTED' in ledger

def test_notebook_executed_with_outputs():
    nb=nbformat.read(phase.NOTEBOOK,as_version=4)
    assert all(c.cell_type!='code' or c.execution_count is not None for c in nb.cells)
    assert all(c.cell_type!='code' or c.outputs for c in nb.cells)

def test_figure_hashes():
    f=pd.read_csv(OUT/'figure_manifest.csv');assert len(f)==6
    assert all(phase.sha256_file(phase.FIGURES/r.figure)==r.sha256 for r in f.itertuples())

def test_validation_manifest_match_and_history_clean():
    v=json.loads((OUT/'validation_report.json').read_text());m=json.loads((OUT/'run_manifest.json').read_text())
    assert v==m['validation'] and v['status']=='PASS'
    assert phase.historical_changes()==[]
