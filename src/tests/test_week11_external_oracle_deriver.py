import csv
import hashlib
import io
import json
import stat
from pathlib import Path

import pytest

import src.week11_external_oracle_deriver as oracle


def _manifest_bytes():
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(oracle.MANIFEST_COLUMNS)
    for i in range(185):
        writer.writerow((f"sim-{i:03d}", f"config-{i:03d}", f"group-{i:03d}", 100 + i, 0.5, 5e-5, 300))
    return stream.getvalue().encode()


def _source_bytes():
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(oracle.SOURCE_COLUMNS)
    for i in range(185):
        # A token outside label_final and all technical status/parameter columns are irrelevant.
        writer.writerow((f"sim-{i:03d}", "", "hidden", "hidden", "hidden", "hidden",
                         "false", "true", i, "Keyhole", "other", "other"))
    writer.writerow(("sim-010", "", "hidden", "hidden", "hidden", "hidden",
                     "true", "false", 999, "other", "other", "Keyhole"))
    writer.writerow(("sim-010", "", "hidden", "hidden", "hidden", "hidden",
                     "false", "false", 1000, "other", "other", "Screenshot Bug"))
    writer.writerow(("sim-010", "", "hidden", "hidden", "hidden", "hidden",
                     "true", "true", 1001, "other", "other", "Conduction"))
    return stream.getvalue().encode()


def _derive(source, manifest):
    return oracle.derive_oracle_bytes(source, manifest, expected_size=len(source),
                                      expected_sha256=hashlib.sha256(source).hexdigest())


def test_exact_final_manual_token_rule_and_sorted_binary_schema():
    manifest, source = _manifest_bytes(), _source_bytes()
    payload = _derive(source, manifest)
    oracle.validate_oracle_bytes(payload, [f"sim-{i:03d}" for i in range(185)])
    rows = list(csv.DictReader(io.StringIO(payload.decode())))
    by_id = {row["sim_id"]: row["has_keyhole"] for row in rows}
    assert by_id["sim-000"] == "0"  # label_1 must not define the target.
    assert by_id["sim-010"] == "1"  # any exact label_final Keyhole does.
    assert [row["sim_id"] for row in rows] == sorted(by_id)


def test_identity_schema_and_membership_fail_with_sanitized_codes():
    manifest, source = _manifest_bytes(), _source_bytes()
    with pytest.raises(oracle.SanitizedFailure) as caught:
        oracle.derive_oracle_bytes(source, manifest, expected_size=len(source), expected_sha256="0" * 64)
    assert (caught.value.stage, caught.value.code) == ("source", "BYTE_IDENTITY_MISMATCH")
    bad_header = source.replace(b"label_final", b"other_final", 1)
    with pytest.raises(oracle.SanitizedFailure) as caught:
        _derive(bad_header, manifest)
    assert caught.value.code == "SCHEMA_MISMATCH"
    outside = source.replace(b"sim-000", b"outside", 1)
    with pytest.raises(oracle.SanitizedFailure) as caught:
        _derive(outside, manifest)
    assert caught.value.code == "MEMBERSHIP_INVALID"


def test_custody_exclusive_create_readback_receipt_and_read_only(tmp_path, monkeypatch):
    manifest, source = _manifest_bytes(), _source_bytes()
    manifest_path = tmp_path / "manifest.csv"; manifest_path.write_bytes(manifest)
    decisions = tmp_path / "decisions.json"; decisions.write_text("{}\n")
    sealed = tmp_path / "quarantine" / "oracle.csv"; receipt = tmp_path / "receipt.json"
    real = oracle.derive_oracle_bytes
    monkeypatch.setattr(oracle, "derive_oracle_bytes", lambda raw, man: real(
        raw, man, expected_size=len(source), expected_sha256=hashlib.sha256(source).hexdigest()))
    result = oracle.create_sealed_oracle(manifest_path=manifest_path, decisions_path=decisions,
        receipt_path=receipt, oracle_path=sealed, fetcher=lambda: source,
        expected_manifest_sha256=hashlib.sha256(manifest).hexdigest(),
        expected_decisions_sha256=hashlib.sha256(decisions.read_bytes()).hexdigest())
    assert result["status"] == "SEALED_READ_ONLY"
    assert result["values_disclosed_to_method_side"] is False
    assert result["sealed_oracle_inventory"]["sha256"] == hashlib.sha256(sealed.read_bytes()).hexdigest()
    assert not (sealed.stat().st_mode & stat.S_IWRITE)
    with pytest.raises(oracle.SanitizedFailure) as caught:
        oracle.create_sealed_oracle(manifest_path=manifest_path, decisions_path=decisions,
            receipt_path=receipt, oracle_path=sealed,
            fetcher=lambda: (_ for _ in ()).throw(AssertionError("fetch must not run")),
            expected_manifest_sha256=hashlib.sha256(manifest).hexdigest(),
            expected_decisions_sha256=hashlib.sha256(decisions.read_bytes()).hexdigest())
    assert caught.value.code == "EXCLUSIVE_CREATE_TARGET_EXISTS"


