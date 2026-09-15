"""Week 8 offline sample-efficiency analysis and thesis consolidation.

This module performs no new simulator run, model fit, acquisition search, data
split, or label construction.  It derives thesis-facing summaries from the
published Week 7 Phase 6/7 row-level artifacts at commit
``167aad945b20822de712e891e901bd3ec6d5ffc6``.

The scientific distinction enforced throughout is:

* B1/B2/B3 q20/q30 accuracy is empirical held-out classification accuracy on
  declared boundary-like subsets;
* GPC confidence is the saved model probability diagnostic and is not the
  probability that a continuous physical boundary is in a particular place.

All unsuccessful target crossings remain explicitly censored at budget 80.
Random-equivalent budgets use only piecewise-linear interpolation between the
observed matched-run mean Random curve and never extrapolate.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import t as student_t


ROOT = Path(__file__).resolve().parents[1]
PHASE7 = ROOT / "outputs" / "week7_07_final_boundary_hybrid_benchmark"
PHASE6 = ROOT / "outputs" / "week7_06_real_data_boundary_active_level_set"
PHASE55 = ROOT / "outputs" / "week7_05_5_g3_robustness_transfer_analysis"
PHASE5 = ROOT / "outputs" / "week7_05_keyhole_physical_proxy_analysis"
SYNTHETIC = ROOT / "outputs" / "week4_09_gpc_bernoulli_sur_validation"

OUT1 = ROOT / "outputs" / "week8_01_final_sample_efficiency"
OUT2 = ROOT / "outputs" / "week8_02_thesis_consolidation"
FIG1 = OUT1 / "figures"
FIG2 = OUT2 / "final_thesis_figures"
TABLE2 = OUT2 / "final_thesis_tables"

EXPECTED_PARENT = "167aad945b20822de712e891e901bd3ec6d5ffc6"
EXPECTED_PHASE6 = "5734de6f533e1de1e15a07de24e7d4e6e53bb6fa"
EXPECTED_BRANCH = "codex/week8-final-sample-efficiency-thesis-consolidation"
PHASE7_BRANCH = "codex/week7-phase7-final-boundary-hybrid-benchmark"

M_BINARY = "binary_uncertainty_repulsion"
M_RANDOM = "shared_random_binary_head"
M_DEPTH = "max_depth_straddle"
METHODS = (M_BINARY, M_RANDOM, M_DEPTH)
METHOD_LABELS = {
    M_BINARY: "Binary",
    M_RANDOM: "Random",
    M_DEPTH: "Max-Depth",
}
COLORS = {
    M_BINARY: "#0072B2",
    M_RANDOM: "#7A7A7A",
    M_DEPTH: "#D55E00",
}

BOUNDARIES = ("B1", "B2", "B3")
QUANTILES = (20, 30)
COMMON_START = 16
FINAL_BUDGET = 80
SNAPSHOT_BUDGETS = (16, 20, 30, 40, 50, 60, 70, 80)
HEADLINE_BUDGETS = (20, 30, 40, 50, 60, 70, 80)
TARGETS = (0.70, 0.75, 0.80, 0.85, 0.90)
EQUIVALENT_BINARY_BUDGETS = (20, 30, 40, 50, 60)
CONFIDENCE_BUDGETS = (20, 30, 40, 60, 80)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=cwd, text=True, stderr=subprocess.STDOUT
    ).strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n", float_format="%.12g")


def strict_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    values = series.astype(str).str.strip().str.lower()
    require(values.isin(["true", "false", "1", "0"]).all(), f"Invalid booleans in {series.name}")
    return values.isin(["true", "1"])


def read_csv(path: Path) -> pd.DataFrame:
    require(path.is_file(), f"Missing authoritative artifact: {path}")
    return pd.read_csv(path, low_memory=False)


def safe_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def describe(values: Iterable[float]) -> dict[str, float | int | None]:
    series = pd.Series(list(values), dtype=float).dropna()
    n = int(len(series))
    if n == 0:
        return {
            "n": 0,
            "mean": None,
            "median": None,
            "sd": None,
            "q25": None,
            "q75": None,
            "iqr": None,
            "ci95_lower": None,
            "ci95_upper": None,
        }
    mean = float(series.mean())
    sd = float(series.std(ddof=1)) if n > 1 else 0.0
    critical = float(student_t.ppf(0.975, n - 1)) if n > 1 else 0.0
    half = critical * sd / math.sqrt(n) if n > 1 else 0.0
    q25 = float(series.quantile(0.25))
    q75 = float(series.quantile(0.75))
    return {
        "n": n,
        "mean": mean,
        "median": float(series.median()),
        "sd": sd,
        "q25": q25,
        "q75": q75,
        "iqr": q75 - q25,
        "ci95_lower": mean - half,
        "ci95_upper": mean + half,
    }


def df_to_markdown(frame: pd.DataFrame, digits: int = 3) -> str:
    """Small dependency-free Markdown table formatter."""

    def format_value(value: Any) -> str:
        if pd.isna(value):
            return "—"
        if isinstance(value, (float, np.floating)):
            return f"{float(value):.{digits}f}"
        return str(value).replace("|", "\\|").replace("\n", " ")

    columns = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in frame.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(format_value(value) for value in row) + " |")
    return "\n".join(lines)


def save_markdown_table(path: Path, title: str, frame: pd.DataFrame, note: str = "") -> None:
    text = f"# {title}\n\n"
    if note:
        text += note.strip() + "\n\n"
    text += df_to_markdown(frame) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def source_audit() -> tuple[dict[str, Any], dict[str, pd.DataFrame]]:
    source_paths = {
        "learning_curves": PHASE7 / "phase7_learning_curve_summary.csv",
        "boundary_curves": PHASE7 / "phase7_boundary_metric_learning_curves.csv",
        "predictions": PHASE7 / "phase7_all_method_prediction_checkpoints.csv",
        "queries": PHASE7 / "phase7_all_method_query_history.csv",
        "discoveries": PHASE7 / "phase7_keyhole_discovery_summary.csv",
        "aulc": PHASE7 / "phase7_aulc_summary.csv",
        "runtime": PHASE7 / "phase7_runtime_comparison.csv",
        "phase7_decision": PHASE7 / "phase7_final_decision.csv",
        "phase7_validation": PHASE7 / "validation_results.csv",
        "phase7_requirements": PHASE7 / "requirement_checklist.csv",
        "phase7_reuse": PHASE7 / "phase6_run_reuse_audit.csv",
        "population": PHASE6 / "primary_common_population.csv",
        "splits": PHASE6 / "outer_split_manifest.csv",
        "phase6_scorecard": PHASE6 / "phase6_formulation_scorecard.csv",
        "phase6_decision": PHASE6 / "phase6_final_decision.csv",
        "phase55_summary": PHASE55 / "summary.json",
        "phase5_summary": PHASE5 / "summary.json",
        "synthetic_summary": SYNTHETIC / "combined" / "gpc_bernoulli_sur_validation_summary.csv",
    }
    for path in source_paths.values():
        require(path.is_file(), f"Missing source artifact: {path}")

    phase7_validation = read_csv(source_paths["phase7_validation"])
    phase7_requirements = read_csv(source_paths["phase7_requirements"])
    require(len(phase7_validation) == 34 and phase7_validation["status"].eq("PASS").all(), "Phase 7 validation is not 34/34 PASS")
    require(len(phase7_requirements) == 18 and phase7_requirements["status"].eq("PASS").all(), "Phase 7 requirements are not 18/18 PASS")

    inventory = []
    for role, path in source_paths.items():
        inventory.append(
            {
                "role": role,
                "relative_path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    remote_line = git("ls-remote", "--heads", "origin", f"refs/heads/{PHASE7_BRANCH}")
    remote_head = remote_line.split()[0] if remote_line else ""
    current_head = git("rev-parse", "HEAD")
    current_branch = git("branch", "--show-current")
    require(current_head == EXPECTED_PARENT, f"Week 8 HEAD drift: {current_head}")
    require(current_branch == EXPECTED_BRANCH, f"Week 8 branch drift: {current_branch}")
    require(remote_head == EXPECTED_PARENT, f"Remote Phase 7 head drift: {remote_head}")

    original = Path(r"C:\Users\ozgur\Documents\thesis")
    original_status = git("status", "--porcelain=v1", "--branch", cwd=original).splitlines()
    original_baseline = {
        "path": str(original),
        "head": git("rev-parse", "HEAD", cwd=original),
        "branch": git("branch", "--show-current", cwd=original),
        "status_lines": original_status,
        "dirty_entries": max(0, len(original_status) - 1),
        "preservation_policy": "Read-only; all Week 8 writes occur in the isolated Week 8 worktree.",
    }
    write_json(OUT1 / "original_worktree_baseline.json", original_baseline)

    audit = {
        "phase": "Week 8 Phase 1 source audit",
        "timestamp_utc": utc_now(),
        "week8_branch": current_branch,
        "week8_head_before_commit": current_head,
        "exact_phase7_parent": EXPECTED_PARENT,
        "phase7_remote_branch": PHASE7_BRANCH,
        "phase7_remote_head": remote_head,
        "remote_parent_verified": True,
        "phase7_validation_pass": 34,
        "phase7_validation_total": 34,
        "phase7_requirement_pass": 18,
        "phase7_requirement_total": 18,
        "new_simulator_runs": False,
        "expensive_benchmark_rerun": False,
        "new_splits": False,
        "new_acquisition": False,
        "new_model": False,
        "manual_labels_modified": False,
        "source_inventory": inventory,
    }
    write_json(OUT1 / "phase7_source_audit.json", audit)

    tables = {
        "learning": read_csv(source_paths["learning_curves"]),
        "predictions": read_csv(source_paths["predictions"]),
        "queries": read_csv(source_paths["queries"]),
        "discoveries": read_csv(source_paths["discoveries"]),
        "aulc": read_csv(source_paths["aulc"]),
        "runtime": read_csv(source_paths["runtime"]),
        "reuse": read_csv(source_paths["phase7_reuse"]),
        "population": read_csv(source_paths["population"]),
        "splits": read_csv(source_paths["splits"]),
        "synthetic": read_csv(source_paths["synthetic_summary"]),
    }
    return audit, tables


def validate_and_prepare_sources(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    population = tables["population"].copy()
    population["has_keyhole"] = strict_bool(population["has_keyhole"])
    require(len(population) == 405, f"Population drift: {len(population)}")
    require(int(population["has_keyhole"].sum()) == 73, "Keyhole count drift")
    require(int((~population["has_keyhole"]).sum()) == 332, "non-Keyhole count drift")

    learning = tables["learning"].copy()
    learning = learning[learning["method"].isin(METHODS)].copy()
    require(learning["run_id"].nunique() == 20, "Expected exactly 20 matched runs")
    for method in METHODS:
        method_frame = learning[learning["method"].eq(method)]
        for budget in range(COMMON_START, FINAL_BUDGET + 1):
            count = method_frame.loc[method_frame["budget"].eq(budget), "run_id"].nunique()
            require(count == 20, f"{method} budget {budget} has {count}/20 runs")
    for boundary in BOUNDARIES:
        for quantile in QUANTILES:
            error = f"{boundary}_q{quantile}_error"
            require(error in learning.columns, f"Missing {error}")
            learning[f"{boundary}_q{quantile}_accuracy"] = 1.0 - pd.to_numeric(learning[error], errors="raise")

    reuse = tables["reuse"].copy()
    require(len(reuse) == 20 and reuse["status"].eq("PASS").all(), "Phase 6 run reuse audit drift")
    require(strict_bool(reuse["warm_hash_matches"]).all(), "Warm-start hash mismatch")
    require(strict_bool(reuse["split_hash_matches"]).all(), "Split hash mismatch")

    predictions = tables["predictions"].copy()
    predictions = predictions[predictions["method"].eq(M_BINARY)].copy()
    predictions["has_keyhole"] = pd.to_numeric(predictions["has_keyhole"], errors="raise").astype(int)
    predictions["predicted_keyhole"] = pd.to_numeric(predictions["predicted_keyhole"], errors="raise").astype(int)
    predictions["keyhole_probability"] = pd.to_numeric(predictions["keyhole_probability"], errors="raise")
    require(predictions["keyhole_probability"].between(0, 1).all(), "Invalid saved probabilities")
    require(set(CONFIDENCE_BUDGETS).issubset(set(predictions["budget"].unique())), "Missing confidence checkpoints")

    queries = tables["queries"].copy()
    require(not strict_bool(queries["boundary_scores_consulted_before_selection"]).any(), "Boundary leakage recorded")
    require(not strict_bool(queries["hidden_label_consulted_before_selection"]).any(), "Hidden-label leakage recorded")
    require(not strict_bool(queries["hidden_max_depth_consulted_before_selection"]).any(), "Hidden-response leakage recorded")

    tables = dict(tables)
    tables.update(
        {
            "population": population,
            "learning": learning,
            "predictions": predictions,
            "queries": queries,
            "reuse": reuse,
        }
    )
    return tables


def write_preflight(audit: dict[str, Any], tables: dict[str, pd.DataFrame]) -> None:
    learning = tables["learning"]
    preflight = {
        "phase": "Week 8 Phase 1",
        "status": "PASS",
        "timestamp_utc": utc_now(),
        "week8_branch": EXPECTED_BRANCH,
        "exact_phase7_parent": EXPECTED_PARENT,
        "exact_phase6_commit": EXPECTED_PHASE6,
        "remote_phase7_verified": bool(audit["remote_parent_verified"]),
        "primary_population_count": len(tables["population"]),
        "keyhole_count": int(tables["population"]["has_keyhole"].sum()),
        "non_keyhole_count": int((~tables["population"]["has_keyhole"]).sum()),
        "outer_run_count": int(learning["run_id"].nunique()),
        "repeats": sorted(int(value) for value in learning["repeat"].unique()),
        "folds": sorted(int(value) for value in learning["fold"].unique()),
        "common_budget_start": COMMON_START,
        "final_budget": FINAL_BUDGET,
        "primary_method": M_BINARY,
        "random_baseline": M_RANDOM,
        "secondary_comparator": M_DEPTH,
        "manual_ground_truth": "has_keyhole",
        "inputs": ["P", "VX", "LS", "ST"],
        "ST_semantics": "substrate temperature",
        "boundary_metrics_evaluation_only": True,
        "offline_retrospective_benchmark": True,
        "prospective_new_simulator_validation": False,
        "expensive_experiment_rerun": False,
    }
    write_json(OUT1 / "phase8_01_preflight.json", preflight)

    reuse = tables["reuse"].copy()
    coverage = (
        tables["learning"]
        .groupby("run_id")
        .agg(
            week8_method_count=("method", "nunique"),
            week8_min_budget=("budget", "min"),
            week8_max_budget=("budget", "max"),
        )
        .reset_index()
    )
    prediction_coverage = (
        tables["predictions"]
        .groupby("run_id")
        .agg(
            saved_prediction_checkpoint_count=("budget", "nunique"),
            saved_prediction_rows=("experiment_name", "size"),
        )
        .reset_index()
    )
    reuse = reuse.merge(coverage, on="run_id", how="left").merge(prediction_coverage, on="run_id", how="left")
    reuse["expected_saved_prediction_checkpoint_count"] = np.where(
        reuse["effective_warm_start"].eq(16), 9, 10
    )
    reuse["week8_source_reuse_status"] = np.where(
        reuse["status"].eq("PASS")
        & reuse["week8_method_count"].eq(3)
        & reuse["week8_max_budget"].eq(80)
        & reuse["saved_prediction_checkpoint_count"].eq(
            reuse["expected_saved_prediction_checkpoint_count"]
        ),
        "PASS",
        "FAIL",
    )
    write_csv(OUT1 / "matched_run_reuse_audit.csv", reuse)


def compute_discovery(tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    discoveries = tables["discoveries"]
    discoveries = discoveries[
        discoveries["method"].isin(METHODS) & discoveries["budget"].isin(SNAPSHOT_BUDGETS)
    ].copy()
    splits = tables["splits"].copy()
    splits["has_keyhole"] = strict_bool(splits["has_keyhole"])
    prevalence = (
        splits[splits["role"].eq("training_pool")]
        .groupby("run_id")
        .agg(
            candidate_pool_count=("has_keyhole", "size"),
            candidate_keyhole_count=("has_keyhole", "sum"),
            candidate_keyhole_prevalence=("has_keyhole", "mean"),
        )
        .reset_index()
    )
    discoveries = discoveries.merge(prevalence, on="run_id", how="left", validate="many_to_one")
    discoveries["queried_keyhole_fraction"] = discoveries["keyhole_discovered"] / discoveries["budget"]
    discoveries["keyhole_enrichment"] = (
        discoveries["queried_keyhole_fraction"] / discoveries["candidate_keyhole_prevalence"]
    )
    run_level = discoveries.sort_values(["budget", "method", "run_id"]).reset_index(drop=True)
    write_csv(OUT1 / "keyhole_discovery_run_level.csv", run_level)

    rows: list[dict[str, Any]] = []
    for (budget, method), group in run_level.groupby(["budget", "method"], sort=True):
        discovered = describe(group["keyhole_discovered"])
        fraction = describe(group["queried_keyhole_fraction"])
        enrichment = describe(group["keyhole_enrichment"])
        rows.append(
            {
                "budget": int(budget),
                "method": method,
                "method_label": METHOD_LABELS[method],
                "run_count": discovered["n"],
                "mean_keyhole_discovered": discovered["mean"],
                "median_keyhole_discovered": discovered["median"],
                "sd_keyhole_discovered": discovered["sd"],
                "ci95_keyhole_discovered_lower": discovered["ci95_lower"],
                "ci95_keyhole_discovered_upper": discovered["ci95_upper"],
                "mean_queried_keyhole_fraction": fraction["mean"],
                "mean_candidate_keyhole_prevalence": float(group["candidate_keyhole_prevalence"].mean()),
                "mean_keyhole_enrichment": enrichment["mean"],
                "median_keyhole_enrichment": enrichment["median"],
                "sd_keyhole_enrichment": enrichment["sd"],
                "discovery_is_not_boundary_localization": True,
            }
        )
    summary = pd.DataFrame(rows).sort_values(["budget", "method"])
    write_csv(OUT1 / "keyhole_discovery_by_budget.csv", summary)
    return run_level, summary


def compute_learning_curves(learning: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    run_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    common = learning[learning["budget"].between(COMMON_START, FINAL_BUDGET)].copy()
    for boundary in BOUNDARIES:
        for quantile in QUANTILES:
            accuracy_col = f"{boundary}_q{quantile}_accuracy"
            error_col = f"{boundary}_q{quantile}_error"
            for row in common[
                ["run_id", "repeat", "fold", "method", "budget", accuracy_col, error_col]
            ].itertuples(index=False):
                run_rows.append(
                    {
                        "run_id": row.run_id,
                        "repeat": int(row.repeat),
                        "fold": int(row.fold),
                        "method": row.method,
                        "method_label": METHOD_LABELS[row.method],
                        "budget": int(row.budget),
                        "boundary_definition": boundary,
                        "quantile": quantile,
                        "boundary_accuracy": float(getattr(row, accuracy_col)),
                        "boundary_error": float(getattr(row, error_col)),
                    }
                )
            for (method, budget), group in common.groupby(["method", "budget"], sort=True):
                stats = describe(group[accuracy_col])
                error_stats = describe(group[error_col])
                summary_rows.append(
                    {
                        "boundary_definition": boundary,
                        "quantile": quantile,
                        "method": method,
                        "method_label": METHOD_LABELS[method],
                        "budget": int(budget),
                        "run_count": stats["n"],
                        "mean_accuracy": stats["mean"],
                        "median_accuracy": stats["median"],
                        "sd_accuracy": stats["sd"],
                        "q25_accuracy": stats["q25"],
                        "q75_accuracy": stats["q75"],
                        "iqr_accuracy": stats["iqr"],
                        "ci95_accuracy_lower": max(0.0, float(stats["ci95_lower"])),
                        "ci95_accuracy_upper": min(1.0, float(stats["ci95_upper"])),
                        "mean_error": error_stats["mean"],
                        "accuracy_identity_max_abs_error": float(
                            np.max(np.abs(group[accuracy_col] - (1.0 - group[error_col])))
                        ),
                        "interval_type": "two-sided descriptive t interval across 20 matched outer runs",
                    }
                )
    run_level = pd.DataFrame(run_rows).sort_values(
        ["boundary_definition", "quantile", "budget", "method", "run_id"]
    )
    summary = pd.DataFrame(summary_rows).sort_values(
        ["boundary_definition", "quantile", "budget", "method"]
    )
    write_csv(OUT1 / "boundary_accuracy_run_level.csv", run_level)
    write_csv(OUT1 / "boundary_accuracy_learning_curves.csv", summary)

    improvement_rows: list[dict[str, Any]] = []
    for (boundary, quantile, budget), group in run_level.groupby(
        ["boundary_definition", "quantile", "budget"], sort=True
    ):
        pivot = group.pivot(index="run_id", columns="method", values="boundary_accuracy")
        require({M_BINARY, M_RANDOM}.issubset(pivot.columns), "Missing paired Binary/Random rows")
        difference = pivot[M_BINARY] - pivot[M_RANDOM]
        stats = describe(difference)
        improvement_rows.append(
            {
                "boundary_definition": boundary,
                "quantile": int(quantile),
                "budget": int(budget),
                "matched_run_count": stats["n"],
                "mean_binary_minus_random_accuracy": stats["mean"],
                "median_binary_minus_random_accuracy": stats["median"],
                "sd_binary_minus_random_accuracy": stats["sd"],
                "ci95_lower": stats["ci95_lower"],
                "ci95_upper": stats["ci95_upper"],
            }
        )
    improvement = pd.DataFrame(improvement_rows)
    write_csv(OUT1 / "binary_minus_random_accuracy_improvement.csv", improvement)
    return summary, improvement


def compute_budget_snapshots(
    learning: pd.DataFrame,
    discovery_run_level: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    outputs: dict[str, pd.DataFrame] = {}
    discovery_small = discovery_run_level[
        ["run_id", "method", "budget", "keyhole_discovered", "keyhole_enrichment"]
    ]
    for boundary in BOUNDARIES:
        rows: list[dict[str, Any]] = []
        for budget in SNAPSHOT_BUDGETS:
            for method in METHODS:
                group = learning[
                    learning["method"].eq(method) & learning["budget"].eq(budget)
                ].copy()
                require(group["run_id"].nunique() == 20, f"Snapshot coverage failure {boundary}/{method}/{budget}")
                group = group.merge(
                    discovery_small[
                        discovery_small["method"].eq(method) & discovery_small["budget"].eq(budget)
                    ],
                    on=["run_id", "method", "budget"],
                    how="left",
                    validate="one_to_one",
                )
                row: dict[str, Any] = {
                    "boundary_definition": boundary,
                    "budget": int(budget),
                    "method": method,
                    "method_label": METHOD_LABELS[method],
                    "run_count": int(group["run_id"].nunique()),
                }
                for quantile in QUANTILES:
                    error_stats = describe(group[f"{boundary}_q{quantile}_error"])
                    accuracy_stats = describe(group[f"{boundary}_q{quantile}_accuracy"])
                    prefix = f"q{quantile}"
                    row.update(
                        {
                            f"mean_{prefix}_error": error_stats["mean"],
                            f"mean_{prefix}_accuracy": accuracy_stats["mean"],
                            f"median_{prefix}_accuracy": accuracy_stats["median"],
                            f"sd_{prefix}_accuracy": accuracy_stats["sd"],
                            f"q25_{prefix}_accuracy": accuracy_stats["q25"],
                            f"q75_{prefix}_accuracy": accuracy_stats["q75"],
                            f"ci95_{prefix}_accuracy_lower": max(0.0, float(accuracy_stats["ci95_lower"])),
                            f"ci95_{prefix}_accuracy_upper": min(1.0, float(accuracy_stats["ci95_upper"])),
                        }
                    )
                for metric in [
                    "balanced_accuracy",
                    "sensitivity",
                    "specificity",
                    "global_error",
                    "brier_score",
                ]:
                    stats = describe(group[metric])
                    row[f"mean_{metric}"] = stats["mean"]
                    row[f"median_{metric}"] = stats["median"]
                    row[f"sd_{metric}"] = stats["sd"]
                discovery_stats = describe(group["keyhole_discovered"])
                enrichment_stats = describe(group["keyhole_enrichment"])
                row.update(
                    {
                        "mean_keyhole_discovered": discovery_stats["mean"],
                        "sd_keyhole_discovered": discovery_stats["sd"],
                        "mean_keyhole_enrichment": enrichment_stats["mean"],
                        "accuracy_exactly_one_minus_error": True,
                    }
                )
                rows.append(row)
        frame = pd.DataFrame(rows).sort_values(["budget", "method"])
        write_csv(OUT1 / f"budget_snapshot_{boundary.lower()}.csv", frame)
        outputs[boundary] = frame
    return outputs


def first_crossing(group: pd.DataFrame, accuracy_col: str, target: float, persistent: bool) -> float | None:
    ordered = group.sort_values("budget")
    values = ordered[accuracy_col].to_numpy(float)
    budgets = ordered["budget"].to_numpy(int)
    if persistent:
        for index in range(max(0, len(values) - 2)):
            if bool(np.all(values[index : index + 3] >= target - 1e-12)):
                return float(budgets[index])
        return None
    reached = np.flatnonzero(values >= target - 1e-12)
    return float(budgets[reached[0]]) if len(reached) else None


def crossing_tables(
    learning: pd.DataFrame,
    persistent: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    run_rows: list[dict[str, Any]] = []
    for boundary in BOUNDARIES:
        for quantile in QUANTILES:
            accuracy_col = f"{boundary}_q{quantile}_accuracy"
            for target in TARGETS:
                for (method, run_id), group in learning.groupby(["method", "run_id"], sort=True):
                    crossing = first_crossing(group, accuracy_col, target, persistent)
                    run_rows.append(
                        {
                            "run_id": run_id,
                            "repeat": int(group["repeat"].iloc[0]),
                            "fold": int(group["fold"].iloc[0]),
                            "method": method,
                            "method_label": METHOD_LABELS[method],
                            "boundary_definition": boundary,
                            "quantile": quantile,
                            "target_accuracy": target,
                            "target_accuracy_percent": int(round(target * 100)),
                            "queries_required": crossing,
                            "status": "reached" if crossing is not None else "not_reached_by_80",
                            "available_start_budget": int(group["budget"].min()),
                            "final_budget": int(group["budget"].max()),
                            "crossing_definition": (
                                "target met at current and next two stored integer-budget checkpoints"
                                if persistent
                                else "first observed integer budget at which target is met"
                            ),
                            "no_extrapolation": True,
                        }
                    )
    run_level = pd.DataFrame(run_rows).sort_values(
        ["boundary_definition", "quantile", "target_accuracy", "method", "run_id"]
    )
    summary_rows: list[dict[str, Any]] = []
    keys = ["boundary_definition", "quantile", "target_accuracy", "target_accuracy_percent", "method", "method_label"]
    for key, group in run_level.groupby(keys, sort=True, dropna=False):
        reached = group[group["status"].eq("reached")]["queries_required"].dropna()
        stats = describe(reached)
        success = int(len(reached))
        summary_rows.append(
            {
                **dict(zip(keys, key)),
                "successful_runs": success,
                "total_runs": int(len(group)),
                "not_reached_by_80": int(len(group) - success),
                "success_fraction": success / len(group),
                "median_queries_successful_runs": stats["median"],
                "mean_queries_successful_runs": stats["mean"],
                "q25_queries_successful_runs": stats["q25"],
                "q75_queries_successful_runs": stats["q75"],
                "iqr_queries_successful_runs": stats["iqr"],
                "conditional_on_success": True,
                "unsuccessful_runs_dropped": False,
                "status_summary": f"{success}/20 reached; {20-success}/20 not reached by budget 80",
                "crossing_type": "persistent" if persistent else "first",
            }
        )
    summary = pd.DataFrame(summary_rows).sort_values(
        ["boundary_definition", "quantile", "target_accuracy", "method"]
    )
    return run_level, summary


def compute_crossings(learning: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    first_run, first_summary = crossing_tables(learning, persistent=False)
    persistent_run, persistent_summary = crossing_tables(learning, persistent=True)
    write_csv(OUT1 / "queries_to_accuracy_target_run_level.csv", first_run)
    write_csv(OUT1 / "queries_to_accuracy_target.csv", first_summary)
    write_csv(OUT1 / "persistent_queries_to_accuracy_target_run_level.csv", persistent_run)
    write_csv(OUT1 / "persistent_queries_to_accuracy_target.csv", persistent_summary)
    return first_run, first_summary, persistent_run, persistent_summary


def compute_matched_savings(first_run: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    source = first_run[
        first_run["boundary_definition"].eq("B1")
        & first_run["quantile"].isin([20, 30])
        & first_run["target_accuracy"].isin([0.75, 0.80, 0.85])
        & first_run["method"].isin([M_BINARY, M_RANDOM])
    ].copy()
    join_columns = [
        "run_id",
        "repeat",
        "fold",
        "quantile",
        "target_accuracy",
        "target_accuracy_percent",
    ]
    binary_rows = source[source["method"].eq(M_BINARY)][
        [*join_columns, "queries_required"]
    ].rename(columns={"queries_required": M_BINARY})
    random_rows = source[source["method"].eq(M_RANDOM)][
        [*join_columns, "queries_required"]
    ].rename(columns={"queries_required": M_RANDOM})
    require(len(binary_rows) == 120 and len(random_rows) == 120, "Matched-savings source coverage drift")
    pivot = binary_rows.merge(
        random_rows,
        on=join_columns,
        how="outer",
        validate="one_to_one",
    )
    require(len(pivot) == 120, "Matched-savings merge must contain 20 runs x 2 quantiles x 3 targets")
    run_rows: list[dict[str, Any]] = []
    for row in pivot.itertuples(index=False):
        binary = getattr(row, M_BINARY)
        random = getattr(row, M_RANDOM)
        binary_reached = not pd.isna(binary)
        random_reached = not pd.isna(random)
        if binary_reached and random_reached:
            if binary < random:
                outcome = "binary_earlier"
            elif binary > random:
                outcome = "random_earlier"
            else:
                outcome = "tie"
            difference = float(random - binary)
        elif binary_reached:
            outcome = "binary_reached_random_not_reached"
            difference = None
        elif random_reached:
            outcome = "random_reached_binary_not_reached"
            difference = None
        else:
            outcome = "neither_reached"
            difference = None
        run_rows.append(
            {
                "run_id": row.run_id,
                "repeat": int(row.repeat),
                "fold": int(row.fold),
                "boundary_definition": "B1",
                "quantile": int(row.quantile),
                "target_accuracy": float(row.target_accuracy),
                "target_accuracy_percent": int(row.target_accuracy_percent),
                "binary_first_budget": safe_float(binary),
                "random_first_budget": safe_float(random),
                "outcome": outcome,
                "random_minus_binary_queries_jointly_reached": difference,
                "censoring_preserved": True,
            }
        )
    run_level = pd.DataFrame(run_rows).sort_values(["quantile", "target_accuracy", "run_id"])
    summary_rows: list[dict[str, Any]] = []
    outcome_columns = [
        "binary_earlier",
        "tie",
        "random_earlier",
        "binary_reached_random_not_reached",
        "random_reached_binary_not_reached",
        "neither_reached",
    ]
    for (quantile, target), group in run_level.groupby(["quantile", "target_accuracy"], sort=True):
        counts = group["outcome"].value_counts().to_dict()
        joint = group["random_minus_binary_queries_jointly_reached"].dropna()
        stats = describe(joint)
        summary_rows.append(
            {
                "boundary_definition": "B1",
                "quantile": int(quantile),
                "target_accuracy": float(target),
                "target_accuracy_percent": int(round(target * 100)),
                "matched_run_count": int(len(group)),
                **{f"count_{name}": int(counts.get(name, 0)) for name in outcome_columns},
                "jointly_reached_count": int(len(joint)),
                "paired_median_random_minus_binary_queries": stats["median"],
                "paired_mean_random_minus_binary_queries": stats["mean"],
                "paired_q25_random_minus_binary_queries": stats["q25"],
                "paired_q75_random_minus_binary_queries": stats["q75"],
                "not_reached_not_imputed": True,
            }
        )
    summary = pd.DataFrame(summary_rows)
    write_csv(OUT1 / "matched_query_savings_run_level.csv", run_level)
    write_csv(OUT1 / "matched_query_savings.csv", summary)
    return run_level, summary


def mean_accuracy_curve(learning: pd.DataFrame, method: str, boundary: str, quantile: int) -> pd.DataFrame:
    column = f"{boundary}_q{quantile}_accuracy"
    frame = learning[
        learning["method"].eq(method) & learning["budget"].between(COMMON_START, FINAL_BUDGET)
    ]
    result = frame.groupby("budget", as_index=False)[column].mean().rename(columns={column: "mean_accuracy"})
    require(len(result) == FINAL_BUDGET - COMMON_START + 1, "Incomplete observed mean curve")
    return result.sort_values("budget")


def random_equivalent_for_target(random_curve: pd.DataFrame, target: float) -> float | None:
    x = random_curve["budget"].to_numpy(float)
    y = random_curve["mean_accuracy"].to_numpy(float)
    if y[0] >= target - 1e-12:
        return float(x[0])
    for index in range(1, len(x)):
        if y[index] >= target - 1e-12 and y[index - 1] < target - 1e-12:
            delta = y[index] - y[index - 1]
            if abs(delta) < 1e-15:
                return float(x[index])
            fraction = (target - y[index - 1]) / delta
            return float(x[index - 1] + fraction * (x[index] - x[index - 1]))
    return None


def compute_random_equivalent(learning: pd.DataFrame) -> pd.DataFrame:
    random_curve = mean_accuracy_curve(learning, M_RANDOM, "B1", 20)
    binary_curve = mean_accuracy_curve(learning, M_BINARY, "B1", 20)
    rows: list[dict[str, Any]] = []
    for budget in EQUIVALENT_BINARY_BUDGETS:
        target = float(binary_curve.loc[binary_curve["budget"].eq(budget), "mean_accuracy"].iloc[0])
        equivalent = random_equivalent_for_target(random_curve, target)
        if equivalent is None:
            status = "not_matched_by_80"
            equivalent_display = ">80"
            saving = None
            saving_lower = float(FINAL_BUDGET - budget)
            saving_display = f">{FINAL_BUDGET - budget:g}"
            multiplier = None
            multiplier_lower = float(FINAL_BUDGET / budget)
            multiplier_display = f">{FINAL_BUDGET / budget:.2f}x"
        else:
            status = "matched_within_observed_curve"
            equivalent_display = f"{equivalent:.2f}"
            saving = equivalent - budget
            saving_lower = None
            saving_display = f"{saving:.2f}"
            multiplier = equivalent / budget
            multiplier_lower = None
            multiplier_display = f"{multiplier:.2f}x"
        rows.append(
            {
                "boundary_definition": "B1",
                "quantile": 20,
                "binary_budget": budget,
                "binary_mean_accuracy": target,
                "random_equivalent_budget": equivalent,
                "random_equivalent_budget_display": equivalent_display,
                "status": status,
                "query_saving": saving,
                "query_saving_lower_bound": saving_lower,
                "query_saving_display": saving_display,
                "efficiency_multiplier": multiplier,
                "efficiency_multiplier_lower_bound": multiplier_lower,
                "efficiency_multiplier_display": multiplier_display,
                "interpolation": "piecewise linear between adjacent observed integer-budget Random means",
                "extrapolation": False,
                "random_curve_start_budget": COMMON_START,
                "random_curve_end_budget": FINAL_BUDGET,
            }
        )
    result = pd.DataFrame(rows)
    write_csv(OUT1 / "random_equivalent_budget.csv", result)
    write_csv(
        OUT1 / "query_savings_summary.csv",
        result[
            [
                "binary_budget",
                "binary_mean_accuracy",
                "random_equivalent_budget_display",
                "query_saving_display",
                "efficiency_multiplier_display",
                "status",
                "interpolation",
                "extrapolation",
            ]
        ],
    )
    return result


def calibration_bins(
    values: np.ndarray,
    outcomes: np.ndarray,
    edges: np.ndarray,
    calibration_type: str,
    metadata: dict[str, Any],
) -> tuple[list[dict[str, Any]], float]:
    rows: list[dict[str, Any]] = []
    total = len(values)
    ece = 0.0
    for index in range(len(edges) - 1):
        left = float(edges[index])
        right = float(edges[index + 1])
        if index == len(edges) - 2:
            mask = (values >= left) & (values <= right)
        else:
            mask = (values >= left) & (values < right)
        n = int(mask.sum())
        mean_value = float(values[mask].mean()) if n else None
        observed = float(outcomes[mask].mean()) if n else None
        gap = abs(mean_value - observed) if n else None
        if n:
            ece += n / total * float(gap)
        rows.append(
            {
                **metadata,
                "calibration_type": calibration_type,
                "bin_index": index + 1,
                "bin_left": left,
                "bin_right": right,
                "row_count": n,
                "mean_prediction_or_confidence": mean_value,
                "observed_positive_rate_or_accuracy": observed,
                "absolute_calibration_gap": gap,
            }
        )
    return rows, float(ece)


def compute_predictive_confidence(
    predictions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    predictions = predictions[predictions["budget"].isin(CONFIDENCE_BUDGETS)].copy()
    predictions["confidence"] = np.maximum(
        predictions["keyhole_probability"], 1.0 - predictions["keyhole_probability"]
    )
    predictions["correct"] = predictions["predicted_keyhole"].eq(predictions["has_keyhole"])
    subsets: list[tuple[str, str, str, pd.Series]] = [
        ("all_test", "all", "all", pd.Series(True, index=predictions.index))
    ]
    for boundary in BOUNDARIES:
        for quantile in QUANTILES:
            column = f"test_{boundary}_q{quantile}"
            mask = strict_bool(predictions[column])
            subsets.append((f"{boundary}_q{quantile}", boundary, str(quantile), mask))

    summary_rows: list[dict[str, Any]] = []
    run_rows: list[dict[str, Any]] = []
    calibration_rows: list[dict[str, Any]] = []
    for budget in CONFIDENCE_BUDGETS:
        budget_frame = predictions[predictions["budget"].eq(budget)]
        require(budget_frame["run_id"].nunique() == 20, f"Confidence budget {budget} lacks 20 runs")
        for subset_name, boundary, quantile, full_mask in subsets:
            mask = full_mask.loc[budget_frame.index]
            group = budget_frame[mask].copy()
            require(len(group) > 0, f"Empty confidence subset {budget}/{subset_name}")
            for run_id, run_group in group.groupby("run_id", sort=True):
                high80 = run_group["confidence"].ge(0.80)
                high90 = run_group["confidence"].ge(0.90)
                run_rows.append(
                    {
                        "budget": budget,
                        "subset": subset_name,
                        "boundary_definition": boundary,
                        "quantile": quantile,
                        "run_id": run_id,
                        "prediction_count": len(run_group),
                        "mean_confidence": float(run_group["confidence"].mean()),
                        "median_confidence": float(run_group["confidence"].median()),
                        "fraction_confidence_ge_080": float(high80.mean()),
                        "fraction_confidence_ge_090": float(high90.mean()),
                        "accuracy_confidence_ge_080": (
                            float(run_group.loc[high80, "correct"].mean()) if high80.any() else None
                        ),
                        "accuracy_confidence_ge_090": (
                            float(run_group.loc[high90, "correct"].mean()) if high90.any() else None
                        ),
                        "brier_score": float(
                            np.mean((run_group["keyhole_probability"] - run_group["has_keyhole"]) ** 2)
                        ),
                    }
                )

            metadata = {
                "budget": budget,
                "subset": subset_name,
                "boundary_definition": boundary,
                "quantile": quantile,
            }
            probability_rows, probability_ece = calibration_bins(
                group["keyhole_probability"].to_numpy(float),
                group["has_keyhole"].to_numpy(float),
                np.linspace(0.0, 1.0, 11),
                "keyhole_probability_reliability",
                metadata,
            )
            confidence_rows, confidence_ece = calibration_bins(
                group["confidence"].to_numpy(float),
                group["correct"].astype(float).to_numpy(),
                np.linspace(0.5, 1.0, 11),
                "confidence_accuracy_reliability",
                metadata,
            )
            calibration_rows.extend(probability_rows)
            calibration_rows.extend(confidence_rows)
            high80 = group["confidence"].ge(0.80)
            high90 = group["confidence"].ge(0.90)
            run_subset = pd.DataFrame(run_rows)
            run_subset = run_subset[
                run_subset["budget"].eq(budget) & run_subset["subset"].eq(subset_name)
            ]
            mean_conf_stats = describe(run_subset["mean_confidence"])
            summary_rows.append(
                {
                    "budget": budget,
                    "method": M_BINARY,
                    "subset": subset_name,
                    "boundary_definition": boundary,
                    "quantile": quantile,
                    "outer_run_count": int(group["run_id"].nunique()),
                    "pooled_prediction_count": int(len(group)),
                    "pooled_mean_confidence": float(group["confidence"].mean()),
                    "pooled_median_confidence": float(group["confidence"].median()),
                    "mean_run_confidence": mean_conf_stats["mean"],
                    "ci95_mean_run_confidence_lower": mean_conf_stats["ci95_lower"],
                    "ci95_mean_run_confidence_upper": mean_conf_stats["ci95_upper"],
                    "fraction_confidence_ge_080": float(high80.mean()),
                    "count_confidence_ge_080": int(high80.sum()),
                    "accuracy_confidence_ge_080": (
                        float(group.loc[high80, "correct"].mean()) if high80.any() else None
                    ),
                    "fraction_confidence_ge_090": float(high90.mean()),
                    "count_confidence_ge_090": int(high90.sum()),
                    "accuracy_confidence_ge_090": (
                        float(group.loc[high90, "correct"].mean()) if high90.any() else None
                    ),
                    "pooled_accuracy": float(group["correct"].mean()),
                    "pooled_brier_score": float(
                        np.mean((group["keyhole_probability"] - group["has_keyhole"]) ** 2)
                    ),
                    "probability_ece_10_equal_width_bins": probability_ece,
                    "confidence_ece_10_equal_width_bins": confidence_ece,
                    "probabilities_authoritatively_saved": True,
                    "probabilities_posthoc_calibrated": False,
                    "repeated_cv_predictions_not_independent_physical_trials": True,
                    "physical_boundary_certainty_claim_allowed": False,
                }
            )
    run_frame = pd.DataFrame(run_rows).sort_values(["budget", "subset", "run_id"])
    summary = pd.DataFrame(summary_rows).sort_values(["budget", "subset"])
    calibration = pd.DataFrame(calibration_rows).sort_values(
        ["budget", "subset", "calibration_type", "bin_index"]
    )
    write_csv(OUT1 / "predictive_confidence_run_level.csv", run_frame)
    write_csv(OUT1 / "predictive_confidence_summary.csv", summary)
    write_csv(OUT1 / "predictive_calibration_summary.csv", calibration)
    return run_frame, summary, calibration


def normalized_aulc(group: pd.DataFrame, metric: str) -> float:
    ordered = group.sort_values("budget")
    x = ordered["budget"].to_numpy(float)
    y = ordered[metric].to_numpy(float)
    require(x[0] == COMMON_START and x[-1] == FINAL_BUDGET and len(x) == 65, "AULC grid drift")
    return float(np.trapezoid(y, x) / (FINAL_BUDGET - COMMON_START))


def method_random_equivalent_at_budget(
    learning: pd.DataFrame,
    method: str,
    budget: int,
) -> tuple[float, float | None, str]:
    if method == M_RANDOM:
        target = float(
            mean_accuracy_curve(learning, method, "B1", 20)
            .loc[lambda frame: frame["budget"].eq(budget), "mean_accuracy"]
            .iloc[0]
        )
        return target, float(budget), "baseline_reference"
    target = float(
        mean_accuracy_curve(learning, method, "B1", 20)
        .loc[lambda frame: frame["budget"].eq(budget), "mean_accuracy"]
        .iloc[0]
    )
    equivalent = random_equivalent_for_target(mean_accuracy_curve(learning, M_RANDOM, "B1", 20), target)
    return target, equivalent, "matched" if equivalent is not None else "not_matched_by_80"


def lookup_target(
    target_summary: pd.DataFrame,
    method: str,
    quantile: int,
    target: float,
) -> pd.Series:
    row = target_summary[
        target_summary["boundary_definition"].eq("B1")
        & target_summary["quantile"].eq(quantile)
        & target_summary["method"].eq(method)
        & np.isclose(target_summary["target_accuracy"], target)
    ]
    require(len(row) == 1, f"Target lookup failed {method}/q{quantile}/{target}")
    return row.iloc[0]


def compute_real_scorecard(
    tables: dict[str, pd.DataFrame],
    target_summary: pd.DataFrame,
) -> pd.DataFrame:
    aulc = tables["aulc"]
    aulc = aulc[aulc["method"].isin(METHODS)].copy()
    learning = tables["learning"]
    run_extra_rows: list[dict[str, Any]] = []
    for (method, run_id), group in learning[
        learning["budget"].between(COMMON_START, FINAL_BUDGET)
    ].groupby(["method", "run_id"], sort=True):
        run_extra_rows.append(
            {
                "method": method,
                "run_id": run_id,
                "sensitivity_aulc": normalized_aulc(group, "sensitivity"),
                "specificity_aulc": normalized_aulc(group, "specificity"),
            }
        )
    extra = pd.DataFrame(run_extra_rows)
    final = learning[learning["budget"].eq(80)]
    runtime = tables["runtime"].set_index("method")
    discovery = read_csv(OUT1 / "keyhole_discovery_by_budget.csv")
    rows: list[dict[str, Any]] = []
    for method in METHODS:
        method_aulc = aulc[aulc["method"].eq(method)]
        require(len(method_aulc) == 20, f"AULC coverage drift for {method}")
        method_extra = extra[extra["method"].eq(method)]
        method_final = final[final["method"].eq(method)]
        target_acc, equivalent, eq_status = method_random_equivalent_at_budget(learning, method, 40)
        t_q20_80 = lookup_target(target_summary, method, 20, 0.80)
        t_q20_85 = lookup_target(target_summary, method, 20, 0.85)
        t_q30_80 = lookup_target(target_summary, method, 30, 0.80)
        discovery30 = discovery[
            discovery["method"].eq(method) & discovery["budget"].eq(30)
        ].iloc[0]
        if method == M_RANDOM:
            saving_display = "0 (reference)"
            saving_lower = 0.0
        elif equivalent is None:
            saving_display = ">40"
            saving_lower = 40.0
        else:
            saving_display = f"{equivalent - 40:.2f}"
            saving_lower = equivalent - 40
        rows.append(
            {
                "method": method,
                "method_label": METHOD_LABELS[method],
                "run_count": 20,
                "mean_B1_q20_error_aulc": float(method_aulc["common_normalized_aulc__B1_q20_error"].mean()),
                "mean_B1_q20_accuracy_aulc": float(1.0 - method_aulc["common_normalized_aulc__B1_q20_error"].mean()),
                "mean_B1_q30_error_aulc": float(method_aulc["common_normalized_aulc__B1_q30_error"].mean()),
                "mean_B1_q30_accuracy_aulc": float(1.0 - method_aulc["common_normalized_aulc__B1_q30_error"].mean()),
                "mean_B2_q20_error_aulc": float(method_aulc["common_normalized_aulc__B2_q20_error"].mean()),
                "mean_B3_q20_error_aulc": float(method_aulc["common_normalized_aulc__B3_q20_error"].mean()),
                "mean_balanced_accuracy_aulc": float(method_aulc["common_normalized_aulc__balanced_accuracy"].mean()),
                "mean_sensitivity_aulc": float(method_extra["sensitivity_aulc"].mean()),
                "mean_specificity_aulc": float(method_extra["specificity_aulc"].mean()),
                "final_budget_mean_balanced_accuracy": float(method_final["balanced_accuracy"].mean()),
                "final_budget_mean_sensitivity": float(method_final["sensitivity"].mean()),
                "final_budget_mean_specificity": float(method_final["specificity"].mean()),
                "q20_80_success_count": int(t_q20_80["successful_runs"]),
                "q20_80_median_queries_successful": safe_float(t_q20_80["median_queries_successful_runs"]),
                "q20_85_success_count": int(t_q20_85["successful_runs"]),
                "q20_85_median_queries_successful": safe_float(t_q20_85["median_queries_successful_runs"]),
                "q30_80_success_count": int(t_q30_80["successful_runs"]),
                "q30_80_median_queries_successful": safe_float(t_q30_80["median_queries_successful_runs"]),
                "mean_keyhole_discovered_budget30": float(discovery30["mean_keyhole_discovered"]),
                "mean_keyhole_enrichment_budget30": float(discovery30["mean_keyhole_enrichment"]),
                "mean_B1_q20_accuracy_budget40": target_acc,
                "random_equivalent_budget_for_budget40_performance": equivalent,
                "random_equivalent_status": eq_status,
                "query_saving_vs_random_at_budget40_display": saving_display,
                "query_saving_vs_random_at_budget40_lower_bound": saving_lower,
                "mean_local_runtime_seconds_per_outer_run": float(runtime.loc[method, "mean_runtime_seconds"]),
                "domain_transfer_caveat": "Combined old/new repeated-CV benchmark; subgroup prevalence and transfer differ.",
                "semantic_alignment": (
                    "Directly models manual has_keyhole"
                    if method in [M_BINARY, M_RANDOM]
                    else "Uses maximum depth for acquisition/prediction threshold; manual has_keyhole remains evaluation reference"
                ),
                "primary_role": (
                    "final primary acquisition"
                    if method == M_BINARY
                    else "authoritative random baseline"
                    if method == M_RANDOM
                    else "secondary continuous physical comparator"
                ),
            }
        )
    scorecard = pd.DataFrame(rows)
    write_csv(OUT2 / "final_real_data_scorecard.csv", scorecard)
    return scorecard


def compute_synthetic_summary(synthetic: pd.DataFrame) -> pd.DataFrame:
    benchmark_map = {
        "branin": "Branin",
        "hartmann4": "Hartmann4",
        "ackley": "Ackley4 (optional, 3 seeds)",
    }
    rows: list[dict[str, Any]] = []
    for benchmark, display in benchmark_map.items():
        group = synthetic[synthetic["benchmark"].eq(benchmark)].copy()
        require(len(group) == 6, f"Synthetic summary drift for {benchmark}")
        repulsion = group[group["method"].eq("classifier_uncertainty_repulsion")].iloc[0]
        random = group[group["method"].eq("random_classifier")].iloc[0]
        sur = group[group["method"].str.startswith("gpc_bernoulli_sur_refit")].sort_values(
            "mean_final_near_boundary_error_q20"
        ).iloc[0]
        best = group.sort_values("mean_final_near_boundary_error_q20").iloc[0]
        rows.append(
            {
                "benchmark": display,
                "source_benchmark_id": benchmark,
                "seed_count": int(group["seed_count"].iloc[0]),
                "final_budget": 80,
                "best_q20_method": best["method"],
                "best_q20_error": float(best["mean_final_near_boundary_error_q20"]),
                "best_q30_method": group.sort_values("mean_final_near_boundary_error_q30").iloc[0]["method"],
                "best_q30_error": float(group["mean_final_near_boundary_error_q30"].min()),
                "uncertainty_repulsion_global_error": float(repulsion["mean_final_global_error"]),
                "uncertainty_repulsion_q20_error": float(repulsion["mean_final_near_boundary_error_q20"]),
                "uncertainty_repulsion_q30_error": float(repulsion["mean_final_near_boundary_error_q30"]),
                "best_sur_method": sur["method"],
                "best_sur_q20_error": float(sur["mean_final_near_boundary_error_q20"]),
                "random_q20_error": float(random["mean_final_near_boundary_error_q20"]),
                "complex_sur_wins_q20": bool(best["method"].startswith("gpc_bernoulli_sur_refit")),
                "boundary_and_global_winner_same": bool(
                    group.sort_values("mean_final_global_error").iloc[0]["method"] == best["method"]
                ),
                "evidence_lesson": (
                    "Simple uncertainty-repulsion wins q20; SUR complexity is not automatically beneficial."
                    if benchmark == "branin"
                    else "SUR k25 wins q20 narrowly; method ranking depends on boundary geometry."
                    if benchmark == "hartmann4"
                    else "Entropy/margin wins q20 while uncertainty-repulsion wins global error; metric choice reorders methods."
                ),
                "source_artifact": "outputs/week4_09_gpc_bernoulli_sur_validation/combined/gpc_bernoulli_sur_validation_summary.csv",
                "fairness_passed": bool(group["fairness_passed"].all()),
                "ackley_is_optional": benchmark == "ackley",
            }
        )
    result = pd.DataFrame(rows)
    write_csv(OUT2 / "synthetic_to_real_summary.csv", result)
    return result


def build_claim_ledger(
    scorecard: pd.DataFrame,
    equivalent: pd.DataFrame,
    confidence: pd.DataFrame,
) -> pd.DataFrame:
    binary = scorecard[scorecard["method"].eq(M_BINARY)].iloc[0]
    random = scorecard[scorecard["method"].eq(M_RANDOM)].iloc[0]
    depth = scorecard[scorecard["method"].eq(M_DEPTH)].iloc[0]
    eq30 = equivalent[equivalent["binary_budget"].eq(30)].iloc[0]
    conf40 = confidence[
        confidence["budget"].eq(40) & confidence["subset"].eq("B1_q20")
    ].iloc[0]
    rows = [
        {
            "claim_id": "C01",
            "category": "SUPPORTED PRIMARY CLAIMS",
            "claim": "Binary active learning is more sample-efficient than random for empirical manual-label boundary localization.",
            "status": "SUPPORTED",
            "evidence_level": "primary matched retrospective benchmark",
            "primary_or_secondary": "primary",
            "supporting_phase": "Week 8 Phase 1",
            "supporting_artifact": "outputs/week8_01_final_sample_efficiency/random_equivalent_budget.csv; outputs/week8_02_thesis_consolidation/final_real_data_scorecard.csv",
            "exact_metric": f"B1-q20 accuracy AULC {binary['mean_B1_q20_accuracy_aulc']:.4f} vs {random['mean_B1_q20_accuracy_aulc']:.4f}; Binary budget 30 matched by Random at {eq30['random_equivalent_budget']:.0f}",
            "allowed_wording": "Binary was more sample-efficient than Random for held-out empirical B1-q20/q30 classification in this offline benchmark.",
            "forbidden_overclaim": "Binary is universally optimal or prospectively proven on new simulator campaigns.",
            "caveat": "Twenty matched repeated-CV runs reuse the same 405 saved simulations.",
        },
        {
            "claim_id": "C02",
            "category": "SUPPORTED PRIMARY CLAIMS",
            "claim": "Binary uncertainty-repulsion is the final primary real-data acquisition.",
            "status": "SUPPORTED",
            "evidence_level": "preregistered Phase 7 decision",
            "primary_or_secondary": "primary",
            "supporting_phase": "Week 7 Phase 7",
            "supporting_artifact": "outputs/week7_07_final_boundary_hybrid_benchmark/phase7_final_decision.csv",
            "exact_metric": "decision = BINARY ACQUISITION PRIMARY; both Hybrid success flags false",
            "allowed_wording": "The final recommended real-data strategy is Binary GPC plus binary uncertainty-repulsion.",
            "forbidden_overclaim": "The method dominates every target, metric, or domain.",
            "caveat": "Max-Depth retains a secondary physical-comparator role.",
        },
        {
            "claim_id": "C03",
            "category": "SUPPORTED SECONDARY / DIAGNOSTIC CLAIMS",
            "claim": "Max-Depth has stronger global balanced-accuracy and sensitivity trajectories under the Phase 6/7 benchmark.",
            "status": "SUPPORTED",
            "evidence_level": "secondary global predictive evidence",
            "primary_or_secondary": "secondary",
            "supporting_phase": "Week 7 Phase 6 and Week 8 consolidation",
            "supporting_artifact": "outputs/week7_06_real_data_boundary_active_level_set/phase6_formulation_scorecard.csv; outputs/week8_02_thesis_consolidation/final_real_data_scorecard.csv",
            "exact_metric": f"balanced-accuracy AULC {depth['mean_balanced_accuracy_aulc']:.4f} vs Binary {binary['mean_balanced_accuracy_aulc']:.4f}; sensitivity AULC {depth['mean_sensitivity_aulc']:.4f} vs {binary['mean_sensitivity_aulc']:.4f}",
            "allowed_wording": "Max-Depth is the stronger secondary global classifier/physical comparator in this benchmark.",
            "forbidden_overclaim": "Max-Depth is therefore the best boundary-localization acquisition.",
            "caveat": "Global accuracy and near-boundary error answer different questions.",
        },
        {
            "claim_id": "C04",
            "category": "SUPPORTED PRIMARY CLAIMS",
            "claim": "Max-Depth does not improve Binary boundary acquisition in the two tested Hybrids.",
            "status": "SUPPORTED",
            "evidence_level": "preregistered negative result",
            "primary_or_secondary": "primary",
            "supporting_phase": "Week 7 Phase 7",
            "supporting_artifact": "outputs/week7_07_final_boundary_hybrid_benchmark/phase7_preregistered_rule_outcome.csv",
            "exact_metric": "Neither gate20 nor equal-rank fusion met the robust success rule.",
            "allowed_wording": "Neither of the two fixed Hybrids improved on Binary under the preregistered hierarchy.",
            "forbidden_overclaim": "All possible hybrid uses of physical side information are useless.",
            "caveat": "Only two fixed, untuned Hybrid formulations were tested.",
        },
        {
            "claim_id": "C05",
            "category": "SUPPORTED SECONDARY / DIAGNOSTIC CLAIMS",
            "claim": "G3 perfectly separates new-data but has a partition-dependent threshold.",
            "status": "SUPPORTED",
            "evidence_level": "secondary proxy and transfer evidence",
            "primary_or_secondary": "secondary",
            "supporting_phase": "Week 7 Phases 5 and 5.5",
            "supporting_artifact": "outputs/week7_05_keyhole_physical_proxy_analysis/results_summary.md; outputs/week7_05_5_g3_robustness_transfer_analysis/results_summary.md",
            "exact_metric": "new-data ROC AUC/AP/LOO balanced accuracy = 1.0000; worst transfer balanced accuracy = 0.8125",
            "allowed_wording": "G3 is a strong scalar companion with partition-shift caveats.",
            "forbidden_overclaim": "G3 defines a universal morphology boundary.",
            "caveat": "Manual cavity-based has_keyhole remains ground truth.",
        },
        {
            "claim_id": "C06",
            "category": "CLAIMS WE MUST NOT MAKE",
            "claim": "A universal G3 threshold is supported.",
            "status": "NOT SUPPORTED / PROHIBITED",
            "evidence_level": "explicit limitation",
            "primary_or_secondary": "limitation",
            "supporting_phase": "Week 7 Phase 5.5",
            "supporting_artifact": "outputs/week7_05_5_g3_robustness_transfer_analysis/results_summary.md",
            "exact_metric": "threshold is partition sensitive despite direction agreement",
            "allowed_wording": "G3 thresholds transfer imperfectly and remain population dependent.",
            "forbidden_overclaim": "One G3 cutoff universally separates Keyhole physics.",
            "caveat": "Observed populations do not establish a physical constant.",
        },
        {
            "claim_id": "C07",
            "category": "CLAIMS WE MUST NOT MAKE",
            "claim": "A universal Max-Depth threshold is supported.",
            "status": "NOT SUPPORTED / PROHIBITED",
            "evidence_level": "explicit limitation",
            "primary_or_secondary": "limitation",
            "supporting_phase": "Week 7 Phase 6",
            "supporting_artifact": "outputs/week7_06_real_data_boundary_active_level_set/phase6_final_decision.csv",
            "exact_metric": "threshold_is_universal_physical_constant = False",
            "allowed_wording": "Max-Depth is a useful learned continuous comparator with online, queried-data thresholds.",
            "forbidden_overclaim": "The fitted depth threshold is a universal physical constant.",
            "caveat": "Thresholds depend on sampled data and partition.",
        },
        {
            "claim_id": "C08",
            "category": "CLAIMS WE MUST NOT MAKE",
            "claim": "Input-response associations establish causal effects.",
            "status": "NOT SUPPORTED / PROHIBITED",
            "evidence_level": "observational simulation-design limitation",
            "primary_or_secondary": "limitation",
            "supporting_phase": "Weeks 6-8",
            "supporting_artifact": "outputs/week7_07_final_boundary_hybrid_benchmark/phase7_final_decision.csv",
            "exact_metric": "causal_claim = False",
            "allowed_wording": "Inputs are associated with saved physical responses under the sampled design.",
            "forbidden_overclaim": "Changing an input causes the reported response change by the fitted amount.",
            "caveat": "No causal intervention design was analyzed.",
        },
        {
            "claim_id": "C09",
            "category": "CLAIMS WE MUST NOT MAKE",
            "claim": "B1/B2/B3 are the true continuous physical boundary.",
            "status": "NOT SUPPORTED / PROHIBITED",
            "evidence_level": "construct-validity limitation",
            "primary_or_secondary": "limitation",
            "supporting_phase": "Week 7 Phase 7 and Week 8",
            "supporting_artifact": "outputs/week7_07_final_boundary_hybrid_benchmark/boundary_metric_definitions.csv",
            "exact_metric": "B1/B2/B3 are evaluation-only empirical subsets based on the 405 sampled points.",
            "allowed_wording": "B1/B2/B3 are empirical near-boundary diagnostics for manual labels.",
            "forbidden_overclaim": "They locate the continuous physical transition surface exactly.",
            "caveat": "Membership is sample-density and definition dependent.",
        },
        {
            "claim_id": "C10",
            "category": "SUPPORTED SECONDARY / DIAGNOSTIC CLAIMS",
            "claim": "No acquisition universally dominates every synthetic benchmark.",
            "status": "SUPPORTED",
            "evidence_level": "multi-benchmark synthetic evidence",
            "primary_or_secondary": "secondary",
            "supporting_phase": "Synthetic Weeks 2-4",
            "supporting_artifact": "outputs/week4_09_gpc_bernoulli_sur_validation/combined/gpc_bernoulli_sur_validation_summary.csv",
            "exact_metric": "q20 winners: uncertainty-repulsion on Branin, SUR-k25 on Hartmann4, entropy/margin on optional Ackley4",
            "allowed_wording": "Method ranking depends on benchmark geometry and evaluation metric.",
            "forbidden_overclaim": "One acquisition is universally best.",
            "caveat": "Synthetic seed counts are 5/5/3 and Ackley is optional diagnostic evidence.",
        },
        {
            "claim_id": "C11",
            "category": "CLAIMS WE MUST NOT MAKE",
            "claim": "Repeated cross-validation is equivalent to independent new physical simulator trials.",
            "status": "NOT SUPPORTED / PROHIBITED",
            "evidence_level": "validation-design limitation",
            "primary_or_secondary": "limitation",
            "supporting_phase": "Week 8",
            "supporting_artifact": "outputs/week8_01_final_sample_efficiency/phase8_01_preflight.json",
            "exact_metric": "20 runs = 4 repeats x 5 folds on the same 405 saved simulations",
            "allowed_wording": "The matched repeated-CV design quantifies retrospective held-out sample efficiency.",
            "forbidden_overclaim": "Twenty independent simulator campaigns confirmed the method.",
            "caveat": "Repeated folds are dependent through shared simulations.",
        },
        {
            "claim_id": "C12",
            "category": "CLAIMS WE MUST NOT MAKE",
            "claim": "Prospective new-simulator validation was performed.",
            "status": "NOT SUPPORTED / PROHIBITED",
            "evidence_level": "scope limitation",
            "primary_or_secondary": "limitation",
            "supporting_phase": "Week 8",
            "supporting_artifact": "outputs/week8_01_final_sample_efficiency/phase8_01_preflight.json",
            "exact_metric": "new_simulator_runs = False; offline_retrospective_benchmark = True",
            "allowed_wording": "Outputs were hidden until queried in an offline benchmark over saved simulations.",
            "forbidden_overclaim": "The method was deployed in a live simulator loop.",
            "caveat": "Prospective confirmation remains future work.",
        },
        {
            "claim_id": "C13",
            "category": "SUPPORTED SECONDARY / DIAGNOSTIC CLAIMS",
            "claim": "Saved probabilities support model-confidence statements near B1-q20, but not physical-boundary certainty.",
            "status": "SUPPORTED WITH CALIBRATION CAVEAT",
            "evidence_level": "held-out saved probability diagnostic",
            "primary_or_secondary": "secondary",
            "supporting_phase": "Week 8 Phase 1",
            "supporting_artifact": "outputs/week8_01_final_sample_efficiency/predictive_confidence_summary.csv",
            "exact_metric": f"budget 40: {conf40['fraction_confidence_ge_080']:.1%} of B1-q20 predictions at >=0.80 confidence; {conf40['accuracy_confidence_ge_080']:.1%} correct in that band",
            "allowed_wording": "At budget 40, the saved GPC assigned at least 80% model confidence to the reported fraction of B1-q20 predictions.",
            "forbidden_overclaim": "The continuous physical boundary is known with 80% certainty.",
            "caveat": "GPC probabilities were not post-hoc calibrated and repeated-CV predictions are dependent.",
        },
    ]
    ledger = pd.DataFrame(rows)
    write_csv(OUT2 / "final_thesis_claim_ledger.csv", ledger)
    return ledger


def snapshot_value(
    snapshots: dict[str, pd.DataFrame],
    boundary: str,
    budget: int,
    method: str,
    column: str,
) -> float:
    row = snapshots[boundary][
        snapshots[boundary]["budget"].eq(budget) & snapshots[boundary]["method"].eq(method)
    ]
    require(len(row) == 1, f"Snapshot lookup failed {boundary}/{budget}/{method}/{column}")
    return float(row.iloc[0][column])


def target_display(row: pd.Series) -> str:
    median = row["median_queries_successful_runs"]
    if pd.isna(median):
        return f"not reached (0/{int(row['total_runs'])})"
    return f"{float(median):g} ({int(row['successful_runs'])}/{int(row['total_runs'])})"


def write_headlines_and_phase1_text(
    snapshots: dict[str, pd.DataFrame],
    target_summary: pd.DataFrame,
    equivalent: pd.DataFrame,
    discovery: pd.DataFrame,
    confidence: pd.DataFrame,
    scorecard: pd.DataFrame,
) -> pd.DataFrame:
    b40 = snapshot_value(snapshots, "B1", 40, M_BINARY, "mean_q20_accuracy")
    r40 = snapshot_value(snapshots, "B1", 40, M_RANDOM, "mean_q20_accuracy")
    b40q30 = snapshot_value(snapshots, "B1", 40, M_BINARY, "mean_q30_accuracy")
    r40q30 = snapshot_value(snapshots, "B1", 40, M_RANDOM, "mean_q30_accuracy")
    binary80 = lookup_target(target_summary, M_BINARY, 20, 0.80)
    random80 = lookup_target(target_summary, M_RANDOM, 20, 0.80)
    eq30 = equivalent[equivalent["binary_budget"].eq(30)].iloc[0]
    eq40 = equivalent[equivalent["binary_budget"].eq(40)].iloc[0]
    disc30_b = discovery[discovery["budget"].eq(30) & discovery["method"].eq(M_BINARY)].iloc[0]
    disc30_r = discovery[discovery["budget"].eq(30) & discovery["method"].eq(M_RANDOM)].iloc[0]
    conf40 = confidence[confidence["budget"].eq(40) & confidence["subset"].eq("B1_q20")].iloc[0]
    sc_binary = scorecard[scorecard["method"].eq(M_BINARY)].iloc[0]
    sc_random = scorecard[scorecard["method"].eq(M_RANDOM)].iloc[0]
    sc_b2_adv = sc_random["mean_B2_q20_error_aulc"] - sc_binary["mean_B2_q20_error_aulc"]
    sc_b3_adv = sc_random["mean_B3_q20_error_aulc"] - sc_binary["mean_B3_q20_error_aulc"]
    statements = [
        (
            "H01",
            f"At 40 simulator queries, Binary reaches {b40:.1%} mean B1-q20 empirical near-boundary accuracy, versus {r40:.1%} for Random (+{(b40-r40)*100:.1f} percentage points).",
            "budget_snapshot_b1.csv",
            "budget=40; methods=Binary,Random; mean_q20_accuracy",
        ),
        (
            "H02",
            f"At 40 queries, Binary reaches {b40q30:.1%} mean B1-q30 accuracy, versus {r40q30:.1%} for Random (+{(b40q30-r40q30)*100:.1f} percentage points).",
            "budget_snapshot_b1.csv",
            "budget=40; methods=Binary,Random; mean_q30_accuracy",
        ),
        (
            "H03",
            f"For B1-q20 accuracy >=80%, Binary succeeds in {int(binary80['successful_runs'])}/20 runs with median first crossing {binary80['median_queries_successful_runs']:.0f} queries; Random succeeds in {int(random80['successful_runs'])}/20 with median {random80['median_queries_successful_runs']:.0f} among successful runs.",
            "queries_to_accuracy_target.csv",
            "B1; q20; target=0.80; methods=Binary,Random",
        ),
        (
            "H04",
            f"Binary's mean {eq30['binary_mean_accuracy']:.1%} B1-q20 accuracy at budget 30 is first matched by the observed Random mean curve at about {eq30['random_equivalent_budget']:.0f} queries: approximately {eq30['query_saving']:.0f} saved simulator calls ({eq30['efficiency_multiplier']:.2f}x query equivalent).",
            "random_equivalent_budget.csv",
            "binary_budget=30",
        ),
        (
            "H05",
            f"Binary's mean {eq40['binary_mean_accuracy']:.1%} B1-q20 accuracy at budget 40 is not matched by Random by budget 80, implying >40 saved calls and a >2.00x lower-query equivalent within the observed horizon.",
            "random_equivalent_budget.csv",
            "binary_budget=40; status=not_matched_by_80",
        ),
        (
            "H06",
            f"At budget 30, Binary has discovered {disc30_b['mean_keyhole_discovered']:.2f} Keyhole simulations on average, versus {disc30_r['mean_keyhole_discovered']:.2f} for Random; discovery is a secondary diagnostic, not a boundary-localization metric.",
            "keyhole_discovery_by_budget.csv",
            "budget=30; methods=Binary,Random",
        ),
        (
            "H07",
            f"At budget 40, {conf40['fraction_confidence_ge_080']:.1%} of held-out B1-q20 predictions carry at least 80% saved GPC confidence, and {conf40['accuracy_confidence_ge_080']:.1%} of that high-confidence band is correct.",
            "predictive_confidence_summary.csv",
            "budget=40; subset=B1_q20",
        ),
        (
            "H08",
            f"Binary's B1-q20 accuracy AULC is {sc_binary['mean_B1_q20_accuracy_aulc']:.4f}, compared with {sc_random['mean_B1_q20_accuracy_aulc']:.4f} for Random over the common 16-80 budget grid.",
            "../week8_02_thesis_consolidation/final_real_data_scorecard.csv",
            "methods=Binary,Random; mean_B1_q20_accuracy_aulc",
        ),
        (
            "H09",
            f"The Binary advantage over Random is robust in direction under B2 and B3 q20 error AULC (reductions {sc_b2_adv:.4f} and {sc_b3_adv:.4f}, respectively).",
            "../week8_02_thesis_consolidation/final_real_data_scorecard.csv",
            "methods=Binary,Random; B2/B3 q20 error AULC",
        ),
        (
            "H10",
            "All sample-efficiency results are offline/retrospective: held-out saved simulations were hidden until queried, but no new simulator campaign or prospective closed loop was run.",
            "phase8_01_preflight.json",
            "offline_retrospective_benchmark=true; prospective_new_simulator_validation=false",
        ),
    ]
    rows = [
        {
            "claim_id": claim_id,
            "statement": statement,
            "source_artifact": (
                f"outputs/week8_02_thesis_consolidation/{artifact.removeprefix('../week8_02_thesis_consolidation/')}"
                if artifact.startswith("../week8_02_thesis_consolidation/")
                else f"outputs/week8_01_final_sample_efficiency/{artifact}"
            ),
            "source_filter_or_metric": source_filter,
            "physical_boundary_certainty_claim": False,
        }
        for claim_id, statement, artifact, source_filter in statements
    ]
    headlines = pd.DataFrame(rows)
    write_csv(OUT1 / "headline_results.csv", headlines)
    markdown = "# Week 8 Phase 1 headline results\n\n"
    markdown += "These statements describe empirical held-out boundary-region classification or saved GPC model confidence. They do **not** state certainty about the continuous physical boundary.\n\n"
    for row in headlines.itertuples(index=False):
        markdown += f"- **{row.claim_id}.** {row.statement}\n"
    (OUT1 / "headline_results.md").write_text(markdown, encoding="utf-8")

    budget_rows = []
    for budget in HEADLINE_BUDGETS:
        budget_rows.append(
            {
                "Bütçe": budget,
                "Binary q20": f"{snapshot_value(snapshots, 'B1', budget, M_BINARY, 'mean_q20_accuracy'):.1%}",
                "Random q20": f"{snapshot_value(snapshots, 'B1', budget, M_RANDOM, 'mean_q20_accuracy'):.1%}",
                "Binary q30": f"{snapshot_value(snapshots, 'B1', budget, M_BINARY, 'mean_q30_accuracy'):.1%}",
                "Random q30": f"{snapshot_value(snapshots, 'B1', budget, M_RANDOM, 'mean_q30_accuracy'):.1%}",
            }
        )
    budget_table = pd.DataFrame(budget_rows)
    target_rows = []
    for target in TARGETS:
        target_rows.append(
            {
                "Hedef": f"{target:.0%}",
                "Binary q20": target_display(lookup_target(target_summary, M_BINARY, 20, target)),
                "Random q20": target_display(lookup_target(target_summary, M_RANDOM, 20, target)),
                "Binary q30": target_display(lookup_target(target_summary, M_BINARY, 30, target)),
                "Random q30": target_display(lookup_target(target_summary, M_RANDOM, 30, target)),
            }
        )
    target_table = pd.DataFrame(target_rows)
    text = f"""# Week 8 Faz 1 — sade Türkçe özet

