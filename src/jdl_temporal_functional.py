"""Temporal repair sub-study — principled functional model: rank-3 probabilistic PCA with missing data (EM) and
coefficient GPs that carry each training run's coefficient-estimation uncertainty.

Why: the frozen Week 20 rank-3 functional model fitted coefficients of partial (early-ending) records by an
unregularized least-squares projection; on their few observed bins the basis is nearly collinear, which produced
coefficients up to 26,571 and exploding predictions.  Here every training run's coefficient vector has the
prior N(0, I) and an exact Gaussian posterior given only its observed bins, so a partial record is shrunk toward the
prior instead of extrapolated, and its posterior variance is passed to the coefficient GP as per-run noise.

Data, checkpoints, compression (K = 360 bin means + native peak accounting in the evaluation) and summaries are the
unchanged Week 20 Track 2 objects.  Only paid training runs enter the fit; test traces never choose anything.

Step: python -m src.jdl_temporal_functional [names...]
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from src.week20_track2_common import sample_summaries
from src.week20_track2_data import S_MAX
from src.week20_track2_models import CKPT, PRED, load_ckpt

ROOT = Path(__file__).resolve().parents[1]
TR = ROOT / "outputs" / "joint_depth_label_development" / "temporal_repair"
RANK = 3
EM_MAX_ITER, EM_TOL = 3000, 1e-9          # relative change of the observed-data log likelihood
RIDGE = 1e-6                              # numerical ridge on the per-bin M-step normal equations
N_SAMPLES, SEED = 2000, 20261013
TAG = "functional_ppca"


def ppca_missing(Y, rank=RANK, max_iter=EM_MAX_ITER, tol=EM_TOL, seed=SEED):
    """EM for y_i = m + W c_i + eps,  c_i ~ N(0, I),  eps ~ N(0, s2 I), on the observed entries of Y (NaN = missing)."""
    n, K = Y.shape
    obs = np.isfinite(Y)
    supported = obs.any(0)
    Ys = Y[:, supported]; O = obs[:, supported]; Kb = Ys.shape[1]
    m = np.nanmean(Ys, axis=0)
    R0 = np.where(O, Ys - m, 0.0)
    _, sv, vt = np.linalg.svd(R0, full_matrices=False)                    # deterministic initialisation (zero-filled residuals)
    W = vt[:rank].T * (sv[:rank] / np.sqrt(max(n, 1)))
    s2 = float(np.sum(R0 ** 2) / O.sum()) * 0.5 + 1e-6
    ll_old, status, it = -np.inf, "max_iter", 0
    for it in range(1, max_iter + 1):
        # E-step: posterior of c_i given only its observed bins
        Mu = np.zeros((n, rank)); S = np.zeros((n, rank, rank)); ll = 0.0
        for i in range(n):
            o = O[i]
            Wo = W[o]; r = Ys[i, o] - m[o]
            P = np.eye(rank) + Wo.T @ Wo / s2
            Si = np.linalg.inv(P); Si = (Si + Si.T) / 2
            Mu[i] = Si @ (Wo.T @ r) / s2; S[i] = Si
            # marginal log likelihood of the observed entries (Woodbury)
            no = int(o.sum())
            sign, logdetP = np.linalg.slogdet(P)
            quad = r @ r / s2 - (Wo.T @ r) @ Si @ (Wo.T @ r) / s2 ** 2
            ll += -0.5 * (no * np.log(2 * np.pi * s2) + logdetP + quad)
        if np.isfinite(ll_old) and abs(ll - ll_old) <= tol * abs(ll_old):
            status = "converged"; break
        ll_old = ll
        # M-step: per bin, regress on the augmented [1, c] with expected sufficient statistics
        Ec = np.c_[np.ones(n), Mu]
        Ecc = np.zeros((n, rank + 1, rank + 1)); Ecc[:, 0, 0] = 1.0; Ecc[:, 0, 1:] = Mu; Ecc[:, 1:, 0] = Mu
        Ecc[:, 1:, 1:] = S + Mu[:, :, None] * Mu[:, None, :]
        resid = 0.0
        for b in range(Kb):
            ib = O[:, b]
            A = Ecc[ib].sum(0) + RIDGE * np.eye(rank + 1)
            rhs = (Ys[ib, b][:, None] * Ec[ib]).sum(0)
            theta = np.linalg.solve(A, rhs)
            m[b], W[b] = theta[0], theta[1:]
        for i in range(n):
            o = O[i]; th = np.c_[m[o], W[o]]
            e = Ys[i, o] - th @ Ec[i]
            resid += e @ e + np.einsum("bj,jk,bk->", th, Ecc[i] - np.outer(Ec[i], Ec[i]), th)
        s2 = float(resid / O.sum())
    # rotate to an orthogonal basis (same model): W = U D V^T -> W' = U D, c' = V^T c
    U, D, Vt = np.linalg.svd(W, full_matrices=False)
    Wr = U * D; Mu_r = Mu @ Vt.T; S_r = np.einsum("jk,ikl,ml->ijm", Vt, S, Vt)
    Wfull = np.zeros((K, rank)); Wfull[supported] = Wr
    mfull = np.full(K, np.nan); mfull[supported] = m
    return {"m": mfull, "W": Wfull, "s2": s2, "Mu": Mu_r, "S": S_r, "supported": supported, "status": status, "iterations": it, "loglik": float(ll)}


def coef_gp(Z, c, v):
    """GP on one coefficient with per-run noise = that run's coefficient posterior variance (plus a learned nugget)."""
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
    mu, sd = c.mean(), c.std() + 1e-12
    k = ConstantKernel(1.0, (1e-3, 1e3)) * Matern(np.ones(Z.shape[1]), (1e-2, 1e2), nu=1.5) + WhiteKernel(1e-2, (1e-6, 1.0))
    gp = GaussianProcessRegressor(k, alpha=v / sd ** 2 + 1e-10, normalize_y=False, n_restarts_optimizer=0, random_state=0).fit(Z, (c - mu) / sd)
    return gp, mu, sd


