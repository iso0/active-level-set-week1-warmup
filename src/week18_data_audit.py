"""Week 18 Phase 1 — OLD/NEW compatibility and the pooled benchmark question (POST-HOC / HISTORICAL; descriptive).

1. Overlap: NEW rows inside the OLD bounding box; agreement of NEW labels with OLD-trained G3 and 5-NN predictions
   inside vs outside the box.
2. Campaign effect under a flexible model: pooled GPC on [x4] (G3) vs [x4] + NEW random intercept
   (k = a² Matérn-ARD(x4) + s_c² c c′, c = 1 for NEW) vs + NEW-specific residual surface; ML-II evidence and
   5-fold CV (stratified by campaign × class, 4 repeats) per-campaign BA / AUC / log loss.
3. "Level shift" vs region: physics-only logistic thresholds in log h fitted on OLD, NEW, and NEW-in-overlap.
4. Settings groups: OLD standard settings (TE 0.0021 s, XI 0.0002) vs non-standard runs.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.gaussian_process.kernels import ConstantKernel, DotProduct, Matern
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler

import src.week17_models as M
from src.week17_audit_impact import SafeguardedFixedMeanLaplaceGPC

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week18_independent_research/phase1"
F = ["P", "VX", "LS", "ST"]


def load():
    from src.week12_development_common import load_new, load_old
    o, n = load_old(), load_new()
    g = lambda s, k: re.search(k + r"-([^_]+)", s).group(1)
    for d in (o, n):
        d["TE"] = d.sim_id.map(lambda s: g(s, "TE")); d["XI"] = d.sim_id.map(lambda s: g(s, "XI"))
        d["DTr"] = d.sim_id.map(lambda s: float(g(s, "DT").replace("p", "."))) * d.VX / d.LS
    o["campaign"] = 0; n["campaign"] = 1
    o["standard"] = (o.TE == "0p0021") & (o.XI == "0p0002"); n["standard"] = True
    D = pd.concat([o, n], ignore_index=True)
    D["y"] = D.has_keyhole.astype(int)
    D["logh"] = np.log(D.P) - .5 * np.log(D.VX) - 1.5 * np.log(D.LS)
    return D


def kernel(kind):
    base = ConstantKernel(1.0, M.AMP) * M.Proj(Matern(np.ones(4), M.LEN, nu=1.5), [0, 1, 2, 3])
    if kind == "G3":
        return base
    off = ConstantKernel(1.0, M.AMP) * M.Proj(DotProduct(sigma_0=0.0, sigma_0_bounds="fixed"), [4])
    if kind == "offset":
        return base + off
    if kind == "offset_resid":
        # NEW-specific residual surface: c c' x Matérn(x4) (product of indicator kernel and a second Matérn)
        res = ConstantKernel(1.0, M.AMP) * M.Proj(DotProduct(sigma_0=0.0, sigma_0_bounds="fixed"), [4]) * M.Proj(Matern(np.ones(4), M.LEN, nu=1.5), [0, 1, 2, 3])
        return base + off + res
    raise ValueError(kind)


def fit_pooled(X, c, y, kind):
    sc = StandardScaler().fit(X)
    Z = np.c_[sc.transform(X), c]
    gp = SafeguardedFixedMeanLaplaceGPC(kernel(kind), optimize=True).fit(Z, y, np.zeros(len(y)))
    return gp, sc


def predict(gp, sc, X, c):
    return gp.predict_proba(np.c_[sc.transform(X), c], np.zeros(len(X)))[:, 1]


def metrics(y, p):
    p = np.clip(p, 1e-9, 1 - 1e-9); yh = (p >= .5).astype(int)
    ba = (np.mean(yh[y == 1] == 1) + np.mean(yh[y == 0] == 0)) / 2 if len(set(y)) == 2 else np.nan
    return {"BA": ba, "AUC": roc_auc_score(y, p) if len(set(y)) == 2 else np.nan, "logloss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
            "minority_recall": float(np.mean(yh[y == int(y.mean() < .5)] == int(y.mean() < .5)))}


def cv_job(D, rep, fold, kind, subset):
    from threadpoolctl import threadpool_limits
    d = D if subset == "all" else D[D.standard].reset_index(drop=True)
    strat = d.campaign * 2 + d.y
    rng = np.random.default_rng([1818, rep]); folds = np.zeros(len(d), int)
    for s in np.unique(strat):
        idx = np.flatnonzero(strat == s); rng.shuffle(idx); folds[idx] = np.arange(len(idx)) % 5
    te = folds == fold; tr = ~te
    X = d[F].to_numpy(float); c = d.campaign.to_numpy(float); y = d.y.to_numpy(int)
    with threadpool_limits(1):
        if kind == "transfer_OLDonly":
            m = tr & (c == 0); gp, sc = fit_pooled(X[m], c[m], y[m], "G3")
        elif kind == "NEWonly":
            m = tr & (c == 1); gp, sc = fit_pooled(X[m], c[m], y[m], "G3")
        else:
            gp, sc = fit_pooled(X[tr], c[tr], y[tr], kind)
        p = predict(gp, sc, X[te], c[te])
    rows = []
    for camp in (0, 1):
        mm = c[te] == camp
        rows.append({"rep": rep, "fold": fold, "model": kind, "subset": subset, "campaign": "NEW" if camp else "OLD",
                     "idx": ",".join(map(str, np.flatnonzero(te)[mm])), "p": ",".join(f"{v:.6g}" for v in p[mm]),
                     "lml": float(gp.log_marginal_likelihood_value_), "fp": float(gp.mode_fp_)})
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    D = load()
    o, n = D[D.campaign == 0], D[D.campaign == 1]
    rep = {}
    # 1 overlap
    lo, hi = o[F].min().values, o[F].max().values
    inside = ((n[F].values >= lo) & (n[F].values <= hi)).all(1)
    rep["NEW_inside_OLD_box"] = int(inside.sum())
    gp, sc = fit_pooled(o[F].to_numpy(float), np.zeros(len(o)), o.y.values, "G3")
    pn = predict(gp, sc, n[F].to_numpy(float), np.zeros(len(n)))
    knn = KNeighborsClassifier(5).fit(StandardScaler().fit(o[F]).transform(o[F]), o.y)
    pk = knn.predict_proba(StandardScaler().fit(o[F]).transform(n[F]))[:, 1]
    for tag, m in (("inside", inside), ("outside", ~inside)):
        yy = n.y.values[m]
        rep[f"{tag}_n"] = int(m.sum()); rep[f"{tag}_nonKH"] = int((yy == 0).sum())
        rep[f"{tag}_agree_G3old"] = float(np.mean((pn[m] >= .5) == yy)); rep[f"{tag}_agree_5NNold"] = float(np.mean((pk[m] >= .5) == yy))
        rep[f"{tag}_nonKH_recall_G3old"] = float(np.mean(pn[m][yy == 0] < .5)) if (yy == 0).any() else np.nan
    # 3 physics threshold in log h
    def thr(d):
        s = StandardScaler().fit(d[["logh"]]); lr = LogisticRegression(C=1e6, max_iter=5000).fit(s.transform(d[["logh"]]), d.y)
        return float(s.inverse_transform([[-lr.intercept_[0] / lr.coef_[0, 0]]])[0, 0])
    rep["logh_threshold_OLD"] = thr(o); rep["logh_threshold_OLD_standard"] = thr(o[o.standard]); rep["logh_threshold_NEW"] = thr(n)
    rep["logh_threshold_NEW_inside"] = thr(n[inside]); rep["logh_threshold_NEW_outside"] = thr(n[~inside])
    oin = o[((o[F].values >= n[F].min().values) & (o[F].values <= n[F].max().values)).all(1)]
    rep["OLD_inside_NEW_box"] = int(len(oin)); rep["OLD_inside_NEW_box_KH"] = int(oin.y.sum())
    rep["logh_threshold_OLD_inside_NEW_box"] = thr(oin) if oin.y.nunique() == 2 else np.nan
    # 2 campaign effect: evidence on all data
    X = D[F].to_numpy(float); c = D.campaign.to_numpy(float); y = D.y.to_numpy(int)
    for kind in ("G3", "offset", "offset_resid"):
        g, _ = fit_pooled(X, c, y, kind); rep[f"lml_pooled_{kind}"] = float(g.log_marginal_likelihood_value_)
        if kind == "offset":
            th = np.exp(g.kernel_.theta); rep["offset_var"] = float(th[-1]); rep["offset_hypers"] = th.round(4).tolist()
    pd.Series(rep).to_csv(OUT / "compatibility_summary.csv")
    jobs = [(r, f, k, sub) for r in range(4) for f in range(5) for k in ("G3", "offset", "offset_resid", "transfer_OLDonly", "NEWonly") for sub in ("all", "standard")]
    res = Parallel(n_jobs=7, verbose=2)(delayed(cv_job)(D, *j) for j in jobs)
    R = pd.DataFrame([x for rr in res for x in rr]); R.to_csv(OUT / "pooled_cv_predictions.csv.gz", index=False)
    rows = []
    for (rp, model, sub, camp), g in R.groupby(["rep", "model", "subset", "campaign"]):
        d = D if sub == "all" else D[D.standard].reset_index(drop=True)
        idx = np.concatenate([np.array(s.split(","), int) for s in g.idx if s]); p = np.concatenate([np.array(s.split(","), float) for s in g.p if s])
        rows.append({"rep": rp, "model": model, "subset": sub, "campaign": camp, **metrics(d.y.values[idx], p)})
    S = pd.DataFrame(rows); S.to_csv(OUT / "pooled_cv_metrics.csv", index=False)
    print(pd.Series(rep).to_string())
    print(S.groupby(["subset", "campaign", "model"])[["BA", "AUC", "logloss", "minority_recall"]].mean().round(4).to_string())


if __name__ == "__main__":
    main()
