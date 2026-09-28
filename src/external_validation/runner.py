"""Locked three-arm execution. This is the only layer allowed to open labels."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from scipy.spatial import distance
from sklearn.preprocessing import StandardScaler

from .common import (ARMS, BUDGETS, PRIMARY, ROOT, check_environment, check_hashes, core_hashes,
                     committed, require, sha, write_new_bytes)
from .freeze import verify as verify_freeze

ORACLE_COLUMNS = ("sim_id", "has_keyhole")


def bind_real_implementations():
    """Import and validate the frozen primitives without invoking historical loaders."""
    from src import week8_5_frozen_sample_efficiency_confirmation as w85
    from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
    from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
    from src import week9_phase1_20_acquisition_search as search
    from src import week9_phase1_21_simplification_replication as p121
    required = (w85.initial_design, p11.fit_physics_mean, p13.fit_hybrid,
                p13.components, search.argbest, search.make_band_coverage,
                p121.coverage_then_margin)
    require(all(callable(x) for x in required), "Frozen implementation binding failed")
    return {"w85": w85, "p11": p11, "p13": p13, "search": search, "p121": p121}


def preflight_execution(freeze_path, freeze_commit, output_root):
    """Complete every non-oracle gate before the sealed oracle path is touched."""
    frozen = verify_freeze(freeze_path)
    committed(freeze_path, freeze_commit)
    committed(Path(freeze_path).with_name("EXTERNAL_BATCH_FREEZE.sha256"), freeze_commit)
    require(frozen["source_code_hashes"] == core_hashes(), "Frozen source hash set/value drift")
    check_hashes(frozen["source_code_hashes"])
    for relative in frozen["source_code_hashes"]:
        committed(ROOT / relative, freeze_commit)
    check_environment(frozen["environment"])
    output_root = Path(output_root).resolve()
    for relative in frozen["output_locations"].values():
        destination = (output_root / relative).resolve()
        require(destination.is_relative_to(output_root), "Output location escapes declared root")
        require(not destination.exists(), f"Frozen output already exists: {destination}")
    return frozen


def open_oracle(path, frozen):
    """After preflight, verify the custodian digest/size and open one explicit oracle."""
    path = Path(path)
    require(not path.is_symlink() and path.is_file(), "Oracle must be one explicit regular file")
    expected = frozen["sealed_oracle_inventory"]
    require(path.name == expected["file_name"], "Oracle filename differs from frozen inventory")
    payload = path.read_bytes()
    require(len(payload) == int(expected["byte_size"]) and sha(payload) == expected["sha256"],
            "Oracle size or SHA-256 differs from frozen custodian inventory")
    with io.StringIO(payload.decode("utf-8-sig"), newline="") as handle:
        reader = csv.DictReader(handle)
        require(tuple(reader.fieldnames or ()) == ORACLE_COLUMNS, "Unexpected oracle schema")
        rows = list(reader)
    allowed = set(frozen["original_manifest_ids"])
    mapping = {}
    for row in rows:
        require(row["sim_id"] in allowed and row["sim_id"] not in mapping,
                "Oracle ID is unknown or duplicated")
        require(row["has_keyhole"] in {"0", "1"}, "Oracle labels must be binary 0/1")
        mapping[row["sim_id"]] = int(row["has_keyhole"])
    require(set(frozen["included_ids"]).issubset(mapping), "Oracle is missing a frozen included ID")
    return {sim_id: mapping[sim_id] for sim_id in frozen["included_ids"]}


def build_splits(groups, frozen):
    """Materialize the exact label-free, owner-approved group-fold certificate."""
    groups = np.asarray(groups, object)
    require(len(groups) == frozen["usable_sample_count"], "Split input length mismatch")
    result = []
    for assignment, seed in zip(frozen["prelabel_fold_assignment"], frozen["random_seeds"]):
        repeat = assignment["repeat"]
        for item in assignment["folds"]:
            fold = item["fold"]
            test_groups = set(item["test_group_tokens"])
            test = np.flatnonzero(np.isin(groups, list(test_groups)))
            train = np.flatnonzero(~np.isin(groups, list(test_groups)))
            require(len(test) == item["test_count"] and len(train) == item["train_count"],
                    "Manifest groups differ from frozen fold certificate")
            require(len(train) >= 80, "A generated training pool cannot support B80")
            result.append({"split_id": f"external__r{repeat:03d}_f{fold:02d}",
                           "repeat": repeat, "fold": fold,
                           "train_indices": train.astype(int).tolist(),
                           "test_indices": test.astype(int).tolist(), "split_seed": seed})
    return result


def feature_only_maximin(x, pool, seed, size=16):
    """Frozen maximin mechanics without the historical function's label read."""
    pool = np.asarray(pool, int)
    require(len(pool) >= size, "Training pool is smaller than initial design")
    scaled = StandardScaler().fit_transform(np.asarray(x, float)[pool])
    rng = np.random.default_rng(int(seed))
    chosen_local = [int(rng.integers(len(pool)))]
    while len(chosen_local) < size:
        remaining = np.setdiff1d(np.arange(len(pool)), chosen_local, assume_unique=True)
        nearest = distance.cdist(scaled[remaining], scaled[chosen_local]).min(axis=1)
        best = nearest.max()
        ties = remaining[np.isclose(nearest, best, rtol=1e-12, atol=1e-14)]
        chosen_local.append(int(ties[np.argmin(pool[ties])]))
    return pool[np.asarray(chosen_local)].astype(int).tolist()


