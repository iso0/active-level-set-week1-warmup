"""Evaluation metrics: boundary subsets, classification/regression scores, AULC, crossings.

Synthetic boundary masks come from the Week 4 scripts, the real-data
empirical boundary (B1/B2/B3) from Phase 6/7, the frozen test-fold flags and
learning-curve endpoints from the Week 8.5 protocol. Everything here is pure:
arrays/frames in, dicts/frames out. Split objects are never imported; callers
pass test indices as plain sequences (``alse.protocol`` wraps these).
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
from scipy.spatial import distance
from scipy.special import ndtr
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from alse.io import require

# frozen: week4_01_boundary_metrics.py::BOUNDARY_QUANTILES, UNCERTAINTY_MULTIPLIER
BOUNDARY_QUANTILES = (10, 20, 30)
UNCERTAINTY_MULTIPLIER = 1.96
# frozen: week4_08_boundary_weighted_sur.py::PRIMARY_CLASSIFIER_EPSILON, GPR_PROBABILITY_EPS
#         (epsilon == week4_06_gp_classifier_surrogate.py::PRIMARY_UNCERTAINTY_EPSILON)
CLASSIFIER_EPSILON = 0.10
GPR_PROBABILITY_EPS = 1e-9
# frozen: week7_phase6_real_data_boundary_active_level_set.py::FEATURE_COLUMNS, KNN_MIXING_K
FEATURES = ("P", "VX", "LS", "ST")
KNN_MIXING_K = 10
# frozen: week7_phase7_final_boundary_hybrid_benchmark.py::BOUNDARY_IDS, PRIMARY_BOUNDARY_QUANTILES
BOUNDARY_IDS = ("B1", "B2", "B3")
PRIMARY_BOUNDARY_QUANTILES = (20, 30)
# frozen: week8_5_frozen_sample_efficiency_confirmation.py::TARGETS (persistent-crossing targets)
CROSSING_TARGETS = (0.75, 0.80, 0.85)
# frozen: week9_phase1_7_physics_ridge_residual_gp.py::EPS (probability clip of metric_values)
PROBABILITY_EPS = 1e-12
# Named budget windows (start, end) of the region AULCs; denominator = end - start.
# frozen: week9_phase1_13_fixed_physics_ard_discrepancy.py::EARLY_BUDGETS, LATE_BUDGETS
#         (== week9_phase1_14_m3_margin_acquisition.py) and
#         week9_phase1_18b_finalize.py::region_contrasts (EARLY_B16_24 / MID_B25_40 / LATE_B41_80 / BROAD_B16_40)
AULC_REGIONS: dict[str, tuple[int, int]] = {
    "EARLY_B16_40": (16, 40),
    "LATE_B41_80": (41, 80),
    "EARLY_B16_24": (16, 24),
    "MID_B25_40": (25, 40),
    "BROAD_B16_40": (16, 40),
}


# --- synthetic benchmarks (Week 4) -------------------------------------------


# frozen: week4_01_boundary_metrics.py::boundary_masks (== week4_06, week4_08)
def boundary_masks(values: np.ndarray, threshold: float | None = None) -> dict[int, np.ndarray]:
    """Masks of the closest q% points to the level set in function-value space.

    ``values`` are |f - threshold| distances when ``threshold`` is None,
    otherwise raw function values. Cutoff = np.percentile(distances, q), inclusive.
    """
    distances = np.asarray(values, dtype=float)
    if threshold is not None:
        distances = np.abs(distances - float(threshold))
    return {q: distances <= float(np.percentile(distances, q)) for q in BOUNDARY_QUANTILES}


# frozen: week4_08_boundary_weighted_sur.py::gpr_p_plus
def gpr_p_plus(mu: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    """P(f > 0) = Phi(mu / max(sigma, 1e-9))."""
    sigma_safe = np.maximum(np.asarray(sigma, dtype=float), GPR_PROBABILITY_EPS)
    return ndtr(np.asarray(mu, dtype=float) / sigma_safe)


# frozen: week4_06_gp_classifier_surrogate.py::predict_p_plus (== week4_08)
def predict_p_plus(model: Any, X: np.ndarray) -> np.ndarray:
    """Column of ``predict_proba`` for class +1 (exactly one such class required)."""
    probabilities = model.predict_proba(X)
    matches = np.flatnonzero(model.classes_ == 1.0)
    require(len(matches) == 1, f"Expected class +1 in classifier classes, got {model.classes_}")
    return probabilities[:, int(matches[0])]


# frozen: week4_01_boundary_metrics.py::evaluate_budget (gpr branch),
#         week4_06_gp_classifier_surrogate.py::evaluate_budget (gpc branch),
#         week4_08_boundary_weighted_sur.py::evaluate_budget (dispatch; row schema)
def evaluate_budget(
    model: Any,
    X_test: np.ndarray,
    y_test: np.ndarray,
    test_masks: Mapping[int, np.ndarray],
    *,
    surrogate: str = "gpr",
    epsilon: float = CLASSIFIER_EPSILON,
    **identity: Any,
) -> dict[str, Any]:
    """Per-budget synthetic metrics on a {-1,+1} test set.

    ``surrogate='gpr'``: prediction sign(mu >= 0), uncertainty region
    |mu| <= 1.96 sigma, p_plus = Phi(mu/sigma). ``surrogate='gpc'``: prediction
    p_plus >= 0.5, uncertainty region |p_plus - 0.5| <= epsilon (0.10).
    Row keys follow week4_08: ``uncertainty_region_fraction`` is week4_01's
    ``latent_uncertainty_region_fraction`` and week4_06's
    ``classifier_uncertainty_region_fraction_eps10`` (same numbers).
    ``identity`` entries (benchmark, method, seed, budget, ...) lead the row.
    """
    y_test = np.asarray(y_test)
    if surrogate == "gpr":
        mu, sigma = model.predict(X_test, return_std=True)
        p_plus = gpr_p_plus(mu, sigma)
        prediction = np.where(mu >= 0.0, 1.0, -1.0)
        uncertainty_region = np.abs(mu) <= UNCERTAINTY_MULTIPLIER * sigma
    elif surrogate == "gpc":
        p_plus = predict_p_plus(model, X_test)
        prediction = np.where(p_plus >= 0.5, 1.0, -1.0)
        uncertainty_region = np.abs(p_plus - 0.5) <= epsilon
    else:
        raise ValueError(f"Unknown surrogate variant: {surrogate}")
    errors = prediction != y_test
    clipped = np.clip(p_plus, 0.0, 1.0)
    bernoulli_u = clipped * (1.0 - clipped)
    row: dict[str, Any] = {
        **identity,
        "global_error": float(np.mean(errors)),
        "uncertainty_region_fraction": float(np.mean(uncertainty_region)),
        "integrated_bernoulli_uncertainty": float(np.mean(bernoulli_u)),
    }
    for quantile, mask in test_masks.items():
        row[f"near_boundary_error_q{quantile}"] = float(np.mean(errors[mask]))
        row[f"near_boundary_test_size_q{quantile}"] = int(mask.sum())
        row[f"uncertainty_region_fraction_q{quantile}"] = float(np.mean(uncertainty_region[mask]))
        row[f"integrated_bernoulli_uncertainty_q{quantile}"] = float(np.mean(bernoulli_u[mask]))
    return row


# --- real-data empirical boundary (Phase 6 / Phase 7) --------------------------


# frozen: week7_phase7_final_boundary_hybrid_benchmark.py::deterministic_order
def deterministic_order(values: np.ndarray, names: np.ndarray, *, ascending: bool) -> np.ndarray:
    """lexsort by value (or -value) with ties broken by experiment name."""
    numeric = np.asarray(values, dtype=float)
    names = np.asarray(names)
    if ascending:
        return np.lexsort((names.astype(str), numeric))
    return np.lexsort((names.astype(str), -numeric))


# frozen: week7_phase7_final_boundary_hybrid_benchmark.py::rank_fraction
def rank_fraction(values: np.ndarray, names: np.ndarray, *, ascending: bool) -> np.ndarray:
    """Rank (1..N) under deterministic_order divided by N."""
    order = deterministic_order(values, names, ascending=ascending)
    rank = np.empty(len(order), dtype=int)
    rank[order] = np.arange(1, len(order) + 1)
    return rank / len(order)


# frozen: week7_phase7_final_boundary_hybrid_benchmark.py::robust_scaled
def robust_scaled(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(x - median) / IQR per column (IQR <= 1e-12 -> 1); returns (scaled, median, iqr)."""
    median = np.median(x, axis=0)
    q25, q75 = np.quantile(x, [0.25, 0.75], axis=0)
    iqr = q75 - q25
    safe_iqr = np.where(iqr > 1e-12, iqr, 1.0)
    return (x - median) / safe_iqr, median, safe_iqr


