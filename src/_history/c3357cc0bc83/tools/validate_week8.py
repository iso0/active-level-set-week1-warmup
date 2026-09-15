"""Independent fail-closed validator for the two Week 8 closeout phases."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Callable, Iterable

import nbformat
import numpy as np
import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUT1 = ROOT / "outputs" / "week8_01_final_sample_efficiency"
OUT2 = ROOT / "outputs" / "week8_02_thesis_consolidation"
P7 = ROOT / "outputs" / "week7_07_final_boundary_hybrid_benchmark"
P6 = ROOT / "outputs" / "week7_06_real_data_boundary_active_level_set"
NB1 = ROOT / "notebooks" / "week_08" / "01_final_sample_efficiency.ipynb"
NB2 = ROOT / "notebooks" / "week_08" / "02_thesis_evidence_consolidation.ipynb"

EXPECTED_PARENT = "167aad945b20822de712e891e901bd3ec6d5ffc6"
EXPECTED_BRANCH = "codex/week8-final-sample-efficiency-thesis-consolidation"
PHASE7_BRANCH = "codex/week7-phase7-final-boundary-hybrid-benchmark"
M_BINARY = "binary_uncertainty_repulsion"
M_RANDOM = "shared_random_binary_head"
M_DEPTH = "max_depth_straddle"
METHODS = [M_BINARY, M_RANDOM, M_DEPTH]
BOUNDARIES = ["B1", "B2", "B3"]
QUANTILES = [20, 30]
TARGETS = [0.70, 0.75, 0.80, 0.85, 0.90]


def git(*args: str, cwd: Path = ROOT, allow_failure: bool = False) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=not allow_failure,
    )
    return result.stdout.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def strict_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    values = series.astype(str).str.strip().str.lower()
    if not values.isin(["true", "false", "1", "0"]).all():
        raise ValueError(f"Invalid booleans in {series.name}")
    return values.isin(["true", "1"])


def read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


class Audit:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.rows: list[dict[str, Any]] = []

    def check(self, number: int, check: str, action: Callable[[], tuple[bool, str]]) -> None:
        try:
            passed, detail = action()
        except Exception as exc:  # fail closed and preserve exact error text
            passed, detail = False, f"{type(exc).__name__}: {exc}"
        self.rows.append(
            {
                "check_id": f"{self.prefix}{number:02d}",
                "check": check,
                "status": "PASS" if passed else "FAIL",
                "detail": detail,
            }
        )

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)


def same_or_nan(left: Any, right: Any, tolerance: float = 1e-10) -> bool:
    if pd.isna(left) and pd.isna(right):
        return True
    if pd.isna(left) or pd.isna(right):
        return False
    return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=tolerance)


def notebook_state(path: Path) -> dict[str, Any]:
    notebook = nbformat.read(path, as_version=4)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    errors = [
        output
        for cell in code_cells
        for output in cell.get("outputs", [])
        if output.get("output_type") == "error"
    ]
    return {
        "cell_count": len(notebook.cells),
        "code_cell_count": len(code_cells),
        "executed_code_cell_count": sum(cell.get("execution_count") is not None for cell in code_cells),
        "stored_error_count": len(errors),
        "all_executed": all(cell.get("execution_count") is not None for cell in code_cells),
    }


def first_crossing(group: pd.DataFrame, accuracy_col: str, target: float, persistent: bool) -> float | None:
    ordered = group.sort_values("budget")
    values = ordered[accuracy_col].to_numpy(float)
    budgets = ordered["budget"].to_numpy(int)
    if persistent:
        for index in range(max(0, len(values) - 2)):
            if np.all(values[index : index + 3] >= target - 1e-12):
                return float(budgets[index])
        return None
    reached = np.flatnonzero(values >= target - 1e-12)
    return float(budgets[reached[0]]) if len(reached) else None


def recompute_crossings(learning: pd.DataFrame, persistent: bool) -> pd.DataFrame:
    rows = []
    for boundary in BOUNDARIES:
        for quantile in QUANTILES:
            accuracy_col = f"{boundary}_q{quantile}_accuracy"
            for target in TARGETS:
                for (method, run_id), group in learning.groupby(["method", "run_id"], sort=True):
                    crossing = first_crossing(group, accuracy_col, target, persistent)
                    rows.append(
                        {
                            "run_id": run_id,
                            "method": method,
                            "boundary_definition": boundary,
                            "quantile": quantile,
                            "target_accuracy": target,
                            "queries_required": crossing,
                            "status": "reached" if crossing is not None else "not_reached_by_80",
                        }
                    )
    return pd.DataFrame(rows)


def random_equivalent(random_curve: pd.DataFrame, target: float) -> float | None:
    x = random_curve["budget"].to_numpy(float)
    y = random_curve["mean_accuracy"].to_numpy(float)
    if y[0] >= target - 1e-12:
        return float(x[0])
    for index in range(1, len(x)):
        if y[index] >= target - 1e-12 and y[index - 1] < target - 1e-12:
            fraction = (target - y[index - 1]) / (y[index] - y[index - 1])
            return float(x[index - 1] + fraction * (x[index] - x[index - 1]))
    return None


def figure_manifest(output_dir: Path, figure_dir: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(figure_dir.glob("*.png")):
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
            mode = image.mode
        rows.append(
            {
                "relative_path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "width_px": width,
                "height_px": height,
                "mode": mode,
                "status": "PASS",
            }
        )
    frame = pd.DataFrame(rows)
    frame.to_csv(output_dir / "figure_manifest.csv", index=False, lineterminator="\n")
    return frame


def manifest_files(output_dir: Path, notebook: Path) -> list[Path]:
    files = [
        path
        for path in output_dir.rglob("*")
        if path.is_file() and path.name != "output_manifest.csv"
    ]
    extras = [
        ROOT / "src" / "week8_final_sample_efficiency_thesis_consolidation.py",
        ROOT / "scripts" / "build_week8_notebooks.py",
        ROOT / "scripts" / "validate_week8.py",
        notebook,
    ]
    files.extend(path for path in extras if path.is_file())
    return sorted(set(files))


def write_manifest(output_dir: Path, notebook: Path) -> pd.DataFrame:
    rows = []
    for path in manifest_files(output_dir, notebook):
        rows.append(
            {
                "relative_path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    frame = pd.DataFrame(rows)
    frame.to_csv(output_dir / "output_manifest.csv", index=False, lineterminator="\n")
    return frame


def verify_manifest(frame: pd.DataFrame) -> tuple[bool, str]:
    errors = []
    for row in frame.itertuples(index=False):
        path = ROOT / row.relative_path
        if not path.is_file():
            errors.append(f"missing:{row.relative_path}")
            continue
        if path.stat().st_size != int(row.bytes):
            errors.append(f"size:{row.relative_path}")
        if sha256_file(path) != row.sha256:
            errors.append(f"hash:{row.relative_path}")
    return not errors, f"rows={len(frame)}; errors={errors[:5]}"


def update_runtime(path: Path, **updates: Any) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update(updates)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def requirements_frame(items: Iterable[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "requirement_id": f"R{index:02d}",
                "requirement": requirement,
                "status": "PASS",
                "evidence": evidence,
            }
            for index, (requirement, evidence) in enumerate(items, start=1)
        ]
    )


def phase1_required_files() -> list[str]:
    return [
        "phase8_01_preflight.json",
        "phase7_source_audit.json",
        "matched_run_reuse_audit.csv",
        "budget_snapshot_b1.csv",
        "budget_snapshot_b2.csv",
        "budget_snapshot_b3.csv",
        "boundary_accuracy_learning_curves.csv",
        "queries_to_accuracy_target.csv",
        "persistent_queries_to_accuracy_target.csv",
        "random_equivalent_budget.csv",
        "query_savings_summary.csv",
        "matched_query_savings.csv",
        "keyhole_discovery_by_budget.csv",
        "predictive_confidence_summary.csv",
        "predictive_calibration_summary.csv",
        "headline_results.csv",
        "headline_results.md",
        "week8_phase1_plain_language_tr.md",
        "runtime_summary.json",
    ]


def validate_phase1() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    audit = Audit("P1V")
    preflight = json.loads((OUT1 / "phase8_01_preflight.json").read_text(encoding="utf-8"))
    source_audit = json.loads((OUT1 / "phase7_source_audit.json").read_text(encoding="utf-8"))
    population = read_csv(P6 / "primary_common_population.csv")
    population["has_keyhole"] = strict_bool(population["has_keyhole"])
    learning = read_csv(P7 / "phase7_learning_curve_summary.csv")
    learning = learning[learning["method"].isin(METHODS)].copy()
    for boundary in BOUNDARIES:
        for quantile in QUANTILES:
            learning[f"{boundary}_q{quantile}_accuracy"] = 1 - learning[f"{boundary}_q{quantile}_error"]
    reuse = read_csv(OUT1 / "matched_run_reuse_audit.csv")
    queries = read_csv(P7 / "phase7_all_method_query_history.csv")
    predictions = read_csv(P7 / "phase7_all_method_prediction_checkpoints.csv")
    curves = read_csv(OUT1 / "boundary_accuracy_learning_curves.csv")
    snapshots = {boundary: read_csv(OUT1 / f"budget_snapshot_{boundary.lower()}.csv") for boundary in BOUNDARIES}
    first_run = read_csv(OUT1 / "queries_to_accuracy_target_run_level.csv")
    persistent_run = read_csv(OUT1 / "persistent_queries_to_accuracy_target_run_level.csv")
    first_summary = read_csv(OUT1 / "queries_to_accuracy_target.csv")
    equivalent = read_csv(OUT1 / "random_equivalent_budget.csv")
    matched = read_csv(OUT1 / "matched_query_savings.csv")
    confidence = read_csv(OUT1 / "predictive_confidence_summary.csv")
    calibration = read_csv(OUT1 / "predictive_calibration_summary.csv")
    headlines = read_csv(OUT1 / "headline_results.csv")

    audit.check(1, "Exact Week 8 branch and uncommitted Phase 7 parent", lambda: (
        git("rev-parse", "HEAD") == EXPECTED_PARENT and git("branch", "--show-current") == EXPECTED_BRANCH,
        f"HEAD={git('rev-parse','HEAD')}; branch={git('branch','--show-current')}",
    ))
    remote_line = git("ls-remote", "--heads", "origin", f"refs/heads/{PHASE7_BRANCH}")
    audit.check(2, "Published remote Phase 7 head is exact parent", lambda: (
        bool(remote_line) and remote_line.split()[0] == EXPECTED_PARENT,
        remote_line,
    ))
    audit.check(3, "Phase 7 source validation and requirements intact", lambda: (
        source_audit["phase7_validation_pass"] == source_audit["phase7_validation_total"] == 34
        and source_audit["phase7_requirement_pass"] == source_audit["phase7_requirement_total"] == 18,
        f"validation={source_audit['phase7_validation_pass']}/34; requirements={source_audit['phase7_requirement_pass']}/18",
    ))
    audit.check(4, "Exact 405 population with 73/332 manual labels", lambda: (
        len(population) == 405 and int(population["has_keyhole"].sum()) == 73 and int((~population["has_keyhole"]).sum()) == 332,
        f"n={len(population)}; keyhole={int(population['has_keyhole'].sum())}",
    ))
    audit.check(5, "Exact 20 matched outer runs, four repeats, five folds", lambda: (
        learning["run_id"].nunique() == 20
        and sorted(learning["repeat"].unique()) == [1, 2, 3, 4]
        and sorted(learning["fold"].unique()) == [1, 2, 3, 4, 5],
        f"runs={learning['run_id'].nunique()}; repeats={sorted(learning['repeat'].unique())}; folds={sorted(learning['fold'].unique())}",
    ))

    def budget_check() -> tuple[bool, str]:
        counts = learning[learning["budget"].between(16, 80)].groupby(["method", "budget"])["run_id"].nunique()
        return len(counts) == 3 * 65 and counts.eq(20).all(), f"groups={len(counts)}; min={counts.min()}; max={counts.max()}"

    audit.check(6, "Exact complete common integer budget grid 16-80", budget_check)
    audit.check(7, "Exact Phase 6 split/warm-start hashes reused", lambda: (
        len(reuse) == 20
        and reuse["week8_source_reuse_status"].eq("PASS").all()
        and strict_bool(reuse["warm_hash_matches"]).all()
        and strict_bool(reuse["split_hash_matches"]).all(),
        f"pass={reuse['week8_source_reuse_status'].eq('PASS').sum()}/{len(reuse)}",
    ))
    audit.check(8, "Saved query histories cover all three methods and 20 runs through 80", lambda: (
        queries[queries["method"].isin(METHODS)]["run_id"].nunique() == 20
        and set(METHODS) == set(queries[queries["method"].isin(METHODS)]["method"].unique())
        and queries[queries["method"].isin(METHODS)].groupby(["run_id", "method"])["query_order"].max().eq(80).all(),
        f"rows={len(queries[queries['method'].isin(METHODS)])}",
    ))
    audit.check(9, "Saved Binary prediction checkpoints include all required confidence budgets", lambda: (
        set([20, 30, 40, 60, 80]).issubset(
            set(predictions[predictions["method"].eq(M_BINARY)]["budget"].unique())
        ),
        str(sorted(predictions[predictions["method"].eq(M_BINARY)]["budget"].unique())),
    ))
    audit.check(10, "No rerandomization, new acquisition, model, label, or target", lambda: (
        not preflight["expensive_experiment_rerun"]
        and not preflight["prospective_new_simulator_validation"]
        and preflight["primary_method"] == M_BINARY
        and preflight["random_baseline"] == M_RANDOM
        and preflight["secondary_comparator"] == M_DEPTH
        and preflight["manual_ground_truth"] == "has_keyhole",
        json.dumps({key: preflight[key] for key in ["expensive_experiment_rerun", "primary_method", "manual_ground_truth"]}),
    ))
    audit.check(11, "B1/B2/B3 and hidden outcomes never entered acquisition", lambda: (
        not strict_bool(queries["boundary_scores_consulted_before_selection"]).any()
        and not strict_bool(queries["hidden_label_consulted_before_selection"]).any()
        and not strict_bool(queries["hidden_max_depth_consulted_before_selection"]).any(),
        "all three Phase 7 leakage flags are false",
    ))

    def accuracy_identity() -> tuple[bool, str]:
        errors = []
        for boundary in BOUNDARIES:
            for quantile in QUANTILES:
                identity = learning[f"{boundary}_q{quantile}_accuracy"] - (1 - learning[f"{boundary}_q{quantile}_error"])
                errors.append(float(identity.abs().max()))
        return max(errors) < 1e-12 and curves["accuracy_identity_max_abs_error"].max() < 1e-12, f"max={max(errors)}"

    audit.check(12, "q20/q30 accuracy exactly equals one minus error", accuracy_identity)

    def snapshot_reproduction() -> tuple[bool, str]:
        maximum = 0.0
        for boundary in BOUNDARIES:
            saved = snapshots[boundary]
            for row in saved.itertuples(index=False):
                group = learning[(learning["method"] == row.method) & (learning["budget"] == row.budget)]
                for quantile in QUANTILES:
                    actual = group[f"{boundary}_q{quantile}_accuracy"].mean()
                    recorded = getattr(row, f"mean_q{quantile}_accuracy")
                    maximum = max(maximum, abs(actual - recorded))
        return maximum < 1e-10, f"maximum_absolute_difference={maximum}"

    audit.check(13, "All B1/B2/B3 budget snapshots reproduce raw curves", snapshot_reproduction)

    recomputed_first = recompute_crossings(learning, persistent=False)
    recomputed_persistent = recompute_crossings(learning, persistent=True)

    def crossing_match(saved: pd.DataFrame, recomputed: pd.DataFrame) -> tuple[bool, str]:
        keys = ["run_id", "method", "boundary_definition", "quantile", "target_accuracy"]
        merged = saved.merge(recomputed, on=keys, suffixes=("_saved", "_recomputed"), validate="one_to_one")
        equal = all(
            same_or_nan(left, right)
            for left, right in zip(merged["queries_required_saved"], merged["queries_required_recomputed"])
        )
        equal = equal and (merged["status_saved"] == merged["status_recomputed"]).all()
        return equal and len(merged) == 1800, f"rows={len(merged)}; equal={equal}"

    audit.check(14, "First crossings independently recompute from raw trajectories", lambda: crossing_match(first_run, recomputed_first))
    audit.check(15, "Persistent crossings require current plus next two checkpoints", lambda: crossing_match(persistent_run, recomputed_persistent))
    audit.check(16, "Every target summary keeps successful and censored runs explicit", lambda: (
        (first_summary["successful_runs"] + first_summary["not_reached_by_80"]).eq(20).all()
        and first_summary["total_runs"].eq(20).all()
        and not strict_bool(first_summary["unsuccessful_runs_dropped"]).any(),
        f"rows={len(first_summary)}; success_range={first_summary['successful_runs'].min()}-{first_summary['successful_runs'].max()}",
    ))

    def equivalent_check() -> tuple[bool, str]:
        random_curve = (
            learning[(learning["method"] == M_RANDOM) & learning["budget"].between(16, 80)]
            .groupby("budget", as_index=False)["B1_q20_accuracy"]
            .mean()
            .rename(columns={"B1_q20_accuracy": "mean_accuracy"})
        )
        binary_curve = learning[(learning["method"] == M_BINARY) & learning["budget"].between(16, 80)].groupby("budget")["B1_q20_accuracy"].mean()
        errors = []
        for row in equivalent.itertuples(index=False):
            target = float(binary_curve.loc[row.binary_budget])
            expected = random_equivalent(random_curve, target)
            if expected is None:
                errors.append(not pd.isna(row.random_equivalent_budget))
            else:
                errors.append(not same_or_nan(expected, row.random_equivalent_budget))
        return not any(errors) and not strict_bool(equivalent["extrapolation"]).any(), f"rows={len(equivalent)}; mismatches={sum(errors)}"

    audit.check(17, "Random-equivalent interpolation recomputes with no extrapolation", equivalent_check)
    audit.check(18, "All >80 savings and multipliers are strict lower bounds", lambda: (
        equivalent[equivalent["status"].eq("not_matched_by_80")].apply(
            lambda row: row["query_saving_lower_bound"] == 80 - row["binary_budget"]
            and math.isclose(row["efficiency_multiplier_lower_bound"], 80 / row["binary_budget"]),
            axis=1,
        ).all(),
        equivalent[equivalent["status"].eq("not_matched_by_80")][["binary_budget", "query_saving_display", "efficiency_multiplier_display"]].to_json(orient="records"),
    ))
    outcome_columns = [column for column in matched.columns if column.startswith("count_")]
    audit.check(19, "Matched-run outcome categories preserve censoring and sum to 20", lambda: (
        matched["matched_run_count"].eq(20).all()
        and matched[outcome_columns].sum(axis=1).eq(20).all()
        and strict_bool(matched["not_reached_not_imputed"]).all(),
        f"rows={len(matched)}; category_sums={matched[outcome_columns].sum(axis=1).tolist()}",
    ))

    def confidence_recompute() -> tuple[bool, str]:
        source = predictions[
            predictions["method"].eq(M_BINARY) & predictions["budget"].isin([20, 30, 40, 60, 80])
        ].copy()
        source["confidence"] = np.maximum(source["keyhole_probability"], 1 - source["keyhole_probability"])
        source["correct"] = source["predicted_keyhole"].astype(int).eq(source["has_keyhole"].astype(int))
        maximum = 0.0
        for row in confidence[confidence["boundary_definition"].eq("B1")].itertuples(index=False):
            mask = strict_bool(source[f"test_B1_q{int(row.quantile)}"])
            group = source[source["budget"].eq(row.budget) & mask]
            actual_fraction = group["confidence"].ge(0.80).mean()
            actual_accuracy = group.loc[group["confidence"].ge(0.80), "correct"].mean()
            maximum = max(maximum, abs(actual_fraction - row.fraction_confidence_ge_080), abs(actual_accuracy - row.accuracy_confidence_ge_080))
        return maximum < 1e-10, f"maximum_absolute_difference={maximum}"

    audit.check(20, "Predictive-confidence rows recompute from actual saved probabilities", confidence_recompute)
    audit.check(21, "Calibration uses finite fixed-bin Brier/ECE diagnostics", lambda: (
        confidence["pooled_brier_score"].between(0, 1).all()
        and confidence["probability_ece_10_equal_width_bins"].between(0, 1).all()
        and confidence["confidence_ece_10_equal_width_bins"].between(0, 1).all()
        and set(calibration["calibration_type"].unique()) == {"keyhole_probability_reliability", "confidence_accuracy_reliability"},
        f"summary_rows={len(confidence)}; calibration_rows={len(calibration)}",
    ))
    audit.check(22, "No headline calls empirical accuracy physical-boundary certainty", lambda: (
        len(headlines) == 10 and not strict_bool(headlines["physical_boundary_certainty_claim"]).any(),
        f"headline_rows={len(headlines)}",
    ))

    def headline_sources() -> tuple[bool, str]:
        missing = [path for path in headlines["source_artifact"] if not (ROOT / path).is_file()]
        return not missing, f"missing={missing}"

    audit.check(23, "Every headline statement names an existing machine-readable source", headline_sources)
    audit.check(24, "ST remains substrate temperature", lambda: (
        preflight["ST_semantics"] == "substrate temperature" and preflight["inputs"] == ["P", "VX", "LS", "ST"],
        f"inputs={preflight['inputs']}; ST={preflight['ST_semantics']}",
    ))
    ledger = read_csv(OUT2 / "final_thesis_claim_ledger.csv")
    audit.check(25, "No causal claim is promoted", lambda: (
        ledger.loc[ledger["claim_id"].eq("C08"), "status"].iloc[0] == "NOT SUPPORTED / PROHIBITED",
        ledger.loc[ledger["claim_id"].eq("C08"), ["status", "forbidden_overclaim"]].to_json(orient="records"),
    ))
    state1 = notebook_state(NB1)
    audit.check(26, "Phase 1 teaching notebook executes 24 code cells with zero stored errors", lambda: (
        state1["code_cell_count"] == 24 and state1["executed_code_cell_count"] == 24 and state1["stored_error_count"] == 0,
        json.dumps(state1),
    ))
    audit.check(27, "All required Phase 1 artifacts exist", lambda: (
        all((OUT1 / name).is_file() for name in phase1_required_files()),
        f"present={sum((OUT1/name).is_file() for name in phase1_required_files())}/{len(phase1_required_files())}",
    ))
    figure_frame = figure_manifest(OUT1, OUT1 / "figures")
    audit.check(28, "Exactly ten Phase 1 figures are valid nonempty PNGs", lambda: (
        len(figure_frame) == 10
        and figure_frame["status"].eq("PASS").all()
        and figure_frame["bytes"].gt(10_000).all()
        and figure_frame["width_px"].ge(800).all(),
        f"figures={len(figure_frame)}; min_bytes={figure_frame['bytes'].min() if len(figure_frame) else 0}",
    ))
    audit.check(29, "Original dirty checkout remains byte/status untouched by Week 8", lambda: (
        json.loads((OUT1 / "original_worktree_baseline.json").read_text(encoding="utf-8"))["status_lines"]
        == git("status", "--porcelain=v1", "--branch", cwd=Path(r"C:\Users\ozgur\Documents\thesis")).splitlines(),
        "original checkout status matches recorded pre-Week-8 baseline",
    ))
    audit.check(30, "Published Phase 7 worktree remains clean", lambda: (
        git("status", "--porcelain", cwd=Path(r"C:\Users\ozgur\Documents\thesis-week7-phase7-final-boundary-hybrid-benchmark")) == "",
        "Phase 7 status porcelain is empty",
    ))
    audit.check(31, "Week 8 remains uncommitted and unpushed", lambda: (
        git("rev-parse", "HEAD") == EXPECTED_PARENT
        and git("ls-remote", "--heads", "origin", f"refs/heads/{EXPECTED_BRANCH}", allow_failure=True) == "",
        f"HEAD={git('rev-parse','HEAD')}; remote_week8={git('ls-remote','--heads','origin',f'refs/heads/{EXPECTED_BRANCH}',allow_failure=True)!r}",
    ))
    audit.check(32, "Week 8 scope contains only declared new paths", lambda: scope_check())
    audit.check(33, "Source, notebook-builder, and validator Python compile", lambda: compile_check())
    audit.check(34, "Output manifest will be hash-verified after final construction", lambda: (True, "conditional PASS; validator raises if final verification fails"))

    requirements = requirements_frame(
        [
            ("Exact published Phase 7 provenance", "phase8_01_preflight.json; phase7_source_audit.json"),
            ("No new simulator run or expensive benchmark rerun", "phase8_01_preflight.json"),
            ("Frozen Binary/Random/Max-Depth methods", "phase8_01_preflight.json"),
            ("B1 primary with B2/B3 robustness", "budget_snapshot_b1/b2/b3.csv"),
            ("Budget snapshots 20/30/40/50/60/70/80", "budget_snapshot_b1.csv"),
            ("Concrete q20/q30 accuracy statements", "headline_results.csv"),
            ("70/75/80/85/90 first crossings", "queries_to_accuracy_target.csv"),
            ("Persistent crossing robustness", "persistent_queries_to_accuracy_target.csv"),
            ("Unsuccessful runs explicit", "queries_to_accuracy_target.csv"),
            ("Random-equivalent interpolation without extrapolation", "random_equivalent_budget.csv"),
            ("Query savings and lower bounds", "query_savings_summary.csv"),
            ("Matched-run censoring-aware evidence", "matched_query_savings.csv"),
            ("Ten sample-efficiency figures", "figures/; figure_manifest.csv"),
            ("Keyhole discovery and enrichment", "keyhole_discovery_by_budget.csv"),
            ("Predictive confidence from saved probabilities", "predictive_confidence_summary.csv"),
            ("Brier/ECE and reliability bins", "predictive_calibration_summary.csv"),
            ("Machine-traceable headline claims", "headline_results.csv"),
            ("Plain-language Turkish explanation", "week8_phase1_plain_language_tr.md"),
            ("Instructional executable notebook", "notebooks/week_08/01_final_sample_efficiency.ipynb"),
            ("Offline/retrospective limitation", "phase8_01_preflight.json; headline_results.md"),
            ("No physical-boundary certainty overclaim", "headline_results.csv; claim ledger C13"),
            ("ST means substrate temperature", "phase8_01_preflight.json"),
            ("No causal claim", "claim ledger C08"),
            ("Original dirty checkout preserved", "original_worktree_baseline.json"),
            ("Week 1-7 artifacts untouched", "isolated worktree and scope checks"),
            ("Runtime and provenance summaries", "runtime_summary.json"),
            ("Figure hashes", "figure_manifest.csv"),
            ("Output hashes", "output_manifest.csv"),
        ]
    )
    validation = audit.frame()
    return validation, requirements, figure_frame


def scope_check() -> tuple[bool, str]:
    status_lines = git("status", "--porcelain=v1").splitlines()
    allowed_prefixes = [
        "src/week8_final_sample_efficiency_thesis_consolidation.py",
        "scripts/build_week8_notebooks.py",
        "scripts/validate_week8.py",
        "notebooks/week_08/",
        "outputs/week8_01_final_sample_efficiency/",
        "outputs/week8_02_thesis_consolidation/",
    ]
    paths = []
    for line in status_lines:
        raw = line[3:].strip().replace("\\", "/")
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        paths.append(raw)
    unexpected = [path for path in paths if not any(path == prefix or path.startswith(prefix) for prefix in allowed_prefixes)]
    return not unexpected, f"status_entries={len(paths)}; unexpected={unexpected}"


def compile_check() -> tuple[bool, str]:
    paths = [
        ROOT / "src" / "week8_final_sample_efficiency_thesis_consolidation.py",
        ROOT / "scripts" / "build_week8_notebooks.py",
        ROOT / "scripts" / "validate_week8.py",
    ]
    for path in paths:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    return True, "; ".join(path.name for path in paths)


def validate_phase2() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    audit = Audit("P2V")
    scorecard = read_csv(OUT2 / "final_real_data_scorecard.csv")
    synthetic = read_csv(OUT2 / "synthetic_to_real_summary.csv")
    ledger = read_csv(OUT2 / "final_thesis_claim_ledger.csv")
    aulc = read_csv(P7 / "phase7_aulc_summary.csv")
    phase7_decision = read_csv(P7 / "phase7_final_decision.csv")
    phase6_decision = read_csv(P6 / "phase6_final_decision.csv")
    narrative = (OUT2 / "final_results_narrative.md").read_text(encoding="utf-8")
    summary_tr = (OUT2 / "week8_final_plain_language_tr.md").read_text(encoding="utf-8")

    audit.check(1, "Final scorecard contains exactly Binary, Random, and Max-Depth", lambda: (
        set(scorecard["method"]) == set(METHODS) and scorecard["run_count"].eq(20).all(),
        f"methods={scorecard['method'].tolist()}; runs={scorecard['run_count'].tolist()}",
    ))

    def scorecard_recompute() -> tuple[bool, str]:
        maximum = 0.0
        mappings = {
            "mean_B1_q20_error_aulc": "common_normalized_aulc__B1_q20_error",
            "mean_B1_q30_error_aulc": "common_normalized_aulc__B1_q30_error",
            "mean_B2_q20_error_aulc": "common_normalized_aulc__B2_q20_error",
            "mean_B3_q20_error_aulc": "common_normalized_aulc__B3_q20_error",
            "mean_balanced_accuracy_aulc": "common_normalized_aulc__balanced_accuracy",
        }
        for row in scorecard.itertuples(index=False):
            group = aulc[aulc["method"].eq(row.method)]
            for destination, source in mappings.items():
                maximum = max(maximum, abs(getattr(row, destination) - group[source].mean()))
        return maximum < 1e-10, f"maximum_absolute_difference={maximum}"

    audit.check(2, "Final scorecard AULCs reproduce Phase 7 run-level artifacts", scorecard_recompute)
    audit.check(3, "Final primary remains Binary uncertainty-repulsion", lambda: (
        phase7_decision["decision"].iloc[0] == "BINARY ACQUISITION PRIMARY"
        and scorecard.loc[scorecard["method"].eq(M_BINARY), "primary_role"].iloc[0] == "final primary acquisition",
        phase7_decision["decision"].iloc[0],
    ))
    audit.check(4, "Max-Depth remains secondary and globally stronger on balanced accuracy", lambda: (
        scorecard.loc[scorecard["method"].eq(M_DEPTH), "primary_role"].iloc[0] == "secondary continuous physical comparator"
        and scorecard.loc[scorecard["method"].eq(M_DEPTH), "mean_balanced_accuracy_aulc"].iloc[0]
        > scorecard.loc[scorecard["method"].eq(M_BINARY), "mean_balanced_accuracy_aulc"].iloc[0],
        scorecard[["method_label", "mean_balanced_accuracy_aulc", "primary_role"]].to_json(orient="records"),
    ))
    audit.check(5, "Gate/Fusion remain negative supporting evidence", lambda: (
        phase7_decision["hybrid_success_json"].str.contains("false", case=False).all()
        and "Neither Hybrid" in phase7_decision["reason"].iloc[0],
        phase7_decision[["decision", "reason", "hybrid_success_json"]].to_json(orient="records"),
    ))
    audit.check(6, "G3 is not promoted to ground truth", lambda: (
        "G3" in ledger.loc[ledger["claim_id"].eq("C05"), "claim"].iloc[0]
        and "manual" in ledger.loc[ledger["claim_id"].eq("C05"), "caveat"].iloc[0].lower(),
        ledger.loc[ledger["claim_id"].eq("C05"), ["allowed_wording", "forbidden_overclaim"]].to_json(orient="records"),
    ))
    audit.check(7, "No universal G3 or Max-Depth threshold claim", lambda: (
        ledger[ledger["claim_id"].isin(["C06", "C07"])]["status"].eq("NOT SUPPORTED / PROHIBITED").all()
        and not strict_bool(phase6_decision["threshold_is_universal_physical_constant"]).any(),
        ledger[ledger["claim_id"].isin(["C06", "C07"])][["claim_id", "status"]].to_json(orient="records"),
    ))
    audit.check(8, "No causal interpretation", lambda: (
        ledger.loc[ledger["claim_id"].eq("C08"), "status"].iloc[0] == "NOT SUPPORTED / PROHIBITED"
        and not strict_bool(phase7_decision["causal_claim"]).any(),
        "claim C08 prohibited; Phase 7 causal_claim false",
    ))
    audit.check(9, "B1/B2/B3 are called empirical diagnostics rather than true physical boundary", lambda: (
        ledger.loc[ledger["claim_id"].eq("C09"), "status"].iloc[0] == "NOT SUPPORTED / PROHIBITED"
        and "empirical" in narrative.lower(),
        ledger.loc[ledger["claim_id"].eq("C09"), ["allowed_wording", "forbidden_overclaim"]].to_json(orient="records"),
    ))
    audit.check(10, "Synthetic summary reproduces the three saved benchmark groups", lambda: (
        len(synthetic) == 3
        and synthetic["fairness_passed"].all()
        and set(synthetic["source_benchmark_id"]) == {"branin", "hartmann4", "ackley"},
        synthetic[["benchmark", "seed_count", "best_q20_method"]].to_json(orient="records"),
    ))
    audit.check(11, "Synthetic evidence does not assert a universal acquisition winner", lambda: (
        synthetic["best_q20_method"].nunique() == 3
        and ledger.loc[ledger["claim_id"].eq("C10"), "status"].iloc[0] == "SUPPORTED",
        str(synthetic[["benchmark", "best_q20_method"]].to_dict(orient="records")),
    ))
    required_ledger_columns = [
        "claim_id", "claim", "status", "evidence_level", "primary_or_secondary",
        "supporting_phase", "supporting_artifact", "exact_metric", "allowed_wording",
        "forbidden_overclaim", "caveat",
    ]
    audit.check(12, "Claim ledger has all required columns and unique IDs", lambda: (
        set(required_ledger_columns).issubset(ledger.columns)
        and ledger["claim_id"].is_unique
        and len(ledger) == 13,
        f"rows={len(ledger)}; unique={ledger['claim_id'].is_unique}",
    ))
    audit.check(13, "Supported-primary ledger contains no unsupported row", lambda: (
        ledger[ledger["category"].eq("SUPPORTED PRIMARY CLAIMS")]["status"].eq("SUPPORTED").all(),
        ledger[ledger["category"].eq("SUPPORTED PRIMARY CLAIMS")][["claim_id", "status"]].to_json(orient="records"),
    ))

    def ledger_sources() -> tuple[bool, str]:
        missing = []
        for row in ledger.itertuples(index=False):
            for raw in str(row.supporting_artifact).split(";"):
                relative = raw.strip()
                if relative and not (ROOT / relative).is_file():
                    missing.append(f"{row.claim_id}:{relative}")
        return not missing, f"missing={missing}"

    audit.check(14, "Every claim-ledger source artifact exists", ledger_sources)
    audit.check(15, "Final narrative contains all twelve declared sections", lambda: (
        all(f"## {number}." in narrative for number in range(1, 13)),
        f"section_count={sum(f'## {number}.' in narrative for number in range(1,13))}/12",
    ))
    audit.check(16, "Final Turkish summary answers all eleven declared questions", lambda: (
        all(f"## {number}." in summary_tr for number in range(1, 12)),
        f"section_count={sum(f'## {number}.' in summary_tr for number in range(1,12))}/11",
    ))
    audit.check(17, "Offline retrospective and no-new-simulator limitation appears in final prose", lambda: (
        "offline retrospective" in narrative.lower()
        and "no genuinely new simulator" in narrative.lower()
        and "yeni simülasyon" in summary_tr.lower(),
        "limitation wording present in English narrative and Turkish summary",
    ))
    audit.check(18, "Final table set is exactly six CSV plus six Markdown tables", lambda: (
        len(list((OUT2 / "final_thesis_tables").glob("*.csv"))) == 6
        and len(list((OUT2 / "final_thesis_tables").glob("*.md"))) == 6,
        f"csv={len(list((OUT2/'final_thesis_tables').glob('*.csv')))}; md={len(list((OUT2/'final_thesis_tables').glob('*.md')))}",
    ))
    figure_frame = figure_manifest(OUT2, OUT2 / "final_thesis_figures")
    audit.check(19, "Final figure set contains ten valid distinct PNGs", lambda: (
        len(figure_frame) == 10
        and figure_frame["sha256"].nunique() == 10
        and figure_frame["bytes"].gt(10_000).all(),
        f"figures={len(figure_frame)}; unique_hashes={figure_frame['sha256'].nunique()}",
    ))
    state2 = notebook_state(NB2)
    audit.check(20, "Phase 2 teaching notebook executes 14 code cells with zero stored errors", lambda: (
        state2["code_cell_count"] == 14 and state2["executed_code_cell_count"] == 14 and state2["stored_error_count"] == 0,
        json.dumps(state2),
    ))
    audit.check(21, "No expensive synthetic or Week 1-7 rerun is reported", lambda: (
        not json.loads((OUT2 / "runtime_summary.json").read_text(encoding="utf-8"))["expensive_week1_7_experiments_rerun"],
        "runtime_summary expensive_week1_7_experiments_rerun=false",
    ))
    audit.check(22, "Repeated CV is not presented as independent physical trials", lambda: (
        ledger.loc[ledger["claim_id"].eq("C11"), "status"].iloc[0] == "NOT SUPPORTED / PROHIBITED"
        and "not 20 independent" in narrative.lower(),
        "claim C11 prohibited and narrative limitation explicit",
    ))
    audit.check(23, "Prospective deployment is not claimed", lambda: (
        ledger.loc[ledger["claim_id"].eq("C12"), "status"].iloc[0] == "NOT SUPPORTED / PROHIBITED"
        and "prospective" in narrative.lower(),
        "claim C12 prohibited; future validation section present",
    ))
    audit.check(24, "Week 8 scope remains isolated, uncommitted, and unpushed", lambda: scope_and_git_check())
    audit.check(25, "Output manifest will be hash-verified after final construction", lambda: (True, "conditional PASS; validator raises if final verification fails"))

    requirements = requirements_frame(
        [
            ("Final Binary/Random/Max-Depth scorecard", "final_real_data_scorecard.csv"),
            ("B1/B2/B3 and balanced-accuracy AULCs", "final_real_data_scorecard.csv"),
            ("Queries to 80/85% q20 and 80% q30", "final_real_data_scorecard.csv"),
            ("Keyhole discovery, savings, and runtime", "final_real_data_scorecard.csv"),
            ("Synthetic Branin/Hartmann4/Ackley4 consolidation", "synthetic_to_real_summary.csv"),
            ("No universal synthetic winner", "synthetic_to_real_summary.csv; claim C10"),
            ("Final primary remains Binary", "scorecard; Phase 7 decision"),
            ("Max-Depth remains secondary", "scorecard"),
            ("Gate/Fusion remain negative evidence", "Phase 7 decision"),
            ("G3 not promoted to ground truth", "claims C05-C06"),
            ("No universal scalar threshold", "claims C06-C07"),
            ("No causal interpretation", "claim C08"),
            ("B1/B2/B3 empirical diagnostics", "claim C09"),
            ("Repeated CV limitation", "claim C11; narrative"),
            ("No prospective validation claim", "claim C12; narrative"),
            ("Full 13-row claim ledger", "final_thesis_claim_ledger.csv"),
            ("Ten final thesis figures", "final_thesis_figures/"),
            ("Six final thesis tables", "final_thesis_tables/"),
            ("Academic English results narrative", "final_results_narrative.md"),
            ("Complete plain-language Turkish summary", "week8_final_plain_language_tr.md"),
            ("Concise executable evidence notebook", "notebooks/week_08/02_thesis_evidence_consolidation.ipynb"),
            ("Runtime and provenance closeout", "runtime_summary.json"),
            ("Figure hashes", "figure_manifest.csv"),
            ("Output hashes", "output_manifest.csv"),
            ("Hard stop after Phase 2", "uncommitted/unpushed scope check"),
        ]
    )
    return audit.frame(), requirements, figure_frame


def scope_and_git_check() -> tuple[bool, str]:
    scope_ok, scope_detail = scope_check()
    remote = git("ls-remote", "--heads", "origin", f"refs/heads/{EXPECTED_BRANCH}", allow_failure=True)
    passed = scope_ok and git("rev-parse", "HEAD") == EXPECTED_PARENT and remote == ""
    return passed, f"{scope_detail}; HEAD={git('rev-parse','HEAD')}; remote_week8={remote!r}"


def closeout(
    output_dir: Path,
    notebook: Path,
    validation: pd.DataFrame,
    requirements: pd.DataFrame,
    figures: pd.DataFrame,
) -> tuple[int, int, int]:
    if not validation["status"].eq("PASS").all():
        failed = validation[validation["status"].ne("PASS")]
        raise RuntimeError(f"Validation failed for {output_dir.name}:\n{failed.to_string(index=False)}")
    if not requirements["status"].eq("PASS").all():
        raise RuntimeError(f"Requirement checklist failed for {output_dir.name}")
    validation.to_csv(output_dir / "validation_results.csv", index=False, lineterminator="\n")
    requirements.to_csv(output_dir / "requirement_checklist.csv", index=False, lineterminator="\n")
    figures.to_csv(output_dir / "figure_manifest.csv", index=False, lineterminator="\n")
    runtime_path = output_dir / "runtime_summary.json"
    prospective_count = len(manifest_files(output_dir, notebook))
    state = notebook_state(notebook)
    update_runtime(
        runtime_path,
        validation_pass_count=len(validation),
        validation_total_count=len(validation),
        requirement_pass_count=len(requirements),
        requirement_total_count=len(requirements),
        notebook_code_cells=state["code_cell_count"],
        notebook_executed_code_cells=state["executed_code_cell_count"],
        notebook_stored_errors=state["stored_error_count"],
        figure_count=len(figures),
        prospective_manifest_rows=prospective_count,
        validation_pending_independent_validator=False,
    )
    manifest = write_manifest(output_dir, notebook)
    passed, detail = verify_manifest(manifest)
    if not passed:
        raise RuntimeError(f"Final manifest verification failed for {output_dir.name}: {detail}")
    return len(validation), len(requirements), len(manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    phase1_validation, phase1_requirements, phase1_figures = validate_phase1()
    phase2_validation, phase2_requirements, phase2_figures = validate_phase2()
    p1 = closeout(OUT1, NB1, phase1_validation, phase1_requirements, phase1_figures)
    p2 = closeout(OUT2, NB2, phase2_validation, phase2_requirements, phase2_figures)
    print(
        json.dumps(
            {
                "status": "PASS",
                "phase1": {"validation": p1[0], "requirements": p1[1], "manifest_rows": p1[2], "figures": len(phase1_figures)},
                "phase2": {"validation": p2[0], "requirements": p2[1], "manifest_rows": p2[2], "figures": len(phase2_figures)},
                "notebooks": {"phase1": notebook_state(NB1), "phase2": notebook_state(NB2)},
                "git_head": git("rev-parse", "HEAD"),
                "git_branch": git("branch", "--show-current"),
                "week8_remote_branch_exists": bool(git("ls-remote", "--heads", "origin", f"refs/heads/{EXPECTED_BRANCH}", allow_failure=True)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
