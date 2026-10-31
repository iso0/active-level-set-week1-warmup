"""IR evaluation of parts B and C (PROTOCOL_IR.md sections 4-5). EVALUATOR ONLY (test labels and test outputs are read here).
  part B  learnability of every physical output on the recorded C1 paths (R2_test, standardised RMSE, 90 % coverage; budget to R2 0.8)
  part C  depth-model screen: proxy BA through the frozen g* (GSTAR_FROZEN.json), log-depth RMSE (all / q20), NLPD;
          contrasts candidate - R0 per learner-path -> cluster means -> one-sided 95 % t bounds; carry rule S1-S4
    python -m src.ir_eval screen
"""
from __future__ import annotations

import json
import math
import sys

import numpy as np
import pandas as pd
from scipy.stats import t as tdist

import src.el_cross as X
import src.ir_data as IRD
import src.ir_screen as SC
import src.rc18_common as RC
import src.rc19_pool as P

OUT = IRD.OUT / "screen"
EARLY = (8, 12, 16, 20, 24)
LATE = (32, 40, 60)
CANDS = ("LMC_W", "LMC_KE", "LMC_T", "CHAIN_W", "CHAIN_KE", "CHAIN_T")
CONTROLS = ("SUM2", "ICM_W", "ORACLE_CHAIN_W", "ORACLE_CHAIN_KE", "ORACLE_CHAIN_T")
TIE_ORDER = ("CHAIN_W", "CHAIN_KE", "CHAIN_T", "LMC_W", "LMC_KE", "LMC_T")       # registered tie-break (simpler first)
LEARN_TRUE = {"W": None, "KE": "log_ke_T0_nJ", "T": "tmax_T0_K", "SPK": "vmax_spike_logratio", "LAS": "laser_T0_W", "ETOT": "log_etot_T0_J", "NPART": "log_npart_T0"}


def _t1(d, upper=False):
    d = np.asarray(d, float); d = d[np.isfinite(d)]; n = len(d)
    if n < 2:
        return {"mean": float(d.mean()) if n else np.nan, "lcb": np.nan, "ucb": np.nan, "n": n}
    m = float(d.mean()); se = float(d.std(ddof=1) / math.sqrt(n)); q = float(tdist.ppf(0.95, n - 1))
    return {"mean": m, "lcb": m - q * se, "ucb": m + q * se, "n": n}


