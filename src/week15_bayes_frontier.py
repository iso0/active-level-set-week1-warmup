"""Week 15 diagnostic — in a WELL-SPECIFIED world, how much of the expectation-oracle advantage can a
Bayes-optimal one-step look-ahead capture?

World (development only, 3-D): f ~ GP(0, Matérn-3/2 ARD) sampled jointly on a dense cloud and the pool;
labels y ~ Bernoulli(sigmoid(f)).  The model uses exactly that prior, so the Laplace posterior is the
(approximately) correct posterior.  At states on margin paths we compute for each candidate:
  ORACLE-E  : E_{y ~ sigmoid(f_true)}[NSD(f_true, pred after update)] − NSD now      (needs the truth)
  BAYES-MC  : E_{f ~ posterior}E_{y ~ sigmoid(f)}[NSD(f, pred after update)] − E_f[NSD(f, pred now)]
              by S posterior samples (Matheron pathwise conditioning on the Laplace Gaussian), i.e. the
              exact one-step Bayes expected gain of the evaluation metric (no surrogate)
  margin, EBR-D, VSUR as before.
By Jensen, E_f[max_c G(c, f)] ≥ max_c E_f[G(c, f)]: the oracle's advantage over BAYES-MC is the one-step
value of knowing f, unattainable by any non-anticipating rule when the prior is correct.
"""
from pathlib import Path
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from scipy.linalg import cho_solve, cholesky
from scipy.spatial import cKDTree
from scipy.special import expit
from scipy.stats import spearmanr
from src.week13_synthetic import LaplaceGPC, matern32
from src.week14_noise_acquisition import latent_mv
from src.week15_ebr import knn_graph, lookahead_scores

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week15_boundary_acquisition/development"
HYP = {"ls": [.35, .5, .7], "var": 9.0}
D, NP, S, TAU = 1500, 108, 24, .1


def nsd(zd, nn, ytrue, yhat):
    tb = (ytrue[nn] != ytrue[:, None]).any(1); pb = (yhat[nn] != yhat[:, None]).any(1)
    if not tb.any() or not pb.any():
        return 0.0
    a = cKDTree(zd[pb]).query(zd[tb])[0]; b = cKDTree(zd[tb]).query(zd[pb])[0]
    return float(((a <= TAU).sum() + (b <= TAU).sum()) / (len(a) + len(b)))


def run(rep):
    rng = np.random.default_rng([15, 77, rep])
    zd, zp = rng.random((D, 3)), rng.random((NP, 3))
    allz = np.vstack([zd, zp])
    Kall = matern32(allz, allz, np.array(HYP["ls"]), HYP["var"]) + 1e-8 * np.eye(D + NP)
    C = cholesky(Kall, lower=True)
    f = C @ rng.standard_normal(D + NP)
    # no level shift: the model prior (zero mean, same kernel) is exactly the generating prior
    fd, fp = f[:D], f[D:]
    yp = (rng.random(NP) < expit(fp)).astype(int)
    _, nn = cKDTree(zd).query(zd, k=9); nn = nn[:, 1:]
    G = C @ rng.standard_normal((D + NP, S))     # prior samples for pathwise conditioning
    Zref = np.random.default_rng([15, 98]).random((400, 3)); Eref = knn_graph(Zref, 8)
    L = list(rng.choice(NP, 8, replace=False))
    while len(set(yp[L])) < 2:
        L.append(int(rng.integers(NP)))
    rows = []
    while len(L) <= 50:
        gp = LaplaceGPC(HYP["ls"], HYP["var"]).fit(zp[L], yp[L])
        cands = np.setdiff1d(np.arange(NP), L)
        if len(L) in (20, 35, 50):
            def fitpred(idx, yy):
                g = LaplaceGPC(HYP["ls"], HYP["var"]).fit(zp[idx], yy)
                return g
            def post_samples(g, idx):
                # Laplace Gaussian: targets t = fhat + W^-1 (y - pi), noise W^-1;  Matheron: f_s = g_s + K_.X (K_XX + W^-1)^-1 (t - g_s(X) - eta)
                W = g.pi * (1 - g.pi)
                fhat = g.latent_mean(zp[idx])
                t = fhat + (g.y - g.pi) / W
                Kxx = matern32(zp[idx], zp[idx], g.ls, g.var) + np.diag(1 / W)
                Lc = cholesky(Kxx, lower=True)
                eta = rng.standard_normal((len(idx), S)) / np.sqrt(W)[:, None]
                rhs = t[:, None] - G[D + np.asarray(idx)] - eta
                Kdx = matern32(zd, zp[idx], g.ls, g.var)
                return G[:D] + Kdx @ cho_solve((Lc, True), rhs)
            ynow = (gp.latent_mean(zd) > 0).astype(int)
            fs_now = post_samples(gp, L)
            bayes_now = np.mean([nsd(zd, nn, (fs_now[:, s] > 0).astype(int), ynow) for s in range(S)])
            true_now = nsd(zd, nn, (fd > 0).astype(int), ynow)
            og, bg = [], []
            for c in cands:
                idx = np.r_[L, c]
                p_true = expit(fp[c]); p_mod = gp.proba(zp[[c]])[0]
                gt, gb = 0.0, 0.0
                for yv, wt, wm in ((1, p_true, p_mod), (0, 1 - p_true, 1 - p_mod)):
                    g2 = fitpred(idx, np.r_[yp[L], yv])
                    yh = (g2.latent_mean(zd) > 0).astype(int)
                    gt += wt * nsd(zd, nn, (fd > 0).astype(int), yh)
                    fs = post_samples(g2, idx)
                    gb += wm * np.mean([nsd(zd, nn, (fs[:, s] > 0).astype(int), yh) for s in range(S)])
                og.append(gt - true_now); bg.append(gb - bayes_now)
            og, bg = np.asarray(og), np.asarray(bg)
            mu, var = latent_mv(gp, zp[cands])
            p = expit(mu / np.sqrt(1 + np.pi * var / 8))
            hypd = {"ls": HYP["ls"], "var": HYP["var"]}
            scores = {"bayes_mc": bg, "margin": -np.abs(p - .5),
                      "ebrd": lookahead_scores(zp, yp, L, cands, hypd, Zref, Eref, "EBRD")[0],
                      "vsur": lookahead_scores(zp, yp, L, cands, hypd, Zref, Eref, "VSUR")[0]}
            for k, v in scores.items():
                ch = int(np.argmax(v))
                rows.append({"rep": rep, "budget": len(L), "criterion": k, "spearman_with_oracle": float(spearmanr(v, og).statistic),
                             "oracle_gain_of_choice": float(og[ch]), "oracle_best_gain": float(og.max()),
                             "bayes_gain_of_choice": float(bg[ch]), "bayes_best_gain": float(bg.max())})
        if len(L) == 50:
            break
        mu, var = latent_mv(gp, zp[cands]); p = expit(mu / np.sqrt(1 + np.pi * var / 8))
        L.append(int(cands[np.argmin(np.abs(p - .5))]))
    return rows


if __name__ == "__main__":
    res = Parallel(n_jobs=7, verbose=2)(delayed(run)(r) for r in range(14))
    df = pd.DataFrame([x for rows in res for x in rows]); OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "bayes_frontier.csv", index=False)
    print(df.groupby("criterion")[["spearman_with_oracle", "oracle_gain_of_choice", "oracle_best_gain", "bayes_gain_of_choice", "bayes_best_gain"]].mean().round(4).to_string())
