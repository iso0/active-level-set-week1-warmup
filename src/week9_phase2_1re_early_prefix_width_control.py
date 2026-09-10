"""Week 9 Phase 2.1R-E: how early can the width signal be read?

Phase 2.1R found that adding the largest width jump to the four process inputs improves
how well the model *ranks* Keyhole risk, and that 95.4% of those largest jumps happen
inside the first 5% of the trace.  That makes the obvious follow-up question sharp:

    **If the signal is all at the start, do we need the rest of the trace at all?**

So this phase rebuilds exactly the same feature using only an opening prefix of each
simulation, and sweeps how long that prefix is.

Concrete example.  Take a simulation whose width at the first few consecutive resampled
analysis points is 4, 31, 52, 56, 63, ... um.  The changes are [+27, +21, +4, +7, ...].
If we are only allowed to watch the first 5 analysis points, we see the changes
[+27, +21, +4, +7] and record max_positive_delta_W = 27.  If we watch the whole trace we
might find a bigger jump later -- but Phase 2.1R says we almost never do.  This phase
measures what that costs.

Every prefix feature obeys a strict no-future rule: the value at prefix p uses only
transitions that end at or before analysis point ``ceil(p * (N-1))``.  A validation check
recomputes the features independently and confirms it.

TERMINOLOGY, inherited unchanged from Phase 2.1R: the points are **consecutive resampled
analysis points** on the pinned Phase 2 tau grid, never raw solver timesteps.

Two built-in audit gates make the numbers comparable to Phase 2.1R rather than merely
similar to them:

* the ``gpc_4d`` baseline here must reproduce the Phase 2.1R ``gpc_4d`` numbers exactly;
* the 100% prefix must reproduce the Phase 2.1R ``gpc_4d_plus_max_delta_W`` numbers exactly.

Run with ``python -m src.week9_phase2_1re_early_prefix_width_control --run``.
"""

from __future__ import annotations

import argparse
import hashlib
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
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, recall_score
from sklearn.preprocessing import StandardScaler

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase2_1r_simple_width_change_control as r21


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase2_1re_early_prefix_width_control"
FIGURES = OUTPUT / "figures"
NOTEBOOK = ROOT / "notebooks" / "week_09" / "08_week9_phase2_1re_early_prefix_width_control.ipynb"
PHASE21R = ROOT / "outputs" / "week9_phase2_1r_simple_width_change_control"

SEED = r21.SEED
BOOTSTRAP_DRAWS = r21.BOOTSTRAP_DRAWS
SIGNFLIP_DRAWS = r21.SIGNFLIP_DRAWS
WORKERS = 6
RESOLUTION = r21.PRIMARY_RESOLUTION
FOURD_FEATURES = r21.FOURD_FEATURES

# How much of the opening of each trace the model is allowed to see.
# 1.00 is the whole trace, i.e. exactly the Phase 2.1R feature.
PREFIXES = (0.02, 0.05, 0.10, 0.20, 0.40, 1.00)
PRIMARY_PREFIX = 0.05          # the one Phase 2.1R's 95.4% finding points at
FULL_PREFIX = 1.00

METRIC_NAMES = r21.METRIC_NAMES
PRIMARY_METRICS = r21.PRIMARY_METRICS
LOWER_IS_BETTER = r21.LOWER_IS_BETTER

require = r21.require
sha256_file = r21.sha256_file
write_csv = r21.write_csv
write_json = r21.write_json
metric_row = r21.metric_row
cliffs_delta = r21.cliffs_delta
apply_threshold = r21.apply_threshold
learn_threshold = r21.learn_threshold


def prefix_tag(prefix: float) -> str:
    """0.05 -> 'p05', 1.00 -> 'p100'. Used for column and model names."""
    return f"p{int(round(prefix * 100)):02d}"


def feature_name(prefix: float) -> str:
    return f"max_positive_delta_W_{prefix_tag(prefix)}"


def prefix_transition_count(prefix: float) -> int:
    """How many consecutive-point transitions a prefix is allowed to see."""
    return max(1, int(math.ceil(prefix * (RESOLUTION - 1))))


# --------------------------------------------------------------------------------------
# prefix features, with a strict no-future rule
# --------------------------------------------------------------------------------------
def build_prefix_features(table: pd.DataFrame, population: pd.DataFrame) -> pd.DataFrame:
    """Largest width rise seen within each opening prefix of the trace.

    Concrete: with 201 analysis points there are 200 transitions.  A 5% prefix is the
    first ``ceil(0.05 * 200) = 10`` transitions, i.e. analysis points 0..10.  The feature
    is the biggest rise among those 10 changes and nothing later is consulted.
    """
    rows: list[dict[str, Any]] = []
    for name, group in table.groupby("simulation_id", sort=True):
        group = group.sort_values("analysis_point_i")
        delta = group.delta_W_um.to_numpy(float)
        time_end = group.t_i_plus_1_ms.to_numpy(float)
        entry: dict[str, Any] = {
            "experiment_name": name,
            "population_row_index": int(group.population_row_index.iloc[0]),
            "has_keyhole": int(group.has_keyhole.iloc[0]),
            "full_trace_duration_ms": float(time_end[-1]),
        }
        for prefix in PREFIXES:
            count = prefix_transition_count(prefix)
            window = delta[:count]
            positive = window[window > 0]
            entry[feature_name(prefix)] = float(positive.max()) if len(positive) else 0.0
            entry[f"observed_ms_{prefix_tag(prefix)}"] = float(time_end[count - 1])
            entry[f"transitions_used_{prefix_tag(prefix)}"] = int(count)
        rows.append(entry)
    features = pd.DataFrame(rows)

    canonical = population[["experiment_name", *FOURD_FEATURES, "log_h"]]
    features = features.merge(canonical, on="experiment_name", how="left", validate="one_to_one")
    require(features.notna().all().all(), "prefix feature table has missing values")

    # The 100% prefix must equal the Phase 2.1R full-trace feature exactly.
    published = pd.read_csv(PHASE21R / "simulation_level_features.csv")[
        ["experiment_name", "max_positive_delta_W"]]
    check = features.merge(published, on="experiment_name", how="left", validate="one_to_one")
    difference = float(np.abs(check[feature_name(FULL_PREFIX)] - check.max_positive_delta_W).max())
    require(difference <= 1e-9, f"100% prefix does not reproduce the Phase 2.1R feature ({difference})")

    return features.sort_values("population_row_index").reset_index(drop=True)


