"""Week 14 Study 2 — rare-regime generalization and campaign transfer (CONTROLLED SYNTHETIC).

Families (u in [0,1]^4 with roles (log P, log VX, log LS, ST); OLD and NEW boxes as in Week 13):
  twoRegime  monotone; physics law s(u) in the bulk, boundary rotates to a VX-like threshold in
             the high-P / small-LS corner (the NEW-like oblique boundary)
  bump       Week 13 localized deviation (violates monotonicity in P near the corner)
  stShift    monotone in (P+, VX-, LS-, ST+); ST matters and NEW doubles the ST range, so the
             frozen ST-free order O3 is violated
Settings:
  transfer   train on all 405 OLD-like cases, test on an independent NEW-like pool (136) + dense truth
  target40 / target80   train on 40 / 80 random NEW-like cases (both classes required)
  indomain80 train on 80 OLD-like cases, test on OLD-like (sanity: order use must not hurt in-domain)
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.optimize import brentq
from scipy.spatial import cKDTree
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from src.week13_boundary_metrics import edge_metrics, gabriel_edges
from src.week14_models import fit_model
from src.week14_order import SIGNS_O3

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week14_research_program/synthetic/transfer"
OLD_BOX = (np.array([0, 0, 0, 0.]), np.array([1, 1, 1, .5]))
NEW_BOX = (np.array([.8, 0, 0, 0.]), np.array([1, 1, .2, 1]))
W = np.array([2.2, -.8, -1.2, 0.])
CORNER = np.array([.9, .95, .1, .5]); CSCALE = np.array([.35, .12, .35, 10.])
import os
SIGMA = float(os.environ.get("W14_SIGMA", "0.5"))
ALL_FAMILIES = ("twoRegime", "bump", "stShift", "curvedMono", "hartmannDev", "twoRegimeST")


def s_phys(u):
    return u @ W


def latent(u, fam, par):
    s = s_phys(u)
    if fam == "twoRegime":
        return np.minimum(4 * (s - par["c"]), 8 * (par["v"] - u[:, 1]))
    if fam == "bump":
        return 4 * (s - par["c"]) - 1.5 * np.exp(-.5 * (((u - CORNER) / CSCALE) ** 2).sum(1))
    if fam == "stShift":
        return 4 * (s - par["c"]) + 3.0 * (u[:, 3] - .25)
    # ---- held-out families (defined before the Week 14 freeze; never used in development)
    if fam == "curvedMono":      # monotone; the VX-like exponent grows with P (orientation drifts)
        return 4 * (2.2 * u[:, 0] - (.8 + par["a"] * np.maximum(u[:, 0] - .5, 0)) * u[:, 1] - 1.2 * u[:, 2] - par["c"])
    if fam == "hartmannDev":     # non-monotone multi-peak deviation (Hartmann-3 shape) inside the NEW box
        A = np.array([[3, 10, 30], [.1, 10, 35], [3, 10, 30], [.1, 10, 35.]])
        Pm = 1e-4 * np.array([[3689, 1170, 2673], [4699, 4387, 7470], [1091, 8732, 5547], [381, 5743, 8828.]])
        al = np.array([1, 1.2, 3, 3.2])
        x = np.c_[(u[:, 0] - .8) / .2, u[:, 1], u[:, 2] / .2].clip(0, 1)
        hart = (al * np.exp(-((A[None] * (x[:, None, :] - Pm[None]) ** 2).sum(2)))).sum(1)
        inside = ((u[:, 0] >= .8) & (u[:, 2] <= .2)).astype(float)
        return 4 * (s - par["c"]) - par["A"] * hart * inside
    if fam == "twoRegimeST":     # two-regime boundary whose VX threshold also depends on ST (O3 violated mildly)
        return np.minimum(4 * (s - par["c"]), 8 * (par["v"] - u[:, 1]) + 2.0 * (u[:, 3] - .5))
    raise ValueError(fam)


def sample(box, n, rng):
    return box[0] + (box[1] - box[0]) * rng.random((n, 4))


def calibrate(fam):
    rng = np.random.default_rng(99)
    uo, un = sample(OLD_BOX, 200000, rng), sample(NEW_BOX, 200000, rng)
    if fam == "twoRegime":
        # v: 9% rare in NEW from the VX regime; c: 18% class 1 in OLD
        par = {"c": 0.8, "v": 0.9}
        for _ in range(4):
            par["v"] = brentq(lambda v: (latent(un, fam, {**par, "v": v}) > 0).mean() - .91, .3, 1.5)
            par["c"] = brentq(lambda c: (latent(uo, fam, {**par, "c": c}) > 0).mean() - .18, -3, 3)
        return par
    if fam in ("curvedMono", "hartmannDev"):
        key = "a" if fam == "curvedMono" else "A"
        par = {"c": 0.8, key: 1.0}
        for _ in range(4):
            par[key] = brentq(lambda v: (latent(un, fam, {**par, key: v}) > 0).mean() - .91, 0.0, 60.0)
            par["c"] = brentq(lambda c: (latent(uo, fam, {**par, "c": c}) > 0).mean() - .18, -3, 3)
        return par
    if fam == "twoRegimeST":
        par = {"c": 0.8, "v": 0.9}
        for _ in range(4):
            par["v"] = brentq(lambda v: (latent(un, fam, {**par, "v": v}) > 0).mean() - .91, .3, 1.5)
            par["c"] = brentq(lambda c: (latent(uo, fam, {**par, "c": c}) > 0).mean() - .18, -3, 3)
        return par
    par = {"c": brentq(lambda c: (latent(uo, fam, {"c": c}) > 0).mean() - .18, -3, 3)}
    return par


class Dense:
    def __init__(self, box, fam, par, n=20000, k=8):
        rng = np.random.default_rng(5)
        self.u = sample(box, n, rng)
        self.z = (self.u - box[0]) / (box[1] - box[0])
        self.y = (latent(self.u, fam, par) > 0).astype(int)
        _, nn = cKDTree(self.z).query(self.z, k=k + 1)
        self.nn = nn[:, 1:]
        self.tb = (self.y[self.nn] != self.y[:, None]).any(1)
        self.tree = cKDTree(self.z[self.tb])

    def metrics(self, yhat):
        pb = (yhat[self.nn] != yhat[:, None]).any(1)
        out = {"dense_BA": float((np.mean(yhat[self.y == 1] == 1) + np.mean(yhat[self.y == 0] == 0)) / 2)}
        if not pb.any():
            out.update({"NSD_0.1": 0.0, "ASSD": 2.0})
            return out
        a = cKDTree(self.z[pb]).query(self.z[self.tb])[0]
        b = self.tree.query(self.z[pb])[0]
        out["NSD_0.1"] = float(((a <= .1).sum() + (b <= .1).sum()) / (len(a) + len(b)))
        out["ASSD"] = float((a.sum() + b.sum()) / (len(a) + len(b)))
        return out


DENSE = {}


def run(fam, setting, rep, models):
    par = PARS[fam]
    rng = np.random.default_rng([41, ALL_FAMILIES.index(fam), ("transfer", "target40", "target80", "indomain80").index(setting), rep])
    test_box = OLD_BOX if setting == "indomain80" else NEW_BOX
    key = (fam, setting == "indomain80")
    if key not in DENSE:
        DENSE[key] = Dense(test_box, fam, par)
    dense = DENSE[key]
    ue = sample(test_box, 136 if test_box is NEW_BOX else 405, rng)
    ye = (latent(ue, fam, par) + SIGMA * rng.standard_normal(len(ue)) > 0).astype(int)
    if setting == "transfer":
        ut = sample(OLD_BOX, 405, rng)
    else:
        nt = 40 if setting == "target40" else 80
        while True:
            ut = sample(test_box, nt, rng)
            yt_try = (latent(ut, fam, par) + SIGMA * rng.standard_normal(nt) > 0).astype(int)
            if 0 < yt_try.mean() < 1:
                break
    yt = yt_try if setting != "transfer" else (latent(ut, fam, par) + SIGMA * rng.standard_normal(len(ut)) > 0).astype(int)
    minority = int(ye.mean() > .5) ^ 1
    edges = gabriel_edges(StandardScaler().fit_transform(ue))
    rows = []
    for mname in models:
        try:
            f = fit_model(mname, ut, yt, s_phys(ut), SIGNS_O3, virtual_points=ue, seed=rep)
            p = f.predict(ue, s_phys(ue))
            yh = (p >= .5).astype(int)
            pdz = f.predict(dense.u, s_phys(dense.u))
            r = {"family": fam, "setting": setting, "rep": rep, "model": mname, "ok": True,
                 "n_train": len(yt), "train_minority": int((yt == minority).sum()), "eval_minority": int((ye == minority).sum()),
                 "BA": float((np.mean(yh[ye == 1] == 1) + np.mean(yh[ye == 0] == 0)) / 2) if 0 < ye.mean() < 1 else np.nan,
                 "minority_recall": float(np.mean(yh[ye == minority] == minority)) if (ye == minority).any() else np.nan,
                 "AUC": float(roc_auc_score(ye, p)) if 0 < ye.mean() < 1 else np.nan,
                 "accuracy": float(np.mean(yh == ye))}
            r.update({k: v for k, v in edge_metrics(edges, ye, yh).items() if k in ("BER", "BEF1")})
            r.update(dense.metrics((pdz >= .5).astype(int)))
            r.update({f"info_{k}": json.dumps(v) if isinstance(v, list) else v for k, v in f.info.items()})
        except Exception as exc:  # retained, never silently dropped
            r = {"family": fam, "setting": setting, "rep": rep, "model": mname, "ok": False, "error": repr(exc)[:300]}
        rows.append(r)
    return rows


PARS = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=12)
    ap.add_argument("--tag", default="development")
    ap.add_argument("--families", default="twoRegime,bump,stShift")
    ap.add_argument("--settings", default="transfer,target40,target80,indomain80")
    ap.add_argument("--models", default="H,M3,G3,GR,GRS,MG,GRC")
    ap.add_argument("--jobs", type=int, default=7)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for fam in a.families.split(","):
        PARS[fam] = calibrate(fam)
    (OUT / f"calibration_{a.tag}.json").write_text(json.dumps(PARS, indent=2))
    jobs = [(f, s, r) for r in range(a.reps) for f in a.families.split(",") for s in a.settings.split(",")]
    res = Parallel(n_jobs=a.jobs, verbose=2)(delayed(_run_with_pars)(f, s, r, a.models.split(","), PARS) for f, s, r in jobs)
    df = pd.DataFrame([x for rows in res for x in rows])
    df.to_csv(OUT / f"transfer_{a.tag}.csv", index=False)
    cols = ["BA", "minority_recall", "AUC", "BEF1", "NSD_0.1", "ASSD"]
    print(df[df.ok].groupby(["family", "setting", "model"])[cols].mean().round(3).to_string())
    print("failures:", int((~df.ok).sum()))


def _run_with_pars(f, s, r, models, pars):
    PARS.update(pars)
    return run(f, s, r, models)


if __name__ == "__main__":
    main()
