"""Independent fail-closed validator for Week 7 Phase 7 artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np
import pandas as pd
from scipy.spatial import distance
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.week7_sph_v2_common import sha256_file, write_csv


OUTPUT_ROOT = ROOT / "outputs" / "week7_07_final_boundary_hybrid_benchmark"
NOTEBOOK = ROOT / "notebooks" / "week_07" / "07_final_boundary_hybrid_benchmark.ipynb"
PHASE6_OUTPUT = ROOT / "outputs" / "week7_06_real_data_boundary_active_level_set"
EXPECTED_PHASE6 = "5734de6f533e1de1e15a07de24e7d4e6e53bb6fa"
EXPECTED_HF = "b6dc254a2b607a31cb9f97b40990339c3d5ca1e8"
EXPECTED_PREREG = "a3581cb61c4b2f95aa71838fc9c199ca8f992fef7de67104970767db0af9643f"
PHASE7_BRANCH = "codex/week7-phase7-final-boundary-hybrid-benchmark"
FEATURES = ["P", "VX", "LS", "ST"]
BOUNDARIES = ["B1", "B2", "B3"]
M0_BINARY = "shared_random_binary_head"
M0_DEPTH = "shared_random_max_depth_head"
M1 = "binary_uncertainty_repulsion"
M2 = "max_depth_straddle"
M3 = "hybrid_binary_gate20_max_depth_straddle"
M4 = "hybrid_equal_rank_fusion"
FULL_METHODS = [M0_BINARY, M0_DEPTH, M1, M2, M3, M4]
SMOKE_METHODS = [M1, M3, M4]


def strict_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    normalized = series.astype(str).str.strip().str.lower()
    if not normalized.isin(["true", "false", "1", "0"]).all():
        raise ValueError(f"Invalid booleans in {series.name}")
    return normalized.isin(["true", "1"])


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()


class Audit:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def check(self, check_id: str, check: str, action: Callable[[], tuple[bool, str]]) -> None:
        try:
            passed, detail = action()
        except Exception as exc:
            passed, detail = False, f"{type(exc).__name__}: {exc}"
        self.rows.append(
            {
                "check_id": check_id,
                "check": check,
                "status": "PASS" if passed else "FAIL",
                "detail": detail,
            }
        )

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)


def load_csv(output_dir: Path, name: str) -> pd.DataFrame:
    path = output_dir / name
    if not path.is_file():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def manifest_inventory(output_dir: Path) -> pd.DataFrame:
    files: set[Path] = set()
    for path in output_dir.rglob("*"):
        if path.is_file() and path.name != "output_manifest.csv":
            files.add(path)
    extra_candidates = [
        ROOT / "src" / "week7_phase7_final_boundary_hybrid_benchmark.py",
        ROOT / "src" / "week7_phase7_reporting.py",
        ROOT / "scripts" / "build_week7_07_notebook.py",
        ROOT / "scripts" / "validate_week7_07.py",
        NOTEBOOK,
        ROOT / "docs" / "thesis_progress_log.md",
    ]
    for path in extra_candidates:
        if path.is_file():
            files.add(path)
    rows = []
    for path in sorted(files):
        rows.append(
            {
                "relative_path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return pd.DataFrame(rows)


def validate(smoke: bool) -> dict[str, Any]:
    output_dir = OUTPUT_ROOT / "smoke" if smoke else OUTPUT_ROOT
    final_budget = 30 if smoke else 80
    expected_runs = 2 if smoke else 20
    expected_methods = SMOKE_METHODS if smoke else FULL_METHODS
    expected_manifest_rows = expected_runs * len(expected_methods)
    audit = Audit()

    preflight = json.loads((output_dir / "phase7_preflight.json").read_text(encoding="utf-8"))
    provenance = json.loads((output_dir / "input_provenance.json").read_text(encoding="utf-8"))
    hf = json.loads((output_dir / "hf_revision_audit.json").read_text(encoding="utf-8"))
    publication = json.loads((output_dir / "phase6_publication_audit.json").read_text(encoding="utf-8"))
    prereg_path = OUTPUT_ROOT / "phase7_preregistered_decision_rule.json"
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    population = pd.read_csv(PHASE6_OUTPUT / "primary_common_population.csv", low_memory=False)
    population["has_keyhole"] = strict_bool(population["has_keyhole"])
    reuse = load_csv(output_dir, "phase6_run_reuse_audit.csv")
    reproduction = load_csv(output_dir, "phase6_reproduction_check.csv")
    boundary = load_csv(output_dir, "boundary_metric_reference.csv")
    definitions = load_csv(output_dir, "boundary_metric_definitions.csv")
    method_definitions = load_csv(output_dir, "phase7_method_definitions.csv")
    run_manifest = load_csv(output_dir, "hybrid_run_manifest.csv")
    queries = load_csv(output_dir, "phase7_all_method_query_history.csv")
    hybrid_queries = load_csv(output_dir, "hybrid_query_history.csv")
    predictions = load_csv(output_dir, "phase7_all_method_prediction_checkpoints.csv")
    hybrid_predictions = load_csv(output_dir, "hybrid_prediction_history.csv")
    thresholds = load_csv(output_dir, "hybrid_online_threshold_history.csv")
    diagnostics = load_csv(output_dir, "hybrid_model_diagnostics.csv")
    fairness = load_csv(output_dir, "phase7_fairness_audit.csv")
    curves = load_csv(output_dir, "phase7_learning_curve_summary.csv")
    aulc = load_csv(output_dir, "phase7_aulc_summary.csv")
    tolerance = load_csv(output_dir, "phase7_queries_to_tolerance.csv")
    comparisons = load_csv(output_dir, "phase7_paired_method_comparisons.csv")
    bootstrap = load_csv(output_dir, "phase7_paired_bootstrap_intervals.csv")
    pareto = load_csv(output_dir, "phase7_pareto_summary.csv")
    representative = load_csv(output_dir, "phase7_representative_runs.csv")
    reconciliation = load_csv(output_dir, "phase6_baseline_replay_reconciliation.csv")

    audit.check("V01", "Exact committed Phase 6 parent and Phase 7 branch", lambda: (
        git("rev-parse", "HEAD") == EXPECTED_PHASE6 and git("branch", "--show-current") == PHASE7_BRANCH,
        f"HEAD={git('rev-parse','HEAD')}; branch={git('branch','--show-current')}",
    ))
    audit.check("V02", "Phase 6 local/upstream/remote publication equality", lambda: (
        bool(publication["all_equal"]) and publication["expected_commit"] == EXPECTED_PHASE6,
        json.dumps(publication, sort_keys=True),
    ))
    audit.check("V03", "HF revision unchanged from Phase 6", lambda: (
        hf["live_revision"] == EXPECTED_HF and bool(hf["matches_phase6"]),
        f"live={hf['live_revision']}",
    ))
    audit.check("V04", "Exact 405 population and 73/332 manual labels", lambda: (
        len(population) == 405 and int(population["has_keyhole"].sum()) == 73 and int((~population["has_keyhole"]).sum()) == 332,
        f"n={len(population)}, positive={int(population['has_keyhole'].sum())}",
    ))
    audit.check("V05", "All 20 saved Phase 6 run definitions hash-reused", lambda: (
        len(reuse) == 20 and reuse["status"].eq("PASS").all() and strict_bool(reuse["warm_hash_matches"]).all() and strict_bool(reuse["split_hash_matches"]).all(),
        f"rows={len(reuse)}, max_warm={pd.to_numeric(reuse['effective_warm_start']).max()}",
    ))
    audit.check("V06", "Small Phase 6 reproduction check", lambda: (
        len(reproduction) >= 20 and reproduction["status"].eq("PASS").all(),
        f"pass={reproduction['status'].eq('PASS').sum()}/{len(reproduction)}, max_diff={pd.to_numeric(reproduction['maximum_absolute_difference']).max()}",
    ))
    audit.check("V07", "Preregistered decision rule hash immutable", lambda: (
        sha256_file(prereg_path) == EXPECTED_PREREG and (OUTPUT_ROOT / "phase7_preregistered_decision_rule.sha256").read_text().split()[0] == EXPECTED_PREREG,
        sha256_file(prereg_path),
    ))
    result_files = [path for path in output_dir.glob("*.csv") if path.name not in {"phase6_run_reuse_audit.csv", "phase6_reproduction_check.csv"}]
    audit.check("V08", "Preregistration predates result artifacts", lambda: (
        all(prereg_path.stat().st_mtime <= path.stat().st_mtime for path in result_files),
        f"prereg_mtime={prereg_path.stat().st_mtime}; result_files={len(result_files)}",
    ))

    def boundary_formula_check() -> tuple[bool, str]:
        x = population[FEATURES].to_numpy(float)
        labels = population["has_keyhole"].astype(int).to_numpy()
        scaled = StandardScaler().fit_transform(x)
        dmat = distance.cdist(scaled, scaled)
        np.fill_diagonal(dmat, np.inf)
        opposite = np.where(labels[:, None] != labels[None, :], dmat, np.inf)
        same_mask = labels[:, None] == labels[None, :]
        np.fill_diagonal(same_mask, False)
        same = np.where(same_mask, dmat, np.inf)
        d_opp = opposite.min(axis=1)
        d_same = same.min(axis=1)
        neighbours = NearestNeighbors(n_neighbors=6).fit(scaled).kneighbors(scaled, return_distance=False)[:, 1:]
        b2 = (labels[neighbours] != labels[:, None]).mean(axis=1)
        b3 = d_opp / (d_opp + d_same)
        diffs = {
            "B1": float(np.max(np.abs(d_opp - pd.to_numeric(boundary["B1_nearest_opposite_distance"]).to_numpy(float)))),
            "B2": float(np.max(np.abs(b2 - pd.to_numeric(boundary["B2_local_disagreement_k5"]).to_numpy(float)))),
            "B3": float(np.max(np.abs(b3 - pd.to_numeric(boundary["B3_relative_class_distance_ratio"]).to_numpy(float)))),
        }
        return max(diffs.values()) <= 1e-12, json.dumps(diffs)

    audit.check("V09", "B1/B2/B3 formulas independently recompute", boundary_formula_check)
    audit.check("V10", "Boundary definitions use no max-depth/G3/model columns and are evaluation-only", lambda: (
        not any("depth" in col.lower() or "g3" in col.lower() or "prediction" in col.lower() for col in boundary.columns)
        and strict_bool(definitions["uses_only_inputs_and_manual_labels"]).all()
        and strict_bool(definitions["evaluation_only"]).all()
        and not strict_bool(definitions["enters_acquisition"]).any(),
        f"definition_rows={len(definitions)}",
    ))
    audit.check("V11", "Predeclared method set only", lambda: (
        set(run_manifest["method"]) == set(expected_methods)
        and set(method_definitions["method"]).issuperset({M0_BINARY, M0_DEPTH, M1, M2, M3, M4}),
        f"executed={sorted(run_manifest['method'].unique())}",
    ))
    audit.check("V12", "Exact method/run and budget counts", lambda: (
        len(run_manifest) == expected_manifest_rows
        and run_manifest["run_id"].nunique() == expected_runs
        and set(pd.to_numeric(run_manifest["final_budget"]).astype(int)) == {final_budget},
        f"manifest={len(run_manifest)}, runs={run_manifest['run_id'].nunique()}, final={sorted(run_manifest['final_budget'].unique())}",
    ))
    audit.check("V13", "All methods share exact split and warm start per run", lambda: (
        run_manifest.groupby("run_id")["split_sha256"].nunique().eq(1).all()
        and run_manifest.groupby("run_id")["warm_start_sha256"].nunique().eq(1).all(),
        f"runs={run_manifest['run_id'].nunique()}",
    ))
    audit.check("V14", "Phase 6 baseline replays reconcile", lambda: (
        len(reconciliation) >= expected_runs and reconciliation["status"].eq("PASS").all(),
        f"pass={reconciliation['status'].eq('PASS').sum()}/{len(reconciliation)}",
    ))

    def fairness_check() -> tuple[bool, str]:
        true_cols = [
            "candidate_pool_is_exact_phase6_outer_training_only",
            "test_set_never_queried",
            "extra_warm_start_queries_counted",
            "gate_fraction_fixed_0_20",
            "rank_weights_fixed_0_5_0_5",
        ]
        false_cols = [
            "test_labels_used_for_fitting_or_acquisition",
            "test_outputs_used_for_acquisition",
            "hidden_pool_labels_used_for_acquisition",
            "hidden_pool_max_depth_used_for_acquisition",
            "boundary_metrics_used_for_acquisition",
        ]
        passed = all(strict_bool(fairness[col]).all() for col in true_cols) and all(not strict_bool(fairness[col]).any() for col in false_cols)
        return passed, f"rows={len(fairness)}"

    audit.check("V15", "Leakage/fairness invariants", fairness_check)
    audit.check("V16", "Every method/run uses exact simulator-query budget", lambda: (
        len(queries) == expected_manifest_rows * final_budget
        and queries.groupby(["run_id", "method"])["query_order"].count().eq(final_budget).all(),
        f"query_rows={len(queries)} expected={expected_manifest_rows * final_budget}",
    ))

    def gate_check() -> tuple[bool, str]:
        rows = hybrid_queries[
            hybrid_queries["method"].eq(M3)
            & hybrid_queries["selection_stage"].eq("preregistered_hybrid_acquisition")
        ]
        metadata = [json.loads(value) for value in rows["acquisition_metadata_json"]]
        passed = all(
            item["requested_gate_fraction"] == 0.2
            and item["gate_count"] == math.ceil(0.2 * item["candidate_count"])
            and item["binary_priority_completion_preregistered"]
            for item in metadata
        )
        return passed and len(metadata) > 0, f"steps={len(metadata)}"

    def fusion_check() -> tuple[bool, str]:
        rows = hybrid_queries[
            hybrid_queries["method"].eq(M4)
            & hybrid_queries["selection_stage"].eq("preregistered_hybrid_acquisition")
        ]
        metadata = [json.loads(value) for value in rows["acquisition_metadata_json"]]
        passed = all(item["binary_weight"] == 0.5 and item["max_depth_weight"] == 0.5 for item in metadata)
        return passed and len(metadata) > 0, f"steps={len(metadata)}"

    audit.check("V17", "Hybrid Gate exactly fixed at top 20%", gate_check)
    audit.check("V18", "Rank Fusion exactly fixed at 0.5/0.5", fusion_check)
    audit.check("V19", "Hybrid primary predictor is Binary GPC", lambda: (
        set(hybrid_predictions["primary_predictor"]) == {"Binary GPC"}
        and set(curves.loc[curves["method"].isin([M3, M4]), "final_primary_predictor"]) == {"Binary GPC"},
        f"hybrid_prediction_rows={len(hybrid_predictions)}",
    ))
    audit.check("V20", "Max depth is Hybrid acquisition-only auxiliary information", lambda: (
        set(curves.loc[curves["method"].isin([M3, M4]), "max_depth_role"]) == {"auxiliary_acquisition_only"}
        and strict_bool(run_manifest.loc[run_manifest["method"].isin([M3, M4]), "max_depth_is_acquisition_only"]).all(),
        f"hybrid_runs={run_manifest['method'].isin([M3,M4]).sum()}",
    ))
    audit.check("V21", "Online tau uses queried rows only with fixed direction", lambda: (
        len(thresholds) > 0
        and set(thresholds["training_scope"]) == {"currently_queried_only"}
        and strict_bool(thresholds["direction_fixed_higher_is_keyhole_like"]).all()
        and not strict_bool(thresholds["test_information_used"]).any()
        and not strict_bool(thresholds["unqueried_pool_information_used"]).any(),
        f"threshold_rows={len(thresholds)}",
    ))

    def curve_check() -> tuple[bool, str]:
        for (run_id, method), group in curves.groupby(["run_id", "method"]):
            budgets = sorted(pd.to_numeric(group["budget"]).astype(int).tolist())
            if budgets != list(range(min(budgets), final_budget + 1)):
                return False, f"gap={run_id}/{method}"
        return True, f"curve_rows={len(curves)}"

    audit.check("V22", "Integer-complete learning curves", curve_check)

    def aulc_check() -> tuple[bool, str]:
        max_diff = 0.0
        for _, row in aulc.iterrows():
            group = curves[curves["run_id"].eq(row["run_id"]) & curves["method"].eq(row["method"])].copy()
            start = int(row["common_start_budget"])
            group = group[pd.to_numeric(group["budget"]).ge(start)].sort_values("budget")
            for column in [col for col in aulc.columns if col.startswith("common_normalized_aulc__")]:
                metric = column.split("__", 1)[1]
                recomputed = float(np.trapezoid(pd.to_numeric(group[metric]), pd.to_numeric(group["budget"])) / max(final_budget - start, 1))
                max_diff = max(max_diff, abs(recomputed - float(row[column])))
        return max_diff <= 1e-12, f"max_diff={max_diff}"

    audit.check("V23", "AULCs independently recompute", aulc_check)

    def tolerance_check() -> tuple[bool, str]:
        mismatches = 0
        for _, row in tolerance.iterrows():
            group = curves[curves["run_id"].eq(row["run_id"]) & curves["method"].eq(row["method"])].sort_values("budget")
            values = pd.to_numeric(group[row["metric"]])
            eligible = values >= float(row["target"]) if row["direction"] == "at_least" else values <= float(row["target"])
            reached = group[eligible]
            expected_status = "reached" if len(reached) else "not_reached"
            expected_query = int(reached["budget"].iloc[0]) if len(reached) else None
            actual_query = None if pd.isna(row["queries_required"]) else int(row["queries_required"])
            mismatches += int(row["status"] != expected_status or actual_query != expected_query)
        return mismatches == 0, f"rows={len(tolerance)}, mismatches={mismatches}"

    audit.check("V24", "Queries-to-tolerance independently recompute", tolerance_check)
    expected_resamples = 200 if smoke else 5000
    audit.check("V25", "Paired comparisons use matched runs and predeclared bootstrap count", lambda: (
        len(comparisons) > 0
        and pd.to_numeric(comparisons["paired_run_count"]).eq(expected_runs).all()
        and pd.to_numeric(bootstrap["bootstrap_resamples"]).eq(expected_resamples).all(),
        f"comparison_rows={len(comparisons)}, bootstrap={sorted(bootstrap['bootstrap_resamples'].unique())}",
    ))

    def pareto_check() -> tuple[bool, str]:
        errors = 0
        for (boundary_id, quantile), group in pareto.groupby(["boundary_definition", "quantile"]):
            for _, row in group.iterrows():
                dominators = group[
                    group["mean_boundary_error_aulc"].le(row["mean_boundary_error_aulc"] + 1e-15)
                    & group["mean_balanced_accuracy_aulc"].ge(row["mean_balanced_accuracy_aulc"] - 1e-15)
                    & (
                        group["mean_boundary_error_aulc"].lt(row["mean_boundary_error_aulc"] - 1e-15)
                        | group["mean_balanced_accuracy_aulc"].gt(row["mean_balanced_accuracy_aulc"] + 1e-15)
                    )
                ]
                expected = len(dominators) > 0
                errors += int(strict_bool(pd.Series([row["pareto_dominated"]])).iloc[0] != expected)
        return errors == 0, f"rows={len(pareto)}, errors={errors}"

    audit.check("V26", "Pareto dominance independently recomputes", pareto_check)
    audit.check("V27", "Representative runs selected algorithmically", lambda: (
        len(representative) == 3 and strict_bool(representative["algorithmic_selection"]).all(),
        f"rows={len(representative)}",
    ))
    audit.check("V28", "No new surrogate family or kernel", lambda: (
        diagnostics["kernel"].astype(str).str.contains("Matern").all()
        and diagnostics["kernel"].astype(str).str.contains("nu=1.5").all(),
        f"diagnostic_rows={len(diagnostics)}",
    ))
    audit.check("V29", "No manual-label or physical-target redefinition", lambda: (
        not bool(preflight["manual_labels_modified"])
        and not bool(preflight["maximum_depth_redefined"])
        and bool(provenance["T0_definition_unchanged"]),
        "manual labels, max depth, and T0 unchanged",
    ))

    if not smoke:
        decision = load_csv(output_dir, "phase7_final_decision.csv")
        rule_outcome = load_csv(output_dir, "phase7_preregistered_rule_outcome.csv")
        surfaces = load_csv(output_dir, "phase7_supported_boundary_surfaces.csv")
        figure_manifest = load_csv(output_dir, "figure_manifest.csv")
        audit.check("V30", "Final decision is allowed and mechanically linked to preregistration", lambda: (
            len(decision) == 1
            and decision["decision"].iloc[0] in {
                "HYBRID ACQUISITION PRIMARY",
                "BINARY ACQUISITION PRIMARY",
                "MAX-DEPTH FORMULATION PRIMARY",
                "NO ROBUST WINNER / METRIC-DEPENDENT",
            }
            and strict_bool(decision["preregistered_rule_applied_mechanically"]).all()
            and decision["decision_rule_sha256"].iloc[0] == EXPECTED_PREREG,
            decision.to_json(orient="records"),
        ))
        audit.check("V31", "Supported boundary surfaces mask unsupported extrapolation", lambda: (
            len(surfaces) > 0
            and "supported" in surfaces
            and strict_bool(surfaces.loc[~strict_bool(surfaces["supported"]), "unsupported_probability_must_be_greyed"]).all(),
            f"surface_rows={len(surfaces)}",
        ))

        def notebook_check() -> tuple[bool, str]:
            notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
            code = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
            markdown = [cell for cell in notebook["cells"] if cell["cell_type"] == "markdown"]
            counts = [cell.get("execution_count") for cell in code]
            errors = [output for cell in code for output in cell.get("outputs", []) if output.get("output_type") == "error"]
            passed = len(markdown) >= 40 and len(code) >= 40 and counts == list(range(1, len(code) + 1)) and not errors
            return passed, f"markdown={len(markdown)}, code={len(code)}, errors={len(errors)}"

        audit.check("V32", "Teaching notebook fully executed without errors", notebook_check)

        def figure_check() -> tuple[bool, str]:
            errors = []
            for _, row in figure_manifest.iterrows():
                path = output_dir / str(row["relative_path"])
                if not path.is_file() or path.stat().st_size != int(row["bytes"]) or sha256_file(path) != row["sha256"]:
                    errors.append(str(path))
            context_cols = ["population_visible", "metric_status_visible", "units_visible", "caveat_visible"]
            context_ok = all(col in figure_manifest and strict_bool(figure_manifest[col]).all() for col in context_cols)
            return len(figure_manifest) >= 40 and not errors and context_ok, f"figures={len(figure_manifest)}, errors={len(errors)}, context={context_ok}"

        audit.check("V33", "At least 40 meaningful figures exist and hash-verify", figure_check)
    else:
        audit.check("V30", "Smoke explicitly not treated as scientific decision", lambda: (
            json.loads((output_dir / "summary.json").read_text())["scientific_result"] is False,
            "smoke scientific_result=false",
        ))

    audit.check("V34", "Original dirty checkout fingerprint remains protected", lambda: (
        bool(provenance["original_dirty_checkout"]["all_protected_hashes_match"])
        and provenance["original_dirty_checkout"]["head"] == "6fd6be57e5341e083a7023a3ae29e65b7b326bbd",
        f"protected={provenance['original_dirty_checkout']['all_protected_hashes_match']}",
    ))

    validation = audit.frame()
    requirement_rows = [
        ("R01", "Phase 6 safely published before Phase 7", {"V01", "V02"}),
        ("R02", "Exact HF and 405-row population reused", {"V03", "V04"}),
        ("R03", "Exact 20 Phase 6 runs and warm starts reused", {"V05", "V13"}),
        ("R04", "Phase 6 reproduction check passed", {"V06", "V14"}),
        ("R05", "Decision rule preregistered before results", {"V07", "V08"}),
        ("R06", "B1/B2/B3 independently valid and evaluation-only", {"V09", "V10"}),
        ("R07", "Only preregistered methods and budgets executed", {"V11", "V12", "V16"}),
        ("R08", "Leakage/fairness barriers hold", {"V15", "V19", "V20", "V21"}),
        ("R09", "Gate and fusion hyperparameters fixed", {"V17", "V18"}),
        ("R10", "Learning curves and AULCs reconcile", {"V22", "V23"}),
        ("R11", "Tolerance and paired uncertainty reconcile", {"V24", "V25"}),
        ("R12", "Pareto and representative-run logic reconcile", {"V26", "V27"}),
        ("R13", "Surrogate family and physical targets unchanged", {"V28", "V29"}),
        ("R14", "Original dirty worktree remains protected", {"V34"}),
    ]
    if not smoke:
        requirement_rows.extend(
            [
                ("R15", "Final decision mechanically applies preregistration", {"V30"}),
                ("R16", "Supported surfaces mask extrapolation", {"V31"}),
                ("R17", "Teaching notebook fully executed", {"V32"}),
                ("R18", "At least 40 figures hash-verify", {"V33"}),
            ]
        )
    requirements = []
    status_lookup = validation.set_index("check_id")["status"].to_dict()
    for requirement_id, requirement, checks in requirement_rows:
        passed = all(status_lookup.get(check) == "PASS" for check in checks)
        requirements.append(
            {
                "requirement_id": requirement_id,
                "requirement": requirement,
                "supporting_checks": ",".join(sorted(checks)),
                "status": "PASS" if passed else "FAIL",
            }
        )
    requirement_frame = pd.DataFrame(requirements)
    write_csv(output_dir / "validation_results.csv", validation)
    write_csv(output_dir / "requirement_checklist.csv", requirement_frame)
    manifest = manifest_inventory(output_dir)
    write_csv(output_dir / "output_manifest.csv", manifest)

    manifest_errors = []
    for _, row in manifest.iterrows():
        path = ROOT / row["relative_path"]
        if not path.is_file() or path.stat().st_size != int(row["bytes"]) or sha256_file(path) != row["sha256"]:
            manifest_errors.append(row["relative_path"])
    passed = validation["status"].eq("PASS").all() and requirement_frame["status"].eq("PASS").all() and not manifest_errors
    result = {
        "mode": "smoke" if smoke else "full",
        "output_dir": str(output_dir),
        "validation_passed": int(validation["status"].eq("PASS").sum()),
        "validation_total": len(validation),
        "requirements_passed": int(requirement_frame["status"].eq("PASS").sum()),
        "requirements_total": len(requirement_frame),
        "manifest_rows": len(manifest),
        "manifest_errors": manifest_errors,
        "status": "PASS" if passed else "FAIL",
    }
    if not passed:
        raise RuntimeError(json.dumps(result, indent=2))
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    print(json.dumps(validate(args.smoke), indent=2))


if __name__ == "__main__":
    main()
