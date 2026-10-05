"""Week 17 Phase 0 — numerical-integrity audit of every authoritative Laplace GPC fit.

Implementations audited (all undamped GPML Alg. 3.1 Newton, stop when the in-loop objective stops rising):
  G3  sklearn GaussianProcessClassifier (src/week9_phase1_12_gpc_kernel_adequacy.py::fit_gpc_model)
  M3  week9_phase1_11 FixedMeanLaplaceGPC with the C = 1e6 physics mean (week9_phase1_13.fit_hybrid;
      also behind external_validation.runner.FrozenM3Evaluator used in the frozen attempt and Week 12)
Both store pi from the iterate *before* the last Newton step (sklearn convention) — at a non-converged stop
the stored state is not a fixed point of f = m + K(y - pi(f)).

Check per fitted model: with the fit's own kernel (optimized hyperparameters) and mean, compute the
Laplace mode with a safeguarded Newton (backtracking on Psi(a) = -1/2 a'Ka + sum log sigma(s(m + Ka))) and
compare (i) latent deviation at training inputs, (ii) test predictive probabilities, (iii) test classes,
(iv) the Laplace log marginal likelihood.  A fit is flagged if |dg| > 1e-6 or |dp| > 1e-4.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.linalg import cho_solve, cholesky, solve_triangular
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week17_model_and_acquisition/integrity"
warnings.filterwarnings("ignore")


def safeguarded_mode(K, y, m, iters=500, tol=1e-12, fp_tol=None):
    """Laplace mode of f = m + g, g ~ N(0, K), logistic likelihood; Newton with backtracking.
    fp_tol=None: Week 17 stopping rule (objective and step stall).  fp_tol given (Week 18): iterate until the
    fixed-point error |K(y - pi) - g| <= fp_tol; when backtracking stalls on round-off the full Newton step is
    taken if it lowers the fixed-point error."""
    y = np.asarray(y, int); m = np.asarray(m, float); s = 2 * y - 1
    psi = lambda a: -.5 * a @ K @ a - np.logaddexp(0, -s * (m + K @ a)).sum()
    fperr = lambda a: float(np.abs(K @ (y - expit(m + K @ a)) - K @ a).max())
    a = np.zeros(len(y)); cur = psi(a); it = 0; conv = False
    for it in range(1, iters + 1):
        g = K @ a
        pi = expit(m + g); W = pi * (1 - pi); sw = np.sqrt(W)
        L = cholesky(np.eye(len(y)) + sw[:, None] * K * sw[None, :], lower=True)
        b = W * g + (y - pi)
        d = b - sw * cho_solve((L, True), sw * (K @ b)) - a
        t = 1.0
        while t > 1e-10 and psi(a + t * d) < cur - 1e-13:
            t *= .5
        if fp_tol is not None and t <= 1e-10 and fperr(a + d) < fperr(a):
            t = 1.0
        a = a + t * d; new = psi(a)
        if fp_tol is not None:
            if fperr(a) <= fp_tol:
                cur = new; conv = True; break
        elif abs(new - cur) < tol and t * np.abs(K @ d).max() < 1e-9:
            cur = new; conv = True; break
        cur = new
    g = K @ a; pi = expit(m + g); sw = np.sqrt(pi * (1 - pi))
    L = cholesky(np.eye(len(y)) + sw[:, None] * K * sw[None, :], lower=True)
    fp = float(np.abs(K @ (y - pi) - g).max())
    return {"g": g, "pi": pi, "sw": sw, "L": L, "converged": conv and fp < 1e-8, "iters": it, "fp": fp,
            "lml": float(cur - np.log(np.diag(L)).sum())}


def predictive(Ks, kss, y, pi, sw, L, mean_test):
    mu = mean_test + Ks.T @ (y - pi)
    v = solve_triangular(L, sw[:, None] * Ks, lower=True)
    var = np.maximum(kss - (v * v).sum(0), 1e-12)
    return mu, var, expit(mu / np.sqrt(1 + np.pi * var / 8))


def compare(K, Ks, kss, y, m_train, m_test, pi_s, sw_s, L_s, lml_s):
    ref = safeguarded_mode(K, y, m_train)
    mu_s, _, p_s = predictive(Ks, kss, y, pi_s, sw_s, L_s, m_test)
    mu_r, _, p_r = predictive(Ks, kss, y, ref["pi"], ref["sw"], ref["L"], m_test)
    dg = float(np.abs(K @ (y - pi_s) - ref["g"]).max())
    return {"dg_train": dg, "dp_test_max": float(np.abs(p_s - p_r).max()), "dclass_test": float(np.mean((p_s >= .5) != (p_r >= .5))),
            "dmu_test_max": float(np.abs(mu_s - mu_r).max()), "lml_stored": float(lml_s), "lml_mode": ref["lml"],
            "ref_converged": ref["converged"], "ref_iters": ref["iters"], "flag": bool(dg > 1e-6 or np.abs(p_s - p_r).max() > 1e-4),
            "mean_abs_train": float(np.abs(m_train).max()), "pi_saturated_share": float(np.mean((pi_s < 1e-6) | (pi_s > 1 - 1e-6)))}


def audit_sklearn(model, Xtest):
    base = getattr(model, "base_estimator_", None)
    if base is None:
        return {"note": "not_a_gpc"}
    K = base.kernel_(base.X_train_); Ks = base.kernel_(base.X_train_, Xtest); kss = base.kernel_.diag(Xtest)
    z = np.zeros(len(base.y_train_))
    return compare(K, Ks, kss, base.y_train_, z, np.zeros(len(Xtest)), base.pi_, base.W_sr_, base.L_, model.log_marginal_likelihood_value_)


def audit_fixedmean(gp, Xtest, mean_test):
    K = gp.kernel_(gp.X_train_); Ks = gp.kernel_(gp.X_train_, Xtest); kss = gp.kernel_.diag(Xtest)
    return compare(K, Ks, kss, gp.y_train_, gp.mean_train_, mean_test, gp.pi_, gp.W_sr_, gp.L_, gp.log_marginal_likelihood_value_)


# ----------------------------------------------------------------------------- fit replays
def fit_g3(x4, y, train_pool, revealed, seed=0):
    from sklearn.preprocessing import StandardScaler
    from src import week9_phase1_12_gpc_kernel_adequacy as p12
    sc = StandardScaler().fit(x4[train_pool])
    model, diag = p12.fit_gpc_model("G3", sc.transform(x4[revealed]), y[revealed], seed)
    return model, sc, diag


def fit_m3(x4, logh, y, train_pool, revealed, seed=0):
    from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
    from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
    phys = p11.fit_physics_mean(logh, y, revealed, seed)
    fit = p13.fit_hybrid(x4, logh, y, revealed, train_pool, phys, "M3", 100.0)
    return fit, phys


def one_state(tag, x4, logh, y, train_pool, revealed, test, models=("G3", "M3")):
    rows = []
    for name in models:
        try:
            if name == "G3":
                model, sc, diag = fit_g3(x4, y, train_pool, revealed)
                r = audit_sklearn(model, sc.transform(x4[test]))
                r.update({"amplitude": diag.get("amplitude"), "fit_status": diag.get("fit_status")})
            else:
                fit, phys = fit_m3(x4, logh, y, train_pool, revealed)
                r = audit_fixedmean(fit.gp, fit.x_scaler.transform(x4[test]), phys.latent(logh[test]))
                r.update({"physics_coef": float(phys.model.coef_[0, 0]), "physics_intercept": float(phys.model.intercept_[0]),
                          "residual_sd": float(fit.residual_sd), "posterior_iterations": fit.gp.diagnostics_.posterior_iterations,
                          "optimizer_converged": fit.gp.diagnostics_.optimizer_converged})
        except Exception as exc:
            r = {"error": f"{type(exc).__name__}: {exc}"}
        rows.append({**tag, "model": name, "n_revealed": len(revealed), **r})
    return rows


def campaigns():
    from src.week12_development_common import load_new, load_old
    out = {}
    for name, df in (("NEW", load_new()), ("OLD", load_old())):
        x4 = df[["P", "VX", "LS", "ST"]].to_numpy(float)
        out[name] = (x4, np.log(x4[:, 0]) - .5 * np.log(x4[:, 1]) - 1.5 * np.log(x4[:, 2]), df.has_keyhole.to_numpy(int))
    return out


def jobs_all(budgets_al=(16, 24, 40, 60, 80), budgets_old=(16, 32, 48, 64, 80)):
    from src.week12_development_common import load_splits
    C = campaigns(); J = []
    xo, lo, yo = C["OLD"]; xn, ln, yn = C["NEW"]
    # A. Week 12 strict transfer: fit on all OLD-405, predict NEW-136
    J.append(("A_transfer", {"split": "OLD405"}, xo, lo, yo, np.arange(len(yo)), np.arange(len(yo)), None))
    # B. Week 12 NEW-only CV (100 frozen splits, full training pools)
    for s in load_splits():
        tr = np.asarray(s["train_indices"]); te = np.asarray(s["test_indices"])
        J.append(("B_new_cv", {"split": s["split_id"]}, xn, ln, yn, tr, tr, te))
    # C. Week 12 AL prefixes (stored query paths), two complete protocols
    q = pd.read_csv(ROOT / "outputs/week12_startup_and_transfer_development/active_learning/query_paths.csv.gz")
    sp = {s["split_id"]: s for s in load_splits()}
    for (sid, arm), g in q[q.arm.isin(["M3_margin__maximin8_continue", "Candidate_B__maximin8_continue"])].groupby(["split_id", "arm"]):
        order = g.sort_values("query_order").row_index.to_numpy(int); tr = np.asarray(sp[sid]["train_indices"])
        for b in budgets_al:
            rev = order[:b]
            if len(set(yn[rev])) == 2:
                J.append(("C_week12_al", {"split": sid, "arm": arm, "budget": b}, xn, ln, yn, tr, rev, np.arange(len(yn))))
    # D. Week 9 OLD A0 paths (historical OLD evidence)
    from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
    pop, specs, paths = p13.load_inputs()
    for spec in specs:
        for b in budgets_old:
            rev = np.asarray(paths[spec.run_id][:b])
            J.append(("D_old_a0", {"split": spec.run_id, "budget": b}, xo, lo, yo, np.asarray(spec.train_indices), rev, np.asarray(spec.test_indices)))
    return J, C


def run_job(kind, tag, x4, logh, y, train_pool, revealed, test, C):
    if kind == "A_transfer":
        xn, ln, yn = C["NEW"]
        rows = []
        for name in ("G3", "M3"):
            if name == "G3":
                model, sc, diag = fit_g3(x4, y, train_pool, revealed)
                r = audit_sklearn(model, sc.transform(xn)); r["amplitude"] = diag.get("amplitude")
            else:
                fit, phys = fit_m3(x4, logh, y, train_pool, revealed)
                r = audit_fixedmean(fit.gp, fit.x_scaler.transform(xn), phys.latent(ln))
                r.update({"physics_coef": float(phys.model.coef_[0, 0]), "physics_intercept": float(phys.model.intercept_[0]), "residual_sd": float(fit.residual_sd)})
            rows.append({"set": kind, **tag, "model": name, "n_revealed": len(revealed), **r})
        return rows
    return [{"set": kind, **r} for r in one_state(tag, x4, logh, y, train_pool, revealed, test)]


def main():
    from threadpoolctl import threadpool_limits
    OUT.mkdir(parents=True, exist_ok=True)
    J, C = jobs_all()
    def go(j):
        with threadpool_limits(1):
            return run_job(*j, C)
    res = Parallel(n_jobs=7, verbose=5)(delayed(go)(j) for j in J)
    df = pd.DataFrame([r for rows in res for r in rows])
    if "error" not in df:
        df["error"] = np.nan
    df.to_csv(OUT / "laplace_mode_audit.csv.gz", index=False)
    s = df.groupby(["set", "model"]).agg(fits=("flag", "size"), flagged=("flag", "sum"), max_dp=("dp_test_max", "max"),
                                         max_dclass=("dclass_test", "max"), max_dg=("dg_train", "max"),
                                         errors=("error", lambda x: int(x.notna().sum())))
    s.to_csv(OUT / "laplace_mode_audit_summary.csv")
    print(s.to_string())


if __name__ == "__main__":
    main()
