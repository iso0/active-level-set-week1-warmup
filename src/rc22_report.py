"""RC22 reports (presentation layer; every metric, verdict and decision rule comes from the frozen src/rc22_eval.py).
    python -m src.rc22_report ingr | miss | start | block | acq | smoke
Outputs under outputs/research_campaign_20261021/opus_rc22/<part>/ (markdown + CSV) and float32 exports of every per-budget test
prediction and every paid path of the sequential jobs (<part>/export/), with an acceptance check against the metric tables.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc19_pool as P
import src.rc22_eval as E
from src.rc19_report import md

OUT = E.OUT
INGR = ("SHQ_ATS_H", "PHR_NRMAP", "HA_LR", "HONLY_LR", "SHQ_ATS_H_RECAL")


def _load(job):
    return EV.load_units(OUT / job)


def _write(part, name, L):
    d = OUT / part; d.mkdir(parents=True, exist_ok=True); (d / name).write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L)[:12000])


def _seq_map(u):
    if u.get("arm") == "E1S":
        return [("E1RAW", "E1RAW+straddle"), ("E1CAL", "E1CAL+straddle")]
    return [(list(u["evals"][0]["p"].keys())[0], u["arm"])]


def _summ(T, cols=("BA", "log_loss", "sensitivity", "specificity", "brier")):
    cols = [c for c in cols if c in T]
    S = T.groupby("arm")[cols].agg(["mean", lambda x: x.std(ddof=1) / np.sqrt(len(x))]); S.columns = [f"{a}_{'se' if b == '<lambda_0>' else b}" for a, b in S.columns]
    return S.reset_index()


def export(part, units, rows, B):
    """float32 predictions per learner and budget + paid paths; acceptance: recomputed pooled metrics equal the table."""
    d = OUT / part / "export"; d.mkdir(parents=True, exist_ok=True); keys, arrs, tids, buds, paths = [], [], [], [], []
    acc = {}
    for r in rows:
        acc.setdefault((r["arm"], r["repeat"], r["fold"]), {})[r["budget"]] = r
    for (arm, rep, f), bd in acc.items():
        bs = sorted(bd); keys.append(f"{arm}|r{rep}|f{f}"); arrs.append(np.asarray([bd[b]["p"] for b in bs], np.float32)); tids.append(np.asarray(bd[bs[0]]["ids"])); buds.append(np.asarray(bs, np.int16))
    for u in units:
        hows = [e.get("how") for e in u["evals"]]
        for q, s in enumerate(u["paid_ids"], 1):
            paths.append({"arm": u["arm"], "startup": u.get("startup", "STD"), "block": u.get("block"), "repeat": u["repeat"], "fold": u["fold"], "query": q, "sim_id": s,
                          "rule": "startup" if q <= P.B0 else (hows[q - P.B0 - 1] or "arm selector") if q - P.B0 - 1 < len(hows) else "arm selector"})
    np.savez_compressed(d / "predictions_f32.npz", keys=np.asarray(keys), **{f"pred_{i}": v for i, v in enumerate(arrs)}, **{f"test_ids_{i}": t for i, t in enumerate(tids)},
                        **{f"budgets_{i}": t for i, t in enumerate(buds)}, schema=np.asarray([json.dumps({"pred": "pred[budget, test] = P(Keyhole), float32; key arm|repeat|fold"})]))
    pd.DataFrame(paths).to_csv(d / "paths.csv.gz", index=False, compression="gzip")
    Z = np.load(d / "predictions_f32.npz", allow_pickle=False); R2 = []; byk = {(r["arm"], r["repeat"], r["fold"], r["budget"]): r for r in rows}
    for i, k in enumerate(Z["keys"]):
        arm, rep, f = k.split("|")
        for j, b in enumerate(Z[f"budgets_{i}"]):
            r = dict(byk[(arm, int(rep[1:]), int(f[1:]), int(b))]); r["p"] = Z[f"pred_{i}"][j].astype(float); R2.append(r)
    B2 = E.pooled_metrics(R2); j = B2.merge(B, on=["arm", "repeat", "budget"], suffixes=("_x", "_t")); res = {"cells": int(len(j)), "cells_table": int(len(B))}
    for c in ("BA", "log_loss", "sensitivity", "specificity", "brier"):
        dd = np.abs(j[f"{c}_x"].to_numpy(float) - j[f"{c}_t"].to_numpy(float)); dd = dd[np.isfinite(dd)]; res[c] = float(dd.max()) if len(dd) else 0.0
    res["PASS"] = bool(res["cells"] == res["cells_table"] and all(res[c] <= 1e-12 for c in ("BA", "log_loss", "sensitivity", "specificity", "brier")))
    (d / "EXPORT_ACCEPTANCE.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); return res


# ======================================================================================== part 2 + audit
def ingr():
    M = P.manifest(); U = _load("g-ingr"); T = {(t["repeat"], t["fold"]): t for t in P.tasks(sorted({u["repeat"] for u in U}))}
    rows = E.learner_rows(U, M, T, cons_map=lambda u: [(c, f"{c}@{u['path_of']}") for c in INGR]); B = E.pooled_metrics(rows); LB = E.learner_metrics(rows)
    B["cons"] = B.arm.str.split("@").str[0]; B["path"] = B.arm.str.split("@").str[1]
    small, allb = (8, 12, 16, 20, 24), (8, 12, 16, 20, 24, 32, 40, 60)
    A = {w: B[B.budget.isin(bs)].groupby(["cons", "path", "repeat"])[["BA", "log_loss", "sensitivity", "specificity", "brier"]].mean().reset_index()
         .groupby(["cons", "repeat"]).mean(numeric_only=True).reset_index().rename(columns={"cons": "arm"}) for w, bs in (("small", small), ("all", allb))}
    R = OUT / "ingr"; R.mkdir(parents=True, exist_ok=True); B.drop(columns=[]).to_csv(R / "ingr_pooled_metrics.csv", index=False, lineterminator="\n")
    pairs = [("HONLY_LR", "PHR_NRMAP"), ("HA_LR", "PHR_NRMAP"), ("HA_LR", "HONLY_LR"), ("PHR_NRMAP", "HA_LR"), ("PHR_NRMAP", "SHQ_ATS_H"), ("SHQ_ATS_H_RECAL", "SHQ_ATS_H"),
             ("PHR_NRMAP", "SHQ_ATS_H_RECAL")]
    Cn = pd.DataFrame([{"window": w, **E.material(A[w], a, b, met, met == "log_loss")} for w in ("small", "all") for a, b in pairs for met in ("BA", "log_loss", "sensitivity", "specificity")])
    Cn.to_csv(R / "ingr_contrasts.csv", index=False, lineterminator="\n")
    S = pd.DataFrame([{"construction": c, **{f"{m} {w}": float(A[w][A[w].arm == c][m].mean()) for w in ("small", "all") for m in ("BA", "log_loss", "sensitivity", "specificity")}} for c in INGR])
    SR = E.scale_ranking(U); SR.to_csv(R / "ingr_scale_ranking.csv", index=False, lineterminator="\n")
    SRs = SR.groupby(["pair", "budget"]).agg(slope=("slope", "median"), intercept=("intercept", "median"), R2=("R2", "median"), sign_disagree=("sign_disagree", "mean"),
                                             spearman_margin=("spearman_margin", "median"), top1_same=("top1_same", "mean"), top5_jaccard=("top5_jaccard", "mean")).reset_index()
    rc = pd.DataFrame([{"budget": e["budget"], **(e.get("recal") or {})} for u in U for e in u["evals"] if e.get("recal")])
    RCs = rc.groupby("budget").agg(fallback=("fallback", "mean"), a_median=("a", "median"), c_median=("c", "median"), c_q25=("c", lambda x: x.quantile(0.25)), c_q75=("c", lambda x: x.quantile(0.75))).reset_index() if len(rc) else pd.DataFrame()
    AU = E.audit(U, M); AU.to_csv(R / "audit_states.csv", index=False, lineterminator="\n")
    AUs = AU.groupby(["selector", "budget"]).agg(median_ratio_max=("ratio_max", "median"), frac_states_max_lt_1e6=("max_score", lambda x: float(np.mean(x < 1e-6))),
                                                 top1_differs_margin=("top1_same_as_margin", lambda x: 1 - x.mean()), median_spearman_margin=("spearman_vs_margin", "median"),
                                                 top1_differs_eta=("top1_same_as_eta_straddle_H", lambda x: 1 - x.mean()), p_ref_at_top1=("p_ref_at_top1", "median"),
                                                 corner_top1=("corner_top1", "mean"), corner_margin_top1=("corner_margin_top1", "mean")).reset_index()
    V = json.loads((OUT / "RC22_VALIDATION.json").read_text(encoding="utf-8")); extra = max(t["H+REF+BALD_s"] - t["H_only_s"] for t in V["timing"])
    sel, sres = E.decide_selector(AU, V["selector_numerics"]["PASS"], extra); simple, simres = E.decide_simple(A["small"])
    chk = [v for u in U for e in u["evals"] for v in (e.get("check_vs_rc21b") or {}).values()]
    dec = {"SELECTOR": sel, "selector_rule": sres, "SIMPLE": simple, "simple_rule": simres, "reproduction_max_abs_vs_rc21b": max(chk) if chk else None}
    (R / "DECISIONS.json").write_text(json.dumps(dec, indent=1), encoding="utf-8")
    L = ["# RC22 part 2 and acquisition audit — identical saved paid prefixes (RC21B NEW_MARGIN and H_MARGIN paths, repeats 35–42)", "",
         f"Reproduction of the recorded RC21B probabilities: max |Δ| = {dec['reproduction_max_abs_vs_rc21b']:.2e}.", "",
         f"**Pre-registered decisions: SELECTOR = {sel}; SIMPLE = {simple}.**", "", "```", json.dumps({k: v for k, v in dec.items() if k in ("selector_rule", "simple_rule")}, indent=1), "```", "",
         "## All-path means (fold-pooled curves; mean over the 2 path types and 8 repeats)", "", md(S, 4), "",
         "## Matched contrasts (MATERIAL iff |Δ| ≥ 0.010 in the good direction and good in ≥ 7/8)", "", md(Cn, 4), "",
         "## How far is PHR_NRMAP (and the controls) from a common positive scaling of SHQ_ATS_H's logit? (medians / means over states, candidates only)", "", md(SRs, 3), "",
         "## Recalibration coefficients of SHQ_ATS_H_RECAL (logit p' = a + c logit p; fallback = identity)", "", md(RCs, 3), "",
         "## Acquisition audit by budget (BALD_LAP = classifier-weight + grid information; BALD_GRID = grid only)", "", md(AUs, 3), ""]
    _write("ingr", "INGREDIENTS.md", L); return dec


# ======================================================================================== part 1c
def miss():
    M = P.manifest(); U = _load("g-miss"); T = {(t["repeat"], t["fold"]): t for t in P.tasks(sorted({u["repeat"] for u in U}))}; rows = []
    for u in U:
        for cond in ("REAL", "MCAR25", "MCAR50", "QOFF", "SHORTDROP"):
            uu = dict(u); uu["evals"] = [e for e in u["evals"] if e["cond"] == cond]
            rows += E.learner_rows([uu], M, T, cons_map=lambda x, cond=cond: [(c, f"{c}|{cond}") for c in ("SHQ_ATS_H", "PHR_NRMAP")])
    B = E.pooled_metrics(rows); R = OUT / "miss"; R.mkdir(parents=True, exist_ok=True); B.to_csv(R / "miss_pooled_metrics.csv", index=False, lineterminator="\n")
    small, allb = (8, 12, 16, 20, 24), (8, 12, 16, 20, 24, 40, 60)
    A = {w: E.aulc(B, bs) for w, bs in (("small", small), ("all", allb))}
    C = []
    for w in ("small", "all"):
        for c in ("PHR_NRMAP", "SHQ_ATS_H"):
            for cond in ("MCAR25", "MCAR50", "QOFF", "SHORTDROP"):
                for met in ("BA", "log_loss"):
                    C.append({"window": w, "kind": "stress − real", **E.material(A[w], f"{c}|{cond}", f"{c}|REAL", met, met == "log_loss")})
        for cond in ("REAL", "MCAR25", "MCAR50", "QOFF", "SHORTDROP"):
            for met in ("BA", "log_loss"):
                C.append({"window": w, "kind": "REF − H under the condition", **E.material(A[w], f"PHR_NRMAP|{cond}", f"SHQ_ATS_H|{cond}", met, met == "log_loss")})
    C = pd.DataFrame(C); C.to_csv(R / "miss_contrasts.csv", index=False, lineterminator="\n")
    cnt = pd.DataFrame([{"cond": e["cond"], "budget": e["budget"], "n_masked": e["n_masked"], "n_short_paid": e["n_short_paid"]} for u in U for e in u["evals"]]).groupby(["cond", "budget"]).mean().round(2).reset_index()
    chk = [v for u in U for e in u["evals"] for v in (e.get("check_vs_rc21b") or {}).values()]
    L = ["# RC22 part 1c — missing monitor channels and record quality (matched RC21B REF paths; paid training monitors only)", "",
         f"REAL condition reproduces the recorded RC21B probabilities: max |Δ| = {max(chk):.2e}.", "", "## AULC by condition (fold-pooled; mean over 8 repeats)", "",
         md(_summ(A["small"]).assign(window="B8–B24"), 4), "", md(_summ(A["all"]).assign(window="B8–B60"), 4), "", "## Contrasts (MATERIAL rule)", "", md(C, 4), "",
         "## Masked values and paid short records per state (means)", "", md(cnt, 2), ""]
    _write("miss", "MISSING_CHANNELS.md", L); return C


# ======================================================================================== part 1a / 1b
def _robust(part, units, T, title, pairs):
    M = P.manifest(); rows = E.learner_rows(units, M, T, cons_map=lambda u: [(c, f"{a}|{u.get('startup', 'STD')}") for c, a in _seq_map(u)])
    B = E.pooled_metrics(rows); LB = E.learner_metrics(rows); R = OUT / part; R.mkdir(parents=True, exist_ok=True)
    B.to_csv(R / f"{part}_pooled_metrics.csv", index=False, lineterminator="\n"); LB.to_csv(R / f"{part}_learner_metrics.csv", index=False, lineterminator="\n")
    A = {w: E.aulc(B, w) for w in ("small", "all")}; Ep = E.endpoints(B); Ep.to_csv(R / f"{part}_endpoints.csv", index=False, lineterminator="\n")
    V, SP = [], []
    for a, b in pairs:
        for w, met, mg, dirn in (("small", "BA", 0.020, "higher"), ("all", "BA", 0.020, "higher"), ("small", "log_loss", 0.010, "lower"), ("all", "log_loss", 0.005, "lower")):
            V.append({"window": w, **E.contrast(A[w], a, b, met, mg, dirn)})
        for tg in ("BA >= 0.93", "BA >= 0.95", "log_loss <= 0.2"):
            SP.append(E.spend_pair(Ep, a, b, tg))
    V, SP = pd.DataFrame(V), pd.DataFrame(SP); V.to_csv(R / f"{part}_verdicts.csv", index=False, lineterminator="\n"); SP.to_csv(R / f"{part}_spend.csv", index=False, lineterminator="\n")
    ES = Ep.groupby(["target", "arm"]).agg(confirmed=("censored", lambda c: f"{int((~c).sum())}/{len(c)}"), spend_mean=("spend", "mean"), spend_max=("spend", "max")).reset_index()
    LA, _ = E.learner_attainment(LB)
    MB = B[B.budget.isin([8, 12, 16, 24, 40, 60])].groupby(["arm", "budget"])[["BA", "sensitivity", "specificity", "log_loss", "spec_NEW", "q20_BA"]].mean().reset_index()
    acc = export(part, units, rows, B)
    L = [f"# {title}", "", "## Pre-declared contrasts (fold-pooled curves, paired by repeat / seed)", "", md(V, 4), "", "## AULC B8–B24", "", md(_summ(A["small"]), 4), "",
         "## AULC B8–B60", "", md(_summ(A["all"]), 4), "", "## Target attainment of the fold-pooled curves", "", md(ES, 2), "", md(SP, 2), "",
         "## Individual learners (one fold / block each): confirmed own BA ≥ 0.93 by B60 (undefined when the learner's test set has one class)", "", md(LA, 2), "",
         "## Matched budgets (fold-pooled, mean over repeats)", "", md(MB, 3), "", f"Export acceptance: {json.dumps(acc)}", ""]
    return L, B, LB, A


def start():
    U = _load("g-start"); reps = sorted({u["repeat"] for u in U}); T = {(t["repeat"], t["fold"]): t for t in P.tasks(reps)}
    S0 = []
    for r in reps:
        for f in range(1, 6):
            for a, nm in (("NEW_MARGIN", "REF"), ("H_MARGIN", "H"), ("E1S", "E1S")):
                u = RC.read_json_gz(E.EB / f"r{r}_f{f}__{a}.json.gz"); u = dict(u); u["arm"] = nm; u["startup"] = "STD"
                if nm != "E1S":
                    u["evals"] = [dict(e, p={({"NEW_MARGIN": "PHR_NRMAP", "H_MARGIN": "SHQ_ATS_H"}[a]): e["p"][{"NEW_MARGIN": "PHR_NRMAP", "H_MARGIN": "SHQ_ATS_H"}[a]]}) for e in u["evals"]]
                S0.append(u)
    allU = S0 + U; pairs = []
    for st in ("STD", "RAND8", "LOCAL8"):
        pairs += [(f"REF|{st}", f"H|{st}"), (f"REF|{st}", f"E1RAW+straddle|{st}"), (f"REF|{st}", f"E1CAL+straddle|{st}")]
    for arm in ("REF", "H", "E1RAW+straddle"):
        pairs += [(f"{arm}|RAND8", f"{arm}|STD"), (f"{arm}|LOCAL8", f"{arm}|STD")]
    L, B, LB, A = _robust("start", U + S0, T, "RC22 part 1a — lawful startups (STD = completed RC21B trajectories, reused; RAND8 / LOCAL8 new)", pairs)
    disc = []
    for u in allU:
        hows = [e.get("how") for e in u["evals"]]; disc.append({"startup": u.get("startup", "STD"), "arm": u["arm"], "repeat": u["repeat"], "fold": u["fold"],
                                                            "one_class_start": hows[0] == "path" if hows else False, "discovery_queries": int(sum(1 for h in hows if h == "path"))})
    D = pd.DataFrame(disc).groupby(["startup", "arm"]).agg(learners=("fold", "size"), one_class_starts=("one_class_start", "sum"), discovery_queries_mean=("discovery_queries", "mean"),
                                                         discovery_queries_max=("discovery_queries", "max")).reset_index()
    L += ["## Class discovery (label-free continuation until both classes are paid; counted in every budget)", "", md(D, 2), ""]
    _write("start", "STARTUPS.md", L)


def block():
    import src.rc22_common as C
    M = P.manifest(); U = _load("g-block"); TB = {(t["repeat"], t["fold"]): t for t in C.block_tasks(sorted({u["repeat"] for u in U}), M)}
    pairs = [("REF|STD", "H|STD"), ("REF|STD", "E1RAW+straddle|STD"), ("REF|STD", "E1CAL+straddle|STD")]
    L, B, LB, A = _robust("block", U, TB, "RC22 part 1b — geometry-blocked evaluation (k-means k = 5 on public log inputs; each block withheld from fitting and querying)", pairs)
    PB = LB[LB.budget.isin([16, 24, 40, 60])].groupby(["arm", "fold", "budget"])[["n1", "n0", "sensitivity", "specificity", "BA", "log_loss"]].mean().reset_index().rename(columns={"fold": "block+1"})
    X = M[list(P.INPUTS)].to_numpy(float); Z = C._z_all(X); lab = C.blocks(M); ext = []
    for b in range(5):
        te, po = np.flatnonzero(lab == b), np.flatnonzero(lab != b); lo, hi = Z[po].min(0), Z[po].max(0)
        dnn = np.min(np.linalg.norm(Z[te][:, None] - Z[po][None], axis=2), axis=1); dpp = np.sort(np.linalg.norm(Z[po][:, None] - Z[po][None], axis=2), axis=1)[:, 1]
        ext.append({"block+1": b + 1, "n": len(te), "keyhole": int(M.y.to_numpy()[te].sum()), "P_median_W": float(np.median(X[te, 0])), "VX_median": float(np.median(X[te, 1])),
                    "LS_median_um": float(np.median(X[te, 2]) * 1e6), "ST_median": float(np.median(X[te, 3])), "frac_outside_pool_box": float(np.mean(np.any((Z[te] < lo) | (Z[te] > hi), axis=1))),
                    "median_dist_to_pool": float(np.median(dnn)), "median_nn_within_pool": float(np.median(dpp))})
    L += ["## Blocks: geometry and extrapolation (public inputs; labels evaluator-side)", "", md(pd.DataFrame(ext), 3), "",
          "## Per block (individual learners, mean over 8 seeds; BA undefined when the block has one class)", "", md(PB, 3), ""]
    _write("block", "BLOCKS.md", L)


# ======================================================================================== part 3
def acq():
    import src.rc22_decisions as DEC
    M = P.manifest(); U = _load("g-acq"); T = {(t["repeat"], t["fold"]): t for t in P.tasks(sorted({u["repeat"] for u in U}))}
    arms = sorted({u["arm"] for u in U}); pr = ("A3_SEL_COV", "A2_MARGIN_COV")
    pairs = ([pr] if "A3_SEL_COV" in arms else []) + [("A2_MARGIN_COV", "A1_MARGIN"), ("A3_SEL_COV", "A1_MARGIN"), ("A4_MAXIMIN", "A1_MARGIN"), ("A5_SIMPLE", "A1_MARGIN")]
    pairs = [p for p in pairs if p[0] in arms and p[1] in arms]
    rows = E.learner_rows(U, M, T, cons_map=lambda u: [(list(u["evals"][0]["p"].keys())[0], u["arm"])]); B = E.pooled_metrics(rows); LB = E.learner_metrics(rows)
    R = OUT / "acq"; R.mkdir(parents=True, exist_ok=True); B.to_csv(R / "acq_pooled_metrics.csv", index=False, lineterminator="\n"); LB.to_csv(R / "acq_learner_metrics.csv", index=False, lineterminator="\n")
    A = {w: E.aulc(B, w) for w in ("small", "all")}; Ep = E.endpoints(B); Ep.to_csv(R / "acq_endpoints.csv", index=False, lineterminator="\n")
    V, SP = [], []
    for a, b in pairs:
        for w, met, mg, dirn in (("small", "BA", 0.020, "higher"), ("all", "BA", 0.020, "higher"), ("all", "BA", 0.010, "higher"), ("small", "log_loss", 0.010, "lower"),
                                 ("all", "log_loss", 0.005, "lower"), ("small", "sensitivity", 0.020, "higher"), ("small", "specificity", 0.020, "higher")):
            V.append({"window": w, **E.contrast(A[w], a, b, met, mg, dirn)})
        for tg in ("BA >= 0.93", "BA >= 0.95", "log_loss <= 0.2"):
            SP.append(E.spend_pair(Ep, a, b, tg))
    V, SP = pd.DataFrame(V), pd.DataFrame(SP); V.to_csv(R / "acq_verdicts.csv", index=False, lineterminator="\n"); SP.to_csv(R / "acq_spend.csv", index=False, lineterminator="\n")
    succ = None
    if "A3_SEL_COV" in arms:
        q1 = V[(V.contrast == "A3_SEL_COV − A2_MARGIN_COV") & (V.metric == "BA") & (V.window == "small") & (V.margin == 0.020)].iloc[0]
        q2 = SP[(SP.contrast == "A3_SEL_COV − A2_MARGIN_COV") & (SP.target == "BA >= 0.93")].iloc[0]
        harm = V[(V.contrast == "A3_SEL_COV − A2_MARGIN_COV") & (V.metric == "BA") & (V.window == "all") & (V.margin == 0.010)].iloc[0]
        succ = {"Q1": q1.verdict, "Q2": q2.verdict, "B8_B60_BA_margin_0.010": harm.verdict,
                "SUCCESS": bool((q1.verdict.startswith("BETTER") or q2.verdict.startswith("FEWER")) and not harm.verdict.startswith("WORSE"))}
    ES = Ep.groupby(["target", "arm"]).agg(confirmed=("censored", lambda c: f"{int((~c).sum())}/{len(c)}"), spend_mean=("spend", "mean"), spend_max=("spend", "max"),
                                         per_repeat=("spend", lambda x: ",".join("–" if pd.isna(v) else str(int(v)) for v in x))).reset_index()
    LA, _ = E.learner_attainment(LB)
    corner = pd.Series(E.CORNER(M), index=M.index); y = M.y; disc = []
    for u in U:
        ids = u["paid_ids"]; cr = corner.reindex(ids).to_numpy(bool); yy = y.reindex(ids).to_numpy(int)
        first_c = next((q + 1 for q, v in enumerate(cr) if v), None); first_cc = next((q + 1 for q, (v, w) in enumerate(zip(cr, yy)) if v and w == 0), None)
        hows = [e.get("how") for e in u["evals"]]
        disc.append({"arm": u["arm"], "first_corner_query": first_c, "first_corner_conduction_hit": first_cc, "corner_share_B24": float(cr[:24].mean()), "corner_share_B60": float(cr[:60].mean()),
                     "coverage_queries": sum(h == "coverage" for h in hows), "selection_cpu_s_per_step": float(np.mean([e["cpu_s"] for e in u["evals"] if e.get("cpu_s") is not None]))})
    D = pd.DataFrame(disc).groupby("arm").agg(first_corner_query=("first_corner_query", "median"), first_corner_conduction_hit=("first_corner_conduction_hit", "median"),
                                             corner_share_B24=("corner_share_B24", "mean"), corner_share_B60=("corner_share_B60", "mean"), coverage_queries=("coverage_queries", "mean"),
                                             cpu_s_per_step=("selection_cpu_s_per_step", "mean")).reset_index()
    MB = B[B.budget.isin([8, 12, 16, 20, 24, 32, 40, 60])].groupby(["arm", "budget"])[["BA", "sensitivity", "specificity", "log_loss", "spec_NEW", "q20_BA", "corner_cond_errors", "corner_key_errors"]].mean().reset_index()
    acc = export("acq", U, rows, B)
    L = ["# RC22 part 3 — acquisition comparison (fresh DEV repeats 43–50; predictive model PHR_NRMAP and cutoff 0.5 fixed in every arm)", "",
         f"SELECTOR = {DEC.SELECTOR}; SIMPLE = {DEC.SIMPLE}; arms: {arms}.", "", f"**Primary (A3 − A2): {json.dumps(succ)}**", "",
         "## Pre-declared contrasts (fold-pooled curves, paired by repeat)", "", md(V, 4), "", "## AULC B8–B24", "", md(_summ(A["small"]), 4), "", "## AULC B8–B60", "", md(_summ(A["all"]), 4), "",
         "## Target attainment (fold-pooled curves)", "", md(ES, 2), "", md(SP, 2), "", "## Individual learners: confirmed own-fold BA ≥ 0.93 by B60", "", md(LA, 2), "",
         "## Discovery vs learning (evaluator-defined corner VX > 0.85 m/s, P > 330 W; never used by any policy) and selection CPU", "", md(D, 2), "",
         "## Matched budgets (fold-pooled, mean over repeats)", "", md(MB, 3), "", f"Export acceptance: {json.dumps(acc)}", ""]
    _write("acq", "ACQUISITION.md", L); return succ


def smoke():
    U = _load("g-smoke"); print(len(U), "smoke units;", sorted({(u.get("startup"), u["arm"]) for u in U}))
    for u in U:
        print(u["arm"], u.get("startup"), u.get("block"), u["queries"], round(u.get("cpu_s", 0), 1), sorted(set(e.get("how", "") for e in u["evals"])))


if __name__ == "__main__":
    RC.limit_threads(1); {"ingr": ingr, "miss": miss, "start": start, "block": block, "acq": acq, "smoke": smoke}[sys.argv[1]]()
