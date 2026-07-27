r"""Week 6 Phase 2.5: matched stable-depth GP closure.

This module deliberately reuses the validated Phase 2 fold fitter.  It only
compares the learned-nugget (B) and observation-specific-alpha (C) models for
penetration depth on the exact 230 Phase 1 stable-window simulations.

Rebuild:
    .\.venv\Scripts\python.exe \
        src\week6_phase2_5_depth_model_closure.py --full --force --workers 4

Validate existing artifacts:
    .\.venv\Scripts\python.exe \
        src\week6_phase2_5_depth_model_closure.py --validate-only
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score

try:
    from src import week6_phase2_gp_response_noise_comparison as phase2
except ModuleNotFoundError:
    import week6_phase2_gp_response_noise_comparison as phase2


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs" / "week6_02_5_depth_model_closure"
PHASE2_OUTPUT_DIR = ROOT / "outputs" / "week6_02_gp_response_noise_comparison"
PHASE1_INPUT = (
    ROOT
    / "outputs"
    / "week6_01_melt_pool_data_audit"
    / "week6_phase1_simulation_level_responses.csv"
)
NOTEBOOK_PATH = (
    ROOT
    / "notebooks"
    / "week_06"
    / "03_phase2_5_depth_model_closure.ipynb"
)

EXPECTED_BRANCH = "codex/week6-phase2-5-depth-closure"
PHASE1_REVISION = "0e859b748fdbc8454f66e58e101e333ac0479d42"
PHASE1_LEDGER_SHA256 = (
    "10DEF11AB64D62444AC14FED506266BEB748EEB5BF892ACDC12E7F0F6DDCF4FF"
)
PHASE1_AGGREGATE_SHA256 = (
    "21FF34AD767C8D4D6C536D66AFD147B8C700884321415078231B7A24D4C7D198"
)
PHASE2_SOURCE_HASHES = {
    "width_loo_predictions.csv": (
        "32FF3A2DB237D1A13CE35903F6B95E66EB614D9FD3028F4E9D429FA915A68F75"
    ),
    "length_loo_predictions.csv": (
        "50531D5BC00DC5C9FBAC897A2568929C344BB371FBF181339808B6EB8F44E1D0"
    ),
    "depth_loo_predictions.csv": (
        "B511702EAD9A91BBC407E2F9D447E62998470F3FD4214CE020520418B589DC00"
    ),
    "stable_subset_loo_predictions.csv": (
        "26C6A6E78B441B22DCCCE8B1573028F539ACD66FC962796ADE43344302E44525"
    ),
}
PHASE2_CONFIG_SHA256 = (
    "CBBA81F86E9B2B9FF46838B793733D9C7DE2982D1A398A67578A8AAE6C3647A6"
)
PHASE2_UNCERTAINTY_SHA256 = (
    "2CE2F5D7984D4A8483166434DD5A0FD7C6DFD700718ED93E7050517412E034FD"
)

FEATURE_COLUMNS = ["P", "VX", "LS", "ST"]
TARGET_SOURCE_COLUMN = (
    "melt_pool_depth_below_surface_selected_primary_scalar_target_m"
)
TARGET_UM_COLUMN = "depth_target_um"
UNCERTAINTY_VARIANCE_COLUMN = "depth_bootstrap_variance_um2"
UNCERTAINTY_STD_COLUMN = "depth_bootstrap_std_um"
METHOD_B = "B_learned_nugget"
METHOD_C = "C_heteroskedastic"
METHODS = [METHOD_B, METHOD_C]
PHASE2_ANALYSIS_LABEL = "stable_only_refit_loo"
PHASE2_5_ANALYSIS_LABEL = "phase2_5_matched_stable_depth_loo"
PAIRED_BOOTSTRAP_RESAMPLES = 10_000
DEFAULT_WORKERS = 4

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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def write_csv(frame: pd.DataFrame, filename: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    frame.to_csv(path, index=False, lineterminator="\n")
    return path


def write_json(payload: dict[str, Any], filename: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    path.write_text(
        json.dumps(_json_safe(payload), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, Path):
        return str(value)
    return value


def protocol_fingerprint() -> str:
    payload = {
        "phase1_revision": PHASE1_REVISION,
        "phase1_ledger_sha256": PHASE1_LEDGER_SHA256,
        "features": FEATURE_COLUMNS,
        "target": TARGET_SOURCE_COLUMN,
        "methods": METHODS,
        "stable_ids_removed": UNSTABLE_SIMULATIONS,
        "phase2_analysis_label_for_seed_compatibility": PHASE2_ANALYSIS_LABEL,
        "phase2_scientific_config_fingerprint": (
            phase2.scientific_config_fingerprint()
        ),
        "paired_bootstrap_resamples": PAIRED_BOOTSTRAP_RESAMPLES,
    }
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest().upper()


def _assert_source_hashes() -> dict[str, str]:
    if sha256(PHASE1_INPUT) != PHASE1_LEDGER_SHA256:
        raise RuntimeError("Phase 1 ledger SHA-256 changed")
    if (
        sha256(PHASE2_OUTPUT_DIR / "phase2_model_configuration.json")
        != PHASE2_CONFIG_SHA256
    ):
        raise RuntimeError("Phase 2 model configuration changed")
    if (
        sha256(
            PHASE2_OUTPUT_DIR / "target_summary_uncertainty_estimates.csv"
        )
        != PHASE2_UNCERTAINTY_SHA256
    ):
        raise RuntimeError("Phase 2 target-summary uncertainty artifact changed")
    current: dict[str, str] = {}
    for filename, expected in PHASE2_SOURCE_HASHES.items():
        actual = sha256(PHASE2_OUTPUT_DIR / filename)
        current[filename] = actual
        if actual != expected:
            raise RuntimeError(
                f"Existing Phase 2 prediction file changed: {filename}"
            )
    aggregate, _ = phase2.phase1_aggregate_sha256()
    if aggregate != PHASE1_AGGREGATE_SHA256:
        raise RuntimeError("Phase 1 protected-file aggregate changed")
    return current


def load_and_validate_sources() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load Phase 1/2 inputs and construct the exact stable modelling table."""

    _assert_source_hashes()
    phase1 = phase2.load_phase1_input()
    if set(phase1["huggingface_revision"].astype(str)) != {PHASE1_REVISION}:
        raise RuntimeError("Unexpected Phase 1 revision")

    flag_unstable = set(
        phase1.loc[
            phase1["flag_primary_window_unstable"].astype(bool),
            "simulation_id",
        ].astype(str)
    )
    expected_unstable = set(UNSTABLE_SIMULATIONS)
    if flag_unstable != expected_unstable:
        raise RuntimeError(
            "Phase 1 unstable flag does not match the expected 11 IDs"
        )

    uncertainty = pd.read_csv(
        PHASE2_OUTPUT_DIR / "target_summary_uncertainty_estimates.csv"
    )
    if not phase2._uncertainty_cache_is_valid(uncertainty):
        raise RuntimeError("Phase 2 target-summary uncertainty is invalid")
    modelling = phase2.uncertainty_wide_table(phase1, uncertainty)
    modelling = modelling.sort_values("numeric_simulation_id").reset_index(
        drop=True
    )
    stable = modelling.loc[
        ~modelling["flag_primary_window_unstable"].astype(bool)
    ].copy()
    stable = stable.sort_values("numeric_simulation_id").reset_index(drop=True)

    if len(stable) != 230:
        raise RuntimeError(f"Expected 230 stable simulations, got {len(stable)}")
    if stable["simulation_id"].duplicated().any():
        raise RuntimeError("Stable simulation IDs are duplicated")
    if stable["flag_primary_window_unstable"].astype(bool).any():
        raise RuntimeError("An unstable simulation remains in the stable subset")
    removed = set(modelling["simulation_id"]) - set(stable["simulation_id"])
    if removed != expected_unstable:
        raise RuntimeError(f"Unexpected removed simulation IDs: {removed}")
    if set(stable["simulation_id"]) != (
        set(modelling["simulation_id"]) - expected_unstable
    ):
        raise RuntimeError("A stable simulation was accidentally removed")
    if not np.isfinite(stable[FEATURE_COLUMNS].to_numpy(float)).all():
        raise RuntimeError("Stable input contains a missing/non-finite feature")
    if (
        not np.isfinite(stable[TARGET_UM_COLUMN].to_numpy(float)).all()
        or not (stable[TARGET_UM_COLUMN].to_numpy(float) > 0).all()
    ):
        raise RuntimeError("Stable depth target is missing, non-finite, or non-positive")
    if (
        not np.isfinite(
            stable[UNCERTAINTY_VARIANCE_COLUMN].to_numpy(float)
        ).all()
        or (stable[UNCERTAINTY_VARIANCE_COLUMN].to_numpy(float) < 0).any()
    ):
        raise RuntimeError("Stable depth bootstrap variance is invalid")

    input_columns = [
        "simulation_id",
        "numeric_simulation_id",
        *FEATURE_COLUMNS,
        TARGET_SOURCE_COLUMN,
        TARGET_UM_COLUMN,
        "flag_primary_window_unstable",
        UNCERTAINTY_VARIANCE_COLUMN,
        UNCERTAINTY_STD_COLUMN,
    ]
    stable_input = stable[input_columns].copy()
    stable_input["fold_index"] = np.arange(len(stable_input), dtype=int)
    return phase1, uncertainty, stable_input


def modelling_table_from_stable_input(
    phase1: pd.DataFrame, uncertainty: pd.DataFrame
) -> pd.DataFrame:
    modelling = phase2.uncertainty_wide_table(phase1, uncertainty)
    stable = modelling.loc[
        ~modelling["flag_primary_window_unstable"].astype(bool)
    ].copy()
    return stable.sort_values("numeric_simulation_id").reset_index(drop=True)


