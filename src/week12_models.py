"""Week 12 bounded model-transfer and NEW-only model-CV lane.

This module is deliberately separate from the frozen external runner.  It
reuses the historical model implementations, fits no model at import time,
and records model failures rather than silently changing the scientific
specification.  The 136-row cohort is post-hoc development data.
"""
from __future__ import annotations

import argparse
import json
import math
import warnings
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import spearmanr
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_12_gpc_kernel_adequacy as p12
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week7_phase6_real_data_boundary_active_level_set as p6
from src.external_validation.analysis import boundary_flags
from src.week12_development_common import (
    FEATURES,
    HIST,
    MANIFEST,
    OLD,
    OUT,
    ROOT,
    load_new,
    load_old,
    load_splits,
    metrics,
    safe,
    seed,
    sha,
    write_csv,
    write_json,
)

MODELS = ("H", "G0", "G3", "M3", "empirical_prior")
FIT_MODELS = MODELS[:-1]
SCHEMA_VERSION = "week12_models_v1"
BOOTSTRAP_DRAWS = 2000


def _x(frame: pd.DataFrame) -> np.ndarray:
    return frame.loc[:, FEATURES].to_numpy(float)


def _subset_flags(frame: pd.DataFrame, indices: np.ndarray) -> dict[int, np.ndarray]:
    """Use the frozen full-batch boundary construction for q20 and q30."""
    return boundary_flags(
        _x(frame),
        frame.has_keyhole.to_numpy(int),
        np.asarray(indices, int),
        frame.sim_id.astype(str).to_numpy(),
        "entire_evaluation_batch",
    )


def _failure_metrics(y: np.ndarray) -> dict[str, Any]:
    y = np.asarray(y, int)
    return {
        "n": int(len(y)),
        "n_keyhole": int((y == 1).sum()),
        "n_non_keyhole": int((y == 0).sum()),
        "accuracy": np.nan,
        "balanced_accuracy": np.nan,
        "keyhole_recall": np.nan,
        "non_keyhole_recall": np.nan,
        "roc_auc": np.nan,
        "pr_auc_keyhole": np.nan,
        "pr_auc_non_keyhole": np.nan,
        "brier": np.nan,
        "log_loss": np.nan,
    }


def _fit_model(name: str, frame: pd.DataFrame, train: np.ndarray, fit_seed: int) -> tuple[Any, dict[str, Any]]:
    """Fit one historical model on ``train``; no fallback beyond its archive API."""
    x = _x(frame)
    y = frame.has_keyhole.to_numpy(int)
    train = np.asarray(train, int)
    if np.unique(y[train]).size != 2:
        raise RuntimeError(f"{name}: one-class training data ({np.unique(y[train]).tolist()})")
    scaler = StandardScaler().fit(x[train])
    xs = scaler.transform(x[train])
    diagnostics: dict[str, Any] = {"model": name, "train_n": int(len(train)), "train_keyhole": int(y[train].sum()), "train_non_keyhole": int((y[train] == 0).sum()), "fit_seed": int(fit_seed)}
    if name == "H":
        fit = p11.fit_physics_mean(frame.log_h.to_numpy(float), y, train, fit_seed)
        diagnostics.update({"fit_status": "historical_h_logistic", "scaler_scope": "training_rows_log_h", "scaler_mean": float(fit.scaler.mean_[0]), "scaler_scale": float(fit.scaler.scale_[0]), "coefficient": float(fit.model.coef_[0, 0]), "intercept": float(fit.model.intercept_[0])})
        return fit, diagnostics
    if name == "G0":
        fit = p6.fit_gpc(x[train], y[train], seed=fit_seed, scaler=scaler, kernel_kind="matern32", restarts=0)
        diagnostics.update({"fit_status": fit.fit_status, "scaler_scope": "training_rows_4d", "scaler_mean": scaler.mean_.tolist(), "scaler_scale": scaler.scale_.tolist(), "kernel": fit.kernel, "constant_value": fit.constant_value, "length_scale": fit.length_scale, "bound_hit": fit.bound_hit, "warnings": fit.warnings})
        return fit, diagnostics
    if name == "G3":
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            model, diag = p12.fit_gpc_model("G3", xs, y[train], fit_seed)
        diagnostics.update({"fit_status": diag.get("fit_status"), "scaler_scope": "training_rows_4d", "scaler_mean": scaler.mean_.tolist(), "scaler_scale": scaler.scale_.tolist(), "kernel": repr(model.kernel_) if hasattr(model, "kernel_") else "logistic_fallback", "historical_diagnostics": diag, "warnings": [str(w.message) for w in caught]})
        return (model, scaler), diagnostics
    if name == "M3":
        physics = p11.fit_physics_mean(frame.log_h.to_numpy(float), y, train, fit_seed)
        fit = p13.fit_hybrid(x, frame.log_h.to_numpy(float), y, train, train, physics, "M3", 100.0)
        diagnostics.update({"fit_status": "historical_m3_fixed_mean_ard", "scaler_scope": "training_rows_4d", "x_scaler_mean": fit.x_scaler.mean_.tolist(), "x_scaler_scale": fit.x_scaler.scale_.tolist(), "physics_scaler_mean": fit.physics.scaler.mean_.tolist(), "physics_scaler_scale": fit.physics.scaler.scale_.tolist(), "kernel": repr(fit.gp.kernel_), "residual_sd": fit.residual_sd, "length_scales": fit.length_scales.tolist(), "length_upper": fit.length_upper, "optimizer_converged": fit.gp.diagnostics_.optimizer_converged, "optimizer_message": fit.gp.diagnostics_.optimizer_message, "optimizer_iterations": fit.gp.diagnostics_.optimizer_iterations, "optimizer_evaluations": fit.gp.diagnostics_.optimizer_evaluations, "posterior_iterations": fit.gp.diagnostics_.posterior_iterations, "fallback_status": fit.gp.diagnostics_.fallback_status, "objective_value": fit.gp.diagnostics_.objective_value, "historical_diagnostics": p13.fit_diagnostic(fit)})
        return fit, diagnostics
    raise ValueError(f"Unknown model {name}")


