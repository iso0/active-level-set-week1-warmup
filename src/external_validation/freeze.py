"""Create the dataset-specific pre-label freeze without opening an oracle."""
from __future__ import annotations

import json
import math
from pathlib import Path

from .common import (ARMS, BUDGETS, GROUPING, PAIRED_INTERVAL_METHOD, PRIMARY,
                     SPLIT_CONSTRUCTION, core_hashes, encoded, environment,
                     read_digest_sidecar, require, sha, write_new, write_new_bytes)

DECISION_FIELDS = {
    "owner", "grouping", "split_construction", "repeat_count", "fold_count",
    "random_seeds", "exact_feasible_budgets", "paired_interval_method",
    "failure_fallback_rules", "output_locations", "included_ids",
    "owner_excluded_ids", "prelabel_fold_assignment",
}
FAILURE_FIELDS = {
    "insufficient_train_for_b80", "single_class_training", "b16_lacks_both_classes",
    "q20_no_opposite_class", "model_fit_failure", "optimizer_nonfinite",
}
OUTPUT_FIELDS = {
    "split_manifest", "path_manifest", "per_budget_predictions", "per_budget_metrics",
    "endpoints", "repeat_block_values", "repeat_block_contrasts", "checkpoints",
    "descriptive_first_crossings", "fit_diagnostics", "failure_events", "fallback_events",
    "run_manifest", "validation_report", "claim_ledger",
}
EXPECTED_FAILURE_RULES = {
    "insufficient_train_for_b80": "STOP_AND_RECORD", "single_class_training": "STOP_AND_RECORD",
    "b16_lacks_both_classes": "STOP_AND_RECORD", "q20_no_opposite_class": "STOP_AND_RECORD",
    "model_fit_failure": "STOP_AND_RECORD",
    "optimizer_nonfinite": "USE_FROZEN_INITIAL_KERNEL_FALLBACK_AND_RECORD",
}
OUTPUT_SUFFIXES = {
    "split_manifest": ".json", "path_manifest": ".csv", "per_budget_predictions": ".csv",
    "per_budget_metrics": ".csv", "endpoints": ".csv", "repeat_block_values": ".csv",
    "repeat_block_contrasts": ".csv", "checkpoints": ".csv",
    "descriptive_first_crossings": ".csv", "fit_diagnostics": ".csv",
    "failure_events": ".json", "fallback_events": ".json", "run_manifest": ".json",
    "validation_report": ".md", "claim_ledger": ".json",
}


def _load_verified_intake(path):
    path = Path(path)
    expected = read_digest_sidecar(str(path) + ".sha256")
    payload = path.read_bytes()
    require(sha(payload) == expected, "Intake report hash mismatch")
    report = json.loads(payload)
    require(report.get("stage") == "LABEL_BLIND", "Not a label-blind intake report")
    require(not report.get("blockers"), "Intake blockers must be resolved before freezing")
    return report, expected


def _validate_fold_certificate(assignments, repeats, included_rows):
    groups = {str(row["group_token"]) for row in included_rows}
    require(len(assignments) == repeats, "One pre-label fold assignment per repeat is required")
    minimum, canonical = len(included_rows), []
    for repeat, assignment in enumerate(assignments, 1):
        require(set(assignment) == {"repeat", "folds"} and assignment["repeat"] == repeat,
                "Fold-certificate repeat mismatch")
        folds = assignment["folds"]
        require(len(folds) == 5 and [x.get("fold") for x in folds] == [1, 2, 3, 4, 5],
                "Fold certificate must contain ordered folds 1-5")
        seen = []
        for fold in folds:
            require(set(fold) == {"fold", "test_group_tokens"} and fold["test_group_tokens"],
                    "Each fold needs explicit nonempty test-group tokens")
            seen.extend(map(str, fold["test_group_tokens"]))
        require(len(seen) == len(set(seen)) and set(seen) == groups,
                "Each included group must occur exactly once per repeat")
        normalized = []
        for fold in folds:
            test_groups = list(map(str, fold["test_group_tokens"]))
            selected = set(test_groups)
            test_count = sum(str(row["group_token"]) in selected for row in included_rows)
            train_count = len(included_rows) - test_count
            require(train_count >= 80, "Certified pre-label fold cannot support B80")
            minimum = min(minimum, train_count)
            normalized.append({"fold": fold["fold"], "test_group_tokens": test_groups,
                               "test_count": test_count, "train_count": train_count})
        canonical.append({"repeat": repeat, "folds": normalized})
    return canonical, minimum


