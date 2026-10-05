"""Week 18 Phase 3 development — depth-aware learners (E1, E2) vs G3 under matched ML-II schedules (DEVELOPMENT).

Tasks: R3_OLD, R2rev (OLD pool; NEW prior labels only), R2_TRANSFER (OLD prior with depth; NEW pool labels only),
R1_POOLED (OLD rows with depth; NEW rows labels only), twins T_TOBIT × {pooled 433, OLD 324, NEW 108} and
T_DEPTH × OLD 324 (DEV reps 0–7).  Arms: G3 + margin (mlii_k4), Tobit + margin (mlii_k4), Tobit + straddle
(mlii_k4), GPR_depth + straddle (mlii).
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
OUT = ROOT / "outputs/week18_independent_research/phase3/depth"
ARMS = [(("G3", "mlii_k4"), "margin"), (("Tobit", "mlii_k4"), "margin"), (("Tobit", "mlii_k4"), "straddle"), (("GPR_depth", "mlii"), "straddle")]


def task_job(t, out_dir):
    from threadpoolctl import threadpool_limits
    import src.week18_engine as E
    dest = Path(out_dir) / f"{t['task']}__r{t['repeat']:03d}_f{t['fold']}.json"
    if dest.exists():
        return json.loads(dest.read_text())
    rows = []
    has_depth = np.isfinite(t["depth"][np.r_[t["prior"], t["pool"]].astype(int)]).any()
    with threadpool_limits(1):
        for learner, rule in ARMS:
            if learner[0] != "G3" and not has_depth:
                continue
            out, L = E.run(t, learner, rule, set(budgets(t)))
            for o in out:
                r = {"task": t["task"], "repeat": t["repeat"], "fold": t["fold"], "model": learner[0], "hyper": learner[1], "rule": rule,
                     "budget": o["budget"], "startup": o["startup"], "fp": o["fp"], "u": o["u"],
                     "rows": ",".join(map(str, t["test"])), "p": ",".join(f"{v:.5g}" for v in o["p"]),
                     "q20": ",".join("1" if v else "0" for v in t["q20"]) if t["q20"] is not None else ""}
                for k in ("NSD_0.1", "NSD_0.05", "ASSD", "dense_BA"):
                    if k in o:
                        r[k] = o[k]
                rows.append(r)
    dest.write_text(json.dumps(rows, default=float))
    return rows


def tasks(which):
    import src.week18_tasks as T
    import src.week18_twins as W
    if which == "real":
        R = T.r3_old_tasks() + T.r3_old_tasks(prior_new=True) + T.pooled_tasks() + T.r3_new_tasks(prior_old=True)
        # attach OLD depth to the pooled / transfer tasks
        D = T.pooled_frame()
        import pandas as pd_
        pop = pd_.read_csv(ROOT / "outputs/week7_06_real_data_boundary_active_level_set/primary_common_population.csv", usecols=["experiment_name", "max_depth_um"])
        dmap = dict(zip(pop.experiment_name, pop.max_depth_um))
        for t in R:
            if t["task"] == "R1_POOLED":
                t["depth"] = D.sim_id.map(dmap).to_numpy(float)
            if t["task"] == "R2_TRANSFER":
                from src.week12_development_common import load_old
                o = load_old(); t["depth"] = np.r_[o.sim_id.map(dmap).to_numpy(float), np.full(len(t["y"]) - len(o), np.nan)]
        return [t for t in R if t["block"] == "DEV"]
    return [W.twin_task(tw, d, n, rep) for tw, d, n in [("T_TOBIT", "pooled", 433), ("T_TOBIT", "OLD", 324), ("T_TOBIT", "NEW", 108), ("T_DEPTH", "OLD", 324)] for rep in range(8)]


def main(which):
    OUT.mkdir(parents=True, exist_ok=True); pdir = OUT / f"cache_{which}"; pdir.mkdir(exist_ok=True)
    T = tasks(which); T.sort(key=lambda t: -(len(t["prior"]) + len(t["pool"])))
    res = Parallel(n_jobs=7, verbose=5)(delayed(task_job)(t, pdir) for t in T)
    pd.DataFrame([r for rr in res for r in rr]).to_csv(OUT / f"depth_dev_{which}.csv.gz", index=False)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "real")
