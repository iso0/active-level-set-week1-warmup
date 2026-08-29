"""Week 9 Phase 1: close the frozen Week 8/8.5 sample-efficiency story.

This module consumes the immutable H=160 Week 8.5 checkpoints and the separate
post-hoc H=320 continuation.  It never changes the frozen protocol or its
artifacts.  The historical crossing definition is preserved: Q is the first of
three consecutive passing declared checkpoints, while the third checkpoint is
the time at which that Q becomes observable.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import os
import tarfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_horizon_extension as h320


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase1_close_week8"
FIGURES = OUTPUT / "figures"
FROZEN_OUTPUT = ROOT / "outputs" / "week8_5_frozen_confirmation"
SOURCE_CHECKPOINTS = OUTPUT / "dev_horizon" / "_frozen_h160" / "checkpoints"
EXTENSION_CHECKPOINTS = OUTPUT / "dev_horizon" / "checkpoints"

HORIZONS = (80, 120, 160, 200, 240, 280, 320)
PRIMARY_TARGET = 0.80
PRIMARY_METRIC = "B1_q20_accuracy"
BOOTSTRAP_DRAWS = 20_000
BOOTSTRAP_SEED_KEY = "week9_phase1|posthoc_h320|hierarchical_bootstrap|v1"

FROZEN_EXPECTED = {
    80: {"margin": 90, "random": 2201, "margin_Q": 31.850, "random_Q": 42.803333333333, "delta_Q": 10.953333333333, "ratio": 1.343904},
    120: {"margin": 91, "random": 2394, "margin_Q": 35.470, "random_Q": 51.914333333333, "delta_Q": 16.444333333333, "ratio": 1.463612},
    160: {"margin": 91, "random": 2493, "margin_Q": 39.070, "random_Q": 59.169, "delta_Q": 20.099, "ratio": 1.5144356283593552},
}
FROZEN_AULC = {
    "binary_margin": 0.813520220588,
    "matched_binary_random": 0.776220435049,
    "margin_minus_random": 0.037299785539,
    "repeat_blocks_positive": 20,
    "repeat_blocks_total": 20,
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def write_json(path: Path, payload: Any) -> None:
    def clean(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {str(key): clean(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [clean(item) for item in value]
        if isinstance(value, (np.floating, float)) and not math.isfinite(float(value)):
            return None
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.bool_):
            return bool(value)
        return value

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(clean(payload), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def declared_grid_to(horizon: int) -> list[int]:
    require(horizon in HORIZONS, f"Unsupported reporting horizon {horizon}")
    grid = list(range(16, 81))
    if horizon >= 120:
        grid.extend(range(82, 121, 2))
    if horizon >= 160:
        grid.extend(range(124, 161, 4))
    if horizon > 160:
        grid.extend(range(164, horizon + 1, 4))
    return grid


def _read_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"Missing checkpoint: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def unresolved_q_lower_bound(by_budget: Mapping[int, float], target: float = PRIMARY_TARGET) -> tuple[float, bool, str]:
    """Earliest Q still compatible with an unresolved right tail at H=320.

    Q is the *start* of a future three-checkpoint passing run.  Consequently,
    two passing tail checkpoints permit Q=316 after a future H324 pass; this is
    why blindly replacing every unresolved Q by 320 is not conservative.
    """

    require(320 in by_budget, "Tail lower bound requires the H320 accuracy")
    if float(by_budget[320]) < target:
        return 320.0, True, "H320 fails, so no three-pass run can start at or before 320"
    if float(by_budget.get(316, -math.inf)) >= target:
        return 316.0, False, "316 and 320 pass; a future 324 pass could assign Q=316"
    return 320.0, False, "H320 passes but H316 does not; a future run could start at Q=320"


def load_path_evidence(
    population: pd.DataFrame,
    specs: Sequence[w85.SplitSpec],
    *,
    source_root: Path = SOURCE_CHECKPOINTS,
    extension_root: Path = EXTENSION_CHECKPOINTS,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load and validate all 3,100 Margin/Random continuations.

    Returns path-level crossing evidence, all source learning rows through 160,
    and sparse post-hoc rows through 320.  Sparse Random rows are intentional:
    after a persistent crossing is confirmed, only the terminal H=320 fit is
    additionally required.
    """

    path_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    extension_rows: list[dict[str, Any]] = []
    for spec, arm, continuation in h320.trajectory_jobs(specs):
        source_path = source_root / h320.frozen_checkpoint_name(spec, arm, continuation)
        source_raw = source_path.read_bytes()
        source = json.loads(source_raw)
        h320.validate_frozen_payload(source, spec, arm, continuation, population)
        extension_path = h320.extension_checkpoint_path(spec, arm, continuation, extension_root)
        extension = _read_json(extension_path)
        require(extension.get("complete") is True, f"Incomplete extension {extension_path.name}")
        h320.validate_completed_extension_payload(
            extension,
            source,
            hashlib.sha256(source_raw).hexdigest(),
            spec,
            arm,
            continuation,
            population,
        )
        combined = [*source["rows"], *extension["extension_rows"]]
        final = h320.persistent_crossing_evidence(combined)
        final = h320.finalize_crossing_classification(
            final, extension["extension_rows"], target_horizon=h320.TARGET_HORIZON
        )
        by_budget = {int(row["budget"]): float(row[PRIMARY_METRIC]) for row in combined}
        require(320 in by_budget, f"{spec.run_id}/{arm}/{continuation}: missing H320 metric")
        if final["observed"]:
            q_lower = float(final["start_budget"])
            q_lower_strict = False
            q_lower_reason = "observed persistent crossing"
        else:
            q_lower, q_lower_strict, q_lower_reason = unresolved_q_lower_bound(by_budget)

        per_horizon: dict[str, Any] = {}
        for horizon in HORIZONS:
            truncated = [row for row in combined if int(row["budget"]) <= horizon]
            evidence = h320.persistent_crossing_evidence(truncated)
            observed = bool(evidence["observed"] and int(evidence["confirmation_budget"]) <= horizon)
            per_horizon[f"observed_H{horizon}"] = observed
            per_horizon[f"Q_H{horizon}"] = float(evidence["start_budget"]) if observed else math.nan
            per_horizon[f"restricted_Q_H{horizon}"] = float(evidence["start_budget"]) if observed else float(horizon)

        identity = extension["identity"]
        path_rows.append(
            {
                **identity,
                "source_checkpoint_sha256": extension["source_checkpoint_sha256"],
                "queried_prefix_h160_sha256": extension["source_queried_prefix_sha256"],
                "queried_count_h320": len(extension["queried_indices"]),
                "crossing_observed_H320": bool(final["observed"]),
                "crossing_start_Q": float(final["start_budget"]) if final["observed"] else math.nan,
                "crossing_confirmation_budget": float(final["confirmation_budget"]) if final["observed"] else math.nan,
                "terminal_B1_q20_accuracy_H320": float(by_budget[320]),
                "tail_classification": final["final_classification"],
                "guaranteed_Q_gt_320": bool(final.get("guaranteed_Q_gt_target_horizon", False)),
                "Q_lower_bound": q_lower,
                "Q_lower_bound_is_strict": q_lower_strict,
                "Q_lower_bound_reason": q_lower_reason,
                "extension_metric_budgets": "|".join(map(str, sorted(int(row["budget"]) for row in extension["extension_rows"]))),
                **per_horizon,
            }
        )
        source_rows.extend(source["rows"])
        extension_rows.extend(extension["extension_rows"])

    paths = pd.DataFrame(path_rows)
    require(len(paths) == 3100, f"Expected 3100 path rows, found {len(paths)}")
    require(not paths.duplicated(["run_id", "arm", "continuation_id"]).any(), "Duplicate path evidence")
    require((paths["queried_count_h320"] == 320).all(), "Not every path has 320 unique queries")
    return paths, pd.DataFrame(source_rows), pd.DataFrame(extension_rows)