# frozen: week7_phase7_final_boundary_hybrid_benchmark.py::class_distance_components
def class_distance_components(
    x_scaled: np.ndarray, labels: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(d_opp, d_same, nearest_opp, nearest_same): Euclidean nearest opposite-
    and same-label neighbour with self excluded (every row needs both)."""
    labels = np.asarray(labels)
    dmat = distance.cdist(x_scaled, x_scaled)
    np.fill_diagonal(dmat, np.inf)
    same_mask = labels[:, None] == labels[None, :]
    opposite_mask = ~same_mask
    np.fill_diagonal(same_mask, False)
    opposite = np.where(opposite_mask, dmat, np.inf)
    same = np.where(same_mask, dmat, np.inf)
    nearest_opp = np.argmin(opposite, axis=1)
    nearest_same = np.argmin(same, axis=1)
    d_opp = opposite[np.arange(len(labels)), nearest_opp]
    d_same = same[np.arange(len(labels)), nearest_same]
    require(np.isfinite(d_opp).all(), "Every row must have an opposite-class neighbour")
    require(np.isfinite(d_same).all(), "Every row must have a same-class neighbour")
    return d_opp, d_same, nearest_opp, nearest_same


def _population_frame(population: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    frame = population[["experiment_name", "partition", "has_keyhole", *FEATURES]].copy()
    labels = frame["has_keyhole"].astype(int).to_numpy()
    names = frame["experiment_name"].astype(str).to_numpy()
    return frame, labels, names


# frozen: week7_phase6_real_data_boundary_active_level_set.py::build_empirical_boundary_reference
#         (reference frame only; the summary/validation tables are scaffolding)
def build_empirical_boundary_reference(population: pd.DataFrame) -> pd.DataFrame:
    """Phase 6 model-independent boundary diagnostic, one row per simulation.

    ``empirical_boundary_distance`` (== B1) is the nearest opposite-label
    Euclidean distance after a StandardScaler fit on the full population;
    ``global_q{10,20,30}`` flag the first ceil(q% N) rows under a mergesort on
    (distance, experiment_name); k=10 neighbour label mixing columns follow.
    """
    frame, labels, names = _population_frame(population)
    scaler = StandardScaler().fit(frame[list(FEATURES)])
    x_scaled = scaler.transform(frame[list(FEATURES)])
    dmat = distance.cdist(x_scaled, x_scaled, metric="euclidean")
    np.fill_diagonal(dmat, np.inf)
    opposite = labels[:, None] != labels[None, :]
    opposite_distances = np.where(opposite, dmat, np.inf)
    nearest_pos = np.argmin(opposite_distances, axis=1)
    frame["empirical_boundary_distance"] = opposite_distances[np.arange(len(frame)), nearest_pos]
    frame["nearest_opposite_experiment"] = names[nearest_pos]
    frame["nearest_opposite_label"] = labels[nearest_pos]
    frame["boundary_rank"] = frame["empirical_boundary_distance"].rank(method="first")
    frame["boundary_rank_fraction"] = frame["boundary_rank"] / len(frame)
    for q in BOUNDARY_QUANTILES:
        count = int(math.ceil(q / 100.0 * len(frame)))
        order = frame.sort_values(["empirical_boundary_distance", "experiment_name"], kind="mergesort").index[:count]
        frame[f"global_q{q}"] = False
        frame.loc[order, f"global_q{q}"] = True

    k = min(KNN_MIXING_K, len(frame) - 1)
    neighbors = NearestNeighbors(n_neighbors=k + 1).fit(x_scaled)
    _, indices = neighbors.kneighbors(x_scaled)
    neighbor_labels = labels[indices[:, 1:]]
    p = neighbor_labels.mean(axis=1)
    entropy = np.zeros_like(p, dtype=float)
    mask = (p > 0) & (p < 1)
    entropy[mask] = -(p[mask] * np.log2(p[mask]) + (1 - p[mask]) * np.log2(1 - p[mask]))
    frame["knn_k"] = k
    frame["knn_positive_fraction"] = p
    frame["knn_label_entropy_bits"] = entropy
    frame["knn_opposite_fraction"] = (neighbor_labels != labels[:, None]).mean(axis=1)
    for j, feature in enumerate(FEATURES):
        frame[f"standardized_{feature}"] = x_scaled[:, j]
    return frame


# frozen: week7_phase6_real_data_boundary_active_level_set.py::assign_test_boundary_subsets, test_boundary_flags
def test_fold_boundary_flags(test_indices: Sequence[int], boundary: pd.DataFrame) -> dict[int, np.ndarray]:
    """Phase 6 test-fold subsets {10, 20, 30}: the first ceil(q% n_test) test
    rows by (empirical_boundary_distance, experiment_name), in test order.

    The archive restored row order with ``sort_index()`` on the population
    index (== test order for the sorted StratifiedGroupKFold folds); the
    positional index below makes that hold for any test order.
    """
    subset = boundary.iloc[list(test_indices)][["experiment_name", "empirical_boundary_distance"]].copy()
    subset.index = pd.RangeIndex(len(subset))
    subset = subset.sort_values(["empirical_boundary_distance", "experiment_name"], kind="mergesort")
    for q in BOUNDARY_QUANTILES:
        count = int(math.ceil(q / 100.0 * len(subset)))
        subset[f"test_q{q}"] = False
        subset.iloc[:count, subset.columns.get_loc(f"test_q{q}")] = True
    subset = subset.sort_index()
    return {q: subset[f"test_q{q}"].to_numpy(bool) for q in BOUNDARY_QUANTILES}


# frozen: week7_phase7_final_boundary_hybrid_benchmark.py::build_boundary_metrics ('reference' frame;
#         definitions/membership/overlap/consensus/scaling tables are scaffolding)
def boundary_metrics(population: pd.DataFrame) -> pd.DataFrame:
    """Phase 7 reference frame: B1 (nearest opposite distance, z-scored inputs),
    B2 (k=5 neighbour disagreement; k=10 secondary), B3 = d_opp/(d_opp+d_same),
    robust (median/IQR) variants, rank fractions, ``{B}_q{10,20,30}`` flags
    (deterministic_order; ascending for B1/B3, descending for B2) and
    ``consensus_q{20,30}`` (member of >= 2 of B1/B2/B3)."""
    frame, labels, names = _population_frame(population)
    x = frame[list(FEATURES)].to_numpy(float)
    x_z = StandardScaler().fit(x).transform(x)
    x_robust, _, _ = robust_scaled(x)

    d_opp, d_same, nearest_opp, nearest_same = class_distance_components(x_z, labels)
    frame["B1_nearest_opposite_distance"] = d_opp
    frame["B1_nearest_opposite_experiment"] = names[nearest_opp]
    frame["B2_local_disagreement_k5"] = 0.0
    frame["B2_local_disagreement_k10_secondary"] = 0.0
    for k, column in [(5, "B2_local_disagreement_k5"), (10, "B2_local_disagreement_k10_secondary")]:
        _, neighbours = NearestNeighbors(n_neighbors=k + 1).fit(x_z).kneighbors(x_z)
        frame[column] = (labels[neighbours[:, 1:]] != labels[:, None]).mean(axis=1)
    frame["B3_d_opp"] = d_opp
    frame["B3_d_same"] = d_same
    frame["B3_relative_class_distance_ratio"] = d_opp / np.maximum(d_opp + d_same, 1e-15)
    frame["B3_nearest_same_experiment"] = names[nearest_same]

    robust_opp, robust_same, _, _ = class_distance_components(x_robust, labels)
    frame["robust_B1_nearest_opposite_distance"] = robust_opp
    frame["robust_B3_relative_class_distance_ratio"] = robust_opp / np.maximum(robust_opp + robust_same, 1e-15)
    for j, feature in enumerate(FEATURES):
        frame[f"standardized_{feature}"] = x_z[:, j]
        frame[f"robust_scaled_{feature}"] = x_robust[:, j]

    metric_columns = {
        "B1": ("B1_nearest_opposite_distance", True),
        "B2": ("B2_local_disagreement_k5", False),
        "B3": ("B3_relative_class_distance_ratio", True),
    }
    for metric, (column, ascending) in metric_columns.items():
        values = frame[column].to_numpy(float)
        frame[f"{metric}_boundary_rank_fraction"] = rank_fraction(values, names, ascending=ascending)
        order = deterministic_order(values, names, ascending=ascending)
        for q in BOUNDARY_QUANTILES:
            flag = np.zeros(len(frame), dtype=bool)
            flag[order[: int(math.ceil(q / 100 * len(frame)))]] = True
            frame[f"{metric}_q{q}"] = flag
    for q in PRIMARY_BOUNDARY_QUANTILES:
        frame[f"consensus_q{q}"] = frame[[f"{metric}_q{q}" for metric in BOUNDARY_IDS]].sum(axis=1).ge(2)
    return frame


# --- frozen protocol flags (Week 8.5 / Week 9) ---------------------------------


# frozen: week8_5_frozen_sample_efficiency_confirmation.py::b1_distance
def b1_distance(population: pd.DataFrame) -> np.ndarray:
    """Nearest opposite-label Euclidean distance on StandardScaler(P,VX,LS,ST) of all rows."""
    x = population.loc[:, list(FEATURES)].to_numpy(float)
    labels = population["has_keyhole"].astype(int).to_numpy()
    z = StandardScaler().fit_transform(x)
    dmat = distance.cdist(z, z)
    opposite = labels[:, None] != labels[None, :]
    return np.where(opposite, dmat, np.inf).min(axis=1)


# frozen: week8_5_frozen_sample_efficiency_confirmation.py::boundary_flags
def boundary_flags(
    test_indices: Sequence[int], population: pd.DataFrame, distances: np.ndarray
) -> dict[str, np.ndarray]:
    """{'B1_q20', 'B1_q30'} over the test rows (test order): the first
    ceil(q% n_test) rows by deterministic_order(B1 distance, experiment_name)
    (17 and 25 of 81)."""
    test = np.asarray(test_indices, dtype=int)
    names = population.iloc[test]["experiment_name"].astype(str).to_numpy()
    order = deterministic_order(np.asarray(distances)[test], names, ascending=True)
    result: dict[str, np.ndarray] = {}
    for q in (20, 30):
        flag = np.zeros(len(test), dtype=bool)
        flag[order[: int(math.ceil(q / 100 * len(test)))]] = True
        result[f"B1_q{q}"] = flag
    return result


# frozen: week9_phase1_7_physics_ridge_residual_gp.py::subset_flags
def subset_flags(
    test_indices: Sequence[int], population: pd.DataFrame, distances: np.ndarray
) -> dict[str, np.ndarray]:
    """{'full81', 'B1_q30', 'B1_q20'} in this order (Week 9 evaluation subsets)."""
    flags = boundary_flags(test_indices, population, distances)
    return {"full81": np.ones(len(test_indices), dtype=bool), "B1_q30": flags["B1_q30"], "B1_q20": flags["B1_q20"]}


# --- classification / regression metrics ---------------------------------------


# frozen: week7_phase6_real_data_boundary_active_level_set.py::classification_metrics
def classification_metrics(
    labels: np.ndarray,
    probabilities: np.ndarray | None,
    predictions: np.ndarray,
    *,
    boundary_flags: Mapping[int, np.ndarray] | None = None,
    ranking_scores: np.ndarray | None = None,
) -> dict[str, Any]:
    """Phase 6 per-budget classification scores on {0,1} labels: BA, sensitivity,
    specificity, precision, F1, global error, confusion counts, ROC/AP on
    probabilities (or ``ranking_scores``), Brier, ``q{q}_error/count/keyhole_count``."""
    labels = np.asarray(labels, dtype=int)
    predictions = np.asarray(predictions, dtype=int)
    tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    result: dict[str, Any] = {
        "balanced_accuracy": float(balanced_accuracy_score(labels, predictions)),
        "sensitivity": float(tp / (tp + fn)) if tp + fn else math.nan,
        "specificity": float(tn / (tn + fp)) if tn + fp else math.nan,
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "global_error": float(np.mean(predictions != labels)),
        "true_positive": int(tp),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
    }
    score = probabilities if probabilities is not None else ranking_scores
    if score is not None and len(np.unique(labels)) == 2:
        result["roc_auc"] = float(roc_auc_score(labels, score))
        result["average_precision"] = float(average_precision_score(labels, score))
    else:
        result["roc_auc"] = math.nan
        result["average_precision"] = math.nan
    result["brier_score"] = float(brier_score_loss(labels, probabilities)) if probabilities is not None else math.nan
    if boundary_flags:
        for q, flag in boundary_flags.items():
            flag_arr = np.asarray(flag, dtype=bool)
            result[f"q{q}_error"] = (
                float(np.mean(predictions[flag_arr] != labels[flag_arr])) if flag_arr.any() else math.nan
            )
            result[f"q{q}_count"] = int(flag_arr.sum())
            result[f"q{q}_keyhole_count"] = int(labels[flag_arr].sum())
    return result


# frozen: week7_phase6_real_data_boundary_active_level_set.py::regression_metrics
def regression_metrics(labels: np.ndarray, predictions: np.ndarray) -> dict[str, float]:
    """MAE, RMSE, both relative to mean |y| (floor 1e-12), and R^2."""
    labels = np.asarray(labels, dtype=float)
    predictions = np.asarray(predictions, dtype=float)
    mae = float(mean_absolute_error(labels, predictions))
    rmse = float(math.sqrt(mean_squared_error(labels, predictions)))
    scale = max(float(np.mean(np.abs(labels))), 1e-12)
    return {"mae": mae, "rmse": rmse, "relative_mae": mae / scale, "relative_rmse": rmse / scale,
            "r2": float(r2_score(labels, predictions))}


# frozen: week8_5_frozen_sample_efficiency_confirmation.py::compute_metrics
def compute_metrics(labels: np.ndarray, probability: np.ndarray, flag: np.ndarray) -> dict[str, float | int]:
    """Week 8.5 metrics on the flagged rows with decision p >= 0.5: accuracy,
    recall, balanced_accuracy, FN/FP/TN/TP, row_count."""
    labels = np.asarray(labels)
    flag = np.asarray(flag, dtype=bool)
    truth = labels[flag].astype(int)
    pred = (np.asarray(probability, dtype=float)[flag] >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(truth, pred, labels=[0, 1]).ravel()
    return {
        "accuracy": float((pred == truth).mean()),
        "recall": float(recall_score(truth, pred, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(truth, pred)),
        "false_negative": int(fn),
        "false_positive": int(fp),
        "true_negative": int(tn),
        "true_positive": int(tp),
        "row_count": int(len(truth)),
    }


# frozen: week9_phase1_12_gpc_kernel_adequacy.py::metric_values
#         (== week9_phase1_7/1_5::metric_values plus the 'brier_score' key)
def probability_metrics(truth: np.ndarray, probability: np.ndarray) -> dict[str, float | int]:
    """Week 9 per-subset metrics with the probability clipped to
    [1e-12, 1-1e-12]: ROC, PR-AUC, accuracy, BA, keyhole/conduction recall,
    Brier, confusion counts, row_count."""
    truth = np.asarray(truth, dtype=int)
    probability = np.clip(np.asarray(probability, dtype=float), PROBABILITY_EPS, 1.0 - PROBABILITY_EPS)
    prediction = (probability >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(truth, prediction, labels=[0, 1]).ravel()
    return {
        "roc_auc": float(roc_auc_score(truth, probability)) if len(np.unique(truth)) == 2 else math.nan,
        "pr_auc": float(average_precision_score(truth, probability)),
        "accuracy": float((prediction == truth).mean()),
        "balanced_accuracy": float(balanced_accuracy_score(truth, prediction)),
        "keyhole_recall": float(recall_score(truth, prediction, pos_label=1, zero_division=0)),
        "conduction_recall": float(recall_score(truth, prediction, pos_label=0, zero_division=0)),
        "brier_score": float(brier_score_loss(truth, probability)),
        "false_negative": int(fn),
        "false_positive": int(fp),
        "true_negative": int(tn),
        "true_positive": int(tp),
        "row_count": int(len(truth)),
    }


# --- learning-curve endpoints ---------------------------------------------------


# frozen: week8_5_frozen_sample_efficiency_confirmation.py::aulc
def aulc(budgets: Sequence[int], values: Sequence[float], start: int = 16, end: int = 80) -> float:
    """np.trapezoid of ``values`` over the complete integer budget grid
    start..end divided by (end - start) (64 for 16-80). Budgets outside the
    window are ignored; a missing budget inside it raises."""
    budgets = np.asarray(budgets, dtype=int)
    values = np.asarray(values, dtype=float)
    order = np.argsort(budgets, kind="stable")
    budgets, values = budgets[order], values[order]
    keep = (budgets >= start) & (budgets <= end)
    require(budgets[keep].tolist() == list(range(start, end + 1)), f"AULC grid {start}-{end} incomplete")
    return float(np.trapezoid(values[keep], budgets[keep].astype(float)) / (end - start))


def region_aulc(budgets: Sequence[int], values: Sequence[float], region: str) -> float:
    """``aulc`` over a named window from AULC_REGIONS."""
    start, end = AULC_REGIONS[region]
    return aulc(budgets, values, start, end)


# frozen: week8_5_frozen_sample_efficiency_confirmation.py::persistent_crossing (consecutive == 3)
def persistent_crossing(
    budgets: Sequence[int], values: Sequence[float], target: float, consecutive: int = 3
) -> tuple[float, bool]:
    """First budget (in budget order) from which ``consecutive`` successive
    values are all >= target; (nan, False) when never observed (right-censored)."""
    budgets = np.asarray(budgets, dtype=int)
    values = np.asarray(values, dtype=float)
    order = np.argsort(budgets, kind="stable")
    budgets, values = budgets[order], values[order]
    for index in range(len(values) - consecutive + 1):
        if bool(np.all(values[index : index + consecutive] >= target)):
            return float(budgets[index]), True
    return math.nan, False