def _initial_seed(frozen, split):
    modules = bind_real_implementations()
    w85 = modules["w85"]
    expected = "w85.seed_u32(w85.seed_key('run',split_id,'initial_design'))"
    require(frozen.get("initial_design_seed_namespace", expected) == expected,
            "Initial-design seed namespace drift")
    return w85.seed_u32(w85.seed_key("run", split["split_id"], "initial_design"))


def _starting_path(arm, frozen16, labels):
    if arm != "early8__coverage_then_margin_B40":
        observed = [int(labels[index]) for index in frozen16]
        require(len(set(observed)) == 2,
                "B16 frozen feature-only design lacks both classes; STOP, do not reseed or extend")
        return list(frozen16)
    queried = list(frozen16[:8])
    observed = [int(labels[index]) for index in queried]
    cursor = 8
    while len(set(observed)) < 2 and cursor < 16:
        queried.append(frozen16[cursor])
        observed.append(int(labels[frozen16[cursor]]))
        cursor += 1
    require(len(set(observed)) == 2,
            "Candidate B lacks both classes by B16; STOP")
    return queried


class FrozenM3Evaluator:
    """Thin adapter around the pinned M3 implementation; labels are revealed-only."""
    def __init__(self):
        self.modules = bind_real_implementations()

    def fit_predict(self, x, revealed, revealed_labels, train, predict, run_id, budget):
        p11, p13 = self.modules["p11"], self.modules["p13"]
        x = np.asarray(x, float)
        revealed = np.asarray(revealed, int)
        masked = np.full(len(x), -1, dtype=int)
        masked[revealed] = np.asarray(revealed_labels, int)
        logh = np.log(x[:, 0]) - 0.5 * np.log(x[:, 1]) - 1.5 * np.log(x[:, 2])
        physics = p11.fit_physics_mean(logh, masked, revealed,
                                       p13.seed_u32("shared_physics", run_id, budget))
        fit = p13.fit_hybrid(x, logh, masked, revealed, train, physics, "M3", 100.0)
        parts = p13.components(fit, x[np.asarray(predict, int)], logh[np.asarray(predict, int)])
        return parts["probability"], p13.fit_diagnostic(fit), fit


