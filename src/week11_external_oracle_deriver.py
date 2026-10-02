"""Owner-authorized blind custody derivation and metadata-only freeze finalization."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import stat
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from src.external_validation import freeze, intake

REPO_ID = "ioandanielc/sph_v2"
PINNED_REVISION = "2e1eec9c98fd57609d2815f174586336ab59da07"
PINNED_FILE = "labels_new_data_4_prep.csv"
PINNED_SIZE = 12_397_054
PINNED_SHA256 = "b45518a51ea59d97d1e28e3f2ce5ef563af1c049bce83d0d88b3d510b1adf16d"
FROZEN_MANIFEST_SHA256 = "46deec01b03b962202f2ad162a969db3fe300c27bf0fcbc98718a4b42606f910"
FROZEN_OWNER_DECISIONS_SHA256 = "8bff98620590f527751a2af68248d7bcbb0807ff3281ad2395a773c9ccd83be6"
SOURCE_COLUMNS = ("name", "hash", "P", "VX", "LS", "ST", "bug_free",
                  "correctly_finished", "timestep", "label_1", "label_2", "label_final")
MANIFEST_COLUMNS = ("sim_id", "config_token", "group_token", "P", "VX", "LS", "ST")
ORACLE_COLUMNS = ("sim_id", "has_keyhole")
AUTHORITY_PATH = Path(__file__).resolve().parent / "alse" / "data.py"
AUTHORITY_RULE = "has_keyhole = any(row.label_final == exact literal 'Keyhole') for the simulation"
SIMULATOR_VERSION_MARKER = "SIMULATOR_VERSION_NOT_SEPARATELY_DOCUMENTED"
CUSTODY_MODE = "OWNER_AUTHORIZED_AUTOMATED_CUSTODY"
QUARANTINE_ORACLE = (Path.home() / "Documents" / "thesis_external_quarantine" / "week11" /
                     PINNED_REVISION / "NEW185_SEALED_ORACLE.csv")


class SanitizedFailure(RuntimeError):
    """Failure whose stage/code are safe to report without source-row context."""
    def __init__(self, stage: str, code: str):
        self.stage, self.code = stage, code
        super().__init__(f"{stage}:{code}")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _manifest_ids(manifest_bytes: bytes) -> tuple[list[str], str]:
    try:
        reader = csv.DictReader(io.StringIO(manifest_bytes.decode("utf-8-sig"), newline=""))
        if tuple(reader.fieldnames or ()) != MANIFEST_COLUMNS:
            raise SanitizedFailure("manifest", "SCHEMA_MISMATCH")
        ids = [str(row["sim_id"]) for row in reader]
    except SanitizedFailure:
        raise
    except Exception as exc:
        raise SanitizedFailure("manifest", "PARSE_FAILURE") from exc
    if len(ids) != 185 or len(set(ids)) != 185 or any(not value for value in ids):
        raise SanitizedFailure("manifest", "MEMBERSHIP_INVALID")
    return sorted(ids), _sha(manifest_bytes)


def derive_oracle_bytes(raw: bytes, manifest_bytes: bytes, *, expected_size: int = PINNED_SIZE,
                        expected_sha256: str = PINNED_SHA256) -> bytes:
    """Return the sealed two-column oracle without exposing any individual value."""
    if len(raw) != expected_size or _sha(raw) != expected_sha256:
        raise SanitizedFailure("source", "BYTE_IDENTITY_MISMATCH")
    allowed, _ = _manifest_ids(manifest_bytes)
    allowed_set = set(allowed)
    flags = {sim_id: False for sim_id in allowed}
    seen: set[str] = set()
    try:
        reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
        header = next(reader)
        if tuple(header) != SOURCE_COLUMNS:
            raise SanitizedFailure("source", "SCHEMA_MISMATCH")
        name_index, final_index = header.index("name"), header.index("label_final")
        for row in reader:
            if len(row) != len(header):
                raise SanitizedFailure("source", "ROW_SHAPE_INVALID")
            sim_id = row[name_index]
            if sim_id not in allowed_set:
                raise SanitizedFailure("source", "MEMBERSHIP_INVALID")
            seen.add(sim_id)
            if row[final_index] == "Keyhole":
                flags[sim_id] = True
            # No other categorical or parameter value is interpreted, retained, enumerated or logged.
    except SanitizedFailure:
        raise
    except Exception as exc:
        raise SanitizedFailure("source", "PARSE_FAILURE") from exc
    if seen != allowed_set:
        raise SanitizedFailure("source", "MEMBERSHIP_INVALID")
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(ORACLE_COLUMNS)
    for sim_id in allowed:
        writer.writerow((sim_id, int(flags[sim_id])))
    return stream.getvalue().encode("utf-8")


def validate_oracle_bytes(payload: bytes, expected_ids: Sequence[str]) -> None:
    """Custody-internal validation; returns no label values or class summaries."""
    try:
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
        if tuple(reader.fieldnames or ()) != ORACLE_COLUMNS:
            raise SanitizedFailure("seal", "ORACLE_SCHEMA_INVALID")
        rows = list(reader)
    except SanitizedFailure:
        raise
    except Exception as exc:
        raise SanitizedFailure("seal", "ORACLE_PARSE_FAILURE") from exc
    ids = [row["sim_id"] for row in rows]
    if ids != sorted(expected_ids) or len(ids) != len(set(ids)):
        raise SanitizedFailure("seal", "ORACLE_MEMBERSHIP_INVALID")
    if any(row["has_keyhole"] not in {"0", "1"} for row in rows):
        raise SanitizedFailure("seal", "ORACLE_VALUE_INVALID")


def fetch_pinned_source() -> bytes:
    url = f"https://huggingface.co/datasets/{REPO_ID}/resolve/{PINNED_REVISION}/{urllib.parse.quote(PINNED_FILE)}"
    try:
        with urllib.request.urlopen(urllib.request.Request(
                url, headers={"User-Agent": "week11-blind-oracle-custody/1"}), timeout=180) as response:
            return response.read()
    except Exception as exc:
        raise SanitizedFailure("fetch", "PINNED_SOURCE_UNAVAILABLE") from exc


def create_sealed_oracle(*, manifest_path: Path, decisions_path: Path,
                         receipt_path: Path, oracle_path: Path = QUARANTINE_ORACLE,
                         fetcher: Callable[[], bytes] = fetch_pinned_source,
                         expected_manifest_sha256: str = FROZEN_MANIFEST_SHA256,
                         expected_decisions_sha256: str = FROZEN_OWNER_DECISIONS_SHA256) -> dict[str, Any]:
    """Create and validate the oracle entirely inside the automated custody boundary."""
    manifest_bytes = manifest_path.read_bytes()
    expected_ids, manifest_sha = _manifest_ids(manifest_bytes)
    decisions_before = _sha(decisions_path.read_bytes())
    if manifest_sha != expected_manifest_sha256:
        raise SanitizedFailure("custody", "FROZEN_MANIFEST_IDENTITY_MISMATCH")
    if decisions_before != expected_decisions_sha256:
        raise SanitizedFailure("custody", "FROZEN_OWNER_DECISIONS_IDENTITY_MISMATCH")
    # Refuse before network/source access when this custody target was already used.
    if oracle_path.exists() or receipt_path.exists():
        raise SanitizedFailure("custody", "EXCLUSIVE_CREATE_TARGET_EXISTS")
    raw = fetcher()
    oracle_bytes = derive_oracle_bytes(raw, manifest_bytes)
    del raw
    if _sha(decisions_path.read_bytes()) != decisions_before:
        raise SanitizedFailure("custody", "PRELABEL_DECISIONS_DRIFT")
    oracle_path.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with oracle_path.open("xb") as stream:
            created = True
            stream.write(oracle_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        # This is the custody process's sole read-back, before the payload is declared sealed.
        written = oracle_path.read_bytes()
        if written != oracle_bytes:
            raise SanitizedFailure("seal", "WRITE_VERIFICATION_FAILED")
        validate_oracle_bytes(written, expected_ids)
        oracle_sha, oracle_size = _sha(written), len(written)
        del written, oracle_bytes
        if _sha(decisions_path.read_bytes()) != decisions_before:
            raise SanitizedFailure("custody", "PRELABEL_DECISIONS_DRIFT")
        os.chmod(oracle_path, stat.S_IREAD)
        authority_sha = _sha(AUTHORITY_PATH.read_bytes())
        receipt = {
            "schema_version": 1, "status": "SEALED_READ_ONLY",
            "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "custody_mode": CUSTODY_MODE,
            "custody_authorization": "Protocol owner explicitly authorized automated oracle derivation in the current owner instruction.",
            "analyst_label_accessed": False, "values_disclosed_to_method_side": False,
            "source_annotations_processed_inside_blinded_deriver": True,
            "prior_bug_audit_exception": "The same pinned source was previously processed only through the approved sanitized Bug/status projection.",
            "source": {"repository": REPO_ID, "revision": PINNED_REVISION, "file_name": PINNED_FILE,
                       "byte_size": PINNED_SIZE, "sha256": PINNED_SHA256},
            "derivation": {"rule": AUTHORITY_RULE,
                           "authority_path": "src/alse/data.py", "authority_sha256": authority_sha,
                           "deriver_path": "src/week11_external_oracle_deriver.py",
                           "deriver_sha256": _sha(Path(__file__).read_bytes()),
                           "full_manifest_sha256": manifest_sha,
                           "prelabel_owner_decisions_sha256": decisions_before,
                           "bug_filter_or_truncation_applied": False},
            "sealed_oracle_inventory": {"file_name": oracle_path.name, "byte_size": oracle_size,
                                        "sha256": oracle_sha, "status": "ok"},
            "post_seal_policy": "Do not open or re-hash outside the locked external-validation gate.",
        }
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        with receipt_path.open("xb") as stream:
            stream.write(_json_bytes(receipt))
        return receipt
    except Exception:
        if created:
            try:
                os.chmod(oracle_path, stat.S_IWRITE | stat.S_IREAD)
                oracle_path.unlink(missing_ok=True)
            except Exception:
                pass
        raise


def write_finalization_metadata(*, receipt_path: Path, base_inventory_path: Path,
                                output_directory: Path) -> dict[str, Path]:
    """Create safe metadata inputs for fresh intake; never opens the sealed oracle."""
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    required = {"status", "custody_mode", "analyst_label_accessed", "values_disclosed_to_method_side",
                "source_annotations_processed_inside_blinded_deriver", "source", "derivation",
                "sealed_oracle_inventory", "created_utc"}
    if not required.issubset(receipt) or receipt["status"] != "SEALED_READ_ONLY" or \
            receipt["custody_mode"] != CUSTODY_MODE or receipt["analyst_label_accessed"] is not False or \
            receipt["values_disclosed_to_method_side"] is not False:
        raise SanitizedFailure("finalization", "CUSTODY_RECEIPT_INVALID")
    if receipt["source"] != {"repository": REPO_ID, "revision": PINNED_REVISION,
                              "file_name": PINNED_FILE, "byte_size": PINNED_SIZE,
                              "sha256": PINNED_SHA256}:
        raise SanitizedFailure("finalization", "SOURCE_BINDING_INVALID")
    derivation = receipt["derivation"]
    if (derivation.get("rule") != AUTHORITY_RULE or
            derivation.get("authority_path") != "src/alse/data.py" or
            derivation.get("authority_sha256") != _sha(AUTHORITY_PATH.read_bytes()) or
            derivation.get("deriver_path") != "src/week11_external_oracle_deriver.py" or
            derivation.get("deriver_sha256") != _sha(Path(__file__).read_bytes()) or
            derivation.get("bug_filter_or_truncation_applied") is not False):
        raise SanitizedFailure("finalization", "DERIVATION_BINDING_INVALID")
    oracle = receipt["sealed_oracle_inventory"]
    if (set(oracle) != {"file_name", "byte_size", "sha256", "status"} or oracle["status"] != "ok" or
            Path(str(oracle["file_name"])).name != oracle["file_name"] or
            not isinstance(oracle["byte_size"], int) or oracle["byte_size"] <= 0 or
            not isinstance(oracle["sha256"], str) or len(oracle["sha256"]) != 64 or
            any(char not in "0123456789abcdef" for char in oracle["sha256"])):
        raise SanitizedFailure("finalization", "ORACLE_INVENTORY_INVALID")
    with base_inventory_path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != intake.INVENTORY_COLUMNS:
            raise SanitizedFailure("finalization", "BASE_INVENTORY_SCHEMA_INVALID")
        rows = list(reader)
    if any(row["kind"] == "sealed_oracle" for row in rows):
        raise SanitizedFailure("finalization", "BASE_INVENTORY_ALREADY_HAS_ORACLE")
    rows.append({"file_name": oracle["file_name"], "sim_id": "", "kind": "sealed_oracle",
                 "byte_size": str(oracle["byte_size"]), "sha256": oracle["sha256"], "status": "ok"})
    output_directory.mkdir(parents=True, exist_ok=False)
    inventory_path = output_directory / "delivery_inventory.csv"
    with inventory_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=intake.INVENTORY_COLUMNS, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    provenance = {
        "source": (f"{REPO_ID}@{PINNED_REVISION}; thesis protocol owner explicitly accepts "
                   f"{SIMULATOR_VERSION_MARKER} under the current owner instruction."),
        "received_utc": receipt["created_utc"],
        "simulator_version": SIMULATOR_VERSION_MARKER,
        "independence_evidence": ("The 185 simulations are genuinely new, independently generated simulations, "
                                  "not copies or reprocessed versions of the historical 405/407 population."),
    }
    provenance_path = output_directory / "provenance.json"
    units_path = output_directory / "units.json"
    provenance_path.write_bytes(_json_bytes(provenance))
    units_path.write_bytes(_json_bytes(intake.CANONICAL_UNITS))
    receipt_copy = output_directory / "ORACLE_CUSTODY_RECEIPT.json"
    receipt_copy.write_bytes(_json_bytes(receipt))
    return {"inventory": inventory_path, "provenance": provenance_path,
            "units": units_path, "receipt": receipt_copy}


def finalize_prelabel_freeze(*, receipt_path: Path, base_inventory_path: Path,
                             manifest_path: Path, old407_path: Path, old405_path: Path,
                             decisions_path: Path, output_directory: Path) -> dict[str, Any]:
    """Run fresh intake and generate the final seal using receipt metadata only."""
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    manifest_sha = _sha(manifest_path.read_bytes())
    decisions_sha = _sha(decisions_path.read_bytes())
    derivation = receipt.get("derivation", {})
    if (manifest_sha != FROZEN_MANIFEST_SHA256 or decisions_sha != FROZEN_OWNER_DECISIONS_SHA256 or
            derivation.get("full_manifest_sha256") != manifest_sha or
            derivation.get("prelabel_owner_decisions_sha256") != decisions_sha):
        raise SanitizedFailure("finalization", "PRELABEL_BINDING_DRIFT")
    paths = write_finalization_metadata(receipt_path=receipt_path,
                                        base_inventory_path=base_inventory_path,
                                        output_directory=output_directory / "intake_inputs")
    intake_path = output_directory / "LABEL_BLIND_INTAKE.json"
    report = intake.intake(manifest_path, old407_path, old405_path, paths["inventory"], intake_path,
                           provenance=json.loads(paths["provenance"].read_text(encoding="utf-8")),
                           units=json.loads(paths["units"].read_text(encoding="utf-8")))
    if report.get("blockers"):
        raise SanitizedFailure("finalization", "FRESH_INTAKE_REMAINS_BLOCKED")
    decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
    if set(decisions) != freeze.DECISION_FIELDS:
        raise SanitizedFailure("finalization", "OWNER_DECISIONS_SCHEMA_INVALID")
    sealed = freeze.generate(intake_path, output_directory, decisions)
    return {"intake": report, "freeze": sealed}


def _safe_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    command = parser.add_subparsers(dest="command", required=True)
    derive = command.add_parser("derive")
    derive.add_argument("--manifest", required=True, type=Path)
    derive.add_argument("--decisions", required=True, type=Path)
    derive.add_argument("--receipt", required=True, type=Path)
    metadata = command.add_parser("metadata")
    metadata.add_argument("--receipt", required=True, type=Path)
    metadata.add_argument("--base-inventory", required=True, type=Path)
    metadata.add_argument("--output-directory", required=True, type=Path)
    finalize = command.add_parser("finalize")
    for name in ("receipt", "base-inventory", "manifest", "old407", "old405",
                 "decisions", "output-directory"):
        finalize.add_argument(f"--{name}", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.command == "derive":
        create_sealed_oracle(manifest_path=args.manifest, decisions_path=args.decisions,
                             receipt_path=args.receipt)
        print(json.dumps({"status": "SEALED", "receipt": str(args.receipt)}))
    elif args.command == "metadata":
        write_finalization_metadata(receipt_path=args.receipt,
                                    base_inventory_path=args.base_inventory,
                                    output_directory=args.output_directory)
        print(json.dumps({"status": "METADATA_READY", "output_directory": str(args.output_directory)}))
    else:
        finalize_prelabel_freeze(receipt_path=args.receipt, base_inventory_path=args.base_inventory,
            manifest_path=args.manifest, old407_path=args.old407, old405_path=args.old405,
            decisions_path=args.decisions, output_directory=args.output_directory)
        print(json.dumps({"status": "FINAL_SEAL_READY", "output_directory": str(args.output_directory)}))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return _safe_main(argv)
    except SanitizedFailure as exc:
        print(json.dumps({"status": "FAILED", "stage": exc.stage, "code": exc.code}), file=sys.stderr)
        return 2
    except Exception:
        print(json.dumps({"status": "FAILED", "stage": "internal", "code": "UNEXPECTED_FAILURE"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
