"""POST-HOC descriptive tables for the exploratory report (no new fit; stored EX1/EX2 predictions only).

Everything here was computed after EX1/EX2 results were seen.  It describes where the registered effects come from
(by full simulation ID) and places the EX2 candidate next to the frozen systems; none of it is a registered test.
  * exports the EX2 predictions from the resumable cache to exploratory/EX2_trained_response_prior/predictions_all.csv.gz
  * POSTHOC_descriptive/complete_system_contrasts.csv  (same estimator and bootstrap as EX1)
  * POSTHOC_descriptive/NEW_negatives_by_rule.csv, NEW_positive_misses_by_rule.csv, NEW_missed_positive_ids.csv
  * POSTHOC_descriptive/NEW_BA_inside_vs_outside_fast_corner.csv and NEW_fast_corner_reference_rule.json (the Week 19
    VX > 0.85 cut used as a fixed reference point, not as a learner)
  * POSTHOC_descriptive/AUC_per_repeat.csv (AUC was listed among the EX2 manifest outcomes but not computed by its
    evaluate step; completed here from the stored probabilities, all arms)
  * POSTHOC_descriptive/EX2_learned_response_hyperparameters.csv (medians over all fits; corrects the mislabelled
    `learned_lengthscales_median_NEW_B40` field of EX2_RESULTS.json, which lists the first three NEW B40 fits)

Step: python -m src.jdl_ex_descriptive
"""
from __future__ import annotations

import gzip
import json

import numpy as np
import pandas as pd

import src.jdl_stage_m as SMM
from src.jdl_evaluate import boot_weights
from src.jdl_ex1 import EX as EX1_DIR, REPEATS, build_tasks_r
from src.jdl_ex2 import CACHE as EX2_CACHE, EX as EX2_DIR

OUT = SMM.OUT / "exploratory" / "POSTHOC_descriptive"
RULES = ("p>=0.5", "p>=pi_hat")
INPUTS = ("P", "VX", "LS", "ST")


def load_predictions():
    e1 = pd.read_csv(EX1_DIR / "predictions_all.csv.gz")
    rows = []
    for f in sorted(EX2_CACHE.glob("*__J_trained.json.gz")):
        r = json.loads(gzip.decompress(f.read_bytes()))
        rows += [{**p, "pi_hat": r["fit"]["paid_prevalence"]} for p in r["predictions"]]
    e2 = pd.DataFrame(rows)
    e2.to_csv(EX2_DIR / "predictions_all.csv.gz", index=False, lineterminator="\n", compression={"method": "gzip", "mtime": 0})
    return pd.concat([e1[["population", "repeat", "fold", "budget", "arm", "sim_id", "p", "pi_hat", "prediction_status"]],
                      e2[["population", "repeat", "fold", "budget", "arm", "sim_id", "p", "pi_hat", "prediction_status"]]], ignore_index=True)


def decisions(pr, pop, ids):
    pos = {s: i for i, s in enumerate(ids)}
    dec, prob = {}, {}
    for (arm, rep, b), g in pr[(pr.population == pop) & (pr.prediction_status == "ok")].groupby(["arm", "repeat", "budget"]):
        p = np.full(len(ids), np.nan); th = np.full(len(ids), np.nan)
        ii = g.sim_id.map(pos).to_numpy(int); p[ii] = g.p.to_numpy(float); th[ii] = g.pi_hat.to_numpy(float)
        prob[(arm, rep, b)] = p
        for rule, thr in (("p>=0.5", np.full(len(ids), 0.5)), ("p>=pi_hat", th)):
            dec[(arm, rep, b, rule)] = np.where(np.isfinite(p), (np.nan_to_num(p) >= np.nan_to_num(thr, nan=0.5)).astype(float), np.nan)
    return dec, prob


