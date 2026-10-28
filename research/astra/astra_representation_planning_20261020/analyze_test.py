"""Frozen-objective, whole-world analysis. Imports numerical libraries only inside Slot."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import time
from coordination import ROOT, Slot, now
from ledger import atomic_json, connection, sha256, status

METRICS = ("error", "boundary_error", "recall_positive", "recall_negative", "BA",
           "island_recall", "island_error", "brier", "log_loss", "RMSE",
           "reported_RMSE", "coverage90", "positive_queries", "island_queries",
           "missing_queries", "local_posterior_weight", "effective_components")
FACTORIAL = ("existing__h1", "existing__h2", "local__h1", "local__h2")
COEFFICIENTS = {"R": [-.5, -.5, .5, .5], "H": [-.5, .5, -.5, .5], "I": [1., -1., -1., 1.]}


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if hasattr(value, "tolist"):
        return clean(value.tolist())
    if isinstance(value, float) and not __import__("math").isfinite(value):
        return None
    return value


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for row in rows for k in row))
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            row = clean(row)
            writer.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v, (list, dict)) else v for k, v in row.items()})
    tmp.replace(path)


def run():
    global np
    import numpy as np
    manifest = json.loads((ROOT/"FROZEN_TEST_V1.json").read_text())
    for name, digest in manifest["source_hashes"].items():
        assert sha256(ROOT/name) == digest, "Frozen source mismatch " + name
    out = ROOT/"results/analysis"
    out.mkdir(exist_ok=True)
    start_cpu = time.process_time()
    with connection() as c:
        records = {r[0]: dict(zip(("status", "result", "note"), r[1:]))
                   for r in c.execute("SELECT id,status,result,note FROM units WHERE phase='TEST'")}
        attempts = [dict(zip(("attempt", "unit", "started", "ended", "status", "pid", "created", "note"), r))
                    for r in c.execute("SELECT * FROM attempts")]
    assert len(records) == len(manifest["units"])
    assert all(r["status"] not in ("PENDING", "RUNNING", "WAIT_ALLOCATION", "CHECKPOINTED") for r in records.values()), "TEST not terminal"
    lookup, worlds, endpoints, readouts, incomplete, files = {}, {}, [], [], [], []
    for unit in manifest["units"]:
        row = records[unit["id"]]
        base = {k: unit[k] for k in ("id", "world_id", "family", "seed", "panel", "model", "selector")}
        base["arm"] = unit["model"]+"__"+unit["selector"]
        if row["status"] != "COMPLETE":
            incomplete.append({**base, **row})
            endpoints.append({**base, "status": row["status"], "complete": False})
            continue
        path = ROOT/row["result"]
        r = json.loads(gzip.decompress(path.read_bytes()))
        assert r["unit"] == unit and r["manifest_sha256"] == sha256(ROOT/unit["manifest"])
        previous = worlds.get(unit["world_id"])
        if previous:
            assert previous["world_hash"] == r["world"]["world_hash"]
        worlds[unit["world_id"]] = {**{k: unit[k] for k in ("world_id", "family", "seed")}, **r["world"]}
        lookup[unit["panel"], unit["world_id"], base["arm"]] = r
        endpoints.append({**base, "status": row["status"], "complete": True, **r["final"],
             **{"cost_"+k: v for k, v in r["costs"].items()},
             **{"count_"+k: v for k, v in r["counters"].items()},
             "target_event": int(r["target_event"]), "target_budget": r["target_budget"],
             "restricted_query_burden": r["restricted_query_burden"],
             "peak_process_memory_bytes": r["peak_process_working_set_bytes"],
             "pool_island_n": r["world"]["pool_island_n"],
             "common_prefix_contains_valid_hit": r["world"]["common_prefix_contains_valid_hit"],
             "common_prefix_first_valid_hit": r["world"]["common_prefix_first_valid_hit"],
             "result_sha256": sha256(path)})
        readouts.extend({**base, **r0} for r0 in r["readouts"])
        files.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)})
    write_csv(out/"per_world_endpoints.csv", endpoints)
    write_csv(out/"per_world_readouts.csv", readouts)
    write_csv(out/"world_provenance.csv", list(worlds.values()))
    write_csv(out/"incomplete_units.csv", incomplete)
    write_csv(out/"attempt_ledger.csv", attempts)
    units = manifest["worlds"]
    families = list(manifest["family_counts"])
    B = manifest["analysis"]["bootstrap_replicates"]
    cache = {}

    def ids_for(panel, family):
        return [w["world_id"] for w in units if w["family"] == family and (panel == "prefix" or w["end_to_end"])]

    def weights(ids):
        key = tuple(ids)
        if key not in cache:
            seed = int.from_bytes(hashlib.sha256(("|".join(key)).encode()).digest()[:8], "little")
            rng = np.random.default_rng(np.random.SeedSequence([manifest["analysis"]["seed"], seed]))
            cache[key] = rng.multinomial(len(ids), np.full(len(ids), 1/len(ids)), size=B).astype(float)
        return cache[key]

    def value(panel, wid, arm, metric, budget=48):
        r = lookup.get((panel, wid, arm))
        if r is None:
            return np.nan
        if metric in ("target_event", "restricted_query_burden"):
            return float(r[metric])
        selected = next((q for q in r["readouts"] if q["budget"] == budget), None)
        v = selected.get(metric) if selected else None
        return np.nan if v is None else float(v)

    def conditional(wid):
        w = worlds.get(wid, {})
        return bool(w.get("common_prefix_contains_valid_hit") and w.get("evaluator_island_n", 0) > 0)

    def paired(panel, arms, coefs, metric, selected_families=None, condition=False, budget=48):
        fs = selected_families or families
        family_values, family_boots, ns = [], [], {}
        for family in fs:
            ids = ids_for(panel, family)
            vals = np.array([[value(panel, wid, a, metric, budget) for a in arms] for wid in ids])
            mask = np.all(np.isfinite(vals), axis=1)
            if condition:
                mask &= np.array([conditional(wid) for wid in ids])
            contrast = np.nan_to_num(vals)@np.array(coefs)
            ns[family] = {"eligible_pairs": int(mask.sum()), "scheduled_worlds": len(ids)}
            if not mask.any():
                family_values.append(np.nan)
                family_boots.append(np.full(B, np.nan))
                continue
            family_values.append(float(contrast[mask].mean()))
            w = weights(ids)
            denom = w@mask.astype(float)
            numer = w@(contrast*mask)
            family_boots.append(np.divide(numer, denom, out=np.full(B, np.nan), where=denom > 0))
        # Defined families contribute equally. An undefined required primary
        # family is handled explicitly by the primary completeness guard below.
        valid = np.isfinite(family_values)
        if not valid.any():
            return {"estimate": None, "ci95_pointwise": [None, None], "n": ns,
                    "undefined_families": list(fs), "invalid_bootstrap_replicates": B}, np.full(B, np.nan)
        theta = float(np.array(family_values)[valid].mean())
        boot = np.array(family_boots)[valid].mean(0)
        good = np.isfinite(boot)
        ci = np.quantile(boot[good], [.025, .975]).tolist() if good.any() else [None, None]
        return {"estimate": theta, "ci95_pointwise": ci, "n": ns,
                "undefined_families": [f for f, v in zip(fs, valid) if not v],
                "invalid_bootstrap_replicates": int((~good).sum())}, boot

    primary, boots = {}, []
    for metric, condition, fs in [("error", False, families), ("island_error", True, ["island_small", "island_large"])]:
        for contrast, coef in COEFFICIENTS.items():
            key = metric+"__"+contrast
            result, boot = paired("prefix", FACTORIAL, coef, metric, fs, condition)
            primary[key] = result
            boots.append(boot)
    boots = np.array(boots).T
    theta = np.array([p["estimate"] if p["estimate"] is not None else np.nan for p in primary.values()])
    good = np.all(np.isfinite(boots), axis=1)
    se = np.std(boots[good], axis=0, ddof=1) if good.sum() > 1 else np.full(6, np.nan)
    inferential = np.isfinite(se) & (se > 1e-12)
    critical = float(np.quantile(np.max(abs((boots[good][:, inferential]-theta[inferential])/se[inferential]), axis=1), .95)) if good.any() and inferential.any() else None
    for j, (key, result) in enumerate(primary.items()):
        result["bootstrap_standard_error"] = se[j]
        result["degenerate"] = not bool(inferential[j])
        result["ci95_simultaneous"] = ((theta[j]-critical*se[j], theta[j]+critical*se[j])
                    if inferential[j] and critical is not None else (theta[j], theta[j]))
        result["missing_outcome_bounds"] = _missing_bounds(
            manifest, lookup, worlds, key, COEFFICIENTS[key.split("__")[1]])
    eligible_primary = not incomplete and good.sum() > B*.95 and all(not p["undefined_families"] for p in primary.values())
    gates = {}
    for effect in ("R", "H"):
        g, i = primary["error__"+effect], primary["island_error__"+effect]
        gu, iu = g["ci95_simultaneous"][1], i["ci95_simultaneous"][1]
        possible = bool(eligible_primary and not g["degenerate"] and not i["degenerate"]
                       and gu is not None and iu is not None and np.isfinite(gu) and np.isfinite(iu))
        gates[effect] = {"supported_under_registered_guard": possible and
                        ((gu < 0 and iu < .05) or (iu < 0 and gu < .01)),
                        "not_a_model_replacement_or_physical_savings_claim": True}
    atomic_json(out/"PRIMARY_CONTRASTS.json", clean({
        "status": "COMPLETE" if not incomplete else "INCOMPLETE_NO_CLEAN_PRIMARY_PASS",
        "contrasts": primary, "max_standardized_critical_value": critical,
        "joint_valid_bootstrap_replicates": int(good.sum()), "replicates": B,
        "gates": gates, "assumptions": "Independent worlds within fixed families; whole-world stratified bootstrap approximation; six simultaneous estimates. No distribution-free or sign-flip claim."}))

    summaries, costs, secondary = [], [], []
    for panel in ("prefix", "e2e"):
        arms = sorted({u["model"]+"__"+u["selector"] for u in manifest["units"] if u["panel"] == panel})
        for arm in arms:
            for group, fs in [("equal_family", families)] + [(f, [f]) for f in families]:
                vals = {}
                for metric in (*METRICS, "target_event", "restricted_query_burden"):
                    result, _ = paired(panel, [arm], [1], metric, fs)
                    vals[metric] = result
                summaries.append({"panel": panel, "arm": arm, "group": group, "metrics": vals})
                group_rows = [r for (p, wid, a), r in lookup.items()
                              if p == panel and a == arm and r["unit"]["family"] in fs]
                cost = {"panel": panel, "arm": arm, "group": group,
                        "complete_n": len(group_rows), "expected_n": sum(len(ids_for(panel, f)) for f in fs),
                        "attainment_fraction": vals["target_event"]["estimate"],
                        "attainment_ci95_pointwise": vals["target_event"]["ci95_pointwise"],
                        "attained_n": sum(r["target_event"] for r in group_rows),
                        "censored_complete_n": sum(not r["target_event"] for r in group_rows),
                        "restricted_paid_query_burden": vals["restricted_query_burden"]["estimate"],
                        "restricted_burden_ci95_pointwise": vals["restricted_query_burden"]["ci95_pointwise"],
                        "event_budgets": [r["target_budget"] for r in group_rows if r["target_event"]]}
                for measure in ("decision_cpu", "fit_cpu", "evaluation_cpu", "total_cpu", "wall"):
                    means = [np.mean([r["costs"][measure] for r in group_rows if r["unit"]["family"] == f])
                             for f in fs if any(r["unit"]["family"] == f for r in group_rows)]
                    cost["mean_"+measure] = float(np.mean(means)) if means else None
                cost["max_peak_memory_bytes"] = max((r["peak_process_working_set_bytes"] for r in group_rows), default=None)
                costs.append(cost)
        pairs = [(a, "ard__straddle", "strong_control") for a in arms if a != "ard__straddle"]
        pairs += [("local__h1", "existing__h1", "representation_h1"),
                  ("local__h2", "existing__h2", "representation_h2"),
                  ("existing__h2", "existing__h1", "horizon_existing"),
                  ("local__h2", "local__h1", "horizon_local")]
        if panel == "prefix":
            for model in ("existing", "local"):
                pairs += [(model+"__mixture_h1", model+"__h1", "component_learning"),
                          (model+"__h2", model+"__mixture_h1", "horizon_against_component_learning")]
        for left, right, kind in pairs:
            for metric in ("error", "boundary_error", "recall_positive", "recall_negative", "island_error",
                           "brier", "log_loss", "target_event", "restricted_query_burden"):
                for group, fs, cond in ([("equal_family", families, False),
                                       ("conditional_prefix_hit", ["island_small", "island_large"], True)]
                                      + [(f, [f], False) for f in families]):
                    result, _ = paired(panel, [left, right], [1, -1], metric, fs, cond)
                    secondary.append({"panel": panel, "left": left, "right": right, "kind": kind,
                                      "metric": metric, "group": group, **result,
                                      "inference": "Pointwise descriptive paired interval; not multiplicity-adjusted promotion."})
    atomic_json(out/"FAMILY_SUMMARIES.json", clean(summaries))
    write_csv(out/"same_target_query_cost.csv", costs)
    write_csv(out/"paired_secondary_effects.csv", secondary)
    write_csv(out/"family_metrics.csv", [
        {"panel": s["panel"], "arm": s["arm"], "group": s["group"], "metric": metric, **v}
        for s in summaries for metric, v in s["metrics"].items()])

    compute = []
    for scope, caps, field in [("decision", manifest["analysis"]["decision_cpu_caps"], "cumulative_decision_cpu"),
                               ("total", manifest["analysis"]["total_cpu_caps"], "cumulative_total_cpu")]:
        for cap in caps:
            for (panel, wid, arm), r in lookup.items():
                eligible = [q for q in r["readouts"] if q[field] <= cap]
                q = eligible[-1] if eligible else None
                compute.append({"scope": scope, "cpu_cap_seconds": cap, "panel": panel,
                    "world_id": wid, "family": r["unit"]["family"], "arm": arm,
                    "available": bool(q), "budget": q["budget"] if q else None,
                    "capped_at_B48": bool(q and q["budget"] == 48),
                    **{k: q[k] if q else None for k in ("error", "boundary_error", "recall_positive", "recall_negative", "island_error", "brier")}})
    write_csv(out/"equal_compute_per_world.csv", compute)
    compute_summary = []
    for scope in ("decision", "total"):
        for cap in sorted({r["cpu_cap_seconds"] for r in compute if r["scope"] == scope}):
            for panel in ("prefix", "e2e"):
                arms = sorted({r["arm"] for r in compute if r["panel"] == panel})
                for arm in arms:
                    rs = [r for r in compute if (r["scope"], r["cpu_cap_seconds"], r["panel"], r["arm"]) == (scope, cap, panel, arm)]
                    rec = {"scope": scope, "cap_seconds": cap, "panel": panel, "arm": arm,
                           "n": len(rs), "available_n": sum(r["available"] for r in rs),
                           "at_query_cap_n": sum(r["capped_at_B48"] for r in rs)}
                    for m in ("error", "boundary_error", "recall_positive", "recall_negative", "island_error", "brier", "budget"):
                        fm = [np.mean([r[m] for r in rs if r["family"] == f and r[m] is not None])
                              for f in families if any(r["family"] == f and r[m] is not None for r in rs)]
                        rec[m] = float(np.mean(fm)) if fm else None
                    rec["scope_note"] = "Completion/availability conditional descriptive means; use paired available worlds for any contrast."
                    compute_summary.append(rec)
    write_csv(out/"equal_compute_summary.csv", compute_summary)
    cp = {(r["scope"], r["cpu_cap_seconds"], r["panel"], r["world_id"], r["arm"]): r for r in compute}
    compute_pairs = []
    for scope, caps in [("decision", manifest["analysis"]["decision_cpu_caps"]),
                        ("total", manifest["analysis"]["total_cpu_caps"])]:
        for cap in caps:
            for panel in ("prefix", "e2e"):
                pairs = [("existing__h2", "existing__h1"), ("local__h2", "local__h1"),
                         ("local__h1", "existing__h1"), ("local__h2", "existing__h2"),
                         ("local__h1", "ard__straddle"), ("local__h2", "ard__straddle")]
                if panel == "prefix":
                    pairs += [("existing__h2", "existing__mixture_h1"), ("local__h2", "local__mixture_h1")]
                for left, right in pairs:
                    for metric in ("error", "boundary_error", "island_error", "budget"):
                        estimates, bs, ns, undefined = [], [], {}, []
                        for family in families:
                            ids = ids_for(panel, family)
                            d = []
                            for wid in ids:
                                l, r = cp.get((scope, cap, panel, wid, left)), cp.get((scope, cap, panel, wid, right))
                                d.append(l[metric]-r[metric] if l and r and l[metric] is not None and r[metric] is not None else np.nan)
                            d = np.array(d)
                            ok = np.isfinite(d)
                            ns[family] = {"paired_available": int(ok.sum()), "scheduled": len(ids)}
                            if not ok.any():
                                undefined.append(family)
                                continue
                            estimates.append(float(d[ok].mean()))
                            w = weights(ids)
                            denom = w@ok.astype(float)
                            bs.append(np.divide(w@np.nan_to_num(d), denom, out=np.full(B, np.nan), where=denom > 0))
                        boot = np.array(bs).mean(0) if bs else np.full(B, np.nan)
                        good_boot = np.isfinite(boot)
                        compute_pairs.append({"scope": scope, "cap_seconds": cap, "panel": panel,
                            "left": left, "right": right, "metric": metric, "n": ns,
                            "estimate": float(np.mean(estimates)) if estimates else None,
                            "ci95_pointwise": np.quantile(boot[good_boot], [.025, .975]).tolist() if good_boot.any() else [None, None],
                            "undefined_families": undefined, "invalid_bootstrap_replicates": int((~good_boot).sum()),
                            "scope_note": "Paired common-available worlds only; missing low-compute predictions remain explicit."})
    write_csv(out/"equal_compute_paired_effects.csv", compute_pairs)
    # B32 matched-path representation: no adaptive paths have yet diverged.
    matched = []
    for left in ("local__h1", "ard__straddle"):
        for metric in ("error", "boundary_error", "recall_positive", "recall_negative", "island_error", "brier", "log_loss"):
            result, _ = paired("prefix", [left, "existing__h1"], [1, -1], metric, budget=32)
            matched.append({"left": left, "right": "existing__h1", "budget": 32, "metric": metric, **result})
    write_csv(out/"B32_same_paid_path_model_effects.csv", matched)
    result = {"status": "COMPLETE" if not incomplete else "COMPLETE_WITH_INCOMPLETE_TEST_UNITS",
              "utc": now().isoformat(), "analysis_source_sha256": sha256(Path(__file__)),
              "test_manifest_sha256": sha256(ROOT/"FROZEN_TEST_V1.json"),
              "worlds": len(worlds), "complete_paths": len(lookup), "incomplete_paths": len(incomplete),
              "ledger": status(), "analysis_cpu_seconds": time.process_time()-start_cpu,
              "result_files": files,
              "cpu_scope": "Trajectory CPU from after synthetic-world generation; includes fit, selection, evaluation, checkpoint/file work. Excludes imports/world generation and supervisor. Attempt timestamps separately include launch-side task work. Interrupted pre-checkpoint cost can be under-recorded; reservations are retained.",
              "claims": "No synthetic-to-SPH or physical-hour savings inference. Overall equal-family means do not remove family harms.",
              "visual_review": "PENDING_MANUAL_REVIEW"}
    atomic_json(out/"ANALYSIS_STATUS.json", clean(result))
    return result


def _missing_bounds(manifest, lookup, worlds, key, coefs):
    """Bounds [0,1] each missing outcome, retaining known terms; no imputed success."""
    metric, _ = key.split("__")
    families = ["island_small", "island_large"] if metric == "island_error" else list(manifest["family_counts"])
    lower, upper = [], []
    unknown_condition = 0
    for family in families:
        ls, us = [], []
        for w in manifest["worlds"]:
            if w["family"] != family:
                continue
            if metric == "island_error":
                meta = worlds.get(w["world_id"])
                if meta is None:
                    unknown_condition += 1
                    continue
                if not (meta["common_prefix_contains_valid_hit"] and meta["evaluator_island_n"] > 0):
                    continue
            lo = hi = 0.
            for a, c in zip(FACTORIAL, coefs):
                r = lookup.get(("prefix", w["world_id"], a))
                v = r["final"].get(metric) if r else None
                if v is None:
                    lo += min(0, c)
                    hi += max(0, c)
                else:
                    lo += c*v
                    hi += c*v
            ls.append(lo); us.append(hi)
        if ls:
            lower.append(sum(ls)/len(ls)); upper.append(sum(us)/len(us))
    return {"lower": sum(lower)/len(lower) if lower else None,
            "upper": sum(upper)/len(upper) if upper else None,
            "unknown_conditional_memberships": unknown_condition,
            "scope": "Known eligibility only; unknown membership prevents a complete conditional bound."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, choices=[1], required=True)
    parser.parse_args()
    with Slot():
        print(json.dumps(clean({k: v for k, v in run().items() if k != "result_files"}), indent=2))
