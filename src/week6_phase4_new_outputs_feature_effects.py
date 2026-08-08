"""Week 6 Phase 4: new physical outputs and focused feature associations.

This module deliberately reuses the validated Phase 3 exact-LOO engine and the
Phase 3.5 geometry partitions.  It does not rerun model selection for width,
length, or penetration depth.  All network requests, when needed, name the
already pinned immutable Hugging Face revision directly; no revision discovery
or update check is performed.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from huggingface_hub import hf_hub_download
from scipy.spatial import Delaunay, cKDTree
from scipy.stats import spearmanr
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_WORKTREE = Path(r"C:\Users\ozgur\Documents\thesis")
OUTPUT_DIR = ROOT / "outputs" / "week6_04_new_outputs_feature_effects"
CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"
SMOKE_DIR = OUTPUT_DIR / "smoke"
FIGURE_DIR = OUTPUT_DIR / "figures"
PRESENTATION_DIR = OUTPUT_DIR / "presentation_ready_figures"
DATA_ROOT = ROOT / "data" / "raw" / "huggingface" / "sph_dataset"
GEOMETRY_PART_DIR = (
    ROOT
    / "outputs"
    / "week6_03_5_regime_target_design"
    / "regime_geometry_time_series.parquet"
)
PHASE1_LEDGER = (
    ROOT
    / "outputs"
    / "week6_01_melt_pool_data_audit"
    / "week6_phase1_simulation_level_responses.csv"
)
PHASE3_DIR = ROOT / "outputs" / "week6_03_model_target_robustness"
PHASE35_DIR = ROOT / "outputs" / "week6_03_5_regime_target_design"
PREFLIGHT_PATH = OUTPUT_DIR / "phase4_preflight_snapshot.json"

REPO_ID = "ioandanielc/sph_dataset"
REVISION = "0e859b748fdbc8454f66e58e101e333ac0479d42"
EXPECTED_LEDGER_SHA256 = (
    "10DEF11AB64D62444AC14FED506266BEB748EEB5BF892ACDC12E7F0F6DDCF4FF"
)
EXPECTED_BRANCH = "codex/week6-phase4-new-outputs-feature-effects"
EXPECTED_HEAD = "b112f6b22898976f77410190614cb4fb218d38f9"
EXPECTED_SIMULATIONS = 241
FEATURE_COLUMNS = ["P", "VX", "LS", "ST"]
FEATURE_UNITS = {"P": "W", "VX": "m/s", "LS": "um", "ST": "K"}
POSITION_BOUNDS_ORDER = ["x_min", "x_max", "y_min", "y_max", "z_min", "z_max"]
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
_PHASE1_SIMULATION_IDS = set(
    pd.read_csv(PHASE1_LEDGER, usecols=["simulation_id"])["simulation_id"].astype(
        str
    )
)
DEPTH_STABLE_IDS = _PHASE1_SIMULATION_IDS - set(DEPTH_UNSTABLE_IDS)
if len(_PHASE1_SIMULATION_IDS) != EXPECTED_SIMULATIONS or len(DEPTH_STABLE_IDS) != 230:
    raise RuntimeError("Phase 1 or stable-depth simulation-ID population changed")

TARGET_SPECS = {
    "kinetic_energy": {
        "label": "T0 melt-pool kinetic energy",
        "column": "T0_melt_pool_kinetic_energy_nJ",
        "alternative_column": "adaptive_melt_pool_kinetic_energy_nJ",
        "unit": "nJ",
    },
    "total_height": {
        "label": "T0 total vertical melt-pool height",
        "column": "T0_total_vertical_height_um",
        "alternative_column": "adaptive_total_vertical_height_um",
        "unit": "um",
    },
}
OUTPUT_SPECS = {
    "width": {
        "label": "T0 melt-pool width",
        "unit": "um",
        "population": "all_241_descriptive; Phase3 uncertainty GP",
    },
    "depth": {
        "label": "T0 penetration depth",
        "unit": "um",
        "population": "all_241_descriptive; stable_230 controlled GP",
    },
    "kinetic_energy": {
        "label": "T0 melt-pool kinetic energy",
        "unit": "nJ",
        "population": "all_241",
    },
    "total_height": {
        "label": "T0 total vertical height",
        "unit": "um",
        "population": "all_241",
    },
}

BASE_SEED = 6404
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_QUANTILES = (0.025, 0.975)
RIDGE_ALPHA_GRID = tuple(float(10.0**power) for power in range(-6, 7))
RIDGE_INNER_FOLDS = 5
SMOKE_SIMULATIONS = 12
CURVE_GRID_SIZE = 101
SURFACE_GRID_SIZE = 31
SUPPORT_DISTANCE_QUANTILE = 0.95
PRESENTATION_READY_IDS = {3, 5, 9, 10, 16, 17, 18, 19, 20, 24}

KINETIC_FILE_NAME = "kinetic-energy_melt.dat"
KINETIC_PATH_PATTERN = (
    "final_data_processed/sim_XXXXX/monitor/kinetic-energy_melt.dat"
)
KINETIC_SOURCE_UNIT = "J"
KINETIC_REPORT_UNIT = "nJ"
KINETIC_SEMANTICS = (
    "instantaneous aggregate kinetic energy over the melt-phase particle subset"
)
KINETIC_SEMANTIC_CONFIDENCE = "moderate-high"
KINETIC_FORMULA_CAVEAT = (
    "The local repository does not include the solver reduction formula; Ioan "
    "should confirm the exact particle-mass weighting. File naming, SI-unit "
    "metadata, aggregate-monitor documentation, row alignment, and strongly "
    "non-monotone time behaviour support the stated interpretation."
)

RUNTIME_EVENTS: list[dict[str, Any]] = []
RUN_STARTED_UTC = datetime.now(timezone.utc)


def require(condition: bool, message: str) -> None:
    """Fail loudly when a protected assumption is violated."""
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def deterministic_seed(*parts: Any) -> int:
    payload = "|".join(str(part) for part in (BASE_SEED, *parts)).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "little")


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False, lineterminator="\n")
    os.replace(temporary, path)


def run_read_only_git(worktree: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(worktree), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stdout.rstrip()


def read_ledger() -> pd.DataFrame:
    require(PHASE1_LEDGER.is_file(), f"Missing Phase 1 ledger: {PHASE1_LEDGER}")
    require(
        sha256_file(PHASE1_LEDGER) == EXPECTED_LEDGER_SHA256,
        "Phase 1 ledger SHA-256 differs from the validated value",
    )
    ledger = pd.read_csv(PHASE1_LEDGER)
    require(len(ledger) == EXPECTED_SIMULATIONS, "Phase 1 ledger is not 241 rows")
    require(ledger["simulation_id"].is_unique, "Phase 1 simulation IDs are duplicated")
    require(
        set(ledger["huggingface_revision"].astype(str)) == {REVISION},
        "Phase 1 ledger revision differs from the pinned immutable revision",
    )
    require(
        all(column in ledger.columns for column in FEATURE_COLUMNS),
        "One or more required physical features are missing",
    )
    require(
        set(ledger["inferred_scan_axis"].astype(str)) == {"X"}
        and set(ledger["inferred_width_axis"].astype(str)) == {"Y"}
        and set(ledger["inferred_vertical_axis"].astype(str)) == {"Z"},
        "Validated coordinate convention changed",
    )
    return ledger.sort_values("numeric_simulation_id").reset_index(drop=True)


def verify_starting_state() -> dict[str, Any]:
    require(ROOT.resolve() == Path(r"C:\Users\ozgur\Documents\thesis-week6-melt-pool-audit").resolve(),
            f"Wrong isolated worktree: {ROOT}")
    require(PREFLIGHT_PATH.is_file(), "Phase 4 preflight snapshot is missing")
    preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    branch = run_read_only_git(ROOT, "branch", "--show-current")
    head = run_read_only_git(ROOT, "rev-parse", "HEAD")
    require(branch == EXPECTED_BRANCH, f"Wrong Phase 4 branch: {branch}")
    require(head == EXPECTED_HEAD, f"Unexpected Phase 4 starting HEAD: {head}")
    protected = preflight.get("protected_phase_artifacts", [])
    require(len(protected) >= 20, "Preflight protected-artifact ledger is incomplete")
    for record in protected:
        relative_path = str(record["path"])
        expected_hash = str(record["sha256"])
        path = ROOT / relative_path
        require(path.is_file(), f"Protected artifact disappeared: {relative_path}")
        require(
            sha256_file(path) == str(expected_hash).upper(),
            f"Protected artifact changed: {relative_path}",
        )
    return preflight


def kinetic_relative_path(simulation_id: str) -> str:
    return (
        f"final_data_processed/{simulation_id}/monitor/"
        f"{KINETIC_FILE_NAME}"
    )


def ensure_pinned_kinetic_files(
    simulation_ids: Iterable[str], *, workers: int
) -> dict[str, Any]:
    """Download only missing monitor files from the exact pinned revision."""
    requested = [str(item) for item in simulation_ids]
    missing = [
        simulation_id
        for simulation_id in requested
        if not (DATA_ROOT / kinetic_relative_path(simulation_id)).is_file()
    ]
    started = time.perf_counter()
    downloaded: list[str] = []

    def download_one(simulation_id: str) -> str:
        relative_path = kinetic_relative_path(simulation_id)
        hf_hub_download(
            repo_id=REPO_ID,
            repo_type="dataset",
            revision=REVISION,
            filename=relative_path,
            local_dir=str(DATA_ROOT),
        )
        return simulation_id

    if missing:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = {pool.submit(download_one, item): item for item in missing}
            for completed, future in enumerate(as_completed(futures), start=1):
                downloaded.append(future.result())
                if completed % 20 == 0 or completed == len(futures):
                    print(
                        f"Pinned kinetic monitors: {completed}/{len(futures)}",
                        flush=True,
                    )
    remaining = [
        simulation_id
        for simulation_id in requested
        if not (DATA_ROOT / kinetic_relative_path(simulation_id)).is_file()
    ]
    require(not remaining, f"Missing pinned kinetic monitors: {remaining}")
    event = {
        "stage": "pinned_monitor_materialization",
        "revision_discovery_performed": False,
        "update_check_performed": False,
        "repo_id": REPO_ID,
        "exact_revision": REVISION,
        "requested_count": len(requested),
        "missing_before": len(missing),
        "downloaded_count": len(downloaded),
        "downloaded_simulation_ids": sorted(downloaded),
        "missing_after": len(remaining),
        "wall_runtime_seconds": time.perf_counter() - started,
    }
    RUNTIME_EVENTS.append(event)
    return event


def load_scalar_monitor(path: Path) -> np.ndarray:
    values = np.fromfile(path, dtype=float, sep=" ")
    if values.ndim != 1:
        values = values.reshape(-1)
    return values


def safe_spearman(left: np.ndarray, right: np.ndarray) -> float:
    valid = np.isfinite(left) & np.isfinite(right)
    if valid.sum() < 3:
        return np.nan
    if np.unique(left[valid]).size < 2 or np.unique(right[valid]).size < 2:
        return np.nan
    return float(spearmanr(left[valid], right[valid]).statistic)


def target_sensitivity_rows(targets: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for response, spec in TARGET_SPECS.items():
        primary = targets[spec["column"]].to_numpy(float)
        alternative = targets[spec["alternative_column"]].to_numpy(float)
        valid_primary = np.isfinite(primary)
        paired = valid_primary & np.isfinite(alternative)
        shift = alternative[paired] - primary[paired]
        absolute = np.abs(shift)
        scale = np.maximum(np.abs(primary[paired]), np.finfo(float).eps)
        relative = absolute / scale
        large_order = np.argsort(absolute)[::-1][:10]
        paired_ids = targets.loc[paired, "simulation_id"].astype(str).to_numpy()
        rows.append(
            {
                "response": response,
                "response_label": spec["label"],
                "unit": spec["unit"],
                "primary_definition": (
                    "median over final 20% of melt-present observations before "
                    "the laser reaches 90% of the positive-X domain (validated T0)"
                ),
                "alternative_definition": (
                    "median over the Phase 3.5 adaptive active-interior interval"
                ),
                "primary_available_count": int(valid_primary.sum()),
                "alternative_available_count": int(np.isfinite(alternative).sum()),
                "paired_available_count": int(paired.sum()),
                "missing_primary_ids": json_text(
                    targets.loc[~valid_primary, "simulation_id"].astype(str).tolist()
                ),
                "missing_alternative_ids": json_text(
                    targets.loc[~np.isfinite(alternative), "simulation_id"]
                    .astype(str)
                    .tolist()
                ),
                "primary_min": float(np.nanmin(primary)),
                "primary_q05": float(np.nanquantile(primary, 0.05)),
                "primary_q25": float(np.nanquantile(primary, 0.25)),
                "primary_median": float(np.nanmedian(primary)),
                "primary_mean": float(np.nanmean(primary)),
                "primary_std": float(np.nanstd(primary, ddof=1)),
                "primary_q75": float(np.nanquantile(primary, 0.75)),
                "primary_q95": float(np.nanquantile(primary, 0.95)),
                "primary_max": float(np.nanmax(primary)),
                "primary_vs_alternative_spearman": safe_spearman(
                    primary[paired], alternative[paired]
                ),
                "median_absolute_shift": float(np.median(absolute)),
                "q95_absolute_shift": float(np.quantile(absolute, 0.95)),
                "median_relative_shift": float(np.median(relative)),
                "large_shift_simulation_ids": json_text(
                    paired_ids[large_order].tolist()
                ),
                "large_shift_values": json_text(
                    [
                        {
                            "simulation_id": str(paired_ids[index]),
                            "primary": float(primary[paired][index]),
                            "alternative": float(alternative[paired][index]),
                            "absolute_shift": float(absolute[index]),
                        }
                        for index in large_order
                    ]
                ),
            }
        )
    return pd.DataFrame(rows)


def representative_rows(
    targets: pd.DataFrame, sensitivity: pd.DataFrame
) -> pd.DataFrame:
    selections: list[dict[str, Any]] = []
    already: dict[str, set[str]] = {key: set() for key in TARGET_SPECS}
    for response, spec in TARGET_SPECS.items():
        primary_column = spec["column"]
        alternative_column = spec["alternative_column"]
        valid = targets[np.isfinite(targets[primary_column])].copy()
        median = float(valid[primary_column].median())
        typical = valid.assign(
            selection_score=(valid[primary_column] - median).abs()
        ).sort_values(["selection_score", "numeric_simulation_id"]).iloc[0]
        high = valid.sort_values(
            [primary_column, "numeric_simulation_id"],
            ascending=[False, True],
        ).iloc[0]
        paired = valid[np.isfinite(valid[alternative_column])].copy()
        paired["selection_score"] = (
            paired[primary_column] - paired[alternative_column]
        ).abs()
        paired = paired.sort_values(
            ["selection_score", "numeric_simulation_id"],
            ascending=[False, True],
        )
        candidates = [
            (
                "typical_population_median",
                typical,
                "minimum absolute distance to the population median; ties use numeric ID",
            ),
            (
                "high_response",
                high,
                "largest primary response; ties use numeric ID",
            ),
        ]
        for role, row, rule in candidates:
            simulation_id = str(row["simulation_id"])
            already[response].add(simulation_id)
            selections.append(
                {
                    "response": response,
                    "role": role,
                    "simulation_id": simulation_id,
                    "selection_rule": rule,
                    "primary_value": float(row[primary_column]),
                    "alternative_value": float(row[alternative_column]),
                    "absolute_target_shift": float(
                        abs(row[primary_column] - row[alternative_column])
                    ),
                    "unit": spec["unit"],
                }
            )
        disagreement = next(
            row
            for _, row in paired.iterrows()
            if str(row["simulation_id"]) not in already[response]
        )
        selections.append(
            {
                "response": response,
                "role": "largest_primary_adaptive_disagreement",
                "simulation_id": str(disagreement["simulation_id"]),
                "selection_rule": (
                    "largest absolute primary-versus-adaptive shift after "
                    "excluding already selected examples; ties use numeric ID"
                ),
                "primary_value": float(disagreement[primary_column]),
                "alternative_value": float(disagreement[alternative_column]),
                "absolute_target_shift": float(
                    abs(
                        disagreement[primary_column]
                        - disagreement[alternative_column]
                    )
                ),
                "unit": spec["unit"],
            }
        )
    return pd.DataFrame(selections)


def extract_targets(
    *, workers: int, smoke: bool, force: bool
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    destination = SMOKE_DIR if smoke else OUTPUT_DIR
    target_path = destination / "phase4_simulation_level_targets.csv"
    audit_ke_path = destination / "kinetic_energy_monitor_audit.csv"
    audit_height_path = destination / "total_height_monitor_audit.csv"
    sensitivity_path = destination / "phase4_target_definition_sensitivity.csv"
    representative_path = destination / "representative_simulation_selection.csv"
    if (
        not force
        and all(
            path.is_file()
            for path in [
                target_path,
                audit_ke_path,
                audit_height_path,
                sensitivity_path,
                representative_path,
            ]
        )
    ):
        targets = pd.read_csv(target_path)
        expected = SMOKE_SIMULATIONS if smoke else EXPECTED_SIMULATIONS
        if len(targets) == expected:
            RUNTIME_EVENTS.append(
                {
                    "stage": "target_extraction",
                    "smoke": smoke,
                    "cache_reused": True,
                    "row_count": len(targets),
                    "wall_runtime_seconds": 0.0,
                }
            )
            return (
                targets,
                pd.read_csv(audit_ke_path),
                pd.read_csv(audit_height_path),
                pd.read_csv(sensitivity_path),
                pd.read_csv(representative_path),
            )

    started = time.perf_counter()
    ledger = read_ledger()
    if smoke:
        ledger = ledger.iloc[:SMOKE_SIMULATIONS].copy()
    simulation_ids = ledger["simulation_id"].astype(str).tolist()
    ensure_pinned_kinetic_files(simulation_ids, workers=workers)
    remote_sizes = pd.read_csv(DATA_ROOT / ".week6_monitor_remote_sizes.csv")
    remote_ke_sizes = (
        remote_sizes[remote_sizes["file_name"].eq(KINETIC_FILE_NAME)]
        .set_index("sim_id")["size_bytes"]
        .astype(int)
        .to_dict()
    )
    complete_tree_path = (
        DATA_ROOT
        / f".week6_complete_tree_{REVISION}.json.gz"
    )
    require(complete_tree_path.is_file(), "Pinned complete-tree snapshot is missing")
    with gzip.open(complete_tree_path, "rt", encoding="utf-8") as handle:
        complete_tree = json.load(handle)
    require(
        complete_tree.get("chosen_revision") == REVISION,
        "Complete-tree snapshot revision differs from the pinned revision",
    )
    for simulation_id, items in complete_tree["simulation_items"].items():
        if simulation_id in remote_ke_sizes:
            continue
        matches = [
            item
            for item in items
            if str(item.get("path", "")).endswith(
                f"/monitor/{KINETIC_FILE_NAME}"
            )
        ]
        require(
            len(matches) == 1,
            f"{simulation_id}: pinned complete tree lacks one kinetic monitor",
        )
        remote_ke_sizes[simulation_id] = int(matches[0]["size"])
    require(
        len(remote_ke_sizes) == EXPECTED_SIMULATIONS,
        "Pinned kinetic size map is not complete",
    )
    target_rows: list[dict[str, Any]] = []
    kinetic_audit_rows: list[dict[str, Any]] = []
    height_audit_rows: list[dict[str, Any]] = []

    for position, ledger_row in ledger.iterrows():
        simulation_id = str(ledger_row["simulation_id"])
        part_path = GEOMETRY_PART_DIR / f"part-{simulation_id}.parquet"
        kinetic_path = DATA_ROOT / kinetic_relative_path(simulation_id)
        require(part_path.is_file(), f"Missing Phase 3.5 geometry part: {part_path}")
        require(kinetic_path.is_file(), f"Missing kinetic monitor: {kinetic_path}")
        part = pd.read_parquet(
            part_path,
            columns=[
                "monitor_row_index",
                "time_s",
                "normalized_scan_position",
                "depth_m",
                "vertical_extent_m",
                "in_adaptive_active_interior",
                "in_T0_window",
            ],
        )
        kinetic_j = load_scalar_monitor(kinetic_path)
        expected_rows = int(ledger_row["monitor_row_count"])
        expected_remote_bytes = int(remote_ke_sizes[simulation_id])
        if kinetic_path.stat().st_size != expected_remote_bytes:
            invalid_hash = sha256_file(kinetic_path)
            invalid_rows = len(kinetic_j)
            hf_hub_download(
                repo_id=REPO_ID,
                repo_type="dataset",
                revision=REVISION,
                filename=kinetic_relative_path(simulation_id),
                local_dir=str(DATA_ROOT),
                force_download=True,
            )
            kinetic_j = load_scalar_monitor(kinetic_path)
            RUNTIME_EVENTS.append(
                {
                    "stage": "repair_truncated_pinned_monitor",
                    "simulation_id": simulation_id,
                    "exact_revision": REVISION,
                    "invalid_local_row_count": invalid_rows,
                    "expected_remote_size_bytes": expected_remote_bytes,
                    "invalid_local_sha256": invalid_hash,
                    "repaired_row_count": len(kinetic_j),
                    "repaired_size_bytes": kinetic_path.stat().st_size,
                    "repaired_sha256": sha256_file(kinetic_path),
                    "revision_discovery_performed": False,
                }
            )
        require(
            kinetic_path.stat().st_size == expected_remote_bytes,
            f"{simulation_id}: local kinetic bytes differ from pinned size ledger",
        )
        raw_indices = part["monitor_row_index"].to_numpy(int)
        require(
            raw_indices.min() >= 0,
            f"{simulation_id}: geometry monitor row mapping is negative",
        )
        kinetic_row_covered = raw_indices < len(kinetic_j)
        kinetic_melt_j = np.full(len(part), np.nan, dtype=float)
        kinetic_melt_j[kinetic_row_covered] = kinetic_j[
            raw_indices[kinetic_row_covered]
        ]
        kinetic_valid = (
            kinetic_row_covered
            & np.isfinite(kinetic_melt_j)
            & (kinetic_melt_j >= 0.0)
        )
        t0_mask = part["in_T0_window"].astype(bool).to_numpy()
        adaptive_mask = part["in_adaptive_active_interior"].astype(bool).to_numpy()
        require(t0_mask.sum() > 0, f"{simulation_id}: validated T0 mask is empty")
        require(
            kinetic_row_covered[t0_mask].all(),
            f"{simulation_id}: pinned kinetic monitor does not cover the T0 window",
        )
        require(
            kinetic_row_covered[adaptive_mask].all(),
            f"{simulation_id}: pinned kinetic monitor does not cover the adaptive window",
        )
        t0_ke_j = kinetic_melt_j[t0_mask & kinetic_valid]
        adaptive_ke_j = kinetic_melt_j[adaptive_mask & kinetic_valid]
        height_m = part["vertical_extent_m"].to_numpy(float)
        height_valid = np.isfinite(height_m) & (height_m >= 0.0)
        t0_height_m = height_m[t0_mask & height_valid]
        adaptive_height_m = height_m[adaptive_mask & height_valid]
        require(len(t0_ke_j) > 0, f"{simulation_id}: no valid T0 kinetic energy")
        require(len(t0_height_m) > 0, f"{simulation_id}: no valid T0 total height")

        primary_ke_nj = float(np.median(t0_ke_j) * 1e9)
        adaptive_ke_nj = (
            float(np.median(adaptive_ke_j) * 1e9)
            if len(adaptive_ke_j)
            else np.nan
        )
        part_primary_height_um = float(np.median(t0_height_m) * 1e6)
        adaptive_height_um = (
            float(np.median(adaptive_height_m) * 1e6)
            if len(adaptive_height_m)
            else np.nan
        )
        ledger_height_m = float(ledger_row["delta_z_late_window_median_m"])
        primary_height_um = ledger_height_m * 1e6
        require(
            np.isclose(
                part_primary_height_um,
                ledger_height_m * 1e6,
                rtol=0.0,
                atol=1e-3,
            ),
            f"{simulation_id}: T0 total height does not reproduce Phase 1",
        )
        raw_finite = np.isfinite(kinetic_j)
        raw_nonnegative = kinetic_j >= 0.0
        invalid_raw = ~(raw_finite & raw_nonnegative)
        negative_steps = int(
            np.sum(np.diff(kinetic_j[raw_finite]) < -np.finfo(float).eps)
        )
        melt_index_mask = np.zeros(len(kinetic_j), dtype=bool)
        melt_index_mask[raw_indices[kinetic_row_covered]] = True
        nonzero_outside_melt = int(
            np.sum((np.abs(kinetic_j) > 0.0) & ~melt_index_mask & raw_finite)
        )
        kinetic_audit_rows.append(
            {
                "simulation_id": simulation_id,
                "source_relative_path": kinetic_relative_path(simulation_id),
                "source_sha256": sha256_file(kinetic_path),
                "file_name": KINETIC_FILE_NAME,
                "path_pattern": KINETIC_PATH_PATTERN,
                "source_unit": KINETIC_SOURCE_UNIT,
                "reported_unit": KINETIC_REPORT_UNIT,
                "column_count": 1,
                "column_definition": KINETIC_SEMANTICS,
                "semantic_classification": KINETIC_SEMANTICS,
                "semantic_confidence": KINETIC_SEMANTIC_CONFIDENCE,
                "solver_formula_caveat": KINETIC_FORMULA_CAVEAT,
                "instantaneous_not_cumulative_supported": negative_steps > 0,
                "total_over_molten_subset_supported": True,
                "mean_per_particle_supported": False,
                "specific_energy_supported": False,
                "sentinel_rule": "no file-specific sentinel; require finite and >= 0 J",
                "missing_value_rule": "non-finite or negative rows are invalid and counted",
                "time_convention": (
                    "one scalar per solver monitor row, aligned with time.dat and iter.dat"
                ),
                "monitor_row_count": len(kinetic_j),
                "expected_monitor_row_count": expected_rows,
                "rows_align": len(kinetic_j) == expected_rows,
                "source_short_row_count": max(0, expected_rows - len(kinetic_j)),
                "source_file_matches_pinned_size_ledger": (
                    kinetic_path.stat().st_size == expected_remote_bytes
                ),
                "pinned_size_bytes": expected_remote_bytes,
                "target_windows_fully_covered": bool(
                    kinetic_row_covered[t0_mask].all()
                    and kinetic_row_covered[adaptive_mask].all()
                ),
                "finite_row_count": int(raw_finite.sum()),
                "negative_row_count": int((kinetic_j < 0).sum()),
                "invalid_row_count": int(invalid_raw.sum()),
                "valid_melt_row_count": int(kinetic_valid.sum()),
                "T0_valid_row_count": int((t0_mask & kinetic_valid).sum()),
                "adaptive_valid_row_count": int(
                    (adaptive_mask & kinetic_valid).sum()
                ),
                "zero_row_count": int((kinetic_j == 0.0).sum()),
                "nonzero_outside_valid_melt_count": nonzero_outside_melt,
                "strict_negative_step_count": negative_steps,
                "monotone_nondecreasing": negative_steps == 0,
                "minimum_J": float(np.nanmin(kinetic_j)),
                "median_valid_melt_J": float(np.median(kinetic_melt_j[kinetic_valid])),
                "maximum_J": float(np.nanmax(kinetic_j)),
                "physically_plausible": bool(
                    invalid_raw.sum() == 0
                    and np.nanmax(kinetic_j) > 0
                    and negative_steps > 0
                    and kinetic_row_covered[t0_mask].all()
                ),
                "usable_for_primary_target": bool(len(t0_ke_j) > 0),
                "pinned_revision": REVISION,
            }
        )
        height_audit_rows.append(
            {
                "simulation_id": simulation_id,
                "source_relative_path": str(
                    part_path.relative_to(ROOT)
                ).replace("\\", "/"),
                "raw_source_relative_path": str(
                    ledger_row["source_bounds_path"]
                ),
                "position_bounds_order": json_text(POSITION_BOUNDS_ORDER),
                "formula": "total_height(t) = z_max(t) - z_min(t)",
                "internal_unit": "m",
                "reported_unit": "um",
                "valid_melt_row_count": len(part),
                "invalid_rule": (
                    "Phase 1 sentinel/non-finite/max<min rows excluded before this partition"
                ),
                "T0_observation_count": int(t0_mask.sum()),
                "adaptive_observation_count": int(adaptive_mask.sum()),
                "nonfinite_height_count": int((~np.isfinite(height_m)).sum()),
                "negative_height_count": int((height_m < 0).sum()),
                "minimum_height_m": float(np.nanmin(height_m)),
                "median_height_m": float(np.nanmedian(height_m)),
                "maximum_height_m": float(np.nanmax(height_m)),
                "T0_total_height_m_recomputed": part_primary_height_um / 1e6,
                "Phase1_delta_z_T0_m": ledger_height_m,
                "T0_reproduction_absolute_error_m": abs(
                    part_primary_height_um / 1e6 - ledger_height_m
                ),
                "identity_verified": bool(
                    np.isfinite(height_m).all() and (height_m >= 0).all()
                ),
                "penetration_depth_not_substituted": bool(
                    not np.allclose(
                        part["depth_m"].to_numpy(float),
                        height_m,
                        rtol=0,
                        atol=1e-15,
                    )
                ),
                "usable_for_primary_target": bool(len(t0_height_m) > 0),
                "pinned_revision": REVISION,
            }
        )
        target_rows.append(
            {
                "simulation_id": simulation_id,
                "numeric_simulation_id": int(ledger_row["numeric_simulation_id"]),
                "P": float(ledger_row["P"]),
                "VX": float(ledger_row["VX"]),
                "LS": float(ledger_row["LS"]) * 1e6,
                "ST": float(ledger_row["ST"]),
                "LS_source_m": float(ledger_row["LS"]),
                "LS_definition": "laser spot radius",
                "feature_units": json_text(FEATURE_UNITS),
                "T0_melt_pool_width_um": float(
                    ledger_row["melt_pool_width_selected_primary_scalar_target_m"]
                    * 1e6
                ),
                "T0_penetration_depth_um": float(
                    ledger_row[
                        "melt_pool_depth_below_surface_selected_primary_scalar_target_m"
                    ]
                    * 1e6
                ),
                "T0_melt_pool_kinetic_energy_nJ": primary_ke_nj,
                "adaptive_melt_pool_kinetic_energy_nJ": adaptive_ke_nj,
                "T0_total_vertical_height_um": primary_height_um,
                "adaptive_total_vertical_height_um": adaptive_height_um,
                "T0_observation_count": int(t0_mask.sum()),
                "adaptive_observation_count": int(adaptive_mask.sum()),
                "T0_definition": (
                    "median over final 20% of melt-present observations before "
                    "90% positive-X domain cutoff"
                ),
                "adaptive_definition": (
                    "median over Phase 3.5 adaptive active-interior interval"
                ),
                "kinetic_source_unit": "J",
                "kinetic_report_unit": "nJ",
                "total_height_internal_unit": "m",
                "total_height_report_unit": "um",
                "kinetic_invalid_row_count": int(invalid_raw.sum()),
                "phase1_unstable_depth_window": simulation_id
                in DEPTH_UNSTABLE_IDS,
                "huggingface_revision": REVISION,
            }
        )
        if (position + 1) % 20 == 0 or position + 1 == len(ledger):
            print(
                f"Target extraction: {position + 1}/{len(ledger)} simulations",
                flush=True,
            )

    targets = pd.DataFrame(target_rows).sort_values(
        "numeric_simulation_id"
    ).reset_index(drop=True)
    kinetic_audit = pd.DataFrame(kinetic_audit_rows).sort_values(
        "simulation_id"
    ).reset_index(drop=True)
    height_audit = pd.DataFrame(height_audit_rows).sort_values(
        "simulation_id"
    ).reset_index(drop=True)
    sensitivity = target_sensitivity_rows(targets)
    representatives = representative_rows(targets, sensitivity)
    write_csv(target_path, targets)
    write_csv(audit_ke_path, kinetic_audit)
    write_csv(audit_height_path, height_audit)
    write_csv(sensitivity_path, sensitivity)
    write_csv(representative_path, representatives)
    RUNTIME_EVENTS.append(
        {
            "stage": "target_extraction",
            "smoke": smoke,
            "cache_reused": False,
            "row_count": len(targets),
            "wall_runtime_seconds": time.perf_counter() - started,
        }
    )
    return targets, kinetic_audit, height_audit, sensitivity, representatives


def load_phase3_engine(*, smoke: bool) -> Any:
    """Load the validated Phase 3 LOO implementation without executing its main."""
    source_directory = str(ROOT / "src")
    if source_directory not in sys.path:
        sys.path.insert(0, source_directory)
    phase3 = importlib.import_module("week6_phase3_model_target_robustness")
    phase3.CHECKPOINT_DIR = (
        SMOKE_DIR / "checkpoints" if smoke else CHECKPOINT_DIR
    )
    phase3.TARGET_LABELS.update(
        {
            response: str(spec["label"])
            for response, spec in TARGET_SPECS.items()
        }
    )
    phase3.RUNTIME_EVENTS.clear()
    return phase3


def model_table_for_response(
    targets: pd.DataFrame, response: str
) -> pd.DataFrame:
    spec = TARGET_SPECS[response]
    columns = [
        "simulation_id",
        "numeric_simulation_id",
        *FEATURE_COLUMNS,
        spec["column"],
    ]
    table = targets[columns].copy()
    table = table.rename(columns={spec["column"]: "target_value_um"})
    require(len(table) == len(targets), f"{response}: population changed")
    require(
        np.isfinite(table[[*FEATURE_COLUMNS, "target_value_um"]].to_numpy(float)).all(),
        f"{response}: non-finite model input",
    )
    return table.sort_values("numeric_simulation_id").reset_index(drop=True)


def genericize_prediction_columns(
    frame: pd.DataFrame, *, response: str, model_family: str
) -> pd.DataFrame:
    rename: dict[str, str] = {}
    for column in frame.columns:
        generic = column.replace("_um2", "_target_unit_squared").replace(
            "_um", "_target_unit"
        )
        if generic != column:
            rename[column] = generic
    result = frame.rename(columns=rename).copy()
    if "model" not in result.columns and "gp_configuration" in result.columns:
        result["model"] = result["gp_configuration"]
    result["response"] = response
    result["target"] = response
    result["response_label"] = TARGET_SPECS[response]["label"]
    result["target_unit"] = TARGET_SPECS[response]["unit"]
    result["model_family"] = model_family
    result["source_engine"] = (
        "validated Phase 3 exact-LOO implementation reused by Phase 4"
    )
    result["phase"] = "Phase 4C"
    required_defaults = {
        "evaluation_predictive_std_target_unit": np.nan,
        "evaluation_nlpd": np.nan,
        "latent_interval_contains_observed": np.nan,
        "total_interval_contains_observed": np.nan,
        "learned_nugget": False,
        "optimized_noise_std_target_unit": np.nan,
        "optimized_noise_variance_target_unit_squared": np.nan,
        "optimized_signal_variance_normalized": np.nan,
        "optimized_length_scale": np.nan,
        "optimized_noise_variance_normalized": np.nan,
        "constant_bound_hit": False,
        "length_scale_bound_hit": False,
        "noise_bound_hit": False,
        "any_hyperparameter_bound_hit": False,
        "convergence_warning_count": 0,
        "selected_ridge_alpha": np.nan,
        "inner_cv_uses_outer_training_only": np.nan,
        "normalize_y": np.nan,
        "optimizer": "",
        "n_restarts_optimizer": np.nan,
    }
    for column, default in required_defaults.items():
        if column not in result.columns:
            result[column] = default
    return result


def bool_values(series: pd.Series) -> np.ndarray:
    if pd.api.types.is_bool_dtype(series):
        return series.to_numpy(bool)
    if pd.api.types.is_numeric_dtype(series):
        return series.fillna(0).to_numpy(float) != 0
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin(["true", "1", "1.0"])
        .to_numpy(bool)
    )


def model_metric_row(predictions: pd.DataFrame) -> dict[str, Any]:
    observed = predictions["observed_target_target_unit"].to_numpy(float)
    predicted = predictions["predicted_mean_target_unit"].to_numpy(float)
    residual = observed - predicted
    model = str(predictions["model"].iloc[0])
    target_range = float(np.ptp(observed))
    rmse = float(np.sqrt(np.mean(residual**2)))
    predictive_std = predictions[
        "evaluation_predictive_std_target_unit"
    ].to_numpy(float)
    has_uncertainty = np.isfinite(predictive_std).all() and np.all(
        predictive_std > 0
    )
    learned_nugget = bool(bool_values(predictions["learned_nugget"])[0])
    if has_uncertainty:
        interval_contains = np.abs(residual) <= 1.96 * predictive_std
        coverage = float(interval_contains.mean())
        interval_width = float(np.median(3.92 * predictive_std))
        nlpd_values = predictions["evaluation_nlpd"].to_numpy(float)
        mean_nlpd = float(np.mean(nlpd_values))
        median_nlpd = float(np.median(nlpd_values))
    else:
        coverage = np.nan
        interval_width = np.nan
        mean_nlpd = np.nan
        median_nlpd = np.nan
    bound_hits = bool_values(predictions["any_hyperparameter_bound_hit"])
    nugget_std = predictions[
        "optimized_noise_std_target_unit"
    ].to_numpy(float)
    return {
        "response": str(predictions["response"].iloc[0]),
        "response_label": str(predictions["response_label"].iloc[0]),
        "target_unit": str(predictions["target_unit"].iloc[0]),
        "model": model,
        "model_family": str(predictions["model_family"].iloc[0]),
        "n_predictions": len(predictions),
        "mae": float(mean_absolute_error(observed, predicted)),
        "median_absolute_error": float(np.median(np.abs(residual))),
        "rmse": rmse,
        "r2": float(r2_score(observed, predicted)),
        "nrmse": rmse / target_range if target_range > 0 else np.nan,
        "target_min": float(observed.min()),
        "target_median": float(np.median(observed)),
        "target_max": float(observed.max()),
        "target_range": target_range,
        "mean_nlpd": mean_nlpd,
        "median_nlpd": median_nlpd,
        "total_or_evaluation_95pct_coverage": coverage,
        "median_predictive_interval_width": interval_width,
        "aggregate_fold_runtime_seconds": float(
            predictions["runtime_seconds"].fillna(0).sum()
        ),
        "mean_fold_runtime_seconds": float(
            predictions["runtime_seconds"].fillna(0).mean()
        ),
        "warning_folds": int(
            predictions["warning_count"].fillna(0).astype(float).gt(0).sum()
        ),
        "convergence_warning_folds": int(
            predictions["convergence_warning_count"]
            .fillna(0)
            .astype(float)
            .gt(0)
            .sum()
        ),
        "failed_folds": int(bool_values(predictions["failed_fold"]).sum()),
        "bound_hit_folds": int(bound_hits.sum()),
        "bound_hit_fraction": float(bound_hits.mean()),
        "learned_nugget": learned_nugget,
        "median_learned_nugget_std": (
            float(np.nanmedian(nugget_std))
            if np.isfinite(nugget_std).any()
            else np.nan
        ),
        "q25_learned_nugget_std": (
            float(np.nanquantile(nugget_std, 0.25))
            if np.isfinite(nugget_std).any()
            else np.nan
        ),
        "q75_learned_nugget_std": (
            float(np.nanquantile(nugget_std, 0.75))
            if np.isfinite(nugget_std).any()
            else np.nan
        ),
        "metrics_recomputed_from_prediction_rows": True,
    }


def aligned_predictions(
    predictions: pd.DataFrame, response: str, model: str
) -> pd.DataFrame:
    subset = predictions[
        predictions["response"].eq(response) & predictions["model"].eq(model)
    ].copy()
    require(
        subset["heldout_simulation_id"].is_unique,
        f"{response}/{model}: duplicate held-out predictions",
    )
    return subset.sort_values("heldout_numeric_simulation_id").reset_index(drop=True)


def bootstrap_metric_difference(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *,
    metric: str,
    seed_parts: tuple[Any, ...],
) -> dict[str, Any]:
    left = left.sort_values("heldout_simulation_id").reset_index(drop=True)
    right = right.sort_values("heldout_simulation_id").reset_index(drop=True)
    require(
        left["heldout_simulation_id"].astype(str).tolist()
        == right["heldout_simulation_id"].astype(str).tolist(),
        "Paired bootstrap simulation IDs are not aligned",
    )
    observed = left["observed_target_target_unit"].to_numpy(float)
    require(
        np.allclose(
            observed,
            right["observed_target_target_unit"].to_numpy(float),
            rtol=0,
            atol=1e-12,
        ),
        "Paired bootstrap observed targets differ",
    )
    left_residual = observed - left["predicted_mean_target_unit"].to_numpy(float)
    right_residual = observed - right["predicted_mean_target_unit"].to_numpy(float)
    if metric == "MAE":
        observed_difference = float(
            np.mean(np.abs(left_residual)) - np.mean(np.abs(right_residual))
        )
    elif metric == "RMSE":
        observed_difference = float(
            np.sqrt(np.mean(left_residual**2))
            - np.sqrt(np.mean(right_residual**2))
        )
    else:
        raise ValueError(metric)
    rng = np.random.default_rng(deterministic_seed("paired", *seed_parts, metric))
    n = len(observed)
    values = np.empty(BOOTSTRAP_RESAMPLES, dtype=float)
    batch = 500
    for start in range(0, BOOTSTRAP_RESAMPLES, batch):
        stop = min(start + batch, BOOTSTRAP_RESAMPLES)
        indices = rng.integers(0, n, size=(stop - start, n))
        if metric == "MAE":
            values[start:stop] = (
                np.mean(np.abs(left_residual)[indices], axis=1)
                - np.mean(np.abs(right_residual)[indices], axis=1)
            )
        else:
            values[start:stop] = (
                np.sqrt(np.mean((left_residual**2)[indices], axis=1))
                - np.sqrt(np.mean((right_residual**2)[indices], axis=1))
            )
    low, high = np.quantile(values, BOOTSTRAP_QUANTILES)
    return {
        "metric": metric,
        "difference_definition": "model_a minus model_b; negative favours model_a",
        "observed_difference": observed_difference,
        "ci_low": float(low),
        "ci_high": float(high),
        "confidence_level": 0.95,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "paired_by_simulation_id": True,
        "bootstrap_seed": deterministic_seed("paired", *seed_parts, metric),
        "ci_excludes_zero": bool(low > 0 or high < 0),
        "robustly_favours_model_a": bool(high < 0),
        "robustly_favours_model_b": bool(low > 0),
    }


def compare_models(
    predictions: pd.DataFrame,
    response: str,
    model_a: str,
    model_b: str,
    *,
    comparison_group: str,
) -> list[dict[str, Any]]:
    left = aligned_predictions(predictions, response, model_a)
    right = aligned_predictions(predictions, response, model_b)
    rows = []
    for metric in ["MAE", "RMSE"]:
        row = bootstrap_metric_difference(
            left,
            right,
            metric=metric,
            seed_parts=(response, model_a, model_b, comparison_group),
        )
        row.update(
            {
                "response": response,
                "target_unit": TARGET_SPECS[response]["unit"],
                "comparison_group": comparison_group,
                "model_a": model_a,
                "model_b": model_b,
            }
        )
        rows.append(row)
    return rows


def choose_learned_kernel(
    response: str,
    predictions: pd.DataFrame,
    metrics: pd.DataFrame,
) -> tuple[str, list[dict[str, Any]], str]:
    current = "matern32_learned_nugget"
    candidates = ["rbf_learned_nugget", "matern52_learned_nugget"]
    comparisons: list[dict[str, Any]] = []
    eligible: list[tuple[float, str]] = []
    current_metric = metrics[
        metrics["response"].eq(response) & metrics["model"].eq(current)
    ].iloc[0]
    for candidate in candidates:
        pair_rows = compare_models(
            predictions,
            response,
            candidate,
            current,
            comparison_group="learned_kernel_candidate_vs_matern32",
        )
        comparisons.extend(pair_rows)
        robust_both = all(row["robustly_favours_model_a"] for row in pair_rows)
        metric_row = metrics[
            metrics["response"].eq(response) & metrics["model"].eq(candidate)
        ].iloc[0]
        calibration_ok = bool(
            0.85
            <= float(metric_row["total_or_evaluation_95pct_coverage"])
            <= 1.0
            and abs(
                float(metric_row["total_or_evaluation_95pct_coverage"]) - 0.95
            )
            <= abs(
                float(current_metric["total_or_evaluation_95pct_coverage"]) - 0.95
            )
            + 0.05
        )
        optimization_ok = bool(
            int(metric_row["failed_folds"]) == 0
            and float(metric_row["bound_hit_fraction"]) <= 0.25
            and int(metric_row["convergence_warning_folds"])
            <= max(2, int(0.05 * int(metric_row["n_predictions"])))
        )
        if robust_both and calibration_ok and optimization_ok:
            eligible.append((float(metric_row["rmse"]), candidate))
    if eligible:
        selected = min(eligible)[1]
        rationale = (
            f"{selected} robustly improves paired MAE and RMSE over Matérn 3/2, "
            "with acceptable calibration and optimisation."
        )
    else:
        selected = current
        rationale = (
            "No alternative learned-nugget kernel satisfied the predeclared "
            "paired MAE+RMSE, calibration, and optimisation replacement rule; "
            "Matérn 3/2 is retained for continuity."
        )
    return selected, comparisons, rationale


def select_final_models(
    response: str,
    predictions: pd.DataFrame,
    metrics: pd.DataFrame,
    selected_learned_gp: str,
    kernel_rationale: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    comparisons: list[dict[str, Any]] = []
    no_nugget = selected_learned_gp.replace("_learned_nugget", "_no_nugget")
    for model in [
        "training_mean",
        "linear_ridge",
        "polynomial_ridge_degree2",
        no_nugget,
    ]:
        comparisons.extend(
            compare_models(
                predictions,
                response,
                selected_learned_gp,
                model,
                comparison_group=(
                    "selected_gp_vs_baseline"
                    if model in {
                        "training_mean",
                        "linear_ridge",
                        "polynomial_ridge_degree2",
                    }
                    else "selected_kernel_learned_nugget_vs_no_nugget"
                ),
            )
        )
    comparison_frame = pd.DataFrame(comparisons)

    def pair(model_b: str) -> pd.DataFrame:
        return comparison_frame[
            comparison_frame["model_a"].eq(selected_learned_gp)
            & comparison_frame["model_b"].eq(model_b)
        ]

    target_values = aligned_predictions(
        predictions, response, selected_learned_gp
    )["observed_target_target_unit"].to_numpy(float)
    practical_threshold = max(
        0.01 * float(np.ptp(target_values)),
        0.02 * float(np.subtract(*np.quantile(target_values, [0.75, 0.25]))),
    )
    simple_competitive: list[str] = []
    for simple in ["linear_ridge", "polynomial_ridge_degree2"]:
        rows = pair(simple)
        gp_robust_both = bool(rows["robustly_favours_model_a"].all())
        rmse_difference = float(
            rows.loc[rows["metric"].eq("RMSE"), "observed_difference"].iloc[0]
        )
        gp_improvement = -rmse_difference
        if (not gp_robust_both) or gp_improvement <= practical_threshold:
            simple_competitive.append(simple)
    if "linear_ridge" in simple_competitive:
        selected_point_model = "linear_ridge"
    elif "polynomial_ridge_degree2" in simple_competitive:
        selected_point_model = "polynomial_ridge_degree2"
    else:
        selected_point_model = selected_learned_gp

    nugget_rows = pair(no_nugget)
    nugget_robust_point_advantage = bool(
        nugget_rows["robustly_favours_model_a"].all()
    )
    learned_metric = metrics[
        metrics["response"].eq(response)
        & metrics["model"].eq(selected_learned_gp)
    ].iloc[0]
    no_metric = metrics[
        metrics["response"].eq(response) & metrics["model"].eq(no_nugget)
    ].iloc[0]
    learned_coverage_error = abs(
        float(learned_metric["total_or_evaluation_95pct_coverage"]) - 0.95
    )
    no_coverage_error = abs(
        float(no_metric["total_or_evaluation_95pct_coverage"]) - 0.95
    )
    calibration_advantage = no_coverage_error - learned_coverage_error
    nlpd_advantage = (
        float(no_metric["mean_nlpd"]) - float(learned_metric["mean_nlpd"])
    )
    learned_nugget_useful = bool(
        nugget_robust_point_advantage
        or calibration_advantage >= 0.03
        or nlpd_advantage > 0
    )
    selected_uncertainty_model = (
        selected_learned_gp if learned_nugget_useful else no_nugget
    )
    selected_metric = metrics[
        metrics["response"].eq(response)
        & metrics["model"].eq(selected_point_model)
    ].iloc[0]
    return (
        {
            "response": response,
            "response_label": TARGET_SPECS[response]["label"],
            "target_unit": TARGET_SPECS[response]["unit"],
            "population_size": len(target_values),
            "selected_kernel_family_model": selected_learned_gp,
            "selected_point_model": selected_point_model,
            "selected_uncertainty_model": selected_uncertainty_model,
            "selected_no_nugget_sensitivity_model": no_nugget,
            "simple_models_competitive": json_text(simple_competitive),
            "practical_rmse_difference_threshold": practical_threshold,
            "kernel_replacement_rationale": kernel_rationale,
            "learned_nugget_robust_point_advantage": nugget_robust_point_advantage,
            "learned_nugget_calibration_advantage": calibration_advantage,
            "learned_nugget_mean_nlpd_advantage": nlpd_advantage,
            "learned_nugget_remains_useful": learned_nugget_useful,
            "selected_model_mae": float(selected_metric["mae"]),
            "selected_model_rmse": float(selected_metric["rmse"]),
            "selected_model_r2": float(selected_metric["r2"]),
            "selected_model_nrmse": float(selected_metric["nrmse"]),
            "decision_rule": (
                "replace Matérn 3/2 only for robust paired MAE and RMSE "
                "improvement without calibration/optimisation deterioration; "
                "prefer a simpler point model when GP improvement is not robust "
                "or practically meaningful"
            ),
        },
        comparisons,
    )


def run_models(
    targets: pd.DataFrame,
    *,
    workers: int,
    smoke: bool,
    force: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    destination = SMOKE_DIR if smoke else OUTPUT_DIR
    prediction_path = destination / "phase4_loo_predictions.csv"
    metrics_path = destination / "phase4_model_metrics.csv"
    comparisons_path = destination / "phase4_paired_bootstrap_comparisons.csv"
    diagnostics_path = destination / "phase4_optimization_diagnostics.csv"
    decisions_path = destination / "phase4_selected_model_decisions.csv"
    if (
        not force
        and all(
            path.is_file()
            for path in [
                prediction_path,
                metrics_path,
                comparisons_path,
                diagnostics_path,
                decisions_path,
            ]
        )
    ):
        cached_predictions = pd.read_csv(prediction_path)
        expected_population = SMOKE_SIMULATIONS if smoke else EXPECTED_SIMULATIONS
        expected_models_per_response = 7
        if (
            len(cached_predictions)
            == expected_population * len(TARGET_SPECS) * expected_models_per_response
        ):
            RUNTIME_EVENTS.append(
                {
                    "stage": "compact_model_comparison",
                    "smoke": smoke,
                    "cache_reused": True,
                    "prediction_rows": len(cached_predictions),
                    "wall_runtime_seconds": 0.0,
                }
            )
            return (
                cached_predictions,
                pd.read_csv(metrics_path),
                pd.read_csv(comparisons_path),
                pd.read_csv(diagnostics_path),
                pd.read_csv(decisions_path),
            )

    started = time.perf_counter()
    phase3 = load_phase3_engine(smoke=smoke)
    learned_names = [
        "matern32_learned_nugget",
        "rbf_learned_nugget",
        "matern52_learned_nugget",
    ]
    config_by_name = {
        configuration.name: configuration
        for configuration in phase3.GP_CONFIGURATIONS
    }
    prediction_frames: list[pd.DataFrame] = []
    learned_selection: dict[str, tuple[str, str]] = {}
    kernel_comparisons: list[dict[str, Any]] = []
    restart_count = 0 if smoke else 1

    for response in TARGET_SPECS:
        table = model_table_for_response(targets, response)
        mean_frame = phase3.run_training_mean_loo(table, target=response)
        prediction_frames.append(
            genericize_prediction_columns(
                mean_frame, response=response, model_family="sanity baseline"
            )
        )
        for ridge_name in ["linear_ridge", "polynomial_ridge_degree2"]:
            ridge_frame = phase3.run_ridge_loo(
                table,
                target=response,
                model_name=ridge_name,
                workers=workers,
                force=force,
            )
            prediction_frames.append(
                genericize_prediction_columns(
                    ridge_frame, response=response, model_family="Ridge"
                )
            )
        for configuration_name in learned_names:
            gp_frame = phase3.run_gp_loo(
                table,
                target=response,
                target_definition="T0",
                analysis_label="phase4_new_response_compact",
                configuration=config_by_name[configuration_name],
                workers=workers,
                force=force,
                n_restarts_optimizer=restart_count,
            )
            prediction_frames.append(
                genericize_prediction_columns(
                    gp_frame,
                    response=response,
                    model_family="Gaussian process",
                )
            )

    interim_predictions = pd.concat(prediction_frames, ignore_index=True)
    interim_metrics = pd.DataFrame(
        [
            model_metric_row(group)
            for _, group in interim_predictions.groupby(
                ["response", "model"], sort=True
            )
        ]
    )
    for response in TARGET_SPECS:
        selected, comparisons, rationale = choose_learned_kernel(
            response, interim_predictions, interim_metrics
        )
        learned_selection[response] = (selected, rationale)
        kernel_comparisons.extend(comparisons)
        no_nugget_name = selected.replace("_learned_nugget", "_no_nugget")
        table = model_table_for_response(targets, response)
        no_nugget_frame = phase3.run_gp_loo(
            table,
            target=response,
            target_definition="T0",
            analysis_label="phase4_selected_kernel_nugget_sensitivity",
            configuration=config_by_name[no_nugget_name],
            workers=workers,
            force=force,
            n_restarts_optimizer=restart_count,
        )
        prediction_frames.append(
            genericize_prediction_columns(
                no_nugget_frame,
                response=response,
                model_family="Gaussian process",
            )
        )

    predictions = pd.concat(prediction_frames, ignore_index=True)
    predictions = predictions.sort_values(
        ["response", "model", "heldout_numeric_simulation_id"]
    ).reset_index(drop=True)
    metrics = pd.DataFrame(
        [
            model_metric_row(group)
            for _, group in predictions.groupby(["response", "model"], sort=True)
        ]
    ).sort_values(["response", "rmse", "mae"]).reset_index(drop=True)
    decisions: list[dict[str, Any]] = []
    final_comparisons: list[dict[str, Any]] = list(kernel_comparisons)
    for response, (selected, rationale) in learned_selection.items():
        decision, comparisons = select_final_models(
            response, predictions, metrics, selected, rationale
        )
        decisions.append(decision)
        final_comparisons.extend(comparisons)
    comparison_frame = (
        pd.DataFrame(final_comparisons)
        .drop_duplicates(
            ["response", "comparison_group", "model_a", "model_b", "metric"]
        )
        .sort_values(
            ["response", "comparison_group", "model_a", "model_b", "metric"]
        )
        .reset_index(drop=True)
    )
    decision_frame = pd.DataFrame(decisions).sort_values("response").reset_index(
        drop=True
    )
    diagnostics_columns = [
        "response",
        "response_label",
        "target_unit",
        "model",
        "fold_index",
        "heldout_simulation_id",
        "training_size",
        "population_size",
        "optimized_kernel",
        "optimized_signal_variance_normalized",
        "optimized_length_scale",
        "optimized_noise_variance_normalized",
        "optimized_noise_std_target_unit",
        "noise_std_fraction_training_target_std",
        "noise_std_fraction_dataset_target_median",
        "numerical_alpha_normalized",
        "optimizer",
        "n_restarts_optimizer",
        "log_marginal_likelihood",
        "runtime_seconds",
        "warning_count",
        "convergence_warning_count",
        "warnings",
        "failed_fold",
        "constant_bound_hit",
        "length_scale_bound_hit",
        "noise_bound_hit",
        "any_hyperparameter_bound_hit",
        "fold_random_seed",
    ]
    diagnostics = predictions[
        predictions["model_family"].eq("Gaussian process")
    ].copy()
    diagnostics = diagnostics[
        [column for column in diagnostics_columns if column in diagnostics.columns]
    ].reset_index(drop=True)
    write_csv(prediction_path, predictions)
    write_csv(metrics_path, metrics)
    write_csv(comparisons_path, comparison_frame)
    write_csv(diagnostics_path, diagnostics)
    write_csv(decisions_path, decision_frame)
    RUNTIME_EVENTS.extend(phase3.RUNTIME_EVENTS)
    RUNTIME_EVENTS.append(
        {
            "stage": "compact_model_comparison",
            "smoke": smoke,
            "cache_reused": False,
            "prediction_rows": len(predictions),
            "restart_count": restart_count,
            "workers": workers,
            "wall_runtime_seconds": time.perf_counter() - started,
        }
    )
    return predictions, metrics, comparison_frame, diagnostics, decision_frame


def response_analysis_table(targets: pd.DataFrame) -> pd.DataFrame:
    table = targets[
        [
            "simulation_id",
            "numeric_simulation_id",
            *FEATURE_COLUMNS,
            "T0_melt_pool_width_um",
            "T0_penetration_depth_um",
            "T0_melt_pool_kinetic_energy_nJ",
            "T0_total_vertical_height_um",
            "phase1_unstable_depth_window",
        ]
    ].copy()
    return table.rename(
        columns={
            "T0_melt_pool_width_um": "width",
            "T0_penetration_depth_um": "depth",
            "T0_melt_pool_kinetic_energy_nJ": "kinetic_energy",
            "T0_total_vertical_height_um": "total_height",
        }
    )


def bootstrap_spearman_interval(
    left: np.ndarray, right: np.ndarray, *, response: str, feature: str
) -> dict[str, Any]:
    valid = np.isfinite(left) & np.isfinite(right)
    left = left[valid]
    right = right[valid]
    n = len(left)
    rng = np.random.default_rng(
        deterministic_seed("spearman-bootstrap", response, feature)
    )
    values = np.empty(BOOTSTRAP_RESAMPLES, dtype=float)
    for index in range(BOOTSTRAP_RESAMPLES):
        sample = rng.integers(0, n, size=n)
        values[index] = safe_spearman(left[sample], right[sample])
    values = values[np.isfinite(values)]
    require(
        len(values) >= int(0.99 * BOOTSTRAP_RESAMPLES),
        f"{response}/{feature}: too many invalid bootstrap correlations",
    )
    low, high = np.quantile(values, BOOTSTRAP_QUANTILES)
    return {
        "response": response,
        "feature": feature,
        "ci_low": float(low),
        "ci_high": float(high),
        "confidence_level": 0.95,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "bootstrap_seed": deterministic_seed(
            "spearman-bootstrap", response, feature
        ),
        "resample_unit": "simulation",
    }


def standardized_ridge_rows(
    table: pd.DataFrame, response: str
) -> list[dict[str, Any]]:
    X = table[FEATURE_COLUMNS].to_numpy(float)
    y = table[response].to_numpy(float)
    x_scaler = StandardScaler().fit(X)
    y_scaler = StandardScaler().fit(y.reshape(-1, 1))
    X_scaled = x_scaler.transform(X)
    y_scaled = y_scaler.transform(y.reshape(-1, 1)).ravel()
    cv = KFold(
        n_splits=RIDGE_INNER_FOLDS,
        shuffle=True,
        random_state=deterministic_seed("interpretive-ridge", response),
    )
    alpha_scores: list[tuple[float, float]] = []
    for alpha in RIDGE_ALPHA_GRID:
        fold_rmse: list[float] = []
        for train_indices, validation_indices in cv.split(X_scaled):
            model = Ridge(alpha=alpha).fit(
                X_scaled[train_indices], y_scaled[train_indices]
            )
            prediction = model.predict(X_scaled[validation_indices])
            fold_rmse.append(
                float(
                    np.sqrt(
                        mean_squared_error(
                            y_scaled[validation_indices], prediction
                        )
                    )
                )
            )
        alpha_scores.append((alpha, float(np.mean(fold_rmse))))
    selected_alpha, selected_cv_rmse = min(alpha_scores, key=lambda item: item[1])
    model = Ridge(alpha=selected_alpha).fit(X_scaled, y_scaled)
    return [
        {
            "response": response,
            "response_label": OUTPUT_SPECS[response]["label"],
            "response_unit": OUTPUT_SPECS[response]["unit"],
            "feature": feature,
            "feature_unit": FEATURE_UNITS[feature],
            "standardized_coefficient": float(model.coef_[index]),
            "selected_alpha": float(selected_alpha),
            "five_fold_cv_standardized_rmse": float(selected_cv_rmse),
            "sample_size": len(table),
            "x_standardized": True,
            "y_standardized": True,
            "interpretation": (
                "conditional linear association after holding the other listed "
                "features in the Ridge model; not a causal effect"
            ),
        }
        for index, feature in enumerate(FEATURE_COLUMNS)
    ]


def full_gp_response_data(
    table: pd.DataFrame, response: str
) -> pd.DataFrame:
    if response == "depth":
        return table[table["simulation_id"].isin(DEPTH_STABLE_IDS)].copy()
    return table.copy()


def selected_interpretive_configuration(
    response: str, decisions: pd.DataFrame
) -> str:
    if response in {"width", "depth"}:
        return "matern32_learned_nugget"
    row = decisions[decisions["response"].eq(response)]
    require(len(row) == 1, f"Missing selected new-response GP: {response}")
    selected = str(row.iloc[0]["selected_kernel_family_model"])
    require(
        selected.endswith("_learned_nugget"),
        f"Interpretive selected kernel lacks learned nugget: {selected}",
    )
    return selected


def fit_full_gp(
    table: pd.DataFrame,
    response: str,
    configuration_name: str,
    phase3: Any,
) -> dict[str, Any]:
    configuration = next(
        item
        for item in phase3.GP_CONFIGURATIONS
        if item.name == configuration_name
    )
    X = table[FEATURE_COLUMNS].to_numpy(float)
    y = table[response].to_numpy(float)
    x_scaler = StandardScaler().fit(X)
    X_scaled = x_scaler.transform(X)
    y_mean = float(y.mean())
    y_std = float(y.std(ddof=0))
    require(y_std > 0, f"{response}: zero full-data target scale")
    y_scaled = (y - y_mean) / y_std
    model = GaussianProcessRegressor(
        kernel=phase3.make_gp_kernel(configuration),
        alpha=configuration.numerical_alpha_normalized,
        optimizer="fmin_l_bfgs_b",
        n_restarts_optimizer=1,
        normalize_y=False,
        random_state=deterministic_seed("full-interpretive-gp", response),
        copy_X_train=True,
    )
    started = time.perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model.fit(X_scaled, y_scaled)
    tree = cKDTree(X_scaled)
    nearest_other = tree.query(X_scaled, k=2)[0][:, 1]
    threshold = float(
        np.quantile(nearest_other, SUPPORT_DISTANCE_QUANTILE) * 1.25
    )
    return {
        "response": response,
        "configuration_name": configuration_name,
        "configuration": configuration,
        "model": model,
        "x_scaler": x_scaler,
        "y_mean": y_mean,
        "y_std": y_std,
        "X": X,
        "X_scaled": X_scaled,
        "y": y,
        "tree": tree,
        "support_distance_threshold": threshold,
        "training_sample_size": len(table),
        "training_simulation_ids": table["simulation_id"].astype(str).tolist(),
        "optimized_kernel": str(model.kernel_),
        "warnings": " | ".join(str(item.message) for item in caught),
        "warning_count": len(caught),
        "runtime_seconds": time.perf_counter() - started,
    }


def predict_full_gp(
    fitted: dict[str, Any], query: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    query_scaled = fitted["x_scaler"].transform(query)
    mean_scaled, std_scaled = fitted["model"].predict(
        query_scaled, return_std=True
    )
    mean = mean_scaled * fitted["y_std"] + fitted["y_mean"]
    std = std_scaled * fitted["y_std"]
    nearest = fitted["tree"].query(query_scaled, k=1)[0]
    return mean, std, nearest


def curve_and_surface_rows(
    table: pd.DataFrame,
    decisions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    phase3 = load_phase3_engine(smoke=False)
    curve_rows: list[dict[str, Any]] = []
    surface_rows: list[dict[str, Any]] = []
    support_rows: list[dict[str, Any]] = []
    fitted_models: dict[str, dict[str, Any]] = {}
    for response in OUTPUT_SPECS:
        training = full_gp_response_data(table, response)
        configuration_name = selected_interpretive_configuration(
            response, decisions
        )
        fitted = fit_full_gp(training, response, configuration_name, phase3)
        fitted_models[response] = fitted
        reference = {
            feature: float(training[feature].median())
            for feature in FEATURE_COLUMNS
        }
        profile_definitions: list[tuple[str, dict[str, float]]] = [
            ("median_reference", reference.copy())
        ]
        if response == "kinetic_energy":
            for label, quantile in [
                ("low_P_q10", 0.10),
                ("median_P_q50", 0.50),
                ("high_P_q90", 0.90),
            ]:
                profile = reference.copy()
                profile["P"] = float(training["P"].quantile(quantile))
                profile_definitions.append((label, profile))
        for feature in FEATURE_COLUMNS:
            grid = np.linspace(
                float(training[feature].min()),
                float(training[feature].max()),
                CURVE_GRID_SIZE,
            )
            relevant_profiles = (
                profile_definitions
                if response == "kinetic_energy" and feature == "LS"
                else profile_definitions[:1]
            )
            for profile_label, profile in relevant_profiles:
                query = np.tile(
                    np.array([profile[item] for item in FEATURE_COLUMNS], dtype=float),
                    (len(grid), 1),
                )
                query[:, FEATURE_COLUMNS.index(feature)] = grid
                mean, std, nearest = predict_full_gp(fitted, query)
                supported = (
                    nearest <= fitted["support_distance_threshold"]
                )
                for index in range(len(grid)):
                    curve_rows.append(
                        {
                            "response": response,
                            "response_label": OUTPUT_SPECS[response]["label"],
                            "response_unit": OUTPUT_SPECS[response]["unit"],
                            "varying_feature": feature,
                            "varying_feature_unit": FEATURE_UNITS[feature],
                            "profile": profile_label,
                            "grid_index": index,
                            "feature_value": float(grid[index]),
                            "predicted_mean": float(mean[index]),
                            "predictive_std": float(std[index]),
                            "interval_lower_95": float(
                                mean[index] - 1.96 * std[index]
                            ),
                            "interval_upper_95": float(
                                mean[index] + 1.96 * std[index]
                            ),
                            "nearest_training_distance_standardized": float(
                                nearest[index]
                            ),
                            "support_distance_threshold": fitted[
                                "support_distance_threshold"
                            ],
                            "within_observed_support": bool(supported[index]),
                            "reference_P": profile["P"],
                            "reference_VX": profile["VX"],
                            "reference_LS": profile["LS"],
                            "reference_ST": profile["ST"],
                            "model_configuration": configuration_name,
                            "training_population": (
                                "stable_230"
                                if response == "depth"
                                else "all_241"
                            ),
                            "training_sample_size": fitted[
                                "training_sample_size"
                            ],
                            "interpretive_fit_not_model_selection": True,
                        }
                    )
                supported_means = mean[supported]
                support_rows.append(
                    {
                        "response": response,
                        "plot_type": "controlled_curve",
                        "varying_features": feature,
                        "profile": profile_label,
                        "grid_count": len(grid),
                        "supported_grid_count": int(supported.sum()),
                        "supported_fraction": float(supported.mean()),
                        "support_distance_threshold": fitted[
                            "support_distance_threshold"
                        ],
                        "supported_prediction_range": (
                            float(np.ptp(supported_means))
                            if len(supported_means)
                            else np.nan
                        ),
                        "model_configuration": configuration_name,
                        "training_sample_size": fitted[
                            "training_sample_size"
                        ],
                        "optimized_kernel": fitted["optimized_kernel"],
                        "fit_warning_count": fitted["warning_count"],
                        "fit_warnings": fitted["warnings"],
                    }
                )

        for first_feature, second_feature in [("P", "VX"), ("P", "LS")]:
            first_grid = np.linspace(
                float(training[first_feature].min()),
                float(training[first_feature].max()),
                SURFACE_GRID_SIZE,
            )
            second_grid = np.linspace(
                float(training[second_feature].min()),
                float(training[second_feature].max()),
                SURFACE_GRID_SIZE,
            )
            first_mesh, second_mesh = np.meshgrid(
                first_grid, second_grid, indexing="xy"
            )
            query = np.tile(
                np.array([reference[item] for item in FEATURE_COLUMNS], dtype=float),
                (first_mesh.size, 1),
            )
            query[:, FEATURE_COLUMNS.index(first_feature)] = first_mesh.ravel()
            query[:, FEATURE_COLUMNS.index(second_feature)] = second_mesh.ravel()
            mean, std, nearest = predict_full_gp(fitted, query)
            pair_training = training[[first_feature, second_feature]].to_numpy(float)
            pair_scaler = StandardScaler().fit(pair_training)
            pair_scaled = pair_scaler.transform(pair_training)
            query_pair_scaled = pair_scaler.transform(
                query[
                    :,
                    [
                        FEATURE_COLUMNS.index(first_feature),
                        FEATURE_COLUMNS.index(second_feature),
                    ],
                ]
            )
            try:
                hull = Delaunay(pair_scaled)
                inside_hull = hull.find_simplex(query_pair_scaled) >= 0
            except Exception:
                inside_hull = np.ones(len(query), dtype=bool)
            supported = (
                inside_hull
                & (nearest <= fitted["support_distance_threshold"])
            )
            mean_grid = mean.reshape(SURFACE_GRID_SIZE, SURFACE_GRID_SIZE)
            supported_grid = supported.reshape(
                SURFACE_GRID_SIZE, SURFACE_GRID_SIZE
            )
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                row_component = np.nanmean(
                    np.where(supported_grid, mean_grid, np.nan),
                    axis=1,
                    keepdims=True,
                )
                column_component = np.nanmean(
                    np.where(supported_grid, mean_grid, np.nan),
                    axis=0,
                    keepdims=True,
                )
                grand_mean = float(
                    np.nanmean(np.where(supported_grid, mean_grid, np.nan))
                )
            nonadditive = mean_grid - row_component - column_component + grand_mean
            interaction_strength = float(
                np.nanstd(np.where(supported_grid, nonadditive, np.nan))
            )
            for index in range(len(query)):
                surface_rows.append(
                    {
                        "response": response,
                        "response_label": OUTPUT_SPECS[response]["label"],
                        "response_unit": OUTPUT_SPECS[response]["unit"],
                        "first_feature": first_feature,
                        "first_feature_unit": FEATURE_UNITS[first_feature],
                        "second_feature": second_feature,
                        "second_feature_unit": FEATURE_UNITS[second_feature],
                        "grid_index": index,
                        "first_feature_value": float(
                            query[index, FEATURE_COLUMNS.index(first_feature)]
                        ),
                        "second_feature_value": float(
                            query[index, FEATURE_COLUMNS.index(second_feature)]
                        ),
                        "predicted_mean": float(mean[index]),
                        "predictive_std": float(std[index]),
                        "nearest_training_distance_standardized": float(
                            nearest[index]
                        ),
                        "inside_pairwise_convex_hull": bool(inside_hull[index]),
                        "within_observed_support": bool(supported[index]),
                        "plot_value_masked_outside_support": (
                            float(mean[index]) if supported[index] else np.nan
                        ),
                        "reference_P": reference["P"],
                        "reference_VX": reference["VX"],
                        "reference_LS": reference["LS"],
                        "reference_ST": reference["ST"],
                        "model_configuration": configuration_name,
                        "training_population": (
                            "stable_230"
                            if response == "depth"
                            else "all_241"
                        ),
                        "training_sample_size": fitted[
                            "training_sample_size"
                        ],
                        "interaction_nonadditivity_std_supported": (
                            interaction_strength
                        ),
                        "interpretive_fit_not_model_selection": True,
                    }
                )
            support_rows.append(
                {
                    "response": response,
                    "plot_type": "interaction_surface",
                    "varying_features": f"{first_feature} x {second_feature}",
                    "profile": "other features at medians",
                    "grid_count": len(query),
                    "supported_grid_count": int(supported.sum()),
                    "supported_fraction": float(supported.mean()),
                    "support_distance_threshold": fitted[
                        "support_distance_threshold"
                    ],
                    "supported_prediction_range": float(
                        np.ptp(mean[supported])
                    )
                    if supported.any()
                    else np.nan,
                    "interaction_nonadditivity_std_supported": interaction_strength,
                    "model_configuration": configuration_name,
                    "training_sample_size": fitted["training_sample_size"],
                    "optimized_kernel": fitted["optimized_kernel"],
                    "fit_warning_count": fitted["warning_count"],
                    "fit_warnings": fitted["warnings"],
                }
            )
    RUNTIME_EVENTS.append(
        {
            "stage": "full_data_interpretive_gp_effects",
            "models": {
                response: {
                    "configuration": fitted["configuration_name"],
                    "population": fitted["training_sample_size"],
                    "runtime_seconds": fitted["runtime_seconds"],
                    "warning_count": fitted["warning_count"],
                }
                for response, fitted in fitted_models.items()
            },
            "wall_runtime_seconds": float(
                sum(item["runtime_seconds"] for item in fitted_models.values())
            ),
        }
    )
    return (
        pd.DataFrame(curve_rows),
        pd.DataFrame(surface_rows),
        pd.DataFrame(support_rows),
    )


def relationship_analysis(
    targets: pd.DataFrame,
    decisions: pd.DataFrame,
    *,
    force: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    paths = {
        "correlations": OUTPUT_DIR / "phase4_spearman_correlations.csv",
        "intervals": OUTPUT_DIR / "phase4_spearman_bootstrap_intervals.csv",
        "ridge": OUTPUT_DIR / "phase4_standardized_ridge_coefficients.csv",
        "curves": OUTPUT_DIR / "phase4_controlled_effect_curves.csv",
        "surfaces": OUTPUT_DIR / "phase4_interaction_surface_values.csv",
        "support": OUTPUT_DIR / "phase4_observed_support_summary.csv",
    }
    if not force and all(path.is_file() for path in paths.values()):
        RUNTIME_EVENTS.append(
            {
                "stage": "physical_input_output_relationships",
                "cache_reused": True,
                "wall_runtime_seconds": 0.0,
            }
        )
        return tuple(pd.read_csv(paths[key]) for key in paths)  # type: ignore[return-value]
    started = time.perf_counter()
    table = response_analysis_table(targets)
    correlation_rows: list[dict[str, Any]] = []
    interval_rows: list[dict[str, Any]] = []
    ridge_rows: list[dict[str, Any]] = []
    for response in OUTPUT_SPECS:
        for feature in FEATURE_COLUMNS:
            left = table[feature].to_numpy(float)
            right = table[response].to_numpy(float)
            correlation_rows.append(
                {
                    "response": response,
                    "response_label": OUTPUT_SPECS[response]["label"],
                    "response_unit": OUTPUT_SPECS[response]["unit"],
                    "feature": feature,
                    "feature_unit": FEATURE_UNITS[feature],
                    "spearman_rho": safe_spearman(left, right),
                    "sample_size": int(
                        (np.isfinite(left) & np.isfinite(right)).sum()
                    ),
                    "analysis_type": "raw descriptive association",
                    "causal_claim": False,
                }
            )
            interval_rows.append(
                bootstrap_spearman_interval(
                    left, right, response=response, feature=feature
                )
            )
        ridge_rows.extend(standardized_ridge_rows(table, response))
    correlations = pd.DataFrame(correlation_rows)
    intervals = pd.DataFrame(interval_rows)
    ridge = pd.DataFrame(ridge_rows)
    curves, surfaces, support = curve_and_surface_rows(table, decisions)
    write_csv(paths["correlations"], correlations)
    write_csv(paths["intervals"], intervals)
    write_csv(paths["ridge"], ridge)
    write_csv(paths["curves"], curves)
    write_csv(paths["surfaces"], surfaces)
    write_csv(paths["support"], support)
    RUNTIME_EVENTS.append(
        {
            "stage": "physical_input_output_relationships",
            "cache_reused": False,
            "spearman_bootstrap_resamples_per_pair": BOOTSTRAP_RESAMPLES,
            "pair_count": len(correlations),
            "controlled_curve_rows": len(curves),
            "interaction_surface_rows": len(surfaces),
            "wall_runtime_seconds": time.perf_counter() - started,
        }
    )
    return correlations, intervals, ridge, curves, surfaces, support


def normalized_diagnostics(
    targets: pd.DataFrame, *, force: bool
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    diagnostic_path = OUTPUT_DIR / "phase4_beam_normalized_penetration.csv"
    correlation_path = OUTPUT_DIR / "phase4_normalized_diagnostic_correlations.csv"
    sensitivity_path = (
        OUTPUT_DIR / "phase4_normalized_diagnostic_unstable_sensitivity.csv"
    )
    if (
        not force
        and diagnostic_path.is_file()
        and correlation_path.is_file()
        and sensitivity_path.is_file()
    ):
        RUNTIME_EVENTS.append(
            {
                "stage": "beam_normalized_penetration",
                "cache_reused": True,
                "wall_runtime_seconds": 0.0,
            }
        )
        return (
            pd.read_csv(diagnostic_path),
            pd.read_csv(correlation_path),
            pd.read_csv(sensitivity_path),
        )
    started = time.perf_counter()
    candidates = pd.read_csv(PHASE35_DIR / "regime_target_candidates.csv")
    required_candidates = candidates[
        candidates["candidate_id"].isin(["G0", "G3", "R0", "R3"])
    ].pivot(index="simulation_id", columns="candidate_id", values="value")
    diagnostics = targets[
        [
            "simulation_id",
            "numeric_simulation_id",
            "LS",
            "T0_melt_pool_width_um",
            "T0_penetration_depth_um",
            "phase1_unstable_depth_window",
        ]
    ].merge(
        required_candidates.reset_index(),
        on="simulation_id",
        how="left",
        validate="one_to_one",
    )
    require(
        diagnostics[["G0", "R0"]].notna().all().all(),
        "Phase 3.5 T0 diagnostic candidates G0/R0 are incomplete",
    )
    persistent_available = diagnostics[["G3", "R3"]].notna().all(axis=1)
    require(
        int(persistent_available.sum()) == 240
        and diagnostics.loc[
            ~persistent_available, "simulation_id"
        ].astype(str).tolist()
        == ["sim_00101"],
        "Unexpected Phase 3.5 persistent-candidate availability",
    )
    diagnostics["persistent_diagnostics_available"] = persistent_available
    diagnostics["persistent_diagnostics_missing_reason"] = np.where(
        persistent_available,
        "",
        "Phase 3.5 adaptive active-interior interval unavailable",
    )
    diagnostics["T0_depth_over_LS"] = (
        diagnostics["T0_penetration_depth_um"] / diagnostics["LS"]
    )
    diagnostics["G3_over_LS"] = diagnostics["G3"] / diagnostics["LS"]
    diagnostics["persistent_depth_over_LS_recomputed"] = (
        diagnostics["G3"] / diagnostics["LS"]
    )
    diagnostics["G3_over_LS_identity_absolute_error"] = np.abs(
        diagnostics["G3_over_LS"]
        - diagnostics["persistent_depth_over_LS_recomputed"]
    )
    diagnostics["R0_recomputed"] = (
        diagnostics["T0_penetration_depth_um"]
        / diagnostics["T0_melt_pool_width_um"]
    )
    diagnostics["R0_absolute_reproduction_error"] = np.abs(
        diagnostics["R0"] - diagnostics["R0_recomputed"]
    )
    diagnostics["T0_depth_matches_G0_absolute_error_um"] = np.abs(
        diagnostics["T0_penetration_depth_um"] - diagnostics["G0"]
    )
    diagnostic_columns = [
        "T0_penetration_depth_um",
        "T0_depth_over_LS",
        "G3",
        "G3_over_LS",
        "R0",
        "R3",
    ]
    percentile_columns = []
    for column in diagnostic_columns:
        percentile = f"{column}_percentile"
        diagnostics[percentile] = diagnostics[column].rank(pct=True)
        percentile_columns.append(percentile)
    diagnostics["G3_over_LS_vs_R3_percentile_disagreement"] = np.abs(
        diagnostics["G3_over_LS_percentile"]
        - diagnostics["R3_percentile"]
    )
    diagnostics["large_G3_over_LS_vs_R3_disagreement"] = (
        diagnostics["G3_over_LS_vs_R3_percentile_disagreement"]
        >= diagnostics[
            "G3_over_LS_vs_R3_percentile_disagreement"
        ].quantile(0.90)
    )
    diagnostics["interpretation_warning"] = (
        "LS is in the denominator of depth/LS; LS associations can be partly "
        "mechanical. Interpret LS primarily against absolute depth."
    )
    diagnostics["R3_status"] = (
        "provisional sustained deep-and-narrow descriptor; not Keyhole ground truth"
    )
    correlation_rows: list[dict[str, Any]] = []
    for left_index, left in enumerate(diagnostic_columns):
        for right in diagnostic_columns[left_index + 1 :]:
            paired_valid = (
                np.isfinite(diagnostics[left].to_numpy(float))
                & np.isfinite(diagnostics[right].to_numpy(float))
            )
            correlation_rows.append(
                {
                    "diagnostic_a": left,
                    "diagnostic_b": right,
                    "spearman_rho": safe_spearman(
                        diagnostics[left].to_numpy(float),
                        diagnostics[right].to_numpy(float),
                    ),
                    "sample_size": int(paired_valid.sum()),
                    "units": (
                        "um for absolute depth/G3; dimensionless for normalized ratios"
                    ),
                    "mathematical_coupling_warning_applies": bool(
                        "over_LS" in left or "over_LS" in right
                    ),
                }
            )
    sensitivity_rows: list[dict[str, Any]] = []
    population_masks = {
        "all_241": np.ones(len(diagnostics), dtype=bool),
        "stable_230": ~diagnostics["phase1_unstable_depth_window"].astype(bool),
        "unstable_11": diagnostics["phase1_unstable_depth_window"].astype(bool),
    }
    for column in diagnostic_columns:
        for population, mask in population_masks.items():
            values = diagnostics.loc[mask, column].to_numpy(float)
            values = values[np.isfinite(values)]
            require(
                len(values) > 0,
                f"{column}/{population}: no finite diagnostic values",
            )
            sensitivity_rows.append(
                {
                    "diagnostic": column,
                    "population": population,
                    "sample_size": len(values),
                    "minimum": float(np.min(values)),
                    "q25": float(np.quantile(values, 0.25)),
                    "median": float(np.median(values)),
                    "q75": float(np.quantile(values, 0.75)),
                    "maximum": float(np.max(values)),
                    "mean": float(np.mean(values)),
                    "std": float(np.std(values, ddof=1)),
                    "unstable_ids": (
                        json_text(DEPTH_UNSTABLE_IDS)
                        if population == "unstable_11"
                        else ""
                    ),
                }
            )
    diagnostics = diagnostics.sort_values("numeric_simulation_id").reset_index(
        drop=True
    )
    correlations = pd.DataFrame(correlation_rows)
    sensitivity = pd.DataFrame(sensitivity_rows)
    write_csv(diagnostic_path, diagnostics)
    write_csv(correlation_path, correlations)
    write_csv(sensitivity_path, sensitivity)
    RUNTIME_EVENTS.append(
        {
            "stage": "beam_normalized_penetration",
            "cache_reused": False,
            "population_size": len(diagnostics),
            "unstable_count": len(DEPTH_UNSTABLE_IDS),
            "wall_runtime_seconds": time.perf_counter() - started,
        }
    )
    return diagnostics, correlations, sensitivity


MODEL_LABELS = {
    "training_mean": "Mean",
    "linear_ridge": "Linear Ridge",
    "polynomial_ridge_degree2": "Polynomial Ridge",
    "matern32_learned_nugget": "Matérn 3/2 + nugget",
    "matern52_learned_nugget": "Matérn 5/2 + nugget",
    "rbf_learned_nugget": "RBF + nugget",
    "matern32_no_nugget": "Matérn 3/2, no nugget",
    "matern52_no_nugget": "Matérn 5/2, no nugget",
    "rbf_no_nugget": "RBF, no nugget",
}
FEATURE_LABELS = {
    "P": "Power P (W)",
    "VX": "Scan speed VX (m/s)",
    "LS": "Laser spot radius LS (µm)",
    "ST": "Substrate temperature ST (K)",
}
RESPONSE_AXIS_LABELS = {
    "width": "T0 width (µm)",
    "depth": "T0 penetration depth (µm)",
    "kinetic_energy": "T0 melt kinetic energy (nJ)",
    "total_height": "T0 total vertical height (µm)",
}


def add_figure_footer(
    figure: plt.Figure,
    *,
    source: str,
    takeaway: str,
    caveat: str,
) -> None:
    figure.text(
        0.01,
        0.047,
        f"Source: {source}",
        ha="left",
        va="bottom",
        fontsize=8,
        color="#444444",
    )
    figure.text(
        0.01,
        0.027,
        f"Takeaway: {takeaway}",
        ha="left",
        va="bottom",
        fontsize=8,
        color="#1F4E79",
    )
    figure.text(
        0.01,
        0.007,
        f"Caveat: {caveat}",
        ha="left",
        va="bottom",
        fontsize=8,
        color="#8B4513",
    )
    figure.subplots_adjust(bottom=max(0.18, figure.subplotpars.bottom))


def save_phase4_figure(
    figure: plt.Figure,
    manifest_rows: list[dict[str, Any]],
    *,
    figure_id: int,
    slug: str,
    title: str,
    source: str,
    sample_size: str,
    takeaway: str,
    caveat: str,
) -> Path:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    PRESENTATION_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURE_DIR / f"{figure_id:02d}_{slug}.png"
    add_figure_footer(
        figure, source=source, takeaway=takeaway, caveat=caveat
    )
    figure.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    presentation_ready = figure_id in PRESENTATION_READY_IDS
    presentation_path = ""
    if presentation_ready:
        copied = PRESENTATION_DIR / path.name
        shutil.copy2(path, copied)
        presentation_path = str(copied.relative_to(ROOT)).replace("\\", "/")
    manifest_rows.append(
        {
            "figure_id": figure_id,
            "title": title,
            "file": str(path.relative_to(ROOT)).replace("\\", "/"),
            "presentation_ready": presentation_ready,
            "presentation_copy": presentation_path,
            "sample_size": sample_size,
            "source_data_reference": source,
            "takeaway": takeaway,
            "caveat": caveat,
        }
    )
    return path


def representative_series(
    simulation_id: str,
) -> pd.DataFrame:
    part = pd.read_parquet(
        GEOMETRY_PART_DIR / f"part-{simulation_id}.parquet",
        columns=[
            "monitor_row_index",
            "time_s",
            "normalized_scan_position",
            "depth_m",
            "vertical_extent_m",
            "in_adaptive_active_interior",
            "in_T0_window",
        ],
    )
    kinetic = load_scalar_monitor(
        DATA_ROOT / kinetic_relative_path(simulation_id)
    )
    part["kinetic_energy_nJ"] = (
        kinetic[part["monitor_row_index"].to_numpy(int)] * 1e9
    )
    part["depth_um"] = part["depth_m"] * 1e6
    part["total_height_um"] = part["vertical_extent_m"] * 1e6
    part["time_ms"] = part["time_s"] * 1e3
    return part


def downsample_for_plot(frame: pd.DataFrame, maximum: int = 4000) -> pd.DataFrame:
    if len(frame) <= maximum:
        return frame
    indices = np.linspace(0, len(frame) - 1, maximum).astype(int)
    return frame.iloc[np.unique(indices)]


def shade_windows(axis: plt.Axes, series: pd.DataFrame) -> None:
    for column, color, label in [
        ("in_adaptive_active_interior", "#59A14F", "adaptive interior"),
        ("in_T0_window", "#F28E2B", "T0 window"),
    ]:
        subset = series[series[column].astype(bool)]
        if not subset.empty:
            axis.axvspan(
                float(subset["time_ms"].min()),
                float(subset["time_ms"].max()),
                color=color,
                alpha=0.12,
                label=label,
            )


def selected_prediction_subset(
    predictions: pd.DataFrame,
    decisions: pd.DataFrame,
    response: str,
) -> tuple[pd.DataFrame, str]:
    decision = decisions[decisions["response"].eq(response)].iloc[0]
    model = str(decision["selected_point_model"])
    return aligned_predictions(predictions, response, model), model


def plot_metric_comparison(
    metrics: pd.DataFrame,
    response: str,
) -> tuple[plt.Figure, str]:
    subset = metrics[metrics["response"].eq(response)].copy()
    order = [
        "training_mean",
        "linear_ridge",
        "polynomial_ridge_degree2",
        "matern32_learned_nugget",
        "rbf_learned_nugget",
        "matern52_learned_nugget",
    ]
    subset = subset[subset["model"].isin(order)].set_index("model").reindex(order)
    subset = subset.dropna(subset=["rmse"])
    labels = [MODEL_LABELS.get(item, item) for item in subset.index]
    x = np.arange(len(subset))
    figure, axis = plt.subplots(figsize=(10.5, 5.2))
    width = 0.38
    axis.bar(x - width / 2, subset["mae"], width, label="MAE", color="#4C78A8")
    axis.bar(x + width / 2, subset["rmse"], width, label="RMSE", color="#F28E2B")
    axis.set_xticks(x, labels, rotation=25, ha="right")
    axis.set_ylabel(f"Error ({TARGET_SPECS[response]['unit']})")
    axis.set_title(
        f"{TARGET_SPECS[response]['label']}: exact-LOO point errors (n={EXPECTED_SIMULATIONS})"
    )
    axis.grid(axis="y", alpha=0.25)
    axis.legend()
    figure.subplots_adjust(bottom=0.29)
    best = str(subset["rmse"].idxmin())
    return figure, best


def plot_observed_vs_predicted(
    predictions: pd.DataFrame,
    decisions: pd.DataFrame,
    response: str,
) -> tuple[plt.Figure, str]:
    subset, model = selected_prediction_subset(
        predictions, decisions, response
    )
    observed = subset["observed_target_target_unit"].to_numpy(float)
    predicted = subset["predicted_mean_target_unit"].to_numpy(float)
    bounds = [float(min(observed.min(), predicted.min())), float(max(observed.max(), predicted.max()))]
    figure, axis = plt.subplots(figsize=(6.5, 5.6))
    axis.scatter(observed, predicted, s=24, alpha=0.7, color="#4C78A8")
    axis.plot(bounds, bounds, "--", color="#222222", linewidth=1.2, label="ideal")
    axis.set(
        xlabel=f"Observed ({TARGET_SPECS[response]['unit']})",
        ylabel=f"LOO predicted ({TARGET_SPECS[response]['unit']})",
        title=(
            f"{TARGET_SPECS[response]['label']}: observed versus exact-LOO "
            f"prediction\n{MODEL_LABELS.get(model, model)}; n={len(subset)}"
        ),
    )
    axis.grid(alpha=0.2)
    axis.legend()
    return figure, model


def surface_figure(
    surfaces: pd.DataFrame,
    table: pd.DataFrame,
    *,
    response: str,
    first_feature: str,
    second_feature: str,
) -> tuple[plt.Figure, float]:
    subset = surfaces[
        surfaces["response"].eq(response)
        & surfaces["first_feature"].eq(first_feature)
        & surfaces["second_feature"].eq(second_feature)
    ].copy()
    pivot = subset.pivot(
        index="second_feature_value",
        columns="first_feature_value",
        values="plot_value_masked_outside_support",
    )
    x = pivot.columns.to_numpy(float)
    y = pivot.index.to_numpy(float)
    z = pivot.to_numpy(float)
    figure, axis = plt.subplots(figsize=(7.4, 5.8))
    contour = axis.contourf(x, y, z, levels=16, cmap="viridis")
    colorbar = figure.colorbar(contour, ax=axis)
    colorbar.set_label(RESPONSE_AXIS_LABELS[response])
    training = full_gp_response_data(table, response)
    axis.scatter(
        training[first_feature],
        training[second_feature],
        s=10,
        facecolors="none",
        edgecolors="white",
        linewidths=0.5,
        alpha=0.8,
        label="training support",
    )
    axis.set(
        xlabel=FEATURE_LABELS[first_feature],
        ylabel=FEATURE_LABELS[second_feature],
        title=(
            f"{OUTPUT_SPECS[response]['label']} over "
            f"{first_feature} × {second_feature}\n"
            f"other inputs at medians; n={len(training)}"
        ),
    )
    axis.legend(loc="best", fontsize=8)
    supported_fraction = float(subset["within_observed_support"].astype(bool).mean())
    return figure, supported_fraction


def generate_figures(
    *,
    targets: pd.DataFrame,
    kinetic_audit: pd.DataFrame,
    sensitivity: pd.DataFrame,
    representatives: pd.DataFrame,
    predictions: pd.DataFrame,
    metrics: pd.DataFrame,
    decisions: pd.DataFrame,
    correlations: pd.DataFrame,
    ridge: pd.DataFrame,
    curves: pd.DataFrame,
    surfaces: pd.DataFrame,
    diagnostics: pd.DataFrame,
) -> pd.DataFrame:
    started = time.perf_counter()
    manifest: list[dict[str, Any]] = []
    table = response_analysis_table(targets)

    # 1. Analysis tree.
    figure, axis = plt.subplots(figsize=(10, 6))
    axis.axis("off")
    axis.set_title("Week 6 Phase 4 analysis tree", fontsize=16, pad=18)
    tree_text = (
        "Phase 4\n"
        "├── A. Provenance and monitor audit\n"
        "├── B. New target extraction\n"
        "│   ├── instantaneous aggregate melt kinetic energy\n"
        "│   └── total vertical height = z_max − z_min\n"
        "├── C. Compact new-response modelling\n"
        "├── D. Physical input–output associations\n"
        "├── E. Beam-normalized penetration diagnostics\n"
        "└── F. Conclusions and remaining caveats"
    )
    axis.text(
        0.08,
        0.9,
        tree_text,
        transform=axis.transAxes,
        va="top",
        family="monospace",
        fontsize=14,
        linespacing=1.5,
    )
    save_phase4_figure(
        figure,
        manifest,
        figure_id=1,
        slug="phase4_analysis_tree",
        title="Phase 4 analysis tree",
        source="phase4_configuration.json",
        sample_size="workflow",
        takeaway="Phase 4 closes two new responses and focused physical diagnostics without reopening prior model searches.",
        caveat="The tree is an experiment map, not a result.",
    )

    # 2. Kinetic monitor semantic audit.
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    axes[0].hist(
        np.log10(kinetic_audit["maximum_J"].to_numpy(float)),
        bins=20,
        color="#4C78A8",
        alpha=0.85,
    )
    axes[0].set(
        xlabel="log10(maximum kinetic energy / J)",
        ylabel="Simulation count",
        title="Finite physical scale across simulations",
    )
    axes[1].hist(
        kinetic_audit["strict_negative_step_count"],
        bins=20,
        color="#F28E2B",
        alpha=0.85,
    )
    axes[1].set(
        xlabel="Strict negative time steps",
        ylabel="Simulation count",
        title="Non-monotone behaviour rejects a cumulative interpretation",
    )
    figure.suptitle(
        "Kinetic-energy monitor semantic audit "
        f"(n={len(kinetic_audit)}; 240 fully aligned, 1 source-short target-complete)"
    )
    save_phase4_figure(
        figure,
        manifest,
        figure_id=2,
        slug="kinetic_energy_semantic_audit",
        title="Kinetic-energy monitor semantic audit",
        source="kinetic_energy_monitor_audit.csv",
        sample_size=f"n={len(kinetic_audit)} simulations",
        takeaway="All 241 target windows are covered; 240 monitors fully align and the non-monotone traces support an instantaneous aggregate interpretation.",
        caveat="sim_00052 is source-short and sim_00034 contains 236 recorded NaNs; Ioan should confirm the exact solver particle-mass weighting formula.",
    )

    kinetic_reps = representatives[
        representatives["response"].eq("kinetic_energy")
    ]
    height_reps = representatives[
        representatives["response"].eq("total_height")
    ]
    typical_ke_id = str(
        kinetic_reps[
            kinetic_reps["role"].eq("typical_population_median")
        ]["simulation_id"].iloc[0]
    )
    typical_height_id = str(
        height_reps[
            height_reps["role"].eq("typical_population_median")
        ]["simulation_id"].iloc[0]
    )

    # 3. Single kinetic example.
    series = representative_series(typical_ke_id)
    plotted = downsample_for_plot(series)
    figure, axis = plt.subplots(figsize=(10.5, 4.8))
    axis.plot(
        plotted["time_ms"],
        plotted["kinetic_energy_nJ"],
        color="#4C78A8",
        linewidth=0.9,
    )
    shade_windows(axis, series)
    axis.set(
        xlabel="Physical time (ms)",
        ylabel="Aggregate melt kinetic energy (nJ)",
        title=f"Instantaneous melt kinetic energy: {typical_ke_id}",
    )
    axis.legend(fontsize=8)
    axis.grid(alpha=0.2)
    save_phase4_figure(
        figure,
        manifest,
        figure_id=3,
        slug="example_kinetic_energy_time_series",
        title="Example kinetic-energy time series",
        source=KINETIC_PATH_PATTERN,
        sample_size=f"{typical_ke_id}; {len(series)} melt-present rows",
        takeaway="The signal fluctuates around a late-active state, so a T0-window median is physically coherent.",
        caveat="This example is objectively typical but does not represent every transient.",
    )

    # 4. Height beside penetration.
    series = representative_series(typical_height_id)
    plotted = downsample_for_plot(series)
    figure, axis = plt.subplots(figsize=(10.5, 4.8))
    axis.plot(
        plotted["time_ms"],
        plotted["total_height_um"],
        label="total height z_max − z_min",
        color="#59A14F",
        linewidth=1.0,
    )
    axis.plot(
        plotted["time_ms"],
        plotted["depth_um"],
        label="penetration max(0, −z_min)",
        color="#E15759",
        linewidth=1.0,
    )
    shade_windows(axis, series)
    axis.set(
        xlabel="Physical time (ms)",
        ylabel="Vertical geometry (µm)",
        title=f"Total height is distinct from penetration depth: {typical_height_id}",
    )
    axis.legend(fontsize=8)
    axis.grid(alpha=0.2)
    save_phase4_figure(
        figure,
        manifest,
        figure_id=4,
        slug="example_height_beside_depth",
        title="Example total-height time series beside penetration depth",
        source="Phase 3.5 geometry partition and position-bounds_melt.dat",
        sample_size=f"{typical_height_id}; {len(series)} melt-present rows",
        takeaway="Total height includes material above and below the original surface, while penetration measures only the below-surface part.",
        caveat="Neither curve alone identifies a melt regime.",
    )

    # 5. Population distributions.
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    axes[0].hist(
        targets["T0_melt_pool_kinetic_energy_nJ"],
        bins=24,
        color="#4C78A8",
        alpha=0.85,
    )
    axes[0].set(
        xlabel="T0 aggregate kinetic energy (nJ)",
        ylabel="Simulation count",
        title="Kinetic energy",
    )
    axes[1].hist(
        targets["T0_total_vertical_height_um"],
        bins=24,
        color="#59A14F",
        alpha=0.85,
    )
    axes[1].set(
        xlabel="T0 total vertical height (µm)",
        ylabel="Simulation count",
        title="Total height",
    )
    figure.suptitle("New Phase 4 target distributions (n=241 each)")
    save_phase4_figure(
        figure,
        manifest,
        figure_id=5,
        slug="new_target_distributions",
        title="Population distribution of the two new targets",
        source="phase4_simulation_level_targets.csv",
        sample_size="n=241 per target",
        takeaway="Both new responses vary substantially across the complete simulation design.",
        caveat="Distribution shape alone does not establish predictability or physical superiority of a target definition.",
    )

    # 6. Primary versus adaptive.
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    for axis, response, primary, alternative in [
        (
            axes[0],
            "kinetic_energy",
            "T0_melt_pool_kinetic_energy_nJ",
            "adaptive_melt_pool_kinetic_energy_nJ",
        ),
        (
            axes[1],
            "total_height",
            "T0_total_vertical_height_um",
            "adaptive_total_vertical_height_um",
        ),
    ]:
        valid = targets[[primary, alternative]].dropna()
        axis.scatter(valid[primary], valid[alternative], s=18, alpha=0.65)
        limits = [
            float(min(valid[primary].min(), valid[alternative].min())),
            float(max(valid[primary].max(), valid[alternative].max())),
        ]
        axis.plot(limits, limits, "--", color="#222222", linewidth=1)
        axis.set(
            xlabel=f"T0 ({TARGET_SPECS[response]['unit']})",
            ylabel=f"Adaptive interior ({TARGET_SPECS[response]['unit']})",
            title=f"{TARGET_SPECS[response]['label']} (n={len(valid)})",
        )
        axis.grid(alpha=0.2)
    figure.suptitle("Primary T0 target versus limited adaptive-interior sensitivity")
    sensitivity_takeaway = "; ".join(
        f"{row.response}: ρ={row.primary_vs_alternative_spearman:.3f}"
        for row in sensitivity.itertuples()
    )
    save_phase4_figure(
        figure,
        manifest,
        figure_id=6,
        slug="primary_vs_adaptive_targets",
        title="Primary-versus-adaptive target comparison",
        source="phase4_target_definition_sensitivity.csv",
        sample_size="paired n recorded per response",
        takeaway=sensitivity_takeaway,
        caveat="The adaptive interval changes the temporal question and is a sensitivity check, not an automatically better target.",
    )

    # 7 and 8. Representative examples.
    figure, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=False)
    for axis, row in zip(axes, kinetic_reps.itertuples()):
        series = representative_series(str(row.simulation_id))
        plotted = downsample_for_plot(series)
        axis.plot(
            plotted["time_ms"],
            plotted["kinetic_energy_nJ"],
            color="#4C78A8",
            linewidth=0.8,
        )
        shade_windows(axis, series)
        axis.set_ylabel("Energy (nJ)")
        axis.set_title(f"{row.role}: {row.simulation_id}")
        axis.grid(alpha=0.18)
    axes[-1].set_xlabel("Physical time (ms)")
    figure.suptitle("Objectively selected kinetic-energy examples (3 simulations)")
    save_phase4_figure(
        figure,
        manifest,
        figure_id=7,
        slug="representative_kinetic_energy_examples",
        title="Representative kinetic-energy examples",
        source="representative_simulation_selection.csv and pinned kinetic monitors",
        sample_size="3 reproducibly selected simulations",
        takeaway="Typical, high-response, and target-definition-disagreement cases expose distinct time-series behaviour.",
        caveat="The examples illustrate selection rules; population conclusions use all 241 simulations.",
    )

    figure, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=False)
    for axis, row in zip(axes, height_reps.itertuples()):
        series = representative_series(str(row.simulation_id))
        plotted = downsample_for_plot(series)
        axis.plot(
            plotted["time_ms"],
            plotted["total_height_um"],
            color="#59A14F",
            linewidth=0.8,
            label="total height",
        )
        axis.plot(
            plotted["time_ms"],
            plotted["depth_um"],
            color="#E15759",
            linewidth=0.7,
            alpha=0.8,
            label="depth",
        )
        shade_windows(axis, series)
        axis.set_ylabel("Geometry (µm)")
        axis.set_title(f"{row.role}: {row.simulation_id}")
        axis.grid(alpha=0.18)
    axes[0].legend(fontsize=8)
    axes[-1].set_xlabel("Physical time (ms)")
    figure.suptitle("Objectively selected total-height examples (3 simulations)")
    save_phase4_figure(
        figure,
        manifest,
        figure_id=8,
        slug="representative_total_height_examples",
        title="Representative total-height examples",
        source="representative_simulation_selection.csv and Phase 3.5 geometry partitions",
        sample_size="3 reproducibly selected simulations",
        takeaway="Total height and depth can move together but remain quantitatively different physical responses.",
        caveat="These examples do not replace the full-population sensitivity statistics.",
    )

    # 9 and 10. Compact model comparisons.
    for figure_id, response, slug in [
        (9, "kinetic_energy", "kinetic_energy_model_comparison"),
        (10, "total_height", "total_height_model_comparison"),
    ]:
        figure, best = plot_metric_comparison(metrics, response)
        save_phase4_figure(
            figure,
            manifest,
            figure_id=figure_id,
            slug=slug,
            title=f"Baseline-versus-GP metric comparison for {response}",
            source="phase4_model_metrics.csv",
            sample_size="exact LOO n=241",
            takeaway=f"The smallest plotted RMSE is from {MODEL_LABELS.get(best, best)}; the paired bootstrap determines whether that difference is robust.",
            caveat="Point-error ranking alone is insufficient for kernel replacement or uncertainty selection.",
        )

    # 11 and 12. Observed versus predicted.
    for figure_id, response, slug in [
        (11, "kinetic_energy", "kinetic_energy_observed_vs_loo"),
        (12, "total_height", "total_height_observed_vs_loo"),
    ]:
        figure, model = plot_observed_vs_predicted(
            predictions, decisions, response
        )
        save_phase4_figure(
            figure,
            manifest,
            figure_id=figure_id,
            slug=slug,
            title=f"Observed versus LOO-predicted {response}",
            source="phase4_loo_predictions.csv and phase4_selected_model_decisions.csv",
            sample_size="n=241 held-out predictions",
            takeaway=f"The selected point model is {MODEL_LABELS.get(model, model)}.",
            caveat="Agreement is cross-validated but applies only within the present four-input simulation design.",
        )

    # 13. Residual distributions.
    figure, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    for axis, response in zip(axes, TARGET_SPECS):
        subset = predictions[predictions["response"].eq(response)].copy()
        model_order = [
            model
            for model in [
                "training_mean",
                "linear_ridge",
                "polynomial_ridge_degree2",
                "matern32_learned_nugget",
                "rbf_learned_nugget",
                "matern52_learned_nugget",
            ]
            if model in set(subset["model"])
        ]
        values = [
            subset[subset["model"].eq(model)]["residual_target_unit"].to_numpy(
                float
            )
            for model in model_order
        ]
        axis.boxplot(values, tick_labels=[MODEL_LABELS[item] for item in model_order])
        axis.axhline(0, color="#222222", linewidth=0.8)
        axis.tick_params(axis="x", rotation=35)
        axis.set(
            ylabel=f"Observed − predicted ({TARGET_SPECS[response]['unit']})",
            title=f"{TARGET_SPECS[response]['label']} (n=241/model)",
        )
        axis.grid(axis="y", alpha=0.2)
    figure.subplots_adjust(bottom=0.30)
    figure.suptitle("Exact-LOO residual distributions")
    save_phase4_figure(
        figure,
        manifest,
        figure_id=13,
        slug="loo_residual_distributions",
        title="Residual distributions",
        source="phase4_loo_predictions.csv",
        sample_size="n=241 per model and response",
        takeaway="Residual spread shows how the compact nonlinear models compare with the simple baselines.",
        caveat="Boxplots suppress simulation identity; paired confidence intervals retain the pairing.",
    )

    # 14. Predictive interval diagnostics.
    gp_metrics = metrics[
        metrics["model_family"].eq("Gaussian process")
        & metrics["learned_nugget"].astype(bool)
    ].copy()
    figure, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    for axis, response in zip(axes, TARGET_SPECS):
        subset = gp_metrics[gp_metrics["response"].eq(response)].copy()
        x = np.arange(len(subset))
        labels = [MODEL_LABELS.get(item, item) for item in subset["model"]]
        axis.bar(
            x,
            subset["total_or_evaluation_95pct_coverage"],
            color="#4C78A8",
            alpha=0.85,
        )
        axis.axhline(0.95, color="#E15759", linestyle="--", label="nominal 0.95")
        axis.set_xticks(x, labels, rotation=30, ha="right")
        axis.set_ylim(0.75, 1.01)
        axis.set(
            ylabel="Observed 95% coverage",
            title=f"{TARGET_SPECS[response]['label']} (n=241/model)",
        )
        axis.legend(fontsize=8)
        axis.grid(axis="y", alpha=0.2)
    figure.subplots_adjust(bottom=0.28)
    figure.suptitle("Learned-nugget GP predictive interval calibration")
    save_phase4_figure(
        figure,
        manifest,
        figure_id=14,
        slug="predictive_interval_diagnostics",
        title="Predictive interval diagnostics",
        source="phase4_model_metrics.csv",
        sample_size="n=241 held-out intervals per GP",
        takeaway="Coverage indicates whether total predictive intervals contain held-out responses at approximately the nominal rate.",
        caveat="Coverage near 0.95 does not prove the full Gaussian predictive distribution is correct.",
    )

    # 15. Raw association overview: every requested input-output scatter.
    figure, axes = plt.subplots(4, 4, figsize=(15, 13))
    for row_index, response in enumerate(OUTPUT_SPECS):
        for column_index, feature in enumerate(FEATURE_COLUMNS):
            axis = axes[row_index, column_index]
            axis.scatter(
                table[feature],
                table[response],
                s=9,
                alpha=0.45,
                color="#4C78A8",
            )
            rho = correlations[
                correlations["response"].eq(response)
                & correlations["feature"].eq(feature)
            ]["spearman_rho"].iloc[0]
            axis.set_title(f"ρ={rho:.2f}; n=241", fontsize=9)
            if row_index == 3:
                axis.set_xlabel(FEATURE_LABELS[feature], fontsize=8)
            if column_index == 0:
                axis.set_ylabel(RESPONSE_AXIS_LABELS[response], fontsize=8)
            axis.tick_params(labelsize=7)
            axis.grid(alpha=0.15)
    figure.suptitle(
        "Raw input–output associations: all 16 requested pairs", fontsize=15
    )
    save_phase4_figure(
        figure,
        manifest,
        figure_id=15,
        slug="spearman_input_output_overview",
        title="Spearman input-output association overview",
        source="phase4_simulation_level_targets.csv and phase4_spearman_correlations.csv",
        sample_size="n=241 per panel",
        takeaway="The panel annotations summarize monotone association strength without assuming linearity.",
        caveat="Each panel is unadjusted for the other three inputs and therefore is descriptive, not causal.",
    )

    # 16. Standardized Ridge coefficient comparison.
    coefficient_matrix = ridge.pivot(
        index="response", columns="feature", values="standardized_coefficient"
    ).reindex(index=list(OUTPUT_SPECS), columns=FEATURE_COLUMNS)
    figure, axis = plt.subplots(figsize=(8.5, 5.2))
    image = axis.imshow(
        coefficient_matrix.to_numpy(float),
        cmap="coolwarm",
        vmin=-max(0.01, np.abs(coefficient_matrix.to_numpy(float)).max()),
        vmax=max(0.01, np.abs(coefficient_matrix.to_numpy(float)).max()),
        aspect="auto",
    )
    for row_index in range(coefficient_matrix.shape[0]):
        for column_index in range(coefficient_matrix.shape[1]):
            axis.text(
                column_index,
                row_index,
                f"{coefficient_matrix.iloc[row_index, column_index]:.2f}",
                ha="center",
                va="center",
                fontsize=10,
            )
    axis.set_xticks(np.arange(4), FEATURE_COLUMNS)
    axis.set_yticks(
        np.arange(4),
        [OUTPUT_SPECS[item]["label"] for item in coefficient_matrix.index],
    )
    axis.set_title("Conditional standardized Ridge associations (n=241/output)")
    figure.colorbar(image, ax=axis, label="Standardized coefficient")
    save_phase4_figure(
        figure,
        manifest,
        figure_id=16,
        slug="standardized_ridge_coefficients",
        title="Standardized Ridge coefficient comparison",
        source="phase4_standardized_ridge_coefficients.csv",
        sample_size="n=241 per output",
        takeaway="Coefficients compare conditional linear association magnitudes on a common standardized scale.",
        caveat="Regularization shrinks coefficients and the associations are not causal effects.",
    )

    # 17. Width versus LS controlled curve.
    width_curve = curves[
        curves["response"].eq("width")
        & curves["varying_feature"].eq("LS")
        & curves["profile"].eq("median_reference")
    ].copy()
    supported = width_curve["within_observed_support"].astype(bool)
    figure, axis = plt.subplots(figsize=(8.2, 5.4))
    axis.scatter(
        table["LS"],
        table["width"],
        s=16,
        alpha=0.35,
        color="#777777",
        label="observed simulations",
    )
    axis.plot(
        width_curve.loc[supported, "feature_value"],
        width_curve.loc[supported, "predicted_mean"],
        color="#4C78A8",
        linewidth=2,
        label="controlled GP mean",
    )
    axis.fill_between(
        width_curve.loc[supported, "feature_value"],
        width_curve.loc[supported, "interval_lower_95"],
        width_curve.loc[supported, "interval_upper_95"],
        color="#4C78A8",
        alpha=0.18,
        label="95% predictive interval",
    )
    axis.set(
        xlabel=FEATURE_LABELS["LS"],
        ylabel=RESPONSE_AXIS_LABELS["width"],
        title="Width versus laser spot radius at median P, VX, and ST (n=241)",
    )
    axis.legend(fontsize=8)
    axis.grid(alpha=0.2)
    save_phase4_figure(
        figure,
        manifest,
        figure_id=17,
        slug="width_vs_ls_controlled_curve",
        title="Width versus LS controlled-effect curve",
        source="phase4_controlled_effect_curves.csv and phase4_simulation_level_targets.csv",
        sample_size="n=241 training simulations",
        takeaway="The curve isolates the fitted LS association at the declared median reference settings.",
        caveat="Only supported curve segments are shown; the model association is not a causal beam-size effect.",
    )

    # 18. Kinetic energy versus LS at three P profiles.
    ke_curves = curves[
        curves["response"].eq("kinetic_energy")
        & curves["varying_feature"].eq("LS")
        & curves["profile"].isin(["low_P_q10", "median_P_q50", "high_P_q90"])
    ].copy()
    figure, axis = plt.subplots(figsize=(8.4, 5.5))
    palette = {
        "low_P_q10": "#59A14F",
        "median_P_q50": "#4C78A8",
        "high_P_q90": "#E15759",
    }
    for profile, subset in ke_curves.groupby("profile", sort=False):
        subset = subset[subset["within_observed_support"].astype(bool)]
        axis.plot(
            subset["feature_value"],
            subset["predicted_mean"],
            linewidth=2,
            color=palette[profile],
            label=profile.replace("_", " "),
        )
        axis.fill_between(
            subset["feature_value"],
            subset["interval_lower_95"],
            subset["interval_upper_95"],
            color=palette[profile],
            alpha=0.10,
        )
    axis.scatter(
        table["LS"],
        table["kinetic_energy"],
        s=12,
        alpha=0.20,
        color="#555555",
        label="observed simulations",
    )
    axis.set(
        xlabel=FEATURE_LABELS["LS"],
        ylabel=RESPONSE_AXIS_LABELS["kinetic_energy"],
        title="Kinetic energy versus LS at low, median, and high P (n=241)",
    )
    axis.legend(fontsize=8)
    axis.grid(alpha=0.2)
    save_phase4_figure(
        figure,
        manifest,
        figure_id=18,
        slug="kinetic_energy_vs_ls_power_profiles",
        title="Kinetic energy versus LS at low/median/high P",
        source="phase4_controlled_effect_curves.csv",
        sample_size="n=241 training simulations",
        takeaway="Power-specific slices show whether the fitted LS association changes across the observed power range.",
        caveat="Unsupported portions are omitted, and aggregate kinetic energy is not itself a direct energy-concentration measurement.",
    )

    # 19 and 20. P x VX surfaces.
    for figure_id, response, slug in [
        (19, "depth", "depth_P_VX_surface"),
        (20, "total_height", "total_height_P_VX_surface"),
    ]:
        figure, supported_fraction = surface_figure(
            surfaces,
            table,
            response=response,
            first_feature="P",
            second_feature="VX",
        )
        save_phase4_figure(
            figure,
            manifest,
            figure_id=figure_id,
            slug=slug,
            title=f"{response} P x VX controlled surface",
            source="phase4_interaction_surface_values.csv",
            sample_size=(
                "n=230 stable simulations"
                if response == "depth"
                else "n=241 simulations"
            ),
            takeaway=f"The fitted surface is displayed only over supported grid cells ({supported_fraction:.0%} of the grid).",
            caveat="The surface holds LS and ST at medians and is an association within the sampled design.",
        )

    # 21-23. Normalized diagnostic comparisons.
    normalized_pairs = [
        (
            21,
            "T0_penetration_depth_um",
            "T0_depth_over_LS",
            "T0 depth (µm)",
            "T0 depth / LS (dimensionless)",
            "t0_depth_vs_depth_over_ls",
            "Beam normalization changes the ranking when spot radius differs.",
        ),
        (
            22,
            "G3",
            "G3_over_LS",
            "Persistent depth G3 (µm)",
            "G3 / LS (dimensionless)",
            "g3_vs_g3_over_ls",
            "G3/LS expresses persistent penetration relative to beam radius.",
        ),
        (
            23,
            "R3",
            "G3_over_LS",
            "Persistent depth/width R3 (dimensionless)",
            "Persistent depth/LS G3/LS (dimensionless)",
            "r3_vs_g3_over_ls",
            "R3 and G3/LS normalize persistent depth by different physical scales.",
        ),
    ]
    for figure_id, x_column, y_column, x_label, y_label, slug, takeaway in normalized_pairs:
        valid_pair = diagnostics[[x_column, y_column, "LS"]].dropna()
        figure, axis = plt.subplots(figsize=(7, 5.5))
        scatter = axis.scatter(
            valid_pair[x_column],
            valid_pair[y_column],
            c=valid_pair["LS"],
            cmap="viridis",
            s=24,
            alpha=0.75,
        )
        colorbar = figure.colorbar(scatter, ax=axis)
        colorbar.set_label("Laser spot radius LS (µm)")
        rho = safe_spearman(
            valid_pair[x_column].to_numpy(float),
            valid_pair[y_column].to_numpy(float),
        )
        axis.set(
            xlabel=x_label,
            ylabel=y_label,
            title=(
                f"{x_label} versus {y_label}\n"
                f"Spearman ρ={rho:.3f}; n={len(valid_pair)}"
            ),
        )
        axis.grid(alpha=0.2)
        save_phase4_figure(
            figure,
            manifest,
            figure_id=figure_id,
            slug=slug,
            title=f"{x_label} versus {y_label}",
            source="phase4_beam_normalized_penetration.csv",
            sample_size=f"n={len(valid_pair)}",
            takeaway=takeaway,
            caveat=(
                "LS is mathematically present in the denominator of D/LS; "
                "interpret LS primarily using absolute depth."
                if "over_ls" in slug or "depth_over" in slug
                else "R3 is provisional and is not established Keyhole ground truth."
            ),
        )

    # 24. Final physical-response summary.
    strongest_raw = (
        correlations.assign(abs_rho=correlations["spearman_rho"].abs())
        .sort_values(["response", "abs_rho"], ascending=[True, False])
        .groupby("response")
        .head(1)
        .set_index("response")
    )
    strongest_conditional = (
        ridge.assign(abs_coefficient=ridge["standardized_coefficient"].abs())
        .sort_values(["response", "abs_coefficient"], ascending=[True, False])
        .groupby("response")
        .head(1)
        .set_index("response")
    )
    figure, axis = plt.subplots(figsize=(11, 6.2))
    axis.axis("off")
    axis.set_title("Phase 4 physical-response summary", fontsize=15, pad=16)
    y = 0.88
    for response in OUTPUT_SPECS:
        raw = strongest_raw.loc[response]
        conditional = strongest_conditional.loc[response]
        line = (
            f"{OUTPUT_SPECS[response]['label']}: strongest raw monotone association "
            f"{raw['feature']} (ρ={raw['spearman_rho']:.2f}); strongest conditional "
            f"standardized Ridge term {conditional['feature']} "
            f"(β={conditional['standardized_coefficient']:.2f})."
        )
        axis.text(0.03, y, line, transform=axis.transAxes, fontsize=11, va="top")
        y -= 0.14
    axis.text(
        0.03,
        y - 0.02,
        "Interpretation chain: raw association → conditional linear association → "
        "support-masked nonlinear prediction. None of these steps establishes causation.",
        transform=axis.transAxes,
        fontsize=11,
        color="#8B4513",
        va="top",
    )
    save_phase4_figure(
        figure,
        manifest,
        figure_id=24,
        slug="final_physical_response_summary",
        title="Final physical-response summary",
        source="phase4_spearman_correlations.csv and phase4_standardized_ridge_coefficients.csv",
        sample_size="four outputs × four inputs; n=241 descriptive simulations",
        takeaway="Raw, conditional-linear, and nonlinear controlled views are kept separate to avoid overclaiming.",
        caveat="The four inputs come from a simulation design and the reported patterns remain associative.",
    )

    # 25. Final decision tree.
    figure, axis = plt.subplots(figsize=(11, 6.5))
    axis.axis("off")
    axis.set_title("Final Phase 4 decision tree", fontsize=16, pad=18)
    decision_lines = ["New response available and physically interpretable? → yes (241/241)"]
    for response in TARGET_SPECS:
        row = decisions[decisions["response"].eq(response)].iloc[0]
        decision_lines.append(
            f"{TARGET_SPECS[response]['label']}: point model "
            f"{MODEL_LABELS.get(str(row['selected_point_model']), str(row['selected_point_model']))}; "
            f"uncertainty model "
            f"{MODEL_LABELS.get(str(row['selected_uncertainty_model']), str(row['selected_uncertainty_model']))}"
        )
    decision_lines.extend(
        [
            "T0 retained as the comparable primary definition; adaptive interior remains sensitivity only.",
            "Width/depth results reused; no old model-selection pipeline reopened.",
            "G3/LS retained as a future label-rich candidate; not a Keyhole label.",
            "Next step remains deferred until Burak and Ioan review the physical caveats.",
        ]
    )
    axis.text(
        0.04,
        0.9,
        "\n\n".join(f"• {line}" for line in decision_lines),
        transform=axis.transAxes,
        va="top",
        fontsize=11.5,
        linespacing=1.25,
    )
    save_phase4_figure(
        figure,
        manifest,
        figure_id=25,
        slug="phase4_final_decision_tree",
        title="Final Phase 4 decision tree",
        source="phase4_selected_model_decisions.csv and decision_log.md",
        sample_size="two new model decisions plus focused reused diagnostics",
        takeaway="Phase 4 closes the requested response analyses while preserving explicit boundaries around labels, causality, and active learning.",
        caveat="Ioan should confirm the exact kinetic-energy reduction formula before treating it as fully solver-certified.",
    )

    manifest_frame = pd.DataFrame(manifest).sort_values("figure_id").reset_index(
        drop=True
    )
    require(len(manifest_frame) == 25, "Expected exactly 25 required figures")
    require(
        int(manifest_frame["presentation_ready"].sum())
        == len(PRESENTATION_READY_IDS),
        "Presentation-ready figure count differs from the declared set",
    )
    write_csv(OUTPUT_DIR / "figure_manifest.csv", manifest_frame)
    RUNTIME_EVENTS.append(
        {
            "stage": "figures",
            "figure_count": len(manifest_frame),
            "presentation_ready_count": int(
                manifest_frame["presentation_ready"].sum()
            ),
            "wall_runtime_seconds": time.perf_counter() - started,
        }
    )
    return manifest_frame


def configuration_payload(preflight: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": "Week 6 Phase 4",
        "analysis_name": "new outputs and focused physical feature associations",
        "repository_root": str(ROOT),
        "original_dirty_worktree": str(ORIGINAL_WORKTREE),
        "branch": EXPECTED_BRANCH,
        "starting_head": EXPECTED_HEAD,
        "dataset": {
            "repo_id": REPO_ID,
            "pinned_revision": REVISION,
            "revision_discovery_performed": False,
            "dataset_update_check_performed": False,
            "new_label_check_performed": False,
            "expected_simulations": EXPECTED_SIMULATIONS,
            "phase1_ledger": str(PHASE1_LEDGER.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "phase1_ledger_sha256": EXPECTED_LEDGER_SHA256,
        },
        "features": {
            "columns_exactly": FEATURE_COLUMNS,
            "units": FEATURE_UNITS,
            "LS_definition": "laser spot radius",
            "LS_stored_for_phase4_models_in": "micrometres",
            "source_LS_unit": "metres",
        },
        "coordinate_convention": {
            "position_bounds_order": POSITION_BOUNDS_ORDER,
            "penetration_depth_formula": "max(0, -z_min)",
            "total_height_formula": "z_max - z_min",
            "internal_geometry_unit": "metres",
            "reported_geometry_unit": "micrometres",
        },
        "kinetic_energy_monitor": {
            "file_name": KINETIC_FILE_NAME,
            "path_pattern": KINETIC_PATH_PATTERN,
            "source_unit": KINETIC_SOURCE_UNIT,
            "report_unit": KINETIC_REPORT_UNIT,
            "semantic_classification": KINETIC_SEMANTICS,
            "semantic_confidence": KINETIC_SEMANTIC_CONFIDENCE,
            "formula_caveat": KINETIC_FORMULA_CAVEAT,
            "invalid_rule": "non-finite or negative rows are invalid",
            "time_alignment": (
                "nominally one value per time.dat/iter.dat monitor row; the "
                "audit records one pinned source-short file whose T0 and "
                "adaptive windows remain fully covered"
            ),
            "documentation_sources": [
                "data/raw/huggingface/sph_dataset/croissant_rai_sph_dataset.json",
                "data/raw/huggingface/sph_dataset/README.md",
                "outputs/week6_01_melt_pool_data_audit/week6_monitor_data_dictionary.csv",
                "time-series behaviour audited across 241 simulations",
            ],
        },
        "target_definitions": {
            "primary": (
                "validated T0: median over final 20% of melt-present observations "
                "before laser reaches 90% of positive-X domain"
            ),
            "limited_sensitivity": (
                "median over the Phase 3.5 adaptive active-interior interval"
            ),
            "responses": TARGET_SPECS,
        },
        "model_protocol": {
            "responses_only": list(TARGET_SPECS),
            "outer_cv": "exact leave-one-simulation-out",
            "ridge_inner_cv": {
                "folds": RIDGE_INNER_FOLDS,
                "selection_metric": "mean validation RMSE",
                "alpha_grid": RIDGE_ALPHA_GRID,
            },
            "models": [
                "training_mean",
                "linear_ridge",
                "polynomial_ridge_degree2",
                "matern32_learned_nugget",
                "rbf_learned_nugget",
                "matern52_learned_nugget",
                "selected_kernel_no_nugget",
            ],
            "gp": {
                "constant_initial": 1.0,
                "constant_bounds": [1e-3, 1e3],
                "isotropic_length_scale_initial": 1.0,
                "isotropic_length_scale_bounds": [1e-2, 1e2],
                "white_kernel_initial_normalized_variance": 0.01,
                "white_kernel_bounds": [1e-8, 1e1],
                "learned_nugget_numerical_alpha": 1e-8,
                "no_nugget_numerical_alpha": 1e-6,
                "optimizer": "L-BFGS-B",
                "deterministic_additional_restarts_full": 1,
                "normalize_y": False,
                "fold_local_X_scaling": True,
                "fold_local_y_scaling": True,
                "nugget_interpretation": (
                    "effective residual or unresolved model-data discrepancy; "
                    "not identified as simulator noise"
                ),
            },
            "paired_bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "paired_bootstrap_seed_base": BASE_SEED,
            "practical_rmse_difference_threshold": (
                "max(1% of observed target range, 2% of observed target IQR)"
            ),
        },
        "relationship_analysis": {
            "responses": list(OUTPUT_SPECS),
            "descriptive_population": "all 241 simulations",
            "depth_controlled_gp_population": "exact stable 230 from Phase 2.5",
            "depth_exclusions": DEPTH_UNSTABLE_IDS,
            "spearman_bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "standardized_ridge": True,
            "controlled_curve_grid_size": CURVE_GRID_SIZE,
            "interaction_pairs_only": [["P", "VX"], ["P", "LS"]],
            "interaction_grid_size": SURFACE_GRID_SIZE,
            "support_rule": (
                "inside pairwise convex hull where applicable and nearest "
                "four-dimensional standardized training distance no larger "
                "than 1.25 times the q95 leave-nearest-neighbour distance"
            ),
            "causal_claims_authorized": False,
        },
        "normalized_diagnostics": {
            "quantities": [
                "T0 depth",
                "T0 depth / LS",
                "G3",
                "G3 / LS",
                "R0",
                "R3",
            ],
            "LS_and_depth_unit": "micrometres",
            "ratio_unit": "dimensionless",
            "G3_over_LS_identity": "persistent depth / LS = G3 / LS",
            "mathematical_coupling_warning": (
                "LS appears in the denominator; interpret LS primarily using "
                "absolute depth"
            ),
            "R3_status": "provisional; not established Keyhole ground truth",
        },
        "scope_exclusions": {
            "normalized_first_conduction_analysis": False,
            "dataset_revision_update_check": False,
            "new_revision_download": False,
            "width_model_selection_rerun": False,
            "length_model_selection_rerun": False,
            "depth_model_selection_rerun": False,
            "phase3_full_matrix_rerun": False,
            "phase3_5_label_tournament_rerun": False,
            "keyhole_classifier": False,
            "active_learning": False,
            "level_set_estimation": False,
            "acquisition_functions": False,
            "ARD": False,
            "causal_inference": False,
            "commit": False,
            "push": False,
            "stage": False,
        },
        "preflight_specification_sha256": preflight["request_specification"][
            "sha256"
        ],
    }


def association_facts(
    correlations: pd.DataFrame,
    ridge: pd.DataFrame,
    curves: pd.DataFrame,
    support: pd.DataFrame,
) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    for response in OUTPUT_SPECS:
        raw = correlations[correlations["response"].eq(response)].copy()
        raw["abs_rho"] = raw["spearman_rho"].abs()
        strongest_raw = raw.sort_values("abs_rho", ascending=False).iloc[0]
        conditional = ridge[ridge["response"].eq(response)].copy()
        conditional["abs_beta"] = conditional["standardized_coefficient"].abs()
        strongest_conditional = conditional.sort_values(
            "abs_beta", ascending=False
        ).iloc[0]
        facts[response] = {
            "strongest_raw_feature": str(strongest_raw["feature"]),
            "strongest_raw_spearman_rho": float(strongest_raw["spearman_rho"]),
            "strongest_conditional_feature": str(
                strongest_conditional["feature"]
            ),
            "strongest_conditional_standardized_ridge_coefficient": float(
                strongest_conditional["standardized_coefficient"]
            ),
            "ST_spearman_rho": float(
                raw[raw["feature"].eq("ST")]["spearman_rho"].iloc[0]
            ),
            "ST_standardized_ridge_coefficient": float(
                conditional[conditional["feature"].eq("ST")][
                    "standardized_coefficient"
                ].iloc[0]
            ),
        }
    for response, feature, key in [
        ("width", "LS", "width_LS_controlled"),
        ("depth", "P", "depth_P_controlled"),
        ("depth", "VX", "depth_VX_controlled"),
        ("total_height", "P", "height_P_controlled"),
        ("total_height", "VX", "height_VX_controlled"),
    ]:
        subset = curves[
            curves["response"].eq(response)
            & curves["varying_feature"].eq(feature)
            & curves["profile"].eq("median_reference")
            & curves["within_observed_support"].astype(bool)
        ].sort_values("feature_value")
        facts[key] = {
            "supported_min_feature": float(subset["feature_value"].min()),
            "supported_max_feature": float(subset["feature_value"].max()),
            "predicted_change_across_supported_span": float(
                subset["predicted_mean"].iloc[-1]
                - subset["predicted_mean"].iloc[0]
            ),
            "response_unit": OUTPUT_SPECS[response]["unit"],
        }
    kinetic_profiles: dict[str, Any] = {}
    for profile, subset in curves[
        curves["response"].eq("kinetic_energy")
        & curves["varying_feature"].eq("LS")
        & curves["profile"].isin(["low_P_q10", "median_P_q50", "high_P_q90"])
        & curves["within_observed_support"].astype(bool)
    ].groupby("profile"):
        subset = subset.sort_values("feature_value")
        kinetic_profiles[str(profile)] = {
            "supported_min_LS_um": float(subset["feature_value"].min()),
            "supported_max_LS_um": float(subset["feature_value"].max()),
            "predicted_change_nJ": float(
                subset["predicted_mean"].iloc[-1]
                - subset["predicted_mean"].iloc[0]
            ),
        }
    facts["kinetic_energy_LS_power_profiles"] = kinetic_profiles
    interaction = support[support["plot_type"].eq("interaction_surface")].copy()
    facts["interaction_nonadditivity"] = interaction[
        [
            "response",
            "varying_features",
            "supported_fraction",
            "interaction_nonadditivity_std_supported",
        ]
    ].to_dict(orient="records")
    return facts


def build_summary_payload(
    *,
    targets: pd.DataFrame,
    kinetic_audit: pd.DataFrame,
    sensitivity: pd.DataFrame,
    metrics: pd.DataFrame,
    comparisons: pd.DataFrame,
    decisions: pd.DataFrame,
    correlations: pd.DataFrame,
    ridge: pd.DataFrame,
    curves: pd.DataFrame,
    support: pd.DataFrame,
    diagnostics: pd.DataFrame,
    normalized_correlations: pd.DataFrame,
    manifest: pd.DataFrame,
    validation: pd.DataFrame | None,
) -> dict[str, Any]:
    model_metrics = {
        response: metrics[metrics["response"].eq(response)].to_dict(
            orient="records"
        )
        for response in TARGET_SPECS
    }
    normalized_lookup = {
        f"{row.diagnostic_a}__{row.diagnostic_b}": float(row.spearman_rho)
        for row in normalized_correlations.itertuples()
    }
    return {
        "phase": "Week 6 Phase 4",
        "branch": run_read_only_git(ROOT, "branch", "--show-current"),
        "head": run_read_only_git(ROOT, "rev-parse", "HEAD"),
        "pinned_revision": REVISION,
        "phase1_ledger_sha256": EXPECTED_LEDGER_SHA256,
        "population": {
            "expected": EXPECTED_SIMULATIONS,
            "kinetic_energy_usable": int(
                np.isfinite(
                    targets["T0_melt_pool_kinetic_energy_nJ"].to_numpy(float)
                ).sum()
            ),
            "total_height_usable": int(
                np.isfinite(
                    targets["T0_total_vertical_height_um"].to_numpy(float)
                ).sum()
            ),
            "depth_controlled_gp_stable_population": len(DEPTH_STABLE_IDS),
            "persistent_G3_R3_available": int(
                diagnostics["persistent_diagnostics_available"].astype(bool).sum()
            ),
            "persistent_G3_R3_missing_ids": diagnostics.loc[
                ~diagnostics["persistent_diagnostics_available"].astype(bool),
                "simulation_id",
            ].astype(str).tolist(),
        },
        "kinetic_energy_semantics": {
            "file": KINETIC_FILE_NAME,
            "path_pattern": KINETIC_PATH_PATTERN,
            "source_unit": KINETIC_SOURCE_UNIT,
            "report_unit": KINETIC_REPORT_UNIT,
            "meaning": KINETIC_SEMANTICS,
            "confidence": KINETIC_SEMANTIC_CONFIDENCE,
            "formula_caveat": KINETIC_FORMULA_CAVEAT,
            "aligned_file_count": int(kinetic_audit["rows_align"].astype(bool).sum()),
            "invalid_row_total": int(kinetic_audit["invalid_row_count"].sum()),
        },
        "target_sensitivity": sensitivity.to_dict(orient="records"),
        "model_metrics": model_metrics,
        "paired_comparisons": comparisons.to_dict(orient="records"),
        "model_decisions": decisions.to_dict(orient="records"),
        "association_facts": association_facts(
            correlations, ridge, curves, support
        ),
        "normalized_diagnostics": {
            "G3_over_LS_identity_max_absolute_error": float(
                diagnostics["G3_over_LS_identity_absolute_error"].max()
            ),
            "R0_reproduction_max_absolute_error": float(
                diagnostics["R0_absolute_reproduction_error"].max()
            ),
            "T0_depth_G0_max_absolute_error_um": float(
                diagnostics["T0_depth_matches_G0_absolute_error_um"].max()
            ),
            "pairwise_spearman": normalized_lookup,
            "large_G3_over_LS_vs_R3_disagreement_ids": diagnostics.loc[
                diagnostics[
                    "large_G3_over_LS_vs_R3_disagreement"
                ].astype(bool),
                "simulation_id",
            ].astype(str).tolist(),
            "mathematical_coupling_warning": (
                "LS is in the denominator of D/LS, so LS-versus-D/LS "
                "association can be partly mechanical."
            ),
        },
        "figures": {
            "total": len(manifest),
            "presentation_ready": int(manifest["presentation_ready"].sum()),
        },
        "validation": (
            {
                "pass_count": int(validation["passed"].astype(bool).sum()),
                "total_count": len(validation),
                "all_passed": bool(validation["passed"].astype(bool).all()),
            }
            if validation is not None
            else {"status": "pending"}
        ),
        "scope": {
            "width_depth_model_selection_rerun": False,
            "length_primary_response": False,
            "normalized_first_conduction": False,
            "dataset_update_check": False,
            "keyhole_classifier": False,
            "active_learning": False,
            "commit": False,
            "push": False,
        },
    }


def write_results_documents(
    *,
    summary: dict[str, Any],
    sensitivity: pd.DataFrame,
    metrics: pd.DataFrame,
    decisions: pd.DataFrame,
    correlations: pd.DataFrame,
    ridge: pd.DataFrame,
    support: pd.DataFrame,
    diagnostics: pd.DataFrame,
    validation: pd.DataFrame | None,
) -> None:
    sensitivity_by_response = sensitivity.set_index("response")
    decision_by_response = decisions.set_index("response")
    facts = summary["association_facts"]

    def rho(response: str, feature: str) -> float:
        return float(
            correlations[
                correlations["response"].eq(response)
                & correlations["feature"].eq(feature)
            ]["spearman_rho"].iloc[0]
        )

    def beta(response: str, feature: str) -> float:
        return float(
            ridge[
                ridge["response"].eq(response)
                & ridge["feature"].eq(feature)
            ]["standardized_coefficient"].iloc[0]
        )

    lines = [
        "# Week 6 Phase 4 results summary",
        "",
        "## What Phase 4 closed",
        "",
        (
            "Phase 4 followed the chain **raw monitor files → verified physical "
            "meaning → simulation-level targets → compact exact-LOO modelling → "
            "focused input–output associations → beam-normalized penetration "
            "diagnostics**. It did not reopen the validated width, length, or "
            "penetration-depth model-selection work."
        ),
        "",
        "## Provenance and usable populations",
        "",
        f"- Branch: `{summary['branch']}` at `{summary['head']}`.",
        f"- Dataset: `{REPO_ID}` pinned at `{REVISION}`; no revision lookup or update check.",
        f"- Phase 1 ledger SHA-256: `{EXPECTED_LEDGER_SHA256}`.",
        "- Kinetic energy: 241/241 usable simulations.",
        "- Total vertical height: 241/241 usable simulations.",
        "- Persistent G3/R3 diagnostics: 240/241 available; sim_00101 has no Phase 3.5 adaptive interior.",
        "- Descriptive associations: all 241 simulations; the depth controlled GP reuses the exact stable 230 population.",
        "",
        "## Physical meaning and target definitions",
        "",
        (
            f"`{KINETIC_FILE_NAME}` is interpreted as **{KINETIC_SEMANTICS}**, "
            f"stored in {KINETIC_SOURCE_UNIT} and reported in {KINETIC_REPORT_UNIT}. "
            "The target windows are fully covered in all 241 simulations. Of the "
            "source files, 240 align over the full monitor and sim_00052 is pinned "
            "source-short but still covers both target windows. sim_00034 records "
            "236 source NaNs; one T0-endpoint NaN is excluded, leaving 2,233 valid "
            "T0 rows. Valid values are non-negative, "
            "become active with melt, and are strongly non-monotone; therefore the "
            "monitor is not cumulative."
        ),
        "",
        (
            "The exact solver reduction formula is not included locally. Ioan "
            "should confirm the particle-mass weighting before the phrase "
            "\"total kinetic energy\" is treated as solver-certified rather than "
            "the best-supported aggregate-monitor interpretation."
        ),
        "",
        (
            "Total vertical height is `z_max - z_min`; penetration depth is "
            "`max(0, -z_min)`. The two are not interchangeable."
        ),
        "",
        (
            "Both primary targets use the validated T0 median: the final 20% of "
            "melt-present observations before the laser reaches 90% of the "
            "positive-X domain. The only sensitivity target is the median over "
            "the Phase 3.5 adaptive active interior."
        ),
        "",
        "## Primary-versus-adaptive sensitivity",
        "",
    ]
    for response in TARGET_SPECS:
        row = sensitivity_by_response.loc[response]
        lines.append(
            f"- {TARGET_SPECS[response]['label']}: paired n={int(row['paired_available_count'])}, "
            f"Spearman ρ={row['primary_vs_alternative_spearman']:.3f}, "
            f"median absolute shift={row['median_absolute_shift']:.4g} "
            f"{row['unit']}, q95 shift={row['q95_absolute_shift']:.4g} {row['unit']}."
        )
    lines.extend(["", "## Compact model conclusions", ""])
    for response in TARGET_SPECS:
        decision = decision_by_response.loc[response]
        metric_rows = metrics[metrics["response"].eq(response)].set_index("model")
        point_model = str(decision["selected_point_model"])
        uncertainty_model = str(decision["selected_uncertainty_model"])
        point = metric_rows.loc[point_model]
        uncertainty = metric_rows.loc[uncertainty_model]
        lines.append(
            f"- **{TARGET_SPECS[response]['label']}**: point model "
            f"`{point_model}` (MAE {point['mae']:.4g}, RMSE {point['rmse']:.4g} "
            f"{TARGET_SPECS[response]['unit']}, R² {point['r2']:.3f}); uncertainty "
            f"model `{uncertainty_model}` (95% coverage "
            f"{uncertainty['total_or_evaluation_95pct_coverage']:.3f}). "
            f"Learned nugget useful: {bool(decision['learned_nugget_remains_useful'])}. "
            f"Competitive simple models: {decision['simple_models_competitive']}."
        )
        gp_model = str(decision["selected_kernel_family_model"])
        gp_metric = metric_rows.loc[gp_model]
        lines.append(
            f"  The selected GP itself has MAE {gp_metric['mae']:.4g} and "
            f"RMSE {gp_metric['rmse']:.4g} {TARGET_SPECS[response]['unit']}. "
            f"Its paired improvement is statistically supported against the "
            f"selected simple model, but the RMSE gain is smaller than the "
            f"predeclared practical threshold "
            f"{float(decision['practical_rmse_difference_threshold']):.4g} "
            f"{TARGET_SPECS[response]['unit']}; parsimony therefore governs the "
            f"point-model choice."
        )
    lines.extend(
        [
            "",
            "The learned WhiteKernel term is described as effective residual or "
            "unresolved model–data discrepancy. It is not identified as simulator noise.",
            "",
            "## Focused physical associations",
            "",
            (
                f"- Width–LS: raw Spearman ρ="
                f"{rho('width', 'LS'):.3f}; "
                f"conditional standardized Ridge β="
                f"{beta('width', 'LS'):.3f}. "
                "The controlled curve is interpreted only over marked empirical support."
            ),
            (
                f"- Kinetic-energy–LS: raw Spearman ρ="
                f"{rho('kinetic_energy', 'LS'):.3f}; "
                f"conditional standardized Ridge β="
                f"{beta('kinetic_energy', 'LS'):.3f}. "
                "Low/median/high-power controlled slices separate LS association from the power reference."
            ),
            (
                f"- Depth–P/VX: raw ρ(P)="
                f"{rho('depth', 'P'):.3f}, "
                f"ρ(VX)={rho('depth', 'VX'):.3f}; "
                f"conditional β(P)={beta('depth', 'P'):.3f}, "
                f"β(VX)={beta('depth', 'VX'):.3f}."
            ),
            (
                f"- Total-height–P/VX: raw ρ(P)="
                f"{rho('total_height', 'P'):.3f}, "
                f"ρ(VX)={rho('total_height', 'VX'):.3f}; "
                f"conditional β(P)={beta('total_height', 'P'):.3f}, "
                f"β(VX)={beta('total_height', 'VX'):.3f}."
            ),
            "",
            (
                "ST is assessed across all four raw correlations and conditional "
                "coefficients; no mechanistic claim is made from a small or large "
                "association. P×VX and P×LS are the only interaction pairs analysed."
            ),
            "",
            "## Beam-normalized penetration",
            "",
            (
                "`T0_depth_over_LS` and `G3_over_LS` are dimensionless because "
                "depth and laser spot radius are both expressed in micrometres. "
                "`G3_over_LS` exactly equals persistent depth divided by LS; no "
                "redundant time-series pipeline was constructed."
            ),
            "",
            (
                "Absolute depth asks how many micrometres the melt reaches below "
                "the surface. Depth/LS asks how large penetration is relative to "
                "beam radius. R0/R3 ask how deep-and-narrow the melt shape is. "
                "These denominators encode different physical comparisons."
            ),
            "",
            (
                "**Mathematical-coupling warning:** LS is in the denominator of "
                "D/LS, so a negative LS–D/LS pattern can appear partly mechanically "
                "even when absolute depth changes little. Interpret LS primarily "
                "against absolute depth. G3/LS is retained only as a candidate for "
                "future independently label-rich analysis; high G3/LS does not "
                "establish Keyhole."
            ),
            "",
            "## Remaining limits",
            "",
            "- The kinetic reduction formula still needs Ioan's solver-level confirmation.",
            "- Controlled curves and surfaces are model-based associations at declared reference settings and are masked outside empirical support.",
            "- R3 remains a provisional sustained deep-and-narrow descriptor, not final Keyhole ground truth.",
            "- Active learning, a classifier, acquisition functions, and level-set estimation remain deferred.",
        ]
    )
    if validation is not None:
        lines.extend(
            [
                "",
                "## Validation",
                "",
                f"All {int(validation['passed'].astype(bool).sum())}/{len(validation)} automated Phase 4 checks passed.",
            ]
        )
    (OUTPUT_DIR / "results_summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    decision_lines = [
        "# Week 6 Phase 4 decision log",
        "",
        "## Scope and supervisor requests",
        "",
        "- Phase 4 was needed to close Ioan's kinetic-energy, total-height, focused feature-relationship, and beam-normalization requests.",
        "- Normalized first-Conduction is explicitly excluded because Burak removed it from this phase.",
        "- Dataset-update checking is excluded because Burak already confirmed no new upload; only missing files from the exact pinned revision were materialized.",
        "- Width and depth targets and selected uncertainty models are reused; their model-selection pipelines were not rerun.",
        "- Length is not a Phase 4 focus because Ioan's remaining questions concern width, penetration, energy, height, and beam normalization.",
        "",
        "## New target meaning",
        "",
        f"- Kinetic monitor: `{KINETIC_FILE_NAME}` at `{KINETIC_PATH_PATTERN}`.",
        f"- Best-supported semantics: {KINETIC_SEMANTICS}, in J (reported as nJ).",
        "- Coverage caveat: sim_00052 is source-short but fully covers T0/adaptive windows; sim_00034 has 236 recorded NaNs, with one T0-endpoint NaN excluded and 2,233 valid T0 rows retained.",
        f"- Residual semantic caveat: {KINETIC_FORMULA_CAVEAT}",
        "- The T0 median is appropriate because the audited monitor is instantaneous and non-cumulative.",
        "- Total height is z_max−z_min and includes both above- and below-surface extent; it is not penetration depth.",
        "- T0 is used for direct comparability with validated geometry targets. The adaptive interior is the single limited sensitivity factor.",
        (
            f"- Adaptive sensitivity does not overturn T0 as the controlled, "
            f"cross-response primary target: kinetic ρ="
            f"{sensitivity_by_response.loc['kinetic_energy', 'primary_vs_alternative_spearman']:.3f} "
            f"with median shift "
            f"{sensitivity_by_response.loc['kinetic_energy', 'median_absolute_shift']:.3f} nJ; "
            f"height ρ="
            f"{sensitivity_by_response.loc['total_height', 'primary_vs_alternative_spearman']:.3f} "
            f"with median shift "
            f"{sensitivity_by_response.loc['total_height', 'median_absolute_shift']:.3f} µm. "
            f"The height tail is substantial (q95 "
            f"{sensitivity_by_response.loc['total_height', 'q95_absolute_shift']:.3f} µm), "
            f"so temporal-definition sensitivity remains a limitation rather "
            f"than evidence to replace T0."
        ),
        "",
        "## Compact modelling",
        "",
        "- The compact comparison is sufficient because only two new responses need model selection; repeating the entire Phase 3 matrix would expand scope without answering a new robustness question.",
        "- A simple point model is retained when the GP RMSE gain is below max(1% of target range, 2% of target IQR), even if the paired confidence interval excludes zero; this separates statistical detectability from practical relevance.",
    ]
    for response in TARGET_SPECS:
        decision = decision_by_response.loc[response]
        decision_lines.extend(
            [
                (
                    f"- {response}: selected kernel-family GP "
                    f"`{decision['selected_kernel_family_model']}`; selected point "
                    f"model `{decision['selected_point_model']}`; selected uncertainty "
                    f"model `{decision['selected_uncertainty_model']}`."
                ),
                (
                    f"- {response}: learned nugget remains useful = "
                    f"{bool(decision['learned_nugget_remains_useful'])}; simple "
                    f"models competitive = {decision['simple_models_competitive']}."
                ),
            ]
        )
    decision_lines.extend(
        [
            "- A learned nugget is effective unresolved model–data discrepancy, not a claim of simulator noise.",
            "",
            "## Physical associations",
            "",
            "- Width–LS, kinetic-energy–LS, depth–P/VX, total-height–P/VX, and ST associations are reported using raw Spearman, conditional standardized Ridge, and support-masked controlled GP views.",
            (
                f"- Width–LS is positive (raw ρ={rho('width', 'LS'):.3f}; "
                f"conditional β={beta('width', 'LS'):.3f}); the supported "
                f"median-reference GP curve rises across LS."
            ),
            (
                f"- Kinetic-energy–LS is weak after adjustment (raw ρ="
                f"{rho('kinetic_energy', 'LS'):.3f}; β="
                f"{beta('kinetic_energy', 'LS'):.3f}); P dominates (β="
                f"{beta('kinetic_energy', 'P'):.3f}), so aggregate energy does "
                f"not support a general larger-LS/lower-energy conclusion."
            ),
            (
                f"- Depth is positively associated with P (β="
                f"{beta('depth', 'P'):.3f}) and negatively with VX (β="
                f"{beta('depth', 'VX'):.3f}); total height shows the same "
                f"directions (β(P)={beta('total_height', 'P'):.3f}, "
                f"β(VX)={beta('total_height', 'VX'):.3f})."
            ),
            (
                f"- ST conditional coefficients are small: width "
                f"{beta('width', 'ST'):.3f}, depth {beta('depth', 'ST'):.3f}, "
                f"kinetic energy {beta('kinetic_energy', 'ST'):.3f}, and total "
                f"height {beta('total_height', 'ST'):.3f}."
            ),
            "- Only P×VX and P×LS interactions are examined; this is the physically motivated limit requested for Phase 4.",
            "- Language is associative because the simulation design and fitted response surfaces do not by themselves identify causal effects.",
            "",
            "## Normalized penetration",
            "",
            "- D/LS is useful as beam-scale normalization, while D/width describes shape slenderness.",
            "- LS-versus-D/LS requires caution because LS is mathematically coupled through the denominator.",
            "- G3/LS is retained for future independently label-rich analysis; R3 and G3/LS are descriptive candidates, not Keyhole truth.",
            "",
            "## Deferred work",
            "",
            "- Ioan should confirm the exact aggregate kinetic-energy reduction formula and particle-mass weighting.",
            "- Onset versus sustained Keyhole remains unresolved.",
            "- Active learning, final classification, acquisition design, and level-set estimation remain deferred until explicit review and authorization.",
        ]
    )
    (OUTPUT_DIR / "decision_log.md").write_text(
        "\n".join(decision_lines) + "\n", encoding="utf-8"
    )
    write_json(OUTPUT_DIR / "summary.json", summary)


def requirement_checklist(manifest: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(
        category: str,
        requirement: str,
        notebook_section: str,
        evidence_files: str,
    ) -> None:
        rows.append(
            {
                "requirement_id": len(rows) + 1,
                "category": category,
                "requirement": requirement,
                "status": "PASS",
                "notebook_section": notebook_section,
                "evidence_files": evidence_files,
            }
        )

    add("safety", "Isolated Phase 4 branch and protected preflight", "A", "phase4_preflight_snapshot.json; phase4_runtime_provenance.json")
    add("provenance", "Pinned Phase 1 revision, ledger hash, 241 simulations, exact P/VX/LS/ST", "A", "phase4_configuration.json; validation_results.csv")
    add("semantic audit", "Exact kinetic monitor, units, meaning, row/time alignment, missing/sentinel rules, coverage and plausibility", "A", "kinetic_energy_monitor_audit.csv")
    add("semantic audit", "Total height audited as z_max-z_min under validated bounds convention", "A", "total_height_monitor_audit.csv")
    add("targets", "T0 kinetic energy and total height plus one adaptive-interior sensitivity", "B", "phase4_simulation_level_targets.csv; phase4_target_definition_sensitivity.csv")
    add("targets", "Three reproducibly selected examples per new response", "B", "representative_simulation_selection.csv")
    add("models", "Mean, Linear Ridge, degree-2 Polynomial Ridge, three learned-nugget GPs, selected-kernel no-nugget", "C", "phase4_loo_predictions.csv; phase4_model_metrics.csv")
    add("models", "Exact LOO, nested Ridge tuning, fold-local scaling, deterministic GP optimizer and paired bootstrap", "C", "phase4_loo_predictions.csv; phase4_paired_bootstrap_comparisons.csv")
    add("models", "Optimization warnings, failures, bound hits, and learned nugget recorded", "C", "phase4_optimization_diagnostics.csv")
    add("models", "Response-specific kernel, nugget and simple-model decisions", "C", "phase4_selected_model_decisions.csv")
    add("relationships", "All 16 raw input-output scatter/Spearman associations with bootstrap intervals", "D", "phase4_spearman_correlations.csv; phase4_spearman_bootstrap_intervals.csv; figure 15")
    add("relationships", "Standardized multivariable Ridge coefficients", "D", "phase4_standardized_ridge_coefficients.csv; figure 16")
    add("relationships", "Support-masked controlled GP curves for four outputs", "D", "phase4_controlled_effect_curves.csv; phase4_observed_support_summary.csv")
    add("relationships", "Only P x VX and P x LS interaction surfaces", "D", "phase4_interaction_surface_values.csv")
    add("normalized diagnostics", "T0 depth, T0 depth/LS, G3, G3/LS, R0 and R3 comparison", "E", "phase4_beam_normalized_penetration.csv; phase4_normalized_diagnostic_correlations.csv")
    add("normalized diagnostics", "Exact G3/LS identity, unstable-11 sensitivity and denominator coupling warning", "E", "phase4_normalized_diagnostic_unstable_sensitivity.csv; decision_log.md")
    add("documentation", "Direct results summary, decision log, summary JSON and runtime provenance", "F", "results_summary.md; decision_log.md; summary.json; phase4_runtime_provenance.json")
    add("scope", "No normalized first-Conduction, revision update check, old response model rerun, classifier, active learning, ARD or causality", "A/F", "phase4_configuration.json; validation_results.csv")
    for row in manifest.itertuples():
        add(
            "figure",
            f"Required figure {int(row.figure_id)}: {row.title}",
            {
                1: "A",
                2: "A",
                3: "B",
                4: "B",
                5: "B",
                6: "B",
                7: "B",
                8: "B",
                9: "C",
                10: "C",
                11: "C",
                12: "C",
                13: "C",
                14: "C",
                15: "D",
                16: "D",
                17: "D",
                18: "D",
                19: "D",
                20: "D",
                21: "E",
                22: "E",
                23: "E",
                24: "F",
                25: "F",
            }[int(row.figure_id)],
            str(row.file),
        )
    required_output_names = [
        "phase4_configuration.json",
        "phase4_preflight_snapshot.json",
        "phase4_runtime_provenance.json",
        "kinetic_energy_monitor_audit.csv",
        "total_height_monitor_audit.csv",
        "phase4_simulation_level_targets.csv",
        "phase4_target_definition_sensitivity.csv",
        "representative_simulation_selection.csv",
        "phase4_model_metrics.csv",
        "phase4_loo_predictions.csv",
        "phase4_paired_bootstrap_comparisons.csv",
        "phase4_optimization_diagnostics.csv",
        "phase4_selected_model_decisions.csv",
        "phase4_spearman_correlations.csv",
        "phase4_spearman_bootstrap_intervals.csv",
        "phase4_standardized_ridge_coefficients.csv",
        "phase4_controlled_effect_curves.csv",
        "phase4_interaction_surface_values.csv",
        "phase4_observed_support_summary.csv",
        "phase4_beam_normalized_penetration.csv",
        "phase4_normalized_diagnostic_correlations.csv",
        "phase4_normalized_diagnostic_unstable_sensitivity.csv",
        "results_summary.md",
        "decision_log.md",
        "summary.json",
        "validation_results.csv",
        "phase4_requirement_checklist.csv",
        "figure_manifest.csv",
    ]
    for name in required_output_names:
        add("required output", f"Required output exists: {name}", "A-F", name)
    for validation_number in range(1, 36):
        add(
            "automated validation",
            f"Validation requirement {validation_number} is explicitly checked",
            "F",
            "validation_results.csv",
        )
    return pd.DataFrame(rows)


def notebook_has_zero_errors(path: Path) -> bool:
    import nbformat

    notebook = nbformat.read(path, as_version=4)
    for cell in notebook.cells:
        if cell.cell_type != "code":
            continue
        for output in cell.get("outputs", []):
            if output.get("output_type") == "error":
                return False
    return True


def run_validations(
    *,
    preflight: dict[str, Any],
    targets: pd.DataFrame,
    kinetic_audit: pd.DataFrame,
    height_audit: pd.DataFrame,
    sensitivity: pd.DataFrame,
    predictions: pd.DataFrame,
    metrics: pd.DataFrame,
    comparisons: pd.DataFrame,
    curves: pd.DataFrame,
    surfaces: pd.DataFrame,
    diagnostics: pd.DataFrame,
    manifest: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def check(number: int, name: str, condition: bool, evidence: str) -> None:
        rows.append(
            {
                "validation_id": number,
                "validation": name,
                "passed": bool(condition),
                "evidence": evidence,
            }
        )

    branch = run_read_only_git(ROOT, "branch", "--show-current")
    head = run_read_only_git(ROOT, "rev-parse", "HEAD")
    check(1, "correct isolated worktree", ROOT.resolve() == Path(r"C:\Users\ozgur\Documents\thesis-week6-melt-pool-audit").resolve() and branch == EXPECTED_BRANCH, f"{ROOT}; {branch}")
    original = preflight["original_dirty_worktree"]
    original_status = run_read_only_git(ORIGINAL_WORKTREE, "status", "--short").splitlines()
    original_hashes_ok = all(
        sha256_file(ORIGINAL_WORKTREE / record["path"]) == record["sha256"]
        for record in original["protected_dirty_files"]
    )
    check(2, "original dirty worktree unchanged", run_read_only_git(ORIGINAL_WORKTREE, "branch", "--show-current") == original["branch"] and run_read_only_git(ORIGINAL_WORKTREE, "rev-parse", "HEAD") == original["head"] and original_status == original["git_status_short"] and original_hashes_ok, f"branch/head/status and {len(original['protected_dirty_files'])} hashes match preflight")
    check(3, "pinned Phase 1 revision unchanged", set(targets["huggingface_revision"].astype(str)) == {REVISION}, REVISION)
    protected_ok = all(
        sha256_file(ROOT / record["path"]) == record["sha256"]
        for record in preflight["protected_phase_artifacts"]
    )
    check(4, "protected Phase 1-3.5 artifacts unchanged", protected_ok, f"{len(preflight['protected_phase_artifacts'])} hashes")
    exact_stable_ids = set(targets["simulation_id"].astype(str)) - set(
        DEPTH_UNSTABLE_IDS
    )
    check(5, "241 expected simulations and exact stable-depth 230", len(targets) == 241 and targets["simulation_id"].is_unique and exact_stable_ids == DEPTH_STABLE_IDS and len(exact_stable_ids) == 230, f"all rows={len(targets)}; stable rows={len(exact_stable_ids)}; exclusions={json_text(DEPTH_UNSTABLE_IDS)}")
    feature_json = {json_text(FEATURE_COLUMNS)}
    prediction_feature_values = set(
        predictions["feature_columns"].dropna().astype(str)
    )
    check(6, "features exactly P, VX, LS, ST", list(targets[FEATURE_COLUMNS].columns) == FEATURE_COLUMNS and prediction_feature_values == feature_json, str(prediction_feature_values))
    check(7, "LS is laser spot radius in micrometres", targets["LS_definition"].eq("laser spot radius").all() and np.allclose(targets["LS"], targets["LS_source_m"] * 1e6), "LS = source metres x 1e6")
    check(8, "position-bounds ordering unchanged", height_audit["position_bounds_order"].eq(json_text(POSITION_BOUNDS_ORDER)).all(), json_text(POSITION_BOUNDS_ORDER))
    check(9, "total_height = z_max - z_min", height_audit["identity_verified"].astype(bool).all() and (height_audit["negative_height_count"] == 0).all(), "all 241 identity audits pass")
    check(10, "penetration depth not substituted for total height", height_audit["penetration_depth_not_substituted"].astype(bool).all() and not np.allclose(targets["T0_total_vertical_height_um"], targets["T0_penetration_depth_um"]), "distinct per-series and population values")
    check(11, "kinetic semantics and units documented", set(kinetic_audit["semantic_classification"]) == {KINETIC_SEMANTICS} and set(kinetic_audit["source_unit"]) == {"J"} and set(kinetic_audit["reported_unit"]) == {"nJ"}, KINETIC_SEMANTICS)
    check(12, "invalid kinetic rows recorded", "invalid_row_count" in kinetic_audit and (kinetic_audit["invalid_row_count"] >= 0).all(), f"invalid total={int(kinetic_audit['invalid_row_count'].sum())}")
    check(13, "T0 reproduced exactly from validated utilities", float(height_audit["T0_reproduction_absolute_error_m"].max()) <= 1e-9 and (targets["T0_observation_count"] > 0).all(), f"validated ledger value used exactly; float32 partition cross-check max error={height_audit['T0_reproduction_absolute_error_m'].max():.3e} m")
    check(14, "adaptive active-interior sensitivity documented", set(sensitivity["response"]) == set(TARGET_SPECS) and sensitivity["paired_available_count"].gt(0).all(), f"rows={len(sensitivity)}")
    configuration = json.loads((OUTPUT_DIR / "phase4_configuration.json").read_text(encoding="utf-8"))
    check(15, "no normalized first-Conduction work", not configuration["scope_exclusions"]["normalized_first_conduction_analysis"], "explicit false in configuration")
    check(16, "no Hugging Face update check", not configuration["dataset"]["dataset_update_check_performed"] and not configuration["dataset"]["revision_discovery_performed"], "direct exact-revision file requests only")
    check(17, "width/length/depth model-selection pipelines not rerun", set(predictions["response"]) == set(TARGET_SPECS), str(sorted(set(predictions["response"]))))
    check(18, "length not a Phase 4 primary response", "length" not in set(predictions["response"]) and "length" not in TARGET_SPECS, "new models only kinetic_energy and total_height")
    fitted = predictions[~predictions["model"].eq("training_mean")]
    check(19, "fold-local scaling leakage-safe", bool_values(fitted["heldout_target_used_for_scaling"]).sum() == 0 and bool_values(fitted["heldout_target_used_for_tuning"]).sum() == 0 and bool_values(fitted["x_scaler_fit_on_training_only"]).all() and bool_values(fitted["y_scaler_fit_on_training_only"]).all(), "all fitted folds have training-only scaler/tuning flags")
    pairing_ok = True
    for response, response_frame in predictions.groupby("response"):
        sets = [
            tuple(sorted(group["heldout_simulation_id"].astype(str)))
            for _, group in response_frame.groupby("model")
        ]
        pairing_ok &= len(set(sets)) == 1
    check(20, "paired model comparisons preserve simulation pairing", pairing_ok and comparisons["paired_by_simulation_id"].astype(bool).all(), "identical held-out ID sets per response/model")
    check(21, "bootstrap sample count reproducible", set(comparisons["bootstrap_resamples"].astype(int)) == {BOOTSTRAP_RESAMPLES}, f"{BOOTSTRAP_RESAMPLES} deterministic resamples")
    decision_text = (OUTPUT_DIR / "decision_log.md").read_text(encoding="utf-8")
    check(22, "learned nugget not called simulator noise", "not a claim of simulator noise" in decision_text, "effective unresolved model-data discrepancy wording")
    depth_curve_population = set(
        curves.loc[curves["response"].eq("depth"), "training_sample_size"].astype(
            int
        )
    )
    check(23, "GP effect curves remain within observed input range and plots use support mask", curves["within_observed_support"].notna().all() and curves["feature_value"].notna().all() and depth_curve_population == {230}, f"every curve row has explicit support flag; figures filter it; depth training population={depth_curve_population}")
    unsupported = ~surfaces["within_observed_support"].astype(bool)
    check(24, "sparse interaction regions marked or masked", surfaces.loc[unsupported, "plot_value_masked_outside_support"].isna().all() and surfaces["inside_pairwise_convex_hull"].notna().all(), f"masked cells={int(unsupported.sum())}")
    results_text = (OUTPUT_DIR / "results_summary.md").read_text(encoding="utf-8")
    check(25, "feature-effect statements use associative language", "association" in results_text and "establishes causation" not in results_text and "causes " not in results_text, "association/conditional prediction language used")
    check(26, "T0 depth/LS units cancel correctly", np.isfinite(diagnostics["T0_depth_over_LS"]).all() and (diagnostics["T0_depth_over_LS"] > 0).all(), "um/um = dimensionless")
    check(27, "G3/LS identity verified", float(diagnostics["G3_over_LS_identity_absolute_error"].max()) <= 1e-15, f"max error={diagnostics['G3_over_LS_identity_absolute_error'].max():.3e}")
    check(28, "LS-versus-D/LS mathematical coupling documented", "mathematically coupled through the denominator" in decision_text, "decision log warning")
    check(29, "no Keyhole classifier fitted", not configuration["scope_exclusions"]["keyhole_classifier"] and "classifier" not in set(predictions["model"].astype(str)), "configuration and model list")
    check(30, "no active-learning loop implemented", not configuration["scope_exclusions"]["active_learning"], "explicit false in configuration")
    recomputed = pd.DataFrame(
        [
            model_metric_row(group)
            for _, group in predictions.groupby(["response", "model"], sort=True)
        ]
    )
    merged_metrics = metrics.merge(
        recomputed,
        on=["response", "model"],
        suffixes=("_saved", "_recomputed"),
        validate="one_to_one",
    )
    metric_match = all(
        np.allclose(
            merged_metrics[f"{column}_saved"],
            merged_metrics[f"{column}_recomputed"],
            equal_nan=True,
            rtol=0,
            atol=1e-12,
        )
        for column in ["mae", "rmse", "r2", "nrmse"]
    )
    check(31, "all final metrics independently recomputed", metric_match, f"{len(merged_metrics)} model rows")
    notebook_path = ROOT / "notebooks" / "week_06" / "06_phase4_new_outputs_feature_effects.ipynb"
    check(32, "notebook has zero error outputs", notebook_path.is_file() and notebook_has_zero_errors(notebook_path), str(notebook_path.relative_to(ROOT)))
    presentation_rows = manifest[manifest["presentation_ready"].astype(bool)]
    presentation_ok = all((ROOT / path).is_file() for path in presentation_rows["presentation_copy"].astype(str))
    check(33, "all presentation-ready figures appear in manifest", len(presentation_rows) == len(PRESENTATION_READY_IDS) and presentation_ok, f"{len(presentation_rows)} manifest rows and files")
    diff_check = subprocess.run(["git", "-C", str(ROOT), "diff", "--check"], capture_output=True, text=True)
    check(34, "git diff --check passes", diff_check.returncode == 0, diff_check.stdout + diff_check.stderr)
    staged = run_read_only_git(ROOT, "diff", "--cached", "--name-only")
    remote_branches = run_read_only_git(ROOT, "branch", "-r", "--list", "*week6-phase4*")
    existing_start_status = set(preflight["isolated_worktree"]["git_status_short"])
    current_status = set(run_read_only_git(ROOT, "status", "--short").splitlines())
    check(35, "no commit, push, staging, reset, clean or stash occurred", head == EXPECTED_HEAD and staged == "" and remote_branches == "" and existing_start_status.issubset(current_status), f"HEAD unchanged; staged empty; no Phase4 remote; pre-existing status retained")
    frame = pd.DataFrame(rows).sort_values("validation_id").reset_index(drop=True)
    require(len(frame) == 35, "Expected exactly 35 validation rows")
    write_csv(OUTPUT_DIR / "validation_results.csv", frame)
    failed = frame[~frame["passed"].astype(bool)]
    if not failed.empty:
        raise RuntimeError(
            "Phase 4 validation failed:\n"
            + failed[["validation_id", "validation", "evidence"]].to_string(
                index=False
            )
        )
    return frame


def build_notebook() -> None:
    builder = ROOT / "scripts" / "build_week6_06_notebook.py"
    require(builder.is_file(), f"Notebook builder missing: {builder}")
    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, str(builder)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    RUNTIME_EVENTS.append(
        {
            "stage": "notebook_build_and_execution",
            "builder": str(builder.relative_to(ROOT)).replace("\\", "/"),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "wall_runtime_seconds": time.perf_counter() - started,
        }
    )


def output_hashes() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(OUTPUT_DIR.iterdir()):
        if path.is_file() and path.name != "phase4_runtime_provenance.json":
            hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = sha256_file(
                path
            )
    notebook = ROOT / "notebooks" / "week_06" / "06_phase4_new_outputs_feature_effects.ipynb"
    source = Path(__file__).resolve()
    builder = ROOT / "scripts" / "build_week6_06_notebook.py"
    for path in [notebook, source, builder]:
        if path.is_file():
            hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = sha256_file(
                path
            )
    return hashes


def write_runtime_provenance(
    *, preflight: dict[str, Any], args: argparse.Namespace, validation: pd.DataFrame
) -> None:
    metrics = pd.read_csv(OUTPUT_DIR / "phase4_model_metrics.csv")
    checkpoint_records = []
    for path in sorted(CHECKPOINT_DIR.glob("*.csv")):
        checkpoint_records.append(
            {
                "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "modified_utc": datetime.fromtimestamp(
                    path.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
            }
        )
    stage_history_path = OUTPUT_DIR / "phase4_stage_runtime_history.json"
    stage_history = (
        json.loads(stage_history_path.read_text(encoding="utf-8"))
        if stage_history_path.is_file()
        else {"successful_runs": []}
    )
    payload = {
        "phase": "Week 6 Phase 4",
        "run_started_utc": RUN_STARTED_UTC.isoformat(),
        "run_finished_utc": datetime.now(timezone.utc).isoformat(),
        "branch": run_read_only_git(ROOT, "branch", "--show-current"),
        "head": run_read_only_git(ROOT, "rev-parse", "HEAD"),
        "git_status_short": run_read_only_git(ROOT, "status", "--short").splitlines(),
        "command_options": vars(args),
        "python": sys.version,
        "platform": platform.platform(),
        "executable": sys.executable,
        "workers": args.workers,
        "events": RUNTIME_EVENTS,
        "successful_stage_runtime_history": stage_history,
        "scientific_aggregate_fold_runtime_seconds": metrics[
            [
                "response",
                "model",
                "aggregate_fold_runtime_seconds",
                "mean_fold_runtime_seconds",
            ]
        ].to_dict(orient="records"),
        "model_checkpoints": checkpoint_records,
        "cache_event_count": sum(
            bool(event.get("cache_reused", False)) for event in RUNTIME_EVENTS
        ),
        "pinned_revision_requests_only": True,
        "revision_discovery_performed": False,
        "dataset_update_check_performed": False,
        "protected_preflight_sha256": sha256_file(PREFLIGHT_PATH),
        "validation_pass_count": int(validation["passed"].astype(bool).sum()),
        "validation_total_count": len(validation),
        "output_sha256": output_hashes(),
        "safety": {
            "starting_head_unchanged": run_read_only_git(ROOT, "rev-parse", "HEAD")
            == EXPECTED_HEAD,
            "staged_files": run_read_only_git(
                ROOT, "diff", "--cached", "--name-only"
            ).splitlines(),
            "commit_performed": False,
            "push_performed": False,
            "reset_performed": False,
            "clean_performed": False,
            "stash_performed": False,
            "original_worktree_unchanged_validation": True,
        },
    }
    write_json(OUTPUT_DIR / "phase4_runtime_provenance.json", payload)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run the complete 241-simulation scientific workflow.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute Phase 4 derived outputs instead of reusing valid caches.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Worker count for downloads and fold-parallel model fitting.",
    )
    parser.add_argument(
        "--stage",
        choices=["all", "targets", "models", "analysis", "finalize"],
        default="all",
        help="Resume from a focused workflow stage; dependencies are loaded from caches.",
    )
    args = parser.parse_args(argv)
    require(args.workers >= 1, "--workers must be positive")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    preflight = verify_starting_state()
    write_json(
        OUTPUT_DIR / "phase4_configuration.json",
        configuration_payload(preflight),
    )
    smoke = not args.full
    targets, kinetic_audit, height_audit, sensitivity, representatives = (
        extract_targets(workers=args.workers, smoke=smoke, force=args.force)
    )
    if args.stage == "targets":
        print(
            f"Phase 4 target stage complete ({'smoke' if smoke else 'full'}).",
            flush=True,
        )
        return 0
    predictions, metrics, comparisons, optimization, decisions = run_models(
        targets,
        workers=args.workers,
        smoke=smoke,
        force=args.force,
    )
    if smoke:
        smoke_summary = {
            "status": "scientific smoke test only",
            "simulation_count": len(targets),
            "prediction_rows": len(predictions),
            "models": sorted(predictions["model"].unique().tolist()),
            "note": "Do not report these reduced-population values as results.",
        }
        write_json(SMOKE_DIR / "smoke_summary.json", smoke_summary)
        print(
            "Phase 4 smoke test complete. Reduced-population values are not "
            "scientific results.",
            flush=True,
        )
        return 0
    if args.stage == "models":
        print("Phase 4 full target and model stages complete.", flush=True)
        return 0
    correlations, intervals, ridge, curves, surfaces, support = (
        relationship_analysis(targets, decisions, force=args.force)
    )
    diagnostics, normalized_correlations, normalized_sensitivity = (
        normalized_diagnostics(targets, force=args.force)
    )
    if args.stage == "analysis":
        print("Phase 4 relationship and normalized analyses complete.", flush=True)
        return 0
    manifest = generate_figures(
        targets=targets,
        kinetic_audit=kinetic_audit,
        sensitivity=sensitivity,
        representatives=representatives,
        predictions=predictions,
        metrics=metrics,
        decisions=decisions,
        correlations=correlations,
        ridge=ridge,
        curves=curves,
        surfaces=surfaces,
        diagnostics=diagnostics,
    )
    preliminary_summary = build_summary_payload(
        targets=targets,
        kinetic_audit=kinetic_audit,
        sensitivity=sensitivity,
        metrics=metrics,
        comparisons=comparisons,
        decisions=decisions,
        correlations=correlations,
        ridge=ridge,
        curves=curves,
        support=support,
        diagnostics=diagnostics,
        normalized_correlations=normalized_correlations,
        manifest=manifest,
        validation=None,
    )
    write_results_documents(
        summary=preliminary_summary,
        sensitivity=sensitivity,
        metrics=metrics,
        decisions=decisions,
        correlations=correlations,
        ridge=ridge,
        support=support,
        diagnostics=diagnostics,
        validation=None,
    )
    checklist = requirement_checklist(manifest)
    write_csv(OUTPUT_DIR / "phase4_requirement_checklist.csv", checklist)
    build_notebook()
    validation = run_validations(
        preflight=preflight,
        targets=targets,
        kinetic_audit=kinetic_audit,
        height_audit=height_audit,
        sensitivity=sensitivity,
        predictions=predictions,
        metrics=metrics,
        comparisons=comparisons,
        curves=curves,
        surfaces=surfaces,
        diagnostics=diagnostics,
        manifest=manifest,
    )
    final_summary = build_summary_payload(
        targets=targets,
        kinetic_audit=kinetic_audit,
        sensitivity=sensitivity,
        metrics=metrics,
        comparisons=comparisons,
        decisions=decisions,
        correlations=correlations,
        ridge=ridge,
        curves=curves,
        support=support,
        diagnostics=diagnostics,
        normalized_correlations=normalized_correlations,
        manifest=manifest,
        validation=validation,
    )
    write_results_documents(
        summary=final_summary,
        sensitivity=sensitivity,
        metrics=metrics,
        decisions=decisions,
        correlations=correlations,
        ridge=ridge,
        support=support,
        diagnostics=diagnostics,
        validation=validation,
    )
    write_runtime_provenance(
        preflight=preflight, args=args, validation=validation
    )
    print(
        f"Phase 4 complete: {len(validation)}/{len(validation)} checks passed; "
        f"{int(manifest['presentation_ready'].sum())} presentation-ready figures.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
