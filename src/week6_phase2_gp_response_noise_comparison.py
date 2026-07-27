"""Week 6 Phase 2: GP observation-treatment comparison.

This module compares three observation treatments for fixed-kernel Gaussian
Process regression of Phase 1 melt-pool width, length, and penetration depth:

* A: deterministic target with fixed numerical jitter;
* B: learned homoskedastic effective nugget via ``WhiteKernel``;
* C: observation-specific target-summary uncertainty from a moving-block
  bootstrap of each simulation's selected-window median.

All reported models use simulation-level leave-one-out cross-validation,
fold-local X and y scaling, an isotropic Matérn 3/2 kernel, L-BFGS-B, one
deterministic additional restart, and the complete 241-simulation population.
No active learning, level-set estimation, kernel-family comparison, ARD,
classifier, or feature-effect analysis is performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

# Keep each fold single-threaded. Fold-level parallelism is controlled below.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import (
    ConstantKernel,
    Matern,
    WhiteKernel,
)
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits


ROOT = Path(__file__).resolve().parents[1]
PHASE1_OUTPUT_DIR = ROOT / "outputs" / "week6_01_melt_pool_data_audit"
PHASE1_INPUT = (
    PHASE1_OUTPUT_DIR / "week6_phase1_simulation_level_responses.csv"
)
RAW_SIMULATION_ROOT = (
    ROOT
    / "data"
    / "raw"
    / "huggingface"
    / "sph_dataset"
    / "final_data_processed"
)
OUTPUT_DIR = ROOT / "outputs" / "week6_02_gp_response_noise_comparison"
NOTEBOOK_PATH = (
    ROOT / "notebooks" / "week_06" / "02_gp_response_noise_comparison.ipynb"
)
ORIGINAL_WORKTREE = Path(r"C:\Users\ozgur\Documents\thesis")

PHASE1_REVISION = "0e859b748fdbc8454f66e58e101e333ac0479d42"
PHASE1_LEDGER_SHA256 = (
    "10DEF11AB64D62444AC14FED506266BEB748EEB5BF892ACDC12E7F0F6DDCF4FF"
)
PHASE1_AGGREGATE_SHA256 = (
    "21FF34AD767C8D4D6C536D66AFD147B8C700884321415078231B7A24D4C7D198"
)

FEATURE_COLUMNS = ["P", "VX", "LS", "ST"]
TARGET_COLUMNS = {
    "width": "melt_pool_width_selected_primary_scalar_target_m",
    "length": "melt_pool_length_selected_primary_scalar_target_m",
    "depth": (
        "melt_pool_depth_below_surface_selected_primary_scalar_target_m"
    ),
}
TARGET_LABELS = {
    "width": "Melt-pool width",
    "length": "Melt-pool length",
    "depth": "Penetration depth below original surface",
}
METHODS = ["A_tiny_jitter", "B_learned_nugget", "C_heteroskedastic"]

UNSTABLE_SIMULATIONS = [
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

CONSTANT_INITIAL = 1.0
CONSTANT_BOUNDS = (1e-3, 1e3)
LENGTH_SCALE_INITIAL = 1.0
LENGTH_SCALE_BOUNDS = (1e-2, 1e2)
MATERN_NU = 1.5
WHITE_INITIAL = 1e-2
WHITE_BOUNDS = (1e-8, 1e1)
ALPHA_A_NORMALIZED = 1e-6
ALPHA_B_NORMALIZED = 1e-8
ALPHA_C_NUMERICAL_FLOOR_NORMALIZED = 1e-6
N_RESTARTS_OPTIMIZER = 1
BASE_RANDOM_SEED = 6202
BOOTSTRAP_RESAMPLES = 500
PAIRED_BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_QUANTILES = (0.025, 0.975)
DEFAULT_WORKERS = 4
BOUND_TOLERANCE = 1e-4

PHASE1_PROTECTED_PATHS = [
    ROOT / "requirements.txt",
    ROOT / "src" / "week6_phase1_melt_pool_data_audit.py",
    ROOT / "scripts" / "build_week6_01_notebook.py",
    ROOT / "notebooks" / "week_06" / "01_melt_pool_monitor_data_audit.ipynb",
]


@dataclass(frozen=True)
class TargetSpec:
    key: str
    source_column: str
    target_um_column: str
    uncertainty_variance_column: str


TARGET_SPECS = {
    key: TargetSpec(
        key=key,
        source_column=column,
        target_um_column=f"{key}_target_um",
        uncertainty_variance_column=f"{key}_bootstrap_variance_um2",
    )
    for key, column in TARGET_COLUMNS.items()
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def write_csv(frame: pd.DataFrame, filename: str) -> Path:
    path = OUTPUT_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")
    return path


def write_json(payload: dict[str, Any], filename: str) -> Path:
    path = OUTPUT_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def json_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def deterministic_seed(*parts: Any) -> int:
    payload = "|".join(map(str, (BASE_RANDOM_SEED, *parts))).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "big")


def configuration() -> dict[str, Any]:
    return {
        "created_at_utc": utc_now(),
        "phase1_input": str(PHASE1_INPUT.relative_to(ROOT)),
        "phase1_revision": PHASE1_REVISION,
        "phase1_ledger_sha256": PHASE1_LEDGER_SHA256,
        "phase1_aggregate_sha256": PHASE1_AGGREGATE_SHA256,
        "feature_columns": FEATURE_COLUMNS,
        "target_columns_m": TARGET_COLUMNS,
        "target_unit_conversion": "y_um = y_m * 1e6",
        "kernel_family": "ConstantKernel * isotropic Matern(nu=1.5)",
        "constant_initial": CONSTANT_INITIAL,
        "constant_bounds": list(CONSTANT_BOUNDS),
        "length_scale_initial": LENGTH_SCALE_INITIAL,
        "length_scale_bounds": list(LENGTH_SCALE_BOUNDS),
        "matern_nu": MATERN_NU,
        "optimizer": "fmin_l_bfgs_b (scikit-learn L-BFGS-B)",
        "n_restarts_optimizer": N_RESTARTS_OPTIMIZER,
        "random_seed": BASE_RANDOM_SEED,
        "fold_order": "ascending numeric simulation_id",
        "x_scaling": "fold-local StandardScaler fit on training X only",
        "y_scaling": (
            "fold-local population mean/std fit on training y only; "
            "GaussianProcessRegressor normalize_y=False"
        ),
        "approaches": {
            "A_tiny_jitter": {
                "kernel": "ConstantKernel * Matern(nu=1.5)",
                "alpha_normalized": ALPHA_A_NORMALIZED,
                "interpretation": "fixed numerical stabilization only",
            },
            "B_learned_nugget": {
                "kernel": (
                    "ConstantKernel * Matern(nu=1.5) + WhiteKernel"
                ),
                "white_initial_normalized_variance": WHITE_INITIAL,
                "white_bounds_normalized_variance": list(WHITE_BOUNDS),
                "alpha_normalized": ALPHA_B_NORMALIZED,
                "interpretation": (
                    "learned effective nugget; not stochastic simulator noise"
                ),
            },
            "C_heteroskedastic": {
                "kernel": "ConstantKernel * Matern(nu=1.5)",
                "alpha_formula": (
                    "bootstrap_variance_um2 / training_y_std_um**2 + 1e-6"
                ),
                "interpretation": (
                    "observation-specific target-summary uncertainty proxy"
                ),
            },
        },
        "bootstrap": {
            "method": "circular moving-block bootstrap of selected-window median",
            "resamples": BOOTSTRAP_RESAMPLES,
            "block_length_rule": "max(5, round(n_window ** (1/3)))",
            "quantiles": list(BOOTSTRAP_QUANTILES),
            "simulation_and_response_specific_seed": True,
        },
        "cross_validation": {
            "method": "exact simulation-level leave-one-out",
            "population_size": 241,
            "predictions_per_target_and_method": 241,
        },
        "paired_bootstrap": {
            "resamples": PAIRED_BOOTSTRAP_RESAMPLES,
            "confidence": 0.95,
            "paired_on": "simulation_id",
        },
        "nrmse_definition": "RMSE divided by observed target range",
        "nlpd_variance_definitions": {
            "A_tiny_jitter": "latent predictive variance",
            "B_learned_nugget": (
                "total predictive variance including learned WhiteKernel nugget"
            ),
            "C_heteroskedastic": (
                "oracle retrospective total variance = latent variance + "
                "held-out target-summary variance"
            ),
        },
        "strict_scope_exclusions": [
            "new kernel families",
            "ARD",
            "active learning",
            "level-set estimation",
            "feature-effect or Sobol analysis",
            "GP classification",
            "new Keyhole-label analysis",
        ],
    }


def _phase1_protected_files() -> list[Path]:
    paths = list(PHASE1_PROTECTED_PATHS)
    paths.extend(sorted(PHASE1_OUTPUT_DIR.rglob("*")))
    return [path for path in paths if path.is_file()]


def phase1_aggregate_sha256() -> tuple[str, int]:
    digest = hashlib.sha256()
    paths = sorted(
        _phase1_protected_files(),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )
    for path in paths:
        relative = path.relative_to(ROOT).as_posix().encode("utf-8")
        data = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest().upper(), len(paths)


def load_phase1_input() -> pd.DataFrame:
    if not PHASE1_INPUT.exists():
        raise FileNotFoundError(PHASE1_INPUT)
    if sha256(PHASE1_INPUT) != PHASE1_LEDGER_SHA256:
        raise RuntimeError("Phase 1 ledger SHA-256 changed")

    frame = pd.read_csv(PHASE1_INPUT)
    required = {
        "simulation_id",
        "numeric_simulation_id",
        "huggingface_revision",
        "flag_primary_window_unstable",
        "selected_window_start_row_index",
        "selected_window_end_row_index",
        "selected_window_start_iteration",
        "selected_window_end_iteration",
        "selected_window_start_time_s",
        "selected_window_end_time_s",
        *FEATURE_COLUMNS,
        *TARGET_COLUMNS.values(),
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise RuntimeError(f"Phase 1 ledger missing columns: {missing}")
    if len(frame) != 241 or len(frame) == 117:
        raise RuntimeError(
            f"Expected corrected 241-row Phase 1 ledger, got {len(frame)}"
        )
    if frame["simulation_id"].duplicated().any():
        raise RuntimeError("Phase 1 simulation IDs are duplicated")
    if frame["numeric_simulation_id"].duplicated().any():
        raise RuntimeError("Phase 1 numeric simulation IDs are duplicated")
    if not np.isfinite(frame[FEATURE_COLUMNS].to_numpy(float)).all():
        raise RuntimeError("At least one of P, VX, LS, ST is missing/non-finite")
    target_values = frame[list(TARGET_COLUMNS.values())].to_numpy(float)
    if not np.isfinite(target_values).all() or not (target_values > 0).all():
        raise RuntimeError("Selected Phase 1 targets must be finite and positive")
    revisions = set(frame["huggingface_revision"].astype(str))
    if revisions != {PHASE1_REVISION}:
        raise RuntimeError(f"Unexpected Phase 1 revision(s): {revisions}")
    unstable = set(
        frame.loc[
            frame["flag_primary_window_unstable"].astype(bool),
            "simulation_id",
        ]
    )
    if unstable != set(UNSTABLE_SIMULATIONS):
        raise RuntimeError(
            "Phase 1 unstable-window set differs from the validated set"
        )

    frame = frame.sort_values("numeric_simulation_id").reset_index(drop=True)
    for key, source_column in TARGET_COLUMNS.items():
        frame[f"{key}_target_um"] = frame[source_column].astype(float) * 1e6
    return frame


def build_phase2_input_table(phase1: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "simulation_id",
        "numeric_simulation_id",
        "huggingface_revision",
        *FEATURE_COLUMNS,
        *TARGET_COLUMNS.values(),
        "width_target_um",
        "length_target_um",
        "depth_target_um",
        "flag_primary_window_unstable",
        "selected_window_start_row_index",
        "selected_window_end_row_index",
        "selected_window_start_iteration",
        "selected_window_end_iteration",
        "selected_window_start_time_s",
        "selected_window_end_time_s",
    ]
    return phase1[columns].copy()


def _load_selected_window_series(
    row: pd.Series,
) -> dict[str, np.ndarray]:
    simulation_id = str(row["simulation_id"])
    start = int(row["selected_window_start_row_index"])
    end = int(row["selected_window_end_row_index"])
    count = end - start + 1
    if start < 0 or count <= 0:
        raise RuntimeError(f"{simulation_id}: invalid selected-window indices")

    monitor_dir = RAW_SIMULATION_ROOT / simulation_id / "monitor"
    bounds = np.loadtxt(
        monitor_dir / "position-bounds_melt.dat",
        delimiter=",",
        ndmin=2,
        skiprows=start,
        max_rows=count,
    )
    time_values = np.loadtxt(
        monitor_dir / "time.dat",
        ndmin=1,
        skiprows=start,
        max_rows=count,
    )
    iterations = np.loadtxt(
        monitor_dir / "iter.dat",
        ndmin=1,
        skiprows=start,
        max_rows=count,
    )
    if not (len(bounds) == len(time_values) == len(iterations) == count):
        raise RuntimeError(f"{simulation_id}: selected-window row mismatch")
    if bounds.shape[1] != 6:
        raise RuntimeError(f"{simulation_id}: melt bounds do not have six columns")

    finite = np.isfinite(bounds).all(axis=1)
    not_sentinel = (np.abs(bounds) < 1e30).all(axis=1)
    ordered = (
        (bounds[:, 1] >= bounds[:, 0])
        & (bounds[:, 3] >= bounds[:, 2])
        & (bounds[:, 5] >= bounds[:, 4])
    )
    valid = finite & not_sentinel & ordered
    if not valid.any():
        raise RuntimeError(f"{simulation_id}: no valid selected-window rows")

    result = {
        "width": (bounds[valid, 3] - bounds[valid, 2]) * 1e6,
        "length": (bounds[valid, 1] - bounds[valid, 0]) * 1e6,
        "depth": np.maximum(0.0, -bounds[valid, 4]) * 1e6,
        "time": time_values[valid],
        "iteration": iterations[valid],
        "valid_mask": valid,
    }
    if not np.isclose(
        time_values[valid][0],
        float(row["selected_window_start_time_s"]),
        rtol=0,
        atol=1e-15,
    ) or not np.isclose(
        time_values[valid][-1],
        float(row["selected_window_end_time_s"]),
        rtol=0,
        atol=1e-15,
    ):
        raise RuntimeError(f"{simulation_id}: selected-window time trace mismatch")
    if not np.isclose(
        iterations[valid][0],
        float(row["selected_window_start_iteration"]),
        rtol=0,
        atol=1e-9,
    ) or not np.isclose(
        iterations[valid][-1],
        float(row["selected_window_end_iteration"]),
        rtol=0,
        atol=1e-9,
    ):
        raise RuntimeError(
            f"{simulation_id}: selected-window iteration trace mismatch"
        )

    for key in TARGET_COLUMNS:
        target_um = float(row[f"{key}_target_um"])
        if not np.isclose(
            np.median(result[key]),
            target_um,
            rtol=1e-9,
            atol=1e-8,
        ):
            raise RuntimeError(
                f"{simulation_id}/{key}: raw selected-window median "
                "does not reproduce the Phase 1 target"
            )
    return result


def block_length_rule(n_window: int) -> int:
    return max(5, int(round(n_window ** (1 / 3))))


def moving_block_bootstrap_medians(
    values: np.ndarray,
    *,
    block_length: int,
    resamples: int,
    seed: int,
    batch_size: int = 25,
) -> np.ndarray:
    """Circular moving-block bootstrap medians with bounded working memory."""
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("Bootstrap input must be a finite one-dimensional series")
    if block_length < 1 or block_length > len(values):
        raise ValueError("Invalid moving-block length")
    if resamples < 1:
        raise ValueError("resamples must be positive")

    rng = np.random.default_rng(seed)
    n = len(values)
    n_blocks = int(math.ceil(n / block_length))
    offsets = np.arange(block_length, dtype=np.int64)
    medians = np.empty(resamples, dtype=float)
    cursor = 0
    while cursor < resamples:
        batch = min(batch_size, resamples - cursor)
        starts = rng.integers(0, n, size=(batch, n_blocks), endpoint=False)
        indices = (
            starts[:, :, None] + offsets[None, None, :]
        ) % n
        indices = indices.reshape(batch, -1)[:, :n]
        samples = values[indices]
        medians[cursor : cursor + batch] = np.median(samples, axis=1)
        cursor += batch
    return medians


def _series_sha256(values: np.ndarray) -> str:
    canonical = np.asarray(values, dtype="<f8").tobytes()
    return hashlib.sha256(canonical).hexdigest().upper()


def build_target_summary_uncertainty(
    phase1: pd.DataFrame,
    *,
    resamples: int = BOOTSTRAP_RESAMPLES,
    progress: bool = True,
) -> tuple[pd.DataFrame, dict[tuple[str, str], np.ndarray]]:
    rows: list[dict[str, Any]] = []
    series_cache: dict[tuple[str, str], np.ndarray] = {}
    for position, phase1_row in phase1.iterrows():
        simulation_id = str(phase1_row["simulation_id"])
        selected = _load_selected_window_series(phase1_row)
        for target_key in TARGET_COLUMNS:
            values = np.asarray(selected[target_key], dtype=float)
            series_cache[(simulation_id, target_key)] = values
            block_length = block_length_rule(len(values))
            seed = deterministic_seed(
                "target-summary-bootstrap",
                simulation_id,
                target_key,
                block_length,
                resamples,
            )
            medians = moving_block_bootstrap_medians(
                values,
                block_length=block_length,
                resamples=resamples,
                seed=seed,
            )
            q_low, q_high = np.quantile(medians, BOOTSTRAP_QUANTILES)
            target_um = float(phase1_row[f"{target_key}_target_um"])
            rows.append(
                {
                    "simulation_id": simulation_id,
                    "numeric_simulation_id": int(
                        phase1_row["numeric_simulation_id"]
                    ),
                    "target": target_key,
                    "target_label": TARGET_LABELS[target_key],
                    "phase1_target_um": target_um,
                    "selected_window_start_row_index": int(
                        phase1_row["selected_window_start_row_index"]
                    ),
                    "selected_window_end_row_index": int(
                        phase1_row["selected_window_end_row_index"]
                    ),
                    "selected_window_start_time_s": float(
                        phase1_row["selected_window_start_time_s"]
                    ),
                    "selected_window_end_time_s": float(
                        phase1_row["selected_window_end_time_s"]
                    ),
                    "selected_window_observation_count": len(values),
                    "block_bootstrap_type": "circular moving-block bootstrap",
                    "block_length_rule": (
                        "max(5, round(n_window ** (1/3)))"
                    ),
                    "block_length": block_length,
                    "bootstrap_resamples": resamples,
                    "bootstrap_seed": seed,
                    "raw_window_median_um": float(np.median(values)),
                    "raw_window_series_sha256": _series_sha256(values),
                    "bootstrap_median_mean_um": float(medians.mean()),
                    "bootstrap_median_std_um": float(
                        medians.std(ddof=1)
                    ),
                    "bootstrap_variance_um2": float(
                        medians.var(ddof=1)
                    ),
                    "bootstrap_quantile_low_um": float(q_low),
                    "bootstrap_quantile_high_um": float(q_high),
                    "phase1_target_reproduced": bool(
                        np.isclose(
                            np.median(values),
                            target_um,
                            rtol=1e-9,
                            atol=1e-8,
                        )
                    ),
                    "phase1_unstable_window_flag": bool(
                        phase1_row["flag_primary_window_unstable"]
                    ),
                    "interpretation": (
                        "target-summary uncertainty proxy; not measurement "
                        "noise and not stochastic simulator noise"
                    ),
                }
            )
        if progress and ((position + 1) % 10 == 0 or position == len(phase1) - 1):
            print(
                f"bootstrap windows: {position + 1}/{len(phase1)}",
                flush=True,
            )
    frame = pd.DataFrame(rows).sort_values(
        ["target", "numeric_simulation_id"]
    )
    if len(frame) != len(phase1) * 3:
        raise RuntimeError(
            "Uncertainty table does not contain three rows per simulation"
        )
    if not frame["phase1_target_reproduced"].all():
        raise RuntimeError("At least one Phase 1 target was not reproduced")
    if (
        not np.isfinite(frame["bootstrap_variance_um2"]).all()
        or (frame["bootstrap_variance_um2"] < 0).any()
    ):
        raise RuntimeError("Invalid target-summary bootstrap variance")
    return frame.reset_index(drop=True), series_cache


def build_block_bootstrap_sensitivity(
    uncertainty: pd.DataFrame,
    series_cache: dict[tuple[str, str], np.ndarray],
    *,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for target_key in TARGET_COLUMNS:
        target_rows = uncertainty.loc[
            uncertainty["target"] == target_key
        ].sort_values("bootstrap_median_std_um")
        representative_positions = {
            "low_variability": 0,
            "middle_variability": len(target_rows) // 2,
            "high_variability": len(target_rows) - 1,
        }
        for variability_class, position in representative_positions.items():
            base_row = target_rows.iloc[position]
            simulation_id = str(base_row["simulation_id"])
            values = series_cache[(simulation_id, target_key)]
            base_length = int(base_row["block_length"])
            lengths = {
                "half": max(2, int(round(base_length / 2))),
                "base": base_length,
                "double": min(len(values), base_length * 2),
            }
            estimates: dict[str, float] = {}
            scenario_rows: list[dict[str, Any]] = []
            for scenario, block_length in lengths.items():
                seed = deterministic_seed(
                    "block-sensitivity",
                    simulation_id,
                    target_key,
                    scenario,
                    block_length,
                    resamples,
                )
                medians = moving_block_bootstrap_medians(
                    values,
                    block_length=block_length,
                    resamples=resamples,
                    seed=seed,
                )
                std_um = float(medians.std(ddof=1))
                estimates[scenario] = std_um
                scenario_rows.append(
                    {
                        "target": target_key,
                        "target_label": TARGET_LABELS[target_key],
                        "variability_class": variability_class,
                        "simulation_id": simulation_id,
                        "selected_window_observation_count": len(values),
                        "block_scenario": scenario,
                        "block_length": block_length,
                        "bootstrap_resamples": resamples,
                        "bootstrap_seed": seed,
                        "bootstrap_median_std_um": std_um,
                        "bootstrap_variance_um2": float(
                            medians.var(ddof=1)
                        ),
                        "bootstrap_quantile_low_um": float(
                            np.quantile(medians, BOOTSTRAP_QUANTILES[0])
                        ),
                        "bootstrap_quantile_high_um": float(
                            np.quantile(medians, BOOTSTRAP_QUANTILES[1])
                        ),
                    }
                )
            base_std = estimates["base"]
            for row in scenario_rows:
                ratio = (
                    row["bootstrap_median_std_um"] / base_std
                    if base_std > 0
                    else np.nan
                )
                row["std_ratio_to_base"] = ratio
                row["qualitatively_stable_vs_base"] = bool(
                    np.isfinite(ratio) and 0.5 <= ratio <= 2.0
                )
                rows.append(row)
    return pd.DataFrame(rows).sort_values(
        ["target", "variability_class", "block_scenario"]
    ).reset_index(drop=True)


def uncertainty_wide_table(
    phase1: pd.DataFrame, uncertainty: pd.DataFrame
) -> pd.DataFrame:
    variance = uncertainty.pivot(
        index="simulation_id",
        columns="target",
        values="bootstrap_variance_um2",
    )
    std = uncertainty.pivot(
        index="simulation_id",
        columns="target",
        values="bootstrap_median_std_um",
    )
    result = phase1.copy()
    for target_key in TARGET_COLUMNS:
        result[f"{target_key}_bootstrap_variance_um2"] = result[
            "simulation_id"
        ].map(variance[target_key])
        result[f"{target_key}_bootstrap_std_um"] = result[
            "simulation_id"
        ].map(std[target_key])
    if result[
        [
            f"{target}_bootstrap_variance_um2"
            for target in TARGET_COLUMNS
        ]
    ].isna().any().any():
        raise RuntimeError("Could not align bootstrap variances to Phase 1 rows")
    return result


def _base_kernel() -> Any:
    return ConstantKernel(
        constant_value=CONSTANT_INITIAL,
        constant_value_bounds=CONSTANT_BOUNDS,
    ) * Matern(
        length_scale=LENGTH_SCALE_INITIAL,
        length_scale_bounds=LENGTH_SCALE_BOUNDS,
        nu=MATERN_NU,
    )


def make_kernel(method: str) -> Any:
    if method not in METHODS:
        raise ValueError(f"Unknown method: {method}")
    kernel = _base_kernel()
    if method == "B_learned_nugget":
        kernel += WhiteKernel(
            noise_level=WHITE_INITIAL,
            noise_level_bounds=WHITE_BOUNDS,
        )
    return kernel


def _optimized_components(
    kernel: Any, method: str
) -> tuple[float, float, float]:
    if method == "B_learned_nugget":
        signal_kernel = kernel.k1
        noise_variance = float(kernel.k2.noise_level)
    else:
        signal_kernel = kernel
        noise_variance = np.nan
    signal_variance = float(signal_kernel.k1.constant_value)
    length_scale = float(np.asarray(signal_kernel.k2.length_scale).item())
    return signal_variance, length_scale, noise_variance


def _bound_hit(value: float, bounds: tuple[float, float]) -> tuple[bool, str]:
    if not np.isfinite(value):
        return False, ""
    lower, upper = bounds
    if value <= lower * (1 + BOUND_TOLERANCE):
        return True, "lower"
    if value >= upper * (1 - BOUND_TOLERANCE):
        return True, "upper"
    return False, ""


def gaussian_nlpd(
    observed: np.ndarray | float,
    mean: np.ndarray | float,
    variance: np.ndarray | float,
) -> np.ndarray:
    observed_array = np.asarray(observed, dtype=float)
    mean_array = np.asarray(mean, dtype=float)
    variance_array = np.maximum(np.asarray(variance, dtype=float), 1e-18)
    return (
        0.5 * np.log(2 * np.pi * variance_array)
        + 0.5 * (observed_array - mean_array) ** 2 / variance_array
    )


def _interval(mean: float, std: float) -> tuple[float, float]:
    return mean - 1.96 * std, mean + 1.96 * std


def scientific_config_fingerprint() -> str:
    payload = configuration()
    payload.pop("created_at_utc", None)
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest().upper()


def _fit_loo_fold(
    *,
    X: np.ndarray,
    y_um: np.ndarray,
    alpha_um2: np.ndarray,
    simulation_ids: np.ndarray,
    numeric_ids: np.ndarray,
    unstable_flags: np.ndarray,
    target_key: str,
    method: str,
    fold_index: int,
    analysis_label: str,
    n_restarts_optimizer: int,
) -> dict[str, Any]:
    n = len(y_um)
    test_index = fold_index
    training_mask = np.ones(n, dtype=bool)
    training_mask[test_index] = False
    train_indices = np.flatnonzero(training_mask)

    X_train = X[training_mask]
    X_test = X[[test_index]]
    y_train = y_um[training_mask]
    y_test = float(y_um[test_index])
    variance_train_um2 = alpha_um2[training_mask]
    heldout_variance_um2 = float(alpha_um2[test_index])

    x_scaler = StandardScaler()
    X_train_scaled = x_scaler.fit_transform(X_train)
    X_test_scaled = x_scaler.transform(X_test)

    y_mean_um = float(y_train.mean())
    y_std_um = float(y_train.std(ddof=0))
    if not np.isfinite(y_std_um) or y_std_um <= 0:
        raise RuntimeError(
            f"{target_key}/{method}/fold {fold_index}: invalid training y std"
        )
    y_train_scaled = (y_train - y_mean_um) / y_std_um

    if method == "A_tiny_jitter":
        alpha_normalized: float | np.ndarray = ALPHA_A_NORMALIZED
        alpha_kind = "fixed numerical jitter"
    elif method == "B_learned_nugget":
        alpha_normalized = ALPHA_B_NORMALIZED
        alpha_kind = "tiny numerical jitter separate from learned nugget"
    elif method == "C_heteroskedastic":
        alpha_normalized = (
            variance_train_um2 / y_std_um**2
            + ALPHA_C_NUMERICAL_FLOOR_NORMALIZED
        )
        if (
            not np.isfinite(alpha_normalized).all()
            or (alpha_normalized < 0).any()
        ):
            raise RuntimeError(
                f"{target_key}/{method}/fold {fold_index}: invalid alpha"
            )
        alpha_kind = (
            "observation-specific target-summary variance plus numerical floor"
        )
    else:
        raise ValueError(method)

    fold_seed = deterministic_seed(
        "loo-fold", analysis_label, target_key, fold_index
    )
    model = GaussianProcessRegressor(
        kernel=make_kernel(method),
        alpha=alpha_normalized,
        optimizer="fmin_l_bfgs_b",
        n_restarts_optimizer=n_restarts_optimizer,
        normalize_y=False,
        random_state=fold_seed,
        copy_X_train=True,
    )

    started = time.perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model.fit(X_train_scaled, y_train_scaled)
        prediction_scaled, returned_std_scaled = model.predict(
            X_test_scaled, return_std=True
        )
    runtime_seconds = time.perf_counter() - started

    prediction_um = float(prediction_scaled[0] * y_std_um + y_mean_um)
    returned_variance_normalized = float(returned_std_scaled[0] ** 2)
    signal_variance, length_scale, noise_variance_normalized = (
        _optimized_components(model.kernel_, method)
    )

    if method == "B_learned_nugget":
        total_variance_normalized = returned_variance_normalized
        latent_variance_normalized = max(
            total_variance_normalized - noise_variance_normalized,
            1e-18,
        )
        total_std_um = math.sqrt(total_variance_normalized) * y_std_um
        latent_std_um = math.sqrt(latent_variance_normalized) * y_std_um
        oracle_total_std_um = np.nan
        evaluation_std_um = total_std_um
        evaluation_variance_definition = (
            "total predictive variance including learned WhiteKernel nugget"
        )
        noise_std_normalized = math.sqrt(noise_variance_normalized)
        noise_std_um = noise_std_normalized * y_std_um
        noise_fraction_training_std = noise_std_normalized
    else:
        latent_variance_normalized = returned_variance_normalized
        latent_std_um = (
            math.sqrt(latent_variance_normalized) * y_std_um
        )
        total_std_um = np.nan
        noise_std_normalized = np.nan
        noise_std_um = np.nan
        noise_fraction_training_std = np.nan
        if method == "C_heteroskedastic":
            oracle_total_std_um = math.sqrt(
                latent_std_um**2 + heldout_variance_um2
            )
            evaluation_std_um = oracle_total_std_um
            evaluation_variance_definition = (
                "oracle retrospective latent variance plus held-out "
                "target-summary variance"
            )
        else:
            oracle_total_std_um = np.nan
            evaluation_std_um = latent_std_um
            evaluation_variance_definition = "latent predictive variance"

    residual_um = y_test - prediction_um
    latent_lower, latent_upper = _interval(prediction_um, latent_std_um)
    if np.isfinite(total_std_um):
        observation_lower, observation_upper = _interval(
            prediction_um, total_std_um
        )
    else:
        observation_lower, observation_upper = np.nan, np.nan
    if np.isfinite(oracle_total_std_um):
        oracle_lower, oracle_upper = _interval(
            prediction_um, oracle_total_std_um
        )
    else:
        oracle_lower, oracle_upper = np.nan, np.nan

    constant_hit, constant_side = _bound_hit(
        signal_variance, CONSTANT_BOUNDS
    )
    length_hit, length_side = _bound_hit(
        length_scale, LENGTH_SCALE_BOUNDS
    )
    noise_hit, noise_side = _bound_hit(
        noise_variance_normalized, WHITE_BOUNDS
    )
    warning_messages = [
        f"{type(item.message).__name__}: {item.message}" for item in caught
    ]
    convergence_warning_count = sum(
        isinstance(item.message, ConvergenceWarning) for item in caught
    )

    return {
        "analysis_label": analysis_label,
        "config_fingerprint": scientific_config_fingerprint(),
        "target": target_key,
        "target_label": TARGET_LABELS[target_key],
        "method": method,
        "fold_index": fold_index,
        "heldout_simulation_id": str(simulation_ids[test_index]),
        "heldout_numeric_simulation_id": int(numeric_ids[test_index]),
        "phase1_unstable_window_flag": bool(
            unstable_flags[test_index]
        ),
        "observed_target_um": y_test,
        "predicted_mean_um": prediction_um,
        "residual_um": residual_um,
        "absolute_error_um": abs(residual_um),
        "squared_error_um2": residual_um**2,
        "latent_predictive_std_um": latent_std_um,
        "latent_predictive_variance_um2": latent_std_um**2,
        "total_predictive_std_um": total_std_um,
        "total_predictive_variance_um2": (
            total_std_um**2 if np.isfinite(total_std_um) else np.nan
        ),
        "oracle_total_predictive_std_um": oracle_total_std_um,
        "oracle_total_predictive_variance_um2": (
            oracle_total_std_um**2
            if np.isfinite(oracle_total_std_um)
            else np.nan
        ),
        "evaluation_predictive_std_um": evaluation_std_um,
        "evaluation_variance_definition": evaluation_variance_definition,
        "latent_nlpd": float(
            gaussian_nlpd(y_test, prediction_um, latent_std_um**2)
        ),
        "observation_level_nlpd": (
            float(gaussian_nlpd(y_test, prediction_um, total_std_um**2))
            if np.isfinite(total_std_um)
            else np.nan
        ),
        "oracle_observation_level_nlpd": (
            float(
                gaussian_nlpd(
                    y_test, prediction_um, oracle_total_std_um**2
                )
            )
            if np.isfinite(oracle_total_std_um)
            else np.nan
        ),
        "evaluation_nlpd": float(
            gaussian_nlpd(y_test, prediction_um, evaluation_std_um**2)
        ),
        "latent_interval_lower_um": latent_lower,
        "latent_interval_upper_um": latent_upper,
        "observation_interval_lower_um": observation_lower,
        "observation_interval_upper_um": observation_upper,
        "oracle_interval_lower_um": oracle_lower,
        "oracle_interval_upper_um": oracle_upper,
        "latent_interval_contains_observed": bool(
            latent_lower <= y_test <= latent_upper
        ),
        "observation_interval_contains_observed": (
            bool(observation_lower <= y_test <= observation_upper)
            if np.isfinite(observation_lower)
            else np.nan
        ),
        "oracle_interval_contains_observed": (
            bool(oracle_lower <= y_test <= oracle_upper)
            if np.isfinite(oracle_lower)
            else np.nan
        ),
        "optimized_kernel": str(model.kernel_),
        "optimized_length_scale": length_scale,
        "optimized_signal_variance_normalized": signal_variance,
        "optimized_noise_variance_normalized": noise_variance_normalized,
        "optimized_noise_std_normalized": noise_std_normalized,
        "optimized_noise_std_um": noise_std_um,
        "noise_std_fraction_training_target_std": (
            noise_fraction_training_std
        ),
        "heldout_target_summary_variance_um2": heldout_variance_um2,
        "heldout_target_summary_std_um": math.sqrt(
            heldout_variance_um2
        ),
        "training_alpha_normalized_min": (
            float(np.min(alpha_normalized))
            if np.ndim(alpha_normalized)
            else float(alpha_normalized)
        ),
        "training_alpha_normalized_median": (
            float(np.median(alpha_normalized))
            if np.ndim(alpha_normalized)
            else float(alpha_normalized)
        ),
        "training_alpha_normalized_max": (
            float(np.max(alpha_normalized))
            if np.ndim(alpha_normalized)
            else float(alpha_normalized)
        ),
        "alpha_kind": alpha_kind,
        "numerical_jitter_normalized": (
            ALPHA_C_NUMERICAL_FLOOR_NORMALIZED
            if method == "C_heteroskedastic"
            else float(alpha_normalized)
        ),
        "whitekernel_is_effective_nugget_not_simulator_noise": (
            method == "B_learned_nugget"
        ),
        "oracle_interval_is_retrospective_not_deployable": (
            method == "C_heteroskedastic"
        ),
        "training_size": len(train_indices),
        "population_size": n,
        "heldout_excluded_from_training": bool(
            test_index not in set(train_indices)
        ),
        "x_scaler_fit_on_training_only": True,
        "y_scaler_fit_on_training_only": True,
        "normalize_y": False,
        "feature_columns": json_compact(FEATURE_COLUMNS),
        "training_y_mean_um": y_mean_um,
        "training_y_std_um": y_std_um,
        "x_training_mean": json_compact(
            [float(value) for value in x_scaler.mean_]
        ),
        "x_training_scale": json_compact(
            [float(value) for value in x_scaler.scale_]
        ),
        **{
            f"heldout_{feature}": float(X[test_index, feature_index])
            for feature_index, feature in enumerate(FEATURE_COLUMNS)
        },
        "fold_random_seed": fold_seed,
        "optimizer": "fmin_l_bfgs_b",
        "n_restarts_optimizer": n_restarts_optimizer,
        "log_marginal_likelihood": float(
            model.log_marginal_likelihood_value_
        ),
        "runtime_seconds": runtime_seconds,
        "warning_count": len(caught),
        "convergence_warning_count": convergence_warning_count,
        "warnings": " | ".join(warning_messages),
        "convergence_status": (
            "completed_with_convergence_warning"
            if convergence_warning_count
            else "completed_without_convergence_warning"
        ),
        "failed_fold": False,
        "constant_bound_hit": constant_hit,
        "constant_bound_side": constant_side,
        "length_scale_bound_hit": length_hit,
        "length_scale_bound_side": length_side,
        "noise_bound_hit": noise_hit,
        "noise_bound_side": noise_side,
        "any_hyperparameter_bound_hit": bool(
            constant_hit or length_hit or noise_hit
        ),
    }


def _checkpoint_path(
    analysis_label: str, target_key: str, method: str
) -> Path:
    return (
        OUTPUT_DIR
        / "checkpoints"
        / f"{analysis_label}__{target_key}__{method}.csv"
    )


def _checkpoint_is_valid(
    frame: pd.DataFrame,
    *,
    expected_rows: int,
    target_key: str,
    method: str,
    analysis_label: str,
) -> bool:
    return bool(
        len(frame) == expected_rows
        and frame["heldout_simulation_id"].is_unique
        and set(frame["target"]) == {target_key}
        and set(frame["method"]) == {method}
        and set(frame["analysis_label"]) == {analysis_label}
        and set(frame["config_fingerprint"])
        == {scientific_config_fingerprint()}
        and np.isfinite(frame["predicted_mean_um"]).all()
    )


def run_loo_method(
    modelling_table: pd.DataFrame,
    *,
    target_key: str,
    method: str,
    analysis_label: str,
    workers: int,
    n_restarts_optimizer: int = N_RESTARTS_OPTIMIZER,
    force: bool = False,
    use_checkpoint: bool = True,
) -> pd.DataFrame:
    spec = TARGET_SPECS[target_key]
    expected_rows = len(modelling_table)
    checkpoint = _checkpoint_path(analysis_label, target_key, method)
    if use_checkpoint and not force and checkpoint.exists():
        cached = pd.read_csv(checkpoint)
        if _checkpoint_is_valid(
            cached,
            expected_rows=expected_rows,
            target_key=target_key,
            method=method,
            analysis_label=analysis_label,
        ):
            print(f"checkpoint reused: {checkpoint.name}", flush=True)
            return cached.sort_values("fold_index").reset_index(drop=True)

    X = modelling_table[FEATURE_COLUMNS].to_numpy(float)
    y_um = modelling_table[spec.target_um_column].to_numpy(float)
    alpha_um2 = modelling_table[
        spec.uncertainty_variance_column
    ].to_numpy(float)
    simulation_ids = modelling_table["simulation_id"].astype(str).to_numpy()
    numeric_ids = modelling_table["numeric_simulation_id"].to_numpy(int)
    unstable_flags = modelling_table[
        "flag_primary_window_unstable"
    ].astype(bool).to_numpy()

    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    with threadpool_limits(limits=1):
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = {
                pool.submit(
                    _fit_loo_fold,
                    X=X,
                    y_um=y_um,
                    alpha_um2=alpha_um2,
                    simulation_ids=simulation_ids,
                    numeric_ids=numeric_ids,
                    unstable_flags=unstable_flags,
                    target_key=target_key,
                    method=method,
                    fold_index=fold_index,
                    analysis_label=analysis_label,
                    n_restarts_optimizer=n_restarts_optimizer,
                ): fold_index
                for fold_index in range(expected_rows)
            }
            for completed, future in enumerate(
                as_completed(futures), start=1
            ):
                fold_index = futures[future]
                try:
                    rows.append(future.result())
                except Exception as exc:
                    raise RuntimeError(
                        f"LOO failed for {analysis_label}/{target_key}/"
                        f"{method}/fold {fold_index}"
                    ) from exc
                if completed % 10 == 0 or completed == expected_rows:
                    elapsed = time.perf_counter() - started
                    print(
                        f"{analysis_label} {target_key} {method}: "
                        f"{completed}/{expected_rows} folds "
                        f"({elapsed:.1f}s)",
                        flush=True,
                    )

    frame = pd.DataFrame(rows).sort_values("fold_index").reset_index(drop=True)
    if not _checkpoint_is_valid(
        frame,
        expected_rows=expected_rows,
        target_key=target_key,
        method=method,
        analysis_label=analysis_label,
    ):
        raise RuntimeError(
            f"Generated LOO rows failed checkpoint validation: "
            f"{analysis_label}/{target_key}/{method}"
        )
    if use_checkpoint:
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(checkpoint, index=False, lineterminator="\n")
    return frame


def run_primary_loo(
    modelling_table: pd.DataFrame,
    *,
    workers: int,
    force: bool,
) -> dict[str, pd.DataFrame]:
    predictions: dict[str, pd.DataFrame] = {}
    for target_key in TARGET_COLUMNS:
        target_frames = [
            run_loo_method(
                modelling_table,
                target_key=target_key,
                method=method,
                analysis_label="full_population_loo",
                workers=workers,
                force=force,
            )
            for method in METHODS
        ]
        combined = pd.concat(target_frames, ignore_index=True).sort_values(
            ["method", "fold_index"]
        )
        predictions[target_key] = combined.reset_index(drop=True)
    return predictions


def metric_row(
    predictions: pd.DataFrame,
    *,
    analysis_label: str | None = None,
) -> dict[str, Any]:
    if predictions.empty:
        raise ValueError("Cannot calculate metrics from an empty frame")
    observed = predictions["observed_target_um"].to_numpy(float)
    predicted = predictions["predicted_mean_um"].to_numpy(float)
    residual = observed - predicted
    absolute = np.abs(residual)
    rmse = float(np.sqrt(np.mean(residual**2)))
    target_range = float(observed.max() - observed.min())

    latent_coverage = predictions[
        "latent_interval_contains_observed"
    ].astype(bool).mean()
    observation_available = predictions[
        "observation_interval_contains_observed"
    ].notna()
    oracle_available = predictions[
        "oracle_interval_contains_observed"
    ].notna()
    if observation_available.any():
        observation_coverage = float(
            predictions.loc[
                observation_available,
                "observation_interval_contains_observed",
            ]
            .astype(bool)
            .mean()
        )
        observation_width = float(
            (
                predictions.loc[
                    observation_available, "observation_interval_upper_um"
                ]
                - predictions.loc[
                    observation_available, "observation_interval_lower_um"
                ]
            ).mean()
        )
    elif oracle_available.any():
        observation_coverage = float(
            predictions.loc[
                oracle_available, "oracle_interval_contains_observed"
            ]
            .astype(bool)
            .mean()
        )
        observation_width = float(
            (
                predictions.loc[
                    oracle_available, "oracle_interval_upper_um"
                ]
                - predictions.loc[
                    oracle_available, "oracle_interval_lower_um"
                ]
            ).mean()
        )
    else:
        observation_coverage = np.nan
        observation_width = np.nan

    return {
        "analysis_label": analysis_label
        or str(predictions["analysis_label"].iloc[0]),
        "target": str(predictions["target"].iloc[0]),
        "target_label": str(predictions["target_label"].iloc[0]),
        "method": str(predictions["method"].iloc[0]),
        "n_predictions": len(predictions),
        "mae_um": float(mean_absolute_error(observed, predicted)),
        "median_absolute_error_um": float(np.median(absolute)),
        "rmse_um": rmse,
        "r2": float(r2_score(observed, predicted)),
        "nrmse": rmse / target_range if target_range > 0 else np.nan,
        "mean_nlpd": float(predictions["evaluation_nlpd"].mean()),
        "median_nlpd": float(predictions["evaluation_nlpd"].median()),
        "nlpd_variance_definition": str(
            predictions["evaluation_variance_definition"].iloc[0]
        ),
        "latent_95_coverage": float(latent_coverage),
        "observation_95_coverage": observation_coverage,
        "observation_coverage_kind": (
            "learned-nugget total interval"
            if observation_available.any()
            else "oracle retrospective interval"
            if oracle_available.any()
            else "not defined"
        ),
        "mean_latent_interval_width_um": float(
            (
                predictions["latent_interval_upper_um"]
                - predictions["latent_interval_lower_um"]
            ).mean()
        ),
        "mean_observation_interval_width_um": observation_width,
        "total_runtime_seconds": float(
            predictions["runtime_seconds"].sum()
        ),
        "mean_fold_runtime_seconds": float(
            predictions["runtime_seconds"].mean()
        ),
        "optimizer_warning_folds": int(
            predictions["warning_count"].gt(0).sum()
        ),
        "convergence_warning_folds": int(
            predictions["convergence_warning_count"].gt(0).sum()
        ),
        "failed_folds": int(predictions["failed_fold"].sum()),
        "any_bound_hit_folds": int(
            predictions["any_hyperparameter_bound_hit"].sum()
        ),
        "constant_bound_hit_folds": int(
            predictions["constant_bound_hit"].sum()
        ),
        "length_scale_bound_hit_folds": int(
            predictions["length_scale_bound_hit"].sum()
        ),
        "noise_bound_hit_folds": int(
            predictions["noise_bound_hit"].sum()
        ),
        "length_scale_min": float(
            predictions["optimized_length_scale"].min()
        ),
        "length_scale_q25": float(
            predictions["optimized_length_scale"].quantile(0.25)
        ),
        "length_scale_median": float(
            predictions["optimized_length_scale"].median()
        ),
        "length_scale_q75": float(
            predictions["optimized_length_scale"].quantile(0.75)
        ),
        "length_scale_max": float(
            predictions["optimized_length_scale"].max()
        ),
        "signal_variance_min": float(
            predictions["optimized_signal_variance_normalized"].min()
        ),
        "signal_variance_median": float(
            predictions["optimized_signal_variance_normalized"].median()
        ),
        "signal_variance_max": float(
            predictions["optimized_signal_variance_normalized"].max()
        ),
        "learned_noise_variance_median_normalized": (
            float(
                predictions[
                    "optimized_noise_variance_normalized"
                ].median()
            )
            if predictions[
                "optimized_noise_variance_normalized"
            ].notna().any()
            else np.nan
        ),
        "learned_noise_std_median_um": (
            float(predictions["optimized_noise_std_um"].median())
            if predictions["optimized_noise_std_um"].notna().any()
            else np.nan
        ),
        "learned_noise_fraction_training_std_median": (
            float(
                predictions[
                    "noise_std_fraction_training_target_std"
                ].median()
            )
            if predictions[
                "noise_std_fraction_training_target_std"
            ].notna().any()
            else np.nan
        ),
    }


def build_all_metrics(
    predictions: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    rows = []
    for target_key, target_predictions in predictions.items():
        for method in METHODS:
            subset = target_predictions.loc[
                target_predictions["method"] == method
            ]
            rows.append(metric_row(subset))
    return pd.DataFrame(rows).sort_values(
        ["target", "method"]
    ).reset_index(drop=True)


def _paired_bootstrap_differences(
    residual_a: np.ndarray,
    residual_b: np.ndarray,
    *,
    seed: int,
    resamples: int = PAIRED_BOOTSTRAP_RESAMPLES,
    batch_size: int = 500,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    n = len(residual_a)
    mae_differences = np.empty(resamples, dtype=float)
    rmse_differences = np.empty(resamples, dtype=float)
    cursor = 0
    while cursor < resamples:
        batch = min(batch_size, resamples - cursor)
        indices = rng.integers(0, n, size=(batch, n), endpoint=False)
        sampled_a = residual_a[indices]
        sampled_b = residual_b[indices]
        mae_differences[cursor : cursor + batch] = (
            np.mean(np.abs(sampled_b), axis=1)
            - np.mean(np.abs(sampled_a), axis=1)
        )
        rmse_differences[cursor : cursor + batch] = (
            np.sqrt(np.mean(sampled_b**2, axis=1))
            - np.sqrt(np.mean(sampled_a**2, axis=1))
        )
        cursor += batch
    return mae_differences, rmse_differences


def build_paired_comparisons(
    predictions: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    detail_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for target_key, target_predictions in predictions.items():
        by_method = {
            method: target_predictions.loc[
                target_predictions["method"] == method
            ]
            .set_index("heldout_simulation_id")
            .sort_index()
            for method in METHODS
        }
        expected_ids = set(next(iter(by_method.values())).index)
        if any(set(frame.index) != expected_ids for frame in by_method.values()):
            raise RuntimeError(
                f"{target_key}: method predictions are not simulation-aligned"
            )
        for method_a, method_b in combinations(METHODS, 2):
            a = by_method[method_a]
            b = by_method[method_b]
            error_a = a["absolute_error_um"].to_numpy(float)
            error_b = b["absolute_error_um"].to_numpy(float)
            residual_a = a["residual_um"].to_numpy(float)
            residual_b = b["residual_um"].to_numpy(float)
            differences = error_b - error_a
            tolerance = 1e-12
            for simulation_id, numeric_id, value_a, value_b, difference in zip(
                a.index,
                a["heldout_numeric_simulation_id"].to_numpy(int),
                error_a,
                error_b,
                differences,
            ):
                detail_rows.append(
                    {
                        "target": target_key,
                        "method_a": method_a,
                        "method_b": method_b,
                        "simulation_id": simulation_id,
                        "numeric_simulation_id": numeric_id,
                        "absolute_error_a_um": value_a,
                        "absolute_error_b_um": value_b,
                        "absolute_error_difference_b_minus_a_um": difference,
                        "method_b_outcome": (
                            "improved"
                            if difference < -tolerance
                            else "worsened"
                            if difference > tolerance
                            else "tied"
                        ),
                    }
                )
            seed = deterministic_seed(
                "paired-bootstrap", target_key, method_a, method_b
            )
            mae_boot, rmse_boot = _paired_bootstrap_differences(
                residual_a,
                residual_b,
                seed=seed,
            )
            mae_low, mae_high = np.quantile(
                mae_boot, BOOTSTRAP_QUANTILES
            )
            rmse_low, rmse_high = np.quantile(
                rmse_boot, BOOTSTRAP_QUANTILES
            )
            summary_rows.append(
                {
                    "target": target_key,
                    "method_a": method_a,
                    "method_b": method_b,
                    "n_aligned_simulations": len(a),
                    "method_b_improved_count": int(
                        (differences < -tolerance).sum()
                    ),
                    "method_b_worsened_count": int(
                        (differences > tolerance).sum()
                    ),
                    "tied_count": int(
                        (np.abs(differences) <= tolerance).sum()
                    ),
                    "observed_mae_difference_b_minus_a_um": float(
                        error_b.mean() - error_a.mean()
                    ),
                    "mae_difference_ci95_low_um": float(mae_low),
                    "mae_difference_ci95_high_um": float(mae_high),
                    "mae_difference_ci_includes_zero": bool(
                        mae_low <= 0 <= mae_high
                    ),
                    "observed_rmse_difference_b_minus_a_um": float(
                        np.sqrt(np.mean(residual_b**2))
                        - np.sqrt(np.mean(residual_a**2))
                    ),
                    "rmse_difference_ci95_low_um": float(rmse_low),
                    "rmse_difference_ci95_high_um": float(rmse_high),
                    "rmse_difference_ci_includes_zero": bool(
                        rmse_low <= 0 <= rmse_high
                    ),
                    "bootstrap_resamples": PAIRED_BOOTSTRAP_RESAMPLES,
                    "bootstrap_seed": seed,
                    "interpretation": (
                        "negative difference favors method_b; superiority "
                        "is not robust when the interval includes zero"
                    ),
                }
            )
    return (
        pd.DataFrame(detail_rows).sort_values(
            ["target", "method_a", "method_b", "numeric_simulation_id"]
        ),
        pd.DataFrame(summary_rows).sort_values(
            ["target", "method_a", "method_b"]
        ),
    )


def _rmse_comparison_is_robust(
    paired_summary: pd.DataFrame,
    *,
    target_key: str,
    preferred: str,
    other: str,
) -> bool:
    row = paired_summary.loc[
        (paired_summary["target"] == target_key)
        & (
            (
                (paired_summary["method_a"] == preferred)
                & (paired_summary["method_b"] == other)
            )
            | (
                (paired_summary["method_a"] == other)
                & (paired_summary["method_b"] == preferred)
            )
        )
    ].iloc[0]
    if row["method_a"] == preferred:
        # reported difference is other - preferred
        return bool(row["rmse_difference_ci95_low_um"] > 0)
    # reported difference is preferred - other
    return bool(row["rmse_difference_ci95_high_um"] < 0)


def select_preferred_methods(
    metrics: pd.DataFrame,
    paired_summary: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for target_key in TARGET_COLUMNS:
        target_metrics = metrics.loc[
            (metrics["target"] == target_key)
            & (metrics["analysis_label"] == "full_population_loo")
        ].copy()
        target_metrics = target_metrics.sort_values(
            ["rmse_um", "mae_um", "mean_nlpd", "total_runtime_seconds"]
        )
        preferred = str(target_metrics.iloc[0]["method"])
        robust_against = {
            other: _rmse_comparison_is_robust(
                paired_summary,
                target_key=target_key,
                preferred=preferred,
                other=other,
            )
            for other in METHODS
            if other != preferred
        }
        robust = all(robust_against.values())
        best = target_metrics.iloc[0]
        mae_winner = str(
            target_metrics.sort_values("mae_um").iloc[0]["method"]
        )
        nlpd_winner = str(
            target_metrics.sort_values("mean_nlpd").iloc[0]["method"]
        )
        rows.append(
            {
                "target": target_key,
                "preferred_method": preferred,
                "selection_strength": (
                    "robust paired-RMSE advantage"
                    if robust
                    else "numerical preference; paired uncertainty overlaps zero"
                ),
                "rmse_winner": preferred,
                "mae_winner": mae_winner,
                "nlpd_winner": nlpd_winner,
                "rmse_um": float(best["rmse_um"]),
                "mae_um": float(best["mae_um"]),
                "mean_nlpd": float(best["mean_nlpd"]),
                "latent_95_coverage": float(
                    best["latent_95_coverage"]
                ),
                "observation_95_coverage": float(
                    best["observation_95_coverage"]
                )
                if np.isfinite(best["observation_95_coverage"])
                else np.nan,
                "robust_against_other_methods": json_compact(
                    robust_against
                ),
                "scientific_interpretation": (
                    "Point prediction has first priority. NLPD, calibration, "
                    "optimization stability, interpretability, and runtime "
                    "are reported as secondary evidence; no claim is made "
                    "from R² alone."
                ),
            }
        )
    return pd.DataFrame(rows)


def run_stable_subset_loo(
    modelling_table: pd.DataFrame,
    preferences: pd.DataFrame,
    *,
    workers: int,
    force: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    stable = modelling_table.loc[
        ~modelling_table["flag_primary_window_unstable"].astype(bool)
    ].copy()
    if len(stable) != 230:
        raise RuntimeError(f"Expected 230 stable simulations, got {len(stable)}")
    prediction_frames: list[pd.DataFrame] = []
    metric_rows: list[dict[str, Any]] = []
    for preference in preferences.itertuples():
        target_key = str(preference.target)
        method = str(preference.preferred_method)
        prediction = run_loo_method(
            stable,
            target_key=target_key,
            method=method,
            analysis_label="stable_only_refit_loo",
            workers=workers,
            force=force,
        )
        prediction_frames.append(prediction)
        metric_rows.append(metric_row(prediction))
    return (
        pd.concat(prediction_frames, ignore_index=True),
        pd.DataFrame(metric_rows),
    )


def build_stable_subset_sensitivity(
    primary_predictions: dict[str, pd.DataFrame],
    stable_predictions: pd.DataFrame,
    preferences: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for preference in preferences.itertuples():
        target_key = str(preference.target)
        method = str(preference.preferred_method)
        full = primary_predictions[target_key].loc[
            primary_predictions[target_key]["method"] == method
        ]
        full_stable = full.loc[
            ~full["phase1_unstable_window_flag"].astype(bool)
        ]
        refit_stable = stable_predictions.loc[
            (stable_predictions["target"] == target_key)
            & (stable_predictions["method"] == method)
        ]
        if len(full) != 241 or len(full_stable) != 230 or len(refit_stable) != 230:
            raise RuntimeError(
                f"{target_key}: stable sensitivity row counts are invalid"
            )
        metric_full = metric_row(
            full, analysis_label="full_241_all_heldouts"
        )
        metric_full_stable = metric_row(
            full_stable,
            analysis_label="full_population_model_stable_heldouts_230",
        )
        metric_refit = metric_row(
            refit_stable,
            analysis_label="stable_only_refit_loo_230",
        )
        reference_rmse = metric_full_stable["rmse_um"]
        refit_relative_change = (
            (metric_refit["rmse_um"] - reference_rmse) / reference_rmse
            if reference_rmse > 0
            else np.nan
        )
        material = bool(
            np.isfinite(refit_relative_change)
            and abs(refit_relative_change) >= 0.05
        )
        for metric in (metric_full, metric_full_stable, metric_refit):
            rows.append(
                {
                    **metric,
                    "preferred_method": method,
                    "stable_refit_rmse_relative_change_vs_full_model_stable_heldouts": (
                        refit_relative_change
                    ),
                    "material_change_threshold": 0.05,
                    "unstable_windows_materially_affect_conclusion": material,
                    "interpretation": (
                        "Material means at least 5% absolute RMSE change "
                        "between stable-only refit LOO and the stable held-out "
                        "rows from full-population LOO."
                    ),
                }
            )
    return pd.DataFrame(rows)


def build_hyperparameter_diagnostics(
    predictions: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    columns = [
        "analysis_label",
        "config_fingerprint",
        "target",
        "method",
        "fold_index",
        "heldout_simulation_id",
        "heldout_numeric_simulation_id",
        "optimized_kernel",
        "optimized_length_scale",
        "optimized_signal_variance_normalized",
        "optimized_noise_variance_normalized",
        "optimized_noise_std_normalized",
        "optimized_noise_std_um",
        "noise_std_fraction_training_target_std",
        "training_alpha_normalized_min",
        "training_alpha_normalized_median",
        "training_alpha_normalized_max",
        "log_marginal_likelihood",
        "runtime_seconds",
        "warning_count",
        "convergence_warning_count",
        "warnings",
        "convergence_status",
        "failed_fold",
        "constant_bound_hit",
        "constant_bound_side",
        "length_scale_bound_hit",
        "length_scale_bound_side",
        "noise_bound_hit",
        "noise_bound_side",
        "any_hyperparameter_bound_hit",
        "fold_random_seed",
    ]
    return pd.concat(
        [frame[columns] for frame in predictions.values()],
        ignore_index=True,
    ).sort_values(["target", "method", "fold_index"])


def build_learned_nugget_summary(
    predictions: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for target_key, frame in predictions.items():
        nugget = frame.loc[frame["method"] == "B_learned_nugget"]
        variance = nugget["optimized_noise_variance_normalized"]
        std_um = nugget["optimized_noise_std_um"]
        fraction = nugget["noise_std_fraction_training_target_std"]
        rows.append(
            {
                "target": target_key,
                "target_label": TARGET_LABELS[target_key],
                "fold_count": len(nugget),
                "noise_variance_normalized_min": float(variance.min()),
                "noise_variance_normalized_q25": float(
                    variance.quantile(0.25)
                ),
                "noise_variance_normalized_median": float(
                    variance.median()
                ),
                "noise_variance_normalized_q75": float(
                    variance.quantile(0.75)
                ),
                "noise_variance_normalized_max": float(variance.max()),
                "noise_std_um_min": float(std_um.min()),
                "noise_std_um_q25": float(std_um.quantile(0.25)),
                "noise_std_um_median": float(std_um.median()),
                "noise_std_um_q75": float(std_um.quantile(0.75)),
                "noise_std_um_max": float(std_um.max()),
                "noise_std_fraction_training_std_min": float(
                    fraction.min()
                ),
                "noise_std_fraction_training_std_median": float(
                    fraction.median()
                ),
                "noise_std_fraction_training_std_max": float(
                    fraction.max()
                ),
                "noise_std_um_coefficient_of_variation_across_folds": (
                    float(std_um.std(ddof=1) / std_um.mean())
                    if std_um.mean() > 0
                    else np.nan
                ),
                "noise_bound_hit_folds": int(
                    nugget["noise_bound_hit"].sum()
                ),
                "optimizer_warning_folds": int(
                    nugget["warning_count"].gt(0).sum()
                ),
                "interpretation": (
                    "effective nugget that can absorb target-summary "
                    "variability, unresolved inputs, kernel misspecification, "
                    "and model discrepancy; not stochastic simulator noise"
                ),
            }
        )
    return pd.DataFrame(rows)


def build_heteroskedastic_alpha_summary(
    uncertainty: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for target_key in TARGET_COLUMNS:
        target_rows = uncertainty.loc[uncertainty["target"] == target_key]
        subsets = {
            "all": target_rows,
            "stable_window": target_rows.loc[
                ~target_rows["phase1_unstable_window_flag"].astype(bool)
            ],
            "unstable_window": target_rows.loc[
                target_rows["phase1_unstable_window_flag"].astype(bool)
            ],
        }
        for subset_name, subset in subsets.items():
            variance = subset["bootstrap_variance_um2"]
            std = subset["bootstrap_median_std_um"]
            rows.append(
                {
                    "target": target_key,
                    "target_label": TARGET_LABELS[target_key],
                    "subset": subset_name,
                    "simulation_count": len(subset),
                    "variance_um2_min": float(variance.min()),
                    "variance_um2_q25": float(variance.quantile(0.25)),
                    "variance_um2_median": float(variance.median()),
                    "variance_um2_q75": float(variance.quantile(0.75)),
                    "variance_um2_q95": float(variance.quantile(0.95)),
                    "variance_um2_max": float(variance.max()),
                    "std_um_min": float(std.min()),
                    "std_um_q25": float(std.quantile(0.25)),
                    "std_um_median": float(std.median()),
                    "std_um_q75": float(std.quantile(0.75)),
                    "std_um_q95": float(std.quantile(0.95)),
                    "std_um_max": float(std.max()),
                    "zero_variance_count": int(variance.eq(0).sum()),
                    "interpretation": (
                        "moving-block-bootstrap uncertainty of the selected "
                        "window median; used as physical-unit training alpha "
                        "only after fold-local variance scaling"
                    ),
                }
            )
    return pd.DataFrame(rows)


def build_model_ready_summary(
    modelling_table: pd.DataFrame,
) -> pd.DataFrame:
    result = modelling_table[
        ["simulation_id", *FEATURE_COLUMNS]
    ].copy()
    result["selected_width_target_um"] = modelling_table["width_target_um"]
    result["selected_length_target_um"] = modelling_table[
        "length_target_um"
    ]
    result["selected_depth_target_um"] = modelling_table["depth_target_um"]
    result["width_target_summary_uncertainty_um"] = modelling_table[
        "width_bootstrap_std_um"
    ]
    result["length_target_summary_uncertainty_um"] = modelling_table[
        "length_bootstrap_std_um"
    ]
    result["depth_target_summary_uncertainty_um"] = modelling_table[
        "depth_bootstrap_std_um"
    ]
    result["phase1_unstable_window_flag"] = modelling_table[
        "flag_primary_window_unstable"
    ].astype(bool)
    expected_columns = [
        "simulation_id",
        "P",
        "VX",
        "LS",
        "ST",
        "selected_width_target_um",
        "selected_length_target_um",
        "selected_depth_target_um",
        "width_target_summary_uncertainty_um",
        "length_target_summary_uncertainty_um",
        "depth_target_summary_uncertainty_um",
        "phase1_unstable_window_flag",
    ]
    if list(result.columns) != expected_columns:
        raise RuntimeError("Model-ready summary column policy changed")
    return result


METHOD_COLORS = {
    "A_tiny_jitter": "#1f77b4",
    "B_learned_nugget": "#ff7f0e",
    "C_heteroskedastic": "#2ca02c",
}
METHOD_SHORT = {
    "A_tiny_jitter": "A: tiny jitter",
    "B_learned_nugget": "B: learned nugget",
    "C_heteroskedastic": "C: heteroskedastic",
}


def _save_figure(fig: plt.Figure, filename: str) -> Path:
    path = OUTPUT_DIR / filename
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_observed_vs_predicted(
    predictions: dict[str, pd.DataFrame],
) -> list[Path]:
    paths = []
    for target_key, frame in predictions.items():
        fig, ax = plt.subplots(figsize=(7.2, 6.2))
        observed_min = float(frame["observed_target_um"].min())
        observed_max = float(frame["observed_target_um"].max())
        padding = 0.04 * (observed_max - observed_min)
        bounds = (observed_min - padding, observed_max + padding)
        ax.plot(bounds, bounds, color="black", linestyle="--", linewidth=1)
        for method in METHODS:
            subset = frame.loc[frame["method"] == method]
            ax.scatter(
                subset["observed_target_um"],
                subset["predicted_mean_um"],
                s=22,
                alpha=0.68,
                label=METHOD_SHORT[method],
                color=METHOD_COLORS[method],
            )
        ax.set(
            xlabel="Observed selected target (µm)",
            ylabel="LOO predictive mean (µm)",
            title=f"{TARGET_LABELS[target_key]}: observed vs LOO prediction",
            xlim=bounds,
            ylim=bounds,
        )
        ax.legend(frameon=False)
        ax.grid(alpha=0.2)
        paths.append(
            _save_figure(fig, f"observed_vs_loo_{target_key}.png")
        )
    return paths


def plot_absolute_error_comparison(
    predictions: dict[str, pd.DataFrame],
) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.8), sharey=False)
    for ax, target_key in zip(axes, TARGET_COLUMNS):
        frame = predictions[target_key]
        values = [
            frame.loc[
                frame["method"] == method, "absolute_error_um"
            ].to_numpy()
            for method in METHODS
        ]
        boxes = ax.boxplot(values, patch_artist=True, showfliers=False)
        for patch, method in zip(boxes["boxes"], METHODS):
            patch.set_facecolor(METHOD_COLORS[method])
            patch.set_alpha(0.65)
        ax.set_xticks(
            range(1, 4), ["A", "B", "C"]
        )
        ax.set_title(TARGET_LABELS[target_key])
        ax.set_ylabel("Absolute LOO error (µm)")
        ax.grid(axis="y", alpha=0.2)
    fig.suptitle("Absolute-error distributions across observation treatments")
    return _save_figure(fig, "absolute_error_comparison.png")


def plot_residual_distributions(
    predictions: dict[str, pd.DataFrame],
) -> list[Path]:
    paths = []
    for target_key, frame in predictions.items():
        fig, ax = plt.subplots(figsize=(7.5, 5.0))
        for method in METHODS:
            residuals = frame.loc[
                frame["method"] == method, "residual_um"
            ]
            ax.hist(
                residuals,
                bins=25,
                alpha=0.42,
                density=True,
                color=METHOD_COLORS[method],
                label=METHOD_SHORT[method],
            )
        ax.axvline(0, color="black", linewidth=1)
        ax.set(
            xlabel="Residual = observed − predicted (µm)",
            ylabel="Density",
            title=f"{TARGET_LABELS[target_key]}: LOO residual distributions",
        )
        ax.legend(frameon=False)
        ax.grid(alpha=0.15)
        paths.append(
            _save_figure(fig, f"residual_distribution_{target_key}.png")
        )
    return paths


def plot_interval_diagnostics(
    predictions: dict[str, pd.DataFrame],
) -> list[Path]:
    paths = []
    for target_key, frame in predictions.items():
        fig, axes = plt.subplots(3, 1, figsize=(9.0, 9.0), sharex=True)
        for ax, method in zip(axes, METHODS):
            subset = frame.loc[frame["method"] == method].sort_values(
                "heldout_numeric_simulation_id"
            )
            standardized = np.abs(subset["residual_um"]) / subset[
                "evaluation_predictive_std_um"
            ]
            colors = np.where(
                subset["phase1_unstable_window_flag"].astype(bool),
                "#d62728",
                METHOD_COLORS[method],
            )
            ax.scatter(
                subset["heldout_numeric_simulation_id"],
                standardized,
                s=14,
                c=colors,
                alpha=0.75,
            )
            ax.axhline(1.96, color="black", linestyle="--", linewidth=1)
            ax.set_ylabel("|residual| / σ")
            ax.set_title(
                f"{METHOD_SHORT[method]} — "
                f"{subset['evaluation_variance_definition'].iloc[0]}"
            )
            ax.grid(alpha=0.15)
        axes[-1].set_xlabel("Held-out numeric simulation ID")
        fig.suptitle(
            f"{TARGET_LABELS[target_key]}: 95% predictive-interval diagnostic\n"
            "red points have the Phase 1 unstable-window flag"
        )
        fig.tight_layout()
        paths.append(
            _save_figure(
                fig, f"predictive_interval_diagnostics_{target_key}.png"
            )
        )
    return paths


def plot_point_metrics(metrics: pd.DataFrame) -> Path:
    primary = metrics.loc[
        metrics["analysis_label"] == "full_population_loo"
    ]
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.8))
    for ax, metric, label in zip(
        axes,
        ["mae_um", "rmse_um", "nrmse"],
        ["MAE (µm)", "RMSE (µm)", "nRMSE"],
    ):
        x = np.arange(len(TARGET_COLUMNS))
        width = 0.24
        for method_index, method in enumerate(METHODS):
            values = [
                primary.loc[
                    (primary["target"] == target)
                    & (primary["method"] == method),
                    metric,
                ].iloc[0]
                for target in TARGET_COLUMNS
            ]
            ax.bar(
                x + (method_index - 1) * width,
                values,
                width=width,
                color=METHOD_COLORS[method],
                label=METHOD_SHORT[method],
            )
        ax.set_xticks(x, ["Width", "Length", "Depth"])
        ax.set_ylabel(label)
        ax.grid(axis="y", alpha=0.2)
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("LOO point-prediction metrics (lower is better)")
    return _save_figure(fig, "point_metric_comparison.png")


def plot_nlpd_coverage(metrics: pd.DataFrame) -> Path:
    primary = metrics.loc[
        metrics["analysis_label"] == "full_population_loo"
    ]
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.8))
    x = np.arange(len(TARGET_COLUMNS))
    width = 0.24
    for method_index, method in enumerate(METHODS):
        nlpd = [
            primary.loc[
                (primary["target"] == target)
                & (primary["method"] == method),
                "mean_nlpd",
            ].iloc[0]
            for target in TARGET_COLUMNS
        ]
        coverage = [
            primary.loc[
                (primary["target"] == target)
                & (primary["method"] == method),
                (
                    "observation_95_coverage"
                    if method != "A_tiny_jitter"
                    else "latent_95_coverage"
                ),
            ].iloc[0]
            for target in TARGET_COLUMNS
        ]
        axes[0].bar(
            x + (method_index - 1) * width,
            nlpd,
            width=width,
            color=METHOD_COLORS[method],
            label=METHOD_SHORT[method],
        )
        axes[1].bar(
            x + (method_index - 1) * width,
            coverage,
            width=width,
            color=METHOD_COLORS[method],
        )
    for ax in axes:
        ax.set_xticks(x, ["Width", "Length", "Depth"])
        ax.grid(axis="y", alpha=0.2)
    axes[0].set_ylabel("Mean NLPD (lower is better)")
    axes[1].set_ylabel("95% interval coverage")
    axes[1].axhline(0.95, color="black", linestyle="--", linewidth=1)
    axes[1].set_ylim(0, 1.05)
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("Predictive density and calibration")
    return _save_figure(fig, "nlpd_and_coverage_comparison.png")


def plot_learned_nuggets(
    predictions: dict[str, pd.DataFrame],
) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(14.0, 4.5))
    for ax, target_key in zip(axes, TARGET_COLUMNS):
        values = predictions[target_key].loc[
            predictions[target_key]["method"] == "B_learned_nugget",
            "optimized_noise_std_um",
        ]
        ax.hist(values, bins=24, color=METHOD_COLORS["B_learned_nugget"], alpha=0.75)
        ax.axvline(values.median(), color="black", linestyle="--")
        ax.set_title(TARGET_LABELS[target_key])
        ax.set_xlabel("Learned effective-nugget std (µm)")
        ax.set_ylabel("LOO folds")
        ax.grid(alpha=0.15)
    fig.suptitle("Learned effective nugget across folds (not simulator noise)")
    return _save_figure(fig, "learned_nugget_distributions.png")


def plot_observation_specific_uncertainty(
    uncertainty: pd.DataFrame,
) -> tuple[Path, Path]:
    fig, axes = plt.subplots(1, 3, figsize=(14.0, 4.5))
    for ax, target_key in zip(axes, TARGET_COLUMNS):
        values = uncertainty.loc[
            uncertainty["target"] == target_key,
            "bootstrap_median_std_um",
        ]
        ax.hist(values, bins=24, color=METHOD_COLORS["C_heteroskedastic"], alpha=0.75)
        ax.axvline(values.median(), color="black", linestyle="--")
        ax.set_title(TARGET_LABELS[target_key])
        ax.set_xlabel("Target-summary uncertainty std (µm)")
        ax.set_ylabel("Simulations")
        ax.grid(alpha=0.15)
    fig.suptitle("Observation-specific moving-block-bootstrap uncertainty")
    distribution_path = _save_figure(
        fig, "observation_specific_uncertainty_distributions.png"
    )

    fig, axes = plt.subplots(1, 3, figsize=(14.0, 4.5))
    for ax, target_key in zip(axes, TARGET_COLUMNS):
        target_rows = uncertainty.loc[
            uncertainty["target"] == target_key
        ]
        groups = [
            target_rows.loc[
                ~target_rows["phase1_unstable_window_flag"].astype(bool),
                "bootstrap_median_std_um",
            ],
            target_rows.loc[
                target_rows["phase1_unstable_window_flag"].astype(bool),
                "bootstrap_median_std_um",
            ],
        ]
        boxes = ax.boxplot(groups, patch_artist=True, showfliers=True)
        boxes["boxes"][0].set_facecolor("#7f7f7f")
        boxes["boxes"][1].set_facecolor("#d62728")
        ax.set_xticks([1, 2], ["Stable", "Flagged"])
        ax.set_title(TARGET_LABELS[target_key])
        ax.set_ylabel("Target-summary uncertainty std (µm)")
        ax.grid(axis="y", alpha=0.2)
    fig.suptitle("Target-summary uncertainty versus Phase 1 instability flag")
    flag_path = _save_figure(
        fig, "target_uncertainty_vs_unstable_flag.png"
    )
    return distribution_path, flag_path


def plot_paired_error_differences(
    paired_detail: pd.DataFrame,
) -> list[Path]:
    paths = []
    for target_key in TARGET_COLUMNS:
        target_rows = paired_detail.loc[
            paired_detail["target"] == target_key
        ]
        fig, axes = plt.subplots(3, 1, figsize=(10.0, 8.5), sharex=True)
        for ax, ((method_a, method_b), pair_rows) in zip(
            axes, target_rows.groupby(["method_a", "method_b"])
        ):
            pair_rows = pair_rows.sort_values("numeric_simulation_id")
            difference = pair_rows[
                "absolute_error_difference_b_minus_a_um"
            ]
            ax.scatter(
                pair_rows["numeric_simulation_id"],
                difference,
                s=13,
                c=np.where(difference < 0, "#2ca02c", "#d62728"),
                alpha=0.7,
            )
            ax.axhline(0, color="black", linewidth=1)
            ax.set_ylabel("B − A error (µm)")
            ax.set_title(
                f"{METHOD_SHORT[method_b]} minus {METHOD_SHORT[method_a]}"
            )
            ax.grid(alpha=0.15)
        axes[-1].set_xlabel("Held-out numeric simulation ID")
        fig.suptitle(
            f"{TARGET_LABELS[target_key]}: paired absolute-error differences\n"
            "negative values favor the second named method"
        )
        fig.tight_layout()
        paths.append(
            _save_figure(fig, f"paired_error_differences_{target_key}.png")
        )
    return paths


def plot_stable_subset_sensitivity(
    stable_sensitivity: pd.DataFrame,
) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8))
    analysis_order = [
        "full_241_all_heldouts",
        "full_population_model_stable_heldouts_230",
        "stable_only_refit_loo_230",
    ]
    labels = ["Full 241", "Full fit, stable held-outs", "Stable-only refit"]
    x = np.arange(len(TARGET_COLUMNS))
    width = 0.24
    for analysis_index, (analysis, label) in enumerate(
        zip(analysis_order, labels)
    ):
        rows = stable_sensitivity.loc[
            stable_sensitivity["analysis_label"] == analysis
        ].set_index("target")
        axes[0].bar(
            x + (analysis_index - 1) * width,
            [rows.loc[target, "rmse_um"] for target in TARGET_COLUMNS],
            width=width,
            label=label,
        )
        axes[1].bar(
            x + (analysis_index - 1) * width,
            [rows.loc[target, "mean_nlpd"] for target in TARGET_COLUMNS],
            width=width,
            label=label,
        )
    for ax, ylabel in zip(axes, ["RMSE (µm)", "Mean NLPD"]):
        ax.set_xticks(x, ["Width", "Length", "Depth"])
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.2)
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("Preferred-method stable-window sensitivity")
    return _save_figure(fig, "stable_subset_sensitivity.png")


def generate_figures(
    *,
    predictions: dict[str, pd.DataFrame],
    metrics: pd.DataFrame,
    uncertainty: pd.DataFrame,
    paired_detail: pd.DataFrame,
    stable_sensitivity: pd.DataFrame,
) -> list[Path]:
    paths: list[Path] = []
    paths.extend(plot_observed_vs_predicted(predictions))
    paths.append(plot_absolute_error_comparison(predictions))
    paths.extend(plot_residual_distributions(predictions))
    paths.extend(plot_interval_diagnostics(predictions))
    paths.append(plot_point_metrics(metrics))
    paths.append(plot_nlpd_coverage(metrics))
    paths.append(plot_learned_nuggets(predictions))
    uncertainty_paths = plot_observation_specific_uncertainty(uncertainty)
    paths.extend(uncertainty_paths)
    paths.extend(plot_paired_error_differences(paired_detail))
    paths.append(plot_stable_subset_sensitivity(stable_sensitivity))
    return paths


def _notebook_clean() -> tuple[bool, str]:
    if not NOTEBOOK_PATH.exists():
        return False, "notebook does not exist"
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    code_cells = [
        cell
        for cell in notebook.get("cells", [])
        if cell.get("cell_type") == "code"
    ]
    errors = [
        output
        for cell in code_cells
        for output in cell.get("outputs", [])
        if output.get("output_type") == "error"
    ]
    executed = bool(code_cells) and all(
        cell.get("execution_count") is not None for cell in code_cells
    )
    return executed and not errors, (
        f"code_cells={len(code_cells)}, executed={executed}, "
        f"error_outputs={len(errors)}"
    )


def _original_worktree_unchanged() -> tuple[bool, str]:
    try:
        from src.week6_phase1_melt_pool_data_audit import (
            _original_worktree_unchanged as phase1_check,
        )
    except ModuleNotFoundError:
        # Direct script execution puts ``src`` rather than the repository root
        # on sys.path, so fall back to the sibling-module import in that mode.
        from week6_phase1_melt_pool_data_audit import (
            _original_worktree_unchanged as phase1_check,
        )

    return phase1_check()


def _git_diff_check() -> tuple[bool, str]:
    result = subprocess.run(
        ["git", "diff", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    detail = (result.stdout + result.stderr).strip()
    return result.returncode == 0, detail or "git diff --check passed"


def _scalers_are_fold_local(
    prediction_frames: Iterable[pd.DataFrame],
    modelling_tables: dict[str, pd.DataFrame],
) -> tuple[bool, str]:
    checked = 0
    for frame in prediction_frames:
        for row in frame.itertuples():
            source = modelling_tables[str(row.analysis_label)]
            heldout = str(row.heldout_simulation_id)
            training = source.loc[source["simulation_id"] != heldout]
            if len(training) != int(row.training_size):
                return False, f"{heldout}: training size mismatch"
            expected_y = training[f"{row.target}_target_um"].to_numpy(float)
            if not np.isclose(
                expected_y.mean(),
                float(row.training_y_mean_um),
                rtol=1e-11,
                atol=1e-11,
            ) or not np.isclose(
                expected_y.std(ddof=0),
                float(row.training_y_std_um),
                rtol=1e-11,
                atol=1e-11,
            ):
                return False, f"{heldout}: y scaler includes wrong rows"
            expected_X = training[FEATURE_COLUMNS].to_numpy(float)
            expected_x_mean = expected_X.mean(axis=0)
            expected_x_scale = expected_X.std(axis=0, ddof=0)
            expected_x_scale[expected_x_scale == 0] = 1.0
            recorded_mean = np.asarray(
                json.loads(row.x_training_mean), dtype=float
            )
            recorded_scale = np.asarray(
                json.loads(row.x_training_scale), dtype=float
            )
            if not np.allclose(
                recorded_mean,
                expected_x_mean,
                rtol=1e-11,
                atol=1e-14,
            ) or not np.allclose(
                recorded_scale,
                expected_x_scale,
                rtol=1e-11,
                atol=1e-14,
            ):
                return False, f"{heldout}: X scaler includes wrong rows"
            if (
                not bool(row.heldout_excluded_from_training)
                or not bool(row.x_scaler_fit_on_training_only)
                or not bool(row.y_scaler_fit_on_training_only)
                or bool(row.normalize_y)
            ):
                return False, f"{heldout}: fold-local policy flag failed"
            checked += 1
    return True, f"{checked} fold scalers independently recomputed"


def _metrics_match_predictions(
    metrics: pd.DataFrame,
    primary_predictions: dict[str, pd.DataFrame],
    stable_predictions: pd.DataFrame,
) -> tuple[bool, str]:
    frames: list[pd.DataFrame] = list(primary_predictions.values())
    frames.extend(
        [
            stable_predictions.loc[
                stable_predictions["target"] == target_key
            ]
            for target_key in TARGET_COLUMNS
        ]
    )
    checked = 0
    for frame in frames:
        for (analysis_label, target, method), group in frame.groupby(
            ["analysis_label", "target", "method"]
        ):
            expected = metric_row(group)
            row = metrics.loc[
                (metrics["analysis_label"] == analysis_label)
                & (metrics["target"] == target)
                & (metrics["method"] == method)
            ]
            if len(row) != 1:
                return False, (
                    f"Missing metric row: {analysis_label}/{target}/{method}"
                )
            row = row.iloc[0]
            for column in [
                "mae_um",
                "median_absolute_error_um",
                "rmse_um",
                "r2",
                "nrmse",
                "mean_nlpd",
                "median_nlpd",
                "latent_95_coverage",
            ]:
                if not np.isclose(
                    float(row[column]),
                    float(expected[column]),
                    rtol=1e-10,
                    atol=1e-12,
                    equal_nan=True,
                ):
                    return False, (
                        f"Metric mismatch {analysis_label}/{target}/"
                        f"{method}/{column}"
                    )
            checked += 1
    return True, f"{checked} metric rows independently recomputed"


def _nlpd_is_correct(
    prediction_frames: Iterable[pd.DataFrame],
) -> tuple[bool, str]:
    checked = 0
    for frame in prediction_frames:
        expected = gaussian_nlpd(
            frame["observed_target_um"].to_numpy(float),
            frame["predicted_mean_um"].to_numpy(float),
            frame["evaluation_predictive_std_um"].to_numpy(float) ** 2,
        )
        if not np.allclose(
            expected,
            frame["evaluation_nlpd"].to_numpy(float),
            rtol=1e-11,
            atol=1e-12,
        ):
            return False, "evaluation NLPD formula mismatch"
        for method, subset in frame.groupby("method"):
            definitions = set(subset["evaluation_variance_definition"])
            expected_definition = {
                "A_tiny_jitter": {"latent predictive variance"},
                "B_learned_nugget": {
                    "total predictive variance including learned WhiteKernel nugget"
                },
                "C_heteroskedastic": {
                    "oracle retrospective latent variance plus held-out target-summary variance"
                },
            }[method]
            if definitions != expected_definition:
                return False, f"{method}: wrong NLPD variance definition"
        checked += len(frame)
    return True, f"{checked} prediction NLPDs independently recomputed"


def build_validations(
    *,
    phase1: pd.DataFrame,
    modelling_table: pd.DataFrame,
    uncertainty: pd.DataFrame,
    primary_predictions: dict[str, pd.DataFrame],
    metrics: pd.DataFrame,
    paired_detail: pd.DataFrame,
    stable_predictions: pd.DataFrame,
) -> pd.DataFrame:
    primary_all = pd.concat(primary_predictions.values(), ignore_index=True)
    all_prediction_frames = [
        *primary_predictions.values(),
        stable_predictions,
    ]
    notebook_ok, notebook_detail = _notebook_clean()
    original_ok, original_detail = _original_worktree_unchanged()
    git_ok, git_detail = _git_diff_check()
    aggregate_hash, protected_count = phase1_aggregate_sha256()
    scaler_ok, scaler_detail = _scalers_are_fold_local(
        all_prediction_frames,
        {
            "full_population_loo": modelling_table,
            "stable_only_refit_loo": modelling_table.loc[
                ~modelling_table[
                    "flag_primary_window_unstable"
                ].astype(bool)
            ],
        },
    )
    metric_ok, metric_detail = _metrics_match_predictions(
        metrics, primary_predictions, stable_predictions
    )
    nlpd_ok, nlpd_detail = _nlpd_is_correct(all_prediction_frames)

    prediction_counts = (
        primary_all.groupby(["target", "method"])
        .size()
        .eq(241)
        .all()
    )
    prediction_unique = all(
        frame.loc[frame["method"] == method, "heldout_simulation_id"].is_unique
        for frame in primary_predictions.values()
        for method in METHODS
    )
    intervals_ordered = all(
        (
            frame["latent_interval_lower_um"]
            <= frame["latent_interval_upper_um"]
        ).all()
        and (
            frame.loc[
                frame["observation_interval_lower_um"].notna(),
                "observation_interval_lower_um",
            ]
            <= frame.loc[
                frame["observation_interval_lower_um"].notna(),
                "observation_interval_upper_um",
            ]
        ).all()
        and (
            frame.loc[
                frame["oracle_interval_lower_um"].notna(),
                "oracle_interval_lower_um",
            ]
            <= frame.loc[
                frame["oracle_interval_lower_um"].notna(),
                "oracle_interval_upper_um",
            ]
        ).all()
        for frame in all_prediction_frames
    )

    b_rows = primary_all.loc[
        primary_all["method"] == "B_learned_nugget"
    ]
    non_b_rows = primary_all.loc[
        primary_all["method"] != "B_learned_nugget"
    ]
    nugget_traceable = bool(
        np.isfinite(
            b_rows[
                [
                    "optimized_noise_variance_normalized",
                    "optimized_noise_std_normalized",
                    "optimized_noise_std_um",
                    "noise_std_fraction_training_target_std",
                ]
            ].to_numpy(float)
        ).all()
        and (
            b_rows["optimized_noise_variance_normalized"] > 0
        ).all()
        and non_b_rows[
            "optimized_noise_variance_normalized"
        ].isna().all()
    )

    paired_aligned = bool(
        len(paired_detail) == 3 * 3 * 241
        and paired_detail.groupby(
            ["target", "method_a", "method_b"]
        )["simulation_id"].nunique().eq(241).all()
    )
    stable_counts = bool(
        len(stable_predictions) == 3 * 230
        and stable_predictions.groupby(
            ["target", "method"]
        )["heldout_simulation_id"].nunique().eq(230).all()
        and not stable_predictions[
            "phase1_unstable_window_flag"
        ].astype(bool).any()
    )
    all_fitted_rows = pd.concat(
        [primary_all, stable_predictions], ignore_index=True
    )
    warning_traceable = bool(
        not all_fitted_rows[
            [
                "warning_count",
                "convergence_warning_count",
                "convergence_status",
                "failed_fold",
                "any_hyperparameter_bound_hit",
            ]
        ].isna().any().any()
        and (
            all_fitted_rows["warning_count"].eq(0)
            | all_fitted_rows["warnings"]
            .fillna("")
            .astype(str)
            .str.len()
            .gt(0)
        ).all()
        and not all_fitted_rows["failed_fold"].astype(bool).any()
    )
    target_values = phase1[
        [f"{target}_target_um" for target in TARGET_COLUMNS]
    ].to_numpy(float)

    checks = [
        (
            "exactly 241 unique simulation rows",
            len(phase1) == 241
            and phase1["simulation_id"].nunique() == 241,
            f"rows={len(phase1)}, unique={phase1['simulation_id'].nunique()}",
        ),
        (
            "X contains exactly P, VX, LS, ST",
            FEATURE_COLUMNS == ["P", "VX", "LS", "ST"],
            json_compact(FEATURE_COLUMNS),
        ),
        (
            "no target-derived feature leakage",
            set(primary_all["feature_columns"])
            == {json_compact(FEATURE_COLUMNS)}
            and not any(
                token in FEATURE_COLUMNS
                for token in ["target", "maximum", "flag", "simulation_id"]
            ),
            "every fold records the four allowed feature names only",
        ),
        (
            "three finite positive targets in micrometres",
            np.isfinite(target_values).all()
            and (target_values > 0).all(),
            f"target cells checked={target_values.size}",
        ),
        (
            "fold-local X scaling",
            scaler_ok,
            scaler_detail,
        ),
        (
            "fold-local y scaling",
            scaler_ok,
            scaler_detail,
        ),
        (
            "held-out target never used for scaling or optimization",
            scaler_ok
            and primary_all[
                "heldout_excluded_from_training"
            ].astype(bool).all()
            and stable_predictions[
                "heldout_excluded_from_training"
            ].astype(bool).all(),
            scaler_detail,
        ),
        (
            "exactly 241 predictions per target and method",
            prediction_counts,
            "nine primary groups, each with 241 rows",
        ),
        (
            "no duplicate held-out predictions",
            prediction_unique,
            "unique simulation ID within every target-method group",
        ),
        (
            "finite predictive means",
            np.isfinite(primary_all["predicted_mean_um"]).all()
            and np.isfinite(
                stable_predictions["predicted_mean_um"]
            ).all(),
            "primary and stable-only predictions checked",
        ),
        (
            "finite positive predictive standard deviations",
            (
                primary_all["latent_predictive_std_um"] > 0
            ).all()
            and np.isfinite(
                primary_all["latent_predictive_std_um"]
            ).all()
            and (
                stable_predictions["latent_predictive_std_um"] > 0
            ).all(),
            "latent standard deviations plus defined total deviations checked",
        ),
        (
            "non-negative observation-specific alpha values",
            np.isfinite(uncertainty["bootstrap_variance_um2"]).all()
            and (uncertainty["bootstrap_variance_um2"] >= 0).all(),
            f"uncertainty rows={len(uncertainty)}",
        ),
        (
            "bootstrap uncertainty traceability",
            len(uncertainty) == 723
            and uncertainty["phase1_target_reproduced"].astype(bool).all()
            and uncertainty["raw_window_series_sha256"].str.len().eq(64).all()
            and uncertainty["bootstrap_resamples"].eq(
                BOOTSTRAP_RESAMPLES
            ).all(),
            "three target rows per simulation with raw-window hashes",
        ),
        (
            "fitted nugget traceability",
            nugget_traceable,
            f"learned-nugget folds={len(b_rows)}",
        ),
        (
            "metrics independently recomputed from prediction rows",
            metric_ok,
            metric_detail,
        ),
        (
            "NLPD uses the correct variance definition",
            nlpd_ok,
            nlpd_detail,
        ),
        (
            "interval bounds ordered correctly",
            intervals_ordered,
            "latent, learned-nugget total, and oracle intervals checked",
        ),
        (
            "optimizer failures and warnings recorded",
            warning_traceable,
            (
                f"warning folds={int(all_fitted_rows['warning_count'].gt(0).sum())}; "
                f"failed folds={int(all_fitted_rows['failed_fold'].sum())}"
            ),
        ),
        (
            "paired comparisons align simulation IDs",
            paired_aligned,
            f"paired detail rows={len(paired_detail)}",
        ),
        (
            "stable-subset analysis contains exactly 230 simulations",
            stable_counts,
            f"stable prediction rows={len(stable_predictions)}",
        ),
        (
            "Phase 1 files unchanged",
            aggregate_hash == PHASE1_AGGREGATE_SHA256
            and sha256(PHASE1_INPUT) == PHASE1_LEDGER_SHA256,
            (
                f"protected_files={protected_count}; "
                f"aggregate_sha256={aggregate_hash}"
            ),
        ),
        (
            "original dirty worktree unchanged",
            original_ok,
            original_detail,
        ),
        (
            "notebook has zero error outputs",
            notebook_ok,
            notebook_detail,
        ),
        (
            "git diff --check passes",
            git_ok,
            git_detail,
        ),
    ]
    return pd.DataFrame(
        [
            {
                "validation_number": index,
                "validation_check": name,
                "status": "PASS" if bool(passed) else "FAIL",
                "passed": bool(passed),
                "details": detail,
            }
            for index, (name, passed, detail) in enumerate(checks, start=1)
        ]
    )


def build_requirement_checklist(
    validation: pd.DataFrame,
) -> pd.DataFrame:
    all_pass = validation["status"].eq("PASS").all()
    rows = [
        ("Fixed scope and Phase 1 provenance", "§1–2", "phase2_model_configuration.json"),
        ("Exact four-feature input policy", "§2", "phase2_input_target_table.csv"),
        ("Three observation treatments explained", "§3", "phase2_model_configuration.json"),
        ("Moving-block target-summary bootstrap", "§4", "target_summary_uncertainty_estimates.csv"),
        ("Half/base/double block sensitivity", "§4", "block_bootstrap_sensitivity.csv"),
        ("Fold-local X and y scaling", "§5", "hyperparameter_fold_diagnostics.csv"),
        ("Width 3-method LOO comparison", "§6", "width_loo_predictions.csv"),
        ("Length 3-method LOO comparison", "§7", "length_loo_predictions.csv"),
        ("Depth 3-method LOO comparison", "§8", "depth_loo_predictions.csv"),
        ("Point and uncertainty metrics", "§6–9", "all_model_metrics.csv"),
        ("Learned effective nugget", "§9", "learned_nugget_summary.csv"),
        ("Observation-specific alpha", "§9", "heteroskedastic_alpha_summary.csv"),
        ("Paired error analysis", "§10", "paired_method_comparisons.csv"),
        ("10,000-resample paired bootstrap", "§10", "paired_bootstrap_summary.csv"),
        ("Target-specific method selection", "§11", "preferred_method_selection.csv"),
        ("Stable-window sensitivity", "§12", "stable_subset_sensitivity.csv"),
        ("Concise model-ready table", "§13", "phase2_model_ready_summary.csv"),
        ("Optimizer and bound diagnostics", "§14", "hyperparameter_fold_diagnostics.csv"),
        ("Automated 24-check validation", "§15", "validation_results.csv"),
        ("Scientific decision log", "§16", "phase2_decision_log.md"),
        ("Strictly no later-phase work", "§1/§16", "results_summary.md"),
    ]
    return pd.DataFrame(
        [
            {
                "phase2_requirement": requirement,
                "notebook_section": section,
                "output_file": output,
                "validation_status": (
                    "PASS" if all_pass else "CHECK VALIDATION RESULTS"
                ),
            }
            for requirement, section, output in rows
        ]
    )


def _markdown_metric_table(metrics: pd.DataFrame) -> str:
    primary = metrics.loc[
        metrics["analysis_label"] == "full_population_loo"
    ].sort_values(["target", "method"])
    lines = [
        "| Target | Method | MAE µm | RMSE µm | R² | nRMSE | Mean NLPD | Latent cov. | Obs./oracle cov. |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in primary.itertuples():
        observation_coverage = (
            f"{row.observation_95_coverage:.3f}"
            if np.isfinite(row.observation_95_coverage)
            else "n/a"
        )
        lines.append(
            f"| {row.target} | {row.method} | {row.mae_um:.3f} | "
            f"{row.rmse_um:.3f} | {row.r2:.3f} | {row.nrmse:.4f} | "
            f"{row.mean_nlpd:.3f} | {row.latent_95_coverage:.3f} | "
            f"{observation_coverage} |"
        )
    return "\n".join(lines)


def build_decision_log(
    preferences: pd.DataFrame,
) -> str:
    preference_lines = "\n".join(
        f"- **{row.target}:** `{row.preferred_method}` — "
        f"{row.selection_strength}."
        for row in preferences.itertuples()
    )
    return f"""# Week 6 Phase 2 decision log

