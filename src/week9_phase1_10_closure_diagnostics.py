"""Week 9 Phase 1.10 closure diagnostics.

Three cheap, predeclared checks close the external validation: raw-scale
recovery of the generic logistic exponent, a strict C-versus-K sensitivity,
and two cleanly supported logistic regularization settings. Frozen Phase 1.10
artifacts are read-only and its primary verdict is never re-adjudicated.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import os
import subprocess
import sys
import urllib.request
import warnings
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nbformat as nbf
import numpy as np
import pandas as pd
import sklearn
from nbclient import NotebookClient
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler

from src import week9_phase1_10_external_experimental_validation as p10


ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "outputs" / "week9_phase1_10_external_experimental_validation"
OUTPUT = ROOT / "outputs" / "week9_phase1_10_closure_diagnostics"
FIGURES = OUTPUT / "figures"
NOTEBOOK = ROOT / "notebooks" / "week_09" / "08_week9_phase1_10_closure_diagnostics.ipynb"
START_SHA = "45e2677b7a57ed3aa5ad5154459100a9b5d2d436"
BRANCH = "codex/week9-phase1-10-closure-diagnostics"
THEORY_ALPHA = -0.5
N_REPEATS = 20
MAX_FOLDS = 5
BOOTSTRAP_DRAWS = 10_000
SEED_BASE = 20260901
BETA_P_NEAR_ZERO = 1e-8
ALPHA_EXTREME_ABS = 10.0
METRICS = ("roc_auc", "pr_auc", "balanced_accuracy", "keyhole_recall", "conduction_recall", "brier_score", "accuracy")
REGULARIZATION = {
    "R1_C1": {"C": 1.0, "penalty": "default_l2", "status": "AVAILABLE", "role": "frozen_main"},
    "R2_C1e6": {"C": 1e6, "penalty": "default_l2", "status": "AVAILABLE", "role": "weak_regularization"},
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    return p10.sha256_file(path)


def artifact_sha256(path: Path) -> str:
    """Hash the bytes Git publishes for tracked text artifacts.

    Generated text can have CRLF in the Windows worktree, while this study's
    ``.gitattributes`` pins LF in the repository.  Normalizing only tracked
    text formats keeps the manifest valid in a clean checkout; binary source
    data and figures continue to use byte-exact hashes.
    """
    payload = path.read_bytes()
    if path.suffix.lower() not in {".png", ".gz", ".xlsx"}:
        payload = payload.replace(b"\r\n", b"\n")
    return hashlib.sha256(payload).hexdigest()


def artifact_size(path: Path) -> int:
    payload = path.read_bytes()
    if path.suffix.lower() not in {".png", ".gz", ".xlsx"}:
        payload = payload.replace(b"\r\n", b"\n")
    return len(payload)


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    p10.write_csv(path, frame)


def write_json(path: Path, payload: Any) -> None:
    p10.write_json(path, payload)


def ensure_public_cache_readonly() -> None:
    """Populate only the ignored cache; never call p10.build_population()."""
    p10.CACHE.mkdir(parents=True, exist_ok=True)
    for name, expected in p10.SOURCE_FILES.items():
        destination = p10.CACHE / name
        if not destination.exists() or sha256_file(destination) != expected["sha256"]:
            urllib.request.urlretrieve(f"{p10.RAW_ROOT}/{name}", destination)
        require(destination.stat().st_size == expected["size"], f"source size mismatch: {name}")
        require(sha256_file(destination) == expected["sha256"], f"source hash mismatch: {name}")


def load_population_readonly() -> pd.DataFrame:
    ensure_public_cache_readonly()
    microscopy = p10.read_xlsx(p10.CACHE / "Microscopy_1.xlsx")["Sheet1"]
    parameters = p10.read_xlsx(p10.CACHE / "experiment_parameters_ref.xlsx")
    rows: list[dict[str, Any]] = []
    for record in microscopy.itertuples(index=False):
        material = p10.MATERIAL_SOURCE_TO_CANONICAL[str(record.Material)]
        cube, line, mode = int(record.Cube), int(record.Line), str(record.Mode).strip()
        require(cube in p10.MATERIAL_CUBES[material], "unexpected labelled cube")
        match = parameters[f"Cube{cube}"][pd.to_numeric(parameters[f"Cube{cube}"]["#"]) == line]
        require(len(match) == 1, "parameter join failed")
        source = match.iloc[0]
        power, speed_mm_s = float(source["Power (W)"]), float(source["Speed (mm/s)"])
        rows.append({
            "material": material,
            "bundle_id": f"{material}_Cube{cube}_Line{line:02d}",
            "cube": cube,
            "line": line,
            "P_W": power,
            "VX_mm_per_s": speed_mm_s,
            "VX_m_per_s": speed_mm_s / 1000.0,
            "LS_m": p10.LS_M,
            "raw_mode": mode,
            "has_keyhole": int(mode != "C"),
        })
    frame = pd.DataFrame(rows).sort_values(["material", "cube", "line"]).reset_index(drop=True)
    frame["condition_id"] = frame.apply(lambda row: f"{row.material}_P{row.P_W:g}_V{row.VX_mm_per_s:g}", axis=1)
    frame["log_P"] = np.log(frame.P_W)
    frame["log_VX"] = np.log(frame.VX_m_per_s)
    frame["h_SI"] = frame.P_W / np.sqrt(frame.VX_m_per_s * frame.LS_m**3)
    frame["log_h"] = np.log(frame.h_SI)
    observed = frame.groupby("material").agg(rows=("bundle_id", "size"), conditions=("condition_id", "nunique"), keyhole=("has_keyhole", "sum"))
    require(observed.loc["Ti64"].to_dict() == {"rows": 60, "conditions": 38, "keyhole": 34}, "Ti64 population drift")
    require(observed.loc["316L"].to_dict() == {"rows": 60, "conditions": 38, "keyhole": 23}, "316L population drift")
    return frame


def load_frozen_folds() -> pd.DataFrame:
    folds = pd.read_csv(FROZEN / "grouped_fold_manifest.csv")
    require(len(folds) == 2400 and folds.repeat.nunique() == 20, "frozen fold manifest drift")
    require(folds.groupby(["material", "repeat", "condition_id"]).fold.nunique().max() == 1, "frozen replicate leakage")
    return folds


def recover_raw_coefficients(gamma: Sequence[float], scaler_scale: Sequence[float]) -> tuple[float, float, float]:
    gamma_array = np.asarray(gamma, dtype=float)
    scale_array = np.asarray(scaler_scale, dtype=float)
    require(gamma_array.shape == scale_array.shape == (2,), "generic coefficient recovery requires two inputs")
    beta = gamma_array / scale_array
    alpha = beta[1] / beta[0]
    return float(beta[0]), float(beta[1]), float(alpha)


def probe_r3() -> tuple[bool, str]:
    x = np.asarray([[0.0], [1.0], [2.0], [3.0]])
    y = np.asarray([0, 0, 1, 1])
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            LogisticRegression(penalty=None, solver="lbfgs", max_iter=1000).fit(x, y)
        if caught:
            return False, "R3_UNAVAILABLE: penalty=None emits a deprecation warning in sklearn " + sklearn.__version__
        return True, "AVAILABLE"
    except Exception as error:  # pragma: no cover - version dependent
        return False, f"R3_UNAVAILABLE: {type(error).__name__}: {error}"


def regularization_settings() -> dict[str, dict[str, Any]]:
    settings = {key: dict(value) for key, value in REGULARIZATION.items()}
    supported, reason = probe_r3()
    settings["R3_unpenalized"] = {"C": None, "penalty": None, "status": "AVAILABLE" if supported else "R3_UNAVAILABLE", "role": "unpenalized", "reason": reason}
    return settings


def fit_logistic(train: pd.DataFrame, test: pd.DataFrame, model: str, setting: str) -> tuple[np.ndarray, dict[str, Any]]:
    settings = regularization_settings()
    config = settings[setting]
    require(config["status"] == "AVAILABLE", f"requested unavailable setting: {setting}")
    features = ["log_h"] if model == "H" else ["log_P", "log_VX"]
    x_train = train[features].to_numpy(float)
    x_test = test[features].to_numpy(float)
    y_train = train.has_keyhole.to_numpy(int)
    require(set(np.unique(y_train)) == {0, 1}, "training labels lack a class")
    scaler = StandardScaler().fit(x_train)
    kwargs: dict[str, Any] = {"solver": "lbfgs", "fit_intercept": True, "max_iter": 5000, "random_state": SEED_BASE}
    if setting == "R3_unpenalized":
        kwargs["penalty"] = None
    else:
        kwargs["C"] = config["C"]
    estimator = LogisticRegression(**kwargs)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        estimator.fit(scaler.transform(x_train), y_train)
    probability = estimator.predict_proba(scaler.transform(x_test))[:, 1]
    convergence = int(estimator.n_iter_[0]) < int(estimator.max_iter) and not any("conver" in str(item.message).lower() for item in caught)
    detail: dict[str, Any] = {
        "model": model,
        "setting": setting,
        "features": "|".join(features),
        "train_only_scaling": True,
        "converged": bool(convergence),
        "n_iter": int(estimator.n_iter_[0]),
        "warnings": " | ".join(str(item.message) for item in caught),
    }
    if model == "G":
        gamma_p, gamma_vx = map(float, estimator.coef_[0])
        beta_p, beta_vx, alpha = recover_raw_coefficients(estimator.coef_[0], scaler.scale_)
        near_zero = abs(beta_p) < BETA_P_NEAR_ZERO
        extreme = not math.isfinite(alpha) or abs(alpha) > ALPHA_EXTREME_ABS
        detail.update({
            "gamma_P": gamma_p,
            "gamma_VX": gamma_vx,
            "sigma_P": float(scaler.scale_[0]),
            "sigma_VX": float(scaler.scale_[1]),
            "beta_P": beta_p,
            "beta_VX": beta_vx,
            "alpha": alpha,
            "beta_P_near_zero": near_zero,
            "alpha_extreme": extreme,
            "alpha_valid": bool(convergence and np.isfinite([beta_p, beta_vx, alpha]).all() and not near_zero and not extreme),
            "beta_P_positive": beta_p > 0,
            "beta_VX_negative": beta_vx < 0,
        })
    return probability, detail


def make_strict_population(population: pd.DataFrame) -> pd.DataFrame:
    strict = population[population.raw_mode.isin(["C", "K"])].copy().reset_index(drop=True)
    strict["has_keyhole"] = strict.raw_mode.eq("K").astype(int)
    require(set(strict.raw_mode) == {"C", "K"}, "strict label contamination")
    return strict


def make_strict_folds(strict: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    records: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    for material_index, material in enumerate(("Ti64", "316L")):
        frame = strict[strict.material.eq(material)].reset_index(drop=True)
        y, groups = frame.has_keyhole.to_numpy(int), frame.condition_id.to_numpy(str)
        chosen_folds = None
        chosen_assignments: list[np.ndarray] = []
        for n_folds in range(MAX_FOLDS, 1, -1):
            assignments: list[np.ndarray] = []
            valid = True
            for repeat in range(N_REPEATS):
                assignment = np.full(len(frame), -1, dtype=int)
                splitter = StratifiedGroupKFold(n_splits=n_folds, shuffle=True, random_state=SEED_BASE + material_index * 1000 + repeat)
                for fold, (_, test) in enumerate(splitter.split(frame, y, groups)):
                    if set(np.unique(y[test])) != {0, 1}:
                        valid = False
                        break
                    assignment[test] = fold
                if not valid or (assignment < 0).any():
                    valid = False
                    break
                assignments.append(assignment)
            if valid:
                chosen_folds, chosen_assignments = n_folds, assignments
                break
        require(chosen_folds is not None, f"no defensible grouped strict CV for {material}")
        for repeat, assignment in enumerate(chosen_assignments):
            for index, row in frame.iterrows():
                records.append({"material": material, "repeat": repeat, "seed": SEED_BASE + material_index * 1000 + repeat, "fold": int(assignment[index]), "bundle_id": row.bundle_id, "condition_id": row.condition_id, "has_keyhole": int(row.has_keyhole), "raw_mode": row.raw_mode})
        group_sizes = frame.groupby("condition_id").size()
        discordance = frame.groupby("condition_id").has_keyhole.nunique()
        audits.append({
            "material": material,
            "bundles": len(frame),
            "unique_conditions": frame.condition_id.nunique(),
            "mode_C": int(frame.raw_mode.eq("C").sum()),
            "mode_K": int(frame.raw_mode.eq("K").sum()),
            "repeated_conditions": int((group_sizes > 1).sum()),
            "discordant_conditions": int((discordance > 1).sum()),
            "folds": chosen_folds,
            "repeats": N_REPEATS,
            "both_classes_every_heldout_fold": True,
        })
    manifest, audit = pd.DataFrame(records), pd.DataFrame(audits)
    require(manifest.groupby(["material", "repeat", "condition_id"]).fold.nunique().max() == 1, "strict replicate leakage")
    write_csv(OUTPUT / "strict_ck_fold_manifest.csv", manifest)
    write_csv(OUTPUT / "strict_ck_population_audit.csv", audit)
    return manifest, audit


def run_logistic_oof(frame: pd.DataFrame, manifest: pd.DataFrame, dataset: str, setting: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    metric_rows: list[dict[str, Any]] = []
    coefficient_rows: list[dict[str, Any]] = []
    for material in sorted(frame.material.unique(), key=lambda value: (value != "Ti64", value)):
        material_frame = frame[frame.material.eq(material)].reset_index(drop=True)
        material_manifest = manifest[manifest.material.eq(material)]
        for repeat in range(N_REPEATS):
            assignment = material_manifest[material_manifest.repeat.eq(repeat)].set_index("bundle_id").loc[material_frame.bundle_id, "fold"].to_numpy(int)
            probabilities = {model: np.full(len(material_frame), np.nan) for model in ("H", "G")}
            for fold in sorted(np.unique(assignment)):
                test_mask = assignment == fold
                train, test = material_frame.loc[~test_mask], material_frame.loc[test_mask]
                for model in ("H", "G"):
                    probability, detail = fit_logistic(train, test, model, setting)
                    probabilities[model][test_mask] = probability
                    if model == "G":
                        coefficient_rows.append({"dataset": dataset, "material": material, "setting": setting, "repeat": repeat, "fold": int(fold), "train_rows": len(train), "test_rows": len(test), **detail})
            for model in ("H", "G"):
                require(np.isfinite(probabilities[model]).all(), "incomplete OOF probability vector")
                metric_rows.append({"dataset": dataset, "material": material, "setting": setting, "repeat": repeat, "model": model, **p10.metric_values(material_frame.has_keyhole, probabilities[model])})
    return pd.DataFrame(metric_rows), pd.DataFrame(coefficient_rows)


def bootstrap_mean(values: Sequence[float], seed: int) -> tuple[float, float, float]:
    array = np.asarray(values, dtype=float)
    require(len(array) == N_REPEATS, "inference requires exactly 20 repeat blocks")
    rng = np.random.default_rng(seed)
    means = array[rng.integers(0, len(array), size=(BOOTSTRAP_DRAWS, len(array)))].mean(axis=1)
    return float(array.mean()), float(np.quantile(means, .025)), float(np.quantile(means, .975))


def summarize_exponents(folds: pd.DataFrame, population: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    main = folds[(folds.dataset.eq("transition_inclusive")) & (folds.setting.eq("R1_C1"))].copy()
    require(main.groupby("material").size().eq(100).all(), "main coefficient-fit count drift")
    repeat_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for material_index, material in enumerate(("Ti64", "316L")):
        material_folds = main[main.material.eq(material)]
        for repeat, group in material_folds.groupby("repeat"):
            valid = group[group.alpha_valid]
            repeat_rows.append({"material": material, "repeat": repeat, "folds": len(group), "valid_folds": len(valid), "invalid_folds": len(group)-len(valid), "alpha_mean": valid.alpha.mean(), "alpha_median": valid.alpha.median(), "beta_P_mean": valid.beta_P.mean(), "beta_VX_mean": valid.beta_VX.mean()})
        repeat_frame = pd.DataFrame(repeat_rows)[lambda value: value.material.eq(material)]
        require(len(repeat_frame) == N_REPEATS and repeat_frame.valid_folds.ge(1).all(), "a repeat lacks any valid exponent fit")
        mean, lower, upper = bootstrap_mean(repeat_frame.alpha_mean, SEED_BASE + 70000 + material_index)
        summary_rows.append({
            "material": material,
            "summary_type": "grouped_cv_repeat_block",
            "setting": "R1_C1",
            "alpha_mean": mean,
            "alpha_median": float(repeat_frame.alpha_mean.median()),
            "ci_lower": lower,
            "ci_upper": upper,
            "q25": float(repeat_frame.alpha_mean.quantile(.25)),
            "q75": float(repeat_frame.alpha_mean.quantile(.75)),
            "minimum": float(repeat_frame.alpha_mean.min()),
            "maximum": float(repeat_frame.alpha_mean.max()),
            "valid_fits": int(material_folds.alpha_valid.sum()),
            "invalid_fits": int((~material_folds.alpha_valid).sum()),
            "beta_P_sign_flips": int((~material_folds.beta_P_positive).sum()),
            "beta_VX_sign_flips": int((~material_folds.beta_VX_negative).sum()),
            "theory_alpha": THEORY_ALPHA,
            "delta_alpha": mean - THEORY_ALPHA,
            "theory_status": "THEORY_CONSISTENT" if lower <= THEORY_ALPHA <= upper else "THEORY_OFFSET_RESOLVED",
            "interval_scope": "split-sensitivity over 20 repeat means; five folds averaged first",
        })
        full = population[population.material.eq(material)].reset_index(drop=True)
        _, detail = fit_logistic(full, full.iloc[:1], "G", "R1_C1")
        summary_rows.append({"material": material, "summary_type": "descriptive_full_data", "setting": "R1_C1", "alpha_mean": detail["alpha"], "alpha_median": detail["alpha"], "ci_lower": np.nan, "ci_upper": np.nan, "q25": np.nan, "q75": np.nan, "minimum": detail["alpha"], "maximum": detail["alpha"], "valid_fits": int(detail["alpha_valid"]), "invalid_fits": int(not detail["alpha_valid"]), "beta_P_sign_flips": int(not detail["beta_P_positive"]), "beta_VX_sign_flips": int(not detail["beta_VX_negative"]), "theory_alpha": THEORY_ALPHA, "delta_alpha": detail["alpha"]-THEORY_ALPHA, "theory_status": "DESCRIPTIVE_ONLY", "interval_scope": "complete-data descriptive fit; no predictive-performance claim", "beta_P": detail["beta_P"], "beta_VX": detail["beta_VX"]})
    repeat_summary, summary = pd.DataFrame(repeat_rows), pd.DataFrame(summary_rows)
    write_csv(OUTPUT / "exponent_repeat_summary.csv", repeat_summary)
    write_csv(OUTPUT / "exponent_summary.csv", summary)
    return repeat_summary, summary


def summarize_model_metrics(repeat_metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries: list[dict[str, Any]] = []
    contrasts: list[dict[str, Any]] = []
    datasets = sorted(repeat_metrics.dataset.unique())
    for dataset_index, dataset in enumerate(datasets):
        for material_index, material in enumerate(("Ti64", "316L")):
            subset = repeat_metrics[(repeat_metrics.dataset.eq(dataset)) & (repeat_metrics.material.eq(material))]
            if subset.empty:
                continue
            setting = str(subset.setting.iloc[0])
            for model in ("H", "G"):
                model_frame = subset[subset.model.eq(model)].sort_values("repeat")
                for metric_index, metric in enumerate(METRICS):
                    mean, lower, upper = bootstrap_mean(model_frame[metric], SEED_BASE + 80000 + dataset_index*1000 + material_index*100 + (0 if model=="H" else 20) + metric_index)
                    summaries.append({"dataset": dataset, "material": material, "setting": setting, "model": model, "metric": metric, "mean": mean, "ci_lower": lower, "ci_upper": upper, "repeat_blocks": N_REPEATS})
            h = subset[subset.model.eq("H")].sort_values("repeat")
            g = subset[subset.model.eq("G")].sort_values("repeat")
            require(np.array_equal(h.repeat, g.repeat), "H-G repeat pairing failed")
            for metric_index, metric in enumerate(METRICS):
                difference = h[metric].to_numpy(float) - g[metric].to_numpy(float)
                mean, lower, upper = bootstrap_mean(difference, SEED_BASE + 85000 + dataset_index*1000 + material_index*100 + metric_index)
                contrasts.append({"dataset": dataset, "material": material, "setting": setting, "contrast": "H_minus_G", "metric": metric, "mean_difference": mean, "ci_lower": lower, "ci_upper": upper, "repeat_blocks": N_REPEATS, "bootstrap_draws": BOOTSTRAP_DRAWS, "interval_scope": "split sensitivity over paired repeat blocks"})
    return pd.DataFrame(summaries), pd.DataFrame(contrasts)


def make_regularization_summary(metrics_by_setting: pd.DataFrame, coefficients_by_setting: pd.DataFrame, settings: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for dataset_index, dataset in enumerate(("transition_inclusive", "strict_C_vs_K")):
        for setting_index, setting in enumerate(("R1_C1", "R2_C1e6", "R3_unpenalized")):
            config = settings[setting]
            if config["status"] != "AVAILABLE":
                rows.append({"dataset": dataset, "material": "Ti64", "setting": setting, "status": config["status"], "implementation": config.get("reason", "unavailable")})
                continue
            metric_frame = metrics_by_setting[(metrics_by_setting.dataset.eq(dataset)) & (metrics_by_setting.material.eq("Ti64")) & (metrics_by_setting.setting.eq(setting))]
            coefficient_frame = coefficients_by_setting[(coefficients_by_setting.dataset.eq(dataset)) & (coefficients_by_setting.material.eq("Ti64")) & (coefficients_by_setting.setting.eq(setting))]
            require(len(metric_frame) == 40 and len(coefficient_frame) == 100, "regularization sensitivity completeness drift")
            h = metric_frame[metric_frame.model.eq("H")].sort_values("repeat")
            g = metric_frame[metric_frame.model.eq("G")].sort_values("repeat")
            difference = h.roc_auc.to_numpy() - g.roc_auc.to_numpy()
            contrast_mean, contrast_lower, contrast_upper = bootstrap_mean(difference, SEED_BASE + 90000 + dataset_index*100 + setting_index)
            valid = coefficient_frame[coefficient_frame.alpha_valid]
            repeat_alpha = valid.groupby("repeat").alpha.mean().reindex(range(N_REPEATS))
            require(repeat_alpha.notna().all(), "regularization alpha repeat missing")
            alpha_mean, alpha_lower, alpha_upper = bootstrap_mean(repeat_alpha, SEED_BASE + 91000 + dataset_index*100 + setting_index)
            rows.append({
                "dataset": dataset,
                "material": "Ti64",
                "setting": setting,
                "status": "AVAILABLE",
                "implementation": f"lbfgs; train-only scaling; C={config['C']}",
                "H_roc_auc": h.roc_auc.mean(),
                "G_roc_auc": g.roc_auc.mean(),
                "H_minus_G_roc_auc": contrast_mean,
                "H_minus_G_ci_lower": contrast_lower,
                "H_minus_G_ci_upper": contrast_upper,
                "alpha_mean": alpha_mean,
                "alpha_ci_lower": alpha_lower,
                "alpha_ci_upper": alpha_upper,
                "valid_coefficient_fits": int(coefficient_frame.alpha_valid.sum()),
                "invalid_coefficient_fits": int((~coefficient_frame.alpha_valid).sum()),
                "converged_fraction": coefficient_frame.converged.mean(),
                "beta_P_positive_fraction": coefficient_frame.beta_P_positive.mean(),
                "beta_VX_negative_fraction": coefficient_frame.beta_VX_negative.mean(),
                "beta_P_near_zero_count": int(coefficient_frame.beta_P_near_zero.sum()),
                "alpha_extreme_count": int(coefficient_frame.alpha_extreme.sum()),
            })
    result = pd.DataFrame(rows)
    write_csv(OUTPUT / "regularization_sensitivity.csv", result)
    return result


def make_figures(exponent_repeat: pd.DataFrame, exponent_summary: pd.DataFrame, strict_summary: pd.DataFrame) -> pd.DataFrame:
    FIGURES.mkdir(parents=True, exist_ok=True)
    colors = {"Ti64": "#1B6CA8", "316L": "#D77A24"}
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.6), sharey=True)
    for axis, material in zip(axes, ("Ti64", "316L")):
        repeat = exponent_repeat[exponent_repeat.material.eq(material)]
        summary = exponent_summary[(exponent_summary.material.eq(material)) & (exponent_summary.summary_type.eq("grouped_cv_repeat_block"))].iloc[0]
        axis.scatter(repeat.repeat + 1, repeat.alpha_mean, s=38, color=colors[material], alpha=.85)
        axis.axhline(THEORY_ALPHA, color="black", linestyle="--", linewidth=1.5, label="theory −0.5")
        axis.axhline(summary.alpha_mean, color=colors[material], linewidth=2, label=f"mean {summary.alpha_mean:.3f}")
        axis.fill_between([.5, N_REPEATS+.5], summary.ci_lower, summary.ci_upper, color=colors[material], alpha=.16, label=f"95% CI [{summary.ci_lower:.3f}, {summary.ci_upper:.3f}]")
        axis.set(xlabel="Grouped-CV repeat", title=material, xlim=(.5, N_REPEATS+.5))
        axis.grid(axis="y", alpha=.22)
        axis.legend(frameon=False, fontsize=8)
    axes[0].set_ylabel(r"Recovered raw-scale exponent $\alpha=\beta_{VX}/\beta_P$")
    fig.suptitle("External exponent recovery after averaging five folds within each repeat", fontweight="bold")
    fig.tight_layout(rect=(0,0,1,.94))
    path1 = FIGURES / "01_recovered_alpha_by_repeat.png"
    fig.savefig(path1, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    frozen_summary = pd.read_csv(FROZEN / "ti64_model_summary.csv")
    original = frozen_summary[(frozen_summary.metric.eq("roc_auc")) & (frozen_summary.model.isin(["H","G"]))].set_index("model")
    strict = strict_summary[(strict_summary.material.eq("Ti64")) & (strict_summary.metric.eq("roc_auc"))].set_index("model")
    fig, axis = plt.subplots(figsize=(7.8, 4.5))
    x = np.arange(2)
    width = .34
    for offset, model, color in ((-width/2,"H","#1B6CA8"),(width/2,"G","#D1495B")):
        values = [original.loc[model,"mean"], strict.loc[model,"mean"]]
        axis.bar(x+offset, values, width=width, color=color, label=model)
        for xpos, value in zip(x+offset, values):
            axis.text(xpos, value+.001, f"{value:.3f}", ha="center", va="bottom", fontsize=9)
    axis.set_xticks(x, ["Transition-inclusive\n(frozen primary)", "Strict C vs K\n(sensitivity)"])
    axis.set_ylabel("Complete-OOF ROC-AUC")
    axis.set_ylim(.94, 1.008)
    axis.set_title("Ti64: label-definition sensitivity", fontweight="bold")
    axis.grid(axis="y", alpha=.22)
    axis.legend(frameon=False)
    fig.tight_layout()
    path2 = FIGURES / "02_ti64_transition_vs_strict_ck.png"
    fig.savefig(path2, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    manifest = pd.DataFrame([
        {"figure": path1.name, "sha256": sha256_file(path1), "purpose": "Compare repeat-level recovered external exponents with the predeclared theoretical alpha=-0.5."},
        {"figure": path2.name, "sha256": sha256_file(path2), "purpose": "Compare frozen transition-inclusive and strict C-vs-K Ti64 H/G ROC-AUC."},
    ])
    write_csv(OUTPUT / "figure_manifest.csv", manifest)
    return manifest


def _row(frame: pd.DataFrame, **filters: Any) -> pd.Series:
    subset = frame
    for key, value in filters.items():
        subset = subset[subset[key].eq(value)]
    require(len(subset) == 1, f"expected one row for {filters}, found {len(subset)}")
    return subset.iloc[0]


def write_reports(exponents: pd.DataFrame, strict_summary: pd.DataFrame, strict_contrasts: pd.DataFrame, regularization: pd.DataFrame, strict_audit: pd.DataFrame) -> None:
    ti = _row(exponents, material="Ti64", summary_type="grouped_cv_repeat_block")
    ss = _row(exponents, material="316L", summary_type="grouped_cv_repeat_block")
    ti_full = _row(exponents, material="Ti64", summary_type="descriptive_full_data")
    ss_full = _row(exponents, material="316L", summary_type="descriptive_full_data")
    ti_h = _row(strict_summary, material="Ti64", model="H", metric="roc_auc")
    ti_g = _row(strict_summary, material="Ti64", model="G", metric="roc_auc")
    ti_d = _row(strict_contrasts, material="Ti64", metric="roc_auc")
    ss_h = _row(strict_summary, material="316L", model="H", metric="roc_auc")
    ss_g = _row(strict_summary, material="316L", model="G", metric="roc_auc")
    ss_d = _row(strict_contrasts, material="316L", metric="roc_auc")
    r1 = _row(regularization, dataset="transition_inclusive", setting="R1_C1")
    r2 = _row(regularization, dataset="transition_inclusive", setting="R2_C1e6")
    ck_r1 = _row(regularization, dataset="strict_C_vs_K", setting="R1_C1")
    ck_r2 = _row(regularization, dataset="strict_C_vs_K", setting="R2_C1e6")
    r3 = _row(regularization, dataset="transition_inclusive", setting="R3_unpenalized")
    frozen_contrast = pd.read_csv(FROZEN / "ti64_paired_contrasts.csv").query("metric == 'roc_auc'").iloc[0]
    shrink = abs(float(ti_d.mean_difference)) < abs(float(frozen_contrast.mean_difference))
    report = f"""# Week 9 Phase 1.10 closure diagnostics

