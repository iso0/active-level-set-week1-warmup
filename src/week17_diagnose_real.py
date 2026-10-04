"""Week 17 Phase 1 — mechanism diagnosis on the real campaigns (POST-HOC NEW / HISTORICAL OLD; descriptive).

States (all previously examined; fixed query paths, so differences are due to the model only):
  transfer  fit on OLD-405, evaluate NEW-136 (strict OLD→NEW)
  new_cv    100 frozen NEW splits, full training pool
  new_al    Week 12 `M3_margin__maximin8_continue` prefixes at budgets 16/24/40/60/80
  old_a0    Week 9 OLD A0 prefixes at budgets 16/32/48/64/80 (historical OLD evidence)
Metrics on the held-out rows: BA, minority recall (NEW: non-Keyhole; OLD: Keyhole), ROC AUC, minority AP,
Brier, log loss, historical q20 accuracy; diagnostics: override rate of the physics mean, hyperparameters.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import average_precision_score, roc_auc_score

import src.week17_models as M
from src.week17_audit import ROOT, campaigns

OUT = ROOT / "outputs/week17_model_and_acquisition/phase1"


def metrics(y, p, q20, minority):
    y = np.asarray(y, int); p = np.clip(np.asarray(p, float), 1e-12, 1 - 1e-12); yh = (p >= .5).astype(int)
    rec = [np.mean(yh[y == k] == k) if (y == k).any() else np.nan for k in (0, 1)]
    both = len(set(y)) == 2
    pr = p if minority == 1 else 1 - p
    out = {"BA": float(np.nanmean(rec)), "minority_recall": float(rec[minority]), "majority_recall": float(rec[1 - minority]),
           "AUC": float(roc_auc_score(y, p)) if both else np.nan,
           "minority_AP": float(average_precision_score((y == minority).astype(int), pr)) if both else np.nan,
           "brier": float(np.mean((p - y) ** 2)), "logloss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
           "accuracy": float(np.mean(yh == y))}
    if q20 is not None and np.any(q20):
        out["q20_accuracy"] = float(np.mean(yh[q20] == y[q20]))
    return out


def state_rows(tag, x4, lh, y, pool, rev, test, q20, minority, models=M.MODELS):
    rows = []
    for name in models:
        try:
            f = M.fit(name, x4, lh, y, pool, rev)
            p = f.proba(x4[test], lh[test])
            r = {**tag, "model": name, **metrics(y[test], p, q20, minority), **M.hyper_summary(f),
                 "pred_rows": ",".join(map(str, test)), "pred_p": ",".join(f"{v:.6g}" for v in p),
                 "pred_q20": ",".join("1" if v else "0" for v in (q20 if q20 is not None else np.zeros(len(test), bool)))}
            if isinstance(f, M.Fitted) and f.phys is not None:
                mu, _ = f.latent(x4[test], lh[test]); m = f.mean(lh[test])
                r["override_rate"] = float(np.mean(np.sign(mu) != np.sign(m)))
                r["needed_override_rate"] = float(np.mean(np.sign(m) != (2 * y[test] - 1)))
                r["max_abs_mean_test"] = float(np.abs(m).max())
            if isinstance(f, M.Fitted):
                r["fp_err"] = f.converged()
            rows.append(r)
        except Exception as exc:
            rows.append({**tag, "model": name, "error": f"{type(exc).__name__}: {exc}"})
    return rows


def jobs():
    from src.week12_development_common import load_new, load_splits
    from src.external_validation.analysis import boundary_flags
    from src import week8_5_frozen_sample_efficiency_confirmation as w85
    from src import week9_phase1_7_physics_ridge_residual_gp as p17
    from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
    C = campaigns(); xo, lo, yo = C["OLD"]; xn, ln, yn = C["NEW"]
    ids = load_new().sim_id.astype(str).to_numpy()
    J = [({"set": "transfer", "split": "OLD405", "budget": 405}, "transfer", None, None, None, None)]
    sp = load_splits()
    for s in sp:
        tr, te = np.asarray(s["train_indices"]), np.asarray(s["test_indices"])
        J.append(({"set": "new_cv", "split": s["split_id"], "budget": len(tr)}, "NEW", tr, tr, te, boundary_flags(xn, yn, te, ids, "entire_evaluation_batch")[20]))
    q = pd.read_csv(ROOT / "outputs/week12_startup_and_transfer_development/active_learning/query_paths.csv.gz")
    q = q[q.arm == "M3_margin__maximin8_continue"]; spd = {s["split_id"]: s for s in sp}
    for sid, g in q.groupby("split_id"):
        order = g.sort_values("query_order").row_index.to_numpy(int); s = spd[sid]
        tr, te = np.asarray(s["train_indices"]), np.asarray(s["test_indices"])
        q20 = boundary_flags(xn, yn, te, ids, "entire_evaluation_batch")[20]
        for b in (16, 24, 40, 60, 80):
            if len(set(yn[order[:b]])) == 2:
                J.append(({"set": "new_al", "split": sid, "budget": b}, "NEW", tr, order[:b], te, q20))
    pop, specs, paths = p13.load_inputs(); dist = w85.b1_distance(pop)
    for spec in specs:
        q20 = np.asarray(p17.subset_flags(spec, pop, dist)["B1_q20"], bool)
        for b in (16, 32, 48, 64, 80):
            J.append(({"set": "old_a0", "split": spec.run_id, "budget": b}, "OLD", np.asarray(spec.train_indices), np.asarray(paths[spec.run_id][:b]), np.asarray(spec.test_indices), q20))
    return J, C, ids


def run(job, C, ids):
    from threadpoolctl import threadpool_limits
    from src.external_validation.analysis import boundary_flags
    tag, camp, pool, rev, te, q20 = job
    with threadpool_limits(1):
        if camp == "transfer":
            xo, lo, yo = C["OLD"]; xn, ln, yn = C["NEW"]
            q = boundary_flags(xn, yn, np.arange(len(yn)), ids, "entire_evaluation_batch")[20]
            rows = []
            for name in M.MODELS:
                f = M.fit(name, xo, lo, yo, np.arange(len(yo)), np.arange(len(yo)))
                p = f.proba(xn, ln)
                r = {**tag, "model": name, **metrics(yn, p, q, 0), **M.hyper_summary(f),
                     "pred_rows": ",".join(map(str, range(len(yn)))), "pred_p": ",".join(f"{v:.6g}" for v in p),
                     "pred_q20": ",".join("1" if v else "0" for v in q)}
                mu, var = f.latent(xn, ln)
                r["latent_mean_NEW"] = float(np.mean(mu)); r["latent_sd_NEW_median"] = float(np.median(np.sqrt(var))) if np.any(var) else 0.0
                rows.append(r)
            return rows
        x4, lh, y = C[camp]
        return state_rows(tag, x4, lh, y, pool, rev, te, q20, 0 if camp == "NEW" else 1)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    J, C, ids = jobs()
    res = Parallel(n_jobs=7, verbose=5)(delayed(run)(j, C, ids) for j in J)
    df = pd.DataFrame([r for rows in res for r in rows]); df.to_csv(OUT / "diagnose_real.csv.gz", index=False)
    cols = ["BA", "minority_recall", "AUC", "minority_AP", "brier", "logloss", "q20_accuracy"]
    s = df.groupby(["set", "model"])[cols].mean(); s.to_csv(OUT / "diagnose_real_summary.csv")
    print(s.round(4).to_string())


if __name__ == "__main__":
    main()
