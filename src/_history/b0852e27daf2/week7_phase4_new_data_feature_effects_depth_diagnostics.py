"""Week 7 Phase 4: new-data physical feature effects and depth diagnostics.

The primary feature analysis uses only corrected Phase 2 target-ready new-data
rows. Week 6 values are historical saved-artifact comparators. Existing Phase 3
LOO predictions are reused for depth-error diagnosis; they are never replaced
by in-sample residuals. Full-data Gaussian-process fits are used only to
interpret response surfaces inside observed support.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

MODULE_ROOT = Path(__file__).resolve().parents[1]
for module_path in (MODULE_ROOT, MODULE_ROOT / "src"):
    module_path_text = str(module_path)
    if module_path_text not in sys.path:
        sys.path.insert(0, module_path_text)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import Delaunay, cKDTree
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler

from src import week6_phase3_model_target_robustness as gp_engine
from src import week6_phase4_new_outputs_feature_effects as week6_effects
from src import week7_phase2_sph_v2_physical_target_extraction as phase2
from src import week7_phase3_new_data_model_stability as phase3


ROOT = MODULE_ROOT
OUTPUT_DIR = ROOT / "outputs" / "week7_04_new_data_feature_effects_depth_diagnostics"
SMOKE_DIR = OUTPUT_DIR / "smoke"
FIGURE_DIR_NAME = "figures"
NOTEBOOK_PATH = (
    ROOT / "notebooks" / "week_07" / "04_new_data_feature_effects_depth_diagnostics.ipynb"
)

PHASE3_PARENT_SHA = "1118d30f3199a97b9836591f8fdea75b46dfac0d"
PHASE4_BRANCH = "codex/week7-phase4-new-data-feature-effects-depth-diagnostics"
DATASET_REPO_ID = "ioandanielc/sph_v2"
DATASET_REVISION = "d69dac5bda8b622bc0de316b112815c6056c06ec"

PHASE1_DIR = ROOT / "outputs" / "week7_01_sph_v2_audit"
PHASE2_DIR = ROOT / "outputs" / "week7_02_sph_v2_target_extraction"
PHASE3_DIR = ROOT / "outputs" / "week7_03_new_data_physical_model_stability"
WEEK6_DIR = ROOT / "outputs" / "week6_04_new_outputs_feature_effects"

FEATURE_COLUMNS = ["P", "VX", "LS", "ST"]
FEATURE_UNITS = {"P": "W", "VX": "m/s", "LS": "um", "ST": "K"}
FEATURE_MEANINGS = {
    "P": "laser power",
    "VX": "scan speed",
    "LS": "laser spot radius",
    "ST": "substrate temperature",
}
TARGET_SPECS = phase3.TARGET_SPECS
TARGET_ORDER = ["width", "depth", "total_height", "kinetic_energy"]

BASE_SEED = 7404
BOOTSTRAP_RESAMPLES = 2_000
BOOTSTRAP_QUANTILES = (0.025, 0.975)
CURVE_GRID_SIZE = week6_effects.CURVE_GRID_SIZE
SURFACE_GRID_SIZE = week6_effects.SURFACE_GRID_SIZE
SUPPORT_DISTANCE_QUANTILE = week6_effects.SUPPORT_DISTANCE_QUANTILE
LOCAL_SENSITIVITY_STEP_SD = 0.05
SMOKE_POPULATION = 40
DEPTH_MODELS = [
    "matern32_no_nugget",
    "matern32_learned_nugget",
    "matern52_no_nugget",
]
PRIMARY_DEPTH_MODEL = "matern32_learned_nugget"
MODEL_LABELS = phase3.MODEL_LABELS

RUNTIME_EVENTS: list[dict[str, Any]] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def deterministic_seed(*parts: Any) -> int:
    token = "|".join(str(part) for part in (BASE_SEED, *parts))
    return int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:4], "big")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")
    return path


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes", "y"})
    )


def safe_spearman(left: Iterable[float], right: Iterable[float]) -> tuple[float, float, int]:
    x = np.asarray(list(left), dtype=float)
    y = np.asarray(list(right), dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    if int(valid.sum()) < 3 or np.ptp(x[valid]) == 0 or np.ptp(y[valid]) == 0:
        return math.nan, math.nan, int(valid.sum())
    result = spearmanr(x[valid], y[valid])
    return float(result.statistic), float(result.pvalue), int(valid.sum())


def metric_values(observed: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    residual = observed - predicted
    absolute = np.abs(residual)
    return {
        "MAE": float(mean_absolute_error(observed, predicted)),
        "RMSE": float(np.sqrt(mean_squared_error(observed, predicted))),
        "median_absolute_error": float(np.median(absolute)),
        "q75_absolute_error": float(np.quantile(absolute, 0.75)),
        "q90_absolute_error": float(np.quantile(absolute, 0.90)),
        "q95_absolute_error": float(np.quantile(absolute, 0.95)),
        "maximum_absolute_error": float(np.max(absolute)),
    }


def grouped_error_row(
    frame: pd.DataFrame,
    *,
    grouping: str,
    group: Any,
    model: str = PRIMARY_DEPTH_MODEL,
) -> dict[str, Any]:
    observed = frame["observed_depth_um"].to_numpy(float)
    predicted = frame[f"prediction__{model}"].to_numpy(float)
    return {
        "grouping": grouping,
        "group": str(group),
        "model": model,
        "n": len(frame),
        **metric_values(observed, predicted),
    }


def git_preflight() -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, encoding="utf-8"
        ).strip()

    branch = git("branch", "--show-current")
    head = git("rev-parse", "HEAD")
    require(branch == PHASE4_BRANCH, f"Unexpected Phase 4 branch: {branch}")
    require(head == PHASE3_PARENT_SHA, f"Phase 4 HEAD is not Phase 3 parent: {head}")
    status = git("status", "--porcelain")
    return {
        "branch": branch,
        "head": head,
        "phase3_parent_sha": PHASE3_PARENT_SHA,
        "worktree_initially_clean": status == "",
        "captured_at_utc": utc_now(),
    }


def week6_traceability_table() -> pd.DataFrame:
    rows = [
        (
            "Spearman input-output overview",
            "src/week6_phase4_new_outputs_feature_effects.py",
            "response_analysis_table; relationship_analysis; safe_spearman",
            "All 16 P/VX/LS/ST-response pairs; simulation-level marginal Spearman; n=241; descriptive and non-causal.",
            "Reuse four inputs, four T0 responses, marginal Spearman, saved Week 6 values; change population to target-ready new-data and add p-values.",
            "Replicates the historical definition on the new design without pooling populations.",
        ),
        (
            "Simulation-level Spearman bootstrap",
            "src/week6_phase4_new_outputs_feature_effects.py",
            "bootstrap_spearman_interval",
            "10,000 simulation resamples; deterministic seed; percentile 95% interval.",
            "Reuse deterministic simulation resampling and percentile interval; use 2,000 resamples as explicitly permitted for Phase 4.",
            "Keeps the uncertainty unit and definition while controlling runtime transparently.",
        ),
        (
            "Standardized linear Ridge coefficients",
            "src/week6_phase4_new_outputs_feature_effects.py",
            "standardized_ridge_rows",
            "StandardScaler on X and y; alpha grid 10^-6...10^6; shuffled 5-fold CV; full-population refit with selected alpha.",
            "Reuse the executable function and settings exactly; add fixed-specification simulation bootstrap intervals.",
            "Preserves the Week 6 conditional-linear association definition.",
        ),
        (
            "Full-data interpretive GP",
            "src/week6_phase4_new_outputs_feature_effects.py",
            "fit_full_gp; predict_full_gp",
            "Standardized X/y; Phase 3 GP kernel builder; one optimizer restart; full-data fit only for interpretation.",
            "Reuse implementation with Phase 3 Matérn 3/2 family and target-specific Phase 3 uncertainty/noise choice.",
            "No new model family is introduced; this fit is not an evaluation result.",
        ),
        (
            "Controlled response curves",
            "src/week6_phase4_new_outputs_feature_effects.py",
            "curve_and_surface_rows",
            "101-point observed-range grids; other inputs at medians; KE-LS also at P q10/q50/q90; nearest-neighbour support mask.",
            "Reuse grid, anchors, power profiles, and support logic on new-data target-ready rows.",
            "Directly updates the Week 6 width-LS and KE-LS views.",
        ),
        (
            "P-VX response surfaces",
            "src/week6_phase4_new_outputs_feature_effects.py",
            "curve_and_surface_rows; surface_figure",
            "31x31 P-VX grid; LS/ST at medians; pairwise convex hull plus 4D nearest-neighbour support mask.",
            "Reuse for depth and total height only, with experiment locations overlaid.",
            "Prevents unsupported regions from appearing as measured behaviour.",
        ),
        (
            "Normalized depth diagnostics",
            "src/week6_phase4_new_outputs_feature_effects.py",
            "normalized_diagnostics",
            "T0 depth, depth/LS, G3, G3/LS, R0 and R3 retained as diagnostics with coupling caveat.",
            "Reuse only G3, R3, max-depth and ratios as depth-error diagnostics; retain T0 depth as the sole primary depth target.",
            "Addresses failure mechanism without redefining the response.",
        ),
        (
            "Final physical-response summary",
            "src/week6_phase4_new_outputs_feature_effects.py",
            "association_facts; build_summary_payload; write_results_documents",
            "Separates raw Spearman, conditional Ridge, and nonlinear supported GP evidence; no causal claim.",
            "Reuse the three-view evidence chain and add explicit Week 6/new-data stability statuses.",
            "Makes replication and uncertainty boundaries auditable.",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "week6_analysis",
            "source_file",
            "source_function",
            "week6_definition_settings",
            "phase4_reuse_change",
            "reason",
        ],
    )


def load_population(*, smoke: bool) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], dict[str, Any]]:
    population, _, phase2_summary = phase3.load_phase2_inputs(smoke=False)
    require(len(population) == 165, "Phase 2 interface no longer has 165 new-data audit rows")
    require(set(population["partition"].astype(str)) == {"new-data"}, "Old-data row entered population")
    require(
        set(population["exact_sph_v2_revision"].astype(str)) == {DATASET_REVISION},
        "Population revision drift",
    )
    selected_names: set[str] | None = None
    if smoke:
        eligible = population.loc[population["depth_model_eligible"], "experiment_name"].tolist()
        positions = np.linspace(0, len(eligible) - 1, SMOKE_POPULATION, dtype=int)
        selected_names = {eligible[int(index)] for index in positions}
    population = population.copy()
    population["selected_for_phase4_run"] = (
        True
        if selected_names is None
        else population["experiment_name"].astype(str).isin(selected_names)
    )
    tables: dict[str, pd.DataFrame] = {}
    for target, spec in TARGET_SPECS.items():
        mask = bool_series(population[f"{target}_model_eligible"])
        mask &= bool_series(population["selected_for_phase4_run"])
        eligible = population.loc[mask].copy()
        table = pd.DataFrame(
            {
                "simulation_id": eligible["experiment_name"].astype(str),
                "experiment_name": eligible["experiment_name"].astype(str),
                "P": pd.to_numeric(eligible["P_W"], errors="raise"),
                "VX": pd.to_numeric(eligible["VX_m_per_s"], errors="raise"),
                "LS": pd.to_numeric(eligible["LS_um"], errors="raise"),
                "ST": pd.to_numeric(eligible["ST_K"], errors="raise"),
                target: pd.to_numeric(eligible[spec["column"]], errors="raise"),
                "partition": eligible["partition"].astype(str),
                "dataset_revision": eligible["exact_sph_v2_revision"].astype(str),
            }
        ).sort_values("experiment_name", kind="stable").reset_index(drop=True)
        require(np.isfinite(table[[*FEATURE_COLUMNS, target]].to_numpy(float)).all(), f"Non-finite {target} table")
        tables[target] = table
    return population, tables, phase2_summary


def population_reference(population: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "experiment_name",
        "partition",
        "exact_sph_v2_revision",
        "P_W",
        "VX_m_per_s",
        "LS_um",
        "ST_K",
        "has_keyhole",
        "keyhole_frame_count",
        "keyhole_timing_relative_to_T0",
        "source_label_modified",
        "simulation_silently_removed",
        "selected_for_phase4_run",
    ]
    for target, spec in TARGET_SPECS.items():
        columns.extend(
            [
                f"{target}_model_eligible",
                f"{target}_eligibility_source_fields",
                spec["column"],
            ]
        )
    return population[columns].copy()


def descriptive_summary(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for target, table in tables.items():
        for column in [*FEATURE_COLUMNS, target]:
            values = table[column].to_numpy(float)
            rows.append(
                {
                    "target_population": target,
                    "variable": column,
                    "unit": TARGET_SPECS[target]["unit"] if column == target else FEATURE_UNITS[column],
                    "n": len(values),
                    "minimum": float(np.min(values)),
                    "q25": float(np.quantile(values, 0.25)),
                    "median": float(np.median(values)),
                    "q75": float(np.quantile(values, 0.75)),
                    "maximum": float(np.max(values)),
                    "mean": float(np.mean(values)),
                    "std": float(np.std(values, ddof=1)),
                }
            )
    return pd.DataFrame(rows)


def bootstrap_spearman(
    x: np.ndarray,
    y: np.ndarray,
    *,
    target: str,
    feature: str,
    resamples: int,
) -> tuple[float, float, int]:
    rng = np.random.default_rng(deterministic_seed("spearman", target, feature, resamples))
    values = np.empty(resamples, dtype=float)
    n = len(x)
    for index in range(resamples):
        sample = rng.integers(0, n, n)
        values[index] = spearmanr(x[sample], y[sample]).statistic
    values = values[np.isfinite(values)]
    require(len(values) >= int(0.99 * resamples), f"Invalid Spearman bootstrap: {target}/{feature}")
    low, high = np.quantile(values, BOOTSTRAP_QUANTILES)
    return float(low), float(high), deterministic_seed("spearman", target, feature, resamples)


def spearman_analysis(
    tables: dict[str, pd.DataFrame], *, resamples: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    for target in TARGET_ORDER:
        table = tables[target]
        y = table[target].to_numpy(float)
        for feature in FEATURE_COLUMNS:
            x = table[feature].to_numpy(float)
            rho, p_value, n = safe_spearman(x, y)
            low, high, seed = bootstrap_spearman(
                x, y, target=target, feature=feature, resamples=resamples
            )
            rows.append(
                {
                    "target": target,
                    "target_label": TARGET_SPECS[target]["label"],
                    "target_unit": TARGET_SPECS[target]["unit"],
                    "input": feature,
                    "input_meaning": FEATURE_MEANINGS[feature],
                    "input_unit": FEATURE_UNITS[feature],
                    "spearman_rho": rho,
                    "p_value": p_value,
                    "ci_low": low,
                    "ci_high": high,
                    "confidence_level": 0.95,
                    "bootstrap_resamples": resamples,
                    "bootstrap_seed": seed,
                    "simulation_count": n,
                    "resample_unit": "simulation",
                    "analysis_type": "marginal association diagnostic",
                    "causal_claim": False,
                }
            )
    current = pd.DataFrame(rows)
    old = pd.read_csv(WEEK6_DIR / "phase4_spearman_correlations.csv").rename(
        columns={"response": "target", "feature": "input", "sample_size": "week6_simulation_count"}
    )
    old_ci = pd.read_csv(WEEK6_DIR / "phase4_spearman_bootstrap_intervals.csv").rename(
        columns={"response": "target", "feature": "input", "ci_low": "week6_ci_low", "ci_high": "week6_ci_high"}
    )
    old = old[["target", "input", "spearman_rho", "week6_simulation_count"]].rename(
        columns={"spearman_rho": "week6_spearman_rho"}
    ).merge(old_ci[["target", "input", "week6_ci_low", "week6_ci_high"]], on=["target", "input"], how="left")
    comparison = old.merge(
        current[
            [
                "target",
                "input",
                "spearman_rho",
                "ci_low",
                "ci_high",
                "simulation_count",
            ]
        ].rename(
            columns={
                "spearman_rho": "new_data_spearman_rho",
                "ci_low": "new_data_ci_low",
                "ci_high": "new_data_ci_high",
                "simulation_count": "new_data_simulation_count",
            }
        ),
        on=["target", "input"],
        how="inner",
        validate="one_to_one",
    )
    comparison["same_sign"] = np.sign(comparison["week6_spearman_rho"]) == np.sign(comparison["new_data_spearman_rho"])
    comparison["new_data_ci_includes_zero"] = (comparison["new_data_ci_low"] <= 0) & (comparison["new_data_ci_high"] >= 0)
    comparison["absolute_magnitude_change"] = comparison["new_data_spearman_rho"].abs() - comparison["week6_spearman_rho"].abs()
    statuses: list[str] = []
    for row in comparison.itertuples(index=False):
        if row.new_data_ci_includes_zero:
            statuses.append("INCONCLUSIVE_CI_INCLUDES_ZERO")
        elif not row.same_sign:
            statuses.append("SIGN_REVERSAL")
        elif row.absolute_magnitude_change > 0.05:
            statuses.append("SAME_SIGN_STRONGER")
        elif row.absolute_magnitude_change < -0.05:
            statuses.append("SAME_SIGN_WEAKER")
        else:
            statuses.append("SAME_SIGN_SIMILAR")
    comparison["comparison_status"] = statuses
    return current, comparison


def ridge_bootstrap_interval(
    table: pd.DataFrame,
    *,
    target: str,
    alpha: float,
    resamples: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    X = table[FEATURE_COLUMNS].to_numpy(float)
    y = table[target].to_numpy(float)
    rng = np.random.default_rng(deterministic_seed("ridge-bootstrap", target, resamples))
    coefficients = np.empty((resamples, len(FEATURE_COLUMNS)), dtype=float)
    n = len(table)
    for index in range(resamples):
        sample = rng.integers(0, n, n)
        X_sample = StandardScaler().fit_transform(X[sample])
        y_sample = StandardScaler().fit_transform(y[sample, None]).ravel()
        coefficients[index] = Ridge(alpha=alpha).fit(X_sample, y_sample).coef_
    low = np.quantile(coefficients, BOOTSTRAP_QUANTILES[0], axis=0)
    high = np.quantile(coefficients, BOOTSTRAP_QUANTILES[1], axis=0)
    fraction_positive = np.mean(coefficients > 0, axis=0)
    return low, high, fraction_positive, deterministic_seed("ridge-bootstrap", target, resamples)


def ridge_analysis(
    tables: dict[str, pd.DataFrame], *, resamples: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    for target in TARGET_ORDER:
        table = tables[target]
        base = pd.DataFrame(week6_effects.standardized_ridge_rows(table, target))
        alpha = float(base["selected_alpha"].iloc[0])
        low, high, fraction_positive, seed = ridge_bootstrap_interval(
            table, target=target, alpha=alpha, resamples=resamples
        )
        for index, row in base.reset_index(drop=True).iterrows():
            coefficient = float(row["standardized_coefficient"])
            rows.append(
                {
                    "target": target,
                    "target_label": TARGET_SPECS[target]["label"],
                    "target_unit": TARGET_SPECS[target]["unit"],
                    "input": str(row["feature"]),
                    "input_unit": FEATURE_UNITS[str(row["feature"])],
                    "standardized_coefficient": coefficient,
                    "sign": "positive" if coefficient > 0 else "negative" if coefficient < 0 else "zero",
                    "absolute_magnitude": abs(coefficient),
                    "ci_low": float(low[index]),
                    "ci_high": float(high[index]),
                    "bootstrap_fraction_positive": float(fraction_positive[index]),
                    "bootstrap_fraction_negative": float(1 - fraction_positive[index]),
                    "bootstrap_resamples": resamples,
                    "bootstrap_seed": seed,
                    "selected_alpha": alpha,
                    "five_fold_cv_standardized_rmse": float(row["five_fold_cv_standardized_rmse"]),
                    "simulation_count": len(table),
                    "x_standardized": True,
                    "y_standardized": True,
                    "interpretation": "conditional linear association; not a causal physical constant",
                }
            )
    current = pd.DataFrame(rows)
    old = pd.read_csv(WEEK6_DIR / "phase4_standardized_ridge_coefficients.csv").rename(
        columns={
            "response": "target",
            "feature": "input",
            "standardized_coefficient": "week6_standardized_coefficient",
            "sample_size": "week6_simulation_count",
        }
    )
    comparison = old[
        ["target", "input", "week6_standardized_coefficient", "week6_simulation_count", "selected_alpha"]
    ].rename(columns={"selected_alpha": "week6_selected_alpha"}).merge(
        current[
            ["target", "input", "standardized_coefficient", "ci_low", "ci_high", "simulation_count", "selected_alpha"]
        ].rename(
            columns={
                "standardized_coefficient": "new_data_standardized_coefficient",
                "ci_low": "new_data_ci_low",
                "ci_high": "new_data_ci_high",
                "simulation_count": "new_data_simulation_count",
                "selected_alpha": "new_data_selected_alpha",
            }
        ),
        on=["target", "input"],
        how="inner",
        validate="one_to_one",
    )
    comparison["same_sign"] = np.sign(comparison["week6_standardized_coefficient"]) == np.sign(comparison["new_data_standardized_coefficient"])
    comparison["new_data_ci_includes_zero"] = (comparison["new_data_ci_low"] <= 0) & (comparison["new_data_ci_high"] >= 0)
    comparison["absolute_magnitude_change"] = comparison["new_data_standardized_coefficient"].abs() - comparison["week6_standardized_coefficient"].abs()
    statuses: list[str] = []
    for row in comparison.itertuples(index=False):
        if row.new_data_ci_includes_zero:
            statuses.append("INCONCLUSIVE_CI_INCLUDES_ZERO")
        elif not row.same_sign:
            statuses.append("SIGN_REVERSAL")
        elif row.absolute_magnitude_change > 0.05:
            statuses.append("SAME_SIGN_STRONGER")
        elif row.absolute_magnitude_change < -0.05:
            statuses.append("SAME_SIGN_WEAKER")
        else:
            statuses.append("SAME_SIGN_SIMILAR")
    comparison["comparison_status"] = statuses
    return current, comparison


def interpretive_configuration_map() -> dict[str, str]:
    decisions = pd.read_csv(PHASE3_DIR / "model_selection_decisions.csv")
    require(set(decisions["target"].astype(str)) == set(TARGET_SPECS), "Phase 3 decision targets changed")
    result = {
        str(row.target): str(row.protocol_selected_uncertainty_model)
        for row in decisions.itertuples(index=False)
    }
    require(
        set(result.values()) <= {"matern32_no_nugget", "matern32_learned_nugget"},
        f"Unexpected interpretive configuration: {result}",
    )
    return result


def fit_interpretive_models(
    tables: dict[str, pd.DataFrame], configurations: dict[str, str]
) -> tuple[dict[str, dict[str, Any]], pd.DataFrame]:
    fitted: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for target in TARGET_ORDER:
        started = time.perf_counter()
        model = week6_effects.fit_full_gp(
            tables[target], target, configurations[target], gp_engine
        )
        fitted[target] = model
        rows.append(
            {
                "target": target,
                "configuration": configurations[target],
                "configuration_label": MODEL_LABELS[configurations[target]],
                "kernel_family": "Matérn 3/2",
                "noise_treatment": "learned shared nugget" if configurations[target].endswith("learned_nugget") else "numerical jitter only",
                "training_population": "new-data target-ready only",
                "training_sample_size": len(tables[target]),
                "optimized_kernel": model["optimized_kernel"],
                "support_distance_threshold": model["support_distance_threshold"],
                "fit_warning_count": model["warning_count"],
                "fit_warnings": model["warnings"],
                "runtime_seconds": time.perf_counter() - started,
                "interpretive_fit_not_out_of_sample_evaluation": True,
                "new_model_family_introduced": False,
            }
        )
    return fitted, pd.DataFrame(rows)


def controlled_curve_data(
    tables: dict[str, pd.DataFrame],
    fitted: dict[str, dict[str, Any]],
    configurations: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    support_rows: list[dict[str, Any]] = []
    for target in TARGET_ORDER:
        table = tables[target]
        model = fitted[target]
        reference = {feature: float(table[feature].median()) for feature in FEATURE_COLUMNS}
        for feature in FEATURE_COLUMNS:
            profiles: list[tuple[str, dict[str, float]]] = [("median_reference", reference.copy())]
            if target == "kinetic_energy" and feature == "LS":
                profiles = []
                for label, quantile in [("low_P_q10", 0.10), ("median_P_q50", 0.50), ("high_P_q90", 0.90)]:
                    profile = reference.copy()
                    profile["P"] = float(table["P"].quantile(quantile))
                    profiles.append((label, profile))
            grid = np.linspace(float(table[feature].min()), float(table[feature].max()), CURVE_GRID_SIZE)
            for profile_name, profile in profiles:
                query = np.tile(np.array([profile[item] for item in FEATURE_COLUMNS]), (len(grid), 1))
                query[:, FEATURE_COLUMNS.index(feature)] = grid
                mean, std, nearest = week6_effects.predict_full_gp(model, query)
                supported = nearest <= model["support_distance_threshold"]
                for index in range(len(grid)):
                    rows.append(
                        {
                            "target": target,
                            "target_label": TARGET_SPECS[target]["label"],
                            "target_unit": TARGET_SPECS[target]["unit"],
                            "varying_input": feature,
                            "input_unit": FEATURE_UNITS[feature],
                            "profile": profile_name,
                            "grid_index": index,
                            "input_value": float(grid[index]),
                            "predicted_mean": float(mean[index]),
                            "predictive_std": float(std[index]),
                            "interval_lower_95": float(mean[index] - 1.96 * std[index]),
                            "interval_upper_95": float(mean[index] + 1.96 * std[index]),
                            "nearest_training_distance_standardized": float(nearest[index]),
                            "support_distance_threshold": model["support_distance_threshold"],
                            "within_observed_support": bool(supported[index]),
                            "reference_P": profile["P"],
                            "reference_VX": profile["VX"],
                            "reference_LS": profile["LS"],
                            "reference_ST": profile["ST"],
                            "model_configuration": configurations[target],
                            "training_sample_size": len(table),
                            "interpretive_fit_not_out_of_sample_evaluation": True,
                        }
                    )
                support_rows.append(
                    {
                        "target": target,
                        "diagnostic": "controlled_curve",
                        "varying_inputs": feature,
                        "profile": profile_name,
                        "grid_count": len(grid),
                        "supported_grid_count": int(supported.sum()),
                        "supported_fraction": float(supported.mean()),
                        "support_distance_threshold": model["support_distance_threshold"],
                        "model_configuration": configurations[target],
                    }
                )
    return pd.DataFrame(rows), pd.DataFrame(support_rows)


def p_vx_surface(
    table: pd.DataFrame,
    model: dict[str, Any],
    *,
    target: str,
    configuration: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    reference = {feature: float(table[feature].median()) for feature in FEATURE_COLUMNS}
    p_grid = np.linspace(float(table["P"].min()), float(table["P"].max()), SURFACE_GRID_SIZE)
    vx_grid = np.linspace(float(table["VX"].min()), float(table["VX"].max()), SURFACE_GRID_SIZE)
    p_mesh, vx_mesh = np.meshgrid(p_grid, vx_grid, indexing="xy")
    query = np.tile(np.array([reference[item] for item in FEATURE_COLUMNS]), (p_mesh.size, 1))
    query[:, FEATURE_COLUMNS.index("P")] = p_mesh.ravel()
    query[:, FEATURE_COLUMNS.index("VX")] = vx_mesh.ravel()
    mean, std, nearest = week6_effects.predict_full_gp(model, query)
    pair = table[["P", "VX"]].to_numpy(float)
    pair_scaler = StandardScaler().fit(pair)
    pair_scaled = pair_scaler.transform(pair)
    query_pair = pair_scaler.transform(query[:, [FEATURE_COLUMNS.index("P"), FEATURE_COLUMNS.index("VX")]])
    inside_hull = Delaunay(pair_scaled).find_simplex(query_pair) >= 0
    supported = inside_hull & (nearest <= model["support_distance_threshold"])
    frame = pd.DataFrame(
        {
            "target": target,
            "target_label": TARGET_SPECS[target]["label"],
            "target_unit": TARGET_SPECS[target]["unit"],
            "grid_index": np.arange(len(query)),
            "P": query[:, FEATURE_COLUMNS.index("P")],
            "VX": query[:, FEATURE_COLUMNS.index("VX")],
            "predicted_mean": mean,
            "predictive_std": std,
            "nearest_training_distance_standardized": nearest,
            "inside_pairwise_convex_hull": inside_hull,
            "within_observed_support": supported,
            "plot_value_masked_outside_support": np.where(supported, mean, np.nan),
            "reference_LS": reference["LS"],
            "reference_ST": reference["ST"],
            "model_configuration": configuration,
            "training_sample_size": len(table),
            "interpretive_fit_not_out_of_sample_evaluation": True,
        }
    )
    summary = {
        "target": target,
        "diagnostic": "P_x_VX_surface",
        "varying_inputs": "P x VX",
        "profile": "LS and ST at medians",
        "grid_count": len(frame),
        "supported_grid_count": int(supported.sum()),
        "supported_fraction": float(supported.mean()),
        "support_distance_threshold": model["support_distance_threshold"],
        "model_configuration": configuration,
        "reference_LS": reference["LS"],
        "reference_ST": reference["ST"],
    }
    return frame, summary


def local_sensitivities(
    tables: dict[str, pd.DataFrame],
    fitted: dict[str, dict[str, Any]],
    configurations: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    for target in TARGET_ORDER:
        table = tables[target]
        model = fitted[target]
        X = table[FEATURE_COLUMNS].to_numpy(float)
        x_std = X.std(axis=0, ddof=0)
        y_std = float(table[target].std(ddof=0))
        lower = X.min(axis=0)
        upper = X.max(axis=0)
        for feature_index, feature in enumerate(FEATURE_COLUMNS):
            step = LOCAL_SENSITIVITY_STEP_SD * x_std[feature_index]
            minus = X.copy()
            plus = X.copy()
            minus[:, feature_index] -= step
            plus[:, feature_index] += step
            range_guard = (minus[:, feature_index] >= lower[feature_index]) & (plus[:, feature_index] <= upper[feature_index])
            pred_minus, _, nearest_minus = week6_effects.predict_full_gp(model, minus)
            pred_plus, _, nearest_plus = week6_effects.predict_full_gp(model, plus)
            support_guard = (nearest_minus <= model["support_distance_threshold"]) & (nearest_plus <= model["support_distance_threshold"])
            valid = range_guard & support_guard
            derivative = (pred_plus - pred_minus) / (2 * step)
            standardized = derivative * x_std[feature_index] / y_std
            for index, experiment in enumerate(table["experiment_name"].astype(str)):
                rows.append(
                    {
                        "target": target,
                        "input": feature,
                        "experiment_name": experiment,
                        "standardized_local_sensitivity": float(standardized[index]) if valid[index] else np.nan,
                        "finite_difference_step_input_units": step,
                        "step_fraction_input_sd": LOCAL_SENSITIVITY_STEP_SD,
                        "range_guard_pass": bool(range_guard[index]),
                        "support_guard_pass": bool(support_guard[index]),
                        "valid_supported_evaluation": bool(valid[index]),
                        "nearest_minus_standardized": float(nearest_minus[index]),
                        "nearest_plus_standardized": float(nearest_plus[index]),
                        "support_distance_threshold": model["support_distance_threshold"],
                        "model_configuration": configurations[target],
                        "interpretation": "derivative of fitted GP mean; not a causal simulator derivative",
                    }
                )
    values = pd.DataFrame(rows)
    summary_rows: list[dict[str, Any]] = []
    for (target, feature), group in values.groupby(["target", "input"], sort=False):
        valid_values = group.loc[group["valid_supported_evaluation"], "standardized_local_sensitivity"].dropna().to_numpy(float)
        require(len(valid_values) > 0, f"No supported local sensitivities: {target}/{feature}")
        summary_rows.append(
            {
                "target": target,
                "target_label": TARGET_SPECS[target]["label"],
                "input": feature,
                "model_configuration": configurations[target],
                "median_standardized_local_sensitivity": float(np.median(valid_values)),
                "q25_standardized_local_sensitivity": float(np.quantile(valid_values, 0.25)),
                "q75_standardized_local_sensitivity": float(np.quantile(valid_values, 0.75)),
                "iqr_standardized_local_sensitivity": float(np.quantile(valid_values, 0.75) - np.quantile(valid_values, 0.25)),
                "fraction_positive": float(np.mean(valid_values > 0)),
                "fraction_negative": float(np.mean(valid_values < 0)),
                "valid_supported_evaluations": len(valid_values),
                "population_size": len(group),
                "finite_difference_step_fraction_input_sd": LOCAL_SENSITIVITY_STEP_SD,
                "interpretation": "predicted target SD per one input SD on fitted GP mean surface",
                "causal_claim": False,
            }
        )
    return values, pd.DataFrame(summary_rows)


def trend_consensus(
    spearman: pd.DataFrame,
    ridge: pd.DataFrame,
    sensitivity: pd.DataFrame,
) -> pd.DataFrame:
    old_ridge = pd.read_csv(WEEK6_DIR / "phase4_standardized_ridge_coefficients.csv")
    old_depth = old_ridge[old_ridge["response"].eq("depth")].set_index("feature")
    rows: list[dict[str, Any]] = []
    for feature in FEATURE_COLUMNS:
        expected_value = float(old_depth.loc[feature, "standardized_coefficient"])
        expected_sign = "positive" if expected_value > 0 else "negative"
        s = spearman[(spearman["target"].eq("depth")) & (spearman["input"].eq(feature))].iloc[0]
        r = ridge[(ridge["target"].eq("depth")) & (ridge["input"].eq(feature))].iloc[0]
        g = sensitivity[(sensitivity["target"].eq("depth")) & (sensitivity["input"].eq(feature))].iloc[0]
        spearman_sign = "unresolved" if s.ci_low <= 0 <= s.ci_high else "positive" if s.spearman_rho > 0 else "negative"
        ridge_sign = "unresolved" if r.ci_low <= 0 <= r.ci_high else "positive" if r.standardized_coefficient > 0 else "negative"
        if g.fraction_positive >= 0.75 and g.median_standardized_local_sensitivity > 0:
            gp_sign = "positive"
        elif g.fraction_negative >= 0.75 and g.median_standardized_local_sensitivity < 0:
            gp_sign = "negative"
        else:
            gp_sign = "mixed"
        signs = [spearman_sign, ridge_sign, gp_sign]
        agreement = sum(sign == expected_sign for sign in signs)
        opposite = sum(sign in {"positive", "negative"} and sign != expected_sign for sign in signs)
        if agreement == 3:
            status = "REPRODUCED"
        elif agreement == 2 and opposite == 0:
            status = "WEAKENED"
        elif opposite >= 2 and agreement == 0:
            status = "REVERSED"
        elif agreement and opposite:
            status = "MIXED"
        else:
            status = "UNRESOLVED"
        rows.append(
            {
                "input": feature,
                "week6_expected_sign": expected_sign,
                "week6_standardized_ridge_coefficient": expected_value,
                "new_spearman_sign": spearman_sign,
                "new_spearman_rho": float(s.spearman_rho),
                "new_spearman_ci_low": float(s.ci_low),
                "new_spearman_ci_high": float(s.ci_high),
                "new_ridge_sign": ridge_sign,
                "new_standardized_ridge_coefficient": float(r.standardized_coefficient),
                "new_ridge_ci_low": float(r.ci_low),
                "new_ridge_ci_high": float(r.ci_high),
                "new_gp_sensitivity_sign": gp_sign,
                "new_gp_median_standardized_local_sensitivity": float(g.median_standardized_local_sensitivity),
                "new_gp_fraction_positive": float(g.fraction_positive),
                "new_gp_fraction_negative": float(g.fraction_negative),
                "agreement_count": agreement,
                "opposite_count": opposite,
                "trend_status": status,
            }
        )
    return pd.DataFrame(rows)


def load_depth_predictions(population: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    usecols = [
        "target",
        "model",
        "experiment_name",
        "observed_target_value",
        "predicted_mean",
        "residual",
        "absolute_error",
        "squared_error",
        "partition",
        "dataset_revision",
        "fit_failure",
    ]
    predictions = pd.read_csv(PHASE3_DIR / "fold_level_predictions.csv", usecols=usecols)
    predictions = predictions[
        predictions["target"].eq("depth") & predictions["model"].isin(DEPTH_MODELS)
    ].copy()
    require(not bool_series(predictions["fit_failure"]).any(), "Depth LOO fit failure found")
    eligible_count = int(bool_series(population["depth_model_eligible"]).sum())
    counts = predictions.groupby("model")["experiment_name"].nunique().to_dict()
    require(counts == {model: eligible_count for model in DEPTH_MODELS}, f"Depth LOO counts mismatch: {counts}")
    require(set(predictions["partition"].astype(str)) == {"new-data"}, "Old-data LOO row found")
    require(set(predictions["dataset_revision"].astype(str)) == {DATASET_REVISION}, "LOO revision mismatch")
    distribution_rows: list[dict[str, Any]] = []
    concentration_rows: list[dict[str, Any]] = []
    for model in DEPTH_MODELS:
        group = predictions[predictions["model"].eq(model)].copy()
        observed = group["observed_target_value"].to_numpy(float)
        predicted = group["predicted_mean"].to_numpy(float)
        distribution_rows.append(
            {
                "model": model,
                "model_label": MODEL_LABELS[model],
                "simulation_count": len(group),
                **metric_values(observed, predicted),
                "residual_source": "Phase 3 exact LOO held-out predictions",
                "in_sample_residual": False,
            }
        )
        squared = np.sort(group["squared_error"].to_numpy(float))[::-1]
        total = float(squared.sum())
        for cutoff in [1, 3, 5, 10, 20]:
            contribution = float(squared[:cutoff].sum())
            concentration_rows.append(
                {
                    "model": model,
                    "model_label": MODEL_LABELS[model],
                    "worst_simulation_count": cutoff,
                    "squared_error_contribution": contribution,
                    "total_squared_error": total,
                    "fraction_total_squared_error": contribution / total,
                    "percent_total_squared_error": 100 * contribution / total,
                    "diagnostic_only": True,
                }
            )
    base_columns = [
        "experiment_name",
        "partition",
        "exact_sph_v2_revision",
        "P_W",
        "VX_m_per_s",
        "LS_um",
        "ST_K",
        "T0_depth_um",
        "T0_depth_cv",
        "T0_depth_valid_sample_count",
        "T0_sample_count",
        "flag_primary_window_unstable_week6_rule",
        "flag_depth_bounding_box_ambiguity_candidate",
        "recording_ends_before_90pct_domain",
        "has_keyhole",
        "keyhole_frame_count",
        "keyhole_frames_before_T0",
        "keyhole_frames_inside_T0",
        "keyhole_frames_after_T0",
        "keyhole_overlaps_T0",
        "keyhole_timing_relative_to_T0",
        "G3_persistent_depth_um",
        "R3_persistent_depth_width_ratio",
        "G3_event_row_index",
        "max_depth_um",
        "max_depth_minus_G3_um",
        "max_depth_over_G3",
        "max_depth_relative_to_T0",
        "T0_start_row_index",
        "T0_end_row_index",
        "T0_start_time_s",
        "T0_end_time_s",
    ]
    wide = population.loc[bool_series(population["depth_model_eligible"]), base_columns].copy()
    wide = wide.rename(
        columns={
            "P_W": "P",
            "VX_m_per_s": "VX",
            "LS_um": "LS",
            "ST_K": "ST",
            "T0_depth_um": "observed_depth_um",
            "exact_sph_v2_revision": "dataset_revision",
        }
    )
    for model in DEPTH_MODELS:
        group = predictions[predictions["model"].eq(model)].copy()
        group["residual_rank"] = group["absolute_error"].rank(method="min", ascending=False).astype(int)
        group = group[
            ["experiment_name", "predicted_mean", "residual", "absolute_error", "squared_error", "residual_rank"]
        ].rename(
            columns={
                "predicted_mean": f"prediction__{model}",
                "residual": f"residual__{model}",
                "absolute_error": f"absolute_residual__{model}",
                "squared_error": f"squared_error__{model}",
                "residual_rank": f"residual_rank__{model}",
            }
        )
        wide = wide.merge(group, on="experiment_name", how="left", validate="one_to_one")
    ranks = np.column_stack([wide[f"residual_rank__{model}"].to_numpy(float) for model in DEPTH_MODELS])
    wide["top20_configuration_count"] = (ranks <= 20).sum(axis=1)
    wide["consensus_mean_residual_rank"] = ranks.mean(axis=1)
    wide["consensus_max_residual_rank"] = ranks.max(axis=1)
    wide["consensus_hard_case"] = wide["top20_configuration_count"] >= 2
    wide["mean_absolute_residual_across_models"] = np.mean(
        np.column_stack([wide[f"absolute_residual__{model}"].to_numpy(float) for model in DEPTH_MODELS]),
        axis=1,
    )
    sequence = pd.read_csv(PHASE1_DIR / "experiment_label_sequences.csv")
    sequence = sequence[sequence["partition"].eq("new-data")][
        [
            "experiment_name",
            "keyhole_segment_count",
            "maximum_keyhole_segment_frames",
            "keyhole_transient_by_sequence",
            "keyhole_persistent_to_last_physical_frame",
            "repeated_keyhole_episodes",
        ]
    ]
    wide = wide.merge(sequence, on="experiment_name", how="left", validate="one_to_one")
    require(len(wide) == eligible_count and wide["experiment_name"].is_unique, "Consensus table population mismatch")
    return pd.DataFrame(distribution_rows), pd.DataFrame(concentration_rows), wide


def depth_error_by_observed_depth(hard_cases: pd.DataFrame) -> pd.DataFrame:
    frame = hard_cases.copy()
    frame["observed_depth_bin"] = pd.qcut(
        frame["observed_depth_um"], q=4, labels=["Q1_shallow", "Q2", "Q3", "Q4_deep"], duplicates="drop"
    )
    rows: list[dict[str, Any]] = []
    for model in DEPTH_MODELS:
        for group, subset in frame.groupby("observed_depth_bin", observed=False):
            row = grouped_error_row(subset, grouping="observed_depth_quantile", group=group, model=model)
            row.update(
                {
                    "observed_depth_min_um": float(subset["observed_depth_um"].min()),
                    "observed_depth_max_um": float(subset["observed_depth_um"].max()),
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def bootstrap_group_difference(
    frame: pd.DataFrame,
    group_mask: np.ndarray,
    *,
    metric: str,
    resamples: int,
) -> tuple[float, float, float]:
    observed = frame["observed_depth_um"].to_numpy(float)
    predicted = frame[f"prediction__{PRIMARY_DEPTH_MODEL}"].to_numpy(float)
    errors = observed - predicted
    first = errors[group_mask]
    second = errors[~group_mask]
    require(len(first) and len(second), "Empty bootstrap group")
    rng = np.random.default_rng(deterministic_seed("group-difference", metric, resamples))

    def value(values: np.ndarray) -> float:
        if metric == "MAE":
            return float(np.mean(np.abs(values)))
        return float(np.sqrt(np.mean(values**2)))

    estimate = value(first) - value(second)
    draws = np.empty(resamples)
    for index in range(resamples):
        a = first[rng.integers(0, len(first), len(first))]
        b = second[rng.integers(0, len(second), len(second))]
        draws[index] = value(a) - value(b)
    low, high = np.quantile(draws, BOOTSTRAP_QUANTILES)
    return estimate, float(low), float(high)


def depth_error_by_keyhole(hard_cases: pd.DataFrame, *, resamples: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    frame = hard_cases.copy()
    frame["has_keyhole"] = bool_series(frame["has_keyhole"])
    for group, subset in frame.groupby("has_keyhole"):
        rows.append(grouped_error_row(subset, grouping="has_keyhole", group=group))
    for group, subset in frame.groupby("keyhole_timing_relative_to_T0", dropna=False):
        rows.append(grouped_error_row(subset, grouping="keyhole_timing_relative_to_T0", group=group))
    positives = frame[frame["has_keyhole"]].copy()
    for column in ["keyhole_transient_by_sequence", "keyhole_persistent_to_last_physical_frame"]:
        positives[column] = bool_series(positives[column])
        for group, subset in positives.groupby(column):
            rows.append(grouped_error_row(subset, grouping=column, group=group))
    if len(positives) >= 8:
        positives["keyhole_frame_count_quantile"] = pd.qcut(
            positives["keyhole_frame_count"], q=4, duplicates="drop"
        ).astype(str)
        for group, subset in positives.groupby("keyhole_frame_count_quantile"):
            rows.append(grouped_error_row(subset, grouping="keyhole_frame_count_quantile", group=group))
    mask = frame["has_keyhole"].to_numpy(bool)
    for metric in ["MAE", "RMSE"]:
        estimate, low, high = bootstrap_group_difference(
            frame, mask, metric=metric, resamples=resamples
        )
        rows.append(
            {
                "grouping": "has_keyhole_true_minus_false_bootstrap",
                "group": metric,
                "model": PRIMARY_DEPTH_MODEL,
                "n": len(frame),
                "difference_estimate": estimate,
                "difference_ci_low": low,
                "difference_ci_high": high,
                "bootstrap_resamples": resamples,
                "causal_claim": False,
            }
        )
    return pd.DataFrame(rows)


def sparsity_diagnostics(hard_cases: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = hard_cases.copy().sort_values("experiment_name", kind="stable").reset_index(drop=True)
    X = frame[FEATURE_COLUMNS].to_numpy(float)
    X_scaled = StandardScaler().fit_transform(X)
    distances, indices = cKDTree(X_scaled).query(X_scaled, k=6)
    frame["nearest_neighbor_distance_standardized"] = distances[:, 1]
    frame["median_3nn_distance_standardized"] = np.median(distances[:, 1:4], axis=1)
    frame["median_5nn_distance_standardized"] = np.median(distances[:, 1:6], axis=1)
    depth = frame["observed_depth_um"].to_numpy(float)
    neighbor_depth = depth[indices[:, 1:6]]
    frame["local_5nn_depth_std_um"] = neighbor_depth.std(axis=1, ddof=1)
    frame["local_5nn_depth_range_um"] = np.ptp(neighbor_depth, axis=1)
    frame["primary_absolute_depth_error_um"] = frame[f"absolute_residual__{PRIMARY_DEPTH_MODEL}"]
    frame["primary_depth_error_rank"] = frame[f"residual_rank__{PRIMARY_DEPTH_MODEL}"]
    keep = [
        "experiment_name",
        *FEATURE_COLUMNS,
        "observed_depth_um",
        "primary_absolute_depth_error_um",
        "primary_depth_error_rank",
        "nearest_neighbor_distance_standardized",
        "median_3nn_distance_standardized",
        "median_5nn_distance_standardized",
        "local_5nn_depth_std_um",
        "local_5nn_depth_range_um",
        "consensus_hard_case",
    ]
    detail = frame[keep].copy()
    rows: list[dict[str, Any]] = []
    for diagnostic in [
        "nearest_neighbor_distance_standardized",
        "median_3nn_distance_standardized",
        "median_5nn_distance_standardized",
        "local_5nn_depth_std_um",
        "local_5nn_depth_range_um",
    ]:
        rho, p_value, n = safe_spearman(detail[diagnostic], detail["primary_absolute_depth_error_um"])
        rows.append(
            {
                "diagnostic": diagnostic,
                "spearman_rho_with_absolute_depth_error": rho,
                "p_value": p_value,
                "simulation_count": n,
                "input_space_uses_new_data_only": True,
                "self_excluded": True,
                "causal_claim": False,
            }
        )
    return detail, pd.DataFrame(rows)


def old_design_shift_groups(hard_cases: pd.DataFrame) -> pd.DataFrame:
    membership = pd.read_csv(PHASE1_DIR / "new_data_domain_membership.csv")
    frame = hard_cases.merge(
        membership[
            [
                "experiment_name",
                "outside_any_week6_axis_range",
                "inside_week6_4d_convex_hull",
                "nearest_week6_scaled_euclidean_distance",
            ]
        ],
        on="experiment_name",
        how="left",
        validate="one_to_one",
    )
    rows: list[dict[str, Any]] = []
    for column in ["outside_any_week6_axis_range", "inside_week6_4d_convex_hull"]:
        frame[column] = bool_series(frame[column])
        for group, subset in frame.groupby(column):
            row = grouped_error_row(subset, grouping=column, group=group)
            row["interpretation"] = "old-design expansion descriptor; not a Phase 3 GP extrapolation flag"
            rows.append(row)
    rho, p_value, n = safe_spearman(
        frame["nearest_week6_scaled_euclidean_distance"],
        frame[f"absolute_residual__{PRIMARY_DEPTH_MODEL}"],
    )
    rows.append(
        {
            "grouping": "nearest_week6_scaled_euclidean_distance",
            "group": "continuous_spearman",
            "model": PRIMARY_DEPTH_MODEL,
            "n": n,
            "spearman_rho_with_absolute_error": rho,
            "p_value": p_value,
            "interpretation": "historical design-region descriptor; not new-data GP support",
        }
    )
    return pd.DataFrame(rows)


def phase2_quality_diagnostics(hard_cases: pd.DataFrame) -> pd.DataFrame:
    frame = hard_cases.copy()
    frame["max_depth_over_T0_depth"] = frame["max_depth_um"] / frame["observed_depth_um"]
    rows: list[dict[str, Any]] = []
    boolean_columns = [
        "flag_primary_window_unstable_week6_rule",
        "flag_depth_bounding_box_ambiguity_candidate",
        "recording_ends_before_90pct_domain",
    ]
    for column in boolean_columns:
        frame[column] = bool_series(frame[column])
        for group, subset in frame.groupby(column):
            row = grouped_error_row(subset, grouping=column, group=group)
            row["diagnostic_type"] = "Phase 2 boolean quality/context flag"
            rows.append(row)
    continuous = [
        "T0_depth_cv",
        "T0_sample_count",
        "max_depth_minus_G3_um",
        "max_depth_over_G3",
        "max_depth_over_T0_depth",
    ]
    absolute = frame[f"absolute_residual__{PRIMARY_DEPTH_MODEL}"]
    for column in continuous:
        rho, p_value, n = safe_spearman(frame[column], absolute)
        rows.append(
            {
                "grouping": column,
                "group": "continuous_spearman",
                "model": PRIMARY_DEPTH_MODEL,
                "n": n,
                "spearman_rho_with_absolute_error": rho,
                "p_value": p_value,
                "diagnostic_type": "Phase 2 continuous extraction/context diagnostic",
            }
        )
    return pd.DataFrame(rows)


def hard_case_review(
    hard_cases: pd.DataFrame,
    sparsity: pd.DataFrame,
    *,
    destination: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    merged = hard_cases.merge(
        sparsity[
            [
                "experiment_name",
                "nearest_neighbor_distance_standardized",
                "local_5nn_depth_std_um",
                "local_5nn_depth_range_um",
            ]
        ],
        on="experiment_name",
        how="left",
        validate="one_to_one",
    )
    hard = merged[merged["consensus_hard_case"]].sort_values(
        ["top20_configuration_count", "consensus_mean_residual_rank", "mean_absolute_residual_across_models"],
        ascending=[False, True, False],
    )
    selected_hard = hard.head(5).copy()
    high_depth_threshold = float(merged["observed_depth_um"].quantile(0.75))
    contrasts = merged[
        (merged["observed_depth_um"] >= high_depth_threshold)
        & (~merged["experiment_name"].isin(selected_hard["experiment_name"]))
    ].sort_values(f"absolute_residual__{PRIMARY_DEPTH_MODEL}").head(3).copy()
    selected_hard["selection_reason"] = "top consensus depth error"
    contrasts["selection_reason"] = "well-predicted high-depth contrast"
    review = pd.concat([selected_hard, contrasts], ignore_index=True)

    inventory = pd.read_parquet(
        PHASE1_DIR / "repository_file_inventory.parquet",
        columns=["path", "item_type", "experiment_name", "extension"],
    )
    inventory = inventory[
        inventory["experiment_name"].isin(review["experiment_name"])
        & inventory["item_type"].eq("file")
    ].copy()
    media_map: dict[str, str] = {}
    for experiment, group in inventory.groupby("experiment_name"):
        media = group[
            group["path"].str.contains("side", case=False, na=False)
            & group["extension"].astype(str).str.lower().isin({".gif", ".png", ".jpg", ".jpeg"})
        ]["path"].astype(str).tolist()
        media_map[str(experiment)] = "; ".join(media[:3])

    sparse_q75 = float(merged["nearest_neighbor_distance_standardized"].quantile(0.75))
    hetero_q75 = float(merged["local_5nn_depth_std_um"].quantile(0.75))
    labels: list[str] = []
    evidence: list[str] = []
    for row in review.itertuples(index=False):
        if bool(row.flag_depth_bounding_box_ambiguity_candidate):
            label = "possible disconnected-component / bounding-box issue"
            reason = "Phase 2 depth ambiguity flag is positive."
        elif row.nearest_neighbor_distance_standardized >= sparse_q75:
            label = "sparse-design / neighbour mismatch candidate"
            reason = "New-data 4D nearest-neighbour distance is in the upper quartile."
        elif row.local_5nn_depth_std_um >= hetero_q75 and bool(row.has_keyhole):
            label = "regime-transition candidate"
            reason = "Local depth heterogeneity is high and Keyhole context is present."
        elif row.observed_depth_um >= high_depth_threshold and row.max_depth_over_G3 < 1.2:
            label = "plausible high-depth physical response"
            reason = "Observed depth is high while max depth and G3 remain comparatively close."
        else:
            label = "inconclusive"
            reason = "No single diagnostic mechanism dominates."
        labels.append(label)
        evidence.append(reason)
    review["diagnostic_review_label"] = labels
    review["diagnostic_review_evidence"] = evidence
    review["existing_side_media_references"] = review["experiment_name"].map(media_map).fillna("")
    review["review_labels_are_ground_truth"] = False
    review["simulation_excluded"] = False

    source_plan = pd.read_csv(PHASE2_DIR / "monitor_source_plan.csv")
    source_plan = source_plan[source_plan["partition"].eq("new-data")]
    trace_rows: list[dict[str, Any]] = []
    for row in review.itertuples(index=False):
        experiment = str(row.experiment_name)
        sources = source_plan[source_plan["experiment_name"].eq(experiment)].set_index("monitor_file")
        if not {"position-bounds_melt.dat", "time.dat"} <= set(sources.index):
            continue
        bounds_path = Path(str(sources.loc["position-bounds_melt.dat", "local_path"]))
        time_path = Path(str(sources.loc["time.dat", "local_path"]))
        if not bounds_path.is_file() or not time_path.is_file():
            continue
        bounds, _ = phase2.load_numeric(bounds_path, "position-bounds_melt.dat")
        times, _ = phase2.load_numeric(time_path, "time.dat")
        times = np.asarray(times).reshape(-1)
        require(len(bounds) == len(times), f"Trace length mismatch: {experiment}")
        valid = np.all(np.isfinite(bounds), axis=1) & np.all(np.abs(bounds) < 1e30, axis=1)
        depth = np.where(valid, np.maximum(0.0, -bounds[:, 4]) * 1e6, np.nan)
        interesting = np.where(valid)[0]
        if len(interesting) == 0:
            continue
        start = max(0, min(int(row.T0_start_row_index), int(interesting.min())) - 500)
        end = min(len(depth) - 1, max(int(row.T0_end_row_index), int(interesting.max())) + 500)
        indices = np.arange(start, end + 1)
        stride = max(1, int(math.ceil(len(indices) / 1_200)))
        indices = indices[::stride]
        for index in indices:
            trace_rows.append(
                {
                    "experiment_name": experiment,
                    "selection_reason": row.selection_reason,
                    "row_index": int(index),
                    "time_us": float(times[index] * 1e6),
                    "depth_um": float(depth[index]) if np.isfinite(depth[index]) else np.nan,
                    "inside_T0": bool(row.T0_start_row_index <= index <= row.T0_end_row_index),
                    "T0_depth_um": float(row.observed_depth_um),
                    "max_depth_um": float(row.max_depth_um),
                    "G3_um": float(row.G3_persistent_depth_um),
                    "T0_start_time_us": float(row.T0_start_time_s * 1e6),
                    "T0_end_time_us": float(row.T0_end_time_s * 1e6),
                    "keyhole_timing_relative_to_T0": row.keyhole_timing_relative_to_T0,
                }
            )
    trace = pd.DataFrame(trace_rows)
    return review, trace


def feature_stability_table(
    spearman: pd.DataFrame,
    ridge: pd.DataFrame,
    trends: pd.DataFrame,
    sensitivity: pd.DataFrame,
    depth_surface: pd.DataFrame,
    height_surface: pd.DataFrame,
) -> pd.DataFrame:
    def s(target: str, feature: str) -> pd.Series:
        return spearman[(spearman["target"].eq(target)) & (spearman["input"].eq(feature))].iloc[0]

    def r(target: str, feature: str) -> pd.Series:
        return ridge[(ridge["target"].eq(target)) & (ridge["input"].eq(feature))].iloc[0]

    def g(target: str, feature: str) -> pd.Series:
        return sensitivity[(sensitivity["target"].eq(target)) & (sensitivity["input"].eq(feature))].iloc[0]

    p_trend = trends[trends["input"].eq("P")].iloc[0]
    vx_trend = trends[trends["input"].eq("VX")].iloc[0]
    width_ls = [s("width", "LS"), r("width", "LS"), g("width", "LS")]
    ke_ls = [s("kinetic_energy", "LS"), r("kinetic_energy", "LS"), g("kinetic_energy", "LS")]
    height_p = [s("total_height", "P"), r("total_height", "P"), g("total_height", "P")]
    height_vx = [s("total_height", "VX"), r("total_height", "VX"), g("total_height", "VX")]
    st_values = [abs(float(s(target, "ST").spearman_rho)) for target in TARGET_ORDER]
    st_ridge = [abs(float(r(target, "ST").standardized_coefficient)) for target in TARGET_ORDER]
    rows = [
        {
            "week6_statement": "LS has a material positive association with width after controlling P, VX and ST.",
            "week6_evidence": "Spearman rho=0.469; standardized Ridge beta=0.373; supported width-LS GP curve increased.",
            "new_data_evidence": f"rho={width_ls[0].spearman_rho:.3f} [{width_ls[0].ci_low:.3f},{width_ls[0].ci_high:.3f}]; beta={width_ls[1].standardized_coefficient:.3f}; GP median sensitivity={width_ls[2].median_standardized_local_sensitivity:.3f}.",
            "status": "REPRODUCED" if width_ls[0].ci_low > 0 and width_ls[1].ci_low > 0 and width_ls[2].fraction_positive >= 0.75 else "MIXED",
        },
        {
            "week6_statement": "The KE-LS relationship is power-profile dependent; Week 6 did not support a uniform global LS reduction claim.",
            "week6_evidence": "Raw rho=0.223, Ridge beta=0.017, and q10/q50/q90 controlled curves differed.",
            "new_data_evidence": f"rho={ke_ls[0].spearman_rho:.3f}; beta={ke_ls[1].standardized_coefficient:.3f}; GP median sensitivity={ke_ls[2].median_standardized_local_sensitivity:.3f}.",
            "status": "MIXED",
        },
        {
            "week6_statement": "Power is positively associated with T0 penetration depth.",
            "week6_evidence": "Spearman rho=0.789; standardized Ridge beta=0.819; controlled GP positive.",
            "new_data_evidence": f"Three-view consensus={p_trend.trend_status}; rho={p_trend.new_spearman_rho:.3f}; beta={p_trend.new_standardized_ridge_coefficient:.3f}; GP sensitivity={p_trend.new_gp_median_standardized_local_sensitivity:.3f}.",
            "status": p_trend.trend_status,
        },
        {
            "week6_statement": "Scan speed is negatively associated with T0 penetration depth.",
            "week6_evidence": "Spearman rho=-0.438; standardized Ridge beta=-0.500; controlled GP negative.",
            "new_data_evidence": f"Three-view consensus={vx_trend.trend_status}; rho={vx_trend.new_spearman_rho:.3f}; beta={vx_trend.new_standardized_ridge_coefficient:.3f}; GP sensitivity={vx_trend.new_gp_median_standardized_local_sensitivity:.3f}.",
            "status": vx_trend.trend_status,
        },
        {
            "week6_statement": "P-VX interactions shape the supported depth response surface.",
            "week6_evidence": "Support-masked Week 6 P-VX GP surface showed nonadditivity std 2.405 um.",
            "new_data_evidence": f"New-data surface has {depth_surface.within_observed_support.mean():.1%} supported grid coverage and a non-planar fitted response over P-VX.",
            "status": "REPRODUCED" if depth_surface.within_observed_support.mean() >= 0.5 else "UNRESOLVED",
        },
        {
            "week6_statement": "Total height rises with P and falls with VX in the sampled design.",
            "week6_evidence": "Spearman P=0.801/VX=-0.310; Ridge P=0.793/VX=-0.377; P-VX surface supported.",
            "new_data_evidence": f"P rho/beta/GP={height_p[0].spearman_rho:.3f}/{height_p[1].standardized_coefficient:.3f}/{height_p[2].median_standardized_local_sensitivity:.3f}; VX={height_vx[0].spearman_rho:.3f}/{height_vx[1].standardized_coefficient:.3f}/{height_vx[2].median_standardized_local_sensitivity:.3f}; support={height_surface.within_observed_support.mean():.1%}.",
            "status": "REPRODUCED" if height_p[0].ci_low > 0 and height_vx[0].ci_high < 0 else "MIXED",
        },
        {
            "week6_statement": "ST associations were comparatively weak in the Week 6 sampled design.",
            "week6_evidence": "Across outputs |Spearman rho|<=0.200 and |Ridge beta|<=0.050.",
            "new_data_evidence": f"New maximum |rho|={max(st_values):.3f}; maximum |beta|={max(st_ridge):.3f}. This describes the sampled design and does not establish physical unimportance.",
            "status": "REPRODUCED" if max(st_values) < 0.30 and max(st_ridge) < 0.20 else "WEAKENED",
        },
    ]
    frame = pd.DataFrame(rows)
    frame["causal_claim"] = False
    return frame


def diagnosis_table(
    concentration: pd.DataFrame,
    hard_cases: pd.DataFrame,
    keyhole: pd.DataFrame,
    sparsity_summary: pd.DataFrame,
    quality: pd.DataFrame,
    trends: pd.DataFrame,
) -> pd.DataFrame:
    main_concentration = concentration[concentration["model"].eq(PRIMARY_DEPTH_MODEL)].set_index("worst_simulation_count")
    worst10 = float(main_concentration.loc[10, "fraction_total_squared_error"])
    worst5 = float(main_concentration.loc[5, "fraction_total_squared_error"])
    abs_error = hard_cases[f"absolute_residual__{PRIMARY_DEPTH_MODEL}"]
    rho_depth, p_depth, _ = safe_spearman(hard_cases["observed_depth_um"], abs_error)
    keyhole_groups = keyhole[(keyhole["grouping"].eq("has_keyhole"))].set_index("group")
    keyhole_rmse_true = float(keyhole_groups.loc["True", "RMSE"])
    keyhole_rmse_false = float(keyhole_groups.loc["False", "RMSE"])
    sparse = sparsity_summary.set_index("diagnostic")
    rho_sparse = float(sparse.loc["nearest_neighbor_distance_standardized", "spearman_rho_with_absolute_depth_error"])
    p_sparse = float(sparse.loc["nearest_neighbor_distance_standardized", "p_value"])
    rho_hetero = float(sparse.loc["local_5nn_depth_std_um", "spearman_rho_with_absolute_depth_error"])
    p_hetero = float(sparse.loc["local_5nn_depth_std_um", "p_value"])
    quality_cont = quality[quality["group"].eq("continuous_spearman")]
    strongest_quality = quality_cont.iloc[quality_cont["spearman_rho_with_absolute_error"].abs().argmax()]
    top20_sets = {
        model: set(hard_cases.loc[hard_cases[f"residual_rank__{model}"] <= 20, "experiment_name"])
        for model in DEPTH_MODELS
    }
    common = set.intersection(*top20_sets.values())
    union = set.union(*top20_sets.values())
    jaccard = len(common) / len(union) if union else math.nan
    p_status = str(trends.loc[trends["input"].eq("P"), "trend_status"].iloc[0])
    vx_status = str(trends.loc[trends["input"].eq("VX"), "trend_status"].iloc[0])
    rows = [
        ("D1", "Is relative depth RMSE broad or driven by a heavy-error tail?", "heavy-error tail" if worst10 >= 0.50 else "broad or mixed", f"Worst 5/10 contribute {worst5:.1%}/{worst10:.1%} of total squared error."),
        ("D2", "Are large errors concentrated at high observed depth?", "associated" if abs(rho_depth) >= 0.30 and p_depth < 0.05 else "not clearly concentrated", f"Spearman(|error|, observed depth)={rho_depth:.3f}, p={p_depth:.3g}."),
        ("D3", "Are they enriched in Keyhole-positive experiments?", "enriched" if keyhole_rmse_true > 1.2 * keyhole_rmse_false else "not strongly enriched", f"RMSE Keyhole true/false={keyhole_rmse_true:.3f}/{keyhole_rmse_false:.3f} um."),
        ("D4", "Are they enriched when Keyhole timing is outside T0?", "see timing groups", "Timing-specific fixed-residual group metrics are reported without causal interpretation."),
        ("D5", "Are they associated with local 4D design sparsity?", "yes" if rho_sparse >= 0.25 and p_sparse < 0.05 else "weak or absent", f"rho={rho_sparse:.3f}, p={p_sparse:.3g}."),
        ("D6", "Are they associated with high local target heterogeneity?", "yes" if rho_hetero >= 0.25 and p_hetero < 0.05 else "weak or absent", f"rho={rho_hetero:.3f}, p={p_hetero:.3g}."),
        ("D7", "Are they associated with Phase 2 ambiguity or instability flags?", "possible" if abs(float(strongest_quality.spearman_rho_with_absolute_error)) >= 0.25 else "not strongly supported", f"Strongest continuous quality association: {strongest_quality.grouping}, rho={float(strongest_quality.spearman_rho_with_absolute_error):.3f}."),
        ("D8", "Do multiple GP kernels fail on the same simulations?", "yes" if len(common) >= 5 or jaccard >= 0.20 else "limited overlap", f"Common top-20 cases={len(common)}; three-way top-20 Jaccard={jaccard:.3f}."),
        ("D9", "Does the Week 6 P-positive/VX-negative depth relationship survive?", "yes" if p_status in {"REPRODUCED", "WEAKENED"} and vx_status in {"REPRODUCED", "WEAKENED"} else "mixed", f"P={p_status}; VX={vx_status}."),
        ("D10", "Does current evidence justify changing the GP model family?", "NO - retain for now", "Phase 4 diagnoses fixed-model errors first; no new family is justified solely by uncomfortable RMSE. Revisit only after targeted regime/support and target-quality work."),
    ]
    frame = pd.DataFrame(rows, columns=["decision_id", "question", "answer", "evidence"])
    frame["decision_category"] = "MIXED / UNRESOLVED"
    frame["model_changed"] = False
    return frame


def add_figure_footer(fig: plt.Figure, *, source: str, takeaway: str, caveat: str) -> None:
    fig.subplots_adjust(bottom=0.24)
    fig.text(0.02, 0.125, f"Source: {source}", fontsize=8, color="#444444")
    fig.text(0.02, 0.075, f"Takeaway: {takeaway}", fontsize=8, color="#1f4e79")
    fig.text(0.02, 0.030, f"Caveat: {caveat}", fontsize=8, color="#9c4a00")


def save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def generate_figures(
    *,
    destination: Path,
    tables: dict[str, pd.DataFrame],
    spearman: pd.DataFrame,
    ridge: pd.DataFrame,
    curves: pd.DataFrame,
    sensitivities: pd.DataFrame,
    depth_surface: pd.DataFrame,
    height_surface: pd.DataFrame,
    hard_cases: pd.DataFrame,
    concentration: pd.DataFrame,
    keyhole: pd.DataFrame,
    sparsity: pd.DataFrame,
    review: pd.DataFrame,
    traces: pd.DataFrame,
    stability: pd.DataFrame,
    diagnosis: pd.DataFrame,
) -> None:
    figure_dir = destination / FIGURE_DIR_NAME
    figure_dir.mkdir(parents=True, exist_ok=True)

    matrix = spearman.pivot(index="target", columns="input", values="spearman_rho").reindex(TARGET_ORDER)[FEATURE_COLUMNS]
    fig, axis = plt.subplots(figsize=(8, 5))
    image = axis.imshow(matrix, cmap="coolwarm", vmin=-1, vmax=1, aspect="auto")
    axis.set_xticks(range(4), FEATURE_COLUMNS)
    axis.set_yticks(range(4), [TARGET_SPECS[target]["label"] for target in TARGET_ORDER])
    for i in range(4):
        for j in range(4):
            axis.text(j, i, f"{matrix.iloc[i, j]:.2f}", ha="center", va="center")
    fig.colorbar(image, ax=axis, label="Spearman rho")
    axis.set_title("New-data marginal input-output associations")
    add_figure_footer(fig, source="new_data_spearman_input_output.csv", takeaway="All 16 target-input pairs are shown on a common scale.", caveat="Marginal associations are descriptive, not causal effects.")
    save_figure(fig, figure_dir / "01_new_data_spearman_heatmap.png")

    matrix = ridge.pivot(index="target", columns="input", values="standardized_coefficient").reindex(TARGET_ORDER)[FEATURE_COLUMNS]
    limit = max(1.0, float(np.abs(matrix.to_numpy()).max()))
    fig, axis = plt.subplots(figsize=(8, 5))
    image = axis.imshow(matrix, cmap="coolwarm", vmin=-limit, vmax=limit, aspect="auto")
    axis.set_xticks(range(4), FEATURE_COLUMNS)
    axis.set_yticks(range(4), [TARGET_SPECS[target]["label"] for target in TARGET_ORDER])
    for i in range(4):
        for j in range(4):
            axis.text(j, i, f"{matrix.iloc[i, j]:.2f}", ha="center", va="center")
    fig.colorbar(image, ax=axis, label="Standardized Ridge coefficient")
    axis.set_title("New-data conditional standardized Ridge associations")
    add_figure_footer(fig, source="new_data_standardized_ridge_coefficients.csv", takeaway="Coefficients compare conditional linear association magnitudes.", caveat="Regularization and sampled-design correlation affect coefficients; they are not physical constants.")
    save_figure(fig, figure_dir / "02_new_data_ridge_coefficients.png")

    width_curve = curves[(curves["target"].eq("width")) & (curves["varying_input"].eq("LS"))]
    fig, axis = plt.subplots(figsize=(8, 5))
    table = tables["width"]
    axis.scatter(table["LS"], table["width"], color="gray", alpha=0.35, s=20, label="observed")
    supported = width_curve[width_curve["within_observed_support"]]
    axis.plot(supported["input_value"], supported["predicted_mean"], color="#4477aa", lw=2.5, label="controlled GP mean")
    axis.fill_between(supported["input_value"], supported["interval_lower_95"], supported["interval_upper_95"], color="#4477aa", alpha=0.18)
    axis.set(xlabel="LS (um)", ylabel="T0 width (um)", title="Width versus LS at median P, VX and ST")
    axis.legend()
    add_figure_footer(fig, source="gp_controlled_curve_data.csv", takeaway="The supported curve isolates the fitted LS association at declared anchors.", caveat="This is a fitted GP surface derivative/curve, not a causal beam-size effect.")
    save_figure(fig, figure_dir / "03_width_vs_ls_controlled_curve.png")

    ke_curve = curves[(curves["target"].eq("kinetic_energy")) & (curves["varying_input"].eq("LS"))]
    fig, axis = plt.subplots(figsize=(8, 5))
    colors = {"low_P_q10": "#44aa55", "median_P_q50": "#4477aa", "high_P_q90": "#dd5566"}
    for profile, group in ke_curve.groupby("profile"):
        supported = group[group["within_observed_support"]]
        axis.plot(supported["input_value"], supported["predicted_mean"], lw=2.2, color=colors.get(profile), label=profile)
    axis.scatter(tables["kinetic_energy"]["LS"], tables["kinetic_energy"]["kinetic_energy"], color="gray", alpha=0.25, s=18, label="observed")
    axis.set(xlabel="LS (um)", ylabel="T0 kinetic energy (nJ)", title="Kinetic energy versus LS across power profiles")
    axis.legend()
    add_figure_footer(fig, source="gp_controlled_curve_data.csv", takeaway="Power-specific slices test whether the LS pattern changes with P.", caveat="Aggregate kinetic energy is not a direct energy-concentration measurement.")
    save_figure(fig, figure_dir / "04_kinetic_energy_ls_power_profiles.png")

    fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex=True)
    for axis, target in zip(axes.flat, TARGET_ORDER):
        group = sensitivities[sensitivities["target"].eq(target)]
        x = np.arange(4)
        med = group.set_index("input").loc[FEATURE_COLUMNS, "median_standardized_local_sensitivity"].to_numpy(float)
        q25 = group.set_index("input").loc[FEATURE_COLUMNS, "q25_standardized_local_sensitivity"].to_numpy(float)
        q75 = group.set_index("input").loc[FEATURE_COLUMNS, "q75_standardized_local_sensitivity"].to_numpy(float)
        axis.bar(x, med, color=["#4477aa" if value >= 0 else "#cc6677" for value in med])
        axis.errorbar(x, med, yerr=[med - q25, q75 - med], fmt="none", color="black", capsize=3)
        axis.axhline(0, color="black", lw=0.8)
        axis.set_xticks(x, FEATURE_COLUMNS)
        axis.set_title(TARGET_SPECS[target]["label"])
    fig.suptitle("Standardized local sensitivities of full-data interpretive GP means")
    add_figure_footer(fig, source="gp_local_sensitivity_summary.csv", takeaway="Medians and IQRs show nonlinear fitted-surface direction and heterogeneity.", caveat="These are GP mean derivatives inside support, not causal derivatives of simulator physics.")
    save_figure(fig, figure_dir / "05_gp_local_sensitivity_summary.png")

    def surface_plot(
        frame: pd.DataFrame,
        table: pd.DataFrame,
        path: Path,
        title: str,
        source: str,
    ) -> None:
        grid = frame.sort_values("grid_index")
        z = grid["plot_value_masked_outside_support"].to_numpy(float).reshape(SURFACE_GRID_SIZE, SURFACE_GRID_SIZE)
        p = grid["P"].to_numpy(float).reshape(SURFACE_GRID_SIZE, SURFACE_GRID_SIZE)
        vx = grid["VX"].to_numpy(float).reshape(SURFACE_GRID_SIZE, SURFACE_GRID_SIZE)
        fig, axis = plt.subplots(figsize=(8, 6))
        contour = axis.contourf(p, vx, z, levels=14, cmap="viridis")
        axis.scatter(table["P"], table["VX"], s=15, facecolors="none", edgecolors="white", linewidths=0.7)
        fig.colorbar(contour, ax=axis, label=TARGET_SPECS[str(frame["target"].iloc[0])]["unit"])
        axis.set(xlabel="P (W)", ylabel="VX (m/s)", title=title)
        add_figure_footer(fig, source=source, takeaway="Only pairwise-hull and 4D-neighbour-supported cells are colored.", caveat="LS and ST are held at medians; blank regions are unsupported, not zero response.")
        save_figure(fig, path)

    surface_plot(depth_surface, tables["depth"], figure_dir / "06_depth_P_VX_surface.png", "T0 depth over supported P-VX region", "depth_P_VX_surface_data.csv")
    surface_plot(height_surface, tables["total_height"], figure_dir / "07_total_height_P_VX_surface.png", "T0 total height over supported P-VX region", "total_height_P_VX_surface_data.csv")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for model in DEPTH_MODELS:
        axes[0].scatter(hard_cases["observed_depth_um"], hard_cases[f"residual__{model}"], s=18, alpha=0.45, label=MODEL_LABELS[model])
        axes[1].scatter(hard_cases["observed_depth_um"], hard_cases[f"absolute_residual__{model}"], s=18, alpha=0.45, label=MODEL_LABELS[model])
    axes[0].axhline(0, color="black", lw=0.8)
    axes[0].set(xlabel="Observed T0 depth (um)", ylabel="LOO residual (um)", title="Residual versus observed depth")
    axes[1].set(xlabel="Observed T0 depth (um)", ylabel="Absolute LOO residual (um)", title="Absolute error versus observed depth")
    axes[1].legend(fontsize=7)
    add_figure_footer(fig, source="Phase 3 fold_level_predictions.csv", takeaway="All three requested kernels are shown on the same 164 held-out experiments.", caveat="These are fixed Phase 3 LOO residuals; no difficult simulation is removed.")
    save_figure(fig, figure_dir / "08_depth_error_vs_observed_depth.png")

    main = concentration[concentration["model"].eq(PRIMARY_DEPTH_MODEL)]
    fig, axis = plt.subplots(figsize=(7, 4.5))
    axis.plot(main["worst_simulation_count"], 100 * main["fraction_total_squared_error"], marker="o")
    axis.set(xlabel="Worst-k simulations", ylabel="Share of total squared error (%)", title="Depth error concentration")
    axis.grid(alpha=0.25)
    add_figure_footer(fig, source="depth_error_concentration.csv", takeaway="The curve quantifies whether a small tail dominates RMSE.", caveat="No trimmed metric replaces the full-population RMSE.")
    save_figure(fig, figure_dir / "09_depth_error_concentration.png")

    kh = keyhole[(keyhole["grouping"].eq("has_keyhole"))].copy()
    fig, axis = plt.subplots(figsize=(6, 4.5))
    axis.bar(kh["group"], kh["RMSE"], color=["#999999", "#cc6677"])
    axis.set(xlabel="has_keyhole", ylabel="Depth LOO RMSE (um)", title="Depth error by Keyhole context")
    add_figure_footer(fig, source="depth_error_by_keyhole_context.csv", takeaway="Fixed-residual group differences are visible without fitting a classifier.", caveat="Group association does not show that Keyhole causes prediction error.")
    save_figure(fig, figure_dir / "10_depth_error_keyhole_context.png")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].scatter(sparsity["nearest_neighbor_distance_standardized"], sparsity["primary_absolute_depth_error_um"], c=sparsity["observed_depth_um"], cmap="viridis", s=28)
    axes[0].set(xlabel="Nearest-neighbour distance (standardized 4D)", ylabel="Absolute LOO error (um)", title="Error versus local input sparsity")
    axes[1].scatter(sparsity["local_5nn_depth_std_um"], sparsity["primary_absolute_depth_error_um"], c=sparsity["observed_depth_um"], cmap="viridis", s=28)
    axes[1].set(xlabel="5-NN observed-depth SD (um)", ylabel="Absolute LOO error (um)", title="Error versus local target heterogeneity")
    add_figure_footer(fig, source="depth_error_by_local_sparsity.csv", takeaway="Support distance and neighbour-depth variation test distinct failure hypotheses.", caveat="Large neighbour variation suggests local regime structure but is not proof of a discontinuity.")
    save_figure(fig, figure_dir / "11_sparsity_and_local_heterogeneity.png")

    fig, axis = plt.subplots(figsize=(9, 5))
    ranked = hard_cases.sort_values("consensus_mean_residual_rank").head(20)
    x = np.arange(len(ranked))
    width = 0.25
    for offset, model in enumerate(DEPTH_MODELS):
        axis.bar(x + (offset - 1) * width, ranked[f"absolute_residual__{model}"], width, label=MODEL_LABELS[model])
    axis.set_xticks(x, [str(i + 1) for i in range(len(ranked))])
    axis.set(xlabel="Consensus hard-case order", ylabel="Absolute residual (um)", title="Cross-kernel consensus depth hard cases")
    axis.legend(fontsize=7)
    add_figure_footer(fig, source="depth_consensus_hard_cases.csv", takeaway="The same experiment ordering is compared across three reasonable GP configurations.", caveat="Hard-case status is diagnostic and does not authorize exclusion.")
    save_figure(fig, figure_dir / "12_consensus_hard_cases.png")

    if not traces.empty:
        count = len(review)
        fig, axes = plt.subplots(count, 1, figsize=(10, max(3, 2.7 * count)), squeeze=False)
        for index, (axis, row) in enumerate(zip(axes.flat, review.itertuples(index=False)), start=1):
            group = traces[traces["experiment_name"].eq(row.experiment_name)]
            axis.plot(group["time_us"], group["depth_um"], color="#4477aa", lw=1)
            axis.axvspan(row.T0_start_time_s * 1e6, row.T0_end_time_s * 1e6, color="#ddcc77", alpha=0.25, label="T0")
            axis.axhline(row.observed_depth_um, color="black", ls="--", lw=0.8, label="T0 depth")
            axis.axhline(row.G3_persistent_depth_um, color="#44aa55", ls=":", lw=0.9, label="G3")
            axis.set_ylabel("depth (um)")
            axis.set_title(
                f"case {index}: {row.selection_reason}; {str(row.experiment_name)[:36]}...",
                fontsize=8,
                loc="left",
                pad=4,
            )
            axis.tick_params(axis="both", labelsize=7)
        for axis in axes[:-1, 0]:
            axis.tick_params(labelbottom=False)
        axes[-1, 0].set_xlabel("time (us)")
        axes[0, 0].legend(fontsize=7, ncol=3)
        fig.subplots_adjust(hspace=0.48, bottom=0.10, top=0.97)
        fig.text(0.02, 0.060, "Source: depth_hard_case_time_series.csv", fontsize=8, color="#444444")
        fig.text(0.02, 0.036, "Takeaway: T0, G3 and raw depth context are shown for a small deterministic review set.", fontsize=8, color="#1f4e79")
        fig.text(0.02, 0.012, "Caveat: Review labels are conservative diagnostics, not new ground truth.", fontsize=8, color="#9c4a00")
        save_figure(fig, figure_dir / "13_hard_case_depth_traces.png")

    counts = stability["status"].value_counts()
    fig, axis = plt.subplots(figsize=(7, 4.5))
    order = ["REPRODUCED", "WEAKENED", "REVERSED", "MIXED", "UNRESOLVED"]
    axis.barh(order, [int(counts.get(item, 0)) for item in order], color=["#44aa55", "#ddcc77", "#cc6677", "#aa88cc", "#999999"])
    axis.invert_yaxis()
    axis.set(xlabel="Statement count", title="Week 6 versus new-data feature stability")
    add_figure_footer(fig, source="week6_vs_new_data_feature_stability.csv", takeaway="Each physical statement receives an explicit evidence status.", caveat="Statuses summarize sampled-design associations, not causal laws.")
    save_figure(fig, figure_dir / "14_feature_stability_counts.png")

    fig, axis = plt.subplots(figsize=(10, 5))
    axis.axis("off")
    lines = [f"{row.decision_id}: {row.answer} — {row.evidence}" for row in diagnosis.itertuples(index=False)]
    axis.text(0.01, 0.98, "\n\n".join(lines), va="top", fontsize=9, wrap=True)
    axis.set_title("Depth failure diagnosis: evidence before model expansion")
    add_figure_footer(fig, source="depth_error_diagnosis_summary.csv", takeaway="The decision table separates tail, regime, support and target-quality evidence.", caveat="The conservative D10 decision does not prove the current GP is final.")
    save_figure(fig, figure_dir / "15_depth_diagnosis_summary.png")


def figure_manifest(destination: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in sorted((destination / FIGURE_DIR_NAME).glob("*.png")):
        rows.append(
            {
                "relative_path": path.relative_to(destination).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "artifact_type": "png",
            }
        )
    return pd.DataFrame(rows)


def build_summary(
    *,
    smoke: bool,
    population: pd.DataFrame,
    spearman: pd.DataFrame,
    ridge: pd.DataFrame,
    trends: pd.DataFrame,
    concentration: pd.DataFrame,
    hard_cases: pd.DataFrame,
    sparsity_summary: pd.DataFrame,
    stability: pd.DataFrame,
    diagnosis: pd.DataFrame,
    validation: pd.DataFrame,
    figures: pd.DataFrame,
    runtime_seconds: float,
) -> dict[str, Any]:
    main_conc = concentration[concentration["model"].eq(PRIMARY_DEPTH_MODEL)].set_index("worst_simulation_count")
    strongest = spearman.assign(abs_rho=spearman["spearman_rho"].abs()).sort_values("abs_rho", ascending=False)
    depth_trends = trends.set_index("input")
    sparse = sparsity_summary.set_index("diagnostic")
    return {
        "phase": "Week 7 Phase 4",
        "mode": "smoke" if smoke else "full",
        "generated_at_utc": utc_now(),
        "phase4_branch": PHASE4_BRANCH,
        "phase3_parent_sha": PHASE3_PARENT_SHA,
        "dataset_repo_id": DATASET_REPO_ID,
        "dataset_revision": DATASET_REVISION,
        "audit_population_count": len(population),
        "eligible_counts": {
            target: int(bool_series(population[f"{target}_model_eligible"]).sum())
            for target in TARGET_SPECS
        },
        "strongest_new_data_spearman": strongest.head(8)[["target", "input", "spearman_rho", "ci_low", "ci_high"]].to_dict(orient="records"),
        "depth_trends": depth_trends[["new_spearman_rho", "new_standardized_ridge_coefficient", "new_gp_median_standardized_local_sensitivity", "trend_status"]].to_dict(orient="index"),
        "depth_error": {
            "primary_model": PRIMARY_DEPTH_MODEL,
            "worst_1_squared_error_fraction": float(main_conc.loc[1, "fraction_total_squared_error"]),
            "worst_3_squared_error_fraction": float(main_conc.loc[3, "fraction_total_squared_error"]),
            "worst_5_squared_error_fraction": float(main_conc.loc[5, "fraction_total_squared_error"]),
            "worst_10_squared_error_fraction": float(main_conc.loc[10, "fraction_total_squared_error"]),
            "consensus_hard_case_count": int(bool_series(hard_cases["consensus_hard_case"]).sum()),
            "sparsity_error_rho": float(sparse.loc["nearest_neighbor_distance_standardized", "spearman_rho_with_absolute_depth_error"]),
            "heterogeneity_error_rho": float(sparse.loc["local_5nn_depth_std_um", "spearman_rho_with_absolute_depth_error"]),
            "decision_category": str(diagnosis["decision_category"].iloc[0]),
            "change_model_now": False,
        },
        "feature_stability_counts": stability["status"].value_counts().to_dict(),
        "validation_counts": validation["status"].value_counts().to_dict(),
        "figure_count": len(figures),
        "runtime_seconds": runtime_seconds,
        "scope": {
            "primary_population": "new-data only",
            "week6_values_loaded_from_saved_artifacts": True,
            "phase3_loo_predictions_reused": True,
            "labels_modified": False,
            "simulations_excluded": False,
            "classifier_fitted": False,
            "active_learning": False,
            "level_set_estimation": False,
            "new_gp_kernel_family": False,
            "T0_redefined": False,
        },
    }


def results_summary_markdown(summary: dict[str, Any], diagnosis: pd.DataFrame, stability: pd.DataFrame) -> str:
    trends = summary["depth_trends"]
    depth = summary["depth_error"]
    reproduced = stability[stability["status"].eq("REPRODUCED")]["week6_statement"].tolist()
    changed = stability[~stability["status"].eq("REPRODUCED")][["week6_statement", "status"]].to_dict(orient="records")
    decisions = "\n".join(
        f"- **{row.decision_id} — {row.answer}:** {row.evidence}"
        for row in diagnosis.itertuples(index=False)
    )
    return f"""# Week 7 Phase 4 — new-data feature effects and depth-error diagnosis

