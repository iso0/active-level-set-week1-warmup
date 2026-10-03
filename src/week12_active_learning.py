"""NEW-only developmental complete protocols, with every label query charged.

This module never invokes run_locked or reuses frozen performance checkpoints.
Startup definitions live in week12_startup and are fixed after mechanism study.
"""
from __future__ import annotations

import argparse
import gzip
import json
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from src.week12_development_common import (
    OUT, ROOT, FEATURES, load_new, load_splits, logh, metrics, original_order,
    q20_flags, require, safe, seed, sha, write_csv, write_json)

DEST = OUT / "active_learning"


def protocol_hash():
    return sha(DEST / "config.json")


def source_hashes():
    return {str(p.relative_to(ROOT)): sha(p) for p in [
        ROOT / "src/week12_active_learning.py", ROOT / "src/week12_startup.py",
        ROOT / "src/week12_development_common.py",
        ROOT / "src/external_validation/runner.py", ROOT / "src/external_validation/analysis.py",
        ROOT / "src/week9_phase1_11_fixed_mean_discrepancy_gp.py",
        ROOT / "src/week9_phase1_13_fixed_physics_ard_discrepancy.py",
        ROOT / "src/week9_phase1_20_acquisition_search.py",
        ROOT / "src/week9_phase1_21_simplification_replication.py",
        ROOT / "src/week8_5_frozen_sample_efficiency_confirmation.py",
        OUT / "audit/input_provenance.json"]}


def select_refinement(kind, x, train, queried, observed, candidates, probs, fit, split_id):
    """Only revealed labels enter this selector; test coordinates are masked upstream."""
    from src.external_validation.runner import _select
    if kind == "random":
        return int(np.random.default_rng(seed(split_id, "random_refinement", len(queried))).choice(candidates)), "random"
    historical_arm = "M3_margin_incumbent" if kind == "margin" else "coverage_then_margin_B40"
    return _select(historical_arm, len(queried), x, logh(x), train, queried,
                   observed, candidates, probs, fit, split_id)


