"""Frozen external endpoints, paired repeat-block inference, and claim ledger."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import distance
from sklearn.preprocessing import StandardScaler

from .common import ARMS, BUDGETS, PAIRED_INTERVAL_METHOD, PRIMARY, require, write_new_bytes

CONTROL, CHALLENGER, ATTRIBUTION = ARMS
SUPPORTED_INTERVAL = PAIRED_INTERVAL_METHOD
SUPPORTED_Q_SCALING = "entire_evaluation_batch"


def boundary_flags(features, labels, test_indices, sim_ids, q_scaling_scope):
    require(q_scaling_scope == SUPPORTED_Q_SCALING,
            "Unsupported q20 scaling decision; owner amendment/implementation required")
    x = StandardScaler().fit_transform(np.asarray(features, float))
    labels = np.asarray(labels, int)
    dmat = distance.cdist(x, x)
    nearest_opposite = np.where(labels[:, None] != labels[None, :], dmat, np.inf).min(axis=1)
    require(np.isfinite(nearest_opposite).all(), "q20 undefined: evaluation batch lacks an opposite class")
    test = np.asarray(test_indices, int)
    order = np.lexsort((np.asarray(sim_ids, object)[test], nearest_opposite[test]))
    result = {}
    for q in (20, 30):
        count = int(np.ceil((q / 100.0) * len(test)))
        flag = np.zeros(len(test), dtype=bool)
        flag[order[:count]] = True
        result[q] = flag
    return result


def _metric(truth, probability):
    truth = np.asarray(truth, int)
    pred = np.asarray(probability, float) >= 0.5
    tp = int(((pred == 1) & (truth == 1)).sum())
    tn = int(((pred == 0) & (truth == 0)).sum())
    fp = int(((pred == 1) & (truth == 0)).sum())
    fn = int(((pred == 0) & (truth == 1)).sum())
    pos, neg = tp + fn, tn + fp
    recall = tp / pos if pos else 0.0
    specificity = tn / neg if neg else 0.0
    return {"row_count": len(truth), "accuracy": (tp + tn) / len(truth),
            "balanced_accuracy": (recall + specificity) / 2,
            "keyhole_recall": recall, "true_positive": tp, "true_negative": tn,
            "false_positive": fp, "false_negative": fn}


def metrics_from_predictions(run, features, labels, sim_ids, frozen):
    rows = []
    predictions = pd.DataFrame(run["predictions"])
    split_by_id = {x["split_id"]: x for x in run["split_manifest"]}
    require(len(split_by_id) == len(run["split_manifest"]), "Duplicate split IDs")
    required = {"split_id", "repeat", "fold", "arm", "budget", "row_index",
                "sim_id", "truth", "probability"}
    require(required.issubset(predictions.columns), "Prediction schema incomplete")
    require(np.isfinite(predictions.probability.to_numpy(float)).all(),
            "Nonfinite prediction probability")
    require(predictions.probability.between(0, 1).all(), "Prediction probability outside [0,1]")
    require(not predictions.duplicated(["split_id", "arm", "budget", "row_index"]).any(),
            "Duplicate per-test-ID prediction")
    expected_groups = {(split_id, arm, budget) for split_id in split_by_id
                       for arm in ARMS for budget in BUDGETS}
    actual_groups = set(predictions.groupby(["split_id", "arm", "budget"]).groups)
    require(actual_groups == expected_groups, "Incomplete arm/fold/budget prediction coverage")
    expected_split_ids = {f"external__r{repeat:03d}_f{fold:02d}"
                          for repeat in range(1, frozen["repeat_count"] + 1)
                          for fold in range(1, 6)} if "repeat_count" in frozen else set(split_by_id)
    require(set(split_by_id) == expected_split_ids, "Frozen repeat/fold split IDs are incomplete")
    for repeat in sorted({int(x["repeat"]) for x in split_by_id.values()}):
        members = [x for x in split_by_id.values() if int(x["repeat"]) == repeat]
        require(sorted(int(x["fold"]) for x in members) == [1, 2, 3, 4, 5],
                "Repeat does not contain folds 1-5")
        held_out = [int(index) for split in members for index in split["test_indices"]]
        require(len(held_out) == len(labels) and sorted(held_out) == list(range(len(labels))),
                "Each included ID must be held out exactly once per repeat")
    for (split_id, arm, budget), group in predictions.groupby(["split_id", "arm", "budget"], sort=True):
        split = split_by_id[split_id]
        require(set(group.row_index.astype(int)) == set(split["test_indices"]) and
                len(group) == len(split["test_indices"]), "Incomplete held-out prediction IDs")
        ordered = group.set_index("row_index").loc[split["test_indices"]].reset_index()
        expected_ids = [str(sim_ids[index]) for index in split["test_indices"]]
        expected_truth = [int(labels[index]) for index in split["test_indices"]]
        require(ordered.sim_id.astype(str).tolist() == expected_ids and
                ordered.truth.astype(int).tolist() == expected_truth,
                "Held-out IDs/truth differ from controlled evaluation inputs")
        flags = boundary_flags(features, labels, split["test_indices"], sim_ids,
                               frozen["q20_scaling_scope"])
        for subset, mask in (("full", np.ones(len(ordered), bool)),
                             ("q20", flags[20]), ("q30", flags[30])):
            if subset == "q20":
                require(set(ordered.truth.to_numpy()[mask].tolist()) == {0, 1},
                        "q20 has no representation of both classes; STOP under frozen failure rule")
            rows.append({"split_id": split_id, "repeat": split["repeat"],
                         "fold": split["fold"], "arm": arm, "budget": int(budget),
                         "subset": subset,
                         **_metric(ordered.truth.to_numpy()[mask],
                                   ordered.probability.to_numpy()[mask])})
    result = pd.DataFrame(rows)
    expected = len(split_by_id) * len(ARMS) * len(BUDGETS) * 3
    require(len(result) == expected, "Metric completeness failure")
    return result


def _aulc(group, metric, low, high):
    ordered = group[group.budget.between(low, high)].sort_values("budget")
    require(ordered.budget.tolist() == list(range(low, high + 1)), "AULC budget grid mismatch")
    return float(np.trapezoid(ordered[metric].to_numpy(float), ordered.budget) / (high - low))


def endpoint_table(metrics):
    specs = [
        ("q20_accuracy_AULC_B16_B80", "q20", "accuracy", 16, 80),
        ("q20_accuracy_AULC_B16_B40", "q20", "accuracy", 16, 40),
        ("q20_balanced_accuracy_AULC_B16_B40", "q20", "balanced_accuracy", 16, 40),
        ("q20_balanced_accuracy_AULC_B16_B80", "q20", "balanced_accuracy", 16, 80),
        ("q20_keyhole_recall_AULC_B16_B80", "q20", "keyhole_recall", 16, 80),
        ("q20_keyhole_recall_AULC_B16_B40", "q20", "keyhole_recall", 16, 40),
        ("q30_accuracy_AULC_B16_B80", "q30", "accuracy", 16, 80),
        ("q30_accuracy_AULC_B16_B40", "q30", "accuracy", 16, 40),
        ("q30_balanced_accuracy_AULC_B16_B80", "q30", "balanced_accuracy", 16, 80),
        ("q30_balanced_accuracy_AULC_B16_B40", "q30", "balanced_accuracy", 16, 40),
        ("q30_keyhole_recall_AULC_B16_B80", "q30", "keyhole_recall", 16, 80),
        ("q30_keyhole_recall_AULC_B16_B40", "q30", "keyhole_recall", 16, 40),
        ("full_accuracy_AULC_B16_B80", "full", "accuracy", 16, 80),
        ("full_accuracy_AULC_B16_B40", "full", "accuracy", 16, 40),
    ]
    rows = []
    for name, subset, metric, low, high in specs:
        part = metrics[metrics.subset.eq(subset)]
        for keys, group in part.groupby(["split_id", "repeat", "fold", "arm"], sort=True):
            split_id, repeat, fold, arm = keys
            rows.append({"endpoint": name, "split_id": split_id, "repeat": repeat,
                         "fold": fold, "arm": arm, "value": _aulc(group, metric, low, high)})
    for name, subset, metric, budget in (
        ("q20_keyhole_recall_B40", "q20", "keyhole_recall", 40),
        ("full_accuracy_B80", "full", "accuracy", 80),
    ):
        for row in metrics[metrics.subset.eq(subset) & metrics.budget.eq(budget)].itertuples():
            rows.append({"endpoint": name, "split_id": row.split_id, "repeat": row.repeat,
                         "fold": row.fold, "arm": row.arm, "value": getattr(row, metric)})
    return pd.DataFrame(rows)


def _interval(values, key, method):
    require(method == SUPPORTED_INTERVAL,
            "Unsupported paired interval decision; owner amendment/implementation required")
    values = np.asarray(values, float)
    require(len(values) > 1 and np.isfinite(values).all(), "Paired inference needs finite repeat blocks")
    seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "little") % (2 ** 32)
    rng = np.random.default_rng(seed)
    draws = values[rng.integers(0, len(values), size=(10_000, len(values)))].mean(axis=1)
    return float(values.mean()), float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))


def paired_inference(endpoints, frozen):
    counts = endpoints.groupby(["endpoint", "repeat", "arm"]).fold.nunique()
    require((counts == 5).all(), "Paired inference requires all five folds in every repeat-arm block")
    require(np.isfinite(endpoints.value.to_numpy(float)).all(), "Nonfinite endpoint value")
    repeat = endpoints.groupby(["endpoint", "repeat", "arm"], as_index=False).value.mean()
    wide = repeat.pivot(index=["endpoint", "repeat"], columns="arm", values="value").reset_index()
    rows = []
    for endpoint, group in wide.groupby("endpoint", sort=True):
        group = group.sort_values("repeat")
        for left, right, role in ((CHALLENGER, CONTROL, "challenger_vs_control"),
                                  (ATTRIBUTION, CONTROL, "same_B16_acquisition_attribution")):
            differences = (group[left] - group[right]).to_numpy(float)
            mean, low, high = _interval(differences, f"{endpoint}|{left}|{right}",
                                        frozen["paired_interval_method"])
            rows.append({"endpoint": endpoint, "contrast": f"{left}_minus_{right}",
                         "role": role, "mean_difference": mean, "ci95_lower": low,
                         "ci95_upper": high, "positive_repeat_blocks": int((differences > 0).sum()),
                         "zero_repeat_blocks": int((differences == 0).sum()),
                         "negative_repeat_blocks": int((differences < 0).sum()),
                         "repeat_blocks": len(differences)})
    return pd.DataFrame(rows)


def checkpoint_table(metrics):
    keep = metrics[metrics.budget.isin((16, 40, 80))]
    return keep.groupby(["arm", "subset", "budget"], as_index=False)[
        ["accuracy", "balanced_accuracy", "keyhole_recall"]].mean()


def claim_ledger(contrasts, failures):
    def row(endpoint, role):
        found = contrasts[(contrasts.endpoint == endpoint) & (contrasts.role == role)]
        require(len(found) == 1, f"Missing frozen contrast {endpoint}/{role}")
        return found.iloc[0]
    primary = row("q20_accuracy_AULC_B16_B80", "challenger_vs_control")
    recall = row("q20_keyhole_recall_B40", "challenger_vs_control")
    full = row("full_accuracy_B80", "challenger_vs_control")
    attribution = row("q20_accuracy_AULC_B16_B80", "same_B16_acquisition_attribution")
    external = bool(primary.mean_difference > 0 and primary.ci95_lower > 0 and
                    recall.mean_difference >= -0.03 and full.mean_difference >= -0.01 and
                    not failures)
    replacement = bool(external and primary.mean_difference >= 0.01)
    same_b16_positive = bool(attribution.mean_difference > 0 and attribution.ci95_lower > 0 and not failures)
    pure = bool(external and same_b16_positive)
    return {
        "primary_endpoint": PRIMARY,
        "external_confirmation": {"pass": external,
            "requires": "primary CI entirely above zero plus frozen recall/accuracy guardrails"},
        "incumbent_replacement": {"pass": replacement,
            "requires": "external confirmation and primary mean difference >= +0.01"},
        "pure_acquisition_attribution": {"pass": pure,
            "same_B16_positive_evidence": same_b16_positive,
            "requires": "external confirmation plus same-B16 mean and CI entirely above zero"},
        "failures": failures,
    }


def analyze(run, features, labels, sim_ids, frozen):
    require(run["arms"] == list(ARMS) and run["primary_endpoint"] == PRIMARY,
            "Run scientific settings drift")
    require(run.get("complete") is True and not run["failures"],
            "Incomplete execution cannot enter frozen inference")
    metrics = metrics_from_predictions(run, features, labels, sim_ids, frozen)
    endpoints = endpoint_table(metrics)
    contrasts = paired_inference(endpoints, frozen)
    ledger = claim_ledger(contrasts, run["failures"])
    repeat_values = endpoints.groupby(["endpoint", "repeat", "arm"], as_index=False).value.mean()
    crossings = descriptive_first_crossings(metrics)
    return {"metrics": metrics, "endpoints": endpoints, "contrasts": contrasts,
            "repeat_block_values": repeat_values, "checkpoints": checkpoint_table(metrics),
            "descriptive_first_crossings": crossings, "claim_ledger": ledger}


def descriptive_first_crossings(metrics):
    """Mean-curve descriptions only; never a simulator-savings guarantee."""
    rows = []
    curves = metrics[metrics.subset.eq("q20")].groupby(["arm", "budget"]).accuracy.mean()
    control = curves.loc[CONTROL]
    for arm in (CHALLENGER, ATTRIBUTION):
        candidate = curves.loc[arm]
        for budget in (24, 32, 40, 60):
            level = float(control.loc[budget])
            reached = candidate[(candidate >= level - 1e-12) & (candidate.index >= 16)]
            first = None if reached.empty else int(reached.index.min())
            rows.append({"arm": arm, "control_target_budget": budget,
                         "control_q20_accuracy": level, "candidate_first_crossing_budget": first,
                         "descriptive_budget_difference": None if first is None else budget - first,
                         "interpretation": "descriptive_mean_curve_only_not_guaranteed_savings"})
    return pd.DataFrame(rows)


def write_analysis(result, output_directory):
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    for name in ("metrics", "endpoints", "contrasts", "checkpoints"):
        result[name].to_csv(output_directory / f"{name}.csv", index=False, lineterminator="\n")
    (output_directory / "CLAIM_LEDGER.json").write_text(
        json.dumps(result["claim_ledger"], indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_frozen_outputs(result, frozen, output_root):
    """Write analysis artifacts only to paths declared in the pre-label addendum."""
    output_root = Path(output_root).resolve()
    mapping = {"per_budget_metrics": result["metrics"], "endpoints": result["endpoints"],
               "repeat_block_values": result["repeat_block_values"],
               "repeat_block_contrasts": result["contrasts"], "checkpoints": result["checkpoints"],
               "descriptive_first_crossings": result["descriptive_first_crossings"],
               "claim_ledger": result["claim_ledger"]}
    for key, value in mapping.items():
        destination = (output_root / frozen["output_locations"][key]).resolve()
        require(destination.is_relative_to(output_root), "Output location escapes declared root")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, pd.DataFrame):
            require(destination.suffix.lower() == ".csv", f"{key} must use a .csv location")
            write_new_bytes(destination, value.to_csv(index=False, lineterminator="\n").encode())
        else:
            write_new_bytes(destination, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())
    report = (output_root / frozen["output_locations"]["validation_report"]).resolve()
    require(report.is_relative_to(output_root), "Output location escapes declared root")
    report.parent.mkdir(parents=True, exist_ok=True)
    ledger = result["claim_ledger"]
    primary = result["contrasts"][(result["contrasts"].endpoint == "q20_accuracy_AULC_B16_B80") &
                                  (result["contrasts"].role == "challenger_vs_control")].iloc[0]
    attribution = result["contrasts"][(result["contrasts"].endpoint == "q20_accuracy_AULC_B16_B80") &
                                      (result["contrasts"].role == "same_B16_acquisition_attribution")].iloc[0]
    recall = result["contrasts"][(result["contrasts"].endpoint == "q20_keyhole_recall_B40") &
                                 (result["contrasts"].role == "challenger_vs_control")].iloc[0]
    full = result["contrasts"][(result["contrasts"].endpoint == "full_accuracy_B80") &
                               (result["contrasts"].role == "challenger_vs_control")].iloc[0]
    write_new_bytes(report, (
        "# Frozen external validation report\n\n"
        f"Primary mean difference: {primary.mean_difference:+.6f} "
        f"(95% CI [{primary.ci95_lower:+.6f}, {primary.ci95_upper:+.6f}]); "
        f"positive repeat blocks {int(primary.positive_repeat_blocks)}/{int(primary.repeat_blocks)}.\n\n"
        f"Same-B16 attribution mean difference: {attribution.mean_difference:+.6f} "
        f"(95% CI [{attribution.ci95_lower:+.6f}, {attribution.ci95_upper:+.6f}]).\n\n"
        f"B40 q20 Keyhole-recall change: {recall.mean_difference:+.6f}.\n\n"
        f"B80 full-test accuracy change: {full.mean_difference:+.6f}.\n\n"
        f"- External confirmation: {'PASS' if ledger['external_confirmation']['pass'] else 'FAIL'}\n"
        f"- Incumbent replacement: {'PASS' if ledger['incumbent_replacement']['pass'] else 'FAIL'}\n"
        f"- Pure acquisition attribution: {'PASS' if ledger['pure_acquisition_attribution']['pass'] else 'FAIL'}\n"
        f"- Recorded failures: {len(ledger['failures'])}\n").encode())