def rows(M):
    G = json.loads((IRD.OUT / "GSTAR_FROZEN.json").read_text(encoding="utf-8")); gmu, gsd, gc, gi = np.array(G["mu"]), np.array(G["sd"]), np.array(G["coef"]), G["intercept"]
    lx = np.log(M[list(P.INPUTS)].to_numpy(float)); hraw = pd.Series(lx[:, 0] - 0.5 * lx[:, 1] - 1.5 * lx[:, 2], index=M.index)
    Gm = IRD.geometry(); sd_pool = {}
    good_all = ~M.short_record.astype(bool)
    for q, c in LEARN_TRUE.items():
        v = np.log(Gm.W_A_um.reindex(M.index)) if q == "W" else M[c]; sd_pool[q] = float(v[good_all & v.notna()].std())
    sd_pool["D"] = float(M.log_A_um[good_all & M.log_A_um.notna()].std())
    units = sorted((IRD.OUT / "ir-screen" / "units").glob("*.json.gz")); S = {}
    for f in units:
        u = RC.read_json_gz(f); S[f.name] = (None, u["condition"], int(u["cluster"]), int(u["learner"]))
    T = X.tasks_for(S, M); R, L = [], []
    for f in units:
        u = RC.read_json_gz(f); c, cl, l = u["condition"], int(u["cluster"]), int(u["learner"]); task = T[(c, cl, l)]
        ids = list(u["test_ids"]); y = M.y.reindex(ids).to_numpy(int); A = M.log_A_um.reindex(ids).to_numpy(float); short = M.short_record.reindex(ids).to_numpy(bool)
        q20 = np.asarray(task["q20"], bool); good = np.isfinite(A) & ~short; both = (y == 1).any() and (y == 0).any()
        h = hraw.reindex(ids).to_numpy(float)
        truth = {"D": A}
        for q, col in LEARN_TRUE.items():
            truth[q] = np.log(Gm.W_A_um.reindex(ids).to_numpy(float)) if q == "W" else M[col].reindex(ids).to_numpy(float)
        ceil = np.nan
        if both:
            pz = 1 / (1 + np.exp(-(gi + ((np.c_[h, A] - gmu) / gsd) @ gc))); hat = pz >= 0.5; ceil = 0.5 * (hat[y == 1].mean() + (~hat[y == 0]).mean())
        for e in u["evals"]:
            b = int(e["budget"])
            for nm, (m, lat, nv) in e["pred"].items():
                m = np.asarray(m, float); lat = np.asarray(lat, float); nv = np.asarray(nv, float)
                if nm.startswith("LEARN_") or nm == "R0":
                    q = "D" if nm == "R0" else nm[6:]; tv = truth[q]; ok = np.isfinite(tv) & ~short & np.isfinite(m)
                    if ok.sum() >= 3:
                        err = m[ok] - tv[ok]; sst = float(np.sum((tv[ok] - tv[ok].mean()) ** 2)); v = lat[ok] + np.where(np.isfinite(nv[ok]), nv[ok], 0.0)
                        L.append({"output": q, "condition": c, "cluster": cl, "learner": l, "budget": b, "R2": 1 - float(np.sum(err ** 2)) / sst if sst > 0 else np.nan,
                                  "sRMSE": float(np.sqrt(np.mean(err ** 2))) / sd_pool[q], "cov90": float(np.mean(np.abs(err) <= 1.6449 * np.sqrt(v)))})
                if nm.startswith("LEARN_"):
                    continue
                r = {"model": nm, "condition": c, "cluster": cl, "learner": l, "budget": b, "both": both, "ceiling_BA_true_depth": ceil}
                ok = good & np.isfinite(m)
                if ok.sum():
                    err = m[ok] - A[ok]; v = lat[ok] + nv[ok]
                    r["rmse"] = float(np.sqrt(np.mean(err ** 2))); r["nlpd"] = float(np.mean(0.5 * np.log(2 * np.pi * v) + 0.5 * err ** 2 / v))
                    okq = ok & q20
                    r["rmse_q20"] = float(np.sqrt(np.mean((m[okq] - A[okq]) ** 2))) if okq.sum() else np.nan
                if both:
                    mm = np.where(np.isfinite(m), m, np.nan); pz = 1 / (1 + np.exp(-(gi + ((np.c_[h, mm] - gmu) / gsd) @ gc))); hat = pz >= 0.5
                    r["proxyBA"] = 0.5 * (hat[y == 1].mean() + (~hat[y == 0]).mean())
                R.append(r)
    return pd.DataFrame(R), pd.DataFrame(L)


def contrasts(R, conds, budgets, model, ref="R0", metric="proxyBA", rel=False):
    T = R[R.condition.isin(conds) & R.budget.isin(budgets)]
    a = T[T.model == model].set_index(["condition", "cluster", "learner", "budget"])[metric]; b = T[T.model == ref].set_index(["condition", "cluster", "learner", "budget"])[metric]
    d = ((a - b) / b) if rel else (a - b); d = d.dropna()
    per_lp = d.groupby(level=[0, 1, 2]).mean(); per_cl = per_lp.groupby(level=[0, 1]).mean()
    return _t1(per_cl.values), int(len(per_lp))