def run_split(split, arms, horizon=80):
    from src.external_validation.runner import FrozenM3Evaluator
    from src.week12_startup import startup_next
    data = load_new()
    x = data[FEATURES].to_numpy(float)
    y = data.has_keyhole.to_numpy(int)
    ids = data.sim_id.to_numpy(str)
    train = np.asarray(split["train_indices"], int)
    test = np.asarray(split["test_indices"], int)
    order = original_order(x, split)
    q20 = q20_flags(x, y, ids, test)  # evaluator only; never supplied to selector
    path = DEST / "checkpoints" / (split["split_id"].replace("external__", "dev__") + ".json.gz")
    if path.exists():
        payload = json.loads(gzip.decompress(path.read_bytes()))
        require(payload["config_sha256"] == protocol_hash(), "Checkpoint config drift")
        require(payload["source_hashes"] == source_hashes(), "Checkpoint code drift")
        require(payload["complete"], "Failed checkpoints are not silently reused")
        return {"split_id": split["split_id"], "cached": True, "seconds": payload["seconds"]}
    start = time.perf_counter()
    paths, predictions, diagnostics, events, failures = [], [], [], [], []
    # Same ordered prefix -> same frozen fit across arms. Predictions only, no
    # decisions cached; deterministic optimizer uses the common split namespace.
    cache = {}
    evaluator = FrozenM3Evaluator()
    with threadpool_limits(limits=1):
        for arm, spec in arms.items():
            queried, observed = [], []
            discovery_cost = None
            try:
                while len(queried) <= horizon:
                    b = len(queried)
                    both = len(set(observed)) == 2
                    if both and discovery_cost is None:
                        discovery_cost = b
                    in_startup = b < spec["minimum_start"] or not both
                    fit = None
                    if b >= 8 or (not in_startup and b < horizon):
                        if not in_startup:
                            key = tuple(queried)
                            if key not in cache:
                                p, diag, fit = evaluator.fit_predict(
                                    x, queried, observed, train, np.arange(len(x)), split["split_id"], b)
                                cache[key] = (p, diag, fit)
                            p, diag, fit = cache[key]
                            diagnostics.append({"split_id": split["split_id"], "arm": arm, "budget": b, **safe(diag)})
                            predictor = "historical_M3"
                        else:
                            # Defined for zero/one observed class, but never
                            # represented as a fitted GP. Same prior all arms.
                            p = np.repeat((sum(observed) + 1.) / (b + 2.), len(x))
                            predictor = "Beta(1,1)_observed_prevalence_during_startup"
                        if b >= 8:
                            for j, row in enumerate(test):
                                predictions.append({"split_id": split["split_id"], "repeat": split["repeat"],
                                    "fold": split["fold"], "arm": arm, "budget": b, "row_index": int(row),
                                    "truth": int(y[row]), "probability": float(p[row]), "q20": bool(q20[j]),
                                    "predictor": predictor, "discovery_cost_so_far": discovery_cost})
                    if b == horizon:
                        break
                    if in_startup:
                        chosen = startup_next(spec["startup"], x, train, queried, observed, order, split["split_id"])
                        mode = "paid_startup_" + spec["startup"]
                    else:
                        candidates = np.setdiff1d(train, queried)
                        chosen, mode = select_refinement(spec["refinement"], x, train,
                            queried, observed, candidates, p[candidates], fit, split["split_id"])
                    require(chosen in train and chosen not in queried, "Illegal or duplicate query")
                    queried.append(int(chosen))
                    observed.append(int(y[chosen]))  # reveal only after committed choice
                    paths.append({"split_id": split["split_id"], "repeat": split["repeat"],
                                  "fold": split["fold"], "arm": arm, "query_order": b+1,
                                  "row_index": int(chosen), "revealed_label": observed[-1], "selection_mode": mode})
                    if "fallback" in mode:
                        events.append({"split_id": split["split_id"], "arm": arm, "budget": b, "event": mode})
            except Exception as exc:
                failures.append({"split_id": split["split_id"], "arm": arm, "budget": len(queried),
                                 "error": repr(exc), "traceback": traceback.format_exc()})
    payload = {"complete": not failures, "config_sha256": protocol_hash(), "source_hashes": source_hashes(),
               "split": split, "seconds": time.perf_counter()-start, "paths": paths, "predictions": predictions,
               "diagnostics": diagnostics, "fallback_events": events, "failures": failures,
               "unique_prefix_fits": len(cache), "classification": "POST-HOC DEVELOPMENT"}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps(safe(payload), allow_nan=False).encode(), mtime=0))
    return {"split_id": split["split_id"], "complete": not failures, "seconds": payload["seconds"], "fits": len(cache)}


def run(workers):
    from src.week12_development_common import verify_protected
    require(verify_protected()["status"] == "PASS", "Protected evidence changed")
    config = json.loads((DEST / "config.json").read_text())
    splits = load_splits()
    require(len(splits) == 100, "Expected all original100 pools")
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_split, s, config["arms"], config["horizon"]): s["split_id"] for s in splits}
        for f in as_completed(futures):
            try:
                result = f.result()
            except Exception as exc:
                result = {"split_id": futures[f], "complete": False, "error": repr(exc)}
            results.append(result)
            print(json.dumps(result), flush=True)
            write_json(DEST / "execution_progress.json", {"completed_split_jobs": len(results), "results": results})
    write_json(DEST / "execution.json", {"jobs": results, "workers": workers, "config_sha256": protocol_hash()})