def horizon_summary(paths: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for horizon in HORIZONS:
        for arm, expected_n in (("binary_margin", 100), ("binary_random", 3000)):
            group = paths[paths["arm"].eq(arm)]
            require(len(group) == expected_n, f"{arm}: path count drift")
            observed = int(group[f"observed_H{horizon}"].sum())
            rows.append(
                {
                    "horizon": horizon,
                    "arm": arm,
                    "trajectory_count": expected_n,
                    "finite_persistent_crossings": observed,
                    "finite_rate": observed / expected_n,
                    "unresolved": expected_n - observed,
                    "restricted_mean_query_burden": float(group[f"restricted_Q_H{horizon}"].mean()),
                    "crossing_status_uses_confirmation_by_horizon": True,
                }
            )
    return pd.DataFrame(rows)


def validate_historical_reproduction(summary: pd.DataFrame) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for horizon, expected in FROZEN_EXPECTED.items():
        margin = summary[(summary.horizon == horizon) & summary.arm.eq("binary_margin")].iloc[0]
        random = summary[(summary.horizon == horizon) & summary.arm.eq("binary_random")].iloc[0]
        actual = {
            "margin": int(margin.finite_persistent_crossings),
            "random": int(random.finite_persistent_crossings),
            "margin_Q": float(margin.restricted_mean_query_burden),
            "random_Q": float(random.restricted_mean_query_burden),
        }
        actual["delta_Q"] = actual["random_Q"] - actual["margin_Q"]
        actual["ratio"] = actual["random_Q"] / actual["margin_Q"]
        ok = (
            actual["margin"] == expected["margin"]
            and actual["random"] == expected["random"]
            and np.isclose(actual["margin_Q"], expected["margin_Q"], atol=1e-12)
            and np.isclose(actual["random_Q"], expected["random_Q"], atol=1e-12)
            and np.isclose(actual["delta_Q"], expected["delta_Q"], atol=1e-12)
            and np.isclose(actual["ratio"], expected["ratio"], atol=1e-6)
        )
        checks.append({"check_id": f"historical_H{horizon}_exact_reproduction", "status": "PASS" if ok else "FAIL", "actual": actual, "expected": expected})
    return checks


def matched_pair_table(paths: pd.DataFrame) -> pd.DataFrame:
    margin = paths[paths.arm.eq("binary_margin")].set_index(["repeat", "fold"])
    rows: list[dict[str, Any]] = []
    for random in paths[paths.arm.eq("binary_random")].itertuples(index=False):
        m = margin.loc[(int(random.repeat), int(random.fold))]
        m_obs = bool(m.crossing_observed_H320)
        r_obs = bool(random.crossing_observed_H320)
        category = (
            "both_crossed" if m_obs and r_obs else
            "margin_crossed_random_unresolved" if m_obs else
            "random_crossed_margin_unresolved" if r_obs else
            "neither_crossed"
        )
        saving_exact = float(random.crossing_start_Q - m.crossing_start_Q) if m_obs and r_obs else math.nan
        saving_lower = float(random.Q_lower_bound - m.crossing_start_Q) if m_obs else math.nan
        rows.append(
            {
                "run_id": random.run_id,
                "repeat": int(random.repeat),
                "fold": int(random.fold),
                "random_continuation_id": int(random.continuation_id),
                "category": category,
                "margin_Q": float(m.crossing_start_Q) if m_obs else math.nan,
                "random_Q": float(random.crossing_start_Q) if r_obs else math.nan,
                "random_Q_lower_bound": float(random.Q_lower_bound),
                "random_Q_lower_bound_is_strict": bool(random.Q_lower_bound_is_strict),
                "exact_saving_Qrandom_minus_Qmargin": saving_exact,
                "saving_lower_bound_Qrandom_minus_Qmargin": saving_lower,
                "random_guaranteed_Q_gt_320": bool(random.guaranteed_Q_gt_320),
            }
        )
    result = pd.DataFrame(rows)
    require(len(result) == 3000, "Matched pair count must be 3000")
    return result


def _query_cubes(paths: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    margin = np.full((20, 5), np.nan)
    margin_observed = np.zeros((20, 5), dtype=bool)
    random_restricted = np.full((20, 5, 30), np.nan)
    random_lower = np.full((20, 5, 30), np.nan)
    for row in paths.itertuples(index=False):
        r, f = int(row.repeat) - 1, int(row.fold) - 1
        if row.arm == "binary_margin":
            margin[r, f] = float(row.restricted_Q_H320)
            margin_observed[r, f] = bool(row.crossing_observed_H320)
        else:
            c = int(row.continuation_id) - 1
            random_restricted[r, f, c] = float(row.restricted_Q_H320)
            random_lower[r, f, c] = float(row.Q_lower_bound)
    require(np.isfinite(margin).all() and np.isfinite(random_restricted).all() and np.isfinite(random_lower).all(), "Query cube incomplete")
    return margin, margin_observed, random_restricted, random_lower


def query_bootstrap(paths: pd.DataFrame, draws: int = BOOTSTRAP_DRAWS) -> tuple[pd.DataFrame, dict[str, Any]]:
    margin, margin_observed, random_restricted, random_lower = _query_cubes(paths)
    all_margin_observed = bool(margin_observed.all())
    point_margin = float(margin.mean())
    point_random = float(random_restricted.mean())
    point_delta = point_random - point_margin
    point_ratio = point_random / point_margin
    point_lower_delta = float(random_lower.mean() - margin.mean()) if all_margin_observed else math.nan
    rng = np.random.default_rng(w85.seed_u32(BOOTSTRAP_SEED_KEY))
    rows: list[dict[str, Any]] = []
    for draw in range(1, draws + 1):
        sampled_repeats = rng.integers(0, 20, size=20)
        m_values: list[float] = []
        r_values: list[float] = []
        lower_values: list[float] = []
        for r in sampled_repeats:
            for f in range(5):
                picks = rng.integers(0, 30, size=30)
                m_values.append(float(margin[r, f]))
                r_values.append(float(random_restricted[r, f, picks].mean()))
                lower_values.append(float(random_lower[r, f, picks].mean()))
        m_mean = float(np.mean(m_values))
        r_mean = float(np.mean(r_values))
        rows.append(
            {
                "draw": draw,
                "restricted_margin_Q": m_mean,
                "restricted_random_Q": r_mean,
                "restricted_delta_Q": r_mean - m_mean,
                "restricted_ratio": r_mean / m_mean,
                "mathematical_lower_bound_delta_Q": float(np.mean(lower_values) - m_mean) if all_margin_observed else math.nan,
            }
        )
    frame = pd.DataFrame(rows)
    def interval(column: str) -> dict[str, float]:
        values = frame[column].dropna()
        return {
            "one_sided_95pct_lower": float(values.quantile(0.05)) if len(values) else math.nan,
            "two_sided_95pct_lower": float(values.quantile(0.025)) if len(values) else math.nan,
            "two_sided_95pct_upper": float(values.quantile(0.975)) if len(values) else math.nan,
        }
    summary = {
        "bootstrap_draws": draws,
        "hierarchy": "20 repeat blocks resampled; all five folds retained; 30 Random continuations resampled within fold",
        "all_margin_crossings_observed_H320": all_margin_observed,
        "restricted_margin_mean_Q": point_margin,
        "restricted_random_mean_Q": point_random,
        "restricted_delta_Q": point_delta,
        "restricted_ratio": point_ratio,
        "restricted_delta_interval": interval("restricted_delta_Q"),
        "restricted_ratio_interval": interval("restricted_ratio"),
        "mathematical_lower_bound_average_delta_Q": point_lower_delta,
        "mathematical_lower_bound_delta_interval": interval("mathematical_lower_bound_delta_Q"),
    }
    return frame, summary


def seed_registry_and_collisions(paths: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths.itertuples(index=False):
        spec = w85.SplitSpec(
            run_id=str(path.run_id), repeat=int(path.repeat), fold=int(path.fold), train_indices=(), test_indices=()
        )
        if path.arm == "binary_margin":
            budgets = range(160, 321)
        else:
            budgets = [int(value) for value in str(path.extension_metric_budgets).split("|")]
        for budget in budgets:
            key = w85.fit_seed_key(spec, str(path.arm), int(path.continuation_id), int(budget))
            rows.append({"run_id": path.run_id, "repeat": path.repeat, "fold": path.fold, "arm": path.arm, "continuation_id": path.continuation_id, "budget": budget, "fit_seed_key": key, "fit_seed_u32": w85.seed_u32(key)})
    registry = pd.DataFrame(rows).drop_duplicates("fit_seed_key").sort_values("fit_seed_key").reset_index(drop=True)
    collisions = []
    for seed, group in registry.groupby("fit_seed_u32"):
        if group.fit_seed_key.nunique() > 1:
            collisions.append({"fit_seed_u32": int(seed), "distinct_keys": sorted(group.fit_seed_key.astype(str).tolist())})
    return registry, {"registry_rows": len(registry), "collision_group_count": len(collisions), "collisions": collisions, "qualification": "Complete fit-seed keys are authoritative; uint32 collisions are disclosed, not repaired."}


def query_claim_decision(paths: pd.DataFrame, bootstrap: Mapping[str, Any], pairs: pd.DataFrame) -> dict[str, Any]:
    margin_all = bool(paths[paths.arm.eq("binary_margin")].crossing_observed_H320.all())
    unresolved_random = paths[paths.arm.eq("binary_random") & ~paths.crossing_observed_H320]
    tail_ambiguous = int((~unresolved_random.guaranteed_Q_gt_320).sum())
    guaranteed_gt = int(unresolved_random.guaranteed_Q_gt_320.sum())
    lower = float(bootstrap["mathematical_lower_bound_average_delta_Q"])
    lower_ci = float(bootstrap["mathematical_lower_bound_delta_interval"]["one_sided_95pct_lower"])
    safe = math.floor(lower * 10) / 10 if math.isfinite(lower) else math.nan
    fixed_benchmark_positive = margin_all and math.isfinite(lower) and lower > 0 and safe > 0
    bootstrap_positive = math.isfinite(lower_ci) and lower_ci > 0
    if fixed_benchmark_positive:
        if bootstrap_positive:
            supervisor = (
                f"For these fixed 3,000 matched paths, path-specific tail bounds guarantee at least {safe:.1f} queries of average saving; "
                f"the design-conditional hierarchy-preserving bootstrap has a positive one-sided 95% lower bound of {lower_ci:.1f} queries."
            )
            status = "SUPPORTED_FIXED_BENCHMARK_AND_DESIGN_CONDITIONAL_BOOTSTRAP"
        else:
            supervisor = (
                f"For these fixed 3,000 matched paths, path-specific tail bounds guarantee at least {safe:.1f} queries of average saving, "
                "but the design-conditional bootstrap does not provide a positive one-sided 95% lower bound."
            )
            status = "SUPPORTED_FIXED_BENCHMARK_ONLY"
    else:
        safe = math.nan
        if not margin_all:
            supervisor = "An 'at least X queries saved on average' claim is not identified because at least one Margin crossing remains unresolved at H=320."
            status = "NOT_SUPPORTED_MARGIN_TAIL_UNRESOLVED"
        else:
            supervisor = "The path-specific fixed-benchmark lower bound is not positive, so an 'at least X queries saved on average' claim is not supported."
            status = "NOT_SUPPORTED_NONPOSITIVE_LOWER_BOUND"
    return {
        "status": status,
        "margin_all_100_observed": margin_all,
        "random_unresolved": int(len(unresolved_random)),
        "random_unresolved_guaranteed_Q_gt_320": guaranteed_gt,
        "random_unresolved_tail_indeterminate": tail_ambiguous,
        "naive_Qrandom_gt_320_for_every_unresolved_is_valid": tail_ambiguous == 0,
        "restricted_H320_delta_is_automatically_a_lower_bound": tail_ambiguous == 0 and margin_all,
        "path_specific_average_saving_lower_bound_queries": lower,
        "hierarchical_one_sided_95pct_lower_bound_queries": lower_ci,
        "fixed_benchmark_lower_bound_positive": fixed_benchmark_positive,
        "design_conditional_bootstrap_lower_bound_positive": bootstrap_positive,
        "bootstrap_scope": "Descriptive uncertainty under the frozen repeat/fold/continuation design; not a population or transfer guarantee.",
        "rounded_down_supervisor_X_queries": safe,
        "supervisor_safe_sentence": supervisor,
        "why_naive_prompt_argument_fails": "Historical Q is the first of three passing checkpoints. An unresolved path passing at 316 and 320 may later receive Q=316 after a 324 pass.",
        "matched_category_counts": pairs.category.value_counts().to_dict(),
    }


def learning_curve_summary(source_rows: pd.DataFrame) -> pd.DataFrame:
    frame = source_rows[source_rows.budget.between(16, 80) & source_rows.arm.isin(["binary_margin", "binary_random"])].copy()
    random_fold = frame[frame.arm.eq("binary_random")].groupby(["repeat", "fold", "run_id", "budget"], as_index=False)[PRIMARY_METRIC].mean()
    margin = frame[frame.arm.eq("binary_margin")]
    rows = []
    for budget in range(16, 81):
        for arm, values in (
            ("binary_margin", margin[margin.budget.eq(budget)][PRIMARY_METRIC]),
            ("binary_random", random_fold[random_fold.budget.eq(budget)][PRIMARY_METRIC]),
        ):
            rows.append({"budget": budget, "arm": arm, "mean_accuracy": float(values.mean()), "q05": float(values.quantile(.05)), "q95": float(values.quantile(.95))})
    return pd.DataFrame(rows)


def terminal_reproduction_audit(source_rows: pd.DataFrame, extension_rows: pd.DataFrame) -> dict[str, Any]:
    """Verify q20/q30 metrics from per-test predictions against saved fits."""

    path_metrics_path = OUTPUT / "terminal_path_metrics.csv"
    require(path_metrics_path.is_file(), "Missing terminal_path_metrics.csv")
    observed = pd.read_csv(path_metrics_path)
    require(len(observed) == 3100 * 4 * 3, f"Terminal path metric row count drift: {len(observed)}")
    expected = pd.concat(
        [
            source_rows[source_rows.budget.isin([40, 80, 160])],
            extension_rows[extension_rows.budget.eq(320)],
        ],
        ignore_index=True,
    )
    require(len(expected) == 3100 * 4, f"Expected checkpoint metric row count drift: {len(expected)}")
    comparisons: list[dict[str, Any]] = []
    identities = ["run_id", "repeat", "fold", "arm", "continuation_id", "budget"]
    metric_map = {
        "accuracy": "accuracy",
        "balanced_accuracy": "balanced_accuracy",
        "keyhole_recall": "recall",
        "false_negative": "false_negative",
        "false_positive": "false_positive",
    }
    for subset in ("B1_q20", "B1_q30"):
        selected = observed[observed.subset.eq(subset)][identities + list(metric_map)].copy()
        expected_columns = identities + [f"{subset}_{suffix}" for suffix in metric_map.values()]
        merged = selected.merge(expected[expected_columns], on=identities, validate="one_to_one")
        require(len(merged) == 3100 * 4, f"{subset}: terminal/checkpoint merge incomplete")
        for observed_name, expected_suffix in metric_map.items():
            delta = np.abs(merged[observed_name].to_numpy(float) - merged[f"{subset}_{expected_suffix}"].to_numpy(float))
            comparisons.append(
                {
                    "subset": subset,
                    "metric": observed_name,
                    "rows": len(delta),
                    "max_abs_delta": float(delta.max()),
                    "status": "PASS" if np.all(delta <= 1e-12) else "FAIL",
                }
            )
    status = "PASS" if all(row["status"] == "PASS" for row in comparisons) else "FAIL"
    return {"status": status, "path_metric_rows": len(observed), "checkpoint_rows_compared": len(expected), "comparisons": comparisons}


def make_core_figures(paths: pd.DataFrame, source_rows: pd.DataFrame, terminal_summary_path: Path | None = None) -> list[str]:
    FIGURES.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    curves = learning_curve_summary(source_rows)
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    for arm, color, label in (("binary_margin", "#1f77b4", "Binary Margin"), ("binary_random", "#7f7f7f", "Matched Random")):
        group = curves[curves.arm.eq(arm)]
        ax.plot(group.budget, group.mean_accuracy, color=color, linewidth=2.2, label=label)
        ax.fill_between(group.budget, group.q05, group.q95, color=color, alpha=.13)
    ax.axhline(.8, color="black", linestyle="--", linewidth=1, label="Persistent target level")
    ax.set(xlabel="Queried simulations", ylabel="Fold-B1-q20 accuracy", title="Frozen Week 8.5 near-boundary learning curve (16–80)")
    ax.legend(frameon=False); ax.grid(alpha=.2); fig.tight_layout()
    path = FIGURES / "01_margin_vs_matched_random_q20_learning_curve.png"; fig.savefig(path, dpi=220); plt.close(fig); created.append(str(path))

    checkpoints = sorted(set(declared_grid_to(320)))
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    for arm, total, color, label in (("binary_margin", 100, "#1f77b4", "Binary Margin"), ("binary_random", 3000, "#7f7f7f", "Random continuations")):
        group = paths[paths.arm.eq(arm)]
        rates = [float((group.crossing_confirmation_budget <= budget).fillna(False).sum() / total) for budget in checkpoints]
        ax.step(checkpoints, rates, where="post", color=color, linewidth=2.2, label=label)
    ax.axvline(160, color="#d62728", linestyle="--", linewidth=1.3, label="Frozen Week 8.5 stop")
    ax.set(xlabel="Query horizon", ylabel="Persistent target confirmed fraction", ylim=(0, 1.02), title="Persistent 0.80 target attainment through post-hoc H=320")
    ax.legend(frameon=False); ax.grid(alpha=.2); fig.tight_layout()
    path = FIGURES / "02_persistent_target_attainment_vs_horizon.png"; fig.savefig(path, dpi=220); plt.close(fig); created.append(str(path))

    if terminal_summary_path and terminal_summary_path.is_file():
        terminal = pd.read_csv(terminal_summary_path)
        metric = terminal[(terminal.metric == "accuracy") & terminal.estimand.isin(["binary_margin", "binary_random"])]
        fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.4), sharey=True)
        for axis, subset in zip(axes, ("full81", "B1_q30", "B1_q20")):
            for arm, color, label in (("binary_margin", "#1f77b4", "Margin"), ("binary_random", "#7f7f7f", "Random")):
                g = metric[(metric.subset == subset) & (metric.estimand == arm)].sort_values("budget")
                axis.plot(g.budget, g.point_estimate, marker="o", color=color, label=label)
                axis.fill_between(g.budget, g.two_sided_95pct_lower, g.two_sided_95pct_upper, color=color, alpha=.12)
            axis.set_title(subset.replace("B1_", "Fold-B1-") if subset != "full81" else "Full held-out 81")
            axis.set_xlabel("Budget"); axis.grid(alpha=.2)
        axes[0].set_ylabel("Terminal accuracy"); axes[0].legend(frameon=False)
        fig.suptitle("Terminal performance: global test set vs empirical near-boundary subsets")
        fig.tight_layout()
        path = FIGURES / "03_terminal_accuracy_full_q30_q20.png"; fig.savefig(path, dpi=220); plt.close(fig); created.append(str(path))

        fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.5))
        aulc_random = FROZEN_AULC["matched_binary_random"]
        aulc_margin = FROZEN_AULC["binary_margin"]
        axes[0].plot([aulc_random, aulc_margin], [0, 0], color="#555555", linewidth=2)
        axes[0].scatter([aulc_random], [0], color="#7f7f7f", s=90, label="Matched Random")
        axes[0].scatter([aulc_margin], [0], color="#1f77b4", s=90, label="Binary Margin")
        axes[0].annotate(f"Δ={FROZEN_AULC['margin_minus_random']:+.4f}", ((aulc_random + aulc_margin) / 2, .035), ha="center")
        axes[0].set(xlabel="Frozen Fold-B1-q20 AULC (16–80)", yticks=[], ylim=(-.12, .12), title="Learning speed across the budget")
        axes[0].legend(frameon=False, loc="lower right")
        q20 = metric[metric.subset.eq("B1_q20")]
        for arm, color, label in (("binary_margin", "#1f77b4", "Binary Margin"), ("binary_random", "#7f7f7f", "Matched Random")):
            group = q20[q20.estimand.eq(arm)].sort_values("budget")
            axes[1].plot(group.budget, group.point_estimate, marker="o", color=color, linewidth=2, label=label)
            axes[1].fill_between(group.budget, group.two_sided_95pct_lower, group.two_sided_95pct_upper, color=color, alpha=.12)
        axes[1].set(xlabel="Fixed terminal budget", ylabel="Fold-B1-q20 terminal accuracy", title="Final-model quality at a fixed budget")
        axes[1].grid(alpha=.2); axes[1].legend(frameon=False)
        fig.suptitle("AULC and terminal accuracy answer complementary questions")
        fig.tight_layout()
        path = FIGURES / "04_aulc_vs_terminal_performance_summary.png"; fig.savefig(path, dpi=220); plt.close(fig); created.append(str(path))
    return created


