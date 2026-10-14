"""EX metrics addendum: completes the EX1/EX2 metrics from the STORED predictions (DEV repeats 5-8 only; no fit).

* every EX arm and rule: BA, q20 (unchanged, fold-mean), specificity, sensitivity, short-K sensitivity, Brier, log loss,
  AUC, with TP/FN/TN/FP summed over the four repeats and unique-simulation counts;
* J_trained at p >= 0.5 against J_trained at p >= pi_hat on the same predictions: changed decisions by class, scan
  speed and short-K membership (full IDs), q20, and how the balanced-accuracy gain trades against short-K detection;
* a POST-HOC threshold frontier (pooled ROC per repeat, with short-K sensitivity along it) - description, not a
  threshold-selection procedure;
* paired intervals from the Stage M class-stratified simulation-cluster bootstrap, conditional on the stored fits
  (a simulation predicted in four repeats is still one cluster).

Step: python -m src.jdl_ex_metrics_addendum
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import json

import numpy as np
import pandas as pd

import src.jdl_stage_m as SMM
from src.jdl_evaluate import boot_weights
from src.jdl_ex1 import EX as EX1_DIR, REPEATS, build_tasks_r
from src.jdl_ex2 import EX as EX2_DIR
from src.jdl_v2_evaluate import METRICS, wmetrics_thr

OUT = SMM.OUT / "exploratory" / "EX_METRICS_ADDENDUM"
RULES = ("p>=0.5", "p>=pi_hat")


def frame(pop, tasks):
    ts = [t for t in tasks if t["population"] == pop]
    ids, y = ts[0]["ids"], ts[0]["y"]
    fold = {r: np.zeros(len(ids), int) for r in REPEATS}; q20 = {r: np.zeros(len(ids), bool) for r in REPEATS}
    for t in ts:
        fold[t["repeat"]][t["test"]] = t["fold"]; q20[t["repeat"]][t["test"]] = t["q20"]
    sk = np.isin(ids, list(SMM.shortk(SMM.inputs_table())))
    return {"ids": ids, "y": y, "fold": fold, "q20": q20, "shortk": sk, "VX": ts[0]["VX"]}


def arrays(pr, arm, rep, b, ids):
    pos = {s: i for i, s in enumerate(ids)}
    g = pr[(pr.arm == arm) & (pr.repeat == rep) & (pr.budget == b) & (pr.prediction_status == "ok")]
    p = np.full(len(ids), np.nan); th = np.full(len(ids), np.nan)
    ii = g.sim_id.map(pos).to_numpy(int); p[ii] = g.p.astype(float).to_numpy(); th[ii] = g.pi_hat.astype(float).to_numpy()
    return p, th


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pr = pd.concat([pd.read_csv(EX1_DIR / "predictions_all.csv.gz"), pd.read_csv(EX2_DIR / "predictions_all.csv.gz")], ignore_index=True)
    tasks = build_tasks_r()
    rows, crow, flips, frontier = [], [], [], []
    for pop in ("NEW", "OLD", "POOLED"):
        F = frame(pop, tasks)
        ids, y, sk = F["ids"], F["y"], F["shortk"]
        fast = F["VX"] > SMM.FAST_VX
        W = boot_weights(y)
        arms = sorted(pr[pr.population == pop].arm.unique())
        P = pr[pr.population == pop]
        store = {}
        for arm in arms:
            for b in SMM.BUDGETS:
                for rule in RULES:
                    agg = {"TP": 0, "FN": 0, "TN": 0, "FP": 0, "shortK_detected": 0, "shortK_n": 0}
                    vals = {k: [] for k in METRICS}
                    for rep in REPEATS:
                        p, th = arrays(P, arm, rep, b, ids)
                        thr = np.full(len(ids), 0.5) if rule == "p>=0.5" else th
                        m, cnt, pred = wmetrics_thr(p, np.isfinite(p), y, sk, F["q20"][rep], F["fold"][rep], W, thr)
                        store[(arm, b, rule, rep)] = (p, thr, pred)
                        for k in METRICS:
                            vals[k].append(float(m[k][0]))
                        for k in agg:
                            agg[k] += cnt[k]
                    rows.append({"population": pop, "arm": arm, "budget": b, "rule": rule, **{k: float(np.mean(v)) for k, v in vals.items()},
                                 **{f"{k}_per_repeat": json.dumps([round(x, 4) for x in v]) for k, v in vals.items() if k in ("BA", "q20", "shortK_sensitivity", "AUC")},
                                 **{f"{k}_sum_over_4_repeats": v for k, v in agg.items()}, "unique_simulations": len(ids),
                                 "unique_positives": int((y == 1).sum()), "unique_negatives": int((y == 0).sum()), "unique_shortK": int(sk.sum())})
        # paired contrasts on the same cohort (same predictions where the arm is shared)
        pairs = [(("J_trained", "p>=pi_hat"), ("J_trained", "p>=0.5")), (("J_trained", "p>=0.5"), ("ACTIVE_E1", "p>=0.5")),
                 (("J_trained", "p>=0.5"), ("G3", "p>=0.5")), (("J_trained", "p>=0.5"), ("J", "p>=0.5")), (("J_trained", "p>=pi_hat"), ("ACTIVE_E1", "p>=0.5")),
                 (("J_trained", "p>=0.5"), ("Binary_matched", "p>=0.5"))]
        for (a1, r1), (a2, r2) in pairs:
            if a1 not in arms or a2 not in arms:
                continue
            for b in SMM.BUDGETS:
                per = {k: [] for k in METRICS}
                for rep in REPEATS:
                    p1, t1, _ = store[(a1, b, r1, rep)]; p2, t2, _ = store[(a2, b, r2, rep)]
                    common = np.isfinite(p1) & np.isfinite(p2)
                    m1, _, _ = wmetrics_thr(p1, common, y, sk, F["q20"][rep], F["fold"][rep], W, t1)
                    m2, _, _ = wmetrics_thr(p2, common, y, sk, F["q20"][rep], F["fold"][rep], W, t2)
                    for k in METRICS:
                        per[k].append(m1[k] - m2[k])
                for k in METRICS:
                    d = np.nanmean(np.vstack(per[k]), axis=0)
                    lo, hi = np.nanpercentile(d[1:], [2.5, 97.5]) if np.isfinite(d[1:]).any() else (np.nan, np.nan)
                    crow.append({"population": pop, "budget": b, "contrast": f"{a1} [{r1}] - {a2} [{r2}]", "metric": k, "estimate": float(d[0]),
                                 "per_repeat": json.dumps([round(float(x[0]), 4) for x in per[k]]), "cluster_bootstrap_lo": float(lo), "cluster_bootstrap_hi": float(hi),
                                 "status": "POST-HOC addendum (stored predictions; not a registered test)"})
        if pop != "NEW" or "J_trained" not in arms:
            continue
        # decisions changed by moving J_trained from p >= 0.5 to p >= pi_hat (same probabilities)
        for b in SMM.BUDGETS:
            changed = np.zeros(len(ids), int); lost_tp = np.zeros(len(ids), int); gained_tn = np.zeros(len(ids), int)
            for rep in REPEATS:
                _, _, d05 = store[("J_trained", b, "p>=0.5", rep)]; _, _, dpi = store[("J_trained", b, "p>=pi_hat", rep)]
                ch = d05 != dpi
                changed += ch; lost_tp += ch & (y == 1) & (d05 == 1); gained_tn += ch & (y == 0) & (d05 == 1)
            for i in np.flatnonzero(changed):
                flips.append({"budget": b, "sim_id": ids[i], "label": int(y[i]), "VX_m_s": float(F["VX"][i]), "fast_scan": bool(fast[i]), "shortK": bool(sk[i]),
                              "repeats_changed_of_4": int(changed[i]), "positive_lost_repeats": int(lost_tp[i]), "negative_gained_repeats": int(gained_tn[i])})
        # POST-HOC frontier: thresholds over the pooled predictions of each repeat (description only)
        for arm in [a for a in ("J_trained", "J", "ACTIVE_E1", "G3", "Binary_matched") if a in arms]:
            for rep in REPEATS:
                p, th, _ = store[(arm, 40, "p>=0.5", rep)]
                ok = np.isfinite(p)
                for c in np.unique(np.r_[p[ok], 0.5, 1.0 + 1e-9]):
                    pred = p >= c
                    frontier.append({"arm": arm, "budget": 40, "repeat": rep, "threshold": float(c),
                                     "sensitivity": float((pred & (y == 1) & ok).sum() / ((y == 1) & ok).sum()),
                                     "specificity": float((~pred & (y == 0) & ok).sum() / ((y == 0) & ok).sum()),
                                     "shortK_sensitivity": float((pred & sk & ok).sum() / (sk & ok).sum())})
    mt, ct, fl, fr = pd.DataFrame(rows), pd.DataFrame(crow), pd.DataFrame(flips), pd.DataFrame(frontier)
    fr["BA"] = 0.5 * (fr.sensitivity + fr.specificity)
    mt.to_csv(OUT / "metrics_with_counts.csv", index=False, lineterminator="\n")
    ct.to_csv(OUT / "paired_contrasts.csv", index=False, lineterminator="\n")
    fl.sort_values(["budget", "label", "VX_m_s"]).to_csv(OUT / "J_trained_rule_change_by_simulation.csv", index=False, lineterminator="\n")
    fr.to_csv(OUT / "POSTHOC_threshold_frontier_B40.csv", index=False, lineterminator="\n")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    new = mt[(mt.population == "NEW") & (mt.budget == 40)]
    print(new[["arm", "rule", "BA", "q20", "specificity", "sensitivity", "shortK_sensitivity", "brier", "log_loss", "AUC", "TP_sum_over_4_repeats", "FN_sum_over_4_repeats",
               "TN_sum_over_4_repeats", "FP_sum_over_4_repeats", "shortK_detected_sum_over_4_repeats"]].round(4).to_string(index=False))
    print(ct[(ct.population == "NEW") & (ct.budget == 40) & ct.metric.isin(["BA", "q20", "shortK_sensitivity", "specificity", "sensitivity"])].round(4).to_string(index=False))
    print(fl[fl.budget == 40].groupby(["label", "fast_scan", "shortK"]).repeats_changed_of_4.agg(["count", "sum"]).to_string())


if __name__ == "__main__":
    main()
