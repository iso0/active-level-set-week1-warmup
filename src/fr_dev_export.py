"""FR DEV closing evidence (after the DEV decision; nothing here changes any rule or input). EVALUATOR ONLY.
  1. Tables at identical paid data on the recorded paths: C1, A (HA_LEAN), GATE, AVG and the registered strong alternative D_on_A
     (HA_TREND ML-II on A's path; A-path learner-paths only), with targets 0.90 / 0.93 / 0.95 ON THE RECORDED PATHS (a model effect on a
     fixed path, not an end-to-end cost) and the hard-group descriptors.
  2. exports/dev: C1, A, GATE and D_on_A at every budget (float32; AVG = (C1 + A) / 2 is recomputed from them) and the recorded paid ids in query order (src.el_export format; the learner key
     is learner * 10 + 1 for A's path, + 2 for C1's path).
  3. Independent recomputation (own BA loop and own t bounds, export files + label manifest only) of the registered DEV numbers
     (C-GEO, C-EARLY, C-LATE in DEV_GATE.json) and of the gain-area G1 (geometric oracle room in GAIN_AREA.json, same block learner-paths).
    python -m src.fr_dev_export
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
from scipy.stats import t as tdist

import src.ea_cand_eval as CE
import src.el_eval as EV
import src.el_export as EX
import src.fr_dev_eval as DE
import src.rc18_common as RC
import src.rc19_pool as P

OUT = DE.OUT
SYS = ("C1", "A", "GATE", "AVG", "D_on_A")


def build(M):
    E, GT = DE.load(M); cache = {}; paths = []
    for f in sorted((OUT / "fr-dev" / "units").glob("*.json.gz")):
        u = RC.read_json_gz(f); c, cl, l, tag = u["condition"], int(u["cluster"]), int(u["learner"]), u["path"]; lk = l * 10 + (1 if tag == "A" else 2)
        if tag == "A":
            src = ("cand_dev_k5" if c == "K5" and cl <= 40 else "cand_dev_k4" if c == "K4" and cl <= 24 else f"validation_{c.lower()}")
            sd = "D" if src.startswith("cand") else "D_on_A"
            if src not in cache:
                cache[src] = DE._npz(src)
            z, ix = cache[src]; i = ix[f"{sd}|{c}|{cl}|{l}"]
            if not np.array_equal(z[f"test_ids_{i}"].astype(str), np.asarray(u["test_ids"], str)):
                raise RuntimeError("D test set differs")
            E[("D_on_A", c, cl, lk)] = (np.arange(8, 61), np.asarray(z[f"pred_{i}"], float), np.asarray(u["test_ids"], str))
        for q, s in enumerate(u["paid_ids"][:60], 1):
            paths.append({"path": "HA_LEAN-selected (recorded)" if tag == "A" else "C1-selected (recorded)", "systems": "C1,A,GATE,AVG" + (",D_on_A" if tag == "A" else ""),
                          "condition": c, "cluster": cl, "learner": lk, "query": q, "sim_id": s, "rule": "startup" if q <= 8 else "recorded"})
    return E, paths


def _t(d):
    d = np.asarray(d, float); d = d[np.isfinite(d)]; n = len(d); m = float(d.mean()); se = float(d.std(ddof=1) / math.sqrt(n)); q = float(tdist.ppf(0.95, n - 1))
    return {"mean": m, "lcb": m - q * se, "ucb": m + q * se, "n": n}


def independent(d, M, dec, gain):
    Z = EX.load(d); y_all = dict(zip(M.index.astype(str), M.y.astype(int))); rows = []
    for (sy, cond, c, l), (bs, Pm, ids) in Z.items():
        y = np.array([y_all[s] for s in ids], int); pos, neg = y == 1, y == 0
        if not pos.any() or not neg.any():
            continue
        hat = Pm >= 0.5; ba = 0.5 * (hat[:, pos].mean(1) + (~hat[:, neg]).mean(1))
        r = {"system": sy, "condition": cond, "cluster": c, "learner": l, "early": float(ba[:17].mean()), "late": float(ba[17:].mean()), "full": float(ba.mean())}
        if sy == "C1":
            pA = Z[("A", cond, c, l)][1]; hA = pA >= 0.5; w = np.where(pos, 1 / (2 * pos.sum()), 1 / (2 * neg.sum()))
            r["GA_full"] = float((((hat != (y == 1)) & (hA == (y == 1))) @ w).mean())
            hv = (0.5 * Pm + 0.5 * pA) >= 0.5; bv = 0.5 * (hv[:, pos].mean(1) + (~hv[:, neg]).mean(1))
            rows.append({"system": "AVG", "condition": cond, "cluster": c, "learner": l, "early": float(bv[:17].mean()), "late": float(bv[17:].mean()), "full": float(bv.mean())})
        rows.append(r)
    R = pd.DataFrame(rows); out = {}

    def diff(cs, x, a, col):
        T = R[R.condition.isin(cs)]; X_ = T[T.system == x].set_index(["condition", "cluster", "learner"])[col]; A_ = T[T.system == a].set_index(["condition", "cluster", "learner"])[col]
        dd = (X_ - A_).dropna(); return _t(dd.groupby(level=[0, 1]).mean().values)
    out["C_GEO"] = diff(("K5", "K4"), "GATE", "C1", "full"); out["C_EARLY"] = diff(("STD",), "GATE", "C1", "early"); out["C_LATE"] = diff(("STD",), "GATE", "C1", "late")
    out["AVG-C1_geometric"] = diff(("K5", "K4"), "AVG", "C1", "full")
    T = R[R.condition.isin(("K5", "K4")) & (R.system == "C1")]; out["G1_geometric_GA"] = float(T.groupby(["condition", "cluster"]).GA_full.mean().mean())
    ref = dec["rule"]; mx = 0.0
    for k in ("C_GEO", "C_EARLY", "C_LATE"):
        mx = max(mx, max(abs(out[k][q] - ref[k][q]) for q in ("mean", "lcb", "ucb")))
    mx = max(mx, max(abs(out["AVG-C1_geometric"][q] - dec["contrasts"]["GEOMETRIC|B8_B60"]["AVG-C1"][q]) for q in ("mean", "lcb", "ucb")))
    g1 = abs(out["G1_geometric_GA"] - gain["gate"]["G1_geometric_GA_B8_B60"])
    out["max_abs_diff_vs_DEV_GATE_json"] = float(mx); out["abs_diff_G1_vs_GAIN_AREA_json"] = float(g1); out["PASS"] = bool(mx <= 1e-9 and g1 <= 1e-9); return out


def run():
    RC.limit_threads(1); M = P.manifest(); E, paths = build(M); D = EV.learner_rows(E, M.y); Ai = DE.aulc(D); res = {"evidence": "DEV, recorded paths (model effect at identical paid data)"}
    lv = {}
    for c, cs in DE.CONDS.items():
        for wn in DE.WINS:
            T = Ai[(Ai.window == wn) & Ai.condition.isin(cs)]
            lv[f"{c}|{wn}"] = {sy: {k: float(T[T.system == sy].groupby(["condition", "cluster"])[k].mean().mean()) for k in ("BA", "sens", "spec", "ll", "brier")} for sy in SYS}
    res["levels_all_paths (D_on_A: A-path only)"] = lv
    A_only = Ai[(Ai.learner % 10) == 1]; con = {}
    for c, cs in DE.CONDS.items():
        for wn in DE.WINS:
            con[f"{c}|{wn}|A-path"] = {f"{x}-{a}": DE.contrast(A_only, cs, wn, x, a) for x, a in (("D_on_A", "C1"), ("D_on_A", "A"), ("GATE", "D_on_A"), ("GATE", "C1"), ("A", "C1"))}
    res["contrasts_on_A_path"] = con
    S = D[D.condition == "STD"]; Ei = EV.endpoints(S, ("system", "cluster", "learner")); Su = CE.sustained(S, ("system", "cluster", "learner")); rows = []
    for sy in SYS:
        for tau in EV.TAUS:
            T = Ei[(Ei.system == sy) & (Ei.target == tau) & (Ei.defined == True)]; att = T.attained.astype(bool); Sx = Su[(Su.system == sy) & (Su.target == tau)]  # noqa: E712
            rows.append({"system": sy, "target": tau, "learner_paths": len(T), "attained": int(att.sum()), "not_attained": int((~att).sum()),
                         "first_mean": round(float(T["first"][att].astype(float).mean()), 2) if att.any() else None,
                         "confirmed_b_mean": round(float(T.confirmed_b[att].astype(float).mean()), 2) if att.any() else None,
                         "spend_mean_attainers_incl_startup_and_confirmation": round(float(T.spend[att].astype(float).mean()), 2) if att.any() else None,
                         "spend_median_attainers": float(T.spend[att].astype(float).median()) if att.any() else None,
                         "rms_horizon_60_not_a_cost": round(float(T.rms.mean()), 2), "kept_BA60": int(T.kept.astype(bool).sum()), "lost_by_60": int(T.lost.astype(bool).sum()),
                         "sustained_every_budget": int(Sx.sustained.astype(bool).sum())})
    res["targets_STD_on_recorded_paths"] = rows
    tc = {}
    for x in ("GATE", "AVG", "A", "D_on_A"):
        for tau in EV.TAUS:
            T = Ei[(Ei.target == tau) & (Ei.defined == True)].copy(); T["att"] = T.attained.astype(float); T["kp"] = T.kept.astype(float)  # noqa: E712
            tc[f"{x}-C1|{tau}"] = {"rms_saving": EV.cluster_diff(T, x, "C1", "rms", sign=-1.0), "d_attain": EV.cluster_diff(T, x, "C1", "att"), "d_kept": EV.cluster_diff(T, x, "C1", "kp")}
    res["target_contrasts_STD"] = tc
    d = OUT / "exports" / "dev"; n = EX.export_set(d, {k: v for k, v in E.items() if k[0] != "AVG"}, paths)   # AVG = (C1 + A) / 2 is recomputed from the exported components
    res["export_keys"] = n
    dec = json.loads((OUT / "dev" / "DEV_GATE.json").read_text(encoding="utf-8")); gain = json.loads((OUT / "gain" / "GAIN_AREA.json").read_text(encoding="utf-8"))
    acc = {"el_export_compare": EX.compare(d, M, Ai[Ai.window != "B25_B60"], EV.endpoints(D, ("system", "cluster", "learner")), "DEV"), "independent": independent(d, M, dec, gain)}
    acc["PASS"] = bool(acc["el_export_compare"]["PASS"] and acc["independent"]["PASS"])
    (OUT / "exports" / "EXPORTS_ACCEPTANCE.json").write_text(json.dumps(acc, indent=1, default=float), encoding="utf-8")
    (OUT / "dev" / "DEV_TABLES.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    pd.DataFrame(rows).to_csv(OUT / "dev" / "dev_targets_std.csv", index=False)
    print(json.dumps({"PASS": acc["PASS"], "compare": acc["el_export_compare"].get("PASS"), "indep": acc["independent"]}, indent=1, default=float)); return res, acc


if __name__ == "__main__":
    run()
