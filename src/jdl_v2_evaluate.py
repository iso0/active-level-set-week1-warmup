"""V2 comparison evaluation (definitions frozen in v2_model_comparison/V2_MANIFEST.json).  Reads the V2 cache; fits nothing.

Per arm, repeat and budget (pooled over the five folds of a repeat, so every NEW simulation is scored once per repeat):
BA, unchanged q20 accuracy (fold-mean), specificity, sensitivity, short-K sensitivity (the ten existing short-K
simulations), Brier, log loss and AUC, with TP/FN/TN/FP counts.  Decision rules: p >= 0.5 for every arm (primary) and,
for the probabilistic arms, the declared train-only p >= pi_hat (secondary).  Contrasts are paired on identical
splits and budgets; intervals come from the Stage M class-stratified simulation-cluster bootstrap (shared multiplicities;
conditional on the stored fits).

Step: python -m src.jdl_v2_comparison evaluate
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import src.jdl_stage_m as SMM
import src.jdl_v2_comparison as C
from src.jdl_evaluate import boot_weights, population_frame

METRICS = ("BA", "q20", "specificity", "sensitivity", "shortK_sensitivity", "brier", "log_loss", "AUC")
PRACTICAL_GAIN = 0.01


def wmetrics_thr(p, avail, y, sk, q20, fold, W, thr):
    """src.jdl_evaluate.wmetrics with a per-simulation decision threshold (identical to it at thr = 0.5)."""
    av = avail.astype(float); pe = np.where(avail, p, 0.5); th = np.where(avail, thr, 0.5)
    pred = (pe >= th).astype(float)
    pos, neg = av * (y == 1), av * (y == 0)
    out = {}
    with np.errstate(invalid="ignore", divide="ignore"):
        sens = (W @ (pos * pred)) / (W @ pos); spec = (W @ (neg * (1 - pred))) / (W @ neg)
        out.update({"BA": 0.5 * (sens + spec), "sensitivity": sens, "specificity": spec})
        skm = av * sk
        out["shortK_sensitivity"] = (W @ (skm * pred)) / (W @ skm) if skm.sum() > 0 else np.full(W.shape[0], np.nan)
        out["brier"] = (W @ (av * (pe - y) ** 2)) / (W @ av)
        pc = np.clip(pe, 1e-12, 1 - 1e-12)
        out["log_loss"] = (W @ (av * -(y * np.log(pc) + (1 - y) * np.log(1 - pc)))) / (W @ av)
        correct = (pred == y).astype(float); accs = []
        for f in np.unique(fold[fold > 0]):
            m = av * q20 * (fold == f)
            if m.sum() == 0:
                continue
            den = W @ m
            accs.append(np.where(den > 0, (W @ (m * correct)) / np.where(den > 0, den, 1), np.nan))
        out["q20"] = np.nanmean(np.vstack(accs), axis=0) if accs else np.full(W.shape[0], np.nan)
        P, N = np.flatnonzero(pos > 0), np.flatnonzero(neg > 0)
        if len(P) and len(N):
            Cm = (pe[P][:, None] > pe[N][None, :]) + 0.5 * (pe[P][:, None] == pe[N][None, :])
            out["AUC"] = np.einsum("di,ij,dj->d", W[:, P], Cm, W[:, N]) / (W[:, P].sum(1) * W[:, N].sum(1))
        else:
            out["AUC"] = np.full(W.shape[0], np.nan)
    counts = {"TP": int(((pred == 1) & (y == 1) & avail).sum()), "FN": int(((pred == 0) & (y == 1) & avail).sum()),
              "TN": int(((pred == 0) & (y == 0) & avail).sum()), "FP": int(((pred == 1) & (y == 0) & avail).sum()),
              "shortK_detected": int(((pred == 1) & sk & avail).sum()), "shortK_n": int((sk & avail).sum()), "n_available": int(avail.sum())}
    return out, counts, pred


def series(preds, fits, arm, rep, b, ids):
    pos = {s: i for i, s in enumerate(ids)}
    g = preds[(preds.arm == arm) & (preds.repeat == rep) & (preds.budget == b)]
    p = np.full(len(ids), np.nan); thr = np.full(len(ids), np.nan)
    ok = g[np.isfinite(g.p.astype(float))]
    p[ok.sim_id.map(pos).to_numpy(int)] = ok.p.astype(float).to_numpy()
    pih = {(f["fold"]): f["pi_hat"] for f in fits if f["arm"] == arm and f["repeat"] == rep and f["budget"] == b}
    thr[g.sim_id.map(pos).to_numpy(int)] = g.fold.map(pih).to_numpy(float)
    return p, thr


def main():
    fits, preds = C.load()
    if len(fits) != 180:
        raise SystemExit(f"expected 180 checkpoint records, found {len(fits)}")
    status = pd.Series([f["status"] for f in fits]).value_counts().to_dict()
    tasks = [t for t in SMM.build_tasks() if t["population"] == C.POP]
    F = population_frame(C.POP, tasks)
    ids, y, sk, VX = F["ids"], F["y"], F["shortk"], F["VX"]
    fast = VX > SMM.FAST_VX                                                    # evaluator-only description
    W = boot_weights(y)
    C.OUT.mkdir(parents=True, exist_ok=True)
    preds.to_csv(C.OUT / "predictions_all.csv.gz", index=False, lineterminator="\n", compression={"method": "gzip", "mtime": 0})
    rows, cache, corner = [], {}, []
    for arm in C.ARMS:
        for rep in C.REPEATS:
            for b in C.BUDGETS:
                p, thr = series(preds, fits, arm, rep, b, ids)
                avail = np.isfinite(p)
                for rule in ("p>=0.5", "p>=pi_hat"):
                    if rule == "p>=pi_hat" and arm not in C.PROBABILISTIC:
                        continue
                    th = np.full(len(ids), 0.5) if rule == "p>=0.5" else thr
                    m, cnt, pred = wmetrics_thr(p, avail, y, sk, F["q20"][rep], F["fold"][rep], W, th)
                    cache[(arm, rep, b, rule)] = (p, th)
                    rows.append({"arm": arm, "repeat": rep, "budget": b, "rule": rule, **{k: float(v[0]) for k, v in m.items()}, **cnt,
                                 "unique_simulations": len(ids), "unique_positives": int((y == 1).sum()), "unique_negatives": int((y == 0).sum())})
                    for region, msk in (("fast_scan_VX_gt_0.85", fast), ("rest", ~fast)):
                        a = avail & msk
                        corner.append({"arm": arm, "repeat": rep, "budget": b, "rule": rule, "region": region,
                                       "TP": int(((pred == 1) & (y == 1) & a).sum()), "FN": int(((pred == 0) & (y == 1) & a).sum()),
                                       "TN": int(((pred == 0) & (y == 0) & a).sum()), "FP": int(((pred == 1) & (y == 0) & a).sum())})
    mt = pd.DataFrame(rows); mt.to_csv(C.OUT / "metrics_per_repeat.csv", index=False, lineterminator="\n")
    cr = pd.DataFrame(corner)
    agg = cr.groupby(["arm", "budget", "rule", "region"])[["TP", "FN", "TN", "FP"]].sum().reset_index()
    with np.errstate(invalid="ignore", divide="ignore"):
        agg["sensitivity"] = agg.TP / (agg.TP + agg.FN); agg["specificity"] = agg.TN / (agg.TN + agg.FP)
    agg["BA"] = 0.5 * (agg.sensitivity + agg.specificity)
    agg["note"] = "evaluation-only description; counts summed over both repeats (each simulation appears once per repeat)"
    agg.to_csv(C.OUT / "fast_scan_corner_errors.csv", index=False, lineterminator="\n")
    # ------------------------------------------------------------------ contrasts
    crow = []
    for family, pairs in C.CONTRASTS.items():
        for a1, a2 in pairs:
            for b in C.BUDGETS:
                for rule in ("p>=0.5", "p>=pi_hat"):
                    if rule == "p>=pi_hat" and not (a1 in C.PROBABILISTIC and a2 in C.PROBABILISTIC):
                        continue
                    per_rep, cohort = [], []
                    for rep in C.REPEATS:
                        p1, t1 = cache[(a1, rep, b, rule)]; p2, t2 = cache[(a2, rep, b, rule)]
                        common = np.isfinite(p1) & np.isfinite(p2)
                        m1, _, _ = wmetrics_thr(p1, common, y, sk, F["q20"][rep], F["fold"][rep], W, t1)
                        m2, _, _ = wmetrics_thr(p2, common, y, sk, F["q20"][rep], F["fold"][rep], W, t2)
                        per_rep.append({k: m1[k] - m2[k] for k in METRICS}); cohort.append(int(common.sum()))
                    for k in METRICS:
                        d = np.nanmean(np.vstack([r[k] for r in per_rep]), axis=0)
                        lo, hi = np.nanpercentile(d[1:], [2.5, 97.5]) if np.isfinite(d[1:]).any() else (np.nan, np.nan)
                        crow.append({"family": family, "arm": a1, "ref": a2, "budget": b, "rule": rule, "metric": k, "estimate_mean_over_repeats": float(d[0]),
                                     "per_repeat": json.dumps([float(r[k][0]) for r in per_rep]), "cluster_bootstrap_lo": float(lo), "cluster_bootstrap_hi": float(hi),
                                     "common_cohort_per_repeat": json.dumps(cohort)})
    ct = pd.DataFrame(crow); ct.to_csv(C.OUT / "contrasts.csv", index=False, lineterminator="\n")
    # ------------------------------------------------------------------ decision (Astra's screen; reported regardless)
    g = lambda metric, a1="V2_EP_mixture", a2="Binary_V2_EP", b=40, rule="p>=0.5": ct[(ct.arm == a1) & (ct.ref == a2) & (ct.budget == b) & (ct.rule == rule) & (ct.metric == metric)].iloc[0]
    ba, sp, ll = g("BA"), g("specificity"), g("log_loss")
    c1, c2, c3 = ba.estimate_mean_over_repeats >= PRACTICAL_GAIN - 1e-12, sp.estimate_mean_over_repeats >= -1e-12, ll.estimate_mean_over_repeats <= 1e-12
    dec = {"primary": {"contrast": "NEW B40 BA at p >= 0.5, V2_EP_mixture - Binary_V2_EP", "estimate": float(ba.estimate_mean_over_repeats),
                       "interval": [float(ba.cluster_bootstrap_lo), float(ba.cluster_bootstrap_hi)], "per_repeat": json.loads(ba.per_repeat)},
           "screen": {"BA_gain_ge_0.01": bool(c1), "specificity_not_lower": bool(c2), "log_loss_not_worse": bool(c3),
                      "specificity_difference": float(sp.estimate_mean_over_repeats), "log_loss_difference": float(ll.estimate_mean_over_repeats),
                      "verdict": "PROMISING FOR FURTHER MODEL WORK (development screen only)" if (c1 and c2 and c3) else "SCREEN NOT PASSED"},
           "tradeoffs_B40_p>=0.5": {m: float(g(m).estimate_mean_over_repeats) for m in ("q20", "shortK_sensitivity", "sensitivity", "AUC", "brier")},
           "mechanism_B40_BA": {f"{a1} - {a2}": [float(g("BA", a1, a2).estimate_mean_over_repeats), float(g("BA", a1, a2).cluster_bootstrap_lo), float(g("BA", a1, a2).cluster_bootstrap_hi)]
                                for a1, a2 in C.CONTRASTS["mechanism"]},
           "system_B40_BA": {f"{a1} - {a2}": [float(g("BA", a1, a2).estimate_mean_over_repeats), float(g("BA", a1, a2).cluster_bootstrap_lo), float(g("BA", a1, a2).cluster_bootstrap_hi)]
                             for a1, a2 in C.CONTRASTS["system"]},
           "fit_status_counts": status, "note": "practical threshold, not a forecast or significance test; development DEV repeats 1-2 of inspected simulations, not confirmation"}
    (C.OUT / "V2_DECISION.json").write_text(json.dumps(dec, indent=1), encoding="utf-8")
    # ------------------------------------------------------------------ mechanism and numerical logs
    path = pd.read_csv(SMM.SM / "paths.csv"); path = path[path.population == C.POP]
    mrows, nrows, pneg = [], [], []
    for f in fits:
        key = {"repeat": f["repeat"], "fold": f["fold"], "budget": f["budget"], "arm": f["arm"]}
        if f["arm"] in ("V2_EP_mixture", "Binary_V2_EP") and f["status"] == "ok":
            mech = f["mechanism"]
            for c_ in mech["components"]:
                mrows.append({**key, **{k: v for k, v in c_.items()}, "fallback": mech["fallback"], "theta_mixture_mean": mech["theta_mixture_mean"],
                              "theta_mixture_sd": mech["theta_mixture_sd"], "test_mean_between_component_h_var": mech["test_mean_between_component_h_var"], "solve_count": mech["solve_count"]})
            ids_paid = path[(path.repeat == f["repeat"]) & (path.fold == f["fold"])].sort_values("query_index").sim_id.tolist()[:f["budget"]]
            for n_ in mech["paid_negatives"]:
                pneg.append({**key, "sim_id": ids_paid[n_["index_in_prefix"]], "p": n_["p"], "h_mean": n_["h_mean"], "h_sd": n_["h_sd"]})
        nrows.append({**key, "status": f["status"], "error": f.get("error"), "reused_from": f.get("reused_from"), "method": f.get("method"),
                      "ep_control": f.get("ep_control"), "solver_status": f.get("solver_status"), "gradient_inf": f.get("gradient_inf"),
                      "f_amplitude": f.get("f_amplitude"), "f_lengthscale": json.dumps(f.get("f_lengthscale")) if f.get("f_lengthscale") is not None else None,
                      "warnings": f.get("warnings"), "stump_type": (f.get("stump") or {}).get("type"), "stump_cut_VX_m_s": f.get("cut_in_VX_m_s"),
                      "stump_orientation": (f.get("stump") or {}).get("orientation"), "stump_paid_BA": (f.get("stump") or {}).get("paid_BA"),
                      "n_paid": f["n_paid"], "n_neg_paid": f["n_neg_paid"], "n_response": f["n_response"], "pi_hat": f["pi_hat"], "seconds": f.get("seconds")})
    pd.DataFrame(mrows).to_csv(C.OUT / "component_masses_and_moments.csv", index=False, lineterminator="\n")
    pd.DataFrame(nrows).to_csv(C.OUT / "fit_log.csv", index=False, lineterminator="\n")
    pd.DataFrame(pneg).to_csv(C.OUT / "paid_negatives.csv", index=False, lineterminator="\n")
    neg = preds[preds.sim_id.isin(set(np.array(ids)[y == 0]))]
    neg.to_csv(C.OUT / "heldout_negative_predictions.csv", index=False, lineterminator="\n")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    show = mt.groupby(["budget", "rule", "arm"])[list(METRICS) + ["TP", "FN", "TN", "FP", "shortK_detected"]].mean().round(3)
    print(show.to_string())
    print(ct[(ct.metric == "BA")].round(4).to_string())
    print(json.dumps(dec, indent=1))
    return mt, ct, dec


if __name__ == "__main__":
    main()
