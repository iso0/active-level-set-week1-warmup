"""Diagnostic for the one Track 1 extension run that does not reproduce its Week 18 cache (G3 margin, R1_POOLED
repeat 8 fold 1, budgets 24-80).  Re-runs the historical engine loop (src.week18_engine.run, unmasked task as in
Week 18) with 1 and with 4 BLAS threads and compares paid sequences and grid-budget predictions with the cache and
with the ledgered extension run.  Diagnostic only: 2 x 73 G3 fits, counted in the attempt ledger; nothing replaces
the frozen result.

Step: python -m src.week20_track1_ext_g3_divergence
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import src.week20_track1_al as A
from src.week20_track1_ext import OUTX, _load, build_tasks_x


def main():
    import src.week18_engine as E
    from threadpoolctl import threadpool_limits
    t = next(t for t in build_tasks_x() if (t["task"], t["repeat"], t["fold"]) == ("R1_POOLED", 8, 1))
    grid = list(A.grid("R1_POOLED"))
    cache = {int(r["budget"]): np.array(r["p"].split(","), float) for r in json.loads((A.W18 / "phase2/cache_real/R1_POOLED__r008_f1.json").read_text())
             if (r["model"], r["hyper"], r["rule"]) == ("G3", "mlii", "margin") and int(r["budget"]) <= A.BMAX}
    ours = _load(t, "G3_MARGIN")
    ours_L = [int(np.flatnonzero(t["ids"] == r["sim_id"])[0]) for r in sorted(ours["ledger"], key=lambda r: r["query_index"])]
    ours_p = {p["budget"]: np.asarray(p["p"]) for p in ours["preds"]}
    rows, seqs = [], {"ledgered_extension_run": ours_L}
    for threads in (1, 4):
        with threadpool_limits(limits=threads):
            out, L = E.run(t, ("G3", "mlii"), "margin", grid)
        seqs[f"engine_run_{threads}_threads"] = [int(i) for i in L]
        for r in out:
            b = int(r["budget"])
            rows.append({"variant": f"engine_run_{threads}_threads", "budget": b, "max_abs_dp_vs_cache": float(np.abs(np.asarray(r["p"]) - cache[b]).max()),
                         "max_abs_dp_vs_ledgered": float(np.abs(np.asarray(r["p"]) - ours_p[b]).max())})
    for b in grid:
        rows.append({"variant": "ledgered_extension_run", "budget": b, "max_abs_dp_vs_cache": float(np.abs(ours_p[b] - cache[b]).max()), "max_abs_dp_vs_ledgered": 0.0})
    d = pd.DataFrame(rows)
    first = {k: next((i + 1 for i, (x, y) in enumerate(zip(v, ours_L)) if x != y), None) for k, v in seqs.items()}
    d.to_csv(OUTX / "DIAG_g3_R1_POOLED_r8f1_divergence.csv", index=False, lineterminator="\n")
    summ = {"first_query_differing_from_ledgered_run": first, "n_fits": 2 * (A.BMAX - len(E.startup(t)) + 1)}
    (OUTX / "DIAG_g3_R1_POOLED_r8f1_divergence.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    print(d.pivot(index="budget", columns="variant", values="max_abs_dp_vs_cache").round(6).to_string()); print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