def fit_checkpoint(name):
    d = load_ckpt(name); t0 = time.time()
    em = ppca_missing(d["Ytr"])
    K = int(d["K"]); sup = em["supported"]
    mus, varl, hyp = [], [], []
    with warnings.catch_warnings(record=True) as wl:
        warnings.simplefilter("always")
        for k in range(RANK):
            gp, mu, sd = coef_gp(d["z_train"], em["Mu"][:, k], em["S"][:, k, k])
            mm, ss = gp.predict(d["z_test"], return_std=True)
            nug = float(np.exp(gp.kernel_.theta[-1]))
            mus.append(mm * sd + mu); varl.append(np.maximum(ss ** 2 - nug, 1e-12) * sd ** 2)
            hyp.append({"component": k, "kernel": str(gp.kernel_)[:200], "lml": float(gp.log_marginal_likelihood_value_)})
    mus, varl = np.array(mus).T, np.array(varl).T
    W, m = em["W"], np.where(sup, em["m"], 0.0)
    mean = m[None, :] + mus @ W.T
    var_lat = varl @ (W ** 2).T
    rng = np.random.default_rng(SEED)
    summ = {k: [] for k in ("max_planned", "max_observed", "argmax_s_observed", "exceed_s_observed")}
    for i in range(len(mus)):
        draws = mus[i] + rng.standard_normal((N_SAMPLES, RANK)) * np.sqrt(varl[i])
        traj = m[None, :] + draws @ W.T
        plan = d["te_plan"][i] & sup; obs = np.isfinite(d["te_obs"][i]) & sup
        for k_, v in sample_summaries(traj, plan, obs, d["centers"], S_MAX / K).items():
            summ[k_].append(v)
    PRED.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(PRED / f"{TAG}_{name}.npz", test_ids=d["test_ids"], mean=mean, var_latent=var_lat, var_noise=np.full(mean.shape, em["s2"]),
                        supported=sup, **{k: np.array(v) for k, v in summ.items()})
    cmax = np.abs(em["Mu"]).max(1)
    row = {"checkpoint": name, "tag": TAG, "fit_seconds": time.time() - t0, "em_status": em["status"], "em_iterations": em["iterations"], "em_loglik": em["loglik"],
           "residual_var": em["s2"], "coef_gp_fits": RANK, "max_abs_coefficient": float(cmax.max()), "median_abs_coefficient": float(np.median(cmax)),
           "max_coefficient_posterior_sd": float(np.sqrt(np.max(np.diagonal(em["S"], axis1=1, axis2=2)))),
           "warnings": " | ".join(sorted({str(w.message)[:80] for w in wl}))[:300], "hyper": json.dumps(hyp)[:900]}
    TR.mkdir(parents=True, exist_ok=True)
    with open(TR / "functional_ppca_fits.jsonl", "a") as fh:
        fh.write(json.dumps(row) + "\n")
    print(json.dumps({k: row[k] for k in ("checkpoint", "fit_seconds", "em_status", "em_iterations", "max_abs_coefficient", "max_coefficient_posterior_sd")}), flush=True)
    return row


