"""Week 9 Phase 1.5: forensic confirmation of the physics-informed h coordinate.

This module creates only Phase 1.5 artifacts.  Frozen Week 8.5 and Week 9
Phase 1 files are inputs and are never modified.  The exact frozen outer
splits, initial designs, Fold-B1 subsets, AULC grid, and persistent crossing
function are imported from the Week 8.5 implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    log_loss,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

from src import week7_phase6_real_data_boundary_active_level_set as p6
from src import week8_5_frozen_sample_efficiency_confirmation as w85


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase1_5_h_physics_confirmation"
FIGURES = OUTPUT / "figures"
CHECKPOINTS = OUTPUT / "checkpoints"
REPORTS = ROOT / "reports"
NOTEBOOK = ROOT / "notebooks" / "week_09" / "02_week9_phase1_5_h_physics_confirmation.ipynb"
FROZEN = ROOT / "outputs" / "week8_5_frozen_confirmation"
PHASE1 = ROOT / "outputs" / "week9_phase1_close_week8"
FEATURES = ("P", "VX", "LS", "ST")
STARTING_BRANCH = "codex/week9-phase1-close-week8-sample-efficiency"
STARTING_SHA = "bdb6eb3628ae5eafaa0e5bc94d454626a6cf550a"
BRANCH = "codex/week9-phase1-5-h-physics-confirmation"
SEED_ROOT = "week9_phase1_5_h_physics_confirmation|v1"
STATIC_MODELS = (
    "log_h_logistic",
    "log_h_st_logistic",
    "logistic_M1",
    "logistic_M3",
    "gpc_1d_h",
    "gpc_4d",
    "gpc_5d_h_augmented",
)
SCORE_MODELS = (
    "log_linear_energy",
    "log_irradiance",
    "log_areal_energy",
    "log_volumetric_energy",
    "log_king_style",
)
AL_ARMS = ("h_margin", "gpc5_margin", "assisted_product")
PRIMARY_HORIZON = 80
LATE_HORIZON = 160
BOOTSTRAP_DRAWS = 5000
EPS = 1e-12

# Gan et al. (2021) Supplementary Table 3 reports 1933 K for Ti-6Al-4V.
# This is used only for an explicitly labelled single-material ST sensitivity;
# the final report does not call the partial coordinate a complete Keyhole number.
TI64_LIQUIDUS_K = 1933.0


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def seed_u32(*parts: object) -> int:
    key = "|".join((SEED_ROOT, *(str(part) for part in parts)))
    return int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "little") % (2**32)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, (np.integer, np.floating)):
        number = value.item()
        return number if not isinstance(number, float) or math.isfinite(number) else None
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    frame.to_csv(
        temporary,
        index=False,
        lineterminator="\n",
        compression="gzip" if path.suffix == ".gz" else None,
    )
    temporary.replace(path)


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def frozen_protocol_hash() -> str:
    """Verify the logical canonical protocol without rewriting a CRLF checkout."""

    protocol = json.loads(w85.PROTOCOL_PATH.read_text(encoding="utf-8"))
    digest = hashlib.sha256(w85.canonical_protocol_bytes(protocol)).hexdigest()
    recorded = (FROZEN / "protocol_sha256.txt").read_text(encoding="utf-8").split()[0]
    require(digest == recorded, "logical frozen protocol hash drift")
    return digest


def h_coordinates(population: pd.DataFrame) -> pd.DataFrame:
    p = population.P.to_numpy(float)
    velocity = population.VX.to_numpy(float)
    radius_m = population.LS.to_numpy(float)
    require((p > 0).all() and (velocity > 0).all() and (radius_m > 0).all(), "h inputs must be positive")
    h = p / np.sqrt(velocity * radius_m**3)
    log_h = np.log(h)
    delta_liquidus = TI64_LIQUIDUS_K - population.ST.to_numpy(float)
    require((delta_liquidus > 0).all(), "ST exceeds fixed liquidus reference")
    h_st = h / delta_liquidus
    frame = pd.DataFrame(
        {
            "population_row_index": population.index.astype(int),
            "experiment_name": population.experiment_name.astype(str),
            "manual_has_keyhole": population.has_keyhole.astype(int),
            "h_SI": h,
            "log_h_SI_reference": log_h,
            "delta_T_liquidus_minus_ST_K": delta_liquidus,
            "h_over_deltaT": h_st,
            "log_h_over_deltaT": np.log(h_st),
        }
    )
    require(np.isfinite(frame.select_dtypes(include=[np.number])).all().all(), "non-finite h coordinate")
    return frame


def derived_scores(population: pd.DataFrame, h_frame: pd.DataFrame) -> dict[str, np.ndarray]:
    p = population.P.to_numpy(float)
    v = population.VX.to_numpy(float)
    r = population.LS.to_numpy(float)
    return {
        "log_h_logistic": h_frame.log_h_SI_reference.to_numpy(float),
        "log_h_st_logistic": h_frame.log_h_over_deltaT.to_numpy(float),
        "log_linear_energy": np.log(p / v),
        "log_irradiance": np.log(p / r**2),
        "log_areal_energy": np.log(p / (v * r)),
        "log_volumetric_energy": np.log(p / (v * r**2)),
        "log_king_style": np.log(p / (r * np.sqrt(v))),
    }


def audit_inputs() -> tuple[pd.DataFrame, list[w85.SplitSpec], dict[str, Any]]:
    population = w85.load_population().reset_index(drop=True)
    specs = w85.build_splits(population)
    require(len(population) == 405, "canonical population must have 405 rows")
    require(int(population.has_keyhole.sum()) == 73, "canonical population must have 73 Keyhole rows")
    require(int((~population.has_keyhole.astype(bool)).sum()) == 332, "canonical population must have 332 Conduction rows")
    require(population.experiment_name.is_unique, "experiment_name must be unique")
    require(not population[[*FEATURES, "has_keyhole"]].isna().any().any(), "canonical inputs/labels contain missing values")
    require(len(specs) == 100, "expected 20 repeats x 5 folds")
    split_rows = []
    distances = w85.b1_distance(population)
    for spec in specs:
        train, test = set(spec.train_indices), set(spec.test_indices)
        require(len(train) == 324 and len(test) == 81 and not train.intersection(test), f"split drift {spec.run_id}")
        initial = w85.initial_design(spec, population)
        require(len(initial) == 16 and set(initial).issubset(train), f"initial design drift {spec.run_id}")
        flags = w85.boundary_flags(spec, population, distances)
        require(int(flags["B1_q20"].sum()) == 17 and int(flags["B1_q30"].sum()) == 25, f"Fold-B1 count drift {spec.run_id}")
        split_rows.append(
            {
                "run_id": spec.run_id,
                "repeat": spec.repeat,
                "fold": spec.fold,
                "training_rows": len(train),
                "test_rows": len(test),
                "initial_rows": len(initial),
                "q20_rows": int(flags["B1_q20"].sum()),
                "q30_rows": int(flags["B1_q30"].sum()),
                "group_disjoint": not set(population.iloc[list(train)].input_tuple_sha256).intersection(
                    set(population.iloc[list(test)].input_tuple_sha256)
                ),
            }
        )
    split_frame = pd.DataFrame(split_rows)
    require(split_frame.group_disjoint.all(), "group leakage in frozen splits")
    ls_um = population.LS.to_numpy(float) * 1e6
    audit = {
        "status": "PASS",
        "starting_branch": STARTING_BRANCH,
        "starting_sha": STARTING_SHA,
        "study_branch": BRANCH,
        "current_sha_before_phase1_5_commit": git_output("rev-parse", "HEAD"),
        "canonical_source": str(w85.SOURCE_POPULATION.relative_to(ROOT)),
        "canonical_source_sha256": sha256_file(w85.SOURCE_POPULATION),
        "rows": len(population),
        "keyhole": int(population.has_keyhole.sum()),
        "conduction": int((population.has_keyhole.astype(int) == 0).sum()),
        "P_range_W": [float(population.P.min()), float(population.P.max())],
        "VX_range_m_per_s": [float(population.VX.min()), float(population.VX.max())],
        "LS_range_um": [float(ls_um.min()), float(ls_um.max())],
        "ST_range_K": [float(population.ST.min()), float(population.ST.max())],
        "LS_definition": "Gaussian laser spot radius r0; stored in metres",
        "ST_definition": "substrate temperature",
        "ground_truth": "manual experiment-level has_keyhole",
        "B1_definition": "nearest opposite-manual-label distance in globally standardized 4D input space; evaluation only",
        "frozen_protocol_sha256": frozen_protocol_hash(),
        "frozen_outer_runs": len(specs),
        "files_read": [
            str(w85.SOURCE_POPULATION.relative_to(ROOT)),
            "outputs/week8_5_frozen_confirmation/preregistered_protocol.json",
            "outputs/week8_5_frozen_confirmation/run_level_metrics.csv",
            "outputs/week8_5_frozen_confirmation/bootstrap_or_hierarchical_ci.csv",
            "outputs/week9_phase1_close_week8/learning_curve_summary_16_80.csv",
        ],
    }
    write_json(OUTPUT / "data_and_protocol_audit.json", audit)
    write_csv(OUTPUT / "split_integrity.csv", split_frame)
    return population, specs, audit


def metric_values(truth: np.ndarray, probability: np.ndarray) -> dict[str, float | int]:
    truth = np.asarray(truth, dtype=int)
    probability = np.clip(np.asarray(probability, dtype=float), EPS, 1.0 - EPS)
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
        "log_loss": float(log_loss(truth, probability, labels=[0, 1])),
        "false_negative": int(fn),
        "false_positive": int(fp),
        "true_negative": int(tn),
        "true_positive": int(tp),
        "row_count": int(len(truth)),
    }


def fit_scalar_logistic(train: np.ndarray, y_train: np.ndarray, test: np.ndarray, seed: int) -> np.ndarray:
    scaler = StandardScaler().fit(np.asarray(train, dtype=float).reshape(-1, 1))
    model = LogisticRegression(C=1e6, solver="lbfgs", max_iter=3000, random_state=seed)
    model.fit(scaler.transform(np.asarray(train).reshape(-1, 1)), y_train)
    return model.predict_proba(scaler.transform(np.asarray(test).reshape(-1, 1)))[:, 1]


def logistic_design(x: np.ndarray, model: str) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if model == "logistic_M1":
        return x
    if model == "logistic_M3":
        return np.column_stack([x, x[:, 0] * x[:, 1]])
    raise RuntimeError(f"unknown logistic design {model}")


def fit_multivariate_logistic(x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray, model: str, seed: int) -> np.ndarray:
    scaler = StandardScaler().fit(x_train)
    train_z = scaler.transform(x_train)
    test_z = scaler.transform(x_test)
    estimator = LogisticRegression(C=1e6, solver="lbfgs", max_iter=3000, random_state=seed)
    estimator.fit(logistic_design(train_z, model), y_train)
    return estimator.predict_proba(logistic_design(test_z, model))[:, 1]


def fit_gpc_probability(x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray, seed: int) -> tuple[np.ndarray, str, str]:
    scaler = StandardScaler().fit(x_train)
    fit = p6.fit_gpc(x_train, y_train, scaler=scaler, seed=seed, kernel_kind="matern32", restarts=0)
    return p6.predict_gpc(fit, x_test), fit.fit_status, fit.kernel


def subset_flags_for_spec(spec: w85.SplitSpec, population: pd.DataFrame, distances: np.ndarray) -> dict[str, np.ndarray]:
    flags = w85.boundary_flags(spec, population, distances)
    return {
        "full81": np.ones(len(spec.test_indices), dtype=bool),
        "B1_q30": flags["B1_q30"],
        "B1_q20": flags["B1_q20"],
    }


def static_fold(
    spec: w85.SplitSpec,
    population: pd.DataFrame,
    h_frame: pd.DataFrame,
    scores: Mapping[str, np.ndarray],
    distances: np.ndarray,
) -> list[dict[str, Any]]:
    train = np.asarray(spec.train_indices, dtype=int)
    test = np.asarray(spec.test_indices, dtype=int)
    x4 = population.loc[:, FEATURES].to_numpy(float)
    y = population.has_keyhole.astype(int).to_numpy()
    log_h = h_frame.log_h_SI_reference.to_numpy(float)
    x5 = np.column_stack([x4, log_h])
    predictions: dict[str, tuple[np.ndarray, str, str]] = {}
    for name in ("log_h_logistic", "log_h_st_logistic", *SCORE_MODELS):
        probability = fit_scalar_logistic(scores[name][train], y[train], scores[name][test], seed_u32("static", spec.run_id, name))
        predictions[name] = (probability, "logistic", "NA")
    for name in ("logistic_M1", "logistic_M3"):
        probability = fit_multivariate_logistic(x4[train], y[train], x4[test], name, seed_u32("static", spec.run_id, name))
        predictions[name] = (probability, "logistic", "NA")
    for name, matrix in (
        ("gpc_1d_h", log_h[:, None]),
        ("gpc_4d", x4),
        ("gpc_5d_h_augmented", x5),
    ):
        probability, status, kernel = fit_gpc_probability(matrix[train], y[train], matrix[test], seed_u32("static", spec.run_id, name))
        predictions[name] = (probability, status, kernel)
    flags = subset_flags_for_spec(spec, population, distances)
    rows: list[dict[str, Any]] = []
    for model, (probability, status, kernel) in predictions.items():
        for local, population_index in enumerate(test):
            rows.append(
                {
                    "run_id": spec.run_id,
                    "repeat": spec.repeat,
                    "fold": spec.fold,
                    "model": model,
                    "population_row_index": int(population_index),
                    "experiment_name": str(population.iloc[population_index].experiment_name),
                    "truth": int(y[population_index]),
                    "probability": float(probability[local]),
                    "is_full81": True,
                    "is_B1_q30": bool(flags["B1_q30"][local]),
                    "is_B1_q20": bool(flags["B1_q20"][local]),
                    "fit_status": status,
                    "kernel": kernel,
                }
            )
    return rows


def summarize_prediction_frame(predictions: pd.DataFrame, prefix: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metric_rows: list[dict[str, Any]] = []
    for keys, group in predictions.groupby(["run_id", "repeat", "fold", "model"], sort=True):
        run_id, repeat, fold, model = keys
        for subset in ("full81", "B1_q30", "B1_q20"):
            selected = group[group[f"is_{subset}"].astype(bool)]
            metric_rows.append(
                {"run_id": run_id, "repeat": repeat, "fold": fold, "model": model, "subset": subset, **metric_values(selected.truth, selected.probability)}
            )
    fold_metrics = pd.DataFrame(metric_rows)
    repeat_rows: list[dict[str, Any]] = []
    for keys, group in predictions.groupby(["repeat", "model"], sort=True):
        repeat, model = keys
        for subset in ("full81", "B1_q30", "B1_q20"):
            selected = group[group[f"is_{subset}"].astype(bool)]
            repeat_rows.append({"repeat": repeat, "model": model, "subset": subset, **metric_values(selected.truth, selected.probability)})
    repeat_metrics = pd.DataFrame(repeat_rows)
    rng = np.random.default_rng(seed_u32(prefix, "summary_bootstrap"))
    summary_rows: list[dict[str, Any]] = []
    metric_names = ("roc_auc", "pr_auc", "accuracy", "balanced_accuracy", "keyhole_recall", "conduction_recall", "brier_score", "log_loss")
    for (model, subset), group in repeat_metrics.groupby(["model", "subset"], sort=True):
        values_by_metric = {metric: group.sort_values("repeat")[metric].to_numpy(float) for metric in metric_names}
        row: dict[str, Any] = {"model": model, "subset": subset, "repeat_blocks": len(group)}
        for metric, values in values_by_metric.items():
            draws = rng.choice(values, size=(BOOTSTRAP_DRAWS, len(values)), replace=True).mean(axis=1)
            row[f"mean_{metric}"] = float(values.mean())
            row[f"ci_lower_{metric}"] = float(np.quantile(draws, 0.025))
            row[f"ci_upper_{metric}"] = float(np.quantile(draws, 0.975))
        summary_rows.append(row)
    return fold_metrics, repeat_metrics, pd.DataFrame(summary_rows)


def paired_static_contrasts(repeat_metrics: pd.DataFrame) -> pd.DataFrame:
    metrics = ("roc_auc", "pr_auc", "accuracy", "balanced_accuracy", "keyhole_recall", "conduction_recall", "brier_score", "log_loss")
    comparisons = [
        ("log_h_logistic", "gpc_4d"),
        ("log_h_st_logistic", "log_h_logistic"),
        ("gpc_5d_h_augmented", "gpc_4d"),
        ("logistic_M3", "logistic_M1"),
    ]
    rng = np.random.default_rng(seed_u32("paired_static_contrasts"))
    rows = []
    indexed = repeat_metrics.set_index(["repeat", "model", "subset"])
    for left, right in comparisons:
        for subset in ("full81", "B1_q30", "B1_q20"):
            for metric in metrics:
                left_values = indexed.xs((left, subset), level=("model", "subset"))[metric].sort_index()
                right_values = indexed.xs((right, subset), level=("model", "subset"))[metric].sort_index()
                difference = left_values.to_numpy(float) - right_values.to_numpy(float)
                draws = rng.choice(difference, size=(BOOTSTRAP_DRAWS, len(difference)), replace=True).mean(axis=1)
                rows.append(
                    {
                        "left_model": left,
                        "right_model": right,
                        "subset": subset,
                        "metric": metric,
                        "left_minus_right": float(difference.mean()),
                        "ci_lower": float(np.quantile(draws, 0.025)),
                        "ci_upper": float(np.quantile(draws, 0.975)),
                        "repeat_blocks_positive": int((difference > 0).sum()),
                        "repeat_blocks": len(difference),
                    }
                )
    return pd.DataFrame(rows)


@dataclass
class MLEFit:
    coefficients: np.ndarray
    covariance: np.ndarray
    log_likelihood: float
    converged: bool


def fit_logistic_mle(x: np.ndarray, y: np.ndarray) -> MLEFit:
    design = np.column_stack([np.ones(len(y)), np.asarray(x, dtype=float)])
    y = np.asarray(y, dtype=float)

    def objective(beta: np.ndarray) -> float:
        linear = design @ beta
        return float(np.logaddexp(0.0, linear).sum() - y @ linear)

    def gradient(beta: np.ndarray) -> np.ndarray:
        return design.T @ (expit(design @ beta) - y)

    result = minimize(objective, np.zeros(design.shape[1]), jac=gradient, method="BFGS", options={"gtol": 1e-8, "maxiter": 2000})
    grad_norm = float(np.linalg.norm(gradient(result.x)))
    require(bool(result.success or grad_norm < 1e-5), f"logistic MLE failed: {result.message}; gradient={grad_norm}")
    probability = expit(design @ result.x)
    weight = probability * (1.0 - probability)
    covariance = np.linalg.pinv(design.T @ (weight[:, None] * design))
    return MLEFit(result.x, covariance, -objective(result.x), True)


def exponent_recovery(population: pd.DataFrame, specs: Sequence[w85.SplitSpec], draws: int = 1000) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    y = population.has_keyhole.astype(int).to_numpy()
    log_inputs = np.column_stack([np.log(population.P), np.log(population.VX), np.log(population.LS)])
    centers = log_inputs.mean(axis=0)
    x = log_inputs - centers
    fit = fit_logistic_mle(x, y)
    beta = fit.coefficients[1:]
    ratios = np.array([beta[1] / beta[0], beta[2] / beta[0]])
    rng = np.random.default_rng(seed_u32("exponent_bootstrap"))
    negative, positive = np.flatnonzero(y == 0), np.flatnonzero(y == 1)
    ratio_draws = []
    for _ in range(draws):
        index = np.concatenate([rng.choice(negative, len(negative), replace=True), rng.choice(positive, len(positive), replace=True)])
        try:
            estimate = fit_logistic_mle(x[index], y[index]).coefficients[1:]
            if abs(estimate[0]) > EPS:
                ratio_draws.append([estimate[1] / estimate[0], estimate[2] / estimate[0]])
        except RuntimeError:
            continue
    ratio_array = np.asarray(ratio_draws, dtype=float)
    require(len(ratio_array) >= int(draws * 0.9), "too many failed exponent bootstraps")
    summary = pd.DataFrame(
        [
            {
                "exponent": "VX relative to P",
                "theory": -0.5,
                "estimate": ratios[0],
                "ci_lower": float(np.quantile(ratio_array[:, 0], 0.025)),
                "ci_upper": float(np.quantile(ratio_array[:, 0], 0.975)),
                "theory_inside_ci": bool(np.quantile(ratio_array[:, 0], 0.025) <= -0.5 <= np.quantile(ratio_array[:, 0], 0.975)),
            },
            {
                "exponent": "LS relative to P",
                "theory": -1.5,
                "estimate": ratios[1],
                "ci_lower": float(np.quantile(ratio_array[:, 1], 0.025)),
                "ci_upper": float(np.quantile(ratio_array[:, 1], 0.975)),
                "theory_inside_ci": bool(np.quantile(ratio_array[:, 1], 0.025) <= -1.5 <= np.quantile(ratio_array[:, 1], 0.975)),
            },
        ]
    )
    fold_rows = []
    for spec in specs:
        train = np.asarray(spec.train_indices, dtype=int)
        estimate = fit_logistic_mle(x[train], y[train]).coefficients[1:]
        fold_rows.append(
            {
                "run_id": spec.run_id,
                "repeat": spec.repeat,
                "fold": spec.fold,
                "beta_logP": estimate[0],
                "beta_logVX": estimate[1],
                "beta_logLS": estimate[2],
                "VX_over_P": estimate[1] / estimate[0],
                "LS_over_P": estimate[2] / estimate[0],
            }
        )
    draws_frame = pd.DataFrame(ratio_array, columns=["VX_over_P", "LS_over_P"])
    return summary, pd.DataFrame(fold_rows), draws_frame


def calibration_audit(predictions: pd.DataFrame, bins: int = 10) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    h = predictions[predictions.model.eq("log_h_logistic")].copy()
    unique = h.groupby(["population_row_index", "experiment_name", "truth"], as_index=False).probability.mean()
    require(len(unique) == 405, "OOF screening must resolve to 405 unique simulations")
    edges = np.linspace(0.0, 1.0, bins + 1)
    unique["bin"] = np.minimum(np.digitize(unique.probability, edges[1:-1], right=False), bins - 1)
    reliability_rows = []
    for index in range(bins):
        group = unique[unique.bin.eq(index)]
        reliability_rows.append(
            {
                "bin": index + 1,
                "lower": edges[index],
                "upper": edges[index + 1],
                "count": len(group),
                "mean_probability": float(group.probability.mean()) if len(group) else math.nan,
                "observed_keyhole_rate": float(group.truth.mean()) if len(group) else math.nan,
                "absolute_gap": float(abs(group.truth.mean() - group.probability.mean())) if len(group) else math.nan,
            }
        )
    reliability = pd.DataFrame(reliability_rows)
    nonempty = reliability[reliability["count"] > 0]
    ece = float(np.sum(nonempty["count"] / len(unique) * nonempty.absolute_gap))
    mce = float(nonempty.absolute_gap.max())
    unique["zone"] = np.select(
        [unique.probability < 0.05, unique.probability > 0.95],
        ["low_p_lt_0.05", "high_p_gt_0.95"],
        default="ambiguous_0.05_to_0.95",
    )
    zone_rows = []
    for zone, group in unique.groupby("zone", sort=False):
        keyholes = int(group.truth.sum())
        conduction = int(len(group) - keyholes)
        zone_rows.append(
            {
                "zone": zone,
                "count": len(group),
                "keyhole": keyholes,
                "conduction": conduction,
                "false_negative_if_low_zone_screened_conduction": keyholes if zone == "low_p_lt_0.05" else 0,
                "false_positive_if_high_zone_screened_keyhole": conduction if zone == "high_p_gt_0.95" else 0,
                "negative_predictive_value": conduction / len(group) if zone == "low_p_lt_0.05" and len(group) else math.nan,
                "positive_predictive_value": keyholes / len(group) if zone == "high_p_gt_0.95" and len(group) else math.nan,
            }
        )
    summary = {
        "status": "retrospective simulator-domain screening rule",
        "oof_unit": "mean of 20 out-of-fold probabilities for each of 405 unique simulations",
        "binning": f"{bins} equal-width probability bins on [0,1]",
        "ECE_definition": "sum_b (n_b/N)*abs(observed_rate_b-mean_probability_b)",
        "MCE_definition": "maximum non-empty-bin absolute calibration gap",
        "ECE": ece,
        "MCE": mce,
        "OOF_Brier": float(brier_score_loss(unique.truth, unique.probability)),
    }
    return unique, pd.DataFrame(zone_rows), {**summary, "reliability": reliability.to_dict(orient="records")}


def residual_cases(predictions: pd.DataFrame, population: pd.DataFrame, h_frame: pd.DataFrame) -> pd.DataFrame:
    selected = predictions[predictions.model.isin(["log_h_logistic", "gpc_4d"])].copy()
    averaged = selected.groupby(["population_row_index", "experiment_name", "truth", "model"], as_index=False).probability.mean()
    wide = averaged.pivot(index=["population_row_index", "experiment_name", "truth"], columns="model", values="probability").reset_index()
    wide["h_prediction"] = (wide.log_h_logistic >= 0.5).astype(int)
    wide["gpc4_prediction"] = (wide.gpc_4d >= 0.5).astype(int)
    wide["h_wrong_gpc4_correct"] = wide.h_prediction.ne(wide.truth) & wide.gpc4_prediction.eq(wide.truth)
    extras = population.loc[:, [*FEATURES]].copy()
    extras["population_row_index"] = population.index.astype(int)
    extras["LS_um"] = extras.LS * 1e6
    extras["log_h"] = h_frame.log_h_SI_reference
    return wide.merge(extras, on="population_row_index", how="left", validate="one_to_one")


def run_static(workers: int = 1) -> dict[str, Any]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    population, specs, audit = audit_inputs()
    h_frame = h_coordinates(population)
    scores = derived_scores(population, h_frame)
    distances = w85.b1_distance(population)
    write_csv(OUTPUT / "h_coordinates.csv", h_frame)
    start = time.time()
    if workers == 1:
        nested = [static_fold(spec, population, h_frame, scores, distances) for spec in specs]
    else:
        nested = Parallel(n_jobs=workers, verbose=5)(
            delayed(static_fold)(spec, population, h_frame, scores, distances) for spec in specs
        )
    predictions = pd.DataFrame([row for block in nested for row in block])
    require(len(predictions) == len(specs) * len(STATIC_MODELS + SCORE_MODELS) * 81, "static prediction count drift")
    require(not predictions.duplicated(["run_id", "model", "population_row_index"]).any(), "duplicate static OOF prediction")
    fold_metrics, repeat_metrics, summary = summarize_prediction_frame(predictions, "static")
    contrasts = paired_static_contrasts(repeat_metrics)
    exponent_summary, exponent_folds, exponent_draws = exponent_recovery(population, specs)
    screening_rows, zones, calibration = calibration_audit(predictions)
    residual = residual_cases(predictions, population, h_frame)
    write_csv(OUTPUT / "static_oof_predictions.csv.gz", predictions)
    write_csv(OUTPUT / "static_fold_metrics.csv", fold_metrics)
    write_csv(OUTPUT / "static_repeat_metrics.csv", repeat_metrics)
    write_csv(OUTPUT / "static_model_summary.csv", summary)
    write_csv(OUTPUT / "static_paired_contrasts.csv", contrasts)
    write_csv(OUTPUT / "empirical_exponent_summary.csv", exponent_summary)
    write_csv(OUTPUT / "empirical_exponent_fold_stability.csv", exponent_folds)
    write_csv(OUTPUT / "empirical_exponent_bootstrap_draws.csv.gz", exponent_draws)
    write_csv(OUTPUT / "screening_oof_unique_predictions.csv", screening_rows)
    write_csv(OUTPUT / "screening_zone_summary.csv", zones)
    write_json(OUTPUT / "calibration_summary.json", calibration)
    write_csv(OUTPUT / "residual_case_analysis.csv", residual)
    result = {
        "status": "PASS",
        "elapsed_seconds": time.time() - start,
        "workers": workers,
        "outer_runs": len(specs),
        "models": list(STATIC_MODELS + SCORE_MODELS),
        "prediction_rows": len(predictions),
        "h_units": "W*s^0.5/m^2",
        "log_reference": "ln(h / (1 W*s^0.5/m^2))",
        "st_sensitivity": "log[h/(T_liquidus-ST)] with Gan et al. (2021) Supplementary Table 3 Ti-6Al-4V T_liquidus=1933 K; not a complete dimensionless Keyhole number",
        "data_audit": audit,
    }
    write_json(OUTPUT / "static_execution_report.json", result)
    return result


def baseline_reproduction_gate() -> dict[str, Any]:
    population = w85.load_population()
    specs = w85.build_splits(population)
    frozen_metrics = pd.read_csv(FROZEN / "run_level_metrics.csv")
    margin = frozen_metrics[frozen_metrics.arm.eq("binary_margin")].set_index("run_id")
    random = (
        frozen_metrics[frozen_metrics.arm.eq("binary_random")]
        .groupby("run_id", as_index=True)
        .B1_q20_AULC_16_80.mean()
    )
    require(len(margin) == 100 and len(random) == 100, "frozen AULC path count drift")
    point = float((margin.B1_q20_AULC_16_80 - random).mean())
    frozen_ci = pd.read_csv(FROZEN / "bootstrap_or_hierarchical_ci.csv")
    recorded = float(frozen_ci.loc[frozen_ci.estimand.eq("delta_AULC"), "point_estimate_bootstrap_mean"].iloc[0])
    require(abs(point - recorded) < 5e-4, f"baseline point estimate mismatch {point} vs {recorded}")
    manifest = pd.read_csv(FROZEN / "initial_design_manifest.csv")
    mismatches = []
    for spec in specs:
        expected = (
            manifest[manifest.run_id.eq(spec.run_id)]
            .sort_values("query_order")
            .population_row_index.astype(int)
            .tolist()
        )
        actual = w85.initial_design(spec, population)
        if expected != actual:
            mismatches.append(spec.run_id)
    require(not mismatches, f"initial design mismatch: {mismatches[:3]}")
    curve = pd.read_csv(PHASE1 / "learning_curve_summary_16_80.csv")
    require(set(curve.arm) == {"binary_margin", "binary_random"}, "saved baseline curve arms drift")
    require(curve.groupby("arm").budget.nunique().to_dict() == {"binary_margin": 65, "binary_random": 65}, "baseline curve grid drift")
    report = {
        "status": "PASS",
        "frozen_protocol_sha256": frozen_protocol_hash(),
        "outer_runs": len(specs),
        "initial_design_exact_matches": len(specs),
        "margin_mean_AULC16_80": float(margin.B1_q20_AULC_16_80.mean()),
        "matched_random_mean_AULC16_80": float(random.mean()),
        "reproduced_margin_minus_random": point,
        "recorded_bootstrap_mean_margin_minus_random": recorded,
        "absolute_difference": abs(point - recorded),
        "saved_learning_curve_grid": "16..80 inclusive for both arms",
    }
    write_json(OUTPUT / "baseline_reproduction_gate.json", report)
    return report


def deterministic_argmax(candidate_indices: np.ndarray, scores: np.ndarray) -> int:
    candidate_indices = np.asarray(candidate_indices, dtype=int)
    scores = np.asarray(scores, dtype=float)
    require(len(candidate_indices) == len(scores) and len(scores) > 0, "invalid acquisition score vector")
    require(np.isfinite(scores).all(), "non-finite acquisition scores")
    order = np.lexsort((candidate_indices, -scores))
    return int(candidate_indices[order[0]])


def choose_h_margin(candidate_indices: np.ndarray, candidate_probability: np.ndarray) -> int:
    """Feature/probability-only chooser; hidden labels and B1 are not accepted."""

    uncertainty = 1.0 - 2.0 * np.abs(np.asarray(candidate_probability, dtype=float) - 0.5)
    return deterministic_argmax(candidate_indices, uncertainty)


def choose_gpc_margin(candidate_indices: np.ndarray, candidate_probability: np.ndarray) -> int:
    """Canonical predictive-margin chooser with deterministic row-index ties."""

    uncertainty = 1.0 - 2.0 * np.abs(np.asarray(candidate_probability, dtype=float) - 0.5)
    return deterministic_argmax(candidate_indices, uncertainty)


def choose_assisted_product(
    candidate_indices: np.ndarray,
    gpc_probability: np.ndarray,
    h_probability: np.ndarray,
) -> int:
    """Product of revealed-label 4D and h uncertainties; no hidden-label threshold."""

    gpc_uncertainty = 4.0 * np.asarray(gpc_probability, dtype=float) * (1.0 - np.asarray(gpc_probability, dtype=float))
    h_uncertainty = 4.0 * np.asarray(h_probability, dtype=float) * (1.0 - np.asarray(h_probability, dtype=float))
    return deterministic_argmax(candidate_indices, gpc_uncertainty * h_uncertainty)


def fit_scalar_logistic_model(values: np.ndarray, labels: np.ndarray, seed: int) -> tuple[StandardScaler, LogisticRegression]:
    scaler = StandardScaler().fit(np.asarray(values, dtype=float).reshape(-1, 1))
    model = LogisticRegression(C=1e6, solver="lbfgs", max_iter=3000, random_state=seed)
    model.fit(scaler.transform(np.asarray(values).reshape(-1, 1)), labels)
    return scaler, model


def predict_scalar_logistic(model_bundle: tuple[StandardScaler, LogisticRegression], values: np.ndarray) -> np.ndarray:
    scaler, model = model_bundle
    return model.predict_proba(scaler.transform(np.asarray(values).reshape(-1, 1)))[:, 1]


def active_metric_rows(
    *,
    spec: w85.SplitSpec,
    population: pd.DataFrame,
    distances: np.ndarray,
    arm: str,
    prediction_model: str,
    budget: int,
    probability: np.ndarray,
    queried: Sequence[int],
    fit_status: str,
    kernel: str,
) -> list[dict[str, Any]]:
    test = np.asarray(spec.test_indices, dtype=int)
    truth = population.has_keyhole.astype(int).to_numpy()[test]
    flags = subset_flags_for_spec(spec, population, distances)
    rows = []
    for subset, flag in flags.items():
        rows.append(
            {
                "run_id": spec.run_id,
                "repeat": spec.repeat,
                "fold": spec.fold,
                "arm": arm,
                "prediction_model": prediction_model,
                "budget": budget,
                "subset": subset,
                "queried_keyhole": int(population.iloc[list(queried)].has_keyhole.astype(int).sum()),
                "queried_conduction": int(len(queried) - population.iloc[list(queried)].has_keyhole.astype(int).sum()),
                "fit_status": fit_status,
                "kernel": kernel,
                **metric_values(truth[flag], np.asarray(probability)[flag]),
            }
        )
    return rows


def active_checkpoint_path(spec: w85.SplitSpec, arm: str, root: Path) -> Path:
    return root / f"{spec.run_id}__{arm}.json"


def run_active_trajectory(
    spec: w85.SplitSpec,
    arm: str,
    horizon: int,
    population: pd.DataFrame,
    distances: np.ndarray,
    checkpoint_root: Path,
) -> dict[str, Any]:
    require(arm in AL_ARMS, f"unknown Phase 1.5 arm {arm}")
    train = np.asarray(spec.train_indices, dtype=int)
    test = np.asarray(spec.test_indices, dtype=int)
    y = population.has_keyhole.astype(int).to_numpy()
    x4 = population.loc[:, FEATURES].to_numpy(float)
    log_h = h_coordinates(population).log_h_SI_reference.to_numpy(float)
    x5 = np.column_stack([x4, log_h])
    path = active_checkpoint_path(spec, arm, checkpoint_root)
    if path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
        require(payload["run_id"] == spec.run_id and payload["arm"] == arm, "active checkpoint identity drift")
        queried = [int(value) for value in payload["queried_indices"]]
        rows = list(payload["rows"])
        mechanism = list(payload["mechanism"])
    else:
        queried = w85.initial_design(spec, population)
        rows = []
        mechanism = []
    require(queried[:16] == w85.initial_design(spec, population), "initial design prefix drift")
    require(set(queried).issubset(set(train)), "checkpoint query outside training pool")
    completed = {(row["prediction_model"], int(row["budget"]), row["subset"]) for row in rows}
    allowed = w85.declared_budgets(horizon)
    start_budget = len(queried)
    for budget in range(start_budget, horizon + 1):
        revealed = np.asarray(queried, dtype=int)
        candidate = np.setdiff1d(train, revealed, assume_unique=False)
        h_bundle: tuple[StandardScaler, LogisticRegression] | None = None
        gpc_fit = None
        gpc_matrix: np.ndarray | None = None
        gpc_name = ""
        if arm == "h_margin":
            h_bundle = fit_scalar_logistic_model(log_h[revealed], y[revealed], seed_u32("active", spec.run_id, arm, "h", budget))
        elif arm == "gpc5_margin":
            gpc_matrix = x5
            gpc_name = "gpc5_margin"
            gpc_fit = p6.fit_gpc(
                gpc_matrix[revealed],
                y[revealed],
                scaler=StandardScaler().fit(gpc_matrix[train]),
                seed=seed_u32("active", spec.run_id, arm, budget),
                kernel_kind="matern32",
                restarts=0,
            )
        elif arm == "assisted_product":
            gpc_matrix = x4
            gpc_name = "gpc4_assisted_product"
            gpc_fit = p6.fit_gpc(
                gpc_matrix[revealed],
                y[revealed],
                scaler=StandardScaler().fit(gpc_matrix[train]),
                seed=seed_u32("active", spec.run_id, arm, budget),
                kernel_kind="matern32",
                restarts=0,
            )
            h_bundle = fit_scalar_logistic_model(log_h[revealed], y[revealed], seed_u32("active", spec.run_id, arm, "h", budget))

        if budget in allowed:
            if arm == "h_margin":
                h_probability = predict_scalar_logistic(h_bundle, log_h[test])
                if ("h_model_h_acquisition", budget, "full81") not in completed:
                    rows.extend(
                        active_metric_rows(
                            spec=spec,
                            population=population,
                            distances=distances,
                            arm=arm,
                            prediction_model="h_model_h_acquisition",
                            budget=budget,
                            probability=h_probability,
                            queried=queried,
                            fit_status="logistic",
                            kernel="NA",
                        )
                    )
                gpc4_fit = p6.fit_gpc(
                    x4[revealed],
                    y[revealed],
                    scaler=StandardScaler().fit(x4[train]),
                    seed=seed_u32("active", spec.run_id, arm, "gpc4_eval", budget),
                    kernel_kind="matern32",
                    restarts=0,
                )
                if ("gpc4_h_acquisition", budget, "full81") not in completed:
                    rows.extend(
                        active_metric_rows(
                            spec=spec,
                            population=population,
                            distances=distances,
                            arm=arm,
                            prediction_model="gpc4_h_acquisition",
                            budget=budget,
                            probability=p6.predict_gpc(gpc4_fit, x4[test]),
                            queried=queried,
                            fit_status=gpc4_fit.fit_status,
                            kernel=gpc4_fit.kernel,
                        )
                    )
            else:
                if (gpc_name, budget, "full81") not in completed:
                    rows.extend(
                        active_metric_rows(
                            spec=spec,
                            population=population,
                            distances=distances,
                            arm=arm,
                            prediction_model=gpc_name,
                            budget=budget,
                            probability=p6.predict_gpc(gpc_fit, gpc_matrix[test]),
                            queried=queried,
                            fit_status=gpc_fit.fit_status,
                            kernel=gpc_fit.kernel,
                        )
                    )

        if budget < horizon:
            if arm == "h_margin":
                candidate_h_probability = predict_scalar_logistic(h_bundle, log_h[candidate])
                next_index = choose_h_margin(candidate, candidate_h_probability)
                acquisition = "maximum revealed-label log(h) logistic uncertainty"
            elif arm == "gpc5_margin":
                candidate_gpc_probability = p6.predict_gpc(gpc_fit, x5[candidate])
                next_index = choose_gpc_margin(candidate, candidate_gpc_probability)
                acquisition = "canonical predictive margin in redundant [P,VX,LS,ST,log(h)] embedding"
            else:
                candidate_gpc_probability = p6.predict_gpc(gpc_fit, x4[candidate])
                candidate_h_probability = predict_scalar_logistic(h_bundle, log_h[candidate])
                next_index = choose_assisted_product(candidate, candidate_gpc_probability, candidate_h_probability)
                acquisition = "product of revealed-label 4D GPC and log(h) logistic uncertainty"
            require(next_index in set(train) and next_index not in queried, "active chooser violated pool membership")
            mechanism.append(
                {
                    "run_id": spec.run_id,
                    "repeat": spec.repeat,
                    "fold": spec.fold,
                    "arm": arm,
                    "selection_budget": budget + 1,
                    "selected_population_row_index": next_index,
                    "selected_experiment_name": str(population.iloc[next_index].experiment_name),
                    "selected_label_revealed_after_selection": int(y[next_index]),
                    "acquisition_definition": acquisition,
                    "candidate_pool_role": "outer_training_pool_only",
                    "test_rows_available_to_acquisition": False,
                    "hidden_pool_labels_available_to_acquisition": False,
                    "B1_B2_B3_available_to_acquisition": False,
                    "threshold_fitted_from_all_pool_labels": False,
                }
            )
            queried.append(next_index)
        if budget % 5 == 0 or budget == horizon:
            write_json(
                path,
                {
                    "run_id": spec.run_id,
                    "repeat": spec.repeat,
                    "fold": spec.fold,
                    "arm": arm,
                    "horizon": horizon,
                    "complete": budget == horizon,
                    "queried_indices": queried,
                    "rows": rows,
                    "mechanism": mechanism,
                },
            )
    return {"run_id": spec.run_id, "arm": arm, "horizon": horizon, "rows": len(rows), "queries": len(queried), "complete": True}


def run_active(
    *,
    horizon: int,
    workers: int,
    arms: Sequence[str] = AL_ARMS,
    limit_specs: int | None = None,
    smoke: bool = False,
) -> dict[str, Any]:
    require(horizon in (80, 160), "Phase 1.5 active horizon must be 80 or 160")
    gate = baseline_reproduction_gate()
    require(gate["status"] == "PASS", "baseline reproduction gate did not pass")
    population, specs, _ = audit_inputs()
    if limit_specs is not None:
        specs = specs[:limit_specs]
    checkpoint_root = OUTPUT / "smoke" / "checkpoints" if smoke else CHECKPOINTS
    jobs = [(spec, arm) for spec in specs for arm in arms]
    distances = w85.b1_distance(population)
    start = time.time()
    if workers == 1:
        results = [run_active_trajectory(spec, arm, horizon, population, distances, checkpoint_root) for spec, arm in jobs]
    else:
        results = Parallel(n_jobs=workers, verbose=10)(
            delayed(run_active_trajectory)(spec, arm, horizon, population, distances, checkpoint_root) for spec, arm in jobs
        )
    require(all(item["complete"] for item in results), "not all active trajectories completed")
    report = {
        "status": "PASS",
        "smoke": smoke,
        "horizon": horizon,
        "workers": workers,
        "outer_runs": len(specs),
        "arms": list(arms),
        "trajectories": len(results),
        "elapsed_seconds": time.time() - start,
        "baseline_gate": gate,
    }
    write_json((OUTPUT / "smoke" if smoke else OUTPUT) / f"active_execution_H{horizon}.json", report)
    return report


def load_active_checkpoints(root: Path = CHECKPOINTS) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, mechanism = [], []
    for path in sorted(root.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        require(payload.get("complete"), f"incomplete checkpoint {path.name}")
        rows.extend(payload["rows"])
        mechanism.extend(payload["mechanism"])
    return pd.DataFrame(rows), pd.DataFrame(mechanism)


def active_path_metrics(rows: pd.DataFrame, horizon: int) -> pd.DataFrame:
    records = []
    for keys, group in rows.groupby(["run_id", "repeat", "fold", "arm", "prediction_model"], sort=True):
        run_id, repeat, fold, arm, model = keys
        q20 = group[group.subset.eq("B1_q20") & group.budget.between(16, 80)].sort_values("budget")
        q30 = group[group.subset.eq("B1_q30") & group.budget.between(16, 80)].sort_values("budget")
        require(q20.budget.tolist() == list(range(16, 81)), f"q20 grid incomplete {run_id} {model}")
        require(q30.budget.tolist() == list(range(16, 81)), f"q30 grid incomplete {run_id} {model}")
        model_horizon = int(group.budget.max())
        require(model_horizon <= horizon, f"model horizon exceeds requested aggregation horizon: {run_id} {model}")
        all_q20 = group[group.subset.eq("B1_q20") & group.budget.le(model_horizon)].sort_values("budget")
        crossing, observed = w85.persistent_crossing(all_q20, "accuracy", 0.80)
        budget40 = group[group.budget.eq(40)]
        records.append(
            {
                "run_id": run_id,
                "repeat": repeat,
                "fold": fold,
                "arm": arm,
                "prediction_model": model,
                "horizon": model_horizon,
                "B1_q20_AULC_16_80": w85.aulc(q20.rename(columns={"accuracy": "metric"}), "metric", 16, 80),
                "B1_q30_AULC_16_80": w85.aulc(q30.rename(columns={"accuracy": "metric"}), "metric", 16, 80),
                "persistent_q20_0_80_crossing": crossing,
                "persistent_q20_0_80_observed": observed,
                **{
                    f"budget40_{row.subset}_{metric}": getattr(row, metric)
                    for row in budget40.itertuples(index=False)
                    for metric in ("accuracy", "balanced_accuracy", "keyhole_recall", "conduction_recall", "false_negative", "false_positive")
                },
            }
        )
    return pd.DataFrame(records)


def active_contrast_summary(path_metrics: pd.DataFrame) -> pd.DataFrame:
    frozen = pd.read_csv(FROZEN / "run_level_metrics.csv")
    baseline_margin = frozen[frozen.arm.eq("binary_margin")][["run_id", "repeat", "fold", "B1_q20_AULC_16_80", "B1_q30_AULC_16_80"]].copy()
    baseline_margin["prediction_model"] = "frozen_4d_margin"
    baseline_random = (
        frozen[frozen.arm.eq("binary_random")]
        .groupby(["run_id", "repeat", "fold"], as_index=False)[["B1_q20_AULC_16_80", "B1_q30_AULC_16_80"]]
        .mean()
    )
    baseline_random["prediction_model"] = "matched_random_mean_of_30_paths"
    combined = pd.concat(
        [
            path_metrics[["run_id", "repeat", "fold", "prediction_model", "B1_q20_AULC_16_80", "B1_q30_AULC_16_80"]],
            baseline_margin,
            baseline_random,
        ],
        ignore_index=True,
    )
    repeat = combined.groupby(["repeat", "prediction_model"], as_index=False)[["B1_q20_AULC_16_80", "B1_q30_AULC_16_80"]].mean()
    rows = []
    rng = np.random.default_rng(seed_u32("active_contrast_bootstrap"))
    models = sorted(set(path_metrics.prediction_model))
    comparators = ("frozen_4d_margin", "matched_random_mean_of_30_paths")
    repeats = sorted(path_metrics.repeat.unique())
    require(repeats == list(range(1, 21)), "active contrasts require repeats 1..20")
    for model in models:
        for comparator in comparators:
            for metric in ("B1_q20_AULC_16_80", "B1_q30_AULC_16_80"):
                left_cube = (
                    path_metrics[path_metrics.prediction_model.eq(model)]
                    .pivot(index="repeat", columns="fold", values=metric)
                    .loc[repeats, list(range(1, 6))]
                    .to_numpy(float)
                )
                if comparator == "frozen_4d_margin":
                    right_cube = (
                        frozen[frozen.arm.eq("binary_margin")]
                        .pivot(index="repeat", columns="fold", values=metric)
                        .loc[repeats, list(range(1, 6))]
                        .to_numpy(float)
                    )
                    right_point = float(right_cube.mean())
                    right_repeat = right_cube.mean(axis=1)
                    draw_values = np.empty(BOOTSTRAP_DRAWS, dtype=float)
                    for draw in range(BOOTSTRAP_DRAWS):
                        repeat_pick = rng.integers(0, 20, size=20)
                        draw_values[draw] = float((left_cube[repeat_pick] - right_cube[repeat_pick]).mean())
                    bootstrap_method = "repeat blocks resampled; all five folds retained"
                else:
                    random = frozen[frozen.arm.eq("binary_random")]
                    random_cube = np.empty((20, 5, 30), dtype=float)
                    for repeat_index, repeat_id in enumerate(repeats):
                        for fold_index, fold_id in enumerate(range(1, 6)):
                            values = random[random.repeat.eq(repeat_id) & random.fold.eq(fold_id)].sort_values("continuation_id")[metric].to_numpy(float)
                            require(len(values) == 30, f"expected 30 Random continuations for r{repeat_id} f{fold_id}")
                            random_cube[repeat_index, fold_index] = values
                    right_point = float(random_cube.mean())
                    right_repeat = random_cube.mean(axis=(1, 2))
                    draw_values = np.empty(BOOTSTRAP_DRAWS, dtype=float)
                    fold_index = np.arange(5)[None, :, None]
                    for draw in range(BOOTSTRAP_DRAWS):
                        repeat_pick = rng.integers(0, 20, size=20)
                        continuation_pick = rng.integers(0, 30, size=(20, 5, 30))
                        sampled_random = random_cube[repeat_pick[:, None, None], fold_index, continuation_pick]
                        draw_values[draw] = float(left_cube[repeat_pick].mean() - sampled_random.mean())
                    bootstrap_method = "repeat blocks resampled; five folds retained; 30 Random continuations resampled within fold"
                left_point = float(left_cube.mean())
                difference = left_cube.mean(axis=1) - right_repeat
                rows.append(
                    {
                        "model": model,
                        "comparator": comparator,
                        "metric": metric,
                        "model_mean": left_point,
                        "comparator_mean": right_point,
                        "difference": left_point - right_point,
                        "ci_lower": float(np.quantile(draw_values, 0.025)),
                        "ci_upper": float(np.quantile(draw_values, 0.975)),
                        "repeat_blocks_positive": int((difference > 0).sum()),
                        "repeat_blocks": len(difference),
                        "bootstrap_method": bootstrap_method,
                    }
                )
    write_csv(OUTPUT / "active_repeat_metrics_with_frozen_baselines.csv", repeat)
    return pd.DataFrame(rows)


def aggregate_active(horizon: int) -> dict[str, Any]:
    rows, mechanism = load_active_checkpoints()
    require(not rows.empty and not mechanism.empty, "no active checkpoints found")
    expected_runs = rows.run_id.nunique()
    require(expected_runs == 100, f"full active aggregation requires 100 outer runs, found {expected_runs}")
    require(not mechanism.test_rows_available_to_acquisition.astype(bool).any(), "test rows entered acquisition")
    require(not mechanism.hidden_pool_labels_available_to_acquisition.astype(bool).any(), "hidden pool labels entered acquisition")
    require(not mechanism.B1_B2_B3_available_to_acquisition.astype(bool).any(), "B1/B2/B3 entered acquisition")
    require(not mechanism.threshold_fitted_from_all_pool_labels.astype(bool).any(), "full-pool label threshold entered acquisition")
    path = active_path_metrics(rows, horizon)
    contrasts = active_contrast_summary(path)
    curve = (
        rows[rows.subset.eq("B1_q20") & rows.budget.between(16, 80)]
        .groupby(["prediction_model", "budget"], as_index=False)
        .accuracy.mean()
        .rename(columns={"accuracy": "mean_accuracy"})
    )
    frozen_curve = pd.read_csv(PHASE1 / "learning_curve_summary_16_80.csv")
    frozen_curve["prediction_model"] = frozen_curve.arm.map(
        {"binary_margin": "frozen_4d_margin", "binary_random": "matched_random_mean_of_30_paths"}
    )
    curve = pd.concat([curve, frozen_curve[["prediction_model", "budget", "mean_accuracy"]]], ignore_index=True)
    write_csv(OUTPUT / "active_per_budget_metrics.csv.gz", rows)
    write_csv(OUTPUT / "active_information_flow.csv.gz", mechanism)
    write_csv(OUTPUT / "active_path_metrics.csv", path)
    write_csv(OUTPUT / "active_AULC_contrasts.csv", contrasts)
    write_csv(OUTPUT / "active_learning_curve_summary.csv", curve)
    report = {
        "status": "PASS",
        "outer_runs": expected_runs,
        "models": sorted(rows.prediction_model.unique()),
        "mechanism_rows": len(mechanism),
        "information_flow": {
            "test_rows_used": False,
            "hidden_pool_labels_used": False,
            "B1_B2_B3_used": False,
            "full_pool_label_threshold_used": False,
        },
        "inference_unit": "20 repeat blocks with all five folds retained together",
        "random_treatment": "30 saved Random continuations averaged only after per-path AULC; no synthetic mean crossing trajectory",
        "contrast_bootstrap": "repeat blocks resampled with all five folds retained; Random continuations resampled within fold",
        "model_horizons": {str(model): int(value) for model, value in path.groupby("prediction_model").horizon.max().items()},
    }
    write_json(OUTPUT / "active_aggregation_report.json", report)
    return report


MODEL_LABELS = {
    "log_h_logistic": "log(h) logistic",
    "logistic_M1": "4D logistic",
    "logistic_M3": "4D logistic + P×VX",
    "gpc_4d": "4D GPC",
    "gpc_5d_h_augmented": "5D GPC",
    "frozen_4d_margin": "4D Margin",
    "matched_random_mean_of_30_paths": "Random",
    "h_model_h_acquisition": "h query → h model",
    "gpc4_h_acquisition": "h query → 4D GPC",
    "gpc5_margin": "5D GPC Margin",
    "gpc4_assisted_product": "4D×h uncertainty",
}


def _save_figure(fig: plt.Figure, name: str) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / name
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def generate_figures() -> list[Path]:
    """Generate the eight declared, result-driven Phase 1.5 figures."""

    plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10})
    created: list[Path] = []

    exponents = pd.read_csv(OUTPUT / "empirical_exponent_summary.csv")
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    y = np.arange(len(exponents))
    estimate = exponents.estimate.to_numpy(float)
    ax.errorbar(
        estimate,
        y,
        xerr=[estimate - exponents.ci_lower.to_numpy(float), exponents.ci_upper.to_numpy(float) - estimate],
        fmt="o",
        color="#275dad",
        capsize=4,
        label="Empirical estimate (95% bootstrap CI)",
    )
    ax.scatter(exponents.theory, y, marker="D", color="#d1495b", label="Theory")
    ax.axvline(0, color="0.75", lw=0.8)
    ax.set_yticks(y, exponents.exponent)
    ax.set_xlabel("Exponent relative to power coefficient")
    ax.set_title("Theory and empirical discriminative direction")
    ax.legend(frameon=False, loc="best")
    created.append(_save_figure(fig, "01_theory_vs_empirical_exponents.png"))

    h = pd.read_csv(OUTPUT / "h_coordinates.csv")
    oof = pd.read_csv(OUTPUT / "screening_oof_unique_predictions.csv")
    calibration = json.loads((OUTPUT / "calibration_summary.json").read_text(encoding="utf-8"))
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.1))
    for label, color, name in ((0, "#4c78a8", "Conduction"), (1, "#e45756", "Keyhole")):
        axes[0].hist(h.loc[h.manual_has_keyhole.eq(label), "log_h_SI_reference"], bins=22, alpha=0.62, color=color, label=name)
    axes[0].set_xlabel("ln[h / (1 W s$^{1/2}$ m$^{-2}$)]")
    axes[0].set_ylabel("Simulation count")
    axes[0].set_title("Empirical separation along log(h)")
    axes[0].legend(frameon=False)
    rel = pd.DataFrame(calibration["reliability"])
    axes[1].plot([0, 1], [0, 1], "--", color="0.55", lw=1)
    axes[1].scatter(rel.mean_probability, rel.observed_keyhole_rate, s=18 + 2.2 * rel["count"], color="#275dad", alpha=0.8)
    axes[1].set(xlim=(0, 1), ylim=(0, 1), xlabel="Mean OOF probability", ylabel="Observed Keyhole rate")
    axes[1].set_title(f"OOF reliability (ECE={calibration['ECE']:.3f}; MCE={calibration['MCE']:.3f})")
    fig.suptitle("Retrospective simulator-domain log(h) model", y=1.02)
    created.append(_save_figure(fig, "02_logh_distribution_and_oof_calibration.png"))

    static = pd.read_csv(OUTPUT / "static_model_summary.csv")
    selected = ["log_h_logistic", "logistic_M1", "logistic_M3", "gpc_4d", "gpc_5d_h_augmented"]
    view = static[static.model.isin(selected) & static.subset.eq("full81")].set_index("model").loc[selected]
    fig, ax = plt.subplots(figsize=(8.2, 4.3))
    x = np.arange(len(selected)); width = 0.24
    for offset, metric, label, stem in (
        (-width, "mean_roc_auc", "ROC-AUC", "roc_auc"),
        (0, "mean_pr_auc", "PR-AUC", "pr_auc"),
        (width, "mean_balanced_accuracy", "Balanced accuracy", "balanced_accuracy"),
    ):
        values = view[metric].to_numpy(float)
        errors = np.vstack([values - view[f"ci_lower_{stem}"].to_numpy(float), view[f"ci_upper_{stem}"].to_numpy(float) - values])
        ax.bar(x + offset, values, width, yerr=errors, capsize=2, label=label)
    ax.set_xticks(x, [MODEL_LABELS[item] for item in selected], rotation=18, ha="right")
    ax.set_ylim(0.80, 1.005)
    ax.set_ylabel("Repeated held-out performance")
    ax.set_title("Leak-free static comparison on full held-out folds")
    ax.legend(frameon=False, ncol=3, loc="lower center")
    created.append(_save_figure(fig, "03_static_model_comparison.png"))

    view = static[static.model.isin(["log_h_logistic", "gpc_4d"])].copy()
    subset_order = ["full81", "B1_q30", "B1_q20"]
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.0), sharey=True)
    for ax, metric, title in zip(axes, ["mean_balanced_accuracy", "mean_keyhole_recall"], ["Balanced accuracy", "Keyhole recall"]):
        for model, color in (("log_h_logistic", "#e45756"), ("gpc_4d", "#4c78a8")):
            values = view[view.model.eq(model)].set_index("subset").loc[subset_order, metric]
            ax.plot(subset_order, values, marker="o", lw=2, color=color, label=MODEL_LABELS[model])
        ax.set_title(title); ax.set_ylim(0.65, 0.96); ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("Held-out performance")
    axes[1].legend(frameon=False)
    fig.suptitle("Performance degrades toward the empirical Fold-B1 boundary", y=1.02)
    created.append(_save_figure(fig, "04_boundary_difficulty.png"))

    residual = pd.read_csv(OUTPUT / "residual_case_analysis.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.2))
    base_colors = np.where(residual.truth.eq(1), "#e45756", "#4c78a8")
    for ax, xcol, xlabel in ((axes[0], "VX", "Scan speed VX (m/s)"), (axes[1], "LS_um", "Spot radius LS (µm)")):
        ax.scatter(residual[xcol], residual.P, c=base_colors, s=18, alpha=0.32, linewidths=0)
        special = residual[residual.h_wrong_gpc4_correct.astype(bool)]
        ax.scatter(special[xcol], special.P, facecolors="none", edgecolors="black", s=76, linewidths=1.3, label="h wrong; 4D GPC correct")
        ax.set(xlabel=xlabel, ylabel="Laser power P (W)")
    axes[0].scatter([], [], color="#4c78a8", s=30, label="Conduction")
    axes[0].scatter([], [], color="#e45756", s=30, label="Keyhole")
    axes[0].legend(frameon=False, loc="best", fontsize=8)
    axes[1].legend(frameon=False, loc="best", fontsize=8)
    fig.suptitle("Residual cases recovered by the 4D GPC (OOF ensemble)", y=1.02)
    created.append(_save_figure(fig, "05_residual_failure_map.png"))

    curve_path = OUTPUT / "active_learning_curve_summary.csv"
    require(curve_path.is_file(), "active aggregation required before active figures")
    curve = pd.read_csv(curve_path)
    order_models = ["matched_random_mean_of_30_paths", "frozen_4d_margin", "h_model_h_acquisition", "gpc4_h_acquisition", "gpc5_margin", "gpc4_assisted_product"]
    colors = ["#9d9d9d", "#275dad", "#e45756", "#f58518", "#54a24b", "#b279a2"]
    for name, limit, title in (("06_active_q20_learning_curves.png", 80, "Fold-B1-q20 active-learning curves"), ("07_active_q20_early_zoom.png", 40, "Early-budget Fold-B1-q20 zoom")):
        fig, ax = plt.subplots(figsize=(8.4, 4.7))
        for model, color in zip(order_models, colors):
            part = curve[curve.prediction_model.eq(model) & curve.budget.le(limit)].sort_values("budget")
            if not part.empty:
                ax.plot(part.budget, part.mean_accuracy, lw=2, color=color, label=MODEL_LABELS[model])
        ax.axhline(0.80, ls="--", lw=1, color="0.35")
        ax.set(xlabel="Queried simulations", ylabel="Mean q20 accuracy", xlim=(16, limit), ylim=(0.62, 0.90))
        ax.grid(alpha=0.22); ax.set_title(title)
        ax.legend(frameon=False, ncol=2, fontsize=8)
        created.append(_save_figure(fig, name))

    path_metrics = pd.read_csv(OUTPUT / "active_path_metrics.csv")
    baseline = pd.read_csv(PHASE1 / "terminal_metric_summary.csv")
    models = ["frozen_4d_margin", "h_model_h_acquisition", "gpc4_h_acquisition", "gpc5_margin", "gpc4_assisted_product"]
    subsets = ["full81", "B1_q30", "B1_q20"]
    metrics = ["accuracy", "balanced_accuracy", "keyhole_recall"]
    records = []
    for model in models:
        for subset in subsets:
            for metric in metrics:
                if model == "frozen_4d_margin":
                    row = baseline[(baseline.budget.eq(40)) & baseline.subset.eq(subset) & baseline.metric.eq(metric) & baseline.estimand.eq("binary_margin")]
                    value = float(row.point_estimate.iloc[0])
                else:
                    value = float(path_metrics[path_metrics.prediction_model.eq(model)][f"budget40_{subset}_{metric}"].mean())
                records.append({"model": model, "subset": subset, "metric": metric, "value": value})
    budget40 = pd.DataFrame(records)
    write_csv(OUTPUT / "budget40_model_comparison.csv", budget40)
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.3), sharey=True)
    x = np.arange(len(subsets)); width = 0.15
    for ax, metric in zip(axes, metrics):
        for idx, (model, color) in enumerate(zip(models, colors[1:])):
            values = budget40[(budget40.model.eq(model)) & budget40.metric.eq(metric)].set_index("subset").loc[subsets, "value"]
            ax.bar(x + (idx - 2) * width, values, width, color=color, label=MODEL_LABELS[model])
        ax.set_xticks(x, ["full", "q30", "q20"]); ax.set_title(metric.replace("_", " ").title()); ax.set_ylim(0.55, 1.0)
    axes[0].set_ylabel("Budget-40 held-out performance")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=8, ncol=5, loc="lower center", bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Budget 40: global and empirical-boundary performance", y=1.02)
    created.append(_save_figure(fig, "08_budget40_comparison.png"))

    manifest = pd.DataFrame(
        {
            "figure": [path.name for path in created],
            "sha256": [sha256_file(path) for path in created],
            "bytes": [path.stat().st_size for path in created],
        }
    )
    write_csv(OUTPUT / "figure_manifest.csv", manifest)
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("audit", "static", "active", "aggregate", "figures"))
    parser.add_argument("--horizon", type=int, default=80)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--arms", nargs="*", default=list(AL_ARMS))
    args = parser.parse_args()
    if args.command == "audit":
        print(audit_inputs()[2])
    elif args.command == "static":
        print(run_static(workers=args.workers))
    elif args.command == "active":
        print(run_active(horizon=args.horizon, workers=args.workers, arms=args.arms))
    elif args.command == "aggregate":
        print(aggregate_active(args.horizon))
    else:
        print([str(path) for path in generate_figures()])


if __name__ == "__main__":
    main()
