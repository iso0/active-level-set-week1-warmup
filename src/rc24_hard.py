"""RC24 section 4 - the hard region (evaluator-only memberships; descriptive; no learner reads any of this).

verify   the owner's B60 figures on the RC23 h-std records (fresh repeats 51-58, standard startup, own-query margin paths):
         recall of HA_LEAN / HONLY_LR on the 10 NEW short-Keyhole originals, specificity on the 12 NEW conduction runs, the
         hard-group BA, pooled short-K recall (22 runs); per repeat (fold-pooled, every run predicted once) and the mean.
mechanism  ONE mechanism question, kept in two parts:
         Q  At equal (active-window) maximum depth, is the short-Keyhole event a start-up transient - i.e. does the TIMING of
            the event separate the NEW short-Keyhole runs from the NEW conduction runs?
         (a) post-opening explanatory separability: per-frame labels of the NEW runs (labels_new_data_4_prep.csv, read-only,
             data/raw of the main checkout, Hugging Face ioandanielc/sph_v2@2e1eec9c) -> the time of the first and last keyhole
             frame and the keyhole share of the active window; leave-one-out AUC of depth alone vs depth + timing summary
             inside the hard group (this is explanation AFTER the simulation, not prediction);
         (b) pre-opening usefulness: can that timing summary be PREDICTED at an unqueried point from paid runs? Honest
             leave-one-out GP prediction from the public inputs over the NEW runs (R^2), and whether the predicted summary keeps
             any separation inside the hard group.
    python -m src.rc24_hard verify | mechanism
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc19_pool as P
import src.rc22_eval as E22
import src.rc24_eval as E24

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc24" / "hard_region"
R23 = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc23"
RAW = Path(r"C:\Users\ozgur\Documents\thesis\data\raw\sph_v2\2e1eec9c98fd57609d2815f174586336ab59da07")


def verify():
    OUT.mkdir(parents=True, exist_ok=True); M = P.manifest(); U = EV.load_units(R23 / "h-std")
    T = {(t["repeat"], t["fold"]): t for t in P.tasks(sorted({u["repeat"] for u in U}))}
    rows = E22.learner_rows(U, M, T, cons_map=lambda u: [(list(u["evals"][0]["p"].keys())[0], u["arm"])])
    X = E24.extra_pooled(rows, M); out = {}
    for b in (24, 40, 60):
        g = X[X.budget == b].groupby("arm")[["recall_shortK_NEW", "spec_cond_NEW", "BA_hard_group", "recall_shortK_pooled"]].mean()
        out[f"B{b}"] = g.round(4).to_dict(orient="index")
    n = X[["n_shortK_NEW", "n_cond_NEW"]].drop_duplicates().to_dict(orient="records")
    res = {"source": "RC23 h-std units (repeats 51-58, 5 folds, own-query margin paths); fold-pooled per repeat, mean over 8 repeats", "group_sizes": n, "by_budget": out,
           "owner_figures": {"HA_LEAN_shortK_NEW_recall": "~0.95", "HA_LEAN_NEW_conduction_specificity": "~0.33", "HONLY_LR": "all positives right, all 12 negatives called Keyhole",
                             "HA_LEAN_local_BA": "~0.64", "HA_LEAN_pooled_22_shortK_recall": "~0.80"}}
    (OUT / "HARD_VERIFY.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); print(json.dumps(res, indent=1)); return res


# ======================================================================================== mechanism (descriptive)
def frame_timing(M):
    """Per NEW run from the per-frame labels: the active window starts at the first 'Forming Phase' frame (laser on, melt pool
    forming) and ends at the last 'Keyhole' / 'Conduction' frame before scanning stops; keyhole-frame times are expressed
    relative to that window (0 = start of forming, 1 = end of the scanned record)."""
    lab = pd.read_csv(RAW / "labels_new_data_4_prep.csv")
    lab = lab[lab.name.isin(M.sim_id)]; rows = []
    for sid, g in lab.groupby("name"):
        g = g.sort_values("timestep"); ts = g.timestep.to_numpy(float); L = g.label_final.astype(str).to_numpy()
        k = L == "Keyhole"; form = L == "Forming Phase"; steady = (L == "Keyhole") | (L == "Conduction")
        if not (form.any() or steady.any()):
            rows.append({"sim_id": sid, "frames": len(g)}); continue
        t0 = ts[form].min() if form.any() else ts[steady].min(); t_form_end = ts[form].max() if form.any() else t0
        t1 = ts[steady].max() if steady.any() else ts[form].max(); span = max(t1 - t0, 1.0); rel = (ts - t0) / span
        rows.append({"sim_id": sid, "frames": len(g), "forming_frames": int(form.sum()), "steady_frames": int(steady.sum()), "keyhole_frames": int(k.sum()),
                     "forming_end_rel": float((t_form_end - t0) / span), "first_K_rel": float(rel[k].min()) if k.any() else np.nan,
                     "last_K_rel": float(rel[k].max()) if k.any() else np.nan, "K_share_steady": float(k[steady].mean()) if steady.any() else np.nan,
                     "K_frames_within_forming_plus_10pct": int(np.sum(k & (rel <= (t_form_end - t0) / span + 0.10))),
                     "labels_seen": "|".join(sorted(set(L.tolist())))})
    return pd.DataFrame(rows)


def _loo_auc(Xf, y):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    s = np.empty(len(y))
    for i in range(len(y)):
        tr = np.arange(len(y)) != i; mu, sd = Xf[tr].mean(0), Xf[tr].std(0) + 1e-12
        lr = LogisticRegression(C=1.0, max_iter=2000).fit((Xf[tr] - mu) / sd, y[tr]); s[i] = lr.decision_function(((Xf[i] - mu) / sd)[None])[0]
    return float(roc_auc_score(y, s))


def mechanism():
    OUT.mkdir(parents=True, exist_ok=True); M = P.manifest().reset_index(drop=False)
    if "sim_id" not in M.columns:
        M = M.rename(columns={"index": "sim_id"})
    N = M[M.source_batch == "NEW"].copy(); Ft = frame_timing(N); N = N.merge(Ft, on="sim_id", how="left")
    hard_all = N[N.shortK_NEW_original.astype(bool) | (N.y == 0)].copy(); hard_all["group"] = np.where(hard_all.y == 1, "shortK_NEW", "cond_NEW")
    cols = ["sim_id", "group", "P", "VX", "LS", "ST", "A_um", "short_record", "frac_K_FCK", "forming_end_rel", "first_K_rel", "last_K_rel", "K_share_steady",
            "K_frames_within_forming_plus_10pct", "keyhole_frames", "steady_frames", "labels_seen"]
    hard_all[cols].to_csv(OUT / "hard_group_timing.csv", index=False)
    hard = hard_all[np.isfinite(hard_all.A_um.to_numpy(float))].copy()                 # depth-based tests need a measured depth
    y = (hard.group == "shortK_NEW").to_numpy(int); logA = np.log(hard.A_um.to_numpy(float))
    res = {"question": "At equal active-window maximum depth, is the short-Keyhole event a start-up transient (timing) that separates the NEW short-Keyhole runs from the NEW conduction runs?",
           "n_shortK_NEW": int(y.sum()), "n_cond_NEW_with_depth": int((1 - y).sum()), "excluded_no_depth": hard_all[~np.isfinite(hard_all.A_um.to_numpy(float))].sim_id.tolist()}
    sk = hard[hard.group == "shortK_NEW"]
    res["timing_of_keyhole_frames_in_shortK_NEW"] = {"forming_end_rel_median": float(sk.forming_end_rel.median()), "first_K_rel_median": float(sk.first_K_rel.median()),
                                                    "first_K_rel_max": float(sk.first_K_rel.max()), "last_K_rel_median": float(sk.last_K_rel.median()), "last_K_rel_max": float(sk.last_K_rel.max()),
                                                    "share_runs_all_K_frames_within_forming_plus_10pct": float((sk.K_frames_within_forming_plus_10pct == sk.keyhole_frames).mean()),
                                                    "per_run": sk[["sim_id", "A_um", "frac_K_FCK", "forming_end_rel", "first_K_rel", "last_K_rel", "keyhole_frames", "steady_frames"]].round(4).to_dict(orient="records")}
    res["depth_overlap"] = {"cond_NEW_A_um_range": [float(hard[hard.y == 0].A_um.min()), float(hard[hard.y == 0].A_um.max())],
                            "shortK_NEW_A_um_range": [float(sk.A_um.min()), float(sk.A_um.max())], "LOO_AUC_logA_only": _loo_auc(logA[:, None], y)}
    # (a) post-opening: the timing summary is defined only for keyhole runs (conduction has no keyhole frame) -> it is a label
    #     consequence, not an explanatory covariate; the non-tautological post-opening covariates are the start-up window
    #     summaries in the manifest (T0-window features), tested at equal depth:
    t0cols = [c for c in ("tmax_T0_K", "laser_T0_W", "log_ke_T0_nJ", "log_etot_T0_J", "log_npart_T0", "vmax_spike_logratio") if c in hard.columns]
    res["post_opening_LOO_AUC_logA_plus_T0_feature"] = {c: _loo_auc(np.c_[logA, hard[c].to_numpy(float)], y) for c in t0cols}
    res["post_opening_LOO_AUC_T0_feature_alone"] = {c: _loo_auc(hard[c].to_numpy(float)[:, None], y) for c in t0cols}
    # (b) pre-opening: honest LOO GP prediction of the best post-opening covariate from the public inputs over ALL NEW runs
    best = max(res["post_opening_LOO_AUC_logA_plus_T0_feature"], key=res["post_opening_LOO_AUC_logA_plus_T0_feature"].get)
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
    Zn = np.log(N[["P", "VX", "LS", "ST"]].to_numpy(float)); Zn = (Zn - Zn.mean(0)) / Zn.std(0); v = N[best].to_numpy(float); ok = np.isfinite(v)
    pred = np.full(len(N), np.nan)
    for i in np.flatnonzero(ok):
        tr = ok & (np.arange(len(N)) != i); mu, sd = v[tr].mean(), v[tr].std() + 1e-12
        gp = GaussianProcessRegressor(ConstantKernel() * Matern(length_scale=np.ones(4), nu=1.5) + WhiteKernel(), normalize_y=False, n_restarts_optimizer=0)
        gp.fit(Zn[tr], (v[tr] - mu) / sd); pred[i] = mu + sd * gp.predict(Zn[i][None])[0]
    r2 = 1 - np.nansum((pred[ok] - v[ok]) ** 2) / np.nansum((v[ok] - v[ok].mean()) ** 2)
    hp = pd.Series(pred, index=N.sim_id).reindex(hard.sim_id).to_numpy(float)
    res["pre_opening"] = {"covariate": best, "LOO_GP_R2_over_NEW_runs": float(r2), "LOO_AUC_logA_plus_PREDICTED_covariate_in_hard_group": _loo_auc(np.c_[logA, hp], y),
                          "LOO_AUC_PREDICTED_covariate_alone_in_hard_group": _loo_auc(hp[:, None], y),
                          "note": "the depth itself is the measured paid depth here (post-opening); the pre-opening test replaces only the covariate by its prediction"}
    (OUT / "HARD_MECHANISM.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); print(json.dumps(res, indent=1)); return res


if __name__ == "__main__":
    {"verify": verify, "mechanism": mechanism}[sys.argv[1]]()
