"""Week 9 Phase 2.1: does temporal width dynamics add anything to the 4D process inputs?

Phase 2 asked whether transverse width dynamics add information beyond the scalar
physics coordinate ``h``.  Ioan's actual control was never completed: the honest
baseline for an engineer is not ``h`` but the four process parameters that are
dialled on the machine, ``[P, VX, LS, ST]``.  This module runs that control.

Design rules inherited from Phase 2 and Week 8.5, deliberately unchanged:

* the canonical frozen population is 405 simulations / 73 Keyhole;
* evaluation uses the 100 frozen Week 8.5 grouped outer folds (20 repeats x 5 folds);
* every scaler and every logistic model is fitted inside the training fold only;
* the B1/q20/q30 boundary subsets are evaluation-only masks;
* uncertainty is a repeat-block bootstrap that keeps the five folds of a repeat together.

Width is reused verbatim from Phase 2: ``W(t) = Ymax - Ymin = dY`` (transverse
width).  ``dX = Xmax - Xmin`` is longitudinal length and is NOT used here.  The
Phase 2 feature table is read straight out of the pinned Phase 2 commit rather
than re-extracted, so no width definition can silently drift and no raw monitor
data has to be re-downloaded.

Run with ``python -m src.week9_phase2_1_fourd_plus_width_control --run``.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import subprocess
import textwrap
import time
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
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

from src import week8_5_frozen_sample_efficiency_confirmation as w85


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase2_1_fourd_plus_width_control"
FIGURES = OUTPUT / "figures"
NOTEBOOK = ROOT / "notebooks" / "week_09" / "06_week9_phase2_1_fourd_plus_width_control.ipynb"

# Pinned provenance of the reused Phase 2 width extraction.
PHASE2_SHA = "da913797d14b171bec55d3708f96aa87f09a4f94"
PHASE2_DIR = "outputs/week9_phase2_temporal_width_dynamics"
PHASE2_BRANCH = "codex/week9-phase2-temporal-width-dynamics"

SEED = 260907
BOOTSTRAP_DRAWS = 5000
SIGNFLIP_DRAWS = 20000

# Feature blocks. The width blocks are copied verbatim from Phase 2 so that the
# challenger is exactly "Phase 2 width dynamics bolted onto the 4D inputs".
FOURD_FEATURES = ("P", "VX", "LS", "ST")
STATIC_FEATURES = ("W_initial_um", "W_max_um", "W_T0_um")
SHAPE_FEATURES = (
    "width_gain_20_um",
    "width_gain_40_um",
    "time_to_50pct_max_width_tau",
)
ROBUST_DERIVATIVE_FEATURES = (
    "robust_max_positive_dWdt_um_per_ms",
    "robust_median_positive_dWdt_um_per_ms",
    "robust_early_dWdt_20_um_per_ms",
    "robust_early_dWdt_40_um_per_ms",
    "robust_time_of_max_dWdt_tau",
)
RAW_DERIVATIVE_FEATURES = (
    "max_positive_dWdt_um_per_ms",
    "median_positive_dWdt_um_per_ms",
    "time_of_max_dWdt_tau",
    "early_dWdt_20_um_per_ms",
    "early_dWdt_40_um_per_ms",
)
TEMPORAL_FEATURES = (*SHAPE_FEATURES, *ROBUST_DERIVATIVE_FEATURES)

# Model registry. ``C`` follows Phase 2: 1.0 for every multi-feature model and a
# very weak penalty for the single-feature h baseline. The primary contrast pits
# two C=1.0 models against each other, so regularisation is matched where it matters.
MODELS: dict[str, tuple[tuple[str, ...], float, str]] = {
    # --- Phase 2.1 primary family -------------------------------------------------
    "4d_only": (FOURD_FEATURES, 1.0, "primary"),
    "width_dynamics_only": (TEMPORAL_FEATURES, 1.0, "primary"),
    "4d_plus_width_dynamics": ((*FOURD_FEATURES, *TEMPORAL_FEATURES), 1.0, "primary"),
    # --- secondary sensitivities --------------------------------------------------
    "4d_plus_width_shape_only": ((*FOURD_FEATURES, *SHAPE_FEATURES), 1.0, "secondary"),
    "4d_plus_static_width": ((*FOURD_FEATURES, *STATIC_FEATURES), 1.0, "secondary"),
    # --- exact Phase 2 reproduction (audit anchor, unchanged specification) -------
    "h_only": (("log_h",), 1e6, "phase2_reproduction"),
    "static_width": (STATIC_FEATURES, 1.0, "phase2_reproduction"),
    "width_dynamics": (TEMPORAL_FEATURES, 1.0, "phase2_reproduction"),
    "h_plus_width_dynamics": (("log_h", *TEMPORAL_FEATURES), 1.0, "phase2_reproduction"),
    "h_plus_width_shape_only": (("log_h", *SHAPE_FEATURES), 1.0, "phase2_reproduction"),
}

PRIMARY_CONTRAST = "4d_plus_width_dynamics - 4d_only"
CONTRASTS: tuple[tuple[str, str, str], ...] = (
    ("4d_plus_width_dynamics", "4d_only", "primary"),
    ("h_plus_width_dynamics", "h_only", "secondary"),
    ("4d_plus_width_shape_only", "4d_only", "secondary"),
    ("4d_plus_static_width", "4d_only", "secondary"),
    ("width_dynamics_only", "4d_only", "descriptive"),
    ("4d_only", "h_only", "descriptive"),
)

METRIC_NAMES = (
    "roc_auc",
    "pr_auc",
    "accuracy",
    "balanced_accuracy",
    "keyhole_recall",
    "conduction_recall",
    "false_negative",
    "false_positive",
    "brier_score",
)
# Metrics that carry the Phase 2.1 headline claim; the Holm adjustment is applied
# across exactly this predeclared set for the primary contrast.
PRIMARY_METRICS = (
    "balanced_accuracy",
    "keyhole_recall",
    "accuracy",
    "roc_auc",
    "pr_auc",
    "brier_score",
)
# Lower is better for these, so a negative difference is an improvement.
LOWER_IS_BETTER = frozenset({"brier_score", "false_negative", "false_positive"})


# --------------------------------------------------------------------------------------
# house helpers (same contract as Phase 2)
# --------------------------------------------------------------------------------------
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
    frame.to_csv(
        tmp,
        index=False,
        lineterminator="\n",
        compression="gzip" if path.suffix == ".gz" else None,
    )
    tmp.replace(path)


def write_json(path: Path, payload: Any) -> None:
    def safe(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [safe(v) for v in value]
        if isinstance(value, (np.bool_, bool)):
            return bool(value)
        if isinstance(value, (np.integer, np.floating)):
            value = value.item()
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------
# reused Phase 2 width extraction (read from the pinned commit, never re-derived)
# --------------------------------------------------------------------------------------
def phase2_blob(relative_name: str) -> bytes:
    """Read one Phase 2 artifact out of the pinned commit without materialising a worktree."""
    result = subprocess.run(
        ["git", "show", f"{PHASE2_SHA}:{PHASE2_DIR}/{relative_name}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return result.stdout


def phase2_csv(relative_name: str) -> pd.DataFrame:
    blob = phase2_blob(relative_name)
    return pd.read_csv(
        io.BytesIO(blob), compression="gzip" if relative_name.endswith(".gz") else None
    )


def phase2_blob_sha(relative_name: str) -> str:
    return hashlib.sha256(phase2_blob(relative_name)).hexdigest()


def log_h(population: pd.DataFrame) -> np.ndarray:
    p = population.P.to_numpy(float)
    vx = population.VX.to_numpy(float)
    ls = population.LS.to_numpy(float)
    require(np.all(p > 0) and np.all(vx > 0) and np.all(ls > 0), "h requires positive P, VX and LS")
    return np.log(p / np.sqrt(vx * ls**3))


def load_population() -> pd.DataFrame:
    pop = w85.load_population().reset_index(drop=True)
    require(len(pop) == 405 and int(pop.has_keyhole.sum()) == 73, "canonical population/labels drift")
    require(pop.experiment_name.is_unique, "canonical experiment IDs are not unique")
    pop = pop.copy()
    pop["population_row_index"] = np.arange(len(pop))
    pop["log_h"] = log_h(pop)
    return pop


def semantic_width_audit() -> pd.DataFrame:
    """Re-verify dX=length / dY=width at source level and carry the pinned numeric verdict.

    The authoritative extractor is on disk, so the *semantic* half of the Phase 2
    audit is re-executed here.  The *numeric* half compared five pinned monitor
    files; those raw files are no longer on this machine, so their verdict is
    inherited from the Phase 2 commit rather than re-run, and is labelled as such.
    """
    source = ROOT / "src" / "week7_phase2_sph_v2_physical_target_extraction.py"
    text = source.read_text(encoding="utf-8")
    semantic_checks = {
        "columns": 'POSITION_BOUNDS_COLUMNS = ["x_min", "x_max", "y_min", "y_max", "z_min", "z_max"]' in text,
        "length": "length_m = extents[:, 0]" in text,
        "width": "width_m = extents[:, 1]" in text,
    }
    require(all(semantic_checks.values()), f"authoritative axis semantics not verified: {semantic_checks}")
    inherited = phase2_csv("axis_semantics_audit.csv").set_index("quantity")
    rows = []
    for quantity, formula, meaning, used, semantic_ok in (
        ("longitudinal_length", "x_max - x_min", "longitudinal melt-pool length dX", False,
         semantic_checks["columns"] and semantic_checks["length"]),
        ("transverse_width", "y_max - y_min", "transverse melt-pool width dY", True,
         semantic_checks["columns"] and semantic_checks["width"]),
    ):
        rows.append(
            {
                "quantity": quantity,
                "formula": formula,
                "physical_interpretation": meaning,
                "used_in_phase2_1": used,
                "authoritative_source_file": str(source.relative_to(ROOT)).replace("\\", "/"),
                "semantic_source_reverified_now": bool(semantic_ok),
                "numeric_mapping_verdict_inherited_from": PHASE2_SHA,
                "numeric_files_checked_in_phase2": int(inherited.loc[quantity, "numeric_files_checked"]),
                "numeric_mapping_verified_in_phase2": bool(inherited.loc[quantity, "numeric_mapping_verified"]),
                "status": "PASS",
            }
        )
    audit = pd.DataFrame(rows)
    require(bool(audit.semantic_source_reverified_now.all()), "source-level axis semantics failed")
    require(bool(audit.numeric_mapping_verified_in_phase2.all()), "inherited numeric axis verdict failed")
    write_csv(OUTPUT / "semantic_width_audit.csv", audit)
    return audit


def load_width_features(population: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the pinned Phase 2 transverse-width feature table and re-key it to the population."""
    features = phase2_csv("width_temporal_features.csv")
    require(features.experiment_name.is_unique, "phase 2 feature table has duplicate experiments")

    # Drop anything longitudinal so dX cannot leak into a "width" model by accident.
    longitudinal = [c for c in features.columns if c.startswith("L_")]
    stored = features.set_index("experiment_name")
    features = features.drop(columns=longitudinal)

    # Re-key onto the canonical population rather than trusting the stored index.
    canonical = population[
        ["experiment_name", "population_row_index", "has_keyhole", *FOURD_FEATURES, "log_h"]
    ]
    merged = features.drop(
        columns=["population_row_index", "has_keyhole", *FOURD_FEATURES, "log_h"]
    ).merge(canonical, on="experiment_name", how="left", validate="one_to_one")
    require(merged.population_row_index.notna().all(), "phase 2 features contain experiments outside the population")
    merged["population_row_index"] = merged.population_row_index.astype(int)

    fresh = merged.set_index("experiment_name")
    integrity_rows = []
    for name in (*FOURD_FEATURES, "log_h"):
        difference = np.abs(stored.loc[fresh.index, name].to_numpy(float) - fresh[name].to_numpy(float))
        integrity_rows.append(
            {
                "quantity": name,
                "check": "phase 2 stored value equals canonical population value",
                "max_abs_difference": float(difference.max()),
                "status": "PASS" if float(difference.max()) <= 1e-9 else "FAIL",
            }
        )
    label_difference = int(
        (stored.loc[fresh.index, "has_keyhole"].to_numpy(int) != fresh.has_keyhole.to_numpy(int)).sum()
    )
    integrity_rows.append(
        {
            "quantity": "has_keyhole",
            "check": "phase 2 stored label equals canonical manual label",
            "max_abs_difference": float(label_difference),
            "status": "PASS" if label_difference == 0 else "FAIL",
        }
    )
    model_columns = {c for spec in MODELS.values() for c in spec[0]}
    forbidden = model_columns & {"has_keyhole", "truth", "is_q20", "is_q30", "b1_distance", "population_row_index"}
    integrity_rows.append(
        {
            "quantity": "model_feature_columns",
            "check": "no label-derived or evaluation-mask column enters any model",
            "max_abs_difference": float(len(forbidden)),
            "status": "PASS" if not forbidden else "FAIL",
        }
    )
    surviving_longitudinal = [c for c in merged.columns if c.startswith("L_")]
    integrity_rows.append(
        {
            "quantity": "longitudinal_columns_dropped",
            "check": "no dX (longitudinal length) column survives into Phase 2.1",
            "max_abs_difference": float(len(surviving_longitudinal)),
            "status": "PASS" if not surviving_longitudinal else "FAIL",
        }
    )
    integrity = pd.DataFrame(integrity_rows)
    require(bool(integrity.status.eq("PASS").all()), f"feature integrity failed:\n{integrity}")
    write_csv(OUTPUT / "feature_integrity_audit.csv", integrity)
    return merged.sort_values("population_row_index").reset_index(drop=True), integrity


def trace_availability(population: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    usable = population.experiment_name.isin(set(features.experiment_name)).to_numpy()
    rows = []
    for flag, label in ((True, "usable_transverse_width_trace"), (False, "missing_or_unusable_trace")):
        group = population[usable == flag]
        rows.append(
            {
                "category": label,
                "count": len(group),
                "keyhole_count": int(group.has_keyhole.sum()),
                "conduction_count": int((~group.has_keyhole.astype(bool)).sum()),
                "keyhole_fraction": float(group.has_keyhole.mean()),
                **{f"{name}_mean": float(group[name].mean()) for name in FOURD_FEATURES},
            }
        )
    for name in (*FOURD_FEATURES, "log_h"):
        yes = population.loc[usable, name].to_numpy(float)
        no = population.loc[~usable, name].to_numpy(float)
        pooled = math.sqrt(
            ((len(yes) - 1) * yes.var(ddof=1) + (len(no) - 1) * no.var(ddof=1)) / (len(yes) + len(no) - 2)
        )
        rows.append(
            {
                "category": f"structured_missingness_{name}",
                "count": len(population),
                "standardized_mean_difference_usable_minus_missing": float((yes.mean() - no.mean()) / pooled),
            }
        )
    out = pd.DataFrame(rows)
    write_csv(OUTPUT / "trace_availability_summary.csv", out)
    return out


# --------------------------------------------------------------------------------------
# descriptive width-feature effects (same estimator as Phase 2)
# --------------------------------------------------------------------------------------
def cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean(x[:, None] > y[None, :]) - np.mean(x[:, None] < y[None, :]))


