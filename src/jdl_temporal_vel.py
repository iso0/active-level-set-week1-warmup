"""TEMPORAL_VEL (pilot C; owner request of 2026-10-16): a small temporal GP q(x, tau) on the maximum-melt-velocity channel.

Why this channel: pilot B found the velocity spike size the most learnable transient summary (R2_oof 0.87) and informative
in the corner.  Small trial only; the 40 long depth SVGP fits are not repeated.
Target: per run, y(tau_k) = log of the bin-median maximum melt velocity over K = 40 equal bins of normalised active-window
time tau in (0, 1] (post-onset valid rows, implausible > 100 m/s and non-finite rows excluded from the bin statistic; Week 19
active window).  Bin maxima are kept separately to score peaks.  A run without all 40 bins is UNAVAILABLE (recorded).
Model (exact, 5-D): Kronecker GP  vec(Y) ~ N(mu, Kx (x) Kt + s2 I) on the complete grid of training runs x bins; Kx = ARD
Matern 3/2 on the four standardised log inputs, Kt = Matern 3/2 on tau, shared signal variance and noise; hyperparameters
by ML-II (L-BFGS-B on the exact log marginal likelihood via the two eigendecompositions; 3 fixed restarts).  mu = per-bin
training mean (the baseline).
Baselines: training-mean curve; independent per-bin GP regressions are NOT run (cost); scalar spike GP from pilot B is cited.
Endpoints (fixed): out-of-fold (DEV repeats 3-4 folds; train = fold pool, all pool runs revealed: an upper bound) curve RMSE
of log velocity (GP vs mean curve), R2_curve = 1 - SSE_gp / SSE_mean, peak error = |max_k yhat - max_k y| (log units) and
peak-bin error |argmax yhat - argmax y| in bins, 90 % pointwise coverage, fit seconds per fold.  Verdict: USEFUL if mean
R2_curve >= 0.3 and the GP beats the mean curve on peak error in both repeats; else NOT USEFUL.
Steps: python -m src.jdl_temporal_vel validate | manifest | run
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import datetime as dt
import json
import sys
import time
import traceback

import numpy as np
import pandas as pd
from scipy.optimize import minimize

import src.jdl_physical_data as PD
import src.jdl_physical_pilot as PP
import src.jdl_stage_m as SMM
import src.jdl_trained_al as TA

STUDY = "TEMPORAL_VEL"
OUT = SMM.OUT / "temporal_vel"
MANIFEST = OUT / "TEMPORAL_VEL_MANIFEST.json"
VALIDATION = OUT / "TEMPORAL_VEL_VALIDATION.json"
K_BINS, RESTARTS = 40, 3
CODE = ("src/jdl_temporal_vel.py", "src/jdl_physical_pilot.py", "src/jdl_physical_data.py", "src/jdl_trained_al.py", "src/jdl_stage_m.py")


def matern32(A, B, ls):
    d = np.sqrt(np.maximum(0.0, (((A[:, None, :] - B[None, :, :]) / ls) ** 2).sum(-1)))
    return (1 + np.sqrt(3) * d) * np.exp(-np.sqrt(3) * d)


def curves(ids):
    """(n_runs, K) bin medians and bin maxima of log velocity; NaN rows for unavailable runs."""
    W = pd.read_csv(PP.W19_DEPTH).set_index("sim_id")
    med, mx, status = np.full((len(ids), K_BINS), np.nan), np.full((len(ids), K_BINS), np.nan), []
    for i, s in enumerate(ids):
        t = PP._load(PD.local(s, "time.dat")) * 1e3; z = PP._load(PD.local(s, "position-bounds_melt.dat"))[:, 4]
        v = PP._load(PD.local(s, "maximum-velocity_melt.dat")); cut = float(W.loc[s, "active_cutoff_ms"])
        if not (len(t) == len(z) == len(v)) or not np.isfinite(cut):
            status.append("UNAVAILABLE: row counts or cutoff"); continue
        valid = np.isfinite(z) & (np.abs(z) < PP.SENT); act = valid & (t <= cut) & np.isfinite(v) & (v > 0) & (v <= PP.V_PLAUSIBLE_MAX)
        if act.sum() < 4 * K_BINS:
            status.append("UNAVAILABLE: too few active rows"); continue
        ta = t[act]; tau = (ta - ta[0]) / max(1e-12, ta[-1] - ta[0]); b = np.minimum(K_BINS - 1, (tau * K_BINS).astype(int)); lv = np.log(v[act])
        ok = True
        for k in range(K_BINS):
            m = b == k
            if not m.any():
                ok = False; break
            med[i, k], mx[i, k] = np.median(lv[m]), np.max(lv[m])
        status.append("ok" if ok else "UNAVAILABLE: empty bin")
        if not ok:
            med[i], mx[i] = np.nan, np.nan
    return med, mx, status


class KronGP:
    """Exact GP on a complete grid: cov = s2f * Kx(theta_x) (x) Kt(theta_t) + s2n I, per-bin mean."""

    def __init__(self, X, tau):
        self.X, self.tau = X, tau[:, None]

    def _parts(self, p):
        lsx, lst, sf, sn = np.exp(p[:4]), np.exp(p[4]), np.exp(p[5]), np.exp(p[6])
        Kx = matern32(self.X, self.X, lsx); Kt = matern32(self.tau, self.tau, np.array([lst]))
        ex, Ux = np.linalg.eigh(Kx); et, Ut = np.linalg.eigh(Kt)
        lam = sf * np.maximum(ex, 0)[:, None] * np.maximum(et, 0)[None, :] + sn
        return Ux, Ut, lam, lsx, lst, sf, sn

    def nlml(self, p, R):
        Ux, Ut, lam, *_ = self._parts(p)
        A = Ux.T @ R @ Ut
        return 0.5 * float(np.sum(A ** 2 / lam) + np.sum(np.log(lam)) + R.size * np.log(2 * np.pi))

    def fit(self, Y):
        self.mu = Y.mean(0); R = Y - self.mu; best = None
        starts = [np.r_[np.zeros(4), np.log(0.2), np.log(R.var()), np.log(0.1 * R.var())]]
        g = np.random.default_rng(0)
        for _ in range(RESTARTS - 1):
            starts.append(starts[0] + g.normal(0, 0.7, 7))
        for s0 in starts:
            r = minimize(self.nlml, s0, args=(R,), method="L-BFGS-B", bounds=[(-4, 4)] * 4 + [(-5, 1), (-8, 3), (-12, 1)], options={"maxiter": 300})
            if best is None or r.fun < best.fun:
                best = r
        self.p = best.x; self.R = R; self.opt = {"nlml": float(best.fun), "success": bool(best.success), "nit": int(best.nit)}
        return self

    def predict(self, Xs):
        """Predictive mean and pointwise variance (noisy observation) at new inputs on the training tau grid."""
        Ux, Ut, lam, lsx, lst, sf, sn = self._parts(self.p)
        alpha = Ux @ ((Ux.T @ self.R @ Ut) / lam) @ Ut.T                       # (sf Kx (x) Kt + s2 I)^-1 vec(R) as a matrix
        Ksx = matern32(Xs, self.X, lsx); Kt = matern32(self.tau, self.tau, np.array([lst]))
        mean = self.mu + sf * Ksx @ alpha @ Kt
        return mean, self._var(Xs)

    def _var(self, Xs):
        Ux, Ut, lam, lsx, lst, sf, sn = self._parts(self.p)
        Ksx = matern32(Xs, self.X, lsx); Kt = matern32(self.tau, self.tau, np.array([lst]))
        a = (sf * Ksx @ Ux) ** 2                                                # (ns, nx): squared projections on x eigenvectors
        c = (Kt @ Ut) ** 2                                                      # (K, K): squared projections on t eigenvectors
        red = a @ (1.0 / lam) @ c.T                                             # (ns, K): sum_ij a_si c_kj / lam_ij
        return np.maximum(1e-12, sf - red + sn)


def run():
    ids = PD.new_ids(); t0 = time.time(); med, mx, status = curves(ids)
    idx = {s: i for i, s in enumerate(ids)}; tau = (np.arange(K_BINS) + 0.5) / K_BINS
    rows, folds = [], []
    for t in TA.build_tasks():
        std = SMM.standardizer(t)[0]; sid = np.asarray(t["ids"]).astype(str)
        tr = [i for i in t["pool"] if np.isfinite(med[idx[sid[i]]]).all()]; te = [i for i in t["test"] if np.isfinite(med[idx[sid[i]]]).all()]
        Ytr = med[[idx[sid[i]] for i in tr]]; Yte = med[[idx[sid[i]] for i in te]]; Mte = mx[[idx[sid[i]] for i in te]]
        ts = time.time(); gp = KronGP(std(t["X"][tr]), tau).fit(Ytr); m, v = gp.predict(std(t["X"][te])); fs = time.time() - ts
        base = np.broadcast_to(Ytr.mean(0), Yte.shape)
        for j, i in enumerate(te):
            rows.append({"repeat": t["repeat"], "fold": t["fold"], "sim_id": sid[i], "sse_gp": float(np.sum((Yte[j] - m[j]) ** 2)), "sse_mean": float(np.sum((Yte[j] - base[j]) ** 2)),
                         "peak_err_gp": float(abs(m[j].max() - Mte[j].max())), "peak_err_mean": float(abs(base[j].max() - Mte[j].max())),
                         "peakbin_err_gp": int(abs(int(np.argmax(m[j])) - int(np.argmax(Mte[j])))), "peakbin_err_mean": int(abs(int(np.argmax(base[j])) - int(np.argmax(Mte[j])))),
                         "cover90": float(np.mean(np.abs(Yte[j] - m[j]) <= 1.645 * np.sqrt(v[j]))), "corner": float(t["X"][i][1]) > SMM.FAST_VX})
        folds.append({"repeat": t["repeat"], "fold": t["fold"], "n_train": len(tr), "n_test": len(te), "fit_seconds": fs, **gp.opt,
                      "lengthscales_x": np.exp(gp.p[:4]).round(3).tolist(), "lengthscale_tau": float(np.exp(gp.p[4])), "signal_var": float(np.exp(gp.p[5])), "noise_var": float(np.exp(gp.p[6]))})
    D, Fd = pd.DataFrame(rows), pd.DataFrame(folds); res = {"study": STUDY, "status_counts": pd.Series(status).value_counts().to_dict(), "per_repeat": {}}
    for rep in (3, 4):
        d = D[D.repeat == rep]
        res["per_repeat"][rep] = {"R2_curve": float(1 - d.sse_gp.sum() / d.sse_mean.sum()), "rmse_gp": float(np.sqrt(d.sse_gp.sum() / (len(d) * K_BINS))),
                                  "rmse_mean": float(np.sqrt(d.sse_mean.sum() / (len(d) * K_BINS))), "peak_err_gp": float(d.peak_err_gp.mean()), "peak_err_mean": float(d.peak_err_mean.mean()),
                                  "peakbin_err_gp": float(d.peakbin_err_gp.mean()), "peakbin_err_mean": float(d.peakbin_err_mean.mean()), "cover90": float(d.cover90.mean()),
                                  "corner_R2_curve": float(1 - d[d.corner].sse_gp.sum() / max(1e-12, d[d.corner].sse_mean.sum())), "n_test_runs": len(d)}
    pr = res["per_repeat"]; r2 = np.mean([pr[r]["R2_curve"] for r in (3, 4)])
    res["verdict"] = "USEFUL" if r2 >= 0.3 and all(pr[r]["peak_err_gp"] < pr[r]["peak_err_mean"] for r in (3, 4)) else "NOT USEFUL"
    res["cost"] = {"fit_seconds_median": float(Fd.fit_seconds.median()), "fit_seconds_total": float(Fd.fit_seconds.sum()), "wall_seconds": time.time() - t0}
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "results").mkdir(exist_ok=True)
    D.to_csv(OUT / "results" / "per_run.csv", index=False, lineterminator="\n"); Fd.to_csv(OUT / "results" / "folds.csv", index=False, lineterminator="\n")
    (OUT / "results" / "TEMPORAL_VEL_RESULTS.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))


def validate():
    t0 = time.time(); checks, info = {}, {}
    try:
        g = np.random.default_rng(1); X = g.normal(0, 1, (7, 4)); tau = (np.arange(5) + 0.5) / 5
        Y = np.sin(X[:, :1] + 3 * tau[None, :]) + 0.05 * g.normal(size=(7, 5))
        gp = KronGP(X, tau); p = np.r_[np.zeros(4), np.log(0.3), 0.0, np.log(0.01)]; R = Y - Y.mean(0)
        # brute-force reference with the full covariance
        Kx = matern32(X, X, np.ones(4)); Kt = matern32(tau[:, None], tau[:, None], np.array([0.3])); C = np.kron(Kx, Kt) + 0.01 * np.eye(35)
        r = R.reshape(-1); sign, logdet = np.linalg.slogdet(C)
        ref = 0.5 * (r @ np.linalg.solve(C, r) + logdet + 35 * np.log(2 * np.pi))
        checks["kronecker_nlml_equals_bruteforce"] = abs(gp.nlml(p, R) - ref) < 1e-8 * max(1, abs(ref))
        gp.p, gp.mu, gp.R = p, Y.mean(0), R
        Xs = g.normal(0, 1, (3, 4)); m, v = gp.predict(Xs)
        Ks = np.kron(matern32(Xs, X, np.ones(4)), Kt); mb = (Ks @ np.linalg.solve(C, r)).reshape(3, 5) + Y.mean(0)
        vb = (1.0 - np.einsum("ij,ji->i", Ks, np.linalg.solve(C, Ks.T)) + 0.01).reshape(3, 5)
        checks["kronecker_mean_equals_bruteforce"] = float(np.max(np.abs(m - mb))) < 1e-8
        checks["kronecker_variance_equals_bruteforce"] = float(np.max(np.abs(v - vb))) < 1e-8
        ids = PD.new_ids()[:3]; med, mx, st = curves(ids)
        checks["curves_extract_three_runs"] = len(st) == 3 and all(s == "ok" for s in st) and np.isfinite(med).all()
        info["example_curve_range_log_m_s"] = [float(np.nanmin(med)), float(np.nanmax(med))]
    except Exception as ex:
        checks["selftest_completed"] = False; info["error"] = f"{type(ex).__name__}: {ex}"[:400]; info["traceback"] = traceback.format_exc()[-2000:]
    res = {"study": STUDY, "status": "PASS" if checks and all(checks.values()) else "FAIL", "checks": {k: bool(v) for k, v in checks.items()}, "info": info,
           "seconds": time.time() - t0, "module_sha256": SMM.sha256(SMM.ROOT / "src" / "jdl_temporal_vel.py")}
    OUT.mkdir(parents=True, exist_ok=True); VALIDATION.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"status": res["status"], "checks": res["checks"], "info": {k: v for k, v in info.items() if k != "traceback"}}, indent=1, default=str))
    if res["status"] != "PASS":
        raise SystemExit(1)


def write_manifest():
    val = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if val["status"] != "PASS" or val["module_sha256"] != SMM.sha256(SMM.ROOT / "src" / "jdl_temporal_vel.py"):
        raise SystemExit("TEMPORAL_VEL validation must PASS with this module before the freeze")
    man = {"study": STUDY, "status": "FROZEN BEFORE ANY TEMPORAL_VEL OUTCOME", "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "parent_commit": SMM._git("rev-parse", "HEAD"), "k_bins": K_BINS, "restarts": RESTARTS,
           "verdict_rule": "USEFUL if mean R2_curve >= 0.3 and GP peak error < mean-curve peak error in both repeats",
           "validation": {"status": val["status"], "sha256": SMM.sha256(VALIDATION)}, "code_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in CODE}}
    MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8"); print(json.dumps({k: man[k] for k in ("status", "written_utc")}, indent=1))


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "run"
    {"validate": validate, "manifest": write_manifest, "run": run}[step]()
