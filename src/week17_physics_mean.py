"""Week 17 Phase 1A — anatomy of the historical physics mean (H / the M3 prior mean).

The historical mean (week9_phase1_11.fit_physics_mean) is an almost unpenalised logistic regression
(C = 1e6) of the revealed labels on StandardScaler(log h) fitted on the revealed rows only.  For every
training set that mattered (whole campaigns, NEW CV pools, Week 12 AL prefixes on NEW, Week 9 A0 prefixes
on OLD) we record its coefficient, intercept, the latent-mean magnitude over the whole campaign, the share
of points whose prior probability is saturated, whether the revealed labels are separable in log h, and how
the same quantities move with the regularization C ∈ {1e6, 1e2, 1, 0.1}.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from src.week17_audit import ROOT, campaigns

OUT = ROOT / "outputs/week17_model_and_acquisition/phase1"
CS = (1e6, 1e2, 1.0, 0.1)


def physics_fit(logh, y, rev, C):
    sc = StandardScaler().fit(logh[rev, None])
    lr = LogisticRegression(C=C, solver="lbfgs", max_iter=3000).fit(sc.transform(logh[rev, None]), y[rev])
    return float(lr.coef_[0, 0]), float(lr.intercept_[0]), lambda h: lr.decision_function(sc.transform(np.asarray(h)[:, None]))


def separable(logh, y, rev):
    h0, h1 = logh[rev][y[rev] == 0], logh[rev][y[rev] == 1]
    return bool(h0.max() < h1.min() or h1.max() < h0.min())


def describe(tag, logh, y, rev, test):
    rows = []
    for C in CS:
        b, a, lat = physics_fit(logh, y, rev, C)
        m_all = lat(logh); m_te = lat(logh[test])
        p_te = 1 / (1 + np.exp(-np.clip(m_te, -700, 700)))
        yt = y[test]
        ba = np.nanmean([np.mean((p_te >= .5)[yt == k] == k) if (yt == k).any() else np.nan for k in (0, 1)])
        rows.append({**tag, "C": C, "n_revealed": len(rev), "n_rev_minority": int(min((y[rev] == 0).sum(), (y[rev] == 1).sum())),
                     "separable": separable(logh, y, rev), "coef_std": b, "intercept": a,
                     "max_abs_latent_campaign": float(np.abs(m_all).max()), "median_abs_latent_campaign": float(np.median(np.abs(m_all))),
                     "share_saturated_5": float(np.mean(np.abs(m_all) > 5)), "share_saturated_10": float(np.mean(np.abs(m_all) > 10)),
                     "test_BA_H": float(ba), "test_logloss_H": float(np.mean(np.logaddexp(0, -(2 * yt - 1) * m_te)))})
    return rows


def jobs():
    from src.week12_development_common import load_splits
    from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
    C = campaigns(); J = []
    for camp in ("OLD", "NEW"):
        x4, lh, y = C[camp]
        J.append(({"set": "whole_campaign", "campaign": camp, "split": "all", "budget": len(y)}, lh, y, np.arange(len(y)), np.arange(len(y))))
    xn, ln, yn = C["NEW"]; xo, lo, yo = C["OLD"]
    # transfer: OLD-405 fit evaluated on NEW
    J.append(({"set": "transfer_OLD_to_NEW", "campaign": "OLD->NEW", "split": "all", "budget": 405}, None, None, None, None))
    sp = load_splits()
    for s in sp:
        tr = np.asarray(s["train_indices"]); te = np.asarray(s["test_indices"])
        J.append(({"set": "new_cv_pool", "campaign": "NEW", "split": s["split_id"], "budget": len(tr)}, ln, yn, tr, te))
    q = pd.read_csv(ROOT / "outputs/week12_startup_and_transfer_development/active_learning/query_paths.csv.gz")
    q = q[q.arm == "M3_margin__maximin8_continue"]
    tests = {s["split_id"]: np.asarray(s["test_indices"]) for s in sp}
    for sid, g in q.groupby("split_id"):
        order = g.sort_values("query_order").row_index.to_numpy(int)
        for b in (8, 12, 16, 24, 32, 48, 64, 80):
            rev = order[:b]
            if len(set(yn[rev])) == 2:
                J.append(({"set": "new_al_prefix", "campaign": "NEW", "split": sid, "budget": b}, ln, yn, rev, tests[sid]))
    pop, specs, paths = p13.load_inputs()
    for spec in specs:
        for b in (8, 12, 16, 24, 32, 48, 64, 80):
            rev = np.asarray(paths[spec.run_id][:b])
            if len(set(yo[rev])) == 2:
                J.append(({"set": "old_a0_prefix", "campaign": "OLD", "split": spec.run_id, "budget": b}, lo, yo, rev, np.asarray(spec.test_indices)))
    return J, C


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    J, Cm = jobs()
    rows = []
    for tag, lh, y, rev, te in J:
        if tag["set"] == "transfer_OLD_to_NEW":
            _, lo, yo = Cm["OLD"]; _, ln, yn = Cm["NEW"]
            for C in CS:
                b, a, lat = physics_fit(lo, yo, np.arange(len(yo)), C)
                m = lat(ln); p = 1 / (1 + np.exp(-np.clip(m, -700, 700)))
                ba = np.mean([np.mean((p >= .5)[yn == k] == k) for k in (0, 1)])
                rows.append({**tag, "C": C, "coef_std": b, "intercept": a, "max_abs_latent_campaign": float(np.abs(m).max()),
                             "median_abs_latent_campaign": float(np.median(np.abs(m))), "share_saturated_5": float(np.mean(np.abs(m) > 5)),
                             "test_BA_H": float(ba), "test_logloss_H": float(np.mean(np.logaddexp(0, -(2 * yn - 1) * m))),
                             "nonKH_recall_H": float(np.mean(p[yn == 0] < .5))})
            continue
        rows += describe(tag, lh, y, rev, te)
    df = pd.DataFrame(rows); df.to_csv(OUT / "physics_mean_anatomy.csv.gz", index=False)
    s = df.groupby(["set", "C"]).agg(n=("coef_std", "size"), separable=("separable", "mean"), coef_med=("coef_std", "median"),
                                     coef_p90=("coef_std", lambda x: np.quantile(np.abs(x), .9)), maxlat_med=("max_abs_latent_campaign", "median"),
                                     sat5=("share_saturated_5", "mean"), BA=("test_BA_H", "mean"), LL=("test_logloss_H", "mean"))
    s.to_csv(OUT / "physics_mean_anatomy_summary.csv")
    print(s.round(3).to_string())
    b = df[df.set.isin(["new_al_prefix", "old_a0_prefix"]) & (df.C == 1e6)].groupby(["set", "budget"]).agg(
        separable=("separable", "mean"), coef_med=("coef_std", "median"), maxlat_med=("max_abs_latent_campaign", "median"), sat5=("share_saturated_5", "mean"))
    b.to_csv(OUT / "physics_mean_by_budget.csv"); print(b.round(3).to_string())


if __name__ == "__main__":
    main()
