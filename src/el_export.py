"""EL study exports and the INDEPENDENT recomputation check.

export_set(d, E, path_rows): d/predictions_f32.npz (key system|condition|cluster|learner; pred[budget, test] = P(Keyhole) float32;
  budgets; test ids) and d/paths.csv.gz (every paid simulation id of every path, in query order, with the rule that chose it).
recompute(d, M): reads ONLY the export files and the label manifest and recomputes, with its own code (no src.el_eval import),
  per-learner BA at every budget, BA-AULC B8-B24 / B8-B60, and the 0.90 / 0.93 / 0.95 confirmed-attainment spend; compare() then
  checks them against the evaluator's CSV tables (max absolute difference; PASS if <= 1e-9 for BA / AULC and exact for spend).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd


def export_set(d, E, path_rows):
    d.mkdir(parents=True, exist_ok=True); keys, preds, tids, buds = [], [], [], []
    for (sy, cond, c, l), (bs, Pm, ids) in sorted(E.items(), key=lambda kv: (kv[0][0], kv[0][1], int(kv[0][2]), int(kv[0][3]))):
        keys.append(f"{sy}|{cond}|{int(c)}|{int(l)}"); preds.append(np.asarray(Pm, np.float32)); tids.append(np.asarray(ids, str)); buds.append(np.asarray(bs, np.int16))
    np.savez_compressed(d / "predictions_f32.npz", keys=np.asarray(keys), **{f"pred_{i}": v for i, v in enumerate(preds)}, **{f"test_ids_{i}": t for i, t in enumerate(tids)},
                        **{f"budgets_{i}": b for i, b in enumerate(buds)},
                        schema=np.asarray([json.dumps({"key": "system|condition|cluster|learner", "pred": "pred[budget index, test run] = P(Keyhole), float32", "budgets": "int16"})]))
    pd.DataFrame(path_rows).to_csv(d / "paths.csv.gz", index=False, compression="gzip")
    return len(keys)


def load(d):
    Z = np.load(d / "predictions_f32.npz", allow_pickle=False); out = {}
    for i, k in enumerate(Z["keys"]):
        sy, cond, c, l = str(k).split("|"); out[(sy, cond, int(c), int(l))] = (Z[f"budgets_{i}"].astype(int), Z[f"pred_{i}"].astype(float), Z[f"test_ids_{i}"].astype(str))
    return out


def recompute(d, M):
    """Own implementation: loops over learners; BA = (TPR + TNR) / 2 at threshold 0.5 (NaN for a one-class test set)."""
    E = load(d); y_all = dict(zip(M.index.astype(str), M.y.astype(int))); ba_rows, ep_rows = [], []
    for (sy, cond, c, l), (bs, Pm, ids) in E.items():
        y = np.array([y_all[s] for s in ids], int); pos = y == 1; neg = ~pos
        curve = {}
        for j, b in enumerate(bs):
            hat = Pm[j] >= 0.5
            curve[int(b)] = 0.5 * (hat[pos].mean() + (~hat[neg]).mean()) if pos.any() and neg.any() else np.nan
        e24 = np.mean([curve[b] for b in range(8, 25)]); e60 = np.mean([curve[b] for b in range(8, 61)])
        ba_rows.append({"system": sy, "condition": cond, "cluster": c, "learner": l, "BA_B8_B24": e24, "BA_B8_B60": e60})
        for tau in (0.90, 0.93, 0.95):
            sp = 61
            if np.isfinite(e60):
                for b in range(8, 57):
                    if curve[b] >= tau and curve[b + 4] >= tau:
                        sp = b + 4; break
            ep_rows.append({"system": sy, "condition": cond, "cluster": c, "learner": l, "target": tau, "rms": float(sp) if np.isfinite(e60) else np.nan})
    return pd.DataFrame(ba_rows), pd.DataFrame(ep_rows)


def compare(d, M, Ai, Ei, condition):
    """Ai / Ei: the evaluator's individual AULC and endpoint tables for this condition (src.el_eval)."""
    R1, R2 = recompute(d, M)
    A = Ai.pivot_table(index=["system", "cluster", "learner"], columns="window", values="BA").reset_index()
    j = R1.merge(A, on=["system", "cluster", "learner"], how="inner")
    d24 = np.nanmax(np.abs(j.BA_B8_B24 - j.B8_B24)) if len(j) else np.nan; d60 = np.nanmax(np.abs(j.BA_B8_B60 - j.B8_B60)) if len(j) else np.nan
    e = Ei[Ei.defined == True][["system", "cluster", "learner", "target", "rms"]]  # noqa: E712
    k = R2.dropna().merge(e, on=["system", "cluster", "learner", "target"], suffixes=("_re", "_ev"), how="inner")
    ds = float(np.max(np.abs(k.rms_re - k.rms_ev))) if len(k) else np.nan
    acc = {"condition": condition, "learner_curves": int(len(R1)), "aulc_cells_compared": int(2 * len(j)), "endpoint_cells_compared": int(len(k)),
           "max_abs_diff_BA_AULC_B8_B24": float(d24), "max_abs_diff_BA_AULC_B8_B60": float(d60), "max_abs_diff_rms_spend": ds}
    acc["PASS"] = bool(len(j) == len(R1) and len(j) > 0 and d24 <= 1e-9 and d60 <= 1e-9 and ds == 0.0)
    (d / "EXPORT_ACCEPTANCE.json").write_text(json.dumps(acc, indent=1), encoding="utf-8"); return acc
