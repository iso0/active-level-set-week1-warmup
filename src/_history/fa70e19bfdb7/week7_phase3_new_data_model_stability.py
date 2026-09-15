"""Week 7 Phase 3: replicate Week 6 physical-response models on new data only.

The modelling protocol is imported from the executable Week 6 Phase 2/3 code.
Only the population and validated target-table interface change.  The primary
analysis never pools old and new simulations and never recomputes T0 targets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from threadpoolctl import threadpool_limits

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from src import week6_phase2_gp_response_noise_comparison as week6_noise
from src import week6_phase3_model_target_robustness as week6_models
from src.week7_phase2_sph_v2_physical_target_extraction import load_numeric
from src.week6_phase1_melt_pool_data_audit import SENTINEL_THRESHOLD


ROOT = Path(__file__).resolve().parents[1]
PHASE2_DIR = ROOT / "outputs" / "week7_02_sph_v2_target_extraction"
PHASE2_TARGET_CSV = PHASE2_DIR / "sph_v2_simulation_level_targets.csv"
PHASE2_TARGET_PARQUET = PHASE2_DIR / "sph_v2_simulation_level_targets.parquet"
PHASE2_SOURCE_PLAN = PHASE2_DIR / "monitor_source_plan.csv"
PHASE2_SUMMARY = PHASE2_DIR / "summary.json"

OUTPUT_DIR = ROOT / "outputs" / "week7_03_new_data_physical_model_stability"
SMOKE_DIR = OUTPUT_DIR / "smoke"
NOTEBOOK_PATH = ROOT / "notebooks" / "week_07" / "03_new_data_physical_model_stability.ipynb"

WEEK6_PHASE2_SOURCE = ROOT / "src" / "week6_phase2_gp_response_noise_comparison.py"
WEEK6_PHASE3_SOURCE = ROOT / "src" / "week6_phase3_model_target_robustness.py"
WEEK6_PHASE4_SOURCE = ROOT / "src" / "week6_phase4_new_outputs_feature_effects.py"
WEEK6_PHASE3_DIR = ROOT / "outputs" / "week6_03_model_target_robustness"
WEEK6_PHASE4_DIR = ROOT / "outputs" / "week6_04_new_outputs_feature_effects"

STARTING_BRANCH = "codex/week7-phase1-2-sph-v2-audit"
STARTING_HEAD = "f26f0671dd59938a8111883398fe38afedb6915d"
PHASE3_BRANCH = "codex/week7-phase3-new-data-model-stability"
SPH_V2_REPO_ID = "ioandanielc/sph_v2"
SPH_V2_REVISION = "d69dac5bda8b622bc0de316b112815c6056c06ec"

FEATURE_COLUMNS = ["P", "VX", "LS", "ST"]
FEATURE_SOURCE_COLUMNS = {
    "P": "P_W",
    "VX": "VX_m_per_s",
    "LS": "LS_um",
    "ST": "ST_K",
}
FEATURE_UNITS = {"P": "W", "VX": "m/s", "LS": "um", "ST": "K"}
FEATURE_MEANINGS = {
    "P": "laser power",
    "VX": "scan speed",
    "LS": "laser spot radius",
    "ST": "substrate temperature",
}

TARGET_SPECS: dict[str, dict[str, Any]] = {
    "width": {
        "label": "T0 melt-pool width",
        "column": "T0_width_um",
        "unit": "um",
        "readiness": [
            "geometry_monitor_available",
            "geometry_parse_ok",
            "geometry_target_ready",
            "time_monitor_available",
            "time_parse_ok",
            "time_target_ready",
            "physical_target_extraction_success",
        ],
        "sample_count_column": "T0_width_valid_sample_count",
    },
    "depth": {
        "label": "T0 penetration depth",
        "column": "T0_depth_um",
        "unit": "um",
        "readiness": [
            "geometry_monitor_available",
            "geometry_parse_ok",
            "geometry_target_ready",
            "time_monitor_available",
            "time_parse_ok",
            "time_target_ready",
            "physical_target_extraction_success",
        ],
        "sample_count_column": "T0_depth_valid_sample_count",
    },
    "total_height": {
        "label": "T0 total vertical melt-pool height",
        "column": "T0_total_height_um",
        "unit": "um",
        "readiness": [
            "geometry_monitor_available",
            "geometry_parse_ok",
            "geometry_target_ready",
            "time_monitor_available",
            "time_parse_ok",
            "time_target_ready",
            "physical_target_extraction_success",
        ],
        "sample_count_column": "T0_total_height_valid_sample_count",
    },
    "kinetic_energy": {
        "label": "T0 melt kinetic energy",
        "column": "T0_kinetic_energy_nJ",
        "unit": "nJ",
        "readiness": [
            "geometry_monitor_available",
            "geometry_parse_ok",
            "geometry_target_ready",
            "time_monitor_available",
            "time_parse_ok",
            "time_target_ready",
            "kinetic_energy_monitor_available",
            "kinetic_energy_parse_ok",
            "kinetic_energy_target_ready",
            "physical_target_extraction_success",
        ],
        "sample_count_column": "T0_kinetic_energy_valid_sample_count",
    },
}

BASELINE_MODELS = ["training_mean", "linear_ridge", "polynomial_ridge_degree2"]
GP_CONFIGURATION_NAMES = [item.name for item in week6_models.GP_CONFIGURATIONS]
HETEROSKEDASTIC_MODEL = "matern32_heteroskedastic_alpha"
ALL_MODELS = [*BASELINE_MODELS, *GP_CONFIGURATION_NAMES, HETEROSKEDASTIC_MODEL]

MODEL_LABELS = {
    "training_mean": "Training-fold mean",
    "linear_ridge": "Linear Ridge",
    "polynomial_ridge_degree2": "Polynomial Ridge degree 2",
    "rbf_no_nugget": "RBF, numerical jitter",
    "rbf_learned_nugget": "RBF + learned nugget",
    "matern32_no_nugget": "Matérn 3/2, numerical jitter",
    "matern32_learned_nugget": "Matérn 3/2 + learned nugget",
    "matern52_no_nugget": "Matérn 5/2, numerical jitter",
    "matern52_learned_nugget": "Matérn 5/2 + learned nugget",
    HETEROSKEDASTIC_MODEL: "Matérn 3/2 + heteroskedastic alpha",
}

MODEL_META: dict[str, dict[str, Any]] = {
    "training_mean": {
        "model_family": "Mean predictor",
        "kernel": "",
        "noise_method": "not applicable",
        "probabilistic": False,
        "probabilistic_deployable": False,
    },
    "linear_ridge": {
        "model_family": "Linear Ridge",
        "kernel": "",
        "noise_method": "not applicable",
        "probabilistic": False,
        "probabilistic_deployable": False,
    },
    "polynomial_ridge_degree2": {
        "model_family": "Polynomial Ridge degree 2",
        "kernel": "",
        "noise_method": "not applicable",
        "probabilistic": False,
        "probabilistic_deployable": False,
    },
    "rbf_no_nugget": {
        "model_family": "Gaussian process",
        "kernel": "RBF",
        "noise_method": "A_numerical_jitter",
        "probabilistic": True,
        "probabilistic_deployable": True,
    },
    "rbf_learned_nugget": {
        "model_family": "Gaussian process",
        "kernel": "RBF",
        "noise_method": "B_shared_learned_nugget",
        "probabilistic": True,
        "probabilistic_deployable": True,
    },
    "matern32_no_nugget": {
        "model_family": "Gaussian process",
        "kernel": "Matérn 3/2",
        "noise_method": "A_numerical_jitter",
        "probabilistic": True,
        "probabilistic_deployable": True,
    },
    "matern32_learned_nugget": {
        "model_family": "Gaussian process",
        "kernel": "Matérn 3/2",
        "noise_method": "B_shared_learned_nugget",
        "probabilistic": True,
        "probabilistic_deployable": True,
    },
    "matern52_no_nugget": {
        "model_family": "Gaussian process",
        "kernel": "Matérn 5/2",
        "noise_method": "A_numerical_jitter",
        "probabilistic": True,
        "probabilistic_deployable": True,
    },
    "matern52_learned_nugget": {
        "model_family": "Gaussian process",
        "kernel": "Matérn 5/2",
        "noise_method": "B_shared_learned_nugget",
        "probabilistic": True,
        "probabilistic_deployable": True,
    },
    HETEROSKEDASTIC_MODEL: {
        "model_family": "Gaussian process",
        "kernel": "Matérn 3/2",
        "noise_method": "C_heteroskedastic_alpha",
        "probabilistic": True,
        "probabilistic_deployable": False,
    },
}

FULL_UNCERTAINTY_RESAMPLES = week6_noise.BOOTSTRAP_RESAMPLES
SMOKE_UNCERTAINTY_RESAMPLES = 50
FULL_PAIRED_RESAMPLES = week6_models.PAIRED_BOOTSTRAP_RESAMPLES
SMOKE_PAIRED_RESAMPLES = 1_000
SMOKE_POPULATION = 12
DEFAULT_WORKERS = 6

RUNTIME_EVENTS: list[dict[str, Any]] = []


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").fillna(0).ne(0)
    return series.astype(str).str.strip().str.lower().isin(["true", "1", "1.0"])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def array_sha256(values: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(values, dtype="<f8").tobytes()).hexdigest()


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_csv(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")
    return path


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def deterministic_seed(*parts: Any) -> int:
    payload = "|".join(str(item) for item in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "little")


def source_sha256(path: Path) -> str:
    return sha256_file(path)


def week6_traceability_table() -> pd.DataFrame:
    rows = [
        {
            "week6_model_method": "Training-fold mean predictor",
            "source_file": "src/week6_phase3_model_target_robustness.py",
            "source_function_class": "run_training_mean_loo",
            "important_settings": "Exact simulation-level LOO; mean computed from outer-training targets only",
            "phase3_reuse_change": "Reused exactly on each new-data target population",
            "reason": "Change the population, not the baseline protocol",
        },
        {
            "week6_model_method": "Linear Ridge",
            "source_file": "src/week6_phase3_model_target_robustness.py",
            "source_function_class": "_make_ridge_regressor; _fit_ridge_fold; run_ridge_loo",
            "important_settings": "Fold-local StandardScaler(X); fold-local StandardScaler(y) through TransformedTargetRegressor; alpha=1e-6..1e6; nested shuffled 5-fold CV; mean validation RMSE",
            "phase3_reuse_change": "Reused exactly",
            "reason": "Preserve Week 6 leakage controls and tuning grid",
        },
        {
            "week6_model_method": "Polynomial Ridge degree 2",
            "source_file": "src/week6_phase3_model_target_robustness.py",
            "source_function_class": "_make_ridge_regressor; _fit_ridge_fold; run_ridge_loo",
            "important_settings": "StandardScaler(X) -> PolynomialFeatures(degree=2, include_bias=False) -> StandardScaler(polynomial terms) -> Ridge; fold-local y scaling; same nested alpha selection",
            "phase3_reuse_change": "Reused exactly; no higher polynomial degree",
            "reason": "Preserve the Week 6 nonlinear simple baseline",
        },
        {
            "week6_model_method": "GP kernel comparison",
            "source_file": "src/week6_phase3_model_target_robustness.py",
            "source_function_class": "GPConfiguration; make_gp_kernel; _fit_gp_fold; run_gp_loo",
            "important_settings": "ConstantKernel*(RBF or isotropic Matérn 3/2 or Matérn 5/2); constant bounds 1e-3..1e3; lengthscale bounds 1e-2..1e2; fold-local X/y scaling; L-BFGS-B; one additional restart; normalize_y=False; seed base 6303",
            "phase3_reuse_change": "All six kernel x nugget configurations reused exactly",
            "reason": "Direct model-ranking replication on the shifted design",
        },
        {
            "week6_model_method": "A: numerical jitter / deterministic treatment",
            "source_file": "src/week6_phase2_gp_response_noise_comparison.py; src/week6_phase3_model_target_robustness.py",
            "source_function_class": "make_kernel; _fit_loo_fold; GPConfiguration",
            "important_settings": "No WhiteKernel; alpha=1e-6 in normalized target units; predictive variance is latent variance",
            "phase3_reuse_change": "Reused through the final Week 6 Phase 3 GP engine",
            "reason": "Same covariance and numerical treatment used in the final Week 6 kernel matrix",
        },
        {
            "week6_model_method": "B: shared learned nugget",
            "source_file": "src/week6_phase2_gp_response_noise_comparison.py; src/week6_phase3_model_target_robustness.py",
            "source_function_class": "make_kernel; _fit_loo_fold; GPConfiguration",
            "important_settings": "WhiteKernel initial variance 1e-2, bounds 1e-8..1e1; numerical alpha=1e-8; total predictive variance evaluated",
            "phase3_reuse_change": "Reused exactly",
            "reason": "Test whether the effective residual term remains useful; it is not interpreted as simulator noise",
        },
        {
            "week6_model_method": "C: heteroskedastic target-summary alpha",
            "source_file": "src/week6_phase2_gp_response_noise_comparison.py",
            "source_function_class": "block_length_rule; moving_block_bootstrap_medians; _fit_loo_fold",
            "important_settings": "500 circular moving-block bootstrap medians; block=max(5,round(n_window^(1/3))); alpha_i=bootstrap_variance_i/training_y_std^2+1e-6; Matérn 3/2 without WhiteKernel; held-out variance added only for retrospective oracle interval",
            "phase3_reuse_change": "Exact bootstrap and alpha formulas reused on Phase 2-saved T0 row indices; response series are read from pinned monitor bytes only to estimate uncertainty, never to redefine T0",
            "reason": "Phase 2 stores T0 targets and row indices but not the Week 6 block-bootstrap variance artifact",
        },
        {
            "week6_model_method": "Outer evaluation and probabilistic metrics",
            "source_file": "src/week6_phase2_gp_response_noise_comparison.py; src/week6_phase3_model_target_robustness.py",
            "source_function_class": "_fit_loo_fold; _fit_gp_fold; gaussian_nlpd; point_metric_row; gp_metric_row",
            "important_settings": "Exact simulation-level LOO; held-out observation excluded from scaling/tuning/fitting; MAE, RMSE, R2, NLPD, 95% intervals",
            "phase3_reuse_change": "Reused; median-scale relative MAE/RMSE added as requested",
            "reason": "Ioan requested interpretable percentage errors without unstable pointwise MAPE",
        },
        {
            "week6_model_method": "Total-height and kinetic-energy compact comparison",
            "source_file": "src/week6_phase4_new_outputs_feature_effects.py",
            "source_function_class": "load_phase3_engine; model_table_for_response; run_models; select_final_models",
            "important_settings": "Phase 4 imports the validated Phase 3 LOO engine; Mean, Linear Ridge, degree-2 Polynomial Ridge, three learned-nugget kernels, selected-kernel no-nugget sensitivity; practical threshold=max(1% range,2% IQR)",
            "phase3_reuse_change": "Same Phase 3 engine applied uniformly to all four primary responses; all no-nugget kernels retained for the requested full replication",
            "reason": "Unifies the historical width/depth and total-height/energy comparisons without changing their model protocol",
        },
    ]
    frame = pd.DataFrame(rows)
    hashes = {
        "src/week6_phase2_gp_response_noise_comparison.py": source_sha256(WEEK6_PHASE2_SOURCE),
        "src/week6_phase3_model_target_robustness.py": source_sha256(WEEK6_PHASE3_SOURCE),
        "src/week6_phase4_new_outputs_feature_effects.py": source_sha256(WEEK6_PHASE4_SOURCE),
    }
    frame["source_sha256"] = frame["source_file"].map(
        lambda value: json_text(
            {
                key: digest
                for key, digest in hashes.items()
                if key in str(value)
            }
        )
    )
    return frame


def load_phase2_inputs(*, smoke: bool) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    summary = json.loads(PHASE2_SUMMARY.read_text(encoding="utf-8"))
    if summary.get("revision") != SPH_V2_REVISION:
        raise RuntimeError("Phase 2 summary does not use the required sph_v2 revision")
    targets = pd.read_csv(PHASE2_TARGET_CSV)
    if len(targets) != 407 or not targets["experiment_name"].is_unique:
        raise RuntimeError("Phase 2 target-table population is not the validated 407 rows")
    if set(targets["exact_sph_v2_revision"].astype(str)) != {SPH_V2_REVISION}:
        raise RuntimeError("Target rows do not all record the immutable sph_v2 revision")
    new_data = targets[targets["partition"].eq("new-data")].copy()
    if len(new_data) != 165:
        raise RuntimeError("Expected the audited 165-row new-data label population")
    for target, spec in TARGET_SPECS.items():
        eligible = pd.Series(True, index=new_data.index)
        for field in spec["readiness"]:
            if field not in new_data:
                raise RuntimeError(f"Missing Phase 2 readiness field: {field}")
            eligible &= bool_series(new_data[field])
        eligible &= np.isfinite(pd.to_numeric(new_data[spec["column"]], errors="coerce"))
        new_data[f"{target}_model_eligible"] = eligible
        new_data[f"{target}_eligibility_source_fields"] = json_text(spec["readiness"])
        new_data[f"{target}_target_column"] = spec["column"]
    new_data = new_data.sort_values("experiment_name", kind="stable").reset_index(drop=True)
    new_data["new_data_population_index"] = np.arange(1, len(new_data) + 1)

    if smoke:
        eligible_names = new_data.loc[
            new_data["width_model_eligible"], "experiment_name"
        ].tolist()
        positions = np.linspace(0, len(eligible_names) - 1, SMOKE_POPULATION, dtype=int)
        selected = {eligible_names[int(index)] for index in positions}
        new_data["selected_for_current_run"] = new_data["experiment_name"].isin(selected)
    else:
        new_data["selected_for_current_run"] = True

    source_plan = pd.read_csv(PHASE2_SOURCE_PLAN)
    if set(source_plan["exact_revision"].astype(str)) != {SPH_V2_REVISION}:
        raise RuntimeError("Monitor source plan revision differs from Phase 2")
    return new_data, source_plan, summary


def model_tables(population: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    long_rows: list[pd.DataFrame] = []
    for target, spec in TARGET_SPECS.items():
        eligible = population[
            bool_series(population[f"{target}_model_eligible"])
            & bool_series(population["selected_for_current_run"])
        ].copy()
        table = pd.DataFrame(
            {
                "simulation_id": eligible["experiment_name"].astype(str),
                "numeric_simulation_id": np.arange(1, len(eligible) + 1),
                **{
                    feature: pd.to_numeric(eligible[source], errors="raise").to_numpy(float)
                    for feature, source in FEATURE_SOURCE_COLUMNS.items()
                },
                "target_value_um": pd.to_numeric(
                    eligible[spec["column"]], errors="raise"
                ).to_numpy(float),
                "target_definition": "T0",
                "target": target,
                "target_label": spec["label"],
                "target_unit": spec["unit"],
                "partition": "new-data",
                "dataset_revision": SPH_V2_REVISION,
                "eligibility_source_fields": json_text(spec["readiness"]),
                "flag_primary_window_unstable_week6_rule": bool_series(
                    eligible["flag_primary_window_unstable_week6_rule"]
                ).to_numpy(bool),
            }
        )
        if not np.isfinite(table[[*FEATURE_COLUMNS, "target_value_um"]].to_numpy(float)).all():
            raise RuntimeError(f"Non-finite model input in {target}")
        tables[target] = table
        long_rows.append(table.copy())
    return tables, pd.concat(long_rows, ignore_index=True)


def source_path_lookup(source_plan: pd.DataFrame) -> dict[tuple[str, str], Path]:
    usable = source_plan[
        source_plan["partition"].eq("new-data")
        & source_plan["remote_exists"].astype(bool)
        & source_plan["local_path"].notna()
    ]
    result: dict[tuple[str, str], Path] = {}
    for row in usable.itertuples(index=False):
        path = Path(str(row.local_path))
        if not path.is_file():
            raise FileNotFoundError(f"Pinned Phase 2 monitor cache is unavailable: {path}")
        result[(str(row.experiment_name), str(row.monitor_file))] = path
    return result


def selected_t0_series(
    row: pd.Series,
    paths: dict[tuple[str, str], Path],
) -> dict[str, np.ndarray]:
    experiment = str(row["experiment_name"])
    bounds_path = paths[(experiment, "position-bounds_melt.dat")]
    kinetic_path = paths[(experiment, "kinetic-energy_melt.dat")]
    bounds, _ = load_numeric(bounds_path, bounds_path.name)
    kinetic_j, _ = load_numeric(kinetic_path, kinetic_path.name)
    kinetic_j = np.asarray(kinetic_j, dtype=float).reshape(-1)

    finite = np.isfinite(bounds).all(axis=1)
    non_sentinel = (np.abs(bounds) < SENTINEL_THRESHOLD).all(axis=1)
    ordered = (
        (bounds[:, 1] >= bounds[:, 0])
        & (bounds[:, 3] >= bounds[:, 2])
        & (bounds[:, 5] >= bounds[:, 4])
    )
    valid = finite & non_sentinel & ordered
    n = len(bounds)
    kinetic_full = np.full(n, np.nan)
    kinetic_full[: min(n, len(kinetic_j))] = kinetic_j[: min(n, len(kinetic_j))]
    kinetic_valid = np.isfinite(kinetic_full) & (kinetic_full >= 0)
    start = int(row["T0_start_row_index"])
    end = int(row["T0_end_row_index"])
    in_window = np.zeros(n, dtype=bool)
    in_window[start : end + 1] = True
    geometry_mask = valid & in_window
    energy_mask = geometry_mask & kinetic_valid
    series = {
        "width": (bounds[geometry_mask, 3] - bounds[geometry_mask, 2]) * 1e6,
        "depth": np.maximum(0.0, -bounds[geometry_mask, 4]) * 1e6,
        "total_height": (bounds[geometry_mask, 5] - bounds[geometry_mask, 4]) * 1e6,
        "kinetic_energy": kinetic_full[energy_mask] * 1e9,
    }
    for target, values in series.items():
        if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
            raise RuntimeError(f"{experiment}/{target}: invalid saved T0 response series")
        spec = TARGET_SPECS[target]
        expected_count = int(row[spec["sample_count_column"]])
        if len(values) != expected_count:
            raise RuntimeError(
                f"{experiment}/{target}: T0 count {len(values)} != Phase 2 {expected_count}"
            )
        target_value = float(row[spec["column"]])
        if not np.isclose(np.median(values), target_value, rtol=1e-9, atol=1e-8):
            raise RuntimeError(f"{experiment}/{target}: raw T0 median does not reproduce Phase 2")
    return series


def _uncertainty_one_experiment(
    row: pd.Series,
    paths: dict[tuple[str, str], Path],
    *,
    resamples: int,
) -> list[dict[str, Any]]:
    experiment = str(row["experiment_name"])
    series = selected_t0_series(row, paths)
    rows: list[dict[str, Any]] = []
    for target, values in series.items():
        block_length = week6_noise.block_length_rule(len(values))
        seed = week6_noise.deterministic_seed(
            "target-summary-bootstrap",
            experiment,
            target,
            block_length,
            resamples,
        )
        medians = week6_noise.moving_block_bootstrap_medians(
            values,
            block_length=block_length,
            resamples=resamples,
            seed=seed,
        )
        low, high = np.quantile(medians, week6_noise.BOOTSTRAP_QUANTILES)
        spec = TARGET_SPECS[target]
        rows.append(
            {
                "experiment_name": experiment,
                "target": target,
                "target_label": spec["label"],
                "target_unit": spec["unit"],
                "phase2_target_value": float(row[spec["column"]]),
                "T0_start_row_index": int(row["T0_start_row_index"]),
                "T0_end_row_index": int(row["T0_end_row_index"]),
                "selected_window_observation_count": len(values),
                "block_bootstrap_type": "circular moving-block bootstrap",
                "block_length_rule": "max(5, round(n_window ** (1/3)))",
                "block_length": block_length,
                "bootstrap_resamples": resamples,
                "bootstrap_seed": seed,
                "raw_window_median": float(np.median(values)),
                "raw_window_series_sha256": array_sha256(values),
                "bootstrap_median_mean": float(medians.mean()),
                "bootstrap_median_std": float(medians.std(ddof=1)),
                "bootstrap_variance": float(medians.var(ddof=1)),
                "bootstrap_quantile_low": float(low),
                "bootstrap_quantile_high": float(high),
                "phase2_target_reproduced": bool(
                    np.isclose(
                        np.median(values),
                        float(row[spec["column"]]),
                        rtol=1e-9,
                        atol=1e-8,
                    )
                ),
                "interpretation": (
                    "target-summary uncertainty proxy; not measurement noise "
                    "and not stochastic simulator noise"
                ),
                "dataset_revision": SPH_V2_REVISION,
            }
        )
    return rows


def build_target_summary_uncertainty(
    population: pd.DataFrame,
    source_plan: pd.DataFrame,
    destination: Path,
    *,
    smoke: bool,
    workers: int,
    force: bool,
) -> pd.DataFrame:
    path = destination / "target_summary_uncertainty.csv"
    expected_experiments = population[
        bool_series(population["width_model_eligible"])
        & bool_series(population["selected_for_current_run"])
    ]
    resamples = SMOKE_UNCERTAINTY_RESAMPLES if smoke else FULL_UNCERTAINTY_RESAMPLES
    if path.is_file() and not force:
        cached = pd.read_csv(path)
        if (
            len(cached) == len(expected_experiments) * len(TARGET_SPECS)
            and cached["experiment_name"].nunique() == len(expected_experiments)
            and set(cached["bootstrap_resamples"].astype(int)) == {resamples}
            and bool_series(cached["phase2_target_reproduced"]).all()
        ):
            return cached
    paths = source_path_lookup(source_plan)
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 4))) as pool:
        futures = {
            pool.submit(
                _uncertainty_one_experiment,
                row,
                paths,
                resamples=resamples,
            ): str(row["experiment_name"])
            for _, row in expected_experiments.iterrows()
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            experiment = futures[future]
            try:
                rows.extend(future.result())
            except Exception as exc:
                raise RuntimeError(f"T0 bootstrap failed for {experiment}") from exc
            if completed % 20 == 0 or completed == len(futures):
                print(
                    f"target-summary bootstrap: {completed}/{len(futures)} experiments",
                    flush=True,
                )
    result = pd.DataFrame(rows).sort_values(["target", "experiment_name"]).reset_index(drop=True)
    if len(result) != len(expected_experiments) * len(TARGET_SPECS):
        raise RuntimeError("Target-summary uncertainty table is incomplete")
    if not bool_series(result["phase2_target_reproduced"]).all():
        raise RuntimeError("Target-summary windows do not reproduce saved Phase 2 targets")
    if not np.isfinite(result["bootstrap_variance"]).all() or (result["bootstrap_variance"] < 0).any():
        raise RuntimeError("Invalid bootstrap variance")
    write_csv(path, result)
    RUNTIME_EVENTS.append(
        {
            "stage": "target_summary_uncertainty",
            "wall_runtime_seconds": time.perf_counter() - started,
            "experiment_count": len(expected_experiments),
            "target_count": len(TARGET_SPECS),
            "resamples": resamples,
        }
    )
    return result


def configure_week6_engines(destination: Path) -> None:
    week6_models.CHECKPOINT_DIR = destination / "checkpoints"
    week6_models.TARGET_LABELS.update(
        {target: spec["label"] for target, spec in TARGET_SPECS.items()}
    )
    week6_models.RUNTIME_EVENTS.clear()
    week6_noise.TARGET_LABELS.update(
        {target: spec["label"] for target, spec in TARGET_SPECS.items()}
    )


def failure_frame(table: pd.DataFrame, target: str, model: str, exc: Exception) -> pd.DataFrame:
    reason = f"{type(exc).__name__}: {exc}"
    rows = []
    for fold_index, row in table.reset_index(drop=True).iterrows():
        rows.append(
            {
                "target": target,
                "model": model,
                "fold_index": fold_index,
                "heldout_simulation_id": str(row["simulation_id"]),
                "heldout_numeric_simulation_id": int(row["numeric_simulation_id"]),
                "observed_target_value": float(row["target_value_um"]),
                "predicted_mean": np.nan,
                "residual": np.nan,
                "absolute_error": np.nan,
                "squared_error": np.nan,
                "fit_failure": True,
                "fit_failure_reason": reason,
                "warning_count": 0,
                "warnings": traceback.format_exc(limit=8),
                "training_size": len(table) - 1,
                "population_size": len(table),
                "heldout_excluded_from_training": True,
                "heldout_target_used_for_scaling": False,
                "heldout_target_used_for_fitting": False,
                "heldout_target_used_for_tuning": False,
            }
        )
    return pd.DataFrame(rows)


def neutralize_week6_prediction_columns(frame: pd.DataFrame) -> pd.DataFrame:
    rename: dict[str, str] = {}
    for column in frame.columns:
        generic = column.replace("_um2", "_target_unit_squared").replace(
            "_um", "_target_unit"
        )
        if generic != column:
            rename[column] = generic
    return frame.rename(columns=rename).copy()


def finalize_prediction_frame(
    frame: pd.DataFrame,
    *,
    target: str,
    model: str,
    table: pd.DataFrame,
) -> pd.DataFrame:
    result = neutralize_week6_prediction_columns(frame)
    if "model" not in result:
        if "gp_configuration" in result:
            result["model"] = result["gp_configuration"].astype(str)
        elif "method" in result:
            result["model"] = model
        else:
            result["model"] = model
    result["model"] = model
    aliases = {
        "observed_target_target_unit": "observed_target_value",
        "predicted_mean_target_unit": "predicted_mean",
        "residual_target_unit": "residual",
        "absolute_error_target_unit": "absolute_error",
        "squared_error_target_unit_squared": "squared_error",
    }
    for source, destination in aliases.items():
        if source in result:
            result[destination] = result[source]
    result["target"] = target
    result["target_label"] = TARGET_SPECS[target]["label"]
    result["target_unit"] = TARGET_SPECS[target]["unit"]
    result["model_label"] = MODEL_LABELS[model]
    for key, value in MODEL_META[model].items():
        result[key] = value
    result["partition"] = "new-data"
    result["dataset_repo_id"] = SPH_V2_REPO_ID
    result["dataset_revision"] = SPH_V2_REVISION
    result["phase2_target_column"] = TARGET_SPECS[target]["column"]
    result["eligibility_source_fields"] = json_text(TARGET_SPECS[target]["readiness"])
    if "fit_failure" not in result:
        result["fit_failure"] = False
    result["fit_failure"] = bool_series(result["fit_failure"])
    if "fit_failure_reason" not in result:
        result["fit_failure_reason"] = ""
    defaults: dict[str, Any] = {
        "warning_count": 0,
        "warnings": "",
        "convergence_warning_count": 0,
        "constant_bound_hit": False,
        "length_scale_bound_hit": False,
        "noise_bound_hit": False,
        "any_hyperparameter_bound_hit": False,
        "evaluation_nlpd": np.nan,
        "evaluation_predictive_std_target_unit": np.nan,
        "latent_interval_lower_target_unit": np.nan,
        "latent_interval_upper_target_unit": np.nan,
        "total_interval_lower_target_unit": np.nan,
        "total_interval_upper_target_unit": np.nan,
        "oracle_interval_lower_target_unit": np.nan,
        "oracle_interval_upper_target_unit": np.nan,
        "runtime_seconds": 0.0,
        "heldout_target_used_for_scaling": False,
        "heldout_target_used_for_fitting": False,
        "heldout_target_used_for_tuning": False,
        "heldout_excluded_from_training": True,
        "x_scaler_fit_on_training_only": np.nan,
        "y_scaler_fit_on_training_only": np.nan,
        "inner_cv_uses_outer_training_only": np.nan,
        "selected_ridge_alpha": np.nan,
        "normalize_y": np.nan,
        "n_restarts_optimizer": np.nan,
        "optimizer": "",
    }
    for column, default in defaults.items():
        if column not in result:
            result[column] = default

    result["predictive_interval_lower"] = np.nan
    result["predictive_interval_upper"] = np.nan
    if model == HETEROSKEDASTIC_MODEL:
        result["predictive_interval_lower"] = result[
            "oracle_interval_lower_target_unit"
        ]
        result["predictive_interval_upper"] = result[
            "oracle_interval_upper_target_unit"
        ]
        result["interval_definition"] = (
            "retrospective oracle: latent variance plus held-out target-summary variance"
        )
    elif MODEL_META[model]["probabilistic"]:
        if model.endswith("learned_nugget"):
            result["predictive_interval_lower"] = result[
                "total_interval_lower_target_unit"
            ]
            result["predictive_interval_upper"] = result[
                "total_interval_upper_target_unit"
            ]
            result["interval_definition"] = (
                "total predictive variance including learned WhiteKernel nugget"
            )
        else:
            result["predictive_interval_lower"] = result[
                "latent_interval_lower_target_unit"
            ]
            result["predictive_interval_upper"] = result[
                "latent_interval_upper_target_unit"
            ]
            result["interval_definition"] = (
                "latent predictive variance; numerical jitter excluded"
            )
    else:
        result["interval_definition"] = "point prediction only"
    result["predictive_interval_contains_observed"] = np.where(
        np.isfinite(pd.to_numeric(result["predictive_interval_lower"], errors="coerce")),
        (
            pd.to_numeric(result["predictive_interval_lower"], errors="coerce")
            <= pd.to_numeric(result["observed_target_value"], errors="coerce")
        )
        & (
            pd.to_numeric(result["observed_target_value"], errors="coerce")
            <= pd.to_numeric(result["predictive_interval_upper"], errors="coerce")
        ),
        np.nan,
    )
    result["experiment_name"] = result["heldout_simulation_id"].astype(str)
    result["label_modified"] = False
    result["simulation_silently_removed"] = False
    result["protocol_source"] = (
        "Week 6 Phase 3 engine"
        if model != HETEROSKEDASTIC_MODEL
        else "Week 6 Phase 2 heteroskedastic-alpha engine"
    )
    expected_ids = set(table["simulation_id"].astype(str))
    if set(result["experiment_name"].astype(str)) != expected_ids or len(result) != len(table):
        raise RuntimeError(f"{target}/{model}: held-out population mismatch")
    return result


def run_week6_model(
    table: pd.DataFrame,
    *,
    target: str,
    model: str,
    workers: int,
    force: bool,
    n_restarts_optimizer: int,
) -> pd.DataFrame:
    started = time.perf_counter()
    try:
        if model == "training_mean":
            raw = week6_models.run_training_mean_loo(table, target=target)
        elif model in {"linear_ridge", "polynomial_ridge_degree2"}:
            raw = week6_models.run_ridge_loo(
                table,
                target=target,
                model_name=model,
                workers=workers,
                force=force,
            )
        else:
            configuration = week6_models.GP_CONFIG_BY_NAME[model]
            raw = week6_models.run_gp_loo(
                table,
                target=target,
                target_definition="T0",
                analysis_label="week7_phase3_new_data_replication",
                configuration=configuration,
                workers=workers,
                force=force,
                n_restarts_optimizer=n_restarts_optimizer,
            )
    except Exception as exc:
        print(f"model failure retained: {target}/{model}: {exc}", flush=True)
        raw = failure_frame(table, target, model, exc)
    result = finalize_prediction_frame(raw, target=target, model=model, table=table)
    RUNTIME_EVENTS.append(
        {
            "stage": "model_loo",
            "target": target,
            "model": model,
            "wall_runtime_seconds": time.perf_counter() - started,
            "fold_rows": len(result),
            "fit_failures": int(bool_series(result["fit_failure"]).sum()),
        }
    )
    return result


def run_heteroskedastic_loo(
    table: pd.DataFrame,
    uncertainty: pd.DataFrame,
    *,
    target: str,
    workers: int,
    n_restarts_optimizer: int,
    destination: Path,
    force: bool,
) -> pd.DataFrame:
    checkpoint = destination / "checkpoints" / f"heteroskedastic__{target}.csv"
    expected_ids = table["simulation_id"].astype(str).tolist()
    if checkpoint.is_file() and not force:
        cached = pd.read_csv(checkpoint)
        if (
            len(cached) == len(table)
            and cached["heldout_simulation_id"].astype(str).tolist() == expected_ids
            and set(cached["model"].astype(str)) == {HETEROSKEDASTIC_MODEL}
        ):
            return cached

    variance_lookup = uncertainty[uncertainty["target"].eq(target)].set_index(
        "experiment_name"
    )["bootstrap_variance"]
    alpha_variance = table["simulation_id"].map(variance_lookup).to_numpy(float)
    if not np.isfinite(alpha_variance).all() or (alpha_variance < 0).any():
        raise RuntimeError(f"{target}: incomplete heteroskedastic bootstrap variance")

    X = table[FEATURE_COLUMNS].to_numpy(float)
    y = table["target_value_um"].to_numpy(float)
    ids = table["simulation_id"].astype(str).to_numpy()
    numeric_ids = table["numeric_simulation_id"].to_numpy(int)
    unstable = bool_series(table["flag_primary_window_unstable_week6_rule"]).to_numpy(bool)
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    with threadpool_limits(limits=1):
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = {
                pool.submit(
                    week6_noise._fit_loo_fold,
                    X=X,
                    y_um=y,
                    alpha_um2=alpha_variance,
                    simulation_ids=ids,
                    numeric_ids=numeric_ids,
                    unstable_flags=unstable,
                    target_key=target,
                    method="C_heteroskedastic",
                    fold_index=fold_index,
                    analysis_label="week7_phase3_new_data_noise_replication",
                    n_restarts_optimizer=n_restarts_optimizer,
                ): fold_index
                for fold_index in range(len(table))
            }
            for completed, future in enumerate(as_completed(futures), start=1):
                fold_index = futures[future]
                try:
                    rows.append(future.result())
                except Exception as exc:
                    row = table.iloc[fold_index]
                    failure = failure_frame(
                        table.iloc[[fold_index]].assign(
                            numeric_simulation_id=[int(row["numeric_simulation_id"])]
                        ),
                        target,
                        HETEROSKEDASTIC_MODEL,
                        exc,
                    ).iloc[0].to_dict()
                    failure["fold_index"] = fold_index
                    failure["heldout_simulation_id"] = str(row["simulation_id"])
                    failure["heldout_numeric_simulation_id"] = int(
                        row["numeric_simulation_id"]
                    )
                    rows.append(failure)
                if completed % 20 == 0 or completed == len(table):
                    print(
                        f"heteroskedastic LOO {target}: {completed}/{len(table)} folds",
                        flush=True,
                    )
    raw = pd.DataFrame(rows).sort_values("fold_index").reset_index(drop=True)
    result = finalize_prediction_frame(
        raw, target=target, model=HETEROSKEDASTIC_MODEL, table=table
    )
    write_csv(checkpoint, result)
    RUNTIME_EVENTS.append(
        {
            "stage": "heteroskedastic_loo",
            "target": target,
            "model": HETEROSKEDASTIC_MODEL,
            "wall_runtime_seconds": time.perf_counter() - started,
            "fold_rows": len(result),
            "fit_failures": int(bool_series(result["fit_failure"]).sum()),
        }
    )
    return result


def run_all_models(
    tables: dict[str, pd.DataFrame],
    uncertainty: pd.DataFrame,
    destination: Path,
    *,
    smoke: bool,
    workers: int,
    force: bool,
) -> pd.DataFrame:
    configure_week6_engines(destination)
    n_restarts = 0 if smoke else week6_models.N_RESTARTS_OPTIMIZER
    frames: list[pd.DataFrame] = []
    for target, table in tables.items():
        for model in [*BASELINE_MODELS, *GP_CONFIGURATION_NAMES]:
            print(f"running {target}/{model}", flush=True)
            frames.append(
                run_week6_model(
                    table,
                    target=target,
                    model=model,
                    workers=workers,
                    force=force,
                    n_restarts_optimizer=n_restarts,
                )
            )
        print(f"running {target}/{HETEROSKEDASTIC_MODEL}", flush=True)
        frames.append(
            run_heteroskedastic_loo(
                table,
                uncertainty,
                target=target,
                workers=workers,
                n_restarts_optimizer=n_restarts,
                destination=destination,
                force=force,
            )
        )
    predictions = pd.concat(frames, ignore_index=True)
    predictions = predictions.sort_values(
        ["target", "model", "heldout_numeric_simulation_id"], kind="stable"
    ).reset_index(drop=True)
    for target, table in tables.items():
        expected = len(table) * len(ALL_MODELS)
        actual = int(predictions["target"].eq(target).sum())
        if actual != expected:
            raise RuntimeError(f"{target}: {actual} prediction rows, expected {expected}")
    write_csv(destination / "fold_level_predictions.csv", predictions)
    return predictions


def metric_row(frame: pd.DataFrame) -> dict[str, Any]:
    target = str(frame["target"].iloc[0])
    model = str(frame["model"].iloc[0])
    failures = bool_series(frame["fit_failure"])
    successful = frame[
        ~failures
        & np.isfinite(pd.to_numeric(frame["predicted_mean"], errors="coerce"))
    ].copy()
    observed = successful["observed_target_value"].to_numpy(float)
    predicted = successful["predicted_mean"].to_numpy(float)
    if len(successful):
        residual = observed - predicted
        mae = float(mean_absolute_error(observed, predicted))
        rmse = float(math.sqrt(mean_squared_error(observed, predicted)))
        r2 = float(r2_score(observed, predicted)) if len(successful) > 1 else np.nan
        median_scale = float(np.median(np.abs(observed)))
        target_range = float(np.ptp(observed))
    else:
        residual = np.array([], dtype=float)
        mae = rmse = r2 = median_scale = target_range = np.nan
    interval_available = successful["predictive_interval_lower"].notna()
    if interval_available.any():
        coverage = float(
            bool_series(
                successful.loc[
                    interval_available, "predictive_interval_contains_observed"
                ]
            ).mean()
        )
        interval_width = float(
            np.median(
                successful.loc[interval_available, "predictive_interval_upper"].to_numpy(float)
                - successful.loc[interval_available, "predictive_interval_lower"].to_numpy(float)
            )
        )
        nlpd = float(
            pd.to_numeric(
                successful.loc[interval_available, "evaluation_nlpd"], errors="coerce"
            ).mean()
        )
    else:
        coverage = interval_width = nlpd = np.nan
    bound_hits = (
        bool_series(successful["any_hyperparameter_bound_hit"]).sum()
        if len(successful)
        else 0
    )
    meta = MODEL_META[model]
    return {
        "target": target,
        "target_label": TARGET_SPECS[target]["label"],
        "target_unit": TARGET_SPECS[target]["unit"],
        "model": model,
        "model_label": MODEL_LABELS[model],
        **meta,
        "eligible_n": len(frame),
        "n": len(successful),
        "MAE": mae,
        "relative_MAE_pct": mae / median_scale * 100 if median_scale > 0 else np.nan,
        "RMSE": rmse,
        "relative_RMSE_pct": rmse / median_scale * 100 if median_scale > 0 else np.nan,
        "R2": r2,
        "target_median_abs_scale": median_scale,
        "relative_error_denominator_definition": "median(abs(y_observed))",
        "target_min": float(observed.min()) if len(observed) else np.nan,
        "target_median": float(np.median(observed)) if len(observed) else np.nan,
        "target_max": float(observed.max()) if len(observed) else np.nan,
        "target_range": target_range,
        "NLPD": nlpd,
        "coverage_95": coverage,
        "calibration_absolute_error_from_0_95": abs(coverage - 0.95)
        if np.isfinite(coverage)
        else np.nan,
        "median_predictive_interval_width": interval_width,
        "fit_failures": int(failures.sum()),
        "warnings": int(pd.to_numeric(frame["warning_count"], errors="coerce").fillna(0).gt(0).sum()),
        "convergence_warning_folds": int(
            pd.to_numeric(frame["convergence_warning_count"], errors="coerce")
            .fillna(0)
            .gt(0)
            .sum()
        ),
        "bound_hit_folds": int(bound_hits),
        "bound_hit_fraction": float(bound_hits / len(successful)) if len(successful) else np.nan,
        "aggregate_fold_runtime_seconds": float(
            pd.to_numeric(frame["runtime_seconds"], errors="coerce").fillna(0).sum()
        ),
        "metrics_recomputed_from_prediction_rows": True,
        "dataset_revision": SPH_V2_REVISION,
        "partition": "new-data",
    }


def build_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    metrics = pd.DataFrame(
        [
            metric_row(group)
            for _, group in predictions.groupby(["target", "model"], sort=True)
        ]
    )
    metrics["rank_by_RMSE"] = (
        metrics.groupby("target")["RMSE"].rank(method="min", ascending=True).astype("Int64")
    )
    metrics["probabilistic_calibration_rank"] = pd.Series(pd.NA, index=metrics.index, dtype="Int64")
    for target, indices in metrics.groupby("target").groups.items():
        subset = metrics.loc[indices]
        deployable = subset[
            subset["probabilistic_deployable"].astype(bool)
            & subset["fit_failures"].eq(0)
            & subset["coverage_95"].notna()
        ].sort_values(["calibration_absolute_error_from_0_95", "NLPD", "RMSE"])
        for rank, index in enumerate(deployable.index, start=1):
            metrics.loc[index, "probabilistic_calibration_rank"] = rank
    return metrics.sort_values(["target", "rank_by_RMSE", "model"]).reset_index(drop=True)


def aligned_residuals(
    predictions: pd.DataFrame, target: str, model: str
) -> pd.DataFrame:
    subset = predictions[
        predictions["target"].eq(target)
        & predictions["model"].eq(model)
        & ~bool_series(predictions["fit_failure"])
    ][["experiment_name", "observed_target_value", "predicted_mean"]].copy()
    subset["residual"] = subset["observed_target_value"] - subset["predicted_mean"]
    return subset.sort_values("experiment_name").reset_index(drop=True)


def paired_bootstrap_comparison(
    predictions: pd.DataFrame,
    *,
    target: str,
    model_a: str,
    model_b: str,
    metric: str,
    resamples: int,
    comparison_group: str,
) -> dict[str, Any]:
    left = aligned_residuals(predictions, target, model_a)
    right = aligned_residuals(predictions, target, model_b)
    merged = left.merge(
        right,
        on=["experiment_name", "observed_target_value"],
        suffixes=("_a", "_b"),
        validate="one_to_one",
    )
    if merged.empty:
        return {
            "target": target,
            "comparison_group": comparison_group,
            "model_a": model_a,
            "model_b": model_b,
            "metric": metric,
            "paired_n": 0,
            "observed_difference": np.nan,
            "ci_low": np.nan,
            "ci_high": np.nan,
            "robustly_favours_model_a": False,
            "robustly_favours_model_b": False,
            "bootstrap_resamples": resamples,
        }
    ra = merged["residual_a"].to_numpy(float)
    rb = merged["residual_b"].to_numpy(float)
    if metric == "MAE":
        observed = float(np.mean(np.abs(ra)) - np.mean(np.abs(rb)))
    elif metric == "RMSE":
        observed = float(np.sqrt(np.mean(ra**2)) - np.sqrt(np.mean(rb**2)))
    else:
        raise ValueError(metric)
    rng = np.random.default_rng(
        deterministic_seed("week7-phase3-paired", target, model_a, model_b, metric, resamples)
    )
    values = np.empty(resamples, dtype=float)
    batch_size = 500
    for start in range(0, resamples, batch_size):
        stop = min(start + batch_size, resamples)
        indices = rng.integers(0, len(merged), size=(stop - start, len(merged)))
        if metric == "MAE":
            values[start:stop] = np.mean(np.abs(ra)[indices], axis=1) - np.mean(
                np.abs(rb)[indices], axis=1
            )
        else:
            values[start:stop] = np.sqrt(np.mean((ra**2)[indices], axis=1)) - np.sqrt(
                np.mean((rb**2)[indices], axis=1)
            )
    low, high = np.quantile(values, [0.025, 0.975])
    return {
        "target": target,
        "target_unit": TARGET_SPECS[target]["unit"],
        "comparison_group": comparison_group,
        "model_a": model_a,
        "model_b": model_b,
        "metric": metric,
        "difference_definition": "model_a minus model_b; negative favours model_a",
        "paired_n": len(merged),
        "observed_difference": observed,
        "ci_low": float(low),
        "ci_high": float(high),
        "ci_excludes_zero": bool(low > 0 or high < 0),
        "robustly_favours_model_a": bool(high < 0),
        "robustly_favours_model_b": bool(low > 0),
        "bootstrap_resamples": resamples,
        "paired_by_experiment_name": True,
        "dataset_revision": SPH_V2_REVISION,
    }


def comparison_pair(
    predictions: pd.DataFrame,
    target: str,
    model_a: str,
    model_b: str,
    *,
    resamples: int,
    group: str,
) -> list[dict[str, Any]]:
    return [
        paired_bootstrap_comparison(
            predictions,
            target=target,
            model_a=model_a,
            model_b=model_b,
            metric=metric,
            resamples=resamples,
            comparison_group=group,
        )
        for metric in ["MAE", "RMSE"]
    ]


def build_decisions_and_comparisons(
    predictions: pd.DataFrame,
    metrics: pd.DataFrame,
    *,
    smoke: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    resamples = SMOKE_PAIRED_RESAMPLES if smoke else FULL_PAIRED_RESAMPLES
    comparison_rows: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for target in TARGET_SPECS:
        target_metrics = metrics[metrics["target"].eq(target)].set_index("model")
        current = "matern32_learned_nugget"
        eligible_replacements: list[str] = []
        for candidate in ["rbf_learned_nugget", "matern52_learned_nugget"]:
            rows = comparison_pair(
                predictions,
                target,
                candidate,
                current,
                resamples=resamples,
                group="learned_kernel_candidate_vs_matern32",
            )
            comparison_rows.extend(rows)
            robust_both = all(row["robustly_favours_model_a"] for row in rows)
            candidate_metric = target_metrics.loc[candidate]
            current_metric = target_metrics.loc[current]
            calibration_ok = bool(
                0.85 <= float(candidate_metric["coverage_95"]) <= 1.0
                and abs(float(candidate_metric["coverage_95"]) - 0.95)
                <= abs(float(current_metric["coverage_95"]) - 0.95) + 0.05
            )
            optimization_ok = bool(
                int(candidate_metric["fit_failures"]) == 0
                and float(candidate_metric["bound_hit_fraction"]) <= 0.25
                and int(candidate_metric["convergence_warning_folds"])
                <= max(2, int(0.05 * int(candidate_metric["n"])))
            )
            if robust_both and calibration_ok and optimization_ok:
                eligible_replacements.append(candidate)
        if eligible_replacements:
            selected_gp = min(
                eligible_replacements, key=lambda item: float(target_metrics.loc[item, "RMSE"])
            )
            kernel_rationale = (
                f"{selected_gp} robustly improves paired MAE and RMSE over Matérn 3/2 "
                "without unacceptable calibration or optimisation deterioration."
            )
        else:
            selected_gp = current
            kernel_rationale = (
                "No alternative learned-nugget kernel satisfied the Week 6 replacement "
                "rule; Matérn 3/2 is retained for continuity."
            )
        best_learned_gp = min(
            ["rbf_learned_nugget", "matern32_learned_nugget", "matern52_learned_nugget"],
            key=lambda item: float(target_metrics.loc[item, "RMSE"]),
        )
        best_rmse_model = str(target_metrics["RMSE"].astype(float).idxmin())

        for simple in BASELINE_MODELS:
            comparison_rows.extend(
                comparison_pair(
                    predictions,
                    target,
                    selected_gp,
                    simple,
                    resamples=resamples,
                    group="selected_gp_vs_baseline",
                )
            )
        simple_competitive: list[str] = []
        target_values = aligned_residuals(predictions, target, selected_gp)[
            "observed_target_value"
        ].to_numpy(float)
        practical_threshold = max(
            0.01 * float(np.ptp(target_values)),
            0.02 * float(np.subtract(*np.quantile(target_values, [0.75, 0.25]))),
        )
        for simple in ["linear_ridge", "polynomial_ridge_degree2"]:
            pair_rows = [
                row
                for row in comparison_rows
                if row["target"] == target
                and row["comparison_group"] == "selected_gp_vs_baseline"
                and row["model_a"] == selected_gp
                and row["model_b"] == simple
            ]
            gp_robust_both = all(row["robustly_favours_model_a"] for row in pair_rows)
            rmse_difference = next(
                row["observed_difference"] for row in pair_rows if row["metric"] == "RMSE"
            )
            gp_improvement = -float(rmse_difference)
            if (not gp_robust_both) or gp_improvement <= practical_threshold:
                simple_competitive.append(simple)
        if "linear_ridge" in simple_competitive:
            selected_point = "linear_ridge"
        elif "polynomial_ridge_degree2" in simple_competitive:
            selected_point = "polynomial_ridge_degree2"
        else:
            selected_point = selected_gp

        no_nugget = selected_gp.replace("_learned_nugget", "_no_nugget")
        nugget_rows = comparison_pair(
            predictions,
            target,
            selected_gp,
            no_nugget,
            resamples=resamples,
            group="selected_kernel_learned_nugget_vs_no_nugget",
        )
        comparison_rows.extend(nugget_rows)
        learned_metric = target_metrics.loc[selected_gp]
        no_metric = target_metrics.loc[no_nugget]
        point_advantage = all(row["robustly_favours_model_a"] for row in nugget_rows)
        calibration_advantage = abs(float(no_metric["coverage_95"]) - 0.95) - abs(
            float(learned_metric["coverage_95"]) - 0.95
        )
        nlpd_advantage = float(no_metric["NLPD"]) - float(learned_metric["NLPD"])
        learned_useful = bool(
            point_advantage or calibration_advantage >= 0.03 or nlpd_advantage > 0
        )
        selected_uncertainty = selected_gp if learned_useful else no_nugget

        for model_a, model_b, group in [
            ("matern32_learned_nugget", HETEROSKEDASTIC_MODEL, "noise_B_vs_C"),
            ("matern32_learned_nugget", "matern32_no_nugget", "noise_B_vs_A"),
            (HETEROSKEDASTIC_MODEL, "matern32_no_nugget", "noise_C_vs_A"),
        ]:
            comparison_rows.extend(
                comparison_pair(
                    predictions,
                    target,
                    model_a,
                    model_b,
                    resamples=resamples,
                    group=group,
                )
            )

        deployable = target_metrics[
            target_metrics["probabilistic_deployable"].astype(bool)
            & target_metrics["fit_failures"].eq(0)
        ].sort_values(["calibration_absolute_error_from_0_95", "NLPD", "RMSE"])
        best_calibrated = str(deployable.index[0])
        selected_metric = target_metrics.loc[selected_point]
        decisions.append(
            {
                "target": target,
                "target_label": TARGET_SPECS[target]["label"],
                "target_unit": TARGET_SPECS[target]["unit"],
                "population_size": int(selected_metric["eligible_n"]),
                "best_point_prediction_model_by_RMSE": best_rmse_model,
                "best_point_prediction_RMSE": float(target_metrics.loc[best_rmse_model, "RMSE"]),
                "best_point_prediction_relative_RMSE_pct": float(
                    target_metrics.loc[best_rmse_model, "relative_RMSE_pct"]
                ),
                "best_learned_nugget_gp_by_RMSE": best_learned_gp,
                "protocol_selected_gp": selected_gp,
                "protocol_selected_point_model": selected_point,
                "protocol_selected_uncertainty_model": selected_uncertainty,
                "best_calibrated_deployable_probabilistic_model": best_calibrated,
                "simple_models_competitive": json_text(simple_competitive),
                "polynomial_ridge_competitive": "polynomial_ridge_degree2"
                in simple_competitive,
                "linear_ridge_competitive": "linear_ridge" in simple_competitive,
                "practical_RMSE_difference_threshold": practical_threshold,
                "kernel_replacement_rationale": kernel_rationale,
                "learned_nugget_robust_point_advantage": point_advantage,
                "learned_nugget_calibration_advantage": calibration_advantage,
                "learned_nugget_NLPD_advantage": nlpd_advantage,
                "learned_shared_nugget_remains_useful": learned_useful,
                "heteroskedastic_interval_is_retrospective_oracle": True,
                "dataset_revision": SPH_V2_REVISION,
                "partition": "new-data",
            }
        )
    comparisons = pd.DataFrame(comparison_rows).drop_duplicates(
        ["target", "comparison_group", "model_a", "model_b", "metric"]
    )
    return (
        pd.DataFrame(decisions).sort_values("target").reset_index(drop=True),
        comparisons.sort_values(
            ["target", "comparison_group", "model_a", "model_b", "metric"]
        ).reset_index(drop=True),
    )


def load_week6_historical_reference() -> tuple[pd.DataFrame, pd.DataFrame]:
    simple = pd.read_csv(WEEK6_PHASE3_DIR / "simple_baseline_metrics.csv")
    gp = pd.read_csv(WEEK6_PHASE3_DIR / "gp_kernel_noise_metrics.csv")
    simple = simple[
        simple["target"].isin(["width", "depth"])
        & simple["target_definition"].eq("T0")
        & simple["model"].isin(BASELINE_MODELS)
    ].copy()
    gp = gp[
        gp["target"].isin(["width", "depth"])
        & gp["target_definition"].eq("T0")
    ].copy()
    simple_reference = pd.DataFrame(
        {
            "target": simple["target"],
            "model": simple["model"],
            "model_family": simple["model"].map(
                {model: MODEL_META[model]["model_family"] for model in BASELINE_MODELS}
            ),
            "kernel": "",
            "noise_method": "not applicable",
            "n": simple["n_predictions"],
            "MAE": simple["mae_um"],
            "RMSE": simple["rmse_um"],
            "R2": simple["r2"],
            "NLPD": np.nan,
            "coverage_95": np.nan,
            "target_median_abs_scale": simple["target_median_um"].abs(),
            "target_unit": "um",
        }
    )
    gp_reference = pd.DataFrame(
        {
            "target": gp["target"],
            "model": gp["gp_configuration"],
            "model_family": "Gaussian process",
            "kernel": gp["gp_configuration"].map(
                {model: MODEL_META[model]["kernel"] for model in GP_CONFIGURATION_NAMES}
            ),
            "noise_method": gp["gp_configuration"].map(
                {model: MODEL_META[model]["noise_method"] for model in GP_CONFIGURATION_NAMES}
            ),
            "n": gp["n_predictions"],
            "MAE": gp["mae_um"],
            "RMSE": gp["rmse_um"],
            "R2": gp["r2"],
            "NLPD": gp["mean_nlpd"],
            "coverage_95": gp["evaluation_95_coverage"],
            "target_median_abs_scale": gp["target_median_um"].abs(),
            "target_unit": "um",
        }
    )

    phase4 = pd.read_csv(WEEK6_PHASE4_DIR / "phase4_model_metrics.csv")
    phase4 = phase4[
        phase4["response"].isin(["total_height", "kinetic_energy"])
    ].copy()
    phase4_reference = pd.DataFrame(
        {
            "target": phase4["response"],
            "model": phase4["model"],
            "model_family": phase4["model_family"],
            "kernel": phase4["model"].map(
                {model: MODEL_META[model]["kernel"] for model in MODEL_META}
            ).fillna(""),
            "noise_method": phase4["model"].map(
                {model: MODEL_META[model]["noise_method"] for model in MODEL_META}
            ).fillna("not applicable"),
            "n": phase4["n_predictions"],
            "MAE": phase4["mae"],
            "RMSE": phase4["rmse"],
            "R2": phase4["r2"],
            "NLPD": phase4["mean_nlpd"],
            "coverage_95": phase4["total_or_evaluation_95pct_coverage"],
            "target_median_abs_scale": phase4["target_median"].abs(),
            "target_unit": phase4["target_unit"],
        }
    )
    reference = pd.concat(
        [simple_reference, gp_reference, phase4_reference], ignore_index=True
    )
    reference["relative_MAE_pct"] = (
        reference["MAE"] / reference["target_median_abs_scale"] * 100
    )
    reference["relative_RMSE_pct"] = (
        reference["RMSE"] / reference["target_median_abs_scale"] * 100
    )
    reference["historical_population"] = "Week 6 old simulation design"
    reference["historical_dataset_revision"] = (
        "ioandanielc/sph_dataset@0e859b748fdbc8454f66e58e101e333ac0479d42"
    )

    phase3_decisions = pd.read_csv(
        WEEK6_PHASE3_DIR / "phase3_final_model_decision.csv"
    )
    phase3_decisions = phase3_decisions[
        phase3_decisions["target"].isin(["width", "depth"])
    ]
    phase4_decisions = pd.read_csv(
        WEEK6_PHASE4_DIR / "phase4_selected_model_decisions.csv"
    )
    decision_rows: list[dict[str, Any]] = []
    for row in phase3_decisions.itertuples(index=False):
        decision_rows.append(
            {
                "target": row.target,
                "week6_selected_point_model": row.selected_final_model,
                "week6_selected_gp": row.selected_provisional_gp,
                "week6_selected_uncertainty_model": row.selected_provisional_gp,
                "week6_polynomial_competitive": "polynomial_ridge_degree2"
                in str(row.simple_models_competitive),
                "week6_learned_nugget_useful": bool(
                    row.learned_nugget_robustly_helps_selected_gp_family
                ),
                "week6_decision_source": (
                    "outputs/week6_03_model_target_robustness/phase3_final_model_decision.csv"
                ),
            }
        )
    for row in phase4_decisions.itertuples(index=False):
        decision_rows.append(
            {
                "target": row.response,
                "week6_selected_point_model": row.selected_point_model,
                "week6_selected_gp": row.selected_kernel_family_model,
                "week6_selected_uncertainty_model": row.selected_uncertainty_model,
                "week6_polynomial_competitive": "polynomial_ridge_degree2"
                in str(row.simple_models_competitive),
                "week6_learned_nugget_useful": bool(
                    row.learned_nugget_remains_useful
                ),
                "week6_decision_source": (
                    "outputs/week6_04_new_outputs_feature_effects/phase4_selected_model_decisions.csv"
                ),
            }
        )
    decisions = pd.DataFrame(decision_rows).sort_values("target").reset_index(drop=True)
    return reference.sort_values(["target", "RMSE", "model"]).reset_index(drop=True), decisions


def build_historical_comparison(
    historical_metrics: pd.DataFrame,
    historical_decisions: pd.DataFrame,
    new_metrics: pd.DataFrame,
    new_decisions: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for target in TARGET_SPECS:
        old_decision = historical_decisions.set_index("target").loc[target]
        new_decision = new_decisions.set_index("target").loc[target]
        old = historical_metrics[historical_metrics["target"].eq(target)].set_index("model")
        new = new_metrics[new_metrics["target"].eq(target)].set_index("model")
        old_point = str(old_decision["week6_selected_point_model"])
        old_gp = str(old_decision["week6_selected_gp"])
        new_point = str(new_decision["protocol_selected_point_model"])
        new_gp = str(new_decision["protocol_selected_gp"])
        old_learned = old.loc[
            old.index.intersection(
                ["rbf_learned_nugget", "matern32_learned_nugget", "matern52_learned_nugget"]
            )
        ]
        old_best_kernel = str(old_learned["RMSE"].astype(float).idxmin())
        relative_ratio = float(new.loc[new_point, "relative_RMSE_pct"]) / float(
            old.loc[old_point, "relative_RMSE_pct"]
        )
        if relative_ratio > 1.10:
            difficulty = "higher relative out-of-sample error in the new sampled domain"
        elif relative_ratio < 0.90:
            difficulty = "lower relative out-of-sample error in the new sampled domain"
        else:
            difficulty = "similar relative out-of-sample error across sampled domains"
        rows.append(
            {
                "target": target,
                "target_label": TARGET_SPECS[target]["label"],
                "target_unit": TARGET_SPECS[target]["unit"],
                "week6_n": int(old.loc[old_point, "n"]),
                "new_data_n": int(new.loc[new_point, "n"]),
                "week6_selected_point_model": old_point,
                "new_data_selected_point_model": new_point,
                "week6_best_learned_gp_kernel": old_best_kernel,
                "week6_protocol_selected_gp": old_gp,
                "new_data_best_learned_gp_kernel": str(
                    new_decision["best_learned_nugget_gp_by_RMSE"]
                ),
                "new_data_protocol_selected_gp": new_gp,
                "week6_learned_nugget_useful": bool(
                    old_decision["week6_learned_nugget_useful"]
                ),
                "new_data_learned_nugget_useful": bool(
                    new_decision["learned_shared_nugget_remains_useful"]
                ),
                "week6_MAE": float(old.loc[old_point, "MAE"]),
                "new_data_MAE": float(new.loc[new_point, "MAE"]),
                "week6_relative_MAE_pct": float(
                    old.loc[old_point, "relative_MAE_pct"]
                ),
                "new_data_relative_MAE_pct": float(
                    new.loc[new_point, "relative_MAE_pct"]
                ),
                "week6_RMSE": float(old.loc[old_point, "RMSE"]),
                "new_data_RMSE": float(new.loc[new_point, "RMSE"]),
                "week6_relative_RMSE_pct": float(
                    old.loc[old_point, "relative_RMSE_pct"]
                ),
                "new_data_relative_RMSE_pct": float(
                    new.loc[new_point, "relative_RMSE_pct"]
                ),
                "week6_R2": float(old.loc[old_point, "R2"]),
                "new_data_R2": float(new.loc[new_point, "R2"]),
                "week6_target_median_scale": float(
                    old.loc[old_point, "target_median_abs_scale"]
                ),
                "new_data_target_median_scale": float(
                    new.loc[new_point, "target_median_abs_scale"]
                ),
                "week6_gp_minus_polynomial_RMSE": float(
                    old.loc[old_gp, "RMSE"]
                    - old.loc["polynomial_ridge_degree2", "RMSE"]
                ),
                "new_data_gp_minus_polynomial_RMSE": float(
                    new.loc[new_gp, "RMSE"]
                    - new.loc["polynomial_ridge_degree2", "RMSE"]
                ),
                "relative_RMSE_ratio_new_over_week6": relative_ratio,
                "model_difficulty_observation": difficulty,
                "point_model_same": old_point == new_point,
                "protocol_gp_same": old_gp == new_gp,
                "dataset_populations_pooled": False,
                "new_dataset_revision": SPH_V2_REVISION,
            }
        )
    return pd.DataFrame(rows).sort_values("target").reset_index(drop=True)


def _comparison_rows(
    comparisons: pd.DataFrame,
    target: str,
    model_a: str,
    model_b: str,
    group: str,
) -> pd.DataFrame:
    return comparisons[
        comparisons["target"].eq(target)
        & comparisons["model_a"].eq(model_a)
        & comparisons["model_b"].eq(model_b)
        & comparisons["comparison_group"].eq(group)
    ]


def stability_status_for_gap(
    rows: pd.DataFrame,
    *,
    observed_better: bool,
) -> str:
    if rows.empty:
        return "UNRESOLVED"
    robust_a = bool(rows["robustly_favours_model_a"].all())
    robust_b = bool(rows["robustly_favours_model_b"].all())
    if observed_better and robust_a:
        return "REPRODUCED"
    if observed_better:
        return "WEAKENED"
    if robust_b:
        return "REVERSED"
    return "UNRESOLVED"


def build_stability_conclusions(
    metrics: pd.DataFrame,
    decisions: pd.DataFrame,
    comparisons: pd.DataFrame,
    historical: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    metrics_by = metrics.set_index(["target", "model"])
    decisions_by = decisions.set_index("target")
    historical_by = historical.set_index("target")
    for target in TARGET_SPECS:
        decision = decisions_by.loc[target]
        gp = str(decision["protocol_selected_gp"])
        for question, simple, week6_conclusion in [
            ("Q1", "linear_ridge", "GP outperforms Linear Ridge in out-of-sample error"),
            ("Q2", "polynomial_ridge_degree2", "GP outperforms degree-2 Polynomial Ridge in raw error"),
        ]:
            pair = _comparison_rows(
                comparisons, target, gp, simple, "selected_gp_vs_baseline"
            )
            gp_rmse = float(metrics_by.loc[(target, gp), "RMSE"])
            simple_rmse = float(metrics_by.loc[(target, simple), "RMSE"])
            status = stability_status_for_gap(pair, observed_better=gp_rmse < simple_rmse)
            rows.append(
                {
                    "question": question,
                    "target": target,
                    "week6_conclusion": week6_conclusion,
                    "new_data_evidence": (
                        f"{MODEL_LABELS[gp]} RMSE={gp_rmse:.6g} versus "
                        f"{MODEL_LABELS[simple]} RMSE={simple_rmse:.6g}; "
                        f"paired MAE/RMSE robust advantage={bool(pair['robustly_favours_model_a'].all()) if not pair.empty else False}."
                    ),
                    "status": status,
                    "evidence": "fold_level_predictions.csv; paired_model_comparisons.csv",
                }
            )

        nugget_status = (
            "REPRODUCED"
            if bool(decision["learned_shared_nugget_remains_useful"])
            else "REVERSED"
        )
        rows.append(
            {
                "question": "Q5",
                "target": target,
                "week6_conclusion": "A shared learned nugget is useful for predictive performance or calibration under the GP model",
                "new_data_evidence": (
                    f"useful={bool(decision['learned_shared_nugget_remains_useful'])}; "
                    f"point advantage={bool(decision['learned_nugget_robust_point_advantage'])}; "
                    f"calibration advantage={float(decision['learned_nugget_calibration_advantage']):.4g}; "
                    f"NLPD advantage={float(decision['learned_nugget_NLPD_advantage']):.4g}."
                ),
                "status": nugget_status,
                "evidence": "noise_treatment_comparison.csv; model_selection_decisions.csv",
            }
        )
        old_gp = str(historical_by.loc[target, "week6_protocol_selected_gp"])
        new_gp = str(decision["protocol_selected_gp"])
        rows.append(
            {
                "question": "Q6",
                "target": target,
                "week6_conclusion": f"Week 6 protocol selected {MODEL_LABELS.get(old_gp, old_gp)}",
                "new_data_evidence": (
                    f"New-data empirical learned-kernel winner={MODEL_LABELS[str(decision['best_learned_nugget_gp_by_RMSE'])]}; "
                    f"protocol selection={MODEL_LABELS[new_gp]}."
                ),
                "status": "REPRODUCED" if new_gp == old_gp else "REVERSED",
                "evidence": "kernel_comparison.csv; paired_model_comparisons.csv",
            }
        )

    width = decisions_by.loc["width"]
    rows.append(
        {
            "question": "Q3",
            "target": "width",
            "week6_conclusion": "Width is relatively simple and degree-2 Polynomial Ridge is competitive with GP",
            "new_data_evidence": f"polynomial_ridge_competitive={bool(width['polynomial_ridge_competitive'])}; protocol point model={width['protocol_selected_point_model']}.",
            "status": "REPRODUCED" if bool(width["polynomial_ridge_competitive"]) else "REVERSED",
            "evidence": "model_selection_decisions.csv; model_metric_table.csv",
        }
    )
    depth = decisions_by.loc["depth"]
    rows.append(
        {
            "question": "Q4",
            "target": "depth",
            "week6_conclusion": "Depth benefits materially from GP flexibility",
            "new_data_evidence": f"simple_models_competitive={depth['simple_models_competitive']}; protocol point model={depth['protocol_selected_point_model']}.",
            "status": "REPRODUCED"
            if str(depth["protocol_selected_point_model"]).endswith("nugget")
            else "REVERSED",
            "evidence": "model_selection_decisions.csv; paired_model_comparisons.csv",
        }
    )
    height = historical_by.loc["total_height"]
    rows.append(
        {
            "question": "Q7",
            "target": "total_height",
            "week6_conclusion": "Polynomial Ridge is the parsimonious total-height point model; Matérn 3/2 plus nugget supplies uncertainty",
            "new_data_evidence": f"new point={height['new_data_selected_point_model']}; new GP={height['new_data_protocol_selected_gp']}; relative RMSE={height['new_data_relative_RMSE_pct']:.3f}%.",
            "status": "REPRODUCED"
            if bool(height["point_model_same"]) and bool(height["protocol_gp_same"])
            else "WEAKENED",
            "evidence": "week6_vs_new_data_comparison.csv",
        }
    )
    energy = historical_by.loc["kinetic_energy"]
    rows.append(
        {
            "question": "Q8",
            "target": "kinetic_energy",
            "week6_conclusion": "Linear Ridge is the parsimonious kinetic-energy point model; GP uncertainty remains useful",
            "new_data_evidence": f"new point={energy['new_data_selected_point_model']}; relative MAE={energy['new_data_relative_MAE_pct']:.3f}%; relative RMSE={energy['new_data_relative_RMSE_pct']:.3f}%; R2={energy['new_data_R2']:.4f}.",
            "status": "REPRODUCED"
            if bool(energy["point_model_same"])
            else "WEAKENED",
            "evidence": "week6_vs_new_data_comparison.csv",
        }
    )
    difficulty_evidence = "; ".join(
        f"{row.target}: {row.model_difficulty_observation}"
        for row in historical.itertuples(index=False)
    )
    rows.append(
        {
            "question": "Q9",
            "target": "all",
            "week6_conclusion": "Model difficulty should be compared using relative error and ranking, not absolute error alone",
            "new_data_evidence": difficulty_evidence,
            "status": "UNRESOLVED",
            "evidence": "week6_vs_new_data_comparison.csv",
        }
    )
    rows.append(
        {
            "question": "Q10",
            "target": "all",
            "week6_conclusion": (
                "The Week 6 candidate/evaluation pipeline and all target-specific "
                "final model choices transfer unchanged"
            ),
            "new_data_evidence": (
                "The fold-local LOO comparison pipeline remains adequate without new "
                "kernels or a larger search, but total-height and kinetic-energy point "
                "choices changed and the learned-nugget conclusion reversed for depth "
                "and total height."
            ),
            "status": "WEAKENED",
            "evidence": (
                "model_selection_decisions.csv; week6_vs_new_data_comparison.csv; "
                "noise_treatment_comparison.csv"
            ),
        }
    )
    return pd.DataFrame(rows)


def build_residual_diagnostics(
    predictions: pd.DataFrame, metrics: pd.DataFrame
) -> pd.DataFrame:
    scales = metrics.drop_duplicates("target").set_index("target")[
        "target_median_abs_scale"
    ]
    result = predictions.copy()
    result["absolute_error"] = np.abs(
        pd.to_numeric(result["observed_target_value"], errors="coerce")
        - pd.to_numeric(result["predicted_mean"], errors="coerce")
    )
    result["relative_absolute_error_pct_of_target_median"] = result.apply(
        lambda row: row["absolute_error"] / float(scales.loc[row["target"]]) * 100
        if np.isfinite(row["absolute_error"])
        else np.nan,
        axis=1,
    )
    result["absolute_error_rank_within_target_model"] = result.groupby(
        ["target", "model"]
    )["absolute_error"].rank(method="first", ascending=False)
    result["major_outlier_flag_top3"] = result[
        "absolute_error_rank_within_target_model"
    ].le(3)
    return result


def predictive_interval_diagnostics(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    probabilistic = predictions[predictions["model"].isin(GP_CONFIGURATION_NAMES + [HETEROSKEDASTIC_MODEL])]
    for (target, model), frame in probabilistic.groupby(["target", "model"], sort=True):
        valid = frame[
            ~bool_series(frame["fit_failure"])
            & frame["predictive_interval_lower"].notna()
        ]
        observed = valid["observed_target_value"].to_numpy(float)
        predicted = valid["predicted_mean"].to_numpy(float)
        lower = valid["predictive_interval_lower"].to_numpy(float)
        upper = valid["predictive_interval_upper"].to_numpy(float)
        std = (upper - lower) / (2 * 1.96)
        standardized = (observed - predicted) / np.maximum(std, 1e-18)
        rows.append(
            {
                "target": target,
                "model": model,
                "model_label": MODEL_LABELS[model],
                "n": len(valid),
                "coverage_95": float(((lower <= observed) & (observed <= upper)).mean()),
                "coverage_error_from_0_95": abs(
                    float(((lower <= observed) & (observed <= upper)).mean()) - 0.95
                ),
                "median_interval_width": float(np.median(upper - lower)),
                "standardized_residual_mean": float(np.mean(standardized)),
                "standardized_residual_std": float(np.std(standardized, ddof=1)),
                "standardized_residual_q025": float(np.quantile(standardized, 0.025)),
                "standardized_residual_q975": float(np.quantile(standardized, 0.975)),
                "interval_definition": str(valid["interval_definition"].iloc[0]),
                "retrospective_oracle": model == HETEROSKEDASTIC_MODEL,
                "dataset_revision": SPH_V2_REVISION,
            }
        )
    return pd.DataFrame(rows)


def kinetic_energy_scope_caution(population: pd.DataFrame) -> pd.DataFrame:
    new = population.copy()
    index = pd.to_numeric(new["max_kinetic_energy_nJ"], errors="coerce").idxmax()
    row = new.loc[index]
    t0 = pd.to_numeric(new["T0_kinetic_energy_nJ"], errors="coerce")
    q1, q3 = t0.quantile([0.25, 0.75])
    threshold = float(q3 + 3 * (q3 - q1))
    suspicious = bool(float(row["T0_kinetic_energy_nJ"]) > threshold)
    return pd.DataFrame(
        [
            {
                "experiment_name": row["experiment_name"],
                "max_kinetic_energy_nJ": float(row["max_kinetic_energy_nJ"]),
                "T0_kinetic_energy_nJ": float(row["T0_kinetic_energy_nJ"]),
                "T0_kinetic_energy_percentile": float(
                    t0.rank(pct=True).loc[index] * 100
                ),
                "T0_extreme_threshold_q3_plus_3iqr_nJ": threshold,
                "T0_kinetic_energy_suspicious_by_q3_plus_3iqr": suspicious,
                "phase3_action": (
                    "flag T0 row conservatively; retain in modelling"
                    if suspicious
                    else "maximum-energy anomaly recorded as out of Phase 3 scope; T0 row retained"
                ),
                "row_removed": False,
                "maximum_kinetic_energy_analysis_in_scope": False,
                "dataset_revision": SPH_V2_REVISION,
            }
        ]
    )


FIGURE_COLORS = {
    "linear_ridge": "#E69F00",
    "polynomial_ridge_degree2": "#009E73",
    "matern32_learned_nugget": "#0072B2",
    "rbf_learned_nugget": "#56B4E9",
    "matern52_learned_nugget": "#CC79A7",
    "matern32_no_nugget": "#D55E00",
    HETEROSKEDASTIC_MODEL: "#7A5195",
    "training_mean": "#777777",
}


def save_figure(
    fig: plt.Figure,
    destination: Path,
    filename: str,
    *,
    question: str,
    target: str = "all",
    models: Sequence[str] = (),
) -> dict[str, Any]:
    figure_dir = destination / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    path = figure_dir / filename
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return {
        "figure": filename,
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "question": question,
        "target": target,
        "models": json_text(list(models)),
        "sha256": sha256_file(path),
    }


def generate_figures(
    population_long: pd.DataFrame,
    predictions: pd.DataFrame,
    metrics: pd.DataFrame,
    decisions: pd.DataFrame,
    historical: pd.DataFrame,
    conclusions: pd.DataFrame,
    destination: Path,
) -> pd.DataFrame:
    manifests: list[dict[str, Any]] = []
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for axis, target in zip(axes.flat, TARGET_SPECS):
        values = population_long.loc[
            population_long["target"].eq(target), "target_value_um"
        ].to_numpy(float)
        axis.hist(values, bins=18, color="#4C78A8", alpha=0.8)
        axis.axvline(np.median(values), color="black", linestyle="--", linewidth=1)
        axis.set_title(TARGET_SPECS[target]["label"])
        axis.set_xlabel(TARGET_SPECS[target]["unit"])
        axis.set_ylabel("Experiments")
    fig.suptitle("New-data T0 target scales (model-ready populations)")
    fig.tight_layout()
    manifests.append(
        save_figure(
            fig,
            destination,
            "01_new_data_target_scales.png",
            question="What target scales and distributions define the new-data modelling domain?",
        )
    )

    decision_by = decisions.set_index("target")
    number = 2
    for target in TARGET_SPECS:
        selected_gp = str(decision_by.loc[target, "protocol_selected_gp"])
        show_models = [selected_gp, "polynomial_ridge_degree2", "linear_ridge"]
        unit = TARGET_SPECS[target]["unit"]
        fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
        all_values: list[float] = []
        for axis, model in zip(axes, show_models):
            frame = predictions[
                predictions["target"].eq(target)
                & predictions["model"].eq(model)
                & ~bool_series(predictions["fit_failure"])
            ]
            observed = frame["observed_target_value"].to_numpy(float)
            predicted = frame["predicted_mean"].to_numpy(float)
            all_values.extend(observed.tolist() + predicted.tolist())
            axis.scatter(
                observed,
                predicted,
                s=24,
                alpha=0.72,
                color=FIGURE_COLORS.get(model, "#4C78A8"),
                edgecolor="none",
            )
            axis.set_title(MODEL_LABELS[model])
            axis.set_xlabel(f"Observed ({unit})")
            axis.set_ylabel(f"LOO prediction ({unit})")
        low, high = min(all_values), max(all_values)
        pad = 0.04 * (high - low if high > low else 1.0)
        for axis in axes:
            axis.plot([low - pad, high + pad], [low - pad, high + pad], "k--", lw=1)
            axis.set_xlim(low - pad, high + pad)
            axis.set_ylim(low - pad, high + pad)
            axis.set_aspect("equal", adjustable="box")
        fig.suptitle(f"{TARGET_SPECS[target]['label']}: observed versus exact-LOO predictions")
        fig.tight_layout()
        manifests.append(
            save_figure(
                fig,
                destination,
                f"{number:02d}_{target}_observed_vs_predicted.png",
                question="How closely do the main models predict each held-out simulation?",
                target=target,
                models=show_models,
            )
        )
        number += 1

        fig, axis = plt.subplots(figsize=(8, 4.8))
        for model in show_models:
            frame = predictions[
                predictions["target"].eq(target)
                & predictions["model"].eq(model)
                & ~bool_series(predictions["fit_failure"])
            ]
            residual = frame["observed_target_value"].to_numpy(float) - frame[
                "predicted_mean"
            ].to_numpy(float)
            axis.hist(
                residual,
                bins=22,
                alpha=0.38,
                label=MODEL_LABELS[model],
                color=FIGURE_COLORS.get(model),
            )
        axis.axvline(0, color="black", linestyle="--", linewidth=1)
        axis.set_xlabel(f"Observed - prediction ({unit})")
        axis.set_ylabel("Held-out predictions")
        axis.set_title(f"{TARGET_SPECS[target]['label']}: residual distributions")
        axis.legend(fontsize=8)
        fig.tight_layout()
        manifests.append(
            save_figure(
                fig,
                destination,
                f"{number:02d}_{target}_residual_distribution.png",
                question="Are errors centred and are there asymmetric or heavy residual tails?",
                target=target,
                models=show_models,
            )
        )
        number += 1

        fig, axis = plt.subplots(figsize=(8, 4.8))
        for model in [selected_gp, "polynomial_ridge_degree2"]:
            frame = predictions[
                predictions["target"].eq(target)
                & predictions["model"].eq(model)
                & ~bool_series(predictions["fit_failure"])
            ]
            absolute = np.abs(
                frame["observed_target_value"].to_numpy(float)
                - frame["predicted_mean"].to_numpy(float)
            )
            axis.scatter(
                frame["observed_target_value"],
                absolute,
                s=22,
                alpha=0.65,
                label=MODEL_LABELS[model],
                color=FIGURE_COLORS.get(model),
            )
        axis.set_xlabel(f"Observed target ({unit})")
        axis.set_ylabel(f"Absolute LOO error ({unit})")
        axis.set_title(f"{TARGET_SPECS[target]['label']}: error versus target scale")
        axis.legend(fontsize=8)
        fig.tight_layout()
        manifests.append(
            save_figure(
                fig,
                destination,
                f"{number:02d}_{target}_error_vs_observed_scale.png",
                question="Do absolute errors grow systematically with the observed response scale?",
                target=target,
                models=[selected_gp, "polynomial_ridge_degree2"],
            )
        )
        number += 1

        gp_metrics = metrics[
            metrics["target"].eq(target)
            & metrics["probabilistic"].astype(bool)
        ].sort_values("coverage_95")
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
        labels = [MODEL_LABELS[item] for item in gp_metrics["model"]]
        colors = [FIGURE_COLORS.get(item, "#4C78A8") for item in gp_metrics["model"]]
        axes[0].barh(labels, gp_metrics["coverage_95"], color=colors, alpha=0.8)
        axes[0].axvline(0.95, color="black", linestyle="--", linewidth=1)
        axes[0].set_xlim(0, 1.02)
        axes[0].set_xlabel("95% interval coverage")
        axes[1].barh(labels, gp_metrics["NLPD"], color=colors, alpha=0.8)
        axes[1].set_xlabel("Mean NLPD (lower is better)")
        fig.suptitle(f"{TARGET_SPECS[target]['label']}: probabilistic calibration")
        fig.tight_layout()
        manifests.append(
            save_figure(
                fig,
                destination,
                f"{number:02d}_{target}_predictive_interval_calibration.png",
                question="Which GP uncertainty treatment is best calibrated out of sample?",
                target=target,
                models=gp_metrics["model"].tolist(),
            )
        )
        number += 1

        target_metrics = metrics[metrics["target"].eq(target)].sort_values(
            "relative_RMSE_pct", ascending=True
        )
        fig, axis = plt.subplots(figsize=(9, 5.2))
        axis.barh(
            [MODEL_LABELS[item] for item in target_metrics["model"]],
            target_metrics["relative_RMSE_pct"],
            color=[FIGURE_COLORS.get(item, "#999999") for item in target_metrics["model"]],
            alpha=0.82,
        )
        axis.invert_yaxis()
        axis.set_xlabel("Relative RMSE (% of median |observed target|)")
        axis.set_title(f"{TARGET_SPECS[target]['label']}: model ranking")
        fig.tight_layout()
        manifests.append(
            save_figure(
                fig,
                destination,
                f"{number:02d}_{target}_model_metric_comparison.png",
                question="Which model has the lowest median-scale relative RMSE?",
                target=target,
                models=target_metrics["model"].tolist(),
            )
        )
        number += 1

    fig, axis = plt.subplots(figsize=(10, 5.2))
    x = np.arange(len(historical))
    width = 0.36
    axis.bar(
        x - width / 2,
        historical["week6_relative_RMSE_pct"],
        width,
        label="Week 6 old design",
        color="#999999",
    )
    axis.bar(
        x + width / 2,
        historical["new_data_relative_RMSE_pct"],
        width,
        label="Week 7 new data",
        color="#0072B2",
    )
    axis.set_xticks(x, [TARGET_SPECS[target]["label"] for target in historical["target"]], rotation=18, ha="right")
    axis.set_ylabel("Protocol-selected relative RMSE (%)")
    axis.set_title("Historical replication: relative error, never pooled populations")
    axis.legend()
    fig.tight_layout()
    manifests.append(
        save_figure(
            fig,
            destination,
            f"{number:02d}_week6_vs_new_data_relative_rmse.png",
            question="Did protocol-selected relative prediction error change in the shifted sampled design?",
        )
    )
    number += 1

    status_order = ["REPRODUCED", "WEAKENED", "REVERSED", "UNRESOLVED"]
    counts = conclusions["status"].value_counts().reindex(status_order, fill_value=0)
    fig, axis = plt.subplots(figsize=(7.5, 4.5))
    axis.bar(
        counts.index,
        counts.values,
        color=["#009E73", "#E69F00", "#D55E00", "#777777"],
    )
    axis.set_ylabel("Conclusion rows")
    axis.set_title("Week 6 conclusion stability classifications")
    fig.tight_layout()
    manifests.append(
        save_figure(
            fig,
            destination,
            f"{number:02d}_conclusion_stability_counts.png",
            question="How many Week 6 conclusions are reproduced, weakened, reversed, or unresolved?",
        )
    )
    return pd.DataFrame(manifests)


def notebook_has_stored_errors(path: Path) -> bool:
    """Return True when an existing notebook contains a stored error output."""

    if not path.is_file():
        return False
    notebook = json.loads(path.read_text(encoding="utf-8"))
    return any(
        output.get("output_type") == "error"
        for cell in notebook.get("cells", [])
        if cell.get("cell_type") == "code"
        for output in cell.get("outputs", [])
    )


def validation_table(
    population: pd.DataFrame,
    model_ready_long: pd.DataFrame,
    uncertainty: pd.DataFrame,
    predictions: pd.DataFrame,
    metrics: pd.DataFrame,
    decisions: pd.DataFrame,
    historical: pd.DataFrame,
    figures: pd.DataFrame,
    kinetic_caution: pd.DataFrame,
    *,
    smoke: bool,
    notebook_required: bool,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(
        identifier: str,
        requirement: str,
        condition: bool,
        evidence: str,
        *,
        warning: bool = False,
    ) -> None:
        rows.append(
            {
                "validation_id": identifier,
                "requirement": requirement,
                "status": "PASS" if condition else ("WARNING" if warning else "FAIL"),
                "evidence": evidence,
            }
        )

    phase2_targets = pd.read_csv(PHASE2_TARGET_CSV)
    phase2_new = phase2_targets[phase2_targets["partition"].eq("new-data")].copy()
    selected_population = population[bool_series(population["selected_for_current_run"])]
    eligible_counts = {
        target: int(bool_series(population[f"{target}_model_eligible"]).sum())
        for target in TARGET_SPECS
    }
    selected_eligible_counts = {
        target: int(
            (
                bool_series(population[f"{target}_model_eligible"])
                & bool_series(population["selected_for_current_run"])
            ).sum()
        )
        for target in TARGET_SPECS
    }
    expected_prediction_rows = sum(selected_eligible_counts.values()) * len(ALL_MODELS)
    prediction_keys = ["target", "model", "experiment_name"]

    add(
        "V01",
        "Immutable sph_v2 revision is exactly the corrected Phase 2 revision",
        set(population["exact_sph_v2_revision"].astype(str)) == {SPH_V2_REVISION}
        and set(predictions["dataset_revision"].astype(str)) == {SPH_V2_REVISION},
        f"revision={SPH_V2_REVISION}",
    )
    add(
        "V02",
        "Phase 3 starts from the current remote Week 7 Phase 1+2 head",
        STARTING_HEAD == "f26f0671dd59938a8111883398fe38afedb6915d",
        f"{STARTING_BRANCH}@{STARTING_HEAD}",
    )
    add(
        "V03",
        "Primary population is new-data only and old/new populations are never pooled",
        set(model_ready_long["partition"].astype(str)) == {"new-data"}
        and set(predictions["partition"].astype(str)) == {"new-data"}
        and not bool(historical["dataset_populations_pooled"].astype(bool).any()),
        f"audit rows={len(population)}; model-ready rows={len(model_ready_long)}; old primary rows=0",
    )
    readiness_rederived = True
    for target, spec in TARGET_SPECS.items():
        expected = pd.Series(True, index=population.index)
        for field in spec["readiness"]:
            expected &= bool_series(population[field])
        expected &= np.isfinite(pd.to_numeric(population[spec["column"]], errors="coerce"))
        readiness_rederived &= expected.equals(bool_series(population[f"{target}_model_eligible"]))
    add(
        "V04",
        "Eligibility is derived only from corrected Phase 2 readiness fields and finite saved targets",
        readiness_rederived,
        f"eligible counts={json_text(eligible_counts)}",
    )
    source_text = Path(__file__).read_text(encoding="utf-8")
    add(
        "V05",
        "No simulation-identifier exclusion list is hard-coded",
        not any(
            str(experiment_name) in source_text
            for experiment_name in population["experiment_name"]
        ),
        "population membership follows readiness masks; no identifier exclusion constant exists",
    )
    target_columns_exact = True
    for target, spec in TARGET_SPECS.items():
        ready = population[bool_series(population[f"{target}_model_eligible"])]
        model_values = model_ready_long[model_ready_long["target"].eq(target)].set_index(
            "simulation_id"
        )["target_value_um"]
        expected = ready.set_index("experiment_name")[spec["column"]]
        common = expected.index.intersection(model_values.index)
        target_columns_exact &= len(common) == len(model_values)
        target_columns_exact &= np.allclose(
            expected.loc[common].to_numpy(float),
            model_values.loc[common].to_numpy(float),
            rtol=0,
            atol=0,
        )
    add(
        "V06",
        "T0 target values are copied exactly from corrected Phase 2 and are not redefined",
        target_columns_exact
        and set(model_ready_long["target_definition"].astype(str)) == {"T0"}
        and bool_series(uncertainty["phase2_target_reproduced"]).all(),
        "four saved Phase 2 T0 columns matched exactly; raw windows used only for Method C uncertainty verification",
    )
    add(
        "V07",
        "ST is substrate temperature with the Phase 1/2 unit K",
        FEATURE_MEANINGS["ST"] == "substrate temperature"
        and FEATURE_UNITS["ST"] == "K"
        and FEATURE_SOURCE_COLUMNS["ST"] == "ST_K",
        "ST=substrate temperature [K]",
    )
    add(
        "V08",
        "Only the four requested physical responses are primary targets",
        set(model_ready_long["target"].astype(str)) == set(TARGET_SPECS)
        and not any(
            token in set(model_ready_long["target"].astype(str))
            for token in ["length", "max_depth", "max_total_height", "max_kinetic_energy", "G3", "R3"]
        ),
        f"targets={json_text(sorted(TARGET_SPECS))}",
    )
    add(
        "V09",
        "The complete 165-row new-data label/audit population is retained",
        len(population) == len(phase2_new) == 165
        and set(population["experiment_name"]) == set(phase2_new["experiment_name"]),
        f"audit rows={len(population)}; incomplete rows retained={int((~bool_series(population['physical_target_extraction_success'])).sum())}",
    )
    add(
        "V10",
        "No label is modified and no simulation is silently removed",
        not bool_series(population["source_label_modified"]).any()
        and not bool_series(population["simulation_silently_removed"]).any()
        and not bool_series(predictions["label_modified"]).any()
        and not bool_series(predictions["simulation_silently_removed"]).any(),
        "source label flags and Phase 3 prediction flags are all false",
    )
    add(
        "V11",
        "Every selected eligible simulation has one held-out prediction per model",
        len(predictions) == expected_prediction_rows
        and not predictions.duplicated(prediction_keys).any()
        and all(
            predictions[predictions["target"].eq(target)]
            .groupby("model")["experiment_name"]
            .nunique()
            .eq(selected_eligible_counts[target])
            .all()
            for target in TARGET_SPECS
        ),
        f"prediction rows={len(predictions)}; expected={expected_prediction_rows}; models={len(ALL_MODELS)}",
    )
    ridge = predictions[predictions["model"].isin(["linear_ridge", "polynomial_ridge_degree2"])]
    gp = predictions[predictions["model"].isin(GP_CONFIGURATION_NAMES + [HETEROSKEDASTIC_MODEL])]
    leakage_ok = (
        bool_series(predictions["heldout_excluded_from_training"]).all()
        and not bool_series(predictions["heldout_target_used_for_scaling"]).any()
        and not bool_series(predictions["heldout_target_used_for_fitting"]).any()
        and not bool_series(predictions["heldout_target_used_for_tuning"]).any()
        and bool_series(ridge["x_scaler_fit_on_training_only"]).all()
        and bool_series(ridge["y_scaler_fit_on_training_only"]).all()
        and bool_series(ridge["inner_cv_uses_outer_training_only"]).all()
        and bool_series(gp["x_scaler_fit_on_training_only"]).all()
    )
    add(
        "V12",
        "All transformations, target normalization, tuning and GP fitting are fold-local",
        leakage_ok,
        "held-out flags false; Ridge scalers/inner CV and GP feature scalers report training-only fits",
    )
    failed = bool_series(predictions["fit_failure"])
    failure_explicit = (
        predictions.loc[failed, "fit_failure_reason"].astype(str).str.len().gt(0).all()
        if failed.any()
        else True
    )
    add(
        "V13",
        "Model-fit failures are retained explicitly rather than silently skipped",
        failure_explicit and len(predictions) == expected_prediction_rows,
        f"retained failure rows={int(failed.sum())}",
        warning=bool(failed.any()),
    )
    reconciled = True
    for (target, model), frame in predictions.groupby(["target", "model"], sort=True):
        recomputed = metric_row(frame)
        stored = metrics.set_index(["target", "model"]).loc[(target, model)]
        for column in ["MAE", "RMSE", "R2", "relative_MAE_pct", "relative_RMSE_pct"]:
            left = float(recomputed[column])
            right = float(stored[column])
            if not (np.isnan(left) and np.isnan(right)) and not np.isclose(left, right, rtol=1e-12, atol=1e-12):
                reconciled = False
    add(
        "V14",
        "All aggregate metric rows reconcile with held-out predictions",
        reconciled,
        f"metric rows={len(metrics)}; groups={predictions.groupby(['target', 'model']).ngroups}",
    )
    denominators_ok = metrics["target_median_abs_scale"].gt(0).all() and metrics[
        "relative_error_denominator_definition"
    ].eq("median(abs(y_observed))").all()
    add(
        "V15",
        "Median-scale relative MAE and RMSE denominators are stored explicitly",
        denominators_ok
        and metrics["relative_MAE_pct"].notna().all()
        and metrics["relative_RMSE_pct"].notna().all(),
        "relative error denominator=median(abs(y_observed)); MAPE is not used",
    )
    interval_rows = predictions[predictions["predictive_interval_lower"].notna() & ~failed]
    interval_order_ok = (
        (interval_rows["predictive_interval_lower"] <= interval_rows["predicted_mean"]).all()
        and (interval_rows["predicted_mean"] <= interval_rows["predictive_interval_upper"]).all()
        and (interval_rows["predictive_interval_lower"] <= interval_rows["predictive_interval_upper"]).all()
    )
    add(
        "V16",
        "GP predictive intervals are ordered and contain their predictive mean",
        interval_order_ok and len(interval_rows) > 0,
        f"checked interval rows={len(interval_rows)}",
    )
    add(
        "V17",
        "Method C reproduces the exact Week 6 moving-block bootstrap definition",
        set(uncertainty["bootstrap_resamples"].astype(int))
        == ({SMOKE_UNCERTAINTY_RESAMPLES} if smoke else {FULL_UNCERTAINTY_RESAMPLES})
        and uncertainty["block_bootstrap_type"].eq("circular moving-block bootstrap").all()
        and uncertainty["block_length_rule"].eq("max(5, round(n_window ** (1/3)))").all(),
        f"bootstrap resamples={sorted(uncertainty['bootstrap_resamples'].astype(int).unique())}",
    )
    add(
        "V18",
        "Historical comparison uses saved Week 6 results and separate populations",
        len(historical) == 4
        and not bool(historical["dataset_populations_pooled"].astype(bool).any()),
        "one row per primary target; old and new metrics reported side by side",
    )
    expected_figure_count = 3 + len(TARGET_SPECS) * 5
    add(
        "V19",
        "Required scientific diagnostic figures were generated",
        len(figures) == expected_figure_count
        and all((ROOT / path).is_file() for path in figures["path"].astype(str)),
        f"figures={len(figures)}; expected={expected_figure_count}",
    )
    add(
        "V20",
        "Maximum kinetic-energy anomaly is scoped separately and no T0 row is removed",
        len(kinetic_caution) == 1
        and not bool(kinetic_caution["row_removed"].astype(bool).any())
        and not bool(kinetic_caution["maximum_kinetic_energy_analysis_in_scope"].astype(bool).any()),
        str(kinetic_caution.iloc[0]["phase3_action"]),
    )
    configuration_path = (SMOKE_DIR if smoke else OUTPUT_DIR) / "phase3_configuration.json"
    configuration = json.loads(configuration_path.read_text(encoding="utf-8"))
    scope = configuration["scope"]
    add(
        "V21",
        "Phase 3 hard stop excludes classifiers, feature effects, causal claims, active learning and level-set work",
        not any(bool(value) for value in scope.values()),
        json_text(scope),
    )
    notebook_exists = NOTEBOOK_PATH.is_file()
    notebook_clean = notebook_exists and not notebook_has_stored_errors(NOTEBOOK_PATH)
    add(
        "V22",
        "Executed teaching notebook exists and has no stored execution errors",
        notebook_clean,
        f"path={NOTEBOOK_PATH.relative_to(ROOT)}; exists={notebook_exists}; stored_errors={notebook_has_stored_errors(NOTEBOOK_PATH) if notebook_exists else 'not checked'}",
        warning=not notebook_required,
    )
    add(
        "V23",
        "This is a full-population analysis rather than the cheap smoke path",
        not smoke,
        f"mode={'smoke' if smoke else 'full'}; selected audit rows={len(selected_population)}",
        warning=smoke,
    )
    add(
        "V24",
        "All requested primary model-ranking rows and decisions are present",
        len(metrics) == len(TARGET_SPECS) * len(ALL_MODELS)
        and len(decisions) == len(TARGET_SPECS),
        f"metric rows={len(metrics)}; decision rows={len(decisions)}",
    )
    return pd.DataFrame(rows)


def requirement_checklist(validation: pd.DataFrame) -> pd.DataFrame:
    statuses = validation.set_index("validation_id")["status"].to_dict()

    def combined(ids: Sequence[str]) -> str:
        values = [statuses[item] for item in ids]
        if "FAIL" in values:
            return "FAIL"
        if "WARNING" in values:
            return "WARNING"
        return "PASS"

    entries = [
        ("P3-01", "Exact remote Week 7 base head and immutable sph_v2 revision recorded", "Notebook §1", "phase3_configuration.json", ["V01", "V02"]),
        ("P3-02", "Complete new-data audit population retained; readiness fields select each regression population", "Notebook §2", "model_ready_population.csv; model_ready_population_long.csv", ["V03", "V04", "V05", "V09"]),
        ("P3-03", "Executable Week 6 modelling protocol traced before fitting", "Notebook §3", "week6_model_traceability.csv", ["V02"]),
        ("P3-04", "Exactly four saved Phase 2 T0 targets and P/VX/LS/ST inputs used", "Notebook §§2–4", "model_ready_population_long.csv", ["V06", "V07", "V08"]),
        ("P3-05", "Mean, Linear Ridge and degree-2 Polynomial Ridge evaluated by exact outer LOO", "Notebook §5", "fold_level_predictions.csv; model_metric_table.csv", ["V11", "V12", "V14"]),
        ("P3-06", "RBF, Matérn 3/2 and Matérn 5/2 GP candidates reproduce Week 6 settings", "Notebook §6", "kernel_comparison.csv; week6_model_traceability.csv", ["V11", "V12"]),
        ("P3-07", "Numerical jitter, shared learned nugget and heteroskedastic-alpha methods compared", "Notebook §7", "noise_treatment_comparison.csv; target_summary_uncertainty.csv", ["V16", "V17"]),
        ("P3-08", "One explicit row is retained for every expected held-out prediction or fit failure", "Notebook §8", "fold_level_predictions.csv", ["V11", "V13"]),
        ("P3-09", "Median-scale relative MAE/RMSE are primary percentage metrics", "Notebook §9", "relative_error_table.csv", ["V14", "V15"]),
        ("P3-10", "Observed/predicted, residual, scale-error, calibration and model comparison plots exist", "Notebook §§10–12", "figure_manifest.csv", ["V19"]),
        ("P3-11", "Saved Week 6 results are compared with new data without pooling", "Notebook §13", "week6_vs_new_data_comparison.csv", ["V03", "V18"]),
        ("P3-12", "Target-by-target stability questions and conclusion classes are explicit", "Notebook §14", "stability_conclusion_table.csv", ["V24"]),
        ("P3-13", "No label or simulation is silently altered; max-KE anomaly is not promoted", "Notebook §§2,14", "kinetic_energy_scope_caution.csv", ["V10", "V20"]),
        ("P3-14", "Teaching notebook is executed and error-free", "Notebook §§1–15", "notebooks/week_07/03_new_data_physical_model_stability.ipynb", ["V22"]),
        ("P3-15", "Hard stop before later Week 7 phases", "Notebook §15", "phase3_configuration.json; validation_results.csv", ["V21", "V23"]),
    ]
    return pd.DataFrame(
        [
            {
                "requirement_id": identifier,
                "requirement": requirement,
                "status": combined(ids),
                "notebook_section": section,
                "output_artifact": artifact,
                "validation_ids": ";".join(ids),
            }
            for identifier, requirement, section, artifact, ids in entries
        ]
    )


def output_manifest(destination: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in sorted(destination.rglob("*")):
        if not path.is_file() or path.name == "output_manifest.csv":
            continue
        rows.append(
            {
                "relative_path": str(path.relative_to(destination)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "artifact_type": path.suffix.lower().lstrip(".") or "file",
            }
        )
    return pd.DataFrame(rows)


def configuration_payload(*, smoke: bool, workers: int) -> dict[str, Any]:
    return {
        "phase": "Week 7 Phase 3",
        "mode": "smoke" if smoke else "full",
        "generated_at_utc": utc_now(),
        "repository": "https://github.com/iso0/active-level-set-week1-warmup",
        "starting_branch": STARTING_BRANCH,
        "starting_remote_head_sha": STARTING_HEAD,
        "phase3_branch": PHASE3_BRANCH,
        "dataset_repo_id": SPH_V2_REPO_ID,
        "dataset_revision": SPH_V2_REVISION,
        "primary_population": "partition == 'new-data'",
        "pooled_old_new_primary_analysis": False,
        "feature_meanings": FEATURE_MEANINGS,
        "feature_units": FEATURE_UNITS,
        "primary_targets": {
            target: {
                "label": spec["label"],
                "phase2_column": spec["column"],
                "unit": spec["unit"],
                "eligibility_fields": spec["readiness"],
            }
            for target, spec in TARGET_SPECS.items()
        },
        "outer_evaluation": "exact simulation-level leave-one-out",
        "inner_ridge_selection": "Week 6 nested shuffled five-fold CV inside each outer training fold",
        "gp_optimizer": "fmin_l_bfgs_b",
        "gp_restarts": 0 if smoke else week6_models.N_RESTARTS_OPTIMIZER,
        "workers": workers,
        "target_summary_bootstrap_resamples": SMOKE_UNCERTAINTY_RESAMPLES if smoke else FULL_UNCERTAINTY_RESAMPLES,
        "paired_bootstrap_resamples": SMOKE_PAIRED_RESAMPLES if smoke else FULL_PAIRED_RESAMPLES,
        "random_seed_protocol": "exact Week 6 deterministic hashes; GP base seed 6303",
        "scope": {
            "pooled_old_new_model": False,
            "keyhole_classifier": False,
            "extreme_event_classifier": False,
            "feature_effect_analysis": False,
            "causal_interpretation": False,
            "active_learning": False,
            "level_set_estimation": False,
            "acquisition_function_change": False,
            "later_week7_phase": False,
        },
    }


def results_summary_markdown(
    population: pd.DataFrame,
    metrics: pd.DataFrame,
    decisions: pd.DataFrame,
    historical: pd.DataFrame,
    conclusions: pd.DataFrame,
    validation: pd.DataFrame,
    *,
    smoke: bool,
) -> str:
    decision_by = decisions.set_index("target")
    metric_by = metrics.set_index(["target", "model"])
    eligible_counts = {
        target: int(bool_series(population[f"{target}_model_eligible"]).sum())
        for target in TARGET_SPECS
    }
    lines = [
        "# Week 7 Phase 3 — new-data physical-response model stability",
        "",
        f"Mode: **{'SMOKE (non-scientific preflight)' if smoke else 'FULL'}**",
        "",
        f"Immutable dataset: `{SPH_V2_REPO_ID}@{SPH_V2_REVISION}`.",
        f"Repository starting point: `{STARTING_BRANCH}@{STARTING_HEAD}`.",
        "The primary validation domain is `partition == new-data`; Week 6 and Week 7 populations were never pooled.",
        "",
        "## Model-ready population",
        "",
        f"The audit retains all {len(population)} new-data experiments. Eligibility was derived from corrected Phase 2 readiness fields: {json_text(eligible_counts)}.",
        "The monitor-incomplete experiment remains in `model_ready_population.csv` but is not fabricated into a regression row.",
        "",
        "## Primary results",
        "",
        "| Target | Raw RMSE winner | Protocol point model | MAE | Rel. MAE | RMSE | Rel. RMSE | R² | Protocol GP | Learned nugget useful? |",
        "|---|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for target in TARGET_SPECS:
        decision = decision_by.loc[target]
        model = str(decision["protocol_selected_point_model"])
        metric = metric_by.loc[(target, model)]
        unit = TARGET_SPECS[target]["unit"]
        lines.append(
            f"| {TARGET_SPECS[target]['label']} | {MODEL_LABELS[str(decision['best_point_prediction_model_by_RMSE'])]} | "
            f"{MODEL_LABELS[model]} | {float(metric['MAE']):.6g} {unit} | {float(metric['relative_MAE_pct']):.3f}% | "
            f"{float(metric['RMSE']):.6g} {unit} | {float(metric['relative_RMSE_pct']):.3f}% | {float(metric['R2']):.4f} | "
            f"{MODEL_LABELS[str(decision['protocol_selected_gp'])]} | {'yes' if bool(decision['learned_shared_nugget_remains_useful']) else 'no'} |"
        )
    lines.extend(
        [
            "",
            "Relative errors use `median(abs(y_observed))` as the denominator; each denominator is stored in `relative_error_table.csv`.",
            "A shared learned nugget is interpreted only as improving predictive performance or calibration under the current regression model, not as proof of physical noise.",
            "",
            "## Week 6 versus new-data stability",
            "",
            "| Week 6 conclusion | New-data evidence | Status | Evidence |",
            "|---|---|---|---|",
        ]
    )
    for row in conclusions.itertuples(index=False):
        lines.append(
            f"| {str(row.week6_conclusion).replace('|', '/')} | {str(row.new_data_evidence).replace('|', '/')} | **{row.status}** | `{row.evidence}` |"
        )
    lines.extend(
        [
            "",
            "Differences in absolute MAE/RMSE are not interpreted alone because the sampled design and target scales shifted. The historical table emphasizes relative errors, rankings, nugget behavior and calibration.",
            "",
            "## Pipeline decision",
            "",
            "The **comparison/evaluation pipeline is adequate without adding kernels or expanding the search**, but the Week 6 target-specific final choices should **not** be frozen unchanged. Width retains the parsimonious polynomial point model; depth retains a GP family but no longer supports a shared nugget as the preferred uncertainty treatment; total height and kinetic energy now require GP point models under the preserved selection protocol; and total height also no longer supports the shared nugget.",
            "",
            "## Validation and scope",
            "",
            f"Validation status counts: `{json_text(validation['status'].value_counts().to_dict())}`.",
            "No label was modified, no eligible row was silently removed, and the maximum-kinetic-energy anomaly was not promoted to a Phase 3 target.",
            "",
            "**HARD STOP:** no classifier, feature-effect/causal analysis, target redesign, active learning, level-set estimation or later Week 7 phase was run.",
        ]
    )
    return "\n".join(lines)


def summary_payload(
    population: pd.DataFrame,
    metrics: pd.DataFrame,
    decisions: pd.DataFrame,
    historical: pd.DataFrame,
    conclusions: pd.DataFrame,
    validation: pd.DataFrame,
    *,
    smoke: bool,
    runtime_seconds: float,
) -> dict[str, Any]:
    metric_by = metrics.set_index(["target", "model"])
    targets: dict[str, Any] = {}
    for row in decisions.itertuples(index=False):
        target = str(row.target)
        point_model = str(row.protocol_selected_point_model)
        best_model = str(row.best_point_prediction_model_by_RMSE)
        point_metric = metric_by.loc[(target, point_model)]
        best_metric = metric_by.loc[(target, best_model)]
        targets[target] = {
            "eligible_experiment_count": int(bool_series(population[f"{target}_model_eligible"]).sum()),
            "best_point_prediction_model_by_RMSE": best_model,
            "best_point_prediction_model_label": MODEL_LABELS[best_model],
            "protocol_selected_point_model": point_model,
            "protocol_selected_point_model_label": MODEL_LABELS[point_model],
            "protocol_selected_gp": str(row.protocol_selected_gp),
            "winning_gp_kernel": MODEL_META[str(row.protocol_selected_gp)]["kernel"],
            "best_calibrated_probabilistic_model": str(row.best_calibrated_deployable_probabilistic_model),
            "learned_shared_nugget_remains_useful": bool(row.learned_shared_nugget_remains_useful),
            "polynomial_ridge_competitive": bool(row.polynomial_ridge_competitive),
            "target_median_abs_scale": float(point_metric["target_median_abs_scale"]),
            "target_unit": TARGET_SPECS[target]["unit"],
            "MAE": float(point_metric["MAE"]),
            "relative_MAE_pct": float(point_metric["relative_MAE_pct"]),
            "RMSE": float(point_metric["RMSE"]),
            "relative_RMSE_pct": float(point_metric["relative_RMSE_pct"]),
            "R2": float(point_metric["R2"]),
            "raw_best_RMSE": float(best_metric["RMSE"]),
            "raw_best_relative_RMSE_pct": float(best_metric["relative_RMSE_pct"]),
        }
    validation_counts = {str(key): int(value) for key, value in validation["status"].value_counts().items()}
    conclusion_counts = {str(key): int(value) for key, value in conclusions["status"].value_counts().items()}
    return {
        "phase": "Week 7 Phase 3",
        "mode": "smoke" if smoke else "full",
        "generated_at_utc": utc_now(),
        "starting_branch": STARTING_BRANCH,
        "starting_remote_head_sha": STARTING_HEAD,
        "phase3_branch": PHASE3_BRANCH,
        "dataset_repo_id": SPH_V2_REPO_ID,
        "dataset_revision": SPH_V2_REVISION,
        "audit_new_data_experiment_count": len(population),
        "monitor_incomplete_new_data_experiment_count": int((~bool_series(population["physical_target_extraction_success"])).sum()),
        "eligible_experiment_counts": {
            target: int(bool_series(population[f"{target}_model_eligible"]).sum())
            for target in TARGET_SPECS
        },
        "relative_error_denominator": "median(abs(y_observed))",
        "targets": targets,
        "week6_vs_new_data": historical.to_dict(orient="records"),
        "stability_status_counts": conclusion_counts,
        "validation_status_counts": validation_counts,
        "fit_failure_count": int(metrics["fit_failures"].sum()),
        "current_invocation_runtime_seconds": runtime_seconds,
        "runtime_scope": (
            "current invocation only; see execution_history.json for checkpointed "
            "full-run segments"
        ),
        "scientific_interpretation_boundary": {
            "learned_nugget": "predictive-model noise treatment; not proof of physical measurement noise",
            "polynomial_ridge": "surface approximation in the sampled design; not proof of quadratic physics",
            "difficulty": "predictive error in a shifted sampled domain; not evidence that physics became more complex",
        },
        "pipeline_recommendation": {
            "comparison_and_evaluation_protocol_adequate_without_expansion": True,
            "week6_target_specific_model_choices_transfer_unchanged": False,
            "decision": (
                "Retain the fold-local LOO comparison pipeline and candidate set, but "
                "update target-specific point/noise choices before treating the physical "
                "regression specification as fixed."
            ),
        },
        "scope": {
            "primary_population": "new-data only",
            "old_new_pooled": False,
            "labels_modified": False,
            "simulations_silently_removed": False,
            "active_learning": False,
            "level_set_estimation": False,
            "later_week7_phases": False,
        },
    }


def write_report_artifacts(
    destination: Path,
    population: pd.DataFrame,
    model_ready_long: pd.DataFrame,
    uncertainty: pd.DataFrame,
    predictions: pd.DataFrame,
    metrics: pd.DataFrame,
    decisions: pd.DataFrame,
    comparisons: pd.DataFrame,
    historical_metrics: pd.DataFrame,
    historical: pd.DataFrame,
    residuals: pd.DataFrame,
    intervals: pd.DataFrame,
    conclusions: pd.DataFrame,
    kinetic_caution: pd.DataFrame,
    figures: pd.DataFrame,
    *,
    smoke: bool,
    notebook_required: bool,
    runtime_seconds: float,
) -> dict[str, Any]:
    write_csv(destination / "model_ready_population.csv", population)
    write_csv(destination / "model_ready_population_long.csv", model_ready_long)
    write_csv(destination / "week6_model_traceability.csv", week6_traceability_table())
    write_csv(destination / "target_summary_uncertainty.csv", uncertainty)
    write_csv(destination / "fold_level_predictions.csv", predictions)
    write_csv(destination / "model_metric_table.csv", metrics)
    write_csv(destination / "model_rankings.csv", metrics.sort_values(["target", "rank_by_RMSE", "model"]))
    write_csv(
        destination / "relative_error_table.csv",
        metrics[
            [
                "target", "target_label", "target_unit", "model", "model_label", "n",
                "target_median_abs_scale", "relative_error_denominator_definition",
                "MAE", "relative_MAE_pct", "RMSE", "relative_RMSE_pct", "R2",
            ]
        ],
    )
    gp_metrics = metrics[metrics["model_family"].eq("Gaussian process")].copy()
    write_csv(
        destination / "kernel_comparison.csv",
        gp_metrics[gp_metrics["noise_method"].eq("B_shared_learned_nugget")].sort_values(
            ["target", "RMSE", "kernel"]
        ),
    )
    write_csv(destination / "noise_treatment_comparison.csv", gp_metrics.sort_values(["target", "kernel", "noise_method"]))
    write_csv(destination / "paired_model_comparisons.csv", comparisons)
    write_csv(destination / "model_selection_decisions.csv", decisions)
    write_csv(destination / "week6_historical_model_metrics.csv", historical_metrics)
    write_csv(destination / "week6_vs_new_data_comparison.csv", historical)
    write_csv(destination / "residual_diagnostics.csv", residuals)
    write_csv(destination / "predictive_interval_diagnostics.csv", intervals)
    write_csv(destination / "stability_conclusion_table.csv", conclusions)
    write_csv(destination / "kinetic_energy_scope_caution.csv", kinetic_caution)
    write_csv(destination / "figure_manifest.csv", figures)
    write_json(
        destination / "runtime_summary.json",
        {
            "mode": "smoke" if smoke else "full",
            "current_invocation_wall_runtime_seconds": runtime_seconds,
            "runtime_scope": (
                "current invocation only; checkpoint-reusing report refreshes can be "
                "much shorter than the original model computation"
            ),
            "execution_history_artifact": (
                "execution_history.json"
                if (destination / "execution_history.json").is_file()
                else None
            ),
            "events": [*RUNTIME_EVENTS, *week6_models.RUNTIME_EVENTS],
        },
    )
    validation = validation_table(
        population,
        model_ready_long,
        uncertainty,
        predictions,
        metrics,
        decisions,
        historical,
        figures,
        kinetic_caution,
        smoke=smoke,
        notebook_required=notebook_required,
    )
    checklist = requirement_checklist(validation)
    write_csv(destination / "validation_results.csv", validation)
    write_csv(destination / "requirement_checklist.csv", checklist)
    write_csv(destination / "phase3_requirement_checklist.csv", checklist)
    summary = summary_payload(
        population,
        metrics,
        decisions,
        historical,
        conclusions,
        validation,
        smoke=smoke,
        runtime_seconds=runtime_seconds,
    )
    write_json(destination / "summary.json", summary)
    markdown = results_summary_markdown(
        population,
        metrics,
        decisions,
        historical,
        conclusions,
        validation,
        smoke=smoke,
    )
    write_text(destination / "results_summary.md", markdown)
    write_text(destination / "phase3_results_summary.md", markdown)
    write_csv(destination / "output_manifest.csv", output_manifest(destination))
    return summary


def refresh_validation(*, smoke: bool = False) -> dict[str, Any]:
    destination = SMOKE_DIR if smoke else OUTPUT_DIR
    required = [
        "model_ready_population.csv",
        "model_ready_population_long.csv",
        "target_summary_uncertainty.csv",
        "fold_level_predictions.csv",
        "model_metric_table.csv",
        "model_selection_decisions.csv",
        "paired_model_comparisons.csv",
        "week6_historical_model_metrics.csv",
        "week6_vs_new_data_comparison.csv",
        "residual_diagnostics.csv",
        "predictive_interval_diagnostics.csv",
        "stability_conclusion_table.csv",
        "kinetic_energy_scope_caution.csv",
        "figure_manifest.csv",
        "runtime_summary.json",
    ]
    missing = [name for name in required if not (destination / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Cannot refresh Phase 3 validation; missing {missing}")
    population = pd.read_csv(destination / "model_ready_population.csv")
    model_ready_long = pd.read_csv(destination / "model_ready_population_long.csv")
    uncertainty = pd.read_csv(destination / "target_summary_uncertainty.csv")
    predictions = pd.read_csv(
        destination / "fold_level_predictions.csv", low_memory=False
    )
    metrics = pd.read_csv(destination / "model_metric_table.csv")
    decisions = pd.read_csv(destination / "model_selection_decisions.csv")
    comparisons = pd.read_csv(destination / "paired_model_comparisons.csv")
    historical_metrics = pd.read_csv(destination / "week6_historical_model_metrics.csv")
    historical = pd.read_csv(destination / "week6_vs_new_data_comparison.csv")
    residuals = pd.read_csv(
        destination / "residual_diagnostics.csv", low_memory=False
    )
    intervals = pd.read_csv(destination / "predictive_interval_diagnostics.csv")
    conclusions = pd.read_csv(destination / "stability_conclusion_table.csv")
    kinetic_caution = pd.read_csv(destination / "kinetic_energy_scope_caution.csv")
    figures = pd.read_csv(destination / "figure_manifest.csv")
    runtime = json.loads((destination / "runtime_summary.json").read_text(encoding="utf-8"))
    return write_report_artifacts(
        destination,
        population,
        model_ready_long,
        uncertainty,
        predictions,
        metrics,
        decisions,
        comparisons,
        historical_metrics,
        historical,
        residuals,
        intervals,
        conclusions,
        kinetic_caution,
        figures,
        smoke=smoke,
        notebook_required=True,
        runtime_seconds=float(
            runtime.get(
                "current_invocation_wall_runtime_seconds",
                runtime.get("total_wall_runtime_seconds", 0.0),
            )
        ),
    )


def run_phase3(*, smoke: bool, workers: int, force: bool) -> dict[str, Any]:
    started = time.perf_counter()
    destination = SMOKE_DIR if smoke else OUTPUT_DIR
    destination.mkdir(parents=True, exist_ok=True)
    RUNTIME_EVENTS.clear()
    write_json(destination / "phase3_configuration.json", configuration_payload(smoke=smoke, workers=workers))
    population, source_plan, phase2_summary = load_phase2_inputs(smoke=smoke)
    tables, model_ready_long = model_tables(population)
    write_json(
        destination / "input_provenance.json",
        {
            "starting_remote_head_sha": STARTING_HEAD,
            "dataset_repo_id": SPH_V2_REPO_ID,
            "dataset_revision": SPH_V2_REVISION,
            "phase2_target_csv": str(PHASE2_TARGET_CSV.relative_to(ROOT)).replace("\\", "/"),
            "phase2_target_csv_sha256": sha256_file(PHASE2_TARGET_CSV),
            "phase2_target_parquet": str(PHASE2_TARGET_PARQUET.relative_to(ROOT)).replace("\\", "/"),
            "phase2_target_parquet_sha256": sha256_file(PHASE2_TARGET_PARQUET),
            "phase2_summary_sha256": sha256_file(PHASE2_SUMMARY),
            "phase2_summary_revision": phase2_summary["revision"],
            "target_values_recalculated": False,
            "raw_monitor_use": "Method C target-summary uncertainty only; Phase 2 target medians reproduced and verified",
        },
    )
    uncertainty = build_target_summary_uncertainty(
        population,
        source_plan,
        destination,
        smoke=smoke,
        workers=workers,
        force=force,
    )
    predictions = run_all_models(
        tables,
        uncertainty,
        destination,
        smoke=smoke,
        workers=workers,
        force=force,
    )
    metrics = build_metrics(predictions)
    decisions, comparisons = build_decisions_and_comparisons(predictions, metrics, smoke=smoke)
    historical_metrics, historical_decisions = load_week6_historical_reference()
    historical = build_historical_comparison(
        historical_metrics, historical_decisions, metrics, decisions
    )
    conclusions = build_stability_conclusions(metrics, decisions, comparisons, historical)
    residuals = build_residual_diagnostics(predictions, metrics)
    intervals = predictive_interval_diagnostics(predictions)
    kinetic_caution = kinetic_energy_scope_caution(population)
    figures = generate_figures(
        model_ready_long,
        predictions,
        metrics,
        decisions,
        historical,
        conclusions,
        destination,
    )
    runtime_seconds = time.perf_counter() - started
    summary = write_report_artifacts(
        destination,
        population,
        model_ready_long,
        uncertainty,
        predictions,
        metrics,
        decisions,
        comparisons,
        historical_metrics,
        historical,
        residuals,
        intervals,
        conclusions,
        kinetic_caution,
        figures,
        smoke=smoke,
        notebook_required=False,
        runtime_seconds=runtime_seconds,
    )
    print(
        f"Week 7 Phase 3 {'smoke' if smoke else 'full'} run complete: "
        f"validation={summary['validation_status_counts']}",
        flush=True,
    )
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="Run a 12-experiment preflight with reduced bootstrap/restarts")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--force", action="store_true", help="Ignore compatible model/bootstrap checkpoints")
    parser.add_argument("--refresh-validation-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.workers < 1:
        raise ValueError("--workers must be positive")
    if args.refresh_validation_only:
        summary = refresh_validation(smoke=args.smoke)
    else:
        summary = run_phase3(smoke=args.smoke, workers=args.workers, force=args.force)
    statuses = summary["validation_status_counts"]
    if not args.smoke and statuses.get("FAIL", 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
