"""Label-blind intake: opens only explicit allowlisted CSVs, never a batch directory.

Custodian-supplied inventories describe sealed payloads; intake never hashes or
opens those payloads. The custodian must export a genuinely label-free manifest.
This is an accidental-disclosure barrier, not protection against maliciously
encoding a target inside an allowed numeric input.
"""
from __future__ import annotations

import csv
import io
import math
import statistics
from collections import Counter
from pathlib import Path

from .common import FEATURES, encoded, require, sha, write_new, write_new_bytes

MANIFEST_COLUMNS = ("sim_id", "config_token", "group_token", *FEATURES)
INVENTORY_COLUMNS = ("file_name", "sim_id", "kind", "byte_size", "sha256", "status")
INVENTORY_KINDS = {"input", "sealed_oracle", "sealed_raw"}
CANONICAL_UNITS = {"P": "W", "VX": "m/s", "LS": "m", "ST": "K"}


class BlindReader:
    """Exact-file capability. No traversal, wildcards, recursion, or data-derived opens."""
    def __init__(self, allowed_paths):
        self.allowed = {Path(p).resolve() for p in allowed_paths}
        self.audit = []

    def csv(self, path, columns):
        original = Path(path)
        require(not original.is_symlink(), "Symlinked intake object is forbidden")
        path = original.resolve()
        require(path in self.allowed and path.is_file(), "Read outside the explicit intake allowlist")
        # Unbuffered byte-by-byte header check prevents reading a hidden column's BODY.
        with path.open("rb", buffering=0) as stream:
            header = bytearray()
            while not header.endswith(b"\n"):
                chunk = stream.read(1)
                if not chunk:
                    break
                header.extend(chunk)
                require(len(header) <= 4096, "Oversized CSV header")
            self.audit.append({"path": str(path), "phase": "header", "bytes": len(header)})
            parsed = next(csv.reader([header.decode("utf-8-sig").strip()]))
            require(tuple(parsed) == tuple(columns), "Unexpected columns: reject BEFORE reading body")
            body = stream.read()
            self.audit.append({"path": str(path), "phase": "allowlisted_body", "bytes": len(body)})
        data = bytes(header) + body
        rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
        require(all(None not in row and all(v is not None for v in row.values()) for row in rows), "Corrupt CSV rows")
        return rows, {"path": str(path), "sha256": sha(data), "byte_size": len(data), "schema": parsed}


def feature_tuple(row):
    values = tuple(float(row[f]) for f in FEATURES)
    require(all(math.isfinite(v) for v in values), "Nonfinite input")
    require(all(v > 0 for v in values[:3]), "P, VX and LS must be positive")
    return values


def _ks(a, b):
    """Descriptive empirical-CDF distance only; no hypothesis test or tuning."""
    support = sorted(set(a + b))
    return max(abs(sum(v <= t for v in a) / len(a) - sum(v <= t for v in b) / len(b)) for t in support)


