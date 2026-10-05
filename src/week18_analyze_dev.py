"""Week 18 Phase 3 analysis of development experiments against the Phase 2 baselines (DEVELOPMENT only).

Usage: python -m src.week18_analyze_dev <experiment> [ref_arm]
Reads phase3/<exp>/<exp>_dev_{real,twins}.csv.gz (or the per-task caches if the CSV is absent), joins the Phase 2
baselines of the same tasks, and writes phase3/<exp>/{aulc,contrasts,qtt}_{real,twins}.csv.  Real endpoint: pooled
per-repeat BA AULC (+ q20 AULC); twins: NSD_0.1 AULC.  Reference arm: G3 + margin with the same ML-II schedule as
the candidate when present in the experiment, otherwise the Phase 2 G3 + margin.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.week18_metrics import aulc, contrast, qtt, real_curves

ROOT = Path(__file__).resolve().parents[1]
W18 = ROOT / "outputs/week18_independent_research"


def load(exp, which):
    f = W18 / f"phase3/{exp}/{exp}_dev_{which}.csv.gz"
    if f.exists():
        return pd.read_csv(f)
    rows = [r for p in sorted((W18 / f"phase3/{exp}/cache_{which}").glob("*.json")) for r in json.loads(p.read_text())]
    return pd.DataFrame(rows)


def y_of_tasks(tasks):
    import src.week18_tasks as T
    from src.week18_dev_depth import tasks as dt
    out = {}
    for t in T.all_real("DEV") + dt("real"):
        out.setdefault(t["task"], t["y"])
    return out


def analyze(exp, which):
    d = load(exp, which)
    if "degenerate" in d:
        d = d[d.degenerate != True]
    d = d.dropna(subset=["model"])
    base = pd.read_csv(W18 / f"phase2/baselines_{which}.csv.gz")
    base = base[base.task.isin(d.task.unique())].dropna(subset=["model"])
    keys = set(zip(d.task, d.repeat, d.fold))               # pair with the same runs (screening subsets)
    base = base[[k in keys for k in zip(base.task, base.repeat, base.fold)]]
    if which == "real":
        y_of = y_of_tasks(d.task.unique())
        cur = pd.concat([real_curves(d, y_of), real_curves(base, y_of)]).drop_duplicates(["task", "repeat", "arm", "budget"])
        key = "BA"
    else:
        allr = pd.concat([d, base]); allr["arm"] = allr.model + "|" + allr.hyper + "|" + allr.rule
        cur = allr.groupby(["task", "repeat", "arm", "budget"], as_index=False)[["NSD_0.1", "dense_BA"]].mean()
        key = "NSD_0.1"
    au = aulc(cur, key)
    if which == "real":
        au = au.merge(aulc(cur, "q20"), on=["task", "repeat", "arm"], how="left")
    cons, qs = [], []
    for task, g in au.groupby("task"):
        arms = set(g.arm)
        for arm in sorted(arms):
            sched = arm.split("|")[1]
            ref = f"G3|{sched}|margin" if f"G3|{sched}|margin" in arms else next((a for a in ("G3|mlii|margin", "G3|mlii_k8|margin") if a in arms), None)
            if ref is None or arm == ref:
                continue
            cons.append(contrast(g, f"{key}_AULC", arm, ref))
            if which == "real":
                cons.append(contrast(g, "q20_AULC", arm, ref))
        ref0 = next((a for a in ("G3|mlii|margin", "G3|mlii_k8|margin") if a in arms), None)
        if ref0:
            q = qtt(cur[cur.task == task], key, ref0); q["ref"] = ref0; qs.append(q)
    con = pd.concat(cons, ignore_index=True)
    q = pd.concat(qs, ignore_index=True)
    qm = q.groupby(["task", "target_at", "arm"]).agg(qtt_median=("qtt", "median"), censored=("qtt", lambda s: float(np.isinf(s).mean()))).reset_index()
    out = W18 / f"phase3/{exp}"
    au.to_csv(out / f"aulc_{which}.csv", index=False); con.to_csv(out / f"contrasts_{which}.csv", index=False); qm.to_csv(out / f"qtt_{which}.csv", index=False)
    fp = d.fp.astype(float)
    conv = {"fits": int(len(fp)), "fp_gt_1e-6": int((fp > 1e-6).sum()), "fp_max": float(fp.max())}
    return au, con, qm, conv


if __name__ == "__main__":
    exp = sys.argv[1]
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
    for which in sys.argv[2:] or ["real", "twins"]:
        au, con, qm, conv = analyze(exp, which)
        k = "BA_AULC" if which == "real" else "NSD_0.1_AULC"
        print(which, conv)
        print(au.pivot_table(index="task", columns="arm", values=k).round(3).to_string())
        print(con[con.metric == k].round(3).to_string())
        if which == "real":
            print(con[con.metric == "q20_AULC"].round(3).to_string())
        print(qm[qm.target_at > 60].round(2).to_string())