def _predict_model(name: str, fit: Any, frame: pd.DataFrame, indices: np.ndarray, old_prevalence: float | None = None) -> tuple[np.ndarray, dict[str, Any]]:
    x = _x(frame)[np.asarray(indices, int)]
    log_h = frame.log_h.to_numpy(float)[np.asarray(indices, int)]
    if name == "empirical_prior":
        p = np.full(len(indices), float(old_prevalence), dtype=float)
        return p, {"components_available": False, "prior_probability": float(old_prevalence)}
    if name == "H":
        latent = fit.latent(log_h)
        p = expit(latent)
        return p, {"components_available": True, "physics_latent": latent.tolist(), "residual_latent": np.zeros(len(p)).tolist(), "final_latent": latent.tolist()}
    if name == "G0":
        p = p6.predict_gpc(fit, x)
        return p, {"components_available": False}
    if name == "G3":
        model, scaler = fit
        p = np.asarray(model.predict_proba(scaler.transform(x))[:, 1], float)
        return p, {"components_available": False}
    if name == "M3":
        c = p13.components(fit, x, log_h)
        return np.asarray(c["probability"], float), {"components_available": True, "physics_latent": c["physics_latent"].tolist(), "residual_latent": c["residual_latent"].tolist(), "final_latent": c["final_latent"].tolist(), "latent_variance": c["latent_variance"].tolist()}
    raise ValueError(name)


def _prediction_frame(name: str, frame: pd.DataFrame, indices: np.ndarray, probability: np.ndarray, fit_status: str, components: dict[str, Any]) -> pd.DataFrame:
    y = frame.has_keyhole.to_numpy(int)
    ids = frame.sim_id.astype(str).to_numpy()
    rows = []
    for j, idx in enumerate(np.asarray(indices, int)):
        row = {"model": name, "row_index": int(idx), "sim_id": str(ids[idx]), "truth": int(y[idx]), "probability": float(probability[j]), "fit_status": fit_status}
        for key, value in components.items():
            if key != "components_available":
                row[key] = float(value[j]) if isinstance(value, list) else value
        rows.append(row)
    return pd.DataFrame(rows)


