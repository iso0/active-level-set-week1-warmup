"""Week 13 analysis of the synthetic study (H1-H5 in synthetic/DESIGN.md) plus the
displaced-boundary family (CONTROLLED METHODOLOGICAL EVIDENCE)."""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler

from src.week13_boundary_metrics import gabriel_edges
from src.week13_synthetic import DenseTruth, latent
from src.week13_synthetic_al import (SCENARIOS, SIGMAS, calibrated, finite_metrics, noisy_labels, q20_flags, to_box)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week13_boundary_evaluation_and_mechanisms/synthetic"
FIN = ["q20_accuracy", "q20_balanced_accuracy", "full_accuracy", "full_balanced_accuracy", "full_minority_recall", "BER", "BEBA", "BEF1"]
TRUE = ["NSD_0.1", "NSD_0.05", "NSD_0.2", "ASSD", "dense_balanced_accuracy"]
CELL = ["scenario", "sigma", "n_pool"]


def aulc(g, col, lo=16, hi=80):
    g = g[(g.budget >= lo) & (g.budget <= hi)].dropna(subset=[col]).sort_values("budget")
    return float(np.trapezoid(g[col], g.budget) / (g.budget.max() - g.budget.min())) if len(g) > 1 else np.nan


def boot_ci(d, draws=4000, seed=1):
    d = np.asarray(d, float)
    b = np.random.default_rng(seed).choice(d, (draws, len(d))).mean(1)
    return float(d.mean()), float(np.quantile(b, .025)), float(np.quantile(b, .975)), int((d > 0).sum()), len(d)


def load():
    """Per-path parquet files written by week13_synthetic_al were consolidated into all_paths.parquet."""
    if (OUT / "all_paths.parquet").exists():
        return pd.read_parquet(OUT / "all_paths.parquet")
    return pd.concat([pd.read_parquet(f) for f in glob.glob(str(OUT / "paths" / "*.parquet"))], ignore_index=True)


def main():
    d = load()
    paths = d[~d.policy.isin(["CEILING_full_pool", "CONSTANT_majority"])]
    refs = d[d.policy.isin(["CEILING_full_pool", "CONSTANT_majority"])]
    # ---------------------------------------------------------------- AULC table
    rows = []
    for key, g in paths.groupby(CELL + ["rep", "policy", "model"]):
        r = dict(zip(CELL + ["rep", "policy", "model"], key))
        for c in FIN + TRUE:
            r[c] = aulc(g, c)
            r[c + "_B8"] = aulc(g, c, 8, 80)
        r["discovery_cost"] = g.discovery_cost.iloc[0]
        for b in (16, 40, 80):
            x = g[g.budget.eq(b)]
            r[f"minority_frac_labeled_B{b}"] = float(x.labeled_minority.iloc[0] / x.pool_minority.iloc[0]) if len(x) else np.nan
        rows.append(r)
    A = pd.DataFrame(rows)
    A.to_csv(OUT / "aulc_by_path.csv", index=False)
    mean = A.groupby(CELL + ["policy", "model"]).mean(numeric_only=True).drop(columns="rep")
    mean.to_csv(OUT / "aulc_mean_by_cell.csv")
    # ---------------------------------------------------------------- paired contrasts (H3, H4)
    W = A.set_index(CELL + ["model", "policy", "rep"])
    contr = []
    for (scn, sig, n, mdl), g in A.groupby(CELL + ["model"]):
        w = g.set_index(["policy", "rep"])
        for a, b in (("margin", "random"), ("coverage", "margin"), ("coverage", "random"), ("maximin", "random")):
            for c in ["q20_accuracy", "q20_balanced_accuracy", "full_balanced_accuracy", "BEF1", "BER", "NSD_0.1", "ASSD"]:
                diff = (w.loc[a][c] - w.loc[b][c]).dropna()
                m, lo, hi, pos, k = boot_ci(diff)
                contr.append({"scenario": scn, "sigma": sig, "n_pool": n, "model": mdl, "contrast": f"{a}-{b}", "metric": c,
                              "mean": m, "ci_low": lo, "ci_high": hi, "positive": pos, "n": k})
    C = pd.DataFrame(contr)
    C.to_csv(OUT / "paired_contrasts.csv", index=False)
    # headroom: ceiling value minus random AULC and margin AULC
    ceil = refs[refs.policy.eq("CEILING_full_pool")].set_index(CELL + ["model", "rep"])
    head = []
    for (scn, sig, n, mdl), g in A.groupby(CELL + ["model"]):
        for c in ["q20_accuracy", "BEF1", "NSD_0.1"]:
            cv = ceil.loc[(scn, sig, n, mdl)][c]
            rnd = g[g.policy.eq("random")].set_index("rep")[c]
            mar = g[g.policy.eq("margin")].set_index("rep")[c]
            head.append({"scenario": scn, "sigma": sig, "n_pool": n, "model": mdl, "metric": c,
                         "ceiling": float(cv.mean()), "random_AULC": float(rnd.mean()), "margin_AULC": float(mar.mean()),
                         "headroom_ceiling_minus_random": float((cv - rnd).mean()),
                         "margin_gain": float((mar - rnd).mean()),
                         "fraction_of_headroom_captured": float((mar - rnd).mean() / (cv - rnd).mean()) if (cv - rnd).mean() != 0 else np.nan})
    H = pd.DataFrame(head)
    H.to_csv(OUT / "headroom.csv", index=False)
    # ---------------------------------------------------------------- H1: metric validity across predictors
    dense_rows = paths.dropna(subset=["NSD_0.1"])
    const = refs[refs.policy.eq("CONSTANT_majority")]
    val = []
    for key, g in dense_rows.groupby(CELL):
        gc = pd.concat([g, const.set_index(CELL).loc[[key]].reset_index()], ignore_index=True)
        for c in FIN:
            for t in ("NSD_0.1", "ASSD"):
                sgn = -1 if t == "ASSD" else 1
                rho = spearmanr(g[c], sgn * g[t], nan_policy="omit").statistic
                rho_c = spearmanr(gc[c], sgn * gc[t], nan_policy="omit").statistic
                val.append({"scenario": key[0], "sigma": key[1], "n_pool": key[2], "finite_metric": c, "truth": t,
                            "spearman_AL_predictors": float(rho), "spearman_with_constant": float(rho_c), "n_predictors": len(g)})
        # H2: percentile rank of constant predictor under each metric among AL predictors
    V = pd.DataFrame(val)
    V.to_csv(OUT / "metric_validity_spearman.csv", index=False)
    crank = []
    for key, g in dense_rows.groupby(CELL):
        cc = const.set_index(CELL).loc[[key]]
        for c in FIN + ["NSD_0.1"]:
            vals = g[c].dropna().to_numpy()
            crank.append({"scenario": key[0], "sigma": key[1], "n_pool": key[2], "metric": c,
                          "constant_value": float(cc[c].mean()), "AL_median": float(np.median(vals)),
                          "fraction_of_AL_predictors_beaten_by_constant": float(np.mean([np.mean(vals < v) for v in cc[c]]))})
    R = pd.DataFrame(crank)
    R.to_csv(OUT / "constant_predictor_rank.csv", index=False)
    # agreement of margin-vs-random sign between q20 accuracy and NSD
    piv = C[C.contrast.eq("margin-random") & C.metric.isin(["q20_accuracy", "NSD_0.1", "BEF1", "full_balanced_accuracy"])].pivot_table(
        index=CELL + ["model"], columns="metric", values="mean")
    piv.to_csv(OUT / "margin_vs_random_by_metric.csv")
    summary = {"n_paths": int(A.shape[0]),
               "metric_validity_mean_spearman_NSD": V[V.truth.eq("NSD_0.1")].groupby(["scenario", "finite_metric"]).spearman_AL_predictors.mean().unstack().round(3).to_dict(),
               "constant_beats_fraction": R.groupby(["scenario", "metric"]).fraction_of_AL_predictors_beaten_by_constant.mean().unstack().round(3).to_dict()}
    (OUT / "analysis_summary.json").write_text(json.dumps(summary, indent=2, default=float))
    pd.set_option("display.width", 260)
    pd.set_option("display.max_columns", 40)
    print(V[V.truth.eq("NSD_0.1")].pivot_table(index=["scenario", "sigma", "n_pool"], columns="finite_metric", values="spearman_AL_predictors").round(2).to_string())
    print(R.pivot_table(index=["scenario", "sigma", "n_pool"], columns="metric", values="fraction_of_AL_predictors_beaten_by_constant").round(2).to_string())
    print(piv.round(4).to_string())
    print(H.round(4).to_string())
    print(mean[["discovery_cost", "minority_frac_labeled_B16", "minority_frac_labeled_B40", "minority_frac_labeled_B80"]].round(2).to_string())