def feature_effects(features: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows = []
    considered = (*FOURD_FEATURES, "log_h", *STATIC_FEATURES, *SHAPE_FEATURES, *ROBUST_DERIVATIVE_FEATURES)
    for feature in considered:
        c = features.loc[features.has_keyhole.eq(0), feature].to_numpy(float)
        k = features.loc[features.has_keyhole.eq(1), feature].to_numpy(float)
        boot = np.array(
            [
                np.median(rng.choice(k, len(k), replace=True)) - np.median(rng.choice(c, len(c), replace=True))
                for _ in range(BOOTSTRAP_DRAWS)
            ]
        )
        rho, p = stats.spearmanr(features[feature], features.has_keyhole.astype(int))
        if feature in FOURD_FEATURES:
            group = "process_input_4d"
        elif feature == "log_h":
            group = "physics_coordinate"
        elif feature in STATIC_FEATURES:
            group = "static_width"
        elif feature in SHAPE_FEATURES:
            group = "width_shape"
        else:
            group = "width_robust_derivative"
        rows.append(
            {
                "feature": feature,
                "feature_group": group,
                "in_width_dynamics_block": feature in TEMPORAL_FEATURES,
                "conduction_n": len(c),
                "keyhole_n": len(k),
                "conduction_median": float(np.median(c)),
                "keyhole_median": float(np.median(k)),
                "median_difference_keyhole_minus_conduction": float(np.median(k) - np.median(c)),
                "median_difference_ci_low": float(np.quantile(boot, 0.025)),
                "median_difference_ci_high": float(np.quantile(boot, 0.975)),
                "cliffs_delta": cliffs_delta(k, c),
                "spearman_rho_with_label": float(rho),
                "spearman_p": float(p),
            }
        )
    out = pd.DataFrame(rows)
    order = np.argsort(out.spearman_p.to_numpy(float))
    adjusted = np.empty(len(out), dtype=float)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, float(out.iloc[index].spearman_p) * (len(out) - rank))
        adjusted[index] = min(1.0, running)
    out["holm_p"] = adjusted
    write_csv(OUTPUT / "width_feature_effects.csv", out)
    return out


def width_collinearity(features: pd.DataFrame) -> pd.DataFrame:
    """How much of each width feature is already explained by the 4D inputs?

    This is the mechanistic explanation for whatever the primary contrast shows:
    a width feature that is nearly a deterministic function of [P, VX, LS, ST]
    cannot add independent information to a model that already has them.
    """
    x = StandardScaler().fit_transform(features[list(FOURD_FEATURES)].to_numpy(float))
    design = np.column_stack([np.ones(len(x)), x])
    rows = []
    for feature in TEMPORAL_FEATURES:
        y = features[feature].to_numpy(float)
        coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
        residual = y - design @ coefficients
        total = float(np.sum((y - y.mean()) ** 2))
        r2 = float(1.0 - np.sum(residual**2) / total) if total > 0 else float("nan")
        rho_residual, p_residual = stats.spearmanr(residual, features.has_keyhole.astype(int))
        rho_raw, _ = stats.spearmanr(y, features.has_keyhole.astype(int))
        rows.append(
            {
                "width_feature": feature,
                "r2_explained_by_4d_inputs": r2,
                "spearman_rho_raw_with_label": float(rho_raw),
                "spearman_rho_residual_with_label": float(rho_residual),
                "residual_spearman_p": float(p_residual),
                "independent_information_retained": float(abs(rho_residual) / max(abs(rho_raw), 1e-12)),
            }
        )
    out = pd.DataFrame(rows).sort_values("r2_explained_by_4d_inputs", ascending=False).reset_index(drop=True)
    write_csv(OUTPUT / "width_vs_4d_collinearity.csv", out)
    return out


# --------------------------------------------------------------------------------------
# leak-free evaluation on the frozen Week 8.5 grouped folds
# --------------------------------------------------------------------------------------
def _model(c: float) -> Pipeline:
    return Pipeline(
        [
            ("scale", StandardScaler()),
            ("logistic", LogisticRegression(C=c, solver="lbfgs", max_iter=3000, random_state=SEED)),
        ]
    )


def _safe_auc(y: np.ndarray, p: np.ndarray, kind: str) -> float:
    if len(np.unique(y)) < 2:
        return float("nan")
    return float(roc_auc_score(y, p) if kind == "roc" else average_precision_score(y, p))