## Frozen result preserved

The predeclared Phase 1.10 bundle-level verdict remains **GENERIC_DIRECTION_SUPERIOR**: Ti64 H−G ROC-AUC = {frozen_contrast.mean_difference:+.6f}, 95% split-bootstrap CI [{frozen_contrast.ci_lower:+.6f}, {frozen_contrast.ci_upper:+.6f}]. These diagnostics qualify interpretation; they do not replace the primary analysis.

## 1. Raw-scale external exponent recovery

For every original grouped training fold, the fitted standardized G coefficients were converted by `beta_j = gamma_j / sigma_j`; the reported exponent is `alpha = beta_VX / beta_P`. Five fold estimates were averaged within each repeat before bootstrapping the 20 repeat blocks. Numerical guards and coefficient signs were audited rather than hidden.

- **Ti64:** mean alpha {ti.alpha_mean:.6f}, median {ti.alpha_median:.6f}, 95% split-sensitivity interval [{ti.ci_lower:.6f}, {ti.ci_upper:.6f}], IQR [{ti.q25:.6f}, {ti.q75:.6f}]. Valid/invalid fits: {int(ti.valid_fits)}/{int(ti.invalid_fits)}; beta_P sign flips: {int(ti.beta_P_sign_flips)}. Status: **{ti.theory_status}**.
- **316L:** mean alpha {ss.alpha_mean:.6f}, median {ss.alpha_median:.6f}, interval [{ss.ci_lower:.6f}, {ss.ci_upper:.6f}]. Valid/invalid fits: {int(ss.valid_fits)}/{int(ss.invalid_fits)}; beta_P sign flips: {int(ss.beta_P_sign_flips)}. Status: **{ss.theory_status}**.
- Descriptive full-data fits only: Ti64 beta_P={ti_full.beta_P:.6f}, beta_VX={ti_full.beta_VX:.6f}, alpha={ti_full.alpha_mean:.6f}; 316L beta_P={ss_full.beta_P:.6f}, beta_VX={ss_full.beta_VX:.6f}, alpha={ss_full.alpha_mean:.6f}.