def summarize():
    config = json.loads((DEST / "config.json").read_text())
    payloads = [json.loads(gzip.decompress(p.read_bytes())) for p in sorted((DEST/"checkpoints").glob("*.json.gz"))]
    failures = [r for p in payloads for r in p["failures"]]
    write_json(DEST / "failures.json", failures)
    require(len(payloads) == 100 and all(p["complete"] for p in payloads), "Incomplete development: see retained failures")
    for p in payloads:
        require(p["config_sha256"] == protocol_hash() and p["source_hashes"] == source_hashes(), "Hash drift")
    predictions = pd.DataFrame(r for p in payloads for r in p["predictions"])
    paths = pd.DataFrame(r for p in payloads for r in p["paths"])
    diag = pd.DataFrame(r for p in payloads for r in p["diagnostics"])
    write_csv(DEST / "predictions.csv.gz", predictions)
    write_csv(DEST / "query_paths.csv.gz", paths)
    write_csv(DEST / "fit_diagnostics.csv.gz", diag)
    rows = []
    for keys, g in predictions.groupby(["split_id", "repeat", "fold", "arm", "budget"], sort=False):
        info = dict(zip(["split_id", "repeat", "fold", "arm", "budget"], keys))
        for subset, v in [("full", g), ("q20", g[g.q20])]:
            rows.append({**info, "subset": subset, **metrics(v.truth, v.probability)})
    fold_metrics = pd.DataFrame(rows)
    write_csv(DEST / "fold_metrics.csv.gz", fold_metrics)
    oof_rows = []
    for keys, g in predictions.groupby(["repeat", "arm", "budget"], sort=False):
        info = dict(zip(["repeat", "arm", "budget"], keys))
        require(len(g) == 136 and g.row_index.nunique() == 136, "OOF coverage")
        for subset, v in [("full", g), ("q20", g[g.q20])]:
            oof_rows.append({**info, "subset": subset, **metrics(v.truth, v.probability)})
    oof = pd.DataFrame(oof_rows)
    write_csv(DEST / "pooled_oof_metrics.csv.gz", oof)
    endpoints = []
    for keys, g in fold_metrics.groupby(["split_id", "repeat", "fold", "arm", "subset"], sort=False):
        info = dict(zip(["split_id", "repeat", "fold", "arm", "subset"], keys))
        g = g.sort_values("budget")
        for low, high in [(16, 80), (16, 40), (8, 80)]:
            v = g[g.budget.between(low, high)]
            require(v.budget.tolist() == list(range(low, high+1)), "Budget completeness")
            endpoints.append({**info, "endpoint": f"accuracy_AULC_B{low}_B{high}",
                              "value": float(np.trapezoid(v.accuracy, v.budget)/(high-low))})
    endpoints = pd.DataFrame(endpoints)
    write_csv(DEST / "fold_endpoints.csv", endpoints)
    reps = endpoints.groupby(["repeat", "arm", "subset", "endpoint"], as_index=False).value.mean()
    write_csv(DEST / "repeat_endpoints.csv", reps)
    contrasts = []
    for subset in ["q20", "full"]:
        for endpoint in reps.endpoint.unique():
            pv = reps[(reps.subset == subset) & (reps.endpoint == endpoint)].pivot(index="repeat", columns="arm", values="value")
            for a, b in config["contrasts"]:
                delta = (pv[a]-pv[b]).to_numpy()
                rng = np.random.default_rng(seed("partition_bootstrap", a, b, subset, endpoint))
                draws = delta[rng.integers(0, len(delta), (10000, len(delta)))].mean(1)
                contrasts.append({"arm": a, "reference": b, "subset": subset, "endpoint": endpoint,
                    "mean_delta": float(delta.mean()), "partition_interval_low": float(np.quantile(draws, .025)),
                    "partition_interval_high": float(np.quantile(draws, .975)),
                    "positive_repeats": int((delta > 0).sum()), "min_repeat_delta": float(delta.min()),
                    "max_repeat_delta": float(delta.max()), "independent_campaigns": 1})
    contrast = pd.DataFrame(contrasts)
    write_csv(DEST / "paired_contrasts.csv", contrast)
    agg = reps.groupby(["arm", "subset", "endpoint"]).value.agg(["mean", "std", "min", "max"]).reset_index()
    write_csv(DEST / "summary_endpoints.csv", agg)
    curves = fold_metrics.groupby(["arm", "subset", "budget"], as_index=False).accuracy.mean()
    write_csv(DEST / "mean_accuracy_curves.csv", curves)
    pooled = oof.groupby(["arm", "subset", "budget"], as_index=False).mean(numeric_only=True)
    write_csv(DEST / "mean_pooled_metrics.csv", pooled)
    check = validate_paths(paths, predictions, config)
    write_json(DEST / "QC.json", check)
    write_json(DEST / "summary.json", {"classification": "POST-HOC DEVELOPMENT", "complete": True,
        "splits": 100, "arms": list(config["arms"]), "path_count": 100*len(config["arms"]),
        "prediction_count": len(predictions), "query_count": len(paths), "fit_diagnostic_count": len(diag),
        "unique_prefix_fits": sum(p["unique_prefix_fits"] for p in payloads),
        "optimizer_nonconvergence_count": int((~diag.optimizer_converged.astype(bool)).sum()),
        "fit_fallback_counts": diag.fallback_status.value_counts().to_dict(),
        "primary_contrasts": contrast[(contrast.subset=="q20") & (contrast.endpoint=="accuracy_AULC_B16_B80")].to_dict("records"),
        "partition_interval_caveat": "Conditional resampling of overlapping repeat blocks, not population/campaign confirmation.",
        "protected_frozen_run_resumed": False})
    figures(curves, pooled, contrast)


