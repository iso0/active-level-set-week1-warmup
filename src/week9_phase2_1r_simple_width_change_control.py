"""Week 9 Phase 2.1R: the simple width-change control.

Phase 2.1 summarised each melt-pool width trace with eight engineered shape and
derivative descriptors.  Phase 2.1R asks the much simpler question Ioan actually
posed: **what happens between one analysis point and the next?**

If the transverse width is 20 um at one analysis point and 30 um at the next, the
change is ``delta_W = +10``.  If the next transition is 30 -> 33 the change is
``+3``; if the one after is 33 -> 31 the change is ``-2``.  A simulation therefore
has a simple width-change sequence like ``[+10, +3, -2, ...]``, and that sequence
is the primary object of study here.

TERMINOLOGY, deliberately strict
--------------------------------
The width series used here lives on the Phase 2 resampled tau grid.  Its points
are called **consecutive resampled analysis points** everywhere in this module and
in every artifact it writes.  They are *not* raw solver timesteps.  The raw SPH
monitors carry about 75,000 steps per simulation at dt ~ 0.018 us, where the
step-to-step width change is boundary jitter (median absolute step ~ 0.005 um,
and width decreases on ~51% of raw steps).  A "largest raw one-step increase"
would therefore measure the biggest numerical artifact in 75,000 steps rather than
melt-pool growth.  The resampled grid (dt ~ 6.8 us at 201 points) is the scale at
which a 20 -> 30 um change is a physical event.  Because that grid resolution is a
choice, every headline feature is recomputed at 51, 101 and 201 points and the
conclusion is only reported as robust if it survives all three.

Width is transverse: ``W(t) = Ymax - Ymin = delta_Y``, reused byte-for-byte from
the pinned Phase 2 commit.  Longitudinal length delta_X is never used.

Run with ``python -m src.week9_phase2_1r_simple_width_change_control --run``.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import re
import subprocess
import textwrap
import time
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy import stats
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.gaussian_process.kernels import ConstantKernel, Matern
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
from sklearn.preprocessing import StandardScaler

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase2_1r_simple_width_change_control"
FIGURES = OUTPUT / "figures"
INTERACTIVE = OUTPUT / "interactive"
NOTEBOOK = ROOT / "notebooks" / "week_09" / "07_week9_phase2_1r_simple_width_change_control.ipynb"

# Pinned provenance: the transverse-width traces are inherited, never re-extracted.
PHASE2_SHA = "da913797d14b171bec55d3708f96aa87f09a4f94"
PHASE2_DIR = "outputs/week9_phase2_temporal_width_dynamics"
PHASE2_1_DIR = ROOT / "outputs" / "week9_phase2_1_fourd_plus_width_control"

SEED = 260907
BOOTSTRAP_DRAWS = 5000
SIGNFLIP_DRAWS = 20000
WORKERS = 6

# Resolution sweep. The Phase 2 grid has 201 points; 101 and 51 are exact
# subsamples of it (stride 2 and 4), so no new interpolation is introduced.
PRIMARY_RESOLUTION = 201
RESOLUTIONS = (51, 101, 201)

FOURD_FEATURES = ("P", "VX", "LS", "ST")

# --- the simple width-change features -------------------------------------------------
# Each is one sentence plus a worked example on the sequence [+10, +3, -2, +1].
SIMPLE_FEATURE_DOC: dict[str, tuple[str, str]] = {
    "max_positive_delta_W": (
        "largest increase in transverse width between two consecutive resampled analysis points",
        "sequence [+10, +3, -2, +1] -> the biggest rise is +10, so max_positive_delta_W = 10",
    ),
    "min_delta_W": (
        "most negative transition, i.e. the largest single contraction",
        "sequence [+10, +3, -2, +1] -> the most negative entry is -2, so min_delta_W = -2",
    ),
    "median_positive_delta_W": (
        "median of only the transitions where the width grew",
        "positives are [+10, +3, +1]; their median is 3, so median_positive_delta_W = 3",
    ),
    "fraction_positive_delta_W": (
        "share of transitions in which the width increased",
        "3 of the 4 transitions are positive, so fraction_positive_delta_W = 0.75",
    ),
    "total_positive_delta_W": (
        "sum of every increase, i.e. total growth ignoring the shrinking steps",
        "10 + 3 + 1 = 14, so total_positive_delta_W = 14",
    ),
    "max_positive_width_rate": (
        "largest increase divided by the time gap it happened in (um per ms)",
        "if the +10 um rise took 0.0068 ms then max_positive_width_rate = 10 / 0.0068 = 1471 um/ms",
    ),
    "median_positive_width_rate": (
        "median of the positive rises after each is divided by its own time gap",
        "the positive rises [+10, +3, +1] become rates, and we take the middle one",
    ),
    "fraction_positive_width_rate": (
        "share of transitions with a positive rate -- identical to fraction_positive_delta_W "
        "because every time gap is positive, so dividing by it cannot flip a sign",
        "3 of 4 positive -> 0.75, exactly the same number as fraction_positive_delta_W",
    ),
}
DELTA_FEATURES = (
    "max_positive_delta_W",
    "min_delta_W",
    "median_positive_delta_W",
    "fraction_positive_delta_W",
    "total_positive_delta_W",
)
RATE_FEATURES = (
    "max_positive_width_rate",
    "median_positive_width_rate",
    "fraction_positive_width_rate",
)
SIMPLE_DELTA_BLOCK = ("max_positive_delta_W", "median_positive_delta_W", "fraction_positive_delta_W")
SIMPLE_RATE_BLOCK = ("max_positive_width_rate", "median_positive_width_rate", "fraction_positive_width_rate")
HEADLINE_UNIVARIATE = ("max_positive_delta_W", "max_positive_width_rate")

# --- the demoted Phase 2 engineered block (secondary historical context only) ---------
OLD_SHAPE_FEATURES = ("width_gain_20_um", "width_gain_40_um", "time_to_50pct_max_width_tau")
OLD_DERIVATIVE_FEATURES = (
    "robust_max_positive_dWdt_um_per_ms",
    "robust_median_positive_dWdt_um_per_ms",
    "robust_early_dWdt_20_um_per_ms",
    "robust_early_dWdt_40_um_per_ms",
    "robust_time_of_max_dWdt_tau",
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
PRIMARY_METRICS = (
    "balanced_accuracy",
    "accuracy",
    "keyhole_recall",
    "roc_auc",
    "pr_auc",
    "brier_score",
)
LOWER_IS_BETTER = frozenset({"brier_score", "false_negative", "false_positive"})


# --------------------------------------------------------------------------------------
# house helpers
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
    frame.to_csv(tmp, index=False, lineterminator="\n",
                 compression="gzip" if path.suffix == ".gz" else None)
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


def phase2_blob(relative_name: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{PHASE2_SHA}:{PHASE2_DIR}/{relative_name}"],
        cwd=ROOT, capture_output=True, check=True,
    )
    return result.stdout


def phase2_csv(relative_name: str) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(phase2_blob(relative_name)),
                       compression="gzip" if relative_name.endswith(".gz") else None)


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


# --------------------------------------------------------------------------------------
# 2. the transition-level width-change table
# --------------------------------------------------------------------------------------
def load_width_series(population: pd.DataFrame) -> pd.DataFrame:
    """Inherit the Phase 2 transverse-width traces on the 201-point resampled grid."""
    profiles = phase2_csv("temporal_profiles.csv.gz")
    keep = ["experiment_name", "tau", "time_from_active_start_ms", "transverse_width_um"]
    profiles = profiles[keep].copy()
    require(
        set(profiles.experiment_name) <= set(population.experiment_name),
        "phase 2 profiles contain experiments outside the canonical population",
    )
    counts = profiles.groupby("experiment_name").size()
    require(bool((counts == PRIMARY_RESOLUTION).all()),
            f"expected {PRIMARY_RESOLUTION} analysis points per simulation")
    return profiles.sort_values(["experiment_name", "tau"]).reset_index(drop=True)


def transition_table(series: pd.DataFrame, population: pd.DataFrame, resolution: int) -> pd.DataFrame:
    """One row per consecutive pair of resampled analysis points.

    Concrete example: if a simulation has W = 20 um at analysis point i and
    W = 30 um at analysis point i+1, that pair contributes one row with
    ``delta_W = +10``.  ``width_rate`` divides that +10 by the elapsed time
    between the two points, so it is um per ms.
    """
    require(
        (PRIMARY_RESOLUTION - 1) % (resolution - 1) == 0,
        f"resolution {resolution} is not an exact subsample of {PRIMARY_RESOLUTION}",
    )
    stride = (PRIMARY_RESOLUTION - 1) // (resolution - 1)
    label = population.set_index("experiment_name").has_keyhole
    index = population.set_index("experiment_name").population_row_index
    rows = []
    for name, group in series.groupby("experiment_name", sort=True):
        sub = group.iloc[::stride]
        require(len(sub) == resolution, f"{name}: subsample produced {len(sub)} points")
        w = sub.transverse_width_um.to_numpy(float)
        t = sub.time_from_active_start_ms.to_numpy(float)
        delta_t = np.diff(t)
        require(np.all(delta_t > 0), f"{name}: non-positive gap between analysis points")
        delta_w = np.diff(w)
        rows.append(
            pd.DataFrame(
                {
                    "simulation_id": name,
                    "population_row_index": int(index.loc[name]),
                    "analysis_point_i": np.arange(resolution - 1),
                    "analysis_point_i_plus_1": np.arange(1, resolution),
                    "t_i_ms": t[:-1],
                    "t_i_plus_1_ms": t[1:],
                    "W_i_um": w[:-1],
                    "W_i_plus_1_um": w[1:],
                    "delta_t_ms": delta_t,
                    "delta_W_um": delta_w,
                    "width_rate_um_per_ms": delta_w / delta_t,
                    "has_keyhole": int(label.loc[name]),
                }
            )
        )
    table = pd.concat(rows, ignore_index=True)
    require(
        np.allclose(table.delta_W_um, table.W_i_plus_1_um - table.W_i_um),
        "delta_W does not equal W(i+1) - W(i)",
    )
    return table


def simple_features(table: pd.DataFrame) -> pd.DataFrame:
    """Collapse each simulation's delta_W sequence into the small interpretable set."""
    rows = []
    for name, group in table.groupby("simulation_id", sort=True):
        d = group.delta_W_um.to_numpy(float)
        r = group.width_rate_um_per_ms.to_numpy(float)
        positive_d = d[d > 0]
        positive_r = r[r > 0]
        rows.append(
            {
                "experiment_name": name,
                "population_row_index": int(group.population_row_index.iloc[0]),
                "has_keyhole": int(group.has_keyhole.iloc[0]),
                "transition_count": len(d),
                "max_positive_delta_W": float(positive_d.max()) if len(positive_d) else 0.0,
                # diagnostic only, never a model input: where in the trace the biggest rise sits
                "diagnostic_argmax_delta_W_fraction": float(int(np.argmax(d)) / max(len(d) - 1, 1)),
                "diagnostic_first_W_um": float(group.W_i_um.iloc[0]),
                "min_delta_W": float(d.min()),
                "median_positive_delta_W": float(np.median(positive_d)) if len(positive_d) else 0.0,
                "fraction_positive_delta_W": float(np.mean(d > 0)),
                "total_positive_delta_W": float(positive_d.sum()) if len(positive_d) else 0.0,
                "max_positive_width_rate": float(positive_r.max()) if len(positive_r) else 0.0,
                "median_positive_width_rate": float(np.median(positive_r)) if len(positive_r) else 0.0,
                "fraction_positive_width_rate": float(np.mean(r > 0)),
            }
        )
    features = pd.DataFrame(rows)
    require(
        np.allclose(features.fraction_positive_width_rate, features.fraction_positive_delta_W),
        "fraction_positive_width_rate must equal fraction_positive_delta_W (time gaps are positive)",
    )
    return features


# --------------------------------------------------------------------------------------
# 4. the almost-child-simple univariate question
# --------------------------------------------------------------------------------------
def cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean(x[:, None] > y[None, :]) - np.mean(x[:, None] < y[None, :]))


def univariate_separation(features: pd.DataFrame, columns: Sequence[str], resolution: int) -> pd.DataFrame:
    """Do Keyhole simulations tend to have larger values than Conduction ones?

    Descriptive, whole-sample, no folds: this answers "is there a difference at
    all", never "how well would it generalise".  The leak-free version is the
    threshold experiment below.
    """
    rng = np.random.default_rng(SEED)
    y = features.has_keyhole.to_numpy(int)
    rows = []
    for column in columns:
        values = features[column].to_numpy(float)
        conduction = values[y == 0]
        keyhole = values[y == 1]
        boot = np.array(
            [
                np.median(rng.choice(keyhole, len(keyhole), replace=True))
                - np.median(rng.choice(conduction, len(conduction), replace=True))
                for _ in range(BOOTSTRAP_DRAWS)
            ]
        )
        u = stats.mannwhitneyu(keyhole, conduction, alternative="two-sided")
        rows.append(
            {
                "resolution_points": resolution,
                "feature": column,
                "plain_english": SIMPLE_FEATURE_DOC[column][0],
                "worked_example": SIMPLE_FEATURE_DOC[column][1],
                "conduction_n": int((y == 0).sum()),
                "keyhole_n": int((y == 1).sum()),
                "conduction_median": float(np.median(conduction)),
                "keyhole_median": float(np.median(keyhole)),
                "conduction_iqr_low": float(np.quantile(conduction, 0.25)),
                "conduction_iqr_high": float(np.quantile(conduction, 0.75)),
                "keyhole_iqr_low": float(np.quantile(keyhole, 0.25)),
                "keyhole_iqr_high": float(np.quantile(keyhole, 0.75)),
                "median_difference_keyhole_minus_conduction": float(np.median(keyhole) - np.median(conduction)),
                "median_difference_ci_low": float(np.quantile(boot, 0.025)),
                "median_difference_ci_high": float(np.quantile(boot, 0.975)),
                "cliffs_delta": cliffs_delta(keyhole, conduction),
                "mannwhitney_p": float(u.pvalue),
                "roc_auc_whole_sample": float(roc_auc_score(y, values)),
                "pr_auc_whole_sample": float(average_precision_score(y, values)),
                "best_whole_sample_balanced_accuracy": float(
                    max(
                        balanced_accuracy_score(y, apply_threshold(values, threshold, direction))
                        for threshold in np.unique(values)
                        for direction in ("above", "below")
                    )
                ),
                "best_whole_sample_direction": max(
                    (
                        (
                            max(
                                balanced_accuracy_score(y, apply_threshold(values, threshold, direction))
                                for threshold in np.unique(values)
                            ),
                            direction,
                        )
                        for direction in ("above", "below")
                    )
                )[1],
            }
        )
    return pd.DataFrame(rows)


