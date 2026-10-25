"""EL study FINAL evaluation and decision (PROTOCOL_EL_OBJECTIVES.md section 9, frozen with PROTOCOL_EL_FINAL.md before any forward run).
Systems from the forward units (src.el_final): path L -> A (own HA_LEAN) and D (HA_TREND on the path); path T -> B (own HA_TREND) and
C (HA_LEAN on the path). Primary: candidate X = D against A on STD (40 repeat clusters, 200 individual learners).
Rule (verbatim from section 9):
  E1 early      dBA-AULC B8-B24 (X - A) one-sided 95 % LCB > 0                                          -> EARLY GAIN SHOWN
  E2 savings    restricted-mean saving RMS_A - RMS_X, tau = 0.93 and 0.95: LCB > 0 -> SAVING SHOWN; LCB > -1.0 -> NOT WORSE; else NOT SHOWN
  E3 reliability tau = 0.93 and 0.95: d attainment (X - A) LCB >= -0.05 and d kept (X - A) LCB >= -0.05
  E4 guardrails dLL B8-B60 <= +0.030, dBrier B8-B60 <= +0.010 (point estimates), mean decision CPU per step <= 3 x A's
  verdict       SAVINGS_SHOWN / PARTIAL_SAVINGS / EARLY_ONLY / NOT_ADOPTED; the same rule for B and C against A (secondary)
  robustness    warning if X's per-region BA-AULC B8-B60 has a one-sided 95 % LCB below -0.02 against A in K5 or K4 (not in the verdict)
    python -m src.el_decide
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import src.el_eval as EV
import src.rc18_common as RC
import src.rc19_pool as P

OUT = RC.ROOT / "outputs" / "research_campaign_20261024" / "opus_early_learning"
FIN = OUT / "final"
CAND = "D"; REF = "A"
D_NW = -1.0; D_REL = -0.05; G_LL = 0.030; G_BR = 0.010; G_CPU = 3.0; W_REG = -0.02


def load_units(cond):
    E, CPU, PATHS, CHK = {}, [], [], []
    d = OUT / "el-fwd" / "units"
    for fL in sorted(d.glob(f"{cond}__*__L.json.gz")):
        uL = RC.read_json_gz(fL); fT = d / fL.name.replace("__L.json.gz", "__T.json.gz"); uT = RC.read_json_gz(fT)
        c, l = int(uL["repeat"]), int(uL["fold"]); ids = np.asarray(uL["test_ids"], str)
        if list(uT["test_ids"]) != list(ids) or uL["paid_ids"][:8] != uT["paid_ids"][:8]:
            raise RuntimeError(f"{fL.name}: test sets or startups differ between the two paths")
        for sy, ev, key in (("A", uL["evals"], "HA_LEAN"), ("D", uL["cross"]["evals"], "HA_TREND"), ("B", uT["evals"], "HA_TREND"), ("C", uT["cross"]["evals"], "HA_LEAN")):
            bs = np.array([e["budget"] for e in ev], int)
            if not np.array_equal(bs, np.arange(8, 61)):
                raise RuntimeError(f"{fL.name} {sy}: budgets are not 8..60")
            E[(sy, cond, c, l)] = (bs, np.array([e["p"][key] for e in ev], float), ids)
        CHK.append({"cluster": c, "learner": l, "C8_equals_A8": float(np.max(np.abs(np.asarray(uT["cross"]["evals"][0]["p"]["HA_LEAN"], float) - np.asarray(uL["evals"][0]["p"]["HA_LEAN"], float)))),
                    "D8_equals_B8": float(np.max(np.abs(np.asarray(uL["cross"]["evals"][0]["p"]["HA_TREND"], float) - np.asarray(uT["evals"][0]["p"]["HA_TREND"], float))))})
        sel = range(52)                                                           # steps b = 8..59 (b = 60 ends the path)
        sL = [uL["evals"][i]["cpu_s"] for i in sel]; sT = [uT["evals"][i]["cpu_s"] for i in sel]; pT = [uL["cross"]["evals"][i]["cpu_s"] for i in sel]; pL = [uT["cross"]["evals"][i]["cpu_s"] for i in sel]
        CPU.append({"cluster": c, "learner": l, "A": float(np.mean(sL)), "B": float(np.mean(sT)), "C": float(np.mean(sT) + np.mean(pL)), "D": float(np.mean(sL) + np.mean(pT))})
        for nm, u in (("HA_LEAN-selected", uL), ("HA_TREND-selected", uT)):
            hows = [e.get("how") for e in u["evals"]]
            for q, s in enumerate(u["paid_ids"][:60], 1):
                PATHS.append({"path": nm, "systems": "A,D" if nm.startswith("HA_LEAN") else "B,C", "condition": cond, "cluster": c, "learner": l, "query": q, "sim_id": s,
                              "rule": "startup" if q <= 8 else (hows[q - 9] or "margin")})
    return E, pd.DataFrame(CPU), pd.DataFrame(PATHS), pd.DataFrame(CHK)


def verdict(con, cpu, x, a=REF):
    e1 = con["dBA_B8_B24"]["lcb"] > 0
    e2 = {}
    for tau in (0.93, 0.95):
        r = con[f"rms_saving_{tau}"]; e2[tau] = "SAVING_SHOWN" if r["lcb"] > 0 else ("NOT_WORSE" if r["lcb"] > D_NW else "NOT_SHOWN")
    e3 = {tau: bool(con[f"d_attain_{tau}"]["lcb"] >= D_REL and con[f"d_kept_{tau}"]["lcb"] >= D_REL) for tau in (0.93, 0.95)}
    ratio = float(cpu[x].mean() / cpu[a].mean())
    e4 = {"dLL_B8_B60": con["dll_B8_B60"]["mean"], "dBrier_B8_B60": con["dbrier_B8_B60"]["mean"], "cpu_ratio": ratio,
          "ok": bool(con["dll_B8_B60"]["mean"] <= G_LL and con["dbrier_B8_B60"]["mean"] <= G_BR and ratio <= G_CPU)}
    ok_nw = all(v != "NOT_SHOWN" for v in e2.values()); n_sav = sum(v == "SAVING_SHOWN" for v in e2.values())
    if e1 and ok_nw and all(e3.values()) and e4["ok"]:
        v = "SAVINGS_SHOWN" if n_sav == 2 else ("PARTIAL_SAVINGS" if n_sav == 1 else "EARLY_ONLY")
    else:
        v = "NOT_ADOPTED"
    return {"system": x, "against": a, "E1_early_gain_shown": bool(e1), "E1": con["dBA_B8_B24"], "E2": e2, "E2_values": {t: con[f"rms_saving_{t}"] for t in (0.93, 0.95)},
            "E3_reliability_not_worse": e3, "E3_values": {t: {"d_attain": con[f"d_attain_{t}"], "d_kept": con[f"d_kept_{t}"]} for t in (0.93, 0.95)}, "E4": e4, "verdict": v}


def region_warning(Ai, x, a=REF):
    out = {}
    T = Ai[(Ai.window == "B8_B60")].dropna(subset=["BA"]); R = T.groupby(["system", "cluster"]).BA.mean()
    d = (R.loc[x] - R.loc[a]).dropna(); s = EV.tstats(d.values); out = {**s, "warning": bool(np.isfinite(s["lcb"]) and s["lcb"] < W_REG)}
    return out


def evaluate(cond, M):
    E, CPU, PATHS, CHK = load_units(cond)
    D = EV.learner_rows(E, M.y); G = EV.pooled_rows(E, M.y)
    Ai = EV.aulc(D, ("system", "cluster", "learner")); Ap = EV.aulc(G, ("system", "cluster"))
    Ei = EV.endpoints(D, ("system", "cluster", "learner")); Ep = EV.endpoints(G, ("system", "cluster"))
    S = EV.summary_by_system(D, Ai, Ei, G, Ap, Ep)
    con = {x: EV.contrast_table(Ai, Ei, x, REF) for x in ("B", "C", "D")}
    return {"E": E, "CPU": CPU, "PATHS": PATHS, "CHK": CHK, "D": D, "G": G, "Ai": Ai, "Ap": Ap, "Ei": Ei, "Ep": Ep, "S": S, "con": con,
            "conB": {x: EV.contrast_table(Ai, Ei, x, "B") for x in ("C", "D")}, "bat": {x: EV.ba_at(D, x, REF) for x in ("B", "C", "D")}, "dec": EV.decomposition(Ai, Ei),
            "pooled_con": {x: {w: EV.cluster_diff(Ap[Ap.window == w], x, REF, "BA", key=("cluster",)) for w in EV.WIN} for x in ("B", "C", "D")}}


def run():
    FIN.mkdir(parents=True, exist_ok=True); M = P.manifest(); res = {}; R = {}
    for cond in ("STD", "K5", "K4"):
        R[cond] = r = evaluate(cond, M)
        for nm in ("D", "G", "Ai", "Ap", "Ei", "Ep", "S", "CPU", "CHK"):
            r[nm].to_csv(FIN / f"{cond.lower()}_{nm.lower()}.csv", index=False)
        res[cond] = {"learners": int(r["D"][["cluster", "learner"]].drop_duplicates().shape[0]), "clusters": int(r["D"].cluster.nunique()),
                     "summary": r["S"].round(4).to_dict(orient="records"), "contrasts_vs_A": r["con"], "contrasts_vs_B": r["conB"], "BA_at_budgets_vs_A": r["bat"],
                     "pooled_vs_A": r["pooled_con"], "decomposition": r["dec"], "cpu_mean_per_step": r["CPU"][["A", "B", "C", "D"]].mean().round(4).to_dict(),
                     "checks": {"C8_equals_A8_maxabs": float(r["CHK"].C8_equals_A8.max()), "D8_equals_B8_maxabs": float(r["CHK"].D8_equals_B8.max())}}
    std = R["STD"]
    res["decision"] = {"primary": verdict(std["con"]["D"], std["CPU"], "D"), "secondary": {x: verdict(std["con"][x], std["CPU"], x) for x in ("B", "C")},
                       "robustness_warning": {c: {x: region_warning(R[c]["Ai"], x) for x in ("B", "C", "D")} for c in ("K5", "K4")}}
    (FIN / "FINAL_DECISION.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return res, R


if __name__ == "__main__":
    res, _ = run(); print(json.dumps(res["decision"]["primary"], indent=1, default=float)[:3000])
