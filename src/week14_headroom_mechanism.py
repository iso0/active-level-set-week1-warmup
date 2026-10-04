"""Week 14 Study 4c — what does the NSD oracle do that margin does not? (CONTROLLED SYNTHETIC, descriptive)"""
from pathlib import Path
import json
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from scipy.spatial import cKDTree
from src.week13_synthetic import DenseTruth, LaplaceGPC, latent
from src.week13_synthetic_al import calibrated, maximin_order, noisy_labels, to_box

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week14_research_program/synthetic/headroom"
HYP = json.loads((ROOT / "outputs/week13_boundary_evaluation_and_mechanisms/synthetic/oracle_hyperparameters.json").read_text())


def run(scn, rep, n_pool=108, sigma=.5):
    sc = calibrated(scn); hyp = HYP[f"{scn}_s{sigma}"]
    rng = np.random.default_rng([14, 4, n_pool, rep, ("BAL", "OLD", "NEW").index(scn)])
    u_pool = sc.sample(n_pool, rng); sc.sample(int(round(n_pool / .8)), rng)
    y_pool = noisy_labels(u_pool, sc, sigma, rng); z_pool = to_box(u_pool, sc)
    f_pool = latent(u_pool, sc)
    small = DenseTruth(sc, n=3000, seed=11)
    btree = cKDTree(small.z[small.true_boundary])
    order = maximin_order(z_pool, np.random.default_rng([14, 4, rep]))
    start = list(order[:8]); k = 8
    while len(set(y_pool[start])) < 2:
        start.append(int(order[k])); k += 1
    gp = lambda idx: LaplaceGPC(hyp["ls"], hyp["var"]).fit(z_pool[idx], y_pool[idx])
    rows = []
    for policy in ("margin", "oracle_NSD"):
        L = list(start)
        while len(L) < 40:
            cands = np.setdiff1d(np.arange(n_pool), L)
            if policy == "margin":
                p = gp(np.asarray(L)).proba(z_pool[cands]); L.append(int(cands[np.argmin(np.abs(p - .5))]))
            else:
                vals = [small.metrics((gp(np.asarray(L + [int(c)])).latent_mean(small.z) > 0).astype(int))["NSD_0.1"] for c in cands]
                L.append(int(cands[int(np.argmax(vals))]))
        sel = np.asarray(L[len(start):])
        # boundary proximity, label-noise exposure and along-boundary coverage of the acquired points
        d_bd = btree.query(z_pool[sel])[0]
        cover = cKDTree(z_pool[L]).query(small.z[small.true_boundary])[0]
        flipped = (y_pool[sel] != (f_pool[sel] > 0)).mean()
        rows.append({"scenario": scn, "rep": rep, "policy": policy, "median_dist_to_true_boundary": float(np.median(d_bd)),
                     "frac_acquired_with_flipped_label": float(flipped),
                     "boundary_coverage_median_dist": float(np.median(cover)), "boundary_coverage_q90": float(np.quantile(cover, .9)),
                     "minority_frac": float((y_pool[sel] == (0 if scn == "NEW" else 1)).mean())})
    return rows


if __name__ == "__main__":
    res = Parallel(n_jobs=3)(delayed(run)(s, r) for s in ("BAL", "OLD", "NEW") for r in range(4))
    df = pd.DataFrame([x for rows in res for x in rows]); df.to_csv(OUT / "headroom_mechanism.csv", index=False)
    print(df.groupby(["scenario", "policy"]).mean(numeric_only=True).drop(columns="rep").round(3).to_string())
