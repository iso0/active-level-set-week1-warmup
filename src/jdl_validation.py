"""Validation of the joint depth-label GP port (src/jdl_model.py) — no SPH data, no comparative fits.

1. Astra's 26 supplied checks, run (a) against the unchanged reference and (b) against the port.
2. Independent checks in four dimensions with the frozen Stage M priors: parity with the reference, covariance
   reconstruction, prediction-batch invariance, one-class paid data, missing response, gradient acceptance,
   corruption of every unpaid/test outcome, refit-from-prior, discrepancy centering, special functions, and a
   small tractable case compared with independent importance sampling and elliptical slice sampling.

Step: python -m src.jdl_validation
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import platform
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import scipy
from scipy.integrate import quad
from scipy.special import log_ndtr, ndtr

import src.jdl_model as P

ROOT = Path(__file__).resolve().parents[1]
ASTRA = ROOT / "outputs" / "astra_week20_method_development"
OUT = ROOT / "outputs" / "joint_depth_label_development" / "validation"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def reference():
    sys.path.insert(0, str(ASTRA))
    try:
        return _load(ASTRA / "joint_depth_label_gp.py", "astra_reference_jdl")
    finally:
        sys.path.remove(str(ASTRA))


def astra_checks(module, label):
    """Run Astra's run_checks.main with `module` substituted for joint_depth_label_gp."""
    saved = sys.modules.get("joint_depth_label_gp")
    sys.modules["joint_depth_label_gp"] = module
    try:
        rc = _load(ASTRA / "run_checks.py", f"astra_run_checks_{label}")
        out = OUT / f"astra_checks_{label}.json"
        rc.main(str(out))
        return json.loads(out.read_text(encoding="utf-8"))
    finally:
        if saved is None:
            sys.modules.pop("joint_depth_label_gp", None)
        else:
            sys.modules["joint_depth_label_gp"] = saved


