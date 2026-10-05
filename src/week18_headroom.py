"""Week 18 headroom: full-pool fits (every paid-pool label revealed) give the pool-limited ceiling of each task.

For each DEV task (real R1/R2/R2rev/R3_NEW/R3_OLD, twins) fit G3 (ML-II), and the depth learners where depth
exists, on prior ∪ all pool rows; evaluate the task's test rows (real) or the dense truth (twins).  The gap
between the B_max value of an arm and this ceiling is the improvement still available to any acquisition rule
for that model; the gap between models' ceilings is what a better model can add at saturation.
Usage: python -m src.week18_headroom <real|twins> [n_jobs]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week18_independent_research/phase3/headroom"


def job(t, dest):
    from threadpoolctl import threadpool_limits
    import src.week18_engine as E
    dest = Path(dest)
    if dest.exists():
        return json.loads(dest.read_text())
    rows = []
    if len(set(t["y"][t["pool"]]) | set(t["y"][t["prior"]])) < 2:
        dest.write_text("[]"); return rows
    has_depth = np.isfinite(t["depth"][np.r_[t["prior"], t["pool"]].astype(int)]).any()
    E._PHYS[0] = t.get("phys_fn")
    L = list(map(int, t["pool"]))
    with threadpool_limits(1):
        for model in ["G3", "LT"] + (["GPR_depth", "Tobit"] if has_depth else []):
            f = E.fit_learner((model, "mlii"), t, L, None, {"kernel": None, "b0": len(L)})
            p = E.proba(f, t["X"][t["test"]])
            r = {"task": t["task"], "repeat": t["repeat"], "fold": t["fold"], "model": model, "n_fit": len(L) + len(t["prior"]),
                 "rows": ",".join(map(str, t["test"])), "p": ",".join(f"{v:.5g}" for v in p),
                 "q20": ",".join("1" if v else "0" for v in t["q20"]) if t["q20"] is not None else ""}
            if "dense_X" in t:
                r.update(t["dense"].metrics((E.proba(f, t["dense_X"]) >= .5).astype(int)))
            rows.append(r)
    dest.write_text(json.dumps(rows, default=float))
    return rows


def tasks(which):
    from src.week18_dev_depth import tasks as depth_tasks
    import src.week18_tasks as T
    import src.week18_twins as W
    if which == "real":
        dt = {(t["task"], t["repeat"], t["fold"]): t for t in depth_tasks("real")}
        return [dt.get((t["task"], t["repeat"], t["fold"]), t) for t in T.all_real("DEV")]
    T_ = [W.twin_task(tw, d, n, rep) for tw in ("T_GP", "T_GBT", "T_NW", "T_QL", "T_TOBIT") for d, n in (("pooled", 433), ("OLD", 324), ("NEW", 108)) for rep in range(8)]
    return T_ + [W.twin_task("T_DEPTH", "OLD", 324, rep) for rep in range(8)]


def main(which, n_jobs=2):
    d = OUT / f"cache_{which}"; d.mkdir(parents=True, exist_ok=True)
    T = tasks(which); T.sort(key=lambda t: -(len(t["prior"]) + len(t["pool"])))
    res = Parallel(n_jobs=n_jobs, verbose=5)(delayed(job)(t, d / f"{t['task']}__r{t['repeat']:03d}_f{t['fold']}.json") for t in T)
    pd.DataFrame([r for rr in res for r in rr]).to_csv(OUT / f"headroom_{which}.csv.gz", index=False)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 2)
