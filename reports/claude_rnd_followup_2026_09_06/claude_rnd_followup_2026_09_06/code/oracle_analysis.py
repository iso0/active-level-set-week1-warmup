"""Section 4.2–4.4: predictability of candidate-level oracle value from allowed features."""
import sys, json, numpy as np, pandas as pd
from scipy.stats import spearmanr, pearsonr
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.linear_model import RidgeCV, LogisticRegression
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
OUT = "/home/claude/rnd/followup/results/"
df = pd.read_csv(OUT + "oracle_values.csv.gz"); df = df[df.eligible == 1].copy()
df["state"] = df.run_id + "|" + df.budget.astype(str)
V = "V_q20_acc"
ALLOWED = ["logh", "dist_thr_logh", "abs_dist_thr", "in_band", "logVX", "logLS", "ST_z", "nn_revealed", "nn_revealed_kh", "nn_revealed_c", "pool_density_r05", "revealed_density_r05", "revealed_density_r10",
           "local_frac_kh", "local_label_entropy", "local_phys_conflict", "m3_p", "m3_margin", "m3_latent_m", "m3_latent_v", "m3_pi_margin", "h_p", "abs_m3_minus_h", "abs_m3_minus_lr4", "abs_m3_minus_T", "T_tau_sd", "T_tv", "T_xsur2", "T_flips2", "cfg_main"]
df["abs_m3_latent_m"] = df.m3_latent_m.abs(); ALLOWED.append("abs_m3_latent_m")
df[ALLOWED] = df[ALLOWED].fillna(df[ALLOWED].median())
print("states:", df.state.nunique(), "candidate rows:", len(df)); print("V_q20 distribution:", df[V].describe().round(4).to_dict())
print("fraction of candidates with V>0:", (df[V] > 0).mean().round(3), " V<0:", (df[V] < 0).mean().round(3), " per-state mean of max V:", df.groupby("state")[V].max().mean().round(4))
# within-state rank-based relabelling: top-k by V within state
def topk_flags(g, frac):
    k = max(1, int(np.ceil(frac * len(g)))); thr = np.sort(g[V].values)[::-1][k - 1]; return (g[V] >= thr) & (g[V] > 0)
for frac in (0.05, 0.10, 0.20):
    df[f"top{int(frac*100)}"] = df.groupby("state", group_keys=False).apply(lambda g: topk_flags(g, frac))
# ---- 4.2 per-feature association, computed within state then aggregated by repeat block
rows = []
for f in ALLOWED:
    per_state = []
    for st, g in df.groupby("state"):
        if g[V].nunique() < 2 or g[f].nunique() < 2: continue
        rho = spearmanr(g[f], g[V])[0]
        au = {}
        for k in ("top5", "top10", "top20"):
            if g[k].nunique() == 2:
                au[f"auroc_{k}"] = roc_auc_score(g[k], g[f]); au[f"ap_{k}"] = average_precision_score(g[k], g[f]); au[f"base_{k}"] = g[k].mean()
                kk = int(g[k].sum()); topf = g.nlargest(kk, f); au[f"prec@k_{k}"] = topf[k].mean(); au[f"enrich_{k}"] = au[f"prec@k_{k}"] / max(g[k].mean(), 1e-9)
        # partial: residual of V after margin, correlation with feature
        per_state.append({"state": st, "repeat": g.repeat.iloc[0], "budget": g.budget.iloc[0], "rho": rho, **au})
    ps = pd.DataFrame(per_state)
    blk = ps.groupby("repeat").rho.mean()
    rows.append({"feature": f, "n_states": len(ps), "rho_median": ps.rho.median(), "rho_mean": ps.rho.mean(), "rho_block_mean": blk.mean(), "rho_block_sd": blk.std(ddof=1), "rho_frac_states_pos": (ps.rho > 0).mean(),
                 **{c: ps[c].mean() for c in ps.columns if c.startswith(("auroc", "ap_", "prec@k", "enrich"))},
                 **{f"rho_B{b}": ps[ps.budget == b].rho.mean() for b in (16, 24, 32, 40)}})
assoc = pd.DataFrame(rows).sort_values("rho_median", ascending=False); assoc.to_csv(OUT + "oracle_feature_associations.csv", index=False)
pd.set_option("display.width", 250); print("\nFeature associations with V_q20 (within-state, aggregated):")
print(assoc[["feature", "rho_median", "rho_block_mean", "rho_block_sd", "rho_frac_states_pos", "auroc_top10", "enrich_top10", "enrich_top5", "rho_B16", "rho_B24", "rho_B32", "rho_B40"]].round(3).to_string())
# partial association controlling for margin: within-state regression of V on margin, then rho of residual with feature
prow = []
for f in ALLOWED:
    if f == "m3_margin": continue
    rs = []
    for st, g in df.groupby("state"):
        if len(g) < 8: continue
        A = np.c_[np.ones(len(g)), g.m3_margin.values]; beta = np.linalg.lstsq(A, g[V].values, rcond=None)[0]; res = g[V].values - A @ beta
        Af = np.c_[np.ones(len(g)), g.m3_margin.values]; bf = np.linalg.lstsq(Af, g[f].values, rcond=None)[0]; resf = g[f].values - Af @ bf
        if np.std(res) > 0 and np.std(resf) > 0: rs.append(spearmanr(resf, res)[0])
    prow.append({"feature": f, "partial_rho_median": np.median(rs), "partial_rho_mean": np.mean(rs), "n": len(rs)})
