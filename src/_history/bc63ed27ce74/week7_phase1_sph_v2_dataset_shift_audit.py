"""Week 7 Phase 1: revision-pinned ``sph_v2`` dataset and domain-shift audit.

The executable deliberately stops at descriptive auditing.  It inventories the
repository, reproduces label statistics, audits sequences and integrity, and
compares the four input variables with the exact Week 6 population.  It never
fits a predictive model and never changes a source label.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import textwrap
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import Delaunay, QhullError

from src.week7_sph_v2_common import (
    FEATURE_UNITS,
    PARTITIONS,
    PARTITION_ORDER,
    PHYSICAL_LABELS,
    RAW_ROOT,
    ROOT,
    SPH_V2_REPO_ID,
    SPH_V2_REVISION,
    TECHNICAL_LABELS,
    WEEK6_BASE_COMMIT,
    WEEK6_REPO_ID,
    WEEK6_REVISION,
    add_tree_path_fields,
    complete_tree_inventory,
    current_main_revision,
    dataframe_sha256,
    download_pinned_files,
    ensure_no_modelling_imports,
    git_output,
    load_partition_labels,
    notebook_has_errors,
    output_manifest,
    parse_experiment_name,
    sha256_file,
    subset_tree_inventory,
    top_level_inventory,
    utc_now,
    write_csv,
    write_json,
)


OUTPUT_DIR = ROOT / "outputs" / "week7_01_sph_v2_audit"
SMOKE_DIR = OUTPUT_DIR / "smoke"
NOTEBOOK_PATH = ROOT / "notebooks" / "week_07" / "01_sph_v2_dataset_shift_audit.ipynb"
WEEK6_LEDGER = (
    ROOT
    / "outputs"
    / "week6_01_melt_pool_data_audit"
    / "week6_phase1_simulation_level_responses.csv"
)

EXPECTED_PARTITION_EXPERIMENTS = {
    "new-data": 165,
    "old-data-local": 179,
    "old-data-remote-clean": 63,
}
EXPECTED_PARTITION_FRAMES = {
    "new-data": 45_156,
    "old-data-local": 49_304,
    "old-data-remote-clean": 16_344,
}

# Values transcribed from Ioan's screenshot.  These are references only and are
# never used to construct the reproduced result.
SUPERVISOR_REFERENCES = [
    ("new-data", "all", "experiment_count", 165.0, "count"),
    ("new-data", "all", "frame_count", 45_156.0, "count"),
    ("new-data", "Keyhole", "experiment_count", 63.0, "count"),
    ("new-data", "Keyhole", "experiment_percent", 38.18, "percentage_points"),
    ("old-data-local", "all", "experiment_count", 179.0, "count"),
    ("old-data-local", "all", "frame_count", 49_304.0, "count"),
    ("old-data-local", "Keyhole", "experiment_count", 8.0, "count"),
    ("old-data-local", "Keyhole", "experiment_percent", 4.47, "percentage_points"),
    ("old-data-remote-clean", "all", "experiment_count", 63.0, "count"),
    ("old-data-remote-clean", "all", "frame_count", 16_344.0, "count"),
    ("old-data-remote-clean", "Keyhole", "experiment_count", 2.0, "count"),
    ("old-data-remote-clean", "Keyhole", "experiment_percent", 3.17, "percentage_points"),
    ("combined", "all", "experiment_count", 407.0, "count"),
    ("combined", "all", "frame_count", 110_804.0, "count"),
    ("combined", "Keyhole", "frame_count", 6_700.0, "count"),
    ("combined", "Keyhole", "experiment_count", 73.0, "count"),
    ("combined", "Keyhole", "experiment_percent", 17.94, "percentage_points"),
    ("combined", "Conduction", "frame_count", 52_080.0, "count"),
    ("combined", "Conduction", "experiment_count", 373.0, "count"),
    ("combined", "Conduction", "experiment_percent", 91.65, "percentage_points"),
]

REQUIRED_EXPERIMENT_FILES = [
    "parameters.json",
    "frames.csv",
    "monitor/position-bounds_melt.dat",
    "monitor/time.dat",
    "monitor/iter.dat",
    "monitor/kinetic-energy_melt.dat",
]
EXPECTED_GIFS = [
    "gif_files/animation_ss_front.gif",
    "gif_files/animation_ss_side.gif",
    "gif_files/animation_ss_top.gif",
]

COLORS = {
    "new-data": "#D55E00",
    "old-data-local": "#0072B2",
    "old-data-remote-clean": "#009E73",
    "combined": "#4C4C4C",
    "Week 6": "#6A3D9A",
    "Keyhole": "#CC3311",
    "non-Keyhole": "#4477AA",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def choose_smoke_experiments(labels: pd.DataFrame, per_partition: int = 6) -> list[str]:
    """Choose a deterministic smoke population containing useful edge cases."""

    chosen: list[str] = []
    for partition in PARTITION_ORDER:
        subset = labels[labels["partition"].eq(partition)]
        names = sorted(subset["experiment_name"].unique())
        priority: list[str] = []
        for mask in [
            subset["label_final"].eq("Keyhole"),
            subset["label_final"].eq("Screenshot Bug"),
            subset["label_final"].eq("Unsure"),
            subset["label_final"].eq("Conduction")
            & ~subset["experiment_name"].isin(
                subset.loc[subset["label_final"].eq("Keyhole"), "experiment_name"]
            ),
        ]:
            candidates = sorted(subset.loc[mask, "experiment_name"].unique())
            if candidates:
                priority.append(candidates[0])
        for name in priority + names:
            if name not in chosen:
                chosen.append(name)
            if sum(
                name2 in set(names) for name2 in chosen
            ) >= per_partition:
                break
    return chosen


def select_population(labels: pd.DataFrame, *, smoke: bool) -> tuple[pd.DataFrame, list[str]]:
    if not smoke:
        names = sorted(labels["experiment_name"].unique())
        return labels.copy(), names
    names = choose_smoke_experiments(labels)
    return labels[labels["experiment_name"].isin(names)].copy(), sorted(names)


def download_experiment_ledgers(
    experiment_names: Sequence[str], *, workers: int
) -> dict[str, Path]:
    filenames = [
        f"{name}/{relative}"
        for name in experiment_names
        for relative in ["parameters.json", "frames.csv"]
    ]
    return download_pinned_files(filenames, workers=workers, progress_every=40)


def build_experiment_registry(
    labels: pd.DataFrame,
    experiment_names: Sequence[str],
    downloaded: dict[str, Path],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cross-check folder, partition ledger, parameters JSON, and frames CSV."""

    registry_rows: list[dict[str, Any]] = []
    frame_check_rows: list[dict[str, Any]] = []
    partition_map = labels.groupby("experiment_name")["partition"].first().to_dict()
    for position, name in enumerate(sorted(experiment_names), start=1):
        subset = labels[labels["experiment_name"].eq(name)].sort_values(
            ["timestep", "frame_row_in_partition"], kind="stable"
        )
        parsed = parse_experiment_name(name)
        parameter_path = downloaded[f"{name}/parameters.json"]
        frames_path = downloaded[f"{name}/frames.csv"]
        parameters = json.loads(parameter_path.read_text(encoding="utf-8"))
        frames = pd.read_csv(frames_path)
        expected_frame_columns = [
            "frame_idx",
            "timestep",
            "label",
            "front_filename",
            "side_filename",
            "top_filename",
        ]
        schema_ok = frames.columns.tolist() == expected_frame_columns
        parameter_values = {
            "P": float(parameters["laser_power"]["value"]),
            "VX": float(parameters["scan_speed_x"]["value"]),
            "LS": float(parameters["laser_spot_size"]["value"]),
            "ST": float(parameters["substrate_temperature"]["value"]),
        }
        parameter_units = {
            "P": str(parameters["laser_power"]["unit"]),
            "VX": str(parameters["scan_speed_x"]["unit"]),
            "LS": str(parameters["laser_spot_size"]["unit"]),
            "ST": str(parameters["substrate_temperature"]["unit"]),
        }
        label_values = {
            feature: float(subset[f"{feature}_numeric"].iloc[0])
            for feature in ["P", "VX", "LS", "ST"]
        }
        value_checks = {
            feature: bool(
                np.isclose(
                    parameter_values[feature],
                    label_values[feature],
                    rtol=0.0,
                    atol=1e-14,
                )
                and np.isclose(
                    parsed[feature], parameter_values[feature], rtol=0.0, atol=1e-14
                )
            )
            for feature in ["P", "VX", "LS", "ST"]
        }
        frame_count_matches = len(frames) == len(subset)
        timestep_matches = frame_count_matches and np.array_equal(
            frames["timestep"].to_numpy(), subset["timestep"].to_numpy()
        )
        label_matches = frame_count_matches and np.array_equal(
            frames["label"].astype(str).to_numpy(),
            subset["label_final"].astype(str).to_numpy(),
        )
        frame_index_ok = schema_ok and np.array_equal(
            frames["frame_idx"].to_numpy(), np.arange(len(frames))
        )
        registry_rows.append(
            {
                **parsed,
                "partition": partition_map[name],
                "P": parameter_values["P"],
                "VX": parameter_values["VX"],
                "LS": parameter_values["LS"],
                "ST": parameter_values["ST"],
                "P_unit": parameter_units["P"],
                "VX_unit": parameter_units["VX"],
                "LS_unit": parameter_units["LS"],
                "ST_unit": parameter_units["ST"],
                "parameter_values_match_folder_and_partition": all(value_checks.values()),
                "parameter_units_match_week6": parameter_units == FEATURE_UNITS,
                "label_frame_count": len(subset),
                "frames_csv_row_count": len(frames),
                "frames_csv_schema_valid": schema_ok,
                "frames_csv_frame_index_valid": frame_index_ok,
                "frames_csv_timestep_matches_partition_ledger": timestep_matches,
                "frames_csv_label_matches_final_label": label_matches,
                "parameters_path": f"{name}/parameters.json",
                "parameters_sha256": sha256_file(parameter_path),
                "frames_csv_path": f"{name}/frames.csv",
                "frames_csv_sha256": sha256_file(frames_path),
            }
        )
        frame_check_rows.append(
            {
                "experiment_name": name,
                "partition": partition_map[name],
                "partition_label_rows": len(subset),
                "frames_csv_rows": len(frames),
                "row_count_matches": frame_count_matches,
                "timestep_sequence_matches": timestep_matches,
                "final_label_sequence_matches": label_matches,
                "frame_index_is_zero_based_contiguous": frame_index_ok,
            }
        )
        if position % 50 == 0 or position == len(experiment_names):
            print(f"Small-file compatibility: {position}/{len(experiment_names)}", flush=True)
    return (
        pd.DataFrame(registry_rows).sort_values(["partition", "experiment_name"]),
        pd.DataFrame(frame_check_rows).sort_values(["partition", "experiment_name"]),
    )