## Fixed scientific scope

Matérn 3/2 is fixed because this phase asks whether observation treatment changes
predictive behavior when the covariance family is held constant. Comparing RBF,
Matérn 5/2, ARD, or other kernels here would confound that question. Kernel-family
comparison, feature-effect analysis, active learning, and level-set estimation remain
deferred.

## Meaning of the three treatments

- **Approach A** treats the selected deterministic target as exact and adds only
  `alpha=1e-6` in normalized units for numerical stability. This is jitter, not noise.
- **Approach B** learns a homoskedastic WhiteKernel effective nugget. It may absorb
  target-summary variability, unresolved inputs, fixed-kernel misspecification, and
  model discrepancy. It is not evidence that the simulator itself is stochastic.
- **Approach C** uses simulation- and response-specific moving-block-bootstrap
  variances of the selected-window median. These are target-summary uncertainty
  proxies, transformed fold-locally into normalized alpha values.

## Limitations of the target-summary uncertainty proxy

The proxy describes temporal stability of a median within an already simulated
window. It does not measure experimental error, numerical discretization error,
between-run simulator randomness, or uncertainty for an unseen simulation. Its
retrospective oracle interval uses the held-out simulation's own bootstrap variance
and therefore is not deployable before that simulation has been run.

## Preferred treatments

