import json
from pathlib import Path

import nbformat
import numpy as np
import pandas as pd

from src import week9_phase1_19a_integrity_posterior_monotonicity_audit as audit


OUT = audit.OUTPUT


def test_frozen_population_and_paths():
    population, specs, paths = audit.load_frozen()
    assert (len(population), int(population.has_keyhole.sum())) == (405, 73)
    assert len(specs) == len(paths) == 100
    assert all(len(path) == len(set(path)) == 80 for path in paths.values())


def test_configuration_counts_and_verified_domain_mapping():
    population, _, _ = audit.load_frozen()
    table, summary, _, _ = audit.configuration_audit(population)
    counts = dict(zip(summary.configuration_group, summary.N))
    assert counts == {"CFG_MAIN": 364, "CFG_NEGATIVE_XI_SHORT": 27, "CFG_POSITIVE_XI_SHORT": 14}
    assert table.domain_mapping_absolute_error_m.max() < 1e-12
    assert int(table.TE_vs_time_dat_flag_mismatch.sum()) == 1


def test_label_free_depth_pile():
    population, _, _ = audit.load_frozen()
    table, _, _, _ = audit.configuration_audit(population)
    censor, summary, threshold = audit.depth_censoring_audit(population, table)
    likely = summary[summary.depth_censoring_class.eq("likely_domain_floor_censored")]
    assert (int(likely.N.sum()), int(likely.keyholes.sum())) == (39, 39)
    assert 287.6517 < threshold < 300.7084
    assert censor.rule.str.contains("labels unused").all()


def test_primary_monotonicity_definition_on_toy_data():
    toy = pd.DataFrame({
        "P": [100.0, 110.0, 90.0],
        "VX": [1.0, 0.9, 0.8],
        "LS": [60e-6, 55e-6, 70e-6],
    })
    dom = audit.dominance_matrix(toy, np.arange(3))
    assert dom[0, 1]
    assert not dom[1, 0]
    assert not dom[0, 2]
    assert not np.diag(dom).any()


def test_exact_pair_counts_and_all_violations_listed():
    pair = pd.read_csv(OUT / "monotonicity_pair_summary.csv").iloc[0]
    main = pd.read_csv(OUT / "monotonicity_main_config_summary.csv").iloc[0]
    violations = pd.read_csv(OUT / "monotonicity_violations.csv")
    assert (int(pair.comparable_directed_pairs), int(pair.comparable_unique_unordered_pairs), int(pair.violations)) == (22050, 22050, 3)
    assert (int(main.comparable_directed_pairs), int(main.violations)) == (19491, 3)
    assert len(violations) == 6 and violations.violation_id.nunique() == 3


def test_stage1_information_flow_and_diagnostic_only_regularization():
    snapshots = pd.read_csv(OUT / "stage1_snapshot_diagnostics.csv.gz")
    regularization = pd.read_csv(OUT / "stage1_regularization_diagnostic.csv")
    assert len(snapshots) == 700
    assert snapshots.revealed_labels_only.all() and not snapshots.heldout_labels_used.any()
    assert set(regularization.C.unique()) == set(audit.REGULARIZATION_C)
    assert regularization.diagnostic_only.all()


def test_no_new_trajectory_or_prior_output_copy():
    names = [path.name.lower() for path in OUT.rglob("*") if path.is_file()]
    assert not any("trajectory" in name or "queries" in name for name in names)
    prior_names = {Path(value).name.lower() for value in audit.HISTORICAL_REFERENCES.values()}
    assert not prior_names.intersection(names)


def test_notebook_has_stored_outputs():
    notebook = nbformat.read(audit.NOTEBOOK, as_version=4)
    code = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert code and all(cell.execution_count is not None and cell.outputs for cell in code)


def test_figure_and_manifest_hashes():
    figures = pd.read_csv(OUT / "figure_manifest.csv")
    assert len(figures) == 6
    assert all(audit.sha256_file(audit.FIGURES / row.figure) == row.sha256 for _, row in figures.iterrows())
    manifest = json.loads((OUT / "run_manifest.json").read_text(encoding="utf-8"))
    for item in manifest["artifacts"]:
        path = audit.ROOT / item["path"]
        assert path.exists() and audit.sha256_file(path) == item["sha256"]


def test_validation_snapshot_passes():
    validation = json.loads((OUT / "validation_report.json").read_text(encoding="utf-8"))
    manifest = json.loads((OUT / "run_manifest.json").read_text(encoding="utf-8"))
    assert validation["status"] == "PASS"
    assert validation == manifest["validation"]
    assert validation["check_count"] == len(validation["checks"])


def test_historical_outputs_unchanged_and_parent_exact():
    assert audit.git("merge-base", "HEAD", audit.PARENT_SHA) == audit.PARENT_SHA
    changed = audit.git("diff", "--name-only", audit.PARENT_SHA, "--", "outputs").splitlines()
    assert all(path.startswith("outputs/week9_phase1_19a_integrity_posterior_monotonicity_audit/") for path in changed)