## Bu analiz neyi ölçüyor?

**Bütçe**, aktif öğrenicinin sonucunu görmesine izin verilen toplam simülasyon sayısıdır. Burada yeni simülasyon çalıştırılmadı; daha önce kaydedilmiş simülasyonlar, sorgulanana kadar öğreniciden gizlendi.

**B1-q20**, 405 örnek içindeki, zıt manuel etikete standartlaştırılmış girdi uzayında en yakın olan yaklaşık yüzde 20'lik test bölgesidir. “q20 doğruluğu %80” demek, bu seçilmiş held-out sınır-benzeri örneklerin yaklaşık %80'inin Keyhole/non-Keyhole olarak doğru sınıflandırılması demektir. Sürekli fiziksel sınırın konumunu “%80 kesinlikle biliyoruz” demek değildir.

## Bütçeye göre somut B1 doğrulukları

{df_to_markdown(budget_table)}

## İstenen doğruluğa kaç sorguda ulaşılıyor?

Hücre biçimi **başarılı koşulardaki medyan sorgu (başarı/20)** şeklindedir. Başarısız koşular medyandan silinmedi; başarı sayısında açıkça görünür.

{df_to_markdown(target_table)}

## En güçlü sorgu tasarrufu sonucu

Binary, 30 sorguda ortalama **{eq30['binary_mean_accuracy']:.1%} B1-q20 doğruluğuna** ulaşıyor. Random'ın gözlenen ortalama eğrisi aynı seviyeyi ilk kez yaklaşık **{eq30['random_equivalent_budget']:.0f} sorguda** yakalıyor. Bu, bu performans seviyesi için yaklaşık **{eq30['query_saving']:.0f} simülasyon çağrısı tasarrufu** ve **{eq30['efficiency_multiplier']:.2f}x sorgu eşdeğeri** demektir. Binary'nin 40 sorgudaki {eq40['binary_mean_accuracy']:.1%} seviyesi ise Random tarafından 80'e kadar yakalanmıyor; burada yalnızca **>40** tasarruf alt sınırı söylenebilir, 80'in ötesine sayı uydurulamaz.