def configuration(stable_input: pd.DataFrame) -> dict[str, Any]:
    original_baseline = json.loads(
        (
            ROOT
            / "outputs"
            / "week6_01_melt_pool_data_audit"
            / "original_worktree_baseline.json"
        ).read_text(encoding="utf-8")
    )
    return {
        "created_at_utc": utc_now(),
        "purpose": (
            "matched 230-stable-simulation depth-only comparison of Phase 2 "
            "Methods B and C"
        ),
        "branch": EXPECTED_BRANCH,
        "worktree_safety_baseline_before_phase2_5_changes": {
            "working_directory_and_repository_root": str(ROOT),
            "branch": "codex/week6-phase2-gp-response-models",
            "head": "1751286bb0da617d8c8c57a5440d187ca288e720",
            "status_short": [
                " M requirements.txt",
                "?? notebooks/week_06/",
                "?? outputs/week6_01_melt_pool_data_audit/",
                "?? outputs/week6_02_gp_response_noise_comparison/",
                "?? scripts/",
                "?? src/week6_phase1_melt_pool_data_audit.py",
                "?? src/week6_phase2_gp_response_noise_comparison.py",
            ],
            "phase2_uncommitted_file_inventory": sorted(
                path.relative_to(ROOT).as_posix()
                for path in PHASE2_OUTPUT_DIR.rglob("*")
                if path.is_file()
            ),
        },
        "original_dirty_worktree_baseline": original_baseline,
        "phase1_input": str(PHASE1_INPUT.relative_to(ROOT)),
        "phase1_revision": PHASE1_REVISION,
        "phase1_ledger_sha256": PHASE1_LEDGER_SHA256,
        "phase1_protected_aggregate_sha256": PHASE1_AGGREGATE_SHA256,
        "phase2_source_hashes": PHASE2_SOURCE_HASHES,
        "phase2_configuration_sha256": PHASE2_CONFIG_SHA256,
        "phase2_uncertainty_sha256": PHASE2_UNCERTAINTY_SHA256,
        "protocol_fingerprint": protocol_fingerprint(),
        "stable_subset": {
            "row_count": len(stable_input),
            "removed_count": len(UNSTABLE_SIMULATIONS),
            "removed_simulation_ids": UNSTABLE_SIMULATIONS,
            "construction": (
                "Phase 1 flag_primary_window_unstable independently matched "
                "against the expected 11-ID set"
            ),
            "fold_order": "ascending numeric_simulation_id",
            "first_simulation_id": str(stable_input.iloc[0]["simulation_id"]),
            "last_simulation_id": str(stable_input.iloc[-1]["simulation_id"]),
        },
        "features": FEATURE_COLUMNS,
        "target_source_m": TARGET_SOURCE_COLUMN,
        "target_model_unit": "micrometres",
        "unit_conversion": "depth_um = depth_m * 1e6",
        "common_settings": {
            "base_kernel": (
                "ConstantKernel(1.0, (1e-3, 1e3)) * "
                "Matern(length_scale=1.0, bounds=(1e-2, 1e2), nu=1.5)"
            ),
            "optimizer": "fmin_l_bfgs_b (L-BFGS-B)",
            "n_restarts_optimizer": phase2.N_RESTARTS_OPTIMIZER,
            "normalize_y": False,
            "x_scaling": "fold-local StandardScaler on 229 training rows",
            "y_scaling": "fold-local population mean/std on 229 training targets",
            "seed_policy": (
                "Phase 2 deterministic_seed('loo-fold', "
                "'stable_only_refit_loo', 'depth', fold_index); identical B/C"
            ),
        },
        "methods": {
            METHOD_B: {
                "kernel": "base kernel + WhiteKernel(0.01, (1e-8, 1e1))",
                "alpha_normalized": phase2.ALPHA_B_NORMALIZED,
                "interpretation": (
                    "learned common effective discrepancy; not stochastic "
                    "simulator noise"
                ),
                "evaluation_variance": (
                    "total variance including optimized WhiteKernel nugget"
                ),
            },
            METHOD_C: {
                "kernel": "base kernel without WhiteKernel",
                "alpha_formula": (
                    "depth_bootstrap_variance_um2 / "
                    "training_y_standard_deviation_um**2 + 1e-6"
                ),
                "interpretation": (
                    "observation-specific target-summary uncertainty proxy; "
                    "not measurement noise"
                ),
                "evaluation_variance": (
                    "oracle retrospective latent variance plus held-out "
                    "target-summary variance; not deployable for unseen runs"
                ),
            },
        },
        "cross_validation": {
            "kind": "exact simulation-level leave-one-out",
            "training_rows_per_fold": 229,
            "predictions_per_method": 230,
            "new_predictions_total": 460,
            "identical_fold_order_and_seed_for_B_and_C": True,
        },
        "paired_bootstrap": {
            "resamples": PAIRED_BOOTSTRAP_RESAMPLES,
            "joint_resampling_unit": "stable simulation ID",
            "differences": ["MAE_C_minus_B_um", "RMSE_C_minus_B_um"],
        },
        "scope_exclusions": [
            "width reruns",
            "length reruns",
            "Method A scientific rerun",
            "new kernels",
            "ARD",
            "new targets/windows",
            "feature-effect or Sobol analysis",
            "active learning",
            "level-set estimation",
            "classification",
            "new labels",
        ],
    }


def _prediction_path(method: str) -> Path:
    filename = (
        "stable_depth_B_loo_predictions.csv"
        if method == METHOD_B
        else "stable_depth_C_loo_predictions.csv"
    )
    return OUTPUT_DIR / filename


def _prediction_is_valid(
    frame: pd.DataFrame, stable_input: pd.DataFrame, method: str
) -> bool:
    required = {
        "simulation_id",
        "heldout_simulation_id",
        "fold_index",
        "target",
        "method",
        "phase2_5_analysis_label",
        "phase2_5_protocol_fingerprint",
        "predicted_mean_um",
        "latent_predictive_std_um",
    }
    expected_ids = stable_input["simulation_id"].astype(str).tolist()
    return bool(
        required.issubset(frame.columns)
        and len(frame) == 230
        and frame["simulation_id"].astype(str).tolist() == expected_ids
        and frame["heldout_simulation_id"].astype(str).tolist() == expected_ids
        and frame["fold_index"].astype(int).tolist() == list(range(230))
        and frame["simulation_id"].is_unique
        and set(frame["target"].astype(str)) == {"depth"}
        and set(frame["method"].astype(str)) == {method}
        and set(frame["phase2_5_analysis_label"].astype(str))
        == {PHASE2_5_ANALYSIS_LABEL}
        and set(frame["phase2_5_protocol_fingerprint"].astype(str))
        == {protocol_fingerprint()}
        and np.isfinite(frame["predicted_mean_um"]).all()
        and (frame["latent_predictive_std_um"].to_numpy(float) > 0).all()
    )


