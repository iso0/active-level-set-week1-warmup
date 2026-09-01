from __future__ import annotations

import inspect
import json
import subprocess

import nbformat as nbf
import numpy as np
import pandas as pd

from src import week9_phase1_10_external_experimental_validation as p10


def population() -> pd.DataFrame:
    return p10.build_population()


def test_exact_external_sources_and_population_gate() -> None:
    source = json.loads((p10.OUTPUT / "source_manifest.json").read_text(encoding="utf-8"))
    by_name = {row["filename"]: row for row in source["downloaded_files"]}
    assert source["github_commit"] == p10.GITHUB_COMMIT
    assert source["doi"] == p10.PAPER_DOI
    assert source["zenodo_doi"] == p10.ZENODO_DOI
    for name, expected in p10.SOURCE_FILES.items():
        assert by_name[name]["sha256"] == expected["sha256"]
        assert by_name[name]["size_bytes"] == expected["size"]
    assert by_name[p10.PAPER_FILE["filename"]]["sha256"] == p10.PAPER_FILE["sha256"]
    assert source["critical_field_verification"]["status"] == "VERIFIED_FROM_ORIGINAL_PUBLIC_SOURCE"
    assert source["raw_data_committed"] is False


def test_exact_per_alloy_rows_conditions_and_classes() -> None:
    frame = population()
    observed = frame.groupby("material").agg(rows=("bundle_id", "size"), conditions=("condition_id", "nunique"), keyhole=("has_keyhole", "sum"))
    assert observed.loc["Ti64"].to_dict() == {"rows": 60, "conditions": 38, "keyhole": 34}
    assert observed.loc["316L"].to_dict() == {"rows": 60, "conditions": 38, "keyhole": 23}
    assert int((frame.material.eq("Ti64") & frame.has_keyhole.eq(0)).sum()) == 26
    assert int((frame.material.eq("316L") & frame.has_keyhole.eq(0)).sum()) == 37


def test_radius_units_speed_conversion_and_h_formula() -> None:
    frame = population()
    assert p10.SPOT_DIAMETER_UM == 50.0
    assert p10.LS_M == 25e-6
    assert frame.LS_m.nunique() == 1
    assert np.allclose(frame.VX_m_per_s, frame.VX_mm_per_s / 1000)
    assert np.allclose(frame.h_SI, frame.P_W / np.sqrt(frame.VX_m_per_s * frame.LS_m**3))
    assert np.allclose(frame.log_h, np.log(frame.h_SI))


def test_model_predictor_contracts_exclude_optical_and_internal_boundary_features() -> None:
    frame = population()
    assert np.array_equal(p10.model_features(frame, "H"), frame[["log_h"]].to_numpy())
    expected_generic = frame[["log_P", "log_VX"]].to_numpy()
    assert np.array_equal(p10.model_features(frame, "G"), expected_generic)
    assert np.array_equal(p10.model_features(frame, "GPC"), expected_generic)
    source = inspect.getsource(p10.model_features)
    assert "-0.5" not in source and "h_SI" not in source.split('if model in {"G", "GPC"}:')[1]
    forbidden = {"optical", "B1", "q20", "q30", "material", "has_keyhole"}
    assert forbidden.isdisjoint({"log_h", "log_P", "log_VX"})


def test_condition_grouping_and_fold_class_validity() -> None:
    folds = pd.read_csv(p10.OUTPUT / "grouped_fold_manifest.csv")
    assert len(folds) == 2 * 20 * 60
    assert folds.repeat.nunique() == p10.N_REPEATS == 20
    assert folds.groupby(["material", "repeat", "condition_id"]).fold.nunique().max() == 1
    per_fold = folds.groupby(["material", "repeat", "fold"]).has_keyhole.agg(["min", "max"])
    assert (per_fold["min"] == 0).all() and (per_fold["max"] == 1).all()


def test_complete_pooled_oof_predictions_and_alloy_separation() -> None:
    frames = [pd.read_csv(p10.OUTPUT / "ti64_oof_predictions.csv.gz"), pd.read_csv(p10.OUTPUT / "ss316_oof_predictions.csv.gz")]
    predictions = pd.concat(frames, ignore_index=True)
    assert len(predictions) == 2 * 20 * 60 * 3
    assert predictions.groupby(["material", "repeat", "model", "bundle_id"]).size().eq(1).all()
    assert predictions.groupby(["material", "repeat", "model"]).size().eq(60).all()
    assert predictions.groupby(["material", "repeat", "model"]).truth.nunique().eq(2).all()
    assert set(frames[0].material) == {"Ti64"} and set(frames[1].material) == {"316L"}