## Model güveni ayrı bir kavramdır

Saklanmış GPC olasılıkları bulunduğu için gerçek bir model-güveni tanısı yapılabildi. Bütçe 40'ta B1-q20 tahminlerinin **{conf40['fraction_confidence_ge_080']:.1%}**'i en az %80 model güvenine sahip; bu yüksek-güven grubunun **{conf40['accuracy_confidence_ge_080']:.1%}**'i doğru. Bu, “fiziksel sınır %80 kesin” anlamına gelmez. Olasılıklar ayrıca sonradan kalibre edilmediği ve aynı 405 simülasyon tekrarlı katlarda kullanıldığı için kalibrasyon sonuçları tanısaldır.

## Random karşılaştırması nasıl yapıldı?

Her iki yöntem aynı 20 dış koşuyu, aynı test katlarını, aynı aday havuzlarını, aynı başlangıç permütasyonlarını ve aynı toplam bütçeyi kullanır. Random-eşdeğer bütçe yalnızca 16–80 arasındaki gözlenen Random ortalama eğrisinin komşu noktaları arasında doğrusal enterpolasyonla hesaplandı; 80 ötesine ekstrapolasyon yapılmadı.

## Keyhole keşfi neden ikincil?

Bütçe 30'da Binary ortalama **{disc30_b['mean_keyhole_discovered']:.2f}**, Random **{disc30_r['mean_keyhole_discovered']:.2f}** Keyhole örneği buluyor. Daha çok pozitif örnek bulmak faydalı olabilir, fakat bu tek başına sınırı daha iyi yerelleştirmek değildir; bu nedenle ana sonuç q20/q30 held-out doğruluğudur.
"""
    (OUT1 / "week8_phase1_plain_language_tr.md").write_text(text, encoding="utf-8")
    return headlines


def plot_accuracy(
    curves: pd.DataFrame,
    boundary: str,
    quantile: int,
    path: Path,
    title: str,
) -> None:
    frame = curves[
        curves["boundary_definition"].eq(boundary) & curves["quantile"].eq(quantile)
    ]
    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    for method in METHODS:
        group = frame[frame["method"].eq(method)].sort_values("budget")
        x = group["budget"].to_numpy(float)
        y = group["mean_accuracy"].to_numpy(float)
        low = group["ci95_accuracy_lower"].to_numpy(float)
        high = group["ci95_accuracy_upper"].to_numpy(float)
        ax.plot(x, y, color=COLORS[method], label=METHOD_LABELS[method], linewidth=2.2)
        ax.fill_between(x, low, high, color=COLORS[method], alpha=0.14)
    for budget in [30, 40, 60, 80]:
        ax.axvline(budget, color="#D0D0D0", linewidth=0.7, zorder=0)
    ax.set(xlabel="Total queried simulations", ylabel="Empirical boundary-region accuracy", title=title)
    ax.set_ylim(0.55, 0.95)
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=3, loc="lower right")
    fig.text(0.01, 0.01, "Shading: descriptive 95% t interval across 20 matched repeated-CV outer runs.", fontsize=8)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_improvement(improvement: pd.DataFrame, quantile: int, path: Path) -> None:
    frame = improvement[
        improvement["boundary_definition"].eq("B1") & improvement["quantile"].eq(quantile)
    ].sort_values("budget")
    x = frame["budget"].to_numpy(float)
    y = frame["mean_binary_minus_random_accuracy"].to_numpy(float) * 100
    low = frame["ci95_lower"].to_numpy(float) * 100
    high = frame["ci95_upper"].to_numpy(float) * 100
    fig, ax = plt.subplots(figsize=(8.8, 5.0))
    ax.axhline(0, color="black", linewidth=1)
    ax.plot(x, y, color=COLORS[M_BINARY], linewidth=2.2)
    ax.fill_between(x, low, high, color=COLORS[M_BINARY], alpha=0.18)
    for budget in [30, 40, 60, 80]:
        ax.axvline(budget, color="#D0D0D0", linewidth=0.7, zorder=0)
    ax.set(
        xlabel="Total queried simulations",
        ylabel="Binary minus Random accuracy (percentage points)",
        title=f"B1-q{quantile}: matched Binary advantage over Random",
    )
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_queries_to_target(targets: pd.DataFrame, path: Path) -> None:
    frame = targets[targets["boundary_definition"].eq("B1")]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), sharey=True)
    for ax, quantile in zip(axes, QUANTILES):
        for method in METHODS:
            group = frame[
                frame["quantile"].eq(quantile) & frame["method"].eq(method)
            ].sort_values("target_accuracy")
            x = group["target_accuracy"].to_numpy(float) * 100
            y = group["median_queries_successful_runs"].to_numpy(float)
            ax.plot(x, y, marker="o", color=COLORS[method], label=METHOD_LABELS[method])
            for target_x, median_y, successes in zip(x, y, group["successful_runs"]):
                if np.isfinite(median_y):
                    ax.annotate(f"{int(successes)}/20", (target_x, median_y), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=7)
        ax.set_title(f"B1-q{quantile}")
        ax.set_xlabel("Target empirical accuracy")
        ax.set_xticks([70, 75, 80, 85, 90])
        ax.set_ylim(8, 82)
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Median first-crossing budget among successful runs")
    axes[1].legend(frameon=False, loc="upper left")
    fig.suptitle("Queries to target (annotations show successful runs / 20)")
    fig.text(0.01, 0.01, "Unsuccessful runs are censored and remain in the success annotations; they are not imputed as 81.", fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_random_equivalent(equivalent: pd.DataFrame, path: Path, savings: bool = False) -> None:
    x = equivalent["binary_budget"].to_numpy(float)
    exact = equivalent["status"].eq("matched_within_observed_curve")
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    if savings:
        values = np.where(exact, equivalent["query_saving"], equivalent["query_saving_lower_bound"])
        bars = ax.bar(x, values, width=6, color=np.where(exact, COLORS[M_BINARY], "#56B4E9"), alpha=0.85)
        for bar, is_exact, display in zip(bars, exact, equivalent["query_saving_display"]):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1, str(display), ha="center", fontsize=9)
            if not is_exact:
                bar.set_hatch("//")
        ax.set_ylabel("Random-equivalent query saving")
        ax.set_title("Simulator-query saving for Binary B1-q20 performance")
    else:
        y = np.where(exact, equivalent["random_equivalent_budget"], FINAL_BUDGET)
        ax.plot([16, 80], [16, 80], color="#AAAAAA", linestyle="--", label="Equal budget")
        ax.plot(x[exact], y[exact], "o-", color=COLORS[M_BINARY], label="Exact observed crossing")
        ax.scatter(x[~exact], y[~exact], marker="^", s=90, color="#56B4E9", label="Not matched by 80")
        for bx, by, display in zip(x, y, equivalent["random_equivalent_budget_display"]):
            ax.annotate(str(display), (bx, by), xytext=(0, 7), textcoords="offset points", ha="center")
        ax.set_ylabel("Random-equivalent budget")
        ax.set_title("Random budget needed to match Binary mean B1-q20 accuracy")
        ax.legend(frameon=False)
    ax.set_xlabel("Binary budget")
    ax.set_xticks(x)
    ax.grid(axis="y", alpha=0.25)
    fig.text(0.01, 0.01, "Piecewise-linear interpolation only; hatched/triangle values are strict lower bounds, not extrapolations.", fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_discovery(discovery: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    for method in METHODS:
        group = discovery[discovery["method"].eq(method)].sort_values("budget")
        ax.errorbar(
            group["budget"],
            group["mean_keyhole_discovered"],
            yerr=[
                group["mean_keyhole_discovered"] - group["ci95_keyhole_discovered_lower"],
                group["ci95_keyhole_discovered_upper"] - group["mean_keyhole_discovered"],
            ],
            marker="o",
            capsize=3,
            color=COLORS[method],
            label=METHOD_LABELS[method],
        )
    ax.set(xlabel="Total queried simulations", ylabel="Mean Keyhole cases discovered", title="Keyhole discovery is secondary sample-efficiency evidence")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    fig.text(0.01, 0.01, "More positives discovered does not by itself imply better boundary localization.", fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_balanced_accuracy(learning: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    common = learning[learning["budget"].between(COMMON_START, FINAL_BUDGET)]
    for method in METHODS:
        rows = []
        for budget, group in common[common["method"].eq(method)].groupby("budget"):
            stats = describe(group["balanced_accuracy"])
            rows.append((budget, stats["mean"], stats["ci95_lower"], stats["ci95_upper"]))
        frame = pd.DataFrame(rows, columns=["budget", "mean", "low", "high"])
        x = frame["budget"].to_numpy(float)
        ax.plot(x, frame["mean"], color=COLORS[method], label=METHOD_LABELS[method], linewidth=2.2)
        ax.fill_between(x, frame["low"].to_numpy(float), frame["high"].to_numpy(float), color=COLORS[method], alpha=0.14)
    ax.set(xlabel="Total queried simulations", ylabel="Balanced accuracy", title="Global held-out classification performance")
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_reliability(calibration: pd.DataFrame, path: Path) -> None:
    frame = calibration[
        calibration["subset"].eq("B1_q20")
        & calibration["calibration_type"].eq("confidence_accuracy_reliability")
        & calibration["budget"].isin([20, 40, 80])
        & calibration["row_count"].gt(0)
    ]
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    ax.plot([0.5, 1.0], [0.5, 1.0], "--", color="#777777", label="Perfect confidence calibration")
    palette = {20: "#56B4E9", 40: "#0072B2", 80: "#003B5C"}
    for budget in [20, 40, 80]:
        group = frame[frame["budget"].eq(budget)]
        ax.plot(
            group["mean_prediction_or_confidence"],
            group["observed_positive_rate_or_accuracy"],
            marker="o",
            label=f"Budget {budget}",
            color=palette[budget],
        )
    ax.set(
        xlim=(0.5, 1.0),
        ylim=(0.5, 1.02),
        xlabel="Mean saved GPC confidence in bin",
        ylabel="Observed accuracy in bin",
        title="B1-q20 confidence reliability (diagnostic)",
    )
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_evidence_chain(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 3.8))
    ax.axis("off")
    labels = [
        "Synthetic benchmarks\nBranin / Hartmann4 / Ackley4",
        "Physical-response audit\nmax depth, G3, transfer",
        "Phase 6\nBinary vs Max-Depth",
        "Phase 7\nHybrid negative result",
        "Week 8\nqueries, savings, claims",
    ]
    colors = ["#E8F1F8", "#F7E8D8", "#E8F1F8", "#F7E8D8", "#D9EAD3"]
    xs = np.linspace(0.08, 0.92, len(labels))
    for index, (x, label, color) in enumerate(zip(xs, labels, colors)):
        ax.text(
            x,
            0.55,
            label,
            ha="center",
            va="center",
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.55", facecolor=color, edgecolor="#555555"),
            transform=ax.transAxes,
        )
        if index < len(labels) - 1:
            ax.annotate(
                "",
                xy=(xs[index + 1] - 0.09, 0.55),
                xytext=(x + 0.09, 0.55),
                xycoords=ax.transAxes,
                arrowprops=dict(arrowstyle="->", color="#555555", lw=1.8),
            )
    ax.text(0.5, 0.1, "Final recommendation: Binary GPC + uncertainty-repulsion; Max-Depth remains secondary", ha="center", fontsize=12, weight="bold", transform=ax.transAxes)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_tradeoff(scorecard: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 5.5))
    for row in scorecard.itertuples(index=False):
        ax.scatter(row.mean_balanced_accuracy_aulc, row.mean_B1_q20_accuracy_aulc, s=110, color=COLORS[row.method])
        ax.annotate(row.method_label, (row.mean_balanced_accuracy_aulc, row.mean_B1_q20_accuracy_aulc), xytext=(6, 6), textcoords="offset points")
    ax.set(
        xlabel="Balanced-accuracy AULC (higher is better)",
        ylabel="B1-q20 accuracy AULC (higher is better)",
        title="Boundary–global performance trade-off",
    )
    ax.grid(alpha=0.25)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_scorecard(scorecard: pd.DataFrame, path: Path) -> None:
    display = scorecard[
        [
            "method_label",
            "mean_B1_q20_accuracy_aulc",
            "mean_B1_q30_accuracy_aulc",
            "mean_balanced_accuracy_aulc",
            "q20_80_success_count",
            "mean_keyhole_discovered_budget30",
        ]
    ].copy()
    display.columns = ["Method", "q20 acc AULC", "q30 acc AULC", "BA AULC", "q20>=80% /20", "Keyhole @30"]
    for column in ["q20 acc AULC", "q30 acc AULC", "BA AULC"]:
        display[column] = display[column].map(lambda value: f"{value:.3f}")
    display["Keyhole @30"] = display["Keyhole @30"].map(lambda value: f"{value:.2f}")
    fig, ax = plt.subplots(figsize=(10, 2.6))
    ax.axis("off")
    table = ax.table(cellText=display.values, colLabels=display.columns, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.6)
    for column in range(len(display.columns)):
        table[(0, column)].set_facecolor("#D9EAD3")
        table[(0, column)].set_text_props(weight="bold")
    ax.set_title("Final real-data scorecard", pad=12, weight="bold")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_synthetic_summary(summary: pd.DataFrame, path: Path) -> None:
    x = np.arange(len(summary))
    width = 0.24
    fig, ax = plt.subplots(figsize=(9, 5.3))
    ax.bar(x - width, summary["uncertainty_repulsion_q20_error"], width, label="Uncertainty-repulsion", color="#0072B2")
    ax.bar(x, summary["best_sur_q20_error"], width, label="Best tested SUR", color="#D55E00")
    ax.bar(x + width, summary["random_q20_error"], width, label="Random", color="#999999")
    ax.set_xticks(x, summary["benchmark"])
    ax.set_ylabel("Final q20 error (lower is better)")
    ax.set_title("Synthetic evidence: the winner depends on benchmark geometry")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_method_schematic(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 3.8))
    ax.axis("off")
    nodes = [
        (0.10, "Inputs\nP, VX, LS, ST"),
        (0.34, "Binary GPC\nP(Keyhole | x)"),
        (0.59, "Acquisition\nuncertainty + repulsion"),
        (0.84, "Query one saved/new\nsimulator case"),
    ]
    for x, label in nodes:
        ax.text(x, 0.58, label, ha="center", va="center", fontsize=11, bbox=dict(boxstyle="round,pad=0.55", facecolor="#E8F1F8", edgecolor="#444444"), transform=ax.transAxes)
    for left, right in zip(nodes[:-1], nodes[1:]):
        ax.annotate("", xy=(right[0] - 0.10, 0.58), xytext=(left[0] + 0.10, 0.58), xycoords=ax.transAxes, arrowprops=dict(arrowstyle="->", lw=1.8))
    ax.annotate("Reveal manual has_keyhole only after query; refit and repeat", xy=(0.34, 0.25), xytext=(0.84, 0.25), xycoords=ax.transAxes, arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.25", lw=1.5), ha="center")
    ax.text(0.5, 0.92, "Final primary active level-set strategy", ha="center", fontsize=14, weight="bold", transform=ax.transAxes)
    ax.text(0.5, 0.05, "B1/B2/B3 are held-out evaluation diagnostics and never enter acquisition.", ha="center", fontsize=9, transform=ax.transAxes)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def generate_figures(
    curves: pd.DataFrame,
    improvement: pd.DataFrame,
    targets: pd.DataFrame,
    equivalent: pd.DataFrame,
    discovery: pd.DataFrame,
    calibration: pd.DataFrame,
    learning: pd.DataFrame,
    scorecard: pd.DataFrame,
    synthetic: pd.DataFrame,
) -> None:
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.labelsize": 10,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    plot_accuracy(curves, "B1", 20, FIG1 / "01_b1_q20_accuracy_vs_budget.png", "B1-q20 empirical near-boundary accuracy")
    plot_accuracy(curves, "B1", 30, FIG1 / "02_b1_q30_accuracy_vs_budget.png", "B1-q30 empirical boundary-region accuracy")
    plot_improvement(improvement, 20, FIG1 / "03_binary_minus_random_q20.png")
    plot_improvement(improvement, 30, FIG1 / "04_binary_minus_random_q30.png")
    plot_queries_to_target(targets, FIG1 / "05_queries_to_accuracy_target.png")
    plot_random_equivalent(equivalent, FIG1 / "06_random_equivalent_budget.png", savings=False)
    plot_random_equivalent(equivalent, FIG1 / "07_query_savings.png", savings=True)
    plot_discovery(discovery, FIG1 / "08_keyhole_discovery.png")
    plot_balanced_accuracy(learning, FIG1 / "09_balanced_accuracy.png")
    plot_reliability(calibration, FIG1 / "10_predictive_confidence_reliability.png")

    plot_evidence_chain(FIG2 / "01_full_thesis_evidence_chain.png")
    plot_accuracy(curves, "B1", 20, FIG2 / "02_final_b1_q20_sample_efficiency.png", "Final B1-q20 sample-efficiency curve")
    plot_accuracy(curves, "B1", 30, FIG2 / "03_final_b1_q30_sample_efficiency.png", "Final B1-q30 sample-efficiency curve")
    plot_queries_to_target(targets, FIG2 / "04_queries_to_target.png")
    plot_random_equivalent(equivalent, FIG2 / "05_random_equivalent_budget.png", savings=False)
    plot_discovery(discovery, FIG2 / "06_keyhole_discovery.png")
    plot_tradeoff(scorecard, FIG2 / "07_boundary_global_tradeoff.png")
    plot_scorecard(scorecard, FIG2 / "08_final_real_data_scorecard.png")
    plot_synthetic_summary(synthetic, FIG2 / "09_synthetic_to_real_summary.png")
    plot_method_schematic(FIG2 / "10_final_method_schematic.png")


def build_dataset_table(population: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for partition, group in population.groupby("partition", sort=True):
        rows.append(
            {
                "partition": partition,
                "simulations": len(group),
                "keyhole": int(group["has_keyhole"].sum()),
                "non_keyhole": int((~group["has_keyhole"]).sum()),
                "keyhole_prevalence": float(group["has_keyhole"].mean()),
            }
        )
    rows.append(
        {
            "partition": "TOTAL primary common population",
            "simulations": len(population),
            "keyhole": int(population["has_keyhole"].sum()),
            "non_keyhole": int((~population["has_keyhole"]).sum()),
            "keyhole_prevalence": float(population["has_keyhole"].mean()),
        }
    )
    return pd.DataFrame(rows)


def write_final_tables(
    population: pd.DataFrame,
    snapshots: dict[str, pd.DataFrame],
    targets: pd.DataFrame,
    equivalent: pd.DataFrame,
    scorecard: pd.DataFrame,
    ledger: pd.DataFrame,
) -> None:
    dataset = build_dataset_table(population)
    table2 = snapshots["B1"][snapshots["B1"]["budget"].isin(HEADLINE_BUDGETS)][
        [
            "budget",
            "method_label",
            "mean_q20_accuracy",
            "median_q20_accuracy",
            "mean_q30_accuracy",
            "median_q30_accuracy",
            "mean_balanced_accuracy",
            "mean_keyhole_discovered",
        ]
    ]
    table3 = targets[targets["boundary_definition"].eq("B1")][
        [
            "quantile",
            "target_accuracy_percent",
            "method_label",
            "successful_runs",
            "total_runs",
            "median_queries_successful_runs",
            "mean_queries_successful_runs",
            "iqr_queries_successful_runs",
            "not_reached_by_80",
        ]
    ]
    table4 = equivalent[
        [
            "binary_budget",
            "binary_mean_accuracy",
            "random_equivalent_budget_display",
            "query_saving_display",
            "efficiency_multiplier_display",
            "status",
        ]
    ]
    table5 = scorecard.copy()
    table6 = (
        ledger.groupby(["category", "status"], as_index=False)
        .agg(claim_count=("claim_id", "size"), claim_ids=("claim_id", lambda values: ", ".join(values)))
    )
    tables = [
        ("table1_final_dataset_population", "Table 1 — Final dataset and population", dataset, "Manual experiment-level has_keyhole remains the reference label."),
        ("table2_final_sample_efficiency_budget_snapshots", "Table 2 — Final B1 sample-efficiency budget snapshots", table2, "Accuracy is empirical held-out q20/q30 classification accuracy, not continuous-boundary certainty."),
        ("table3_queries_to_boundary_accuracy_targets", "Table 3 — Queries to boundary-accuracy targets", table3, "Medians condition on successful runs; failures remain explicit."),
        ("table4_random_equivalent_simulator_savings", "Table 4 — Random-equivalent simulator savings", table4, "No extrapolation beyond budget 80."),
        ("table5_final_real_data_method_scorecard", "Table 5 — Final real-data method scorecard", table5, "Binary is primary; Max-Depth is the secondary physical comparator."),
        ("table6_supported_claim_ledger_summary", "Table 6 — Supported-claim ledger summary", table6, "The full row-level ledger remains authoritative."),
    ]
    for stem, title, frame, note in tables:
        write_csv(TABLE2 / f"{stem}.csv", frame)
        save_markdown_table(TABLE2 / f"{stem}.md", title, frame, note)


def write_final_narratives(
    snapshots: dict[str, pd.DataFrame],
    targets: pd.DataFrame,
    equivalent: pd.DataFrame,
    scorecard: pd.DataFrame,
    synthetic: pd.DataFrame,
    confidence: pd.DataFrame,
) -> None:
    eq30 = equivalent[equivalent["binary_budget"].eq(30)].iloc[0]
    eq40 = equivalent[equivalent["binary_budget"].eq(40)].iloc[0]
    b40 = snapshot_value(snapshots, "B1", 40, M_BINARY, "mean_q20_accuracy")
    r40 = snapshot_value(snapshots, "B1", 40, M_RANDOM, "mean_q20_accuracy")
    b80 = snapshot_value(snapshots, "B1", 80, M_BINARY, "mean_q20_accuracy")
    conf80 = confidence[confidence["budget"].eq(80) & confidence["subset"].eq("B1_q20")].iloc[0]
    binary = scorecard[scorecard["method"].eq(M_BINARY)].iloc[0]
    random = scorecard[scorecard["method"].eq(M_RANDOM)].iloc[0]
    depth = scorecard[scorecard["method"].eq(M_DEPTH)].iloc[0]

    narrative = f"""# Final results narrative

