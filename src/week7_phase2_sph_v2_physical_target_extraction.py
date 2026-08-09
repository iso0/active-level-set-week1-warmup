"""Week 7 Phase 2: migrate and validate the Week 6 target extraction.

The code reuses the executable Week 6 constants and rolling-window helpers.
Only the repository-layout compatibility layer is new: ``sph_v2`` experiment
folders are semantic names at repository root and no longer contain
``experiment_details.json``.  The mapping from folder ``min(XF, XL)`` to the
former domain maximum is verified on all exact Week 6 matches before it is used.

No predictive model is fitted in this module.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import time
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.week6_phase1_melt_pool_data_audit import (
    ACTIVE_DOMAIN_FRACTION,
    LATE_WINDOW_FRACTION,
    MIN_LATE_ROWS,
    SENTINEL_THRESHOLD,
    _window_cv_trend,
)
from src.week6_phase3_5_regime_target_design import (
    END_MARGIN_M,
    PRIMARY_PERSISTENCE_WINDOW_UM,
    PRIMARY_WIDTH_GUARD_M,
    STARTUP_MARGIN_M,
    rolling_distance_stat,
    safe_ratio,
)
from src.week7_sph_v2_common import (
    FEATURE_UNITS,
    PARTITION_ORDER,
    RAW_ROOT,
    ROOT,
    SPH_V2_REPO_ID,
    SPH_V2_REVISION,
    WEEK6_BASE_COMMIT,
    WEEK6_RAW_ROOT,
    WEEK6_REVISION,
    download_pinned_files,
    ensure_no_modelling_imports,
    git_blob_sha1,
    load_partition_labels,
    notebook_has_errors,
    output_manifest,
    sha256_file,
    utc_now,
    write_csv,
    write_json,
)


OUTPUT_DIR = ROOT / "outputs" / "week7_02_sph_v2_target_extraction"
SMOKE_DIR = OUTPUT_DIR / "smoke"
PHASE1_DIR = ROOT / "outputs" / "week7_01_sph_v2_audit"
NOTEBOOK_PATH = ROOT / "notebooks" / "week_07" / "02_sph_v2_physical_target_extraction.ipynb"
WEEK6_LEDGER = ROOT / "outputs" / "week6_01_melt_pool_data_audit" / "week6_phase1_simulation_level_responses.csv"
WEEK6_PHASE4_TARGETS = ROOT / "outputs" / "week6_04_new_outputs_feature_effects" / "phase4_simulation_level_targets.csv"
WEEK6_EXACT_MAP_ARTIFACT = OUTPUT_DIR / "week6_exact_identifier_map.csv"
SUPERVISOR_CORRECTION_BASELINE = OUTPUT_DIR / "supervisor_correction_baseline_targets.parquet"

REQUIRED_MONITORS = [
    "position-bounds_melt.dat",
    "time.dat",
    "iter.dat",
    "kinetic-energy_melt.dat",
]
MONITOR_METADATA = {
    "position-bounds_melt.dat": {
        "source_unit": "m",
        "reported_unit_or_use": "derived width/length/depth/height reported in µm",
        "timestep_or_index_interpretation": "one six-column x/y/z min/max row per geometry monitor row",
        "physical_semantics": "axis-aligned bounds of the melt subset",
    },
    "time.dat": {
        "source_unit": "s",
        "reported_unit_or_use": "s (plots additionally show ms)",
        "timestep_or_index_interpretation": "strictly increasing physical monitor time aligned row-for-row to geometry",
        "physical_semantics": "simulation time",
    },
    "iter.dat": {
        "source_unit": "solver iteration (dimensionless index)",
        "reported_unit_or_use": "integer iteration used for exact label-timestep alignment",
        "timestep_or_index_interpretation": "strictly increasing solver iteration aligned row-for-row to geometry",
        "physical_semantics": "solver iteration identifier, not elapsed physical time",
    },
    "kinetic-energy_melt.dat": {
        "source_unit": "J",
        "reported_unit_or_use": "nJ",
        "timestep_or_index_interpretation": "instantaneous aggregate value aligned by monitor row",
        "physical_semantics": "aggregate kinetic energy of the melt subset; not cumulative",
    },
}
POSITION_BOUNDS_COLUMNS = ["x_min", "x_max", "y_min", "y_max", "z_min", "z_max"]
SOLVER_NO_MELT_SENTINEL_VALUE = float("3.402823e+38")
KNOWN_MALFORMED_NO_MELT_SENTINEL_TOKEN = "s3.402823e+38"
# This pattern recognizes one complete CSV field only.  It deliberately does
# not strip letters or otherwise coerce arbitrary malformed numeric strings.
KNOWN_MALFORMED_NO_MELT_SENTINEL_FIELD = re.compile(
    rb"(?m)(^|,)([ \t]*)s3\.402823e\+38(?=,|\r?$)"
)
PARTICLE_SPACING_M = 4e-6
DOMAIN_WALL_EXTENSION_M = 3 * PARTICLE_SPACING_M
ACTIVE_TOO_SHORT_ROWS = max(25, MIN_LATE_ROWS)

COLORS = {
    "new-data": "#D55E00",
    "old-data-local": "#0072B2",
    "old-data-remote-clean": "#009E73",
    "Keyhole": "#CC3311",
    "non-Keyhole": "#4477AA",
    "T0": "#6C8EBF",
    "active": "#A8DADC",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def phase1_path(smoke: bool, filename: str) -> Path:
    return (PHASE1_DIR / "smoke" if smoke else PHASE1_DIR) / filename


def load_phase1_inputs(smoke: bool) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    registry = pd.read_csv(phase1_path(smoke, "experiment_registry.csv"))
    sequence = pd.read_csv(phase1_path(smoke, "experiment_label_sequences.csv"))
    inventory = pd.read_parquet(phase1_path(smoke, "repository_file_inventory.parquet"))
    provenance_path = phase1_path(smoke, "dataset_provenance.json")
    if provenance_path.is_file():
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    else:
        # Phase 2 needs only the immutable revision guard from provenance.  The
        # fallback keeps this correction runnable if an unrelated untracked
        # Phase 1 reporting file is locally absent; it does not regenerate or
        # alter Phase 1 scientific outputs.
        phase1_summary = json.loads(phase1_path(smoke, "summary.json").read_text(encoding="utf-8"))
        provenance = {
            "analysis_revision": phase1_summary["revision"],
            "label_files": [],
        }
    require(provenance["analysis_revision"] == SPH_V2_REVISION, "Phase 1 revision differs from Phase 2")
    require(set(registry["experiment_name"]) == set(sequence["experiment_name"]), "Phase 1 populations disagree")
    return registry, sequence, inventory, pd.DataFrame(provenance["label_files"])


def week6_exact_name_map() -> pd.DataFrame:
    if WEEK6_EXACT_MAP_ARTIFACT.is_file():
        frame = pd.read_csv(WEEK6_EXACT_MAP_ARTIFACT)
        require(
            len(frame) == 241
            and frame["experiment_name"].is_unique
            and frame["week6_simulation_id"].is_unique,
            "Stored Week 6 exact-identifier map is malformed",
        )
        return frame
    rows: list[dict[str, Any]] = []
    if not WEEK6_RAW_ROOT.is_dir():
        raise RuntimeError(f"Week 6 raw cache is unavailable: {WEEK6_RAW_ROOT}")
    for metadata_path in sorted(WEEK6_RAW_ROOT.glob("sim_*/metadata.json")):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        rows.append(
            {
                "experiment_name": str(metadata["original_folder_name"]),
                "week6_simulation_id": metadata_path.parent.name,
                "week6_original_hash": str(metadata.get("original_hash", "")),
                "week6_metadata_path": str(metadata_path),
                "week6_metadata_sha256": sha256_file(metadata_path),
                "week6_dataset_revision": WEEK6_REVISION,
            }
        )
    frame = pd.DataFrame(rows)
    require(len(frame) == 241 and frame["experiment_name"].is_unique, "Unexpected Week 6 name map")
    return frame


def verify_domain_compatibility(registry: pd.DataFrame, name_map: pd.DataFrame) -> pd.DataFrame:
    week6 = pd.read_csv(WEEK6_LEDGER)[["simulation_id", "VX", "laser_exit_time_s"]]
    merged = registry.merge(name_map, on="experiment_name", how="inner").merge(
        week6, left_on="week6_simulation_id", right_on="simulation_id", how="left", suffixes=("", "_week6")
    )
    merged["week6_domain_max_reconstructed_m"] = merged["laser_exit_time_s"] * merged["VX_week6"]
    merged["sph_v2_folder_domain_max_m"] = merged[["XF", "XL"]].min(axis=1) + DOMAIN_WALL_EXTENSION_M
    merged["absolute_error_m"] = (
        merged["week6_domain_max_reconstructed_m"] - merged["sph_v2_folder_domain_max_m"]
    ).abs()
    merged["mapping_matches_week6"] = merged["absolute_error_m"] <= 1e-15
    merged["compatibility_rule"] = "domain_max_x = min(folder XF, folder XL) + 12 µm boundary-wall extension"
    return merged[
        [
            "experiment_name", "partition", "week6_simulation_id", "XF",
            "sph_v2_folder_domain_max_m", "week6_domain_max_reconstructed_m",
            "absolute_error_m", "mapping_matches_week6", "compatibility_rule",
        ]
    ].sort_values("week6_simulation_id")


def build_source_plan(
    registry: pd.DataFrame,
    inventory: pd.DataFrame,
    name_map: pd.DataFrame,
    *,
    workers: int,
) -> pd.DataFrame:
    """Prefer verified Week 6 bytes for exact matches; download all others pinned."""

    files = inventory[inventory["item_type"].eq("file")].copy()
    remote = files.set_index("path")
    old_lookup = name_map.set_index("experiment_name")["week6_simulation_id"].to_dict()
    rows: list[dict[str, Any]] = []
    download_names: list[str] = []

    for item in registry.itertuples(index=False):
        old_sim = old_lookup.get(item.experiment_name, "")
        for filename in REQUIRED_MONITORS:
            relative = f"{item.experiment_name}/monitor/{filename}"
            remote_exists = relative in remote.index
            remote_row = remote.loc[relative] if remote_exists else None
            remote_size = int(remote_row["size_bytes"]) if remote_exists and pd.notna(remote_row["size_bytes"]) else np.nan
            remote_blob = str(remote_row["blob_id"]) if remote_exists and pd.notna(remote_row["blob_id"]) else ""
            local_path = ""
            source_mode = "missing_in_pinned_sph_v2"
            local_blob = ""
            blob_verified = False
            if remote_exists and old_sim:
                candidate = WEEK6_RAW_ROOT / old_sim / "monitor" / filename
                if candidate.is_file() and candidate.stat().st_size == remote_size:
                    local_blob = git_blob_sha1(candidate)
                    if local_blob == remote_blob:
                        local_path = str(candidate)
                        source_mode = "week6_cache_verified_against_sph_v2_git_blob"
                        blob_verified = True
            if remote_exists and not local_path:
                source_mode = "pinned_sph_v2_download"
                download_names.append(relative)
            rows.append(
                {
                    "experiment_name": item.experiment_name,
                    "partition": item.partition,
                    "week6_simulation_id": old_sim,
                    "monitor_file": filename,
                    "sph_v2_relative_path": relative,
                    "remote_exists": remote_exists,
                    "remote_size_bytes": remote_size,
                    "remote_git_blob_id": remote_blob,
                    "local_path": local_path,
                    "source_mode": source_mode,
                    "local_git_blob_id": local_blob,
                    "local_blob_matches_pinned_sph_v2": blob_verified,
                    "exact_revision": SPH_V2_REVISION,
                }
            )

    downloaded = download_pinned_files(download_names, workers=workers, progress_every=20) if download_names else {}
    for row in rows:
        if row["source_mode"] != "pinned_sph_v2_download":
            continue
        path = downloaded[row["sph_v2_relative_path"]]
        local_blob = git_blob_sha1(path)
        row["local_path"] = str(path)
        row["local_git_blob_id"] = local_blob
        row["local_blob_matches_pinned_sph_v2"] = local_blob == row["remote_git_blob_id"]
    frame = pd.DataFrame(rows).sort_values(["partition", "experiment_name", "monitor_file"])
    return frame


def source_lookup(plan: pd.DataFrame) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(row.experiment_name), str(row.monitor_file)): row._asdict()
        for row in plan.itertuples(index=False)
    }


def enrich_monitor_compatibility(compatibility: pd.DataFrame) -> pd.DataFrame:
    """Attach explicit unit, index, and physical-semantics metadata."""

    frame = compatibility.copy()
    for column in [
        "source_unit",
        "reported_unit_or_use",
        "timestep_or_index_interpretation",
        "physical_semantics",
    ]:
        frame[column] = frame["monitor_file"].map(
            {name: metadata[column] for name, metadata in MONITOR_METADATA.items()}
        )
    return frame


def _empty_numeric_audit() -> dict[str, Any]:
    return {
        "known_malformed_no_melt_sentinel_count": 0,
        "known_malformed_no_melt_sentinel_locations": "[]",
        "known_malformed_no_melt_sentinel_rule_applied": False,
        "positive_solver_sentinel_count": 0,
        "negative_solver_sentinel_count": 0,
        "positive_solver_sentinel_column_counts": "[]",
        "negative_solver_sentinel_column_counts": "[]",
        "complete_no_melt_sentinel_row_count": 0,
        "partial_solver_sentinel_row_count": 0,
        "other_near_1e38_numeric_count": 0,
        "unrelated_malformed_token_coercion_count": 0,
    }


def load_numeric(path: Path, filename: str) -> tuple[np.ndarray, dict[str, Any]]:
    """Load one monitor and report any narrowly authorized compatibility use.

    Normal files still go directly through ``numpy.loadtxt``.  Only if bounds
    parsing fails do we inspect raw fields for the exact supervisor-confirmed
    token ``s3.402823e+38``.  Every complete occurrence of that exact field is
    replaced with the ordinary positive solver sentinel before parsing.  The
    unchanged Week 6 ``abs(value) < 1e30`` rule subsequently excludes its row.
    Any other malformed token continues to raise a parse error.
    """

    audit = _empty_numeric_audit()
    if filename != "position-bounds_melt.dat":
        return np.loadtxt(path, ndmin=1), audit

    try:
        values = np.loadtxt(path, delimiter=",", ndmin=2)
    except ValueError:
        raw = path.read_bytes()
        locations: list[dict[str, Any]] = []
        for row_index, line in enumerate(raw.splitlines()):
            for column_index, token in enumerate(line.split(b",")):
                if token.strip() == KNOWN_MALFORMED_NO_MELT_SENTINEL_TOKEN.encode("ascii"):
                    locations.append(
                        {
                            "row_index": row_index,
                            "row_number": row_index + 1,
                            "column_index": column_index,
                            "column": POSITION_BOUNDS_COLUMNS[column_index]
                            if column_index < len(POSITION_BOUNDS_COLUMNS)
                            else f"unexpected_column_{column_index}",
                        }
                    )

        def exact_replacement(match: re.Match[bytes]) -> bytes:
            return match.group(1) + match.group(2) + b"3.402823e+38"

        compatible_raw, replacement_count = KNOWN_MALFORMED_NO_MELT_SENTINEL_FIELD.subn(
            exact_replacement, raw
        )
        if not replacement_count or replacement_count != len(locations):
            raise
        # If another malformed token exists, this second strict load still
        # fails.  There is no generic letter stripping or permissive converter.
        values = np.loadtxt(io.BytesIO(compatible_raw), delimiter=",", ndmin=2)
        audit.update(
            {
                "known_malformed_no_melt_sentinel_count": replacement_count,
                "known_malformed_no_melt_sentinel_locations": json.dumps(
                    locations, separators=(",", ":")
                ),
                "known_malformed_no_melt_sentinel_rule_applied": True,
            }
        )

    positive = values == SOLVER_NO_MELT_SENTINEL_VALUE
    negative = values == -SOLVER_NO_MELT_SENTINEL_VALUE
    complete_no_melt = (
        positive[:, [0, 2, 4]].all(axis=1)
        & negative[:, [1, 3, 5]].all(axis=1)
    )
    any_solver_sentinel = (positive | negative).any(axis=1)
    near_1e38 = np.isfinite(values) & (np.abs(values) >= SENTINEL_THRESHOLD)
    audit.update(
        {
            "positive_solver_sentinel_count": int(positive.sum()),
            "negative_solver_sentinel_count": int(negative.sum()),
            "positive_solver_sentinel_column_counts": json.dumps(
                positive.sum(axis=0).astype(int).tolist(), separators=(",", ":")
            ),
            "negative_solver_sentinel_column_counts": json.dumps(
                negative.sum(axis=0).astype(int).tolist(), separators=(",", ":")
            ),
            "complete_no_melt_sentinel_row_count": int(complete_no_melt.sum()),
            "partial_solver_sentinel_row_count": int(
                (any_solver_sentinel & ~complete_no_melt).sum()
            ),
            "other_near_1e38_numeric_count": int(
                (near_1e38 & ~positive & ~negative).sum()
            ),
        }
    )
    return values, audit


def sentinel_audit_table(compatibility: pd.DataFrame) -> pd.DataFrame:
    """Summarize solver and textual sentinel variants across pinned bounds."""

    bounds = compatibility[
        compatibility["monitor_file"].eq("position-bounds_melt.dat")
        & compatibility["remote_exists"].astype(bool)
        & compatibility["schema_compatible"].astype(bool)
    ].copy()

    positive_columns = np.zeros(len(POSITION_BOUNDS_COLUMNS), dtype=np.int64)
    negative_columns = np.zeros(len(POSITION_BOUNDS_COLUMNS), dtype=np.int64)
    malformed_columns = np.zeros(len(POSITION_BOUNDS_COLUMNS), dtype=np.int64)
    malformed_experiments: list[str] = []
    malformed_locations: list[str] = []
    for row in bounds.itertuples(index=False):
        positive_counts = json.loads(row.positive_solver_sentinel_column_counts)
        negative_counts = json.loads(row.negative_solver_sentinel_column_counts)
        if len(positive_counts) == len(POSITION_BOUNDS_COLUMNS):
            positive_columns += np.asarray(positive_counts, dtype=np.int64)
        if len(negative_counts) == len(POSITION_BOUNDS_COLUMNS):
            negative_columns += np.asarray(negative_counts, dtype=np.int64)
        locations = json.loads(row.known_malformed_no_melt_sentinel_locations)
        if locations:
            malformed_experiments.append(str(row.experiment_name))
            for location in locations:
                column_index = int(location["column_index"])
                if 0 <= column_index < len(malformed_columns):
                    malformed_columns[column_index] += 1
                malformed_locations.append(
                    f"{row.experiment_name}: row {location['row_number']}, {location['column']}"
                )

    malformed_count = int(
        bounds["known_malformed_no_melt_sentinel_count"].sum()
    )
    # The exact textual variant becomes the ordinary positive sentinel only so
    # that the complete no-melt row can be parsed and excluded.  Subtract it
    # here to keep raw-token counts distinct in the audit table.
    standard_positive_columns = positive_columns - malformed_columns
    standard_positive_count = int(standard_positive_columns.sum())
    negative_count = int(negative_columns.sum())
    standard_files = int(
        (
            bounds["positive_solver_sentinel_count"]
            - bounds["known_malformed_no_melt_sentinel_count"]
        ).gt(0).sum()
    )
    negative_files = int(bounds["negative_solver_sentinel_count"].gt(0).sum())
    other_count = int(bounds["other_near_1e38_numeric_count"].sum())
    complete_rows = int(bounds["complete_no_melt_sentinel_row_count"].sum())
    partial_rows = int(bounds["partial_solver_sentinel_row_count"].sum())
    partial_files = int(bounds["partial_solver_sentinel_row_count"].gt(0).sum())

    def locations_text(counts: np.ndarray) -> str:
        return "; ".join(
            f"{column}={int(count)}"
            for column, count in zip(POSITION_BOUNDS_COLUMNS, counts)
            if count
        )

    rows = [
        {
            "token": "3.402823e+38",
            "count": standard_positive_count,
            "file_count": standard_files,
            "experiment_count": standard_files,
            "files_experiments_affected": f"{standard_files} present bounds files / experiments",
            "column_location": locations_text(standard_positive_columns),
            "numerically_parseable": True,
            "proposed_interpretation": "ordinary positive float32-max no-melt sentinel; never a physical minimum coordinate",
            "parser_action": "parse normally; exclude the entire row with the unchanged abs(value)<1e30 rule",
            "evidence_supervisor_clarification": (
                f"Supervisor confirmed ~1e38 means missing melt; {complete_rows - malformed_count} "
                "ordinary complete no-melt rows were observed."
            ),
        },
        {
            "token": "-3.402823e+38",
            "count": negative_count,
            "file_count": negative_files,
            "experiment_count": negative_files,
            "files_experiments_affected": f"{negative_files} present bounds files / experiments",
            "column_location": locations_text(negative_columns),
            "numerically_parseable": True,
            "proposed_interpretation": "ordinary negative float32-max no-melt sentinel; never a physical maximum coordinate",
            "parser_action": "parse normally; exclude the entire row with the unchanged abs(value)<1e30 rule",
            "evidence_supervisor_clarification": (
                f"Supervisor confirmed ~1e38 means missing melt; {partial_rows} partial-sentinel rows "
                f"occur in {partial_files} file(s) and remain invalid under the same Week 6 rule."
            ),
        },
        {
            "token": KNOWN_MALFORMED_NO_MELT_SENTINEL_TOKEN,
            "count": malformed_count,
            "file_count": len(set(malformed_experiments)),
            "experiment_count": len(set(malformed_experiments)),
            "files_experiments_affected": " | ".join(sorted(set(malformed_experiments))),
            "column_location": " | ".join(malformed_locations),
            "numerically_parseable": False,
            "proposed_interpretation": "exact textual variant of the positive no-melt sentinel",
            "parser_action": (
                "recognize this exact complete field only as +3.402823e+38, then exclude its row; "
                "do not strip arbitrary letters"
            ),
            "evidence_supervisor_clarification": (
                "The other five fields in the affected row are the ordinary alternating solver "
                "sentinels, following rows repeat that pattern, and the supervisor confirmed the semantics."
            ),
        },
        {
            "token": "other numeric/textual variants near 1e38",
            "count": other_count,
            "file_count": int(bounds["other_near_1e38_numeric_count"].gt(0).sum()),
            "experiment_count": int(bounds["other_near_1e38_numeric_count"].gt(0).sum()),
            "files_experiments_affected": "none found",
            "column_location": "none",
            "numerically_parseable": "not applicable",
            "proposed_interpretation": "none",
            "parser_action": "no compatibility rule; any unrelated malformed token remains a parse failure",
            "evidence_supervisor_clarification": (
                "All present pinned bounds files were parsed; no other near-1e38 numeric value was found "
                "and unrelated malformed-token coercion count is zero."
            ),
        },
    ]
    table = pd.DataFrame(rows)
    table.insert(0, "exact_sph_v2_revision", SPH_V2_REVISION)
    return table


CORRECTION_INVARIANCE_COLUMNS = [
    "T0_width_um",
    "T0_depth_um",
    "T0_total_height_um",
    "T0_kinetic_energy_nJ",
    "max_depth_um",
    "max_total_height_um",
    "max_kinetic_energy_nJ",
    "G3_persistent_depth_um",
    "R3_persistent_depth_width_ratio",
    "T0_start_row_index",
    "T0_end_row_index",
    "T0_start_time_s",
    "T0_end_time_s",
    "active_region_start_row_index",
    "active_region_end_row_index",
]


def capture_supervisor_correction_baseline(output_dir: Path) -> pd.DataFrame:
    """Persist the pre-clarification target table once for regression evidence."""

    baseline_path = output_dir / SUPERVISOR_CORRECTION_BASELINE.name
    if baseline_path.is_file():
        return pd.read_parquet(baseline_path)
    previous_path = output_dir / "sph_v2_simulation_level_targets.parquet"
    if not previous_path.is_file():
        return pd.DataFrame()
    baseline = pd.read_parquet(previous_path)
    baseline.to_parquet(baseline_path, index=False, compression="zstd")
    return baseline


def supervisor_correction_comparison(
    baseline: pd.DataFrame,
    current: pd.DataFrame,
    sentinel_experiments: set[str],
) -> pd.DataFrame:
    """Compare pre/post status and targets without assuming a fixed population."""

    if baseline.empty:
        return pd.DataFrame(
            columns=[
                "experiment_name",
                "partition_before",
                "partition_after",
                "status_changed",
                "changed_due_to_confirmed_sentinel_rule",
                "previous_valid_target_changed_unexpectedly",
            ]
        )
    label_columns = [
        "has_conduction",
        "has_keyhole",
        "first_keyhole_label_frame_index",
        "first_keyhole_timestep",
        "keyhole_frame_count",
        "keyhole_fraction_relevant_frames",
    ]
    shared = [
        column
        for column in CORRECTION_INVARIANCE_COLUMNS + label_columns
        if column in baseline.columns and column in current.columns
    ]
    before = baseline[
        [
            "experiment_name",
            "partition",
            "target_extraction_valid",
            "extraction_status",
            "extraction_failure_reasons",
            *shared,
        ]
    ].copy()
    after = current[
        [
            "experiment_name",
            "partition",
            "target_extraction_valid",
            "extraction_status",
            "extraction_failure_reasons",
            *shared,
        ]
    ].copy()
    comparison = before.merge(
        after,
        on="experiment_name",
        how="outer",
        suffixes=("_before", "_after"),
        validate="one_to_one",
        indicator=True,
    )
    comparison["status_changed"] = (
        comparison["target_extraction_valid_before"].fillna(False).astype(bool)
        != comparison["target_extraction_valid_after"].fillna(False).astype(bool)
    )
    comparison["changed_due_to_confirmed_sentinel_rule"] = (
        comparison["status_changed"]
        & comparison["experiment_name"].isin(sentinel_experiments)
    )

    unexpected_change = np.zeros(len(comparison), dtype=bool)
    label_change = np.zeros(len(comparison), dtype=bool)
    for column in shared:
        left = comparison[f"{column}_before"]
        right = comparison[f"{column}_after"]
        if column in label_columns:
            equal = left.fillna("<NA>").astype(str).eq(
                right.fillna("<NA>").astype(str)
            )
            label_change |= ~equal.to_numpy()
            continue
        left_numeric = pd.to_numeric(left, errors="coerce")
        right_numeric = pd.to_numeric(right, errors="coerce")
        tolerance = 1e-15 if column.endswith("_time_s") else 0.0 if "row_index" in column else 1e-10 if "kinetic" in column else 1e-8
        equal = np.isclose(
            left_numeric.to_numpy(float),
            right_numeric.to_numpy(float),
            rtol=0,
            atol=tolerance,
            equal_nan=True,
        )
        comparison[f"difference_{column}"] = right_numeric - left_numeric
        unexpected_change |= ~equal
    comparison["label_context_changed"] = label_change
    comparison["previous_valid_target_changed_unexpectedly"] = (
        comparison["target_extraction_valid_before"].fillna(False).astype(bool)
        & unexpected_change
    )
    return comparison.sort_values(["status_changed", "experiment_name"], ascending=[False, True])


def locate_relative(index: int, start: int, end: int) -> str:
    if index < start:
        return "before_T0"
    if index > end:
        return "after_T0"
    return "inside_T0"


def scalar_window_stats(values: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    selected = values[mask & np.isfinite(values)]
    if not len(selected):
        return {"median": np.nan, "mean": np.nan, "variance": np.nan, "std": np.nan, "cv": np.nan, "relative_trend": np.nan, "count": 0}
    cv, trend = _window_cv_trend(selected)
    return {
        "median": float(np.median(selected)),
        "mean": float(np.mean(selected)),
        "variance": float(np.var(selected, ddof=1)) if len(selected) > 1 else 0.0,
        "std": float(np.std(selected, ddof=1)) if len(selected) > 1 else 0.0,
        "cv": cv,
        "relative_trend": trend,
        "count": int(len(selected)),
    }


def base_target_row(item: pd.Series, seq: pd.Series, old_sim: str) -> dict[str, Any]:
    return {
        "experiment_name": item["experiment_name"],
        "partition": item["partition"],
        "week6_simulation_id": old_sim,
        "exact_sph_v2_revision": SPH_V2_REVISION,
        "P_W": float(item["P"]),
        "VX_m_per_s": float(item["VX"]),
        "LS_m": float(item["LS"]),
        "LS_um": float(item["LS"]) * 1e6,
        "ST_K": float(item["ST"]),
        "has_conduction": bool(seq["has_conduction"]),
        "has_keyhole": bool(seq["has_keyhole"]),
        "first_keyhole_label_frame_index": seq["first_keyhole_frame_index"],
        "first_keyhole_timestep": seq["first_keyhole_timestep"],
        "keyhole_frame_count": int(seq["keyhole_frame_count"]),
        "keyhole_fraction_relevant_frames": seq["keyhole_fraction_of_relevant_physical_frames"],
        "target_extraction_valid": False,
        "physical_target_extraction_success": False,
        "extraction_status": "FAIL",
        "extraction_failure_reasons": "not processed",
        "extraction_failure_reason": "not processed",
        "extraction_warning_reasons": "",
        "geometry_monitor_available": False,
        "geometry_parse_ok": False,
        "geometry_target_ready": False,
        "time_monitor_available": False,
        "time_parse_ok": False,
        "time_target_ready": False,
        "iteration_monitor_available": False,
        "iteration_parse_ok": False,
        "iteration_target_ready": False,
        "kinetic_energy_monitor_available": False,
        "kinetic_energy_parse_ok": False,
        "kinetic_energy_target_ready": False,
        "label_analysis_ready": True,
        "known_malformed_no_melt_sentinel_row_count": 0,
        "known_malformed_no_melt_sentinel_rows_excluded": True,
        "source_label_modified": False,
        "simulation_silently_removed": False,
    }


def set_extraction_outcome(
    target: dict[str, Any],
    failures: Sequence[str],
    warnings: Sequence[str],
    *,
    success: bool,
) -> None:
    failure_text = "; ".join(sorted(set(failures)))
    warning_text = "; ".join(sorted(set(warnings)))
    target.update(
        {
            "target_extraction_valid": success,
            "physical_target_extraction_success": success,
            "extraction_status": "WARNING" if success and warning_text else "PASS" if success else "FAIL",
            "extraction_failure_reasons": failure_text,
            "extraction_failure_reason": failure_text,
            "extraction_warning_reasons": warning_text,
        }
    )


def extract_one(
    item: pd.Series,
    seq: pd.Series,
    label_rows: pd.DataFrame,
    plan_lookup: dict[tuple[str, str], dict[str, Any]],
    old_sim: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    name = str(item["experiment_name"])
    target = base_target_row(item, seq, old_sim)
    compatibility: list[dict[str, Any]] = []
    raw: dict[str, np.ndarray] = {}
    numeric_audits: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    warnings: list[str] = []

    for filename in REQUIRED_MONITORS:
        source = plan_lookup[(name, filename)]
        prefix = {
            "position-bounds_melt.dat": "geometry",
            "time.dat": "time",
            "iter.dat": "iteration",
            "kinetic-energy_melt.dat": "kinetic_energy",
        }[filename]
        target[f"{prefix}_monitor_available"] = bool(source["remote_exists"])
        row = {
            "experiment_name": name,
            "partition": item["partition"],
            "monitor_file": filename,
            "expected_columns": 6 if filename == "position-bounds_melt.dat" else 1,
            "source_mode": source["source_mode"],
            "remote_exists": bool(source["remote_exists"]),
            "remote_size_bytes": source["remote_size_bytes"],
            "remote_git_blob_id": source["remote_git_blob_id"],
            "local_blob_matches_pinned_sph_v2": bool(source["local_blob_matches_pinned_sph_v2"]),
            "local_path": source["local_path"],
            "schema_compatible": False,
            "row_count": np.nan,
            "column_count": np.nan,
            "nonfinite_count": np.nan,
            "negative_count": np.nan,
            "detail": "",
            **_empty_numeric_audit(),
        }
        if not source["remote_exists"]:
            row["detail"] = "File absent in exact pinned tree; no coercion attempted."
            failures.append(f"missing {filename}")
            compatibility.append(row)
            continue
        if not source["local_blob_matches_pinned_sph_v2"]:
            row["detail"] = "Local bytes do not match pinned remote Git blob."
            failures.append(f"unverified bytes for {filename}")
            compatibility.append(row)
            continue
        try:
            values, numeric_audit = load_numeric(Path(source["local_path"]), filename)
            raw[filename] = values
            numeric_audits[filename] = numeric_audit
            row.update(numeric_audit)
            if filename == "position-bounds_melt.dat":
                row["row_count"] = values.shape[0]
                row["column_count"] = values.shape[1]
                row["nonfinite_count"] = int((~np.isfinite(values)).sum())
                row["negative_count"] = np.nan
                row["schema_compatible"] = values.ndim == 2 and values.shape[1] == 6
            else:
                row["row_count"] = len(values)
                row["column_count"] = 1 if values.ndim == 1 else values.shape[1]
                row["nonfinite_count"] = int((~np.isfinite(values)).sum())
                row["negative_count"] = int((values < 0).sum()) if filename == "kinetic-energy_melt.dat" else np.nan
                row["schema_compatible"] = values.ndim == 1
            if numeric_audit["known_malformed_no_melt_sentinel_rule_applied"]:
                row["detail"] = (
                    "Parsed after recognizing only the exact supervisor-confirmed "
                    "s3.402823e+38 no-melt sentinel field; its row remains excluded "
                    "by the unchanged abs(value)<1e30 rule."
                )
            else:
                row["detail"] = "Parsed without structural coercion."
            if not row["schema_compatible"]:
                failures.append(f"schema changed for {filename}")
            target[f"{prefix}_parse_ok"] = bool(row["schema_compatible"])
        except Exception as exc:  # explicit row, never silent removal
            row["detail"] = f"parse error: {exc.__class__.__name__}: {exc}"
            failures.append(f"parse error for {filename}")
        compatibility.append(row)

    trace_metadata: dict[str, Any] = {}
    if failures:
        set_extraction_outcome(target, failures, warnings, success=False)
        return target, compatibility, trace_metadata

    bounds = raw["position-bounds_melt.dat"]
    time_s = raw["time.dat"]
    iterations = raw["iter.dat"]
    kinetic_j = raw["kinetic-energy_melt.dat"]
    n_rows = len(bounds)
    if not (len(time_s) == len(iterations) == n_rows):
        failures.append(
            f"bounds/time/iter row mismatch: {n_rows}/{len(time_s)}/{len(iterations)}"
        )
    if not np.all(np.diff(time_s) > 0):
        failures.append("time is not strictly increasing")
    if not np.all(np.diff(iterations) > 0):
        failures.append("iteration is not strictly increasing")
    target["time_target_ready"] = bool(
        len(time_s) == n_rows and np.all(np.diff(time_s) > 0)
    )
    target["iteration_target_ready"] = bool(
        len(iterations) == n_rows and np.all(np.diff(iterations) > 0)
    )
    finite = np.isfinite(bounds).all(axis=1)
    non_sentinel = (np.abs(bounds) < SENTINEL_THRESHOLD).all(axis=1)
    ordered_bounds = (
        (bounds[:, 1] >= bounds[:, 0])
        & (bounds[:, 3] >= bounds[:, 2])
        & (bounds[:, 5] >= bounds[:, 4])
    )
    malformed_bounds = finite & non_sentinel & ~ordered_bounds
    if malformed_bounds.any():
        failures.append(f"{int(malformed_bounds.sum())} finite non-sentinel rows have max < min")
    valid = finite & non_sentinel & ordered_bounds
    bounds_audit = numeric_audits["position-bounds_melt.dat"]
    sentinel_locations = json.loads(
        bounds_audit["known_malformed_no_melt_sentinel_locations"]
    )
    sentinel_row_indices = sorted({int(item["row_index"]) for item in sentinel_locations})
    target["known_malformed_no_melt_sentinel_row_count"] = len(sentinel_row_indices)
    target["known_malformed_no_melt_sentinel_rows_excluded"] = bool(
        all(0 <= index < len(valid) and not valid[index] for index in sentinel_row_indices)
    )
    target["geometry_target_ready"] = bool(valid.any() and not malformed_bounds.any())
    if not valid.any():
        failures.append("no valid melt-bound rows")
    if failures:
        set_extraction_outcome(target, failures, warnings, success=False)
        return target, compatibility, trace_metadata

    extents = np.full((n_rows, 3), np.nan)
    extents[valid] = bounds[valid][:, [1, 3, 5]] - bounds[valid][:, [0, 2, 4]]
    length_m = extents[:, 0]
    width_m = extents[:, 1]
    total_height_m = extents[:, 2]
    depth_m = np.full(n_rows, np.nan)
    depth_m[valid] = np.maximum(0.0, -bounds[valid, 4])
    z_max_m = np.full(n_rows, np.nan)
    z_max_m[valid] = bounds[valid, 5]

    domain_max_m = min(float(item["XF"]), float(item["XL"])) + DOMAIN_WALL_EXTENSION_M
    vx = float(item["VX"])
    laser_exit_time_s = domain_max_m / vx
    active_cutoff_s = min(float(time_s[-1]), ACTIVE_DOMAIN_FRACTION * laser_exit_time_s)
    first_valid_index = int(np.flatnonzero(valid)[0])
    first_valid_time_s = float(time_s[first_valid_index])
    active_mask = valid & (time_s <= active_cutoff_s)
    if not active_mask.any() or active_cutoff_s < first_valid_time_s:
        failures.append("no active region before the Week 6 90% domain cutoff")
        set_extraction_outcome(target, failures, warnings, success=False)
        return target, compatibility, trace_metadata
    selected_start_s = first_valid_time_s + (1 - LATE_WINDOW_FRACTION) * (
        active_cutoff_s - first_valid_time_s
    )
    t0_mask = valid & (time_s >= selected_start_s) & (time_s <= active_cutoff_s)
    fallback_used = False
    if t0_mask.sum() < MIN_LATE_ROWS:
        eligible = np.flatnonzero(active_mask)
        t0_mask = np.zeros(n_rows, dtype=bool)
        t0_mask[eligible[-min(MIN_LATE_ROWS, len(eligible)) :]] = True
        fallback_used = True
    active_indices = np.flatnonzero(active_mask)
    t0_indices = np.flatnonzero(t0_mask)
    t0_start, t0_end = int(t0_indices[0]), int(t0_indices[-1])

    kinetic_full = np.full(n_rows, np.nan)
    covered = np.arange(n_rows) < len(kinetic_j)
    kinetic_full[covered] = kinetic_j[np.arange(n_rows)[covered]]
    kinetic_valid = covered & np.isfinite(kinetic_full) & (kinetic_full >= 0)
    if not kinetic_valid[t0_mask].any():
        failures.append("kinetic-energy monitor has no valid T0 rows")
    if not covered[t0_mask].all():
        failures.append("kinetic-energy monitor does not cover the complete T0 window")
    if len(kinetic_j) != n_rows:
        warnings.append(f"kinetic-energy row count {len(kinetic_j)} differs from geometry {n_rows}")
    if failures:
        set_extraction_outcome(target, failures, warnings, success=False)
        return target, compatibility, trace_metadata
    target["kinetic_energy_target_ready"] = True

    response_arrays = {
        "width": width_m,
        "length": length_m,
        "depth": depth_m,
        "total_height": total_height_m,
        "kinetic_energy": kinetic_full,
    }
    units_to_report = {
        "width": 1e6,
        "length": 1e6,
        "depth": 1e6,
        "total_height": 1e6,
        "kinetic_energy": 1e9,
    }
    unit_names = {
        "width": "um", "length": "um", "depth": "um", "total_height": "um", "kinetic_energy": "nJ"
    }

    for response, values in response_arrays.items():
        report = values * units_to_report[response]
        response_valid = valid & np.isfinite(report)
        if response == "kinetic_energy":
            response_valid &= kinetic_valid
        stats = scalar_window_stats(report, t0_mask & response_valid)
        prefix = f"T0_{response}"
        target[f"{prefix}_{unit_names[response]}"] = stats["median"]
        target[f"{prefix}_mean_{unit_names[response]}"] = stats["mean"]
        target[f"{prefix}_variance_{unit_names[response]}2"] = stats["variance"]
        target[f"{prefix}_std_{unit_names[response]}"] = stats["std"]
        target[f"{prefix}_cv"] = stats["cv"]
        target[f"{prefix}_relative_trend"] = stats["relative_trend"]
        target[f"{prefix}_valid_sample_count"] = stats["count"]
        maximum_index = int(np.nanargmax(np.where(response_valid, report, np.nan)))
        target[f"max_{response}_{unit_names[response]}"] = float(report[maximum_index])
        target[f"max_{response}_row_index"] = maximum_index
        target[f"max_{response}_iteration"] = int(iterations[maximum_index])
        target[f"max_{response}_time_s"] = float(time_s[maximum_index])
        target[f"max_{response}_relative_to_T0"] = locate_relative(maximum_index, t0_start, t0_end)

    laser_x_m = vx * time_s
    normalized_s = laser_x_m / domain_max_m
    valid_x = laser_x_m[valid]
    onset_x = float(valid_x[0])
    last_active_x = float(valid_x[-1])
    adaptive_start_x = onset_x + STARTUP_MARGIN_M
    adaptive_end_x = min(last_active_x, domain_max_m) - END_MARGIN_M
    adaptive_mask = valid & (laser_x_m >= adaptive_start_x) & (laser_x_m <= adaptive_end_x)
    ratio, ratio_reason = safe_ratio(depth_m, width_m, PRIMARY_WIDTH_GUARD_M)
    if adaptive_mask.any():
        adaptive_indices = np.flatnonzero(adaptive_mask)
        roll_depth, roll_count, roll_span, _ = rolling_distance_stat(
            laser_x_m[adaptive_indices], depth_m[adaptive_indices], PRIMARY_PERSISTENCE_WINDOW_UM * 1e-6
        )
        roll_ratio, _, _, _ = rolling_distance_stat(
            laser_x_m[adaptive_indices], ratio[adaptive_indices], PRIMARY_PERSISTENCE_WINDOW_UM * 1e-6
        )
        target["G3_persistent_depth_um"] = float(np.nanmax(roll_depth) * 1e6) if np.isfinite(roll_depth).any() else np.nan
        target["R3_persistent_depth_width_ratio"] = float(np.nanmax(roll_ratio)) if np.isfinite(roll_ratio).any() else np.nan
        target["G3_event_row_index"] = int(adaptive_indices[int(np.nanargmax(roll_depth))]) if np.isfinite(roll_depth).any() else np.nan
        target["R3_event_row_index"] = int(adaptive_indices[int(np.nanargmax(roll_ratio))]) if np.isfinite(roll_ratio).any() else np.nan
        target["rolling_50um_median_observation_count"] = float(np.nanmedian(roll_count[np.isfinite(roll_depth)])) if np.isfinite(roll_depth).any() else np.nan
        target["rolling_50um_median_span_um"] = float(np.nanmedian(roll_span[np.isfinite(roll_depth)]) * 1e6) if np.isfinite(roll_depth).any() else np.nan
    else:
        target["G3_persistent_depth_um"] = np.nan
        target["R3_persistent_depth_width_ratio"] = np.nan
        target["G3_event_row_index"] = np.nan
        target["R3_event_row_index"] = np.nan
        target["rolling_50um_median_observation_count"] = np.nan
        target["rolling_50um_median_span_um"] = np.nan
        warnings.append("adaptive active interior unavailable")

    iteration_lookup = {int(value): index for index, value in enumerate(iterations.astype(int))}
    ordered_labels = label_rows.sort_values(["timestep", "frame_row_in_partition"], kind="stable")
    missing_alignments = [int(value) for value in ordered_labels["timestep"] if int(value) not in iteration_lookup]
    target["label_timestep_exact_alignment_count"] = len(ordered_labels) - len(missing_alignments)
    target["label_timestep_unmatched_count"] = len(missing_alignments)
    target["label_timestep_alignment_exact"] = not missing_alignments
    target["unmatched_label_timesteps"] = json.dumps(missing_alignments, separators=(",", ":"))
    keyhole_rows = [
        iteration_lookup[int(value)]
        for value in ordered_labels.loc[ordered_labels["label_final"].eq("Keyhole"), "timestep"]
        if int(value) in iteration_lookup
    ]
    target["first_keyhole_monitor_row_index"] = min(keyhole_rows) if keyhole_rows else np.nan
    target["keyhole_frames_before_T0"] = sum(index < t0_start for index in keyhole_rows)
    target["keyhole_frames_inside_T0"] = sum(t0_start <= index <= t0_end for index in keyhole_rows)
    target["keyhole_frames_after_T0"] = sum(index > t0_end for index in keyhole_rows)
    target["keyhole_overlaps_T0"] = target["keyhole_frames_inside_T0"] > 0
    if not keyhole_rows:
        target["keyhole_timing_relative_to_T0"] = "no_Keyhole"
    else:
        categories = {
            locate_relative(index, t0_start, t0_end) for index in keyhole_rows
        }
        target["keyhole_timing_relative_to_T0"] = next(iter(categories)) if len(categories) == 1 else "spans_multiple_T0_regions"
    if missing_alignments:
        warnings.append(f"{len(missing_alignments)} label timesteps do not exactly match iter.dat")

    target.update(
        {
            "monitor_row_count": n_rows,
            "kinetic_monitor_row_count": len(kinetic_j),
            "valid_melt_row_count": int(valid.sum()),
            "sentinel_or_invalid_melt_row_count": int((~valid).sum()),
            "active_region_start_row_index": int(active_indices[0]),
            "active_region_end_row_index": int(active_indices[-1]),
            "active_region_start_time_s": float(time_s[active_indices[0]]),
            "active_region_end_time_s": float(time_s[active_indices[-1]]),
            "active_region_sample_count": len(active_indices),
            "active_region_fraction_of_monitor": len(active_indices) / n_rows,
            "active_region_too_short": len(active_indices) < ACTIVE_TOO_SHORT_ROWS,
            "T0_start_row_index": t0_start,
            "T0_end_row_index": t0_end,
            "T0_start_iteration": int(iterations[t0_start]),
            "T0_end_iteration": int(iterations[t0_end]),
            "T0_start_time_s": float(time_s[t0_start]),
            "T0_end_time_s": float(time_s[t0_end]),
            "T0_sample_count": len(t0_indices),
            "T0_fallback_last_rows_used": fallback_used,
            "T0_inside_active_region": bool(t0_mask[active_mask].sum() == t0_mask.sum()),
            "cooling_rows_selected_in_T0": int((t0_mask & ~active_mask).sum()),
            "domain_max_x_m": domain_max_m,
            "laser_exit_time_s": laser_exit_time_s,
            "active_cutoff_time_s": active_cutoff_s,
            "recording_ends_before_90pct_domain": bool(float(time_s[-1]) < ACTIVE_DOMAIN_FRACTION * laser_exit_time_s),
            "length_flat_or_decreasing_across_active_region": bool(
                length_m[active_indices[-1]] <= length_m[active_indices[0]]
            ),
            "flag_primary_window_unstable_week6_rule": bool(
                target["T0_width_cv"] > 0.10
                or target["T0_length_cv"] > 0.10
                or target["T0_depth_cv"] > 0.15
            ),
            "width_formula": "y_max - y_min",
            "depth_formula": "max(0, -z_min)",
            "total_height_formula": "z_max - z_min",
            "kinetic_energy_semantics": "instantaneous aggregate melt-subset kinetic energy; source J, reported nJ",
            "T0_definition": "median over final 20% of valid melt-present time before 90% +X-domain cutoff",
            "active_region_definition": "valid melt rows from first valid melt through min(recording end, 90% laser-domain-exit time)",
            "length_is_primary_target": False,
            "length_retained_as_diagnostic": True,
            "minimum_z_max_inside_T0_um": float(np.nanmin(z_max_m[t0_mask]) * 1e6),
            "source_bundle_git_blob_sha256": hashlib.sha256(
                "\n".join(
                    plan_lookup[(name, filename)]["remote_git_blob_id"] for filename in REQUIRED_MONITORS
                ).encode()
            ).hexdigest(),
        }
    )
    set_extraction_outcome(target, failures, warnings, success=True)
    max_depth = target["max_depth_um"]
    g3 = target["G3_persistent_depth_um"]
    target["max_depth_minus_G3_um"] = max_depth - g3 if np.isfinite(g3) else np.nan
    target["max_depth_over_G3"] = max_depth / g3 if np.isfinite(g3) and g3 > 0 else np.nan
    max_depth_index = int(target["max_depth_row_index"])
    target["width_at_max_depth_um"] = float(width_m[max_depth_index] * 1e6)
    target["total_height_at_max_depth_um"] = float(total_height_m[max_depth_index] * 1e6)
    target["depth_ambiguity_score"] = (
        max(0.0, target["max_depth_minus_G3_um"]) * max(1.0, target["max_depth_over_G3"])
        if np.isfinite(target["max_depth_minus_G3_um"]) and np.isfinite(target["max_depth_over_G3"])
        else np.nan
    )
    target["flag_depth_bounding_box_ambiguity_candidate"] = bool(
        np.isfinite(target["max_depth_minus_G3_um"])
        and target["max_depth_minus_G3_um"] > 20.0
        and target["max_depth_over_G3"] > 1.25
    )

    trace_metadata = {
        "bounds": bounds,
        "time_s": time_s,
        "iterations": iterations,
        "valid": valid,
        "active_mask": active_mask,
        "t0_mask": t0_mask,
        "width_m": width_m,
        "length_m": length_m,
        "depth_m": depth_m,
        "total_height_m": total_height_m,
        "kinetic_j": kinetic_full,
        "laser_x_m": laser_x_m,
        "normalized_s": normalized_s,
        "ratio_valid": ratio_reason == "valid",
    }
    return target, compatibility, trace_metadata


def extract_population(
    registry: pd.DataFrame,
    sequence: pd.DataFrame,
    labels: pd.DataFrame,
    plan: pd.DataFrame,
    name_map: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, dict[str, Any]]]:
    lookup = source_lookup(plan)
    old_lookup = name_map.set_index("experiment_name")["week6_simulation_id"].to_dict()
    seq_lookup = sequence.set_index("experiment_name")
    targets: list[dict[str, Any]] = []
    compatibility: list[dict[str, Any]] = []
    # Full traces are intentionally not retained for all experiments: the
    # complete population contains tens of millions of monitor rows.  A small
    # deterministic representative set is reconstructed after scalar selection.
    traces: dict[str, dict[str, Any]] = {}
    for position, (_, item) in enumerate(registry.sort_values(["partition", "experiment_name"]).iterrows(), start=1):
        name = str(item["experiment_name"])
        target, monitor_rows, trace = extract_one(
            item,
            seq_lookup.loc[name],
            labels[labels["experiment_name"].eq(name)],
            lookup,
            old_lookup.get(name, ""),
        )
        targets.append(target)
        compatibility.extend(monitor_rows)
        if position % 20 == 0 or position == len(registry):
            print(f"Target extraction: {position}/{len(registry)}", flush=True)
    return pd.DataFrame(targets), pd.DataFrame(compatibility), traces


def reconstruct_representative_traces(
    representatives: pd.DataFrame,
    registry: pd.DataFrame,
    sequence: pd.DataFrame,
    labels: pd.DataFrame,
    plan: pd.DataFrame,
    name_map: pd.DataFrame,
) -> dict[str, dict[str, Any]]:
    lookup = source_lookup(plan)
    old_lookup = name_map.set_index("experiment_name")["week6_simulation_id"].to_dict()
    registry_lookup = registry.set_index("experiment_name")
    sequence_lookup = sequence.set_index("experiment_name")
    traces: dict[str, dict[str, Any]] = {}
    for name in representatives["experiment_name"]:
        if name not in registry_lookup.index:
            continue
        item = registry_lookup.loc[name].copy()
        item["experiment_name"] = name
        _, _, trace = extract_one(
            item,
            sequence_lookup.loc[name],
            labels[labels["experiment_name"].eq(name)],
            lookup,
            old_lookup.get(name, ""),
        )
        if trace:
            traces[name] = trace
    return traces


def old_new_comparison(targets: pd.DataFrame, name_map: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    del name_map  # matching is already exact and recorded on each target row
    old_phase4 = pd.read_csv(WEEK6_PHASE4_TARGETS)[
        [
            "simulation_id", "T0_melt_pool_width_um", "T0_penetration_depth_um",
            "T0_total_vertical_height_um", "T0_melt_pool_kinetic_energy_nJ",
        ]
    ].rename(columns={"simulation_id": "week6_simulation_id"})
    old_ledger = pd.read_csv(WEEK6_LEDGER)[
        [
            "simulation_id", "selected_window_start_row_index",
            "selected_window_end_row_index", "selected_window_start_time_s",
            "selected_window_end_time_s",
        ]
    ].rename(columns={"simulation_id": "week6_simulation_id"})
    match = targets[
        targets["week6_simulation_id"].fillna("").astype(str).str.len().gt(0)
        & targets["target_extraction_valid"].astype(bool)
    ].merge(old_phase4, on="week6_simulation_id", how="left").merge(
        old_ledger, on="week6_simulation_id", how="left"
    )
    pairs = {
        "width_um": ("T0_width_um", "T0_melt_pool_width_um"),
        "depth_um": ("T0_depth_um", "T0_penetration_depth_um"),
        "total_height_um": ("T0_total_height_um", "T0_total_vertical_height_um"),
        "kinetic_energy_nJ": ("T0_kinetic_energy_nJ", "T0_melt_pool_kinetic_energy_nJ"),
    }
    rows: list[dict[str, Any]] = []
    for row in match.itertuples(index=False):
        result = {
            "experiment_name": row.experiment_name,
            "partition": row.partition,
            "week6_simulation_id": row.week6_simulation_id,
            "new_T0_start_row_index": row.T0_start_row_index,
            "old_T0_start_row_index": row.selected_window_start_row_index,
            "new_T0_end_row_index": row.T0_end_row_index,
            "old_T0_end_row_index": row.selected_window_end_row_index,
            "new_T0_start_time_s": row.T0_start_time_s,
            "old_T0_start_time_s": row.selected_window_start_time_s,
            "new_T0_end_time_s": row.T0_end_time_s,
            "old_T0_end_time_s": row.selected_window_end_time_s,
        }
        for label, (new_column, old_column) in pairs.items():
            new_value = getattr(row, new_column)
            old_value = getattr(row, old_column)
            result[f"new_{label}"] = new_value
            result[f"old_{label}"] = old_value
            result[f"difference_{label}"] = new_value - old_value
            result[f"relative_difference_{label}"] = (new_value - old_value) / old_value if old_value != 0 else np.nan
            tolerance = 1e-8 if label != "kinetic_energy_nJ" else 1e-10
            result[f"identical_within_tolerance_{label}"] = bool(np.isclose(new_value, old_value, rtol=0, atol=tolerance))
        result["window_endpoints_identical"] = bool(
            row.T0_start_row_index == row.selected_window_start_row_index
            and row.T0_end_row_index == row.selected_window_end_row_index
            and np.isclose(row.T0_start_time_s, row.selected_window_start_time_s, rtol=0, atol=1e-15)
            and np.isclose(row.T0_end_time_s, row.selected_window_end_time_s, rtol=0, atol=1e-15)
        )
        rows.append(result)
    comparison = pd.DataFrame(rows).sort_values("week6_simulation_id")
    summary_rows = []
    for label in pairs:
        finite = comparison[[f"new_{label}", f"old_{label}"]].dropna()
        summary_rows.append(
            {
                "target": label,
                "exact_match_count": len(finite),
                "pearson_correlation": finite[f"new_{label}"].corr(finite[f"old_{label}"]),
                "maximum_absolute_difference": comparison[f"difference_{label}"].abs().max(),
                "median_absolute_difference": comparison[f"difference_{label}"].abs().median(),
                "identical_within_tolerance_count": int(comparison[f"identical_within_tolerance_{label}"].sum()),
                "materially_changed_count": int((~comparison[f"identical_within_tolerance_{label}"]).sum()),
            }
        )
    return comparison, pd.DataFrame(summary_rows)


def descriptive_target_summary(targets: pd.DataFrame) -> pd.DataFrame:
    columns = ["T0_width_um", "T0_depth_um", "T0_total_height_um", "T0_kinetic_energy_nJ", "max_depth_um", "max_total_height_um", "max_kinetic_energy_nJ"]
    rows = []
    groups: list[tuple[str, pd.DataFrame]] = [("overall", targets)]
    groups.extend((f"partition={partition}", targets[targets["partition"].eq(partition)]) for partition in PARTITION_ORDER)
    groups.extend((f"has_keyhole={value}", targets[targets["has_keyhole"].eq(value)]) for value in [False, True])
    for group, subset in groups:
        for column in columns:
            values = pd.to_numeric(subset[column], errors="coerce")
            finite = values[np.isfinite(values)]
            rows.append(
                {
                    "group": group,
                    "target": column,
                    "row_count": len(values),
                    "finite_count": len(finite),
                    "missing_count": len(values) - len(finite),
                    "min": finite.min() if len(finite) else np.nan,
                    "q05": finite.quantile(0.05) if len(finite) else np.nan,
                    "q25": finite.quantile(0.25) if len(finite) else np.nan,
                    "median": finite.median() if len(finite) else np.nan,
                    "mean": finite.mean() if len(finite) else np.nan,
                    "q75": finite.quantile(0.75) if len(finite) else np.nan,
                    "q95": finite.quantile(0.95) if len(finite) else np.nan,
                    "max": finite.max() if len(finite) else np.nan,
                    "std": finite.std(ddof=1) if len(finite) > 1 else np.nan,
                }
            )
    return pd.DataFrame(rows)


def extraction_anomalies(targets: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in targets.itertuples(index=False):
        reasons: list[tuple[str, str, str]] = []
        if not row.target_extraction_valid:
            reasons.append(("extraction_failed", "FAIL", row.extraction_failure_reasons))
        else:
            if row.extraction_status == "WARNING":
                reasons.append(("extraction_warning", "WARNING", row.extraction_warning_reasons))
            if row.active_region_too_short:
                reasons.append(("active_region_too_short", "WARNING", f"{row.active_region_sample_count} rows"))
            if row.recording_ends_before_90pct_domain:
                reasons.append(("recording_ends_before_90pct_domain", "WARNING", "T0 ends at recording end under the exact Week 6 min rule"))
            if row.length_flat_or_decreasing_across_active_region:
                reasons.append(("length_flat_or_decreasing", "WARNING", "end length <= start length inside active region"))
            if row.flag_primary_window_unstable_week6_rule:
                reasons.append(("week6_window_instability", "WARNING", f"CV width={row.T0_width_cv:.3g}, length={row.T0_length_cv:.3g}, depth={row.T0_depth_cv:.3g}"))
            if row.flag_depth_bounding_box_ambiguity_candidate:
                reasons.append(("depth_bounding_box_ambiguity_candidate", "WARNING", f"max-G3={row.max_depth_minus_G3_um:.3f} µm; max/G3={row.max_depth_over_G3:.3f}"))
        for reason, severity, detail in reasons:
            rows.append(
                {
                    "severity": severity,
                    "reason": reason,
                    "partition": row.partition,
                    "experiment_name": row.experiment_name,
                    "week6_simulation_id": row.week6_simulation_id,
                    "detail": detail,
                    "source_data_removed": False,
                }
            )
    return pd.DataFrame(rows, columns=["severity", "reason", "partition", "experiment_name", "week6_simulation_id", "detail", "source_data_removed"])


def depth_ambiguity_table(targets: pd.DataFrame, inventory: pd.DataFrame) -> pd.DataFrame:
    valid = targets[targets["target_extraction_valid"]].copy()
    valid = valid.sort_values(["flag_depth_bounding_box_ambiguity_candidate", "depth_ambiguity_score"], ascending=[False, False])
    gif_paths = (
        inventory[inventory["path"].str.endswith("/gif_files/animation_ss_side.gif")]
        .assign(experiment_name=lambda frame: frame["path"].str.split("/").str[0])
        .set_index("experiment_name")["path"].to_dict()
    )
    columns = [
        "experiment_name", "partition", "week6_simulation_id", "has_keyhole",
        "max_depth_um", "T0_depth_um", "G3_persistent_depth_um",
        "max_depth_minus_G3_um", "max_depth_over_G3", "width_at_max_depth_um",
        "total_height_at_max_depth_um", "depth_ambiguity_score",
        "flag_depth_bounding_box_ambiguity_candidate", "max_depth_row_index",
        "max_depth_iteration", "max_depth_time_s",
    ]
    table = valid[columns].copy()
    table["gif_path_in_repository"] = table["experiment_name"].map(gif_paths).fillna("")
    table["diagnostic_limitation"] = "Bounding-box monitors cannot identify connected components; flags select cases for visual review and are not exclusions."
    table["permanently_excluded"] = False
    return table


def prepare_depth_review_assets(
    depth_flags: pd.DataFrame,
    labels: pd.DataFrame,
    inventory: pd.DataFrame,
    *,
    workers: int,
    maximum_cases: int = 4,
    maximum_gif_bytes: int = 50 * 2**20,
) -> pd.DataFrame:
    """Fetch a small, deterministic visual-review set at the pinned revision.

    The bounding-box diagnostic can nominate cases, but it cannot reveal whether
    the deepest component is connected to the main melt pool.  We therefore
    fetch one side-view frame nearest the numerical maximum depth for at most
    four cases.  The corresponding side GIF is fetched only when it is present
    and below an explicit size cap.  No visual judgement or exclusion is made
    automatically.
    """

    table = depth_flags.copy()
    for column, default in [
        ("selected_for_visual_review", False),
        ("visual_review_rank", np.nan),
        ("nearest_saved_frame_timestep", np.nan),
        ("side_frame_path_in_repository", ""),
        ("local_side_frame_path", ""),
        ("side_gif_size_bytes", np.nan),
        ("local_side_gif_path", ""),
        ("visual_review_status", "not_selected"),
        ("visual_review_note", ""),
    ]:
        table[column] = default
    if table.empty:
        return table

    candidates = table[table["flag_depth_bounding_box_ambiguity_candidate"].astype(bool)].copy()
    if len(candidates) < maximum_cases:
        supplement = table.loc[~table.index.isin(candidates.index)].copy()
        candidates = pd.concat([candidates, supplement], ignore_index=False)
    candidates = candidates.sort_values(
        ["flag_depth_bounding_box_ambiguity_candidate", "depth_ambiguity_score"],
        ascending=[False, False],
        na_position="last",
    ).head(maximum_cases)

    file_inventory = inventory[inventory["item_type"].eq("file")].set_index("path")
    downloads: list[str] = []
    details: dict[int, dict[str, Any]] = {}
    for rank, (index, row) in enumerate(candidates.iterrows(), start=1):
        name = str(row["experiment_name"])
        experiment_labels = labels[labels["experiment_name"].eq(name)].sort_values(
            ["timestep", "frame_row_in_partition"], kind="stable"
        )
        if experiment_labels.empty:
            continue
        nearest_position = int(
            np.argmin(
                np.abs(
                    experiment_labels["timestep"].to_numpy(float)
                    - float(row["max_depth_iteration"])
                )
            )
        )
        nearest = experiment_labels.iloc[nearest_position]
        frames_csv_relative = f"{name}/frames.csv"
        frames_csv = download_pinned_files(
            [frames_csv_relative], workers=1, progress_every=1
        )[frames_csv_relative]
        frame_ledger = pd.read_csv(frames_csv)
        matched = frame_ledger[frame_ledger["timestep"].eq(int(nearest["timestep"]))]
        if matched.empty:
            matched = frame_ledger.iloc[[min(nearest_position, len(frame_ledger) - 1)]]
        side_relative_inside = str(matched.iloc[0]["side_filename"])
        side_frame = f"{name}/{side_relative_inside}"
        gif_path = str(row.get("gif_path_in_repository", ""))
        gif_size = np.nan
        fetch_gif = False
        if gif_path and gif_path in file_inventory.index:
            value = file_inventory.loc[gif_path, "size_bytes"]
            gif_size = int(value) if pd.notna(value) else np.nan
            fetch_gif = bool(pd.notna(gif_size) and gif_size <= maximum_gif_bytes)
        downloads.append(side_frame)
        if fetch_gif:
            downloads.append(gif_path)
        details[index] = {
            "rank": rank,
            "nearest_timestep": int(nearest["timestep"]),
            "side_frame": side_frame,
            "gif_path": gif_path,
            "gif_size": gif_size,
            "fetch_gif": fetch_gif,
        }

    downloaded = (
        download_pinned_files(downloads, workers=min(workers, maximum_cases * 2), progress_every=2)
        if downloads
        else {}
    )
    for index, detail in details.items():
        table.at[index, "selected_for_visual_review"] = True
        table.at[index, "visual_review_rank"] = detail["rank"]
        table.at[index, "nearest_saved_frame_timestep"] = detail["nearest_timestep"]
        table.at[index, "side_frame_path_in_repository"] = detail["side_frame"]
        table.at[index, "local_side_frame_path"] = str(downloaded.get(detail["side_frame"], ""))
        table.at[index, "side_gif_size_bytes"] = detail["gif_size"]
        table.at[index, "local_side_gif_path"] = str(downloaded.get(detail["gif_path"], ""))
        table.at[index, "visual_review_status"] = "PENDING_MANUAL_REVIEW"
        table.at[index, "visual_review_note"] = (
            "Side frame nearest maximum depth downloaded; side GIF downloaded within 50 MiB cap."
            if detail["fetch_gif"]
            else "Side frame nearest maximum depth downloaded; GIF absent or above 50 MiB cap."
        )
    return table.sort_values(
        ["selected_for_visual_review", "visual_review_rank", "depth_ambiguity_score"],
        ascending=[False, True, False],
        na_position="last",
    )


def preserve_existing_visual_reviews(
    table: pd.DataFrame, existing: pd.DataFrame
) -> pd.DataFrame:
    """Carry forward manual review notes for unchanged experiment identifiers."""

    if existing.empty or "visual_review_status" not in existing.columns:
        return table
    reviewed = existing[existing["visual_review_status"].eq("REVIEWED")].copy()
    if reviewed.empty:
        return table
    reviewed = reviewed.drop_duplicates("experiment_name").set_index("experiment_name")
    result = table.copy()
    for column in [
        "visual_review_status",
        "visual_review_note",
        "reviewer",
        "reviewed_at_utc",
        "visual_evidence_scope",
        "exclusion_decision",
    ]:
        if column not in reviewed.columns:
            continue
        if column not in result.columns:
            result[column] = ""
        mapped = result["experiment_name"].map(reviewed[column])
        result[column] = mapped.where(mapped.notna(), result[column])
    return result


def select_representatives(targets: pd.DataFrame, anomalies: pd.DataFrame) -> pd.DataFrame:
    valid = targets[targets["target_extraction_valid"]].copy()
    choices: list[dict[str, Any]] = []

    def add(row: pd.Series, reason: str) -> None:
        if row["experiment_name"] not in {item["experiment_name"] for item in choices}:
            choices.append({"experiment_name": row["experiment_name"], "partition": row["partition"], "has_keyhole": bool(row["has_keyhole"]), "selection_reason": reason})

    for partition in PARTITION_ORDER:
        part = valid[valid["partition"].eq(partition)]
        for has_keyhole in [True, False]:
            subset = part[part["has_keyhole"].eq(has_keyhole)]
            if len(subset):
                median = subset["T0_depth_um"].median()
                add(subset.loc[(subset["T0_depth_um"] - median).abs().idxmin()], f"{partition}; {'Keyhole' if has_keyhole else 'non-Keyhole'}; median T0 depth")
    for feature, label in [("LS_um", "lowest LS"), ("LS_um", "highest LS"), ("ST_K", "lowest ST"), ("ST_K", "highest ST")]:
        index = valid[feature].idxmin() if "lowest" in label else valid[feature].idxmax()
        add(valid.loc[index], label)
    if valid["depth_ambiguity_score"].notna().any():
        add(valid.loc[valid["depth_ambiguity_score"].idxmax()], "largest automatic depth-ambiguity score")
    failures = targets[~targets["target_extraction_valid"]]
    if len(failures):
        add(failures.iloc[0], "explicit extraction failure; no time-series plot available")
    return pd.DataFrame(choices)


def configure_plotting() -> None:
    plt.rcParams.update({"figure.dpi": 120, "savefig.dpi": 180, "font.size": 10, "axes.grid": True, "grid.alpha": 0.22, "axes.spines.top": False, "axes.spines.right": False})


def save_figure(fig: plt.Figure, output_dir: Path, filename: str) -> str:
    path = output_dir / "figures" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path.relative_to(ROOT).as_posix()


def generate_depth_review_contact_sheet(
    output_dir: Path, depth_flags: pd.DataFrame
) -> dict[str, Any] | None:
    selected_visuals = (
        depth_flags[depth_flags["selected_for_visual_review"].astype(bool)]
        if "selected_for_visual_review" in depth_flags.columns
        else depth_flags.iloc[0:0]
    )
    selected_visuals = selected_visuals.sort_values("visual_review_rank")
    if not len(selected_visuals):
        return None
    configure_plotting()
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.5))
    for axis, (_, row) in zip(axes.flat, selected_visuals.iterrows()):
        local = Path(str(row["local_side_frame_path"]))
        if local.is_file():
            axis.imshow(plt.imread(local))
        axis.set_title(
            f"Review {int(row['visual_review_rank'])}: {row['partition']}\n"
            f"max depth={row['max_depth_um']:.1f} µm; G3={row['G3_persistent_depth_um']:.1f} µm",
            fontsize=9,
        )
        axis.axis("off")
    for axis in axes.flat[len(selected_visuals) :]:
        axis.axis("off")
    return {
        "figure": "12_depth_visual_review_contact_sheet.png",
        "path": save_figure(fig, output_dir, "12_depth_visual_review_contact_sheet.png"),
        "question": "Do automatically selected maximum-depth side views show a disconnected lower component?",
    }


def generate_figures(
    output_dir: Path,
    targets: pd.DataFrame,
    compatibility: pd.DataFrame,
    comparison: pd.DataFrame,
    depth_flags: pd.DataFrame,
    representatives: pd.DataFrame,
    traces: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    configure_plotting()
    manifest: list[dict[str, Any]] = []
    valid = targets[targets["target_extraction_valid"]].copy()

    schema = compatibility.groupby(["partition", "monitor_file"])["schema_compatible"].mean().unstack(fill_value=0).reindex(PARTITION_ORDER)
    fig, ax = plt.subplots(figsize=(9.5, 4.5))
    image = ax.imshow(schema.to_numpy(), vmin=0, vmax=1, cmap="RdYlGn", aspect="auto")
    ax.set_xticks(np.arange(len(schema.columns)), schema.columns, rotation=25, ha="right")
    ax.set_yticks(np.arange(len(schema.index)), schema.index)
    for i in range(len(schema.index)):
        for j in range(len(schema.columns)):
            ax.text(j, i, f"{schema.iloc[i, j]*100:.1f}%", ha="center", va="center")
    ax.set_title("Monitor schema compatibility by partition")
    fig.colorbar(image, ax=ax, label="Compatible fraction")
    manifest.append({"figure": "01_monitor_schema_compatibility.png", "path": save_figure(fig, output_dir, "01_monitor_schema_compatibility.png"), "question": "Do required monitor schemas transfer?"})

    active_fraction = valid["active_region_fraction_of_monitor"]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.5))
    axes[0].hist(active_fraction, bins=25, color="#4C78A8", alpha=0.8)
    axes[0].set(xlabel="Active rows / all monitor rows", ylabel="Experiments", title="Active-region fraction")
    axes[1].hist(valid["T0_sample_count"], bins=25, color="#59A14F", alpha=0.8)
    axes[1].axvline(MIN_LATE_ROWS, color="#CC3311", ls="--", label=f"minimum fallback={MIN_LATE_ROWS}")
    axes[1].set(xlabel="T0 sample count", ylabel="Experiments", title="T0 window size")
    axes[1].legend(frameon=False)
    manifest.append({"figure": "02_active_region_diagnostics.png", "path": save_figure(fig, output_dir, "02_active_region_diagnostics.png"), "question": "Are active and T0 windows sufficiently populated?"})

    for number, (column, unit, title) in enumerate(
        [
            ("T0_width_um", "µm", "T0 melt-pool width"),
            ("T0_depth_um", "µm", "T0 penetration depth"),
            ("T0_total_height_um", "µm", "T0 total vertical height"),
            ("T0_kinetic_energy_nJ", "nJ", "T0 melt kinetic energy"),
        ], start=3
    ):
        fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4))
        for partition in PARTITION_ORDER:
            values = valid.loc[valid["partition"].eq(partition), column]
            axes[0].hist(values, bins=22, density=True, histtype="step", linewidth=2, color=COLORS[partition], label=partition)
        for has_keyhole, label in [(False, "non-Keyhole"), (True, "Keyhole")]:
            values = valid.loc[valid["has_keyhole"].eq(has_keyhole), column]
            axes[1].hist(values, bins=22, density=True, histtype="step", linewidth=2, color=COLORS[label], label=label)
        axes[0].set(xlabel=f"{title} ({unit})", ylabel="Density", title="By partition")
        axes[1].set(xlabel=f"{title} ({unit})", ylabel="Density", title="By observed Keyhole presence")
        axes[0].legend(frameon=False, fontsize=8); axes[1].legend(frameon=False)
        filename = f"{number:02d}_{column}_distribution.png"
        manifest.append({"figure": filename, "path": save_figure(fig, output_dir, filename), "question": f"Is {title} distributed plausibly?"})

    for number, (t0, maximum, unit, label) in enumerate(
        [
            ("T0_depth_um", "max_depth_um", "µm", "penetration depth"),
            ("T0_total_height_um", "max_total_height_um", "µm", "total height"),
            ("T0_kinetic_energy_nJ", "max_kinetic_energy_nJ", "nJ", "kinetic energy"),
        ], start=7
    ):
        fig, ax = plt.subplots(figsize=(6.2, 5.4))
        for has_keyhole, group in [(False, "non-Keyhole"), (True, "Keyhole")]:
            subset = valid[valid["has_keyhole"].eq(has_keyhole)]
            ax.scatter(subset[t0], subset[maximum], s=18, alpha=0.6, color=COLORS[group], label=group)
        limits = [min(valid[t0].min(), valid[maximum].min()), max(valid[t0].max(), valid[maximum].max())]
        ax.plot(limits, limits, "--", color="black", lw=1, label="identity")
        ax.set(xlabel=f"T0 {label} ({unit})", ylabel=f"Maximum {label} ({unit})", title=f"T0 versus maximum {label}")
        ax.legend(frameon=False)
        filename = f"{number:02d}_T0_vs_max_{label.replace(' ', '_')}.png"
        manifest.append({"figure": filename, "path": save_figure(fig, output_dir, filename), "question": f"How often does T0 differ from extreme {label}?"})

    timing = valid[valid["has_keyhole"]]["keyhole_timing_relative_to_T0"].value_counts()
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.bar(timing.index, timing.values, color="#CC6677")
    ax.tick_params(axis="x", rotation=25)
    ax.set(ylabel="Keyhole-positive experiments", title="Observed Keyhole frames relative to T0")
    manifest.append({"figure": "10_keyhole_timing_relative_to_T0.png", "path": save_figure(fig, output_dir, "10_keyhole_timing_relative_to_T0.png"), "question": "Does T0 overlap observed transient Keyhole frames?"})

    if len(comparison):
        fig, axes = plt.subplots(2, 2, figsize=(10.5, 8.5))
        for ax, label in zip(axes.flat, ["width_um", "depth_um", "total_height_um", "kinetic_energy_nJ"]):
            ax.scatter(comparison[f"old_{label}"], comparison[f"new_{label}"], s=14, alpha=0.55, color="#4C78A8")
            finite = comparison[[f"old_{label}", f"new_{label}"]].to_numpy(float)
            lo, hi = np.nanmin(finite), np.nanmax(finite)
            ax.plot([lo, hi], [lo, hi], "--", color="black", lw=1)
            ax.set(xlabel=f"Week 6 {label}", ylabel=f"sph_v2 {label}", title=label)
        manifest.append({"figure": "11_exact_old_vs_new_target_comparison.png", "path": save_figure(fig, output_dir, "11_exact_old_vs_new_target_comparison.png"), "question": "Do exact matched experiments preserve Week 6 target semantics?"})

    contact_sheet = generate_depth_review_contact_sheet(output_dir, depth_flags)
    if contact_sheet:
        manifest.append(contact_sheet)

    for index, rep in representatives.iterrows():
        name = rep["experiment_name"]
        if name not in traces:
            continue
        trace = traces[name]
        target = valid[valid["experiment_name"].eq(name)].iloc[0]
        row_count = len(trace["time_s"])
        indices = np.unique(np.linspace(0, row_count - 1, min(2500, row_count), dtype=int))
        fig, axes = plt.subplots(4, 1, figsize=(11, 9), sharex=True)
        series = [
            (trace["width_m"] * 1e6, "Width (µm)", target["T0_width_um"]),
            (trace["depth_m"] * 1e6, "Depth (µm)", target["T0_depth_um"]),
            (trace["total_height_m"] * 1e6, "Total height (µm)", target["T0_total_height_um"]),
            (trace["kinetic_j"] * 1e9, "Kinetic energy (nJ)", target["T0_kinetic_energy_nJ"]),
        ]
        active_start, active_end = target["active_region_start_time_s"], target["active_region_end_time_s"]
        t0_start, t0_end = target["T0_start_time_s"], target["T0_end_time_s"]
        for axis, (values, ylabel, median) in zip(axes, series):
            axis.plot(trace["time_s"][indices] * 1e3, values[indices], lw=0.9, color="#264653")
            axis.axvspan(active_start * 1e3, active_end * 1e3, color=COLORS["active"], alpha=0.22, label="active region")
            axis.axvspan(t0_start * 1e3, t0_end * 1e3, color=COLORS["T0"], alpha=0.28, label="T0")
            axis.axhline(median, color="#CC3311", ls="--", lw=1, label="T0 median")
            axis.set_ylabel(ylabel)
        axes[-1].set_xlabel("Simulation time (ms; monitor time, not label-frame duration)")
        axes[0].legend(frameon=False, ncol=3, fontsize=8)
        fig.suptitle(f"{rep['selection_reason']}\n{name}", fontsize=10)
        filename = f"representative_{index+1:02d}_{hashlib.sha256(name.encode()).hexdigest()[:10]}.png"
        manifest.append({"figure": filename, "path": save_figure(fig, output_dir, filename), "question": f"Does extraction look plausible for {rep['selection_reason']}?", "experiment_name": name})
    return pd.DataFrame(manifest)


def traceability_table() -> pd.DataFrame:
    sources = [
        ("active cutoff", "src/week6_phase1_melt_pool_data_audit.py", "ACTIVE_DOMAIN_FRACTION", "min(recording end, 0.90 * laser exit time)", "constant imported and used directly"),
        ("T0 duration", "src/week6_phase1_melt_pool_data_audit.py", "LATE_WINDOW_FRACTION", "final 20% between first valid melt and active cutoff", "constant imported and used directly"),
        ("minimum T0 rows", "src/week6_phase1_melt_pool_data_audit.py", "MIN_LATE_ROWS", "fallback to final 50 eligible rows", "constant imported and used directly"),
        ("melt validity", "src/week6_phase1_melt_pool_data_audit.py", "SENTINEL_THRESHOLD", "finite, ordered bounds with abs(value)<1e30", "constant imported and same formula"),
        ("width", "src/week6_phase1_melt_pool_data_audit.py", "parse_all_melt_bounds", "y_max-y_min", "same executable formula"),
        ("depth", "src/week6_phase1_melt_pool_data_audit.py", "parse_all_melt_bounds", "max(0,-z_min)", "same executable formula"),
        ("total height", "src/week6_phase3_5_regime_target_design.py", "process_simulation", "z_max-z_min", "same executable formula"),
        ("kinetic energy", "src/week6_phase4_new_outputs_feature_effects.py", "extract_targets", "median aligned kinetic-energy_melt.dat values in T0", "same formula and units"),
        ("G3/R3 continuity", "src/week6_phase3_5_regime_target_design.py", "rolling_distance_stat / safe_ratio", "maximum trailing 50 µm rolling medians in adaptive interior", "functions imported and used directly"),
        ("sph_v2 domain layer", "src/week7_phase2_sph_v2_physical_target_extraction.py", "verify_domain_compatibility", "domain_max=min(XF,XL)+12 µm", "smallest structural compatibility layer; verified against all exact Week 6 matches"),
        (
            "supervisor-confirmed textual no-melt sentinel",
            "src/week7_phase2_sph_v2_physical_target_extraction.py",
            "load_numeric",
            "recognize only exact field s3.402823e+38 as +3.402823e+38, then exclude row with abs(value)<1e30",
            "parser compatibility only; Week 6 melt-validity and target formulas unchanged",
        ),
    ]
    rows = []
    for quantity, path_text, symbol, formula, reuse in sources:
        path = ROOT / path_text
        rows.append({"quantity": quantity, "source_file": path_text, "source_symbol": symbol, "formula_or_definition": formula, "reuse_method": reuse, "source_sha256": sha256_file(path)})
    return pd.DataFrame(rows)


def validation_table(
    targets: pd.DataFrame,
    compatibility: pd.DataFrame,
    comparison: pd.DataFrame,
    domain: pd.DataFrame,
    labels: pd.DataFrame,
    depth_flags: pd.DataFrame,
    sentinel_audit: pd.DataFrame,
    correction: pd.DataFrame,
    smoke: bool,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(identifier: str, requirement: str, condition: bool, detail: str, *, warning: bool = False) -> None:
        rows.append({"validation_id": identifier, "requirement": requirement, "status": "PASS" if condition else "WARNING" if warning else "FAIL", "detail": detail})

    valid = targets[targets["target_extraction_valid"]]
    invalid = targets[~targets["target_extraction_valid"]]
    add("V01", "Exact sph_v2 revision recorded on every row", set(targets["exact_sph_v2_revision"].astype(str)) == {SPH_V2_REVISION}, SPH_V2_REVISION)
    add("V02", "One target row retained per Phase 1 experiment", targets["experiment_name"].is_unique and len(targets) == labels["experiment_name"].nunique(), f"targets={len(targets)}; labels={labels['experiment_name'].nunique()}")
    add("V03", "All P/VX/LS/ST finite", np.isfinite(targets[["P_W", "VX_m_per_s", "LS_m", "ST_K"]].to_numpy(float)).all(), "all target-table input fields checked")
    missing = compatibility[~compatibility["remote_exists"].astype(bool)]
    add("V04", "Every required monitor exists", missing.empty, f"missing monitor rows={len(missing)}", warning=not missing.empty)
    present = compatibility[compatibility["remote_exists"].astype(bool)]
    add("V05", "All present monitor bytes match pinned Git blobs", present["local_blob_matches_pinned_sph_v2"].astype(bool).all(), f"verified={int(present['local_blob_matches_pinned_sph_v2'].astype(bool).sum())}/{len(present)}")
    add("V06", "All present monitor schemas compatible", present["schema_compatible"].astype(bool).all(), f"compatible={int(present['schema_compatible'].astype(bool).sum())}/{len(present)}")
    add("V07", "Every extraction failure is retained explicitly", set(invalid["experiment_name"]).issubset(set(targets["experiment_name"])) and invalid["extraction_failure_reasons"].astype(str).str.len().gt(0).all(), f"invalid rows retained={len(invalid)}")
    target_columns = ["T0_width_um", "T0_depth_um", "T0_total_height_um", "T0_kinetic_energy_nJ", "max_depth_um", "max_total_height_um", "max_kinetic_energy_nJ"]
    add("V08", "Targets finite where extraction succeeds", np.isfinite(valid[target_columns].to_numpy(float)).all(), f"valid rows={len(valid)}")
    add("V09", "Physical dimensions and energy non-negative", (valid[target_columns].to_numpy(float) >= 0).all(), "width/depth/height/energy checked")
    add("V10", "Total height >= penetration depth where observed melt crosses surface", (valid["T0_total_height_um"] + 1e-9 >= valid["T0_depth_um"]).all(), f"violations={int((valid['T0_total_height_um'] + 1e-9 < valid['T0_depth_um']).sum())}")
    add("V11", "Max responses >= corresponding T0 medians", ((valid["max_depth_um"] + 1e-9 >= valid["T0_depth_um"]) & (valid["max_total_height_um"] + 1e-9 >= valid["T0_total_height_um"]) & (valid["max_kinetic_energy_nJ"] + 1e-12 >= valid["T0_kinetic_energy_nJ"])).all(), "depth, height, and kinetic energy")
    add("V12", "T0 lies inside active region", valid["T0_inside_active_region"].astype(bool).all(), f"violations={int((~valid['T0_inside_active_region'].astype(bool)).sum())}")
    add("V13", "No cooling-only rows selected in T0", valid["cooling_rows_selected_in_T0"].eq(0).all(), f"selected cooling rows={int(valid['cooling_rows_selected_in_T0'].sum())}")
    add("V14", "Folder-domain mapping reproduces Week 6", domain["mapping_matches_week6"].astype(bool).all(), f"matches={int(domain['mapping_matches_week6'].astype(bool).sum())}/{len(domain)}")
    if not smoke:
        identical_columns = [column for column in comparison if column.startswith("identical_within_tolerance_")]
        expected_comparable = int(
            (
                targets["week6_simulation_id"].fillna("").astype(str).str.len().gt(0)
                & targets["target_extraction_valid"].astype(bool)
            ).sum()
        )
        add("V15", "All comparable exact old matches reproduce Week 6 targets", len(comparison) == expected_comparable and comparison[identical_columns].all(axis=None) and comparison["window_endpoints_identical"].all(), f"comparable matches={len(comparison)}/{expected_comparable}; target mismatches={int((~comparison[identical_columns]).sum().sum())}; endpoint mismatches={int((~comparison['window_endpoints_identical']).sum())}")
    else:
        add("V15", "Smoke comparable exact matches reproduce Week 6 targets", comparison[[column for column in comparison if column.startswith("identical_within_tolerance_")]].all(axis=None) and comparison["window_endpoints_identical"].all(), f"smoke comparable exact matches={len(comparison)}")
    add("V16", "No source label modified", targets["source_label_modified"].eq(False).all(), "read-only label context")
    add("V17", "No simulation silently removed", targets["simulation_silently_removed"].eq(False).all() and set(targets["experiment_name"]) == set(labels["experiment_name"]), "Phase 1 and Phase 2 populations match")
    source_ok, hits = ensure_no_modelling_imports(Path(__file__))
    add("V18", "No predictive model fitting code in Phase 2", source_ok, f"executable forbidden imports/calls={hits}")
    notebook_ok = NOTEBOOK_PATH.is_file() and not notebook_has_errors(NOTEBOOK_PATH)
    add("V19", "Teaching notebook exists with no stored errors", notebook_ok, str(NOTEBOOK_PATH.relative_to(ROOT)), warning=not NOTEBOOK_PATH.is_file())
    selected = (
        depth_flags[depth_flags["selected_for_visual_review"].astype(bool)]
        if "selected_for_visual_review" in depth_flags.columns
        else depth_flags.iloc[0:0]
    )
    assets_exist = bool(len(selected)) and selected["local_side_frame_path"].astype(str).map(
        lambda value: Path(value).is_file()
    ).all()
    available_asset_count = int(
        selected["local_side_frame_path"].astype(str).map(lambda value: Path(value).is_file()).sum()
    )
    review_complete = assets_exist and selected["visual_review_status"].eq("REVIEWED").all()
    add(
        "V20",
        "Small automatically selected depth-ambiguity set visually reviewed",
        review_complete,
        f"selected={len(selected)}; side frames available={available_asset_count}; reviewed={int(selected['visual_review_status'].eq('REVIEWED').sum()) if len(selected) else 0}",
        warning=assets_exist and not review_complete,
    )
    exact_variant = sentinel_audit[
        sentinel_audit["token"].eq(KNOWN_MALFORMED_NO_MELT_SENTINEL_TOKEN)
    ]
    recognized_count = int(
        compatibility["known_malformed_no_melt_sentinel_count"].sum()
    )
    add(
        "V21",
        "Only the exact supervisor-confirmed textual sentinel variant is recognized",
        len(exact_variant) == 1
        and int(exact_variant.iloc[0]["count"]) == recognized_count
        and (recognized_count > 0 or smoke),
        f"token={KNOWN_MALFORMED_NO_MELT_SENTINEL_TOKEN}; recognized fields={recognized_count}; smoke deferral={smoke and recognized_count == 0}",
    )
    affected = targets[
        targets["known_malformed_no_melt_sentinel_row_count"].fillna(0).gt(0)
    ]
    add(
        "V22",
        "Recognized textual sentinel rows are excluded from physical coordinates",
        (len(affected) > 0
        and affected["known_malformed_no_melt_sentinel_rows_excluded"].astype(bool).all())
        or (smoke and affected.empty),
        f"affected experiments={len(affected)}; excluded rows={int(affected['known_malformed_no_melt_sentinel_row_count'].sum())}",
    )
    add(
        "V23",
        "No unrelated malformed token is coerced",
        int(compatibility["unrelated_malformed_token_coercion_count"].sum()) == 0
        and int(
            sentinel_audit.loc[
                sentinel_audit["token"].eq("other numeric/textual variants near 1e38"),
                "count",
            ].sum()
        )
        == 0,
        "generic letter stripping is absent; unrelated coercion count=0",
    )
    changed = correction[correction.get("status_changed", False).astype(bool)] if len(correction) else correction
    affected_names = set(affected["experiment_name"])
    add(
        "V24",
        "Extraction-status changes are confined to sentinel-affected experiments",
        len(correction) > 0
        and set(changed["experiment_name"]).issubset(affected_names)
        and correction["_merge"].eq("both").all(),
        f"status changes={len(changed)}; sentinel-affected={len(affected_names)}; rows compared={len(correction)}",
    )
    previous_valid_changes = int(
        correction.get(
            "previous_valid_target_changed_unexpectedly", pd.Series(dtype=bool)
        ).fillna(False).sum()
    )
    add(
        "V25",
        "Previously valid physical targets remain unchanged",
        len(correction) > 0 and previous_valid_changes == 0,
        f"unexpected previously-valid changes={previous_valid_changes}",
    )
    label_changes = int(
        correction.get("label_context_changed", pd.Series(dtype=bool)).fillna(False).sum()
    )
    add(
        "V26",
        "Per-experiment label context is unchanged from the pre-clarification baseline",
        len(correction) > 0 and label_changes == 0,
        f"label-context changes={label_changes}",
    )
    eligibility_columns = [
        "geometry_monitor_available",
        "geometry_parse_ok",
        "geometry_target_ready",
        "time_monitor_available",
        "time_parse_ok",
        "kinetic_energy_monitor_available",
        "kinetic_energy_parse_ok",
        "kinetic_energy_target_ready",
        "physical_target_extraction_success",
        "extraction_failure_reason",
        "label_analysis_ready",
    ]
    eligibility_ok = set(eligibility_columns).issubset(targets.columns)
    if eligibility_ok:
        eligibility_ok = bool(
            targets["physical_target_extraction_success"].astype(bool).eq(
                targets["target_extraction_valid"].astype(bool)
            ).all()
            and targets["extraction_failure_reason"].fillna("").eq(
                targets["extraction_failure_reasons"].fillna("")
            ).all()
            and targets["label_analysis_ready"].astype(bool).all()
            and valid[
                [
                    "geometry_target_ready",
                    "time_target_ready",
                    "iteration_target_ready",
                    "kinetic_energy_target_ready",
                ]
            ].astype(bool).all(axis=None)
        )
    add(
        "V27",
        "Generic monitor, target-readiness, and extraction eligibility flags are consistent",
        eligibility_ok,
        f"required fields={len(eligibility_columns)}; successful rows={len(valid)}",
    )
    new_missing_names = set(
        compatibility.loc[
            compatibility["partition"].eq("new-data")
            & ~compatibility["remote_exists"].astype(bool)
            & compatibility["monitor_file"].isin(
                ["position-bounds_melt.dat", "kinetic-energy_melt.dat"]
            ),
            "experiment_name",
        ]
    )
    new_missing_rows = targets[targets["experiment_name"].isin(new_missing_names)]
    add(
        "V28",
        "Completely monitor-missing new-data targets remain explicitly unavailable",
        (bool(new_missing_names)
        and len(new_missing_rows) == len(new_missing_names)
        and (~new_missing_rows["physical_target_extraction_success"].astype(bool)).all()
        and new_missing_rows["extraction_failure_reasons"].str.contains("missing", na=False).all())
        or (smoke and not new_missing_names),
        f"source-derived unavailable new-data experiments={len(new_missing_names)}",
    )
    old_missing = compatibility[
        compatibility["partition"].eq("old-data-local")
        & ~compatibility["remote_exists"].astype(bool)
    ]
    old_missing_names = set(old_missing["experiment_name"])
    old_missing_rows = targets[targets["experiment_name"].isin(old_missing_names)]
    add(
        "V29",
        "Old-data-local missing monitors remain unresolved and are not backfilled",
        (bool(old_missing_names)
        and old_missing["source_mode"].eq("missing_in_pinned_sph_v2").all()
        and (~old_missing_rows["physical_target_extraction_success"].astype(bool)).all())
        or (smoke and not old_missing_names),
        f"missing monitor rows={len(old_missing)}; affected experiments={len(old_missing_names)}",
        warning=bool(old_missing_names),
    )
    formulas_unchanged = bool(
        valid["width_formula"].eq("y_max - y_min").all()
        and valid["depth_formula"].eq("max(0, -z_min)").all()
        and valid["total_height_formula"].eq("z_max - z_min").all()
        and valid["kinetic_energy_semantics"].str.contains("source J, reported nJ", regex=False).all()
    )
    add(
        "V30",
        "Target formulas and units remain the Week 6 definitions",
        formulas_unchanged,
        "geometry reported in um; kinetic energy source J and reported nJ",
    )
    return pd.DataFrame(rows)


def requirement_checklist(validation: pd.DataFrame) -> pd.DataFrame:
    by_id = validation.set_index("validation_id")["status"].to_dict()

    def status_for(validation_ids: Sequence[str], *, audit_caveat: bool = False) -> str:
        values = [by_id[identifier] for identifier in validation_ids]
        if "FAIL" in values:
            return "WARNING" if audit_caveat else "FAIL"
        if "WARNING" in values:
            return "WARNING"
        return "PASS"

    entries = [
        ("P2-01", "Exact Week 6 definitions traced to executable sources", "Notebook §2", "week6_definition_traceability.csv", ["V14"], False),
        ("P2-02", "Monitor existence, schema, rows, units and invalid values audited", "Notebook §3", "monitor_schema_compatibility.csv", ["V04", "V05", "V06"], True),
        ("P2-03", "Smallest domain compatibility layer verified on exact matches", "Notebook §3", "domain_mapping_compatibility.csv", ["V14"], False),
        ("P2-04", "Active region and T0 reconstructed without redefining T0", "Notebook §4", "active_region_diagnostics.csv", ["V04", "V07", "V12", "V13"], True),
        ("P2-05", "Representative normal, edge and suspicious time series plotted", "Notebook §5", "representative_simulation_selection.csv; figures/representative_*.png", ["V08"], False),
        ("P2-06", "One-row-per-simulation target table saved as CSV and Parquet", "Notebook §6", "sph_v2_simulation_level_targets.csv; sph_v2_simulation_level_targets.parquet", ["V02", "V07", "V17"], False),
        ("P2-07", "Width/depth/height/kinetic T0 and maximum responses retained", "Notebook §6", "sph_v2_simulation_level_targets.csv", ["V08", "V09", "V11"], False),
        ("P2-08", "Length retained as diagnostic, not promoted to primary target", "Notebook §6", "sph_v2_simulation_level_targets.csv", ["V08"], False),
        ("P2-09", "Exact old/new matches compared without fuzzy matching", "Notebook §7", "week6_exact_identifier_map.csv; exact_old_new_target_comparison.csv", ["V15"], False),
        ("P2-10", "Target distributions audited overall, by partition and Keyhole", "Notebook §8", "target_distribution_summary.csv; figures/03_*.png–06_*.png", ["V08", "V09"], False),
        ("P2-11", "T0 versus extreme-event timing diagnosed", "Notebook §9", "t0_extreme_event_diagnostics.csv; figures/07_*.png–10_*.png", ["V11", "V12", "V13"], False),
        ("P2-12", "Depth bounding-box ambiguity flagged and a small set visually reviewed without exclusion", "Notebook §10", "flagged_depth_ambiguity.csv", ["V20"], True),
        ("P2-13", "Failures and warnings retained explicitly", "Notebook §11", "extraction_failure_anomalies.csv", ["V04", "V07"], True),
        ("P2-14", "Validation dashboard and machine-readable summary written", "Notebook §12", "validation_results.csv; summary.json", ["V01", "V02"], False),
        ("P2-15", "No label changed and no simulation silently removed", "Notebook §12", "validation_results.csv", ["V16", "V17"], False),
        ("P2-16", "Hard stop before modelling and active learning", "Notebook §12", "validation_results.csv", ["V18"], False),
        ("P2-17", "Executed teaching notebook contains no stored errors", "Notebook §§1–12", "notebooks/week_07/02_sph_v2_physical_target_extraction.ipynb", ["V19"], False),
        (
            "P2-18",
            "Supervisor-confirmed no-melt sentinel audited, narrowly parsed, and regression-tested",
            "Notebook §3A",
            "sentinel_audit.csv; supervisor_correction_before_after.csv; new_data_readiness_summary.csv",
            ["V21", "V22", "V23", "V24", "V25", "V26", "V27", "V28", "V29", "V30"],
            True,
        ),
    ]
    return pd.DataFrame(
        [
            {
                "requirement_id": identifier,
                "requirement": requirement,
                "status": status_for(validation_ids, audit_caveat=audit_caveat),
                "notebook_section": section,
                "output_artifact": artifact,
                "validation_ids": ";".join(validation_ids),
            }
            for identifier, requirement, section, artifact, validation_ids, audit_caveat in entries
        ]
    )


def results_markdown(
    targets: pd.DataFrame,
    comparison_summary: pd.DataFrame,
    validation: pd.DataFrame,
    sentinel_audit: pd.DataFrame,
    correction: pd.DataFrame,
    smoke: bool,
) -> str:
    valid = targets[targets["target_extraction_valid"]]
    keyhole = valid[valid["has_keyhole"]]
    no_t0_keyhole = int((~keyhole["keyhole_overlaps_T0"].astype(bool)).sum())
    before_depth = int(valid["max_depth_relative_to_T0"].eq("before_T0").sum())
    review_path = (SMOKE_DIR if smoke else OUTPUT_DIR) / "depth_visual_review_notes.csv"
    reviews = pd.read_csv(review_path) if review_path.is_file() else pd.DataFrame()
    reviewed_count = int(reviews["visual_review_status"].eq("REVIEWED").sum()) if len(reviews) else 0
    clear_disconnected_count = int(
        reviews["visual_review_note"].str.contains("clearly separated", case=False, na=False).sum()
    ) if len(reviews) else 0
    connected_count = int(
        reviews["visual_review_note"].str.contains("continuous red melt", case=False, na=False).sum()
    ) if len(reviews) else 0
    inconclusive_count = int(
        reviews["visual_review_note"].str.contains("inconclusive", case=False, na=False).sum()
    ) if len(reviews) else 0
    new_data = targets[targets["partition"].eq("new-data")]
    new_valid = new_data[new_data["target_extraction_valid"]]
    new_failures = new_data[~new_data["target_extraction_valid"]]
    exact_variant = sentinel_audit.set_index("token").loc[
        KNOWN_MALFORMED_NO_MELT_SENTINEL_TOKEN
    ]
    changed = correction[correction["status_changed"].astype(bool)] if len(correction) else correction
    changed_text = ", ".join(changed["experiment_name"].tolist()) or "none"
    remaining_text = (
        "\n".join(
            f"- `{row.experiment_name}`: {row.extraction_failure_reasons}"
            for row in new_failures.itertuples(index=False)
        )
        or "- None."
    )
    prior_valid_changes = int(
        correction["previous_valid_target_changed_unexpectedly"].fillna(False).sum()
    ) if len(correction) else 0
    return f"""# Week 7 Phase 2 — sph_v2 physical-target extraction