def displaced_family(reps=30, deltas=np.linspace(-3, 3, 25)):
    """Predictors with the true boundary shape but displaced level: yhat = 1[f + delta > 0]."""
    rows = []
    for scn in SCENARIOS:
        sc = calibrated(scn)
        dense = DenseTruth(sc, seed=5)
        lat_d = latent(dense.u, sc)
        truth_by_delta = {dl: dense.metrics((lat_d + dl > 0).astype(int)) for dl in deltas}
        for sigma in SIGMAS:
            for n_eval in (136, 405):
                for rep in range(reps):
                    rng = np.random.default_rng([77, int(sigma * 10), n_eval, rep])
                    u = sc.sample(n_eval, rng)
                    y = noisy_labels(u, sc, sigma, rng)
                    z = to_box(u, sc)
                    q = q20_flags(z, y)
                    e = gabriel_edges(StandardScaler().fit_transform(z))
                    minority = int(np.mean(y) > .5) ^ 1
                    lat = latent(u, sc)
                    for dl in deltas:
                        r = {"scenario": scn, "sigma": sigma, "n_eval": n_eval, "rep": rep, "delta": float(dl)}
                        r.update(finite_metrics(y, (lat + dl > 0).astype(int), q, e, minority))
                        r.update(truth_by_delta[dl])
                        rows.append(r)
    F = pd.DataFrame(rows)
    F.to_csv(OUT / "displaced_boundary_family.csv.gz", index=False)
    S = F.groupby(["scenario", "sigma", "n_eval", "delta"])[FIN + ["NSD_0.1", "ASSD"]].mean().reset_index()
    S.to_csv(OUT / "displaced_boundary_summary.csv", index=False)
    # where does each metric peak?  (the truth peaks at delta = 0 by construction)
    peaks = []
    for key, g in S.groupby(["scenario", "sigma", "n_eval"]):
        for c in FIN + ["NSD_0.1"]:
            peaks.append({"scenario": key[0], "sigma": key[1], "n_eval": key[2], "metric": c,
                          "argmax_delta": float(g.loc[g[c].idxmax(), "delta"]),
                          "value_at_0": float(g.loc[(g.delta.abs()).idxmin(), c]), "max_value": float(g[c].max())})
    P = pd.DataFrame(peaks)
    P.to_csv(OUT / "displaced_boundary_peaks.csv", index=False)
    print(P.pivot_table(index=["scenario", "sigma", "n_eval"], columns="metric", values="argmax_delta").to_string())


if __name__ == "__main__":
    import sys
    if "--displaced" in sys.argv:
        displaced_family()
    else:
        main()
