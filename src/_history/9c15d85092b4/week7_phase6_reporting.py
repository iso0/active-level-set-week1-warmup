"""Reporting and supported-boundary visualisation for Week 7 Phase 6.

The core Phase 6 module owns dataset construction, model fitting, and the
matched active-learning benchmark.  This module owns two deliberately
separate reporting concerns:

* a *descriptive, full-common-population* pair of Matérn-3/2 models used only
  to draw supported two-dimensional slices of the four-dimensional boundary;
* deterministic explanatory figures made from the saved Phase 6 artifact
  tables.

Nothing here changes a label or a physical target.  The full-population
threshold and surfaces are explicitly oracle/descriptive references and are
never valid active-learning methods.  Surface support is fail-closed: a grid
cell is shown only when it lies inside the standardized four-dimensional
convex hull and within a data-derived nearest-neighbour radius.

The imports from the core Phase 6 module are intentionally lazy so that the
core pipeline may import this reporting module without creating a circular
import at module-import time.
"""

from __future__ import annotations

import hashlib
import math
import re
import textwrap
import warnings
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from scipy.spatial import ConvexHull, QhullError
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler


FEATURE_COLUMNS = ("P", "VX", "LS", "ST")
FEATURE_LABELS = {
    "P": "Laser power P (W)",
    "VX": "Scan speed VX (m/s)",
    "LS": "Laser size LS (µm)",
    "ST": "Substrate temperature ST (K)",
}
FEATURE_UNITS = {"P": "W", "VX": "m/s", "LS": "µm", "ST": "K"}
SURFACE_PAIRS = (("P", "VX"), ("P", "LS"), ("VX", "LS"))

PHASE6_ARTIFACT_TABLES = (
    "population_audit.csv",
    "primary_common_population.csv",
    "secondary_g3_common_population.csv",
    "max_depth_event_audit.csv",
    "max_depth_raw_review_cases.csv",
    "max_depth_semantic_summary.csv",
    "empirical_boundary_reference.csv",
    "empirical_boundary_subset_summary.csv",
    "empirical_boundary_validation.csv",
    "outer_split_manifest.csv",
    "outer_split_balance_audit.csv",
    "fairness_audit.csv",
    "static_model_fold_predictions.csv",
    "static_model_summary.csv",
    "static_boundary_metric_summary.csv",
    "static_probability_calibration.csv",
    "active_run_manifest.csv",
    "active_initialization_audit.csv",
    "active_query_history.csv",
    "active_prediction_history.csv",
    "online_threshold_history.csv",
    "online_threshold_bootstrap_summary.csv",
    "active_learning_curve_summary.csv",
    "active_learning_final_budget_summary.csv",
    "active_learning_aulc_summary.csv",
    "queries_to_tolerance.csv",
    "active_paired_method_comparisons.csv",
    "active_paired_bootstrap_intervals.csv",
    "query_boundary_distance_summary.csv",
    "subgroup_transient_persistent_results.csv",
    "subgroup_t0_timing_results.csv",
    "g3_secondary_active_summary.csv",
    "max_depth_vs_g3_summary.csv",
    "domain_transfer_model_summary.csv",
    "boundary_surface_data.csv",
    "boundary_disagreement_summary.csv",
    "phase6_formulation_scorecard.csv",
    "phase6_final_decision.csv",
    "validation_results.csv",
    "requirement_checklist.csv",
)

BLUE = "#4477AA"
RED = "#CC3311"
TEAL = "#228833"
ORANGE = "#EE7733"
PURPLE = "#AA3377"
GREY = "#999999"
LIGHT_GREY = "#E4E4E4"
METHOD_COLORS = {
    "max_depth": TEAL,
    "binary": PURPLE,
    "g3": ORANGE,
}


class ReportingDataError(RuntimeError):
    """Raised when an artifact cannot support a requested scientific plot."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReportingDataError(message)


def _find_column(frame: pd.DataFrame, *candidates: str, required: bool = True) -> str | None:
    lookup = {str(column).casefold(): str(column) for column in frame.columns}
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
        found = lookup.get(candidate.casefold())
        if found is not None:
            return found
    if required:
        raise ReportingDataError(
            f"None of {candidates!r} is present; available columns are {list(frame.columns)!r}"
        )
    return None


def _bool_values(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").fillna(0).ne(0)
    missing = series.isna()
    normalized = series.astype(str).str.strip().str.casefold()
    allowed = {
        "true": True,
        "false": False,
        "1": True,
        "0": False,
        "yes": True,
        "no": False,
        "keyhole": True,
        "conduction": False,
    }
    unknown = sorted(set(normalized.loc[~missing]) - set(allowed))
    _require(not unknown, f"Unrecognized boolean values: {unknown}")
    return normalized.map(allowed).where(~missing, False).fillna(False).astype(bool)


def _finite_numeric(series: pd.Series) -> np.ndarray:
    values = pd.to_numeric(series, errors="coerce").to_numpy(float)
    return values[np.isfinite(values)]


def _display_values(feature: str, values: np.ndarray | pd.Series) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    return array * 1e6 if feature == "LS" else array


def _safe_slug(value: object) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", str(value).strip()).strip("_").lower()
    return text or "figure"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_phase6_artifacts(output_dir: str | Path) -> dict[str, pd.DataFrame]:
    """Load only the declared Phase 6 CSV artifacts that currently exist.

    Missing artifacts are not replaced with synthetic or empty proxy data.
    Callers can inspect the returned keys and decide whether a plot is
    supported.  A malformed existing CSV raises with its exact path.
    """

    destination = Path(output_dir)
    loaded: dict[str, pd.DataFrame] = {}
    for filename in PHASE6_ARTIFACT_TABLES:
        path = destination / filename
        if not path.is_file():
            continue
        try:
            frame = pd.read_csv(path, low_memory=False)
        except Exception as exc:  # pragma: no cover - pandas supplies the detail
            raise ReportingDataError(f"Could not read Phase 6 artifact {path}: {exc}") from exc
        loaded[filename] = frame
        loaded[path.stem] = frame
    return loaded


def _artifact(
    artifacts: Mapping[str, pd.DataFrame],
    name: str,
    *,
    allow_empty: bool = False,
) -> pd.DataFrame:
    candidates = (name, f"{name}.csv", Path(name).stem)
    for candidate in candidates:
        if candidate in artifacts:
            frame = artifacts[candidate]
            _require(isinstance(frame, pd.DataFrame), f"Artifact {candidate} is not a DataFrame")
            if not allow_empty:
                _require(len(frame) > 0, f"Artifact {candidate} is empty")
            return frame.copy()
    raise ReportingDataError(f"Required artifact is unavailable: {name}.csv")


def _benchmark_rows(frame: pd.DataFrame, benchmark: str) -> pd.DataFrame:
    """Return one declared benchmark population when the schema identifies it."""

    benchmark_col = _find_column(
        frame, "benchmark_population", "population", "benchmark", required=False
    )
    if benchmark_col is None:
        return frame.copy()
    subset = frame[
        frame[benchmark_col].astype(str).str.casefold().eq(benchmark.casefold())
    ].copy()
    _require(len(subset) > 0, f"No rows are available for benchmark {benchmark}")
    return subset


def _population_for_surfaces(population: pd.DataFrame) -> pd.DataFrame:
    _require(len(population) >= 5, "At least five common-population rows are required")
    frame = population.copy()
    missing = set(FEATURE_COLUMNS) - set(frame.columns)
    _require(not missing, f"Surface population is missing physical inputs: {sorted(missing)}")
    depth_col = _find_column(frame, "value__max_depth", "max_depth_um", "maximum_depth_um")
    label_col = _find_column(frame, "has_keyhole", "manual_has_keyhole")
    identifier_col = _find_column(
        frame, "experiment_name", "experiment_id", "simulation_id", required=False
    )
    clean = pd.DataFrame(index=frame.index)
    clean["experiment_name"] = (
        frame[identifier_col].astype(str)
        if identifier_col is not None
        else pd.Series([f"row_{index}" for index in range(len(frame))], index=frame.index)
    )
    for feature in FEATURE_COLUMNS:
        clean[feature] = pd.to_numeric(frame[feature], errors="coerce")
    clean["value__max_depth"] = pd.to_numeric(frame[depth_col], errors="coerce")
    clean["has_keyhole"] = _bool_values(frame[label_col])
    finite = np.isfinite(clean[[*FEATURE_COLUMNS, "value__max_depth"]]).all(axis=1)
    _require(bool(finite.all()), f"Surface population contains {int((~finite).sum())} non-finite rows")
    _require(clean["experiment_name"].is_unique, "Surface population identifiers are not unique")
    _require(clean["has_keyhole"].nunique() == 2, "Both manual classes are required")
    for feature in FEATURE_COLUMNS:
        _require(clean[feature].nunique() >= 2, f"Physical input {feature} is constant")
    return clean.reset_index(drop=True)


def build_supported_boundary_surfaces(
    population: pd.DataFrame,
    grid_size: int = 51,
    nn_support_quantile: float = 0.95,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Fit descriptive full-common GP models and build supported 2D slices.

    Parameters
    ----------
    population:
        Exact Binary/Max-Depth common population.  It must contain P, VX, LS,
        ST, the unchanged maximum-depth scalar, and the manual label.
    grid_size:
        Number of points along each slice axis.  The default produces 2,601
        cells per pair and materially reduces reporting runtime while retaining
        smooth contours.
    nn_support_quantile:
        Quantile of observed leave-one-out nearest-neighbour distances used as
        the local-support radius in standardized four-dimensional space.

    Returns
    -------
    boundary_surface_data, boundary_disagreement_summary, diagnostics
        The first two values are directly writable to the correspondingly
        named Phase 6 CSV artifacts.  ``diagnostics`` is JSON-serializable and
        records fit/support details.  All fits are explicitly descriptive and
        unavailable to active-learning acquisition or held-out ranking.
    """

    _require(int(grid_size) == grid_size and 21 <= grid_size <= 301, "grid_size must be 21..301")
    _require(0.50 <= float(nn_support_quantile) < 1.0, "nn_support_quantile must be in [0.50, 1)")
    common = _population_for_surfaces(population)

    # Lazy by design: the core pipeline may itself import this module.
    from src import week7_phase6_real_data_boundary_active_level_set as core

    required_helpers = (
        "fit_gpc",
        "fit_gpr",
        "predict_gpc",
        "predict_gpr",
        "choose_higher_threshold",
        "continuous_probability",
        "stable_seed",
    )
    missing_helpers = [name for name in required_helpers if not hasattr(core, name)]
    _require(not missing_helpers, f"Core Phase 6 helpers are unavailable: {missing_helpers}")

    x = common[list(FEATURE_COLUMNS)].to_numpy(float)
    labels = common["has_keyhole"].astype(int).to_numpy()
    depth = common["value__max_depth"].to_numpy(float)
    scaler = StandardScaler().fit(x)
    x_scaled = scaler.transform(x)
    threshold = core.choose_higher_threshold(depth, labels)
    seed = int(core.stable_seed("phase6", "descriptive_supported_surfaces"))

    gpc_fit = core.fit_gpc(
        x,
        labels,
        scaler=scaler,
        seed=seed,
        kernel_kind="matern32",
        restarts=0,
    )
    gpr_fit = core.fit_gpr(
        x,
        depth,
        scaler=scaler,
        seed=int(core.stable_seed(seed, "max_depth")),
        kernel_kind="matern32",
        restarts=0,
    )

    # Four-dimensional hull membership.  QJ resolves duplicate/coplanar input
    # tuples for hull construction without changing the saved observations.
    unique_scaled = np.unique(x_scaled, axis=0)
    hull_status = "PASS"
    hull_detail = "standardized_4d_convex_hull_QJ"
    hull_equations: np.ndarray | None
    try:
        hull = ConvexHull(unique_scaled, qhull_options="QJ")
        hull_equations = hull.equations.copy()
    except QhullError as exc:
        hull_equations = None
        hull_status = "FAIL_CLOSED"
        hull_detail = f"4d_convex_hull_unavailable:{type(exc).__name__}"

    neighbours = NearestNeighbors(n_neighbors=min(2, len(x_scaled))).fit(x_scaled)
    observed_distances, _ = neighbours.kneighbors(x_scaled)
    if observed_distances.shape[1] >= 2:
        observed_loo_distance = observed_distances[:, 1]
    else:  # protected by the population-size requirement
        observed_loo_distance = np.full(len(x_scaled), math.nan)
    finite_loo = observed_loo_distance[np.isfinite(observed_loo_distance)]
    _require(len(finite_loo) > 0, "Observed nearest-neighbour distances are unavailable")
    nn_radius = float(np.quantile(finite_loo, nn_support_quantile))
    if not math.isfinite(nn_radius) or nn_radius <= 0:
        positive = finite_loo[finite_loo > np.finfo(float).eps]
        _require(len(positive) > 0, "Nearest-neighbour support radius is non-positive")
        nn_radius = float(np.max(positive))

    medians = common[list(FEATURE_COLUMNS)].median(numeric_only=True).to_dict()
    surface_frames: list[pd.DataFrame] = []
    summary_rows: list[dict[str, Any]] = []
    for x_feature, y_feature in SURFACE_PAIRS:
        x_axis = np.linspace(float(common[x_feature].min()), float(common[x_feature].max()), grid_size)
        y_axis = np.linspace(float(common[y_feature].min()), float(common[y_feature].max()), grid_size)
        grid_x, grid_y = np.meshgrid(x_axis, y_axis, indexing="xy")
        grid = np.column_stack(
            [np.full(grid_x.size, float(medians[feature])) for feature in FEATURE_COLUMNS]
        )
        grid[:, FEATURE_COLUMNS.index(x_feature)] = grid_x.ravel()
        grid[:, FEATURE_COLUMNS.index(y_feature)] = grid_y.ravel()
        grid_scaled = scaler.transform(grid)

        if hull_equations is None:
            inside_hull = np.zeros(len(grid), dtype=bool)
        else:
            signed = grid_scaled @ hull_equations[:, :-1].T + hull_equations[:, -1]
            inside_hull = np.all(signed <= 1e-9, axis=1)
        nearest_distance, nearest_index = neighbours.kneighbors(grid_scaled, n_neighbors=1)
        nearest_distance = nearest_distance[:, 0]
        nearest_index = nearest_index[:, 0]
        local_support = nearest_distance <= nn_radius
        supported = inside_hull & local_support

        binary_probability = np.asarray(core.predict_gpc(gpc_fit, grid), dtype=float)
        depth_mean, depth_std = core.predict_gpr(gpr_fit, grid)
        depth_mean = np.asarray(depth_mean, dtype=float)
        depth_std = np.asarray(depth_std, dtype=float)
        depth_probability = np.asarray(
            core.continuous_probability(depth_mean, depth_std, float(threshold["threshold"])),
            dtype=float,
        )
        binary_class = binary_probability >= 0.5
        depth_class = depth_mean > float(threshold["threshold"])
        disagreement = binary_class != depth_class
        support_reason = np.select(
            [supported, ~inside_hull & ~local_support, ~inside_hull, ~local_support],
            [
                "supported",
                "outside_4d_convex_hull_and_nn_radius",
                "outside_4d_convex_hull",
                "beyond_nn_support_radius",
            ],
            default="unsupported",
        )

        pair = f"{x_feature}-{y_feature}"
        part = pd.DataFrame(
            {
                "slice_pair": pair,
                "x_feature": x_feature,
                "y_feature": y_feature,
                "grid_i": np.tile(np.arange(grid_size), grid_size),
                "grid_j": np.repeat(np.arange(grid_size), grid_size),
                "x_value_raw": grid_x.ravel(),
                "y_value_raw": grid_y.ravel(),
                "x_value_display": _display_values(x_feature, grid_x.ravel()),
                "y_value_display": _display_values(y_feature, grid_y.ravel()),
                "x_units": FEATURE_UNITS[x_feature],
                "y_units": FEATURE_UNITS[y_feature],
                "P": grid[:, 0],
                "VX": grid[:, 1],
                "LS": grid[:, 2],
                "ST": grid[:, 3],
                "fixed_P": float(medians["P"]) if x_feature != "P" and y_feature != "P" else math.nan,
                "fixed_VX": float(medians["VX"]) if x_feature != "VX" and y_feature != "VX" else math.nan,
                "fixed_LS": float(medians["LS"]) if x_feature != "LS" and y_feature != "LS" else math.nan,
                "fixed_ST": float(medians["ST"]) if x_feature != "ST" and y_feature != "ST" else math.nan,
                "inside_standardized_4d_convex_hull": inside_hull,
                "nearest_observed_standardized_4d_distance": nearest_distance,
                "nearest_observed_experiment": common.iloc[nearest_index]["experiment_name"].to_numpy(),
                "nn_support_radius": nn_radius,
                "inside_nn_support_radius": local_support,
                "supported": supported,
                "support_reason": support_reason,
                "binary_gpc_keyhole_probability": binary_probability,
                "binary_gpc_predicted_keyhole": binary_class,
                "max_depth_gpr_mean_um": depth_mean,
                "max_depth_gpr_latent_std_um": depth_std,
                "max_depth_gaussian_tail_keyhole_probability": depth_probability,
                "max_depth_predicted_keyhole": depth_class,
                "descriptive_full_common_threshold_um": float(threshold["threshold"]),
                "binary_max_depth_disagreement": disagreement,
                "binary_boundary_level": 0.5,
                "max_depth_boundary_level_um": float(threshold["threshold"]),
                "population": "primary_common_full",
                "fit_status": "descriptive_oracle_not_held_out",
                "held_out_performance_claim": False,
                "available_to_active_method": False,
                "surface_interpretation": "supported_2d_slice_of_4d_descriptive_models",
            }
        )
        surface_frames.append(part)

        supported_count = int(supported.sum())
        disagreement_count = int((supported & disagreement).sum())
        summary_rows.append(
            {
                "slice_pair": pair,
                "x_feature": x_feature,
                "y_feature": y_feature,
                "grid_size_per_axis": grid_size,
                "grid_cell_count": len(grid),
                "inside_4d_convex_hull_count": int(inside_hull.sum()),
                "inside_nn_support_radius_count": int(local_support.sum()),
                "supported_cell_count": supported_count,
                "supported_fraction": supported_count / len(grid),
                "supported_disagreement_count": disagreement_count,
                "supported_disagreement_fraction": (
                    disagreement_count / supported_count if supported_count else math.nan
                ),
                "supported_both_conduction_count": int(
                    (supported & ~binary_class & ~depth_class).sum()
                ),
                "supported_both_keyhole_count": int((supported & binary_class & depth_class).sum()),
                "supported_binary_only_keyhole_count": int(
                    (supported & binary_class & ~depth_class).sum()
                ),
                "supported_max_depth_only_keyhole_count": int(
                    (supported & ~binary_class & depth_class).sum()
                ),
                "fixed_values_raw_json": str(
                    {
                        feature: float(medians[feature])
                        for feature in FEATURE_COLUMNS
                        if feature not in {x_feature, y_feature}
                    }
                ),
                "nn_support_quantile": float(nn_support_quantile),
                "nn_support_radius_standardized_4d": nn_radius,
                "convex_hull_status": hull_status,
                "descriptive_full_common_threshold_um": float(threshold["threshold"]),
                "binary_gpc_fit_status": str(gpc_fit.fit_status),
                "max_depth_gpr_fit_status": str(gpr_fit.fit_status),
                "evaluation_status": "descriptive_oracle_not_held_out",
                "major_caveat": "2d median slice of a 4d problem; unsupported cells must remain masked",
            }
        )

    surfaces = pd.concat(surface_frames, ignore_index=True)
    disagreement_summary = pd.DataFrame(summary_rows)
    diagnostics: dict[str, Any] = {
        "population": "primary_common_full",
        "population_count": int(len(common)),
        "keyhole_count": int(labels.sum()),
        "non_keyhole_count": int((labels == 0).sum()),
        "features": list(FEATURE_COLUMNS),
        "grid_size_per_axis": int(grid_size),
        "slice_pairs": [f"{left}-{right}" for left, right in SURFACE_PAIRS],
        "nn_support_quantile": float(nn_support_quantile),
        "nn_support_radius_standardized_4d": nn_radius,
        "observed_loo_nn_distance_min": float(np.min(finite_loo)),
        "observed_loo_nn_distance_median": float(np.median(finite_loo)),
        "observed_loo_nn_distance_max": float(np.max(finite_loo)),
        "convex_hull_status": hull_status,
        "convex_hull_detail": hull_detail,
        "unique_standardized_input_count": int(len(unique_scaled)),
        "descriptive_full_common_threshold_um": float(threshold["threshold"]),
        "threshold_balanced_accuracy_descriptive": float(threshold["balanced_accuracy"]),
        "binary_gpc_fit_status": str(gpc_fit.fit_status),
        "binary_gpc_kernel": str(gpc_fit.kernel),
        "max_depth_gpr_fit_status": str(gpr_fit.fit_status),
        "max_depth_gpr_kernel": str(gpr_fit.kernel),
        "input_scaler_scope": "full_common_descriptive_only",
        "fit_status": "descriptive_oracle_not_held_out",
        "available_to_active_method": False,
    }
    return surfaces, disagreement_summary, diagnostics


