"""C1S fresh-test evaluation and registered decisions (PROTOCOL_C1S.md sections 3-6; frozen before any fresh result).

Systems (all from the fresh units; test outcomes read only here):
  C1        unchanged C1 + margin, own path (the method)          A   HA_LEAN + margin, own path (historical reference)
  AVG4      candidate: C1's own probabilities, b <= 24 unchanged, b >= 25 mean over the last 4 budgets (src.c1s_dev.variant)
  EVERY4    simple control "update less often" (b >= 24: probabilities of the last multiple-of-4 budget)
  FREEZE24  simple control "freeze at a fixed budget" (b >= 24: probabilities of budget 24)
  C1_on_A   C1 on HA_LEAN's path (decomposition only)
AVG4 / EVERY4 / FREEZE24 open exactly C1's runs: equal simulations, no extra query.
Primary: dS95 = S95(AVG4) - S95(C1), S95 = mean over b = 24..60 of max(0, 0.95 - BA(b)), individual learners, repeat clusters,
one-sided 95 % t bounds (+ 10,000-resample cluster bootstrap check). Reuses src.c1c_eval / src.el_eval / src.ea_cand_eval unchanged.
    python -m src.c1s_eval all
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.c1c_eval as CV
import src.c1s_dev as DV
import src.c1s_diag as DG
import src.c1s_fwd as FW
import src.el_eval as EV
import src.rc18_common as RC
import src.rc19_pool as P

OUT = FW.OUT / "evaluation"
SYS = ("C1", "A", "AVG4", "EVERY4", "FREEZE24", "C1_on_A")
PRACTICAL_S95 = 0.0005; EARLY_MARGIN = 0.003; RECALL_LIMIT = 0.005; LATE_LIMIT = 0.003; SPEND_LIMIT = 1.0; RELIABLE_LIMIT = 0.05
CORNER = lambda M: ((M.VX > 0.85) & (M.P > 330)).to_numpy()


def build(units_dir, cond):
    E0, CPU, CHK = CV.load(units_dir, cond); E = {}
    for (sy, c_, r, f), v in E0.items():
        if sy == "C1_own":
            bs, Pm, ids = v; E[("C1", c_, r, f)] = v
            for k in ("AVG4", "EVERY4", "FREEZE24"):
                E[(k, c_, r, f)] = (bs, DV.variant(bs, Pm, k), ids)
        elif sy == "A_own":
            E[("A", c_, r, f)] = v
        elif sy == "C1_on_A":
            E[("C1_on_A", c_, r, f)] = v
    return E, CPU, CHK


def stability(D):
    """Per learner: S95, S93, level / fluctuation parts of S95, total variation and max drawdown over B24-B60."""
    T = D[(D.budget >= 24) & (D.budget <= 60)].sort_values("budget"); rows = []
    for (sy, c, l), g in T.groupby(["system", "cluster", "learner"]):
        ba = g.BA.to_numpy(float)
        if not np.isfinite(ba).all():
            continue
        s95 = float(np.mean(np.maximum(0, 0.95 - ba))); lev = float(max(0.0, 0.95 - ba.mean()))
        rows.append({"system": sy, "cluster": c, "learner": l, "S95": s95, "S93": float(np.mean(np.maximum(0, 0.93 - ba))), "S95_level": lev, "S95_fluct": s95 - lev,
                     "TV": float(np.abs(np.diff(ba)).sum()), "drawdown": float(np.max(np.maximum.accumulate(ba) - ba)), "n_reg": int((np.diff(ba) < 0).sum())})
    return pd.DataFrame(rows)


def supplementary(D):
    T = D[(D.budget >= 24) & (D.budget <= 60)].copy(); fp = T.n0 - T.tn; fn = T.n1 - T.tp
    T["precision"] = np.where(T.tp + fp > 0, T.tp / (T.tp + fp).clip(lower=1), np.nan); r = T.sens
    T["F2"] = np.where((4 * T.precision + r) > 0, 5 * T.precision * r / (4 * T.precision + r), np.nan); T["FN"] = fn; T["FP"] = fp
    return T.groupby(["system", "cluster", "learner"])[["precision", "F2", "FN", "FP", "ll", "brier"]].mean().reset_index()


def anatomy(E, M):
    """Mechanism replication on the fresh data: flips per step B24-B60, harmful / helpful, share of regression steps with <= 2 harmful flips,
    corner share of flips (evaluator-only descriptor)."""
    y_all = M.y.astype(int); cr = pd.Series(CORNER(M), index=M.index); out = {}
    for sy in ("C1", "AVG4", "A"):
        fl_n, harm, helpf, reg, reg_le2, corner_fl, steps = 0, 0, 0, 0, 0, 0, 0
        for (s, cond, c, l), (bs, Pm, ids) in E.items():
            if s != sy:
                continue
            y = y_all.reindex(ids).to_numpy(int); c_ = cr.reindex(ids).to_numpy(bool); ba, hat = DG.ba_curve(np.asarray(Pm, float), y)
            corr = hat == (y == 1)[None, :]
            for j in range(len(bs) - 1):
                if bs[j] < 24:
                    continue
                f = hat[j + 1] != hat[j]; h = (corr[j] & ~corr[j + 1]).sum(); hp = (~corr[j] & corr[j + 1]).sum(); d = ba[j + 1] - ba[j]
                steps += 1; fl_n += int(f.sum()); harm += int(h); helpf += int(hp); corner_fl += int((f & c_).sum())
                if d < 0:
                    reg += 1; reg_le2 += int(h <= 2)
        out[sy] = {"steps": steps, "flips_per_step": fl_n / max(1, steps), "harmful_per_step": harm / max(1, steps), "helpful_per_step": helpf / max(1, steps),
                   "regression_share": reg / max(1, steps), "regression_steps_le2_harmful": reg_le2 / max(1, reg), "corner_share_of_flips": corner_fl / max(1, fl_n)}
    return out


def hard(E, M):
    """Evaluator-only hard group (EA robustness): B24-B60 mean recall of short-Keyhole NEW test runs and specificity on NEW conduction test runs."""
    sk = M.shortK_NEW_original.astype(bool); cn = (M.source_batch == "NEW") & (M.y == 0); rows = []
    for (sy, cond, c, l), (bs, Pm, ids) in E.items():
        m = np.asarray(bs) >= 24; hat = np.asarray(Pm)[m] >= 0.5; a = sk.reindex(ids).to_numpy(bool); b = cn.reindex(ids).to_numpy(bool)
        rows.append({"system": sy, "cluster": c, "learner": l, "shortK_NEW_recall": float(hat[:, a].mean()) if a.any() else np.nan,
                     "NEW_cond_spec": float((~hat[:, b]).mean()) if b.any() else np.nan})
    return pd.DataFrame(rows)


def verdicts(con, sv, sup):
    s = sv["dS95"]; e = con["dBA_B8_B24"]; late = sv["dBA_B24_B60"]
    stab = ("STABILITY_GAIN_SHOWN" + ("+PRACTICAL" if s["mean"] <= -PRACTICAL_S95 else "")) if s["ucb"] < 0 else ("STABILITY_LOSS_SHOWN" if s["lcb"] > 0 else "NOT_SHOWN")
    sav = {tau: CV.FE.status_saving(con[f"rms_saving_{tau}"]) for tau in (0.9, 0.93, 0.95)}
    harm = {"keyhole_recall_B24_B60_ok": bool(sv["dsens_B24_B60"]["lcb"] >= -RECALL_LIMIT), "conduction_recall_B24_B60_ok": bool(sv["dspec_B24_B60"]["lcb"] >= -RECALL_LIMIT),
            "late_BA_B24_B60_ok": bool(late["lcb"] >= -LATE_LIMIT), "spend_ok": {str(t): bool(con[f"rms_saving_{t}"]["lcb"] >= -SPEND_LIMIT) for t in (0.9, 0.93, 0.95)},
            "attain_095_ok": bool(con["d_attain_0.95"]["lcb"] >= -RELIABLE_LIMIT), "kept_095_ok": bool(con["d_kept_0.95"]["lcb"] >= -RELIABLE_LIMIT)}
    harm["all_ok"] = bool(harm["keyhole_recall_B24_B60_ok"] and harm["conduction_recall_B24_B60_ok"] and harm["late_BA_B24_B60_ok"] and all(harm["spend_ok"].values())
                          and harm["attain_095_ok"] and harm["kept_095_ok"])
    sus = {str(t): ("SUSTAIN_GAIN_SHOWN" if con[f"d_sustained_{t}"]["lcb"] > 0 else ("SUSTAIN_LOSS_SHOWN" if con[f"d_sustained_{t}"]["ucb"] < 0 else "NOT_SHOWN")) for t in (0.93, 0.95)}
    early = "EARLY_NONINFERIOR" if e["lcb"] > -EARLY_MARGIN else "EARLY_LOSS_NOT_EXCLUDED"
    return {"STABILITY": stab, "dS95": s, "EARLY": early, "early": e, "SAVING": sav, "SUSTAINED": sus, "HARM": harm}


def use_decision(v):
    if v["STABILITY"].endswith("+PRACTICAL") and v["HARM"]["all_ok"]:
        return "ADOPT_AVG4_FOR_LATE_USE"
    if v["SUSTAINED"]["0.95"] == "SUSTAIN_GAIN_SHOWN" and v["HARM"]["all_ok"]:
        return "AVG4_ONLY_FOR_HOLD_THE_TARGET_USE"
    return "KEEP_C1_UNCHANGED"


def evaluate(units_dir, cond, M):
    E, CPU, CHK = build(units_dir, cond); t = CV.tables(E, M)
    late = t["D"][t["D"].budget.isin(range(24, 61))].groupby(["system", "cluster", "learner"])[["BA", "sens", "spec", "ll", "brier"]].mean().reset_index(); late["window"] = "B24_B60"
    St = stability(t["D"]); Sp = supplementary(t["D"]); res = {"condition": cond, "clusters": int(t["D"].cluster.nunique()), "learners": int(t["D"][["cluster", "learner"]].drop_duplicates().shape[0])}
    pairs = [("AVG4", "C1"), ("EVERY4", "C1"), ("FREEZE24", "C1"), ("A", "C1"), ("C1", "A"), ("AVG4", "A"), ("AVG4", "EVERY4"), ("C1_on_A", "A")]
    con, stv = {}, {}
    for x, a in pairs:
        con[f"{x}-{a}"] = CV.contrast(t, x, a)
        r = {}
        for col in ("S95", "S93", "S95_level", "S95_fluct", "TV", "drawdown", "n_reg"):
            r[f"d{col}"] = EV.cluster_diff(St, x, a, col)
        for col in ("BA", "sens", "spec", "ll", "brier"):
            r[f"d{col}_B24_B60"] = EV.cluster_diff(late, x, a, col)
        for col in ("precision", "F2", "FN", "FP"):
            r[f"d{col}_B24_B60"] = EV.cluster_diff(Sp, x, a, col)
        stv[f"{x}-{a}"] = r
    res["contrasts"] = con; res["stability_contrasts"] = stv
    res["verdicts_primary"] = verdicts(con["AVG4-C1"], stv["AVG4-C1"], Sp); res["use_decision"] = use_decision(res["verdicts_primary"])
    res["verdicts_controls"] = {k: verdicts(con[f"{k}-C1"], stv[f"{k}-C1"], Sp) for k in ("EVERY4", "FREEZE24")}
    res["early_identity_max_abs"] = float(np.max([np.max(np.abs(E[("AVG4",) + k[1:]][1][:17] - E[k][1][:17])) for k in E if k[0] == "C1"]))
    Gs = stability(t["G"].assign(learner=0)); res["pooled_dS95_AVG4_C1"] = EV.cluster_diff(Gs, "AVG4", "C1", "S95")
    H = hard(E, M); res["hard_group"] = {f"{x}-{a}": {c: EV.cluster_diff(H, x, a, c) for c in ("shortK_NEW_recall", "NEW_cond_spec")} for x, a in (("AVG4", "C1"), ("C1", "A"))}
    res["hard_group_means"] = H.groupby("system")[["shortK_NEW_recall", "NEW_cond_spec"]].mean().round(4).to_dict()
    res["means"] = {sy: {"S95": float(St[St.system == sy].S95.mean()), "S95_level": float(St[St.system == sy].S95_level.mean()), "S95_fluct": float(St[St.system == sy].S95_fluct.mean()),
                         "S93": float(St[St.system == sy].S93.mean()), "BA_B8_B24": float(t["Ai"][(t["Ai"].window == "B8_B24") & (t["Ai"].system == sy)].BA.mean()),
                         "BA_B8_B60": float(t["Ai"][(t["Ai"].window == "B8_B60") & (t["Ai"].system == sy)].BA.mean()), "BA_B24_B60": float(late[late.system == sy].BA.mean()),
                         "TV": float(St[St.system == sy].TV.mean())} for sy in SYS}
    res["target_table"] = CV.target_table(t, SYS).to_dict(orient="records"); res["recalls_at"] = CV.recalls_at(t["D"], SYS).to_dict(orient="records")
    res["second_class"] = CV.second_class(units_dir, cond)[1]; res["anatomy"] = anatomy(E, M)
    res["cpu_mean_per_step"] = CPU.drop(columns=["cluster", "learner"]).mean().round(4).to_dict(); res["check_pL_vs_own_A_maxabs"] = float(CHK.pL_vs_own_A.max())
    return res, t, St, Sp, late


def run():
    OUT.mkdir(parents=True, exist_ok=True); M = P.manifest(); R = {}
    for job, conds in (("c1s-main", ("STD",)), ("c1s-start", ("RAND8", "LOCAL8"))):
        for cond in conds:
            r, t, St, Sp, late = evaluate(FW.OUT / job / "units", cond, M); R[cond] = r
            pre = cond.lower()
            for nm in ("D", "Ai", "Ei", "Su"):
                t[nm].to_csv(OUT / f"{pre}_{nm.lower()}.csv.gz", index=False, compression="gzip")
            St.to_csv(OUT / f"{pre}_stability.csv.gz", index=False, compression="gzip"); Sp.to_csv(OUT / f"{pre}_supplementary.csv.gz", index=False, compression="gzip")
    v = {c: R[c]["verdicts_primary"] for c in ("RAND8", "LOCAL8")}
    R["startup_rule"] = {"S95_direction_consistent": bool(all(x["dS95"]["mean"] <= 0 for x in v.values())), "no_stability_loss_shown": bool(all(x["STABILITY"] != "STABILITY_LOSS_SHOWN" for x in v.values())),
                         "sustained_095_direction_consistent": bool(all(R[c]["contrasts"]["AVG4-C1"]["d_sustained_0.95"]["mean"] >= 0 for c in v)),
                         "harm_all_ok_each": {c: x["HARM"]["all_ok"] for c, x in v.items()}}
    R["utc"] = RC.utc(); (OUT / "C1S_DECISION.json").write_text(json.dumps(R, indent=1, default=float), encoding="utf-8"); return R


if __name__ == "__main__":
    r = run(); p = r["STD"]
    print(json.dumps({"use_decision": p["use_decision"], **{k: p["verdicts_primary"][k] for k in ("STABILITY", "EARLY", "SAVING", "SUSTAINED")}, "harm_all_ok": p["verdicts_primary"]["HARM"]["all_ok"]}, indent=1, default=float))