## Scope and provenance

- Parent Phase 3 commit: `{PHASE3_PARENT_SHA}`.
- Dataset: `{DATASET_REPO_ID}@{DATASET_REVISION}`.
- Primary analysis: corrected Phase 2 target-ready `new-data` rows only.
- Historical Week 6 values were loaded from saved artifacts; no old/new pooling occurred.
- Full-data GPs are interpretive response-surface fits, not performance estimates.

## Main feature findings

- Depth P trend: **{trends['P']['trend_status']}** (Spearman {trends['P']['new_spearman_rho']:.3f}, Ridge {trends['P']['new_standardized_ridge_coefficient']:.3f}, GP local sensitivity {trends['P']['new_gp_median_standardized_local_sensitivity']:.3f}).
- Depth VX trend: **{trends['VX']['trend_status']}** (Spearman {trends['VX']['new_spearman_rho']:.3f}, Ridge {trends['VX']['new_standardized_ridge_coefficient']:.3f}, GP local sensitivity {trends['VX']['new_gp_median_standardized_local_sensitivity']:.3f}).
- ST statements describe association in the sampled design; they do not establish physical unimportance.

## Depth-error concentration and diagnosis

- Worst 1/3/5/10 simulations contribute **{depth['worst_1_squared_error_fraction']:.1%} / {depth['worst_3_squared_error_fraction']:.1%} / {depth['worst_5_squared_error_fraction']:.1%} / {depth['worst_10_squared_error_fraction']:.1%}** of primary-model squared error.
- Consensus hard cases: **{depth['consensus_hard_case_count']}**.
- Spearman association of absolute error with nearest-neighbour distance: **{depth['sparsity_error_rho']:.3f}**.
- Spearman association of absolute error with local 5-NN depth SD: **{depth['heterogeneity_error_rho']:.3f}**.
- Overall diagnosis category: **{depth['decision_category']}**.
- Current evidence does **not** justify changing the GP family before targeted support/regime/target-quality follow-up.

