"""Week 16 item 0 — PEER closed form against (i) Monte Carlo from the same Gaussian posterior and (ii) VSUR's
refit look-ahead, on 18 fixed states of regenerated margin paths (safeguarded Laplace fit throughout; VSUR is
recomputed with safeguarded refits, `vsur_refit`, and also reported as implemented in Week 15).  The
martingale statistic sum_i |E_y q_i' - q_i| measures how far the refit look-ahead is from a coherent Bayesian
update (zero for exact conditioning).  Only agreement statistics are reported here; nothing about margin's
value is computed (that is item 1, after PREDICTIONS.md)."""
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.special import ndtr
from scipy.stats import pearsonr, spearmanr

from src.week15_ebr import knn_graph, lookahead_scores
from src.week16_cells import build, cell_key, margin_states, pars
from src.week16_peer import Model, peer_values, peer_values_mc

OUT = Path(__file__).resolve().parents[1] / "outputs/week16_theory_meets_data/validation"
STATES = ([("dev", {"scn": s, "sigma": g}, 0, b) for s in ("BAL", "OLD", "NEW") for g in (0.5, 1.0) for b in ((24,) if g == .5 else (48,))] +
          [("dev", {"scn": "OLD", "sigma": 0.0}, 1, 24), ("dev", {"scn": "NEW", "sigma": 0.0}, 1, 32),
           ("dev", {"scn": "BAL", "sigma": 1.0}, 2, 24), ("dev", {"scn": "NEW", "sigma": 0.5}, 2, 64)] +
          [("curvedMono", {"box": "NEW", "sigma": 1.0, "pool": 108}, 0, b) for b in (24, 48)] +
          [("gpworld", {"m0": m, "pool": 108}, 0, 32) for m in (0.0, -4.0)] +
          [("branin4d", {"sigma": .5, "pool": 108}, 0, 32), ("rough", {"sigma": .5, "pool": 108}, 0, 32),
           ("curvedMono", {"box": "OLD", "sigma": .5, "pool": 108}, 0, 32), ("gpworld", {"m0": 0.0, "pool": 108}, 1, 64)])


def vsur_refit(model, z, y, L, cands, Z):
    """VSUR one-step score r0 - sum_y p_y r(y) with refits of `model`, and the martingale gap per candidate."""
    post = model.fit(z[L], y[L])
    mu, v = post.mean_var(Z); q = ndtr(mu / np.sqrt(v)); r0 = np.minimum(q, 1 - q).sum()
    p1 = post.proba(z[cands])
    sc, gap = np.empty(len(cands)), np.empty(len(cands))
    for t, j in enumerate(cands):
        qs = []
        for lab in (1, 0):
            pj = model.fit(z[np.r_[L, j]], np.r_[y[L], lab]); m_, v_ = pj.mean_var(Z); qs.append(ndtr(m_ / np.sqrt(v_)))
        sc[t] = r0 - (p1[t] * np.minimum(qs[0], 1 - qs[0]).sum() + (1 - p1[t]) * np.minimum(qs[1], 1 - qs[1]).sum())
        gap[t] = np.abs(p1[t] * qs[0] + (1 - p1[t]) * qs[1] - q).sum()
    return sc, gap


def one(fam, cfg, rep, b, P):
    c = build(fam, cfg, rep, P)
    model = Model.from_hyp(c["hyp"])
    st, _ = margin_states(c, (b,), model)
    L = st[b]; z = c["z_pool"]
    cands = np.setdiff1d(np.arange(len(z)), L)
    post = model.fit(z[L], c["y_pool"][L])
    v = peer_values(post, c["zref"], z[cands])
    sc15, _ = lookahead_scores(z, c["y_pool"], L, cands, c["hyp"], c["zref"], knn_graph(c["zref"], 8), kind="VSUR")
    sc, gap = vsur_refit(model, z, c["y_pool"], L, cands, c["zref"])
    sub = np.random.default_rng([16, 0, rep, b]).choice(len(cands), 12, replace=False)
    vm = peer_values_mc(post, c["zref"], z[cands[sub]], n=60000, seed=b)
    top = lambda x, k=5: set(np.argsort(-x)[:k])
    return {"cell": cell_key(fam, cfg), "rep": rep, "budget": b, "n_cands": len(cands), "peer_max": float(v.max()),
            "vsur_max": float(sc.max()), "pearson_peer_vsur": pearsonr(v, sc).statistic, "spearman_peer_vsur": spearmanr(v, sc).statistic,
            "argmax_agree": bool(np.argmax(v) == np.argmax(sc)), "top5_overlap": len(top(v) & top(sc)),
            "vsur_value_at_peer_argmax_over_vsur_max": float(sc[np.argmax(v)] / sc.max()) if sc.max() > 0 else np.nan,
            "mean_abs_diff_over_peer_max": float(np.mean(np.abs(v - sc)) / v.max()),
            "mc_max_abs_diff": float(np.abs(v[sub] - vm).max()), "mc_pearson": pearsonr(v[sub], vm).statistic,
            "mc_mean_value": float(vm.mean()), "spearman_peer_vsur_week15_impl": spearmanr(v, sc15).statistic,
            "martingale_gap_median": float(np.median(gap)), "martingale_gap_max": float(gap.max()),
            "vsur_minus_peer_mean": float(np.mean(sc - v)), "vsur_negative_share": float(np.mean(sc < 0))}


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    P = pars()
    rows = Parallel(n_jobs=7, verbose=2)(delayed(one)(f, c, r, b, P) for f, c, r, b in STATES)
    df = pd.DataFrame(rows); df.to_csv(OUT / "peer_validation.csv", index=False)
    cols = ["cell", "budget", "peer_max", "vsur_max", "spearman_peer_vsur", "spearman_peer_vsur_week15_impl", "top5_overlap",
            "martingale_gap_median", "vsur_negative_share", "mc_max_abs_diff", "mc_pearson"]
    print(df[cols].round(3).to_string())