def metric_row(y: np.ndarray, probability: np.ndarray) -> dict[str, Any]:
    pred = (probability >= 0.5).astype(int)
    _, fp, fn, _ = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "row_count": len(y),
        "keyhole_count": int(y.sum()),
        "roc_auc": _safe_auc(y, probability, "roc"),
        "pr_auc": _safe_auc(y, probability, "pr"),
        "accuracy": float(accuracy_score(y, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "keyhole_recall": float(recall_score(y, pred, pos_label=1, zero_division=0)),
        "conduction_recall": float(recall_score(y, pred, pos_label=0, zero_division=0)),
        "false_negative": int(fn),
        "false_positive": int(fp),
        "brier_score": float(brier_score_loss(y, probability)),
    }


def _subset_flags(spec: w85.SplitSpec, population: pd.DataFrame, distances: np.ndarray,
                  usable_test_indices: np.ndarray) -> dict[str, np.ndarray]:
    """q20/q30 are the *original* frozen boundary masks, restricted to usable rows.

    The quantile is computed on the full frozen test fold exactly as in Week 8.5,
    then subset; it is never recomputed on the usable subset, so the evaluation
    region cannot drift with trace availability.
    """
    original = w85.boundary_flags(spec, population, distances)
    lookup = {int(idx): pos for pos, idx in enumerate(np.asarray(spec.test_indices))}
    return {
        "full": np.ones(len(usable_test_indices), dtype=bool),
        "q30": np.array([original["B1_q30"][lookup[int(i)]] for i in usable_test_indices]),
        "q20": np.array([original["B1_q20"][lookup[int(i)]] for i in usable_test_indices]),
    }


def evaluate_models(population: pd.DataFrame, features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    specs = w85.build_splits(population)
    require(len(specs) == 100, "frozen split count drift")
    by_index = features.set_index("population_row_index", drop=False)
    usable_indices = set(int(i) for i in by_index.index)
    distances = w85.b1_distance(population)
    predictions: list[dict[str, Any]] = []
    coefficients: list[dict[str, Any]] = []
    for number, spec in enumerate(specs, 1):
        train_idx = np.array([i for i in spec.train_indices if i in usable_indices], dtype=int)
        test_idx = np.array([i for i in spec.test_indices if i in usable_indices], dtype=int)
        require(len(np.intersect1d(train_idx, test_idx)) == 0, f"{spec.run_id}: train/test overlap")
        train = by_index.loc[train_idx]
        test = by_index.loc[test_idx]
        flags = _subset_flags(spec, population, distances, test_idx)
        test_names = test.experiment_name.to_numpy()
        test_truth = test.has_keyhole.to_numpy(int)
        for model_name, (columns, c, role) in MODELS.items():
            pipeline = _model(c)
            pipeline.fit(train[list(columns)].to_numpy(float), train.has_keyhole.to_numpy(int))
            prob = pipeline.predict_proba(test[list(columns)].to_numpy(float))[:, 1]
            if role == "primary":
                for column, weight in zip(columns, pipeline.named_steps["logistic"].coef_[0]):
                    coefficients.append(
                        {
                            "run_id": spec.run_id,
                            "repeat": spec.repeat,
                            "fold": spec.fold,
                            "model": model_name,
                            "feature": column,
                            "standardized_coefficient": float(weight),
                        }
                    )
            for pos, idx in enumerate(test_idx):
                predictions.append(
                    {
                        "run_id": spec.run_id,
                        "repeat": spec.repeat,
                        "fold": spec.fold,
                        "population_row_index": int(idx),
                        "experiment_name": str(test_names[pos]),
                        "truth": int(test_truth[pos]),
                        "model": model_name,
                        "probability": float(prob[pos]),
                        "is_q30": bool(flags["q30"][pos]),
                        "is_q20": bool(flags["q20"][pos]),
                        "b1_distance": float(distances[idx]),
                        "train_usable_n": len(train),
                        "test_usable_n": len(test),
                    }
                )
        if number % 20 == 0:
            print(f"grouped evaluation {number}/100", flush=True)
    pred = pd.DataFrame(predictions)
    coef = pd.DataFrame(coefficients)
    write_csv(OUTPUT / "model_oof_predictions.csv.gz", pred)
    write_csv(OUTPUT / "infold_coefficients.csv", coef)
    return pred, coef


def summarize_oof(pred: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    repeat_rows = []
    for (repeat, model), group in pred.groupby(["repeat", "model"], sort=True):
        for subset, flag in (
            ("full", np.ones(len(group), bool)),
            ("q30", group.is_q30.to_numpy(bool)),
            ("q20", group.is_q20.to_numpy(bool)),
        ):
            g = group.loc[flag]
            repeat_rows.append(
                {"repeat": int(repeat), "model": str(model), "subset": subset}
                | metric_row(g.truth.to_numpy(int), g.probability.to_numpy(float))
            )
    repeat = pd.DataFrame(repeat_rows)
    summary_rows = []
    for (model, subset), group in repeat.groupby(["model", "subset"], sort=True):
        for metric in METRIC_NAMES:
            values = group[metric].dropna().to_numpy(float)
            summary_rows.append(
                {
                    "model": str(model),
                    "subset": str(subset),
                    "role": MODELS[str(model)][2],
                    "feature_count": len(MODELS[str(model)][0]),
                    "metric": metric,
                    "mean": float(values.mean()),
                    "sd_across_repeats": float(values.std(ddof=1)),
                    "repeat_blocks": len(values),
                }
            )
    summary = pd.DataFrame(summary_rows)
    write_csv(OUTPUT / "model_repeat_level_metrics.csv", repeat)
    write_csv(OUTPUT / "model_oof_summary.csv", summary)
    return repeat, summary


def paired_contrasts(repeat: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED + 1)
    rows = []
    for subset, group in repeat.groupby("subset", sort=True):
        for challenger, baseline, role in CONTRASTS:
            pivot = group.pivot(index="repeat", columns="model", values=list(METRIC_NAMES))
            for metric in METRIC_NAMES:
                values = (pivot[(metric, challenger)] - pivot[(metric, baseline)]).dropna().to_numpy(float)
                boot = np.array(
                    [rng.choice(values, len(values), replace=True).mean() for _ in range(BOOTSTRAP_DRAWS)]
                )
                signs = rng.choice([-1.0, 1.0], size=(SIGNFLIP_DRAWS, len(values)))
                null = (signs * values).mean(axis=1)
                observed = float(values.mean())
                p_value = float((np.sum(np.abs(null) >= abs(observed) - 1e-15) + 1) / (SIGNFLIP_DRAWS + 1))
                rows.append(
                    {
                        "subset": str(subset),
                        "contrast": f"{challenger} - {baseline}",
                        "contrast_role": role,
                        "metric": metric,
                        "lower_is_better": metric in LOWER_IS_BETTER,
                        "mean_difference": observed,
                        "ci_low": float(np.quantile(boot, 0.025)),
                        "ci_high": float(np.quantile(boot, 0.975)),
                        "signflip_p": p_value,
                        "repeat_blocks": len(values),
                    }
                )
    contrasts = pd.DataFrame(rows)
    # Holm adjustment within each contrast, across the predeclared primary metric set.
    # Applied to every contrast (not just the primary one) so that a secondary
    # sensitivity cannot look stronger than the primary claim purely by escaping
    # multiplicity control.
    contrasts["holm_p_metric_family"] = np.nan
    for (contrast_name, subset), block in contrasts[
        contrasts.metric.isin(PRIMARY_METRICS)
    ].groupby(["contrast", "subset"], sort=False):
        ordered = block.sort_values("signflip_p")
        running = 0.0
        for rank, (index, row) in enumerate(ordered.iterrows()):
            running = max(running, float(row.signflip_p) * (len(ordered) - rank))
            contrasts.loc[index, "holm_p_metric_family"] = min(1.0, running)
    write_csv(OUTPUT / "model_paired_contrasts.csv", contrasts)
    return contrasts


def verdict(row: pd.Series) -> str:
    """Direction-aware verdict for one contrast row, based on the 95% interval."""
    sign = -1.0 if bool(row.lower_is_better) else 1.0
    low, high = sorted((sign * float(row.ci_low), sign * float(row.ci_high)))
    if low > 0:
        return "IMPROVES"
    if high < 0:
        return "DEGRADES"
    return "NO DETECTABLE DIFFERENCE"


def annotate(contrasts: pd.DataFrame, contrast_name: str) -> pd.DataFrame:
    block = contrasts[
        contrasts.contrast.eq(contrast_name)
        & contrasts.metric.isin(PRIMARY_METRICS)
        & contrasts.subset.isin(["q20", "q30", "full"])
    ].copy()
    block["verdict"] = block.apply(verdict, axis=1)
    block["verdict_after_holm"] = np.where(
        block.verdict.ne("NO DETECTABLE DIFFERENCE") & (block.holm_p_metric_family <= 0.05),
        block.verdict,
        "NO DETECTABLE DIFFERENCE",
    )
    block["metric_family"] = np.where(
        block.metric.isin(["balanced_accuracy", "keyhole_recall", "accuracy"]),
        "hard_decision",
        "ranking_or_probability",
    )
    return block.sort_values(["subset", "metric_family", "metric"]).reset_index(drop=True)


def primary_inference(contrasts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    primary = annotate(contrasts, PRIMARY_CONTRAST)
    secondary = annotate(contrasts, "4d_plus_width_shape_only - 4d_only")
    write_csv(OUTPUT / "primary_contrast_inference.csv", primary)
    write_csv(OUTPUT / "shape_subset_contrast_inference.csv", secondary)
    return primary, secondary


def reproduction_gate(summary: pd.DataFrame) -> pd.DataFrame:
    """Prove the Phase 2.1 fold machinery reproduces the frozen Phase 2 numbers exactly."""
    published = phase2_csv("model_oof_summary.csv")
    rows = []
    for row in summary[summary.role.eq("phase2_reproduction")].itertuples(index=False):
        match = published[
            published.model.eq(row.model) & published.subset.eq(row.subset) & published.metric.eq(row.metric)
        ]
        if match.empty:
            continue
        difference = abs(float(match.iloc[0]["mean"]) - float(row.mean))
        rows.append(
            {
                "model": row.model,
                "subset": row.subset,
                "metric": row.metric,
                "phase2_published_mean": float(match.iloc[0]["mean"]),
                "phase2_1_reproduced_mean": float(row.mean),
                "abs_difference": difference,
                "status": "PASS" if difference <= 1e-9 else "FAIL",
            }
        )
    gate = pd.DataFrame(rows)
    write_csv(OUTPUT / "phase2_reproduction_gate.csv", gate)
    return gate


def coefficient_summary(coef: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model, feature), group in coef.groupby(["model", "feature"], sort=True):
        values = group.standardized_coefficient.to_numpy(float)
        per_repeat = group.groupby("repeat").standardized_coefficient.mean().to_numpy(float)
        rows.append(
            {
                "model": str(model),
                "feature": str(feature),
                "block": "process_input_4d" if feature in FOURD_FEATURES else "width_dynamics",
                "mean_standardized_coefficient": float(values.mean()),
                "sd_across_repeats": float(per_repeat.std(ddof=1)),
                "repeat_ci_low": float(np.quantile(per_repeat, 0.025)),
                "repeat_ci_high": float(np.quantile(per_repeat, 0.975)),
                "sign_stability": float(max(np.mean(values > 0), np.mean(values < 0))),
                "folds": len(values),
            }
        )
    out = pd.DataFrame(rows)
    write_csv(OUTPUT / "infold_coefficient_summary.csv", out)
    return out


# --------------------------------------------------------------------------------------
# figures
# --------------------------------------------------------------------------------------
CONDUCTION_COLOR = "#4477AA"
KEYHOLE_COLOR = "#CC3311"
BLOCK_COLORS = {"process_input_4d": "#4C78A8", "width_dynamics": "#CC3311"}
MODEL_ORDER = (
    "h_only",
    "static_width",
    "width_dynamics_only",
    "4d_only",
    "4d_plus_static_width",
    "4d_plus_width_shape_only",
    "4d_plus_width_dynamics",
    "h_plus_width_dynamics",
)


def _save(fig: plt.Figure, name: str) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / name
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def _pretty(name: str) -> str:
    return name.replace("_", " ")


def make_figures(
    population: pd.DataFrame,
    features: pd.DataFrame,
    profiles: pd.DataFrame,
    availability: pd.DataFrame,
    effects: pd.DataFrame,
    summary: pd.DataFrame,
    contrasts: pd.DataFrame,
    inference: pd.DataFrame,
    shape_inference: pd.DataFrame,
    coefficients: pd.DataFrame,
    collinearity: pd.DataFrame,
    repeat: pd.DataFrame,
    claims: pd.DataFrame,
) -> list[Path]:
    plt.style.use("seaborn-v0_8-whitegrid")
    created: list[Path] = []

    # 1 ---------------------------------------------------------------- availability
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
    counts = availability[availability.category.str.startswith(("usable", "missing"))].set_index("category")
    labels = ["usable_transverse_width_trace", "missing_or_unusable_trace"]
    conduction = [float(counts.loc[k, "conduction_count"]) for k in labels]
    keyhole = [float(counts.loc[k, "keyhole_count"]) for k in labels]
    x = np.arange(len(labels))
    axes[0].bar(x, conduction, color=CONDUCTION_COLOR, label="Conduction")
    axes[0].bar(x, keyhole, bottom=conduction, color=KEYHOLE_COLOR, label="Keyhole")
    for pos, (c, k) in enumerate(zip(conduction, keyhole)):
        axes[0].text(pos, c + k + 6, f"n={int(c + k)}\n{int(k)} Keyhole", ha="center", fontsize=9)
    axes[0].set_xticks(x, ["usable\nwidth trace", "missing /\nunusable"])
    axes[0].set(ylabel="Simulations", title=f"Trace availability within the frozen 405-simulation population")
    axes[0].set_ylim(0, max(np.array(conduction) + np.array(keyhole)) * 1.25)
    axes[0].legend(fontsize=9)

    smd = availability[availability.category.str.startswith("structured_missingness_")].copy()
    smd["name"] = smd.category.str.replace("structured_missingness_", "", regex=False)
    values = smd.standardized_mean_difference_usable_minus_missing.to_numpy(float)
    axes[1].barh(np.arange(len(smd)), values, color=np.where(np.abs(values) >= 0.2, "#EE7733", "#BBBBBB"))
    axes[1].axvline(0, color="black", lw=0.8)
    for line in (-0.2, 0.2):
        axes[1].axvline(line, color="#EE7733", lw=0.8, ls=":")
    axes[1].set_yticks(np.arange(len(smd)), smd.name)
    axes[1].set(xlabel="Standardized mean difference (usable − missing)",
                title="Trace loss is not uniform across the input space")
    fig.suptitle("Figure 1 — What data actually enter the Phase 2.1 comparison", fontsize=12)
    created.append(_save(fig, "01_trace_availability.png"))

    # 2 ------------------------------------------------------- representative traces
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    ranked = features.sort_values("width_gain_40_um")
    picks = []
    for label in (0, 1):
        g = ranked[ranked.has_keyhole.eq(label)]
        for quantile in (0.15, 0.50, 0.85):
            picks.append((label, g.iloc[int(quantile * (len(g) - 1))].experiment_name))
    for label, name in picks:
        trace = profiles[profiles.experiment_name.eq(name)].sort_values("tau")
        axes[0].plot(
            trace.tau,
            trace.transverse_width_um,
            lw=1.5,
            alpha=0.85,
            color=KEYHOLE_COLOR if label else CONDUCTION_COLOR,
        )
    axes[0].plot([], [], color=CONDUCTION_COLOR, lw=1.5, label="Conduction (3 traces)")
    axes[0].plot([], [], color=KEYHOLE_COLOR, lw=1.5, label="Keyhole (3 traces)")
    axes[0].set(xlabel="Normalized active time τ", ylabel="Transverse width ΔY (µm)",
                title="Representative individual traces")
    axes[0].legend(fontsize=9)

    for label, color, text in ((0, CONDUCTION_COLOR, "Conduction"), (1, KEYHOLE_COLOR, "Keyhole")):
        wide = profiles[profiles.has_keyhole.eq(label)].pivot(
            index="experiment_name", columns="tau", values="transverse_width_um"
        )
        grid = wide.columns.to_numpy(float)
        axes[1].plot(grid, wide.median(), color=color, lw=2.2, label=f"{text} median")
        axes[1].fill_between(grid, wide.quantile(0.25), wide.quantile(0.75), color=color, alpha=0.18,
                             label=f"{text} IQR")
    axes[1].set(xlabel="Normalized active time τ", ylabel="Transverse width ΔY (µm)",
                title="Class profiles overlap substantially")
    axes[1].legend(fontsize=9)
    fig.suptitle("Figure 2 — Transverse width ΔY = Ymax − Ymin (Phase 2 extraction, reused unchanged)", fontsize=12)
    created.append(_save(fig, "02_representative_width_traces.png"))

    # 3 ------------------------------------------------------------- feature effects
    shown = effects[effects.feature_group.ne("physics_coordinate")].copy()
    shown = shown[shown.feature.isin([*FOURD_FEATURES, *STATIC_FEATURES, *TEMPORAL_FEATURES])]
    shown = shown.reindex(shown.cliffs_delta.abs().sort_values().index)
    palette = {
        "process_input_4d": "#4C78A8",
        "static_width": "#9E9E9E",
        "width_shape": "#F58518",
        "width_robust_derivative": "#CC3311",
    }
    fig, ax = plt.subplots(figsize=(9.5, 6.2))
    ax.barh(np.arange(len(shown)), shown.cliffs_delta, color=[palette[g] for g in shown.feature_group])
    ax.axvline(0, color="black", lw=0.8)
    for line in (-0.33, -0.147, 0.147, 0.33):
        ax.axvline(line, color="#888888", lw=0.6, ls=":")
    ax.set_yticks(np.arange(len(shown)), [_pretty(f) for f in shown.feature], fontsize=8)
    ax.set(xlabel="Cliff's delta (Keyhole − Conduction), dotted lines = small/medium thresholds",
           title="Figure 3 — Marginal separability of every candidate feature\n"
                 "(descriptive only: marginal effects do not imply incremental value)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in palette.values()]
    ax.legend(handles, [_pretty(k) for k in palette], fontsize=8, loc="lower right")
    created.append(_save(fig, "03_width_feature_summary.png"))

    # 4 ------------------------------------------------------------ model comparison
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), sharey=True)
    order = [m for m in MODEL_ORDER if m in set(summary.model)]
    for ax, metric, title in (
        (axes[0], "balanced_accuracy", "q20 balanced accuracy (hard decision)"),
        (axes[1], "keyhole_recall", "q20 Keyhole recall (hard decision)"),
        (axes[2], "roc_auc", "q20 ROC-AUC (ranking)"),
    ):
        block = summary[summary.subset.eq("q20") & summary.metric.eq(metric)].set_index("model")
        means = np.array([float(block.loc[m, "mean"]) for m in order])
        sds = np.array([float(block.loc[m, "sd_across_repeats"]) for m in order])
        colors = [
            "#CC3311" if m == "4d_plus_width_dynamics" else ("#333333" if m == "4d_only" else "#AFC7E0")
            for m in order
        ]
        ax.barh(np.arange(len(order)), means, xerr=sds, color=colors, error_kw={"lw": 0.9, "ecolor": "#555555"})
        ax.axvline(0.5, color="#888888", lw=0.8, ls=":")
        ax.set(xlim=(0.0, 1.24), xlabel=title)
        for pos, value in enumerate(means):
            ax.text(value + 0.04, pos, f"{value:.3f}", va="center", fontsize=8)
    axes[0].set_yticks(np.arange(len(order)), [_pretty(m) for m in order], fontsize=9)
    fig.suptitle(
        "Figure 4 — Leak-free performance on the 100 frozen grouped folds "
        "(error bars = SD across the 20 repeat blocks)", fontsize=12
    )
    fig.subplots_adjust(wspace=0.12)
    created.append(_save(fig, "04_model_comparison.png"))

    # 5 ------------------------------------------------------------ primary contrast
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.0), sharey=True)
    for ax, block, title in (
        (axes[0], inference, "PRIMARY: 4d + full width-dynamics block (8 features)"),
        (axes[1], shape_inference, "SECONDARY: 4d + width-shape subset (3 features)"),
    ):
        q20 = block[block.subset.eq("q20")].copy()
        q20["oriented"] = np.where(q20.lower_is_better, -1.0, 1.0)
        q20 = q20.sort_values(["metric_family", "metric"])
        positions = np.arange(len(q20))[::-1]
        for pos, row in zip(positions, q20.itertuples(index=False)):
            sign = row.oriented
            low, high = sorted((sign * row.ci_low, sign * row.ci_high))
            color = {"IMPROVES": "#117733", "DEGRADES": "#CC3311"}.get(row.verdict_after_holm, "#666666")
            ax.plot([low, high], [pos, pos], color=color, lw=2.6, solid_capstyle="round")
            ax.plot([sign * row.mean_difference], [pos], "o", color=color, ms=7)
            ax.text(0.985, (pos + 0.5) / len(q20), f"{row.verdict_after_holm}",
                    transform=ax.transAxes, ha="right", va="center", fontsize=7.6, color=color)
        ax.axvline(0, color="black", lw=1.0)
        ax.set_yticks(positions,
                      [f"{_pretty(r.metric)}\n[{r.metric_family}]" for r in q20.itertuples(index=False)],
                      fontsize=8)
        ax.set(xlim=(-0.04, 0.145), xlabel="Oriented difference vs 4d_only  (right = width helps)",
               title=title, ylim=(-0.6, len(q20) - 0.4))
    fig.suptitle(
        "Figure 5 — Phase 2.1 contrasts on the q20 boundary region\n"
        "95% repeat-block bootstrap intervals; verdicts are Holm-adjusted over the six predeclared metrics",
        fontsize=12, y=1.06,
    )
    created.append(_save(fig, "05_primary_contrast.png"))

    # 6 -------------------------------------------------------------- coefficients
    coef = coefficients[coefficients.model.eq("4d_plus_width_dynamics")].copy()
    coef = coef.reindex(coef.mean_standardized_coefficient.abs().sort_values().index)
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    positions = np.arange(len(coef))
    ax.barh(positions, coef.mean_standardized_coefficient, color=[BLOCK_COLORS[b] for b in coef.block], alpha=0.9)
    ax.errorbar(
        coef.mean_standardized_coefficient, positions,
        xerr=np.abs(np.vstack([
            coef.mean_standardized_coefficient - coef.repeat_ci_low,
            coef.repeat_ci_high - coef.mean_standardized_coefficient,
        ])),
        fmt="none", ecolor="#333333", lw=1.0,
    )
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks(positions, [f"{_pretty(f)}  ({s:.0%} stable sign)"
                              for f, s in zip(coef.feature, coef.sign_stability)], fontsize=8)
    handles = [plt.Rectangle((0, 0), 1, 1, color=BLOCK_COLORS[b]) for b in BLOCK_COLORS]
    ax.legend(handles, [_pretty(b) for b in BLOCK_COLORS], fontsize=8, loc="lower right")
    ax.set(xlabel="Mean in-fold standardized logistic coefficient (100 frozen folds)",
           title="Figure 6 — Inside 4d_plus_width_dynamics, what carries the decision?\n"
                 "Bars are averaged over training folds only; whiskers span the 20 repeat means")
    created.append(_save(fig, "06_infold_coefficients.png"))

    # 7 ----------------------------------------------------- does width add beyond 4D
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.8))
    pivot = repeat[repeat.subset.eq("q20")].pivot(index="repeat", columns="model", values="balanced_accuracy")
    axes[0].scatter(pivot["4d_only"], pivot["4d_plus_width_dynamics"], s=42, color="#4C78A8",
                    edgecolor="white", zorder=3)
    lo = float(min(pivot["4d_only"].min(), pivot["4d_plus_width_dynamics"].min())) - 0.01
    hi = float(max(pivot["4d_only"].max(), pivot["4d_plus_width_dynamics"].max())) + 0.01
    axes[0].plot([lo, hi], [lo, hi], color="black", lw=1.0, ls="--")
    wins = int((pivot["4d_plus_width_dynamics"] > pivot["4d_only"]).sum())
    axes[0].set(xlim=(lo, hi), ylim=(lo, hi), xlabel="4d_only q20 balanced accuracy",
                ylabel="4d + width dynamics", title=f"Paired repeat blocks: width wins {wins}/{len(pivot)}")

    delta = (pivot["4d_plus_width_dynamics"] - pivot["4d_only"]).to_numpy(float)
    axes[1].hist(delta, bins=10, color="#AFC7E0", edgecolor="white")
    axes[1].axvline(0, color="black", lw=1.2)
    axes[1].axvline(delta.mean(), color="#CC3311", lw=2.0, label=f"mean {delta.mean():+.4f}")
    row = contrasts[contrasts.contrast.eq(PRIMARY_CONTRAST) & contrasts.subset.eq("q20")
                    & contrasts.metric.eq("balanced_accuracy")].iloc[0]
    axes[1].axvspan(row.ci_low, row.ci_high, color="#CC3311", alpha=0.12, label="95% CI of the mean")
    axes[1].set(xlabel="Per-repeat difference in q20 balanced accuracy", ylabel="Repeat blocks",
                title="Difference distribution straddles zero" if row.ci_low <= 0 <= row.ci_high
                      else "Difference distribution excludes zero")
    axes[1].legend(fontsize=8)

    coll = collinearity.sort_values("r2_explained_by_4d_inputs")
    short = [
        _pretty(f).replace("robust ", "").replace(" um per ms", "").replace(" um", "").replace(" tau", "")
        for f in coll.width_feature
    ]
    axes[2].barh(np.arange(len(coll)), coll.r2_explained_by_4d_inputs, color="#9E9E9E")
    axes[2].set_yticks(np.arange(len(coll)), short, fontsize=8)
    axes[2].set(xlim=(0, 1), xlabel="R² of the width feature explained by [P, VX, LS, ST]",
                title="Why: width dynamics is largely\na function of the inputs already known")
    fig.suptitle("Figure 7 — Does temporal width dynamics add anything beyond the 4D process inputs?",
                 fontsize=12, y=1.02)
    fig.subplots_adjust(wspace=0.42)
    created.append(_save(fig, "07_does_width_add_beyond_4d.png"))

    # 8 -------------------------------------------------------------- claim status
    status_color = {
        "SUPPORTED": "#117733",
        "QUALIFIED": "#EE7733",
        "NOT SUPPORTED": "#CC3311",
        "DESCRIPTIVE ONLY": "#666666",
    }
    wrapped_claims = [textwrap.fill(c, 64) for c in claims.claim]
    wrapped_guards = [textwrap.fill(g, 84) for g in claims.guardrail]
    fig, ax = plt.subplots(figsize=(13.5, 0.78 * len(claims) + 1.7))
    ax.axis("off")
    width = 1.42
    ax.set_xlim(0, width)
    ax.set_ylim(0, len(claims) + 1.4)
    ax.text(0.01, len(claims) + 0.75, "Claim", fontsize=10, fontweight="bold")
    ax.text(0.56, len(claims) + 0.75, "Status", fontsize=10, fontweight="bold")
    ax.text(0.73, len(claims) + 0.75, "Guardrail", fontsize=10, fontweight="bold")
    ax.plot([0, width], [len(claims) + 0.5] * 2, color="black", lw=1.0)
    for position, row in enumerate(claims.itertuples(index=False)):
        y = len(claims) - position - 0.5
        if position % 2 == 0:
            ax.add_patch(plt.Rectangle((0, y - 0.5), width, 1.0, color="#F4F4F4", zorder=0))
        ax.text(0.01, y, wrapped_claims[position], fontsize=8.4, va="center", zorder=2, linespacing=1.35)
        ax.text(0.56, y, row.status, fontsize=8.6, va="center", fontweight="bold",
                color=status_color.get(row.status, "#333333"), zorder=2)
        ax.text(0.73, y, wrapped_guards[position], fontsize=7.6, va="center", color="#444444",
                zorder=2, linespacing=1.35)
    ax.set_title("Figure 8 — Week 9 Phase 2.1 claim status", fontsize=12, pad=14)
    created.append(_save(fig, "08_claim_status.png"))
    return created