def select_representative_trajectory_runs(
    aulc: pd.DataFrame,
    method: str | None = None,
) -> pd.DataFrame:
    """Select deterministic q20-AULC best/median/worst trajectory runs.

    If ``method`` is omitted, the non-random method with the lowest mean q20
    error AULC is selected independently for each formulation.  Method and run
    ties are resolved lexicographically.  Representative selection is
    post-hoc/descriptive and must not be interpreted as an independent test.
    """

    _require(len(aulc) > 0, "AULC table is empty")
    benchmark_col = _find_column(
        aulc, "benchmark_population", "population", "benchmark", required=False
    )
    if benchmark_col is not None:
        aulc = aulc[
            aulc[benchmark_col].astype(str).str.casefold().eq("primary_common")
        ].copy()
        _require(len(aulc) > 0, "No primary-common AULC rows are available")
    run_col = _find_column(aulc, "run_id")
    method_col = _find_column(aulc, "method")
    formulation_col = _find_column(aulc, "formulation")
    metric_col = _find_column(
        aulc,
        "common_normalized_aulc__q20_error",
        "q20_error_aulc",
        "q20_aulc",
    )
    frame = aulc[[run_col, method_col, formulation_col, metric_col]].copy()
    frame.columns = ["run_id", "method", "formulation", "q20_error_aulc"]
    frame["q20_error_aulc"] = pd.to_numeric(frame["q20_error_aulc"], errors="coerce")
    frame = frame[np.isfinite(frame["q20_error_aulc"])].copy()
    _require(len(frame) > 0, "AULC table has no finite q20 AULC values")
    rows: list[dict[str, Any]] = []
    available_formulations = sorted(frame["formulation"].astype(str).unique())
    primary_formulations = [
        formulation for formulation in ("binary", "max_depth") if formulation in available_formulations
    ]
    formulations = primary_formulations or available_formulations
    for formulation in formulations:
        subset = frame[frame["formulation"].astype(str).eq(formulation)].copy()
        if method is not None:
            chosen_method = method
            subset = subset[subset["method"].astype(str).eq(chosen_method)]
            if len(subset) == 0:
                continue
            method_rule = "caller_selected_method"
        else:
            candidates = subset[~subset["method"].astype(str).str.endswith("_random")].copy()
            if len(candidates) == 0:
                candidates = subset
            means = (
                candidates.groupby("method", as_index=False)["q20_error_aulc"]
                .mean()
                .sort_values(["q20_error_aulc", "method"], kind="mergesort")
            )
            chosen_method = str(means.iloc[0]["method"])
            subset = subset[subset["method"].astype(str).eq(chosen_method)].copy()
            method_rule = "lowest_mean_q20_error_aulc_nonrandom_then_method_name"
        subset = subset.sort_values(["q20_error_aulc", "run_id"], kind="mergesort")
        _require(subset["run_id"].is_unique, f"Duplicate AULC rows for {formulation}/{chosen_method}")

        best = subset.iloc[0]
        worst = subset.iloc[-1]
        median_value = float(subset["q20_error_aulc"].median())
        median = (
            subset.assign(_distance=(subset["q20_error_aulc"] - median_value).abs())
            .sort_values(["_distance", "run_id"], kind="mergesort")
            .iloc[0]
        )
        for rank, selected in (("best", best), ("median", median), ("worst", worst)):
            rows.append(
                {
                    "formulation": formulation,
                    "method": chosen_method,
                    "representative_rank": rank,
                    "run_id": str(selected["run_id"]),
                    "q20_error_aulc": float(selected["q20_error_aulc"]),
                    "within_method_run_count": int(len(subset)),
                    "method_selection_rule": method_rule,
                    "run_selection_rule": (
                        "ascending q20 error AULC; median is closest to numeric median; "
                        "run_id breaks ties"
                    ),
                    "selection_status": "post_hoc_descriptive_not_independent_evaluation",
                }
            )
    result = pd.DataFrame(rows)
    _require(len(result) > 0, "No representative trajectories could be selected")
    rank_order = pd.Categorical(result["representative_rank"], ["best", "median", "worst"], ordered=True)
    return (
        result.assign(_rank_order=rank_order)
        .sort_values(["formulation", "method", "_rank_order", "run_id"], kind="mergesort")
        .drop(columns="_rank_order")
        .reset_index(drop=True)
    )


