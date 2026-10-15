"""CORNER_LOCAL evaluation (frozen with the protocol, before any CORNER_LOCAL outcome is viewed).

Readouts are pooled per repeat (the five fold test sets of a repeat partition NEW-136) and a readout exists only if all
five folds reached the budget (otherwise UNAVAILABLE; never a surviving subset).  Decision cutoff 0.5 for every predictor.
Corner = VX > 0.85 m/s, an EVALUATOR-ONLY description (the learner never sees it); corner metrics use the 23 corner runs.
Uncertainty: the Stage M class-stratified simulation-cluster bootstrap (2000 draws, seed 20261013), identical multiplicities
for every predictor, arm, budget and repeat; conditional on the realised paths and fits; previously inspected simulations.
Prospective verdicts
  L1 (primary, local discrimination): corner AUC at B40 on TREED_MARGIN's paid sets, TREED - TREED_PERM, mean of repeats
     3-4.  SUPPORTED iff the 95% interval is above 0; otherwise NOT SUPPORTED.  Reported beside it: the same on the fixed
     paths (repeats 1-2), per repeat, at B24/B32, and TREED - TREED_CONST (the split alone).
  L2 (system): TREED_MARGIN - JT_MARGIN (TRAINED_AL, same frozen starts) BA-AULC over B16-B40.  "Practically better" iff
     >= +0.04, interval above 0, both repeats positive and short-K at B40 at most 2 missed events (of 20) worse than
     JT_MARGIN; a BA gain failing only the short-K condition is a TRADE-OFF; anything else NO PRACTICAL DIFFERENCE.
     Against G3 / ACTIVE E1 only repeat 4 exists (descriptive; the repeat-3 controls are unavailable by protocol).
  L3 (path held fixed): TREED - JT on TREED_MARGIN's own paid sets (predictor effect without a path difference).
  Query efficiency: the TRAINED_AL target (BA >= 0.75, short-K >= 0.70, q20 >= 0.70, sustained over two consecutive grid
     points of 16..40 step 4), right-censored at B40; a saving is reported only if TREED_MARGIN attains it in both repeats,
     as a lower bound against censored comparators (every query, start included, counted).
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import gzip
import json

import numpy as np
import pandas as pd

import src.jdl_corner_local as CL
import src.jdl_evaluate as EV
import src.jdl_stage_m as SMM
import src.jdl_trained_al_eval as TE

RES = CL.OUT / "results"
BUDGETS = tuple(range(CL.B_START, CL.B_END + 1))
GRID = tuple(range(16, 41, 4))
CHECKPOINTS = (16, 24, 32, 40)
PRACTICAL_AULC = 0.04
SHORTK_TOL_EVENTS = 2
KEYS = ("BA", "sensitivity", "specificity", "q20", "shortK_sensitivity", "AUC", "brier", "log_loss")
CKEYS = ("BA", "sensitivity", "specificity", "AUC")


def load():
    adaptive, fixed = {}, []
    for p in sorted(CL.CACHE.glob("NEW__*.json.gz")):
        r = json.loads(gzip.decompress(p.read_bytes()))
        if "rows" in r:
            fixed = r["rows"]
        else:
            adaptive[(r["repeat"], r["fold"])] = r
    return adaptive, fixed


def frame_r12():
    old_s, old_e = SMM.REPEATS, EV.REPEATS
    SMM.REPEATS, EV.REPEATS = CL.FIXED_REPEATS, CL.FIXED_REPEATS
    try:
        tasks = [t for t in SMM.build_tasks() if t["population"] == "NEW"]
        F = EV.population_frame("NEW", tasks)
    finally:
        SMM.REPEATS, EV.REPEATS = old_s, old_e
    return F


def _pool(F, per_fold):
    """per_fold: list of (test_ids, p) for the five folds of a repeat -> pooled p or None."""
    if len(per_fold) != len(CL.FOLDS):
        return None
    pos = {s: i for i, s in enumerate(F["ids"])}; p = np.full(len(F["ids"]), np.nan)
    for ids, q in per_fold:
        p[[pos[s] for s in ids]] = q
    return p if np.isfinite(p).all() else None


def metrics(F, p, rep, W):
    y, sk = F["y"], F["shortk"]; corner = np.asarray(F["VX"], float) > SMM.FAST_VX
    m = EV.wmetrics(p, np.ones(len(p), bool), y, sk, F["q20"][rep], F["fold"][rep], W)
    c = EV.wmetrics(p, corner, y, sk, F["q20"][rep], F["fold"][rep], W)
    out = {k: m[k] for k in KEYS}; out.update({f"corner_{k}": c[k] for k in CKEYS})
    d = p >= .5
    out["_counts"] = {"TP": int((d & (y == 1)).sum()), "FN": int((~d & (y == 1)).sum()), "TN": int((~d & (y == 0)).sum()), "FP": int((d & (y == 0)).sum()),
                      "shortK_detected": int((d & sk).sum()), "shortK_n": int(sk.sum()), "corner_TP": int((d & corner & (y == 1)).sum()),
                      "corner_FN": int((~d & corner & (y == 1)).sum()), "corner_TN": int((~d & corner & (y == 0)).sum()), "corner_FP": int((d & corner & (y == 0)).sum())}
    return out


def _diff(A, B, key):
    """Mean over repeats of A - B (lists of metric dicts per repeat) for one key -> (estimate, lo, hi, per_repeat)."""
    d = np.mean([a[key] - b[key] for a, b in zip(A, B)], axis=0); lo, hi = np.nanpercentile(d[1:], [2.5, 97.5])
    return float(d[0]), float(lo), float(hi), [float(a[key][0] - b[key][0]) for a, b in zip(A, B)]


def evaluate():
    adaptive, fixed = load()
    _, F = TE.frame(); W = EV.boot_weights(F["y"])
    ta_rows = TE.load()
    M = {}
    for rep in CL.REPEATS:
        for b in BUDGETS:
            for k in CL.PREDICTORS:
                per = []
                for f in CL.FOLDS:
                    r = adaptive.get((rep, f)); e = None if r is None else {x["budget"]: x for x in r["evals"]}.get(b)
                    if e is not None:
                        per.append((r["test_ids"], e[k]))
                p = _pool(F, per)
                if p is not None:
                    M[(f"{k}@TREED_PATHS", rep, b)] = metrics(F, p, rep, W)
            for arm in ("JT_MARGIN", "G3_MARGIN", "ACTIVE_E1_STRADDLE"):
                p = TE.pooled(ta_rows, F, arm, rep, b)
                if p is not None:
                    M[(f"{arm}@OWN_PATHS", rep, b)] = metrics(F, p, rep, W)
    # fixed paths, repeats 1-2
    F12 = frame_r12(); W12 = EV.boot_weights(F12["y"]); MF = {}
    for rep in CL.FIXED_REPEATS:
        for b in CL.FIXED_BUDGETS:
            for k in CL.PREDICTORS:
                per = [(x["test_ids"], x[k]) for x in fixed if x["repeat"] == rep and x["budget"] == b]
                p = _pool(F12, per)
                if p is not None:
                    MF[(k, rep, b)] = metrics(F12, p, rep, W12)
    rows = [{"setting": s, "repeat": rep, "budget": b, **{k: float(m[k][0]) for k in KEYS}, **{f"corner_{k}": float(m[f'corner_{k}'][0]) for k in CKEYS}, **m["_counts"]}
            for (s, rep, b), m in M.items()]
    rows += [{"setting": f"{k}@FIXED_PATHS", "repeat": rep, "budget": b, **{q: float(m[q][0]) for q in KEYS}, **{f"corner_{q}": float(m[f'corner_{q}'][0]) for q in CKEYS},
              **m["_counts"]} for (k, rep, b), m in MF.items()]
    bb = pd.DataFrame(rows)
    if len(bb):
        bb = bb.sort_values(["setting", "repeat", "budget"])
    have = lambda s, b: all((s, rep, b) in M for rep in CL.REPEATS)
    res = {"units_done": len(adaptive) + (1 if fixed else 0), "units_expected": len(CL.units()), "complete": len(adaptive) == 10 and bool(fixed)}
    # L1 primary and its companions
    L1 = {}
    for b in (24, 32, 40):
        if have("TREED@TREED_PATHS", b) and have("TREED_PERM@TREED_PATHS", b):
            A = [M[("TREED@TREED_PATHS", rep, b)] for rep in CL.REPEATS]; B = [M[("TREED_PERM@TREED_PATHS", rep, b)] for rep in CL.REPEATS]
            C = [M[("TREED_CONST@TREED_PATHS", rep, b)] for rep in CL.REPEATS]; J = [M[("JT@TREED_PATHS", rep, b)] for rep in CL.REPEATS]
            for name, R in (("TREED-TREED_PERM", B), ("TREED-TREED_CONST", C), ("TREED-JT", J)):
                for key in ("corner_AUC", "corner_BA", "BA", "shortK_sensitivity"):
                    e, lo, hi, per = _diff(A, R, key)
                    L1[f"B{b}:{name}:{key}"] = {"estimate": e, "lo": lo, "hi": hi, "per_repeat": per}
    prim = L1.get("B40:TREED-TREED_PERM:corner_AUC")
    res["L1_primary"] = None if prim is None else {**prim, "verdict": "SUPPORTED" if prim["lo"] > 0 else "NOT SUPPORTED"}
    res["L1_companions"] = L1
    FX = {}
    for b in CL.FIXED_BUDGETS:
        if all((k, rep, b) in MF for k in CL.PREDICTORS for rep in CL.FIXED_REPEATS):
            A = [MF[("TREED", rep, b)] for rep in CL.FIXED_REPEATS]
            for name in ("TREED_PERM", "TREED_CONST", "JT"):
                R = [MF[(name, rep, b)] for rep in CL.FIXED_REPEATS]
                for key in ("corner_AUC", "corner_BA", "BA", "shortK_sensitivity", "specificity"):
                    e, lo, hi, per = _diff(A, R, key)
                    FX[f"B{b}:TREED-{name}:{key}"] = {"estimate": e, "lo": lo, "hi": hi, "per_repeat": per}
    res["fixed_path_contrasts"] = FX

    # L2 system contrast against JT_MARGIN (and descriptive repeat-4 contrasts against G3 / ACTIVE E1)
    def aulc(s, rep, key):
        if not all((s, rep, b) in M for b in BUDGETS):
            return None
        v = np.vstack([M[(s, rep, b)][key] for b in BUDGETS])
        return np.trapezoid(v, x=np.array(BUDGETS, float), axis=0) / (CL.B_END - CL.B_START)
    L2 = {}
    for key in ("BA", "shortK_sensitivity", "q20", "corner_AUC"):
        a = [aulc("TREED@TREED_PATHS", rep, key) for rep in CL.REPEATS]; j = [aulc("JT_MARGIN@OWN_PATHS", rep, key) for rep in CL.REPEATS]
        if any(x is None for x in a + j):
            L2[f"{key}_AULC"] = {"available": False}; continue
        d = np.mean([x - z for x, z in zip(a, j)], axis=0); lo, hi = np.nanpercentile(d[1:], [2.5, 97.5])
        L2[f"{key}_AULC"] = {"available": True, "treed": float(np.mean([x[0] for x in a])), "jt_margin": float(np.mean([x[0] for x in j])),
                             "estimate": float(d[0]), "lo": float(lo), "hi": float(hi), "per_repeat": [float(x[0] - z[0]) for x, z in zip(a, j)]}
    if L2.get("BA_AULC", {}).get("available") and have("TREED@TREED_PATHS", 40) and have("JT_MARGIN@OWN_PATHS", 40):
        dt_ = sum(M[("TREED@TREED_PATHS", rep, 40)]["_counts"]["shortK_detected"] for rep in CL.REPEATS)
        dj = sum(M[("JT_MARGIN@OWN_PATHS", rep, 40)]["_counts"]["shortK_detected"] for rep in CL.REPEATS)
        q = L2["BA_AULC"]; gain = q["estimate"] >= PRACTICAL_AULC and q["lo"] > 0 and all(v > 0 for v in q["per_repeat"])
        guard = dt_ >= dj - SHORTK_TOL_EVENTS
        L2["verdict"] = "PRACTICALLY BETTER" if gain and guard else "TRADE-OFF (BA gain with short-K loss)" if gain else "NO PRACTICAL DIFFERENCE ESTABLISHED"
        L2["shortK_detected_B40"] = {"TREED_MARGIN": dt_, "JT_MARGIN": dj, "events": 2 * int(F["shortk"].sum())}
    r4 = {}
    for arm in ("G3_MARGIN", "ACTIVE_E1_STRADDLE"):
        a, g = aulc("TREED@TREED_PATHS", 4, "BA"), aulc(f"{arm}@OWN_PATHS", 4, "BA")
        if a is not None and g is not None:
            d = a - g; lo, hi = np.nanpercentile(d[1:], [2.5, 97.5])
            r4[f"TREED_MARGIN-{arm}:BA_AULC:repeat4"] = {"estimate": float(d[0]), "lo": float(lo), "hi": float(hi)}
        if ("TREED@TREED_PATHS", 4, 40) in M and (f"{arm}@OWN_PATHS", 4, 40) in M:
            r4[f"shortK_detected_B40_repeat4:{arm}"] = {"TREED_MARGIN": M[("TREED@TREED_PATHS", 4, 40)]["_counts"]["shortK_detected"],
                                                        arm: M[(f"{arm}@OWN_PATHS", 4, 40)]["_counts"]["shortK_detected"], "events": int(F["shortk"].sum())}
    res["L2_system"] = L2; res["repeat4_descriptive"] = r4
    # target attainment (right-censored at B40)
    att = []
    for s in ("TREED@TREED_PATHS", "JT_MARGIN@OWN_PATHS", "G3_MARGIN@OWN_PATHS", "ACTIVE_E1_STRADDLE@OWN_PATHS"):
        for rep in CL.REPEATS:
            ok = {b: bool(all(float(M[(s, rep, b)][k][0]) >= v for k, v in TE.TARGET.items())) for b in GRID if (s, rep, b) in M}
            hit = next((b for i, b in enumerate(GRID[:-1]) if ok.get(b) and ok.get(GRID[i + 1])), None)
            att.append({"setting": s, "repeat": rep, "available": bool(ok), "queries_to_sustained_target": hit,
                        "censored_at": None if hit is not None or not ok else max(ok), "target_met_at": [b for b in GRID if ok.get(b)]})
    res["attainment"] = att
    sav = [a for a in att if a["setting"] == "TREED@TREED_PATHS"]
    res["query_saving"] = ("lower bound reportable" if all(a["queries_to_sustained_target"] is not None for a in sav) and len(sav) == 2
                           else "NONE MEASURED (target not attained in both repeats)")
    # where the queries went (evaluator-only) and region diagnostics
    VXd = dict(zip(F["ids"], F["VX"])); yd = dict(zip(F["ids"], F["y"])); skd = dict(zip(F["ids"], F["shortk"]))
    qp, rg = [], []
    for (rep, f), r in sorted(adaptive.items()):
        q = r.get("paid_ids", [])[CL.B_START:]
        qp.append({"repeat": rep, "fold": f, "status": r["status"], "queries_after_start": len(q), "queried_fast_scan_EVALUATOR_ONLY": int(sum(VXd[s] > SMM.FAST_VX for s in q)),
                   "queried_negatives": int(sum(yd[s] == 0 for s in q)), "queried_shortK_EVALUATOR_ONLY": int(sum(bool(skd[s]) for s in q)), "unit_seconds": r.get("unit_seconds")})
        for s in r["steps"]:
            lo = s.get("local") or {}
            rg.append({"repeat": rep, "fold": f, "budget": s["budget"], "stump_type": s["stump"].get("type"), "cut": s["stump"].get("cut"), "leaf": s["leaf"],
                       "leaf_score": s["leaf_score"], "region_paid": (lo.get("TREED") or {}).get("n_region_paid"), "region_n1": (lo.get("TREED") or {}).get("n1"),
                       "region_n0": (lo.get("TREED") or {}).get("n0"), "local_type": (lo.get("TREED") or {}).get("type"), "local_kernel": (lo.get("TREED") or {}).get("kernel"),
                       "perm_kernel": (lo.get("TREED_PERM") or {}).get("kernel"), "selected_in_region": s.get("selected_in_region")})
    RES.mkdir(parents=True, exist_ok=True)
    bb.to_csv(RES / "metrics_by_budget.csv", index=False, lineterminator="\n"); pd.DataFrame(qp).to_csv(RES / "query_paths.csv", index=False, lineterminator="\n")
    pd.DataFrame(rg).to_csv(RES / "region_diagnostics.csv", index=False, lineterminator="\n")
    (RES / "CORNER_LOCAL_RESULTS.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("units_done", "units_expected", "complete", "L1_primary", "query_saving")}, indent=1, default=str))
    return res


if __name__ == "__main__":
    evaluate()
