"""Pinned, outcome-blind Bug/status audit for the Week 11 batch."""
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
import statistics
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ID = "ioandanielc/sph_v2"
PINNED_REVISION = "2e1eec9c98fd57609d2815f174586336ab59da07"
PINNED_FILE = "labels_new_data_4_prep.csv"
PINNED_SIZE = 12_397_054
PINNED_SHA256 = "b45518a51ea59d97d1e28e3f2ce5ef563af1c049bce83d0d88b3d510b1adf16d"
EXPECTED_HEADER = ("name", "hash", "P", "VX", "LS", "ST", "bug_free",
                   "correctly_finished", "timestep", "label_1", "label_2", "label_final")
LABEL_COLUMNS = ("label_1", "label_2", "label_final")
SCREENSHOT_BUG = "Screenshot Bug"
BUG_PATTERN = re.compile(r"\bbugs?\b", re.IGNORECASE)


def _boolean(value: str, column: str) -> bool:
    text = value.strip().lower()
    if text in {"true", "1"}: return True
    if text in {"false", "0"}: return False
    raise ValueError(f"invalid boolean in approved status column {column}: {value!r}")


def _time(value: str) -> float:
    result = float(value)
    if not math.isfinite(result): raise ValueError("non-finite timestep")
    return result


def project_bug_only(raw: bytes, allowed_ids: Sequence[str], *, expected_sha256: str = PINNED_SHA256,
                     expected_size: int = PINNED_SIZE) -> dict[str, Any]:
    """Project only Bug tokens and technical status, discarding other labels."""
    digest = hashlib.sha256(raw).hexdigest()
    if len(raw) != expected_size or digest != expected_sha256:
        raise ValueError("pinned mixed annotation byte identity mismatch")
    allowed = set(allowed_ids)
    if len(allowed) != 185 or len(allowed_ids) != 185:
        raise ValueError("allowlist must contain exactly 185 unique simulation IDs")
    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    header = next(reader)
    if tuple(header) != EXPECTED_HEADER: raise ValueError("mixed annotation header differs from approved schema")
    wanted = ("name", "hash", "bug_free", "correctly_finished", "timestep", *LABEL_COLUMNS)
    index = {name: header.index(name) for name in wanted}
    rows_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_hashes: dict[str, str] = {}
    frame_crosstab: Counter[tuple[bool, bool, bool, bool]] = Counter()
    category_counts: Counter[str] = Counter()
    for csv_row, row in enumerate(reader, start=2):
        if len(row) != len(header): raise ValueError(f"malformed row {csv_row}")
        sim_id = row[index["name"]].strip()
        if sim_id not in allowed: raise ValueError(f"row outside 185-ID allowlist: {sim_id!r}")
        source_hash = row[index["hash"]].strip()
        if sim_id in source_hashes and source_hashes[sim_id] and source_hash and source_hashes[sim_id] != source_hash:
            raise ValueError(f"source hash changes within {sim_id}")
        if sim_id not in source_hashes or source_hash:
            source_hashes[sim_id] = source_hash
        bug_free = _boolean(row[index["bug_free"]], "bug_free")
        finished = _boolean(row[index["correctly_finished"]], "correctly_finished")
        exact_flags, any_flags, categories = {}, {}, set()
        for column in LABEL_COLUMNS:
            value = row[index[column]]
            suffix = "final" if column == "label_final" else column[-1]
            exact_flags[f"screenshot_bug_flag_{suffix}"] = value == SCREENSHOT_BUG
            any_flags[f"explicit_bug_token_{suffix}"] = bool(BUG_PATTERN.search(value))
            if any_flags[f"explicit_bug_token_{suffix}"]:
                category = value.strip()
                if len(category) > 200: raise ValueError("oversized explicit Bug category")
                categories.add(category)
                category_counts[category] += 1
            # Non-Bug categorical values are immediately discarded.
        any_bug = any(any_flags.values())
        exact_bug = any(exact_flags.values())
        frame_crosstab[(bug_free, finished, any_bug, exact_bug)] += 1
        rows_by_id[sim_id].append({
            "simulation_id": sim_id, "source_hash": source_hash,
            "annotation_ordinal": len(rows_by_id[sim_id]), "timestep": _time(row[index["timestep"]]),
            "bug_free": bug_free, "correctly_finished": finished,
            "explicit_bug_categories": ";".join(sorted(categories)), **any_flags, **exact_flags,
        })
    if set(rows_by_id) != allowed:
        raise ValueError(f"missing allowed simulations: {sorted(allowed - set(rows_by_id))[:3]}")
    affected, statuses, bug_frames = [], [], []
    for sim_id in sorted(allowed):
        rows = rows_by_id[sim_id]
        flagged = [row for row in rows if any(row[f"explicit_bug_token_{s}"] for s in ("1", "2", "final"))]
        timesteps = [row["timestep"] for row in rows]
        if any(right <= left for left, right in zip(timesteps, timesteps[1:])):
            raise ValueError(f"timestep order is not strictly increasing within {sim_id}")
        first = flagged[0] if flagged else None
        prior = rows[first["annotation_ordinal"] - 1] if first and first["annotation_ordinal"] else None
        unexpected = sorted({cat for row in flagged for cat in row["explicit_bug_categories"].split(";")
                             if cat and cat != SCREENSHOT_BUG})
        statuses.append({
            "simulation_id": sim_id, "source_hash": source_hashes[sim_id], "bug_affected": bool(first),
            "bug_from_beginning": bool(first and first["annotation_ordinal"] == 0),
            "any_bug_free_false": any(not row["bug_free"] for row in rows),
            "any_correctly_finished_false": any(not row["correctly_finished"] for row in rows),
            "technical_usability_status": (
                "UNRESOLVED" if first or any(not row["bug_free"] or not row["correctly_finished"] for row in rows)
                else "PROVISIONAL_KEEP_NO_EXPLICIT_BUG_TOKEN"
            ),
        })
        if first:
            span = max(1, len(rows) - 1)
            affected.append({
                "simulation_id": sim_id, "source_hash": source_hashes[sim_id], "bug_reason": "unknown",
                "first_bug_annotation_ordinal": first["annotation_ordinal"], "first_bug_timestep": first["timestep"],
                "preceding_non_bug_annotation_ordinal": prior["annotation_ordinal"] if prior else None,
                "preceding_non_bug_timestep": prior["timestep"] if prior else None,
                "last_valid_frame": "UNRESOLVED",
                "bug_from_beginning": first["annotation_ordinal"] == 0,
                "annotation_count": len(rows),
                "bug_frame_count": len(flagged),
                "last_bug_annotation_ordinal": flagged[-1]["annotation_ordinal"],
                "first_bug_fraction_of_annotation_span": first["annotation_ordinal"] / span,
                "explicit_bug_categories": ";".join(sorted({cat for row in flagged for cat in row["explicit_bug_categories"].split(";") if cat})),
                "unexpected_bug_categories": ";".join(unexpected),
                "any_bug_free_false": any(not row["bug_free"] for row in rows),
                "any_correctly_finished_false": any(not row["correctly_finished"] for row in rows),
                "technical_usability_status": "UNRESOLVED",
            })
            bug_frames.extend(flagged)
    unexpected_categories = sorted(category for category in category_counts if category != SCREENSHOT_BUG)
    summary = {
        "total_simulations": 185, "bug_affected_simulations": len(affected),
        "bug_free_simulations": 185 - len(affected), "bug_percentage": 100 * len(affected) / 185,
        "bug_from_beginning": sum(row["bug_from_beginning"] for row in affected),
        "bug_later": sum(not row["bug_from_beginning"] for row in affected),
        "bug_frame_count": len(bug_frames),
        "reason_counts": {"unknown": len(affected)},
        "explicit_bug_category_cell_counts": dict(sorted(category_counts.items())),
        "unexpected_bug_categories": unexpected_categories,
        "representation_mismatch": bool(unexpected_categories),
        "bug_free_varies_within_simulation_count": sum(len({row["bug_free"] for row in rows}) > 1 for rows in rows_by_id.values()),
        "bug_free_constant_false_simulation_count": sum({row["bug_free"] for row in rows} == {False} for rows in rows_by_id.values()),
        "bug_free_constant_true_simulation_count": sum({row["bug_free"] for row in rows} == {True} for rows in rows_by_id.values()),
        "correctly_finished_varies_within_simulation_count": sum(len({row["correctly_finished"] for row in rows}) > 1 for rows in rows_by_id.values()),
        "correctly_finished_constant_false_simulation_count": sum({row["correctly_finished"] for row in rows} == {False} for rows in rows_by_id.values()),
        "correctly_finished_constant_true_simulation_count": sum({row["correctly_finished"] for row in rows} == {True} for rows in rows_by_id.values()),
        "frame_status_crosstab": {
            f"bug_free_{int(bf)}__finished_{int(fin)}__any_bug_{int(any_bug)}__screenshot_bug_{int(exact)}": count
            for (bf, fin, any_bug, exact), count in sorted(frame_crosstab.items())},
        "raw_sha256": digest, "raw_size_bytes": len(raw), "source_revision": PINNED_REVISION,
        "source_file": PINNED_FILE,
        "missing_source_hash_simulations": sum(not value for value in source_hashes.values()),
        "representation": "Frame-level explicit Bug word token flags; annotation ordinal is row order, not confirmed frame_idx.",
        "reason_and_wall_contact": "UNRESOLVED_NO_FIELD_IN_HEADER",
        "limitations": "Non-Bug physical categories were not retained, counted, displayed, or used.",
    }
    return {"affected": affected, "status_rows": statuses, "bug_frames": bug_frames, "summary": summary}