class _FigureRecorder:
    """Save PNGs and retain auditable figure-manifest rows."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.figure_dir = output_dir / "figures"
        self.figure_dir.mkdir(parents=True, exist_ok=True)
        self.rows: list[dict[str, Any]] = []
        self.skipped: list[dict[str, str]] = []

    def save(
        self,
        fig: plt.Figure,
        *,
        slug: str,
        title: str,
        question: str,
        sources: Sequence[str],
        population: str,
        units: str,
        status: str,
        caveat: str,
    ) -> None:
        number = len(self.rows) + 1
        filename = f"{number:02d}_{_safe_slug(slug)}.png"
        path = self.figure_dir / filename
        status_display = status.strip()
        evidence_words = ("held-out", "held_out", "descriptive", "oracle")
        if not any(word in status_display.casefold() for word in evidence_words):
            status_display += "; not itself held-out/descriptive/oracle performance"
        subtitle = "\n".join(
            textwrap.wrap(
                f"Population: {population} | Units: {units} | Status: {status_display}",
                width=155,
            )
        )
        caveat_line = "Caveat: " + caveat
        fig.suptitle(title, fontsize=14, fontweight="semibold", y=0.985)
        fig.text(0.5, 0.947, subtitle, ha="center", va="top", fontsize=8.1, color="#333333")
        fig.text(
            0.01,
            0.012,
            "\n".join(textwrap.wrap(caveat_line, width=170)),
            ha="left",
            va="bottom",
            fontsize=7.2,
            color="#444444",
        )
        try:
            fig.tight_layout(rect=(0.0, 0.075, 1.0, 0.915))
        except Exception:
            # Some colorbar/inset combinations do not participate in
            # tight_layout; savefig(bbox_inches="tight") remains deterministic.
            pass
        width_px = int(round(fig.get_figwidth() * 180))
        height_px = int(round(fig.get_figheight() * 180))
        fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        _require(path.is_file() and path.stat().st_size > 1000, f"Invalid generated figure: {path}")
        with path.open("rb") as handle:
            _require(handle.read(8) == b"\x89PNG\r\n\x1a\n", f"Not a PNG file: {path}")
        self.rows.append(
            {
                "figure_number": number,
                "figure": f"figures/{filename}",
                "relative_path": f"figures/{filename}",
                "filename": filename,
                "title": title,
                "question": question,
                "source_artifacts": ";".join(sources),
                "population": population,
                "units": units,
                "evaluation_status": status_display,
                "training_evaluation_status": status_display,
                "major_caveat": caveat,
                "sha256": _sha256(path),
                "bytes": int(path.stat().st_size),
                "nominal_width_px": width_px,
                "nominal_height_px": height_px,
                "population_units_method_caveat_in_figure": True,
                "population_units_status_caveat_visible": True,
                "meaningful_explanatory_figure": True,
            }
        )

    def skip(self, slug: str, reason: str) -> None:
        self.skipped.append({"slug": slug, "reason": reason})


def _attempt(recorder: _FigureRecorder, slug: str, action: Callable[[], None]) -> None:
    """Skip unsupported plots, but never replace them with fabricated values."""

    before = len(recorder.rows)
    try:
        action()
    except (ReportingDataError, KeyError, ValueError, TypeError, IndexError) as exc:
        plt.close("all")
        recorder.skip(slug, str(exc))
        return
    if len(recorder.rows) == before:
        recorder.skip(slug, "plot action produced no figure")


def _label_series(frame: pd.DataFrame) -> pd.Series:
    return _bool_values(frame[_find_column(frame, "has_keyhole", "manual_has_keyhole")])


def _depth_column(frame: pd.DataFrame) -> str:
    return str(_find_column(frame, "value__max_depth", "max_depth_um", "maximum_depth_um"))


def _g3_column(frame: pd.DataFrame) -> str:
    return str(_find_column(frame, "value__G3", "G3_persistent_depth_um", "G3_um", "g3_um"))


def _method_label(method: object) -> str:
    return str(method).replace("_", " ")


def _method_color(method: object, formulation: object | None = None) -> str:
    text = str(formulation if formulation is not None else method).casefold()
    for key, color in METHOD_COLORS.items():
        if key in text:
            return color
    palette = [BLUE, RED, TEAL, ORANGE, PURPLE, "#66CCEE", "#BBBBBB", "#CCBB44"]
    digest = hashlib.sha256(str(method).encode("utf-8")).digest()[0]
    return palette[digest % len(palette)]


def _numeric_column(frame: pd.DataFrame, *candidates: str) -> tuple[str, pd.Series]:
    column = str(_find_column(frame, *candidates))
    values = pd.to_numeric(frame[column], errors="coerce")
    _require(values.notna().any(), f"Column {column} contains no numeric values")
    return column, values


def _categorical_counts(
    recorder: _FigureRecorder,
    frame: pd.DataFrame,
    column: str,
    *,
    slug: str,
    title: str,
    question: str,
    source: str,
    population: str,
    status: str,
    caveat: str,
    top_n: int = 14,
) -> None:
    counts = frame[column].fillna("missing").astype(str).value_counts().head(top_n)
    _require(len(counts) > 0, f"No categories in {column}")
    fig, ax = plt.subplots(figsize=(10, 5.5))
    positions = np.arange(len(counts))
    ax.barh(positions, counts.to_numpy(), color=BLUE, alpha=0.85)
    ax.set_yticks(positions, counts.index)
    ax.invert_yaxis()
    ax.set_xlabel("Simulations")
    ax.grid(axis="x", alpha=0.2)
    for y, value in enumerate(counts.to_numpy()):
        ax.text(value, y, f" {int(value)}", va="center", fontsize=8)
    recorder.save(
        fig,
        slug=slug,
        title=title,
        question=question,
        sources=[source],
        population=population,
        units="simulation count",
        status=status,
        caveat=caveat,
    )


def _box_by_label(
    recorder: _FigureRecorder,
    frame: pd.DataFrame,
    value_column: str,
    *,
    slug: str,
    title: str,
    question: str,
    source: str,
    units: str,
    caveat: str,
) -> None:
    labels = _label_series(frame)
    values = pd.to_numeric(frame[value_column], errors="coerce")
    groups = [values[~labels].dropna().to_numpy(float), values[labels].dropna().to_numpy(float)]
    _require(all(len(group) > 0 for group in groups), f"Both classes need finite {value_column}")
    fig, ax = plt.subplots(figsize=(8, 5.3))
    ax.boxplot(groups, tick_labels=["Conduction", "Keyhole"], showfliers=False, widths=0.5)
    rng = np.random.default_rng(6022026)
    for position, (group, color) in enumerate(zip(groups, [BLUE, RED]), start=1):
        jitter = rng.uniform(-0.10, 0.10, len(group))
        ax.scatter(position + jitter, group, s=15, alpha=0.45, color=color, edgecolors="none")
    ax.set_ylabel(f"{title.split(' by ')[0]} ({units})")
    ax.grid(axis="y", alpha=0.2)
    recorder.save(
        fig,
        slug=slug,
        title=title,
        question=question,
        sources=[source],
        population=f"{len(frame):,} common simulations",
        units=units,
        status="descriptive full-common; not held-out",
        caveat=caveat,
    )


def _long_static_metric(frame: pd.DataFrame, metric: str) -> pd.DataFrame:
    metric_col = _find_column(frame, "metric", required=False)
    model_col = _find_column(frame, "model", "method", required=False)
    formulation_col = _find_column(frame, "formulation", required=False)
    _require(model_col is not None, "Static summary has no model/method column")
    if metric_col is not None and metric_col in frame and frame[metric_col].astype(str).eq(metric).any():
        subset = frame[frame[metric_col].astype(str).eq(metric)].copy()
        mean_col = _find_column(subset, "mean", "metric_mean", "value")
        std_col = _find_column(subset, "std", "metric_std", required=False)
        result = pd.DataFrame(
            {
                "model": subset[model_col].astype(str),
                "formulation": (
                    subset[formulation_col].astype(str)
                    if formulation_col is not None
                    else subset[model_col].astype(str)
                ),
                "mean": pd.to_numeric(subset[mean_col], errors="coerce"),
                "std": (
                    pd.to_numeric(subset[std_col], errors="coerce")
                    if std_col is not None
                    else 0.0
                ),
            }
        )
    else:
        value_col = _find_column(frame, metric)
        group_columns = [model_col] + ([formulation_col] if formulation_col is not None else [])
        grouped = (
            frame.assign(_value=pd.to_numeric(frame[value_col], errors="coerce"))
            .groupby(group_columns, as_index=False)["_value"]
            .agg(["mean", "std"])
            .reset_index()
        )
        result = pd.DataFrame(
            {
                "model": grouped[model_col].astype(str),
                "formulation": (
                    grouped[formulation_col].astype(str)
                    if formulation_col is not None
                    else grouped[model_col].astype(str)
                ),
                "mean": grouped["mean"],
                "std": grouped["std"].fillna(0.0),
            }
        )
    result = result[np.isfinite(result["mean"])].copy()
    _require(len(result) > 0, f"No finite static values for {metric}")
    return result.sort_values(["formulation", "mean", "model"], kind="mergesort")


def _save_static_metric(
    recorder: _FigureRecorder,
    frame: pd.DataFrame,
    metric: str,
    *,
    slug: str,
    title: str,
    units: str,
    question: str,
    caveat: str,
) -> None:
    summary = _long_static_metric(frame, metric)
    fig, ax = plt.subplots(figsize=(11, 5.6))
    positions = np.arange(len(summary))
    colors = [_method_color(row.model, row.formulation) for row in summary.itertuples()]
    errors = summary["std"].fillna(0).to_numpy(float)
    ax.bar(positions, summary["mean"], yerr=errors, capsize=3, color=colors, alpha=0.85)
    ax.set_xticks(positions, [_method_label(value) for value in summary["model"]], rotation=28, ha="right")
    ax.set_ylabel(units)
    ax.grid(axis="y", alpha=0.2)
    recorder.save(
        fig,
        slug=slug,
        title=title,
        question=question,
        sources=["static_model_summary.csv"],
        population="20 matched outer held-out folds; primary common population",
        units=units,
        status="held-out repeated stratified evaluation",
        caveat=caveat,
    )


def _curve_summary(frame: pd.DataFrame, metric: str) -> pd.DataFrame:
    method_col = _find_column(frame, "method")
    budget_col = _find_column(frame, "budget", "query_budget", "queries")
    formulation_col = _find_column(frame, "formulation", required=False)
    metric_name_col = _find_column(frame, "metric", required=False)
    if metric in frame.columns:
        work = frame.copy()
        work["_value"] = pd.to_numeric(work[metric], errors="coerce")
    elif metric_name_col is not None and frame[metric_name_col].astype(str).eq(metric).any():
        work = frame[frame[metric_name_col].astype(str).eq(metric)].copy()
        value_col = _find_column(work, "mean", "value", "metric_mean")
        work["_value"] = pd.to_numeric(work[value_col], errors="coerce")
    else:
        raise ReportingDataError(f"Active curve metric {metric} is unavailable")
    work["_budget"] = pd.to_numeric(work[budget_col], errors="coerce")
    groups = [method_col, budget_col] + ([formulation_col] if formulation_col is not None else [])
    summary = (
        work[np.isfinite(work["_value"]) & np.isfinite(work["_budget"])]
        .groupby(groups, as_index=False)
        .agg(mean=("_value", "mean"), std=("_value", "std"), run_count=("_value", "count"))
    )
    summary = summary.rename(columns={method_col: "method", budget_col: "budget"})
    if formulation_col is not None:
        summary = summary.rename(columns={formulation_col: "formulation"})
    else:
        summary["formulation"] = summary["method"].astype(str)
    summary["std"] = summary["std"].fillna(0.0)
    _require(len(summary) > 0, f"No finite active curve values for {metric}")
    return summary


def _save_active_curve(
    recorder: _FigureRecorder,
    frame: pd.DataFrame,
    metric: str,
    *,
    slug: str,
    title: str,
    y_label: str,
    question: str,
    caveat: str,
    source: str = "active_learning_curve_summary.csv",
) -> None:
    summary = _curve_summary(frame, metric)
    fig, ax = plt.subplots(figsize=(11, 5.8))
    for (method, formulation), group in summary.groupby(["method", "formulation"], sort=True):
        group = group.sort_values("budget")
        color = _method_color(method, formulation)
        ax.plot(group["budget"], group["mean"], label=_method_label(method), color=color, lw=1.7)
        if (group["std"] > 0).any():
            ax.fill_between(
                group["budget"].to_numpy(float),
                (group["mean"] - group["std"]).to_numpy(float),
                (group["mean"] + group["std"]).to_numpy(float),
                color=color,
                alpha=0.10,
                linewidth=0,
            )
    ax.set_xlabel("Simulator queries")
    ax.set_ylabel(y_label)
    ax.grid(alpha=0.2)
    ax.legend(fontsize=7.2, ncol=2)
    recorder.save(
        fig,
        slug=slug,
        title=title,
        question=question,
        sources=[source],
        population="20 matched held-out runs; primary common population",
        units=f"{y_label}; query count",
        status="held-out active-learning evaluation",
        caveat=caveat,
    )


def _save_calibration(
    recorder: _FigureRecorder,
    frame: pd.DataFrame,
    formulation: str,
    *,
    slug: str,
    title: str,
) -> None:
    formulation_col = _find_column(frame, "formulation")
    probability_col = _find_column(
        frame, "mean_predicted_probability", "predicted_probability", "mean_probability"
    )
    observed_col = _find_column(
        frame, "observed_keyhole_fraction", "observed_fraction", "fraction_positive"
    )
    model_col = _find_column(frame, "model", "method", required=False)
    subset = frame[frame[formulation_col].astype(str).str.casefold().eq(formulation.casefold())].copy()
    _require(len(subset) > 0, f"No {formulation} probability calibration rows")
    subset["_predicted"] = pd.to_numeric(subset[probability_col], errors="coerce")
    subset["_observed"] = pd.to_numeric(subset[observed_col], errors="coerce")
    subset = subset[np.isfinite(subset["_predicted"]) & np.isfinite(subset["_observed"])]
    _require(len(subset) > 0, f"No finite {formulation} calibration rows")
    fig, ax = plt.subplots(figsize=(7.2, 6.1))
    grouping = [model_col] if model_col is not None else []
    if grouping:
        for model, group in subset.groupby(model_col, sort=True):
            group = group.sort_values("_predicted")
            ax.plot(group["_predicted"], group["_observed"], marker="o", ms=4, label=_method_label(model))
    else:
        subset = subset.sort_values("_predicted")
        ax.plot(subset["_predicted"], subset["_observed"], marker="o", color=_method_color(formulation))
    ax.plot([0, 1], [0, 1], ls=":", color="#444444", label="ideal calibration")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Mean predicted Keyhole probability")
    ax.set_ylabel("Observed Keyhole fraction")
    ax.grid(alpha=0.2)
    ax.legend(fontsize=7.5)
    caveat = (
        "pooled repeated-fold calibration is descriptive because each simulation appears in several repeats; "
        + (
            "Gaussian-tail probabilities also inherit the training-only point-threshold approximation"
            if formulation == "max_depth"
            else "the 0.5 decision boundary is not a physical scalar threshold"
        )
    )
    recorder.save(
        fig,
        slug=slug,
        title=title,
        question=f"Are held-out {formulation} probabilities calibrated?",
        sources=["static_probability_calibration.csv"],
        population="pooled held-out predictions from 20 matched outer folds",
        units="probability / fraction",
        status="held-out pooled calibration diagnostic",
        caveat=caveat,
    )


def _save_threshold_trajectories(
    recorder: _FigureRecorder,
    frame: pd.DataFrame,
    formulation: str,
    *,
    slug: str,
    title: str,
    source: str,
) -> None:
    formulation_col = _find_column(frame, "formulation")
    method_col = _find_column(frame, "method")
    budget_col = _find_column(frame, "budget")
    run_col = _find_column(frame, "run_id")
    threshold_col = _find_column(frame, "threshold", "threshold_um", "training_only_threshold_um")
    subset = frame[frame[formulation_col].astype(str).str.casefold().eq(formulation.casefold())].copy()
    subset["_budget"] = pd.to_numeric(subset[budget_col], errors="coerce")
    subset["_threshold"] = pd.to_numeric(subset[threshold_col], errors="coerce")
    subset = subset[np.isfinite(subset["_budget"]) & np.isfinite(subset["_threshold"])]
    _require(len(subset) > 0, f"No finite threshold history for {formulation}")
    fig, ax = plt.subplots(figsize=(11, 5.8))
    for method, method_group in subset.groupby(method_col, sort=True):
        for _, run_group in method_group.groupby(run_col, sort=True):
            run_group = run_group.sort_values("_budget")
            ax.plot(
                run_group["_budget"],
                run_group["_threshold"],
                color=_method_color(method, formulation),
                alpha=0.10,
                lw=0.8,
            )
        median = method_group.groupby("_budget")["_threshold"].median().sort_index()
        ax.plot(median.index, median.values, lw=2, color=_method_color(method, formulation), label=_method_label(method))
    ax.set_xlabel("Simulator queries")
    ax.set_ylabel("Training-only threshold (µm)")
    ax.grid(alpha=0.2)
    ax.legend(fontsize=7.4, ncol=2)
    recorder.save(
        fig,
        slug=slug,
        title=title,
        question=f"How quickly does the queried-only {formulation} threshold stabilize?",
        sources=[source],
        population="queried subsets from matched active-learning runs",
        units="threshold µm; query count",
        status="query-only training diagnostic; held-out sets excluded",
        caveat="thin lines are individual runs; threshold movement may reflect changing queried-set composition, not a universal physical constant",
    )


def _save_aulc_distribution(
    recorder: _FigureRecorder,
    frame: pd.DataFrame,
    metric_column: str,
    *,
    slug: str,
    title: str,
    y_label: str,
    question: str,
    lower_is_better: bool,
) -> None:
    method_col = _find_column(frame, "method")
    formulation_col = _find_column(frame, "formulation")
    value_col = _find_column(frame, metric_column)
    work = frame[[method_col, formulation_col, value_col]].copy()
    work["_value"] = pd.to_numeric(work[value_col], errors="coerce")
    work = work[np.isfinite(work["_value"])]
    _require(len(work) > 0, f"No finite AULC values for {metric_column}")
    methods = sorted(work[method_col].astype(str).unique())
    data = [work.loc[work[method_col].astype(str).eq(method), "_value"].to_numpy(float) for method in methods]
    fig, ax = plt.subplots(figsize=(12, 5.8))
    boxes = ax.boxplot(data, tick_labels=[_method_label(value) for value in methods], showfliers=False, patch_artist=True)
    for patch, method in zip(boxes["boxes"], methods):
        formulation = work.loc[work[method_col].astype(str).eq(method), formulation_col].astype(str).iloc[0]
        patch.set_facecolor(_method_color(method, formulation))
        patch.set_alpha(0.65)
    rng = np.random.default_rng(6022026)
    for position, values in enumerate(data, start=1):
        ax.scatter(position + rng.uniform(-0.09, 0.09, len(values)), values, s=13, color="#333333", alpha=0.35)
    ax.set_ylabel(y_label)
    ax.tick_params(axis="x", rotation=30)
    ax.grid(axis="y", alpha=0.2)
    direction = "lower is better" if lower_is_better else "higher is better"
    recorder.save(
        fig,
        slug=slug,
        title=title,
        question=question,
        sources=["active_learning_aulc_summary.csv"],
        population="20 matched primary-common outer runs",
        units=f"normalized AULC ({direction})",
        status="held-out active-learning summary",
        caveat="box points are repeated-CV runs and are not statistically independent; comparisons must remain paired by run",
    )


def _surface_matrix(group: pd.DataFrame, value_column: str) -> tuple[np.ndarray, np.ndarray, np.ma.MaskedArray]:
    i_col = _find_column(group, "grid_i")
    j_col = _find_column(group, "grid_j")
    x_col = _find_column(group, "x_value_display")
    y_col = _find_column(group, "y_value_display")
    support_col = _find_column(group, "supported")
    value_col = _find_column(group, value_column)
    work = group.copy()
    work["_support"] = _bool_values(work[support_col])
    x_matrix = work.pivot(index=j_col, columns=i_col, values=x_col).to_numpy(float)
    y_matrix = work.pivot(index=j_col, columns=i_col, values=y_col).to_numpy(float)
    value_matrix = work.pivot(index=j_col, columns=i_col, values=value_col).to_numpy(float)
    support_matrix = work.pivot(index=j_col, columns=i_col, values="_support").to_numpy(bool)
    _require(support_matrix.any(), "This slice has no cells passing both 4D support masks")
    return x_matrix, y_matrix, np.ma.array(value_matrix, mask=~support_matrix)


def _surface_context(group: pd.DataFrame) -> str:
    fixed: list[str] = []
    varied = {str(group["x_feature"].iloc[0]), str(group["y_feature"].iloc[0])}
    for feature in FEATURE_COLUMNS:
        if feature in varied:
            continue
        column = f"fixed_{feature}"
        if column not in group:
            continue
        values = pd.to_numeric(group[column], errors="coerce").dropna()
        if not len(values):
            continue
        value = float(values.iloc[0])
        display = value * 1e6 if feature == "LS" else value
        fixed.append(f"{feature}={display:.4g} {FEATURE_UNITS[feature]}")
    return ", ".join(fixed) if fixed else "other inputs fixed at their common-population medians"


def _save_surface_family(
    recorder: _FigureRecorder,
    surfaces: pd.DataFrame,
    population: pd.DataFrame | None,
    pair: str,
) -> None:
    pair_col = _find_column(surfaces, "slice_pair")
    group = surfaces[surfaces[pair_col].astype(str).eq(pair)].copy()
    _require(len(group) > 0, f"No boundary surface rows for {pair}")
    x_feature = str(group["x_feature"].iloc[0])
    y_feature = str(group["y_feature"].iloc[0])
    x_label = FEATURE_LABELS.get(x_feature, x_feature)
    y_label = FEATURE_LABELS.get(y_feature, y_feature)
    context = _surface_context(group)
    common_caveat = (
        f"{context}; descriptive full-common fit, not held-out; 2D projection of a 4D problem; "
        "grey cells fail the 4D convex-hull and/or nearest-neighbour support mask"
    )

    def observed(ax: plt.Axes) -> None:
        if population is None or len(population) == 0:
            return
        if not {x_feature, y_feature}.issubset(population.columns):
            return
        labels = _label_series(population)
        x_values = _display_values(x_feature, pd.to_numeric(population[x_feature], errors="coerce"))
        y_values = _display_values(y_feature, pd.to_numeric(population[y_feature], errors="coerce"))
        finite = np.isfinite(x_values) & np.isfinite(y_values)
        ax.scatter(
            x_values[finite & ~labels.to_numpy()],
            y_values[finite & ~labels.to_numpy()],
            s=12,
            facecolors="none",
            edgecolors=BLUE,
            linewidths=0.6,
            alpha=0.45,
        )
        ax.scatter(
            x_values[finite & labels.to_numpy()],
            y_values[finite & labels.to_numpy()],
            s=16,
            marker="x",
            color=RED,
            linewidths=0.8,
            alpha=0.6,
        )

    x_grid, y_grid, binary = _surface_matrix(group, "binary_gpc_keyhole_probability")
    fig, ax = plt.subplots(figsize=(8.3, 6.3))
    ax.set_facecolor(LIGHT_GREY)
    mesh = ax.pcolormesh(x_grid, y_grid, binary, cmap="RdBu_r", vmin=0, vmax=1, shading="auto")
    finite_binary = binary.compressed()
    if len(finite_binary) and float(np.min(finite_binary)) <= 0.5 <= float(np.max(finite_binary)):
        ax.contour(x_grid, y_grid, binary, levels=[0.5], colors="black", linewidths=2)
    observed(ax)
    fig.colorbar(mesh, ax=ax, label="Descriptive GPC P(Keyhole)")
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    recorder.save(
        fig,
        slug=f"{pair}_supported_binary_boundary_slice",
        title=f"{pair} supported binary GPC boundary slice",
        question="Where does the descriptive binary GPC place P(Keyhole)=0.5 inside observed support?",
        sources=["boundary_surface_data.csv", "primary_common_population.csv"],
        population="full 405-row Binary/Max-Depth common population",
        units=f"{FEATURE_UNITS[x_feature]}; {FEATURE_UNITS[y_feature]}; probability",
        status="descriptive/oracle surface; not held-out and unavailable to acquisition",
        caveat=common_caveat,
    )

    x_grid, y_grid, depth = _surface_matrix(group, "max_depth_gpr_mean_um")
    threshold_col = _find_column(group, "descriptive_full_common_threshold_um")
    threshold = float(pd.to_numeric(group[threshold_col], errors="coerce").dropna().iloc[0])
    fig, ax = plt.subplots(figsize=(8.3, 6.3))
    ax.set_facecolor(LIGHT_GREY)
    mesh = ax.pcolormesh(x_grid, y_grid, depth, cmap="viridis", shading="auto")
    finite_depth = depth.compressed()
    if len(finite_depth) and float(np.min(finite_depth)) <= threshold <= float(np.max(finite_depth)):
        ax.contour(x_grid, y_grid, depth, levels=[threshold], colors="white", linewidths=2)
    observed(ax)
    fig.colorbar(mesh, ax=ax, label="Descriptive max-depth GPR mean (µm)")
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    recorder.save(
        fig,
        slug=f"{pair}_supported_max_depth_boundary_slice",
        title=f"{pair} supported maximum-depth GPR boundary slice",
        question="Where does the descriptive maximum-depth surface cross the full-common oracle threshold?",
        sources=["boundary_surface_data.csv", "primary_common_population.csv"],
        population="full 405-row Binary/Max-Depth common population",
        units=f"{FEATURE_UNITS[x_feature]}; {FEATURE_UNITS[y_feature]}; maximum depth µm",
        status="descriptive/oracle surface; not held-out and unavailable to acquisition",
        caveat=common_caveat + "; the full-common scalar threshold is an unavailable oracle reference",
    )

    _, _, binary_for_overlay = _surface_matrix(group, "binary_gpc_keyhole_probability")
    _, _, depth_for_overlay = _surface_matrix(group, "max_depth_gpr_mean_um")
    fig, ax = plt.subplots(figsize=(8.3, 6.3))
    ax.set_facecolor(LIGHT_GREY)
    support_background = np.ma.array(np.ones(binary_for_overlay.shape), mask=binary_for_overlay.mask)
    ax.pcolormesh(x_grid, y_grid, support_background, cmap=ListedColormap(["#FAFAFA"]), shading="auto")
    if len(binary_for_overlay.compressed()) and np.min(binary_for_overlay) <= 0.5 <= np.max(binary_for_overlay):
        ax.contour(x_grid, y_grid, binary_for_overlay, levels=[0.5], colors=PURPLE, linewidths=2.2)
    if len(depth_for_overlay.compressed()) and np.min(depth_for_overlay) <= threshold <= np.max(depth_for_overlay):
        ax.contour(x_grid, y_grid, depth_for_overlay, levels=[threshold], colors=TEAL, linewidths=2.2, linestyles="--")
    observed(ax)
    ax.plot([], [], color=PURPLE, lw=2.2, label="Binary GPC P=0.5")
    ax.plot([], [], color=TEAL, lw=2.2, ls="--", label="Max-depth GPR mean=tau")
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.legend(fontsize=8)
    recorder.save(
        fig,
        slug=f"{pair}_binary_max_depth_boundary_overlay",
        title=f"{pair} supported Binary/Max-Depth boundary overlay",
        question="Do the two descriptive boundary formulations place their contours in the same supported region?",
        sources=["boundary_surface_data.csv", "primary_common_population.csv"],
        population="full 405-row Binary/Max-Depth common population",
        units=f"{FEATURE_UNITS[x_feature]}; {FEATURE_UNITS[y_feature]}",
        status="descriptive/oracle comparison; not held-out",
        caveat=common_caveat + "; contour proximity is visual and does not replace held-out q20/q30 evidence",
    )

    disagreement_col = _find_column(group, "binary_max_depth_disagreement")
    binary_class_col = _find_column(group, "binary_gpc_predicted_keyhole")
    depth_class_col = _find_column(group, "max_depth_predicted_keyhole")
    support_col = _find_column(group, "supported")
    work = group.copy()
    binary_class = _bool_values(work[binary_class_col])
    depth_class = _bool_values(work[depth_class_col])
    categories = binary_class.astype(int) + 2 * depth_class.astype(int)
    work["_category"] = categories
    i_col = _find_column(work, "grid_i")
    j_col = _find_column(work, "grid_j")
    category_matrix = work.pivot(index=j_col, columns=i_col, values="_category").to_numpy(float)
    support_matrix = work.assign(_support=_bool_values(work[support_col])).pivot(
        index=j_col, columns=i_col, values="_support"
    ).to_numpy(bool)
    category_masked = np.ma.array(category_matrix, mask=~support_matrix)
    fig, ax = plt.subplots(figsize=(8.3, 6.3))
    ax.set_facecolor(LIGHT_GREY)
    cmap = ListedColormap(["#D9EAF7", "#D7B5D8", "#B8E0C1", "#F6C6C2"])
    ax.pcolormesh(x_grid, y_grid, category_masked, cmap=cmap, vmin=-0.5, vmax=3.5, shading="auto")
    observed(ax)
    legend_handles = [
        plt.Line2D([0], [0], marker="s", color="none", markerfacecolor=color, markeredgecolor="none", markersize=9, label=label)
        for color, label in zip(
            cmap.colors,
            ["both Conduction", "Binary only Keyhole", "Max-Depth only Keyhole", "both Keyhole"],
        )
    ]
    ax.legend(handles=legend_handles, fontsize=7.7, loc="best")
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    disagreement = _bool_values(work[disagreement_col]) & _bool_values(work[support_col])
    fraction = float(disagreement.sum() / max(_bool_values(work[support_col]).sum(), 1))
    recorder.save(
        fig,
        slug=f"{pair}_binary_max_depth_disagreement_map",
        title=f"{pair} supported Binary/Max-Depth disagreement map ({fraction:.1%})",
        question="Which supported cells are assigned to different regimes by the two descriptive formulations?",
        sources=["boundary_surface_data.csv", "boundary_disagreement_summary.csv", "primary_common_population.csv"],
        population="full 405-row Binary/Max-Depth common population",
        units=f"{FEATURE_UNITS[x_feature]}; {FEATURE_UNITS[y_feature]}; regime category",
        status="descriptive/oracle disagreement; not held-out",
        caveat=common_caveat + "; cell fractions depend on the displayed grid and must not be treated as physical domain volume",
    )


def _save_representative_trajectories(
    recorder: _FigureRecorder,
    aulc: pd.DataFrame,
    queries: pd.DataFrame,
) -> None:
    selected = select_representative_trajectory_runs(aulc)
    run_col = _find_column(queries, "run_id")
    method_col = _find_column(queries, "method")
    order_col = _find_column(queries, "query_order")
    label_col = _find_column(queries, "revealed_has_keyhole", "has_keyhole")
    depth_col = _find_column(queries, "revealed_max_depth_um", "max_depth_um")
    boundary_col = _find_column(
        queries,
        "empirical_boundary_distance_evaluation_only",
        "empirical_boundary_distance",
    )
    p_col = _find_column(queries, "P", "P_W")
    vx_col = _find_column(queries, "VX", "VX_m_per_s")
    stage_col = _find_column(queries, "selection_stage", required=False)
    for row in selected.itertuples(index=False):
        subset = queries[
            queries[run_col].astype(str).eq(str(row.run_id))
            & queries[method_col].astype(str).eq(str(row.method))
        ].copy()
        _require(len(subset) > 0, f"No query history for {row.run_id}/{row.method}")
        subset["_order"] = pd.to_numeric(subset[order_col], errors="coerce")
        subset["_boundary"] = pd.to_numeric(subset[boundary_col], errors="coerce")
        subset["_P"] = pd.to_numeric(subset[p_col], errors="coerce")
        subset["_VX"] = pd.to_numeric(subset[vx_col], errors="coerce")
        subset["_label"] = _bool_values(subset[label_col])
        subset["_depth"] = pd.to_numeric(subset[depth_col], errors="coerce")
        subset = subset.sort_values("_order", kind="mergesort")
        fig, axes = plt.subplots(1, 2, figsize=(13, 5.8))
        ax = axes[0]
        scatter = ax.scatter(
            subset["_VX"],
            subset["_P"],
            c=subset["_order"],
            cmap="viridis",
            s=np.where(subset["_label"], 52, 34),
            marker="o",
            edgecolors=np.where(subset["_label"], RED, BLUE),
            linewidths=1.2,
        )
        if stage_col is not None:
            warm = subset[stage_col].astype(str).str.contains("warm", case=False, na=False)
            ax.scatter(
                subset.loc[warm, "_VX"],
                subset.loc[warm, "_P"],
                facecolors="none",
                edgecolors="black",
                s=90,
                linewidths=0.9,
                label="shared warm start",
            )
            ax.legend(fontsize=8)
        fig.colorbar(scatter, ax=ax, label="Query order")
        ax.set_xlabel("VX (m/s)")
        ax.set_ylabel("P (W)")
        ax.grid(alpha=0.2)
        ax.set_title("P–VX projection of queried simulations")

        ax = axes[1]
        colors = np.where(subset["_label"], RED, BLUE)
        ax.scatter(subset["_order"], subset["_boundary"], c=colors, s=28, alpha=0.8)
        ax.plot(subset["_order"], subset["_boundary"], color=GREY, lw=0.7, alpha=0.5)
        ax.set_xlabel("Query order")
        ax.set_ylabel("True empirical opposite-label distance (standardized 4D)")
        ax.grid(alpha=0.2)
        ax.set_title("Evaluation-only boundary proximity after selection")
        recorder.save(
            fig,
            slug=f"representative_acquisition_trajectory_{row.formulation}_{row.representative_rank}",
            title=(
                f"{str(row.formulation).replace('_', ' ').title()} {row.representative_rank} q20-AULC "
                f"trajectory: {row.run_id}"
            ),
            question="What did the deterministically selected representative run query, and how boundary-near were those points?",
            sources=["active_learning_aulc_summary.csv", "active_query_history.csv"],
            population=f"training pool of matched run {row.run_id}; method {_method_label(row.method)}",
            units="P W; VX m/s; standardized 4D boundary distance; query count",
            status="active query history; held-out q20 AULC used only for post-hoc representative selection",
            caveat=(
                "P–VX is only a projection of a 4D acquisition; manual label, max depth, and empirical boundary distance "
                "were hidden before each query; best/median/worst selection is descriptive, not an independent test"
            ),
        )


def generate_phase6_figures(
    output_dir: str | Path,
    artifacts: Mapping[str, pd.DataFrame] | None = None,
    minimum_count: int = 40,
) -> pd.DataFrame:
    """Generate an auditable Phase 6 PNG suite and return manifest rows.

    Every generated figure is backed by one or more declared Phase 6 artifact
    tables.  Unsupported figures are skipped and recorded in
    ``manifest.attrs['skipped_figures']``; they are never filled with dummy
    points.  By default the function fails closed unless at least forty valid,
    non-decorative figures were actually written.
    """

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    _require(int(minimum_count) == minimum_count and minimum_count >= 0, "minimum_count must be a non-negative integer")
    source = load_phase6_artifacts(destination) if artifacts is None else dict(artifacts)
    # Accept either stems or filenames from callers without mutating their
    # DataFrames.  Existing exact keys remain authoritative.
    normalized: dict[str, pd.DataFrame] = dict(source)
    for key, value in list(source.items()):
        path = Path(str(key))
        normalized.setdefault(path.name, value)
        normalized.setdefault(path.stem, value)
    recorder = _FigureRecorder(destination)

    # ------------------------------------------------------------------
    # Population, labels, and scalar responses.
    # ------------------------------------------------------------------
    def population_readiness() -> None:
        frame = _artifact(normalized, "population_audit")
        partition_col = _find_column(frame, "partition")
        primary_col = _find_column(frame, "primary_ready")
        g3_col = _find_column(frame, "secondary_g3_ready", "g3_ready")
        work = frame.assign(
            _primary=_bool_values(frame[primary_col]),
            _g3=_bool_values(frame[g3_col]),
        )
        summary = (
            work.groupby(partition_col, as_index=False)
            .agg(retained=(partition_col, "size"), primary_ready=("_primary", "sum"), g3_ready=("_g3", "sum"))
            .sort_values(partition_col)
        )
        positions = np.arange(len(summary))
        width = 0.26
        fig, ax = plt.subplots(figsize=(10, 5.4))
        ax.bar(positions - width, summary["retained"], width, label="retained", color="#B7C9E2")
        ax.bar(positions, summary["primary_ready"], width, label="Binary/Max-Depth common", color=TEAL)
        ax.bar(positions + width, summary["g3_ready"], width, label="three-way G3 common", color=ORANGE)
        ax.set_xticks(positions, summary[partition_col], rotation=18)
        ax.set_ylabel("Simulations")
        ax.grid(axis="y", alpha=0.2)
        ax.legend(fontsize=8)
        recorder.save(
            fig,
            slug="combined_population_readiness",
            title="Combined population readiness by audited partition",
            question="Which retained rows support the primary and three-way comparisons?",
            sources=["population_audit.csv"],
            population=f"{len(frame):,} retained simulation rows",
            units="simulation count",
            status="descriptive provenance/readiness audit",
            caveat="ineligible rows remain visible; the primary Binary arm may not use rows unavailable to maximum depth",
        )

    _attempt(recorder, "combined_population_readiness", population_readiness)

    def label_composition() -> None:
        frame = _artifact(normalized, "primary_common_population")
        labels = _label_series(frame)
        counts = np.array([int((~labels).sum()), int(labels.sum())])
        fig, ax = plt.subplots(figsize=(7.5, 5.2))
        bars = ax.bar(["Conduction", "Keyhole"], counts, color=[BLUE, RED])
        ax.bar_label(bars, labels=[f"{value:,}" for value in counts], padding=3)
        ax.set_ylabel("Simulations")
        ax.grid(axis="y", alpha=0.2)
        recorder.save(
            fig,
            slug="label_composition_primary_common",
            title="Manual Keyhole label composition in the primary common population",
            question="How imbalanced is the manual reference label?",
            sources=["primary_common_population.csv"],
            population=f"{len(frame):,} exact Binary/Max-Depth-ready simulations",
            units="simulation count",
            status="descriptive full-common composition",
            caveat="has_keyhole means at least one valid saved physical frame was manually labelled Keyhole; it is not a scalar-derived label",
        )

    _attempt(recorder, "label_composition_primary_common", label_composition)

    def partition_composition() -> None:
        frame = _artifact(normalized, "primary_common_population")
        partition_col = _find_column(frame, "partition")
        labels = _label_series(frame)
        work = frame.assign(_label=labels)
        table = work.groupby(partition_col)["_label"].agg(total="size", keyhole="sum").sort_index()
        table["conduction"] = table["total"] - table["keyhole"]
        fig, ax = plt.subplots(figsize=(9.5, 5.3))
        positions = np.arange(len(table))
        ax.bar(positions, table["conduction"], label="Conduction", color=BLUE)
        ax.bar(positions, table["keyhole"], bottom=table["conduction"], label="Keyhole", color=RED)
        ax.set_xticks(positions, table.index, rotation=18)
        ax.set_ylabel("Simulations")
        ax.legend()
        ax.grid(axis="y", alpha=0.2)
        recorder.save(
            fig,
            slug="partition_composition_primary_common",
            title="Primary common population by partition and manual label",
            question="How do label prevalence and sample size differ across old/new source partitions?",
            sources=["primary_common_population.csv"],
            population=f"{len(frame):,} exact primary-common simulations",
            units="simulation count",
            status="descriptive composition; old/new is not the primary split",
            caveat="partition imbalance motivates a secondary transfer stress test but does not replace repeated combined-data validation",
        )

    _attempt(recorder, "partition_composition_primary_common", partition_composition)

    _attempt(
        recorder,
        "max_depth_distribution_by_manual_label",
        lambda: _box_by_label(
            recorder,
            _artifact(normalized, "primary_common_population"),
            _depth_column(_artifact(normalized, "primary_common_population")),
            slug="max_depth_distribution_by_manual_label",
            title="Maximum depth by manual Keyhole label",
            question="Does unchanged maximum depth separate the manual morphology labels?",
            source="primary_common_population.csv",
            units="µm",
            caveat="association motivates a continuous formulation but does not prove semantic equivalence or held-out sample efficiency",
        ),
    )
    _attempt(
        recorder,
        "g3_distribution_by_manual_label",
        lambda: _box_by_label(
            recorder,
            _artifact(normalized, "secondary_g3_common_population"),
            _g3_column(_artifact(normalized, "secondary_g3_common_population")),
            slug="g3_distribution_by_manual_label",
            title="G3 persistent depth by manual Keyhole label",
            question="How does the secondary persistent-depth comparator separate labels?",
            source="secondary_g3_common_population.csv",
            units="µm",
            caveat="G3 imposes a 50 µm persistence concept absent from the manual at-least-once saved-frame definition",
        ),
    )

    def max_depth_vs_g3() -> None:
        frame = _artifact(normalized, "secondary_g3_common_population")
        depth_col = _depth_column(frame)
        g3_col = _g3_column(frame)
        labels = _label_series(frame)
        depth = pd.to_numeric(frame[depth_col], errors="coerce")
        g3 = pd.to_numeric(frame[g3_col], errors="coerce")
        finite = np.isfinite(depth) & np.isfinite(g3)
        _require(finite.sum() >= 3, "Fewer than three complete max-depth/G3 rows")
        fig, ax = plt.subplots(figsize=(7.6, 5.8))
        ax.scatter(depth[finite & ~labels], g3[finite & ~labels], color=BLUE, s=22, alpha=0.55, label="Conduction")
        ax.scatter(depth[finite & labels], g3[finite & labels], color=RED, s=25, alpha=0.65, label="Keyhole")
        ax.set_xlabel("Maximum depth (µm)")
        ax.set_ylabel("G3 persistent depth (µm)")
        ax.grid(alpha=0.2)
        ax.legend()
        recorder.save(
            fig,
            slug="max_depth_vs_g3_by_manual_label",
            title="Maximum depth versus G3, colored by manual label",
            question="Do the transient-sensitive and persistence-sensitive continuous responses carry distinct information?",
            sources=["secondary_g3_common_population.csv"],
            population=f"{int(finite.sum()):,} exact three-way complete simulations",
            units="maximum depth µm; G3 µm",
            status="descriptive full-common association",
            caveat="correlation or separation does not establish causal or universal physical superiority",
        )

    _attempt(recorder, "max_depth_vs_g3_by_manual_label", max_depth_vs_g3)

    def max_depth_partition_label() -> None:
        frame = _artifact(normalized, "primary_common_population")
        depth_col = _depth_column(frame)
        partition_col = _find_column(frame, "partition")
        labels = _label_series(frame)
        partitions = sorted(frame[partition_col].astype(str).unique())
        fig, axes = plt.subplots(1, len(partitions), figsize=(5 * len(partitions), 5.2), sharey=True)
        axes_array = np.atleast_1d(axes)
        for ax, partition in zip(axes_array, partitions):
            mask = frame[partition_col].astype(str).eq(partition)
            groups = [
                pd.to_numeric(frame.loc[mask & ~labels, depth_col], errors="coerce").dropna(),
                pd.to_numeric(frame.loc[mask & labels, depth_col], errors="coerce").dropna(),
            ]
            _require(all(len(group) for group in groups), f"{partition} lacks one label for max-depth plot")
            ax.boxplot(groups, tick_labels=["Cond.", "Keyhole"], showfliers=False)
            ax.set_title(partition)
            ax.grid(axis="y", alpha=0.2)
        axes_array[0].set_ylabel("Maximum depth (µm)")
        recorder.save(
            fig,
            slug="max_depth_distribution_by_partition_and_label",
            title="Maximum-depth separation within each source partition",
            question="Is the descriptive max-depth/label relationship visibly partition-dependent?",
            sources=["primary_common_population.csv"],
            population=f"{len(frame):,} primary-common simulations across base partitions",
            units="maximum depth µm",
            status="descriptive partition robustness context",
            caveat="small old-partition positive counts make visual separation imprecise; source-only thresholds are evaluated separately",
        )

    _attempt(recorder, "max_depth_distribution_by_partition_and_label", max_depth_partition_label)

    # ------------------------------------------------------------------
    # Maximum-depth event semantics and raw-review selection.
    # ------------------------------------------------------------------
    for column, slug, title, question, caveat in (
        (
            "max_depth_relative_to_T0",
            "max_depth_event_timing_relative_to_T0",
            "Maximum-depth event timing relative to T0",
            "Does the deepest event occur before, inside, or after the unchanged T0 interval?",
            "timing categories audit the unchanged target definition; they do not redefine maximum depth",
        ),
        (
            "saved_keyhole_episode_span_relation",
            "max_depth_relative_to_saved_keyhole_timing",
            "Maximum-depth timing relative to saved Keyhole episode spans",
            "Where does maximum depth occur relative to the span of saved Keyhole frames?",
            "episode-span membership is not exact frame-level morphology at the maximum-depth monitor sample",
        ),
        (
            "max_depth_relative_to_active_region",
            "max_depth_event_timing_relative_to_active_region",
            "Maximum-depth timing relative to the active region",
            "How often is the deepest event outside the pre-existing active-region window?",
            "the active-region definition is inherited unchanged; this is a semantic audit, not target selection",
        ),
    ):
        _attempt(
            recorder,
            slug,
            lambda column=column, slug=slug, title=title, question=question, caveat=caveat: _categorical_counts(
                recorder,
                _artifact(normalized, "max_depth_event_audit"),
                str(_find_column(_artifact(normalized, "max_depth_event_audit"), column)),
                slug=slug,
                title=title,
                question=question,
                source="max_depth_event_audit.csv",
                population="full primary-common physical event audit",
                status="descriptive semantic/timing audit",
                caveat=caveat,
            ),
        )

    def event_context_flags() -> None:
        frame = _artifact(normalized, "max_depth_event_audit")
        flags = [
            "near_recording_end_last_5pct",
            "near_laser_exit_within_5pct_exit_time",
            "flag_depth_bounding_box_ambiguity_candidate",
            "recording_ends_before_90pct_domain",
            "flag_primary_window_unstable_week6_rule",
        ]
        present = [column for column in flags if column in frame]
        _require(present, "No event-context flags are available")
        rates = [_bool_values(frame[column]).mean() for column in present]
        fig, ax = plt.subplots(figsize=(10.5, 5.4))
        positions = np.arange(len(present))
        ax.bar(positions, rates, color=[ORANGE if value > 0 else BLUE for value in rates])
        ax.set_xticks(positions, [_method_label(value) for value in present], rotation=25, ha="right")
        ax.set_ylabel("Fraction of simulations")
        ax.set_ylim(0, max(0.05, min(1.0, max(rates) * 1.25)))
        ax.grid(axis="y", alpha=0.2)
        recorder.save(
            fig,
            slug="max_depth_event_context_and_ambiguity_flags",
            title="Maximum-depth recording-end, laser-exit, and geometry flags",
            question="Do obvious timing or geometry warning contexts dominate maximum-depth events?",
            sources=["max_depth_event_audit.csv"],
            population=f"{len(frame):,} primary-common event-audit simulations",
            units="fraction of simulations",
            status="descriptive semantic artifact audit",
            caveat="a flag marks review context, not proof that the maximum-depth scalar is invalid",
        )

    _attempt(recorder, "max_depth_event_context_and_ambiguity_flags", event_context_flags)

    def recording_fraction_distribution() -> None:
        frame = _artifact(normalized, "max_depth_event_audit")
        fraction_col = _find_column(frame, "recording_row_fraction")
        labels = _label_series(frame)
        values = pd.to_numeric(frame[fraction_col], errors="coerce")
        fig, ax = plt.subplots(figsize=(8.2, 5.2))
        bins = np.linspace(0, 1, 21)
        ax.hist(values[~labels].dropna(), bins=bins, alpha=0.55, color=BLUE, label="Conduction")
        ax.hist(values[labels].dropna(), bins=bins, alpha=0.55, color=RED, label="Keyhole")
        ax.axvspan(0.95, 1.0, color=ORANGE, alpha=0.12, label="last 5%")
        ax.set_xlabel("Max-depth monitor row / recording length")
        ax.set_ylabel("Simulations")
        ax.legend()
        ax.grid(axis="y", alpha=0.2)
        recorder.save(
            fig,
            slug="max_depth_recording_fraction_by_label",
            title="Recording position of maximum depth by manual label",
            question="Are maximum-depth events concentrated at the recording end?",
            sources=["max_depth_event_audit.csv"],
            population=f"{len(frame):,} primary-common event-audit simulations",
            units="recording fraction; simulation count",
            status="descriptive semantic timing audit",
            caveat="recording-row fraction is not physical time equivalence to saved labelled frames",
        )

    _attempt(recorder, "max_depth_recording_fraction_by_label", recording_fraction_distribution)

    def depth_vs_recording_fraction() -> None:
        frame = _artifact(normalized, "max_depth_event_audit")
        labels = _label_series(frame)
        x = pd.to_numeric(frame[_find_column(frame, "recording_row_fraction")], errors="coerce")
        y = pd.to_numeric(frame[_find_column(frame, "max_depth_um")], errors="coerce")
        finite = np.isfinite(x) & np.isfinite(y)
        fig, ax = plt.subplots(figsize=(8.2, 5.5))
        ax.scatter(x[finite & ~labels], y[finite & ~labels], s=18, alpha=0.5, color=BLUE, label="Conduction")
        ax.scatter(x[finite & labels], y[finite & labels], s=21, alpha=0.6, color=RED, label="Keyhole")
        ax.axvspan(0.95, 1.0, color=ORANGE, alpha=0.12)
        ax.set_xlabel("Max-depth recording-row fraction")
        ax.set_ylabel("Maximum depth (µm)")
        ax.grid(alpha=0.2)
        ax.legend()
        recorder.save(
            fig,
            slug="max_depth_value_vs_recording_position",
            title="Maximum-depth value versus recording position",
            question="Are unusually deep cases explained mainly by late recording position?",
            sources=["max_depth_event_audit.csv"],
            population=f"{int(finite.sum()):,} finite primary-common event-audit simulations",
            units="recording fraction; maximum depth µm",
            status="descriptive semantic artifact audit",
            caveat="visual association cannot establish an artifact mechanism; flagged cases require raw trajectory/GIF review",
        )

    _attempt(recorder, "max_depth_value_vs_recording_position", depth_vs_recording_fraction)

    def oracle_error_types() -> None:
        frame = _artifact(normalized, "max_depth_event_audit")
        error_col = _find_column(frame, "descriptive_oracle_error_type")
        depth_col = _find_column(frame, "max_depth_um")
        threshold_col = _find_column(frame, "descriptive_oracle_threshold_um")
        values = pd.to_numeric(frame[depth_col], errors="coerce")
        categories = frame[error_col].astype(str)
        colors = {"correct": GREY, "false_positive": ORANGE, "false_negative": PURPLE}
        fig, ax = plt.subplots(figsize=(10, 5.5))
        order = np.argsort(values.to_numpy(float))
        for category in sorted(categories.unique()):
            mask = categories.eq(category).to_numpy() & np.isfinite(values.to_numpy(float))
            ranks = np.flatnonzero(mask[order])
            ax.scatter(ranks, values.to_numpy(float)[order][mask[order]], s=20, color=colors.get(category, BLUE), label=_method_label(category), alpha=0.7)
        threshold = float(pd.to_numeric(frame[threshold_col], errors="coerce").dropna().iloc[0])
        ax.axhline(threshold, color="black", ls="--", label=f"oracle tau={threshold:.2f} µm")
        ax.set_xlabel("Within-category displayed order")
        ax.set_ylabel("Maximum depth (µm)")
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.2)
        recorder.save(
            fig,
            slug="max_depth_descriptive_oracle_error_cases",
            title="Full-common maximum-depth oracle errors",
            question="Which high-depth negatives and low-depth positives remain under the best full-common scalar threshold?",
            sources=["max_depth_event_audit.csv"],
            population=f"{len(frame):,} primary-common simulations",
            units="maximum depth µm",
            status="unavailable full-common oracle diagnostic; not held-out",
            caveat="this threshold sees all manual labels and may never enter active acquisition or primary method ranking",
        )

    _attempt(recorder, "max_depth_descriptive_oracle_error_cases", oracle_error_types)

    def raw_review_reasons() -> None:
        frame = _artifact(normalized, "max_depth_raw_review_cases")
        reason_col = _find_column(frame, "review_reasons")
        exploded = frame[reason_col].fillna("").astype(str).str.split(";").explode().str.strip()
        exploded = exploded[exploded.ne("")]
        counts = exploded.value_counts()
        _require(len(counts) > 0, "No deterministic raw-review reasons")
        fig, ax = plt.subplots(figsize=(10, 5.5))
        positions = np.arange(len(counts))
        ax.barh(positions, counts, color=ORANGE)
        ax.set_yticks(positions, [_method_label(value) for value in counts.index])
        ax.invert_yaxis()
        ax.set_xlabel("Selected cases")
        ax.grid(axis="x", alpha=0.2)
        recorder.save(
            fig,
            slug="max_depth_raw_review_case_selection",
            title="Deterministic maximum-depth raw-review set",
            question="Which semantic-risk and error-case categories were selected for raw GIF/frame review?",
            sources=["max_depth_raw_review_cases.csv"],
            population=f"{len(frame):,} unique deterministic review cases",
            units="selected-case count",
            status="descriptive case-selection audit",
            caveat="selection does not relabel experiments or redefine the scalar after inspection; categories may overlap",
        )

    _attempt(recorder, "max_depth_raw_review_case_selection", raw_review_reasons)

    def event_marker_timeline(keyhole: bool, slug: str, title: str) -> None:
        frame = _artifact(normalized, "max_depth_event_audit")
        labels = _label_series(frame)
        subset = frame[labels.eq(keyhole)].copy()
        depth_col = _find_column(subset, "max_depth_um")
        subset["_depth"] = pd.to_numeric(subset[depth_col], errors="coerce")
        subset = subset.sort_values(["_depth", "experiment_name"], ascending=[False, True], kind="mergesort").head(8)
        _require(len(subset) > 0, "No event-marker cases")
        max_col = _find_column(subset, "max_depth_iteration")
        first_col = _find_column(subset, "first_keyhole_timestep", required=False)
        last_col = _find_column(subset, "last_keyhole_timestep", required=False)
        fig, ax = plt.subplots(figsize=(11, 5.7))
        span_count = 0
        for position, row in enumerate(subset.itertuples(index=False)):
            row_map = row._asdict()
            maximum = float(row_map[max_col])
            if first_col is not None and last_col is not None:
                first = pd.to_numeric(pd.Series([row_map[first_col]]), errors="coerce").iloc[0]
                last = pd.to_numeric(pd.Series([row_map[last_col]]), errors="coerce").iloc[0]
                if math.isfinite(float(first)) and math.isfinite(float(last)):
                    ax.hlines(position, float(first), float(last), color=RED, lw=5, alpha=0.35)
                    span_count += 1
            ax.scatter(maximum, position, color=TEAL, marker="D", s=38)
        p_col = _find_column(subset, "P", "P_W", required=False)
        vx_col = _find_column(subset, "VX", "VX_m_per_s", required=False)
        if p_col is not None and vx_col is not None:
            names = [
                f"case {index + 1}: P={float(p):.1f} W, VX={float(vx):.3f} m/s"
                for index, (p, vx) in enumerate(zip(subset[p_col], subset[vx_col]))
            ]
        else:
            names = [f"deterministic case {index + 1}" for index in range(len(subset))]
        ax.set_yticks(np.arange(len(subset)), names)
        ax.set_xlabel("Saved-label timestep / max-depth monitor iteration")
        ax.set_ylabel("Experiment")
        ax.grid(axis="x", alpha=0.2)
        if span_count:
            ax.plot([], [], color=RED, lw=5, alpha=0.35, label="first–last saved Keyhole span")
        ax.scatter([], [], color=TEAL, marker="D", label="max-depth iteration")
        ax.legend(fontsize=8)
        timing_caveat = (
            "monitor iterations and saved labelled frames are not asserted equivalent; the red span does not prove continuous Keyhole morphology between frames"
            if span_count
            else "monitor iterations and saved labelled frames are not asserted equivalent; no Keyhole span exists for these manual-negative cases"
        )
        recorder.save(
            fig,
            slug=slug,
            title=title,
            question="How do maximum-depth event markers align with the available saved Keyhole span in deterministic high-depth cases?",
            sources=["max_depth_event_audit.csv"],
            population=f"top {len(subset)} {'Keyhole' if keyhole else 'non-Keyhole'} cases by maximum depth",
            units="iteration/timestep index",
            status="descriptive event-marker audit; not a reconstructed time series",
            caveat=timing_caveat,
        )

    _attempt(
        recorder,
        "representative_keyhole_max_depth_event_timeline",
        lambda: event_marker_timeline(True, "representative_keyhole_max_depth_event_timeline", "High-depth Keyhole event-marker timelines"),
    )
    _attempt(
        recorder,
        "representative_non_keyhole_high_depth_event_timeline",
        lambda: event_marker_timeline(False, "representative_non_keyhole_high_depth_event_timeline", "High-depth non-Keyhole event-marker timelines"),
    )

    # ------------------------------------------------------------------
    # Model-independent empirical boundary reference and split audits.
    # ------------------------------------------------------------------
    def boundary_distance_distribution() -> None:
        frame = _artifact(normalized, "empirical_boundary_reference")
        distance_col = _find_column(frame, "empirical_boundary_distance")
        labels = _label_series(frame)
        values = pd.to_numeric(frame[distance_col], errors="coerce")
        finite = values[np.isfinite(values)]
        _require(len(finite) > 0, "No finite empirical boundary distances")
        fig, ax = plt.subplots(figsize=(8.5, 5.3))
        bins = np.linspace(float(finite.min()), float(finite.max()), 24)
        ax.hist(values[~labels].dropna(), bins=bins, color=BLUE, alpha=0.55, label="Conduction")
        ax.hist(values[labels].dropna(), bins=bins, color=RED, alpha=0.55, label="Keyhole")
        for quantile, color in ((0.10, ORANGE), (0.20, PURPLE), (0.30, TEAL)):
            level = float(np.quantile(finite, quantile))
            ax.axvline(level, color=color, ls="--", lw=1.4, label=f"global q{int(100*quantile)} cutoff")
        ax.set_xlabel("Nearest opposite-label distance in standardized 4D input space")
        ax.set_ylabel("Simulations")
        ax.grid(axis="y", alpha=0.2)
        ax.legend(fontsize=8)
        recorder.save(
            fig,
            slug="empirical_boundary_distance_distribution",
            title="Model-independent empirical boundary-distance distribution",
            question="How many observed experiments lie near an opposite manual label in physical input space?",
            sources=["empirical_boundary_reference.csv"],
            population=f"{len(frame):,} primary-common simulations",
            units="Euclidean distance in standardized P,VX,LS,ST space",
            status="full-label offline evaluation reference only",
            caveat="the score may define held-out q20/q30 evaluation subsets but must never enter fitting or acquisition",
        )

    _attempt(recorder, "empirical_boundary_distance_distribution", boundary_distance_distribution)

    def boundary_projection(pair: tuple[str, str]) -> None:
        frame = _artifact(normalized, "empirical_boundary_reference")
        left, right = pair
        _require({left, right}.issubset(frame.columns), f"Boundary reference lacks {pair}")
        labels = _label_series(frame)
        x = _display_values(left, pd.to_numeric(frame[left], errors="coerce"))
        y = _display_values(right, pd.to_numeric(frame[right], errors="coerce"))
        fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), sharex=True, sharey=True)
        for ax, q, color in zip(axes, (10, 20, 30), (ORANGE, PURPLE, TEAL)):
            flag_col = _find_column(frame, f"global_q{q}")
            flag = _bool_values(frame[flag_col])
            ax.scatter(x[~flag], y[~flag], s=10, color="#CCCCCC", alpha=0.35)
            ax.scatter(x[flag & ~labels], y[flag & ~labels], s=23, color=BLUE, label="Conduction")
            ax.scatter(x[flag & labels], y[flag & labels], s=28, marker="x", color=RED, label="Keyhole")
            ax.set_title(f"Lowest-distance q{q} ({int(flag.sum())} rows)")
            ax.set_xlabel(FEATURE_LABELS[left])
            ax.grid(alpha=0.2)
        axes[0].set_ylabel(FEATURE_LABELS[right])
        axes[-1].legend(fontsize=7.5)
        recorder.save(
            fig,
            slug=f"empirical_boundary_q10_q20_q30_{left}_{right}_projection",
            title=f"Empirical q10/q20/q30 boundary subsets in the {left}–{right} projection",
            question="Where do model-independent opposite-label-near observations appear in this 2D projection?",
            sources=["empirical_boundary_reference.csv"],
            population=f"{len(frame):,} primary-common simulations",
            units=f"{FEATURE_UNITS[left]}; {FEATURE_UNITS[right]}",
            status="full-label offline evaluation reference only",
            caveat="membership is computed in standardized 4D, so apparent 2D overlap or separation can be misleading; q20/q30 are primary and q10 is noisy",
        )

    _attempt(recorder, "empirical_boundary_q10_q20_q30_P_VX_projection", lambda: boundary_projection(("P", "VX")))
    _attempt(recorder, "empirical_boundary_q10_q20_q30_P_LS_projection", lambda: boundary_projection(("P", "LS")))

    def boundary_mixing_relationship() -> None:
        frame = _artifact(normalized, "empirical_boundary_reference")
        distance = pd.to_numeric(frame[_find_column(frame, "empirical_boundary_distance")], errors="coerce")
        entropy = pd.to_numeric(frame[_find_column(frame, "knn_label_entropy_bits")], errors="coerce")
        opposite = pd.to_numeric(frame[_find_column(frame, "knn_opposite_fraction")], errors="coerce")
        labels = _label_series(frame)
        finite = np.isfinite(distance) & np.isfinite(entropy) & np.isfinite(opposite)
        fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
        axes[0].scatter(distance[finite & ~labels], entropy[finite & ~labels], s=18, alpha=0.5, color=BLUE)
        axes[0].scatter(distance[finite & labels], entropy[finite & labels], s=21, alpha=0.6, color=RED)
        axes[0].set_xlabel("Nearest opposite-label distance")
        axes[0].set_ylabel("kNN label entropy (bits)")
        axes[1].scatter(distance[finite & ~labels], opposite[finite & ~labels], s=18, alpha=0.5, color=BLUE, label="Conduction")
        axes[1].scatter(distance[finite & labels], opposite[finite & labels], s=21, alpha=0.6, color=RED, label="Keyhole")
        axes[1].set_xlabel("Nearest opposite-label distance")
        axes[1].set_ylabel("kNN opposite-label fraction")
        for ax in axes:
            ax.grid(alpha=0.2)
        axes[1].legend(fontsize=8)
        recorder.save(
            fig,
            slug="empirical_boundary_distance_vs_local_label_mixing",
            title="Primary boundary distance versus secondary local-label mixing",
            question="Do two model-independent boundary-proximity diagnostics tell a compatible story?",
            sources=["empirical_boundary_reference.csv"],
            population=f"{int(finite.sum()):,} finite primary-common simulations",
            units="standardized 4D distance; entropy bits; fraction",
            status="full-label offline evaluation robustness diagnostic",
            caveat="both diagnostics use full manual labels and are prohibited from acquisition; local mixing depends on the declared k",
        )

    _attempt(recorder, "empirical_boundary_distance_vs_local_label_mixing", boundary_mixing_relationship)

    def boundary_entropy_projection() -> None:
        frame = _artifact(normalized, "empirical_boundary_reference")
        x = pd.to_numeric(frame[_find_column(frame, "VX")], errors="coerce")
        y = pd.to_numeric(frame[_find_column(frame, "LS")], errors="coerce") * 1e6
        entropy = pd.to_numeric(frame[_find_column(frame, "knn_label_entropy_bits")], errors="coerce")
        finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(entropy)
        fig, ax = plt.subplots(figsize=(8.2, 5.5))
        scatter = ax.scatter(x[finite], y[finite], c=entropy[finite], cmap="magma", s=25, alpha=0.75)
        fig.colorbar(scatter, ax=ax, label="kNN label entropy (bits)")
        ax.set_xlabel("VX (m/s)")
        ax.set_ylabel("LS (µm)")
        ax.grid(alpha=0.2)
        recorder.save(
            fig,
            slug="empirical_boundary_local_mixing_VX_LS_projection",
            title="Local manual-label mixing in the VX–LS projection",
            question="Where are locally mixed labels observed in one diagnostic projection?",
            sources=["empirical_boundary_reference.csv"],
            population=f"{int(finite.sum()):,} primary-common simulations",
            units="VX m/s; LS µm; entropy bits",
            status="full-label offline evaluation robustness diagnostic",
            caveat="entropy is computed in 4D and only projected here; it is not an acquisition score",
        )

    _attempt(recorder, "empirical_boundary_local_mixing_VX_LS_projection", boundary_entropy_projection)

    def outer_label_balance() -> None:
        frame = _artifact(normalized, "outer_split_balance_audit")
        benchmark_col = _find_column(
            frame, "benchmark_population", "population", "benchmark", required=False
        )
        if benchmark_col is not None:
            frame = frame[
                frame[benchmark_col].astype(str).str.casefold().eq("primary_common")
            ].copy()
        role_col = _find_column(frame, "role")
        partition_col = _find_column(frame, "partition")
        run_col = _find_column(frame, "run_id")
        fraction_col = _find_column(frame, "keyhole_fraction")
        subset = frame[
            frame[role_col].astype(str).eq("untouched_test")
            & frame[partition_col].astype(str).eq("all")
        ].copy()
        subset["_fraction"] = pd.to_numeric(subset[fraction_col], errors="coerce")
        subset = subset.sort_values(run_col)
        _require(len(subset) > 0, "No untouched-test all-partition split rows")
        fig, ax = plt.subplots(figsize=(12, 5.3))
        positions = np.arange(len(subset))
        ax.bar(positions, subset["_fraction"], color=PURPLE, alpha=0.8)
        ax.axhline(subset["_fraction"].mean(), color="black", ls="--", label="mean across runs")
        ax.set_xticks(positions, subset[run_col], rotation=60, ha="right", fontsize=7)
        ax.set_ylabel("Held-out Keyhole fraction")
        ax.set_ylim(0, max(0.25, float(subset["_fraction"].max()) * 1.2))
        ax.grid(axis="y", alpha=0.2)
        ax.legend(fontsize=8)
        recorder.save(
            fig,
            slug="outer_split_heldout_label_balance",
            title="Manual-label balance across the 20 untouched test folds",
            question="Did repeated stratification preserve a usable class balance in every held-out run?",
            sources=["outer_split_balance_audit.csv"],
            population="20 primary-common untouched test folds",
            units="Keyhole fraction",
            status="predeclared held-out split audit",
            caveat="repeated-CV test sets overlap across repeats; this chart verifies design rather than independent sample size",
        )

    _attempt(recorder, "outer_split_heldout_label_balance", outer_label_balance)

    def outer_partition_balance() -> None:
        frame = _artifact(normalized, "outer_split_balance_audit")
        benchmark_col = _find_column(
            frame, "benchmark_population", "population", "benchmark", required=False
        )
        if benchmark_col is not None:
            frame = frame[
                frame[benchmark_col].astype(str).str.casefold().eq("primary_common")
            ].copy()
        role_col = _find_column(frame, "role")
        partition_col = _find_column(frame, "partition")
        run_col = _find_column(frame, "run_id")
        count_col = _find_column(frame, "row_count")
        subset = frame[
            frame[role_col].astype(str).eq("untouched_test")
            & ~frame[partition_col].astype(str).eq("all")
        ].copy()
        pivot = subset.pivot(index=run_col, columns=partition_col, values=count_col).fillna(0).sort_index()
        _require(len(pivot) > 0, "No untouched-test partition rows")
        fig, ax = plt.subplots(figsize=(12, 5.7))
        bottom = np.zeros(len(pivot))
        colors = [TEAL, BLUE, ORANGE, PURPLE]
        for color, partition in zip(colors, pivot.columns):
            values = pd.to_numeric(pivot[partition], errors="coerce").fillna(0).to_numpy(float)
            ax.bar(np.arange(len(pivot)), values, bottom=bottom, label=partition, color=color, alpha=0.8)
            bottom += values
        ax.set_xticks(np.arange(len(pivot)), pivot.index, rotation=60, ha="right", fontsize=7)
        ax.set_ylabel("Held-out simulations")
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.2)
        recorder.save(
            fig,
            slug="outer_split_heldout_partition_balance",
            title="Source-partition composition of the 20 untouched test folds",
            question="Are major source partitions represented across held-out runs without forcing impossible partition-by-label strata?",
            sources=["outer_split_balance_audit.csv"],
            population="20 primary-common untouched test folds",
            units="simulation count",
            status="predeclared held-out split audit",
            caveat="stratification is by manual label; partition balance is audited rather than guaranteed exactly",
        )

    _attempt(recorder, "outer_split_heldout_partition_balance", outer_partition_balance)

    def fairness_dashboard() -> None:
        frame = _artifact(normalized, "fairness_audit")
        bool_columns = [
            column
            for column in frame.columns
            if pd.api.types.is_bool_dtype(frame[column])
            or frame[column].astype(str).str.casefold().isin({"true", "false"}).all()
        ]
        bool_columns = [column for column in bool_columns if column not in {"query_local_response_scaler"}]
        _require(bool_columns, "No fairness boolean checks")
        pass_rates = [_bool_values(frame[column]).mean() for column in bool_columns]
        fig, ax = plt.subplots(figsize=(11, 6.2))
        positions = np.arange(len(bool_columns))
        ax.barh(positions, pass_rates, color=np.where(np.asarray(pass_rates) == 1.0, TEAL, RED))
        ax.set_yticks(positions, [_method_label(value) for value in bool_columns], fontsize=8)
        ax.invert_yaxis()
        ax.set_xlim(0, 1.02)
        ax.set_xlabel("Fraction of method/run rows passing")
        ax.grid(axis="x", alpha=0.2)
        recorder.save(
            fig,
            slug="active_learning_fairness_and_leakage_audit",
            title="Matched-design and leakage audit across active-learning arms",
            question="Did every saved active arm respect the common split, warm start, hidden-information, and test-set rules?",
            sources=["fairness_audit.csv"],
            population=f"{len(frame):,} saved run/method audit rows",
            units="pass fraction",
            status="protocol validation; no performance inference",
            caveat="a passing design audit is necessary but does not establish model quality or a winning formulation",
        )

    _attempt(recorder, "active_learning_fairness_and_leakage_audit", fairness_dashboard)

    # ------------------------------------------------------------------
    # Static held-out models and probability calibration.
    # ------------------------------------------------------------------
    static = None
    try:
        static = _artifact(normalized, "static_model_summary")
        benchmark_col = _find_column(
            static, "benchmark_population", "population", "benchmark", required=False
        )
        if benchmark_col is not None:
            static = static[
                static[benchmark_col].astype(str).str.casefold().eq("primary_common")
            ].copy()
    except ReportingDataError:
        static = None
    if static is not None:
        for metric, slug, title, units, question, caveat in (
            (
                "balanced_accuracy",
                "static_model_heldout_balanced_accuracy",
                "Static held-out balanced accuracy by model",
                "balanced accuracy",
                "Which predeclared static Binary and Max-Depth models predict unseen manual labels best?",
                "this is global held-out classification agreement; it is not active sample efficiency",
            ),
            (
                "roc_auc",
                "static_model_heldout_roc_auc",
                "Static held-out ROC AUC by model",
                "ROC AUC",
                "Which static formulation ranks held-out Keyhole cases most effectively?",
                "ROC AUC is global and prevalence-insensitive; it is insufficient evidence for a boundary formulation",
            ),
            (
                "average_precision",
                "static_model_heldout_average_precision",
                "Static held-out average precision by model",
                "average precision",
                "How well do static models rank the rarer Keyhole class under observed prevalence?",
                "average precision depends on prevalence and remains a global rather than boundary-specific metric",
            ),
            (
                "rmse",
                "static_max_depth_regression_rmse",
                "Static held-out maximum-depth regression RMSE",
                "RMSE (µm)",
                "How accurately can maximum depth itself be predicted from P,VX,LS,ST?",
                "regression accuracy does not guarantee correct threshold-side classification near the manual boundary",
            ),
            (
                "r2",
                "static_max_depth_regression_r2",
                "Static held-out maximum-depth regression R²",
                "R²",
                "How much held-out maximum-depth variation do the continuous models explain?",
                "R² is a global regression measure and may be dominated by regions far from the regime boundary",
            ),
        ):
            _attempt(
                recorder,
                slug,
                lambda metric=metric, slug=slug, title=title, units=units, question=question, caveat=caveat: _save_static_metric(
                    recorder,
                    static,
                    metric,
                    slug=slug,
                    title=title,
                    units=units,
                    question=question,
                    caveat=caveat,
                ),
            )

    def static_boundary_metrics() -> None:
        frame = _benchmark_rows(
            _artifact(normalized, "static_boundary_metric_summary"), "primary_common"
        )
        model_col = _find_column(frame, "model")
        subset_col = _find_column(frame, "boundary_subset")
        error_col = _find_column(frame, "mean_error")
        formulation_col = _find_column(frame, "formulation")
        subset = frame[frame[subset_col].astype(str).isin(["q20", "q30"])].copy()
        _require(len(subset) > 0, "No q20/q30 static boundary rows")
        labels = sorted(subset[model_col].astype(str).unique())
        fig, ax = plt.subplots(figsize=(12, 5.8))
        positions = np.arange(len(labels))
        width = 0.35
        for offset, boundary_subset, color in ((-width / 2, "q20", PURPLE), (width / 2, "q30", TEAL)):
            values = []
            for model in labels:
                rows = subset[
                    subset[model_col].astype(str).eq(model)
                    & subset[subset_col].astype(str).eq(boundary_subset)
                ]
                values.append(float(pd.to_numeric(rows[error_col], errors="coerce").mean()) if len(rows) else math.nan)
            ax.bar(positions + offset, values, width, label=boundary_subset, color=color, alpha=0.8)
        ax.set_xticks(positions, [_method_label(value) for value in labels], rotation=28, ha="right")
        ax.set_ylabel("Held-out boundary error")
        ax.grid(axis="y", alpha=0.2)
        ax.legend()
        recorder.save(
            fig,
            slug="static_boundary_specific_q20_q30_performance",
            title="Static held-out error on empirical q20 and q30 boundary subsets",
            question="Which static formulation is most accurate near observed opposite-label transitions?",
            sources=["static_boundary_metric_summary.csv"],
            population="test-local q20/q30 subsets across 20 matched held-out folds",
            units="misclassification fraction",
            status="held-out boundary-specific evaluation",
            caveat="boundary subsets use full-label offline evaluation only and never enter model fitting; q10 is intentionally secondary/noisy",
        )

    _attempt(recorder, "static_boundary_specific_q20_q30_performance", static_boundary_metrics)

    _attempt(
        recorder,
        "continuous_probability_calibration",
        lambda: _save_calibration(
            recorder,
            _benchmark_rows(
                _artifact(normalized, "static_probability_calibration"), "primary_common"
            ),
            "max_depth",
            slug="continuous_probability_calibration",
            title="Held-out Gaussian-tail probability calibration for Max-Depth models",
        ),
    )
    _attempt(
        recorder,
        "binary_probability_calibration",
        lambda: _save_calibration(
            recorder,
            _benchmark_rows(
                _artifact(normalized, "static_probability_calibration"), "primary_common"
            ),
            "binary",
            slug="binary_probability_calibration",
            title="Held-out probability calibration for Binary models",
        ),
    )

    # ------------------------------------------------------------------
    # Warm start, active-learning curves, threshold learning, and AULC.
    # ------------------------------------------------------------------
    def warm_start_classes() -> None:
        frame = _artifact(normalized, "active_initialization_audit")
        run_col = _find_column(frame, "run_id")
        positive_col = _find_column(frame, "positive_count", "keyhole_count")
        negative_col = _find_column(frame, "negative_count", "non_keyhole_count")
        # Initialization rows may be repeated by method; identical run rows are
        # collapsed only after exact consistency is checked.
        grouped = frame.groupby(run_col, sort=True)
        rows = []
        for run_id, group in grouped:
            positives = pd.to_numeric(group[positive_col], errors="coerce").dropna().unique()
            negatives = pd.to_numeric(group[negative_col], errors="coerce").dropna().unique()
            _require(len(positives) == 1 and len(negatives) == 1, f"Warm-start counts disagree within {run_id}")
            rows.append((str(run_id), float(positives[0]), float(negatives[0])))
        summary = pd.DataFrame(rows, columns=["run_id", "positive", "negative"])
        fig, ax = plt.subplots(figsize=(12, 5.5))
        positions = np.arange(len(summary))
        ax.bar(positions, summary["negative"], color=BLUE, label="Conduction discovered")
        ax.bar(positions, summary["positive"], bottom=summary["negative"], color=RED, label="Keyhole discovered")
        ax.set_xticks(positions, summary["run_id"], rotation=60, ha="right", fontsize=7)
        ax.set_ylabel("Sequential warm-start queries")
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.2)
        recorder.save(
            fig,
            slug="warm_start_class_composition",
            title="Shared warm-start class composition across matched runs",
            question="How many manual positives and negatives were discovered before active acquisition began?",
            sources=["active_initialization_audit.csv"],
            population="one shared initialization per matched outer run",
            units="simulator-query count",
            status="query-sequential training protocol audit",
            caveat="the predetermined permutation is label-blind; only already revealed labels may trigger the both-class stopping rule",
        )

    _attempt(recorder, "warm_start_class_composition", warm_start_classes)

    def warm_start_budget() -> None:
        frame = _artifact(normalized, "active_initialization_audit")
        run_col = _find_column(frame, "run_id")
        budget_col = _find_column(frame, "effective_warm_start")
        nominal_col = _find_column(frame, "nominal_warm_start", required=False)
        values = []
        names = []
        for run_id, group in frame.groupby(run_col, sort=True):
            unique = pd.to_numeric(group[budget_col], errors="coerce").dropna().unique()
            _require(len(unique) == 1, f"Effective warm start differs across methods in {run_id}")
            names.append(str(run_id))
            values.append(float(unique[0]))
        nominal = (
            float(pd.to_numeric(frame[nominal_col], errors="coerce").dropna().iloc[0])
            if nominal_col is not None
            else 12.0
        )
        fig, ax = plt.subplots(figsize=(12, 5.2))
        positions = np.arange(len(values))
        ax.bar(positions, values, color=np.where(np.asarray(values) > nominal, ORANGE, TEAL))
        ax.axhline(nominal, color="black", ls="--", label=f"nominal n0={nominal:g}")
        ax.set_xticks(positions, names, rotation=60, ha="right", fontsize=7)
        ax.set_ylabel("Effective warm-start queries")
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.2)
        recorder.save(
            fig,
            slug="warm_start_effective_budget",
            title="Nominal versus effective shared warm-start budget",
            question="How often did sequential random querying need to continue beyond n0 to reveal both classes?",
            sources=["active_initialization_audit.csv"],
            population="one shared initialization per matched outer run",
            units="simulator-query count",
            status="query-sequential training protocol audit",
            caveat="every extra reveal is counted as a simulator query and is shared identically by all methods within a run",
        )

    _attempt(recorder, "warm_start_effective_budget", warm_start_budget)

    curves = None
    try:
        curves = _artifact(normalized, "active_learning_curve_summary")
        benchmark_col = _find_column(
            curves, "benchmark_population", "population", "benchmark", required=False
        )
        if benchmark_col is not None:
            curves = curves[
                curves[benchmark_col].astype(str).str.casefold().eq("primary_common")
            ].copy()
    except ReportingDataError:
        curves = None
    if curves is not None:
        for metric, slug, title, label, question, caveat in (
            (
                "q20_error",
                "q20_active_learning_curves",
                "Active-learning error on held-out empirical q20 boundary points",
                "q20 misclassification fraction",
                "Which formulation/acquisition reduces primary near-boundary error fastest?",
                "q20 is computed only on each untouched test fold; shaded bands summarize repeated-CV variability",
            ),
            (
                "q30_error",
                "q30_active_learning_curves",
                "Active-learning error on held-out empirical q30 boundary points",
                "q30 misclassification fraction",
                "Does the q20 ranking persist in the broader primary boundary region?",
                "q30 is boundary-specific but broader than q20; repeated-CV runs are matched rather than independent",
            ),
            (
                "balanced_accuracy",
                "balanced_accuracy_learning_curves",
                "Global held-out balanced-accuracy learning curves",
                "balanced accuracy",
                "How quickly do methods learn the global manual-label classification task?",
                "global performance can hide errors concentrated near the regime transition",
            ),
            (
                "roc_auc",
                "roc_auc_learning_curves",
                "Held-out ROC AUC learning curves",
                "ROC AUC",
                "How rapidly do active models learn a useful ranking of held-out manual labels?",
                "ROC AUC is a global ranking metric and a single strong value cannot decide the boundary formulation",
            ),
            (
                "average_precision",
                "average_precision_learning_curves",
                "Held-out average-precision learning curves",
                "average precision",
                "How sample-efficiently do methods rank the rarer Keyhole class?",
                "average precision depends on prevalence and is not itself a boundary-distance metric",
            ),
            (
                "brier_score",
                "brier_score_learning_curves",
                "Held-out Brier-score learning curves",
                "Brier score",
                "How quickly do probabilistic predictions become accurate?",
                "Max-Depth Gaussian-tail probabilities inherit a training-only point-threshold approximation; lower is better",
            ),
        ):
            _attempt(
                recorder,
                slug,
                lambda metric=metric, slug=slug, title=title, label=label, question=question, caveat=caveat: _save_active_curve(
                    recorder,
                    curves,
                    metric,
                    slug=slug,
                    title=title,
                    y_label=label,
                    question=question,
                    caveat=caveat,
                ),
            )

    def query_distance_by_order() -> None:
        frame = _benchmark_rows(
            _artifact(normalized, "active_query_history"), "primary_common"
        )
        method_col = _find_column(frame, "method")
        order_col = _find_column(frame, "query_order")
        distance_col = _find_column(
            frame, "empirical_boundary_distance_evaluation_only", "empirical_boundary_distance"
        )
        work = frame.copy()
        work["_order"] = pd.to_numeric(work[order_col], errors="coerce")
        work["_distance"] = pd.to_numeric(work[distance_col], errors="coerce")
        summary = work.groupby([method_col, "_order"], as_index=False)["_distance"].agg(["mean", "std"]).reset_index()
        _require(len(summary) > 0, "No query-boundary distance history")
        fig, ax = plt.subplots(figsize=(11, 5.7))
        for method, group in summary.groupby(method_col, sort=True):
            group = group.sort_values("_order")
            ax.plot(group["_order"], group["mean"], lw=1.6, label=_method_label(method), color=_method_color(method))
        ax.set_xlabel("Query order")
        ax.set_ylabel("Mean true opposite-label distance (standardized 4D)")
        ax.grid(alpha=0.2)
        ax.legend(fontsize=7.2, ncol=2)
        recorder.save(
            fig,
            slug="acquired_true_boundary_distance_curves",
            title="True empirical boundary distance of acquired points",
            question="Do active methods query nearer observed manual-label transitions than their shared random baselines?",
            sources=["active_query_history.csv"],
            population="queried training-pool simulations across matched runs",
            units="standardized 4D opposite-label distance; query count",
            status="post-selection evaluation-only acquisition diagnostic",
            caveat="the full-label distance is joined only after selection and must never enter acquisition; smaller does not by itself prove better prediction",
        )

    _attempt(recorder, "acquired_true_boundary_distance_curves", query_distance_by_order)

    def query_distance_summary() -> None:
        frame = _benchmark_rows(
            _artifact(normalized, "query_boundary_distance_summary"), "primary_common"
        )
        method_col = _find_column(frame, "method")
        value_col = _find_column(
            frame,
            "mean_query_boundary_distance",
            "median_query_boundary_distance",
            "mean_empirical_boundary_distance",
        )
        work = frame.assign(_value=pd.to_numeric(frame[value_col], errors="coerce"))
        methods = sorted(work[method_col].astype(str).unique())
        data = [work.loc[work[method_col].astype(str).eq(method), "_value"].dropna() for method in methods]
        _require(all(len(values) for values in data), "Missing method query-distance summaries")
        fig, ax = plt.subplots(figsize=(12, 5.6))
        ax.boxplot(data, tick_labels=[_method_label(value) for value in methods], showfliers=False)
        ax.set_ylabel("Run-level mean acquired boundary distance")
        ax.tick_params(axis="x", rotation=28)
        ax.grid(axis="y", alpha=0.2)
        recorder.save(
            fig,
            slug="query_boundary_distance_method_summary",
            title="Run-to-run distribution of acquired boundary proximity",
            question="Which methods systematically acquire points nearer empirical manual-label transitions?",
            sources=["query_boundary_distance_summary.csv"],
            population="matched active-learning runs on primary common candidate pools",
            units="standardized 4D opposite-label distance",
            status="post-selection evaluation-only acquisition diagnostic",
            caveat="the boundary score is forbidden from acquisition and this diagnostic cannot establish causal acquisition quality",
        )

    _attempt(recorder, "query_boundary_distance_method_summary", query_distance_summary)

    _attempt(
        recorder,
        "max_depth_threshold_trajectories",
        lambda: _save_threshold_trajectories(
            recorder,
            _benchmark_rows(
                _artifact(normalized, "online_threshold_history"), "primary_common"
            ),
            "max_depth",
            slug="max_depth_threshold_trajectories",
            title="Queried-only maximum-depth threshold trajectories",
            source="online_threshold_history.csv",
        ),
    )
    _attempt(
        recorder,
        "g3_threshold_trajectories",
        lambda: _save_threshold_trajectories(
            recorder,
            _benchmark_rows(
                _artifact(normalized, "online_threshold_history"), "secondary_g3_common"
            ),
            "g3",
            slug="g3_threshold_trajectories",
            title="Queried-only G3 threshold trajectories",
            source="online_threshold_history.csv",
        ),
    )

    def threshold_bootstrap_width() -> None:
        frame = _artifact(normalized, "online_threshold_bootstrap_summary")
        formulation_col = _find_column(frame, "formulation")
        method_col = _find_column(frame, "method")
        budget_col = _find_column(frame, "budget")
        low_col = _find_column(frame, "ci_low")
        high_col = _find_column(frame, "ci_high")
        work = frame.copy()
        work["_budget"] = pd.to_numeric(work[budget_col], errors="coerce")
        work["_width"] = pd.to_numeric(work[high_col], errors="coerce") - pd.to_numeric(work[low_col], errors="coerce")
        work = work[np.isfinite(work["_budget"]) & np.isfinite(work["_width"])]
        _require(len(work) > 0, "No valid threshold-bootstrap intervals")
        fig, ax = plt.subplots(figsize=(11, 5.6))
        for (formulation, method), group in work.groupby([formulation_col, method_col], sort=True):
            summary = group.groupby("_budget")["_width"].median().sort_index()
            ax.plot(summary.index, summary.values, marker="o", ms=4, label=_method_label(method), color=_method_color(method, formulation))
        ax.set_xlabel("Simulator queries")
        ax.set_ylabel("Median 95% bootstrap interval width (µm)")
        ax.grid(alpha=0.2)
        ax.legend(fontsize=7.2, ncol=2)
        recorder.save(
            fig,
            slug="online_threshold_bootstrap_uncertainty",
            title="Selected-set threshold bootstrap uncertainty",
            question="How quickly does diagnostic uncertainty in the queried-only scalar threshold contract?",
            sources=["online_threshold_bootstrap_summary.csv"],
            population="primary 405-row Max-Depth runs plus explicitly secondary 404-row G3-common diagnostics",
            units="threshold interval width µm; query count",
            status="query-only bootstrap diagnostic; not acquisition input",
            caveat="primary and secondary populations are not pooled for inference; selected-set intervals condition on adaptively queried points and are descriptive rather than formal confidence intervals",
        )

    _attempt(recorder, "online_threshold_bootstrap_uncertainty", threshold_bootstrap_width)

    aulc = None
    try:
        aulc = _artifact(normalized, "active_learning_aulc_summary")
        benchmark_col = _find_column(
            aulc, "benchmark_population", "population", "benchmark", required=False
        )
        if benchmark_col is not None:
            aulc = aulc[
                aulc[benchmark_col].astype(str).str.casefold().eq("primary_common")
            ].copy()
    except ReportingDataError:
        aulc = None
    if aulc is not None:
        for metric, slug, title, label, question, lower in (
            (
                "common_normalized_aulc__q20_error",
                "q20_aulc_comparison",
                "Primary q20 error AULC comparison",
                "Normalized q20 error AULC",
                "Which method has the best matched q20 sample efficiency?",
                True,
            ),
            (
                "common_normalized_aulc__q30_error",
                "q30_aulc_comparison",
                "Primary q30 error AULC comparison",
                "Normalized q30 error AULC",
                "Does the sample-efficiency ranking persist for the broader q30 boundary set?",
                True,
            ),
            (
                "common_normalized_aulc__balanced_accuracy",
                "balanced_accuracy_aulc_comparison",
                "Global balanced-accuracy AULC comparison",
                "Normalized balanced-accuracy AULC",
                "Which method accumulates the strongest global held-out accuracy over the common budget range?",
                False,
            ),
        ):
            _attempt(
                recorder,
                slug,
                lambda metric=metric, slug=slug, title=title, label=label, question=question, lower=lower: _save_aulc_distribution(
                    recorder,
                    aulc,
                    metric,
                    slug=slug,
                    title=title,
                    y_label=label,
                    question=question,
                    lower_is_better=lower,
                ),
            )

    def aulc_run_variability() -> None:
        frame = _artifact(normalized, "active_learning_aulc_summary")
        benchmark_col = _find_column(
            frame, "benchmark_population", "population", "benchmark", required=False
        )
        if benchmark_col is not None:
            frame = frame[
                frame[benchmark_col].astype(str).str.casefold().eq("primary_common")
            ].copy()
        run_col = _find_column(frame, "run_id")
        method_col = _find_column(frame, "method")
        value_col = _find_column(frame, "common_normalized_aulc__q20_error")
        pivot = frame.pivot(index=run_col, columns=method_col, values=value_col).sort_index()
        _require(pivot.size > 0, "No q20 AULC run matrix")
        fig, ax = plt.subplots(figsize=(12, 7.0))
        image = ax.imshow(pivot.to_numpy(float), aspect="auto", cmap="YlOrRd", interpolation="nearest")
        ax.set_xticks(np.arange(len(pivot.columns)), [_method_label(value) for value in pivot.columns], rotation=35, ha="right", fontsize=8)
        ax.set_yticks(np.arange(len(pivot.index)), pivot.index, fontsize=7)
        fig.colorbar(image, ax=ax, label="q20 error AULC (lower better)")
        recorder.save(
            fig,
            slug="q20_aulc_run_to_run_variability",
            title="Matched run-to-run variability in q20 error AULC",
            question="Are apparent method advantages stable across the same twenty outer splits?",
            sources=["active_learning_aulc_summary.csv"],
            population="20 matched primary-common outer runs",
            units="normalized q20 error AULC",
            status="held-out active-learning run diagnostic",
            caveat="color comparisons should be made within rows because methods share each run; repeats are not independent experiments",
        )

    _attempt(recorder, "q20_aulc_run_to_run_variability", aulc_run_variability)

    def queries_to_tolerance() -> None:
        frame = _benchmark_rows(
            _artifact(normalized, "queries_to_tolerance"), "primary_common"
        )
        method_col = _find_column(frame, "method")
        metric_col = _find_column(frame, "metric")
        target_col = _find_column(frame, "target")
        queries_col = _find_column(frame, "queries_required")
        status_col = _find_column(frame, "status")
        preferred = frame[
            frame[metric_col].astype(str).eq("q20_error")
            & np.isclose(pd.to_numeric(frame[target_col], errors="coerce"), 0.25)
        ].copy()
        if len(preferred) == 0:
            preferred = frame[frame[metric_col].astype(str).eq("q20_error")].copy()
        _require(len(preferred) > 0, "No q20 queries-to-tolerance rows")
        preferred["_queries"] = pd.to_numeric(preferred[queries_col], errors="coerce")
        summary = preferred.groupby(method_col)["_queries"].agg(["median", "count"]).sort_values("median")
        methods = list(summary.index)
        reached_fraction = [
            preferred.loc[preferred[method_col].astype(str).eq(str(method)), status_col].astype(str).str.casefold().eq("reached").mean()
            for method in methods
        ]
        fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
        axes[0].bar(np.arange(len(methods)), summary["median"], color=[_method_color(value) for value in methods])
        axes[0].set_xticks(np.arange(len(methods)), [_method_label(value) for value in methods], rotation=30, ha="right")
        axes[0].set_ylabel("Median queries among reached runs")
        axes[0].grid(axis="y", alpha=0.2)
        axes[1].bar(np.arange(len(methods)), reached_fraction, color=[_method_color(value) for value in methods])
        axes[1].set_xticks(np.arange(len(methods)), [_method_label(value) for value in methods], rotation=30, ha="right")
        axes[1].set_ylabel("Fraction of runs reaching tolerance")
        axes[1].set_ylim(0, 1.02)
        axes[1].grid(axis="y", alpha=0.2)
        recorder.save(
            fig,
            slug="queries_to_tolerance_comparison",
            title="Queries required to reach q20 error tolerance",
            question="Which methods reach useful boundary error with fewer simulator queries, and how often?",
            sources=["queries_to_tolerance.csv"],
            population="20 matched primary-common outer runs",
            units="simulator queries; reached-run fraction",
            status="held-out active-learning time-to-target summary",
            caveat="unreached runs are not extrapolated or assigned an artificial query count; median queries alone must be read with reach fraction",
        )

    _attempt(recorder, "queries_to_tolerance_comparison", queries_to_tolerance)

    # ------------------------------------------------------------------
    # Subgroups, domain shift, the G3 comparator, and decision evidence.
    # ------------------------------------------------------------------
    def subgroup_sensitivity(subgroup: str, slug: str, title: str) -> None:
        frame = _artifact(normalized, "subgroup_transient_persistent_results")
        subgroup_col = _find_column(frame, "subgroup")
        method_col = _find_column(frame, "method")
        sensitivity_col = _find_column(frame, "sensitivity")
        formulation_col = _find_column(frame, "formulation")
        subset = frame[frame[subgroup_col].astype(str).eq(subgroup)].copy()
        subset["_sensitivity"] = pd.to_numeric(subset[sensitivity_col], errors="coerce")
        subset = subset[np.isfinite(subset["_sensitivity"])]
        _require(len(subset) > 0, f"No interpretable subgroup rows for {subgroup}")
        summary = subset.groupby([method_col, formulation_col], as_index=False)["_sensitivity"].agg(["mean", "std"]).reset_index()
        methods = summary[method_col].astype(str).tolist()
        fig, ax = plt.subplots(figsize=(11, 5.4))
        positions = np.arange(len(summary))
        colors = [_method_color(method, formulation) for method, formulation in zip(summary[method_col], summary[formulation_col])]
        ax.bar(positions, summary["mean"], yerr=summary["std"].fillna(0), capsize=3, color=colors, alpha=0.8)
        ax.set_xticks(positions, [_method_label(value) for value in methods], rotation=28, ha="right")
        ax.set_ylabel("Held-out subgroup sensitivity")
        ax.set_ylim(0, 1.02)
        ax.grid(axis="y", alpha=0.2)
        recorder.save(
            fig,
            slug=slug,
            title=title,
            question=f"Which formulation retains sensitivity for held-out {subgroup.replace('_', ' ')} cases?",
            sources=["subgroup_transient_persistent_results.csv"],
            population=f"held-out manual-positive {subgroup.replace('_', ' ')} cases at final budget",
            units="sensitivity fraction",
            status="held-out final-budget subgroup diagnostic",
            caveat="small subgroup counts are reported per run and rows below the predeclared minimum n must not drive a strong conclusion",
        )

    for subgroup, slug, title in (
        ("transient_Keyhole", "transient_keyhole_sensitivity", "Final-budget sensitivity for transient Keyhole cases"),
        ("persistent_Keyhole", "persistent_keyhole_sensitivity", "Final-budget sensitivity for persistent Keyhole cases"),
        ("repeated_Keyhole", "repeated_keyhole_sensitivity", "Final-budget sensitivity for repeated-Keyhole cases"),
    ):
        _attempt(
            recorder,
            slug,
            lambda subgroup=subgroup, slug=slug, title=title: subgroup_sensitivity(subgroup, slug, title),
        )

    def t0_subgroups() -> None:
        frame = _artifact(normalized, "subgroup_t0_timing_results")
        timing_col = _find_column(frame, "timing_group")
        method_col = _find_column(frame, "method")
        sensitivity_col = _find_column(frame, "sensitivity")
        formulation_col = _find_column(frame, "formulation")
        work = frame.assign(_sensitivity=pd.to_numeric(frame[sensitivity_col], errors="coerce"))
        summary = work.groupby([timing_col, formulation_col], as_index=False)["_sensitivity"].mean()
        pivot = summary.pivot(index=timing_col, columns=formulation_col, values="_sensitivity")
        _require(pivot.size > 0, "No T0 timing subgroup values")
        fig, ax = plt.subplots(figsize=(10.5, 6.2))
        image = ax.imshow(pivot.to_numpy(float), vmin=0, vmax=1, cmap="YlGn", aspect="auto")
        ax.set_xticks(np.arange(len(pivot.columns)), [_method_label(value) for value in pivot.columns])
        ax.set_yticks(np.arange(len(pivot.index)), [_method_label(value) for value in pivot.index])
        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                value = pivot.iloc[i, j]
                if pd.notna(value):
                    ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=8)
        fig.colorbar(image, ax=ax, label="Mean held-out sensitivity")
        recorder.save(
            fig,
            slug="keyhole_t0_timing_subgroup_sensitivity",
            title="Final-budget sensitivity by saved-Keyhole timing relative to T0",
            question="Do formulation differences concentrate in specific pre/inside/post-T0 manual-positive subgroups?",
            sources=["subgroup_t0_timing_results.csv"],
            population="held-out manual-positive T0 timing subgroups at final budget",
            units="sensitivity fraction",
            status="held-out final-budget subgroup diagnostic",
            caveat="subgroup sample sizes vary and T0 groups are inherited unchanged; no post-hoc target or label redefinition is allowed",
        )

    _attempt(recorder, "keyhole_t0_timing_subgroup_sensitivity", t0_subgroups)

    def domain_transfer_metric(metric: str, slug: str, title: str, y_label: str) -> None:
        frame = _artifact(normalized, "domain_transfer_model_summary")
        route_col = _find_column(frame, "route")
        formulation_col = _find_column(frame, "formulation")
        value_col = _find_column(frame, metric)
        frame = frame.assign(_value=pd.to_numeric(frame[value_col], errors="coerce"))
        routes = sorted(frame[route_col].astype(str).unique())
        formulations = sorted(frame[formulation_col].astype(str).unique())
        fig, ax = plt.subplots(figsize=(11, 5.8))
        width = 0.8 / max(len(formulations), 1)
        positions = np.arange(len(routes))
        for index, formulation in enumerate(formulations):
            values = []
            for route in routes:
                rows = frame[
                    frame[route_col].astype(str).eq(route)
                    & frame[formulation_col].astype(str).eq(formulation)
                ]
                values.append(float(rows["_value"].mean()) if len(rows) else math.nan)
            ax.bar(
                positions - 0.4 + width / 2 + index * width,
                values,
                width,
                label=_method_label(formulation),
                color=_method_color(formulation),
                alpha=0.82,
            )
        ax.set_xticks(positions, [_method_label(value) for value in routes], rotation=22, ha="right")
        ax.set_ylabel(y_label)
        ax.grid(axis="y", alpha=0.2)
        ax.legend(fontsize=8)
        recorder.save(
            fig,
            slug=slug,
            title=title,
            question="Do source-trained Binary and Max-Depth models remain useful under old/new domain shift?",
            sources=["domain_transfer_model_summary.csv"],
            population="predeclared disjoint source-to-target partition routes",
            units=y_label,
            status="secondary held-out domain-transfer stress test",
            caveat="old-remote has very few Keyhole positives, so route estimates are descriptive and imprecise; transfer does not replace the combined-data benchmark",
        )

    _attempt(
        recorder,
        "domain_transfer_balanced_accuracy",
        lambda: domain_transfer_metric(
            "balanced_accuracy",
            "domain_transfer_balanced_accuracy",
            "Secondary source-to-target balanced accuracy",
            "balanced accuracy",
        ),
    )
    _attempt(
        recorder,
        "domain_transfer_q20_error",
        lambda: domain_transfer_metric(
            "q20_error",
            "domain_transfer_q20_error",
            "Secondary source-to-target q20 boundary error",
            "q20 misclassification fraction",
        ),
    )

    def domain_threshold_shift() -> None:
        frame = _artifact(normalized, "domain_transfer_model_summary")
        formulation_col = _find_column(frame, "formulation")
        route_col = _find_column(frame, "route")
        shift_col = _find_column(frame, "threshold_shift_source_minus_target_oracle_um")
        subset = frame[frame[formulation_col].astype(str).eq("max_depth")].copy()
        subset["_shift"] = pd.to_numeric(subset[shift_col], errors="coerce")
        subset = subset[np.isfinite(subset["_shift"])].sort_values(route_col)
        _require(len(subset) > 0, "No max-depth source/target threshold shifts")
        fig, ax = plt.subplots(figsize=(9.5, 5.4))
        positions = np.arange(len(subset))
        ax.bar(positions, subset["_shift"], color=np.where(subset["_shift"] >= 0, ORANGE, BLUE))
        ax.axhline(0, color="black", lw=1)
        ax.set_xticks(positions, [_method_label(value) for value in subset[route_col]], rotation=22, ha="right")
        ax.set_ylabel("Source tau − target oracle tau (µm)")
        ax.grid(axis="y", alpha=0.2)
        recorder.save(
            fig,
            slug="domain_transfer_max_depth_threshold_shift",
            title="Maximum-depth threshold shift under partition transfer",
            question="How far does the valid source-only threshold lie from the unavailable target oracle reference?",
            sources=["domain_transfer_model_summary.csv"],
            population="predeclared disjoint max-depth transfer routes",
            units="threshold difference µm",
            status="secondary transfer diagnostic with unavailable target oracle",
            caveat="the target oracle is displayed only to quantify shift and is never available to a valid transferred model",
        )

    _attempt(recorder, "domain_transfer_max_depth_threshold_shift", domain_threshold_shift)

    # A G3-specific curve table may use either the same direct curve schema or
    # a long summary schema.  Unsupported schemas are skipped without dummy
    # values.
    for metric, slug, title in (
        ("q20_error", "g3_secondary_q20_active_learning", "Secondary G3 q20 active-learning curves"),
        ("q30_error", "g3_secondary_q30_active_learning", "Secondary G3 q30 active-learning curves"),
    ):
        _attempt(
            recorder,
            slug,
            lambda metric=metric, slug=slug, title=title: _save_active_curve(
                recorder,
                _artifact(normalized, "g3_secondary_active_summary"),
                metric,
                slug=slug,
                title=title,
                y_label=f"{metric.replace('_', ' ')}",
                question="Does G3 add boundary-learning value on the exact three-way common population?",
                caveat="G3 is secondary and uses the separately reported three-way complete population; it cannot redefine the primary narrative",
                source="g3_secondary_active_summary.csv",
            ),
        )

    def max_depth_g3_scorecard() -> None:
        frame = _artifact(normalized, "max_depth_vs_g3_summary")
        candidate_col = _find_column(frame, "candidate", "formulation", "response")
        metric_col = _find_column(frame, "metric")
        value_col = _find_column(frame, "mean", "value", "metric_mean")
        work = frame.copy()
        work["_value"] = pd.to_numeric(work[value_col], errors="coerce")
        pivot = work.pivot_table(index=metric_col, columns=candidate_col, values="_value", aggfunc="mean")
        _require(pivot.size > 0, "No Max-Depth/G3 scorecard values")
        # Normalize each metric row only for visualization; exact values remain
        # printed inside cells and no cross-metric ranking is inferred.
        matrix = pivot.to_numpy(float)
        row_min = np.nanmin(matrix, axis=1, keepdims=True)
        row_range = np.nanmax(matrix, axis=1, keepdims=True) - row_min
        normalized_matrix = np.divide(matrix - row_min, row_range, out=np.zeros_like(matrix), where=row_range > 0)
        fig, ax = plt.subplots(figsize=(9.5, max(5.0, 0.45 * len(pivot))))
        image = ax.imshow(normalized_matrix, aspect="auto", cmap="Blues", vmin=0, vmax=1)
        ax.set_xticks(np.arange(len(pivot.columns)), [_method_label(value) for value in pivot.columns])
        ax.set_yticks(np.arange(len(pivot.index)), [_method_label(value) for value in pivot.index], fontsize=8)
        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                if pd.notna(pivot.iloc[i, j]):
                    ax.text(j, i, f"{pivot.iloc[i, j]:.3g}", ha="center", va="center", fontsize=8)
        fig.colorbar(image, ax=ax, label="within-row normalized display only")
        recorder.save(
            fig,
            slug="max_depth_vs_g3_secondary_scorecard",
            title="Maximum-Depth versus G3 secondary evidence scorecard",
            question="Across stored comparable metrics, what does G3 add after maximum depth is included?",
            sources=["max_depth_vs_g3_summary.csv"],
            population="exact separately documented three-way common population",
            units="metric-specific exact values printed in cells",
            status="held-out/descriptive secondary comparison as declared per source row",
            caveat="row colors encode magnitude, not goodness, and are normalized only within each metric (q-error lower, balanced accuracy higher); neither response is claimed universally physically superior",
        )

    _attempt(recorder, "max_depth_vs_g3_secondary_scorecard", max_depth_g3_scorecard)

    # ------------------------------------------------------------------
    # Supported descriptive boundary surfaces and deterministic trajectories.
    # ------------------------------------------------------------------
    def surface_family(pair: str) -> None:
        surfaces = _artifact(normalized, "boundary_surface_data")
        try:
            population = _artifact(normalized, "primary_common_population")
        except ReportingDataError:
            population = None
        _save_surface_family(recorder, surfaces, population, pair)

    for pair in ("P-VX", "P-LS", "VX-LS"):
        _attempt(recorder, f"{pair}_surface_family", lambda pair=pair: surface_family(pair))

    _attempt(
        recorder,
        "representative_acquisition_trajectories",
        lambda: _save_representative_trajectories(
            recorder,
            _artifact(normalized, "active_learning_aulc_summary"),
            _artifact(normalized, "active_query_history"),
        ),
    )

    def formulation_scorecard() -> None:
        frame = _artifact(normalized, "phase6_formulation_scorecard")
        row_col = _find_column(frame, "criterion", "metric", "evidence", required=False)
        formulation_col = _find_column(frame, "formulation", "candidate", required=False)
        value_col = _find_column(frame, "score", "value", "mean", required=False)
        if row_col is not None and formulation_col is not None and value_col is not None:
            work = frame.assign(_value=pd.to_numeric(frame[value_col], errors="coerce"))
            pivot = work.pivot_table(index=row_col, columns=formulation_col, values="_value", aggfunc="mean")
        else:
            numeric = [column for column in frame.columns if pd.to_numeric(frame[column], errors="coerce").notna().any()]
            _require(numeric, "Formulation scorecard has no plottable numeric evidence")
            identifier = formulation_col or frame.columns[0]
            pivot = frame.set_index(identifier)[numeric].apply(pd.to_numeric, errors="coerce")
        _require(pivot.size > 0, "Empty formulation scorecard matrix")
        matrix = pivot.to_numpy(float)
        fig, ax = plt.subplots(figsize=(9.5, max(5.0, 0.42 * len(pivot))))
        image = ax.imshow(matrix, aspect="auto", cmap="coolwarm")
        ax.set_xticks(np.arange(len(pivot.columns)), [_method_label(value) for value in pivot.columns])
        ax.set_yticks(np.arange(len(pivot.index)), [_method_label(value) for value in pivot.index], fontsize=8)
        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                value = pivot.iloc[i, j]
                if pd.notna(value):
                    ax.text(j, i, f"{value:.3g}", ha="center", va="center", fontsize=8)
        fig.colorbar(image, ax=ax, label="stored score / metric value")
        recorder.save(
            fig,
            slug="phase6_formulation_scorecard",
            title="Phase 6 Binary versus Max-Depth formulation scorecard",
            question="How do the two formulations compare across the predeclared global, boundary, threshold, subgroup, and transfer evidence?",
            sources=["phase6_formulation_scorecard.csv"],
            population="primary common benchmark plus explicitly secondary robustness analyses",
            units="criterion-specific stored values",
            status="evidence synthesis; held-out/descriptive/oracle status inherited per criterion",
            caveat="heterogeneous criteria must not be averaged blindly; the final decision follows the declared evidence rule rather than one attractive metric",
        )

    _attempt(recorder, "phase6_formulation_scorecard", formulation_scorecard)

    def final_decision_figure() -> None:
        frame = _artifact(normalized, "phase6_final_decision")
        _require(len(frame) == 1, f"Expected one final-decision row, found {len(frame)}")
        row = frame.iloc[0]
        decision_col = _find_column(
            frame,
            "final_decision",
            "decision",
            "recommended_formulation",
            "recommended_boundary_formulation",
        )
        decision = str(row[decision_col])
        allowed = {
            "CONTINUOUS MAX-DEPTH PRIMARY",
            "BINARY KEYHOLE PRIMARY",
            "HYBRID / NO CLEAR WINNER",
        }
        _require(decision in allowed, f"Final decision uses undeclared language: {decision!r}")
        evidence_col = _find_column(frame, "justification", "reason", "evidence_summary", required=False)
        evidence = str(row[evidence_col]) if evidence_col is not None else "See the stored formulation scorecard and paired held-out summaries."
        fig, ax = plt.subplots(figsize=(12, 5.8))
        ax.axis("off")
        color = TEAL if decision.startswith("CONTINUOUS") else PURPLE if decision.startswith("BINARY") else ORANGE
        ax.text(0.5, 0.72, decision, ha="center", va="center", fontsize=22, fontweight="bold", color=color, transform=ax.transAxes)
        ax.text(
            0.5,
            0.40,
            "\n".join(textwrap.wrap(evidence, width=110)),
            ha="center",
            va="center",
            fontsize=11,
            transform=ax.transAxes,
        )
        recorder.save(
            fig,
            slug="final_phase6_decision_summary",
            title="Final Phase 6 real-data boundary formulation decision",
            question="What exactly should the thesis carry forward after the matched Phase 6 evidence?",
            sources=["phase6_final_decision.csv", "phase6_formulation_scorecard.csv"],
            population="primary common benchmark with declared secondary robustness evidence",
            units="categorical predeclared decision",
            status="evidence-based Phase 6 synthesis; no Phase 7 claim",
            caveat="the manual annotation remains the reference; no scalar threshold is a universal physical constant and no causal claim is made",
        )

    _attempt(recorder, "final_phase6_decision_summary", final_decision_figure)

    def validation_dashboard() -> None:
        validation = _artifact(normalized, "validation_results")
        requirements = _artifact(normalized, "requirement_checklist")
        status_v = _find_column(validation, "status")
        status_r = _find_column(requirements, "status")
        counts_v = validation[status_v].astype(str).str.upper().value_counts()
        counts_r = requirements[status_r].astype(str).str.upper().value_counts()
        categories = sorted(set(counts_v.index) | set(counts_r.index))
        fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), sharey=True)
        for ax, counts, title in ((axes[0], counts_v, "Automated validations"), (axes[1], counts_r, "Requirements")):
            values = [int(counts.get(category, 0)) for category in categories]
            colors = [TEAL if category == "PASS" else ORANGE if category in {"WARN", "NA"} else RED for category in categories]
            bars = ax.bar(categories, values, color=colors)
            ax.bar_label(bars, padding=3)
            ax.set_title(title)
            ax.grid(axis="y", alpha=0.2)
        axes[0].set_ylabel("Checks")
        recorder.save(
            fig,
            slug="phase6_validation_requirement_dashboard",
            title="Phase 6 validation and requirement dashboard",
            question="Did the saved run satisfy its predeclared leakage, reproducibility, artifact, notebook, and figure requirements?",
            sources=["validation_results.csv", "requirement_checklist.csv"],
            population=f"{len(validation):,} validation checks and {len(requirements):,} requirement rows",
            units="check count",
            status="completion audit; no scientific performance inference",
            caveat="a PASS dashboard verifies implementation consistency, not the truth of a physical interpretation",
        )

    _attempt(recorder, "phase6_validation_requirement_dashboard", validation_dashboard)

    manifest = pd.DataFrame(recorder.rows)
    manifest.attrs["skipped_figures"] = recorder.skipped
    manifest.attrs["created_figure_count"] = len(manifest)
    manifest.attrs["minimum_required"] = int(minimum_count)
    if len(manifest) < minimum_count:
        details = "; ".join(
            f"{item['slug']}: {item['reason']}" for item in recorder.skipped[:12]
        )
        raise ReportingDataError(
            f"Only {len(manifest)} valid Phase 6 figures were created; minimum_count={minimum_count}. "
            f"No missing figures were fabricated. Representative skip reasons: {details}"
        )
    _require(manifest["relative_path"].is_unique, "Duplicate figure paths in manifest")
    _require(manifest["sha256"].str.fullmatch(r"[0-9a-f]{64}").all(), "Invalid figure hash")
    _require(manifest["population_units_status_caveat_visible"].all(), "A figure lacks required visible context")
    return manifest
