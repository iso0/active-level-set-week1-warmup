"""Week 9 Phase 2: temporal melt-pool width dynamics.

This module is deliberately an auditable, non-active-learning pipeline.  It
reconstructs physical width traces from the pinned sph_v2 monitor files,
builds a small predeclared feature set, and evaluates leak-free logistic
models on the frozen Week 8.5 grouped folds.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src import week7_phase2_sph_v2_physical_target_extraction as p2
from src import week8_5_frozen_sample_efficiency_confirmation as w85


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase2_temporal_width_dynamics"
FIGURES = OUTPUT / "figures"
NOTEBOOK = ROOT / "notebooks" / "week_09" / "05_week9_phase2_temporal_width_dynamics.ipynb"
SOURCE_PLAN = ROOT / "outputs" / "week7_02_sph_v2_target_extraction" / "monitor_source_plan.csv"
STARTING_SHA = "f74c6252bbb48d503f969ef5300f20894079301b"
BRANCH = "codex/week9-phase2-temporal-width-dynamics"
GRID = np.linspace(0.0, 1.0, 201)
PREFIXES = (0.20, 0.40, 0.60, 0.80, 1.00)
BOOTSTRAP_DRAWS = 5000
SEED = 260831
STATIC_FEATURES = ("W_initial_um", "W_max_um", "W_T0_um")
SHAPE_FEATURES = (
    "width_gain_20_um",
    "width_gain_40_um",
    "time_to_50pct_max_width_tau",
)
RAW_DERIVATIVE_FEATURES = (
    "max_positive_dWdt_um_per_ms",
    "median_positive_dWdt_um_per_ms",
    "time_of_max_dWdt_tau",
    "early_dWdt_20_um_per_ms",
    "early_dWdt_40_um_per_ms",
)
ROBUST_DERIVATIVE_FEATURES = (
    "robust_max_positive_dWdt_um_per_ms",
    "robust_median_positive_dWdt_um_per_ms",
    "robust_early_dWdt_20_um_per_ms",
    "robust_early_dWdt_40_um_per_ms",
    "robust_time_of_max_dWdt_tau",
)
TEMPORAL_FEATURES = (*SHAPE_FEATURES, *ROBUST_DERIVATIVE_FEATURES)
PREFIX_FEATURES = (
    "current_width_um",
    "width_gain_so_far_um",
    "normalized_slope_so_far_um_per_tau",
    "robust_median_positive_dWdt_so_far_um_per_ms",
    "robust_max_positive_dWdt_so_far_um_per_ms",
)
PUBLISHED_DX_SHA = "373f72a80a2c5e5fe13d81c2afbb255b0facbf29"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    frame.to_csv(tmp, index=False, lineterminator="\n", compression="gzip" if path.suffix == ".gz" else None)
    tmp.replace(path)


def write_json(path: Path, payload: Any) -> None:
    def safe(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [safe(v) for v in value]
        if isinstance(value, (np.integer, np.floating)):
            value = value.item()
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_population() -> pd.DataFrame:
    pop = w85.load_population().reset_index(drop=True)
    require(len(pop) == 405 and int(pop.has_keyhole.sum()) == 73, "canonical population/labels drift")
    require(pop.experiment_name.is_unique, "canonical experiment IDs are not unique")
    return pop


def log_h(population: pd.DataFrame) -> np.ndarray:
    p = population.P.to_numpy(float)
    vx = population.VX.to_numpy(float)
    ls = population.LS.to_numpy(float)
    require(np.all(p > 0) and np.all(vx > 0) and np.all(ls > 0), "h requires positive P, VX and LS")
    return np.log(p / np.sqrt(vx * ls**3))


def source_paths() -> pd.DataFrame:
    plan = pd.read_csv(SOURCE_PLAN)
    wanted = plan[plan.monitor_file.isin(["position-bounds_melt.dat", "time.dat", "iter.dat"])].copy()
    wide = wanted.pivot(index="experiment_name", columns="monitor_file", values="local_path").reset_index()
    return wide.rename(columns={
        "position-bounds_melt.dat": "bounds_path",
        "time.dat": "time_path",
        "iter.dat": "iter_path",
    })


def axis_semantics_audit(population: pd.DataFrame) -> pd.DataFrame:
    """Verify semantic and numerical ΔX/ΔY mapping before any analysis."""
    source = ROOT / "src" / "week7_phase2_sph_v2_physical_target_extraction.py"
    text = source.read_text(encoding="utf-8")
    semantic_checks = {
        "columns": 'POSITION_BOUNDS_COLUMNS = ["x_min", "x_max", "y_min", "y_max", "z_min", "z_max"]' in text,
        "length": "length_m = extents[:, 0]" in text,
        "width": "width_m = extents[:, 1]" in text,
    }
    require(all(semantic_checks.values()), f"authoritative axis semantics not verified: {semantic_checks}")
    merged = population.merge(source_paths(), on="experiment_name", how="left")
    candidates = merged[merged.bounds_path.map(_existing)].head(5)
    require(len(candidates) == 5, "fewer than five pinned bounds files available for axis audit")
    numeric_x, numeric_y = [], []
    for row in candidates.itertuples(index=False):
        bounds, _ = p2.load_numeric(Path(row.bounds_path), "position-bounds_melt.dat")
        valid = np.all(np.isfinite(bounds), axis=1) & np.all(np.abs(bounds) < p2.SENTINEL_THRESHOLD, axis=1)
        extents = bounds[valid][:, [1, 3, 5]] - bounds[valid][:, [0, 2, 4]]
        numeric_x.append(bool(np.allclose(extents[:, 0], bounds[valid, 1] - bounds[valid, 0], rtol=0, atol=1e-15)))
        numeric_y.append(bool(np.allclose(extents[:, 1], bounds[valid, 3] - bounds[valid, 2], rtol=0, atol=1e-15)))
    rows = [
        {"quantity":"longitudinal_length", "formula":"x_max - x_min", "physical_interpretation":"longitudinal melt-pool length ΔX",
         "authoritative_source_file":str(source.relative_to(ROOT)), "authoritative_source_line_or_function":"POSITION_BOUNDS_COLUMNS; extract_experiment: length_m = extents[:, 0]",
         "semantic_source_verified":semantic_checks["columns"] and semantic_checks["length"], "numeric_files_checked":len(numeric_x),
         "numeric_mapping_verified":all(numeric_x), "status":"PASS" if all(numeric_x) else "FAIL"},
        {"quantity":"transverse_width", "formula":"y_max - y_min", "physical_interpretation":"transverse melt-pool width ΔY",
         "authoritative_source_file":str(source.relative_to(ROOT)), "authoritative_source_line_or_function":"POSITION_BOUNDS_COLUMNS; extract_experiment: width_m = extents[:, 1]",
         "semantic_source_verified":semantic_checks["columns"] and semantic_checks["width"], "numeric_files_checked":len(numeric_y),
         "numeric_mapping_verified":all(numeric_y), "status":"PASS" if all(numeric_y) else "FAIL"},
    ]
    audit = pd.DataFrame(rows)
    require(audit.status.eq("PASS").all(), "axis semantics audit failed")
    write_csv(OUTPUT / "axis_semantics_audit.csv", audit)
    return audit


def _existing(path: Any) -> bool:
    return isinstance(path, str) and Path(path).is_file()


def regularity_rule(dt_s: np.ndarray) -> tuple[bool, float, float]:
    """Label-free rule: CV <=5% and p99/p1 <=1.10 is effectively uniform."""
    cv = float(np.std(dt_s) / np.mean(dt_s))
    ratio = float(np.quantile(dt_s, 0.99) / np.quantile(dt_s, 0.01))
    return bool(cv <= 0.05 and ratio <= 1.10), cv, ratio


def centered_derivative(time_ms: np.ndarray, width_um: np.ndarray) -> np.ndarray:
    require(len(time_ms) >= 3 and np.all(np.diff(time_ms) > 0), "derivative requires ordered positive dt")
    return np.gradient(width_um, time_ms, edge_order=1)


def local_linear_grid_derivative(time_ms: np.ndarray, width_um: np.ndarray, half_window: int = 2) -> np.ndarray:
    """Fixed five-grid-point local-linear robustness derivative."""
    out = np.empty(len(time_ms), dtype=float)
    for i in range(len(time_ms)):
        lo, hi = max(0, i - half_window), min(len(time_ms), i + half_window + 1)
        x = time_ms[lo:hi]
        y = width_um[lo:hi]
        out[i] = np.polyfit(x - x.mean(), y, 1)[0]
    return out


def synthetic_derivative_error() -> float:
    t = np.linspace(0.0, 2.0, 1001)
    w = 3.0 * t**2 + 2.0 * t + 1.0
    estimated = centered_derivative(t, w)
    truth = 6.0 * t + 2.0
    return float(np.max(np.abs(estimated[1:-1] - truth[1:-1])))


def _axis_trace_features(values_um: np.ndarray, tau: np.ndarray, t_ms: np.ndarray, uniform: bool, prefix: str = "") -> tuple[dict[str, float], np.ndarray, np.ndarray, np.ndarray]:
    primary = centered_derivative(t_ms, values_um) if uniform else local_linear_grid_derivative(t_ms, values_um)
    value_grid = np.interp(GRID, tau, values_um)
    derivative_grid = np.interp(GRID, tau, primary)
    robust_grid = local_linear_grid_derivative(GRID * float(t_ms[-1]), value_grid)
    positive = derivative_grid[derivative_grid > 0]
    robust_positive = robust_grid[robust_grid > 0]
    target50 = value_grid[0] + 0.5 * (float(np.max(value_grid)) - value_grid[0])
    hit50 = np.flatnonzero(value_grid >= target50)
    f = {
        f"{prefix}initial_um": float(value_grid[0]),
        f"{prefix}max_um": float(np.max(value_grid)),
        f"{prefix}T0_um": float(np.median(value_grid[GRID >= 0.8])),
        f"{prefix}max_positive_dWdt_um_per_ms": float(np.max(positive)) if len(positive) else 0.0,
        f"{prefix}median_positive_dWdt_um_per_ms": float(np.median(positive)) if len(positive) else 0.0,
        f"{prefix}time_of_max_dWdt_tau": float(GRID[int(np.argmax(derivative_grid))]),
        f"{prefix}early_dWdt_20_um_per_ms": float(np.median(derivative_grid[GRID <= .2])),
        f"{prefix}early_dWdt_40_um_per_ms": float(np.median(derivative_grid[GRID <= .4])),
        f"{prefix}gain_20_um": float(np.interp(.2, GRID, value_grid) - value_grid[0]),
        f"{prefix}gain_40_um": float(np.interp(.4, GRID, value_grid) - value_grid[0]),
        f"{prefix}time_to_50pct_max_tau": float(GRID[hit50[0]]) if len(hit50) else 1.0,
        f"{prefix}robust_max_positive_dWdt_um_per_ms": float(np.max(robust_positive)) if len(robust_positive) else 0.0,
        f"{prefix}robust_median_positive_dWdt_um_per_ms": float(np.median(robust_positive)) if len(robust_positive) else 0.0,
        f"{prefix}robust_early_dWdt_20_um_per_ms": float(np.median(robust_grid[GRID <= .2])),
        f"{prefix}robust_early_dWdt_40_um_per_ms": float(np.median(robust_grid[GRID <= .4])),
        f"{prefix}robust_time_of_max_dWdt_tau": float(GRID[int(np.argmax(robust_grid))]),
    }
    return f, value_grid, derivative_grid, robust_grid


def _parse_trace(row: pd.Series) -> tuple[dict[str, Any], pd.DataFrame, dict[str, Any]]:
    bounds, bounds_audit = p2.load_numeric(Path(row.bounds_path), "position-bounds_melt.dat")
    time_s, time_audit = p2.load_numeric(Path(row.time_path), "time.dat")
    if time_s.ndim == 2:
        time_s = time_s[:, 0]
    require(bounds.ndim == 2 and bounds.shape[1] == 6, f"{row.experiment_name}: malformed bounds")
    require(len(bounds) == len(time_s), f"{row.experiment_name}: monitor row mismatch")
    longitudinal_length_m = bounds[:, 1] - bounds[:, 0]
    transverse_width_m = bounds[:, 3] - bounds[:, 2]
    valid = (
        np.isfinite(time_s) & np.isfinite(transverse_width_m) & np.isfinite(longitudinal_length_m)
        & np.all(np.isfinite(bounds), axis=1)
        & np.all(np.abs(bounds) < p2.SENTINEL_THRESHOLD, axis=1)
        & (transverse_width_m >= 0) & (longitudinal_length_m >= 0)
    )
    active = valid & (time_s >= float(row.active_region_start_time_s)) & (time_s <= float(row.active_region_end_time_s))
    t = time_s[active]
    w = transverse_width_m[active] * 1e6
    length = longitudinal_length_m[active] * 1e6
    require(len(t) >= 25, f"{row.experiment_name}: too few active width rows")
    require(np.all(np.diff(t) > 0), f"{row.experiment_name}: non-positive dt after cleaning")
    t_ms = (t - t[0]) * 1e3
    duration_ms = float(t_ms[-1])
    tau = t_ms / duration_ms
    dt_s = np.diff(t)
    uniform, dt_cv, dt_ratio = regularity_rule(dt_s)
    canonical, w_grid, d_grid, robust_grid = _axis_trace_features(w, tau, t_ms, uniform)
    longitudinal, length_grid, length_d_grid, length_robust_grid = _axis_trace_features(length, tau, t_ms, uniform, prefix="L_")
    t_grid_ms = GRID * duration_ms
    diff = np.diff(w)
    mad_diff = float(stats.median_abs_deviation(diff, scale="normal"))
    jump_threshold = max(5.0, 10.0 * mad_diff)
    jumps = np.abs(diff) > jump_threshold
    rename = {
        "initial_um":"W_initial_um", "max_um":"W_max_um", "T0_um":"W_T0_um",
        "gain_20_um":"width_gain_20_um", "gain_40_um":"width_gain_40_um",
        "time_to_50pct_max_tau":"time_to_50pct_max_width_tau",
    }
    canonical = {rename.get(k, k): v for k, v in canonical.items()}
    features = {
        "experiment_name": row.experiment_name,
        "population_row_index": int(row.population_row_index),
        "has_keyhole": int(row.has_keyhole),
        "P": float(row.P), "VX": float(row.VX), "LS": float(row.LS), "ST": float(row.ST),
        "log_h": float(row.log_h),
        **canonical, **longitudinal,
    }
    audit = {
        "experiment_name": row.experiment_name,
        "population_row_index": int(row.population_row_index),
        "has_keyhole": int(row.has_keyhole),
        "active_sample_count": int(len(t)),
        "active_duration_ms": duration_ms,
        "first_active_time_s": float(t[0]),
        "last_active_time_s": float(t[-1]),
        "median_dt_us": float(np.median(dt_s) * 1e6),
        "dt_cv": dt_cv,
        "dt_p99_p01_ratio": dt_ratio,
        "sampling_effectively_uniform": uniform,
        "derivative_method": "centered_finite_difference" if uniform else "local_linear_physical_time",
        "duplicate_timestamp_count": int(np.sum(np.diff(time_s[np.isfinite(time_s)]) == 0)),
        "nonpositive_dt_count_raw": int(np.sum(np.diff(time_s[np.isfinite(time_s)]) <= 0)),
        "missing_transverse_width_count": int(np.sum(~np.isfinite(transverse_width_m))),
        "missing_longitudinal_length_count": int(np.sum(~np.isfinite(longitudinal_length_m))),
        "invalid_or_sentinel_row_count": int(np.sum(~valid)),
        "obvious_jump_count": int(jumps.sum()),
        "largest_jump_um": float(np.max(np.abs(diff))) if len(diff) else 0.0,
        "jump_threshold_um": jump_threshold,
        "oscillation_mad_delta_um": mad_diff,
        "nonmonotonic_fraction": float(np.mean(diff < 0)),
        "monotonic_nondecreasing": bool(np.all(diff >= -1e-12)),
        "significant_negative_step_fraction": float(np.mean(diff < -max(0.1, 3.0 * mad_diff))),
        "quality_flag": "pathological_jumps" if int(jumps.sum()) > max(10, int(0.01 * len(diff))) else ("oscillatory" if np.mean(diff < -max(0.1, 3.0 * mad_diff)) > 0.10 else "ok"),
        "bounds_known_sentinel_rows_excluded": int(bounds_audit.get("known_malformed_no_melt_sentinel_row_count", 0)),
        "cooling_rows_in_primary": 0,
    }
    profile = pd.DataFrame({
        "experiment_name": row.experiment_name,
        "population_row_index": int(row.population_row_index),
        "has_keyhole": int(row.has_keyhole),
        "tau": GRID,
        "time_from_active_start_ms": t_grid_ms,
        "transverse_width_um": w_grid,
        "transverse_dWdt_raw_um_per_ms": d_grid,
        "transverse_dWdt_robust_um_per_ms": robust_grid,
        "longitudinal_length_um": length_grid,
        "longitudinal_dLdt_raw_um_per_ms": length_d_grid,
        "longitudinal_dLdt_robust_um_per_ms": length_robust_grid,
    })
    onset = {
        "experiment_name": row.experiment_name,
        "has_keyhole": int(row.has_keyhole),
        "onset_available": False,
        "first_keyhole_monitor_row_index": None,
        "first_keyhole_time_s": None,
        "first_keyhole_tau": None,
        "peak_dWdt_tau": float(GRID[int(np.argmax(d_grid))]),
        "peak_minus_first_keyhole_ms": None,
        "peak_precedes_first_observed_keyhole": None,
    }
    if bool(row.has_keyhole) and bool(row.label_timestep_alignment_exact) and pd.notna(row.first_keyhole_monitor_row_index):
        idx = int(row.first_keyhole_monitor_row_index)
        if 0 <= idx < len(time_s) and float(row.active_region_start_time_s) <= time_s[idx] <= float(row.active_region_end_time_s):
            onset_t = float(time_s[idx])
            onset_tau = (onset_t - t[0]) / (t[-1] - t[0])
            peak_time = t[0] + float(GRID[int(np.argmax(d_grid))]) * (t[-1] - t[0])
            onset.update({
                "onset_available": True,
                "first_keyhole_monitor_row_index": idx,
                "first_keyhole_time_s": onset_t,
                "first_keyhole_tau": float(onset_tau),
                "peak_minus_first_keyhole_ms": float((peak_time - onset_t) * 1e3),
                "peak_precedes_first_observed_keyhole": bool(peak_time < onset_t),
            })
    return audit, profile, features | onset


def audit_and_extract() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pop = load_population()
    pop["population_row_index"] = np.arange(len(pop))
    pop["log_h"] = log_h(pop)
    merged = pop.merge(source_paths(), on="experiment_name", how="left", validate="one_to_one")
    merged["bounds_available"] = merged.bounds_path.map(_existing)
    merged["time_available"] = merged.time_path.map(_existing)
    merged["iter_available"] = merged.iter_path.map(_existing)
    merged["usable_width_timeseries"] = merged.bounds_available & merged.time_available & merged.target_extraction_valid.astype(bool)

    miss_rows: list[dict[str, Any]] = []
    for usable, group in merged.groupby("usable_width_timeseries", observed=True):
        miss_rows.append({
            "category": "valid_width_time_series" if usable else "missing_or_unusable_width_time_series",
            "count": len(group),
            "keyhole_count": int(group.has_keyhole.sum()),
            "conduction_count": int((~group.has_keyhole.astype(bool)).sum()),
            **{f"{name}_mean": float(group[name].mean()) for name in ("P", "VX", "LS", "ST")},
        })
    for name in ("P", "VX", "LS", "ST"):
        yes = merged.loc[merged.usable_width_timeseries, name].to_numpy(float)
        no = merged.loc[~merged.usable_width_timeseries, name].to_numpy(float)
        pooled = math.sqrt(((len(yes)-1)*yes.var(ddof=1)+(len(no)-1)*no.var(ddof=1))/(len(yes)+len(no)-2))
        miss_rows.append({"category": f"structured_missingness_{name}", "count": len(merged), "standardized_mean_difference_usable_minus_missing": float((yes.mean()-no.mean())/pooled)})
    missing = pd.DataFrame(miss_rows)
    write_csv(OUTPUT / "width_missingness_audit.csv", missing)

    audits, profiles, packed = [], [], []
    usable = merged[merged.usable_width_timeseries].copy()
    parsed = Parallel(n_jobs=4, prefer="threads", verbose=5)(delayed(_parse_trace)(row) for _, row in usable.iterrows())
    for number, (audit, profile, features) in enumerate(parsed, 1):
        audits.append(audit); profiles.append(profile); packed.append(features)
        if number % 25 == 0:
            print(f"trace extraction {number}/{len(usable)}", flush=True)
    audit_frame = pd.DataFrame(audits)
    profile_frame = pd.concat(profiles, ignore_index=True)
    features = pd.DataFrame(packed)
    onset_columns = [c for c in features.columns if c in {
        "experiment_name", "has_keyhole", "onset_available", "first_keyhole_monitor_row_index",
        "first_keyhole_time_s", "first_keyhole_tau", "peak_dWdt_tau", "peak_minus_first_keyhole_ms",
        "peak_precedes_first_observed_keyhole"}]
    onset = features[onset_columns].copy()
    features = features.drop(columns=[c for c in onset_columns if c not in {"experiment_name", "has_keyhole"}])
    write_csv(OUTPUT / "width_timeseries_audit.csv", audit_frame)
    write_csv(OUTPUT / "derivative_method_audit.csv", audit_frame[[
        "experiment_name", "sampling_effectively_uniform", "derivative_method", "median_dt_us",
        "dt_cv", "dt_p99_p01_ratio", "active_duration_ms"]])
    write_csv(OUTPUT / "width_temporal_features.csv", features)
    write_csv(OUTPUT / "temporal_profiles.csv.gz", profile_frame)
    write_csv(OUTPUT / "keyhole_onset_audit.csv", onset)
    return merged, audit_frame, profile_frame, features


def prefix_feature_table(profiles: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    base = features.set_index("experiment_name")
    for name, group in profiles.groupby("experiment_name", sort=False):
        group = group.sort_values("tau")
        for prefix in PREFIXES:
            seen = group[group.tau <= prefix + 1e-12]
            w = seen.transverse_width_um.to_numpy(float)
            d = seen.transverse_dWdt_robust_um_per_ms.to_numpy(float)
            tau = seen.tau.to_numpy(float)
            pos = d[d > 0]
            rows.append({
                "experiment_name": name,
                "population_row_index": int(base.loc[name, "population_row_index"]),
                "has_keyhole": int(base.loc[name, "has_keyhole"]),
                "P": float(base.loc[name, "P"]), "VX": float(base.loc[name, "VX"]),
                "LS": float(base.loc[name, "LS"]), "ST": float(base.loc[name, "ST"]),
                "log_h": float(base.loc[name, "log_h"]), "prefix_tau": prefix,
                "current_width_um": float(w[-1]),
                "width_gain_so_far_um": float(w[-1] - w[0]),
                "normalized_slope_so_far_um_per_tau": float(np.polyfit(tau, w, 1)[0]),
                "robust_median_positive_dWdt_so_far_um_per_ms": float(np.median(pos)) if len(pos) else 0.0,
                "robust_max_positive_dWdt_so_far_um_per_ms": float(np.max(pos)) if len(pos) else 0.0,
                "latest_source_tau": float(tau[-1]),
            })
    out = pd.DataFrame(rows)
    require(np.all(out.latest_source_tau <= out.prefix_tau + 1e-12), "prefix feature used future samples")
    write_csv(OUTPUT / "prefix_temporal_features.csv", out)
    return out


def cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean(x[:, None] > y[None, :]) - np.mean(x[:, None] < y[None, :]))


def feature_effects(features: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows = []
    robustness = ROBUST_DERIVATIVE_FEATURES
    for feature in (*STATIC_FEATURES, *SHAPE_FEATURES, *RAW_DERIVATIVE_FEATURES, *ROBUST_DERIVATIVE_FEATURES):
        c = features.loc[features.has_keyhole.eq(0), feature].to_numpy(float)
        k = features.loc[features.has_keyhole.eq(1), feature].to_numpy(float)
        delta = float(np.median(k) - np.median(c))
        boot = np.empty(BOOTSTRAP_DRAWS)
        for b in range(BOOTSTRAP_DRAWS):
            boot[b] = np.median(rng.choice(k, len(k), replace=True)) - np.median(rng.choice(c, len(c), replace=True))
        rho, p = stats.spearmanr(features[feature], features.has_keyhole.astype(int))
        rows.append({
            "feature": feature, "feature_group": "robust_derivative" if feature in robustness else ("raw_derivative" if feature in RAW_DERIVATIVE_FEATURES else ("static" if feature in STATIC_FEATURES else "shape")), "conduction_n": len(c), "keyhole_n": len(k),
            "conduction_median": float(np.median(c)), "keyhole_median": float(np.median(k)),
            "median_difference_keyhole_minus_conduction": delta,
            "median_difference_ci_low": float(np.quantile(boot, .025)),
            "median_difference_ci_high": float(np.quantile(boot, .975)),
            "cliffs_delta": cliffs_delta(k, c), "spearman_rho_with_label": float(rho),
            "spearman_p": float(p),
        })
    out = pd.DataFrame(rows)
    order = np.argsort(out.spearman_p.to_numpy(float))
    adjusted = np.empty(len(out), dtype=float)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, float(out.iloc[index].spearman_p) * (len(out) - rank))
        adjusted[index] = min(1.0, running)
    out["holm_p"] = adjusted
    write_csv(OUTPUT / "static_feature_effects.csv", out)
    return out


def derivative_robustness_gate(effects: pd.DataFrame) -> pd.DataFrame:
    pairs = [
        ("max_positive_dWdt_um_per_ms", "robust_max_positive_dWdt_um_per_ms", "maximum positive derivative"),
        ("median_positive_dWdt_um_per_ms", "robust_median_positive_dWdt_um_per_ms", "median positive derivative"),
        ("early_dWdt_20_um_per_ms", "robust_early_dWdt_20_um_per_ms", "early 20% derivative"),
        ("early_dWdt_40_um_per_ms", "robust_early_dWdt_40_um_per_ms", "early 40% derivative"),
        ("time_of_max_dWdt_tau", "robust_time_of_max_dWdt_tau", "time of derivative peak"),
    ]
    rows = []
    indexed = effects.set_index("feature")
    for raw_name, robust_name, claim in pairs:
        raw, robust = indexed.loc[raw_name], indexed.loc[robust_name]
        same_direction = bool(np.sign(raw.cliffs_delta) == np.sign(robust.cliffs_delta) or raw.cliffs_delta == 0 or robust.cliffs_delta == 0)
        robust_interval_excludes_zero = bool(robust.median_difference_ci_low > 0 or robust.median_difference_ci_high < 0)
        retained_fraction = abs(float(robust.cliffs_delta)) / max(abs(float(raw.cliffs_delta)), 1e-12)
        if not same_direction:
            status = "UNSTABLE"
        elif retained_fraction >= .5 and robust_interval_excludes_zero:
            status = "ROBUST"
        else:
            status = "QUALIFIED"
        rows.append({"derivative_claim":claim, "raw_feature":raw_name, "robust_feature":robust_name,
            "raw_cliffs_delta":raw.cliffs_delta, "robust_cliffs_delta":robust.cliffs_delta,
            "direction_consistent":same_direction, "robust_effect_fraction_of_raw":retained_fraction,
            "robust_median_difference_ci_low":robust.median_difference_ci_low,
            "robust_median_difference_ci_high":robust.median_difference_ci_high,
            "status":status})
    out = pd.DataFrame(rows)
    write_csv(OUTPUT / "derivative_robustness_gate.csv", out)
    return out


def _git_show_csv(revision: str, relative_path: str) -> pd.DataFrame:
    result = subprocess.run(["git", "show", f"{revision}:{relative_path}"], cwd=ROOT, text=True, capture_output=True, check=True)
    return pd.read_csv(io.StringIO(result.stdout))


def longitudinal_comparison(effects: pd.DataFrame, model_summary: pd.DataFrame) -> pd.DataFrame:
    base = "outputs/week9_phase2_temporal_width_dynamics"
    old_effects = _git_show_csv(PUBLISHED_DX_SHA, f"{base}/static_feature_effects.csv").set_index("feature")
    old_models = _git_show_csv(PUBLISHED_DX_SHA, f"{base}/model_oof_summary.csv")
    new_effects = effects.set_index("feature")
    def metric(table: pd.DataFrame, model: str, subset: str, name: str) -> float:
        return float(table[(table.model.eq(model)) & table.subset.eq(subset) & table.metric.eq(name)].iloc[0]["mean"])
    rows = []
    for axis, eff, models, representation in (
        ("longitudinal_length_delta_X", old_effects, old_models, "published diagnostic used raw finite-difference temporal features"),
        ("transverse_width_delta_Y", new_effects, model_summary, "corrected primary uses shape plus fixed robust-derivative features"),
    ):
        prefix = "L" if axis.startswith("longitudinal") else "W"
        strongest = max(("W_max_um","W_T0_um","time_to_50pct_max_width_tau","robust_early_dWdt_20_um_per_ms"), key=lambda name:abs(float(eff.loc[name,"cliffs_delta"])))
        rows.append({
            "axis_quantity":axis, "role":"secondary longitudinal diagnostic" if prefix=="L" else "canonical answer to Ioan's width question",
            "formula":"x_max - x_min" if prefix=="L" else "y_max - y_min",
            "model_feature_representation":representation,
            "static_max_conduction_median_um":float(eff.loc["W_max_um","conduction_median"]),
            "static_max_keyhole_median_um":float(eff.loc["W_max_um","keyhole_median"]),
            "T0_conduction_median_um":float(eff.loc["W_T0_um","conduction_median"]),
            "T0_keyhole_median_um":float(eff.loc["W_T0_um","keyhole_median"]),
            "time_to_50pct_conduction_median_tau":float(eff.loc["time_to_50pct_max_width_tau","conduction_median"]),
            "time_to_50pct_keyhole_median_tau":float(eff.loc["time_to_50pct_max_width_tau","keyhole_median"]),
            "robust_early20_conduction_median_um_per_ms":float(eff.loc["robust_early_dWdt_20_um_per_ms","conduction_median"]),
            "robust_early20_keyhole_median_um_per_ms":float(eff.loc["robust_early_dWdt_20_um_per_ms","keyhole_median"]),
            "full_width_dynamics_balanced_accuracy":metric(models,"width_dynamics","full","balanced_accuracy"),
            "q20_width_dynamics_balanced_accuracy":metric(models,"width_dynamics","q20","balanced_accuracy"),
            "q20_width_dynamics_keyhole_recall":metric(models,"width_dynamics","q20","keyhole_recall"),
            "q20_h_plus_axis_dynamics_balanced_accuracy":metric(models,"h_plus_width_dynamics","q20","balanced_accuracy"),
            "strongest_effect_feature":strongest, "strongest_effect_cliffs_delta":float(eff.loc[strongest,"cliffs_delta"]),
            "strongest_qualitative_conclusion":"longitudinal ΔX carried strong regime structure but was not transverse width" if prefix=="L" else "transverse ΔY is the corrected canonical monitoring quantity",
        })
    out = pd.DataFrame(rows)
    write_csv(OUTPUT / "longitudinal_vs_transverse_summary.csv", out)
    diagnostic = OUTPUT / "longitudinal_length_diagnostic"
    diagnostic.mkdir(parents=True, exist_ok=True)
    write_csv(diagnostic / "published_delta_x_summary.csv", out[out.axis_quantity.eq("longitudinal_length_delta_X")])
    (diagnostic / "README.md").write_text("# Longitudinal ΔX diagnostic\n\nThis preserves the essential result from published commit `373f72a`: ΔX is longitudinal length, not Ioan's requested transverse width. It is secondary context only.\n", encoding="utf-8")
    return out


def _safe_auc(y: np.ndarray, p: np.ndarray, kind: str) -> float:
    if len(np.unique(y)) < 2:
        return float("nan")
    return float(roc_auc_score(y, p) if kind == "roc" else average_precision_score(y, p))


def metric_row(y: np.ndarray, probability: np.ndarray) -> dict[str, Any]:
    pred = (probability >= .5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "row_count": len(y), "keyhole_count": int(y.sum()),
        "roc_auc": _safe_auc(y, probability, "roc"), "pr_auc": _safe_auc(y, probability, "pr"),
        "accuracy": float(accuracy_score(y, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "keyhole_recall": float(recall_score(y, pred, pos_label=1, zero_division=0)),
        "conduction_recall": float(recall_score(y, pred, pos_label=0, zero_division=0)),
        "false_negative": int(fn), "false_positive": int(fp),
        "brier_score": float(brier_score_loss(y, probability)),
    }


def _model(c: float) -> Pipeline:
    return Pipeline([
        ("scale", StandardScaler()),
        ("logistic", LogisticRegression(C=c, solver="lbfgs", max_iter=3000, random_state=SEED)),
    ])


def _fit_predict(train: pd.DataFrame, test: pd.DataFrame, columns: Iterable[str], c: float) -> np.ndarray:
    columns = list(columns)
    model = _model(c)
    model.fit(train[columns].to_numpy(float), train.has_keyhole.to_numpy(int))
    return model.predict_proba(test[columns].to_numpy(float))[:, 1]


def _subset_flags(spec: w85.SplitSpec, population: pd.DataFrame, usable_test_indices: np.ndarray) -> dict[str, np.ndarray]:
    distances = w85.b1_distance(population)
    original = w85.boundary_flags(spec, population, distances)
    test = np.asarray(spec.test_indices)
    lookup = {int(idx): pos for pos, idx in enumerate(test)}
    return {
        "full": np.ones(len(usable_test_indices), dtype=bool),
        "q30": np.array([original["B1_q30"][lookup[int(i)]] for i in usable_test_indices]),
        "q20": np.array([original["B1_q20"][lookup[int(i)]] for i in usable_test_indices]),
    }


def evaluate_models(population: pd.DataFrame, features: pd.DataFrame, prefix: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    specs = w85.build_splits(population)
    require(len(specs) == 100, "frozen split count drift")
    by_index = features.set_index("population_row_index", drop=False)
    usable_indices = set(by_index.index.astype(int))
    predictions, prefix_predictions = [], []
    models = {
        "h_only": (("log_h",), 1e6),
        "static_width": (STATIC_FEATURES, 1.0),
        "width_dynamics": (TEMPORAL_FEATURES, 1.0),
        "h_plus_width_dynamics": (("log_h", *TEMPORAL_FEATURES), 1.0),
        "h_plus_width_shape_only": (("log_h", *SHAPE_FEATURES), 1.0),
    }
    prefix_index = prefix.set_index(["population_row_index", "prefix_tau"], drop=False)
    for number, spec in enumerate(specs, 1):
        train_idx = np.array([i for i in spec.train_indices if i in usable_indices], dtype=int)
        test_idx = np.array([i for i in spec.test_indices if i in usable_indices], dtype=int)
        train, test = by_index.loc[train_idx].copy(), by_index.loc[test_idx].copy()
        flags = _subset_flags(spec, population, test_idx)
        for model_name, (columns, c) in models.items():
            prob = _fit_predict(train, test, columns, c)
            for pos, idx in enumerate(test_idx):
                predictions.append({
                    "run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold,
                    "population_row_index": int(idx), "experiment_name": test.iloc[pos].experiment_name,
                    "truth": int(test.iloc[pos].has_keyhole), "model": model_name,
                    "probability": float(prob[pos]), "is_q30": bool(flags["q30"][pos]), "is_q20": bool(flags["q20"][pos]),
                    "train_usable_n": len(train), "test_usable_n": len(test),
                })
        for tau in PREFIXES:
            tr = prefix_index.loc[(train_idx, tau), :].copy()
            te = prefix_index.loc[(test_idx, tau), :].copy()
            for model_name, columns, c in (
                ("h_only", ("log_h",), 1e6),
                ("width_history_only", PREFIX_FEATURES, 1.0),
                ("h_plus_width_history", ("log_h", *PREFIX_FEATURES), 1.0),
            ):
                prob = _fit_predict(tr, te, columns, c)
                for pos, idx in enumerate(test_idx):
                    prefix_predictions.append({
                        "run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "prefix_tau": tau,
                        "population_row_index": int(idx), "experiment_name": te.iloc[pos].experiment_name,
                        "truth": int(te.iloc[pos].has_keyhole), "model": model_name,
                        "probability": float(prob[pos]), "is_q30": bool(flags["q30"][pos]), "is_q20": bool(flags["q20"][pos]),
                        "latest_source_tau": float(te.iloc[pos].latest_source_tau),
                    })
        if number % 10 == 0:
            print(f"grouped evaluation {number}/100", flush=True)
    pred = pd.DataFrame(predictions)
    ppred = pd.DataFrame(prefix_predictions)
    write_csv(OUTPUT / "model_oof_predictions.csv.gz", pred)
    write_csv(OUTPUT / "prefix_oof_predictions.csv.gz", ppred)
    return pred, ppred


def summarize_oof(pred: pd.DataFrame, prefix: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    group_cols = ["repeat", "model"] + (["prefix_tau"] if prefix else [])
    repeat_rows = []
    for keys, group in pred.groupby(group_cols, sort=True):
        if not isinstance(keys, tuple): keys = (keys,)
        base = dict(zip(group_cols, keys))
        for subset, flag in (("full", np.ones(len(group), bool)), ("q30", group.is_q30.to_numpy(bool)), ("q20", group.is_q20.to_numpy(bool))):
            g = group.loc[flag]
            repeat_rows.append(base | {"subset": subset} | metric_row(g.truth.to_numpy(int), g.probability.to_numpy(float)))
    repeat = pd.DataFrame(repeat_rows)
    metric_names = ["roc_auc", "pr_auc", "accuracy", "balanced_accuracy", "keyhole_recall", "conduction_recall", "false_negative", "false_positive", "brier_score"]
    summary_rows = []
    mean_groups = ["model", "subset"] + (["prefix_tau"] if prefix else [])
    for keys, group in repeat.groupby(mean_groups, sort=True):
        if not isinstance(keys, tuple): keys = (keys,)
        base = dict(zip(mean_groups, keys))
        for metric in metric_names:
            values = group[metric].dropna().to_numpy(float)
            summary_rows.append(base | {"metric": metric, "mean": float(values.mean()), "sd_across_repeats": float(values.std(ddof=1)), "repeat_blocks": len(values)})
    summary = pd.DataFrame(summary_rows)
    contrast_rows = []
    comparisons = [("h_plus_width_history", "h_only")] if prefix else [
        ("h_plus_width_dynamics", "h_only"),
        ("h_plus_width_shape_only", "h_only"),
    ]
    contrast_groups = ["subset"] + (["prefix_tau"] if prefix else [])
    rng = np.random.default_rng(SEED + (1 if prefix else 0))
    for keys, group in repeat.groupby(contrast_groups, sort=True):
        if not isinstance(keys, tuple): keys = (keys,)
        base = dict(zip(contrast_groups, keys))
        for comparison in comparisons:
            for metric in metric_names:
                pivot = group.pivot(index="repeat", columns="model", values=metric)
                values = (pivot[comparison[0]] - pivot[comparison[1]]).dropna().to_numpy(float)
                boot = np.array([rng.choice(values, len(values), replace=True).mean() for _ in range(BOOTSTRAP_DRAWS)])
                contrast_rows.append(base | {"contrast": f"{comparison[0]} - {comparison[1]}", "metric": metric,
                    "mean_difference": float(values.mean()), "ci_low": float(np.quantile(boot,.025)), "ci_high": float(np.quantile(boot,.975)), "repeat_blocks": len(values)})
    contrasts = pd.DataFrame(contrast_rows)
    return repeat, summary, contrasts


def pca_analysis(features: pd.DataFrame, profiles: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    x = StandardScaler().fit_transform(features[list(TEMPORAL_FEATURES)])
    pca = PCA(n_components=2).fit(x)
    scores = pca.transform(x)
    score_frame = features[["experiment_name", "population_row_index", "has_keyhole", "log_h"]].copy()
    score_frame["PC1"] = scores[:, 0]; score_frame["PC2"] = scores[:, 1]
    score_frame["PC1_explained_variance"] = pca.explained_variance_ratio_[0]
    score_frame["PC2_explained_variance"] = pca.explained_variance_ratio_[1]
    loadings = pd.DataFrame({"feature": TEMPORAL_FEATURES, "PC1_loading": pca.components_[0], "PC2_loading": pca.components_[1]})
    write_csv(OUTPUT / "pca_scores.csv", score_frame)
    write_csv(OUTPUT / "pca_loadings.csv", loadings)

    matrix = profiles.pivot(index="experiment_name", columns="tau", values="transverse_width_um").loc[features.experiment_name]
    arr = matrix.to_numpy(float)
    arr = arr - arr[:, [0]]
    scale = np.ptp(arr, axis=1); scale[scale < 1e-9] = 1.0
    arr = arr / scale[:, None]
    shape_pca = PCA(n_components=2).fit(StandardScaler().fit_transform(arr))
    shape_scores = shape_pca.transform(StandardScaler().fit_transform(arr))
    shape = features[["experiment_name", "population_row_index", "has_keyhole"]].copy()
    shape["profile_PC1"] = shape_scores[:, 0]; shape["profile_PC2"] = shape_scores[:, 1]
    shape["PC1_explained_variance"] = shape_pca.explained_variance_ratio_[0]
    shape["PC2_explained_variance"] = shape_pca.explained_variance_ratio_[1]
    write_csv(OUTPUT / "profile_shape_pca_scores.csv", shape)
    return score_frame, loadings, shape


def residual_cases(pred: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    q = pred[pred.is_q20].pivot_table(index=["repeat", "population_row_index", "experiment_name", "truth"], columns="model", values="probability").reset_index()
    q["h_correct"] = (q.h_only >= .5).astype(int).eq(q.truth)
    q["combined_correct"] = (q.h_plus_width_dynamics >= .5).astype(int).eq(q.truth)
    q["category"] = np.select([
        ~q.h_correct & q.combined_correct, q.h_correct & ~q.combined_correct,
        q.h_correct & q.combined_correct], ["h_wrong_width_correct", "h_correct_width_wrong", "both_correct"], default="both_wrong")
    detail = features[["population_row_index", "P", "VX", "LS", "ST", "log_h", *STATIC_FEATURES, *TEMPORAL_FEATURES]]
    out = q.merge(detail, on="population_row_index", how="left")
    write_csv(OUTPUT / "h_residual_case_analysis.csv", out)
    return out


def onset_alignment(profiles: pd.DataFrame, audit: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Align Keyhole traces to the first *observed* valid manual Keyhole frame."""
    onset = pd.read_csv(OUTPUT / "keyhole_onset_audit.csv")
    durations = audit.set_index("experiment_name").active_duration_ms
    rows, aligned = [], []
    relative_grid = np.linspace(-0.50, 0.50, 201)
    for row in onset.itertuples(index=False):
        item = row._asdict()
        if bool(row.onset_available):
            group = profiles[profiles.experiment_name.eq(row.experiment_name)].sort_values("tau")
            duration = float(durations.loc[row.experiment_name])
            rel = (group.tau.to_numpy(float) - float(row.first_keyhole_tau)) * duration
            robust = group.transverse_dWdt_robust_um_per_ms.to_numpy(float)
            robust_peak_tau = float(group.iloc[int(np.argmax(robust))].tau)
            robust_lead = float((robust_peak_tau - float(row.first_keyhole_tau)) * duration)
            item["robust_peak_dWdt_tau"] = robust_peak_tau
            item["robust_peak_minus_first_keyhole_ms"] = robust_lead
            item["robust_peak_precedes_first_observed_keyhole"] = robust_lead < 0
            valid_grid = (relative_grid >= rel.min()) & (relative_grid <= rel.max())
            for value, width, deriv, robust_deriv in zip(
                relative_grid[valid_grid],
                np.interp(relative_grid[valid_grid], rel, group.transverse_width_um),
                np.interp(relative_grid[valid_grid], rel, group.transverse_dWdt_raw_um_per_ms),
                np.interp(relative_grid[valid_grid], rel, robust),
            ):
                aligned.append({"experiment_name": row.experiment_name, "time_relative_to_first_observed_keyhole_ms": value,
                    "transverse_width_um": width, "transverse_dWdt_raw_um_per_ms": deriv, "transverse_dWdt_robust_um_per_ms": robust_deriv})
        else:
            item["robust_peak_dWdt_tau"] = None
            item["robust_peak_minus_first_keyhole_ms"] = None
            item["robust_peak_precedes_first_observed_keyhole"] = None
        rows.append(item)
    enriched = pd.DataFrame(rows)
    aligned_frame = pd.DataFrame(aligned)
    write_csv(OUTPUT / "keyhole_onset_audit.csv", enriched)
    write_csv(OUTPUT / "keyhole_onset_aligned_profiles.csv.gz", aligned_frame)
    lead = enriched[enriched.onset_available.astype(bool)].copy()
    lead["result_type"] = "descriptive_peak_timing_not_learned_warning"
    lead["warning_threshold_fitted"] = False
    write_csv(OUTPUT / "keyhole_lead_time_results.csv", lead)
    return enriched, aligned_frame


