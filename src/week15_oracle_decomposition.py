"""Week 15 Step A — how much of the Week 14 true-boundary headroom is attainable without label peeking?

Week 14's NSD oracle (Oracle-R) chose the candidate maximizing NSD *after seeing the candidate's realized
noisy label*.  Oracle-E knows the true latent f and the noise law P(y = 1 | u) = Phi(f(u)/sigma) but not
the realization: it maximizes the expected NSD over both label outcomes.  Oracle-E is the best one-step
greedy design available to a method with perfect knowledge of the truth; Oracle-R - Oracle-E is pure
label-peeking (unattainable by any non-cheating rule).
Pools, seeds, startup, model and reporting dense set are identical to Week 14 Study 4/4b (reps 0-5).
CONTROLLED SYNTHETIC (Week 13 generator = development family for Week 15).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.special import ndtr

from src.week13_synthetic import DenseTruth, LaplaceGPC, latent
from src.week13_synthetic_al import calibrated, maximin_order, noisy_labels, to_box

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week15_boundary_acquisition/development"
HYP = json.loads((ROOT / "outputs/week13_boundary_evaluation_and_mechanisms/synthetic/oracle_hyperparameters.json").read_text())
BUDGETS = tuple(range(16, 81, 8))


def run(scn, rep, n_pool=108, sigma=.5):
    sc = calibrated(scn); hyp = HYP[f"{scn}_s{sigma}"]
    rng = np.random.default_rng([14, 4, n_pool, rep, ("BAL", "OLD", "NEW").index(scn)])
    u_pool = sc.sample(n_pool, rng); sc.sample(int(round(n_pool / .8)), rng)
    y_pool = noisy_labels(u_pool, sc, sigma, rng)
    z_pool = to_box(u_pool, sc)
    p_true = ndtr(latent(u_pool, sc) / sigma)
    small = DenseTruth(sc, n=3000, seed=11)
    big = DenseTruth(sc, n=8000, seed=5)
    order = maximin_order(z_pool, np.random.default_rng([14, 4, rep]))
    L = list(order[:8]); k = 8
    while len(set(y_pool[L])) < 2:
        L.append(int(order[k])); k += 1
    def nsd_if(labels_idx, labels_y):
        gp = LaplaceGPC(hyp["ls"], hyp["var"]).fit(z_pool[labels_idx], labels_y)
        return small.metrics((gp.latent_mean(small.z) > 0).astype(int))["NSD_0.1"]
    rows = []
    while len(L) < 80:
        cands = np.setdiff1d(np.arange(n_pool), L)
        base_idx = np.asarray(L); base_y = y_pool[base_idx]
        vals = []
        for c in cands:
            idx = np.r_[base_idx, c]
            v1 = nsd_if(idx, np.r_[base_y, 1]); v0 = nsd_if(idx, np.r_[base_y, 0])
            vals.append(p_true[c] * v1 + (1 - p_true[c]) * v0)
        c = int(cands[int(np.argmax(vals))])
        L.append(c)
        if len(L) in BUDGETS:
            gp = LaplaceGPC(hyp["ls"], hyp["var"]).fit(z_pool[L], y_pool[L])
            r = big.metrics((gp.latent_mean(big.z) > 0).astype(int))
            rows.append({"scenario": scn, "rep": rep, "policy": "oracle_E", "budget": len(L), "NSD_0.1": r["NSD_0.1"], "ASSD": r["ASSD"],
                         "flipped_acquired_so_far": float(np.mean(y_pool[L] != (latent(u_pool[L], sc) > 0)))})
    return rows


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    res = Parallel(n_jobs=7, verbose=2)(delayed(run)(s, r) for s in ("BAL", "OLD", "NEW") for r in range(6))
    df = pd.DataFrame([x for rows in res for x in rows])
    df.to_csv(OUT / "oracle_E.csv", index=False)
    w14 = ROOT / "outputs/week14_research_program/synthetic/headroom"
    h = pd.read_csv(w14 / "headroom_oracle.csv"); h = h[(h.rep < 6) & h.policy.isin(["random", "margin"])]
    o = pd.read_csv(w14 / "headroom_oracle_nsd.csv")
    allp = pd.concat([h[["scenario", "rep", "policy", "budget", "NSD_0.1"]], o.assign(policy="oracle_R")[["scenario", "rep", "policy", "budget", "NSD_0.1"]],
                      df[["scenario", "rep", "policy", "budget", "NSD_0.1"]]])
    t = allp.groupby(["scenario", "policy"])["NSD_0.1"].mean().unstack()
    t["attainable_headroom_E_minus_margin"] = t.oracle_E - t.margin
    t["peeking_R_minus_E"] = t.oracle_R - t.oracle_E
    t.to_csv(OUT / "oracle_decomposition.csv")
    print(t.round(3).to_string())
