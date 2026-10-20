"""RC20 Stage 1 additions written AFTER the sequential freeze (reporting / exploratory only; not part of any frozen verdict):
  export : float32 export of every recomputed Stage 1 prediction + acceptance against stage1_metrics.csv
  replayx: exploratory h-specificity control on the 200 Stage 1 paths (generic exact inputs vs log h)
    python -m src.rc20_eval_extra export | replayx
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.rc19_eval as EV
import src.rc19_pool as P
import src.rc20_eval as R20
from src.rc19_report import md

OUT = R20.OUT


def export_stage1():
    M = P.manifest(); U = EV.load_units(OUT / "c-replay"); exp = OUT / "stage1_export"; exp.mkdir(parents=True, exist_ok=True)
    keys, arrs, tids, buds = [], [], [], []
    for u in U:
        for c in u["evals"][0]["p"]:
            keys.append(f"{c}@{u['path_of']}|r{u['repeat']}|f{u['fold']}"); arrs.append(np.asarray([R20._arr(e["p"][c]) for e in u["evals"]], np.float32))
            tids.append(np.asarray(u["test_ids"])); buds.append(np.asarray([e["budget"] for e in u["evals"]], np.int16))
    np.savez_compressed(exp / "stage1_predictions_f32.npz", keys=np.asarray(keys), **{f"pred_{i}": v for i, v in enumerate(arrs)}, **{f"test_ids_{i}": t for i, t in enumerate(tids)},
                        **{f"budgets_{i}": t for i, t in enumerate(buds)},
                        schema=np.asarray([json.dumps({"pred": "pred[budget, test] = P(Keyhole) of construction@path on the SAME paid prefix as the RC19B unit "
                                                               "(paths: opus_rc19b/export_final/paths_final.csv.gz), float32"})]))
    Z = np.load(exp / "stage1_predictions_f32.npz", allow_pickle=False); Xe = []
    for i, k in enumerate(Z["keys"]):
        arm, r, f = k.split("|"); to = lambda x: [None if not np.isfinite(v) else float(v) for v in x]
        Xe.append({"arm": arm, "repeat": int(r[1:]), "fold": int(f[1:]), "test_ids": list(Z[f"test_ids_{i}"]),
                   "evals": [{"budget": int(b), "p": to(Z[f"pred_{i}"][j])} for j, b in enumerate(Z[f"budgets_{i}"])]})
    a = EV.label_metrics(Xe, M); b = pd.read_csv(OUT / "stage1" / "stage1_metrics.csv"); j = a.merge(b, on=["arm", "repeat", "budget"], suffixes=("_export", "_csv"))
    res = {"cells_compared": int(len(j)), "cells_recomputed_constructions": int(len(a))}
    for c in ("BA", "sensitivity", "specificity", "AUC", "brier", "log_loss"):
        d = np.abs(j[f"{c}_export"].to_numpy(float) - j[f"{c}_csv"].to_numpy(float)); d = d[np.isfinite(d)]
        res[c] = {"max_abs_diff": float(d.max()) if len(d) else 0.0, "cells_differing_gt_1e-12": int((d > 1e-12).sum())}
    res["PASS"] = bool(res["cells_compared"] == res["cells_recomputed_constructions"] and all(v["cells_differing_gt_1e-12"] == 0 for v in res.values() if isinstance(v, dict)))
    (exp / "EXPORT_ACCEPTANCE.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); print(json.dumps(res)); return res


def replay_x():
    M = P.manifest(); U = EV.load_units(OUT / "c-replay-x"); X = []
    for u in U:
        for c in u["evals"][0]["p"]:
            X.append({"arm": f"{c}@{u['path_of']}", "repeat": u["repeat"], "fold": u["fold"], "test_ids": u["test_ids"],
                      "evals": [{"budget": e["budget"], "p": e["p"][c], "status": "ok"} for e in u["evals"]]})
    B = EV.label_metrics(X, M); R = OUT / "stage1_x"; R.mkdir(parents=True, exist_ok=True); B.to_csv(R / "stage1x_metrics.csv", index=False, lineterminator="\n")
    A_all, A_small = R20.aulc(B, R20.W_ALL), R20.aulc(B, R20.W_SMALL); rows = []
    for title, a, b in (("generic inputs vs log h (ATS)", "SHQ_ATS_X", "SHQ_ATS_H"), ("generic inputs vs log h (A)", "SHQ_A_X", "SHQ_A_H"),
                        ("generic inputs vs none (ATS)", "SHQ_ATS_X", "SHQ_ATS"), ("log h vs none (ATS), recomputed", "SHQ_ATS_H", "SHQ_ATS")):
        for win, A in (("B8–B60", A_all), ("B8–B24", A_small)):
            for met, low in (("LL", True), ("BA", False)):
                rows.append({"comparison": title, "window": win, **R20.contrast(A, a, b, met, low)})
    C = pd.DataFrame(rows); C.to_csv(R / "stage1x_contrasts.csv", index=False, lineterminator="\n")
    S = pd.DataFrame([{"construction": c, **{f"{m} {w}": float(R20.allpath(A, m).loc[c].mean()) for w, A in (("B8–B60", A_all), ("B8–B24", A_small)) for m in ("LL", "BA")}}
                      for c in sorted(A_all.cons.unique())])
    L = ["# RC20 exploratory h-specificity control (registered after Stage 1; the same 200 paths and paid prefixes)", "",
         "SHQ_*_X replaces log h~ by the 4 standardised exact log inputs in the same L2 logistic classifier (C = 1).", "", md(S, 4), "", md(C, 4), ""]
    (R / "STAGE1_X.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L)); return C


if __name__ == "__main__":
    {"export": export_stage1, "replayx": replay_x}[sys.argv[1]]()
