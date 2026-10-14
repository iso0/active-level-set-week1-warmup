"""Exploratory EX1 — balanced-accuracy-aligned decision rule (prospective test; separate manifest in exploratory/).

Mechanism.  BA = (TPR + TNR) / 2 weights the two classes equally.  For a calibrated posterior probability
p(x) = P(Y = 1 | x, D), predicting 1 adds p / (2 pi) to the expected BA and predicting 0 adds (1 - p) / (2 (1 - pi)),
so the BA-optimal decision is p >= pi (the class prior), not p >= 0.5.  A fixed proper-prior probit model is roughly
calibrated to the paid class mix; on NEW (pi about 0.9) the 0.5 rule therefore labels well-ranked negatives positive.
Rule tested here (train-only): pi_hat = share of positives among the PAID labels of the checkpoint.

Data: NEW, OLD, POOLED, DEV repeats 5-8 (never used in Stage M; repeats 3-4 stay reserved for Stage A), five folds,
feature-only maximin paths (same routine and task seeds as Stage M), B16 and B40.  Arms: J and Binary_matched in all
three populations; ACTIVE_E1 and G3 on NEW (complete-system context).  Frozen Stage M priors; no tuning.

Steps: python -m src.jdl_ex1 manifest | run | evaluate
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import datetime as dt
import gzip
import hashlib
import json
import sys
import time

import numpy as np
import pandas as pd

import src.jdl_stage_m as SMM
from src.jdl_evaluate import boot_weights

EX = SMM.OUT / "exploratory" / "EX1_ba_aligned_decision_rule"
CACHE = SMM.OUT / "_cache" / "ex1"
REPEATS = (5, 6, 7, 8)
ARMS_BY_POP = {"NEW": ("J", "Binary_matched", "ACTIVE_E1", "G3"), "OLD": ("J", "Binary_matched"), "POOLED": ("J", "Binary_matched")}
PREDICTIONS = {
    "EX1-P1_primary": "NEW, B40, J: BA at p >= pi_hat minus BA at p >= 0.5 is > 0 (mean over repeats 5-8). Direction from the Stage M POST-HOC table (+0.32 on repeats 1-2); no magnitude committed. Falsified if <= 0.",
    "EX1-P2_mechanism": "NEW, B40, J: the change comes from specificity (> 0) at a sensitivity cost (< 0).",
    "EX1-P3_control": "NEW, B40, Binary_matched: BA at pi_hat minus BA at 0.5 is <= 0 (its depth-free probabilities are compressed below the paid prevalence; Stage M POST-HOC -0.04).",
    "EX1-P4_system": "NEW, B40: J at pi_hat has higher BA than ACTIVE_E1 at its own frozen 0.5 rule (Stage M POST-HOC 0.870 vs 0.730). A complete-system comparison.",
    "EX1-P5_secondary": "OLD and POOLED (prevalence about 0.18 and 0.36): no directional expectation for J; reported.",
}


def build_tasks_r():
    old = SMM.REPEATS
    SMM.REPEATS = REPEATS
    try:
        return SMM.build_tasks()
    finally:
        SMM.REPEATS = old


def write_manifest():
    tasks = build_tasks_r()
    paths = SMM.make_paths(tasks)
    EX.mkdir(parents=True, exist_ok=True)
    paths.to_csv(EX / "paths.csv", index=False, lineterminator="\n")
    n_fits = sum(len(ARMS_BY_POP[t["population"]]) for t in tasks) * len(SMM.BUDGETS)
    man = {"idea": "EX1 balanced-accuracy-aligned decision rule", "status": "EXPLORATORY, frozen before any EX1 fit; separate from the main study; does not change the Stage M decision",
           "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "parent_commit": SMM._git("rev-parse", "HEAD"),
           "mechanism": __doc__.split("Mechanism.")[1].split("Data:")[0].strip(), "rule": "pi_hat = mean of the paid canonical labels at the checkpoint (train-only); compare decisions p >= pi_hat with p >= 0.5 on the same stored probabilities",
           "data": {"repeats": list(REPEATS), "reason": "DEV repeats never used for any J fit; Stage M used 1-2, Stage A reserves 3-4", "populations": list(ARMS_BY_POP)},
           "paths_sha256": {f"{p}_r{r}_f{f}": hashlib.sha256("\n".join(g.sort_values("query_index").sim_id).encode()).hexdigest() for (p, r, f), g in paths.groupby(["population", "repeat", "fold"])},
           "arms": ARMS_BY_POP, "budgets": list(SMM.BUDGETS), "fit_requests": n_fits, "priors": "frozen Stage M STAGE_M_CONFIG; E1/G3 frozen implementations",
           "predictions": PREDICTIONS, "outcomes": "BA, specificity, sensitivity at both rules; paired differences with a simulation-cluster bootstrap (2000, class-stratified); per-repeat values",
           "controls": "Binary_matched (same priors without the response) at both rules; ACTIVE_E1 and G3 at their frozen 0.5 rules and at pi_hat",
           "protections": ["train-only threshold", "no prior or threshold tuning", "held-out labels only in evaluation", "all outcomes preserved"],
           "code_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in ("src/jdl_ex1.py", "src/jdl_stage_m.py", "src/jdl_model.py", "src/jdl_evaluate.py")}}
    (EX / "EX1_MANIFEST.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(json.dumps({k: man[k] for k in ("fit_requests", "data")}, indent=1))


def run():
    import src.week18_engine as E
    if not (EX / "EX1_MANIFEST.json").exists():
        raise SystemExit("commit the EX1 manifest first")
    man = json.loads((EX / "EX1_MANIFEST.json").read_text(encoding="utf-8"))
    tasks = build_tasks_r()
    paths = pd.read_csv(EX / "paths.csv")
    CACHE.mkdir(parents=True, exist_ok=True)
    t0, n = time.time(), 0
    for t in tasks:
        g = paths[(paths.population == t["population"]) & (paths.repeat == t["repeat"]) & (paths.fold == t["fold"])].sort_values("query_index")
        if hashlib.sha256("\n".join(g.sim_id).encode()).hexdigest() != man["paths_sha256"][f"{t['population']}_r{t['repeat']}_f{t['fold']}"]:
            raise SystemExit("path differs from the EX1 manifest")
        pos = {s: i for i, s in enumerate(t["ids"])}
        t["path"] = g.sim_id.map(pos).to_numpy(int)
        for b in SMM.BUDGETS:
            for arm in ARMS_BY_POP[t["population"]]:
                cf = CACHE / f"{t['population']}__r{t['repeat']}_f{t['fold']}__B{b}__{arm}.json.gz"
                if cf.exists():
                    continue
                if arm in SMM.J_ARMS:
                    rec, preds = SMM.fit_joint(t, arm, b)
                else:
                    rec, preds, _ = SMM.fit_baseline(t, arm, b, E, n)
                n += 1
                rec["paid_prevalence"] = float(np.mean(t["y"][t["path"][:b]]))
                cf.write_bytes(gzip.compress(json.dumps({"fit": rec, "predictions": preds}, default=float).encode()))
    print(f"EX1 fits this session: {n}, {time.time() - t0:.1f}s")


def evaluate():
    fits, preds = [], []
    for f in sorted(CACHE.glob("*.json.gz")):
        r = json.loads(gzip.decompress(f.read_bytes())); fits.append(r["fit"]); preds += r["predictions"]
    fits, preds = pd.DataFrame(fits), pd.DataFrame(preds)
    prev = {(r.population, r.repeat, r.fold, r.budget, r.arm): r.paid_prevalence for r in fits.itertuples()}
    preds["pi_hat"] = [prev[(r.population, r.repeat, r.fold, r.budget, r.arm)] for r in preds.itertuples()]
    tasks = build_tasks_r()
    rows, crow = [], []
    for pop, arms in ARMS_BY_POP.items():
        ts = [t for t in tasks if t["population"] == pop]
        ids, y = ts[0]["ids"], ts[0]["y"]; pos = {s: i for i, s in enumerate(ids)}
        W = boot_weights(y)
        dec = {}
        for arm in arms:
            for rep in REPEATS:
                for b in SMM.BUDGETS:
                    g = preds[(preds.population == pop) & (preds.arm == arm) & (preds.repeat == rep) & (preds.budget == b) & (preds.prediction_status == "ok")]
                    p = np.full(len(ids), np.nan); th = np.full(len(ids), np.nan)
                    ii = g.sim_id.map(pos).to_numpy(int); p[ii] = g.p.to_numpy(float); th[ii] = g.pi_hat.to_numpy(float)
                    av = np.isfinite(p)
                    for rule, thr in (("p>=0.5", np.full(len(ids), 0.5)), ("p>=pi_hat", th)):
                        d = np.where(av, (np.nan_to_num(p) >= np.nan_to_num(thr, nan=0.5)).astype(float), np.nan)
                        dec[(arm, rep, b, rule)] = d
                        posm, negm = av & (y == 1), av & (y == 0)
                        sens = (W @ (posm * np.nan_to_num(d))) / (W @ posm); spec = (W @ (negm * (1 - np.nan_to_num(d)))) / (W @ negm)
                        rows.append({"population": pop, "arm": arm, "repeat": rep, "budget": b, "rule": rule, "BA": float(0.5 * (sens[0] + spec[0])),
                                     "specificity": float(spec[0]), "sensitivity": float(sens[0]), "n_available": int(av.sum()), "mean_pi_hat": float(np.nanmean(th))})
        def ba_draws(d, mask):
            posm, negm = mask & (y == 1), mask & (y == 0)
            dd = np.nan_to_num(d)
            sens = (W @ (posm * dd)) / (W @ posm); spec = (W @ (negm * (1 - dd))) / (W @ negm)
            return 0.5 * (sens + spec), spec, sens
        comps = [((a, "p>=pi_hat"), (a, "p>=0.5")) for a in arms]
        if pop == "NEW":
            comps += [(("J", "p>=pi_hat"), ("ACTIVE_E1", "p>=0.5")), (("J", "p>=pi_hat"), ("G3", "p>=0.5")), (("J", "p>=pi_hat"), ("Binary_matched", "p>=pi_hat")),
                      (("J", "p>=pi_hat"), ("ACTIVE_E1", "p>=pi_hat"))]
        for (a1, r1), (a2, r2) in comps:
            for b in SMM.BUDGETS:
                per = {"BA": [], "specificity": [], "sensitivity": []}
                for rep in REPEATS:
                    d1, d2 = dec[(a1, rep, b, r1)], dec[(a2, rep, b, r2)]
                    mask = np.isfinite(d1) & np.isfinite(d2)
                    m1, m2 = ba_draws(d1, mask), ba_draws(d2, mask)
                    for k, i in (("BA", 0), ("specificity", 1), ("sensitivity", 2)):
                        per[k].append(m1[i] - m2[i])
                for k, v in per.items():
                    d = np.nanmean(np.vstack(v), axis=0)
                    lo, hi = np.nanpercentile(d[1:], [2.5, 97.5])
                    crow.append({"population": pop, "budget": b, "metric": k, "contrast": f"{a1} [{r1}] - {a2} [{r2}]", "estimate": float(d[0]),
                                 "per_repeat": json.dumps([float(x[0]) for x in v]), "cluster_bootstrap_lo": float(lo), "cluster_bootstrap_hi": float(hi)})
    mt, ct = pd.DataFrame(rows), pd.DataFrame(crow)
    EX.mkdir(parents=True, exist_ok=True)
    mt.to_csv(EX / "metrics_per_repeat.csv", index=False, lineterminator="\n"); ct.to_csv(EX / "contrasts.csv", index=False, lineterminator="\n")
    preds.to_csv(EX / "predictions_all.csv.gz", index=False, lineterminator="\n", compression={"method": "gzip", "mtime": 0})
    fits.to_csv(EX / "fit_log.csv", index=False, lineterminator="\n")
    g = lambda c, b, m="BA": ct[(ct.contrast == c) & (ct.budget == b) & (ct.metric == m) & (ct.population == "NEW")].iloc[0]
    p1 = g("J [p>=pi_hat] - J [p>=0.5]", 40); p2s, p2n = g("J [p>=pi_hat] - J [p>=0.5]", 40, "specificity"), g("J [p>=pi_hat] - J [p>=0.5]", 40, "sensitivity")
    p3 = g("Binary_matched [p>=pi_hat] - Binary_matched [p>=0.5]", 40); p4 = g("J [p>=pi_hat] - ACTIVE_E1 [p>=0.5]", 40)
    verdict = {"EX1-P1_primary": {"estimate": p1.estimate, "interval": [p1.cluster_bootstrap_lo, p1.cluster_bootstrap_hi], "per_repeat": json.loads(p1.per_repeat), "supported": bool(p1.estimate > 0)},
               "EX1-P2_mechanism": {"specificity": p2s.estimate, "sensitivity": p2n.estimate, "supported": bool(p2s.estimate > 0 and p2n.estimate < 0)},
               "EX1-P3_control": {"estimate": p3.estimate, "interval": [p3.cluster_bootstrap_lo, p3.cluster_bootstrap_hi], "supported": bool(p3.estimate <= 0)},
               "EX1-P4_system": {"estimate": p4.estimate, "interval": [p4.cluster_bootstrap_lo, p4.cluster_bootstrap_hi], "supported": bool(p4.estimate > 0)},
               "fits": int(len(fits)), "fit_statuses": fits.status.value_counts().to_dict()}
    (EX / "EX1_RESULTS.json").write_text(json.dumps(verdict, indent=1), encoding="utf-8")
    pd.set_option("display.width", 250)
    print(mt.groupby(["population", "budget", "arm", "rule"])[["BA", "specificity", "sensitivity", "mean_pi_hat"]].mean().round(3).to_string())
    print(ct[ct.metric == "BA"].round(4).to_string()); print(json.dumps(verdict, indent=1))


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "manifest"
    {"manifest": write_manifest, "run": run, "evaluate": evaluate}[step]()
