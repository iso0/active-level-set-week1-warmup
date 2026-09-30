from __future__ import annotations

import json

import pytest

import src.week11_new_data_arrival_audit as week11

from src.week11_new_data_arrival_audit import (
    compare_trees,
    normalized_path,
    parse_experiment_folder,
    structural_b80_advisory,
    structural_b80_witnesses,
    validate_parameter_bytes,
)


NAME = (
    "P-449p849097257_VX-0p339655264522_LS-4p59307144915e-05_"
    "ST-426p907541557_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_"
    "TE-0p0021_DT-1p42029908172e-05_H-0d4cb30208"
)


def row(path: str, oid: str | None) -> dict[str, object]:
    return {"path": path, "type": "file", "size": 1, "oid": oid}


def test_path_normalization_rejects_traversal_and_absolute_paths() -> None:
    assert normalized_path("a\\parameters.json") == "a/parameters.json"
    for value in ("../labels.csv", "/labels.csv", "a/../labels.csv", ""):
        with pytest.raises(ValueError):
            normalized_path(value)


def test_tree_comparison_keeps_change_classes_and_ambiguous_duplicates_separate() -> None:
    old = [row("same", "1"), row("changed", "2"), row("gone", "3"), row("rename-old", "4"), row("unknown", None)]
    new = [row("same", "1"), row("changed", "9"), row("new", "5"), row("rename-new", "4"), row("unknown", None), row("dup-a", "d"), row("dup-b", "d")]
    report = compare_trees(old, new)
    assert report["unchanged"] == ["same"]
    assert report["modified"] == ["changed"]
    assert report["unknown_content_change"] == ["unknown"]
    assert report["renamed"] == [{"from": "rename-old", "to": "rename-new", "identity": "oid:4"}]
    assert {"identity": "oid:d", "paths": ["new:dup-a", "new:dup-b"]} in report["exact_content_duplicate_groups"]


def test_folder_parser_preserves_tokens_as_provenance() -> None:
    parsed = parse_experiment_folder(NAME)
    assert parsed["material"] == "TI64"
    assert parsed["folder_hash"] == "0d4cb30208"
    assert parsed["folder_P"] == pytest.approx(449.849097257)


def parameter_bytes(extra: bool = False) -> bytes:
    payload = {
        "laser_power": {"value": 449.849097257, "unit": "W"},
        "scan_speed_x": {"value": 0.339655264522, "unit": "m/s"},
        "laser_spot_size": {"value": 4.59307144915e-05, "unit": "m"},
        "substrate_temperature": {"value": 426.907541557, "unit": "K"},
    }
    if extra:
        payload["target"] = {"value": 1, "unit": "label"}
    return json.dumps(payload).encode()


def test_parameter_projection_accepts_only_four_input_keys_and_canonical_units() -> None:
    projected = validate_parameter_bytes(parameter_bytes(), NAME)
    assert projected["P"] == pytest.approx(449.849097257)
    assert projected["P_unit"] == "W"
    assert projected["folder_precision_mismatches"] == []
    with pytest.raises(ValueError, match="top-level keys"):
        validate_parameter_bytes(parameter_bytes(extra=True), NAME)


def test_parameter_projection_reports_precision_mismatch_without_excluding() -> None:
    payload = json.loads(parameter_bytes())
    payload["laser_power"]["value"] = 450.0
    projected = validate_parameter_bytes(json.dumps(payload).encode(), NAME)
    assert projected["folder_precision_mismatches"] == ["P"]


def test_parameter_projection_rejects_wrong_unit_and_nested_extra_key() -> None:
    payload = json.loads(parameter_bytes())
    payload["laser_power"]["unit"] = "kW"
    with pytest.raises(ValueError, match="value or unit"):
        validate_parameter_bytes(json.dumps(payload).encode(), NAME)
    payload = json.loads(parameter_bytes())
    payload["laser_power"]["note"] = "unexpected"
    with pytest.raises(ValueError, match="nested schema"):
        validate_parameter_bytes(json.dumps(payload).encode(), NAME)