def test_repeat_level_paired_inference_and_primary_endpoint() -> None:
    contrast = pd.read_csv(p10.OUTPUT / "ti64_paired_contrasts.csv")
    metrics = pd.read_csv(p10.OUTPUT / "ti64_repeat_metrics.csv")
    assert metrics.groupby("model").repeat.nunique().eq(20).all()
    assert contrast.repeat_blocks.eq(20).all()
    assert contrast.bootstrap_draws.ge(5000).all()
    primary = contrast[contrast.metric.eq("roc_auc")].iloc[0]
    assert primary.mean_difference < 0 and primary.ci_upper < 0
    assert p10.scientific_verdict(
        pd.concat([pd.read_csv(p10.OUTPUT / "ti64_model_summary.csv"), pd.read_csv(p10.OUTPUT / "ss316_model_summary.csv")]),
        pd.concat([contrast, pd.read_csv(p10.OUTPUT / "ss316_paired_contrasts.csv")]),
    ) == "GENERIC_DIRECTION_SUPERIOR"


def test_discordant_conditions_and_predeclared_sensitivities() -> None:
    frame = population()
    ti_discordant = frame[frame.material.eq("Ti64")].groupby("condition_id").has_keyhole.nunique()
    ss_discordant = frame[frame.material.eq("316L")].groupby("condition_id").has_keyhole.nunique()
    assert int((ti_discordant > 1).sum()) == 2
    assert int((ss_discordant > 1).sum()) == 0
    sensitivity = pd.read_csv(p10.OUTPUT / "condition_level_sensitivity.csv")
    a = sensitivity[sensitivity.sensitivity.eq("A_exclude_discordant")].drop(columns="sensitivity").reset_index(drop=True)
    b = sensitivity[sensitivity.sensitivity.eq("B_strict_majority")].drop(columns="sensitivity").reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b)
    assert set(sensitivity[sensitivity.material.eq("Ti64")].condition_rows) == {36}


def test_pca_is_label_free_descriptive_and_not_a_predictor() -> None:
    loadings = pd.read_csv(p10.OUTPUT / "pca_loadings.csv")
    scores = pd.read_csv(p10.OUTPUT / "pca_scores.csv")
    assert not loadings.labels_used_in_fit.astype(bool).any()
    assert set(loadings.fit_features) == {"log_P|log_VX"}
    ratios = loadings.drop_duplicates(["material", "component"]).groupby("material").explained_variance_ratio.sum()
    assert np.allclose(ratios, 1.0)
    assert len(scores) == 120
    assert "PC1" not in {"log_h", "log_P", "log_VX"}


def test_notebook_executed_figures_and_manifest_hashes() -> None:
    notebook = nbf.read(p10.NOTEBOOK, as_version=4)
    code = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert code and all(cell.execution_count is not None for cell in code)
    assert not [output for cell in code for output in cell.get("outputs", []) if output.get("output_type") == "error"]
    figures = pd.read_csv(p10.OUTPUT / "figure_manifest.csv")
    assert len(figures) == 4
    assert all(p10.sha256_file(p10.FIGURES / row.figure) == row.sha256 for row in figures.itertuples(index=False))
    manifest = json.loads((p10.OUTPUT / "run_manifest.json").read_text(encoding="utf-8"))
    validation = json.loads((p10.OUTPUT / "validation_report.json").read_text(encoding="utf-8"))
    assert manifest["validation"] == validation
    assert validation["status"] == "PASS" and validation["check_count"] == 30
    for row in manifest["files"]:
        path = p10.ROOT / row["path"]
        assert path.is_file() and p10.sha256_file(path) == row["sha256"]


def test_no_external_raw_data_or_historical_phase1x_change_and_claim_safety() -> None:
    assert subprocess.check_output(["git", "ls-files", ".cache"], cwd=p10.ROOT, text=True).strip() == ""
    assert not list(p10.ROOT.rglob("Neuchatel data.zip"))
    assert p10.historical_phase1x_changes() == []
    ledger = (p10.OUTPUT / "claim_ledger.md").read_text(encoding="utf-8")
    report = (p10.OUTPUT / "FINAL_PHASE1_10_REPORT.md").read_text(encoding="utf-8")
    assert "LS^-3/2` exponent. | NOT TESTABLE" in ledger
    assert "Cross-material transfer is demonstrated. | NOT TESTED" in ledger
    assert "External active-learning improvement is demonstrated. | NOT TESTED" in ledger
    assert "GENERIC_DIRECTION_SUPERIOR" in report
    assert "not intervals from 20 independent experimental datasets" in report