def fetch_pinned_bytes() -> bytes:
    url = f"https://huggingface.co/datasets/{REPO_ID}/resolve/{PINNED_REVISION}/{urllib.parse.quote(PINNED_FILE)}"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "week11-bug-only-audit/1"}), timeout=120) as response:
        return response.read()


def _fetch_repo_path(path: str) -> bytes:
    url = f"https://huggingface.co/datasets/{REPO_ID}/resolve/{PINNED_REVISION}/{urllib.parse.quote(path, safe='/')}"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "week11-bug-timing-audit/1"}), timeout=120) as response:
        return response.read()


def enrich_technical_timing(affected: Sequence[Mapping[str, Any]], bug_frames: Sequence[Mapping[str, Any]],
                            monitor_metadata: Sequence[Mapping[str, Any]], directory_metadata: Sequence[Mapping[str, Any]],
                            *, fetcher=_fetch_repo_path, workers: int = 6, include_bounds: bool = False) -> dict[str, Any]:
    """Add approved frame/time and pre-Bug bounds integrity facts."""
    import numpy as np

    ids = {row["simulation_id"] for row in affected}
    wanted_monitor = {"iter.dat", "time.dat"}
    if include_bounds: wanted_monitor.add("position-bounds_melt.dat")
    metadata: dict[tuple[str, str], Mapping[str, Any]] = {}
    for item in monitor_metadata:
        parts = item["path"].split("/")
        if parts[0] in ids and parts[-1] in wanted_monitor:
            metadata[(parts[0], parts[-1])] = item
    frames_meta = {item["path"].split("/")[0]: item for item in directory_metadata
                   if item["path"].split("/")[0] in ids and item["path"].endswith("/frames.csv")}
    if len(metadata) != len(ids) * len(wanted_monitor) or len(frames_meta) != len(ids):
        raise ValueError("incomplete approved technical metadata for affected simulations")
    by_oid: dict[str, str] = {}
    for item in [*metadata.values(), *frames_meta.values()]:
        oid = str(item["oid"])
        by_oid.setdefault(oid, str(item["path"]))
    fetched: dict[str, bytes] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetcher, path): oid for oid, path in by_oid.items()}
        for future in concurrent.futures.as_completed(futures):
            fetched[futures[future]] = future.result()
    provenance = [{"oid": oid, "representative_path": by_oid[oid], "byte_size": len(raw),
                   "sha256": hashlib.sha256(raw).hexdigest()} for oid, raw in sorted(fetched.items())]

    def vector(sim_id: str, name: str) -> Any:
        raw = fetched[str(metadata[(sim_id, name)]["oid"])]
        return np.loadtxt(io.BytesIO(raw), delimiter="," if name == "position-bounds_melt.dat" else None, ndmin=2 if name.startswith("position") else 1)

    def frames(sim_id: str) -> list[tuple[int, float]]:
        raw = fetched[str(frames_meta[sim_id]["oid"])]
        reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
        header = next(reader)
        expected = ["frame_idx", "timestep", "label", "front_filename", "side_filename", "top_filename"]
        if header != expected: raise ValueError(f"unexpected frames.csv schema for {sim_id}")
        projected = []
        for row in reader:
            if len(row) != len(expected): raise ValueError(f"malformed frames.csv row for {sim_id}")
            projected.append((int(row[0]), _time(row[1])))
            # label and image-name cells are never inspected or retained.
        return projected

    bug_by_id: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in bug_frames: bug_by_id[row["simulation_id"]].append(row)
    enriched, enriched_frames, integrity = [], [], []
    for source in affected:
        sim_id = source["simulation_id"]
        iterations, times, frame_rows = vector(sim_id, "iter.dat"), vector(sim_id, "time.dat"), frames(sim_id)
        bounds = vector(sim_id, "position-bounds_melt.dat") if include_bounds else None
        if include_bounds and (bounds.ndim != 2 or bounds.shape[1] != 6): raise ValueError(f"bounds schema is not six columns for {sim_id}")
        if not (len(iterations) == len(times)) or (include_bounds and len(bounds) != len(times)): raise ValueError(f"monitor row alignment failed for {sim_id}")
        if not (np.isfinite(iterations).all() and np.isfinite(times).all() and
                np.all(np.diff(iterations) > 0) and np.all(np.diff(times) > 0)):
            raise ValueError(f"monitor chronology failed for {sim_id}")
        if source.get("annotation_count") not in (None, "") and len(frame_rows) != int(source["annotation_count"]):
            raise ValueError(f"frame/annotation count mismatch for {sim_id}")
        frame_indices = [item[0] for item in frame_rows]
        if frame_indices != list(range(len(frame_rows))): raise ValueError(f"frame indices not contiguous for {sim_id}")
        if any(right <= left for left, right in zip([item[1] for item in frame_rows], [item[1] for item in frame_rows][1:])):
            raise ValueError(f"frame timesteps not strictly increasing for {sim_id}")
        ledger = bug_by_id[sim_id]
        for row in ledger:
            ordinal = int(row["annotation_ordinal"])
            frame_idx, frame_timestep = frame_rows[ordinal]
            if frame_timestep != float(row["timestep"]): raise ValueError(f"frame/annotation timestep mismatch for {sim_id}")
            matches = np.flatnonzero(iterations == frame_timestep)
            if len(matches) != 1: raise ValueError(f"annotation timestep does not map uniquely to iter.dat for {sim_id}")
            monitor_index = int(matches[0])
            enriched_frames.append({**row, "confirmed_frame_idx": frame_idx, "monitor_row_index": monitor_index,
                                    "physical_time_seconds": float(times[monitor_index])})
        first_ordinal = int(source["first_bug_annotation_ordinal"])
        first_frame_idx, first_frame_timestep = frame_rows[first_ordinal]
        first_monitor = int(np.flatnonzero(iterations == first_frame_timestep)[0])
        preceding_timestep = frame_rows[first_ordinal - 1][1] if first_ordinal else None
        preceding_matches = np.flatnonzero(iterations == preceding_timestep) if preceding_timestep is not None else []
        if preceding_timestep is not None and len(preceding_matches) != 1:
            raise ValueError(f"preceding annotation timestep does not map uniquely for {sim_id}")
        preceding_monitor = int(preceding_matches[0]) if preceding_timestep is not None else None
        check = {"simulation_id": sim_id, "prebug_monitor_rows": first_monitor,
                 "bounds_integrity_status": "NOT_RUN_REMOTE_FETCH_TIMEOUT"}
        if include_bounds:
            finite = np.isfinite(bounds[:first_monitor]); sentinel = np.abs(bounds[:first_monitor]) >= 1e30
            nonsentinel_rows = ~sentinel.any(axis=1)
            ordered = ((bounds[:first_monitor, 1] >= bounds[:first_monitor, 0]) &
                       (bounds[:first_monitor, 3] >= bounds[:first_monitor, 2]) &
                       (bounds[:first_monitor, 5] >= bounds[:first_monitor, 4]))
            check.update({"bounds_integrity_status": "COMPLETED",
                          "extreme_value_threshold": 1e30,
                          "extreme_value_definition": "Historical SENTINEL_THRESHOLD; descriptive only, no eligibility effect",
                          "prebug_nonfinite_cell_count": int((~finite).sum()),
                          "prebug_sentinel_row_count": int(sentinel.any(axis=1).sum()),
                          "prebug_unordered_nonsentinel_row_count": int((~ordered & nonsentinel_rows).sum()),
                          "numeric_prebug_integrity_pass": bool(finite.all() and not (~ordered & nonsentinel_rows).any())})
        integrity.append(check)
        enriched.append({**source, "annotation_count": len(frame_rows), "bug_frame_count": len(ledger),
                         "last_bug_annotation_ordinal": max(int(row["annotation_ordinal"]) for row in ledger),
                         "first_bug_fraction_of_annotation_span": first_ordinal / max(1, len(frame_rows) - 1),
                         "confirmed_first_bug_frame_idx": first_frame_idx,
                         "first_bug_physical_time_seconds": float(times[first_monitor]),
                         "preceding_non_bug_physical_time_seconds": float(times[preceding_monitor]) if preceding_monitor is not None else None,
                         **{key: value for key, value in check.items() if key != "simulation_id"}})
    return {"affected": enriched, "bug_frames": enriched_frames, "integrity": integrity,
            "provenance": provenance, "unique_payload_downloads": len(fetched)}


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n"); writer.writeheader(); writer.writerows(rows)