## 1. From synthetic active level-set benchmarks to real data

The synthetic program established that acquisition rankings are geometry- and metric-dependent. At budget 80, uncertainty-repulsion was the best q20 method on thresholded Branin, Bernoulli-SUR-k25 was best on Hartmann4, and entropy/margin was best on the optional three-seed Ackley4 diagnostic. The source-backed comparison is preserved in `synthetic_to_real_summary.csv`. Consequently, the thesis does not claim a universal acquisition winner; it treats direct pointwise boundary methods as strong baselines and evaluates them with boundary-specific metrics.

## 2. Real-data audit and physical-response reconstruction

The final common population contains 405 simulations: 73 manually labelled Keyhole and 332 non-Keyhole. All Week 8 results reuse the exact saved population and Phase 6/7 split hashes. No source label, target, physical monitor, or simulator output was changed.

## 3. Predictability of physical responses

Earlier response-modelling phases showed that maximum penetration depth is a strong continuous response and a useful classifier-side comparator. Week 8 does not refit those models; it carries forward the saved Phase 6 Max-Depth GPR and its exact query trajectory.

## 4. Physical responses and manual Keyhole morphology

Manual `has_keyhole` labels encode the presence of cavity-like Keyhole morphology in at least one valid saved frame. Continuous responses are associated with that annotation but do not redefine it. G3 achieved perfect new-data ranking and leave-one-out separation, while its transfer performance and threshold shifted by partition; maximum depth was more robust as a scalar companion.