## Outcome

The {'smoke' if smoke else 'full'} run applied the executable Week 6 T0,
width, depth, total-height, kinetic-energy, G3, and R3 definitions to
`{SPH_V2_REPO_ID}@{SPH_V2_REVISION}`.  The compatibility layer changes paths
and reconstructs `domain_max_x` from folder `min(XF, XL)`; it does not change the
scientific target definition.

- Target rows retained: **{len(targets)}**.
- Successful extractions: **{len(valid)}**.
- Explicit failures: **{int((~targets['target_extraction_valid']).sum())}**.
- Exact Week 6 identifiers matched: **{int(targets['week6_simulation_id'].fillna('').astype(str).str.len().gt(0).sum())}**.
- Exact matches with sufficient pinned monitors for target comparison: **{int(comparison_summary['exact_match_count'].max()) if len(comparison_summary) else 0}**.

## Supervisor clarification: no-melt `1e38` sentinel

The raw-token audit found `3.402823e+38` **{int(sentinel_audit.set_index('token').loc['3.402823e+38', 'count']):,}** times,
`-3.402823e+38` **{int(sentinel_audit.set_index('token').loc['-3.402823e+38', 'count']):,}** times, and the exact
non-numeric field `s3.402823e+38` **{int(exact_variant['count'])}** time(s). No other numeric or textual
variant near `1e38` was found. The parser recognizes only that exact complete
field as the ordinary positive no-melt sentinel and then excludes its entire
row with the unchanged Week 6 `abs(value) < 1e30` rule. It does not strip
arbitrary letters, replace the sentinel with zero, interpolate it, or use it as
a physical coordinate.

