"""Week 17 Phase 1B/1D — deterministic boundaries seen through a logistic likelihood (CONTROLLED SYNTHETIC).

For every Week 16 state (regenerated margin paths, same seeds, safeguarded fits) and every candidate whose
expectation-oracle value V_true was computed in Week 16 (`headroom/candidates.csv.gz`), compute four
acquisition values from the same Laplace posterior:
  margin_pred : −|p − ½|,  p = Φ(μ/√(s² + 8/π))       (what the thesis's margin maximizes)
  margin_lat  : −|μ|/s                                  (latent-sign uncertainty only)
  PEER_noisy  : one-step Hamming value with probit observation noise 8/π (Week 16)
  PEER_det    : the same with a noise-free observation O_j = sign(f_j)
and, per state, the share of predictive variance at the reference-cloud points near the true boundary that is
attributed to observation noise, 8/π / (s² + 8/π)  ("aleatoric share").
Alignment = per-state Spearman with V_true (Hamming on the reference cloud and NSD) and the true value of each
rule's argmax.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.special import ndtr
from scipy.stats import spearmanr

from src.week15_ebr import bvn_lower
from src.week16_cells import ALL_CELLS, build, cell_key, margin_states, pars
from src.week16_headroom import BUDGETS16
from src.week16_peer import GaussPost, Model

ROOT = Path(__file__).resolve().parents[1]
W16 = ROOT / "outputs/week16_theory_meets_data/headroom"
OUT = ROOT / "outputs/week17_model_and_acquisition/phase1"
NOISE = 8 / np.pi


def peer(post: GaussPost, Zt, Zc, noise):
    mt, vt = post.mean_var(Zt); mc, vc = post.mean_var(Zc)
    C = post.cross_cov(Zt, Zc)
    st, sg = np.sqrt(vt), np.sqrt(vc + noise)
    rho = np.clip(C / (st[:, None] * sg[None, :]), -.999999, .999999)
    at, ac = mt / st, mc / sg
    pT, pO = ndtr(at), ndtr(ac)
    A, B = np.broadcast_to(at[:, None], C.shape), np.broadcast_to(ac[None, :], C.shape)
    p11 = bvn_lower(A.ravel(), B.ravel(), rho.ravel()).reshape(C.shape)
    ET = 2 * pT - 1; ETO = 4 * p11 - 2 * pT[:, None] - 2 * pO[None, :] + 1
    return .5 * np.maximum(np.abs(ETO) - np.abs(ET)[:, None], 0).sum(0)


def one(fam, cfg, rep, P, cand):
    c = build(fam, cfg, rep, P); m = Model.from_hyp(c["hyp"])
    states, _ = margin_states(c, BUDGETS16, m, ())
    key = cell_key(fam, cfg); rows, srows = [], []
    for b, L in states.items():
        g = cand[(cand.cell == key) & (cand.rep == rep) & (cand.budget == b)]
        if g.empty:
            continue
        post = m.fit(c["z_pool"][L], c["y_pool"][L])
        J = g.cand.to_numpy(int); Zc = c["z_pool"][J]
        mu, v = post.mean_var(Zc); s = np.sqrt(v)
        vals = {"margin_pred": -np.abs(ndtr(mu / np.sqrt(v + NOISE)) - .5), "margin_lat": -np.abs(mu) / s,
                "PEER_noisy": peer(post, c["zref"], Zc, NOISE), "PEER_det": peer(post, c["zref"], Zc, 1e-10)}
        mr, vr = post.mean_var(c["zref"])
        near = np.abs(mr) / np.sqrt(vr + NOISE) < .5          # reference points inside the predicted band
        tb = c["tref"]
        srows.append({"cell": key, "family": fam, "rep": rep, "budget": b,
                      "aleatoric_share_band": float(np.mean(NOISE / (vr[near] + NOISE))) if near.any() else np.nan,
                      "band_points": int(near.sum()), "median_s_band": float(np.median(np.sqrt(vr[near]))) if near.any() else np.nan})
        for rule, val in vals.items():
            j = int(np.argmax(val))
            r = {"cell": key, "family": fam, "rep": rep, "budget": b, "rule": rule}
            for vt in ("Vt_ham_ref", "Vt_nsd"):
                tv = g[vt].to_numpy()
                r[f"rho_{vt}"] = float(spearmanr(val, tv).statistic) if np.ptp(tv) > 0 and np.ptp(val) > 0 else np.nan
                r[f"pick_{vt}"] = float(tv[j]); r[f"max_{vt}"] = float(tv.max()); r[f"rand_{vt}"] = float(tv.mean())
            rows.append(r)
    return rows, srows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cand = pd.read_csv(W16 / "candidates.csv.gz"); P = pars()
    res = Parallel(n_jobs=7, verbose=5)(delayed(one)(f, c, r, P, cand) for f, c in ALL_CELLS for r in range(8))
    R = pd.DataFrame([x for a, _ in res for x in a]); S = pd.DataFrame([x for _, b in res for x in b])
    R.to_csv(OUT / "likelihood_rules.csv.gz", index=False); S.to_csv(OUT / "likelihood_aleatoric.csv", index=False)
    R["det"] = R.cell.str.contains("sigma=0.0")
    print(R.groupby(["det", "rule"])[["rho_Vt_ham_ref", "rho_Vt_nsd", "pick_Vt_ham_ref", "pick_Vt_nsd", "rand_Vt_ham_ref"]].mean().round(4).to_string())
    print(S.groupby("family")[["aleatoric_share_band", "median_s_band"]].median().round(3).to_string())


if __name__ == "__main__":
    main()
