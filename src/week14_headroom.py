"""Week 14 Study 4 — how much room is there for acquisition? (CONTROLLED SYNTHETIC)

On the Week 13 generator (sigma = 0.5, pool 108 / 324, model G with oracle fixed hyperparameters):
  * random and margin paths (as Week 13),
  * a greedy ORACLE path that, at each step, queries the pool case maximising balanced accuracy on
    the evaluation pool (it cheats with evaluation labels; it is an empirical upper reference, not
    the optimum),
  * replace-one sensitivity beta_b estimated along the margin path by random swaps (Prop. H1 uses
    the supremum; the average reported here is only indicative).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from src.week13_synthetic import DenseTruth, LaplaceGPC
from src.week13_synthetic_al import calibrated, maximin_order, noisy_labels, to_box

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week14_research_program/synthetic/headroom"
HYP = json.loads((ROOT / "outputs/week13_boundary_evaluation_and_mechanisms/synthetic/oracle_hyperparameters.json").read_text())
BUDGETS = tuple(range(16, 81, 8))


def ba(y, yh):
    return float((np.mean(yh[y == 1] == 1) + np.mean(yh[y == 0] == 0)) / 2)


def run(scn, n_pool, rep, sigma=.5):
    sc = calibrated(scn)
    hyp = HYP[f"{scn}_s{sigma}"]
    rng = np.random.default_rng([14, 4, n_pool, rep, ("BAL", "OLD", "NEW").index(scn)])
    u_pool, u_eval = sc.sample(n_pool, rng), sc.sample(int(round(n_pool / .8)), rng)
    y_pool, y_eval = noisy_labels(u_pool, sc, sigma, rng), noisy_labels(u_eval, sc, sigma, rng)
    z_pool, z_eval = to_box(u_pool, sc), to_box(u_eval, sc)
    dense = DenseTruth(sc, n=8000, seed=5)
    order = maximin_order(z_pool, np.random.default_rng([14, 4, rep]))
    start = list(order[:8])
    k = 8
    while len(set(y_pool[start])) < 2:
        start.append(int(order[k])); k += 1
    gp = lambda idx: LaplaceGPC(hyp["ls"], hyp["var"]).fit(z_pool[idx], y_pool[idx])
    rows = []
    for policy in ("random", "margin", "oracle"):
        prng = np.random.default_rng([14, 4, rep, ("random", "margin", "oracle").index(policy)])
        L = list(start)
        while len(L) < 80:
            cands = np.setdiff1d(np.arange(n_pool), L)
            if policy == "random":
                L.append(int(prng.choice(cands)))
            elif policy == "margin":
                p = gp(np.asarray(L)).proba(z_pool[cands])
                L.append(int(cands[np.argmin(np.abs(p - .5))]))
            else:
                best, bv = None, -1
                for c in cands:
                    m = gp(np.asarray(L + [int(c)]))
                    v = ba(y_eval, (m.latent_mean(z_eval) > 0).astype(int))
                    if v > bv:
                        best, bv = int(c), v
                L.append(best)
            b = len(L)
            if b in BUDGETS:
                m = gp(np.asarray(L))
                r = {"scenario": scn, "n_pool": n_pool, "rep": rep, "policy": policy, "budget": b,
                     "eval_BA": ba(y_eval, (m.latent_mean(z_eval) > 0).astype(int))}
                r.update({k2: v for k2, v in dense.metrics((m.latent_mean(dense.z) > 0).astype(int)).items() if k2 in ("NSD_0.1", "ASSD")})
                if policy == "margin":   # indicative replace-one sensitivity at this budget
                    deltas = []
                    for _ in range(30):
                        x = prng.choice(L)
                        zc = prng.choice(np.setdiff1d(np.arange(n_pool), L))
                        L2 = [i for i in L if i != x] + [int(zc)]
                        m2 = gp(np.asarray(L2))
                        deltas.append(abs(r["eval_BA"] - ba(y_eval, (m2.latent_mean(z_eval) > 0).astype(int))))
                    r["swap_sensitivity_mean"] = float(np.mean(deltas))
                    r["swap_sensitivity_max"] = float(np.max(deltas))
                rows.append(r)
    m = gp(np.arange(n_pool))
    rows.append({"scenario": scn, "n_pool": n_pool, "rep": rep, "policy": "CEILING", "budget": n_pool,
                 "eval_BA": ba(y_eval, (m.latent_mean(z_eval) > 0).astype(int))})
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(s, n, r) for s in ("BAL", "OLD", "NEW") for n in (108,) for r in range(12)]
    res = Parallel(n_jobs=7, verbose=2)(delayed(run)(*j) for j in jobs)
    df = pd.DataFrame([x for rows in res for x in rows])
    df.to_csv(OUT / "headroom_oracle.csv", index=False)
    print(df.groupby(["scenario", "policy", "budget"])[["eval_BA", "NSD_0.1", "swap_sensitivity_mean", "swap_sensitivity_max"]].mean().round(3).to_string())


if __name__ == "__main__":
    main()
