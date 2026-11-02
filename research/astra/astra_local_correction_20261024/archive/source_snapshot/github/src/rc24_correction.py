"""RC24 section 2 - dated correction (2026-10-21) of the RC23 decision rule, plus the missing direct acceptance witness.

Defect in the FROZEN src/rc23_eval.py::decide (the file is NOT edited; it stays the recorded RC23 source):
  pass = all(x["verdict"].startswith("NON-INFERIOR") for x in ni) and not sp["verdict"].startswith("MORE") and rob
  * the failing verdict string "NON-INFERIORITY NOT SHOWN" also starts with "NON-INFERIOR", so a FAILED non-inferiority test passed;
  * spend_pair() returns verdict "INCOMPLETE" when no unit is paired, which passed as "not MORE";
  * robust_ok() only loops over the conditions it is given, so a missing condition (or a missing window) passed.
Correction (this module): every component returns an explicit status from numeric conditions, never from a string prefix.
  non-inferiority  PASS       n == expected paired repeats and finite one-sided 95 % lower bound >= -delta
                   FAIL       n == expected and finite lower bound < -delta
                   INCOMPLETE otherwise (missing repeats, n < 2, non-finite bound)
  spend            PASS       units == expected and verdict exactly "FEWER SIMULATIONS (DEV)" or "NO CLEAR DIFFERENCE (DEV)"
                   FAIL       units == expected and verdict exactly "MORE SIMULATIONS (DEV)"
                   INCOMPLETE otherwise (verdict "INCOMPLETE", missing or partial units)
  robustness       per required condition (STD, RAND8, LOCAL8, BLOCK) x window (B8-B24, B8-B60), with the frozen RC22 contrast:
                   FAIL       verdict exactly "WORSE (DEV)", or window B8-B60 with finite mean < -0.010
                   INCOMPLETE condition / window absent, n != expected, verdict "INCOMPLETE" or non-finite mean
                   PASS       otherwise;  the robustness status is FAIL if any cell FAILs, else INCOMPLETE if any cell is INCOMPLETE
  candidate        FAIL if any component FAILs, else INCOMPLETE if any is INCOMPLETE, else PASS
  decision         HA_LEAN PASS -> D1;  HA_LEAN FAIL and HA_LR PASS -> D2;  both FAIL -> D3;  anything INCOMPLETE on the path -> INCOMPLETE
The RC23 decision is recomputed from the SAVED RC23 tables (fold-pooled metric CSVs; no GP refit) with both rules, the recomputed
numbers are checked against RC23/DECISION.json, and negative controls (real-data and synthetic) show that failing or incomplete
inputs cannot reach D1 under the corrected rule while the old rule lets them through.

Witness (direct, separate from HA_LR): on one recorded paid state, a channel (temperature, spike or both) is removed from EVERY paid
run; each construction is computed ALONE and its outcome recorded (exception or finite / non-finite output). A control state with no
channel removed checks that the witness test is not vacuous (it must report a finite PHR_NRMAP there).
    python -m src.rc24_correction decision | witness
"""
from __future__ import annotations

import json
import sys
import traceback

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc22_eval as E22
import src.rc23_eval as E23

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc24" / "correction"
R23 = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc23"
R22 = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc22"
PASS, FAIL, INCOMPLETE = "PASS", "FAIL", "INCOMPLETE"
CONDITIONS = ("STD", "RAND8", "LOCAL8", "BLOCK")
WINDOWS = ("small", "all")
EXPECTED_N = 8
SPEND_OK = ("FEWER SIMULATIONS (DEV)", "NO CLEAR DIFFERENCE (DEV)")
SPEND_BAD = "MORE SIMULATIONS (DEV)"


def _combine(statuses):
    s = list(statuses)
    return FAIL if FAIL in s else INCOMPLETE if (INCOMPLETE in s or not s) else PASS


# ======================================================================================== corrected components
def ni_status(T, a, b, metric="BA", delta=E23.DELTA, n_expected=EXPECTED_N):
    r = E23.noninferiority(T, a, b, metric, delta)
    n = int(r["good"].split("/")[1]); lcb = r["lower_95"]
    if n != n_expected or n < 2 or lcb is None or not np.isfinite(lcb):
        st = INCOMPLETE
    else:
        st = PASS if lcb >= -delta else FAIL
    return {**r, "n": n, "status": st}