## 5. Why G3 was not promoted to a universal boundary definition

Perfect separation within new-data is not a universal physical threshold. Phase 5.5 retained a worst predeclared G3 transfer balanced accuracy of 0.8125 and explicitly classified the threshold as partition-sensitive. The thesis therefore preserves manual `has_keyhole` ground truth and avoids a universal G3 cutoff claim.

## 6. Binary versus Max-Depth active learning

Across the common 16–80 budget grid, Binary has B1-q20 accuracy AULC {binary['mean_B1_q20_accuracy_aulc']:.4f}, Random {random['mean_B1_q20_accuracy_aulc']:.4f}, and Max-Depth {depth['mean_B1_q20_accuracy_aulc']:.4f}. Max-Depth retains the strongest global balanced-accuracy AULC ({depth['mean_balanced_accuracy_aulc']:.4f} versus Binary {binary['mean_balanced_accuracy_aulc']:.4f}), making it scientifically useful as a secondary comparator rather than the primary boundary acquisition.

## 7. Hybrid negative result

Phase 7 tested two fixed ways to inject queried maximum-depth side information: a binary gate and equal-rank fusion. Neither met the preregistered robust success rule. This supports the narrow conclusion that these two Hybrids did not improve Binary; it does not prove that every conceivable hybrid is ineffective.

