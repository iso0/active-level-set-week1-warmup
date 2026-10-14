"""Stage M evaluation (frozen in STUDY_MANIFEST.json before any comparative fit).  Reads the run cache; fits nothing.

Per population, arm, repeat and budget (pooled over the five folds of a repeat, i.e. every simulation once):
BA at p >= 0.5, unchanged q20 accuracy (fold-mean, folds without q20 points skipped), specificity, sensitivity,
short-K sensitivity (the ten existing NEW short-K simulations, 0 < K/(F+C+K) < 0.10), Brier, log loss, AUC.
Contrasts are paired on identical tasks and restricted to the common available cohort; uncertainty is a
simulation-cluster bootstrap (class-stratified multiplicities per simulation, shared by both repeats, both budgets and
all arms), conditional on the stored fits.

Step: python -m src.jdl_stage_m evaluate
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.jdl_stage_m import ARMS, BUDGETS, OUT, POPS, REPEATS, SM, build_tasks, inputs_table, load_cache, shortk

PAIRS = (("J", "Binary_matched"), ("J", "J_fixed_theta"), ("J", "J_no_delta"), ("J", "ACTIVE_E1"), ("J", "G3"),
         ("Binary_matched", "G3"), ("ACTIVE_E1", "G3"), ("J_no_delta", "Binary_matched"))
METRICS = ("BA", "q20", "specificity", "sensitivity", "shortK_sensitivity", "brier", "log_loss", "AUC")
N_BOOT, BOOT_SEED = 2000, 20261013
PRACTICAL_GAIN, PRACTICAL_LOSS = 0.01, -0.01


def population_frame(pop, tasks):
    """Evaluator-only arrays for one population in a fixed simulation order."""
    ts = [t for t in tasks if t["population"] == pop]
    ids = ts[0]["ids"]; y = ts[0]["y"]
    fold = {r: np.zeros(len(ids), int) for r in REPEATS}; q20 = {r: np.zeros(len(ids), bool) for r in REPEATS}
    for t in ts:
        fold[t["repeat"]][t["test"]] = t["fold"]; q20[t["repeat"]][t["test"]] = t["q20"]
    sk = np.isin(ids, list(shortk(inputs_table())))
    return {"ids": ids, "y": y, "fold": fold, "q20": q20, "shortk": sk, "VX": ts[0]["VX"], "early_end": ts[0]["early_end"], "A": ts[0]["A"]}


def boot_weights(y, draws=N_BOOT, seed=BOOT_SEED):
    rng = np.random.default_rng(seed)
    pos, neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
    W = np.zeros((draws + 1, len(y))); W[0] = 1.0
    for d in range(1, draws + 1):
        W[d] += np.bincount(rng.choice(pos, len(pos)), minlength=len(y)) + np.bincount(rng.choice(neg, len(neg)), minlength=len(y))
    return W


def wmetrics(p, avail, y, sk, q20, fold, W):
    """Weighted metrics (rows of W = bootstrap draws; row 0 = observed sample).  Returns dict of (D,) arrays."""
    av = avail.astype(float); pe = np.where(avail, p, 0.5)
    pred = (pe >= 0.5).astype(float)
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
            C = (pe[P][:, None] > pe[N][None, :]) + 0.5 * (pe[P][:, None] == pe[N][None, :])
            out["AUC"] = np.einsum("di,ij,dj->d", W[:, P], C, W[:, N]) / (W[:, P].sum(1) * W[:, N].sum(1))
        else:
            out["AUC"] = np.full(W.shape[0], np.nan)
    return out


def series(preds, pop, arm, rep, b, ids):
    g = preds[(preds.population == pop) & (preds.arm == arm) & (preds.repeat == rep) & (preds.budget == b)]
    pos = {s: i for i, s in enumerate(ids)}
    p = np.full(len(ids), np.nan)
    ok = g[(g.prediction_status == "ok") & np.isfinite(g.p.astype(float))]
    p[ok.sim_id.map(pos).to_numpy(int)] = ok.p.astype(float).to_numpy()
    n_rows = len(g)
    return p, n_rows


def main():
    fits, preds, orc = load_cache()
    if len(fits) != 360:
        raise SystemExit(f"expected 360 fit requests, found {len(fits)}")
    tasks = build_tasks()
    SM.mkdir(parents=True, exist_ok=True)
    preds.to_csv(SM / "predictions_all.csv.gz", index=False, lineterminator="\n", compression={"method": "gzip", "mtime": 0})
    fits.to_csv(SM / "fit_log.csv", index=False, lineterminator="\n")
    orc.to_csv(SM / "baseline_oracle_response_NOT_DEPLOYABLE.csv.gz", index=False, lineterminator="\n", compression={"method": "gzip", "mtime": 0})
    rows, prow, frows = [], [], []
    for pop in POPS:
        F = population_frame(pop, tasks)
        ids, y, sk = F["ids"], F["y"], F["shortk"]
        W = boot_weights(y)
        cache = {}
        for arm in ARMS:
            for rep in REPEATS:
                for b in BUDGETS:
                    p, n_rows = series(preds, pop, arm, rep, b, ids)
                    avail = np.isfinite(p)
                    cache[(arm, rep, b)] = p
                    m = wmetrics(p, avail, y, sk, F["q20"][rep], F["fold"][rep], W[:1])
                    rows.append({"population": pop, "arm": arm, "repeat": rep, "budget": b, "n_sims": len(ids), "n_available": int(avail.sum()),
                                 "n_unavailable": int((~avail).sum()), "n_neg_available": int((avail & (y == 0)).sum()),
                                 **{k: float(v[0]) for k, v in m.items()}})
                    for f in range(1, 6):
                        mk = F["fold"][rep] == f
                        mf = wmetrics(np.where(mk, p, np.nan), avail & mk, y, sk, F["q20"][rep], np.where(mk, f, 0), W[:1])
                        frows.append({"population": pop, "arm": arm, "repeat": rep, "fold": f, "budget": b, "n_available": int((avail & mk).sum()),
                                      **{k: float(v[0]) for k, v in mf.items()}})
        for a1, a2 in PAIRS:
            for b in BUDGETS:
                per_rep, draws = [], []
                for rep in REPEATS:
                    p1, p2 = cache[(a1, rep, b)], cache[(a2, rep, b)]
                    common = np.isfinite(p1) & np.isfinite(p2)
                    m1 = wmetrics(p1, common, y, sk, F["q20"][rep], F["fold"][rep], W)
                    m2 = wmetrics(p2, common, y, sk, F["q20"][rep], F["fold"][rep], W)
                    per_rep.append({k: m1[k] - m2[k] for k in METRICS}); draws.append(int(common.sum()))
                for k in METRICS:
                    d = np.nanmean(np.vstack([r[k] for r in per_rep]), axis=0)
                    est, bd = d[0], d[1:]
                    lo, hi = (np.nanpercentile(bd, [2.5, 97.5]) if np.isfinite(bd).any() else (np.nan, np.nan))
                    prow.append({"population": pop, "arm": a1, "ref": a2, "budget": b, "metric": k, "estimate_mean_over_repeats": float(est),
                                 "per_repeat": json.dumps([float(r[k][0]) for r in per_rep]), "cluster_bootstrap_lo": float(lo), "cluster_bootstrap_hi": float(hi),
                                 "common_cohort_per_repeat": json.dumps(draws), "interval_note": "simulation-cluster bootstrap conditional on the stored fits and these splits"})
    mt, ct, fm = pd.DataFrame(rows), pd.DataFrame(prow), pd.DataFrame(frows)
    mt.to_csv(SM / "metrics_per_repeat.csv", index=False, lineterminator="\n")
    fm.to_csv(SM / "metrics_per_fold.csv", index=False, lineterminator="\n")
    ct.to_csv(SM / "paired_contrasts.csv", index=False, lineterminator="\n")
    dec = decision(mt, ct, fits)
    (SM / "STAGE_M_DECISION.json").write_text(json.dumps(dec, indent=1), encoding="utf-8")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(mt.groupby(["population", "budget", "arm"])[["BA", "q20", "specificity", "sensitivity", "shortK_sensitivity", "brier", "log_loss", "AUC", "n_unavailable"]].mean().round(3).to_string())
    print(ct[ct.metric.isin(["BA", "specificity", "log_loss"])].round(4).to_string())
    print(json.dumps(dec, indent=1))
    return mt, ct, dec


def decision(mt, ct, fits):
    """Frozen screen: recommend Stage A iff numerical/leakage checks pass and, on NEW at B40 (means over the two repeats),
    J - Binary_matched BA >= +0.01, specificity(J) >= specificity(Binary_matched), log loss(J) <= log loss(Binary_matched)."""
    val = json.loads((OUT / "validation/validation_results.json").read_text(encoding="utf-8"))
    jf = fits[fits.arm.isin(["J", "Binary_matched"]) & (fits.population == "NEW") & (fits.budget == 40)]
    leak = fits[fits.arm.isin(["ACTIVE_E1", "G3"])].get("leakage_guard_ok", pd.Series(dtype=bool)).fillna(True).astype(bool).all()
    numerics = bool(val["status"] == "PASS" and (jf.status == "ok").all() and jf.gradient_accepted.fillna(False).astype(bool).all() and leak)
    g = lambda metric: ct[(ct.population == "NEW") & (ct.arm == "J") & (ct.ref == "Binary_matched") & (ct.budget == 40) & (ct.metric == metric)].iloc[0]
    dba, dsp, dll = g("BA"), g("specificity"), g("log_loss")
    c1, c2, c3 = dba.estimate_mean_over_repeats >= PRACTICAL_GAIN - 1e-12, dsp.estimate_mean_over_repeats >= -1e-12, dll.estimate_mean_over_repeats <= 1e-12
    rec = bool(numerics and c1 and c2 and c3)
    reasons = []
    if not numerics:
        reasons.append("numerical or leakage check failed")
    if not c1:
        reasons.append("BA gain below +0.01" + (" (point estimate below the practical deterioration threshold -0.01)" if dba.estimate_mean_over_repeats <= PRACTICAL_LOSS else ""))
    if not c2:
        reasons.append("specificity sacrificed")
    if not c3:
        reasons.append("log loss worse")
    return {"rule": decision.__doc__.replace("\n", " "), "numerical_and_leakage_checks_pass": numerics,
            "NEW_B40_J_minus_Binary": {"BA": float(dba.estimate_mean_over_repeats), "BA_interval": [float(dba.cluster_bootstrap_lo), float(dba.cluster_bootstrap_hi)],
                                       "specificity": float(dsp.estimate_mean_over_repeats), "log_loss": float(dll.estimate_mean_over_repeats),
                                       "BA_per_repeat": json.loads(dba.per_repeat)},
            "criteria": {"BA_gain_ge_0.01": bool(c1), "specificity_not_lower": bool(c2), "log_loss_not_worse": bool(c3)},
            "decision": "RECOMMEND STAGE A" if rec else "SCREEN FAILED - Stage A not recommended", "reasons_if_failed": reasons,
            "note": "pragmatic development screen on DEV repeats 1-2, not confirmation; failure classification is in STAGE_M_REPORT.md"}


if __name__ == "__main__":
    main()