def validate():
    """Controlled staircase example: known rank-3 structure, records truncated at random lengths (some very short).
    Checks: EM recovers the true subspace, partial records get bounded (shrunk) coefficients with larger posterior
    variance, and the frozen Week 20 least-squares ALS on the same data shows the original blow-up."""
    from src.week20_track2_models import als_rank
    g = np.random.default_rng(3)
    n, K = 60, 360
    s = np.linspace(0, 0.9, K)
    W0 = np.c_[np.sin(3 * s), np.cos(5 * s) * s, np.exp(-((s - 0.3) / 0.1) ** 2)]
    c0 = g.standard_normal((n, 3))
    m0 = 4.0 * (1 - np.exp(-8 * s))
    Y = m0 + c0 @ W0.T + 0.05 * g.standard_normal((n, K))
    ends = np.r_[g.integers(60, 100, 8), g.integers(200, K + 1, n - 8)]          # 8 early-ending records
    for i, e in enumerate(ends):
        Y[i, e:] = np.nan
    em = ppca_missing(Y)
    Q0, _ = np.linalg.qr(W0); Q1, _ = np.linalg.qr(em["W"])
    angle = float(np.degrees(np.arccos(np.clip(np.linalg.svd(Q0.T @ Q1, compute_uv=False).min(), -1, 1))))
    short = ends < 100
    psd = np.sqrt(np.diagonal(em["S"], axis1=1, axis2=2)).max(1)
    sup = np.isfinite(Y).any(0)
    R = (Y - np.nanmean(Y, 0))[:, sup]
    _, C_als, _ = als_rank(R)
    res = {"largest_principal_angle_deg_true_vs_EM_subspace": angle, "em_status": em["status"], "em_iterations": em["iterations"],
           "max_abs_coefficient_partial_records": float(np.abs(em["Mu"][short]).max()), "max_abs_coefficient_full_records": float(np.abs(em["Mu"][~short]).max()),
           "mean_posterior_sd_partial": float(psd[short].mean()), "mean_posterior_sd_full": float(psd[~short].mean()),
           "frozen_week20_ALS_max_abs_coefficient_partial_records": float(np.abs(C_als[short]).max()),
           "frozen_week20_ALS_max_abs_coefficient_full_records": float(np.abs(C_als[~short]).max())}
    res["passed"] = bool(angle < 10 and res["max_abs_coefficient_partial_records"] < 10 and res["mean_posterior_sd_partial"] > res["mean_posterior_sd_full"])
    TR.mkdir(parents=True, exist_ok=True)
    (TR / "functional_ppca_validation.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    return res


def main(names=None):
    ck = pd.read_csv(ROOT / "outputs/week20_active_temporal_development/track2/checkpoints.csv")
    done = set()
    f = TR / "functional_ppca_fits.jsonl"
    if f.exists():
        done = {json.loads(l)["checkpoint"] for l in f.read_text().splitlines() if l.strip()}
    for name in (names or ck.checkpoint.tolist()):
        if name not in done:
            fit_checkpoint(name)


if __name__ == "__main__":
    if sys.argv[1:2] == ["validate"]:
        validate()
    else:
        main(sys.argv[1:] or None)
