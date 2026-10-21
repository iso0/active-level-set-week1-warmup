"""RC24 Stage C evaluation (frozen with PROTOCOL_RC24_STAGE_C.md before any Stage C outcome). Test outcomes are read here only.

Arms (own query): HA_LEAN_MARGIN (reference, RC23 D1), HONLY_MARGIN (strong baseline), HA_TREND_MARGIN; derived arm HT_PHYS = HA_TREND
on the HONLY_MARGIN paths (c-match; its acquisition reads only h, so these ARE its own-query trajectories). Conditions: STD (fresh repeats
67-74) and BLOCK (fresh k-means seeds 9-16). Metrics: src.rc24_eval (fold-pooled BA-AULC B8-B24 / B8-B60, recalls, log loss, AUC,
hard group, attainment 0.80-0.95 with observed and restricted spend) and the corrected explicit-status rules of src.rc24_correction.
Decision for the PRIMARY candidate X (fixed in the protocol) against HA_LEAN_MARGIN:
  std_ni     non-inferiority PASS in both windows (one-sided 95 % t lower bound >= -0.010, n = 8 repeats)
  std_spend  spend to BA >= 0.95 status PASS (not MORE, complete)
  block_gain one-sided 95 % t lower bound of X - HA_LEAN BA-AULC B8-B60 > 0 over the 8 block seeds (fold-pooled over the 5 blocks)
  CONFIRMED iff std_ni and std_spend and block_gain; PARTIAL iff (std_ni and std_spend) xor block_gain; NOT CONFIRMED otherwise;
  INCOMPLETE if any component is incomplete.
Secondary (reported, not decisive): the same rule for the other candidate; X vs HONLY_MARGIN non-inferiority in both conditions and
windows ("dominates both references" only if all PASS); RC22 verdicts (margin 0.020, 7/8) and MATERIAL labels; matched prior
sensitivity (HA_TREND_B1 / B10) and falsifying controls (PAC_GEN, PAC) on the HA_LEAN paths.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import t as tdist

import src.rc22_eval as E22
import src.rc23_eval as E23
import src.rc24_correction as CR
import src.rc24_eval as E

REF = "HA_LEAN_MARGIN"


def own_rows(units, M, T):
    return E22.learner_rows(units, M, T, cons_map=lambda u: [(list(u["evals"][0]["p"].keys())[0], u["arm"])])


def derived_rows(match_units, M, T):
    """HT_PHYS = HA_TREND on the HONLY_MARGIN paths; plus every matched construction on both path types (label 'cons@path')."""
    sel = [u for u in match_units if u["path_of"] == "HONLY_MARGIN"]
    r1 = E22.learner_rows(sel, M, T, cons_map=lambda u: [("HA_TREND", "HT_PHYS")])
    r2 = E22.learner_rows(match_units, M, T, cons_map=lambda u: [(k, f"{k}@{u['path_of']}") for k in u["evals"][0]["p"].keys()])
    return r1, r2


def tables(rows, M):
    return E.tables(rows, M)


def superiority(T, a, b, metric="BA"):
    x = T[T.arm == a].set_index("repeat")[metric]; y = T[T.arm == b].set_index("repeat")[metric]; d = (x - y).dropna(); n = len(d)
    if n < 2:
        return {"contrast": f"{a} − {b}", "n": n, "status": CR.INCOMPLETE}
    m = float(d.mean()); se = float(d.std(ddof=1) / math.sqrt(n)); lcb = m - tdist.ppf(0.95, n - 1) * se
    return {"contrast": f"{a} − {b}", "metric": metric, "n": n, "mean": m, "se": se, "lower_95": lcb, "good": f"{int((d > 0).sum())}/{n}",
            "status": CR.PASS if (n == 8 and np.isfinite(lcb) and lcb > 0) else (CR.INCOMPLETE if n != 8 else CR.FAIL)}


def decide(A_std, E_std, A_blk, X, ref=REF):
    ni = [CR.ni_status(A_std[w], X, ref) for w in ("small", "all")]; sp = CR.spend_status(E_std, X, ref, "BA >= 0.95"); bg = superiority(A_blk["all"], X, ref)
    comp = {"std_ni_B8_B24": ni[0]["status"], "std_ni_B8_B60": ni[1]["status"], "std_spend_BA_0.95": sp["status"], "block_gain_B8_B60": bg["status"]}
    if CR.INCOMPLETE in comp.values():
        lab = "INCOMPLETE"
    else:
        a = comp["std_ni_B8_B24"] == comp["std_ni_B8_B60"] == comp["std_spend_BA_0.95"] == CR.PASS; b = comp["block_gain_B8_B60"] == CR.PASS
        lab = "CONFIRMED (DEV-confirm)" if (a and b) else "PARTIAL (DEV-confirm)" if (a or b) else "NOT CONFIRMED (DEV-confirm)"
    return lab, {"components": comp, "noninferiority": ni, "spend_BA_0.95": sp, "block_gain": bg}


def vs_honly(A_std, A_blk, X):
    out = {}
    for cond, A in (("STD", A_std), ("BLOCK", A_blk)):
        for w in ("small", "all"):
            r = CR.ni_status(A[w], X, "HONLY_MARGIN"); out[f"{cond}_{w}"] = {"mean": r["mean"], "lower_95": r["lower_95"], "status": r["status"]}
    out["dominates_both_references"] = all(v["status"] == CR.PASS for v in out.values() if isinstance(v, dict))
    return out