def build_addendum(intake_path, decisions):
    require(set(decisions) == DECISION_FIELDS,
            f"Explicit dataset decisions required: {sorted(DECISION_FIELDS)}")
    report, intake_hash = _load_verified_intake(intake_path)
    require(str(decisions["owner"]).strip(), "Protocol owner is required")
    require(decisions["grouping"] == GROUPING, "Only frozen grouping 'group_token' is supported")
    require(decisions["split_construction"] == SPLIT_CONSTRUCTION,
            "Grouped stratification lacks a pre-label B80 certificate; preassign five group folds")
    repeats = decisions["repeat_count"]
    require(isinstance(repeats, int) and repeats >= 2, "At least two repeat blocks are required")
    require(decisions["fold_count"] == 5, "Frozen protocol requires five-fold pairing")
    seeds = decisions["random_seeds"]
    require(isinstance(seeds, list) and len(seeds) == repeats and len(set(seeds)) == len(seeds)
            and all(isinstance(v, int) for v in seeds), "One unique integer seed per repeat is required")
    require(decisions["exact_feasible_budgets"] == BUDGETS,
            "Frozen primary horizon is every integer budget B16-B80")
    require(decisions["paired_interval_method"] == PAIRED_INTERVAL_METHOD,
            "Unsupported paired interval estimator")
    require(decisions["failure_fallback_rules"] == EXPECTED_FAILURE_RULES,
            "Failure/fallback rules differ from supported frozen behavior")
    require(set(decisions["output_locations"]) == OUTPUT_FIELDS and
            all(str(v).strip() for v in decisions["output_locations"].values()),
            f"Exact output locations required: {sorted(OUTPUT_FIELDS)}")
    require(len(set(decisions["output_locations"].values())) == len(OUTPUT_FIELDS),
            "Every frozen output must have a distinct location")
    require(all(Path(decisions["output_locations"][key]).suffix.lower() == suffix
                for key, suffix in OUTPUT_SUFFIXES.items()),
            "Frozen output file extensions do not match their artifact types")

    valid_rows = report["technically_usable_rows"]
    eligible = {str(row["sim_id"]) for row in valid_rows}
    included = list(map(str, decisions["included_ids"]))
    owner_excluded = decisions["owner_excluded_ids"]
    require(len(included) == len(set(included)), "Duplicate included IDs")
    require(isinstance(owner_excluded, list) and all(set(x) == {"sim_id", "technical_reason"}
            and str(x["technical_reason"]).strip() for x in owner_excluded),
            "Owner exclusions require exactly sim_id and label-free technical_reason")
    owner_ids = [str(x["sim_id"]) for x in owner_excluded]
    require(len(owner_ids) == len(set(owner_ids)) and set(included).isdisjoint(owner_ids),
            "Included/owner-excluded IDs overlap or repeat")
    require(set(included) | set(owner_ids) == eligible,
            "Included plus owner exclusions must partition technically usable rows")
    included_rows = [row for row in valid_rows if str(row["sim_id"]) in set(included)]
    require(len(included_rows) == len(included), "Included IDs are not unique usable manifest rows")
    require(len(included) - math.ceil(len(included) / 5) >= 80,
            "B80 is impossible even under balanced five-fold allocation")
    certificate, minimum_train = _validate_fold_certificate(
        decisions["prelabel_fold_assignment"], repeats, included_rows)

    exclusions = [{"manifest_row": int(x["manifest_row"]), "sim_id": str(x["sim_id"]),
                   "technical_reasons": list(x["reasons"]), "source": "intake"}
                  for x in report["technical_exclusion_candidates"]]
    for item in owner_excluded:
        row_number = next(i for i, row in enumerate(report["manifest_rows"])
                          if str(row["sim_id"]) == str(item["sim_id"]))
        exclusions.append({"manifest_row": row_number, "sim_id": str(item["sim_id"]),
                           "technical_reasons": [str(item["technical_reason"])],
                           "source": "owner_prelabel"})
    require(len(included) + len(exclusions) == len(report["manifest_rows"]),
            "Every manifest row must be included or carry a technical exclusion")
    oracle_rows = [row for row in report["inventory"] if row["kind"] == "sealed_oracle"]
    require(len(oracle_rows) == 1 and oracle_rows[0]["status"] == "ok",
            "Exactly one intact sealed-oracle inventory row is required")
    oracle = {key: oracle_rows[0][key] for key in ("file_name", "byte_size", "sha256")}

    return {
        "schema_version": 1, "stage": "PRE_LABEL_DATASET_FREEZE", "label_accessed": False,
        "protocol_owner": decisions["owner"], "batch_manifest_sha256": report["manifest"]["sha256"],
        "intake_report_sha256": intake_hash,
        "original_manifest_ids": sorted({str(row["sim_id"]) for row in report["manifest_rows"]
                                         if str(row["sim_id"]).strip()}),
        "included_ids": included, "excluded_rows": exclusions,
        "usable_sample_count": len(included), "grouping": GROUPING,
        "split_construction": SPLIT_CONSTRUCTION, "repeat_count": repeats, "fold_count": 5,
        "random_seeds": seeds, "prelabel_fold_assignment": certificate,
        "minimum_training_pool_size": minimum_train, "exact_feasible_budgets": BUDGETS,
        "paired_interval_method": PAIRED_INTERVAL_METHOD,
        "q20_scaling_scope": "entire_evaluation_batch", "q20_tie_break": "stable_simulation_id",
        "initial_design_seed_namespace": "w85.seed_u32(w85.seed_key('run',split_id,'initial_design'))",
        "arms": list(ARMS), "primary_endpoint": PRIMARY,
        "failure_fallback_rules": EXPECTED_FAILURE_RULES, "sealed_oracle_inventory": oracle,
        "environment": environment(), "source_code_hashes": core_hashes(),
        "output_locations": decisions["output_locations"],
    }