def _ids(manifest: Path) -> list[str]:
    with manifest.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["sim_id", "config_token", "group_token", "P", "VX", "LS", "ST"]:
            raise ValueError("unexpected input manifest schema")
        return [row["sim_id"] for row in reader]


def finalize_result(result: dict[str, Any], manifest: Path) -> dict[str, Any]:
    """Apply the accepted technical statuses and structural B80 witness."""
    bug_by_id: dict[str, set[int]] = defaultdict(set)
    for row in result["bug_frames"]: bug_by_id[row["simulation_id"]].add(int(row["annotation_ordinal"]))
    pattern_counts: Counter[str] = Counter()
    for row in result["affected"]:
        ordinals = bug_by_id[row["simulation_id"]]; count = int(row["annotation_count"])
        pattern = ("TERMINAL_CONTIGUOUS_SUFFIX" if ordinals == set(range(min(ordinals), count))
                   else "NONTERMINAL" if max(ordinals) < count - 1 else "INTERMITTENT_TO_END")
        row["bug_sequence_pattern"] = pattern; pattern_counts[pattern] += 1
    for row in result["status_rows"]:
        consistent = not row["any_bug_free_false"] and not row["any_correctly_finished_false"]
        keep = not row["bug_affected"] and consistent
        row["technical_usability_status"] = "KEEP" if keep else "UNRESOLVED"
        row["eligibility_basis"] = (
            "No explicit Bug token and repeated technical status fields are consistent" if keep else
            "Explicit Bug token present; reason/target safety unresolved" if row["bug_affected"] else
            "No explicit Bug token, but an approved technical status flag is contrary"
        )
    fractions = [float(row["first_bug_fraction_of_annotation_span"]) for row in result["affected"]]
    times = [float(row["first_bug_physical_time_seconds"]) for row in result["affected"]]
    ordinals = [int(row["first_bug_annotation_ordinal"]) for row in result["affected"]]
    usability = Counter(row["technical_usability_status"] for row in result["status_rows"])
    result["summary"].update({
        "bug_sequence_pattern_counts": dict(sorted(pattern_counts.items())),
        "timing_enrichment": {"affected_with_confirmed_frame_iter_time_mapping": len(result["affected"]),
            "first_bug_annotation_ordinal_min": min(ordinals),
            "first_bug_annotation_ordinal_median": statistics.median(ordinals),
            "first_bug_annotation_ordinal_max": max(ordinals),
            "first_bug_fraction_min": min(fractions), "first_bug_fraction_median": statistics.median(fractions),
            "first_bug_fraction_max": max(fractions), "first_bug_physical_time_seconds_min": min(times),
            "first_bug_physical_time_seconds_median": statistics.median(times),
            "first_bug_physical_time_seconds_max": max(times), "near_beginning_cutoff": "NOT_DEFINED"},
        "usability_counts": {name: usability.get(name, 0) for name in ("KEEP", "KEEP_WITH_TRUNCATION", "EXCLUDE", "UNRESOLVED")},
        "clearly_usable_whole_run_cohort": usability.get("KEEP", 0),
        "bounds_integrity": "NOT_COMPLETED_REMOTE_FETCH_TIMEOUT; no integrity or eligibility inference",
        "source_hash_column": "EMPTY_FOR_ALL_185_ROWS; pinned file SHA-256 plus simulation IDs provide provenance",
    })
    with manifest.open(encoding="utf-8", newline="") as stream: rows = list(csv.DictReader(stream))
    keep = {row["simulation_id"] for row in result["status_rows"] if row["technical_usability_status"] == "KEEP"}
    selected = [row for row in rows if row["sim_id"] in keep]
    groups = sorted(row["group_token"] for row in selected)
    if len(groups) != len(keep) or len(set(groups)) != len(groups):
        raise ValueError("B80 witness requires one unique exact-configuration group per KEEP simulation")
    cohort = len(groups)
    shuffled = groups.copy(); random.Random(1101).shuffle(shuffled); assignment = {group: index % 5 for index, group in enumerate(shuffled)}
    held = {str(fold): sum(value == fold for value in assignment.values()) for fold in range(5)}
    result["b80_witness"] = {"status": "ADVISORY_NOT_APPROVED", "seed": 1101,
        "grouping": "accepted exact-configuration singleton groups",
        "independent_campaign_or_solver_grouping": "UNRESOLVED_SEPARATE_ARRIVAL_GATE",
        "assignment_algorithm": "Python random.Random(seed).shuffle(sorted(group IDs)); fold=index modulo 5",
        "eligible_whole_run_count": cohort, "held_out_group_counts": held,
        "training_group_counts": {fold: cohort - count for fold, count in held.items()},
        "B80_structurally_feasible": min(cohort - count for count in held.values()) >= 80,
        "assignment_sha256": hashlib.sha256("\n".join(f"{g},{assignment[g]}" for g in groups).encode()).hexdigest(),
        "fold_by_group": assignment}
    return result


