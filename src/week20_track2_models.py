"""Week 20 Track 2 — checkpoint datasets, the scalar A GP reference and the rank-3 functional baseline.

Checkpoints: NEW, repeats 1-2, the ten original folds, budgets 16/40/80, using the Week 19 pilot's shared label-blind
paid prefixes (tables/paid_paths.csv).  Training uses paid runs only; complete runs are held out.  The separable
input x time GP is fitted by src.week20_track2_svgp (GPyTorch, in .venv) from the same checkpoint files.

Steps: python -m src.week20_track2_models prep | scalar | functional | all
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "4")

import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from src.week20_track2_common import sample_summaries
from src.week20_track2_data import CACHE, K_CANDIDATES, PILOT, S_MAX, T2, bin_means, choose_K, compression_rmse, load_native, registry

UREF = 110.9641179189907
BUDGETS = (16, 40, 80)
REPEATS = (1, 2)
CKPT = CACHE / "checkpoints"
PRED = CACHE / "predictions"
N_SAMPLES = 2000
SEED = 20261012


def checkpoints():
    import src.week19_dev_pilot as P
    tasks = {(t["repeat"], t["fold"]): t for t in P.build_tasks()}
    pp = pd.read_csv(PILOT / "tables/paid_paths.csv")
    for (r, f), g in pp.groupby(["repeat", "fold"]):
        g = g.sort_values("query_index")
        for b in BUDGETS:
            yield r, f, b, g.sim_id.iloc[:b].tolist(), tasks[(r, f)]


def compression_table(native):
    rows = []
    for s, tr in native.items():
        if tr is None:
            continue
        for K in K_CANDIDATES:
            e, loss = compression_rmse(tr, K)
            rows.append({"sim_id": s, "K": K, "rmse": e, "max_loss_log1p": loss})
    return pd.DataFrame(rows)


def prep():
    """Per-checkpoint training/test arrays (npz) and a checkpoint table; no model is fitted."""
    native = load_native(); reg = registry(); inp = pd.read_csv(PILOT / "tables/pilot_inputs.csv").set_index("sim_id")
    CKPT.mkdir(parents=True, exist_ok=True); T2.mkdir(parents=True, exist_ok=True)
    comp = compression_table(native); comp.to_csv(T2 / "compression_error_all_runs.csv", index=False, lineterminator="\n")
    rows = []
    for r, f, b, paid, task in checkpoints():
        train = [s for s in paid if native.get(s) is not None]
        test = [s for s in task["ids"][task["test"]] if native.get(s) is not None]
        K, kt = choose_K(train, native)
        logX = lambda ids: np.log(inp.loc[ids, ["P_W", "VX_m_s", "LS_radius_m", "ST_K"]].to_numpy(float))
        mu_x, sd_x = logX(train).mean(0), logX(train).std(0) + 1e-12
        z = lambda ids: (logX(ids) - mu_x) / sd_x
        # training points: bin means on the observed window + each run's exact native maximum
        tz, ts, ty, tw, tb = [], [], [], [], []
        Ytr = np.full((len(train), K), np.nan)
        for i, s in enumerate(train):
            g = bin_means(native[s], K)
            Ytr[i, g.b.to_numpy()] = g.y.to_numpy()
            tz.append(np.repeat(z([s]), len(g) + 1, 0)); ts.append(np.r_[g.s.to_numpy(), native[s]["s"][np.argmax(native[s]["y"])]])
            ty.append(np.r_[g.y.to_numpy(), native[s]["y"].max()]); tw.append(np.r_[np.zeros(len(g)), 1.0]); tb.append(np.r_[g.b.to_numpy(), -1])
        centers = (np.arange(K) + 0.5) * (S_MAX / K)
        te_obs = np.full((len(test), K), np.nan); te_plan = np.zeros((len(test), K), bool)
        for i, s in enumerate(test):
            g = bin_means(native[s], K); te_obs[i, g.b.to_numpy()] = g.y.to_numpy()
            te_plan[i] = centers <= reg.loc[s, "s_plan"] + 1e-12
        name = f"ckpt_r{r}_f{f}_B{b}"
        np.savez_compressed(CKPT / f"{name}.npz", train_ids=np.array(train), test_ids=np.array(test), z_train=z(train), z_test=z(test),
                            pts_z=np.vstack(tz), pts_s=np.concatenate(ts), pts_y=np.concatenate(ty), pts_is_max=np.concatenate(tw), pts_bin=np.concatenate(tb),
                            Ytr=Ytr, centers=centers, te_obs=te_obs, te_plan=te_plan, K=K, mu_x=mu_x, sd_x=sd_x)
        rows.append({"checkpoint": name, "repeat": r, "fold": f, "budget": b, "n_paid": len(paid), "n_train_trajectories": len(train),
                     "paid_without_trajectory": ";".join(s.split("_H-")[-1] for s in paid if native.get(s) is None), "n_test_trajectories": len(test),
                     "test_without_trajectory": ";".join(s.split("_H-")[-1] for s in task["ids"][task["test"]] if native.get(s) is None),
                     "K": K, "bin_width_s": S_MAX / K, "n_train_points": int(sum(len(x) for x in ty)),
                     **{f"median_rmse_K{k}": float(kt[kt.K == k].median_rmse.iloc[0]) for k in K_CANDIDATES}})
    ck = pd.DataFrame(rows); ck.to_csv(T2 / "checkpoints.csv", index=False, lineterminator="\n")
    print(ck[["checkpoint", "n_train_trajectories", "n_test_trajectories", "K", "n_train_points"]].to_string())
    return ck


def load_ckpt(name):
    d = np.load(CKPT / f"{name}.npz", allow_pickle=False)
    return {k: d[k] for k in d.files}


# ======================================================================================== scalar A GP reference
def scalar():
    """Refit the Week 19 ACTIVE E1 scalar GP (DepthGPR on log A, engine code) at each checkpoint; check equality with
    the pilot's saved predictions; save predictive mean and variances of log A for the test runs."""
    import src.week18_engine as E
    import src.week19_dev_pilot as P
    from threadpoolctl import threadpool_limits
    od = pd.read_csv(PILOT / "tables/oracle_response_diagnostics.csv")
    PRED.mkdir(parents=True, exist_ok=True)
    rows = []
    tasks = {(t["repeat"], t["fold"]): t for t in P.build_tasks()}
    pp = pd.read_csv(PILOT / "tables/paid_paths.csv")
    with threadpool_limits(limits=4):
        for r, f, b, paid, task in checkpoints():
            name = f"ckpt_r{r}_f{f}_B{b}"
            idx = {s: i for i, s in enumerate(task["ids"])}
            L = [idx[s] for s in paid]
            y_m = np.full(len(task["y"]), -1, int); y_m[L] = task["y"][L]
            d_m = np.full(len(task["y"]), np.nan); d_m[L] = task["A"][L]
            t0 = time.time()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fgp = E.fit_learner(("GPR_depth", "mlii"), {"X": task["X"], "y": y_m, "pool": task["pool"], "prior": task["prior"], "depth": d_m}, L, None, {"kernel": None, "b0": len(L)})
            ck = load_ckpt(name); test = [idx[s] for s in ck["test_ids"]]
            m, sd = fgp.gp.predict(fgp.xs.transform(np.log(task["X"][test])), return_std=True)
            mu = m * fgp.sd_t + fgp.mu_t
            noise = float(np.exp(fgp.gp.kernel_.theta[-1]) * fgp.sd_t ** 2)
            var_lat = np.maximum((sd * fgp.sd_t) ** 2 - noise, 1e-12)
            saved = od[(od.arm == "ACTIVE_E1_SHARED") & (od.repeat == r) & (od.fold == f) & (od.budget == b)].set_index("sim_id").predicted_log_depth
            diff = float(np.max(np.abs(saved.loc[ck["test_ids"]].to_numpy() - mu)))
            np.savez_compressed(PRED / f"scalar_{name}.npz", test_ids=ck["test_ids"], mu_logA=mu, var_latent=var_lat, var_noise=np.full(len(mu), noise), u_um=float(np.exp(fgp.u)))
            rows.append({"checkpoint": name, "fit_seconds": time.time() - t0, "max_abs_diff_vs_pilot_saved": diff, "noise_var_log": noise})
    t = pd.DataFrame(rows); t.to_csv(T2 / "scalar_reference_fits.csv", index=False, lineterminator="\n")
    print(t.describe().T)
    return t