def generate(intake_path, output_directory, decisions):
    output_directory = Path(output_directory)
    payload = build_addendum(intake_path, decisions)
    target = output_directory / "EXTERNAL_BATCH_FREEZE.json"
    write_new(target, payload)
    write_new_bytes(output_directory / "EXTERNAL_BATCH_FREEZE.sha256",
                    (sha(encoded(payload)) + "\n").encode("ascii"))
    return payload


def verify(path):
    path = Path(path)
    expected = read_digest_sidecar(path.with_name("EXTERNAL_BATCH_FREEZE.sha256"))
    require(sha(path.read_bytes()) == expected, "External batch freeze hash mismatch")
    payload = json.loads(path.read_bytes())
    require(payload.get("stage") == "PRE_LABEL_DATASET_FREEZE" and payload.get("label_accessed") is False,
            "Invalid pre-label freeze")
    require(tuple(payload.get("arms", ())) == ARMS and payload.get("primary_endpoint") == PRIMARY,
            "Frozen arm or endpoint mismatch")
    require(payload.get("exact_feasible_budgets") == BUDGETS, "Frozen budget grid mismatch")
    require(payload.get("grouping") == GROUPING and payload.get("split_construction") == SPLIT_CONSTRUCTION,
            "Unsupported split/grouping freeze")
    require(payload.get("paired_interval_method") == PAIRED_INTERVAL_METHOD,
            "Unsupported interval freeze")
    return payload
