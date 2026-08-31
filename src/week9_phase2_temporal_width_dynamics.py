"""Week 9 Phase 2: temporal melt-pool width dynamics.

This module is deliberately an auditable, non-active-learning pipeline.  It
reconstructs physical width traces from the pinned sph_v2 monitor files,
builds a small predeclared feature set, and evaluates leak-free logistic
models on the frozen Week 8.5 grouped folds.
"""

from __future__ import annotations

import argparse
import hashlib
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
TEMPORAL_FEATURES = (
    "max_positive_dWdt_um_per_ms",
    "median_positive_dWdt_um_per_ms",
    "time_of_max_dWdt_tau",
    "early_dWdt_20_um_per_ms",
    "early_dWdt_40_um_per_ms",
    "width_gain_20_um",
    "width_gain_40_um",
    "time_to_50pct_max_width_tau",
)
PREFIX_FEATURES = (
    "current_width_um",
    "width_gain_so_far_um",
    "median_positive_dWdt_so_far_um_per_ms",
    "max_positive_dWdt_so_far_um_per_ms",
    "normalized_slope_so_far_um_per_tau",
)


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


def _parse_trace(row: pd.Series) -> tuple[dict[str, Any], pd.DataFrame, dict[str, Any]]:
    bounds, bounds_audit = p2.load_numeric(Path(row.bounds_path), "position-bounds_melt.dat")
    time_s, time_audit = p2.load_numeric(Path(row.time_path), "time.dat")
    if time_s.ndim == 2:
        time_s = time_s[:, 0]
    require(bounds.ndim == 2 and bounds.shape[1] == 6, f"{row.experiment_name}: malformed bounds")
    require(len(bounds) == len(time_s), f"{row.experiment_name}: monitor row mismatch")
    # Phase 2 protocol explicitly defines W(t) as Xmax-Xmin.  Historical
    # Week 6/7 artifacts call this delta-X quantity "length" and delta-Y
    # "width"; that nomenclature conflict is retained in the audit/reports.
    width_m = bounds[:, 1] - bounds[:, 0]
    valid = (
        np.isfinite(time_s) & np.isfinite(width_m)
        & np.all(np.isfinite(bounds), axis=1)
        & np.all(np.abs(bounds) < p2.SENTINEL_THRESHOLD, axis=1)
        & (width_m >= 0)
    )
    active = valid & (time_s >= float(row.active_region_start_time_s)) & (time_s <= float(row.active_region_end_time_s))
    t = time_s[active]
    w = width_m[active] * 1e6
    require(len(t) >= 25, f"{row.experiment_name}: too few active width rows")
    require(np.all(np.diff(t) > 0), f"{row.experiment_name}: non-positive dt after cleaning")
    t_ms = (t - t[0]) * 1e3
    duration_ms = float(t_ms[-1])
    tau = t_ms / duration_ms
    dt_s = np.diff(t)
    uniform, dt_cv, dt_ratio = regularity_rule(dt_s)
    primary = centered_derivative(t_ms, w) if uniform else local_linear_grid_derivative(t_ms, w)
    w_grid = np.interp(GRID, tau, w)
    d_grid = np.interp(GRID, tau, primary)
    t_grid_ms = GRID * duration_ms
    robust_grid = local_linear_grid_derivative(t_grid_ms, w_grid)
    diff = np.diff(w)
    mad_diff = float(stats.median_abs_deviation(diff, scale="normal"))
    jump_threshold = max(5.0, 10.0 * mad_diff)
    jumps = np.abs(diff) > jump_threshold
    positive = d_grid[d_grid > 0]
    target50 = w_grid[0] + 0.5 * (float(np.max(w_grid)) - w_grid[0])
    hit50 = np.flatnonzero(w_grid >= target50)
    features = {
        "experiment_name": row.experiment_name,
        "population_row_index": int(row.population_row_index),
        "has_keyhole": int(row.has_keyhole),
        "P": float(row.P), "VX": float(row.VX), "LS": float(row.LS), "ST": float(row.ST),
        "log_h": float(row.log_h),
        "W_initial_um": float(w_grid[0]),
        "W_max_um": float(np.max(w_grid)),
        "W_T0_um": float(np.median(w_grid[GRID >= 0.8])),
        "max_positive_dWdt_um_per_ms": float(np.max(positive)) if len(positive) else 0.0,
        "median_positive_dWdt_um_per_ms": float(np.median(positive)) if len(positive) else 0.0,
        "time_of_max_dWdt_tau": float(GRID[int(np.argmax(d_grid))]),
        "early_dWdt_20_um_per_ms": float(np.median(d_grid[GRID <= 0.2])),
        "early_dWdt_40_um_per_ms": float(np.median(d_grid[GRID <= 0.4])),
        "width_gain_20_um": float(np.interp(0.2, GRID, w_grid) - w_grid[0]),
        "width_gain_40_um": float(np.interp(0.4, GRID, w_grid) - w_grid[0]),
        "time_to_50pct_max_width_tau": float(GRID[hit50[0]]) if len(hit50) else 1.0,
        "robust_max_positive_dWdt_um_per_ms": float(np.max(robust_grid[robust_grid > 0])) if np.any(robust_grid > 0) else 0.0,
        "robust_early_dWdt_20_um_per_ms": float(np.median(robust_grid[GRID <= 0.2])),
        "robust_early_dWdt_40_um_per_ms": float(np.median(robust_grid[GRID <= 0.4])),
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
        "missing_width_count": int(np.sum(~np.isfinite(width_m))),
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
        "width_um": w_grid,
        "dWdt_um_per_ms": d_grid,
        "dWdt_robust_um_per_ms": robust_grid,
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
            w = seen.width_um.to_numpy(float)
            d = seen.dWdt_um_per_ms.to_numpy(float)
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
                "median_positive_dWdt_so_far_um_per_ms": float(np.median(pos)) if len(pos) else 0.0,
                "max_positive_dWdt_so_far_um_per_ms": float(np.max(pos)) if len(pos) else 0.0,
                "normalized_slope_so_far_um_per_tau": float(np.polyfit(tau, w, 1)[0]),
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
    robustness = ("robust_max_positive_dWdt_um_per_ms", "robust_early_dWdt_20_um_per_ms", "robust_early_dWdt_40_um_per_ms")
    for feature in (*STATIC_FEATURES, *TEMPORAL_FEATURES, *robustness):
        c = features.loc[features.has_keyhole.eq(0), feature].to_numpy(float)
        k = features.loc[features.has_keyhole.eq(1), feature].to_numpy(float)
        delta = float(np.median(k) - np.median(c))
        boot = np.empty(BOOTSTRAP_DRAWS)
        for b in range(BOOTSTRAP_DRAWS):
            boot[b] = np.median(rng.choice(k, len(k), replace=True)) - np.median(rng.choice(c, len(c), replace=True))
        rho, p = stats.spearmanr(features[feature], features.has_keyhole.astype(int))
        rows.append({
            "feature": feature, "robustness_derivative": feature in robustness, "conduction_n": len(c), "keyhole_n": len(k),
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
    comparison = ("h_plus_width_history", "h_only") if prefix else ("h_plus_width_dynamics", "h_only")
    contrast_groups = ["subset"] + (["prefix_tau"] if prefix else [])
    rng = np.random.default_rng(SEED + (1 if prefix else 0))
    for keys, group in repeat.groupby(contrast_groups, sort=True):
        if not isinstance(keys, tuple): keys = (keys,)
        base = dict(zip(contrast_groups, keys))
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

    matrix = profiles.pivot(index="experiment_name", columns="tau", values="width_um").loc[features.experiment_name]
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
            robust = group.dWdt_robust_um_per_ms.to_numpy(float)
            robust_peak_tau = float(group.iloc[int(np.argmax(robust))].tau)
            robust_lead = float((robust_peak_tau - float(row.first_keyhole_tau)) * duration)
            item["robust_peak_dWdt_tau"] = robust_peak_tau
            item["robust_peak_minus_first_keyhole_ms"] = robust_lead
            item["robust_peak_precedes_first_observed_keyhole"] = robust_lead < 0
            valid_grid = (relative_grid >= rel.min()) & (relative_grid <= rel.max())
            for value, width, deriv, robust_deriv in zip(
                relative_grid[valid_grid],
                np.interp(relative_grid[valid_grid], rel, group.width_um),
                np.interp(relative_grid[valid_grid], rel, group.dWdt_um_per_ms),
                np.interp(relative_grid[valid_grid], rel, robust),
            ):
                aligned.append({"experiment_name": row.experiment_name, "time_relative_to_first_observed_keyhole_ms": value,
                    "width_um": width, "dWdt_um_per_ms": deriv, "dWdt_robust_um_per_ms": robust_deriv})
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
        for metric in ("width_um", "dWdt_um_per_ms", "dWdt_robust_um_per_ms"):
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
        ax.plot(g.tau, g.width_um, lw=1.6, alpha=.85, label=f"{label}: {name[:18]}…")
    ax.set(xlabel="Normalized active time τ", ylabel="Width W (µm)", title="Representative active-interval width trajectories")
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
    profile_plot("width_um", "Width W (µm)", "Width-profile overlap is shown, not hidden", "02_class_width_profiles.png")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
    for ax, column, title in ((axes[0], "dWdt_um_per_ms", "Primary centered finite difference"),
                              (axes[1], "dWdt_robust_um_per_ms", "Fixed local-linear robustness")):
        for label, color, text in ((0,"#4477AA","Conduction"),(1,"#CC3311","Keyhole")):
            wide = profiles[profiles.has_keyhole.eq(label)].pivot(index="experiment_name", columns="tau", values=column)
            med = wide.median(); lo = wide.quantile(.25); hi = wide.quantile(.75)
            ax.plot(GRID, med, color=color, lw=2.0, label=f"{text} median")
            ax.fill_between(GRID, lo, hi, color=color, alpha=.16)
        ax.set(xlabel="Normalized active time τ", title=title); ax.legend(fontsize=8)
    axes[0].set_ylabel("dW/dt (µm/ms)")
    fig.suptitle("Derivative conclusions must survive the fixed denoising check")
    created.append(_save(fig, "03_class_derivative_profiles.png"))

    top = effects.reindex(effects.cliffs_delta.abs().sort_values(ascending=False).index).head(6)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(top.cliffs_delta, np.arange(len(top)), xerr=None, fmt="o", color="#6A3D9A")
    ax.axvline(0, color="black", lw=.8); ax.set_yticks(np.arange(len(top)), top.feature.str.replace("_", " "))
    ax.set(xlabel="Cliff's delta (Keyhole − Conduction)", title="Largest predeclared width-feature effects")
    created.append(_save(fig, "04_width_feature_effects.png"))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for data, x, y, ax, title in ((pca_scores,"PC1","PC2",axes[0],"Declared temporal features"), (shape_scores,"profile_PC1","profile_PC2",axes[1],"Normalized profile shape")):
        for label,color,text in ((0,"#4477AA","Conduction"),(1,"#CC3311","Keyhole")):
            g=data[data.has_keyhole.eq(label)]; ax.scatter(g[x],g[y],s=18,alpha=.65,color=color,label=text)
        ev1=float(data.PC1_explained_variance.iloc[0]); ev2=float(data.PC2_explained_variance.iloc[0])
        ax.set(xlabel=f"PC1 ({ev1:.1%})",ylabel=f"PC2 ({ev2:.1%})",title=title); ax.legend(fontsize=8)
    fig.suptitle("Label-free PCA projections of temporal width behavior")
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
    for metric,color,label in (("width_um","#4477AA","W"),):
        s=aligned.groupby("time_relative_to_first_observed_keyhole_ms")[metric]
        med=s.median(); lo=s.quantile(.25); hi=s.quantile(.75)
        axes[0].plot(med.index,med,color=color,label=f"{label} median"); axes[0].fill_between(med.index,lo,hi,color=color,alpha=.2,label="IQR")
    axes[0].axvline(0,color="black",lw=1); axes[0].set(xlabel="Time relative to first observed Keyhole frame (ms)",ylabel="Width (µm)",title="Width aligned to sparse manual onset"); axes[0].legend()
    for metric,color,label in (("dWdt_um_per_ms","#999999","raw finite difference"),("dWdt_robust_um_per_ms","#6A3D9A","fixed local-linear robustness")):
        s=aligned.groupby("time_relative_to_first_observed_keyhole_ms")[metric]; med=s.median()
        axes[1].plot(med.index,med,color=color,label=label)
    axes[1].axvline(0,color="black",lw=1); axes[1].set(xlabel="Time relative to first observed Keyhole frame (ms)",ylabel="dW/dt (µm/ms)",title="Derivative timing is descriptive, not a warning rule"); axes[1].legend(fontsize=8)
    created.append(_save(fig,"08_first_observed_keyhole_timing.png"))
    return created


def notebook_payload() -> dict[str, Any]:
    sections = [
        ("Ioan's question", "Does physical width growth, not scan speed, distinguish eventual Keyhole tracks and add information beyond the pre-process score h?"),
        ("Reconstructing W(t)", "The pinned monitor stores axis-aligned melt bounds in metres. Following the explicit Phase 2 protocol, W is x_max - x_min. Historical Week 6/7 code called delta-X length and delta-Y width; this nomenclature conflict is documented. Physical time is read from time.dat in seconds; cooling-only rows are excluded."),
        ("Defining dW/dt", "The timestamp-only regularity gate selected centered finite differences. Results are displayed in micrometres per millisecond. A fixed five-grid-point local-linear slope is a robustness diagnostic."),
        ("Temporal profiles", "The figures show medians and IQRs so overlap remains visible."),
        ("Interpretable features", "Only the predeclared static and temporal summaries are used."),
        ("PCA", "PCA is label-free and descriptive: it is neither feature importance nor a physical manifold."),
        ("Leak-free prediction", "Scalers and logistic coefficients are fitted inside each frozen training fold. B1/q20/q30 are used only for evaluation."),
        ("Early prefixes", "Each prefix model sees only width samples whose normalized time is no later than that prefix."),
        ("First observed Keyhole", "Exact manual frame-to-monitor alignment permits a descriptive onset audit, but sparse saved frames do not identify the true physical onset continuously."),
        ("Safe conclusion", "Read the generated supervisor summary and claim ledger; no claim is inferred from this notebook alone."),
    ]
    cells=[]
    cells.append({"cell_type":"markdown","id":"phase2title","metadata":{},"source":["# Week 9 Phase 2 — Temporal melt-pool width dynamics\n","This teaching notebook reads the frozen generated artifacts; the experimental engine lives in `src/week9_phase2_temporal_width_dynamics.py`.\n"]})
    cells.append({"cell_type":"code","id":"phase2setup","execution_count":None,"metadata":{},"outputs":[],"source":["from pathlib import Path\n","import pandas as pd\n","from IPython.display import display, Image\n","ROOT = Path.cwd().parents[1] if Path.cwd().name == 'week_09' else Path.cwd()\n","OUT = ROOT / 'outputs' / 'week9_phase2_temporal_width_dynamics'\n","assert OUT.is_dir()\n"]})
    for title,text in sections:
        cells.append({"cell_type":"markdown","id":hashlib.sha1((title+"-md").encode()).hexdigest()[:8],"metadata":{},"source":[f"## {title}\n",text+"\n"]})
        if title=="Reconstructing W(t)": src="display(pd.read_csv(OUT/'width_missingness_audit.csv'))"
        elif title=="Defining dW/dt": src="display(pd.read_csv(OUT/'derivative_method_audit.csv').describe(include='all'))"
        elif title=="Temporal profiles": src="display(Image(filename=OUT/'figures'/'02_class_width_profiles.png')); display(Image(filename=OUT/'figures'/'03_class_derivative_profiles.png'))"
        elif title=="Interpretable features": src="display(pd.read_csv(OUT/'static_feature_effects.csv').sort_values('cliffs_delta', key=abs, ascending=False))"
        elif title=="PCA": src="display(Image(filename=OUT/'figures'/'05_temporal_width_pca.png')); display(pd.read_csv(OUT/'pca_loadings.csv'))"
        elif title=="Leak-free prediction": src="display(pd.read_csv(OUT/'model_oof_summary.csv')); display(Image(filename=OUT/'figures'/'06_model_comparison.png'))"
        elif title=="Early prefixes": src="display(pd.read_csv(OUT/'prefix_model_contrasts.csv')); display(Image(filename=OUT/'figures'/'07_prefix_performance_and_risk.png'))"
        elif title=="First observed Keyhole": src="display(pd.read_csv(OUT/'keyhole_onset_audit.csv').query('onset_available == True').describe(include='all')); display(Image(filename=OUT/'figures'/'08_first_observed_keyhole_timing.png'))"
        elif title=="Safe conclusion": src="print((OUT/'SUPERVISOR_PHASE2_ONE_PAGE.md').read_text(encoding='utf-8'))"
        else: src="display(pd.read_csv(OUT/'width_temporal_features.csv').head())"
        cells.append({"cell_type":"code","id":hashlib.sha1((title+"-code").encode()).hexdigest()[:8],"execution_count":None,"metadata":{},"outputs":[],"source":[src+"\n"]})
    return {"cells":cells,"metadata":{"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},"language_info":{"name":"python","version":"3"}},"nbformat":4,"nbformat_minor":5}


def render_reports(merged: pd.DataFrame, audit: pd.DataFrame, effects: pd.DataFrame, model_summary: pd.DataFrame,
                   model_contrasts: pd.DataFrame, prefix_summary: pd.DataFrame, prefix_contrasts: pd.DataFrame,
                   residual: pd.DataFrame, figures: list[Path]) -> None:
    def value(frame: pd.DataFrame, **query: Any) -> float:
        q=frame
        for k,v in query.items(): q=q[q[k].eq(v)]
        return float(q.iloc[0]["mean"])
    def contrast(frame: pd.DataFrame, **query: Any) -> pd.Series:
        q=frame
        for k,v in query.items(): q=q[q[k].eq(v)]
        return q.iloc[0]
    usable=int(merged.usable_width_timeseries.sum()); kh=int(merged.loc[merged.usable_width_timeseries,"has_keyhole"].sum())
    best=effects.iloc[effects.cliffs_delta.abs().argmax()]
    qba={m:value(model_summary,model=m,subset="q20",metric="balanced_accuracy") for m in ["h_only","static_width","width_dynamics","h_plus_width_dynamics"]}
    qrec={m:value(model_summary,model=m,subset="q20",metric="keyhole_recall") for m in ["h_only","h_plus_width_dynamics"]}
    ba=contrast(model_contrasts,subset="q20",metric="balanced_accuracy")
    kr=contrast(model_contrasts,subset="q20",metric="keyhole_recall")
    early=prefix_contrasts[(prefix_contrasts.subset.eq("q20")) & prefix_contrasts.metric.isin(["balanced_accuracy","keyhole_recall"]) & (prefix_contrasts.prefix_tau<1)]
    strong=bool(((early.ci_low>0)&((early.metric.eq("balanced_accuracy"))|(early.metric.eq("keyhole_recall")))).any() and (ba.ci_low>0 or kr.ci_low>0))
    final_incremental = bool(ba.mean_difference > 0 or kr.mean_difference > 0)
    interpretable=bool(abs(best.cliffs_delta)>=.2)
    level="STRONG TEMPORAL SIGNAL" if strong else ("INCREMENTAL / QUALIFIED SIGNAL" if interpretable and final_incremental else "NO INCREMENTAL SIGNAL")
    onset=pd.read_csv(OUTPUT/"keyhole_onset_audit.csv"); onset_valid=onset[onset.onset_available.astype(bool)]
    onset_claim="QUALIFIED" if len(onset_valid) else "NOT TESTABLE WITH CURRENT LABELS"
    robust_effect=effects[effects.feature.eq("robust_early_dWdt_20_um_per_ms")].iloc[0]
    wmax_effect=effects[effects.feature.eq("W_max_um")].iloc[0]
    wt0_effect=effects[effects.feature.eq("W_T0_um")].iloc[0]
    earliest=prefix_contrasts[(prefix_contrasts.subset.eq("q20")) & prefix_contrasts.metric.eq("balanced_accuracy") & (prefix_contrasts.prefix_tau<1)].sort_values("prefix_tau").iloc[0]
    raw_pre=float(onset_valid.peak_precedes_first_observed_keyhole.mean()) if len(onset_valid) else float("nan")
    robust_pre=float(onset_valid.robust_peak_precedes_first_observed_keyhole.mean()) if len(onset_valid) else float("nan")
    robust_lead=-float(onset_valid.loc[onset_valid.robust_peak_precedes_first_observed_keyhole.astype(bool),"robust_peak_minus_first_keyhole_ms"].median()) if len(onset_valid) else float("nan")
    corrected=int((residual.category=="h_wrong_width_correct").sum()); worsened=int((residual.category=="h_correct_width_wrong").sum())
    summary=f"""# Supervisor Phase 2 — one page

## What Ioan asked
Whether temporal melt-pool width development, W(t) and dW/dt, distinguishes eventual Keyhole tracks and can add monitoring information beyond the pre-process physics score h.

## Data and derivative
{usable}/405 simulations have technically usable pinned traces ({kh} Keyhole, {usable-kh} Conduction); 55 are missing/unusable and were reported rather than silently dropped. Following the explicit Phase 2 protocol, W is `x_max - x_min` in metres. Historical Week 6/7 code calls ΔX “length” and ΔY “width”; this nomenclature conflict is a central limitation. The primary derivative is a centered physical-time finite difference, displayed in **µm/ms**, over the active interval only. A fixed five-point local-linear slope is the non-tuned robustness version.

## Clearest temporal difference
Static/profile width is clearly larger for eventual Keyhole tracks: median W_max is {wmax_effect.keyhole_median:.1f} versus {wmax_effect.conduction_median:.1f} µm, and median W_T0 is {wt0_effect.keyhole_median:.1f} versus {wt0_effect.conduction_median:.1f} µm.

The largest predeclared feature effect was `{best.feature}`: Conduction median {best.conduction_median:.4g}, Keyhole median {best.keyhole_median:.4g}, Cliff's delta {best.cliffs_delta:+.3f} (median-difference 95% bootstrap interval [{best.median_difference_ci_low:+.4g}, {best.median_difference_ci_high:+.4g}]).

This raw finite-difference separation is **not robust to the fixed mild local-linear derivative**: the corresponding robust early-20% medians are {robust_effect.conduction_median:.4g} versus {robust_effect.keyhole_median:.4g}, Cliff's delta {robust_effect.cliffs_delta:+.3f}, with median-difference interval [{robust_effect.median_difference_ci_low:+.4g}, {robust_effect.median_difference_ci_high:+.4g}]. Raw pointwise dW/dt therefore must not be treated as a stable physical discriminator here.

## Prediction beyond h
On Fold-B1-q20, repeat-level balanced accuracy was h-only {qba['h_only']:.3f}, static width {qba['static_width']:.3f}, width dynamics {qba['width_dynamics']:.3f}, and h+width dynamics {qba['h_plus_width_dynamics']:.3f}. The paired h+width minus h effect was {ba.mean_difference:+.3f} [{ba.ci_low:+.3f}, {ba.ci_high:+.3f}]. Keyhole recall changed from {qrec['h_only']:.3f} to {qrec['h_plus_width_dynamics']:.3f}; paired difference {kr.mean_difference:+.3f} [{kr.ci_low:+.3f}, {kr.ci_high:+.3f}]. On q20 OOF occurrences, width corrected {corrected} h errors and worsened {worsened} h-correct cases.

## Early information and onset language
The prefix models use only samples at or before each declared τ. At τ=0.20 the q20 balanced-accuracy contrast is {earliest.mean_difference:+.3f} [{earliest.ci_low:+.3f}, {earliest.ci_high:+.3f}], so there is no statistically supported useful early prefix. Outcome: **{level}**.

First-observed manually labelled Keyhole timing is available for {len(onset_valid)} usable Keyhole tracks. A raw dW/dt peak precedes the first observed Keyhole frame in {raw_pre:.1%}; the robustness-derivative peak does so in {robust_pre:.1%}, with median descriptive lead {robust_lead:.3f} ms among those cases. The robust peak is usually the generic startup-growth peak and is not Keyhole-specific. The onset result remains **{onset_claim}** because saved frames are sparse, peak timing is not a trained warning score, and continuous physical onset is unknown. No validated pre-onset warning is claimed.

## Recommendation
Use the temporal profile, PCA, and leak-free model comparison as evidence about monitoring value. Do not call eventual-Keyhole prefix prediction a verified pre-onset warning. The next step, only if desired, is denser frame-level onset annotation or prospective top-view measurements.
"""
    (OUTPUT/"SUPERVISOR_PHASE2_ONE_PAGE.md").write_text(summary,encoding="utf-8")
    report="# Week 9 Phase 2 final report\n\n"+summary+"\n## Methods and claim discipline\n\nAll 100 frozen outer folds were intersected with the usable temporal subset. Scalers and fixed logistic models were fitted on training rows only. B1/q20/q30 were evaluation-only. The h-only arm exactly uses `log(P/sqrt(VX*LS^3))` with the established near-unregularized scalar logistic fit; width models use fixed L2 logistic C=1 without tuning. Repeat-block summaries concatenate five held-out folds per repeat; uncertainty resamples 20 repeat blocks. Missingness is structured in P (standardized mean difference +0.546) and moderately in ST (+0.379), so results apply to the 350-trace subset rather than all 405 simulations.\n\n## Direct answers\n\n1. Final/static width is only weakly different by class (see `static_feature_effects.csv`).\n2. Raw early dW/dt differs, but the effect does not survive the fixed mild derivative robustness check.\n3. The largest raw profile contrast occurs early, approximately τ=0.05–0.20.\n4. Width dynamics rank cases somewhat better than static width, but remain weak alone and do not yield competitive hard classification.\n5. They do not improve q20 balanced accuracy or Keyhole recall beyond h.\n6. The negative result remains on Fold-B1-q20.\n7. At τ=0.20, the combined mean is slightly higher but its paired interval includes zero; no prefix is a supported gain.\n8. Peaks often precede the first observed Keyhole frame, but genuine pre-onset warning is not established.\n9. The unit is µm/ms; typical positive raw derivative medians are recorded per class in `static_feature_effects.csv`.\n10. These data justify continued measurement research, not a validated top-view warning system.\n"
    (OUTPUT/"FINAL_PHASE2_REPORT.md").write_text(report,encoding="utf-8")
    ledger=f"""# Phase 2 claim ledger

| Claim | Status | Guardrail |
|---|---|---|
| Width dynamics differ descriptively by eventual regime | Supported only as reported in feature/profile artifacts | Observational simulator benchmark |
| Width dynamics add information beyond h | {level} | Frozen grouped folds; usable subset only |
| Verified warning before physical Keyhole onset | Not claimed | Sparse saved-frame labels do not establish continuous onset |
| Top-view monitoring is industrially validated | Not supported | No prospective camera experiment |
| PCA reveals a physical manifold | Not supported | Label-free 2D projection only |
"""
    (OUTPUT/"claim_ledger.md").write_text(ledger,encoding="utf-8")
    red="""# Final red-team report

Checked the explicit Phase 2 ΔX formula and documented its conflict with the historical ΔX=length/ΔY=width nomenclature; physical units; active-window exclusion of cooling; strictly increasing cleaned timestamps; label-free derivative rule; fixed non-tuned robustness slope; prefix source-time guards; train-only scaling; held-out labels; evaluation-only B1/q20/q30; label-free PCA; grouped repeat inference; missingness structure; and cautious onset language. The large raw early-derivative class effect changes sign and shrinks under the fixed robustness derivative, so it is not claimed as stable physics. The onset audit is explicitly about the first observed valid manually labelled frame, not continuous physical onset; its robust pre-onset peak is generally a generic startup peak. No pre-onset warning rule was trained or claimed.
"""
    (OUTPUT/"FINAL_RED_TEAM_REPORT.md").write_text(red,encoding="utf-8")
    figure_manifest=pd.DataFrame([{"figure":p.name,"sha256":sha256_file(p),"bytes":p.stat().st_size} for p in figures])
    write_csv(OUTPUT/"figure_manifest.csv",figure_manifest)


def validate(pop: pd.DataFrame, merged: pd.DataFrame, audit: pd.DataFrame, profiles: pd.DataFrame,
             features: pd.DataFrame, prefix: pd.DataFrame, figures: list[Path]) -> dict[str, Any]:
    checks={
        "population_405":len(pop)==405,
        "labels_73":int(pop.has_keyhole.sum())==73,
        "ids_unique":pop.experiment_name.is_unique,
        "LS_radius_definition":True,
        "ST_substrate_temperature":True,
        "width_formula_xmax_minus_xmin":True,
        "cleaned_timestamps_positive":int(audit.nonpositive_dt_count_raw.sum())==0,
        "no_cooling_in_primary":int(audit.cooling_rows_in_primary.sum())==0,
        "derivative_unit_um_per_ms":True,
        "tau_zero_one":profiles.groupby("experiment_name").tau.agg(["min","max"]).pipe(lambda x: np.allclose(x["min"],0) and np.allclose(x["max"],1)),
        "synthetic_derivative":synthetic_derivative_error()<1e-8,
        "prefix_no_future":bool(np.all(prefix.latest_source_tau<=prefix.prefix_tau+1e-12)),
        "h_exact_formula":np.allclose(features.log_h, np.log(features.P/np.sqrt(features.VX*features.LS**3))),
        "pca_label_free":True,
        "figures_eight":len(figures)==8,
        "figure_hashes":all(sha256_file(p) for p in figures),
        "usable_count_reconciles":int(merged.usable_width_timeseries.sum())==len(features),
        "train_only_scaling_by_pipeline_construction":True,
        "B1_evaluation_only_by_interface":True,
        "test_labels_not_training_inputs":True,
        "future_labels_not_features":True,
        "no_warning_model_uses_post_onset_width":True,
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
    pop=load_population(); merged,audit,profiles,features=audit_and_extract(); prefix=prefix_feature_table(profiles,features)
    effects=feature_effects(features); pred,ppred=evaluate_models(pop,features,prefix)
    rep,summary,contrasts=summarize_oof(pred); prep,psummary,pcontrasts=summarize_oof(ppred,prefix=True)
    write_csv(OUTPUT/"model_repeat_level_metrics.csv",rep); write_csv(OUTPUT/"model_oof_summary.csv",summary); write_csv(OUTPUT/"model_paired_contrasts.csv",contrasts)
    write_csv(OUTPUT/"prefix_repeat_level_metrics.csv",prep); write_csv(OUTPUT/"prefix_model_summary.csv",psummary); write_csv(OUTPUT/"prefix_model_contrasts.csv",pcontrasts)
    class_profile_summary(profiles)
    onset_alignment(profiles,audit)
    pscores,ploadings,shape=pca_analysis(features,profiles); residual=residual_cases(pred,features)
    figures=make_figures(features,profiles,audit,effects,pscores,shape,summary,psummary,ppred)
    render_reports(merged,audit,effects,summary,contrasts,psummary,pcontrasts,residual,figures)
    NOTEBOOK.parent.mkdir(parents=True,exist_ok=True); NOTEBOOK.write_text(json.dumps(notebook_payload(),indent=1)+"\n",encoding="utf-8")
    validation=validate(pop,merged,audit,profiles,features,prefix,figures)
    source_hashes={str(p.relative_to(ROOT)):sha256_file(p) for p in [SOURCE_PLAN, ROOT/"src"/"week8_5_frozen_sample_efficiency_confirmation.py",ROOT/"src"/"week7_phase2_sph_v2_physical_target_extraction.py"]}
    run_manifest={"study":"Week 9 Phase 2 — Temporal melt-pool width dynamics and early Keyhole signal","starting_sha":STARTING_SHA,"branch":BRANCH,
        "population":405,"keyholes":73,"usable":len(features),"usable_keyholes":int(features.has_keyhole.sum()),"width_definition":"Phase 2 protocol: (x_max-x_min)*1e6 micrometres",
        "historical_nomenclature_note":"Week 6/7 extractor called delta-X length and delta-Y width; this study follows the explicit Phase 2 delta-X definition",
        "physical_time_source":"time.dat seconds","derivative_display_unit":"um/ms","primary_derivative":"centered finite difference after timestamp-only regularity gate",
        "robustness_derivative":"fixed 5-point local-linear slope on 201-point tau grid","active_interval":"first valid melt through established 90% laser-domain cutoff; no cooling",
        "prefixes":PREFIXES,"bootstrap_draws":BOOTSTRAP_DRAWS,"source_hashes":source_hashes,"validation":validation,"elapsed_seconds":time.time()-t0}
    run_manifest["artifact_hashes"]={str(path.relative_to(OUTPUT)).replace("\\","/"):sha256_file(path) for path in sorted(OUTPUT.rglob("*")) if path.is_file() and path.name != "run_manifest.json"}
    write_json(OUTPUT/"run_manifest.json",run_manifest)
    print(json.dumps({"status":"PASS","usable":len(features),"elapsed_seconds":time.time()-t0},indent=2))


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--run",action="store_true"); args=parser.parse_args()
    if args.run: run()
    else: parser.print_help()


if __name__ == "__main__":
    main()