def _prepare_prediction_output(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result.insert(
        0, "simulation_id", result["heldout_simulation_id"].astype(str)
    )
    result.insert(1, "phase2_5_analysis_label", PHASE2_5_ANALYSIS_LABEL)
    result.insert(2, "phase2_5_protocol_fingerprint", protocol_fingerprint())
    result.insert(
        result.columns.get_loc("optimized_signal_variance_normalized") + 1,
        "optimized_constant_value_normalized",
        result["optimized_signal_variance_normalized"].to_numpy(float),
    )
    return result


def run_or_load_method(
    modelling: pd.DataFrame,
    stable_input: pd.DataFrame,
    *,
    method: str,
    workers: int,
    force: bool,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    path = _prediction_path(method)
    if not force and path.exists():
        cached = pd.read_csv(path)
        if _prediction_is_valid(cached, stable_input, method):
            return cached, {
                "method": method,
                "cache_reused": True,
                "measured_wall_runtime_seconds": 0.0,
                "timer_start_utc": None,
                "timer_end_utc": None,
                "included": ["artifact validation and load"],
                "excluded": ["all GP fits because the Phase 2.5 artifact was cached"],
            }

    start_utc = utc_now()
    started = time.perf_counter()
    raw = phase2.run_loo_method(
        modelling,
        target_key="depth",
        method=method,
        analysis_label=PHASE2_ANALYSIS_LABEL,
        workers=workers,
        n_restarts_optimizer=phase2.N_RESTARTS_OPTIMIZER,
        force=True,
        use_checkpoint=False,
    )
    runtime = time.perf_counter() - started
    end_utc = utc_now()
    result = _prepare_prediction_output(raw)
    if not _prediction_is_valid(result, stable_input, method):
        raise RuntimeError(f"Generated Phase 2.5 {method} predictions are invalid")
    write_csv(result, path.name)
    return result, {
        "method": method,
        "cache_reused": False,
        "measured_wall_runtime_seconds": runtime,
        "timer_start_utc": start_utc,
        "timer_end_utc": end_utc,
        "included": [
            "230 exact LOO folds",
            "fold-local X/y scaling",
            "one initial L-BFGS-B optimization plus one deterministic restart",
            "prediction and fold diagnostics",
            "CSV serialization after the timer",
        ],
        "excluded": [
            "Phase 2 target-summary bootstrap",
            "notebook execution",
            "Phase 2.5 reporting and validation",
        ],
    }


def build_metrics(
    predictions_b: pd.DataFrame, predictions_c: pd.DataFrame
) -> pd.DataFrame:
    rows = [
        phase2.metric_row(
            predictions_b, analysis_label=PHASE2_5_ANALYSIS_LABEL
        ),
        phase2.metric_row(
            predictions_c, analysis_label=PHASE2_5_ANALYSIS_LABEL
        ),
    ]
    frame = pd.DataFrame(rows).sort_values("method").reset_index(drop=True)
    frame.insert(1, "phase2_5_protocol_fingerprint", protocol_fingerprint())
    return frame


def build_paired_comparison(
    predictions_b: pd.DataFrame, predictions_c: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    columns = [
        "simulation_id",
        "fold_index",
        "observed_target_um",
        "predicted_mean_um",
        "residual_um",
        "absolute_error_um",
        "squared_error_um2",
    ]
    b = predictions_b[columns].copy().set_index("simulation_id")
    c = predictions_c[columns].copy().set_index("simulation_id")
    if b.index.tolist() != c.index.tolist():
        raise RuntimeError("B/C paired comparison is not in identical fold order")
    if not np.allclose(
        b["observed_target_um"], c["observed_target_um"], atol=0, rtol=0
    ):
        raise RuntimeError("B/C observed targets differ")

    detail = pd.DataFrame(
        {
            "simulation_id": b.index,
            "fold_index": b["fold_index"].to_numpy(int),
            "observed_depth_um": b["observed_target_um"].to_numpy(float),
            "B_predicted_mean_um": b["predicted_mean_um"].to_numpy(float),
            "C_predicted_mean_um": c["predicted_mean_um"].to_numpy(float),
            "B_residual_um": b["residual_um"].to_numpy(float),
            "C_residual_um": c["residual_um"].to_numpy(float),
            "B_absolute_error_um": b["absolute_error_um"].to_numpy(float),
            "C_absolute_error_um": c["absolute_error_um"].to_numpy(float),
            "absolute_error_C_minus_B_um": (
                c["absolute_error_um"].to_numpy(float)
                - b["absolute_error_um"].to_numpy(float)
            ),
            "B_squared_error_um2": b["squared_error_um2"].to_numpy(float),
            "C_squared_error_um2": c["squared_error_um2"].to_numpy(float),
            "squared_error_C_minus_B_um2": (
                c["squared_error_um2"].to_numpy(float)
                - b["squared_error_um2"].to_numpy(float)
            ),
        }
    )
    tolerance = 1e-12
    difference = detail["absolute_error_C_minus_B_um"].to_numpy(float)
    detail["paired_outcome"] = np.where(
        difference < -tolerance,
        "C_improved",
        np.where(difference > tolerance, "B_improved", "tied"),
    )

    seed = phase2.deterministic_seed(
        "phase2-5-paired-bootstrap", "depth", METHOD_B, METHOD_C
    )
    residual_b = detail["B_residual_um"].to_numpy(float)
    residual_c = detail["C_residual_um"].to_numpy(float)
    mae_boot, rmse_boot = phase2._paired_bootstrap_differences(
        residual_b,
        residual_c,
        seed=seed,
        resamples=PAIRED_BOOTSTRAP_RESAMPLES,
    )
    mae_low, mae_high = np.quantile(mae_boot, phase2.BOOTSTRAP_QUANTILES)
    rmse_low, rmse_high = np.quantile(
        rmse_boot, phase2.BOOTSTRAP_QUANTILES
    )
    mae_difference = float(
        detail["C_absolute_error_um"].mean()
        - detail["B_absolute_error_um"].mean()
    )
    rmse_b = math.sqrt(float(np.mean(residual_b**2)))
    rmse_c = math.sqrt(float(np.mean(residual_c**2)))
    rmse_difference = rmse_c - rmse_b

    summary = pd.DataFrame(
        [
            {
                "target": "depth",
                "method_B": METHOD_B,
                "method_C": METHOD_C,
                "n_aligned_simulations": len(detail),
                "B_improved_count": int((difference > tolerance).sum()),
                "C_improved_count": int((difference < -tolerance).sum()),
                "tie_count": int((np.abs(difference) <= tolerance).sum()),
                "observed_MAE_C_minus_B_um": mae_difference,
                "MAE_C_minus_B_ci95_low_um": float(mae_low),
                "MAE_C_minus_B_ci95_high_um": float(mae_high),
                "MAE_ci_includes_zero": bool(mae_low <= 0 <= mae_high),
                "observed_RMSE_C_minus_B_um": rmse_difference,
                "RMSE_C_minus_B_ci95_low_um": float(rmse_low),
                "RMSE_C_minus_B_ci95_high_um": float(rmse_high),
                "RMSE_ci_includes_zero": bool(rmse_low <= 0 <= rmse_high),
                "paired_bootstrap_resamples": PAIRED_BOOTSTRAP_RESAMPLES,
                "paired_bootstrap_seed": seed,
                "paired_resampling_unit": "stable simulation ID",
                "difference_sign_interpretation": (
                    "negative favors C; positive favors B"
                ),
                "superiority_rule": (
                    "superiority is not robust when the relevant CI includes zero"
                ),
            }
        ]
    )
    return detail, summary


def _distribution_summary(values: pd.Series, prefix: str) -> dict[str, float]:
    numeric = values.astype(float)
    return {
        f"{prefix}_min": float(numeric.min()),
        f"{prefix}_q25": float(numeric.quantile(0.25)),
        f"{prefix}_median": float(numeric.median()),
        f"{prefix}_q75": float(numeric.quantile(0.75)),
        f"{prefix}_q95": float(numeric.quantile(0.95)),
        f"{prefix}_max": float(numeric.max()),
    }


def build_method_summaries(
    predictions_b: pd.DataFrame,
    predictions_c: pd.DataFrame,
    stable_input: pd.DataFrame,
) -> dict[str, Any]:
    nugget = {
        **_distribution_summary(
            predictions_b["optimized_noise_variance_normalized"],
            "normalized_variance",
        ),
        **_distribution_summary(
            predictions_b["optimized_noise_std_um"], "std_um"
        ),
        **_distribution_summary(
            predictions_b["noise_std_fraction_training_target_std"],
            "fraction_training_target_std",
        ),
        "coefficient_of_variation_std_um": float(
            predictions_b["optimized_noise_std_um"].std(ddof=1)
            / predictions_b["optimized_noise_std_um"].mean()
        ),
        "noise_bound_hit_folds": int(
            predictions_b["noise_bound_hit"].astype(bool).sum()
        ),
        "interpretation": (
            "learned common effective discrepancy; it can absorb unresolved "
            "inputs and fixed-kernel/model mismatch and is not simulator noise"
        ),
    }
    heteroskedastic = {
        **_distribution_summary(
            stable_input[UNCERTAINTY_VARIANCE_COLUMN], "variance_um2"
        ),
        **_distribution_summary(
            stable_input[UNCERTAINTY_STD_COLUMN], "std_um"
        ),
        "zero_variance_count": int(
            stable_input[UNCERTAINTY_VARIANCE_COLUMN].eq(0).sum()
        ),
        "interpretation": (
            "existing moving-block-bootstrap variance of each selected-window "
            "median; not measurement or stochastic simulator noise"
        ),
    }
    return {
        "learned_B_effective_nugget": nugget,
        "C_target_summary_uncertainty": heteroskedastic,
    }


def _metric_snapshot(
    frame: pd.DataFrame, analysis_label: str
) -> dict[str, Any]:
    row = phase2.metric_row(frame, analysis_label=analysis_label)
    row.update(
        {
            "optimized_length_scale_median": float(
                frame["optimized_length_scale"].median()
            ),
            "optimized_signal_variance_median_normalized": float(
                frame["optimized_signal_variance_normalized"].median()
            ),
            "optimized_noise_variance_median_normalized": (
                float(frame["optimized_noise_variance_normalized"].median())
                if frame["optimized_noise_variance_normalized"].notna().any()
                else np.nan
            ),
            "training_alpha_normalized_median_across_folds": float(
                frame["training_alpha_normalized_median"].median()
            ),
        }
    )
    return row


def build_stable_vs_full_comparison(
    predictions_b: pd.DataFrame,
    predictions_c: pd.DataFrame,
    stable_input: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    existing = pd.read_csv(PHASE2_OUTPUT_DIR / "depth_loo_predictions.csv")
    expected_ids = stable_input["simulation_id"].astype(str).tolist()
    rows: list[dict[str, Any]] = []
    snapshots: dict[str, dict[str, Any]] = {}
    metric_names = [
        "mae_um",
        "rmse_um",
        "r2",
        "mean_nlpd",
        "latent_95_coverage",
        "observation_95_coverage",
        "optimized_length_scale_median",
        "optimized_signal_variance_median_normalized",
        "optimized_noise_variance_median_normalized",
        "training_alpha_normalized_median_across_folds",
    ]
    for method, refit in (
        (METHOD_B, predictions_b),
        (METHOD_C, predictions_c),
    ):
        full_stable = existing.loc[
            (existing["method"] == method)
            & existing["heldout_simulation_id"].astype(str).isin(expected_ids)
        ].copy()
        full_stable = full_stable.sort_values(
            "heldout_numeric_simulation_id"
        ).reset_index(drop=True)
        if full_stable["heldout_simulation_id"].astype(str).tolist() != expected_ids:
            raise RuntimeError(
                f"{method}: full-population stable held-out IDs/order differ"
            )
        refit_sorted = refit.sort_values("fold_index").reset_index(drop=True)
        if refit_sorted["simulation_id"].astype(str).tolist() != expected_ids:
            raise RuntimeError(f"{method}: refit stable IDs/order differ")

        full_metric = _metric_snapshot(
            full_stable, "full_population_model_stable_heldouts_230"
        )
        refit_metric = _metric_snapshot(
            refit_sorted, PHASE2_5_ANALYSIS_LABEL
        )
        snapshots[method] = {
            "full_population_model_stable_heldouts": full_metric,
            "stable_only_refit": refit_metric,
        }
        for metric_name in metric_names:
            before = float(full_metric[metric_name])
            after = float(refit_metric[metric_name])
            relative = (
                (after - before) / abs(before)
                if np.isfinite(before) and before != 0
                else np.nan
            )
            rows.append(
                {
                    "method": method,
                    "metric": metric_name,
                    "full_population_model_stable_heldouts": before,
                    "stable_only_refit": after,
                    "absolute_change": after - before,
                    "relative_change": relative,
                    "percent_change": relative * 100
                    if np.isfinite(relative)
                    else np.nan,
                    "rmse_materiality_threshold_absolute_relative": (
                        0.05 if metric_name == "rmse_um" else np.nan
                    ),
                    "rmse_change_is_material": (
                        bool(abs(relative) >= 0.05)
                        if metric_name == "rmse_um"
                        else np.nan
                    ),
                    "materiality_interpretation": (
                        "5% absolute relative RMSE change is descriptive only, "
                        "not a formal statistical test"
                        if metric_name == "rmse_um"
                        else ""
                    ),
                }
            )
    return pd.DataFrame(rows), snapshots


def build_hyperparameter_diagnostics(
    predictions_b: pd.DataFrame, predictions_c: pd.DataFrame
) -> pd.DataFrame:
    columns = [
        "phase2_5_analysis_label",
        "phase2_5_protocol_fingerprint",
        "simulation_id",
        "analysis_label",
        "target",
        "method",
        "fold_index",
        "fold_random_seed",
        "optimized_kernel",
        "optimized_constant_value_normalized",
        "optimized_length_scale",
        "optimized_signal_variance_normalized",
        "optimized_noise_variance_normalized",
        "optimized_noise_std_normalized",
        "optimized_noise_std_um",
        "noise_std_fraction_training_target_std",
        "training_alpha_normalized_min",
        "training_alpha_normalized_median",
        "training_alpha_normalized_max",
        "heldout_target_summary_variance_um2",
        "heldout_target_summary_std_um",
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
    ]
    return pd.concat(
        [predictions_b[columns], predictions_c[columns]], ignore_index=True
    ).sort_values(["method", "fold_index"])


def trace_phase2_runtime_metadata() -> dict[str, Any]:
    summary = json.loads(
        (PHASE2_OUTPUT_DIR / "summary.json").read_text(encoding="utf-8")
    )
    config = json.loads(
        (PHASE2_OUTPUT_DIR / "phase2_model_configuration.json").read_text(
            encoding="utf-8"
        )
    )
    original_value = float(summary["full_pipeline_runtime_seconds"])
    source_lines, source_start = inspect.getsourcelines(
        phase2.run_full_pipeline
    )
    source_text = "".join(source_lines)
    if (
        "started = time.perf_counter()" not in source_text
        or "full_runtime_seconds = time.perf_counter() - started"
        not in source_text
    ):
        raise RuntimeError("Could not trace the Phase 2 runtime timer")

    checkpoint_paths = sorted(
        (PHASE2_OUTPUT_DIR / "checkpoints").glob("*.csv")
    )
    latest_checkpoint = max(
        datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        for path in checkpoint_paths
    )
    config_created = datetime.fromisoformat(config["created_at_utc"])
    checkpoints_predate_cached_invocation = latest_checkpoint < config_created

    smoke = json.loads(
        (PHASE2_OUTPUT_DIR / "smoke_test_summary.json").read_text(
            encoding="utf-8"
        )
    )
    bootstrap_text = (
        PHASE2_OUTPUT_DIR / "bootstrap_run.stdout.log"
    ).read_text(encoding="utf-8")
    match = re.search(
        r'(\{\s*"status":\s*"bootstrap_only_complete".*?\})\s*$',
        bootstrap_text,
        flags=re.DOTALL,
    )
    bootstrap_payload = json.loads(match.group(1)) if match else {}
    metrics = pd.read_csv(PHASE2_OUTPUT_DIR / "all_model_metrics.csv")
    primary = metrics.loc[metrics["analysis_label"] == "full_population_loo"]
    stable = metrics.loc[metrics["analysis_label"] == "stable_only_refit_loo"]

    return {
        "original_field_name": "full_pipeline_runtime_seconds",
        "original_value_seconds": original_value,
        "status": "deprecated_ambiguous_name",
        "corrected_authoritative_field_name": (
            "cached_artifact_assembly_figure_and_validation_runtime_seconds"
        ),
        "corrected_authoritative_value_seconds": original_value,
        "classification": (
            "measured cached Phase 2 pre-report invocation, not the original "
            "end-to-end experiment"
        ),
        "timer_trace": {
            "function": "run_full_pipeline",
            "source_file": str(Path(phase2.__file__).relative_to(ROOT)),
            "function_start_line": source_start,
            "timer_start": (
                "at function entry before configuration, Phase 1 checks, and "
                "cache/checkpoint loading"
            ),
            "timer_end": (
                "after figure generation and validation, immediately before "
                "write_reporting_outputs"
            ),
            "included_stages": [
                "Phase 1 verification",
                "loading/re-writing cached target-summary uncertainty",
                "loading all 9 primary and 3 stable LOO checkpoints",
                "metric, paired, preference, and stable-sensitivity assembly",
                "figure generation",
                "automated validation",
            ],
            "excluded_stages": [
                "original moving-block bootstrap computation",
                "original 241-simulation GP fits",
                "original stable-only GP fits",
                "report/checklist/summary writes after the timer stop",
                "notebook execution",
            ],
        },
        "cache_evidence": {
            "phase2_configuration_created_at_utc": config["created_at_utc"],
            "latest_checkpoint_mtime_utc": latest_checkpoint.isoformat(),
            "all_checkpoints_predate_timed_invocation": (
                checkpoints_predate_cached_invocation
            ),
            "checkpoint_count": len(checkpoint_paths),
        },
        "available_separately_measured_phase2_durations": {
            "smoke_test_runtime_seconds": float(smoke["runtime_seconds"]),
            "target_summary_bootstrap_invocation_runtime_seconds": float(
                bootstrap_payload.get("runtime_seconds", np.nan)
            ),
            "full_241_loo_aggregate_fold_runtime_seconds": float(
                primary["total_runtime_seconds"].sum()
            ),
            "stable_only_aggregate_fold_runtime_seconds": float(
                stable["total_runtime_seconds"].sum()
            ),
            "aggregate_fold_runtime_warning": (
                "fold durations overlap under parallel execution and are not "
                "end-to-end wall-clock durations"
            ),
        },
        "not_available_as_measured_values": [
            "original full Phase 2 end-to-end wall-clock runtime",
            "original full 241-LOO wall-clock runtime",
            "original Phase 2 notebook execution runtime",
        ],
        "correction_policy": (
            "The historical value is preserved but deprecated. The corrected "
            "name above is authoritative; no guessed end-to-end sum is added."
        ),
    }


def build_runtime_provenance(
    *,
    workers: int,
    invocation_start_utc: str,
    invocation_end_utc: str,
    invocation_runtime_seconds: float,
    method_runtime_records: list[dict[str, Any]],
    artifact_generation_runtime_seconds: float,
) -> dict[str, Any]:
    existing = {}
    path = OUTPUT_DIR / "runtime_provenance.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
    phase2_5_existing = existing.get("phase2_5_measured_durations", {})
    return {
        "generated_at_utc": utc_now(),
        "phase2_runtime_metadata_correction": trace_phase2_runtime_metadata(),
        "phase2_5_measured_durations": {
            **phase2_5_existing,
            "latest_full_or_cached_invocation": {
                "timer_start_utc": invocation_start_utc,
                "timer_end_utc": invocation_end_utc,
                "measured_wall_runtime_seconds": invocation_runtime_seconds,
                "included_stages": [
                    "source validation",
                    "stable subset construction",
                    "B/C LOO fit or validated cache loading",
                    "metrics and paired bootstrap",
                    "stable-vs-full comparison",
                    "figures",
                    "initial validation and reports",
                ],
                "excluded_stages": [
                    "notebook build/execution",
                    "later final validation invocation",
                ],
                "cached_stages": [
                    record["method"]
                    for record in method_runtime_records
                    if record["cache_reused"]
                ],
                "parallel_worker_count": workers,
            },
            "method_loo_invocations": method_runtime_records,
            "artifact_generation_runtime_seconds": (
                artifact_generation_runtime_seconds
            ),
            "notebook_execution_runtime_seconds": phase2_5_existing.get(
                "notebook_execution_runtime_seconds"
            ),
            "last_validation_runtime_seconds": phase2_5_existing.get(
                "last_validation_runtime_seconds"
            ),
            "end_to_end_wall_clock_runtime_seconds": None,
            "end_to_end_note": (
                "No end-to-end value is reported because notebook execution "
                "and final validation occur in separate measured invocations."
            ),
        },
        "timing_principles": {
            "measured_only": True,
            "no_inferred_duration_reported_as_measured": True,
            "parallel_fold_sums_not_treated_as_wall_clock": True,
        },
    }


def record_runtime_value(field: str, seconds: float) -> dict[str, Any]:
    path = OUTPUT_DIR / "runtime_provenance.json"
    if not path.exists():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["generated_at_utc"] = utc_now()
    payload["phase2_5_measured_durations"][field] = float(seconds)
    write_json(payload, "runtime_provenance.json")
    return payload


METHOD_COLORS = {
    METHOD_B: "#2878B5",
    METHOD_C: "#D55E00",
}
METHOD_LABELS = {
    METHOD_B: "B: learned effective nugget",
    METHOD_C: "C: heteroskedastic alpha",
}


def _save_figure(fig: plt.Figure, filename: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_observed_vs_predicted(
    predictions_b: pd.DataFrame, predictions_c: pd.DataFrame
) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6), sharex=True, sharey=True)
    observed = predictions_b["observed_target_um"].to_numpy(float)
    low = min(
        observed.min(),
        predictions_b["predicted_mean_um"].min(),
        predictions_c["predicted_mean_um"].min(),
    )
    high = max(
        observed.max(),
        predictions_b["predicted_mean_um"].max(),
        predictions_c["predicted_mean_um"].max(),
    )
    padding = 0.04 * (high - low)
    for ax, (method, frame) in zip(
        axes, ((METHOD_B, predictions_b), (METHOD_C, predictions_c))
    ):
        ax.scatter(
            frame["observed_target_um"],
            frame["predicted_mean_um"],
            s=22,
            alpha=0.72,
            color=METHOD_COLORS[method],
            edgecolor="none",
        )
        ax.plot(
            [low - padding, high + padding],
            [low - padding, high + padding],
            color="black",
            linewidth=1,
            linestyle="--",
            label="ideal y = x",
        )
        ax.set_title(METHOD_LABELS[method])
        ax.set_xlabel("Observed stable depth (µm)")
        ax.grid(alpha=0.22)
        ax.legend(frameon=False)
    axes[0].set_ylabel("LOO-predicted depth (µm)")
    fig.suptitle("Stable-depth exact LOO: observed versus predicted")
    return _save_figure(fig, "stable_depth_observed_vs_loo_predicted.png")


def plot_absolute_error_comparison(detail: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    b = detail["B_absolute_error_um"].to_numpy(float)
    c = detail["C_absolute_error_um"].to_numpy(float)
    ax.scatter(b, c, s=25, alpha=0.7, color="#6A5ACD", edgecolor="none")
    high = max(b.max(), c.max())
    ax.plot([0, high], [0, high], color="black", linestyle="--", linewidth=1)
    ax.set_xlabel("B absolute error (µm)")
    ax.set_ylabel("C absolute error (µm)")
    ax.set_title(
        "Paired stable-depth absolute errors\n"
        "below the diagonal favors C; above favors B"
    )
    ax.grid(alpha=0.22)
    return _save_figure(fig, "stable_depth_paired_absolute_errors.png")


def plot_paired_bootstrap(summary: pd.DataFrame) -> Path:
    row = summary.iloc[0]
    estimates = [
        float(row["observed_MAE_C_minus_B_um"]),
        float(row["observed_RMSE_C_minus_B_um"]),
    ]
    lows = [
        float(row["MAE_C_minus_B_ci95_low_um"]),
        float(row["RMSE_C_minus_B_ci95_low_um"]),
    ]
    highs = [
        float(row["MAE_C_minus_B_ci95_high_um"]),
        float(row["RMSE_C_minus_B_ci95_high_um"]),
    ]
    fig, ax = plt.subplots(figsize=(7.8, 4.3))
    y = np.arange(2)
    ax.errorbar(
        estimates,
        y,
        xerr=[
            np.asarray(estimates) - np.asarray(lows),
            np.asarray(highs) - np.asarray(estimates),
        ],
        fmt="o",
        color="#4C4C4C",
        ecolor="#4C4C4C",
        capsize=6,
        markersize=7,
    )
    ax.axvline(0, color="black", linestyle="--", linewidth=1)
    ax.set_yticks(y, ["MAE C − B", "RMSE C − B"])
    ax.set_xlabel("Difference (µm); negative favors C, positive favors B")
    ax.set_title("10,000-resample paired-bootstrap 95% confidence intervals")
    ax.grid(axis="x", alpha=0.22)
    return _save_figure(fig, "stable_depth_paired_bootstrap_intervals.png")


def plot_calibration(
    predictions_b: pd.DataFrame, predictions_c: pd.DataFrame
) -> Path:
    fig, axes = plt.subplots(2, 1, figsize=(10.6, 7.6), sharex=True)
    for ax, (method, frame, lower, upper, label) in zip(
        axes,
        (
            (
                METHOD_B,
                predictions_b,
                "observation_interval_lower_um",
                "observation_interval_upper_um",
                "B total interval (includes effective nugget)",
            ),
            (
                METHOD_C,
                predictions_c,
                "oracle_interval_lower_um",
                "oracle_interval_upper_um",
                "C oracle retrospective interval (not deployable)",
            ),
        ),
    ):
        ordered = frame.sort_values("observed_target_um").reset_index(drop=True)
        x = np.arange(len(ordered))
        ax.fill_between(
            x,
            ordered[lower].to_numpy(float),
            ordered[upper].to_numpy(float),
            color=METHOD_COLORS[method],
            alpha=0.2,
            label="95% interval",
        )
        ax.plot(
            x,
            ordered["predicted_mean_um"],
            color=METHOD_COLORS[method],
            linewidth=1.2,
            label="predictive mean",
        )
        ax.scatter(
            x,
            ordered["observed_target_um"],
            color="black",
            s=9,
            alpha=0.68,
            label="observed",
        )
        ax.set_ylabel("Depth (µm)")
        ax.set_title(label)
        ax.grid(alpha=0.18)
        ax.legend(ncol=3, frameon=False, fontsize=8)
    axes[-1].set_xlabel("Stable held-outs sorted by observed depth")
    fig.suptitle("Stable-depth observation/oracle interval calibration")
    return _save_figure(fig, "stable_depth_predictive_interval_calibration.png")


def plot_stable_vs_full(comparison: pd.DataFrame) -> Path:
    selected = comparison.loc[
        comparison["metric"].isin(["mae_um", "rmse_um", "mean_nlpd"])
    ].copy()
    labels = ["MAE", "RMSE", "Mean NLPD"]
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.6))
    for ax, method in zip(axes, METHODS):
        rows = selected.loc[selected["method"] == method].set_index("metric")
        x = np.arange(3)
        width = 0.36
        ax.bar(
            x - width / 2,
            rows.loc[
                ["mae_um", "rmse_um", "mean_nlpd"],
                "full_population_model_stable_heldouts",
            ],
            width,
            label="Full-population trained",
            color="#9E9E9E",
        )
        ax.bar(
            x + width / 2,
            rows.loc[
                ["mae_um", "rmse_um", "mean_nlpd"], "stable_only_refit"
            ],
            width,
            label="Stable-only refit",
            color=METHOD_COLORS[method],
        )
        ax.set_xticks(x, labels)
        ax.set_title(METHOD_LABELS[method])
        ax.grid(axis="y", alpha=0.2)
        ax.legend(frameon=False, fontsize=8)
    fig.suptitle(
        "Same 230 stable held-outs: full-population training versus stable refit"
    )
    return _save_figure(fig, "stable_depth_stable_vs_full_training.png")


def plot_nugget_vs_target_uncertainty(
    predictions_b: pd.DataFrame, stable_input: pd.DataFrame
) -> Path:
    b_std = predictions_b["optimized_noise_std_um"].to_numpy(float)
    c_std = stable_input[UNCERTAINTY_STD_COLUMN].to_numpy(float)
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.4))
    axes[0].hist(b_std, bins=24, color=METHOD_COLORS[METHOD_B], alpha=0.78)
    axes[0].set_xlabel("Learned effective-nugget std (µm)")
    axes[0].set_ylabel("LOO folds")
    axes[0].set_title("B: common discrepancy learned per fold")
    axes[1].hist(
        c_std,
        bins=np.geomspace(max(c_std.min(), 1e-5), c_std.max(), 24),
        color=METHOD_COLORS[METHOD_C],
        alpha=0.78,
    )
    axes[1].set_xscale("log")
    axes[1].set_xlabel("Target-summary bootstrap std (µm, log scale)")
    axes[1].set_ylabel("Stable simulations")
    axes[1].set_title("C: observation-specific window stability")
    for ax in axes:
        ax.grid(alpha=0.18)
    fig.suptitle(
        "Different quantities: B effective nugget versus C target-summary proxy"
    )
    return _save_figure(
        fig, "stable_depth_nugget_vs_target_summary_uncertainty.png"
    )