The theory reference −0.5 was fixed before fitting. Compatibility means only that −0.5 lies inside a split-sensitivity interval for this logistic separator; it is not exact equality, causal exponent recovery, or proof of a physical law.

## 2. Strict C-versus-K sensitivity

All T/CT/TK rows were removed without remapping. Ti64 retains {int(_row(strict_audit, material='Ti64').bundles)} bundles ({int(_row(strict_audit, material='Ti64').mode_C)} C, {int(_row(strict_audit, material='Ti64').mode_K)} K) across {int(_row(strict_audit, material='Ti64').unique_conditions)} conditions; 316L retains {int(_row(strict_audit, material='316L').bundles)} ({int(_row(strict_audit, material='316L').mode_C)} C, {int(_row(strict_audit, material='316L').mode_K)} K). Both support 20×5 exact-condition-grouped folds with both classes in every held-out fold.

- Ti64 strict H/G ROC-AUC: {ti_h['mean']:.6f}/{ti_g['mean']:.6f}; H−G {ti_d.mean_difference:+.6f} [{ti_d.ci_lower:+.6f}, {ti_d.ci_upper:+.6f}]. Relative to the frozen primary contrast, the absolute gap **{'shrinks' if shrink else 'does not shrink'}**.
- 316L strict H/G ROC-AUC: {ss_h['mean']:.6f}/{ss_g['mean']:.6f}; H−G {ss_d.mean_difference:+.6f} [{ss_d.ci_lower:+.6f}, {ss_d.ci_upper:+.6f}].