def spend_status(E, a, b, target="BA >= 0.93", n_expected=EXPECTED_N):
    r = E23.spend_pair(E, a, b, target); units = int(r.get("units", 0) or 0); v = r["verdict"]
    if units != n_expected or v == "INCOMPLETE":
        st = INCOMPLETE
    elif v == SPEND_BAD:
        st = FAIL
    elif v in SPEND_OK:
        st = PASS
    else:
        st = INCOMPLETE
    return {**r, "status": st}


def robust_status(Ts, a, b, required=CONDITIONS, n_expected=EXPECTED_N):
    cells = []
    for cond in required:
        for w in WINDOWS:
            if cond not in Ts or w not in Ts[cond]:
                cells.append({"condition": cond, "window": w, "verdict": "ABSENT", "status": INCOMPLETE}); continue
            r = E22.contrast(Ts[cond][w], a, b, "BA", 0.020, "higher"); n = int(r["good"].split("/")[1]); m = r["mean"]
            if r["verdict"] == "WORSE (DEV)" or (w == "all" and m is not None and np.isfinite(m) and m < -0.010):
                st = FAIL
            elif n != n_expected or r["verdict"] == "INCOMPLETE" or m is None or not np.isfinite(m):
                st = INCOMPLETE
            else:
                st = PASS
            cells.append({"condition": cond, "window": w, **r, "n": n, "status": st})
    return _combine(c["status"] for c in cells), cells


def decide_corrected(A_std, E_std, Ts, R="PHR_NRMAP", S="HA_LR", L="HA_LEAN", n_expected=EXPECTED_N, required=CONDITIONS):
    out = {}
    for cand in (L, S):
        ni = [ni_status(A_std[w], cand, R, n_expected=n_expected) for w in WINDOWS] if all(w in A_std for w in WINDOWS) else \
             [{"window": w, "status": INCOMPLETE} for w in WINDOWS]
        sp = spend_status(E_std, cand, R, n_expected=n_expected); rob, cells = robust_status(Ts, cand, R, required, n_expected)
        comp = {"noninferiority_B8_B24": ni[0]["status"], "noninferiority_B8_B60": ni[1]["status"], "spend_BA_0.93": sp["status"], "robustness": rob}
        out[cand] = {"components": comp, "status": _combine(comp.values()), "noninferiority": ni, "spend_BA_0.93": sp, "robust_cells": cells}
    sl, ss = out[L]["status"], out[S]["status"]
    if sl == PASS:
        dec = "D1: the fully lean system is sufficient - HA_LEAN + margin"
    elif sl == INCOMPLETE:
        dec = "INCOMPLETE: HA_LEAN status incomplete - no decision"
    elif ss == PASS:
        dec = "D2: the shared upstream is needed - HA_LR + margin"
    elif ss == FAIL:
        dec = "D3: simplification not robust enough - keep PHR_NRMAP + margin"
    else:
        dec = "INCOMPLETE: HA_LEAN FAIL and HA_LR status incomplete - D2/D3 undetermined"
    return dec, out


# ======================================================================================== saved RC23 tables (no refit)
def saved_tables():
    rd = lambda part: pd.read_csv(R23 / part / f"{part}_pooled_metrics.csv")
    B = rd("std"); A_std = {w: E22.aulc(B, w) for w in WINDOWS}; E_std = E23.endpoints(B)
    Ts = {"STD": "rob_std", "RAND8": "rob_rand8", "LOCAL8": "rob_local8", "BLOCK": "block"}
    rob = {}
    for cond, part in Ts.items():
        Bc = rd(part); rob[cond] = {w: E22.aulc(Bc, w) for w in WINDOWS}
    return A_std, E_std, rob


def _check_against_record(det_new):
    rec = json.loads((R23 / "DECISION.json").read_text(encoding="utf-8"))["detail"]; diffs = []
    for cand in ("HA_LEAN", "HA_LR"):
        for k, w in enumerate(WINDOWS):
            a, b = det_new[cand]["noninferiority"][k], rec[cand]["noninferiority"][k]
            diffs += [abs(a["mean"] - b["mean"]), abs(a["lower_95"] - b["lower_95"])]
        a, b = det_new[cand]["spend_BA_0.93"], rec[cand]["spend_BA_0.93"]
        diffs.append(abs(a["restricted_mean_diff(censored=61)"] - b["restricted_mean_diff(censored=61)"]))
        rr = {(r["condition"], r["window"]): r for r in rec[cand]["robust_rows"]}
        for c in det_new[cand]["robust_cells"]:
            diffs.append(abs(c["mean"] - rr[(c["condition"], c["window"])]["mean"]))
    return float(max(diffs)), len(diffs)


