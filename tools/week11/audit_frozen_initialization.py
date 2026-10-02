"""Post-hoc audit of the 100 already-frozen feature-only B16 designs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd


HEADLINE = "POST-HOC EXPLORATORY — NOT PRE-REGISTERED CONFIRMATORY EVIDENCE"
FEATURES = ("P", "VX", "LS", "ST")


class AuditError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def single_class_probability(n0: int, n1: int, sample_size: int = 16) -> float:
    """Exact uniform-without-replacement reference for one fixed class pool."""
    require(n0 >= 0 and n1 >= 0 and sample_size > 0 and n0 + n1 >= sample_size,
            "Invalid hypergeometric population")
    numerator = (math.comb(n0, sample_size) if n0 >= sample_size else 0)
    numerator += math.comb(n1, sample_size) if n1 >= sample_size else 0
    return numerator / math.comb(n0 + n1, sample_size)


def _histogram(values: list[int]) -> dict[str, int]:
    return {str(value): values.count(value) for value in sorted(set(values))}


def _distribution(values: list[int]) -> dict:
    array = np.asarray(values, int)
    return {"minimum": int(array.min()), "median": float(np.median(array)),
            "maximum": int(array.max()), "histogram": _histogram(values)}


def _load_truth(prediction_path: Path, included_ids: list[str]) -> np.ndarray:
    predictions = pd.read_csv(prediction_path, usecols=["row_index", "sim_id", "truth"])
    require(set(predictions.truth.astype(int)) <= {0, 1}, "Saved truth is not binary")
    grouped = predictions.groupby("row_index").agg(
        id_count=("sim_id", "nunique"), truth_count=("truth", "nunique"),
        sim_id=("sim_id", "first"), truth=("truth", "first"))
    require(set(grouped.index.astype(int)) == set(range(len(included_ids))),
            "Saved predictions do not cover every included row index")
    require((grouped.id_count == 1).all() and (grouped.truth_count == 1).all(),
            "Saved prediction identity/truth is inconsistent")
    ordered = grouped.loc[list(range(len(included_ids)))]
    require(ordered.sim_id.astype(str).tolist() == included_ids,
            "Saved prediction IDs differ from frozen included-ID order")
    return ordered.truth.to_numpy(int)


def audit(freeze_path: Path, manifest_path: Path, split_path: Path,
          prediction_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    freeze = json.loads(Path(freeze_path).read_text(encoding="utf-8"))
    require(sha256(manifest_path) == freeze["batch_manifest_sha256"],
            "Manifest bytes differ from frozen binding")
    with Path(manifest_path).open("r", encoding="utf-8-sig", newline="") as handle:
        manifest_rows = list(csv.DictReader(handle))
    by_id = {row["sim_id"]: row for row in manifest_rows}
    require(len(by_id) == len(manifest_rows), "Duplicate manifest ID")
    included_ids = list(freeze["included_ids"])
    require(len(included_ids) == 136 and set(included_ids).issubset(by_id),
            "Frozen included cohort is unavailable")
    selected = [by_id[sim_id] for sim_id in included_ids]
    x = np.asarray([[float(row[name]) for name in FEATURES] for row in selected], float)
    groups = [row["group_token"] for row in selected]
    require(np.isfinite(x).all() and (x[:, :3] > 0).all(), "Invalid included feature matrix")
    labels = _load_truth(prediction_path, included_ids)

    repository_root = Path(__file__).resolve().parents[2]
    if str(repository_root) not in sys.path:
        sys.path.insert(0, str(repository_root))
    from src.external_validation import runner

    saved_splits = json.loads(Path(split_path).read_text(encoding="utf-8"))
    expected_splits = runner.build_splits(groups, freeze)
    require(saved_splits == expected_splits and len(saved_splits) == 100,
            "Saved split certificate differs from frozen runner reconstruction")

    rows = []
    train_minority, design_minority = [], []
    for split in saved_splits:
        train = np.asarray(split["train_indices"], int)
        train_labels = labels[train]
        train0, train1 = int((train_labels == 0).sum()), int((train_labels == 1).sum())
        seed = runner._initial_seed(freeze, split)
        design = runner.feature_only_maximin(x, train, seed)
        design_labels = labels[np.asarray(design, int)]
        b0, b1 = int((design_labels == 0).sum()), int((design_labels == 1).sum())
        probability = single_class_probability(train0, train1, 16)
        train_minority.append(min(train0, train1))
        design_minority.append(min(b0, b1))
        rows.append({
            "evidence_status": HEADLINE,
            "split_id": split["split_id"], "repeat": int(split["repeat"]),
            "fold": int(split["fold"]), "split_seed": int(split["split_seed"]),
            "train_size": len(train), "train_class_0": train0, "train_class_1": train1,
            "train_has_both_classes": train0 > 0 and train1 > 0,
            "b16_class_0": b0, "b16_class_1": b1,
            "b16_has_both_classes": b0 > 0 and b1 > 0,
            "uniform16_single_class_probability": probability,
        })
    split_table = pd.DataFrame(rows)

    logh = np.log(x[:, 0]) - 0.5 * np.log(x[:, 1]) - 1.5 * np.log(x[:, 2])
    feature_rows = []
    feature_units = {"P": "W", "VX": "m/s", "LS": "m", "ST": "K", "logh": "frozen formula"}
    values = {**{name: x[:, i] for i, name in enumerate(FEATURES)}, "logh": logh}
    for class_value in (0, 1):
        mask = labels == class_value
        for feature in (*FEATURES, "logh"):
            data = values[feature][mask]
            feature_rows.append({
                "evidence_status": HEADLINE, "class_value": class_value,
                "class_count": int(mask.sum()), "feature": feature,
                "unit": feature_units[feature], "minimum": float(data.min()),
                "median": float(np.median(data)), "maximum": float(data.max()),
            })
    feature_table = pd.DataFrame(feature_rows)

    per_repeat = []
    for repeat, group in split_table.groupby("repeat", sort=True):
        per_repeat.append({"repeat": int(repeat), "split_count": len(group),
                           "single_class_b16_count": int((~group.b16_has_both_classes).sum())})
    expected_failures = float(split_table.uniform16_single_class_probability.sum())
    summary = {
        "headline": HEADLINE,
        "scope": "MECHANISM_DIAGNOSTIC_OF_EXACTLY_100_EXISTING_FROZEN_B16_DESIGNS",
        "included_count": 136, "included_class_0": int((labels == 0).sum()),
        "included_class_1": int((labels == 1).sum()),
        "frozen_split_count": len(split_table),
        "training_pools_with_both_classes": int(split_table.train_has_both_classes.sum()),
        "single_class_b16_count": int((~split_table.b16_has_both_classes).sum()),
        "two_class_b16_count": int(split_table.b16_has_both_classes.sum()),
        "training_pool_minority_count_distribution": _distribution(train_minority),
        "b16_minority_count_distribution": _distribution(design_minority),
        "per_repeat": per_repeat,
        "uniform16_without_replacement_reference": {
            "formula": "(C(n0,16)+C(n1,16))/C(N,16)",
            "sum_probability_across_fixed_100_pools": expected_failures,
            "interpretation": "descriptive expectation only; fixed pools are not asserted independent",
            "p_value_computed": False,
        },
        "frozen_logh_formula": "log(P) - 0.5*log(VX) - 1.5*log(LS)",
        "significance_tests_or_cutpoint_search": False,
        "new_seeds_or_designs_or_models": False,
        "oracle_or_withheld_outcomes_accessed": False,
    }
    validation = {
        "headline": HEADLINE, "status": "PASS",
        "checks": {
            "manifest_hash_matches_freeze": True,
            "saved_truth_covers_exact_136_included_ids": True,
            "saved_100_splits_equal_runner_build_splits": True,
            "used_runner_initial_seed_and_feature_only_maximin": True,
            "enumerated_only_existing_100_splits": True,
            "no_oracle_or_withheld_input": True,
            "no_model_evaluator_or_prediction_execution": True,
            "no_alternate_seed_or_design": True,
            "no_confirmatory_endpoint_or_p_value": True,
        },
        "input_sha256": {
            "freeze": sha256(freeze_path), "manifest": sha256(manifest_path),
            "split_manifest": sha256(split_path), "saved_predictions": sha256(prediction_path),
        },
    }
    return split_table, feature_table, summary, validation


def write_outputs(output_dir: Path, split_table: pd.DataFrame, feature_table: pd.DataFrame,
                  summary: dict, validation: dict) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    split_table.to_csv(output_dir / "FROZEN_B16_SPLIT_AUDIT.csv", index=False, lineterminator="\n")
    feature_table.to_csv(output_dir / "INCLUDED_CLASS_CONDITIONED_INPUT_SUMMARY.csv",
                         index=False, lineterminator="\n")
    (output_dir / "POSTHOC_INITIALIZATION_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (output_dir / "VALIDATION.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    report = (
        f"# {HEADLINE}\n\n"
        "This is a mechanical mechanism diagnostic of the 100 initial designs fixed before label access. "
        "It is not a rerun, repair, alternative design, or confirmatory result.\n\n"
        f"All {summary['training_pools_with_both_classes']}/100 training pools contain both classes. "
        f"The frozen feature-only B16 contains one class in {summary['single_class_b16_count']}/100 splits "
        f"and both classes in {summary['two_class_b16_count']}/100 splits.\n\n"
        "For each fixed pool, the descriptive uniform-without-replacement reference is "
        "`(C(n0,16)+C(n1,16))/C(N,16)`. Summing those 100 probabilities gives "
        f"{summary['uniform16_without_replacement_reference']['sum_probability_across_fixed_100_pools']:.6f}. "
        "The fixed pools are not treated as independent trials, and no p-value is computed.\n\n"
        "The accompanying files contain per-split class counts, per-repeat failure counts, minority-count "
        "distributions, and included-only class-conditioned min/median/max input summaries. No significance "
        "test, cutpoint search, new seed, acquisition arm, model fit, prediction, endpoint, oracle read, or "
        "withheld-outcome access was performed. Interpretation and any future design decision remain separate.\n"
    )
    (output_dir / "POSTHOC_INITIALIZATION_REPORT.md").write_text(report, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--saved-predictions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    write_outputs(args.output_dir, *audit(args.freeze, args.manifest,
                                         args.split_manifest, args.saved_predictions))
    print("PASS: post-hoc frozen initialization audit")


if __name__ == "__main__":
    main()
