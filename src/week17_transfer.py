"""Week 17 Phase 1C — what fails in strict OLD→NEW transfer?  (POST-HOC NEW; descriptive)

For each model fitted on OLD-405, NEW predictions are post-processed in nested steps:
  raw        as transferred
  prior      label-shift correction with the known NEW class prevalence only (Saerens et al. 2002):
             logit p' = logit p + logit(π_NEW) − logit(π_OLD)  — no per-row NEW labels
  intercept  ORACLE: one intercept fitted on NEW labels (level/threshold shift)
  platt      ORACLE: intercept + slope on NEW labels (level + confidence)
AUC is invariant to all of these, so it isolates the ranking (direction / residual covariance) component.
Also: physics level shift (H refitted on NEW vs OLD), and error by distance of NEW rows to OLD support.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, logit
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from src.week17_audit import ROOT, campaigns
from src.week17_pooled import pooled_metrics

P1 = ROOT / "outputs/week17_model_and_acquisition/phase1"


def recal(z, y, slope):
    f = lambda t: np.mean(np.logaddexp(0, -(2 * y - 1) * ((t[1] if slope else 1.0) * z + t[0])))
    return minimize(f, [0.0, 1.0], method="Nelder-Mead").x


def main():
    C = campaigns(); xo, lo, yo = C["OLD"]; xn, ln, yn = C["NEW"]
    D = pd.read_csv(P1 / "diagnose_real.csv.gz"); T = D[D.set == "transfer"]
    pi_o, pi_n = yo.mean(), yn.mean()
    rows = []
    for r in T.itertuples():
        p = np.clip(np.array(r.pred_p.split(","), float), 1e-9, 1 - 1e-9); z = logit(p)
        a, _ = recal(z, yn, False); a2, b2 = recal(z, yn, True)
        for step, zz in (("raw", z), ("prior", z + logit(pi_n) - logit(pi_o)), ("intercept", z + a), ("platt", b2 * z + a2)):
            rows.append({"model": r.model, "step": step, **pooled_metrics(yn, expit(zz), 0),
                         "shift": float(a) if step == "intercept" else (float(logit(pi_n) - logit(pi_o)) if step == "prior" else np.nan),
                         "slope": float(b2) if step == "platt" else np.nan})
    R = pd.DataFrame(rows); R.to_csv(P1 / "transfer_decomposition.csv", index=False)
    # physics level: H on OLD vs H on NEW (same standardization of log h by OLD)
    from sklearn.linear_model import LogisticRegression
    sc = StandardScaler().fit(lo[:, None])
    h_old = LogisticRegression(C=1e6, max_iter=3000).fit(sc.transform(lo[:, None]), yo)
    h_new = LogisticRegression(C=1e6, max_iter=3000).fit(sc.transform(ln[:, None]), yn)
    thr = lambda m: float(sc.inverse_transform([[-m.intercept_[0] / m.coef_[0, 0]]])[0, 0])
    lvl = {"OLD_coef": float(h_old.coef_[0, 0]), "OLD_intercept": float(h_old.intercept_[0]), "OLD_threshold_logh": thr(h_old),
           "NEW_coef": float(h_new.coef_[0, 0]), "NEW_intercept": float(h_new.intercept_[0]), "NEW_threshold_logh": thr(h_new),
           "AUC_logh_OLD": float(roc_auc_score(yo, lo)), "AUC_logh_NEW": float(roc_auc_score(yn, ln)),
           "AUC_VX_NEW": float(roc_auc_score(yn, -xn[:, 1])), "AUC_VX_OLD": float(roc_auc_score(yo, -xo[:, 1])),
           "prevalence_OLD": float(pi_o), "prevalence_NEW": float(pi_n)}
    pd.Series(lvl).to_csv(P1 / "transfer_physics_level.csv")
    # support: distance of each NEW row to the nearest OLD row (OLD-standardized x4)
    so = StandardScaler().fit(xo); d = np.sqrt(((so.transform(xn)[:, None] - so.transform(xo)[None]) ** 2).sum(-1)).min(1)
    terc = pd.qcut(d, 3, labels=["near", "mid", "far"])
    srows = []
    for r in T.itertuples():
        p = np.array(r.pred_p.split(","), float)
        for t in ("near", "mid", "far"):
            m = np.asarray(terc == t)
            srows.append({"model": r.model, "support": t, "rows": int(m.sum()), "non_KH": int((yn[m] == 0).sum()),
                          "error_rate": float(np.mean((p[m] >= .5) != yn[m])), "nonKH_recall": float(np.mean(p[m][yn[m] == 0] < .5)) if (yn[m] == 0).any() else np.nan})
    S = pd.DataFrame(srows); S.to_csv(P1 / "transfer_support.csv", index=False)
    return R, lvl, S, d


if __name__ == "__main__":
    R, lvl, S, d = main()
    pd.set_option("display.width", 200)
    print(R.pivot_table(index="model", columns="step", values=["BA", "logloss"]).round(4).to_string())
    print(R[R.step == "raw"][["model", "AUC", "minority_AP"]].round(4).to_string(index=False))
    print(pd.Series(lvl).round(4).to_string())
    print(S.pivot_table(index="model", columns="support", values=["error_rate", "nonKH_recall"]).round(3).to_string())
    print("support distance quantiles", np.quantile(d, [.1, .5, .9]).round(3))
