"""Week 18 Phase 5 confirmation runner (one round = one locked real block + fresh twin reps + fresh stress seeds).

Usage: python -m src.week18_confirm <round_k> <real|twins|stress|stress_depth> [n_jobs]
Reads outputs/week18_independent_research/round_<k>/freeze_spec.json.  Refuses to run unless FREEZE_ROUND_<k>.md and
the spec are committed and present on origin/main unchanged (the freeze must be pushed before any confirmatory run).
Spec keys: round, real_block ("C1"/"C2"/"C3"), real_tasks, twin_tasks [[twin, dist, pool]], twin_reps, stress_round,
arms [{name, model, hyper, rule}] with hyper "phase2" (per-step ML-II; every 8 queries with a large prior — the
locked Phase 2 schedule), "auto4" (per-step; every 4 with a large prior) or an explicit engine schedule.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

ROOT = Path(__file__).resolve().parents[1]
W18 = ROOT / "outputs/week18_independent_research"


def check_freeze(k):
    rel = [f"outputs/week18_independent_research/FREEZE_ROUND_{k}.md", f"outputs/week18_independent_research/round_{k}/freeze_spec.json"]
    subprocess.run(["git", "fetch", "-q", "origin"], cwd=ROOT, check=True)
    for r in rel:
        on_remote = subprocess.run(["git", "cat-file", "-e", f"origin/main:{r}"], cwd=ROOT).returncode == 0
        if not on_remote:
            raise SystemExit(f"freeze not pushed: {r}")
        diff = subprocess.run(["git", "diff", "--quiet", "origin/main", "--", r], cwd=ROOT).returncode
        if diff != 0:
            raise SystemExit(f"local copy differs from the pushed freeze: {r}")


def schedule(t, hyper):
    big = len(t["prior"]) > 0 and len(t["prior"]) + 120 > 200
    if hyper == "phase2":
        return "mlii_k8" if big else "mlii"
    if hyper == "auto4":
        return "mlii_k4" if big else "mlii"
    return hyper


def job(t, arms, dest):
    from threadpoolctl import threadpool_limits
    import src.week18_engine as E
    from src.week18_baselines import budgets
    dest = Path(dest)
    if dest.exists():
        return json.loads(dest.read_text())
    if len(set(t["y"][t["pool"]]) | set(t["y"][t["prior"]])) < 2:
        rows = [{"task": t["task"], "repeat": t["repeat"], "fold": t["fold"], "degenerate": True}]
        dest.write_text(json.dumps(rows)); return rows
    rows = []
    with threadpool_limits(1):
        for a in arms:
            learner = (a["model"], schedule(t, a["hyper"]))
            out, L = E.run(t, learner, a["rule"], set(budgets(t)))
            for o in out:
                r = {"task": t["task"], "repeat": t["repeat"], "fold": t["fold"], "arm_name": a["name"], "model": learner[0], "hyper": learner[1],
                     "rule": a["rule"], "budget": o["budget"], "startup": o["startup"], "fp": o["fp"], "u": o["u"],
                     "rows": ",".join(map(str, t["test"])), "p": ",".join(f"{v:.5g}" for v in o["p"]),
                     "q20": ",".join("1" if v else "0" for v in t["q20"]) if t["q20"] is not None else ""}
                for key in ("NSD_0.1", "NSD_0.05", "ASSD", "dense_BA"):
                    if key in o:
                        r[key] = o[key]
                rows.append(r)
    dest.write_text(json.dumps(rows, default=float))
    return rows


def tasks(spec, which):
    if which == "real":
        import src.week18_tasks as T
        build = T.all_real_full_depth if spec.get("depth") == "full" else T.all_real_with_depth   # "full": OLD + NEW depth (after D1)
        return [t for t in build(spec["real_block"]) if t["task"] in spec["real_tasks"]]
    if which == "twins":
        import src.week18_twins as W
        return [W.twin_task(tw, d, n, rep) for tw, d, n in spec["twin_tasks"] for rep in spec["twin_reps"]]
    if which == "stress_depth":
        import src.week18_stress_depth as SD
        return SD.all_depth_stress(spec["stress_round"])
    import src.week18_stress as S
    return S.all_stress(spec["stress_round"])


def main(k, which, n_jobs=7):
    check_freeze(k)
    spec = json.loads((W18 / f"round_{k}/freeze_spec.json").read_text())
    d = W18 / f"round_{k}/cache_{which}"; d.mkdir(parents=True, exist_ok=True)
    T = tasks(spec, which); T.sort(key=lambda t: -(len(t["prior"]) + len(t["pool"])))
    res = Parallel(n_jobs=n_jobs, verbose=5)(delayed(job)(t, spec["arms"], d / f"{t['task']}__r{t['repeat']:03d}_f{t['fold']}.json") for t in T)
    pd.DataFrame([r for rr in res for r in rr]).to_csv(W18 / f"round_{k}/results_{which}.csv.gz", index=False)


if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 7)
