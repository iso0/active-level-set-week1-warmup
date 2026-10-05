"""Week 18 Phase 3 development runner for candidate arms (DEVELOPMENT blocks only; resumable).

Usage: python -m src.week18_dev_arms <experiment> <real|twins>
Experiments (arms defined here, kill criteria in ATTEMPT_LEDGER.md):
  depth  : G3 + margin (mlii_k4), Tobit + margin / straddle (mlii_k4) on tasks with depth (OLD tasks, pooled/transfer
           with OLD depth) and the depth twins
  cfa    : G3L + margin (C1), LTn + margin (F1), G3 + mix25 (A1) on all DEV real tasks and the binary twins
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from src.week18_baselines import budgets

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week18_independent_research/phase3"
EXPERIMENTS = {
    "depth": [(("G3", "mlii_k4"), "margin"), (("Tobit", "mlii_k4"), "margin"), (("Tobit", "mlii_k4"), "straddle")],
    "cfa": [(("G3L", "mlii"), "margin"), (("LTn", "mlii"), "margin"), (("G3", "mlii"), "mix25")],
}


def hyper_for(t, hyper):
    big = len(t["prior"]) + 120 > 200 and len(t["prior"]) > 0
    return "mlii_k8" if (big and hyper == "mlii") else hyper


def task_job(t, arms, out_dir):
    from threadpoolctl import threadpool_limits
    import src.week18_engine as E
    dest = Path(out_dir) / f"{t['task']}__r{t['repeat']:03d}_f{t['fold']}.json"
    if dest.exists():
        return json.loads(dest.read_text())
    has_depth = np.isfinite(t["depth"][np.r_[t["prior"], t["pool"]].astype(int)]).any()
    rows = []
    with threadpool_limits(1):
        for (model, hyper), rule in arms:
            if model == "Tobit" and not has_depth:
                continue
            if model == "LTn" and len(t["prior"]) + 120 > 200 and len(t["prior"]) > 0:
                continue                      # nested LT is per-step ML-II only; skipped on the large transfer fits
            learner = (model, hyper_for(t, hyper))
            out, L = E.run(t, learner, rule, set(budgets(t)))
            for o in out:
                r = {"task": t["task"], "repeat": t["repeat"], "fold": t["fold"], "model": model, "hyper": learner[1], "rule": rule,
                     "budget": o["budget"], "startup": o["startup"], "fp": o["fp"], "u": o["u"],
                     "rows": ",".join(map(str, t["test"])), "p": ",".join(f"{v:.5g}" for v in o["p"]),
                     "q20": ",".join("1" if v else "0" for v in t["q20"]) if t["q20"] is not None else ""}
                for k in ("NSD_0.1", "NSD_0.05", "ASSD", "dense_BA"):
                    if k in o:
                        r[k] = o[k]
                rows.append(r)
    dest.write_text(json.dumps(rows, default=float))
    return rows


def tasks(exp, which):
    import src.week18_tasks as T
    import src.week18_twins as W
    from src.week18_dev_depth import tasks as depth_tasks
    if exp == "depth":
        return depth_tasks(which)
    if which == "real":
        return T.all_real("DEV")
    return [W.twin_task(tw, d, n, rep) for tw in ("T_GP", "T_GBT", "T_NW", "T_QL", "T_TOBIT") for d, n in (("pooled", 433), ("OLD", 324), ("NEW", 108)) for rep in range(8)]


def main(exp, which):
    pdir = OUT / exp / f"cache_{which}"; pdir.mkdir(parents=True, exist_ok=True)
    T = tasks(exp, which); T.sort(key=lambda t: -(len(t["prior"]) + len(t["pool"])))
    res = Parallel(n_jobs=7, verbose=5)(delayed(task_job)(t, EXPERIMENTS[exp], pdir) for t in T)
    pd.DataFrame([r for rr in res for r in rr]).to_csv(OUT / exp / f"{exp}_dev_{which}.csv.gz", index=False)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
