"""Temporal repair sub-study — evaluation (definitions unchanged from Week 20 Track 2) and freeze manifest.

Models compared on the same 30 checkpoints (NEW DEV repeats 1-2, B16/B40/B80, Week 19 shared paid paths):
  controls: training-mean trajectory, scalar A GP (unchanged), frozen functional (Week 20), frozen SVGP (2000 it),
            SVGP 6000 it (T2-PS1, five repeat-1 B40 checkpoints only);
  repaired: functional_ppca (30), svgp_ngd_M400 (30), svgp_ngd_M800 (the ten B40 checkpoints; inducing sensitivity).
Trajectory metrics on observed bins; A on like-for-like runs (recording reaches the planned horizon); planned vs
observed windows kept apart; no tail filling.  Curve accuracy is not canonical-label success.

Steps: python -m src.jdl_temporal_eval manifest | evaluate
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TR = ROOT / "outputs" / "joint_depth_label_development" / "temporal_repair"
W20 = ROOT / "outputs" / "week20_active_temporal_development"
B40 = [f"ckpt_r{r}_f{f}_B40" for r in (1, 2) for f in range(1, 6)]
MODEL_TAGS = ("mean_trajectory", "functional", "functional_ppca", "svgp", "svgp_it6000", "svgp_ngd_M400", "svgp_ngd_M800")
CODE = ["src/jdl_temporal_functional.py", "src/jdl_temporal_svgp.py", "src/jdl_temporal_eval.py", "src/week20_track2_models.py", "src/week20_track2_svgp.py",
        "src/week20_track2_common.py", "src/week20_track2_data.py", "src/week20_track2_eval.py"]


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


HYP = {
    "TR-H1_svgp_convergence_rmse": "The converged SVGP (svgp_ngd_M400) has lower mean trajectory RMSE than the frozen 2000-iteration SVGP at every budget. Direction from Week 20 T2-PS1 (6000 iterations: -23 % on five checkpoints). Magnitude not committed.",
    "TR-H2_svgp_convergence_A": "The converged SVGP has lower median |A error| than the frozen SVGP at B40 and B80, but stays above the scalar A GP. Direction from T2-PS1 (A error 60 -> 45 um, scalar 5.0 um on the same rows).",
    "TR-H3_inducing_sensitivity": "Under equal convergence effort, the RMS difference of the predictive mean between M=400 and M=800 at B40 is smaller than under the frozen protocol (0.167 at ckpt_r1_f1_B40). Direction only.",
    "TR-H4_functional_conditioning": "The PPCA functional model has no exploding coefficients (max |posterior-mean coefficient| below 10 at every checkpoint) and lower mean trajectory RMSE than the frozen functional model at every budget. Basis: controlled staircase validation and the Week 20 diagnosis.",
    "TR-H5_model_ranking": "PPCA functional vs converged SVGP: no directional expectation.",
    "TR-H6_A_gap": "Neither repaired temporal model reaches the scalar A GP's median |A error| at B40 or B80 (Week 20: about 10x gap).",
    "TR-H7_calibration": "No numerical expectation for 50 %/90 % pointwise coverage; reported with widths.",
}


def write_manifest_no_torch():
    ck = pd.read_csv(W20 / "track2/checkpoints.csv")
    cache = W20 / "_cache/track2"
    proto_src = (ROOT / "src/jdl_temporal_svgp.py").read_text(encoding="utf-8")
    man = {"study": "temporal repair sub-study (separate from Stage M; authorized irrespective of the Stage M gate)",
           "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "status": "FROZEN BEFORE ANY NEW TEMPORAL FIT ON STUDY DATA",
           "checkpoints": ck.checkpoint.tolist(), "checkpoint_files_sha256": {c: sha256(cache / f"checkpoints/{c}.npz") for c in ck.checkpoint},
           "native_trajectories_sha256": sha256(cache / "native_trajectories.pkl.gz"),
           "inputs_unchanged": "Week 20 Track 2 checkpoints: NEW DEV repeats 1-2, ten folds, B16/40/80, Week 19 shared label-blind paid prefixes; K = 360 bin means from the training-only rule; native maxima as extra training points; planned horizon from scheduled settings; observed window = recording end; no stretching or tail filling",
           "repairs": {"svgp": "NGD (lr 0.1) on the natural variational distribution + Adam (lr 0.01) on hyperparameters and inducing locations; lr halved at 5000 and 10000; stop on training evidence only (probe ELBO relative change <= 5e-4 and probe-mean RMS change <= 5e-3 for 3 consecutive 250-iteration checks, 1000 <= iterations <= 20000); identical protocol for M = 400 (30 checkpoints) and M = 800 (the ten B40 checkpoints)",
                       "functional": "rank-3 probabilistic PCA with missing data (EM; coefficient prior N(0, I), exact per-run posterior on observed bins; EM tol 1e-9 relative log likelihood, max 3000 iterations), orthogonal rotation, then one GP per coefficient with per-run noise = that run's coefficient posterior variance (sklearn, ConstantKernel x Matern-3/2 ARD + White, alpha = posterior variance)"},
           "controls_unchanged": ["training-mean trajectory", "scalar A GP (Week 20 refit)", "frozen functional", "frozen SVGP 2000 it", "SVGP 6000 it (T2-PS1)"],
           "validation_before_freeze": {"svgp_ngd": json.loads((TR / "svgp_ngd_validation.json").read_text()), "functional_ppca": json.loads((TR / "functional_ppca_validation.json").read_text())},
           "fit_counts": {"svgp_ngd_M400": 30, "svgp_ngd_M800": 10, "functional_ppca_em": 30, "functional_ppca_coefficient_gps": 90, "total_temporal_fits": 160},
           "threads": "SVGP: 3 torch threads; functional: 1 BLAS thread; at most 4 in total",
           "metrics": "unchanged Week 20 Track 2 definitions: trajectory RMSE/MAE on observed bins, 50/90 % pointwise coverage and width (latent + noise), A = median of posterior maxima over the planned horizon (like-for-like runs), A 90 % interval, signed and absolute A error, argmax timing error, time above u_ref error, P(max > u_ref) Brier vs the event; plus conditioning, convergence, inducing sensitivity and runtime",
           "hypotheses": HYP, "code_sha256": {c: sha256(ROOT / c) for c in CODE}}
    TR.mkdir(parents=True, exist_ok=True)
    (TR / "TEMPORAL_MANIFEST.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    print("temporal manifest written", sha256(TR / "TEMPORAL_MANIFEST.json"))


def _load_pred(tag, ck):
    from src.week20_track2_models import PRED
    p = PRED / f"{tag}_{ck}.npz"
    return dict(np.load(p, allow_pickle=False)) if p.exists() else None


def evaluate():
    from scipy.special import ndtr  # noqa: F401
    from src.week20_track2_common import UREF_LOG1P
    from src.week20_track2_data import PILOT, S_MAX, load_native, registry
    from src.week20_track2_eval import Z50, Z90, native_features
    from src.week20_track2_models import load_ckpt
    native = load_native(); reg = registry(); nf = native_features(native, reg)
    inp = pd.read_csv(PILOT / "tables/pilot_inputs.csv").set_index("sim_id")
    ck = pd.read_csv(W20 / "track2/checkpoints.csv")
    rows = []
    for c in ck.itertuples():
        d = load_ckpt(c.checkpoint); K = int(d["K"]); Y = d["Ytr"]; sup0 = np.isfinite(Y).any(0)
        m0 = np.where(sup0, np.nanmean(np.where(np.isfinite(Y), Y, np.nan), axis=0), np.nan)
        v0 = np.where(sup0, np.nanvar(np.where(np.isfinite(Y), Y, np.nan), axis=0), np.nan)
        n_te = len(d["test_ids"])
        preds = {"mean_trajectory": {"mean": np.repeat(m0[None], n_te, 0), "var_latent": np.repeat(v0[None], n_te, 0), "var_noise": np.zeros((n_te, K)), "supported": sup0}}
        for tag in MODEL_TAGS[1:]:
            z = _load_pred(tag, c.checkpoint)
            if z is not None:
                preds[tag] = z
        sc = _load_pred("scalar", c.checkpoint)
        for i, sid in enumerate(d["test_ids"]):
            f = nf.loc[sid]; obs = np.isfinite(d["te_obs"][i]); trunc = bool(reg.loc[sid, "truncated_before_plan"])
            A = float(inp.loc[sid, "A_um"])
            base = {"checkpoint": c.checkpoint, "repeat": c.repeat, "fold": c.fold, "budget": c.budget, "sim_id": sid, "truncated_before_plan": trunc, "A_um": A,
                    "has_keyhole": int(inp.loc[sid, "has_keyhole"]), "VX_m_s": float(inp.loc[sid, "VX_m_s"])}
            mu, vl, vn = sc["mu_logA"][i], sc["var_latent"][i], sc["var_noise"][i]
            q = np.exp(mu + np.array([-Z90, 0.0, Z90]) * np.sqrt(vl + vn))
            rows.append({**base, "model": "scalar_A_GP", "pred_A_um": float(q[1]), "A_lo90": float(q[0]), "A_hi90": float(q[2])})
            for tag, p in preds.items():
                sup = p["supported"].astype(bool); o = obs & sup
                mean, sd = p["mean"][i], np.sqrt(p["var_latent"][i] + p["var_noise"][i])
                e = mean[o] - d["te_obs"][i][o]
                row = {**base, "model": tag, "n_unsupported_obs_bins": int((obs & ~sup).sum()), "traj_rmse": float(np.sqrt(np.mean(e ** 2))) if o.any() else np.nan,
                       "cov50": float(np.mean(np.abs(e) <= Z50 * sd[o])) if o.any() else np.nan, "cov90": float(np.mean(np.abs(e) <= Z90 * sd[o])) if o.any() else np.nan,
                       "width90": float(np.mean(2 * Z90 * sd[o])) if o.any() else np.nan}
                if "max_planned" in p:
                    mp = np.expm1(p["max_planned"][i].astype(float))
                    row.update({"pred_A_um": float(np.median(mp)), "A_lo90": float(np.quantile(mp, .05)), "A_hi90": float(np.quantile(mp, .95)),
                                "p_max_exceeds_uref": float(np.mean(p["max_planned"][i] > UREF_LOG1P)),
                                "argmax_err_us": float(abs(np.median(p["argmax_s_observed"][i]) - f.argmax_s) * f.exit_us),
                                "exceed_abs_err_us": float(abs(np.mean(p["exceed_s_observed"][i]) * f.exit_us - f.exceed_us_native))})
                rows.append(row)
    ev = pd.DataFrame(rows)
    ev["A_abs_err_um"] = (ev.pred_A_um - ev.A_um).abs(); ev["A_signed_err_um"] = ev.pred_A_um - ev.A_um
    ev["A_in_90"] = np.where(ev.pred_A_um.notna(), (ev.A_um >= ev.A_lo90) & (ev.A_um <= ev.A_hi90), np.nan)
    ev["A_event"] = (ev.A_um > np.expm1(UREF_LOG1P)).astype(int)
    ev.to_csv(TR / "evaluation_per_run.csv.gz", index=False, lineterminator="\n", compression={"method": "gzip", "mtime": 0})
    like = ev[~ev.truncated_before_plan]
    s1 = ev[ev.model.isin(MODEL_TAGS)].groupby(["model", "budget"]).agg(rows=("sim_id", "size"), checkpoints=("checkpoint", "nunique"), traj_rmse_mean=("traj_rmse", "mean"),
                                                                       traj_rmse_median=("traj_rmse", "median"), cov50=("cov50", "mean"), cov90=("cov90", "mean"), width90=("width90", "mean")).reset_index()
    s2 = like[like.pred_A_um.notna()].assign(brier=lambda x: (x.p_max_exceeds_uref - x.A_event) ** 2).groupby(["model", "budget"]).agg(
        rows=("sim_id", "size"), A_abs_err_median_um=("A_abs_err_um", "median"), A_signed_err_median_um=("A_signed_err_um", "median"), A_in_90=("A_in_90", "mean"),
        argmax_err_median_us=("argmax_err_us", "median"), exceed_abs_err_median_us=("exceed_abs_err_us", "median"), brier_exceed=("brier", "mean")).reset_index()
    s1.to_csv(TR / "summary_trajectory.csv", index=False, lineterminator="\n"); s2.to_csv(TR / "summary_A_timing_exceedance.csv", index=False, lineterminator="\n")
    # paired comparisons on identical rows (cluster bootstrap over simulations)
    rng = np.random.default_rng(0)
    pairs = [("svgp_ngd_M400", "svgp", "traj_rmse", ev), ("svgp_ngd_M400", "svgp", "A_abs_err_um", like), ("functional_ppca", "functional", "traj_rmse", ev),
             ("functional_ppca", "svgp_ngd_M400", "traj_rmse", ev), ("functional_ppca", "svgp_ngd_M400", "A_abs_err_um", like), ("svgp_ngd_M400", "mean_trajectory", "traj_rmse", ev),
             ("functional_ppca", "mean_trajectory", "traj_rmse", ev), ("svgp_ngd_M400", "scalar_A_GP", "A_abs_err_um", like), ("functional_ppca", "scalar_A_GP", "A_abs_err_um", like)]
    prs = []
    for a, b, metric, src in pairs:
        for bud in (16, 40, 80):
            t = src[(src.budget == bud) & src.model.isin([a, b])].pivot_table(index=["sim_id", "repeat"], columns="model", values=metric).dropna()
            if a not in t or b not in t or not len(t):
                continue
            stat = (lambda x: float(np.median(x[a]) - np.median(x[b]))) if metric == "A_abs_err_um" else (lambda x: float((x[a] - x[b]).mean()))
            sims = t.index.get_level_values("sim_id").unique().to_numpy()
            draws = []
            for _ in range(2000):
                pick = rng.choice(sims, len(sims))
                draws.append(stat(pd.concat([t.xs(s, level="sim_id") for s in pick])))
            prs.append({"model": a, "reference": b, "metric": metric, "budget": bud, "rows": len(t), "estimate": stat(t),
                        "ci95_lo": float(np.quantile(draws, .025)), "ci95_hi": float(np.quantile(draws, .975)),
                        "statistic": "difference of medians" if metric == "A_abs_err_um" else "mean paired difference"})
    pd.DataFrame(prs).to_csv(TR / "paired_differences.csv", index=False, lineterminator="\n")
    # inducing sensitivity under equal convergence effort (B40) and under the frozen protocol (one checkpoint)
    ind = []
    for c in B40:
        a, b = _load_pred("svgp_ngd_M400", c), _load_pred("svgp_ngd_M800", c)
        d = load_ckpt(c); obs = np.isfinite(d["te_obs"])
        if a is None or b is None:
            continue
        ind.append({"checkpoint": c, "protocol": "converged NGD (equal effort)", "rms_mean_difference_M400_vs_M800": float(np.sqrt(np.mean((a["mean"][obs] - b["mean"][obs]) ** 2))),
                    "median_abs_diff_pred_A_um": float(np.median(np.abs(np.expm1(np.median(a["max_planned"].astype(float), 1)) - np.expm1(np.median(b["max_planned"].astype(float), 1))))),
                    "rmse_M400": float(np.sqrt(np.mean((a["mean"][obs] - d["te_obs"][obs]) ** 2))), "rmse_M800": float(np.sqrt(np.mean((b["mean"][obs] - d["te_obs"][obs]) ** 2)))})
    fr = pd.read_csv(W20 / "track2/svgp_inducing_fidelity.csv")
    for r in fr.itertuples():
        ind.append({"checkpoint": r.checkpoint, "protocol": "frozen Week 20 (2000 Adam iterations)", "rms_mean_difference_M400_vs_M800": r.rms_mean_difference_M400_vs_M800,
                    "median_abs_diff_pred_A_um": r.median_abs_diff_pred_A_um, "rmse_M400": r.rmse_M400, "rmse_M800": r.rmse_M800})
    pd.DataFrame(ind).to_csv(TR / "inducing_sensitivity.csv", index=False, lineterminator="\n")
    # convergence, conditioning and runtime
    sv = [json.loads(l) for l in (TR / "svgp_ngd_fits.jsonl").read_text().splitlines() if l.strip()] if (TR / "svgp_ngd_fits.jsonl").exists() else []
    fu = [json.loads(l) for l in (TR / "functional_ppca_fits.jsonl").read_text().splitlines() if l.strip()] if (TR / "functional_ppca_fits.jsonl").exists() else []
    cv = pd.DataFrame([{k: r[k] for k in ("checkpoint", "tag", "status", "iterations", "fit_seconds", "peak_memory_bytes", "lengthscale_s", "noise")} for r in sv])
    cf = pd.DataFrame([{k: r[k] for k in ("checkpoint", "tag", "em_status", "em_iterations", "fit_seconds", "max_abs_coefficient", "max_coefficient_posterior_sd", "residual_var")} for r in fu])
    old = pd.read_csv(W20 / "track2/POSTHOC_functional_failure.csv")[["checkpoint", "max_abs_coefficient"]].rename(columns={"max_abs_coefficient": "frozen_ALS_max_abs_coefficient"})
    if len(cf):
        cf = cf.merge(old, on="checkpoint", how="left")
    cv.to_csv(TR / "svgp_ngd_convergence.csv", index=False, lineterminator="\n"); cf.to_csv(TR / "functional_ppca_conditioning.csv", index=False, lineterminator="\n")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(s1.round(4).to_string()); print(s2.round(3).to_string()); print(pd.DataFrame(prs).round(4).to_string()); print(pd.DataFrame(ind).round(4).to_string())
    if len(cv):
        print(cv.groupby("tag").agg(fits=("status", "size"), converged=("status", lambda s: int((s == "converged").sum())), it_median=("iterations", "median"),
                                    it_max=("iterations", "max"), sec_median=("fit_seconds", "median"), sec_total=("fit_seconds", "sum")).to_string())
    if len(cf):
        print(cf[["checkpoint", "em_status", "em_iterations", "max_abs_coefficient", "frozen_ALS_max_abs_coefficient", "max_coefficient_posterior_sd"]].round(3).to_string())
    return ev


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "evaluate"
    if step == "manifest":
        write_manifest_no_torch()
    else:
        evaluate()