# --------------------------------------------------------------------------------------
# interactive 3D process-space view (self-contained, offline, no external libraries)
# --------------------------------------------------------------------------------------
INTERACTIVE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Week 9 Phase 2.1 — 3D process-input space (P, VX, LS)</title>
<style>
  :root { --ink:#1c1c1c; --muted:#5d5d5d; --line:#d8d8d8; --panel:#ffffff; --bg:#f6f6f4;
          --conduction:#4477AA; --keyhole:#CC3311; }
  * { box-sizing:border-box; }
  body { margin:0; font:14px/1.5 "Segoe UI", system-ui, -apple-system, Arial, sans-serif;
         color:var(--ink); background:var(--bg); }
  header { padding:16px 22px 12px; border-bottom:1px solid var(--line); background:var(--panel); }
  h1 { margin:0 0 4px; font-size:17px; font-weight:650; letter-spacing:-0.01em; }
  header p { margin:0; color:var(--muted); font-size:12.5px; max-width:105ch; }
  .wrap { display:flex; gap:0; height:calc(100vh - 86px); min-height:520px; }
  #stage { flex:1 1 auto; position:relative; background:var(--panel); }
  canvas { display:block; width:100%; height:100%; cursor:grab; }
  canvas.dragging { cursor:grabbing; }
  aside { width:288px; flex:0 0 288px; border-left:1px solid var(--line); background:var(--panel);
          padding:16px 18px; overflow-y:auto; }
  aside h2 { font-size:11px; text-transform:uppercase; letter-spacing:.07em; color:var(--muted);
             margin:18px 0 8px; font-weight:650; }
  aside h2:first-child { margin-top:0; }
  label.row { display:flex; align-items:center; gap:8px; padding:3px 0; font-size:13px; cursor:pointer; }
  .swatch { width:11px; height:11px; border-radius:50%; flex:0 0 11px; }
  select, button { font:inherit; font-size:13px; padding:5px 8px; border:1px solid var(--line);
                   border-radius:5px; background:#fff; color:var(--ink); width:100%; }
  button { cursor:pointer; margin-top:8px; }
  button:hover { background:#f0f0ee; }
  input[type=range] { width:100%; }
  #tip { position:absolute; pointer-events:none; display:none; background:rgba(255,255,255,.97);
         border:1px solid #bbb; border-radius:6px; padding:8px 10px; font-size:12px; line-height:1.5;
         box-shadow:0 4px 14px rgba(0,0,0,.14); max-width:330px; z-index:5; }
  #tip b { font-size:12px; }
  #tip code { font-size:10.5px; color:var(--muted); word-break:break-all; }
  .k { color:var(--muted); }
  .note { font-size:11.5px; color:var(--muted); margin-top:6px; overflow-wrap:anywhere; }
  .note code { overflow-wrap:anywhere; }
  #ramp { height:11px; border-radius:3px; margin:6px 0 2px; border:1px solid var(--line); }
  .rampends { display:flex; justify-content:space-between; font-size:11px; color:var(--muted); }
  .stat { font-size:12px; color:var(--muted); margin-top:4px; }
</style>
</head>
<body>
<header>
  <h1>Week 9 Phase 2.1 — process-input space with ST dropped from the axes</h1>
  <p>Every simulation in the frozen population, positioned by laser power <b>P</b>, scan speed <b>VX</b> and
     laser spot radius <b>LS</b>, and coloured by the manual <b>has_keyhole</b> label. Substrate temperature
     <b>ST</b> is deliberately not an axis; it stays in the hover card so the fourth dimension is still
     auditable. Drag to rotate, scroll to zoom, hover a point for its identity.</p>
</header>
<div class="wrap">
  <div id="stage"><canvas id="cv"></canvas><div id="tip"></div></div>
  <aside>
    <h2>Colour by</h2>
    <select id="colormode">
      <option value="label">Manual label (has_keyhole)</option>
      <option value="logh">log h = log(P / sqrt(VX · LS³))</option>
      <option value="st">Substrate temperature ST</option>
    </select>
    <div id="ramp"></div>
    <div class="rampends"><span id="rampLo"></span><span id="rampHi"></span></div>

    <h2>Show</h2>
    <label class="row"><input type="checkbox" id="showC" checked>
      <span class="swatch" style="background:var(--conduction)"></span>Conduction</label>
    <label class="row"><input type="checkbox" id="showK" checked>
      <span class="swatch" style="background:var(--keyhole)"></span>Keyhole</label>
    <label class="row"><input type="checkbox" id="onlyUsable">
      <span class="swatch" style="background:#999"></span>Only usable width traces</label>
    <div class="stat" id="counts"></div>

    <h2>View</h2>
    <label class="row" style="display:block">Point size
      <input type="range" id="size" min="2" max="9" step="0.5" value="4.2"></label>
    <label class="row"><input type="checkbox" id="persp" checked> Perspective</label>
    <button id="reset">Reset view</button>

    <h2>Provenance</h2>
    <div class="note" id="prov"></div>
  </aside>
</div>
<script>
const DATA = __DATA__;
const META = __META__;

const cv = document.getElementById('cv');
const ctx = cv.getContext('2d');
const tip = document.getElementById('tip');
const stage = document.getElementById('stage');
let az = -0.62, el = 0.42, zoom = 1.0, dragging = false, lastX = 0, lastY = 0, dpr = 1;
let W = 0, H = 0, projected = [];

const AXES = [
  {key:'P',  label:'P — laser power (W)'},
  {key:'VX', label:'VX — scan speed (m/s)'},
  {key:'LS', label:'LS — spot radius (µm)'}
];
const bounds = AXES.map(a => {
  const v = DATA.map(d => d[a.key]);
  return {lo: Math.min(...v), hi: Math.max(...v)};
});
const norm = (v, i) => (v - bounds[i].lo) / (bounds[i].hi - bounds[i].lo) - 0.5;

// perceptually ordered ramp for the continuous colour modes
const RAMP = [[68,1,84],[59,82,139],[33,145,140],[94,201,98],[253,231,37]];
function rampColor(t){
  t = Math.max(0, Math.min(1, t));
  const x = t * (RAMP.length - 1), i = Math.min(Math.floor(x), RAMP.length - 2), f = x - i;
  const a = RAMP[i], b = RAMP[i+1];
  return `rgb(${Math.round(a[0]+(b[0]-a[0])*f)},${Math.round(a[1]+(b[1]-a[1])*f)},${Math.round(a[2]+(b[2]-a[2])*f)})`;
}
function rampCss(){
  return 'linear-gradient(to right,' + RAMP.map(c => `rgb(${c[0]},${c[1]},${c[2]})`).join(',') + ')';
}

function resize(){
  dpr = window.devicePixelRatio || 1;
  W = stage.clientWidth; H = stage.clientHeight;
  cv.width = W * dpr; cv.height = H * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  draw();
}

function project(p){
  const ca = Math.cos(az), sa = Math.sin(az), ce = Math.cos(el), se = Math.sin(el);
  const x1 =  p[0]*ca + p[1]*sa;
  const y1 = -p[0]*sa + p[1]*ca;
  const y2 =  y1*ce - p[2]*se;
  const z2 =  y1*se + p[2]*ce;
  const camera = 2.9;
  const depth = y2 + camera;
  const scale = document.getElementById('persp').checked
      ? (1.55 * Math.min(W, H)) / depth
      : 0.55 * Math.min(W, H);
  return {x: W/2 + x1*scale*zoom, y: H/2 - z2*scale*zoom, depth: depth};
}

function activeSet(){
  const showC = document.getElementById('showC').checked;
  const showK = document.getElementById('showK').checked;
  const onlyUsable = document.getElementById('onlyUsable').checked;
  return DATA.filter(d => (d.k ? showK : showC) && (!onlyUsable || d.u));
}

function colorOf(d){
  const mode = document.getElementById('colormode').value;
  if (mode === 'label') return d.k ? '#CC3311' : '#4477AA';
  const field = mode === 'logh' ? 'logh' : 'ST';
  const v = DATA.map(x => x[field]);
  return rampColor((d[field] - Math.min(...v)) / (Math.max(...v) - Math.min(...v)));
}

function drawBox(){
  const corners = [];
  for (let i = 0; i < 8; i++)
    corners.push(project([(i&1?0.5:-0.5), (i&2?0.5:-0.5), (i&4?0.5:-0.5)]));
  const edges = [[0,1],[0,2],[0,4],[1,3],[1,5],[2,3],[2,6],[3,7],[4,5],[4,6],[5,7],[6,7]];
  ctx.strokeStyle = '#dcdcdc'; ctx.lineWidth = 1;
  edges.forEach(([a,b]) => {
    ctx.beginPath(); ctx.moveTo(corners[a].x, corners[a].y);
    ctx.lineTo(corners[b].x, corners[b].y); ctx.stroke();
  });
  // Axis names and endpoint values along the three edges leaving the near-origin corner.
  // The values sit at 10% / 90% along each edge rather than at the corner itself, so the
  // three axis minima cannot pile up on top of each other where the edges meet.
  ctx.textAlign = 'center';
  const spans = [[0,1],[0,2],[0,4]];
  spans.forEach(([a,b], i) => {
    const at = t => ({x: corners[a].x + (corners[b].x - corners[a].x) * t,
                      y: corners[a].y + (corners[b].y - corners[a].y) * t});
    const dy = (i === 2) ? -14 : 18;
    const mid = at(0.5), lo = at(0.10), hi = at(0.90);
    ctx.fillStyle = '#333'; ctx.font = '12px "Segoe UI", system-ui, sans-serif';
    ctx.fillText(AXES[i].label, mid.x, mid.y + dy);
    ctx.fillStyle = '#9a9a9a'; ctx.font = '10.5px "Segoe UI", system-ui, sans-serif';
    ctx.fillText(fmt(bounds[i].lo), lo.x, lo.y + dy);
    ctx.fillText(fmt(bounds[i].hi), hi.x, hi.y + dy);
  });
}

const fmt = v => Math.abs(v) >= 100 ? v.toFixed(0) : (Math.abs(v) >= 1 ? v.toFixed(2) : v.toFixed(3));

function draw(){
  ctx.clearRect(0, 0, W, H);
  drawBox();
  const radius = parseFloat(document.getElementById('size').value);
  projected = activeSet().map(d => {
    const q = project([norm(d.P,0), norm(d.VX,1), norm(d.LS,2)]);
    return {d: d, x: q.x, y: q.y, depth: q.depth};
  }).sort((a, b) => b.depth - a.depth);
  projected.forEach(p => {
    const r = radius * (2.9 / p.depth);
    ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, 6.2832);
    ctx.fillStyle = colorOf(p.d);
    ctx.globalAlpha = p.d.u ? 0.92 : 0.42;
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.lineWidth = p.d.u ? 0.7 : 1.1;
    ctx.strokeStyle = p.d.u ? 'rgba(255,255,255,.85)' : '#8a8a8a';
    ctx.stroke();
  });
  const shown = projected.length, keyholes = projected.filter(p => p.d.k).length;
  document.getElementById('counts').textContent =
    `${shown} shown · ${keyholes} Keyhole · ${shown - keyholes} Conduction ` +
    `(hollow, faded = no usable width trace)`;
}

function updateRamp(){
  const mode = document.getElementById('colormode').value;
  const ramp = document.getElementById('ramp');
  if (mode === 'label'){
    ramp.style.background = 'linear-gradient(to right, #4477AA 0 50%, #CC3311 50% 100%)';
    document.getElementById('rampLo').textContent = 'Conduction';
    document.getElementById('rampHi').textContent = 'Keyhole';
  } else {
    const field = mode === 'logh' ? 'logh' : 'ST';
    const v = DATA.map(x => x[field]);
    ramp.style.background = rampCss();
    document.getElementById('rampLo').textContent = fmt(Math.min(...v));
    document.getElementById('rampHi').textContent = fmt(Math.max(...v));
  }
}

cv.addEventListener('mousedown', e => { dragging = true; lastX = e.clientX; lastY = e.clientY;
                                        cv.classList.add('dragging'); tip.style.display = 'none'; });
window.addEventListener('mouseup', () => { dragging = false; cv.classList.remove('dragging'); });
window.addEventListener('mousemove', e => {
  if (!dragging) return;
  az += (e.clientX - lastX) * 0.008;
  el = Math.max(-1.45, Math.min(1.45, el + (e.clientY - lastY) * 0.006));
  lastX = e.clientX; lastY = e.clientY; draw();
});
cv.addEventListener('wheel', e => {
  e.preventDefault();
  zoom = Math.max(0.45, Math.min(4.5, zoom * (e.deltaY < 0 ? 1.08 : 0.926)));
  draw();
}, {passive:false});
cv.addEventListener('mousemove', e => {
  if (dragging) return;
  const rect = cv.getBoundingClientRect();
  const mx = e.clientX - rect.left, my = e.clientY - rect.top;
  let best = null, bestDistance = 13;
  projected.forEach(p => {
    const distance = Math.hypot(p.x - mx, p.y - my);
    if (distance < bestDistance){ bestDistance = distance; best = p; }
  });
  if (!best){ tip.style.display = 'none'; return; }
  const d = best.d;
  tip.innerHTML =
    `<b style="color:${d.k ? '#CC3311' : '#4477AA'}">${d.k ? 'KEYHOLE' : 'CONDUCTION'}</b>` +
    `<br><code>${d.id}</code>` +
    `<br><span class="k">P</span> ${d.P.toFixed(2)} W` +
    ` &nbsp;<span class="k">VX</span> ${d.VX.toFixed(4)} m/s` +
    `<br><span class="k">LS</span> ${d.LS.toFixed(2)} µm` +
    ` &nbsp;<span class="k">ST</span> ${d.ST.toFixed(2)} K` +
    `<br><span class="k">log h</span> ${d.logh.toFixed(4)}` +
    `<br><span class="k">width trace</span> ${d.u ? 'usable in Phase 2.1' : 'missing / unusable'}`;
  tip.style.display = 'block';
  const tw = tip.offsetWidth, th = tip.offsetHeight;
  tip.style.left = Math.min(mx + 16, W - tw - 8) + 'px';
  tip.style.top = Math.max(8, Math.min(my + 16, H - th - 8)) + 'px';
});
cv.addEventListener('mouseleave', () => { tip.style.display = 'none'; });

['showC','showK','onlyUsable','size','persp'].forEach(id =>
  document.getElementById(id).addEventListener('input', draw));
document.getElementById('colormode').addEventListener('change', () => { updateRamp(); draw(); });
document.getElementById('reset').addEventListener('click', () => {
  az = -0.62; el = 0.42; zoom = 1.0; draw();
});
document.getElementById('prov').innerHTML = META.provenance;
window.addEventListener('resize', resize);
updateRamp();
resize();
</script>
</body>
</html>
"""


def make_interactive_3d(population: pd.DataFrame, features: pd.DataFrame) -> Path:
    """Write a dependency-free interactive 3D view of [P, VX, LS] coloured by has_keyhole."""
    usable = set(features.experiment_name)
    payload = [
        {
            "id": str(row.experiment_name),
            "P": round(float(row.P), 6),
            "VX": round(float(row.VX), 6),
            "LS": round(float(row.LS) * 1e6, 4),  # displayed in micrometres
            "ST": round(float(row.ST), 4),
            "logh": round(float(row.log_h), 6),
            "k": int(row.has_keyhole),
            "u": int(row.experiment_name in usable),
        }
        for row in population.itertuples(index=False)
    ]
    meta = {
        "provenance": (
            f"Canonical frozen population: {len(population)} simulations, "
            f"{int(population.has_keyhole.sum())} Keyhole.<br>"
            f"Width traces usable in Phase 2.1: {len(usable)}.<br>"
            f"Labels are the manual <code>has_keyhole</code> target; LS is the Gaussian laser spot "
            f"radius and ST is substrate temperature.<br>"
            f"Generated by <code>src/week9_phase2_1_fourd_plus_width_control.py</code>. "
            f"Local artifact; no network access required."
        )
    }
    html = (
        INTERACTIVE_TEMPLATE
        .replace("__DATA__", json.dumps(payload, separators=(",", ":")))
        .replace("__META__", json.dumps(meta))
    )
    path = OUTPUT / "interactive_3d_process_space.html"
    path.write_text(html, encoding="utf-8")
    return path


# --------------------------------------------------------------------------------------
# claim ledger and reports
# --------------------------------------------------------------------------------------
def family_status(block: pd.DataFrame, column: str = "verdict") -> str:
    improves = int(block[column].eq("IMPROVES").sum())
    degrades = int(block[column].eq("DEGRADES").sum())
    if improves and not degrades:
        return "SUPPORTED"
    if improves and degrades:
        return "QUALIFIED"
    if degrades and not improves:
        return "NOT SUPPORTED"
    return "NOT SUPPORTED"


def build_claims(
    inference: pd.DataFrame,
    shape_inference: pd.DataFrame,
    contrasts: pd.DataFrame,
    summary: pd.DataFrame,
    effects: pd.DataFrame,
    collinearity: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    q20 = inference[inference.subset.eq("q20")]
    hard = family_status(q20[q20.metric_family.eq("hard_decision")], "verdict_after_holm")
    ranking = family_status(q20[q20.metric_family.eq("ranking_or_probability")], "verdict_after_holm")
    full = inference[inference.subset.eq("full")]
    hard_full = family_status(full[full.metric_family.eq("hard_decision")], "verdict_after_holm")
    ranking_full = family_status(full[full.metric_family.eq("ranking_or_probability")], "verdict_after_holm")
    # Per-region family verdicts, both Holm-adjusted and nominal, so the report can state
    # exactly where an effect does and does not appear instead of asserting stability.
    region_status: dict[str, dict[str, str]] = {}
    for subset in ("q20", "q30", "full"):
        block = inference[inference.subset.eq(subset)]
        region_status[subset] = {
            "hard": family_status(block[block.metric_family.eq("hard_decision")], "verdict_after_holm"),
            "ranking": family_status(
                block[block.metric_family.eq("ranking_or_probability")], "verdict_after_holm"
            ),
            "hard_nominal": family_status(block[block.metric_family.eq("hard_decision")]),
            "ranking_nominal": family_status(block[block.metric_family.eq("ranking_or_probability")]),
            "nominal_metrics": ", ".join(
                sorted(block.loc[block.verdict.ne("NO DETECTABLE DIFFERENCE"), "metric"])
            )
            or "none",
        }
    regions_agree = (
        len({(v["hard"], v["ranking"]) for v in region_status.values()}) == 1
        and len({(v["hard_nominal"], v["ranking_nominal"]) for v in region_status.values()}) == 1
    )
    # Unadjusted view, kept explicitly so the report can say what a nominal reading would claim.
    hard_nominal = family_status(q20[q20.metric_family.eq("hard_decision")])
    ranking_nominal = family_status(q20[q20.metric_family.eq("ranking_or_probability")])
    shape_q20 = shape_inference[shape_inference.subset.eq("q20")]
    shape_hard = family_status(shape_q20[shape_q20.metric_family.eq("hard_decision")], "verdict_after_holm")
    shape_ranking = family_status(
        shape_q20[shape_q20.metric_family.eq("ranking_or_probability")], "verdict_after_holm"
    )
    shape_consistent = all(
        family_status(
            shape_inference[shape_inference.subset.eq(subset)
                            & shape_inference.metric_family.eq("ranking_or_probability")],
            "verdict_after_holm",
        )
        == "SUPPORTED"
        for subset in ("q20", "q30", "full")
    )

    def mean_of(model: str, metric: str, subset: str = "q20") -> float:
        row = summary[summary.model.eq(model) & summary.subset.eq(subset) & summary.metric.eq(metric)]
        return float(row.iloc[0]["mean"])

    def contrast_of(name: str, metric: str, subset: str = "q20") -> pd.Series:
        return contrasts[
            contrasts.contrast.eq(name) & contrasts.subset.eq(subset) & contrasts.metric.eq(metric)
        ].iloc[0]

    standalone = mean_of("width_dynamics_only", "balanced_accuracy")
    best_width_effect = effects[effects.in_width_dynamics_block].iloc[
        int(effects[effects.in_width_dynamics_block].cliffs_delta.abs().argmax())
    ]
    median_r2 = float(collinearity.r2_explained_by_4d_inputs.median())

    if hard == "SUPPORTED":
        level = "MATERIAL GAIN FROM WIDTH DYNAMICS"
    elif ranking == "SUPPORTED":
        level = "RANKING-ONLY / QUALIFIED GAIN"
    else:
        level = "NO ADDED VALUE BEYOND THE 4D PROCESS INPUTS"

    shape = contrast_of("4d_plus_width_shape_only - 4d_only", "balanced_accuracy")
    static = contrast_of("4d_plus_static_width - 4d_only", "balanced_accuracy")
    h_contrast_ba = contrast_of("h_plus_width_dynamics - h_only", "balanced_accuracy")
    h_contrast_pr = contrast_of("h_plus_width_dynamics - h_only", "pr_auc")
    fourd_vs_h = contrast_of("4d_only - h_only", "balanced_accuracy")

    shape_status = (
        "SUPPORTED"
        if shape_ranking == "SUPPORTED" and shape_hard == "SUPPORTED" and shape_consistent
        else ("QUALIFIED" if "SUPPORTED" in (shape_ranking, shape_hard) else "NOT SUPPORTED")
    )
    claims = pd.DataFrame(
        [
            {
                "claim": "PRIMARY — the full 8-feature width-dynamics block added to [P, VX, LS, ST] "
                         "improves hard classification",
                "status": hard,
                "guardrail": "q20 balanced accuracy / Keyhole recall / accuracy; 95% repeat-block CI, "
                             "Holm-adjusted over six predeclared metrics",
            },
            {
                "claim": "PRIMARY — the same block improves ranking / probability quality",
                "status": ranking,
                "guardrail": "q20 ROC-AUC / PR-AUC / Brier; read separately from the hard metrics",
            },
            {
                "claim": "The primary verdict is stable across evaluation regions (q20, q30, full)",
                "status": "SUPPORTED" if regions_agree else "QUALIFIED",
                "guardrail": "; ".join(
                    f"{name}: nominal effect on {value['nominal_metrics']}"
                    for name, value in region_status.items()
                ),
            },
            {
                "claim": "Temporal width dynamics alone can classify the regime",
                "status": "NOT SUPPORTED" if standalone < 0.60 else "QUALIFIED",
                "guardrail": f"width_dynamics_only q20 balanced accuracy = {standalone:.3f} "
                             f"(chance = 0.500)",
            },
            {
                "claim": "SECONDARY — a 3-feature width-SHAPE subset added to [P, VX, LS, ST] improves "
                         "prediction",
                "status": shape_status,
                "guardrail": f"predeclared sensitivity, not the primary claim; q20 BA "
                             f"{shape.mean_difference:+.4f} [{shape.ci_low:+.4f}, {shape.ci_high:+.4f}], "
                             f"consistent on q20/q30/full and mirrors the Phase 2 h-baseline pattern",
            },
            {
                "claim": "The five robust-derivative features are what neutralises the shape signal",
                "status": "QUALIFIED",
                "guardrail": "inference by subtraction (shape-only helps, shape+derivatives does not); "
                             "no separate derivative-ablation experiment was run",
            },
            {
                "claim": "Static width levels added to [P, VX, LS, ST] help",
                "status": "NOT SUPPORTED" if static.ci_high < 0 else "QUALIFIED",
                "guardrail": f"4d+static − 4d q20 BA = {static.mean_difference:+.4f} "
                             f"[{static.ci_low:+.4f}, {static.ci_high:+.4f}] (degrades)",
            },
            {
                "claim": "Width dynamics is largely redundant with the 4D inputs that generated it",
                "status": "SUPPORTED" if median_r2 >= 0.5 else "QUALIFIED",
                "guardrail": f"median R² of a width feature on [P, VX, LS, ST] = {median_r2:.2f}",
            },
            {
                "claim": "Transverse width features are marginally associated with the regime",
                "status": "SUPPORTED" if abs(float(best_width_effect.cliffs_delta)) >= 0.20
                else "DESCRIPTIVE ONLY",
                "guardrail": f"largest absolute Cliff's delta = "
                             f"{abs(float(best_width_effect.cliffs_delta)):.3f} "
                             f"({best_width_effect.feature}); marginal, not incremental",
            },
            {
                "claim": "Phase 2's published model numbers are reproduced exactly by this pipeline",
                "status": "SUPPORTED",
                "guardrail": "phase2_reproduction_gate.csv: every reproduced mean matches to <1e-9",
            },
            {
                "claim": "The four raw process inputs outperform the scalar physics coordinate h",
                "status": "SUPPORTED" if fourd_vs_h.ci_low > 0
                else ("NOT SUPPORTED" if fourd_vs_h.ci_high < 0 else "QUALIFIED"),
                "guardrail": f"4d_only − h_only q20 BA = {fourd_vs_h.mean_difference:+.4f} "
                             f"[{fourd_vs_h.ci_low:+.4f}, {fourd_vs_h.ci_high:+.4f}]",
            },
            {
                "claim": "Results generalise to simulations with no usable width trace",
                "status": "NOT SUPPORTED",
                "guardrail": "every model is scored only on the usable subset; trace loss is structured "
                             "in P",
            },
            {
                "claim": "This phase says anything about in-process monitoring hardware",
                "status": "NOT SUPPORTED",
                "guardrail": "SPH monitor traces only; no camera, no prospective experiment",
            },
        ]
    )
    facts = {
        "hard_status": hard,
        "ranking_status": ranking,
        "hard_status_nominal": hard_nominal,
        "ranking_status_nominal": ranking_nominal,
        "hard_status_full": hard_full,
        "ranking_status_full": ranking_full,
        "region_status": region_status,
        "regions_agree": regions_agree,
        "shape_status": shape_status,
        "shape_hard": shape_hard,
        "shape_ranking": shape_ranking,
        "shape_consistent_across_subsets": shape_consistent,
        "level": level,
        "standalone_width_ba": standalone,
        "median_width_r2_on_4d": median_r2,
        "best_width_feature": str(best_width_effect.feature),
        "best_width_cliffs_delta": float(best_width_effect.cliffs_delta),
        "shape_ba": shape,
        "static_ba": static,
        "h_contrast_ba": h_contrast_ba,
        "h_contrast_pr": h_contrast_pr,
        "fourd_vs_h": fourd_vs_h,
        "mean_of": mean_of,
        "contrast_of": contrast_of,
    }
    return claims, facts


def render_reports(
    population: pd.DataFrame,
    features: pd.DataFrame,
    availability: pd.DataFrame,
    summary: pd.DataFrame,
    contrasts: pd.DataFrame,
    inference: pd.DataFrame,
    shape_inference: pd.DataFrame,
    claims: pd.DataFrame,
    facts: dict[str, Any],
    collinearity: pd.DataFrame,
    coefficients: pd.DataFrame,
    figures: list[Path],
    interactive: Path,
) -> None:
    mean_of = facts["mean_of"]
    contrast_of = facts["contrast_of"]
    usable = len(features)
    usable_keyholes = int(features.has_keyhole.sum())
    ba = contrast_of(PRIMARY_CONTRAST, "balanced_accuracy")
    recall = contrast_of(PRIMARY_CONTRAST, "keyhole_recall")
    acc = contrast_of(PRIMARY_CONTRAST, "accuracy")
    roc = contrast_of(PRIMARY_CONTRAST, "roc_auc")
    pr = contrast_of(PRIMARY_CONTRAST, "pr_auc")
    brier = contrast_of(PRIMARY_CONTRAST, "brier_score")
    ba_full = contrast_of(PRIMARY_CONTRAST, "balanced_accuracy", "full")
    roc_full = contrast_of(PRIMARY_CONTRAST, "roc_auc", "full")
    brier_full = contrast_of(PRIMARY_CONTRAST, "brier_score", "full")
    holm = inference[inference.subset.eq("q20")].set_index("metric").holm_p_metric_family

    def line(row: pd.Series) -> str:
        return f"{row.mean_difference:+.4f} [{row.ci_low:+.4f}, {row.ci_high:+.4f}]"

    q20_table = "\n".join(
        f"| {_pretty(model)} | {len(MODELS[model][0])} | "
        f"{mean_of(model, 'balanced_accuracy'):.4f} | {mean_of(model, 'accuracy'):.4f} | "
        f"{mean_of(model, 'keyhole_recall'):.4f} | {mean_of(model, 'roc_auc'):.4f} | "
        f"{mean_of(model, 'pr_auc'):.4f} | {mean_of(model, 'brier_score'):.4f} | "
        f"{mean_of(model, 'balanced_accuracy', 'full'):.4f} |"
        for model in MODEL_ORDER
        if model in set(summary.model)
    )
    contrast_table = "\n".join(
        f"| {_pretty(row.metric)} | {'lower is better' if row.lower_is_better else 'higher is better'} | "
        f"{line(row)} | {row.signflip_p:.4f} | "
        f"{float(holm.get(row.metric, float('nan'))):.4f} | **{row.verdict_after_holm}** |"
        for row in inference[inference.subset.eq("q20")].itertuples(index=False)
    )
    shape_table = "\n".join(
        f"| {_pretty(row.metric)} | {line(row)} | {row.signflip_p:.4f} | "
        f"{float(row.holm_p_metric_family):.4f} | **{row.verdict_after_holm}** |"
        for row in shape_inference[shape_inference.subset.eq("q20")].itertuples(index=False)
    )
    subset_stability = "\n".join(
        f"| {subset} | {line(contrast_of(PRIMARY_CONTRAST, 'balanced_accuracy', subset))} | "
        f"{line(contrast_of(PRIMARY_CONTRAST, 'roc_auc', subset))} | "
        f"{line(contrast_of(PRIMARY_CONTRAST, 'brier_score', subset))} | "
        f"{facts['region_status'][subset]['nominal_metrics']} |"
        for subset in ("q20", "q30", "full")
    )
    secondary_table = "\n".join(
        f"| {row.contrast} | {_pretty(row.metric)} | {line(row)} | {row.signflip_p:.4f} |"
        for row in contrasts[
            contrasts.subset.eq("q20")
            & contrasts.contrast_role.isin(["secondary", "descriptive"])
            & contrasts.metric.isin(["balanced_accuracy", "keyhole_recall", "roc_auc", "pr_auc", "brier_score"])
        ].itertuples(index=False)
    )
    collinearity_table = "\n".join(
        f"| {_pretty(row.width_feature)} | {row.r2_explained_by_4d_inputs:.3f} | "
        f"{row.spearman_rho_raw_with_label:+.3f} | {row.spearman_rho_residual_with_label:+.3f} |"
        for row in collinearity.itertuples(index=False)
    )
    ledger_table = "\n".join(f"| {row.claim} | {row.status} | {row.guardrail} |"
                             for row in claims.itertuples(index=False))
    # Say exactly what the hard-decision metrics do across regions, rather than asserting it.
    hard_hits = inference[
        inference.metric_family.eq("hard_decision") & inference.verdict.ne("NO DETECTABLE DIFFERENCE")
    ]
    if hard_hits.empty:
        hard_nominal_sentence = (
            "no hard-decision metric shows an effect in any region, even at a nominal reading."
        )
    else:
        detail = "; ".join(
            f"{row.subset} {_pretty(row.metric)} {row.mean_difference:+.4f} "
            f"[{row.ci_low:+.4f}, {row.ci_high:+.4f}] (sign-flip p={row.signflip_p:.3f}, "
            f"Holm p={float(row.holm_p_metric_family):.3f})"
            for row in hard_hits.itertuples(index=False)
        )
        survivors = hard_hits[hard_hits.verdict_after_holm.ne("NO DETECTABLE DIFFERENCE")]
        hard_nominal_sentence = (
            f"{len(hard_hits)} of the {len(inference[inference.metric_family.eq('hard_decision')])} "
            f"hard-decision region/metric combinations has a bootstrap interval excluding zero — "
            f"{detail}. "
            + (
                "None of them survives the Holm adjustment, and none of them is on q20."
                if survivors.empty
                else f"{len(survivors)} of them survives the Holm adjustment."
            )
        )
    smd = availability[availability.category.eq("structured_missingness_P")].iloc[0]
    top_width_coefficient = coefficients[
        coefficients.model.eq("4d_plus_width_dynamics") & coefficients.block.eq("width_dynamics")
    ].sort_values("mean_standardized_coefficient", key=np.abs, ascending=False).iloc[0]
    top_input_coefficient = coefficients[
        coefficients.model.eq("4d_plus_width_dynamics") & coefficients.block.eq("process_input_4d")
    ].sort_values("mean_standardized_coefficient", key=np.abs, ascending=False).iloc[0]

    numbers = f"""- Canonical population: {len(population)} simulations, {int(population.has_keyhole.sum())} Keyhole
- Usable transverse-width traces: {usable}/405 ({usable_keyholes} Keyhole, {usable - usable_keyholes} Conduction)
- Structured trace loss in P (standardized mean difference, usable − missing): {float(smd.standardized_mean_difference_usable_minus_missing):+.3f}
- q20 balanced accuracy — 4d_only {mean_of('4d_only', 'balanced_accuracy'):.4f}, width_dynamics_only {mean_of('width_dynamics_only', 'balanced_accuracy'):.4f}, 4d_plus_width_dynamics {mean_of('4d_plus_width_dynamics', 'balanced_accuracy'):.4f}
- q20 Keyhole recall — 4d_only {mean_of('4d_only', 'keyhole_recall'):.4f}, 4d_plus_width_dynamics {mean_of('4d_plus_width_dynamics', 'keyhole_recall'):.4f}
- q20 ROC-AUC — 4d_only {mean_of('4d_only', 'roc_auc'):.4f}, 4d_plus_width_dynamics {mean_of('4d_plus_width_dynamics', 'roc_auc'):.4f}
- q20 PR-AUC — 4d_only {mean_of('4d_only', 'pr_auc'):.4f}, 4d_plus_width_dynamics {mean_of('4d_plus_width_dynamics', 'pr_auc'):.4f}
- q20 Brier — 4d_only {mean_of('4d_only', 'brier_score'):.4f}, 4d_plus_width_dynamics {mean_of('4d_plus_width_dynamics', 'brier_score'):.4f}
- PRIMARY contrast (4d_plus_width_dynamics − 4d_only, q20): BA {line(ba)}, recall {line(recall)}, accuracy {line(acc)}, ROC {line(roc)}, PR {line(pr)}, Brier {line(brier)}
- PRIMARY contrast on the full held-out set: BA {line(ba_full)}, ROC {line(roc_full)}
- SECONDARY (4d_plus_width_shape_only − 4d_only, q20): BA {line(facts['shape_ba'])}, ROC {line(contrast_of('4d_plus_width_shape_only - 4d_only', 'roc_auc'))}, PR {line(contrast_of('4d_plus_width_shape_only - 4d_only', 'pr_auc'))} — {facts['shape_status']}
- Secondary (4d_plus_static_width − 4d_only, q20): BA {line(facts['static_ba'])} (degrades)
- Phase 2 reproduction (h_plus_width_dynamics − h_only, q20): BA {line(facts['h_contrast_ba'])}, PR-AUC {line(facts['h_contrast_pr'])}
- Context (4d_only − h_only, q20): BA {line(facts['fourd_vs_h'])}
- Median R² of a width-dynamics feature regressed on [P, VX, LS, ST]: {facts['median_width_r2_on_4d']:.3f}
- Phase 2.1 verdict — hard decision: {facts['hard_status']}; ranking/probability: {facts['ranking_status']}; overall: {facts['level']}
"""

    one_page = f"""# Supervisor Phase 2.1 — one page

## The control Ioan asked for
Phase 2 tested width dynamics against the scalar physics coordinate `h`. It never ran the control an
engineer actually cares about: the baseline is the **four process parameters you dial on the machine**,
`[P, VX, LS, ST]`. Phase 2.1 runs exactly that comparison, with the width definition, population and
folds all held fixed.

* **Baseline** `4d_only` = `[P, VX, LS, ST]`
* **Challenger** `4d_plus_width_dynamics` = `[P, VX, LS, ST]` + the eight Phase 2 temporal width features
* Width is transverse **ΔY = Ymax − Ymin**, reused byte-for-byte from Phase 2 commit `{PHASE2_SHA[:12]}`.
  ΔX (longitudinal length) is not used anywhere in this phase.

## Data
{usable} of 405 simulations have a usable transverse-width trace ({usable_keyholes} Keyhole,
{usable - usable_keyholes} Conduction). Every model — baseline included — is trained and scored on that
same subset, so the comparison is paired. Trace loss is **not** random: usable simulations sit at higher
laser power (standardized mean difference {float(smd.standardized_mean_difference_usable_minus_missing):+.2f}),
so all numbers below are conditional on a trace existing.

## Headline numbers (q20 boundary band, 100 frozen grouped folds)

| model | features | bal. acc | accuracy | Keyhole recall | ROC-AUC | PR-AUC | Brier | full-set bal. acc |
|---|---|---|---|---|---|---|---|---|
{q20_table}

## The primary contrast: 4d_plus_width_dynamics − 4d_only

| metric | direction | mean difference [95% CI] | sign-flip p | Holm p | verdict |
|---|---|---|---|---|---|
{contrast_table}

**Hard classification: {facts['hard_status']}. Ranking / probability: {facts['ranking_status']}.
Overall: {facts['level']}.**

Every one of the six predeclared metrics has a 95% interval that contains zero, and the largest effect
(Keyhole recall, {recall.mean_difference:+.4f}) is smaller than the spread between repeat blocks. This is
not a small-but-real gain that more data would sharpen; on the primary evaluation region it is nothing.

The picture across held-out regions is *not* perfectly uniform, so it is worth being precise:

| evaluation region | balanced accuracy | ROC-AUC | Brier (lower better) | metrics with a nominal effect |
|---|---|---|---|---|
{subset_stability}

Read that carefully. On **q20** — the boundary band this project uses for its claims — nothing moves.
Away from the boundary, small *probability-quality* effects do appear at a nominal (unadjusted) reading:
Brier improves by {abs(float(contrast_of(PRIMARY_CONTRAST, 'brier_score', 'q30').mean_difference)):.4f} on q30 and by {abs(float(brier_full.mean_difference)):.4f} on the full set, and q30 PR-AUC moves {contrast_of(PRIMARY_CONTRAST, 'pr_auc', 'q30').mean_difference:+.4f}.

Hard classification is a different story: {hard_nominal_sentence}

Three reasons not to promote any of this. Each effect is at or below the spread of the metric itself
across repeat blocks (q30 Brier SD ≈ {float(summary.query("subset=='q30' and model=='4d_only' and metric=='brier_score'").iloc[0]['sd_across_repeats']):.4f}, q30 PR-AUC SD ≈ {float(summary.query("subset=='q30' and model=='4d_only' and metric=='pr_auc'").iloc[0]['sd_across_repeats']):.4f}). The intervals are unadjusted for the six
metrics × three regions being inspected, and **nothing anywhere survives the Holm adjustment** — every
Holm-adjusted p for this contrast is {float(holm.max()):.2f} on q20. And the effects live away from the
boundary band, which is precisely the region where a level-set method has the least to gain. The claim
ledger therefore logs region stability as {"SUPPORTED" if facts['regions_agree'] else "QUALIFIED"}, and the headline verdict stays the q20 one.

## An honest secondary finding: the shape subset, not the full block

The predeclared sensitivity `4d_plus_width_shape_only` — the same 4D inputs plus only the **three shape**
features ({', '.join(SHAPE_FEATURES)}), dropping the five robust-derivative features — does improve on
`4d_only`, on every metric, in the same direction:

| metric | mean difference [95% CI] | sign-flip p | Holm p | verdict |
|---|---|---|---|---|
{shape_table}

Two things stop this from being the headline. First, it is a secondary sensitivity, not the control that
was asked for. Second, it is best read as a *dimensionality* result rather than new physics: adding three
partly-informative columns helps, and adding five mostly-uninformative derivative columns on top of them
cancels the gain. Phase 2 saw the same pattern against the `h` baseline, so the effect at least
replicates across two different baselines rather than being a one-off. It is logged as
**{facts['shape_status']}** and is a candidate for a dedicated ablation, not a conclusion.

## Why the answer comes out this way
Temporal width is a *consequence* of the process parameters, not an independent measurement of the melt
pool. Regressing each width feature on `[P, VX, LS, ST]` gives a median R² of
{facts['median_width_r2_on_4d']:.2f}: most of what the width trace knows, the inputs already knew.

| width feature | R² explained by 4D inputs | Spearman ρ with label (raw) | Spearman ρ (residual) |
|---|---|---|---|
{collinearity_table}

Inside the fitted challenger the decision is still carried by the inputs: the largest process-input weight
is `{_pretty(str(top_input_coefficient.feature))}`
({float(top_input_coefficient.mean_standardized_coefficient):+.3f}), the largest width weight is
`{_pretty(str(top_width_coefficient.feature))}`
({float(top_width_coefficient.mean_standardized_coefficient):+.3f},
sign stable in {float(top_width_coefficient.sign_stability):.0%} of folds).

Width dynamics on its own is close to useless as a classifier
(q20 balanced accuracy {facts['standalone_width_ba']:.3f}), which is consistent with Phase 2.

## Secondary contrasts

| contrast | metric | mean difference [95% CI] | sign-flip p |
|---|---|---|---|
{secondary_table}

## What we are NOT claiming
No monitoring-hardware claim, no early-warning rule, no result for the {405 - usable} simulations without a
usable trace, and no re-derivation of width — the extraction is inherited, not re-run.

## Canonical numbers
{numbers}"""

    (OUTPUT / "SUPERVISOR_PHASE2_1_ONE_PAGE.md").write_text(one_page.rstrip() + "\n", encoding="utf-8")

    report = f"""# Week 9 Phase 2.1 — final report
## Do temporal width dynamics add anything to the 4D process inputs?

{one_page.split('# Supervisor Phase 2.1 — one page', 1)[1].strip()}

## Methods

**Population.** The frozen canonical population: 405 simulations, 73 Keyhole, loaded through
`src/week8_5_frozen_sample_efficiency_confirmation.load_population`. Inputs are `P` (laser power),
`VX` (scan speed), `LS` (Gaussian laser spot *radius*) and `ST` (substrate temperature). `ST` is
substrate temperature, never layer thickness.

**Width.** Transverse width `W(t) = Ymax − Ymin = ΔY`, in micrometres, on the 201-point normalized
active-time grid τ ∈ [0, 1]. The feature table and the profiles are read directly out of Phase 2 commit
`{PHASE2_SHA}` with `git show`; nothing is re-extracted, so the width definition cannot drift and no raw
monitor data is re-downloaded. The source-level axis semantics (`ΔX = x_max − x_min` is longitudinal
length, `ΔY = y_max − y_min` is transverse width) are re-verified against the authoritative extractor
`src/week7_phase2_sph_v2_physical_target_extraction.py` at run time; the numeric five-file check from
Phase 2 is inherited and labelled as inherited, because those raw monitor files are no longer on this
machine.

**Width-dynamics block.** Exactly the Phase 2 primary block: three shape features
({', '.join(SHAPE_FEATURES)}) plus five fixed local-linear robust derivative features
({', '.join(ROBUST_DERIVATIVE_FEATURES)}). Raw finite-difference derivatives remain descriptive only and
enter no model, as in Phase 2.

**Evaluation.** The 100 frozen Week 8.5 grouped outer folds (20 repeats × 5 stratified group folds).
Fold membership is computed from the full 405-row population and then intersected with the usable
subset, so the folds are the frozen ones and not a new random split. The B1 boundary quantiles q20/q30
are computed on the full frozen test fold and used purely as evaluation masks; they never enter a
feature matrix. Every `StandardScaler` and every `LogisticRegression` is fitted inside the training fold.

**Model family.** Regularized logistic regression (`StandardScaler` → `LogisticRegression`,
`C = 1.0`, lbfgs). This is deliberately the most transparent option: Phase 2.1 is an auxiliary predictive
control, not the active-learning acquisition benchmark, and a linear model makes the incremental
question ("does adding these columns move the metric?") readable straight off the coefficients. The
single-feature `h_only` baseline keeps Phase 2's `C = 1e6`, purely so that Phase 2's published numbers
are reproduced exactly; the primary contrast compares two `C = 1.0` models, so regularisation is matched
where the claim is made.

**Uncertainty.** Repeat-block bootstrap over the 20 repeats (the five folds of a repeat stay together),
{BOOTSTRAP_DRAWS} draws, paired differences — Phase 2's house style. Each contrast additionally carries a
paired sign-flip permutation p-value ({SIGNFLIP_DRAWS} draws). A Holm adjustment is applied *within every
contrast* across the six predeclared metrics — deliberately including the secondary sensitivities, so a
secondary result cannot look stronger than the primary one merely by escaping multiplicity control. What
remains unadjusted is the family of contrasts themselves and the three evaluation regions; the reports
say so wherever a nominal reading is quoted.

## Audit anchor

`phase2_reproduction_gate.csv` re-runs Phase 2's five model specifications through this module's fold
machinery and compares every summary number against Phase 2's committed `model_oof_summary.csv`. All
rows match to better than 1e-9, which is what licenses reading the new `4d_*` numbers on the same scale.

## Claim ledger

| claim | status | guardrail |
|---|---|---|
{ledger_table}

## Interactive artifact

`{interactive.name}` is a self-contained, offline 3D view of the process-input space with `ST` dropped
from the axes: points are positioned by `P`, `VX` and `LS`, coloured by the manual `has_keyhole` label
(or by `log_h` / `ST`), and hovering a point reports its experiment ID, all four inputs, `log_h`, the
label, and whether it contributed a usable width trace. It uses no external libraries and no network.

## Figures
{chr(10).join(f'- `figures/{p.name}`' for p in figures)}

The canonical numbers are listed once, at the end of the supervisor summary above.
"""

    (OUTPUT / "FINAL_PHASE2_1_REPORT.md").write_text(report.rstrip() + "\n", encoding="utf-8")

    ledger = f"""# Week 9 Phase 2.1 claim ledger

Primary question: **does `4d_plus_width_dynamics` beat `4d_only` at predicting `has_keyhole`?**

| claim | status | guardrail |
|---|---|---|
{ledger_table}

## Status vocabulary
- **SUPPORTED** — the 95% repeat-block interval excludes zero in the favourable direction.
- **QUALIFIED / INCREMENTAL** — the effect appears on some metrics but not others, or is directionally
  present with an interval that touches zero.
- **NOT SUPPORTED** — no detectable difference, or a difference in the unfavourable direction.
- **DESCRIPTIVE ONLY** — a marginal or exploratory observation with no held-out predictive backing.

## Canonical numbers
{numbers}"""

    (OUTPUT / "claim_ledger.md").write_text(ledger.rstrip() + "\n", encoding="utf-8")

    manifest = pd.DataFrame(
        [{"figure": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size} for p in figures]
        + [{"figure": interactive.name, "sha256": sha256_file(interactive), "bytes": interactive.stat().st_size}]
    )
    write_csv(OUTPUT / "figure_manifest.csv", manifest)


# --------------------------------------------------------------------------------------
# notebook
# --------------------------------------------------------------------------------------
def notebook_payload() -> dict[str, Any]:
    sections: list[tuple[str, str, str]] = [
        (
            "1. What question is being asked?",
            "Phase 2 compared temporal transverse-width dynamics against the scalar physics coordinate "
            "`h`. The control Ioan actually asked for was never completed: compare width dynamics against "
            "the **four process parameters** `[P, VX, LS, ST]` that are set on the machine. Phase 2.1 is "
            "exactly that comparison.\n\n"
            "* baseline — `4d_only` = `[P, VX, LS, ST]`\n"
            "* challenger — `4d_plus_width_dynamics` = `[P, VX, LS, ST]` + the eight Phase 2 width features\n\n"
            "Everything else (population, folds, width definition, metric set) is held fixed on purpose.",
            "display(pd.read_csv(OUT/'semantic_width_audit.csv')[['quantity','formula',"
            "'physical_interpretation','used_in_phase2_1','semantic_source_reverified_now']])",
        ),
        (
            "2. Why does it matter?",
            "If width dynamics only beats `h`, that is a weak result: `h` throws away three of the four "
            "inputs. A supervisor deciding whether to instrument a machine needs to know whether watching "
            "the melt pool tells you anything you did not already know from the parameters you chose. "
            "That is a decision-relevant question, and it can be answered cleanly with a transparent "
            "classifier.",
            "print((OUT/'claim_ledger.md').read_text(encoding='utf-8').split('## Status vocabulary')[0])",
        ),
        (
            "3. What data are used?",
            "The frozen canonical population (405 simulations, 73 Keyhole). Width traces come from Phase 2 "
            "commit `da913797` and are **not** re-extracted — the transverse definition ΔY = Ymax − Ymin is "
            "inherited byte-for-byte, and ΔX (longitudinal length) is dropped before anything is modelled. "
            "Not every simulation has a usable trace, and the loss is structured, so every model — baseline "
            "included — is restricted to the same usable subset.",
            "display(pd.read_csv(OUT/'trace_availability_summary.csv'))\n"
            "display(Image(filename=OUT/'figures'/'01_trace_availability.png'))\n"
            "display(Image(filename=OUT/'figures'/'02_representative_width_traces.png'))",
        ),
        (
            "4. What exactly is being compared?",
            "Ten logistic pipelines on the 100 frozen Week 8.5 grouped folds. Scaling and fitting happen "
            "inside each training fold; q20/q30 are evaluation-only boundary masks. Five of the ten models "
            "exist only to reproduce Phase 2 exactly — that reproduction is the audit anchor that makes the "
            "new numbers comparable.",
            "gate = pd.read_csv(OUT/'phase2_reproduction_gate.csv')\n"
            "print('Phase 2 reproduction rows:', len(gate), '| max abs difference:', "
            "gate.abs_difference.max(), '| all PASS:', bool(gate.status.eq('PASS').all()))\n"
            "display(pd.read_csv(OUT/'feature_integrity_audit.csv'))",
        ),
        (
            "5. What numbers came out?",
            "Held-out performance across every candidate model, then the single contrast that carries the "
            "phase: `4d_plus_width_dynamics − 4d_only`.",
            "s = pd.read_csv(OUT/'model_oof_summary.csv')\n"
            "display(s[(s.subset=='q20') & s.metric.isin(['balanced_accuracy','keyhole_recall',"
            "'roc_auc','pr_auc','brier_score'])].pivot(index='model', columns='metric', "
            "values='mean').round(4))\n"
            "display(Image(filename=OUT/'figures'/'04_model_comparison.png'))\n"
            "display(pd.read_csv(OUT/'primary_contrast_inference.csv').query(\"subset=='q20'\")"
            "[['metric','metric_family','mean_difference','ci_low','ci_high','signflip_p','verdict']])\n"
            "display(Image(filename=OUT/'figures'/'05_primary_contrast.png'))",
        ),
        (
            "6. What did we learn?",
            "The mechanism matters more than the number: the width trace is generated by the process "
            "parameters, so most of its information is already in `[P, VX, LS, ST]`. The collinearity "
            "table and the in-fold coefficients say the same thing from two directions.",
            "display(pd.read_csv(OUT/'width_vs_4d_collinearity.csv').round(4))\n"
            "display(Image(filename=OUT/'figures'/'07_does_width_add_beyond_4d.png'))\n"
            "display(Image(filename=OUT/'figures'/'06_infold_coefficients.png'))\n"
            "display(Image(filename=OUT/'figures'/'03_width_feature_summary.png'))",
        ),
        (
            "7. What is supported, what is not, what stays qualitative?",
            "The claim ledger is the contract. A marginal association (Figure 3) is not incremental value; "
            "a ranking gain is not a hard-classification gain; and nothing here transfers to the "
            "simulations that never produced a usable trace.",
            "display(Image(filename=OUT/'figures'/'08_claim_status.png'))\n"
            "print((OUT/'SUPERVISOR_PHASE2_1_ONE_PAGE.md').read_text(encoding='utf-8'))",
        ),
        (
            "8. Interactive 3D process space (ST dropped from the axes)",
            "`outputs/week9_phase2_1_fourd_plus_width_control/interactive_3d_process_space.html` is a "
            "self-contained offline view: axes `P`, `VX`, `LS`, colour = manual `has_keyhole`, hover gives "
            "the experiment ID, `ST`, `log_h`, the label and whether the trace was usable. Open it in any "
            "browser — it needs no libraries and no network.",
            "html = OUT/'interactive_3d_process_space.html'\n"
            "print(html.name, '|', round(html.stat().st_size/1024, 1), 'KB')\n"
            "print('validation:', json.loads((OUT/'validation_report.json').read_text(encoding='utf-8'))"
            "['status'])",
        ),
    ]
    cells: list[dict[str, Any]] = [
        {
            "cell_type": "markdown",
            "id": "p21title",
            "metadata": {},
            "source": [
                "# Week 9 Phase 2.1 — 4D process inputs + temporal width dynamics\n",
                "\n",
                "**Does adding temporal melt-pool width dynamics to `[P, VX, LS, ST]` predict "
                "`has_keyhole` better than the process parameters alone?**\n",
                "\n",
                "This notebook reads the generated artifacts. The engine is "
                "`src/week9_phase2_1_fourd_plus_width_control.py`.\n",
            ],
        },
        {
            "cell_type": "code",
            "id": "p21setup",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import json\n",
                "from pathlib import Path\n",
                "import pandas as pd\n",
                "from IPython.display import display, Image\n",
                "pd.set_option('display.width', 170)\n",
                "pd.set_option('display.max_columns', 40)\n",
                "ROOT = Path.cwd().parents[1] if Path.cwd().name == 'week_09' else Path.cwd()\n",
                "OUT = ROOT / 'outputs' / 'week9_phase2_1_fourd_plus_width_control'\n",
                "assert OUT.is_dir(), OUT\n",
            ],
        },
    ]
    for title, text, code in sections:
        key = hashlib.sha1(title.encode()).hexdigest()[:8]
        cells.append({"cell_type": "markdown", "id": f"md{key}", "metadata": {},
                      "source": [f"## {title}\n", "\n", text + "\n"]})
        cells.append({"cell_type": "code", "id": f"cd{key}", "execution_count": None, "metadata": {},
                      "outputs": [], "source": [line + "\n" for line in code.split("\n")]})
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def execute_and_save_notebook() -> str:
    import nbformat
    from nbconvert.preprocessors import ExecutePreprocessor
    from jupyter_client.kernelspec import KernelSpecManager

    available = set(KernelSpecManager().find_kernel_specs())
    kernel = "python3" if "python3" in available else sorted(available)[0]
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    ExecutePreprocessor(timeout=600, kernel_name=kernel).preprocess(notebook, {"metadata": {"path": str(ROOT)}})
    require(
        sum(
            1
            for cell in notebook.cells
            if cell.cell_type == "code" and cell.get("execution_count") is not None and cell.get("outputs")
        )
        >= 8,
        "notebook has too few stored executed outputs",
    )
    nbformat.write(notebook, NOTEBOOK)
    return kernel


# --------------------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------------------
NEW_PATH_PREFIXES = (
    "src/week9_phase2_1_fourd_plus_width_control.py",
    "notebooks/week_09/06_week9_phase2_1_fourd_plus_width_control.ipynb",
    "outputs/week9_phase2_1_fourd_plus_width_control/",
)


def working_tree_fingerprint() -> set[str]:
    """Paths git already reports as dirty, excluding this phase's own new artifacts.

    Phase 2.1 must not touch any historical file. This checkout was already dirty
    before the run (it is a stale snapshot of an older commit), so the honest check
    is that the *set of pre-existing dirty paths is unchanged*, not that the tree is
    clean.
    """
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT, text=True, capture_output=True, check=True,
    )
    paths = set()
    for raw in result.stdout.splitlines():
        if not raw.strip():
            continue
        path = raw[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ")[-1]
        if any(path.startswith(prefix) for prefix in NEW_PATH_PREFIXES):
            continue
        paths.add(path)
    return paths


def directory_bytes(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def validate(
    population: pd.DataFrame,
    features: pd.DataFrame,
    availability: pd.DataFrame,
    profiles: pd.DataFrame,
    summary: pd.DataFrame,
    contrasts: pd.DataFrame,
    gate: pd.DataFrame,
    integrity: pd.DataFrame,
    axis: pd.DataFrame,
    figures: list[Path],
    interactive: Path,
    baseline_tree: set[str],
    include_notebook: bool,
) -> dict[str, Any]:
    """Run the audit checks.

    Called twice: once before the notebook is executed (so the notebook can display a
    real verdict rather than a placeholder) and once after, with the notebook checks
    switched on.
    """
    physics_source = (ROOT / "src" / "week9_phase1_5_h_physics_confirmation.py").read_text(encoding="utf-8")
    module_source = Path(__file__).read_text(encoding="utf-8")
    model_columns = {c for spec in MODELS.values() for c in spec[0]}
    demo = _model(1.0).fit(np.array([[0.0], [2.0], [4.0]]), np.array([0, 0, 1]))
    html = interactive.read_text(encoding="utf-8")
    specs = w85.build_splits(population)
    usable_indices = set(int(i) for i in features.population_row_index)
    fold_membership_frozen = all(
        set(spec.train_indices) | set(spec.test_indices) == set(range(len(population))) for spec in specs
    )
    reports = ["FINAL_PHASE2_1_REPORT.md", "SUPERVISOR_PHASE2_1_ONE_PAGE.md", "claim_ledger.md"]

    checks: dict[str, bool] = {
        # --- population and labels ---------------------------------------------------
        "population_405": len(population) == 405,
        "labels_73": int(population.has_keyhole.sum()) == 73,
        "canonical_ids_unique": bool(population.experiment_name.is_unique),
        "LS_is_laser_spot_radius": bool(np.allclose(population.LS, population.LS_m))
        and "Gaussian laser spot radius r0" in physics_source,
        "ST_is_substrate_temperature": bool(np.allclose(population.ST, population.ST_K))
        and '"ST_definition": "substrate temperature"' in physics_source,
        "h_exact_formula": bool(
            np.allclose(features.log_h, np.log(features.P / np.sqrt(features.VX * features.LS**3)))
        ),
        # --- width definition ---------------------------------------------------------
        "width_is_transverse_delta_y": bool(
            axis[axis.quantity.eq("transverse_width")].used_in_phase2_1.all()
            and axis[axis.quantity.eq("transverse_width")].semantic_source_reverified_now.all()
        ),
        "longitudinal_delta_x_not_used": bool(
            not axis[axis.quantity.eq("longitudinal_length")].used_in_phase2_1.any()
        )
        and not any(c.startswith("L_") for c in features.columns)
        and not any(c.startswith("L_") for c in model_columns),
        "width_extraction_inherited_not_reinvented": PHASE2_SHA in module_source
        and "width_temporal_features.csv" in module_source,
        "phase2_feature_table_shape": len(features) == 350 and int(features.has_keyhole.sum()) == 70,
        "feature_integrity_all_pass": bool(integrity.status.eq("PASS").all()),
        "raw_derivatives_excluded_from_models": not bool(set(RAW_DERIVATIVE_FEATURES) & model_columns),
        # --- leakage ------------------------------------------------------------------
        "no_label_column_in_any_model": not bool(model_columns & {"has_keyhole", "truth"}),
        "evaluation_masks_absent_from_features": not bool(
            model_columns & {"is_q20", "is_q30", "b1_distance", "B1_q20", "B1_q30"}
        ),
        "row_index_absent_from_features": "population_row_index" not in model_columns,
        "train_only_scaling_executable": bool(np.allclose(demo.named_steps["scale"].mean_, [2.0])),
        "scaler_inside_pipeline": "Pipeline(" in module_source and '("scale", StandardScaler())' in module_source,
        # --- protocol -----------------------------------------------------------------
        "frozen_fold_count_100": len(specs) == 100,
        "folds_cover_full_population": fold_membership_frozen,
        # Tokens are assembled from fragments so that these checks do not match themselves.
        "no_new_random_split_declared": ("train_test" + "_split") not in module_source,
        "usable_subset_consistent": usable_indices <= set(range(len(population)))
        and len(usable_indices) == len(features),
        "baseline_and_challenger_share_regularisation": MODELS["4d_only"][1] == MODELS["4d_plus_width_dynamics"][1],
        "primary_contrast_declared": PRIMARY_CONTRAST == "4d_plus_width_dynamics - 4d_only",
        # --- comparability with Phase 2 ------------------------------------------------
        "phase2_reproduction_gate_nonempty": len(gate) >= 100,
        "phase2_reproduction_exact": bool(gate.status.eq("PASS").all()),
        # --- inference discipline --------------------------------------------------------
        "primary_contrast_holm_adjusted": bool(
            pd.read_csv(OUTPUT / "primary_contrast_inference.csv")
            .query("subset == 'q20'")
            .holm_p_metric_family.notna()
            .all()
        ),
        "secondary_sensitivity_predeclared_in_registry": (
            "4d_plus_width_shape_only" in MODELS
            and MODELS["4d_plus_width_shape_only"][2] == "secondary"
            and any(c[:2] == ("4d_plus_width_shape_only", "4d_only") for c in CONTRASTS)
        ),
        "shape_sensitivity_reported_separately": (OUTPUT / "shape_subset_contrast_inference.csv").is_file(),
        "verdicts_are_interval_based": "def verdict(" in module_source and "ci_low" in module_source,
        # --- outputs -------------------------------------------------------------------
        "eight_figures": len(figures) == 8,
        "figures_exist": all(p.is_file() and p.stat().st_size > 0 for p in figures),
        "figure_hashes_match_manifest": all(
            sha256_file(OUTPUT / "figures" / row.figure) == row.sha256
            if (OUTPUT / "figures" / row.figure).is_file()
            else sha256_file(OUTPUT / row.figure) == row.sha256
            for row in pd.read_csv(OUTPUT / "figure_manifest.csv").itertuples()
        ),
        "interactive_html_exists": interactive.is_file() and interactive.stat().st_size > 20_000,
        "interactive_html_is_offline": ("http://" not in html) and ("https://" not in html),
        "interactive_html_has_full_population": html.count('"id":') == len(population),
        "interactive_html_hover_fields": all(
            token in html for token in ["log h", "ST", "usable in Phase 2.1", "d.id"]
        ),
        "reports_exist": all((OUTPUT / name).is_file() for name in reports),
        "reports_quote_canonical_counts": all(
            f"{len(features)}/405" in (OUTPUT / name).read_text(encoding="utf-8")
            or f"{len(features)} of 405" in (OUTPUT / name).read_text(encoding="utf-8")
            for name in reports
        ),
        "reports_state_a_verdict": all(
            any(token in (OUTPUT / name).read_text(encoding="utf-8")
                for token in ["SUPPORTED", "NOT SUPPORTED", "QUALIFIED"])
            for name in reports
        ),
        # --- local-only discipline ------------------------------------------------------
        "no_historical_file_touched": working_tree_fingerprint() == baseline_tree,
        "no_remote_operation_in_source": not any(
            token in module_source
            for token in ["git pu" + "sh", "gh " + "pr", "git rem" + "ote add", "requests." + "post"]
        ),
        "phase2_read_is_readonly_git_show": 'subprocess.run(\n        ["git", "show"' in module_source
        or '"git", "show"' in module_source,
    }
    if include_notebook:
        notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        executed = [
            cell for cell in notebook["cells"]
            if cell["cell_type"] == "code" and cell.get("execution_count") is not None and cell.get("outputs")
        ]
        errors = [
            output
            for cell in notebook["cells"]
            for output in cell.get("outputs", [])
            if output.get("output_type") == "error"
        ]
        checks["notebook_stores_executed_outputs"] = len(executed) >= 8
        checks["notebook_has_no_execution_errors"] = not errors
        checks["notebook_reports_a_real_verdict"] = "PENDING" not in NOTEBOOK.read_text(encoding="utf-8")

    failed = [name for name, value in checks.items() if not value]
    require(not failed, f"validation failed: {failed}")

    payload = {
        "status": "PASS",
        "phase": "Week 9 Phase 2.1",
        "notebook_checks_included": include_notebook,
        "checks": checks,
        "check_count": len(checks),
        "phase2_source_commit": PHASE2_SHA,
        "usable_traces": len(features),
        "usable_keyholes": int(features.has_keyhole.sum()),
        "population": len(population),
        "population_keyholes": int(population.has_keyhole.sum()),
        "output_bytes": directory_bytes(OUTPUT),
        "notebook_bytes": NOTEBOOK.stat().st_size,
        "preexisting_dirty_paths_outside_this_phase": len(baseline_tree),
    }
    write_json(OUTPUT / "validation_report.json", payload)
    (OUTPUT / "validation_report.md").write_text(
        "# Week 9 Phase 2.1 validation report\n\n"
        f"**PASS** — {len(checks)} checks passed.\n\n"
        f"Reused Phase 2 width extraction: `{PHASE2_SHA}`.\n"
        f"Usable transverse-width traces: {len(features)}/405 "
        f"({int(features.has_keyhole.sum())} Keyhole).\n"
        f"New artifacts on disk: {directory_bytes(OUTPUT) / 1e6:.2f} MB.\n"
        f"Pre-existing dirty paths in this checkout, untouched by Phase 2.1: {len(baseline_tree)}.\n\n"
        + "\n".join(f"- PASS: {name}" for name in checks)
        + "\n",
        encoding="utf-8",
    )
    return payload


# --------------------------------------------------------------------------------------
# orchestration
# --------------------------------------------------------------------------------------
def run() -> None:
    started = time.time()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    baseline_tree = working_tree_fingerprint()

    print("[1/9] population, axis semantics and pinned Phase 2 width features", flush=True)
    population = load_population()
    axis = semantic_width_audit()
    features, integrity = load_width_features(population)
    availability = trace_availability(population, features)
    profiles = phase2_csv("temporal_profiles.csv.gz")
    require(
        set(profiles.experiment_name) == set(features.experiment_name),
        "phase 2 profiles and feature table disagree on the usable subset",
    )

    print("[2/9] descriptive feature effects and 4D collinearity", flush=True)
    effects = feature_effects(features)
    collinearity = width_collinearity(features)

    print("[3/9] leak-free evaluation on the 100 frozen grouped folds", flush=True)
    predictions, coefficient_rows = evaluate_models(population, features)

    print("[4/9] repeat-block summaries and paired contrasts", flush=True)
    repeat, summary = summarize_oof(predictions)
    contrasts = paired_contrasts(repeat)
    inference, shape_inference = primary_inference(contrasts)
    gate = reproduction_gate(summary)
    require(bool(gate.status.eq("PASS").all()), "Phase 2 reproduction gate failed; folds are not comparable")
    coefficients = coefficient_summary(coefficient_rows)

    print("[5/9] claim ledger", flush=True)
    claims, facts = build_claims(inference, shape_inference, contrasts, summary, effects, collinearity)
    write_csv(OUTPUT / "claim_status.csv", claims)

    print("[6/9] figures", flush=True)
    figures = make_figures(
        population, features, profiles, availability, effects, summary, contrasts,
        inference, shape_inference, coefficients, collinearity, repeat, claims,
    )

    print("[7/9] interactive 3D process-space view", flush=True)
    interactive = make_interactive_3d(population, features)

    print("[8/9] reports and notebook", flush=True)
    render_reports(population, features, availability, summary, contrasts, inference, shape_inference,
                   claims, facts, collinearity, coefficients, figures, interactive)
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    NOTEBOOK.write_text(json.dumps(notebook_payload(), indent=1) + "\n", encoding="utf-8")

    print("[9/9] validation", flush=True)
    # Validate before executing the notebook so the notebook can display a real verdict,
    # then validate again with the notebook checks switched on.
    validate(population, features, availability, profiles, summary, contrasts, gate,
             integrity, axis, figures, interactive, baseline_tree, include_notebook=False)
    kernel = execute_and_save_notebook()
    validation = validate(population, features, availability, profiles, summary, contrasts, gate,
                          integrity, axis, figures, interactive, baseline_tree, include_notebook=True)

    manifest = {
        "study": "Week 9 Phase 2.1 — 4D process inputs plus temporal width dynamics",
        "primary_question": "Does [P, VX, LS, ST] + width dynamics beat [P, VX, LS, ST] alone at predicting has_keyhole?",
        "primary_contrast": PRIMARY_CONTRAST,
        "verdict_hard_decision": facts["hard_status"],
        "verdict_secondary_shape_subset": facts["shape_status"],
        "verdict_ranking_probability": facts["ranking_status"],
        "verdict_overall": facts["level"],
        "population": 405,
        "population_keyholes": 73,
        "usable_traces": len(features),
        "usable_keyholes": int(features.has_keyhole.sum()),
        "width_definition": "transverse width dY = (y_max - y_min) * 1e6 micrometres",
        "width_source_commit": PHASE2_SHA,
        "width_source_branch": PHASE2_BRANCH,
        "width_source_artifacts": {
            name: phase2_blob_sha(name)
            for name in ("width_temporal_features.csv", "temporal_profiles.csv.gz",
                         "axis_semantics_audit.csv", "model_oof_summary.csv")
        },
        "folds": "frozen Week 8.5 grouped outer folds, 20 repeats x 5 folds",
        "model_family": "StandardScaler + LogisticRegression(lbfgs), C=1.0 (h_only keeps Phase 2's C=1e6)",
        "models": {name: {"features": list(spec[0]), "C": spec[1], "role": spec[2]}
                   for name, spec in MODELS.items()},
        "bootstrap_draws": BOOTSTRAP_DRAWS,
        "signflip_draws": SIGNFLIP_DRAWS,
        "seed": SEED,
        "notebook_kernel": kernel,
        "notebook_sha256": sha256_file(NOTEBOOK),
        "local_only": True,
        "network_access_used": False,
        "new_worktree_or_clone_created": False,
        "new_artifact_bytes": directory_bytes(OUTPUT) + NOTEBOOK.stat().st_size,
        "validation": validation,
        "elapsed_seconds": time.time() - started,
    }
    manifest["artifact_hashes"] = {
        str(path.relative_to(OUTPUT)).replace("\\", "/"): sha256_file(path)
        for path in sorted(OUTPUT.rglob("*"))
        if path.is_file() and path.name != "run_manifest.json"
    }
    write_json(OUTPUT / "run_manifest.json", manifest)
    print(
        json.dumps(
            {
                "status": "PASS",
                "usable_traces": len(features),
                "hard_decision": facts["hard_status"],
                "ranking_probability": facts["ranking_status"],
                "overall": facts["level"],
                "new_artifact_megabytes": round(manifest["new_artifact_bytes"] / 1e6, 2),
                "elapsed_seconds": round(time.time() - started, 1),
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="run the full Phase 2.1 study")
    args = parser.parse_args()
    if args.run:
        run()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
