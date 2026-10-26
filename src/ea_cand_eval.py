"""EA stage 2 DEV evaluation (PROTOCOL_EA_CANDIDATES.md sections 4-5). All test rows; every budget 8..60; individual learners primary,
pooled beside. Systems on the SAME recorded HA_LEAN paths: A (= HA_LEAN, recorded), D (HA_TREND, recorded), E (EL-2 mixture, recorded),
C1, C1a, C1b (this study). Windows: early B8-B24, late B28-B60 (every budget), all B8-B60.
    python -m src.ea_cand_eval
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import src.ea_cand as CA
import src.el_eval as EV
import src.rc18_common as RC
import src.rc19_pool as P

OUT = CA.OUT / "cand_dev"
LATE = tuple(range(28, 61))


def sustained(D, by, taus=(0.90, 0.93, 0.95)):
    """attained (b and b + 4) AND BA >= tau at EVERY budget from the confirmation to 60 (stricter than 'kept' = BA(60) >= tau)."""
    out = []
    for key, g in D.groupby(list(by)):
        cur = dict(zip(g.budget.astype(int), g.BA.astype(float))); bs = sorted(cur)
        if any(not np.isfinite(cur[b]) for b in bs):
            continue
        for tau in taus:
            conf = next((b for b in bs if b + 4 in cur and cur[b] >= tau and cur[b + 4] >= tau), None)
            out.append({**dict(zip(by, key)), "target": tau, "sustained": bool(conf is not None and all(cur[b] >= tau for b in bs if b >= conf))})
    return pd.DataFrame(out)


def load(cond):
    E = {}; CPU = []
    for fp in sorted((CA.OUT / "ea-cand-dev" / "units").glob(f"{cond}__*.json.gz")):
        u = RC.read_json_gz(fp); r, f = int(u["repeat"]), int(u["fold"]); ids = np.asarray(u["test_ids"], str); src = CA.dev_path_unit(cond, r, f)
        bs = np.array([e["budget"] for e in u["evals"]], int)
        for nm in ("C1", "C1a", "C1b"):
            E[(nm, cond, r, f)] = (bs, np.array([e["p"][nm] for e in u["evals"]], float), ids)
        bs2 = np.array([e["budget"] for e in src["evals"]], int)
        for nm, k in (("A", "p_L"), ("D", "p_T"), ("E", "p_E")):
            E[(nm, cond, r, f)] = (bs2, np.array([e[k] for e in src["evals"]], float), ids)
        CPU.append({"cluster": r, "learner": f, **{nm: float(np.mean([e["cpu_s"][nm] for e in u["evals"][:52]])) for nm in ("C1", "C1a", "C1b")},
                    "A_step_recorded": float(np.mean([e["cpu_s"] for e in src["own_evals"][:52]])), "T_fit_recorded": float(np.mean([e["cpu_T"] for e in src["evals"][:52]]))})
    return E, pd.DataFrame(CPU)


def run():
    OUT.mkdir(parents=True, exist_ok=True); M = P.manifest(); res = {}
    for cond in ("STD", "K5", "K4"):
        E, CPU = load(cond); D = EV.learner_rows(E, M.y); G = EV.pooled_rows(E, M.y)
        Ai = EV.aulc(D, ("system", "cluster", "learner")); Ap = EV.aulc(G, ("system", "cluster"))
        late = D[D.budget.isin(LATE)].groupby(["system", "cluster", "learner"])[["BA", "sens", "spec", "ll", "brier"]].mean().reset_index(); late["window"] = "B28_B60"
        Ai2 = pd.concat([Ai, late], ignore_index=True)
        Ei = EV.endpoints(D, ("system", "cluster", "learner")); Ep = EV.endpoints(G, ("system", "cluster")); S = EV.summary_by_system(D, Ai, Ei, G, Ap, Ep)
        Su = sustained(D, ("system", "cluster", "learner"))
        con = {}
        for x, a in (("C1", "A"), ("C1", "D"), ("C1", "E"), ("C1", "C1b"), ("C1a", "A"), ("C1a", "D"), ("C1b", "A"), ("D", "A"), ("E", "A"), ("C1", "C1a")):
            c = EV.contrast_table(Ai, Ei, x, a); c["dBA_B28_B60"] = EV.cluster_diff(Ai2[Ai2.window == "B28_B60"], x, a, "BA")
            for tau in (0.90, 0.93, 0.95):
                T = Su[Su.target == tau].copy(); T["s"] = T.sustained.astype(float); c[f"d_sustained_{tau}"] = EV.cluster_diff(T, x, a, "s")
            con[f"{x}-{a}"] = c
        sus = Su.groupby(["system", "target"]).sustained.agg(lambda s: f"{int(s.sum())}/{len(s)}").unstack().to_dict()
        bat = {x: EV.ba_at(D, x, "A") for x in ("C1", "C1a", "C1b", "D", "E")}
        reg = None
        if cond != "STD":
            Td = Ai[Ai.window == "B8_B60"].dropna(subset=["BA"]); R = Td.groupby(["system", "cluster"]).BA.mean()
            reg = {x: EV.tstats((R.loc[x] - R.loc["A"]).dropna().values) for x in ("C1", "C1a", "C1b", "D", "E")}
        res[cond] = {"learners": int(D[["cluster", "learner"]].drop_duplicates().shape[0]), "summary": S.round(4).to_dict(orient="records"), "sustained": sus,
                     "late_window_means": late.groupby("system")[["BA", "ll", "brier"]].mean().round(4).to_dict(), "contrasts": con, "BA_at_budgets_vs_A": bat,
                     "per_region_vs_A": reg, "cpu_mean_per_step": CPU.drop(columns=["cluster", "learner"]).mean().round(4).to_dict()}
        for nm, T in (("learner_curves", D), ("pooled_curves", G), ("individual_aulc", Ai2), ("endpoints_learners", Ei), ("summary", S), ("cpu", CPU), ("sustained", Su)):
            T.to_csv(OUT / f"{cond.lower()}_{nm}.csv.gz", index=False, compression="gzip")
    # carry rule (section 5), STD
    c = res["STD"]["contrasts"]
    def ok(x, dtol):
        e = c[f"{x}-A"]["dBA_B8_B24"]; d = c[f"{x}-D"]["dBA_B8_B24"]["mean"]; l = c[f"{x}-A"]["dBA_B28_B60"]["mean"]
        return {"early_vs_A_lcb_gt_0": bool(e["lcb"] > 0), "early_vs_D_ge_tol": bool(d >= dtol), "late_vs_A_ge_0": bool(l >= 0), "early_vs_A": e["mean"], "early_vs_D": d, "late_vs_A": l}
    r1, r1a = ok("C1", -0.001), ok("C1a", -0.002); p1 = all(v for k, v in r1.items() if isinstance(v, bool)); p1a = all(v for k, v in r1a.items() if isinstance(v, bool))
    carried = None
    if p1 or p1a:
        carried = "C1" if (p1 and (not p1a or r1["early_vs_A"] >= r1a["early_vs_A"])) else "C1a"
    mech = c["C1-C1b"]["dBA_B8_B24"]["mean"]
    if carried == "C1" and mech <= 0:
        carried = "C1b"
    res["carry_rule"] = {"C1": r1, "C1a": r1a, "C1_minus_C1b_early": mech, "carried": carried}
    (OUT / "CAND_DEV.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); return res


if __name__ == "__main__":
    r = run(); print(json.dumps(r["carry_rule"], indent=1, default=float))
