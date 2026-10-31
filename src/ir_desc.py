"""IR part A (PROTOCOL_IR.md section 3): correlation structure of the physical outputs with depth, width-depth physics and label
information beyond depth. DESCRIPTIVE, evaluator view (all runs, true values); no learner, no budget.
    python -m src.ir_desc run
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import json
import sys
import time
import warnings

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr, theilslopes
from scipy.stats import t as tdist
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, log_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

import src.ea_cand as EC
import src.ir_data as IRD
import src.rc18_common as RC
import src.rc19_pool as P

OUT = IRD.OUT / "descriptive"
SEED = 31
NBOOT = 2000
NREP = 20
# variable name -> (label, column builder); all on the scale used in the thesis models (log for positive extensive quantities)
VARS = {
    "D": "log depth A (active max)",
    "W_A": "log width (active max)", "W_T0": "log width (T0 median)", "W_atA": "log width at max-depth row", "L_A": "log length (active max)",
    "KE": "log kinetic energy (T0)", "T": "max temperature (T0)", "SPK": "velocity spike ratio", "SPT": "velocity spike time",
    "LAS": "absorbed laser power (T0)", "ETOT": "log total energy (T0)", "NPART": "log melt particles (T0)",
    "KE_A": "log kinetic energy (active max)", "T_A": "max temperature (active max)", "V_A": "log max velocity (active max)",
    "H": "log h (input formula)"}
T0_OUT = ("KE", "T", "SPK", "SPT", "LAS", "ETOT", "NPART")


def table():
    M = P.manifest(); G = IRD.geometry().reindex(M.index)
    lx = np.log(M[list(P.INPUTS)].to_numpy(float))
    X = pd.DataFrame(index=M.index)
    X["y"] = M.y.astype(int); X["batch"] = M.source_batch.astype(str); X["short"] = M.short_record.astype(bool)
    X["D"] = M.log_A_um.astype(float)
    X["W_A"] = np.log(G.W_A_um); X["W_T0"] = np.log(G.W_T0_um); X["W_atA"] = np.log(G.W_atA_um); X["L_A"] = np.log(G.L_A_um)
    X["KE"] = M.log_ke_T0_nJ; X["T"] = M.tmax_T0_K; X["SPK"] = M.vmax_spike_logratio; X["SPT"] = M.vmax_spike_us; X["LAS"] = M.laser_T0_W
    X["ETOT"] = M.log_etot_T0_J; X["NPART"] = M.log_npart_T0
    X["KE_A"] = np.log(G.KE_A_max.where(G.KE_A_max > 0)); X["T_A"] = G.T_A_max; X["V_A"] = np.log(G.V_A_max.where(G.V_A_max > 0))
    X["H"] = lx[:, 0] - 0.5 * lx[:, 1] - 1.5 * lx[:, 2]
    for j, c in enumerate(P.INPUTS):
        X[f"log_{c}"] = lx[:, j]
    from src.external_validation.analysis import boundary_flags
    ids = M.index.to_numpy(str); X["q20_pooled"] = boundary_flags(M[list(P.INPUTS)].to_numpy(float), M.y.to_numpy(int), np.arange(len(M)), ids, "entire_evaluation_batch")[20]
    X = X.replace([np.inf, -np.inf], np.nan)
    return X


def _boot_rho(a, b, rng, nb=NBOOT):
    n = len(a); r0 = float(spearmanr(a, b).statistic); bs = np.empty(nb)
    for k in range(nb):
        i = rng.integers(0, n, n); bs[k] = np.corrcoef(rankdata(a[i]), rankdata(b[i]))[0, 1]
    return r0, float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))


def a1(X):
    good = ~X.short; rows = []; rng = np.random.default_rng(SEED)
    subsets = {"all": good, "conduction": good & (X.y == 0), "keyhole": good & (X.y == 1), "OLD": good & (X.batch == "OLD"), "NEW": good & (X.batch == "NEW"),
               "boundary_q20": good & X.q20_pooled}
    for sub, m0 in subsets.items():
        for v in VARS:
            if v == "D":
                continue
            m = m0 & X.D.notna() & X[v].notna()
            if m.sum() < 10:
                continue
            r, lo, hi = _boot_rho(X.D[m].to_numpy(), X[v][m].to_numpy(), rng)
            rows.append({"subset": sub, "var": v, "label": VARS[v], "n": int(m.sum()), "rho": r, "lo95": lo, "hi95": hi})
    full = X.loc[good, list(VARS)].corr(method="spearman", min_periods=50)
    return pd.DataFrame(rows), full


def _resid(v, Z):
    Z1 = np.c_[np.ones(len(Z)), Z]; b, *_ = np.linalg.lstsq(Z1, v, rcond=None); return v - Z1 @ b


def _gp_oof(X, v, folds):
    """Out-of-fold mean of variable v from the C1-style GP (h trend, Matern 3/2 ARD, C1 MAP prior, 2 starts) on all good runs."""
    good = (~X.short) & X[v].notna(); idx = np.flatnonzero(good.to_numpy()); lx = X[[f"log_{c}" for c in P.INPUTS]].to_numpy(float)
    Z = (lx - lx.mean(0)) / lx.std(0); h = X.H.to_numpy(float); hs = ((h - h.mean()) / h.std())[:, None]; y = X[v].to_numpy(float)
    pred = np.full(len(X), np.nan)
    for k in range(folds.max() + 1):
        tr = idx[folds[idx] != k]; te = idx[folds[idx] == k]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            g = EC.gp_fit(Z[tr], y[tr], hs[tr], np.ones(len(tr)), "phys", True, EC.STARTS)
        pred[te] = g.predict(Z[te], Hs=hs[te])[0]
    return y - pred, pred


def a2(X):
    good = (~X.short) & X.D.notna(); rows = []; Zin = X[[f"log_{c}" for c in P.INPUTS]].to_numpy(float)
    folds = np.random.default_rng(SEED).permutation(len(X)) % 10
    res = {}; t0 = time.time()
    import concurrent.futures
    with concurrent.futures.ProcessPoolExecutor(max_workers=3) as ex:                 # 3 single-thread workers (PROTOCOL_IR section 11)
        fut = {v: ex.submit(_gp_oof, X, v, folds) for v in VARS if v != "H"}
        for v, f in fut.items():
            res[v], _ = f.result()
            print(json.dumps({"gp_oof": v, "s": round(time.time() - t0, 1)}), flush=True)
    R = pd.DataFrame(res, index=X.index)
    for v in VARS:
        if v in ("D",):
            continue
        m = good & X[v].notna()
        a, b = X.D[m].to_numpy(), X[v][m].to_numpy(); ra, rb = rankdata(a), rankdata(b)
        row = {"var": v, "label": VARS[v], "n": int(m.sum()), "rho_raw": float(spearmanr(a, b).statistic)}
        if v != "H":
            row["partial_rank_given_log_h"] = float(np.corrcoef(_resid(ra, X.H[m].to_numpy()[:, None]), _resid(rb, X.H[m].to_numpy()[:, None]))[0, 1])
        row["partial_rank_given_4_log_inputs"] = float(np.corrcoef(_resid(ra, Zin[m.to_numpy()]), _resid(rb, Zin[m.to_numpy()]))[0, 1])
        if v != "H":
            mr = m & R[v].notna() & R["D"].notna(); ea, eb = R.D[mr].to_numpy(), R[v][mr].to_numpy()
            row["gp_oof_resid_pearson"] = float(np.corrcoef(ea, eb)[0, 1]); row["gp_oof_resid_spearman"] = float(spearmanr(ea, eb).statistic)
            row["gp_oof_R2_of_var"] = float(1 - np.sum(eb ** 2) / np.sum((X[v][mr] - X[v][mr].mean()) ** 2))
        rows.append(row)
    D = R["D"][good & R.D.notna()]; r2d = float(1 - np.sum(D ** 2) / np.sum((X.D[D.index] - X.D[D.index].mean()) ** 2))
    Rc = R[[c for c in R.columns]].loc[~X.short].corr(method="pearson", min_periods=50)
    return pd.DataFrame(rows), Rc, {"gp_oof_R2_depth": r2d}, R


def a3(X):
    good = (~X.short) & X.D.notna() & X.W_A.notna(); out = {}
    A = np.exp(X.D[good]); W = np.exp(X.W_A[good]); y = X.y[good].to_numpy()
    for cls, lab in ((0, "conduction"), (1, "keyhole")):
        m = y == cls; s = theilslopes(np.log(A[m]), np.log(W[m]))
        out[f"theil_sen_logA_on_logW_{lab}"] = {"slope": float(s.slope), "lo95": float(s.low_slope), "hi95": float(s.high_slope), "n": int(m.sum())}
        ar = (A[m] / W[m]).to_numpy(); out[f"aspect_D_over_W_{lab}"] = {"median": float(np.median(ar)), "q25": float(np.percentile(ar, 25)), "q75": float(np.percentile(ar, 75)),
                                                                        "min": float(ar.min()), "max": float(ar.max())}
    wd = (W / A).to_numpy()
    for c in (1.5, 2.0, 2.5):
        hat = wd <= c; sens = float(hat[y == 1].mean()); spec = float((~hat[y == 0]).mean())
        out[f"criterion_W_over_D_le_{c}"] = {"BA": 0.5 * (sens + spec), "sensitivity": sens, "specificity": spec}
    feats = {"log(D/W)": np.log(A / W).to_numpy(), "log D": np.log(A).to_numpy(), "log W": np.log(W).to_numpy()}
    for nm, f in feats.items():
        auc = roc_auc_score(y, f); bas = []
        for rep in range(NREP):
            for tr, te in StratifiedKFold(10, shuffle=True, random_state=rep).split(f, y):
                th = _best_threshold(f[tr], y[tr], auc >= 0.5); hat = (f[te] >= th) if auc >= 0.5 else (f[te] <= th)
                bas.append(0.5 * (hat[y[te] == 1].mean() + (~hat[y[te] == 0]).mean()))
        out[f"cv_threshold_{nm}"] = {"AUC_full_sample": float(max(auc, 1 - auc)), "CV_BA_mean": float(np.mean(bas))}
    out["n"] = int(good.sum()); return out


def _best_threshold(f, y, up):
    s = np.sort(np.unique(f)); cand = (s[:-1] + s[1:]) / 2 if len(s) > 1 else s; best, bt = -1, cand[0]
    for c in cand:
        hat = (f >= c) if up else (f <= c); ba = 0.5 * (hat[y == 1].mean() + (~hat[y == 0]).mean())
        if ba > best:
            best, bt = ba, c
    return bt


def _cv(Xm, y, model="lr", reps=NREP):
    ll, ba, au = [], [], []
    for rep in range(reps):
        p = np.zeros(len(y))
        for tr, te in StratifiedKFold(10, shuffle=True, random_state=rep).split(Xm, y):
            if model == "lr":
                mdl = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=5000))
            elif model == "poly":
                mdl = make_pipeline(StandardScaler(), PolynomialFeatures(2, include_bias=False), StandardScaler(), LogisticRegression(C=1.0, max_iter=5000))
            else:
                mdl = HistGradientBoostingClassifier(max_depth=3, max_iter=200, learning_rate=0.05, early_stopping=False, random_state=rep)
            mdl.fit(Xm[tr], y[tr]); p[te] = mdl.predict_proba(Xm[te])[:, 1]
        p = np.clip(p, 1e-12, 1 - 1e-12); ll.append(log_loss(y, p)); ba.append(balanced_accuracy_score(y, p >= 0.5)); au.append(roc_auc_score(y, p))
    return np.array(ll), np.array(ba), np.array(au)


def _tci(d):
    d = np.asarray(d, float); n = len(d); m = float(d.mean()); se = float(d.std(ddof=1) / np.sqrt(n)); q = float(tdist.ppf(0.975, n - 1))
    return {"mean": m, "lo95": m - q * se, "hi95": m + q * se}


def a4(X):
    others = [v for v in VARS if v not in ("D", "H")]
    need = ["D", "H"] + others
    good = (~X.short) & X[need].notna().all(axis=1); y = X.y[good].to_numpy(int); F = X.loc[good]
    sets = {"[h]": ["H"], "[D]": ["D"], "[h, D]": ["H", "D"]}
    for v in others:
        sets[f"[h, D, {v}]"] = ["H", "D", v]; sets[f"[h, {v}]"] = ["H", v]; sets[f"[{v}]"] = [v]
    sets["[h, D, all T0 outputs]"] = ["H", "D", *T0_OUT]; sets["[h, D, W_A, all T0 outputs]"] = ["H", "D", "W_A", *T0_OUT]
    res = {}; base = None
    for nm, cs in sets.items():
        ll, ba, au = _cv(F[cs].to_numpy(float), y)
        res[nm] = {"logloss": ll, "BA": ba, "AUC": au}
    base = res["[h, D]"]; rows = []
    for nm, r in res.items():
        row = {"set": nm, "logloss": float(r["logloss"].mean()), "BA": float(r["BA"].mean()), "AUC": float(r["AUC"].mean())}
        if nm != "[h, D]":
            for k in ("logloss", "BA", "AUC"):
                c = _tci(r[k] - base[k]); row[f"d_{k}_vs_hD"] = c["mean"]; row[f"d_{k}_lo95"] = c["lo95"]; row[f"d_{k}_hi95"] = c["hi95"]
        rows.append(row)
    gb = []
    llb, bab, aub = _cv(F[["H", "D"]].to_numpy(float), y, "hgb")
    for v in ("W_A", "KE", "T"):
        ll, ba, au = _cv(F[["H", "D", v]].to_numpy(float), y, "hgb")
        gb.append({"set": f"HGB [h, D, {v}] - [h, D]", **{f"d_{k}": _tci(a - b) for k, a, b in (("logloss", ll, llb), ("BA", ba, bab), ("AUC", au, aub))}})
    gb.append({"set": "HGB [h, D] level", "logloss": float(llb.mean()), "BA": float(bab.mean()), "AUC": float(aub.mean())})
    # width-only sets on the larger width sample (reported extra)
    gw = (~X.short) & X[["H", "D", "W_A"]].notna().all(axis=1); yw = X.y[gw].to_numpy(int); ext = []
    lb, bb, ab = _cv(X.loc[gw, ["H", "D"]].to_numpy(float), yw)
    for nm, cs in (("[h, D, W_A]", ["H", "D", "W_A"]), ("[h, W_A]", ["H", "W_A"]), ("[W_A]", ["W_A"]), ("[h]", ["H"]), ("[D]", ["D"])):
        ll, ba, au = _cv(X.loc[gw, cs].to_numpy(float), yw)
        ext.append({"set": nm, "n": int(gw.sum()), "logloss": float(ll.mean()), "BA": float(ba.mean()), "AUC": float(au.mean()), "d_logloss_vs_hD": _tci(ll - lb), "d_BA_vs_hD": _tci(ba - bb)})
    return pd.DataFrame(rows), gb, ext, int(good.sum()), float(y.mean())


def a5(X):
    inp = [f"log_{c}" for c in P.INPUTS]; good = (~X.short) & X[inp + ["D", "W_A"]].notna().all(axis=1); y = X.y[good].to_numpy(int); F = X.loc[good]; out = []
    for nm, cs, mdl in (("[4 log inputs]", inp, "lr"), ("[4 log inputs, quadratic + pairwise]", inp, "poly"), ("[D]", ["D"], "lr"), ("[h, D]", ["H", "D"], "lr"),
                        ("[inputs, D]", inp + ["D"], "lr"), ("[inputs, D, W_A]", inp + ["D", "W_A"], "lr"), ("[inputs quadratic, D]", inp + ["D"], "poly")):
        ll, ba, au = _cv(F[cs].to_numpy(float), y, mdl)
        out.append({"set": nm, "model": mdl, "n": int(good.sum()), "logloss": float(ll.mean()), "logloss_sd_over_repeats": float(ll.std(ddof=1)), "BA": float(ba.mean()), "AUC": float(au.mean())})
    return out


def run():
    RC.limit_threads(1); OUT.mkdir(parents=True, exist_ok=True); t0 = time.time(); X = table()
    X.to_csv(OUT / "analysis_table.csv", lineterminator="\n")
    A1, full = a1(X); A1.to_csv(OUT / "A1_spearman_with_depth.csv", index=False, lineterminator="\n"); full.to_csv(OUT / "A1_spearman_matrix.csv", lineterminator="\n")
    print(json.dumps({"A1": "done", "s": round(time.time() - t0, 1)}), flush=True)
    A2, Rc, a2info, R = a2(X); A2.to_csv(OUT / "A2_beyond_inputs.csv", index=False, lineterminator="\n"); Rc.to_csv(OUT / "A2_gp_residual_corr_matrix.csv", lineterminator="\n")
    R.to_csv(OUT / "A2_gp_oof_residuals.csv", lineterminator="\n")
    A3 = a3(X); A4, gb, ext, n4, prev = a4(X); A4.to_csv(OUT / "A4_label_information.csv", index=False, lineterminator="\n"); A5 = a5(X)
    res = {"evidence": "DESCRIPTIVE (evaluator view, all runs, true values)", "seconds": round(time.time() - t0, 1), "A2_info": a2info, "A3": A3,
           "A4_common_sample_n": n4, "A4_keyhole_share": prev, "A4_hgb_check": gb, "A4_width_sample_extra": ext, "A5_mediation": A5,
           "n_good_records": int((~X.short).sum()), "n_short": int(X.short.sum())}
    (OUT / "PART_A_RESULTS.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("seconds", "A2_info", "A4_common_sample_n")}, default=float)); return res


if __name__ == "__main__":
    {"run": run}[sys.argv[1]]()