- New-data readiness after correction: **{len(new_valid)}/{len(new_data)}**.
- Extraction-status changes: **{len(changed)}** — {changed_text}.
- Unexpected changes among previously valid targets: **{prior_valid_changes}**.
- Remaining new-data failures:
{remaining_text}

## T0 and extreme-event evidence

Maximum depth occurs before T0 in **{before_depth}/{len(valid)}** successful
experiments.  Among **{len(keyhole)}** successful Keyhole-positive experiments,
**{no_t0_keyhole}** have no stored Keyhole-labelled frame inside T0.  This does
not make T0 wrong: T0 represents typical late-active behaviour, while maxima
and brief Keyhole labels answer different physical questions.

## Migration boundary

All exact matches use identifier equality through Week 6
`metadata.json.original_folder_name`; no fuzzy match is used.  Local Week 6
monitor bytes are reused only when their computed Git blob IDs equal the pinned
`sph_v2` tree. Missing monitors are never fabricated or backfilled. The only
textual parser compatibility is the exact confirmed sentinel field above;
unrelated malformed values remain parse failures.

Ioan confirmed that the old-data-local missing files may later be restored by a
separate Hugging Face pull request. They remain visible here as upstream
maintenance flags and are not a blocker for new-data target readiness.

The blue-dot/disconnected-component question cannot be decided from bounding
boxes alone.  Of **{reviewed_count}** automatically selected side frames reviewed,
**{clear_disconnected_count}** clearly shows separated lower components,
**{connected_count}** shows a continuous main melt region without an obvious
detached component, and **{inconclusive_count}** are inconclusive at the nearest
saved-frame cadence.  The automatic table retains all flags and pinned GIF
references; nothing is excluded.

