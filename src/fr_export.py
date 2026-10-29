"""FR exports and independent recomputation (after the decision; nothing here changes any rule or input).
  exports/{std,k5,k4}: every system at every budget (float32: GATE, C1, A, D_on_A, AVG_on_G, C1_on_G, A_on_G, A_on_C1, and W_on_G = GATE's weight
  at the test runs) + the three paths' paid ids in query order with the rule that chose each (src.el_export format).
Checks (own code; export files + label manifest only):
  1. src.el_export.compare: per-learner BA-AULC B8-B24 / B8-B60 and the restricted-mean target spend against the evaluator's tables;
  2. GATE = W p_C1 + (1 - W) p_A and AVG = (p_C1 + p_A) / 2 recomputed from the exported components on GATE's path;
  3. headline: STD early GATE - C1 and geometric per-region GATE - C1 (B8-B60) recomputed with an own BA loop and own t bounds = FR_DECISION.json.
    python -m src.fr_export
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
from scipy.stats import t as tdist

import src.ea_export as EAX
import src.el_eval as EV
import src.el_export as EX
import src.fr_eval as FE
import src.rc18_common as RC
import src.rc19_pool as P

BASE = FE.OUT / "exports"


def _paths(cond):
    rows = []
    for fG in sorted((FE.OUT / "fr-fresh" / "units").glob(f"{cond}__*__G.json.gz")):
        uG = RC.read_json_gz(fG); uX = RC.read_json_gz(fG.with_name(fG.name.replace("__G.json.gz", "__X.json.gz"))); uL = RC.read_json_gz(fG.with_name(fG.name.replace("__G.json.gz", "__L.json.gz")))
        rows += EAX._rows_paths(uG, "GATE-selected", cond, "GATE,C1_on_G,A_on_G,AVG_on_G", [e.get("how") for e in uG["evals"]])
        rows += EAX._rows_paths(uX, "C1-selected", cond, "C1,A_on_C1", [e.get("how") for e in uX["evals"]])
        rows += EAX._rows_paths(uL, "HA_LEAN-selected", cond, "A,D_on_A", [e.get("how") for e in uL["evals"]])
    return rows


def _t(d):
    d = np.asarray(d, float); d = d[np.isfinite(d)]; n = len(d); m = float(d.mean()); se = float(d.std(ddof=1) / math.sqrt(n)); q = float(tdist.ppf(0.95, n - 1))
    return {"mean": m, "lcb": m - q * se, "ucb": m + q * se, "n": n}


def _ba_curve(Pm, y):
    pos, neg = y == 1, y == 0
    if not pos.any() or not neg.any():
        return None
    hat = Pm >= 0.5; return 0.5 * (hat[:, pos].mean(1) + (~hat[:, neg]).mean(1))


def run():
    M = P.manifest(); acc = {}; dec = json.loads((FE.OUT / "evaluation" / "FR_DECISION.json").read_text(encoding="utf-8"))
    FE.UNITS[0] = FE.OUT / "fr-fresh" / "units"; y_all = dict(zip(M.index.astype(str), M.y.astype(int))); AU = {}
    for cond in ("STD", "K5", "K4"):
        E, _, _, _ = FE.load(cond)
        for fG in sorted(FE.UNITS[0].glob(f"{cond}__*__G.json.gz")):
            uG = RC.read_json_gz(fG); E[("W_on_G", cond, int(uG["repeat"]), int(uG["fold"]))] = (np.arange(8, 61), np.array([e["w_test"] for e in uG["evals"]], float), np.asarray(uG["test_ids"], str))
        d = BASE / cond.lower(); n = EX.export_set(d, E, _paths(cond))
        D = EV.learner_rows({k: v for k, v in E.items() if k[0] != "W_on_G"}, M.y); Ai = EV.aulc(D, ("system", "cluster", "learner")); Ei = EV.endpoints(D, ("system", "cluster", "learner"))
        acc[cond] = {**EX.compare(d, M, Ai, Ei, cond), "keys": n}
        Z = EX.load(d); err_g = err_a = 0.0
        for (sy, cd, c, l), (bs, Pm, ids) in Z.items():
            if sy == "GATE":
                W = Z[("W_on_G", cd, c, l)][1]; p1 = Z[("C1_on_G", cd, c, l)][1]; p2 = Z[("A_on_G", cd, c, l)][1]
                err_g = max(err_g, float(np.max(np.abs(W * p1 + (1 - W) * p2 - Pm)))); err_a = max(err_a, float(np.max(np.abs(0.5 * p1 + 0.5 * p2 - Z[("AVG_on_G", cd, c, l)][1]))))
            if sy in ("GATE", "C1"):
                y = np.array([y_all[s] for s in ids], int); cur = _ba_curve(Pm, y)
                AU[(cd, sy, c, l)] = (np.nan, np.nan) if cur is None else (float(cur[:17].mean()), float(cur.mean()))
        acc[cond]["GATE_from_components_max_abs"] = err_g; acc[cond]["AVG_from_components_max_abs"] = err_a
    R = pd.DataFrame([{"condition": k[0], "system": k[1], "cluster": k[2], "learner": k[3], "early": v[0], "full": v[1]} for k, v in AU.items()])
    S = R[R.condition == "STD"].pivot_table(index=["cluster", "learner"], columns="system", values="early"); e = _t((S["GATE"] - S["C1"]).dropna().groupby(level=0).mean().values)
    gd = []
    for cond in ("K5", "K4"):
        T = R[(R.condition == cond)].dropna(subset=["full"]).groupby(["system", "cluster"]).full.mean(); gd += list((T.loc["GATE"] - T.loc["C1"]).dropna().values)
    g = _t(gd); ref_e = dec["verdicts"]["early"]; ref_g = dec["verdicts"]["geo"]
    acc["headline"] = {"STD_early_GATE-C1": e, "geometric_B8_B60_GATE-C1": g,
                       "max_abs_diff_vs_decision": float(max(abs(e[q] - ref_e[q]) for q in ("mean", "lcb", "ucb"))),
                       "max_abs_diff_geo_vs_decision": float(max(abs(g[q] - ref_g[q]) for q in ("mean", "lcb", "ucb")))}
    acc["PASS"] = bool(all(acc[c]["PASS"] for c in ("STD", "K5", "K4")) and all(acc[c]["GATE_from_components_max_abs"] <= 1e-6 and acc[c]["AVG_from_components_max_abs"] <= 1e-6 for c in ("STD", "K5", "K4"))
                       and acc["headline"]["max_abs_diff_vs_decision"] <= 1e-9 and acc["headline"]["max_abs_diff_geo_vs_decision"] <= 1e-9)
    BASE.mkdir(parents=True, exist_ok=True); (BASE / "EXPORTS_ACCEPTANCE.json").write_text(json.dumps(acc, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: (v.get("PASS") if isinstance(v, dict) and "PASS" in v else v) for k, v in acc.items()}, indent=1, default=float)); return acc


if __name__ == "__main__":
    run()