{preference_lines}

Point prediction is the first selection criterion. NLPD and coverage, optimization
stability, scientific interpretation, and cost are secondary. A numerical winner is
not described as superior when paired bootstrap intervals include zero.

## Remaining work

Later work may study feature effects only after accepting the predictive treatment.
Active learning and level-set estimation have not started.

## Rebuild command

From the isolated Week 6 repository root:

```powershell
.\\.venv\\Scripts\\python.exe src\\week6_phase2_gp_response_noise_comparison.py --full --force --workers 4
```

Without `--force`, valid per-target/per-method checkpoints are reused.
"""


def build_results_summary(
    *,
    metrics: pd.DataFrame,
    preferences: pd.DataFrame,
    nugget_summary: pd.DataFrame,
    alpha_summary: pd.DataFrame,
    paired_summary: pd.DataFrame,
    stable_sensitivity: pd.DataFrame,
    validation: pd.DataFrame,
) -> str:
    preference_lines = "\n".join(
        f"- **{row.target}:** `{row.preferred_method}` "
        f"({row.selection_strength})."
        for row in preferences.itertuples()
    )
    nugget_lines = "\n".join(
        f"- **{row.target}:** median effective-nugget std "
        f"{row.noise_std_um_median:.4f} µm; median fraction of fold training "
        f"target std {row.noise_std_fraction_training_std_median:.4f}; "
        f"noise-bound hits {row.noise_bound_hit_folds}/{row.fold_count}."
        for row in nugget_summary.itertuples()
    )
    alpha_all = alpha_summary.loc[alpha_summary["subset"] == "all"]
    alpha_lines = "\n".join(
        f"- **{row.target}:** bootstrap std median "
        f"{row.std_um_median:.4f} µm, q95 {row.std_um_q95:.4f} µm, "
        f"max {row.std_um_max:.4f} µm."
        for row in alpha_all.itertuples()
    )
    paired_nonrobust = int(
        paired_summary["rmse_difference_ci_includes_zero"].sum()
    )
    material_targets = stable_sensitivity.loc[
        stable_sensitivity["analysis_label"] == "stable_only_refit_loo_230",
        ["target", "unstable_windows_materially_affect_conclusion"],
    ]
    stable_lines = "\n".join(
        f"- **{row.target}:** "
        f"{'material (≥5% RMSE change)' if row.unstable_windows_materially_affect_conclusion else 'not material under the 5% RMSE rule'}."
        for row in material_targets.itertuples()
    )
    return f"""# Week 6 Phase 2 GP response-noise comparison

