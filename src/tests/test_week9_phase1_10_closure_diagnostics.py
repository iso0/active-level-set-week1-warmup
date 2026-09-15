from __future__ import annotations

import inspect
import json
import subprocess

import nbformat as nbf
import numpy as np
import pandas as pd

from src import week9_phase1_10_closure_diagnostics as c


def test_start_sha_and_frozen_phase110_are_untouched() -> None:
    assert c.START_SHA == "45e2677b7a57ed3aa5ad5154459100a9b5d2d436"
    assert subprocess.run(["git","merge-base","--is-ancestor",c.START_SHA,"HEAD"],cwd=c.ROOT).returncode == 0
    assert c.historical_changes() == []
    report=(c.OUTPUT/"FINAL_PHASE1_10_CLOSURE_REPORT.md").read_text(encoding="utf-8")
    assert "GENERIC_DIRECTION_SUPERIOR" in report


def test_population_and_strict_CK_audit() -> None:
    population=c.load_population_readonly()
    assert population.groupby("material").size().to_dict()=={"316L":60,"Ti64":60}
    assert population.groupby("material").has_keyhole.sum().to_dict()=={"316L":23,"Ti64":34}
    strict=c.make_strict_population(population)
    assert set(strict.raw_mode)=={"C","K"}
    assert not strict.raw_mode.isin(["T","CT","TK"]).any()
    assert strict.groupby(["material","raw_mode"]).size().to_dict()=={("316L","C"):37,("316L","K"):11,("Ti64","C"):26,("Ti64","K"):22}
    audit=pd.read_csv(c.OUTPUT/"strict_ck_population_audit.csv").set_index("material")
    assert audit.loc["Ti64","unique_conditions"]==32 and audit.loc["316L","unique_conditions"]==32
    assert audit.folds.eq(5).all()


def test_raw_scale_coefficient_conversion_and_alpha_formula() -> None:
    beta_p,beta_vx,alpha=c.recover_raw_coefficients([6.0,-4.0],[2.0,4.0])
    assert (beta_p,beta_vx)==(3.0,-1.0)
    assert np.isclose(alpha,-1/3)
    assert not np.isclose(alpha,-4/6)  # standardized ratio must not be used
    estimates=pd.read_csv(c.OUTPUT/"exponent_fold_estimates.csv")
    assert np.allclose(estimates.beta_P,estimates.gamma_P/estimates.sigma_P)
    assert np.allclose(estimates.beta_VX,estimates.gamma_VX/estimates.sigma_VX)
    assert np.allclose(estimates.alpha,estimates.beta_VX/estimates.beta_P)


def test_exponent_protocol_is_repeat_blocked_and_stable() -> None:
    estimates=pd.read_csv(c.OUTPUT/"exponent_fold_estimates.csv")
    repeats=pd.read_csv(c.OUTPUT/"exponent_repeat_summary.csv")
    summary=pd.read_csv(c.OUTPUT/"exponent_summary.csv")
    assert estimates.groupby("material").size().eq(100).all()
    assert estimates.groupby("material").alpha_valid.sum().to_dict()=={"316L":99,"Ti64":100}
    assert not estimates.beta_P_near_zero.any() and int(estimates.alpha_extreme.sum())==1
    assert estimates.groupby("material").beta_P_positive.mean().ge(.99).all()
    assert repeats.groupby("material").size().eq(20).all()
    assert repeats.folds.eq(5).all() and repeats.valid_folds.ge(4).all()
    assert int(repeats.invalid_folds.sum())==1
    assert c.N_REPEATS==20 and c.BOOTSTRAP_DRAWS>=10000 and c.THEORY_ALPHA==-0.5
    assert set(summary.summary_type)=={"grouped_cv_repeat_block","descriptive_full_data"}


def test_strict_grouping_and_complete_oof_metrics() -> None:
    folds=pd.read_csv(c.OUTPUT/"strict_ck_fold_manifest.csv")
    metrics=pd.read_csv(c.OUTPUT/"strict_ck_repeat_metrics.csv")
    assert folds.groupby(["material","repeat","condition_id"]).fold.nunique().max()==1
    assert folds.groupby(["material","repeat","bundle_id"]).size().eq(1).all()
    per_fold=folds.groupby(["material","repeat","fold"]).has_keyhole.agg(["min","max"])
    assert per_fold["min"].eq(0).all() and per_fold["max"].eq(1).all()
    assert metrics.groupby(["material","model"]).repeat.nunique().eq(20).all()
    assert set(metrics.model)=={"H","G"}


def test_regularization_settings_are_exact_and_not_a_sweep() -> None:
    settings=c.regularization_settings()
    assert settings["R1_C1"]["C"]==1.0
    assert settings["R2_C1e6"]["C"]==1e6
    assert settings["R3_unpenalized"]["status"] in {"AVAILABLE","R3_UNAVAILABLE"}
    assert (settings["R3_unpenalized"]["status"]=="AVAILABLE")==c.probe_r3()[0]
    table=pd.read_csv(c.OUTPUT/"regularization_sensitivity.csv")
    assert set(table.setting)=={"R1_C1","R2_C1e6","R3_unpenalized"}
    available=table[table.status.eq("AVAILABLE")]
    assert available.valid_coefficient_fits.add(available.invalid_coefficient_fits).eq(100).all()
    assert available.converged_fraction.eq(1).all()
    assert available.beta_P_near_zero_count.eq(0).all()


def test_train_only_features_exclude_optical_and_internal_boundary_inputs() -> None:
    source=inspect.getsource(c.fit_logistic)
    assert "StandardScaler().fit(x_train)" in source
    assert 'features = ["log_h"] if model == "H" else ["log_P", "log_VX"]' in source
    assert not {"optical","emission","reflection","B1","q20","q30"}.intersection({"log_h","log_P","log_VX"})


def test_notebook_figures_validation_and_manifest() -> None:
    notebook=nbf.read(c.NOTEBOOK,as_version=4)
    code=[cell for cell in notebook.cells if cell.cell_type=="code"]
    assert code and all(cell.execution_count is not None for cell in code)
    assert not [output for cell in code for output in cell.get("outputs",[]) if output.get("output_type")=="error"]
    figures=pd.read_csv(c.OUTPUT/"figure_manifest.csv")
    assert len(figures)==2
    assert all(c.sha256_file(c.FIGURES/row.figure)==row.sha256 for row in figures.itertuples(index=False))
    validation=json.loads((c.OUTPUT/"validation_report.json").read_text(encoding="utf-8"))
    manifest=json.loads((c.OUTPUT/"run_manifest.json").read_text(encoding="utf-8"))
    assert validation["status"]=="PASS" and validation["check_count"]==28
    assert manifest["validation"]==validation
    for row in manifest["files"]:
        path=c.ROOT/row["path"]
        assert path.is_file() and c.artifact_sha256(path)==row["sha256"]
        assert c.artifact_size(path)==row["size_bytes"]


def test_claim_boundaries_and_no_raw_data() -> None:
    ledger=(c.OUTPUT/"claim_ledger.md").read_text(encoding="utf-8")
    assert "The LS^-3/2 exponent is externally validated. | NOT TESTABLE" in ledger
    assert "Physics is universally proven. | NOT SUPPORTED" in ledger
    assert "Frozen Phase 1.10 primary verdict changes. | NOT ALLOWED / UNCHANGED" in ledger
    assert subprocess.check_output(["git","ls-files",".cache"],cwd=c.ROOT,text=True).strip()==""
    assert not list(c.ROOT.rglob("Neuchatel data.zip"))
    assert c.historical_changes()==[]