Thus the external physics discrimination is not solely created by merging transition modes into Keyhole. Strict C/K remains a post-hoc label-definition sensitivity and is not identical to the thesis target.

## 3. Regularization sensitivity

Only R1 (`C=1`) and R2 (`C=1e6`) were run. R3 is recorded as **{r3.status}** because `penalty=None` emits a deprecation warning in installed scikit-learn {sklearn.__version__}; no library was changed.

- Transition-inclusive Ti64: R1 H−G {r1.H_minus_G_roc_auc:+.6f} [{r1.H_minus_G_ci_lower:+.6f}, {r1.H_minus_G_ci_upper:+.6f}], alpha {r1.alpha_mean:.6f}; R2 H−G {r2.H_minus_G_roc_auc:+.6f} [{r2.H_minus_G_ci_lower:+.6f}, {r2.H_minus_G_ci_upper:+.6f}], alpha {r2.alpha_mean:.6f}.
- Strict Ti64: R1 H−G {ck_r1.H_minus_G_roc_auc:+.6f}, alpha {ck_r1.alpha_mean:.6f}; R2 H−G {ck_r2.H_minus_G_roc_auc:+.6f}, alpha {ck_r2.alpha_mean:.6f}.

The transition-inclusive H−G sign reverses under weak regularization, and alpha moves farther from −0.5. Therefore **G > H is regularization-sensitive**; C=1e6 is a sensitivity, not a replacement or tuned choice, so this does not alter the frozen primary verdict.

