#!/usr/bin/env python
"""Week 6 Phase 3: model-and-target robustness for melt-pool responses.

This module deliberately stays inside the Phase 3 scope:

* Phase 3A compares simple point-prediction baselines with the current GP.
* Phase 3B compares three isotropic GP kernel families, with and without a
  learned WhiteKernel nugget.
* Phase 3C reconstructs six simulation-level target definitions from the raw
  aligned monitor series, then evaluates them with one fixed GP per response.

The expensive stages are checkpointed.  The canonical deterministic rebuild is:

    .\\.venv\\Scripts\\python.exe src\\week6_phase3_model_target_robustness.py \
        --full --force --workers 4

No feature-effect analysis, active learning, level-set estimation, GP
classification, kinetic-energy modelling, or total-height modelling is
implemented here.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version as package_version
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
from typing import Any, Iterable, Sequence
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.compose import TransformedTargetRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import (
    ConstantKernel,
    Matern,
    RBF,
    WhiteKernel,
)
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from threadpoolctl import threadpool_limits

import week6_phase1_melt_pool_data_audit as phase1
import week6_phase2_gp_response_noise_comparison as phase2


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs" / "week6_03_model_target_robustness"
CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"
FIGURE_DIR = OUTPUT_DIR / "figures"
NOTEBOOK_PATH = (
    ROOT / "notebooks" / "week_06" / "04_phase3_model_target_robustness.ipynb"
)
NOTEBOOK_BUILDER = ROOT / "scripts" / "build_week6_04_notebook.py"
ORIGINAL_WORKTREE = Path(r"C:\Users\ozgur\Documents\thesis")
PREFLIGHT_PATH = OUTPUT_DIR / "phase3_preflight_snapshot.json"

EXPECTED_BRANCH = "codex/week6-phase3-model-target-robustness"
STARTING_HEAD = "b112f6b22898976f77410190614cb4fb218d38f9"
EXPECTED_PHASE1_REVISION = "0e859b748fdbc8454f66e58e101e333ac0479d42"
EXPECTED_PHASE1_LEDGER_SHA256 = (
    "10DEF11AB64D62444AC14FED506266BEB748EEB5BF892ACDC12E7F0F6DDCF4FF"
)
EXPECTED_PHASE1_AGGREGATE_SHA256 = (
    "21FF34AD767C8D4D6C536D66AFD147B8C700884321415078231B7A24D4C7D198"
)

FEATURE_COLUMNS = ["P", "VX", "LS", "ST"]
TARGET_KEYS = ["width", "length", "depth"]
TARGET_LABELS = {
    "width": "Melt-pool width",
    "length": "Melt-pool length",
    "depth": "Penetration depth below original surface",
}
TARGET_SOURCE_COLUMNS = {
    "width": "melt_pool_width_selected_primary_scalar_target_m",
    "length": "melt_pool_length_selected_primary_scalar_target_m",
    "depth": "melt_pool_depth_below_surface_selected_primary_scalar_target_m",
}
TARGET_UNSTABLE_CV_THRESHOLDS = {
    "width": 0.10,
    "length": 0.10,
    "depth": 0.15,
}
DEPTH_EXCLUSIONS = [
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
EXPECTED_POPULATION_SIZES = {"width": 241, "length": 241, "depth": 230}

CONSTANT_INITIAL = 1.0
CONSTANT_BOUNDS = (1e-3, 1e3)
LENGTH_SCALE_INITIAL = 1.0
LENGTH_SCALE_BOUNDS = (1e-2, 1e2)
WHITE_INITIAL = 1e-2
WHITE_BOUNDS = (1e-8, 1e1)
NO_NUGGET_ALPHA = 1e-6
LEARNED_NUGGET_ALPHA = 1e-8
N_RESTARTS_OPTIMIZER = 1
BOUND_TOLERANCE = 1e-4

BASE_RANDOM_SEED = 6303
RIDGE_ALPHA_GRID = tuple(float(10.0**power) for power in range(-6, 7))
RIDGE_INNER_FOLDS = 5
PAIRED_BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_QUANTILES = (0.025, 0.975)
DEFAULT_WORKERS = 4

SENTINEL_THRESHOLD = 1e30
MIN_CONTROLLED_WINDOW_ROWS = 50
TARGET_DEFINITION_CODES = ["T0", "T1", "T2", "T3", "T4", "T5"]
CURRENT_GP_CONFIG_NAME = "matern32_learned_nugget"


@dataclass(frozen=True)
class GPConfiguration:
    name: str
    kernel_family: str
    matern_nu: float | None
    learned_nugget: bool
    numerical_alpha_normalized: float
    label: str


GP_CONFIGURATIONS: tuple[GPConfiguration, ...] = (
    GPConfiguration(
        name="rbf_no_nugget",
        kernel_family="RBF",
        matern_nu=None,
        learned_nugget=False,
        numerical_alpha_normalized=NO_NUGGET_ALPHA,
        label="RBF, no nugget",
    ),
    GPConfiguration(
        name="rbf_learned_nugget",
        kernel_family="RBF",
        matern_nu=None,
        learned_nugget=True,
        numerical_alpha_normalized=LEARNED_NUGGET_ALPHA,
        label="RBF + learned nugget",
    ),
    GPConfiguration(
        name="matern32_no_nugget",
        kernel_family="Matern",
        matern_nu=1.5,
        learned_nugget=False,
        numerical_alpha_normalized=NO_NUGGET_ALPHA,
        label="Matérn 3/2, no nugget",
    ),
    GPConfiguration(
        name="matern32_learned_nugget",
        kernel_family="Matern",
        matern_nu=1.5,
        learned_nugget=True,
        numerical_alpha_normalized=LEARNED_NUGGET_ALPHA,
        label="Matérn 3/2 + learned nugget",
    ),
    GPConfiguration(
        name="matern52_no_nugget",
        kernel_family="Matern",
        matern_nu=2.5,
        learned_nugget=False,
        numerical_alpha_normalized=NO_NUGGET_ALPHA,
        label="Matérn 5/2, no nugget",
    ),
    GPConfiguration(
        name="matern52_learned_nugget",
        kernel_family="Matern",
        matern_nu=2.5,
        learned_nugget=True,
        numerical_alpha_normalized=LEARNED_NUGGET_ALPHA,
        label="Matérn 5/2 + learned nugget",
    ),
)
GP_CONFIG_BY_NAME = {item.name: item for item in GP_CONFIGURATIONS}


@dataclass(frozen=True)
class TargetDefinition:
    code: str
    label: str
    window_fraction: float | None
    cutoff_fraction: float | None
    aggregation: str
    final_valid_row_count: int | None = None


TARGET_DEFINITIONS: tuple[TargetDefinition, ...] = (
    TargetDefinition(
        "T0",
        "Current: median over final 20% before 90% +X cutoff",
        0.20,
        0.90,
        "median",
    ),
    TargetDefinition(
        "T1",
        "Shorter: median over final 10% before 90% +X cutoff",
        0.10,
        0.90,
        "median",
    ),
    TargetDefinition(
        "T2",
        "Longer: median over final 30% before 90% +X cutoff",
        0.30,
        0.90,
        "median",
    ),
    TargetDefinition(
        "T3",
        "Earlier: median over final 20% before 85% +X cutoff",
        0.20,
        0.85,
        "median",
    ),
    TargetDefinition(
        "T4",
        "Later: median over final 20% before 95% +X cutoff",
        0.20,
        0.95,
        "median",
    ),
    TargetDefinition(
        "T5",
        "Reference: mean of final 50 valid melt-present rows",
        None,
        None,
        "mean",
        final_valid_row_count=50,
    ),
)
TARGET_DEFINITION_BY_CODE = {item.code: item for item in TARGET_DEFINITIONS}


EXPECTED_CORE_ARTIFACT_HASHES = {
    "outputs/week6_01_melt_pool_data_audit/week6_phase1_simulation_level_responses.csv": EXPECTED_PHASE1_LEDGER_SHA256,
    "outputs/week6_01_melt_pool_data_audit/summary.json": "A18BC9A688792268F5514BCAA9758BEE327DC6F71AA15A14123C47B177357F96",
    "notebooks/week_06/01_melt_pool_monitor_data_audit.ipynb": "BB4897432224C9A16ADAE084FBE5004DD7987DA43BA9B6195C5DABD65D9DF65F",
    "src/week6_phase1_melt_pool_data_audit.py": "64A5E3998D411961CBFBC3AD0A761F9B9D8F2C876550548B835C3EBF0E1C63A4",
    "notebooks/week_06/02_gp_response_noise_comparison.ipynb": "DF04ADF427DA98D238488C0BE6D15807ACBDE07478F35F22D187CDD707FBA359",
    "src/week6_phase2_gp_response_noise_comparison.py": "4228223095EA40A4F05DC6084C565E99FA0E0747AB2B8C0891C2C534B6BA9701",
    "outputs/week6_02_gp_response_noise_comparison/phase2_model_configuration.json": "CBBA81F86E9B2B9FF46838B793733D9C7DE2982D1A398A67578A8AAE6C3647A6",
    "outputs/week6_02_gp_response_noise_comparison/width_loo_predictions.csv": "32FF3A2DB237D1A13CE35903F6B95E66EB614D9FD3028F4E9D429FA915A68F75",
    "outputs/week6_02_gp_response_noise_comparison/length_loo_predictions.csv": "50531D5BC00DC5C9FBAC897A2568929C344BB371FBF181339808B6EB8F44E1D0",
    "outputs/week6_02_gp_response_noise_comparison/depth_loo_predictions.csv": "B511702EAD9A91BBC407E2F9D447E62998470F3FD4214CE020520418B589DC00",
    "outputs/week6_02_gp_response_noise_comparison/stable_subset_loo_predictions.csv": "26C6A6E78B441B22DCCCE8B1573028F539ACD66FC962796ADE43344302E44525",
    "outputs/week6_02_gp_response_noise_comparison/summary.json": "E95161972078503BF67926D549A1140274DC91F8F12BF899BD882FF9F84C75EF",
    "notebooks/week_06/03_phase2_5_depth_model_closure.ipynb": "FDA44EF49D15EB72789003F8D9218FC945A1F8D5752098F4CF3C7D2B6FD54454",
    "src/week6_phase2_5_depth_model_closure.py": "2766ED6D8551151B29582C6B7D83C88D39367153A70B4DCFDE249410481204B3",
    "outputs/week6_02_5_depth_model_closure/phase2_5_configuration.json": "CCCB6E47279AE2D6A6DBEF9906450F5404AD80207DD0E7C84DCC82C4E8BE7AED",
    "outputs/week6_02_5_depth_model_closure/stable_depth_B_loo_predictions.csv": "398A5C355E12B0B9FFE276578E9242DC5655CFC01D529DE6FF5FC0130BC0B59A",
    "outputs/week6_02_5_depth_model_closure/stable_depth_C_loo_predictions.csv": "62D55CC6EE844354E7A62C29358DAC68EC9EAD74D6A768810382752C8FB6272B",
    "outputs/week6_02_5_depth_model_closure/summary.json": "3093361B89745ACF7F62271B0576DAEAD17A91E0225B3A4C4B55B9DF059D678F",
}

ORIGINAL_BASELINE = {
    "branch": "main",
    "head": "6fd6be57e5341e083a7023a3ae29e65b7b326bbd",
    "status_short": [
        " M outputs/week2_acquisition_comparison/week2_slide_notes.md",
        "?? docs/",
        "?? outputs/week1_active_level_set_progress.pptx",
        "?? outputs/week2_active_level_set_progress_v2.pptx",
        "?? outputs/week3_active_level_set_progress.pptx",
        "?? outputs/week3_active_level_set_progress_v2.pptx",
    ],
    "protected_hashes": {
        "docs/deep-research-report.md": "A714E0C2249A134287B76A86FC8D660A075C69184A5CAB851A3C1F52412E321C",
        "outputs/week1_active_level_set_progress.pptx": "BDD1F515EAAB313E5371CBE5E2C0B7FB3E87713037A21337DD7D078406C23577",
        "outputs/week2_acquisition_comparison/week2_slide_notes.md": "9F00ECE946170F936E5EFFFA019CDB4C3B2DBCC93037155CDFCCFCA716E2E99C",
        "outputs/week2_active_level_set_progress_v2.pptx": "92A760D21A1C9B9E07F15724D2CEDD225A19B05439AF8ECA6273AC4212B913AB",
        "outputs/week3_active_level_set_progress.pptx": "F129A4F5310B808D23F810B1E4CBFB8BE2039A5DDFE408D9B26DE55E7C9CFCBD",
        "outputs/week3_active_level_set_progress_v2.pptx": "AEC8EFE32B358D2F6BBD3C3610FC9D76FF8B45D74CDDBDD0074C261E127AE09E",
    },
}


RUNTIME_EVENTS: list[dict[str, Any]] = []
PRIOR_COMPLETE_RUNTIME_PROVENANCE: dict[str, Any] | None = None
PRIOR_COMPLETE_COVERAGE_REPAIR_PROVENANCE: dict[str, Any] | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def array_sha256(values: np.ndarray) -> str:
    array = np.ascontiguousarray(values)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("utf-8"))
    digest.update(str(array.shape).encode("utf-8"))
    digest.update(array.tobytes())
    return digest.hexdigest().upper()


def deterministic_seed(*parts: Any) -> int:
    payload = "|".join(map(str, (BASE_RANDOM_SEED, *parts))).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "big")


def json_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def write_csv(frame: pd.DataFrame, filename: str) -> Path:
    path = OUTPUT_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False, lineterminator="\n")
    os.replace(temporary, path)
    return path


def write_json(payload: dict[str, Any], filename: str) -> Path:
    path = OUTPUT_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(json_safe(payload), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    return path


def write_text(text: str, filename: str) -> Path:
    path = OUTPUT_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text.rstrip() + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return path


def run_git(
    *arguments: str, workdir: Path = ROOT, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=workdir,
        text=True,
        capture_output=True,
        check=check,
    )


def verify_original_worktree() -> tuple[bool, str]:
    if not ORIGINAL_WORKTREE.exists():
        return False, f"missing original worktree: {ORIGINAL_WORKTREE}"
    branch = run_git("branch", "--show-current", workdir=ORIGINAL_WORKTREE).stdout.strip()
    head = run_git("rev-parse", "HEAD", workdir=ORIGINAL_WORKTREE).stdout.strip()
    status = run_git("status", "--short", workdir=ORIGINAL_WORKTREE).stdout.splitlines()
    hash_mismatches: list[str] = []
    for relative, expected in ORIGINAL_BASELINE["protected_hashes"].items():
        path = ORIGINAL_WORKTREE / relative
        if not path.exists():
            hash_mismatches.append(f"{relative}:missing")
        elif sha256(path) != expected:
            hash_mismatches.append(f"{relative}:hash")
    passed = bool(
        branch == ORIGINAL_BASELINE["branch"]
        and head == ORIGINAL_BASELINE["head"]
        and status == ORIGINAL_BASELINE["status_short"]
        and not hash_mismatches
    )
    detail = (
        f"branch={branch}; head={head}; status_lines={len(status)}; "
        f"protected_hash_mismatches={hash_mismatches}"
    )
    return passed, detail


def current_repository_state() -> dict[str, Any]:
    return {
        "repo_root": run_git("rev-parse", "--show-toplevel").stdout.strip(),
        "branch": run_git("branch", "--show-current").stdout.strip(),
        "head": run_git("rev-parse", "HEAD").stdout.strip(),
        "status_short": run_git("status", "--short").stdout.splitlines(),
    }


def phase3_configuration() -> dict[str, Any]:
    return {
        "created_at_utc": utc_now(),
        "phase": "Week 6 Phase 3 model-and-target robustness",
        "starting_head": STARTING_HEAD,
        "required_branch": EXPECTED_BRANCH,
        "phase1_input": str(phase2.PHASE1_INPUT.relative_to(ROOT)),
        "phase1_revision": EXPECTED_PHASE1_REVISION,
        "phase1_ledger_sha256": EXPECTED_PHASE1_LEDGER_SHA256,
        "phase1_aggregate_sha256": EXPECTED_PHASE1_AGGREGATE_SHA256,
        "features": FEATURE_COLUMNS,
        "target_source_columns_m": TARGET_SOURCE_COLUMNS,
        "target_conversion": "y_um = y_m * 1e6",
        "target_populations": {
            "width": {
                "size": 241,
                "definition": "all validated Phase 1 simulations",
                "excluded_ids": [],
            },
            "length": {
                "size": 241,
                "definition": "all validated Phase 1 simulations",
                "excluded_ids": [],
            },
            "depth": {
                "size": 230,
                "definition": "exact stable-window population fixed in Phase 2.5",
                "excluded_ids": DEPTH_EXCLUSIONS,
            },
        },
        "outer_cross_validation": {
            "method": "exact simulation-level leave-one-out",
            "fold_order": "ascending numeric_simulation_id",
            "x_preprocessing": "fold-local StandardScaler fit on outer training X only",
            "y_preprocessing": "fold-local scaling fit on outer training y only where used",
            "heldout_target_access": "prohibited for preprocessing, tuning, fitting, and selection",
            "deterministic_seed": BASE_RANDOM_SEED,
        },
        "phase3a": {
            "models": [
                "training_mean",
                "linear_ridge",
                "polynomial_ridge_degree2",
                CURRENT_GP_CONFIG_NAME,
            ],
            "ridge_alpha_grid": list(RIDGE_ALPHA_GRID),
            "ridge_alpha_grid_scale": "log10 integer powers from 1e-6 through 1e6",
            "inner_cv": {
                "folds": RIDGE_INNER_FOLDS,
                "shuffle": True,
                "selection_metric": "mean inner validation RMSE in micrometres",
                "preprocessing": "fit independently inside every inner training fold",
            },
            "polynomial_degree": 2,
            "polynomial_include_bias": False,
            "paired_bootstrap_resamples": PAIRED_BOOTSTRAP_RESAMPLES,
        },
        "phase3b": {
            "gp_configurations": [asdict(item) for item in GP_CONFIGURATIONS],
            "kernel_construction": (
                "ConstantKernel * isotropic base kernel, optionally + WhiteKernel"
            ),
            "constant_initial": CONSTANT_INITIAL,
            "constant_bounds": list(CONSTANT_BOUNDS),
            "length_scale_initial": LENGTH_SCALE_INITIAL,
            "length_scale_bounds": list(LENGTH_SCALE_BOUNDS),
            "white_initial_normalized_variance": WHITE_INITIAL,
            "white_bounds_normalized_variance": list(WHITE_BOUNDS),
            "optimizer": "fmin_l_bfgs_b (L-BFGS-B)",
            "n_restarts_optimizer": N_RESTARTS_OPTIMIZER,
            "normalize_y": False,
            "paired_bootstrap_resamples": PAIRED_BOOTSTRAP_RESAMPLES,
            "ard": False,
            "constantkernel_explanation": (
                "ConstantKernel multiplies the base covariance and controls "
                "vertical signal-amplitude variance; it does not add a constant mean."
            ),
        },
        "phase3c": {
            "definitions": [asdict(item) for item in TARGET_DEFINITIONS],
            "sentinel_threshold": SENTINEL_THRESHOLD,
            "controlled_window_minimum_rows": MIN_CONTROLLED_WINDOW_ROWS,
            "minimum_row_rule": (
                "Preserve Phase 1: if the time-fraction window has fewer than "
                "50 valid rows, use the final min(50, available) valid rows "
                "not later than that definition's cutoff."
            ),
            "t5_rule": (
                "Use exactly the final 50 valid non-sentinel melt-present rows "
                "when available; otherwise use all available rows and flag the count."
            ),
            "kernel_selection": (
                "one provisional GP configuration per response selected from "
                "Phase 3B, then held fixed across T0-T5"
            ),
        },
        "paired_bootstrap": {
            "resamples": PAIRED_BOOTSTRAP_RESAMPLES,
            "confidence": 0.95,
            "paired_on": "heldout_simulation_id",
            "quantiles": list(BOOTSTRAP_QUANTILES),
        },
        "nrmse_definition": "RMSE divided by observed target range",
        "strict_scope_exclusions": [
            "ARD",
            "feature importance",
            "permutation importance",
            "partial dependence",
            "Sobol analysis",
            "causal feature-effect claims",
            "kinetic energy",
            "total vertical height",
            "normalized first-Conduction timestep",
            "new labels",
            "active learning",
            "level-set estimation",
            "GP classification",
            "Week 5 modification",
            "Phase 4 work",
        ],
    }


def scientific_config_fingerprint() -> str:
    payload = phase3_configuration()
    payload.pop("created_at_utc", None)
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest().upper()


def verify_required_inputs() -> tuple[pd.DataFrame, dict[str, Any]]:
    if not PREFLIGHT_PATH.exists():
        raise RuntimeError("Phase 3 preflight snapshot is missing")
    repository = current_repository_state()
    if Path(repository["repo_root"]).resolve() != ROOT.resolve():
        raise RuntimeError(f"Unexpected repository root: {repository['repo_root']}")
    if repository["branch"] != EXPECTED_BRANCH:
        raise RuntimeError(
            f"Phase 3 must run on {EXPECTED_BRANCH}, got {repository['branch']}"
        )
    if repository["head"] != STARTING_HEAD:
        raise RuntimeError(
            "A commit occurred after the Phase 3 branch was created; "
            f"expected HEAD {STARTING_HEAD}, got {repository['head']}"
        )

    artifact_rows: list[dict[str, Any]] = []
    for relative, expected_hash in EXPECTED_CORE_ARTIFACT_HASHES.items():
        path = ROOT / relative
        if not path.exists():
            raise FileNotFoundError(f"Required historical artifact missing: {relative}")
        observed_hash = sha256(path)
        if observed_hash != expected_hash:
            raise RuntimeError(
                f"Protected historical artifact changed: {relative}; "
                f"expected {expected_hash}, got {observed_hash}"
            )
        artifact_rows.append(
            {
                "path": relative,
                "expected_sha256": expected_hash,
                "observed_sha256": observed_hash,
                "bytes": path.stat().st_size,
            }
        )

    aggregate_hash, aggregate_file_count = phase2.phase1_aggregate_sha256()
    if aggregate_hash != EXPECTED_PHASE1_AGGREGATE_SHA256:
        raise RuntimeError(
            "Phase 1 protected aggregate changed: "
            f"expected {EXPECTED_PHASE1_AGGREGATE_SHA256}, got {aggregate_hash}"
        )
    ledger = phase2.load_phase1_input()
    if list(phase2.FEATURE_COLUMNS) != FEATURE_COLUMNS:
        raise RuntimeError("Validated Phase 2 feature list changed")
    if set(ledger["huggingface_revision"].astype(str)) != {
        EXPECTED_PHASE1_REVISION
    }:
        raise RuntimeError("Phase 1 Hugging Face revision differs")

    phase2_decisions = pd.read_csv(
        ROOT
        / "outputs"
        / "week6_02_gp_response_noise_comparison"
        / "preferred_method_selection.csv"
    ).set_index("target")
    if (
        phase2_decisions.loc["width", "preferred_method"] != "B_learned_nugget"
        or phase2_decisions.loc["length", "preferred_method"]
        != "B_learned_nugget"
    ):
        raise RuntimeError("Phase 2 width/length decisions differ from expected")
    phase25_summary = json.loads(
        (
            ROOT
            / "outputs"
            / "week6_02_5_depth_model_closure"
            / "summary.json"
        ).read_text(encoding="utf-8")
    )
    phase25_validation = pd.read_csv(
        ROOT
        / "outputs"
        / "week6_02_5_depth_model_closure"
        / "validation_results.csv"
    )
    if phase25_summary["decision"]["decision_code"] != "B_preferred_for_depth":
        raise RuntimeError("Phase 2.5 depth decision differs from expected")
    if not (
        len(phase25_validation) == 30
        and (phase25_validation["status"] == "PASS").all()
    ):
        raise RuntimeError("Phase 2.5 validation is not the expected 30/30 PASS")

    original_passed, original_detail = verify_original_worktree()
    if not original_passed:
        raise RuntimeError(f"Original dirty worktree changed: {original_detail}")

    provenance = {
        "verified_at_utc": utc_now(),
        "repository": repository,
        "historical_artifacts": artifact_rows,
        "phase1_aggregate_sha256": aggregate_hash,
        "phase1_aggregate_file_count": aggregate_file_count,
        "phase1_rows": len(ledger),
        "phase1_unique_simulation_ids": int(ledger["simulation_id"].nunique()),
        "phase1_revision": EXPECTED_PHASE1_REVISION,
        "phase2_width_decision": str(
            phase2_decisions.loc["width", "preferred_method"]
        ),
        "phase2_length_decision": str(
            phase2_decisions.loc["length", "preferred_method"]
        ),
        "phase2_5_depth_decision": phase25_summary["decision"]["decision_code"],
        "phase2_5_validation": "30/30 PASS",
        "original_worktree_unchanged": True,
        "original_worktree_detail": original_detail,
    }
    return ledger, provenance


def build_populations(
    ledger: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    sorted_ledger = ledger.sort_values("numeric_simulation_id").reset_index(drop=True)
    populations = {
        "width": sorted_ledger.copy(),
        "length": sorted_ledger.copy(),
        "depth": sorted_ledger.loc[
            ~sorted_ledger["simulation_id"].isin(DEPTH_EXCLUSIONS)
        ].reset_index(drop=True),
    }
    unstable_ids = set(
        sorted_ledger.loc[
            sorted_ledger["flag_primary_window_unstable"].astype(bool),
            "simulation_id",
        ].astype(str)
    )
    if unstable_ids != set(DEPTH_EXCLUSIONS):
        raise RuntimeError(
            "Phase 1 unstable IDs differ from exact Phase 2.5 exclusions"
        )

    rows: list[dict[str, Any]] = []
    for target in TARGET_KEYS:
        population = populations[target]
        expected_size = EXPECTED_POPULATION_SIZES[target]
        if len(population) != expected_size:
            raise RuntimeError(
                f"{target} population: expected {expected_size}, got {len(population)}"
            )
        if population["simulation_id"].duplicated().any():
            raise RuntimeError(f"{target} population has duplicate simulation IDs")
        target_um = population[f"{target}_target_um"].to_numpy(float)
        if not np.isfinite(target_um).all() or (target_um <= 0).any():
            raise RuntimeError(f"{target} target is not finite and positive")
        excluded = sorted(
            set(sorted_ledger["simulation_id"]) - set(population["simulation_id"])
        )
        expected_excluded = DEPTH_EXCLUSIONS if target == "depth" else []
        if excluded != expected_excluded:
            raise RuntimeError(f"{target} exclusions differ: {excluded}")
        rows.append(
            {
                "target": target,
                "target_label": TARGET_LABELS[target],
                "population_size": len(population),
                "first_simulation_id": population["simulation_id"].iloc[0],
                "last_simulation_id": population["simulation_id"].iloc[-1],
                "excluded_count": len(excluded),
                "excluded_simulation_ids": json_compact(excluded),
                "feature_columns": json_compact(FEATURE_COLUMNS),
                "target_source_column_m": TARGET_SOURCE_COLUMNS[target],
                "target_min_um": float(target_um.min()),
                "target_median_um": float(np.median(target_um)),
                "target_max_um": float(target_um.max()),
                "target_range_um": float(target_um.max() - target_um.min()),
                "phase1_unstable_rows_in_population": int(
                    population["flag_primary_window_unstable"].astype(bool).sum()
                ),
                "fold_order": "ascending numeric_simulation_id",
            }
        )
    return populations, pd.DataFrame(rows)


def _window_cv_trend(values: np.ndarray) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    if (
        len(values) < 2
        or not np.isfinite(values).all()
        or math.isclose(float(values.mean()), 0.0)
    ):
        return np.nan, np.nan
    cv = float(values.std(ddof=0) / values.mean())
    trend = float(
        np.polyfit(np.linspace(0.0, 1.0, len(values)), values, 1)[0]
        / values.mean()
    )
    return cv, trend


def _raw_monitor_arrays(
    simulation_id: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any], dict[str, str]]:
    simulation_dir = phase1.FINAL_DATA / simulation_id
    bounds_path = simulation_dir / "monitor" / "position-bounds_melt.dat"
    time_path = simulation_dir / "monitor" / "time.dat"
    iteration_path = simulation_dir / "monitor" / "iter.dat"
    details_path = simulation_dir / "experiment_details.json"
    required = [bounds_path, time_path, iteration_path, details_path]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            f"{simulation_id}: missing raw Phase 1 monitor sources: {missing}"
        )
    bounds = np.loadtxt(bounds_path, delimiter=",", ndmin=2)
    time_values = np.loadtxt(time_path, ndmin=1)
    iterations = np.loadtxt(iteration_path, ndmin=1)
    if bounds.ndim != 2 or bounds.shape[1] != 6:
        raise RuntimeError(f"{simulation_id}: expected six melt-bound columns")
    if not (len(bounds) == len(time_values) == len(iterations)):
        raise RuntimeError(f"{simulation_id}: raw monitor rows are not aligned")
    if not np.all(np.diff(time_values) > 0):
        raise RuntimeError(f"{simulation_id}: time is not strictly increasing")
    if not np.all(np.diff(iterations) > 0):
        raise RuntimeError(f"{simulation_id}: iteration is not strictly increasing")
    details = json.loads(details_path.read_text(encoding="utf-8"))
    hashes = {
        "bounds_sha256": sha256(bounds_path),
        "time_sha256": sha256(time_path),
        "iteration_sha256": sha256(iteration_path),
        "experiment_details_sha256": sha256(details_path),
    }
    return bounds, time_values, iterations, details, hashes


def _valid_melt_rows(bounds: np.ndarray) -> tuple[np.ndarray, dict[str, int]]:
    finite = np.isfinite(bounds).all(axis=1)
    not_sentinel = (np.abs(bounds) < SENTINEL_THRESHOLD).all(axis=1)
    ordered = (
        (bounds[:, 1] >= bounds[:, 0])
        & (bounds[:, 3] >= bounds[:, 2])
        & (bounds[:, 5] >= bounds[:, 4])
    )
    valid = finite & not_sentinel & ordered
    counts = {
        "finite_row_count": int(finite.sum()),
        "sentinel_row_count": int((finite & ~not_sentinel).sum()),
        "non_finite_row_count": int((~finite).sum()),
        "unordered_row_count_after_sentinel_filter": int(
            (finite & not_sentinel & ~ordered).sum()
        ),
        "valid_melt_row_count": int(valid.sum()),
        "invalid_or_no_melt_row_count": int((~valid).sum()),
    }
    if not valid.any():
        raise RuntimeError("raw monitor has no valid melt-present rows")
    return valid, counts


def _response_series(
    bounds: np.ndarray, valid: np.ndarray
) -> dict[str, np.ndarray]:
    extents = np.full((len(bounds), 3), np.nan, dtype=float)
    extents[valid] = (
        bounds[valid][:, [1, 3, 5]] - bounds[valid][:, [0, 2, 4]]
    )
    depth = np.full(len(bounds), np.nan, dtype=float)
    depth[valid] = np.maximum(0.0, -bounds[valid, 4])
    return {
        "width": extents[:, 1],
        "length": extents[:, 0],
        "depth": depth,
    }


def _definition_indices(
    *,
    definition: TargetDefinition,
    valid: np.ndarray,
    time_values: np.ndarray,
    laser_exit_time_s: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    valid_indices = np.flatnonzero(valid)
    first_valid_time_s = float(time_values[valid_indices[0]])
    final_recorded_time_s = float(time_values[-1])
    cutoff_requested_s = np.nan
    cutoff_applied_s = np.nan
    nominal_start_s = np.nan
    minimum_row_fallback_used = False

    if definition.code == "T5":
        count = min(int(definition.final_valid_row_count or 50), len(valid_indices))
        selected_indices = valid_indices[-count:]
        fewer_than_50 = len(valid_indices) < int(
            definition.final_valid_row_count or 50
        )
    else:
        if (
            definition.window_fraction is None
            or definition.cutoff_fraction is None
        ):
            raise RuntimeError(f"Incomplete target definition: {definition}")
        cutoff_requested_s = float(
            definition.cutoff_fraction * laser_exit_time_s
        )
        cutoff_applied_s = min(final_recorded_time_s, cutoff_requested_s)
        nominal_start_s = first_valid_time_s + (
            1.0 - definition.window_fraction
        ) * (cutoff_applied_s - first_valid_time_s)
        selected_mask = (
            valid
            & (time_values >= nominal_start_s)
            & (time_values <= cutoff_applied_s)
        )
        if int(selected_mask.sum()) < MIN_CONTROLLED_WINDOW_ROWS:
            eligible = np.flatnonzero(valid & (time_values <= cutoff_applied_s))
            if not len(eligible):
                raise RuntimeError(
                    f"{definition.code}: no valid row at or before cutoff"
                )
            selected_indices = eligible[
                -min(MIN_CONTROLLED_WINDOW_ROWS, len(eligible)) :
            ]
            minimum_row_fallback_used = True
        else:
            selected_indices = np.flatnonzero(selected_mask)
        fewer_than_50 = False

    if not len(selected_indices):
        raise RuntimeError(f"{definition.code}: target window is empty")
    cutoff_90_s = 0.90 * laser_exit_time_s
    selected_times = time_values[selected_indices]
    metadata = {
        "window_observation_count": int(len(selected_indices)),
        "window_start_row_index": int(selected_indices[0]),
        "window_end_row_index": int(selected_indices[-1]),
        "window_start_time_s": float(selected_times[0]),
        "window_end_time_s": float(selected_times[-1]),
        "first_valid_time_s": first_valid_time_s,
        "final_recorded_time_s": final_recorded_time_s,
        "laser_exit_time_s": float(laser_exit_time_s),
        "requested_cutoff_time_s": cutoff_requested_s,
        "applied_cutoff_time_s": cutoff_applied_s,
        "nominal_window_start_time_s": nominal_start_s,
        "recording_ended_before_requested_cutoff": bool(
            definition.code != "T5"
            and final_recorded_time_s < cutoff_requested_s
        ),
        "minimum_50_row_fallback_used": minimum_row_fallback_used,
        "fewer_than_50_valid_rows": fewer_than_50,
        "selected_rows_after_90pct_cutoff": int(
            np.sum(selected_times > cutoff_90_s)
        ),
        "selected_rows_after_full_domain_exit": int(
            np.sum(selected_times > laser_exit_time_s)
        ),
        "selected_row_indices_sha256": array_sha256(
            selected_indices.astype(np.int64)
        ),
        "controlled_cutoff_respected": bool(
            definition.code == "T5"
            or float(selected_times.max()) <= cutoff_applied_s + 1e-15
        ),
    }
    return selected_indices, metadata


def build_target_definition_tables(
    ledger: pd.DataFrame,
    populations: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    started = time.perf_counter()
    model_population_ids = {
        target: set(frame["simulation_id"].astype(str))
        for target, frame in populations.items()
    }
    value_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    sorted_ledger = ledger.sort_values("numeric_simulation_id").reset_index(drop=True)

    for position, ledger_row in sorted_ledger.iterrows():
        simulation_id = str(ledger_row["simulation_id"])
        bounds, time_values, iterations, details, hashes = _raw_monitor_arrays(
            simulation_id
        )
        valid, raw_counts = _valid_melt_rows(bounds)
        responses = _response_series(bounds, valid)
        velocity = float(
            details["lasers"]["single_gaussian_laser"]["physics"]["motion"][
                "velocity"
            ][0]
        )
        domain_max_x = float(details["domain"]["domain_max"][0])
        if not np.isfinite(velocity) or velocity <= 0:
            raise RuntimeError(f"{simulation_id}: invalid positive-X velocity")
        if not np.isfinite(domain_max_x) or domain_max_x <= 0:
            raise RuntimeError(f"{simulation_id}: invalid positive-X domain maximum")
        laser_exit_time_s = domain_max_x / velocity

        for definition in TARGET_DEFINITIONS:
            selected_indices, window = _definition_indices(
                definition=definition,
                valid=valid,
                time_values=time_values,
                laser_exit_time_s=laser_exit_time_s,
            )
            selected_iteration = iterations[selected_indices]
            trace_rows.append(
                {
                    "simulation_id": simulation_id,
                    "numeric_simulation_id": int(
                        ledger_row["numeric_simulation_id"]
                    ),
                    "target_definition": definition.code,
                    "target_definition_label": definition.label,
                    "aggregation": definition.aggregation,
                    "window_fraction": definition.window_fraction,
                    "cutoff_fraction_of_positive_x_domain": (
                        definition.cutoff_fraction
                    ),
                    "source_bounds_path": str(
                        (
                            phase1.FINAL_DATA
                            / simulation_id
                            / "monitor"
                            / "position-bounds_melt.dat"
                        ).relative_to(ROOT)
                    ).replace("\\", "/"),
                    "source_time_path": str(
                        (
                            phase1.FINAL_DATA
                            / simulation_id
                            / "monitor"
                            / "time.dat"
                        ).relative_to(ROOT)
                    ).replace("\\", "/"),
                    "source_iteration_path": str(
                        (
                            phase1.FINAL_DATA
                            / simulation_id
                            / "monitor"
                            / "iter.dat"
                        ).relative_to(ROOT)
                    ).replace("\\", "/"),
                    **hashes,
                    **raw_counts,
                    **window,
                    "window_start_iteration": float(selected_iteration[0]),
                    "window_end_iteration": float(selected_iteration[-1]),
                    "valid_row_indices_sha256": array_sha256(
                        np.flatnonzero(valid).astype(np.int64)
                    ),
                    "sentinel_rows_excluded": True,
                    "aligned_bounds_time_iteration": True,
                    "t5_exact_final_50_rule": bool(
                        definition.code != "T5"
                        or len(selected_indices)
                        == min(50, int(valid.sum()))
                    ),
                }
            )
            for target in TARGET_KEYS:
                values = responses[target][selected_indices]
                if not np.isfinite(values).all():
                    raise RuntimeError(
                        f"{simulation_id}/{definition.code}/{target}: "
                        "non-finite selected response"
                    )
                target_value_m = (
                    float(np.median(values))
                    if definition.aggregation == "median"
                    else float(np.mean(values))
                )
                cv, trend = _window_cv_trend(values)
                value_rows.append(
                    {
                        "simulation_id": simulation_id,
                        "numeric_simulation_id": int(
                            ledger_row["numeric_simulation_id"]
                        ),
                        "target": target,
                        "target_label": TARGET_LABELS[target],
                        "target_definition": definition.code,
                        "target_definition_label": definition.label,
                        "aggregation": definition.aggregation,
                        "available": bool(np.isfinite(target_value_m)),
                        "target_value_m": target_value_m,
                        "target_value_um": target_value_m * 1e6,
                        "window_observation_count": len(selected_indices),
                        "within_window_cv": cv,
                        "within_window_relative_trend": trend,
                        "within_window_absolute_relative_trend": (
                            abs(trend) if np.isfinite(trend) else np.nan
                        ),
                        "window_unstable": bool(
                            np.isfinite(cv)
                            and cv > TARGET_UNSTABLE_CV_THRESHOLDS[target]
                        ),
                        "instability_cv_threshold": (
                            TARGET_UNSTABLE_CV_THRESHOLDS[target]
                        ),
                        "in_target_modelling_population": bool(
                            simulation_id in model_population_ids[target]
                        ),
                        "minimum_50_row_fallback_used": window[
                            "minimum_50_row_fallback_used"
                        ],
                        "fewer_than_50_valid_rows": window[
                            "fewer_than_50_valid_rows"
                        ],
                        "selected_rows_after_90pct_cutoff": window[
                            "selected_rows_after_90pct_cutoff"
                        ],
                        "selected_rows_after_full_domain_exit": window[
                            "selected_rows_after_full_domain_exit"
                        ],
                        "sentinel_rows_excluded": True,
                        "P": float(ledger_row["P"]),
                        "VX": float(ledger_row["VX"]),
                        "LS": float(ledger_row["LS"]),
                        "ST": float(ledger_row["ST"]),
                    }
                )
        if (position + 1) % 25 == 0 or position + 1 == len(sorted_ledger):
            print(
                "target reconstruction: "
                f"{position + 1}/{len(sorted_ledger)} simulations",
                flush=True,
            )

    values = pd.DataFrame(value_rows).sort_values(
        ["target", "target_definition", "numeric_simulation_id"]
    )
    trace = pd.DataFrame(trace_rows).sort_values(
        ["target_definition", "numeric_simulation_id"]
    )
    expected_value_rows = len(sorted_ledger) * len(TARGET_KEYS) * len(
        TARGET_DEFINITIONS
    )
    expected_trace_rows = len(sorted_ledger) * len(TARGET_DEFINITIONS)
    if len(values) != expected_value_rows:
        raise RuntimeError(
            f"Expected {expected_value_rows} target rows, got {len(values)}"
        )
    if len(trace) != expected_trace_rows:
        raise RuntimeError(
            f"Expected {expected_trace_rows} trace rows, got {len(trace)}"
        )
    if values.duplicated(
        ["target", "target_definition", "simulation_id"]
    ).any():
        raise RuntimeError("Target-definition table has duplicate rows")
    if trace.duplicated(["target_definition", "simulation_id"]).any():
        raise RuntimeError("Target traceability table has duplicate rows")

    # T0 must reproduce the immutable Phase 1 target values and selected rows.
    for target in TARGET_KEYS:
        t0 = (
            values.loc[
                (values["target"] == target)
                & (values["target_definition"] == "T0")
            ]
            .sort_values("numeric_simulation_id")
            .reset_index(drop=True)
        )
        expected_m = sorted_ledger[TARGET_SOURCE_COLUMNS[target]].to_numpy(float)
        if not np.allclose(
            t0["target_value_m"].to_numpy(float),
            expected_m,
            rtol=0.0,
            atol=5e-15,
        ):
            maximum = float(
                np.max(
                    np.abs(
                        t0["target_value_m"].to_numpy(float) - expected_m
                    )
                )
            )
            raise RuntimeError(
                f"T0 {target} does not reproduce Phase 1; max difference={maximum}"
            )
    t0_trace = trace.loc[trace["target_definition"] == "T0"].sort_values(
        "numeric_simulation_id"
    )
    if not np.array_equal(
        t0_trace["window_start_row_index"].to_numpy(int),
        sorted_ledger["selected_window_start_row_index"].to_numpy(int),
    ):
        raise RuntimeError("T0 start rows do not reproduce Phase 1")
    if not np.array_equal(
        t0_trace["window_end_row_index"].to_numpy(int),
        sorted_ledger["selected_window_end_row_index"].to_numpy(int),
    ):
        raise RuntimeError("T0 end rows do not reproduce Phase 1")

    RUNTIME_EVENTS.append(
        {
            "stage": "target_definition_reconstruction",
            "cache_reused": False,
            "wall_runtime_seconds": time.perf_counter() - started,
            "simulation_count": len(sorted_ledger),
            "target_value_rows": len(values),
            "traceability_rows": len(trace),
        }
    )
    return values.reset_index(drop=True), trace.reset_index(drop=True)


def _distribution_quantiles(
    values: pd.Series, prefix: str
) -> dict[str, float]:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return {
            f"{prefix}_min": np.nan,
            f"{prefix}_q25": np.nan,
            f"{prefix}_median": np.nan,
            f"{prefix}_q75": np.nan,
            f"{prefix}_q95": np.nan,
            f"{prefix}_max": np.nan,
        }
    return {
        f"{prefix}_min": float(numeric.min()),
        f"{prefix}_q25": float(numeric.quantile(0.25)),
        f"{prefix}_median": float(numeric.median()),
        f"{prefix}_q75": float(numeric.quantile(0.75)),
        f"{prefix}_q95": float(numeric.quantile(0.95)),
        f"{prefix}_max": float(numeric.max()),
    }


def build_target_distribution_summary(
    target_table: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    modelling = target_table.loc[
        target_table["in_target_modelling_population"].astype(bool)
    ]
    for (target, definition), subset in modelling.groupby(
        ["target", "target_definition"], sort=True
    ):
        available = subset.loc[subset["available"].astype(bool)]
        target_values = available["target_value_um"]
        rows.append(
            {
                "target": target,
                "target_label": TARGET_LABELS[target],
                "target_definition": definition,
                "target_definition_label": TARGET_DEFINITION_BY_CODE[
                    definition
                ].label,
                "population_size": len(subset),
                "availability_count": len(available),
                "availability_fraction": len(available) / len(subset),
                "target_min_um": float(target_values.min()),
                "target_median_um": float(target_values.median()),
                "target_max_um": float(target_values.max()),
                "target_mean_um": float(target_values.mean()),
                "target_std_um": float(target_values.std(ddof=0)),
                **_distribution_quantiles(
                    subset["window_observation_count"], "window_count"
                ),
                **_distribution_quantiles(
                    subset["within_window_cv"], "within_window_cv"
                ),
                **_distribution_quantiles(
                    subset["within_window_relative_trend"],
                    "within_window_relative_trend",
                ),
                **_distribution_quantiles(
                    subset["within_window_absolute_relative_trend"],
                    "within_window_absolute_relative_trend",
                ),
                "fraction_unstable_windows": float(
                    subset["window_unstable"].astype(bool).mean()
                ),
                "minimum_50_row_fallback_count": int(
                    subset["minimum_50_row_fallback_used"].astype(bool).sum()
                ),
                "fewer_than_50_valid_rows_count": int(
                    subset["fewer_than_50_valid_rows"].astype(bool).sum()
                ),
                "simulations_with_rows_after_90pct_cutoff": int(
                    subset["selected_rows_after_90pct_cutoff"].gt(0).sum()
                ),
                "simulations_with_rows_after_full_domain_exit": int(
                    subset["selected_rows_after_full_domain_exit"].gt(0).sum()
                ),
            }
        )
    result = pd.DataFrame(rows).sort_values(
        ["target", "target_definition"]
    )
    if len(result) != len(TARGET_KEYS) * len(TARGET_DEFINITIONS):
        raise RuntimeError("Target distribution summary is incomplete")
    return result.reset_index(drop=True)


def make_gp_kernel(configuration: GPConfiguration) -> Any:
    amplitude = ConstantKernel(
        constant_value=CONSTANT_INITIAL,
        constant_value_bounds=CONSTANT_BOUNDS,
    )
    if configuration.kernel_family == "RBF":
        base = RBF(
            length_scale=LENGTH_SCALE_INITIAL,
            length_scale_bounds=LENGTH_SCALE_BOUNDS,
        )
    elif configuration.kernel_family == "Matern":
        if configuration.matern_nu not in (1.5, 2.5):
            raise ValueError(f"Unsupported Matérn nu: {configuration.matern_nu}")
        base = Matern(
            length_scale=LENGTH_SCALE_INITIAL,
            length_scale_bounds=LENGTH_SCALE_BOUNDS,
            nu=float(configuration.matern_nu),
        )
    else:
        raise ValueError(f"Unsupported kernel family: {configuration.kernel_family}")
    kernel: Any = amplitude * base
    if configuration.learned_nugget:
        kernel += WhiteKernel(
            noise_level=WHITE_INITIAL,
            noise_level_bounds=WHITE_BOUNDS,
        )
    return kernel


def optimized_gp_components(
    kernel: Any, configuration: GPConfiguration
) -> tuple[float, float, float]:
    if configuration.learned_nugget:
        signal_kernel = kernel.k1
        noise_variance = float(kernel.k2.noise_level)
    else:
        signal_kernel = kernel
        noise_variance = np.nan
    signal_variance = float(signal_kernel.k1.constant_value)
    length_scale = float(np.asarray(signal_kernel.k2.length_scale).item())
    return signal_variance, length_scale, noise_variance


def bound_hit(
    value: float, bounds: tuple[float, float]
) -> tuple[bool, str]:
    if not np.isfinite(value):
        return False, ""
    lower, upper = bounds
    if value <= lower * (1.0 + BOUND_TOLERANCE):
        return True, "lower"
    if value >= upper * (1.0 - BOUND_TOLERANCE):
        return True, "upper"
    return False, ""


def gaussian_nlpd(
    observed: float | np.ndarray,
    predicted: float | np.ndarray,
    variance: float | np.ndarray,
) -> np.ndarray:
    observed_array = np.asarray(observed, dtype=float)
    predicted_array = np.asarray(predicted, dtype=float)
    variance_array = np.maximum(np.asarray(variance, dtype=float), 1e-18)
    return (
        0.5 * np.log(2.0 * np.pi * variance_array)
        + 0.5 * (observed_array - predicted_array) ** 2 / variance_array
    )


def _interval(mean: float, std: float) -> tuple[float, float]:
    return mean - 1.96 * std, mean + 1.96 * std


def _gp_run_fingerprint(
    modelling_table: pd.DataFrame,
    *,
    target: str,
    target_definition: str,
    analysis_label: str,
    configuration: GPConfiguration,
    n_restarts_optimizer: int,
) -> str:
    payload = {
        "phase3_scientific_config": scientific_config_fingerprint(),
        "analysis_label": analysis_label,
        "target": target,
        "target_definition": target_definition,
        "configuration": asdict(configuration),
        "n_restarts_optimizer": n_restarts_optimizer,
        "simulation_ids": modelling_table["simulation_id"].astype(str).tolist(),
        "numeric_ids": modelling_table["numeric_simulation_id"].astype(int).tolist(),
        "target_values_sha256": array_sha256(
            modelling_table["target_value_um"].to_numpy(float)
        ),
        "features_sha256": array_sha256(
            modelling_table[FEATURE_COLUMNS].to_numpy(float)
        ),
    }
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest().upper()


def _fit_gp_fold(
    *,
    X: np.ndarray,
    y_um: np.ndarray,
    simulation_ids: np.ndarray,
    numeric_ids: np.ndarray,
    target: str,
    target_definition: str,
    analysis_label: str,
    configuration: GPConfiguration,
    fold_index: int,
    run_fingerprint: str,
    dataset_target_median_um: float,
    n_restarts_optimizer: int,
) -> dict[str, Any]:
    n = len(y_um)
    training_mask = np.ones(n, dtype=bool)
    training_mask[fold_index] = False
    train_indices = np.flatnonzero(training_mask)
    X_train = X[training_mask]
    X_test = X[[fold_index]]
    y_train = y_um[training_mask]
    y_test = float(y_um[fold_index])

    x_scaler = StandardScaler()
    X_train_scaled = x_scaler.fit_transform(X_train)
    X_test_scaled = x_scaler.transform(X_test)
    y_mean_um = float(y_train.mean())
    y_std_um = float(y_train.std(ddof=0))
    if not np.isfinite(y_std_um) or y_std_um <= 0:
        raise RuntimeError(
            f"{target}/{target_definition}/{configuration.name}/fold "
            f"{fold_index}: invalid training target scale"
        )
    y_train_scaled = (y_train - y_mean_um) / y_std_um
    fold_seed = deterministic_seed(
        "gp-loo",
        analysis_label,
        target,
        target_definition,
        configuration.name,
        fold_index,
    )
    model = GaussianProcessRegressor(
        kernel=make_gp_kernel(configuration),
        alpha=configuration.numerical_alpha_normalized,
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
    (
        signal_variance_normalized,
        length_scale,
        noise_variance_normalized,
    ) = optimized_gp_components(model.kernel_, configuration)
    if configuration.learned_nugget:
        total_variance_normalized = returned_variance_normalized
        latent_variance_normalized = max(
            total_variance_normalized - noise_variance_normalized, 1e-18
        )
        total_std_um = math.sqrt(total_variance_normalized) * y_std_um
        latent_std_um = math.sqrt(latent_variance_normalized) * y_std_um
        noise_variance_um2 = noise_variance_normalized * y_std_um**2
        noise_std_um = math.sqrt(noise_variance_normalized) * y_std_um
        evaluation_std_um = total_std_um
        evaluation_variance_definition = (
            "total predictive variance including learned WhiteKernel nugget"
        )
    else:
        latent_variance_normalized = returned_variance_normalized
        latent_std_um = math.sqrt(latent_variance_normalized) * y_std_um
        total_std_um = np.nan
        noise_variance_um2 = np.nan
        noise_std_um = np.nan
        evaluation_std_um = latent_std_um
        evaluation_variance_definition = (
            "latent predictive variance; numerical jitter excluded"
        )

    residual_um = y_test - prediction_um
    latent_lower, latent_upper = _interval(prediction_um, latent_std_um)
    if np.isfinite(total_std_um):
        total_lower, total_upper = _interval(prediction_um, total_std_um)
    else:
        total_lower, total_upper = np.nan, np.nan
    constant_hit, constant_side = bound_hit(
        signal_variance_normalized, CONSTANT_BOUNDS
    )
    length_hit, length_side = bound_hit(length_scale, LENGTH_SCALE_BOUNDS)
    noise_hit, noise_side = bound_hit(
        noise_variance_normalized, WHITE_BOUNDS
    )
    warning_messages = [
        f"{type(item.message).__name__}: {item.message}" for item in caught
    ]
    convergence_warning_count = sum(
        isinstance(item.message, ConvergenceWarning) for item in caught
    )
    training_ids = simulation_ids[training_mask].astype(str).tolist()
    return {
        "analysis_label": analysis_label,
        "phase": "Phase 3B" if target_definition == "T0" else "Phase 3C",
        "phase3_config_fingerprint": scientific_config_fingerprint(),
        "run_fingerprint": run_fingerprint,
        "target": target,
        "target_label": TARGET_LABELS[target],
        "target_definition": target_definition,
        "gp_configuration": configuration.name,
        "gp_configuration_label": configuration.label,
        "kernel_family": configuration.kernel_family,
        "matern_nu": configuration.matern_nu,
        "learned_nugget": configuration.learned_nugget,
        "fold_index": fold_index,
        "heldout_simulation_id": str(simulation_ids[fold_index]),
        "heldout_numeric_simulation_id": int(numeric_ids[fold_index]),
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
        "evaluation_predictive_std_um": evaluation_std_um,
        "evaluation_variance_definition": evaluation_variance_definition,
        "latent_nlpd": float(
            gaussian_nlpd(y_test, prediction_um, latent_std_um**2)
        ),
        "total_nlpd": (
            float(gaussian_nlpd(y_test, prediction_um, total_std_um**2))
            if np.isfinite(total_std_um)
            else np.nan
        ),
        "evaluation_nlpd": float(
            gaussian_nlpd(y_test, prediction_um, evaluation_std_um**2)
        ),
        "latent_interval_lower_um": latent_lower,
        "latent_interval_upper_um": latent_upper,
        "total_interval_lower_um": total_lower,
        "total_interval_upper_um": total_upper,
        "latent_interval_contains_observed": bool(
            latent_lower <= y_test <= latent_upper
        ),
        "total_interval_contains_observed": (
            bool(total_lower <= y_test <= total_upper)
            if np.isfinite(total_lower)
            else np.nan
        ),
        "optimized_kernel": str(model.kernel_),
        "optimized_signal_variance_normalized": (
            signal_variance_normalized
        ),
        "optimized_length_scale": length_scale,
        "optimized_noise_variance_normalized": noise_variance_normalized,
        "optimized_noise_std_normalized": (
            math.sqrt(noise_variance_normalized)
            if np.isfinite(noise_variance_normalized)
            else np.nan
        ),
        "optimized_noise_variance_um2": noise_variance_um2,
        "optimized_noise_std_um": noise_std_um,
        "noise_std_fraction_training_target_std": (
            noise_std_um / y_std_um if np.isfinite(noise_std_um) else np.nan
        ),
        "noise_std_fraction_dataset_target_median": (
            noise_std_um / dataset_target_median_um
            if np.isfinite(noise_std_um) and dataset_target_median_um > 0
            else np.nan
        ),
        "dataset_target_median_um_reporting_only": dataset_target_median_um,
        "dataset_target_median_used_for_fitting": False,
        "numerical_alpha_normalized": (
            configuration.numerical_alpha_normalized
        ),
        "numerical_alpha_interpretation": (
            "numerical jitter only; separate from WhiteKernel nugget"
        ),
        "training_size": len(train_indices),
        "population_size": n,
        "heldout_excluded_from_training": bool(
            fold_index not in set(train_indices)
        ),
        "heldout_target_used_for_scaling": False,
        "heldout_target_used_for_fitting": False,
        "heldout_target_used_for_tuning": False,
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
        "outer_training_simulation_ids_sha256": hashlib.sha256(
            json_compact(training_ids).encode("utf-8")
        ).hexdigest().upper(),
        **{
            f"heldout_{feature}": float(X[fold_index, feature_index])
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


def _gp_checkpoint_path(
    analysis_label: str,
    target: str,
    target_definition: str,
    configuration_name: str,
) -> Path:
    safe_analysis = re.sub(r"[^a-zA-Z0-9_-]+", "_", analysis_label)
    return (
        CHECKPOINT_DIR
        / (
            f"gp__{safe_analysis}__{target}__{target_definition}__"
            f"{configuration_name}.csv"
        )
    )


def _gp_checkpoint_valid(
    frame: pd.DataFrame,
    *,
    expected_rows: int,
    target: str,
    target_definition: str,
    configuration: GPConfiguration,
    run_fingerprint: str,
) -> bool:
    required = {
        "heldout_simulation_id",
        "predicted_mean_um",
        "latent_predictive_std_um",
        "run_fingerprint",
        "target",
        "target_definition",
        "gp_configuration",
    }
    if not required.issubset(frame.columns):
        return False
    return bool(
        len(frame) == expected_rows
        and frame["heldout_simulation_id"].is_unique
        and set(frame["target"].astype(str)) == {target}
        and set(frame["target_definition"].astype(str)) == {target_definition}
        and set(frame["gp_configuration"].astype(str)) == {configuration.name}
        and set(frame["run_fingerprint"].astype(str)) == {run_fingerprint}
        and np.isfinite(frame["predicted_mean_um"].to_numpy(float)).all()
        and (
            frame["latent_predictive_std_um"].to_numpy(float) > 0
        ).all()
    )


def run_gp_loo(
    modelling_table: pd.DataFrame,
    *,
    target: str,
    target_definition: str,
    analysis_label: str,
    configuration: GPConfiguration,
    workers: int,
    force: bool,
    n_restarts_optimizer: int = N_RESTARTS_OPTIMIZER,
    use_checkpoint: bool = True,
) -> pd.DataFrame:
    required = {
        "simulation_id",
        "numeric_simulation_id",
        "target_value_um",
        *FEATURE_COLUMNS,
    }
    missing = sorted(required - set(modelling_table.columns))
    if missing:
        raise RuntimeError(f"GP modelling table missing columns: {missing}")
    table = modelling_table.sort_values("numeric_simulation_id").reset_index(
        drop=True
    )
    X = table[FEATURE_COLUMNS].to_numpy(float)
    y_um = table["target_value_um"].to_numpy(float)
    if not np.isfinite(X).all() or not np.isfinite(y_um).all():
        raise RuntimeError(f"{target}/{target_definition}: non-finite GP input")
    if table["simulation_id"].duplicated().any():
        raise RuntimeError(f"{target}/{target_definition}: duplicate simulation IDs")
    run_fingerprint = _gp_run_fingerprint(
        table,
        target=target,
        target_definition=target_definition,
        analysis_label=analysis_label,
        configuration=configuration,
        n_restarts_optimizer=n_restarts_optimizer,
    )
    checkpoint = _gp_checkpoint_path(
        analysis_label, target, target_definition, configuration.name
    )
    if use_checkpoint and not force and checkpoint.exists():
        cached = pd.read_csv(checkpoint)
        if _gp_checkpoint_valid(
            cached,
            expected_rows=len(table),
            target=target,
            target_definition=target_definition,
            configuration=configuration,
            run_fingerprint=run_fingerprint,
        ):
            print(f"checkpoint reused: {checkpoint.name}", flush=True)
            RUNTIME_EVENTS.append(
                {
                    "stage": "gp_loo",
                    "analysis_label": analysis_label,
                    "target": target,
                    "target_definition": target_definition,
                    "configuration": configuration.name,
                    "cache_reused": True,
                    "checkpoint": str(checkpoint.relative_to(ROOT)),
                    "wall_runtime_seconds": 0.0,
                    "aggregate_fold_runtime_seconds": float(
                        cached["runtime_seconds"].sum()
                    ),
                    "fold_count": len(cached),
                }
            )
            return cached.sort_values("fold_index").reset_index(drop=True)

    simulation_ids = table["simulation_id"].astype(str).to_numpy()
    numeric_ids = table["numeric_simulation_id"].to_numpy(int)
    dataset_median_um = float(np.median(y_um))
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    with threadpool_limits(limits=1):
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = {
                pool.submit(
                    _fit_gp_fold,
                    X=X,
                    y_um=y_um,
                    simulation_ids=simulation_ids,
                    numeric_ids=numeric_ids,
                    target=target,
                    target_definition=target_definition,
                    analysis_label=analysis_label,
                    configuration=configuration,
                    fold_index=fold_index,
                    run_fingerprint=run_fingerprint,
                    dataset_target_median_um=dataset_median_um,
                    n_restarts_optimizer=n_restarts_optimizer,
                ): fold_index
                for fold_index in range(len(table))
            }
            for completed, future in enumerate(as_completed(futures), start=1):
                fold_index = futures[future]
                try:
                    rows.append(future.result())
                except Exception as exc:
                    raise RuntimeError(
                        f"GP LOO failed for {analysis_label}/{target}/"
                        f"{target_definition}/{configuration.name}/fold "
                        f"{fold_index}"
                    ) from exc
                if completed % 20 == 0 or completed == len(table):
                    print(
                        f"{analysis_label} {target} {target_definition} "
                        f"{configuration.name}: {completed}/{len(table)} folds "
                        f"({time.perf_counter() - started:.1f}s)",
                        flush=True,
                    )
    wall_runtime = time.perf_counter() - started
    frame = pd.DataFrame(rows).sort_values("fold_index").reset_index(drop=True)
    if not _gp_checkpoint_valid(
        frame,
        expected_rows=len(table),
        target=target,
        target_definition=target_definition,
        configuration=configuration,
        run_fingerprint=run_fingerprint,
    ):
        raise RuntimeError(
            f"Generated GP checkpoint is invalid: {analysis_label}/{target}/"
            f"{target_definition}/{configuration.name}"
        )
    if use_checkpoint:
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        temporary = checkpoint.with_suffix(checkpoint.suffix + ".tmp")
        frame.to_csv(temporary, index=False, lineterminator="\n")
        os.replace(temporary, checkpoint)
    RUNTIME_EVENTS.append(
        {
            "stage": "gp_loo",
            "analysis_label": analysis_label,
            "target": target,
            "target_definition": target_definition,
            "configuration": configuration.name,
            "cache_reused": False,
            "checkpoint": (
                str(checkpoint.relative_to(ROOT)) if use_checkpoint else None
            ),
            "wall_runtime_seconds": wall_runtime,
            "aggregate_fold_runtime_seconds": float(
                frame["runtime_seconds"].sum()
            ),
            "fold_count": len(frame),
            "workers": max(1, workers),
        }
    )
    return frame


def population_t0_modelling_table(
    population: pd.DataFrame, target: str
) -> pd.DataFrame:
    table = population[
        ["simulation_id", "numeric_simulation_id", *FEATURE_COLUMNS]
    ].copy()
    table["target_value_um"] = population[f"{target}_target_um"].to_numpy(float)
    table["target_definition"] = "T0"
    return table


def target_definition_modelling_table(
    target_table: pd.DataFrame, target: str, definition: str
) -> pd.DataFrame:
    subset = target_table.loc[
        (target_table["target"] == target)
        & (target_table["target_definition"] == definition)
        & target_table["in_target_modelling_population"].astype(bool)
    ].copy()
    subset = subset.sort_values("numeric_simulation_id").reset_index(drop=True)
    if len(subset) != EXPECTED_POPULATION_SIZES[target]:
        raise RuntimeError(
            f"{target}/{definition}: expected "
            f"{EXPECTED_POPULATION_SIZES[target]} rows, got {len(subset)}"
        )
    if not subset["available"].astype(bool).all():
        unavailable = subset.loc[
            ~subset["available"].astype(bool), "simulation_id"
        ].tolist()
        raise RuntimeError(
            f"{target}/{definition}: target unavailable for {unavailable}"
        )
    return subset[
        [
            "simulation_id",
            "numeric_simulation_id",
            *FEATURE_COLUMNS,
            "target_value_um",
            "target_definition",
        ]
    ].copy()


def _make_ridge_regressor(model_name: str, alpha: float) -> Any:
    if model_name == "linear_ridge":
        pipeline = Pipeline(
            [
                ("scale_inputs", StandardScaler()),
                ("ridge", Ridge(alpha=alpha)),
            ]
        )
    elif model_name == "polynomial_ridge_degree2":
        pipeline = Pipeline(
            [
                ("scale_inputs", StandardScaler()),
                (
                    "polynomial_features",
                    PolynomialFeatures(degree=2, include_bias=False),
                ),
                ("scale_polynomial_features", StandardScaler()),
                ("ridge", Ridge(alpha=alpha)),
            ]
        )
    else:
        raise ValueError(f"Unknown Ridge model: {model_name}")
    return TransformedTargetRegressor(
        regressor=pipeline,
        transformer=StandardScaler(),
        check_inverse=False,
    )


def _ridge_run_fingerprint(
    modelling_table: pd.DataFrame,
    *,
    target: str,
    model_name: str,
) -> str:
    payload = {
        "phase3_scientific_config": scientific_config_fingerprint(),
        "target": target,
        "target_definition": "T0",
        "model": model_name,
        "alpha_grid": RIDGE_ALPHA_GRID,
        "inner_folds": RIDGE_INNER_FOLDS,
        "simulation_ids": modelling_table["simulation_id"].astype(str).tolist(),
        "target_values_sha256": array_sha256(
            modelling_table["target_value_um"].to_numpy(float)
        ),
        "features_sha256": array_sha256(
            modelling_table[FEATURE_COLUMNS].to_numpy(float)
        ),
    }
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest().upper()


def _fit_ridge_fold(
    *,
    X: np.ndarray,
    y_um: np.ndarray,
    simulation_ids: np.ndarray,
    numeric_ids: np.ndarray,
    target: str,
    model_name: str,
    fold_index: int,
    run_fingerprint: str,
) -> dict[str, Any]:
    n = len(y_um)
    training_mask = np.ones(n, dtype=bool)
    training_mask[fold_index] = False
    train_indices = np.flatnonzero(training_mask)
    X_train = X[training_mask]
    X_test = X[[fold_index]]
    y_train = y_um[training_mask]
    y_test = float(y_um[fold_index])
    outer_training_ids = simulation_ids[training_mask].astype(str)

    inner_seed = deterministic_seed("ridge-inner", target, fold_index)
    inner_cv = KFold(
        n_splits=RIDGE_INNER_FOLDS,
        shuffle=True,
        random_state=inner_seed,
    )
    inner_splits = list(inner_cv.split(X_train))
    validation_id_groups = [
        outer_training_ids[validation_indices].tolist()
        for _, validation_indices in inner_splits
    ]
    split_hash = hashlib.sha256(
        json_compact(validation_id_groups).encode("utf-8")
    ).hexdigest().upper()

    started = time.perf_counter()
    mean_rmse_by_alpha: list[float] = []
    fold_rmse_by_alpha: list[list[float]] = []
    for alpha in RIDGE_ALPHA_GRID:
        split_rmses: list[float] = []
        for inner_train_indices, inner_validation_indices in inner_splits:
            estimator = _make_ridge_regressor(model_name, alpha)
            estimator.fit(
                X_train[inner_train_indices],
                y_train[inner_train_indices],
            )
            validation_prediction = estimator.predict(
                X_train[inner_validation_indices]
            )
            validation_rmse = float(
                math.sqrt(
                    mean_squared_error(
                        y_train[inner_validation_indices],
                        validation_prediction,
                    )
                )
            )
            split_rmses.append(validation_rmse)
        fold_rmse_by_alpha.append(split_rmses)
        mean_rmse_by_alpha.append(float(np.mean(split_rmses)))
    selected_index = int(np.argmin(mean_rmse_by_alpha))
    selected_alpha = float(RIDGE_ALPHA_GRID[selected_index])
    final_estimator = _make_ridge_regressor(model_name, selected_alpha)
    final_estimator.fit(X_train, y_train)
    predicted = float(final_estimator.predict(X_test)[0])
    runtime_seconds = time.perf_counter() - started

    fitted_pipeline = final_estimator.regressor_
    input_scaler = fitted_pipeline.named_steps["scale_inputs"]
    target_scaler = final_estimator.transformer_
    residual = y_test - predicted
    return {
        "analysis_label": "phase3a_simple_baselines",
        "phase": "Phase 3A",
        "phase3_config_fingerprint": scientific_config_fingerprint(),
        "run_fingerprint": run_fingerprint,
        "target": target,
        "target_label": TARGET_LABELS[target],
        "target_definition": "T0",
        "model": model_name,
        "model_family": "Ridge",
        "fold_index": fold_index,
        "heldout_simulation_id": str(simulation_ids[fold_index]),
        "heldout_numeric_simulation_id": int(numeric_ids[fold_index]),
        "observed_target_um": y_test,
        "predicted_mean_um": predicted,
        "residual_um": residual,
        "absolute_error_um": abs(residual),
        "squared_error_um2": residual**2,
        "selected_ridge_alpha": selected_alpha,
        "selected_alpha_grid_index": selected_index,
        "selected_mean_inner_validation_rmse_um": mean_rmse_by_alpha[
            selected_index
        ],
        "inner_mean_validation_rmse_by_alpha_json": json_compact(
            [
                {"alpha": alpha, "mean_rmse_um": rmse}
                for alpha, rmse in zip(RIDGE_ALPHA_GRID, mean_rmse_by_alpha)
            ]
        ),
        "inner_fold_validation_rmse_by_alpha_json": json_compact(
            [
                {"alpha": alpha, "fold_rmse_um": rmses}
                for alpha, rmses in zip(
                    RIDGE_ALPHA_GRID, fold_rmse_by_alpha
                )
            ]
        ),
        "ridge_alpha_grid": json_compact(list(RIDGE_ALPHA_GRID)),
        "inner_cv_folds": RIDGE_INNER_FOLDS,
        "inner_cv_shuffle": True,
        "inner_cv_random_seed": inner_seed,
        "inner_cv_validation_id_groups_json": json_compact(
            validation_id_groups
        ),
        "inner_cv_split_sha256": split_hash,
        "inner_cv_selection_metric": "mean validation RMSE in micrometres",
        "polynomial_degree": 2 if model_name.startswith("polynomial") else 1,
        "polynomial_include_bias": (
            False if model_name.startswith("polynomial") else np.nan
        ),
        "preprocessing_pipeline": (
            "StandardScaler -> PolynomialFeatures(degree=2, "
            "include_bias=False) -> StandardScaler -> Ridge"
            if model_name.startswith("polynomial")
            else "StandardScaler -> Ridge"
        ),
        "training_size": len(train_indices),
        "population_size": n,
        "heldout_excluded_from_training": bool(
            fold_index not in set(train_indices)
        ),
        "heldout_target_used_for_scaling": False,
        "heldout_target_used_for_fitting": False,
        "heldout_target_used_for_tuning": False,
        "inner_cv_uses_outer_training_only": True,
        "x_scaler_fit_on_training_only": True,
        "y_scaler_fit_on_training_only": True,
        "feature_columns": json_compact(FEATURE_COLUMNS),
        "training_y_mean_um": float(target_scaler.mean_[0]),
        "training_y_std_um": float(target_scaler.scale_[0]),
        "x_training_mean": json_compact(
            [float(value) for value in input_scaler.mean_]
        ),
        "x_training_scale": json_compact(
            [float(value) for value in input_scaler.scale_]
        ),
        "outer_training_simulation_ids_sha256": hashlib.sha256(
            json_compact(outer_training_ids.tolist()).encode("utf-8")
        ).hexdigest().upper(),
        **{
            f"heldout_{feature}": float(X[fold_index, feature_index])
            for feature_index, feature in enumerate(FEATURE_COLUMNS)
        },
        "runtime_seconds": runtime_seconds,
        "warning_count": 0,
        "warnings": "",
        "failed_fold": False,
    }


def _ridge_checkpoint_path(target: str, model_name: str) -> Path:
    return CHECKPOINT_DIR / f"ridge__{target}__{model_name}.csv"


def _ridge_checkpoint_valid(
    frame: pd.DataFrame,
    *,
    expected_rows: int,
    target: str,
    model_name: str,
    run_fingerprint: str,
) -> bool:
    required = {
        "heldout_simulation_id",
        "predicted_mean_um",
        "selected_ridge_alpha",
        "run_fingerprint",
        "target",
        "model",
    }
    if not required.issubset(frame.columns):
        return False
    return bool(
        len(frame) == expected_rows
        and frame["heldout_simulation_id"].is_unique
        and set(frame["target"].astype(str)) == {target}
        and set(frame["model"].astype(str)) == {model_name}
        and set(frame["run_fingerprint"].astype(str)) == {run_fingerprint}
        and np.isfinite(frame["predicted_mean_um"].to_numpy(float)).all()
        and set(frame["selected_ridge_alpha"].astype(float)).issubset(
            set(RIDGE_ALPHA_GRID)
        )
    )


def run_ridge_loo(
    modelling_table: pd.DataFrame,
    *,
    target: str,
    model_name: str,
    workers: int,
    force: bool,
    use_checkpoint: bool = True,
) -> pd.DataFrame:
    table = modelling_table.sort_values("numeric_simulation_id").reset_index(
        drop=True
    )
    run_fingerprint = _ridge_run_fingerprint(
        table, target=target, model_name=model_name
    )
    checkpoint = _ridge_checkpoint_path(target, model_name)
    if use_checkpoint and not force and checkpoint.exists():
        cached = pd.read_csv(checkpoint)
        if _ridge_checkpoint_valid(
            cached,
            expected_rows=len(table),
            target=target,
            model_name=model_name,
            run_fingerprint=run_fingerprint,
        ):
            print(f"checkpoint reused: {checkpoint.name}", flush=True)
            RUNTIME_EVENTS.append(
                {
                    "stage": "ridge_loo",
                    "target": target,
                    "model": model_name,
                    "cache_reused": True,
                    "checkpoint": str(checkpoint.relative_to(ROOT)),
                    "wall_runtime_seconds": 0.0,
                    "aggregate_fold_runtime_seconds": float(
                        cached["runtime_seconds"].sum()
                    ),
                    "fold_count": len(cached),
                }
            )
            return cached.sort_values("fold_index").reset_index(drop=True)

    X = table[FEATURE_COLUMNS].to_numpy(float)
    y_um = table["target_value_um"].to_numpy(float)
    simulation_ids = table["simulation_id"].astype(str).to_numpy()
    numeric_ids = table["numeric_simulation_id"].to_numpy(int)
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    with threadpool_limits(limits=1):
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = {
                pool.submit(
                    _fit_ridge_fold,
                    X=X,
                    y_um=y_um,
                    simulation_ids=simulation_ids,
                    numeric_ids=numeric_ids,
                    target=target,
                    model_name=model_name,
                    fold_index=fold_index,
                    run_fingerprint=run_fingerprint,
                ): fold_index
                for fold_index in range(len(table))
            }
            for completed, future in enumerate(as_completed(futures), start=1):
                fold_index = futures[future]
                try:
                    rows.append(future.result())
                except Exception as exc:
                    raise RuntimeError(
                        f"Nested Ridge failed for {target}/{model_name}/fold "
                        f"{fold_index}"
                    ) from exc
                if completed % 20 == 0 or completed == len(table):
                    print(
                        f"Phase 3A {target} {model_name}: "
                        f"{completed}/{len(table)} folds "
                        f"({time.perf_counter() - started:.1f}s)",
                        flush=True,
                    )
    wall_runtime = time.perf_counter() - started
    frame = pd.DataFrame(rows).sort_values("fold_index").reset_index(drop=True)
    if not _ridge_checkpoint_valid(
        frame,
        expected_rows=len(table),
        target=target,
        model_name=model_name,
        run_fingerprint=run_fingerprint,
    ):
        raise RuntimeError(f"Generated Ridge checkpoint is invalid: {target}/{model_name}")
    if use_checkpoint:
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        temporary = checkpoint.with_suffix(checkpoint.suffix + ".tmp")
        frame.to_csv(temporary, index=False, lineterminator="\n")
        os.replace(temporary, checkpoint)
    RUNTIME_EVENTS.append(
        {
            "stage": "ridge_loo",
            "target": target,
            "model": model_name,
            "cache_reused": False,
            "checkpoint": (
                str(checkpoint.relative_to(ROOT)) if use_checkpoint else None
            ),
            "wall_runtime_seconds": wall_runtime,
            "aggregate_fold_runtime_seconds": float(
                frame["runtime_seconds"].sum()
            ),
            "fold_count": len(frame),
            "workers": max(1, workers),
        }
    )
    return frame


def run_training_mean_loo(
    modelling_table: pd.DataFrame, *, target: str
) -> pd.DataFrame:
    table = modelling_table.sort_values("numeric_simulation_id").reset_index(
        drop=True
    )
    y = table["target_value_um"].to_numpy(float)
    total = float(y.sum())
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for fold_index, row in table.iterrows():
        prediction = (total - float(y[fold_index])) / (len(y) - 1)
        residual = float(y[fold_index] - prediction)
        rows.append(
            {
                "analysis_label": "phase3a_simple_baselines",
                "phase": "Phase 3A",
                "phase3_config_fingerprint": scientific_config_fingerprint(),
                "run_fingerprint": hashlib.sha256(
                    (
                        f"{scientific_config_fingerprint()}|mean|{target}|"
                        f"{array_sha256(y)}"
                    ).encode("utf-8")
                ).hexdigest().upper(),
                "target": target,
                "target_label": TARGET_LABELS[target],
                "target_definition": "T0",
                "model": "training_mean",
                "model_family": "sanity baseline",
                "fold_index": fold_index,
                "heldout_simulation_id": str(row["simulation_id"]),
                "heldout_numeric_simulation_id": int(
                    row["numeric_simulation_id"]
                ),
                "observed_target_um": float(y[fold_index]),
                "predicted_mean_um": prediction,
                "residual_um": residual,
                "absolute_error_um": abs(residual),
                "squared_error_um2": residual**2,
                "training_size": len(y) - 1,
                "population_size": len(y),
                "heldout_excluded_from_training": True,
                "heldout_target_used_for_scaling": False,
                "heldout_target_used_for_fitting": False,
                "heldout_target_used_for_tuning": False,
                "x_scaler_fit_on_training_only": np.nan,
                "y_scaler_fit_on_training_only": np.nan,
                "feature_columns": json_compact(FEATURE_COLUMNS),
                "training_y_mean_um": prediction,
                "training_y_std_um": float(
                    np.delete(y, fold_index).std(ddof=0)
                ),
                "runtime_seconds": 0.0,
                "warning_count": 0,
                "warnings": "",
                "failed_fold": False,
            }
        )
    wall_runtime = time.perf_counter() - started
    RUNTIME_EVENTS.append(
        {
            "stage": "mean_predictor_loo",
            "target": target,
            "cache_reused": False,
            "wall_runtime_seconds": wall_runtime,
            "fold_count": len(rows),
        }
    )
    return pd.DataFrame(rows)


def _boolean_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    if pd.api.types.is_numeric_dtype(series):
        numeric = pd.to_numeric(series, errors="coerce")
        return numeric.fillna(0.0).ne(0.0)
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .map(
            {
                "true": True,
                "false": False,
                "1": True,
                "0": False,
                "1.0": True,
                "0.0": False,
            }
        )
        .fillna(False)
        .astype(bool)
    )


def point_metric_row(
    predictions: pd.DataFrame,
    *,
    model_column: str,
) -> dict[str, Any]:
    if predictions.empty:
        raise ValueError("Cannot calculate metrics from an empty prediction table")
    observed = predictions["observed_target_um"].to_numpy(float)
    predicted = predictions["predicted_mean_um"].to_numpy(float)
    residual = observed - predicted
    absolute = np.abs(residual)
    rmse = float(np.sqrt(np.mean(residual**2)))
    target_range = float(observed.max() - observed.min())
    return {
        "target": str(predictions["target"].iloc[0]),
        "target_label": str(predictions["target_label"].iloc[0]),
        "target_definition": str(
            predictions["target_definition"].iloc[0]
        ),
        "model": str(predictions[model_column].iloc[0]),
        "n_predictions": len(predictions),
        "mae_um": float(mean_absolute_error(observed, predicted)),
        "median_absolute_error_um": float(np.median(absolute)),
        "rmse_um": rmse,
        "r2": float(r2_score(observed, predicted)),
        "nrmse": rmse / target_range if target_range > 0 else np.nan,
        "target_min_um": float(observed.min()),
        "target_median_um": float(np.median(observed)),
        "target_max_um": float(observed.max()),
        "target_range_um": target_range,
        "aggregate_fold_runtime_seconds": float(
            predictions["runtime_seconds"].fillna(0.0).sum()
        ),
        "mean_fold_runtime_seconds": float(
            predictions["runtime_seconds"].fillna(0.0).mean()
        ),
        "failed_folds": int(
            _boolean_series(predictions["failed_fold"]).sum()
        ),
        "warning_folds": int(predictions["warning_count"].fillna(0).gt(0).sum()),
    }


def gp_metric_row(predictions: pd.DataFrame) -> dict[str, Any]:
    row = point_metric_row(predictions, model_column="gp_configuration")
    learned_nugget = bool(
        _boolean_series(predictions["learned_nugget"]).iloc[0]
    )
    latent_coverage = float(
        _boolean_series(
            predictions["latent_interval_contains_observed"]
        ).mean()
    )
    total_available = predictions[
        "total_interval_contains_observed"
    ].notna()
    if total_available.any():
        total_coverage = float(
            _boolean_series(
                predictions.loc[
                    total_available, "total_interval_contains_observed"
                ]
            ).mean()
        )
        total_width = float(
            (
                predictions.loc[
                    total_available, "total_interval_upper_um"
                ].to_numpy(float)
                - predictions.loc[
                    total_available, "total_interval_lower_um"
                ].to_numpy(float)
            ).mean()
        )
    else:
        total_coverage = np.nan
        total_width = np.nan
    latent_width = float(
        (
            predictions["latent_interval_upper_um"].to_numpy(float)
            - predictions["latent_interval_lower_um"].to_numpy(float)
        ).mean()
    )
    evaluation_coverage = total_coverage if learned_nugget else latent_coverage
    row.update(
        {
            "gp_configuration": row.pop("model"),
            "gp_configuration_label": str(
                predictions["gp_configuration_label"].iloc[0]
            ),
            "kernel_family": str(predictions["kernel_family"].iloc[0]),
            "matern_nu": predictions["matern_nu"].iloc[0],
            "learned_nugget": learned_nugget,
            "mean_nlpd": float(predictions["evaluation_nlpd"].mean()),
            "median_nlpd": float(predictions["evaluation_nlpd"].median()),
            "mean_latent_nlpd": float(predictions["latent_nlpd"].mean()),
            "mean_total_nlpd": (
                float(predictions["total_nlpd"].mean())
                if predictions["total_nlpd"].notna().any()
                else np.nan
            ),
            "nlpd_variance_definition": str(
                predictions["evaluation_variance_definition"].iloc[0]
            ),
            "latent_95_coverage": latent_coverage,
            "total_95_coverage": total_coverage,
            "evaluation_95_coverage": evaluation_coverage,
            "calibration_absolute_error_from_0_95": abs(
                evaluation_coverage - 0.95
            ),
            "mean_latent_interval_width_um": latent_width,
            "mean_total_interval_width_um": total_width,
            "optimizer_warning_folds": int(
                predictions["warning_count"].fillna(0).gt(0).sum()
            ),
            "convergence_warning_folds": int(
                predictions["convergence_warning_count"]
                .fillna(0)
                .gt(0)
                .sum()
            ),
            "constant_bound_hit_folds": int(
                _boolean_series(predictions["constant_bound_hit"]).sum()
            ),
            "length_scale_bound_hit_folds": int(
                _boolean_series(predictions["length_scale_bound_hit"]).sum()
            ),
            "nugget_bound_hit_folds": int(
                _boolean_series(predictions["noise_bound_hit"]).sum()
            ),
            "any_bound_hit_folds": int(
                _boolean_series(
                    predictions["any_hyperparameter_bound_hit"]
                ).sum()
            ),
            **_distribution_quantiles(
                predictions["optimized_signal_variance_normalized"],
                "signal_variance_normalized",
            ),
            **_distribution_quantiles(
                predictions["optimized_length_scale"],
                "length_scale",
            ),
            **_distribution_quantiles(
                predictions["optimized_noise_variance_normalized"],
                "learned_nugget_variance_normalized",
            ),
            **_distribution_quantiles(
                predictions["optimized_noise_std_um"],
                "learned_nugget_std_um",
            ),
            **_distribution_quantiles(
                predictions["noise_std_fraction_training_target_std"],
                "nugget_fraction_training_target_std",
            ),
            **_distribution_quantiles(
                predictions["noise_std_fraction_dataset_target_median"],
                "nugget_fraction_dataset_target_median",
            ),
        }
    )
    return row


def build_gp_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = [
        gp_metric_row(subset)
        for _, subset in predictions.groupby(
            ["target", "target_definition", "gp_configuration"], sort=True
        )
    ]
    return pd.DataFrame(rows).sort_values(
        ["target", "target_definition", "gp_configuration"]
    ).reset_index(drop=True)


def _paired_bootstrap_arrays(
    reference_residuals: np.ndarray,
    candidate_residuals: np.ndarray,
    *,
    seed: int,
    resamples: int = PAIRED_BOOTSTRAP_RESAMPLES,
    batch_size: int = 500,
) -> tuple[np.ndarray, np.ndarray]:
    reference = np.asarray(reference_residuals, dtype=float)
    candidate = np.asarray(candidate_residuals, dtype=float)
    if reference.shape != candidate.shape or reference.ndim != 1:
        raise ValueError("Paired bootstrap residual arrays must be aligned 1-D")
    rng = np.random.default_rng(seed)
    n = len(reference)
    mae_differences = np.empty(resamples, dtype=float)
    rmse_differences = np.empty(resamples, dtype=float)
    cursor = 0
    while cursor < resamples:
        batch = min(batch_size, resamples - cursor)
        indices = rng.integers(0, n, size=(batch, n), endpoint=False)
        ref_sample = reference[indices]
        cand_sample = candidate[indices]
        mae_differences[cursor : cursor + batch] = (
            np.mean(np.abs(cand_sample), axis=1)
            - np.mean(np.abs(ref_sample), axis=1)
        )
        rmse_differences[cursor : cursor + batch] = (
            np.sqrt(np.mean(cand_sample**2, axis=1))
            - np.sqrt(np.mean(ref_sample**2, axis=1))
        )
        cursor += batch
    return mae_differences, rmse_differences


def aligned_prediction_comparison(
    predictions: pd.DataFrame,
    *,
    target: str,
    model_column: str,
    reference_model: str,
    candidate_model: str,
    comparison_type: str,
    target_definition: str = "T0",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    relevant = predictions.loc[
        (predictions["target"] == target)
        & (predictions["target_definition"] == target_definition)
        & predictions[model_column].isin([reference_model, candidate_model])
    ].copy()
    reference = relevant.loc[relevant[model_column] == reference_model].copy()
    candidate = relevant.loc[relevant[model_column] == candidate_model].copy()
    reference = reference.sort_values("heldout_numeric_simulation_id")
    candidate = candidate.sort_values("heldout_numeric_simulation_id")
    reference_ids = reference["heldout_simulation_id"].astype(str).tolist()
    candidate_ids = candidate["heldout_simulation_id"].astype(str).tolist()
    if reference_ids != candidate_ids:
        raise RuntimeError(
            f"Paired comparison IDs differ for {target}/{reference_model}/"
            f"{candidate_model}"
        )
    if not np.allclose(
        reference["observed_target_um"].to_numpy(float),
        candidate["observed_target_um"].to_numpy(float),
        rtol=0.0,
        atol=1e-12,
    ):
        raise RuntimeError("Paired comparison observed targets differ")
    detail = pd.DataFrame(
        {
            "comparison_type": comparison_type,
            "target": target,
            "target_definition": target_definition,
            "reference_model": reference_model,
            "candidate_model": candidate_model,
            "heldout_simulation_id": reference_ids,
            "heldout_numeric_simulation_id": reference[
                "heldout_numeric_simulation_id"
            ].to_numpy(int),
            "observed_target_um": reference["observed_target_um"].to_numpy(
                float
            ),
            "reference_predicted_mean_um": reference[
                "predicted_mean_um"
            ].to_numpy(float),
            "candidate_predicted_mean_um": candidate[
                "predicted_mean_um"
            ].to_numpy(float),
            "reference_residual_um": reference["residual_um"].to_numpy(float),
            "candidate_residual_um": candidate["residual_um"].to_numpy(float),
            "reference_absolute_error_um": reference[
                "absolute_error_um"
            ].to_numpy(float),
            "candidate_absolute_error_um": candidate[
                "absolute_error_um"
            ].to_numpy(float),
        }
    )
    detail["candidate_minus_reference_absolute_error_um"] = (
        detail["candidate_absolute_error_um"]
        - detail["reference_absolute_error_um"]
    )
    seed = deterministic_seed(
        "paired-bootstrap",
        comparison_type,
        target,
        target_definition,
        reference_model,
        candidate_model,
    )
    mae_draws, rmse_draws = _paired_bootstrap_arrays(
        detail["reference_residual_um"].to_numpy(float),
        detail["candidate_residual_um"].to_numpy(float),
        seed=seed,
    )
    reference_residual = detail["reference_residual_um"].to_numpy(float)
    candidate_residual = detail["candidate_residual_um"].to_numpy(float)
    observed_mae_difference = float(
        np.mean(np.abs(candidate_residual))
        - np.mean(np.abs(reference_residual))
    )
    observed_rmse_difference = float(
        np.sqrt(np.mean(candidate_residual**2))
        - np.sqrt(np.mean(reference_residual**2))
    )
    summary = {
        "comparison_type": comparison_type,
        "target": target,
        "target_definition": target_definition,
        "reference_model": reference_model,
        "candidate_model": candidate_model,
        "difference_direction": "candidate minus reference; negative favors candidate",
        "paired_simulation_count": len(detail),
        "bootstrap_resamples": PAIRED_BOOTSTRAP_RESAMPLES,
        "bootstrap_seed": seed,
        "pairing_preserved": True,
        "observed_mae_difference_um": observed_mae_difference,
        "mae_difference_ci95_lower_um": float(
            np.quantile(mae_draws, BOOTSTRAP_QUANTILES[0])
        ),
        "mae_difference_ci95_upper_um": float(
            np.quantile(mae_draws, BOOTSTRAP_QUANTILES[1])
        ),
        "observed_rmse_difference_um": observed_rmse_difference,
        "rmse_difference_ci95_lower_um": float(
            np.quantile(rmse_draws, BOOTSTRAP_QUANTILES[0])
        ),
        "rmse_difference_ci95_upper_um": float(
            np.quantile(rmse_draws, BOOTSTRAP_QUANTILES[1])
        ),
        "candidate_robust_mae_advantage": bool(
            np.quantile(mae_draws, BOOTSTRAP_QUANTILES[1]) < 0
        ),
        "candidate_robust_rmse_advantage": bool(
            np.quantile(rmse_draws, BOOTSTRAP_QUANTILES[1]) < 0
        ),
        "reference_robust_mae_advantage": bool(
            np.quantile(mae_draws, BOOTSTRAP_QUANTILES[0]) > 0
        ),
        "reference_robust_rmse_advantage": bool(
            np.quantile(rmse_draws, BOOTSTRAP_QUANTILES[0]) > 0
        ),
    }
    return detail, summary


def build_phase3a_outputs(
    populations: dict[str, pd.DataFrame],
    current_gp_predictions: dict[str, pd.DataFrame],
    *,
    workers: int,
    force: bool,
) -> dict[str, pd.DataFrame]:
    started = time.perf_counter()
    prediction_frames: list[pd.DataFrame] = []
    for target in TARGET_KEYS:
        modelling = population_t0_modelling_table(populations[target], target)
        mean_rows = run_training_mean_loo(modelling, target=target)
        linear_rows = run_ridge_loo(
            modelling,
            target=target,
            model_name="linear_ridge",
            workers=workers,
            force=force,
        )
        polynomial_rows = run_ridge_loo(
            modelling,
            target=target,
            model_name="polynomial_ridge_degree2",
            workers=workers,
            force=force,
        )
        gp_rows = current_gp_predictions[target].copy()
        gp_rows["source_analysis_label"] = gp_rows["analysis_label"]
        gp_rows["analysis_label"] = "phase3a_simple_baselines"
        gp_rows["phase"] = "Phase 3A"
        gp_rows["model"] = CURRENT_GP_CONFIG_NAME
        gp_rows["model_family"] = "Gaussian process"
        gp_rows["source_gp_rows_reused_without_refit"] = True
        prediction_frames.extend(
            [mean_rows, linear_rows, polynomial_rows, gp_rows]
        )
    predictions = pd.concat(
        prediction_frames, ignore_index=True, sort=False
    ).sort_values(["target", "model", "fold_index"])
    predictions = predictions.reset_index(drop=True)

    metric_rows: list[dict[str, Any]] = []
    for (_, _), subset in predictions.groupby(["target", "model"], sort=True):
        metric_rows.append(point_metric_row(subset, model_column="model"))
    metrics = pd.DataFrame(metric_rows).sort_values(["target", "model"])

    hyperparameter_columns = [
        "target",
        "target_label",
        "model",
        "fold_index",
        "heldout_simulation_id",
        "heldout_numeric_simulation_id",
        "selected_ridge_alpha",
        "selected_alpha_grid_index",
        "selected_mean_inner_validation_rmse_um",
        "ridge_alpha_grid",
        "inner_cv_folds",
        "inner_cv_shuffle",
        "inner_cv_random_seed",
        "inner_cv_split_sha256",
        "inner_cv_selection_metric",
        "inner_mean_validation_rmse_by_alpha_json",
        "inner_fold_validation_rmse_by_alpha_json",
        "inner_cv_validation_id_groups_json",
        "training_size",
        "population_size",
        "heldout_excluded_from_training",
        "heldout_target_used_for_tuning",
        "inner_cv_uses_outer_training_only",
        "runtime_seconds",
    ]
    hyperparameters = predictions.loc[
        predictions["model"].isin(
            ["linear_ridge", "polynomial_ridge_degree2"]
        ),
        hyperparameter_columns,
    ].copy()

    comparison_details: list[pd.DataFrame] = []
    comparison_summaries: list[dict[str, Any]] = []
    for target in TARGET_KEYS:
        gp_rmse = float(
            metrics.loc[
                (metrics["target"] == target)
                & (metrics["model"] == CURRENT_GP_CONFIG_NAME),
                "rmse_um",
            ].iloc[0]
        )
        practical_threshold = max(0.5, 0.05 * gp_rmse)
        for candidate in ["linear_ridge", "polynomial_ridge_degree2"]:
            detail, summary = aligned_prediction_comparison(
                predictions,
                target=target,
                model_column="model",
                reference_model=CURRENT_GP_CONFIG_NAME,
                candidate_model=candidate,
                comparison_type="Phase 3A simple model minus current GP",
            )
            summary["practical_rmse_difference_threshold_um"] = (
                practical_threshold
            )
            summary["practical_difference_negligible"] = bool(
                abs(summary["observed_rmse_difference_um"])
                <= practical_threshold
            )
            summary["confidence_interval_includes_zero_mae"] = bool(
                summary["mae_difference_ci95_lower_um"] <= 0
                <= summary["mae_difference_ci95_upper_um"]
            )
            summary["confidence_interval_includes_zero_rmse"] = bool(
                summary["rmse_difference_ci95_lower_um"] <= 0
                <= summary["rmse_difference_ci95_upper_um"]
            )
            summary["simple_model_competitive"] = bool(
                summary["confidence_interval_includes_zero_rmse"]
                or summary["practical_difference_negligible"]
                or summary["candidate_robust_rmse_advantage"]
            )
            comparison_details.append(detail)
            comparison_summaries.append(summary)
    comparison_detail = pd.concat(comparison_details, ignore_index=True)
    comparison_summary = pd.DataFrame(comparison_summaries).sort_values(
        ["target", "candidate_model"]
    )
    RUNTIME_EVENTS.append(
        {
            "stage": "phase3a_assembly",
            "cache_reused": False,
            "wall_runtime_seconds": time.perf_counter() - started,
            "prediction_rows": len(predictions),
        }
    )
    return {
        "predictions": predictions,
        "metrics": metrics.reset_index(drop=True),
        "hyperparameters": hyperparameters.reset_index(drop=True),
        "comparison_detail": comparison_detail.reset_index(drop=True),
        "comparison_summary": comparison_summary.reset_index(drop=True),
    }


def build_gp_hyperparameter_diagnostics(
    predictions: pd.DataFrame,
) -> pd.DataFrame:
    columns = [
        "target",
        "target_label",
        "target_definition",
        "gp_configuration",
        "gp_configuration_label",
        "kernel_family",
        "matern_nu",
        "learned_nugget",
        "fold_index",
        "heldout_simulation_id",
        "heldout_numeric_simulation_id",
        "training_size",
        "population_size",
        "optimized_kernel",
        "optimized_signal_variance_normalized",
        "optimized_length_scale",
        "optimized_noise_variance_normalized",
        "optimized_noise_std_normalized",
        "optimized_noise_variance_um2",
        "optimized_noise_std_um",
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
    return predictions[columns].copy().sort_values(
        ["target", "gp_configuration", "fold_index"]
    )


def build_learned_nugget_summary(
    predictions: pd.DataFrame,
) -> pd.DataFrame:
    learned = predictions.loc[
        _boolean_series(predictions["learned_nugget"])
    ].copy()
    rows: list[dict[str, Any]] = []
    for (target, configuration), subset in learned.groupby(
        ["target", "gp_configuration"], sort=True
    ):
        rows.append(
            {
                "target": target,
                "target_label": TARGET_LABELS[target],
                "gp_configuration": configuration,
                "gp_configuration_label": subset[
                    "gp_configuration_label"
                ].iloc[0],
                "kernel_family": subset["kernel_family"].iloc[0],
                "matern_nu": subset["matern_nu"].iloc[0],
                "fold_count": len(subset),
                **_distribution_quantiles(
                    subset["optimized_noise_variance_normalized"],
                    "nugget_variance_normalized",
                ),
                **_distribution_quantiles(
                    subset["optimized_noise_variance_um2"],
                    "nugget_variance_um2",
                ),
                **_distribution_quantiles(
                    subset["optimized_noise_std_um"], "nugget_std_um"
                ),
                **_distribution_quantiles(
                    subset["noise_std_fraction_training_target_std"],
                    "nugget_fraction_training_target_std",
                ),
                **_distribution_quantiles(
                    subset["noise_std_fraction_dataset_target_median"],
                    "nugget_fraction_dataset_target_median",
                ),
                "nugget_bound_hit_folds": int(
                    _boolean_series(subset["noise_bound_hit"]).sum()
                ),
                "warning_folds": int(subset["warning_count"].gt(0).sum()),
            }
        )
    result = pd.DataFrame(rows).sort_values(
        ["target", "gp_configuration"]
    )
    if len(result) != len(TARGET_KEYS) * 3:
        raise RuntimeError("Learned-nugget summary is incomplete")
    return result.reset_index(drop=True)


def choose_provisional_kernels(
    metrics: pd.DataFrame,
    candidate_comparisons: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for target in TARGET_KEYS:
        target_metrics = metrics.loc[metrics["target"] == target].set_index(
            "gp_configuration"
        )
        current = target_metrics.loc[CURRENT_GP_CONFIG_NAME]
        eligible: list[str] = []
        reasons: dict[str, str] = {}
        for candidate in GP_CONFIG_BY_NAME:
            if candidate == CURRENT_GP_CONFIG_NAME:
                continue
            comparison = candidate_comparisons.loc[
                (candidate_comparisons["target"] == target)
                & (
                    candidate_comparisons["candidate_model"]
                    == candidate
                )
            ].iloc[0]
            candidate_metrics = target_metrics.loc[candidate]
            robust_point_advantage = bool(
                comparison["candidate_robust_mae_advantage"]
                and comparison["candidate_robust_rmse_advantage"]
            )
            candidate_coverage = float(
                candidate_metrics["evaluation_95_coverage"]
            )
            no_serious_calibration_deterioration = bool(
                0.90 <= candidate_coverage <= 0.99
                and float(candidate_metrics["mean_nlpd"])
                <= float(current["mean_nlpd"]) + 0.25
                and float(
                    candidate_metrics[
                        "calibration_absolute_error_from_0_95"
                    ]
                )
                <= float(
                    current["calibration_absolute_error_from_0_95"]
                )
                + 0.02
            )
            stable_optimization = bool(
                int(candidate_metrics["failed_folds"]) == 0
                and int(candidate_metrics["optimizer_warning_folds"])
                <= max(
                    1,
                    math.floor(
                        0.05 * EXPECTED_POPULATION_SIZES[target]
                    ),
                )
                and int(candidate_metrics["any_bound_hit_folds"])
                <= math.floor(
                    0.10 * EXPECTED_POPULATION_SIZES[target]
                )
            )
            if (
                robust_point_advantage
                and no_serious_calibration_deterioration
                and stable_optimization
            ):
                eligible.append(candidate)
            reasons[candidate] = (
                f"robust_point_advantage={robust_point_advantage}; "
                "no_serious_calibration_deterioration="
                f"{no_serious_calibration_deterioration}; "
                f"stable_optimization={stable_optimization}"
            )
        if eligible:
            selected = min(
                eligible,
                key=lambda name: float(
                    target_metrics.loc[name, "rmse_um"]
                ),
            )
            replacement = True
            rationale = (
                f"{selected} satisfies the predeclared replacement rule and "
                "has the lowest RMSE among eligible robust replacements."
            )
        else:
            selected = CURRENT_GP_CONFIG_NAME
            replacement = False
            rationale = (
                "No alternative jointly showed robust MAE and RMSE gains, "
                "acceptable calibration, and stable optimization; retain "
                "Matérn 3/2 + learned nugget for parsimony and continuity."
            )
        selected_metrics = target_metrics.loc[selected]
        rows.append(
            {
                "target": target,
                "target_label": TARGET_LABELS[target],
                "current_configuration": CURRENT_GP_CONFIG_NAME,
                "selected_provisional_gp_configuration": selected,
                "selected_configuration_label": GP_CONFIG_BY_NAME[
                    selected
                ].label,
                "another_kernel_replaces_current": replacement,
                "eligible_replacements": json_compact(eligible),
                "candidate_rule_evaluations": json_compact(reasons),
                "decision_rule": (
                    "replace only for robust paired MAE and RMSE advantage, "
                    "no serious calibration deterioration, stable optimization, "
                    "and no systematic bound-hitting"
                ),
                "rationale": rationale,
                "selected_mae_um": float(selected_metrics["mae_um"]),
                "selected_rmse_um": float(selected_metrics["rmse_um"]),
                "selected_mean_nlpd": float(
                    selected_metrics["mean_nlpd"]
                ),
                "selected_evaluation_95_coverage": float(
                    selected_metrics["evaluation_95_coverage"]
                ),
                "selected_warning_folds": int(
                    selected_metrics["optimizer_warning_folds"]
                ),
                "selected_bound_hit_folds": int(
                    selected_metrics["any_bound_hit_folds"]
                ),
                "selected_failed_folds": int(
                    selected_metrics["failed_folds"]
                ),
            }
        )
    return pd.DataFrame(rows)


def build_phase3b_outputs(
    populations: dict[str, pd.DataFrame],
    current_gp_predictions: dict[str, pd.DataFrame],
    *,
    workers: int,
    force: bool,
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    started = time.perf_counter()
    frames: list[pd.DataFrame] = []
    prediction_by_key: dict[tuple[str, str], pd.DataFrame] = {}
    for target in TARGET_KEYS:
        current = current_gp_predictions[target]
        prediction_by_key[(target, CURRENT_GP_CONFIG_NAME)] = current
        frames.append(current)
        modelling = population_t0_modelling_table(populations[target], target)
        for configuration in GP_CONFIGURATIONS:
            if configuration.name == CURRENT_GP_CONFIG_NAME:
                continue
            result = run_gp_loo(
                modelling,
                target=target,
                target_definition="T0",
                analysis_label="phase3b_kernel_noise",
                configuration=configuration,
                workers=workers,
                force=force,
            )
            prediction_by_key[(target, configuration.name)] = result
            frames.append(result)
    predictions = pd.concat(frames, ignore_index=True).sort_values(
        ["target", "gp_configuration", "fold_index"]
    )
    metrics = build_gp_metrics(predictions)
    hyperparameters = build_gp_hyperparameter_diagnostics(predictions)
    learned_nugget = build_learned_nugget_summary(predictions)

    within_details: list[pd.DataFrame] = []
    within_summaries: list[dict[str, Any]] = []
    candidate_details: list[pd.DataFrame] = []
    candidate_summaries: list[dict[str, Any]] = []
    family_pairs = [
        ("RBF", "rbf_no_nugget", "rbf_learned_nugget"),
        (
            "Matérn 3/2",
            "matern32_no_nugget",
            "matern32_learned_nugget",
        ),
        (
            "Matérn 5/2",
            "matern52_no_nugget",
            "matern52_learned_nugget",
        ),
    ]
    for target in TARGET_KEYS:
        for family, no_nugget, learned in family_pairs:
            detail, summary = aligned_prediction_comparison(
                predictions,
                target=target,
                model_column="gp_configuration",
                reference_model=no_nugget,
                candidate_model=learned,
                comparison_type="within-kernel learned nugget minus no nugget",
            )
            detail["kernel_family_comparison"] = family
            summary["kernel_family_comparison"] = family
            summary["nugget_conclusion"] = (
                "learned nugget robustly improves MAE and RMSE"
                if summary["candidate_robust_mae_advantage"]
                and summary["candidate_robust_rmse_advantage"]
                else "no nugget robustly improves MAE and RMSE"
                if summary["reference_robust_mae_advantage"]
                and summary["reference_robust_rmse_advantage"]
                else "mixed or statistically uncertain point-prediction difference"
            )
            within_details.append(detail)
            within_summaries.append(summary)
        for configuration in GP_CONFIGURATIONS:
            if configuration.name == CURRENT_GP_CONFIG_NAME:
                continue
            detail, summary = aligned_prediction_comparison(
                predictions,
                target=target,
                model_column="gp_configuration",
                reference_model=CURRENT_GP_CONFIG_NAME,
                candidate_model=configuration.name,
                comparison_type="GP candidate minus current Matérn 3/2 learned nugget",
            )
            candidate_details.append(detail)
            candidate_summaries.append(summary)
    within_detail = pd.concat(within_details, ignore_index=True)
    within_summary = pd.DataFrame(within_summaries)
    candidate_detail = pd.concat(candidate_details, ignore_index=True)
    candidate_summary = pd.DataFrame(candidate_summaries)
    bootstrap_summary = pd.concat(
        [
            within_summary.assign(summary_scope="within_kernel"),
            candidate_summary.assign(summary_scope="candidate_vs_current"),
        ],
        ignore_index=True,
        sort=False,
    ).sort_values(["target", "summary_scope", "candidate_model"])
    provisional = choose_provisional_kernels(metrics, candidate_summary)
    RUNTIME_EVENTS.append(
        {
            "stage": "phase3b_assembly",
            "cache_reused": False,
            "wall_runtime_seconds": time.perf_counter() - started,
            "prediction_rows": len(predictions),
        }
    )
    outputs = {
        "predictions": predictions.reset_index(drop=True),
        "metrics": metrics,
        "hyperparameters": hyperparameters.reset_index(drop=True),
        "within_detail": within_detail.reset_index(drop=True),
        "candidate_detail": candidate_detail.reset_index(drop=True),
        "bootstrap_summary": bootstrap_summary.reset_index(drop=True),
        "learned_nugget": learned_nugget,
        "provisional": provisional,
    }
    frames_by_target_config = {
        f"{target}|{configuration}": frame
        for (target, configuration), frame in prediction_by_key.items()
    }
    return outputs, frames_by_target_config


def build_target_difference_summary(
    target_table: pd.DataFrame,
    phase3b_nugget_summary: pd.DataFrame,
) -> pd.DataFrame:
    modelling = target_table.loc[
        target_table["in_target_modelling_population"].astype(bool)
    ].copy()
    current_nugget = phase3b_nugget_summary.loc[
        phase3b_nugget_summary["gp_configuration"]
        == CURRENT_GP_CONFIG_NAME
    ].set_index("target")
    rows: list[dict[str, Any]] = []
    for target in TARGET_KEYS:
        target_rows = modelling.loc[modelling["target"] == target].copy()
        t0 = (
            target_rows.loc[target_rows["target_definition"] == "T0"]
            .set_index("simulation_id")
            .sort_index()
        )
        nugget_std_um = float(
            current_nugget.loc[target, "nugget_std_um_median"]
        )
        for definition in TARGET_DEFINITION_CODES:
            alternative = (
                target_rows.loc[
                    target_rows["target_definition"] == definition
                ]
                .set_index("simulation_id")
                .sort_index()
            )
            if list(t0.index) != list(alternative.index):
                raise RuntimeError(
                    f"Target-difference IDs differ for {target}/{definition}"
                )
            current_values = t0["target_value_um"].to_numpy(float)
            alternative_values = alternative["target_value_um"].to_numpy(float)
            difference = alternative_values - current_values
            absolute = np.abs(difference)
            relative = np.divide(
                absolute,
                np.abs(current_values),
                out=np.full_like(absolute, np.nan),
                where=np.abs(current_values) > 0,
            )
            if definition == "T0":
                pearson = 1.0
                pearson_p = 0.0
                spearman = 1.0
                spearman_p = 0.0
            else:
                pearson_result = pearsonr(current_values, alternative_values)
                spearman_result = spearmanr(current_values, alternative_values)
                pearson = float(pearson_result.statistic)
                pearson_p = float(pearson_result.pvalue)
                spearman = float(spearman_result.statistic)
                spearman_p = float(spearman_result.pvalue)
            rows.append(
                {
                    "target": target,
                    "target_label": TARGET_LABELS[target],
                    "target_definition": definition,
                    "target_definition_label": TARGET_DEFINITION_BY_CODE[
                        definition
                    ].label,
                    "paired_simulation_count": len(current_values),
                    "pearson_correlation_with_t0": pearson,
                    "pearson_p_value": pearson_p,
                    "spearman_correlation_with_t0": spearman,
                    "spearman_p_value": spearman_p,
                    "median_signed_difference_from_t0_um": float(
                        np.median(difference)
                    ),
                    "median_absolute_difference_from_t0_um": float(
                        np.median(absolute)
                    ),
                    "q95_absolute_difference_from_t0_um": float(
                        np.quantile(absolute, 0.95)
                    ),
                    "maximum_absolute_difference_from_t0_um": float(
                        absolute.max()
                    ),
                    "median_relative_difference_from_t0": float(
                        np.nanmedian(relative)
                    ),
                    "q95_relative_difference_from_t0": float(
                        np.nanquantile(relative, 0.95)
                    ),
                    "fraction_absolute_difference_exceeds_1_um": float(
                        np.mean(absolute > 1.0)
                    ),
                    "current_matern32_learned_nugget_std_median_um": (
                        nugget_std_um
                    ),
                    "fraction_absolute_difference_exceeds_current_learned_nugget_std": float(
                        np.mean(absolute > nugget_std_um)
                    ),
                    "fraction_absolute_difference_exceeds_5pct_t0": float(
                        np.mean(absolute > 0.05 * np.abs(current_values))
                    ),
                    "target_shift_and_nugget_are_conceptually_distinct": True,
                    "scale_comparison_interpretation": (
                        "descriptive only: between-definition target shift is "
                        "not the same concept as a GP's learned effective nugget"
                    ),
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["target", "target_definition"]
    ).reset_index(drop=True)


def build_target_definition_nugget_summary(
    predictions: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (target, definition), subset in predictions.groupby(
        ["target", "target_definition"], sort=True
    ):
        learned = bool(_boolean_series(subset["learned_nugget"]).iloc[0])
        row = {
            "target": target,
            "target_label": TARGET_LABELS[target],
            "target_definition": definition,
            "target_definition_label": TARGET_DEFINITION_BY_CODE[
                definition
            ].label,
            "gp_configuration": subset["gp_configuration"].iloc[0],
            "learned_nugget": learned,
            "fold_count": len(subset),
            **_distribution_quantiles(
                subset["optimized_noise_variance_normalized"],
                "nugget_variance_normalized",
            ),
            **_distribution_quantiles(
                subset["optimized_noise_variance_um2"],
                "nugget_variance_um2",
            ),
            **_distribution_quantiles(
                subset["optimized_noise_std_um"], "nugget_std_um"
            ),
            **_distribution_quantiles(
                subset["noise_std_fraction_training_target_std"],
                "nugget_fraction_training_target_std",
            ),
            **_distribution_quantiles(
                subset["noise_std_fraction_dataset_target_median"],
                "nugget_fraction_dataset_target_median",
            ),
            "warning_folds": int(subset["warning_count"].gt(0).sum()),
            "failed_folds": int(_boolean_series(subset["failed_fold"]).sum()),
            "any_bound_hit_folds": int(
                _boolean_series(
                    subset["any_hyperparameter_bound_hit"]
                ).sum()
            ),
        }
        rows.append(row)
    result = pd.DataFrame(rows).sort_values(
        ["target", "target_definition"]
    )
    if len(result) != len(TARGET_KEYS) * len(TARGET_DEFINITIONS):
        raise RuntimeError("Target-definition nugget summary is incomplete")
    return result.reset_index(drop=True)


def target_definition_predictability_comparison(
    predictions: pd.DataFrame,
    *,
    target: str,
    alternative_definition: str,
) -> dict[str, Any]:
    t0 = (
        predictions.loc[
            (predictions["target"] == target)
            & (predictions["target_definition"] == "T0")
        ]
        .sort_values("heldout_numeric_simulation_id")
        .reset_index(drop=True)
    )
    alternative = (
        predictions.loc[
            (predictions["target"] == target)
            & (
                predictions["target_definition"]
                == alternative_definition
            )
        ]
        .sort_values("heldout_numeric_simulation_id")
        .reset_index(drop=True)
    )
    if t0["heldout_simulation_id"].astype(str).tolist() != alternative[
        "heldout_simulation_id"
    ].astype(str).tolist():
        raise RuntimeError(
            f"Target-definition model IDs differ for "
            f"{target}/{alternative_definition}"
        )
    seed = deterministic_seed(
        "target-definition-predictability-bootstrap",
        target,
        alternative_definition,
    )
    mae_draws, rmse_draws = _paired_bootstrap_arrays(
        t0["residual_um"].to_numpy(float),
        alternative["residual_um"].to_numpy(float),
        seed=seed,
    )
    t0_residual = t0["residual_um"].to_numpy(float)
    alternative_residual = alternative["residual_um"].to_numpy(float)
    return {
        "target": target,
        "target_label": TARGET_LABELS[target],
        "reference_target_definition": "T0",
        "alternative_target_definition": alternative_definition,
        "gp_configuration": t0["gp_configuration"].iloc[0],
        "difference_direction": (
            "alternative minus T0 predictability metric; target quantity "
            "changes, so this is not a same-target accuracy contest"
        ),
        "paired_simulation_count": len(t0),
        "bootstrap_resamples": PAIRED_BOOTSTRAP_RESAMPLES,
        "bootstrap_seed": seed,
        "pairing_preserved": True,
        "observed_mae_difference_um": float(
            np.mean(np.abs(alternative_residual))
            - np.mean(np.abs(t0_residual))
        ),
        "mae_difference_ci95_lower_um": float(
            np.quantile(mae_draws, BOOTSTRAP_QUANTILES[0])
        ),
        "mae_difference_ci95_upper_um": float(
            np.quantile(mae_draws, BOOTSTRAP_QUANTILES[1])
        ),
        "observed_rmse_difference_um": float(
            np.sqrt(np.mean(alternative_residual**2))
            - np.sqrt(np.mean(t0_residual**2))
        ),
        "rmse_difference_ci95_lower_um": float(
            np.quantile(rmse_draws, BOOTSTRAP_QUANTILES[0])
        ),
        "rmse_difference_ci95_upper_um": float(
            np.quantile(rmse_draws, BOOTSTRAP_QUANTILES[1])
        ),
        "alternative_robust_mae_predictability_advantage": bool(
            np.quantile(mae_draws, BOOTSTRAP_QUANTILES[1]) < 0
        ),
        "alternative_robust_rmse_predictability_advantage": bool(
            np.quantile(rmse_draws, BOOTSTRAP_QUANTILES[1]) < 0
        ),
    }


def choose_target_definitions(
    distribution_summary: pd.DataFrame,
    difference_summary: pd.DataFrame,
    model_metrics: pd.DataFrame,
    nugget_summary: pd.DataFrame,
    predictability_comparisons: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    physically_eligible = {
        "T1": False,
        "T2": False,
        "T3": True,
        "T4": False,
        "T5": False,
    }
    physical_notes = {
        "T1": (
            "A 10% window is more local in time but averages fewer late-active "
            "observations; it is not automatically a better physical summary."
        ),
        "T2": (
            "A 30% window includes more of the earlier transient and changes "
            "the late-active quantity."
        ),
        "T3": (
            "The 85% cutoff is a scientifically plausible conservative "
            "domain-exit control, but it measures an earlier active state."
        ),
        "T4": (
            "The 95% cutoff moves closer to domain exit and therefore weakens "
            "the existing contamination safeguard."
        ),
        "T5": (
            "The final-50 reference is not domain controlled and may include "
            "shutdown or post-exit behaviour."
        ),
    }
    for target in TARGET_KEYS:
        distributions = distribution_summary.loc[
            distribution_summary["target"] == target
        ].set_index("target_definition")
        differences = difference_summary.loc[
            difference_summary["target"] == target
        ].set_index("target_definition")
        metrics = model_metrics.loc[model_metrics["target"] == target].set_index(
            "target_definition"
        )
        nuggets = nugget_summary.loc[
            nugget_summary["target"] == target
        ].set_index("target_definition")
        t0_distribution = distributions.loc["T0"]
        t0_metric = metrics.loc["T0"]
        t0_nugget = nuggets.loc["T0"]
        eligible_alternatives: list[str] = []
        evaluations: dict[str, Any] = {}
        for alternative in TARGET_DEFINITION_CODES[1:]:
            distribution = distributions.loc[alternative]
            metric = metrics.loc[alternative]
            comparison = predictability_comparisons.loc[
                (predictability_comparisons["target"] == target)
                & (
                    predictability_comparisons[
                        "alternative_target_definition"
                    ]
                    == alternative
                )
            ].iloc[0]
            equal_or_better_availability = bool(
                int(distribution["availability_count"])
                >= int(t0_distribution["availability_count"])
            )
            equal_or_better_stability = bool(
                float(distribution["fraction_unstable_windows"])
                <= float(t0_distribution["fraction_unstable_windows"])
            )
            robustly_improved_predictability = bool(
                comparison[
                    "alternative_robust_mae_predictability_advantage"
                ]
                and comparison[
                    "alternative_robust_rmse_predictability_advantage"
                ]
            )
            no_shutdown_or_exit_contamination = bool(
                alternative != "T5"
                and int(
                    distribution[
                        "simulations_with_rows_after_full_domain_exit"
                    ]
                )
                == 0
            )
            optimization_stable = bool(
                int(metric["failed_folds"]) == 0
                and int(metric["optimizer_warning_folds"])
                <= max(1, math.floor(0.05 * EXPECTED_POPULATION_SIZES[target]))
                and int(metric["any_bound_hit_folds"])
                <= math.floor(0.10 * EXPECTED_POPULATION_SIZES[target])
            )
            eligible = bool(
                physically_eligible[alternative]
                and equal_or_better_availability
                and equal_or_better_stability
                and robustly_improved_predictability
                and no_shutdown_or_exit_contamination
                and optimization_stable
            )
            if eligible:
                eligible_alternatives.append(alternative)
            evaluations[alternative] = {
                "physical_interpretation_equal_or_better": (
                    physically_eligible[alternative]
                ),
                "physical_note": physical_notes[alternative],
                "equal_or_better_availability": equal_or_better_availability,
                "equal_or_better_temporal_stability": equal_or_better_stability,
                "robustly_improved_predictability": (
                    robustly_improved_predictability
                ),
                "no_shutdown_or_exit_contamination": (
                    no_shutdown_or_exit_contamination
                ),
                "optimizer_stable": optimization_stable,
                "eligible": eligible,
            }
        if eligible_alternatives:
            selected = min(
                eligible_alternatives,
                key=lambda code: float(metrics.loc[code, "nrmse"]),
            )
            changed_quantity = (
                "The selected target is the late-active response at an earlier "
                "85% +X-domain cutoff rather than at the current 90% cutoff."
                if selected == "T3"
                else f"The selected physical quantity changes to {selected}."
            )
            rationale = (
                f"{selected} uniquely satisfies the physical, stability, "
                "availability, paired-predictability, contamination, and "
                "optimization criteria."
            )
        else:
            selected = "T0"
            changed_quantity = "None; retain the current late-active T0 quantity."
            rationale = (
                "No alternative jointly improves physical interpretation, "
                "temporal stability, availability, paired predictability, and "
                "domain-exit control. T0 is retained; large shifts, if present, "
                "are reported as target-definition uncertainty."
            )
        alternative_differences = differences.loc[
            [code for code in TARGET_DEFINITION_CODES if code != "T0"]
        ]
        substantial_sensitivity = bool(
            (
                alternative_differences[
                    "fraction_absolute_difference_exceeds_current_learned_nugget_std"
                ]
                > 0.25
            ).any()
            or (
                alternative_differences[
                    "fraction_absolute_difference_exceeds_5pct_t0"
                ]
                > 0.25
            ).any()
        )
        t0_nugget_std = float(t0_nugget["nugget_std_um_median"])
        if np.isfinite(t0_nugget_std) and t0_nugget_std > 0:
            nugget_change_fraction = float(
                np.nanmax(
                    np.abs(
                        nuggets["nugget_std_um_median"].to_numpy(float)
                        - t0_nugget_std
                    )
                    / t0_nugget_std
                )
            )
        else:
            nugget_change_fraction = np.nan
        nrmse_change_fraction = float(
            np.max(
                np.abs(
                    metrics["nrmse"].to_numpy(float)
                    - float(t0_metric["nrmse"])
                )
                / max(float(t0_metric["nrmse"]), 1e-12)
            )
        )
        fixed_gp_conclusion_materially_sensitive = bool(
            (
                np.isfinite(nugget_change_fraction)
                and nugget_change_fraction > 0.50
            )
            or nrmse_change_fraction > 0.25
        )
        rows.append(
            {
                "target": target,
                "target_label": TARGET_LABELS[target],
                "selected_target_definition": selected,
                "selected_target_definition_label": (
                    TARGET_DEFINITION_BY_CODE[selected].label
                ),
                "t0_retained": selected == "T0",
                "eligible_alternatives": json_compact(eligible_alternatives),
                "alternative_evaluations": json_compact(evaluations),
                "decision_rule": (
                    "retain T0 unless an alternative has equal/better physical "
                    "meaning, stability and availability, robustly improved "
                    "predictability, no new contamination, and stable optimization"
                ),
                "rationale": rationale,
                "physical_quantity_change": changed_quantity,
                "target_definition_sensitivity_substantial": (
                    substantial_sensitivity
                ),
                "maximum_nugget_std_relative_change_across_definitions": (
                    nugget_change_fraction
                ),
                "maximum_nrmse_relative_change_across_definitions": (
                    nrmse_change_fraction
                ),
                "fixed_gp_performance_or_nugget_materially_sensitive": (
                    fixed_gp_conclusion_materially_sensitive
                ),
                "kernel_preference_researched_per_definition": False,
                "interpretation_limit": (
                    "The GP family was intentionally held fixed, so Phase 3C "
                    "tests target sensitivity rather than re-searching kernel "
                    "preference for each definition."
                ),
            }
        )
    return pd.DataFrame(rows)


def build_phase3c_outputs(
    target_table: pd.DataFrame,
    distribution_summary: pd.DataFrame,
    difference_summary: pd.DataFrame,
    phase3b_outputs: dict[str, pd.DataFrame],
    phase3b_prediction_frames: dict[str, pd.DataFrame],
    *,
    workers: int,
    force: bool,
) -> dict[str, pd.DataFrame]:
    started = time.perf_counter()
    provisional = phase3b_outputs["provisional"].set_index("target")
    frames: list[pd.DataFrame] = []
    for target in TARGET_KEYS:
        selected_name = str(
            provisional.loc[
                target, "selected_provisional_gp_configuration"
            ]
        )
        configuration = GP_CONFIG_BY_NAME[selected_name]
        for definition in TARGET_DEFINITION_CODES:
            if definition == "T0":
                source = phase3b_prediction_frames[
                    f"{target}|{selected_name}"
                ].copy()
                source["source_analysis_label"] = source["analysis_label"]
                source["analysis_label"] = (
                    "phase3c_fixed_gp_target_definition_sensitivity"
                )
                source["phase"] = "Phase 3C"
                source["source_phase3b_t0_rows_reused_without_refit"] = True
                frames.append(source)
                RUNTIME_EVENTS.append(
                    {
                        "stage": "phase3c_t0_reuse",
                        "target": target,
                        "target_definition": "T0",
                        "configuration": selected_name,
                        "cache_reused": True,
                        "source": "Phase 3B exact T0 LOO rows",
                        "wall_runtime_seconds": 0.0,
                        "fold_count": len(source),
                    }
                )
                continue
            modelling = target_definition_modelling_table(
                target_table, target, definition
            )
            result = run_gp_loo(
                modelling,
                target=target,
                target_definition=definition,
                analysis_label=(
                    "phase3c_fixed_gp_target_definition_sensitivity"
                ),
                configuration=configuration,
                workers=workers,
                force=force,
            )
            frames.append(result)
    predictions = pd.concat(frames, ignore_index=True).sort_values(
        ["target", "target_definition", "fold_index"]
    )
    metrics = build_gp_metrics(predictions)
    nuggets = build_target_definition_nugget_summary(predictions)
    comparison_rows: list[dict[str, Any]] = []
    for target in TARGET_KEYS:
        for alternative in TARGET_DEFINITION_CODES[1:]:
            comparison_rows.append(
                target_definition_predictability_comparison(
                    predictions,
                    target=target,
                    alternative_definition=alternative,
                )
            )
    comparisons = pd.DataFrame(comparison_rows).sort_values(
        ["target", "alternative_target_definition"]
    )
    decisions = choose_target_definitions(
        distribution_summary,
        difference_summary,
        metrics,
        nuggets,
        comparisons,
    )
    RUNTIME_EVENTS.append(
        {
            "stage": "phase3c_assembly",
            "cache_reused": False,
            "wall_runtime_seconds": time.perf_counter() - started,
            "prediction_rows": len(predictions),
        }
    )
    return {
        "predictions": predictions.reset_index(drop=True),
        "metrics": metrics.reset_index(drop=True),
        "nuggets": nuggets.reset_index(drop=True),
        "predictability_comparisons": comparisons.reset_index(drop=True),
        "decisions": decisions.reset_index(drop=True),
    }


def build_final_model_decisions(
    phase3a_outputs: dict[str, pd.DataFrame],
    phase3b_outputs: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    phase3a_predictions = phase3a_outputs["predictions"]
    phase3a_metrics = phase3a_outputs["metrics"]
    gp_predictions = phase3b_outputs["predictions"]
    gp_metrics = phase3b_outputs["metrics"]
    provisional = phase3b_outputs["provisional"].set_index("target")
    within_bootstrap = phase3b_outputs["bootstrap_summary"].loc[
        phase3b_outputs["bootstrap_summary"]["summary_scope"]
        == "within_kernel"
    ]

    decision_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    for target in TARGET_KEYS:
        selected_gp = str(
            provisional.loc[
                target, "selected_provisional_gp_configuration"
            ]
        )
        selected_gp_rows = gp_predictions.loc[
            (gp_predictions["target"] == target)
            & (gp_predictions["gp_configuration"] == selected_gp)
        ].copy()
        selected_gp_rows["model"] = selected_gp
        simple_rows = phase3a_predictions.loc[
            (phase3a_predictions["target"] == target)
            & phase3a_predictions["model"].isin(
                ["linear_ridge", "polynomial_ridge_degree2"]
            )
        ].copy()
        comparison_frame = pd.concat(
            [selected_gp_rows, simple_rows], ignore_index=True, sort=False
        )
        selected_gp_metric = gp_metrics.loc[
            (gp_metrics["target"] == target)
            & (gp_metrics["gp_configuration"] == selected_gp)
        ].iloc[0]
        practical_threshold = max(
            0.5, 0.05 * float(selected_gp_metric["rmse_um"])
        )
        competitive: list[str] = []
        summaries: dict[str, Any] = {}
        for simple_model in [
            "linear_ridge",
            "polynomial_ridge_degree2",
        ]:
            _, summary = aligned_prediction_comparison(
                comparison_frame,
                target=target,
                model_column="model",
                reference_model=selected_gp,
                candidate_model=simple_model,
                comparison_type=(
                    "final simple model minus provisional robust GP"
                ),
            )
            ci_includes_zero = bool(
                summary["rmse_difference_ci95_lower_um"] <= 0
                <= summary["rmse_difference_ci95_upper_um"]
            )
            practical_negligible = bool(
                abs(summary["observed_rmse_difference_um"])
                <= practical_threshold
            )
            is_competitive = bool(
                ci_includes_zero
                or practical_negligible
                or summary["candidate_robust_rmse_advantage"]
            )
            summary["practical_rmse_difference_threshold_um"] = (
                practical_threshold
            )
            summary["confidence_interval_includes_zero_rmse"] = (
                ci_includes_zero
            )
            summary["practical_difference_negligible"] = practical_negligible
            summary["simple_model_competitive"] = is_competitive
            comparison_rows.append(summary)
            summaries[simple_model] = summary
            if is_competitive:
                competitive.append(simple_model)

        if competitive:
            simple_metric_rows = phase3a_metrics.loc[
                (phase3a_metrics["target"] == target)
                & phase3a_metrics["model"].isin(competitive)
            ].set_index("model")
            best_simple = min(
                competitive,
                key=lambda name: float(
                    simple_metric_rows.loc[name, "rmse_um"]
                ),
            )
            if (
                "linear_ridge" in competitive
                and float(simple_metric_rows.loc["linear_ridge", "rmse_um"])
                <= float(simple_metric_rows.loc[best_simple, "rmse_um"])
                + practical_threshold
            ):
                selected_final = "linear_ridge"
            else:
                selected_final = best_simple
            final_model_family = "simple regression"
            final_metric = simple_metric_rows.loc[selected_final]
            rationale = (
                f"{selected_final} is statistically or practically competitive "
                "with the provisional GP. The simpler point model is selected "
                "for parsimony; it does not supply GP-style predictive intervals."
            )
            learned_nugget_required_for_final = False
            selected_gp_operationally_retained_for_uncertainty = True
        else:
            selected_final = selected_gp
            final_model_family = "Gaussian process"
            final_metric = selected_gp_metric
            rationale = (
                "Neither Ridge baseline is statistically or practically "
                "competitive with the provisional robust GP; retain the GP."
            )
            learned_nugget_required_for_final = bool(
                GP_CONFIG_BY_NAME[selected_gp].learned_nugget
            )
            selected_gp_operationally_retained_for_uncertainty = False

        selected_configuration = GP_CONFIG_BY_NAME[selected_gp]
        if selected_configuration.kernel_family == "RBF":
            family_label = "RBF"
        elif selected_configuration.matern_nu == 1.5:
            family_label = "Matérn 3/2"
        else:
            family_label = "Matérn 5/2"
        no_nugget_name = selected_gp.replace(
            "_learned_nugget", "_no_nugget"
        )
        learned_name = selected_gp.replace(
            "_no_nugget", "_learned_nugget"
        )
        family_comparison = within_bootstrap.loc[
            (within_bootstrap["target"] == target)
            & (
                within_bootstrap["reference_model"]
                == no_nugget_name
            )
            & (within_bootstrap["candidate_model"] == learned_name)
        ]
        if len(family_comparison) == 1:
            family_nugget_conclusion = str(
                family_comparison.iloc[0]["nugget_conclusion"]
            )
            learned_nugget_robustly_helps_selected_gp_family = bool(
                family_comparison.iloc[0][
                    "candidate_robust_mae_advantage"
                ]
                and family_comparison.iloc[0][
                    "candidate_robust_rmse_advantage"
                ]
            )
        else:
            family_nugget_conclusion = "not available"
            learned_nugget_robustly_helps_selected_gp_family = False

        statistically_nonrobust = [
            model
            for model, summary in summaries.items()
            if summary["confidence_interval_includes_zero_rmse"]
        ]
        decision_rows.append(
            {
                "target": target,
                "target_label": TARGET_LABELS[target],
                "selected_final_model": selected_final,
                "selected_final_model_family": final_model_family,
                "selected_provisional_gp": selected_gp,
                "selected_provisional_gp_label": GP_CONFIG_BY_NAME[
                    selected_gp
                ].label,
                "selected_gp_kernel_family": family_label,
                "simple_models_competitive": json_compact(competitive),
                "statistically_nonrobust_gp_vs_simple_rmse_differences": (
                    json_compact(statistically_nonrobust)
                ),
                "practical_rmse_difference_threshold_um": (
                    practical_threshold
                ),
                "selected_final_mae_um": float(final_metric["mae_um"]),
                "selected_final_rmse_um": float(final_metric["rmse_um"]),
                "selected_final_r2": float(final_metric["r2"]),
                "selected_final_nrmse": float(final_metric["nrmse"]),
                "learned_nugget_required_by_selected_final_model": (
                    learned_nugget_required_for_final
                ),
                "learned_nugget_robustly_helps_selected_gp_family": (
                    learned_nugget_robustly_helps_selected_gp_family
                ),
                "selected_gp_family_nugget_conclusion": (
                    family_nugget_conclusion
                ),
                "provisional_gp_retained_as_uncertainty_model_when_simple_selected": (
                    selected_gp_operationally_retained_for_uncertainty
                ),
                "rationale": rationale,
                "uncertainty_limit_for_simple_model": (
                    "Ridge supplies point predictions only in this Phase 3 "
                    "comparison; GP uncertainty diagnostics are not transferred "
                    "to Ridge."
                    if final_model_family == "simple regression"
                    else ""
                ),
            }
        )
    return (
        pd.DataFrame(decision_rows),
        pd.DataFrame(comparison_rows).sort_values(
            ["target", "candidate_model"]
        ),
    )


def _save_figure(fig: plt.Figure, filename: str) -> Path:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURE_DIR / filename
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


MODEL_COLORS = {
    "training_mean": "#9CA3AF",
    "linear_ridge": "#3B82F6",
    "polynomial_ridge_degree2": "#8B5CF6",
    CURRENT_GP_CONFIG_NAME: "#E11D48",
}
GP_COLORS = {
    "rbf_no_nugget": "#93C5FD",
    "rbf_learned_nugget": "#2563EB",
    "matern32_no_nugget": "#FDA4AF",
    "matern32_learned_nugget": "#E11D48",
    "matern52_no_nugget": "#86EFAC",
    "matern52_learned_nugget": "#16A34A",
}


def plot_experiment_tree() -> Path:
    fig, ax = plt.subplots(figsize=(11, 5.8))
    ax.axis("off")
    root_box = dict(boxstyle="round,pad=0.5", fc="#111827", ec="#111827")
    child_colors = ["#DBEAFE", "#FFE4E6", "#DCFCE7"]
    ax.text(
        0.5,
        0.83,
        "Phase 3\nModel-and-target robustness",
        ha="center",
        va="center",
        color="white",
        fontsize=15,
        fontweight="bold",
        bbox=root_box,
        transform=ax.transAxes,
    )
    children = [
        (
            0.18,
            "Phase 3A\nSimple-model test",
            "Mean, Ridge,\nPolynomial Ridge, GP",
        ),
        (
            0.50,
            "Phase 3B\nKernel/nugget test",
            "RBF, Matérn 3/2,\nMatérn 5/2 × nugget",
        ),
        (
            0.82,
            "Phase 3C\nTarget-definition test",
            "T0–T5 with one\nfixed GP per response",
        ),
    ]
    for (x, title, subtitle), color in zip(children, child_colors):
        ax.annotate(
            "",
            xy=(x, 0.59),
            xytext=(0.5, 0.75),
            xycoords=ax.transAxes,
            textcoords=ax.transAxes,
            arrowprops=dict(arrowstyle="-|>", lw=2, color="#4B5563"),
        )
        ax.text(
            x,
            0.43,
            f"{title}\n\n{subtitle}",
            ha="center",
            va="center",
            fontsize=12,
            bbox=dict(
                boxstyle="round,pad=0.6", fc=color, ec="#374151", lw=1.5
            ),
            transform=ax.transAxes,
        )
    ax.text(
        0.5,
        0.06,
        "Strictly deferred: feature effects, ARD, active learning, "
        "level-set estimation, kinetic energy, and total height",
        ha="center",
        va="center",
        fontsize=10,
        color="#4B5563",
        transform=ax.transAxes,
    )
    fig.suptitle("Week 6 Phase 3 experiment tree", fontsize=17, y=0.98)
    return _save_figure(fig, "01_phase3_experiment_tree.png")


def plot_simple_model_performance(metrics: pd.DataFrame) -> Path:
    model_order = [
        "training_mean",
        "linear_ridge",
        "polynomial_ridge_degree2",
        CURRENT_GP_CONFIG_NAME,
    ]
    labels = ["Mean", "Ridge", "Polynomial Ridge", "Current GP"]
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), constrained_layout=True)
    for column, target in enumerate(TARGET_KEYS):
        subset = metrics.loc[metrics["target"] == target].set_index("model")
        for row, (metric, unit) in enumerate(
            [("rmse_um", "RMSE (µm)"), ("mae_um", "MAE (µm)")]
        ):
            ax = axes[row, column]
            values = [float(subset.loc[name, metric]) for name in model_order]
            bars = ax.bar(
                np.arange(len(model_order)),
                values,
                color=[MODEL_COLORS[name] for name in model_order],
            )
            ax.set_xticks(np.arange(len(model_order)), labels, rotation=25, ha="right")
            ax.set_ylabel(unit)
            ax.set_title(f"{TARGET_LABELS[target]} — {unit.split()[0]}")
            ax.grid(axis="y", alpha=0.25)
            for bar, value in zip(bars, values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height(),
                    f"{value:.2f}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )
    fig.suptitle(
        "Phase 3A: exact-LOO simple-model performance (lower is better)",
        fontsize=16,
    )
    return _save_figure(fig, "02_simple_model_performance_comparison.png")


def plot_gp_kernel_rmse(metrics: pd.DataFrame) -> Path:
    order = [item.name for item in GP_CONFIGURATIONS]
    short_labels = [
        "RBF\nno nugget",
        "RBF\n+nugget",
        "M3/2\nno nugget",
        "M3/2\n+nugget",
        "M5/2\nno nugget",
        "M5/2\n+nugget",
    ]
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), constrained_layout=True)
    for ax, target in zip(axes, TARGET_KEYS):
        subset = metrics.loc[metrics["target"] == target].set_index(
            "gp_configuration"
        )
        values = [float(subset.loc[name, "rmse_um"]) for name in order]
        bars = ax.bar(
            range(len(order)),
            values,
            color=[GP_COLORS[name] for name in order],
        )
        ax.set_xticks(range(len(order)), short_labels, rotation=20, ha="right")
        ax.set_ylabel("RMSE (µm)")
        ax.set_title(TARGET_LABELS[target])
        ax.grid(axis="y", alpha=0.25)
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value,
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )
    fig.suptitle(
        "Phase 3B: GP kernel/noise exact-LOO RMSE", fontsize=16
    )
    return _save_figure(fig, "03_gp_kernel_noise_rmse_comparison.png")


def plot_nugget_paired_intervals(bootstrap: pd.DataFrame) -> Path:
    within = bootstrap.loc[bootstrap["summary_scope"] == "within_kernel"].copy()
    family_order = ["RBF", "Matérn 3/2", "Matérn 5/2"]
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), constrained_layout=True)
    for ax, target in zip(axes, TARGET_KEYS):
        subset = within.loc[within["target"] == target].set_index(
            "kernel_family_comparison"
        )
        for offset, (metric, marker, color) in enumerate(
            [("mae", "o", "#2563EB"), ("rmse", "s", "#E11D48")]
        ):
            centers = np.array(
                [
                    float(
                        subset.loc[
                            family,
                            f"observed_{metric}_difference_um",
                        ]
                    )
                    for family in family_order
                ]
            )
            lower = np.array(
                [
                    float(
                        subset.loc[
                            family,
                            f"{metric}_difference_ci95_lower_um",
                        ]
                    )
                    for family in family_order
                ]
            )
            upper = np.array(
                [
                    float(
                        subset.loc[
                            family,
                            f"{metric}_difference_ci95_upper_um",
                        ]
                    )
                    for family in family_order
                ]
            )
            y = np.arange(len(family_order)) + (offset - 0.5) * 0.16
            ax.errorbar(
                centers,
                y,
                xerr=np.vstack([centers - lower, upper - centers]),
                fmt=marker,
                color=color,
                capsize=3,
                label=metric.upper(),
            )
        ax.axvline(0.0, color="#111827", lw=1, ls="--")
        ax.set_yticks(range(len(family_order)), family_order)
        ax.set_xlabel("Learned nugget − no nugget (µm)")
        ax.set_title(TARGET_LABELS[target])
        ax.grid(axis="x", alpha=0.25)
        ax.legend()
    fig.suptitle(
        "Phase 3B: paired 95% bootstrap confidence intervals\n"
        "Negative values favor the learned nugget",
        fontsize=16,
    )
    return _save_figure(
        fig, "04_nugget_vs_no_nugget_paired_confidence_intervals.png"
    )


def plot_provisional_observed_vs_predicted(
    predictions: pd.DataFrame, provisional: pd.DataFrame
) -> Path:
    decisions = provisional.set_index("target")
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
    for ax, target in zip(axes, TARGET_KEYS):
        configuration = decisions.loc[
            target, "selected_provisional_gp_configuration"
        ]
        subset = predictions.loc[
            (predictions["target"] == target)
            & (predictions["gp_configuration"] == configuration)
        ]
        observed = subset["observed_target_um"].to_numpy(float)
        predicted = subset["predicted_mean_um"].to_numpy(float)
        limits = [
            min(observed.min(), predicted.min()),
            max(observed.max(), predicted.max()),
        ]
        ax.scatter(
            observed,
            predicted,
            s=28,
            alpha=0.75,
            color=GP_COLORS.get(configuration, "#E11D48"),
            edgecolor="white",
            linewidth=0.4,
        )
        ax.plot(limits, limits, "--", color="#111827", lw=1.2, label="Ideal")
        ax.set_xlim(limits)
        ax.set_ylim(limits)
        ax.set_xlabel("Observed target (µm)")
        ax.set_ylabel("LOO-predicted target (µm)")
        ax.set_title(
            f"{TARGET_LABELS[target]}\n"
            f"{GP_CONFIG_BY_NAME[str(configuration)].label}"
        )
        ax.grid(alpha=0.2)
        ax.legend()
    fig.suptitle(
        "Phase 3B: observed versus exact-LOO prediction for provisional GPs",
        fontsize=16,
    )
    return _save_figure(
        fig, "05_provisional_models_observed_vs_loo_predicted.png"
    )


def plot_learned_nugget_by_kernel(
    nugget_summary: pd.DataFrame,
) -> Path:
    learned_order = [
        "rbf_learned_nugget",
        "matern32_learned_nugget",
        "matern52_learned_nugget",
    ]
    labels = ["RBF", "Matérn 3/2", "Matérn 5/2"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8), constrained_layout=True)
    for ax, target in zip(axes, TARGET_KEYS):
        subset = nugget_summary.loc[
            nugget_summary["target"] == target
        ].set_index("gp_configuration")
        medians = [
            float(subset.loc[name, "nugget_std_um_median"])
            for name in learned_order
        ]
        q25 = [
            float(subset.loc[name, "nugget_std_um_q25"])
            for name in learned_order
        ]
        q75 = [
            float(subset.loc[name, "nugget_std_um_q75"])
            for name in learned_order
        ]
        ax.bar(
            range(3),
            medians,
            yerr=np.vstack(
                [np.array(medians) - np.array(q25), np.array(q75) - np.array(medians)]
            ),
            capsize=4,
            color=["#2563EB", "#E11D48", "#16A34A"],
        )
        ax.set_xticks(range(3), labels, rotation=20, ha="right")
        ax.set_ylabel("Learned nugget standard deviation (µm)")
        ax.set_title(TARGET_LABELS[target])
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle(
        "Phase 3B: learned effective nugget by kernel (median and IQR)",
        fontsize=16,
    )
    return _save_figure(
        fig, "06_learned_nugget_std_by_kernel_and_target.png"
    )


def plot_target_definition_scatter(
    target_table: pd.DataFrame,
) -> list[Path]:
    paths: list[Path] = []
    modelling = target_table.loc[
        target_table["in_target_modelling_population"].astype(bool)
    ]
    for target in TARGET_KEYS:
        subset = modelling.loc[modelling["target"] == target]
        pivot = subset.pivot(
            index="simulation_id",
            columns="target_definition",
            values="target_value_um",
        )
        fig, axes = plt.subplots(
            2, 3, figsize=(13, 8), constrained_layout=True
        )
        axes_flat = axes.ravel()
        for ax, alternative in zip(axes_flat, TARGET_DEFINITION_CODES[1:]):
            current = pivot["T0"].to_numpy(float)
            other = pivot[alternative].to_numpy(float)
            limits = [min(current.min(), other.min()), max(current.max(), other.max())]
            ax.scatter(
                current,
                other,
                s=22,
                alpha=0.65,
                color="#4F46E5",
                edgecolor="none",
            )
            ax.plot(limits, limits, "--", color="#111827", lw=1)
            ax.set_xlim(limits)
            ax.set_ylim(limits)
            ax.set_xlabel("T0 target (µm)")
            ax.set_ylabel(f"{alternative} target (µm)")
            ax.set_title(
                f"T0 versus {alternative}\n"
                f"{TARGET_DEFINITION_BY_CODE[alternative].label.split(':')[0]}"
            )
            ax.grid(alpha=0.2)
        axes_flat[-1].axis("off")
        fig.suptitle(
            f"Phase 3C: current versus alternative definitions — "
            f"{TARGET_LABELS[target]}",
            fontsize=16,
        )
        paths.append(
            _save_figure(
                fig,
                f"07_target_definition_scatter_{target}.png",
            )
        )
    return paths


def plot_target_absolute_differences(
    target_table: pd.DataFrame,
) -> Path:
    modelling = target_table.loc[
        target_table["in_target_modelling_population"].astype(bool)
    ]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
    for ax, target in zip(axes, TARGET_KEYS):
        pivot = modelling.loc[
            modelling["target"] == target
        ].pivot(
            index="simulation_id",
            columns="target_definition",
            values="target_value_um",
        )
        differences = [
            np.abs(pivot[definition] - pivot["T0"]).to_numpy(float)
            for definition in TARGET_DEFINITION_CODES[1:]
        ]
        boxes = ax.boxplot(
            differences,
            tick_labels=TARGET_DEFINITION_CODES[1:],
            patch_artist=True,
            showfliers=False,
        )
        for patch, color in zip(
            boxes["boxes"],
            ["#60A5FA", "#A78BFA", "#34D399", "#FBBF24", "#F87171"],
        ):
            patch.set_facecolor(color)
            patch.set_alpha(0.75)
        ax.set_ylabel("Absolute difference from T0 (µm)")
        ax.set_xlabel("Alternative target definition")
        ax.set_title(TARGET_LABELS[target])
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle(
        "Phase 3C: target-definition absolute-shift distributions",
        fontsize=16,
    )
    return _save_figure(
        fig, "08_target_definition_absolute_difference_distributions.png"
    )


def plot_stability_vs_predictability(
    distribution_summary: pd.DataFrame,
    model_metrics: pd.DataFrame,
) -> Path:
    merged = distribution_summary.merge(
        model_metrics[
            ["target", "target_definition", "nrmse"]
        ],
        on=["target", "target_definition"],
        validate="one_to_one",
    )
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
    colors = {
        code: color
        for code, color in zip(
            TARGET_DEFINITION_CODES,
            ["#111827", "#60A5FA", "#A78BFA", "#34D399", "#FBBF24", "#F87171"],
        )
    }
    for ax, target in zip(axes, TARGET_KEYS):
        subset = merged.loc[merged["target"] == target]
        for _, row in subset.iterrows():
            code = str(row["target_definition"])
            ax.scatter(
                float(row["fraction_unstable_windows"]),
                float(row["nrmse"]),
                s=75 if code == "T0" else 55,
                color=colors[code],
                edgecolor="white",
                linewidth=0.6,
            )
            ax.annotate(
                code,
                (
                    float(row["fraction_unstable_windows"]),
                    float(row["nrmse"]),
                ),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=9,
            )
        ax.set_xlabel("Fraction of unstable windows")
        ax.set_ylabel("Exact-LOO nRMSE")
        ax.set_title(TARGET_LABELS[target])
        ax.grid(alpha=0.25)
    fig.suptitle(
        "Phase 3C: temporal stability versus fixed-GP predictability\n"
        "Lower-left is preferable, but physical meaning remains decisive",
        fontsize=16,
    )
    return _save_figure(
        fig, "09_target_stability_vs_predictability.png"
    )


def plot_nugget_vs_target_shift(
    difference_summary: pd.DataFrame,
) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
    for ax, target in zip(axes, TARGET_KEYS):
        subset = difference_summary.loc[
            (difference_summary["target"] == target)
            & (difference_summary["target_definition"] != "T0")
        ].set_index("target_definition")
        shifts = [
            float(
                subset.loc[
                    code, "median_absolute_difference_from_t0_um"
                ]
            )
            for code in TARGET_DEFINITION_CODES[1:]
        ]
        nugget = float(
            subset.iloc[0][
                "current_matern32_learned_nugget_std_median_um"
            ]
        )
        ax.bar(
            range(5),
            shifts,
            color=["#60A5FA", "#A78BFA", "#34D399", "#FBBF24", "#F87171"],
            label="Median |target shift|",
        )
        ax.axhline(
            nugget,
            color="#E11D48",
            lw=2,
            ls="--",
            label="Current GP nugget std",
        )
        ax.set_xticks(range(5), TARGET_DEFINITION_CODES[1:])
        ax.set_ylabel("Scale (µm)")
        ax.set_title(TARGET_LABELS[target])
        ax.grid(axis="y", alpha=0.25)
        ax.legend(fontsize=8)
    fig.suptitle(
        "Phase 3C: target-definition shift versus learned-nugget scale\n"
        "Descriptive scale comparison only — the quantities are conceptually different",
        fontsize=15,
    )
    return _save_figure(
        fig, "10_learned_nugget_vs_target_definition_shift.png"
    )


def plot_final_scorecard(
    final_models: pd.DataFrame,
    final_targets: pd.DataFrame,
) -> Path:
    merged = final_models.merge(
        final_targets[
            [
                "target",
                "selected_target_definition",
                "target_definition_sensitivity_substantial",
            ]
        ],
        on="target",
        validate="one_to_one",
    )
    rows = []
    for _, row in merged.iterrows():
        rows.append(
            [
                TARGET_LABELS[str(row["target"])],
                str(row["selected_final_model"]),
                str(row["selected_provisional_gp"]),
                (
                    "Yes"
                    if bool(
                        row[
                            "learned_nugget_robustly_helps_selected_gp_family"
                        ]
                    )
                    else "No / uncertain"
                ),
                str(row["selected_target_definition"]),
                (
                    "Substantial"
                    if bool(
                        row[
                            "target_definition_sensitivity_substantial"
                        ]
                    )
                    else "Limited"
                ),
            ]
        )
    fig, ax = plt.subplots(figsize=(14, 4.2))
    ax.axis("off")
    table = ax.table(
        cellText=rows,
        colLabels=[
            "Response",
            "Final point model",
            "Provisional GP",
            "Nugget helps\nselected GP family",
            "Target",
            "Target sensitivity",
        ],
        cellLoc="center",
        colLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 2.0)
    for column in range(6):
        table[(0, column)].set_facecolor("#111827")
        table[(0, column)].set_text_props(color="white", weight="bold")
    for row_index in range(1, len(rows) + 1):
        color = "#F9FAFB" if row_index % 2 else "#EEF2FF"
        for column in range(6):
            table[(row_index, column)].set_facecolor(color)
    fig.suptitle("Week 6 Phase 3 final decision scorecard", fontsize=17)
    return _save_figure(fig, "11_phase3_final_decision_scorecard.png")


def generate_figures(
    phase3a_outputs: dict[str, pd.DataFrame],
    phase3b_outputs: dict[str, pd.DataFrame],
    target_table: pd.DataFrame,
    distribution_summary: pd.DataFrame,
    difference_summary: pd.DataFrame,
    phase3c_outputs: dict[str, pd.DataFrame],
    final_models: pd.DataFrame,
    final_targets: pd.DataFrame,
) -> list[Path]:
    started = time.perf_counter()
    paths = [
        plot_experiment_tree(),
        plot_simple_model_performance(phase3a_outputs["metrics"]),
        plot_gp_kernel_rmse(phase3b_outputs["metrics"]),
        plot_nugget_paired_intervals(
            phase3b_outputs["bootstrap_summary"]
        ),
        plot_provisional_observed_vs_predicted(
            phase3b_outputs["predictions"],
            phase3b_outputs["provisional"],
        ),
        plot_learned_nugget_by_kernel(
            phase3b_outputs["learned_nugget"]
        ),
        *plot_target_definition_scatter(target_table),
        plot_target_absolute_differences(target_table),
        plot_stability_vs_predictability(
            distribution_summary, phase3c_outputs["metrics"]
        ),
        plot_nugget_vs_target_shift(difference_summary),
        plot_final_scorecard(final_models, final_targets),
    ]
    RUNTIME_EVENTS.append(
        {
            "stage": "figure_generation",
            "cache_reused": False,
            "wall_runtime_seconds": time.perf_counter() - started,
            "figure_count": len(paths),
            "figures": [str(path.relative_to(ROOT)) for path in paths],
        }
    )
    return paths


def _markdown_table(
    frame: pd.DataFrame,
    columns: Sequence[str],
    *,
    float_digits: int = 4,
) -> str:
    subset = frame.loc[:, list(columns)].copy()
    headers = [str(column) for column in subset.columns]
    rows: list[list[str]] = []
    for _, item in subset.iterrows():
        formatted: list[str] = []
        for value in item.tolist():
            if isinstance(value, (float, np.floating)):
                formatted.append(
                    "—"
                    if not np.isfinite(float(value))
                    else f"{float(value):.{float_digits}f}"
                )
            else:
                formatted.append(str(value))
        rows.append(formatted)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def build_decision_log(
    phase3a_outputs: dict[str, pd.DataFrame],
    phase3b_outputs: dict[str, pd.DataFrame],
    difference_summary: pd.DataFrame,
    phase3c_outputs: dict[str, pd.DataFrame],
    final_models: pd.DataFrame,
    final_targets: pd.DataFrame,
) -> str:
    phase3a_bootstrap = phase3a_outputs["comparison_summary"]
    within = phase3b_outputs["bootstrap_summary"].loc[
        phase3b_outputs["bootstrap_summary"]["summary_scope"]
        == "within_kernel"
    ]
    lines = [
        "# Week 6 Phase 3 decision log",
        "",
        "## Why these tests were run",
        "",
        "Simple models were tested because a Gaussian process is not justified "
        "merely by being flexible. Ridge supplies a transparent linear baseline, "
        "and degree-2 Polynomial Ridge adds all squares and pairwise interactions "
        "without opening an unrestricted high-degree search. Degree 2 is the "
        "maximum because higher degrees would rapidly expand complexity, become "
        "harder to interpret, and create a new tuning study outside Phase 3.",
        "",
        "ARD was excluded so that kernel comparisons change only smoothness and "
        "nugget treatment. All GP lengthscales remain isotropic. The "
        "ConstantKernel multiplies the base covariance and controls vertical "
        "signal variance; it does not add a constant prediction to the mean. "
        "WhiteKernel is compared inside every family to test whether a learned "
        "effective nugget remains useful under RBF, Matérn 3/2, and Matérn 5/2.",
        "",
        "Target definitions were changed one factor at a time: window duration, "
        "domain cutoff, or the final-50 aggregation. T5 is a reference rather "
        "than an automatic candidate because it is not domain controlled and can "
        "include shutdown or post-exit behaviour. A between-definition shift "
        "changes the measured target; a GP nugget describes unresolved effective "
        "variation under a fixed target/model. Comparing their scales is therefore "
        "descriptive, not an identity.",
        "",
        "## Phase 3A — simple-model evidence",
        "",
    ]
    for target in TARGET_KEYS:
        model_decision = final_models.loc[
            final_models["target"] == target
        ].iloc[0]
        lines.append(f"### {TARGET_LABELS[target]}")
        lines.append("")
        for candidate in ["linear_ridge", "polynomial_ridge_degree2"]:
            comparison = phase3a_bootstrap.loc[
                (phase3a_bootstrap["target"] == target)
                & (phase3a_bootstrap["candidate_model"] == candidate)
            ].iloc[0]
            lines.append(
                f"- {candidate}: candidate − current-GP RMSE "
                f"{comparison['observed_rmse_difference_um']:+.4f} µm, "
                f"95% CI [{comparison['rmse_difference_ci95_lower_um']:+.4f}, "
                f"{comparison['rmse_difference_ci95_upper_um']:+.4f}] µm; "
                f"competitive={bool(comparison['simple_model_competitive'])}."
            )
        lines.extend(
            [
                f"- Final point-model decision: "
                f"`{model_decision['selected_final_model']}`.",
                f"- Reason: {model_decision['rationale']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Phase 3B — kernel and nugget evidence",
            "",
        ]
    )
    for target in TARGET_KEYS:
        provisional = phase3b_outputs["provisional"].loc[
            phase3b_outputs["provisional"]["target"] == target
        ].iloc[0]
        lines.append(f"### {TARGET_LABELS[target]}")
        lines.append("")
        for family in ["RBF", "Matérn 3/2", "Matérn 5/2"]:
            comparison = within.loc[
                (within["target"] == target)
                & (within["kernel_family_comparison"] == family)
            ].iloc[0]
            lines.append(
                f"- {family}, learned nugget − no nugget: RMSE "
                f"{comparison['observed_rmse_difference_um']:+.4f} µm, "
                f"95% CI [{comparison['rmse_difference_ci95_lower_um']:+.4f}, "
                f"{comparison['rmse_difference_ci95_upper_um']:+.4f}] µm; "
                f"{comparison['nugget_conclusion']}."
            )
        lines.extend(
            [
                f"- Provisional robust GP: "
                f"`{provisional['selected_provisional_gp_configuration']}`.",
                f"- Replacement of Matérn 3/2 + nugget: "
                f"{bool(provisional['another_kernel_replaces_current'])}.",
                f"- Reason: {provisional['rationale']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Phase 3C — target-definition evidence",
            "",
        ]
    )
    for target in TARGET_KEYS:
        target_decision = final_targets.loc[
            final_targets["target"] == target
        ].iloc[0]
        target_differences = difference_summary.loc[
            (difference_summary["target"] == target)
            & (difference_summary["target_definition"] != "T0")
        ]
        largest = target_differences.sort_values(
            "median_absolute_difference_from_t0_um", ascending=False
        ).iloc[0]
        lines.extend(
            [
                f"### {TARGET_LABELS[target]}",
                "",
                f"- Largest median absolute shift is "
                f"{largest['target_definition']}: "
                f"{largest['median_absolute_difference_from_t0_um']:.4f} µm "
                f"(q95 {largest['q95_absolute_difference_from_t0_um']:.4f} µm).",
                f"- Selected definition: "
                f"`{target_decision['selected_target_definition']}`.",
                f"- Sensitivity substantial: "
                f"{bool(target_decision['target_definition_sensitivity_substantial'])}.",
                f"- Reason: {target_decision['rationale']}",
                f"- Physical quantity change: "
                f"{target_decision['physical_quantity_change']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Remaining limitations and deferred work",
            "",
            "- Exact LOO measures interpolation/generalization across these "
            "simulation settings; it does not establish causal feature effects.",
            "- A learned nugget can absorb target-definition variability, omitted "
            "structure, kernel mismatch, and numerical/model discrepancy. It is "
            "not evidence of stochastic simulator noise.",
            "- Phase 3C intentionally holds one GP configuration fixed per "
            "response; it does not re-search kernels for every alternative target.",
            "- Target physical validity still depends on the monitor geometry and "
            "the active-domain control assumptions validated in Phase 1.",
            "- Feature effects, ARD, kinetic energy, total height, active learning, "
            "and level-set estimation remain deferred to later explicitly scoped "
            "phases.",
        ]
    )
    return "\n".join(lines)


def build_results_summary(
    *,
    input_provenance: dict[str, Any],
    population_summary: pd.DataFrame,
    phase3a_outputs: dict[str, pd.DataFrame],
    phase3b_outputs: dict[str, pd.DataFrame],
    difference_summary: pd.DataFrame,
    phase3c_outputs: dict[str, pd.DataFrame],
    final_models: pd.DataFrame,
    final_targets: pd.DataFrame,
    validation: pd.DataFrame,
    runtime_provenance: dict[str, Any],
) -> str:
    validation_passes = int((validation["status"] == "PASS").sum())
    lines = [
        "# Week 6 Phase 3 — model-and-target robustness",
        "",
        "## Outcome",
        "",
        "Phase 3 tested whether the learned-nugget GP remains useful relative "
        "to simple regressions, alternative isotropic kernels, and five "
        "reasonable target variants. The tables below separate point-model "
        "parsimony, GP uncertainty, and physical target choice; they are not "
        "collapsed into a single score.",
        "",
        "## Immutable inputs and populations",
        "",
        f"- Branch start: `{EXPECTED_BRANCH}` at `{STARTING_HEAD}`.",
        f"- Phase 1 revision: `{EXPECTED_PHASE1_REVISION}`.",
        f"- Phase 1 ledger SHA-256: `{EXPECTED_PHASE1_LEDGER_SHA256}`.",
        f"- Phase 2.5 decision: "
        f"`{input_provenance['phase2_5_depth_decision']}`.",
        "- Features: exactly `P, VX, LS, ST`; targets converted only from "
        "metres to micrometres.",
        "",
        _markdown_table(
            population_summary,
            [
                "target",
                "population_size",
                "excluded_count",
                "target_min_um",
                "target_median_um",
                "target_max_um",
            ],
        ),
        "",
        "## Phase 3A — simple models",
        "",
        _markdown_table(
            phase3a_outputs["metrics"],
            [
                "target",
                "model",
                "mae_um",
                "median_absolute_error_um",
                "rmse_um",
                "r2",
                "nrmse",
            ],
        ),
        "",
        "A simple model is called competitive when the paired RMSE confidence "
        "interval includes zero, its RMSE difference falls inside the "
        "predeclared practical threshold, or it robustly improves on the GP. "
        "This avoids claiming that GP complexity is necessary on a numerical "
        "difference alone.",
        "",
        _markdown_table(
            phase3a_outputs["comparison_summary"],
            [
                "target",
                "candidate_model",
                "observed_mae_difference_um",
                "mae_difference_ci95_lower_um",
                "mae_difference_ci95_upper_um",
                "observed_rmse_difference_um",
                "rmse_difference_ci95_lower_um",
                "rmse_difference_ci95_upper_um",
                "simple_model_competitive",
            ],
        ),
        "",
        "## Phase 3B — kernel and nugget robustness",
        "",
        _markdown_table(
            phase3b_outputs["metrics"],
            [
                "target",
                "gp_configuration",
                "mae_um",
                "rmse_um",
                "mean_nlpd",
                "latent_95_coverage",
                "total_95_coverage",
                "optimizer_warning_folds",
                "any_bound_hit_folds",
            ],
        ),
        "",
        _markdown_table(
            phase3b_outputs["provisional"],
            [
                "target",
                "selected_provisional_gp_configuration",
                "another_kernel_replaces_current",
                "selected_rmse_um",
                "selected_mean_nlpd",
                "selected_evaluation_95_coverage",
            ],
        ),
        "",
        "## Phase 3C — target-definition sensitivity",
        "",
        _markdown_table(
            difference_summary,
            [
                "target",
                "target_definition",
                "pearson_correlation_with_t0",
                "spearman_correlation_with_t0",
                "median_absolute_difference_from_t0_um",
                "q95_absolute_difference_from_t0_um",
                "fraction_absolute_difference_exceeds_current_learned_nugget_std",
            ],
        ),
        "",
        "Target-definition shifts and learned nugget sizes are conceptually "
        "different. Their scale comparison is descriptive only.",
        "",
        _markdown_table(
            phase3c_outputs["metrics"],
            [
                "target",
                "target_definition",
                "gp_configuration",
                "mae_um",
                "rmse_um",
                "r2",
                "nrmse",
                "mean_nlpd",
                "evaluation_95_coverage",
                "learned_nugget_std_um_median",
            ],
        ),
        "",
        "## Final decisions",
        "",
        _markdown_table(
            final_models,
            [
                "target",
                "selected_final_model",
                "selected_provisional_gp",
                "simple_models_competitive",
                "learned_nugget_robustly_helps_selected_gp_family",
            ],
        ),
        "",
        _markdown_table(
            final_targets,
            [
                "target",
                "selected_target_definition",
                "t0_retained",
                "target_definition_sensitivity_substantial",
                "fixed_gp_performance_or_nugget_materially_sensitive",
            ],
        ),
        "",
        "## Runtime, validation, and repository state",
        "",
        f"- Full invocation wall time recorded so far: "
        f"{runtime_provenance.get('full_invocation_wall_runtime_seconds', np.nan):.2f} s.",
        f"- Cache events: "
        f"{runtime_provenance.get('cache_reused_event_count', 0)} reused, "
        f"{runtime_provenance.get('computed_event_count', 0)} computed.",
        f"- Validation: {validation_passes}/{len(validation)} PASS.",
        "- The notebook is executed separately inside the deterministic rebuild "
        "and final validation confirms zero error outputs.",
        "- No commit or push is part of Phase 3.",
        "- The original dirty worktree is fingerprinted before and after the run.",
    ]
    return "\n".join(lines)


def build_summary_json(
    *,
    input_provenance: dict[str, Any],
    population_summary: pd.DataFrame,
    phase3a_outputs: dict[str, pd.DataFrame],
    phase3b_outputs: dict[str, pd.DataFrame],
    distribution_summary: pd.DataFrame,
    difference_summary: pd.DataFrame,
    phase3c_outputs: dict[str, pd.DataFrame],
    final_models: pd.DataFrame,
    final_targets: pd.DataFrame,
    validation: pd.DataFrame,
    runtime_provenance: dict[str, Any],
) -> dict[str, Any]:
    return {
        "generated_at_utc": utc_now(),
        "phase": "Week 6 Phase 3 model-and-target robustness",
        "repository": current_repository_state(),
        "input_provenance": input_provenance,
        "configuration_fingerprint": scientific_config_fingerprint(),
        "populations": population_summary.to_dict(orient="records"),
        "phase3a": {
            "metrics": phase3a_outputs["metrics"].to_dict(orient="records"),
            "paired_comparisons": phase3a_outputs[
                "comparison_summary"
            ].to_dict(orient="records"),
        },
        "phase3b": {
            "metrics": phase3b_outputs["metrics"].to_dict(orient="records"),
            "paired_bootstrap": phase3b_outputs[
                "bootstrap_summary"
            ].to_dict(orient="records"),
            "learned_nugget": phase3b_outputs[
                "learned_nugget"
            ].to_dict(orient="records"),
            "provisional_decisions": phase3b_outputs[
                "provisional"
            ].to_dict(orient="records"),
        },
        "phase3c": {
            "distribution_summary": distribution_summary.to_dict(
                orient="records"
            ),
            "difference_summary": difference_summary.to_dict(
                orient="records"
            ),
            "model_metrics": phase3c_outputs["metrics"].to_dict(
                orient="records"
            ),
            "nugget_summary": phase3c_outputs["nuggets"].to_dict(
                orient="records"
            ),
            "decisions": phase3c_outputs["decisions"].to_dict(
                orient="records"
            ),
        },
        "final_model_decisions": final_models.to_dict(orient="records"),
        "final_target_decisions": final_targets.to_dict(orient="records"),
        "validation_pass_count": int((validation["status"] == "PASS").sum()),
        "validation_total_count": len(validation),
        "runtime_provenance": runtime_provenance,
        "scope_status": (
            "Phase 3 complete; feature effects, ARD, active learning, "
            "level-set estimation, kinetic energy, and total height deferred."
        ),
    }


REQUIREMENT_MAP: tuple[tuple[str, str, str], ...] = (
    (
        "Repository isolation and immutable-history preflight",
        "Notebook §0 — provenance and scope",
        "phase3_preflight_snapshot.json; phase3_runtime_provenance.json",
    ),
    (
        "Requested Phase 3 branch and unchanged starting HEAD",
        "Notebook §0 — provenance and scope",
        "phase3_preflight_snapshot.json; validation_results.csv",
    ),
    (
        "Exact Phase 1 revision, ledger hash, rows, and decisions",
        "Notebook §0 — provenance and scope",
        "phase3_configuration.json; validation_results.csv",
    ),
    (
        "Phase 1, Phase 2, and Phase 2.5 artifacts unchanged",
        "Notebook §0 — provenance and scope",
        "phase3_runtime_provenance.json; validation_results.csv",
    ),
    (
        "Features exactly P, VX, LS, ST; metre-to-micrometre conversion only",
        "Notebook §0 — common protocol",
        "phase3_configuration.json; phase3_input_population_summary.csv",
    ),
    (
        "Width 241, length 241, exact stable depth 230",
        "Notebook §0 — populations",
        "phase3_input_population_summary.csv; validation_results.csv",
    ),
    (
        "Exact outer LOO, common fold order, fold-local preprocessing",
        "Notebook §0 — common protocol",
        "all three LOO prediction files; validation_results.csv",
    ),
    (
        "Phase 3A training-mean sanity baseline",
        "Notebook Part 1 — Phase 3A",
        "simple_baseline_loo_predictions.csv; simple_baseline_metrics.csv",
    ),
    (
        "Phase 3A Linear Ridge with nested 5-fold tuning",
        "Notebook Part 1 — Phase 3A",
        "simple_baseline_selected_hyperparameters.csv",
    ),
    (
        "Phase 3A degree-2 Polynomial Ridge, no higher degree",
        "Notebook Part 1 — Phase 3A",
        "phase3_configuration.json; simple_baseline_selected_hyperparameters.csv",
    ),
    (
        "Phase 3A logarithmic alpha grid 1e-6 through 1e6",
        "Notebook Part 1 — nested CV",
        "phase3_configuration.json; simple_baseline_selected_hyperparameters.csv",
    ),
    (
        "Phase 3A MAE, median AE, RMSE, R², nRMSE, runtime",
        "Notebook Part 1 — results",
        "simple_baseline_metrics.csv",
    ),
    (
        "Phase 3A aligned 10,000-resample GP-versus-Ridge bootstraps",
        "Notebook Part 1 — paired evidence",
        "simple_baseline_paired_comparisons.csv; simple_baseline_paired_bootstrap_summary.csv",
    ),
    (
        "Six isotropic Phase 3B kernel/noise GP configurations",
        "Notebook Part 2 — Phase 3B",
        "phase3_configuration.json; gp_kernel_noise_loo_predictions.csv",
    ),
    (
        "Common ConstantKernel, lengthscale, WhiteKernel bounds and one restart",
        "Notebook Part 2 — configuration",
        "phase3_configuration.json",
    ),
    (
        "No ARD; comparison isolates smoothness and nugget",
        "Notebook Part 2 — configuration",
        "phase3_configuration.json; validation_results.csv",
    ),
    (
        "ConstantKernel interpretation is explicit",
        "Notebook Part 2 — technical terms",
        "phase3_configuration.json; decision_log.md",
    ),
    (
        "Phase 3B point, uncertainty, calibration, and runtime metrics",
        "Notebook Part 2 — results",
        "gp_kernel_noise_metrics.csv",
    ),
    (
        "Fold-level signal variance, lengthscale, nugget, warnings, and bounds",
        "Notebook Part 2 — diagnostics",
        "gp_kernel_noise_hyperparameter_diagnostics.csv",
    ),
    (
        "Within-family nugget-minus-no-nugget paired comparisons",
        "Notebook Part 2 — paired evidence",
        "within_kernel_nugget_comparisons.csv; gp_kernel_paired_bootstrap_summary.csv",
    ),
    (
        "Every candidate compared with Matérn 3/2 + learned nugget",
        "Notebook Part 2 — paired evidence",
        "gp_candidate_vs_current_comparisons.csv; gp_kernel_paired_bootstrap_summary.csv",
    ),
    (
        "Target-specific provisional GP decision rule",
        "Notebook Part 2 — decisions",
        "provisional_kernel_decision.csv",
    ),
    (
        "Six exact raw-monitor definitions T0–T5",
        "Notebook Part 3 — Phase 3C",
        "target_definition_simulation_level_table.csv",
    ),
    (
        "Raw source paths, hashes, aligned rows, and window traceability",
        "Notebook Part 3 — traceability",
        "target_definition_traceability.csv",
    ),
    (
        "Sentinels excluded and T0–T4 domain cutoffs applied",
        "Notebook Part 3 — traceability",
        "target_definition_traceability.csv; validation_results.csv",
    ),
    (
        "T5 final 50 valid rows, with fewer-than-50 flag",
        "Notebook Part 3 — T5 reference",
        "target_definition_traceability.csv; validation_results.csv",
    ),
    (
        "Availability, distribution, window CV/trend, and instability",
        "Notebook Part 3 — target statistics",
        "target_definition_distribution_summary.csv",
    ),
    (
        "Pearson, Spearman, differences, relative shifts, and thresholds",
        "Notebook Part 3 — target statistics",
        "target_definition_difference_summary.csv",
    ),
    (
        "Nugget-versus-target-shift comparison explicitly descriptive",
        "Notebook Part 3 — interpretation",
        "target_definition_difference_summary.csv; decision_log.md",
    ),
    (
        "One provisional GP held fixed per response across T0–T5",
        "Notebook Part 3 — fixed-model test",
        "target_definition_loo_predictions.csv; validation_results.csv",
    ),
    (
        "Phase 3C point, NLPD, coverage, width, nugget, optimizer metrics",
        "Notebook Part 3 — fixed-model results",
        "target_definition_model_metrics.csv; target_definition_nugget_summary.csv",
    ),
    (
        "Target-definition decision applies physical/stability/availability rule",
        "Notebook Part 3 — target decisions",
        "target_definition_decision.csv; phase3_final_target_decision.csv",
    ),
    (
        "All eleven focused figure requirements",
        "Notebook Parts 1–3 and final scorecard",
        "figures/",
    ),
    (
        "Notebook experiment tree and three visible parts",
        "Notebook title and Parts 1–3",
        "04_phase3_model_target_robustness.ipynb",
    ),
    (
        "Technical terms defined at first use without textbook expansion",
        "Notebook Parts 1–3 — term boxes",
        "04_phase3_model_target_robustness.ipynb",
    ),
    (
        "Markdown explanation follows every major code cell",
        "Entire notebook",
        "04_phase3_model_target_robustness.ipynb; validation_results.csv",
    ),
    (
        "Reusable source has smoke, full, force, workers, checkpoints",
        "Notebook §0 — rebuild command",
        "src/week6_phase3_model_target_robustness.py",
    ),
    (
        "Machine-readable configuration and measured runtime provenance",
        "Notebook §0 and final section",
        "phase3_configuration.json; phase3_runtime_provenance.json",
    ),
    (
        "Automated validation covers all 34 minimum checks",
        "Notebook final validation section",
        "validation_results.csv",
    ),
    (
        "Decision log records all requested scientific reasons and limits",
        "Notebook final decisions",
        "decision_log.md",
    ),
    (
        "Final model and target decisions are response-specific",
        "Notebook final scorecard",
        "phase3_final_model_decision.csv; phase3_final_target_decision.csv",
    ),
    (
        "Strict Phase 3 scope; no Phase 4 or feature-effect work",
        "Notebook §0 and limitations",
        "phase3_configuration.json; validation_results.csv",
    ),
    (
        "No commit, no push, original dirty worktree unchanged",
        "Notebook final repository check",
        "phase3_runtime_provenance.json; validation_results.csv",
    ),
)


def build_requirement_checklist(validation: pd.DataFrame) -> pd.DataFrame:
    validation_passed = bool(
        len(validation) >= 34 and (validation["status"] == "PASS").all()
    )
    rows = [
        {
            "requirement_id": f"P3-{index:02d}",
            "requirement": requirement,
            "notebook_section": notebook_section,
            "evidence_files": evidence,
            "status": "PASS" if validation_passed else "PENDING_FINAL_VALIDATION",
        }
        for index, (requirement, notebook_section, evidence) in enumerate(
            REQUIREMENT_MAP, start=1
        )
    ]
    return pd.DataFrame(rows)


REQUIRED_OUTPUT_FILENAMES = [
    "phase3_preflight_snapshot.json",
    "phase3_configuration.json",
    "phase3_input_population_summary.csv",
    "phase3_runtime_provenance.json",
    "simple_baseline_loo_predictions.csv",
    "simple_baseline_metrics.csv",
    "simple_baseline_selected_hyperparameters.csv",
    "simple_baseline_paired_comparisons.csv",
    "simple_baseline_paired_bootstrap_summary.csv",
    "gp_kernel_noise_loo_predictions.csv",
    "gp_kernel_noise_metrics.csv",
    "gp_kernel_noise_hyperparameter_diagnostics.csv",
    "within_kernel_nugget_comparisons.csv",
    "gp_candidate_vs_current_comparisons.csv",
    "gp_kernel_paired_bootstrap_summary.csv",
    "learned_nugget_by_kernel_summary.csv",
    "provisional_kernel_decision.csv",
    "target_definition_simulation_level_table.csv",
    "target_definition_traceability.csv",
    "target_definition_distribution_summary.csv",
    "target_definition_difference_summary.csv",
    "target_definition_loo_predictions.csv",
    "target_definition_model_metrics.csv",
    "target_definition_nugget_summary.csv",
    "target_definition_decision.csv",
    "phase3_final_model_decision.csv",
    "phase3_final_target_decision.csv",
    "phase3_requirement_checklist.csv",
    "validation_results.csv",
    "decision_log.md",
    "results_summary.md",
    "summary.json",
]


def _check_notebook() -> tuple[bool, str, bool, str]:
    if not NOTEBOOK_PATH.exists():
        return False, "notebook missing", False, "notebook missing"
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    cells = notebook.get("cells", [])
    code_cells = [cell for cell in cells if cell.get("cell_type") == "code"]
    errors = [
        output
        for cell in code_cells
        for output in cell.get("outputs", [])
        if output.get("output_type") == "error"
    ]
    executed = bool(code_cells) and all(
        cell.get("execution_count") is not None for cell in code_cells
    )
    execution_passed = bool(executed and not errors)
    explanation_failures: list[int] = []
    for index, cell in enumerate(cells):
        if cell.get("cell_type") != "code":
            continue
        if index + 1 >= len(cells) or cells[index + 1].get("cell_type") != "markdown":
            explanation_failures.append(index)
    explanations_passed = not explanation_failures
    return (
        execution_passed,
        f"code_cells={len(code_cells)}; executed={executed}; errors={len(errors)}",
        explanations_passed,
        f"code_cells_without_following_markdown={explanation_failures}",
    )


def _metric_values_match(
    predictions: pd.DataFrame,
    metrics: pd.DataFrame,
    *,
    model_column: str,
) -> tuple[bool, str]:
    mismatches: list[str] = []
    grouping = ["target", "target_definition", model_column]
    for keys, subset in predictions.groupby(grouping, sort=True):
        target, definition, model = keys
        stored = metrics.loc[
            (metrics["target"] == target)
            & (metrics["target_definition"] == definition)
            & (metrics[model_column] == model)
        ]
        if len(stored) != 1:
            mismatches.append(f"{keys}:stored_rows={len(stored)}")
            continue
        observed = subset["observed_target_um"].to_numpy(float)
        predicted = subset["predicted_mean_um"].to_numpy(float)
        residual = observed - predicted
        expected = {
            "mae_um": float(np.mean(np.abs(residual))),
            "median_absolute_error_um": float(np.median(np.abs(residual))),
            "rmse_um": float(np.sqrt(np.mean(residual**2))),
            "r2": float(r2_score(observed, predicted)),
            "nrmse": float(
                np.sqrt(np.mean(residual**2))
                / (observed.max() - observed.min())
            ),
        }
        row = stored.iloc[0]
        for column, value in expected.items():
            if not math.isclose(
                float(row[column]), value, rel_tol=1e-10, abs_tol=1e-10
            ):
                mismatches.append(
                    f"{keys}:{column} stored={row[column]} expected={value}"
                )
    return not mismatches, f"mismatches={mismatches[:8]}"


def _fold_scalers_match(
    predictions: pd.DataFrame,
    target_table: pd.DataFrame,
    populations: dict[str, pd.DataFrame],
) -> tuple[bool, str]:
    mismatches: list[str] = []
    checked = 0
    table_cache: dict[tuple[str, str], pd.DataFrame] = {}
    for target in TARGET_KEYS:
        table_cache[(target, "T0")] = population_t0_modelling_table(
            populations[target], target
        ).sort_values("numeric_simulation_id").reset_index(drop=True)
        for definition in TARGET_DEFINITION_CODES[1:]:
            table_cache[(target, definition)] = (
                target_definition_modelling_table(
                    target_table, target, definition
                )
                .sort_values("numeric_simulation_id")
                .reset_index(drop=True)
            )
    scalable = predictions.loc[
        predictions["x_training_mean"].notna()
        & predictions["training_y_mean_um"].notna()
    ]
    for _, row in scalable.iterrows():
        target = str(row["target"])
        definition = str(row["target_definition"])
        table = table_cache[(target, definition)]
        fold_index = int(row["fold_index"])
        if fold_index < 0 or fold_index >= len(table):
            mismatches.append(f"{target}/{definition}:bad_fold={fold_index}")
            continue
        heldout = str(table.loc[fold_index, "simulation_id"])
        if heldout != str(row["heldout_simulation_id"]):
            mismatches.append(
                f"{target}/{definition}/{fold_index}:heldout={heldout}"
            )
            continue
        training = table.drop(index=fold_index)
        X_train = training[FEATURE_COLUMNS].to_numpy(float)
        y_train = training["target_value_um"].to_numpy(float)
        expected_x_mean = X_train.mean(axis=0)
        expected_x_scale = X_train.std(axis=0, ddof=0)
        expected_x_scale[expected_x_scale == 0] = 1.0
        stored_x_mean = np.asarray(json.loads(row["x_training_mean"]), dtype=float)
        stored_x_scale = np.asarray(
            json.loads(row["x_training_scale"]), dtype=float
        )
        if not np.allclose(
            stored_x_mean, expected_x_mean, rtol=1e-10, atol=1e-10
        ):
            mismatches.append(
                f"{target}/{definition}/{fold_index}:x_mean"
            )
        if not np.allclose(
            stored_x_scale, expected_x_scale, rtol=1e-10, atol=1e-10
        ):
            mismatches.append(
                f"{target}/{definition}/{fold_index}:x_scale"
            )
        if not math.isclose(
            float(row["training_y_mean_um"]),
            float(y_train.mean()),
            rel_tol=1e-10,
            abs_tol=1e-10,
        ):
            mismatches.append(
                f"{target}/{definition}/{fold_index}:y_mean"
            )
        if not math.isclose(
            float(row["training_y_std_um"]),
            float(y_train.std(ddof=0)),
            rel_tol=1e-10,
            abs_tol=1e-10,
        ):
            mismatches.append(
                f"{target}/{definition}/{fold_index}:y_std"
            )
        checked += 1
    return (
        not mismatches,
        f"checked_fold_scalers={checked}; mismatches={mismatches[:8]}",
    )


def _ridge_inner_cv_valid(
    hyperparameters: pd.DataFrame,
    populations: dict[str, pd.DataFrame],
) -> tuple[bool, str]:
    failures: list[str] = []
    checked = 0
    for _, row in hyperparameters.iterrows():
        target = str(row["target"])
        population = populations[target].sort_values(
            "numeric_simulation_id"
        ).reset_index(drop=True)
        fold = int(row["fold_index"])
        heldout = str(population.loc[fold, "simulation_id"])
        outer_training = population.drop(index=fold)[
            "simulation_id"
        ].astype(str).to_numpy()
        if heldout != str(row["heldout_simulation_id"]):
            failures.append(f"{target}/{fold}:heldout")
            continue
        groups = json.loads(row["inner_cv_validation_id_groups_json"])
        flattened = [item for group in groups for item in group]
        if (
            len(groups) != RIDGE_INNER_FOLDS
            or sorted(flattened) != sorted(outer_training.tolist())
            or len(flattened) != len(set(flattened))
            or heldout in flattened
        ):
            failures.append(f"{target}/{fold}:partition")
        seed = int(row["inner_cv_random_seed"])
        expected_groups = [
            outer_training[validation_indices].tolist()
            for _, validation_indices in KFold(
                n_splits=RIDGE_INNER_FOLDS,
                shuffle=True,
                random_state=seed,
            ).split(np.empty((len(outer_training), 1)))
        ]
        if groups != expected_groups:
            failures.append(f"{target}/{fold}:determinism")
        scores = json.loads(row["inner_mean_validation_rmse_by_alpha_json"])
        if [float(item["alpha"]) for item in scores] != list(RIDGE_ALPHA_GRID):
            failures.append(f"{target}/{fold}:alpha_grid")
        else:
            selected = float(scores[int(np.argmin([item["mean_rmse_um"] for item in scores]))]["alpha"])
            if not math.isclose(
                selected,
                float(row["selected_ridge_alpha"]),
                rel_tol=0.0,
                abs_tol=0.0,
            ):
                failures.append(f"{target}/{fold}:selection")
        checked += 1
    return not failures, f"checked={checked}; failures={failures[:8]}"


def _gp_uncertainty_calculations_valid(
    predictions: pd.DataFrame,
) -> tuple[bool, str]:
    learned = predictions.loc[
        _boolean_series(predictions["learned_nugget"])
    ]
    no_nugget = predictions.loc[
        ~_boolean_series(predictions["learned_nugget"])
    ]
    noise_expected = (
        learned["optimized_noise_variance_normalized"].to_numpy(float)
        * learned["training_y_std_um"].to_numpy(float) ** 2
    )
    noise_recorded = learned["optimized_noise_variance_um2"].to_numpy(float)
    total_minus_latent = (
        learned["total_predictive_variance_um2"].to_numpy(float)
        - learned["latent_predictive_variance_um2"].to_numpy(float)
    )
    passed = bool(
        np.allclose(noise_expected, noise_recorded, rtol=1e-8, atol=1e-8)
        and np.allclose(
            noise_recorded,
            learned["optimized_noise_std_um"].to_numpy(float) ** 2,
            rtol=1e-8,
            atol=1e-8,
        )
        and np.allclose(
            total_minus_latent,
            noise_recorded,
            rtol=1e-7,
            atol=1e-7,
        )
        and no_nugget["total_predictive_std_um"].isna().all()
        and no_nugget["optimized_noise_std_um"].isna().all()
        and set(
            no_nugget["numerical_alpha_normalized"].astype(float).unique()
        )
        == {NO_NUGGET_ALPHA}
        and set(
            learned["numerical_alpha_normalized"].astype(float).unique()
        )
        == {LEARNED_NUGGET_ALPHA}
    )
    maximum_difference = (
        float(np.max(np.abs(total_minus_latent - noise_recorded)))
        if len(learned)
        else np.nan
    )
    return (
        passed,
        f"learned_rows={len(learned)}; no_nugget_rows={len(no_nugget)}; "
        f"max_total_minus_latent_error_um2={maximum_difference}",
    )


def _gp_coverage_calculations_valid(
    predictions: pd.DataFrame,
    metrics: pd.DataFrame,
) -> tuple[bool, str]:
    failures: list[str] = []
    groups_checked = 0
    grouping = ["target", "target_definition", "gp_configuration"]
    for keys, subset in predictions.groupby(grouping, sort=True):
        observed = subset["observed_target_um"].to_numpy(float)
        latent_expected = (
            observed
            >= subset["latent_interval_lower_um"].to_numpy(float)
        ) & (
            observed
            <= subset["latent_interval_upper_um"].to_numpy(float)
        )
        latent_stored = _boolean_series(
            subset["latent_interval_contains_observed"]
        ).to_numpy(bool)
        if not np.array_equal(latent_expected, latent_stored):
            failures.append(f"{keys}:latent_row_flags")

        learned = bool(
            _boolean_series(subset["learned_nugget"]).iloc[0]
        )
        expected_latent_coverage = float(latent_expected.mean())
        expected_total_coverage = np.nan
        expected_evaluation_coverage = expected_latent_coverage
        if learned:
            total_expected = (
                observed
                >= subset["total_interval_lower_um"].to_numpy(float)
            ) & (
                observed
                <= subset["total_interval_upper_um"].to_numpy(float)
            )
            total_stored = _boolean_series(
                subset["total_interval_contains_observed"]
            ).to_numpy(bool)
            if not np.array_equal(total_expected, total_stored):
                failures.append(f"{keys}:total_row_flags")
            expected_total_coverage = float(total_expected.mean())
            expected_evaluation_coverage = expected_total_coverage
        elif subset["total_interval_contains_observed"].notna().any():
            failures.append(f"{keys}:unexpected_total_flags")

        metric = metrics.loc[
            (metrics["target"] == keys[0])
            & (metrics["target_definition"] == keys[1])
            & (metrics["gp_configuration"] == keys[2])
        ]
        if len(metric) != 1:
            failures.append(f"{keys}:metric_rows={len(metric)}")
            continue
        metric_row = metric.iloc[0]
        for column, expected in [
            ("latent_95_coverage", expected_latent_coverage),
            ("total_95_coverage", expected_total_coverage),
            ("evaluation_95_coverage", expected_evaluation_coverage),
        ]:
            stored = float(metric_row[column])
            if math.isnan(expected):
                matches = math.isnan(stored)
            else:
                matches = math.isclose(
                    stored, expected, rel_tol=0.0, abs_tol=1e-12
                )
            if not matches:
                failures.append(
                    f"{keys}:{column} stored={stored} expected={expected}"
                )
        groups_checked += 1
    return (
        not failures,
        f"groups_checked={groups_checked}; failures={failures[:8]}",
    )


def _target_traceability_valid(
    target_table: pd.DataFrame,
    trace: pd.DataFrame,
    ledger: pd.DataFrame,
) -> tuple[bool, str]:
    failures: list[str] = []
    checked_hashes = 0
    trace_t5 = trace.loc[trace["target_definition"] == "T5"].sort_values(
        "numeric_simulation_id"
    )
    for _, row in trace_t5.iterrows():
        for path_column, hash_column in [
            ("source_bounds_path", "bounds_sha256"),
            ("source_time_path", "time_sha256"),
            ("source_iteration_path", "iteration_sha256"),
        ]:
            path = ROOT / str(row[path_column])
            if not path.exists() or sha256(path) != str(row[hash_column]):
                failures.append(
                    f"{row['simulation_id']}:{path_column}"
                )
            checked_hashes += 1
        valid_count = int(row["valid_melt_row_count"])
        expected_count = min(50, valid_count)
        if int(row["window_observation_count"]) != expected_count:
            failures.append(f"{row['simulation_id']}:T5_count")
        expected_flag = valid_count < 50
        if bool(row["fewer_than_50_valid_rows"]) != expected_flag:
            failures.append(f"{row['simulation_id']}:T5_flag")

    t0_values = target_table.loc[
        target_table["target_definition"] == "T0"
    ]
    for target in TARGET_KEYS:
        observed = (
            t0_values.loc[t0_values["target"] == target]
            .sort_values("numeric_simulation_id")["target_value_m"]
            .to_numpy(float)
        )
        expected = (
            ledger.sort_values("numeric_simulation_id")[
                TARGET_SOURCE_COLUMNS[target]
            ].to_numpy(float)
        )
        if not np.allclose(observed, expected, rtol=0.0, atol=5e-15):
            failures.append(f"{target}:T0_values")

    controlled = trace.loc[
        trace["target_definition"].isin(["T0", "T1", "T2", "T3", "T4"])
    ]
    for _, row in controlled.iterrows():
        definition = TARGET_DEFINITION_BY_CODE[
            str(row["target_definition"])
        ]
        expected_requested = (
            float(definition.cutoff_fraction)
            * float(row["laser_exit_time_s"])
        )
        expected_applied = min(
            float(row["final_recorded_time_s"]), expected_requested
        )
        expected_start = float(row["first_valid_time_s"]) + (
            1.0 - float(definition.window_fraction)
        ) * (expected_applied - float(row["first_valid_time_s"]))
        if not math.isclose(
            float(row["requested_cutoff_time_s"]),
            expected_requested,
            rel_tol=1e-12,
            abs_tol=1e-15,
        ):
            failures.append(
                f"{row['simulation_id']}/{definition.code}:requested_cutoff"
            )
        if not math.isclose(
            float(row["applied_cutoff_time_s"]),
            expected_applied,
            rel_tol=1e-12,
            abs_tol=1e-15,
        ):
            failures.append(
                f"{row['simulation_id']}/{definition.code}:applied_cutoff"
            )
        if not math.isclose(
            float(row["nominal_window_start_time_s"]),
            expected_start,
            rel_tol=1e-12,
            abs_tol=1e-15,
        ):
            failures.append(
                f"{row['simulation_id']}/{definition.code}:start"
            )
        if (
            float(row["window_end_time_s"])
            > float(row["applied_cutoff_time_s"]) + 1e-15
        ):
            failures.append(
                f"{row['simulation_id']}/{definition.code}:cutoff_exceeded"
            )
    return (
        not failures,
        f"trace_rows={len(trace)}; raw_hashes_checked={checked_hashes}; "
        f"failures={failures[:8]}",
    )


def _bootstrap_outputs_reproducible(
    phase3a_outputs: dict[str, pd.DataFrame],
    phase3b_outputs: dict[str, pd.DataFrame],
) -> tuple[bool, str]:
    failures: list[str] = []
    checked = 0
    for _, stored in phase3a_outputs["comparison_summary"].iterrows():
        _, recomputed = aligned_prediction_comparison(
            phase3a_outputs["predictions"],
            target=str(stored["target"]),
            model_column="model",
            reference_model=str(stored["reference_model"]),
            candidate_model=str(stored["candidate_model"]),
            comparison_type=str(stored["comparison_type"]),
        )
        for column in [
            "mae_difference_ci95_lower_um",
            "mae_difference_ci95_upper_um",
            "rmse_difference_ci95_lower_um",
            "rmse_difference_ci95_upper_um",
        ]:
            if not math.isclose(
                float(stored[column]),
                float(recomputed[column]),
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                failures.append(
                    f"3A/{stored['target']}/{stored['candidate_model']}/{column}"
                )
        checked += 1
    for _, stored in phase3b_outputs["bootstrap_summary"].iterrows():
        _, recomputed = aligned_prediction_comparison(
            phase3b_outputs["predictions"],
            target=str(stored["target"]),
            model_column="gp_configuration",
            reference_model=str(stored["reference_model"]),
            candidate_model=str(stored["candidate_model"]),
            comparison_type=str(stored["comparison_type"]),
        )
        for column in [
            "mae_difference_ci95_lower_um",
            "mae_difference_ci95_upper_um",
            "rmse_difference_ci95_lower_um",
            "rmse_difference_ci95_upper_um",
        ]:
            if not math.isclose(
                float(stored[column]),
                float(recomputed[column]),
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                failures.append(
                    f"3B/{stored['target']}/{stored['candidate_model']}/{column}"
                )
        checked += 1
    return not failures, f"comparisons_checked={checked}; failures={failures[:8]}"


def build_validations(
    *,
    ledger: pd.DataFrame,
    populations: dict[str, pd.DataFrame],
    input_provenance: dict[str, Any],
    phase3a_outputs: dict[str, pd.DataFrame],
    phase3b_outputs: dict[str, pd.DataFrame],
    target_table: pd.DataFrame,
    trace: pd.DataFrame,
    distribution_summary: pd.DataFrame,
    difference_summary: pd.DataFrame,
    phase3c_outputs: dict[str, pd.DataFrame],
    final_models: pd.DataFrame,
    final_targets: pd.DataFrame,
    require_notebook: bool,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(
        check_id: str,
        requirement: str,
        passed: bool,
        detail: str,
        evidence: str,
    ) -> None:
        rows.append(
            {
                "check_id": check_id,
                "requirement": requirement,
                "status": "PASS" if passed else "FAIL",
                "detail": detail,
                "evidence": evidence,
            }
        )

    revision_set = set(ledger["huggingface_revision"].astype(str))
    add(
        "V01",
        "exact Phase 1 provenance",
        revision_set == {EXPECTED_PHASE1_REVISION}
        and input_provenance["phase1_rows"] == 241,
        f"revision={revision_set}; rows={len(ledger)}",
        "Phase 1 ledger; phase3_runtime_provenance.json",
    )
    add(
        "V02",
        "unchanged Phase 1 ledger hash",
        sha256(phase2.PHASE1_INPUT) == EXPECTED_PHASE1_LEDGER_SHA256,
        f"sha256={sha256(phase2.PHASE1_INPUT)}",
        "week6_phase1_simulation_level_responses.csv",
    )
    aggregate, aggregate_count = phase2.phase1_aggregate_sha256()
    add(
        "V03",
        "unchanged Phase 1 protected aggregate",
        aggregate == EXPECTED_PHASE1_AGGREGATE_SHA256,
        f"aggregate={aggregate}; files={aggregate_count}",
        "Phase 1 protected files",
    )
    phase2_paths = [
        path
        for path in EXPECTED_CORE_ARTIFACT_HASHES
        if "week6_02_gp_response_noise_comparison" in path
        or path.endswith("02_gp_response_noise_comparison.ipynb")
        or path.endswith("week6_phase2_gp_response_noise_comparison.py")
    ]
    add(
        "V04",
        "Phase 2 source and artifacts unchanged",
        all(
            sha256(ROOT / path) == EXPECTED_CORE_ARTIFACT_HASHES[path]
            for path in phase2_paths
        ),
        f"checked_paths={len(phase2_paths)}",
        "Phase 2 source, notebook, configurations, predictions, summary",
    )
    phase25_paths = [
        path
        for path in EXPECTED_CORE_ARTIFACT_HASHES
        if "week6_02_5_depth_model_closure" in path
        or path.endswith("03_phase2_5_depth_model_closure.ipynb")
        or path.endswith("week6_phase2_5_depth_model_closure.py")
    ]
    add(
        "V05",
        "Phase 2.5 source and artifacts unchanged",
        all(
            sha256(ROOT / path) == EXPECTED_CORE_ARTIFACT_HASHES[path]
            for path in phase25_paths
        ),
        f"checked_paths={len(phase25_paths)}",
        "Phase 2.5 source, notebook, configurations, predictions, summary",
    )
    add(
        "V06",
        "features exactly P, VX, LS, ST",
        FEATURE_COLUMNS == ["P", "VX", "LS", "ST"]
        and all(
            set(frame["feature_columns"].dropna().astype(str))
            == {json_compact(FEATURE_COLUMNS)}
            for frame in [
                phase3a_outputs["predictions"],
                phase3b_outputs["predictions"],
                phase3c_outputs["predictions"],
            ]
        ),
        f"features={FEATURE_COLUMNS}",
        "configuration and prediction rows",
    )
    add(
        "V07",
        "width population exactly 241",
        len(populations["width"]) == 241,
        f"rows={len(populations['width'])}",
        "phase3_input_population_summary.csv",
    )
    add(
        "V08",
        "length population exactly 241",
        len(populations["length"]) == 241,
        f"rows={len(populations['length'])}",
        "phase3_input_population_summary.csv",
    )
    add(
        "V09",
        "depth population exactly 230",
        len(populations["depth"]) == 230,
        f"rows={len(populations['depth'])}",
        "phase3_input_population_summary.csv",
    )
    observed_exclusions = sorted(
        set(ledger["simulation_id"]) - set(populations["depth"]["simulation_id"])
    )
    add(
        "V10",
        "exact expected depth exclusions",
        observed_exclusions == DEPTH_EXCLUSIONS,
        f"excluded={observed_exclusions}",
        "phase3_input_population_summary.csv",
    )

    def fold_ids_match(
        frame: pd.DataFrame, model_column: str
    ) -> tuple[bool, str]:
        failures: list[str] = []
        for keys, subset in frame.groupby(
            ["target", "target_definition", model_column], sort=True
        ):
            target = str(keys[0])
            expected = (
                populations[target]
                .sort_values("numeric_simulation_id")["simulation_id"]
                .astype(str)
                .tolist()
            )
            observed = (
                subset.sort_values("fold_index")["heldout_simulation_id"]
                .astype(str)
                .tolist()
            )
            if observed != expected:
                failures.append(str(keys))
        return not failures, f"mismatched_groups={failures}"

    passed, detail = fold_ids_match(phase3a_outputs["predictions"], "model")
    add(
        "V11",
        "identical Phase 3A outer fold IDs",
        passed,
        detail,
        "simple_baseline_loo_predictions.csv",
    )
    passed, detail = fold_ids_match(
        phase3b_outputs["predictions"], "gp_configuration"
    )
    add(
        "V12",
        "identical Phase 3B outer fold IDs",
        passed,
        detail,
        "gp_kernel_noise_loo_predictions.csv",
    )
    passed, detail = fold_ids_match(
        phase3c_outputs["predictions"], "gp_configuration"
    )
    add(
        "V13",
        "identical Phase 3C outer fold IDs",
        passed,
        detail,
        "target_definition_loo_predictions.csv",
    )
    duplicate_groups: list[str] = []
    for label, frame, model_column in [
        ("3A", phase3a_outputs["predictions"], "model"),
        ("3B", phase3b_outputs["predictions"], "gp_configuration"),
        ("3C", phase3c_outputs["predictions"], "gp_configuration"),
    ]:
        if frame.duplicated(
            [
                "target",
                "target_definition",
                model_column,
                "heldout_simulation_id",
            ]
        ).any():
            duplicate_groups.append(label)
    add(
        "V14",
        "no duplicate held-out predictions",
        not duplicate_groups,
        f"duplicate_outputs={duplicate_groups}",
        "all LOO prediction files",
    )

    combined_scalable = pd.concat(
        [
            phase3a_outputs["predictions"].loc[
                phase3a_outputs["predictions"]["model"].isin(
                    ["linear_ridge", "polynomial_ridge_degree2"]
                )
            ],
            phase3b_outputs["predictions"],
            phase3c_outputs["predictions"].loc[
                phase3c_outputs["predictions"]["target_definition"] != "T0"
            ],
        ],
        ignore_index=True,
        sort=False,
    )
    passed, detail = _fold_scalers_match(
        combined_scalable, target_table, populations
    )
    add(
        "V15",
        "fold-local X preprocessing",
        passed,
        detail,
        "stored and independently recomputed fold scaler means/scales",
    )
    add(
        "V16",
        "fold-local y scaling",
        passed,
        detail,
        "stored and independently recomputed training y mean/std",
    )
    passed, detail = _ridge_inner_cv_valid(
        phase3a_outputs["hyperparameters"], populations
    )
    add(
        "V17",
        "nested Ridge tuning uses outer-training data only",
        passed,
        detail,
        "simple_baseline_selected_hyperparameters.csv",
    )
    ridge_predictions = phase3a_outputs["predictions"].loc[
        phase3a_outputs["predictions"]["model"].isin(
            ["linear_ridge", "polynomial_ridge_degree2"]
        )
    ]
    heldout_never_used = bool(
        (~_boolean_series(ridge_predictions["heldout_target_used_for_tuning"])).all()
        and (~_boolean_series(ridge_predictions["heldout_target_used_for_fitting"])).all()
        and (~_boolean_series(ridge_predictions["heldout_target_used_for_scaling"])).all()
    )
    add(
        "V18",
        "held-out targets never used for Ridge tuning/fitting/scaling",
        heldout_never_used,
        f"ridge_rows={len(ridge_predictions)}",
        "simple_baseline_loo_predictions.csv",
    )
    add(
        "V19",
        "exact Ridge alpha grid and one selection per outer fold",
        set(
            phase3a_outputs["hyperparameters"]["selected_ridge_alpha"].astype(
                float
            )
        ).issubset(set(RIDGE_ALPHA_GRID))
        and len(phase3a_outputs["hyperparameters"])
        == 2 * sum(EXPECTED_POPULATION_SIZES.values()),
        f"grid={RIDGE_ALPHA_GRID}; rows={len(phase3a_outputs['hyperparameters'])}",
        "simple_baseline_selected_hyperparameters.csv",
    )
    expected_a_rows = 4 * sum(EXPECTED_POPULATION_SIZES.values())
    add(
        "V20",
        "exactly one Phase 3A prediction per model/target/simulation",
        len(phase3a_outputs["predictions"]) == expected_a_rows,
        f"expected={expected_a_rows}; observed={len(phase3a_outputs['predictions'])}",
        "simple_baseline_loo_predictions.csv",
    )
    expected_b_rows = 6 * sum(EXPECTED_POPULATION_SIZES.values())
    add(
        "V21",
        "exactly one Phase 3B prediction per configuration/target/simulation",
        len(phase3b_outputs["predictions"]) == expected_b_rows,
        f"expected={expected_b_rows}; observed={len(phase3b_outputs['predictions'])}",
        "gp_kernel_noise_loo_predictions.csv",
    )
    expected_c_rows = 6 * sum(EXPECTED_POPULATION_SIZES.values())
    add(
        "V22",
        "exactly one Phase 3C prediction per definition/target/simulation",
        len(phase3c_outputs["predictions"]) == expected_c_rows,
        f"expected={expected_c_rows}; observed={len(phase3c_outputs['predictions'])}",
        "target_definition_loo_predictions.csv",
    )
    prediction_frames = [
        phase3a_outputs["predictions"],
        phase3b_outputs["predictions"],
        phase3c_outputs["predictions"],
    ]
    add(
        "V23",
        "all predictions are finite",
        all(
            np.isfinite(frame["predicted_mean_um"].to_numpy(float)).all()
            for frame in prediction_frames
        ),
        f"rows_checked={sum(map(len, prediction_frames))}",
        "all LOO prediction files",
    )
    gp_combined = pd.concat(
        [
            phase3b_outputs["predictions"],
            phase3c_outputs["predictions"],
        ],
        ignore_index=True,
    )
    add(
        "V24",
        "valid positive GP predictive standard deviations",
        bool(
            np.isfinite(
                gp_combined["latent_predictive_std_um"].to_numpy(float)
            ).all()
            and (
                gp_combined["latent_predictive_std_um"].to_numpy(float) > 0
            ).all()
            and (
                gp_combined.loc[
                    _boolean_series(gp_combined["learned_nugget"]),
                    "total_predictive_std_um",
                ].to_numpy(float)
                > 0
            ).all()
        ),
        f"gp_rows={len(gp_combined)}",
        "GP prediction files",
    )
    passed, detail = _gp_uncertainty_calculations_valid(gp_combined)
    add(
        "V25",
        "correct nugget and no-nugget variance calculations",
        passed,
        detail,
        "GP prediction rows",
    )
    passed, detail = _target_traceability_valid(target_table, trace, ledger)
    add(
        "V26",
        "target candidates trace to raw aligned monitor files",
        passed,
        detail,
        "target_definition_traceability.csv",
    )
    add(
        "V27",
        "T0 exactly reproduces Phase 1 target definition",
        passed,
        detail,
        "target_definition_simulation_level_table.csv; Phase 1 ledger",
    )
    add(
        "V28",
        "all T0–T5 definitions present for all responses",
        set(target_table["target_definition"]) == set(TARGET_DEFINITION_CODES)
        and set(target_table["target"]) == set(TARGET_KEYS)
        and len(target_table) == 241 * 6 * 3,
        f"rows={len(target_table)}; definitions={sorted(target_table['target_definition'].unique())}",
        "target_definition_simulation_level_table.csv",
    )
    add(
        "V29",
        "target candidate availability recorded",
        target_table["available"].notna().all()
        and distribution_summary["availability_count"].notna().all(),
        f"unavailable_rows={int((~_boolean_series(target_table['available'])).sum())}",
        "target tables and distribution summary",
    )
    add(
        "V30",
        "sentinel rows excluded",
        _boolean_series(target_table["sentinel_rows_excluded"]).all()
        and _boolean_series(trace["sentinel_rows_excluded"]).all(),
        f"trace_sentinel_rows={int(trace['sentinel_row_count'].sum())}",
        "target_definition_traceability.csv",
    )
    controlled = trace.loc[
        trace["target_definition"].isin(["T0", "T1", "T2", "T3", "T4"])
    ]
    add(
        "V31",
        "T0–T4 domain cutoffs correctly applied",
        _boolean_series(controlled["controlled_cutoff_respected"]).all()
        and controlled["window_end_time_s"].le(
            controlled["applied_cutoff_time_s"] + 1e-15
        ).all(),
        f"controlled_rows={len(controlled)}",
        "target_definition_traceability.csv",
    )
    t5 = trace.loc[trace["target_definition"] == "T5"]
    add(
        "V32",
        "T5 uses final 50 valid rows and flags short series",
        _boolean_series(t5["t5_exact_final_50_rule"]).all()
        and (
            t5["window_observation_count"].to_numpy(int)
            == np.minimum(50, t5["valid_melt_row_count"].to_numpy(int))
        ).all(),
        f"T5_rows={len(t5)}; short_series={int(_boolean_series(t5['fewer_than_50_valid_rows']).sum())}",
        "target_definition_traceability.csv",
    )
    paired_details = [
        phase3a_outputs["comparison_detail"],
        phase3b_outputs["within_detail"],
        phase3b_outputs["candidate_detail"],
    ]
    add(
        "V33",
        "paired comparisons aligned by simulation ID",
        all(
            not frame.duplicated(
                [
                    "target",
                    "reference_model",
                    "candidate_model",
                    "heldout_simulation_id",
                ]
            ).any()
            for frame in paired_details
        ),
        f"paired_detail_rows={sum(map(len, paired_details))}",
        "paired comparison files",
    )
    bootstrap_summaries = [
        phase3a_outputs["comparison_summary"],
        phase3b_outputs["bootstrap_summary"],
        phase3c_outputs["predictability_comparisons"],
    ]
    add(
        "V34",
        "paired bootstrap preserves pairing and uses 10,000 resamples",
        all(
            _boolean_series(frame["pairing_preserved"]).all()
            and set(frame["bootstrap_resamples"].astype(int))
            == {PAIRED_BOOTSTRAP_RESAMPLES}
            for frame in bootstrap_summaries
        ),
        f"summary_rows={sum(map(len, bootstrap_summaries))}",
        "paired bootstrap summary files",
    )
    passed_a, detail_a = _metric_values_match(
        phase3a_outputs["predictions"],
        phase3a_outputs["metrics"],
        model_column="model",
    )
    passed_b, detail_b = _metric_values_match(
        phase3b_outputs["predictions"],
        phase3b_outputs["metrics"],
        model_column="gp_configuration",
    )
    passed_c, detail_c = _metric_values_match(
        phase3c_outputs["predictions"],
        phase3c_outputs["metrics"],
        model_column="gp_configuration",
    )
    add(
        "V35",
        "metrics independently recomputed from prediction rows",
        passed_a and passed_b and passed_c,
        f"3A={detail_a}; 3B={detail_b}; 3C={detail_c}",
        "all metrics and prediction files",
    )
    passed, detail = _bootstrap_outputs_reproducible(
        phase3a_outputs, phase3b_outputs
    )
    add(
        "V36",
        "confidence intervals are deterministic and reproducible",
        passed,
        detail,
        "paired bootstrap summaries and predictions",
    )
    diagnostics = phase3b_outputs["hyperparameters"]
    add(
        "V37",
        "optimizer failures, warnings, and bound hits recorded",
        len(diagnostics) == expected_b_rows
        and {
            "failed_fold",
            "warning_count",
            "constant_bound_hit",
            "length_scale_bound_hit",
            "noise_bound_hit",
        }.issubset(diagnostics.columns)
        and diagnostics[
            [
                "failed_fold",
                "warning_count",
                "constant_bound_hit",
                "length_scale_bound_hit",
                "noise_bound_hit",
            ]
        ].notna().all().all(),
        f"diagnostic_rows={len(diagnostics)}",
        "gp_kernel_noise_hyperparameter_diagnostics.csv",
    )
    notebook_passed, notebook_detail, markdown_passed, markdown_detail = (
        _check_notebook()
    )
    add(
        "V38",
        "notebook has zero error outputs",
        notebook_passed if require_notebook else True,
        notebook_detail if require_notebook else f"deferred; {notebook_detail}",
        "04_phase3_model_target_robustness.ipynb",
    )
    add(
        "V39",
        "all major notebook code cells followed by explanatory Markdown",
        markdown_passed if require_notebook else True,
        markdown_detail if require_notebook else f"deferred; {markdown_detail}",
        "04_phase3_model_target_robustness.ipynb",
    )
    original_passed, original_detail = verify_original_worktree()
    add(
        "V40",
        "original dirty worktree unchanged",
        original_passed,
        original_detail,
        "protected branch, HEAD, status, and six SHA-256 fingerprints",
    )
    diff_check = run_git("diff", "--check", check=False)
    add(
        "V41",
        "git diff --check passes",
        diff_check.returncode == 0,
        diff_check.stdout.strip() or diff_check.stderr.strip() or "no errors",
        "git diff --check",
    )
    source_text = Path(__file__).read_text(encoding="utf-8")
    prohibited_implementation_patterns = [
        r"from\s+sklearn\.inspection\s+import",
        r"permutation_importance\s*\(",
        r"partial_dependence\s*\(",
        r"GaussianProcessClassifier\s*\(",
        r"\bSALib\b",
        r"def\s+.*sobol",
        r"def\s+.*active_learning",
        r"def\s+.*level_set",
    ]
    matches = [
        pattern
        for pattern in prohibited_implementation_patterns
        if re.search(pattern, source_text, flags=re.IGNORECASE)
    ]
    add(
        "V42",
        "no Phase 4 or feature-effect work introduced",
        not matches,
        f"prohibited_implementation_matches={matches}",
        "Phase 3 source inspection",
    )
    repository = current_repository_state()
    add(
        "V43",
        "no commit occurred during Phase 3",
        repository["head"] == STARTING_HEAD,
        f"head={repository['head']}; starting_head={STARTING_HEAD}",
        "git rev-parse HEAD",
    )
    remote_phase3 = run_git(
        "ls-remote",
        "--heads",
        "origin",
        f"refs/heads/{EXPECTED_BRANCH}",
        check=False,
    )
    add(
        "V44",
        "no Phase 3 push occurred",
        remote_phase3.returncode == 0 and not remote_phase3.stdout.strip(),
        f"remote_output={remote_phase3.stdout.strip()!r}; returncode={remote_phase3.returncode}",
        "git ls-remote --heads origin",
    )
    missing_outputs = [
        filename
        for filename in REQUIRED_OUTPUT_FILENAMES
        if not (OUTPUT_DIR / filename).exists()
    ]
    add(
        "V45",
        "all required output files exist",
        not missing_outputs,
        f"missing={missing_outputs}",
        "outputs/week6_03_model_target_robustness/",
    )
    figure_files = sorted(FIGURE_DIR.glob("*.png"))
    add(
        "V46",
        "all focused figures exist and are non-empty",
        len(figure_files) >= 13
        and all(path.stat().st_size > 10_000 for path in figure_files),
        f"figure_count={len(figure_files)}; files={[path.name for path in figure_files]}",
        "figures/",
    )
    add(
        "V47",
        "target definitions use unchanged target-specific populations",
        all(
            len(
                target_table.loc[
                    (target_table["target"] == target)
                    & target_table[
                        "in_target_modelling_population"
                    ].astype(bool)
                    & (target_table["target_definition"] == definition)
                ]
            )
            == EXPECTED_POPULATION_SIZES[target]
            for target in TARGET_KEYS
            for definition in TARGET_DEFINITION_CODES
        ),
        "all 18 target/definition populations checked",
        "target_definition_simulation_level_table.csv",
    )
    fixed_gp_valid = True
    fixed_gp_detail: dict[str, list[str]] = {}
    for target in TARGET_KEYS:
        configs = sorted(
            phase3c_outputs["predictions"]
            .loc[
                phase3c_outputs["predictions"]["target"] == target,
                "gp_configuration",
            ]
            .astype(str)
            .unique()
        )
        fixed_gp_detail[target] = configs
        fixed_gp_valid &= len(configs) == 1
    add(
        "V48",
        "one provisional GP configuration held fixed across T0–T5",
        fixed_gp_valid,
        f"configurations={fixed_gp_detail}",
        "target_definition_loo_predictions.csv",
    )
    add(
        "V49",
        "final model decisions are target-specific and complete",
        set(final_models["target"]) == set(TARGET_KEYS)
        and len(final_models) == 3,
        f"rows={len(final_models)}; targets={sorted(final_models['target'].tolist())}",
        "phase3_final_model_decision.csv",
    )
    add(
        "V50",
        "final target decisions are target-specific and complete",
        set(final_targets["target"]) == set(TARGET_KEYS)
        and len(final_targets) == 3,
        f"rows={len(final_targets)}; targets={sorted(final_targets['target'].tolist())}",
        "phase3_final_target_decision.csv",
    )
    coverage_b_passed, coverage_b_detail = (
        _gp_coverage_calculations_valid(
            phase3b_outputs["predictions"],
            phase3b_outputs["metrics"],
        )
    )
    coverage_c_passed, coverage_c_detail = (
        _gp_coverage_calculations_valid(
            phase3c_outputs["predictions"],
            phase3c_outputs["metrics"],
        )
    )
    add(
        "V51",
        "GP interval flags and aggregate coverage are independently recomputed",
        coverage_b_passed and coverage_c_passed,
        f"3B={coverage_b_detail}; 3C={coverage_c_detail}",
        "GP prediction and metrics files",
    )
    validation = pd.DataFrame(rows)
    if len(validation) < 34:
        raise RuntimeError("Validation suite unexpectedly contains fewer than 34 checks")
    return validation


def _package_version(distribution: str) -> str:
    try:
        return package_version(distribution)
    except PackageNotFoundError:
        return "not installed"


def build_runtime_provenance(
    *,
    invocation_start_utc: str,
    invocation_start_perf: float,
    workers: int,
    force: bool,
    mode: str,
    input_provenance: dict[str, Any],
    complete: bool,
) -> dict[str, Any]:
    existing_outputs: list[dict[str, Any]] = []
    mutable_snapshot_exclusions = {
        "phase3_runtime_provenance.json",
        "results_summary.md",
        "summary.json",
    }
    if OUTPUT_DIR.exists():
        for path in sorted(OUTPUT_DIR.rglob("*")):
            if (
                not path.is_file()
                or path.name in mutable_snapshot_exclusions
                or path.name.endswith(".stdout.log")
                or path.name.endswith(".stderr.log")
            ):
                continue
            existing_outputs.append(
                {
                    "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    repository = current_repository_state()
    original_passed, original_detail = verify_original_worktree()
    cache_reused = sum(
        bool(event.get("cache_reused")) for event in RUNTIME_EVENTS
    )
    computed = sum(
        not bool(event.get("cache_reused")) for event in RUNTIME_EVENTS
    )
    return {
        "generated_at_utc": utc_now(),
        "invocation_start_utc": invocation_start_utc,
        "invocation_complete": complete,
        "mode": mode,
        "exact_command_line": [sys.executable, *sys.argv],
        "deterministic_full_rebuild_command": (
            ".\\.venv\\Scripts\\python.exe "
            "src\\week6_phase3_model_target_robustness.py "
            "--full --force --workers 4"
        ),
        "workers": workers,
        "force_recompute": force,
        "full_invocation_wall_runtime_seconds": (
            time.perf_counter() - invocation_start_perf
        ),
        "runtime_environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": _package_version("scikit-learn"),
            "scipy": _package_version("scipy"),
            "matplotlib": matplotlib.__version__,
            "threadpoolctl": _package_version("threadpoolctl"),
            "nbformat": _package_version("nbformat"),
            "nbclient": _package_version("nbclient"),
        },
        "input_provenance": input_provenance,
        "repository": repository,
        "original_worktree_unchanged": original_passed,
        "original_worktree_detail": original_detail,
        "events": RUNTIME_EVENTS,
        "cache_reused_event_count": cache_reused,
        "computed_event_count": computed,
        "timing_principles": {
            "wall_runtime_is_measured": True,
            "aggregate_fold_runtime_is_not_treated_as_wall_clock": True,
            "checkpoint_reuse_is_labelled": True,
            "Phase3A_and_Phase3C_T0_reuse_exact_Phase3B_rows": True,
        },
        "output_artifacts_excluding_this_file": existing_outputs,
        "output_hash_snapshot_exclusions": {
            "files": sorted(mutable_snapshot_exclusions),
            "patterns": ["*.stdout.log", "*.stderr.log"],
            "reason": (
                "These files are written from, or continue changing after, "
                "the runtime snapshot; excluding them avoids stale recursive "
                "or active-log hashes."
            ),
        },
        "prior_complete_force_rebuild_provenance": (
            PRIOR_COMPLETE_RUNTIME_PROVENANCE
        ),
        "prior_complete_coverage_repair_provenance": (
            PRIOR_COMPLETE_COVERAGE_REPAIR_PROVENANCE
        ),
    }


def write_phase_outputs(
    *,
    configuration: dict[str, Any],
    population_summary: pd.DataFrame,
    phase3a_outputs: dict[str, pd.DataFrame],
    phase3b_outputs: dict[str, pd.DataFrame],
    target_table: pd.DataFrame,
    trace: pd.DataFrame,
    distribution_summary: pd.DataFrame,
    difference_summary: pd.DataFrame,
    phase3c_outputs: dict[str, pd.DataFrame],
    final_models: pd.DataFrame,
    final_model_comparisons: pd.DataFrame,
    final_targets: pd.DataFrame,
) -> list[Path]:
    paths = [
        write_json(configuration, "phase3_configuration.json"),
        write_csv(
            population_summary, "phase3_input_population_summary.csv"
        ),
        write_csv(
            phase3a_outputs["predictions"],
            "simple_baseline_loo_predictions.csv",
        ),
        write_csv(
            phase3a_outputs["metrics"], "simple_baseline_metrics.csv"
        ),
        write_csv(
            phase3a_outputs["hyperparameters"],
            "simple_baseline_selected_hyperparameters.csv",
        ),
        write_csv(
            phase3a_outputs["comparison_detail"],
            "simple_baseline_paired_comparisons.csv",
        ),
        write_csv(
            phase3a_outputs["comparison_summary"],
            "simple_baseline_paired_bootstrap_summary.csv",
        ),
        write_csv(
            phase3b_outputs["predictions"],
            "gp_kernel_noise_loo_predictions.csv",
        ),
        write_csv(
            phase3b_outputs["metrics"], "gp_kernel_noise_metrics.csv"
        ),
        write_csv(
            phase3b_outputs["hyperparameters"],
            "gp_kernel_noise_hyperparameter_diagnostics.csv",
        ),
        write_csv(
            phase3b_outputs["within_detail"],
            "within_kernel_nugget_comparisons.csv",
        ),
        write_csv(
            phase3b_outputs["candidate_detail"],
            "gp_candidate_vs_current_comparisons.csv",
        ),
        write_csv(
            phase3b_outputs["bootstrap_summary"],
            "gp_kernel_paired_bootstrap_summary.csv",
        ),
        write_csv(
            phase3b_outputs["learned_nugget"],
            "learned_nugget_by_kernel_summary.csv",
        ),
        write_csv(
            phase3b_outputs["provisional"],
            "provisional_kernel_decision.csv",
        ),
        write_csv(
            target_table, "target_definition_simulation_level_table.csv"
        ),
        write_csv(trace, "target_definition_traceability.csv"),
        write_csv(
            distribution_summary,
            "target_definition_distribution_summary.csv",
        ),
        write_csv(
            difference_summary,
            "target_definition_difference_summary.csv",
        ),
        write_csv(
            phase3c_outputs["predictions"],
            "target_definition_loo_predictions.csv",
        ),
        write_csv(
            phase3c_outputs["metrics"],
            "target_definition_model_metrics.csv",
        ),
        write_csv(
            phase3c_outputs["nuggets"],
            "target_definition_nugget_summary.csv",
        ),
        write_csv(
            phase3c_outputs["decisions"],
            "target_definition_decision.csv",
        ),
        write_csv(
            phase3c_outputs["predictability_comparisons"],
            "target_definition_model_paired_bootstrap_summary.csv",
        ),
        write_csv(final_models, "phase3_final_model_decision.csv"),
        write_csv(
            final_model_comparisons,
            "phase3_final_model_paired_bootstrap_summary.csv",
        ),
        write_csv(final_targets, "phase3_final_target_decision.csv"),
    ]
    return paths


def execute_notebook() -> float:
    import nbformat
    from nbclient import NotebookClient

    if not NOTEBOOK_PATH.exists():
        raise FileNotFoundError(NOTEBOOK_PATH)
    notebook = nbformat.read(NOTEBOOK_PATH, as_version=4)
    started = time.perf_counter()
    client = NotebookClient(
        notebook,
        timeout=180,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
        allow_errors=False,
    )
    executed = client.execute()
    duration = time.perf_counter() - started
    temporary = NOTEBOOK_PATH.with_suffix(".ipynb.tmp")
    nbformat.write(executed, temporary)
    os.replace(temporary, NOTEBOOK_PATH)
    return duration


def build_notebook() -> None:
    if not NOTEBOOK_BUILDER.exists():
        raise FileNotFoundError(NOTEBOOK_BUILDER)
    subprocess.run(
        [sys.executable, str(NOTEBOOK_BUILDER)],
        cwd=ROOT,
        check=True,
    )


def _placeholder_validation() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "check_id": "PENDING",
                "requirement": "Final validation will run after artifact assembly",
                "status": "PENDING",
                "detail": "not a scientific result",
                "evidence": "pipeline orchestration",
            }
        ]
    )


def write_reports_and_summary(
    *,
    input_provenance: dict[str, Any],
    population_summary: pd.DataFrame,
    phase3a_outputs: dict[str, pd.DataFrame],
    phase3b_outputs: dict[str, pd.DataFrame],
    distribution_summary: pd.DataFrame,
    difference_summary: pd.DataFrame,
    phase3c_outputs: dict[str, pd.DataFrame],
    final_models: pd.DataFrame,
    final_targets: pd.DataFrame,
    validation: pd.DataFrame,
    runtime_provenance: dict[str, Any],
) -> None:
    write_text(
        build_decision_log(
            phase3a_outputs,
            phase3b_outputs,
            difference_summary,
            phase3c_outputs,
            final_models,
            final_targets,
        ),
        "decision_log.md",
    )
    write_text(
        build_results_summary(
            input_provenance=input_provenance,
            population_summary=population_summary,
            phase3a_outputs=phase3a_outputs,
            phase3b_outputs=phase3b_outputs,
            difference_summary=difference_summary,
            phase3c_outputs=phase3c_outputs,
            final_models=final_models,
            final_targets=final_targets,
            validation=validation,
            runtime_provenance=runtime_provenance,
        ),
        "results_summary.md",
    )
    write_json(
        build_summary_json(
            input_provenance=input_provenance,
            population_summary=population_summary,
            phase3a_outputs=phase3a_outputs,
            phase3b_outputs=phase3b_outputs,
            distribution_summary=distribution_summary,
            difference_summary=difference_summary,
            phase3c_outputs=phase3c_outputs,
            final_models=final_models,
            final_targets=final_targets,
            validation=validation,
            runtime_provenance=runtime_provenance,
        ),
        "summary.json",
    )


def load_existing_outputs() -> dict[str, Any]:
    required = [
        filename
        for filename in REQUIRED_OUTPUT_FILENAMES
        if filename
        not in {
            "phase3_requirement_checklist.csv",
            "validation_results.csv",
            "decision_log.md",
            "results_summary.md",
            "summary.json",
            "phase3_runtime_provenance.json",
        }
    ]
    missing = [
        filename
        for filename in required
        if not (OUTPUT_DIR / filename).exists()
    ]
    if missing:
        raise RuntimeError(f"Cannot validate; missing outputs: {missing}")
    phase3a_outputs = {
        "predictions": pd.read_csv(
            OUTPUT_DIR / "simple_baseline_loo_predictions.csv"
        ),
        "metrics": pd.read_csv(
            OUTPUT_DIR / "simple_baseline_metrics.csv"
        ),
        "hyperparameters": pd.read_csv(
            OUTPUT_DIR / "simple_baseline_selected_hyperparameters.csv"
        ),
        "comparison_detail": pd.read_csv(
            OUTPUT_DIR / "simple_baseline_paired_comparisons.csv"
        ),
        "comparison_summary": pd.read_csv(
            OUTPUT_DIR / "simple_baseline_paired_bootstrap_summary.csv"
        ),
    }
    phase3b_outputs = {
        "predictions": pd.read_csv(
            OUTPUT_DIR / "gp_kernel_noise_loo_predictions.csv"
        ),
        "metrics": pd.read_csv(
            OUTPUT_DIR / "gp_kernel_noise_metrics.csv"
        ),
        "hyperparameters": pd.read_csv(
            OUTPUT_DIR / "gp_kernel_noise_hyperparameter_diagnostics.csv"
        ),
        "within_detail": pd.read_csv(
            OUTPUT_DIR / "within_kernel_nugget_comparisons.csv"
        ),
        "candidate_detail": pd.read_csv(
            OUTPUT_DIR / "gp_candidate_vs_current_comparisons.csv"
        ),
        "bootstrap_summary": pd.read_csv(
            OUTPUT_DIR / "gp_kernel_paired_bootstrap_summary.csv"
        ),
        "learned_nugget": pd.read_csv(
            OUTPUT_DIR / "learned_nugget_by_kernel_summary.csv"
        ),
        "provisional": pd.read_csv(
            OUTPUT_DIR / "provisional_kernel_decision.csv"
        ),
    }
    phase3c_outputs = {
        "predictions": pd.read_csv(
            OUTPUT_DIR / "target_definition_loo_predictions.csv"
        ),
        "metrics": pd.read_csv(
            OUTPUT_DIR / "target_definition_model_metrics.csv"
        ),
        "nuggets": pd.read_csv(
            OUTPUT_DIR / "target_definition_nugget_summary.csv"
        ),
        "decisions": pd.read_csv(
            OUTPUT_DIR / "target_definition_decision.csv"
        ),
        "predictability_comparisons": pd.read_csv(
            OUTPUT_DIR
            / "target_definition_model_paired_bootstrap_summary.csv"
        ),
    }
    return {
        "configuration": json.loads(
            (OUTPUT_DIR / "phase3_configuration.json").read_text(
                encoding="utf-8"
            )
        ),
        "population_summary": pd.read_csv(
            OUTPUT_DIR / "phase3_input_population_summary.csv"
        ),
        "phase3a": phase3a_outputs,
        "phase3b": phase3b_outputs,
        "target_table": pd.read_csv(
            OUTPUT_DIR / "target_definition_simulation_level_table.csv"
        ),
        "trace": pd.read_csv(
            OUTPUT_DIR / "target_definition_traceability.csv"
        ),
        "distribution_summary": pd.read_csv(
            OUTPUT_DIR / "target_definition_distribution_summary.csv"
        ),
        "difference_summary": pd.read_csv(
            OUTPUT_DIR / "target_definition_difference_summary.csv"
        ),
        "phase3c": phase3c_outputs,
        "final_models": pd.read_csv(
            OUTPUT_DIR / "phase3_final_model_decision.csv"
        ),
        "final_model_comparisons": pd.read_csv(
            OUTPUT_DIR / "phase3_final_model_paired_bootstrap_summary.csv"
        ),
        "final_targets": pd.read_csv(
            OUTPUT_DIR / "phase3_final_target_decision.csv"
        ),
    }


def run_full_pipeline(*, workers: int, force: bool) -> dict[str, Any]:
    global PRIOR_COMPLETE_RUNTIME_PROVENANCE
    global PRIOR_COMPLETE_COVERAGE_REPAIR_PROVENANCE
    invocation_start_utc = utc_now()
    invocation_start_perf = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    existing_runtime_path = OUTPUT_DIR / "phase3_runtime_provenance.json"
    if not force and existing_runtime_path.exists():
        try:
            existing_runtime = json.loads(
                existing_runtime_path.read_text(encoding="utf-8")
            )
            prior_force_runtime = existing_runtime.get(
                "prior_complete_force_rebuild_provenance"
            )
            if (
                existing_runtime.get("invocation_complete")
                and existing_runtime.get("force_recompute")
            ):
                PRIOR_COMPLETE_RUNTIME_PROVENANCE = existing_runtime
            elif isinstance(prior_force_runtime, dict):
                PRIOR_COMPLETE_RUNTIME_PROVENANCE = prior_force_runtime
            prior_coverage_repair = existing_runtime.get(
                "prior_complete_coverage_repair_provenance"
            )
            if isinstance(prior_coverage_repair, dict):
                PRIOR_COMPLETE_COVERAGE_REPAIR_PROVENANCE = (
                    prior_coverage_repair
                )
            elif (
                existing_runtime.get("invocation_complete")
                and not existing_runtime.get("force_recompute")
                and any(
                    "interval-coverage flags" in str(event.get("reason", ""))
                    for event in existing_runtime.get("events", [])
                )
            ):
                coverage_repair = dict(existing_runtime)
                coverage_repair.pop(
                    "prior_complete_force_rebuild_provenance", None
                )
                coverage_repair.pop(
                    "prior_complete_coverage_repair_provenance", None
                )
                PRIOR_COMPLETE_COVERAGE_REPAIR_PROVENANCE = coverage_repair
            if PRIOR_COMPLETE_RUNTIME_PROVENANCE is not None:
                RUNTIME_EVENTS.append(
                    {
                        "stage": (
                            "preserve_prior_complete_force_rebuild_provenance"
                        ),
                        "cache_reused": True,
                        "source_force_recompute": True,
                        "source_wall_runtime_seconds": (
                            PRIOR_COMPLETE_RUNTIME_PROVENANCE.get(
                                "full_invocation_wall_runtime_seconds"
                            )
                        ),
                        "reason": (
                            "independent closeout audit corrected parsing of "
                            "numeric 1.0/0.0 interval-coverage flags"
                        ),
                    }
                )
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                "Existing runtime provenance could not be preserved "
                "before the cached reporting rebuild"
            ) from exc
    print("Phase 3 input and worktree verification", flush=True)
    ledger, input_provenance = verify_required_inputs()
    populations, population_summary = build_populations(ledger)
    configuration = phase3_configuration()
    write_json(configuration, "phase3_configuration.json")
    write_csv(population_summary, "phase3_input_population_summary.csv")

    print("Phase 3A: current GP and nested simple baselines", flush=True)
    current_gp_predictions: dict[str, pd.DataFrame] = {}
    for target in TARGET_KEYS:
        current_gp_predictions[target] = run_gp_loo(
            population_t0_modelling_table(populations[target], target),
            target=target,
            target_definition="T0",
            analysis_label="phase3b_kernel_noise",
            configuration=GP_CONFIG_BY_NAME[CURRENT_GP_CONFIG_NAME],
            workers=workers,
            force=force,
        )
    phase3a_outputs = build_phase3a_outputs(
        populations,
        current_gp_predictions,
        workers=workers,
        force=force,
    )

    print("Phase 3B: six isotropic kernel/noise configurations", flush=True)
    phase3b_outputs, phase3b_prediction_frames = build_phase3b_outputs(
        populations,
        current_gp_predictions,
        workers=workers,
        force=force,
    )

    print("Phase 3C: exact raw T0-T5 target reconstruction", flush=True)
    target_table, trace = build_target_definition_tables(
        ledger, populations
    )
    distribution_summary = build_target_distribution_summary(target_table)
    difference_summary = build_target_difference_summary(
        target_table, phase3b_outputs["learned_nugget"]
    )
    print("Phase 3C: fixed-GP exact LOO for T0-T5", flush=True)
    phase3c_outputs = build_phase3c_outputs(
        target_table,
        distribution_summary,
        difference_summary,
        phase3b_outputs,
        phase3b_prediction_frames,
        workers=workers,
        force=force,
    )
    final_models, final_model_comparisons = build_final_model_decisions(
        phase3a_outputs, phase3b_outputs
    )
    final_targets = phase3c_outputs["decisions"].copy()
    final_targets = final_targets.merge(
        phase3b_outputs["provisional"][
            ["target", "selected_provisional_gp_configuration"]
        ],
        on="target",
        validate="one_to_one",
    )

    write_phase_outputs(
        configuration=configuration,
        population_summary=population_summary,
        phase3a_outputs=phase3a_outputs,
        phase3b_outputs=phase3b_outputs,
        target_table=target_table,
        trace=trace,
        distribution_summary=distribution_summary,
        difference_summary=difference_summary,
        phase3c_outputs=phase3c_outputs,
        final_models=final_models,
        final_model_comparisons=final_model_comparisons,
        final_targets=final_targets,
    )
    generate_figures(
        phase3a_outputs,
        phase3b_outputs,
        target_table,
        distribution_summary,
        difference_summary,
        phase3c_outputs,
        final_models,
        final_targets,
    )

    placeholder = _placeholder_validation()
    write_csv(placeholder, "validation_results.csv")
    write_csv(
        build_requirement_checklist(placeholder),
        "phase3_requirement_checklist.csv",
    )
    runtime = build_runtime_provenance(
        invocation_start_utc=invocation_start_utc,
        invocation_start_perf=invocation_start_perf,
        workers=workers,
        force=force,
        mode="full",
        input_provenance=input_provenance,
        complete=False,
    )
    write_json(runtime, "phase3_runtime_provenance.json")
    write_reports_and_summary(
        input_provenance=input_provenance,
        population_summary=population_summary,
        phase3a_outputs=phase3a_outputs,
        phase3b_outputs=phase3b_outputs,
        distribution_summary=distribution_summary,
        difference_summary=difference_summary,
        phase3c_outputs=phase3c_outputs,
        final_models=final_models,
        final_targets=final_targets,
        validation=placeholder,
        runtime_provenance=runtime,
    )

    preliminary_validation = build_validations(
        ledger=ledger,
        populations=populations,
        input_provenance=input_provenance,
        phase3a_outputs=phase3a_outputs,
        phase3b_outputs=phase3b_outputs,
        target_table=target_table,
        trace=trace,
        distribution_summary=distribution_summary,
        difference_summary=difference_summary,
        phase3c_outputs=phase3c_outputs,
        final_models=final_models,
        final_targets=final_targets,
        require_notebook=False,
    )
    preliminary_failures = preliminary_validation.loc[
        preliminary_validation["status"] != "PASS"
    ]
    if not preliminary_failures.empty:
        write_csv(preliminary_validation, "validation_results.csv")
        raise RuntimeError(
            "Pre-notebook validation failed:\n"
            + preliminary_failures[
                ["check_id", "requirement", "detail"]
            ].to_string(index=False)
        )
    write_csv(preliminary_validation, "validation_results.csv")
    write_csv(
        build_requirement_checklist(preliminary_validation),
        "phase3_requirement_checklist.csv",
    )
    runtime = build_runtime_provenance(
        invocation_start_utc=invocation_start_utc,
        invocation_start_perf=invocation_start_perf,
        workers=workers,
        force=force,
        mode="full",
        input_provenance=input_provenance,
        complete=False,
    )
    write_json(runtime, "phase3_runtime_provenance.json")
    write_reports_and_summary(
        input_provenance=input_provenance,
        population_summary=population_summary,
        phase3a_outputs=phase3a_outputs,
        phase3b_outputs=phase3b_outputs,
        distribution_summary=distribution_summary,
        difference_summary=difference_summary,
        phase3c_outputs=phase3c_outputs,
        final_models=final_models,
        final_targets=final_targets,
        validation=preliminary_validation,
        runtime_provenance=runtime,
    )

    print("Building and executing the Phase 3 notebook", flush=True)
    build_notebook()
    first_notebook_runtime = execute_notebook()
    RUNTIME_EVENTS.append(
        {
            "stage": "notebook_build_and_first_execution",
            "cache_reused": False,
            "wall_runtime_seconds": first_notebook_runtime,
            "notebook": str(NOTEBOOK_PATH.relative_to(ROOT)),
        }
    )
    final_validation = build_validations(
        ledger=ledger,
        populations=populations,
        input_provenance=input_provenance,
        phase3a_outputs=phase3a_outputs,
        phase3b_outputs=phase3b_outputs,
        target_table=target_table,
        trace=trace,
        distribution_summary=distribution_summary,
        difference_summary=difference_summary,
        phase3c_outputs=phase3c_outputs,
        final_models=final_models,
        final_targets=final_targets,
        require_notebook=True,
    )
    final_failures = final_validation.loc[
        final_validation["status"] != "PASS"
    ]
    if not final_failures.empty:
        write_csv(final_validation, "validation_results.csv")
        raise RuntimeError(
            "Final validation failed:\n"
            + final_failures[
                ["check_id", "requirement", "detail"]
            ].to_string(index=False)
        )
    write_csv(final_validation, "validation_results.csv")
    write_csv(
        build_requirement_checklist(final_validation),
        "phase3_requirement_checklist.csv",
    )
    runtime = build_runtime_provenance(
        invocation_start_utc=invocation_start_utc,
        invocation_start_perf=invocation_start_perf,
        workers=workers,
        force=force,
        mode="full",
        input_provenance=input_provenance,
        complete=False,
    )
    write_json(runtime, "phase3_runtime_provenance.json")
    write_reports_and_summary(
        input_provenance=input_provenance,
        population_summary=population_summary,
        phase3a_outputs=phase3a_outputs,
        phase3b_outputs=phase3b_outputs,
        distribution_summary=distribution_summary,
        difference_summary=difference_summary,
        phase3c_outputs=phase3c_outputs,
        final_models=final_models,
        final_targets=final_targets,
        validation=final_validation,
        runtime_provenance=runtime,
    )

    # Re-execute once so the notebook embeds the final validation/report state.
    build_notebook()
    second_notebook_runtime = execute_notebook()
    RUNTIME_EVENTS.append(
        {
            "stage": "notebook_final_execution",
            "cache_reused": False,
            "wall_runtime_seconds": second_notebook_runtime,
            "notebook": str(NOTEBOOK_PATH.relative_to(ROOT)),
        }
    )
    final_validation = build_validations(
        ledger=ledger,
        populations=populations,
        input_provenance=input_provenance,
        phase3a_outputs=phase3a_outputs,
        phase3b_outputs=phase3b_outputs,
        target_table=target_table,
        trace=trace,
        distribution_summary=distribution_summary,
        difference_summary=difference_summary,
        phase3c_outputs=phase3c_outputs,
        final_models=final_models,
        final_targets=final_targets,
        require_notebook=True,
    )
    final_failures = final_validation.loc[
        final_validation["status"] != "PASS"
    ]
    write_csv(final_validation, "validation_results.csv")
    if not final_failures.empty:
        raise RuntimeError(
            "Post-report notebook validation failed:\n"
            + final_failures[
                ["check_id", "requirement", "detail"]
            ].to_string(index=False)
        )
    write_csv(
        build_requirement_checklist(final_validation),
        "phase3_requirement_checklist.csv",
    )
    runtime = build_runtime_provenance(
        invocation_start_utc=invocation_start_utc,
        invocation_start_perf=invocation_start_perf,
        workers=workers,
        force=force,
        mode="full",
        input_provenance=input_provenance,
        complete=True,
    )
    write_json(runtime, "phase3_runtime_provenance.json")
    write_reports_and_summary(
        input_provenance=input_provenance,
        population_summary=population_summary,
        phase3a_outputs=phase3a_outputs,
        phase3b_outputs=phase3b_outputs,
        distribution_summary=distribution_summary,
        difference_summary=difference_summary,
        phase3c_outputs=phase3c_outputs,
        final_models=final_models,
        final_targets=final_targets,
        validation=final_validation,
        runtime_provenance=runtime,
    )
    print(
        f"Phase 3 complete: "
        f"{int((final_validation['status'] == 'PASS').sum())}/"
        f"{len(final_validation)} validation checks PASS",
        flush=True,
    )
    return {
        "validation": final_validation,
        "runtime": runtime,
        "final_models": final_models,
        "final_targets": final_targets,
    }


def run_smoke_test(*, workers: int) -> dict[str, Any]:
    started_utc = utc_now()
    started = time.perf_counter()
    ledger, input_provenance = verify_required_inputs()
    smoke_ledger = ledger.sort_values("numeric_simulation_id").head(12).copy()
    smoke_populations = {
        target: smoke_ledger.copy() for target in TARGET_KEYS
    }
    modelling = population_t0_modelling_table(
        smoke_populations["width"], "width"
    )
    mean_rows = run_training_mean_loo(modelling, target="width")
    ridge_rows = [
        run_ridge_loo(
            modelling,
            target="width",
            model_name=model_name,
            workers=workers,
            force=True,
            use_checkpoint=False,
        )
        for model_name in ["linear_ridge", "polynomial_ridge_degree2"]
    ]
    gp_rows = [
        run_gp_loo(
            modelling,
            target="width",
            target_definition="T0",
            analysis_label="phase3_smoke",
            configuration=configuration,
            workers=workers,
            force=True,
            n_restarts_optimizer=N_RESTARTS_OPTIMIZER,
            use_checkpoint=False,
        )
        for configuration in GP_CONFIGURATIONS
    ]
    target_values, trace = build_target_definition_tables(
        smoke_ledger, smoke_populations
    )
    if len(mean_rows) != 12 or any(len(frame) != 12 for frame in ridge_rows + gp_rows):
        raise RuntimeError("Smoke prediction row count failed")
    if len(target_values) != 12 * 3 * 6 or len(trace) != 12 * 6:
        raise RuntimeError("Smoke target-definition row count failed")
    smoke_dir = OUTPUT_DIR / "smoke"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    combined = pd.concat(
        [mean_rows, *ridge_rows, *gp_rows],
        ignore_index=True,
        sort=False,
    )
    combined.to_csv(
        smoke_dir / "smoke_prediction_rows.csv",
        index=False,
        lineterminator="\n",
    )
    target_values.to_csv(
        smoke_dir / "smoke_target_definition_rows.csv",
        index=False,
        lineterminator="\n",
    )
    payload = {
        "started_at_utc": started_utc,
        "completed_at_utc": utc_now(),
        "wall_runtime_seconds": time.perf_counter() - started,
        "scientific_results_reported": False,
        "simulation_count": 12,
        "target_exercised_for_models": "width",
        "mean_prediction_rows": len(mean_rows),
        "ridge_prediction_rows": sum(map(len, ridge_rows)),
        "gp_prediction_rows": sum(map(len, gp_rows)),
        "target_definition_rows": len(target_values),
        "traceability_rows": len(trace),
        "gp_configurations": [item.name for item in GP_CONFIGURATIONS],
        "ridge_models": ["linear_ridge", "polynomial_ridge_degree2"],
        "input_provenance": input_provenance,
        "status": "PASS",
    }
    write_json(payload, "smoke_test_summary.json")
    print(
        f"Phase 3 smoke PASS in {payload['wall_runtime_seconds']:.2f}s; "
        "no scientific conclusions were drawn",
        flush=True,
    )
    return payload


def validate_existing_outputs() -> pd.DataFrame:
    invocation_start_utc = utc_now()
    invocation_start_perf = time.perf_counter()
    ledger, input_provenance = verify_required_inputs()
    populations, _ = build_populations(ledger)
    outputs = load_existing_outputs()
    validation = build_validations(
        ledger=ledger,
        populations=populations,
        input_provenance=input_provenance,
        phase3a_outputs=outputs["phase3a"],
        phase3b_outputs=outputs["phase3b"],
        target_table=outputs["target_table"],
        trace=outputs["trace"],
        distribution_summary=outputs["distribution_summary"],
        difference_summary=outputs["difference_summary"],
        phase3c_outputs=outputs["phase3c"],
        final_models=outputs["final_models"],
        final_targets=outputs["final_targets"],
        require_notebook=True,
    )
    write_csv(validation, "validation_results.csv")
    write_csv(
        build_requirement_checklist(validation),
        "phase3_requirement_checklist.csv",
    )
    existing_runtime = (
        json.loads(
            (OUTPUT_DIR / "phase3_runtime_provenance.json").read_text(
                encoding="utf-8"
            )
        )
        if (OUTPUT_DIR / "phase3_runtime_provenance.json").exists()
        else {}
    )
    RUNTIME_EVENTS.append(
        {
            "stage": "validate_existing_outputs",
            "cache_reused": True,
            "wall_runtime_seconds": time.perf_counter()
            - invocation_start_perf,
            "validation_pass_count": int(
                (validation["status"] == "PASS").sum()
            ),
            "validation_total_count": len(validation),
        }
    )
    runtime = build_runtime_provenance(
        invocation_start_utc=invocation_start_utc,
        invocation_start_perf=invocation_start_perf,
        workers=0,
        force=False,
        mode="validate-only",
        input_provenance=input_provenance,
        complete=bool((validation["status"] == "PASS").all()),
    )
    runtime["prior_full_runtime_provenance"] = existing_runtime
    write_json(runtime, "phase3_runtime_provenance.json")
    write_reports_and_summary(
        input_provenance=input_provenance,
        population_summary=outputs["population_summary"],
        phase3a_outputs=outputs["phase3a"],
        phase3b_outputs=outputs["phase3b"],
        distribution_summary=outputs["distribution_summary"],
        difference_summary=outputs["difference_summary"],
        phase3c_outputs=outputs["phase3c"],
        final_models=outputs["final_models"],
        final_targets=outputs["final_targets"],
        validation=validation,
        runtime_provenance=runtime,
    )
    failures = validation.loc[validation["status"] != "PASS"]
    if not failures.empty:
        raise RuntimeError(
            "Validation failed:\n"
            + failures[
                ["check_id", "requirement", "detail"]
            ].to_string(index=False)
        )
    print(
        f"Validation complete: {len(validation)}/{len(validation)} PASS",
        flush=True,
    )
    return validation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--smoke",
        action="store_true",
        help="Run a small non-scientific protocol smoke test.",
    )
    mode.add_argument(
        "--full",
        action="store_true",
        help="Run the complete Phase 3 study and final validation.",
    )
    mode.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate existing complete Phase 3 outputs without refitting.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute Phase 3 checkpoints instead of reusing valid caches.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="Parallel outer-fold worker count (default: 4).",
    )
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    if args.validate_only and args.force:
        parser.error("--force is incompatible with --validate-only")
    return args


def main() -> None:
    args = parse_args()
    if args.smoke:
        run_smoke_test(workers=args.workers)
    elif args.full:
        run_full_pipeline(workers=args.workers, force=args.force)
    else:
        validate_existing_outputs()


if __name__ == "__main__":
    main()