## 8. Final sample-efficiency result

At 40 total queries, Binary achieves {b40:.1%} mean B1-q20 empirical near-boundary accuracy, compared with {r40:.1%} for Random. At budget 80 Binary retains {b80:.1%}. These are held-out classification accuracies on empirical boundary-like subsets, not probabilities that the continuous physical boundary lies at a known location.

## 9. Concrete simulator-query savings

Binary's mean {eq30['binary_mean_accuracy']:.1%} B1-q20 accuracy at budget 30 is first matched by the observed Random mean curve at about {eq30['random_equivalent_budget']:.0f} queries. This corresponds to approximately {eq30['query_saving']:.0f} saved simulator calls and a {eq30['efficiency_multiplier']:.2f}x query equivalent. Binary's budget-40 performance is not matched by Random by budget 80, so only a strict >40 saving and >2.00x lower-bound statement is defensible; no value above 80 is extrapolated.

## 10. Final recommended strategy

The final primary strategy is a Binary Gaussian Process Classifier mapping `(P, VX, LS, ST)` to `P(Keyhole)`, with binary uncertainty-repulsion acquisition. `ST` is substrate temperature. Maximum depth remains a physical side variable and separate continuous comparator.

## 11. Limitations

No genuinely new simulator evaluation was run in Week 8. This is an offline retrospective active-learning benchmark. The 20 outer runs are four repeated five-fold splits of the same 405 simulations, not 20 independent physical campaigns. Saved GPC probabilities permit model-confidence diagnostics—for example, at budget 80, {conf80['fraction_confidence_ge_080']:.1%} of pooled B1-q20 predictions have at least 80% model confidence—but the probabilities were not post-hoc calibrated and do not quantify physical-boundary certainty. B1/B2/B3 depend on sampled points and are not the true continuous boundary. Associations are not causal.