## Validation dashboard

- PASS: **{int(validation['status'].eq('PASS').sum())}**
- WARNING: **{int(validation['status'].eq('WARNING').sum())}**
- FAIL: **{int(validation['status'].eq('FAIL').sum())}**

## Hard stop

No GP, Ridge, polynomial model, classifier, active learning, kernel comparison,
or level-set estimation was run.  Phase 2 ends here.
"""


def run_phase2(*, smoke: bool = False, workers: int = 6) -> dict[str, Any]:
    started = time.perf_counter()
    output_dir = SMOKE_DIR if smoke else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    correction_baseline = capture_supervisor_correction_baseline(output_dir)
    existing_depth_flags_path = output_dir / "flagged_depth_ambiguity.csv"
    existing_depth_flags = (
        pd.read_csv(existing_depth_flags_path)
        if existing_depth_flags_path.is_file()
        else pd.DataFrame()
    )
    print(f"Week 7 Phase 2 {'smoke' if smoke else 'full'} extraction", flush=True)
    registry, sequence, inventory, _ = load_phase1_inputs(smoke)
    all_labels = load_partition_labels(workers=min(3, workers))
    labels = all_labels[all_labels["experiment_name"].isin(registry["experiment_name"])].copy()
    name_map = week6_exact_name_map()
    write_csv(WEEK6_EXACT_MAP_ARTIFACT, name_map)
    domain = verify_domain_compatibility(registry, name_map)
    require(domain["mapping_matches_week6"].all(), "The proposed sph_v2 domain compatibility layer does not reproduce Week 6")
    plan = build_source_plan(registry, inventory, name_map, workers=workers)
    write_csv(output_dir / "monitor_source_plan.csv", plan)
    targets, compatibility, traces = extract_population(registry, sequence, labels, plan, name_map)
    targets = targets.sort_values(["partition", "experiment_name"]).reset_index(drop=True)
    compatibility = compatibility.sort_values(["partition", "experiment_name", "monitor_file"]).reset_index(drop=True)
    compatibility = enrich_monitor_compatibility(compatibility)
    sentinel_audit = sentinel_audit_table(compatibility)
    sentinel_experiments = set(
        compatibility.loc[
            compatibility["known_malformed_no_melt_sentinel_count"].gt(0),
            "experiment_name",
        ]
    )
    correction = supervisor_correction_comparison(
        correction_baseline, targets, sentinel_experiments
    )
    comparison, comparison_summary = old_new_comparison(targets, name_map)
    target_summary = descriptive_target_summary(targets)
    anomalies = extraction_anomalies(targets)
    depth_flags = depth_ambiguity_table(targets, inventory)
    depth_flags = prepare_depth_review_assets(
        depth_flags, labels, inventory, workers=workers
    )
    depth_flags = preserve_existing_visual_reviews(depth_flags, existing_depth_flags)
    representatives = select_representatives(targets, anomalies)
    traces = reconstruct_representative_traces(
        representatives, registry, sequence, labels, plan, name_map
    )
    figures = generate_figures(
        output_dir,
        targets,
        compatibility,
        comparison,
        depth_flags,
        representatives,
        traces,
    )
    traceability = traceability_table()

    active_columns = [column for column in targets.columns if column.startswith("active_") or column.startswith("T0_") and any(token in column for token in ["row_index", "time_s", "sample_count", "inside", "fallback"]) or column in ["experiment_name", "partition", "target_extraction_valid", "extraction_status", "extraction_failure_reasons", "recording_ends_before_90pct_domain", "length_flat_or_decreasing_across_active_region", "flag_primary_window_unstable_week6_rule"]]
    active = targets.loc[:, list(dict.fromkeys(active_columns))]
    t0_extreme_columns = ["experiment_name", "partition", "has_keyhole", "T0_depth_um", "max_depth_um", "max_depth_relative_to_T0", "T0_total_height_um", "max_total_height_um", "max_total_height_relative_to_T0", "T0_kinetic_energy_nJ", "max_kinetic_energy_nJ", "max_kinetic_energy_relative_to_T0", "keyhole_frames_before_T0", "keyhole_frames_inside_T0", "keyhole_frames_after_T0", "keyhole_overlaps_T0", "keyhole_timing_relative_to_T0"]
    t0_extreme = targets[[column for column in t0_extreme_columns if column in targets.columns]]
    readiness_columns = [
        "geometry_monitor_available",
        "geometry_parse_ok",
        "geometry_target_ready",
        "time_monitor_available",
        "time_parse_ok",
        "time_target_ready",
        "iteration_monitor_available",
        "iteration_parse_ok",
        "iteration_target_ready",
        "kinetic_energy_monitor_available",
        "kinetic_energy_parse_ok",
        "kinetic_energy_target_ready",
        "physical_target_extraction_success",
        "label_analysis_ready",
    ]
    readiness = (
        targets.groupby("partition", sort=False)
        .agg(
            experiment_count=("experiment_name", "size"),
            **{
                f"{column}_count": (column, "sum")
                for column in readiness_columns
            },
        )
        .reset_index()
    )

    write_csv(output_dir / "week6_definition_traceability.csv", traceability)
    write_csv(output_dir / "domain_mapping_compatibility.csv", domain)
    write_csv(output_dir / "monitor_schema_compatibility.csv", compatibility)
    write_csv(output_dir / "sentinel_audit.csv", sentinel_audit)
    write_csv(output_dir / "sentinel_audit_table.csv", sentinel_audit)
    write_csv(output_dir / "supervisor_correction_before_after.csv", correction)
    write_csv(output_dir / "new_data_readiness_summary.csv", readiness)
    write_csv(output_dir / "active_region_diagnostics.csv", active)
    write_csv(output_dir / "sph_v2_simulation_level_targets.csv", targets)
    targets.to_parquet(output_dir / "sph_v2_simulation_level_targets.parquet", index=False, compression="zstd")
    write_csv(output_dir / "exact_old_new_target_comparison.csv", comparison)
    write_csv(output_dir / "exact_old_new_target_comparison_summary.csv", comparison_summary)
    write_csv(output_dir / "target_distribution_summary.csv", target_summary)
    write_csv(output_dir / "t0_extreme_event_diagnostics.csv", t0_extreme)
    write_csv(output_dir / "extraction_failure_anomalies.csv", anomalies)
    write_csv(output_dir / "flagged_depth_ambiguity.csv", depth_flags)
    reviewed_notes = depth_flags[depth_flags["visual_review_status"].eq("REVIEWED")].copy()
    if len(reviewed_notes):
        review_columns = [
            "experiment_name",
            "visual_review_status",
            "visual_review_note",
            "reviewer",
            "reviewed_at_utc",
            "visual_evidence_scope",
            "exclusion_decision",
        ]
        write_csv(
            output_dir / "depth_visual_review_notes.csv",
            reviewed_notes[[column for column in review_columns if column in reviewed_notes.columns]],
        )
    write_csv(output_dir / "representative_simulation_selection.csv", representatives)
    write_csv(output_dir / "figure_manifest.csv", figures)

    validation = validation_table(
        targets,
        compatibility,
        comparison,
        domain,
        labels,
        depth_flags,
        sentinel_audit,
        correction,
        smoke,
    )
    checklist = requirement_checklist(validation)
    write_csv(output_dir / "validation_results.csv", validation)
    write_csv(output_dir / "phase2_requirement_checklist.csv", checklist)
    write_csv(output_dir / "requirement_checklist.csv", checklist)
    markdown = results_markdown(
        targets, comparison_summary, validation, sentinel_audit, correction, smoke
    )
    (output_dir / "results_summary.md").write_text(markdown, encoding="utf-8")
    (output_dir / "phase2_results_summary.md").write_text(markdown, encoding="utf-8")
    valid = targets[targets["target_extraction_valid"]]
    keyhole = valid[valid["has_keyhole"]]
    new_data = targets[targets["partition"].eq("new-data")]
    new_data_failures = new_data[~new_data["target_extraction_valid"]]
    changed_names = correction.loc[
        correction["status_changed"].astype(bool), "experiment_name"
    ].tolist() if len(correction) else []
    summary = {
        "phase": "Week 7 Phase 2",
        "mode": "smoke" if smoke else "full",
        "repository": SPH_V2_REPO_ID,
        "revision": SPH_V2_REVISION,
        "week6_base_commit": WEEK6_BASE_COMMIT,
        "target_row_count": len(targets),
        "successful_extraction_count": len(valid),
        "failed_extraction_count": int((~targets["target_extraction_valid"]).sum()),
        "warning_extraction_count": int(targets["extraction_status"].eq("WARNING").sum()),
        "successful_extraction_by_partition": valid.groupby("partition").size().to_dict(),
        "failed_extraction_by_partition": targets[~targets["target_extraction_valid"]].groupby("partition").size().to_dict(),
        "new_data_successful_extraction_count": int(new_data["target_extraction_valid"].sum()),
        "new_data_experiment_count": len(new_data),
        "remaining_new_data_failure_count": len(new_data_failures),
        "remaining_new_data_failures": new_data_failures[
            ["experiment_name", "extraction_failure_reasons"]
        ].to_dict(orient="records"),
        "missing_required_monitor_record_count": int((~compatibility["remote_exists"].astype(bool)).sum()),
        "monitor_incomplete_experiment_count": int(
            compatibility.loc[~compatibility["remote_exists"].astype(bool), "experiment_name"].nunique()
        ),
        "present_schema_incompatible_monitor_record_count": int(
            (compatibility["remote_exists"].astype(bool) & ~compatibility["schema_compatible"].astype(bool)).sum()
        ),
        "sentinel_variants": sentinel_audit[
            ["token", "count", "file_count", "experiment_count"]
        ].to_dict(orient="records"),
        "known_malformed_no_melt_sentinel_rule": (
            "Recognize only the exact complete field s3.402823e+38 as the ordinary "
            "+3.402823e+38 no-melt sentinel, then exclude its row with the unchanged "
            "abs(value)<1e30 rule; no generic malformed-number repair."
        ),
        "correction_status_changed_experiments": changed_names,
        "correction_status_changed_experiment_count": len(changed_names),
        "previous_valid_target_unexpected_change_count": int(
            correction["previous_valid_target_changed_unexpectedly"].fillna(False).sum()
        ) if len(correction) else 0,
        "label_context_change_count": int(
            correction["label_context_changed"].fillna(False).sum()
        ) if len(correction) else 0,
        "old_data_local_missing_monitor_maintenance_decision": (
            "Keep missing rows explicit; Ioan confirmed files may be restored later "
            "through a separate Hugging Face pull request. No backfill was performed here."
        ),
        "exact_week6_match_count": int(targets["week6_simulation_id"].astype(str).str.len().gt(0).sum()),
        "comparable_exact_week6_match_count": int(comparison_summary["exact_match_count"].max()) if len(comparison_summary) else 0,
        "exact_match_material_change_count": int(comparison_summary["materially_changed_count"].sum()) if len(comparison_summary) else 0,
        "max_depth_before_T0_count": int(valid["max_depth_relative_to_T0"].eq("before_T0").sum()),
        "max_depth_inside_T0_count": int(valid["max_depth_relative_to_T0"].eq("inside_T0").sum()),
        "max_depth_after_T0_count": int(valid["max_depth_relative_to_T0"].eq("after_T0").sum()),
        "keyhole_positive_successful_count": len(keyhole),
        "keyhole_positive_without_T0_overlap_count": int((~keyhole["keyhole_overlaps_T0"].astype(bool)).sum()),
        "depth_ambiguity_candidate_count": int(valid["flag_depth_bounding_box_ambiguity_candidate"].sum()),
        "recording_ends_before_90pct_domain_count": int(valid["recording_ends_before_90pct_domain"].sum()),
        "week6_T0_window_instability_count": int(valid["flag_primary_window_unstable_week6_rule"].sum()),
        "label_timestep_unmatched_count": int(valid["label_timestep_unmatched_count"].sum()),
        "validation": validation["status"].value_counts().to_dict(),
        "scope": {"models_fitted": False, "labels_modified": False, "simulations_removed": False, "active_learning": False, "level_set_estimation": False},
        "runtime_seconds": time.perf_counter() - started,
    }
    write_json(output_dir / "summary.json", summary)
    write_csv(output_dir / "output_manifest.csv", output_manifest(output_dir))
    print(f"Phase 2 complete: {len(valid)}/{len(targets)} valid; validation {validation['status'].value_counts().to_dict()}", flush=True)
    return summary


def refresh_phase2_validation(*, smoke: bool = False) -> dict[str, Any]:
    """Refresh notebook/visual-review validation from existing extraction outputs."""

    output_dir = SMOKE_DIR if smoke else OUTPUT_DIR
    required = [
        "sph_v2_simulation_level_targets.csv",
        "monitor_schema_compatibility.csv",
        "exact_old_new_target_comparison.csv",
        "exact_old_new_target_comparison_summary.csv",
        "domain_mapping_compatibility.csv",
        "flagged_depth_ambiguity.csv",
        "sentinel_audit.csv",
        "supervisor_correction_before_after.csv",
        "summary.json",
    ]
    missing = [name for name in required if not (output_dir / name).is_file()]
    require(not missing, f"Cannot refresh Phase 2 validation; missing outputs: {missing}")
    targets = pd.read_csv(output_dir / "sph_v2_simulation_level_targets.csv")
    compatibility = pd.read_csv(output_dir / "monitor_schema_compatibility.csv")
    compatibility = enrich_monitor_compatibility(compatibility)
    write_csv(output_dir / "monitor_schema_compatibility.csv", compatibility)
    comparison = pd.read_csv(output_dir / "exact_old_new_target_comparison.csv")
    comparison_summary = pd.read_csv(output_dir / "exact_old_new_target_comparison_summary.csv")
    domain = pd.read_csv(output_dir / "domain_mapping_compatibility.csv")
    depth_flags = pd.read_csv(output_dir / "flagged_depth_ambiguity.csv")
    sentinel_audit = pd.read_csv(output_dir / "sentinel_audit.csv")
    correction = pd.read_csv(output_dir / "supervisor_correction_before_after.csv")
    if not WEEK6_EXACT_MAP_ARTIFACT.is_file():
        write_csv(WEEK6_EXACT_MAP_ARTIFACT, week6_exact_name_map())
    review_notes_path = output_dir / "depth_visual_review_notes.csv"
    if review_notes_path.is_file():
        review_notes = pd.read_csv(review_notes_path)
        require(
            review_notes["experiment_name"].is_unique,
            "Visual-review notes must have unique experiment identifiers",
        )
        note_lookup = review_notes.set_index("experiment_name")
        for column in [
            "visual_review_status",
            "visual_review_note",
            "reviewer",
            "reviewed_at_utc",
            "visual_evidence_scope",
            "exclusion_decision",
        ]:
            mapped = depth_flags["experiment_name"].map(note_lookup[column])
            if column not in depth_flags.columns:
                depth_flags[column] = ""
            depth_flags[column] = mapped.where(mapped.notna(), depth_flags[column])
        write_csv(output_dir / "flagged_depth_ambiguity.csv", depth_flags)
    labels_all = load_partition_labels(workers=3)
    labels = labels_all[labels_all["experiment_name"].isin(targets["experiment_name"])].copy()
    # The traceability table hashes the current migration source as well as the
    # unchanged Week 6 sources, so refresh it after notebook/validation-only
    # maintenance edits.
    write_csv(output_dir / "week6_definition_traceability.csv", traceability_table())
    validation = validation_table(
        targets,
        compatibility,
        comparison,
        domain,
        labels,
        depth_flags,
        sentinel_audit,
        correction,
        smoke,
    )
    checklist = requirement_checklist(validation)
    write_csv(output_dir / "validation_results.csv", validation)
    write_csv(output_dir / "phase2_requirement_checklist.csv", checklist)
    write_csv(output_dir / "requirement_checklist.csv", checklist)
    refreshed_markdown = results_markdown(
        targets, comparison_summary, validation, sentinel_audit, correction, smoke
    )
    (output_dir / "results_summary.md").write_text(refreshed_markdown, encoding="utf-8")
    (output_dir / "phase2_results_summary.md").write_text(
        refreshed_markdown, encoding="utf-8"
    )
    summary_path = output_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["validation"] = validation["status"].value_counts().to_dict()
    valid = targets[targets["target_extraction_valid"]]
    summary["successful_extraction_by_partition"] = valid.groupby("partition").size().to_dict()
    summary["failed_extraction_by_partition"] = targets[
        ~targets["target_extraction_valid"]
    ].groupby("partition").size().to_dict()
    summary["missing_required_monitor_record_count"] = int(
        (~compatibility["remote_exists"].astype(bool)).sum()
    )
    summary["monitor_incomplete_experiment_count"] = int(
        compatibility.loc[
            ~compatibility["remote_exists"].astype(bool), "experiment_name"
        ].nunique()
    )
    summary["present_schema_incompatible_monitor_record_count"] = int(
        (
            compatibility["remote_exists"].astype(bool)
            & ~compatibility["schema_compatible"].astype(bool)
        ).sum()
    )
    summary["recording_ends_before_90pct_domain_count"] = int(
        valid["recording_ends_before_90pct_domain"].sum()
    )
    summary["week6_T0_window_instability_count"] = int(
        valid["flag_primary_window_unstable_week6_rule"].sum()
    )
    summary["label_timestep_unmatched_count"] = int(
        valid["label_timestep_unmatched_count"].sum()
    )
    summary["visual_depth_review_count"] = int(
        depth_flags.get("visual_review_status", pd.Series(dtype=str)).eq("REVIEWED").sum()
    )
    if review_notes_path.is_file():
        summary["visual_depth_review_clear_disconnected_count"] = int(
            review_notes["visual_review_note"].str.contains(
                "clearly separated", case=False, na=False
            ).sum()
        )
        summary["visual_depth_review_continuous_count"] = int(
            review_notes["visual_review_note"].str.contains(
                "continuous red melt", case=False, na=False
            ).sum()
        )
        summary["visual_depth_review_inconclusive_count"] = int(
            review_notes["visual_review_note"].str.contains(
                "inconclusive", case=False, na=False
            ).sum()
        )
    summary["validation_refreshed_at_utc"] = utc_now()
    write_json(summary_path, summary)
    contact_sheet = generate_depth_review_contact_sheet(output_dir, depth_flags)
    if contact_sheet:
        figure_manifest_path = output_dir / "figure_manifest.csv"
        figure_manifest = pd.read_csv(figure_manifest_path)
        figure_manifest = figure_manifest[
            ~figure_manifest["figure"].eq(contact_sheet["figure"])
        ]
        figure_manifest = pd.concat(
            [figure_manifest, pd.DataFrame([contact_sheet])], ignore_index=True
        )
        write_csv(figure_manifest_path, figure_manifest)
    write_csv(output_dir / "output_manifest.csv", output_manifest(output_dir))
    print(f"Phase 2 validation refreshed: {summary['validation']}", flush=True)
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument(
        "--refresh-validation-only",
        action="store_true",
        help="Refresh notebook/visual-review validation from existing outputs",
    )
    parser.add_argument("--workers", type=int, default=6)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.refresh_validation_only:
        refresh_phase2_validation(smoke=args.smoke)
    else:
        run_phase2(smoke=args.smoke, workers=args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