## Scope and input

The corrected 241-row Phase 1 ledger at immutable Hugging Face revision
`{PHASE1_REVISION}` was used unchanged. Inputs are exactly `[P, VX, LS, ST]`.
Targets are width, length, and penetration depth converted from metres to
micrometres without redefining their Phase 1 selected-window median rule.

All models use `ConstantKernel × isotropic Matérn 3/2`, L-BFGS-B, one
deterministic extra restart, exact simulation-level LOO, and fold-local X/y
scaling.

## Primary 241-simulation LOO metrics

{_markdown_metric_table(metrics)}

Approach A's NLPD uses latent variance. Approach B uses total variance including the
learned effective nugget. Approach C uses the explicitly labelled retrospective oracle
variance; that oracle interval is not deployable for a new simulation.

## Preferred observation treatment

{preference_lines}

## Learned effective nugget

{nugget_lines}

The nugget is an effective discrepancy term, not stochastic simulator noise.

## Observation-specific target-summary uncertainty

{alpha_lines}

These values come from 500-resample circular moving-block bootstraps and are not
measurement-noise estimates.

## Paired conclusions

{paired_nonrobust}/{len(paired_summary)} paired RMSE-difference intervals include
zero. Method superiority is not claimed for comparisons whose interval crosses zero.

## Stable-window sensitivity

