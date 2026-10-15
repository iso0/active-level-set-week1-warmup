"""ASTRA_AL evaluation (frozen with the protocol and manifest, before any ASTRA_AL outcome is viewed).

Primary readout: the delivered finite-batch decision (A_m >= B_m, m = 136, A1 level) of Astra's V2 model on the pooled
test simulations of each repeat (the five fold test sets of a repeat partition NEW-136).  A readout at budget b exists for
a repeat only if all five trajectories of that arm reached b with a numerically accepted test decision; otherwise it is
UNAVAILABLE (never a surviving-subset value, never carried forward).  Endpoint: BA-AULC over B16-B24 (trapezoid / 8), mean
over repeats 3-4, per-repeat values always reported.  Secondary readouts on the same posterior: the 0.5 cutoff of the
mixture probability, and AUC, Brier and log loss of the mixture probability.
Uncertainty: the Stage M class-stratified simulation-cluster bootstrap (2000 draws, seed 20261013) with identical
multiplicities for every arm, budget and repeat; conditional on the realised trajectories and fits and on two repeats of
previously inspected simulations.  It is not a confirmation interval.
Prospective adoption rule (thresholds fixed before the run, as Astra's draft requires): a selector is "practically better"
than a comparator only if the mean BA-AULC contrast is >= 0.02, its 95% bootstrap interval excludes 0, both repeats agree
in sign, and the short-K guardrail holds at B24 (at most 2 more missed short-K events, of 20 over two repeats, than the
comparator).  A gain that fails only the guardrail is a trade-off; anything else is "no practical difference established".
Evaluator-only quantities (short-K membership, q20 membership, VX region) are never inputs to any learner or selector.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import gzip
import json

import numpy as np
import pandas as pd

import src.jdl_astra_al as AA
import src.jdl_evaluate as EV
import src.jdl_stage_m as SMM
import src.jdl_trained_al_eval as TE

RES = AA.OUT / "results"
BUDGETS = tuple(range(AA.B_START, AA.B_END + 1))
CHECKPOINTS = (16, 20, 24)
CONTRASTS = (("P1_primary", "BA_RISK", "ALIGNED_MARGIN"), ("P2_primary", "BA_RISK", "V2_VARIANCE"), ("S1", "V2_VARIANCE", "ALIGNED_MARGIN"))
PRIMARY = ("P1_primary", "P2_primary")
PRACTICAL_AULC = 0.02            # mean BA over B16-B24 higher by 0.02 = about one more correct class-balanced call in 25 per repeat
SHORTK_TOL_EVENTS = 2            # at most two more missed short-K events at B24 than the comparator (of 20 over two repeats)
DEC_KEYS = ("BA", "sensitivity", "specificity", "q20", "shortK_sensitivity")
PROB_KEYS = ("AUC", "brier", "log_loss")


def load():
    rows = {}
    for p in sorted(AA.CACHE.glob("NEW__*.json.gz")):
        r = json.loads(gzip.decompress(p.read_bytes()))
        rows[(r["repeat"], r["fold"], r["arm"])] = r
    return rows


def pooled(rows, F, arm, rep, b):
    """Pooled test probabilities and finite-batch decisions of one repeat at budget b, or None if unavailable."""
    pos = {s: i for i, s in enumerate(F["ids"])}
    p = np.full(len(F["ids"]), np.nan); d = p.copy()
    for f in AA.FOLDS:
        r = rows.get((rep, f, arm))
        if r is None:
            return None
        e = {x["budget"]: x for x in r.get("evals", [])}.get(b)
        if e is None or not e.get("test_decision_accepted", False):
            return None
        idx = [pos[s] for s in r["test_ids"]]
        p[idx] = e["p"]; d[idx] = e["finite_batch"]
    if not (np.isfinite(p).all() and np.isfinite(d).all()):
        return None
    return p, d


def evaluate():
    rows = load()
    tasks, F = TE.frame()
    y, sk = F["y"], F["shortk"]
    W = EV.boot_weights(y)
    M, per_sim = {}, []
    for a in AA.ARMS:
        for rep in AA.REPEATS:
            for b in BUDGETS:
                q = pooled(rows, F, a, rep, b)
                if q is None:
                    continue
                p, d = q; ones = np.ones(len(p), bool)
                md = EV.wmetrics(d.astype(float), ones, y, sk, F["q20"][rep], F["fold"][rep], W)
                mp = EV.wmetrics(p, ones, y, sk, F["q20"][rep], F["fold"][rep], W)
                M[(a, rep, b)] = {**{k: md[k] for k in DEC_KEYS}, **{f"p05_{k}": mp[k] for k in DEC_KEYS}, **{k: mp[k] for k in PROB_KEYS},
                                  "_counts": {"TP": int(((d == 1) & (y == 1)).sum()), "FN": int(((d == 0) & (y == 1)).sum()), "TN": int(((d == 0) & (y == 0)).sum()),
                                              "FP": int(((d == 1) & (y == 0)).sum()), "shortK_detected": int(((d == 1) & sk).sum()), "shortK_n": int(sk.sum()),
                                              "decided_positive": int(d.sum()), "decision_differs_from_p05": int(((p >= .5).astype(int) != d.astype(int)).sum())}}
                per_sim += [{"arm": a, "repeat": rep, "budget": b, "sim_id": s, "y_EVALUATOR": int(yy), "shortK_EVALUATOR": bool(kk), "finite_batch": int(dd), "p": float(pp)}
                            for s, yy, kk, dd, pp in zip(F["ids"], y, sk, d, p)]
    keys = DEC_KEYS + tuple(f"p05_{k}" for k in DEC_KEYS) + PROB_KEYS
    bb = pd.DataFrame([{"arm": a, "repeat": rep, "budget": b, **{k: float(m[k][0]) for k in keys}, **m["_counts"]} for (a, rep, b), m in M.items()])
    if len(bb):
        bb = bb.sort_values(["arm", "repeat", "budget"])

    def aulc(a, rep, key):
        if not all((a, rep, b) in M for b in BUDGETS):
            return None
        v = np.vstack([M[(a, rep, b)][key] for b in BUDGETS])
        return np.trapezoid(v, x=np.array(BUDGETS, float), axis=0) / (AA.B_END - AA.B_START)

    akeys = ("BA", "shortK_sensitivity", "q20", "p05_BA", "AUC")
    A = {(a, rep, k): aulc(a, rep, k) for a in AA.ARMS for rep in AA.REPEATS for k in akeys}
    au = []
    for a in AA.ARMS:
        for k in akeys:
            per = [A[(a, rep, k)] for rep in AA.REPEATS]
            au.append({"arm": a, "metric": f"{k}_AULC", "available": all(x is not None for x in per),
                       "estimate": float(np.mean([x[0] for x in per])) if all(x is not None for x in per) else None,
                       "per_repeat": [None if x is None else float(x[0]) for x in per]})
    # short-K guardrail at B24 (finite-batch decision; events summed over both repeats)
    def shortk_b24(a):
        if not all((a, rep, AA.B_END) in M for rep in AA.REPEATS):
            return None
        return sum(M[(a, rep, AA.B_END)]["_counts"]["shortK_detected"] for rep in AA.REPEATS)
    contrasts = []
    for name, c, ref in CONTRASTS:
        for k in akeys:
            pa, pr = [A[(c, rep, k)] for rep in AA.REPEATS], [A[(ref, rep, k)] for rep in AA.REPEATS]
            if any(x is None for x in pa + pr):
                contrasts.append({"contrast": name, "arm": c, "ref": ref, "metric": f"{k}_AULC", "available": False}); continue
            d = np.mean([x - z for x, z in zip(pa, pr)], axis=0); lo, hi = np.nanpercentile(d[1:], [2.5, 97.5])
            row = {"contrast": name, "arm": c, "ref": ref, "metric": f"{k}_AULC", "available": True, "estimate": float(d[0]),
                   "per_repeat": [float(x[0] - z[0]) for x, z in zip(pa, pr)], "boot_lo": float(lo), "boot_hi": float(hi)}
            if k == "BA":
                dc, dr = shortk_b24(c), shortk_b24(ref)
                guard = None if dc is None or dr is None else bool(dc >= dr - SHORTK_TOL_EVENTS)
                gain = bool(row["estimate"] >= PRACTICAL_AULC and lo > 0 and all(v > 0 for v in row["per_repeat"]))
                row.update({"shortK_detected_B24": dc, "ref_shortK_detected_B24": dr, "shortK_events_B24": 2 * int(sk.sum()), "guardrail_ok": guard,
                            "verdict": ("PRACTICALLY BETTER" if gain and guard else "TRADE-OFF (BA gain with short-K loss)" if gain and guard is False
                                        else "NO PRACTICAL DIFFERENCE ESTABLISHED")})
            contrasts.append(row)
    cps = []
    for a in AA.ARMS:
        for b in CHECKPOINTS:
            if all((a, rep, b) in M for rep in AA.REPEATS):
                row = {"arm": a, "budget": b, "available": True, **{k: float(np.mean([M[(a, rep, b)][k][0] for rep in AA.REPEATS])) for k in keys}}
                for k in ("TP", "FN", "TN", "FP", "shortK_detected", "shortK_n", "decision_differs_from_p05"):
                    row[k + "_sum_repeats"] = int(sum(M[(a, rep, b)]["_counts"][k] for rep in AA.REPEATS))
                cps.append(row)
            else:
                cps.append({"arm": a, "budget": b, "available": False})
    # numerics, costs and where the queries went (evaluator-only description)
    VXd = dict(zip(F["ids"], F["VX"])); yd = dict(zip(F["ids"], y)); skd = dict(zip(F["ids"], sk))
    units, steps = [], []
    for (rep, f, a), r in sorted(rows.items()):
        q = r.get("paid_ids", [])[AA.B_START:]
        units.append({"arm": a, "repeat": rep, "fold": f, "status": r.get("status"), "last_budget": max([e["budget"] for e in r.get("evals", [])], default=None),
                      "queries_after_start": len(q), "fits_executed": r.get("fits_executed"), "component_solves": r.get("component_solves"),
                      "unit_seconds": r.get("unit_seconds"), "resumed_at": r.get("resumed_at"),
                      "queried_fast_scan_EVALUATOR_ONLY": int(sum(VXd[s] > SMM.FAST_VX for s in q)), "queried_negatives": int(sum(yd[s] == 0 for s in q)),
                      "queried_shortK_EVALUATOR_ONLY": int(sum(bool(skd[s]) for s in q))})
        for s in r.get("steps", []):
            steps.append({"arm": a, "repeat": rep, "fold": f, "budget": s.get("budget"), "selector_status": s.get("selector_status"), "status": s.get("status"),
                          "fallback": s.get("fallback"), "risk_levels_after_first": len(s.get("history") or []) if a == "BA_RISK" else None,
                          "ranking_resolved": s.get("ranking_resolved"), "n_near_ties": len(s.get("near_tie_ids") or []), "score_evaluations": s.get("score_evaluations"),
                          "score_seconds": s.get("score_seconds"), "seconds": s.get("seconds"), "response_availability": s.get("response_availability"),
                          "low_ess_outcome_mass": s.get("low_ess_outcome_mass"), "max_tower_risk_difference": s.get("max_tower_risk_difference")})
    U, S = pd.DataFrame(units), pd.DataFrame(steps)
    caps = {"fits_executed": int(U.fits_executed.sum()) if len(U) else 0, "component_solves": int(U.component_solves.sum()) if len(U) else 0, **AA.CAPS}
    caps["within_caps"] = caps["fits_executed"] <= AA.CAPS["top_level_requests"] and caps["component_solves"] <= AA.CAPS["component_solves_including_fallback"]
    RES.mkdir(parents=True, exist_ok=True)
    for name, df in (("metrics_by_budget", bb), ("checkpoints", pd.DataFrame(cps)), ("aulc", pd.DataFrame(au)), ("contrasts", pd.DataFrame(contrasts)),
                     ("units", U), ("steps", S), ("per_simulation_decisions", pd.DataFrame(per_sim))):
        df.to_csv(RES / f"{name}.csv", index=False, lineterminator="\n")
    done = {a: int(sum(1 for (_, _, x) in rows if x == a)) for a in AA.ARMS}
    summary = {"study": AA.STUDY, "units_done": len(rows), "units_expected": len(AA.units()), "units_done_by_arm": done,
               "complete": len(rows) == len(AA.units()), "statuses": {a: dict(pd.Series([r.get("status") for (rep, f, x), r in rows.items() if x == a]).value_counts()) for a in AA.ARMS},
               "practical_aulc_threshold": PRACTICAL_AULC, "shortK_tolerance_events": SHORTK_TOL_EVENTS, "contrasts": contrasts, "aulc": au, "caps": caps,
               "note": "UNAVAILABLE readouts are never replaced by surviving subsets; partial units are not loaded"}
    (RES / "ASTRA_AL_RESULTS.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("units_done", "units_expected", "units_done_by_arm", "complete", "statuses", "caps")}, indent=1, default=str))
    return summary


if __name__ == "__main__":
    evaluate()