def generate_figures(
    *,
    predictions_b: pd.DataFrame,
    predictions_c: pd.DataFrame,
    paired_detail: pd.DataFrame,
    paired_summary: pd.DataFrame,
    stable_vs_full: pd.DataFrame,
    stable_input: pd.DataFrame,
) -> list[Path]:
    return [
        plot_observed_vs_predicted(predictions_b, predictions_c),
        plot_absolute_error_comparison(paired_detail),
        plot_paired_bootstrap(paired_summary),
        plot_calibration(predictions_b, predictions_c),
        plot_stable_vs_full(stable_vs_full),
        plot_nugget_vs_target_uncertainty(predictions_b, stable_input),
    ]


def resolve_decision(
    metrics: pd.DataFrame,
    paired_summary: pd.DataFrame,
    stable_vs_full: pd.DataFrame,
) -> dict[str, Any]:
    b = metrics.loc[metrics["method"] == METHOD_B].iloc[0]
    c = metrics.loc[metrics["method"] == METHOD_C].iloc[0]
    pair = paired_summary.iloc[0]
    mae_low = float(pair["MAE_C_minus_B_ci95_low_um"])
    mae_high = float(pair["MAE_C_minus_B_ci95_high_um"])
    rmse_low = float(pair["RMSE_C_minus_B_ci95_low_um"])
    rmse_high = float(pair["RMSE_C_minus_B_ci95_high_um"])
    both_robust_c = mae_high < 0 and rmse_high < 0
    both_robust_b = mae_low > 0 and rmse_low > 0
    any_interval_zero = bool(
        pair["MAE_ci_includes_zero"] or pair["RMSE_ci_includes_zero"]
    )

    b_coverage_distance = abs(float(b["observation_95_coverage"]) - 0.95)
    c_coverage_distance = abs(float(c["observation_95_coverage"]) - 0.95)
    b_nlpd_better = float(b["mean_nlpd"]) < float(c["mean_nlpd"])
    b_calibration_better = b_coverage_distance < c_coverage_distance
    if both_robust_c:
        code = "C_preferred_for_depth"
        headline = "C is preferred for stable-window penetration depth."
    elif both_robust_b:
        code = "B_preferred_for_depth"
        headline = "B is preferred for stable-window penetration depth."
    elif any_interval_zero and b_nlpd_better and b_calibration_better:
        code = "B_operational_default_C_sensitivity"
        headline = (
            "No robust point-prediction winner exists; use B as the "
            "operational default and retain C as a depth-specific sensitivity model."
        )
    else:
        code = "no_robust_depth_winner"
        headline = "No robust depth winner exists between B and C."

    rmse_rows = stable_vs_full.loc[stable_vs_full["metric"] == "rmse_um"]
    materiality = {
        str(row.method): bool(row.rmse_change_is_material)
        for row in rmse_rows.itertuples()
    }
    return {
        "decision_code": code,
        "headline": headline,
        "paired_MAE_C_minus_B_ci95_um": [mae_low, mae_high],
        "paired_RMSE_C_minus_B_ci95_um": [rmse_low, rmse_high],
        "paired_superiority_is_robust": bool(
            both_robust_b or both_robust_c
        ),
        "B_mean_nlpd_is_lower": b_nlpd_better,
        "B_observation_coverage_is_closer_to_95_percent": (
            b_calibration_better
        ),
        "B_observation_interval_is_deployable_for_new_inputs": True,
        "C_oracle_interval_is_deployable_for_new_inputs": False,
        "unstable_training_rows_materially_change_RMSE_by_method": materiality,
        "evidence_order": [
            "paired point prediction",
            "calibration and NLPD",
            "robustness to removing unstable simulations",
            "optimizer and hyperparameter stability",
            "deployability and scientific interpretation",
            "runtime",
        ],
        "scientific_limit": (
            "This matched comparison resolves only the observation treatment "
            "for depth under the fixed Matérn 3/2 model. It does not establish "
            "causal feature effects or validate C's oracle interval for unseen runs."
        ),
    }