## 12. What future prospective validation would require

A prospective study would freeze this method and its hyperparameters, start from a declared initial design, request genuinely new simulator evaluations sequentially, keep future outcomes unavailable until each query completes, and compare against a concurrently budget-matched random policy. That experiment was not available in Week 8 and is not implied by the present results.
"""
    (OUT2 / "final_results_narrative.md").write_text(narrative, encoding="utf-8")

    budget_rows = []
    for budget in [20, 30, 40, 60, 80]:
        budget_rows.append(
            {
                "Bütçe": budget,
                "Binary q20": f"{snapshot_value(snapshots, 'B1', budget, M_BINARY, 'mean_q20_accuracy'):.1%}",
                "Random q20": f"{snapshot_value(snapshots, 'B1', budget, M_RANDOM, 'mean_q20_accuracy'):.1%}",
                "Binary q30": f"{snapshot_value(snapshots, 'B1', budget, M_BINARY, 'mean_q30_accuracy'):.1%}",
                "Random q30": f"{snapshot_value(snapshots, 'B1', budget, M_RANDOM, 'mean_q30_accuracy'):.1%}",
            }
        )
    all_target_rows = []
    for quantile in QUANTILES:
        for target in TARGETS:
            all_target_rows.append(
                {
                    "Bölge": f"q{quantile}",
                    "Hedef": f"{target:.0%}",
                    "Binary": target_display(lookup_target(targets, M_BINARY, quantile, target)),
                    "Random": target_display(lookup_target(targets, M_RANDOM, quantile, target)),
                    "Max-Depth": target_display(lookup_target(targets, M_DEPTH, quantile, target)),
                }
            )
    savings_rows = []
    for row in equivalent.itertuples(index=False):
        savings_rows.append(
            {
                "Binary bütçe": row.binary_budget,
                "Binary q20": f"{row.binary_mean_accuracy:.1%}",
                "Random-eşdeğer": row.random_equivalent_budget_display,
                "Tasarruf": row.query_saving_display,
                "Çarpan": row.efficiency_multiplier_display,
            }
        )
    final_tr = f"""# Week 8 final — sade Türkçe tez özeti