def _select(arm, budget, x, logh, train, queried, revealed_labels, candidates,
            candidate_probability, fit, run_id):
    modules = bind_real_implementations()
    search = modules["search"]
    if arm == "M3_margin_incumbent" or budget >= 40:
        return search.argbest(candidates, -np.abs(candidate_probability - 0.5)), "margin"
    seen = np.full(len(x), -1, dtype=int)
    seen[np.asarray(queried, int)] = np.asarray(revealed_labels, int)
    train = np.asarray(train, int)
    train_mask = np.zeros(len(x), dtype=bool)
    train_mask[train] = True
    scaled_view = np.full_like(x, np.nan, dtype=float)
    scaled_view[train] = StandardScaler().fit(x[train]).transform(x[train])
    logh_view = np.where(train_mask, logh, np.nan)
    x_view = np.where(train_mask[:, None], x, np.nan)
    state = SimpleNamespace(
        run_id=run_id, budget=budget, revealed=np.asarray(queried, int),
        candidates=np.asarray(candidates, int), seen_label=seen,
        x_scaled=scaled_view, logh=logh_view, p_cand=np.asarray(candidate_probability, float),
        cache={}, x4=x_view, train=train, fit=fit,
    )
    mask = search.estimated_band(state, 0.25)
    if not mask.any():
        return search.pol_margin(state), "empty_band_margin_fallback"
    return modules["p121"].coverage_then_margin()(state), "coverage_then_margin"


def _append_diagnostic(diagnostics, fallback_events, split_id, arm, budget, diagnostic):
    row = {"split_id": split_id, "arm": arm, "budget": budget, **(diagnostic or {})}
    diagnostics.append(row)
    status = str(row.get("fallback_status", "none"))
    if status.lower() not in {"", "none", "not_used", "nan"}:
        fallback_events.append({"split_id": split_id, "arm": arm, "budget": budget,
                                "event": "optimizer_fallback", "status": status})


def _run_arm(arm, split, frozen16, x, logh, labels, sim_ids, evaluator,
             paths, predictions, diagnostics, fallback_events):
    train = np.asarray(split["train_indices"], int)
    test = np.asarray(split["test_indices"], int)
    queried = _starting_path(arm, frozen16, labels)
    paths.extend({"split_id": split["split_id"], "arm": arm, "query_order": order,
                  "row_index": int(row), "sim_id": str(sim_ids[row]),
                  "selection_mode": "frozen_maximin"} for order, row in enumerate(queried, 1))
    while len(queried) < 16:
        budget = len(queried)
        candidates = np.setdiff1d(train, queried)
        probs, diag, fit = evaluator.fit_predict(
            x, queried, labels[queried], train, candidates, split["split_id"], budget)
        _append_diagnostic(diagnostics, fallback_events, split["split_id"], arm, budget, diag)
        chosen, mode = _select(arm, budget, x, logh, train, queried, labels[queried],
                               candidates, probs, fit, split["split_id"])
        if mode.endswith("fallback"):
            fallback_events.append({"split_id": split["split_id"], "arm": arm,
                                    "budget": budget, "event": mode})
        queried.append(int(chosen))
        paths.append({"split_id": split["split_id"], "arm": arm, "query_order": len(queried),
                      "row_index": int(chosen), "sim_id": str(sim_ids[chosen]),
                      "selection_mode": mode})
    for budget in BUDGETS:
        require(len(queried) == budget, "Path/budget mismatch")
        candidates = np.setdiff1d(train, queried)
        predict_at = np.concatenate([test, candidates]) if budget < 80 else test
        all_probs, diag, fit = evaluator.fit_predict(
            x, queried, labels[queried], train, predict_at, split["split_id"], budget)
        _append_diagnostic(diagnostics, fallback_events, split["split_id"], arm, budget, diag)
        probs = all_probs[:len(test)]
        predictions.extend({"split_id": split["split_id"], "repeat": split["repeat"],
            "fold": split["fold"], "arm": arm, "budget": budget, "row_index": int(row),
            "sim_id": str(sim_ids[row]), "truth": int(labels[row]), "probability": float(prob)}
            for row, prob in zip(test, probs))
        if budget == 80:
            break
        cprob = all_probs[len(test):]
        chosen, mode = _select(arm, budget, x, logh, train, queried, labels[queried],
                               candidates, cprob, fit, split["split_id"])
        if mode.endswith("fallback"):
            fallback_events.append({"split_id": split["split_id"], "arm": arm,
                                    "budget": budget, "event": mode})
        queried.append(int(chosen))
        paths.append({"split_id": split["split_id"], "arm": arm, "query_order": len(queried),
                      "row_index": int(chosen), "sim_id": str(sim_ids[chosen]),
                      "selection_mode": mode})
    require(len(queried) == 80 and len(set(queried)) == 80, "Incomplete/duplicate path")


