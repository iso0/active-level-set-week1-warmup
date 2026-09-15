import inspect
import json
from pathlib import Path

import nbformat
import numpy as np
import pandas as pd

from src import week9_phase1_19b_prospective_robust_monotone_pool_lse as phase


OUT = phase.OUTPUT


def test_population_and_phase19a_gate():
    population, _ = phase.load_population()
    assert (len(population), int(population.has_keyhole.sum())) == (405, 73)
    gate = json.loads((OUT / "baseline_gate.json").read_text())
    values = {(row["population"], row["directed_pairs"], row["violations"]) for row in gate["independent_reproduction"]}
    assert values == {("full_405", 22050, 3), ("main_364", 19491, 3)}


def test_dominance_direction_on_toy_poset():
    toy = pd.DataFrame({"P": [100, 110, 95], "VX": [1.0, .9, .8], "LS": [60e-6, 55e-6, 70e-6]})
    dom = phase.dominance_matrix(toy, np.arange(3))
    assert dom[0, 1] and not dom[1, 0]
    assert not dom[0, 2] and not np.diag(dom).any()


def test_conflict_rule():
    queried = np.array([False, False, False])
    kh = np.array([0, 1, 1])
    conduction = np.array([0, 0, 1])
    status = phase.status_from_evidence(queried, kh, conduction)
    assert status.tolist() == ["unresolved", "inferred_KH", "conflicted"]
    queried[1] = True
    assert phase.status_from_evidence(queried, kh, conduction)[1] == "queried"


def test_gkh_gc_on_chain():
    # 0 < 1 < 2: KH at candidate 0 implies 1 and 2; C at candidate 2 implies 0 and 1.
    dom = np.array([[False, True, True], [False, False, True], [False, False, False]])
    status = np.array(["unresolved"] * 3, dtype=object)
    gkh, gc = phase.gains_for_candidates(dom, status, np.arange(3))
    assert gkh.tolist() == [2, 1, 0]
    assert gc.tolist() == [0, 1, 2]


def test_frozen_acquisition_formulas_and_ties():
    candidates = np.array([9, 4, 7])
    p = np.array([.5, .5, .7])
    gkh = np.array([1, 1, 5])
    gc = np.array([1, 1, 0])
    chosen, _ = phase.select_candidate(phase.ARMS[0], candidates, p, gkh, gc)
    assert chosen == 4  # equal margin, smallest canonical row
    chosen, _ = phase.select_candidate(phase.ARMS[2], candidates, p, gkh, gc)
    assert chosen == 4  # equal worst-case and uncertainty, smallest row
    chosen, info = phase.select_candidate(phase.ARMS[3], candidates, p, gkh, gc)
    expected = p * gkh + (1 - p) * gc
    norm = (expected - expected.min()) / (expected.max() - expected.min())
    score = (1 - 2 * np.abs(p - .5)) * (1 + norm)
    assert chosen == int(candidates[np.lexsort((candidates, -score))[0]])
    assert info["acquisition_score"] == score[np.flatnonzero(candidates == chosen)[0]]


def test_acquisition_signature_has_no_labels_or_q_fields():
    parameters = set(inspect.signature(phase.select_candidate).parameters)
    assert not parameters.intersection({"labels", "truth", "q20", "q30", "B1"})


def test_initial_designs_shared_and_feature_only():
    spec = pd.read_csv(OUT / "run_specification.csv")
    assert spec.groupby(["population", "repeat"]).initial_design.nunique().eq(1).all()
    assert spec.feature_only.all() and spec.initial_design_N.eq(16).all()