# ======================================================================================== rank-3 functional baseline
RANK = 3


def als_rank(R, rank=RANK, iters=500, tol=1e-10, ridge=1e-6, seed=SEED):
    """Low-rank factorization of a residual matrix with missing entries (NaN), fitted on observed entries only.
    Initialisation: SVD of the fully observed rows (>= rank of them), else a fixed-seed random orthonormal basis.
    Vectorised alternating least squares (batched 3x3 normal equations)."""
    obs = np.isfinite(R); W = obs.astype(float); R0 = np.where(obs, R, 0.0); n, K = R.shape
    full = obs.all(1)
    if full.sum() >= rank:
        _, _, vt = np.linalg.svd(R[full], full_matrices=False); Phi = vt[:rank].T.copy(); init = "svd_full_rows"
    else:
        Phi = np.linalg.qr(np.random.default_rng(seed).normal(size=(K, rank)))[0]; init = "random_orthonormal"
    I = ridge * np.eye(rank); prev = np.inf; obj = np.nan
    for it in range(iters):
        G = np.einsum("ik,kp,kq->ipq", W, Phi, Phi) + I; C = np.linalg.solve(G, np.einsum("ik,kp->ip", R0, Phi)[..., None])[..., 0]
        G = np.einsum("ik,ip,iq->kpq", W, C, C) + I; Phi = np.linalg.solve(G, np.einsum("ik,ip->kp", R0, C)[..., None])[..., 0]
        obj = float(((R0 - (C @ Phi.T) * W) ** 2).sum())
        if abs(prev - obj) <= tol * max(1.0, obj):
            break
        prev = obj
    Q, Rr = np.linalg.qr(Phi); Phi = Q; C = C @ Rr.T                    # orthonormal basis, same fitted surface
    return Phi, C, {"init": init, "iterations": it + 1, "objective": obj}


