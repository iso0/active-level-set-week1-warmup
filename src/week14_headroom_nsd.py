"""Week 14 Study 4b — true-objective oracle: greedy maximisation of dense-truth NSD (CONTROLLED SYNTHETIC).

The oracle sees the noise-free boundary through a 3,000-point dense reference set (a cheat) and
greedily picks the pool case that maximises NSD_0.1 of the refitted model.  This measures acquisition
headroom on the estimand itself, not on a finite evaluation pool.
"""
from pathlib import Path
import json
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from src.week13_synthetic import DenseTruth, LaplaceGPC
from src.week13_synthetic_al import calibrated, maximin_order, noisy_labels, to_box

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week14_research_program/synthetic/headroom"
HYP = json.loads((ROOT / "outputs/week13_boundary_evaluation_and_mechanisms/synthetic/oracle_hyperparameters.json").read_text())
BUDGETS = tuple(range(16, 81, 8))


def run(scn, rep, n_pool=108, sigma=.5):
    sc = calibrated(scn); hyp = HYP[f"{scn}_s{sigma}"]
    rng = np.random.default_rng([14, 4, n_pool, rep, ("BAL", "OLD", "NEW").index(scn)])
    u_pool = sc.sample(n_pool, rng); sc.sample(int(round(n_pool / .8)), rng)
    y_pool = noisy_labels(u_pool, sc, sigma, rng)
    z_pool = to_box(u_pool, sc)
    small = DenseTruth(sc, n=3000, seed=11)     # oracle's objective
    big = DenseTruth(sc, n=8000, seed=5)        # reporting (same as Study 4)
    order = maximin_order(z_pool, np.random.default_rng([14, 4, rep]))
    L = list(order[:8]); k = 8
    while len(set(y_pool[L])) < 2:
        L.append(int(order[k])); k += 1
    gp = lambda idx: LaplaceGPC(hyp["ls"], hyp["var"]).fit(z_pool[idx], y_pool[idx])
    rows = []
    while len(L) < 80:
        cands = np.setdiff1d(np.arange(n_pool), L)
        vals = [small.metrics((gp(np.asarray(L + [int(c)])).latent_mean(small.z) > 0).astype(int))["NSD_0.1"] for c in cands]
        L.append(int(cands[int(np.argmax(vals))]))
        if len(L) in BUDGETS:
            m = gp(np.asarray(L))
            r = big.metrics((m.latent_mean(big.z) > 0).astype(int))
            rows.append({"scenario": scn, "rep": rep, "policy": "oracle_NSD", "budget": len(L), "NSD_0.1": r["NSD_0.1"], "ASSD": r["ASSD"]})
    return rows


if __name__ == "__main__":
    res = Parallel(n_jobs=7, verbose=2)(delayed(run)(s, r) for s in ("BAL", "OLD", "NEW") for r in range(6))
    df = pd.DataFrame([x for rows in res for x in rows])
    df.to_csv(OUT / "headroom_oracle_nsd.csv", index=False)
    print(df.groupby(["scenario", "budget"]).NSD_0.mean().round(3).to_string() if False else df.groupby(["scenario", "budget"])["NSD_0.1"].mean().round(3).to_string())
