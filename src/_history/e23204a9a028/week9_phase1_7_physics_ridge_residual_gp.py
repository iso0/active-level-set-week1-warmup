"""Week 9 Phase 1.7: physics-ridge plus low-amplitude 4D residual GP.

The only new scientific arm is an additive latent classifier

    f(x) = beta_0 + beta_h z(log h(x)) + r(x),

where r is an exact scikit-learn Laplace GPC component with a Matern-3/2
kernel on the standardized four-dimensional input. Historical Week 8.5 and
Phase 1.5 artifacts are read-only comparators.
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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.special import expit
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.gaussian_process.kernels import Hyperparameter, Kernel
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

from src import week7_phase6_real_data_boundary_active_level_set as p6
from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_5_h_physics_confirmation as p15


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase1_7_physics_ridge_residual_gp"
TABLES = OUTPUT / "tables"
FIGURES = OUTPUT / "figures"
CHECKPOINTS = OUTPUT / "checkpoints"
SMOKE = OUTPUT / "smoke"
NOTEBOOK = ROOT / "notebooks" / "week_09" / "03_week9_phase1_7_physics_ridge_residual_gp.ipynb"
FROZEN = ROOT / "outputs" / "week8_5_frozen_confirmation"
PHASE1 = ROOT / "outputs" / "week9_phase1_close_week8"
PHASE15 = ROOT / "outputs" / "week9_phase1_5_h_physics_confirmation"
FEATURES = ("P", "VX", "LS", "ST")
STARTING_SHA = "b36a815e12dfa872c20a050228e0545f18c443ef"
BRANCH = "codex/week9-phase1-7-physics-ridge-residual-gp"
SEED_ROOT = "week9_phase1_7_physics_ridge_residual_gp|v1"
PRIMARY_HORIZON = 80
MATERN_LENGTH_SCALE = 1.5
RESIDUAL_SD_BOUNDS = (0.05, 1.0)
RESIDUAL_VARIANCE_BOUNDS = tuple(value**2 for value in RESIDUAL_SD_BOUNDS)
LENGTH_SCALE_BOUNDS = (0.25, 4.0)
PHYSICS_PRIOR_VARIANCE = 25.0
BOOTSTRAP_DRAWS = 5000
EPS = 1e-12


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
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, (np.integer, np.floating)):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for attempt in range(20):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.05 * (attempt + 1))


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    frame.to_csv(temporary, index=False, lineterminator="\n", compression="gzip" if path.suffix == ".gz" else None)
    temporary.replace(path)


def load_population_and_specs() -> tuple[pd.DataFrame, list[w85.SplitSpec]]:
    population = w85.load_population().reset_index(drop=True)
    specs = w85.build_splits(population)
    require(len(population) == 405, "canonical population drift")
    require(int(population.has_keyhole.sum()) == 73, "canonical Keyhole count drift")
    require(len(specs) == 100, "frozen outer-run count drift")
    return population, specs


def log_h(population: pd.DataFrame) -> np.ndarray:
    p = population.P.to_numpy(float)
    velocity = population.VX.to_numpy(float)
    radius = population.LS.to_numpy(float)
    require((p > 0).all() and (velocity > 0).all() and (radius > 0).all(), "h inputs must be positive")
    return np.log(p / np.sqrt(velocity * radius**3))


def baseline_gate() -> dict[str, Any]:
    population, specs = load_population_and_specs()
    frozen = pd.read_csv(FROZEN / "run_level_metrics.csv")
    margin = frozen[frozen.arm.eq("binary_margin")]
    random = frozen[frozen.arm.eq("binary_random")]
    margin_mean = float(margin.B1_q20_AULC_16_80.mean())
    random_mean = float(random.B1_q20_AULC_16_80.mean())
    require(abs(margin_mean - 0.8135202205882354) < 1e-10, "frozen Margin AULC mismatch")
    require(abs(random_mean - 0.7762204350490195) < 1e-10, "frozen Random AULC mismatch")

    split_manifest = pd.read_csv(FROZEN / "split_manifest.csv")
    initial_manifest = pd.read_csv(FROZEN / "initial_design_manifest.csv")
    split_matches = 0
    initial_matches = 0
    for spec in specs:
        expected_train = set(split_manifest[(split_manifest.run_id.eq(spec.run_id)) & split_manifest.role.eq("training_pool")].population_row_index.astype(int))
        expected_test = set(split_manifest[(split_manifest.run_id.eq(spec.run_id)) & split_manifest.role.eq("untouched_test")].population_row_index.astype(int))
        if expected_train == set(spec.train_indices) and expected_test == set(spec.test_indices):
            split_matches += 1
        expected_initial = initial_manifest[initial_manifest.run_id.eq(spec.run_id)].sort_values("query_order").population_row_index.astype(int).tolist()
        if expected_initial == w85.initial_design(spec, population):
            initial_matches += 1
    require(split_matches == 100 and initial_matches == 100, "frozen split or initial-design mismatch")
    result = {
        "status": "PASS",
        "starting_sha": STARTING_SHA,
        "outer_runs": len(specs),
        "split_exact_matches": split_matches,
        "initial_design_exact_matches": initial_matches,
        "margin_q20_AULC_16_80": margin_mean,
        "matched_random_q20_AULC_16_80": random_mean,
        "frozen_protocol_sha256": p15.frozen_protocol_hash(),
    }
    write_json(OUTPUT / "baseline_gate.json", result)
    return result


def matern32(xa: np.ndarray, xb: np.ndarray, length_scale: float = MATERN_LENGTH_SCALE) -> np.ndarray:
    xa = np.asarray(xa, dtype=float)
    xb = np.asarray(xb, dtype=float)
    squared = np.maximum(
        np.sum(xa**2, axis=1)[:, None] + np.sum(xb**2, axis=1)[None, :] - 2.0 * xa @ xb.T,
        0.0,
    )
    radius = np.sqrt(squared) / float(length_scale)
    root3 = math.sqrt(3.0)
    return (1.0 + root3 * radius) * np.exp(-root3 * radius)


class PhysicsRidgeResidualKernel(Kernel):
    """Additive covariance: random intercept + linear log(h) ridge + 4D Matern residual."""

    def __init__(
        self,
        residual_variance: float = 0.09,
        length_scale: float = MATERN_LENGTH_SCALE,
        residual_variance_bounds: tuple[float, float] = RESIDUAL_VARIANCE_BOUNDS,
        length_scale_bounds: tuple[float, float] = LENGTH_SCALE_BOUNDS,
        physics_prior_variance: float = PHYSICS_PRIOR_VARIANCE,
    ) -> None:
        self.residual_variance = residual_variance
        self.length_scale = length_scale
        self.residual_variance_bounds = residual_variance_bounds
        self.length_scale_bounds = length_scale_bounds
        self.physics_prior_variance = physics_prior_variance

    @property
    def hyperparameter_residual_variance(self) -> Hyperparameter:
        return Hyperparameter("residual_variance", "numeric", self.residual_variance_bounds)

    @property
    def hyperparameter_length_scale(self) -> Hyperparameter:
        return Hyperparameter("length_scale", "numeric", self.length_scale_bounds)

    def __call__(self, X: np.ndarray, Y: np.ndarray | None = None, eval_gradient: bool = False):
        X = np.atleast_2d(np.asarray(X, dtype=float))
        Y_is_none = Y is None
        Y = X if Y_is_none else np.atleast_2d(np.asarray(Y, dtype=float))
        require(X.shape[1] == 5 and Y.shape[1] == 5, "additive kernel expects [z4, z(logh)]")
        x4, h = X[:, :4], X[:, 4]
        y4, yh = Y[:, :4], Y[:, 4]
        squared = np.maximum(
            np.sum(x4**2, axis=1)[:, None] + np.sum(y4**2, axis=1)[None, :] - 2.0 * x4 @ y4.T,
            0.0,
        )
        scaled = math.sqrt(3.0) * np.sqrt(squared) / float(self.length_scale)
        residual_base = (1.0 + scaled) * np.exp(-scaled)
        residual = float(self.residual_variance) * residual_base
        physics = float(self.physics_prior_variance) * (1.0 + h[:, None] * yh[None, :])
        covariance = physics + residual
        if not eval_gradient:
            return covariance
        if not Y_is_none:
            raise ValueError("Gradient can only be evaluated when Y is None")
        grad_variance = residual
        grad_length = float(self.residual_variance) * scaled**2 * np.exp(-scaled)
        return covariance, np.stack([grad_length, grad_variance], axis=2)

    def diag(self, X: np.ndarray) -> np.ndarray:
        X = np.atleast_2d(np.asarray(X, dtype=float))
        return float(self.physics_prior_variance) * (1.0 + X[:, 4] ** 2) + float(self.residual_variance)

    def is_stationary(self) -> bool:
        return False

    def __repr__(self) -> str:
        return (
            "PhysicsRidgeResidualKernel("
            f"residual_sd={math.sqrt(float(self.residual_variance)):.4g}, "
            f"length_scale={float(self.length_scale):.4g}, "
            f"physics_prior_sd={math.sqrt(float(self.physics_prior_variance)):.4g})"
        )


@dataclass
class AdditiveFit:
    model: GaussianProcessClassifier
    x_scaler: StandardScaler
    h_scaler: StandardScaler
    revealed_indices: np.ndarray
    x_train_transformed: np.ndarray
    y_train: np.ndarray
    warnings: str
    fit_status: str

    @property
    def kernel(self) -> PhysicsRidgeResidualKernel:
        return self.model.kernel_

    @property
    def residual_sd(self) -> float:
        return math.sqrt(float(self.kernel.residual_variance))

    @property
    def length_scale(self) -> float:
        return float(self.kernel.length_scale)


def transform_additive_inputs(
    x4: np.ndarray,
    logh_values: np.ndarray,
    x_scaler: StandardScaler,
    h_scaler: StandardScaler,
) -> np.ndarray:
    return np.column_stack(
        [
            x_scaler.transform(np.asarray(x4, dtype=float)),
            h_scaler.transform(np.asarray(logh_values, dtype=float).reshape(-1, 1)).ravel(),
        ]
    )


def fit_additive(
    x4: np.ndarray,
    logh_values: np.ndarray,
    labels: np.ndarray,
    revealed_indices: Sequence[int],
    training_pool_indices: Sequence[int],
    seed: int,
) -> AdditiveFit:
    revealed = np.asarray(revealed_indices, dtype=int)
    training_pool = np.asarray(training_pool_indices, dtype=int)
    x_scaler = StandardScaler().fit(x4[training_pool])
    h_scaler = StandardScaler().fit(logh_values[training_pool].reshape(-1, 1))
    transformed = transform_additive_inputs(x4[revealed], logh_values[revealed], x_scaler, h_scaler)
    kernel = PhysicsRidgeResidualKernel()
    model = GaussianProcessClassifier(
        kernel=kernel,
        optimizer="fmin_l_bfgs_b",
        n_restarts_optimizer=0,
        max_iter_predict=100,
        warm_start=False,
        random_state=int(seed),
    )
    fit_status = "optimized_additive_laplace"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            model.fit(transformed, labels[revealed])
        except (np.linalg.LinAlgError, ValueError, FloatingPointError):
            fit_status = "fixed_additive_laplace_fallback"
            model = GaussianProcessClassifier(
                kernel=PhysicsRidgeResidualKernel(residual_variance=0.35**2, length_scale=MATERN_LENGTH_SCALE),
                optimizer=None,
                n_restarts_optimizer=0,
                max_iter_predict=100,
                random_state=int(seed),
            )
            model.fit(transformed, labels[revealed])
    warning_text = " | ".join(str(item.message) for item in caught if issubclass(item.category, ConvergenceWarning))
    return AdditiveFit(model, x_scaler, h_scaler, revealed, transformed, labels[revealed].astype(int), warning_text, fit_status)


def additive_components(fit: AdditiveFit, x4: np.ndarray, logh_values: np.ndarray) -> dict[str, np.ndarray]:
    transformed = transform_additive_inputs(x4, logh_values, fit.x_scaler, fit.h_scaler)
    base = fit.model.base_estimator_
    alpha = fit.y_train.astype(float) - np.asarray(base.pi_, dtype=float)
    train_h = fit.x_train_transformed[:, 4]
    target_h = transformed[:, 4]
    beta_0 = PHYSICS_PRIOR_VARIANCE * float(alpha.sum())
    beta_h = PHYSICS_PRIOR_VARIANCE * float(train_h @ alpha)
    physics_latent = beta_0 + beta_h * target_h
    residual_base = matern32(fit.x_train_transformed[:, :4], transformed[:, :4], fit.length_scale)
    residual_latent = float(fit.kernel.residual_variance) * residual_base.T @ alpha
    combined_latent = physics_latent + residual_latent
    latent_mean, latent_variance = fit.model.latent_mean_and_variance(transformed)
    require(np.allclose(combined_latent, latent_mean, rtol=2e-6, atol=2e-6), "additive component decomposition mismatch")
    probability = fit.model.predict_proba(transformed)[:, 1]
    return {
        "physics_latent": physics_latent,
        "residual_latent": residual_latent,
        "combined_latent": combined_latent,
        "latent_variance": latent_variance,
        "probability": probability,
        "physics_probability": expit(physics_latent),
        "beta_0": np.full(len(transformed), beta_0),
        "beta_h": np.full(len(transformed), beta_h),
    }


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
        "false_negative": int(fn),
        "false_positive": int(fp),
        "true_negative": int(tn),
        "true_positive": int(tp),
        "row_count": int(len(truth)),
    }


def subset_flags(spec: w85.SplitSpec, population: pd.DataFrame, distances: np.ndarray) -> dict[str, np.ndarray]:
    flags = w85.boundary_flags(spec, population, distances)
    return {"full81": np.ones(len(spec.test_indices), dtype=bool), "B1_q30": flags["B1_q30"], "B1_q20": flags["B1_q20"]}


def fit_diagnostic_row(fit: AdditiveFit) -> dict[str, Any]:
    return {
        "fit_status": fit.fit_status,
        "kernel": repr(fit.kernel),
        "residual_sd": fit.residual_sd,
        "length_scale": fit.length_scale,
        "residual_sd_lower_bound_hit": bool(np.isclose(fit.residual_sd, RESIDUAL_SD_BOUNDS[0], rtol=0, atol=5e-4)),
        "residual_sd_upper_bound_hit": bool(np.isclose(fit.residual_sd, RESIDUAL_SD_BOUNDS[1], rtol=0, atol=5e-4)),
        "length_scale_lower_bound_hit": bool(np.isclose(fit.length_scale, LENGTH_SCALE_BOUNDS[0], rtol=0, atol=5e-4)),
        "length_scale_upper_bound_hit": bool(np.isclose(fit.length_scale, LENGTH_SCALE_BOUNDS[1], rtol=0, atol=5e-4)),
        "convergence_warning": bool(fit.warnings),
        "warning_text": fit.warnings,
    }


def _static_one(spec: w85.SplitSpec, population: pd.DataFrame, distances: np.ndarray) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    x4 = population.loc[:, FEATURES].to_numpy(float)
    lh = log_h(population)
    labels = population.has_keyhole.astype(int).to_numpy()
    train = np.asarray(spec.train_indices, dtype=int)
    test = np.asarray(spec.test_indices, dtype=int)
    fit = fit_additive(x4, lh, labels, train, train, seed_u32("static", spec.run_id))
    components = additive_components(fit, x4[test], lh[test])
    flags = subset_flags(spec, population, distances)
    metric_rows = []
    for subset, flag in flags.items():
        metric_rows.append(
            {
                "run_id": spec.run_id,
                "repeat": spec.repeat,
                "fold": spec.fold,
                "model": "physics_ridge_residual_gp",
                "subset": subset,
                **metric_values(labels[test][flag], components["probability"][flag]),
                **fit_diagnostic_row(fit),
            }
        )
    prediction_rows = []
    for local, population_index in enumerate(test):
        prediction_rows.append(
            {
                "run_id": spec.run_id,
                "repeat": spec.repeat,
                "fold": spec.fold,
                "population_row_index": int(population_index),
                "experiment_name": str(population.iloc[population_index].experiment_name),
                "truth": int(labels[population_index]),
                "P": float(population.iloc[population_index].P),
                "VX": float(population.iloc[population_index].VX),
                "LS": float(population.iloc[population_index].LS),
                "ST": float(population.iloc[population_index].ST),
                "log_h": float(lh[population_index]),
                "physics_latent": float(components["physics_latent"][local]),
                "residual_latent": float(components["residual_latent"][local]),
                "combined_latent": float(components["combined_latent"][local]),
                "physics_probability": float(components["physics_probability"][local]),
                "combined_probability": float(components["probability"][local]),
                "beta_0": float(components["beta_0"][local]),
                "beta_h": float(components["beta_h"][local]),
                "is_q30": bool(flags["B1_q30"][local]),
                "is_q20": bool(flags["B1_q20"][local]),
            }
        )
    return metric_rows, prediction_rows


def _repeat_metrics_from_predictions(predictions: pd.DataFrame, model: str) -> pd.DataFrame:
    records = []
    for repeat, repeat_group in predictions.groupby("repeat", sort=True):
        for subset, flag_column in (("full81", None), ("B1_q30", "is_q30"), ("B1_q20", "is_q20")):
            group = repeat_group if flag_column is None else repeat_group[repeat_group[flag_column].astype(bool)]
            records.append(
                {
                    "repeat": int(repeat),
                    "model": model,
                    "subset": subset,
                    **metric_values(group.truth.to_numpy(int), group.combined_probability.to_numpy(float)),
                }
            )
    return pd.DataFrame(records)


def _summary_from_repeat_metrics(repeat_metrics: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(seed_u32("static_summary_bootstrap"))
    records = []
    metrics = ("roc_auc", "pr_auc", "balanced_accuracy", "keyhole_recall", "conduction_recall")
    for (model, subset), group in repeat_metrics.groupby(["model", "subset"], sort=True):
        row: dict[str, Any] = {"model": model, "subset": subset, "repeat_blocks": len(group)}
        for metric in metrics:
            values = group.sort_values("repeat")[metric].to_numpy(float)
            draws = values[rng.integers(0, len(values), size=(BOOTSTRAP_DRAWS, len(values)))].mean(axis=1)
            row[f"mean_{metric}"] = float(values.mean())
            row[f"ci_lower_{metric}"] = float(np.quantile(draws, 0.025))
            row[f"ci_upper_{metric}"] = float(np.quantile(draws, 0.975))
        records.append(row)
    return pd.DataFrame(records)


def run_static(*, workers: int = 1, limit_specs: int | None = None, smoke: bool = False) -> dict[str, Any]:
    gate = baseline_gate()
    require(gate["status"] == "PASS", "baseline gate failed")
    population, specs = load_population_and_specs()
    if limit_specs is not None:
        specs = specs[:limit_specs]
    distances = w85.b1_distance(population)
    start = time.time()
    if workers == 1:
        results = [_static_one(spec, population, distances) for spec in specs]
    else:
        results = Parallel(n_jobs=workers, verbose=10)(delayed(_static_one)(spec, population, distances) for spec in specs)
    metric_rows = [row for metrics, _ in results for row in metrics]
    prediction_rows = [row for _, predictions in results for row in predictions]
    destination = SMOKE if smoke else TABLES
    write_csv(destination / "static_fold_metrics.csv", pd.DataFrame(metric_rows))
    write_csv(destination / "static_oof_predictions.csv.gz", pd.DataFrame(prediction_rows))
    report = {
        "status": "PASS",
        "smoke": smoke,
        "outer_runs": len(specs),
        "elapsed_seconds": time.time() - start,
        "model": "exact additive Laplace GPC with linear physics kernel and constrained 4D Matern-3/2 residual",
    }
    if not smoke:
        predictions = pd.DataFrame(prediction_rows)
        new_repeat = _repeat_metrics_from_predictions(predictions, "physics_ridge_residual_gp")
        historical = pd.read_csv(PHASE15 / "static_repeat_metrics.csv")
        historical = historical[historical.model.isin(["log_h_logistic", "gpc_4d"])].copy()
        historical["source"] = "reused_phase1_5"
        new_repeat["source"] = "new_phase1_7"
        combined = pd.concat([historical, new_repeat], ignore_index=True, sort=False)
        write_csv(TABLES / "static_repeat_metrics.csv", combined)
        write_csv(TABLES / "static_model_summary.csv", _summary_from_repeat_metrics(combined))
        diagnostics = pd.DataFrame(metric_rows)
        report.update(
            {
                "fallback_fits": int(diagnostics.fit_status.ne("optimized_additive_laplace").sum() / 3),
                "convergence_warning_fits": int(diagnostics.convergence_warning.sum() / 3),
                "residual_sd_upper_bound_fits": int(diagnostics.residual_sd_upper_bound_hit.sum() / 3),
                "length_scale_bound_fits": int((diagnostics.length_scale_lower_bound_hit | diagnostics.length_scale_upper_bound_hit).sum() / 3),
            }
        )
    write_json((SMOKE if smoke else OUTPUT) / "static_execution_report.json", report)
    return report


def _mechanism_summary(
    spec: w85.SplitSpec,
    budget: int,
    fit: AdditiveFit,
    truth: np.ndarray,
    components: dict[str, np.ndarray],
    flags: dict[str, np.ndarray],
) -> list[dict[str, Any]]:
    physics_prediction = components["physics_latent"] >= 0.0
    combined_prediction = components["combined_latent"] >= 0.0
    rows = []
    for subset, flag in flags.items():
        subset_truth = truth[flag]
        physics = physics_prediction[flag]
        combined = combined_prediction[flag]
        changed = physics != combined
        corrected = (physics != subset_truth) & (combined == subset_truth)
        worsened = (physics == subset_truth) & (combined != subset_truth)
        residual = components["residual_latent"][flag]
        trend = components["physics_latent"][flag]
        residual_rms = float(np.sqrt(np.mean(residual**2)))
        trend_rms = float(np.sqrt(np.mean(trend**2)))
        rows.append(
            {
                "run_id": spec.run_id,
                "repeat": spec.repeat,
                "fold": spec.fold,
                "budget": budget,
                "subset": subset,
                "beta_0": float(components["beta_0"][0]),
                "beta_h": float(components["beta_h"][0]),
                "physics_mean_abs_latent": float(np.mean(np.abs(trend))),
                "physics_rms_latent": trend_rms,
                "residual_mean_abs_latent": float(np.mean(np.abs(residual))),
                "residual_rms_latent": residual_rms,
                "residual_to_physics_rms_ratio": residual_rms / max(trend_rms, EPS),
                "residual_sd": fit.residual_sd,
                "length_scale": fit.length_scale,
                "class_changed_count": int(changed.sum()),
                "class_changed_fraction": float(changed.mean()),
                "corrected_count": int(corrected.sum()),
                "worsened_count": int(worsened.sum()),
                "keyholes_missed_by_physics": int(((subset_truth == 1) & ~physics).sum()),
                "keyholes_recovered_by_residual": int(((subset_truth == 1) & ~physics & combined).sum()),
                "new_keyhole_misses_induced": int(((subset_truth == 1) & physics & ~combined).sum()),
                **fit_diagnostic_row(fit),
            }
        )
    return rows


def _case_rows(
    spec: w85.SplitSpec,
    budget: int,
    population: pd.DataFrame,
    test: np.ndarray,
    truth: np.ndarray,
    lh: np.ndarray,
    components: dict[str, np.ndarray],
    flags: dict[str, np.ndarray],
) -> list[dict[str, Any]]:
    physics_prediction = components["physics_latent"] >= 0.0
    combined_prediction = components["combined_latent"] >= 0.0
    rows = []
    for local, population_index in enumerate(test):
        physics_correct = bool(physics_prediction[local] == bool(truth[local]))
        combined_correct = bool(combined_prediction[local] == bool(truth[local]))
        if not physics_correct and combined_correct:
            category = "physics_wrong_combined_correct"
        elif physics_correct and not combined_correct:
            category = "physics_correct_combined_wrong"
        elif physics_correct:
            category = "both_correct"
        else:
            category = "both_wrong"
        row = population.iloc[population_index]
        rows.append(
            {
                "run_id": spec.run_id,
                "repeat": spec.repeat,
                "fold": spec.fold,
                "budget": budget,
                "population_row_index": int(population_index),
                "experiment_name": str(row.experiment_name),
                "truth": int(truth[local]),
                "P": float(row.P),
                "VX": float(row.VX),
                "LS": float(row.LS),
                "LS_um": float(row.LS * 1e6),
                "ST": float(row.ST),
                "log_h": float(lh[population_index]),
                "physics_probability": float(components["physics_probability"][local]),
                "physics_latent": float(components["physics_latent"][local]),
                "residual_correction": float(components["residual_latent"][local]),
                "combined_latent": float(components["combined_latent"][local]),
                "combined_probability": float(components["probability"][local]),
                "category": category,
                "is_q30": bool(flags["B1_q30"][local]),
                "is_q20": bool(flags["B1_q20"][local]),
            }
        )
    return rows


def active_checkpoint_path(spec: w85.SplitSpec, root: Path) -> Path:
    return root / f"{spec.run_id}__physics_ridge_residual_gp.json"


def run_active_trajectory(
    spec: w85.SplitSpec,
    horizon: int,
    population: pd.DataFrame,
    distances: np.ndarray,
    checkpoint_root: Path,
) -> dict[str, Any]:
    train = np.asarray(spec.train_indices, dtype=int)
    test = np.asarray(spec.test_indices, dtype=int)
    labels = population.has_keyhole.astype(int).to_numpy()
    x4 = population.loc[:, FEATURES].to_numpy(float)
    lh = log_h(population)
    flags = subset_flags(spec, population, distances)
    path = active_checkpoint_path(spec, checkpoint_root)
    if path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
        require(payload["run_id"] == spec.run_id, "checkpoint run identity drift")
        queried = [int(value) for value in payload["queried_indices"]]
        metric_rows = list(payload["metric_rows"])
        diagnostic_rows = list(payload["diagnostic_rows"])
        acquisition_rows = list(payload["acquisition_rows"])
        case_rows = list(payload["case_rows"])
    else:
        queried = w85.initial_design(spec, population)
        metric_rows, diagnostic_rows, acquisition_rows, case_rows = [], [], [], []
    require(queried[:16] == w85.initial_design(spec, population), "initial design prefix drift")
    require(set(queried).issubset(set(train)), "checkpoint query outside training pool")
    completed = {int(row["budget"]) for row in diagnostic_rows if row["subset"] == "full81"}
    allowed = list(range(16, horizon + 1)) if horizon < 80 else w85.declared_budgets(horizon)
    for budget in range(len(queried), horizon + 1):
        revealed = np.asarray(queried, dtype=int)
        fit = fit_additive(x4, lh, labels, revealed, train, seed_u32("active", spec.run_id, budget))
        test_components = additive_components(fit, x4[test], lh[test])
        if budget in allowed and budget not in completed:
            truth = labels[test]
            for subset, flag in flags.items():
                metric_rows.append(
                    {
                        "run_id": spec.run_id,
                        "repeat": spec.repeat,
                        "fold": spec.fold,
                        "arm": "physics_ridge_residual_gp_margin",
                        "prediction_model": "physics_ridge_residual_gp",
                        "budget": budget,
                        "subset": subset,
                        "queried_keyhole": int(labels[revealed].sum()),
                        "queried_conduction": int(len(revealed) - labels[revealed].sum()),
                        **metric_values(truth[flag], test_components["probability"][flag]),
                    }
                )
            diagnostic_rows.extend(_mechanism_summary(spec, budget, fit, truth, test_components, flags))
            if budget in (40, 80):
                case_rows.extend(_case_rows(spec, budget, population, test, truth, lh, test_components, flags))
            completed.add(budget)

        if budget < horizon:
            candidate = np.setdiff1d(train, revealed, assume_unique=False)
            candidate_components = additive_components(fit, x4[candidate], lh[candidate])
            next_index = p15.choose_gpc_margin(candidate, candidate_components["probability"])
            require(next_index in set(train) and next_index not in queried, "active chooser violated pool membership")
            acquisition_rows.append(
                {
                    "run_id": spec.run_id,
                    "repeat": spec.repeat,
                    "fold": spec.fold,
                    "selection_budget": budget + 1,
                    "selected_population_row_index": int(next_index),
                    "selected_experiment_name": str(population.iloc[next_index].experiment_name),
                    "selected_label_revealed_after_selection": int(labels[next_index]),
                    "acquisition_definition": "combined-model predictive probability closest to 0.5",
                    "candidate_pool_role": "outer_training_pool_only",
                    "test_rows_available_to_acquisition": False,
                    "hidden_pool_labels_available_to_acquisition": False,
                    "B1_q20_q30_available_to_acquisition": False,
                    "external_h_threshold_used": False,
                }
            )
            queried.append(int(next_index))
        if budget % 5 == 0 or budget == horizon:
            write_json(
                path,
                {
                    "run_id": spec.run_id,
                    "repeat": spec.repeat,
                    "fold": spec.fold,
                    "horizon": horizon,
                    "complete": budget == horizon,
                    "queried_indices": queried,
                    "metric_rows": metric_rows,
                    "diagnostic_rows": diagnostic_rows,
                    "acquisition_rows": acquisition_rows,
                    "case_rows": case_rows,
                },
            )
    return {"run_id": spec.run_id, "complete": True, "queries": len(queried)}


def run_active(*, horizon: int = PRIMARY_HORIZON, workers: int = 1, limit_specs: int | None = None, smoke: bool = False) -> dict[str, Any]:
    require((smoke and 16 <= horizon <= 80) or horizon == PRIMARY_HORIZON, "primary active horizon must be 80")
    gate = baseline_gate()
    require(gate["status"] == "PASS", "baseline gate failed")
    population, specs = load_population_and_specs()
    if limit_specs is not None:
        specs = specs[:limit_specs]
    distances = w85.b1_distance(population)
    checkpoint_root = SMOKE / "checkpoints" if smoke else CHECKPOINTS
    start = time.time()
    if workers == 1:
        results = [run_active_trajectory(spec, horizon, population, distances, checkpoint_root) for spec in specs]
    else:
        results = Parallel(n_jobs=workers, verbose=10)(
            delayed(run_active_trajectory)(spec, horizon, population, distances, checkpoint_root) for spec in specs
        )
    require(all(item["complete"] for item in results), "active trajectory incomplete")
    report = {
        "status": "PASS",
        "smoke": smoke,
        "horizon": horizon,
        "outer_runs": len(specs),
        "trajectories": len(results),
        "elapsed_seconds": time.time() - start,
        "new_arm": "physics_ridge_residual_gp_margin",
        "historical_comparators_reused": ["frozen_4d_margin", "matched_random", "phase1_5_h_only", "phase1_5_5d_gpc"],
    }
    write_json((SMOKE if smoke else OUTPUT) / f"active_execution_H{horizon}.json", report)
    return report


def load_active_checkpoints(root: Path = CHECKPOINTS) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metrics, diagnostics, acquisition, cases = [], [], [], []
    for path in sorted(root.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        require(payload.get("complete"), f"incomplete checkpoint {path.name}")
        metrics.extend(payload["metric_rows"])
        diagnostics.extend(payload["diagnostic_rows"])
        acquisition.extend(payload["acquisition_rows"])
        cases.extend(payload["case_rows"])
    return pd.DataFrame(metrics), pd.DataFrame(diagnostics), pd.DataFrame(acquisition), pd.DataFrame(cases)


def active_path_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    records = []
    for keys, group in metrics.groupby(["run_id", "repeat", "fold"], sort=True):
        run_id, repeat, fold = keys
        row: dict[str, Any] = {"run_id": run_id, "repeat": int(repeat), "fold": int(fold), "model": "physics_ridge_residual_gp"}
        for subset in ("B1_q20", "B1_q30"):
            path = group[group.subset.eq(subset)].sort_values("budget")
            require(path.budget.tolist() == list(range(16, 81)), f"incomplete {subset} path {run_id}")
            row[f"{subset}_AULC_16_80"] = w85.aulc(path.rename(columns={"accuracy": "metric"}), "metric", 16, 80)
        records.append(row)
    return pd.DataFrame(records)


def _bootstrap_primary(path: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    frozen = pd.read_csv(FROZEN / "run_level_metrics.csv")
    baseline = frozen[frozen.arm.eq("binary_margin")][
        ["run_id", "repeat", "fold", "B1_q20_AULC_16_80", "B1_q30_AULC_16_80"]
    ].copy()
    merged = path.merge(baseline, on=["run_id", "repeat", "fold"], suffixes=("_new", "_baseline"), validate="one_to_one")
    repeat_rows = []
    summary_rows = []
    rng = np.random.default_rng(seed_u32("primary_repeat_block_bootstrap"))
    for endpoint in ("B1_q20_AULC_16_80", "B1_q30_AULC_16_80"):
        merged[f"delta_{endpoint}"] = merged[f"{endpoint}_new"] - merged[f"{endpoint}_baseline"]
        repeat_delta = merged.groupby("repeat", as_index=False)[f"delta_{endpoint}"].mean().sort_values("repeat")
        values = repeat_delta[f"delta_{endpoint}"].to_numpy(float)
        draws = values[rng.integers(0, 20, size=(BOOTSTRAP_DRAWS, 20))].mean(axis=1)
        mean = float(values.mean())
        lower = float(np.quantile(draws, 0.025))
        upper = float(np.quantile(draws, 0.975))
        if endpoint.startswith("B1_q20"):
            decision = "PASS" if mean >= 0.010 and lower > 0 else ("QUALIFY" if mean > 0 else "FAIL")
        else:
            decision = "secondary"
        summary_rows.append(
            {
                "endpoint": endpoint,
                "new_mean": float(merged[f"{endpoint}_new"].mean()),
                "baseline_mean": float(merged[f"{endpoint}_baseline"].mean()),
                "delta": mean,
                "ci_lower": lower,
                "ci_upper": upper,
                "positive_repeat_blocks": int((values > 0).sum()),
                "repeat_blocks": 20,
                "decision": decision,
                "bootstrap_method": "20 repeat blocks resampled; all five folds retained",
            }
        )
        for record in repeat_delta.to_dict("records"):
            repeat_rows.append({"endpoint": endpoint, "repeat": int(record["repeat"]), "delta_AULC": float(record[f"delta_{endpoint}"])})
    primary = next(row for row in summary_rows if row["endpoint"] == "B1_q20_AULC_16_80")
    return pd.DataFrame(summary_rows), pd.DataFrame(repeat_rows), primary


def _historical_context_contrasts(path: pd.DataFrame) -> pd.DataFrame:
    historical = pd.read_csv(PHASE15 / "active_path_metrics.csv")
    comparators = {
        "h_model_h_acquisition": "Phase1.5 h-only model/policy",
        "gpc5_margin": "Phase1.5 redundant 5D GPC Margin",
    }
    rng = np.random.default_rng(seed_u32("historical_context_bootstrap"))
    rows = []
    for model, label in comparators.items():
        right = historical[historical.prediction_model.eq(model)][["run_id", "repeat", "fold", "B1_q20_AULC_16_80"]]
        merged = path.merge(right, on=["run_id", "repeat", "fold"], validate="one_to_one")
        merged["difference"] = merged.B1_q20_AULC_16_80_x - merged.B1_q20_AULC_16_80_y
        repeat_values = merged.groupby("repeat").difference.mean().sort_index().to_numpy(float)
        draws = repeat_values[rng.integers(0, 20, size=(BOOTSTRAP_DRAWS, 20))].mean(axis=1)
        rows.append(
            {
                "new_model": "physics_ridge_residual_gp",
                "comparator": model,
                "comparator_label": label,
                "new_mean": float(merged.B1_q20_AULC_16_80_x.mean()),
                "comparator_mean": float(merged.B1_q20_AULC_16_80_y.mean()),
                "difference": float(repeat_values.mean()),
                "ci_lower": float(np.quantile(draws, 0.025)),
                "ci_upper": float(np.quantile(draws, 0.975)),
                "note": "historical context; same frozen splits and initial designs, but both model and acquisition differ",
            }
        )
    return pd.DataFrame(rows)


def _terminal_summary(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    new = metrics[metrics.budget.isin([40, 80])].copy()
    new["model"] = "physics_ridge_residual_gp"
    baseline = pd.read_csv(PHASE1 / "terminal_fold_metrics_random_averaged.csv")
    baseline = baseline[baseline.arm.eq("binary_margin") & baseline.budget.isin([40, 80])].copy()
    baseline["model"] = "frozen_4d_margin"
    baseline = baseline.rename(columns={"specificity": "conduction_recall"})
    columns = [
        "run_id",
        "repeat",
        "fold",
        "model",
        "budget",
        "subset",
        "accuracy",
        "balanced_accuracy",
        "keyhole_recall",
        "conduction_recall",
        "false_negative",
        "false_positive",
    ]
    per_run = pd.concat([new[columns], baseline[columns]], ignore_index=True)
    summary = (
        per_run.groupby(["model", "budget", "subset"], as_index=False)[
            ["accuracy", "balanced_accuracy", "keyhole_recall", "conduction_recall", "false_negative", "false_positive"]
        ]
        .mean()
    )
    return per_run, summary


def _terminal_contrasts(per_run: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(seed_u32("terminal_repeat_block_bootstrap"))
    rows = []
    for budget in (40, 80):
        for subset in ("full81", "B1_q30", "B1_q20"):
            group = per_run[(per_run.budget.eq(budget)) & per_run.subset.eq(subset)]
            for metric in ("accuracy", "balanced_accuracy", "keyhole_recall", "false_negative", "false_positive"):
                pivot = group.pivot(index=["repeat", "fold"], columns="model", values=metric)
                fold_delta = pivot.physics_ridge_residual_gp - pivot.frozen_4d_margin
                repeat_delta = fold_delta.groupby(level="repeat").mean().sort_index().to_numpy(float)
                draws = repeat_delta[rng.integers(0, 20, size=(BOOTSTRAP_DRAWS, 20))].mean(axis=1)
                rows.append(
                    {
                        "budget": budget,
                        "subset": subset,
                        "metric": metric,
                        "new_minus_baseline": float(repeat_delta.mean()),
                        "ci_lower": float(np.quantile(draws, 0.025)),
                        "ci_upper": float(np.quantile(draws, 0.975)),
                        "positive_repeat_blocks": int((repeat_delta > 0).sum()),
                        "repeat_blocks": 20,
                    }
                )
    return pd.DataFrame(rows)


def _pca_diagnostic(population: pd.DataFrame, cases: pd.DataFrame) -> pd.DataFrame:
    x = population.loc[:, FEATURES].to_numpy(float)
    scaler = StandardScaler().fit(x)
    pca = PCA(n_components=2, svd_solver="full").fit(scaler.transform(x))
    scores = pca.transform(scaler.transform(x))
    base = pd.DataFrame(
        {
            "population_row_index": population.index.astype(int),
            "experiment_name": population.experiment_name.astype(str),
            "truth": population.has_keyhole.astype(int),
            "PC1": scores[:, 0],
            "PC2": scores[:, 1],
        }
    )
    budget40 = cases[cases.budget.eq(40)].copy()
    budget40["corrected"] = budget40.category.eq("physics_wrong_combined_correct").astype(int)
    budget40["worsened"] = budget40.category.eq("physics_correct_combined_wrong").astype(int)
    aggregate = (
        budget40.groupby("population_row_index", as_index=False)
        .agg(
            mean_abs_residual=("residual_correction", lambda values: float(np.mean(np.abs(values)))),
            mean_residual=("residual_correction", "mean"),
            mean_physics_probability=("physics_probability", "mean"),
            mean_combined_probability=("combined_probability", "mean"),
            corrected_occurrences=("corrected", "sum"),
            worsened_occurrences=("worsened", "sum"),
            heldout_occurrences=("run_id", "size"),
        )
    )
    result = base.merge(aggregate, on="population_row_index", how="left")
    result[["mean_abs_residual", "mean_residual", "corrected_occurrences", "worsened_occurrences", "heldout_occurrences"]] = result[
        ["mean_abs_residual", "mean_residual", "corrected_occurrences", "worsened_occurrences", "heldout_occurrences"]
    ].fillna(0)
    write_json(
        TABLES / "pca_metadata.json",
        {
            "fit": "label-free PCA on globally standardized P,VX,LS,ST; labels and residuals used only after projection for display",
            "features": list(FEATURES),
            "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
            "loadings": {feature: pca.components_[:, index].tolist() for index, feature in enumerate(FEATURES)},
        },
    )
    return result


def aggregate_active() -> dict[str, Any]:
    metrics, diagnostics, acquisition, cases = load_active_checkpoints()
    require(metrics.run_id.nunique() == 100, "full aggregation requires 100 outer runs")
    require(len(acquisition) == 100 * (80 - 16), "acquisition-row count drift")
    require(not acquisition.test_rows_available_to_acquisition.astype(bool).any(), "test data entered acquisition")
    require(not acquisition.hidden_pool_labels_available_to_acquisition.astype(bool).any(), "hidden labels entered acquisition")
    require(not acquisition.B1_q20_q30_available_to_acquisition.astype(bool).any(), "B1/q flags entered acquisition")
    require(not acquisition.external_h_threshold_used.astype(bool).any(), "external h threshold entered acquisition")
    path = active_path_metrics(metrics)
    primary_summary, repeat_delta, primary = _bootstrap_primary(path)
    context = _historical_context_contrasts(path)
    terminal_per_run, terminal_summary = _terminal_summary(metrics)
    terminal_contrasts = _terminal_contrasts(terminal_per_run)
    population, _ = load_population_and_specs()
    pca = _pca_diagnostic(population, cases)

    curve_new = (
        metrics[metrics.subset.eq("B1_q20")]
        .groupby("budget", as_index=False).accuracy.mean()
        .assign(model="physics_ridge_residual_gp", source="new_phase1_7")
    )
    historical_curve = pd.read_csv(PHASE1 / "learning_curve_summary_16_80.csv")
    historical_curve["model"] = historical_curve.arm.map({"binary_margin": "frozen_4d_margin", "binary_random": "matched_random"})
    historical_curve = historical_curve.rename(columns={"mean_accuracy": "accuracy"}).assign(source="reused_frozen")
    historical_curve = historical_curve[["budget", "accuracy", "model", "source"]]
    phase15_curve = pd.read_csv(PHASE15 / "active_learning_curve_summary.csv")
    phase15_curve = phase15_curve[phase15_curve.prediction_model.isin(["h_model_h_acquisition", "gpc5_margin"])].rename(
        columns={"mean_accuracy": "accuracy", "prediction_model": "model"}
    )
    phase15_curve = phase15_curve[["budget", "accuracy", "model"]].assign(source="reused_phase1_5")
    curves = pd.concat([curve_new, historical_curve, phase15_curve], ignore_index=True)

    budget40_q20 = cases[cases.budget.eq(40) & cases.is_q20.astype(bool)].copy()
    budget40_q20["corrected"] = budget40_q20.category.eq("physics_wrong_combined_correct").astype(int)
    budget40_q20["worsened"] = budget40_q20.category.eq("physics_correct_combined_wrong").astype(int)
    representatives = (
        budget40_q20.groupby(
            ["population_row_index", "experiment_name", "truth", "P", "VX", "LS", "LS_um", "ST", "log_h"], as_index=False
        )
        .agg(
            heldout_q20_occurrences=("run_id", "size"),
            corrected_occurrences=("corrected", "sum"),
            worsened_occurrences=("worsened", "sum"),
            mean_physics_probability=("physics_probability", "mean"),
            mean_residual_correction=("residual_correction", "mean"),
            mean_abs_residual_correction=("residual_correction", lambda values: float(np.mean(np.abs(values)))),
            mean_combined_probability=("combined_probability", "mean"),
        )
        .sort_values(["corrected_occurrences", "mean_abs_residual_correction"], ascending=[False, False])
    )

    write_csv(TABLES / "active_per_budget_metrics.csv.gz", metrics)
    write_csv(TABLES / "active_path_metrics.csv", path)
    write_csv(TABLES / "primary_AULC_summary.csv", primary_summary)
    write_csv(TABLES / "repeat_level_delta_AULC.csv", repeat_delta)
    write_csv(TABLES / "historical_context_AULC.csv", context)
    write_csv(TABLES / "terminal_budget_metrics_per_run.csv", terminal_per_run)
    write_csv(TABLES / "terminal_budget_summary.csv", terminal_summary)
    write_csv(TABLES / "terminal_budget_contrasts.csv", terminal_contrasts)
    write_csv(TABLES / "model_mechanism_diagnostics.csv.gz", diagnostics)
    write_csv(TABLES / "active_information_flow.csv.gz", acquisition)
    write_csv(TABLES / "active_case_diagnostics_budget40_80.csv.gz", cases)
    write_csv(TABLES / "representative_residual_cases.csv", representatives)
    write_csv(TABLES / "active_learning_curve_summary.csv", curves)
    write_csv(TABLES / "pca_residual_diagnostic.csv", pca)
    write_json(OUTPUT / "primary_decision.json", primary)
    report = {
        "status": "PASS",
        "decision": primary["decision"],
        "outer_runs": 100,
        "primary": primary,
        "information_flow": {
            "test_rows_used": False,
            "hidden_pool_labels_used": False,
            "B1_q20_q30_used": False,
            "external_h_threshold_used": False,
        },
        "new_runs": ["physics_ridge_residual_gp_margin H80"],
        "reused_comparators": ["frozen_4d_margin", "matched_random", "Phase1.5 h-only", "Phase1.5 5D GPC"],
        "inference_unit": "20 repeat blocks; all five folds retained",
    }
    write_json(OUTPUT / "active_aggregation_report.json", report)
    return report


def _save_figure(fig: plt.Figure, name: str) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / name
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def generate_figures() -> list[Path]:
    plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10})
    created: list[Path] = []
    cases = pd.read_csv(TABLES / "active_case_diagnostics_budget40_80.csv.gz")
    diagnostics = pd.read_csv(TABLES / "model_mechanism_diagnostics.csv.gz")

    # Figure 1: trend and residual mechanism at the thesis-relevant budget 40.
    budget40 = cases[cases.budget.eq(40)].copy()
    budget40["combined_latent_probability"] = expit(budget40.combined_latent.to_numpy(float))
    aggregate = (
        budget40.groupby(["population_row_index", "log_h"], as_index=False)
        .agg(
            physics_probability=("physics_probability", "mean"),
            combined_probability=("combined_latent_probability", "mean"),
            residual_correction=("residual_correction", "mean"),
        )
        .sort_values("log_h")
    )
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2))
    axes[0].plot(aggregate.log_h, aggregate.physics_probability, color="#275dad", lw=2.2, label="Physics trend g(log h)")
    axes[0].scatter(aggregate.log_h, aggregate.combined_probability, s=13, color="#e07a2d", alpha=0.45, label="Combined latent mean sigmoid(g+r)")
    selected = aggregate.nlargest(14, "residual_correction").index.union(aggregate.nsmallest(14, "residual_correction").index)
    for index in selected:
        row = aggregate.loc[index]
        axes[0].annotate(
            "",
            xy=(row.log_h, row.combined_probability),
            xytext=(row.log_h, row.physics_probability),
            arrowprops={"arrowstyle": "-", "color": "0.25", "lw": 0.7, "alpha": 0.65},
        )
    axes[0].axhline(0.5, color="0.5", lw=0.8, ls="--")
    axes[0].set(xlabel="log(h) [SI reference]", ylabel="Predicted Keyhole probability", title="Budget 40: dominant physics trend and residual corrections")
    axes[0].legend(frameon=False, loc="upper left")

    full = diagnostics[diagnostics.subset.eq("full81")]
    path = full.groupby("budget", as_index=False).agg(
        physics_rms=("physics_rms_latent", "mean"),
        residual_rms=("residual_rms_latent", "mean"),
        residual_sd=("residual_sd", "mean"),
    )
    axes[1].plot(path.budget, path.physics_rms, color="#275dad", lw=2, label="RMS physics latent")
    axes[1].plot(path.budget, path.residual_rms, color="#e07a2d", lw=2, label="RMS residual correction")
    axes[1].plot(path.budget, path.residual_sd, color="#5c9a48", lw=1.8, ls="--", label="Learned residual prior SD")
    axes[1].set(xlabel="Queried labels", ylabel="Latent-logit scale", title="Residual remains a correction in realized magnitude")
    axes[1].legend(frameon=False)
    fig.suptitle("Physics-ridge + 4D residual GP mechanism", fontsize=14)
    fig.tight_layout()
    created.append(_save_figure(fig, "01_model_mechanism.png"))

    # Figure 2: exact frozen primary learning curves.
    new_metrics = pd.read_csv(TABLES / "active_per_budget_metrics.csv.gz")
    new_q20 = new_metrics[new_metrics.subset.eq("B1_q20")].groupby("budget").accuracy.agg(["mean", lambda s: s.quantile(0.05), lambda s: s.quantile(0.95)]).reset_index()
    new_q20.columns = ["budget", "mean", "q05", "q95"]
    historical = pd.read_csv(PHASE1 / "learning_curve_summary_16_80.csv")
    p15_curve = pd.read_csv(PHASE15 / "active_learning_curve_summary.csv")
    fig, ax = plt.subplots(figsize=(8.3, 4.8))
    ax.plot(new_q20.budget, new_q20["mean"], color="#d1495b", lw=2.5, label="Physics ridge + residual GP (new)")
    styles = {
        "binary_margin": ("#275dad", "4D Margin (frozen)"),
        "binary_random": ("#777777", "Matched Random (frozen)"),
    }
    for arm, (color, label) in styles.items():
        group = historical[historical.arm.eq(arm)]
        ax.plot(group.budget, group.mean_accuracy, color=color, lw=2, label=label)
    h_curve = p15_curve[p15_curve.prediction_model.eq("h_model_h_acquisition")]
    ax.plot(h_curve.budget, h_curve.mean_accuracy, color="#5c9a48", lw=1.5, ls="--", label="h-only model/policy (Phase 1.5)")
    ax.set(xlabel="Queried labels", ylabel="Fold-B1-q20 accuracy", title="Near-boundary active-learning performance")
    ax.set_xlim(16, 80)
    ax.set_ylim(0.72, 0.86)
    ax.legend(frameon=False, ncol=2, fontsize=9)
    ax.grid(axis="y", alpha=0.2)
    ax.text(0.99, 0.02, "Curves are means over the 100 matched outer runs.", transform=ax.transAxes, ha="right", fontsize=8, color="0.35")
    fig.tight_layout()
    created.append(_save_figure(fig, "02_q20_learning_curves.png"))

    # Figure 3: preregistered matched repeat-block contrast.
    repeat_delta = pd.read_csv(TABLES / "repeat_level_delta_AULC.csv")
    repeat_delta = repeat_delta[repeat_delta.endpoint.eq("B1_q20_AULC_16_80")]
    summary = pd.read_csv(TABLES / "primary_AULC_summary.csv")
    primary = summary[summary.endpoint.eq("B1_q20_AULC_16_80")].iloc[0]
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    colors = np.where(repeat_delta.delta_AULC > 0, "#275dad", "#d1495b")
    ax.scatter(repeat_delta.repeat, repeat_delta.delta_AULC, c=colors, s=42, zorder=3)
    ax.axhline(0, color="0.25", lw=1)
    ax.axhline(0.010, color="#5c9a48", lw=1.2, ls="--", label="PASS effect threshold +0.010")
    ax.errorbar(
        21.5,
        primary.delta,
        yerr=[[primary.delta - primary.ci_lower], [primary.ci_upper - primary.delta]],
        fmt="D",
        color="black",
        capsize=5,
        label="Mean and repeat-block 95% CI",
    )
    ax.set_xticks([1, 5, 10, 15, 20, 21.5], ["1", "5", "10", "15", "20", "Mean"])
    ax.set(xlabel="Frozen repeat block", ylabel="ΔAULC (new − 4D Margin)", title="Primary matched Fold-B1-q20 AULC contrast")
    ax.legend(frameon=False, loc="upper right")
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    created.append(_save_figure(fig, "03_primary_delta_AULC.png"))

    # Figure 4: label-free PCA coordinates, colored by realized correction magnitude.
    pca = pd.read_csv(TABLES / "pca_residual_diagnostic.csv")
    fig, ax = plt.subplots(figsize=(7.5, 5.6))
    scatter = ax.scatter(pca.PC1, pca.PC2, c=pca.mean_abs_residual, cmap="viridis", s=28, alpha=0.78, edgecolors="none")
    recovered = pca.corrected_occurrences > pca.worsened_occurrences
    worsened = pca.worsened_occurrences > pca.corrected_occurrences
    ax.scatter(pca.loc[recovered, "PC1"], pca.loc[recovered, "PC2"], facecolors="none", edgecolors="#1b9e77", s=68, lw=1.3, label="More corrected than worsened")
    ax.scatter(pca.loc[worsened, "PC1"], pca.loc[worsened, "PC2"], marker="x", c="#d95f02", s=48, lw=1.2, label="More worsened than corrected")
    fig.colorbar(scatter, ax=ax, label="Mean |residual latent correction| at budget 40")
    ax.set(xlabel="PC1", ylabel="PC2", title="Where the residual matters in standardized 4D input space")
    ax.legend(frameon=False, loc="best")
    ax.text(0.01, 0.01, "PCA is label-free and descriptive; it is not physical boundary geometry.", transform=ax.transAxes, fontsize=8, color="0.35")
    fig.tight_layout()
    created.append(_save_figure(fig, "04_pca_residual_diagnostic.png"))

    manifest = pd.DataFrame(
        [{"figure": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in created]
    )
    write_csv(OUTPUT / "figure_manifest.csv", manifest)
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("baseline-gate")
    static_parser = subparsers.add_parser("static")
    static_parser.add_argument("--workers", type=int, default=1)
    active_parser = subparsers.add_parser("active")
    active_parser.add_argument("--workers", type=int, default=1)
    subparsers.add_parser("aggregate")
    subparsers.add_parser("figures")
    args = parser.parse_args()
    if args.command == "baseline-gate":
        print(json.dumps(baseline_gate(), indent=2))
    elif args.command == "static":
        print(json.dumps(run_static(workers=args.workers), indent=2))
    elif args.command == "active":
        print(json.dumps(run_active(horizon=80, workers=args.workers), indent=2))
    elif args.command == "aggregate":
        print(json.dumps(aggregate_active(), indent=2))
    elif args.command == "figures":
        print("\n".join(str(path) for path in generate_figures()))


if __name__ == "__main__":
    main()
