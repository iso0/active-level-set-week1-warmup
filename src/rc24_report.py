"""RC24 reports (presentation layer; every metric, verdict, status and decision comes from the frozen src/rc24_eval.py,
src/rc22_eval.py, src/rc23_eval.py and src/rc24_correction.py).
    python -m src.rc24_report stage_a
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc19_pool as P
import src.rc23_eval as E23
import src.rc24_eval as E
from src.rc19_report import md

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc24"


def _summ(T, cols):
    cols = [c for c in cols if c in T]
    S = T.groupby("arm")[cols].agg(["mean", lambda x: x.std(ddof=1) / np.sqrt(len(x))]); S.columns = [f"{a}_{'se' if b == '<lambda_0>' else b}" for a, b in S.columns]
    return S.reset_index()


def stage_a():
    M = P.manifest(); d = OUT / "stage_a"; d.mkdir(parents=True, exist_ok=True)
    U = EV.load_units(OUT / "a-own"); T = {(t["repeat"], t["fold"]): t for t in P.tasks(sorted({u["repeat"] for u in U}))}
    rows = E.own_rows(U, M, T); B, LB, A, AL = E.tables(rows, M); EP = E23.endpoints(B); EPL = E23.endpoints(LB, by=("arm", "repeat", "fold"))
    B.to_csv(d / "own_pooled_metrics.csv", index=False); LB.to_csv(d / "own_learner_metrics.csv", index=False); EP.to_csv(d / "own_endpoints_pooled.csv", index=False)
    EPL.to_csv(d / "own_endpoints_learners.csv", index=False)
    cols = ("BA", "sensitivity", "specificity", "log_loss", "brier", "AUC", "BA_hard_group", "q20_BA")
    S = {w: _summ(A[w], cols) for w in ("small", "all")}; SL = {w: _summ(AL[w], ("BA", "sensitivity", "specificity", "log_loss")) for w in ("small", "all")}
    C = []
    for a in E.COMPARATORS + ("E1S_RAW",):
        C += [{"comparator": a, **r} for r in E.contrasts(A, EP, a)]
    C = pd.DataFrame(C); C.to_csv(d / "own_contrasts_vs_HA_LEAN_MARGIN.csv", index=False)
    att = E23.attainment_table(EP); att.to_csv(d / "own_attainment_pooled.csv", index=False); attL = E23.attainment_table(EPL); attL.to_csv(d / "own_attainment_learners.csv", index=False)
    q1 = E.decide_q1(A, EP); q2 = {a: E.decide_vs_ref(A, EP, a) for a in ("M3_MARGIN", "E1S", "G3_MARGIN", "E1S_RAW")}; q3 = E.decide_vs_ref(A, EP, "HA_LEAN_STRADDLE")
    aud = E.straddle_audit([u for u in U if u["arm"] == "HA_LEAN_STRADDLE"])
    hard = B[B.budget.isin([24, 40, 60])].groupby(["arm", "budget"])[["recall_shortK_NEW", "spec_cond_NEW", "BA_hard_group", "recall_shortK_pooled", "corner_cond_errors", "corner_key_errors"]].mean().reset_index()
    hard.to_csv(d / "own_hard_region.csv", index=False)
    cpu = pd.DataFrame([{"arm": u["arm"], "cpu_s_per_step": np.mean([e.get("cpu_s", np.nan) for e in u["evals"]])} for u in U]).groupby("arm").cpu_s_per_step.agg(["mean", "median"]).reset_index()
    # matched matrix
    UM = EV.load_units(OUT / "a-match"); dec, chk = {}, []
    if UM:
        rm = E.match_rows(UM, M, T); Bm = E22_pooled(rm, M); Bm.to_csv(d / "match_pooled_metrics.csv", index=False)
        for u in UM:
            for e in u["evals"]:
                chk += list(e.get("check_vs_own", {}).values())
        for a in ("HONLY_MARGIN", "M3_MARGIN", "E1S", "G3_MARGIN", "HA_LEAN_STRADDLE"):
            dec[a] = {w: E.decomposition(Bm, a, w) for w in ("small", "all")}
        AM = {w: __import__("src.rc22_eval", fromlist=["aulc"]).aulc(Bm, E.WIN_MB[w], cols=("BA", "AUC", "BA_oracle_threshold", "log_loss", "sensitivity", "specificity", "BA_hard_group")) for w in ("small", "all")}
        MM = {w: _summ(AM[w], ("BA", "AUC", "BA_oracle_threshold", "log_loss", "BA_hard_group")) for w in ("small", "all")}
        for w in ("small", "all"):
            MM[w].to_csv(d / f"match_aulc_{w}.csv", index=False)
        hardm = Bm[Bm.budget.isin([40, 60])].groupby(["arm", "budget"])[["recall_shortK_NEW", "spec_cond_NEW", "BA_hard_group", "recall_shortK_pooled"]].mean().reset_index()
        hardm.to_csv(d / "match_hard_region.csv", index=False)
    res = {"utc": RC.utc(), "units_own": len(U), "units_match": len(UM), "Q1": q1, "Q2": q2, "Q3": q3, "straddle_audit": aud, "Q4": dec,
           "match_reproduction_max_abs_vs_own": float(max(chk)) if chk else None, "match_reproduction_checks": len(chk)}
    (d / "STAGE_A_DECISIONS.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    L = ["# RC24 Stage A — strong comparisons (fresh DEV repeats 59–66, 40 tasks per arm)", "",
         f"Own-query units {len(U)}; matched units {len(UM)}; matched reproduction of own-path probabilities: max |Δ| = {res['match_reproduction_max_abs_vs_own']} ({len(chk)} checks).", "",
         "## Fold-pooled AULC, own query (mean and SE over 8 repeats)", "", "B8–B24:", "", md(S["small"], 4), "", "B8–B60:", "", md(S["all"], 4), "",
         "## Individual learners (AULC averaged over 40 learners)", "", "B8–B24:", "", md(SL["small"], 4), "", "B8–B60:", "", md(SL["all"], 4), "",
         "## Contrasts against HA_LEAN + margin (RC23 D1)", "", md(C, 4), "",
         "## Target attainment (fold-pooled)", "", md(att, 3), "", "## Target attainment (individual learners)", "", md(attL, 3), "",
         "## Pre-registered decisions", "", f"- **Q1 (h alone sufficient?)** {q1[0]} — {json.dumps(q1[1], default=str)}",
         *[f"- **Q2 {a}** {v[0]} — {json.dumps(v[1], default=str)}" for a, v in q2.items()], f"- **Q3 (straddle vs margin on HA_LEAN)** {q3[0]} — {json.dumps(q3[1], default=str)}",
         f"- Straddle discriminability audit: {json.dumps(aud)}", "", "## Q4 decomposition (matched matrix, BA-AULC on the step-4 grid)", ""]
    for a, v in dec.items():
        for w, r in v.items():
            L.append(f"- {a} [{w}]: total {r['total_own_query']['mean']:+.4f} = model on X path {r['order1_model_on_X_path']['mean']:+.4f} + path for HA_LEAN {r['order1_path_for_HA_LEAN']['mean']:+.4f}; "
                     f"model on HA_LEAN path {r['order2_model_on_HA_LEAN_path']['mean']:+.4f}, path for X {r['order2_path_for_X']['mean']:+.4f}, interaction {r['interaction']['mean']:+.4f}")
    L += ["", "## Hard region (own query; evaluator-only memberships)", "", md(hard, 3), "", "## Compute (CPU s per step)", "", md(cpu, 3), ""]
    (d / "STAGE_A.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L)[:12000])


def stage_c():
    import src.rc22_common as C22
    import src.rc22_eval as E22
    import src.rc24_eval_c as EC
    M = P.manifest(); C22.set_manifest(M); d = OUT / "stage_c"; d.mkdir(parents=True, exist_ok=True)
    U = EV.load_units(OUT / "c-own"); UM = EV.load_units(OUT / "c-match"); res = {"utc": RC.utc(), "units_own": len(U), "units_match": len(UM)}; L = []
    tabs = {}
    for cond in ("STD", "BLOCK"):
        Uc = [u for u in U if (u.get("block") is None) == (cond == "STD")]; Mc = [u for u in UM if (u.get("block") is None) == (cond == "STD")]
        if cond == "STD":
            T = {(t["repeat"], t["fold"]): t for t in P.tasks(sorted({u["repeat"] for u in Uc}))}
        else:
            T = {(t["repeat"], t["fold"]): t for t in C22.block_tasks(sorted({u["repeat"] for u in Uc}), M)}
        r_own = EC.own_rows(Uc, M, T); r_ht, r_m = EC.derived_rows(Mc, M, T)
        B, LB, A, AL = EC.tables(r_own + r_ht, M); Bm, LBm, Am, ALm = EC.tables(r_m, M); EP = E23.endpoints(B); EPL = E23.endpoints(LB, by=("arm", "repeat", "fold"))
        tabs[cond] = (A, EP)
        for nm, T_ in (("pooled_metrics", B), ("learner_metrics", LB), ("match_pooled_metrics", Bm), ("endpoints_pooled", EP), ("endpoints_learners", EPL)):
            T_.to_csv(d / f"{cond.lower()}_{nm}.csv", index=False)
        cols = ("BA", "sensitivity", "specificity", "log_loss", "brier", "AUC", "BA_hard_group")
        S = {w: _summ(A[w], cols) for w in ("small", "all")}; SL = {w: _summ(AL[w], ("BA", "sensitivity", "specificity", "log_loss")) for w in ("small", "all")}
        SM = {w: _summ(Am[w], ("BA", "log_loss", "AUC", "BA_hard_group")) for w in ("small", "all")}
        C = []
        for a in ("HA_TREND_MARGIN", "HT_PHYS", "HONLY_MARGIN"):
            C += [{"comparator": a, **r} for r in E.contrasts(A, EP, a)]
        for a in ("HA_TREND_MARGIN", "HT_PHYS"):
            C += [{"comparator": a, **r} for r in E.contrasts(A, EP, a, b="HONLY_MARGIN")]
        C = pd.DataFrame(C); C.to_csv(d / f"{cond.lower()}_contrasts.csv", index=False)
        att = E23.attainment_table(EP); attL = E23.attainment_table(EPL)
        hard = B[B.budget.isin([40, 60])].groupby(["arm", "budget"])[["recall_shortK_NEW", "spec_cond_NEW", "BA_hard_group", "recall_shortK_pooled", "corner_cond_errors"]].mean().reset_index()
        q = pd.DataFrame([{"arm": u["arm"], "corner_query_share": float(E22.CORNER(M.reindex(u["paid_ids"][8:])).mean()), "cpu_s_per_step": np.mean([e.get("cpu_s", np.nan) for e in u["evals"]])} for u in Uc]).groupby("arm").mean().reset_index()
        mtc = []
        for k in ("HA_TREND", "HA_TREND_B1", "HA_TREND_B10", "PAC", "PAC_GEN", "HONLY_LR"):
            for w in ("small", "all"):
                r = E22.contrast(Am[w], f"{k}@HA_LEAN_MARGIN", "HA_LEAN@HA_LEAN_MARGIN", "BA", 0.020, "higher"); mtc.append({"window": w, "contrast": r["contrast"], "mean": r["mean"], "good": r["good"], "verdict": r["verdict"]})
        chk = [v for u in Mc for e in u["evals"] for v in e.get("check_vs_own", {}).values()]
        L += [f"## {cond}", "", f"Own-query units {len(Uc)}; matched units {len(Mc)}; matched reproduction of own-path probabilities max |Δ| = {max(chk) if chk else None} ({len(chk)} checks).", "",
              "Fold-pooled AULC B8–B24:", "", md(S["small"], 4), "", "B8–B60:", "", md(S["all"], 4), "", "Individual learners B8–B24:", "", md(SL["small"], 4), "", "B8–B60:", "", md(SL["all"], 4), "",
              "Contrasts:", "", md(C, 4), "", "Attainment (fold-pooled):", "", md(att, 2), "", "Attainment (individual learners):", "", md(attL, 2), "",
              "Matched on the HA_LEAN paths (prior sensitivity, falsifying controls):", "", md(SM["small"], 4), "", md(SM["all"], 4), "", md(pd.DataFrame(mtc), 4), "",
              "Hard group / corner errors:", "", md(hard, 3), "", "Corner query share and CPU:", "", md(q, 3), ""]
    lab, det = EC.decide(tabs["STD"][0], tabs["STD"][1], tabs["BLOCK"][0], "HA_TREND_MARGIN"); lab2, det2 = EC.decide(tabs["STD"][0], tabs["STD"][1], tabs["BLOCK"][0], "HT_PHYS")
    dom = EC.vs_honly(tabs["STD"][0], tabs["BLOCK"][0], "HA_TREND_MARGIN"); dom2 = EC.vs_honly(tabs["STD"][0], tabs["BLOCK"][0], "HT_PHYS")
    res.update({"PRIMARY_HA_TREND_MARGIN": {"label": lab, **det}, "SECONDARY_HT_PHYS": {"label": lab2, **det2}, "vs_HONLY_primary": dom, "vs_HONLY_secondary": dom2})
    (d / "STAGE_C_DECISION.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    head = ["# RC24 Stage C — confirmatory test on fresh data (STD repeats 67–74, BLOCK seeds 9–16)", "", f"**Primary HA_TREND + margin: {lab}** — {json.dumps(det['components'])}",
            f"Secondary HT_PHYS: {lab2} — {json.dumps(det2['components'])}", "", f"Against h-only (primary): {json.dumps(dom, default=str)}", f"Against h-only (secondary): {json.dumps(dom2, default=str)}", ""]
    (d / "STAGE_C.md").write_text("\n".join(head + L) + "\n", encoding="utf-8"); print("\n".join(head)); return res


def export(d, U, rows, B):
    """Compact float32 predictions + query paths with an acceptance check (metrics recomputed from the export equal the tables;
    the RC23 export logic, src/rc23_report.py::export, with the output folder as argument)."""
    import src.rc22_eval as E22
    d.mkdir(parents=True, exist_ok=True); acc = {}; keys, arrs, tids, buds, paths = [], [], [], [], []
    for r in rows:
        acc.setdefault((r["arm"], r["repeat"], r["fold"]), {})[r["budget"]] = r
    for (arm, rep, f), bd in acc.items():
        bs = sorted(bd); keys.append(f"{arm}|r{rep}|f{f}"); arrs.append(np.asarray([bd[b]["p"] for b in bs], np.float32)); tids.append(np.asarray(bd[bs[0]]["ids"])); buds.append(np.asarray(bs, np.int16))
    for u in U:
        hows = [e.get("how") for e in u["evals"]]
        for q, s_ in enumerate(u.get("paid_ids", []), 1):
            paths.append({"arm": u.get("arm", u.get("path_of")), "block": u.get("block"), "repeat": u["repeat"], "fold": u["fold"], "query": q, "sim_id": s_,
                          "rule": "startup" if q <= P.B0 else (hows[q - P.B0 - 1] if q - P.B0 - 1 < len(hows) and hows[q - P.B0 - 1] else "margin")})
    np.savez_compressed(d / "predictions_f32.npz", keys=np.asarray(keys), **{f"pred_{i}": v for i, v in enumerate(arrs)}, **{f"test_ids_{i}": t for i, t in enumerate(tids)},
                        **{f"budgets_{i}": t for i, t in enumerate(buds)}, schema=np.asarray([json.dumps({"pred": "pred[budget, test] = P(Keyhole), float32; key arm|repeat|fold"})]))
    pd.DataFrame(paths).to_csv(d / "paths.csv.gz", index=False, compression="gzip")
    Z = np.load(d / "predictions_f32.npz", allow_pickle=False); byk = {(r["arm"], r["repeat"], r["fold"], r["budget"]): r for r in rows}; R2 = []
    for i, k in enumerate(Z["keys"]):
        arm, rep, f = k.rsplit("|", 2)
        for j, b in enumerate(Z[f"budgets_{i}"]):
            rr = dict(byk[(arm, int(rep[1:]), int(f[1:]), int(b))]); rr["p"] = Z[f"pred_{i}"][j].astype(float); R2.append(rr)
    B2 = E22.pooled_metrics(R2); B0 = E22.pooled_metrics(rows); j = B2.merge(B0, on=["arm", "repeat", "budget"], suffixes=("_x", "_t")); res = {"cells": int(len(j)), "cells_table": int(len(B0))}
    for c in ("BA", "log_loss", "sensitivity", "specificity", "brier"):
        dd = np.abs(j[f"{c}_x"].to_numpy(float) - j[f"{c}_t"].to_numpy(float)); dd = dd[np.isfinite(dd)]; res[c] = float(dd.max()) if len(dd) else 0.0
    res["PASS"] = bool(res["cells"] == res["cells_table"] and all(res[c] <= 1e-12 for c in ("BA", "log_loss", "sensitivity", "specificity", "brier")))
    (d / "EXPORT_ACCEPTANCE.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); return res


def exports():
    import src.rc22_common as C22
    import src.rc24_eval_c as EC
    M = P.manifest(); C22.set_manifest(M); out = {}
    U = EV.load_units(OUT / "a-own"); T = {(t["repeat"], t["fold"]): t for t in P.tasks(sorted({u["repeat"] for u in U}))}; rows = E.own_rows(U, M, T)
    out["stage_a"] = export(OUT / "stage_a" / "export", U, rows, None)
    U = EV.load_units(OUT / "c-own")
    for cond in ("STD", "BLOCK"):
        Uc = [u for u in U if (u.get("block") is None) == (cond == "STD")]
        T = ({(t["repeat"], t["fold"]): t for t in P.tasks(sorted({u["repeat"] for u in Uc}))} if cond == "STD" else
             {(t["repeat"], t["fold"]): t for t in C22.block_tasks(sorted({u["repeat"] for u in Uc}), M)})
        out[f"stage_c_{cond}"] = export(OUT / "stage_c" / f"export_{cond.lower()}", Uc, EC.own_rows(Uc, M, T), None)
    print(out); return out


def E22_pooled(rows, M):
    import src.rc22_eval as E22
    Bm = E22.pooled_metrics(rows); X = E.extra_pooled(rows, M); return Bm.merge(X, on=["arm", "repeat", "budget"], how="left")


if __name__ == "__main__":
    RC.limit_threads(1); {"stage_a": stage_a, "stage_c": stage_c, "exports": exports}[sys.argv[1]]()
