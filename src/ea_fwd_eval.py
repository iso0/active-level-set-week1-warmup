"""EA forward validation evaluation and verdicts (PROTOCOL_EA_VALIDATION.md section 4; frozen before any fresh run).
Systems (keys): C1_own, A_own (own margin paths), C1_on_A, D_on_A, E_on_A (on A's path), A_on_C1 (on C1's path; decomposition).
Primary pair: C1_own vs A_own (STD, individual learners, 40 clusters). Every verdict separate; no combined winner.
    python -m src.ea_fwd_eval
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import src.ea_cand as CA
import src.ea_cand_eval as CE
import src.el_eval as EV
import src.rc18_common as RC
import src.rc19_pool as P

OUT = CA.OUT / "validation"
UNITS = CA.OUT / "ea-fwd" / "units"
REF = "A_own"; PRIMARY = "C1_own"; SECONDARY = ("C1_on_A", "D_on_A", "E_on_A")
LATE = tuple(range(28, 61))


def load(cond):
    E, CPU, CHK = {}, [], []
    d = UNITS
    for fL in sorted(d.glob(f"{cond}__*__L.json.gz")):
        uL = RC.read_json_gz(fL); uX = RC.read_json_gz(d / fL.name.replace("__L.json.gz", "__X.json.gz")); c, l = int(uL["repeat"]), int(uL["fold"]); ids = np.asarray(uL["test_ids"], str)
        if list(uX["test_ids"]) != list(ids) or uL["paid_ids"][:8] != uX["paid_ids"][:8]:
            raise RuntimeError(f"{fL.name}: paths do not share the test set / startup")
        E[("A_own", cond, c, l)] = (np.array([e["budget"] for e in uL["evals"]], int), np.array([e["p"]["HA_LEAN"] for e in uL["evals"]], float), ids)
        for k in ("C1", "D", "E"):
            E[(f"{k}_on_A", cond, c, l)] = (np.array([e["budget"] for e in uL["cross"]], int), np.array([e["p"][k] for e in uL["cross"]], float), ids)
        E[("C1_own", cond, c, l)] = (np.array([e["budget"] for e in uX["evals"]], int), np.array([e["p"]["C1"] for e in uX["evals"]], float), ids)
        E[("A_on_C1", cond, c, l)] = (np.array([e["budget"] for e in uX["cross"]], int), np.array([e["p"]["A"] for e in uX["cross"]], float), ids)
        s = range(52)
        CPU.append({"cluster": c, "learner": l, "A_own": float(np.mean([uL["evals"][i]["cpu_s"] for i in s])), "C1_own": float(np.mean([uX["evals"][i]["cpu_s"] for i in s])),
                    "C1_on_A": float(np.mean([uL["evals"][i]["cpu_s"] + uL["cross"][i]["cpu_C1"] for i in s])),
                    "D_on_A": float(np.mean([uL["evals"][i]["cpu_s"] + uL["cross"][i]["cpu_T"] for i in s])), "E_on_A": float(np.mean([uL["evals"][i]["cpu_s"] + uL["cross"][i]["cpu_T"] for i in s]))})
        CHK.append({"cluster": c, "learner": l, "pL_vs_own_A": uL["check_pL_vs_own_A_maxabs"]})
    for k, v in E.items():
        if not np.array_equal(v[0], np.arange(8, 61)):
            raise RuntimeError(f"{k}: budgets are not 8..60")
    return E, pd.DataFrame(CPU), pd.DataFrame(CHK)


def status_saving(r):
    if r["lcb"] > 0:
        return "SAVING_SHOWN" + ("+PRACTICAL" if r["mean"] >= 1.0 else "")
    return "NOT_WORSE" if r["lcb"] > -1.0 else "NOT_SHOWN"


def verdicts(con, cpu, x, a=REF):
    e = con["dBA_B8_B24"]; s93 = con["rms_saving_0.93"]; s95 = con["rms_saving_0.95"]; late = con["dBA_B28_B60"]
    rel = bool(con["d_attain_0.95"]["lcb"] >= -0.05 and con["d_kept_0.95"]["lcb"] >= -0.05)
    ratio = float(cpu[x].mean() / cpu[a].mean())
    harm = {"dLL_B8_B60": con["dll_B8_B60"]["mean"], "dBrier_B8_B60": con["dbrier_B8_B60"]["mean"], "cpu_ratio": ratio,
            "LL_ok": bool(con["dll_B8_B60"]["mean"] <= 0.030), "Brier_ok": bool(con["dbrier_B8_B60"]["mean"] <= 0.010), "CPU_ok": bool(ratio <= 3.0)}
    return {"system": x, "against": a,
            "V_EARLY": ("EARLY_GAIN_SHOWN" + ("+PRACTICAL" if e["mean"] >= 0.003 else "")) if e["lcb"] > 0 else "NOT_SHOWN", "early": e,
            "V_093": status_saving(s93), "saving_093": s93, "saving_090": con["rms_saving_0.9"], "attain_table_093": con["attain_table_0.93"], "cum_attain_093": con["cum_attain_0.93"],
            "V_095": "RELIABLE" if rel else "NOT_RELIABLE", "d_attain_095": con["d_attain_0.95"], "d_kept_095": con["d_kept_0.95"], "d_sustained_095": con["d_sustained_0.95"],
            "saving_095_status": status_saving(s95), "saving_095": s95, "attain_table_095": con["attain_table_0.95"], "cum_attain_095": con["cum_attain_0.95"],
            "LATE": "LOSS_SHOWN" if late["ucb"] < 0 else "NO_LOSS_SHOWN", "late": late, "harm": harm}


def evaluate(cond, M):
    E, CPU, CHK = load(cond); D = EV.learner_rows(E, M.y); G = EV.pooled_rows(E, M.y)
    Ai = EV.aulc(D, ("system", "cluster", "learner")); Ap = EV.aulc(G, ("system", "cluster"))
    late = D[D.budget.isin(LATE)].groupby(["system", "cluster", "learner"])[["BA", "sens", "spec", "ll", "brier"]].mean().reset_index(); late["window"] = "B28_B60"
    Ai2 = pd.concat([Ai, late], ignore_index=True); Ei = EV.endpoints(D, ("system", "cluster", "learner")); Ep = EV.endpoints(G, ("system", "cluster"))
    S = EV.summary_by_system(D, Ai, Ei, G, Ap, Ep); Su = CE.sustained(D, ("system", "cluster", "learner"))
    con = {}
    pairs = [(PRIMARY, REF)] + [(x, REF) for x in SECONDARY] + [("C1_own", "A_on_C1"), ("A_on_C1", "A_own"), ("C1_own", "C1_on_A"), ("C1_own", "D_on_A"), ("C1_own", "E_on_A")]
    for x, a in pairs:
        c = EV.contrast_table(Ai, Ei, x, a); c["dBA_B28_B60"] = EV.cluster_diff(Ai2[Ai2.window == "B28_B60"], x, a, "BA")
        for tau in (0.90, 0.93, 0.95):
            T = Su[Su.target == tau].copy(); T["s"] = T.sustained.astype(float); c[f"d_sustained_{tau}"] = EV.cluster_diff(T, x, a, "s")
        con[f"{x}-{a}"] = c
    pooled = {x: {w: EV.cluster_diff(Ap[Ap.window == w], x, REF, "BA", key=("cluster",)) for w in EV.WIN} for x in (PRIMARY,) + SECONDARY}
    reg = None
    if cond != "STD":
        Td = Ai[Ai.window == "B8_B60"].dropna(subset=["BA"]); R = Td.groupby(["system", "cluster"]).BA.mean()
        reg = {x: {**EV.tstats((R.loc[x] - R.loc[REF]).dropna().values)} for x in (PRIMARY,) + SECONDARY}
        for x in reg:
            reg[x]["warning"] = bool(np.isfinite(reg[x]["lcb"]) and reg[x]["lcb"] < -0.02)
    return {"E": E, "D": D, "G": G, "Ai": Ai2, "Ap": Ap, "Ei": Ei, "Ep": Ep, "S": S, "Su": Su, "con": con, "pooled": pooled, "reg": reg, "CPU": CPU, "CHK": CHK,
            "bat": {x: EV.ba_at(D, x, REF) for x in (PRIMARY,) + SECONDARY}}


def run():
    OUT.mkdir(parents=True, exist_ok=True); M = P.manifest(); res = {}; R = {}
    for cond in ("STD", "K5", "K4"):
        R[cond] = r = evaluate(cond, M)
        for nm in ("D", "G", "Ai", "Ap", "Ei", "Ep", "S", "Su", "CPU", "CHK"):
            r[nm].to_csv(OUT / f"{cond.lower()}_{nm.lower()}.csv.gz", index=False, compression="gzip")
        res[cond] = {"learners": int(r["D"][["cluster", "learner"]].drop_duplicates().shape[0]), "clusters": int(r["D"].cluster.nunique()), "summary": r["S"].round(4).to_dict(orient="records"),
                     "sustained": r["Su"].groupby(["system", "target"]).sustained.agg(lambda s: f"{int(s.sum())}/{len(s)}").unstack().to_dict(),
                     "late_window_means": r["Ai"][r["Ai"].window == "B28_B60"].groupby("system")[["BA", "ll", "brier"]].mean().round(4).to_dict(),
                     "contrasts": r["con"], "pooled_vs_A": r["pooled"], "per_region_vs_A": r["reg"], "BA_at_budgets_vs_A": r["bat"],
                     "cpu_mean_per_step": r["CPU"].drop(columns=["cluster", "learner"]).mean().round(4).to_dict(), "check_pL_vs_own_A_maxabs": float(r["CHK"].pL_vs_own_A.max())}
    std = R["STD"]
    res["verdicts"] = {"primary": verdicts(std["con"][f"{PRIMARY}-{REF}"], std["CPU"], PRIMARY),
                       "secondary": {x: verdicts(std["con"][f"{x}-{REF}"], std["CPU"], x) for x in SECONDARY},
                       "geometry_warnings": {c: {x: R[c]["reg"][x]["warning"] for x in R[c]["reg"]} for c in ("K5", "K4")}}
    (OUT / "EA_VALIDATION_DECISION.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); return res, R


if __name__ == "__main__":
    res, _ = run(); v = res["verdicts"]["primary"]
    print(json.dumps({k: v[k] for k in ("V_EARLY", "V_093", "V_095", "saving_095_status", "LATE", "harm")}, indent=1, default=float))
