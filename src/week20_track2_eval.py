"""Week 20 Track 2 evaluation: trajectory accuracy, calibration, maximum depth, timing, exceedance, short events,
the matched pair and fast scans, runtime and approximation fidelity.  Reads saved predictions; fits nothing.
Decision rules: track2/EVALUATION_RULES_T2.md (written before any held-out evaluation).

Step: python -m src.week20_track2_eval
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from src.week20_track2_common import UREF_LOG1P
from src.week20_track2_data import PILOT, S_MAX, T2, bin_means, load_native, registry
from src.week20_track2_models import PRED, load_ckpt

MODELS = ("mean_trajectory", "functional", "svgp")
TEMPORAL = ("functional", "svgp")
UREF = float(np.expm1(UREF_LOG1P))
NAMED = {"H-b302fc6cbd": "matched pair, recorded negative (G5)", "H-b7e3ed2e12": "matched pair, recorded positive (G4)", "H-f4fc937e86": "late negative"}
Z90, Z50 = 1.6448536269514722, 0.6744897501960817
PAIR = ("P-387p361336282_VX-0p960187357846_LS-4p72484046084e-05_ST-390p52586458_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p02414509376e-06_H-b302fc6cbd",
        "P-380p041479483_VX-0p952843483906_LS-4p56527036263e-05_ST-376p177191048_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p0628678104e-06_H-b7e3ed2e12")
N_BOOT, BOOT_SEED, MIN_SHORT_RUNS = 2000, 0, 5


def native_features(native, reg):
    rows = []
    for s, tr in native.items():
        if tr is None:
            continue
        r = reg.loc[s]; ex_us = r.derived_exit_ms * 1e3
        y = tr["y"]; sv = tr["s"]; i = int(np.argmax(y)); A = float(np.expm1(y[i]))
        ds = float(np.median(np.diff(sv))) if len(sv) > 1 else np.nan
        near = np.expm1(y) >= 0.95 * A
        best = cur = 0
        for v in near:
            cur = cur + 1 if v else 0; best = max(best, cur)
        rows.append({"sim_id": s, "A_native_um": A, "argmax_s": float(sv[i]), "exceed_us_native": float((y > UREF_LOG1P).sum() * ds * ex_us),
                     "near_peak_episode_us": float(best * ds * ex_us), "exit_us": ex_us})
    return pd.DataFrame(rows).set_index("sim_id")


def evaluate():
    native = load_native(); reg = registry(); nf = native_features(native, reg)
    inp = pd.read_csv(PILOT / "tables/pilot_inputs.csv").set_index("sim_id")
    ck = pd.read_csv(T2 / "checkpoints.csv")
    rows = []
    for c in ck.itertuples():
        d = load_ckpt(c.checkpoint); K = int(d["K"]); width = S_MAX / K
        Y = d["Ytr"]; train_support = np.isfinite(Y).any(0)
        m0 = np.where(train_support, np.nanmean(np.where(np.isfinite(Y), Y, np.nan), axis=0), np.nan)
        v0 = np.where(train_support, np.nanvar(np.where(np.isfinite(Y), Y, np.nan), axis=0), np.nan)
        n_te = len(d["test_ids"])
        preds = {"mean_trajectory": {"mean": np.repeat(m0[None, :], n_te, 0), "var_latent": np.repeat(v0[None, :], n_te, 0),
                                     "var_noise": np.zeros((n_te, K)), "supported": train_support}}
        for mname in TEMPORAL:
            p = PRED / f"{mname}_{c.checkpoint}.npz"
            if p.exists():
                preds[mname] = dict(np.load(p, allow_pickle=False))
        sc = dict(np.load(PRED / f"scalar_{c.checkpoint}.npz", allow_pickle=False))
        for i, sid in enumerate(d["test_ids"]):
            r = reg.loc[sid]; f = nf.loc[sid]; obs = np.isfinite(d["te_obs"][i])
            trunc = bool(r.truncated_before_plan); bw_us = width * f.exit_us
            A = float(inp.loc[sid, "A_um"])
            base = {"checkpoint": c.checkpoint, "repeat": c.repeat, "fold": c.fold, "budget": c.budget, "sim_id": sid, "H": "H-" + sid.split("_H-")[-1],
                    "has_keyhole": int(inp.loc[sid, "has_keyhole"]), "VX_m_s": float(inp.loc[sid, "VX_m_s"]), "truncated_before_plan": trunc,
                    "A_um": A, "A_native_um": float(f.A_native_um), "A_exceeds_uref": int(A > UREF), "binmean_max_um": float(np.expm1(np.nanmax(d["te_obs"][i]))),
                    "near_peak_episode_us": float(f.near_peak_episode_us), "bin_width_us": bw_us, "short_event": bool(f.near_peak_episode_us < bw_us)}
            mu, vl, vn = sc["mu_logA"][i], sc["var_latent"][i], sc["var_noise"][i]
            q = np.exp(mu + np.array([-Z90, 0.0, Z90]) * np.sqrt(vl + vn))
            rows.append({**base, "model": "scalar_A_GP", "pred_A_um": float(q[1]), "A_lo90": float(q[0]), "A_hi90": float(q[2]),
                         "p_max_exceeds_uref": float(norm.sf((np.log(UREF) - mu) / np.sqrt(vl + vn)))})
            for mname, p in preds.items():
                sup = p["supported"].astype(bool); o = obs & sup
                mean, sd = p["mean"][i], np.sqrt(p["var_latent"][i] + p["var_noise"][i])
                e = mean[o] - d["te_obs"][i][o]
                row = {**base, "model": mname, "n_obs_bins": int(o.sum()), "n_unsupported_obs_bins": int((obs & ~sup).sum()),
                       "traj_rmse": float(np.sqrt(np.mean(e ** 2))) if o.any() else np.nan, "traj_mae": float(np.mean(np.abs(e))) if o.any() else np.nan,
                       "cov50": float(np.mean(np.abs(e) <= Z50 * sd[o])) if o.any() else np.nan, "cov90": float(np.mean(np.abs(e) <= Z90 * sd[o])) if o.any() else np.nan,
                       "width90": float(np.mean(2 * Z90 * sd[o])) if o.any() else np.nan}
                if "max_planned" in p:
                    mp = np.expm1(p["max_planned"][i].astype(float)); mo = np.expm1(p["max_observed"][i].astype(float))
                    row.update({"pred_A_um": float(np.median(mp)), "A_lo90": float(np.quantile(mp, .05)), "A_hi90": float(np.quantile(mp, .95)),
                                "p_max_exceeds_uref": float(np.mean(p["max_planned"][i] > UREF_LOG1P)),
                                "pred_max_observed_window_um": float(np.median(mo)),
                                "argmax_err_us": float(abs(np.median(p["argmax_s_observed"][i]) - f.argmax_s) * f.exit_us),
                                "pred_exceed_us": float(np.mean(p["exceed_s_observed"][i]) * f.exit_us), "obs_exceed_us": float(f.exceed_us_native),
                                "pred_mean_max_um": float(np.expm1(np.nanmax(np.where(d["te_plan"][i] & sup, mean, -np.inf))))})
                rows.append(row)
    ev = pd.DataFrame(rows)
    ev["A_abs_err_um"] = (ev.pred_A_um - ev.A_um).abs(); ev["A_signed_err_um"] = ev.pred_A_um - ev.A_um
    ev["A_log1p_err"] = np.log1p(ev.pred_A_um) - np.log1p(ev.A_um)
    ev["A_in_90"] = np.where(ev.pred_A_um.notna(), (ev.A_um >= ev.A_lo90) & (ev.A_um <= ev.A_hi90), np.nan)
    ev["binmax_abs_err_um"] = (ev.pred_A_um - ev.binmean_max_um).abs()
    ev["exceed_abs_err_us"] = (ev.pred_exceed_us - ev.obs_exceed_us).abs()
    ev.to_csv(T2 / "evaluation_per_run.csv.gz", index=False, lineterminator="\n")
    return ev


def summarise(ev):
    like = ev[~ev.truncated_before_plan]
    s1 = ev[ev.model.isin(MODELS)].groupby(["model", "budget"]).agg(rows=("sim_id", "size"), traj_rmse_mean=("traj_rmse", "mean"), traj_rmse_median=("traj_rmse", "median"),
                                                                     cov50=("cov50", "mean"), cov90=("cov90", "mean"), width90=("width90", "mean"),
                                                                     unsupported_bins=("n_unsupported_obs_bins", "sum")).reset_index()
    fm = (ev[ev.model.isin(MODELS)].groupby(["model", "budget", "checkpoint"]).traj_rmse.mean().groupby(["model", "budget"])
          .agg(traj_rmse_fold_mean="mean", traj_rmse_fold_sd="std", checkpoints="size").reset_index())
    s1 = s1.merge(fm, on=["model", "budget"])
    s2 = like[like.pred_A_um.notna()].groupby(["model", "budget"]).agg(rows=("sim_id", "size"), A_abs_err_median_um=("A_abs_err_um", "median"), A_abs_err_mean_um=("A_abs_err_um", "mean"),
                                                                       A_signed_err_median_um=("A_signed_err_um", "median"), A_log1p_err_median=("A_log1p_err", "median"),
                                                                       A_in_90=("A_in_90", "mean"), binmax_abs_err_median_um=("binmax_abs_err_um", "median"),
                                                                       argmax_err_median_us=("argmax_err_us", "median"), exceed_abs_err_median_us=("exceed_abs_err_us", "median"),
                                                                       obs_exceed_median_us=("obs_exceed_us", "median")).reset_index()
    b = like[like.pred_A_um.notna()].assign(brier=lambda x: (x.p_max_exceeds_uref - x.A_exceeds_uref) ** 2)
    s2 = s2.merge(b.groupby(["model", "budget"]).brier.mean().rename("brier_p_max_exceeds_uref_vs_event").reset_index(), on=["model", "budget"])
    sh = like[like.model.isin([*TEMPORAL, "scalar_A_GP"]) & like.pred_A_um.notna()].groupby(["model", "budget", "short_event"]).agg(
        rows=("sim_id", "size"), runs=("sim_id", "nunique"), A_log1p_err_median=("A_log1p_err", "median"), A_signed_err_median_um=("A_signed_err_um", "median"),
        A_abs_err_median_um=("A_abs_err_um", "median")).reset_index()
    tr = ev[ev.truncated_before_plan & ev.pred_A_um.notna()][["model", "budget", "repeat", "H", "A_um", "pred_A_um", "pred_max_observed_window_um", "A_lo90", "A_hi90"]]
    s1.to_csv(T2 / "summary_trajectory.csv", index=False, lineterminator="\n"); s2.to_csv(T2 / "summary_max_timing_exceedance.csv", index=False, lineterminator="\n")
    sh.to_csv(T2 / "summary_short_events.csv", index=False, lineterminator="\n"); tr.to_csv(T2 / "truncated_runs_planned_vs_observed.csv", index=False, lineterminator="\n")
    return s1, s2, sh, tr


def _cluster_boot(sim_ids, stat):
    """95 % cluster bootstrap over simulations (both repeats of a run resampled together).  stat(row_index) -> float."""
    rng = np.random.default_rng(BOOT_SEED)
    codes, keys = pd.factorize(np.asarray(sim_ids))
    members = [np.flatnonzero(codes == k) for k in range(len(keys))]
    draws = [stat(np.concatenate([members[k] for k in rng.integers(0, len(keys), len(keys))])) for _ in range(N_BOOT)]
    return float(np.quantile(draws, .025)), float(np.quantile(draws, .975))


def paired(ev):
    """ADDED: paired differences with cluster-bootstrap intervals for T2-H1 (RMSE vs training mean) and T2-H3 (A error vs scalar)."""
    rows = []
    for b in (16, 40, 80):
        t = ev[(ev.budget == b) & ev.model.isin(MODELS)].pivot_table(index=["sim_id", "repeat"], columns="model", values="traj_rmse").reset_index()
        for m in TEMPORAL:
            diff = (t[m] - t["mean_trajectory"]).to_numpy()
            st = lambda ix, diff=diff: float(diff[ix].mean())
            lo, hi = _cluster_boot(t.sim_id, st)
            rows.append({"comparison": f"T2-H1 traj_rmse {m} - mean_trajectory", "budget": b, "estimate": st(np.arange(len(t))), "ci95_lo": lo, "ci95_hi": hi, "rows": len(t)})
        a = ev[(ev.budget == b) & ~ev.truncated_before_plan & ev.pred_A_um.notna()].pivot_table(index=["sim_id", "repeat"], columns="model", values="A_abs_err_um").reset_index()
        for m in TEMPORAL:
            xs, xm = a["scalar_A_GP"].to_numpy(), a[m].to_numpy()
            st = lambda ix, xs=xs, xm=xm: float(np.median(xs[ix]) - np.median(xm[ix]))
            lo, hi = _cluster_boot(a.sim_id, st)
            rows.append({"comparison": f"T2-H3 median |A err| scalar_A_GP - {m} (um)", "budget": b, "estimate": st(np.arange(len(a))), "ci95_lo": lo, "ci95_hi": hi, "rows": len(a)})
    t = pd.DataFrame(rows); t.to_csv(T2 / "paired_differences.csv", index=False, lineterminator="\n")
    return t


def information(ev):
    """Descriptive only (no classifier): how well observed and predicted trajectory features rank the canonical labels
    of held-out runs, overall and within fast scans (VX > 0.85, exploratory).  Label information is kept apart from
    trajectory accuracy; p_max_exceeds_uref is an exceedance probability of the maximum, not a keyhole probability."""
    from sklearn.metrics import roc_auc_score
    rows = []
    like = ev[~ev.truncated_before_plan]
    for (model, b), g in like[like.pred_A_um.notna()].groupby(["model", "budget"]):
        for scope, h in (("all", g), ("VX>0.85 (exploratory)", g[g.VX_m_s > 0.85])):
            if h.has_keyhole.nunique() < 2:
                continue
            r = {"model": model, "budget": b, "scope": scope, "rows": len(h), "runs": h.sim_id.nunique(), "n_pos": int(h.has_keyhole.sum()), "n_neg": int((h.has_keyhole == 0).sum()),
                 "AUC_label_pred_A": roc_auc_score(h.has_keyhole, h.pred_A_um), "AUC_label_p_max_exceeds_uref": roc_auc_score(h.has_keyhole, h.p_max_exceeds_uref),
                 "AUC_label_observed_A": roc_auc_score(h.has_keyhole, h.A_um)}
            if h.pred_exceed_us.notna().all():
                r.update({"AUC_label_pred_exceed_time": roc_auc_score(h.has_keyhole, h.pred_exceed_us), "AUC_label_observed_exceed_time": roc_auc_score(h.has_keyhole, h.obs_exceed_us)})
            if h.A_exceeds_uref.nunique() == 2:
                r["AUC_event_A_gt_uref_p_max_exceeds"] = roc_auc_score(h.A_exceeds_uref, h.p_max_exceeds_uref)
            r["label_agrees_with_event_A_gt_uref"] = float((h.has_keyhole == h.A_exceeds_uref).mean())
            rows.append(r)
    t = pd.DataFrame(rows); t.to_csv(T2 / "information_preserved_descriptive.csv", index=False, lineterminator="\n")
    comp = pd.read_csv(T2 / "compression_error_all_runs.csv")
    k = comp[comp.K == 360]
    rep = pd.DataFrame([{"K": 360, "runs": len(k), "rmse_median_log1p": k.rmse.median(), "rmse_p90_log1p": k.rmse.quantile(.9), "rmse_max_log1p": k.rmse.max(),
                         "peak_loss_median_log1p": k.max_loss_log1p.median(), "peak_loss_p90_log1p": k.max_loss_log1p.quantile(.9), "peak_loss_max_log1p": k.max_loss_log1p.max(),
                         "note": "label-free; the exact native maximum of every training run is added as an extra GP training point"}])
    rep.to_csv(T2 / "information_preserved_representation.csv", index=False, lineterminator="\n")
    return t, rep


def matched_pair(ev):
    """Observed difference between the matched pair's trajectories vs each model's predictive spread, and the models'
    predicted difference (each run predicted from the checkpoint in which it is held out)."""
    native = load_native(); ck = pd.read_csv(T2 / "checkpoints.csv")
    rows = []
    K = int(ck.K.iloc[0]); assert (ck.K == K).all()
    ga, gb = bin_means(native[PAIR[0]], K).set_index("b"), bin_means(native[PAIR[1]], K).set_index("b")
    common = ga.index.intersection(gb.index).to_numpy()
    obs_diff = float(np.sqrt(np.mean((ga.y.loc[common].to_numpy() - gb.y.loc[common].to_numpy()) ** 2)))
    for b in (16, 40, 80):
        for rep in (1, 2):
            hits = {}
            for sid in PAIR:
                for c in ck[(ck.budget == b) & (ck.repeat == rep)].itertuples():
                    ids = list(load_ckpt(c.checkpoint)["test_ids"])
                    if sid in ids:
                        hits[sid] = (c.checkpoint, ids.index(sid)); break
            if len(hits) < 2:
                continue
            for mname in TEMPORAL:
                vals = {}
                for sid, (cn, i) in hits.items():
                    z = dict(np.load(PRED / f"{mname}_{cn}.npz", allow_pickle=False))
                    vals[sid] = (z["mean"][i], np.sqrt(z["var_latent"][i] + z["var_noise"][i]))
                (ma, sa), (mb, sb) = vals[PAIR[0]], vals[PAIR[1]]
                spread = float(np.sqrt(np.mean(sa[common] ** 2 + sb[common] ** 2)))
                rows.append({"model": mname, "budget": b, "repeat": rep, "observed_rms_difference": obs_diff,
                             "predicted_rms_difference": float(np.sqrt(np.mean((ma[common] - mb[common]) ** 2))),
                             "rms_sd_of_difference": spread, "ratio_observed_to_sd_of_difference": obs_diff / spread,
                             "differs_beyond_predictive_uncertainty": bool(obs_diff / spread > 2), "common_bins": len(common),
                             "checkpoints": f"{hits[PAIR[0]][0]} / {hits[PAIR[1]][0]}"})
    t = pd.DataFrame(rows); t.to_csv(T2 / "matched_pair_trajectories.csv", index=False, lineterminator="\n")
    nr = ev[ev.H.isin(NAMED)][["H", "model", "budget", "repeat", "has_keyhole", "VX_m_s", "A_um", "pred_A_um", "A_lo90", "A_hi90", "p_max_exceeds_uref",
                               "traj_rmse", "cov90", "obs_exceed_us", "pred_exceed_us"]].assign(role=lambda x: x.H.map(NAMED))
    nr.sort_values(["H", "model", "budget", "repeat"]).to_csv(T2 / "named_runs_predictions.csv", index=False, lineterminator="\n")
    return t, nr


def verdicts(ev, s1, s2, ps):
    """Hypothesis verdicts by the rules in EVALUATION_RULES_T2.md."""
    out = []
    r = s1.set_index(["model", "budget"])
    h1 = {(m, b): bool(r.loc[(m, b), "traj_rmse_mean"] < r.loc[("mean_trajectory", b), "traj_rmse_mean"]) for m in TEMPORAL for b in (16, 40, 80)}
    out.append({"hypothesis": "T2-H1_inputs_help", "verdict": "SUPPORTED" if all(h1.values()) else "FALSIFIED",
                "detail": "; ".join(f"{m} B{b}: {'lower' if v else 'NOT lower'}" for (m, b), v in h1.items())})
    h2 = {m: (r.loc[(m, 80), "traj_rmse_fold_mean"] < r.loc[(m, 16), "traj_rmse_fold_mean"],
              r.loc[(m, 16), "traj_rmse_fold_mean"] > r.loc[(m, 40), "traj_rmse_fold_mean"] > r.loc[(m, 80), "traj_rmse_fold_mean"]) for m in TEMPORAL}
    out.append({"hypothesis": "T2-H2_learning", "verdict": "SUPPORTED" if all(v[0] for v in h2.values()) else "FALSIFIED",
                "detail": "; ".join(f"{m}: B80<B16 {v[0]}, monotone {v[1]}" for m, v in h2.items())})
    q = s2.set_index(["model", "budget"])
    h3 = {(m, b): bool(q.loc[("scalar_A_GP", b), "A_abs_err_median_um"] < q.loc[(m, b), "A_abs_err_median_um"]) for m in TEMPORAL for b in (40, 80)}
    out.append({"hypothesis": "T2-H3_max_depth", "verdict": "SUPPORTED" if all(h3.values()) else "FALSIFIED",
                "detail": "; ".join(f"scalar vs {m} B{b}: {'scalar lower' if v else 'scalar NOT lower'}" for (m, b), v in h3.items())})
    out.append(_h4(ev))
    for h, txt in (("T2-H5_calibration", "descriptive"), ("T2-H6_model_ranking", "descriptive"), ("T2-H7_matched_pair_fast_scans", "descriptive"), ("T2-H8_truncated", "descriptive")):
        out.append({"hypothesis": h, "verdict": "NO VERDICT (descriptive by design)", "detail": txt})
    if len(ps) and "relative_change" in ps:
        p = ps.iloc[0]
        out.append({"hypothesis": "T2-PS1 (POST-START)", "verdict": p.hypothesis_abs_change_lt_10pct,
                    "detail": f"mean RMSE {p.rmse_mean_it2000:.4f} (2000 it) -> {p.rmse_mean_it6000:.4f} (6000 it), relative change {p.relative_change:+.1%}, {int(p.rows)} rows"})
    t = pd.DataFrame(out); t.to_csv(T2 / "hypothesis_verdicts_T2.csv", index=False, lineterminator="\n")
    return t


def _h4(ev):
    like = ev[~ev.truncated_before_plan & ev.model.isin(TEMPORAL) & ev.pred_A_um.notna()]
    n_short = like[like.short_event].sim_id.nunique()
    if n_short < MIN_SHORT_RUNS:
        return {"hypothesis": "T2-H4_short_events", "verdict": "INCONCLUSIVE", "detail": f"{n_short} distinct short-event runs (< {MIN_SHORT_RUNS})"}
    res = {}
    for m, g in like.groupby("model"):
        res[m] = (float(g[g.short_event].A_log1p_err.median()), float(g[~g.short_event].A_log1p_err.median()))
    ok = all(a < b for a, b in res.values())
    return {"hypothesis": "T2-H4_short_events", "verdict": "SUPPORTED" if ok else "FALSIFIED",
            "detail": f"{n_short} short-event runs; " + "; ".join(f"{m}: median log1p err short {a:+.4f} vs other {b:+.4f}" for m, (a, b) in res.items())}


def figures(ev):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    native = load_native(); reg = registry(); (T2 / "figures").mkdir(parents=True, exist_ok=True)
    col = {"mean_trajectory": "#999999", "functional": "#228833", "svgp": "#AA3377", "scalar_A_GP": "#CC3311"}
    s = ev[ev.model.isin(MODELS)].groupby(["model", "budget"]).traj_rmse.mean().unstack(0)
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.2))
    for m in s.columns:
        axs[0].plot(s.index, s[m], marker="o", color=col[m], label=m)
    axs[0].set_title("Trajectory RMSE (log1p depth), mean over held-out runs", loc="left", fontsize=8); axs[0].set_xlabel("paid simulations"); axs[0].legend(fontsize=7, frameon=False)
    like = ev[~ev.truncated_before_plan & ev.pred_A_um.notna()]
    a = like.groupby(["model", "budget"]).A_abs_err_um.median().unstack(0)
    for m in a.columns:
        axs[1].plot(a.index, a[m], marker="o", color=col.get(m, "#000000"), label=m)
    axs[1].set_title("Maximum depth A: median absolute error (µm), like-for-like runs", loc="left", fontsize=8); axs[1].set_xlabel("paid simulations"); axs[1].legend(fontsize=7, frameon=False)
    for ax in axs:
        ax.set_xticks([16, 40, 80]); ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(T2 / "figures/track2_errors_by_budget.png", dpi=160); plt.close(fig)
    # representative held-out runs at B40, repeat 1 (best / median / worst by SVGP RMSE) + named runs
    sv = ev[(ev.model == "svgp") & (ev.budget == 40) & (ev.repeat == 1)].dropna(subset=["traj_rmse"]).sort_values("traj_rmse")
    if not len(sv):
        return
    picks = [("best", sv.iloc[0]), ("median", sv.iloc[len(sv) // 2]), ("worst", sv.iloc[-1])]
    for h in NAMED:
        q = sv[sv.H == h]
        if len(q):
            picks.append((NAMED[h], q.iloc[0]))
    fig, axs = plt.subplots(len(picks), 1, figsize=(9, 2.3 * len(picks)))
    for ax, (lab, r) in zip(np.atleast_1d(axs), picks):
        d = load_ckpt(r.checkpoint); i = list(d["test_ids"]).index(r.sim_id); c_ = d["centers"]; tr = native[r.sim_id]
        step = max(1, len(tr["s"]) // 4000)
        ax.plot(tr["s"][::step], tr["y"][::step], color="#BBBBBB", lw=0.6, label="native (thinned)")
        ax.plot(c_, d["te_obs"][i], color="black", lw=0.9, label="observed bin means")
        for m in TEMPORAL:
            z = dict(np.load(PRED / f"{m}_{r.checkpoint}.npz", allow_pickle=False)); sd = np.sqrt(z["var_latent"][i] + z["var_noise"][i])
            ax.plot(c_, z["mean"][i], color=col[m], lw=1.0, label=f"{m} mean ± 90 %"); ax.fill_between(c_, z["mean"][i] - Z90 * sd, z["mean"][i] + Z90 * sd, color=col[m], alpha=.15, lw=0)
        sc = dict(np.load(PRED / f"scalar_{r.checkpoint}.npz", allow_pickle=False))
        ax.axhline(np.log1p(np.exp(sc["mu_logA"][i])), color=col["scalar_A_GP"], ls="--", lw=0.8, label="scalar A GP: predicted A")
        ax.axhline(UREF_LOG1P, color="#666666", ls=":", lw=0.7, label="u_ref")
        ax.axvline(reg.loc[r.sim_id, "s_plan"], color="#888888", ls="--", lw=0.6)
        ax.set_xlim(0, 0.92); ax.set_title(f"{lab}: {r.H}, label {r.has_keyhole}, VX {r.VX_m_s:.3f} m/s; SVGP RMSE {r.traj_rmse:.3f}", loc="left", fontsize=8)
        ax.set_ylabel("log(1 + depth µm)", fontsize=7); ax.spines[["top", "right"]].set_visible(False)
    np.atleast_1d(axs)[0].legend(fontsize=6, frameon=False, ncol=3, loc="lower right"); np.atleast_1d(axs)[-1].set_xlabel("s = t / derived exit (dashed vertical line: planned horizon)")
    fig.tight_layout(); fig.savefig(T2 / "figures/track2_representative_B40_r1.png", dpi=150); plt.close(fig)


def resources():
    rows = []
    sc = pd.read_csv(T2 / "scalar_reference_fits.csv"); fu = pd.read_csv(T2 / "functional_fits.csv")
    sv = pd.DataFrame([json.loads(l) for l in (T2 / "svgp_fits.jsonl").read_text().splitlines() if l.strip()])
    for name, t in (("scalar_A_GP", sc), ("functional_rank3 (3 coefficient GPs + basis)", fu)):
        rows.append({"model": name, "fits": len(t) * (3 if name.startswith("functional") else 1), "checkpoints": len(t),
                     "seconds_median": float(t.fit_seconds.median()), "seconds_total": float(t.fit_seconds.sum())})
    for tag, g in sv.groupby("tag"):
        rows.append({"model": tag, "fits": len(g), "checkpoints": len(g), "seconds_median": float(g.total_seconds.median()), "seconds_total": float(g.total_seconds.sum()),
                     "peak_memory_gib_max": float(g.peak_memory_bytes.max() / 2 ** 30), "points_median": float(g.n_points.median()),
                     "loss_trace_last_block_change_median": float(g.trace_last10pct_change.median()), "lengthscale_s_median": float(g.lengthscale_s.median()),
                     "noise_median": float(g.noise.median())})
    t = pd.DataFrame(rows); t.to_csv(T2 / "resources_and_runtime.csv", index=False, lineterminator="\n")
    return t, sv


def fidelity_m800(name="ckpt_r1_f1_B40"):
    a, b = PRED / f"svgp_{name}.npz", PRED / f"svgp_M800_{name}.npz"
    if not (a.exists() and b.exists()):
        return pd.DataFrame()
    A, B = dict(np.load(a, allow_pickle=False)), dict(np.load(b, allow_pickle=False)); d = load_ckpt(name)
    obs = np.isfinite(d["te_obs"])
    rows = [{"checkpoint": name, "rms_mean_difference_M400_vs_M800": float(np.sqrt(np.mean((A["mean"][obs] - B["mean"][obs]) ** 2))),
             "rmse_M400": float(np.sqrt(np.mean((A["mean"][obs] - d["te_obs"][obs]) ** 2))), "rmse_M800": float(np.sqrt(np.mean((B["mean"][obs] - d["te_obs"][obs]) ** 2))),
             "median_abs_diff_pred_A_um": float(np.median(np.abs(np.expm1(np.median(A["max_planned"].astype(float), 1)) - np.expm1(np.median(B["max_planned"].astype(float), 1))))),
             "mean_sd_ratio_M800_over_M400": float(np.mean(np.sqrt(B["var_latent"][obs] + B["var_noise"][obs]) / np.sqrt(A["var_latent"][obs] + A["var_noise"][obs])))}]
    t = pd.DataFrame(rows); t.to_csv(T2 / "svgp_inducing_fidelity.csv", index=False, lineterminator="\n")
    return t


def poststart():
    """POST-START T2-PS1: frozen SVGP (2000 iterations) vs 6000 iterations on the five repeat-1 B40 checkpoints."""
    rows = []
    for f in range(1, 6):
        name = f"ckpt_r1_f{f}_B40"; a, b = PRED / f"svgp_{name}.npz", PRED / f"svgp_it6000_{name}.npz"
        if not (a.exists() and b.exists()):
            continue
        A, B = dict(np.load(a, allow_pickle=False)), dict(np.load(b, allow_pickle=False)); d = load_ckpt(name)
        for i, sid in enumerate(d["test_ids"]):
            o = np.isfinite(d["te_obs"][i])
            rows.append({"checkpoint": name, "sim_id": sid, "rmse_it2000": float(np.sqrt(np.mean((A["mean"][i][o] - d["te_obs"][i][o]) ** 2))),
                         "rmse_it6000": float(np.sqrt(np.mean((B["mean"][i][o] - d["te_obs"][i][o]) ** 2)))})
    t = pd.DataFrame(rows)
    if len(t):
        t.to_csv(T2 / "POSTSTART_T2-PS1_per_run.csv", index=False, lineterminator="\n")
        s = {"POSTSTART": "T2-PS1", "checkpoints": t.checkpoint.nunique(), "rows": len(t), "rmse_mean_it2000": float(t.rmse_it2000.mean()), "rmse_mean_it6000": float(t.rmse_it6000.mean()),
             "relative_change": float(t.rmse_it6000.mean() / t.rmse_it2000.mean() - 1)}
        s["hypothesis_abs_change_lt_10pct"] = "SUPPORTED" if abs(s["relative_change"]) < 0.10 else "FALSIFIED"
        pd.DataFrame([s]).to_csv(T2 / "POSTSTART_T2-PS1_convergence.csv", index=False, lineterminator="\n")
        return pd.DataFrame([s])
    return t


def main():
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    ev = evaluate(); s1, s2, sh, tr = summarise(ev); pr = paired(ev); info, rep = information(ev); mp, nr = matched_pair(ev)
    rs, sv = resources(); fm = fidelity_m800(); ps = poststart(); vd = verdicts(ev, s1, s2, ps); figures(ev)
    for t, nd in ((rs, 3), (fm, 4), (ps, 4), (s1, 4), (s2, 3), (sh, 3), (tr, 1), (pr, 4), (info, 3), (rep, 4), (mp, 4), (vd, 0)):
        print(t.round(nd).to_string(), "\n")
    return ev


if __name__ == "__main__":
    main()