def test_decision_drift_stops_before_oracle_write(tmp_path, monkeypatch):
    manifest, source = _manifest_bytes(), _source_bytes()
    manifest_path = tmp_path / "manifest.csv"; manifest_path.write_bytes(manifest)
    decisions = tmp_path / "decisions.json"; decisions.write_text("{}\n")
    sealed = tmp_path / "oracle.csv"; receipt = tmp_path / "receipt.json"
    real = oracle.derive_oracle_bytes
    monkeypatch.setattr(oracle, "derive_oracle_bytes", lambda raw, man: real(
        raw, man, expected_size=len(source), expected_sha256=hashlib.sha256(source).hexdigest()))
    def drift():
        decisions.write_text('{"changed":true}\n')
        return source
    with pytest.raises(oracle.SanitizedFailure) as caught:
        oracle.create_sealed_oracle(manifest_path=manifest_path, decisions_path=decisions,
            receipt_path=receipt, oracle_path=sealed, fetcher=drift,
            expected_manifest_sha256=hashlib.sha256(manifest).hexdigest(),
            expected_decisions_sha256=hashlib.sha256(decisions.read_bytes()).hexdigest())
    assert caught.value.code == "PRELABEL_DECISIONS_DRIFT"
    assert not sealed.exists() and not receipt.exists()


def test_metadata_workflow_adds_only_custodial_inventory(tmp_path):
    authority_sha = hashlib.sha256(oracle.AUTHORITY_PATH.read_bytes()).hexdigest()
    deriver_sha = hashlib.sha256(Path(oracle.__file__).read_bytes()).hexdigest()
    receipt = {
        "status": "SEALED_READ_ONLY", "custody_mode": oracle.CUSTODY_MODE,
        "analyst_label_accessed": False, "values_disclosed_to_method_side": False,
        "source_annotations_processed_inside_blinded_deriver": True,
        "created_utc": "2026-10-02T00:00:00Z",
        "source": {"repository": oracle.REPO_ID, "revision": oracle.PINNED_REVISION,
                   "file_name": oracle.PINNED_FILE, "byte_size": oracle.PINNED_SIZE,
                   "sha256": oracle.PINNED_SHA256},
        "derivation": {"rule": oracle.AUTHORITY_RULE, "authority_path": "src/alse/data.py",
                       "authority_sha256": authority_sha,
                       "deriver_path": "src/week11_external_oracle_deriver.py",
                       "deriver_sha256": deriver_sha, "bug_filter_or_truncation_applied": False},
        "sealed_oracle_inventory": {"file_name": "oracle.csv", "byte_size": 123,
                                    "sha256": "a" * 64, "status": "ok"},
    }
    receipt_path = tmp_path / "receipt.json"; receipt_path.write_text(json.dumps(receipt))
    inventory = tmp_path / "inventory.csv"
    with inventory.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n"); writer.writerow(oracle.intake.INVENTORY_COLUMNS)
        writer.writerow(("input.json", "sim-000", "input", 10, "b" * 64, "ok"))
    paths = oracle.write_finalization_metadata(receipt_path=receipt_path,
        base_inventory_path=inventory, output_directory=tmp_path / "metadata")
    rows = list(csv.DictReader(paths["inventory"].open(encoding="utf-8", newline="")))
    assert rows[-1]["kind"] == "sealed_oracle" and rows[-1]["sha256"] == "a" * 64
    provenance = json.loads(paths["provenance"].read_text())
    assert provenance["simulator_version"] == oracle.SIMULATOR_VERSION_MARKER
    assert provenance["independence_evidence"] == (
        "The 185 simulations are genuinely new, independently generated simulations, "
        "not copies or reprocessed versions of the historical 405/407 population.")
    assert "explicitly accepts SIMULATOR_VERSION_NOT_SEPARATELY_DOCUMENTED" in provenance["source"]


def test_cli_failure_is_sanitized_without_traceback_or_paths(tmp_path, capsys):
    code = oracle.main(["derive", "--manifest", str(tmp_path / "missing-manifest"),
                        "--decisions", str(tmp_path / "missing-decisions"),
                        "--receipt", str(tmp_path / "receipt")])
    captured = capsys.readouterr()
    assert code == 2 and "Traceback" not in captured.err and str(tmp_path) not in captured.err
    assert json.loads(captured.err) == {"status": "FAILED", "stage": "internal", "code": "UNEXPECTED_FAILURE"}


def test_finalization_rejects_manifest_or_decision_drift_before_writes(tmp_path):
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps({"derivation": {
        "full_manifest_sha256": oracle.FROZEN_MANIFEST_SHA256,
        "prelabel_owner_decisions_sha256": oracle.FROZEN_OWNER_DECISIONS_SHA256}}))
    manifest = tmp_path / "manifest.csv"; manifest.write_text("drifted")
    decisions = tmp_path / "decisions.json"; decisions.write_text("drifted")
    output = tmp_path / "final"
    with pytest.raises(oracle.SanitizedFailure) as caught:
        oracle.finalize_prelabel_freeze(receipt_path=receipt, base_inventory_path=tmp_path / "unused",
            manifest_path=manifest, old407_path=tmp_path / "unused407", old405_path=tmp_path / "unused405",
            decisions_path=decisions, output_directory=output)
    assert caught.value.code == "PRELABEL_BINDING_DRIFT" and not output.exists()
