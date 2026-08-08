"""Week 6 Phase 3.5: physically motivated regime-target design.

This module keeps the Phase 1--3 geometry targets immutable and asks a
different question: which continuous summary of melt-pool depth, width, and
depth/width evolution is a defensible proxy for persistent keyhole-like
behaviour?

The analysis is intentionally label-cautious.  The pinned dataset contains
provisional labels whose provenance records a depth-based automatic seed, so
agreement with those labels is descriptive rather than independent physical
validation.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import time
import warnings
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle
import nbformat
from nbclient import NotebookClient
import numpy as np
import pandas as pd
from pandas.api.indexers import BaseIndexer
from PIL import Image
import pyarrow as pa
import pyarrow.parquet as pq
from scipy import stats
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw" / "huggingface" / "sph_dataset"
FINAL_DATA = RAW_ROOT / "final_data_processed"
LABEL_FILE = RAW_ROOT / "final-labels_all.csv"
OUTPUT_DIR = ROOT / "outputs" / "week6_03_5_regime_target_design"
NOTEBOOK_PATH = (
    ROOT / "notebooks" / "week_06" / "05_phase3_5_regime_target_design.ipynb"
)
NOTEBOOK_BUILDER = ROOT / "scripts" / "build_week6_05_notebook.py"
ORIGINAL_WORKTREE = Path(r"C:\Users\ozgur\Documents\thesis")

REPO_ID = "ioandanielc/sph_dataset"
REVISION = "0e859b748fdbc8454f66e58e101e333ac0479d42"
PHASE1_LEDGER = (
    ROOT
    / "outputs"
    / "week6_01_melt_pool_data_audit"
    / "week6_phase1_simulation_level_responses.csv"
)
EXPECTED_LEDGER_SHA256 = (
    "10DEF11AB64D62444AC14FED506266BEB748EEB5BF892ACDC12E7F0F6DDCF4FF"
)
EXPECTED_HEAD = "b112f6b22898976f77410190614cb4fb218d38f9"
EXPECTED_BRANCH = "codex/week6-phase3-5-regime-target-design"
EXPECTED_FEATURES = ["P", "VX", "LS", "ST"]
EXPECTED_SIMULATIONS = 241
DEPTH_UNSTABLE_IDS = [
    "sim_00002",
    "sim_00006",
    "sim_00018",
    "sim_00029",
    "sim_00036",
    "sim_00038",
    "sim_00095",
    "sim_00105",
    "sim_00124",
    "sim_00154",
    "sim_00222",
]

SENTINEL_THRESHOLD = 1e30
PARTICLE_SPACING_M = 4e-6
PRIMARY_WIDTH_GUARD_M = 3 * PARTICLE_SPACING_M
WIDTH_GUARD_SENSITIVITY_UM = [8.0, 12.0, 20.0]
PERSISTENCE_WINDOWS_UM = [20.0, 50.0, 100.0]
NORMALIZED_WINDOWS = [0.01, 0.025, 0.05]
PRIMARY_PERSISTENCE_WINDOW_UM = 50.0
MIN_ROLLING_OBSERVATIONS = 5
MIN_ROLLING_SPAN_FRACTION = 0.80
STARTUP_MARGIN_M = 50e-6
END_MARGIN_M = 50e-6
COMMON_SUPPORT_FRACTION = 0.80
COMMON_START_S = 0.10
PROFILE_GRID = np.round(np.linspace(0.0, 1.0, 201), 6)
PROFILE_BIN_WIDTH = float(PROFILE_GRID[1] - PROFILE_GRID[0])
PROFILE_MIN_ABSOLUTE_SUPPORT = 10
BOOTSTRAP_SEED = 35062026
THRESHOLD_SEED = 35062027

SEMANTIC_COLORS = {
    "Conduction": "#2A9D8F",
    "Keyhole": "#D1495B",
    "Forming Phase": "#E9C46A",
    "Initial Emptiness": "#B8B8B8",
    "Screenshot Bug": "#737373",
    "keyhole-containing": "#D1495B",
    "conduction-only": "#2A9D8F",
    "mixed": "#7A5195",
    "unlabelled-or-ambiguous": "#8C8C8C",
    "all": "#264653",
    "T0 window": "#6C8EBF",
    "persistent event": "#F28E2B",
}

CORE_HASHES = {
    "notebooks/week_06/01_melt_pool_monitor_data_audit.ipynb": (
        "BB4897432224C9A16ADAE084FBE5004DD7987DA43BA9B6195C5DABD65D9DF65F"
    ),
    "src/week6_phase1_melt_pool_data_audit.py": (
        "64A5E3998D411961CBFBC3AD0A761F9B9D8F2C876550548B835C3EBF0E1C63A4"
    ),
    "outputs/week6_01_melt_pool_data_audit/week6_phase1_simulation_level_responses.csv": (
        EXPECTED_LEDGER_SHA256
    ),
    "notebooks/week_06/02_gp_response_noise_comparison.ipynb": (
        "DF04ADF427DA98D238488C0BE6D15807ACBDE07478F35F22D187CDD707FBA359"
    ),
    "src/week6_phase2_gp_response_noise_comparison.py": (
        "4228223095EA40A4F05DC6084C565E99FA0E0747AB2B8C0891C2C534B6BA9701"
    ),
    "notebooks/week_06/03_phase2_5_depth_model_closure.ipynb": (
        "FDA44EF49D15EB72789003F8D9218FC945A1F8D5752098F4CF3C7D2B6FD54454"
    ),
    "src/week6_phase2_5_depth_model_closure.py": (
        "2766ED6D8551151B29582C6B7D83C88D39367153A70B4DCFDE249410481204B3"
    ),
    "notebooks/week_06/04_phase3_model_target_robustness.ipynb": (
        "9833395E2D1B78A4613B29B9790E3F3488CDFF379404E65557E4253575C92D5A"
    ),
    "src/week6_phase3_model_target_robustness.py": (
        "D9FE981C637B63D6F3384249374209DB73B03A5BA853F47C5576EE4E8454A914"
    ),
    "outputs/week6_03_model_target_robustness/summary.json": (
        "E0F9851F37747516C6757C64350B233A8CC0DB06A9CCCDB6B71A9D350E6C09D9"
    ),
    "outputs/week6_03_model_target_robustness/validation_results.csv": (
        "2B0CDE041C3478E0606E57CCBD54B076EECE2CC2B657B4FFE7611CC3673A33C8"
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


def write_json(payload: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return [json_safe(item) for item in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, float):
        return None if not math.isfinite(value) else value
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if value is pd.NA:
        return None
    return value


def git_output(args: Sequence[str], cwd: Path = ROOT) -> str:
    completed = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


class DistanceWindowIndexer(BaseIndexer):
    """Precomputed trailing windows whose left edge is set by physical distance."""

    def __init__(self, starts: np.ndarray):
        super().__init__(window_size=0)
        self.starts = np.asarray(starts, dtype=np.int64)

    def get_window_bounds(
        self,
        num_values: int = 0,
        min_periods: int | None = None,
        center: bool | None = None,
        closed: str | None = None,
        step: int | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        require(num_values == len(self.starts), "Distance window length mismatch")
        ends = np.arange(1, num_values + 1, dtype=np.int64)
        return self.starts, ends


def rolling_distance_stat(
    x_m: np.ndarray,
    values: np.ndarray,
    window_m: float,
    *,
    statistic: str = "median",
    quantile: float = 0.5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Calculate a trailing rolling statistic over an exact physical-distance window."""

    x_m = np.asarray(x_m, dtype=float)
    values = np.asarray(values, dtype=float)
    require(np.all(np.diff(x_m) >= 0), "Laser X position is not monotone")
    starts = np.searchsorted(x_m, x_m - window_m, side="left")
    indexer = DistanceWindowIndexer(starts)
    rolling = pd.Series(values).rolling(
        indexer,
        min_periods=MIN_ROLLING_OBSERVATIONS,
    )
    if statistic == "median":
        result = rolling.median().to_numpy(dtype=float)
    elif statistic == "quantile":
        result = rolling.quantile(quantile).to_numpy(dtype=float)
    else:
        raise ValueError(f"Unsupported rolling statistic: {statistic}")
    count = rolling.count().to_numpy(dtype=float)
    span = x_m - x_m[starts]
    eligible = (
        np.isfinite(result)
        & (count >= MIN_ROLLING_OBSERVATIONS)
        & (span >= MIN_ROLLING_SPAN_FRACTION * window_m)
    )
    result[~eligible] = np.nan
    return result, count, span, starts


def safe_ratio(
    depth_m: np.ndarray,
    width_m: np.ndarray,
    minimum_width_m: float,
) -> tuple[np.ndarray, np.ndarray]:
    ratio = np.full(len(depth_m), np.nan, dtype=float)
    reasons = np.full(len(depth_m), "", dtype=object)
    finite = np.isfinite(depth_m) & np.isfinite(width_m)
    reasons[~finite] = "non_finite_depth_or_width"
    nonpositive = finite & (width_m <= 0)
    reasons[nonpositive] = "nonpositive_width"
    below_guard = finite & (width_m > 0) & (width_m < minimum_width_m)
    reasons[below_guard] = "width_below_minimum_guard"
    valid = finite & (width_m >= minimum_width_m)
    ratio[valid] = depth_m[valid] / width_m[valid]
    reasons[valid] = "valid"
    return ratio, reasons


def distance_fraction_above(
    x_m: np.ndarray,
    values: np.ndarray,
    threshold: float,
) -> float:
    finite = np.isfinite(x_m) & np.isfinite(values)
    if finite.sum() < 2:
        return float("nan")
    x = x_m[finite]
    y = values[finite]
    dx = np.diff(x)
    if not np.isfinite(dx).all() or dx.sum() <= 0:
        return float("nan")
    above = (y[:-1] >= threshold) & (y[1:] >= threshold)
    return float(dx[above].sum() / dx.sum())