def no_future_audit(table: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    """Independently recompute each prefix feature and prove no later point was used.

    The check is deliberately naive and written a second way: for every simulation and
    every prefix, take the raw transition rows, keep only those whose *ending* analysis
    point is within the prefix, and recompute the maximum rise from scratch.
    """
    rows = []
    indexed = {name: group.sort_values("analysis_point_i")
               for name, group in table.groupby("simulation_id", sort=True)}
    by_name = features.set_index("experiment_name")
    for prefix in PREFIXES:
        count = prefix_transition_count(prefix)
        worst_difference = 0.0
        latest_point_used = 0
        for name, group in indexed.items():
            allowed = group[group.analysis_point_i_plus_1 <= count]
            values = allowed.delta_W_um.to_numpy(float)
            positive = values[values > 0]
            recomputed = float(positive.max()) if len(positive) else 0.0
            worst_difference = max(worst_difference,
                                   abs(recomputed - float(by_name.loc[name, feature_name(prefix)])))
            latest_point_used = max(latest_point_used, int(allowed.analysis_point_i_plus_1.max()))
        rows.append(
            {
                "prefix_fraction": prefix,
                "transitions_allowed": count,
                "latest_analysis_point_used": latest_point_used,
                "no_future_point_used": latest_point_used <= count,
                "max_abs_difference_vs_independent_recompute": worst_difference,
                "median_observed_window_ms": float(
                    features[f"observed_ms_{prefix_tag(prefix)}"].median()),
                "median_observed_window_us": float(
                    features[f"observed_ms_{prefix_tag(prefix)}"].median() * 1000.0),
                "status": "PASS" if (latest_point_used <= count and worst_difference <= 1e-9) else "FAIL",
            }
        )
    audit = pd.DataFrame(rows)
    require(bool(audit.status.eq("PASS").all()), f"prefix no-future audit failed:\n{audit}")
    write_csv(OUTPUT / "prefix_no_future_audit.csv", audit)
    return audit


def saturation_profile(features: pd.DataFrame) -> pd.DataFrame:
    """How quickly does the prefix feature converge to the full-trace value?"""
    full = features[feature_name(FULL_PREFIX)].to_numpy(float)
    rows = []
    for prefix in PREFIXES:
        values = features[feature_name(prefix)].to_numpy(float)
        rows.append(
            {
                "prefix_fraction": prefix,
                "transitions_used": prefix_transition_count(prefix),
                "median_observed_window_us": float(
                    features[f"observed_ms_{prefix_tag(prefix)}"].median() * 1000.0),
                "pearson_r_with_full_trace": float(np.corrcoef(values, full)[0, 1])
                if np.std(values) > 0 else float("nan"),
                "spearman_r_with_full_trace": float(stats.spearmanr(values, full).statistic),
                "fraction_already_equal_to_full": float(np.mean(np.isclose(values, full, atol=1e-9))),
                "median_shortfall_um": float(np.median(full - values)),
                "median_ratio_to_full": float(np.median(values / np.where(full == 0, np.nan, full))),
            }
        )
    out = pd.DataFrame(rows)
    write_csv(OUTPUT / "prefix_saturation_profile.csv", out)
    return out


def univariate_by_prefix(features: pd.DataFrame) -> pd.DataFrame:
    """Marginal Keyhole/Conduction separation of the feature at each prefix."""
    rng = np.random.default_rng(SEED)
    y = features.has_keyhole.to_numpy(int)
    rows = []
    for prefix in PREFIXES:
        values = features[feature_name(prefix)].to_numpy(float)
        conduction, keyhole = values[y == 0], values[y == 1]
        boot = np.array(
            [
                np.median(rng.choice(keyhole, len(keyhole), replace=True))
                - np.median(rng.choice(conduction, len(conduction), replace=True))
                for _ in range(BOOTSTRAP_DRAWS)
            ]
        )
        rows.append(
            {
                "prefix_fraction": prefix,
                "feature": feature_name(prefix),
                "median_observed_window_us": float(
                    features[f"observed_ms_{prefix_tag(prefix)}"].median() * 1000.0),
                "conduction_median": float(np.median(conduction)),
                "keyhole_median": float(np.median(keyhole)),
                "median_difference_keyhole_minus_conduction": float(
                    np.median(keyhole) - np.median(conduction)),
                "median_difference_ci_low": float(np.quantile(boot, 0.025)),
                "median_difference_ci_high": float(np.quantile(boot, 0.975)),
                "cliffs_delta": cliffs_delta(keyhole, conduction),
                "roc_auc_whole_sample": float(r21.roc_auc_score(y, values)),
                "pr_auc_whole_sample": float(r21.average_precision_score(y, values)),
            }
        )
    out = pd.DataFrame(rows)
    write_csv(OUTPUT / "prefix_univariate_separation.csv", out)
    return out


# --------------------------------------------------------------------------------------
# models: the same frozen ARD Matern-3/2 GPC, only the observation window changes
# --------------------------------------------------------------------------------------
def build_models() -> dict[str, tuple[str, tuple[str, ...], str]]:
    models: dict[str, tuple[str, tuple[str, ...], str]] = {
        "gpc_4d": ("gpc", FOURD_FEATURES, "baseline"),
    }
    for prefix in PREFIXES:
        models[f"gpc_4d_plus_early_{prefix_tag(prefix)}"] = (
            "gpc", (*FOURD_FEATURES, feature_name(prefix)),
            "full_trace_reference" if prefix == FULL_PREFIX else "early_prefix",
        )
    return models


MODELS = build_models()

# Predeclared equivalence margin. If the whole 95% interval for
# (full trace - early prefix) lies inside +/- this, the early prefix is called
# "as good as the full trace" for that metric. 0.005 PR-AUC is about a third of the
# +0.0145 gain Phase 2.1R measured, so it is a demanding rather than a flattering margin.
EQUIVALENCE_MARGIN = 0.005

PRIMARY_CONTRAST = f"gpc_4d_plus_early_{prefix_tag(PRIMARY_PREFIX)} - gpc_4d"
CONTRASTS: tuple[tuple[str, str, str], ...] = tuple(
    (f"gpc_4d_plus_early_{prefix_tag(p)}", "gpc_4d",
     "full_trace_reference" if p == FULL_PREFIX else "early_prefix")
    for p in PREFIXES
) + (
    # does the rest of the trace add anything beyond the opening 5%?
    (f"gpc_4d_plus_early_{prefix_tag(FULL_PREFIX)}",
     f"gpc_4d_plus_early_{prefix_tag(PRIMARY_PREFIX)}", "equivalence"),
    # and is 5% already better than an even shorter look?
    (f"gpc_4d_plus_early_{prefix_tag(PRIMARY_PREFIX)}",
     "gpc_4d_plus_early_p02", "equivalence"),
)


def _run_fold(spec: Any, features: pd.DataFrame, usable: set[int],
              boundary: dict[str, dict[str, np.ndarray]]) -> tuple[list[dict], list[dict]]:
    by_index = features.set_index("population_row_index", drop=False)
    train_idx = np.array([i for i in spec.train_indices if i in usable], dtype=int)
    test_idx = np.array([i for i in spec.test_indices if i in usable], dtype=int)
    require(len(np.intersect1d(train_idx, test_idx)) == 0, f"{spec.run_id}: train/test overlap")
    train, test = by_index.loc[train_idx], by_index.loc[test_idx]
    flags = boundary[spec.run_id]
    truth = test.has_keyhole.to_numpy(int)
    names = test.experiment_name.to_numpy()
    # identical seed string to Phase 2.1R so the shared models reproduce exactly
    seed = w85.seed_u32(f"week9_phase2_1r|{spec.run_id}")

    predictions: list[dict[str, Any]] = []
    for model_name, (kind, columns, role) in MODELS.items():
        probability, _ = r21._fit_predict(kind, columns, train, test, seed)
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

    thresholds: list[dict[str, Any]] = []
    for prefix in PREFIXES:
        column = feature_name(prefix)
        train_values = train[column].to_numpy(float)
        test_values = test[column].to_numpy(float)
        threshold, direction = learn_threshold(train_values, train.has_keyhole.to_numpy(int))
        predicted = apply_threshold(test_values, threshold, direction)
        for subset, mask in (("full", np.ones(len(test_idx), bool)),
                             ("q30", flags["q30"]), ("q20", flags["q20"])):
            y, p = truth[mask], predicted[mask]
            tn, fp, fn, tp = confusion_matrix(y, p, labels=[0, 1]).ravel()
            thresholds.append(
                {
                    "run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold,
                    "prefix_fraction": prefix, "subset": subset,
                    "learned_threshold": threshold, "learned_direction": direction,
                    "direction_is_below": int(direction == "below"),
                    "balanced_accuracy": float(balanced_accuracy_score(y, p))
                    if len(np.unique(y)) > 1 else float("nan"),
                    "keyhole_recall": float(recall_score(y, p, pos_label=1, zero_division=0)),
                    "true_negative": int(tn), "false_positive": int(fp),
                    "false_negative": int(fn), "true_positive": int(tp),
                }
            )
    return predictions, thresholds


def evaluate(population: pd.DataFrame, features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
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
        delayed(_run_fold)(spec, features, usable, boundary) for spec in specs
    )
    predictions = pd.DataFrame([row for block, _ in results for row in block])
    thresholds = pd.DataFrame([row for _, block in results for row in block])
    write_csv(OUTPUT / "model_oof_predictions.csv.gz", predictions)
    write_csv(OUTPUT / "prefix_threshold_fold_results.csv", thresholds)
    return predictions, thresholds


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
                    "model": str(model), "subset": str(subset), "role": MODELS[str(model)][2],
                    "features": " + ".join(MODELS[str(model)][1]), "metric": metric,
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
                rows.append(
                    {
                        "subset": str(subset), "contrast": f"{challenger} - {baseline}",
                        "contrast_role": role, "metric": metric,
                        "lower_is_better": metric in LOWER_IS_BETTER,
                        "mean_difference": observed,
                        "ci_low": float(np.quantile(boot, 0.025)),
                        "ci_high": float(np.quantile(boot, 0.975)),
                        "signflip_p": float(
                            (np.sum(np.abs(null) >= abs(observed) - 1e-15) + 1) / (SIGNFLIP_DRAWS + 1)),
                        "repeat_blocks": len(values),
                    }
                )
    contrasts = pd.DataFrame(rows)
    contrasts["holm_p_metric_family"] = np.nan
    for _, block in contrasts[contrasts.metric.isin(PRIMARY_METRICS)].groupby(
            ["contrast", "subset"], sort=False):
        ordered = block.sort_values("signflip_p")
        running = 0.0
        for rank, (index, row) in enumerate(ordered.iterrows()):
            running = max(running, float(row.signflip_p) * (len(ordered) - rank))
            contrasts.loc[index, "holm_p_metric_family"] = min(1.0, running)
    write_csv(OUTPUT / "model_paired_contrasts.csv", contrasts)
    return contrasts


def annotate(contrasts: pd.DataFrame) -> pd.DataFrame:
    block = contrasts[contrasts.metric.isin(PRIMARY_METRICS)].copy()
    block["verdict"] = block.apply(r21.verdict_of, axis=1)
    block["verdict_after_holm"] = np.where(
        block.verdict.ne("NO DETECTABLE DIFFERENCE") & (block.holm_p_metric_family <= 0.05),
        block.verdict, "NO DETECTABLE DIFFERENCE")
    block["metric_family"] = np.where(
        block.metric.isin(["balanced_accuracy", "keyhole_recall", "accuracy"]),
        "hard_decision", "ranking_or_probability")
    block = block.sort_values(["contrast", "subset", "metric_family", "metric"]).reset_index(drop=True)
    write_csv(OUTPUT / "contrast_inference.csv", block)
    return block


def equivalence_test(contrasts: pd.DataFrame) -> pd.DataFrame:
    """Is the opening prefix as good as the whole trace, within a predeclared margin?

    Not a p-value: the question is whether the entire 95% interval for
    (full trace - early prefix) sits inside +/- EQUIVALENCE_MARGIN. If it does, the rest
    of the trace demonstrably adds less than the margin, which is the useful statement.
    """
    name = (f"gpc_4d_plus_early_{prefix_tag(FULL_PREFIX)} - "
            f"gpc_4d_plus_early_{prefix_tag(PRIMARY_PREFIX)}")
    rows = []
    for subset in ("q20", "q30", "full"):
        for metric in PRIMARY_METRICS:
            row = contrasts[contrasts.contrast.eq(name) & contrasts.subset.eq(subset)
                            & contrasts.metric.eq(metric)].iloc[0]
            inside = bool(abs(row.ci_low) <= EQUIVALENCE_MARGIN
                          and abs(row.ci_high) <= EQUIVALENCE_MARGIN)
            rows.append(
                {
                    "subset": subset, "metric": metric,
                    "full_minus_early_prefix": float(row.mean_difference),
                    "ci_low": float(row.ci_low), "ci_high": float(row.ci_high),
                    "equivalence_margin": EQUIVALENCE_MARGIN,
                    "interval_inside_margin": inside,
                    "verdict": "EQUIVALENT WITHIN MARGIN" if inside else (
                        "FULL TRACE BETTER" if row.ci_low > 0 and not row.lower_is_better else (
                            "EARLY PREFIX BETTER" if row.ci_high < 0 and not row.lower_is_better
                            else "INCONCLUSIVE")),
                }
            )
    out = pd.DataFrame(rows)
    write_csv(OUTPUT / "early_vs_full_equivalence.csv", out)
    return out


def reproduction_gate(summary: pd.DataFrame) -> pd.DataFrame:
    """The shared models must reproduce Phase 2.1R exactly, not merely closely."""
    published = pd.read_csv(PHASE21R / "model_oof_summary.csv")
    pairs = [("gpc_4d", "gpc_4d"),
             (f"gpc_4d_plus_early_{prefix_tag(FULL_PREFIX)}", "gpc_4d_plus_max_delta_W")]
    rows = []
    for local_name, published_name in pairs:
        for subset in ("q20", "q30", "full"):
            for metric in METRIC_NAMES:
                here = summary[summary.model.eq(local_name) & summary.subset.eq(subset)
                               & summary.metric.eq(metric)].iloc[0]["mean"]
                there = published[published.model.eq(published_name) & published.subset.eq(subset)
                                  & published.metric.eq(metric)].iloc[0]["mean"]
                difference = abs(float(here) - float(there))
                rows.append(
                    {
                        "phase2_1re_model": local_name, "phase2_1r_model": published_name,
                        "subset": subset, "metric": metric,
                        "phase2_1re_mean": float(here), "phase2_1r_mean": float(there),
                        "abs_difference": difference,
                        "status": "PASS" if difference <= 1e-9 else "FAIL",
                    }
                )
    gate = pd.DataFrame(rows)
    write_csv(OUTPUT / "phase2_1r_reproduction_gate.csv", gate)
    require(bool(gate.status.eq("PASS").all()),
            f"Phase 2.1R reproduction failed:\n{gate[gate.status.eq('FAIL')]}")
    return gate


def summarize_thresholds(thresholds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (prefix, subset), group in thresholds.groupby(["prefix_fraction", "subset"], sort=True):
        per_repeat = group.groupby("repeat")[["balanced_accuracy", "keyhole_recall"]].mean()
        rows.append(
            {
                "prefix_fraction": float(prefix), "subset": str(subset),
                "learned_threshold_median": float(group.learned_threshold.median()),
                "fraction_of_folds_choosing_below": float(group.direction_is_below.mean()),
                "balanced_accuracy_mean": float(per_repeat.balanced_accuracy.mean()),
                "balanced_accuracy_sd_across_repeats": float(per_repeat.balanced_accuracy.std(ddof=1)),
                "keyhole_recall_mean": float(per_repeat.keyhole_recall.mean()),
                "total_false_negative": int(group.false_negative.sum()),
                "total_false_positive": int(group.false_positive.sum()),
            }
        )
    out = pd.DataFrame(rows)
    write_csv(OUTPUT / "prefix_threshold_summary.csv", out)
    return out


# --------------------------------------------------------------------------------------
# figures
# --------------------------------------------------------------------------------------
CONDUCTION = "#4477AA"
KEYHOLE = "#CC3311"


def _save(fig: plt.Figure, name: str) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / name
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def _pretty(name: str) -> str:
    return name.replace("_", " ")


def _prefix_ticklabels(saturation: pd.DataFrame) -> list[str]:
    return [
        f"{int(p * 100)}%\n{row.median_observed_window_us:.0f} µs"
        for p, row in zip(PREFIXES, saturation.itertuples(index=False))
    ]


def make_figures(features: pd.DataFrame, table: pd.DataFrame, saturation: pd.DataFrame,
                 separation: pd.DataFrame, threshold_summary: pd.DataFrame,
                 summary: pd.DataFrame, inference: pd.DataFrame, equivalence: pd.DataFrame,
                 claims: pd.DataFrame) -> list[Path]:
    plt.style.use("seaborn-v0_8-whitegrid")
    created: list[Path] = []
    labels = _prefix_ticklabels(saturation)

    # 1 -------------------------------------------------------- what a prefix means
    example = features[features.has_keyhole.eq(1)].sort_values(
        feature_name(FULL_PREFIX)).iloc[len(features[features.has_keyhole.eq(1)]) // 2]
    rows = table[table.simulation_id.eq(example.experiment_name)].sort_values("analysis_point_i")
    width = np.concatenate([rows.W_i_um.to_numpy(float), [rows.W_i_plus_1_um.iloc[-1]]])
    delta = rows.delta_W_um.to_numpy(float)
    fig, axes = plt.subplots(2, 1, figsize=(12.5, 7), sharex=True,
                             gridspec_kw={"height_ratios": [1.15, 1]})
    axes[0].plot(np.arange(len(width)), width, color=KEYHOLE, lw=1.8, zorder=3)
    shades = ["#2b2b2b", "#5a5a5a", "#8a8a8a", "#b4b4b4"]
    for colour, prefix in zip(shades, PREFIXES[:4]):
        count = prefix_transition_count(prefix)
        axes[0].axvline(count, color=colour, lw=1.4, ls="--")
        axes[0].text(count + 1.5, width.max() * 0.34,
                     f"{int(prefix * 100)}% = first {count}\nanalysis points\n"
                     f"({features[f'observed_ms_{prefix_tag(prefix)}'].median() * 1000:.0f} µs)",
                     fontsize=8, color=colour, va="top")
    axes[0].set(ylabel="transverse width W (µm)", xlim=(-2, 92),
                title=f"One Keyhole simulation: {example.experiment_name[:38]}…")
    axes[1].bar(np.arange(len(delta)), delta, width=1.0,
                color=np.where(delta > 0, "#117733", "#CC3311"))
    axes[1].axhline(0, color="black", lw=0.8)
    for colour, prefix in zip(shades, PREFIXES[:4]):
        count = prefix_transition_count(prefix)
        axes[1].axvline(count, color=colour, lw=1.4, ls="--")
        value = float(example[feature_name(prefix)])
        axes[1].plot([count], [value], "o", color=colour, ms=7, zorder=5)
        axes[1].text(count + 1.5, value, f"max so far {value:.1f} µm", fontsize=8, color=colour,
                     va="center")
    axes[1].set(xlabel="consecutive resampled analysis point", ylabel="ΔW (µm)", xlim=(-2, 92))
    fig.suptitle("Figure 1 — A 'prefix' is simply how much of the opening we are allowed to watch.\n"
                 "The largest rise is already found within the first few points.", fontsize=12.5)
    created.append(_save(fig, "01_what_a_prefix_means.png"))

    # 2 ------------------------------------------------- prefix feature vs full trace
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.0))
    full = features[feature_name(FULL_PREFIX)].to_numpy(float)
    for prefix, colour in zip(PREFIXES[:3], ("#4C78A8", "#EE7733", "#117733")):
        axes[0].scatter(full, features[feature_name(prefix)], s=16, alpha=0.55, color=colour,
                        label=f"{int(prefix * 100)}% prefix")
    limit = (min(full.min(), 0) - 2, full.max() + 2)
    axes[0].plot(limit, limit, color="black", lw=1.0, ls="--", label="identical to full trace")
    axes[0].set(xlim=limit, ylim=limit, xlabel="max ΔW using the WHOLE trace (µm)",
                ylabel="max ΔW using only the prefix (µm)",
                title="Short prefixes already recover the full-trace value")
    axes[0].legend(fontsize=8)
    axes[1].plot(range(len(PREFIXES)), saturation.fraction_already_equal_to_full, "o-",
                 color="#4C78A8", lw=2, ms=8, label="exactly equal to full-trace value")
    axes[1].plot(range(len(PREFIXES)), saturation.pearson_r_with_full_trace, "s--",
                 color="#EE7733", lw=2, ms=7, label="correlation with full-trace value")
    axes[1].set_xticks(range(len(PREFIXES)), labels, fontsize=8.5)
    axes[1].set(ylim=(0, 1.05), xlabel="prefix watched (share of trace / median window)",
                ylabel="fraction / correlation", title="How fast the feature saturates")
    axes[1].legend(fontsize=8.5, loc="lower right")
    fig.suptitle("Figure 2 — Does an opening prefix already contain the full-trace number?", fontsize=12.5)
    created.append(_save(fig, "02_prefix_vs_full_feature.png"))

    # 3 --------------------------------------------------- marginal separation vs prefix
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8))
    axes[0].errorbar(range(len(PREFIXES)), separation.cliffs_delta, fmt="o-", lw=2, ms=8,
                     color="#4C78A8")
    axes[0].axhline(0, color="black", lw=1.0, ls="--")
    axes[0].set_xticks(range(len(PREFIXES)), labels, fontsize=8.5)
    axes[0].set(xlabel="prefix watched", ylabel="Cliff's δ (Keyhole − Conduction)",
                title="Separation is negative at every prefix\n(Keyhole widens more slowly)")
    axes[1].plot(range(len(PREFIXES)), separation.roc_auc_whole_sample, "o-", lw=2, ms=8,
                 color="#CC3311")
    axes[1].axhline(0.5, color="black", lw=1.0, ls="--", label="chance")
    axes[1].set_xticks(range(len(PREFIXES)), labels, fontsize=8.5)
    axes[1].set(xlabel="prefix watched", ylabel="whole-sample ROC-AUC",
                title="Ranking power vs how long we watch")
    axes[1].legend(fontsize=8.5)
    fig.suptitle("Figure 3 — Marginal Keyhole/Conduction separation as a function of the prefix",
                 fontsize=12.5)
    created.append(_save(fig, "03_separation_vs_prefix.png"))

    # 4 ------------------------------------------------ leak-free threshold vs prefix
    fig, ax = plt.subplots(figsize=(11, 5.0))
    for subset, colour, marker in (("q20", "#CC3311", "o"), ("q30", "#EE7733", "s"),
                                   ("full", "#4C78A8", "^")):
        block = threshold_summary[threshold_summary.subset.eq(subset)].sort_values("prefix_fraction")
        ax.errorbar(range(len(PREFIXES)), block.balanced_accuracy_mean,
                    yerr=block.balanced_accuracy_sd_across_repeats, fmt=f"{marker}-", lw=2, ms=8,
                    color=colour, capsize=3, label=f"{subset} region")
    ax.axhline(0.5, color="black", lw=1.4, ls="--", label="chance (0.50)")
    ax.set_xticks(range(len(PREFIXES)), labels, fontsize=9)
    ax.set(xlabel="prefix watched (share of trace / median window)",
           ylabel="held-out balanced accuracy",
           title="Figure 4 — The simple threshold rule, leak-free, as a function of the prefix\n"
                 "(cut and direction learned on training folds only, at each prefix)")
    ax.legend(fontsize=9)
    created.append(_save(fig, "04_threshold_vs_prefix.png"))

    # 5 ------------------------------------------------------------- HEADLINE curve
    fig, axes = plt.subplots(1, 2, figsize=(14.5, 5.2))
    for metric, colour, marker in (("pr_auc", "#CC3311", "o"), ("roc_auc", "#4C78A8", "s"),
                                   ("balanced_accuracy", "#999999", "^")):
        means, lows, highs = [], [], []
        for prefix in PREFIXES:
            row = inference[
                inference.contrast.eq(f"gpc_4d_plus_early_{prefix_tag(prefix)} - gpc_4d")
                & inference.subset.eq("q20") & inference.metric.eq(metric)].iloc[0]
            means.append(row.mean_difference)
            lows.append(row.mean_difference - row.ci_low)
            highs.append(row.ci_high - row.mean_difference)
        axes[0].errorbar(range(len(PREFIXES)), means, yerr=[lows, highs], fmt=f"{marker}-",
                         lw=2, ms=8, color=colour, capsize=4, label=_pretty(metric))
    axes[0].axhline(0, color="black", lw=1.2, ls="--")
    axes[0].set_xticks(range(len(PREFIXES)), labels, fontsize=8.5)
    axes[0].set(xlabel="prefix watched (share of trace / median window)",
                ylabel="q20 gain over the 4D-only GPC",
                title="Gain over [P, VX, LS, ST] vs how long we watch")
    axes[0].legend(fontsize=9)

    order = ["gpc_4d"] + [f"gpc_4d_plus_early_{prefix_tag(p)}" for p in PREFIXES]
    block = summary[summary.subset.eq("q20") & summary.metric.eq("pr_auc")].set_index("model")
    means = np.array([float(block.loc[m, "mean"]) for m in order])
    sds = np.array([float(block.loc[m, "sd_across_repeats"]) for m in order])
    colours = ["#333333"] + ["#CC3311" if p != FULL_PREFIX else "#117733" for p in PREFIXES]
    axes[1].barh(np.arange(len(order)), means, xerr=sds, color=colours,
                 error_kw={"lw": 0.9, "ecolor": "#555555"})
    axes[1].set_yticks(np.arange(len(order)),
                       ["4D only"] + [f"+ max ΔW, first {int(p * 100)}%" for p in PREFIXES],
                       fontsize=9)
    axes[1].set(xlim=(0.80, 0.95), xlabel="q20 PR-AUC")
    for position, value in enumerate(means):
        axes[1].text(value + 0.002, position, f"{value:.4f}", va="center", fontsize=8.5)
    axes[1].set_title("q20 PR-AUC by observation window")
    fig.suptitle("Figure 5 — How early can the width signal be read?", fontsize=13)
    fig.subplots_adjust(wspace=0.28)
    created.append(_save(fig, "05_gpc_gain_vs_prefix.png"))

    # 6 ------------------------------------------------------------ equivalence forest
    block = equivalence[equivalence.subset.eq("q20")].copy()
    fig, ax = plt.subplots(figsize=(10.5, 5.0))
    positions = np.arange(len(block))[::-1]
    for position, row in zip(positions, block.itertuples(index=False)):
        inside = bool(row.interval_inside_margin)
        colour = "#117733" if inside else "#CC3311"
        ax.plot([row.ci_low, row.ci_high], [position, position], color=colour, lw=2.6,
                solid_capstyle="round")
        ax.plot([row.full_minus_early_prefix], [position], "o", color=colour, ms=7)
        ax.text(EQUIVALENCE_MARGIN * 1.18, position,
                "within margin" if inside else "outside margin",
                va="center", fontsize=8.5, color=colour)
    ax.axvspan(-EQUIVALENCE_MARGIN, EQUIVALENCE_MARGIN, color="#117733", alpha=0.09,
               label=f"predeclared equivalence margin ±{EQUIVALENCE_MARGIN}")
    ax.axvline(0, color="black", lw=1.2)
    ax.set_yticks(positions, [_pretty(m) for m in block.metric], fontsize=9)
    ax.set(xlim=(-EQUIVALENCE_MARGIN * 2.4, EQUIVALENCE_MARGIN * 3.2),
           xlabel=f"whole trace − first {int(PRIMARY_PREFIX * 100)}% only  "
                  f"(right = the rest of the trace helps)",
           title=f"Figure 6 — Does the rest of the trace add anything beyond the opening "
                 f"{int(PRIMARY_PREFIX * 100)}%?\nq20, 95% repeat-block intervals")
    ax.legend(fontsize=8.5, loc="lower right")
    created.append(_save(fig, "06_early_vs_full_equivalence.png"))

    # 7 ------------------------------------------------------------------ claim status
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
        ax.text(0.01, y, wrapped_claims[position], fontsize=8.3, va="center", zorder=2,
                linespacing=1.35)
        ax.text(0.55, y, row.status, fontsize=8.5, va="center", fontweight="bold",
                color=status_colour.get(row.status, "#333333"), zorder=2)
        ax.text(0.72, y, wrapped_guards[position], fontsize=7.5, va="center", color="#444444",
                zorder=2, linespacing=1.35)
    ax.set_title("Figure 7 — Week 9 Phase 2.1R-E claim status", fontsize=13, pad=14)
    created.append(_save(fig, "07_claim_status.png"))
    return created


