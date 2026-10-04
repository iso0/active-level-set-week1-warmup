"""Week 17 Phase 0 — does the M3 Laplace non-convergence change any historical conclusion?

Refit M3 exactly as week9_phase1_13.fit_hybrid does (same C = 1e6 physics mean, same residual kernel, same
L-BFGS-B hyperparameter optimization) but with the posterior mode found by a safeguarded Newton
(`SafeguardedFixedMeanLaplaceGPC`), so that both the predictive state *and* the optimized hyperparameters
are computed from the true Laplace objective.  Compare with the historical fit on the same states:
test-class flips, historical q20 accuracy, balanced accuracy, and the hyperparameters.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.preprocessing import StandardScaler

from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src.week17_audit import OUT, ROOT, campaigns, safeguarded_mode


class SafeguardedFixedMeanLaplaceGPC(p11.FixedMeanLaplaceGPC):
    """p11.FixedMeanLaplaceGPC with the posterior mode found by backtracking Newton (consistent temporaries)."""

    def _posterior_mode(self, kernel, return_temporaries=False):
        K = kernel(self.X_train_)
        r = safeguarded_mode(K, self.y_train_, self.mean_train_)
        self.mode_fp_, self.mode_converged_ = r["fp"], r["converged"]
        pi, sw, L, g = r["pi"], r["sw"], r["L"], r["g"]
        a = self.y_train_ - pi
        b = pi * (1 - pi) * g + a
        if return_temporaries:
            return r["lml"], (pi, sw, L, b, a, r["iters"])
        return r["lml"]


def fit_m3(x4, logh, y, train_pool, revealed, safe):
    phys = p11.fit_physics_mean(logh, y, revealed, 0)
    sc = StandardScaler().fit(x4[train_pool])
    cls = SafeguardedFixedMeanLaplaceGPC if safe else p11.FixedMeanLaplaceGPC
    gp = cls(p13.residual_kernel("M3", 100.0), optimize=True).fit(sc.transform(x4[revealed]), y[revealed], phys.latent(logh[revealed]))
    return gp, sc, phys


def predict(gp, sc, phys, x4, logh, idx):
    return gp.predict_proba(sc.transform(x4[idx]), phys.latent(logh[idx]))[:, 1]


def ba(y, p):
    yh = (p >= .5).astype(int)
    return float(np.nanmean([np.mean(yh[y == k] == k) if (y == k).any() else np.nan for k in (0, 1)]))


def compare_state(tag, x4, logh, y, train_pool, revealed, test, q20):
    out = {**tag}
    res = {}
    for safe in (False, True):
        gp, sc, phys = fit_m3(x4, logh, y, train_pool, revealed, safe)
        p = predict(gp, sc, phys, x4, logh, test)
        th = np.exp(gp.kernel_.theta)
        res[safe] = p
        k = "safe" if safe else "hist"
        out.update({f"q20_{k}": float(np.mean((p[q20] >= .5) == y[test][q20])) if q20 is not None and q20.any() else np.nan,
                    f"BA_{k}": ba(y[test], p), f"resid_var_{k}": float(th[0]), f"ls_min_{k}": float(th[1:].min()),
                    f"ls_max_{k}": float(th[1:].max()), f"lml_{k}": float(gp.log_marginal_likelihood_value_)})
    out["class_flips"] = int(np.sum((res[False] >= .5) != (res[True] >= .5)))
    out["max_dp"] = float(np.abs(res[False] - res[True]).max())
    out["q20_flips"] = int(np.sum(((res[False] >= .5) != (res[True] >= .5))[q20])) if q20 is not None else 0
    return out


def jobs():
    from src.week12_development_common import load_splits, load_new
    from src.external_validation.analysis import boundary_flags
    from src import week8_5_frozen_sample_efficiency_confirmation as w85
    from src import week9_phase1_7_physics_ridge_residual_gp as p17
    C = campaigns(); J = []
    xo, lo, yo = C["OLD"]; xn, ln, yn = C["NEW"]
    new = load_new(); ids = new.sim_id.astype(str).to_numpy()
    sp = load_splits()
    for s in sp:
        tr, te = np.asarray(s["train_indices"]), np.asarray(s["test_indices"])
        q20 = boundary_flags(xn, yn, te, ids, "entire_evaluation_batch")[20]
        J.append(({"set": "B_new_cv", "split": s["split_id"], "budget": len(tr)}, xn, ln, yn, tr, tr, te, q20))
    q = pd.read_csv(ROOT / "outputs/week12_startup_and_transfer_development/active_learning/query_paths.csv.gz")
    spd = {s["split_id"]: s for s in sp}
    for (sid, arm), g in q[q.arm.isin(["M3_margin__maximin8_continue", "Candidate_B__maximin8_continue"])].groupby(["split_id", "arm"]):
        order = g.sort_values("query_order").row_index.to_numpy(int); s = spd[sid]
        tr, te = np.asarray(s["train_indices"]), np.asarray(s["test_indices"])
        q20 = boundary_flags(xn, yn, te, ids, "entire_evaluation_batch")[20]
        for b in (16, 24, 40, 60, 80):
            rev = order[:b]
            if len(set(yn[rev])) == 2:
                J.append(({"set": "C_week12_al", "split": sid, "arm": arm, "budget": b}, xn, ln, yn, tr, rev, te, q20))
    pop, specs, paths = p13.load_inputs(); dist = w85.b1_distance(pop)
    for spec in specs:
        q20 = p17.subset_flags(spec, pop, dist)["B1_q20"]
        for b in (16, 32, 48, 64, 80):
            J.append(({"set": "D_old_a0", "split": spec.run_id, "budget": b}, xo, lo, yo, np.asarray(spec.train_indices),
                      np.asarray(paths[spec.run_id][:b]), np.asarray(spec.test_indices), np.asarray(q20, bool)))
    J.append(({"set": "A_transfer", "split": "OLD405", "budget": 405}, None, None, None, None, None, None, None))
    return J, C


def run(job, C):
    from threadpoolctl import threadpool_limits
    tag, x4, logh, y, tr, rev, te, q20 = job
    with threadpool_limits(1):
        if tag["set"] == "A_transfer":
            xo, lo, yo = C["OLD"]; xn, ln, yn = C["NEW"]
            from src.week12_development_common import load_new
            from src.external_validation.analysis import boundary_flags
            ids = load_new().sim_id.astype(str).to_numpy()
            q = boundary_flags(xn, yn, np.arange(len(yn)), ids, "entire_evaluation_batch")[20]
            out = {**tag}; res = {}
            for safe in (False, True):
                phys = p11.fit_physics_mean(lo, yo, np.arange(len(yo)), 0)
                sc = StandardScaler().fit(xo)
                cls = SafeguardedFixedMeanLaplaceGPC if safe else p11.FixedMeanLaplaceGPC
                gp = cls(p13.residual_kernel("M3", 100.0), optimize=True).fit(sc.transform(xo), yo, phys.latent(lo))
                p = gp.predict_proba(sc.transform(xn), phys.latent(ln))[:, 1]; res[safe] = p; k = "safe" if safe else "hist"
                out.update({f"q20_{k}": float(np.mean((p[q] >= .5) == yn[q])), f"BA_{k}": ba(yn, p), f"lml_{k}": float(gp.log_marginal_likelihood_value_),
                            f"resid_var_{k}": float(np.exp(gp.kernel_.theta)[0])})
            out["class_flips"] = int(np.sum((res[False] >= .5) != (res[True] >= .5))); out["max_dp"] = float(np.abs(res[False] - res[True]).max())
            return out
        return compare_state(tag, x4, logh, y, tr, rev, te, q20)


def main():
    J, C = jobs()
    rows = Parallel(n_jobs=7, verbose=5)(delayed(run)(j, C) for j in J)
    df = pd.DataFrame(rows); df.to_csv(OUT / "m3_safeguarded_refit_impact.csv.gz", index=False)
    s = df.groupby("set").agg(states=("max_dp", "size"), states_with_flip=("class_flips", lambda x: int((x > 0).sum())),
                              total_flips=("class_flips", "sum"), q20_flip_states=("q20_flips", lambda x: int((x > 0).sum())),
                              max_dp=("max_dp", "max"), mean_q20_hist=("q20_hist", "mean"), mean_q20_safe=("q20_safe", "mean"),
                              mean_BA_hist=("BA_hist", "mean"), mean_BA_safe=("BA_safe", "mean"))
    s.to_csv(OUT / "m3_safeguarded_refit_impact_summary.csv"); print(s.round(5).to_string())


if __name__ == "__main__":
    main()
