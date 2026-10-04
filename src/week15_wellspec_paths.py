"""Week 15 development — full paths in the well-specified 3-D GP world (same world as week15_bayes_frontier).

Policies: random, margin, EBR-D, VSUR, BAYES-MC (exact posterior-expected NSD one-step look-ahead, S = 16).
Budget 8 -> 50, true NSD/ASSD against the sampled truth on the dense cloud.  Development only.
"""
from pathlib import Path
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from scipy.linalg import cho_solve, cholesky
from scipy.spatial import cKDTree
from scipy.special import expit
from src.week13_synthetic import LaplaceGPC, matern32
from src.week14_noise_acquisition import latent_mv
from src.week15_ebr import knn_graph, lookahead_scores
from src.week15_bayes_frontier import HYP, D, NP, TAU, nsd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week15_boundary_acquisition/development"
S = 16


def assd(zd, nn, ytrue, yhat):
    tb = (ytrue[nn] != ytrue[:, None]).any(1); pb = (yhat[nn] != yhat[:, None]).any(1)
    if not tb.any() or not pb.any():
        return float(np.sqrt(3))
    a = cKDTree(zd[pb]).query(zd[tb])[0]; b = cKDTree(zd[tb]).query(zd[pb])[0]
    return float((a.sum() + b.sum()) / (len(a) + len(b)))


def run(rep, policy):
    rng = np.random.default_rng([15, 78, rep])
    zd, zp = rng.random((D, 3)), rng.random((NP, 3))
    allz = np.vstack([zd, zp])
    C = cholesky(matern32(allz, allz, np.array(HYP["ls"]), HYP["var"]) + 1e-8 * np.eye(D + NP), lower=True)
    f = C @ rng.standard_normal(D + NP); fd, fp = f[:D], f[D:]
    yp = (rng.random(NP) < expit(fp)).astype(int)
    _, nn = cKDTree(zd).query(zd, k=9); nn = nn[:, 1:]
    G = C @ rng.standard_normal((D + NP, S))
    Zref = np.random.default_rng([15, 98]).random((400, 3)); Eref = knn_graph(Zref, 8)
    L = list(rng.choice(NP, 8, replace=False)); k = 0
    while len(set(yp[L])) < 2:
        L.append(int(rng.integers(NP)))
    prng = np.random.default_rng([15, 79, rep])
    srng = np.random.default_rng([15, 80, rep])
    rows = []
    while True:
        gp = LaplaceGPC(HYP["ls"], HYP["var"]).fit(zp[L], yp[L])
        yh = (gp.latent_mean(zd) > 0).astype(int)
        if len(L) % 6 == 2 or len(L) >= 50:
            rows.append({"rep": rep, "policy": policy, "budget": len(L), "NSD": nsd(zd, nn, (fd > 0).astype(int), yh),
                         "ASSD": assd(zd, nn, (fd > 0).astype(int), yh)})
        if len(L) >= 50:
            return rows
        cands = np.setdiff1d(np.arange(NP), L)
        if policy == "random":
            L.append(int(prng.choice(cands))); continue
        if policy == "margin":
            mu, var = latent_mv(gp, zp[cands]); p = expit(mu / np.sqrt(1 + np.pi * var / 8))
            L.append(int(cands[np.argmin(np.abs(p - .5))])); continue
        if policy in ("ebrd", "vsur"):
            sc, _ = lookahead_scores(zp, yp, L, cands, HYP, Zref, Eref, "EBRD" if policy == "ebrd" else "VSUR")
            L.append(int(cands[np.argmax(sc)])); continue
        # BAYES-MC
        def post_samples(g, idx):
            W = g.pi * (1 - g.pi); t = g.latent_mean(zp[idx]) + (g.y - g.pi) / W
            Lc = cholesky(matern32(zp[idx], zp[idx], g.ls, g.var) + np.diag(1 / W), lower=True)
            eta = srng.standard_normal((len(idx), S)) / np.sqrt(W)[:, None]
            return G[:D] + matern32(zd, zp[idx], g.ls, g.var) @ cho_solve((Lc, True), t[:, None] - G[D + np.asarray(idx)] - eta)
        pm = gp.proba(zp[cands])
        val = []
        for t, c in enumerate(cands):
            idx = np.r_[L, c]; v = 0.0
            for yv, w in ((1, pm[t]), (0, 1 - pm[t])):
                g2 = LaplaceGPC(HYP["ls"], HYP["var"]).fit(zp[idx], np.r_[yp[L], yv])
                yh2 = (g2.latent_mean(zd) > 0).astype(int); fs = post_samples(g2, idx)
                v += w * np.mean([nsd(zd, nn, (fs[:, s] > 0).astype(int), yh2) for s in range(S)])
            val.append(v)
        L.append(int(cands[int(np.argmax(val))]))


if __name__ == "__main__":
    jobs = [(r, p) for p in ("bayesmc", "random", "margin", "ebrd", "vsur") for r in range(12)]
    res = Parallel(n_jobs=7, verbose=2)(delayed(run)(r, p) for r, p in jobs)
    df = pd.DataFrame([x for rows in res for x in rows]); df.to_csv(OUT / "wellspec_paths.csv", index=False)
    au = df.groupby(["rep", "policy"]).apply(lambda g: pd.Series({c: np.trapezoid(g.sort_values("budget")[c], g.sort_values("budget").budget) / (g.budget.max() - g.budget.min()) for c in ("NSD", "ASSD")}), include_groups=False).reset_index()
    au.to_csv(OUT / "wellspec_aulc.csv", index=False)
    print(au.groupby("policy")[["NSD", "ASSD"]].mean().round(4))
    w = au.pivot(index="rep", columns="policy", values="NSD")
    for p in ("ebrd", "vsur", "bayesmc", "random"):
        d = w[p] - w["margin"]; print(p, "- margin NSD AULC", round(d.mean(), 4), "positive", int((d > 0).sum()), "/", len(d))
