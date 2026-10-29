"""C1S exports and independent recomputation (after the decisions; nothing here changes any rule or input).
  exports/main, exports/start_rand8, exports/start_local8: C1, A, AVG4, EVERY4, FREEZE24, C1_on_A at every budget (float32) + both paths'
  paid ids in query order with the rule that chose each (src.el_export format).
Checks (own code, export files + label manifest only):
  1. src.el_export.compare (per-learner BA-AULC B8-B24 / B8-B60 and target spend against the evaluator's tables);
  2. AVG4 / EVERY4 / FREEZE24 recomputed from the exported C1 probabilities with an independent implementation = exported values;
  3. headline: per-learner S95 and early BA-AULC recomputed, cluster means of AVG4 - C1 and C1 - A with t bounds = decision JSON.
    python -m src.c1s_export
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
from scipy.stats import t as tdist

import src.c1c_export as CX
import src.c1s_eval as SE
import src.c1s_fwd as FW
import src.el_eval as EV
import src.el_export as EX
import src.rc18_common as RC
import src.rc19_pool as P

BASE = FW.OUT / "exports"
SETS = {"main": ("c1s-main", "STD"), "start_rand8": ("c1s-start", "RAND8"), "start_local8": ("c1s-start", "LOCAL8")}


def fwd_set(name, M):
    job, cond = SETS[name]; d_units = FW.OUT / job / "units"; E, _, _ = SE.build(d_units, cond); reps = sorted({k[2] for k in E})
    d = BASE / name; n = EX.export_set(d, E, CX._paths(d_units, cond, reps))
    D = EV.learner_rows(E, M.y); Ai = EV.aulc(D, ("system", "cluster", "learner")); Ei = EV.endpoints(D, ("system", "cluster", "learner"))
    return {**EX.compare(d, M, Ai, Ei, cond), "keys": n}


def _avg_indep(bs, C, kind):
    """Independent re-implementation of the three decision-layer variants (b0 = 24)."""
    out = np.array(C, dtype=float, copy=True); pos = {int(b): i for i, b in enumerate(bs)}
    for i, b in enumerate(bs):
        b = int(b)
        if kind == "AVG4" and b >= 25:
            out[i] = np.mean(np.asarray(C, float)[max(0, i - 3):i + 1], axis=0)
        elif kind == "EVERY4" and b >= 24:
            out[i] = C[pos[24 + 4 * ((b - 24) // 4)]]
        elif kind == "FREEZE24" and b >= 24:
            out[i] = C[pos[24]]
    return out.astype(np.float32)


def _t(d):
    d = np.asarray(d, float); n = len(d); m = float(d.mean()); se = float(d.std(ddof=1) / math.sqrt(n)); q = float(tdist.ppf(0.95, n - 1))
    return {"mean": m, "lcb": m - q * se, "ucb": m + q * se, "n": n}


def independent(name, M, dec):
    Z = EX.load(BASE / name); y_all = dict(zip(M.index.astype(str), M.y.astype(int))); rows = []; var_err = 0.0
    for (sy, cond, c, l), (bs, Pm, ids) in Z.items():
        if sy == "C1":
            for k in ("AVG4", "EVERY4", "FREEZE24"):
                var_err = max(var_err, float(np.max(np.abs(_avg_indep(bs, Pm.astype(np.float32), k).astype(float) - Z[(k, cond, c, l)][1]))))
        y = np.array([y_all[s] for s in ids], int); pos = y == 1; neg = ~pos; ba = {}
        for j, b in enumerate(bs):
            hat = Pm[j] >= 0.5; ba[int(b)] = 0.5 * (hat[pos].mean() + (~hat[neg]).mean())
        s95 = float(np.mean([max(0.0, 0.95 - ba[b]) for b in range(24, 61)])); early = float(np.mean([ba[b] for b in range(8, 25)]))
        rows.append({"system": sy, "cluster": c, "learner": l, "S95": s95, "early": early})
    R = pd.DataFrame(rows); out = {"variant_recompute_max_abs": var_err}
    for x, a in (("AVG4", "C1"), ("C1", "A")):
        for col, key in (("S95", "dS95"), ("early", None)):
            T = R.pivot_table(index=["cluster", "learner"], columns="system", values=col); dd = (T[x] - T[a]).dropna().groupby(level=0).mean(); r = _t(dd.values)
            ref = dec["stability_contrasts"][f"{x}-{a}"]["dS95"] if col == "S95" else dec["contrasts"][f"{x}-{a}"]["dBA_B8_B24"]
            r["max_abs_diff_vs_decision"] = float(max(abs(r[q] - ref[q]) for q in ("mean", "lcb", "ucb")) if np.isfinite(ref["ucb"]) else abs(r["mean"] - ref["mean"]))
            out[f"{col}_{x}-{a}"] = r
    out["PASS"] = bool(var_err <= 1e-7 and all(v["max_abs_diff_vs_decision"] <= 1e-9 for k, v in out.items() if isinstance(v, dict)))
    return out


def run():
    M = P.manifest(); acc = {}; dec = json.loads((SE.OUT / "C1S_DECISION.json").read_text(encoding="utf-8"))
    for name in SETS:
        acc[name] = fwd_set(name, M); acc[f"{name}_independent"] = independent(name, M, dec[SETS[name][1]])
    BASE.mkdir(parents=True, exist_ok=True); (BASE / "EXPORTS_ACCEPTANCE.json").write_text(json.dumps(acc, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: v.get("PASS") for k, v in acc.items()}, indent=1)); return acc


if __name__ == "__main__":
    run()