def screen():
    RC.limit_threads(1); OUT.mkdir(parents=True, exist_ok=True); M = P.manifest(); R, L = rows(M)
    R.to_csv(OUT / "screen_rows.csv.gz", index=False); L.to_csv(OUT / "learnability_rows.csv.gz", index=False)
    res = {"evidence": "DEV (recorded C1-selected paths, identical paid prefixes; evaluator-only metrics)", "units": int(R.groupby(["condition", "cluster", "learner"]).ngroups)}
    models = sorted(R.model.unique()); res["models"] = models
    res["missing_states"] = {m: int(len(R[R.model == "R0"]) - len(R[R.model == m])) for m in models}
    lev = {}
    for cset, cs in (("STD", ("STD",)), ("GEOMETRIC", ("K5", "K4"))):
        for wn, bs in (("early", EARLY), ("late", LATE), ("all", tuple(SC.BUDGETS))):
            T = R[R.condition.isin(cs) & R.budget.isin(bs)]
            lev[f"{cset}|{wn}"] = {m: {k: float(T[T.model == m].groupby(["condition", "cluster"])[k].mean().mean()) for k in ("proxyBA", "rmse", "rmse_q20", "nlpd", "ceiling_BA_true_depth")} for m in models}
    res["levels"] = lev
    rule, table = {}, []
    for m in [x for x in models if x != "R0"]:
        s1, n1 = contrasts(R, ("STD",), EARLY, m); s2, n2 = contrasts(R, ("STD",), EARLY, m, metric="rmse_q20", rel=True)
        s3, n3 = contrasts(R, ("STD",), LATE, m); s4, n4 = contrasts(R, ("K5", "K4"), tuple(SC.BUDGETS), m)
        ex = {"STD_early_rmse_rel": contrasts(R, ("STD",), EARLY, m, metric="rmse", rel=True)[0], "STD_early_nlpd": contrasts(R, ("STD",), EARLY, m, metric="nlpd")[0],
              "STD_late_rmse_q20_rel": contrasts(R, ("STD",), LATE, m, metric="rmse_q20", rel=True)[0], "GEO_rmse_q20_rel": contrasts(R, ("K5", "K4"), tuple(SC.BUDGETS), m, metric="rmse_q20", rel=True)[0]}
        ok = {"S1": bool(s1["mean"] >= 0.005 and s1["lcb"] > 0), "S2": bool(s2["mean"] <= -0.03 and s2["ucb"] < 0), "S3": bool(s3["lcb"] >= -0.003), "S4": bool(s4["lcb"] >= -0.005)}
        rule[m] = {"S1_STD_early_proxyBA": s1, "S2_STD_early_rmse_q20_rel": s2, "S3_STD_late_proxyBA": s3, "S4_GEO_all_proxyBA": s4, "pass": ok,
                   "candidate": m in CANDS, "all_pass": bool(all(ok.values())), "learner_paths": {"S1": n1, "S2": n2, "S3": n3, "S4": n4}, "extra": ex}
        table.append({"model": m, "candidate": m in CANDS, **{f"{k}_{q}": v[q] for k, v in (("S1", s1), ("S2", s2), ("S3", s3), ("S4", s4)) for q in ("mean", "lcb", "ucb")},
                      **{f"pass_{k}": v for k, v in ok.items()}})
    res["rule"] = rule
    passing = [m for m in CANDS if rule.get(m, {}).get("all_pass")]
    if passing:
        best = max(passing, key=lambda m: (round(rule[m]["S1_STD_early_proxyBA"]["mean"], 12), -TIE_ORDER.index(m)))
        res["decision"] = {"carried": best, "passing": passing, "next": "part D (downstream DEV test), registered rule D1-D4"}
    else:
        res["decision"] = {"carried": None, "passing": [], "next": "close the method part: NOT SHOWN on DEV; parts D and E are not run"}
    # part B summary
    B = []
    for q, g in L[L.condition == "STD"].groupby("output"):
        for b, gb in g.groupby("budget"):
            B.append({"output": q, "budget": int(b), "R2_median": float(gb.R2.median()), "R2_mean": float(gb.R2.mean()), "sRMSE_median": float(gb.sRMSE.median()),
                      "cov90_mean": float(gb.cov90.mean()), "learner_paths": int(len(gb))})
    Bt = pd.DataFrame(B); Bt.to_csv(OUT / "partB_learnability_STD.csv", index=False, lineterminator="\n")
    first = []
    for (q, c, cl, l), g in L[L.condition == "STD"].groupby(["output", "condition", "cluster", "learner"]):
        g = g.sort_values("budget"); hit = g[g.R2 >= 0.8]; first.append({"output": q, "first_b_R2_0.8": int(hit.budget.iloc[0]) if len(hit) else np.nan})
    Fh = pd.DataFrame(first); res["partB_budget_to_R2_0.8"] = {q: {"median": float(g["first_b_R2_0.8"].median()) if g["first_b_R2_0.8"].notna().any() else None,
                                                                    "never_by_60": int(g["first_b_R2_0.8"].isna().sum()), "learner_paths": int(len(g))} for q, g in Fh.groupby("output")}
    pd.DataFrame(table).to_csv(OUT / "screen_rule_table.csv", index=False, lineterminator="\n")
    (OUT / "SCREEN_RESULT.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(json.dumps({"decision": res["decision"], "missing": res["missing_states"]}, indent=1, default=float))
    print(pd.DataFrame(table)[["model", "candidate", "S1_mean", "S1_lcb", "S2_mean", "S2_ucb", "S3_lcb", "S4_lcb", "pass_S1", "pass_S2", "pass_S3", "pass_S4"]].round(4).to_string(index=False))
    return res


if __name__ == "__main__":
    {"screen": screen}[sys.argv[1]]()
