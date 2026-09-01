from __future__ import annotations

import inspect
import json
import subprocess

import nbformat as nbf
import numpy as np
import pandas as pd

from src import week9_phase1_11_fixed_mean_discrepancy_gp as p


def test_start_population_h_and_historical_integrity() -> None:
    population,specs,paths,_=p.load_inputs()
    assert p.START_SHA=="e33cca4f81b865d330577ef9a8140c4bbe306e5a"
    assert len(population)==405 and int(population.has_keyhole.sum())==73
    expected=np.log(population.P.to_numpy(float)/np.sqrt(population.VX.to_numpy(float)*population.LS.to_numpy(float)**3))
    np.testing.assert_allclose(p.log_h_values(population),expected,rtol=0,atol=1e-12)
    assert len(specs)==len(paths)==100 and p.historical_changes()==[]


def test_a0_path_and_initial_design_are_exact() -> None:
    population,specs,paths,_=p.load_inputs()
    for spec in specs:
        path=paths[spec.run_id]
        assert len(path)==80 and len(set(path))==80
        assert path[:16]==p.w85.initial_design(spec,population)
        assert set(path)<=set(spec.train_indices)
        assert set(path).isdisjoint(spec.test_indices)


def test_stage1_is_prefix_only_latent_logit_and_hidden_labels_invariant() -> None:
    population,specs,paths,_=p.load_inputs(); spec=specs[0]; revealed=np.asarray(paths[spec.run_id][:16])
    logh=p.log_h_values(population); labels=population.has_keyhole.astype(int).to_numpy()
    fit=p.fit_physics_mean(logh,labels,revealed,7); latent=fit.latent(logh)
    altered=labels.copy(); hidden=np.setdiff1d(np.arange(len(labels)),revealed); altered[hidden]=1-altered[hidden]
    changed=p.fit_physics_mean(logh,altered,revealed,7)
    np.testing.assert_allclose(latent,changed.latent(logh),rtol=0,atol=0)
    assert not np.allclose(latent,p.expit(latent))
    assert np.array_equal(fit.revealed_indices,revealed)


def test_stage2_freezes_mean_and_uses_only_four_inputs() -> None:
    population,specs,paths,_=p.load_inputs(); spec=specs[0]; revealed=paths[spec.run_id][:16]
    x4=population.loc[:,p.FEATURES].to_numpy(float); labels=population.has_keyhole.astype(int).to_numpy(); logh=p.log_h_values(population)
    fit=p.fit_fixed_mean(x4,logh,labels,revealed,spec.train_indices,11)
    assert fit.gp.X_train_.shape==(16,4)
    assert fit.physics.model.coef_.shape==(1,1)
    np.testing.assert_allclose(fit.gp.mean_train_,fit.physics.latent(logh[np.asarray(revealed)]))
    source=inspect.getsource(p.fit_fixed_mean)
    assert "x4" in source and "FixedMeanLaplaceGPC(residual_kernel()" in source
    assert "log_h" not in inspect.getsource(p.residual_kernel)


def test_no_external_or_evaluation_information_enters_model() -> None:
    source=inspect.getsource(p.fit_fixed_mean)+inspect.getsource(p.run_one_spec)
    assert "Masinelli" not in source and "-1.713" not in source and "-1.219" not in source
    assert p.FEATURES==("P","VX","LS","ST")
    fit_portion=inspect.getsource(p.fit_fixed_mean)
    assert all(token not in fit_portion for token in ("B1","q20","q30","acquisition"))


def test_zero_mean_parity_and_kernel_contract() -> None:
    report=json.loads((p.OUTPUT/"implementation_parity_report.json").read_text())
    assert report["status"]=="PASS"
    assert report["maximum_fixed_kernel_probability_difference"]<=1e-5
    assert report["sklearn_private_estimator_subclassed"] is False
    assert p.RESIDUAL_SD_BOUNDS==(0.05,1.0) and p.LENGTH_SCALE_BOUNDS==(0.25,4.0)
    kernel=p.residual_kernel(); assert kernel.k2.nu==1.5