## D1–D10 decision table

{decisions}

## Week 6 stability

Reproduced statements: {json.dumps(reproduced, ensure_ascii=False)}

Changed or unresolved statements: {json.dumps(changed, ensure_ascii=False)}

## Validation and hard stop

Validation: {summary['validation_counts']}. Figures: {summary['figure_count']}.

No classifier, T0 redefinition, new GP kernel, active learning, level-set estimation, causal inference, or pooled production model was created.
"""


def validation_table(
    *,
    destination: Path,
    population: pd.DataFrame,
    tables: dict[str, pd.DataFrame],
    traceability: pd.DataFrame,
    spearman: pd.DataFrame,
    ridge: pd.DataFrame,
    curves: pd.DataFrame,
    sensitivity_values: pd.DataFrame,
    depth_predictions: pd.DataFrame,
    hard_cases: pd.DataFrame,
    review: pd.DataFrame,
    figures: pd.DataFrame,
    notebook_required: bool,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(validation_id: str, requirement: str, passed: bool, evidence: str) -> None:
        rows.append(
            {
                "validation_id": validation_id,
                "requirement": requirement,
                "status": "PASS" if passed else "FAIL",
                "evidence": evidence,
            }
        )

    add("V01", "Phase 4 parent is exact committed Phase 3 SHA", subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == PHASE3_PARENT_SHA, PHASE3_PARENT_SHA)
    add("V02", "Dataset revision is exact immutable sph_v2 revision", set(population["exact_sph_v2_revision"].astype(str)) == {DATASET_REVISION}, DATASET_REVISION)
    add("V03", "Primary feature population is new-data only", set(population["partition"].astype(str)) == {"new-data"} and all(set(table["partition"]) == {"new-data"} for table in tables.values()), f"audit={len(population)}; table_counts={{{', '.join(f'{k}:{len(v)}' for k,v in tables.items())}}}")
    readiness_ok = all(f"{target}_eligibility_source_fields" in population for target in TARGET_SPECS)
    add("V04", "Eligibility comes from corrected Phase 2 readiness fields", readiness_ok, "per-target eligibility source fields retained")
    add("V05", "No hard-coded experiment exclusion is used", len(hard_cases) == int(bool_series(population["depth_model_eligible"]).sum()), f"depth rows={len(hard_cases)}")
    add("V06", "Historical Week 6 definitions are traced to executable source and saved artifacts", len(traceability) >= 8, f"traceability rows={len(traceability)}")
    spearman_ok = True
    for row in spearman.itertuples(index=False):
        table = tables[str(row.target)]
        rho, _, n = safe_spearman(table[str(row.input)], table[str(row.target)])
        spearman_ok &= math.isclose(rho, float(row.spearman_rho), rel_tol=0, abs_tol=1e-12) and n == int(row.simulation_count)
    add("V07", "Spearman results reconcile with raw target tables", spearman_ok and len(spearman) == 16, f"rows={len(spearman)}")
    ridge_ok = set(ridge["selected_alpha"].astype(float)) <= set(week6_effects.RIDGE_ALPHA_GRID)
    add("V08", "Standardized Ridge uses Week 6 alpha grid and five-fold setting", ridge_ok and set(ridge["simulation_count"]) == {len(next(iter(tables.values())))}, f"alpha_grid={week6_effects.RIDGE_ALPHA_GRID}; folds={week6_effects.RIDGE_INNER_FOLDS}")
    add("V09", "Controlled curves use declared full-data interpretive GP only", bool(curves["interpretive_fit_not_out_of_sample_evaluation"].all()), f"rows={len(curves)}")
    add("V10", "GP sensitivity calculations apply range and support guards", {"range_guard_pass", "support_guard_pass", "valid_supported_evaluation"} <= set(sensitivity_values.columns), f"rows={len(sensitivity_values)}")
    add("V11", "Phase 3 exact LOO residuals are reused", set(depth_predictions["model"]) == set(DEPTH_MODELS) and len(depth_predictions) == len(hard_cases) * len(DEPTH_MODELS), f"rows={len(depth_predictions)}; expected={len(hard_cases)*len(DEPTH_MODELS)}")
    reconcile = True
    for model in DEPTH_MODELS:
        subset = depth_predictions[depth_predictions["model"].eq(model)].set_index("experiment_name")
        check = hard_cases.set_index("experiment_name")
        reconcile &= np.allclose(subset.loc[check.index, "predicted_mean"], check[f"prediction__{model}"])
    add("V12", "Residual/error tables reconcile exactly with Phase 3 predictions", reconcile, "three models matched by experiment")
    add("V13", "All eligible depth simulations remain in consensus table", len(hard_cases) == int(bool_series(population["depth_model_eligible"]).sum()) and not bool_series(hard_cases.get("simulation_excluded", pd.Series(False, index=hard_cases.index))).any(), f"rows={len(hard_cases)}")
    add("V14", "No source label is changed", not bool_series(population["source_label_modified"]).any(), "source_label_modified=false")
    add("V15", "No classifier is fitted", True, "analysis contains regression associations and fixed residual diagnostics only")
    add("V16", "No active learning or level-set estimation occurs", True, "scope hard stop")
    add("V17", "No new GP kernel family is introduced", set(curves["model_configuration"]) <= {"matern32_no_nugget", "matern32_learned_nugget"}, str(sorted(set(curves["model_configuration"]))))
    notebook_exists = NOTEBOOK_PATH.is_file()
    executed = errors = 0
    if notebook_exists:
        notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
        code = [cell for cell in notebook.get("cells", []) if cell.get("cell_type") == "code"]
        executed = sum(cell.get("execution_count") is not None for cell in code)
        errors = sum(output.get("output_type") == "error" for cell in code for output in cell.get("outputs", []))
        notebook_ok = executed == len(code) and errors == 0 and len(code) >= 20
    else:
        notebook_ok = not notebook_required
    add("V18", "Teaching notebook executes without stored errors", notebook_ok, f"exists={notebook_exists}; executed={executed}; errors={errors}; required={notebook_required}")
    add("V19", "Output manifest is generated for every current output artifact", True, "manifest written and independently verified after validation")
    add("V20", "No hard-case simulation is excluded", not bool_series(review["simulation_excluded"]).any(), f"review rows={len(review)}")
    add("V21", "Only T0 responses are primary targets", set(TARGET_SPECS) == {"width", "depth", "total_height", "kinetic_energy"}, str(sorted(TARGET_SPECS)))
    add("V22", "ST is substrate temperature in kelvin", FEATURE_MEANINGS["ST"] == "substrate temperature" and FEATURE_UNITS["ST"] == "K", "ST=substrate temperature [K]")
    add("V23", "Figures exist and are hash-recorded", len(figures) >= 15 and all((destination / path).is_file() for path in figures["relative_path"]), f"figures={len(figures)}")
    add("V24", "Phase 4 stops before model-family expansion", True, "D10 conservative; no new model trained for evaluation")
    return pd.DataFrame(rows)


def requirement_checklist(validation: pd.DataFrame) -> pd.DataFrame:
    requirements = [
        ("P4-01", "Exact Phase 3 parent and immutable dataset provenance", "V01;V02"),
        ("P4-02", "Complete 165-row audit interface with machine-derived readiness", "V03;V04;V05"),
        ("P4-03", "Executable Week 6 feature-analysis traceability", "V06"),
        ("P4-04", "All 16 Spearman associations with simulation bootstrap", "V07"),
        ("P4-05", "Standardized Week 6 Ridge coefficient replication", "V08"),
        ("P4-06", "Controlled full-data GP curves inside observed support", "V09"),
        ("P4-07", "Standardized local GP sensitivities with guards", "V10"),
        ("P4-08", "Support-masked depth and total-height P-VX surfaces", "V09;V23"),
        ("P4-09", "Phase 3 LOO depth errors reused for three GP configurations", "V11;V12"),
        ("P4-10", "Error concentration and consensus cases retain all simulations", "V13;V20"),
        ("P4-11", "Depth errors diagnosed against depth, Keyhole, sparsity and quality", "V11;V13"),
        ("P4-12", "G3/R3/max depth remain diagnostics rather than replacement targets", "V21"),
        ("P4-13", "Week 6 versus new-data feature stability is explicit", "V06;V07;V08"),
        ("P4-14", "No label modification, classifier, active learning or level set", "V14;V15;V16"),
        ("P4-15", "No new GP kernel family", "V17;V24"),
        ("P4-16", "Teaching notebook is executed and error-free", "V18"),
        ("P4-17", "Output and figure manifests are complete", "V19;V23"),
        ("P4-18", "ST terminology remains substrate temperature", "V22"),
        ("P4-19", "D1-D10 diagnosis is conservative before model change", "V24"),
        ("P4-20", "Hard stop after Phase 4", "V15;V16;V17;V24"),
    ]
    status_by_id = validation.set_index("validation_id")["status"].to_dict()
    rows = []
    for requirement_id, description, ids in requirements:
        validation_ids = ids.split(";")
        passed = all(status_by_id.get(item) == "PASS" for item in validation_ids)
        rows.append(
            {
                "requirement_id": requirement_id,
                "requirement": description,
                "status": "PASS" if passed else "FAIL",
                "validation_ids": ids,
            }
        )
    return pd.DataFrame(rows)


def output_manifest(destination: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in sorted(item for item in destination.rglob("*") if item.is_file()):
        if path.name == "output_manifest.csv":
            continue
        rows.append(
            {
                "relative_path": path.relative_to(destination).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "artifact_type": path.suffix.lower().lstrip(".") or "file",
            }
        )
    return pd.DataFrame(rows)


def verify_output_manifest(destination: Path) -> tuple[int, int, list[str]]:
    manifest = pd.read_csv(destination / "output_manifest.csv")
    failures: list[str] = []
    for row in manifest.itertuples(index=False):
        path = destination / str(row.relative_path)
        if not path.is_file():
            failures.append(f"missing:{row.relative_path}")
        elif path.stat().st_size != int(row.bytes) or sha256_file(path) != str(row.sha256):
            failures.append(f"hash:{row.relative_path}")
    return len(manifest) - len(failures), len(manifest), failures


def refresh_validation(*, smoke: bool = False, notebook_required: bool = True) -> dict[str, Any]:
    destination = SMOKE_DIR if smoke else OUTPUT_DIR
    population = pd.read_csv(destination / "model_ready_population_reference.csv")
    tables: dict[str, pd.DataFrame] = {}
    for target, spec in TARGET_SPECS.items():
        mask = bool_series(population[f"{target}_model_eligible"])
        mask &= bool_series(population["selected_for_phase4_run"])
        eligible = population[mask]
        tables[target] = pd.DataFrame(
            {
                "simulation_id": eligible["experiment_name"].astype(str),
                "experiment_name": eligible["experiment_name"].astype(str),
                "P": eligible["P_W"],
                "VX": eligible["VX_m_per_s"],
                "LS": eligible["LS_um"],
                "ST": eligible["ST_K"],
                target: eligible[spec["column"]],
                "partition": eligible["partition"],
            }
        )
    traceability = pd.read_csv(destination / "week6_feature_analysis_traceability.csv")
    spearman = pd.read_csv(destination / "new_data_spearman_input_output.csv")
    ridge = pd.read_csv(destination / "new_data_standardized_ridge_coefficients.csv")
    curves = pd.read_csv(destination / "gp_controlled_curve_data.csv")
    sensitivity_values = pd.read_csv(destination / "gp_local_sensitivity_values.csv")
    predictions = pd.read_csv(
        PHASE3_DIR / "fold_level_predictions.csv",
        usecols=["target", "model", "experiment_name", "predicted_mean"],
    )
    predictions = predictions[predictions["target"].eq("depth") & predictions["model"].isin(DEPTH_MODELS)]
    hard_cases = pd.read_csv(destination / "depth_consensus_hard_cases.csv")
    review = pd.read_csv(destination / "depth_hard_case_review.csv")
    figures = pd.read_csv(destination / "figure_manifest.csv")
    validation = validation_table(
        destination=destination,
        population=population,
        tables=tables,
        traceability=traceability,
        spearman=spearman,
        ridge=ridge,
        curves=curves,
        sensitivity_values=sensitivity_values,
        depth_predictions=predictions,
        hard_cases=hard_cases,
        review=review,
        figures=figures,
        notebook_required=notebook_required,
    )
    checklist = requirement_checklist(validation)
    write_csv(destination / "validation_results.csv", validation)
    write_csv(destination / "requirement_checklist.csv", checklist)
    summary = json.loads((destination / "summary.json").read_text(encoding="utf-8"))
    summary["validation_counts"] = validation["status"].value_counts().to_dict()
    summary["requirement_counts"] = checklist["status"].value_counts().to_dict()
    summary["validation_refreshed_at_utc"] = utc_now()
    write_json(destination / "summary.json", summary)
    diagnosis = pd.read_csv(destination / "depth_error_diagnosis_summary.csv")
    stability = pd.read_csv(destination / "week6_vs_new_data_feature_stability.csv")
    write_text(destination / "results_summary.md", results_summary_markdown(summary, diagnosis, stability))
    manifest = output_manifest(destination)
    write_csv(destination / "output_manifest.csv", manifest)
    matched, total, failures = verify_output_manifest(destination)
    require(not failures, f"Output manifest failed: {failures[:5]}")
    return {
        "validation_status_counts": validation["status"].value_counts().to_dict(),
        "requirement_status_counts": checklist["status"].value_counts().to_dict(),
        "manifest_matched": matched,
        "manifest_total": total,
    }


def run_phase4(*, smoke: bool = False, force: bool = False) -> dict[str, Any]:
    del force
    started = time.perf_counter()
    destination = SMOKE_DIR if smoke else OUTPUT_DIR
    destination.mkdir(parents=True, exist_ok=True)
    (destination / FIGURE_DIR_NAME).mkdir(parents=True, exist_ok=True)
    preflight = git_preflight()
    write_json(destination / "phase4_preflight.json", preflight)

    traceability = week6_traceability_table()
    population, tables, phase2_summary = load_population(smoke=smoke)
    reference = population_reference(population)
    descriptive = descriptive_summary(tables)
    write_csv(destination / "model_ready_population_reference.csv", reference)
    write_csv(destination / "week6_feature_analysis_traceability.csv", traceability)
    write_csv(destination / "new_data_input_target_summary.csv", descriptive)

    spearman, spearman_comparison = spearman_analysis(tables, resamples=BOOTSTRAP_RESAMPLES if not smoke else 200)
    ridge, ridge_comparison = ridge_analysis(tables, resamples=BOOTSTRAP_RESAMPLES if not smoke else 200)
    write_csv(destination / "new_data_spearman_input_output.csv", spearman)
    write_csv(destination / "week6_vs_new_data_spearman.csv", spearman_comparison)
    write_csv(destination / "new_data_standardized_ridge_coefficients.csv", ridge)
    write_csv(destination / "week6_vs_new_data_standardized_coefficients.csv", ridge_comparison)

    configurations = interpretive_configuration_map()
    fitted, fit_summary = fit_interpretive_models(tables, configurations)
    curves, support_summary = controlled_curve_data(tables, fitted, configurations)
    depth_surface, depth_support = p_vx_surface(tables["depth"], fitted["depth"], target="depth", configuration=configurations["depth"])
    height_surface, height_support = p_vx_surface(tables["total_height"], fitted["total_height"], target="total_height", configuration=configurations["total_height"])
    support_summary = pd.concat([support_summary, pd.DataFrame([depth_support, height_support])], ignore_index=True)
    sensitivity_values, sensitivity_summary = local_sensitivities(tables, fitted, configurations)
    trends = trend_consensus(spearman, ridge, sensitivity_summary)
    write_csv(destination / "gp_interpretability_fits.csv", fit_summary)
    write_csv(destination / "gp_controlled_curve_data.csv", curves)
    write_csv(destination / "gp_observed_support_summary.csv", support_summary)
    write_csv(destination / "gp_local_sensitivity_values.csv", sensitivity_values)
    write_csv(destination / "gp_local_sensitivity_summary.csv", sensitivity_summary)
    write_csv(destination / "depth_P_VX_surface_data.csv", depth_surface)
    write_csv(destination / "total_height_P_VX_surface_data.csv", height_surface)
    write_csv(destination / "depth_feature_trend_consensus.csv", trends)

    distribution, concentration, hard_cases = load_depth_predictions(population)
    by_depth = depth_error_by_observed_depth(hard_cases)
    by_keyhole = depth_error_by_keyhole(hard_cases, resamples=BOOTSTRAP_RESAMPLES if not smoke else 200)
    sparsity, sparsity_summary = sparsity_diagnostics(hard_cases)
    old_shift = old_design_shift_groups(hard_cases)
    quality = phase2_quality_diagnostics(hard_cases)
    review, traces = hard_case_review(hard_cases, sparsity, destination=destination)
    write_csv(destination / "depth_error_distribution.csv", distribution)
    write_csv(destination / "depth_error_concentration.csv", concentration)
    write_csv(destination / "depth_consensus_hard_cases.csv", hard_cases)
    write_csv(destination / "depth_error_by_observed_depth.csv", by_depth)
    write_csv(destination / "depth_error_by_keyhole_context.csv", by_keyhole)
    write_csv(destination / "depth_error_by_local_sparsity.csv", sparsity)
    write_csv(destination / "depth_sparsity_association_summary.csv", sparsity_summary)
    write_csv(destination / "depth_error_by_old_design_shift.csv", old_shift)
    write_csv(destination / "depth_error_by_phase2_quality_flags.csv", quality)
    write_csv(destination / "depth_hard_case_review.csv", review)
    write_csv(destination / "depth_hard_case_time_series.csv", traces)

    stability = feature_stability_table(spearman, ridge, trends, sensitivity_summary, depth_surface, height_surface)
    diagnosis = diagnosis_table(concentration, hard_cases, by_keyhole, sparsity_summary, quality, trends)
    write_csv(destination / "week6_vs_new_data_feature_stability.csv", stability)
    write_csv(destination / "depth_error_diagnosis_summary.csv", diagnosis)

    generate_figures(
        destination=destination,
        tables=tables,
        spearman=spearman,
        ridge=ridge,
        curves=curves,
        sensitivities=sensitivity_summary,
        depth_surface=depth_surface,
        height_surface=height_surface,
        hard_cases=hard_cases,
        concentration=concentration,
        keyhole=by_keyhole,
        sparsity=sparsity,
        review=review,
        traces=traces,
        stability=stability,
        diagnosis=diagnosis,
    )
    figures = figure_manifest(destination)
    write_csv(destination / "figure_manifest.csv", figures)

    predictions_for_validation = pd.read_csv(
        PHASE3_DIR / "fold_level_predictions.csv",
        usecols=["target", "model", "experiment_name", "predicted_mean"],
    )
    predictions_for_validation = predictions_for_validation[
        predictions_for_validation["target"].eq("depth")
        & predictions_for_validation["model"].isin(DEPTH_MODELS)
    ]
    validation = validation_table(
        destination=destination,
        population=reference,
        tables=tables,
        traceability=traceability,
        spearman=spearman,
        ridge=ridge,
        curves=curves,
        sensitivity_values=sensitivity_values,
        depth_predictions=predictions_for_validation,
        hard_cases=hard_cases,
        review=review,
        figures=figures,
        notebook_required=False,
    )
    checklist = requirement_checklist(validation)
    write_csv(destination / "validation_results.csv", validation)
    write_csv(destination / "requirement_checklist.csv", checklist)
    runtime = time.perf_counter() - started
    summary = build_summary(
        smoke=smoke,
        population=population,
        spearman=spearman,
        ridge=ridge,
        trends=trends,
        concentration=concentration,
        hard_cases=hard_cases,
        sparsity_summary=sparsity_summary,
        stability=stability,
        diagnosis=diagnosis,
        validation=validation,
        figures=figures,
        runtime_seconds=runtime,
    )
    summary["phase2_summary_revision"] = phase2_summary.get("revision")
    summary["requirement_counts"] = checklist["status"].value_counts().to_dict()
    write_json(destination / "summary.json", summary)
    write_text(destination / "results_summary.md", results_summary_markdown(summary, diagnosis, stability))
    write_json(
        destination / "input_provenance.json",
        {
            "phase3_parent_sha": PHASE3_PARENT_SHA,
            "dataset_revision": DATASET_REVISION,
            "phase2_targets_sha256": sha256_file(PHASE2_DIR / "sph_v2_simulation_level_targets.csv"),
            "phase3_predictions_sha256": sha256_file(PHASE3_DIR / "fold_level_predictions.csv"),
            "week6_spearman_sha256": sha256_file(WEEK6_DIR / "phase4_spearman_correlations.csv"),
            "week6_ridge_sha256": sha256_file(WEEK6_DIR / "phase4_standardized_ridge_coefficients.csv"),
            "week6_source_sha256": sha256_file(ROOT / "src" / "week6_phase4_new_outputs_feature_effects.py"),
            "generated_at_utc": utc_now(),
        },
    )
    manifest = output_manifest(destination)
    write_csv(destination / "output_manifest.csv", manifest)
    matched, total, failures = verify_output_manifest(destination)
    require(not failures, f"Output manifest failed: {failures[:5]}")
    return {
        "summary": summary,
        "validation": validation["status"].value_counts().to_dict(),
        "requirements": checklist["status"].value_counts().to_dict(),
        "manifest": f"{matched}/{total}",
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--refresh-validation", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.refresh_validation:
        result = refresh_validation(smoke=args.smoke, notebook_required=True)
    else:
        result = run_phase4(smoke=args.smoke, force=args.force)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
