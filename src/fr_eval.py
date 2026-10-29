"""FR fresh-test evaluation, verdicts and use decision (PROTOCOL_FR_FRESH.md; frozen with the candidate before any fresh result).
EVALUATOR ONLY: test labels and evaluator descriptors (hard group, corner) are read here and nowhere else.
Systems (keys)
  GATE      GATE + margin own path (src.fr_gate.run_gate);  on GATE's path: C1_on_G, A_on_G, AVG_on_G (identical paid data)
  C1        C1 + margin own path (src.ea_fwd.unit_X, unchanged);  on it: A_on_C1
  A         HA_LEAN + margin own path (src.rc23_common.run_arm, unchanged);  on it: D_on_A = HA_TREND (ML-II), the registered strong alternative
Primary pair: GATE vs C1 (own paths, end to end). Individual learners; STD clusters = repeats; blocks: per region, clusters = startups.
    python -m src.fr_eval
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import src.ea_cand_eval as CE
import src.el_eval as EV
import src.rc18_common as RC
import src.rc19_pool as P

OUT = RC.ROOT / "outputs" / "research_campaign_20261029" / "opus_final_robustness"
UNITS = [OUT / "fr-fresh" / "units"]
EVAL = [OUT / "evaluation"]
WINS = {"B8_B24": tuple(range(8, 25)), "B25_B60": tuple(range(25, 61)), "B8_B60": tuple(range(8, 61))}
SYS = ("GATE", "C1", "A", "D_on_A", "AVG_on_G", "C1_on_G", "A_on_G", "A_on_C1")
CORNER = lambda M: ((M.VX > 0.85) & (M.P > 330)).to_numpy()


def load(cond):
    E, CPU, CHK, PAID = {}, [], [], []
    for fG in sorted(UNITS[0].glob(f"{cond}__*__G.json.gz")):
        uG = RC.read_json_gz(fG); uX = RC.read_json_gz(UNITS[0] / fG.name.replace("__G.json.gz", "__X.json.gz")); uL = RC.read_json_gz(UNITS[0] / fG.name.replace("__G.json.gz", "__L.json.gz"))
        c, l = int(uG["repeat"]), int(uG["fold"]); ids = np.asarray(uG["test_ids"], str)
        if list(uX["test_ids"]) != list(ids) or list(uL["test_ids"]) != list(ids) or not (uG["paid_ids"][:8] == uX["paid_ids"][:8] == uL["paid_ids"][:8]):
            raise RuntimeError(f"{fG.name}: the three paths do not share the test set / startup")
        bs = lambda ev: np.array([e["budget"] for e in ev], int)
        for k in ("GATE", "C1", "A", "AVG"):
            E[("GATE" if k == "GATE" else f"{k}_on_G", cond, c, l)] = (bs(uG["evals"]), np.array([e["p"][k] for e in uG["evals"]], float), ids)
        E[("C1", cond, c, l)] = (bs(uX["evals"]), np.array([e["p"]["C1"] for e in uX["evals"]], float), ids)
        E[("A_on_C1", cond, c, l)] = (bs(uX["cross"]), np.array([e["p"]["A"] for e in uX["cross"]], float), ids)
        E[("A", cond, c, l)] = (bs(uL["evals"]), np.array([e["p"]["HA_LEAN"] for e in uL["evals"]], float), ids)
        E[("D_on_A", cond, c, l)] = (bs(uL["cross"]), np.array([e["p"]["D"] for e in uL["cross"]], float), ids)
        s = range(52)
        CPU.append({"cluster": c, "learner": l, "GATE_step": float(np.mean([uG["evals"][i]["cpu_s"] for i in s])), "GATE_gate_share": float(np.sum([uG["evals"][i]["cpu_gate_s"] for i in s]) / max(1e-9, np.sum([uG["evals"][i]["cpu_s"] for i in s]))),
                    "C1_step": float(np.mean([uX["evals"][i]["cpu_s"] for i in s])), "A_step": float(np.mean([uL["evals"][i]["cpu_s"] for i in s])),
                    "D_extra_step": float(np.mean([uL["cross"][i]["cpu_D"] for i in s])), "unit_cpu_G": uG["cpu_s"], "unit_cpu_X": uX["cpu_s"], "unit_cpu_L": uL["cpu_s"]})
        CHK.append({"cluster": c, "learner": l, "pL_vs_own_A": uL["check_pL_vs_own_A_maxabs"], "GATE_vs_C1_on_G_b_lt_16": float(max(np.max(np.abs(np.asarray(e["p"]["GATE"], float) - np.asarray(e["p"]["C1"], float))) for e in uG["evals"] if e["budget"] < 16)),
                    "gate_fits": sum(g["status"] == "fit" for g in uG["gates"]), "gate_insufficient": sum(g["status"] != "fit" for g in uG["gates"]),
                    "one_class_start": bool(uG["evals"][0]["one_class"]), "one_class_steps_G": int(sum(e["one_class"] for e in uG["evals"])), "w_test_mean_b60": float(np.mean(uG["evals"][-1]["w_test"]))})
        un = set(uG["paid_ids"]) | set(uX["paid_ids"]) | set(uL["paid_ids"])
        PAID.append({"cluster": c, "learner": l, "GATE": len(uG["paid_ids"]), "C1": len(uX["paid_ids"]), "A": len(uL["paid_ids"]), "union": len(un),
                     "GATE_C1_shared": len(set(uG["paid_ids"]) & set(uX["paid_ids"])), "GATE_A_shared": len(set(uG["paid_ids"]) & set(uL["paid_ids"]))})
    for k, v in E.items():
        if not np.array_equal(v[0], np.arange(8, 61)):
            raise RuntimeError(f"{k}: budgets are not 8..60")
    return E, pd.DataFrame(CPU), pd.DataFrame(CHK), pd.DataFrame(PAID)


def aulc(D):
    out = []
    for wn, ws in WINS.items():
        a = D[D.budget.isin(ws)].groupby(["system", "cluster", "learner"])[["BA", "sens", "spec", "ll", "brier"]].mean().reset_index(); a["window"] = wn; out.append(a)
    return pd.concat(out, ignore_index=True)


def per_region(Ai_by_cond, x, a, win, col="BA"):
    """Blocks: per startup cluster the mean over its defined regions of x - a; K5 and K4 clusters pooled when both are given."""
    d = []
    for cond, Ai in Ai_by_cond.items():
        T = Ai[(Ai.window == win)].dropna(subset=[col]); R = T.groupby(["system", "cluster"])[col].mean()
        if x in R.index.get_level_values(0) and a in R.index.get_level_values(0):
            dd = (R.loc[x] - R.loc[a]).dropna(); d += list(dd.values)
    r = EV.tstats(np.asarray(d)); r.update(EV.boot(np.asarray(d))); r["clusters"] = len(d); return r


def hard(E, M):
    sk = M.shortK_NEW_original.astype(bool); cn = (M.source_batch == "NEW") & (M.y == 0); rows = []
    for (sy, cond, c, l), (bs, Pm, ids) in E.items():
        a = sk.reindex(ids).to_numpy(bool); z = cn.reindex(ids).to_numpy(bool); hat = np.asarray(Pm) >= 0.5
        for wn in ("B8_B60", "B25_B60"):
            j = np.isin(bs, WINS[wn])
            rows.append({"system": sy, "condition": cond, "cluster": c, "learner": l, "window": wn,
                         "shortK_NEW_recall": float(hat[j][:, a].mean()) if a.any() else np.nan, "NEW_cond_spec": float((~hat[j][:, z]).mean()) if z.any() else np.nan})
    return pd.DataFrame(rows)


def targets(Ei, Su, systems):
    rows = []
    for sy in systems:
        for tau in EV.TAUS:
            T = Ei[(Ei.system == sy) & (Ei.target == tau) & (Ei.defined == True)]; att = T.attained.astype(bool)  # noqa: E712
            S_ = Su[(Su.system == sy) & (Su.target == tau)]
            rows.append({"system": sy, "target": tau, "learners": len(T), "attained": int(att.sum()), "not_attained": int((~att).sum()),
                         "first_mean": float(T["first"][att].astype(float).mean()) if att.any() else np.nan,
                         "confirmed_b_mean": float(T.confirmed_b[att].astype(float).mean()) if att.any() else np.nan,
                         "spend_mean_attainers_incl_startup_and_confirmation": float(T.spend[att].astype(float).mean()) if att.any() else np.nan,
                         "spend_median_attainers": float(T.spend[att].astype(float).median()) if att.any() else np.nan,
                         "rms_horizon_60_not_a_cost": float(T.rms.mean()) if len(T) else np.nan,
                         "kept_BA60": int(T.kept.astype(bool).sum()), "lost_by_60": int(T.lost.astype(bool).sum()), "sustained_every_budget": int(S_.sustained.astype(bool).sum())})
    return pd.DataFrame(rows)


def run(job="fr-fresh", sub="evaluation"):
    UNITS[0] = OUT / job / "units"; EVAL[0] = OUT / sub
    RC.limit_threads(1); M = P.manifest(); R = {}; res = {"protocol": "PROTOCOL_FR_FRESH.md (frozen before any fresh result)", "evidence": "DEV-pool fresh splits / startups (same 541 runs; not external)"}
    for cond in ("STD", "K5", "K4"):
        E, CPU, CHK, PAID = load(cond); D = EV.learner_rows(E, M.y); Ai = aulc(D); Ei = EV.endpoints(D, ("system", "cluster", "learner")); Su = CE.sustained(D, ("system", "cluster", "learner"))
        R[cond] = {"E": E, "D": D, "Ai": Ai, "Ei": Ei, "Su": Su, "CPU": CPU, "CHK": CHK, "PAID": PAID, "H": hard(E, M)}
    S = R["STD"]; Ai = S["Ai"]; Ei = S["Ei"]
    pair = lambda x, a: {**EV.contrast_table(Ai[Ai.window != "B25_B60"], Ei, x, a), "dBA_B25_B60": EV.cluster_diff(Ai[Ai.window == "B25_B60"], x, a, "BA"),
                         **{f"d_sustained_{tau}": EV.cluster_diff(S["Su"][S["Su"].target == tau].assign(s=lambda t: t.sustained.astype(float)), x, a, "s") for tau in EV.TAUS}}
    con = {f"{x}-{a}": pair(x, a) for x, a in (("GATE", "C1"), ("GATE", "A"), ("C1", "A"), ("D_on_A", "C1"), ("D_on_A", "A"), ("GATE", "D_on_A"),
                                               ("GATE", "AVG_on_G"), ("GATE", "C1_on_G"), ("C1_on_G", "C1"), ("AVG_on_G", "C1"))}
    geo = {f"{x}-{a}|{w}": {"GEOMETRIC": per_region({"K5": R["K5"]["Ai"], "K4": R["K4"]["Ai"]}, x, a, w), "K5": per_region({"K5": R["K5"]["Ai"]}, x, a, w), "K4": per_region({"K4": R["K4"]["Ai"]}, x, a, w)}
           for x, a in (("GATE", "C1"), ("GATE", "A"), ("C1", "A"), ("D_on_A", "C1"), ("GATE", "AVG_on_G"), ("GATE", "C1_on_G"), ("AVG_on_G", "C1")) for w in ("B8_B24", "B25_B60", "B8_B60")}
    levels = {}
    for cond in ("STD", "K5", "K4"):
        A_ = R[cond]["Ai"]
        for w in WINS:
            T = A_[A_.window == w]
            levels[f"{cond}|{w}"] = {sy: {"BA": float(T[T.system == sy].groupby("cluster").BA.mean().mean()), "keyhole_recall": float(T[T.system == sy].groupby("cluster").sens.mean().mean()),
                                          "conduction_recall": float(T[T.system == sy].groupby("cluster").spec.mean().mean()), "logloss": float(T[T.system == sy].groupby("cluster").ll.mean().mean()),
                                          "brier": float(T[T.system == sy].groupby("cluster").brier.mean().mean())} for sy in SYS}
    G = {}
    for cond in ("K5", "K4"):
        Gp = EV.pooled_rows(R[cond]["E"], M.y); Ap = Gp[Gp.budget.isin(WINS["B8_B60"])].groupby(["system", "cluster"]).BA.mean()
        G[cond] = {sy: float(Ap.loc[sy].mean()) for sy in SYS}
        G[f"{cond}_GATE-C1"] = EV.tstats((Ap.loc["GATE"] - Ap.loc["C1"]).values)
    hardt = {}
    for cond in ("STD", "K5", "K4"):
        H = R[cond]["H"]
        for w in ("B8_B60", "B25_B60"):
            T = H[H.window == w]
            hardt[f"{cond}|{w}"] = {"means": {sy: {k: float(T[T.system == sy].groupby("cluster")[k].mean().mean()) for k in ("shortK_NEW_recall", "NEW_cond_spec")} for sy in ("GATE", "C1", "A", "D_on_A", "AVG_on_G")},
                                    "GATE-C1": {k: EV.cluster_diff(T, "GATE", "C1", k) for k in ("shortK_NEW_recall", "NEW_cond_spec")}}
    tt = targets(Ei, S["Su"], SYS)
    # ---------------------------------------------------------------- registered verdicts
    g = geo["GATE-C1|B8_B60"]; gg = g["GEOMETRIC"]; e = con["GATE-C1"]["dBA_B8_B24"]; c_ = con["GATE-C1"]
    V = {"V_GEO": ("GEO_GAIN_SHOWN+PRACTICAL" if gg["lcb"] > 0 and gg["mean"] >= 0.010 else "GEO_GAIN_SHOWN" if gg["lcb"] > 0 else "NOT_SHOWN"), "geo": gg,
         "V_EARLY": "EARLY_NONINFERIOR" if e["lcb"] > -0.003 else "EARLY_LOSS_NOT_EXCLUDED", "early": e}
    harm = {"late_B25_B60": c_["dBA_B25_B60"]["lcb"] >= -0.003, "keyhole_recall_B8_B60": c_["dsens_B8_B60"]["lcb"] >= -0.005, "conduction_recall_B8_B60": c_["dspec_B8_B60"]["lcb"] >= -0.005,
            "spend_0.9": c_["rms_saving_0.9"]["lcb"] >= -1.0, "spend_0.93": c_["rms_saving_0.93"]["lcb"] >= -1.0, "spend_0.95": c_["rms_saving_0.95"]["lcb"] >= -1.0,
            "attain_0.95": c_["d_attain_0.95"]["lcb"] >= -0.05, "kept_0.95": c_["d_kept_0.95"]["lcb"] >= -0.05,
            "no_K5_loss_shown": not (g["K5"]["ucb"] < 0), "no_K4_loss_shown": not (g["K4"]["ucb"] < 0)}
    V["harm"] = harm; V["harm_ok"] = bool(all(harm.values()))
    ctl_g = geo["GATE-AVG_on_G|B8_B60"]["GEOMETRIC"]; ctl_e = con["GATE-AVG_on_G"]["dBA_B8_B24"]
    V["control_local_rule_needed"] = bool((ctl_g["lcb"] > 0 or ctl_e["lcb"] > 0) and not (ctl_g["ucb"] < 0 or ctl_e["ucb"] < 0)); V["control"] = {"geometric_B8_B60": ctl_g, "STD_B8_B24": ctl_e}
    hk = hardt["STD|B8_B60"]["GATE-C1"]; sk_, cn_ = hk["shortK_NEW_recall"], hk["NEW_cond_spec"]
    V["hard_group_STD"] = ("IMPROVED_ONE_WITHOUT_LOSS_ON_OTHER" if ((sk_["lcb"] > 0 and not cn_["ucb"] < 0) or (cn_["lcb"] > 0 and not sk_["ucb"] < 0))
                           else "TRADE_OFF" if ((sk_["lcb"] > 0 and cn_["ucb"] < 0) or (cn_["lcb"] > 0 and sk_["ucb"] < 0)) else "NO_CHANGE_SHOWN")
    if V["V_GEO"] == "GEO_GAIN_SHOWN+PRACTICAL" and V["V_EARLY"] == "EARLY_NONINFERIOR" and V["harm_ok"]:
        use = "1_ADOPT_GATE_FOR_GEOMETRIC_ROBUSTNESS"
    elif V["V_GEO"].startswith("GEO_GAIN_SHOWN") and V["V_EARLY"] == "EARLY_NONINFERIOR":
        use = "2_GATE_EVIDENCE_FOR_BLOCK_EXTRAPOLATION_ONLY"
    else:
        use = "3_KEEP_C1_UNCHANGED"
    V["use_decision"] = use
    cpu = {c: R[c]["CPU"].drop(columns=["cluster", "learner"]).mean().round(4).to_dict() for c in R}
    paid = {c: R[c]["PAID"].drop(columns=["cluster", "learner"]).agg(["mean", "sum"]).round(2).to_dict() for c in R}
    chk = {c: {"pL_vs_own_A_max": float(R[c]["CHK"].pL_vs_own_A.max()), "GATE_eq_C1_below_16_max": float(R[c]["CHK"].GATE_vs_C1_on_G_b_lt_16.max()),
               "one_class_starts": int(R[c]["CHK"].one_class_start.sum()), "learners": int(len(R[c]["CHK"])), "gate_fits_mean": float(R[c]["CHK"].gate_fits.mean()),
               "gate_insufficient_mean": float(R[c]["CHK"].gate_insufficient.mean()), "w_test_mean_b60": float(R[c]["CHK"].w_test_mean_b60.mean())} for c in R}
    res.update({"verdicts": V, "contrasts_STD": con, "geometric": geo, "levels": levels, "pooled_blocks_B8_B60": G, "hard_group": hardt, "targets_STD": tt.round(3).to_dict(orient="records"),
                "cpu_mean": cpu, "simulations": paid, "checks": chk,
                "learners": {c: int(R[c]["CHK"].shape[0]) for c in R}, "clusters": {c: int(R[c]["CHK"].cluster.nunique()) for c in R}})
    EVAL[0].mkdir(parents=True, exist_ok=True)
    for cond in R:
        for nm in ("D", "Ai", "Ei", "Su", "CPU", "CHK", "PAID", "H"):
            R[cond][nm].to_csv(EVAL[0] / f"{cond.lower()}_{nm.lower()}.csv.gz", index=False, compression="gzip")
    tt.to_csv(EVAL[0] / "std_targets.csv", index=False)
    (EVAL[0] / "FR_DECISION.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); return res, R


if __name__ == "__main__":
    import sys
    res, _ = run(*sys.argv[1:3]) if len(sys.argv) > 2 else run(); v = res["verdicts"]
    print(json.dumps({k: v[k] for k in ("V_GEO", "geo", "V_EARLY", "early", "harm", "harm_ok", "control_local_rule_needed", "hard_group_STD", "use_decision")}, indent=1, default=float))
