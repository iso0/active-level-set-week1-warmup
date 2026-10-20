"""RC21 reporting additions (not frozen; no verdict depends on them):
  export : float32 export of every recomputed Stage 1 prediction (PHR family on the 200 RC19B paths) + acceptance against
           stage1/stage1_metrics.csv; posterior diagnostics per state as CSV
  compute: CPU accounting of every RC21 / RC21B job from the unit records
    python -m src.rc21_eval_extra export | compute
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc19_pool as P

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc21"


def _arr(x):
    return np.asarray([np.nan if v is None else v for v in x], float)


def export_stage1():
    M = P.manifest(); U = EV.load_units(OUT / "d-replay"); exp = OUT / "stage1_export"; exp.mkdir(parents=True, exist_ok=True)
    keys, arrs, tids, buds, post = [], [], [], [], []
    for u in U:
        for c in u["evals"][0]["p"]:
            keys.append(f"{c}@{u['path_of']}|r{u['repeat']}|f{u['fold']}"); arrs.append(np.asarray([_arr(e["p"][c]) for e in u["evals"]], np.float32))
            tids.append(np.asarray(u["test_ids"])); buds.append(np.asarray([e["budget"] for e in u["evals"]], np.int16))
        for e in u["evals"]:
            ph = e["info"].get("phr") or {}
            post.append({"path": u["path_of"], "repeat": u["repeat"], "fold": u["fold"], "budget": e["budget"], "cpu_s": e["cpu_s"],
                         **{k: v for k, v in ph.items() if not isinstance(v, list)}, "map_config": json.dumps(ph.get("map_config"))})
    np.savez_compressed(exp / "stage1_predictions_f32.npz", keys=np.asarray(keys), **{f"pred_{i}": v for i, v in enumerate(arrs)}, **{f"test_ids_{i}": t for i, t in enumerate(tids)},
                        **{f"budgets_{i}": t for i, t in enumerate(buds)},
                        schema=np.asarray([json.dumps({"pred": "pred[budget, test] = P(Keyhole) of construction@path on the SAME paid prefix as the RC19B unit "
                                                               "(paths: opus_rc19b/export_final/paths_final.csv.gz), float32"})]))
    pd.DataFrame(post).to_csv(exp / "stage1_phr_posterior.csv.gz", index=False, compression="gzip")
    Z = np.load(exp / "stage1_predictions_f32.npz", allow_pickle=False); Xe = []
    for i, k in enumerate(Z["keys"]):
        arm, r, f = k.split("|"); to = lambda x: [None if not np.isfinite(v) else float(v) for v in x]
        Xe.append({"arm": arm, "repeat": int(r[1:]), "fold": int(f[1:]), "test_ids": list(Z[f"test_ids_{i}"]),
                   "evals": [{"budget": int(b), "p": to(Z[f"pred_{i}"][j])} for j, b in enumerate(Z[f"budgets_{i}"])]})
    a = EV.label_metrics(Xe, M); b = pd.read_csv(OUT / "stage1" / "stage1_metrics.csv"); j = a.merge(b, on=["arm", "repeat", "budget"], suffixes=("_export", "_csv"))
    res = {"cells_compared": int(len(j)), "cells_recomputed_constructions": int(len(a)), "note": "SHQ_ATS_H in the export is the recomputed value (= RC20 cache within 3e-8); the tables use the cache"}
    for c in ("BA", "sensitivity", "specificity", "AUC", "brier", "log_loss"):
        jj = j[~j.arm.str.startswith("SHQ_ATS_H@")]
        d = np.abs(jj[f"{c}_export"].to_numpy(float) - jj[f"{c}_csv"].to_numpy(float)); d = d[np.isfinite(d)]
        res[c] = {"max_abs_diff": float(d.max()) if len(d) else 0.0, "cells_differing_gt_1e-12": int((d > 1e-12).sum())}
    res["PASS"] = bool(all(v["cells_differing_gt_1e-12"] == 0 for v in res.values() if isinstance(v, dict)))
    (exp / "EXPORT_ACCEPTANCE.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); print(json.dumps(res)); return res


def compute():
    rows = []
    for job in ("d-replay", "d-smoke", "d-final", "e-smoke", "e-final"):
        d = OUT / job / "units"
        if not d.exists():
            continue
        U = EV.load_units(OUT / job); cpu = 0.0
        for u in U:
            cpu += float(u.get("cpu_s") or sum(e.get("cpu_s") or 0.0 for e in u["evals"]) or u.get("seconds", 0.0))
        rows.append({"job": job, "units": len(U), "CPU-h": round(cpu / 3600, 2)})
    T = pd.DataFrame(rows); tot = float(T["CPU-h"].sum())
    L = ["# RC21 compute accounting (single-thread CPU seconds recorded by each unit; validation, evaluation and reporting runs excluded, each < 5 min)", "",
         "| job | units | CPU-h |", "|---|---|---|"] + [f"| {r.job} | {r.units} | {r['CPU-h']:.2f} |" for _, r in T.iterrows()] + [f"| **total** | {int(T.units.sum())} | **{tot:.2f}** |", "",
         "Paid simulations are a separate cost axis: every Keyhole trajectory spends up to 60 (startup included); no new physical simulation was run (all outcomes are from the 541-run pool)."]
    (OUT / "COMPUTE.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L)); return T


if __name__ == "__main__":
    RC.limit_threads(1); {"export": export_stage1, "compute": compute}[sys.argv[1]]()
