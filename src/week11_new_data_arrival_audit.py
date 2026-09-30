"""Bounded, label-blind Week 11 arrival audit.

This module handles Hugging Face tree metadata and the explicitly approved
``parameters.json`` input files.  It deliberately has no dependency on model,
label, frame, monitor-value, or image loaders.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import io
import json
import math
import random
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence


OLD_REVISION = "b6dc254a2b607a31cb9f97b40990339c3d5ca1e8"
NEW_REVISION = "2e1eec9c98fd57609d2815f174586336ab59da07"
REPO_ID = "ioandanielc/sph_v2"
PARAMETER_KEYS = {
    "laser_power": ("P", "W"),
    "scan_speed_x": ("VX", "m/s"),
    "laser_spot_size": ("LS", "m"),
    "substrate_temperature": ("ST", "K"),
}
FOLDER_PATTERN = re.compile(
    r"^P-(?P<P>[^_]+)_VX-(?P<VX>[^_]+)_LS-(?P<LS>[^_]+)_"
    r"ST-(?P<ST>[^_]+)_M-(?P<M>[^_]+)_XI-(?P<XI>[^_]+)_"
    r"XF-(?P<XF>[^_]+)_XL-(?P<XL>[^_]+)_TE-(?P<TE>[^_]+)_"
    r"DT-(?P<DT>[^_]+)_H-(?P<H>[^_]+)$"
)


def normalized_path(value: str) -> str:
    """Return a canonical repository-relative path, rejecting traversal."""

    text = str(value).replace("\\", "/")
    path = PurePosixPath(text)
    if not text or text.startswith("/") or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe repository path: {value!r}")
    return path.as_posix()


def _oid(row: Mapping[str, Any]) -> str | None:
    """Return an explicitly typed content identity without relabelling hashes."""

    for key in ("lfs_sha256", "sha256", "oid"):
        value = row.get(key)
        if value:
            return f"{key}:{value}"
    return None


def canonical_tree(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Normalize a tree response and reject duplicate paths."""

    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in rows:
        path = normalized_path(str(source["path"]))
        if path in seen:
            raise ValueError(f"duplicate tree path: {path}")
        seen.add(path)
        result.append(
            {
                "path": path,
                "type": str(source.get("type", "unknown")),
                "size": int(source["size"]) if source.get("size") is not None else None,
                "oid": source.get("oid"),
                "sha256": source.get("sha256"),
                "lfs_sha256": source.get("lfs_sha256"),
            }
        )
    return sorted(result, key=lambda row: row["path"])