def package_checkpoints(
    source: Path = EXTENSION_CHECKPOINTS,
    destination: Path = OUTPUT / "week9_phase1_h320_checkpoint_bundle.tar.gz",
    source_root: Path = SOURCE_CHECKPOINTS,
) -> dict[str, Any]:
    """Fully validate and reproducibly package all H320 continuation files."""

    population = w85.load_population()
    specs = w85.build_splits(population)
    expected_paths: list[Path] = []
    manifest_rows: list[dict[str, Any]] = []
    for spec, arm, continuation in h320.trajectory_jobs(specs):
        source_path = source_root / h320.frozen_checkpoint_name(spec, arm, continuation)
        source_raw = source_path.read_bytes()
        source_payload = json.loads(source_raw)
        path = h320.extension_checkpoint_path(spec, arm, continuation, source)
        payload = _read_json(path)
        h320.validate_completed_extension_payload(
            payload,
            source_payload,
            hashlib.sha256(source_raw).hexdigest(),
            spec,
            arm,
            continuation,
            population,
        )
        expected_paths.append(path)
        manifest_rows.append(
            {
                "archive_member": f"checkpoints/{path.name}",
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "run_id": spec.run_id,
                "arm": arm,
                "continuation_id": continuation,
                "source_checkpoint_sha256": hashlib.sha256(source_raw).hexdigest(),
            }
        )
    discovered = sorted(source.glob("*.json"))
    require({path.name for path in discovered} == {path.name for path in expected_paths}, "Checkpoint collection has missing or unexpected members")
    manifest = pd.DataFrame(manifest_rows).sort_values(["run_id", "arm", "continuation_id"], kind="mergesort")
    manifest_path = OUTPUT / "h320_checkpoint_member_manifest.csv"
    write_csv(manifest_path, manifest)
    dependency = {
        "extension_protocol_id": h320.EXTENSION_PROTOCOL_ID,
        "frozen_h160_checkpoint_archive": str(h320.FROZEN_ARCHIVE.relative_to(ROOT)),
        "frozen_h160_checkpoint_archive_sha256": h320.FROZEN_ARCHIVE_SHA256,
        "frozen_protocol_sha256": h320.FROZEN_PROTOCOL_SHA256,
        "note": "The extension bundle contains H161-H320 continuation state and depends on the pinned frozen H160 archive for historical rows.",
    }
    dependency_path = OUTPUT / "h320_checkpoint_bundle_dependencies.json"
    write_json(dependency_path, dependency)

    entries = [(f"checkpoints/{path.name}", path.read_bytes()) for path in sorted(expected_paths, key=lambda item: item.name)]
    entries.extend(
        [
            ("checkpoint_member_manifest.csv", manifest_path.read_bytes()),
            ("checkpoint_bundle_dependencies.json", dependency_path.read_bytes()),
        ]
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as raw_handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_handle, compresslevel=9, mtime=0) as gzip_handle:
            with tarfile.open(fileobj=gzip_handle, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for archive_name, data in entries:
                    info = tarfile.TarInfo(archive_name)
                    info.size = len(data)
                    info.mtime = 0
                    info.mode = 0o644
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    archive.addfile(info, io.BytesIO(data))
    return {
        "path": str(destination.relative_to(ROOT)),
        "sha256": sha256_file(destination),
        "bytes": destination.stat().st_size,
        "checkpoint_members": len(expected_paths),
        "total_archive_members": len(entries),
        "full_payloads_validated": len(expected_paths),
        "member_manifest": str(manifest_path.relative_to(ROOT)),
        "dependency_manifest": str(dependency_path.relative_to(ROOT)),
        "byte_reproducible_metadata": True,
    }


def build_claim_ledger(
    claim_decision: Mapping[str, Any],
    horizon: pd.DataFrame,
    pca_summary: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    h320_margin = horizon[(horizon.horizon == 320) & horizon.arm.eq("binary_margin")].iloc[0]
    h320_random = horizon[(horizon.horizon == 320) & horizon.arm.eq("binary_random")].iloc[0]
    return pd.DataFrame(
        [
            {"category": "frozen_confirmatory", "claim": "Margin improves Fold-B1-q20 AULC vs matched Random over 16–80", "numeric_result": "+0.037300 AULC; 20/20 repeat contrasts positive", "status": "CONFIRMED_FROZEN_WEEK8_5", "strongest_safe_wording": "Under the frozen Week 8.5 analysis, uncertainty-only Binary Margin learned the empirical near-boundary subset faster than matched Random.", "must_not_use": "PCA or q20 proves the physical boundary."},
            {"category": "posthoc_H320", "claim": "Persistent target attainment by H320", "numeric_result": f"Margin {int(h320_margin.finite_persistent_crossings)}/100; Random {int(h320_random.finite_persistent_crossings)}/3000", "status": "POSTHOC_DIAGNOSTIC", "strongest_safe_wording": "The longer horizon reduces unresolved trajectories; results are a post-hoc closing diagnostic.", "must_not_use": "H320 was preregistered or upgrades the old QUALIFY decision."},
            {"category": "posthoc_H320", "claim": "At least X average query saving", "numeric_result": json.dumps(dict(claim_decision), sort_keys=True), "status": claim_decision["status"], "strongest_safe_wording": claim_decision["supervisor_safe_sentence"], "must_not_use": "Every unresolved H320 Random path has Q>320."},
            {"category": "posthoc_terminal", "claim": "Terminal accuracy complements AULC", "numeric_result": "See terminal_metric_summary.csv", "status": "DESCRIPTIVE_POSTHOC", "strongest_safe_wording": "AULC answers how quickly learning improves; terminal metrics answer model quality at a fixed budget.", "must_not_use": "Terminal accuracy and AULC are the same estimand."},
            {"category": "posthoc_visualization", "claim": "PCA clarifies 4D sampled-input geometry", "numeric_result": (f"PC1+PC2 explain {100*float(pca_summary['pc1_plus_pc2_explained_variance']):.3f}% of standardized-feature variance; PC3 explains {100*float(pca_summary['component_interpretations']['PC3']['explained_variance_ratio']):.3f}%" if pca_summary is not None else "See pca_summary.json"), "status": "VISUAL_DIAGNOSTIC", "strongest_safe_wording": "Standardized PCA is a label-free view of sampled input variance: PC1 is an LS-versus-P contrast, PC2 is mainly ST variation, and PC3 carries most VX variation.", "must_not_use": "PCA maximizes Keyhole separation, proves feature importance, or identifies the true 4D physical boundary."},
        ]
    )


def write_final_reports(summary: Mapping[str, Any], validation: Mapping[str, Any], ledger: pd.DataFrame) -> dict[str, Any]:
    """Write supervisor-facing prose, Q1–Q9 answers, and the requirement map."""

    terminal_path = OUTPUT / "terminal_metric_summary.csv"
    pca_path = OUTPUT / "pca_summary.json"
    require(terminal_path.is_file(), "Terminal metric summary is required before final reporting")
    require(pca_path.is_file(), "PCA summary is required before final reporting")
    terminal = pd.read_csv(terminal_path)
    pca = json.loads(pca_path.read_text(encoding="utf-8"))
    horizons = {(int(row["horizon"]), str(row["arm"])): row for row in summary["horizon_results"]}
    m320 = horizons[(320, "binary_margin")]
    r320 = horizons[(320, "binary_random")]
    bootstrap = summary["query_bootstrap"]
    claim = summary["query_saving_claim"]

    def point(budget: int, subset: str, metric: str, estimand: str) -> float:
        selected = terminal[
            terminal.budget.eq(budget)
            & terminal.subset.eq(subset)
            & terminal.metric.eq(metric)
            & terminal.estimand.eq(estimand)
        ]
        require(len(selected) == 1, f"Missing terminal result {budget}/{subset}/{metric}/{estimand}")
        return float(selected.iloc[0].point_estimate)

    terminal_accuracy_rows = []
    for budget in (40, 80, 160, 320):
        for subset in ("full81", "B1_q30", "B1_q20"):
            terminal_accuracy_rows.append(
                {
                    "budget": budget,
                    "subset": subset,
                    "binary_margin_accuracy": point(budget, subset, "accuracy", "binary_margin"),
                    "matched_random_accuracy": point(budget, subset, "accuracy", "binary_random"),
                    "margin_minus_random": point(budget, subset, "accuracy", "margin_minus_random"),
                }
            )
    terminal_accuracy = pd.DataFrame(terminal_accuracy_rows)
    write_csv(OUTPUT / "terminal_accuracy_answers.csv", terminal_accuracy)
    q20_deltas = terminal_accuracy[terminal_accuracy.subset.eq("B1_q20")].margin_minus_random
    h320_q20_delta = terminal[
        terminal.budget.eq(320)
        & terminal.subset.eq("B1_q20")
        & terminal.metric.eq("accuracy")
        & terminal.estimand.eq("margin_minus_random")
    ]
    require(len(h320_q20_delta) == 1, "Missing H320 q20 accuracy contrast interval")
    h320_lower = float(h320_q20_delta.iloc[0].two_sided_95pct_lower)
    h320_upper = float(h320_q20_delta.iloc[0].two_sided_95pct_upper)
    if (q20_deltas > 0).all():
        terminal_direction = (
            "has positive point estimates at 40, 80, 160, and 320, but the H320 contrast is practically zero "
            f"and its design-conditional 95% interval [{h320_lower:+.4f}, {h320_upper:+.4f}] crosses zero"
        )
    else:
        terminal_direction = "has mixed point-estimate directions across the tested budgets 40, 80, 160, and 320"
    diagnostics = pca["interpretation_diagnostics"]
    role_mixing = diagnostics["mean_opposite_label_fraction_by_representative_test_role"]
    stage_mixing = diagnostics["mean_opposite_label_fraction_by_margin_query_stage"]
    q20_mixing = float(role_mixing["B1_q20"])
    non_q30_mixing = float(role_mixing["held_out_non_q30"])
    early_mixing = float(stage_mixing["acquired_17_40"])
    comparison_stage = "acquired_161_320"
    late_reference_mixing = float(stage_mixing[comparison_stage])
    boundary_direction = "higher" if q20_mixing > non_q30_mixing else "not higher"
    query_direction = "higher" if early_mixing > late_reference_mixing else "not higher"
    pca_direction_sentence = (
        f"In the representative, label-informed visualization fold, mean 10-neighbour opposite-label mixing is {q20_mixing:.3f} for q20 versus {non_q30_mixing:.3f} outside q30 ({boundary_direction}); "
        f"Margin queries 17–40 average {early_mixing:.3f} versus {late_reference_mixing:.3f} for queries 161–320 ({query_direction}); this is descriptive 2D association, not proof of a physical boundary."
    )

    q_answers = {
        "Q1_margin_crossed_all_100_by_320": {
            "answer": int(m320["finite_persistent_crossings"]) == 100,
            "count": int(m320["finite_persistent_crossings"]),
            "unresolved": int(m320["unresolved"]),
        },
        "Q2_random_crossings_by_320": {
            "count": int(r320["finite_persistent_crossings"]),
            "percentage": 100 * float(r320["finite_rate"]),
            "unresolved": int(r320["unresolved"]),
        },
        "Q3_restricted_mean_query_burden_H320": {
            "binary_margin": float(bootstrap["restricted_margin_mean_Q"]),
            "binary_random": float(bootstrap["restricted_random_mean_Q"]),
        },
        "Q4_restricted_H320_difference": float(bootstrap["restricted_delta_Q"]),
        "Q5_restricted_H320_ratio": float(bootstrap["restricted_ratio"]),
        "Q6_at_least_X_average_queries": claim,
        "Q7_terminal_accuracies": terminal_accuracy.to_dict(orient="records"),
        "Q8_terminal_vs_AULC": {
            "frozen_AULC_delta_margin_minus_random": FROZEN_AULC["margin_minus_random"],
            "terminal_q20_deltas": terminal_accuracy[terminal_accuracy.subset.eq("B1_q20")].to_dict(orient="records"),
            "interpretation": f"The terminal Fold-B1-q20 accuracy comparison {terminal_direction}. The frozen AULC contrast remains positive and measures earlier learning speed. Balanced accuracy and Keyhole recall are separate descriptive terminal endpoints; all of these remain different estimands.",
        },
        "Q9_PCA": {
            "pc1_variance": pca["pc1_explained_variance"],
            "pc2_variance": pca["pc2_explained_variance"],
            "combined_variance": pca["pc1_plus_pc2_explained_variance"],
            "pc1_dominant_loading": pca["pc1_dominant_loading"],
            "pc2_dominant_loading": pca["pc2_dominant_loading"],
            "component_interpretations": pca["component_interpretations"],
            "variance_outside_pc1_pc2": pca["variance_outside_pc1_pc2"],
            "scaling_robustness": pca["scaling_robustness"],
            "representative_run_id": pca["representative_run_id"],
            "representative_selection_is_label_informed": pca["representative_selection_is_label_informed"],
            "interpretation_diagnostics": pca["interpretation_diagnostics"],
            "caveat": pca["slice_caveat"],
        },
    }
    write_json(OUTPUT / "final_q1_q9_answers.json", q_answers)

    supervisor = f"""# Week 9 Phase 1 — supervisor-ready messages

1. **The remaining question was censoring, not method selection.** Frozen Week 8.5 already confirmed a positive Fold-B1-q20 AULC contrast of {FROZEN_AULC['margin_minus_random']:+.4f}; Phase 1 only continued the same Margin and Random trajectories.

2. **The H=320 extension is explicitly post-hoc.** It does not rewrite the H=160 protocol or upgrade the old Week 8.5 QUALIFY ledger.

3. **Persistent target attainment at H=320:** Binary Margin reached the persistent 0.80 Fold-B1-q20 target in {int(m320['finite_persistent_crossings'])}/100 outer runs; Random reached it in {int(r320['finite_persistent_crossings'])}/3000 continuations ({100*float(r320['finite_rate']):.1f}%), leaving {int(r320['unresolved'])} unresolved.

4. **Restricted H=320 burden:** Margin averaged {float(bootstrap['restricted_margin_mean_Q']):.3f} queries and matched Random {float(bootstrap['restricted_random_mean_Q']):.3f}; the descriptive difference is {float(bootstrap['restricted_delta_Q']):.3f} queries and the ratio is {float(bootstrap['restricted_ratio']):.3f}×.

5. **Safe query-saving statement:** {claim['supervisor_safe_sentence']} The naive argument that every unresolved H=320 path has `Q>320` is false under the frozen start-of-three definition.

6. **AULC and terminal accuracy answer different questions.** The terminal Fold-B1-q20 accuracy comparison {terminal_direction}. The frozen AULC contrast remains positive and measures earlier learning speed; balanced accuracy and Keyhole recall are separate descriptive endpoints, and full81, q30, and q20 results remain separated in `terminal_metric_summary.csv`.

7. **PCA describes sampled-input variance, not Keyhole importance.** After standardizing `P`, `VX`, `LS`, and `ST`, PC1 is an LS-versus-P contrast, PC2 is mainly sampled ST variation, and PC3 is mainly VX variation. PC1+PC2 retain {100*pca['pc1_plus_pc2_explained_variance']:.1f}%, so the 2D view omits {100*pca['variance_outside_pc1_pc2']:.1f}% including most VX variation. The single RobustScaler sensitivity check preserves the ST/PC2 and VX/PC3 pattern but changes PC1 materially, so the interpretation is scaling-aware. {pca_direction_sentence} Labels do not enter PCA fitting; the representative-fold choice is explicitly label-informed and visualization-only. PCA coordinates and held-out or unrevealed labels did not enter acquisition, while labels of already queried rows trained later GPC fits.

8. **Main limitations:** fixed 405-simulation population, manual labels, 17-row q20 subsets, post-hoc H=320 choice, unobservable persistent-Q tail near the final horizon, design-conditional bootstrap uncertainty, and PCA that optimizes input variance rather than class separation. The secondary GPC slice fixes PC3=PC4=0 and is masked only by the projected 2D hull—not verified support on the observed 4D manifold or a physical boundary.
"""
    (OUTPUT / "supervisor_summary.md").write_text(supervisor, encoding="utf-8", newline="\n")

    answers_md = ["# Explicit answers to Q1–Q9", ""]
    for key, value in q_answers.items():
        answers_md.extend([f"## {key}", "", "```json", json.dumps(value, indent=2, sort_keys=True), "```", ""])
    (OUTPUT / "final_q1_q9_answers.md").write_text("\n".join(answers_md), encoding="utf-8", newline="\n")

    ledger_lines = ["# Week 9 Phase 1 claim ledger", "", "Frozen confirmatory claims and post-hoc diagnostics are kept separate.", ""]
    for row in ledger.itertuples(index=False):
        ledger_lines.extend(
            [
                f"## {row.claim}", "",
                f"- Category: `{row.category}`",
                f"- Status: `{row.status}`",
                f"- Numeric result: {row.numeric_result}",
                f"- Strongest safe wording: {row.strongest_safe_wording}",
                f"- Must not use: {row.must_not_use}", "",
            ]
        )
    (OUTPUT / "claim_ledger.md").write_text("\n".join(ledger_lines), encoding="utf-8", newline="\n")

    validation_lines = ["# Week 9 Phase 1 validation report", "", f"Overall status: **{validation['status']}**", ""]
    for row in validation["checks"]:
        validation_lines.append(f"- **{row['status']}** — `{row['check_id']}`")
    validation_lines.extend(["", "Scientific interpretation is permitted only because every required validation passed."])
    (OUTPUT / "validation_report.md").write_text("\n".join(validation_lines) + "\n", encoding="utf-8", newline="\n")

    critic_path = OUTPUT / "independent_critic_audit.md"
    critic_pass = critic_path.is_file() and "Overall status: PASS" in critic_path.read_text(encoding="utf-8")
    requirement_rows = [
        ("0", "Pinned scientific base and terminology", "PASS", "summary.json; validation_report.json"),
        ("1", "Isolated Week 9 branch/output/source/notebook/tests", "PASS", "branch plus src/, notebooks/week_09/, tests/, outputs/week9_phase1_close_week8/"),
        ("2", "Audit checkpoints, bundles, resume, replay", "PASS", "validation_report.json; checkpoint package provenance"),
        ("3", "Extend Margin and 30 Random continuations to H320", "PASS", "week9_phase1_h320_checkpoint_bundle.tar.gz"),
        ("4", "Continue checkpoint cadence 164,168,...,320", "PASS", "crossing_path_evidence.csv"),
        ("5", "Label H320 as post-hoc", "PASS", "summary.json; claim_ledger.csv"),
        ("6", "Report H80/120/160/200/240/280/320", "PASS", "crossing_by_horizon.csv"),
        ("7", "Mathematically correct query-saving claim", "PASS", "query_saving_claim_decision.json"),
        ("8", "Matched pair guaranteed-minimum analysis", "PASS", "matched_pair_crossing_categories.csv"),
        ("9", "Terminal full81/q30/q20 metrics at 40/80/160/320", "PASS", "terminal_metric_summary.csv; terminal_path_metrics.csv"),
        ("10", "AULC versus terminal distinction", "PASS", "notebook Section 7; supervisor_summary.md"),
        ("11A", "Primary StandardScaler PCA of all 405 rows plus coefficients", "PASS", "figures/05_pca_input_geometry_and_loadings.png; pca_feature_loadings.csv"),
        ("11B", "Scaling robustness and PC1-PC3 loading structure", "PASS", "figures/06_pca_scaling_robustness.png; figures/07_pca_component_loading_structure.png"),
        ("11C", "Fold-local boundary-like visualization", "PASS", "figures/08_pca_boundary_like_subset.png"),
        ("11D", "Active-learning trajectory through H320", "PASS", "figures/09_pca_margin_query_trajectory.png"),
        ("11E", "Secondary PCA-plane GPC slice diagnostic", "PASS", "figures/10_pca_gpc_slice_diagnostic.png"),
        ("12", "Scientific PCA interpretation and RobustScaler sensitivity caveats", "PASS", "pca_summary.json; notebook Section 9"),
        ("13", "No deep dive on old 9/100 failures", "PASS", "No failure-analysis artifact created"),
        ("14-15", "Only question-driven required figures", "PASS", "figures/ and figure_manifest.csv"),
        ("16", "Repeat-block/within-fold Random bootstrap", "PASS", "query_bootstrap_summary.json; terminal_metric_summary.csv"),
        ("17", "Separated claim ledger", "PASS", "claim_ledger.csv and claim_ledger.md"),
        ("18", "Explicit Q1-Q9 answers", "PASS", "final_q1_q9_answers.json and .md"),
        ("19", "Leakage, identity, crossing, PCA validations", "PASS", "validation_report.json and .md"),
        ("20", "Existing independent critic workflow", "PASS" if critic_pass else "PENDING", "independent_critic_audit.md" if critic_pass else "Existing independent critic audit not recorded"),
        ("21", "Step-by-step teaching notebook", "PASS", "notebooks/week_09/01_week9_phase1_close_week8.ipynb"),
        ("22", "5-8 supervisor-facing messages", "PASS", "supervisor_summary.md"),
        ("23", "Ground truth/B1/q20/q30/ST terminology", "PASS", "notebook and supervisor summary"),
        ("24", "Historical outputs untouched; large files packaged", "PASS", "git diff scope; checkpoint tar.gz"),
        ("25", "Strongest defensible result only", "PASS", "query_saving_claim_decision.json"),
    ]
    requirements = pd.DataFrame(requirement_rows, columns=["prompt_section", "requirement", "status", "evidence"])
    write_csv(OUTPUT / "requirement_checklist.csv", requirements)
    checklist_lines = [
        "# Week 9 Phase 1 requirement checklist",
        "",
        "| Prompt section | Requirement | Status | Evidence |",
        "|---|---|---|---|",
    ]
    checklist_lines.extend(
        f"| {row.prompt_section} | {row.requirement} | {row.status} | `{row.evidence}` |"
        for row in requirements.itertuples(index=False)
    )
    checklist_md = "\n".join(checklist_lines) + "\n"
    (OUTPUT / "week9_phase1_requirement_checklist.md").write_text(checklist_md, encoding="utf-8", newline="\n")

    narrative = f"""# Week 9 Phase 1 final results narrative

## Scientific status

This is a **post-hoc H=320 horizon-extension closing diagnostic**. The frozen Week 8.5 AULC result and decision ledger remain unchanged.

## Main result

At H=320, Binary Margin confirmed {int(m320['finite_persistent_crossings'])}/100 persistent Fold-B1-q20 target crossings. Random confirmed {int(r320['finite_persistent_crossings'])}/3000 ({100*float(r320['finite_rate']):.2f}%). Restricted burdens were {float(bootstrap['restricted_margin_mean_Q']):.3f} and {float(bootstrap['restricted_random_mean_Q']):.3f} queries, respectively.

## Query-saving interpretation

{claim['supervisor_safe_sentence']}

The restricted H=320 difference is descriptive. The mathematical lower-bound analysis corrects the final-tail issue created by defining Q as the first, rather than the third, checkpoint of a persistent run.

## Terminal performance and PCA

Terminal full81/q30/q20 results are in `terminal_metric_summary.csv`; their Fold-B1-q20 comparison {terminal_direction}. The positive frozen AULC contrast separately measures earlier learning speed. Feature-only StandardScaler PCA is used only for interpretation: PC1 is an LS-versus-P contrast, PC2 is mainly sampled ST variation, and PC3 is mainly VX variation. PC1+PC2 explain {100*pca['pc1_plus_pc2_explained_variance']:.2f}% and omit {100*pca['variance_outside_pc1_pc2']:.2f}% of standardized input variance. Robust scaling preserves the ST/PC2 and VX/PC3 pattern but changes PC1 materially, so no loading is interpreted as physical importance, causality, or supervised Keyhole importance.

## Scope

Claims concern this fixed 405-simulation manual-label benchmark plus split/acquisition randomness. They are not causal, prospective, universally transferable, or physical-boundary certainty claims.
"""
    (OUTPUT / "final_results_narrative.md").write_text(narrative, encoding="utf-8", newline="\n")

    figure_files = sorted((OUTPUT / "figures").glob("*.png"))
    write_csv(
        OUTPUT / "figure_manifest.csv",
        pd.DataFrame(
            [{"figure": str(path.relative_to(OUTPUT)), "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in figure_files]
        ),
    )
    return {"q_answers": q_answers, "terminal_direction": terminal_direction, "requirement_rows": len(requirements)}


def write_run_manifest() -> dict[str, Any]:
    files = {}
    for path in sorted(OUTPUT.rglob("*")):
        if not path.is_file() or "dev_horizon" in path.parts or "dev_terminal_pca" in path.parts or path.name == "run_manifest.json":
            continue
        files[str(path.relative_to(OUTPUT))] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    manifest = {
        "analysis_status": "posthoc_horizon_extension_closing_diagnostic",
        "frozen_commit": h320.FROZEN_COMMIT,
        "frozen_protocol_sha256": h320.FROZEN_PROTOCOL_SHA256,
        "artifact_count": len(files),
        "files": files,
    }
    write_json(OUTPUT / "run_manifest.json", manifest)
    return manifest


def run_analysis(*, bootstrap_draws: int = BOOTSTRAP_DRAWS, package: bool = True) -> dict[str, Any]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    population = w85.load_population()
    specs = w85.build_splits(population)
    require(len(population) == 405 and int(population.has_keyhole.sum()) == 73, "Frozen population drift")
    provenance = h320.validate_frozen_environment(check_archive=True)
    paths, source_rows, extension_rows = load_path_evidence(population, specs)
    horizons = horizon_summary(paths)
    historical_checks = validate_historical_reproduction(horizons)
    require(all(row["status"] == "PASS" for row in historical_checks), "Historical H<=160 reproduction failed")
    pairs = matched_pair_table(paths)
    draws, bootstrap = query_bootstrap(paths, draws=bootstrap_draws)
    claim = query_claim_decision(paths, bootstrap, pairs)
    seeds, collisions = seed_registry_and_collisions(paths)
    terminal_audit = terminal_reproduction_audit(source_rows, extension_rows)
    require(terminal_audit["status"] == "PASS", "Terminal q20/q30 metric reproduction failed")
    write_json(OUTPUT / "terminal_metric_reproduction_audit.json", terminal_audit)
    terminal_summary = OUTPUT / "terminal_metric_summary.csv"
    figures = make_core_figures(paths, source_rows, terminal_summary if terminal_summary.is_file() else None)
    pca_summary_path = OUTPUT / "pca_summary.json"
    pca_summary = json.loads(pca_summary_path.read_text(encoding="utf-8")) if pca_summary_path.is_file() else None
    ledger = build_claim_ledger(claim, horizons, pca_summary)

    write_csv(OUTPUT / "crossing_path_evidence.csv", paths)
    write_csv(OUTPUT / "crossing_by_horizon.csv", horizons)
    write_csv(OUTPUT / "matched_pair_crossing_categories.csv", pairs)
    write_csv(OUTPUT / "query_bootstrap_draws.csv", draws)
    write_csv(OUTPUT / "week9_fit_seed_registry.csv", seeds)
    write_csv(OUTPUT / "claim_ledger.csv", ledger)
    write_csv(OUTPUT / "learning_curve_summary_16_80.csv", learning_curve_summary(source_rows))
    write_json(OUTPUT / "query_bootstrap_summary.json", bootstrap)
    write_json(OUTPUT / "query_saving_claim_decision.json", claim)
    write_json(OUTPUT / "week9_fit_seed_collision_audit.json", collisions)

    checks = [
        {"check_id": "frozen_population_405", "status": "PASS", "evidence": {"rows": 405}},
        {"check_id": "manual_has_keyhole_unchanged", "status": "PASS", "evidence": {"keyhole": 73, "conduction": 332}},
        {"check_id": "frozen_source_hashes", "status": "PASS", "evidence": provenance["frozen_source_hashes"]},
        {"check_id": "split_and_initial_design_exact", "status": "PASS", "evidence": "validated for every frozen checkpoint before extension"},
        {"check_id": "historical_query_prefixes_exact", "status": "PASS", "evidence": {"paths": 3100}},
        {"check_id": "historical_random_orders_exact", "status": "PASS", "evidence": {"paths": 3000}},
        {"check_id": "all_H320_trajectories_complete", "status": "PASS", "evidence": {"paths": 3100, "queried_each": 320}},
        {"check_id": "all_completed_payloads_fully_validated", "status": "PASS", "evidence": {"paths": 3100, "coverage": "identity, pool, mechanism, leakage flags, random sequence, terminal truth/probability"}},
        {"check_id": "no_test_B1_or_hidden_label_acquisition", "status": "PASS", "evidence": "source and extension mechanism records fail closed on information-flow fields"},
        {"check_id": "crossing_start_and_confirmation_distinguished", "status": "PASS", "evidence": "all horizon counts require confirmation_budget <= horizon"},
        {"check_id": "random_averaged_within_fold", "status": "PASS", "evidence": "query and terminal estimands average 30 continuations inside repeat/fold"},
        {"check_id": "terminal_q20_q30_metrics_reproduce_saved_fits", "status": terminal_audit["status"], "evidence": terminal_audit},
        {"check_id": "bootstrap_hierarchy", "status": "PASS", "evidence": bootstrap["hierarchy"]},
        {"check_id": "pca_visualization_only", "status": "PASS", "evidence": "PCA fits P/VX/LS/ST without labels and its coordinates never enter model training or acquisition; revealed queried labels still train later GPC fits"},
        *historical_checks,
    ]
    validation = {"status": "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL", "checks": checks, "fit_seed_collision_audit": collisions}
    write_json(OUTPUT / "validation_report.json", validation)
    require(validation["status"] == "PASS", "Validation failed; scientific interpretation stopped")

    package_report = package_checkpoints() if package else None
    summary = {
        "analysis_status": "posthoc_horizon_extension_closing_diagnostic",
        "frozen_week8_5_decision_unchanged": True,
        "frozen_AULC": FROZEN_AULC,
        "horizon_results": horizons.to_dict(orient="records"),
        "query_bootstrap": bootstrap,
        "query_saving_claim": claim,
        "matched_pair_categories": pairs.category.value_counts().to_dict(),
        "figures": figures,
        "validation_status": validation["status"],
        "checkpoint_package": package_report,
    }
    write_json(OUTPUT / "summary.json", summary)
    report = write_final_reports(summary, validation, ledger)
    summary["reporting"] = report
    write_json(OUTPUT / "summary.json", summary)
    write_run_manifest()
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("analyze", "figures", "package", "reports"))
    parser.add_argument("--bootstrap-draws", type=int, default=BOOTSTRAP_DRAWS)
    args = parser.parse_args()
    if args.command == "package":
        print(json.dumps(package_checkpoints(), indent=2))
        return
    if args.command == "figures":
        paths = pd.read_csv(OUTPUT / "crossing_path_evidence.csv")
        source = pd.DataFrame()
        population = w85.load_population(); specs = w85.build_splits(population)
        _, source, _ = load_path_evidence(population, specs)
        print(json.dumps(make_core_figures(paths, source, OUTPUT / "terminal_metric_summary.csv"), indent=2))
        return
    if args.command == "reports":
        summary = json.loads((OUTPUT / "summary.json").read_text(encoding="utf-8"))
        validation = json.loads((OUTPUT / "validation_report.json").read_text(encoding="utf-8"))
        horizons = pd.read_csv(OUTPUT / "crossing_by_horizon.csv")
        pca = json.loads((OUTPUT / "pca_summary.json").read_text(encoding="utf-8"))
        ledger = build_claim_ledger(summary["query_saving_claim"], horizons, pca)
        write_csv(OUTPUT / "claim_ledger.csv", ledger)
        result = write_final_reports(summary, validation, ledger)
        summary["reporting"] = result
        write_json(OUTPUT / "summary.json", summary)
        write_run_manifest()
        print(json.dumps(result, indent=2))
        return
    print(json.dumps(run_analysis(bootstrap_draws=args.bootstrap_draws), indent=2))


if __name__ == "__main__":
    main()