def write_outputs(result: Mapping[str, Any], output_dir: Path, technical_provenance: Mapping[str, Any] | None = None) -> None:
    """Write the complete sanitized audit atomically to a new directory."""
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_csv(output_dir / "bug_affected_simulations.csv", result["affected"], tuple(result["affected"][0]))
    _write_csv(output_dir / "simulation_bug_status.csv", result["status_rows"], tuple(result["status_rows"][0]))
    _write_csv(output_dir / "bug_frames_projection.csv", result["bug_frames"], tuple(result["bug_frames"][0]))
    (output_dir / "bug_audit_summary.json").write_text(json.dumps(result["summary"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if technical_provenance is not None:
        _write_csv(output_dir / "prebug_numeric_integrity.csv", result["integrity"], tuple(result["integrity"][0]))
        (output_dir / "technical_payload_provenance.json").write_text(json.dumps(technical_provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (output_dir / "b80_structural_witness.json").write_text(json.dumps(result["b80_witness"], indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path); parser.add_argument("output_dir", type=Path)
    parser.add_argument("--mixed-csv", type=Path, help="Offline/test source; never copied")
    parser.add_argument("--monitor-metadata", type=Path)
    parser.add_argument("--directory-metadata", type=Path)
    args = parser.parse_args()
    result = project_bug_only(args.mixed_csv.read_bytes() if args.mixed_csv else fetch_pinned_bytes(), _ids(args.manifest))
    technical_provenance = None
    if args.monitor_metadata or args.directory_metadata:
        if not (args.monitor_metadata and args.directory_metadata): raise ValueError("both metadata paths are required")
        enriched = enrich_technical_timing(result["affected"], result["bug_frames"],
            json.loads(args.monitor_metadata.read_text()), json.loads(args.directory_metadata.read_text()), include_bounds=False)
        result["affected"], result["bug_frames"], result["integrity"] = enriched["affected"], enriched["bug_frames"], enriched["integrity"]
        technical_provenance = {"unique_payload_downloads": enriched["unique_payload_downloads"], "payloads": enriched["provenance"]}
    if technical_provenance is not None: result = finalize_result(result, args.manifest)
    write_outputs(result, args.output_dir, technical_provenance)
    return 0


if __name__ == "__main__": raise SystemExit(main())