def toy_4d(seed=7, n_pool=60, n_paid=15, n_test=12):
    """Synthetic four-input case with a depth-like response and labels from a different law (with exceptions)."""
    g = np.random.default_rng(seed)
    X = g.standard_normal((n_pool + n_test, 4))
    z = 0.5 * X[:, 0] - 0.3 * X[:, 1] + 0.15 * np.sin(2 * X[:, 2]) + 0.03 * g.standard_normal(len(X))
    y = ((z - 0.1 + 0.35 * np.exp(-((X[:, 3] - 0.5) / 0.6) ** 2) * np.sign(X[:, 1])) > 0).astype(int)
    pool, test = np.arange(n_pool), np.arange(n_pool, n_pool + n_test)
    paid = pool[g.permutation(n_pool)[:n_paid]]
    return X, y, z, pool, test, paid


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    R = reference()
    res = {"version": P.VERSION, "environment": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__},
           "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in ("src/jdl_model.py", "src/jdl_validation.py")},
           "astra_package_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ASTRA.iterdir()) if p.is_file()},
           "checks": {}}
    C = res["checks"]

    def check(name, ok, **info):
        C[name] = {"passed": bool(ok), **{k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in info.items()}}

    # ---------------------------------------------------------------- 1. Astra's 26 checks: reference and port
    ra = astra_checks(R, "reference"); pa = astra_checks(P, "port")
    check("astra_26_checks_reference", ra["status"] == "PASS" and len(ra["checks"]) == 26, n=len(ra["checks"]), status=ra["status"])
    check("astra_26_checks_port", pa["status"] == "PASS" and len(pa["checks"]) == 26, n=len(pa["checks"]), status=pa["status"],
          failed=[k for k, v in pa["checks"].items() if not v["passed"]])
    lim = {"scalar_Laplace_abs_probability_error": (ra["cases"]["exact_scalar_threshold_reference"]["absolute_probability_error"],
                                                    pa["cases"]["exact_scalar_threshold_reference"]["absolute_probability_error"]),
           "sparse_primary_p_at_paid_negative": (ra["cases"]["sparse_negatives"]["primary_p_at_paid_negative"], pa["cases"]["sparse_negatives"]["primary_p_at_paid_negative"]),
           "adverse_joint_brier": (ra["cases"]["adverse_depth_bridge"]["joint"]["Brier"], pa["cases"]["adverse_depth_bridge"]["joint"]["Brier"]),
           "adverse_binary_brier": (ra["cases"]["adverse_depth_bridge"]["binary_only"]["Brier"], pa["cases"]["adverse_depth_bridge"]["binary_only"]["Brier"]),
           "mismatch_joint_BA": (ra["cases"]["depth_label_mismatch"]["heldout_metrics"]["joint"]["BA"], pa["cases"]["depth_label_mismatch"]["heldout_metrics"]["joint"]["BA"]),
           "acquisition_selected_x": (ra["acquisition"]["selected_x"], pa["acquisition"]["selected_x"])}
    worst = max(abs(a - b) for a, b in lim.values())
    check("astra_documented_limitations_reproduced_by_port", worst < 1e-7, max_abs_difference=worst,
          values={k: {"reference": a, "port": b} for k, (a, b) in lim.items()},
          note="the Laplace error (0.017), the prior-sensitive sparse negative (0.674) and the worse joint Brier in the adverse case are reproduced, not tuned away")
    acq_r, acq_p = np.array(ra["acquisition"]["joint"]), np.array(pa["acquisition"]["joint"])
    check("astra_toy_acquisition_scores_port_vs_reference", np.max(np.abs(acq_r - acq_p)) < 1e-8, max_abs_difference=float(np.max(np.abs(acq_r - acq_p))))

    # ---------------------------------------------------------------- 2. independent four-input checks
    cfg = P.STAGE_M_CONFIG
    X, y, z, pool, test, paid = toy_4d()
    Rcfg = R.Config(**{k: v for k, v in asdict(cfg).items()})
    variants = {"J": {}, "J_fixed_theta": {"threshold_sd": 0.0}, "J_no_delta": {"discrepancy_amplitude": 0.0}, "Binary_matched": {"_binary": True}}
    worst_post, worst_p, worst_acq = 0.0, 0.0, 0.0
    for name, ch in variants.items():
        kw = {k: v for k, v in ch.items() if not k.startswith("_")}
        binary = ch.get("_binary", False)
        mp = P.JointDepthLabelGP(X[pool], replace(cfg, **kw)).fit(X[paid], y[paid], z[paid], use_response=not binary)
        mr = R.JointDepthLabelGP(X[pool], replace(Rcfg, **kw)).fit(X[paid], y[paid], z[paid], use_response=not binary)
        qp, qr = mp.posterior(X), mr.posterior(X)
        for k in ("f_mean", "f_cov", "h_mean", "h_cov", "f_h_cov", "delta_mean", "delta_cov", "f_delta_cov", "f_theta_cov", "delta_theta_cov"):
            worst_post = max(worst_post, float(np.max(np.abs(np.asarray(qp[k]) - np.asarray(qr[k])))))
        worst_post = max(worst_post, abs(qp["theta_mean"] - qr["theta_mean"]), abs(qp["theta_var"] - qr["theta_var"]))
        worst_p = max(worst_p, float(np.max(np.abs(mp.predict_proba(X) - mr.predict_proba(X)))))
        cand = np.setdiff1d(pool, paid)[:10]
        ap, ar = mp.acquisition(X[cand], X[pool]), mr.acquisition(X[cand], X[pool])
        worst_acq = max(worst_acq, float(np.max(np.abs(ap["score"] - ar["score"]))))
    check("parity_4d_posterior_vs_reference", worst_post < 1e-8, max_abs_difference=worst_post, variants=list(variants))
    check("parity_4d_probability_vs_reference", worst_p < 1e-8, max_abs_difference=worst_p)
    check("parity_4d_acquisition_vs_reference", worst_acq < 1e-8, max_abs_difference=worst_acq,
          note="port: Genz BVNU; reference: Plackett integral with adaptive quadrature")

    m = P.JointDepthLabelGP(X[pool], cfg).fit(X[paid], y[paid], z[paid])
    q, mg = m.posterior(X), m.marginals(X)
    recon = np.diag(q["f_cov"]) + q["theta_var"] + np.diag(q["delta_cov"]) - 2 * q["f_theta_cov"] + 2 * np.diag(q["f_delta_cov"]) - 2 * q["delta_theta_cov"]
    e1 = float(np.max(np.abs(recon - np.diag(q["h_cov"])))); e2 = float(np.max(np.abs(mg["h_var"] - np.diag(q["h_cov"]))))
    e3 = float(np.max(np.abs(mg["h_mean"] - q["h_mean"])))
    check("covariance_reconstruction_4d", max(e1, e2, e3) < 1e-10, full_matrix_reconstruction=e1, marginal_vs_full_variance=e2, marginal_vs_full_mean=e3)
    g = np.random.default_rng(3)
    ref = m.predict_proba(X)
    worst = 0.0
    for _ in range(20):
        idx = g.permutation(len(X))[:g.integers(1, len(X))]
        worst = max(worst, float(np.max(np.abs(m.predict_proba(X[idx]) - ref[idx]))))
    far = np.vstack([X[test], 5 + g.standard_normal((7, 4))])
    worst = max(worst, float(np.max(np.abs(m.predict_proba(far)[:len(test)] - ref[test]))))
    check("prediction_batch_invariance_4d", worst < 1e-13, max_abs_difference=worst, note="random subsets, permutations and far-away companions")
    dm, dv = m.posterior(X[pool])["delta_mean"], m.posterior(X[pool])["delta_cov"]
    check("discrepancy_centering_exact_on_fixed_pool_4d", abs(dm.mean()) < 1e-12 and abs(dv.mean()) < 1e-12, mean=float(dm.mean()), mean_cov=float(dv.mean()))

    one_pos = P.JointDepthLabelGP(X[pool], cfg).fit(X[paid], np.ones(len(paid)), z[paid])
    one_neg = P.JointDepthLabelGP(X[pool], cfg).fit(X[paid], np.zeros(len(paid)), z[paid])
    ok = all(np.isfinite(mm.predict_proba(X)).all() and mm.diagnostics["gradient_accepted"] for mm in (one_pos, one_neg))
    tp, tn = one_pos.marginals(X[:1])["theta_mean"], one_neg.marginals(X[:1])["theta_mean"]
    check("one_class_paid_data_finite_and_directional", ok and tp < cfg.threshold_mean < tn, theta_all_positive=tp, theta_all_negative=tn,
          note="all-positive labels lower theta, all-negative raise it; both fits accepted")

    zmiss = z[paid].copy(); zmiss[3] = np.nan
    mm = P.JointDepthLabelGP(X[pool], cfg).fit(X[paid], y[paid], zmiss)
    flip = y[paid].copy(); flip[3] = 1 - flip[3]
    mf = P.JointDepthLabelGP(X[pool], cfg).fit(X[paid], flip, zmiss)
    mr = R.JointDepthLabelGP(X[pool], Rcfg).fit(X[paid], y[paid], zmiss)
    d = mm.diagnostics
    check("missing_response_keeps_label_and_cost", d["n_response"] == len(paid) - 1 and d["n_labels"] == len(paid) and d["n_missing_response"] == 1
          and float(np.max(np.abs(mm.predict_proba(X) - mf.predict_proba(X)))) > 1e-6 and float(np.max(np.abs(mm.predict_proba(X) - mr.predict_proba(X)))) < 1e-8,
          label_influence=float(np.max(np.abs(mm.predict_proba(X) - mf.predict_proba(X)))), reference_difference=float(np.max(np.abs(mm.predict_proba(X) - mr.predict_proba(X)))))

    saved = P.NEWTON_MAX_ITER
    P.NEWTON_MAX_ITER = 1
    try:
        P.JointDepthLabelGP(X[pool], replace(cfg, probit_scale=0.02)).fit(X[paid], y[paid], z[paid])
        refused, msg = False, ""
    except RuntimeError as e:
        refused, msg = True, str(e)[:160]
    finally:
        P.NEWTON_MAX_ITER = saved
    check("gradient_acceptance_enforced_separately_from_solver_status", refused and "max_iter" in msg and m.diagnostics["gradient_accepted"]
          and m.diagnostics["solver_status"] in ("converged", "stalled_at_objective_tolerance"), refused_message=msg,
          normal_fit={k: m.diagnostics[k] for k in ("solver_status", "gradient_inf", "gradient_accepted", "newton_iterations", "min_whitened_hessian_eigenvalue")})

    yc, zc = y.copy(), z.copy()
    unpaid = np.setdiff1d(np.arange(len(X)), paid)
    yc[unpaid] = 1 - yc[unpaid]; zc[unpaid] = 1e3 * np.sign(zc[unpaid] + 1e-9)
    a = P.fit_paid_prefix(X[pool], y[pool], z[pool], np.searchsorted(pool, paid), cfg)
    b = P.fit_paid_prefix(X[pool], yc[pool], zc[pool], np.searchsorted(pool, paid), cfg)
    cand = np.setdiff1d(pool, paid)
    dp = float(np.max(np.abs(a.predict_proba(X) - b.predict_proba(X))))
    da = float(np.max(np.abs(a.acquisition(X[cand])["score"] - b.acquisition(X[cand])["score"])))
    check("corruption_of_every_unpaid_and_test_outcome_has_no_effect", dp == 0.0 and da == 0.0, prediction_difference=dp, acquisition_difference=da)

    m1 = P.JointDepthLabelGP(X[pool], cfg).fit(X[paid[:5]], y[paid[:5]], z[paid[:5]]).fit(X[paid], y[paid], z[paid])
    check("refit_from_prior_no_state_carried", float(np.max(np.abs(m1.predict_proba(X) - ref))) == 0.0)
    bz = P.JointDepthLabelGP(X[pool], cfg).fit(X[paid], y[paid], z[paid], use_response=False)
    bz2 = P.JointDepthLabelGP(X[pool], cfg).fit(X[paid], y[paid], z[paid] * -7 + 3, use_response=False)
    check("binary_matched_ignores_responses_4d", float(np.max(np.abs(bz.predict_proba(X) - bz2.predict_proba(X)))) == 0.0)

    # ---------------------------------------------------------------- special functions
    g = np.random.default_rng(11)
    aa = np.r_[g.normal(0, 2, 4000), g.uniform(-8, 8, 2000), np.zeros(50), g.normal(0, 1e-6, 50)]
    bb = np.r_[g.normal(0, 2, 4000), g.uniform(-8, 8, 2000), g.normal(0, 1, 50), np.zeros(50)]
    rr = np.r_[g.uniform(-1, 1, 4000), np.sign(g.uniform(-1, 1, 2000)) * (1 - 10.0 ** g.uniform(-12, -1, 2000)), g.uniform(-0.999, 0.999, 100)]
    mine = P.phi2(aa, bb, rr)
    refv, ref_fail = np.full(len(aa), np.nan), 0
    for i in range(len(aa)):
        try:
            refv[i] = float(R.phi2(aa[i], bb[i], rr[i], 96))
        except FloatingPointError:
            ref_fail += 1                                    # reference's own convergence guard
    ok_r = np.isfinite(refv)
    dmax = float(np.max(np.abs(mine[ok_r] - refv[ok_r])))
    qerr, nq = 0.0, 0
    for a_, b_, r_ in zip(aa[::97], bb[::97], rr[::97]):
        end = np.arcsin(r_)
        pts = [end * (1 - 10.0 ** (-k)) for k in range(1, 10)] if abs(r_) > 0.995 else None
        val = ndtr(a_) * ndtr(b_) + quad(lambda t: np.exp(-(a_ * a_ - 2 * np.sin(t) * a_ * b_ + b_ * b_) / (2 * np.cos(t) ** 2)), 0, end,
                                         points=pts, epsabs=1e-15, epsrel=1e-12, limit=400)[0] / (2 * np.pi)
        qerr = max(qerr, abs(float(P.phi2(a_, b_, r_)) - val)); nq += 1
    check("bvn_genz_vs_reference_plackett", dmax < 1e-9, max_abs_difference=dmax, n=int(ok_r.sum()), reference_guard_refusals=ref_fail)
    check("bvn_genz_vs_independent_quad", qerr < 1e-9, max_abs_difference=qerr, n=nq)
    tt = np.r_[-np.logspace(5, np.log10(31), 60), np.linspace(-30, 37, 400)]
    lp, lam, cv = P.probit_terms(tt)
    near = tt >= -300                                        # exp(-t^2/2 - log Phi) is itself accurate only for moderate |t|
    lam_ref = np.exp(-0.5 * tt[near] ** 2 - 0.5 * np.log(2 * np.pi) - log_ndtr(tt[near]))
    rel = float(np.max(np.abs(lam[near] - lam_ref) / np.maximum(lam_ref, 1e-300)))
    lpr, lamr, cvr = R.probit_terms(tt)
    check("probit_terms_vs_independent_log_ndtr_and_reference", rel < 1e-10 and float(np.max(np.abs(cv - cvr))) < 1e-9 and float(np.max(np.abs(lam - lamr) / lamr)) < 1e-12,
          max_relative_lambda_error_vs_log_ndtr=rel, max_relative_lambda_difference_vs_reference=float(np.max(np.abs(lam - lamr) / lamr)),
          max_curvature_difference_vs_reference=float(np.max(np.abs(cv - cvr))))

    # ---------------------------------------------------------------- tractable case: Laplace vs independent sampling
    g = np.random.default_rng(5)
    Xs = g.standard_normal((40, 4)); paid_s = np.arange(6); test_s = np.arange(30, 40)
    zs = 0.6 * Xs[:, 0] + 0.03 * g.standard_normal(40)
    ys = np.array([1, 1, 0, 1, 0, 1])
    ms = P.JointDepthLabelGP(Xs[:30], cfg).fit(Xs[paid_s], ys, zs[paid_s])
    lap = ms.marginals(Xs[test_s]); lap_p = lap["p"]
    # joint prior after z: (h_P, h_test, theta)
    pts = np.vstack([Xs[paid_s], Xs[test_s]])
    pr = P.JointDepthLabelGP(Xs[:30], cfg).fit(Xs[paid_s], np.zeros(6), zs[paid_s], use_labels=False).posterior(pts)
    mh, Ch = pr["h_mean"], pr["h_cov"]
    c_th = np.r_[np.full(len(pts), -cfg.threshold_sd ** 2)]                      # Cov(h, theta) before labels
    Cfull = np.block([[Ch, c_th[:, None]], [c_th[None, :], np.array([[cfg.threshold_sd ** 2]])]])
    mfull = np.r_[mh, cfg.threshold_mean]
    Lf = np.linalg.cholesky(Cfull + 1e-12 * np.eye(len(mfull)))
    sgn = 2 * ys - 1
    # (a) exact rejection sampling with the Albert-Chib augmentation u = h + tau*eps, Y = 1{u > 0}
    rng = np.random.default_rng(20261013)
    acc_p, acc_t, n_draw = [], [], 0
    while sum(len(a) for a in acc_t) < 40000 and n_draw < 60_000_000:
        dr = mfull + rng.standard_normal((2_000_000, len(mfull))) @ Lf.T
        u = dr[:, :6] + cfg.probit_scale * rng.standard_normal((len(dr), 6))
        keep_ = np.all(sgn * u > 0, axis=1)
        acc_p.append(ndtr(dr[keep_, 6:6 + len(test_s)] / cfg.probit_scale)); acc_t.append(dr[keep_, -1]); n_draw += len(dr)
    acc_p, acc_t = np.vstack(acc_p), np.concatenate(acc_t)
    is_p = acc_p.mean(0); is_se = acc_p.std(0) / np.sqrt(len(acc_p))
    is_theta, is_theta_sd = float(acc_t.mean()), float(acc_t.std())
    ess_is = float(len(acc_t))
    # (b) Genz quasi-Monte Carlo orthant probabilities: p* = P(s u_P > 0, u_* > 0) / P(s u_P > 0)
    from scipy.stats import multivariate_normal
    S = np.diag(np.r_[sgn, 1.0])
    orth = []
    for j in range(len(test_s)):
        ii = np.r_[np.arange(6), 6 + j]
        mu_u = S @ mfull[ii]
        cov_u = S @ (Cfull[np.ix_(ii, ii)] + cfg.probit_scale ** 2 * np.eye(7)) @ S
        num = multivariate_normal.cdf(np.zeros(7), mean=-mu_u, cov=cov_u, maxpts=2_000_000, abseps=1e-7, releps=1e-6)
        den = multivariate_normal.cdf(np.zeros(6), mean=-mu_u[:6], cov=cov_u[:6, :6], maxpts=2_000_000, abseps=1e-7, releps=1e-6)
        orth.append(num / den)
    orth = np.array(orth)
    # elliptical slice sampling on (h_P, h_test, theta) jointly (prior N(mfull, Cfull), likelihood on h_P only)
    def loglik(v):
        return float(log_ndtr((2 * ys - 1) * v[:6] / cfg.probit_scale).sum())
    rng = np.random.default_rng(99); cur = mfull.copy(); ll = loglik(cur); keep = []
    for it in range(405000):
        nu = Lf @ rng.standard_normal(len(mfull))
        logy = ll + np.log(rng.uniform())
        ang = rng.uniform(0, 2 * np.pi); lo_, hi_ = ang - 2 * np.pi, ang
        while True:
            prop = mfull + (cur - mfull) * np.cos(ang) + nu * np.sin(ang)
            lp_ = loglik(prop)
            if lp_ > logy:
                cur, ll = prop, lp_; break
            if ang < 0:
                lo_ = ang
            else:
                hi_ = ang
            ang = rng.uniform(lo_, hi_)
        if it >= 5000 and it % 5 == 0:
            keep.append(cur.copy())
    keep = np.array(keep)
    pk = ndtr(keep[:, 6:6 + len(test_s)] / cfg.probit_scale)
    ess_p = pk.mean(0)
    ess_theta = float(keep[:, -1].mean())
    nb = 40; bl = len(pk) // nb                                  # batch-means Monte Carlo standard error of the chain
    ess_se = pk[:nb * bl].reshape(nb, bl, -1).mean(1).std(0, ddof=1) / np.sqrt(nb)
    lap_theta, lap_theta_sd = lap["theta_mean"], float(np.sqrt(lap["theta_var"]))
    agree_ro = float(np.max(np.abs(is_p - orth))); agree_re = float(np.max(np.abs(is_p - ess_p))); agree_oe = float(np.max(np.abs(orth - ess_p)))
    # orthant QMC is the precise reference; rejection sampling is exact but noisy (few accepted draws), ESS is MCMC
    tol_oe = float(4 * np.max(ess_se) + 1e-3)
    check("tractable_case_three_independent_methods_agree", agree_oe < tol_oe and agree_ro < 4 * float(np.max(is_se)) + 1e-4 and abs(is_theta - ess_theta) < 4 * is_theta_sd / np.sqrt(ess_is) + 0.005,
          orthant_qmc_vs_elliptical_slice=agree_oe, tolerance_4_batch_means_se=tol_oe, ess_samples=int(len(pk)), rejection_accepted_draws=ess_is, rejection_total_draws=n_draw, max_rejection_standard_error=float(np.max(is_se)),
          max_rejection_vs_orthant_qmc=agree_ro, max_rejection_vs_elliptical_slice=agree_re, theta_rejection=is_theta, theta_ess=ess_theta,
          note="validation design repaired after the first run: prior importance sampling had only 163 effective draws (recorded in the ledger)")
    check("tractable_case_laplace_error_reported", True, max_abs_probability_error_laplace_vs_exact=float(np.max(np.abs(lap_p - orth))),
          mean_abs_probability_error=float(np.mean(np.abs(lap_p - orth))), laplace_p=lap_p.round(4).tolist(), exact_p_orthant=orth.round(4).tolist(),
          theta_mean_laplace=lap_theta, theta_mean_exact=is_theta, theta_sd_laplace=lap_theta_sd, theta_sd_exact=is_theta_sd,
          note="approximation error of the Laplace step on a 6-label 4-input case; a limitation, not a pass/fail")
    res["seconds"] = time.time() - t0
    res["status"] = "PASS" if all(v["passed"] for v in C.values()) else "FAIL"
    (OUT / "validation_results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ("passed", "max_abs_difference", "max_abs_probability_error_laplace_vs_IS", "failed", "refused_message")} for k, v in C.items()}, indent=1, default=float))
    print("STATUS", res["status"], f"{res['seconds']:.1f}s")
    return res


if __name__ == "__main__":
    main()