{stable_lines}

The 11 flagged simulations remain in the primary analysis and are not automatically
treated as invalid.

## Validation and readiness

{int(validation['status'].eq('PASS').sum())}/{len(validation)} automated checks pass.
The dataset is ready for later feature-effect analysis only under the target-specific
preferred observation treatments and the caveats above. No active learning or
level-set estimation was performed.
"""


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def build_summary_json(
    *,
    metrics: pd.DataFrame,
    preferences: pd.DataFrame,
    nugget_summary: pd.DataFrame,
    alpha_summary: pd.DataFrame,
    paired_summary: pd.DataFrame,
    stable_sensitivity: pd.DataFrame,
    validation: pd.DataFrame,
    full_runtime_seconds: float,
) -> dict[str, Any]:
    primary_metrics = metrics.loc[
        metrics["analysis_label"] == "full_population_loo"
    ]
    stable_rows = stable_sensitivity.loc[
        stable_sensitivity["analysis_label"] == "stable_only_refit_loo_230"
    ]
    return _json_safe(
        {
            "generated_at_utc": utc_now(),
            "phase1_input": str(PHASE1_INPUT.relative_to(ROOT)),
            "phase1_revision": PHASE1_REVISION,
            "phase1_rows": 241,
            "features": FEATURE_COLUMNS,
            "targets": TARGET_COLUMNS,
            "methods": METHODS,
            "primary_loo_model_count": 9,
            "primary_loo_prediction_count": int(
                primary_metrics["n_predictions"].sum()
            ),
            "metrics": primary_metrics.to_dict("records"),
            "preferences": preferences.to_dict("records"),
            "learned_nugget": nugget_summary.to_dict("records"),
            "heteroskedastic_alpha": alpha_summary.loc[
                alpha_summary["subset"] == "all"
            ].to_dict("records"),
            "paired_bootstrap_comparisons": paired_summary.to_dict("records"),
            "stable_subset_refit": stable_rows.to_dict("records"),
            "validation_pass_count": int(
                validation["status"].eq("PASS").sum()
            ),
            "validation_total_count": len(validation),
            "full_pipeline_runtime_seconds": full_runtime_seconds,
            "ready_for_later_feature_effect_analysis": bool(
                validation["status"].eq("PASS").all()
            ),
            "scope_status": (
                "No kernel-family comparison, ARD, active learning, "
                "level-set estimation, classifier, or feature-effect "
                "analysis performed."
            ),
        }
    )


def _uncertainty_cache_is_valid(frame: pd.DataFrame) -> bool:
    required = {
        "simulation_id",
        "target",
        "phase1_target_um",
        "selected_window_observation_count",
        "block_length",
        "bootstrap_resamples",
        "bootstrap_median_std_um",
        "bootstrap_variance_um2",
        "phase1_target_reproduced",
        "raw_window_series_sha256",
    }
    return bool(
        required.issubset(frame.columns)
        and len(frame) == 723
        and frame.groupby("simulation_id")["target"].nunique().eq(3).all()
        and frame["bootstrap_resamples"].eq(
            BOOTSTRAP_RESAMPLES
        ).all()
        and frame["phase1_target_reproduced"].astype(bool).all()
        and np.isfinite(frame["bootstrap_variance_um2"]).all()
        and (frame["bootstrap_variance_um2"] >= 0).all()
    )


def load_or_build_uncertainty(
    phase1: pd.DataFrame,
    *,
    force: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    uncertainty_path = OUTPUT_DIR / "target_summary_uncertainty_estimates.csv"
    sensitivity_path = OUTPUT_DIR / "block_bootstrap_sensitivity.csv"
    if not force and uncertainty_path.exists() and sensitivity_path.exists():
        uncertainty = pd.read_csv(uncertainty_path)
        sensitivity = pd.read_csv(sensitivity_path)
        if _uncertainty_cache_is_valid(uncertainty) and len(sensitivity) == 27:
            print("target-summary uncertainty cache reused", flush=True)
            return uncertainty, sensitivity

    uncertainty, series_cache = build_target_summary_uncertainty(phase1)
    sensitivity = build_block_bootstrap_sensitivity(
        uncertainty, series_cache
    )
    write_csv(uncertainty, "target_summary_uncertainty_estimates.csv")
    write_csv(sensitivity, "block_bootstrap_sensitivity.csv")
    return uncertainty, sensitivity


def _load_primary_predictions() -> dict[str, pd.DataFrame]:
    predictions = {
        target_key: pd.read_csv(
            OUTPUT_DIR / f"{target_key}_loo_predictions.csv"
        )
        for target_key in TARGET_COLUMNS
    }
    for target_key, frame in predictions.items():
        if len(frame) != 3 * 241:
            raise RuntimeError(
                f"{target_key} prediction artifact has {len(frame)} rows"
            )
    return predictions


def write_reporting_outputs(
    *,
    metrics: pd.DataFrame,
    preferences: pd.DataFrame,
    nugget_summary: pd.DataFrame,
    alpha_summary: pd.DataFrame,
    paired_summary: pd.DataFrame,
    stable_sensitivity: pd.DataFrame,
    validation: pd.DataFrame,
    full_runtime_seconds: float,
) -> dict[str, Any]:
    write_csv(validation, "validation_results.csv")
    write_csv(
        build_requirement_checklist(validation),
        "phase2_requirement_checklist.csv",
    )
    (OUTPUT_DIR / "phase2_decision_log.md").write_text(
        build_decision_log(preferences), encoding="utf-8"
    )
    (OUTPUT_DIR / "results_summary.md").write_text(
        build_results_summary(
            metrics=metrics,
            preferences=preferences,
            nugget_summary=nugget_summary,
            alpha_summary=alpha_summary,
            paired_summary=paired_summary,
            stable_sensitivity=stable_sensitivity,
            validation=validation,
        ),
        encoding="utf-8",
    )
    summary = build_summary_json(
        metrics=metrics,
        preferences=preferences,
        nugget_summary=nugget_summary,
        alpha_summary=alpha_summary,
        paired_summary=paired_summary,
        stable_sensitivity=stable_sensitivity,
        validation=validation,
        full_runtime_seconds=full_runtime_seconds,
    )
    write_json(summary, "summary.json")
    return summary


def run_full_pipeline(
    *,
    workers: int,
    force: bool,
    bootstrap_only: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config = configuration()
    write_json(config, "phase2_model_configuration.json")

    phase1 = load_phase1_input()
    aggregate_hash, protected_count = phase1_aggregate_sha256()
    if aggregate_hash != PHASE1_AGGREGATE_SHA256:
        raise RuntimeError(
            "Phase 1 protected-file aggregate changed before Phase 2"
        )
    print(
        f"Phase 1 verified: {len(phase1)} rows, "
        f"{protected_count} protected files",
        flush=True,
    )
    write_csv(
        build_phase2_input_table(phase1),
        "phase2_input_target_table.csv",
    )

    uncertainty, sensitivity = load_or_build_uncertainty(
        phase1, force=force
    )
    # Ensure both artifacts are refreshed even when loaded from a valid cache.
    write_csv(uncertainty, "target_summary_uncertainty_estimates.csv")
    write_csv(sensitivity, "block_bootstrap_sensitivity.csv")
    modelling_table = uncertainty_wide_table(phase1, uncertainty)
    write_csv(
        build_model_ready_summary(modelling_table),
        "phase2_model_ready_summary.csv",
    )
    write_csv(
        build_heteroskedastic_alpha_summary(uncertainty),
        "heteroskedastic_alpha_summary.csv",
    )

    if bootstrap_only:
        payload = {
            "status": "bootstrap_only_complete",
            "phase1_rows": len(phase1),
            "uncertainty_rows": len(uncertainty),
            "sensitivity_rows": len(sensitivity),
            "runtime_seconds": time.perf_counter() - started,
        }
        print(json.dumps(payload, indent=2))
        return payload

    primary_predictions = run_primary_loo(
        modelling_table,
        workers=workers,
        force=force,
    )
    for target_key, frame in primary_predictions.items():
        write_csv(frame, f"{target_key}_loo_predictions.csv")

    primary_metrics = build_all_metrics(primary_predictions)
    paired_detail, paired_summary = build_paired_comparisons(
        primary_predictions
    )
    preferences = select_preferred_methods(
        primary_metrics, paired_summary
    )
    stable_predictions, stable_metrics = run_stable_subset_loo(
        modelling_table,
        preferences,
        workers=workers,
        force=force,
    )
    metrics = pd.concat(
        [primary_metrics, stable_metrics],
        ignore_index=True,
    ).sort_values(["analysis_label", "target", "method"])
    stable_sensitivity = build_stable_subset_sensitivity(
        primary_predictions,
        stable_predictions,
        preferences,
    )

    write_csv(metrics, "all_model_metrics.csv")
    write_csv(paired_detail, "paired_method_comparisons.csv")
    write_csv(paired_summary, "paired_bootstrap_summary.csv")
    write_csv(preferences, "preferred_method_selection.csv")
    write_csv(
        stable_predictions, "stable_subset_loo_predictions.csv"
    )
    write_csv(
        stable_sensitivity, "stable_subset_sensitivity.csv"
    )

    hyperparameters = build_hyperparameter_diagnostics(
        primary_predictions
    )
    stable_hyperparameters = stable_predictions[
        hyperparameters.columns
    ]
    hyperparameters = pd.concat(
        [hyperparameters, stable_hyperparameters], ignore_index=True
    ).sort_values(["analysis_label", "target", "method", "fold_index"])
    write_csv(
        hyperparameters, "hyperparameter_fold_diagnostics.csv"
    )
    nugget_summary = build_learned_nugget_summary(
        primary_predictions
    )
    alpha_summary = build_heteroskedastic_alpha_summary(uncertainty)
    write_csv(nugget_summary, "learned_nugget_summary.csv")
    write_csv(alpha_summary, "heteroskedastic_alpha_summary.csv")

    figure_paths = generate_figures(
        predictions=primary_predictions,
        metrics=metrics,
        uncertainty=uncertainty,
        paired_detail=paired_detail,
        stable_sensitivity=stable_sensitivity,
    )
    print(f"figures generated: {len(figure_paths)}", flush=True)

    validation = build_validations(
        phase1=phase1,
        modelling_table=modelling_table,
        uncertainty=uncertainty,
        primary_predictions=primary_predictions,
        metrics=metrics,
        paired_detail=paired_detail,
        stable_predictions=stable_predictions,
    )
    full_runtime_seconds = time.perf_counter() - started
    summary = write_reporting_outputs(
        metrics=metrics,
        preferences=preferences,
        nugget_summary=nugget_summary,
        alpha_summary=alpha_summary,
        paired_summary=paired_summary,
        stable_sensitivity=stable_sensitivity,
        validation=validation,
        full_runtime_seconds=full_runtime_seconds,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def validate_existing_outputs() -> dict[str, Any]:
    phase1 = load_phase1_input()
    uncertainty = pd.read_csv(
        OUTPUT_DIR / "target_summary_uncertainty_estimates.csv"
    )
    if not _uncertainty_cache_is_valid(uncertainty):
        raise RuntimeError("Existing uncertainty artifact is invalid")
    modelling_table = uncertainty_wide_table(phase1, uncertainty)
    predictions = _load_primary_predictions()
    metrics = pd.read_csv(OUTPUT_DIR / "all_model_metrics.csv")
    paired_detail = pd.read_csv(
        OUTPUT_DIR / "paired_method_comparisons.csv"
    )
    paired_summary = pd.read_csv(
        OUTPUT_DIR / "paired_bootstrap_summary.csv"
    )
    preferences = pd.read_csv(
        OUTPUT_DIR / "preferred_method_selection.csv"
    )
    stable_predictions = pd.read_csv(
        OUTPUT_DIR / "stable_subset_loo_predictions.csv"
    )
    stable_sensitivity = pd.read_csv(
        OUTPUT_DIR / "stable_subset_sensitivity.csv"
    )
    nugget_summary = pd.read_csv(
        OUTPUT_DIR / "learned_nugget_summary.csv"
    )
    alpha_summary = pd.read_csv(
        OUTPUT_DIR / "heteroskedastic_alpha_summary.csv"
    )
    validation = build_validations(
        phase1=phase1,
        modelling_table=modelling_table,
        uncertainty=uncertainty,
        primary_predictions=predictions,
        metrics=metrics,
        paired_detail=paired_detail,
        stable_predictions=stable_predictions,
    )
    full_runtime_seconds = 0.0
    summary_path = OUTPUT_DIR / "summary.json"
    if summary_path.exists():
        try:
            full_runtime_seconds = float(
                json.loads(
                    summary_path.read_text(encoding="utf-8")
                ).get("full_pipeline_runtime_seconds", 0.0)
            )
        except Exception:
            full_runtime_seconds = 0.0
    return write_reporting_outputs(
        metrics=metrics,
        preferences=preferences,
        nugget_summary=nugget_summary,
        alpha_summary=alpha_summary,
        paired_summary=paired_summary,
        stable_sensitivity=stable_sensitivity,
        validation=validation,
        full_runtime_seconds=full_runtime_seconds,
    )


def run_smoke_test(*, workers: int) -> dict[str, Any]:
    phase1 = load_phase1_input()
    positions = [0, 1, 35, 80, 116, 117, 135, 160, 200, 223, 239, 240]
    smoke_phase1 = phase1.iloc[positions].copy().reset_index(drop=True)
    started = time.perf_counter()
    uncertainty, _ = build_target_summary_uncertainty(
        smoke_phase1,
        resamples=50,
        progress=False,
    )
    modelling = uncertainty_wide_table(smoke_phase1, uncertainty)
    metric_rows: list[dict[str, Any]] = []
    warning_count = 0
    bound_hits = 0
    for target_key in TARGET_COLUMNS:
        for method in METHODS:
            prediction = run_loo_method(
                modelling,
                target_key=target_key,
                method=method,
                analysis_label="smoke_12_simulations",
                workers=workers,
                n_restarts_optimizer=N_RESTARTS_OPTIMIZER,
                force=True,
                use_checkpoint=False,
            )
            metric_rows.append(metric_row(prediction))
            warning_count += int(prediction["warning_count"].sum())
            bound_hits += int(
                prediction["any_hyperparameter_bound_hit"].sum()
            )
    payload = {
        "status": "smoke_only_not_scientific_result",
        "simulation_count": len(smoke_phase1),
        "bootstrap_resamples": 50,
        "targets": list(TARGET_COLUMNS),
        "methods": METHODS,
        "model_comparisons": 9,
        "prediction_rows": 12 * 9,
        "optimizer_warning_count": warning_count,
        "bound_hit_count": bound_hits,
        "runtime_seconds": time.perf_counter() - started,
        "metrics": _json_safe(metric_rows),
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(payload, "smoke_test_summary.json")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--smoke", action="store_true")
    modes.add_argument("--bootstrap-only", action="store_true")
    modes.add_argument("--full", action="store_true")
    modes.add_argument("--validate-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--workers", type=int, default=DEFAULT_WORKERS
    )
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")
    if args.smoke:
        run_smoke_test(workers=args.workers)
    elif args.validate_only:
        summary = validate_existing_outputs()
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        run_full_pipeline(
            workers=args.workers,
            force=args.force,
            bootstrap_only=args.bootstrap_only,
        )


if __name__ == "__main__":
    main()
