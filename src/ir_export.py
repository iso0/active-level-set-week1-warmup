"""IR export of the part C predictions (float32) and an INDEPENDENT recomputation of the registered carry-rule numbers.
The recomputation uses only the export (predictions, test ids, q20 flags), the pooled manifest and GSTAR_FROZEN.json, with its own
BA / RMSE / t-bound loop (no code from src.ir_eval), and compares S1-S4 for every model with screen/SCREEN_RESULT.json.
    python -m src.ir_export
"""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np
import pandas as pd
from scipy.stats import t as tdist

import src.el_cross as X
import src.ir_data as IRD
import src.rc18_common as RC
import src.rc19_pool as P

OUT = IRD.OUT / "exports" / "screen"


def export():
    M = P.manifest(); units = sorted((IRD.OUT / "ir-screen" / "units").glob("*.json.gz")); S = {}
    for f in units:
        u = RC.read_json_gz(f); S[f.name] = (None, u["condition"], int(u["cluster"]), int(u["learner"]))
    T = X.tasks_for(S, M); arr, keys, paths = {}, [], []
    for f in units:
        u = RC.read_json_gz(f); c, cl, l = u["condition"], int(u["cluster"]), int(u["learner"]); task = T[(c, cl, l)]
        bs = [int(e["budget"]) for e in u["evals"]]; models = sorted(set().union(*[e["pred"].keys() for e in u["evals"]]))
        for m in models:
            if m.startswith("LEARN_"):
                continue
            k = f"{m}|{c}|{cl}|{l}"; i = len(keys); keys.append(k)
            arr[f"mean_{i}"] = np.array([e["pred"][m][0] for e in u["evals"]], np.float32); arr[f"lat_{i}"] = np.array([e["pred"][m][1] for e in u["evals"]], np.float32)
            arr[f"noise_{i}"] = np.array([e["pred"][m][2] for e in u["evals"]], np.float32); arr[f"test_ids_{i}"] = np.array(u["test_ids"]); arr[f"q20_{i}"] = np.asarray(task["q20"], bool)
            arr[f"budgets_{i}"] = np.array(bs, int)
        for q, s in enumerate(u["paid_ids"], 1):
            paths.append({"condition": c, "cluster": cl, "learner": l, "query": q, "sim_id": s})
    OUT.mkdir(parents=True, exist_ok=True); np.savez_compressed(OUT / "predictions_f32.npz", keys=np.array(keys), **arr)
    pd.DataFrame(paths).to_csv(OUT / "paths.csv.gz", index=False)
    return {"keys": len(keys), "sha256_npz": hashlib.sha256((OUT / "predictions_f32.npz").read_bytes()).hexdigest()}


def independent():
    M = P.manifest(); G = json.loads((IRD.OUT / "GSTAR_FROZEN.json").read_text(encoding="utf-8")); z = np.load(OUT / "predictions_f32.npz")
    lx = np.log(M[list(P.INPUTS)].to_numpy(float)); H = dict(zip(M.index.astype(str), lx[:, 0] - 0.5 * lx[:, 1] - 1.5 * lx[:, 2]))
    Y = dict(zip(M.index.astype(str), M.y.astype(int))); AT = dict(zip(M.index.astype(str), M.log_A_um.astype(float))); SH = dict(zip(M.index.astype(str), M.short_record.astype(bool)))
    rows = []
    for i, k in enumerate([str(s) for s in z["keys"]]):
        m, c, cl, l = k.split("|"); ids = [str(s) for s in z[f"test_ids_{i}"]]; y = np.array([Y[s] for s in ids]); h = np.array([H[s] for s in ids]); a = np.array([AT[s] for s in ids])
        sh = np.array([SH[s] for s in ids]); q20 = z[f"q20_{i}"]; mu = np.asarray(z[f"mean_{i}"], float)
        for j, b in enumerate(z[f"budgets_{i}"]):
            r = {"model": m, "c": c, "cl": int(cl), "l": int(l), "b": int(b)}
            if (y == 1).any() and (y == 0).any():
                s1 = (h - G["mu"][0]) / G["sd"][0]; s2 = (mu[j] - G["mu"][1]) / G["sd"][1]; eta = G["intercept"] + G["coef"][0] * s1 + G["coef"][1] * s2
                hat = eta >= 0.0; r["ba"] = 0.5 * (np.mean(hat[y == 1]) + np.mean(~hat[y == 0]))
            ok = np.isfinite(a) & ~sh & np.isfinite(mu[j]) & q20
            r["rq"] = float(np.sqrt(np.mean((mu[j][ok] - a[ok]) ** 2))) if ok.any() else np.nan
            rows.append(r)
    D = pd.DataFrame(rows)

    def bound(model, conds, bs, col, rel=False):
        A = D[(D.model == model) & D.c.isin(conds) & D.b.isin(bs)].set_index(["c", "cl", "l", "b"])[col]; B = D[(D.model == "R0") & D.c.isin(conds) & D.b.isin(bs)].set_index(["c", "cl", "l", "b"])[col]
        d = ((A - B) / B if rel else A - B).dropna(); v = d.groupby(level=[0, 1, 2]).mean().groupby(level=[0, 1]).mean().to_numpy(); n = len(v)
        mm = float(v.mean()); se = float(v.std(ddof=1) / math.sqrt(n)); q = float(tdist.ppf(0.95, n - 1)); return {"mean": mm, "lcb": mm - q * se, "ucb": mm + q * se}
    ref = json.loads((IRD.OUT / "screen" / "SCREEN_RESULT.json").read_text(encoding="utf-8"))["rule"]; worst = 0.0; mine = {}
    for m in ref:
        got = {"S1_STD_early_proxyBA": bound(m, ("STD",), (8, 12, 16, 20, 24), "ba"), "S2_STD_early_rmse_q20_rel": bound(m, ("STD",), (8, 12, 16, 20, 24), "rq", True),
               "S3_STD_late_proxyBA": bound(m, ("STD",), (32, 40, 60), "ba"), "S4_GEO_all_proxyBA": bound(m, ("K5", "K4"), (8, 12, 16, 20, 24, 32, 40, 60), "ba")}
        mine[m] = got
        for rk, v in got.items():
            worst = max(worst, max(abs(v[q] - ref[m][rk][q]) for q in ("mean", "lcb", "ucb")))
    return {"max_abs_diff_vs_SCREEN_RESULT": worst, "PASS": bool(worst <= 1e-9), "models": len(mine)}


def run():
    RC.limit_threads(1); e = export(); ind = independent(); res = {"export": e, "independent_recomputation": ind, "utc": RC.utc()}
    (OUT.parent / "EXPORTS_ACCEPTANCE.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); print(json.dumps(res, indent=1, default=float)); return res


if __name__ == "__main__":
    run()