def test_complete_trajectory_and_information_flow():
    paths = pd.read_csv(OUT / "trajectory_summary.csv.gz")
    diagnostics = pd.read_csv(OUT / "acquisition_diagnostics.csv.gz")
    metrics = pd.read_csv(OUT / "budget_metrics.csv.gz")
    assert paths.groupby(["population", "repeat", "arm"]).ngroups == 160
    assert paths.groupby(["population", "repeat", "arm"]).apply(
        lambda part: part.population_row_index.is_unique, include_groups=False
    ).all()
    assert paths.groupby(["population", "repeat", "arm"]).query_order.min().eq(1).all()
    assert not diagnostics.unrevealed_labels_available_to_acquisition.any()
    assert not diagnostics.q20_q30_B1_available_to_acquisition.any()
    assert not diagnostics.inferred_labels_used_for_m3_training.any()
    assert phase.full_metrics(metrics).groupby(["population", "repeat", "arm"]).budget.nunique().eq(105).all()


def test_B16_M3_fit_is_identical_across_arms():
    metrics = phase.full_metrics(pd.read_csv(OUT / "budget_metrics.csv.gz"))
    b16 = metrics[metrics.budget.eq(16)].pivot(
        index=["population", "repeat"], columns="arm", values="m3_brier_score"
    )
    assert b16.shape == (40, 4)
    assert np.array_equal(b16.max(axis=1).to_numpy(), b16.min(axis=1).to_numpy())


def test_P0_replays_standard_M3_margin_rule():
    diagnostics = pd.read_csv(OUT / "acquisition_diagnostics.csv.gz")
    p0 = diagnostics[diagnostics.arm.eq(phase.ARMS[0])]
    assert np.allclose(p0.acquisition_score, p0.uncertainty)
    assert p0[["G_KH", "G_C"]].eq(0).all().all()


def test_structural_safety_decision_respects_directional_class_cap():
    decision = json.loads((OUT / "structural_safety_decision.json").read_text())
    assert decision["P3_B120_mean_error_among_inferred"] <= 0.01
    assert decision["ci"][1] <= 0.01
    assert decision["KH_as_C_population_rate"] > 0.01
    assert decision["decision"] == "MONOTONE_PROPAGATION_TOO_RISKY"


def test_pretruth_freeze_and_retrospective_join():
    pre_path = OUT / "query_event_log_pretruth.csv.gz"
    pre = pd.read_csv(pre_path)
    assert not {"target_truth", "retrospective_target_truth", "inference_correct", "retrospective_inference_correct"}.intersection(pre.columns)
    recorded = (OUT / "query_event_log_pretruth.sha256").read_text().split()[0]
    assert phase.sha256_file(pre_path) == recorded
    post = pd.read_csv(OUT / "query_event_log_retrospective.csv.gz", nrows=10)
    assert {"retrospective_target_truth", "retrospective_inference_correct"}.issubset(post.columns)


def test_holm_and_main_sensitivity_are_frozen():
    contrasts = pd.read_csv(OUT / "paired_contrasts.csv")
    assert contrasts.groupby("population").size().eq(3).all()
    assert contrasts.holm_adjusted_p.between(0, 1).all()
    assert pd.read_csv(OUT / "main_configuration_sensitivity.csv").no_retuning.all()


def test_notebook_figures_manifest_and_validation():
    notebook = nbformat.read(phase.NOTEBOOK, as_version=4)
    assert all(cell.execution_count is not None and cell.outputs for cell in notebook.cells if cell.cell_type == "code")
    figures = pd.read_csv(OUT / "figure_manifest.csv")
    assert len(figures) == 7
    assert all(phase.sha256_file(phase.FIGURES / row.figure) == row.sha256 for _, row in figures.iterrows())
    validation = json.loads((OUT / "validation_report.json").read_text())
    manifest = json.loads((OUT / "run_manifest.json").read_text())
    assert validation["status"] == "PASS" and validation == manifest["validation"]
    for artifact in manifest["artifacts"]:
        path = phase.ROOT / artifact["path"]
        assert path.exists() and phase.sha256_file(path) == artifact["sha256"]


def test_no_historical_output_changes_or_checkpoint_cache():
    changed = phase.git("diff", "--name-only", phase.PARENT_SHA, "--", "outputs").splitlines()
    assert all(path.startswith("outputs/week9_phase1_19b_prospective_robust_monotone_pool_lse/") for path in changed)
    assert not phase.CHECKPOINTS.exists()