Bu Week 8 çalışmasında **yeni simülasyon çalıştırılmadı**. Bütün sayılar, daha önce kaydedilmiş 405 simülasyonun sonuçları sorgulanana kadar öğreniciden gizlenerek yapılan offline/retrospektif değerlendirmeden gelir.

## 1. Tez aslında ne yapmaya çalışıyor?

Amaç, pahalı eriyik-havuzu simülasyonlarını mümkün olduğunca az çağırarak manuel Keyhole/non-Keyhole geçiş bölgesini öğrenmek. Öğrenici her adımda hangi simülasyonun sonucunu görmesi gerektiğini seçiyor; başarısı, daha önce görmediği held-out simülasyonlarda ölçülüyor.

## 2. Final model nedir?

Final model bir **Binary Gaussian Process Classifier (GPC)**. Girdiler `P`, `VX`, `LS`, `ST`; çıktı `P(Keyhole)`. `ST`, **substrate temperature** demektir, katman kalınlığı değildir.

## 3. Final acquisition function nedir?

**binary_uncertainty_repulsion**. Model, Keyhole olasılığının 0.5'e yakın olduğu belirsiz noktaları tercih eder; repulsion terimi aynı yere yığılmayı azaltır.

## 4. q20/q30 nedir?

B1-q20, manuel etiketi zıt olan örneğe girdi uzayında en yakın yaklaşık %20'lik test kümesidir; q30 daha geniş yaklaşık %30'luk bölgedir. Bunlar ampirik sınır tanılarıdır, gerçek sürekli fiziksel sınır değildir.

## 5. İstenen doğruluk için kaç simülasyon gerekiyor?

Hücreler **başarılı koşulardaki medyan ilk sorgu (başarı/20)** biçimindedir. “Başarısız” koşular 81 diye uydurulmadı.

{df_to_markdown(pd.DataFrame(all_target_rows))}

## 6. Binary, Random'a göre kaç çağrı tasarruf ediyor?

{df_to_markdown(pd.DataFrame(savings_rows))}

En güçlü tam sayısal sonuç: Binary'nin 30 sorguda ulaştığı **{eq30['binary_mean_accuracy']:.1%} B1-q20 doğruluğunu** Random yaklaşık **{eq30['random_equivalent_budget']:.0f} sorguda** yakalıyor; yaklaşık **{eq30['query_saving']:.0f} simülasyon çağrısı** tasarruf ediliyor. Binary'nin 40 sorgudaki seviyesi Random tarafından 80'e kadar yakalanmadığı için burada sonuç **>40** tasarruf alt sınırıdır.

## 7. 20/30/40/60/80 bütçelerinde sınır-bölgesi doğruluğu nedir?

{df_to_markdown(pd.DataFrame(budget_rows))}

## 8. “%80 boundary certainty” diyebilir miyiz?

Hayır. “Bütçe 40'ta ortalama B1-q20 held-out doğruluğu {b40:.1%}” diyebiliriz. Ayrıca saklanmış olasılıklar sayesinde “bütçe 40'ta B1-q20 tahminlerinin {confidence[(confidence['budget']==40)&(confidence['subset']=='B1_q20')].iloc[0]['fraction_confidence_ge_080']:.1%}'i en az %80 **model güveni** taşıyor” diyebiliriz. Fakat bu, fiziksel sınırın konumunu %80 kesinlikle bildiğimiz anlamına gelmez.

## 9. Max-Depth hâlâ ne katıyor?

Max-Depth global balanced accuracy AULC'sinde daha güçlü: **{depth['mean_balanced_accuracy_aulc']:.4f}**, Binary **{binary['mean_balanced_accuracy_aulc']:.4f}**. Bu nedenle fiziksel yorum ve genel sınıflandırma için değerli bir ikincil karşılaştırıcıdır; final sınır acquisition'ı değildir.

## 10. Hybrid neden başarısız oldu?

Gate ve eşit-rank Fusion, sorgulanan Max-Depth bilgisini kullandı ama Binary'yi B1/B2/B3 hiyerarşisinde sağlam biçimde geçemedi ve ek hesap maliyeti getirdi. Sonuç yalnızca test edilen iki sabit Hybrid için geçerlidir.

## 11. Final tez sonucu nedir?

Final öneri **Binary GPC + uncertainty-repulsion**. Bu yöntem, aynı 20 eşlenmiş offline koşuda Random'dan daha iyi ampirik sınır doğruluğu ve somut sorgu tasarrufu sağlıyor. Max-Depth ikincil fiziksel karşılaştırıcıdır. Sonuç canlı/prospektif doğrulama değil; aynı 405 kayıtlı simülasyon üzerinde tekrarlı held-out değerlendirmedir. Evrensel G3/Max-Depth eşiği, nedensellik, gerçek sürekli sınırın kesin konumu veya her problemde evrensel üstünlük iddia edilemez.
"""
    (OUT2 / "week8_final_plain_language_tr.md").write_text(final_tr, encoding="utf-8")


def initial_runtime_payload(phase: str, wall_seconds: float, extra: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": phase,
        "timestamp_utc": utc_now(),
        "wall_seconds_analysis_and_reporting": wall_seconds,
        "python_executable": sys.executable,
        "new_simulator_runs": False,
        "expensive_week1_7_experiments_rerun": False,
        "new_model_fit": False,
        "new_acquisition": False,
        "saved_artifacts_only": True,
        **extra,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    started = time.perf_counter()
    for directory in [OUT1, OUT2, FIG1, FIG2, TABLE2]:
        directory.mkdir(parents=True, exist_ok=True)

    audit, tables = source_audit()
    tables = validate_and_prepare_sources(tables)
    write_preflight(audit, tables)

    discovery_run, discovery = compute_discovery(tables)
    curves, improvement = compute_learning_curves(tables["learning"])
    snapshots = compute_budget_snapshots(tables["learning"], discovery_run)
    first_run, first_summary, persistent_run, persistent_summary = compute_crossings(tables["learning"])
    compute_matched_savings(first_run)
    equivalent = compute_random_equivalent(tables["learning"])
    _, confidence, calibration = compute_predictive_confidence(tables["predictions"])
    scorecard = compute_real_scorecard(tables, first_summary)
    synthetic = compute_synthetic_summary(tables["synthetic"])
    ledger = build_claim_ledger(scorecard, equivalent, confidence)
    write_headlines_and_phase1_text(
        snapshots, first_summary, equivalent, discovery, confidence, scorecard
    )
    write_final_tables(tables["population"], snapshots, first_summary, equivalent, scorecard, ledger)
    write_final_narratives(snapshots, first_summary, equivalent, scorecard, synthetic, confidence)
    generate_figures(
        curves,
        improvement,
        first_summary,
        equivalent,
        discovery,
        calibration,
        tables["learning"],
        scorecard,
        synthetic,
    )

    elapsed = time.perf_counter() - started
    write_json(
        OUT1 / "runtime_summary.json",
        initial_runtime_payload(
            "Week 8 Phase 1",
            elapsed,
            {
                "source_outer_runs": 20,
                "source_population": 405,
                "common_budget_grid": [COMMON_START, FINAL_BUDGET],
                "budget_snapshots": list(SNAPSHOT_BUDGETS),
                "confidence_analysis_available": True,
                "confidence_budgets": list(CONFIDENCE_BUDGETS),
                "phase1_figure_count": len(list(FIG1.glob("*.png"))),
                "validation_pending_independent_validator": True,
            },
        ),
    )
    write_json(
        OUT2 / "runtime_summary.json",
        initial_runtime_payload(
            "Week 8 Phase 2",
            elapsed,
            {
                "synthetic_benchmarks_reused": ["Branin", "Hartmann4", "Ackley4 optional"],
                "final_figure_count": len(list(FIG2.glob("*.png"))),
                "final_table_csv_count": len(list(TABLE2.glob("*.csv"))),
                "claim_ledger_rows": len(ledger),
                "validation_pending_independent_validator": True,
            },
        ),
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "phase7_parent": EXPECTED_PARENT,
                "phase1_output": str(OUT1),
                "phase2_output": str(OUT2),
                "new_simulator_runs": False,
                "expensive_benchmark_rerun": False,
                "wall_seconds": elapsed,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
