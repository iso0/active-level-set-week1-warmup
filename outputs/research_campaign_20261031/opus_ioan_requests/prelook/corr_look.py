"""DESCRIPTIVE first look (all 541 pooled runs, true simulated values; evaluator view, no learner, nothing written to the repo).
1. How strongly does each physical output co-vary with melt-pool depth (raw Spearman, and partial after the 4 log inputs / log h)?
2. Oracle: with the TRUE values, does an output add label information beyond depth + log h? (10-fold stratified CV, L2 logistic C=1)
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, rankdata
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, log_loss, balanced_accuracy_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

WT = Path(r"C:\Users\ozgur\Documents\thesis\.claude\worktrees\joint-depth-label-dev")
D = Path(__file__).resolve().parent
M = pd.read_csv(WT / "outputs/research_campaign_20261018/opus_pooled/data/POOLED_MANIFEST.csv")
W = pd.read_csv(D / "width_per_run.csv")
X = M.merge(W, on="sim_id", how="left")
print("failure row:", W.loc[W.failure.fillna("") != "", ["sim_id", "failure"]].to_string()[:400])
X["log_W_um"] = np.log(X.W_active_max_um)
X["log_W_T0_um"] = np.log(X.W_T0_median_um)
X["log_W_at_Amax_um"] = np.log(X.W_at_Amax_um)
X["log_AR"] = X.log_A_um - X.log_W_um                      # aspect ratio depth / width (active-window maxima)
lx = np.log(X[["P", "VX", "LS", "ST"]].to_numpy(float))
X["log_h"] = lx[:, 0] - 0.5 * lx[:, 1] - 1.5 * lx[:, 2]
NAMES = {"log_W_um": "width (active max)", "log_W_T0_um": "width (T0 median)", "log_W_at_Amax_um": "width at max-depth row",
         "log_ke_T0_nJ": "kinetic energy (T0)", "tmax_T0_K": "max temperature (T0)", "vmax_spike_logratio": "velocity spike ratio",
         "vmax_spike_us": "velocity spike time", "laser_T0_W": "absorbed laser power (T0)", "log_etot_T0_J": "total energy (T0)",
         "log_npart_T0": "melt particles (T0)", "log_h": "log h (input formula)", "log_AR": "aspect ratio depth/width"}

good = ~X.short_record.astype(bool)


def resid(v, Z):
    Z1 = np.c_[np.ones(len(Z)), Z]
    b, *_ = np.linalg.lstsq(Z1, v, rcond=None)
    return v - Z1 @ b


rows = []
for c, nm in NAMES.items():
    m = good & np.isfinite(X[c]) & np.isfinite(X.log_A_um)
    a, q, z, h, y = X.log_A_um[m].to_numpy(), X[c][m].to_numpy(), lx[m.to_numpy()], X.log_h[m].to_numpy()[:, None], X.y[m].to_numpy()
    rs = spearmanr(q, a).statistic
    # partial (rank-based): residualise the RANKS on the inputs, then correlate
    ra, rq = rankdata(a), rankdata(q)
    p_in = np.corrcoef(resid(ra, z), resid(rq, z))[0, 1]
    p_h = np.corrcoef(resid(ra, h), resid(rq, h))[0, 1] if c != "log_h" else np.nan
    auc = roc_auc_score(y, q); auc = max(auc, 1 - auc)
    rows.append({"quantity": nm, "n": int(m.sum()), "rho_with_depth": rs, "partial_rho_given_4_inputs": p_in, "partial_rho_given_log_h": p_h, "label_AUC_alone": auc})
m = good & np.isfinite(X.log_A_um)
auc_d = roc_auc_score(X.y[m], X.log_A_um[m])
T1 = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(f"\nGood records n = {int(m.sum())}; depth label AUC alone = {auc_d:.3f}")
print(T1.round(3).to_string(index=False))

# ---- 2. oracle: label information beyond depth + log h, TRUE values, 10-fold CV (5 seeds)
OTH = ["log_ke_T0_nJ", "tmax_T0_K", "vmax_spike_logratio", "vmax_spike_us", "laser_T0_W", "log_etot_T0_J", "log_npart_T0"]
SETS = {"h": ["log_h"], "depth": ["log_A_um"], "h + depth": ["log_h", "log_A_um"], "h + depth + width": ["log_h", "log_A_um", "log_W_um"],
        "h + aspect ratio": ["log_h", "log_AR"], "h + width": ["log_h", "log_W_um"],
        "h + depth + 7 other outputs": ["log_h", "log_A_um", *OTH], "h + depth + width + 7 others": ["log_h", "log_A_um", "log_W_um", *OTH]}
cols = sorted({c for v in SETS.values() for c in v})
m = good & X[cols].notna().all(1) & np.isfinite(X[cols]).all(1)
y = X.y[m].to_numpy()
out = []
for nm, cs in SETS.items():
    Z = X.loc[m, cs].to_numpy(float); ll, ba, au = [], [], []
    for seed in range(5):
        p = np.zeros(len(y))
        for tr, te in StratifiedKFold(10, shuffle=True, random_state=seed).split(Z, y):
            mdl = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000)).fit(Z[tr], y[tr]); p[te] = mdl.predict_proba(Z[te])[:, 1]
        ll.append(log_loss(y, p)); ba.append(balanced_accuracy_score(y, p >= 0.5)); au.append(roc_auc_score(y, p))
    out.append({"features (true values)": nm, "CV_logloss": np.mean(ll), "CV_BA": np.mean(ba), "CV_AUC": np.mean(au)})
print(f"\nOracle, n = {int(m.sum())} good records with every output, keyhole share {y.mean():.3f}")
print(pd.DataFrame(out).round(4).to_string(index=False))
T1.to_csv(D / "corr_table.csv", index=False, lineterminator="\n"); pd.DataFrame(out).to_csv(D / "oracle_table.csv", index=False, lineterminator="\n")
