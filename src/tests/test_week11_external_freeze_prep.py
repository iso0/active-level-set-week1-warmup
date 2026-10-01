import csv
import json
from pathlib import Path

import pytest

from src.external_validation import freeze
from src.external_validation.common import encoded, sha
from src.week11_external_freeze_prep import MANIFEST_COLUMNS, WITHHELD_REASON, prepare


def _csv(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def _fixture(root: Path):
    ids = [f"sim-{i:03d}" for i in range(185)]
    manifest = root / "manifest.csv"
    rows = [{"sim_id": sim_id, "config_token": f"config-{i:03d}",
             "group_token": f"group-{i:03d}", "P": 100 + i, "VX": 0.5,
             "LS": 5e-5, "ST": 300} for i, sim_id in enumerate(ids)]
    _csv(manifest, MANIFEST_COLUMNS, rows)
    status = root / "status.csv"
    status_fields = ["simulation_id", "bug_affected", "any_bug_free_false",
                     "any_correctly_finished_false", "technical_usability_status"]
    status_rows = []
    for i, sim_id in enumerate(ids):
        keep = i < 136
        status_rows.append({"simulation_id": sim_id, "bug_affected": str(not keep),
                            "any_bug_free_false": str(not keep),
                            "any_correctly_finished_false": "False",
                            "technical_usability_status": "KEEP" if keep else "UNRESOLVED"})
    _csv(status, status_fields, status_rows)
    overlap = root / "overlap.json"
    overlap.write_text(json.dumps({"simulation_id_overlap_count": 0, "exact_input_overlap_count": 0}))
    directory = root / "directory.json"; monitor = root / "monitor.json"
    directory.write_text(json.dumps([item for sim_id in ids for item in
        ({"path": f"{sim_id}/parameters.json"}, {"path": f"{sim_id}/frames.csv"})]))
    monitor.write_text(json.dumps([item for sim_id in ids for item in
        ({"path": f"{sim_id}/monitor/iter.dat"}, {"path": f"{sim_id}/monitor/time.dat"})]))
    intake = root / "intake.json"
    report = {"stage": "LABEL_BLIND", "manifest": {"sha256": sha(manifest.read_bytes())},
              "blockers": ["INDEPENDENCE_OR_PROVENANCE_UNRESOLVED",
              "ONE_CUSTODIAN_ORACLE_DIGEST_REQUIRED"]}
    intake.write_bytes(encoded(report)); Path(str(intake) + ".sha256").write_text(sha(encoded(report)) + "\n")
    return manifest, status, overlap, directory, monitor, intake


def test_preparation_partitions_cohort_and_stops_without_seal(tmp_path):
    sources = _fixture(tmp_path); output = tmp_path / "output"
    result = prepare(manifest_path=sources[0], bug_status_path=sources[1], overlap_path=sources[2],
        directory_metadata_path=sources[3], monitor_metadata_path=sources[4],
        intake_path=sources[5], output_directory=output)
    assert result["status"] == "BLOCKED_AND_NOT_LABEL_AUTHORIZATION"
    assert (result["included_count"], result["withheld_count"]) == (136, 49)
    assert result["fold_train_counts"] == [[108, 109, 109, 109, 109]] * 20
    assert result["minimum_training_pool_size"] == 108
    assert result["cohort_scope"].startswith("All future external-validation claims")
    assert not (output / "EXTERNAL_BATCH_FREEZE.json").exists()
    assert not (output / "EXTERNAL_BATCH_FREEZE.sha256").exists()
    assert (output / "FREEZE_PREPARATION.sha256").read_text().strip() == sha(
        (output / "FREEZE_PREPARATION.json").read_bytes())
    with (output / "WITHHELD_MANIFEST.csv").open(encoding="utf-8", newline="") as stream:
        withheld = list(csv.DictReader(stream))
    assert len(withheld) == 49 and {row["technical_reason"] for row in withheld} == {WITHHELD_REASON}
    assert (output / "FULL_DELIVERY_MANIFEST.csv").read_bytes() == sources[0].read_bytes()
    folds = json.loads((output / "PRELABEL_FOLD_ASSIGNMENTS.json").read_text())
    assert folds["seeds"] == list(range(1101, 1121))
    assert len({item["assignment_sha256"] for item in folds["assignments"]}) == 20
    decisions = json.loads((output / "PRELABEL_OWNER_DECISIONS.json").read_text())
    assert set(decisions) == freeze.DECISION_FIELDS
    assert decisions["owner"] == "Thesis protocol owner (user instructions dated 2026-10-01)"


def test_contrary_status_cannot_enter_included_cohort(tmp_path):
    sources = list(_fixture(tmp_path))
    with sources[1].open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream)); fields = stream.seek(0) or next(csv.reader(stream))
    rows[0]["any_bug_free_false"] = "True"
    _csv(sources[1], fields, rows)
    with pytest.raises(ValueError, match="contradicts"):
        prepare(manifest_path=sources[0], bug_status_path=sources[1], overlap_path=sources[2],
            directory_metadata_path=sources[3], monitor_metadata_path=sources[4],
            intake_path=sources[5], output_directory=tmp_path / "output")


def test_withheld_row_requires_explicit_bug_and_unresolved(tmp_path):
    sources = list(_fixture(tmp_path))
    with sources[1].open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream); fields = list(reader.fieldnames); rows = list(reader)
    rows[-1]["bug_affected"] = "False"
    _csv(sources[1], fields, rows)
    with pytest.raises(ValueError, match="withheld simulation"):
        prepare(manifest_path=sources[0], bug_status_path=sources[1], overlap_path=sources[2],
            directory_metadata_path=sources[3], monitor_metadata_path=sources[4],
            intake_path=sources[5], output_directory=tmp_path / "output")


def test_manifest_byte_drift_is_rejected_against_verified_intake(tmp_path):
    sources = list(_fixture(tmp_path))
    sources[0].write_bytes(sources[0].read_bytes() + b"\n")
    with pytest.raises(ValueError, match="verified intake manifest"):
        prepare(manifest_path=sources[0], bug_status_path=sources[1], overlap_path=sources[2],
            directory_metadata_path=sources[3], monitor_metadata_path=sources[4],
            intake_path=sources[5], output_directory=tmp_path / "output")


def test_duplicate_numeric_input_tuple_is_rejected(tmp_path):
    sources = list(_fixture(tmp_path))
    with sources[0].open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream); fields = list(reader.fieldnames); rows = list(reader)
    for key in ("P", "VX", "LS", "ST"): rows[1][key] = rows[0][key]
    _csv(sources[0], fields, rows)
    report = json.loads(sources[5].read_text()); report["manifest"]["sha256"] = sha(sources[0].read_bytes())
    sources[5].write_bytes(encoded(report)); Path(str(sources[5]) + ".sha256").write_text(sha(encoded(report)) + "\n")
    with pytest.raises(ValueError, match="numeric input tuples"):
        prepare(manifest_path=sources[0], bug_status_path=sources[1], overlap_path=sources[2],
            directory_metadata_path=sources[3], monitor_metadata_path=sources[4],
            intake_path=sources[5], output_directory=tmp_path / "output")
