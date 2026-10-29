"""C1S DEV diagnosis, part 2: instrumented replay of C1 on RECORDED C1C paths (same paid data), with same-data controls.

The replica uses the frozen C1 functions (src.ea_cand.depth_fit_cand / GPMAP, src.rc19b_keyhole.folds, src.rc24_pac.depth_predict,
src.rc22_common.phr_family pieces) and must reproduce the recorded C1_own probabilities bit-exactly (float32) at every budget;
it additionally records the internals and evaluates three controls at step b -> b + 1 on the paid data of b + 1:
  HYP   depth GPs (full fit and the 10 fold fits) with hyperparameters AND response standardisation frozen at their budget-b values,
        conditioned on the b + 1 data (posterior update only)            -> effect of re-estimation = p(b+1) - p_HYP
  CLF   the budget-b classifier (feature standardisation, 16 Laplace modes, weights) applied to the b + 1 depth predictions
                                                                         -> depth-change-only effect = p_CLF - p(b)
  W     the b + 1 classifier with the budget-b configuration weights   -> weight-switch effect = p(b+1) - p_W
Learners: all 5 folds of STD repeats 203, 211, ..., 275 (every 8th repeat; chosen by ID, not by outcome). DEV.
    python -m src.c1s_trace work c1s-trace | summary
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
import pandas as pd
from scipy.linalg import cho_factor, cho_solve
from scipy.special import expit

import src.ea_cand as CA
import src.ea_diag2 as D2
import src.el_export as EX
import src.rc18_campaign as C18
import src.rc18_common as RC
import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc20_attr as A
import src.rc21_phr as PH
import src.rc22_common as C22
import src.rc24_pac as PC

OUT = RC.ROOT / "outputs" / "research_campaign_20261029" / "opus_c1_stability"
C1C = RC.ROOT / "outputs" / "research_campaign_20261026" / "opus_c1_confirmation"
REPS = tuple(range(203, 283, 8))


# ---------------------------------------------------------------- depth GP fits (replica of ea_cand.gp_fit with the start index)
def fit_c1(Zl, Yl, Hl, Wl):
    kind, prior, starts = CA.SYSTEMS["C1"]; best, bi = None, -1
    for si, th0 in enumerate(starts):
        g = CA.GPMAP(H_cols=1, b=PC.B_TREND, prior=prior).fit(Zl, Yl, H=Hl, w=Wl, theta0=np.asarray(th0, float))
        if best is None or g.opt["nlml"] < best.opt["nlml"]:
            best, bi = g, si
    return best, bi


def fit_fixed(Zl, Yl, Hl, Wl, theta, mu, sd):
    """Posterior update only: hyperparameters and response standardisation given (from the previous budget)."""
    g = CA.GPMAP(H_cols=1, b=PC.B_TREND, prior=True); Zl = np.asarray(Zl, float); n = len(Zl)
    g.m0_train = np.zeros(n); g.w = np.asarray(Wl, float); g.mu, g.sd = float(mu), float(sd); ys = (np.asarray(Yl, float) - g.mu) / g.sd
    g.H = np.asarray(Hl, float); g.theta = np.asarray(theta, float); g.opt = {"nlml": np.nan, "nit": 0, "success": True}
    Kx = g._K(g.theta, Zl, g.H, g.w)[0]; g.c = cho_factor(Kx + 1e-10 * np.eye(n), lower=True); g.alpha = cho_solve(g.c, ys); g.Z = Zl
    return g


def depth_fit(task, rev, Z, rows, fixed=None):
    """= ea_cand.depth_fit_cand("phys", prior, STARTS) with optional frozen (theta, mu, sd); returns fit dict + record."""
    L = np.asarray(rows); Y = rev.paid_Y()[:, PC.DEPTH_COL]; W = np.where(rev.paid_short(), C18.W_SHORT, 1.0)
    Lu = L[np.isfinite(Y[L])]
    if (W[Lu] <= 100).sum() < 3:
        return None, None
    H = A.hcol(task)[:, None]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if fixed is None:
            g, si = fit_c1(Z[Lu], Y[Lu], H[Lu], W[Lu])
        else:
            g = fit_fixed(Z[Lu], Y[Lu], H[Lu], W[Lu], *fixed); si = -1
    return {"g": g, "H": H, "rows": Lu}, {"theta": g.theta.tolist(), "mu": g.mu, "sd": g.sd, "nlml": g.opt["nlml"], "start": si, "n": int(len(Lu))}


def cf(task, rev, Z, rows, frozen=None):
    """= ea_diag2.cf_generic with the C1 fitter; frozen = {key: (theta, mu, sd)} from the previous budget."""
    paid = rev.paid; Y = rev.paid_Y()[:, D2.DCOL]; fold, k = K.folds(len(paid), A.KF); F = np.full(len(paid), np.nan); rec = {}
    for j in range(k):
        tr = paid[fold != j]; f, r = depth_fit(task, rev, Z, tr, None if frozen is None or j not in frozen else frozen[j]); rec[j] = r
        if f is None:
            v = Y[tr]; v = v[np.isfinite(v)]; F[fold == j] = float(np.mean(v)) if len(v) else 0.0
        else:
            F[fold == j] = PC.depth_predict(f, Z, paid[fold == j])[0]
    full, r = depth_fit(task, rev, Z, paid, None if frozen is None or "full" not in frozen else frozen["full"]); rec["full"] = r
    E = PC.depth_predict(full, Z, rows)[0] if full is not None else np.full(len(rows), np.nanmean(Y[paid]))
    return F, E, rec


# ---------------------------------------------------------------- classifier (replica of rc22_common.phr_family, feats = (0,))
def clf_fit(Ftr, htr, y):
    Xtr = np.c_[htr, np.asarray(Ftr, float).reshape(-1, 1)]; mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-12; Htr = (Xtr - mu) / sd; y = np.asarray(y, float)
    Utr = np.zeros((len(Htr), 1)); Gtt = PH.Gram(Htr, Htr, Utr, Utr); cfg = [(tf, th) for tf in PH.TAU_F for th in PH.TAU_H]; modes, logw = [], np.empty(len(cfg))
    for g, (tf, th) in enumerate(cfg):
        mode = PH.laplace(Gtt.K(tf, th, 0.0, None), y); modes.append(mode); logw[g] = mode["logZ"]
    w = np.exp(logw - logw.max()); w /= w.sum()
    return {"mu": mu, "sd": sd, "Htr": Htr, "Utr": Utr, "cfg": cfg, "modes": modes, "w": w}


def clf_apply(st, Fev, hev, w=None):
    Xev = np.c_[hev, np.asarray(Fev, float).reshape(-1, 1)]; Hev = (Xev - st["mu"]) / st["sd"]; Uev = np.zeros((len(Hev), 1))
    Get = PH.Gram(Hev, st["Htr"], Uev, st["Utr"]); kss_h = Hev[:, 0] ** 2; kss_F = np.sum(Hev[:, 1:] ** 2, 1); Mm = np.empty((len(st["cfg"]), len(Hev)))
    for g, (tf, th) in enumerate(st["cfg"]):
        kss = PH.V0 + th ** 2 * kss_h + tf ** 2 * kss_F; Mm[g], _, _ = PH.predictive(st["modes"][g], Get.K(tf, th, 0.0, None), kss, plugin=True)
    return (st["w"] if w is None else w) @ expit(Mm)


# ---------------------------------------------------------------- replay of one learner
def replay(task, M, paid_ids, rec_p):
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid_all = [pos[s] for s in paid_ids]; te = np.asarray(task["test"]); nt = len(te)
    h = A.hcol(task); out = []; prev = None; chk = 0.0; path_ok = True
    for b in range(8, 61):
        rev = K._rev_with(task, M, paid_all[:b]); L = rev.paid; y = rev.paid_y()[L]; cands = np.setdiff1d(task["pool"], rev.paid); rows = np.r_[te, cands]
        F, E, rec = cf(task, rev, Z, rows); st = clf_fit(F, h[L], y); p = clf_apply(st, E, h[rows])
        p32 = np.asarray(LN._f32(p[:nt])); chk = max(chk, float(np.max(np.abs(p32 - np.asarray(rec_p[b], float)))))
        if b < 60:
            nxt = int(cands[int(np.argmax(-np.abs(p[nt:] - 0.5)))]); path_ok &= (task["ids"][nxt] == paid_ids[b])
        e = {"budget": b, "p": p32.tolist(), "rec_full": rec["full"], "theta_folds": [rec[j]["theta"] if rec.get(j) else None for j in range(10)],
             "mu_sd_folds": [(rec[j]["mu"], rec[j]["sd"]) if rec.get(j) else None for j in range(10)], "E_test": LN._f32(E[:nt]), "w": st["w"].tolist(),
             "clf_mu": st["mu"].tolist(), "clf_sd": st["sd"].tolist()}
        if prev is not None:                         # controls on the b data relative to b - 1 (prev)
            frozen = {j: (np.asarray(prev["rec"][j]["theta"]), prev["rec"][j]["mu"], prev["rec"][j]["sd"]) for j in range(10) if prev["rec"].get(j)}
            frozen["full"] = (np.asarray(prev["rec"]["full"]["theta"]), prev["rec"]["full"]["mu"], prev["rec"]["full"]["sd"])
            Fh, Eh, _ = cf(task, rev, Z, te, frozen); p_hyp = clf_apply(clf_fit(Fh, h[L], y), Eh, h[te])
            p_clf = clf_apply(prev["st"], E[:nt], h[te]); p_w = clf_apply(st, E[:nt], h[te], w=prev["st"]["w"])
            e["p_HYP"] = LN._f32(p_hyp); e["p_CLF"] = LN._f32(p_clf); e["p_W"] = LN._f32(p_w)
        prev = {"rec": rec, "st": st}; out.append(e)
    return out, chk, path_ok


def units(job):
    if job == "c1s-trace":
        return [(f"STD__r{r}_f{f}", ("STD", r, f)) for r in REPS for f in range(1, 6)]
    if job == "c1s-trace-smoke":
        return [("STD__r203_f1", ("STD", 203, 1))]
    raise ValueError(job)


def work(job):
    RC.limit_threads(1); U_ = units(job); M = P.manifest(); S = dict(U_); C22.set_manifest(M)
    E = {}
    for s in ("main_s1", "main_s2"):
        E.update({k: v for k, v in EX.load(C1C / "exports" / s).items() if k[0] == "C1_own"})
    paths = pd.concat([pd.read_csv(C1C / "exports" / s / "paths.csv.gz") for s in ("main_s1", "main_s2")], ignore_index=True)
    T = {(t["repeat"], t["fold"]): t for t in P.tasks(sorted({r for _, r, _ in S.values()}))}

    def fn(name):
        c, r, f = S[name]; task = T[(r, f)]; bs, Pm, ids = E[("C1_own", "STD", r, f)]
        if [task["ids"][i] for i in task["test"]] != list(ids):
            raise RuntimeError("test set differs")
        pid = paths[(paths.path == "C1-selected") & (paths.cluster == r) & (paths.learner == f)].sort_values("query").sim_id.astype(str).tolist()
        ev, chk, ok = replay(task, M, pid, {int(b): Pm[i] for i, b in enumerate(bs)})
        return {"repeat": r, "fold": f, "test_ids": list(ids), "paid_ids": pid, "evals": ev, "check_p_vs_recorded_maxabs": chk, "path_reproduced": bool(ok)}
    d = OUT / job
    RC.run_units([n for n, _ in U_], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


def summary():
    """Attribution of the C1 decision flips at b -> b + 1 (b >= 24) to re-estimation (HYP), depth change (CLF) and weight switching (W)."""
    M = P.manifest(); y_all = M.y.astype(int); rows = []; drift = []
    for fp in sorted((OUT / "c1s-trace" / "units").glob("*.json.gz")):
        u = RC.read_json_gz(fp); y = y_all.reindex(u["test_ids"]).to_numpy(int)
        ev = {e["budget"]: e for e in u["evals"]}
        for b in range(24, 60):
            e0, e1 = ev[b], ev[b + 1]; p0, p1 = np.asarray(e0["p"]) >= 0.5, np.asarray(e1["p"]) >= 0.5
            hyp, clf, w = np.asarray(e1["p_HYP"]) >= 0.5, np.asarray(e1["p_CLF"]) >= 0.5, np.asarray(e1["p_W"]) >= 0.5
            fl = p1 != p0; corr0 = p0 == (y == 1); corr1 = p1 == (y == 1); harm = corr0 & ~corr1
            th0, th1 = np.asarray(e0["rec_full"]["theta"]), np.asarray(e1["rec_full"]["theta"])
            rows.append({"repeat": u["repeat"], "fold": u["fold"], "b": b, "n_flip": int(fl.sum()), "n_harm": int(harm.sum()),
                         "flip_also_without_reestimation": int((fl & (hyp != p0)).sum()), "flip_caused_by_reestimation": int((fl & (hyp == p0)).sum()),
                         "flip_from_depth_change_alone": int((fl & (clf != p0)).sum()), "flip_needs_classifier_refit": int((fl & (clf == p0)).sum()),
                         "flip_caused_by_weight_switch": int((fl & (w == p0)).sum()),
                         "harm_caused_by_reestimation": int((harm & (hyp == p0)).sum()), "harm_needs_classifier_refit": int((harm & (clf == p0)).sum()),
                         "harm_caused_by_weight_switch": int((harm & (w == p0)).sum()),
                         "reest_only_flips": int(((hyp != p1) & (p1 != p0)).sum()),
                         "dtheta_max": float(np.max(np.abs(th1 - th0))), "start_switch": bool(e0["rec_full"]["start"] != e1["rec_full"]["start"]),
                         "dmu": float(e1["rec_full"]["mu"] - e0["rec_full"]["mu"]), "dsd_rel": float(e1["rec_full"]["sd"] / e0["rec_full"]["sd"] - 1),
                         "w_TV": float(0.5 * np.abs(np.asarray(e1["w"]) - np.asarray(e0["w"])).sum()), "w_argmax_switch": bool(np.argmax(e1["w"]) != np.argmax(e0["w"])),
                         "dE_test_med": float(np.median(np.abs(np.asarray(e1["E_test"]) - np.asarray(e0["E_test"]))))})
        drift.append({"repeat": u["repeat"], "fold": u["fold"], "check": u["check_p_vs_recorded_maxabs"], "path_ok": u["path_reproduced"]})
    R = pd.DataFrame(rows); D = pd.DataFrame(drift)
    tot = R[["n_flip", "n_harm"]].sum()
    res = {"learners": int(len(D)), "replay_bit_exact_all": bool((D.check == 0).all()), "replay_max_abs": float(D.check.max()), "paths_reproduced_all": bool(D.path_ok.all()),
           "steps": int(len(R)), "flips": int(tot.n_flip), "harmful": int(tot.n_harm),
           "share_flips_caused_by_reestimation": float(R.flip_caused_by_reestimation.sum() / max(1, tot.n_flip)),
           "share_harm_caused_by_reestimation": float(R.harm_caused_by_reestimation.sum() / max(1, tot.n_harm)),
           "share_flips_from_depth_change_alone": float(R.flip_from_depth_change_alone.sum() / max(1, tot.n_flip)),
           "share_flips_needing_classifier_refit": float(R.flip_needs_classifier_refit.sum() / max(1, tot.n_flip)),
           "share_harm_needing_classifier_refit": float(R.harm_needs_classifier_refit.sum() / max(1, tot.n_harm)),
           "share_flips_caused_by_weight_switch": float(R.flip_caused_by_weight_switch.sum() / max(1, tot.n_flip)),
           "share_harm_caused_by_weight_switch": float(R.harm_caused_by_weight_switch.sum() / max(1, tot.n_harm)),
           "reestimation_only_flips_per_step": float(R.reest_only_flips.mean()),
           "start_switch_share": float(R.start_switch.mean()), "dtheta_max_median": float(R.dtheta_max.median()), "dtheta_max_p90": float(R.dtheta_max.quantile(0.9)),
           "dmu_abs_median": float(R.dmu.abs().median()), "dsd_rel_abs_median": float(R.dsd_rel.abs().median()), "w_TV_median": float(R.w_TV.median()),
           "w_argmax_switch_share": float(R.w_argmax_switch.mean()), "dE_test_median": float(R.dE_test_med.median()),
           "harm_steps_vs_others": {k: [float(R[R.n_harm > 0][k].mean()), float(R[R.n_harm == 0][k].mean())] for k in ("dtheta_max", "w_TV", "dE_test_med")}}
    R.to_csv(OUT / "diag" / "trace_steps.csv.gz", index=False, compression="gzip"); (OUT / "diag" / "TRACE_SUMMARY.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return res


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "summary":
        print(json.dumps(summary(), indent=1, default=float))