def contrasts(dec, y, W, comps, pop):
    def ba(d, mask):
        posm, negm = mask & (y == 1), mask & (y == 0); dd = np.nan_to_num(d)
        sens = (W @ (posm * dd)) / (W @ posm); spec = (W @ (negm * (1 - dd))) / (W @ negm)
        return 0.5 * (sens + spec), spec, sens
    out = []
    for (a1, r1), (a2, r2) in comps:
        for b in SMM.BUDGETS:
            if (a1, REPEATS[0], b, r1) not in dec or (a2, REPEATS[0], b, r2) not in dec:
                continue
            per = {"BA": [], "specificity": [], "sensitivity": []}
            for rep in REPEATS:
                d1, d2 = dec[(a1, rep, b, r1)], dec[(a2, rep, b, r2)]
                mask = np.isfinite(d1) & np.isfinite(d2)
                m1, m2 = ba(d1, mask), ba(d2, mask)
                for k, i in (("BA", 0), ("specificity", 1), ("sensitivity", 2)):
                    per[k].append(m1[i] - m2[i])
            for k, v in per.items():
                d = np.nanmean(np.vstack(v), axis=0); lo, hi = np.nanpercentile(d[1:], [2.5, 97.5])
                out.append({"population": pop, "budget": b, "metric": k, "contrast": f"{a1} [{r1}] - {a2} [{r2}]", "estimate": float(d[0]),
                            "per_repeat": json.dumps([round(float(x[0]), 6) for x in v]), "cluster_bootstrap_lo": float(lo), "cluster_bootstrap_hi": float(hi),
                            "status": "POST-HOC descriptive (not registered)"})
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pr = load_predictions()
    tasks = build_tasks_r()
    inp = SMM.inputs_table(); sk = SMM.shortk(inp)
    crow, neg_rows, miss_rows, miss_ids, corner_rows, auc_rows = [], [], [], [], [], []
    from sklearn.metrics import roc_auc_score
    for pop in ("NEW", "OLD", "POOLED"):
        t = [t for t in tasks if t["population"] == pop][0]
        ids, y, A, VX = t["ids"], t["y"], t["A"], t["VX"]
        W = boot_weights(y)
        dec, prob = decisions(pr, pop, ids)
        for (arm, rep, b), p in prob.items():                                # EX2 manifest outcome omitted by its evaluate step
            ok = np.isfinite(p)
            auc_rows.append({"population": pop, "arm": arm, "repeat": rep, "budget": b, "n": int(ok.sum()), "AUC": float(roc_auc_score(y[ok], p[ok]))})
        arms = sorted({k[0] for k in dec})
        comps = [(("J_trained", "p>=pi_hat"), (a, r)) for a in arms for r in RULES if (a, r) != ("J_trained", "p>=pi_hat")]
        comps += [(("J_trained", "p>=0.5"), ("Binary_matched", "p>=0.5"))]
        crow += contrasts(dec, y, W, comps, pop)
        if pop != "NEW":
            continue
        fast = VX > SMM.FAST_VX
        is_sk = np.array([s in sk for s in ids], bool)
        z = np.where(np.isfinite(A) & (A > 0), np.log(np.where(np.isfinite(A) & (A > 0), A, 1.0) / SMM.Z_REF_UM), np.nan)
        for i in np.where(y == 0)[0]:
            r = {"sim_id": ids[i], "VX_m_s": float(VX[i]), "A_um": float(A[i]), "z_log_A_over_111": float(z[i]), "fast_scan": bool(fast[i]), "early_end": bool(t["early_end"][i])}
            for arm in arms:
                r[f"mean_p_{arm}_B40"] = float(np.nanmean([prob[(arm, rep, 40)][i] for rep in REPEATS]))
                for rule in RULES:
                    r[f"FP_{arm}_{rule}_B40_of4"] = int(np.nansum([dec[(arm, rep, 40, rule)][i] for rep in REPEATS]))
            neg_rows.append(r)
        for arm in arms:                                                     # balanced accuracy inside and outside the fast-scan corner
            for rule in RULES:
                for b in SMM.BUDGETS:
                    for region, m in (("fast_scan_VX_gt_0.85", fast), ("rest", ~fast)):
                        per = []
                        for rep in REPEATS:
                            d = dec[(arm, rep, b, rule)]; ok = np.isfinite(d) & m
                            tp, fn_ = ((d == 1) & (y == 1) & ok).sum(), ((d == 0) & (y == 1) & ok).sum()
                            tn, fp = ((d == 0) & (y == 0) & ok).sum(), ((d == 1) & (y == 0) & ok).sum()
                            per.append((tp / max(tp + fn_, 1), tn / max(tn + fp, 1), int(tp + fn_), int(tn + fp)))
                        P = np.array(per)
                        corner_rows.append({"arm": arm, "rule": rule, "budget": b, "region": region, "positives": int(P[0, 2]), "negatives": int(P[0, 3]),
                                            "sensitivity": float(P[:, 0].mean()), "specificity": float(P[:, 1].mean()) if P[0, 3] else np.nan,
                                            "BA": float(0.5 * (P[:, 0].mean() + P[:, 1].mean())) if P[0, 3] else np.nan,
                                            "BA_per_repeat": json.dumps([round(float(0.5 * (se + sp)), 4) for se, sp, _, _ in per]) if P[0, 3] else "[]"})
        for arm in arms:
            for rule in RULES:
                for b in SMM.BUDGETS:
                    fn = np.vstack([(y == 1) & (dec[(arm, rep, b, rule)] == 0) for rep in REPEATS])        # repeats x sims
                    per_rep = fn.sum(1)
                    miss_rows.append({"arm": arm, "rule": rule, "budget": b, "positives": int((y == 1).sum()), "FN_mean_per_repeat": float(per_rep.mean()),
                                      "FN_fast_scan_mean": float(fn[:, fast].sum(1).mean()), "FN_not_fast_mean": float(fn[:, ~fast].sum(1).mean()),
                                      "FN_shortK_mean": float(fn[:, is_sk].sum(1).mean()), "positives_fast_scan": int(((y == 1) & fast).sum()),
                                      "positives_shortK": int(((y == 1) & is_sk).sum())})
                    if b == 40 and arm in ("J", "J_trained") and rule == "p>=pi_hat":
                        for j in np.where(fn.sum(0) >= 2)[0]:
                            miss_ids.append({"arm": arm, "rule": rule, "budget": b, "sim_id": ids[j], "missed_in_repeats_of4": int(fn[:, j].sum()), "VX_m_s": float(VX[j]),
                                             "A_um": float(A[j]), "fast_scan": bool(fast[j]), "shortK": bool(is_sk[j]),
                                             "mean_p": float(np.nanmean([prob[(arm, rep, 40)][j] for rep in REPEATS]))})
    ct = pd.DataFrame(crow); ng = pd.DataFrame(neg_rows); ms = pd.DataFrame(miss_rows); mi = pd.DataFrame(miss_ids)
    ct.to_csv(OUT / "complete_system_contrasts.csv", index=False, lineterminator="\n")
    ng.sort_values("VX_m_s").to_csv(OUT / "NEW_negatives_by_rule.csv", index=False, lineterminator="\n")
    ms.to_csv(OUT / "NEW_positive_misses_by_rule.csv", index=False, lineterminator="\n")
    mi.to_csv(OUT / "NEW_missed_positive_ids.csv", index=False, lineterminator="\n")
    cr = pd.DataFrame(corner_rows); cr.to_csv(OUT / "NEW_BA_inside_vs_outside_fast_corner.csv", index=False, lineterminator="\n")
    au = pd.DataFrame(auc_rows).sort_values(["population", "budget", "arm", "repeat"]); au.to_csv(OUT / "AUC_per_repeat.csv", index=False, lineterminator="\n")
    # reference point, not a learner: the fast-scan cut was set in Week 19 after inspecting these NEW data
    t = [t for t in tasks if t["population"] == "NEW"][0]; ref_fast = t["VX"] > SMM.FAST_VX
    sens_ref = float(((t["y"] == 1) & ~ref_fast).sum() / (t["y"] == 1).sum()); spec_ref = float(((t["y"] == 0) & ref_fast).sum() / (t["y"] == 0).sum())
    (OUT / "NEW_fast_corner_reference_rule.json").write_text(json.dumps({"rule": "predict no Keyhole iff VX > 0.85 m/s (Week 19 cut; NOT train-only)", "sensitivity": sens_ref,
                                                                         "specificity": spec_ref, "BA": 0.5 * (sens_ref + spec_ref)}, indent=1), encoding="utf-8")
    # learned response hyperparameters (all fits)
    f = pd.read_csv(EX2_DIR / "fit_log.csv")
    ell = np.vstack(f.f_lengthscale.apply(lambda s: np.array(json.loads(s), float)).to_numpy())
    hp = []
    for (pop, b), g in f.groupby(["population", "budget"]):
        L = ell[g.index.to_numpy()]
        hp.append({"population": pop, "budget": b, "fits": len(g), **{f"median_lengthscale_{n}": float(np.median(L[:, k])) for k, n in enumerate(INPUTS)},
                   **{f"at_upper_bound_20_{n}": int((L[:, k] >= 19.99).sum()) for k, n in enumerate(INPUTS)},
                   **{f"at_lower_bound_0.05_{n}": int((L[:, k] <= 0.0501).sum()) for k, n in enumerate(INPUTS)},
                   "median_amplitude": float(g.f_amplitude.median()), "fits_with_bound_warning": int(g.warnings.notna().sum()), "frozen_lengthscale": 1.5, "frozen_amplitude": 0.6})
    hp = pd.DataFrame(hp); hp.to_csv(OUT / "EX2_learned_response_hyperparameters.csv", index=False, lineterminator="\n")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(ct[ct.metric == "BA"].round(4).to_string())
    print(ng.round(3).to_string())
    print(ms[ms.budget == 40].round(2).to_string())
    print(mi.round(3).to_string())
    print(cr[cr.budget == 40].round(3).to_string())
    print(au.groupby(["population", "budget", "arm"]).AUC.mean().round(3).unstack().to_string())
    print(json.loads((OUT / "NEW_fast_corner_reference_rule.json").read_text(encoding="utf-8")))
    print(hp.round(3).to_string())


if __name__ == "__main__":
    main()
