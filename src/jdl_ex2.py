"""Exploratory EX2 — joint model with a TRAINED response prior (train-only ML-II on the paid responses).

Mechanism (from the Stage M mechanism report).  Under the fixed four-input response prior (amplitude 0.60,
lengthscales 1.5 on standardized log inputs) the response GP smooths slow-scan depths into the fast-scan corner: for
the fast-scan NEW negatives J predicted f = 0.10-0.42 while the observed z = log(A/111) was -0.33 to +0.17, and the
response oracle showed that better depth would separate part of them.  ACTIVE E1 learns its response kernel by
paid-only ML-II and reaches higher NEW BA.  EX2 keeps J's coupling, threshold and discrepancy priors fixed and only
replaces the response amplitude and four lengthscales by the ML-II estimate on the PAID responses (z, fixed noise
0.03, zero mean - the J response model), refitted at every checkpoint.  Test responses never enter.

Data and paths: identical to EX1 (DEV repeats 5-8, feature-only maximin paths, B16/B40; three populations).
Arms: J_trained (new) vs J (frozen priors; from the EX1 cache, identical paths), both evaluated at p >= 0.5 and at
p >= pi_hat (the EX1 rule, train-only).

Steps: python -m src.jdl_ex2 manifest | run | evaluate
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import datetime as dt
import gzip
import hashlib
import json
import sys
import time
import warnings
from dataclasses import replace

import numpy as np
import pandas as pd

import src.jdl_model as JM
import src.jdl_stage_m as SMM
from src.jdl_ex1 import CACHE as EX1_CACHE, EX as EX1_DIR, REPEATS, build_tasks_r
from src.jdl_evaluate import boot_weights

EX = SMM.OUT / "exploratory" / "EX2_trained_response_prior"
CACHE = SMM.OUT / "_cache" / "ex2"
POPS = ("NEW", "OLD", "POOLED")
PREDICTIONS = {
    "EX2-P1_response": "NEW, B40: held-out response error RMSE(f_mean - z_obs) of J_trained < J (all NEW runs with A, and the fast scans VX > 0.85 separately). Direction from the mechanism report; magnitude unknown.",
    "EX2-P2_labels": "NEW, B40, at p >= pi_hat: BA(J_trained) >= BA(J); log loss(J_trained) <= log loss(J). Direction only; magnitude unknown.",
    "EX2-P3_other_populations": "OLD and POOLED: no directional expectation; reported.",
    "falsification": "EX2-P1 is falsified if the trained response prior does not lower the NEW B40 held-out response RMSE; EX2-P2 is falsified if BA at pi_hat is lower.",
}


def trained_config(paid_X_std, z):
    """ML-II of the J response prior on the paid responses only (amplitude, four ARD lengthscales; noise fixed 0.03)."""
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern
    ok = np.isfinite(z)
    k = ConstantKernel(0.36, (1e-3, 1e2)) * Matern(np.full(paid_X_std.shape[1], 1.5), (5e-2, 2e1), nu=1.5)
    with warnings.catch_warnings(record=True) as wl:
        warnings.simplefilter("always")
        gp = GaussianProcessRegressor(k, alpha=JM.STAGE_M_CONFIG.response_noise_sd ** 2 + 1e-10, normalize_y=False, n_restarts_optimizer=0,
                                      random_state=0).fit(paid_X_std[ok], z[ok])
    amp = float(np.sqrt(gp.kernel_.k1.constant_value)); ell = tuple(float(v) for v in np.atleast_1d(gp.kernel_.k2.length_scale))
    return replace(JM.STAGE_M_CONFIG, f_amplitude=amp, f_lengthscale=ell), {"f_amplitude": amp, "f_lengthscale": ell,
                                                                            "lml": float(gp.log_marginal_likelihood_value_), "warnings": " | ".join(sorted({str(w.message)[:80] for w in wl}))[:200]}


def write_manifest():
    if not (EX1_DIR / "EX1_MANIFEST.json").exists():
        raise SystemExit("EX1 manifest (shared paths) must exist")
    EX.mkdir(parents=True, exist_ok=True)
    tasks = build_tasks_r()
    man = {"idea": "EX2 trained response prior for the joint model", "status": "EXPLORATORY, frozen before any EX2 fit; separate from the main study",
           "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "parent_commit": SMM._git("rev-parse", "HEAD"),
           "mechanism": __doc__.split("Mechanism")[1].split("Data and paths")[0].strip(" .\n"), "paths": "identical to EX1 (exploratory/EX1_ba_aligned_decision_rule/paths.csv)",
           "trained_part": "ML-II (sklearn L-BFGS-B, 0 restarts, start at the frozen values) of the response amplitude in [0.03, 10] and four lengthscales in [0.05, 20] on the paid responses only, noise fixed at 0.03, zero mean; theta, delta and tau priors unchanged",
           "arms": {"J_trained": "new fits", "J": "frozen-prior J from the EX1 cache (identical paths and checkpoints)"},
           "fit_requests": len(tasks) * len(SMM.BUDGETS), "predictions": PREDICTIONS,
           "outcomes": "held-out response RMSE (all and fast scans), BA/specificity/sensitivity at p >= 0.5 and p >= pi_hat, log loss, AUC; paired differences with the class-stratified simulation-cluster bootstrap",
           "protections": ["train-only hyperparameters (paid responses)", "no selection on held-out outcomes", "outcomes preserved"],
           "code_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in ("src/jdl_ex2.py", "src/jdl_ex1.py", "src/jdl_stage_m.py", "src/jdl_model.py")}}
    (EX / "EX2_MANIFEST.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(json.dumps({k: man[k] for k in ("fit_requests", "trained_part")}, indent=1))


def run():
    if not (EX / "EX2_MANIFEST.json").exists():
        raise SystemExit("commit the EX2 manifest first")
    tasks = build_tasks_r()
    paths = pd.read_csv(EX1_DIR / "paths.csv")
    CACHE.mkdir(parents=True, exist_ok=True)
    t0, n = time.time(), 0
    for t in tasks:
        g = paths[(paths.population == t["population"]) & (paths.repeat == t["repeat"]) & (paths.fold == t["fold"])].sort_values("query_index")
        pos = {s: i for i, s in enumerate(t["ids"])}; t["path"] = g.sim_id.map(pos).to_numpy(int)
        std, _ = SMM.standardizer(t)
        for b in SMM.BUDGETS:
            cf = CACHE / f"{t['population']}__r{t['repeat']}_f{t['fold']}__B{b}__J_trained.json.gz"
            if cf.exists():
                continue
            L = t["path"][:b]; paid = SMM.Oracle(t).reveal(L)
            cfg, info = trained_config(std(paid.X), paid.z)
            rec = {"population": t["population"], "repeat": t["repeat"], "fold": t["fold"], "budget": b, "arm": "J_trained", **{k: (list(v) if isinstance(v, tuple) else v) for k, v in info.items()}}
            try:
                m = JM.JointDepthLabelGP(std(t["X"][t["pool"]]), cfg).fit(std(paid.X), paid.y, paid.z)
                q = m.marginals(std(t["X"][t["test"]]))
                rec.update({"status": "ok", "solver_status": m.diagnostics["solver_status"], "gradient_inf": m.diagnostics["gradient_inf"], "theta_mean": q["theta_mean"],
                            "paid_prevalence": float(np.mean(paid.y))})
                preds = [{"population": t["population"], "repeat": t["repeat"], "fold": t["fold"], "budget": b, "arm": "J_trained", "sim_id": t["ids"][i],
                          "p": float(q["p"][j]), "f_mean": float(q["f_mean"][j]), "prediction_status": "ok"} for j, i in enumerate(t["test"])]
            except Exception as e:
                rec.update({"status": "failed", "error": f"{type(e).__name__}: {e}"[:200], "paid_prevalence": float(np.mean(paid.y))}); preds = []
            n += 1
            cf.write_bytes(gzip.compress(json.dumps({"fit": rec, "predictions": preds}, default=float).encode()))
    print(f"EX2 fits this session: {n}, {time.time() - t0:.1f}s")


def evaluate():
    rows = []
    for d, arm in ((CACHE, "J_trained"), (EX1_CACHE, "J")):
        for f in sorted(d.glob(f"*__{arm}.json.gz")):
            r = json.loads(gzip.decompress(f.read_bytes()))
            for p in r["predictions"]:
                rows.append({**p, "pi_hat": r["fit"]["paid_prevalence"]})
    pr = pd.DataFrame(rows)
    tasks = build_tasks_r()
    out, crow, fits = [], [], []
    for pop in POPS:
        ts = [t for t in tasks if t["population"] == pop]
        ids, y, A, VX = ts[0]["ids"], ts[0]["y"], ts[0]["A"], ts[0]["VX"]; pos = {s: i for i, s in enumerate(ids)}
        zobs = np.where(np.isfinite(A), np.log(np.where(np.isfinite(A), A, 1.0) / 111.0), np.nan)
        W = boot_weights(y)
        store = {}
        for arm in ("J", "J_trained"):
            for rep in REPEATS:
                for b in SMM.BUDGETS:
                    g = pr[(pr.population == pop) & (pr.arm == arm) & (pr.repeat == rep) & (pr.budget == b)]
                    p = np.full(len(ids), np.nan); f = np.full(len(ids), np.nan); th = np.full(len(ids), np.nan)
                    ii = g.sim_id.map(pos).to_numpy(int); p[ii] = g.p.to_numpy(float); f[ii] = g.f_mean.to_numpy(float); th[ii] = g.pi_hat.to_numpy(float)
                    store[(arm, rep, b)] = (p, f, th)
                    ok = np.isfinite(zobs) & np.isfinite(f); fast = ok & (VX > 0.85)
                    for rule, thr in (("p>=0.5", np.full(len(ids), 0.5)), ("p>=pi_hat", th)):
                        dec = p >= thr
                        out.append({"population": pop, "arm": arm, "repeat": rep, "budget": b, "rule": rule,
                                    "BA": 0.5 * (np.mean(dec[y == 1]) + np.mean(~dec[y == 0])), "specificity": float(np.mean(~dec[y == 0])), "sensitivity": float(np.mean(dec[y == 1])),
                                    "log_loss": float(-np.mean(y * np.log(np.clip(p, 1e-12, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-12, 1)))),
                                    "response_rmse_all": float(np.sqrt(np.mean((f[ok] - zobs[ok]) ** 2))), "response_rmse_fast": float(np.sqrt(np.mean((f[fast] - zobs[fast]) ** 2))) if fast.any() else np.nan})
        for b in SMM.BUDGETS:
            for metric in ("BA@pi_hat", "BA@0.5", "log_loss", "response_rmse_all"):
                dd = []
                for rep in REPEATS:
                    (p1, f1, t1), (p0, f0, t0) = store[("J_trained", rep, b)], store[("J", rep, b)]
                    def stat(p, f, th):
                        if metric.startswith("BA"):
                            thr = th if metric == "BA@pi_hat" else 0.5
                            dec = (p >= thr).astype(float)
                            sens = (W @ ((y == 1) * dec)) / (W @ (y == 1)); spec = (W @ ((y == 0) * (1 - dec))) / (W @ (y == 0))
                            return 0.5 * (sens + spec)
                        if metric == "log_loss":
                            pc = np.clip(p, 1e-12, 1 - 1e-12)
                            return (W @ -(y * np.log(pc) + (1 - y) * np.log(1 - pc))) / W.sum(1)
                        ok = np.isfinite(zobs) & np.isfinite(f)
                        return np.sqrt((W[:, ok] @ (f[ok] - zobs[ok]) ** 2) / W[:, ok].sum(1))
                    dd.append(stat(p1, f1, t1) - stat(p0, f0, t0))
                d = np.mean(np.vstack(dd), axis=0)
                crow.append({"population": pop, "budget": b, "metric": metric, "contrast": "J_trained - J", "estimate": float(d[0]),
                             "per_repeat": json.dumps([float(x[0]) for x in dd]), "cluster_bootstrap_lo": float(np.percentile(d[1:], 2.5)), "cluster_bootstrap_hi": float(np.percentile(d[1:], 97.5))})
    for f in sorted(CACHE.glob("*.json.gz")):
        fits.append(json.loads(gzip.decompress(f.read_bytes()))["fit"])
    mt, ct, ft = pd.DataFrame(out), pd.DataFrame(crow), pd.DataFrame(fits)
    EX.mkdir(parents=True, exist_ok=True)
    mt.to_csv(EX / "metrics_per_repeat.csv", index=False, lineterminator="\n"); ct.to_csv(EX / "contrasts.csv", index=False, lineterminator="\n")
    ft.to_csv(EX / "fit_log.csv", index=False, lineterminator="\n")
    g = lambda m, b=40: ct[(ct.population == "NEW") & (ct.budget == b) & (ct.metric == m)].iloc[0]
    nm = mt[(mt.population == "NEW") & (mt.budget == 40) & (mt.rule == "p>=0.5")].groupby("arm").response_rmse_fast.mean()
    res = {"EX2-P1_response": {"estimate_all": g("response_rmse_all").estimate, "interval": [g("response_rmse_all").cluster_bootstrap_lo, g("response_rmse_all").cluster_bootstrap_hi],
                               "fast_scan_rmse": nm.to_dict(), "supported": bool(g("response_rmse_all").estimate < 0 and nm["J_trained"] < nm["J"])},
           "EX2-P2_labels": {"BA_at_pi_hat": g("BA@pi_hat").estimate, "BA_interval": [g("BA@pi_hat").cluster_bootstrap_lo, g("BA@pi_hat").cluster_bootstrap_hi],
                             "log_loss": g("log_loss").estimate, "supported": bool(g("BA@pi_hat").estimate >= 0 and g("log_loss").estimate <= 0)},
           "fits": int(len(ft)), "statuses": ft.status.value_counts().to_dict() if len(ft) else {},
           "learned_lengthscales_median_NEW_B40": ft[(ft.population == "NEW") & (ft.budget == 40)].f_lengthscale.apply(lambda v: np.round(v, 2).tolist()).head(3).tolist() if len(ft) else []}
    (EX / "EX2_RESULTS.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    pd.set_option("display.width", 250)
    print(mt.groupby(["population", "budget", "arm", "rule"])[["BA", "specificity", "sensitivity", "log_loss", "response_rmse_all", "response_rmse_fast"]].mean().round(3).to_string())
    print(ct.round(4).to_string()); print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "manifest"
    {"manifest": write_manifest, "run": run, "evaluate": evaluate}[step]()
