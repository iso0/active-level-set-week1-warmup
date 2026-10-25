"""EL study DEV stage analysis (PROTOCOL_EL_OBJECTIVES.md section 7): A, B (recorded own paths), C (el-cross), D (existing matched
records + el-cross missing budgets) at every budget 8..60; individual-learner primary, pooled beside; 2x2 decomposition; the
registered candidate rule. DEV evidence for mechanism and candidate choice only.
    python -m src.el_dev
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import src.el_cross as X
import src.el_eval as EV
import src.rc18_common as RC
import src.rc19_pool as P

OUT = X.OUT / "dev"
SYS = ("A", "B", "C", "D")


def load(cond):
    E, CPU, PATHS = {}, [], {}
    for (c, s), (reps, nf) in X.SOURCES.items():
        if c != cond:
            continue
        for r in reps:
            for f in range(1, nf + 1):
                fa, ka = X.own_path(c, r, f, "L"); fb, kb = X.own_path(c, r, f, "T"); A = RC.read_json_gz(fa); B = RC.read_json_gz(fb)
                Cu = RC.read_json_gz(X.OUT / "el-cross" / "units" / f"C__{c}__r{r}_f{f}.json.gz")
                fd, kd, every = X.existing_D(c, r, f); Dx = RC.read_json_gz(fd)
                dp = {e["budget"]: e["p"][kd] for e in Dx["evals"]}; dcpu = {}; dchk = (0.0, 0.0)
                if not every:
                    Du = RC.read_json_gz(X.OUT / "el-cross" / "units" / f"D__{c}__r{r}_f{f}.json.gz")
                    dchk = (Du["check_b12_vs_existing_maxabs"], Du["check_D8_equals_B8_maxabs"])
                    for e in Du["evals"]:
                        dcpu[e["budget"]] = e["cpu_s"]
                        if e["budget"] not in dp:
                            dp[e["budget"]] = e["p"]["HA_TREND"]
                ids = np.asarray(A["test_ids"], str)
                for sy, ev, key in (("A", A["evals"], ka), ("B", B["evals"], kb), ("C", Cu["evals"], "HA_LEAN")):
                    bs = np.array([e["budget"] for e in ev], int); E[(sy, c, r, f)] = (bs, np.array([e["p"][key] for e in ev], float), ids)
                bs = np.array(sorted(dp), int); E[("D", c, r, f)] = (bs, np.array([dp[b] for b in bs], float), ids)
                for sy in SYS:
                    if not np.array_equal(E[(sy, c, r, f)][0], np.arange(8, 61)):
                        raise RuntimeError(f"{sy} {c} r{r} f{f}: budgets are not 8..60")
                ca = {e["budget"]: e["cpu_s"] for e in A["evals"]}; cb = {e["budget"]: e["cpu_s"] for e in B["evals"]}; cc = {e["budget"]: e["cpu_s"] for e in Cu["evals"]}
                sel = range(8, 60)                                                  # selection steps (b = 60 ends the path)
                tp = float(np.mean([dcpu[b] for b in sel if b in dcpu])) if dcpu else np.nan   # HA_TREND prediction cost: measured on the computed budgets only
                CPU.append({"condition": c, "cluster": r, "learner": f, "A_step": np.mean([ca[b] for b in sel]), "B_step": np.mean([cb[b] for b in sel]),
                            "C_step": np.mean([cb[b] + cc[b] for b in sel]), "D_step": float(np.mean([ca[b] for b in sel])) + tp,
                            "L_predict": np.mean([cc[b] for b in sel]), "T_predict": tp,
                            "C8_equals_A8": Cu["check_C8_equals_A8_maxabs"], "D_check": dchk[0], "D8_equals_B8": dchk[1]})
                la, lb = A["paid_ids"][:60], B["paid_ids"][:60]
                PATHS[(c, r, f)] = {"L_path": la, "T_path": lb, "overlap_60": len(set(la) & set(lb)),
                                    "first_divergence_query": next((q + 1 for q in range(60) if la[q] != lb[q]), None),
                                    "overlap_24": len(set(la[:24]) & set(lb[:24])),
                                    "L_how": [e.get("how") for e in A["evals"]], "T_how": [e.get("how") for e in B["evals"]]}
    return E, pd.DataFrame(CPU), PATHS


def hard_rows(E, M):
    """Pooled per cluster: recall on the 10 NEW short-Keyhole originals, specificity on the 12 NEW conduction runs, their mean,
    and recall on the 22 pooled short-Keyhole runs (evaluator-only memberships, RC24 definition)."""
    acc = {}
    for (sy, c, r, f), (bs, Pm, ids) in E.items():
        acc.setdefault((sy, c, r), []).append((bs, Pm, ids))
    out = []
    for (sy, c, r), parts in acc.items():
        bs = parts[0][0]; Pm = np.concatenate([p[1] for p in parts], 1); ids = np.concatenate([p[2] for p in parts]); m = M.reindex(ids)
        sk = m.shortK_NEW_original.to_numpy(bool); cn = ((m.source_batch == "NEW") & (m.y == 0)).to_numpy(bool); sp = m.shortK_pooled.to_numpy(bool); hat = Pm >= 0.5
        for j, b in enumerate(bs):
            rk = float(hat[j, sk].mean()) if sk.any() else np.nan; sc = float((~hat[j, cn]).mean()) if cn.any() else np.nan
            out.append({"system": sy, "condition": c, "cluster": r, "budget": int(b), "recall_shortK_NEW": rk, "spec_cond_NEW": sc, "BA_hard": 0.5 * (rk + sc),
                        "recall_shortK_pooled": float(hat[j, sp].mean()) if sp.any() else np.nan, "n_shortK_NEW": int(sk.sum()), "n_cond_NEW": int(cn.sum())})
    return pd.DataFrame(out)


def candidate(con):
    """Registered rule: largest dBA-AULC B8-B24 vs A among B, C, D; within 0.001 -> larger RMS saving at 0.95, then 0.93."""
    sc = {x: (con[x]["dBA_B8_B24"]["mean"], con[x]["rms_saving_0.95"]["mean"], con[x]["rms_saving_0.93"]["mean"]) for x in ("B", "C", "D")}
    best = max(sc, key=lambda x: sc[x][0]); near = [x for x in sc if sc[best][0] - sc[x][0] <= 0.001]
    pick = sorted(near, key=lambda x: (sc[x][1], sc[x][2]), reverse=True)[0]
    return pick, sc


def enough(con, summ, x):
    a = summ.set_index("system")
    c1 = con[x]["dBA_B8_B24"]["mean"] > 0; c2 = con[x]["rms_saving_0.93"]["mean"] > 0 and con[x]["rms_saving_0.95"]["mean"] > 0
    c3 = (a.loc[x, "attain_rate_0.95"] >= a.loc["A", "attain_rate_0.95"] - 0.025)
    kx = int(a.loc[x, "kept_0.95"].split("/")[0]) / int(a.loc[x, "kept_0.95"].split("/")[1]); ka = int(a.loc["A", "kept_0.95"].split("/")[0]) / int(a.loc["A", "kept_0.95"].split("/")[1])
    c4 = kx >= ka - 0.025
    return {"early_gain_positive": bool(c1), "rms_savings_both_positive": bool(c2), "attain_0.95_not_lower_by_0.025": bool(c3), "kept_0.95_not_lower_by_0.025": bool(c4),
            "enough": bool(c1 and c2 and c3 and c4), "kept_rate_x": kx, "kept_rate_a": ka}


def run():
    OUT.mkdir(parents=True, exist_ok=True); M = P.manifest(); res = {}
    for cond in ("STD", "K5", "K4"):
        E, CPU, PATHS = load(cond)
        D = EV.learner_rows(E, M.y); G = EV.pooled_rows(E, M.y)
        Ai = EV.aulc(D, ("system", "cluster", "learner")); Ap = EV.aulc(G, ("system", "cluster"))
        Ei = EV.endpoints(D, ("system", "cluster", "learner")); Ep = EV.endpoints(G, ("system", "cluster"))
        S = EV.summary_by_system(D, Ai, Ei, G, Ap, Ep)
        con = {x: EV.contrast_table(Ai, Ei, x, "A") for x in ("B", "C", "D")}
        conB = {x: EV.contrast_table(Ai, Ei, x, "B") for x in ("C", "D")}
        bat = {x: EV.ba_at(D, x, "A") for x in ("B", "C", "D")}
        dec = EV.decomposition(Ai, Ei)
        pooled_con = {x: {w: EV.cluster_diff(Ap[Ap.window == w], x, "A", "BA", key=("cluster",)) for w in EV.WIN} for x in ("B", "C", "D")}
        Hd = hard_rows(E, M); Ha = EV.aulc(Hd.assign(BA=Hd.BA_hard), ("system", "cluster"), cols=("BA",))
        hard = {"B60_mean": Hd[Hd.budget == 60].groupby("system")[["recall_shortK_NEW", "spec_cond_NEW", "BA_hard", "recall_shortK_pooled"]].mean().round(4).to_dict(),
                "BA_hard_AULC": Ha.groupby(["window", "system"]).BA.mean().round(4).unstack().to_dict()}
        reg = None
        if cond != "STD":
            Td = Ai.dropna(subset=["BA"]); R = Td.groupby(["window", "system", "cluster"]).BA.mean().reset_index()
            reg = {x: {w: EV.tstats((R[(R.window == w) & (R.system == x)].set_index("cluster").BA - R[(R.window == w) & (R.system == "A")].set_index("cluster").BA).values) for w in EV.WIN} for x in ("B", "C", "D")}
            reg["means"] = R.groupby(["window", "system"]).BA.mean().round(4).unstack().to_dict()
        ov = pd.Series([v["overlap_60"] for v in PATHS.values()])
        corner = pd.Series(((M.VX > 0.85) & (M.P > 330)).to_numpy(), index=M.index.astype(str))     # RC21 evaluator-only geometric diagnostic
        pdiag = []
        for (c, r, f), v in PATHS.items():
            for nm in ("L", "T"):
                q = v[f"{nm}_path"][8:]; h = [x for x in v[f"{nm}_how"][:52]]
                pdiag.append({"cluster": r, "learner": f, "path": nm, "corner_share_q9_60": float(corner.reindex(q).mean()), "corner_share_q9_24": float(corner.reindex(q[:16]).mean()),
                              "one_class_steps": int(sum(1 for x in h if x == "path")), "first_divergence_query": v["first_divergence_query"], "overlap_24": v["overlap_24"]})
        PD = pd.DataFrame(pdiag); PD.to_csv(OUT / f"{cond.lower()}_path_diagnostic.csv", index=False)
        path_diag = {"corner_share_q9_60": PD.groupby("path").corner_share_q9_60.mean().round(4).to_dict(), "corner_share_q9_24": PD.groupby("path").corner_share_q9_24.mean().round(4).to_dict(),
                     "one_class_steps_mean": PD.groupby("path").one_class_steps.mean().round(3).to_dict(),
                     "first_divergence_query": {"median": float(PD.first_divergence_query.dropna().median()), "min": float(PD.first_divergence_query.dropna().min()), "identical_paths": int(PD.first_divergence_query.isna().sum() // 2)},
                     "overlap_24_mean": float(PD.overlap_24.mean()), "pool_corner_share": float(corner.mean())}
        res[cond] = {"learners": int(D[["cluster", "learner"]].drop_duplicates().shape[0]), "clusters": int(D.cluster.nunique()), "summary": S.round(4).to_dict(orient="records"),
                     "contrasts_vs_A": con, "contrasts_vs_B": conB, "BA_at_budgets_vs_A": bat, "pooled_vs_A": pooled_con, "decomposition": dec, "hard_group": hard, "per_region": reg,
                     "cpu_mean_per_step": CPU[["A_step", "B_step", "C_step", "D_step", "L_predict", "T_predict"]].mean().round(4).to_dict(),
                     "checks": {"C8_equals_A8_maxabs": float(CPU.C8_equals_A8.max()), "D_check_b12_maxabs": float(CPU.D_check.max()), "D8_equals_B8_maxabs": float(CPU.D8_equals_B8.max())},
                     "path_overlap_L_T_of_60": {"mean": float(ov.mean()), "min": int(ov.min()), "max": int(ov.max())}, "path_diagnostic": path_diag}
        for nm, T in (("learner_curves", D), ("pooled_curves", G), ("individual_aulc", Ai), ("pooled_aulc", Ap), ("endpoints_learners", Ei), ("endpoints_pooled", Ep),
                      ("summary", S), ("cpu", CPU), ("hard_group", Hd)):
            T.to_csv(OUT / f"{cond.lower()}_{nm}.csv", index=False)
        if cond == "STD":
            pick, sc = candidate(con); res["candidate_rule"] = {"scores (dBA_B8_B24, rms_saving_0.95, rms_saving_0.93)": sc, "candidate": pick, "enough": enough(con, S, pick)}
    (OUT / "DEV_CROSS.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return res


if __name__ == "__main__":
    r = run(); print(json.dumps(r.get("candidate_rule"), indent=1, default=float))