def _synthetic(kind, seed=24):
    """Synthetic AULC / endpoint tables for 8 repeats with a controlled candidate - reference difference."""
    rng = np.random.default_rng([seed, abs(hash(kind)) % 1000]); reps = np.arange(1, 9)
    shift = {"pass": 0.004, "fail_ni": -0.020, "nan_ni": 0.004, "spend_incomplete": 0.004, "missing_condition": 0.004, "worse": 0.004, "more_spend": 0.004}[kind]
    def table(sh, n=8):
        base = 0.94 + 0.005 * rng.standard_normal(n); rows = []
        for r, v in zip(reps[:n], base):
            rows += [{"arm": "REF", "repeat": r, "BA": v}, {"arm": "CAND", "repeat": r, "BA": v + sh + 0.002 * rng.standard_normal()}, {"arm": "SIMPLE", "repeat": r, "BA": v - 0.05}]
        return pd.DataFrame(rows)
    nrep = 1 if kind == "nan_ni" else 8
    A = {w: table(shift, nrep) for w in WINDOWS}
    ends = []
    for r in reps:
        for arm, sp in (("REF", 20.0), ("CAND", 28.0 if kind == "more_spend" else 19.0), ("SIMPLE", 30.0)):
            if kind == "spend_incomplete" and arm == "CAND":
                continue
            ends.append({"arm": arm, "repeat": r, "target": "BA >= 0.93", "defined": True, "spend": sp, "censored": False})
    E = pd.DataFrame(ends)
    rob = {c: {w: table(-0.030 if (kind == "worse" and c == "BLOCK") else 0.003) for w in WINDOWS} for c in CONDITIONS}
    if kind == "missing_condition":
        rob.pop("BLOCK")
    return A, E, rob


