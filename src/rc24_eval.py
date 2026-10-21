"""RC24 Stage A evaluation (frozen with PROTOCOL_RC24_STAGE_A.md before any Stage A outcome). Test outcomes are read here only.

Built on the frozen RC22 / RC23 metric functions (src.rc22_eval: learner rows, fold-pooled and individual-learner metrics, AULC,
verdict contrasts; src.rc23_eval: BA target endpoints, paired spend) and the corrected explicit-status rules of
src.rc24_correction (non-inferiority PASS / FAIL / INCOMPLETE). Adds (evaluator-only memberships, never used by a learner):
  hard group   the 10 NEW short-Keyhole originals (shortK_NEW_original) and the 12 NEW conduction runs;
               hard-group BA = (recall on the 10 + specificity on the 12) / 2; pooled short-K recall (22 runs, shortK_pooled)
  AUC          threshold-free discrimination of the fold-pooled predictions
  oracle-threshold BA (calibration diagnostic, NOT deployable): the best BA reachable by moving only the threshold
Primary metrics: BA-AULC B8-B24 and B8-B60 (fold-pooled repeat curves), both recalls, attainment / purchases to BA 0.80 / 0.90 /
0.93 / 0.95 (first, b and b + 4 confirmation, sustained share, censoring; observed both-attained difference and restricted score
with censored = 61 kept apart). Decisions Q1-Q3 (section 5 of the protocol) and the Q4 decomposition on the matched matrix.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

import src.rc19_eval as EV
import src.rc22_eval as E22
import src.rc23_eval as E23
import src.rc24_correction as CR

REF = "HA_LEAN_MARGIN"
COMPARATORS = ("HONLY_MARGIN", "M3_MARGIN", "E1S", "G3_MARGIN", "HA_LEAN_STRADDLE")
OWN_KEYS = {"HA_LEAN_MARGIN": [("HA_LEAN", "HA_LEAN_MARGIN")], "HONLY_MARGIN": [("HONLY_LR", "HONLY_MARGIN")], "M3_MARGIN": [("M3", "M3_MARGIN")],
            "E1S": [("E1CAL", "E1S"), ("E1RAW", "E1S_RAW")], "G3_MARGIN": [("G3", "G3_MARGIN")], "HA_LEAN_STRADDLE": [("HA_LEAN", "HA_LEAN_STRADDLE")]}
MODEL_OF = {"HA_LEAN_MARGIN": "HA_LEAN", "HONLY_MARGIN": "HONLY_LR", "M3_MARGIN": "M3", "E1S": "E1CAL", "G3_MARGIN": "G3", "HA_LEAN_STRADDLE": "HA_LEAN"}
MB = tuple(range(8, 61, 4))
WIN_MB = {"small": tuple(b for b in MB if b <= 24), "all": MB}


# ======================================================================================== rows and metrics
def own_rows(units, M, T):
    return E22.learner_rows(units, M, T, cons_map=lambda u: OWN_KEYS[u["arm"]])


def match_rows(units, M, T, models=("HA_LEAN", "HONLY_LR", "M3", "M3_C1", "E1RAW", "E1CAL", "G3")):
    return E22.learner_rows(units, M, T, cons_map=lambda u: [(m, f"{m}@{u['path_of']}") for m in models])


def hard_flags(M, ids):
    m = M.reindex(ids); new = (m.source_batch == "NEW").to_numpy(); y = m.y.to_numpy(int)
    return {"shortK_new": m.shortK_NEW_original.to_numpy(bool), "cond_new": new & (y == 0), "shortK_pooled": m.shortK_pooled.to_numpy(bool)}


def extra_pooled(rows, M):
    """Per (arm, repeat, budget) on the fold-pooled predictions: AUC, oracle-threshold BA, hard-group recalls / BA."""
    acc = {}
    for r in rows:
        acc.setdefault((r["arm"], r["repeat"], r["budget"]), []).append(r)
    out = []
    for (arm, rep, b), rs in acc.items():
        p = np.concatenate([x["p"] for x in rs]); y = np.concatenate([x["y"] for x in rs]); ids = sum([list(x["ids"]) for x in rs], [])
        f = hard_flags(M, ids); hat = p >= 0.5; ok = np.isfinite(p).all() and len(rs) == 5
        rec = lambda m: float(np.mean(hat[m])) if m.any() else np.nan
        spec = lambda m: float(np.mean(~hat[m])) if m.any() else np.nan
        row = {"arm": arm, "repeat": rep, "budget": b, "AUC": float(roc_auc_score(y, p)) if ok and len(set(y)) == 2 else np.nan,
               "BA_oracle_threshold": _oracle_ba(p, y) if ok else np.nan, "recall_shortK_NEW": rec(f["shortK_new"]), "spec_cond_NEW": spec(f["cond_new"]),
               "recall_shortK_pooled": rec(f["shortK_pooled"]), "n_shortK_NEW": int(f["shortK_new"].sum()), "n_cond_NEW": int(f["cond_new"].sum())}
        row["BA_hard_group"] = 0.5 * (row["recall_shortK_NEW"] + row["spec_cond_NEW"]); out.append(row)
    return pd.DataFrame(out).sort_values(["arm", "repeat", "budget"]).reset_index(drop=True)


def _oracle_ba(p, y):
    o = np.argsort(-p, kind="stable"); ys = y[o]; tp = np.cumsum(ys); fp = np.cumsum(1 - ys); n1, n0 = ys.sum(), (1 - ys).sum()
    ba = 0.5 * (tp / n1 + (n0 - fp) / n0); return float(max(ba.max(), 0.5))


def tables(rows, M):
    B = E22.pooled_metrics(rows); X = extra_pooled(rows, M); B = B.merge(X, on=["arm", "repeat", "budget"], how="left"); LB = E22.learner_metrics(rows)
    cols = ("BA", "log_loss", "brier", "sensitivity", "specificity", "q20_BA", "spec_NEW", "AUC", "BA_oracle_threshold", "BA_hard_group")
    A = {w: E22.aulc(B, w, cols=cols) for w in ("small", "all")}; AL = {w: E22.aulc(LB, w, by=("arm", "repeat", "fold")) for w in ("small", "all")}
    return B, LB, A, AL


# ======================================================================================== contrasts and decisions
def contrasts(A, E, a, b=REF):
    out = []
    for w in ("small", "all"):
        for met, mg, d in (("BA", 0.020, "higher"), ("log_loss", 0.010, "lower"), ("sensitivity", 0.020, "higher"), ("specificity", 0.020, "higher")):
            out.append({"window": w, **E22.contrast(A[w], a, b, met, mg, d)})
        ni = CR.ni_status(A[w], a, b); out.append({"window": w, "contrast": f"{a} − {b}", "metric": "BA non-inferiority", "mean": ni["mean"], "lower_95": ni["lower_95"], "good": ni["good"], "verdict": ni["status"]})
    for t in ("BA >= 0.80", "BA >= 0.90", "BA >= 0.93", "BA >= 0.95"):
        s = CR.spend_status(E, a, b, t); out.append({"window": "endpoint", "contrast": s["contrast"], "metric": t, "mean": s.get("restricted_mean_diff(censored=61)"),
                                                     "observed_both_attained": s.get("observed_mean_diff_both_attained"), "attained": f"{s.get('attained_a')}/{s.get('attained_b')}",
                                                     "verdict": s["verdict"], "status": s["status"]})
    return out


def _v(rows, w, met):
    return [r for r in rows if r["window"] == w and r["metric"] == met][0]


def decide_q1(A, E):
    c = contrasts(A, E, "HONLY_MARGIN"); ni = [_v(c, w, "BA non-inferiority")["verdict"] for w in ("small", "all")]; sp = _v(c, "endpoint", "BA >= 0.95")
    att = lambda arm: int(((E.target == "BA >= 0.95") & (E.arm == arm) & ~E.censored).sum())
    if INCOMPLETE_ in ni or sp["status"] == CR.INCOMPLETE:
        lab = "INCOMPLETE"
    elif all(x == CR.PASS for x in ni) and sp["status"] == CR.PASS and att("HONLY_MARGIN") >= att(REF) - 1:
        lab = "H-ONLY SUFFICIENT (DEV)"
    else:
        lab = "H-ONLY NOT SUFFICIENT (DEV)"
    return lab, {"noninferiority": ni, "spend_BA_0.95": sp, "attained_0.95": {"HONLY_MARGIN": att("HONLY_MARGIN"), REF: att(REF)}}


INCOMPLETE_ = CR.INCOMPLETE


def decide_vs_ref(A, E, arm):
    c = contrasts(A, E, arm); ba = [_v(c, w, "BA")["verdict"] for w in ("small", "all")]; ni = [_v(c, w, "BA non-inferiority")["verdict"] for w in ("small", "all")]
    if INCOMPLETE_ in ni or "INCOMPLETE" in ba:
        lab = "INCOMPLETE"
    elif any(v.startswith("BETTER") for v in ba) and not any(v.startswith("WORSE") for v in ba):
        lab = "BETTER (DEV)"
    elif any(v.startswith("WORSE") for v in ba):
        lab = "WORSE (DEV)"
    elif all(x == CR.PASS for x in ni):
        lab = "SIMILAR (non-inferior, DEV)"
    else:
        lab = "NON-INFERIORITY NOT SHOWN (DEV)"
    return lab, {"BA_verdicts": ba, "noninferiority": ni}


def straddle_audit(units):
    rows = []
    for u in units:
        for e in u["evals"]:
            a = e.get("audit")
            if a:
                rows.append({"repeat": u["repeat"], "fold": u["fold"], "budget": e["budget"], **a})
    D = pd.DataFrame(rows)
    if not len(D):
        return {"steps": 0}
    tiny = (D.top2_gap.abs() <= 1e-9 * D.score_range.abs().clip(lower=1e-300)).mean()
    return {"steps": int(len(D)), "share_choice_differs_from_margin": float(1 - D.same_as_margin.mean()), "share_numerically_indistinguishable_top2": float(tiny),
            "median_s_at_choice": float(D.s_at_choice.median()), "median_abs_eta_at_choice": float(D.abs_eta_at_choice.median()), "median_s_over_candidates": float(D.s_median.median()),
            "median_share_rows_with_excess_depth_variance": float(D.excess_depth_share.median())}


# ======================================================================================== Q4 decomposition on the matched matrix
def decomposition(Bm, arm, window):
    """Bm: fold-pooled metrics of the matched units (arm label 'model@path'); 2 x 2 cells of model {X, HA_LEAN} x path {P_X, P_L}."""
    A = E22.aulc(Bm, WIN_MB[window], cols=("BA", "AUC", "BA_oracle_threshold", "log_loss"))
    X = MODEL_OF[arm]; L = "HA_LEAN"; cell = lambda m, q, met="BA": A[A.arm == f"{m}@{q}"].set_index("repeat")[met]
    XX, LX, XL, LL = cell(X, arm), cell(L, arm), cell(X, REF), cell(L, REF)
    tot = (XX - LL); m1 = (XX - LX); p1 = (LX - LL); m2 = (XL - LL); p2 = (XX - XL); inter = tot - m2 - (LX - LL)
    f = lambda s: {"mean": float(s.mean()), "se": float(s.std(ddof=1) / math.sqrt(len(s))) if len(s) > 1 else np.nan, "good": f"{int((s > 0).sum())}/{len(s)}"}
    cal = {}
    for (m, q) in ((X, arm), (L, arm), (X, REF), (L, REF)):
        ba, auc, orc = cell(m, q), cell(m, q, "AUC"), cell(m, q, "BA_oracle_threshold")
        cal[f"{m}@{q}"] = {"BA": float(ba.mean()), "AUC": float(auc.mean()), "oracle_threshold_BA": float(orc.mean()), "threshold_gap": float((orc - ba).mean())}
    return {"window": window, "total_own_query": f(tot), "order1_model_on_X_path": f(m1), "order1_path_for_HA_LEAN": f(p1), "order2_model_on_HA_LEAN_path": f(m2),
            "order2_path_for_X": f(p2), "interaction": f(inter), "calibration_cells": cal}