def test_structural_b80_witness_is_advisory_and_bug_unknown() -> None:
    groups = [f"g{i:03d}" for i in range(100)]
    report = structural_b80_advisory(groups, {group: i % 5 for i, group in enumerate(groups)})
    assert report["structural_b80_feasible"] is True
    assert report["final_bug_eligibility"] == "UNKNOWN"
    assert report["status"] == "ADVISORY_ONLY"


def test_structural_witness_rejects_incomplete_certificate() -> None:
    with pytest.raises(ValueError, match="cover"):
        structural_b80_advisory(["a", "b"], {"a": 0})


def test_two_structural_witnesses_are_distinct_balanced_and_advisory() -> None:
    groups = [f"g{i:03d}" for i in range(185)]
    witnesses = structural_b80_witnesses(groups)
    assert [witness["seed"] for witness in witnesses] == [1101, 1102]
    assert len({witness["assignment_sha256"] for witness in witnesses}) == 2
    assert all(set(witness["training_group_counts"].values()) == {148} for witness in witnesses)
    assert all(witness["status"] == "ADVISORY_NOT_APPROVED" for witness in witnesses)


def test_checked_artifacts_remain_label_blind_and_blocked() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "outputs" / "week11_new_data_arrival_audit"
    if not root.exists():
        pytest.skip("pinned metadata artifacts have not been collected")
    parameters = json.loads((root / "new_input_parameters.json").read_text())
    intake = json.loads((root / "prepared_intake_report.json").read_text())
    overlap = json.loads((root / "label_blind_overlap_summary.json").read_text())
    identity = json.loads((root / "metadata_content_identity_review.json").read_text())
    assert len(parameters) == 185
    assert len({row["config_token"] for row in parameters}) == 185
    assert all(not row["folder_precision_mismatches"] for row in parameters)
    assert len(intake["technically_usable_rows"]) == 185
    assert intake["technical_exclusion_candidates"] == []
    assert intake["blockers"] == [
        "INDEPENDENCE_OR_PROVENANCE_UNRESOLVED",
        "ONE_CUSTODIAN_ORACLE_DIGEST_REQUIRED",
    ]
    assert overlap["simulation_id_overlap_count"] == 0
    assert overlap["exact_input_overlap_count"] == 0
    assert identity["historical_archive_identity_comparison_status"].startswith("UNRESOLVED")
    assert (root / "WEEK11_NEW_BATCH_MANIFEST.csv").read_bytes() == (root / "new185_input_manifest_candidate.csv").read_bytes()
    sidecar = (root / "prepared_intake_report.json.sha256").read_text().strip()
    import hashlib
    assert hashlib.sha256((root / "prepared_intake_report.json").read_bytes()).hexdigest() == sidecar
    witnesses = json.loads((root / "structural_b80_witnesses.json").read_text())
    assert [item["assignment_sha256"] for item in witnesses] == [
        "ba697cacc393c10a68b7c9581f06c2d603eaaec265326026a145cb2df436c825",
        "4f4d5faa9b064300abb6a16d3d2506cfe795da697f5b8b7226ffc856f8b98eb8",
    ]


def test_collection_fetches_only_tree_metadata_and_approved_parameter_payload(monkeypatch) -> None:
    tree_calls = []
    payload_calls = []
    parameter_path = f"{NAME}/parameters.json"
    immediate = [
        {"path": parameter_path, "type": "file", "size": 298, "oid": "parameter-oid"},
        {"path": f"{NAME}/frames.csv", "type": "file", "size": 10, "oid": "blocked-oid"},
        {"path": f"{NAME}/monitor", "type": "directory", "size": 0, "oid": "monitor-oid"},
    ]
    monkeypatch.setattr(week11, "_tree", lambda revision, path=None: tree_calls.append((revision, path)) or (immediate if path == NAME else []))
    monkeypatch.setattr(week11, "_read_url", lambda url: payload_calls.append(url) or parameter_bytes())
    result = week11._collect_one(NAME)
    assert result["parameter"]["source_blob_oid"] == "parameter-oid"
    assert tree_calls == [(week11.NEW_REVISION, NAME), (week11.NEW_REVISION, f"{NAME}/monitor")]
    assert len(payload_calls) == 1 and payload_calls[0].endswith(f"/{parameter_path}")
    assert "frames.csv" not in payload_calls[0] and "/monitor/" not in payload_calls[0]