def decision():
    OUT.mkdir(parents=True, exist_ok=True); res = {"utc": RC.utc(), "frozen_rule": "src/rc23_eval.py::decide (unchanged)", "corrected_rule": "src/rc24_correction.py::decide_corrected"}
    A_std, E_std, rob = saved_tables()
    old_dec, _ = E23.decide(A_std, E_std, rob); new_dec, det = decide_corrected(A_std, E_std, rob)
    mx, nchk = _check_against_record(det)
    res["rc23_recomputed_from_saved_tables"] = {"old_rule": old_dec, "corrected_rule": new_dec, "candidate_status": {k: v["components"] | {"overall": v["status"]} for k, v in det.items()},
                                                "max_abs_diff_vs_DECISION_json": mx, "checked_numbers": nchk, "reproduced": bool(mx < 1e-12)}
    # real-data negative control: the same rule with h-only as the reference; HA_LEAN - HONLY_LR B8-B24 non-inferiority fails (RC23 std)
    old_h, _ = E23.decide(A_std, E_std, rob, R="HONLY_LR"); new_h, det_h = decide_corrected(A_std, E_std, rob, R="HONLY_LR")
    res["negative_control_real_data_reference_HONLY_LR"] = {"old_rule": old_h, "corrected_rule": new_h,
                                                             "HA_LEAN_components": det_h["HA_LEAN"]["components"], "HA_LEAN_status": det_h["HA_LEAN"]["status"],
                                                             "HA_LEAN_minus_HONLY_LR_B8_B24": {k: det_h["HA_LEAN"]["noninferiority"][0][k] for k in ("mean", "lower_95", "verdict", "status")},
                                                             "reaches_D1_old": old_h.startswith("D1"), "reaches_D1_corrected": new_h.startswith("D1")}
    syn = {}
    expect = {"pass": PASS, "fail_ni": FAIL, "nan_ni": INCOMPLETE, "spend_incomplete": INCOMPLETE, "missing_condition": INCOMPLETE, "worse": FAIL, "more_spend": FAIL}
    for kind, want in expect.items():
        A, E, R = _synthetic(kind)
        try:
            od, _ = E23.decide(A, E, R, R="REF", S="SIMPLE", L="CAND"); od_s = od
        except Exception as ex:
            od_s = f"ERROR {type(ex).__name__}"
        nd, dd = decide_corrected(A, E, R, R="REF", S="SIMPLE", L="CAND")
        syn[kind] = {"expected_candidate_status": want, "corrected_candidate_status": dd["CAND"]["status"], "corrected_components": dd["CAND"]["components"],
                     "corrected_decision": nd, "old_decision": od_s, "old_reaches_D1": od_s.startswith("D1"), "corrected_reaches_D1": nd.startswith("D1"),
                     "status_as_expected": dd["CAND"]["status"] == want}
    res["negative_controls_synthetic"] = syn
    ok = (res["rc23_recomputed_from_saved_tables"]["reproduced"] and new_dec.startswith("D1")
          and not res["negative_control_real_data_reference_HONLY_LR"]["reaches_D1_corrected"]
          and all(v["status_as_expected"] for v in syn.values())
          and all(not v["corrected_reaches_D1"] for k, v in syn.items() if k != "pass") and syn["pass"]["corrected_reaches_D1"])
    res["old_rule_defect_demonstrated"] = {k: v["old_reaches_D1"] for k, v in syn.items() if k != "pass"} | {"real_data_HONLY_LR": res["negative_control_real_data_reference_HONLY_LR"]["reaches_D1_old"]}
    res["status"] = PASS if ok else FAIL
    (OUT / "RC24_DECISION_CORRECTION.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("rc23_recomputed_from_saved_tables", "old_rule_defect_demonstrated", "status")}, indent=1, default=str))
    return res


# ======================================================================================== direct witness (one paid state)
def _run_alone(fn):
    try:
        o = fn(); v = np.asarray(o, float)
        return {"outcome": "finite" if np.all(np.isfinite(v)) else "non-finite", "n": int(v.size), "n_nonfinite": int((~np.isfinite(v)).sum()), "_v": v}
    except Exception as ex:
        return {"outcome": "exception", "type": type(ex).__name__, "message": str(ex)[:300], "where": traceback.extract_tb(ex.__traceback__)[-1].name}


def witness():
    import src.rc19_pool as P
    import src.rc19b_keyhole as K
    import src.rc22_common as C22
    import src.rc23_common as C23
    RC.limit_threads(1); OUT.mkdir(parents=True, exist_ok=True)
    M = P.manifest(); C22.set_manifest(M); t = {(x["repeat"], x["fold"]): x for x in P.tasks([35])}[(35, 1)]; pos = {s: i for i, s in enumerate(t["ids"])}
    gi = RC.read_json_gz(R22 / "g-ingr" / "units" / "r35_f1__H_MARGIN.json.gz"); paid = [pos[s] for s in gi["paid_ids"][:24]]; Z = P.zstd(t)
    rows = np.r_[t["test"], np.setdiff1d(t["pool"], K._rev_with(t, M, paid).paid)]
    res = {"utc": RC.utc(), "state": "repeat 35 fold 1, the recorded RC22 g-ingr H_MARGIN paid prefix at budget 24 (as RC23 validation)", "cases": {}}
    base = {}
    cases = {"control_none_absent": (), "T_absent": (C22.ATS_T,), "S_absent": (C22.ATS_S,), "TS_absent": (C22.ATS_T, C22.ATS_S)}
    for case, cols in cases.items():
        rec = {}
        for cons in C23.CONS:
            rv = K._rev_with(t, M, paid)
            for i in rv.paid:
                for k in cols:
                    rv._Y[i, k] = np.nan
            r = _run_alone(lambda: C23.state(t, rv, Z, rows, which=(cons,))[0][cons])
            if case == "control_none_absent" and r["outcome"] == "finite":
                base[cons] = r["_v"]
            if r.get("_v") is not None and cons in base and r["outcome"] == "finite":
                r["max_abs_change_vs_control"] = float(np.max(np.abs(r["_v"] - base[cons])))
            r.pop("_v", None); rec[cons] = r
        res["cases"][case] = rec
    absent = [c for c in cases if c != "control_none_absent"]
    w1 = all(res["cases"][c]["PHR_NRMAP"]["outcome"] in ("exception", "non-finite") for c in absent)
    w1_control = res["cases"]["control_none_absent"]["PHR_NRMAP"]["outcome"] == "finite"
    w2 = all(res["cases"][c][k]["outcome"] == "finite" and res["cases"][c][k].get("max_abs_change_vs_control") == 0.0 for c in absent for k in ("HA_LEAN", "HONLY_LR"))
    res["acceptance"] = {
        "W1_PHR_NRMAP_fails_visibly_when_a_channel_is_wholly_absent": PASS if w1 else FAIL,
        "W1_control_PHR_NRMAP_finite_with_all_channels": PASS if w1_control else FAIL,
        "W2_HA_LEAN_and_HONLY_LR_unchanged_bitwise": PASS if w2 else FAIL,
        "HA_LR_recorded_separately": {c: res["cases"][c]["HA_LR"]["outcome"] for c in absent}}
    res["status"] = PASS if (w1 and w1_control and w2) else FAIL
    (OUT / "RC24_PHR_NRMAP_WITNESS.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str)[:4000])
    return res


if __name__ == "__main__":
    {"decision": decision, "witness": witness}[sys.argv[1]]()