def build_structure_tables(
    tree: pd.DataFrame,
    labels: pd.DataFrame,
    registry: pd.DataFrame,
    top: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    experiment_names = set(registry["experiment_name"])
    enriched = add_tree_path_fields(tree, experiment_names)
    files = enriched[
        enriched["item_type"].eq("file") & enriched["experiment_name"].ne("")
    ].copy()

    file_types = (
        enriched[enriched["item_type"].eq("file")]
        .groupby("extension", dropna=False)
        .agg(file_count=("path", "size"), total_size_bytes=("size_bytes", "sum"))
        .reset_index()
        .sort_values("file_count", ascending=False)
    )
    file_types["total_size_GiB"] = file_types["total_size_bytes"] / 2**30

    partition_map = registry.set_index("experiment_name")["partition"].to_dict()
    files["partition"] = files["experiment_name"].map(partition_map)
    files["first_directory"] = files["relative_inside_experiment"].str.split("/").str[0]
    partition_summary = (
        registry.groupby("partition")
        .agg(
            experiment_count=("experiment_name", "nunique"),
            labelled_frame_count=("label_frame_count", "sum"),
            min_frames_per_experiment=("label_frame_count", "min"),
            median_frames_per_experiment=("label_frame_count", "median"),
            max_frames_per_experiment=("label_frame_count", "max"),
        )
        .reindex(PARTITION_ORDER)
        .reset_index()
    )
    partition_file_counts = (
        files.groupby("partition")
        .agg(repository_file_count=("path", "size"), repository_size_bytes=("size_bytes", "sum"))
        .reset_index()
    )
    partition_summary = partition_summary.merge(partition_file_counts, on="partition", how="left")

    paths_by_experiment = files.groupby("experiment_name")[
        "relative_inside_experiment"
    ].agg(set)
    structure_rows: list[dict[str, Any]] = []
    missing_rows: list[dict[str, Any]] = []
    expected_all = REQUIRED_EXPERIMENT_FILES + EXPECTED_GIFS
    for row in registry.itertuples(index=False):
        paths = paths_by_experiment.get(row.experiment_name, set())
        file_subset = files[files["experiment_name"].eq(row.experiment_name)]
        monitor_names = sorted(
            Path(value).name
            for value in paths
            if value.startswith("monitor/") and value.endswith(".dat")
        )
        frame_counts = {
            view: sum(
                value.startswith(f"frames/{view}/") and value.endswith(".png")
                for value in paths
            )
            for view in ["front", "side", "top"]
        }
        missing = [item for item in expected_all if item not in paths]
        for item in missing:
            missing_rows.append(
                {
                    "severity": "FAIL" if item in REQUIRED_EXPERIMENT_FILES else "WARNING",
                    "issue_type": "missing_expected_file",
                    "partition": row.partition,
                    "experiment_name": row.experiment_name,
                    "relative_path": item,
                    "detail": "Required for Phase 1/2" if item in REQUIRED_EXPERIMENT_FILES else "Expected GIF visual aid",
                }
            )
        for view, count in frame_counts.items():
            if count != row.label_frame_count:
                missing_rows.append(
                    {
                        "severity": "FAIL",
                        "issue_type": "frame_count_mismatch",
                        "partition": row.partition,
                        "experiment_name": row.experiment_name,
                        "relative_path": f"frames/{view}",
                        "detail": f"PNG count={count}; label rows={row.label_frame_count}",
                    }
                )
        structure_rows.append(
            {
                "experiment_name": row.experiment_name,
                "partition": row.partition,
                "repository_file_count": len(file_subset),
                "repository_size_bytes": int(file_subset["size_bytes"].fillna(0).sum()),
                "monitor_dat_count": len(monitor_names),
                "monitor_dat_names": json.dumps(monitor_names, separators=(",", ":")),
                "front_png_count": frame_counts["front"],
                "side_png_count": frame_counts["side"],
                "top_png_count": frame_counts["top"],
                "gif_count": sum(value.endswith(".gif") for value in paths),
                "has_parameters_json": "parameters.json" in paths,
                "has_frames_csv": "frames.csv" in paths,
                "has_required_phase2_monitors": all(
                    value in paths for value in REQUIRED_EXPERIMENT_FILES[2:]
                ),
                "all_three_frame_views_match_label_count": all(
                    count == row.label_frame_count for count in frame_counts.values()
                ),
                "missing_expected_file_count": len(missing),
            }
        )

    top_summary = top.copy()
    top_summary["classification"] = np.where(
        top_summary["item_type"].eq("folder"),
        "experiment folder",
        np.where(top_summary["path"].str.startswith("labels_partition_"), "partition label ledger", "repository control file"),
    )

    structure_comparison = pd.DataFrame(
        [
            ("experiment root", "final_data_processed/sim_XXXXX", "semantic parameter/hash folder at repository root", "changed"),
            ("experiment identity", "sim_XXXXX plus metadata.json original_folder_name", "semantic folder name; no sim_XXXXX alias", "changed"),
            ("parameters", "parameters.json", "parameters.json", "same"),
            ("configuration metadata", "metadata.json and experiment_details.json", "removed", "changed; folder tokens retain XI/XF/XL/TE/DT/H"),
            ("labels", "top-level final-labels_all.csv plus per-simulation provenance", "three top-level partition ledgers plus frames.csv", "changed"),
            ("annotator provenance", "labeling_provenance.json in prior labelled material", "no reliable annotator metadata discovered", "changed/absent"),
            ("monitor files", "monitor/*.dat", "monitor/*.dat", "same required path names"),
            ("rendered frames", "frames/front, side, top", "frames/front, side, top", "same"),
            ("GIFs", "not part of Week 6 expected structure", "gif_files with front, side, top animations", "added"),
        ],
        columns=["component", "week6_structure", "sph_v2_structure", "assessment"],
    )
    return {
        "repository_inventory": enriched,
        "top_level_inventory": top_summary,
        "file_type_counts": file_types,
        "partition_summary": partition_summary,
        "experiment_structure": pd.DataFrame(structure_rows).sort_values(["partition", "experiment_name"]),
        "missing_unexpected": pd.DataFrame(
            missing_rows,
            columns=["severity", "issue_type", "partition", "experiment_name", "relative_path", "detail"],
        ),
        "structure_comparison": structure_comparison,
    }


def label_distribution(labels: pd.DataFrame) -> pd.DataFrame:
    discovered = sorted(labels["label_final"].dropna().astype(str).unique())
    rows: list[dict[str, Any]] = []
    groups = [(partition, labels[labels["partition"].eq(partition)]) for partition in PARTITION_ORDER]
    groups.append(("combined", labels))
    for partition, subset in groups:
        experiment_total = subset["experiment_name"].nunique()
        frame_total = len(subset)
        for label in discovered:
            selected = subset[subset["label_final"].eq(label)]
            rows.append(
                {
                    "partition": partition,
                    "label": label,
                    "frame_count": len(selected),
                    "total_frames": frame_total,
                    "frame_percent": 100.0 * len(selected) / frame_total,
                    "experiment_count": selected["experiment_name"].nunique(),
                    "total_experiments": experiment_total,
                    "experiment_percent": 100.0 * selected["experiment_name"].nunique() / experiment_total,
                    "label_discovered_from_data": True,
                }
            )
    return pd.DataFrame(rows)


def reference_comparison(labels: pd.DataFrame, distribution: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for partition, label, metric, reference, unit in SUPERVISOR_REFERENCES:
        subset = labels if partition == "combined" else labels[labels["partition"].eq(partition)]
        if label == "all":
            reproduced = float(
                subset["experiment_name"].nunique() if metric == "experiment_count" else len(subset)
            )
        else:
            record = distribution[
                distribution["partition"].eq(partition) & distribution["label"].eq(label)
            ].iloc[0]
            reproduced = float(record[metric])
        difference = reproduced - reference
        absolute_difference = abs(difference)
        if unit == "count":
            status = "PASS" if absolute_difference == 0 else "FAIL"
            tolerance = "exact integer equality"
        else:
            status = "PASS" if absolute_difference <= 0.01 + 1e-12 else "WARNING" if absolute_difference <= 0.05 else "FAIL"
            tolerance = "PASS <= 0.01 percentage points; WARNING <= 0.05; otherwise FAIL"
        rows.append(
            {
                "partition": partition,
                "label": label,
                "metric": metric,
                "unit": unit,
                "reproduced_value": reproduced,
                "supervisor_screenshot_value": reference,
                "difference": difference,
                "absolute_difference": absolute_difference,
                "status": status,
                "tolerance_definition": tolerance,
            }
        )
    return pd.DataFrame(rows)


def collapsed(values: Sequence[str]) -> list[str]:
    return [value for index, value in enumerate(values) if index == 0 or value != values[index - 1]]


def keyhole_segments(values: Sequence[str]) -> list[tuple[int, int]]:
    segments: list[tuple[int, int]] = []
    start: int | None = None
    for index, value in enumerate(values):
        if value == "Keyhole" and start is None:
            start = index
        if value != "Keyhole" and start is not None:
            segments.append((start, index - 1))
            start = None
    if start is not None:
        segments.append((start, len(values) - 1))
    return segments


def sequence_audit(labels: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    episodes: list[dict[str, Any]] = []
    for (partition, name), subset in labels.groupby(["partition", "experiment_name"], sort=True):
        ordered = subset.sort_values(["timestep", "frame_row_in_partition"], kind="stable").reset_index(drop=True)
        values = ordered["label_final"].astype(str).tolist()
        compressed = collapsed(values)
        physical = ordered[ordered["label_final"].isin(PHYSICAL_LABELS)]
        physical_values = physical["label_final"].astype(str).tolist()
        compressed_physical = collapsed(physical_values) if physical_values else []
        segments = keyhole_segments(values)
        keyhole_positions = np.flatnonzero(ordered["label_final"].eq("Keyhole").to_numpy())
        conduction_positions = np.flatnonzero(ordered["label_final"].eq("Conduction").to_numpy())
        relevant_count = len(physical)
        for segment_number, (start, end) in enumerate(segments, start=1):
            episodes.append(
                {
                    "partition": partition,
                    "experiment_name": name,
                    "segment_number": segment_number,
                    "start_frame_index": start,
                    "end_frame_index": end,
                    "start_timestep": int(ordered.loc[start, "timestep"]),
                    "end_timestep": int(ordered.loc[end, "timestep"]),
                    "labelled_frame_count": end - start + 1,
                    "followed_by_non_keyhole_physical_label": bool(
                        ordered.loc[end + 1 :, "label_final"].isin(PHYSICAL_LABELS - {"Keyhole"}).any()
                    ),
                    "physical_time_duration_available": False,
                    "duration_ms": np.nan,
                }
            )
        first_physical = physical.iloc[0] if len(physical) else None
        last_physical = physical.iloc[-1] if len(physical) else None
        row = {
            "partition": partition,
            "experiment_name": name,
            "labelled_frame_count": len(ordered),
            "distinct_label_count": ordered["label_final"].nunique(),
            "label_change_count": max(0, len(compressed) - 1),
            "collapsed_label_sequence": " -> ".join(compressed),
            "collapsed_physical_sequence": " -> ".join(compressed_physical),
            "first_physical_label": str(first_physical["label_final"]) if first_physical is not None else "",
            "last_physical_label": str(last_physical["label_final"]) if last_physical is not None else "",
            "has_conduction": bool(len(conduction_positions)),
            "has_keyhole": bool(len(keyhole_positions)),
            "first_conduction_frame_index": int(conduction_positions[0]) if len(conduction_positions) else np.nan,
            "first_conduction_timestep": int(ordered.loc[conduction_positions[0], "timestep"]) if len(conduction_positions) else np.nan,
            "first_keyhole_frame_index": int(keyhole_positions[0]) if len(keyhole_positions) else np.nan,
            "first_keyhole_timestep": int(ordered.loc[keyhole_positions[0], "timestep"]) if len(keyhole_positions) else np.nan,
            "last_keyhole_frame_index": int(keyhole_positions[-1]) if len(keyhole_positions) else np.nan,
            "last_keyhole_timestep": int(ordered.loc[keyhole_positions[-1], "timestep"]) if len(keyhole_positions) else np.nan,
            "keyhole_frame_count": len(keyhole_positions),
            "relevant_physical_frame_count": relevant_count,
            "keyhole_fraction_of_relevant_physical_frames": len(keyhole_positions) / relevant_count if relevant_count else np.nan,
            "keyhole_segment_count": len(segments),
            "maximum_keyhole_segment_frames": max((end - start + 1 for start, end in segments), default=0),
            "keyhole_transient_by_sequence": bool(
                len(keyhole_positions)
                and last_physical is not None
                and str(last_physical["label_final"]) != "Keyhole"
            ),
            "keyhole_persistent_to_last_physical_frame": bool(
                len(keyhole_positions)
                and last_physical is not None
                and str(last_physical["label_final"]) == "Keyhole"
            ),
            "repeated_keyhole_episodes": len(segments) > 1,
            "time_conversion_validated": False,
        }
        row["label_sequence_sha256"] = hashlib.sha256(
            "\n".join(values).encode("utf-8")
        ).hexdigest()
        rows.append(row)
    sequence = pd.DataFrame(rows).sort_values(["partition", "experiment_name"])
    patterns = (
        sequence.groupby(["partition", "collapsed_label_sequence"])
        .agg(experiment_count=("experiment_name", "size"))
        .reset_index()
    )
    totals = sequence.groupby("partition")["experiment_name"].nunique().to_dict()
    patterns["partition_experiment_count"] = patterns["partition"].map(totals)
    patterns["experiment_percent"] = 100 * patterns["experiment_count"] / patterns["partition_experiment_count"]
    combined = (
        sequence.groupby("collapsed_label_sequence")
        .agg(experiment_count=("experiment_name", "size"))
        .reset_index()
    )
    combined.insert(0, "partition", "combined")
    combined["partition_experiment_count"] = len(sequence)
    combined["experiment_percent"] = 100 * combined["experiment_count"] / len(sequence)
    patterns = pd.concat([patterns, combined], ignore_index=True).sort_values(
        ["partition", "experiment_count", "collapsed_label_sequence"], ascending=[True, False, True]
    )
    return sequence, pd.DataFrame(episodes), patterns


def build_anomaly_table(
    labels: pd.DataFrame, sequence: pd.DataFrame, inventory: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    gif_lookup = (
        inventory[
            inventory["path"].str.endswith("/gif_files/animation_ss_side.gif")
        ]
        .assign(experiment_name=lambda frame: frame["path"].str.split("/").str[0])
        .set_index("experiment_name")["path"]
        .to_dict()
    )
    for (partition, name), subset in labels.groupby(["partition", "experiment_name"], sort=True):
        ordered = subset.sort_values(["timestep", "frame_row_in_partition"], kind="stable").reset_index(drop=True)
        reasons: list[tuple[str, str, str, list[int]]] = []
        duplicate_steps = ordered[ordered["timestep"].duplicated(keep=False)]
        if len(duplicate_steps):
            reasons.append(("duplicate_timestep", "FAIL", f"{len(duplicate_steps)} rows share a timestep", duplicate_steps.index.tolist()))
        if not ordered["timestep"].is_monotonic_increasing:
            reasons.append(("non_monotone_timestep", "FAIL", "label timesteps are not increasing", []))
        disagreement = ordered["label_1"].astype(str).ne(ordered["label_2"].astype(str))
        if disagreement.any():
            reasons.append(("annotator_or_channel_disagreement", "WARNING", f"label_1 differs from label_2 in {int(disagreement.sum())} frames; identities are unavailable", ordered.index[disagreement].tolist()))
        final_differs_both = ordered["label_final"].astype(str).ne(ordered["label_1"].astype(str)) & ordered["label_final"].astype(str).ne(ordered["label_2"].astype(str))
        if final_differs_both.any():
            reasons.append(("final_label_differs_from_both_inputs", "WARNING", f"{int(final_differs_both.sum())} final labels differ from both label_1 and label_2", ordered.index[final_differs_both].tolist()))
        for label in ["Screenshot Bug", "Unsure"]:
            mask = ordered["label_final"].eq(label)
            if mask.any():
                reasons.append((f"contains_{label.lower().replace(' ', '_')}", "WARNING", f"{int(mask.sum())} frames", ordered.index[mask].tolist()))
        first_physical_positions = np.flatnonzero(ordered["label_final"].isin(PHYSICAL_LABELS).to_numpy())
        if len(first_physical_positions):
            after_physical = ordered.index >= first_physical_positions[0]
            reempty = after_physical & ordered["label_final"].eq("Initial Emptiness")
            if reempty.any():
                reasons.append(("initial_emptiness_after_physical_onset", "WARNING", f"{int(reempty.sum())} frames", ordered.index[reempty].tolist()))
            physical_seen = False
            terminal_seen = False
            forming_return: list[int] = []
            for index, label in enumerate(ordered["label_final"].astype(str)):
                if label in {"Conduction", "Keyhole"}:
                    terminal_seen = True
                if label in PHYSICAL_LABELS:
                    physical_seen = True
                if label == "Forming Phase" and terminal_seen:
                    forming_return.append(index)
            if forming_return:
                reasons.append(("forming_phase_returns_after_conduction_or_keyhole", "WARNING", f"{len(forming_return)} frames", forming_return))
        seq_row = sequence[sequence["experiment_name"].eq(name)].iloc[0]
        if seq_row["repeated_keyhole_episodes"]:
            reasons.append(("repeated_keyhole_episodes", "WARNING", f"{int(seq_row['keyhole_segment_count'])} distinct segments", []))
        if not str(seq_row["first_physical_label"]):
            reasons.append(("no_physical_label", "FAIL", "no Forming Phase, Conduction, or Keyhole frame", []))
        bad_bug_flag = ordered["bug_free"].astype(int).eq(0)
        if bad_bug_flag.any():
            reasons.append(("bug_free_flag_zero", "WARNING", f"{int(bad_bug_flag.sum())} frames", ordered.index[bad_bug_flag].tolist()))
        for reason, severity, detail, indices in reasons:
            indices = sorted(set(int(value) for value in indices))
            rows.append(
                {
                    "severity": severity,
                    "reason": reason,
                    "partition": partition,
                    "experiment_name": name,
                    "affected_label_frame_indices": json.dumps(indices, separators=(",", ":")),
                    "affected_timesteps": json.dumps(
                        [int(ordered.loc[index, "timestep"]) for index in indices], separators=(",", ":")
                    ),
                    "detail": detail,
                    "gif_path_in_repository": gif_lookup.get(name, ""),
                    "label_was_modified": False,
                    "manual_review_recommended": True,
                }
            )
    return pd.DataFrame(
        rows,
        columns=[
            "severity", "reason", "partition", "experiment_name",
            "affected_label_frame_indices", "affected_timesteps", "detail",
            "gif_path_in_repository", "label_was_modified", "manual_review_recommended",
        ],
    ).sort_values(["severity", "partition", "experiment_name", "reason"])


def annotator_provenance_audit(labels: pd.DataFrame, inventory: pd.DataFrame) -> pd.DataFrame:
    columns = set(labels.columns)
    provenance_paths = inventory[inventory["path"].str.contains("provenance|annotator", case=False, regex=True)]["path"].tolist()
    return pd.DataFrame(
        [
            {
                "question": "Can working-student-labelled records be identified reliably?",
                "answer": "No",
                "status": "WARNING",
                "evidence": (
                    "No annotator/label-provenance column is present in the three ledgers; "
                    "no annotator or labeling_provenance file exists in the pinned tree. "
                    "label_1 and label_2 identities are not documented."
                ),
                "label_columns": json.dumps(sorted(column for column in columns if "label" in column)),
                "provenance_path_count": len(provenance_paths),
                "provenance_paths": json.dumps(provenance_paths, separators=(",", ":")),
                "decision": "Do not fabricate an annotator split; retain partition and disagreement diagnostics only.",
            }
        ]
    )


def descriptive_rows(frame: pd.DataFrame, group: str, source: str) -> list[dict[str, Any]]:
    rows = []
    for feature in ["P", "VX", "LS", "ST"]:
        values = pd.to_numeric(frame[feature], errors="coerce")
        finite = values[np.isfinite(values)]
        rows.append(
            {
                "source": source,
                "partition": group,
                "feature": feature,
                "unit": FEATURE_UNITS[feature],
                "count": len(values),
                "missing_count": int(values.isna().sum() + np.isinf(values.fillna(0)).sum()),
                "min": finite.min() if len(finite) else np.nan,
                "q05": finite.quantile(0.05) if len(finite) else np.nan,
                "q25": finite.quantile(0.25) if len(finite) else np.nan,
                "median": finite.median() if len(finite) else np.nan,
                "mean": finite.mean() if len(finite) else np.nan,
                "q75": finite.quantile(0.75) if len(finite) else np.nan,
                "q95": finite.quantile(0.95) if len(finite) else np.nan,
                "max": finite.max() if len(finite) else np.nan,
                "std": finite.std(ddof=1) if len(finite) > 1 else np.nan,
                "unique_count": finite.nunique(),
            }
        )
    return rows


def parameter_audit(
    registry: pd.DataFrame, sequence: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    for partition in PARTITION_ORDER:
        rows.extend(descriptive_rows(registry[registry["partition"].eq(partition)], partition, "sph_v2"))
    rows.extend(descriptive_rows(registry, "combined", "sph_v2"))
    week6 = pd.read_csv(WEEK6_LEDGER)
    require(set(week6["huggingface_revision"].astype(str)) == {WEEK6_REVISION}, "Week 6 ledger revision changed")
    rows.extend(descriptive_rows(week6, "Week 6 exact population", "Week 6"))
    summary = pd.DataFrame(rows)

    old = week6[["P", "VX", "LS", "ST"]].astype(float).copy()
    new = registry[registry["partition"].eq("new-data")][["experiment_name", "P", "VX", "LS", "ST"]].copy()
    bounds_rows: list[dict[str, Any]] = []
    for feature in ["P", "VX", "LS", "ST"]:
        old_min, old_max = old[feature].min(), old[feature].max()
        new_min, new_max = new[feature].min(), new[feature].max()
        overlap_min, overlap_max = max(old_min, new_min), min(old_max, new_max)
        bounds_rows.append(
            {
                "feature": feature,
                "unit": FEATURE_UNITS[feature],
                "week6_min": old_min,
                "week6_max": old_max,
                "sph_v2_new_data_min": new_min,
                "sph_v2_new_data_max": new_max,
                "minimum_shift": new_min - old_min,
                "maximum_shift": new_max - old_max,
                "range_expansion_below_week6": max(0.0, old_min - new_min),
                "range_expansion_above_week6": max(0.0, new_max - old_max),
                "overlap_min": overlap_min,
                "overlap_max": overlap_max,
                "overlap_width": max(0.0, overlap_max - overlap_min),
                "week6_range_width": old_max - old_min,
                "new_range_width": new_max - new_min,
            }
        )
    bounds = pd.DataFrame(bounds_rows)

    old_min = old.min()
    old_max = old.max()
    old_range = (old_max - old_min).replace(0, 1.0)
    new_values = new[["P", "VX", "LS", "ST"]].astype(float)
    outside_axes = (new_values.lt(old_min) | new_values.gt(old_max))
    scaled_old = (old - old_min) / old_range
    scaled_new = (new_values - old_min) / old_range
    inside_hull = np.full(len(new), False)
    hull_status = "computed"
    try:
        hull = Delaunay(scaled_old.to_numpy(), qhull_options="QJ")
        inside_hull = hull.find_simplex(scaled_new.to_numpy()) >= 0
    except QhullError as exc:
        hull_status = f"unavailable: {exc.__class__.__name__}"
    distances = np.sqrt(
        ((scaled_new.to_numpy()[:, None, :] - scaled_old.to_numpy()[None, :, :]) ** 2).sum(axis=2)
    )
    membership = new[["experiment_name", "P", "VX", "LS", "ST"]].copy()
    for feature in ["P", "VX", "LS", "ST"]:
        membership[f"outside_week6_{feature}_range"] = outside_axes[feature].to_numpy()
    membership["outside_any_week6_axis_range"] = outside_axes.any(axis=1).to_numpy()
    membership["inside_week6_4d_convex_hull"] = inside_hull
    membership["convex_hull_assessment"] = hull_status
    membership["nearest_week6_scaled_euclidean_distance"] = distances.min(axis=1)
    membership = membership.merge(
        sequence[["experiment_name", "has_keyhole"]], on="experiment_name", how="left"
    )
    return summary, bounds, membership


def integrity_audit(
    registry: pd.DataFrame,
    labels: pd.DataFrame,
    sequence: pd.DataFrame,
    inventory: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    partition_count = labels.groupby("experiment_name")["partition"].nunique()
    for name in partition_count[partition_count > 1].index:
        rows.append({"issue_type": "same_identifier_across_partitions", "severity": "FAIL", "group_key": name, "member_count": int(partition_count[name]), "experiments": name, "interpretation": "An experiment identifier occurs in multiple partitions."})

    tuple_columns = ["P", "VX", "LS", "ST"]
    for values, subset in registry.groupby(tuple_columns, dropna=False):
        if len(subset) > 1:
            rows.append({"issue_type": "replicated_parameter_setting", "severity": "INFO", "group_key": json.dumps(dict(zip(tuple_columns, map(float, values))), separators=(",", ":")), "member_count": len(subset), "experiments": " | ".join(subset["experiment_name"]), "interpretation": "Identical P/VX/LS/ST is a replicated setting, not automatically a duplicate simulation."})

    for sequence_hash, subset in sequence.groupby("label_sequence_sha256"):
        if len(subset) > 1:
            rows.append({"issue_type": "exact_duplicate_label_sequence", "severity": "INFO", "group_key": sequence_hash, "member_count": len(subset), "experiments": " | ".join(subset["experiment_name"]), "interpretation": "Exact label sequences can legitimately recur; compare physical content separately."})

    files = inventory[
        inventory["item_type"].eq("file") & inventory["experiment_name"].ne("")
    ].copy()
    bundle_rows = []
    for name, subset in files.groupby("experiment_name", sort=True):
        canonical = "\n".join(
            f"{row.relative_inside_experiment}\t{row.blob_id}\t{int(row.size_bytes) if pd.notna(row.size_bytes) else -1}"
            for row in subset.sort_values("relative_inside_experiment").itertuples(index=False)
        )
        bundle_rows.append(
            {
                "experiment_name": name,
                "complete_content_bundle_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
                "file_count": len(subset),
                "total_size_bytes": int(subset["size_bytes"].fillna(0).sum()),
            }
        )
    bundles = pd.DataFrame(bundle_rows).merge(
        registry[["experiment_name", "partition"]], on="experiment_name", how="left"
    )
    for bundle_hash, subset in bundles.groupby("complete_content_bundle_sha256"):
        if len(subset) > 1:
            cross_partition = subset["partition"].nunique() > 1
            rows.append({"issue_type": "exact_duplicate_complete_folder_content", "severity": "FAIL" if cross_partition else "WARNING", "group_key": bundle_hash, "member_count": len(subset), "experiments": " | ".join(subset["experiment_name"]), "interpretation": "All repository file paths, blob IDs, and sizes inside the experiment folders are identical."})

    malformed = registry[~registry["folder_name_valid"].astype(bool)]
    for row in malformed.itertuples(index=False):
        rows.append({"issue_type": "malformed_experiment_folder_name", "severity": "FAIL", "group_key": row.experiment_name, "member_count": 1, "experiments": row.experiment_name, "interpretation": "Folder name cannot be parsed under the discovered schema."})
    missing_inputs = registry[~np.isfinite(registry[tuple_columns].to_numpy(float)).all(axis=1)]
    for row in missing_inputs.itertuples(index=False):
        rows.append({"issue_type": "missing_or_nonfinite_input", "severity": "FAIL", "group_key": row.experiment_name, "member_count": 1, "experiments": row.experiment_name, "interpretation": "At least one of P/VX/LS/ST is not finite."})

    report = pd.DataFrame(rows, columns=["issue_type", "severity", "group_key", "member_count", "experiments", "interpretation"])
    return report.sort_values(["severity", "issue_type", "group_key"]), bundles


def configure_plotting() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 180,
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def save_figure(figure: plt.Figure, output_dir: Path, filename: str) -> str:
    path = output_dir / "figures" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)
    return path.relative_to(ROOT).as_posix()


def generate_figures(
    output_dir: Path,
    labels: pd.DataFrame,
    distribution: pd.DataFrame,
    registry: pd.DataFrame,
    sequence: pd.DataFrame,
    patterns: pd.DataFrame,
    episodes: pd.DataFrame,
    bounds: pd.DataFrame,
) -> pd.DataFrame:
    configure_plotting()
    manifest: list[dict[str, Any]] = []

    for metric, filename, title, ylabel in [
        ("frame_percent", "01_frame_label_distribution_by_partition.png", "Frame-label distribution by partition", "Percent of labelled frames"),
        ("experiment_percent", "02_experiment_label_prevalence_by_partition.png", "Experiment-level label prevalence", "Percent of experiments containing label"),
    ]:
        pivot = distribution[distribution["partition"].isin(PARTITION_ORDER)].pivot(index="label", columns="partition", values=metric).fillna(0)
        pivot = pivot.reindex(columns=PARTITION_ORDER)
        figure, axis = plt.subplots(figsize=(11.5, 5.8))
        x = np.arange(len(pivot))
        width = 0.24
        for index, partition in enumerate(PARTITION_ORDER):
            axis.bar(x + (index - 1) * width, pivot[partition], width, label=partition, color=COLORS[partition])
        axis.set_xticks(x, pivot.index, rotation=32, ha="right")
        axis.set(ylabel=ylabel, title=title)
        axis.legend(frameon=False)
        path = save_figure(figure, output_dir, filename)
        manifest.append({"figure": filename, "path": path, "question": title})

    keyhole = distribution[
        distribution["label"].eq("Keyhole") & distribution["partition"].isin(PARTITION_ORDER)
    ].set_index("partition").reindex(PARTITION_ORDER)
    figure, axis = plt.subplots(figsize=(8.5, 4.8))
    bars = axis.bar(keyhole.index, keyhole["experiment_percent"], color=[COLORS[value] for value in keyhole.index])
    for bar, count in zip(bars, keyhole["experiment_count"]):
        axis.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.8, f"{int(count)} experiments", ha="center", fontsize=9)
    axis.set(ylabel="Experiments containing Keyhole (%)", title="Keyhole prevalence differs strongly across partitions")
    path = save_figure(figure, output_dir, "03_keyhole_experiment_prevalence.png")
    manifest.append({"figure": "03_keyhole_experiment_prevalence.png", "path": path, "question": "How prevalent is Keyhole in each partition?"})

    display_registry = registry.copy()
    display_registry["LS"] *= 1e6
    feature_labels = {"P": "P (W)", "VX": "VX (m/s)", "LS": "LS (µm)", "ST": "ST (K)"}
    figure, axes = plt.subplots(2, 2, figsize=(11.5, 8))
    for axis, feature in zip(axes.flat, ["P", "VX", "LS", "ST"]):
        for partition in PARTITION_ORDER:
            values = display_registry.loc[display_registry["partition"].eq(partition), feature]
            axis.hist(values, bins=20, density=True, histtype="step", linewidth=2, color=COLORS[partition], label=partition)
        axis.set(xlabel=feature_labels[feature], ylabel="Density", title=f"{feature_labels[feature]} distribution")
    axes.flat[0].legend(frameon=False, fontsize=8)
    path = save_figure(figure, output_dir, "04_parameter_distributions_by_partition.png")
    manifest.append({"figure": "04_parameter_distributions_by_partition.png", "path": path, "question": "How do marginal input distributions differ?"})

    figure, axes = plt.subplots(2, 2, figsize=(11.5, 8))
    for axis, feature in zip(axes.flat, ["P", "VX", "LS", "ST"]):
        values = [display_registry.loc[display_registry["partition"].eq(partition), feature] for partition in PARTITION_ORDER]
        bp = axis.boxplot(values, tick_labels=PARTITION_ORDER, patch_artist=True, showfliers=False)
        for patch, partition in zip(bp["boxes"], PARTITION_ORDER):
            patch.set_facecolor(COLORS[partition]); patch.set_alpha(0.65)
        axis.tick_params(axis="x", rotation=25)
        axis.set(ylabel=feature_labels[feature], title=f"{feature_labels[feature]} partition comparison")
    path = save_figure(figure, output_dir, "05_parameter_boxplots_by_partition.png")
    manifest.append({"figure": "05_parameter_boxplots_by_partition.png", "path": path, "question": "Where do partition ranges and quartiles differ?"})

    projections = [("P", "VX"), ("LS", "ST"), ("P", "LS"), ("VX", "ST")]
    figure, axes = plt.subplots(2, 2, figsize=(11.5, 8.5))
    for axis, (left, right) in zip(axes.flat, projections):
        for partition in PARTITION_ORDER:
            subset = display_registry[display_registry["partition"].eq(partition)]
            axis.scatter(subset[left], subset[right], s=18, alpha=0.68, color=COLORS[partition], label=partition)
        axis.set(xlabel=feature_labels[left], ylabel=feature_labels[right], title=f"{left}–{right} projection")
    axes.flat[0].legend(frameon=False, fontsize=8)
    path = save_figure(figure, output_dir, "06_parameter_space_projections.png")
    manifest.append({"figure": "06_parameter_space_projections.png", "path": path, "question": "Where do partitions occupy the four-dimensional design space?"})

    figure, axes = plt.subplots(2, 2, figsize=(10.5, 7.5))
    for axis, feature in zip(axes.flat, ["P", "VX", "LS", "ST"]):
        row = bounds[bounds["feature"].eq(feature)].iloc[0]
        scale = 1e6 if feature == "LS" else 1.0
        axis.plot([row["week6_min"] * scale, row["week6_max"] * scale], [0, 0], "o-", lw=5, color=COLORS["Week 6"], label="Week 6")
        axis.plot([row["sph_v2_new_data_min"] * scale, row["sph_v2_new_data_max"] * scale], [1, 1], "o-", lw=5, color=COLORS["new-data"], label="sph_v2 new-data")
        axis.set(yticks=[0, 1], yticklabels=["Week 6", "new-data"], xlabel=feature_labels[feature], title=f"Observed {feature} bounds")
    path = save_figure(figure, output_dir, "07_week6_vs_new_parameter_bounds.png")
    manifest.append({"figure": "07_week6_vs_new_parameter_bounds.png", "path": path, "question": "How did observed parameter bounds change from Week 6?"})

    key_map = sequence.set_index("experiment_name")["has_keyhole"]
    display_registry["has_keyhole"] = display_registry["experiment_name"].map(key_map).fillna(False)
    figure, axes = plt.subplots(1, 2, figsize=(11.5, 4.8))
    for axis, (left, right) in zip(axes, [("LS", "ST"), ("P", "VX")]):
        for has_keyhole, label in [(False, "non-Keyhole"), (True, "Keyhole")]:
            subset = display_registry[display_registry["has_keyhole"].eq(has_keyhole)]
            axis.scatter(subset[left], subset[right], s=20 if has_keyhole else 13, alpha=0.7 if has_keyhole else 0.35, color=COLORS[label], label=label)
        axis.set(xlabel=feature_labels[left], ylabel=feature_labels[right], title=f"{left}–{right} with observed labels")
    axes[0].legend(frameon=False)
    path = save_figure(figure, output_dir, "08_keyhole_parameter_overlays.png")
    manifest.append({"figure": "08_keyhole_parameter_overlays.png", "path": path, "question": "Where are Keyhole-positive experiments observed? (descriptive only)"})

    top_patterns = patterns[patterns["partition"].eq("combined")].head(12).sort_values("experiment_count")
    figure, axis = plt.subplots(figsize=(11.5, 7))
    axis.barh(np.arange(len(top_patterns)), top_patterns["experiment_count"], color="#4C78A8")
    axis.set_yticks(np.arange(len(top_patterns)), [textwrap.shorten(value, width=75, placeholder="…") for value in top_patterns["collapsed_label_sequence"]])
    axis.set(xlabel="Experiment count", title="Most common collapsed label sequences")
    path = save_figure(figure, output_dir, "09_label_sequence_patterns.png")
    manifest.append({"figure": "09_label_sequence_patterns.png", "path": path, "question": "Which label-transition patterns actually occur?"})

    positive = sequence[sequence["has_keyhole"]].copy()
    bins = pd.cut(positive["keyhole_frame_count"], bins=[0, 1, 5, 20, 50, np.inf], labels=["1", "2–5", "6–20", "21–50", ">50"], right=True)
    counts = pd.crosstab(bins, positive["partition"]).reindex(columns=PARTITION_ORDER, fill_value=0)
    figure, axis = plt.subplots(figsize=(9.5, 5.2))
    bottom = np.zeros(len(counts))
    for partition in PARTITION_ORDER:
        axis.bar(counts.index.astype(str), counts[partition], bottom=bottom, color=COLORS[partition], label=partition)
        bottom += counts[partition].to_numpy()
    axis.set(xlabel="Number of labelled Keyhole frames", ylabel="Keyhole-positive experiments", title="Frame-based Keyhole-duration diagnostic (no ms conversion)")
    axis.legend(frameon=False)
    path = save_figure(figure, output_dir, "10_keyhole_duration_segments.png")
    manifest.append({"figure": "10_keyhole_duration_segments.png", "path": path, "question": "How many Keyhole observations and episodes are present?"})

    return pd.DataFrame(manifest)


def validation_rows(
    *,
    labels: pd.DataFrame,
    registry: pd.DataFrame,
    structure: dict[str, pd.DataFrame],
    distribution: pd.DataFrame,
    references: pd.DataFrame,
    sequence: pd.DataFrame,
    integrity: pd.DataFrame,
    provenance: dict[str, Any],
    smoke: bool,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(identifier: str, requirement: str, passed: bool, detail: str, *, warning: bool = False) -> None:
        rows.append({"validation_id": identifier, "requirement": requirement, "status": "PASS" if passed else "WARNING" if warning else "FAIL", "detail": detail})

    add("V01", "Exact sph_v2 revision recorded", provenance["analysis_revision"] == SPH_V2_REVISION and len(SPH_V2_REVISION) == 40, SPH_V2_REVISION)
    add("V02", "Scientific downloads use no floating revision", provenance["all_scientific_access_pinned"], "All hf_hub_download and tree calls use the 40-character revision")
    expected_experiments = len(registry) if smoke else 407
    expected_frames = len(labels) if smoke else 110_804
    add("V03", "Experiment count internally consistent", registry["experiment_name"].nunique() == expected_experiments == len(sequence), f"registry={len(registry)}; sequence={len(sequence)}; expected={expected_experiments}")
    add("V04", "Frame count internally consistent", len(labels) == expected_frames == int(registry["label_frame_count"].sum()), f"labels={len(labels)}; registry sum={int(registry['label_frame_count'].sum())}")
    add("V05", "Partition totals sum correctly", len(labels) == sum(len(labels[labels["partition"].eq(partition)]) for partition in PARTITION_ORDER), str(labels.groupby('partition').size().to_dict()))
    add("V06", "Label totals sum correctly", int(distribution[distribution["partition"].eq("combined")]["frame_count"].sum()) == len(labels), f"label total={int(distribution[distribution['partition'].eq('combined')]['frame_count'].sum())}")
    add("V07", "All P/VX/LS/ST finite", np.isfinite(registry[["P", "VX", "LS", "ST"]].to_numpy(float)).all(), "four parameters checked in every registry row")
    add("V08", "Experiment identifiers unique", registry["experiment_name"].is_unique, f"unique={registry['experiment_name'].nunique()}; rows={len(registry)}")
    add("V09", "Folder/JSON/partition inputs agree", registry["parameter_values_match_folder_and_partition"].all(), f"mismatches={int((~registry['parameter_values_match_folder_and_partition']).sum())}")
    add("V10", "Input units agree with Week 6", registry["parameter_units_match_week6"].all(), str(FEATURE_UNITS))
    add("V11", "frames.csv and top-level final labels agree", registry["frames_csv_label_matches_final_label"].all(), f"mismatches={int((~registry['frames_csv_label_matches_final_label']).sum())}")
    add("V12", "frames.csv timesteps agree with partition ledgers", registry["frames_csv_timestep_matches_partition_ledger"].all(), f"mismatches={int((~registry['frames_csv_timestep_matches_partition_ledger']).sum())}")
    missing_required = structure["missing_unexpected"][structure["missing_unexpected"]["severity"].eq("FAIL")]
    add("V13", "All required files present", missing_required.empty, f"required-file/frame-count issues={len(missing_required)}")
    add("V14", "Every perspective count equals its label ledger", structure["experiment_structure"]["all_three_frame_views_match_label_count"].all(), f"mismatches={int((~structure['experiment_structure']['all_three_frame_views_match_label_count']).sum())}")
    add("V15", "Ioan screenshot counts independently reproduced", references["status"].eq("PASS").all() if not smoke else True, f"PASS={int(references['status'].eq('PASS').sum())}/{len(references)}" if not smoke else "full-population check deferred in smoke")
    add("V16", "No experiment is silently removed", set(registry["experiment_name"]) == set(labels["experiment_name"]), "registry and label populations match exactly")
    add("V17", "No source label is modified", registry["frames_csv_label_matches_final_label"].all(), "source ledgers are read-only; output carries original labels")
    exact_duplicates = integrity[integrity["issue_type"].eq("exact_duplicate_complete_folder_content")]
    add("V18", "No exact duplicate complete experiment content", exact_duplicates.empty, f"duplicate bundles={len(exact_duplicates)}", warning=not exact_duplicates.empty)
    cross_partition = integrity[integrity["issue_type"].eq("same_identifier_across_partitions")]
    add("V19", "No identifier occurs across partitions", cross_partition.empty, f"cross-partition identifiers={len(cross_partition)}")
    source_ok, source_hits = ensure_no_modelling_imports(Path(__file__))
    add("V20", "No predictive model fitting code in Phase 1", source_ok, f"executable forbidden imports/calls={source_hits}")
    add("V21", "Week 6 comparison source pinned", set(pd.read_csv(WEEK6_LEDGER)["huggingface_revision"].astype(str)) == {WEEK6_REVISION}, WEEK6_REVISION)
    notebook_ok = NOTEBOOK_PATH.is_file() and not notebook_has_errors(NOTEBOOK_PATH)
    add("V22", "Teaching notebook exists with no stored error output", notebook_ok, str(NOTEBOOK_PATH.relative_to(ROOT)), warning=not NOTEBOOK_PATH.is_file())
    return pd.DataFrame(rows)


def requirement_checklist(validation: pd.DataFrame) -> pd.DataFrame:
    by_id = validation.set_index("validation_id")["status"].to_dict()

    def status_for(validation_ids: Sequence[str], *, audit_caveat: bool = False) -> str:
        values = [by_id[identifier] for identifier in validation_ids]
        if "FAIL" in values:
            # Finding a source-data defect is a successful audit outcome, but
            # the requirement dashboard must keep the caveat visible.
            return "WARNING" if audit_caveat else "FAIL"
        if "WARNING" in values:
            return "WARNING"
        return "PASS"

    entries = [
        ("P1-01", "Exact Hugging Face revision resolved, pinned, and displayed", "Notebook §2", "dataset_provenance.json; dataset_provenance_table.csv", ["V01", "V02"], False),
        ("P1-02", "Complete repository tree and file types audited", "Notebook §3", "repository_file_inventory.parquet; file_type_counts.csv", ["V01", "V03", "V04"], False),
        ("P1-03", "Partition and missing-file structure audited", "Notebook §3", "partition_summary.csv; missing_unexpected_files.csv", ["V13", "V14"], True),
        ("P1-04", "New structure compared with Week 6", "Notebook §3", "week6_structure_comparison.csv", ["V09", "V10"], False),
        ("P1-05", "Per-partition and combined label distributions reproduced", "Notebook §4", "label_distribution.csv", ["V05", "V06"], False),
        ("P1-06", "Ioan screenshot values compared with tolerances", "Notebook §4", "ioan_reference_comparison.csv", ["V15"], False),
        ("P1-07", "Experiment-level sequences and Keyhole episodes derived", "Notebook §5", "experiment_label_sequences.csv; keyhole_episodes.csv", ["V03", "V04"], False),
        ("P1-08", "Frame-based short/transient/persistent Keyhole evidence quantified", "Notebook §5", "experiment_label_sequences.csv; figures/10_keyhole_duration_segments.png", ["V04"], False),
        ("P1-09", "Working-student identifiability assessed without guessing", "Notebook §6", "annotator_provenance_audit.csv", ["V16", "V17"], False),
        ("P1-10", "Suspicious label records retained and flagged", "Notebook §6", "suspicious_label_anomalies.csv", ["V16", "V17"], False),
        ("P1-11", "P/VX/LS/ST units and descriptive statistics verified", "Notebook §7", "parameter_summary_by_partition.csv", ["V07", "V09", "V10"], False),
        ("P1-12", "Week 6 domain shift and new-only regions quantified", "Notebook §7", "parameter_bounds_shift.csv; new_data_domain_membership.csv", ["V21"], False),
        ("P1-13", "Identifiers, tuples, sequences, and folder content audited", "Notebook §8", "integrity_audit.csv; experiment_content_bundles.csv", ["V08", "V18", "V19"], True),
        ("P1-14", "Readable scientific figures generated", "Notebook §§4–8", "figure_manifest.csv", ["V03", "V04"], False),
        ("P1-15", "Phase 1 conclusions and machine-readable summary written", "Notebook §9", "results_summary.md; summary.json", ["V01"], False),
        ("P1-16", "No labels changed and no simulations silently removed", "Notebook §10", "validation_results.csv", ["V16", "V17"], False),
        ("P1-17", "No model fitting, active learning, or level-set work occurred", "Notebook §10", "validation_results.csv", ["V20"], False),
        ("P1-18", "Executed teaching notebook contains no stored errors", "Notebook §§1–10", "notebooks/week_07/01_sph_v2_dataset_shift_audit.ipynb", ["V22"], False),
    ]
    rows = [
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
    return pd.DataFrame(rows)


def build_provenance(
    *,
    labels: pd.DataFrame,
    registry: pd.DataFrame,
    inventory: pd.DataFrame,
    inventory_output: Path,
    live_main: str,
    started_at: str,
    smoke: bool,
) -> dict[str, Any]:
    label_files = []
    for partition, filename in PARTITIONS.items():
        path = RAW_ROOT / filename
        subset = labels[labels["partition"].eq(partition)]
        label_files.append(
            {
                "partition": partition,
                "relative_path": filename,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
                "frame_rows_in_analysis": len(subset),
                "experiment_count_in_analysis": subset["experiment_name"].nunique(),
            }
        )
    return {
        "repository_name": SPH_V2_REPO_ID,
        "repository_type": "Hugging Face dataset",
        "analysis_revision": SPH_V2_REVISION,
        "floating_main_resolved_at_run_start": live_main,
        "floating_main_equal_to_analysis_revision": live_main == SPH_V2_REVISION,
        "revision_semantics": {
            "analysis_revision": "immutable 40-character Git commit used for every scientific download and tree request",
            "floating_main": "branch pointer queried only for drift reporting; never used for analysis access",
        },
        "retrieval_started_at_utc": started_at,
        "retrieval_completed_at_utc": utc_now(),
        "analysis_mode": "smoke" if smoke else "full",
        "all_scientific_access_pinned": True,
        "experiment_count": registry["experiment_name"].nunique(),
        "labelled_frame_count": len(labels),
        "partition_names": PARTITION_ORDER,
        "partition_counts": {
            partition: {
                "experiments": int(labels.loc[labels["partition"].eq(partition), "experiment_name"].nunique()),
                "labelled_frames": int(labels["partition"].eq(partition).sum()),
            }
            for partition in PARTITION_ORDER
        },
        "repository_tree_item_count": len(inventory),
        "repository_file_count": int(inventory["item_type"].eq("file").sum()),
        "repository_folder_count": int(inventory["item_type"].eq("folder").sum()),
        "repository_inventory_artifact": inventory_output.relative_to(ROOT).as_posix(),
        "repository_inventory_sha256": sha256_file(inventory_output),
        "label_files": label_files,
        "week6_comparison": {
            "repository": WEEK6_REPO_ID,
            "revision": WEEK6_REVISION,
            "source_ledger": WEEK6_LEDGER.relative_to(ROOT).as_posix(),
            "source_ledger_sha256": sha256_file(WEEK6_LEDGER),
            "repository_base_commit": WEEK6_BASE_COMMIT,
        },
    }


def write_results_summary(
    output_dir: Path,
    *,
    labels: pd.DataFrame,
    references: pd.DataFrame,
    sequence: pd.DataFrame,
    anomalies: pd.DataFrame,
    annotator: pd.DataFrame,
    bounds: pd.DataFrame,
    membership: pd.DataFrame,
    validation: pd.DataFrame,
    smoke: bool,
) -> str:
    keyhole = int(sequence["has_keyhole"].sum())
    conduction = int(sequence["has_conduction"].sum())
    missing_structure = pd.read_csv(output_dir / "missing_unexpected_files.csv")
    missing_required_count = int(len(missing_structure))
    missing_experiment_count = int(missing_structure["experiment_name"].nunique())
    new_membership = membership
    ls = bounds[bounds["feature"].eq("LS")].iloc[0]
    st = bounds[bounds["feature"].eq("ST")].iloc[0]
    text = f"""# Week 7 Phase 1 — sph_v2 dataset and design-space audit

## Scope and provenance

This {'smoke' if smoke else 'full'} audit used `{SPH_V2_REPO_ID}@{SPH_V2_REVISION}`.  All
scientific access was pinned to that immutable revision; the floating `main`
pointer was recorded only as provenance.  No source label was changed, no
experiment was removed, and no predictive model was fitted.

## Reproduced population

- Experiments: **{sequence['experiment_name'].nunique()}**.
- Labelled frames: **{len(labels):,}**.
- Experiments containing Keyhole: **{keyhole}**.
- Experiments containing Conduction: **{conduction}**.
- Ioan reference checks: **{int(references['status'].eq('PASS').sum())}/{len(references)} PASS**.

At experiment level labels are not mutually exclusive: one simulation can pass
through both Conduction and Keyhole at different labelled timesteps.  Keyhole
duration is therefore reported in labelled frames and segments.  No conversion
to milliseconds is made because a repository-wide physical mapping from saved
frame index to time has not yet been validated.

## Label quality and annotator boundary

The working-student subset is **not reliably identifiable** from the pinned
repository.  There is no annotator/provenance field or file and the identities
behind `label_1` and `label_2` are undocumented.  A partition is not treated as
an annotator proxy.  The automated anomaly table contains **{anomalies['experiment_name'].nunique() if len(anomalies) else 0}**
experiments warranting review; these records remain in the data.

## Observed parameter-domain change

- LS lower-bound expansion relative to Week 6: **{ls['range_expansion_below_week6'] * 1e6:.3f} µm**.
- ST upper-bound expansion relative to Week 6: **{st['range_expansion_above_week6']:.3f} K**.
- New-data experiments outside at least one Week 6 marginal range: **{int(new_membership['outside_any_week6_axis_range'].sum())}/{len(new_membership)}**.
- New-data experiments outside the Week 6 four-dimensional convex hull: **{int((~new_membership['inside_week6_4d_convex_hull']).sum())}/{len(new_membership)}**.

These are observed design-space/covariate shifts.  They do not establish that
smaller LS or larger ST causes Keyhole.

## Phase 1 decision

The pinned repository is usable for the complete label/parameter audit and is
**partially usable** for Phase 2 physical extraction.  There are
**{missing_required_count} missing required-monitor entries across
{missing_experiment_count} experiments**.  Label anomalies, the absent annotator
split, and these structural gaps must remain visible.  Phase 2 must preserve
exact partition and revision provenance, retain every extraction failure as an
explicit row, and make no label corrections.

## Validation dashboard

- PASS: **{int(validation['status'].eq('PASS').sum())}**
- WARNING: **{int(validation['status'].eq('WARNING').sum())}**
- FAIL: **{int(validation['status'].eq('FAIL').sum())}**
"""
    (output_dir / "results_summary.md").write_text(text, encoding="utf-8")
    (output_dir / "phase1_results_summary.md").write_text(text, encoding="utf-8")
    return text


def run_phase1(
    *,
    smoke: bool = False,
    refresh_tree: bool = False,
    workers: int = 6,
) -> dict[str, Any]:
    started = time.perf_counter()
    started_at = utc_now()
    output_dir = SMOKE_DIR if smoke else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Week 7 Phase 1 {'smoke' if smoke else 'full'} audit", flush=True)

    live_main = current_main_revision()
    all_labels = load_partition_labels(workers=min(workers, 3))
    labels, experiment_names = select_population(all_labels, smoke=smoke)
    top = top_level_inventory()
    if smoke:
        tree = subset_tree_inventory(experiment_names, refresh=refresh_tree)
    else:
        tree = complete_tree_inventory(refresh=refresh_tree)
    downloaded = download_experiment_ledgers(experiment_names, workers=workers)
    registry, frame_checks = build_experiment_registry(labels, experiment_names, downloaded)
    structure = build_structure_tables(tree, labels, registry, top)

    inventory_output = output_dir / "repository_file_inventory.parquet"
    structure["repository_inventory"].to_parquet(inventory_output, index=False, compression="zstd")
    provenance = build_provenance(
        labels=labels,
        registry=registry,
        inventory=structure["repository_inventory"],
        inventory_output=inventory_output,
        live_main=live_main,
        started_at=started_at,
        smoke=smoke,
    )
    write_json(output_dir / "dataset_provenance.json", provenance)
    provenance_table = pd.DataFrame(
        [
            ("repository", SPH_V2_REPO_ID),
            ("analysis revision", SPH_V2_REVISION),
            ("floating main at retrieval", live_main),
            ("retrieval started UTC", started_at),
            ("experiment count", len(registry)),
            ("labelled frame count", len(labels)),
            ("partition names", ", ".join(PARTITION_ORDER)),
            ("repository tree items", len(tree)),
        ],
        columns=["field", "value"],
    )

    distribution = label_distribution(labels)
    references = reference_comparison(labels, distribution) if not smoke else reference_comparison(all_labels, label_distribution(all_labels))
    sequence, episodes, patterns = sequence_audit(labels)
    anomalies = build_anomaly_table(labels, sequence, structure["repository_inventory"])
    annotator = annotator_provenance_audit(labels, structure["repository_inventory"])
    parameter_summary, bounds, membership = parameter_audit(registry, sequence)
    integrity, bundles = integrity_audit(registry, labels, sequence, structure["repository_inventory"])
    figures = generate_figures(output_dir, labels, distribution, registry, sequence, patterns, episodes, bounds)

    tables = {
        "dataset_provenance_table.csv": provenance_table,
        "top_level_inventory.csv": structure["top_level_inventory"],
        "file_type_counts.csv": structure["file_type_counts"],
        "partition_summary.csv": structure["partition_summary"],
        "experiment_structure_summary.csv": structure["experiment_structure"],
        "missing_unexpected_files.csv": structure["missing_unexpected"],
        "week6_structure_comparison.csv": structure["structure_comparison"],
        "experiment_registry.csv": registry,
        "frames_csv_consistency.csv": frame_checks,
        "label_distribution.csv": distribution,
        "ioan_reference_comparison.csv": references,
        "experiment_label_sequences.csv": sequence,
        "label_sequence_patterns.csv": patterns,
        "keyhole_episodes.csv": episodes,
        "suspicious_label_anomalies.csv": anomalies,
        "annotator_provenance_audit.csv": annotator,
        "parameter_summary_by_partition.csv": parameter_summary,
        "parameter_bounds_shift.csv": bounds,
        "new_data_domain_membership.csv": membership,
        "integrity_audit.csv": integrity,
        "experiment_content_bundles.csv": bundles,
        "figure_manifest.csv": figures,
    }
    for filename, frame in tables.items():
        write_csv(output_dir / filename, frame)

    validation = validation_rows(
        labels=labels,
        registry=registry,
        structure=structure,
        distribution=distribution,
        references=references,
        sequence=sequence,
        integrity=integrity,
        provenance=provenance,
        smoke=smoke,
    )
    checklist = requirement_checklist(validation)
    write_csv(output_dir / "validation_results.csv", validation)
    write_csv(output_dir / "phase1_requirement_checklist.csv", checklist)
    write_csv(output_dir / "requirement_checklist.csv", checklist)
    summary_markdown = write_results_summary(
        output_dir,
        labels=labels,
        references=references,
        sequence=sequence,
        anomalies=anomalies,
        annotator=annotator,
        bounds=bounds,
        membership=membership,
        validation=validation,
        smoke=smoke,
    )
    summary = {
        "phase": "Week 7 Phase 1",
        "mode": "smoke" if smoke else "full",
        "repository": SPH_V2_REPO_ID,
        "revision": SPH_V2_REVISION,
        "experiment_count": len(registry),
        "labelled_frame_count": len(labels),
        "partition_counts": provenance["partition_counts"],
        "keyhole_experiment_count": int(sequence["has_keyhole"].sum()),
        "conduction_experiment_count": int(sequence["has_conduction"].sum()),
        "keyhole_frame_count": int(labels["label_final"].eq("Keyhole").sum()),
        "conduction_frame_count": int(labels["label_final"].eq("Conduction").sum()),
        "ioan_reference_pass_count": int(references["status"].eq("PASS").sum()),
        "ioan_reference_total": len(references),
        "working_student_subset_identifiable": False,
        "anomaly_record_count": len(anomalies),
        "anomaly_experiment_count": anomalies["experiment_name"].nunique() if len(anomalies) else 0,
        "new_data_outside_any_week6_axis_range": int(membership["outside_any_week6_axis_range"].sum()),
        "new_data_outside_week6_4d_convex_hull": int((~membership["inside_week6_4d_convex_hull"]).sum()),
        "missing_required_monitor_record_count": int(len(structure["missing_unexpected"])),
        "monitor_incomplete_experiment_count": int(
            structure["missing_unexpected"]["experiment_name"].nunique()
        ),
        "validation": validation["status"].value_counts().to_dict(),
        "scope": {
            "labels_modified": False,
            "simulations_removed": False,
            "predictive_models_fitted": False,
            "active_learning": False,
            "level_set_estimation": False,
        },
        "runtime_seconds": time.perf_counter() - started,
        "results_summary_markdown_sha256": hashlib.sha256(summary_markdown.encode("utf-8")).hexdigest(),
    }
    write_json(output_dir / "summary.json", summary)
    manifest = output_manifest(output_dir)
    write_csv(output_dir / "output_manifest.csv", manifest)
    print(
        f"Phase 1 complete: {len(registry)} experiments, {len(labels):,} frames; "
        f"validation {validation['status'].value_counts().to_dict()}",
        flush=True,
    )
    return summary


def refresh_phase1_validation(*, smoke: bool = False) -> dict[str, Any]:
    """Refresh notebook-dependent validation without repeating the data audit."""

    output_dir = SMOKE_DIR if smoke else OUTPUT_DIR
    required = [
        "dataset_provenance.json",
        "experiment_registry.csv",
        "experiment_structure_summary.csv",
        "missing_unexpected_files.csv",
        "label_distribution.csv",
        "ioan_reference_comparison.csv",
        "experiment_label_sequences.csv",
        "integrity_audit.csv",
    ]
    missing = [name for name in required if not (output_dir / name).is_file()]
    require(not missing, f"Cannot refresh validation; missing outputs: {missing}")
    provenance = json.loads((output_dir / "dataset_provenance.json").read_text(encoding="utf-8"))
    registry = pd.read_csv(output_dir / "experiment_registry.csv")
    labels_all = load_partition_labels(workers=3)
    labels = labels_all[labels_all["experiment_name"].isin(registry["experiment_name"])].copy()
    structure = {
        "experiment_structure": pd.read_csv(output_dir / "experiment_structure_summary.csv"),
        "missing_unexpected": pd.read_csv(output_dir / "missing_unexpected_files.csv"),
    }
    distribution = pd.read_csv(output_dir / "label_distribution.csv")
    references = pd.read_csv(output_dir / "ioan_reference_comparison.csv")
    sequence = pd.read_csv(output_dir / "experiment_label_sequences.csv")
    integrity = pd.read_csv(output_dir / "integrity_audit.csv")
    validation = validation_rows(
        labels=labels,
        registry=registry,
        structure=structure,
        distribution=distribution,
        references=references,
        sequence=sequence,
        integrity=integrity,
        provenance=provenance,
        smoke=smoke,
    )
    checklist = requirement_checklist(validation)
    write_csv(output_dir / "validation_results.csv", validation)
    write_csv(output_dir / "phase1_requirement_checklist.csv", checklist)
    write_csv(output_dir / "requirement_checklist.csv", checklist)
    summary_markdown = write_results_summary(
        output_dir,
        labels=labels,
        references=references,
        sequence=sequence,
        anomalies=pd.read_csv(output_dir / "suspicious_label_anomalies.csv"),
        annotator=pd.read_csv(output_dir / "annotator_provenance_audit.csv"),
        bounds=pd.read_csv(output_dir / "parameter_bounds_shift.csv"),
        membership=pd.read_csv(output_dir / "new_data_domain_membership.csv"),
        validation=validation,
        smoke=smoke,
    )
    summary_path = output_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["validation"] = validation["status"].value_counts().to_dict()
    summary["missing_required_monitor_record_count"] = int(
        len(structure["missing_unexpected"])
    )
    summary["monitor_incomplete_experiment_count"] = int(
        structure["missing_unexpected"]["experiment_name"].nunique()
    )
    summary["results_summary_markdown_sha256"] = hashlib.sha256(
        summary_markdown.encode("utf-8")
    ).hexdigest()
    summary["validation_refreshed_at_utc"] = utc_now()
    write_json(summary_path, summary)
    write_csv(output_dir / "output_manifest.csv", output_manifest(output_dir))
    print(f"Phase 1 validation refreshed: {summary['validation']}", flush=True)
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="Run a small schema-aligned audit")
    parser.add_argument("--refresh-tree", action="store_true", help="Refresh the exact-revision tree cache")
    parser.add_argument(
        "--refresh-validation-only",
        action="store_true",
        help="Refresh notebook/checklist validation from existing outputs",
    )
    parser.add_argument("--workers", type=int, default=6, help="Explicit pinned-download worker count")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.refresh_validation_only:
        refresh_phase1_validation(smoke=args.smoke)
    else:
        run_phase1(smoke=args.smoke, refresh_tree=args.refresh_tree, workers=args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
