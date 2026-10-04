"""Week 15 diagnostic — can a legal (non-cheating) criterion see what the expectation oracle sees?

At states visited by margin paths (development generator, sigma = 0.5, budgets 24/40/60), compute for
every candidate:
  * ORACLE-E gain   = E_{y ~ P_true}[NSD_true(D ∪ (c,y))] − NSD_true(D)    (uses the truth; reference)
  * legal scores    = margin (−|p − 1/2|), BALD, VSUR, EBR-D look-ahead reductions (model only)
and report Spearman rank correlation with the oracle gain and the regret of each criterion's top choice
(oracle gain of the best candidate minus that of the chosen one).
"""
from pathlib import Path
import json
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from scipy.special import ndtr
from scipy.stats import spearmanr
from src.week13_synthetic import DenseTruth, LaplaceGPC, latent
from src.week13_synthetic_al import calibrated, noisy_labels, to_box
from src.week14_noise_acquisition import bald, latent_mv
from src.week15_al import start_design
from src.week15_ebr import knn_graph, lookahead_scores

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week15_boundary_acquisition/development"
HYP = json.loads((ROOT / "outputs/week14_research_program/synthetic/noise_acquisition/hyperparameters.json").read_text())


def state(scn, rep, sigma=.5, n_pool=108):
    sc = calibrated(scn); hyp = HYP[f"{scn}_s{sigma}"]
    rng = np.random.default_rng([15, int(sigma * 10), n_pool, rep, ("BAL", "OLD", "NEW").index(scn)])
    u_pool, u_eval = sc.sample(n_pool, rng), sc.sample(int(round(n_pool / .8)), rng)
    y_pool = noisy_labels(u_pool, sc, sigma, rng)
    z_pool = to_box(u_pool, sc)
    p_true = ndtr(latent(u_pool, sc) / sigma)
    small = DenseTruth(sc, n=3000, seed=11)
    Zref = np.random.default_rng([15, 99]).random((400, 4)); Eref = knn_graph(Zref, 8)
    L = start_design(z_pool, y_pool, [15, rep, 2])
    rows = []
    while len(L) <= 60:
        gp = LaplaceGPC(hyp["ls"], hyp["var"]).fit(z_pool[L], y_pool[L])
        cands = np.setdiff1d(np.arange(n_pool), L)
        if len(L) in (24, 40, 60):
            nsd = lambda idx, yy: small.metrics((LaplaceGPC(hyp["ls"], hyp["var"]).fit(z_pool[idx], yy).latent_mean(small.z) > 0).astype(int))["NSD_0.1"]
            base = nsd(np.asarray(L), y_pool[L])
            og = np.array([p_true[c] * nsd(np.r_[L, c], np.r_[y_pool[L], 1]) + (1 - p_true[c]) * nsd(np.r_[L, c], np.r_[y_pool[L], 0]) - base for c in cands])
            mu, var = latent_mv(gp, z_pool[cands])
            p = 1 / (1 + np.exp(-mu / np.sqrt(1 + np.pi * var / 8)))
            scores = {"margin": -np.abs(p - .5), "bald": bald(mu, var),
                      "vsur": lookahead_scores(z_pool, y_pool, L, cands, hyp, Zref, Eref, "VSUR")[0],
                      "ebrd": lookahead_scores(z_pool, y_pool, L, cands, hyp, Zref, Eref, "EBRD")[0],
                      "true_label_reliability": np.maximum(p_true[cands], 1 - p_true[cands])}
            for k, v in scores.items():
                rows.append({"scenario": scn, "rep": rep, "budget": len(L), "criterion": k,
                             "spearman_with_oracle_gain": float(spearmanr(v, og).statistic),
                             "regret": float(og.max() - og[int(np.argmax(v))]), "oracle_best_gain": float(og.max()),
                             "oracle_gain_of_choice": float(og[int(np.argmax(v))])})
        if len(L) == 60:
            break
        mu_, var_ = latent_mv(gp, z_pool[cands]); L.append(int(cands[np.argmin(np.abs(1 / (1 + np.exp(-mu_ / np.sqrt(1 + np.pi * var_ / 8))) - .5))]))
    return rows


if __name__ == "__main__":
    res = Parallel(n_jobs=7, verbose=2)(delayed(state)(s, r) for s in ("BAL", "OLD", "NEW") for r in range(6))
    df = pd.DataFrame([x for rows in res for x in rows]); OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "oracle_alignment.csv", index=False)
    print(df.groupby(["scenario", "criterion"])[["spearman_with_oracle_gain", "regret", "oracle_gain_of_choice", "oracle_best_gain"]].mean().round(4).to_string())