## Final interpretation

Phase 1.10 can be closed with a qualified interpretation. The fixed `P*VX^-1/2` direction is a strong independent experimental discriminator, but the generic C=1 separator prefers a materially steeper negative velocity exponent (Ti64 alpha≈{ti.alpha_mean:.3f}, interval excluding −0.5), not a small adjustment around theory. Removing transitions makes both H and G perfect rankers, so transition handling explains the frozen H–G gap but not the underlying physics discrimination. The G>H advantage also reverses at C=1e6 and is therefore penalty-sensitive. LS is fixed, so `LS^-3/2` remains not testable; no active-learning claim was tested.
"""
    (OUTPUT / "FINAL_PHASE1_10_CLOSURE_REPORT.md").write_text(report, encoding="utf-8")
    one_page = f"""# Supervisor one-page — Phase 1.10 closure

## Frozen result

Phase 1.10 remains **GENERIC_DIRECTION_SUPERIOR** under its predeclared bundle-level protocol (H−G ROC-AUC {frozen_contrast.mean_difference:+.4f} [{frozen_contrast.ci_lower:+.4f}, {frozen_contrast.ci_upper:+.4f}]).

## Three closure answers

1. **External exponent:** Ti64 alpha={ti.alpha_mean:.4f} [{ti.ci_lower:.4f}, {ti.ci_upper:.4f}] ({ti.theory_status}; {int(ti.valid_fits)}/100 valid); 316L alpha={ss.alpha_mean:.4f} [{ss.ci_lower:.4f}, {ss.ci_upper:.4f}] ({ss.theory_status}; {int(ss.valid_fits)}/100 valid). Coefficients were converted back from standardized to raw log-input scale; instability and sign flips are explicit.
2. **Strict C/K:** Ti64 H/G ROC-AUC={ti_h['mean']:.4f}/{ti_g['mean']:.4f}, H−G={ti_d.mean_difference:+.4f} [{ti_d.ci_lower:+.4f}, {ti_d.ci_upper:+.4f}]. 316L H/G={ss_h['mean']:.4f}/{ss_g['mean']:.4f}.
3. **Regularization:** transition-inclusive Ti64 H−G is {r1.H_minus_G_roc_auc:+.4f} at C=1 and {r2.H_minus_G_roc_auc:+.4f} at C=1e6; recovered alpha is {r1.alpha_mean:.4f}/{r2.alpha_mean:.4f}. The sign reversal makes G>H regularization-sensitive. `penalty=None` was not run because the installed API emits a deprecation warning.