def coef_gp(Z, c):
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
    mu, sd = c.mean(), c.std() + 1e-12
    k = ConstantKernel(1.0, (1e-3, 1e3)) * Matern(np.ones(Z.shape[1]), (1e-2, 1e2), nu=1.5) + WhiteKernel(1e-2, (1e-6, 1.0))
    gp = GaussianProcessRegressor(k, normalize_y=False, n_restarts_optimizer=0, random_state=0).fit(Z, (c - mu) / sd)
    return gp, mu, sd


def functional():
    PRED.mkdir(parents=True, exist_ok=True)
    rows = []
    ck_table = pd.read_csv(T2 / "checkpoints.csv")
    rng = np.random.default_rng(SEED)
    for name in ck_table.checkpoint:
        d = load_ckpt(name); t0 = time.time()
        Y = d["Ytr"]; supported = np.isfinite(Y).any(0)
        m = np.where(supported, np.nanmean(np.where(np.isfinite(Y), Y, np.nan), axis=0), np.nan)
        R = (Y - m)[:, supported]
        Phi_s, C, info = als_rank(R)
        Phi = np.zeros((Y.shape[1], RANK)); Phi[supported] = Phi_s
        res = R - C @ Phi_s.T; sig2 = float(np.nanmean(res ** 2))
        mus, varl = [], []
        hyp = []
        with warnings.catch_warnings(record=True) as wl:
            warnings.simplefilter("always")
            for k in range(RANK):
                gp, mu, sd = coef_gp(d["z_train"], C[:, k])
                mm, ss = gp.predict(d["z_test"], return_std=True)
                noise = float(np.exp(gp.kernel_.theta[-1]))
                mus.append(mm * sd + mu); varl.append(np.maximum(ss ** 2 - noise, 1e-12) * sd ** 2)
                hyp.append({"component": k, "kernel": str(gp.kernel_)[:200], "lml": float(gp.log_marginal_likelihood_value_)})
        mus, varl = np.array(mus).T, np.array(varl).T                   # (n_test, rank)
        mean = m[None, :] + mus @ Phi.T
        var_lat = varl @ (Phi ** 2).T
        summ = {k: [] for k in ("max_planned", "max_observed", "argmax_s_observed", "exceed_s_observed")}
        for i in range(len(mus)):                                          # posterior trajectories (latent; residual noise excluded)
            draws = mus[i] + rng.standard_normal((N_SAMPLES, RANK)) * np.sqrt(varl[i])
            traj = m[None, :] + draws @ Phi.T
            plan = d["te_plan"][i] & supported; obs = np.isfinite(d["te_obs"][i]) & supported
            for k, v in sample_summaries(traj, plan, obs, d["centers"], S_MAX / int(d["K"])).items():
                summ[k].append(v)
        np.savez_compressed(PRED / f"functional_{name}.npz", test_ids=d["test_ids"], mean=mean, var_latent=var_lat, var_noise=np.full(mean.shape, sig2),
                            supported=supported, **{k: np.array(v) for k, v in summ.items()})
        rows.append({"checkpoint": name, "fit_seconds": time.time() - t0, "K": int(d["K"]), "n_supported_bins": int(supported.sum()), "als_init": info["init"],
                     "als_iterations": info["iterations"], "residual_var": sig2, "coef_gp_fits": RANK,
                     "warnings": " | ".join(sorted({str(w.message)[:80] for w in wl}))[:300], "hyper": json.dumps(hyp)[:900]})
        print(name, f"{time.time() - t0:.1f}s", info, flush=True)
    t = pd.DataFrame(rows); t.to_csv(T2 / "functional_fits.csv", index=False, lineterminator="\n")
    return t


