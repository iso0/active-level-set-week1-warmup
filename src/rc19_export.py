"""RC19 compact export of every final trajectory (the unit files themselves are git-ignored but reproducible):
  report/paths.csv.gz          - every paid query in order (unit, workstream, arm, design, repeat, fold, query index, sim_id)
  report/predictions_*.npz     - held-out predictions with the matching test IDs and budgets: region (mean, latent var) and label (p) at every
                                 recorded budget in float16; regression (mean, predictive SD) in float32 at REG_BUDGETS
    python -m src.rc19_export
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import src.rc19_eval as EV
import src.rc19_pool as P

REP = P.OUT / "report"
REG_BUDGETS = (8, 16, 24, 40, 60, 80)


def main():
    rows = []; jobs = {"final-reg": "reg", "final-region": "region", "final-label": "label"}
    for job, kind in jobs.items():
        U = EV.load_units(P.OUT / "final" / job); keys, vals, tid = [], [], []
        for u in U:
            arm = u.get("arm", u.get("model")); acq = u.get("acq", "")
            for q, s in enumerate(u["paid_ids"], 1):
                rows.append({"workstream": kind, "arm": arm, "design": acq, "repeat": u["repeat"], "fold": u["fold"], "query": q, "sim_id": s})
            bud = [e["budget"] for e in u["evals"]]
            if kind == "reg":                                                  # float32 mean and predictive SD at REG_BUDGETS (full curves: reg_curves.csv)
                ev = [e for e in u["evals"] if e["budget"] in REG_BUDGETS]
                arr = np.full((len(ev), len(P.TARGETS), 2, len(u["test_ids"])), np.nan, np.float32)
                for i, e in enumerate(ev):
                    for k, c in enumerate(P.TARGETS):
                        pr = e["pred"].get(c)
                        if pr is not None:
                            arr[i, k, 0] = [np.nan if v is None else v for v in pr[0]]; arr[i, k, 1] = np.sqrt([np.nan if v is None else v for v in pr[1]])
            elif kind == "region":
                arr = np.full((len(bud), 2, len(u["test_ids"])), np.nan, np.float32)
                for i, e in enumerate(u["evals"]):
                    if e["mean"] is not None:
                        arr[i, 0] = [np.nan if v is None else v for v in e["mean"]]; arr[i, 1] = [np.nan if v is None else v for v in e["lat"]]
            else:
                arr = np.full((len(bud), len(u["test_ids"])), np.nan, np.float32)
                for i, e in enumerate(u["evals"]):
                    arr[i] = [np.nan if v is None else v for v in e["p"]]
            keys.append(f"{arm}|{acq}|r{u['repeat']}|f{u['fold']}"); vals.append(arr if kind == "reg" else arr.astype(np.float16)); tid.append(np.asarray(u["test_ids"]))
        bl = list(REG_BUDGETS) if kind == "reg" else ([e["budget"] for e in U[0]["evals"]] if U else [])
        np.savez_compressed(REP / f"predictions_{kind}.npz", keys=np.asarray(keys), budgets=np.asarray(bl),
                            targets=np.asarray(P.TARGETS), **{f"pred_{i}": v for i, v in enumerate(vals)}, **{f"test_ids_{i}": t for i, t in enumerate(tid)})
    pd.DataFrame(rows).to_csv(REP / "paths.csv.gz", index=False, compression="gzip")
    print("exported", len(rows), "paid queries")


if __name__ == "__main__":
    main()
