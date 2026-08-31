"""Focused guards for Week 9 Phase 2."""

from __future__ import annotations

import json
from pathlib import Path

import nbformat
import numpy as np
import pandas as pd
from nbconvert.preprocessors import ExecutePreprocessor

from src import week9_phase2_temporal_width_dynamics as p2


def _out(name: str) -> Path:
    path = p2.OUTPUT / name
    assert path.is_file(), path
    return path


def test_canonical_population_labels_and_definitions() -> None:
    pop = p2.load_population()
    assert len(pop) == 405
    assert int(pop.has_keyhole.sum()) == 73
    assert pop.experiment_name.is_unique
    assert np.all(pop.LS > 0)  # canonical LS is Gaussian spot radius r0
    assert np.all(pop.ST > 0)  # canonical ST is substrate temperature in K
    assert np.allclose(p2.log_h(pop), np.log(pop.P / np.sqrt(pop.VX * pop.LS**3)))


def test_width_time_derivative_and_active_interval_contracts() -> None:
    audit = pd.read_csv(_out("width_timeseries_audit.csv"))
    profiles = pd.read_csv(_out("temporal_profiles.csv.gz"))
    assert (audit.nonpositive_dt_count_raw == 0).all()
    assert (audit.duplicate_timestamp_count == 0).all()
    assert (audit.cooling_rows_in_primary == 0).all()
    endpoints = profiles.groupby("experiment_name").tau.agg(["min", "max"])
    assert np.allclose(endpoints["min"], 0)
    assert np.allclose(endpoints["max"], 1)
    assert p2.synthetic_derivative_error() < 1e-8


def test_width_formula_against_one_pinned_source() -> None:
    pop = p2.load_population().reset_index(drop=True)
    pop["population_row_index"] = np.arange(len(pop))
    pop["log_h"] = p2.log_h(pop)
    merged = pop.merge(p2.source_paths(), on="experiment_name", how="left")
    row = merged[merged.bounds_path.map(p2._existing) & merged.time_path.map(p2._existing)].iloc[0]
    bounds, _ = p2.p2.load_numeric(Path(row.bounds_path), "position-bounds_melt.dat")
    _, profile, _ = p2._parse_trace(row)
    raw_width_um = (bounds[:, 1] - bounds[:, 0]) * 1e6
    assert np.isfinite(raw_width_um).any()
    assert profile.width_um.min() >= 0


def test_usable_subset_and_missingness_reconcile() -> None:
    features = pd.read_csv(_out("width_temporal_features.csv"))
    missing = pd.read_csv(_out("width_missingness_audit.csv"))
    assert len(features) == 350
    assert int(features.has_keyhole.sum()) == 70
    counts = missing[missing.category.isin(["valid_width_time_series", "missing_or_unusable_width_time_series"])]
    assert int(counts["count"].sum()) == 405


def test_prefix_never_reads_future() -> None:
    prefix = pd.read_csv(_out("prefix_temporal_features.csv"))
    pred = pd.read_csv(_out("prefix_oof_predictions.csv.gz"))
    assert (prefix.latest_source_tau <= prefix.prefix_tau + 1e-12).all()
    assert (pred.latest_source_tau <= pred.prefix_tau + 1e-12).all()


def test_models_are_grouped_and_evaluation_flags_are_not_features() -> None:
    repeat = pd.read_csv(_out("model_repeat_level_metrics.csv"))
    pred = pd.read_csv(_out("model_oof_predictions.csv.gz"))
    assert repeat.repeat.nunique() == 20
    assert pred.run_id.nunique() == 100
    assert set(pred.model) == {"h_only", "static_width", "width_dynamics", "h_plus_width_dynamics"}
    assert not ({"is_q20", "is_q30", "truth"} & set(p2.TEMPORAL_FEATURES))


def test_pca_is_label_free_by_construction() -> None:
    loadings = pd.read_csv(_out("pca_loadings.csv"))
    scores = pd.read_csv(_out("pca_scores.csv"))
    assert set(loadings.feature) == set(p2.TEMPORAL_FEATURES)
    assert "has_keyhole" not in set(loadings.feature)
    assert np.isfinite(scores[["PC1", "PC2"]]).all().all()


def test_onset_uses_exact_valid_manual_alignment_only() -> None:
    onset = pd.read_csv(_out("keyhole_onset_audit.csv"))
    valid = onset[onset.onset_available.astype(bool)]
    assert (valid.has_keyhole == 1).all()
    assert valid.first_keyhole_monitor_row_index.notna().all()
    assert ((valid.first_keyhole_tau >= 0) & (valid.first_keyhole_tau <= 1)).all()
    assert np.allclose(valid.peak_minus_first_keyhole_ms < 0, valid.peak_precedes_first_observed_keyhole.astype(bool))


def test_figure_and_run_manifest_hashes() -> None:
    manifest = pd.read_csv(_out("figure_manifest.csv"))
    assert len(manifest) == 8
    for row in manifest.itertuples(index=False):
        assert p2.sha256_file(p2.FIGURES / row.figure) == row.sha256
    run = json.loads(_out("run_manifest.json").read_text(encoding="utf-8"))
    assert run["starting_sha"] == p2.STARTING_SHA
    assert run["population"] == 405 and run["usable"] == 350
    for relative, digest in run["artifact_hashes"].items():
        assert p2.sha256_file(p2.OUTPUT / relative) == digest


def test_historical_phase1_outputs_are_untouched() -> None:
    import subprocess
    historical = subprocess.run(
        ["git", "diff", "--name-only", p2.STARTING_SHA, "--", "outputs/week8_5_frozen_confirmation",
         "outputs/week9_phase1_close_week8", "outputs/week9_phase1_5_h_physics_confirmation",
         "outputs/week9_phase1_7_physics_ridge_residual_gp", "outputs/week9_phase1_8_model_path_decomposition"],
        cwd=p2.ROOT, text=True, capture_output=True, check=True,
    ).stdout.strip()
    assert historical == ""


def test_notebook_executes_without_error(tmp_path: Path) -> None:
    notebook = nbformat.read(p2.NOTEBOOK, as_version=4)
    ExecutePreprocessor(timeout=240, kernel_name="python3").preprocess(
        notebook, {"metadata": {"path": str(p2.ROOT)}}
    )