def validate_paths(paths, predictions, config):
    splits = {s["split_id"]: s for s in load_splits()}
    y = load_new().has_keyhole.to_numpy(int)
    for (sid, arm), g in paths.groupby(["split_id", "arm"]):
        g = g.sort_values("query_order")
        require(g.query_order.tolist() == list(range(1, 81)), "Query budget ledger mismatch")
        require(g.row_index.nunique() == 80, "Duplicate queried label")
        require(set(g.row_index) <= set(splits[sid]["train_indices"]), "Test query leakage")
        first2 = next((i for i in range(2,81) if g.revealed_label.iloc[:i].nunique()==2), None)
        for row in g.itertuples():
            if not row.selection_mode.startswith("paid_startup"):
                require(first2 is not None and row.query_order > first2, "Refinement before discovery")
    require(not predictions.duplicated(["split_id","arm","budget","row_index"]).any(), "Duplicate prediction")
    require(len(paths.groupby(["split_id","arm"])) == 100*len(config["arms"]), "Missing paths")
    expected = {(sid,arm,b) for sid in splits for arm in config["arms"] for b in range(8,81)}
    groups = predictions.groupby(["split_id","arm","budget"])
    require(set(groups.groups) == expected, "Incomplete prediction budget groups")
    for (sid,arm,b),g in groups:
        test = splits[sid]["test_indices"]
        require(len(g)==len(test) and set(g.row_index)==set(test), "Test prediction IDs mismatch")
        require(np.array_equal(g.truth.to_numpy(int),y[g.row_index.to_numpy(int)]), "Prediction truth drift")
    return {"status": "PASS", "all_queries_charged": True, "no_test_queries": True,
            "no_duplicate_queries": True, "refinement_requires_observed_two_classes": True,
            "all_100_development_splits_complete": True, "frozen_checkpoints_reused": False,
            "complete_heldout_prediction_grid": True, "truth_mapping_verified": True,
            "q20_implementation_sha256":sha(ROOT/"src/external_validation/analysis.py")}


def figures(curves, pooled, contrast):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10,6))
    for arm, g in curves[curves.subset=="q20"].groupby("arm"):
        ax.plot(g.budget, g.accuracy, label=arm)
    ax.set(xlabel="Total paid labels", ylabel="Mean fold q20 accuracy", title="NEW-only development: startup + boundary refinement")
    ax.legend(fontsize=7); ax.grid(alpha=.2); fig.tight_layout()
    fig.savefig(DEST/"q20_curves.png", dpi=170); plt.close(fig)
    fig, axes = plt.subplots(1,2,figsize=(12,5))
    for arm,g in pooled[pooled.subset=="full"].groupby("arm"):
        axes[0].plot(g.budget,g.balanced_accuracy,label=arm)
        axes[1].plot(g.budget,g.non_keyhole_recall,label=arm)
    axes[0].set(ylabel="Pooled OOF balanced accuracy",xlabel="Total paid labels")
    axes[1].set(ylabel="Non-Keyhole recall",xlabel="Total paid labels")
    axes[1].legend(fontsize=6); fig.suptitle("NEW-only development; 12 unique non-Keyhole cases")
    fig.tight_layout(); fig.savefig(DEST/"class_sensitive_curves.png",dpi=170); plt.close(fig)


def main():
    p=argparse.ArgumentParser();p.add_argument("mode",choices=["run","summarize"]);p.add_argument("--workers",type=int,default=4)
    a=p.parse_args()
    if a.mode=="run": run(a.workers)
    else: summarize()


if __name__ == "__main__":
    main()