def _fit_predict(name: str, frame: pd.DataFrame, train: np.ndarray, test: np.ndarray, fit_seed: int, old_prevalence: float | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    y = frame.has_keyhole.to_numpy(int)
    ids = frame.sim_id.astype(str).to_numpy()
    try:
        if name == "empirical_prior":
            fit, diagnostics = (None, {"model": name, "fit_status": "fixed_training_prevalence", "prior_scope": "training_rows", "train_n": int(len(train)), "train_keyhole": int(y[train].sum()), "train_non_keyhole": int((y[train] == 0).sum()), "fit_seed": int(fit_seed)})
        else:
            fit, diagnostics = _fit_model(name, frame, train, fit_seed)
        p, components = _predict_model(name, fit, frame, test, old_prevalence)
        frame_out = _prediction_frame(name, frame, test, p, diagnostics.get("fit_status", "ok"), components)
        diagnostics.update({"prediction_count": int(len(frame_out)), "prediction_finite": bool(np.isfinite(p).all()), "components": components.get("components_available", False)})
        return frame_out, diagnostics
    except Exception as exc:
        diagnostics = {"model": name, "fit_seed": int(fit_seed), "fit_status": "FAILED", "error_type": type(exc).__name__, "error": str(exc), "train_n": int(len(train)), "train_keyhole": int(y[train].sum()), "train_non_keyhole": int((y[train] == 0).sum())}
        rows = [{"model": name, "row_index": int(idx), "sim_id": str(ids[idx]), "truth": int(y[idx]), "probability": np.nan, "fit_status": "FAILED"} for idx in np.asarray(test, int)]
        return pd.DataFrame(rows), diagnostics


def _fit_predict_transfer(name: str, old: pd.DataFrame, new: pd.DataFrame, fit_seed: int, old_prevalence: float) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fit on a physically separate OLD frame, then predict on NEW rows."""
    train_old = np.arange(len(old), dtype=int)
    test_new = np.arange(len(new), dtype=int)
    y_new = new.has_keyhole.to_numpy(int)
    try:
        if name == "empirical_prior":
            diagnostics = {"model": name, "fit_status": "fixed_old_training_prevalence", "prior_scope": "OLD-405", "train_n": int(len(old)), "train_keyhole": int(old.has_keyhole.sum()), "train_non_keyhole": int((old.has_keyhole == 0).sum()), "fit_seed": int(fit_seed), "prior_probability": float(old_prevalence)}
            probability, components = _predict_model(name, None, new, test_new, old_prevalence)
        else:
            fit, diagnostics = _fit_model(name, old, train_old, fit_seed)
            probability, components = _predict_model(name, fit, new, test_new, old_prevalence)
        output = _prediction_frame(name, new, test_new, probability, diagnostics.get("fit_status", "ok"), components)
        diagnostics.update({"prediction_count": int(len(output)), "prediction_finite": bool(np.isfinite(probability).all()), "components": components.get("components_available", False)})
        return output, diagnostics
    except Exception as exc:
        diagnostics = {"model": name, "fit_seed": int(fit_seed), "fit_status": "FAILED", "error_type": type(exc).__name__, "error": str(exc), "train_n": int(len(old)), "train_keyhole": int(old.has_keyhole.sum()), "train_non_keyhole": int((old.has_keyhole == 0).sum())}
        rows = [{"model": name, "row_index": int(idx), "sim_id": str(new.sim_id.iloc[idx]), "truth": int(y_new[idx]), "probability": np.nan, "fit_status": "FAILED"} for idx in test_new]
        return pd.DataFrame(rows), diagnostics


def _provenance(mode: str, frame: pd.DataFrame, old: pd.DataFrame) -> dict[str, Any]:
    historical_sources = {"H": "src/week9_phase1_11_fixed_mean_discrepancy_gp.py", "G0": "src/week7_phase6_real_data_boundary_active_level_set.py", "G3": "src/week9_phase1_12_gpc_kernel_adequacy.py", "M3": "src/week9_phase1_13_fixed_physics_ard_discrepancy.py"}
    source_paths = [OLD, MANIFEST, HIST / "split_manifest.json", HIST / "per_budget_predictions.csv", ROOT / "src/week12_development_common.py", ROOT / "src/week12_models.py", *(ROOT / p for p in historical_sources.values())]
    return {"schema_version": SCHEMA_VERSION, "mode": mode, "status": "POST-HOC DEVELOPMENT", "models": list(MODELS), "fit_models": list(FIT_MODELS), "features": list(FEATURES), "new_rows": int(len(frame)), "new_keyhole": int(frame.has_keyhole.sum()), "old_rows": int(len(old)), "old_keyhole": int(old.has_keyhole.sum()), "source_hashes": {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in source_paths}, "historical_sources": historical_sources, "model_specs": {"H": "p11.fit_physics_mean(log_h, labels, training_indices, seed); logistic C=1e6 on StandardScaler(log_h)", "G0": "p6.fit_gpc(P,VX,LS,ST training rows; historical Matérn-3/2 isotropic; restarts=0)", "G3": "p12.fit_gpc_model('G3', StandardScaler(training rows).transform(X), labels, seed); ARD Matérn-3/2; restarts=0", "M3": "p11.fit_physics_mean then p13.fit_hybrid(X, log_h, labels, revealed=training_indices, training_pool=training_indices, physics, 'M3', 100.0)", "empirical_prior": "constant training prevalence; no fitted scaler/model"}, "seed_namespace": "week12|...", "q20": "src.external_validation.analysis.boundary_flags with entire_evaluation_batch; evaluation-only", "failure_policy": "retain failed fit/prediction rows and diagnostics with NaN metrics; no unrecorded fallback"}


def run_transfer() -> dict[str, Any]:
    new, old = load_new(), load_old()
    root = OUT / "models/transfer"
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "config.json", {**_provenance("transfer", new, old), "train_source": "OLD-405 only", "test_source": "NEW-136 included", "scaler_scope": "OLD-405 only", "bootstrap_draws": BOOTSTRAP_DRAWS, "bootstrap": "class-stratified NEW cohort resampling of fixed predictions", "models": list(MODELS), "computational_notes": "M3 Laplace GP optimization is the dominant O(n^3) fit cost; 2000 bootstrap draws do not refit. NEW labels are evaluation-only."})
    write_json(root / "provenance.json", _provenance("transfer", new, old))
    y_new = new.has_keyhole.to_numpy(int)
    old_prevalence = float(old.has_keyhole.mean())
    flags = _subset_flags(new, np.arange(len(new), dtype=int))
    predictions, diagnostics = [], []
    for name in MODELS:
        frame, diag = _fit_predict_transfer(name, old, new, seed("transfer", name), old_prevalence)
        frame["is_q20"] = flags[20]
        frame["is_q30"] = flags[30]
        predictions.append(frame[["model", "row_index", "sim_id", "truth", "probability", "fit_status"] + [c for c in frame.columns if c in ("physics_latent", "residual_latent", "final_latent", "latent_variance")]])
        predictions[-1]["is_q20"] = flags[20]
        predictions[-1]["is_q30"] = flags[30]
        diagnostics.append(diag)
    pred = pd.concat(predictions, ignore_index=True)
    write_csv(root / "predictions.csv.gz", pred)
    write_json(root / "fit_diagnostics.json", diagnostics)
    summary_rows = []
    for name, group in pred.groupby("model", sort=True):
        for subset, mask in (("full", np.ones(len(group), dtype=bool)), ("q20", group.is_q20.to_numpy(bool)), ("q30", group.is_q30.to_numpy(bool))):
            part = group.loc[mask].sort_values("row_index")
            good = part.probability.notna()
            row = {"model": name, "subset": subset, "fit_status": ";".join(sorted(group.fit_status.astype(str).unique())), "prediction_count": int(len(part)), "finite_count": int(good.sum())}
            if len(part) and good.all():
                row.update(metrics(part.truth.to_numpy(int), part.probability.to_numpy(float)))
            else:
                row.update(_failure_metrics(part.truth.to_numpy(int)))
            summary_rows.append(row)
    summary = pd.DataFrame(summary_rows)
    write_csv(root / "summary.csv", summary)
    write_csv(root / "q20_fixedmask_summary.csv", summary[summary.subset.eq("q20")])
    _transfer_bootstrap(pred, new, root)
    _transfer_diagnostics(pred, new, old, root)
    _make_transfer_figures(pred, new, root)
    (root / "REPORT.md").write_text(_transfer_report(summary), encoding="utf-8")
    qc = _write_qc(root, pred, diagnostics)
    reference = pred[pred.model.eq(MODELS[0])].sort_values("row_index")
    (root / "summary.json").write_text(json.dumps(safe({"mode": "transfer", "models": list(MODELS), "qc": qc, "subsets": {"full": int(len(reference)), "q20": int(reference.is_q20.sum()), "q30": int(reference.is_q30.sum())}}), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": qc["status"], "mode": "transfer", "models": list(MODELS), "output": str(root)}


def _write_qc(root: Path, predictions: pd.DataFrame, diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [d for d in diagnostics if d.get("fit_status") == "FAILED"]
    missing = int(predictions.probability.isna().sum())
    qc = {"status": "PASS" if not failed and missing == 0 else "FAIL", "fit_failure_count": len(failed), "prediction_missing_count": missing, "prediction_rows": int(len(predictions)), "models": sorted(predictions.model.astype(str).unique().tolist()), "failure_policy": "retained in predictions and fit_diagnostics; lane status is FAIL"}
    write_json(root / "qc.json", qc)
    return qc


def _transfer_bootstrap(pred: pd.DataFrame, new: pd.DataFrame, root: Path) -> None:
    y = new.has_keyhole.to_numpy(int)
    pos, neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
    rng = np.random.default_rng(seed("transfer", "class_stratified_bootstrap"))
    rows = []
    subset_masks = {"full": np.ones(len(y), dtype=bool), "q20": pred[pred.model.eq(MODELS[0])].sort_values("row_index").is_q20.to_numpy(bool), "q30": pred[pred.model.eq(MODELS[0])].sort_values("row_index").is_q30.to_numpy(bool)}
    for draw in range(BOOTSTRAP_DRAWS):
        idx = np.r_[rng.choice(pos, len(pos), replace=True), rng.choice(neg, len(neg), replace=True)]
        for name, group in pred.groupby("model", sort=True):
            p = group.sort_values("row_index").probability.to_numpy(float)
            for subset, subset_mask in subset_masks.items():
                selected = subset_mask[idx]
                if np.isfinite(p).all() and selected.any():
                    row = metrics(y[idx][selected], p[idx][selected])
                else:
                    row = _failure_metrics(y[idx][selected])
                rows.append({"draw": draw, "model": name, "subset": subset, **row})
    frame = pd.DataFrame(rows)
    write_csv(root / "class_stratified_bootstrap.csv.gz", frame)
    cols = ["accuracy", "balanced_accuracy", "roc_auc", "pr_auc_keyhole", "brier", "log_loss"]
    out = []
    for (name, subset), group in frame.groupby(["model", "subset"], sort=True):
        for col in cols:
            vals = group[col].dropna().to_numpy(float)
            out.append({"model": name, "subset": subset, "metric": col, "mean": float(vals.mean()) if len(vals) else np.nan, "ci95_lower": float(np.quantile(vals, .025)) if len(vals) else np.nan, "ci95_upper": float(np.quantile(vals, .975)) if len(vals) else np.nan, "draws": int(len(vals))})
    write_csv(root / "class_stratified_bootstrap_summary.csv", pd.DataFrame(out))
    contrasts = []
    for subset in ("full", "q20", "q30"):
        wide = frame[frame.subset.eq(subset)].pivot(index="draw", columns="model")
        for right in ("H", "G0", "G3"):
            for col in ("balanced_accuracy", "roc_auc", "brier", "pr_auc_keyhole"):
                if (col, "M3") not in wide.columns or (col, right) not in wide.columns:
                    continue
                delta = (wide[(col, "M3")] - wide[(col, right)]).dropna().to_numpy(float)
                contrasts.append({"contrast": f"M3_minus_{right}", "subset": subset, "metric": col, "mean": float(delta.mean()) if len(delta) else np.nan, "ci95_lower": float(np.quantile(delta, .025)) if len(delta) else np.nan, "ci95_upper": float(np.quantile(delta, .975)) if len(delta) else np.nan, "draws": int(len(delta)), "interpretation": "paired class-stratified fixed-prediction cohort resampling"})
    write_csv(root / "paired_bootstrap_contrasts.csv", pd.DataFrame(contrasts))
    _leave_one_negative_out(pred, new, root)
    _calibration_bootstrap(pred, new, root)


def _leave_one_negative_out(pred: pd.DataFrame, new: pd.DataFrame, root: Path) -> None:
    """Fixed-prediction sensitivity to each of the 12 NEW non-keyholes."""
    y = new.has_keyhole.to_numpy(int)
    negatives = np.flatnonzero(y == 0)
    rows = []
    for name, group in pred.groupby("model", sort=True):
        part = group.sort_values("row_index")
        p = part.probability.to_numpy(float)
        if not np.isfinite(p).all():
            rows.append({"model": name, "negative_count": len(negatives), "metric": "balanced_accuracy", "min": np.nan, "max": np.nan, "mean": np.nan, "interpretation": "fixed predictions; model fit unchanged"})
            continue
        values = {metric: [] for metric in ("accuracy", "balanced_accuracy", "roc_auc", "pr_auc_keyhole", "pr_auc_non_keyhole", "brier", "log_loss")}
        for omitted in negatives:
            keep = np.ones(len(y), dtype=bool)
            keep[omitted] = False
            result = metrics(y[keep], p[keep])
            for metric in values:
                values[metric].append(result[metric])
        for metric, vals in values.items():
            vals = np.asarray(vals, float)
            rows.append({"model": name, "negative_count": len(negatives), "metric": metric, "min": float(np.nanmin(vals)), "max": float(np.nanmax(vals)), "mean": float(np.nanmean(vals)), "interpretation": "fixed predictions; model fit unchanged; 12-negative fragility sensitivity"})
    write_csv(root / "leave_one_negative_out_sensitivity.csv", pd.DataFrame(rows))


def _calibration_bootstrap(pred: pd.DataFrame, new: pd.DataFrame, root: Path) -> None:
    """Bin-level calibration uncertainty under the same fixed-prediction draws."""
    y = new.has_keyhole.to_numpy(int)
    pos, neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
    rng = np.random.default_rng(seed("transfer", "calibration_bootstrap"))
    bins = np.linspace(0.0, 1.0, 6)
    rows = []
    for name, group in pred.groupby("model", sort=True):
        p = group.sort_values("row_index").probability.to_numpy(float)
        if not np.isfinite(p).all():
            continue
        observed = {i: [] for i in range(len(bins) - 1)}
        predicted = {i: [] for i in range(len(bins) - 1)}
        for _ in range(BOOTSTRAP_DRAWS):
            idx = np.r_[rng.choice(pos, len(pos), replace=True), rng.choice(neg, len(neg), replace=True)]
            for b, (lo, hi) in enumerate(zip(bins[:-1], bins[1:])):
                mask = (p[idx] >= lo) & (p[idx] <= hi if hi == 1 else p[idx] < hi)
                observed[b].append(float(y[idx][mask].mean()) if mask.any() else np.nan)
                predicted[b].append(float(p[idx][mask].mean()) if mask.any() else np.nan)
        for b, (lo, hi) in enumerate(zip(bins[:-1], bins[1:])):
            obs, pr = np.asarray(observed[b], float), np.asarray(predicted[b], float)
            rows.append({"model": name, "bin_lower": lo, "bin_upper": hi, "bootstrap_draws": BOOTSTRAP_DRAWS, "observed_fraction_mean": float(np.nanmean(obs)) if np.isfinite(obs).any() else np.nan, "observed_fraction_ci95_lower": float(np.nanquantile(obs, .025)) if np.isfinite(obs).any() else np.nan, "observed_fraction_ci95_upper": float(np.nanquantile(obs, .975)) if np.isfinite(obs).any() else np.nan, "predicted_probability_mean": float(np.nanmean(pr)) if np.isfinite(pr).any() else np.nan, "bin_nonempty_draws": int(np.isfinite(obs).sum()), "interpretation": "descriptive fixed-prediction calibration uncertainty"})
    write_csv(root / "calibration_bootstrap_summary.csv", pd.DataFrame(rows))


def _transfer_diagnostics(pred: pd.DataFrame, new: pd.DataFrame, old: pd.DataFrame, root: Path) -> None:
    scaler = StandardScaler().fit(_x(old))
    distance = np.linalg.norm(scaler.transform(_x(new))[:, None, :] - scaler.transform(_x(old))[None, :, :], axis=2).min(axis=1)
    rows = []
    for name, group in pred.groupby("model", sort=True):
        part = group.sort_values("row_index")
        p = part.probability.to_numpy(float)
        error = np.abs(p - part.truth.to_numpy(int))
        for feature in ["log_h", "VX", "ST"]:
            xv = new.sort_values("row_index")[feature].to_numpy(float)
            valid = np.isfinite(p)
            corr = spearmanr(xv[valid], error[valid]).statistic if valid.sum() > 2 else np.nan
            rows.append({"model": name, "analysis": "abs_error_association", "variable": feature, "spearman_abs_error": float(corr) if np.isfinite(corr) else np.nan})
        rows.append({"model": name, "analysis": "abs_error_association", "variable": "nearest_old_standardized_distance", "spearman_abs_error": float(spearmanr(distance[valid], error[valid]).statistic) if valid.sum() > 2 else np.nan})
        rows.append({"model": name, "analysis": "rare_class_calibration", "variable": "non_keyhole_n", "spearman_abs_error": float(np.sum(new.has_keyhole.to_numpy(int) == 0))})
    write_csv(root / "transfer_diagnostics.csv", pd.DataFrame(rows))
    row = new[["sim_id", "row_index", *FEATURES, "log_h", "has_keyhole"]].copy()
    row["nearest_old_standardized_distance"] = distance
    for name, group in pred.groupby("model", sort=True):
        row = row.merge(group[["row_index", "probability", "fit_status"]].rename(columns={"probability": f"probability_{name}", "fit_status": f"fit_status_{name}"}), on="row_index", how="left")
    write_csv(root / "per_simulation_transfer.csv.gz", row)


def _make_transfer_figures(pred: pd.DataFrame, new: pd.DataFrame, root: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for name, group in pred.groupby("model", sort=True):
        p = group.sort_values("row_index").probability.to_numpy(float)
        order = np.argsort(p)
        ax.plot(np.arange(len(p)), p[order], ".", ms=3, label=name)
    ax.set(xlabel="NEW-136 rows ordered within model by predicted probability", ylabel="Predicted P(Keyhole)", title="OLD→NEW transfer predictions")
    ax.legend(frameon=False, ncol=2); fig.tight_layout(); fig.savefig(root / "transfer_probability_distributions.png", dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for name, group in pred.groupby("model", sort=True):
        p = group.sort_values("row_index").probability.to_numpy(float)
        y = group.sort_values("row_index").truth.to_numpy(int)
        bins = np.linspace(0, 1, 6); xs = []; ys = []
        for lo, hi in zip(bins[:-1], bins[1:]):
            mask = (p >= lo) & (p <= hi if hi == 1 else p < hi)
            if mask.any(): xs.append(float(p[mask].mean())); ys.append(float(y[mask].mean()))
        ax.plot(xs, ys, "o-", label=name)
    ax.plot([0, 1], [0, 1], "k--", lw=1); ax.set(xlabel="Mean predicted probability", ylabel="Observed Keyhole fraction", title="Transfer calibration (descriptive)")
    ax.legend(frameon=False, ncol=2); fig.tight_layout(); fig.savefig(root / "transfer_calibration.png", dpi=160); plt.close(fig)


def _transfer_report(summary: pd.DataFrame) -> str:
    lines = ["# Week 12 strict OLD→NEW model transfer", "", "This is post-hoc developmental evidence. Models and scalers were fitted on OLD-405 only; NEW-136 labels were used only for evaluation.", "", "| Subset | Model | Fit status | ROC AUC | PR AUC Keyhole | Balanced accuracy | Brier |", "|---|---|---|---:|---:|---:|---:|"]
    for row in summary.itertuples(index=False):
        lines.append(f"| {row.subset} | {row.model} | {row.fit_status} | {row.roc_auc:.4f} | {row.pr_auc_keyhole:.4f} | {row.balanced_accuracy:.4f} | {row.brier:.4f} |" if np.isfinite(row.roc_auc) else f"| {row.subset} | {row.model} | {row.fit_status} | NA | NA | NA | NA |")
    lines.extend(["", "The empirical prior is the OLD-405 Keyhole prevalence. ARD length scales are standardized-space geometry diagnostics, not causal feature importance. The class-stratified bootstrap and calibration bands are descriptive uncertainty conditional on these fixed predictions and cohort class counts; they are not independent-campaign intervals. Leave-one-negative-out results expose fragility from the 12 NEW non-keyholes and do not refit models."])
    return "\n".join(lines) + "\n"


def run_new_only() -> dict[str, Any]:
    new = load_new()
    root = OUT / "models/new_only"
    root.mkdir(parents=True, exist_ok=True)
    splits = load_splits()
    write_json(root / "config.json", {**_provenance("new_only", new, load_old()), "split_source": "Week 11 original 100 frozen splits", "training_scope": "NEW training rows only", "q20_scope": "entire_evaluation_batch", "models": list(MODELS), "computational_notes": "100 frozen folds x five models; M3 Laplace GP optimization is the dominant O(n^3) fit cost. No model tuning or nested selection."})
    write_json(root / "provenance.json", {**_provenance("new_only", new, load_old()), "split_manifest_sha256": sha(HIST / "split_manifest.json")})
    predictions, diagnostics, metric_rows = [], [], []
    y = new.has_keyhole.to_numpy(int)
    checkpoint_root = root / "checkpoints"
    with threadpool_limits(limits=1):
        for split in splits:
            train, test = np.asarray(split["train_indices"], int), np.asarray(split["test_indices"], int)
            flags = _subset_flags(new, test)
            split_predictions, split_diagnostics, split_metrics = [], [], []
            for name in MODELS:
                pframe, diag = _fit_predict(name, new, train, test, seed("new_only", split["split_id"], name), float(y[train].mean()))
                pframe["split_id"] = split["split_id"]; pframe["repeat"] = int(split["repeat"]); pframe["fold"] = int(split["fold"])
                flag_map = {int(idx): bool(flag) for idx, flag in zip(test, flags[20])}
                flag30_map = {int(idx): bool(flag) for idx, flag in zip(test, flags[30])}
                pframe["is_q20"] = pframe.row_index.map(flag_map).astype(bool)
                pframe["is_q30"] = pframe.row_index.map(flag30_map).astype(bool)
                split_predictions.append(pframe); diag.update({"split_id": split["split_id"], "repeat": int(split["repeat"]), "fold": int(split["fold"]), "test_n": int(len(test)), "test_keyhole": int(y[test].sum()), "test_non_keyhole": int((y[test] == 0).sum())}); split_diagnostics.append(diag)
                ordered = pframe.set_index("row_index").loc[test]
                p = ordered.probability.to_numpy(float)
                for subset, mask in [("full", np.ones(len(test), bool)), ("q20", flags[20]), ("q30", flags[30])]:
                    sub_y, sub_p = y[test][mask], p[mask]
                    metric = metrics(sub_y, sub_p) if np.isfinite(sub_p).all() else _failure_metrics(sub_y)
                    split_metrics.append({"split_id": split["split_id"], "repeat": int(split["repeat"]), "fold": int(split["fold"]), "model": name, "subset": subset, **metric, "fit_status": diag.get("fit_status", "ok")})
            predictions.extend(split_predictions); diagnostics.extend(split_diagnostics); metric_rows.extend(split_metrics)
            write_json(checkpoint_root / f"{split['split_id']}.json", {"split_id": split["split_id"], "status": "retained", "predictions": split_predictions, "diagnostics": split_diagnostics, "metrics": split_metrics})
    pred = pd.concat(predictions, ignore_index=True); metric_frame = pd.DataFrame(metric_rows)
    write_csv(root / "predictions.csv.gz", pred); write_csv(root / "metrics.csv.gz", metric_frame); write_json(root / "fit_diagnostics.json", diagnostics)
    _new_only_summary(metric_frame, pred, root)
    qc = _write_qc(root, pred, diagnostics)
    write_json(root / "summary.json", {"mode": "new_only", "splits": len(splits), "qc": qc, "pooled_oof": "pooled_oof_per_repeat.csv", "fold_summary": "summary.csv"})
    return {"status": qc["status"], "mode": "new_only", "splits": len(splits), "output": str(root)}


def _new_only_summary(metrics_frame: pd.DataFrame, predictions: pd.DataFrame, root: Path) -> None:
    rows = []
    for (model, subset), group in metrics_frame.groupby(["model", "subset"], sort=True):
        repeat = group.groupby("repeat", as_index=False).agg(value=("accuracy", "mean"))
        rows.append({"evaluation_unit": "fold_average", "model": model, "subset": subset, "fold_mean_accuracy": float(group.accuracy.mean()), "repeat_mean_accuracy": float(repeat.value.mean()), "repeat_sd_accuracy": float(repeat.value.std(ddof=1)), "fold_mean_balanced_accuracy": float(group.balanced_accuracy.mean()), "fold_mean_roc_auc": float(group.roc_auc.mean()), "fold_mean_pr_auc_keyhole": float(group.pr_auc_keyhole.mean()), "finite_fold_count": int(group.accuracy.notna().sum()), "finite_fold_balanced_accuracy_count": int(group.balanced_accuracy.notna().sum()), "finite_fold_roc_auc_count": int(group.roc_auc.notna().sum()), "fold_count": int(len(group)), "interpretation": "conditional partition variability over original 100 frozen splits; missing-class metrics remain NaN"})
    pooled_rows = []
    for (model, repeat), group in predictions.groupby(["model", "repeat"], sort=True):
        for subset in ("full", "q20", "q30"):
            mask = np.ones(len(group), bool) if subset == "full" else group["is_q20" if subset == "q20" else "is_q30"].to_numpy(bool)
            selected = group.loc[mask].sort_values("row_index")
            y = selected.truth.to_numpy(int); p = selected.probability.to_numpy(float)
            m = metrics(y, p) if len(selected) and np.isfinite(p).all() else _failure_metrics(y)
            pooled_rows.append({"model": model, "repeat": int(repeat), "subset": subset, **m})
    pooled = pd.DataFrame(pooled_rows)
    write_csv(root / "pooled_oof_per_repeat.csv", pooled)
    for (model, subset), group in pooled.groupby(["model", "subset"], sort=True):
        rows.append({"evaluation_unit": "pooled_oof_per_repeat", "model": model, "subset": subset, "fold_mean_accuracy": np.nan, "repeat_mean_accuracy": float(group.accuracy.mean()), "repeat_sd_accuracy": float(group.accuracy.std(ddof=1)), "fold_mean_balanced_accuracy": float(group.balanced_accuracy.mean()), "fold_mean_roc_auc": float(group.roc_auc.mean()), "fold_mean_pr_auc_keyhole": float(group.pr_auc_keyhole.mean()), "finite_fold_count": int(group.accuracy.notna().sum()), "finite_fold_balanced_accuracy_count": int(group.balanced_accuracy.notna().sum()), "finite_fold_roc_auc_count": int(group.roc_auc.notna().sum()), "fold_count": int(len(group)), "interpretation": "pooled OOF per repeat; conditional partition variability, not campaign CI"})
    write_csv(root / "summary.csv", pd.DataFrame(rows))
    (root / "REPORT.md").write_text("# Week 12 NEW-only model CV\n\nThis is post-hoc developmental cross-validation on NEW-136. The original 100 Week 11 splits are reused; model training uses only each NEW training partition. q20 uses the frozen entire-evaluation-batch construction and remains evaluation-only. Repeat summaries describe conditional partition variability, not independent-campaign uncertainty.\n", encoding="utf-8")


def summarize() -> dict[str, Any]:
    for mode in ("transfer", "new_only"):
        root = OUT / "models" / mode
        if not (root / "summary.csv").exists():
            continue
    return {"status": "PASS", "mode": "summarize", "available": [m for m in ("transfer", "new_only") if (OUT / "models" / m / "summary.csv").exists()]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("transfer", "new-only", "summarize"), required=True)
    args = parser.parse_args()
    if args.mode == "transfer":
        result = run_transfer()
    elif args.mode == "new-only":
        result = run_new_only()
    else:
        result = summarize()
    print(json.dumps(safe(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
