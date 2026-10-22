"""RC24 post-audit FINAL evaluation and decision (frozen with post_audit/PROTOCOL_RC24P_FINAL.md before any final outcome).
Metrics are computed with src.rc24p_audit (confusion counts from the stored predictions; pooled = the learners of one repeat /
startup concatenated; individual = one learner; BA undefined -> NaN for a one-class test set). Margins are the RC23 / RC24 practical
margins, not loosened: BA 0.010, log loss 0.010, spend 2 simulations.
Statuses (explicit): PASS / FAIL / NOT_SHOWN / INCOMPLETE. "NOT_SHOWN" means neither non-inferiority nor a loss was established.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import t as tdist

import src.rc24p_audit as AU

REF, CAND, HON, GEN = "F_HA_LEAN", "F_HA_TREND", "F_HONLY", "F_TR_GEN15"
D_BA, D_LL, D_SPEND = 0.010, 0.010, 2.0


def to_E(units):
    out = {}
    for u in units:
        k = list(u["evals"][0]["p"].keys())[0]; bs = np.array([e["budget"] for e in u["evals"]], int)
        out[(u["arm"], u["repeat"], u["fold"])] = (bs, np.array([np.asarray(e["p"][k], float) for e in u["evals"]]), np.asarray(u["test_ids"], str))
    return out


def match_E(units, cons):
    out = {}
    for u in units:
        bs = np.array([e["budget"] for e in u["evals"]], int)
        for c in cons:
            out[(f"{c}@HA_LEAN_path", u["repeat"], u["fold"])] = (bs, np.array([np.asarray(e["p"][c], float) for e in u["evals"]]), np.asarray(u["test_ids"], str))
    return out


def tables(E, y):
    D = AU.rows_from(E, y); G = AU.pooled(D)
    # pooled log loss: recompute from predictions (mean over all pooled test rows)
    L = {}
    for (arm, rep, f), (bs, Pm, ids) in E.items():
        yy = y.reindex(ids).to_numpy(int)
        for j, b in enumerate(bs):
            p = np.clip(Pm[j], 1e-6, 1 - 1e-6); s = L.setdefault((arm, rep, int(b)), [0.0, 0]); s[0] += float(-(yy * np.log(p) + (1 - yy) * np.log(1 - p)).sum()); s[1] += len(yy)
    G = G.merge(pd.DataFrame([{"arm": a, "repeat": r, "budget": b, "ll": v[0] / v[1]} for (a, r, b), v in L.items()]), on=["arm", "repeat", "budget"], how="left")
    Ap = AU.aulc(G, ("arm", "repeat"), cols=("BA", "sens", "spec", "ll")); Ai = AU.aulc(D, ("arm", "repeat", "fold"), cols=("BA", "sens", "spec", "ll"))
    return D, G, Ap, Ai


def _paired(A, a, b, col, by="repeat", window="B8_B60"):
    T = A[A.window == window]; x = T[T.arm == a].set_index(by)[col]; y = T[T.arm == b].set_index(by)[col]; d = (x - y).dropna(); n = len(d)
    if n < 2:
        return {"n": n, "mean": np.nan, "lcb": np.nan, "ucb": np.nan}
    m = float(d.mean()); se = float(d.std(ddof=1) / math.sqrt(n)); q = tdist.ppf(0.95, n - 1)
    return {"n": n, "mean": m, "lcb": m - q * se, "ucb": m + q * se, "pos": int((d > 0).sum())}


def ni_ba(Ap, a, b, window, n_exp=8):
    r = _paired(Ap, a, b, "BA", window=window); st = "INCOMPLETE" if r["n"] != n_exp else ("PASS" if r["lcb"] >= -D_BA else "FAIL"); return {**r, "status": st, "window": window}


def ni_ll(Ap, a, b, n_exp=8):
    r = _paired(Ap, a, b, "ll", window="B8_B60"); st = "INCOMPLETE" if r["n"] != n_exp else ("PASS" if r["ucb"] <= D_LL else "FAIL"); return {**r, "status": st}


def spend_ni(Ep, a, b, lev, n_exp=8):
    e = Ep[(Ep.target == lev) & (Ep.defined == True)]  # noqa: E712
    x = e[e.arm == a].set_index("repeat"); y = e[e.arm == b].set_index("repeat"); j = x.join(y, lsuffix="_a", rsuffix="_b", how="inner")
    if len(j) != n_exp:
        return {"target": lev, "status": "INCOMPLETE"}
    aa, ab = j.attained_a.astype(bool), j.attained_b.astype(bool); both = aa & ab; d = (j.spend_a.astype(float) - j.spend_b.astype(float))[both]; n = int(both.sum())
    ub = float(d.mean() + tdist.ppf(0.95, n - 1) * d.std(ddof=1) / math.sqrt(n)) if n > 1 else np.nan
    lb = float(d.mean() - tdist.ppf(0.95, n - 1) * d.std(ddof=1) / math.sqrt(n)) if n > 1 else np.nan
    if aa.sum() >= ab.sum() and n >= 6 and np.isfinite(ub) and ub <= D_SPEND:
        st = "PASS"
    elif aa.sum() <= ab.sum() - 2 or (n >= 2 and np.isfinite(lb) and lb > 0 and d.mean() >= D_SPEND):
        st = "FAIL"
    else:
        st = "NOT_SHOWN"
    return {"target": lev, "attained_a": int(aa.sum()), "attained_b": int(ab.sum()), "both": n, "diff_mean_both": float(d.mean()) if n else np.nan, "ucb_both": ub, "status": st}


def region_mean(Ai, window="B8_B60"):
    """Per startup: mean of the per-block BA-AULC over the blocks where BA is defined (two-class test blocks)."""
    T = Ai[Ai.window == window].dropna(subset=["BA"]); return T.groupby(["arm", "repeat"]).BA.mean().reset_index().assign(window=window)


def extrapolation(Ap, Ai, a, b):
    sup = _paired(Ap, a, b, "BA"); R = region_mean(Ai); reg = _paired(R, a, b, "BA")
    return {"pooled": {**sup, "status": "PASS" if (sup["n"] == 8 and sup["lcb"] > 0) else "FAIL"},
            "per_region": {**reg, "status": "PASS" if (reg["n"] == 8 and reg["lcb"] >= -D_BA) else "FAIL"}}


def decide(std, blk_a, blk_b):
    """std / blk_*: dicts with Ap, Ai, Ep (pooled endpoints) of each condition. Returns the frozen decision and every component."""
    Ap, Ep = std["Ap"], std["Ep"]
    comp = {"STD_BA_B8_B24": ni_ba(Ap, CAND, REF, "B8_B24"), "STD_BA_B8_B60": ni_ba(Ap, CAND, REF, "B8_B60"), "STD_LL": ni_ll(Ap, CAND, REF),
            "STD_spend_0.93": spend_ni(Ep, CAND, REF, 0.93), "STD_spend_0.95": spend_ni(Ep, CAND, REF, 0.95)}
    ext = {"BLOCK_A": extrapolation(blk_a["Ap"], blk_a["Ai"], CAND, REF), "BLOCK_B": extrapolation(blk_b["Ap"], blk_b["Ai"], CAND, REF)}
    early_sup = _paired(Ap, CAND, REF, "BA", window="B8_B24")
    in_dist_ok = all(comp[k]["status"] == "PASS" for k in comp)
    ext_benefit = all(ext[c][k]["status"] == "PASS" for c in ext for k in ("pooled", "per_region"))
    early_benefit = early_sup["n"] == 8 and early_sup["lcb"] > 0
    if any(comp[k]["status"] == "INCOMPLETE" for k in comp):
        choice = "INCOMPLETE"
    elif in_dist_ok and (ext_benefit or early_benefit):
        choice = "HA_TREND + margin"
    else:
        choice = "HA_LEAN + margin"
    # h-only replaces the reference only if it passes every in-distribution component against it
    hcomp = {"STD_BA_B8_B24": ni_ba(Ap, HON, REF, "B8_B24"), "STD_BA_B8_B60": ni_ba(Ap, HON, REF, "B8_B60"), "STD_LL": ni_ll(Ap, HON, REF),
             "STD_spend_0.93": spend_ni(Ep, HON, REF, 0.93), "STD_spend_0.95": spend_ni(Ep, HON, REF, 0.95)}
    if choice == "HA_LEAN + margin" and all(hcomp[k]["status"] == "PASS" for k in hcomp):
        choice = "HONLY + margin"
    # physics specificity of the anchor (HA_TREND vs the generic-trend control)
    phys = {"STD_B8_B24": _paired(Ap, CAND, GEN, "BA", window="B8_B24"), "STD_B8_B60": _paired(Ap, CAND, GEN, "BA"),
            "BLOCK_A_pooled": _paired(blk_a["Ap"], CAND, GEN, "BA"), "BLOCK_B_pooled": _paired(blk_b["Ap"], CAND, GEN, "BA"),
            "BLOCK_A_region": _paired(region_mean(blk_a["Ai"]), CAND, GEN, "BA"), "BLOCK_B_region": _paired(region_mean(blk_b["Ai"]), CAND, GEN, "BA")}
    phys_shown = (phys["STD_B8_B24"]["lcb"] > 0) or (phys["BLOCK_A_pooled"]["lcb"] > 0 and phys["BLOCK_B_pooled"]["lcb"] > 0) or \
                 (phys["BLOCK_A_region"]["lcb"] > 0 and phys["BLOCK_B_region"]["lcb"] > 0)
    return {"choice": choice, "candidate_in_distribution": comp, "candidate_in_distribution_all_pass": in_dist_ok, "candidate_extrapolation": ext,
            "extrapolation_benefit_both_partitions": ext_benefit, "early_superiority": {**early_sup, "shown": early_benefit},
            "honly_vs_ref": hcomp, "physics_specific": {"contrasts": phys, "shown": bool(phys_shown)}}