# --------------------------------------------------------------------------------------
# claims and reports
# --------------------------------------------------------------------------------------
def build_claims(saturation: pd.DataFrame, separation: pd.DataFrame,
                 threshold_summary: pd.DataFrame, summary: pd.DataFrame,
                 inference: pd.DataFrame, equivalence: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    def mean_of(model: str, metric: str, subset: str = "q20") -> float:
        return float(summary[summary.model.eq(model) & summary.subset.eq(subset)
                             & summary.metric.eq(metric)].iloc[0]["mean"])

    def contrast_of(name: str, metric: str, subset: str = "q20") -> pd.Series:
        return inference[inference.contrast.eq(name) & inference.subset.eq(subset)
                         & inference.metric.eq(metric)].iloc[0]

    def family(prefix: float, subset: str = "q20") -> tuple[str, str]:
        block = inference[inference.contrast.eq(f"gpc_4d_plus_early_{prefix_tag(prefix)} - gpc_4d")
                          & inference.subset.eq(subset)]
        return (r21.family_status(block[block.metric_family.eq("hard_decision")]),
                r21.family_status(block[block.metric_family.eq("ranking_or_probability")]))

    primary_hard, primary_rank = family(PRIMARY_PREFIX)
    full_hard, full_rank = family(FULL_PREFIX)
    shortest_hard, shortest_rank = family(PREFIXES[0])

    saturation_at_primary = saturation[saturation.prefix_fraction.eq(PRIMARY_PREFIX)].iloc[0]
    window_us = float(saturation_at_primary.median_observed_window_us)
    equal_share = float(saturation_at_primary.fraction_already_equal_to_full)

    q20_equivalence = equivalence[equivalence.subset.eq("q20")]
    equivalent_metrics = int(q20_equivalence.interval_inside_margin.sum())
    all_equivalent = equivalent_metrics == len(q20_equivalence)

    threshold_primary = threshold_summary[threshold_summary.prefix_fraction.eq(PRIMARY_PREFIX)
                                          & threshold_summary.subset.eq("q20")].iloc[0]
    threshold_full_region = threshold_summary[threshold_summary.prefix_fraction.eq(PRIMARY_PREFIX)
                                              & threshold_summary.subset.eq("full")].iloc[0]

    # Is the gain flat in the prefix, i.e. is watching longer pointless?
    gains = [float(contrast_of(f"gpc_4d_plus_early_{prefix_tag(p)} - gpc_4d", "pr_auc").mean_difference)
             for p in PREFIXES]
    monotone_increase = all(b >= a - 1e-9 for a, b in zip(gains, gains[1:]))

    claims = pd.DataFrame(
        [
            {
                "claim": f"PRIMARY — watching only the opening {int(PRIMARY_PREFIX * 100)}% of the trace "
                         f"improves ranking over [P, VX, LS, ST]",
                "status": primary_rank,
                "guardrail": f"q20 PR-AUC {mean_of('gpc_4d', 'pr_auc'):.4f} -> "
                             f"{mean_of(f'gpc_4d_plus_early_{prefix_tag(PRIMARY_PREFIX)}', 'pr_auc'):.4f}; "
                             f"median observed window {window_us:.0f} µs; Holm over six metrics",
            },
            {
                "claim": f"PRIMARY — the same {int(PRIMARY_PREFIX * 100)}% prefix improves hard "
                         f"classification on q20",
                "status": primary_hard,
                "guardrail": "q20 balanced accuracy / accuracy / Keyhole recall, read separately from "
                             "the ranking metrics",
            },
            {
                "claim": f"The rest of the trace adds nothing beyond the opening "
                         f"{int(PRIMARY_PREFIX * 100)}% (equivalence within ±{EQUIVALENCE_MARGIN})",
                "status": "SUPPORTED" if all_equivalent else (
                    "QUALIFIED" if equivalent_metrics >= len(q20_equivalence) - 1 else "NOT SUPPORTED"),
                "guardrail": f"{equivalent_metrics}/{len(q20_equivalence)} q20 metrics have their whole "
                             f"95% interval inside ±{EQUIVALENCE_MARGIN}; predeclared margin, about a "
                             f"third of the Phase 2.1R gain",
            },
            {
                "claim": f"An even shorter look ({int(PREFIXES[0] * 100)}% of the trace) is already enough "
                         f"for the ranking gain",
                "status": shortest_rank,
                "guardrail": f"median observed window "
                             f"{float(saturation.iloc[0].median_observed_window_us):.0f} µs; "
                             f"q20 PR-AUC gain {gains[0]:+.4f}",
            },
            {
                "claim": "Watching longer keeps improving the model",
                "status": "SUPPORTED" if monotone_increase else "NOT SUPPORTED",
                "guardrail": "q20 PR-AUC gain across prefixes: "
                             + " / ".join(f"{g:+.4f}" for g in gains),
            },
            {
                "claim": f"The opening prefix already contains the full-trace value of the feature",
                "status": "SUPPORTED" if equal_share >= 0.90 else "QUALIFIED",
                "guardrail": f"at the {int(PRIMARY_PREFIX * 100)}% prefix, {equal_share:.1%} of "
                             f"simulations already have exactly the full-trace maximum",
            },
            {
                "claim": "A simple leak-free threshold on the early feature beats chance on q20",
                "status": "SUPPORTED" if threshold_primary.balanced_accuracy_mean
                          - 2 * threshold_primary.balanced_accuracy_sd_across_repeats > 0.5
                          else ("QUALIFIED" if threshold_primary.balanced_accuracy_mean > 0.55
                                else "NOT SUPPORTED"),
                "guardrail": f"q20 balanced accuracy {threshold_primary.balanced_accuracy_mean:.3f} "
                             f"± {threshold_primary.balanced_accuracy_sd_across_repeats:.3f}; on the full "
                             f"held-out set {threshold_full_region.balanced_accuracy_mean:.3f}",
            },
            {
                "claim": "Phase 2.1R's shared models are reproduced exactly by this pipeline",
                "status": "SUPPORTED",
                "guardrail": "phase2_1r_reproduction_gate.csv: the 4D baseline and the 100% prefix both "
                             "match Phase 2.1R to <1e-9 on every metric and region",
            },
            {
                "claim": "No prefix feature uses a later analysis point",
                "status": "SUPPORTED",
                "guardrail": "prefix_no_future_audit.csv independently recomputes every prefix feature "
                             "and checks the latest analysis point consulted",
            },
            {
                "claim": "This is an in-process monitoring result",
                "status": "NOT SUPPORTED",
                "guardrail": "retrospective prefix analysis of SPH monitor traces; no camera, no sensor "
                             "model, no prospective experiment, and the window is tens of microseconds",
            },
            {
                "claim": "This changes the active-learning acquisition rule",
                "status": "NOT SUPPORTED",
                "guardrail": "predictive feature-value study on the frozen folds; the A0 path is untouched",
            },
            {
                "claim": "Results generalise to simulations with no usable width trace",
                "status": "NOT SUPPORTED",
                "guardrail": "every model is trained and scored only on the 350 usable simulations",
            },
        ]
    )
    facts = {
        "primary_hard": primary_hard, "primary_rank": primary_rank,
        "full_hard": full_hard, "full_rank": full_rank,
        "shortest_hard": shortest_hard, "shortest_rank": shortest_rank,
        "window_us": window_us, "equal_share": equal_share,
        "all_equivalent": all_equivalent, "equivalent_metrics": equivalent_metrics,
        "gains": gains, "monotone_increase": monotone_increase,
        "threshold_primary": threshold_primary, "threshold_full_region": threshold_full_region,
        "mean_of": mean_of, "contrast_of": contrast_of,
    }
    write_csv(OUTPUT / "claim_status.csv", claims)
    return claims, facts


def render_reports(population: pd.DataFrame, features: pd.DataFrame, saturation: pd.DataFrame,
                   separation: pd.DataFrame, threshold_summary: pd.DataFrame, summary: pd.DataFrame,
                   inference: pd.DataFrame, equivalence: pd.DataFrame, gate: pd.DataFrame,
                   claims: pd.DataFrame, facts: dict[str, Any], figures: list[Path]) -> None:
    mean_of, contrast_of = facts["mean_of"], facts["contrast_of"]
    usable = len(features)
    keyholes = int(features.has_keyhole.sum())

    def line(row: pd.Series) -> str:
        return f"{row.mean_difference:+.4f} [{row.ci_low:+.4f}, {row.ci_high:+.4f}]"

    prefix_table = "\n".join(
        f"| {int(row.prefix_fraction * 100)}% | {row.transitions_used} | "
        f"{row.median_observed_window_us:.0f} µs | {row.fraction_already_equal_to_full:.1%} | "
        f"{row.pearson_r_with_full_trace:.4f} | {row.median_shortfall_um:.3f} µm |"
        for row in saturation.itertuples(index=False)
    )
    separation_table = "\n".join(
        f"| {int(row.prefix_fraction * 100)}% | {row.conduction_median:.3f} | {row.keyhole_median:.3f} | "
        f"{row.cliffs_delta:+.3f} | {row.roc_auc_whole_sample:.3f} | {row.pr_auc_whole_sample:.3f} |"
        for row in separation.itertuples(index=False)
    )
    gain_table = "\n".join(
        f"| {int(p * 100)}% | {saturation[saturation.prefix_fraction.eq(p)].iloc[0].median_observed_window_us:.0f} µs | "
        f"{mean_of(f'gpc_4d_plus_early_{prefix_tag(p)}', 'pr_auc'):.4f} | "
        f"{line(contrast_of(f'gpc_4d_plus_early_{prefix_tag(p)} - gpc_4d', 'pr_auc'))} | "
        f"{contrast_of(f'gpc_4d_plus_early_{prefix_tag(p)} - gpc_4d', 'pr_auc').verdict_after_holm} |"
        for p in PREFIXES
    )
    threshold_table = "\n".join(
        f"| {int(row.prefix_fraction * 100)}% | {row.subset} | {row.learned_threshold_median:.3f} µm | "
        f"{row.fraction_of_folds_choosing_below:.0%} | "
        f"{row.balanced_accuracy_mean:.4f} ± {row.balanced_accuracy_sd_across_repeats:.4f} | "
        f"{row.keyhole_recall_mean:.4f} |"
        for row in threshold_summary.sort_values(["subset", "prefix_fraction"]).itertuples(index=False)
    )
    equivalence_table = "\n".join(
        f"| {_pretty(row.metric)} | {row.full_minus_early_prefix:+.4f} "
        f"[{row.ci_low:+.4f}, {row.ci_high:+.4f}] | "
        f"{'yes' if row.interval_inside_margin else 'no'} | {row.verdict} |"
        for row in equivalence[equivalence.subset.eq("q20")].itertuples(index=False)
    )
    ledger_table = "\n".join(
        f"| {row.claim} | {row.status} | {row.guardrail} |" for row in claims.itertuples(index=False)
    )
    primary_name = f"gpc_4d_plus_early_{prefix_tag(PRIMARY_PREFIX)} - gpc_4d"
    primary_metric_table = "\n".join(
        f"| {_pretty(row.metric)} | {'lower is better' if row.lower_is_better else 'higher is better'} | "
        f"{line(row)} | {row.signflip_p:.4f} | {float(row.holm_p_metric_family):.4f} | "
        f"**{row.verdict_after_holm}** |"
        for row in inference[inference.contrast.eq(primary_name)
                             & inference.subset.eq("q20")].itertuples(index=False)
    )

    one_page = f"""# What did we actually ask?

Phase 2.1R found two things that, put together, ask an obvious next question.

1. Adding the largest width jump to the four process inputs improves how well the model **ranks**
   Keyhole risk (q20 PR-AUC +0.0145), though it does not change hard classification.
2. **95.4%** of those largest jumps happen inside the first 5% of the trace.

So: **if the signal is all at the beginning, do we need the rest of the trace at all?**

This phase rebuilds exactly the same feature using only an opening slice of each simulation, and
sweeps how long that slice is: 2%, 5%, 10%, 20%, 40% and 100% of the trace. Nothing else changes —
same 350 simulations, same 100 frozen folds, same ARD Matérn-3/2 GPC.

The slices are counted in **consecutive resampled analysis point** steps on the pinned Phase 2 grid
(201 points per simulation, so 5% is the first 10 transitions), never in raw solver timesteps.

Concrete example. A simulation's opening widths might be 4, 31, 52, 56, 63 µm, so the changes are
`[+27, +21, +4, +7]`. Allowed to watch only the first five analysis points, we record
`max_positive_delta_W = 27`. Allowed the whole trace, we might find something bigger later — this
phase measures how often we do, and what it costs when we do not.

**Strict no-future rule.** The feature at prefix *p* uses only transitions ending at or before
analysis point `ceil(p × 200)`. `prefix_no_future_audit.csv` recomputes every value a second,
independent way and records the latest analysis point consulted.

## Does an opening slice already contain the full-trace number?

{usable} of 405 simulations have a usable trace ({keyholes} Keyhole, {usable - keyholes} Conduction).

| prefix | transitions seen | median window | already equal to full-trace value | correlation with full | median shortfall |
|---|---|---|---|---|---|
{prefix_table}

**At the {int(PRIMARY_PREFIX * 100)}% prefix — a median window of {facts['window_us']:.0f} µs —
{facts['equal_share']:.1%} of simulations already have exactly the same number they would have had from
the whole trace.**

## Marginal separation at each prefix

| prefix | Conduction median | Keyhole median | Cliff's δ | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|
{separation_table}

The sign is negative at every prefix: Keyhole simulations widen **more slowly** in their opening, at
every observation window tested.

## Does the early feature help the 4D GPC?

| prefix | median window | q20 PR-AUC | gain over 4D-only [95% CI] | verdict |
|---|---|---|---|---|
{gain_table}

### The primary contrast: opening {int(PRIMARY_PREFIX * 100)}% only, versus 4D-only, on q20

| metric | direction | mean difference [95% CI] | sign-flip p | Holm p | verdict |
|---|---|---|---|---|---|
{primary_metric_table}

**Hard classification: {facts['primary_hard']}. Ranking / probability: {facts['primary_rank']}.**

## Does the rest of the trace add anything?

Predeclared equivalence margin **±{EQUIVALENCE_MARGIN}** on each metric — roughly a third of the
Phase 2.1R gain, so a demanding rather than a flattering test. The question is whether the whole 95%
interval for (whole trace − opening {int(PRIMARY_PREFIX * 100)}%) sits inside it.

| metric | whole trace − early prefix [95% CI] | inside margin? | verdict |
|---|---|---|---|
{equivalence_table}

{facts['equivalent_metrics']} of {len(equivalence[equivalence.subset.eq('q20')])} q20 metrics are
equivalent within the margin.

## The simple threshold rule at each prefix

| prefix | region | median learned cut | folds choosing 'small means Keyhole' | balanced accuracy | Keyhole recall |
|---|---|---|---|---|---|
{threshold_table}

## Claim ledger

| claim | status | guardrail |
|---|---|---|
{ledger_table}

## What this is not

A retrospective prefix analysis of simulation monitor traces is **not** an in-process monitoring
result. There is no camera, no sensor noise model, no latency budget, and the windows involved are
tens of microseconds. Nothing here changes the active-learning acquisition rule, and nothing here
transfers to the {405 - usable} simulations with no usable trace.
"""

    (OUTPUT / "SUPERVISOR_PHASE2_1RE_ONE_PAGE.md").write_text(one_page.rstrip() + "\n", encoding="utf-8")

    methods = f"""
## Methods

**Inherited unchanged from Phase 2.1R.** Population (405 simulations, 73 Keyhole, of which {usable}
have a usable transverse-width trace), the pinned Phase 2 width extraction, the 100 frozen Week 8.5
grouped outer folds, the q20/q30 evaluation masks, the ARD Matérn-3/2 GPC (Phase 1.12 winner G3), the
repeat-block bootstrap, the sign-flip permutation test, and the Holm adjustment within each contrast
across the six predeclared metrics. This module imports those directly from
`src/week9_phase2_1r_simple_width_change_control.py` rather than restating them, so they cannot drift.

**What is new.** Only the observation window. For each prefix *p* the feature
`max_positive_delta_W_{{tag}}` is the largest positive change among the first `ceil(p × 200)`
consecutive-point transitions.

**Audit gates.** Two models here are shared with Phase 2.1R by construction: the `gpc_4d` baseline, and
the 100% prefix, which is the Phase 2.1R full-trace feature. `phase2_1r_reproduction_gate.csv` confirms
both reproduce the published Phase 2.1R means to better than 1e-9 on every metric and every region —
which is what licenses reading the prefix curve on the same scale. The fold seed string is deliberately
kept as `week9_phase2_1r|<run_id>` for exactly this reason.

**Multiplicity.** Corrected: the six predeclared metrics within each contrast. Not corrected: the six
prefixes, the set of contrasts, and the three evaluation regions. The prefix sweep is therefore read as
a *shape* — does the gain rise, fall or stay flat as the window grows — rather than as six independent
tests.

## Figures
{chr(10).join(f'- `figures/{p.name}`' for p in figures)}
"""

    (OUTPUT / "FINAL_PHASE2_1RE_REPORT.md").write_text(
        "# Week 9 Phase 2.1R-E — final report\n## How early can the width signal be read?\n\n"
        + one_page.split("# What did we actually ask?", 1)[1].strip() + "\n"
        + methods.rstrip() + "\n",
        encoding="utf-8",
    )

    (OUTPUT / "claim_ledger.md").write_text(
        f"""# Week 9 Phase 2.1R-E claim ledger

Primary question: **if the width signal is all at the start of the trace, is an opening prefix enough?**

A "prefix" is an opening slice of the width series measured at **consecutive resampled analysis point**
spacing on the pinned Phase 2 grid — 201 points per simulation, so the 5% prefix is the first 10
transitions, a median window of about 68 µs. These are not raw solver timesteps.

| claim | status | guardrail |
|---|---|---|
{ledger_table}

## Status vocabulary
- **SUPPORTED** — the 95% repeat-block interval excludes zero in the favourable direction and, for model
  contrasts, survives Holm across the six predeclared metrics.
- **QUALIFIED** — present on some metrics or regions but not others.
- **NOT SUPPORTED** — no detectable difference, or a difference in the unfavourable direction.
""".rstrip() + "\n",
        encoding="utf-8",
    )

    write_csv(OUTPUT / "figure_manifest.csv", pd.DataFrame(
        [{"artifact": f"figures/{p.name}", "sha256": sha256_file(p), "bytes": p.stat().st_size}
         for p in figures]))


# --------------------------------------------------------------------------------------
# notebook
# --------------------------------------------------------------------------------------
def notebook_payload() -> dict[str, Any]:
    sections: list[tuple[str, str, str]] = [
        (
            "1. Why this follow-up exists",
            "Phase 2.1R found that the largest width jump helps the model **rank** Keyhole risk, and "
            "that **95.4%** of those largest jumps happen in the first 5% of the trace.\n\n"
            "Put those together and the question is obvious: **if the signal is all at the start, do we "
            "need the rest of the trace?**\n\n"
            "So we rebuild exactly the same feature, but only allow the model to watch an opening slice "
            "— 2%, 5%, 10%, 20%, 40% or 100% of the analysis points — and see what changes.",
            "display(Image(filename=OUT/'figures'/'01_what_a_prefix_means.png'))",
        ),
        (
            "2. What a prefix feature is, concretely",
            "Suppose a simulation's opening widths are 4, 31, 52, 56, 63 µm. The changes between "
            "neighbouring analysis points are `[+27, +21, +4, +7]`.\n\n"
            "* Allowed to watch **only the first five analysis points**, we record the biggest rise we "
            "have seen: `max_positive_delta_W = 27`.\n"
            "* Allowed the **whole trace**, we might find something bigger later.\n\n"
            "The whole phase is measuring how often we actually do find something bigger later, and "
            "what it costs us when we stop early.\n\n"
            "**No peeking.** The feature at prefix *p* uses only transitions ending at or before "
            "analysis point `ceil(p × 200)`. The audit below recomputes every value a second, "
            "independent way and reports the latest analysis point it consulted.",
            "display(pd.read_csv(OUT/'prefix_no_future_audit.csv'))",
        ),
        (
            "3. Does a short opening already contain the full-trace number?",
            "This is the cheapest possible check and it decides most of the phase. For each prefix we "
            "ask what fraction of simulations already have *exactly* the number they would have got "
            "from the whole trace.",
            "display(pd.read_csv(OUT/'prefix_saturation_profile.csv').round(4))\n"
            "display(Image(filename=OUT/'figures'/'02_prefix_vs_full_feature.png'))",
        ),
        (
            "4. Separation at each prefix",
            "Keyhole simulations widen **more slowly** at the start — the effect is negative at every "
            "window tested, which is the same inverted direction Phase 2.1R found.",
            "display(pd.read_csv(OUT/'prefix_univariate_separation.csv').round(4))\n"
            "display(Image(filename=OUT/'figures'/'03_separation_vs_prefix.png'))",
        ),
        (
            "5. The simple threshold rule, at each prefix",
            "Same leak-free rule as Phase 2.1R: inside each fold the cut **and its direction** are "
            "learned from the training simulations only, then frozen and applied to the held-out ones.",
            "display(pd.read_csv(OUT/'prefix_threshold_summary.csv').round(4))\n"
            "display(Image(filename=OUT/'figures'/'04_threshold_vs_prefix.png'))",
        ),
        (
            "6. The headline: gain over the 4D GPC versus how long we watch",
            "Every model is the same ARD Matérn-3/2 GPC on the same folds. Only the observation window "
            "changes. Two of these models are shared with Phase 2.1R by construction — the 4D baseline "
            "and the 100% prefix — and the reproduction gate confirms they match the published numbers "
            "exactly, which is what lets us read this curve on the same scale.",
            "gate = pd.read_csv(OUT/'phase2_1r_reproduction_gate.csv')\n"
            "print('reproduction rows:', len(gate), '| max abs difference:', gate.abs_difference.max(),\n"
            "      '| all PASS:', bool(gate.status.eq('PASS').all()))\n"
            "s = pd.read_csv(OUT/'model_oof_summary.csv')\n"
            "display(s[(s.subset=='q20') & s.metric.isin(['balanced_accuracy','keyhole_recall',"
            "'roc_auc','pr_auc'])].pivot(index='model', columns='metric', values='mean').round(4))\n"
            "display(Image(filename=OUT/'figures'/'05_gpc_gain_vs_prefix.png'))",
        ),
        (
            "7. Does the rest of the trace add anything?",
            "This is the question that matters, and a plain 'no significant difference' would not answer "
            "it — absence of evidence is not evidence of absence. So we use a **predeclared equivalence "
            "margin** of ±0.005 and ask whether the entire 95% interval for "
            "(whole trace − opening 5%) sits inside it. If it does, the rest of the trace demonstrably "
            "adds less than the margin.",
            "display(pd.read_csv(OUT/'early_vs_full_equivalence.csv').round(4))\n"
            "display(Image(filename=OUT/'figures'/'06_early_vs_full_equivalence.png'))",
        ),
        (
            "8. What is supported, and what this is not",
            "A retrospective prefix analysis of simulation traces is not an in-process monitoring "
            "result: no camera, no sensor noise, no latency budget, and the windows are tens of "
            "microseconds. Nothing here touches the acquisition rule.",
            "display(Image(filename=OUT/'figures'/'07_claim_status.png'))\n"
            "print(json.loads((OUT/'validation_report.json').read_text(encoding='utf-8'))['status'])",
        ),
    ]
    cells: list[dict[str, Any]] = [
        {
            "cell_type": "markdown", "id": "e0", "metadata": {},
            "source": [
                "# Week 9 Phase 2.1R-E — how early can the width signal be read?\n", "\n",
                "**Phase 2.1R showed the useful width number is almost always found in the first few "
                "percent of the trace. So: is an opening slice enough, and how short can it be?**\n", "\n",
                "This notebook reads the generated artifacts. The engine is "
                "`src/week9_phase2_1re_early_prefix_width_control.py`.\n",
            ],
        },
        {
            "cell_type": "code", "id": "esetup", "execution_count": None, "metadata": {}, "outputs": [],
            "source": [
                "import json\n", "from pathlib import Path\n", "import pandas as pd\n",
                "from IPython.display import display, Image\n",
                "pd.set_option('display.width', 190)\n",
                "pd.set_option('display.max_columns', 40)\n",
                "ROOT = Path.cwd().parents[1] if Path.cwd().name == 'week_09' else Path.cwd()\n",
                "OUT = ROOT / 'outputs' / 'week9_phase2_1re_early_prefix_width_control'\n",
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
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python", "version": "3"}},
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
        notebook, {"metadata": {"path": str(ROOT)}})
    nbformat.write(notebook, NOTEBOOK)
    return kernel


# --------------------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------------------
NEW_PATH_PREFIXES = (
    "src/week9_phase2_1re_early_prefix_width_control.py",
    "notebooks/week_09/08_week9_phase2_1re_early_prefix_width_control.ipynb",
    "outputs/week9_phase2_1re_early_prefix_width_control/",
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
             audit: pd.DataFrame, gate: pd.DataFrame, summary: pd.DataFrame, inference: pd.DataFrame,
             equivalence: pd.DataFrame, figures: list[Path], baseline_tree: set[str],
             include_notebook: bool) -> dict[str, Any]:
    module_source = Path(__file__).read_text(encoding="utf-8")
    physics_source = (ROOT / "src" / "week9_phase1_5_h_physics_confirmation.py").read_text(encoding="utf-8")
    model_columns = {c for _, columns, _ in MODELS.values() for c in columns}
    reports = ["FINAL_PHASE2_1RE_REPORT.md", "SUPERVISOR_PHASE2_1RE_ONE_PAGE.md", "claim_ledger.md"]
    report_text = {name: (OUTPUT / name).read_text(encoding="utf-8") for name in reports}

    contrast_markers = ("not ", "rather than", "instead", "would ", "never", "n't", "no raw")
    offending: list[str] = []
    for name, text in report_text.items():
        for sentence in re.split(r"(?<=[.;:])\s+|\n\n", text.lower()):
            if "raw" in sentence and ("timestep" in sentence or "solver step" in sentence):
                if not any(marker in sentence for marker in contrast_markers):
                    offending.append(f"{name}: {sentence.strip()[:110]}")

    checks: dict[str, bool] = {
        "population_405": len(population) == 405,
        "labels_73": int(population.has_keyhole.sum()) == 73,
        "usable_subset_350_70": len(features) == 350 and int(features.has_keyhole.sum()) == 70,
        "LS_is_laser_spot_radius": bool(np.allclose(population.LS, population.LS_m))
        and "Gaussian laser spot radius r0" in physics_source,
        "ST_is_substrate_temperature": bool(np.allclose(population.ST, population.ST_K))
        and '"ST_definition": "substrate temperature"' in physics_source,
        # prefix construction
        "prefix_no_future_audit_pass": bool(audit.status.eq("PASS").all()),
        "prefix_audit_covers_all_prefixes": len(audit) == len(PREFIXES),
        "full_prefix_equals_phase2_1r_feature": bool(np.allclose(
            features[feature_name(FULL_PREFIX)].to_numpy(float),
            pd.read_csv(PHASE21R / "simulation_level_features.csv")
            .set_index("experiment_name").loc[features.experiment_name, "max_positive_delta_W"]
            .to_numpy(float), atol=1e-9)),
        "prefix_windows_are_increasing": bool(
            np.all(np.diff([prefix_transition_count(p) for p in PREFIXES]) > 0)),
        # leakage and protocol
        "no_label_column_in_any_model": not bool(model_columns & {"has_keyhole", "truth"}),
        "no_evaluation_mask_in_any_model": not bool(model_columns & {"is_q20", "is_q30"}),
        "frozen_fold_count_100": len(w85.build_splits(population)) == 100,
        "no_new_random_split_declared": ("train_test" + "_split") not in module_source,
        "threshold_direction_learned_on_training": "learn_threshold" in module_source
        and "train_values" in module_source,
        # comparability
        "phase2_1r_reproduction_exact": bool(gate.status.eq("PASS").all()),
        "reproduction_gate_covers_both_shared_models": gate.phase2_1re_model.nunique() == 2,
        "shared_seed_string_with_phase2_1r": "week9_phase2_1r|" in module_source,
        # Tokens assembled from fragments so these checks cannot match themselves.
        # The point is that this module calls Phase 2.1R's fitter and never defines its
        # own kernel, model registry constant or metric function.
        "gpc_family_inherited_not_reinvented": ("r21._fit" + "_predict") in module_source
        and ("def g3" + "_kernel") not in module_source
        and ("def metric" + "_row") not in module_source,
        # inference discipline
        "holm_applied_to_every_contrast": bool(
            inference.groupby("contrast").holm_p_metric_family.apply(lambda s: s.notna().all()).all()),
        "equivalence_margin_predeclared": "EQUIVALENCE_MARGIN = " in module_source,
        "equivalence_uses_interval_not_pvalue": bool(
            {"interval_inside_margin", "equivalence_margin"} <= set(equivalence.columns)),
        # terminology
        "terminology_resampled_analysis_points": not offending,
        "reports_define_analysis_point": all(
            "consecutive resampled analysis point" in text for text in report_text.values()),
        # outputs
        "seven_figures": len(figures) == 7,
        "figures_exist": all(p.is_file() and p.stat().st_size > 0 for p in figures),
        "figure_manifest_hashes_match": all(
            sha256_file(OUTPUT / row.artifact) == row.sha256
            for row in pd.read_csv(OUTPUT / "figure_manifest.csv").itertuples()),
        "reports_exist": all((OUTPUT / name).is_file() for name in reports),
        "reports_open_with_what_did_we_ask": report_text["SUPERVISOR_PHASE2_1RE_ONE_PAGE.md"]
        .lstrip().startswith("# What did we actually ask?"),
        "reports_state_not_monitoring": all(
            "monitoring" in text.lower() for text in report_text.values()),
        # local-only
        "no_historical_file_touched": working_tree_fingerprint() == baseline_tree,
        "phase2_1r_outputs_untouched": not any(
            p.startswith("outputs/week9_phase2_1r_simple_width_change_control/")
            and p not in baseline_tree for p in working_tree_fingerprint()),
        "no_remote_operation_in_source": not any(
            token in module_source
            for token in ["git pu" + "sh", "gh " + "pr", "git rem" + "ote add", "requests." + "post"]),
        "no_raw_monitor_download": ("hf_hub" + "_download") not in module_source
        and ("snapshot" + "_download") not in module_source,
    }
    if include_notebook:
        notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        executed = [c for c in notebook["cells"] if c["cell_type"] == "code"
                    and c.get("execution_count") is not None and c.get("outputs")]
        errors = [o for c in notebook["cells"] for o in c.get("outputs", [])
                  if o.get("output_type") == "error"]
        checks["notebook_stores_executed_outputs"] = len(executed) >= 7
        checks["notebook_has_no_execution_errors"] = not errors

    failed = [name for name, value in checks.items() if not value]
    require(not failed, f"validation failed: {failed}"
                        + (f"; offending terminology: {offending[:3]}" if offending else ""))
    payload = {
        "status": "PASS", "phase": "Week 9 Phase 2.1R-E",
        "notebook_checks_included": include_notebook,
        "checks": checks, "check_count": len(checks),
        "prefixes_tested": list(PREFIXES), "primary_prefix": PRIMARY_PREFIX,
        "equivalence_margin": EQUIVALENCE_MARGIN,
        "usable_traces": len(features), "usable_keyholes": int(features.has_keyhole.sum()),
        "models_evaluated": len(MODELS),
        "output_bytes": directory_bytes(OUTPUT),
        "preexisting_dirty_paths_outside_this_phase": len(baseline_tree),
    }
    write_json(OUTPUT / "validation_report.json", payload)
    (OUTPUT / "validation_report.md").write_text(
        "# Week 9 Phase 2.1R-E validation report\n\n"
        f"**PASS** - {len(checks)} checks passed.\n\n"
        f"Prefixes tested: {list(PREFIXES)}; primary {PRIMARY_PREFIX}.\n"
        f"Usable simulations: {len(features)}/405 ({int(features.has_keyhole.sum())} Keyhole).\n"
        f"Phase 2.1R shared models reproduced exactly (4D baseline and 100% prefix).\n"
        f"New artifacts on disk: {directory_bytes(OUTPUT) / 1e6:.2f} MB. No raw monitor data downloaded.\n"
        f"Pre-existing dirty paths untouched: {len(baseline_tree)}.\n\n"
        + "\n".join(f"- PASS: {name}" for name in checks) + "\n",
        encoding="utf-8")
    return payload


# --------------------------------------------------------------------------------------
# orchestration
# --------------------------------------------------------------------------------------
def run() -> None:
    started = time.time()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    baseline_tree = working_tree_fingerprint()

    print("[1/7] population, inherited width traces, transition table", flush=True)
    population = r21.load_population()
    series = r21.load_width_series(population)
    table = r21.transition_table(series, population, RESOLUTION)

    print("[2/7] prefix features and the no-future audit", flush=True)
    features = build_prefix_features(table, population)
    write_csv(OUTPUT / "prefix_features.csv", features)
    audit = no_future_audit(table, features)
    saturation = saturation_profile(features)
    separation = univariate_by_prefix(features)

    print("[3/7] leak-free evaluation across prefixes", flush=True)
    predictions, thresholds = evaluate(population, features)
    repeat, summary = summarize(predictions)
    gate = reproduction_gate(summary)
    contrasts = paired_contrasts(repeat)
    inference = annotate(contrasts)
    equivalence = equivalence_test(contrasts)
    threshold_summary = summarize_thresholds(thresholds)

    print("[4/7] claim ledger", flush=True)
    claims, facts = build_claims(saturation, separation, threshold_summary, summary, inference,
                                 equivalence)

    print("[5/7] figures", flush=True)
    figures = make_figures(features, table, saturation, separation, threshold_summary, summary,
                           inference, equivalence, claims)

    print("[6/7] reports and notebook", flush=True)
    render_reports(population, features, saturation, separation, threshold_summary, summary,
                   inference, equivalence, gate, claims, facts, figures)
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    NOTEBOOK.write_text(json.dumps(notebook_payload(), indent=1) + "\n", encoding="utf-8")

    print("[7/7] validation", flush=True)
    validate(population, features, table, audit, gate, summary, inference, equivalence, figures,
             baseline_tree, include_notebook=False)
    kernel = execute_and_save_notebook()
    validation = validate(population, features, table, audit, gate, summary, inference, equivalence,
                          figures, baseline_tree, include_notebook=True)

    manifest = {
        "study": "Week 9 Phase 2.1R-E - early-prefix width control",
        "primary_question": "If the width signal is all at the start of the trace, is an opening "
                            "prefix enough?",
        "primary_contrast": PRIMARY_CONTRAST,
        "prefixes": list(PREFIXES), "primary_prefix": PRIMARY_PREFIX,
        "equivalence_margin": EQUIVALENCE_MARGIN,
        "median_observed_window_us_at_primary_prefix": facts["window_us"],
        "verdict_primary_hard": facts["primary_hard"],
        "verdict_primary_ranking": facts["primary_rank"],
        "rest_of_trace_equivalent_metrics": facts["equivalent_metrics"],
        "raw_solver_timesteps_used": False, "raw_monitor_bytes_downloaded": 0,
        "inherited_from": "src/week9_phase2_1r_simple_width_change_control.py",
        "models": {name: {"kind": kind, "features": list(columns), "role": role}
                   for name, (kind, columns, role) in MODELS.items()},
        "bootstrap_draws": BOOTSTRAP_DRAWS, "signflip_draws": SIGNFLIP_DRAWS, "seed": SEED,
        "notebook_kernel": kernel, "notebook_sha256": sha256_file(NOTEBOOK),
        "local_only": True, "new_worktree_or_clone_created": False,
        "new_artifact_bytes": directory_bytes(OUTPUT) + NOTEBOOK.stat().st_size,
        "validation": validation, "elapsed_seconds": time.time() - started,
    }
    manifest["artifact_hashes"] = {
        str(path.relative_to(OUTPUT)).replace("\\", "/"): sha256_file(path)
        for path in sorted(OUTPUT.rglob("*")) if path.is_file() and path.name != "run_manifest.json"}
    write_json(OUTPUT / "run_manifest.json", manifest)
    print(json.dumps({
        "status": "PASS",
        "primary_prefix": PRIMARY_PREFIX,
        "median_window_us": round(facts["window_us"], 1),
        "fraction_already_full_value": round(facts["equal_share"], 4),
        "primary_hard": facts["primary_hard"],
        "primary_ranking": facts["primary_rank"],
        "q20_metrics_equivalent_to_full_trace": f"{facts['equivalent_metrics']}/6",
        "new_artifact_megabytes": round(manifest["new_artifact_bytes"] / 1e6, 2),
        "elapsed_seconds": round(time.time() - started, 1),
    }, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Week 9 Phase 2.1R-E early-prefix width control")
    parser.add_argument("--run", action="store_true", help="run the full Phase 2.1R-E study")
    args = parser.parse_args()
    if args.run:
        run()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