def test_baseline_and_prediction_completeness() -> None:
    gate=json.loads((p.OUTPUT/"baseline_gate.json").read_text())
    assert abs(gate["M0_q20_AULC"]-0.8135202205882354)<1e-12
    assert abs(gate["M1_A0_q20_AULC"]-0.8299724264705881)<1e-12
    m2=pd.read_csv(p.OUTPUT/"fixed_mean_oof_predictions.csv.gz")
    mh=pd.read_csv(p.OUTPUT/"h_only_a0_predictions.csv.gz")
    assert len(m2)==len(mh)==100*65*81
    assert m2.run_id.nunique()==mh.run_id.nunique()==100
    assert m2.budget.nunique()==mh.budget.nunique()==65


def test_repeat_inference_and_contrasts_are_matched() -> None:
    repeats=pd.read_csv(p.OUTPUT/"repeat_metrics.csv")
    contrasts=pd.read_csv(p.OUTPUT/"paired_contrasts.csv")
    assert repeats.repeat.nunique()==20 and p.BOOTSTRAP_DRAWS>=10_000
    assert set(contrasts.contrast)=={"M2-M0","M2-M1","M2-MH"}
    assert set(contrasts.subset)=={"B1_q20","B1_q30"}
    part=repeats[repeats.subset.eq("B1_q20")].pivot(index="repeat",columns="model",values="accuracy_AULC_16_80")
    expected=float((part.M2-part.M0).mean())
    actual=float(contrasts[(contrasts.contrast.eq("M2-M0"))&contrasts.subset.eq("B1_q20")].mean_difference.iloc[0])
    assert abs(expected-actual)<1e-14


def test_matched_bound_definitions_and_diagnostics() -> None:
    detail=pd.read_csv(p.OUTPUT/"residual_stability_detail.csv.gz")
    assert len(detail[detail.model.eq("M1")])==len(detail[detail.model.eq("M2")])==6500
    assert not detail.duplicated(["run_id","budget","model"]).any()
    m2=detail[detail.model.eq("M2")]
    np.testing.assert_array_equal(m2.residual_sd_any_bound_hit.astype(bool),m2.residual_sd_lower_bound_hit.astype(bool)|m2.residual_sd_upper_bound_hit.astype(bool))
    assert set(m2.fallback_status.dropna().unique())=={"none"}


def test_notebook_figures_validation_and_manifest() -> None:
    notebook=nbf.read(p.NOTEBOOK,as_version=4); code=[cell for cell in notebook.cells if cell.cell_type=="code"]
    assert code and all(cell.execution_count is not None for cell in code)
    assert not [out for cell in code for out in cell.get("outputs",[]) if out.get("output_type")=="error"]
    figures=pd.read_csv(p.OUTPUT/"figure_manifest.csv"); assert len(figures)==4
    assert all(p.sha256_file(p.FIGURES/row.figure)==row.sha256 for row in figures.itertuples(index=False))
    validation=json.loads((p.OUTPUT/"validation_report.json").read_text()); assert validation["status"]=="PASS" and validation["check_count"]==36
    manifest=json.loads((p.OUTPUT/"run_manifest.json").read_text()); assert manifest["validation"]==validation
    for row in manifest["files"]:
        path=p.ROOT/row["path"]; payload=p.artifact_bytes(path)
        assert path.is_file() and p.hashlib.sha256(payload).hexdigest()==row["sha256"] and len(payload)==row["size_bytes"]


def test_claim_language_and_no_checkpoint_or_raw_data_tracking() -> None:
    report=(p.OUTPUT/"FINAL_PHASE1_11_REPORT.md").read_text().lower()
    assert "no acquisition claim" in report and "does not solve identifiability" in report
    tracked=subprocess.check_output(["git","ls-files",str(p.OUTPUT/"checkpoints")],cwd=p.ROOT,text=True).strip()
    assert tracked=="" and p.historical_changes()==[]
