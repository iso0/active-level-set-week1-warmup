"""Week 13: does the physics coordinate transfer its ordering, its level, or both? (EXPLORATORY)

Descriptive only.  Fits are 1-D/3-D logistic summaries used to locate the
log-h level of the Conduction/Keyhole transition in each campaign separately.
No model is selected or tuned on NEW for any acquisition purpose.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, balanced_accuracy_score

ROOT = Path(__file__).resolve().parents[1]
W12 = ROOT / "outputs/week12_startup_and_transfer_development/audit"
OUT = ROOT / "outputs/week13_boundary_evaluation_and_mechanisms/real_data"
T_LIQ_TI64 = 1928.0  # K, nominal Ti-6Al-4V liquidus used only for an analytic upper bound


def level(logh, y, C=1e6):
    m = LogisticRegression(C=C, max_iter=5000).fit(logh.reshape(-1, 1), y)
    return float(-m.intercept_[0] / m.coef_[0, 0]), float(m.coef_[0, 0])


def free_exponents(frame, C=1e6):
    X = np.column_stack([np.log(frame.P), np.log(frame.VX), np.log(frame.LS)])
    m = LogisticRegression(C=C, max_iter=20000).fit((X - X.mean(0)) / X.std(0), frame.has_keyhole)
    beta = m.coef_[0] / X.std(0)
    return {"VX_over_P": float(beta[1] / beta[0]), "LS_over_P": float(beta[2] / beta[0])}


def main():
    old = pd.read_csv(W12 / "old405_inputs_labels.csv"); new = pd.read_csv(W12 / "new136.csv")
    res = {}
    for name, d in (("OLD", old), ("NEW", new)):
        lh, y = d.log_h.to_numpy(), d.has_keyhole.to_numpy(int)
        lv, slope = level(lh, y)
        res[name] = {"logh_level_p50": lv, "slope_per_logh": slope, "auc_logh": float(roc_auc_score(y, lh)),
                     "free_exponent_ratios": free_exponents(d), "h_exponents_ratio_reference": {"VX_over_P": -0.5, "LS_over_P": -1.5}}
    rng = np.random.default_rng(13)
    boots = {"OLD": [], "NEW": []}
    for name, d in (("OLD", old), ("NEW", new)):
        for _ in range(2000):
            idx = np.concatenate([rng.choice(np.nonzero(d.has_keyhole.values == c)[0], (d.has_keyhole.values == c).sum()) for c in (0, 1)])
            dd = d.iloc[idx]
            boots[name].append(level(dd.log_h.to_numpy(), dd.has_keyhole.to_numpy(int))[0])
    for name in boots:
        res[name]["logh_level_p50_stratified_bootstrap_95"] = [float(np.quantile(boots[name], .025)), float(np.quantile(boots[name], .975))]
    res["level_shift_NEW_minus_OLD"] = res["NEW"]["logh_level_p50"] - res["OLD"]["logh_level_p50"]
    # OLD threshold applied to NEW: ordering kept, level transferred
    lv_old = res["OLD"]["logh_level_p50"]
    yhat = (new.log_h.to_numpy() >= lv_old).astype(int)
    res["OLD_level_on_NEW"] = {"balanced_accuracy": float(balanced_accuracy_score(new.has_keyhole, yhat)), "rare_recall": float(np.mean(yhat[new.has_keyhole.values == 0] == 0))}
    # best achievable single log-h threshold on NEW (oracle, descriptive ceiling of the 1-D ordering)
    best = max(((balanced_accuracy_score(new.has_keyhole, (new.log_h.values >= t).astype(int)), t) for t in np.unique(new.log_h.values)))
    res["NEW_oracle_logh_threshold"] = {"balanced_accuracy": float(best[0]), "threshold": float(best[1])}
    best_vx = max(((balanced_accuracy_score(new.has_keyhole, (new.VX.values < t).astype(int)), t) for t in np.unique(new.VX.values)))
    res["NEW_oracle_VX_threshold"] = {"balanced_accuracy": float(best_vx[0]), "threshold": float(best_vx[1])}
    # analytic bound on the substrate-temperature factor of the keyhole number Ke ~ h / (T_l - T0)
    st = pd.concat([old.ST, new.ST])
    res["Ke_ST_factor_max_log_range_over_both_campaigns"] = float(np.log((T_LIQ_TI64 - st.min()) / (T_LIQ_TI64 - st.max())))
    res["Ke_ST_factor_mean_log_difference_NEW_rare_vs_keyhole"] = float(np.log((T_LIQ_TI64 - new.ST[new.has_keyhole == 0].mean()) / (T_LIQ_TI64 - new.ST[new.has_keyhole == 1].mean())))
    # OLD support inside the NEW box
    box = {c: (new[c].min(), new[c].max()) for c in ["P", "VX", "LS", "ST"]}
    inside = np.all([old[c].between(*box[c]) for c in box], axis=0)
    res["OLD_cases_inside_NEW_bounding_box"] = {"n": int(inside.sum()), "keyhole": int(old.has_keyhole[inside].sum())}
    inside3 = np.all([old[c].between(*box[c]) for c in ["P", "LS"]], axis=0)
    res["OLD_cases_inside_NEW_P_LS_range"] = {"n": int(inside3.sum()), "keyhole": int(old.has_keyhole[inside3].sum()),
                                             "non_keyhole_VX_values": sorted(old.VX[inside3 & (old.has_keyhole == 0)].round(3).tolist())}
    (OUT / "level_shift_summary.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