partial = pd.DataFrame(prow).sort_values("partial_rho_median", ascending=False); partial.to_csv(OUT + "oracle_feature_partial_margin.csv", index=False)
print("\nPartial (margin-controlled) associations:"); print(partial.round(3).to_string())
# ---- 4.3 cross-fitted predictor: leave-repeat-block-out
def cross_fit(model_fn, name):
    preds = np.full(len(df), np.nan); reps = sorted(df.repeat.unique())
    for r in reps:
        tr = df.repeat != r; te = df.repeat == r
        m = model_fn().fit(df.loc[tr, ALLOWED].values, df.loc[tr, V].values); preds[te.values] = m.predict(df.loc[te, ALLOWED].values)
    df[f"pred_{name}"] = preds
    ps = []
    for st, g in df.groupby("state"):
        if g[V].nunique() < 2: continue
        e = {}
        for k in ("top5", "top10", "top20"):
            if g[k].nunique() == 2:
                kk = int(g[k].sum()); e[f"enrich_{k}"] = g.nlargest(kk, f"pred_{name}")[k].mean() / g[k].mean(); e[f"auroc_{k}"] = roc_auc_score(g[k], g[f"pred_{name}"])
        ps.append({"state": st, "repeat": g.repeat.iloc[0], "rho": spearmanr(g[f"pred_{name}"], g[V])[0], "top1_V": g.loc[g[f"pred_{name}"].idxmax(), V], "margin_top1_V": g.loc[g.m3_margin.idxmax(), V], "best_V": g[V].max(), **e})
    ps = pd.DataFrame(ps); blk = ps.groupby("repeat").rho.mean()
    r2 = 1 - np.nansum((df[V] - df[f"pred_{name}"]) ** 2) / np.sum((df[V] - df[V].mean()) ** 2)
    out = {"model": name, "out_of_block_R2": r2, "rho_median": ps.rho.median(), "rho_block_mean": blk.mean(), "rho_block_sd": blk.std(ddof=1), "rho_block_lo": blk.mean() - 1.96 * blk.std(ddof=1) / np.sqrt(len(blk)),
           "frac_states_rho_pos": (ps.rho > 0).mean(), **{c: ps[c].mean() for c in ps.columns if c.startswith(("enrich", "auroc"))},
           "mean_V_of_predicted_top1": ps.top1_V.mean(), "mean_V_of_margin_top1": ps.margin_top1_V.mean(), "mean_best_V": ps.best_V.mean()}
    return out, ps
res = []
for name, fn in (("ridge", lambda: make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 12)))), ("gbm_small", lambda: GradientBoostingRegressor(n_estimators=150, max_depth=2, learning_rate=0.05, subsample=0.8, random_state=0))):
    o, ps = cross_fit(fn, name); res.append(o); ps.to_csv(OUT + f"oracle_predictor_states_{name}.csv", index=False)
cf = pd.DataFrame(res); cf.to_csv(OUT + "oracle_predictor_crossfit.csv", index=False); print("\nCross-fitted predictors (leave-repeat-block-out):"); print(cf.round(3).T.to_string())
# ---- 4.4 composition of top oracle-value candidates vs eligible pool vs margin picks
comp = []
for label, mask in (("all_eligible", np.ones(len(df), bool)), ("top5_oracle", df.top5.values), ("top10_oracle", df.top10.values), ("V>0", (df[V] > 0).values), ("margin_top1", df.groupby("state").m3_margin.transform("max").eq(df.m3_margin).values)):
    g = df[mask]
    comp.append({"set": label, "n": len(g), "frac_KH": g.true_y.mean(), "frac_exception": g.is_exception.mean(), "frac_late_kh": g.is_late_kh.mean(), "frac_transient_kh": g.is_transient_kh.mean(), "frac_main_cfg": g.cfg_main.mean(),
                 "frac_new_data_partition": (g.partition == "new-data").mean(), "mean_logh": g.logh.mean(), "mean_abs_dist_thr": g.abs_dist_thr.mean(), "frac_in_band": g.in_band.mean(), "mean_pool_density": g.pool_density_r05.mean(),
                 "mean_local_conflict": g.local_phys_conflict.mean(), "mean_m3_margin": g.m3_margin.mean(), "mean_m3_p": g.m3_p.mean(), "mean_V": g[V].mean()})
comp = pd.DataFrame(comp); comp.to_csv(OUT + "oracle_composition.csv", index=False); print("\nComposition:"); print(comp.round(3).to_string())
# how much of the top-oracle value is due to KH labels vs C labels
print("\nMean V by true label among eligible:", df.groupby("true_y")[V].mean().round(4).to_dict(), " top10 share KH:", df[df.top10].true_y.mean().round(3))
print("Per-state: does any candidate have V>0? fraction of states:", df.groupby("state")[V].max().gt(0).mean().round(3))
print("By budget: mean best V, mean V of margin pick, mean V:"); print(df.groupby("budget").apply(lambda g: pd.Series({"best_V": g.groupby("state")[V].max().mean(), "margin_pick_V": g[g.groupby("state").m3_margin.transform("max").eq(g.m3_margin)][V].mean(), "mean_V": g[V].mean(), "n_elig_per_state": g.groupby("state").size().mean()})).round(4).to_string())