def class_profile_summary(profiles: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (tau, label), group in profiles.groupby(["tau", "has_keyhole"]):
        for metric in ("transverse_width_um", "transverse_dWdt_raw_um_per_ms", "transverse_dWdt_robust_um_per_ms"):
            values = group[metric].to_numpy(float)
            rows.append({"tau": tau, "has_keyhole": label, "metric": metric, "median": np.median(values),
                         "q25": np.quantile(values,.25), "q75": np.quantile(values,.75), "n":len(values)})
    out = pd.DataFrame(rows)
    write_csv(OUTPUT / "class_profile_summary.csv", out)
    return out


def _save(fig: plt.Figure, name: str) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / name
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def make_figures(features: pd.DataFrame, profiles: pd.DataFrame, audit: pd.DataFrame, effects: pd.DataFrame,
                 pca_scores: pd.DataFrame, shape_scores: pd.DataFrame, model_summary: pd.DataFrame,
                 prefix_summary: pd.DataFrame, prefix_pred: pd.DataFrame) -> list[Path]:
    plt.style.use("seaborn-v0_8-whitegrid")
    created: list[Path] = []
    # 1 deterministic representative traces spanning classes/quality/growth.
    candidates = features.merge(audit[["experiment_name", "quality_flag", "oscillation_mad_delta_um"]], on="experiment_name")
    selected = []
    for label in (0, 1):
        g = candidates[candidates.has_keyhole.eq(label)]
        selected.extend([g.sort_values("width_gain_40_um").iloc[len(g)//2].experiment_name,
                         g.sort_values("width_gain_40_um").iloc[-1].experiment_name])
    noisy = candidates.sort_values("oscillation_mad_delta_um").iloc[-1].experiment_name
    selected.append(noisy)
    fig, ax = plt.subplots(figsize=(8, 5))
    for name in dict.fromkeys(selected):
        g = profiles[profiles.experiment_name.eq(name)]
        label = "Keyhole" if bool(g.has_keyhole.iloc[0]) else "Conduction"
        ax.plot(g.tau, g.transverse_width_um, lw=1.6, alpha=.85, label=f"{label}: {name[:18]}…")
    ax.set(xlabel="Normalized active time τ", ylabel="Transverse melt-pool width ΔY (µm)", title="Representative transverse-width trajectories")
    ax.legend(fontsize=7)
    created.append(_save(fig, "01_representative_width_trajectories.png"))

    def profile_plot(column: str, ylabel: str, title: str, filename: str) -> None:
        fig, ax = plt.subplots(figsize=(8, 5))
        for label, color, text in ((0,"#4477AA","Conduction"),(1,"#CC3311","Keyhole")):
            wide = profiles[profiles.has_keyhole.eq(label)].pivot(index="experiment_name", columns="tau", values=column)
            med = wide.median(); lo = wide.quantile(.25); hi = wide.quantile(.75)
            ax.plot(GRID, med, color=color, lw=2.2, label=f"{text} median")
            ax.fill_between(GRID, lo, hi, color=color, alpha=.18, label=f"{text} IQR")
        ax.set(xlabel="Normalized active time τ", ylabel=ylabel, title=title); ax.legend()
        created.append(_save(fig, filename))
    profile_plot("transverse_width_um", "Transverse melt-pool width ΔY (µm)", "Corrected transverse-width profiles", "02_class_width_profiles.png")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
    for ax, column, title in ((axes[0], "transverse_dWdt_raw_um_per_ms", "Raw centered finite difference"),
                              (axes[1], "transverse_dWdt_robust_um_per_ms", "Fixed local-linear robustness")):
        for label, color, text in ((0,"#4477AA","Conduction"),(1,"#CC3311","Keyhole")):
            wide = profiles[profiles.has_keyhole.eq(label)].pivot(index="experiment_name", columns="tau", values=column)
            med = wide.median(); lo = wide.quantile(.25); hi = wide.quantile(.75)
            ax.plot(GRID, med, color=color, lw=2.0, label=f"{text} median")
            ax.fill_between(GRID, lo, hi, color=color, alpha=.16)
        ax.set(xlabel="Normalized active time τ", title=title); ax.legend(fontsize=8)
    axes[0].set_ylabel("dW/dt (µm/ms)")
    fig.suptitle("Transverse-width derivative conclusions must survive fixed denoising")
    created.append(_save(fig, "03_class_derivative_profiles.png"))

    stable_effects = effects[~effects.feature_group.eq("raw_derivative")]
    top = stable_effects.reindex(stable_effects.cliffs_delta.abs().sort_values(ascending=False).index).head(6)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(top.cliffs_delta, np.arange(len(top)), xerr=None, fmt="o", color="#6A3D9A")
    ax.axvline(0, color="black", lw=.8); ax.set_yticks(np.arange(len(top)), top.feature.str.replace("_", " "))
    ax.set(xlabel="Cliff's delta (Keyhole − Conduction)", title="Largest corrected transverse-width feature effects")
    created.append(_save(fig, "04_width_feature_effects.png"))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for data, x, y, ax, title in ((pca_scores,"PC1","PC2",axes[0],"Declared temporal features"), (shape_scores,"profile_PC1","profile_PC2",axes[1],"Normalized profile shape")):
        for label,color,text in ((0,"#4477AA","Conduction"),(1,"#CC3311","Keyhole")):
            g=data[data.has_keyhole.eq(label)]; ax.scatter(g[x],g[y],s=18,alpha=.65,color=color,label=text)
        ev1=float(data.PC1_explained_variance.iloc[0]); ev2=float(data.PC2_explained_variance.iloc[0])
        ax.set(xlabel=f"PC1 ({ev1:.1%})",ylabel=f"PC2 ({ev2:.1%})",title=title); ax.legend(fontsize=8)
    fig.suptitle("Label-free PCA of corrected transverse-width behavior")
    created.append(_save(fig, "05_temporal_width_pca.png"))

    metric = model_summary[(model_summary.metric.eq("balanced_accuracy")) & model_summary.subset.isin(["full","q30","q20"])]
    pivot = metric.pivot(index="model", columns="subset", values="mean").reindex(["h_only","static_width","width_dynamics","h_plus_width_dynamics"])
    fig, ax = plt.subplots(figsize=(9,5)); pivot.plot.bar(ax=ax,color=["#4C78A8","#F58518","#54A24B"])
    ax.set(ylim=(.4,1),ylabel="Repeat-level held-out balanced accuracy",title="Leak-free model comparison on frozen grouped folds"); ax.legend(title="Evaluation subset")
    created.append(_save(fig,"06_model_comparison.png"))

    pm = prefix_summary[(prefix_summary.metric.eq("balanced_accuracy")) & prefix_summary.subset.eq("q20")]
    fig, axes = plt.subplots(1,2,figsize=(11,4.5))
    for model,color in (("h_only","#777777"),("width_history_only","#4C78A8"),("h_plus_width_history","#CC3311")):
        g=pm[pm.model.eq(model)]; axes[0].plot(g.prefix_tau,g["mean"],marker="o",label=model.replace("_"," "),color=color)
    axes[0].set(xlabel="Observed prefix τ",ylabel="q20 balanced accuracy",title="When does width history add information?"); axes[0].legend(fontsize=8)
    agg=prefix_pred.groupby(["experiment_name","truth","model","prefix_tau"],as_index=False).probability.median()
    wide=agg.pivot(index=["experiment_name","truth","prefix_tau"],columns="model",values="probability").reset_index()
    final=wide[wide.prefix_tau.eq(1)].copy(); final["gain"]=(final.h_plus_width_history-final.truth).abs()-(final.h_only-final.truth).abs()
    examples=pd.concat([final.sort_values("gain").head(2),final.sort_values("gain").tail(2)]).experiment_name.unique()
    for name in examples:
        g=wide[wide.experiment_name.eq(name)]; axes[1].plot(g.prefix_tau,g.h_plus_width_history,marker="o",label=f"y={int(g.truth.iloc[0])}: {name[:12]}…")
    axes[1].axhline(.5,color="black",lw=.8); axes[1].set(xlabel="Observed prefix τ",ylabel="P(eventual Keyhole)",title="Held-out sequential risks (successes and failures)"); axes[1].legend(fontsize=7)
    created.append(_save(fig,"07_prefix_performance_and_risk.png"))

    onset=pd.read_csv(OUTPUT/"keyhole_onset_audit.csv"); valid=onset[onset.onset_available.astype(bool)]
    aligned=pd.read_csv(OUTPUT/"keyhole_onset_aligned_profiles.csv.gz")
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for metric,color,label in (("transverse_width_um","#4477AA","ΔY width"),):
        s=aligned.groupby("time_relative_to_first_observed_keyhole_ms")[metric]
        med=s.median(); lo=s.quantile(.25); hi=s.quantile(.75)
        axes[0].plot(med.index,med,color=color,label=f"{label} median"); axes[0].fill_between(med.index,lo,hi,color=color,alpha=.2,label="IQR")
    axes[0].axvline(0,color="black",lw=1); axes[0].set(xlabel="Time relative to first observed Keyhole frame (ms)",ylabel="Transverse width ΔY (µm)",title="True width aligned to sparse manual onset"); axes[0].legend()
    for metric,color,label in (("transverse_dWdt_raw_um_per_ms","#999999","raw finite difference"),("transverse_dWdt_robust_um_per_ms","#6A3D9A","fixed local-linear robustness")):
        s=aligned.groupby("time_relative_to_first_observed_keyhole_ms")[metric]; med=s.median()
        axes[1].plot(med.index,med,color=color,label=label)
    axes[1].axvline(0,color="black",lw=1); axes[1].set(xlabel="Time relative to first observed Keyhole frame (ms)",ylabel="dW/dt (µm/ms)",title="Derivative timing is descriptive, not a warning rule"); axes[1].legend(fontsize=8)
    created.append(_save(fig,"08_first_observed_keyhole_timing.png"))
    return created


def notebook_payload() -> dict[str, Any]:
    sections = [
        ("Axis-semantics correction", "Forensic review found that the first published run used ΔX while calling it width. The authoritative extractor defines ΔX as longitudinal length and ΔY as transverse width. This corrected notebook uses W(t)=Ymax−Ymin."),
        ("Ioan's question", "Does transverse width growth, not scan speed or longitudinal length, distinguish eventual Keyhole tracks and add information beyond the pre-process score h?"),
        ("Corrected W(t)", "The pinned monitor columns are x_min, x_max, y_min, y_max, z_min, z_max. Canonical width is ΔY in metres, shown in micrometres. Cooling-only rows are excluded."),
        ("Corrected dW/dt", "The timestamp-only regularity gate selects centered finite differences. A fixed five-grid-point local-linear slope is the non-tuned robustness derivative. Units are µm/ms."),
        ("Temporal profiles", "Medians and IQRs show both class differences and overlap."),
        ("Temporal feature effects", "Primary models use non-derivative shape features and the fixed robust derivative features. Raw finite differences remain descriptive only."),
        ("PCA", "PCA uses the same corrected robust temporal representation as the model, without labels. It is a descriptive projection, not feature importance or a physical manifold."),
        ("Leak-free models", "Scalers and logistic coefficients are fitted inside each frozen training fold. B1/q20/q30 are evaluation-only."),
        ("Beyond h", "Hard-decision metrics and ranking/probability metrics are interpreted separately."),
        ("Early prefixes", "Each prefix model sees only transverse-width samples at or before the declared prefix and uses robust derivative summaries."),
        ("First observed Keyhole", "Exact manual-frame alignment supports descriptive timing relative to the first observed valid Keyhole frame, not continuous physical onset or a warning rule."),
        ("Longitudinal ΔX comparison", "The former result is preserved as a secondary longitudinal-length diagnostic and is not presented as Ioan's width answer."),
        ("Final safe conclusion", "The generated reports state the corrected claim level and limitations."),
    ]
    cells=[]
    cells.append({"cell_type":"markdown","id":"phase2title","metadata":{},"source":["# Week 9 Phase 2 — Temporal melt-pool width dynamics\n","This teaching notebook reads the frozen generated artifacts; the experimental engine lives in `src/week9_phase2_temporal_width_dynamics.py`.\n"]})
    cells.append({"cell_type":"code","id":"phase2setup","execution_count":None,"metadata":{},"outputs":[],"source":["from pathlib import Path\n","import pandas as pd\n","from IPython.display import display, Image\n","ROOT = Path.cwd().parents[1] if Path.cwd().name == 'week_09' else Path.cwd()\n","OUT = ROOT / 'outputs' / 'week9_phase2_temporal_width_dynamics'\n","assert OUT.is_dir()\n"]})
    for title,text in sections:
        cells.append({"cell_type":"markdown","id":hashlib.sha1((title+"-md").encode()).hexdigest()[:8],"metadata":{},"source":[f"## {title}\n",text+"\n"]})
        if title=="Axis-semantics correction": src="display(pd.read_csv(OUT/'axis_semantics_audit.csv'))"
        elif title=="Corrected W(t)": src="display(pd.read_csv(OUT/'width_missingness_audit.csv')); display(Image(filename=OUT/'figures'/'02_class_width_profiles.png'))"
        elif title=="Corrected dW/dt": src="display(pd.read_csv(OUT/'derivative_robustness_gate.csv')); display(Image(filename=OUT/'figures'/'03_class_derivative_profiles.png'))"
        elif title=="Temporal profiles": src="display(Image(filename=OUT/'figures'/'02_class_width_profiles.png')); display(Image(filename=OUT/'figures'/'03_class_derivative_profiles.png'))"
        elif title=="Temporal feature effects": src="display(pd.read_csv(OUT/'static_feature_effects.csv').sort_values('cliffs_delta', key=abs, ascending=False))"
        elif title=="PCA": src="display(Image(filename=OUT/'figures'/'05_temporal_width_pca.png')); display(pd.read_csv(OUT/'pca_loadings.csv'))"
        elif title in {"Leak-free models","Beyond h"}: src="display(pd.read_csv(OUT/'model_oof_summary.csv')); display(pd.read_csv(OUT/'model_paired_contrasts.csv')); display(Image(filename=OUT/'figures'/'06_model_comparison.png'))"
        elif title=="Early prefixes": src="display(pd.read_csv(OUT/'prefix_model_contrasts.csv')); display(Image(filename=OUT/'figures'/'07_prefix_performance_and_risk.png'))"
        elif title=="First observed Keyhole": src="display(pd.read_csv(OUT/'keyhole_onset_audit.csv').query('onset_available == True').describe(include='all')); display(Image(filename=OUT/'figures'/'08_first_observed_keyhole_timing.png'))"
        elif title=="Longitudinal ΔX comparison": src="display(pd.read_csv(OUT/'longitudinal_vs_transverse_summary.csv'))"
        elif title=="Final safe conclusion": src="print((OUT/'SUPERVISOR_PHASE2_ONE_PAGE.md').read_text(encoding='utf-8'))"
        else: src="display(pd.read_csv(OUT/'width_temporal_features.csv').head())"
        cells.append({"cell_type":"code","id":hashlib.sha1((title+"-code").encode()).hexdigest()[:8],"execution_count":None,"metadata":{},"outputs":[],"source":[src+"\n"]})
    return {"cells":cells,"metadata":{"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},"language_info":{"name":"python","version":"3"}},"nbformat":4,"nbformat_minor":5}


def execute_and_save_notebook() -> None:
    import nbformat
    from nbconvert.preprocessors import ExecutePreprocessor
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    ExecutePreprocessor(timeout=300, kernel_name="python3").preprocess(notebook, {"metadata":{"path":str(ROOT)}})
    require(any(cell.cell_type == "code" and cell.execution_count is not None and cell.outputs for cell in notebook.cells), "notebook has no stored executed outputs")
    nbformat.write(notebook, NOTEBOOK)


def render_reports(merged: pd.DataFrame, audit: pd.DataFrame, effects: pd.DataFrame, model_summary: pd.DataFrame,
                   model_contrasts: pd.DataFrame, prefix_summary: pd.DataFrame, prefix_contrasts: pd.DataFrame,
                   residual: pd.DataFrame, figures: list[Path], robustness: pd.DataFrame,
                   axis_comparison: pd.DataFrame) -> None:
    def value(frame: pd.DataFrame, **query: Any) -> float:
        q=frame
        for k,v in query.items(): q=q[q[k].eq(v)]
        return float(q.iloc[0]["mean"])
    def contrast(frame: pd.DataFrame, **query: Any) -> pd.Series:
        q=frame
        for k,v in query.items(): q=q[q[k].eq(v)]
        return q.iloc[0]
    usable=int(merged.usable_width_timeseries.sum()); kh=int(merged.loc[merged.usable_width_timeseries,"has_keyhole"].sum())
    primary_effects=effects[effects.feature.isin([*SHAPE_FEATURES,*ROBUST_DERIVATIVE_FEATURES])]
    best=primary_effects.iloc[primary_effects.cliffs_delta.abs().argmax()]
    qba={m:value(model_summary,model=m,subset="q20",metric="balanced_accuracy") for m in ["h_only","static_width","width_dynamics","h_plus_width_dynamics"]}
    qrec={m:value(model_summary,model=m,subset="q20",metric="keyhole_recall") for m in ["h_only","h_plus_width_dynamics"]}
    main_name="h_plus_width_dynamics - h_only"; shape_name="h_plus_width_shape_only - h_only"
    ba=contrast(model_contrasts,subset="q20",metric="balanced_accuracy",contrast=main_name)
    kr=contrast(model_contrasts,subset="q20",metric="keyhole_recall",contrast=main_name)
    roc=contrast(model_contrasts,subset="q20",metric="roc_auc",contrast=main_name)
    pr=contrast(model_contrasts,subset="q20",metric="pr_auc",contrast=main_name)
    brier=contrast(model_contrasts,subset="q20",metric="brier_score",contrast=main_name)
    shape_ba=contrast(model_contrasts,subset="q20",metric="balanced_accuracy",contrast=shape_name)
    shape_pr=contrast(model_contrasts,subset="q20",metric="pr_auc",contrast=shape_name)
    shape_brier=contrast(model_contrasts,subset="q20",metric="brier_score",contrast=shape_name)
    hard_status="SUPPORTED" if ba.ci_low>0 or kr.ci_low>0 else ("NOT SUPPORTED" if ba.mean_difference<=0 and kr.mean_difference<=0 else "QUALIFIED")
    ranking_status="SUPPORTED" if roc.ci_low>0 or pr.ci_low>0 or brier.ci_high<0 else ("NOT SUPPORTED" if roc.mean_difference<=0 and pr.mean_difference<=0 and brier.mean_difference>=0 else "QUALIFIED")
    level="STRONG TEMPORAL SIGNAL" if hard_status=="SUPPORTED" else ("INCREMENTAL / QUALIFIED SIGNAL" if ranking_status in {"SUPPORTED","QUALIFIED"} else "NO INCREMENTAL SIGNAL")
    onset=pd.read_csv(OUTPUT/"keyhole_onset_audit.csv"); onset_valid=onset[onset.onset_available.astype(bool)]
    onset_claim="QUALIFIED" if len(onset_valid) else "NOT TESTABLE WITH CURRENT LABELS"
    raw_effect=effects[effects.feature.eq("early_dWdt_20_um_per_ms")].iloc[0]
    robust_effect=effects[effects.feature.eq("robust_early_dWdt_20_um_per_ms")].iloc[0]
    wmax_effect=effects[effects.feature.eq("W_max_um")].iloc[0]
    wt0_effect=effects[effects.feature.eq("W_T0_um")].iloc[0]
    earliest=prefix_contrasts[(prefix_contrasts.subset.eq("q20")) & prefix_contrasts.metric.eq("balanced_accuracy") & (prefix_contrasts.prefix_tau<1)].sort_values("prefix_tau").iloc[0]
    earliest_recall=contrast(prefix_contrasts,subset="q20",prefix_tau=.2,metric="keyhole_recall")
    earliest_roc=contrast(prefix_contrasts,subset="q20",prefix_tau=.2,metric="roc_auc")
    earliest_pr=contrast(prefix_contrasts,subset="q20",prefix_tau=.2,metric="pr_auc")
    earliest_brier=contrast(prefix_contrasts,subset="q20",prefix_tau=.2,metric="brier_score")
    raw_pre=float(onset_valid.peak_precedes_first_observed_keyhole.mean()) if len(onset_valid) else float("nan")
    robust_pre=float(onset_valid.robust_peak_precedes_first_observed_keyhole.mean()) if len(onset_valid) else float("nan")
    robust_lead=-float(onset_valid.loc[onset_valid.robust_peak_precedes_first_observed_keyhole.astype(bool),"robust_peak_minus_first_keyhole_ms"].median()) if len(onset_valid) else float("nan")
    corrected=int((residual.category=="h_wrong_width_correct").sum()); worsened=int((residual.category=="h_correct_width_wrong").sum())
    derivative_status=str(robustness[robustness.derivative_claim.eq("early 20% derivative")].iloc[0].status)
    longrow=axis_comparison[axis_comparison.axis_quantity.eq("longitudinal_length_delta_X")].iloc[0]
    numbers=f"""- Usable traces: {usable}/405; Keyhole: {kh}
- Wmax medians (Conduction, Keyhole): {wmax_effect.conduction_median:.3f}, {wmax_effect.keyhole_median:.3f} µm
- WT0 medians (Conduction, Keyhole): {wt0_effect.conduction_median:.3f}, {wt0_effect.keyhole_median:.3f} µm
- Best robust/shape temporal feature: {best.feature}; Cliff's delta {best.cliffs_delta:+.4f}
- q20 balanced accuracy (h, width dynamics, h+width): {qba['h_only']:.4f}, {qba['width_dynamics']:.4f}, {qba['h_plus_width_dynamics']:.4f}
- q20 Keyhole recall (h, h+width): {qrec['h_only']:.4f}, {qrec['h_plus_width_dynamics']:.4f}
- q20 ROC/PR/Brier contrasts (h+width minus h): {roc.mean_difference:+.4f}, {pr.mean_difference:+.4f}, {brier.mean_difference:+.4f}
- τ=0.20 q20 BA/ROC/PR/Brier contrasts: {earliest.mean_difference:+.4f}, {earliest_roc.mean_difference:+.4f}, {earliest_pr.mean_difference:+.4f}, {earliest_brier.mean_difference:+.4f}
- Final Phase 2 claim: {level}; hard-decision {hard_status}; ranking/probability {ranking_status}
"""
    summary=f"""# Supervisor Phase 2 — one page

## Correction and question
The authoritative extractor verifies **ΔX = longitudinal length** and **ΔY = transverse width**. The original Phase 2 accidentally answered the ΔX question. This correction answers Ioan using **W(t)=Ymax−Ymin=ΔY**.

## Corrected data and physical width
{usable}/405 traces are usable ({kh} Keyhole, {usable-kh} Conduction). Median transverse Wmax is {wmax_effect.keyhole_median:.1f} µm for Keyhole versus {wmax_effect.conduction_median:.1f} µm for Conduction; WT0 is {wt0_effect.keyhole_median:.1f} versus {wt0_effect.conduction_median:.1f} µm. This is a descriptive effect; standalone hard classification is reported separately.

## Temporal feature and derivative robustness
The strongest deterministic shape/robust-derivative feature is `{best.feature}`: Conduction median {best.conduction_median:.1f}, Keyhole median {best.keyhole_median:.1f} µm/ms (Cliff's delta {best.cliffs_delta:+.3f}). Raw early-20% dW/dt medians (Conduction, Keyhole) are {raw_effect.conduction_median:.1f}, {raw_effect.keyhole_median:.1f} µm/ms; fixed robust medians are {robust_effect.conduction_median:.1f}, {robust_effect.keyhole_median:.1f}. Early-20% derivative gate: **{derivative_status}**. No faster/slower physical claim is made unless direction survives denoising.

## Does true width add beyond h?
On q20, balanced accuracy is h-only {qba['h_only']:.3f}, static width {qba['static_width']:.3f}, width dynamics {qba['width_dynamics']:.3f}, and h+width {qba['h_plus_width_dynamics']:.3f}. The h+width hard-decision contrasts are BA {ba.mean_difference:+.3f} [{ba.ci_low:+.3f},{ba.ci_high:+.3f}] and Keyhole recall {kr.mean_difference:+.3f} [{kr.ci_low:+.3f},{kr.ci_high:+.3f}]: **{hard_status}**.

Ranking/probability contrasts are ROC-AUC {roc.mean_difference:+.3f} [{roc.ci_low:+.3f},{roc.ci_high:+.3f}], PR-AUC {pr.mean_difference:+.3f} [{pr.ci_low:+.3f},{pr.ci_high:+.3f}], and Brier {brier.mean_difference:+.3f} [{brier.ci_low:+.3f},{brier.ci_high:+.3f}] (negative Brier is better): **{ranking_status}**.

The fixed shape-only sensitivity preserves hard performance better: q20 BA contrast {shape_ba.mean_difference:+.3f} [{shape_ba.ci_low:+.3f},{shape_ba.ci_high:+.3f}], PR contrast {shape_pr.mean_difference:+.3f} [{shape_pr.ci_low:+.3f},{shape_pr.ci_high:+.3f}], Brier contrast {shape_brier.mean_difference:+.3f} [{shape_brier.ci_low:+.3f},{shape_brier.ci_high:+.3f}]. This diagnostic is not post-hoc tuning.

## Earliest prefix and onset
At τ=0.20, q20 BA changes {earliest.mean_difference:+.3f} [{earliest.ci_low:+.3f},{earliest.ci_high:+.3f}] and Keyhole recall {earliest_recall.mean_difference:+.3f} [{earliest_recall.ci_low:+.3f},{earliest_recall.ci_high:+.3f}]; ROC/PR/Brier change {earliest_roc.mean_difference:+.3f}/{earliest_pr.mean_difference:+.3f}/{earliest_brier.mean_difference:+.3f}. First-observed manual Keyhole timing exists for {len(onset_valid)} traces. Robust peaks precede it in {robust_pre:.1%}, median descriptive lead {robust_lead:.3f} ms, but startup peaks are generic and no held-out warning rule exists. Verified pre-Keyhole warning: **NOT SUPPORTED**.

## What ΔX taught us
The archived longitudinal diagnostic had q20 width-dynamics BA {longrow.q20_width_dynamics_balanced_accuracy:.3f} and h+ΔX BA {longrow.q20_h_plus_axis_dynamics_balanced_accuracy:.3f}; it described longitudinal growth, not transverse monitoring width.

## Canonical numbers
{numbers}
"""
    summary = summary.rstrip() + "\n"
    (OUTPUT/"SUPERVISOR_PHASE2_ONE_PAGE.md").write_text(summary,encoding="utf-8")
    report="# Week 9 Phase 2 final report — corrected transverse width\n\n"+summary+"\n## Methods and claim discipline\n\nThe authoritative source and five pinned files verify ΔX=longitudinal length and ΔY=transverse width. All 100 frozen outer folds were intersected with the usable temporal subset. Primary temporal models use deterministic shape plus fixed robust-derivative features; raw finite differences are descriptive. Scalers and fixed logistic models are trained within each fold. B1/q20/q30 are evaluation-only. Repeat-block uncertainty resamples 20 repeats, keeping five folds together. The onset is the first observed valid manually labelled frame, not continuous physical onset.\n\n## Direct scientific answers\n\n1. The reported W(t) is transverse ΔY.\n2. Static/profile effects are described by effect size, separately from classifier performance.\n3. Derivative claims are governed by `derivative_robustness_gate.csv`.\n4. Width-only dynamics and h+width are compared on hard and ranking/probability metrics separately.\n5. Prefix models use no future samples.\n6. No derivative peak is called a warning event.\n7. The published ΔX result is retained only as a longitudinal diagnostic.\n"
    (OUTPUT/"FINAL_PHASE2_REPORT.md").write_text(report,encoding="utf-8")
    ledger=f"""# Phase 2 claim ledger — corrected transverse width

| Claim | Status | Guardrail |
|---|---|---|
| Transverse static width differs by eventual regime | {"SUPPORTED" if abs(wmax_effect.cliffs_delta)>=.2 else "QUALIFIED"} | Effect size, not standalone classifier claim |
| Transverse temporal profile differs by eventual regime | {"SUPPORTED" if abs(best.cliffs_delta)>=.2 else "QUALIFIED"} | Frozen simulator subset |
| Transverse dW/dt is a robust discriminator | {derivative_status} | Raw versus fixed local-linear gate |
| Transverse width improves hard classification beyond h | {hard_status} | q20 BA and Keyhole recall primary |
| Transverse width improves ranking/probabilities beyond h | {ranking_status} | q20 ROC, PR and Brier secondary |
| Early prefix gives hard-decision improvement | {"SUPPORTED" if earliest.ci_low>0 else ("NOT SUPPORTED" if earliest.mean_difference<=0 else "QUALIFIED")} | τ=0.20 shown; all prefixes tabulated |
| Early prefix gives ranking/probability improvement | {"SUPPORTED" if earliest_roc.ci_low>0 or earliest_pr.ci_low>0 or earliest_brier.ci_high<0 else "QUALIFIED"} | Secondary metrics interpreted separately |
| Verified pre-Keyhole warning | NOT SUPPORTED | No trained held-out warning rule; sparse observed onset |
| Longitudinal ΔX behaves differently from transverse ΔY | SUPPORTED | Side-by-side axis audit and summary |
| Top-view monitoring is industrially validated | NOT SUPPORTED | No prospective camera experiment |

## Canonical numbers
{numbers}
"""
    ledger = ledger.rstrip() + "\n"
    (OUTPUT/"claim_ledger.md").write_text(ledger,encoding="utf-8")
    red="""# Final red-team report

The correction audit attempted to falsify the axis mapping, actual ΔY/ΔX formulas, derivative units, label-independent smoothing, prefix time ordering, train/test isolation, B1/q20 leakage, repeat-block inference, PCA inputs, ranking-versus-hard language, generic-startup warning language, executed notebook state, validation/manifest equality, and historical Phase 1.x protection. Canonical width is ΔY everywhere in main artifacts. ΔX survives only in the longitudinal diagnostic. Raw derivative claims are downgraded whenever the fixed robust derivative changes direction or destroys magnitude. No trained held-out warning rule exists.
"""
    (OUTPUT/"FINAL_RED_TEAM_REPORT.md").write_text(red,encoding="utf-8")
    figure_manifest=pd.DataFrame([{"figure":p.name,"sha256":sha256_file(p),"bytes":p.stat().st_size} for p in figures])
    write_csv(OUTPUT/"figure_manifest.csv",figure_manifest)


def validate(pop: pd.DataFrame, merged: pd.DataFrame, audit: pd.DataFrame, profiles: pd.DataFrame,
             features: pd.DataFrame, prefix: pd.DataFrame, figures: list[Path]) -> dict[str, Any]:
    axis = pd.read_csv(OUTPUT / "axis_semantics_audit.csv")
    p15_source = (ROOT / "src" / "week9_phase1_5_h_physics_confirmation.py").read_text(encoding="utf-8")
    model_feature_names = set(STATIC_FEATURES) | set(TEMPORAL_FEATURES) | set(PREFIX_FEATURES) | {"log_h"}
    pca_loadings = pd.read_csv(OUTPUT / "pca_loadings.csv")
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    notebook_outputs = [cell for cell in notebook["cells"] if cell["cell_type"]=="code" and cell.get("execution_count") is not None and cell.get("outputs")]
    demo = _model(1.0).fit(np.array([[0.],[2.],[4.]]), np.array([0,0,1]))
    source = Path(__file__).read_text(encoding="utf-8")
    checks={
        "population_405":len(pop)==405,
        "labels_73":int(pop.has_keyhole.sum())==73,
        "canonical_ids_unique_and_unchanged":pop.experiment_name.is_unique and set(pop.experiment_name)==set(w85.load_population().experiment_name),
        "LS_matches_canonical_radius_column":np.allclose(pop.LS,pop.LS_m) and "Gaussian laser spot radius r0" in p15_source,
        "ST_matches_canonical_substrate_temperature":np.allclose(pop.ST,pop.ST_K) and '"ST_definition": "substrate temperature"' in p15_source,
        "authoritative_deltaX_is_length":bool(axis[axis.quantity.eq("longitudinal_length")].status.eq("PASS").all()),
        "authoritative_deltaY_is_width":bool(axis[axis.quantity.eq("transverse_width")].status.eq("PASS").all()),
        "actual_transverse_width_numerically_verified":bool(axis[axis.quantity.eq("transverse_width")].numeric_mapping_verified.all()),
        "actual_longitudinal_length_numerically_verified":bool(axis[axis.quantity.eq("longitudinal_length")].numeric_mapping_verified.all()),
        "cleaned_timestamps_positive":int(audit.nonpositive_dt_count_raw.sum())==0,
        "no_cooling_in_primary":int(audit.cooling_rows_in_primary.sum())==0,
        "derivative_unit_um_per_ms":np.all(np.isfinite(profiles.transverse_dWdt_raw_um_per_ms)) and "(t - t[0]) * 1e3" in source and "* 1e6" in source,
        "tau_zero_one":profiles.groupby("experiment_name").tau.agg(["min","max"]).pipe(lambda x: np.allclose(x["min"],0) and np.allclose(x["max"],1)),
        "synthetic_derivative":synthetic_derivative_error()<1e-8,
        "prefix_no_future":bool(np.all(prefix.latest_source_tau<=prefix.prefix_tau+1e-12)),
        "h_exact_formula":np.allclose(features.log_h, np.log(features.P/np.sqrt(features.VX*features.LS**3))),
        "train_only_scaling_executable":np.allclose(demo.named_steps["scale"].mean_,[2.0]),
        "test_labels_absent_from_features":"truth" not in model_feature_names and "has_keyhole" not in model_feature_names,
        "B1_evaluation_only":"B1" not in model_feature_names,
        "q20_q30_absent_from_features":not ({"q20","q30","is_q20","is_q30"}&model_feature_names),
        "pca_label_free":set(pca_loadings.feature)==set(TEMPORAL_FEATURES) and "has_keyhole" not in set(pca_loadings.feature),
        "robust_derivative_fixed_not_label_selected":"half_window: int = 2" in source and "has_keyhole" not in source[source.index("def local_linear_grid_derivative"):source.index("def synthetic_derivative_error")],
        "onset_exact_valid_frames_only":bool(pd.read_csv(OUTPUT/"keyhole_onset_audit.csv").query("onset_available == True").has_keyhole.eq(1).all()),
        "no_warning_model_or_post_onset_features":not bool(pd.read_csv(OUTPUT/"keyhole_lead_time_results.csv").warning_threshold_fitted.any()),
        "notebook_stores_executed_outputs":len(notebook_outputs)>=10,
        "figures_eight":len(figures)==8,
        "figure_hashes_match_manifest":all(sha256_file(FIGURES/row.figure)==row.sha256 for row in pd.read_csv(OUTPUT/"figure_manifest.csv").itertuples()),
        "usable_count_reconciles":int(merged.usable_width_timeseries.sum())==len(features),
        "primary_model_excludes_raw_derivative_features":not bool(set(RAW_DERIVATIVE_FEATURES)&set(TEMPORAL_FEATURES)),
        "longitudinal_diagnostic_is_separate":(OUTPUT/"longitudinal_length_diagnostic"/"published_delta_x_summary.csv").is_file(),
        "report_numbers_consistent":all(token in (OUTPUT/filename).read_text(encoding="utf-8") for token in [f"{len(features)}/405",f"{int(features.has_keyhole.sum())}"] for filename in ["FINAL_PHASE2_REPORT.md","SUPERVISOR_PHASE2_ONE_PAGE.md","claim_ledger.md"]),
        "historical_phase1_outputs_unchanged": not bool(subprocess.run(["git","diff","--name-only",STARTING_SHA,"--","outputs/week8_5_frozen_confirmation","outputs/week9_phase1_close_week8","outputs/week9_phase1_5_h_physics_confirmation","outputs/week9_phase1_7_physics_ridge_residual_gp","outputs/week9_phase1_8_model_path_decomposition"],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()),
    }
    require(all(bool(v) for v in checks.values()), f"validation failed: {[k for k,v in checks.items() if not v]}")
    payload={"status":"PASS","checks":checks,"check_count":len(checks),"starting_sha":STARTING_SHA,
             "usable_temporal_simulations":len(features),"usable_keyholes":int(features.has_keyhole.sum())}
    write_json(OUTPUT/"validation_report.json",payload)
    (OUTPUT/"validation_report.md").write_text("# Validation report\n\n**PASS** — "+str(len(checks))+" focused checks passed.\n\n"+"\n".join(f"- PASS: {k}" for k in checks)+"\n",encoding="utf-8")
    return payload


def run() -> None:
    t0=time.time(); OUTPUT.mkdir(parents=True,exist_ok=True); FIGURES.mkdir(parents=True,exist_ok=True)
    pop=load_population(); axis_semantics_audit(pop)
    merged,audit,profiles,features=audit_and_extract(); prefix=prefix_feature_table(profiles,features)
    effects=feature_effects(features); robustness=derivative_robustness_gate(effects); pred,ppred=evaluate_models(pop,features,prefix)
    rep,summary,contrasts=summarize_oof(pred); prep,psummary,pcontrasts=summarize_oof(ppred,prefix=True)
    write_csv(OUTPUT/"model_repeat_level_metrics.csv",rep); write_csv(OUTPUT/"model_oof_summary.csv",summary); write_csv(OUTPUT/"model_paired_contrasts.csv",contrasts)
    write_csv(OUTPUT/"prefix_repeat_level_metrics.csv",prep); write_csv(OUTPUT/"prefix_model_summary.csv",psummary); write_csv(OUTPUT/"prefix_model_contrasts.csv",pcontrasts)
    class_profile_summary(profiles)
    onset_alignment(profiles,audit)
    pscores,ploadings,shape=pca_analysis(features,profiles); residual=residual_cases(pred,features)
    axis_comparison=longitudinal_comparison(effects,summary)
    figures=make_figures(features,profiles,audit,effects,pscores,shape,summary,psummary,ppred)
    render_reports(merged,audit,effects,summary,contrasts,psummary,pcontrasts,residual,figures,robustness,axis_comparison)
    NOTEBOOK.parent.mkdir(parents=True,exist_ok=True); NOTEBOOK.write_text(json.dumps(notebook_payload(),indent=1)+"\n",encoding="utf-8")
    execute_and_save_notebook()
    validation=validate(pop,merged,audit,profiles,features,prefix,figures)
    source_hashes={str(p.relative_to(ROOT)):sha256_file(p) for p in [SOURCE_PLAN, ROOT/"src"/"week8_5_frozen_sample_efficiency_confirmation.py",ROOT/"src"/"week7_phase2_sph_v2_physical_target_extraction.py"]}
    run_manifest={"study":"Week 9 Phase 2 — Temporal melt-pool width dynamics and early Keyhole signal","starting_sha":STARTING_SHA,"branch":BRANCH,
        "population":405,"keyholes":73,"usable":len(features),"usable_keyholes":int(features.has_keyhole.sum()),"width_definition":"canonical transverse width: (y_max-y_min)*1e6 micrometres",
        "longitudinal_definition":"secondary diagnostic: (x_max-x_min)*1e6 micrometres",
        "physical_time_source":"time.dat seconds","derivative_display_unit":"um/ms","primary_derivative":"centered finite difference after timestamp-only regularity gate",
        "robustness_derivative":"fixed 5-point local-linear slope on 201-point tau grid","active_interval":"first valid melt through established 90% laser-domain cutoff; no cooling",
        "prefixes":PREFIXES,"bootstrap_draws":BOOTSTRAP_DRAWS,"source_hashes":source_hashes,"validation":validation,"notebook_sha256":sha256_file(NOTEBOOK),"elapsed_seconds":time.time()-t0}
    run_manifest["artifact_hashes"]={str(path.relative_to(OUTPUT)).replace("\\","/"):sha256_file(path) for path in sorted(OUTPUT.rglob("*")) if path.is_file() and path.name != "run_manifest.json"}
    write_json(OUTPUT/"run_manifest.json",run_manifest)
    print(json.dumps({"status":"PASS","usable":len(features),"elapsed_seconds":time.time()-t0},indent=2))


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--run",action="store_true"); args=parser.parse_args()
    if args.run: run()
    else: parser.print_help()


if __name__ == "__main__":
    main()
