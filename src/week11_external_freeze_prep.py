"""Prepare the Week 11 external-validation freeze without opening labels."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.external_validation import freeze
from src.external_validation.common import BUDGETS, PAIRED_INTERVAL_METHOD, core_hashes, environment

PINNED_REVISION = "2e1eec9c98fd57609d2815f174586336ab59da07"
WITHHELD_REASON = "WITHHELD_DUE_TO_BUG_FOR_EXTERNAL_VALIDATION"
EXPECTED_BLOCKERS = {
    "INDEPENDENCE_OR_PROVENANCE_UNRESOLVED",
    "ONE_CUSTODIAN_ORACLE_DIGEST_REQUIRED",
}
MANIFEST_COLUMNS = ("sim_id", "config_token", "group_token", "P", "VX", "LS", "ST")
STATUS_COLUMNS = {
    "simulation_id", "bug_affected", "any_bug_free_false",
    "any_correctly_finished_false", "technical_usability_status",
}
APPROVED_REPEAT_SEEDS = tuple(range(1101, 1121))
PROTOCOL_OWNER = "Thesis protocol owner (user instructions dated 2026-10-01)"


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or ()), list(reader)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _write_csv(path: Path, fields: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def fold_candidate(rows: Sequence[Mapping[str, str]], seed: int, repeat: int) -> dict[str, Any]:
    groups = sorted(str(row["group_token"]) for row in rows)
    if len(groups) != len(rows) or len(set(groups)) != len(groups):
        raise ValueError("final cohort must contain one unique exact-configuration group per simulation")
    shuffled = groups.copy()
    random.Random(seed).shuffle(shuffled)
    by_group = {group: index % 5 + 1 for index, group in enumerate(shuffled)}
    folds = []
    for fold in range(1, 6):
        test = sorted(group for group, assigned in by_group.items() if assigned == fold)
        folds.append({"fold": fold, "test_group_tokens": test,
                      "test_count": len(test), "train_count": len(rows) - len(test)})
    digest = hashlib.sha256("\n".join(f"{group},{by_group[group]}" for group in groups).encode()).hexdigest()
    return {"repeat": repeat, "seed": seed,
            "algorithm": "random.Random(seed).shuffle(sorted(group IDs)); fold=index modulo 5 plus 1",
            "assignment_sha256": digest, "folds": folds}


def prepare(*, manifest_path: Path, bug_status_path: Path, overlap_path: Path,
            directory_metadata_path: Path, monitor_metadata_path: Path,
            intake_path: Path, output_directory: Path) -> dict[str, Any]:
    manifest_header, manifest = _read_csv(manifest_path)
    status_header, statuses = _read_csv(bug_status_path)
    if tuple(manifest_header) != MANIFEST_COLUMNS or len(manifest) != 185:
        raise ValueError("canonical delivery manifest must have the exact seven-column schema and 185 rows")
    if not STATUS_COLUMNS.issubset(status_header) or len(statuses) != 185:
        raise ValueError("Bug-status artifact lacks the approved 185-row projection")
    by_id = {row["sim_id"]: row for row in manifest}
    status_by_id = {row["simulation_id"]: row for row in statuses}
    if len(by_id) != 185 or len(status_by_id) != 185 or set(by_id) != set(status_by_id):
        raise ValueError("manifest and Bug-status membership differ or contain duplicates")
    included_ids = sorted(sim_id for sim_id, row in status_by_id.items()
                          if row["technical_usability_status"] == "KEEP")
    withheld_ids = sorted(set(by_id) - set(included_ids))
    if len(included_ids) != 136 or len(withheld_ids) != 49:
        raise ValueError("accepted owner rule must produce exactly 136 included and 49 withheld")
    for sim_id in included_ids:
        row = status_by_id[sim_id]
        if (row["bug_affected"].lower() != "false" or
                row["any_bug_free_false"].lower() != "false" or
                row["any_correctly_finished_false"].lower() != "false"):
            raise ValueError("an included simulation contradicts the accepted Bug/status rule")
    for sim_id in withheld_ids:
        row = status_by_id[sim_id]
        if row["bug_affected"].lower() != "true" or row["technical_usability_status"] != "UNRESOLVED":
            raise ValueError("a withheld simulation lacks the accepted explicit-Bug UNRESOLVED status")
    included = [by_id[sim_id] for sim_id in included_ids]
    if len({row["config_token"] for row in included}) != 136 or len({row["group_token"] for row in included}) != 136:
        raise ValueError("included configurations/groups are not unique")
    if not all(all(str(row[key]).strip() for key in MANIFEST_COLUMNS) for row in included):
        raise ValueError("included manifest has a missing required input field")
    try:
        input_tuples = [tuple(float(row[key]) for key in ("P", "VX", "LS", "ST")) for row in included]
    except ValueError as exc:
        raise ValueError("included manifest has a nonnumeric input") from exc
    if not all(all(math.isfinite(value) for value in values) for values in input_tuples):
        raise ValueError("included manifest has a nonfinite input")
    if len(set(input_tuples)) != 136:
        raise ValueError("included exact numeric input tuples are not unique")

    overlap = json.loads(overlap_path.read_text(encoding="utf-8"))
    if overlap.get("simulation_id_overlap_count") != 0 or overlap.get("exact_input_overlap_count") != 0:
        raise ValueError("OLD population overlap is not zero")
    directory_metadata = json.loads(directory_metadata_path.read_text(encoding="utf-8"))
    monitor_metadata = json.loads(monitor_metadata_path.read_text(encoding="utf-8"))
    available: dict[str, set[str]] = {sim_id: set() for sim_id in included_ids}
    for item in [*directory_metadata, *monitor_metadata]:
        parts = str(item["path"]).split("/")
        if parts[0] in available:
            available[parts[0]].add("/".join(parts[1:]))
    required_names = {"parameters.json", "frames.csv", "monitor/iter.dat", "monitor/time.dat"}
    if not all(required_names.issubset(available[sim_id]) for sim_id in included_ids):
        raise ValueError("an included simulation lacks required technical-file metadata")

    intake = json.loads(intake_path.read_text(encoding="utf-8"))
    if set(intake.get("blockers", ())) != EXPECTED_BLOCKERS:
        raise ValueError("prepared intake blockers differ from the two acknowledged unresolved gates")
    if intake.get("manifest", {}).get("sha256") != _sha(manifest_path):
        raise ValueError("canonical manifest bytes differ from the verified intake manifest")
    assignments = [fold_candidate(included, seed, repeat)
                   for repeat, seed in enumerate(APPROVED_REPEAT_SEEDS, 1)]
    executable_assignments = [{"repeat": item["repeat"], "folds": [
        {"fold": fold["fold"], "test_group_tokens": fold["test_group_tokens"]}
        for fold in item["folds"]]} for item in assignments]
    _, certified_minimum_train = freeze._validate_fold_certificate(executable_assignments, 20, included)

    output_directory.mkdir(parents=True, exist_ok=False)
    (output_directory / "FULL_DELIVERY_MANIFEST.csv").write_bytes(manifest_path.read_bytes())
    _write_csv(output_directory / "INCLUDED_MANIFEST.csv", MANIFEST_COLUMNS, included)
    withheld_fields = (*MANIFEST_COLUMNS, "external_validation_status", "technical_reason")
    withheld = [{**by_id[sim_id], "external_validation_status": WITHHELD_REASON,
                 "technical_reason": WITHHELD_REASON} for sim_id in withheld_ids]
    _write_csv(output_directory / "WITHHELD_MANIFEST.csv", withheld_fields, withheld)
    _write_json(output_directory / "PRELABEL_FOLD_ASSIGNMENTS.json", {
        "status": "DATASET_DECISION_RECORDED_PRELABEL", "repeat_count": 20,
        "seeds": list(APPROVED_REPEAT_SEEDS), "assignments": assignments,
        "decision_basis": "Twenty repeats were chosen before labels; two repeats meet only the software minimum and are too discrete for the frozen percentile interval."})

    outputs = {name: f"external_validation/{name}{freeze.OUTPUT_SUFFIXES[name]}"
               for name in sorted(freeze.OUTPUT_FIELDS)}
    decisions = {
        "owner": PROTOCOL_OWNER,
        "included_ids": included_ids,
        "owner_excluded_ids": [{"sim_id": sim_id, "technical_reason": WITHHELD_REASON}
                               for sim_id in withheld_ids],
        "grouping": "group_token", "split_construction": "PreassignedGroupFiveFold",
        "fold_count": 5, "repeat_count": 20,
        "random_seeds": list(APPROVED_REPEAT_SEEDS),
        "prelabel_fold_assignment": executable_assignments,
        "exact_feasible_budgets": BUDGETS, "paired_interval_method": PAIRED_INTERVAL_METHOD,
        "failure_fallback_rules": freeze.EXPECTED_FAILURE_RULES, "output_locations": outputs,
    }
    _write_json(output_directory / "PRELABEL_OWNER_DECISIONS.json", decisions)
    if set(decisions) != freeze.DECISION_FIELDS:
        raise RuntimeError("owner decision artifact must exactly match the executable freeze schema")

    # Exercise the real freeze gate with a structurally complete candidate. It must stop
    # at intake before any seal is written because provenance and oracle custody are absent.
    freeze_gate_error = None
    try:
        freeze.build_addendum(intake_path, decisions)
    except Exception as exc:
        freeze_gate_error = f"{type(exc).__name__}: {exc}"
    if not freeze_gate_error or "Intake blockers must be resolved before freezing" not in freeze_gate_error:
        raise RuntimeError("existing freeze gate did not stop on the acknowledged intake blockers")

    included_vx = [float(row["VX"]) for row in included]
    withheld_vx = [float(row["VX"]) for row in withheld]
    preparation = {
        "status": "BLOCKED_AND_NOT_LABEL_AUTHORIZATION", "label_accessed": False,
        "ready_to_open_sealed_label_oracle": False, "pinned_hf_revision": PINNED_REVISION,
        "included_count": len(included), "withheld_count": len(withheld),
        "withheld_reason": WITHHELD_REASON, "blockers": sorted(EXPECTED_BLOCKERS),
        "freeze_gate_result": freeze_gate_error,
        "repeat_count": 20, "repeat_seeds": list(APPROVED_REPEAT_SEEDS),
        "fold_train_counts": [[f["train_count"] for f in item["folds"]] for item in assignments],
        "minimum_training_pool_size": certified_minimum_train,
        "b80_structurally_feasible_for_all_100_folds": True,
        "cohort_scope": "All future external-validation claims are conditional on the 136-run Bug-cleared cohort, not the full 185-run arrival batch.",
        "label_free_input_selection_observation": {
            "feature": "VX", "units": "m/s", "interpretation": "STRUCTURED_INPUT_SELECTION_NOT_RANDOM_LOSS",
            "included_136": {"minimum": min(included_vx), "median": statistics.median(included_vx), "maximum": max(included_vx)},
            "withheld_49": {"minimum": min(withheld_vx), "median": statistics.median(withheld_vx), "maximum": max(withheld_vx)},
            "action": "No further exclusion or label work; scope claims to the Bug-cleared cohort.",
        },
        "contracts": {"arms": list(freeze.ARMS), "primary_endpoint": freeze.PRIMARY,
                      "budgets": BUDGETS, "paired_interval_method": PAIRED_INTERVAL_METHOD,
                      "failure_fallback_rules": freeze.EXPECTED_FAILURE_RULES,
                      "output_locations": outputs,
                      "execution_output_root": "outputs/week11_track_a_external_validation",
                      "initial_design_seed_namespace": "w85.seed_u32(w85.seed_key('run',split_id,'initial_design'))"},
        "bindings": {"environment": environment(), "source_code_hashes": core_hashes()},
        "source_artifacts": {str(path.name): _sha(path) for path in
            (manifest_path, bug_status_path, overlap_path, directory_metadata_path,
             monitor_metadata_path, intake_path)},
        "generated_artifact_sha256": {name: _sha(output_directory / name) for name in (
            "FULL_DELIVERY_MANIFEST.csv", "INCLUDED_MANIFEST.csv", "WITHHELD_MANIFEST.csv",
            "PRELABEL_FOLD_ASSIGNMENTS.json", "PRELABEL_OWNER_DECISIONS.json")},
        "limitations": [
            "Scientific provenance is absent and cannot be inferred from the Hugging Face tree.",
            "A distinct custodial sim_id,has_keyhole oracle filename, byte size, and SHA-256 are absent.",
            "The mixed annotation payload is not accepted as the sealed binary oracle.",
            "No EXTERNAL_BATCH_FREEZE.json or SHA-256 sidecar was created.",
        ],
    }
    preparation_path = output_directory / "FREEZE_PREPARATION.json"
    _write_json(preparation_path, preparation)
    with (output_directory / "FREEZE_PREPARATION.sha256").open("x", encoding="ascii", newline="\n") as stream:
        stream.write(_sha(preparation_path) + "\n")
    return preparation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "bug-status", "overlap", "directory-metadata",
                 "monitor-metadata", "intake", "output-directory"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    args = parser.parse_args()
    prepare(manifest_path=args.manifest, bug_status_path=args.bug_status,
            overlap_path=args.overlap, directory_metadata_path=args.directory_metadata,
            monitor_metadata_path=args.monitor_metadata, intake_path=args.intake,
            output_directory=args.output_directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