# ======================================================================================== Track 2 manifest (before any Track 2 fit)
HYPOTHESES_T2 = {
    "T2-H1_inputs_help": "At every budget (B16/B40/B80) both temporal models (rank-3 functional and separable SVGP) have lower simulation-weighted trajectory RMSE (log1p depth, observed bins) than the input-free training-mean trajectory. Basis: depth trajectories depend strongly on scan speed (slow scans near 300 um, fast scans near 110 um). Falsified if either model is not lower at any budget.",
    "T2-H2_learning": "Trajectory RMSE of both temporal models decreases from B16 to B80 (mean over the ten folds). Falsified otherwise.",
    "T2-H3_max_depth": "For the maximum depth A of held-out runs (like-for-like runs, observed window = planned horizon), the scalar A GP has a lower median absolute error (um) than both temporal models at B40 and at B80. Basis: the scalar model targets A directly, while bin means lose 0.004-0.02 log1p units at the native peak (measured compression gap). Falsified if a temporal model is lower at B40 or B80.",
    "T2-H4_short_events": "The temporal models' underestimation of A (relative to the native maximum) is larger for runs whose near-peak episode (depth >= 95 % of A) is shorter than one bin width than for longer episodes. Basis: bin means smooth sub-bin peaks by construction.",
    "T2-H5_calibration": "No numerical expectation. 50 % and 90 % pointwise predictive intervals are evaluated on observed bins, together with interval coverage for A.",
    "T2-H6_model_ranking": "No directional expectation between the functional baseline and the separable SVGP.",
    "T2-H7_matched_pair_fast_scans": "No assumption either way. Evaluated: (a) whether the observed trajectories of the matched pair (H-b302fc6cbd vs H-b7e3ed2e12) differ beyond each model's predictive uncertainty; (b) whether the models' predictions for the two runs differ; (c) descriptively, whether trajectory features (predicted A, predicted time above u_ref) rank held-out labels within fast scans (VX > 0.85; exploratory). Trajectory accuracy and canonical-label information are reported separately; no classifier is built.",
    "T2-H8_truncated": "For the six runs whose recording ends before the planned horizon, planned-horizon predicted maxima and observed-window maxima are reported separately as different estimands. No expectation.",
}