def run_locked(features, sim_ids, labels, splits, frozen, evaluator=None,
               *, arms=ARMS, primary_endpoint=PRIMARY):
    """Run exactly the three frozen arms on already-authorized oracle labels."""
    require(tuple(arms) == ARMS, "Attempted policy override")
    require(primary_endpoint == PRIMARY, "Attempted endpoint override")
    require(tuple(frozen["arms"]) == ARMS and frozen["primary_endpoint"] == PRIMARY,
            "Frozen scientific settings drift")
    require(frozen["exact_feasible_budgets"] == BUDGETS, "Budget override")
    x = np.asarray(features, float)
    labels = np.asarray(labels, int)
    require(x.shape == (len(labels), 4) and np.isfinite(x).all(), "Feature matrix mismatch")
    require(set(np.unique(labels)).issubset({0, 1}), "Labels must be binary")
    require(len(sim_ids) == len(labels), "Simulation ID mismatch")
    evaluator = evaluator or FrozenM3Evaluator()
    logh = np.log(x[:, 0]) - 0.5 * np.log(x[:, 1]) - 1.5 * np.log(x[:, 2])
    paths, predictions, diagnostics, failures, fallback_events = [], [], [], [], []
    for split in splits:
        train = np.asarray(split["train_indices"], int)
        test = np.asarray(split["test_indices"], int)
        require(len(train) >= 80 and set(train).isdisjoint(test), "Invalid/insufficient split")
        frozen16 = feature_only_maximin(x, train, _initial_seed(frozen, split))
        for arm in ARMS:
            try:
                _run_arm(arm, split, frozen16, x, logh, labels, sim_ids, evaluator,
                         paths, predictions, diagnostics, fallback_events)
            except Exception as error:
                failures.append({"split_id": split["split_id"], "arm": arm,
                                 "event": "STOP", "error_type": type(error).__name__,
                                 "message": str(error)})
                return {"split_manifest": splits, "paths": paths, "predictions": predictions,
                        "fit_diagnostics": diagnostics, "failures": failures,
                        "fallback_events": fallback_events, "complete": False,
                        "arms": list(ARMS), "primary_endpoint": PRIMARY}
    return {"split_manifest": splits, "paths": paths, "predictions": predictions,
            "fit_diagnostics": diagnostics, "failures": failures,
            "fallback_events": fallback_events, "complete": True,
            "arms": list(ARMS), "primary_endpoint": PRIMARY}


def write_run(run, frozen, output_root):
    """Write every required execution artifact to the predeclared locations."""
    import pandas as pd
    output_root = Path(output_root).resolve()
    keys = {"split_manifest", "path_manifest", "per_budget_predictions",
            "fit_diagnostics", "failure_events", "fallback_events", "run_manifest"}
    locations = frozen["output_locations"]
    for key in keys:
        require(key in locations, f"Missing frozen output location: {key}")
        destination = (output_root / locations[key]).resolve()
        require(destination.is_relative_to(output_root), "Output location escapes declared root")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if key == "split_manifest":
            value = run["split_manifest"]
        elif key == "path_manifest":
            value = run["paths"]
        elif key == "per_budget_predictions":
            value = run["predictions"]
        elif key == "fit_diagnostics":
            value = run["fit_diagnostics"]
        elif key == "failure_events":
            value = run["failures"]
        elif key == "fallback_events":
            value = run["fallback_events"]
        else:
            value = {"arms": run["arms"], "primary_endpoint": run["primary_endpoint"],
                     "split_count": len(run["split_manifest"]),
                     "failure_count": len(run["failures"]), "complete": run["complete"],
                     "source_code_hashes": frozen["source_code_hashes"]}
        if destination.suffix.lower() == ".csv":
            write_new_bytes(destination, pd.DataFrame(value).to_csv(index=False, lineterminator="\n").encode())
        else:
            write_new_bytes(destination, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())