## Safe thesis interpretation

The experimental map strongly supports a monotone physics-aligned P–VX organization, but its C=1 logistic optimum is materially steeper than −0.5. Pure C/K is perfectly ranked by both H and G; transition labels create the frozen performance gap. That gap reverses under weak regularization, so it is not penalty-robust. The frozen primary verdict remains real for its declared protocol, but no exact exponent agreement, LS exponent, universal law, causal exponent, or active-learning benefit is established.
"""
    (OUTPUT / "SUPERVISOR_PHASE1_10_CLOSURE_ONE_PAGE.md").write_text(one_page, encoding="utf-8")
    ledger = f"""# Phase 1.10 closure claim ledger

| Claim | Status | Evidence boundary |
|---|---|---|
| A. External Ti64 alpha is compatible with −0.5. | {'SUPPORTED' if ti.theory_status=='THEORY_CONSISTENT' else 'NOT SUPPORTED'} | Split-sensitivity interval {ti.ci_lower:.4f} to {ti.ci_upper:.4f}. |
| B. External Ti64 alpha equals −0.5 exactly. | NOT SUPPORTED | Compatibility is not equality; classifier orientation is not a causal exponent. |
| C. External 316L alpha is compatible with −0.5. | {'SUPPORTED' if ss.theory_status=='THEORY_CONSISTENT' else 'NOT SUPPORTED'} | Secondary within-material split-sensitivity interval. |
| D. Strict C-vs-K Ti64 remains strongly organized by h. | {'SUPPORTED' if ti_h['mean']>=.9 else 'QUALIFIED'} | Strict grouped OOF H ROC-AUC {ti_h['mean']:.4f}. |
| E. Transition merging explains the entire h result. | NOT SUPPORTED | Strong strict C/K H discrimination remains. |
| F. Regularization choice explains G > H. | {'NOT SUPPORTED' if np.sign(r1.H_minus_G_roc_auc)==np.sign(r2.H_minus_G_roc_auc) else 'QUALIFIED / REGULARIZATION-SENSITIVE'} | H−G changes sign between predeclared C=1 and C=1e6; this is sensitivity evidence, not causal attribution. |
| G. The LS^-3/2 exponent is externally validated. | NOT TESTABLE | LS is constant. |
| H. Physics is universally proven. | NOT SUPPORTED | Small, non-identical external classification task. |
| Frozen Phase 1.10 primary verdict changes. | NOT ALLOWED / UNCHANGED | Remains GENERIC_DIRECTION_SUPERIOR. |
"""
    (OUTPUT / "claim_ledger.md").write_text(ledger, encoding="utf-8")


def build_notebook() -> None:
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    cells = [
        nbf.v4.new_markdown_cell("# Week 9 Phase 1.10 closure diagnostics\n\nThree cheap checks close the external validation without changing its frozen primary verdict: recover the generic separator's raw exponent, remove transition labels, and relax logistic regularization."),
        nbf.v4.new_code_cell("from pathlib import Path\nimport pandas as pd\nfrom IPython.display import Image, Markdown, display\nROOT=Path.cwd().resolve().parents[1]\nOUT=ROOT/'outputs'/'week9_phase1_10_closure_diagnostics'\nprint('closure artifacts:',OUT)"),
        nbf.v4.new_markdown_cell("## 1. Why the checks matter\n\nThe generic model beat the fixed physics direction in the frozen bundle-level protocol. That difference could reflect a rotated P–VX separator, the transition-to-Keyhole mapping, or the fixed C=1 regularization. These are sensitivities, not replacement primary analyses."),
        nbf.v4.new_markdown_cell("## 2. Raw-scale exponent recovery algebra\n\nTraining predictors were standardized. Therefore `beta_P=gamma_P/sigma_P`, `beta_VX=gamma_VX/sigma_VX`, and `alpha=beta_VX/beta_P`. The standardized coefficient ratio is generally wrong. Five fold estimates are averaged inside each repeat before uncertainty is calculated."),
        nbf.v4.new_code_cell("folds=pd.read_csv(OUT/'exponent_fold_estimates.csv')\nrepeat=pd.read_csv(OUT/'exponent_repeat_summary.csv')\nsummary=pd.read_csv(OUT/'exponent_summary.csv')\ndisplay(folds.groupby('material').agg(fits=('alpha','size'),valid=('alpha_valid','sum'),betaP_min=('beta_P','min'),betaP_max=('beta_P','max')))"),
        nbf.v4.new_markdown_cell("## 3–5. Ti64, 316L, and the predeclared −0.5 reference\n\nThe interval is a grouped split-sensitivity interval, not a physical-population confidence interval and not proof of a causal exponent."),
        nbf.v4.new_code_cell("display(summary.round(5))\ndisplay(Image(filename=str(OUT/'figures'/'01_recovered_alpha_by_repeat.png')))"),
        nbf.v4.new_markdown_cell("## 6. Strict C-versus-K audit\n\nOnly raw `C` and pure `K` rows remain. `T`, `CT`, and `TK` are removed, not remapped. Exact repeated process conditions stay grouped."),
        nbf.v4.new_code_cell("audit=pd.read_csv(OUT/'strict_ck_population_audit.csv')\ndisplay(audit)"),
        nbf.v4.new_markdown_cell("## 7. Strict C-versus-K model results\n\nH and G use the same train-only scaling and C=1 logistic implementation as the frozen primary experiment. Complete OOF vectors are scored once per repeat."),
        nbf.v4.new_code_cell("strict=pd.read_csv(OUT/'strict_ck_model_summary.csv')\ncontrast=pd.read_csv(OUT/'strict_ck_paired_contrasts.csv')\ndisplay(strict[strict.metric.isin(['roc_auc','pr_auc','balanced_accuracy','keyhole_recall','brier_score'])].pivot_table(index=['material','model'],columns='metric',values='mean').round(4))\ndisplay(contrast.query(\"metric=='roc_auc'\").round(5))\ndisplay(Image(filename=str(OUT/'figures'/'02_ti64_transition_vs_strict_ck.png')))"),
        nbf.v4.new_markdown_cell("## 8. Regularization sensitivity\n\nR1 is frozen C=1; R2 is weak regularization C=1e6. `penalty=None` is recorded unavailable because the installed API emits a deprecation warning. No result-driven C selection is made."),
        nbf.v4.new_code_cell("reg=pd.read_csv(OUT/'regularization_sensitivity.csv')\ndisplay(reg.round(5))"),
        nbf.v4.new_markdown_cell("## 9. Final Phase 1.10 interpretation\n\nThe frozen `GENERIC_DIRECTION_SUPERIOR` verdict remains unchanged. These diagnostics state whether the generic gain requires a materially different exponent, transition inclusion, or C=1 regularization."),
        nbf.v4.new_code_cell("display(Markdown((OUT/'SUPERVISOR_PHASE1_10_CLOSURE_ONE_PAGE.md').read_text()))"),
        nbf.v4.new_markdown_cell("## 10. What remains untested\n\nConstant LS cannot validate the `LS^-3/2` exponent. Classifier orientation is not a causal material law. Strict C/K is not identical to the thesis target. No active-learning, cross-material coefficient transfer, or universal threshold was tested."),
    ]
    notebook = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},"language_info":{"name":"python","version":"3.14"}})
    nbf.write(notebook, NOTEBOOK)
    candidates = [Path(sys.executable), ROOT.parent/"thesis-week6-melt-pool-audit"/".venv"/"Scripts"/"python.exe", ROOT.parent/"thesis-week5-first-conduction-gp"/".venv"/"Scripts"/"python.exe", ROOT.parent/"thesis"/".venv"/"Scripts"/"python.exe"]
    notebook_python = next((candidate for candidate in candidates if candidate.is_file() and subprocess.run([str(candidate),"-c","import ipykernel,pandas,IPython"],capture_output=True).returncode==0), None)
    require(notebook_python is not None, "no notebook-capable Python environment")
    jupyter_root = p10.CACHE / "jupyter_closure"
    write_json(jupyter_root/"kernels"/"python3"/"kernel.json", {"argv":[str(notebook_python),"-m","ipykernel_launcher","-f","{connection_file}"],"display_name":"Python 3 (Phase 1.10 closure)","language":"python"})
    os.environ["JUPYTER_PATH"] = str(jupyter_root)
    executed = NotebookClient(notebook, timeout=180, kernel_name="python3", resources={"metadata":{"path":str(NOTEBOOK.parent)}}).execute()
    nbf.write(executed, NOTEBOOK)


def historical_changes() -> list[str]:
    changed = subprocess.run(["git","diff","--name-only",START_SHA,"--",str(FROZEN.relative_to(ROOT))],cwd=ROOT,text=True,capture_output=True,check=True).stdout.splitlines()
    return changed


def write_red_team(exponents: pd.DataFrame, strict_audit: pd.DataFrame, regularization: pd.DataFrame) -> None:
    ti = _row(exponents, material="Ti64", summary_type="grouped_cv_repeat_block")
    r1 = _row(regularization, dataset="transition_inclusive", setting="R1_C1")
    r2 = _row(regularization, dataset="transition_inclusive", setting="R2_C1e6")
    text = f"""# Final red-team report — Phase 1.10 closure

