"""EA amendment-1 analysis: D2 (hyperparameter oracle) and D3 (linear-in-z_h emulator) against R0_L / R0_T of the ladder on the same
learners, budgets and common rows; D4 (corner-capped margin path) against the recorded margin path (EL-1 forward A) on all test rows,
every budget, with the registered target endpoints. Test outcomes are read only here.
    python -m src.ea_analyze2
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import src.ea_analyze as AN
import src.ea_diag as DG
import src.el_eval as EV
import src.rc18_common as RC
import src.rc19_pool as P

OUT = DG.OUT / "diagnosis"


def run():
    M = P.manifest(); y_of = M.y; recs = []; Ecap = {}; Eref = {}
    for fp in sorted((DG.OUT / "ea-diag2" / "units").glob("STD__*.json.gz")):
        u = RC.read_json_gz(fp); r, f = u["repeat"], u["fold"]; ids = np.asarray(u["test_ids"], str)
        lad = RC.read_json_gz(DG.OUT / "ea-diag" / "units" / f"STD__r{r}_f{f}.json.gz"); ok = np.asarray(lad["test_has_depth"], bool); y = y_of.reindex(ids[ok]).to_numpy(int)
        lp = {e["budget"]: e["p"] for e in lad["evals"]}
        for e in u["evals"]:
            b = e["budget"]
            for k, p in list(e["p"].items()) + [("R0_L", lp[b]["R0_L"]), ("R0_T", lp[b]["R0_T"]), ("R3", lp[b]["R3"])]:
                hat = np.asarray(p, float)[ok] >= 0.5; n1, n0 = int((y == 1).sum()), int((y == 0).sum())
                recs.append({"cluster": r, "learner": f, "budget": b, "rung": k, "BA": 0.5 * (np.mean(hat[y == 1]) + np.mean(~hat[y == 0])), "sens": float(np.mean(hat[y == 1])), "spec": float(np.mean(~hat[y == 0]))})
        cap = u["D4_capped"]; bs = np.array([e["budget"] for e in cap["evals"]], int)
        Ecap[("D4_capped", "STD", r, f)] = (bs, np.array([e["p"] for e in cap["evals"]], float), ids)
        ref = DG.path_unit("STD", r, f); Eref[("A_margin", "STD", r, f)] = (np.array([e["budget"] for e in ref["evals"]], int), np.array([e["p"]["HA_LEAN"] for e in ref["evals"]], float), np.asarray(ref["test_ids"], str))
    D = pd.DataFrame(recs); D["window"] = np.where(D.budget <= 24, "early_B8_B24", "late_B28_B60")
    W = D.groupby(["window", "cluster", "learner", "rung"])[["BA", "sens", "spec"]].mean().reset_index().rename(columns={"rung": "system"})
    res = {"D2_D3_window_means": W.groupby(["window", "system"])[["BA", "sens", "spec"]].mean().round(4).reset_index().to_dict(orient="records"),
           "D2_D3_BA_at_budget": D[D.budget.isin((8, 12, 16, 24, 40, 60))].groupby(["budget", "rung"]).BA.mean().round(4).unstack().to_dict()}
    res["D2_D3_contrasts"] = {w: {f"{x} - {a}": EV.cluster_diff(W[W.window == w], x, a, "BA") for x, a in (("D2_hp_oracle", "R0_L"), ("D3_lin_h", "R0_L"), ("D3_lin_h", "R0_T"), ("D2_hp_oracle", "R0_T"))}
                              for w in ("early_B8_B24", "late_B28_B60")}
    # D4 vs the recorded margin path: full learner metrics + endpoints (all test rows)
    E = {**Ecap, **Eref}; L = EV.learner_rows(E, y_of); Ai = EV.aulc(L, ("system", "cluster", "learner")); Ei = EV.endpoints(L, ("system", "cluster", "learner"))
    con = EV.contrast_table(Ai, Ei, "D4_capped", "A_margin"); S = EV.summary_by_system(L, Ai, Ei)
    res["D4_summary"] = S.round(4).to_dict(orient="records"); res["D4_vs_margin"] = con
    corner = ((M.VX > 0.85) & (M.P > 330))
    res["D4_corner_paid_at_60"] = float(np.mean([RC.read_json_gz(fp)["D4_capped"]["evals"][-1]["corner_paid"] for fp in sorted((DG.OUT / "ea-diag2" / "units").glob("STD__*.json.gz"))]))
    res["margin_corner_paid_at_60"] = float(np.mean([corner.reindex(DG.path_unit("STD", r, f)["paid_ids"][:60]).sum() for r in range(83, 123) for f in range(1, 6)]))
    (OUT / "AMENDMENT1_DIAGNOSTICS.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); return res


if __name__ == "__main__":
    r = run()
    print(pd.DataFrame(r["D2_D3_window_means"]).pivot_table(index="system", columns="window", values="BA").round(4).to_string())
    print(pd.DataFrame(r["D2_D3_BA_at_budget"]).round(4).to_string())
    for w, d in r["D2_D3_contrasts"].items():
        for k, v in d.items():
            print(w, k, EV.fmt(v))
    S = pd.DataFrame(r["D4_summary"]); print(S[["system", "BA_B8_B24", "BA_B8_B60", "attained_0.93", "rms_0.93", "attained_0.95", "rms_0.95", "kept_0.95"]].to_string())
    c = r["D4_vs_margin"]; print("D4 - margin: early", EV.fmt(c["dBA_B8_B24"]), "all", EV.fmt(c["dBA_B8_B60"]), "rms0.93", EV.fmt(c["rms_saving_0.93"], 2), "rms0.95", EV.fmt(c["rms_saving_0.95"], 2),
          "dAtt0.95", EV.fmt(c["d_attain_0.95"], 3), "dKept0.95", EV.fmt(c["d_kept_0.95"], 3))
    print("corner paid at 60: capped", r["D4_corner_paid_at_60"], "margin", r["margin_corner_paid_at_60"])