def write_manifest_t2():
    import ast
    import hashlib
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
    root = Path(__file__).resolve().parents[1]
    ck = pd.read_csv(T2 / "checkpoints.csv")
    from src.week20_track2_data import RESOLUTION_RULE, TAU
    src = (root / "src/week20_track2_svgp.py").read_text(encoding="utf-8")
    svgp_cfg = ast.literal_eval(src.split("CONFIG = ", 1)[1].split("\ntorch.set_num_threads", 1)[0])
    man = {"status": "POST-HOC DEV RESEARCH — temporal-GP development; not confirmatory; C3 reserved",
           "written_utc": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "written_before_any_track2_fit": True,
           "data": {"population": "NEW, 135 runs with an aligned bounds/time record (H-e7dbd8e5ce has none: a paid query without a trajectory, absent from test scoring)",
                    "checkpoints": "repeats 1-2 x folds 1-5 x budgets 16/40/80 = 30; training = Week 19 pilot shared label-blind paid prefixes (tables/paid_paths.csv); complete runs held out",
                    "target": "y = log(1 + depth_um) on s = t / derived_exit; depth = 0 on rows without melt; native monitor time from iter.dat -> time.dat",
                    "planned_horizon": "s_plan = min(TE, 0.9 exit) / exit (pre-query scheduled settings)",
                    "observed_window": "s_obs = min(recording end, 0.9 exit) / exit (scoring support only; no stretching or tail filling)",
                    "compression": "per-bin means on a uniform s-grid of K bins over [0, 0.9]; each training run also contributes its exact native maximum (s, y) to the separable GP",
                    "resolution_rule": RESOLUTION_RULE, "tau": TAU, "K_selected": sorted(int(k) for k in ck.K.unique())},
           "models": {"scalar_A_GP": "Week 19 ACTIVE E1 regression (src.week18_engine DepthGPR on log A, ML-II, one start), refitted on the same paid prefixes; must equal the pilot's saved predictions",
                      "mean_trajectory": "input-free training mean per bin (no fit)",
                      "functional_rank3": "per-bin training mean + rank-3 basis from alternating least squares on observed training entries only (no imputation as data); three coefficient GPs (sklearn, ConstantKernel x Matern-3/2 ARD + white noise, ML-II, one start) on training-standardized log inputs; global residual variance",
                      "separable_SVGP": {"library": "gpytorch 1.15.1 / torch 2.13.0+cpu in .venv", "kernel": "sigma^2 Matern32_ARD(z) x Matern32(s)", **svgp_cfg,
                                         "why_not_kronecker": "training design is a staircase (each run covers [0, s_obs]); Kronecker identities need a complete grid with common noise; validated on a complete synthetic grid only"}},
           "uncertainty": "maximum, argmax timing and exceedance distributions from 2000 posterior latent trajectories per held-out run (never the maximum of the posterior mean); scalar A from its predictive lognormal",
           "evaluation": ["simulation-weighted trajectory RMSE (observed bins) and median", "50 %/90 % pointwise interval coverage and width (latent + noise variance)",
                          "A error (um, log1p) vs native maximum and vs bin-mean maximum; 90 % interval coverage of A",
                          "argmax timing error (us) and time-above-u_ref error (us) on the observed window", "short-event analysis: near-peak (>= 95 % of A) episode shorter than one bin",
                          "runtime, peak memory, SVGP ELBO trace, SVGP vs exact on a controlled example, M=400 vs M=800 at one checkpoint",
                          "representative best / median / worst held-out runs and the named runs (matched pair, late negative)",
                          "planned-horizon vs observed-window quantities reported separately for the six truncated runs"],
           "hypotheses": HYPOTHESES_T2,
           "fit_accounting": {"scalar_refits": 30, "functional_coefficient_GPs": 90, "separable_SVGP": 30, "validation_SVGP": 2, "approximation_fidelity_SVGP": 1,
                              "total_temporal_functional": 123, "cap": 160},
           "resource_limits": {"threads": 4, "memory_gib": 8, "total_hours_both_tracks": 8},
           "code_sha256": {c: sha(root / c) for c in ["src/week20_track2_data.py", "src/week20_track2_models.py", "src/week20_track2_svgp.py", "src/week20_track2_common.py"]}}
    (T2 / "manifest_track2.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    L = ["# Track 2 hypotheses and evaluation criteria (frozen before any Track 2 fit)", "", f"*Written {man['written_utc']}; methods in `manifest_track2.json`.*", "",
         "**Status.** Post-hoc DEV development; not confirmatory. Numerical expectations are given only where measured evidence supports them.", "", "## Hypotheses", ""]
    L += [f"- **{k}.** {v}" for k, v in HYPOTHESES_T2.items()]
    L += ["", "## Evaluation", ""] + [f"- {e};" for e in man["evaluation"][:-1]] + [f"- {man['evaluation'][-1]}."]
    (T2 / "HYPOTHESES_TRACK2.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("manifest_track2", sha(T2 / "manifest_track2.json"))
    return man


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step in ("prep", "all"):
        prep()
    if step in ("scalar", "all"):
        scalar()
    if step in ("functional", "all"):
        functional()
    if step == "manifest":
        write_manifest_t2()
