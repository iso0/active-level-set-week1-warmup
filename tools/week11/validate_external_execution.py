"""Independent structural QC for the completed frozen Week 11 execution.

This checker never opens the sealed oracle and never imports or runs a model. It
reads only the committed freeze and the completed execution artifacts, then
writes evidence outside the frozen output tree.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd


EXPECTED_FREEZE_SHA256 = "856219763ec41ba22eb13ebb5c23e2137fb3d6eb884de71a44f96d80debe1eee"
CONTROL = "M3_margin_incumbent"
CHALLENGER = "early8__coverage_then_margin_B40"
ATTRIBUTION = "coverage_then_margin_B40"
ARMS = (CONTROL, CHALLENGER, ATTRIBUTION)
BUDGETS = tuple(range(16, 81))
class QCError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise QCError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _check_path_group(group: pd.DataFrame, train: set[int]) -> None:
    require(len(group) == 80, "Each split-arm path must contain B1..B80")
    order = group.sort_values("query_order")
    require(order.query_order.astype(int).tolist() == list(range(1, 81)),
            "Path query orders must be exactly 1..80")
    rows = order.row_index.astype(int).tolist()
    require(len(set(rows)) == 80, "Path contains a repeated query")
    require(set(rows).issubset(train), "Path includes a held-out row")


def _check_prediction_group(group: pd.DataFrame, expected_test: set[int]) -> None:
    require(len(group) == len(expected_test), "Prediction group row count differs from held-out fold")
    require(set(group.row_index.astype(int)) == expected_test,
            "Prediction group does not contain exactly the held-out rows")


def _require_exact(actual, expected, message: str) -> None:
    require(actual == expected, message)


def _candidate_start_length(frozen16: list[int], labels: dict[int, int]) -> int:
    queried = list(frozen16[:8])
    observed = [labels[index] for index in queried]
    cursor = 8
    while len(set(observed)) < 2 and cursor < 16:
        queried.append(frozen16[cursor])
        observed.append(labels[frozen16[cursor]])
        cursor += 1
    require(len(set(observed)) == 2, "Candidate B would not have both classes by frozen B16")
    return len(queried)


def _split_checks(splits: list[dict]) -> dict[str, dict]:
    require(len(splits) == 100, "Split manifest must contain 100 splits")
    by_split = {row["split_id"]: row for row in splits}
    require(len(by_split) == 100, "Duplicate split IDs")
    expected = {f"external__r{repeat:03d}_f{fold:02d}"
                for repeat in range(1, 21) for fold in range(1, 6)}
    require(set(by_split) == expected, "Split IDs do not cover 20x5")
    universe = set(range(136))
    for split in splits:
        train, test = set(map(int, split["train_indices"])), set(map(int, split["test_indices"]))
        require(train.isdisjoint(test) and train | test == universe, "Split is not a train/test partition")
        require(len(train) in {108, 109} and len(test) in {27, 28}, "Unexpected fold size")
    for repeat in range(1, 21):
        held = [int(i) for s in splits if int(s["repeat"]) == repeat for i in s["test_indices"]]
        require(len(held) == 136 and set(held) == universe, "A repeat does not hold out every ID once")
    return by_split


def _completed_pairs_before_failure(splits: list[dict], failure: dict) -> list[tuple[str, str]]:
    ordered = [(split["split_id"], arm) for split in splits for arm in ARMS]
    target = (failure["split_id"], failure["arm"])
    require(target in ordered, "Failure split-arm is outside the frozen execution order")
    return ordered[:ordered.index(target)]


def _maximin_b16(x: np.ndarray, pool: list[int], seed: int) -> list[int]:
    from scipy.spatial import distance
    from sklearn.preprocessing import StandardScaler

    pool_array = np.asarray(pool, int)
    scaled = StandardScaler().fit_transform(np.asarray(x, float)[pool_array])
    rng = np.random.default_rng(int(seed))
    chosen = [int(rng.integers(len(pool_array)))]
    while len(chosen) < 16:
        remaining = np.setdiff1d(np.arange(len(pool_array)), chosen, assume_unique=True)
        nearest = distance.cdist(scaled[remaining], scaled[chosen]).min(axis=1)
        best = nearest.max()
        ties = remaining[np.isclose(nearest, best, rtol=1e-12, atol=1e-14)]
        chosen.append(int(ties[np.argmin(pool_array[ties])]))
    return pool_array[np.asarray(chosen)].astype(int).tolist()


def _validate_incomplete(frozen: dict, paths: dict[str, Path], output_root: Path,
                         manifest_path: Path, run_manifest: dict, failures: list,
                         fallbacks: list) -> dict:
    execution_keys = {"split_manifest", "path_manifest", "per_budget_predictions",
                      "fit_diagnostics", "failure_events", "fallback_events", "run_manifest"}
    actual_files = {p.resolve() for p in (output_root.resolve() / "external_validation").iterdir() if p.is_file()}
    require(actual_files == {paths[k] for k in execution_keys},
            "Incomplete run must preserve exactly the seven execution artifacts")
    require(run_manifest.get("complete") is False and run_manifest.get("failure_count") == 1,
            "Incomplete run manifest must record exactly one fatal stop")
    require(len(failures) == 1 and failures[0].get("event") == "STOP",
            "Expected exactly one preserved STOP event")
    failure = failures[0]
    require(failure.get("message") ==
            "B16 frozen feature-only design lacks both classes; STOP, do not reseed or extend",
            "Frozen STOP reason differs from the B16 class-diversity barrier")
    require(run_manifest.get("source_code_hashes") == frozen["source_code_hashes"],
            "Run manifest source bindings differ from freeze")

    manifest_path = Path(manifest_path)
    require(_sha256(manifest_path) == frozen["batch_manifest_sha256"],
            "Execution manifest bytes differ from the frozen batch hash")
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        manifest_rows = list(csv.DictReader(handle))
    by_id = {row["sim_id"]: row for row in manifest_rows}
    require(len(by_id) == len(manifest_rows) and set(frozen["included_ids"]).issubset(by_id),
            "Execution manifest has duplicate or missing frozen IDs")
    selected = [by_id[sim_id] for sim_id in frozen["included_ids"]]
    x = np.asarray([[float(row[name]) for name in ("P", "VX", "LS", "ST")] for row in selected], float)
    groups = [row["group_token"] for row in selected]

    repository_root = Path(__file__).resolve().parents[2]
    if str(repository_root) not in sys.path:
        sys.path.insert(0, str(repository_root))
    from src import week8_5_frozen_sample_efficiency_confirmation as w85
    from src.external_validation import runner as frozen_runner

    splits = _read_json(paths["split_manifest"])
    by_split = _split_checks(splits)
    expected_splits = frozen_runner.build_splits(groups, frozen)
    _require_exact(splits, expected_splits,
                   "Saved split manifest differs from runner.build_splits frozen certificate")
    completed_pairs = _completed_pairs_before_failure(splits, failure)
    completed_pair_set = set(completed_pairs)
    all_pairs = [(split["split_id"], arm) for split in splits for arm in ARMS]
    missing_pairs = [pair for pair in all_pairs if pair not in completed_pair_set]

    path_df = pd.read_csv(paths["path_manifest"])
    required_path = {"split_id", "arm", "query_order", "row_index", "sim_id", "selection_mode"}
    require(required_path.issubset(path_df.columns), "Path manifest schema incomplete")
    actual_path_pairs = set(path_df.groupby(["split_id", "arm"]).groups)
    require(actual_path_pairs == completed_pair_set, "Path pairs differ from the prefix before STOP")
    frozen_prefix_lengths = {}
    grouped_paths = {}
    for split_id, arm in completed_pairs:
        group = path_df[(path_df.split_id == split_id) & (path_df.arm == arm)].sort_values("query_order")
        _check_path_group(group, set(map(int, by_split[split_id]["train_indices"])))
        modes = group.selection_mode.astype(str).tolist()
        prefix = sum(mode == "frozen_maximin" for mode in modes)
        require(modes[:prefix] == ["frozen_maximin"] * prefix and
                "frozen_maximin" not in modes[prefix:], "Frozen seed rows are not a prefix")
        frozen_prefix_lengths[(split_id, arm)] = prefix
        grouped_paths[(split_id, arm)] = group
    for split_id in {pair[0] for pair in completed_pairs}:
        if all((split_id, arm) in completed_pair_set for arm in ARMS):
            control16 = grouped_paths[(split_id, CONTROL)].row_index.astype(int).tolist()[:16]
            same16 = grouped_paths[(split_id, ATTRIBUTION)].row_index.astype(int).tolist()[:16]
            require(frozen_prefix_lengths[(split_id, CONTROL)] == 16 and
                    frozen_prefix_lengths[(split_id, ATTRIBUTION)] == 16 and control16 == same16,
                    "Completed control and same-B16 paths do not share frozen B16")
            n = frozen_prefix_lengths[(split_id, CHALLENGER)]
            require(8 <= n <= 16 and
                    grouped_paths[(split_id, CHALLENGER)].row_index.astype(int).tolist()[:n] == control16[:n],
                    "Completed Candidate B path violates its frozen early8/extension prefix")

    pred = pd.read_csv(paths["per_budget_predictions"])
    required_pred = {"split_id", "repeat", "fold", "arm", "budget", "row_index",
                     "sim_id", "truth", "probability"}
    require(required_pred.issubset(pred.columns), "Prediction schema incomplete")
    require(not pred.duplicated(["split_id", "arm", "budget", "row_index"]).any(),
            "Duplicate held-out prediction")
    require(np.isfinite(pred.probability.to_numpy(float)).all() and pred.probability.between(0, 1).all(),
            "Invalid prediction probability")
    actual_groups = set(pred.groupby(["split_id", "arm", "budget"]).groups)
    expected_completed_groups = {(s, a, b) for s, a in completed_pairs for b in BUDGETS}
    require(actual_groups == expected_completed_groups, "Predictions differ from the complete prefix before STOP")
    for (split_id, _arm, _budget), group in pred.groupby(["split_id", "arm", "budget"], sort=False):
        _check_prediction_group(group, set(map(int, by_split[split_id]["test_indices"])))
    id_map = pred.groupby("row_index").agg(sim_ids=("sim_id", "nunique"), truths=("truth", "nunique"),
                                            sim_id=("sim_id", "first"), truth=("truth", "first"))
    require(set(id_map.index.astype(int)) == set(range(136)) and (id_map.sim_ids == 1).all() and
            (id_map.truths == 1).all(), "Partial predictions do not provide consistent truth for all 136 IDs")
    row_to_id = {int(i): str(row.sim_id) for i, row in id_map.iterrows()}
    _require_exact([row_to_id[i] for i in range(136)], list(frozen["included_ids"]),
                   "Saved prediction row_index/sim_id mapping differs from frozen included_ids order")
    require(all(str(row.sim_id) == row_to_id[int(row.row_index)] for row in path_df.itertuples()),
            "Path row index/simulation ID mapping differs from predictions")
    labels = {int(i): int(row.truth) for i, row in id_map.iterrows()}

    recomputed_b16 = {}
    for split_id, arm in completed_pairs:
        if split_id not in recomputed_b16:
            seed = w85.seed_u32(w85.seed_key("run", split_id, "initial_design"))
            local = _maximin_b16(x, by_split[split_id]["train_indices"], seed)
            bound = frozen_runner.feature_only_maximin(x, by_split[split_id]["train_indices"], seed)
            _require_exact(local, bound, "Independent and frozen feature-only maximin B16 differ")
            recomputed_b16[split_id] = bound
        frozen16 = recomputed_b16[split_id]
        actual = grouped_paths[(split_id, arm)].row_index.astype(int).tolist()
        if arm in {CONTROL, ATTRIBUTION}:
            _require_exact(actual[:16], frozen16,
                           "Completed control/same-B16 initial design differs from recomputed frozen B16")
        else:
            expected_length = _candidate_start_length(frozen16, labels)
            require(frozen_prefix_lengths[(split_id, arm)] == expected_length,
                    "Candidate B frozen prefix did not stop at the first two-class prefix")
            _require_exact(actual[:expected_length], frozen16[:expected_length],
                           "Candidate B early8/sequential extension differs from recomputed frozen B16")

    diagnostics = pd.read_csv(paths["fit_diagnostics"])
    require({"split_id", "arm", "budget"}.issubset(diagnostics.columns), "Fit diagnostic schema incomplete")
    for split_id, arm in completed_pairs:
        group = diagnostics[(diagnostics.split_id == split_id) & (diagnostics.arm == arm)]
        prefix = frozen_prefix_lengths[(split_id, arm)]
        expected = list(range(prefix, 16)) + list(BUDGETS) if arm == CHALLENGER else list(BUDGETS)
        require(sorted(group.budget.astype(int).tolist()) == expected,
                "Fit diagnostics do not cover every fit in a completed path")
    require(set(diagnostics.groupby(["split_id", "arm"]).groups) == completed_pair_set,
            "Fit diagnostics include a noncompleted split-arm")
    for event in fallbacks:
        require(event.get("split_id") in by_split and event.get("arm") in ARMS and
                isinstance(event.get("budget"), int) and event.get("event"), "Malformed fallback event")
    fallback_keys = {(e["split_id"], e["arm"], int(e["budget"]), e["event"]) for e in fallbacks}
    for row in path_df[path_df.selection_mode.astype(str).str.endswith("fallback")].itertuples():
        require((row.split_id, row.arm, int(row.query_order) - 1, row.selection_mode) in fallback_keys,
                "Selection fallback is absent from fallback_events")
    if "fallback_status" in diagnostics.columns:
        used = diagnostics[~diagnostics.fallback_status.astype(str).str.lower().isin(
            {"", "none", "not_used", "nan"})]
        for row in used.itertuples():
            require((row.split_id, row.arm, int(row.budget), "optimizer_fallback") in fallback_keys,
                    "Optimizer fallback is absent from fallback_events")

    # Reproduce only the exact failed frozen B16. No alternative seed or rescue is evaluated.
    seed = w85.seed_u32(w85.seed_key("run", failure["split_id"], "initial_design"))
    frozen16 = _maximin_b16(x, by_split[failure["split_id"]]["train_indices"], seed)
    _require_exact(frozen16,
                   frozen_runner.feature_only_maximin(x, by_split[failure["split_id"]]["train_indices"], seed),
                   "Failed-fold independent and frozen maximin B16 differ")
    require(len({labels[i] for i in frozen16}) == 1,
            "Saved prediction truth does not reproduce the frozen B16 single-class STOP")

    class_counts = id_map.truth.astype(int).value_counts().sort_index()
    missing_analysis_keys = sorted(set(paths) - execution_keys)
    return {
        "status": "INCOMPLETE_FROZEN_STOP",
        "forensic_quality": "PASS",
        "scientific_inference_status": "NOT_COMPUTED_INCOMPLETE_RUN",
        "failure": failure,
        "failure_reproduction": {"split_id": failure["split_id"], "initial_design_size": 16,
                                 "unique_class_count": 1, "seed_namespace": frozen["initial_design_seed_namespace"],
                                 "alternative_seeds_or_rescue_evaluated": False,
                                 "truth_source": "deduplicated saved held-out prediction truth only"},
        "partial_coverage": {
            "completed_split_arm_pairs": len(completed_pairs),
            "planned_split_manifest_entries": 100,
            "executed_complete_splits_with_all_three_arms": len(completed_pairs) // 3,
            "completed_split_arm_budget_groups": len(expected_completed_groups),
            "path_rows": len(path_df), "prediction_rows": len(pred),
            "diagnostic_rows": len(diagnostics), "fallback_events": len(fallbacks),
            "missing_split_arm_pairs": [{"split_id": s, "arm": a, "missing_budget_range": [16, 80],
                                          "missing_budget_count": 65} for s, a in missing_pairs],
            "missing_split_arm_pair_count": len(missing_pairs),
            "missing_split_arm_budget_group_count": len(missing_pairs) * 65,
            "analysis_artifacts_absent_by_design_after_stop": missing_analysis_keys,
        },
        "included_class_balance_from_deduplicated_prediction_truth": {
            "class_0": int(class_counts.get(0, 0)), "class_1": int(class_counts.get(1, 0)),
            "total": int(class_counts.sum()), "all_136_covered": True,
            "withheld_outcomes_accessed": False,
        },
        "artifact_sha256": {name: _sha256(paths[name]) for name in sorted(execution_keys)},
        "frozen_binding_checks": {
            "batch_manifest_sha256_matches": True,
            "prediction_row_index_to_included_id_order_matches": True,
            "saved_split_manifest_equals_runner_build_splits": True,
            "completed_split_b16_recomputed_count": len(recomputed_b16),
            "completed_control_and_same_b16_paths_match_recomputed_seed": True,
            "completed_candidate_b_prefixes_stop_at_first_two_class_prefix": True,
        },
        "fallback_categories": {
            "event_counts": dict(sorted(Counter(str(event["event"]) for event in fallbacks).items())),
            "optimizer_status_counts": dict(sorted(Counter(str(event.get("status")) for event in fallbacks
                                                            if event.get("event") == "optimizer_fallback").items())),
        },
        "partial_primary_contrasts_computed": False,
        "guardrails_or_rankings_computed": False,
        "exploratory_metrics_computed": False,
        "oracle_opened_by_qc": False,
        "methodological_repair_or_retry_authorized": False,
        "information_barrier_scope": {
            "artifact_verified": "completed selections are training-only and completed predictions are held-out-only",
            "accepted_source_audit": "frozen runner masks unrevealed labels and held-out selector features",
            "limitation": "saved CSVs cannot independently prove in-memory access behavior",
        },
    }


def validate(freeze_path: Path, output_root: Path, manifest_path: Path) -> dict:
    freeze_path, output_root = Path(freeze_path), Path(output_root)
    require(_sha256(freeze_path) == EXPECTED_FREEZE_SHA256, "Frozen addendum SHA-256 drift")
    frozen = _read_json(freeze_path)
    require(tuple(frozen["arms"]) == ARMS, "Frozen arm set drift")
    require(tuple(frozen["exact_feasible_budgets"]) == BUDGETS, "Frozen budget grid drift")
    require(int(frozen["repeat_count"]) == 20 and len(frozen["included_ids"]) == 136,
            "Frozen repeat or included-cohort count drift")
    locations = frozen["output_locations"]
    require(len(locations) == 15, "Frozen output map must contain exactly 15 artifacts")
    paths = {name: (output_root / rel).resolve() for name, rel in locations.items()}
    root = output_root.resolve()
    require(all(path.is_relative_to(root) for path in paths.values()),
            "Frozen output location escapes output root")
    execution_keys = {"split_manifest", "path_manifest", "per_budget_predictions",
                      "fit_diagnostics", "failure_events", "fallback_events", "run_manifest"}
    require(all(paths[key].is_file() for key in execution_keys), "An execution artifact is missing")
    run_manifest = _read_json(paths["run_manifest"])
    require(run_manifest.get("complete") is False,
            "This bounded checker is only for the recorded incomplete frozen STOP")
    return _validate_incomplete(frozen, paths, output_root, manifest_path, run_manifest,
                                _read_json(paths["failure_events"]),
                                _read_json(paths["fallback_events"]))


def write_evidence(result: dict, record_dir: Path) -> None:
    record_dir = Path(record_dir)
    record_dir.mkdir(parents=True, exist_ok=True)
    json_path = record_dir / "QC_VALIDATION.json"
    md_path = record_dir / "QC_SUMMARY.md"
    with json_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    require(result["status"] == "INCOMPLETE_FROZEN_STOP", "Unexpected QC result type")
    coverage = result["partial_coverage"]
    balance = result["included_class_balance_from_deduplicated_prediction_truth"]
    text = (
            "# Frozen external execution QC\n\n"
            "Execution status: **INCOMPLETE — FROZEN STOP**\n"
            "Forensic artifact quality: **PASS**\n\n"
            f"The locked run stopped at `{result['failure']['split_id']}` / "
            f"`{result['failure']['arm']}` because its frozen feature-only B16 contained one class. "
            "The saved included-cohort prediction truths reproduce that barrier. No reseed, rescue, retry, "
            "method repair, or alternative design was evaluated.\n\n"
            f"Before STOP, {coverage['completed_split_arm_pairs']} split-arm paths and "
            f"{coverage['completed_split_arm_budget_groups']} full budget groups completed, producing "
            f"{coverage['prediction_rows']} held-out prediction rows. Logged fallbacks: "
            f"{coverage['fallback_events']}.\n\n"
            f"Deduplicated included-cohort truth coverage is 136/136: class 0 = {balance['class_0']}, "
            f"class 1 = {balance['class_1']}. QC did not open the oracle or any withheld outcome.\n\n"
            "No partial endpoint, contrast, confidence interval, guardrail decision, ranking, or exploratory "
            "metric was computed. The STOP is a frozen design-evaluation outcome, not an implementation defect.\n"
    )
    with md_path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--record-dir", required=True, type=Path)
    args = parser.parse_args()
    result = validate(args.freeze, args.output_root, args.manifest)
    write_evidence(result, args.record_dir)
    print(f"{result['status']}: frozen external execution QC")


if __name__ == "__main__":
    main()