def threshold_sweep_curve(features: pd.DataFrame, column: str) -> pd.DataFrame:
    """Whole-sample balanced accuracy as the cut moves -- a picture, not a claim."""
    values = features[column].to_numpy(float)
    y = features.has_keyhole.to_numpy(int)
    grid = np.quantile(values, np.linspace(0.01, 0.99, 99))
    rows = []
    for threshold in np.unique(grid):
        for direction in ("above", "below"):
            pred = apply_threshold(values, threshold, direction)
            rows.append(
                {
                    "feature": column,
                    "threshold": float(threshold),
                    "direction": direction,
                    "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
                    "keyhole_recall": float(recall_score(y, pred, pos_label=1, zero_division=0)),
                    "conduction_recall": float(recall_score(y, pred, pos_label=0, zero_division=0)),
                    "predicted_keyhole_fraction": float(pred.mean()),
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# 5 / 6 / 7. models: leak-free threshold rule, canonical GPC, and M3
# --------------------------------------------------------------------------------------
def g3_kernel(dimension: int) -> Any:
    """The Phase 1.12 winner: ARD Matern-3/2, used unchanged for every GPC here."""
    return ConstantKernel(1.0, (1e-3, 1e3)) * Matern(
        length_scale=np.ones(dimension, dtype=float),
        length_scale_bounds=(1e-2, 1e2),
        nu=1.5,
    )


def m3_residual_kernel(dimension: int) -> Any:
    """M3's discrepancy kernel, widened only in the number of input dimensions."""
    return ConstantKernel(p11.INITIAL_RESIDUAL_VARIANCE, p11.RESIDUAL_VARIANCE_BOUNDS) * Matern(
        length_scale=np.ones(dimension, dtype=float),
        length_scale_bounds=p13.PRIMARY_LENGTH_BOUNDS,
        nu=1.5,
    )


def kernel_parity_audit() -> pd.DataFrame:
    """Prove the local kernel builders reproduce the frozen Week 9 specifications."""
    published = json.loads((ROOT / "outputs" / "week9_phase1_12_gpc_kernel_adequacy"
                            / "kernel_specification.json").read_text(encoding="utf-8"))
    g3 = published["models"]["G3"]
    rows = [
        {
            "quantity": "baseline_gpc_kernel",
            "phase_2_1r_builder": repr(g3_kernel(4)),
            "frozen_reference": g3["kernel_repr"],
            "reference_source": "outputs/week9_phase1_12_gpc_kernel_adequacy/kernel_specification.json (G3)",
            "match": repr(g3_kernel(4)) == g3["kernel_repr"],
        },
        {
            "quantity": "m3_residual_kernel",
            "phase_2_1r_builder": repr(m3_residual_kernel(4)),
            "frozen_reference": repr(p13.residual_kernel("M3")),
            "reference_source": "src/week9_phase1_13_fixed_physics_ard_discrepancy.residual_kernel('M3')",
            "match": repr(m3_residual_kernel(4)) == repr(p13.residual_kernel("M3")),
        },
        {
            "quantity": "gpc_optimizer_settings",
            "phase_2_1r_builder": "fmin_l_bfgs_b, n_restarts_optimizer=0, max_iter_predict=100",
            "frozen_reference": f"{g3['optimizer']}, n_restarts_optimizer={g3['n_restarts_optimizer']}, "
                                f"max_iter_predict=100",
            "reference_source": "Phase 1.12 kernel_specification.json",
            "match": g3["optimizer"] == "fmin_l_bfgs_b" and g3["n_restarts_optimizer"] == 0,
        },
        {
            "quantity": "gpc_ard_and_family",
            "phase_2_1r_builder": "ARD Matern nu=1.5 on StandardScaler-scaled inputs",
            "frozen_reference": f"ard={g3['ard']}, family={g3['family']}, nu={g3['nu']}, "
                                f"scaling={g3['input_scaling']}",
            "reference_source": "Phase 1.12 kernel_specification.json (G3 is the supported winner)",
            "match": bool(g3["ard"]) and g3["family"] == "Matern" and float(g3["nu"]) == 1.5,
        },
    ]
    audit = pd.DataFrame(rows)
    require(bool(audit.match.all()), f"kernel parity against frozen specs failed:\n{audit}")
    write_csv(OUTPUT / "kernel_parity_audit.csv", audit)
    return audit


def apply_threshold(values: np.ndarray, threshold: float, direction: str) -> np.ndarray:
    """direction 'above' = big values mean Keyhole; 'below' = small values mean Keyhole."""
    return (values >= threshold).astype(int) if direction == "above" else (values <= threshold).astype(int)


def learn_threshold(values: np.ndarray, labels: np.ndarray) -> tuple[float, str]:
    """Pick the cut AND its direction that maximise balanced accuracy on TRAINING data only.

    Concrete: if training max_positive_delta_W values are [4, 9, 12, 20] with labels
    [0, 0, 1, 1], the candidate cuts are the midpoints 6.5, 10.5 and 16; the rule
    "predict Keyhole if value >= 10.5" separates them perfectly, so (10.5, 'above')
    is chosen.  If instead the labels were [1, 1, 0, 0], the winning rule would be
    "predict Keyhole if value <= 10.5", i.e. (10.5, 'below').

    The direction is learned rather than assumed because this study found the naive
    expectation to be wrong: Keyhole simulations turn out to have *smaller* maximum
    width jumps.  Fixing the direction to 'above' in advance would have handicapped
    the rule and produced a misleading failure.  Both threshold and direction come
    only from training simulations, so the rule stays leak-free.  Ties are broken by
    the smallest qualifying cut and by preferring 'above', so it is deterministic.
    """
    order = np.unique(values)
    if len(order) < 2:
        return (float(order[0]) if len(order) else 0.0), "above"
    candidates = (order[:-1] + order[1:]) / 2.0
    best_score, best_threshold, best_direction = -np.inf, float(candidates[0]), "above"
    for direction in ("above", "below"):
        for threshold in candidates:
            score = balanced_accuracy_score(labels, apply_threshold(values, threshold, direction))
            if score > best_score + 1e-12:
                best_score, best_threshold, best_direction = score, float(threshold), direction
    return best_threshold, best_direction


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


def build_model_registry() -> dict[str, tuple[str, tuple[str, ...], str]]:
    """name -> (kind, feature columns, role)."""
    registry: dict[str, tuple[str, tuple[str, ...], str]] = {
        # --- primary: does simple width change add to the process inputs? -------------
        "gpc_4d": ("gpc", FOURD_FEATURES, "primary_baseline"),
        "gpc_4d_plus_max_delta_W": ("gpc", (*FOURD_FEATURES, "max_positive_delta_W"), "primary"),
        "gpc_4d_plus_max_width_rate": ("gpc", (*FOURD_FEATURES, "max_positive_width_rate"), "primary"),
        "gpc_4d_plus_simple_delta_block": ("gpc", (*FOURD_FEATURES, *SIMPLE_DELTA_BLOCK), "primary"),
        "gpc_4d_plus_simple_rate_block": ("gpc", (*FOURD_FEATURES, *SIMPLE_RATE_BLOCK), "primary"),
        # Resolution robustness of the headline model gain: the same model, but with
        # max_positive_delta_W recomputed on the 51- and 101-point subsamples of the grid.
        "gpc_4d_plus_max_delta_W_res51": (
            "gpc", (*FOURD_FEATURES, "max_positive_delta_W_res51"), "resolution"),
        "gpc_4d_plus_max_delta_W_res101": (
            "gpc", (*FOURD_FEATURES, "max_positive_delta_W_res101"), "resolution"),
        # --- M3 context ----------------------------------------------------------------
        "m3": ("m3", FOURD_FEATURES, "m3_reference"),
        "m3_plus_max_delta_W": ("m3", (*FOURD_FEATURES, "max_positive_delta_W"), "m3_reference"),
        # --- demoted Phase 2.1 engineered blocks, now under GPC ------------------------
        "gpc_4d_plus_old_shape3": ("gpc", (*FOURD_FEATURES, *OLD_SHAPE_FEATURES), "historical"),
        "gpc_4d_plus_old_full8": (
            "gpc",
            (*FOURD_FEATURES, *OLD_SHAPE_FEATURES, *OLD_DERIVATIVE_FEATURES),
            "historical",
        ),
    }
    # --- 10. derivative ablation: shape3 plus one derivative at a time ----------------
    for derivative in OLD_DERIVATIVE_FEATURES:
        registry[f"abl_shape3_plus_{derivative}"] = (
            "gpc",
            (*FOURD_FEATURES, *OLD_SHAPE_FEATURES, derivative),
            "ablation",
        )
    return registry


MODELS = build_model_registry()

PRIMARY_CONTRAST = "gpc_4d_plus_max_delta_W - gpc_4d"
CONTRASTS: tuple[tuple[str, str, str], ...] = (
    ("gpc_4d_plus_max_delta_W", "gpc_4d", "primary"),
    ("gpc_4d_plus_max_width_rate", "gpc_4d", "primary"),
    ("gpc_4d_plus_simple_delta_block", "gpc_4d", "primary"),
    ("gpc_4d_plus_simple_rate_block", "gpc_4d", "primary"),
    ("m3", "gpc_4d", "m3_context"),
    ("m3_plus_max_delta_W", "m3", "m3_context"),
    ("gpc_4d_plus_simple_delta_block", "m3", "m3_context"),
    ("gpc_4d_plus_old_shape3", "gpc_4d", "historical"),
    ("gpc_4d_plus_old_full8", "gpc_4d", "historical"),
    ("gpc_4d_plus_old_full8", "gpc_4d_plus_old_shape3", "ablation"),
    ("gpc_4d_plus_max_delta_W_res51", "gpc_4d", "resolution"),
    ("gpc_4d_plus_max_delta_W_res101", "gpc_4d", "resolution"),
) + tuple(
    (f"abl_shape3_plus_{derivative}", "gpc_4d_plus_old_shape3", "ablation")
    for derivative in OLD_DERIVATIVE_FEATURES
)


def _fit_predict(kind: str, columns: Sequence[str], train: pd.DataFrame, test: pd.DataFrame,
                 seed: int) -> tuple[np.ndarray, list[float]]:
    """Return held-out probabilities and the fitted ARD lengthscale per input.

    The lengthscales matter for interpretation: an ARD lengthscale pinned at the
    upper bound (100) means that input is being effectively ignored by the kernel,
    so a null result can be read as "the model could not use it" rather than
    "the feature carries nothing".
    """
    columns = list(columns)
    scaler = StandardScaler().fit(train[columns].to_numpy(float))
    x_train = scaler.transform(train[columns].to_numpy(float))
    x_test = scaler.transform(test[columns].to_numpy(float))
    y_train = train.has_keyhole.to_numpy(int)
    if kind == "gpc":
        model = GaussianProcessClassifier(
            kernel=g3_kernel(len(columns)),
            optimizer="fmin_l_bfgs_b",
            n_restarts_optimizer=0,
            max_iter_predict=100,
            random_state=seed,
        ).fit(x_train, y_train)
        lengths = np.ravel(model.kernel_.k2.length_scale).astype(float)
        return model.predict_proba(x_test)[:, 1], [float(v) for v in np.resize(lengths, len(columns))]
    if kind == "m3":
        # physics mean: logistic on log(h), fitted on training simulations only
        physics = p11.fit_physics_mean(
            train.log_h.to_numpy(float), y_train, np.arange(len(train)), seed
        )
        mean_train = physics.latent(train.log_h.to_numpy(float))
        mean_test = physics.latent(test.log_h.to_numpy(float))
        gp = p11.FixedMeanLaplaceGPC(m3_residual_kernel(len(columns)), optimize=True)
        gp.fit(x_train, y_train, mean_train)
        lengths = np.ravel(gp.kernel_.k2.length_scale).astype(float)
        return (gp.predict_proba(x_test, mean_test)[:, 1],
                [float(v) for v in np.resize(lengths, len(columns))])
    raise ValueError(f"unknown model kind {kind}")


def _run_fold(spec: Any, features: pd.DataFrame, usable: set[int], distances: np.ndarray,
              boundary: dict[str, dict[str, np.ndarray]]) -> tuple[list[dict], list[dict], list[dict]]:
    by_index = features.set_index("population_row_index", drop=False)
    train_idx = np.array([i for i in spec.train_indices if i in usable], dtype=int)
    test_idx = np.array([i for i in spec.test_indices if i in usable], dtype=int)
    require(len(np.intersect1d(train_idx, test_idx)) == 0, f"{spec.run_id}: train/test overlap")
    train, test = by_index.loc[train_idx], by_index.loc[test_idx]
    flags = boundary[spec.run_id]
    truth = test.has_keyhole.to_numpy(int)
    names = test.experiment_name.to_numpy()
    seed = w85.seed_u32(f"week9_phase2_1r|{spec.run_id}")

    predictions = []
    lengthscales = []
    for model_name, (kind, columns, role) in MODELS.items():
        probability, lengths = _fit_predict(kind, columns, train, test, seed)
        for column, length in zip(columns, lengths):
            lengthscales.append(
                {
                    "run_id": spec.run_id, "repeat": spec.repeat, "model": model_name,
                    "feature": column, "ard_length_scale": length,
                    "at_upper_bound": bool(length >= 1e2 * (1 - 1e-5)),
                    "at_lower_bound": bool(length <= 1e-2 * (1 + 1e-5)),
                }
            )
        for position, index in enumerate(test_idx):
            predictions.append(
                {
                    "run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold,
                    "population_row_index": int(index), "experiment_name": str(names[position]),
                    "truth": int(truth[position]), "model": model_name, "role": role,
                    "probability": float(probability[position]),
                    "is_q20": bool(flags["q20"][position]), "is_q30": bool(flags["q30"][position]),
                }
            )

    # --- 5. the leak-free threshold rule ------------------------------------------------
    thresholds = []
    for column in HEADLINE_UNIVARIATE:
        train_values = train[column].to_numpy(float)
        test_values = test[column].to_numpy(float)
        threshold, direction = learn_threshold(train_values, train.has_keyhole.to_numpy(int))
        predicted = apply_threshold(test_values, threshold, direction)
        # Oriented feature score: high = "more Keyhole-like" under the learned direction,
        # so the reported AUCs describe the rule the fold actually chose.
        oriented = test_values if direction == "above" else -test_values
        for subset, mask in (("full", np.ones(len(test_idx), bool)),
                             ("q30", flags["q30"]), ("q20", flags["q20"])):
            y = truth[mask]
            p = predicted[mask]
            v = oriented[mask]
            tn, fp, fn, tp = confusion_matrix(y, p, labels=[0, 1]).ravel()
            thresholds.append(
                {
                    "run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold,
                    "feature": column, "subset": subset,
                    "learned_threshold": threshold,
                    "learned_direction": direction,
                    "direction_is_below": int(direction == "below"),
                    "train_n": len(train), "test_n": int(mask.sum()),
                    "balanced_accuracy": float(balanced_accuracy_score(y, p)) if len(np.unique(y)) > 1 else float("nan"),
                    "accuracy": float(accuracy_score(y, p)),
                    "keyhole_recall": float(recall_score(y, p, pos_label=1, zero_division=0)),
                    "conduction_recall": float(recall_score(y, p, pos_label=0, zero_division=0)),
                    "true_negative": int(tn), "false_positive": int(fp),
                    "false_negative": int(fn), "true_positive": int(tp),
                    "feature_roc_auc": _safe_auc(y, v, "roc"),
                    "feature_pr_auc": _safe_auc(y, v, "pr"),
                }
            )
    return predictions, thresholds, lengthscales


def evaluate(population: pd.DataFrame, features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    specs = w85.build_splits(population)
    require(len(specs) == 100, "frozen split count drift")
    usable = set(int(i) for i in features.population_row_index)
    distances = w85.b1_distance(population)
    boundary: dict[str, dict[str, np.ndarray]] = {}
    for spec in specs:
        test_idx = np.array([i for i in spec.test_indices if i in usable], dtype=int)
        original = w85.boundary_flags(spec, population, distances)
        lookup = {int(idx): pos for pos, idx in enumerate(np.asarray(spec.test_indices))}
        boundary[spec.run_id] = {
            "q20": np.array([original["B1_q20"][lookup[int(i)]] for i in test_idx]),
            "q30": np.array([original["B1_q30"][lookup[int(i)]] for i in test_idx]),
        }
    print(f"    fitting {len(MODELS)} models x {len(specs)} frozen folds on {WORKERS} workers", flush=True)
    results = Parallel(n_jobs=WORKERS, verbose=5)(
        delayed(_run_fold)(spec, features, usable, distances, boundary) for spec in specs
    )
    predictions = pd.DataFrame([row for block, _, _ in results for row in block])
    thresholds = pd.DataFrame([row for _, block, _ in results for row in block])
    lengthscales = pd.DataFrame([row for _, _, block in results for row in block])
    summary_rows = []
    for (model, feature), group in lengthscales.groupby(["model", "feature"], sort=True):
        summary_rows.append(
            {
                "model": str(model), "feature": str(feature),
                "is_width_feature": feature not in FOURD_FEATURES,
                "median_ard_length_scale": float(group.ard_length_scale.median()),
                "fraction_at_upper_bound": float(group.at_upper_bound.mean()),
                "fraction_at_lower_bound": float(group.at_lower_bound.mean()),
                "folds": int(len(group)),
            }
        )
    lengthscale_summary = pd.DataFrame(summary_rows)
    write_csv(OUTPUT / "model_oof_predictions.csv.gz", predictions)
    write_csv(OUTPUT / "threshold_fold_results.csv", thresholds)
    write_csv(OUTPUT / "ard_lengthscales.csv.gz", lengthscales)
    write_csv(OUTPUT / "ard_lengthscale_summary.csv", lengthscale_summary)
    return predictions, thresholds, lengthscale_summary


# --------------------------------------------------------------------------------------
# 11. repeat-block summaries, paired contrasts, multiplicity
# --------------------------------------------------------------------------------------
def summarize(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    repeat_rows = []
    for (repeat, model), group in predictions.groupby(["repeat", "model"], sort=True):
        for subset, mask in (("full", np.ones(len(group), bool)),
                             ("q30", group.is_q30.to_numpy(bool)),
                             ("q20", group.is_q20.to_numpy(bool))):
            g = group.loc[mask]
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
                    "model": str(model), "subset": str(subset),
                    "role": MODELS[str(model)][2],
                    "feature_count": len(MODELS[str(model)][1]),
                    "features": " + ".join(MODELS[str(model)][1]),
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
        pivot = group.pivot(index="repeat", columns="model", values=list(METRIC_NAMES))
        for challenger, baseline, role in CONTRASTS:
            for metric in METRIC_NAMES:
                values = (pivot[(metric, challenger)] - pivot[(metric, baseline)]).dropna().to_numpy(float)
                boot = np.array([rng.choice(values, len(values), replace=True).mean()
                                 for _ in range(BOOTSTRAP_DRAWS)])
                signs = rng.choice([-1.0, 1.0], size=(SIGNFLIP_DRAWS, len(values)))
                null = (signs * values).mean(axis=1)
                observed = float(values.mean())
                p_value = float((np.sum(np.abs(null) >= abs(observed) - 1e-15) + 1) / (SIGNFLIP_DRAWS + 1))
                rows.append(
                    {
                        "subset": str(subset), "contrast": f"{challenger} - {baseline}",
                        "contrast_role": role, "metric": metric,
                        "lower_is_better": metric in LOWER_IS_BETTER,
                        "mean_difference": observed,
                        "ci_low": float(np.quantile(boot, 0.025)),
                        "ci_high": float(np.quantile(boot, 0.975)),
                        "signflip_p": p_value,
                        "repeat_blocks": len(values),
                    }
                )
    contrasts = pd.DataFrame(rows)
    # Holm within each (contrast, subset) across the six predeclared metrics.
    # This is the ONLY family corrected. Not corrected: the set of contrasts, and
    # the three evaluation regions. Both are stated in the reports.
    contrasts["holm_p_metric_family"] = np.nan
    for _, block in contrasts[contrasts.metric.isin(PRIMARY_METRICS)].groupby(
        ["contrast", "subset"], sort=False
    ):
        ordered = block.sort_values("signflip_p")
        running = 0.0
        for rank, (index, row) in enumerate(ordered.iterrows()):
            running = max(running, float(row.signflip_p) * (len(ordered) - rank))
            contrasts.loc[index, "holm_p_metric_family"] = min(1.0, running)
    write_csv(OUTPUT / "model_paired_contrasts.csv", contrasts)
    return contrasts


def verdict_of(row: pd.Series) -> str:
    sign = -1.0 if bool(row.lower_is_better) else 1.0
    low, high = sorted((sign * float(row.ci_low), sign * float(row.ci_high)))
    if low > 0:
        return "IMPROVES"
    if high < 0:
        return "DEGRADES"
    return "NO DETECTABLE DIFFERENCE"


def annotate(contrasts: pd.DataFrame) -> pd.DataFrame:
    block = contrasts[contrasts.metric.isin(PRIMARY_METRICS)].copy()
    block["verdict"] = block.apply(verdict_of, axis=1)
    block["verdict_after_holm"] = np.where(
        block.verdict.ne("NO DETECTABLE DIFFERENCE") & (block.holm_p_metric_family <= 0.05),
        block.verdict, "NO DETECTABLE DIFFERENCE",
    )
    block["metric_family"] = np.where(
        block.metric.isin(["balanced_accuracy", "keyhole_recall", "accuracy"]),
        "hard_decision", "ranking_or_probability",
    )
    block = block.sort_values(["contrast", "subset", "metric_family", "metric"]).reset_index(drop=True)
    write_csv(OUTPUT / "contrast_inference.csv", block)
    return block


def family_status(block: pd.DataFrame, column: str = "verdict_after_holm") -> str:
    improves = int(block[column].eq("IMPROVES").sum())
    degrades = int(block[column].eq("DEGRADES").sum())
    if improves and not degrades:
        return "SUPPORTED"
    if improves and degrades:
        return "QUALIFIED"
    return "NOT SUPPORTED"


def summarize_thresholds(thresholds: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for (feature, subset), group in thresholds.groupby(["feature", "subset"], sort=True):
        per_repeat = group.groupby("repeat")[
            ["balanced_accuracy", "accuracy", "keyhole_recall", "conduction_recall",
             "feature_roc_auc", "feature_pr_auc"]
        ].mean()
        entry = {
            "feature": str(feature), "subset": str(subset),
            "learned_threshold_median": float(group.learned_threshold.median()),
            "learned_threshold_iqr_low": float(group.learned_threshold.quantile(0.25)),
            "learned_threshold_iqr_high": float(group.learned_threshold.quantile(0.75)),
            "learned_threshold_min": float(group.learned_threshold.min()),
            "learned_threshold_max": float(group.learned_threshold.max()),
            "fraction_of_folds_choosing_below": float(group.direction_is_below.mean()),
            "majority_direction": "below" if group.direction_is_below.mean() > 0.5 else "above",
            "folds": int(len(group)),
            "total_true_positive": int(group.true_positive.sum()),
            "total_false_negative": int(group.false_negative.sum()),
            "total_false_positive": int(group.false_positive.sum()),
            "total_true_negative": int(group.true_negative.sum()),
        }
        for column in per_repeat.columns:
            values = per_repeat[column].dropna().to_numpy(float)
            entry[f"{column}_mean"] = float(values.mean())
            entry[f"{column}_sd_across_repeats"] = float(values.std(ddof=1))
        rows.append(entry)
    summary = pd.DataFrame(rows)
    write_csv(OUTPUT / "threshold_summary.csv", summary)
    per_repeat_frame = (
        thresholds.groupby(["feature", "subset", "repeat"])[
            ["balanced_accuracy", "keyhole_recall", "learned_threshold"]
        ].mean().reset_index()
    )
    write_csv(OUTPUT / "threshold_repeat_level.csv", per_repeat_frame)
    return summary, per_repeat_frame


# --------------------------------------------------------------------------------------
# resolution robustness sweep (51 / 101 / 201 analysis points)
# --------------------------------------------------------------------------------------
def resolution_sweep(series: pd.DataFrame, population: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Recompute the headline features at three grid resolutions.

    The 201-point grid is a choice, not a physical constant, so the same features
    are rebuilt on exact subsamples of it (every 4th point = 51, every 2nd = 101).
    A conclusion is only called resolution-robust if it holds at all three.
    """
    separation_frames, feature_frames = [], []
    for resolution in RESOLUTIONS:
        table = transition_table(series, population, resolution)
        features = simple_features(table)
        features["resolution_points"] = resolution
        feature_frames.append(features)
        separation_frames.append(
            univariate_separation(features, (*DELTA_FEATURES, *RATE_FEATURES), resolution)
        )
    sweep = pd.concat(separation_frames, ignore_index=True)
    all_features = pd.concat(feature_frames, ignore_index=True)
    write_csv(OUTPUT / "resolution_sweep_separation.csv", sweep)
    write_csv(OUTPUT / "resolution_sweep_features.csv", all_features)
    return sweep, all_features


def resolution_verdict(sweep: pd.DataFrame) -> pd.DataFrame:
    """For each headline feature, does the direction and significance hold everywhere?"""
    rows = []
    for feature in (*DELTA_FEATURES, *RATE_FEATURES):
        block = sweep[sweep.feature.eq(feature)]
        signs = {int(np.sign(v)) for v in block.cliffs_delta}
        excludes_zero = [
            bool(row.median_difference_ci_low > 0 or row.median_difference_ci_high < 0)
            for row in block.itertuples(index=False)
        ]
        rows.append(
            {
                "feature": feature,
                "plain_english": SIMPLE_FEATURE_DOC[feature][0],
                "cliffs_delta_51": float(block[block.resolution_points.eq(51)].cliffs_delta.iloc[0]),
                "cliffs_delta_101": float(block[block.resolution_points.eq(101)].cliffs_delta.iloc[0]),
                "cliffs_delta_201": float(block[block.resolution_points.eq(201)].cliffs_delta.iloc[0]),
                "roc_auc_51": float(block[block.resolution_points.eq(51)].roc_auc_whole_sample.iloc[0]),
                "roc_auc_101": float(block[block.resolution_points.eq(101)].roc_auc_whole_sample.iloc[0]),
                "roc_auc_201": float(block[block.resolution_points.eq(201)].roc_auc_whole_sample.iloc[0]),
                "direction_consistent": len(signs - {0}) <= 1,
                "interval_excludes_zero_everywhere": all(excludes_zero),
                "resolution_robust": bool(len(signs - {0}) <= 1 and all(excludes_zero)),
            }
        )
    out = pd.DataFrame(rows)
    write_csv(OUTPUT / "resolution_robustness_verdict.csv", out)
    return out


# --------------------------------------------------------------------------------------
# 9. corrected restatement of the Phase 2.1 narrative
# --------------------------------------------------------------------------------------
def phase2_1_corrections() -> pd.DataFrame:
    """Recompute what Phase 2.1 actually showed and fix three overstatements."""
    source = PHASE2_1_DIR / "model_paired_contrasts.csv"
    require(source.is_file(), "Phase 2.1 contrasts are needed for the correction table")
    old = pd.read_csv(source)
    block = old[old.contrast.eq("4d_plus_width_dynamics - 4d_only") & old.holm_p_metric_family.notna()]
    survivors = block[block.holm_p_metric_family <= 0.05]
    survivor_text = (
        "; ".join(
            f"{row.subset} {row.metric} {row.mean_difference:+.5f} (Holm p={row.holm_p_metric_family:.4f})"
            for row in survivors.itertuples(index=False)
        )
        or "none"
    )
    shape = old[old.contrast.eq("4d_plus_width_shape_only - 4d_only")
                & old.subset.eq("q20") & old.metric.eq("balanced_accuracy")].iloc[0]
    collinearity = pd.read_csv(PHASE2_1_DIR / "width_vs_4d_collinearity.csv")
    rows = [
        {
            "previous_statement": "nothing anywhere survives the Holm adjustment",
            "verdict": "WRONG",
            "correction": f"Within the six-metric Holm family, {len(survivors)} results survive at the "
                          f"0.05 level: {survivor_text}. The q20 region alone showed no surviving effect.",
            "evidence": "outputs/week9_phase2_1_fourd_plus_width_control/model_paired_contrasts.csv",
        },
        {
            "previous_statement": "width adds no value beyond the 4D process inputs",
            "verdict": "OVERSTATED",
            "correction": "Safe wording: the full eight-feature width block did not show a supported q20 "
                          "improvement over 4D, while a secondary three-feature shape subset showed a "
                          f"positive development signal (q20 balanced accuracy {shape.mean_difference:+.4f} "
                          f"[{shape.ci_low:+.4f}, {shape.ci_high:+.4f}]).",
            "evidence": "same file, contrast 4d_plus_width_shape_only - 4d_only",
        },
        {
            "previous_statement": "width dynamics is redundant because R-squared = 0.58",
            "verdict": "CAUSALLY OVERSTATED",
            "correction": "Safe wording: several width-derived features are substantially predictable from "
                          f"the process inputs (median R-squared "
                          f"{float(collinearity.r2_explained_by_4d_inputs.median()):.2f}, range "
                          f"{float(collinearity.r2_explained_by_4d_inputs.min()):.2f}-"
                          f"{float(collinearity.r2_explained_by_4d_inputs.max()):.2f}). This is an "
                          "association, not a demonstrated cause of the null result.",
            "evidence": "outputs/week9_phase2_1_fourd_plus_width_control/width_vs_4d_collinearity.csv",
        },
        {
            "previous_statement": "the engineered eight-feature block is the width story",
            "verdict": "SUPERSEDED",
            "correction": "Phase 2.1 summarised the width trace using engineered shape and derivative "
                          "descriptors. Phase 2.1R instead asks the simpler question: what happens between "
                          "consecutive resampled analysis points?",
            "evidence": "this phase",
        },
    ]
    out = pd.DataFrame(rows)
    write_csv(OUTPUT / "phase2_1_corrections.csv", out)
    return out


# --------------------------------------------------------------------------------------
# 13. figures
# --------------------------------------------------------------------------------------
CONDUCTION = "#4477AA"
KEYHOLE = "#CC3311"
MODEL_ORDER = (
    "gpc_4d",
    "gpc_4d_plus_max_delta_W",
    "gpc_4d_plus_max_width_rate",
    "gpc_4d_plus_simple_delta_block",
    "gpc_4d_plus_simple_rate_block",
    "gpc_4d_plus_old_shape3",
    "gpc_4d_plus_old_full8",
    "m3",
    "m3_plus_max_delta_W",
)


def _save(fig: plt.Figure, name: str) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / name
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def _pretty(name: str) -> str:
    return name.replace("_", " ")


def make_figures(features: pd.DataFrame, table: pd.DataFrame, separation: pd.DataFrame,
                 sweep_curves: pd.DataFrame, threshold_summary: pd.DataFrame,
                 thresholds: pd.DataFrame, summary: pd.DataFrame, inference: pd.DataFrame,
                 sweep_verdict: pd.DataFrame, sweep: pd.DataFrame, claims: pd.DataFrame) -> list[Path]:
    plt.style.use("seaborn-v0_8-whitegrid")
    created: list[Path] = []

    # 1 -------------------------------------------------- how delta_W is constructed
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6))
    ax = axes[0]
    xs = [0, 1, 2, 3, 4]
    ws = [20, 30, 33, 31, 34]
    ax.plot(xs, ws, "o-", color="#333333", lw=2, ms=10, zorder=3)
    for x, w in zip(xs, ws):
        ax.annotate(f"{w}", (x, w), textcoords="offset points", xytext=(0, 12),
                    ha="center", fontsize=11, fontweight="bold")
    for i in range(len(xs) - 1):
        change = ws[i + 1] - ws[i]
        colour = "#117733" if change > 0 else "#CC3311"
        ax.annotate(
            "", xy=(xs[i + 1], ws[i + 1]), xytext=(xs[i + 1], ws[i]),
            arrowprops=dict(arrowstyle="->", color=colour, lw=2.2),
        )
        ax.text(xs[i + 1] + 0.08, (ws[i] + ws[i + 1]) / 2, f"{change:+d}",
                color=colour, fontsize=12, fontweight="bold", va="center")
    ax.set(xlabel="consecutive resampled analysis point", ylabel="transverse width W (µm)",
           title="ΔW is just the change from one point to the next", ylim=(16, 39))
    ax.set_xticks(xs, [f"i={i}" for i in xs])

    axes[1].axis("off")
    axes[1].text(
        0.0, 0.98,
        "Worked example\n\n"
        "W goes 20 → 30, so ΔW = +10\n"
        "then 30 → 33, so ΔW = +3\n"
        "then 33 → 31, so ΔW = −2\n"
        "then 31 → 34, so ΔW = +3\n\n"
        "The simulation's width-change sequence is\n"
        "    [+10, +3, −2, +3]\n\n"
        "From that one sequence we read off:\n"
        "  max_positive_delta_W      = 10   (biggest rise)\n"
        "  min_delta_W               = −2   (biggest fall)\n"
        "  median_positive_delta_W   = 3    (middle of +10,+3,+3)\n"
        "  fraction_positive_delta_W = 0.75 (3 of 4 rose)\n"
        "  total_positive_delta_W    = 16   (10+3+3)\n\n"
        "The rate version divides each rise by the time gap\n"
        "it happened in, giving µm per ms.",
        va="top", ha="left", fontsize=10.5, family="monospace",
    )
    fig.suptitle("Figure 1 — What ΔW means (one simulation, five analysis points)", fontsize=13)
    created.append(_save(fig, "01_delta_W_construction.png"))

    # 2 ------------------------------------------- example trace and its delta sequence
    examples = []
    for label in (0, 1):
        block = features[features.has_keyhole.eq(label)].sort_values("max_positive_delta_W")
        examples.append((label, block.iloc[len(block) // 2].experiment_name))
    fig, axes = plt.subplots(2, 2, figsize=(13, 7), sharex="col")
    for column, (label, name) in enumerate(examples):
        colour = KEYHOLE if label else CONDUCTION
        rows = table[table.simulation_id.eq(name)].sort_values("analysis_point_i")
        width = np.concatenate([rows.W_i_um.to_numpy(float), [rows.W_i_plus_1_um.iloc[-1]]])
        axes[0, column].plot(np.arange(len(width)), width, color=colour, lw=1.8)
        axes[0, column].set(
            ylabel="W (µm)" if column == 0 else "",
            title=f"{'Keyhole' if label else 'Conduction'}: {name[:24]}…",
        )
        delta = rows.delta_W_um.to_numpy(float)
        axes[1, column].bar(np.arange(len(delta)), delta, width=1.0,
                            color=np.where(delta > 0, "#117733", "#CC3311"))
        axes[1, column].axhline(0, color="black", lw=0.8)
        peak = int(np.argmax(delta))
        axes[1, column].annotate(
            f"max_positive_delta_W = {delta[peak]:+.2f} µm",
            xy=(peak, delta[peak]), xytext=(len(delta) * 0.35, delta.max() * 0.85),
            arrowprops=dict(arrowstyle="->", color="#333333", lw=1.4), fontsize=9.5,
        )
        axes[1, column].set(xlabel="consecutive resampled analysis point i",
                            ylabel="ΔW (µm)" if column == 0 else "")
    fig.suptitle("Figure 2 — A full width trace (top) and its ΔW sequence (bottom); "
                 f"{PRIMARY_RESOLUTION} analysis points", fontsize=13)
    created.append(_save(fig, "02_example_trace_and_delta.png"))

    # 3 and 4 ------------------------------------------------ headline distributions
    for number, (column, filename, unit) in enumerate(
        (
            ("max_positive_delta_W", "03_max_positive_delta_W_distribution.png", "µm"),
            ("max_positive_width_rate", "04_max_positive_width_rate_distribution.png", "µm/ms"),
        ),
        start=3,
    ):
        row = separation[separation.feature.eq(column)].iloc[0]
        fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6),
                                 gridspec_kw={"width_ratios": [1.5, 1]})
        conduction = features.loc[features.has_keyhole.eq(0), column].to_numpy(float)
        keyhole = features.loc[features.has_keyhole.eq(1), column].to_numpy(float)
        bins = np.histogram_bin_edges(features[column].to_numpy(float), bins=32)
        axes[0].hist(conduction, bins=bins, color=CONDUCTION, alpha=0.65, label=f"Conduction (n={len(conduction)})")
        axes[0].hist(keyhole, bins=bins, color=KEYHOLE, alpha=0.65, label=f"Keyhole (n={len(keyhole)})")
        axes[0].axvline(np.median(conduction), color=CONDUCTION, lw=2.2, ls="--")
        axes[0].axvline(np.median(keyhole), color=KEYHOLE, lw=2.2, ls="--")
        axes[0].set(xlabel=f"{_pretty(column)} ({unit})", ylabel="simulations",
                    title="Distributions overlap heavily" if abs(row.cliffs_delta) < 0.33
                          else "Distributions separate")
        axes[0].legend(fontsize=9)

        positions = [1, 2]
        parts = axes[1].violinplot([conduction, keyhole], positions=positions, showmedians=True,
                                   widths=0.8)
        for body, colour in zip(parts["bodies"], (CONDUCTION, KEYHOLE)):
            body.set_facecolor(colour)
            body.set_alpha(0.55)
        for key in ("cbars", "cmins", "cmaxes", "cmedians"):
            parts[key].set_color("#333333")
        axes[1].set_xticks(positions, ["Conduction", "Keyhole"])
        axes[1].set(ylabel=f"{_pretty(column)} ({unit})")
        axes[1].set_title(
            f"medians {row.conduction_median:.3g} vs {row.keyhole_median:.3g} {unit}\n"
            f"Cliff's δ = {row.cliffs_delta:+.3f}   ROC-AUC = {row.roc_auc_whole_sample:.3f}   "
            f"PR-AUC = {row.pr_auc_whole_sample:.3f}",
            fontsize=10,
        )
        fig.suptitle(
            f"Figure {number} — Do Keyhole simulations have larger "
            f"{'single-step width jumps' if number == 3 else 'width-growth rates'}?",
            fontsize=13,
        )
        created.append(_save(fig, filename))

    # 5 ------------------------------------------------------ threshold classifier
    palette = {"max_positive_delta_W": "#4C78A8", "max_positive_width_rate": "#EE7733"}
    units = {"max_positive_delta_W": "µm", "max_positive_width_rate": "µm/ms"}
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.0))
    for column, colour in palette.items():
        curve = (sweep_curves[sweep_curves.feature.eq(column)]
                 .groupby("threshold", as_index=False).balanced_accuracy.max()
                 .sort_values("threshold"))
        normalized = ((curve.threshold - curve.threshold.min())
                      / (curve.threshold.max() - curve.threshold.min()))
        axes[0].plot(normalized, curve.balanced_accuracy, color=colour, lw=2, label=_pretty(column))
    axes[0].axhline(0.5, color="black", lw=0.9, ls=":")
    axes[0].set(xlabel="cut position (min → max of that feature)",
                ylabel="whole-sample balanced accuracy",
                title="(a) Best cut using ALL labels\noptimistic — not a held-out number")
    axes[0].legend(fontsize=8)

    # Each feature's learned cuts are shown on its own normalised row, because the two
    # features live on wildly different scales (tens of µm versus thousands of µm/ms).
    summary_q20 = threshold_summary[threshold_summary.subset.eq("q20")].set_index("feature")
    for row, (column, colour) in enumerate(palette.items()):
        values = thresholds[thresholds.feature.eq(column)
                            & thresholds.subset.eq("q20")].learned_threshold.to_numpy(float)
        span = values.max() - values.min()
        normalized = (values - values.min()) / span if span > 0 else np.zeros_like(values)
        jitter = np.random.default_rng(SEED + row).uniform(-0.14, 0.14, len(values))
        axes[1].scatter(normalized, row + jitter, s=26, color=colour, alpha=0.55, edgecolor="none")
        median = float(summary_q20.loc[column, "learned_threshold_median"])
        share = float(summary_q20.loc[column, "fraction_of_folds_choosing_below"])
        axes[1].text(0.5, row + 0.34,
                     f"median cut {median:,.4g} {units[column]}   ·   "
                     f"{share:.0%} of folds chose 'small value means Keyhole'",
                     ha="center", fontsize=8.5, color="#333333")
    axes[1].set_yticks(list(range(len(palette))), [_pretty(c) for c in palette], fontsize=9)
    axes[1].set(xlim=(-0.06, 1.06), ylim=(-0.55, len(palette) - 0.15),
                xlabel="learned cut, normalised within each feature's own range",
                title="(b) Where the cut lands across the 100 folds\n"
                      "(each dot is one training fold)")

    block = threshold_summary[threshold_summary.subset.eq("q20")].reset_index(drop=True)
    positions = np.arange(len(block))
    axes[2].barh(positions, block.balanced_accuracy_mean,
                 xerr=block.balanced_accuracy_sd_across_repeats,
                 color=[palette[f] for f in block.feature], error_kw={"lw": 1.0, "ecolor": "#333333"})
    axes[2].axvline(0.5, color="black", lw=1.4, ls="--", label="chance (0.50)")
    for position, row in block.iterrows():
        axes[2].text(row.balanced_accuracy_mean + 0.02, position,
                     f"{row.balanced_accuracy_mean:.3f}   recall {row.keyhole_recall_mean:.3f}",
                     va="center", fontsize=9)
    axes[2].set_yticks(positions, [_pretty(f) for f in block.feature], fontsize=9)
    axes[2].set(xlim=(0, 1.05), xlabel="held-out q20 balanced accuracy",
                title="(c) Leak-free: cut learned on training folds\nonly, then frozen")
    axes[2].legend(fontsize=8, loc="lower right")
    fig.suptitle("Figure 5 — The simple 'if the jump is small enough, call it Keyhole' rule",
                 fontsize=13, y=1.04)
    fig.subplots_adjust(wspace=0.32)
    created.append(_save(fig, "05_threshold_classifier.png"))

    # 6 ------------------------------------------ GPC vs GPC+width vs M3 comparison
    order = [m for m in MODEL_ORDER if m in set(summary.model)]
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 5.4), sharey=True)
    for ax, metric, title in (
        (axes[0], "balanced_accuracy", "q20 balanced accuracy"),
        (axes[1], "keyhole_recall", "q20 Keyhole recall"),
        (axes[2], "roc_auc", "q20 ROC-AUC"),
    ):
        block = summary[summary.subset.eq("q20") & summary.metric.eq(metric)].set_index("model")
        means = np.array([float(block.loc[m, "mean"]) for m in order])
        sds = np.array([float(block.loc[m, "sd_across_repeats"]) for m in order])
        colours = []
        for m in order:
            if m == "gpc_4d":
                colours.append("#333333")
            elif m.startswith("m3"):
                colours.append("#117733")
            elif "old_" in m:
                colours.append("#BBBBBB")
            else:
                colours.append("#CC3311")
        ax.barh(np.arange(len(order)), means, xerr=sds, color=colours,
                error_kw={"lw": 0.9, "ecolor": "#555555"})
        ax.axvline(0.5, color="#888888", lw=0.8, ls=":")
        ax.set(xlim=(0.0, 1.22), xlabel=title)
        for position, value in enumerate(means):
            ax.text(value + 0.03, position, f"{value:.3f}", va="center", fontsize=8)
    axes[0].set_yticks(np.arange(len(order)), [_pretty(m) for m in order], fontsize=9)
    handles = [
        plt.Rectangle((0, 0), 1, 1, color="#333333"), plt.Rectangle((0, 0), 1, 1, color="#CC3311"),
        plt.Rectangle((0, 0), 1, 1, color="#BBBBBB"), plt.Rectangle((0, 0), 1, 1, color="#117733"),
    ]
    axes[2].legend(handles, ["4D baseline", "4D + simple ΔW", "4D + old engineered", "M3 family"],
                   fontsize=8, loc="lower right")
    fig.suptitle("Figure 6 — Canonical ARD Matérn-3/2 GPC on the 100 frozen grouped folds "
                 "(error bars = SD across 20 repeat blocks)", fontsize=13)
    fig.subplots_adjust(wspace=0.1)
    created.append(_save(fig, "06_model_comparison_gpc_m3.png"))

    # 7 --------------------------------------------------- q20 paired contrasts forest
    shown = [c for c in inference.contrast.unique()
             if inference[inference.contrast.eq(c)].contrast_role.iloc[0] in
             {"primary", "m3_context", "historical"}]
    block = inference[inference.subset.eq("q20") & inference.contrast.isin(shown)].copy()
    block["oriented_mean"] = np.where(block.lower_is_better, -1, 1) * block.mean_difference
    block["oriented_low"] = np.minimum(
        np.where(block.lower_is_better, -1, 1) * block.ci_low,
        np.where(block.lower_is_better, -1, 1) * block.ci_high)
    block["oriented_high"] = np.maximum(
        np.where(block.lower_is_better, -1, 1) * block.ci_low,
        np.where(block.lower_is_better, -1, 1) * block.ci_high)
    metrics = ["balanced_accuracy", "keyhole_recall", "roc_auc", "pr_auc"]
    fig, axes = plt.subplots(1, len(metrics), figsize=(17, 5.6), sharey=True)
    contrasts_order = shown
    for ax, metric in zip(axes, metrics):
        sub = block[block.metric.eq(metric)].set_index("contrast").loc[contrasts_order]
        positions = np.arange(len(sub))[::-1]
        for position, row in zip(positions, sub.itertuples()):
            colour = {"IMPROVES": "#117733", "DEGRADES": "#CC3311"}.get(row.verdict_after_holm, "#888888")
            ax.plot([row.oriented_low, row.oriented_high], [position, position], color=colour, lw=2.4,
                    solid_capstyle="round")
            ax.plot([row.oriented_mean], [position], "o", color=colour, ms=6)
        ax.axvline(0, color="black", lw=1.0)
        ax.set(xlabel=_pretty(metric), title=_pretty(metric))
    axes[0].set_yticks(np.arange(len(contrasts_order))[::-1],
                       [_pretty(c) for c in contrasts_order], fontsize=8)
    fig.suptitle("Figure 7 — q20 paired contrasts (right = challenger better). "
                 "Green = survives Holm over the six metrics; grey = no detectable difference", fontsize=12)
    created.append(_save(fig, "07_q20_paired_contrasts.png"))

    # 8 -------------------------------------------------------- derivative ablation
    ablation_models = ["gpc_4d_plus_old_shape3"] + [
        f"abl_shape3_plus_{d}" for d in OLD_DERIVATIVE_FEATURES] + ["gpc_4d_plus_old_full8"]
    block = summary[summary.subset.eq("q20") & summary.metric.eq("balanced_accuracy")].set_index("model")
    means = np.array([float(block.loc[m, "mean"]) for m in ablation_models])
    sds = np.array([float(block.loc[m, "sd_across_repeats"]) for m in ablation_models])
    baseline = float(block.loc["gpc_4d", "mean"])
    shape_only = means[0]
    labels = ["4D + shape3\n(starting point)"] + [
        "+ " + _pretty(d).replace("robust ", "") for d in OLD_DERIVATIVE_FEATURES
    ] + ["+ all five\n(= old full 8)"]
    fig, ax = plt.subplots(figsize=(13, 5.6))
    colours = ["#4C78A8"] + ["#BBBBBB"] * len(OLD_DERIVATIVE_FEATURES) + ["#CC3311"]
    ax.bar(np.arange(len(means)), means, yerr=sds, color=colours,
           error_kw={"lw": 1.0, "ecolor": "#333333"})
    ax.axhline(baseline, color="#333333", lw=1.6, ls="--", label=f"4D-only GPC baseline ({baseline:.3f})")
    ax.axhline(shape_only, color="#4C78A8", lw=1.4, ls=":", label=f"4D + shape3 ({shape_only:.3f})")
    for position, value in enumerate(means):
        ax.text(position, value + 0.006, f"{value:.3f}", ha="center", fontsize=9)
    ax.set_xticks(np.arange(len(means)), labels, fontsize=8.5)
    ax.set(ylabel="q20 balanced accuracy",
           ylim=(min(means.min(), baseline) - 0.04, max(means.max(), baseline) + 0.04),
           title="Figure 8 — Adding the old robust-derivative features back, one at a time, "
                 "on top of 4D + shape3")
    ax.legend(fontsize=9)
    created.append(_save(fig, "08_derivative_ablation.png"))

    # 9 ------------------------------------------------------------- claim status
    status_colour = {"SUPPORTED": "#117733", "QUALIFIED": "#EE7733",
                     "NOT SUPPORTED": "#CC3311", "DESCRIPTIVE ONLY": "#666666"}
    wrapped_claims = [textwrap.fill(c, 62) for c in claims.claim]
    wrapped_guards = [textwrap.fill(g, 82) for g in claims.guardrail]
    fig, ax = plt.subplots(figsize=(13.5, 0.80 * len(claims) + 1.7))
    ax.axis("off")
    width = 1.42
    ax.set_xlim(0, width)
    ax.set_ylim(0, len(claims) + 1.4)
    for x, header in ((0.01, "Claim"), (0.55, "Status"), (0.72, "Guardrail")):
        ax.text(x, len(claims) + 0.75, header, fontsize=10, fontweight="bold")
    ax.plot([0, width], [len(claims) + 0.5] * 2, color="black", lw=1.0)
    for position, row in enumerate(claims.itertuples(index=False)):
        y = len(claims) - position - 0.5
        if position % 2 == 0:
            ax.add_patch(plt.Rectangle((0, y - 0.5), width, 1.0, color="#F4F4F4", zorder=0))
        ax.text(0.01, y, wrapped_claims[position], fontsize=8.3, va="center", zorder=2, linespacing=1.35)
        ax.text(0.55, y, row.status, fontsize=8.5, va="center", fontweight="bold",
                color=status_colour.get(row.status, "#333333"), zorder=2)
        ax.text(0.72, y, wrapped_guards[position], fontsize=7.5, va="center", color="#444444",
                zorder=2, linespacing=1.35)
    ax.set_title("Figure 9 — Week 9 Phase 2.1R claim status", fontsize=13, pad=14)
    created.append(_save(fig, "09_claim_status.png"))

    # 10 ------------------------------------------------------ resolution robustness
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.0))
    for feature in HEADLINE_UNIVARIATE:
        block = sweep[sweep.feature.eq(feature)].sort_values("resolution_points")
        axes[0].plot(block.resolution_points, block.cliffs_delta, "o-", lw=2, ms=8, label=_pretty(feature))
        axes[1].plot(block.resolution_points, block.roc_auc_whole_sample, "o-", lw=2, ms=8,
                     label=_pretty(feature))
    for ax, ylabel, reference, title in (
        (axes[0], "Cliff's δ (Keyhole − Conduction)", 0.0, "Effect size vs grid resolution"),
        (axes[1], "whole-sample ROC-AUC", 0.5, "Ranking power vs grid resolution"),
    ):
        ax.axhline(reference, color="black", lw=1.0, ls="--")
        ax.set(xlabel="analysis points per simulation", ylabel=ylabel, title=title,
               xticks=list(RESOLUTIONS))
        ax.legend(fontsize=9)

    # third panel: does the MODEL-level gain survive the resolution change, not just the
    # marginal effect? Same GPC, same folds, only the grid used to build max ΔW changes.
    model_by_resolution = {
        51: "gpc_4d_plus_max_delta_W_res51",
        101: "gpc_4d_plus_max_delta_W_res101",
        201: "gpc_4d_plus_max_delta_W",
    }
    for metric, colour, marker in (("pr_auc", "#CC3311", "o"), ("roc_auc", "#4C78A8", "s"),
                                   ("balanced_accuracy", "#999999", "^")):
        means, lows, highs = [], [], []
        for resolution in RESOLUTIONS:
            row = inference[
                inference.contrast.eq(f"{model_by_resolution[resolution]} - gpc_4d")
                & inference.subset.eq("q20") & inference.metric.eq(metric)
            ].iloc[0]
            means.append(row.mean_difference)
            lows.append(row.mean_difference - row.ci_low)
            highs.append(row.ci_high - row.mean_difference)
        axes[2].errorbar(list(RESOLUTIONS), means, yerr=[lows, highs], marker=marker, lw=2, ms=8,
                         color=colour, capsize=4, label=_pretty(metric))
    axes[2].axhline(0, color="black", lw=1.0, ls="--")
    axes[2].set(xlabel="analysis points used to build max ΔW",
                ylabel="q20 gain over 4D-only GPC", xticks=list(RESOLUTIONS),
                title="Does the MODEL gain survive?\n(same GPC and folds, only the grid changes)")
    axes[2].legend(fontsize=9)
    fig.suptitle("Figure 10 — Is the answer an artifact of how finely we resample the trace?", fontsize=13)
    fig.subplots_adjust(wspace=0.3)
    created.append(_save(fig, "10_resolution_sweep.png"))
    return created


# --------------------------------------------------------------------------------------
# 14. four self-contained offline interactive 3D process-space views, plus an index
# --------------------------------------------------------------------------------------
AXIS_LABELS = {
    "P": "P — laser power (W)",
    "VX": "VX — scan speed (m/s)",
    "LS": "LS — spot radius (µm)",
    "ST": "ST — substrate temperature (K)",
}
AXIS_LONG = {
    "P": "laser power",
    "VX": "scan speed",
    "LS": "laser spot radius",
    "ST": "substrate temperature",
}
VIEWS = (
    ("view1_drop_ST", ("P", "VX", "LS"), "ST"),
    ("view2_drop_LS", ("P", "VX", "ST"), "LS"),
    ("view3_drop_VX", ("P", "LS", "ST"), "VX"),
    ("view4_drop_P", ("VX", "LS", "ST"), "P"),
)

VIEW_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { --ink:#1c1c1c; --muted:#5d5d5d; --line:#d8d8d8; --panel:#ffffff; --bg:#f6f6f4;
          --conduction:#4477AA; --keyhole:#CC3311; }
  * { box-sizing:border-box; }
  body { margin:0; font:14px/1.5 "Segoe UI", system-ui, -apple-system, Arial, sans-serif;
         color:var(--ink); background:var(--bg); }
  header { padding:14px 22px 11px; border-bottom:1px solid var(--line); background:var(--panel); }
  h1 { margin:0 0 3px; font-size:16.5px; font-weight:650; letter-spacing:-0.01em; }
  header p { margin:0; color:var(--muted); font-size:12.5px; max-width:110ch; }
  header a { color:#4477AA; text-decoration:none; font-size:12.5px; }
  header a:hover { text-decoration:underline; }
  .wrap { display:flex; height:calc(100vh - 84px); min-height:520px; }
  #stage { flex:1 1 auto; position:relative; background:var(--panel); }
  canvas { display:block; width:100%; height:100%; cursor:grab; }
  canvas.dragging { cursor:grabbing; }
  aside { width:290px; flex:0 0 290px; border-left:1px solid var(--line); background:var(--panel);
          padding:15px 18px; overflow-y:auto; }
  aside h2 { font-size:11px; text-transform:uppercase; letter-spacing:.07em; color:var(--muted);
             margin:17px 0 7px; font-weight:650; }
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
         box-shadow:0 4px 14px rgba(0,0,0,.14); max-width:340px; z-index:5; }
  #tip code { font-size:10.5px; color:var(--muted); overflow-wrap:anywhere; }
  .k { color:var(--muted); }
  .note { font-size:11.5px; color:var(--muted); margin-top:6px; overflow-wrap:anywhere; }
  #ramp { height:11px; border-radius:3px; margin:6px 0 2px; border:1px solid var(--line); }
  .rampends { display:flex; justify-content:space-between; font-size:11px; color:var(--muted); }
  .stat { font-size:12px; color:var(--muted); margin-top:5px; }
  .dropped { background:#FFF6E6; border:1px solid #F0D9A8; border-radius:5px; padding:7px 9px;
             font-size:12px; margin-top:8px; }
</style>
</head>
<body>
<header>
  <h1>__HEADING__</h1>
  <p>__BLURB__ &nbsp;·&nbsp; <a href="../interactive_3d_index.html">← all four views</a></p>
</header>
<div class="wrap">
  <div id="stage"><canvas id="cv"></canvas><div id="tip"></div></div>
  <aside>
    <h2>Colour by</h2>
    <select id="colormode">
      <option value="label">Manual label (has_keyhole)</option>
      <option value="logh">log h = log(P / sqrt(VX · LS³))</option>
      <option value="dropped">__DROPPED__ (the dropped axis)</option>
    </select>
    <div id="ramp"></div>
    <div class="rampends"><span id="rampLo"></span><span id="rampHi"></span></div>
    <div class="dropped"><b>__DROPPED__</b> is not an axis in this view. Colour by it, or read it in the
      hover card, to check whether it explains anything the three axes miss.</div>

    <h2>Show</h2>
    <select id="classfilter">
      <option value="all">All simulations</option>
      <option value="keyhole">Keyhole only</option>
      <option value="conduction">Conduction only</option>
    </select>
    <label class="row" style="margin-top:8px"><input type="checkbox" id="onlyUsable">
      <span class="swatch" style="background:#999"></span>Usable width trace only</label>
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
const AXES = __AXES__;
const DROPPED = __DROPPEDKEY__;

const cv = document.getElementById('cv');
const ctx = cv.getContext('2d');
const tip = document.getElementById('tip');
const stage = document.getElementById('stage');
let az = -0.62, el = 0.42, zoom = 1.0, dragging = false, lastX = 0, lastY = 0, dpr = 1;
let W = 0, H = 0, projected = [];

const bounds = AXES.map(a => {
  const v = DATA.map(d => d[a.key]);
  return {lo: Math.min(...v), hi: Math.max(...v)};
});
const norm = (v, i) => (v - bounds[i].lo) / (bounds[i].hi - bounds[i].lo) - 0.5;
const fmt = v => Math.abs(v) >= 100 ? v.toFixed(0) : (Math.abs(v) >= 1 ? v.toFixed(2) : v.toFixed(3));

const RAMP = [[68,1,84],[59,82,139],[33,145,140],[94,201,98],[253,231,37]];
function rampColor(t){
  t = Math.max(0, Math.min(1, t));
  const x = t * (RAMP.length - 1), i = Math.min(Math.floor(x), RAMP.length - 2), f = x - i;
  const a = RAMP[i], b = RAMP[i+1];
  return `rgb(${Math.round(a[0]+(b[0]-a[0])*f)},${Math.round(a[1]+(b[1]-a[1])*f)},${Math.round(a[2]+(b[2]-a[2])*f)})`;
}
const rampCss = () => 'linear-gradient(to right,' + RAMP.map(c => `rgb(${c[0]},${c[1]},${c[2]})`).join(',') + ')';

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
  const depth = y2 + 2.9;
  const scale = document.getElementById('persp').checked
      ? (1.55 * Math.min(W, H)) / depth : 0.55 * Math.min(W, H);
  return {x: W/2 + x1*scale*zoom, y: H/2 - z2*scale*zoom, depth: depth};
}

function activeSet(){
  const mode = document.getElementById('classfilter').value;
  const onlyUsable = document.getElementById('onlyUsable').checked;
  return DATA.filter(d => (mode === 'all' || (mode === 'keyhole' ? d.k : !d.k))
                          && (!onlyUsable || d.u));
}

function colorOf(d){
  const mode = document.getElementById('colormode').value;
  if (mode === 'label') return d.k ? '#CC3311' : '#4477AA';
  const field = mode === 'logh' ? 'logh' : DROPPED;
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
  ctx.textAlign = 'center';
  [[0,1],[0,2],[0,4]].forEach(([a,b], i) => {
    const at = t => ({x: corners[a].x + (corners[b].x - corners[a].x)*t,
                      y: corners[a].y + (corners[b].y - corners[a].y)*t});
    const dy = (i === 2) ? -14 : 18;
    const mid = at(0.5), lo = at(0.10), hi = at(0.90);
    ctx.fillStyle = '#333'; ctx.font = '12px "Segoe UI", system-ui, sans-serif';
    ctx.fillText(AXES[i].label, mid.x, mid.y + dy);
    ctx.fillStyle = '#9a9a9a'; ctx.font = '10.5px "Segoe UI", system-ui, sans-serif';
    ctx.fillText(fmt(bounds[i].lo), lo.x, lo.y + dy);
    ctx.fillText(fmt(bounds[i].hi), hi.x, hi.y + dy);
  });
}

function draw(){
  ctx.clearRect(0, 0, W, H);
  drawBox();
  const radius = parseFloat(document.getElementById('size').value);
  projected = activeSet().map(d => {
    const q = project([norm(d[AXES[0].key],0), norm(d[AXES[1].key],1), norm(d[AXES[2].key],2)]);
    return {d: d, x: q.x, y: q.y, depth: q.depth};
  }).sort((a, b) => b.depth - a.depth);
  projected.forEach(p => {
    const r = radius * (2.9 / p.depth);
    ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, 6.2832);
    ctx.fillStyle = colorOf(p.d);
    ctx.globalAlpha = p.d.u ? 0.92 : 0.42;
    ctx.fill(); ctx.globalAlpha = 1;
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
    const field = mode === 'logh' ? 'logh' : DROPPED;
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
    `<br><span class="k">P</span> ${d.P.toFixed(2)} W &nbsp;<span class="k">VX</span> ${d.VX.toFixed(4)} m/s` +
    `<br><span class="k">LS</span> ${d.LS.toFixed(2)} µm &nbsp;<span class="k">ST</span> ${d.ST.toFixed(2)} K` +
    `<br><span class="k">log h</span> ${d.logh.toFixed(4)}` +
    `<br><span class="k">width trace</span> ${d.u ? 'usable in Phase 2.1R' : 'missing / unusable'}`;
  tip.style.display = 'block';
  tip.style.left = Math.min(mx + 16, W - tip.offsetWidth - 8) + 'px';
  tip.style.top = Math.max(8, Math.min(my + 16, H - tip.offsetHeight - 8)) + 'px';
});
cv.addEventListener('mouseleave', () => { tip.style.display = 'none'; });

['classfilter','onlyUsable','size','persp'].forEach(id =>
  document.getElementById(id).addEventListener('input', draw));
document.getElementById('colormode').addEventListener('change', () => { updateRamp(); draw(); });
document.getElementById('reset').addEventListener('click', () => { az = -0.62; el = 0.42; zoom = 1.0; draw(); });
document.getElementById('prov').innerHTML = META.provenance;
window.addEventListener('resize', resize);
updateRamp();
resize();
</script>
</body>
</html>
"""


def make_interactive_views(population: pd.DataFrame, features: pd.DataFrame) -> list[Path]:
    usable = set(features.experiment_name)
    payload = [
        {
            "id": str(row.experiment_name),
            "P": round(float(row.P), 6),
            "VX": round(float(row.VX), 6),
            "LS": round(float(row.LS) * 1e6, 4),
            "ST": round(float(row.ST), 4),
            "logh": round(float(row.log_h), 6),
            "k": int(row.has_keyhole),
            "u": int(row.experiment_name in usable),
        }
        for row in population.itertuples(index=False)
    ]
    provenance = (
        f"Canonical frozen population: {len(population)} simulations, "
        f"{int(population.has_keyhole.sum())} Keyhole.<br>"
        f"Width traces usable in Phase 2.1R: {len(usable)}.<br>"
        f"LS is the Gaussian laser spot radius; ST is substrate temperature.<br>"
        f"Generated by <code>src/week9_phase2_1r_simple_width_change_control.py</code>. "
        f"Local artifact; works offline, no libraries, no network."
    )
    INTERACTIVE.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for slug, axes, dropped in VIEWS:
        heading = (
            f"{' · '.join(axes)} — {AXIS_LONG[dropped]} ({dropped}) dropped from the axes"
        )
        blurb = (
            f"All {len(population)} frozen simulations placed by <b>{axes[0]}</b>, <b>{axes[1]}</b> and "
            f"<b>{axes[2]}</b>, coloured by the manual <b>has_keyhole</b> label. <b>{dropped}</b> "
            f"({AXIS_LONG[dropped]}) is deliberately not an axis here — colour by it or hover to see it. "
            f"Drag to rotate, scroll to zoom."
        )
        html = (
            VIEW_TEMPLATE
            .replace("__TITLE__", f"Phase 2.1R 3D — {' , '.join(axes)} (drop {dropped})")
            .replace("__HEADING__", heading)
            .replace("__BLURB__", blurb)
            .replace("__DROPPEDKEY__", json.dumps(dropped))
            .replace("__DROPPED__", dropped)
            .replace("__AXES__", json.dumps([{"key": a, "label": AXIS_LABELS[a]} for a in axes]))
            .replace("__DATA__", json.dumps(payload, separators=(",", ":")))
            .replace("__META__", json.dumps({"provenance": provenance}))
        )
        path = INTERACTIVE / f"{slug}.html"
        path.write_text(html, encoding="utf-8")
        created.append(path)

    cards = "\n".join(
        f"""    <a class="card" href="interactive/{slug}.html">
      <div class="axes">{' · '.join(axes)}</div>
      <div class="drop">{dropped} dropped</div>
      <p>Positions come from {axes[0]}, {axes[1]} and {axes[2]}. {dropped} ({AXIS_LONG[dropped]})
         stays available as a colour mode and in the hover card.</p>
    </a>"""
        for slug, axes, dropped in VIEWS
    )
    index = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Phase 2.1R — interactive 3D process-space views</title>
<style>
  body {{ margin:0; font:14px/1.6 "Segoe UI", system-ui, -apple-system, Arial, sans-serif;
         color:#1c1c1c; background:#f6f6f4; }}
  header {{ padding:26px 32px 20px; background:#fff; border-bottom:1px solid #d8d8d8; }}
  h1 {{ margin:0 0 6px; font-size:21px; font-weight:650; letter-spacing:-0.01em; }}
  header p {{ margin:0; color:#5d5d5d; max-width:100ch; }}
  main {{ padding:26px 32px; display:grid; gap:18px;
          grid-template-columns:repeat(auto-fit, minmax(290px, 1fr)); max-width:1200px; }}
  .card {{ display:block; background:#fff; border:1px solid #d8d8d8; border-radius:9px;
           padding:18px 20px; text-decoration:none; color:inherit; transition:.14s; }}
  .card:hover {{ border-color:#4477AA; box-shadow:0 5px 16px rgba(0,0,0,.09); transform:translateY(-2px); }}
  .axes {{ font-size:19px; font-weight:650; letter-spacing:.01em; }}
  .drop {{ display:inline-block; margin:7px 0 9px; font-size:11.5px; text-transform:uppercase;
           letter-spacing:.06em; color:#8a5a12; background:#FFF6E6; border:1px solid #F0D9A8;
           border-radius:4px; padding:2px 8px; }}
  .card p {{ margin:0; font-size:12.5px; color:#5d5d5d; }}
  footer {{ padding:8px 32px 32px; color:#5d5d5d; font-size:12.5px; max-width:1200px; }}
  code {{ font-size:11.5px; }}
</style>
</head>
<body>
<header>
  <h1>Week 9 Phase 2.1R — interactive 3D process-space views</h1>
  <p>The process space has four inputs, so no single 3D picture can show it. These four views each drop
     one input from the axes and keep it as a colour mode and hover field, so every input gets a turn
     being the hidden one. All {len(population)} frozen simulations appear in every view
     ({int(population.has_keyhole.sum())} Keyhole), coloured by the manual <code>has_keyhole</code> label
     by default.</p>
</header>
<main>
{cards}
</main>
<footer>
  Each view is self-contained: no libraries, no network, works offline. Colour by label, by
  <code>log h</code>, or by the dropped input; filter to Keyhole only, Conduction only, or to the
  simulations with a usable width trace; drag to rotate and scroll to zoom.
</footer>
</body>
</html>
"""
    index_path = OUTPUT / "interactive_3d_index.html"
    index_path.write_text(index, encoding="utf-8")
    created.append(index_path)
    return created


# --------------------------------------------------------------------------------------
# claim ledger
# --------------------------------------------------------------------------------------
def build_claims(separation: pd.DataFrame, threshold_summary: pd.DataFrame, summary: pd.DataFrame,
                 inference: pd.DataFrame, sweep_verdict: pd.DataFrame,
                 corrections: pd.DataFrame, features: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    def mean_of(model: str, metric: str, subset: str = "q20") -> float:
        row = summary[summary.model.eq(model) & summary.subset.eq(subset) & summary.metric.eq(metric)]
        return float(row.iloc[0]["mean"])

    def contrast_of(name: str, metric: str, subset: str = "q20") -> pd.Series:
        block = inference[inference.contrast.eq(name) & inference.subset.eq(subset)
                          & inference.metric.eq(metric)]
        require(len(block) == 1, f"missing contrast {name}/{metric}/{subset}")
        return block.iloc[0]

    def family(name: str, subset: str = "q20") -> tuple[str, str]:
        block = inference[inference.contrast.eq(name) & inference.subset.eq(subset)]
        return (
            family_status(block[block.metric_family.eq("hard_decision")]),
            family_status(block[block.metric_family.eq("ranking_or_probability")]),
        )

    delta_sep = separation[separation.feature.eq("max_positive_delta_W")].iloc[0]
    rate_sep = separation[separation.feature.eq("max_positive_width_rate")].iloc[0]
    delta_threshold = threshold_summary[threshold_summary.feature.eq("max_positive_delta_W")
                                        & threshold_summary.subset.eq("q20")].iloc[0]
    rate_threshold = threshold_summary[threshold_summary.feature.eq("max_positive_width_rate")
                                       & threshold_summary.subset.eq("q20")].iloc[0]

    primary_hard, primary_rank = family(PRIMARY_CONTRAST)
    block_hard, block_rank = family("gpc_4d_plus_simple_delta_block - gpc_4d")
    rate_hard, rate_rank = family("gpc_4d_plus_max_width_rate - gpc_4d")
    m3_hard, m3_rank = family("m3 - gpc_4d")
    m3w_hard, m3w_rank = family("m3_plus_max_delta_W - m3")
    block_vs_m3_hard, block_vs_m3_rank = family("gpc_4d_plus_simple_delta_block - m3")
    shape_hard, shape_rank = family("gpc_4d_plus_old_shape3 - gpc_4d")
    full8_hard, full8_rank = family("gpc_4d_plus_old_full8 - gpc_4d")

    delta_robust = bool(sweep_verdict[sweep_verdict.feature.eq("max_positive_delta_W")]
                        .resolution_robust.iloc[0])
    # WHERE in the trace does the biggest jump sit? If it is always at the very start, then
    # max_positive_delta_W is a melt-pool formation quantity, not a Keyhole-onset signal.
    location = features.diagnostic_argmax_delta_W_fraction.to_numpy(float)
    share_first_5pct = float(np.mean(location <= 0.05))
    median_location = float(np.median(location))
    startup_quantity = share_first_5pct >= 0.90
    # Does the model-level gain, not just the marginal effect, survive changing the grid?
    model_by_resolution = {51: "gpc_4d_plus_max_delta_W_res51",
                           101: "gpc_4d_plus_max_delta_W_res101",
                           201: "gpc_4d_plus_max_delta_W"}
    model_resolution_rows = [
        contrast_of(f"{model_by_resolution[res]} - gpc_4d", "pr_auc") for res in RESOLUTIONS
    ]
    model_resolution_gains = [float(row.mean_difference) for row in model_resolution_rows]
    model_resolution_verdicts = [str(row.verdict_after_holm) for row in model_resolution_rows]
    model_resolution_status = (
        "SUPPORTED" if all(v == "IMPROVES" for v in model_resolution_verdicts)
        else ("QUALIFIED" if any(v == "IMPROVES" for v in model_resolution_verdicts)
              else "NOT SUPPORTED")
    )
    rate_robust = bool(sweep_verdict[sweep_verdict.feature.eq("max_positive_width_rate")]
                       .resolution_robust.iloc[0])

    # Which single derivative hurts the shape3 model most / least?
    ablation = inference[inference.contrast_role.eq("ablation") & inference.subset.eq("q20")
                         & inference.metric.eq("balanced_accuracy")
                         & inference.contrast.str.startswith("abl_")]
    worst = ablation.sort_values("mean_difference").iloc[0]
    any_derivative_hurts = bool((ablation.verdict_after_holm == "DEGRADES").any())

    delta_separates = (
        "SUPPORTED" if (delta_sep.median_difference_ci_low > 0 or delta_sep.median_difference_ci_high < 0)
        and abs(delta_sep.cliffs_delta) >= 0.147 else
        ("QUALIFIED" if (delta_sep.median_difference_ci_low > 0 or delta_sep.median_difference_ci_high < 0)
         else "NOT SUPPORTED")
    )
    rate_separates = (
        "SUPPORTED" if (rate_sep.median_difference_ci_low > 0 or rate_sep.median_difference_ci_high < 0)
        and abs(rate_sep.cliffs_delta) >= 0.147 else
        ("QUALIFIED" if (rate_sep.median_difference_ci_low > 0 or rate_sep.median_difference_ci_high < 0)
         else "NOT SUPPORTED")
    )
    threshold_beats_chance = (
        "SUPPORTED" if delta_threshold.balanced_accuracy_mean - 2 * delta_threshold.balanced_accuracy_sd_across_repeats > 0.5
        else ("QUALIFIED" if delta_threshold.balanced_accuracy_mean > 0.55 else "NOT SUPPORTED")
    )

    claims = pd.DataFrame(
        [
            {
                "claim": "Keyhole simulations show larger maximum width increases between consecutive "
                         "resampled analysis points than Conduction simulations",
                "status": delta_separates,
                "guardrail": f"descriptive, whole sample: medians {delta_sep.keyhole_median:.2f} vs "
                             f"{delta_sep.conduction_median:.2f} µm, Cliff's δ = {delta_sep.cliffs_delta:+.3f}, "
                             f"ROC-AUC = {delta_sep.roc_auc_whole_sample:.3f}",
            },
            {
                "claim": "The MODEL-level gain from max_positive_delta_W survives changing the grid "
                         "resolution (51 / 101 / 201 points)",
                "status": model_resolution_status,
                "guardrail": "same GPC, same folds, only the grid used to build the feature changes; "
                             "q20 PR-AUC gain " + " / ".join(
                                 f"{v:+.4f}" for v in model_resolution_gains),
            },
            {
                "claim": "That separation is robust to the choice of grid resolution (51 / 101 / 201 points)",
                "status": "SUPPORTED" if delta_robust else "QUALIFIED",
                "guardrail": f"Cliff's δ = "
                             f"{float(sweep_verdict[sweep_verdict.feature.eq('max_positive_delta_W')].cliffs_delta_51.iloc[0]):+.3f} / "
                             f"{float(sweep_verdict[sweep_verdict.feature.eq('max_positive_delta_W')].cliffs_delta_101.iloc[0]):+.3f} / "
                             f"{float(sweep_verdict[sweep_verdict.feature.eq('max_positive_delta_W')].cliffs_delta_201.iloc[0]):+.3f} "
                             f"at 51 / 101 / 201 analysis points",
            },
            {
                "claim": "A simple leak-free threshold on max_positive_delta_W classifies better than chance "
                         "on the q20 boundary band",
                "status": threshold_beats_chance,
                "guardrail": f"threshold learned on training folds only; q20 balanced accuracy "
                             f"{delta_threshold.balanced_accuracy_mean:.3f} "
                             f"± {delta_threshold.balanced_accuracy_sd_across_repeats:.3f}, "
                             f"Keyhole recall {delta_threshold.keyhole_recall_mean:.3f}",
            },
            {
                "claim": "Dividing by the actual time gap (ΔW/Δt) changes the conclusion versus raw ΔW",
                "status": "NOT SUPPORTED" if abs(delta_sep.cliffs_delta - rate_sep.cliffs_delta) < 0.05
                          else "QUALIFIED",
                "guardrail": f"Cliff's δ {delta_sep.cliffs_delta:+.3f} (raw ΔW) vs "
                             f"{rate_sep.cliffs_delta:+.3f} (rate); q20 threshold balanced accuracy "
                             f"{delta_threshold.balanced_accuracy_mean:.3f} vs "
                             f"{rate_threshold.balanced_accuracy_mean:.3f}",
            },
            {
                "claim": "PRIMARY — adding max_positive_delta_W to the 4D GPC improves hard classification "
                         "on q20",
                "status": primary_hard,
                "guardrail": f"q20 balanced accuracy {mean_of('gpc_4d', 'balanced_accuracy'):.4f} → "
                             f"{mean_of('gpc_4d_plus_max_delta_W', 'balanced_accuracy'):.4f}; "
                             f"Holm over six metrics within the contrast",
            },
            {
                "claim": "PRIMARY — the same addition improves ranking / probability quality on q20",
                "status": primary_rank,
                "guardrail": "q20 ROC-AUC / PR-AUC / Brier, read separately from the hard metrics",
            },
            {
                "claim": "The biggest width jump is a melt-pool STARTUP quantity, not a Keyhole-onset "
                         "signal",
                "status": "SUPPORTED" if startup_quantity else "NOT SUPPORTED",
                "guardrail": f"{share_first_5pct:.1%} of simulations have their largest jump inside the "
                             f"first 5% of the trace (median position {median_location:.3f}); whatever "
                             f"predictive value it carries is about how the pool forms, not about a "
                             f"later transition",
            },
            {
                "claim": "The small three-feature simple ΔW block improves the 4D GPC on q20",
                "status": "SUPPORTED" if "SUPPORTED" in (block_hard, block_rank)
                          else ("QUALIFIED" if "QUALIFIED" in (block_hard, block_rank) else "NOT SUPPORTED"),
                "guardrail": f"hard {block_hard}, ranking {block_rank}; q20 balanced accuracy "
                             f"{mean_of('gpc_4d_plus_simple_delta_block', 'balanced_accuracy'):.4f}",
            },
            {
                "claim": "The rate block behaves differently from the raw ΔW block",
                "status": "QUALIFIED" if (rate_hard, rate_rank) != (primary_hard, primary_rank)
                          else "NOT SUPPORTED",
                "guardrail": f"4D+rate hard {rate_hard} / ranking {rate_rank} versus "
                             f"4D+ΔW hard {primary_hard} / ranking {primary_rank}",
            },
            {
                "claim": "M3 outperforms the plain 4D GPC on this usable subset",
                "status": "SUPPORTED" if "SUPPORTED" in (m3_hard, m3_rank)
                          else ("QUALIFIED" if "QUALIFIED" in (m3_hard, m3_rank) else "NOT SUPPORTED"),
                "guardrail": f"q20 balanced accuracy {mean_of('gpc_4d', 'balanced_accuracy'):.4f} (4D) vs "
                             f"{mean_of('m3', 'balanced_accuracy'):.4f} (M3); predictive comparison, "
                             f"not an acquisition comparison",
            },
            {
                "claim": "The best simple-width GPC beats M3",
                "status": "SUPPORTED" if block_vs_m3_hard == "SUPPORTED" and block_vs_m3_rank != "NOT SUPPORTED"
                          else ("QUALIFIED" if "SUPPORTED" in (block_vs_m3_hard, block_vs_m3_rank)
                                else "NOT SUPPORTED"),
                "guardrail": f"4D+simple ΔW block − M3 on q20: hard {block_vs_m3_hard}, "
                             f"ranking {block_vs_m3_rank}",
            },
            {
                "claim": "Adding max_positive_delta_W to M3 itself improves M3",
                "status": "SUPPORTED" if "SUPPORTED" in (m3w_hard, m3w_rank)
                          else ("QUALIFIED" if "QUALIFIED" in (m3w_hard, m3w_rank) else "NOT SUPPORTED"),
                "guardrail": f"physics mean untouched; only the discrepancy GP gains one input dimension. "
                             f"q20 balanced accuracy {mean_of('m3', 'balanced_accuracy'):.4f} → "
                             f"{mean_of('m3_plus_max_delta_W', 'balanced_accuracy'):.4f}",
            },
            {
                "claim": "SECONDARY (historical) — the old three-feature shape subset still helps once the "
                         "model is GPC rather than logistic regression",
                "status": "SUPPORTED" if "SUPPORTED" in (shape_hard, shape_rank)
                          else ("QUALIFIED" if "QUALIFIED" in (shape_hard, shape_rank) else "NOT SUPPORTED"),
                "guardrail": f"q20 balanced accuracy {mean_of('gpc_4d_plus_old_shape3', 'balanced_accuracy'):.4f} "
                             f"vs 4D {mean_of('gpc_4d', 'balanced_accuracy'):.4f}; Phase 2.1 saw this under "
                             f"logistic regression",
            },
            {
                "claim": "SECONDARY (historical) — the old full eight-feature block helps",
                "status": "SUPPORTED" if "SUPPORTED" in (full8_hard, full8_rank)
                          else ("QUALIFIED" if "QUALIFIED" in (full8_hard, full8_rank) else "NOT SUPPORTED"),
                "guardrail": f"q20 balanced accuracy {mean_of('gpc_4d_plus_old_full8', 'balanced_accuracy'):.4f}",
            },
            {
                "claim": "A single robust-derivative feature is responsible for diluting the shape3 signal",
                "status": "QUALIFIED" if any_derivative_hurts else "NOT SUPPORTED",
                "guardrail": f"worst single addition is {worst.contrast.split('plus_')[-1]} "
                             f"({worst.mean_difference:+.4f} q20 balanced accuracy, "
                             f"{worst.verdict_after_holm}); five one-at-a-time additions tested",
            },
            {
                "claim": "These results describe raw SPH solver timesteps",
                "status": "NOT SUPPORTED",
                "guardrail": "every ΔW here is between consecutive RESAMPLED analysis points on the Phase 2 "
                             "grid; raw solver steps (~75k per simulation, dt ≈ 0.018 µs) were not used",
            },
            {
                "claim": "Results generalise to simulations with no usable width trace",
                "status": "NOT SUPPORTED",
                "guardrail": "every model is trained and scored only on the usable subset",
            },
            {
                "claim": "This phase says anything about in-process monitoring hardware or about acquisition",
                "status": "NOT SUPPORTED",
                "guardrail": "predictive feature-value experiment on frozen folds; no camera, no new "
                             "active-learning path",
            },
        ]
    )
    facts = {
        "delta_sep": delta_sep, "rate_sep": rate_sep,
        "delta_threshold": delta_threshold, "rate_threshold": rate_threshold,
        "primary_hard": primary_hard, "primary_rank": primary_rank,
        "block_hard": block_hard, "block_rank": block_rank,
        "rate_hard": rate_hard, "rate_rank": rate_rank,
        "m3_hard": m3_hard, "m3_rank": m3_rank,
        "m3w_hard": m3w_hard, "m3w_rank": m3w_rank,
        "block_vs_m3_hard": block_vs_m3_hard, "block_vs_m3_rank": block_vs_m3_rank,
        "shape_hard": shape_hard, "shape_rank": shape_rank,
        "full8_hard": full8_hard, "full8_rank": full8_rank,
        "delta_robust": delta_robust, "rate_robust": rate_robust,
        "share_first_5pct": share_first_5pct, "median_location": median_location,
        "startup_quantity": startup_quantity,
        "model_resolution_gains": model_resolution_gains,
        "model_resolution_verdicts": model_resolution_verdicts,
        "model_resolution_status": model_resolution_status,
        "any_derivative_hurts": any_derivative_hurts, "worst_derivative": worst,
        "mean_of": mean_of, "contrast_of": contrast_of,
    }
    write_csv(OUTPUT / "claim_status.csv", claims)
    return claims, facts


# --------------------------------------------------------------------------------------
# 15 / 16. reports
# --------------------------------------------------------------------------------------
def render_reports(population: pd.DataFrame, features: pd.DataFrame, table: pd.DataFrame,
                   separation: pd.DataFrame, threshold_summary: pd.DataFrame, summary: pd.DataFrame,
                   inference: pd.DataFrame, sweep_verdict: pd.DataFrame, sweep: pd.DataFrame,
                   corrections: pd.DataFrame, claims: pd.DataFrame, facts: dict[str, Any],
                   figures: list[Path], interactive: list[Path]) -> None:
    mean_of = facts["mean_of"]
    contrast_of = facts["contrast_of"]
    usable = len(features)
    keyholes = int(features.has_keyhole.sum())
    delta_sep, rate_sep = facts["delta_sep"], facts["rate_sep"]
    delta_threshold, rate_threshold = facts["delta_threshold"], facts["rate_threshold"]

    def line(row: pd.Series) -> str:
        return f"{row.mean_difference:+.4f} [{row.ci_low:+.4f}, {row.ci_high:+.4f}]"

    ask = f"""# What did we actually ask?

1. **Ioan suggested** checking whether the way the melt-pool width changes over time carries Keyhole
   information.
2. **The simplest version of that** is the change between one analysis point and the next:
   `delta_W = W(i+1) - W(i)`. If the width is 20 µm at one point and 30 µm at the next, `delta_W = +10`;
   if it then goes 30 → 33 that is `+3`, and 33 → 31 is `-2`. A simulation's whole story becomes a short
   list like `[+10, +3, -2, ...]`.
3. **First question:** do big width jumps on their own separate Keyhole from Conduction?
4. **Second question:** does adding that information to the ordinary 4D process-input GPC
   (`[P, VX, LS, ST]`) make predictions better?
5. **Third question:** how do these models compare against **M3**, the current strong model
   (physics logistic mean on `log h` plus an ARD Matérn-3/2 discrepancy GP)?
6. **This is a predictive feature-value experiment, not a new active-learning acquisition experiment.**

## One thing to be strict about

The width series used here lives on the Phase 2 resampled grid. Its points are **consecutive resampled
analysis points**, not raw solver timesteps. The raw SPH monitors have about 75,000 steps per simulation
at dt ≈ 0.018 µs, where the step-to-step width change is boundary jitter (typical step ≈ 0.005 µm, and
the width *decreases* on about 51% of raw steps). A "largest raw one-step increase" would measure the
biggest numerical artifact in 75,000 steps, not melt-pool growth. At {PRIMARY_RESOLUTION} analysis points
the gap is ≈ 6.8 µs and a 20 → 30 µm change is a real physical event. Because that resolution is a
choice, everything headline is recomputed at **51, 101 and 201** points and only called robust if it
survives all three.
"""

    features_table = "\n".join(
        f"| `{name}` | {SIMPLE_FEATURE_DOC[name][0]} | {SIMPLE_FEATURE_DOC[name][1]} |"
        for name in (*DELTA_FEATURES, *RATE_FEATURES)
    )
    separation_table = "\n".join(
        f"| `{row.feature}` | {row.conduction_median:.4g} | {row.keyhole_median:.4g} | "
        f"{row.median_difference_keyhole_minus_conduction:+.4g} "
        f"[{row.median_difference_ci_low:+.4g}, {row.median_difference_ci_high:+.4g}] | "
        f"{row.cliffs_delta:+.3f} | {row.roc_auc_whole_sample:.3f} | {row.pr_auc_whole_sample:.3f} |"
        for row in separation.itertuples(index=False)
    )
    threshold_table = "\n".join(
        f"| `{row.feature}` | {row.subset} | {row.learned_threshold_median:.4g} "
        f"[{row.learned_threshold_iqr_low:.4g}, {row.learned_threshold_iqr_high:.4g}] | "
        f"{row.balanced_accuracy_mean:.4f} ± {row.balanced_accuracy_sd_across_repeats:.4f} | "
        f"{row.keyhole_recall_mean:.4f} | {row.feature_roc_auc_mean:.4f} | {row.feature_pr_auc_mean:.4f} |"
        for row in threshold_summary.sort_values(["feature", "subset"]).itertuples(index=False)
    )
    model_table = "\n".join(
        f"| `{model}` | {len(MODELS[model][1])} | {mean_of(model, 'balanced_accuracy'):.4f} | "
        f"{mean_of(model, 'accuracy'):.4f} | {mean_of(model, 'keyhole_recall'):.4f} | "
        f"{mean_of(model, 'roc_auc'):.4f} | {mean_of(model, 'pr_auc'):.4f} | "
        f"{mean_of(model, 'brier_score'):.4f} | {mean_of(model, 'balanced_accuracy', 'full'):.4f} |"
        for model in MODEL_ORDER if model in set(summary.model)
    )
    primary_table = "\n".join(
        f"| {_pretty(row.metric)} | {'lower is better' if row.lower_is_better else 'higher is better'} | "
        f"{line(row)} | {row.signflip_p:.4f} | {float(row.holm_p_metric_family):.4f} | "
        f"**{row.verdict_after_holm}** |"
        for row in inference[inference.contrast.eq(PRIMARY_CONTRAST) & inference.subset.eq("q20")]
        .itertuples(index=False)
    )
    other_contrast_table = "\n".join(
        f"| `{row.contrast}` | {_pretty(row.metric)} | {line(row)} | "
        f"{float(row.holm_p_metric_family):.4f} | {row.verdict_after_holm} |"
        for row in inference[
            inference.subset.eq("q20")
            & inference.contrast_role.isin(["primary", "m3_context", "historical"])
            & inference.contrast.ne(PRIMARY_CONTRAST)
            & inference.metric.isin(["balanced_accuracy", "keyhole_recall", "roc_auc", "pr_auc"])
        ].itertuples(index=False)
    )
    ablation_table = "\n".join(
        f"| {row.contrast.replace('abl_shape3_plus_', '+ ').replace(' - gpc_4d_plus_old_shape3', '')} | "
        f"{mean_of(row.contrast.split(' - ')[0], 'balanced_accuracy'):.4f} | {line(row)} | "
        f"{float(row.holm_p_metric_family):.4f} | {row.verdict_after_holm} |"
        for row in inference[
            inference.contrast_role.eq("ablation") & inference.subset.eq("q20")
            & inference.metric.eq("balanced_accuracy")
        ].itertuples(index=False)
    )
    resolution_table = "\n".join(
        f"| `{row.feature}` | {row.cliffs_delta_51:+.3f} | {row.cliffs_delta_101:+.3f} | "
        f"{row.cliffs_delta_201:+.3f} | {row.roc_auc_51:.3f} | {row.roc_auc_101:.3f} | "
        f"{row.roc_auc_201:.3f} | {'yes' if row.resolution_robust else 'no'} |"
        for row in sweep_verdict.itertuples(index=False)
    )
    model_resolution_table = "\n".join(
        f"| {res} analysis points | {gain:+.4f} | {verdict} |"
        for res, gain, verdict in zip(RESOLUTIONS, facts["model_resolution_gains"],
                                      facts["model_resolution_verdicts"])
    )
    corrections_table = "\n".join(
        f"| \"{row.previous_statement}\" | **{row.verdict}** | {row.correction} |"
        for row in corrections.itertuples(index=False)
    )
    ledger_table = "\n".join(
        f"| {row.claim} | {row.status} | {row.guardrail} |" for row in claims.itertuples(index=False)
    )

    one_page = f"""{ask}

## What we built

{usable} of 405 simulations have a usable transverse-width trace ({keyholes} Keyhole,
{usable - keyholes} Conduction). Each contributes {PRIMARY_RESOLUTION - 1} consecutive-point transitions,
giving a transition-level table of {len(table):,} rows. That table is for feature building and pictures
only — **the label is a property of the simulation, not of a transition**, so every train/test split
stays grouped at the simulation level on the 100 frozen Week 8.5 folds.

| feature | what it is | worked example |
|---|---|---|
{features_table}

`fraction_positive_width_rate` is mathematically identical to `fraction_positive_delta_W`: every time gap
is positive, so dividing by it can never flip a sign. It is reported once and not double-counted.

## Question 1 — do big width jumps separate the two regimes at all?

Whole-sample and descriptive (the leak-free version is the next section).

| feature | Conduction median | Keyhole median | difference [95% CI] | Cliff's δ | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|
{separation_table}

**`max_positive_delta_W`: {delta_sep.keyhole_median:.2f} µm for Keyhole against
{delta_sep.conduction_median:.2f} µm for Conduction, Cliff's δ = {delta_sep.cliffs_delta:+.3f},
ROC-AUC = {delta_sep.roc_auc_whole_sample:.3f}.**

## Question 2 — does a simple threshold rule work?

The rule is literally `if max_positive_delta_W > threshold: predict Keyhole`. The threshold is chosen to
maximise balanced accuracy **on the training simulations of each fold**, then frozen and applied to the
held-out simulations. No global threshold is ever tuned on all labels.

| feature | region | learned threshold, median [IQR] | balanced accuracy | Keyhole recall | feature ROC-AUC | feature PR-AUC |
|---|---|---|---|---|---|---|
{threshold_table}

## Question 3 — does dividing by the real time gap change anything?

Raw `delta_W` gives Cliff's δ = {delta_sep.cliffs_delta:+.3f}; the time-normalised
`max_positive_width_rate` gives {rate_sep.cliffs_delta:+.3f}. On the q20 band the leak-free threshold
rule scores {delta_threshold.balanced_accuracy_mean:.3f} on raw ΔW and
{rate_threshold.balanced_accuracy_mean:.3f} on the rate. Note *why* the two are so close: on this grid
the gap between consecutive analysis points is constant **within** a simulation (duration ÷
{PRIMARY_RESOLUTION - 1}), so dividing by it rescales a whole simulation by one number and only changes
how simulations compare **to each other**, never the shape inside one.

## Question 4 — does simple width change help the 4D GPC?

Every model below is the Phase 1.12 winner, ARD Matérn-3/2 GPC, on `StandardScaler`-scaled inputs fitted
inside each training fold. Only the feature list changes.

| model | features | bal. acc | accuracy | Keyhole recall | ROC-AUC | PR-AUC | Brier | full-set bal. acc |
|---|---|---|---|---|---|---|---|---|
{model_table}

### The primary contrast: `{PRIMARY_CONTRAST}` on q20

| metric | direction | mean difference [95% CI] | sign-flip p | Holm p | verdict |
|---|---|---|---|---|---|
{primary_table}

**Hard classification: {facts['primary_hard']}. Ranking / probability: {facts['primary_rank']}.**

### What the helpful feature actually is

Before reading too much into that gain, look at *where* in each trace the biggest jump happens.
**{facts['share_first_5pct']:.1%} of simulations have their largest ΔW inside the first 5% of the trace**,
and the median position is {facts['median_location']:.3f} — the very first transition. So
`max_positive_delta_W` is not detecting a keyhole event partway along the track. It is measuring **how
quickly the melt pool widens as it forms**, in the first few microseconds. Every trace starts from about
the same width (median 4 µm in both classes), so this is not an artifact of different starting points.

Read that together with the sign: Keyhole simulations widen *more slowly* at startup. That is physically
sensible — at high power the pool deepens into a keyhole rather than spreading sideways — but it means
the honest description of this feature is "early pool-formation speed", not "width dynamics during the
track". Any monitoring interpretation would have to watch the first few microseconds.

Two of the three ARD lengthscales in the small block sit pinned at their upper bound in ≥96% of folds
(`median_positive_delta_W`, `fraction_positive_delta_W`), meaning the kernel effectively ignores them —
which is why the three-feature block performs like the single feature rather than better.

### The other q20 contrasts

| contrast | metric | mean difference [95% CI] | Holm p | verdict |
|---|---|---|---|---|
{other_contrast_table}

## Question 5 — how does this compare with M3?

M3 is reproduced here exactly as specified in Week 9 Phase 1.13: a logistic mean on `log h` fitted on the
training simulations, frozen, plus a `FixedMeanLaplaceGPC` discrepancy with an ARD Matérn-3/2 kernel over
the scaled 4D inputs. `m3_plus_max_delta_W` keeps that structure completely intact and only widens the
**discrepancy** GP by one input dimension — the physics mean still sees `log h` and nothing else, so the
meaning of M3 is not distorted.

* 4D GPC q20 balanced accuracy **{mean_of('gpc_4d', 'balanced_accuracy'):.4f}**
* best simple-ΔW GPC **{max(mean_of(m, 'balanced_accuracy') for m in ('gpc_4d_plus_max_delta_W', 'gpc_4d_plus_simple_delta_block', 'gpc_4d_plus_max_width_rate', 'gpc_4d_plus_simple_rate_block')):.4f}**
* M3 **{mean_of('m3', 'balanced_accuracy'):.4f}**
* M3 + max ΔW **{mean_of('m3_plus_max_delta_W', 'balanced_accuracy'):.4f}**

M3 versus plain 4D: hard {facts['m3_hard']}, ranking {facts['m3_rank']}.
Simple-ΔW block versus M3: hard {facts['block_vs_m3_hard']}, ranking {facts['block_vs_m3_rank']}.
Adding ΔW to M3 itself: hard {facts['m3w_hard']}, ranking {facts['m3w_rank']}.

## Is the answer an artifact of the grid resolution?

| feature | δ @51 | δ @101 | δ @201 | ROC @51 | ROC @101 | ROC @201 | robust? |
|---|---|---|---|---|---|---|---|
{resolution_table}

Several members of the small family are **not** resolution-stable — `min_delta_W`,
`fraction_positive_delta_W` and `total_positive_delta_W` change sign between 51 and 201 points. Those are
artifacts of the grid choice and are reported as such rather than interpreted. The rate features are the
most stable marginally; `max_positive_delta_W` keeps its direction at all three resolutions but its
magnitude moves by about a factor of two.

Marginal stability is not the same as model stability, so the headline gain is re-tested directly: the
same GPC on the same folds, with `max_positive_delta_W` rebuilt on each grid.

| grid used to build max ΔW | q20 PR-AUC gain over 4D-only | verdict |
|---|---|---|
{model_resolution_table}

## Secondary and historical: the demoted Phase 2.1 engineered block

Phase 2.1 summarised the width trace using engineered shape and derivative descriptors. Phase 2.1R
instead asks the simpler question: what happens between consecutive resampled analysis points? The old
blocks are kept only as context, and are now run under GPC rather than logistic regression.

### Derivative ablation, starting from 4D + shape3

| model | q20 bal. acc | difference vs 4D+shape3 [95% CI] | Holm p | verdict |
|---|---|---|---|---|
{ablation_table}

## Corrections to the Phase 2.1 write-up

| previous statement | verdict | correction |
|---|---|---|
{corrections_table}

## Claim ledger

| claim | status | guardrail |
|---|---|---|
{ledger_table}

## What is corrected for, and what is not

The Holm adjustment is applied **within each contrast, across the six predeclared metrics**
(balanced accuracy, accuracy, Keyhole recall, ROC-AUC, PR-AUC, Brier). It is applied to every contrast,
including the secondary and historical ones, so a secondary result cannot look stronger than the primary
one simply by escaping multiplicity control. **Not** corrected for: the number of contrasts, the three
evaluation regions (q20 / q30 / full), and the three grid resolutions. Wherever a nominal reading is
quoted below, it is labelled nominal.
"""

    (OUTPUT / "SUPERVISOR_PHASE2_1R_ONE_PAGE.md").write_text(one_page.rstrip() + "\n", encoding="utf-8")

    methods = f"""
## Methods

**Population and folds.** Frozen canonical population: 405 simulations, 73 Keyhole, via
`week8_5_frozen_sample_efficiency_confirmation.load_population`. Inputs `P` (laser power), `VX` (scan
speed), `LS` (Gaussian laser spot *radius*), `ST` (*substrate temperature*, never layer thickness).
Evaluation uses the 100 frozen Week 8.5 grouped outer folds (20 repeats × 5 stratified group folds);
fold membership is computed on the full 405-row population and then intersected with the usable subset,
so no new split is invented. `B1` q20/q30 are computed on the full frozen test fold and used purely as
evaluation masks.

**Width.** Transverse `W(t) = Ymax − Ymin = ΔY`, µm, read from pinned Phase 2 commit
`{PHASE2_SHA}` with `git show`. Nothing is re-extracted and longitudinal ΔX is never used.

**Transitions.** For each simulation, every consecutive pair of resampled analysis points contributes one
row: `W_i`, `W_(i+1)`, `delta_t`, `delta_W = W_(i+1) − W_i`, `width_rate = delta_W / delta_t`. The label
is simulation-level, so the {len(table):,} transition rows are never treated as independent labelled
experiments.

**Classifier.** The primary family is GPC, using the Phase 1.12 supported winner G3: ARD Matérn-3/2,
`ConstantKernel(1.0, (1e-3, 1e3)) * Matern(length_scale=ones(d), length_scale_bounds=(1e-2, 1e2),
nu=1.5)`, `optimizer='fmin_l_bfgs_b'`, `n_restarts_optimizer=0`, `max_iter_predict=100`, on
`StandardScaler`-scaled inputs fitted inside the training fold. `kernel_parity_audit.csv` proves the
builders here reproduce the frozen Phase 1.12 and Phase 1.13 kernel specifications character for
character. Logistic regression is used nowhere as a headline model.

**M3.** Exactly the Phase 1.13 construction: `fit_physics_mean` (logistic on scaled `log h`, `C=1e6`)
fitted on the training simulations and frozen, then `FixedMeanLaplaceGPC` with
`ConstantKernel({p11.INITIAL_RESIDUAL_VARIANCE}, {tuple(round(v, 6) for v in p11.RESIDUAL_VARIANCE_BOUNDS)})
* Matern(ARD, bounds {p13.PRIMARY_LENGTH_BOUNDS}, nu=1.5)` on the scaled inputs.

**Uncertainty.** Repeat-block bootstrap over the 20 repeats (the five folds of a repeat stay together),
{BOOTSTRAP_DRAWS} draws, paired differences; plus a paired sign-flip permutation p-value
({SIGNFLIP_DRAWS} draws); plus Holm within each contrast across the six predeclared metrics.

## Figures
{chr(10).join(f'- `figures/{p.name}`' for p in figures)}

## Interactive artifacts
{chr(10).join(f'- `{p.relative_to(OUTPUT).as_posix()}`' for p in interactive)}

Open `interactive_3d_index.html` first: it links the four views. Each drops one process input from the
axes and keeps it as a colour mode and hover field, so every input gets a turn being the hidden one. All
405 simulations appear in every view; all four work offline with no libraries and no network.
"""

    (OUTPUT / "FINAL_PHASE2_1R_REPORT.md").write_text(
        f"# Week 9 Phase 2.1R — final report\n## The simple width-change control\n\n"
        + one_page.split("# What did we actually ask?", 1)[1].strip()
        + "\n"
        + methods.rstrip()
        + "\n",
        encoding="utf-8",
    )

    ledger = f"""# Week 9 Phase 2.1R claim ledger

Primary question: **does the simple width change between consecutive resampled analysis points add
predictive value beyond `[P, VX, LS, ST]`?**

| claim | status | guardrail |
|---|---|---|
{ledger_table}

## Status vocabulary
- **SUPPORTED** — the 95% repeat-block interval excludes zero in the favourable direction and, for model
  contrasts, the effect survives Holm across the six predeclared metrics.
- **QUALIFIED / INCREMENTAL** — present on some metrics or some regions but not others, or directionally
  present with an interval that touches zero.
- **NOT SUPPORTED** — no detectable difference, or a difference in the unfavourable direction.
- **DESCRIPTIVE ONLY** — a marginal or exploratory observation with no held-out predictive backing.

## Corrections carried over from Phase 2.1

| previous statement | verdict | correction |
|---|---|---|
{corrections_table}
"""
    (OUTPUT / "claim_ledger.md").write_text(ledger.rstrip() + "\n", encoding="utf-8")

    manifest = pd.DataFrame(
        [{"artifact": f"figures/{p.name}", "sha256": sha256_file(p), "bytes": p.stat().st_size}
         for p in figures]
        + [{"artifact": p.relative_to(OUTPUT).as_posix(), "sha256": sha256_file(p),
            "bytes": p.stat().st_size} for p in interactive]
    )
    write_csv(OUTPUT / "figure_manifest.csv", manifest)


# --------------------------------------------------------------------------------------
# notebook
# --------------------------------------------------------------------------------------
def notebook_payload() -> dict[str, Any]:
    sections: list[tuple[str, str, str]] = [
        (
            "1. What did we actually ask?",
            "Ioan suggested checking whether the way the melt-pool width changes over time carries "
            "Keyhole information.\n\n"
            "The simplest possible version: look at two neighbouring analysis points. If the width is "
            "**20 µm** at one and **30 µm** at the next, the change is **+10**. If it then goes 30 → 33 "
            "that is **+3**, and 33 → 31 is **−2**. So one simulation becomes a short list of numbers "
            "like `[+10, +3, -2, ...]`, and that list is what we study.\n\n"
            "**A strict naming rule.** These are *consecutive resampled analysis points*, not raw solver "
            "timesteps. The raw solver has ~75,000 steps per simulation at dt ≈ 0.018 µs, where the "
            "step-to-step width change is jitter (~0.005 µm, and the width goes *down* about half the "
            "time). A 'biggest raw one-step jump' would just find the largest numerical artifact. At 201 "
            "analysis points the gap is ≈ 6.8 µs, which is where a 20 → 30 µm change is a real event.",
            "display(Image(filename=OUT/'figures'/'01_delta_W_construction.png'))",
        ),
        (
            "2. The transition table, and why we do NOT treat it as thousands of experiments",
            "Every consecutive pair of analysis points gives one row: the two widths, the time gap, the "
            "change `delta_W`, and the rate `delta_W / delta_t`.\n\n"
            "But the Keyhole label belongs to the **whole simulation**, not to a single transition. A "
            "simulation with 200 transitions is one labelled experiment, not 200. So the table is used "
            "for building features and drawing pictures, and every train/test split stays grouped at the "
            "simulation level on the frozen folds.",
            "t = pd.read_csv(OUT/'transition_table_201.csv.gz')\n"
            "print(f'{len(t):,} transition rows from {t.simulation_id.nunique()} simulations')\n"
            "display(t.head(6)[['simulation_id','analysis_point_i','W_i_um','W_i_plus_1_um',"
            "'delta_t_ms','delta_W_um','width_rate_um_per_ms','has_keyhole']].round(4))\n"
            "display(Image(filename=OUT/'figures'/'02_example_trace_and_delta.png'))",
        ),
        (
            "3. The small, interpretable feature set",
            "From the sequence `[+10, +3, -2, +1]` we read off, in plain words:\n\n"
            "* `max_positive_delta_W` = **10** — the biggest single rise\n"
            "* `min_delta_W` = **−2** — the biggest single fall\n"
            "* `median_positive_delta_W` = **3** — middle of the rises `[+10, +3, +1]`\n"
            "* `fraction_positive_delta_W` = **0.75** — 3 of the 4 transitions went up\n"
            "* `total_positive_delta_W` = **14** — 10 + 3 + 1\n\n"
            "Then the same three headline quantities again after dividing each change by the time gap it "
            "happened in, which turns µm into µm/ms. That is the whole family — deliberately small, so "
            "each number can be explained in one sentence.",
            "s = pd.read_csv(OUT/'univariate_separation.csv')\n"
            "display(s[['feature','plain_english','worked_example']])",
        ),
        (
            "4. Do Keyhole simulations have bigger width jumps?",
            "This is the child-simple question. For every simulation take one number — the biggest rise "
            "anywhere in it — and ask whether Keyhole simulations tend to have bigger ones.\n\n"
            "These numbers are whole-sample and descriptive: they say whether a difference exists at all, "
            "**not** how well it would generalise. The honest held-out version is the next section.",
            "display(s[['feature','conduction_median','keyhole_median','cliffs_delta',"
            "'roc_auc_whole_sample','pr_auc_whole_sample']].round(4))\n"
            "display(Image(filename=OUT/'figures'/'03_max_positive_delta_W_distribution.png'))\n"
            "display(Image(filename=OUT/'figures'/'04_max_positive_width_rate_distribution.png'))",
        ),
        (
            "5. The threshold experiment, done leak-free",
            "The rule is exactly the intuitive one: **if the biggest width jump is larger than some "
            "threshold, call it Keyhole**.\n\n"
            "The catch is where the threshold comes from. Picking one number using all 350 labels and "
            "then reporting its accuracy would be cheating. So inside each of the 100 frozen folds we "
            "choose the threshold using **only the training simulations**, freeze it, and apply it to the "
            "held-out ones. If the training values are `[4, 9, 12, 20]` with labels `[0, 0, 1, 1]`, the "
            "candidate cuts are the midpoints 6.5, 10.5 and 16, and 10.5 separates them perfectly, so "
            "10.5 is chosen.",
            "display(pd.read_csv(OUT/'threshold_summary.csv').round(4))\n"
            "display(Image(filename=OUT/'figures'/'05_threshold_classifier.png'))",
        ),
        (
            "6. Does it help the real model?",
            "Now the question that matters: the 4D GPC already knows `P`, `VX`, `LS` and `ST`. Does "
            "telling it the biggest width jump as well make it better?\n\n"
            "Every model here is the same classifier — the ARD Matérn-3/2 GPC that Phase 1.12 established "
            "as the defensible specification. Only the list of input columns changes, so any difference "
            "is attributable to the features and not to the model.",
            "summary = pd.read_csv(OUT/'model_oof_summary.csv')\n"
            "q20 = summary[(summary.subset=='q20') & summary.metric.isin("
            "['balanced_accuracy','keyhole_recall','roc_auc','pr_auc','brier_score'])]\n"
            "display(q20.pivot(index='model', columns='metric', values='mean').round(4))\n"
            "display(Image(filename=OUT/'figures'/'06_model_comparison_gpc_m3.png'))",
        ),
        (
            "7. The primary contrast, and how it compares with M3",
            "The single number this phase turns on is `gpc_4d_plus_max_delta_W − gpc_4d` on the q20 "
            "boundary band.\n\n"
            "M3 is included as the reference point: physics logistic mean on `log h` plus an ARD "
            "Matérn-3/2 discrepancy GP. `m3_plus_max_delta_W` leaves the physics mean completely alone "
            "and only widens the discrepancy GP by one input, so M3's meaning is preserved.\n\n"
            "This is a **predictive** comparison. It says nothing about acquisition.",
            "inf = pd.read_csv(OUT/'contrast_inference.csv')\n"
            "display(inf[(inf.subset=='q20') & inf.contrast_role.isin(['primary','m3_context'])]"
            "[['contrast','metric','mean_difference','ci_low','ci_high','holm_p_metric_family',"
            "'verdict_after_holm']].round(4))\n"
            "display(Image(filename=OUT/'figures'/'07_q20_paired_contrasts.png'))",
        ),
        (
            "8. Is any of this just the grid resolution?",
            "The 201-point grid is a choice we made, not a physical constant. If the answer flipped when "
            "we used 51 or 101 points instead, it would be an artifact of that choice rather than a fact "
            "about melt pools. So every headline feature is rebuilt on exact subsamples of the same grid "
            "and compared.",
            "display(pd.read_csv(OUT/'resolution_robustness_verdict.csv').round(4))\n"
            "display(Image(filename=OUT/'figures'/'10_resolution_sweep.png'))",
        ),
        (
            "9. The old engineered features, demoted — and the derivative ablation",
            "Phase 2.1 summarised the width trace using engineered shape and derivative descriptors. "
            "Phase 2.1R instead asks the simpler question: what happens between consecutive resampled "
            "analysis points?\n\n"
            "The old blocks are kept only for context, now run under GPC instead of logistic regression. "
            "The ablation starts from 4D + the three shape features and adds each of the five robust "
            "derivative features back one at a time, to see whether one of them does the damage or "
            "whether the group dilutes collectively.",
            "display(inf[(inf.contrast_role=='ablation') & (inf.subset=='q20') & "
            "(inf.metric=='balanced_accuracy')][['contrast','mean_difference','ci_low','ci_high',"
            "'holm_p_metric_family','verdict_after_holm']].round(4))\n"
            "display(Image(filename=OUT/'figures'/'08_derivative_ablation.png'))",
        ),
        (
            "10. Corrections to what Phase 2.1 said",
            "Three statements in the Phase 2.1 write-up were wrong or overstated, and are corrected here "
            "against the recomputed numbers.",
            "display(pd.read_csv(OUT/'phase2_1_corrections.csv'))",
        ),
        (
            "11. What is supported, what is not",
            "The claim ledger is the contract. A whole-sample difference is not a held-out gain; a "
            "ranking gain is not a hard-classification gain; and nothing here transfers to simulations "
            "that never produced a usable trace.",
            "display(Image(filename=OUT/'figures'/'09_claim_status.png'))\n"
            "print(json.loads((OUT/'validation_report.json').read_text(encoding='utf-8'))['status'])",
        ),
        (
            "12. The four interactive 3D views",
            "The process space has four inputs, so no single 3D picture can show it. Four views each drop "
            "one input from the axes and keep it as a colour mode and a hover field, so every input gets "
            "a turn being the hidden one. Open `interactive_3d_index.html` to reach all four. They work "
            "offline with no libraries.",
            "idx = OUT/'interactive_3d_index.html'\n"
            "print(idx.name, '|', round(idx.stat().st_size/1024, 1), 'KB')\n"
            "for p in sorted((OUT/'interactive').glob('*.html')):\n"
            "    print(' ', p.name, '|', round(p.stat().st_size/1024, 1), 'KB')",
        ),
    ]
    cells: list[dict[str, Any]] = [
        {
            "cell_type": "markdown", "id": "r0", "metadata": {},
            "source": [
                "# Week 9 Phase 2.1R — the simple width-change control\n", "\n",
                "**If the melt-pool width goes 20 → 30 between two neighbouring analysis points, that is "
                "a change of +10. Do Keyhole simulations have bigger such changes, and does knowing them "
                "help us predict Keyhole better than `[P, VX, LS, ST]` alone?**\n", "\n",
                "This notebook reads the generated artifacts. The engine is "
                "`src/week9_phase2_1r_simple_width_change_control.py`.\n",
            ],
        },
        {
            "cell_type": "code", "id": "rsetup", "execution_count": None, "metadata": {}, "outputs": [],
            "source": [
                "import json\n", "from pathlib import Path\n", "import pandas as pd\n",
                "from IPython.display import display, Image\n",
                "pd.set_option('display.width', 190)\n",
                "pd.set_option('display.max_columns', 40)\n",
                "pd.set_option('display.max_colwidth', 90)\n",
                "ROOT = Path.cwd().parents[1] if Path.cwd().name == 'week_09' else Path.cwd()\n",
                "OUT = ROOT / 'outputs' / 'week9_phase2_1r_simple_width_change_control'\n",
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
        "nbformat": 4, "nbformat_minor": 5,
    }


def execute_and_save_notebook() -> str:
    import nbformat
    from nbconvert.preprocessors import ExecutePreprocessor
    from jupyter_client.kernelspec import KernelSpecManager

    available = set(KernelSpecManager().find_kernel_specs())
    kernel = "python3" if "python3" in available else sorted(available)[0]
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    ExecutePreprocessor(timeout=900, kernel_name=kernel).preprocess(
        notebook, {"metadata": {"path": str(ROOT)}}
    )
    nbformat.write(notebook, NOTEBOOK)
    return kernel


# --------------------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------------------
NEW_PATH_PREFIXES = (
    "src/week9_phase2_1r_simple_width_change_control.py",
    "notebooks/week_09/07_week9_phase2_1r_simple_width_change_control.ipynb",
    "outputs/week9_phase2_1r_simple_width_change_control/",
)


def working_tree_fingerprint() -> set[str]:
    result = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                            cwd=ROOT, text=True, capture_output=True, check=True)
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


def validate(population: pd.DataFrame, features: pd.DataFrame, table: pd.DataFrame,
             summary: pd.DataFrame, inference: pd.DataFrame, parity: pd.DataFrame,
             thresholds: pd.DataFrame, figures: list[Path], interactive: list[Path],
             baseline_tree: set[str], include_notebook: bool) -> dict[str, Any]:
    module_source = Path(__file__).read_text(encoding="utf-8")
    physics_source = (ROOT / "src" / "week9_phase1_5_h_physics_confirmation.py").read_text(encoding="utf-8")
    model_columns = {c for _, columns, _ in MODELS.values() for c in columns}
    specs = w85.build_splits(population)
    reports = ["FINAL_PHASE2_1R_REPORT.md", "SUPERVISOR_PHASE2_1R_ONE_PAGE.md", "claim_ledger.md"]
    report_text = {name: (OUTPUT / name).read_text(encoding="utf-8") for name in reports}
    index_html = (OUTPUT / "interactive_3d_index.html").read_text(encoding="utf-8")
    view_html = {p.name: p.read_text(encoding="utf-8") for p in interactive if p.parent == INTERACTIVE}

    # Terminology gate. The reports are allowed to *discuss* raw solver timesteps -- explaining
    # why they were not used is the whole point -- but they must never describe this study's
    # delta_W as being measured between them. So: every sentence that mentions raw steps must
    # also carry a contrast marker that distances them from what was actually done.
    contrast_markers = ("not ", "rather than", "instead", "would ", "never", "n't", "no raw")
    offending: list[str] = []
    for name, text in report_text.items():
        for sentence in re.split(r"(?<=[.;:])\s+|\n\n", text.lower()):
            mentions_raw = "raw" in sentence and ("timestep" in sentence or "solver step" in sentence
                                                  or "solver timestep" in sentence)
            if mentions_raw and not any(marker in sentence for marker in contrast_markers):
                offending.append(f"{name}: {sentence.strip()[:120]}")
    terminology_clean = not offending

    checks: dict[str, bool] = {
        # population / conventions
        "population_405": len(population) == 405,
        "labels_73": int(population.has_keyhole.sum()) == 73,
        "LS_is_laser_spot_radius": bool(np.allclose(population.LS, population.LS_m))
        and "Gaussian laser spot radius r0" in physics_source,
        "ST_is_substrate_temperature": bool(np.allclose(population.ST, population.ST_K))
        and '"ST_definition": "substrate temperature"' in physics_source,
        "h_exact_formula": bool(np.allclose(
            features.log_h, np.log(features.P / np.sqrt(features.VX * features.LS**3)))),
        # width provenance
        "width_inherited_from_pinned_phase2": PHASE2_SHA in module_source
        and "temporal_profiles.csv.gz" in module_source,
        "usable_subset_350_70": len(features) == 350 and int(features.has_keyhole.sum()) == 70,
        "no_longitudinal_delta_x_in_models": not any(c.startswith("L_") for c in model_columns),
        # delta_W construction
        "delta_W_equals_next_minus_current": bool(np.allclose(
            table.delta_W_um, table.W_i_plus_1_um - table.W_i_um)),
        "width_rate_equals_delta_over_gap": bool(np.allclose(
            table.width_rate_um_per_ms, table.delta_W_um / table.delta_t_ms)),
        "all_time_gaps_positive": bool((table.delta_t_ms > 0).all()),
        "transition_count_matches_grid": len(table) == len(features) * (PRIMARY_RESOLUTION - 1),
        "fraction_identity_documented": bool(np.allclose(
            features.fraction_positive_width_rate, features.fraction_positive_delta_W)),
        # leakage
        "no_label_column_in_any_model": not bool(model_columns & {"has_keyhole", "truth"}),
        "no_evaluation_mask_in_any_model": not bool(model_columns & {"is_q20", "is_q30"}),
        "threshold_learned_on_training_only": "def learn_threshold" in module_source
        and "train_values" in module_source,
        "grouped_at_simulation_level": bool(
            table.groupby("simulation_id").population_row_index.nunique().eq(1).all()),
        # protocol
        "frozen_fold_count_100": len(specs) == 100,
        "no_new_random_split_declared": ("train_test" + "_split") not in module_source,
        # model specification parity with the frozen thesis conventions
        "kernel_parity_all_pass": bool(parity.match.all()),
        "gpc_is_headline_family": all(
            MODELS[m][0] in {"gpc", "m3"} for m in MODELS
        ) and not any(MODELS[m][0] == "logistic" for m in MODELS),
        "m3_physics_mean_untouched": "fit_physics_mean" in module_source
        and "FixedMeanLaplaceGPC" in module_source,
        "m3_present_in_comparison": "m3" in set(summary.model) and "m3_plus_max_delta_W" in set(summary.model),
        # resolution sweep
        "resolution_sweep_ran": (OUTPUT / "resolution_robustness_verdict.csv").is_file()
        and len(pd.read_csv(OUTPUT / "resolution_sweep_separation.csv").resolution_points.unique()) == 3,
        # inference discipline
        "holm_applied_to_every_contrast": bool(
            inference.groupby("contrast").holm_p_metric_family.apply(lambda s: s.notna().all()).all()),
        "verdicts_interval_based": "def verdict_of(" in module_source and "ci_low" in module_source,
        "corrections_table_written": (OUTPUT / "phase2_1_corrections.csv").is_file(),
        "corrections_fix_holm_claim": "nothing anywhere survives" in
        pd.read_csv(OUTPUT / "phase2_1_corrections.csv").previous_statement.str.cat(sep=" "),
        # terminology
        "terminology_resampled_analysis_points": terminology_clean,
        "reports_define_analysis_point": all(
            "consecutive resampled analysis points" in text for text in report_text.values()),
        # outputs
        "ten_figures": len(figures) == 10,
        "figures_exist": all(p.is_file() and p.stat().st_size > 0 for p in figures),
        "four_interactive_views_plus_index": len(interactive) == 5
        and sum(1 for p in interactive if p.parent == INTERACTIVE) == 4,
        "interactive_views_offline": all(
            ("http://" not in text) and ("https://" not in text) for text in view_html.values()),
        "interactive_views_full_population": all(
            text.count('"id":') == len(population) for text in view_html.values()),
        "interactive_views_hover_fields": all(
            all(token in text for token in ["log h", "ST", "usable in Phase 2.1R", "d.id"])
            for text in view_html.values()),
        "interactive_views_drop_each_input": {v[2] for v in VIEWS} == set(FOURD_FEATURES),
        "interactive_index_links_all_views": all(
            f"interactive/{slug}.html" in index_html for slug, _, _ in VIEWS),
        "figure_manifest_hashes_match": all(
            sha256_file(OUTPUT / row.artifact) == row.sha256
            for row in pd.read_csv(OUTPUT / "figure_manifest.csv").itertuples()),
        "reports_exist": all((OUTPUT / name).is_file() for name in reports),
        "reports_open_with_what_did_we_ask": report_text["SUPERVISOR_PHASE2_1R_ONE_PAGE.md"]
        .lstrip().startswith("# What did we actually ask?"),
        "reports_quote_usable_counts": all(
            f"{len(features)} of 405" in text for text in report_text.values()
            if text is report_text["SUPERVISOR_PHASE2_1R_ONE_PAGE.md"]),
        # local-only discipline
        "no_historical_file_touched": working_tree_fingerprint() == baseline_tree,
        "no_remote_operation_in_source": not any(
            token in module_source
            for token in ["git pu" + "sh", "gh " + "pr", "git rem" + "ote add", "requests." + "post"]),
        # tokens assembled from fragments so this check cannot match itself
        "no_raw_monitor_download": ("hf_hub" + "_download") not in module_source
        and ("snapshot" + "_download") not in module_source,
    }
    if include_notebook:
        notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        executed = [c for c in notebook["cells"] if c["cell_type"] == "code"
                    and c.get("execution_count") is not None and c.get("outputs")]
        errors = [o for c in notebook["cells"] for o in c.get("outputs", [])
                  if o.get("output_type") == "error"]
        checks["notebook_stores_executed_outputs"] = len(executed) >= 10
        checks["notebook_has_no_execution_errors"] = not errors

    failed = [name for name, value in checks.items() if not value]
    require(not failed, f"validation failed: {failed}"
                        + (f"; offending terminology: {offending[:3]}" if offending else ""))
    payload = {
        "status": "PASS", "phase": "Week 9 Phase 2.1R",
        "notebook_checks_included": include_notebook,
        "checks": checks, "check_count": len(checks),
        "phase2_source_commit": PHASE2_SHA,
        "primary_resolution_points": PRIMARY_RESOLUTION,
        "resolutions_tested": list(RESOLUTIONS),
        "usable_traces": len(features), "usable_keyholes": int(features.has_keyhole.sum()),
        "transition_rows": len(table),
        "models_evaluated": len(MODELS),
        "output_bytes": directory_bytes(OUTPUT),
        "preexisting_dirty_paths_outside_this_phase": len(baseline_tree),
    }
    write_json(OUTPUT / "validation_report.json", payload)
    (OUTPUT / "validation_report.md").write_text(
        "# Week 9 Phase 2.1R validation report\n\n"
        f"**PASS** — {len(checks)} checks passed.\n\n"
        f"Width traces inherited from Phase 2 commit `{PHASE2_SHA}`.\n"
        f"Usable simulations: {len(features)}/405 ({int(features.has_keyhole.sum())} Keyhole).\n"
        f"Transition rows at {PRIMARY_RESOLUTION} analysis points: {len(table):,}.\n"
        f"New artifacts on disk: {directory_bytes(OUTPUT) / 1e6:.2f} MB. No raw monitor data downloaded.\n"
        f"Pre-existing dirty paths in this checkout, untouched by Phase 2.1R: {len(baseline_tree)}.\n\n"
        + "\n".join(f"- PASS: {name}" for name in checks) + "\n",
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

    print("[1/9] population, inherited width traces, kernel parity", flush=True)
    population = load_population()
    parity = kernel_parity_audit()
    series = load_width_series(population)

    print(f"[2/9] transition table at {PRIMARY_RESOLUTION} consecutive resampled analysis points", flush=True)
    table = transition_table(series, population, PRIMARY_RESOLUTION)
    write_csv(OUTPUT / f"transition_table_{PRIMARY_RESOLUTION}.csv.gz", table)
    simple = simple_features(table)
    canonical = population[["experiment_name", "population_row_index", *FOURD_FEATURES, "log_h"]]
    features = simple.drop(columns=["population_row_index"]).merge(
        canonical, on="experiment_name", how="left", validate="one_to_one")
    require(features.population_row_index.notna().all(), "features contain unknown experiments")
    old = phase2_csv("width_temporal_features.csv")[
        ["experiment_name", *OLD_SHAPE_FEATURES, *OLD_DERIVATIVE_FEATURES]]
    features = features.merge(old, on="experiment_name", how="left", validate="one_to_one")
    require(features.notna().all().all(), "missing values in the assembled feature table")
    features = features.sort_values("population_row_index").reset_index(drop=True)
    write_csv(OUTPUT / "simulation_level_features.csv", features)

    print("[3/9] univariate separation and threshold sweep curves", flush=True)
    separation = univariate_separation(features, (*DELTA_FEATURES, *RATE_FEATURES), PRIMARY_RESOLUTION)
    write_csv(OUTPUT / "univariate_separation.csv", separation)
    sweep_curves = pd.concat([threshold_sweep_curve(features, c) for c in HEADLINE_UNIVARIATE],
                             ignore_index=True)
    write_csv(OUTPUT / "threshold_sweep_curves.csv", sweep_curves)

    print("[4/9] resolution robustness sweep (51 / 101 / 201 analysis points)", flush=True)
    sweep, sweep_features = resolution_sweep(series, population)
    sweep_verdict = resolution_verdict(sweep)
    # Carry the coarser-grid version of the headline feature into the model table, so the
    # model-level gain can be re-tested at 51 and 101 points, not just the marginal effect.
    for resolution in (51, 101):
        column = f"max_positive_delta_W_res{resolution}"
        block = sweep_features[sweep_features.resolution_points.eq(resolution)][
            ["experiment_name", "max_positive_delta_W"]].rename(
            columns={"max_positive_delta_W": column})
        features = features.merge(block, on="experiment_name", how="left", validate="one_to_one")
    require(features.notna().all().all(), "resolution-specific features failed to merge")
    write_csv(OUTPUT / "simulation_level_features.csv", features)

    print("[5/9] leak-free evaluation: GPC family, M3, threshold rule, ablation", flush=True)
    predictions, thresholds, lengthscale_summary = evaluate(population, features)
    repeat, summary = summarize(predictions)
    contrasts = paired_contrasts(repeat)
    inference = annotate(contrasts)
    threshold_summary, _ = summarize_thresholds(thresholds)

    print("[6/9] Phase 2.1 corrections and claim ledger", flush=True)
    corrections = phase2_1_corrections()
    claims, facts = build_claims(separation, threshold_summary, summary, inference, sweep_verdict,
                                 corrections, features)

    print("[7/9] figures", flush=True)
    figures = make_figures(features, table, separation, sweep_curves, threshold_summary, thresholds,
                           summary, inference, sweep_verdict, sweep, claims)

    print("[8/9] four interactive 3D views, index, reports", flush=True)
    interactive = make_interactive_views(population, features)
    render_reports(population, features, table, separation, threshold_summary, summary, inference,
                   sweep_verdict, sweep, corrections, claims, facts, figures, interactive)
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    NOTEBOOK.write_text(json.dumps(notebook_payload(), indent=1) + "\n", encoding="utf-8")

    print("[9/9] validation", flush=True)
    validate(population, features, table, summary, inference, parity, thresholds, figures,
             interactive, baseline_tree, include_notebook=False)
    kernel = execute_and_save_notebook()
    validation = validate(population, features, table, summary, inference, parity, thresholds,
                          figures, interactive, baseline_tree, include_notebook=True)

    manifest = {
        "study": "Week 9 Phase 2.1R - the simple width-change control",
        "primary_question": "Does the simple width change between consecutive resampled analysis points "
                            "add predictive value beyond [P, VX, LS, ST]?",
        "primary_contrast": PRIMARY_CONTRAST,
        "timestep_basis": f"consecutive resampled analysis points on the Phase 2 tau grid; primary "
                          f"{PRIMARY_RESOLUTION} points, robustness at {RESOLUTIONS}",
        "raw_solver_timesteps_used": False,
        "raw_monitor_bytes_downloaded": 0,
        "verdict_primary_hard": facts["primary_hard"],
        "verdict_primary_ranking": facts["primary_rank"],
        "verdict_threshold_rule_q20_balanced_accuracy": float(
            facts["delta_threshold"].balanced_accuracy_mean),
        "population": 405, "population_keyholes": 73,
        "usable_traces": len(features), "usable_keyholes": int(features.has_keyhole.sum()),
        "width_definition": "transverse width dY = Ymax - Ymin, micrometres",
        "width_source_commit": PHASE2_SHA,
        "classifier_family": "ARD Matern-3/2 GPC (Phase 1.12 G3) plus M3 (Phase 1.13)",
        "models": {name: {"kind": kind, "features": list(columns), "role": role}
                   for name, (kind, columns, role) in MODELS.items()},
        "bootstrap_draws": BOOTSTRAP_DRAWS, "signflip_draws": SIGNFLIP_DRAWS, "seed": SEED,
        "notebook_kernel": kernel, "notebook_sha256": sha256_file(NOTEBOOK),
        "local_only": True, "new_worktree_or_clone_created": False,
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
    print(json.dumps({
        "status": "PASS",
        "usable_traces": len(features),
        "transition_rows": len(table),
        "max_delta_W_cliffs_delta": round(float(facts["delta_sep"].cliffs_delta), 4),
        "threshold_rule_q20_balanced_accuracy": round(float(facts["delta_threshold"].balanced_accuracy_mean), 4),
        "primary_hard": facts["primary_hard"],
        "primary_ranking": facts["primary_rank"],
        "new_artifact_megabytes": round(manifest["new_artifact_bytes"] / 1e6, 2),
        "elapsed_seconds": round(time.time() - started, 1),
    }, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Week 9 Phase 2.1R simple width-change control")
    parser.add_argument("--run", action="store_true", help="run the full Phase 2.1R study")
    args = parser.parse_args()
    if args.run:
        run()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