def _bool_values(series: pd.Series) -> np.ndarray:
    if pd.api.types.is_bool_dtype(series):
        return series.to_numpy(bool)
    return series.astype(str).str.lower().eq("true").to_numpy(bool)


def _notebook_clean() -> tuple[bool, str]:
    if not NOTEBOOK_PATH.exists():
        return False, "notebook missing"
    try:
        payload = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"notebook unreadable: {exc}"
    code_cells = [cell for cell in payload.get("cells", []) if cell["cell_type"] == "code"]
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


def _fold_scalers_are_correct(
    predictions: list[pd.DataFrame], stable_input: pd.DataFrame
) -> tuple[bool, bool, bool, str]:
    X = stable_input[FEATURE_COLUMNS].to_numpy(float)
    y = stable_input[TARGET_UM_COLUMN].to_numpy(float)
    x_ok = True
    y_ok = True
    leakage_ok = True
    checked = 0
    for frame in predictions:
        for row in frame.sort_values("fold_index").itertuples():
            fold_index = int(row.fold_index)
            mask = np.ones(len(stable_input), dtype=bool)
            mask[fold_index] = False
            expected_x_mean = X[mask].mean(axis=0)
            expected_x_scale = X[mask].std(axis=0, ddof=0)
            expected_y_mean = float(y[mask].mean())
            expected_y_std = float(y[mask].std(ddof=0))
            recorded_x_mean = np.asarray(
                json.loads(row.x_training_mean), dtype=float
            )
            recorded_x_scale = np.asarray(
                json.loads(row.x_training_scale), dtype=float
            )
            x_ok &= bool(
                np.allclose(recorded_x_mean, expected_x_mean, rtol=1e-12, atol=1e-12)
                and np.allclose(
                    recorded_x_scale, expected_x_scale, rtol=1e-12, atol=1e-12
                )
                and json.loads(row.feature_columns) == FEATURE_COLUMNS
            )
            y_ok &= bool(
                math.isclose(
                    float(row.training_y_mean_um),
                    expected_y_mean,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
                and math.isclose(
                    float(row.training_y_std_um),
                    expected_y_std,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
            )
            leakage_ok &= bool(
                row.heldout_excluded_from_training
                and row.x_scaler_fit_on_training_only
                and row.y_scaler_fit_on_training_only
                and int(row.training_size) == 229
                and int(row.population_size) == 230
                and str(row.normalize_y).lower() == "false"
            )
            checked += 1
    return x_ok, y_ok, leakage_ok, f"independently recomputed {checked} folds"


def _metrics_match(
    metrics: pd.DataFrame,
    predictions_b: pd.DataFrame,
    predictions_c: pd.DataFrame,
) -> tuple[bool, str]:
    numeric = [
        "mae_um",
        "median_absolute_error_um",
        "rmse_um",
        "r2",
        "nrmse",
        "mean_nlpd",
        "median_nlpd",
        "latent_95_coverage",
        "observation_95_coverage",
        "mean_latent_interval_width_um",
        "mean_observation_interval_width_um",
    ]
    for method, frame in ((METHOD_B, predictions_b), (METHOD_C, predictions_c)):
        expected = phase2.metric_row(
            frame, analysis_label=PHASE2_5_ANALYSIS_LABEL
        )
        actual = metrics.loc[metrics["method"] == method].iloc[0]
        for column in numeric:
            a = float(actual[column])
            e = float(expected[column])
            if not (
                (np.isnan(a) and np.isnan(e))
                or math.isclose(a, e, rel_tol=1e-10, abs_tol=1e-10)
            ):
                return False, f"{method}/{column}: {a} != {e}"
    return True, "both metric rows independently recomputed"


def _phase2_summary_has_runtime_addendum() -> tuple[bool, str]:
    payload = json.loads(
        (PHASE2_OUTPUT_DIR / "summary.json").read_text(encoding="utf-8")
    )
    addendum = payload.get("phase2_5_runtime_metadata_addendum", {})
    ok = bool(
        addendum.get("historical_full_pipeline_runtime_field_preserved")
        and addendum.get("historical_field_status")
        == "deprecated_ambiguous_name"
        and addendum.get("corrected_authoritative_field_name")
        == "cached_artifact_assembly_figure_and_validation_runtime_seconds"
    )
    return ok, (
        f"historical_value={payload.get('full_pipeline_runtime_seconds')}; "
        f"corrected_name={addendum.get('corrected_authoritative_field_name')}"
    )


def build_validations(
    *,
    phase1: pd.DataFrame,
    stable_input: pd.DataFrame,
    predictions_b: pd.DataFrame,
    predictions_c: pd.DataFrame,
    metrics: pd.DataFrame,
    paired_detail: pd.DataFrame,
    paired_summary: pd.DataFrame,
    stable_vs_full: pd.DataFrame,
    runtime_provenance: dict[str, Any],
) -> pd.DataFrame:
    expected_ids = stable_input["simulation_id"].astype(str).tolist()
    ids_b = predictions_b["simulation_id"].astype(str).tolist()
    ids_c = predictions_c["simulation_id"].astype(str).tolist()
    fold_b = predictions_b["fold_index"].astype(int).tolist()
    fold_c = predictions_c["fold_index"].astype(int).tolist()
    removed = set(phase1["simulation_id"].astype(str)) - set(expected_ids)
    x_ok, y_ok, leakage_ok, scaler_detail = _fold_scalers_are_correct(
        [predictions_b, predictions_c], stable_input
    )

    b_total_expected = (
        predictions_b["latent_predictive_variance_um2"].to_numpy(float)
        + predictions_b[
            "optimized_noise_variance_normalized"
        ].to_numpy(float)
        * predictions_b["training_y_std_um"].to_numpy(float) ** 2
    )
    b_total_ok = bool(
        np.allclose(
            b_total_expected,
            predictions_b["total_predictive_variance_um2"].to_numpy(float),
            rtol=1e-9,
            atol=1e-9,
        )
    )
    c_oracle_expected = (
        predictions_c["latent_predictive_variance_um2"].to_numpy(float)
        + predictions_c[
            "heldout_target_summary_variance_um2"
        ].to_numpy(float)
    )
    c_oracle_ok = bool(
        np.allclose(
            c_oracle_expected,
            predictions_c[
                "oracle_total_predictive_variance_um2"
            ].to_numpy(float),
            rtol=1e-9,
            atol=1e-9,
        )
    )
    metrics_ok, metrics_detail = _metrics_match(
        metrics, predictions_b, predictions_c
    )

    seed = int(paired_summary.iloc[0]["paired_bootstrap_seed"])
    mae_boot, rmse_boot = phase2._paired_bootstrap_differences(
        paired_detail["B_residual_um"].to_numpy(float),
        paired_detail["C_residual_um"].to_numpy(float),
        seed=seed,
        resamples=PAIRED_BOOTSTRAP_RESAMPLES,
    )
    q_mae = np.quantile(mae_boot, phase2.BOOTSTRAP_QUANTILES)
    q_rmse = np.quantile(rmse_boot, phase2.BOOTSTRAP_QUANTILES)
    paired_bootstrap_ok = bool(
        np.allclose(
            q_mae,
            paired_summary.iloc[0][
                ["MAE_C_minus_B_ci95_low_um", "MAE_C_minus_B_ci95_high_um"]
            ].to_numpy(float),
            rtol=1e-12,
            atol=1e-12,
        )
        and np.allclose(
            q_rmse,
            paired_summary.iloc[0][
                [
                    "RMSE_C_minus_B_ci95_low_um",
                    "RMSE_C_minus_B_ci95_high_um",
                ]
            ].to_numpy(float),
            rtol=1e-12,
            atol=1e-12,
        )
    )

    existing = pd.read_csv(PHASE2_OUTPUT_DIR / "depth_loo_predictions.csv")
    full_id_ok = True
    for method in METHODS:
        ids = (
            existing.loc[
                (existing["method"] == method)
                & existing["heldout_simulation_id"].astype(str).isin(expected_ids)
            ]
            .sort_values("heldout_numeric_simulation_id")[
                "heldout_simulation_id"
            ]
            .astype(str)
            .tolist()
        )
        full_id_ok &= ids == expected_ids

    aggregate, protected_count = phase2.phase1_aggregate_sha256()
    phase2_hashes_ok = all(
        sha256(PHASE2_OUTPUT_DIR / filename) == expected
        for filename, expected in PHASE2_SOURCE_HASHES.items()
    )
    original_ok, original_detail = phase2._original_worktree_unchanged()
    notebook_ok, notebook_detail = _notebook_clean()
    git_diff = subprocess.run(
        ["git", "diff", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    runtime_correction = runtime_provenance[
        "phase2_runtime_metadata_correction"
    ]
    runtime_addendum_ok, runtime_addendum_detail = (
        _phase2_summary_has_runtime_addendum()
    )
    runtime_ok = bool(
        runtime_correction["status"] == "deprecated_ambiguous_name"
        and runtime_correction[
            "corrected_authoritative_field_name"
        ]
        == "cached_artifact_assembly_figure_and_validation_runtime_seconds"
        and runtime_correction["cache_evidence"][
            "all_checkpoints_predate_timed_invocation"
        ]
        and runtime_provenance["timing_principles"]["measured_only"]
        and runtime_addendum_ok
    )

    warning_count = int(
        predictions_b["warning_count"].astype(int).gt(0).sum()
        + predictions_c["warning_count"].astype(int).gt(0).sum()
    )
    failed_count = int(
        _bool_values(predictions_b["failed_fold"]).sum()
        + _bool_values(predictions_c["failed_fold"]).sum()
    )
    bound_count = int(
        _bool_values(predictions_b["any_hyperparameter_bound_hit"]).sum()
        + _bool_values(predictions_c["any_hyperparameter_bound_hit"]).sum()
    )

    checks: list[tuple[str, bool, str]] = [
        (
            "exact Phase 1 provenance",
            set(phase1["huggingface_revision"].astype(str))
            == {PHASE1_REVISION},
            f"revision={PHASE1_REVISION}",
        ),
        (
            "unchanged Phase 1 ledger hash",
            sha256(PHASE1_INPUT) == PHASE1_LEDGER_SHA256,
            f"sha256={sha256(PHASE1_INPUT)}",
        ),
        (
            "exactly 230 stable simulations",
            len(stable_input) == 230
            and stable_input["simulation_id"].is_unique,
            f"rows={len(stable_input)}, unique={stable_input['simulation_id'].nunique()}",
        ),
        (
            "exactly the expected 11 removed simulation IDs",
            removed == set(UNSTABLE_SIMULATIONS),
            json.dumps(sorted(removed), separators=(",", ":")),
        ),
        (
            "features exactly P, VX, LS, ST",
            FEATURE_COLUMNS == phase2.FEATURE_COLUMNS,
            json.dumps(FEATURE_COLUMNS, separators=(",", ":")),
        ),
        (
            "target exactly penetration depth",
            phase2.TARGET_COLUMNS["depth"] == TARGET_SOURCE_COLUMN,
            TARGET_SOURCE_COLUMN,
        ),
        (
            "B and C use identical stable simulation IDs",
            ids_b == ids_c == expected_ids,
            f"aligned IDs={len(ids_b)}",
        ),
        (
            "B and C use identical fold order",
            fold_b == fold_c == list(range(230))
            and predictions_b["fold_random_seed"].astype(int).tolist()
            == predictions_c["fold_random_seed"].astype(int).tolist(),
            "fold indices 0..229 and fold seeds are identical",
        ),
        (
            "exactly 230 B predictions",
            len(predictions_b) == 230,
            f"rows={len(predictions_b)}",
        ),
        (
            "exactly 230 C predictions",
            len(predictions_c) == 230,
            f"rows={len(predictions_c)}",
        ),
        (
            "no duplicate held-out predictions",
            predictions_b["simulation_id"].is_unique
            and predictions_c["simulation_id"].is_unique,
            "unique simulation ID within both methods",
        ),
        ("fold-local X scaling", x_ok, scaler_detail),
        ("fold-local y scaling", y_ok, scaler_detail),
        (
            "no held-out-target leakage",
            leakage_ok,
            "training-only flags and independently recomputed scalers agree",
        ),
        (
            "finite predictive means",
            np.isfinite(predictions_b["predicted_mean_um"]).all()
            and np.isfinite(predictions_c["predicted_mean_um"]).all(),
            "460 predictive means checked",
        ),
        (
            "finite positive predictive standard deviations",
            (predictions_b["latent_predictive_std_um"].to_numpy(float) > 0).all()
            and (predictions_b["total_predictive_std_um"].to_numpy(float) > 0).all()
            and (predictions_c["latent_predictive_std_um"].to_numpy(float) > 0).all()
            and (
                predictions_c["oracle_total_predictive_std_um"].to_numpy(float)
                > 0
            ).all(),
            "latent plus B total and C oracle standard deviations checked",
        ),
        (
            "correct B total-variance calculation",
            b_total_ok,
            "total = latent + WhiteKernel variance in physical units",
        ),
        (
            "correct C oracle-variance calculation",
            c_oracle_ok,
            "oracle = latent + held-out target-summary variance",
        ),
        (
            "metrics independently recomputed from prediction rows",
            metrics_ok,
            metrics_detail,
        ),
        (
            "paired comparisons aligned by simulation ID",
            paired_detail["simulation_id"].astype(str).tolist() == expected_ids,
            f"paired rows={len(paired_detail)}",
        ),
        (
            "paired bootstrap uses paired resampling",
            paired_bootstrap_ok
            and paired_summary.iloc[0]["paired_resampling_unit"]
            == "stable simulation ID",
            "CIs independently reproduced from jointly indexed residual arrays",
        ),
        (
            "optimizer failures and warnings recorded",
            {"warning_count", "failed_fold", "convergence_status"}.issubset(
                predictions_b.columns
            )
            and {"warning_count", "failed_fold", "convergence_status"}.issubset(
                predictions_c.columns
            ),
            f"warning folds={warning_count}; failed folds={failed_count}",
        ),
        (
            "bound hits recorded",
            {
                "constant_bound_hit",
                "length_scale_bound_hit",
                "noise_bound_hit",
                "any_hyperparameter_bound_hit",
            }.issubset(predictions_b.columns)
            and {
                "constant_bound_hit",
                "length_scale_bound_hit",
                "noise_bound_hit",
                "any_hyperparameter_bound_hit",
            }.issubset(predictions_c.columns),
            f"bound-hit folds={bound_count}",
        ),
        (
            "stable-only versus full-population comparisons use identical held-out IDs",
            full_id_ok and len(stable_vs_full) == 20,
            "230 identical stable held-outs for B and C",
        ),
        (
            "Phase 1 outputs unchanged",
            aggregate == PHASE1_AGGREGATE_SHA256,
            f"protected_files={protected_count}; aggregate_sha256={aggregate}",
        ),
        (
            "existing Phase 2 prediction files unchanged",
            phase2_hashes_ok,
            json.dumps(PHASE2_SOURCE_HASHES, separators=(",", ":")),
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
            git_diff.returncode == 0,
            (git_diff.stdout + git_diff.stderr).strip() or "no whitespace errors",
        ),
        (
            "runtime metadata corrected or accurately renamed with provenance",
            runtime_ok,
            runtime_addendum_detail,
        ),
    ]
    return pd.DataFrame(
        [
            {
                "validation_number": index,
                "validation_check": name,
                "status": "PASS" if passed else "FAIL",
                "passed": bool(passed),
                "details": detail,
            }
            for index, (name, passed, detail) in enumerate(checks, start=1)
        ]
    )


def build_requirement_checklist(validation: pd.DataFrame) -> pd.DataFrame:
    validation_status = (
        "PASS" if validation["status"].eq("PASS").all() else "INCOMPLETE"
    )
    rows = [
        ("Phase 1/2 source provenance and hashes", "§2", "phase2_5_configuration.json"),
        ("Exact 230 stable subset", "§3", "stable_depth_input_table.csv"),
        ("Matched B/C mathematical definitions", "§4", "phase2_5_configuration.json"),
        ("Identical exact LOO protocol", "§5–6", "stable_depth_B_loo_predictions.csv"),
        ("230 Method B predictions", "§6", "stable_depth_B_loo_predictions.csv"),
        ("230 Method C predictions", "§6", "stable_depth_C_loo_predictions.csv"),
        ("Point-prediction metrics", "§7", "stable_depth_model_metrics.csv"),
        ("Uncertainty metrics and calibration", "§8", "stable_depth_model_metrics.csv"),
        ("Per-simulation paired errors", "§9", "stable_depth_paired_comparison.csv"),
        ("10,000 paired-bootstrap resamples", "§9", "stable_depth_paired_bootstrap_summary.csv"),
        ("Stable-refit versus full-trained comparison", "§10", "stable_vs_full_population_comparison.csv"),
        ("Learned B effective nugget", "§11", "stable_depth_hyperparameter_diagnostics.csv"),
        ("C heteroskedastic uncertainty", "§11", "stable_depth_input_table.csv"),
        ("Warnings, failures, and bound hits", "§12", "stable_depth_hyperparameter_diagnostics.csv"),
        ("Depth decision", "§13/§16", "depth_model_decision.md"),
        ("Runtime metadata correction", "§14", "runtime_metadata_correction.md"),
        ("Machine-readable runtime provenance", "§14", "runtime_provenance.json"),
        ("Thirty automated validations", "§15", "validation_results.csv"),
        ("Focused six-figure audit", "§7–12", "stable_depth_observed_vs_loo_predicted.png"),
        ("Phase 2.5 scientific summary", "§16", "results_summary.md"),
        ("Strictly no Phase 3 work", "§1/§16", "phase2_5_requirement_checklist.csv"),
    ]
    return pd.DataFrame(
        [
            {
                "phase2_5_requirement": requirement,
                "notebook_section": section,
                "output_file": output,
                "validation_status": validation_status,
            }
            for requirement, section, output in rows
        ]
    )


def _metric_value(metrics: pd.DataFrame, method: str, column: str) -> float:
    return float(metrics.loc[metrics["method"] == method, column].iloc[0])


def build_depth_decision_markdown(
    *,
    metrics: pd.DataFrame,
    paired_summary: pd.DataFrame,
    stable_vs_full: pd.DataFrame,
    method_summaries: dict[str, Any],
    decision: dict[str, Any],
) -> str:
    pair = paired_summary.iloc[0]
    rmse_comparison = stable_vs_full.loc[
        stable_vs_full["metric"] == "rmse_um"
    ]
    rmse_lines = "\n".join(
        (
            f"- `{row.method}`: full-population trained on the same stable "
            f"held-outs `{row.full_population_model_stable_heldouts:.6f} µm`; "
            f"stable-only refit `{row.stable_only_refit:.6f} µm`; "
            f"change `{row.percent_change:+.3f}%`; descriptive materiality "
            f"`{bool(row.rmse_change_is_material)}`."
        )
        for row in rmse_comparison.itertuples()
    )
    nugget = method_summaries["learned_B_effective_nugget"]
    alpha = method_summaries["C_target_summary_uncertainty"]
    return f"""# Week 6 Phase 2.5 depth-model decision

## Why the closure was required

Phase 2 compared depth Methods B and C on all 241 simulations, but only C was
rerun after removing the 11 unstable-window simulations. Phase 2.5 closes that
single fairness gap. Width and length were not reopened because their learned-
nugget preference was already robust and the requested ambiguity concerns only
depth.

## Matched protocol

Both methods used the same 230 stable simulation IDs, ascending fold order, 229
training rows per exact LOO fold, training-only X/y scaling, the same Phase 2
fold seed, the same isotropic Matérn 3/2 kernel bounds, L-BFGS-B, and one
deterministic restart. Only the observation treatment differs.

- **B** learns one common WhiteKernel effective nugget per fold. It is a model-
  discrepancy term and not stochastic simulator noise.
- **C** uses existing simulation-specific moving-block-bootstrap variances of
  the selected-window median. They are target-summary uncertainty proxies and
  not measurement noise.

## Stable-only metrics

| Method | MAE µm | Median AE µm | RMSE µm | R² | nRMSE | Mean NLPD | Latent cov. | Total/oracle cov. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B | {_metric_value(metrics, METHOD_B, 'mae_um'):.6f} | {_metric_value(metrics, METHOD_B, 'median_absolute_error_um'):.6f} | {_metric_value(metrics, METHOD_B, 'rmse_um'):.6f} | {_metric_value(metrics, METHOD_B, 'r2'):.6f} | {_metric_value(metrics, METHOD_B, 'nrmse'):.6f} | {_metric_value(metrics, METHOD_B, 'mean_nlpd'):.6f} | {_metric_value(metrics, METHOD_B, 'latent_95_coverage'):.4f} | {_metric_value(metrics, METHOD_B, 'observation_95_coverage'):.4f} |
| C | {_metric_value(metrics, METHOD_C, 'mae_um'):.6f} | {_metric_value(metrics, METHOD_C, 'median_absolute_error_um'):.6f} | {_metric_value(metrics, METHOD_C, 'rmse_um'):.6f} | {_metric_value(metrics, METHOD_C, 'r2'):.6f} | {_metric_value(metrics, METHOD_C, 'nrmse'):.6f} | {_metric_value(metrics, METHOD_C, 'mean_nlpd'):.6f} | {_metric_value(metrics, METHOD_C, 'latent_95_coverage'):.4f} | {_metric_value(metrics, METHOD_C, 'observation_95_coverage'):.4f} |

B's NLPD/observation coverage use total variance including the learned nugget.
C's corresponding values use the held-out simulation's retrospective oracle
variance. The C oracle interval is not available for a genuinely unseen
simulation and is therefore not a deployable uncertainty interval.

## Paired result

- B improved `{int(pair['B_improved_count'])}` simulations; C improved
  `{int(pair['C_improved_count'])}`; ties `{int(pair['tie_count'])}`.
- `MAE_C − MAE_B = {float(pair['observed_MAE_C_minus_B_um']):+.6f} µm`,
  paired-bootstrap 95% CI
  `[{float(pair['MAE_C_minus_B_ci95_low_um']):+.6f},
  {float(pair['MAE_C_minus_B_ci95_high_um']):+.6f}]`.
- `RMSE_C − RMSE_B = {float(pair['observed_RMSE_C_minus_B_um']):+.6f} µm`,
  paired-bootstrap 95% CI
  `[{float(pair['RMSE_C_minus_B_ci95_low_um']):+.6f},
  {float(pair['RMSE_C_minus_B_ci95_high_um']):+.6f}]`.

Negative differences favor C and positive differences favor B. A confidence
interval crossing zero does not support a robust superiority claim.

## Influence of unstable training simulations

{rmse_lines}

The 5% rule is a descriptive threshold, not a statistical test.

## Observation-treatment scale

- B median learned effective-nugget standard deviation:
  `{nugget['std_um_median']:.6f} µm`; median fraction of fold training-target
  standard deviation:
  `{nugget['fraction_training_target_std_median']:.6f}`.
- C median stable target-summary bootstrap standard deviation:
  `{alpha['std_um_median']:.6f} µm`; q95 `{alpha['std_um_q95']:.6f} µm`;
  maximum `{alpha['std_um_max']:.6f} µm`.

These scales are not interchangeable: B can absorb unresolved variables and
fixed-kernel discrepancy, whereas C measures within-window median stability.

## Decision

**{decision['headline']}**

The paired point-prediction evidence is considered first. Calibration/NLPD,
training-set sensitivity, optimizer behavior, deployability, interpretation,
and runtime are secondary evidence. This decision does not prove causal input
effects and does not validate C's oracle interval for unseen simulations.
"""


def build_runtime_correction_markdown(
    runtime_provenance: dict[str, Any]
) -> str:
    correction = runtime_provenance["phase2_runtime_metadata_correction"]
    available = correction["available_separately_measured_phase2_durations"]
    return f"""# Phase 2 runtime metadata correction

## Finding

The Phase 2 field `full_pipeline_runtime_seconds` contains
`{correction['original_value_seconds']:.12f}` seconds. The timer itself is real,
but the field name is too broad.

The value was created inside `run_full_pipeline`: the timer starts at function
entry and stops after figures and validation, immediately before reporting
files are written. File timestamps show that all
`{correction['cache_evidence']['checkpoint_count']}` GP checkpoints predate the
configuration timestamp for the timed invocation. Therefore the 11.2-second
invocation loaded cached bootstrap and LOO artifacts; it did not perform the
original expensive bootstrap or GP fits.

## Corrected name

The authoritative name is:

`{correction['corrected_authoritative_field_name']}`

The historical JSON value is preserved and marked deprecated rather than
replaced with a guessed end-to-end duration.

## Included

- Phase 1 verification
- cached uncertainty and checkpoint loading
- metric, paired, preference, and stable-sensitivity assembly
- figure generation
- validation

## Excluded

- original moving-block bootstrap
- original 241-simulation GP fits
- original stable-only GP fits
- reporting writes after the timer stop
- notebook execution

## Separately measured evidence

- Phase 2 smoke test:
  `{available['smoke_test_runtime_seconds']:.6f}` seconds.
- Target-summary bootstrap invocation:
  `{available['target_summary_bootstrap_invocation_runtime_seconds']:.6f}`
  seconds.
- Primary 241-LOO aggregate fold durations:
  `{available['full_241_loo_aggregate_fold_runtime_seconds']:.6f}` seconds.
- Stable-only aggregate fold durations:
  `{available['stable_only_aggregate_fold_runtime_seconds']:.6f}` seconds.

The fold-duration sums overlap because four workers ran folds concurrently.
They are measured diagnostic totals, not end-to-end wall-clock durations.
No unavailable duration is inferred or reported as measured.
"""


def build_results_summary_markdown(
    *,
    stable_input: pd.DataFrame,
    metrics: pd.DataFrame,
    paired_summary: pd.DataFrame,
    stable_vs_full: pd.DataFrame,
    method_summaries: dict[str, Any],
    decision: dict[str, Any],
    validation: pd.DataFrame,
) -> str:
    pair = paired_summary.iloc[0]
    nugget = method_summaries["learned_B_effective_nugget"]
    alpha = method_summaries["C_target_summary_uncertainty"]
    rmse_rows = stable_vs_full.loc[
        stable_vs_full["metric"] == "rmse_um"
    ].set_index("method")
    return f"""# Week 6 Phase 2.5 stable-depth closure

## Scope

Exactly `{len(stable_input)}` Phase 1 stable-window simulations were used after
removing the independently verified 11 flagged IDs. Features remained exactly
`[P, VX, LS, ST]`; the target remained the Phase 1 penetration depth converted
from metres to micrometres. No width/length model, Method A, kernel family,
target definition, feature-effect analysis, active learning, or level-set
estimation was introduced.

## Stable-only exact LOO

| Method | MAE µm | RMSE µm | R² | Mean NLPD | Latent coverage | Total/oracle coverage |
|---|---:|---:|---:|---:|---:|---:|
| B learned nugget | {_metric_value(metrics, METHOD_B, 'mae_um'):.6f} | {_metric_value(metrics, METHOD_B, 'rmse_um'):.6f} | {_metric_value(metrics, METHOD_B, 'r2'):.6f} | {_metric_value(metrics, METHOD_B, 'mean_nlpd'):.6f} | {_metric_value(metrics, METHOD_B, 'latent_95_coverage'):.4f} | {_metric_value(metrics, METHOD_B, 'observation_95_coverage'):.4f} |
| C heteroskedastic alpha | {_metric_value(metrics, METHOD_C, 'mae_um'):.6f} | {_metric_value(metrics, METHOD_C, 'rmse_um'):.6f} | {_metric_value(metrics, METHOD_C, 'r2'):.6f} | {_metric_value(metrics, METHOD_C, 'mean_nlpd'):.6f} | {_metric_value(metrics, METHOD_C, 'latent_95_coverage'):.4f} | {_metric_value(metrics, METHOD_C, 'observation_95_coverage'):.4f} |

## Paired B-versus-C evidence

- B/C improved counts:
  `{int(pair['B_improved_count'])}` / `{int(pair['C_improved_count'])}`;
  ties `{int(pair['tie_count'])}`.
- `MAE_C − MAE_B`:
  `{float(pair['observed_MAE_C_minus_B_um']):+.6f} µm`,
  95% CI `[{float(pair['MAE_C_minus_B_ci95_low_um']):+.6f},
  {float(pair['MAE_C_minus_B_ci95_high_um']):+.6f}]`.
- `RMSE_C − RMSE_B`:
  `{float(pair['observed_RMSE_C_minus_B_um']):+.6f} µm`,
  95% CI `[{float(pair['RMSE_C_minus_B_ci95_low_um']):+.6f},
  {float(pair['RMSE_C_minus_B_ci95_high_um']):+.6f}]`.

## Training-set sensitivity

- B RMSE full-trained/stable-held-outs → stable-only:
  `{float(rmse_rows.loc[METHOD_B, 'full_population_model_stable_heldouts']):.6f}`
  → `{float(rmse_rows.loc[METHOD_B, 'stable_only_refit']):.6f} µm`
  (`{float(rmse_rows.loc[METHOD_B, 'percent_change']):+.3f}%`).
- C RMSE full-trained/stable-held-outs → stable-only:
  `{float(rmse_rows.loc[METHOD_C, 'full_population_model_stable_heldouts']):.6f}`
  → `{float(rmse_rows.loc[METHOD_C, 'stable_only_refit']):.6f} µm`
  (`{float(rmse_rows.loc[METHOD_C, 'percent_change']):+.3f}%`).

The 5% threshold is descriptive only.

## Observation scales and interpretation

B's median effective-nugget standard deviation is
`{nugget['std_um_median']:.6f} µm`. C's median/q95/max target-summary
uncertainty standard deviations are `{alpha['std_um_median']:.6f}`,
`{alpha['std_um_q95']:.6f}`, and `{alpha['std_um_max']:.6f} µm`.
B is an effective discrepancy model; C is a within-window stability proxy.
Neither is evidence of stochastic simulator noise. C's oracle interval is
retrospective and not deployable for an unseen simulation.

## Decision

**{decision['headline']}**

This conclusion is limited to stable-window penetration depth under the fixed
isotropic Matérn 3/2 protocol.

## Runtime correction and validation

The historical Phase 2 `11.2`-second field was a cached pre-report invocation,
not the original end-to-end experiment. It is deprecated and accurately renamed
in `runtime_provenance.json`; no guessed runtime was substituted.

Automated validation: `{validation['status'].eq('PASS').sum()}/{len(validation)}`
PASS.
"""


def update_phase2_addenda(
    *,
    runtime_provenance: dict[str, Any],
    decision: dict[str, Any],
    paired_summary: pd.DataFrame,
) -> None:
    """Add a labelled addendum without rewriting historical Phase 2 results."""

    correction = runtime_provenance["phase2_runtime_metadata_correction"]
    summary_path = PHASE2_OUTPUT_DIR / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["phase2_5_runtime_metadata_addendum"] = {
        "added_at_utc": utc_now(),
        "historical_full_pipeline_runtime_field_preserved": True,
        "historical_field_name": "full_pipeline_runtime_seconds",
        "historical_field_value_seconds": float(
            summary["full_pipeline_runtime_seconds"]
        ),
        "historical_field_status": "deprecated_ambiguous_name",
        "corrected_authoritative_field_name": correction[
            "corrected_authoritative_field_name"
        ],
        "corrected_authoritative_value_seconds": correction[
            "corrected_authoritative_value_seconds"
        ],
        "phase2_5_runtime_provenance": (
            "outputs/week6_02_5_depth_model_closure/runtime_provenance.json"
        ),
        "phase2_5_depth_decision": decision["decision_code"],
        "historical_phase2_scientific_metrics_changed": False,
        "historical_phase2_prediction_files_changed": False,
    }
    summary_path.write_text(
        json.dumps(_json_safe(summary), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    pair = paired_summary.iloc[0]
    addendum = f"""

## Phase 2.5 addendum — matched stable-depth B/C closure

Phase 2.5 reran only penetration-depth Methods B and C on the same 230 stable
simulation IDs with identical fold ordering, fold-local scaling, seed logic,
kernel bounds, optimizer, and restart count. Historical Phase 2 results above
remain unchanged.

Decision: **{decision['headline']}**

`MAE_C − MAE_B = {float(pair['observed_MAE_C_minus_B_um']):+.6f} µm`
(95% paired-bootstrap CI
`[{float(pair['MAE_C_minus_B_ci95_low_um']):+.6f},
{float(pair['MAE_C_minus_B_ci95_high_um']):+.6f}]`);
`RMSE_C − RMSE_B = {float(pair['observed_RMSE_C_minus_B_um']):+.6f} µm`
(CI `[{float(pair['RMSE_C_minus_B_ci95_low_um']):+.6f},
{float(pair['RMSE_C_minus_B_ci95_high_um']):+.6f}]`).

Runtime metadata correction: the historical `full_pipeline_runtime_seconds`
value is preserved but deprecated. It measured a cached pre-report invocation,
not the original end-to-end experiment. Its authoritative descriptive name is
`{correction['corrected_authoritative_field_name']}`. Full provenance is in
`outputs/week6_02_5_depth_model_closure/runtime_provenance.json`.

Phase 3, feature-effect analysis, active learning, and level-set estimation
remain deferred.
""".rstrip()
    marker = "## Phase 2.5 addendum — matched stable-depth B/C closure"
    for filename in ("phase2_decision_log.md", "results_summary.md"):
        path = PHASE2_OUTPUT_DIR / filename
        historical = path.read_text(encoding="utf-8").rstrip()
        if marker in historical:
            historical = historical.split(marker, maxsplit=1)[0].rstrip()
        path.write_text(
            historical + "\n\n" + addendum + "\n", encoding="utf-8"
        )


def write_reports(
    *,
    stable_input: pd.DataFrame,
    metrics: pd.DataFrame,
    paired_summary: pd.DataFrame,
    stable_vs_full: pd.DataFrame,
    method_summaries: dict[str, Any],
    decision: dict[str, Any],
    runtime_provenance: dict[str, Any],
    validation: pd.DataFrame,
) -> dict[str, Any]:
    write_csv(validation, "validation_results.csv")
    write_csv(
        build_requirement_checklist(validation),
        "phase2_5_requirement_checklist.csv",
    )
    (OUTPUT_DIR / "runtime_metadata_correction.md").write_text(
        build_runtime_correction_markdown(runtime_provenance),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "depth_model_decision.md").write_text(
        build_depth_decision_markdown(
            metrics=metrics,
            paired_summary=paired_summary,
            stable_vs_full=stable_vs_full,
            method_summaries=method_summaries,
            decision=decision,
        ),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "results_summary.md").write_text(
        build_results_summary_markdown(
            stable_input=stable_input,
            metrics=metrics,
            paired_summary=paired_summary,
            stable_vs_full=stable_vs_full,
            method_summaries=method_summaries,
            decision=decision,
            validation=validation,
        ),
        encoding="utf-8",
    )
    summary = {
        "generated_at_utc": utc_now(),
        "phase": "Week 6 Phase 2.5",
        "stable_subset_size": len(stable_input),
        "removed_unstable_simulation_ids": UNSTABLE_SIMULATIONS,
        "features": FEATURE_COLUMNS,
        "target": TARGET_SOURCE_COLUMN,
        "methods": METHODS,
        "new_prediction_count": 460,
        "metrics": metrics.to_dict("records"),
        "paired_comparison": paired_summary.to_dict("records")[0],
        "method_summaries": method_summaries,
        "decision": decision,
        "validation_pass_count": int(validation["status"].eq("PASS").sum()),
        "validation_total_count": len(validation),
        "runtime_metadata_status": (
            "historical Phase 2 11.2-second field deprecated and accurately "
            "renamed with machine-readable provenance"
        ),
        "scope_status": (
            "Depth B/C closure only; no Phase 3, width/length rerun, Method A "
            "experiment, new kernel/target, feature effect, active learning, "
            "level-set estimation, or classification."
        ),
    }
    write_json(summary, "summary.json")
    return summary


def _load_existing_artifacts() -> dict[str, Any]:
    phase1, uncertainty, stable_input = load_and_validate_sources()
    modelling = modelling_table_from_stable_input(phase1, uncertainty)
    predictions_b = pd.read_csv(_prediction_path(METHOD_B))
    predictions_c = pd.read_csv(_prediction_path(METHOD_C))
    if not _prediction_is_valid(predictions_b, stable_input, METHOD_B):
        raise RuntimeError("Existing B Phase 2.5 prediction artifact is invalid")
    if not _prediction_is_valid(predictions_c, stable_input, METHOD_C):
        raise RuntimeError("Existing C Phase 2.5 prediction artifact is invalid")
    metrics = pd.read_csv(OUTPUT_DIR / "stable_depth_model_metrics.csv")
    paired_detail = pd.read_csv(
        OUTPUT_DIR / "stable_depth_paired_comparison.csv"
    )
    paired_summary = pd.read_csv(
        OUTPUT_DIR / "stable_depth_paired_bootstrap_summary.csv"
    )
    stable_vs_full = pd.read_csv(
        OUTPUT_DIR / "stable_vs_full_population_comparison.csv"
    )
    runtime = json.loads(
        (OUTPUT_DIR / "runtime_provenance.json").read_text(encoding="utf-8")
    )
    return {
        "phase1": phase1,
        "uncertainty": uncertainty,
        "stable_input": stable_input,
        "modelling": modelling,
        "predictions_b": predictions_b,
        "predictions_c": predictions_c,
        "metrics": metrics,
        "paired_detail": paired_detail,
        "paired_summary": paired_summary,
        "stable_vs_full": stable_vs_full,
        "runtime": runtime,
    }


def run_full_pipeline(*, workers: int, force: bool) -> dict[str, Any]:
    invocation_start_utc = utc_now()
    invocation_started = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    phase1, uncertainty, stable_input = load_and_validate_sources()
    modelling = modelling_table_from_stable_input(phase1, uncertainty)
    write_csv(stable_input, "stable_depth_input_table.csv")
    write_json(configuration(stable_input), "phase2_5_configuration.json")

    predictions_b, runtime_b = run_or_load_method(
        modelling,
        stable_input,
        method=METHOD_B,
        workers=workers,
        force=force,
    )
    predictions_c, runtime_c = run_or_load_method(
        modelling,
        stable_input,
        method=METHOD_C,
        workers=workers,
        force=force,
    )
    if (
        predictions_b["simulation_id"].astype(str).tolist()
        != predictions_c["simulation_id"].astype(str).tolist()
    ):
        raise RuntimeError("B and C did not use identical stable LOO IDs/order")
    if (
        predictions_b["fold_random_seed"].astype(int).tolist()
        != predictions_c["fold_random_seed"].astype(int).tolist()
    ):
        raise RuntimeError("B and C fold seeds differ")

    artifact_started = time.perf_counter()
    metrics = build_metrics(predictions_b, predictions_c)
    paired_detail, paired_summary = build_paired_comparison(
        predictions_b, predictions_c
    )
    stable_vs_full, _ = build_stable_vs_full_comparison(
        predictions_b, predictions_c, stable_input
    )
    hyperparameters = build_hyperparameter_diagnostics(
        predictions_b, predictions_c
    )
    method_summaries = build_method_summaries(
        predictions_b, predictions_c, stable_input
    )
    decision = resolve_decision(metrics, paired_summary, stable_vs_full)

    write_csv(metrics, "stable_depth_model_metrics.csv")
    write_csv(paired_detail, "stable_depth_paired_comparison.csv")
    write_csv(
        paired_summary, "stable_depth_paired_bootstrap_summary.csv"
    )
    write_csv(
        stable_vs_full, "stable_vs_full_population_comparison.csv"
    )
    write_csv(
        hyperparameters, "stable_depth_hyperparameter_diagnostics.csv"
    )
    figure_paths = generate_figures(
        predictions_b=predictions_b,
        predictions_c=predictions_c,
        paired_detail=paired_detail,
        paired_summary=paired_summary,
        stable_vs_full=stable_vs_full,
        stable_input=stable_input,
    )
    artifact_runtime = time.perf_counter() - artifact_started
    invocation_runtime = time.perf_counter() - invocation_started
    invocation_end_utc = utc_now()
    runtime = build_runtime_provenance(
        workers=workers,
        invocation_start_utc=invocation_start_utc,
        invocation_end_utc=invocation_end_utc,
        invocation_runtime_seconds=invocation_runtime,
        method_runtime_records=[runtime_b, runtime_c],
        artifact_generation_runtime_seconds=artifact_runtime,
    )
    write_json(runtime, "runtime_provenance.json")
    update_phase2_addenda(
        runtime_provenance=runtime,
        decision=decision,
        paired_summary=paired_summary,
    )
    validation = build_validations(
        phase1=phase1,
        stable_input=stable_input,
        predictions_b=predictions_b,
        predictions_c=predictions_c,
        metrics=metrics,
        paired_detail=paired_detail,
        paired_summary=paired_summary,
        stable_vs_full=stable_vs_full,
        runtime_provenance=runtime,
    )
    non_notebook_failures = validation.loc[
        (validation["status"] == "FAIL")
        & (validation["validation_number"] != 28)
    ]
    if not non_notebook_failures.empty:
        raise RuntimeError(
            "Phase 2.5 validation failed before notebook execution:\n"
            + non_notebook_failures.to_string(index=False)
        )
    summary = write_reports(
        stable_input=stable_input,
        metrics=metrics,
        paired_summary=paired_summary,
        stable_vs_full=stable_vs_full,
        method_summaries=method_summaries,
        decision=decision,
        runtime_provenance=runtime,
        validation=validation,
    )
    print(
        json.dumps(
            {
                "status": "phase2_5_full_complete",
                "figures": [path.name for path in figure_paths],
                "validation": (
                    f"{validation['status'].eq('PASS').sum()}/{len(validation)}"
                ),
                "decision": decision["headline"],
                "summary": summary,
            },
            indent=2,
            ensure_ascii=False,
        ),
        flush=True,
    )
    return summary


def validate_existing_outputs(
    *, notebook_runtime_seconds: float | None = None
) -> dict[str, Any]:
    started = time.perf_counter()
    artifacts = _load_existing_artifacts()
    if notebook_runtime_seconds is not None:
        artifacts["runtime"]["phase2_5_measured_durations"][
            "notebook_execution_runtime_seconds"
        ] = float(notebook_runtime_seconds)
    validation = build_validations(
        phase1=artifacts["phase1"],
        stable_input=artifacts["stable_input"],
        predictions_b=artifacts["predictions_b"],
        predictions_c=artifacts["predictions_c"],
        metrics=artifacts["metrics"],
        paired_detail=artifacts["paired_detail"],
        paired_summary=artifacts["paired_summary"],
        stable_vs_full=artifacts["stable_vs_full"],
        runtime_provenance=artifacts["runtime"],
    )
    elapsed = time.perf_counter() - started
    artifacts["runtime"]["phase2_5_measured_durations"][
        "last_validation_runtime_seconds"
    ] = elapsed
    artifacts["runtime"]["generated_at_utc"] = utc_now()
    write_json(artifacts["runtime"], "runtime_provenance.json")
    method_summaries = build_method_summaries(
        artifacts["predictions_b"],
        artifacts["predictions_c"],
        artifacts["stable_input"],
    )
    decision = resolve_decision(
        artifacts["metrics"],
        artifacts["paired_summary"],
        artifacts["stable_vs_full"],
    )
    update_phase2_addenda(
        runtime_provenance=artifacts["runtime"],
        decision=decision,
        paired_summary=artifacts["paired_summary"],
    )
    summary = write_reports(
        stable_input=artifacts["stable_input"],
        metrics=artifacts["metrics"],
        paired_summary=artifacts["paired_summary"],
        stable_vs_full=artifacts["stable_vs_full"],
        method_summaries=method_summaries,
        decision=decision,
        runtime_provenance=artifacts["runtime"],
        validation=validation,
    )
    if not validation["status"].eq("PASS").all():
        failures = validation.loc[
            validation["status"] == "FAIL",
            ["validation_number", "validation_check", "details"],
        ]
        raise RuntimeError(
            "Phase 2.5 validation failures:\n"
            + failures.to_string(index=False)
        )
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
    return summary


def run_smoke_test(*, workers: int) -> dict[str, Any]:
    phase1, uncertainty, stable_input = load_and_validate_sources()
    modelling = modelling_table_from_stable_input(phase1, uncertainty)
    positions = [0, 1, 37, 75, 113, 150, 188, 229]
    smoke = modelling.iloc[positions].copy().reset_index(drop=True)
    started = time.perf_counter()
    frames: dict[str, pd.DataFrame] = {}
    for method in METHODS:
        frames[method] = phase2.run_loo_method(
            smoke,
            target_key="depth",
            method=method,
            analysis_label="phase2_5_smoke_8_stable",
            workers=workers,
            n_restarts_optimizer=phase2.N_RESTARTS_OPTIMIZER,
            force=True,
            use_checkpoint=False,
        )
    payload = {
        "status": "smoke_only_not_scientific_result",
        "simulation_count": len(smoke),
        "methods": METHODS,
        "prediction_rows": sum(len(frame) for frame in frames.values()),
        "identical_fold_order": (
            frames[METHOD_B]["heldout_simulation_id"].tolist()
            == frames[METHOD_C]["heldout_simulation_id"].tolist()
        ),
        "identical_fold_seeds": (
            frames[METHOD_B]["fold_random_seed"].tolist()
            == frames[METHOD_C]["fold_random_seed"].tolist()
        ),
        "failed_folds": int(
            frames[METHOD_B]["failed_fold"].sum()
            + frames[METHOD_C]["failed_fold"].sum()
        ),
        "runtime_seconds": time.perf_counter() - started,
    }
    write_json(payload, "smoke_test_summary.json")
    print(json.dumps(payload, indent=2), flush=True)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Week 6 Phase 2.5 matched stable-depth GP closure"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--full", action="store_true")
    mode.add_argument("--validate-only", action="store_true")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--notebook-runtime-seconds",
        type=float,
        default=None,
        help="Measured notebook execution runtime to record during validation",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be positive")
    if args.smoke:
        run_smoke_test(workers=args.workers)
    elif args.full:
        run_full_pipeline(workers=args.workers, force=args.force)
    else:
        validate_existing_outputs(
            notebook_runtime_seconds=args.notebook_runtime_seconds
        )


if __name__ == "__main__":
    main()
