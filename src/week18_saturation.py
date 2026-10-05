"""Week 18 theory check P-T18-2: saturation budget vs pool size (SEMI-SYNTHETIC, development reps).

Truths T_GP and T_DEPTH-free binary T_GBT on the pooled input distribution; pool sizes N ∈ {108, 216, 433, 866};
G3 + margin (ML-II every 4 paid queries, warm start) to B = min(N, 200), NSD_0.1 and dense BA every 8 queries, and the
full-pool G3 ceiling.  Saturation budget = first budget at which the rep's NSD reaches 95% of the way from its B16
value to the ceiling.  P-T18-2 predicts growth like N^{(d−1)/(α+d−1)} (0.6–0.75 for α ∈ [1, 2], d = 4), or like
log N for index-like boundaries.
Usage: python -m src.week18_saturation [n_jobs]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week18_independent_research/phase4/saturation"
SIZES = (108, 216, 433, 866)


def job(twin, n, rep):
    from threadpoolctl import threadpool_limits
    import src.week18_engine as E
    import src.week18_twins as W
    dest = OUT / f"cache/{twin}_{n}_r{rep}.json"
    if dest.exists():
        return json.loads(dest.read_text())
    t = W.twin_task(twin, "pooled", n, 900 + rep, test_size=28)   # reps 900+: theory checks only (confirmation uses 100k..100k+7)
    rows = []
    with threadpool_limits(1):
        try:
            bmax = min(n, 200)
            out, L = E.run(t, ("G3", "mlii_k4"), "margin", set(range(16, bmax + 1, 8)))
            rows += [{"twin": twin, "N": n, "rep": rep, "budget": o["budget"], "NSD": o["NSD_0.1"], "dense_BA": o["dense_BA"], "fp": o["fp"]} for o in out]
            f = E.fit_learner(("G3", "mlii"), t, list(map(int, t["pool"])), None, {"kernel": None, "b0": n})
            m = t["dense"].metrics((E.proba(f, t["dense_X"]) >= .5).astype(int))
            rows.append({"twin": twin, "N": n, "rep": rep, "budget": -1, "NSD": m["NSD_0.1"], "dense_BA": m["dense_BA"], "fp": float(f.gp.mode_fp_)})
        except E.DegenerateTask:
            pass
    dest.parent.mkdir(parents=True, exist_ok=True); dest.write_text(json.dumps(rows, default=float))
    return rows


def summarize(df):
    out = []
    for (tw, n, rep), g in df.groupby(["twin", "N", "rep"]):
        ceil = g[g.budget == -1].NSD
        c = g[g.budget > 0].sort_values("budget")
        if not len(ceil) or not len(c):
            continue
        c0, cmax = c.NSD.iloc[0], float(ceil.iloc[0])
        thr = c0 + .95 * (cmax - c0)
        hit = c[c.NSD >= thr]
        out.append({"twin": tw, "N": n, "rep": rep, "ceiling": cmax, "B16": c0, "B_end": c.NSD.iloc[-1],
                    "B_sat": float(hit.budget.iloc[0]) if len(hit) else np.inf})
    s = pd.DataFrame(out)
    fit = []
    for tw, g in s.groupby("twin"):
        m = g.groupby("N").B_sat.median()
        ok = np.isfinite(m.to_numpy())
        if ok.sum() >= 2:
            slope = np.polyfit(np.log(m.index.to_numpy(float)[ok]), np.log(m.to_numpy()[ok]), 1)[0]
            fit.append({"twin": tw, "loglog_slope": float(slope), **{f"Bsat_med_N{k}": float(v) for k, v in m.items()}})
    return s, pd.DataFrame(fit)


def main(n_jobs=7):
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(tw, n, r) for tw in ("T_GP", "T_GBT") for n in SIZES[::-1] for r in range(6)]
    res = Parallel(n_jobs=n_jobs, verbose=5)(delayed(job)(*a) for a in jobs)
    df = pd.DataFrame([r for rr in res for r in rr]); df.to_csv(OUT / "saturation_curves.csv", index=False)
    s, fit = summarize(df); s.to_csv(OUT / "saturation_summary.csv", index=False); fit.to_csv(OUT / "saturation_fit.csv", index=False)
    return s, fit


if __name__ == "__main__":
    s, fit = main(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
    print(s.groupby(["twin", "N"])[["ceiling", "B16", "B_end", "B_sat"]].median().round(3).to_string()); print(fit.round(3).to_string())