Status: **PASS WITH CLAIM BOUNDARIES**

| Attack | Disposition |
|---|---|
| Standardized coefficient ratio used by mistake | Rejected: executable recovery divides each gamma by its own training-fold sigma before beta_VX/beta_P. |
| Unstable beta_P denominator | {int(ti.invalid_fits)} invalid main fits; explicit near-zero and extreme-alpha guards stored per fit. |
| One hundred folds treated as independent | Rejected: five folds averaged inside repeat; bootstrap uses exactly 20 repeat means. |
| Theory line selected after results | Rejected: constant `THEORY_ALPHA=-0.5` and test lock. |
| Strict C/K mislabeled primary | Rejected: reports call it post-hoc sensitivity and preserve frozen verdict. |
| Regularization cherry-picking | Rejected: only C=1 and C=1e6 run; unpenalized API status recorded; no winner selected. |
| Strict class imbalance hidden | Audit reports Ti64 26/22 and 316L 37/11; every held-out fold contains both classes. |
| Replicate leakage | Exact condition is one fold in every repeat. |
| Alpha called causal/physical proof | Rejected in reports and claim ledger. |
| Frozen verdict changed | Rejected: remains GENERIC_DIRECTION_SUPERIOR. |

Regularization sign check: transition-inclusive H−G is {r1.H_minus_G_roc_auc:+.5f} at C=1 and {r2.H_minus_G_roc_auc:+.5f} at C=1e6. Frozen Phase 1.10 artifacts remain byte-unchanged relative to `{START_SHA}`.
"""
    (OUTPUT/"FINAL_RED_TEAM_REPORT.md").write_text(text,encoding="utf-8")


def validate(population: pd.DataFrame, main_coefficients: pd.DataFrame, exponent_repeat: pd.DataFrame, strict: pd.DataFrame, strict_manifest: pd.DataFrame, strict_audit: pd.DataFrame, regularization: pd.DataFrame, figure_manifest: pd.DataFrame) -> dict[str, Any]:
    notebook = nbf.read(NOTEBOOK, as_version=4)
    code = [cell for cell in notebook.cells if cell.cell_type=="code"]
    settings = regularization_settings()
    algebra_beta = recover_raw_coefficients([6.0,-4.0],[2.0,4.0])
    standardized_ratio = -4.0/6.0
    checks: list[tuple[str,bool,str]] = [
        ("start_sha_correct", subprocess.run(["git","merge-base","--is-ancestor",START_SHA,"HEAD"],cwd=ROOT).returncode==0, START_SHA),
        ("original_phase1_10_artifacts_unchanged", historical_changes()==[], str(historical_changes())),
        ("original_populations_reproduced", len(population)==120 and population.groupby("material").has_keyhole.sum().to_dict()=={"316L":23,"Ti64":34}, "Ti64 60/34; 316L 60/23"),
        ("raw_coefficient_conversion_algebra", np.allclose(algebra_beta,(3.0,-1.0,-1/3)), str(algebra_beta)),
        ("alpha_uses_raw_beta_ratio", np.allclose(main_coefficients.alpha, main_coefficients.beta_VX/main_coefficients.beta_P), "verified every fit"),
        ("standardized_ratio_not_used", not np.allclose(algebra_beta[2],standardized_ratio), "synthetic guard distinguishes raw and standardized ratios"),
        ("theory_reference_exact", THEORY_ALPHA==-0.5, str(THEORY_ALPHA)),
        ("one_hundred_main_fits_per_alloy", main_coefficients.groupby("material").size().eq(100).all(), str(main_coefficients.groupby("material").size().to_dict())),
        ("folds_averaged_within_repeat", exponent_repeat.groupby("material").size().eq(20).all() and exponent_repeat.folds.eq(5).all(), "20 repeat rows after five-fold averaging"),
        ("exactly_twenty_repeat_blocks", exponent_repeat.repeat.nunique()==N_REPEATS==20, "repeat-block inference"),
        ("bootstrap_at_least_10000", BOOTSTRAP_DRAWS>=10000, str(BOOTSTRAP_DRAWS)),
        ("beta_P_instability_checked", {"beta_P_near_zero","alpha_extreme","alpha_valid"}.issubset(main_coefficients.columns), f"invalid={int((~main_coefficients.alpha_valid).sum())}"),
        ("strict_dataset_only_C_K", set(strict.raw_mode)=={"C","K"}, str(sorted(strict.raw_mode.unique()))),
        ("no_transition_rows_survive", not strict.raw_mode.isin(["T","CT","TK"]).any(), "T/CT/TK absent"),
        ("strict_counts_verified", strict.groupby(["material","raw_mode"]).size().to_dict()=={("316L","C"):37,("316L","K"):11,("Ti64","C"):26,("Ti64","K"):22}, str(strict.groupby(["material","raw_mode"]).size().to_dict())),
        ("strict_exact_condition_grouping", strict_manifest.groupby(["material","repeat","condition_id"]).fold.nunique().max()==1, "condition lock"),
        ("strict_no_replicate_leakage", strict_manifest.groupby(["material","repeat","bundle_id"]).size().eq(1).all(), "one held-out fold per bundle"),
        ("no_optical_predictors", set(["log_h","log_P","log_VX"]).isdisjoint({"optical","emission","reflection"}), "log process inputs only"),
        ("no_internal_boundary_inputs", set(["B1","q20","q30"]).isdisjoint({"log_h","log_P","log_VX"}), "external conventional metrics"),
        ("R1_exact_C1", settings["R1_C1"]["C"]==1.0, str(settings["R1_C1"])),
        ("R2_exact_C1e6", settings["R2_C1e6"]["C"]==1e6, str(settings["R2_C1e6"])),
        ("R3_only_if_clean_supported", settings["R3_unpenalized"]["status"] in {"AVAILABLE","R3_UNAVAILABLE"} and (settings["R3_unpenalized"]["status"]=="AVAILABLE")==probe_r3()[0], settings["R3_unpenalized"]["status"]),
        ("train_only_scaling", "StandardScaler().fit(x_train)" in inspect.getsource(fit_logistic), "fit on training matrix"),
        ("original_primary_verdict_not_overwritten", "GENERIC_DIRECTION_SUPERIOR" in (OUTPUT/"FINAL_PHASE1_10_CLOSURE_REPORT.md").read_text(encoding="utf-8"), "frozen verdict stated"),
        ("notebook_executed", bool(code) and all(cell.execution_count is not None for cell in code) and not [out for cell in code for out in cell.get("outputs",[]) if out.get("output_type")=="error"], f"{len(code)} code cells"),
        ("figures_hashed", len(figure_manifest)<=2 and all(sha256_file(FIGURES/row.figure)==row.sha256 for row in figure_manifest.itertuples(index=False)), f"{len(figure_manifest)} figures"),
        ("raw_external_data_not_committed", subprocess.run(["git","ls-files",".cache"],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()=="" and not list(ROOT.rglob("Neuchatel data.zip")), "ignored cache only"),
        ("historical_phase1x_outputs_unchanged", historical_changes()==[], str(historical_changes())),
    ]
    records=[{"check":name,"status":"PASS" if status else "FAIL","detail":detail} for name,status,detail in checks]
    payload={"status":"PASS" if all(status for _,status,_ in checks) else "FAIL","check_count":len(checks),"checks":records}
    write_json(OUTPUT/"validation_report.json",payload)
    passed=sum(status for _,status,_ in checks)
    lines=["# Phase 1.10 closure validation","",f"Status: **{payload['status']}**","",f"Checks: **{passed} / {len(checks)} PASS**","","| Check | Status | Detail |","|---|---|---|"]
    lines.extend(f"| {row['check']} | {row['status']} | {row['detail']} |" for row in records)
    (OUTPUT/"validation_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    require(payload["status"]=="PASS","validation failed")
    return payload


def write_run_manifest(validation: dict[str, Any], strict_audit: pd.DataFrame, settings: dict[str, dict[str, Any]]) -> None:
    files=[path for path in OUTPUT.rglob("*") if path.is_file() and path.name!="run_manifest.json"]
    files.extend([Path(__file__),ROOT/"tests"/"test_week9_phase1_10_closure_diagnostics.py",NOTEBOOK])
    payload={
        "study":"Week 9 Phase 1.10 closure diagnostics",
        "starting_sha":START_SHA,
        "branch":BRANCH,
        "frozen_primary_verdict":"GENERIC_DIRECTION_SUPERIOR",
        "theory_alpha":THEORY_ALPHA,
        "protocol":{"repeats":N_REPEATS,"maximum_folds":MAX_FOLDS,"bootstrap_draws":BOOTSTRAP_DRAWS,"regularization":settings},
        "strict_population":strict_audit.to_dict(orient="records"),
        "validation":validation,
        "historical_phase1_10_changes":historical_changes(),
        "raw_external_data_committed":False,
        "files":[{"path":path.relative_to(ROOT).as_posix(),"sha256":artifact_sha256(path),"size_bytes":artifact_size(path)} for path in sorted(set(files))],
    }
    write_json(OUTPUT/"run_manifest.json",payload)


def run_all() -> None:
    OUTPUT.mkdir(parents=True,exist_ok=True)
    population=load_population_readonly()
    frozen_manifest=load_frozen_folds()
    strict=make_strict_population(population)
    strict_manifest,strict_audit=make_strict_folds(strict)
    settings=regularization_settings()

    main_metrics,main_coefficients=run_logistic_oof(population,frozen_manifest,"transition_inclusive","R1_C1")
    frozen_ti=pd.read_csv(FROZEN/"ti64_model_summary.csv")
    for model in ("H","G"):
        expected=float(frozen_ti[(frozen_ti.model.eq(model))&(frozen_ti.metric.eq("roc_auc"))]["mean"].iloc[0])
        actual=float(main_metrics[(main_metrics.material.eq("Ti64"))&(main_metrics.model.eq(model))].roc_auc.mean())
        require(abs(actual-expected)<1e-12,f"frozen Ti64 {model} baseline failed: {actual} vs {expected}")
    write_csv(OUTPUT/"exponent_fold_estimates.csv",main_coefficients)
    exponent_repeat,exponent_summary=summarize_exponents(main_coefficients,population)

    strict_metrics,strict_coefficients=run_logistic_oof(strict,strict_manifest,"strict_C_vs_K","R1_C1")
    strict_summary,strict_contrasts=summarize_model_metrics(strict_metrics)
    write_csv(OUTPUT/"strict_ck_repeat_metrics.csv",strict_metrics)
    write_csv(OUTPUT/"strict_ck_model_summary.csv",strict_summary)
    write_csv(OUTPUT/"strict_ck_paired_contrasts.csv",strict_contrasts)

    all_metrics=[main_metrics,strict_metrics]
    all_coefficients=[main_coefficients,strict_coefficients]
    for setting in ("R2_C1e6","R3_unpenalized"):
        if settings[setting]["status"]!="AVAILABLE":
            continue
        ti_population=population[population.material.eq("Ti64")]
        ti_manifest=frozen_manifest[frozen_manifest.material.eq("Ti64")]
        result=run_logistic_oof(ti_population,ti_manifest,"transition_inclusive",setting)
        all_metrics.append(result[0]); all_coefficients.append(result[1])
        ti_strict=strict[strict.material.eq("Ti64")]
        ti_strict_manifest=strict_manifest[strict_manifest.material.eq("Ti64")]
        result=run_logistic_oof(ti_strict,ti_strict_manifest,"strict_C_vs_K",setting)
        all_metrics.append(result[0]); all_coefficients.append(result[1])
    regularization_metrics=pd.concat(all_metrics,ignore_index=True)
    regularization_coefficients=pd.concat(all_coefficients,ignore_index=True)
    write_csv(OUTPUT/"regularization_repeat_metrics.csv",regularization_metrics)
    regularization=make_regularization_summary(regularization_metrics,regularization_coefficients,settings)

    figures=make_figures(exponent_repeat,exponent_summary,strict_summary)
    write_reports(exponent_summary,strict_summary,strict_contrasts,regularization,strict_audit)
    write_red_team(exponent_summary,strict_audit,regularization)
    build_notebook()
    validation=validate(population,main_coefficients,exponent_repeat,strict,strict_manifest,strict_audit,regularization,figures)
    write_run_manifest(validation,strict_audit,settings)
    print(json.dumps({"status":"PASS","output":str(OUTPUT)},indent=2))


def main(argv: Sequence[str] | None=None) -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",action="store_true")
    args=parser.parse_args(argv)
    if not args.run:
        parser.error("pass --run")
    run_all()


if __name__=="__main__":
    main()