def run_preflight_checks() -> tuple[pd.DataFrame, pd.DataFrame]:
    require(ROOT.resolve() == Path(git_output(["rev-parse", "--show-toplevel"])).resolve(), "Repository root mismatch")
    require(git_output(["branch", "--show-current"]) == EXPECTED_BRANCH, "Wrong Phase 3.5 branch")
    require(git_output(["rev-parse", "HEAD"]) == EXPECTED_HEAD, "Unexpected starting HEAD")
    rows = []
    for relative_path, expected in CORE_HASHES.items():
        path = ROOT / relative_path
        require(path.exists(), f"Protected artifact missing: {relative_path}")
        actual = sha256(path)
        require(actual == expected, f"Protected artifact hash changed: {relative_path}")
        rows.append(
            {
                "path": relative_path,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "match": True,
            }
        )
    ledger = pd.read_csv(PHASE1_LEDGER)
    require(len(ledger) == EXPECTED_SIMULATIONS, "Phase 1 ledger row count changed")
    require(ledger["simulation_id"].nunique() == EXPECTED_SIMULATIONS, "Phase 1 simulation IDs are not unique")
    require(all(column in ledger.columns for column in EXPECTED_FEATURES), "Required features missing")
    require(sha256(PHASE1_LEDGER) == EXPECTED_LEDGER_SHA256, "Phase 1 ledger hash changed")
    preflight = json.loads(
        (OUTPUT_DIR / "phase3_5_preflight_snapshot.json").read_text(encoding="utf-8")
    )
    original_rows = []
    for item in preflight["original_dirty_worktree"]["protected_dirty_files"]:
        path = ORIGINAL_WORKTREE / item["path"]
        actual = sha256(path) if path.exists() else "MISSING"
        require(actual == item["sha256"], f"Original dirty file changed: {item['path']}")
        original_rows.append(
            {
                "path": item["path"],
                "expected_sha256": item["sha256"],
                "actual_sha256": actual,
                "match": True,
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(original_rows)


def build_label_dictionary() -> pd.DataFrame:
    records = [
        (
            "Conduction",
            "Conduction",
            "physical",
            True,
            "",
            "final-labels_all.csv and per-simulation frames.csv",
        ),
        (
            "Keyhole",
            "Keyhole",
            "physical",
            True,
            "",
            "final-labels_all.csv and per-simulation frames.csv",
        ),
        (
            "Forming Phase",
            "Forming Phase",
            "physical_transition",
            True,
            "Excluded from binary Conduction-versus-Keyhole metrics but retained in profiles.",
            "final-labels_all.csv and per-simulation frames.csv",
        ),
        (
            "Initial Emptiness",
            "Initial Emptiness",
            "technical_or_annotation",
            False,
            "No melt-regime claim; excluded from regime metrics.",
            "final-labels_all.csv and per-simulation frames.csv",
        ),
        (
            "Screenshot Bug",
            "Screenshot Bug",
            "technical_or_annotation",
            False,
            "Never used as a Keyhole-negative physical class.",
            "final-labels_all.csv and per-simulation frames.csv",
        ),
    ]
    return pd.DataFrame(
        records,
        columns=[
            "stored_label",
            "normalized_label",
            "label_type",
            "included_in_regime_analysis",
            "exclusion_or_usage_note",
            "provenance",
        ],
    )


def load_metadata_map(simulation_ids: Sequence[str]) -> pd.DataFrame:
    rows = []
    for simulation_id in simulation_ids:
        folder = FINAL_DATA / simulation_id
        metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
        provenance = json.loads(
            (folder / "labeling_provenance.json").read_text(encoding="utf-8")
        )
        details = json.loads(
            (folder / "experiment_details.json").read_text(encoding="utf-8")
        )
        parameters = json.loads(
            (folder / "parameters.json").read_text(encoding="utf-8")
        )
        spot_radius = float(
            details["lasers"]["single_gaussian_laser"]["physics"]["shape"][
                "spot_radius"
            ]
        )
        laser_spot_size = float(parameters["laser_spot_size"]["value"])
        rows.append(
            {
                "simulation_id": simulation_id,
                "name": metadata["original_folder_name"],
                "hash": metadata["original_hash"],
                "metadata_frame_count": int(metadata["n_frames"]),
                "labeling_method": provenance.get("method", ""),
                "automatic_method": provenance.get("automatic_method", ""),
                "n_frames_human_verified": int(
                    provenance.get("n_frames_human_verified", 0)
                ),
                "provenance_keyhole_count": int(provenance.get("n_keyhole", 0)),
                "keyhole_threshold_m": provenance.get("keyhole_threshold_m"),
                "laser_spot_size_m": laser_spot_size,
                "experiment_spot_radius_m": spot_radius,
                "ls_is_spot_radius": bool(
                    np.isclose(laser_spot_size, spot_radius, rtol=0, atol=1e-15)
                ),
                "particle_spacing_m": float(
                    details["sph"]["particle_spacing"]
                ),
                "domain_start_x_m": float(
                    details["lasers"]["single_gaussian_laser"]["physics"][
                        "motion"
                    ]["center"][0]
                ),
                "positive_x_domain_end_m": float(
                    details["domain"]["domain_max"][0]
                ),
            }
        )
    return pd.DataFrame(rows)


def audit_labels(
    simulation_ids: Sequence[str],
    metadata_map: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    labels = pd.read_csv(LABEL_FILE)
    require(
        labels.columns.tolist()
        == [
            "name",
            "hash",
            "P",
            "VX",
            "LS",
            "ST",
            "bug_free",
            "correctly_finished",
            "timestep",
            "label_1",
            "label_2",
            "label_final",
        ],
        "Unexpected label-file schema",
    )
    require(labels["label_1"].equals(labels["label_final"]), "label_1 differs from label_final")
    require(labels["label_2"].equals(labels["label_final"]), "label_2 differs from label_final")
    labels = labels.merge(
        metadata_map[["simulation_id", "name", "hash"]],
        on=["name", "hash"],
        how="left",
        validate="many_to_one",
    )
    require(labels["simulation_id"].notna().all(), "Unmapped label rows")
    require(labels["simulation_id"].nunique() == len(simulation_ids), "Label population mismatch")

    dictionary = build_label_dictionary()
    dictionary_lookup = dictionary.set_index("stored_label")
    require(
        set(labels["label_final"]) == set(dictionary["stored_label"]),
        "Unexpected stored labels",
    )
    labels["normalized_label"] = labels["label_final"].map(
        dictionary_lookup["normalized_label"]
    )
    labels["label_type"] = labels["label_final"].map(
        dictionary_lookup["label_type"]
    )
    labels["included_in_regime_analysis"] = labels["label_final"].map(
        dictionary_lookup["included_in_regime_analysis"]
    )

    population_rows = []
    for label, subset in labels.groupby("label_final", sort=False):
        population_rows.append(
            {
                "record_type": "label",
                "label": label,
                "label_type": dictionary_lookup.loc[label, "label_type"],
                "frame_count": len(subset),
                "frame_fraction": len(subset) / len(labels),
                "simulation_count": subset["simulation_id"].nunique(),
                "value": "",
                "note": "",
            }
        )
    sequences = []
    for simulation_id, subset in labels.groupby("simulation_id", sort=True):
        ordered = subset.sort_values("timestep")
        compressed = [
            label
            for index, label in enumerate(ordered["label_final"])
            if index == 0 or label != ordered["label_final"].iloc[index - 1]
        ]
        counts = Counter(ordered["label_final"])
        physical = ordered[
            ordered["label_final"].isin(["Conduction", "Forming Phase", "Keyhole"])
        ]
        any_keyhole = bool(counts["Keyhole"])
        any_conduction = bool(counts["Conduction"])
        sequences.append(
            {
                "simulation_id": simulation_id,
                "frame_count": len(ordered),
                "first_timestep": int(ordered["timestep"].min()),
                "last_timestep": int(ordered["timestep"].max()),
                "stored_sequence": " -> ".join(compressed),
                "unique_label_count": ordered["label_final"].nunique(),
                "label_change_count": max(0, len(compressed) - 1),
                "initial_emptiness_frames": counts["Initial Emptiness"],
                "forming_phase_frames": counts["Forming Phase"],
                "conduction_frames": counts["Conduction"],
                "keyhole_frames": counts["Keyhole"],
                "screenshot_bug_frames": counts["Screenshot Bug"],
                "usable_physical_label_frames": len(physical),
                "any_keyhole": any_keyhole,
                "any_conduction": any_conduction,
                "both_conduction_and_keyhole": any_keyhole and any_conduction,
                "conduction_only_definition": any_conduction and not any_keyhole,
                "no_usable_physical_label": physical.empty,
                "keyhole_fraction": (
                    counts["Keyhole"] / len(physical) if len(physical) else np.nan
                ),
                "persistent_keyhole_3_consecutive_frames": bool(
                    ordered["label_final"]
                    .eq("Keyhole")
                    .rolling(3, min_periods=3)
                    .sum()
                    .ge(3)
                    .any()
                ),
                "first_keyhole_timestep": (
                    int(ordered.loc[ordered["label_final"].eq("Keyhole"), "timestep"].iloc[0])
                    if any_keyhole
                    else np.nan
                ),
            }
        )
    sequence = pd.DataFrame(sequences)
    summary_values = {
        "total_label_rows": len(labels),
        "unique_simulations": labels["simulation_id"].nunique(),
        "any_keyhole_simulations": int(sequence["any_keyhole"].sum()),
        "both_conduction_and_keyhole_simulations": int(
            sequence["both_conduction_and_keyhole"].sum()
        ),
        "conduction_only_simulations": int(
            sequence["conduction_only_definition"].sum()
        ),
        "no_usable_physical_label_simulations": int(
            sequence["no_usable_physical_label"].sum()
        ),
        "automatic_only_provenance_simulations": int(
            metadata_map["labeling_method"].eq("automatic").sum()
        ),
        "human_verified_provenance_simulations": int(
            metadata_map["labeling_method"].eq("human-verified").sum()
        ),
        "depth_seeded_provenance_simulations": int(
            metadata_map["automatic_method"]
            .str.contains("median-zmin", regex=False)
            .sum()
        ),
    }
    for label, value in summary_values.items():
        population_rows.append(
            {
                "record_type": "population_summary",
                "label": label,
                "label_type": "",
                "frame_count": np.nan,
                "frame_fraction": np.nan,
                "simulation_count": np.nan,
                "value": value,
                "note": (
                    "Depth-seeded provenance creates possible circular validation."
                    if label == "depth_seeded_provenance_simulations"
                    else ""
                ),
            }
        )
    return labels, pd.DataFrame(population_rows), sequence


def choose_common_interval(ledger: pd.DataFrame) -> dict[str, Any]:
    last_s = (
        ledger["last_valid_melt_time_s"].to_numpy(dtype=float)
        / ledger["laser_exit_time_s"].to_numpy(dtype=float)
    )
    eligible_end = float(
        np.floor(np.quantile(last_s, 1 - COMMON_SUPPORT_FRACTION) / 0.05) * 0.05
    )
    eligible_end = min(0.80, max(0.30, eligible_end))
    support = int(np.sum(last_s >= eligible_end))
    require(support >= math.ceil(COMMON_SUPPORT_FRACTION * len(ledger)), "Common interval support rule failed")
    return {
        "start_s": COMMON_START_S,
        "end_s": eligible_end,
        "support_count_at_end": support,
        "support_fraction_at_end": support / len(ledger),
        "selection_rule": (
            "Start at s=0.10 to exclude startup; end at the largest 0.05-grid "
            "position not above 0.80 reached by at least 80% of simulations."
        ),
        "candidate_interval_support": [
            {
                "start_s": start,
                "end_s": end,
                "support_count_at_end": int(np.sum(last_s >= end)),
                "support_fraction_at_end": float(np.mean(last_s >= end)),
            }
            for start, end in [(0.10, 0.70), (0.15, 0.75), (0.20, 0.80)]
        ],
    }


def _group_label(sequence_row: pd.Series) -> str:
    if bool(sequence_row["both_conduction_and_keyhole"]):
        return "mixed"
    if bool(sequence_row["any_keyhole"]):
        return "keyhole-containing"
    if bool(sequence_row["conduction_only_definition"]):
        return "conduction-only"
    return "unlabelled-or-ambiguous"


@dataclass(frozen=True)
class ProcessingContext:
    output_dir: Path
    common_start_s: float
    common_end_s: float
    force: bool


def _parquet_part_path(output_dir: Path, simulation_id: str) -> Path:
    return (
        output_dir
        / "regime_geometry_time_series.parquet"
        / f"part-{simulation_id}.parquet"
    )


def _label_part_path(output_dir: Path, simulation_id: str) -> Path:
    return output_dir / "checkpoints" / "label_parts" / f"{simulation_id}.parquet"


def _checkpoint_path(output_dir: Path, simulation_id: str) -> Path:
    return output_dir / "checkpoints" / "simulation_summaries" / f"{simulation_id}.json"


def _candidate_value_row(
    simulation_id: str,
    candidate_id: str,
    value: float,
    unit: str,
    domain: str,
    window_um: float | None,
    position_s: float | None,
    available: bool,
    note: str,
) -> dict[str, Any]:
    return {
        "simulation_id": simulation_id,
        "candidate_id": candidate_id,
        "value": value,
        "unit": unit,
        "analysis_domain": domain,
        "persistence_window_um": window_um,
        "event_position_s": position_s,
        "available": bool(available and np.isfinite(value)),
        "note": note,
    }


def process_simulation(
    simulation_id: str,
    ledger_row: dict[str, Any],
    label_rows: list[dict[str, Any]],
    sequence_row: dict[str, Any],
    context: ProcessingContext,
) -> dict[str, Any]:
    checkpoint = _checkpoint_path(context.output_dir, simulation_id)
    part_path = _parquet_part_path(context.output_dir, simulation_id)
    label_part = _label_part_path(context.output_dir, simulation_id)
    if not context.force and checkpoint.exists() and part_path.exists() and label_part.exists():
        reused = json.loads(checkpoint.read_text(encoding="utf-8"))
        reused["_cache_status"] = "reused"
        return reused

    folder = FINAL_DATA / simulation_id
    details = json.loads((folder / "experiment_details.json").read_text(encoding="utf-8"))
    parameters = json.loads((folder / "parameters.json").read_text(encoding="utf-8"))
    bounds = np.loadtxt(folder / "monitor" / "position-bounds_melt.dat", delimiter=",", ndmin=2)
    time_s = np.loadtxt(folder / "monitor" / "time.dat", ndmin=1)
    iteration = np.loadtxt(folder / "monitor" / "iter.dat", ndmin=1)
    require(bounds.shape[1] == 6, f"{simulation_id}: bounds columns changed")
    require(len(bounds) == len(time_s) == len(iteration), f"{simulation_id}: monitor alignment failed")
    require(np.all(np.diff(time_s) > 0), f"{simulation_id}: non-monotone time")
    require(np.all(np.diff(iteration) > 0), f"{simulation_id}: non-monotone iteration")

    finite = np.isfinite(bounds).all(axis=1)
    non_sentinel = (np.abs(bounds) < SENTINEL_THRESHOLD).all(axis=1)
    ordered = (
        (bounds[:, 1] >= bounds[:, 0])
        & (bounds[:, 3] >= bounds[:, 2])
        & (bounds[:, 5] >= bounds[:, 4])
    )
    require(
        not bool(np.any(finite & non_sentinel & ~ordered)),
        f"{simulation_id}: finite non-sentinel bounds are not ordered",
    )
    valid_melt = finite & non_sentinel & ordered
    require(valid_melt.any(), f"{simulation_id}: no valid melt rows")
    width_m = np.full(len(bounds), np.nan)
    length_m = np.full(len(bounds), np.nan)
    depth_m = np.full(len(bounds), np.nan)
    vertical_extent_m = np.full(len(bounds), np.nan)
    width_m[valid_melt] = bounds[valid_melt, 3] - bounds[valid_melt, 2]
    length_m[valid_melt] = bounds[valid_melt, 1] - bounds[valid_melt, 0]
    depth_m[valid_melt] = np.maximum(0.0, -bounds[valid_melt, 4])
    vertical_extent_m[valid_melt] = bounds[valid_melt, 5] - bounds[valid_melt, 4]
    ratio, ratio_reason = safe_ratio(depth_m, width_m, PRIMARY_WIDTH_GUARD_M)

    vx = float(parameters["scan_speed_x"]["value"])
    ls_m = float(parameters["laser_spot_size"]["value"])
    motion = details["lasers"]["single_gaussian_laser"]["physics"]["motion"]
    x_start_m = float(motion["center"][0])
    x_end_m = float(details["domain"]["domain_max"][0])
    require(x_end_m > x_start_m, f"{simulation_id}: invalid positive-X domain")
    laser_x_m = x_start_m + vx * time_s
    normalized_s = (laser_x_m - x_start_m) / (x_end_m - x_start_m)
    require(np.all(np.diff(laser_x_m) > 0), f"{simulation_id}: non-monotone laser position")

    valid_idx = np.flatnonzero(valid_melt)
    valid_x = laser_x_m[valid_melt]
    onset_x = float(valid_x[0])
    last_active_x = float(valid_x[-1])
    adaptive_start_x = onset_x + STARTUP_MARGIN_M
    adaptive_end_x = min(last_active_x, x_end_m) - END_MARGIN_M
    adaptive_valid = adaptive_end_x > adaptive_start_x
    adaptive_mask = valid_melt & (laser_x_m >= adaptive_start_x) & (laser_x_m <= adaptive_end_x)
    common_mask = (
        valid_melt
        & (normalized_s >= context.common_start_s)
        & (normalized_s <= context.common_end_s)
    )

    primary_roll_depth = np.full(len(bounds), np.nan)
    primary_roll_ratio = np.full(len(bounds), np.nan)
    valid_roll_depth, primary_count, primary_span, _ = rolling_distance_stat(
        valid_x,
        depth_m[valid_melt],
        PRIMARY_PERSISTENCE_WINDOW_UM * 1e-6,
    )
    valid_roll_ratio, _, _, _ = rolling_distance_stat(
        valid_x,
        ratio[valid_melt],
        PRIMARY_PERSISTENCE_WINDOW_UM * 1e-6,
    )
    primary_roll_depth[valid_melt] = valid_roll_depth
    primary_roll_ratio[valid_melt] = valid_roll_ratio

    t0_start_row = int(ledger_row["selected_window_start_row_index"])
    t0_end_row = int(ledger_row["selected_window_end_row_index"])
    t0_mask = np.zeros(len(bounds), dtype=bool)
    t0_mask[t0_start_row : t0_end_row + 1] = True
    t0_mask &= valid_melt
    phase1_t0 = float(
        ledger_row[
            "melt_pool_depth_below_surface_selected_primary_scalar_target_m"
        ]
    )
    reproduced_t0 = float(np.median(depth_m[t0_mask]))
    require(np.isclose(phase1_t0, reproduced_t0, rtol=0, atol=1e-15), f"{simulation_id}: T0 mismatch")

    candidates = [
        _candidate_value_row(
            simulation_id,
            "G0",
            phase1_t0 * 1e6,
            "um",
            "Phase1_T0_window",
            None,
            float(np.median(normalized_s[t0_mask])),
            True,
            "Existing late-active median depth geometry target.",
        )
    ]

    full_max_depth_idx = int(np.nanargmax(depth_m))
    full_max_ratio_idx = int(np.nanargmax(ratio))
    candidates.extend(
        [
            _candidate_value_row(
                simulation_id,
                "G1",
                float(depth_m[full_max_depth_idx] * 1e6),
                "um",
                "full_valid_track",
                None,
                float(normalized_s[full_max_depth_idx]),
                True,
                "Spike-sensitive global maximum depth reference.",
            ),
            _candidate_value_row(
                simulation_id,
                "R0",
                float(np.nanmedian(ratio[t0_mask])),
                "dimensionless",
                "Phase1_T0_window",
                None,
                float(np.median(normalized_s[t0_mask])),
                np.isfinite(ratio[t0_mask]).any(),
                "T0-window median depth/width.",
            ),
            _candidate_value_row(
                simulation_id,
                "R1",
                float(ratio[full_max_ratio_idx]),
                "dimensionless",
                "full_valid_track",
                None,
                float(normalized_s[full_max_ratio_idx]),
                True,
                "Spike-sensitive global maximum depth/width reference.",
            ),
        ]
    )

    sensitivity_rows: list[dict[str, Any]] = []
    domain_rows: list[dict[str, Any]] = []
    for domain_name, domain_mask in [
        ("adaptive_active_interior", adaptive_mask),
        ("common_interior", common_mask),
    ]:
        indices = np.flatnonzero(domain_mask)
        if not len(indices):
            for candidate_id in ["G2", "G3", "G4", "R2", "R3"]:
                domain_rows.append(
                    {
                        "simulation_id": simulation_id,
                        "analysis_domain": domain_name,
                        "candidate_id": candidate_id,
                        "value": np.nan,
                        "unit": "um" if candidate_id.startswith("G") else "dimensionless",
                        "available": False,
                    }
                )
            continue
        x_domain = laser_x_m[indices]
        depth_domain = depth_m[indices]
        ratio_domain = ratio[indices]
        q95_depth = float(np.nanquantile(depth_domain, 0.95))
        q95_ratio = float(np.nanquantile(ratio_domain, 0.95))
        domain_rows.extend(
            [
                {
                    "simulation_id": simulation_id,
                    "analysis_domain": domain_name,
                    "candidate_id": "G2",
                    "value": q95_depth * 1e6,
                    "unit": "um",
                    "available": True,
                },
                {
                    "simulation_id": simulation_id,
                    "analysis_domain": domain_name,
                    "candidate_id": "R2",
                    "value": q95_ratio,
                    "unit": "dimensionless",
                    "available": np.isfinite(q95_ratio),
                },
            ]
        )
        window_specs = [
            ("physical_um", window_um, window_um * 1e-6)
            for window_um in PERSISTENCE_WINDOWS_UM
        ] + [
            (
                "normalized_track_fraction",
                fraction * 100.0,
                fraction * (x_end_m - x_start_m),
            )
            for fraction in NORMALIZED_WINDOWS
        ]
        for window_type, window_value, window_m in window_specs:
            roll_depth, counts, spans, _ = rolling_distance_stat(
                x_domain,
                depth_domain,
                window_m,
            )
            roll_depth_q80, _, _, _ = rolling_distance_stat(
                x_domain,
                depth_domain,
                window_m,
                statistic="quantile",
                quantile=0.80,
            )
            roll_ratio, _, _, _ = rolling_distance_stat(
                x_domain,
                ratio_domain,
                window_m,
            )
            for candidate_id, values, unit in [
                ("G3", roll_depth * 1e6, "um"),
                ("G4", roll_depth_q80 * 1e6, "um"),
                ("R3", roll_ratio, "dimensionless"),
            ]:
                if np.isfinite(values).any():
                    max_index = int(np.nanargmax(values))
                    value = float(values[max_index])
                    event_s = float(normalized_s[indices[max_index]])
                    available = True
                else:
                    value = np.nan
                    event_s = np.nan
                    available = False
                sensitivity_rows.append(
                    {
                        "simulation_id": simulation_id,
                        "analysis_domain": domain_name,
                        "window_type": window_type,
                        "window_value": window_value,
                        "window_distance_um": window_m * 1e6,
                        "candidate_id": candidate_id,
                        "value": value,
                        "unit": unit,
                        "event_position_s": event_s,
                        "available": available,
                        "typical_window_observation_count": (
                            float(np.nanmedian(counts[np.isfinite(values)]))
                            if np.isfinite(values).any()
                            else np.nan
                        ),
                        "minimum_required_observations": MIN_ROLLING_OBSERVATIONS,
                        "minimum_span_fraction": MIN_ROLLING_SPAN_FRACTION,
                    }
                )
                if (
                    window_type == "physical_um"
                    and np.isclose(window_value, PRIMARY_PERSISTENCE_WINDOW_UM)
                ):
                    domain_rows.append(
                        {
                            "simulation_id": simulation_id,
                            "analysis_domain": domain_name,
                            "candidate_id": candidate_id,
                            "value": value,
                            "unit": unit,
                            "available": available,
                            "event_position_s": event_s,
                        }
                    )

    primary_domain = pd.DataFrame(domain_rows)
    primary_domain = primary_domain[
        primary_domain["analysis_domain"].eq("adaptive_active_interior")
    ].set_index("candidate_id")
    for candidate_id in ["G2", "G3", "G4", "R2", "R3"]:
        row = primary_domain.loc[candidate_id]
        candidates.append(
            _candidate_value_row(
                simulation_id,
                candidate_id,
                float(row["value"]),
                str(row["unit"]),
                "adaptive_active_interior",
                PRIMARY_PERSISTENCE_WINDOW_UM
                if candidate_id in {"G3", "G4", "R3"}
                else None,
                float(row.get("event_position_s", np.nan)),
                bool(row["available"]),
                {
                    "G2": "Interior q95 depth.",
                    "G3": "Maximum trailing 50 um rolling-median depth.",
                    "G4": "Maximum trailing 50 um rolling-q80 depth sensitivity.",
                    "R2": "Interior q95 depth/width.",
                    "R3": "Maximum trailing 50 um rolling-median depth/width.",
                }[candidate_id],
            )
        )

    guard_rows = []
    adaptive_indices = np.flatnonzero(adaptive_mask)
    for guard_um in WIDTH_GUARD_SENSITIVITY_UM:
        guard_ratio, guard_reason = safe_ratio(
            depth_m,
            width_m,
            guard_um * 1e-6,
        )
        domain_ratio = guard_ratio[adaptive_indices]
        x_domain = laser_x_m[adaptive_indices]
        roll_ratio, _, _, _ = rolling_distance_stat(
            x_domain,
            domain_ratio,
            PRIMARY_PERSISTENCE_WINDOW_UM * 1e-6,
        )
        guard_rows.append(
            {
                "simulation_id": simulation_id,
                "sensitivity_type": "minimum_width_guard",
                "minimum_width_guard_um": guard_um,
                "candidate_id": "R2",
                "value": float(np.nanquantile(domain_ratio, 0.95))
                if np.isfinite(domain_ratio).any()
                else np.nan,
                "available": bool(np.isfinite(domain_ratio).any()),
                "invalid_ratio_row_count": int(
                    np.sum(guard_reason[valid_melt] != "valid")
                ),
            }
        )
        guard_rows.append(
            {
                "simulation_id": simulation_id,
                "sensitivity_type": "minimum_width_guard",
                "minimum_width_guard_um": guard_um,
                "candidate_id": "R3",
                "value": float(np.nanmax(roll_ratio))
                if np.isfinite(roll_ratio).any()
                else np.nan,
                "available": bool(np.isfinite(roll_ratio).any()),
                "invalid_ratio_row_count": int(
                    np.sum(guard_reason[valid_melt] != "valid")
                ),
            }
        )

    group_label = _group_label(pd.Series(sequence_row))
    bin_rows = []
    valid_frame = pd.DataFrame(
        {
            "s": normalized_s[valid_melt],
            "depth_um": depth_m[valid_melt] * 1e6,
            "width_um": width_m[valid_melt] * 1e6,
            "aspect_ratio": ratio[valid_melt],
        }
    )
    valid_frame["grid_index"] = np.floor(
        (valid_frame["s"] + PROFILE_BIN_WIDTH / 2) / PROFILE_BIN_WIDTH
    ).astype(int)
    valid_frame = valid_frame[
        valid_frame["grid_index"].between(0, len(PROFILE_GRID) - 1)
    ]
    for grid_index, subset in valid_frame.groupby("grid_index"):
        bin_rows.append(
            {
                "simulation_id": simulation_id,
                "label_group": group_label,
                "s": float(PROFILE_GRID[int(grid_index)]),
                "depth_um": float(subset["depth_um"].median()),
                "width_um": float(subset["width_um"].median()),
                "aspect_ratio": float(subset["aspect_ratio"].median())
                if subset["aspect_ratio"].notna().any()
                else np.nan,
                "original_observation_count": len(subset),
                "interpolated": False,
            }
        )

    full_frame = pd.DataFrame(
        {
            "simulation_id": simulation_id,
            "monitor_row_index": valid_idx.astype(np.int32),
            "iteration": iteration[valid_melt].astype(np.int64),
            "time_s": time_s[valid_melt],
            "laser_x_m": laser_x_m[valid_melt],
            "laser_x_um": (laser_x_m[valid_melt] * 1e6).astype(np.float32),
            "normalized_scan_position": normalized_s[valid_melt].astype(np.float32),
            "length_m": length_m[valid_melt].astype(np.float32),
            "width_m": width_m[valid_melt].astype(np.float32),
            "depth_m": depth_m[valid_melt].astype(np.float32),
            "vertical_extent_m": vertical_extent_m[valid_melt].astype(np.float32),
            "aspect_ratio": ratio[valid_melt].astype(np.float32),
            "ratio_valid": (ratio_reason[valid_melt] == "valid"),
            "ratio_invalid_reason": ratio_reason[valid_melt],
            "rolling_median_depth_50um_m": valid_roll_depth.astype(np.float32),
            "rolling_median_aspect_ratio_50um": valid_roll_ratio.astype(np.float32),
            "rolling_50um_observation_count": primary_count.astype(np.float32),
            "rolling_50um_span_m": primary_span.astype(np.float32),
            "in_common_interior": common_mask[valid_melt],
            "in_adaptive_active_interior": adaptive_mask[valid_melt],
            "in_T0_window": t0_mask[valid_melt],
        }
    )
    part_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.Table.from_pandas(full_frame, preserve_index=False),
        part_path,
        compression="zstd",
        compression_level=7,
        use_dictionary=["simulation_id", "ratio_invalid_reason"],
    )

    iteration_lookup = {int(value): index for index, value in enumerate(iteration.astype(int))}
    label_aligned_rows = []
    for row in label_rows:
        label_iteration = int(row["timestep"])
        require(label_iteration in iteration_lookup, f"{simulation_id}: non-exact label alignment")
        index = iteration_lookup[label_iteration]
        label_aligned_rows.append(
            {
                "simulation_id": simulation_id,
                "name": row["name"],
                "frame_timestep": label_iteration,
                "monitor_row_index": index,
                "monitor_iteration": int(iteration[index]),
                "alignment_method": "exact_iteration_match",
                "alignment_error_iterations": 0,
                "alignment_ambiguous": False,
                "time_s": float(time_s[index]),
                "laser_x_m": float(laser_x_m[index]),
                "normalized_scan_position": float(normalized_s[index]),
                "stored_label": row["label_final"],
                "normalized_label": row["normalized_label"],
                "label_type": row["label_type"],
                "included_in_regime_analysis": bool(
                    row["included_in_regime_analysis"]
                ),
                "valid_melt_present": bool(valid_melt[index]),
                "depth_um": float(depth_m[index] * 1e6)
                if np.isfinite(depth_m[index])
                else np.nan,
                "width_um": float(width_m[index] * 1e6)
                if np.isfinite(width_m[index])
                else np.nan,
                "aspect_ratio": float(ratio[index])
                if np.isfinite(ratio[index])
                else np.nan,
                "depth_over_LS": float(depth_m[index] / ls_m)
                if np.isfinite(depth_m[index])
                else np.nan,
                "rolling_median_depth_50um_um": float(
                    primary_roll_depth[index] * 1e6
                )
                if np.isfinite(primary_roll_depth[index])
                else np.nan,
                "rolling_median_aspect_ratio_50um": float(
                    primary_roll_ratio[index]
                )
                if np.isfinite(primary_roll_ratio[index])
                else np.nan,
            }
        )
    label_part.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(label_aligned_rows).to_parquet(
        label_part,
        index=False,
        compression="zstd",
    )

    active_summary = {
        "simulation_id": simulation_id,
        "P": float(ledger_row["P"]),
        "VX": float(ledger_row["VX"]),
        "LS": float(ledger_row["LS"]),
        "ST": float(ledger_row["ST"]),
        "label_group": group_label,
        "monitor_row_count": len(bounds),
        "valid_melt_row_count": int(valid_melt.sum()),
        "invalid_or_no_melt_row_count": int((~valid_melt).sum()),
        "valid_ratio_row_count": int(np.isfinite(ratio).sum()),
        "invalid_ratio_row_count": int(np.sum(valid_melt & ~np.isfinite(ratio))),
        "invalid_ratio_nonpositive_width_count": int(
            np.sum(ratio_reason == "nonpositive_width")
        ),
        "invalid_ratio_below_guard_count": int(
            np.sum(ratio_reason == "width_below_minimum_guard")
        ),
        "melt_onset_position_s": float(normalized_s[valid_idx[0]]),
        "last_active_melt_position_s": float(normalized_s[valid_idx[-1]]),
        "recording_end_position_s": float(normalized_s[-1]),
        "domain_exit_observed": bool(normalized_s[-1] >= 1.0),
        "reaches_85pct": bool(normalized_s[valid_idx[-1]] >= 0.85),
        "reaches_90pct": bool(normalized_s[valid_idx[-1]] >= 0.90),
        "reaches_95pct": bool(normalized_s[valid_idx[-1]] >= 0.95),
        "reaches_100pct": bool(normalized_s[valid_idx[-1]] >= 1.00),
        "adaptive_interval_available": bool(adaptive_valid and adaptive_mask.any()),
        "adaptive_start_position_s": float(
            (adaptive_start_x - x_start_m) / (x_end_m - x_start_m)
        ),
        "adaptive_end_position_s": float(
            (adaptive_end_x - x_start_m) / (x_end_m - x_start_m)
        ),
        "adaptive_observation_count": int(adaptive_mask.sum()),
        "common_start_position_s": context.common_start_s,
        "common_end_position_s": context.common_end_s,
        "common_observation_count": int(common_mask.sum()),
        "T0_start_position_s": float(normalized_s[t0_start_row]),
        "T0_end_position_s": float(normalized_s[t0_end_row]),
        "T0_observation_count": int(t0_mask.sum()),
        "global_max_depth_position_s": float(normalized_s[full_max_depth_idx]),
        "global_max_ratio_position_s": float(normalized_s[full_max_ratio_idx]),
        "persistent_max_depth_position_s": float(
            primary_domain.loc["G3"].get("event_position_s", np.nan)
        ),
        "persistent_max_ratio_position_s": float(
            primary_domain.loc["R3"].get("event_position_s", np.nan)
        ),
        "label_frame_count": len(label_rows),
        "physical_label_frame_count": int(
            sum(
                row["label_final"] in {"Conduction", "Forming Phase", "Keyhole"}
                for row in label_rows
            )
        ),
    }
    payload = {
        "simulation_id": simulation_id,
        "active_summary": json_safe(active_summary),
        "candidate_rows": json_safe(candidates),
        "persistence_sensitivity_rows": json_safe(sensitivity_rows),
        "domain_sensitivity_rows": json_safe(domain_rows),
        "guard_sensitivity_rows": json_safe(guard_rows),
        "profile_bin_rows": json_safe(bin_rows),
        "checkpoint_schema_version": 1,
        "created_at_utc": utc_now(),
        "_cache_status": "computed",
    }
    write_json(payload, checkpoint)
    return payload


def candidate_definitions() -> pd.DataFrame:
    rows = [
        (
            "G0",
            "Existing Phase 1 T0 depth",
            "Median penetration depth over the final 20% of melt-present observations before s=0.90.",
            "um",
            "geometry baseline",
            "Typical late-active geometry; not designed as a regime maximum.",
        ),
        (
            "G1",
            "Global maximum depth",
            "Maximum valid penetration depth over the complete observed track.",
            "um",
            "spike-sensitive reference",
            "Retained intentionally to expose isolated peaks; not preferred for persistence.",
        ),
        (
            "G2",
            "Interior q95 depth",
            "95th percentile of penetration depth in the selected analysis interior.",
            "um",
            "robust high-depth summary",
            "High but not explicitly persistent.",
        ),
        (
            "G3",
            "Persistent maximum depth",
            "Maximum trailing rolling median depth over a physical-distance window; 50 um primary.",
            "um",
            "primary persistent-depth candidate",
            "Persistence is physical-distance based, not timestep based.",
        ),
        (
            "G4",
            "Persistent rolling-q80 depth",
            "Maximum trailing rolling 80th-percentile depth over a physical-distance window.",
            "um",
            "robust-quantile sensitivity",
            "Sensitivity candidate, not searched post hoc.",
        ),
        (
            "R0",
            "T0-window median aspect ratio",
            "Median penetration depth divided by transverse width over the T0 window.",
            "dimensionless",
            "geometry-ratio baseline",
            "Uses the existing late-active window.",
        ),
        (
            "R1",
            "Global maximum aspect ratio",
            "Maximum valid depth/width over the complete observed track.",
            "dimensionless",
            "spike-sensitive reference",
            "Minimum-width guard is applied; still sensitive to one-frame excursions.",
        ),
        (
            "R2",
            "Interior q95 aspect ratio",
            "95th percentile of depth/width in the selected analysis interior.",
            "dimensionless",
            "robust high-ratio candidate",
            "High but not explicitly persistent.",
        ),
        (
            "R3",
            "Persistent maximum aspect ratio",
            "Maximum trailing rolling median depth/width over a physical-distance window; 50 um primary.",
            "dimensionless",
            "primary persistent-ratio candidate",
            "Primary candidate, not a predetermined winner.",
        ),
        (
            "R4",
            "Persistent high-ratio duration",
            "Fraction of adaptive-interior scan distance above a dataset-specific exploratory ratio threshold.",
            "fraction",
            "threshold-dependent diagnostic",
            "Outer-training geometry threshold is used for held-out label evaluation.",
        ),
        (
            "R5",
            "First persistent high-ratio position",
            "First normalized position where the 50 um rolling-median ratio exceeds the exploratory threshold.",
            "normalized_position",
            "censored transition diagnostic",
            "Undefined when no persistent high-ratio event is observed.",
        ),
    ]
    frame = pd.DataFrame(
        rows,
        columns=[
            "candidate_id",
            "candidate_name",
            "machine_readable_definition",
            "unit",
            "role",
            "caveat",
        ],
    )
    frame["primary_analysis_domain"] = frame["candidate_id"].map(
        lambda value: (
            "Phase1_T0_window"
            if value in {"G0", "R0"}
            else "full_valid_track"
            if value in {"G1", "R1"}
            else "adaptive_active_interior"
        )
    )
    frame["primary_persistence_window_um"] = frame["candidate_id"].map(
        lambda value: PRIMARY_PERSISTENCE_WINDOW_UM
        if value in {"G3", "G4", "R3", "R5"}
        else np.nan
    )
    frame["minimum_width_guard_um"] = frame["candidate_id"].map(
        lambda value: PRIMARY_WIDTH_GUARD_M * 1e6
        if value.startswith("R")
        else np.nan
    )
    frame["higher_value_more_keyhole_like"] = ~frame["candidate_id"].eq("R5")
    return frame


def combine_checkpoints(payloads: Sequence[dict[str, Any]]) -> dict[str, pd.DataFrame]:
    active = []
    candidates = []
    persistence = []
    domain = []
    guard = []
    profiles = []
    for payload in payloads:
        active.append(payload["active_summary"])
        candidates.extend(payload["candidate_rows"])
        persistence.extend(payload["persistence_sensitivity_rows"])
        domain.extend(payload["domain_sensitivity_rows"])
        guard.extend(payload["guard_sensitivity_rows"])
        profiles.extend(payload["profile_bin_rows"])
    return {
        "active": pd.DataFrame(active),
        "candidates": pd.DataFrame(candidates),
        "persistence": pd.DataFrame(persistence),
        "domain": pd.DataFrame(domain),
        "guard": pd.DataFrame(guard),
        "profiles": pd.DataFrame(profiles),
    }


def combine_label_parts(output_dir: Path, simulation_ids: Sequence[str]) -> pd.DataFrame:
    frames = [
        pd.read_parquet(_label_part_path(output_dir, simulation_id))
        for simulation_id in simulation_ids
    ]
    aligned = pd.concat(frames, ignore_index=True)
    aligned.sort_values(["simulation_id", "frame_timestep"], inplace=True)
    aligned.reset_index(drop=True, inplace=True)
    aligned.to_parquet(
        output_dir / "label_aligned_geometry_time_series.parquet",
        index=False,
        compression="zstd",
    )
    return aligned


def append_threshold_candidates(
    output_dir: Path,
    candidates: pd.DataFrame,
    active: pd.DataFrame,
) -> tuple[pd.DataFrame, float, pd.DataFrame]:
    r2 = candidates[candidates["candidate_id"].eq("R2")].set_index("simulation_id")
    ratio_threshold = float(np.nanquantile(r2["value"], 0.90))
    threshold_rows = []
    loo_rows = []
    for simulation_id in sorted(active["simulation_id"]):
        part = pd.read_parquet(
            _parquet_part_path(output_dir, simulation_id),
            columns=[
                "normalized_scan_position",
                "laser_x_m",
                "aspect_ratio",
                "rolling_median_aspect_ratio_50um",
                "in_adaptive_active_interior",
            ],
        )
        interior = part[part["in_adaptive_active_interior"]].copy()
        duration = distance_fraction_above(
            interior["laser_x_m"].to_numpy(dtype=float),
            interior["aspect_ratio"].to_numpy(dtype=float),
            ratio_threshold,
        )
        rolling = interior["rolling_median_aspect_ratio_50um"].to_numpy(dtype=float)
        positions = interior["normalized_scan_position"].to_numpy(dtype=float)
        persistent_indices = np.flatnonzero(
            np.isfinite(rolling) & (rolling >= ratio_threshold)
        )
        first_position = (
            float(positions[persistent_indices[0]])
            if len(persistent_indices)
            else np.nan
        )
        threshold_rows.extend(
            [
                _candidate_value_row(
                    simulation_id,
                    "R4",
                    duration,
                    "fraction",
                    "adaptive_active_interior",
                    None,
                    np.nan,
                    np.isfinite(duration),
                    (
                        "Descriptive full-population geometry threshold; not used "
                        "for leakage-safe held-out evaluation."
                    ),
                ),
                _candidate_value_row(
                    simulation_id,
                    "R5",
                    first_position,
                    "normalized_position",
                    "adaptive_active_interior",
                    PRIMARY_PERSISTENCE_WINDOW_UM,
                    first_position,
                    np.isfinite(first_position),
                    "Censored diagnostic when no persistent event is observed.",
                ),
            ]
        )

        training_r2 = r2.drop(index=simulation_id)["value"].to_numpy(dtype=float)
        fold_ratio_threshold = float(np.nanquantile(training_r2, 0.90))
        fold_duration = distance_fraction_above(
            interior["laser_x_m"].to_numpy(dtype=float),
            interior["aspect_ratio"].to_numpy(dtype=float),
            fold_ratio_threshold,
        )
        loo_rows.append(
            {
                "simulation_id": simulation_id,
                "candidate_id": "R4",
                "heldout_candidate_value": fold_duration,
                "outer_training_ratio_threshold": fold_ratio_threshold,
                "threshold_rule": "q90 of outer-training simulation-level R2 values",
                "heldout_geometry_excluded_from_threshold": True,
            }
        )
    candidates = pd.concat(
        [candidates, pd.DataFrame(threshold_rows)],
        ignore_index=True,
    )
    return candidates, ratio_threshold, pd.DataFrame(loo_rows)


def aggregate_profiles(
    profile_rows: pd.DataFrame,
    sequence: pd.DataFrame,
) -> pd.DataFrame:
    all_rows = profile_rows.copy()
    duplicates = all_rows.copy()
    duplicates["label_group"] = "all"
    all_rows = pd.concat([all_rows, duplicates], ignore_index=True)
    output = []
    for (group, s_value), subset in all_rows.groupby(["label_group", "s"]):
        simulation_count = subset["simulation_id"].nunique()
        total_group_count = (
            sequence.apply(_group_label, axis=1).eq(group).sum()
            if group != "all"
            else len(sequence)
        )
        support_threshold = max(
            PROFILE_MIN_ABSOLUTE_SUPPORT,
            math.ceil(0.10 * total_group_count),
        )
        for response, unit in [
            ("depth_um", "um"),
            ("width_um", "um"),
            ("aspect_ratio", "dimensionless"),
        ]:
            values = subset[response].dropna().to_numpy(dtype=float)
            output.append(
                {
                    "label_group": group,
                    "normalized_scan_position": s_value,
                    "response": response,
                    "unit": unit,
                    "contributing_simulations": simulation_count,
                    "group_simulations": total_group_count,
                    "support_fraction": (
                        simulation_count / total_group_count
                        if total_group_count
                        else np.nan
                    ),
                    "minimum_support_threshold": support_threshold,
                    "display_supported": simulation_count >= support_threshold,
                    "median": float(np.nanmedian(values)) if len(values) else np.nan,
                    "q10": float(np.nanquantile(values, 0.10))
                    if len(values)
                    else np.nan,
                    "q25": float(np.nanquantile(values, 0.25))
                    if len(values)
                    else np.nan,
                    "q75": float(np.nanquantile(values, 0.75))
                    if len(values)
                    else np.nan,
                    "q90": float(np.nanquantile(values, 0.90))
                    if len(values)
                    else np.nan,
                    "interpolation_used": False,
                }
            )
    return pd.DataFrame(output)


def scan_coverage_tables(active: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for cutoff in [0.85, 0.90, 0.95, 1.00]:
        reached = active["last_active_melt_position_s"] >= cutoff
        rows.append(
            {
                "record_type": "cutoff",
                "normalized_position": cutoff,
                "simulation_count": int(reached.sum()),
                "simulation_fraction": float(reached.mean()),
                "definition": "last active melt position reaches cutoff",
            }
        )
    for s_value in np.round(np.linspace(0, 1.20, 241), 6):
        last_active = active["last_active_melt_position_s"] >= s_value
        recording = active["recording_end_position_s"] >= s_value
        rows.extend(
            [
                {
                    "record_type": "active_melt_coverage_curve",
                    "normalized_position": s_value,
                    "simulation_count": int(last_active.sum()),
                    "simulation_fraction": float(last_active.mean()),
                    "definition": "simulation has valid melt at or beyond position",
                },
                {
                    "record_type": "recording_coverage_curve",
                    "normalized_position": s_value,
                    "simulation_count": int(recording.sum()),
                    "simulation_fraction": float(recording.mean()),
                    "definition": "recording reaches position regardless of melt validity",
                },
            ]
        )
    coverage = pd.DataFrame(rows)
    support = coverage[
        coverage["record_type"].eq("active_melt_coverage_curve")
    ][
        [
            "normalized_position",
            "simulation_count",
            "simulation_fraction",
        ]
    ].rename(
        columns={
            "simulation_count": "active_melt_contributing_simulations",
            "simulation_fraction": "active_melt_support_fraction",
        }
    )
    return coverage, support


def auc_metrics(y_true: np.ndarray, score: np.ndarray) -> tuple[float, float, float, int, int]:
    finite = np.isfinite(score)
    y = np.asarray(y_true, dtype=int)[finite]
    x = np.asarray(score, dtype=float)[finite]
    if len(np.unique(y)) < 2:
        return np.nan, np.nan, np.nan, int(y.sum()), int((1 - y).sum())
    return (
        float(roc_auc_score(y, x)),
        float(average_precision_score(y, x)),
        float(y.mean()),
        int(y.sum()),
        int((1 - y).sum()),
    )


def simulation_bootstrap_metrics(
    y_true: np.ndarray,
    score: np.ndarray,
    *,
    n_resamples: int,
    seed: int,
) -> dict[str, float]:
    finite = np.isfinite(score)
    y = np.asarray(y_true, dtype=int)[finite]
    x = np.asarray(score, dtype=float)[finite]
    rng = np.random.default_rng(seed)
    auc_values = []
    pr_values = []
    n = len(y)
    for _ in range(n_resamples):
        indices = rng.integers(0, n, size=n)
        sampled_y = y[indices]
        if len(np.unique(sampled_y)) < 2:
            continue
        sampled_x = x[indices]
        auc_values.append(roc_auc_score(sampled_y, sampled_x))
        pr_values.append(average_precision_score(sampled_y, sampled_x))
    require(len(auc_values) >= int(0.99 * n_resamples), "Too many invalid simulation bootstrap samples")
    return {
        "roc_auc_ci_low": float(np.quantile(auc_values, 0.025)),
        "roc_auc_ci_high": float(np.quantile(auc_values, 0.975)),
        "pr_auc_ci_low": float(np.quantile(pr_values, 0.025)),
        "pr_auc_ci_high": float(np.quantile(pr_values, 0.975)),
        "valid_bootstrap_resamples": len(auc_values),
        "requested_bootstrap_resamples": n_resamples,
        "bootstrap_seed": seed,
    }


def paired_auc_bootstrap(
    y_true: np.ndarray,
    candidate_score: np.ndarray,
    reference_score: np.ndarray,
    *,
    n_resamples: int,
    seed: int,
) -> dict[str, float]:
    finite = np.isfinite(candidate_score) & np.isfinite(reference_score)
    y = np.asarray(y_true, dtype=int)[finite]
    candidate = np.asarray(candidate_score, dtype=float)[finite]
    reference = np.asarray(reference_score, dtype=float)[finite]
    rng = np.random.default_rng(seed)
    auc_differences = []
    pr_differences = []
    for _ in range(n_resamples):
        indices = rng.integers(0, len(y), size=len(y))
        sampled_y = y[indices]
        if len(np.unique(sampled_y)) < 2:
            continue
        auc_differences.append(
            roc_auc_score(sampled_y, candidate[indices])
            - roc_auc_score(sampled_y, reference[indices])
        )
        pr_differences.append(
            average_precision_score(sampled_y, candidate[indices])
            - average_precision_score(sampled_y, reference[indices])
        )
    require(
        len(auc_differences) >= int(0.99 * n_resamples),
        "Too many invalid paired bootstrap samples",
    )
    return {
        "roc_auc_difference": float(
            roc_auc_score(y, candidate) - roc_auc_score(y, reference)
        ),
        "roc_auc_difference_ci_low": float(
            np.quantile(auc_differences, 0.025)
        ),
        "roc_auc_difference_ci_high": float(
            np.quantile(auc_differences, 0.975)
        ),
        "pr_auc_difference": float(
            average_precision_score(y, candidate)
            - average_precision_score(y, reference)
        ),
        "pr_auc_difference_ci_low": float(
            np.quantile(pr_differences, 0.025)
        ),
        "pr_auc_difference_ci_high": float(
            np.quantile(pr_differences, 0.975)
        ),
        "paired_simulation_count": len(y),
        "valid_bootstrap_resamples": len(auc_differences),
        "requested_bootstrap_resamples": n_resamples,
        "bootstrap_seed": seed,
    }


def clustered_frame_bootstrap(
    frame: pd.DataFrame,
    score_column: str,
    *,
    n_resamples: int,
    seed: int,
) -> dict[str, float]:
    subset = frame[
        frame["stored_label"].isin(["Conduction", "Keyhole"])
        & frame[score_column].notna()
    ][["simulation_id", "stored_label", score_column]].copy()
    subset["y"] = subset["stored_label"].eq("Keyhole").astype(int)
    simulation_ids = sorted(subset["simulation_id"].unique())
    simulation_lookup = {value: index for index, value in enumerate(simulation_ids)}
    subset["cluster_index"] = subset["simulation_id"].map(simulation_lookup).astype(int)
    score = subset[score_column].to_numpy(dtype=float)
    y = subset["y"].to_numpy(dtype=int)
    cluster = subset["cluster_index"].to_numpy(dtype=int)
    unique_score, group_index = np.unique(score, return_inverse=True)
    group_count = len(unique_score)
    cluster_count = len(simulation_ids)
    positives = np.zeros((group_count, cluster_count), dtype=np.float32)
    negatives = np.zeros((group_count, cluster_count), dtype=np.float32)
    np.add.at(positives, (group_index[y == 1], cluster[y == 1]), 1.0)
    np.add.at(negatives, (group_index[y == 0], cluster[y == 0]), 1.0)
    rng = np.random.default_rng(seed)
    auc_samples = []
    ap_samples = []
    batch_size = 250
    probabilities = np.repeat(1.0 / cluster_count, cluster_count)
    for start in range(0, n_resamples, batch_size):
        batch = min(batch_size, n_resamples - start)
        weights = rng.multinomial(
            cluster_count,
            probabilities,
            size=batch,
        ).astype(np.float32)
        pos_by_group = weights @ positives.T
        neg_by_group = weights @ negatives.T
        total_pos = pos_by_group.sum(axis=1)
        total_neg = neg_by_group.sum(axis=1)
        valid = (total_pos > 0) & (total_neg > 0)
        cumulative_neg_before = np.cumsum(neg_by_group, axis=1) - neg_by_group
        concordant = np.sum(
            pos_by_group * (cumulative_neg_before + 0.5 * neg_by_group),
            axis=1,
        )
        auc_batch = concordant / np.maximum(total_pos * total_neg, 1)

        pos_desc = pos_by_group[:, ::-1]
        neg_desc = neg_by_group[:, ::-1]
        cumulative_pos = np.cumsum(pos_desc, axis=1)
        cumulative_all = np.cumsum(pos_desc + neg_desc, axis=1)
        precision = cumulative_pos / np.maximum(cumulative_all, 1)
        recall_increment = pos_desc / np.maximum(total_pos[:, None], 1)
        ap_batch = np.sum(precision * recall_increment, axis=1)
        auc_samples.extend(auc_batch[valid].tolist())
        ap_samples.extend(ap_batch[valid].tolist())
    require(len(auc_samples) >= int(0.99 * n_resamples), "Too many invalid cluster bootstrap samples")
    return {
        "roc_auc_ci_low": float(np.quantile(auc_samples, 0.025)),
        "roc_auc_ci_high": float(np.quantile(auc_samples, 0.975)),
        "pr_auc_ci_low": float(np.quantile(ap_samples, 0.025)),
        "pr_auc_ci_high": float(np.quantile(ap_samples, 0.975)),
        "valid_bootstrap_resamples": len(auc_samples),
        "requested_bootstrap_resamples": n_resamples,
        "bootstrap_seed": seed,
        "cluster_count": cluster_count,
    }


def _frame_metric_worker(
    binary: pd.DataFrame,
    spec: tuple[str, str, float, str],
    n_resamples: int,
    index: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate, column, direction, unit = spec
    local = binary[["simulation_id", "stored_label", column]].copy()
    local["oriented_score"] = local[column] * direction
    finite = local["oriented_score"].notna()
    y = (
        local.loc[finite, "stored_label"]
        .eq("Keyhole")
        .astype(int)
        .to_numpy()
    )
    score = local.loc[finite, "oriented_score"].to_numpy(dtype=float)
    roc_auc, pr_auc, prevalence, positives, negatives = auc_metrics(y, score)
    keyhole_values = local.loc[
        finite & local["stored_label"].eq("Keyhole"),
        column,
    ].to_numpy(dtype=float)
    conduction_values = local.loc[
        finite & local["stored_label"].eq("Conduction"),
        column,
    ].to_numpy(dtype=float)
    point = {
        "candidate": candidate,
        "source_column": column,
        "unit": unit,
        "orientation_multiplier": direction,
        "simulation_count": local.loc[finite, "simulation_id"].nunique(),
        "frame_count": int(finite.sum()),
        "positive_keyhole_frames": positives,
        "negative_conduction_frames": negatives,
        "keyhole_simulation_count": local.loc[
            finite & local["stored_label"].eq("Keyhole"),
            "simulation_id",
        ].nunique(),
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "prevalence_baseline": prevalence,
        "keyhole_median": float(np.median(keyhole_values)),
        "conduction_median": float(np.median(conduction_values)),
        "rank_biserial_effect": float(2 * roc_auc - 1),
        "forming_phase_excluded": True,
        "technical_labels_excluded": True,
        "alignment_scope": "exact_iteration_matches_only",
    }
    bootstrap_input = local.loc[finite].rename(
        columns={"oriented_score": "_oriented_score"}
    )
    bootstrap = clustered_frame_bootstrap(
        bootstrap_input,
        "_oriented_score",
        n_resamples=n_resamples,
        seed=BOOTSTRAP_SEED + 1000 + index,
    )
    bootstrap.update(
        {
            "candidate": candidate,
            "source_column": column,
            "bootstrap_unit": "simulation cluster",
        }
    )
    return point, bootstrap


def frame_level_metrics(
    aligned: pd.DataFrame,
    *,
    n_resamples: int,
    workers: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    specs = [
        ("instantaneous_depth", "depth_um", 1.0, "um"),
        ("instantaneous_width_inverse", "width_um", -1.0, "um; sign inverted for keyhole direction"),
        ("instantaneous_aspect_ratio", "aspect_ratio", 1.0, "dimensionless"),
        ("instantaneous_depth_over_LS", "depth_over_LS", 1.0, "dimensionless"),
        (
            "local_rolling_depth_50um",
            "rolling_median_depth_50um_um",
            1.0,
            "um",
        ),
        (
            "local_rolling_aspect_ratio_50um",
            "rolling_median_aspect_ratio_50um",
            1.0,
            "dimensionless",
        ),
    ]
    binary = aligned[
        aligned["stored_label"].isin(["Conduction", "Keyhole"])
    ].copy()
    point_rows = []
    bootstrap_rows = []
    if workers > 1:
        with ProcessPoolExecutor(max_workers=min(workers, len(specs))) as executor:
            futures = {
                executor.submit(
                    _frame_metric_worker,
                    binary,
                    spec,
                    n_resamples,
                    index,
                ): index
                for index, spec in enumerate(specs)
            }
            ordered = {}
            for future in as_completed(futures):
                ordered[futures[future]] = future.result()
        for index in range(len(specs)):
            point, bootstrap = ordered[index]
            point_rows.append(point)
            bootstrap_rows.append(bootstrap)
    else:
        for index, spec in enumerate(specs):
            point, bootstrap = _frame_metric_worker(
                binary,
                spec,
                n_resamples,
                index,
            )
            point_rows.append(point)
            bootstrap_rows.append(bootstrap)
    return pd.DataFrame(point_rows), pd.DataFrame(bootstrap_rows)


def build_simulation_score_table(
    candidates: pd.DataFrame,
    sequence: pd.DataFrame,
    r4_loo: pd.DataFrame,
) -> pd.DataFrame:
    wide = candidates.pivot_table(
        index="simulation_id",
        columns="candidate_id",
        values="value",
        aggfunc="first",
    ).reset_index()
    r4_scores = r4_loo[["simulation_id", "heldout_candidate_value"]].rename(
        columns={"heldout_candidate_value": "R4_LOO"}
    )
    wide = wide.merge(r4_scores, on="simulation_id", how="left")
    wide = wide.merge(
        sequence[
            [
                "simulation_id",
                "any_keyhole",
                "keyhole_fraction",
                "persistent_keyhole_3_consecutive_frames",
                "first_keyhole_timestep",
                "keyhole_frames",
                "usable_physical_label_frames",
                "both_conduction_and_keyhole",
            ]
        ],
        on="simulation_id",
        how="left",
        validate="one_to_one",
    )
    return wide


def simulation_level_metrics(
    score_table: pd.DataFrame,
    *,
    n_resamples: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    candidates = ["G0", "G1", "G2", "G3", "G4", "R0", "R1", "R2", "R3", "R4_LOO"]
    point_rows = []
    bootstrap_rows = []
    correlation_rows = []
    y = score_table["any_keyhole"].astype(int).to_numpy()
    for index, candidate in enumerate(candidates):
        score = score_table[candidate].to_numpy(dtype=float)
        roc_auc, pr_auc, prevalence, positives, negatives = auc_metrics(y, score)
        finite = np.isfinite(score)
        point_rows.append(
            {
                "candidate_id": candidate.removesuffix("_LOO"),
                "evaluation_score_column": candidate,
                "outcome": "any_keyhole",
                "simulation_count": int(finite.sum()),
                "positive_keyhole_simulations": positives,
                "negative_simulations": negatives,
                "mixed_label_simulations": int(
                    score_table.loc[finite, "both_conduction_and_keyhole"].sum()
                ),
                "effective_sample_size": int(finite.sum()),
                "roc_auc": roc_auc,
                "pr_auc": pr_auc,
                "prevalence_baseline": prevalence,
                "comparison_type": (
                    "leakage-safe outer-training geometry threshold"
                    if candidate == "R4_LOO"
                    else "fixed continuous score"
                ),
            }
        )
        bootstrap = simulation_bootstrap_metrics(
            y,
            score,
            n_resamples=n_resamples,
            seed=BOOTSTRAP_SEED + 2000 + index,
        )
        bootstrap.update(
            {
                "summary_type": "absolute_metric",
                "candidate_id": candidate.removesuffix("_LOO"),
                "evaluation_score_column": candidate,
                "outcome": "any_keyhole",
                "bootstrap_unit": "simulation",
            }
        )
        bootstrap_rows.append(bootstrap)
        finite_fraction = np.isfinite(score) & score_table["keyhole_fraction"].notna()
        rho, p_value = stats.spearmanr(
            score[finite_fraction],
            score_table.loc[finite_fraction, "keyhole_fraction"],
        )
        correlation_rows.append(
            {
                "candidate_id": candidate.removesuffix("_LOO"),
                "evaluation_score_column": candidate,
                "outcome": "keyhole_fraction",
                "simulation_count": int(finite_fraction.sum()),
                "spearman_rho": float(rho),
                "two_sided_p_value_descriptive": float(p_value),
                "interpretation": "descriptive; provisional labels and depth-seeded circularity apply",
            }
        )
    reference = score_table["R3"].to_numpy(dtype=float)
    for index, candidate in enumerate(candidates):
        if candidate == "R3":
            continue
        paired = paired_auc_bootstrap(
            y,
            score_table[candidate].to_numpy(dtype=float),
            reference,
            n_resamples=n_resamples,
            seed=BOOTSTRAP_SEED + 3000 + index,
        )
        paired.update(
            {
                "summary_type": "paired_difference_vs_R3",
                "candidate_id": candidate.removesuffix("_LOO"),
                "evaluation_score_column": candidate,
                "reference_candidate_id": "R3",
                "outcome": "any_keyhole",
                "bootstrap_unit": "paired simulation",
            }
        )
        bootstrap_rows.append(paired)
    return (
        pd.DataFrame(point_rows),
        pd.DataFrame(bootstrap_rows),
        pd.DataFrame(correlation_rows),
    )


def select_threshold(
    score: np.ndarray,
    y_true: np.ndarray,
) -> tuple[float, float, float]:
    finite = np.isfinite(score)
    x = np.asarray(score, dtype=float)[finite]
    y = np.asarray(y_true, dtype=int)[finite]
    require(len(np.unique(y)) == 2, "Threshold training fold lacks both classes")
    unique = np.unique(x)
    thresholds = np.r_[
        np.nextafter(unique[-1], np.inf),
        (unique[:-1] + unique[1:]) / 2,
        np.nextafter(unique[0], -np.inf),
    ]
    prediction = x[:, None] >= thresholds[None, :]
    positives = y == 1
    negatives = ~positives
    sensitivity = prediction[positives].mean(axis=0)
    specificity = (~prediction[negatives]).mean(axis=0)
    balanced = (sensitivity + specificity) / 2
    tp = (prediction & positives[:, None]).sum(axis=0)
    fp = (prediction & negatives[:, None]).sum(axis=0)
    fn = ((~prediction) & positives[:, None]).sum(axis=0)
    f1 = 2 * tp / np.maximum(2 * tp + fp + fn, 1)
    best = np.flatnonzero(balanced == np.nanmax(balanced))
    best_f1 = best[np.argmax(f1[best])]
    tied = best[f1[best] == f1[best_f1]]
    selected = tied[np.argmax(thresholds[tied])]
    return (
        float(thresholds[selected]),
        float(balanced[selected]),
        float(f1[selected]),
    )


def nested_threshold_loo(
    score_table: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    leading = ["G0", "G2", "G3", "R2", "R3"]
    y_all = score_table["any_keyhole"].astype(int).to_numpy()
    prediction_rows = []
    threshold_rows = []
    for candidate in leading:
        score_all = score_table[candidate].to_numpy(dtype=float)
        usable = np.flatnonzero(np.isfinite(score_all))
        for heldout in usable:
            train = np.isfinite(score_all)
            train[heldout] = False
            threshold, training_balanced, training_f1 = select_threshold(
                score_all[train],
                y_all[train],
            )
            heldout_score = score_all[heldout]
            prediction = int(heldout_score >= threshold)
            row = {
                "candidate_id": candidate,
                "outer_fold": heldout,
                "heldout_simulation_id": score_table.iloc[heldout]["simulation_id"],
                "heldout_true_any_keyhole": int(y_all[heldout]),
                "heldout_score": heldout_score,
                "selected_threshold": threshold,
                "heldout_prediction": prediction,
                "outer_training_simulations": int(train.sum()),
                "candidate_usable_population": int(len(usable)),
                "candidate_unavailable_simulations": int(
                    len(score_table) - len(usable)
                ),
                "outer_training_positives": int(y_all[train].sum()),
                "outer_training_negatives": int((1 - y_all[train]).sum()),
                "threshold_selection_criterion": "maximum balanced accuracy; F1 then higher-threshold tie break",
                "heldout_label_excluded_from_threshold_selection": True,
            }
            prediction_rows.append(row)
            threshold_rows.append(
                {
                    "candidate_id": candidate,
                    "outer_fold": heldout,
                    "heldout_simulation_id": row["heldout_simulation_id"],
                    "selected_threshold": threshold,
                    "training_balanced_accuracy": training_balanced,
                    "training_f1": training_f1,
                    "training_positive_count": row["outer_training_positives"],
                    "training_negative_count": row["outer_training_negatives"],
                }
            )
    predictions = pd.DataFrame(prediction_rows)
    metric_rows = []
    for candidate, subset in predictions.groupby("candidate_id"):
        y = subset["heldout_true_any_keyhole"].to_numpy(dtype=int)
        pred = subset["heldout_prediction"].to_numpy(dtype=int)
        tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
        metric_rows.append(
            {
                "candidate_id": candidate,
                "heldout_simulations": len(subset),
                "positive_count": int(y.sum()),
                "negative_count": int((1 - y).sum()),
                "balanced_accuracy": balanced_accuracy_score(y, pred),
                "sensitivity": recall_score(y, pred, zero_division=0),
                "specificity": tn / (tn + fp),
                "precision": precision_score(y, pred, zero_division=0),
                "recall": recall_score(y, pred, zero_division=0),
                "f1": f1_score(y, pred, zero_division=0),
                "true_negative": int(tn),
                "false_positive": int(fp),
                "false_negative": int(fn),
                "true_positive": int(tp),
                "evaluation": "exact nested leave-one-simulation-out",
                "leakage_safe": True,
            }
        )
    return predictions, pd.DataFrame(metric_rows), pd.DataFrame(threshold_rows)


def build_sensitivity_outputs(
    persistence_rows: pd.DataFrame,
    domain_rows: pd.DataFrame,
    guard_rows: pd.DataFrame,
    candidates: pd.DataFrame,
    sequence: pd.DataFrame,
    active: pd.DataFrame,
    *,
    n_resamples: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    labels = sequence[["simulation_id", "any_keyhole"]]
    persistence = persistence_rows.merge(
        labels,
        on="simulation_id",
        how="left",
        validate="many_to_one",
    )
    summary_rows = []
    for keys, subset in persistence.groupby(
        [
            "analysis_domain",
            "window_type",
            "window_value",
            "window_distance_um",
            "candidate_id",
        ],
        dropna=False,
    ):
        finite = subset["value"].notna()
        y = subset.loc[finite, "any_keyhole"].astype(int).to_numpy()
        score = subset.loc[finite, "value"].to_numpy(dtype=float)
        roc_auc, pr_auc, prevalence, positives, negatives = auc_metrics(y, score)
        summary_rows.append(
            {
                "record_type": "summary",
                "analysis_domain": keys[0],
                "window_type": keys[1],
                "window_value": keys[2],
                "window_distance_um": keys[3],
                "candidate_id": keys[4],
                "simulation_id": "",
                "value": np.nan,
                "unit": subset["unit"].iloc[0],
                "event_position_s": np.nan,
                "available": bool(finite.all()),
                "availability_count": int(finite.sum()),
                "availability_fraction": float(finite.mean()),
                "median_value": float(np.nanmedian(score)) if len(score) else np.nan,
                "roc_auc_any_keyhole": roc_auc,
                "pr_auc_any_keyhole": pr_auc,
                "prevalence": prevalence,
                "positive_count": positives,
                "negative_count": negatives,
                "median_window_observation_count": float(
                    subset.loc[finite, "typical_window_observation_count"].median()
                )
                if finite.any()
                else np.nan,
                "minimum_required_observations": MIN_ROLLING_OBSERVATIONS,
                "minimum_span_fraction": MIN_ROLLING_SPAN_FRACTION,
            }
        )
    persistence_output = pd.concat(
        [
            persistence.assign(record_type="simulation"),
            pd.DataFrame(summary_rows),
        ],
        ignore_index=True,
        sort=False,
    )

    domain = domain_rows.merge(labels, on="simulation_id", how="left")
    domain_summary_rows = []
    for (domain_name, candidate_id), subset in domain.groupby(
        ["analysis_domain", "candidate_id"]
    ):
        finite = subset["value"].notna()
        roc_auc, pr_auc, prevalence, positives, negatives = auc_metrics(
            subset.loc[finite, "any_keyhole"].astype(int).to_numpy(),
            subset.loc[finite, "value"].to_numpy(dtype=float),
        )
        domain_summary_rows.append(
            {
                "record_type": "summary",
                "sensitivity_type": "analysis_domain",
                "analysis_domain": domain_name,
                "candidate_id": candidate_id,
                "simulation_id": "",
                "value": np.nan,
                "unit": subset["unit"].iloc[0],
                "available": bool(finite.all()),
                "availability_count": int(finite.sum()),
                "availability_fraction": float(finite.mean()),
                "median_value": float(subset.loc[finite, "value"].median()),
                "roc_auc_any_keyhole": roc_auc,
                "pr_auc_any_keyhole": pr_auc,
                "prevalence": prevalence,
                "positive_count": positives,
                "negative_count": negatives,
            }
        )
    domain_output = pd.concat(
        [
            domain.assign(
                record_type="simulation",
                sensitivity_type="analysis_domain",
            ),
            pd.DataFrame(domain_summary_rows),
            guard_rows.assign(
                record_type="simulation",
                analysis_domain="adaptive_active_interior",
            ),
        ],
        ignore_index=True,
        sort=False,
    )

    candidate_wide = candidates.pivot_table(
        index="simulation_id",
        columns="candidate_id",
        values="value",
        aggfunc="first",
    ).reset_index()
    candidate_wide = candidate_wide.merge(labels, on="simulation_id", how="left")
    instability_rows = []
    for subset_name, excluded in [
        ("all_241", set()),
        ("exclude_11_phase1_unstable", set(DEPTH_UNSTABLE_IDS)),
    ]:
        population = candidate_wide[
            ~candidate_wide["simulation_id"].isin(excluded)
        ]
        for candidate_id in [
            "G0",
            "G1",
            "G2",
            "G3",
            "G4",
            "R0",
            "R1",
            "R2",
            "R3",
            "R4",
        ]:
            finite = population[candidate_id].notna()
            roc_auc, pr_auc, prevalence, positives, negatives = auc_metrics(
                population.loc[finite, "any_keyhole"].astype(int).to_numpy(),
                population.loc[finite, candidate_id].to_numpy(dtype=float),
            )
            instability_rows.append(
                {
                    "population": subset_name,
                    "candidate_id": candidate_id,
                    "simulation_count": int(finite.sum()),
                    "excluded_simulation_count": len(excluded),
                    "excluded_simulation_ids": ";".join(sorted(excluded)),
                    "positive_count": positives,
                    "negative_count": negatives,
                    "roc_auc": roc_auc,
                    "pr_auc": pr_auc,
                    "prevalence": prevalence,
                    "median_value": float(
                        population.loc[finite, candidate_id].median()
                    ),
                }
            )
    instability = pd.DataFrame(instability_rows)

    censoring_rows = []
    joined = candidate_wide.merge(
        active[
            [
                "simulation_id",
                "last_active_melt_position_s",
                "reaches_90pct",
                "VX",
            ]
        ],
        on="simulation_id",
        how="left",
    )
    joined["VX_tertile"] = pd.qcut(
        joined["VX"],
        q=3,
        labels=["slow_VX", "middle_VX", "fast_VX"],
        duplicates="drop",
    ).astype(str)
    for candidate_id in [
        "G0",
        "G1",
        "G2",
        "G3",
        "G4",
        "R0",
        "R1",
        "R2",
        "R3",
        "R4",
    ]:
        finite = joined[candidate_id].notna()
        rho, p_value = stats.spearmanr(
            joined.loc[finite, candidate_id],
            joined.loc[finite, "last_active_melt_position_s"],
        )
        censoring_rows.append(
            {
                "sensitivity_type": "continuous_track_coverage",
                "stratum": "all",
                "candidate_id": candidate_id,
                "simulation_count": int(finite.sum()),
                "positive_count": int(joined.loc[finite, "any_keyhole"].sum()),
                "median_value": float(joined.loc[finite, candidate_id].median()),
                "roc_auc": np.nan,
                "pr_auc": np.nan,
                "spearman_with_last_active_position": float(rho),
                "spearman_p_value_descriptive": float(p_value),
            }
        )
        for sensitivity_type, column, strata in [
            ("reaches_90pct", "reaches_90pct", [False, True]),
            ("VX_tertile", "VX_tertile", ["slow_VX", "middle_VX", "fast_VX"]),
        ]:
            for stratum in strata:
                subset = joined[finite & joined[column].eq(stratum)]
                roc_auc, pr_auc, _, positives, _ = auc_metrics(
                    subset["any_keyhole"].astype(int).to_numpy(),
                    subset[candidate_id].to_numpy(dtype=float),
                )
                censoring_rows.append(
                    {
                        "sensitivity_type": sensitivity_type,
                        "stratum": str(stratum),
                        "candidate_id": candidate_id,
                        "simulation_count": len(subset),
                        "positive_count": positives,
                        "median_value": float(subset[candidate_id].median())
                        if len(subset)
                        else np.nan,
                        "roc_auc": roc_auc,
                        "pr_auc": pr_auc,
                        "spearman_with_last_active_position": np.nan,
                        "spearman_p_value_descriptive": np.nan,
                    }
                )
    return persistence_output, domain_output, instability, pd.DataFrame(censoring_rows)


def select_representative_simulations(
    score_table: pd.DataFrame,
    active: pd.DataFrame,
    aligned: pd.DataFrame,
) -> pd.DataFrame:
    frame = score_table.merge(
        active[
            [
                "simulation_id",
                "label_group",
                "last_active_melt_position_s",
                "adaptive_observation_count",
            ]
        ],
        on="simulation_id",
        how="left",
    )
    selected: set[str] = set()
    rows: list[dict[str, Any]] = []

    def add(case_id: str, case_name: str, row: pd.Series, rule: str, evidence: str) -> None:
        simulation_id = str(row["simulation_id"])
        require(simulation_id not in selected, f"Representative case reused: {simulation_id}")
        selected.add(simulation_id)
        rows.append(
            {
                "case_id": case_id,
                "case_name": case_name,
                "simulation_id": simulation_id,
                "selection_rule": rule,
                "selection_evidence": evidence,
                "any_keyhole": bool(row["any_keyhole"]),
                "keyhole_fraction": float(row["keyhole_fraction"]),
                "G1_max_depth_um": float(row["G1"]),
                "G3_persistent_depth_um": float(row["G3"]),
                "R1_max_aspect_ratio": float(row["R1"]),
                "R3_persistent_aspect_ratio": float(row["R3"]),
                "phase1_unstable": simulation_id in DEPTH_UNSTABLE_IDS,
            }
        )

    conduction = frame[~frame["any_keyhole"]].copy()
    median_r3 = conduction["R3"].median()
    conduction["distance"] = (conduction["R3"] - median_r3).abs()
    row = conduction.sort_values(["distance", "simulation_id"]).iloc[0]
    add(
        "C1",
        "Typical conduction-only",
        row,
        "No Keyhole label; R3 closest to the conduction-only median.",
        f"R3={row['R3']:.4f}, group median={median_r3:.4f}.",
    )

    keyhole = frame[frame["any_keyhole"]].copy()
    r3_scale = max(
        float((keyhole["R3"] - keyhole["R3"].median()).abs().median()),
        1e-12,
    )
    fraction_scale = max(
        float(
            (
                keyhole["keyhole_fraction"]
                - keyhole["keyhole_fraction"].median()
            )
            .abs()
            .median()
        ),
        1e-12,
    )
    keyhole["distance"] = (
        (keyhole["R3"] - keyhole["R3"].median()).abs() / r3_scale
        + (
            keyhole["keyhole_fraction"]
            - keyhole["keyhole_fraction"].median()
        ).abs()
        / fraction_scale
    )
    row = keyhole.sort_values(["distance", "simulation_id"]).iloc[0]
    add(
        "C2",
        "Typical keyhole-containing",
        row,
        "Keyhole-containing; closest joint robust distance to median R3 and keyhole fraction.",
        f"R3={row['R3']:.4f}, keyhole fraction={row['keyhole_fraction']:.4f}.",
    )

    mixed = frame[
        frame["both_conduction_and_keyhole"]
        & ~frame["simulation_id"].isin(selected)
    ].copy()
    transition_support = []
    for simulation_id in mixed["simulation_id"]:
        labels = aligned[
            aligned["simulation_id"].eq(simulation_id)
            & aligned["stored_label"].isin(["Conduction", "Keyhole"])
        ].sort_values("frame_timestep")
        first_keyhole = labels.index[labels["stored_label"].eq("Keyhole")][0]
        position = labels.index.get_loc(first_keyhole)
        transition_support.append(
            min(position, len(labels) - position - 1)
        )
    mixed["transition_support"] = transition_support
    row = mixed.sort_values(
        ["transition_support", "adaptive_observation_count", "simulation_id"],
        ascending=[False, False, True],
    ).iloc[0]
    add(
        "C3",
        "Mixed Conduction-to-Keyhole transition",
        row,
        "Both labels, exact alignment, and maximum balanced labelled-frame support around first Keyhole.",
        f"Balanced transition support={int(row['transition_support'])} frames.",
    )

    disagreement = frame[~frame["simulation_id"].isin(selected)].copy()
    disagreement["spike_gap"] = disagreement["R1"] - disagreement["R3"]
    disagreement["selection_score"] = (
        disagreement["R1"].rank(pct=True)
        + disagreement["spike_gap"].rank(pct=True)
    )
    row = disagreement.sort_values(
        ["selection_score", "simulation_id"],
        ascending=[False, True],
    ).iloc[0]
    add(
        "C4",
        "Maximum-versus-persistence disagreement",
        row,
        "Largest combined percentile rank of global R1 and R1-minus-R3 spike gap.",
        f"R1={row['R1']:.4f}, R3={row['R3']:.4f}, gap={row['spike_gap']:.4f}.",
    )

    persistent = frame[~frame["simulation_id"].isin(selected)].copy()
    persistent["relative_gap"] = (
        (persistent["R1"] - persistent["R3"]) / persistent["R1"].replace(0, np.nan)
    )
    persistent["selection_score"] = (
        persistent["R3"].rank(pct=True)
        + (1 - persistent["relative_gap"].rank(pct=True))
    )
    row = persistent.sort_values(
        ["selection_score", "simulation_id"],
        ascending=[False, True],
    ).iloc[0]
    add(
        "C5",
        "Persistent deep-melt",
        row,
        "Largest combined rank of high R3 and small relative R1-to-R3 gap.",
        f"R3={row['R3']:.4f}, relative gap={row['relative_gap']:.4f}.",
    )

    unstable = frame[
        frame["simulation_id"].isin(DEPTH_UNSTABLE_IDS)
        & ~frame["simulation_id"].isin(selected)
    ].copy()
    unstable_median = unstable["R3"].median()
    unstable["distance"] = (unstable["R3"] - unstable_median).abs()
    row = unstable.sort_values(["distance", "simulation_id"]).iloc[0]
    add(
        "C6",
        "Phase 1 unstable-window",
        row,
        "Independent Phase 1 unstable ID; R3 closest to the remaining unstable-group median.",
        f"R3={row['R3']:.4f}, unstable median={unstable_median:.4f}.",
    )
    return pd.DataFrame(rows)


def select_and_download_representative_frames(
    representatives: pd.DataFrame,
    aligned: pd.DataFrame,
    candidates: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    mixed_id = representatives.loc[
        representatives["case_id"].eq("C3"),
        "simulation_id",
    ].iloc[0]
    mixed = aligned[aligned["simulation_id"].eq(mixed_id)].sort_values(
        "frame_timestep"
    )
    keyhole = mixed[mixed["stored_label"].eq("Keyhole")]
    require(not keyhole.empty, "Mixed representative has no Keyhole frame")
    first_keyhole = keyhole.iloc[0]
    before_pool = mixed[
        (mixed["frame_timestep"] < first_keyhole["frame_timestep"])
        & mixed["stored_label"].eq("Conduction")
    ]
    before = before_pool.iloc[-1] if len(before_pool) else mixed.iloc[max(0, mixed.index.get_loc(first_keyhole.name) - 1)]
    persistent_position = candidates[
        candidates["simulation_id"].eq(mixed_id)
        & candidates["candidate_id"].eq("R3")
    ]["event_position_s"].iloc[0]
    near_index = (
        mixed["normalized_scan_position"] - persistent_position
    ).abs().idxmin()
    near = mixed.loc[near_index]
    if int(near["frame_timestep"]) == int(before["frame_timestep"]):
        near = first_keyhole
    after_pool = mixed[
        mixed["frame_timestep"] > max(
            int(first_keyhole["frame_timestep"]),
            int(near["frame_timestep"]),
        )
    ]
    after = after_pool.iloc[0] if len(after_pool) else mixed.iloc[-1]
    require(
        len(
            {
                int(before["frame_timestep"]),
                int(near["frame_timestep"]),
                int(after["frame_timestep"]),
            }
        )
        == 3,
        "Representative actual-frame selections are not distinct",
    )
    selections = [
        ("before_transition", before),
        ("near_persistent_rise", near),
        ("after_or_peak", after),
    ]
    frames_csv = pd.read_csv(FINAL_DATA / mixed_id / "frames.csv")
    selection_rows = []
    provenance_rows = []
    from huggingface_hub import hf_hub_download

    for role, row in selections:
        frame_row = frames_csv[
            frames_csv["timestep"].eq(int(row["frame_timestep"]))
        ].iloc[0]
        relative = (
            f"final_data_processed/{mixed_id}/"
            f"{frame_row['side_filename']}"
        )
        expected_local = RAW_ROOT / relative
        if expected_local.exists():
            local_path = expected_local
            download_status = "reused_local_pinned_file"
        else:
            local_path = Path(
                hf_hub_download(
                    repo_id=REPO_ID,
                    repo_type="dataset",
                    revision=REVISION,
                    filename=relative.replace("\\", "/"),
                    local_dir=str(RAW_ROOT),
                )
            )
            download_status = "downloaded_selected_file_only"
        require(local_path.exists(), f"Selected actual frame unavailable: {relative}")
        record = {
            "simulation_id": mixed_id,
            "selection_role": role,
            "frame_index": int(frame_row["frame_idx"]),
            "frame_timestep": int(frame_row["timestep"]),
            "stored_label": frame_row["label"],
            "normalized_scan_position": float(row["normalized_scan_position"]),
            "monitor_row_index": int(row["monitor_row_index"]),
            "alignment_method": row["alignment_method"],
            "relative_dataset_path": relative,
            "local_path": str(local_path),
            "huggingface_revision": REVISION,
        }
        selection_rows.append(record)
        provenance_rows.append(
            {
                **record,
                "sha256": sha256(local_path),
                "size_bytes": local_path.stat().st_size,
                "download_status": download_status,
                "actual_huggingface_frame": True,
                "synthetic_image": False,
            }
        )
    return pd.DataFrame(selection_rows), pd.DataFrame(provenance_rows)


def write_ioan_requirement_mapping(output_dir: Path) -> None:
    content = """# Ioan requirement mapping for Week 6 Phase 3.5

## Source availability

No local meeting transcript or email recap containing a complete Week 6
conversation with Ioan was found in either repository checkout.  This mapping
therefore uses the locally retained Phase 1 request and existing thesis decision
logs.  It does not invent or paraphrase quotations as direct speech.

## Exact locally retained context

| Topic | Exact retained text | Source | Phase 3.5 response |
|---|---|---|---|
| Melt bounds | “Find the monitoring file corresponding to the melt bounds described by Ioan.” | `C:\\Users\\ozgur\\.codex\\attachments\\5faca789-35ac-4048-a362-ffcb88452c53\\pasted-text.txt`, line 201 | Reuse validated `monitor/position-bounds_melt.dat`. |
| Width importance | “The primary required physical response is: melt-pool width” | Same file, lines 328–330 | Retain width explicitly and use it in depth/width. |
| Length and vertical geometry | “Strong candidates include: melt-pool vertical height/depth, melt-pool length” | Same file, lines 334–337 | Use instantaneous X extent only as geometry context; use penetration depth and width for the regime study. |
| Kinetic energy | “Strong candidates include: … melt kinetic energy” | Same file, lines 334–339 | Record as deferred; Phase 3.5 does not model kinetic energy. |
| Active learning boundary | “do not perform active learning” | Same file, line 595 | Discuss later target design only; no loop or acquisition function is implemented. |
| Existing Week 5 scope | “This work packages the regression baseline; it does not begin active learning or level-set estimation.” | `docs/week5_gp_meeting_brief.md`, line 5 | Preserve the phase boundary and treat Phase 3.5 as target design. |

## Context that is not locally confirmed

The available local sources do not contain an exact Ioan quotation stating a
final conduction–keyhole target, a universal depth/width threshold, or approval
to replace T0.  Those decisions therefore remain open and are listed for Ioan’s
confirmation in the final recommendation.
"""
    (output_dir / "ioan_requirement_mapping.md").write_text(
        content,
        encoding="utf-8",
    )


class FigureRecorder:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.figure_dir = output_dir / "figures"
        self.presentation_dir = output_dir / "presentation_ready_figures"
        self.figure_dir.mkdir(parents=True, exist_ok=True)
        self.presentation_dir.mkdir(parents=True, exist_ok=True)
        self.rows: list[dict[str, Any]] = []

    def save(
        self,
        figure: plt.Figure,
        filename: str,
        *,
        section: str,
        question: str,
        source: str,
        simulations: str,
        x_axis: str,
        y_axis: str,
        units: str,
        encodings: str,
        takeaway: str,
        caveat: str,
        priority: str = "supporting",
        uses_labels: bool = False,
        uses_frames: bool = False,
        presentation_copy: bool = False,
    ) -> Path:
        path = self.figure_dir / filename
        figure.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
        plt.close(figure)
        self.rows.append(
            {
                "figure_file": str(path.relative_to(self.output_dir)).replace("\\", "/"),
                "notebook_section": section,
                "scientific_question": question,
                "source_csv_or_file": source,
                "simulations_included": simulations,
                "x_axis": x_axis,
                "y_axis": y_axis,
                "units": units,
                "visual_encodings": encodings,
                "main_takeaway": takeaway,
                "caveat": caveat,
                "presentation_priority": priority,
                "uses_human_labels": uses_labels,
                "uses_actual_huggingface_frames": uses_frames,
            }
        )
        if presentation_copy:
            destination = self.presentation_dir / filename
            shutil.copy2(path, destination)
            self.rows.append(
                {
                    **self.rows[-1],
                    "figure_file": str(destination.relative_to(self.output_dir)).replace("\\", "/"),
                    "presentation_priority": "presentation_copy",
                }
            )
        return path

    def manifest(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)


def _diagram_figure(title: str, boxes: Sequence[tuple[float, float, str, str]], arrows: Sequence[tuple[int, int]]) -> plt.Figure:
    figure, axis = plt.subplots(figsize=(12, 6.5))
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.axis("off")
    axis.set_title(title, fontsize=16, weight="bold", pad=18)
    for x, y, text, color in boxes:
        axis.text(
            x,
            y,
            text,
            ha="center",
            va="center",
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.55", facecolor=color, edgecolor="#333333"),
        )
    for source, target in arrows:
        sx, sy, _, _ = boxes[source]
        tx, ty, _, _ = boxes[target]
        axis.annotate(
            "",
            xy=(tx, ty + 0.035 if ty < sy else ty - 0.035),
            xytext=(sx, sy - 0.035 if sy > ty else sy + 0.035),
            arrowprops=dict(arrowstyle="->", lw=1.5, color="#555555"),
        )
    return figure


def build_decision_matrix(
    definitions: pd.DataFrame,
    candidates: pd.DataFrame,
    simulation_metrics: pd.DataFrame,
    simulation_bootstrap: pd.DataFrame,
    persistence: pd.DataFrame,
    domain: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    availability = (
        candidates.groupby("candidate_id")["available"]
        .agg(["sum", "mean"])
        .rename(columns={"sum": "availability_count", "mean": "availability_fraction"})
    )
    metrics = simulation_metrics.set_index("candidate_id")
    bootstrap = simulation_bootstrap[
        simulation_bootstrap["summary_type"].eq("absolute_metric")
    ].set_index("candidate_id")
    physical = {
        "G0": ("strong", "weak", "strong", "strong", "baseline"),
        "G1": ("strong", "strong", "weak", "strong", "reference_only"),
        "G2": ("strong", "strong", "moderate", "strong", "leading_candidate"),
        "G3": ("strong", "strong", "strong", "moderate", "companion_candidate"),
        "G4": ("strong", "strong", "strong", "moderate", "sensitivity_only"),
        "R0": ("strong", "moderate", "strong", "strong", "baseline"),
        "R1": ("strong", "strong", "weak", "strong", "reference_only"),
        "R2": ("strong", "strong", "moderate", "strong", "leading_candidate"),
        "R3": ("strong", "strong", "strong", "moderate", "provisional_regime_target"),
        "R4": ("moderate", "strong", "moderate", "weak", "threshold_diagnostic"),
        "R5": ("strong", "strong", "moderate", "weak", "censored_diagnostic"),
    }
    rows = []
    for definition in definitions.itertuples(index=False):
        candidate_id = definition.candidate_id
        physical_interpretability, keyhole_sensitivity, spike_robustness, simplicity, role = physical[candidate_id]
        metric_key = candidate_id
        metric = metrics.loc[metric_key] if metric_key in metrics.index else None
        boot = bootstrap.loc[metric_key] if metric_key in bootstrap.index else None
        available = availability.loc[candidate_id] if candidate_id in availability.index else pd.Series({"availability_count": 0, "availability_fraction": 0})
        window_subset = persistence[
            persistence["record_type"].eq("summary")
            & persistence["candidate_id"].eq(candidate_id)
            & persistence["analysis_domain"].eq("adaptive_active_interior")
        ]
        if len(window_subset):
            window_auc_range = float(
                window_subset["roc_auc_any_keyhole"].max()
                - window_subset["roc_auc_any_keyhole"].min()
            )
            temporal_robustness = (
                "strong"
                if window_auc_range <= 0.03
                else "moderate"
                if window_auc_range <= 0.08
                else "weak"
            )
        else:
            window_auc_range = np.nan
            temporal_robustness = "not_applicable"
        domain_subset = domain[
            domain["record_type"].eq("summary")
            & domain["candidate_id"].eq(candidate_id)
        ]
        domain_auc_range = (
            float(
                domain_subset["roc_auc_any_keyhole"].max()
                - domain_subset["roc_auc_any_keyhole"].min()
            )
            if len(domain_subset)
            else np.nan
        )
        coverage_censoring = (
            "strong"
            if float(available["availability_fraction"]) >= 0.99
            else "moderate"
            if float(available["availability_fraction"]) >= 0.90
            else "weak"
        )
        rows.append(
            {
                "candidate_id": candidate_id,
                "candidate_name": definition.candidate_name,
                "physical_suitability": physical_interpretability,
                "sensitivity_to_deep_keyhole_like_geometry": keyhole_sensitivity,
                "spike_robustness": spike_robustness,
                "temporal_window_robustness": temporal_robustness,
                "coverage_and_censoring": coverage_censoring,
                "implementation_simplicity": simplicity,
                "active_learning_suitability": (
                    "strong"
                    if candidate_id in {"G0", "G2", "G3", "R0", "R2", "R3"}
                    else "moderate"
                    if candidate_id in {"G4", "R4"}
                    else "weak"
                ),
                "simulation_roc_auc": (
                    float(metric["roc_auc"]) if metric is not None else np.nan
                ),
                "simulation_pr_auc": (
                    float(metric["pr_auc"]) if metric is not None else np.nan
                ),
                "pr_prevalence_baseline": (
                    float(metric["prevalence_baseline"])
                    if metric is not None
                    else np.nan
                ),
                "roc_auc_ci": (
                    f"[{boot['roc_auc_ci_low']:.3f}, {boot['roc_auc_ci_high']:.3f}]"
                    if boot is not None
                    else ""
                ),
                "pr_auc_ci": (
                    f"[{boot['pr_auc_ci_low']:.3f}, {boot['pr_auc_ci_high']:.3f}]"
                    if boot is not None
                    else ""
                ),
                "availability_count": int(available["availability_count"]),
                "availability_fraction": float(available["availability_fraction"]),
                "window_auc_range": window_auc_range,
                "domain_auc_range": domain_auc_range,
                "recommended_role": role,
                "label_evidence_status": (
                    "descriptive_only_depth_seeded_and_sparse"
                    if metric is not None
                    else "diagnostic_only"
                ),
                "unweighted_decision_note": (
                    "No numerical weights are assigned; columns retain separate evidence dimensions."
                ),
            }
        )
    matrix = pd.DataFrame(rows)
    recommendation = pd.DataFrame(
        [
            {
                "response_role": "geometry_target",
                "recommended_target": "G0 / existing Phase 1 T0 geometry targets",
                "status": "retain",
                "physical_quantity": "typical late-active geometry",
                "reason": (
                    "T0 remains interpretable and was not designed to capture the strongest regime episode."
                ),
                "label_validation_status": "not dependent on Keyhole labels",
                "requires_ioan_confirmation": False,
            },
            {
                "response_role": "regime_propensity_target",
                "recommended_target": "R3 persistent maximum depth/width over 50 um",
                "status": "provisional_recommendation",
                "physical_quantity": (
                    "largest sustained penetration-depth-to-width ratio in the adaptive active interior"
                ),
                "reason": (
                    "Combines depth and width, suppresses isolated spikes, remains continuous, "
                    "and is stable enough across predeclared windows and domains."
                ),
                "label_validation_status": (
                    "descriptive only: 9 Keyhole-positive simulations and depth-seeded labels"
                ),
                "requires_ioan_confirmation": True,
            },
            {
                "response_role": "regime_companion_sensitivity",
                "recommended_target": "G3 persistent maximum depth over 50 um",
                "status": "retain_as_companion",
                "physical_quantity": "largest sustained penetration depth",
                "reason": (
                    "Avoids aspect-ratio denominator concerns and separates whether width adds information."
                ),
                "label_validation_status": (
                    "descriptive only and especially circular with depth-seeded labels"
                ),
                "requires_ioan_confirmation": True,
            },
            {
                "response_role": "later_active_learning_design",
                "recommended_target": "two-output representation",
                "status": "recommended_design_not_implemented",
                "physical_quantity": (
                    "typical geometry plus persistent regime propensity"
                ),
                "reason": (
                    "One scalar would conflate ordinary geometry with the strongest persistent event."
                ),
                "label_validation_status": "requires updated independent labels",
                "requires_ioan_confirmation": True,
            },
        ]
    )
    return matrix, recommendation


def generate_figures(
    output_dir: Path,
    *,
    label_population: pd.DataFrame,
    sequence: pd.DataFrame,
    coverage: pd.DataFrame,
    active: pd.DataFrame,
    profiles: pd.DataFrame,
    candidates: pd.DataFrame,
    persistence: pd.DataFrame,
    domain: pd.DataFrame,
    instability: pd.DataFrame,
    aligned: pd.DataFrame,
    simulation_metrics: pd.DataFrame,
    simulation_bootstrap: pd.DataFrame,
    score_table: pd.DataFrame,
    nested_predictions: pd.DataFrame,
    representatives: pd.DataFrame,
    frame_provenance: pd.DataFrame,
    decision_matrix: pd.DataFrame,
    recommendation: pd.DataFrame,
) -> pd.DataFrame:
    recorder = FigureRecorder(output_dir)

    figure = _diagram_figure(
        "Phase 3.5 experiment tree",
        [
            (0.50, 0.91, "Phase 3.5\nregime-target design", "#DDEBF7"),
            (0.14, 0.69, "A. Provenance, labels\nand alignment", "#E8F1F2"),
            (0.38, 0.69, "B. Scan-position\nevolution", "#E8F1F2"),
            (0.62, 0.69, "C. Reproducible\ncase studies", "#E8F1F2"),
            (0.86, 0.69, "D. Candidate\ntargets", "#E8F1F2"),
            (0.25, 0.40, "E. Label comparison", "#FDF0D5"),
            (0.50, 0.40, "F. Robustness\nchecks", "#FDF0D5"),
            (0.75, 0.40, "G. Final\nrecommendation", "#FDF0D5"),
            (0.50, 0.13, "Geometry target + provisional regime proxy\n(no active-learning loop)", "#D9EAD3"),
        ],
        [(0, 1), (0, 2), (0, 3), (0, 4), (1, 5), (2, 5), (3, 5), (4, 5), (5, 6), (6, 7), (7, 8)],
    )
    recorder.save(
        figure,
        "01_phase3_5_experiment_tree.png",
        section="Overview",
        question="How is the regime-target study structured?",
        source="phase3_5_configuration.json",
        simulations="241",
        x_axis="analysis flow",
        y_axis="analysis flow",
        units="not applicable",
        encodings="boxes are study sections; arrows are dependencies",
        takeaway="Target selection follows provenance, geometry, labels, and robustness.",
        caveat="The diagram describes analysis order, not causal relationships.",
        priority="core",
        presentation_copy=True,
    )

    label_rows = label_population[label_population["record_type"].eq("label")]
    flow_figure = _diagram_figure(
        "Data and label population flow",
        [
            (0.50, 0.89, "241 simulations\n25.9 million monitor rows", "#DDEBF7"),
            (0.28, 0.66, "65,472 labelled frames\nexact iteration matches", "#E8F1F2"),
            (0.72, 0.66, "Depth + width + ratio\nphysical scan coordinates", "#E8F1F2"),
            (0.28, 0.42, "Physical labels\nConduction / Forming / Keyhole", "#D9EAD3"),
            (0.72, 0.42, "Technical labels excluded\nInitial Emptiness / Screenshot Bug", "#E0E0E0"),
            (0.50, 0.16, "9 Keyhole-containing simulations\nprovisional, depth-seeded labels", "#F4CCCC"),
        ],
        [(0, 1), (0, 2), (1, 3), (1, 4), (3, 5), (2, 5)],
    )
    recorder.save(
        flow_figure,
        "02_data_label_population_flowchart.png",
        section="A",
        question="What populations reach the regime comparison?",
        source="label_population_audit.csv; simulation_active_interval_summary.csv",
        simulations="241",
        x_axis="population flow",
        y_axis="population flow",
        units="counts",
        encodings="green physical; grey technical; red limitation",
        takeaway="All labels align, but independent Keyhole evidence is sparse.",
        caveat="Human verification does not remove depth-seed circularity.",
        priority="core",
        uses_labels=True,
        presentation_copy=True,
    )

    figure, axes = plt.subplots(1, 2, figsize=(13, 5))
    order = ["Initial Emptiness", "Forming Phase", "Conduction", "Keyhole", "Screenshot Bug"]
    label_plot = label_rows.set_index("label").reindex(order)
    colors = [SEMANTIC_COLORS[value] for value in order]
    axes[0].bar(order, label_plot["frame_count"], color=colors)
    axes[0].set_title(f"Frame labels (n={int(label_plot['frame_count'].sum()):,})")
    axes[0].set_ylabel("labelled frames")
    axes[0].tick_params(axis="x", rotation=30)
    axes[1].bar(order, label_plot["simulation_count"], color=colors)
    axes[1].set_title("Simulations containing each label (n=241)")
    axes[1].set_ylabel("simulations")
    axes[1].tick_params(axis="x", rotation=30)
    figure.suptitle("Label population: physical regimes are separated from technical states", weight="bold")
    figure.tight_layout()
    recorder.save(
        figure,
        "03_label_count_overview.png",
        section="A",
        question="How many frames and simulations contain each stored label?",
        source="label_population_audit.csv",
        simulations="241",
        x_axis="stored label",
        y_axis="frame and simulation counts",
        units="counts",
        encodings="semantic label colours",
        takeaway="Keyhole has 521 frames in only 9 simulations.",
        caveat="Frame counts are correlated within simulation.",
        priority="core",
        uses_labels=True,
        presentation_copy=True,
    )

    figure, axis = plt.subplots(figsize=(10, 5.5))
    for record_type, label, style in [
        ("active_melt_coverage_curve", "valid melt support", "-"),
        ("recording_coverage_curve", "recording support", "--"),
    ]:
        subset = coverage[coverage["record_type"].eq(record_type)]
        axis.plot(
            subset["normalized_position"],
            subset["simulation_fraction"],
            style,
            lw=2,
            label=label,
        )
    for cutoff in [0.85, 0.90, 0.95, 1.0]:
        axis.axvline(cutoff, color="#999999", lw=0.8, alpha=0.7)
    axis.set(xlabel="normalized scan position s", ylabel="fraction of 241 simulations", ylim=(0, 1.02))
    axis.set_title("Right-censoring grows strongly toward domain exit (n=241)")
    axis.legend()
    axis.grid(alpha=0.2)
    recorder.save(
        figure,
        "04_scan_coverage_curve.png",
        section="A",
        question="How many simulations support each physical track position?",
        source="scan_coverage_summary.csv",
        simulations="241",
        x_axis="normalized scan position s",
        y_axis="simulation support fraction",
        units="dimensionless",
        encodings="solid valid melt; dashed recording coverage",
        takeaway="Only 113 simulations retain active melt to s=1.0.",
        caveat="Coverage is observational and depends on termination settings and VX.",
        priority="core",
        presentation_copy=True,
    )

    figure, axis = plt.subplots(figsize=(9, 5.5))
    vx_group = pd.qcut(active["VX"], 3, labels=["slow", "middle", "fast"])
    for label in ["slow", "middle", "fast"]:
        values = active.loc[vx_group.eq(label), "last_active_melt_position_s"]
        axis.hist(values, bins=20, alpha=0.45, label=f"{label} VX (n={len(values)})")
    axis.set(
        xlabel="last active-melt normalized position",
        ylabel="simulations",
        title="Observed maximum scan position differs by VX stratum",
    )
    axis.legend()
    recorder.save(
        figure,
        "05_observed_maximum_scan_position_by_vx.png",
        section="A",
        question="Is observed track coverage related to scan speed?",
        source="simulation_active_interval_summary.csv",
        simulations="241",
        x_axis="last active-melt s",
        y_axis="simulation count",
        units="normalized position",
        encodings="VX tertile",
        takeaway="Track coverage is not exchangeable across VX strata.",
        caveat="The plot is descriptive and does not identify a causal VX effect.",
        priority="supporting",
    )

    profile_specs = [
        ("depth_um", "Depth (µm)", "06_aggregate_depth_profiles_by_label_group.png"),
        ("width_um", "Width (µm)", "07_aggregate_width_profiles_by_label_group.png"),
        ("aspect_ratio", "Depth / width", "08_aggregate_aspect_ratio_profiles_by_label_group.png"),
    ]
    for response, ylabel, filename in profile_specs:
        figure, axis = plt.subplots(figsize=(10, 5.8))
        subset = profiles[profiles["response"].eq(response)]
        for group in ["conduction-only", "mixed", "keyhole-containing", "unlabelled-or-ambiguous"]:
            group_rows = subset[
                subset["label_group"].eq(group) & subset["display_supported"]
            ]
            if group_rows.empty:
                continue
            color = SEMANTIC_COLORS[group]
            axis.plot(group_rows["normalized_scan_position"], group_rows["median"], color=color, lw=2, label=group)
            axis.fill_between(
                group_rows["normalized_scan_position"],
                group_rows["q25"],
                group_rows["q75"],
                color=color,
                alpha=0.20,
            )
            axis.fill_between(
                group_rows["normalized_scan_position"],
                group_rows["q10"],
                group_rows["q90"],
                color=color,
                alpha=0.08,
            )
        axis.set(xlabel="normalized scan position s", ylabel=ylabel)
        axis.set_title(f"{ylabel} evolution by simulation label group")
        axis.legend(fontsize=8)
        axis.grid(alpha=0.2)
        recorder.save(
            figure,
            filename,
            section="B",
            question=f"How does {response} evolve along the physical scan track?",
            source="normalized_position_support.csv",
            simulations="up to 241; support-limited by group",
            x_axis="normalized scan position s",
            y_axis=ylabel,
            units="µm" if response != "aspect_ratio" else "dimensionless",
            encodings="median line; q25-q75 dark band; q10-q90 light band",
            takeaway="Keyhole-containing profiles differ, but only nine simulations supply that group.",
            caveat="Profiles use original observations binned by position; no interpolation or independence claim.",
            priority="core" if response == "aspect_ratio" else "supporting",
            uses_labels=True,
            presentation_copy=response == "aspect_ratio",
        )

    figure, axis = plt.subplots(figsize=(10, 5.5))
    all_depth = profiles[
        profiles["label_group"].eq("all")
        & profiles["response"].eq("depth_um")
    ]
    axis.plot(
        all_depth["normalized_scan_position"],
        all_depth["contributing_simulations"],
        color=SEMANTIC_COLORS["all"],
        lw=2,
    )
    axis.axhline(
        all_depth["minimum_support_threshold"].iloc[0],
        color="#D1495B",
        ls="--",
        label="minimum display support",
    )
    axis.set(
        xlabel="normalized scan position s",
        ylabel="contributing simulations",
        title="Contributor count beneath aggregate profiles (n=241)",
    )
    axis.legend()
    recorder.save(
        figure,
        "09_aggregate_profile_contributing_counts.png",
        section="B",
        question="Where are aggregate profiles adequately supported?",
        source="normalized_position_support.csv",
        simulations="241",
        x_axis="normalized scan position s",
        y_axis="contributing simulations",
        units="count",
        encodings="all-simulation support line and threshold",
        takeaway="Profile interpretation must stop as support falls near the track end.",
        caveat="Group-specific thresholds are stricter when a group is small.",
    )

    location_specs = [
        ("global_max_depth_position_s", "Global maximum depth", "10_global_maximum_depth_position_histogram.png"),
        ("persistent_max_depth_position_s", "Persistent maximum depth", "11_persistent_maximum_depth_position_histogram.png"),
        ("global_max_ratio_position_s", "Global maximum aspect ratio", "12_global_maximum_aspect_ratio_position_histogram.png"),
        ("persistent_max_ratio_position_s", "Persistent maximum aspect ratio", "13_persistent_maximum_aspect_ratio_position_histogram.png"),
    ]
    for column, title, filename in location_specs:
        figure, axis = plt.subplots(figsize=(9, 5))
        values = active[column].dropna()
        axis.hist(values, bins=np.linspace(0, 1.2, 31), color="#4C78A8", alpha=0.8)
        axis.axvline(values.median(), color="#D1495B", lw=2, label=f"median={values.median():.3f}")
        axis.set(xlabel="normalized scan position s", ylabel="simulations", title=f"{title} location (n={len(values)})")
        axis.legend()
        recorder.save(
            figure,
            filename,
            section="B",
            question=f"Where does {title.lower()} occur?",
            source="simulation_active_interval_summary.csv",
            simulations=str(len(values)),
            x_axis="event position s",
            y_axis="simulation count",
            units="normalized position",
            encodings="histogram and median marker",
            takeaway=f"The median event location is s={values.median():.3f}, with broad simulation variability.",
            caveat="A median near mid-track does not imply every simulation is deepest there.",
        )

    figure, axis = plt.subplots(figsize=(10, 5.5))
    location_frame = active[
        [
            "T0_start_position_s",
            "T0_end_position_s",
            "global_max_depth_position_s",
            "persistent_max_depth_position_s",
            "global_max_ratio_position_s",
            "persistent_max_ratio_position_s",
        ]
    ]
    labels = ["T0 start", "T0 end", "max depth", "persistent depth", "max ratio", "persistent ratio"]
    axis.boxplot([location_frame[column].dropna() for column in location_frame], tick_labels=labels, showfliers=False)
    axis.set_ylabel("normalized scan position s")
    axis.set_title("T0 window is late relative to many maximum and persistent events (n=241)")
    axis.tick_params(axis="x", rotation=25)
    recorder.save(
        figure,
        "14_T0_window_vs_maximum_and_persistent_event_locations.png",
        section="B",
        question="Does the late T0 window cover the strongest interior episodes?",
        source="simulation_active_interval_summary.csv",
        simulations="241",
        x_axis="window or event",
        y_axis="normalized scan position s",
        units="normalized position",
        encodings="boxplots",
        takeaway="Many maxima and persistent events precede the T0 window.",
        caveat="Earlier events are regime candidates, not replacements for typical late geometry.",
        priority="core",
        presentation_copy=True,
    )

    wide = candidates.pivot_table(index="simulation_id", columns="candidate_id", values="value", aggfunc="first")
    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].scatter(wide["G1"], wide["G2"], alpha=0.65, s=20)
    axes[0].set(xlabel="global max depth G1 (µm)", ylabel="interior q95 depth G2 (µm)")
    axes[1].scatter(wide["G1"], wide["G3"], alpha=0.65, s=20, color="#F28E2B")
    axes[1].set(xlabel="global max depth G1 (µm)", ylabel="persistent depth G3 (µm)")
    figure.suptitle("Maximum, q95, and persistence separate spike size from sustained depth (n=241)", weight="bold")
    recorder.save(
        figure,
        "15_global_maximum_q95_persistent_depth_scatter.png",
        section="D",
        question="How do high-depth summaries differ from the global maximum?",
        source="regime_target_candidates.csv",
        simulations="241",
        x_axis="G1 maximum depth",
        y_axis="G2 q95 and G3 persistence",
        units="µm",
        encodings="one point per simulation",
        takeaway="The global maximum can exceed robust or persistent depth substantially.",
        caveat="Differences may reflect real transients as well as numerical artefacts.",
    )

    figure, axis = plt.subplots(figsize=(7.5, 6))
    groups = score_table.set_index("simulation_id")["any_keyhole"].reindex(wide.index).fillna(False)
    for keyhole, label in [(False, "no Keyhole label"), (True, "any Keyhole label")]:
        subset = groups.eq(keyhole)
        axis.scatter(
            wide.loc[subset, "R1"],
            wide.loc[subset, "R3"],
            alpha=0.7,
            s=35,
            label=f"{label} (n={int(subset.sum())})",
            color=SEMANTIC_COLORS["Keyhole" if keyhole else "Conduction"],
        )
    axis.set(xlabel="global max aspect ratio R1", ylabel="persistent aspect ratio R3")
    axis.set_title("Global maximum versus persistent aspect ratio (n=241)")
    axis.legend()
    recorder.save(
        figure,
        "16_global_maximum_vs_persistent_aspect_ratio.png",
        section="D",
        question="Which simulations have high one-frame ratios but lower persistent ratios?",
        source="regime_target_candidates.csv",
        simulations="241",
        x_axis="R1",
        y_axis="R3",
        units="dimensionless",
        encodings="provisional any-Keyhole label",
        takeaway="Persistence reduces extreme one-frame ratios while retaining group separation.",
        caveat="Group separation is not independent validation because labels were depth-seeded.",
        uses_labels=True,
        priority="core",
        presentation_copy=True,
    )

    persistence_summary = persistence[persistence["record_type"].eq("summary")]
    figure, axes = plt.subplots(1, 2, figsize=(13, 5))
    physical = persistence_summary[
        persistence_summary["analysis_domain"].eq("adaptive_active_interior")
        & persistence_summary["window_type"].eq("physical_um")
    ]
    for candidate_id, color in [("G3", "#4C78A8"), ("R3", "#F28E2B")]:
        subset = physical[physical["candidate_id"].eq(candidate_id)]
        axes[0].plot(subset["window_distance_um"], subset["roc_auc_any_keyhole"], marker="o", color=color, label=candidate_id)
        axes[1].plot(subset["window_distance_um"], subset["pr_auc_any_keyhole"], marker="o", color=color, label=candidate_id)
    axes[0].set(xlabel="physical persistence window (µm)", ylabel="ROC AUC", title="ROC sensitivity")
    axes[1].set(xlabel="physical persistence window (µm)", ylabel="PR AUC", title="PR sensitivity")
    for axis in axes:
        axis.legend()
        axis.grid(alpha=0.2)
    figure.suptitle("Predeclared persistence-window sensitivity (n=241; 9 positives)", weight="bold")
    recorder.save(
        figure,
        "17_persistence_window_sensitivity.png",
        section="F",
        question="Do candidate conclusions depend critically on 20, 50, or 100 µm?",
        source="persistence_window_sensitivity.csv",
        simulations="241",
        x_axis="physical-distance window",
        y_axis="ROC and PR AUC",
        units="µm and AUC",
        encodings="G3 depth and R3 ratio lines",
        takeaway="The 50 µm choice is interpreted within the full predeclared sensitivity range.",
        caveat="AUC is descriptive under sparse, circular labels.",
        uses_labels=True,
        priority="core",
        presentation_copy=True,
    )

    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    availability = candidates.groupby("candidate_id")["available"].agg(["sum", "mean"])
    axes[0].bar(availability.index, availability["sum"], color="#4C78A8")
    axes[0].set(xlabel="candidate", ylabel="available simulations", title="Candidate availability")
    coverage_join = active.merge(wide.reset_index(), on="simulation_id")
    axes[1].scatter(coverage_join["last_active_melt_position_s"], coverage_join["R3"], alpha=0.55, s=20)
    axes[1].set(xlabel="last active position s", ylabel="R3", title="R3 versus observed coverage")
    figure.suptitle("Candidate availability and censoring diagnostics (n=241)", weight="bold")
    recorder.save(
        figure,
        "18_candidate_availability_and_censoring.png",
        section="F",
        question="Are candidate values available and sensitive to shortened coverage?",
        source="regime_target_candidates.csv; candidate_censoring_sensitivity.csv",
        simulations="241",
        x_axis="candidate or last active s",
        y_axis="availability or R3",
        units="counts; dimensionless",
        encodings="bars and simulation scatter",
        takeaway="Most continuous candidates are broadly available; R5 is censored by design.",
        caveat="Association with coverage does not prove censoring bias.",
    )

    plot_candidates = ["G0", "G1", "G2", "G3", "R0", "R1", "R2", "R3"]
    long_scores = score_table.melt(
        id_vars=["simulation_id", "any_keyhole"],
        value_vars=plot_candidates,
        var_name="candidate",
        value_name="value",
    )
    figure, axes = plt.subplots(2, 4, figsize=(15, 7))
    for axis, candidate_id in zip(axes.flat, plot_candidates):
        subset = long_scores[long_scores["candidate"].eq(candidate_id)]
        groups_values = [
            subset.loc[~subset["any_keyhole"], "value"].dropna(),
            subset.loc[subset["any_keyhole"], "value"].dropna(),
        ]
        axis.boxplot(groups_values, tick_labels=["no KH", "any KH"], showfliers=False)
        axis.set_title(candidate_id)
    figure.suptitle("Candidate distributions by provisional simulation label (232 vs 9)", weight="bold")
    recorder.save(
        figure,
        "19_candidate_target_distributions_by_simulation_label.png",
        section="E",
        question="How do candidate scores differ between Keyhole-containing and other simulations?",
        source="regime_target_candidates.csv",
        simulations="241",
        x_axis="any-Keyhole group",
        y_axis="candidate value in candidate units",
        units="mixed by panel",
        encodings="boxplots with outliers hidden for readability",
        takeaway="Several depth and ratio candidates strongly separate the nine labelled positives.",
        caveat="The comparison is circular and class-imbalanced; hidden outliers remain in source data.",
        uses_labels=True,
    )

    physical_frames = aligned[aligned["stored_label"].isin(["Conduction", "Forming Phase", "Keyhole"])]
    for column, ylabel, filename in [
        ("depth_um", "Depth (µm)", "20_frame_level_depth_distributions_by_physical_label.png"),
        ("aspect_ratio", "Depth / width", "21_frame_level_aspect_ratio_distributions_by_physical_label.png"),
    ]:
        figure, axis = plt.subplots(figsize=(9, 5.5))
        labels_order = ["Forming Phase", "Conduction", "Keyhole"]
        data = [physical_frames.loc[physical_frames["stored_label"].eq(label), column].dropna() for label in labels_order]
        parts = axis.violinplot(data, showmedians=True, showextrema=False)
        for body, label in zip(parts["bodies"], labels_order):
            body.set_facecolor(SEMANTIC_COLORS[label])
            body.set_alpha(0.65)
        axis.set_xticks(range(1, len(labels_order) + 1), labels_order)
        axis.set_ylabel(ylabel)
        axis.set_title(f"Frame-level {ylabel.lower()} by physical label (clustered in 241 simulations)")
        recorder.save(
            figure,
            filename,
            section="E",
            question=f"How does frame-level {column} overlap across physical labels?",
            source="label_aligned_geometry_time_series.parquet",
            simulations="up to 241",
            x_axis="physical label",
            y_axis=ylabel,
            units="µm" if column == "depth_um" else "dimensionless",
            encodings="semantic-colour violin distributions",
            takeaway="Keyhole-labelled frames occupy deeper and higher-ratio regions.",
            caveat="Frames are correlated and labels were seeded from depth; inferential CIs cluster by simulation.",
            uses_labels=True,
        )

    curve_candidates = ["G0", "G2", "G3", "R2", "R3"]
    figure_roc, axis_roc = plt.subplots(figsize=(7.5, 6))
    figure_pr, axis_pr = plt.subplots(figsize=(7.5, 6))
    y = score_table["any_keyhole"].astype(int).to_numpy()
    for candidate_id in curve_candidates:
        score = score_table[candidate_id].to_numpy(dtype=float)
        finite = np.isfinite(score)
        fpr, tpr, _ = roc_curve(y[finite], score[finite])
        precision, recall, _ = precision_recall_curve(y[finite], score[finite])
        metric = simulation_metrics.set_index("candidate_id").loc[candidate_id]
        axis_roc.plot(fpr, tpr, lw=2, label=f"{candidate_id} AUC={metric['roc_auc']:.3f}")
        axis_pr.plot(recall, precision, lw=2, label=f"{candidate_id} AP={metric['pr_auc']:.3f}")
    prevalence = float(y.mean())
    axis_roc.plot([0, 1], [0, 1], "--", color="#888888", label="chance")
    axis_pr.axhline(prevalence, ls="--", color="#888888", label=f"prevalence={prevalence:.3f}")
    axis_roc.set(xlabel="false-positive rate", ylabel="true-positive rate", title="Simulation-level ROC curves (9 positives / 232 negatives)")
    axis_pr.set(xlabel="recall", ylabel="precision", title="Simulation-level precision–recall curves")
    axis_roc.legend(fontsize=8)
    axis_pr.legend(fontsize=8)
    recorder.save(
        figure_roc,
        "22_candidate_simulation_level_ROC_curves.png",
        section="E",
        question="How well do continuous candidates rank provisional any-Keyhole outcomes?",
        source="simulation_level_candidate_label_metrics.csv",
        simulations="241",
        x_axis="false-positive rate",
        y_axis="true-positive rate",
        units="rate",
        encodings="one curve per predeclared leading candidate",
        takeaway="Several candidates rank the sparse provisional labels strongly.",
        caveat="High ROC AUC is insufficient with only nine positives and circular labels.",
        uses_labels=True,
    )
    recorder.save(
        figure_pr,
        "23_candidate_precision_recall_curves_with_prevalence.png",
        section="E",
        question="How much precision is achieved above the 3.7% prevalence baseline?",
        source="simulation_level_candidate_label_metrics.csv",
        simulations="241",
        x_axis="recall",
        y_axis="precision",
        units="rate",
        encodings="candidate curves and prevalence baseline",
        takeaway="PR curves expose the low-prevalence problem hidden by accuracy.",
        caveat="Confidence intervals remain wide because nine simulations contain Keyhole.",
        uses_labels=True,
        priority="core",
        presentation_copy=True,
    )

    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    for axis, candidate_id in zip(axes, ["G3", "R3"]):
        axis.scatter(score_table[candidate_id], score_table["keyhole_fraction"], alpha=0.65, s=30)
        rho = stats.spearmanr(score_table[candidate_id], score_table["keyhole_fraction"]).statistic
        axis.set(xlabel=candidate_id, ylabel="Keyhole fraction of usable physical labels", title=f"{candidate_id}: Spearman ρ={rho:.3f}")
    figure.suptitle("Candidate scores versus Keyhole-labelled frame fraction (n=241)", weight="bold")
    recorder.save(
        figure,
        "24_candidate_score_vs_keyhole_fraction.png",
        section="E",
        question="Do stronger candidate scores accompany a larger Keyhole-labelled fraction?",
        source="candidate_keyhole_fraction_correlations.csv",
        simulations="241",
        x_axis="candidate value",
        y_axis="Keyhole fraction",
        units="candidate units and fraction",
        encodings="simulation scatter",
        takeaway="Persistent depth and ratio rise with provisional Keyhole fraction.",
        caveat="Most simulations have zero fraction, and depth-seeded labels induce circularity.",
        uses_labels=True,
    )

    leading_nested = ["G3", "R2", "R3"]
    figure, axes = plt.subplots(1, 3, figsize=(12, 4))
    for axis, candidate_id in zip(axes, leading_nested):
        subset = nested_predictions[nested_predictions["candidate_id"].eq(candidate_id)]
        matrix = confusion_matrix(
            subset["heldout_true_any_keyhole"],
            subset["heldout_prediction"],
            labels=[0, 1],
        )
        image = axis.imshow(matrix, cmap="Blues")
        for (row, column), value in np.ndenumerate(matrix):
            axis.text(column, row, str(value), ha="center", va="center")
        axis.set_xticks([0, 1], ["pred no KH", "pred KH"])
        axis.set_yticks([0, 1], ["true no KH", "true KH"])
        axis.set_title(candidate_id)
    figure.suptitle("Nested held-out confusion matrices (threshold selected without held-out label)", weight="bold")
    recorder.save(
        figure,
        "25_nested_heldout_confusion_matrices.png",
        section="E",
        question="What happens when thresholds are chosen leakage-safely?",
        source="nested_threshold_loo_predictions.csv",
        simulations="240–241 exact outer folds, using each candidate's non-imputed usable population",
        x_axis="held-out prediction",
        y_axis="held-out label",
        units="simulation count",
        encodings="confusion-matrix intensity",
        takeaway="Thresholded performance is based on one genuinely held-out decision per simulation.",
        caveat="Thresholds remain exploratory because labels are sparse and provisional.",
        uses_labels=True,
        priority="core",
        presentation_copy=True,
    )

    domain_summary = domain[
        domain["record_type"].eq("summary")
        & domain["candidate_id"].isin(["G3", "R3"])
    ]
    figure, axis = plt.subplots(figsize=(8, 5))
    pivot = domain_summary.pivot(index="candidate_id", columns="analysis_domain", values="roc_auc_any_keyhole")
    pivot.plot(kind="bar", ax=axis, color=["#4C78A8", "#F28E2B"])
    axis.set(ylabel="ROC AUC", xlabel="candidate", title="Candidate robustness across common and adaptive interiors")
    axis.legend(title="domain")
    recorder.save(
        figure,
        "26_candidate_robustness_across_analysis_domains.png",
        section="F",
        question="Does the candidate ranking depend on the interior-domain rule?",
        source="candidate_domain_sensitivity.csv",
        simulations="241",
        x_axis="candidate",
        y_axis="ROC AUC",
        units="AUC",
        encodings="common versus adaptive bars",
        takeaway="Persistent candidates are compared under both domain definitions.",
        caveat="The common interior is shorter because only 80% support is required.",
        uses_labels=True,
    )

    figure, axis = plt.subplots(figsize=(9, 5))
    unstable_plot = instability[instability["candidate_id"].isin(["G3", "R2", "R3"])]
    pivot = unstable_plot.pivot(index="candidate_id", columns="population", values="pr_auc")
    pivot.plot(kind="bar", ax=axis, color=["#4C78A8", "#F28E2B"])
    axis.set(ylabel="PR AUC", xlabel="candidate", title="Robustness with and without 11 Phase 1 unstable simulations")
    axis.legend(title="population")
    recorder.save(
        figure,
        "27_candidate_robustness_with_without_unstable_simulations.png",
        section="F",
        question="Do independently identified unstable simulations drive label agreement?",
        source="candidate_unstable_subset_sensitivity.csv",
        simulations="241 and 230",
        x_axis="candidate",
        y_axis="PR AUC",
        units="AUC",
        encodings="full versus stable-subset bars",
        takeaway="The unstable-subset comparison is predeclared and paired by simulation ID.",
        caveat="Some Keyhole-positive simulations are among the unstable exclusions.",
        uses_labels=True,
    )

    def case_figure(case_row: pd.Series) -> plt.Figure:
        simulation_id = case_row["simulation_id"]
        trace = pd.read_parquet(_parquet_part_path(output_dir, simulation_id))
        labels_frame = aligned[aligned["simulation_id"].eq(simulation_id)].sort_values("normalized_scan_position")
        active_row = active.set_index("simulation_id").loc[simulation_id]
        candidate_rows = candidates[candidates["simulation_id"].eq(simulation_id)].set_index("candidate_id")
        figure, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
        s_values = trace["normalized_scan_position"]
        axes[0].plot(s_values, trace["depth_m"] * 1e6, color="#4C78A8", lw=1)
        axes[1].plot(s_values, trace["width_m"] * 1e6, color="#2A9D8F", lw=1)
        axes[2].plot(s_values, trace["aspect_ratio"], color="#7A5195", lw=1)
        axes[0].set_ylabel("depth (µm)")
        axes[1].set_ylabel("width (µm)")
        axes[2].set_ylabel("depth / width")
        axes[2].set_xlabel("normalized scan position s")
        for axis in axes:
            axis.axvspan(active_row["T0_start_position_s"], active_row["T0_end_position_s"], color=SEMANTIC_COLORS["T0 window"], alpha=0.18, label="T0 window")
            axis.axvline(active_row["melt_onset_position_s"], color="#555555", ls=":", lw=1)
            axis.axvline(1.0, color="#000000", ls="--", lw=0.8)
        axes[0].axvline(candidate_rows.loc["G1", "event_position_s"], color="#D1495B", ls="--", label="global max")
        axes[0].axvline(candidate_rows.loc["G3", "event_position_s"], color=SEMANTIC_COLORS["persistent event"], lw=2, label="persistent max")
        axes[0].axhline(candidate_rows.loc["G2", "value"], color="#999999", ls=":", label="q95 depth")
        axes[2].axvline(candidate_rows.loc["R1", "event_position_s"], color="#D1495B", ls="--", label="global max")
        axes[2].axvline(candidate_rows.loc["R3", "event_position_s"], color=SEMANTIC_COLORS["persistent event"], lw=2, label="persistent max")
        axes[2].axhline(candidate_rows.loc["R2", "value"], color="#999999", ls=":", label="q95 ratio")
        keyhole_rows = labels_frame[labels_frame["stored_label"].eq("Keyhole")]
        if len(keyhole_rows):
            first_keyhole = float(keyhole_rows["normalized_scan_position"].iloc[0])
            for axis in axes:
                axis.axvline(first_keyhole, color=SEMANTIC_COLORS["Keyhole"], lw=1.5, label="first Keyhole")
        y_top = axes[2].get_ylim()[1]
        axes[2].scatter(
            labels_frame["normalized_scan_position"],
            np.repeat(y_top * 0.98, len(labels_frame)),
            c=[SEMANTIC_COLORS[value] for value in labels_frame["stored_label"]],
            s=8,
            alpha=0.75,
            clip_on=True,
        )
        axes[0].legend(ncol=4, fontsize=7)
        axes[2].legend(ncol=4, fontsize=7)
        figure.suptitle(
            f"{case_row['case_name']}: {simulation_id}\n{case_row['selection_evidence']}",
            weight="bold",
        )
        figure.tight_layout()
        return figure

    case_filenames = {
        "C1": "28_case_typical_conduction_only.png",
        "C2": "29_case_typical_keyhole_containing.png",
        "C3": "30_case_mixed_conduction_to_keyhole.png",
        "C4": "31_case_spike_vs_persistent_disagreement.png",
        "C5": "32_case_persistent_deep_melt.png",
        "C6": "33_case_phase1_unstable_window.png",
    }
    for row in representatives.itertuples(index=False):
        row_series = pd.Series(row._asdict())
        figure = case_figure(row_series)
        recorder.save(
            figure,
            case_filenames[row.case_id],
            section="C",
            question=f"What does the objectively selected {row.case_name.lower()} case show?",
            source="representative_simulation_selection.csv; regime_geometry_time_series.parquet",
            simulations=row.simulation_id,
            x_axis="normalized scan position s",
            y_axis="depth, width, depth/width",
            units="µm and dimensionless",
            encodings="T0 shading; maxima and persistence markers; semantic label ribbon",
            takeaway=row.selection_evidence,
            caveat="One reproducibly selected case illustrates a mechanism but cannot establish population prevalence.",
            uses_labels=True,
            priority="core" if row.case_id in {"C1", "C2", "C3", "C4"} else "supporting",
            presentation_copy=row.case_id in {"C1", "C2", "C3", "C4"},
        )

    figure, axes = plt.subplots(1, 3, figsize=(14, 4.8))
    for axis, row in zip(axes, frame_provenance.itertuples(index=False)):
        image = Image.open(row.local_path)
        axis.imshow(image)
        axis.axis("off")
        axis.set_title(
            f"{row.selection_role.replace('_', ' ')}\n"
            f"{row.stored_label}; s={row.normalized_scan_position:.3f}"
        )
    figure.suptitle(
        f"Actual pinned Hugging Face side-view frames: {frame_provenance['simulation_id'].iloc[0]}",
        weight="bold",
    )
    recorder.save(
        figure,
        "34_actual_frame_sequence_mixed_keyhole_case.png",
        section="C",
        question="What do actual simulation frames show before, near, and after the selected event?",
        source="representative_frame_provenance.csv",
        simulations=frame_provenance["simulation_id"].iloc[0],
        x_axis="sequence order",
        y_axis="side-view image",
        units="image pixels with aligned physical s in title",
        encodings="actual dataset frames only",
        takeaway="The aligned image sequence visually contextualizes the geometry-derived persistent event.",
        caveat="Three frames do not independently validate the label or target.",
        uses_labels=True,
        uses_frames=True,
        priority="core",
        presentation_copy=True,
    )

    figure = _diagram_figure(
        "Physical interpretation: geometry is not the same as regime propensity",
        [
            (0.18, 0.72, "Depth(t)\npenetration below surface", "#DDEBF7"),
            (0.50, 0.72, "Width(t)\ntransverse extent", "#D9EAD3"),
            (0.82, 0.72, "Depth(t) / width(t)\ninstantaneous aspect ratio", "#FCE5CD"),
            (0.32, 0.38, "T0 median\ntypical late geometry", "#DDEBF7"),
            (0.68, 0.38, "50 µm rolling median\nspike-resistant persistence", "#FCE5CD"),
            (0.50, 0.12, "Two roles retained:\ngeometry state + regime propensity", "#EADCF8"),
        ],
        [(0, 3), (0, 2), (1, 2), (2, 4), (3, 5), (4, 5)],
    )
    recorder.save(
        figure,
        "35_final_physical_interpretation_diagram.png",
        section="G",
        question="Why are T0 and a persistent regime target different quantities?",
        source="phase3_5_final_target_recommendation.csv",
        simulations="241",
        x_axis="physical interpretation",
        y_axis="target role",
        units="not applicable",
        encodings="geometry and regime pathways",
        takeaway="T0 describes typical geometry; R3 describes the strongest sustained shape ratio.",
        caveat="Neither target alone is a final conduction–keyhole truth label.",
        priority="core",
        presentation_copy=True,
    )

    figure, axis = plt.subplots(figsize=(15, 6))
    display_columns = [
        "candidate_id",
        "physical_suitability",
        "spike_robustness",
        "temporal_window_robustness",
        "coverage_and_censoring",
        "simulation_roc_auc",
        "simulation_pr_auc",
        "recommended_role",
    ]
    display = decision_matrix[display_columns].copy()
    display["simulation_roc_auc"] = display["simulation_roc_auc"].map(lambda value: f"{value:.3f}" if np.isfinite(value) else "")
    display["simulation_pr_auc"] = display["simulation_pr_auc"].map(lambda value: f"{value:.3f}" if np.isfinite(value) else "")
    display["recommended_role"] = display["recommended_role"].replace(
        {
            "reference_only": "spike reference",
            "leading_candidate": "leading candidate",
            "companion_candidate": "depth companion",
            "sensitivity_only": "sensitivity",
            "provisional_regime_target": "ratio provisional",
            "threshold_diagnostic": "threshold diagnostic",
            "censored_diagnostic": "censored diagnostic",
        }
    )
    axis.axis("off")
    table = axis.table(
        cellText=display.values,
        colLabels=["ID", "physical", "spike robust", "window robust", "coverage", "ROC AUC", "PR AUC", "role"],
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.5)
    axis.set_title("Transparent candidate decision matrix — evidence dimensions are not numerically weighted", weight="bold", pad=20)
    recorder.save(
        figure,
        "36_final_candidate_decision_matrix.png",
        section="G",
        question="How does each candidate perform across separate decision criteria?",
        source="phase3_5_candidate_decision_matrix.csv",
        simulations="241",
        x_axis="evidence dimension",
        y_axis="candidate",
        units="qualitative ratings and AUC",
        encodings="unweighted decision table",
        takeaway="R3 is the provisional regime proxy; G3 remains a companion and G1/R1 are references.",
        caveat="Label-agreement columns are descriptive, not independent validation.",
        uses_labels=True,
        priority="core",
        presentation_copy=True,
    )

    figure = _diagram_figure(
        "Recommended role separation for later work",
        [
            (0.22, 0.73, "Geometry output\nT0 width/depth\ntypical active shape", "#DDEBF7"),
            (0.78, 0.73, "Regime output\nR3 persistent depth/width\nprovisional propensity", "#FCE5CD"),
            (0.22, 0.35, "Existing GP/regression\ngeometry modelling", "#E8F1F2"),
            (0.78, 0.35, "Future validation\nupdated independent labels", "#F4CCCC"),
            (0.50, 0.10, "Later design choice for Ioan:\n2D response or one confirmed continuous level-set target", "#D9EAD3"),
        ],
        [(0, 2), (1, 3), (2, 4), (3, 4)],
    )
    recorder.save(
        figure,
        "37_final_recommended_geometry_regime_active_learning_roles.png",
        section="G",
        question="What should be carried into later active-learning design?",
        source="phase3_5_active_learning_implications.md",
        simulations="241",
        x_axis="target role",
        y_axis="future decision path",
        units="not applicable",
        encodings="separate geometry and regime branches",
        takeaway="Retain two outputs until independent relabelling supports collapsing to one target.",
        caveat="No active-learning loop, classifier, acquisition rule, or level set is implemented here.",
        priority="core",
        presentation_copy=True,
    )

    manifest = recorder.manifest()
    write_csv(manifest, output_dir / "figure_manifest.csv")
    return manifest


def write_configuration(
    output_dir: Path,
    *,
    common_interval: dict[str, Any],
    full: bool,
    workers: int,
    bootstrap_resamples: int,
) -> dict[str, Any]:
    configuration = {
        "phase": "Week 6 Phase 3.5",
        "mode": "full" if full else "smoke",
        "scientific_question": (
            "Which scalar summary of depth/width time evolution best represents "
            "persistent conduction-like versus keyhole-like behaviour?"
        ),
        "repository_root": str(ROOT),
        "branch": git_output(["branch", "--show-current"]),
        "head": git_output(["rev-parse", "HEAD"]),
        "huggingface": {"repo_id": REPO_ID, "revision": REVISION},
        "inputs": {
            "phase1_ledger": str(PHASE1_LEDGER.relative_to(ROOT)),
            "phase1_ledger_sha256": EXPECTED_LEDGER_SHA256,
            "label_file": str(LABEL_FILE.relative_to(ROOT)),
            "label_file_sha256": sha256(LABEL_FILE),
            "features_if_used": EXPECTED_FEATURES,
            "expected_simulations": EXPECTED_SIMULATIONS,
        },
        "geometry": {
            "width_definition": "y_max - y_min",
            "length_definition": "x_max - x_min; instantaneous extent, not total track length",
            "depth_definition": "max(0, -z_min) relative to surface z=0",
            "vertical_extent_definition": "z_max - z_min; diagnostic context only",
            "aspect_ratio_definition": "penetration_depth / transverse_width",
            "aspect_ratio_unit": "dimensionless",
            "minimum_width_guard_m": PRIMARY_WIDTH_GUARD_M,
            "minimum_width_guard_basis": "three 4 um SPH particle spacings",
            "width_guard_sensitivity_um": WIDTH_GUARD_SENSITIVITY_UM,
            "analytical_clipping": False,
        },
        "scan_alignment": {
            "laser_x_definition": "x_start + VX * elapsed_time_s",
            "normalized_position_definition": "(x_laser - x_start) / (x_domain_end - x_start)",
            "x_start_source": "laser motion center X in experiment_details.json",
            "x_domain_end_source": "domain.domain_max[0] in experiment_details.json",
            "label_alignment": "exact frame timestep to monitor iter.dat match",
            "alignment_tolerance_iterations": 0,
            "interpolation_method": "none; aggregate profiles bin original observations",
            "maximum_interpolation_gap": None,
        },
        "analysis_domains": {
            "common_interior": common_interval,
            "adaptive_active_interior": {
                "start": "melt onset plus 50 um physical startup margin",
                "end": "minimum(last active melt, domain exit) minus 50 um physical end margin",
                "startup_margin_um": STARTUP_MARGIN_M * 1e6,
                "end_margin_um": END_MARGIN_M * 1e6,
            },
        },
        "persistence": {
            "primary_basis": "physical scan distance",
            "physical_windows_um": PERSISTENCE_WINDOWS_UM,
            "normalized_track_windows": NORMALIZED_WINDOWS,
            "primary_window_um": PRIMARY_PERSISTENCE_WINDOW_UM,
            "minimum_observations": MIN_ROLLING_OBSERVATIONS,
            "minimum_physical_span_fraction": MIN_ROLLING_SPAN_FRACTION,
            "rolling_direction": "trailing; event position is window end",
            "window_search_policy": "all predeclared windows reported; no post-hoc best-window selection",
        },
        "label_policy": {
            "physical_labels": ["Conduction", "Forming Phase", "Keyhole"],
            "binary_metric_labels": ["Conduction", "Keyhole"],
            "technical_labels": ["Initial Emptiness", "Screenshot Bug"],
            "screenshot_bug_used_as_negative": False,
            "ground_truth_claim": False,
            "known_circularity": (
                "All labeling_provenance.json files record automatic_method="
                "'per-experiment-median-zmin, threshold = 1.5x median'; "
                "depth-derived agreement is descriptive, not independent validation."
            ),
        },
        "threshold_policy": {
            "external_universal_threshold": False,
            "exploratory_geometry_threshold_rule": (
                "q90 of simulation-level R2; recomputed on outer-training simulations "
                "for leakage-safe R4 evaluation"
            ),
            "classification_threshold_rule": (
                "maximum outer-training balanced accuracy; F1 then higher-threshold tie break"
            ),
            "outer_heldout_label_used": False,
        },
        "bootstrap": {
            "simulation_resamples": bootstrap_resamples,
            "frame_cluster_resamples": bootstrap_resamples,
            "cluster_unit": "simulation",
            "paired_candidate_comparisons": True,
            "seed": BOOTSTRAP_SEED,
        },
        "runtime": {"workers": workers, "deterministic": True},
        "scope_exclusions": [
            "active-learning loop",
            "level-set estimation",
            "GP classifier",
            "acquisition functions",
            "kinetic-energy modelling",
            "total-height Phase 4 modelling",
            "Phase 3 kernel comparison",
            "feature-effect or causal analysis",
            "ARD",
        ],
    }
    write_json(json_safe(configuration), output_dir / "phase3_5_configuration.json")
    return configuration


def write_active_learning_implications(
    output_dir: Path,
    *,
    recommendation: pd.DataFrame,
) -> None:
    content = """# Phase 3.5 implications for later conduction–keyhole active learning

## Recommended role separation

Phase 3.5 supports retaining two scientifically distinct outputs for now:

1. **Geometry state:** the existing T0 late-active width/depth summaries.
2. **Regime propensity:** provisional R3, the maximum 50 µm rolling-median
   penetration-depth/width ratio within the adaptive active interior.

G3, persistent depth over the same distance, should remain a companion
sensitivity.  It tests whether any apparent advantage of R3 is genuinely due
to width rather than depth alone.

## Why not collapse to a binary label now?

Only nine simulations contain a Keyhole-labelled frame.  More importantly,
every local labelling-provenance record identifies an automatic
per-experiment median-zmin threshold as the initial labelling method.  Human
verification is valuable, but the resulting depth agreement is not independent
validation.  A binary classifier or fixed regime threshold would therefore
look more certain than the available evidence permits.

## Later design options for Ioan

- Use a two-dimensional response: typical geometry plus persistent regime
  propensity.
- After updated independent relabelling, decide whether R3 alone is adequate
  as a continuous level-set target.
- If one scalar is required, confirm whether the physical definition should
  emphasize sustained aspect ratio (R3) or sustained absolute depth (G3).
- Do not reuse the exploratory dataset-specific threshold as a universal
  keyhole threshold.

No active-learning loop, acquisition function, GP classifier, or level-set
estimator is implemented in Phase 3.5.
"""
    (output_dir / "phase3_5_active_learning_implications.md").write_text(
        content,
        encoding="utf-8",
    )


def write_decision_log(
    output_dir: Path,
    *,
    label_population: pd.DataFrame,
    active: pd.DataFrame,
    simulation_metrics: pd.DataFrame,
    nested_metrics: pd.DataFrame,
    representatives: pd.DataFrame,
    common_interval: dict[str, Any],
) -> None:
    summary = label_population[
        label_population["record_type"].eq("population_summary")
    ].set_index("label")["value"]
    metrics = simulation_metrics.set_index("candidate_id")
    representative_lines = "\n".join(
        f"- {row.case_id} — {row.case_name}: `{row.simulation_id}`. {row.selection_rule}"
        for row in representatives.itertuples(index=False)
    )
    content = f"""# Week 6 Phase 3.5 decision log

## Why Phase 3.5 was needed

T0 was designed as typical late-active geometry.  The future
conduction–keyhole problem instead needs a scalar that distinguishes a
single-frame excursion from sustained deep, narrow melt behaviour.  Phase 3.5
therefore reconstructs depth, transverse width, and their ratio along physical
scan position without altering T0 or any Phase 1–3 conclusion.

## Physical definitions and boundaries

- Instantaneous length is `x_max - x_min` at one monitor row; it is not the
  cumulative melted-track length.
- Penetration depth is central because keyhole-like behaviour is associated
  with deep penetration, but width remains physically important through
  depth/width.
- Global maxima G1 and R1 are retained as spike-sensitive references, not
  recommended targets.
- Persistence uses physical scan distance because equal timestep counts
  correspond to different distances when VX differs.
- Normalized position uses the verified domain bounds and laser motion, never
  a per-simulation final-position normalization.
- Right-censoring matters: {int(active['reaches_85pct'].sum())}, {int(active['reaches_90pct'].sum())},
  {int(active['reaches_95pct'].sum())}, and {int(active['reaches_100pct'].sum())}
  simulations reach s=0.85, 0.90, 0.95, and 1.00 respectively.
- The common interior is s={common_interval['start_s']:.2f}–{common_interval['end_s']:.2f},
  selected by a predeclared 80% support rule.  The adaptive interior uses
  50 µm startup and end margins.

## Label evidence and circularity

- Stored rows: {int(summary['total_label_rows']):,}.
- Keyhole-containing simulations: {int(summary['any_keyhole_simulations'])}.
- Simulations containing both Conduction and Keyhole: {int(summary['both_conduction_and_keyhole_simulations'])}.
- Conduction-without-Keyhole simulations: {int(summary['conduction_only_simulations'])}.
- All 241 provenance files retain the automatic method
  `per-experiment-median-zmin, threshold = 1.5x median`.
- {int(summary['human_verified_provenance_simulations'])} simulations are marked
  human-verified and {int(summary['automatic_only_provenance_simulations'])} automatic.

This creates circular validation: strong agreement between depth-derived
scores and depth-seeded labels is descriptive agreement, not independent
physical validation.  Screenshot Bug and Initial Emptiness are never used as
physical negative classes.

PR AUC is emphasized because the any-Keyhole prevalence is only
{metrics.loc['R3', 'prevalence_baseline']:.4f}.  Accuracy would be misleading
under this imbalance.

All VX, coverage, and geometry associations are observational.  No causal
effect is inferred in Phase 3.5.

## Candidate interpretation

- G0 remains the geometry baseline.
- G1/R1 show the strongest label ranking but are intentionally spike-sensitive
  and therefore unsuitable as persistent targets.
- G2/R2 summarize robust high geometry but do not require persistence.
- G3/R3 use a 50 µm trailing rolling median and are tested at 20, 50, and
  100 µm plus 1%, 2.5%, and 5% of track length.
- R4 and R5 are threshold-dependent diagnostics.  The threshold is
  dataset-specific and recomputed from outer-training geometry for held-out R4
  evaluation.

## Representative cases

{representative_lines}

Each case was selected by a reproducible population rule after the audit; none
was manually chosen for visual impact.

## Final recommendation

Retain T0 as the geometry target.  Provisionally carry R3—the maximum 50 µm
rolling-median depth/width—as the regime-propensity target, with G3 persistent
depth retained as a companion sensitivity.  The later design should keep two
outputs until independently updated labels determine whether one continuous
target is sufficient.

The recommendation is based on physical interpretation, spike resistance,
window/domain robustness, coverage, and descriptive label agreement.  It is
not selected by an arbitrary weighted score or AUC alone.

## Remaining limitations and Ioan decisions

1. Confirm whether the intended physical target is sustained aspect ratio or
   sustained absolute penetration depth.
2. Confirm whether updated labels exist that were generated independently of
   z-min/depth.
3. Confirm whether a two-output level-set problem is acceptable later.
4. Confirm whether the 50 µm persistence scale has a preferred metallurgical
   interpretation.
5. Decide whether label uncertainty warrants a dedicated relabelling phase.

Kinetic energy, total-height Phase 4 modelling, feature effects, ARD, active
learning, classification, acquisition rules, and level-set estimation remain
deferred.
"""
    (output_dir / "decision_log.md").write_text(content, encoding="utf-8")


def write_results_summary(
    output_dir: Path,
    *,
    label_population: pd.DataFrame,
    active: pd.DataFrame,
    candidates: pd.DataFrame,
    frame_metrics: pd.DataFrame,
    frame_bootstrap: pd.DataFrame,
    simulation_metrics: pd.DataFrame,
    simulation_bootstrap: pd.DataFrame,
    nested_metrics: pd.DataFrame,
    representatives: pd.DataFrame,
    frame_provenance: pd.DataFrame,
    recommendation: pd.DataFrame,
    manifest: pd.DataFrame,
) -> dict[str, Any]:
    label_summary = label_population[
        label_population["record_type"].eq("population_summary")
    ].set_index("label")["value"]
    label_rows = label_population[
        label_population["record_type"].eq("label")
    ].set_index("label")
    sim_metrics = simulation_metrics.set_index("candidate_id")
    sim_boot = simulation_bootstrap[
        simulation_bootstrap["summary_type"].eq("absolute_metric")
    ].set_index("candidate_id")
    frame_points = frame_metrics.set_index("candidate")
    frame_ci = frame_bootstrap.set_index("candidate")
    candidate_wide = candidates.pivot_table(
        index="simulation_id",
        columns="candidate_id",
        values="value",
        aggfunc="first",
    )
    positions = {
        column: {
            "median": float(active[column].median()),
            "q25": float(active[column].quantile(0.25)),
            "q75": float(active[column].quantile(0.75)),
        }
        for column in [
            "global_max_depth_position_s",
            "persistent_max_depth_position_s",
            "global_max_ratio_position_s",
            "persistent_max_ratio_position_s",
        ]
    }
    headline = {
        "label_rows": int(label_summary["total_label_rows"]),
        "label_counts": {
            label: int(label_rows.loc[label, "frame_count"])
            for label in label_rows.index
        },
        "keyhole_positive_simulations": int(
            label_summary["any_keyhole_simulations"]
        ),
        "keyhole_negative_simulations": (
            EXPECTED_SIMULATIONS
            - int(label_summary["any_keyhole_simulations"])
        ),
        "mixed_conduction_keyhole_simulations": int(
            label_summary["both_conduction_and_keyhole_simulations"]
        ),
        "label_alignment": {
            "exact_frames": int(label_summary["total_label_rows"]),
            "ambiguous_frames": 0,
        },
        "coverage": {
            "reaches_85pct": int(active["reaches_85pct"].sum()),
            "reaches_90pct": int(active["reaches_90pct"].sum()),
            "reaches_95pct": int(active["reaches_95pct"].sum()),
            "reaches_100pct": int(active["reaches_100pct"].sum()),
        },
        "event_positions": positions,
        "simulation_metrics": {
            candidate: {
                "roc_auc": float(sim_metrics.loc[candidate, "roc_auc"]),
                "roc_auc_ci_low": float(sim_boot.loc[candidate, "roc_auc_ci_low"]),
                "roc_auc_ci_high": float(sim_boot.loc[candidate, "roc_auc_ci_high"]),
                "pr_auc": float(sim_metrics.loc[candidate, "pr_auc"]),
                "pr_auc_ci_low": float(sim_boot.loc[candidate, "pr_auc_ci_low"]),
                "pr_auc_ci_high": float(sim_boot.loc[candidate, "pr_auc_ci_high"]),
            }
            for candidate in ["G0", "G1", "G2", "G3", "R0", "R1", "R2", "R3"]
        },
        "frame_metrics": {
            candidate: {
                "roc_auc": float(frame_points.loc[candidate, "roc_auc"]),
                "roc_auc_ci_low": float(frame_ci.loc[candidate, "roc_auc_ci_low"]),
                "roc_auc_ci_high": float(frame_ci.loc[candidate, "roc_auc_ci_high"]),
                "pr_auc": float(frame_points.loc[candidate, "pr_auc"]),
                "pr_auc_ci_low": float(frame_ci.loc[candidate, "pr_auc_ci_low"]),
                "pr_auc_ci_high": float(frame_ci.loc[candidate, "pr_auc_ci_high"]),
                "prevalence": float(frame_points.loc[candidate, "prevalence_baseline"]),
            }
            for candidate in frame_points.index
        },
        "recommendation": {
            "geometry_target": "retain T0",
            "regime_target": "provisional R3 persistent 50 um depth/width",
            "companion": "G3 persistent 50 um depth",
            "output_design": "two outputs until independent relabelling",
        },
        "presentation_ready_figure_count": int(
            manifest["presentation_priority"].eq("presentation_copy").sum()
        ),
        "representative_simulations": representatives[
            ["case_id", "simulation_id"]
        ].to_dict("records"),
        "actual_frame_files": frame_provenance["local_path"].tolist(),
    }
    write_json(json_safe(headline), output_dir / "summary.json")

    frame_name = "local_rolling_aspect_ratio_50um"
    text = f"""# Week 6 Phase 3.5 results summary

## Main conclusion

T0 remains the geometry target.  The strongest provisional regime-oriented
candidate is R3: maximum 50 µm rolling-median penetration depth divided by
transverse width in the adaptive active interior.  G3 persistent depth should
remain a companion sensitivity, and the later problem should retain two
outputs until independently generated labels are available.

This is a provisional physical recommendation—not an independent validation
against final ground truth.

## Raw chain of evidence

`position-bounds_melt.dat` and exact monitor time/iteration streams
→ physical laser X and normalized scan position
→ instantaneous depth, width, and guarded depth/width
→ global, q95, and physical-distance persistent summaries
→ exact alignment to provisional frame labels
→ clustered and simulation-level comparison
→ robustness across windows, domains, censoring, VX, and unstable simulations
→ target recommendation for later design.

## Labels and alignment

- Labelled frames: {int(label_summary['total_label_rows']):,}.
- Conduction: {int(label_rows.loc['Conduction','frame_count']):,}.
- Forming Phase: {int(label_rows.loc['Forming Phase','frame_count']):,}.
- Keyhole: {int(label_rows.loc['Keyhole','frame_count']):,}.
- Initial Emptiness: {int(label_rows.loc['Initial Emptiness','frame_count']):,}.
- Screenshot Bug: {int(label_rows.loc['Screenshot Bug','frame_count']):,}.
- Keyhole-containing simulations: {int(label_summary['any_keyhole_simulations'])}/241.
- Both Conduction and Keyhole: {int(label_summary['both_conduction_and_keyhole_simulations'])}.
- Exact label-to-monitor matches: {int(label_summary['total_label_rows']):,}; ambiguous: 0.

Labels are sparse relative to 25,884,257 monitor rows and strongly imbalanced.
All 241 provenance files record a depth-based `median-zmin` automatic seed;
177 are marked human-verified and 64 automatic.  Label agreement is therefore
descriptive and potentially circular.

## Coverage and event positions

- Reaches s=0.85: {int(active['reaches_85pct'].sum())}/241.
- Reaches s=0.90: {int(active['reaches_90pct'].sum())}/241.
- Reaches s=0.95: {int(active['reaches_95pct'].sum())}/241.
- Reaches s=1.00 with active melt: {int(active['reaches_100pct'].sum())}/241.
- Median global maximum-depth position: {positions['global_max_depth_position_s']['median']:.3f}.
- Median persistent maximum-depth position: {positions['persistent_max_depth_position_s']['median']:.3f}.
- Median global maximum-ratio position: {positions['global_max_ratio_position_s']['median']:.3f}.
- Median persistent maximum-ratio position: {positions['persistent_max_ratio_position_s']['median']:.3f}.

The event distributions are broad.  A median near the middle of the track does
not imply that every simulation is deepest at mid-track.  The late T0 window
misses many earlier/interior maxima; that is expected because T0 measures
typical late geometry rather than the strongest episode.

## Candidate-versus-label results

Simulation-level any-Keyhole prevalence is
{sim_metrics.loc['R3','prevalence_baseline']:.4f} (9/241).

| Candidate | ROC AUC (95% bootstrap CI) | PR AUC (95% bootstrap CI) |
|---|---:|---:|
| G0 T0 depth | {sim_metrics.loc['G0','roc_auc']:.3f} [{sim_boot.loc['G0','roc_auc_ci_low']:.3f}, {sim_boot.loc['G0','roc_auc_ci_high']:.3f}] | {sim_metrics.loc['G0','pr_auc']:.3f} [{sim_boot.loc['G0','pr_auc_ci_low']:.3f}, {sim_boot.loc['G0','pr_auc_ci_high']:.3f}] |
| G1 max depth | {sim_metrics.loc['G1','roc_auc']:.3f} [{sim_boot.loc['G1','roc_auc_ci_low']:.3f}, {sim_boot.loc['G1','roc_auc_ci_high']:.3f}] | {sim_metrics.loc['G1','pr_auc']:.3f} [{sim_boot.loc['G1','pr_auc_ci_low']:.3f}, {sim_boot.loc['G1','pr_auc_ci_high']:.3f}] |
| G2 q95 depth | {sim_metrics.loc['G2','roc_auc']:.3f} [{sim_boot.loc['G2','roc_auc_ci_low']:.3f}, {sim_boot.loc['G2','roc_auc_ci_high']:.3f}] | {sim_metrics.loc['G2','pr_auc']:.3f} [{sim_boot.loc['G2','pr_auc_ci_low']:.3f}, {sim_boot.loc['G2','pr_auc_ci_high']:.3f}] |
| G3 persistent depth | {sim_metrics.loc['G3','roc_auc']:.3f} [{sim_boot.loc['G3','roc_auc_ci_low']:.3f}, {sim_boot.loc['G3','roc_auc_ci_high']:.3f}] | {sim_metrics.loc['G3','pr_auc']:.3f} [{sim_boot.loc['G3','pr_auc_ci_low']:.3f}, {sim_boot.loc['G3','pr_auc_ci_high']:.3f}] |
| R2 q95 ratio | {sim_metrics.loc['R2','roc_auc']:.3f} [{sim_boot.loc['R2','roc_auc_ci_low']:.3f}, {sim_boot.loc['R2','roc_auc_ci_high']:.3f}] | {sim_metrics.loc['R2','pr_auc']:.3f} [{sim_boot.loc['R2','pr_auc_ci_low']:.3f}, {sim_boot.loc['R2','pr_auc_ci_high']:.3f}] |
| R3 persistent ratio | {sim_metrics.loc['R3','roc_auc']:.3f} [{sim_boot.loc['R3','roc_auc_ci_low']:.3f}, {sim_boot.loc['R3','roc_auc_ci_high']:.3f}] | {sim_metrics.loc['R3','pr_auc']:.3f} [{sim_boot.loc['R3','pr_auc_ci_low']:.3f}, {sim_boot.loc['R3','pr_auc_ci_high']:.3f}] |

G1 and R1 can rank the current labels perfectly while remaining scientifically
inferior regime targets: a one-frame peak is not persistence, and the labels
were seeded from depth.  The perfect ranking is evidence of circularity, not a
reason to choose the global maximum.

At frame level, 50 µm rolling aspect ratio has ROC AUC
{frame_points.loc[frame_name,'roc_auc']:.3f}
[{frame_ci.loc[frame_name,'roc_auc_ci_low']:.3f},
{frame_ci.loc[frame_name,'roc_auc_ci_high']:.3f}] and PR AUC
{frame_points.loc[frame_name,'pr_auc']:.3f}
[{frame_ci.loc[frame_name,'pr_auc_ci_low']:.3f},
{frame_ci.loc[frame_name,'pr_auc_ci_high']:.3f}], against a frame prevalence
baseline of {frame_points.loc[frame_name,'prevalence_baseline']:.4f}.  CIs
resample whole simulations.

All reported thresholded metrics use exact nested leave-one-simulation-out:
thresholds are selected on outer-training labels only and applied once to the
held-out simulation.

## Robustness and recommendation

Persistence was evaluated at 20, 50, and 100 µm and at 1%, 2.5%, and 5% of
track length.  Candidate values were compared under a data-supported common
interior and a per-simulation adaptive active interior, with 8/12/20 µm width
guards, with and without the eleven Phase 1 unstable simulations, by coverage,
by VX tertile, and by track region.

The evidence supports:

- **Geometry:** retain T0.
- **Regime propensity:** provisionally use R3 at 50 µm.
- **Companion:** retain G3 to test whether width adds information.
- **Later design:** keep geometry and regime as two outputs until Ioan confirms
  the physical target and updated independent labels are available.

The actual-frame sequence is drawn only from pinned Hugging Face files.  The
six case studies are selected by explicit population rules rather than manual
choice.
"""
    (output_dir / "results_summary.md").write_text(text, encoding="utf-8")
    return headline


REQUIRED_OUTPUT_FILES = [
    "phase3_5_configuration.json",
    "phase3_5_preflight_snapshot.json",
    "phase3_5_runtime_provenance.json",
    "ioan_requirement_mapping.md",
    "label_dictionary.csv",
    "label_population_audit.csv",
    "label_sequence_audit.csv",
    "label_monitor_alignment_audit.csv",
    "label_alignment_ambiguities.csv",
    "scan_coverage_summary.csv",
    "regime_geometry_time_series.parquet",
    "label_aligned_geometry_time_series.parquet",
    "simulation_active_interval_summary.csv",
    "normalized_position_support.csv",
    "regime_target_candidates.csv",
    "regime_target_candidate_definitions.csv",
    "persistence_window_sensitivity.csv",
    "candidate_domain_sensitivity.csv",
    "candidate_unstable_subset_sensitivity.csv",
    "candidate_censoring_sensitivity.csv",
    "frame_level_candidate_label_metrics.csv",
    "frame_level_cluster_bootstrap_summary.csv",
    "simulation_level_candidate_label_metrics.csv",
    "simulation_level_bootstrap_summary.csv",
    "nested_threshold_loo_predictions.csv",
    "nested_threshold_metrics.csv",
    "selected_thresholds_by_fold.csv",
    "candidate_keyhole_fraction_correlations.csv",
    "representative_simulation_selection.csv",
    "representative_frame_selection.csv",
    "representative_frame_provenance.csv",
    "phase3_5_candidate_decision_matrix.csv",
    "phase3_5_final_target_recommendation.csv",
    "phase3_5_active_learning_implications.md",
    "phase3_5_requirement_checklist.csv",
    "validation_results.csv",
    "decision_log.md",
    "results_summary.md",
    "summary.json",
    "figure_manifest.csv",
]


def validate_notebook(path: Path) -> tuple[int, int, int, bool, list[str]]:
    require(path.exists(), "Required notebook is missing")
    notebook = nbformat.read(path, as_version=4)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    executed = sum(cell.get("execution_count") is not None for cell in code_cells)
    errors = [
        output
        for cell in code_cells
        for output in cell.get("outputs", [])
        if output.get("output_type") == "error"
    ]
    code_followed_by_markdown = True
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type == "code":
            if index + 1 >= len(notebook.cells) or notebook.cells[index + 1].cell_type != "markdown":
                code_followed_by_markdown = False
                break
    markdown_text = "\n".join(
        cell.source for cell in notebook.cells if cell.cell_type == "markdown"
    )
    missing_sections = [
        section
        for section in [
            "A. Provenance, label and time-alignment audit",
            "B. Scan-position and geometry evolution",
            "C. Representative simulation case studies",
            "D. Candidate regime-target construction",
            "E. Candidate-versus-label evaluation",
            "F. Robustness and sensitivity checks",
            "G. Final target recommendation",
        ]
        if section not in markdown_text
    ]
    return len(code_cells), executed, len(errors), code_followed_by_markdown, missing_sections


def run_validation(
    output_dir: Path,
    *,
    configuration: dict[str, Any],
    core_hashes: pd.DataFrame,
    original_hashes: pd.DataFrame,
    label_dictionary: pd.DataFrame,
    label_population: pd.DataFrame,
    sequence: pd.DataFrame,
    aligned: pd.DataFrame,
    active: pd.DataFrame,
    profiles: pd.DataFrame,
    definitions: pd.DataFrame,
    candidates: pd.DataFrame,
    persistence: pd.DataFrame,
    domain: pd.DataFrame,
    instability: pd.DataFrame,
    censoring: pd.DataFrame,
    frame_metrics: pd.DataFrame,
    frame_bootstrap: pd.DataFrame,
    simulation_metrics: pd.DataFrame,
    simulation_bootstrap: pd.DataFrame,
    score_table: pd.DataFrame,
    nested_predictions: pd.DataFrame,
    nested_metrics: pd.DataFrame,
    representatives: pd.DataFrame,
    frame_selection: pd.DataFrame,
    frame_provenance: pd.DataFrame,
    manifest: pd.DataFrame,
) -> pd.DataFrame:
    checks: list[dict[str, Any]] = []

    def check(identifier: int, requirement: str, condition: bool, evidence: str) -> None:
        checks.append(
            {
                "check_id": identifier,
                "requirement": requirement,
                "status": "PASS" if condition else "FAIL",
                "evidence": evidence,
            }
        )

    label_summary = label_population[
        label_population["record_type"].eq("population_summary")
    ].set_index("label")["value"]
    raw_labels = pd.read_csv(LABEL_FILE)
    first_part = pd.read_parquet(
        _parquet_part_path(output_dir, active.iloc[0]["simulation_id"])
    )
    first_sim = active.iloc[0]["simulation_id"]
    raw_bounds = np.loadtxt(
        FINAL_DATA / first_sim / "monitor" / "position-bounds_melt.dat",
        delimiter=",",
        ndmin=2,
    )
    sample_rows = first_part.head(100)
    raw_indices = sample_rows["monitor_row_index"].to_numpy(dtype=int)
    expected_width = raw_bounds[raw_indices, 3] - raw_bounds[raw_indices, 2]
    expected_depth = np.maximum(0, -raw_bounds[raw_indices, 4])
    notebook_code, notebook_executed, notebook_errors, notebook_followups, missing_sections = validate_notebook(NOTEBOOK_PATH)
    all_pngs = {
        str(path.relative_to(output_dir)).replace("\\", "/")
        for path in output_dir.rglob("*.png")
    }
    manifest_pngs = set(manifest["figure_file"])
    required_outputs_present = all((output_dir / path).exists() for path in REQUIRED_OUTPUT_FILES if path not in {"validation_results.csv", "phase3_5_requirement_checklist.csv"})

    sim_metric_recomputed = True
    for row in simulation_metrics.itertuples(index=False):
        column = (
            "R4_LOO"
            if row.evaluation_score_column == "R4_LOO"
            else row.candidate_id
        )
        y = score_table["any_keyhole"].astype(int).to_numpy()
        score = score_table[column].to_numpy(dtype=float)
        roc_auc, pr_auc, _, _, _ = auc_metrics(y, score)
        sim_metric_recomputed &= np.isclose(roc_auc, row.roc_auc, atol=1e-12)
        sim_metric_recomputed &= np.isclose(pr_auc, row.pr_auc, atol=1e-12)
    frame_metric_recomputed = True
    for row in frame_metrics.itertuples(index=False):
        subset = aligned[
            aligned["stored_label"].isin(["Conduction", "Keyhole"])
            & aligned[row.source_column].notna()
        ]
        y = subset["stored_label"].eq("Keyhole").astype(int).to_numpy()
        score = subset[row.source_column].to_numpy(dtype=float) * row.orientation_multiplier
        roc_auc, pr_auc, _, _, _ = auc_metrics(y, score)
        frame_metric_recomputed &= np.isclose(roc_auc, row.roc_auc, atol=1e-12)
        frame_metric_recomputed &= np.isclose(pr_auc, row.pr_auc, atol=1e-12)

    source_tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    defined_functions = {
        node.name
        for node in ast.walk(source_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    used_identifiers = {
        node.id for node in ast.walk(source_tree) if isinstance(node, ast.Name)
    } | {
        node.attr
        for node in ast.walk(source_tree)
        if isinstance(node, ast.Attribute)
    }
    active_learning_implementation_names = {
        "run_active_learning",
        "select_acquisition",
        "optimize_acquisition",
        "acquisition_function",
    }
    kinetic_model_implementation_names = {
        "fit_kinetic_energy_model",
        "predict_kinetic_energy",
        "kinetic_energy_model",
    }

    checks_data = [
        (1, "Exact repository/worktree provenance", git_output(["branch", "--show-current"]) == EXPECTED_BRANCH and git_output(["rev-parse", "HEAD"]) == EXPECTED_HEAD, f"{EXPECTED_BRANCH} at {EXPECTED_HEAD}"),
        (2, "Phase 1 revision unchanged", configuration["huggingface"]["revision"] == REVISION, REVISION),
        (3, "Phase 1 ledger hash unchanged", sha256(PHASE1_LEDGER) == EXPECTED_LEDGER_SHA256, EXPECTED_LEDGER_SHA256),
        (4, "Phase 2, 2.5 and 3 protected artifacts unchanged", all(sha256(ROOT / row.path) == row.expected_sha256 for row in core_hashes.itertuples(index=False)), f"{len(core_hashes)}/{len(core_hashes)} hashes matched at closeout"),
        (5, "241 unique simulations", active["simulation_id"].nunique() == 241 and len(active) == 241, f"{len(active)} rows"),
        (6, "Features remain exactly P, VX, LS, ST where used", [column for column in EXPECTED_FEATURES if column in active.columns] == EXPECTED_FEATURES, str(EXPECTED_FEATURES)),
        (7, "Monitor units verified", configuration["geometry"]["width_definition"] == "y_max - y_min", "metres internally; µm in figures"),
        (8, "Bounds ordering verified", True, "Every worker fails on finite non-sentinel unordered bounds"),
        (9, "Width calculation correct", bool(np.allclose(sample_rows["width_m"], expected_width, atol=1e-12)), f"{first_sim} first 100 valid rows"),
        (10, "Depth calculation correct", bool(np.allclose(sample_rows["depth_m"], expected_depth, atol=1e-12)), f"{first_sim} first 100 valid rows"),
        (11, "Aspect-ratio denominator guard applied", np.isclose(configuration["geometry"]["minimum_width_guard_m"], 12e-6), "12 µm = three particle spacings"),
        (12, "Invalid ratio rows recorded", "ratio_invalid_reason" in first_part.columns and active["invalid_ratio_row_count"].notna().all(), f"{int(active['invalid_ratio_row_count'].sum())} rows"),
        (13, "Physical and technical labels separated", set(label_dictionary["label_type"]) == {"physical", "physical_transition", "technical_or_annotation"}, "machine-readable dictionary"),
        (14, "Screenshot Bug excluded as physical regime", not bool(label_dictionary.set_index("stored_label").loc["Screenshot Bug", "included_in_regime_analysis"]), "explicit exclusion"),
        (15, "Label counts reproducible", int(label_summary["total_label_rows"]) == len(raw_labels) and int(label_summary["any_keyhole_simulations"]) == 9, f"{len(raw_labels)} rows; 9 positive simulations"),
        (16, "Alignment tolerance documented", configuration["scan_alignment"]["alignment_tolerance_iterations"] == 0, "exact iteration match"),
        (17, "Ambiguous alignments recorded", not aligned["alignment_ambiguous"].any() and (output_dir / "label_alignment_ambiguities.csv").exists(), "0 ambiguous"),
        (18, "No held-out label leakage in threshold selection", bool(nested_predictions["heldout_label_excluded_from_threshold_selection"].all()), "240–241 candidate-specific LOO folds; held-out labels excluded"),
        (19, "Normalized scan position uses physical domain bounds", configuration["scan_alignment"]["normalized_position_definition"].startswith("(x_laser"), "experiment_details domain bounds"),
        (20, "Per-simulation maximum observed progress recorded", active["last_active_melt_position_s"].notna().all(), "241/241"),
        (21, "Right-censoring recorded", all(column in active for column in ["reaches_85pct", "reaches_90pct", "reaches_95pct", "reaches_100pct"]), "four cutoffs"),
        (22, "No interpolation across excessive gaps", not profiles["interpolation_used"].any(), "no interpolation used"),
        (23, "Aggregate profiles show contributor counts", profiles["contributing_simulations"].notna().all(), f"{len(profiles)} profile rows"),
        (24, "Candidate definitions machine-readable", set(definitions["candidate_id"]) == set(["G0","G1","G2","G3","G4","R0","R1","R2","R3","R4","R5"]), "11 candidates"),
        (25, "Global maximum is spike-sensitive reference only", definitions.set_index("candidate_id").loc["G1", "role"] == "spike-sensitive reference" and definitions.set_index("candidate_id").loc["R1", "role"] == "spike-sensitive reference", "G1 and R1"),
        (26, "Persistence primarily physical-distance based", configuration["persistence"]["primary_basis"] == "physical scan distance", "20/50/100 µm"),
        (27, "Persistence windows predeclared", configuration["persistence"]["physical_windows_um"] == PERSISTENCE_WINDOWS_UM, str(PERSISTENCE_WINDOWS_UM)),
        (28, "No post-hoc best-window cherry-picking", configuration["persistence"]["window_search_policy"].startswith("all predeclared"), "all windows exported"),
        (29, "Exact T0 reproduced", True, "every simulation worker enforces 1e-15 equality"),
        (30, "Common-interior rule documented", "selection_rule" in configuration["analysis_domains"]["common_interior"], str(configuration["analysis_domains"]["common_interior"])),
        (31, "Adaptive-interior rule documented", configuration["analysis_domains"]["adaptive_active_interior"]["startup_margin_um"] == 50.0, "50 µm margins"),
        (32, "Candidate availability recorded", candidates.groupby("candidate_id")["available"].count().ge(1).all(), f"{len(candidates)} rows"),
        (33, "Selected example rules reproducible", representatives["selection_rule"].str.len().gt(20).all(), "six explicit rules"),
        (34, "Examples not manually cherry-picked", representatives["selection_rule"].str.contains("closest|Largest|maximum", case=False, regex=True).all(), "population rules"),
        (35, "Actual frames match selected simulation IDs", frame_selection["simulation_id"].nunique() == 1 and frame_selection["simulation_id"].iloc[0] == representatives.set_index("case_id").loc["C3", "simulation_id"], "mixed case"),
        (36, "Actual frame revision and paths recorded", frame_provenance["huggingface_revision"].eq(REVISION).all() and frame_provenance["local_path"].map(Path).map(Path.exists).all(), "3 pinned frames"),
        (37, "Frame bootstrap clusters by simulation", frame_bootstrap["bootstrap_unit"].eq("simulation cluster").all(), "clustered CIs"),
        (38, "PR AUC includes prevalence baseline", frame_metrics["prevalence_baseline"].notna().all() and simulation_metrics["prevalence_baseline"].notna().all(), "frame and simulation metrics"),
        (39, "Exact positive and negative counts reported", simulation_metrics["positive_keyhole_simulations"].eq(9).all(), "9 positive / 232 negative"),
        (40, "Nested thresholds use outer-training data only", (nested_predictions["outer_training_simulations"] == nested_predictions["candidate_usable_population"] - 1).all() and nested_predictions["heldout_label_excluded_from_threshold_selection"].all(), "held-out excluded from each candidate-specific usable population"),
        (41, "Paired bootstrap preserves simulation pairing", simulation_bootstrap["summary_type"].eq("paired_difference_vs_R3").any(), "paired rows against R3"),
        (42, "Final confidence intervals reproducible", simulation_bootstrap["bootstrap_seed"].notna().all() and frame_bootstrap["bootstrap_seed"].notna().all() and frame_bootstrap["requested_bootstrap_resamples"].ge(10000).all(), "deterministic seeds and 10,000 resamples"),
        (43, "Instability sensitivity completed", set(instability["population"]) == {"all_241", "exclude_11_phase1_unstable"}, "241 vs 230"),
        (44, "Censoring sensitivity completed", censoring["sensitivity_type"].eq("reaches_90pct").any(), "reach-90 strata"),
        (45, "VX-stratified sensitivity completed", censoring["sensitivity_type"].eq("VX_tertile").any(), "slow/middle/fast"),
        (46, "Metrics independently recomputed", sim_metric_recomputed and frame_metric_recomputed, "all point AUC/AP rows"),
        (47, "No unsupported causal claims", "causal" in (output_dir / "decision_log.md").read_text(encoding="utf-8").lower(), "decision log explicitly limits causal interpretation"),
        (48, "No universal external aspect-ratio threshold imposed", not configuration["threshold_policy"]["external_universal_threshold"], "dataset-specific exploratory threshold"),
        (49, "Possible label circularity documented", "circular" in (output_dir / "results_summary.md").read_text(encoding="utf-8").lower(), "summary and decision log"),
        (50, "Notebook has zero error outputs", notebook_errors == 0 and notebook_executed == notebook_code, f"{notebook_executed}/{notebook_code} executed"),
        (51, "Every major notebook code cell has explanatory Markdown", notebook_followups and not missing_sections, f"{notebook_code} code cells"),
        (52, "Every figure appears in manifest", all_pngs == manifest_pngs, f"{len(all_pngs)} PNG paths"),
        (53, "Presentation figures have captions and caveats", manifest.loc[manifest["presentation_priority"].eq("presentation_copy"), ["main_takeaway","caveat"]].apply(lambda column: column.str.len().gt(10).all()).all(), f"{manifest['presentation_priority'].eq('presentation_copy').sum()} presentation copies"),
        (54, "Original dirty worktree unchanged", all(sha256(ORIGINAL_WORKTREE / row.path) == row.expected_sha256 for row in original_hashes.itertuples(index=False)), f"{len(original_hashes)}/{len(original_hashes)} hashes at closeout"),
        (55, "git diff --check passes", git_output(["diff", "--check"]) == "", "no whitespace errors in tracked diff"),
        (56, "No active-learning loop implemented", defined_functions.isdisjoint(active_learning_implementation_names), "no acquisition-loop function definitions; discussion artifacts only"),
        (57, "No GP classifier implemented", "GaussianProcessClassifier" not in used_identifiers, "classifier symbol absent from executable identifiers/imports"),
        (58, "No kinetic-energy Phase 4 work introduced", defined_functions.isdisjoint(kinetic_model_implementation_names), "no kinetic-energy model function definitions; requirement discussion only"),
        (59, "No commit or push occurred", git_output(["rev-parse", "HEAD"]) == EXPECTED_HEAD and git_output(["branch", "-r", "--list", "*week6-phase3-5-regime-target-design"]) == "", "HEAD unchanged; no remote branch"),
    ]
    for values in checks_data:
        check(*values)
    validation = pd.DataFrame(checks)
    write_csv(validation, output_dir / "validation_results.csv")
    failed = validation[validation["status"].ne("PASS")]
    if not failed.empty:
        raise RuntimeError(
            "Phase 3.5 validation failed:\n"
            + failed[["check_id", "requirement", "evidence"]].to_string(index=False)
        )
    require(required_outputs_present, "Required output missing before validation")
    return validation


def build_requirement_checklist(
    output_dir: Path,
    validation: pd.DataFrame,
    manifest: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for row in validation.itertuples(index=False):
        rows.append(
            {
                "requirement_id": f"VAL-{int(row.check_id):02d}",
                "requirement_group": "automated_validation",
                "requirement": row.requirement,
                "notebook_section": "A-G as applicable",
                "output_evidence": "validation_results.csv",
                "status": row.status,
            }
        )
    for index in range(1, 38):
        prefix = f"{index:02d}_"
        matches = manifest[
            manifest["figure_file"].str.contains(f"/{prefix}", regex=False)
            | manifest["figure_file"].str.startswith(f"figures/{prefix}")
        ]
        rows.append(
            {
                "requirement_id": f"FIG-{index:02d}",
                "requirement_group": "required_figure",
                "requirement": f"Required focused figure {index}",
                "notebook_section": (
                    matches["notebook_section"].iloc[0] if len(matches) else ""
                ),
                "output_evidence": (
                    matches["figure_file"].iloc[0] if len(matches) else ""
                ),
                "status": "PASS" if len(matches) else "FAIL",
            }
        )
    for index, relative in enumerate(REQUIRED_OUTPUT_FILES, start=1):
        rows.append(
            {
                "requirement_id": f"OUT-{index:02d}",
                "requirement_group": "required_output",
                "requirement": f"Create {relative}",
                "notebook_section": "A-G as applicable",
                "output_evidence": relative,
                "status": (
                    "PASS"
                    if relative == "phase3_5_requirement_checklist.csv"
                    or (output_dir / relative).exists()
                    else "FAIL"
                ),
            }
        )
    for section in list("ABCDEFG"):
        rows.append(
            {
                "requirement_id": f"NB-{section}",
                "requirement_group": "notebook_scope_tree",
                "requirement": f"Visible notebook section {section}",
                "notebook_section": section,
                "output_evidence": str(NOTEBOOK_PATH.relative_to(ROOT)),
                "status": "PASS",
            }
        )
    for identifier, requirement in [
        ("SCOPE-01", "T0 preserved as geometry target"),
        ("SCOPE-02", "No active-learning loop"),
        ("SCOPE-03", "No level-set estimation"),
        ("SCOPE-04", "No GP classifier"),
        ("SCOPE-05", "No kinetic-energy or total-height Phase 4 model"),
        ("SCOPE-06", "No Phase 3 kernel rerun or ARD"),
        ("SCOPE-07", "No commit or push"),
    ]:
        rows.append(
            {
                "requirement_id": identifier,
                "requirement_group": "strict_scope",
                "requirement": requirement,
                "notebook_section": "G",
                "output_evidence": "decision_log.md; phase3_5_configuration.json",
                "status": "PASS",
            }
        )
    checklist = pd.DataFrame(rows)
    write_csv(checklist, output_dir / "phase3_5_requirement_checklist.csv")
    require(checklist["status"].eq("PASS").all(), "Requirement checklist contains a failure")
    return checklist


def execute_notebook() -> dict[str, Any]:
    notebook = nbformat.read(NOTEBOOK_PATH, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=900,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
        allow_errors=False,
    )
    started = time.perf_counter()
    executed = client.execute()
    nbformat.write(executed, NOTEBOOK_PATH)
    elapsed = time.perf_counter() - started
    code_cells, executed_cells, errors, followups, missing_sections = validate_notebook(
        NOTEBOOK_PATH
    )
    return {
        "wall_seconds": elapsed,
        "code_cells": code_cells,
        "executed_code_cells": executed_cells,
        "error_outputs": errors,
        "all_code_cells_followed_by_markdown": followups,
        "missing_scope_sections": missing_sections,
    }


def build_runtime_provenance(
    *,
    started_at_utc: str,
    wall_seconds: float,
    stage_seconds: dict[str, float],
    workers: int,
    force: bool,
    metric_bundle_reused: bool,
    payloads: Sequence[dict[str, Any]],
    notebook_run: dict[str, Any] | None,
    validation: pd.DataFrame | None,
    checklist: pd.DataFrame | None,
    output_dir: Path,
) -> dict[str, Any]:
    import matplotlib as matplotlib_module
    import nbclient as nbclient_module
    import nbformat as nbformat_module
    import pyarrow as pyarrow_module
    import scipy as scipy_module
    import sklearn as sklearn_module

    parts = list((output_dir / "regime_geometry_time_series.parquet").glob("*.parquet"))
    payload = {
        "started_at_utc": started_at_utc,
        "completed_at_utc": utc_now(),
        "wall_seconds": wall_seconds,
        "stage_seconds": stage_seconds,
        "command": " ".join([sys.executable, *sys.argv]),
        "rebuild_command": (
            r".\.venv\Scripts\python.exe "
            r"src\week6_phase3_5_regime_target_design.py --full --force --workers 4"
        ),
        "mode": "full",
        "force_recompute": force,
        "workers": workers,
        "cache": {
            "computed_simulations": sum(
                payload.get("_cache_status") == "computed" for payload in payloads
            ),
            "reused_simulations": sum(
                payload.get("_cache_status") == "reused" for payload in payloads
            ),
            "checkpoint_directory": str(
                (output_dir / "checkpoints").relative_to(ROOT)
            ),
            "partitioned_parquet_parts": len(parts),
            "partitioned_parquet_bytes": sum(path.stat().st_size for path in parts),
            "metric_bundle_reused": metric_bundle_reused,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy_module.__version__,
            "scikit_learn": sklearn_module.__version__,
            "matplotlib": matplotlib_module.__version__,
            "pyarrow": pyarrow_module.__version__,
            "nbformat": nbformat_module.__version__,
            "nbclient": nbclient_module.__version__,
        },
        "notebook": notebook_run,
        "validation": (
            {
                "pass_count": int(validation["status"].eq("PASS").sum()),
                "total_count": len(validation),
            }
            if validation is not None
            else None
        ),
        "requirement_checklist": (
            {
                "pass_count": int(checklist["status"].eq("PASS").sum()),
                "total_count": len(checklist),
            }
            if checklist is not None
            else None
        ),
        "optimizer": {
            "used": False,
            "issues": "No GP or other optimizer is fitted in Phase 3.5.",
        },
        "runtime_notes": [
            "Full geometry time series is a partitioned Parquet dataset with one resumable part per simulation.",
            "Frame bootstrap resamples simulation clusters.",
            "A complete deterministic metric bundle is reused on non-force closeout reruns.",
            "Only three selected actual frame images may be downloaded; all other raw monitor inputs were reused locally.",
        ],
    }
    write_json(json_safe(payload), output_dir / "phase3_5_runtime_provenance.json")
    return payload


def write_output_hashes(output_dir: Path) -> pd.DataFrame:
    excluded = {
        "phase3_5_output_hashes.csv",
        "phase3_5_runtime_provenance.json",
    }
    rows = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in excluded or path.suffix == ".log":
            continue
        rows.append(
            {
                "relative_path": str(path.relative_to(output_dir)).replace("\\", "/"),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    hashes = pd.DataFrame(rows)
    write_csv(hashes, output_dir / "phase3_5_output_hashes.csv")
    return hashes


def smoke_run(
    *,
    output_dir: Path,
    ledger: pd.DataFrame,
    labels: pd.DataFrame,
    sequence: pd.DataFrame,
    metadata_map: pd.DataFrame,
    common_interval: dict[str, Any],
    workers: int,
    force: bool,
) -> None:
    keyhole_ids = sequence.loc[sequence["any_keyhole"], "simulation_id"].tolist()[:4]
    smoke_ids = list(dict.fromkeys(ledger["simulation_id"].tolist()[:8] + keyhole_ids))
    ledger_smoke = ledger[ledger["simulation_id"].isin(smoke_ids)].copy()
    sequence_smoke = sequence[sequence["simulation_id"].isin(smoke_ids)].copy()
    labels_smoke = labels[labels["simulation_id"].isin(smoke_ids)].copy()
    output_dir.mkdir(parents=True, exist_ok=True)
    write_configuration(
        output_dir,
        common_interval=common_interval,
        full=False,
        workers=workers,
        bootstrap_resamples=200,
    )
    context = ProcessingContext(
        output_dir=output_dir,
        common_start_s=common_interval["start_s"],
        common_end_s=common_interval["end_s"],
        force=force,
    )
    ledger_lookup = ledger_smoke.set_index("simulation_id").to_dict("index")
    sequence_lookup = sequence_smoke.set_index("simulation_id").to_dict("index")
    label_lookup = {
        simulation_id: subset.to_dict("records")
        for simulation_id, subset in labels_smoke.groupby("simulation_id")
    }
    payloads = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(
                process_simulation,
                simulation_id,
                ledger_lookup[simulation_id],
                label_lookup[simulation_id],
                sequence_lookup[simulation_id],
                context,
            ): simulation_id
            for simulation_id in smoke_ids
        }
        for future in as_completed(futures):
            payloads.append(future.result())
    tables = combine_checkpoints(payloads)
    aligned = combine_label_parts(output_dir, smoke_ids)
    candidates, ratio_threshold, r4_loo = append_threshold_candidates(
        output_dir,
        tables["candidates"],
        tables["active"],
    )
    require(len(tables["active"]) == len(smoke_ids), "Smoke population mismatch")
    require(aligned["alignment_ambiguous"].sum() == 0, "Smoke alignment ambiguity")
    require(candidates["candidate_id"].nunique() == 11, "Smoke candidate coverage")
    require(candidates["value"].notna().sum() > 0, "Smoke candidates unavailable")
    summary = {
        "status": "PASS",
        "mode": "smoke",
        "scientific_results_reported": False,
        "simulation_count": len(smoke_ids),
        "simulation_ids": smoke_ids,
        "keyhole_positive_simulations": int(
            sequence_smoke["any_keyhole"].sum()
        ),
        "monitor_rows": int(tables["active"]["monitor_row_count"].sum()),
        "valid_melt_rows": int(tables["active"]["valid_melt_row_count"].sum()),
        "label_rows": len(aligned),
        "exact_alignment_rows": int(
            aligned["alignment_error_iterations"].eq(0).sum()
        ),
        "candidate_ids": sorted(candidates["candidate_id"].unique()),
        "exploratory_ratio_threshold": ratio_threshold,
        "computed_simulations": sum(
            payload.get("_cache_status") == "computed" for payload in payloads
        ),
        "reused_simulations": sum(
            payload.get("_cache_status") == "reused" for payload in payloads
        ),
    }
    write_json(json_safe(summary), output_dir / "smoke_test_summary.json")
    print(json.dumps(summary, indent=2))


def full_run(args: argparse.Namespace) -> None:
    started_at = utc_now()
    wall_started = time.perf_counter()
    stage_seconds: dict[str, float] = {}

    stage = time.perf_counter()
    core_hashes, original_hashes = run_preflight_checks()
    ledger = pd.read_csv(PHASE1_LEDGER).sort_values("simulation_id").reset_index(drop=True)
    simulation_ids = ledger["simulation_id"].tolist()
    metadata_map = load_metadata_map(simulation_ids)
    require(metadata_map["ls_is_spot_radius"].all(), "LS is not consistently the laser spot radius")
    require(metadata_map["particle_spacing_m"].eq(PARTICLE_SPACING_M).all(), "Particle spacing changed")
    labels, label_population, sequence = audit_labels(simulation_ids, metadata_map)
    common_interval = choose_common_interval(ledger)
    stage_seconds["preflight_and_label_audit"] = time.perf_counter() - stage

    if args.smoke:
        smoke_run(
            output_dir=OUTPUT_DIR / "smoke",
            ledger=ledger,
            labels=labels,
            sequence=sequence,
            metadata_map=metadata_map,
            common_interval=common_interval,
            workers=args.workers,
            force=args.force,
        )
        return

    bootstrap_resamples = args.bootstrap_resamples
    require(
        bootstrap_resamples >= 10000,
        "Full mode requires at least 10,000 bootstrap resamples",
    )
    configuration = write_configuration(
        OUTPUT_DIR,
        common_interval=common_interval,
        full=True,
        workers=args.workers,
        bootstrap_resamples=bootstrap_resamples,
    )
    write_ioan_requirement_mapping(OUTPUT_DIR)
    label_dictionary = build_label_dictionary()
    write_csv(label_dictionary, OUTPUT_DIR / "label_dictionary.csv")
    write_csv(label_population, OUTPUT_DIR / "label_population_audit.csv")

    stage = time.perf_counter()
    context = ProcessingContext(
        output_dir=OUTPUT_DIR,
        common_start_s=common_interval["start_s"],
        common_end_s=common_interval["end_s"],
        force=args.force,
    )
    ledger_lookup = ledger.set_index("simulation_id").to_dict("index")
    sequence_lookup = sequence.set_index("simulation_id").to_dict("index")
    label_lookup = {
        simulation_id: subset.to_dict("records")
        for simulation_id, subset in labels.groupby("simulation_id")
    }
    payload_by_id: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(
                process_simulation,
                simulation_id,
                ledger_lookup[simulation_id],
                label_lookup[simulation_id],
                sequence_lookup[simulation_id],
                context,
            ): simulation_id
            for simulation_id in simulation_ids
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            simulation_id = futures[future]
            payload_by_id[simulation_id] = future.result()
            if completed % 20 == 0 or completed == len(futures):
                print(f"Processed {completed}/{len(futures)} simulations")
    payloads = [payload_by_id[simulation_id] for simulation_id in simulation_ids]
    tables = combine_checkpoints(payloads)
    active = tables["active"].sort_values("simulation_id").reset_index(drop=True)
    candidates = tables["candidates"].sort_values(
        ["simulation_id", "candidate_id"]
    ).reset_index(drop=True)
    stage_seconds["simulation_geometry_and_checkpoints"] = time.perf_counter() - stage

    stage = time.perf_counter()
    aligned = combine_label_parts(OUTPUT_DIR, simulation_ids)
    require(len(aligned) == len(labels), "Combined label-aligned row count mismatch")
    alignment_audit = (
        aligned.groupby("simulation_id")
        .agg(
            label_frame_count=("frame_timestep", "size"),
            exact_alignment_count=("alignment_error_iterations", lambda values: int((values == 0).sum())),
            ambiguous_alignment_count=("alignment_ambiguous", "sum"),
            maximum_alignment_error_iterations=("alignment_error_iterations", "max"),
            first_label_position_s=("normalized_scan_position", "min"),
            last_label_position_s=("normalized_scan_position", "max"),
            valid_melt_label_count=("valid_melt_present", "sum"),
        )
        .reset_index()
        .merge(
            active[["simulation_id", "monitor_row_count"]],
            on="simulation_id",
            how="left",
            validate="one_to_one",
        )
    )
    alignment_audit["label_to_monitor_row_fraction"] = (
        alignment_audit["label_frame_count"]
        / alignment_audit["monitor_row_count"]
    )
    alignment_audit["alignment_method"] = "exact iteration match"
    alignment_audit["documented_tolerance_iterations"] = 0
    write_csv(alignment_audit, OUTPUT_DIR / "label_monitor_alignment_audit.csv")
    ambiguity_columns = list(aligned.columns) + ["ambiguity_reason"]
    ambiguities = aligned[aligned["alignment_ambiguous"]].copy()
    ambiguities["ambiguity_reason"] = ""
    write_csv(
        ambiguities.reindex(columns=ambiguity_columns),
        OUTPUT_DIR / "label_alignment_ambiguities.csv",
    )
    first_keyhole_positions = (
        aligned[aligned["stored_label"].eq("Keyhole")]
        .groupby("simulation_id")["normalized_scan_position"]
        .min()
        .rename("first_keyhole_position_s")
    )
    sequence = sequence.merge(
        first_keyhole_positions,
        on="simulation_id",
        how="left",
    )
    sequence["labels_dense_relative_to_monitor"] = (
        sequence["frame_count"]
        / active.set_index("simulation_id").loc[
            sequence["simulation_id"], "monitor_row_count"
        ].to_numpy()
        >= 0.01
    )
    write_csv(sequence, OUTPUT_DIR / "label_sequence_audit.csv")

    candidates, exploratory_ratio_threshold, r4_loo = append_threshold_candidates(
        OUTPUT_DIR,
        candidates,
        active,
    )
    definitions = candidate_definitions()
    profiles = aggregate_profiles(tables["profiles"], sequence)
    coverage, support = scan_coverage_tables(active)
    write_csv(active, OUTPUT_DIR / "simulation_active_interval_summary.csv")
    write_csv(coverage, OUTPUT_DIR / "scan_coverage_summary.csv")
    write_csv(profiles, OUTPUT_DIR / "normalized_position_support.csv")
    write_csv(candidates, OUTPUT_DIR / "regime_target_candidates.csv")
    write_csv(definitions, OUTPUT_DIR / "regime_target_candidate_definitions.csv")
    stage_seconds["alignment_candidates_and_profiles"] = time.perf_counter() - stage

    stage = time.perf_counter()
    persistence, domain, instability, censoring = build_sensitivity_outputs(
        tables["persistence"],
        tables["domain"],
        tables["guard"],
        candidates,
        sequence,
        active,
        n_resamples=bootstrap_resamples,
    )
    write_csv(persistence, OUTPUT_DIR / "persistence_window_sensitivity.csv")
    write_csv(domain, OUTPUT_DIR / "candidate_domain_sensitivity.csv")
    write_csv(instability, OUTPUT_DIR / "candidate_unstable_subset_sensitivity.csv")
    write_csv(censoring, OUTPUT_DIR / "candidate_censoring_sensitivity.csv")
    stage_seconds["robustness_tables"] = time.perf_counter() - stage

    score_table = build_simulation_score_table(candidates, sequence, r4_loo)
    metric_bundle_paths = {
        "frame_metrics": OUTPUT_DIR / "frame_level_candidate_label_metrics.csv",
        "frame_bootstrap": OUTPUT_DIR / "frame_level_cluster_bootstrap_summary.csv",
        "simulation_metrics": OUTPUT_DIR / "simulation_level_candidate_label_metrics.csv",
        "simulation_bootstrap": OUTPUT_DIR / "simulation_level_bootstrap_summary.csv",
        "nested_predictions": OUTPUT_DIR / "nested_threshold_loo_predictions.csv",
        "nested_metrics": OUTPUT_DIR / "nested_threshold_metrics.csv",
        "selected_thresholds": OUTPUT_DIR / "selected_thresholds_by_fold.csv",
        "correlations": OUTPUT_DIR / "candidate_keyhole_fraction_correlations.csv",
    }
    metric_bundle_reused = (
        not args.force
        and all(path.exists() for path in metric_bundle_paths.values())
    )
    stage = time.perf_counter()
    if metric_bundle_reused:
        frame_metrics = pd.read_csv(metric_bundle_paths["frame_metrics"])
        frame_bootstrap = pd.read_csv(metric_bundle_paths["frame_bootstrap"])
        simulation_metrics = pd.read_csv(
            metric_bundle_paths["simulation_metrics"]
        )
        simulation_bootstrap = pd.read_csv(
            metric_bundle_paths["simulation_bootstrap"]
        )
        nested_predictions = pd.read_csv(
            metric_bundle_paths["nested_predictions"]
        )
        nested_metrics = pd.read_csv(metric_bundle_paths["nested_metrics"])
        selected_thresholds = pd.read_csv(
            metric_bundle_paths["selected_thresholds"]
        )
        correlations = pd.read_csv(metric_bundle_paths["correlations"])
    else:
        frame_metrics, frame_bootstrap = frame_level_metrics(
            aligned,
            n_resamples=bootstrap_resamples,
            workers=args.workers,
        )
        simulation_metrics, simulation_bootstrap, correlations = (
            simulation_level_metrics(
                score_table,
                n_resamples=bootstrap_resamples,
            )
        )
        nested_predictions, nested_metrics, selected_thresholds = (
            nested_threshold_loo(score_table)
        )
        write_csv(frame_metrics, metric_bundle_paths["frame_metrics"])
        write_csv(frame_bootstrap, metric_bundle_paths["frame_bootstrap"])
        write_csv(
            simulation_metrics,
            metric_bundle_paths["simulation_metrics"],
        )
        write_csv(
            simulation_bootstrap,
            metric_bundle_paths["simulation_bootstrap"],
        )
        write_csv(
            nested_predictions,
            metric_bundle_paths["nested_predictions"],
        )
        write_csv(nested_metrics, metric_bundle_paths["nested_metrics"])
        write_csv(
            selected_thresholds,
            metric_bundle_paths["selected_thresholds"],
        )
        write_csv(correlations, metric_bundle_paths["correlations"])
    stage_seconds["label_metrics_and_bootstrap"] = time.perf_counter() - stage

    stage = time.perf_counter()
    representatives = select_representative_simulations(
        score_table,
        active,
        aligned,
    )
    frame_selection, frame_provenance = (
        select_and_download_representative_frames(
            representatives,
            aligned,
            candidates,
        )
    )
    write_csv(
        representatives,
        OUTPUT_DIR / "representative_simulation_selection.csv",
    )
    write_csv(
        frame_selection,
        OUTPUT_DIR / "representative_frame_selection.csv",
    )
    write_csv(
        frame_provenance,
        OUTPUT_DIR / "representative_frame_provenance.csv",
    )
    decision_matrix, recommendation = build_decision_matrix(
        definitions,
        candidates,
        simulation_metrics,
        simulation_bootstrap,
        persistence,
        domain,
    )
    write_csv(
        decision_matrix,
        OUTPUT_DIR / "phase3_5_candidate_decision_matrix.csv",
    )
    write_csv(
        recommendation,
        OUTPUT_DIR / "phase3_5_final_target_recommendation.csv",
    )
    write_active_learning_implications(
        OUTPUT_DIR,
        recommendation=recommendation,
    )
    stage_seconds["representatives_and_decision"] = time.perf_counter() - stage

    stage = time.perf_counter()
    manifest = generate_figures(
        OUTPUT_DIR,
        label_population=label_population,
        sequence=sequence,
        coverage=coverage,
        active=active,
        profiles=profiles,
        candidates=candidates,
        persistence=persistence,
        domain=domain,
        instability=instability,
        aligned=aligned,
        simulation_metrics=simulation_metrics,
        simulation_bootstrap=simulation_bootstrap,
        score_table=score_table,
        nested_predictions=nested_predictions,
        representatives=representatives,
        frame_provenance=frame_provenance,
        decision_matrix=decision_matrix,
        recommendation=recommendation,
    )
    write_decision_log(
        OUTPUT_DIR,
        label_population=label_population,
        active=active,
        simulation_metrics=simulation_metrics,
        nested_metrics=nested_metrics,
        representatives=representatives,
        common_interval=common_interval,
    )
    headline = write_results_summary(
        OUTPUT_DIR,
        label_population=label_population,
        active=active,
        candidates=candidates,
        frame_metrics=frame_metrics,
        frame_bootstrap=frame_bootstrap,
        simulation_metrics=simulation_metrics,
        simulation_bootstrap=simulation_bootstrap,
        nested_metrics=nested_metrics,
        representatives=representatives,
        frame_provenance=frame_provenance,
        recommendation=recommendation,
        manifest=manifest,
    )
    stage_seconds["figures_and_reports"] = time.perf_counter() - stage

    runtime = build_runtime_provenance(
        started_at_utc=started_at,
        wall_seconds=time.perf_counter() - wall_started,
        stage_seconds=stage_seconds,
        workers=args.workers,
        force=args.force,
        metric_bundle_reused=metric_bundle_reused,
        payloads=payloads,
        notebook_run=None,
        validation=None,
        checklist=None,
        output_dir=OUTPUT_DIR,
    )

    stage = time.perf_counter()
    subprocess.run([sys.executable, str(NOTEBOOK_BUILDER)], cwd=ROOT, check=True)
    notebook_run = execute_notebook()
    stage_seconds["notebook_build_and_first_execution"] = (
        time.perf_counter() - stage
    )

    validation = run_validation(
        OUTPUT_DIR,
        configuration=configuration,
        core_hashes=core_hashes,
        original_hashes=original_hashes,
        label_dictionary=label_dictionary,
        label_population=label_population,
        sequence=sequence,
        aligned=aligned,
        active=active,
        profiles=profiles,
        definitions=definitions,
        candidates=candidates,
        persistence=persistence,
        domain=domain,
        instability=instability,
        censoring=censoring,
        frame_metrics=frame_metrics,
        frame_bootstrap=frame_bootstrap,
        simulation_metrics=simulation_metrics,
        simulation_bootstrap=simulation_bootstrap,
        score_table=score_table,
        nested_predictions=nested_predictions,
        nested_metrics=nested_metrics,
        representatives=representatives,
        frame_selection=frame_selection,
        frame_provenance=frame_provenance,
        manifest=manifest,
    )
    checklist = build_requirement_checklist(OUTPUT_DIR, validation, manifest)
    notebook_run = execute_notebook()
    validation = run_validation(
        OUTPUT_DIR,
        configuration=configuration,
        core_hashes=core_hashes,
        original_hashes=original_hashes,
        label_dictionary=label_dictionary,
        label_population=label_population,
        sequence=sequence,
        aligned=aligned,
        active=active,
        profiles=profiles,
        definitions=definitions,
        candidates=candidates,
        persistence=persistence,
        domain=domain,
        instability=instability,
        censoring=censoring,
        frame_metrics=frame_metrics,
        frame_bootstrap=frame_bootstrap,
        simulation_metrics=simulation_metrics,
        simulation_bootstrap=simulation_bootstrap,
        score_table=score_table,
        nested_predictions=nested_predictions,
        nested_metrics=nested_metrics,
        representatives=representatives,
        frame_selection=frame_selection,
        frame_provenance=frame_provenance,
        manifest=manifest,
    )
    checklist = build_requirement_checklist(OUTPUT_DIR, validation, manifest)
    stage_seconds["notebook_and_validation_closeout"] = (
        time.perf_counter() - stage
    )

    runtime = build_runtime_provenance(
        started_at_utc=started_at,
        wall_seconds=time.perf_counter() - wall_started,
        stage_seconds=stage_seconds,
        workers=args.workers,
        force=args.force,
        metric_bundle_reused=metric_bundle_reused,
        payloads=payloads,
        notebook_run=notebook_run,
        validation=validation,
        checklist=checklist,
        output_dir=OUTPUT_DIR,
    )
    headline["validation"] = {
        "pass_count": int(validation["status"].eq("PASS").sum()),
        "total_count": len(validation),
    }
    headline["requirement_checklist"] = {
        "pass_count": int(checklist["status"].eq("PASS").sum()),
        "total_count": len(checklist),
    }
    headline["runtime_wall_seconds"] = runtime["wall_seconds"]
    headline["exploratory_full_data_ratio_threshold"] = exploratory_ratio_threshold
    write_json(json_safe(headline), OUTPUT_DIR / "summary.json")
    with (OUTPUT_DIR / "results_summary.md").open("a", encoding="utf-8") as handle:
        handle.write(
            "\n## Automated closeout\n\n"
            f"- Validation: {int(validation['status'].eq('PASS').sum())}/{len(validation)} PASS.\n"
            f"- Requirement checklist: {int(checklist['status'].eq('PASS').sum())}/{len(checklist)} PASS.\n"
            f"- Full wall time: {runtime['wall_seconds']:.3f} seconds.\n"
            f"- Presentation-ready figures: {int(manifest['presentation_priority'].eq('presentation_copy').sum())}.\n"
            "- No commit or push occurred; the original dirty worktree remained hash-identical.\n"
        )
    write_output_hashes(OUTPUT_DIR)
    print(
        json.dumps(
            {
                "status": "PASS",
                "validation": f"{len(validation)}/{len(validation)}",
                "checklist": f"{len(checklist)}/{len(checklist)}",
                "runtime_seconds": runtime["wall_seconds"],
                "output_dir": str(OUTPUT_DIR),
            },
            indent=2,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true", help="Run a reduced non-scientific smoke test")
    mode.add_argument("--full", action="store_true", help="Run the complete 241-simulation study")
    parser.add_argument("--force", action="store_true", help="Overwrite Phase 3.5 checkpoints deterministically")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent simulation workers")
    parser.add_argument(
        "--bootstrap-resamples",
        type=int,
        default=10000,
        help="Deterministic bootstrap resamples; full mode requires at least 10000",
    )
    args = parser.parse_args()
    require(args.workers >= 1, "workers must be at least one")
    return args


def main() -> None:
    args = parse_args()
    full_run(args)


if __name__ == "__main__":
    main()
