"""RC24 post-audit reporting: final comparison tables, the frozen decision, exports of EVERY comparison arm (own, secondary, control,
matched constructions) with an independent metric recomputation check.
    python -m src.rc24p_report final | exports
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc19_pool as P
import src.rc22_common as C22
import src.rc24p_audit as AU
import src.rc24p_eval as FE
import src.rc24p_final as FF
from src.rc19_report import md

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc24"
D_OUT = OUT / "post_audit" / "final"


def _cond_units(U, cond):
    return [u for u in U if u.get("condition") == cond]


def final():
    D_OUT.mkdir(parents=True, exist_ok=True); M = P.manifest(); C22.set_manifest(M)
    U = EV.load_units(OUT / "f-own"); UM = EV.load_units(OUT / "f-match"); res = {"utc": RC.utc(), "units_own": len(U), "units_match": len(UM)}; parts = {}; L = []
    for cond in FF.COND:
        Uc = _cond_units(U, cond); D, G, Ap, Ai = FE.tables(FE.to_E(Uc), M.y); Ep = AU.endpoints(G, ("arm", "repeat")); Ei = AU.endpoints(D, ("arm", "repeat", "fold"))
        parts[cond] = {"Ap": Ap, "Ai": Ai, "Ep": Ep}
        for nm, T in (("pooled_aulc", Ap), ("individual_aulc", Ai), ("endpoints_pooled", Ep), ("endpoints_learners", Ei), ("learner_curves", D), ("pooled_curves", G)):
            T.to_csv(D_OUT / f"{cond.lower()}_{nm}.csv", index=False)
        summ = Ap.groupby(["window", "arm"])[["BA", "sens", "spec", "ll"]].mean().round(4).reset_index()
        reg = FE.region_mean(Ai, "B8_B60").groupby("arm").BA.mean().round(4) if cond != "STD" else None
        ind = Ai.groupby(["window", "arm"])[["BA", "sens", "spec", "ll"]].mean().round(4).reset_index()
        sp = pd.concat([AU.spend_compare(Ep, a, FE.REF) for a in (FE.CAND, FE.HON, FE.GEN)]); sp.to_csv(D_OUT / f"{cond.lower()}_spend_vs_HA_LEAN.csv", index=False)
        Ei2 = Ei.copy(); Ei2["unit"] = Ei2.repeat.astype(str) + "_" + Ei2.fold.astype(str)
        spl = pd.concat([AU.spend_compare(Ei2, a, FE.REF, by="unit") for a in (FE.CAND, FE.HON, FE.GEN)]); spl.to_csv(D_OUT / f"{cond.lower()}_spend_vs_HA_LEAN_learners.csv", index=False)
        L += [f"## {cond}", "", "Pooled AULC:", "", md(summ, 4), "", "Individual learners (one block or fold each; BA NaN for one-class test sets):", "", md(ind, 4), ""]
        if reg is not None:
            cnt = D[(D.budget == 8)].groupby("fold")[["n1", "n0"]].first().reset_index()
            pb = Ai[Ai.window == "B8_B60"].groupby(["fold", "arm"])[["BA", "sens", "spec"]].mean().round(3).reset_index()
            mins = []
            for (f, arm), g in D[D.budget == 60].groupby(["fold", "arm"]):
                n1, n0, tp, tn = int(g.n1.sum()), int(g.n0.sum()), int(g.tp.sum()), int(g.tn.sum())
                mins.append({"block": f, "arm": arm, "keyhole_hits": f"{tp}/{n1}", "keyhole_CI95": AU.cp(tp, n1), "conduction_hits": f"{tn}/{n0}", "conduction_CI95": AU.cp(tn, n0)})
            dec = {f"{a} − {FE.REF}": AU.decomposition(D, a, FE.REF) for a in (FE.CAND, FE.HON, FE.GEN)}
            L += ["Class counts per block:", "", md(cnt, 0), "", "Per-region mean BA-AULC B8–B60 over the two-class blocks:", "", md(reg.reset_index(), 4), "",
                  "Per block (B8–B60 AULC):", "", md(pb, 3), "", "Minority / majority hits at B60 (summed over startups; exact 95 % CI):", "", md(pd.DataFrame(mins), 3), ""]
            for k, v in dec.items():
                v = v[v.window == "B8_B60"]; L += [f"Pooled-difference decomposition {k} (B8–B60): " + "; ".join(f"block {int(r.fold)}: K {r.cK:+.4f}, C {r.cC:+.4f}" for r in v.itertuples()), ""]
        L += ["Spend vs HA_LEAN (pooled curves):", "", md(sp, 3), "", "Spend vs HA_LEAN (individual learners):", "", md(spl, 3), ""]
    dec = FE.decide(parts["STD"], parts["BLOCK_A"], parts["BLOCK_B"]); res["decision"] = dec
    # matched trend family on the F_HA_LEAN paths
    mrows = []
    for cond in FF.COND:
        Um = _cond_units(UM, cond); E = FE.match_E(Um, ("TR_NONE", "TR_PHYS", "TR_GEN3", "TR_GEN15", "HONLY_LR")); D, G, Ap, Ai = FE.tables(E, M.y)
        Ap4 = AU.aulc(G[G.budget.isin(range(8, 61, 4))], ("arm", "repeat"), cols=("BA", "ll")); R4 = Ai if cond == "STD" else FE.region_mean(Ai)
        for a, b in (("TR_PHYS", "TR_NONE"), ("TR_GEN15", "TR_NONE"), ("TR_PHYS", "TR_GEN15"), ("TR_GEN3", "TR_GEN15"), ("HONLY_LR", "TR_NONE")):
            for w in ("B8_B24", "B8_B60"):
                r = FE._paired(Ap4, f"{a}@HA_LEAN_path", f"{b}@HA_LEAN_path", "BA", window=w); mrows.append({"condition": cond, "window": w, "metric": "pooled BA", "contrast": f"{a} − {b}", **r})
            if cond != "STD":
                r = FE._paired(R4, f"{a}@HA_LEAN_path", f"{b}@HA_LEAN_path", "BA"); mrows.append({"condition": cond, "window": "B8_B60", "metric": "per-region BA", "contrast": f"{a} − {b}", **r})
        chk = [e["check_TR_NONE_vs_own_HA_LEAN"] for u in Um for e in u["evals"]]; res[f"match_check_{cond}"] = {"max_abs": float(max(chk)) if chk else None, "n": len(chk)}
    MR = pd.DataFrame(mrows); MR.to_csv(D_OUT / "matched_trend_family.csv", index=False)
    L += ["## Matched trend family on the F_HA_LEAN paths (step-4 grid)", "", md(MR.round(4), 4), ""]
    (D_OUT / "FINAL_DECISION.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    head = ["# RC24 post-audit final comparison (fresh STD repeats 75–82; BLOCK_A = same five regions with new startups 17–24; BLOCK_B = new k = 4 partition)", "",
            f"**Frozen decision: {dec['choice']}**", "", "In-distribution components (HA_TREND vs HA_LEAN): " + json.dumps({k: v["status"] for k, v in dec["candidate_in_distribution"].items()}),
            "Extrapolation (HA_TREND vs HA_LEAN): " + json.dumps({c: {k: v[k]["status"] for k in v} for c, v in dec["candidate_extrapolation"].items()}),
            f"Early superiority shown: {dec['early_superiority']['shown']}; physics-specific benefit shown: {dec['physics_specific']['shown']}",
            "h-only vs HA_LEAN: " + json.dumps({k: v["status"] for k, v in dec["honly_vs_ref"].items()}), ""]
    (D_OUT / "FINAL_COMPARISON.md").write_text("\n".join(head + L) + "\n", encoding="utf-8"); print("\n".join(head)); return res


def _export(d, units_or_E, M, from_units=True):
    """Compact float32 export + independent recomputation (rc24p_audit from the npz vs the RC22 metric code from the predictions)."""
    import src.rc22_eval as E22
    d.mkdir(parents=True, exist_ok=True); E = units_or_E; keys, arrs, tids, buds = [], [], [], []
    for (arm, rep, f), (bs, Pm, ids) in E.items():
        keys.append(f"{arm}|r{rep}|f{f}"); arrs.append(Pm.astype(np.float32)); tids.append(ids); buds.append(bs.astype(np.int16))
    np.savez_compressed(d / "predictions_f32.npz", keys=np.asarray(keys), **{f"pred_{i}": v for i, v in enumerate(arrs)}, **{f"test_ids_{i}": t for i, t in enumerate(tids)},
                        **{f"budgets_{i}": t for i, t in enumerate(buds)}, schema=np.asarray([json.dumps({"pred": "pred[budget, test] = P(Keyhole), float32; key arm|repeat|fold"})]))
    Z = AU.load_export(d); A1 = AU.pooled(AU.rows_from(Z, M.y))
    rows = []
    for (arm, rep, f), (bs, Pm, ids) in E.items():
        y = M.y.reindex(ids).to_numpy(int)
        for j, b in enumerate(bs):
            rows.append({"arm": arm, "repeat": rep, "fold": f, "budget": int(b), "p": Pm[j].astype(np.float32).astype(float), "y": y, "new": np.zeros(len(y), bool), "corner": np.zeros(len(y), bool), "q20": None, "ids": ids})
    B = E22.pooled_metrics(rows, n_learners=max(1, int(pd.Series([k[2] for k in E]).max())))
    j = A1.merge(B, on=["arm", "repeat", "budget"], suffixes=("_aud", "_rc22")); acc = {"cells": int(len(j))}
    for c_a, c_b in (("BA", "BA"), ("sens", "sensitivity"), ("spec", "specificity")):
        dd = np.abs(j[f"{c_a}_aud" if c_a == "BA" else c_a].to_numpy(float) - j[f"{c_b}_rc22" if c_b == "BA" else c_b].to_numpy(float)); dd = dd[np.isfinite(dd)]; acc[c_a] = float(dd.max()) if len(dd) else 0.0
    acc["PASS"] = bool(acc["cells"] > 0 and all(acc[k] <= 1e-12 for k in ("BA", "sens", "spec")))
    (d / "EXPORT_ACCEPTANCE.json").write_text(json.dumps(acc, indent=1), encoding="utf-8"); return acc


def _paths(units, d, arm_key="arm"):
    rows = []
    for u in units:
        hows = [e.get("how") for e in u["evals"]]
        for q, s in enumerate(u.get("paid_ids", []), 1):
            rows.append({"arm": u.get(arm_key) or u.get("path_of"), "condition": u.get("condition", u.get("source")), "repeat": u["repeat"], "fold": u["fold"], "query": q, "sim_id": s,
                         "rule": "startup" if q <= P.B0 else (hows[q - P.B0 - 1] if q - P.B0 - 1 < len(hows) and hows[q - P.B0 - 1] else "margin")})
    pd.DataFrame(rows).to_csv(d / "paths.csv.gz", index=False, compression="gzip")


def exports():
    M = P.manifest(); acc = {}; base = OUT / "post_audit" / "exports"
    U = EV.load_units(OUT / "f-own")
    for cond in FF.COND:
        Uc = _cond_units(U, cond); d = base / f"final_own_{cond.lower()}"; acc[d.name] = _export(d, FE.to_E(Uc), M); _paths(Uc, d)
    UM = EV.load_units(OUT / "f-match")
    for cond in FF.COND:
        Um = _cond_units(UM, cond); d = base / f"final_match_{cond.lower()}"; acc[d.name] = _export(d, FE.match_E(Um, ("TR_NONE", "TR_PHYS", "TR_GEN3", "TR_GEN15", "HONLY_LR")), M); _paths(Um, d, "path_of")
    UP = EV.load_units(OUT / "p-match")
    for src in sorted({u["source"] for u in UP}):
        Us = [u for u in UP if u["source"] == src]; d = base / f"devmatch_{src}"; acc[d.name] = _export(d, FE.match_E(Us, ("TR_NONE", "TR_PHYS", "TR_GEN3", "TR_GEN15", "HONLY_LR")), M); _paths(Us, d, "path_of")
    # RC24 Stage C matched constructions (incl. the secondary HT_PHYS = HA_TREND on HONLY paths, and controls) and Stage A matched
    for job, cons in (("c-match", ("HA_LEAN", "HONLY_LR", "HA_TREND", "HA_TREND_B1", "HA_TREND_B10", "PAC", "PAC_GEN")), ("a-match", ("HA_LEAN", "HONLY_LR", "M3", "M3_C1", "E1RAW", "E1CAL", "G3"))):
        UU = EV.load_units(OUT / job)
        for cond in (("STD", "BLOCK") if job == "c-match" else ("STD",)):
            Us = [u for u in UU if (u.get("block") is None) == (cond == "STD")]; E = {}
            for u in Us:
                bs = np.array([e["budget"] for e in u["evals"]], int)
                for c in cons:
                    E[(f"{c}@{u['path_of']}", u["repeat"], u["fold"])] = (bs, np.array([np.asarray(e["p"][c], float) for e in u["evals"]]), np.asarray(u["test_ids"], str))
            d = base / f"rc24_{job}_{cond.lower()}"; acc[d.name] = _export(d, E, M); _paths(Us, d, "path_of")
    (base / "EXPORTS_ACCEPTANCE.json").write_text(json.dumps(acc, indent=1), encoding="utf-8"); print(json.dumps(acc, indent=1)); return acc


if __name__ == "__main__":
    RC.limit_threads(1); {"final": final, "exports": exports}[sys.argv[1]]()