def intake(manifest, old407, old405, inventory, output, *, provenance, units):
    require(set(provenance) == {"source", "received_utc", "simulator_version", "independence_evidence"}, "Explicit provenance fields required")
    require(set(units) == set(FEATURES), "Record each feature unit, using UNKNOWN where unavailable")
    reader = BlindReader([manifest, old407, old405, inventory])
    rows, manifest_info = reader.csv(manifest, MANIFEST_COLUMNS)
    references = {}
    for name, path in (("OLD-407", old407), ("OLD-405", old405)):
        ref, info = reader.csv(path, MANIFEST_COLUMNS)
        require(len(ref) == (407 if name == "OLD-407" else 405), f"Incomplete {name} reference")
        references[name] = (ref, info)
    files, inventory_info = reader.csv(inventory, INVENTORY_COLUMNS)
    require(all(r["kind"] in INVENTORY_KINDS for r in files), "Unknown inventory kind")
    require(all(r["status"] in {"ok", "missing", "corrupt"} for r in files), "Unknown inventory status")
    require(all(Path(r["file_name"]).name == r["file_name"] and
                not Path(r["file_name"]).is_absolute() for r in files),
            "Inventory file names must be basenames; traversal is forbidden")
    require(all(r["byte_size"].isdigit() and len(r["sha256"]) == 64 and
                all(c in "0123456789abcdef" for c in r["sha256"]) for r in files), "Malformed custodian inventory")
    require(len({r["file_name"] for r in files}) == len(files), "Duplicate inventory file names")
    ids = Counter(r["sim_id"] for r in rows)
    exclusions, valid = [], []
    for index, row in enumerate(rows):
        reasons = []
        if not row["sim_id"] or ids[row["sim_id"]] != 1:
            reasons.append("missing_or_duplicate_simulation_id")
        if not row["config_token"] or not row["group_token"]:
            reasons.append("missing_configuration_or_group_token")
        try:
            feature_tuple(row)
        except (ValueError, TypeError, RuntimeError):
            reasons.append("missing_or_invalid_feature")
        bad = [f for f in files if f["sim_id"] == row["sim_id"] and f["status"] != "ok"]
        if bad:
            reasons.append("custodian_reports_missing_or_corrupt_file")
        if not any(f["sim_id"] == row["sim_id"] and f["kind"] == "input" for f in files):
            reasons.append("no_input_file_inventory_entry")
        if reasons:
            exclusions.append({"manifest_row": index, "sim_id": row["sim_id"], "reasons": reasons})
        else:
            valid.append(row)
    overlaps, diagnostics = {}, {}
    for name, (reference, _) in references.items():
        old_ids = {r["sim_id"] for r in reference}
        old_tokens = {r["config_token"] for r in reference}
        old_inputs = {feature_tuple(r) for r in reference}
        overlaps[name] = [{"sim_id": r["sim_id"], "id": r["sim_id"] in old_ids,
                           "configuration_token": r["config_token"] in old_tokens,
                           "exact_inputs": feature_tuple(r) in old_inputs}
                          for r in valid if r["sim_id"] in old_ids or r["config_token"] in old_tokens or feature_tuple(r) in old_inputs]
        diagnostics[name] = {}
        for feature in FEATURES:
            before, after = [float(r[feature]) for r in reference], [float(r[feature]) for r in valid]
            if after:
                diagnostics[name][feature] = {"old_min": min(before), "old_max": max(before),
                    "new_min": min(after), "new_max": max(after), "old_mean": statistics.mean(before),
                    "new_mean": statistics.mean(after), "ecdf_distance": _ks(before, after),
                    "fraction_outside_old_range": sum(v < min(before) or v > max(before) for v in after) / len(after)}
    dup_inputs = {}
    for row in valid:
        dup_inputs.setdefault(str(feature_tuple(row)), []).append(row["sim_id"])
    exact_duplicates = [v for v in dup_inputs.values() if len(v) > 1]
    digest_files = {}
    for item in files:
        digest_files.setdefault(item["sha256"], []).append(item["file_name"])
    inventory_digest_duplicates = [
        {"sha256": digest, "file_names": names,
         "status": "CUSTODIAN_DECLARED_NOT_INDEPENDENTLY_VERIFIED"}
        for digest, names in sorted(digest_files.items()) if len(names) > 1]
    # Near duplicates are distances for owner review; no unstated exclusion threshold.
    nearest = []
    old_values = [feature_tuple(r) for r in references["OLD-407"][0]]
    ranges = [max(v[j] for v in old_values) - min(v[j] for v in old_values) for j in range(4)]
    for row in valid:
        x = feature_tuple(row)
        nearest.append({"sim_id": row["sim_id"], "nearest_old407_range_scaled_distance":
                        min(math.sqrt(sum(((x[j] - v[j]) / (ranges[j] or 1.0)) ** 2 for j in range(4))) for v in old_values)})
    blockers = []
    if any(overlaps.values()):
        blockers.append("OLD_POPULATION_OVERLAP_REQUIRES_PROVENANCE_RESOLUTION")
    if any(not str(v).strip() or str(v).upper() == "UNKNOWN" for v in provenance.values()):
        blockers.append("INDEPENDENCE_OR_PROVENANCE_UNRESOLVED")
    if units != CANONICAL_UNITS:
        blockers.append("INPUT_UNITS_NOT_CANONICAL_PRECONVERT_TO_W_M_PER_S_M_K")
    if sum(f["kind"] == "sealed_oracle" for f in files) != 1:
        blockers.append("ONE_CUSTODIAN_ORACLE_DIGEST_REQUIRED")
    report = {"schema_version": 1, "stage": "LABEL_BLIND", "manifest": manifest_info,
        "reference_manifests": {n: x[1] for n, x in references.items()}, "inventory_manifest": inventory_info,
        "inventory": files, "inventory_payload_hashes": "CUSTODIAN_DECLARED_NOT_READ_OR_VERIFIED_BY_INTAKE",
        "provenance": provenance, "units": units, "feature_availability": {f: all(r[f] for r in rows) for f in FEATURES},
        "manifest_rows": rows, "technically_usable_rows": valid, "technical_exclusion_candidates": exclusions,
        "duplicate_ids": [i for i, count in ids.items() if count > 1], "exact_input_duplicates": exact_duplicates,
        "inventory_sha256_duplicates": inventory_digest_duplicates,
        "old_overlap": overlaps, "range_and_shift": diagnostics, "near_input_review": nearest,
        "blockers": blockers, "blind_io_audit": reader.audit,
        "limitations": "No raw/oracle access; no automatic independence proof, near-duplicate exclusion or unit conversion."}
    write_new(output, report)
    write_new_bytes(str(output) + ".sha256", (sha(encoded(report)) + "\n").encode("ascii"))
    return report
