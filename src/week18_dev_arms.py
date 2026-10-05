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
    # depth2: re-run of E2 with the analytic-gradient solver, E3 mixed-likelihood depth GP, E1 on partial-depth tasks;
    # "auto4" = per-step ML-II without a prior, ML-II every 4 paid queries (warm start) with a large prior
    "depth2": [(("G3", "auto4"), "margin"), (("Tobit", "auto4"), "margin"), (("MixGP", "auto4"), "margin"),
               (("MixGP", "auto4"), "straddle"), (("GPR_depth", "mlii"), "straddle")],
}


def hyper_for(t, hyper):
    big = len(t["prior"]) + 120 > 200 and len(t["prior"]) > 0
    if hyper == "auto4":
        return "mlii_k4" if big else "mlii"
    return "mlii_k8" if (big and hyper == "mlii") else hyper


def task_job(t, arms, out_dir, exp_name=""):
    from threadpoolctl import threadpool_limits
    import src.week18_engine as E
    dest = Path(out_dir) / f"{t['task']}__r{t['repeat']:03d}_f{t['fold']}.json"
    if dest.exists():
        return json.loads(dest.read_text())
    has_depth = np.isfinite(t["depth"][np.r_[t["prior"], t["pool"]].astype(int)]).any()
    rows = []
    if len(set(t["y"][t["pool"]]) | set(t["y"][t["prior"]])) < 2:
        rows = [{"task": t["task"], "repeat": t["repeat"], "fold": t["fold"], "degenerate": True}]
        dest.write_text(json.dumps(rows)); return rows
    with threadpool_limits(1):
        for (model, hyper), rule in arms:
            if model in ("Tobit", "GPR_depth") and not has_depth:
                continue
            if exp_name == "depth2" and model == "GPR_depth" and len(t["prior"]) == 0 and t["task"] != "R1_POOLED" and not t["task"].startswith("S1_"):
                continue                      # E1 baseline already run in Phase 2 on R3_OLD / R2rev (same seeds)
            if exp_name == "depth2" and model in ("G3", "Tobit") and len(t["prior"]) + 120 > 200 and len(t["prior"]) > 0:
                continue                      # large-prior tasks: reference = locked Phase 2 G3 + margin (mlii_k8); E2 not needed
            if exp_name == "depth2" and model in ("Tobit", "GPR_depth", "G3") and t["task"].startswith("S1_") and not has_depth:
                continue                      # binary twins: only the label-only MixGP non-inferiority check (G3 from Phase 2)
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
    if exp == "depth2":
        if which == "real":
            return depth_tasks("real") + [t for t in T.r3_new_tasks() if t["block"] == "DEV"]
        return depth_tasks("twins") + [W.twin_task(tw, d, n, rep) for tw in ("T_GP", "T_GBT", "T_NW", "T_QL") for d, n in (("pooled", 433), ("OLD", 324), ("NEW", 108)) for rep in range(8)]
    if which == "real":
        return T.all_real("DEV")
    return [W.twin_task(tw, d, n, rep) for tw in ("T_GP", "T_GBT", "T_NW", "T_QL", "T_TOBIT") for d, n in (("pooled", 433), ("OLD", 324), ("NEW", 108)) for rep in range(8)]


def main(exp, which, part="all"):
    """part: 'all', 'noprior' (tasks without free prior labels) or 'prior' (transfer tasks) — lets long runs be
    split into pieces that fit the 2 h background limit; the CSV is written from all cached tasks."""
    pdir = OUT / exp / f"cache_{which}"; pdir.mkdir(parents=True, exist_ok=True)
    T = tasks(exp, which); T.sort(key=lambda t: -(len(t["prior"]) + len(t["pool"])))
    if part in ("noprior", "prior"):
        T = [t for t in T if (len(t["prior"]) == 0) == (part == "noprior")]
    elif part.startswith("screen"):     # screening subset: real folds 1–2 of every DEV repeat, twins reps 0–3
        T = [t for t in T if (t["fold"] in (1, 2) if not t["task"].startswith("S1_") else t["repeat"] < 4)]
        if part == "screen_noprior":
            T = [t for t in T if len(t["prior"]) == 0]
    Parallel(n_jobs=7, verbose=5)(delayed(task_job)(t, EXPERIMENTS[exp], pdir, exp) for t in T)
    rows = [r for p in sorted(pdir.glob("*.json")) for r in json.loads(p.read_text())]
    pd.DataFrame(rows).to_csv(OUT / exp / f"{exp}_dev_{which}.csv.gz", index=False)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "all")
