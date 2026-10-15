"""TRAINED_AL evaluation (frozen with the protocol, before any TRAINED_AL outcome is viewed).

Readouts are pooled per repeat (the five fold test sets of a repeat partition NEW-136; each simulation appears once
per repeat) and averaged over repeats 3-4.  A readout exists only if all five trajectories of the repeat reached the
budget; otherwise it is UNAVAILABLE (never a surviving-subset value).  Decision rule p >= 0.5 for every arm.
Uncertainty: the Stage M class-stratified simulation-cluster bootstrap (2000 draws, seed 20261013), with the same
multiplicities for every arm, budget and repeat; it is conditional on the realised trajectories (it does not resample
the acquisition paths) and on two repeats of previously inspected simulations.
Evaluator-only quantities (short-K membership, q20 membership, VX region) are never inputs to any learner or selector.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import gzip
import json
import sys

import numpy as np
import pandas as pd

import src.jdl_evaluate as EV
import src.jdl_stage_m as SMM
import src.jdl_trained_al as TA

RES = TA.OUT / "results"
GRID = (16, 20, 24, 28, 32, 36, 40)
CHECKPOINTS = (16, 24, 32, 40)
CONTRASTS = (("C1_primary", "JT_PV", "G3_MARGIN"), ("C2_selection", "JT_PV", "JT_MARGIN"), ("C3_model", "JT_MARGIN", "G3_MARGIN"),
             ("S1", "ACTIVE_E1_STRADDLE", "G3_MARGIN"), ("S2", "JT_PV", "ACTIVE_E1_STRADDLE"), ("S3", "JT_MARGIN", "ACTIVE_E1_STRADDLE"))
PRACTICAL_AULC = 0.04            # about one more of the 12 negatives correctly rejected per repeat across the curve
SHORTK_TOL_EVENTS = 2            # at most two more missed short-K events than G3 (of 20 over two repeats) = 0.10 recall
TARGET = {"BA": 0.75, "shortK_sensitivity": 0.70, "q20": 0.70}     # development criterion; sustained over 2 consecutive grid points


def load():
    rows = {}
    for p in sorted(TA.CACHE.glob("NEW__*.json.gz")):
        r = json.loads(gzip.decompress(p.read_bytes()))
        rows[(r["repeat"], r["fold"], r["arm"])] = r
    return rows


def frame():
    old_s, old_e = SMM.REPEATS, EV.REPEATS
    SMM.REPEATS, EV.REPEATS = TA.REPEATS, TA.REPEATS
    try:
        tasks = [t for t in SMM.build_tasks() if t["population"] == "NEW"]
        F = EV.population_frame("NEW", tasks)
    finally:
        SMM.REPEATS, EV.REPEATS = old_s, old_e
    return tasks, F


def pooled(rows, F, arm, rep, b):
    """Pooled test probabilities of one repeat at budget b, or None if any fold is unavailable."""
    pos = {s: i for i, s in enumerate(F["ids"])}
    p = np.full(len(F["ids"]), np.nan)
    for f in TA.FOLDS:
        r = rows.get((rep, f, arm))
        if r is None:
            return None
        ev = {e["budget"]: e["p"] for e in r.get("evals", [])}
        if b not in ev:
            return None
        idx = [pos[s] for s in r["test_ids"]]
        p[idx] = ev[b]
    return p if np.isfinite(p).all() else None


def evaluate():
    rows = load()
    tasks, F = frame()
    y, sk = F["y"], F["shortk"]
    W = EV.boot_weights(y)
    budgets = range(TA.B_START, TA.B_END + 1)
    M = {}                                                                 # (arm, rep, b) -> dict of (D,) arrays
    for a in TA.ARMS:
        for rep in TA.REPEATS:
            for b in budgets:
                p = pooled(rows, F, a, rep, b)
                if p is not None:
                    M[(a, rep, b)] = EV.wmetrics(p, np.ones(len(p), bool), y, sk, F["q20"][rep], F["fold"][rep], W)
                    M[(a, rep, b)]["_counts"] = {"TP": int(((p >= .5) & (y == 1)).sum()), "FN": int(((p < .5) & (y == 1)).sum()), "TN": int(((p < .5) & (y == 0)).sum()),
                                                 "FP": int(((p >= .5) & (y == 0)).sum()), "shortK_detected": int(((p >= .5) & sk).sum()), "shortK_n": int(sk.sum())}
    mets = ("BA", "sensitivity", "specificity", "q20", "shortK_sensitivity", "AUC", "brier", "log_loss")
    by_budget = []
    for (a, rep, b), m in M.items():
        by_budget.append({"arm": a, "repeat": rep, "budget": b, **{k: float(m[k][0]) for k in mets if k in m}, **m["_counts"]})
    bb = pd.DataFrame(by_budget).sort_values(["arm", "repeat", "budget"])

    def aulc(a, rep, key="BA"):
        if not all((a, rep, b) in M for b in budgets):
            return None
        v = np.vstack([M[(a, rep, b)][key] for b in budgets])            # (n_budgets, D)
        return np.trapezoid(v, x=np.array(list(budgets), float), axis=0) / (TA.B_END - TA.B_START)

    au, contrasts = [], []
    A = {(a, rep, k): aulc(a, rep, k) for a in TA.ARMS for rep in TA.REPEATS for k in ("BA", "shortK_sensitivity", "q20")}
    for a in TA.ARMS:
        for k in ("BA", "shortK_sensitivity", "q20"):
            per = [A[(a, rep, k)] for rep in TA.REPEATS]
            au.append({"arm": a, "metric": f"{k}_AULC", "estimate": float(np.mean([x[0] for x in per])) if all(x is not None for x in per) else None,
                       "per_repeat": [None if x is None else float(x[0]) for x in per], "available": all(x is not None for x in per)})
    for name, c, ref in CONTRASTS:
        for k in ("BA", "shortK_sensitivity", "q20"):
            pa, pr = [A[(c, rep, k)] for rep in TA.REPEATS], [A[(ref, rep, k)] for rep in TA.REPEATS]
            if any(x is None for x in pa + pr):
                contrasts.append({"contrast": name, "arm": c, "ref": ref, "metric": f"{k}_AULC", "available": False}); continue
            d = np.mean([x - z for x, z in zip(pa, pr)], axis=0); lo, hi = np.nanpercentile(d[1:], [2.5, 97.5])
            contrasts.append({"contrast": name, "arm": c, "ref": ref, "metric": f"{k}_AULC", "available": True, "estimate": float(d[0]),
                              "per_repeat": [float(x[0] - z[0]) for x, z in zip(pa, pr)], "boot_lo": float(lo), "boot_hi": float(hi)})
    # checkpoint metrics (mean over repeats; available only if both repeats exist)
    cps = []
    for a in TA.ARMS:
        for b in CHECKPOINTS:
            if all((a, rep, b) in M for rep in TA.REPEATS):
                row = {"arm": a, "budget": b}
                for k in mets:
                    row[k] = float(np.mean([M[(a, rep, b)][k][0] for rep in TA.REPEATS]))
                for k in ("TP", "FN", "TN", "FP", "shortK_detected", "shortK_n"):
                    row[k + "_sum_repeats"] = int(sum(M[(a, rep, b)]["_counts"][k] for rep in TA.REPEATS))
                cps.append(row)
            else:
                cps.append({"arm": a, "budget": b, "available": False})
    cp = pd.DataFrame(cps)
    # short-K retention relative to G3 (evaluation guardrail; events summed over both repeats)
    ret = {}
    for a in TA.ARMS:
        r = {}
        for b in CHECKPOINTS:
            ok = all((x, rep, b) in M for x in (a, "G3_MARGIN") for rep in TA.REPEATS)
            if ok:
                da = sum(M[(a, rep, b)]["_counts"]["shortK_detected"] for rep in TA.REPEATS); dg = sum(M[("G3_MARGIN", rep, b)]["_counts"]["shortK_detected"] for rep in TA.REPEATS)
                r[f"B{b}"] = {"detected": da, "g3_detected": dg, "events": 2 * int(sk.sum()), "missed_vs_g3": dg - da, "retained": da >= dg - SHORTK_TOL_EVENTS}
        sa, sg = [A[(a, rep, "shortK_sensitivity")] for rep in TA.REPEATS], [A[("G3_MARGIN", rep, "shortK_sensitivity")] for rep in TA.REPEATS]
        if all(x is not None for x in sa + sg):
            r["shortK_AULC"] = {"arm": float(np.mean([x[0] for x in sa])), "g3": float(np.mean([x[0] for x in sg])),
                                "retained": float(np.mean([x[0] for x in sa])) >= float(np.mean([x[0] for x in sg])) - SHORTK_TOL_EVENTS / (2 * int(sk.sum()))}
        ret[a] = r
    # query efficiency: sustained attainment of the frozen target over two consecutive grid points (right-censored)
    att = []
    for a in TA.ARMS:
        for rep in TA.REPEATS:
            ok_at = {}
            for b in GRID:
                if (a, rep, b) in M:
                    m = M[(a, rep, b)]
                    ok_at[b] = bool(all(float(m[k][0]) >= v for k, v in TARGET.items()))
            reached = [b for b in GRID if b in ok_at]
            hit = next((b for i, b in enumerate(GRID[:-1]) if ok_at.get(b) and ok_at.get(GRID[i + 1])), None)
            last = max(reached) if reached else None
            att.append({"arm": a, "repeat": rep, "attained": hit is not None, "queries_to_sustained_target": hit,
                        "censored_at": None if hit is not None else last, "trajectory_complete": last == TA.B_END, "target_met_at": [b for b in GRID if ok_at.get(b)]})
    # where the queries went (evaluator-only description) and learner-visible paid composition
    VXd = dict(zip(F["ids"], F["VX"])); yd = dict(zip(F["ids"], y)); skd = dict(zip(F["ids"], sk))
    qp = []
    for (rep, f, a), r in rows.items():
        q = r.get("paid_ids", [])[TA.B_START:]
        qp.append({"arm": a, "repeat": rep, "fold": f, "status": r.get("status"), "queries_after_start": len(q),
                   "queried_fast_scan_EVALUATOR_ONLY": int(sum(VXd[s] > SMM.FAST_VX for s in q)), "queried_negatives": int(sum(yd[s] == 0 for s in q)),
                   "queried_shortK_EVALUATOR_ONLY": int(sum(bool(skd[s]) for s in q)), "unit_seconds": r.get("unit_seconds")})
    RES.mkdir(parents=True, exist_ok=True)
    bb.to_csv(RES / "metrics_by_budget.csv", index=False, lineterminator="\n"); cp.to_csv(RES / "checkpoints.csv", index=False, lineterminator="\n")
    pd.DataFrame(au).to_csv(RES / "aulc.csv", index=False, lineterminator="\n"); pd.DataFrame(contrasts).to_csv(RES / "contrasts.csv", index=False, lineterminator="\n")
    pd.DataFrame(att).to_csv(RES / "attainment.csv", index=False, lineterminator="\n"); pd.DataFrame(qp).to_csv(RES / "query_paths.csv", index=False, lineterminator="\n")
    status = {a: dict(pd.Series([r.get("status") for (rep, f, x), r in rows.items() if x == a]).value_counts()) for a in TA.ARMS}
    summary = {"study": TA.STUDY, "units_done": len(rows), "units_expected": len(TA.units()), "complete": len(rows) == len(TA.units()), "statuses": status,
               "practical_aulc_threshold": PRACTICAL_AULC, "shortK_tolerance_events": SHORTK_TOL_EVENTS, "target": TARGET, "shortK_retention": ret,
               "contrasts": contrasts, "aulc": au, "attainment": att}
    (RES / "TRAINED_AL_RESULTS.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("units_done", "units_expected", "complete", "statuses")}, indent=1, default=str))
    return summary


if __name__ == "__main__":
    evaluate()