def compare_trees(old_rows: Iterable[Mapping[str, Any]], new_rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Compare two metadata snapshots without opening repository payloads."""

    old = {row["path"]: row for row in canonical_tree(old_rows)}
    new = {row["path"]: row for row in canonical_tree(new_rows)}
    unchanged, modified, unknown = [], [], []
    for path in sorted(old.keys() & new.keys()):
        left, right = old[path], new[path]
        left_id, right_id = _oid(left), _oid(right)
        if left_id is not None and left_id == right_id and left["type"] == right["type"]:
            unchanged.append(path)
        elif left_id is None or right_id is None:
            unknown.append(path)
        else:
            modified.append(path)

    added = sorted(new.keys() - old.keys())
    deleted = sorted(old.keys() - new.keys())
    deleted_by_id: dict[str, list[str]] = defaultdict(list)
    added_by_id: dict[str, list[str]] = defaultdict(list)
    for path in deleted:
        if (identity := _oid(old[path])) is not None:
            deleted_by_id[identity].append(path)
    for path in added:
        if (identity := _oid(new[path])) is not None:
            added_by_id[identity].append(path)
    renamed = []
    for identity in sorted(deleted_by_id.keys() & added_by_id.keys()):
        if len(deleted_by_id[identity]) == len(added_by_id[identity]) == 1:
            renamed.append({"from": deleted_by_id[identity][0], "to": added_by_id[identity][0], "identity": identity})

    duplicate_groups: list[dict[str, Any]] = []
    combined: dict[str, list[str]] = defaultdict(list)
    for prefix, table in (("old", old), ("new", new)):
        for path, row in table.items():
            if (identity := _oid(row)) is not None:
                combined[identity].append(f"{prefix}:{path}")
    for identity, paths in sorted(combined.items()):
        current_paths = [path for path in paths if path.startswith("new:")]
        if len(current_paths) > 1:
            duplicate_groups.append({"identity": identity, "paths": current_paths})

    return {
        "unchanged": unchanged,
        "modified": modified,
        "unknown_content_change": unknown,
        "added": added,
        "deleted": deleted,
        "renamed": renamed,
        "exact_content_duplicate_groups": duplicate_groups,
    }


def parse_experiment_folder(name: str) -> dict[str, Any]:
    """Parse the historical folder grammar; values remain provenance only."""

    match = FOLDER_PATTERN.fullmatch(str(name))
    if not match:
        raise ValueError(f"invalid experiment folder: {name!r}")
    raw = match.groupdict()
    result: dict[str, Any] = {"experiment_name": name, "material": raw["M"], "folder_hash": raw["H"]}
    for key in ("P", "VX", "LS", "ST", "XI", "XF", "XL", "TE", "DT"):
        value = float(raw[key].replace("p", "."))
        if not math.isfinite(value):
            raise ValueError(f"non-finite folder token {key}")
        result[f"folder_{key}"] = value
    return result


def validate_parameter_bytes(raw: bytes, experiment_name: str) -> dict[str, Any]:
    """Validate and project the approved input-only JSON schema."""

    parsed = json.loads(raw)
    if not isinstance(parsed, dict) or set(parsed) != set(PARAMETER_KEYS):
        keys = sorted(parsed) if isinstance(parsed, dict) else [f"<{type(parsed).__name__}>"]
        raise ValueError(f"unexpected parameters.json top-level keys: {keys}")
    folder = parse_experiment_folder(experiment_name)
    projected: dict[str, Any] = {
        "experiment_name": experiment_name,
        "material": folder["material"],
        "folder_hash": folder["folder_hash"],
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
    }
    mismatches: list[str] = []
    for source_key, (short_key, unit) in PARAMETER_KEYS.items():
        item = parsed[source_key]
        if not isinstance(item, dict) or set(item) != {"value", "unit"}:
            raise ValueError(f"unexpected nested schema for {source_key}")
        value = float(item["value"])
        if not math.isfinite(value) or item["unit"] != unit:
            raise ValueError(f"invalid value or unit for {source_key}")
        projected[short_key] = value
        projected[f"{short_key}_unit"] = unit
        if not math.isclose(value, folder[f"folder_{short_key}"], rel_tol=0.0, abs_tol=1e-14):
            mismatches.append(short_key)
    projected["folder_precision_mismatches"] = mismatches
    return projected


def structural_b80_advisory(group_ids: Sequence[str], fold_by_group: Mapping[str, int], folds: int = 5) -> dict[str, Any]:
    """Check only label-free capacity; this is not a freeze or Bug eligibility proof."""

    if len(group_ids) != len(set(group_ids)):
        raise ValueError("group IDs must be unique exact configurations")
    if set(group_ids) != set(fold_by_group):
        raise ValueError("fold certificate must cover every group exactly once")
    fold_values = set(fold_by_group.values())
    if fold_values != set(range(folds)):
        raise ValueError("fold IDs must be contiguous 0..folds-1")
    held_out = {fold: sum(fold_by_group[group] == fold for group in group_ids) for fold in range(folds)}
    training = {fold: len(group_ids) - count for fold, count in held_out.items()}
    return {
        "status": "ADVISORY_ONLY",
        "structural_b80_feasible": min(training.values()) >= 80,
        "final_bug_eligibility": "UNKNOWN",
        "held_out_group_counts": held_out,
        "training_group_counts": training,
    }


def structural_b80_witnesses(group_ids: Sequence[str], seeds: Sequence[int] = (1101, 1102)) -> list[dict[str, Any]]:
    """Build distinct, balanced public-seed witnesses without label access."""

    ordered = sorted(group_ids)
    witnesses: list[dict[str, Any]] = []
    assignments_seen: set[str] = set()
    for seed in seeds:
        shuffled = ordered.copy()
        random.Random(seed).shuffle(shuffled)
        assignment = {group: index % 5 for index, group in enumerate(shuffled)}
        digest = hashlib.sha256(
            "\n".join(f"{group},{assignment[group]}" for group in ordered).encode("ascii")
        ).hexdigest()
        if digest in assignments_seen:
            raise ValueError("structural witnesses must be distinct")
        assignments_seen.add(digest)
        witness = structural_b80_advisory(ordered, assignment)
        witness.update({
            "seed": seed,
            "assignment_sha256": digest,
            "fold_by_group": assignment,
            "status": "ADVISORY_NOT_APPROVED",
        })
        witnesses.append(witness)
    return witnesses


def _read_url(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "thesis-week11-label-blind-audit/1"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def _tree_url(revision: str, path: str | None = None) -> str:
    suffix = "" if path is None else "/" + urllib.parse.quote(normalized_path(path), safe="/")
    return f"https://huggingface.co/api/datasets/{REPO_ID}/tree/{revision}{suffix}?recursive=false&expand=false&limit=1000"


def _tree(revision: str, path: str | None = None) -> list[dict[str, Any]]:
    value = json.loads(_read_url(_tree_url(revision, path)))
    if not isinstance(value, list):
        raise ValueError("Hugging Face tree response was not a list")
    return canonical_tree(value)


def _approved_parameter_url(experiment_name: str) -> str:
    parse_experiment_folder(experiment_name)
    path = urllib.parse.quote(f"{experiment_name}/parameters.json", safe="/")
    return f"https://huggingface.co/datasets/{REPO_ID}/resolve/{NEW_REVISION}/{path}"


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _csv_bytes(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _collect_one(experiment_name: str) -> dict[str, Any]:
    immediate = _tree(NEW_REVISION, experiment_name)
    parameter_rows = [row for row in immediate if row["path"] == f"{experiment_name}/parameters.json"]
    if len(parameter_rows) != 1:
        raise ValueError(f"expected exactly one parameters.json for {experiment_name}")
    raw = _read_url(_approved_parameter_url(experiment_name))
    parameter = validate_parameter_bytes(raw, experiment_name)
    parameter["source_blob_oid"] = parameter_rows[0]["oid"]
    parameter["source_revision"] = NEW_REVISION
    monitor_path = f"{experiment_name}/monitor"
    monitor = _tree(NEW_REVISION, monitor_path) if any(row["path"] == monitor_path for row in immediate) else []
    return {"experiment_name": experiment_name, "immediate": immediate, "monitor": monitor, "parameter": parameter}


def _input_token(row: Mapping[str, Any]) -> str:
    text = "|".join(f"{float(row[key]):.17g}" for key in ("P", "VX", "LS", "ST"))
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def collect_pinned_metadata(output_dir: Path, workers: int = 12) -> dict[str, Any]:
    """Collect only approved tree metadata and new input parameter files."""

    old_root = _tree(OLD_REVISION)
    new_root = _tree(NEW_REVISION)
    comparison = compare_trees(old_root, new_root)
    added_directories = sorted(
        path for path in comparison["added"]
        if next(row for row in new_root if row["path"] == path)["type"] == "directory"
    )
    if len(added_directories) != 185 or not all(FOLDER_PATTERN.fullmatch(path) for path in added_directories):
        raise ValueError(f"expected exactly 185 added experiment directories, got {len(added_directories)}")
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_collect_one, name): name for name in added_directories}
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda row: row["experiment_name"])
    parameters = [row["parameter"] for row in results]
    for row in parameters:
        row["config_token"] = _input_token(row)
        row["group_token"] = row["config_token"]
    by_token: dict[str, list[str]] = defaultdict(list)
    for row in parameters:
        by_token[row["config_token"]].append(row["experiment_name"])
    exact_config_duplicates = [
        {"config_token": token, "experiment_names": names}
        for token, names in sorted(by_token.items()) if len(names) > 1
    ]
    unique_groups = sorted(by_token)
    witnesses = structural_b80_witnesses(unique_groups)
    immediate_counts: dict[str, int] = defaultdict(int)
    monitor_counts: dict[str, int] = defaultdict(int)
    for result in results:
        for row in result["immediate"]:
            immediate_counts[PurePosixPath(row["path"]).name] += 1
        for row in result["monitor"]:
            monitor_counts[PurePosixPath(row["path"]).name] += 1
    summary = {
        "scope": "metadata and approved input parameters only",
        "old_revision": OLD_REVISION,
        "new_revision": NEW_REVISION,
        "root_comparison_counts": {key: len(value) for key, value in comparison.items()},
        "added_experiment_count": len(results),
        "validated_parameter_count": len(parameters),
        "folder_precision_mismatch_count": sum(bool(row["folder_precision_mismatches"]) for row in parameters),
        "unique_exact_configuration_count": len(unique_groups),
        "exact_configuration_duplicate_groups": exact_config_duplicates,
        "immediate_name_availability": dict(sorted(immediate_counts.items())),
        "monitor_name_availability": dict(sorted(monitor_counts.items())),
        "structural_b80_witness_count": len(witnesses),
        "structural_b80_witnesses": [
            {key: value for key, value in witness.items() if key != "fold_by_group"}
            for witness in witnesses
        ],
        "final_repeat_count": "OWNER_DECISION_REQUIRED",
        "bug_eligibility": "UNKNOWN - no independent approved Bug/status source",
    }
    _write_json(output_dir / "old_root_tree.json", old_root)
    _write_json(output_dir / "new_root_tree.json", new_root)
    _write_json(output_dir / "root_tree_comparison.json", comparison)
    _write_json(output_dir / "new_directory_metadata.json", [item for row in results for item in row["immediate"]])
    _write_json(output_dir / "new_monitor_metadata.json", [item for row in results for item in row["monitor"]])
    _write_json(output_dir / "new_input_parameters.json", parameters)
    _write_json(output_dir / "structural_b80_witnesses.json", witnesses)
    _write_json(output_dir / "audit_summary.json", summary)
    return summary


def build_offline_intake(source_dir: Path, output_dir: Path, received_utc: str) -> dict[str, Any]:
    """Rebuild prepared intake from saved approved inputs, without network access."""

    from datetime import datetime, timedelta, timezone
    from .external_validation.intake import MANIFEST_COLUMNS, intake
    from .external_validation.reference_manifests import export

    source_dir, output_dir = Path(source_dir), Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("offline output directory must be absent or empty")
    parsed_time = datetime.fromisoformat(received_utc.replace("Z", "+00:00"))
    if parsed_time.tzinfo is None or parsed_time.utcoffset() != timedelta(0):
        raise ValueError("received_utc must be an explicit UTC instant")
    received_utc = parsed_time.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    parameters = json.loads((source_dir / "new_input_parameters.json").read_text(encoding="utf-8"))
    if len(parameters) != 185:
        raise ValueError("expected 185 saved approved parameter projections")
    output_dir.mkdir(parents=True, exist_ok=True)
    projection_dir = output_dir / "input_projections"
    projection_dir.mkdir()
    manifest_rows, inventory_rows, mapping_rows = [], [], []
    for row in sorted(parameters, key=lambda item: item["experiment_name"]):
        token = _input_token(row)
        if token != row["config_token"] or row["folder_precision_mismatches"]:
            raise ValueError("saved parameter projection failed exact-input validation")
        manifest_rows.append({"sim_id": row["experiment_name"], "config_token": token,
                              "group_token": token, **{key: f"{float(row[key]):.17g}" for key in ("P", "VX", "LS", "ST")}})
        name = token + ".input.json"
        payload = {"sim_id": row["experiment_name"], **{key: row[key] for key in ("P", "VX", "LS", "ST")},
                   "units": {"P": "W", "VX": "m/s", "LS": "m", "ST": "K"}}
        raw = (json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
        (projection_dir / name).write_bytes(raw)
        local_sha = hashlib.sha256(raw).hexdigest()
        inventory_rows.append({"file_name": name, "sim_id": row["experiment_name"], "kind": "input",
                               "byte_size": str(len(raw)), "sha256": local_sha, "status": "ok"})
        mapping_rows.append({"file_name": name, "sim_id": row["experiment_name"],
                             "local_projection_sha256": local_sha,
                             "remote_path": row["experiment_name"] + "/parameters.json",
                             "remote_raw_sha256": row["raw_sha256"], "remote_blob_oid": row["source_blob_oid"],
                             "source_revision": row["source_revision"]})
    manifest_bytes = _csv_bytes(manifest_rows, MANIFEST_COLUMNS)
    (output_dir / "WEEK11_NEW_BATCH_MANIFEST.csv").write_bytes(manifest_bytes)
    (output_dir / "new185_input_manifest_candidate.csv").write_bytes(manifest_bytes)
    (output_dir / "input_inventory.csv").write_bytes(_csv_bytes(inventory_rows, ("file_name", "sim_id", "kind", "byte_size", "sha256", "status")))
    (output_dir / "input_projection_source_mapping.csv").write_bytes(_csv_bytes(mapping_rows, ("file_name", "sim_id", "local_projection_sha256", "remote_path", "remote_raw_sha256", "remote_blob_oid", "source_revision")))
    refs = export(output_dir / "reference_manifests")
    report = intake(output_dir / "WEEK11_NEW_BATCH_MANIFEST.csv", refs["OLD-407"], refs["OLD-405"],
                    output_dir / "input_inventory.csv", output_dir / "prepared_intake_report.json",
                    provenance={"source": f"{REPO_ID}@{NEW_REVISION}", "received_utc": received_utc,
                                "simulator_version": "UNKNOWN", "independence_evidence": "UNKNOWN"},
                    units={"P": "W", "VX": "m/s", "LS": "m", "ST": "K"})
    witnesses = structural_b80_witnesses(sorted(row["config_token"] for row in manifest_rows))
    _write_json(output_dir / "structural_b80_witnesses.json", witnesses)
    overlap = {"stage": "LABEL_BLIND_INPUT_ONLY", "new_rows": 185, "old_reference_rows": 407,
               "simulation_id_overlap_count": sum(item["id"] for item in report["old_overlap"]["OLD-407"]),
               "exact_input_overlap_count": sum(item["exact_inputs"] for item in report["old_overlap"]["OLD-407"]),
               "limitations": ["Bug eligibility is unknown.", "Prepared frozen intake ran and remains blocked by unresolved independence/provenance and the missing custodian sealed-oracle digest."]}
    _write_json(output_dir / "label_blind_overlap_summary.json", overlap)
    return {"technically_usable_rows": len(report["technically_usable_rows"]),
            "technical_exclusions": len(report["technical_exclusion_candidates"]),
            "blockers": report["blockers"], "witness_count": len(witnesses)}


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    compare = subparsers.add_parser("compare")
    compare.add_argument("old_tree", type=Path)
    compare.add_argument("new_tree", type=Path)
    compare.add_argument("output", type=Path)
    collect = subparsers.add_parser("collect")
    collect.add_argument("output_dir", type=Path)
    collect.add_argument("--workers", type=int, default=12)
    offline = subparsers.add_parser("build-offline")
    offline.add_argument("source_dir", type=Path)
    offline.add_argument("output_dir", type=Path)
    offline.add_argument("--received-utc", required=True)
    args = parser.parse_args()
    if args.command == "collect":
        print(json.dumps(collect_pinned_metadata(args.output_dir, workers=args.workers), indent=2, sort_keys=True))
        return 0
    if args.command == "build-offline":
        print(json.dumps(build_offline_intake(args.source_dir, args.output_dir, args.received_utc), indent=2, sort_keys=True))
        return 0
    old = json.loads(args.old_tree.read_text(encoding="utf-8"))
    new = json.loads(args.new_tree.read_text(encoding="utf-8"))
    report = compare_trees(old, new)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
