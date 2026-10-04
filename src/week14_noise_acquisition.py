"""Week 14 Study 5 — does margin sample boundary label noise, and does an epistemic criterion fix it?

Mechanism found in Study 4c: a true-objective (NSD) oracle avoids cases near the boundary, where
boundary-localized label noise concentrates; margin does the opposite.  BALD (Houlsby et al. 2011)
scores only the epistemic part of predictive uncertainty and is the standard principled answer.
This module compares random, margin and BALD (and margin restricted away from the predicted boundary
as a crude ablation) on the Week 13 generator with fixed oracle hyperparameters.
CONTROLLED SYNTHETIC; development unless a separate freeze says otherwise.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.special import ndtr
from scipy.linalg import solve_triangular

from src.week13_synthetic import DenseTruth, LaplaceGPC, matern32
from src.week13_synthetic_al import calibrated, maximin_order, noisy_labels, oracle_hypers, to_box, q20_flags

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week14_research_program/synthetic/noise_acquisition"
HYP13 = json.loads((ROOT / "outputs/week13_boundary_evaluation_and_mechanisms/synthetic/oracle_hyperparameters.json").read_text())
LN2C = np.sqrt(np.pi * np.log(2) / 2)
BUDGETS = tuple(range(16, 81, 4))


def latent_mv(gp, Z):
    ks = matern32(gp.x, Z, gp.ls, gp.var)
    mu = ks.T @ gp.resid
    v = solve_triangular(gp.L, gp.sw[:, None] * ks, lower=True)
    return mu, np.maximum(gp.var - (v * v).sum(0), 1e-12)


def bald(mu, var):
    """BALD for a logistic GPC through the probit approximation sigma(f) ~ Phi(f sqrt(pi/8))."""
    a = np.pi / 8
    m, s2 = mu * np.sqrt(a), var * a
    p = ndtr(m / np.sqrt(1 + s2))
    h = -(p * np.log2(np.clip(p, 1e-12, 1)) + (1 - p) * np.log2(np.clip(1 - p, 1e-12, 1)))
    ce = LN2C / np.sqrt(s2 + LN2C ** 2) * np.exp(-m ** 2 / (2 * (s2 + LN2C ** 2)))
    return h - ce


def run(scn, sigma, rep, n_pool=108, policies=("random", "margin", "bald")):
    sc = calibrated(scn)
    hyp = HYP[(scn, sigma)]
    rng = np.random.default_rng([14, 5, int(sigma * 10), rep, ("BAL", "OLD", "NEW").index(scn)])
    u_pool, u_eval = sc.sample(n_pool, rng), sc.sample(int(round(n_pool / .8)), rng)
    y_pool, y_eval = noisy_labels(u_pool, sc, sigma, rng), noisy_labels(u_eval, sc, sigma, rng)
    z_pool, z_eval = to_box(u_pool, sc), to_box(u_eval, sc)
    dense = DENSE.setdefault(scn, DenseTruth(sc, n=8000, seed=5))
    q = q20_flags(z_eval, y_eval)
    order = maximin_order(z_pool, np.random.default_rng([14, 5, rep]))
    start = list(order[:8]); k = 8
    while len(set(y_pool[start])) < 2:
        start.append(int(order[k])); k += 1
    rows = []
    for policy in policies:
        prng = np.random.default_rng([14, 5, rep, policies.index(policy)])
        L = list(start)
        while len(L) <= 80:
            gp = LaplaceGPC(hyp["ls"], hyp["var"]).fit(z_pool[L], y_pool[L])
            b = len(L)
            if b in BUDGETS:
                yh = (gp.latent_mean(z_eval) > 0).astype(int)
                r = {"scenario": scn, "sigma": sigma, "rep": rep, "policy": policy, "budget": b,
                     "q20_accuracy": float(np.mean(yh[q] == y_eval[q])),
                     "BA": float((np.mean(yh[y_eval == 1] == 1) + np.mean(yh[y_eval == 0] == 0)) / 2)}
                r.update({kk: v for kk, v in dense.metrics((gp.latent_mean(dense.z) > 0).astype(int)).items() if kk in ("NSD_0.1", "ASSD")})
                rows.append(r)
            if b == 80:
                break
            cands = np.setdiff1d(np.arange(n_pool), L)
            if policy == "random":
                L.append(int(prng.choice(cands)))
            else:
                mu, var = latent_mv(gp, z_pool[cands])
                if policy == "margin":
                    p = 1 / (1 + np.exp(-mu / np.sqrt(1 + np.pi * var / 8)))
                    L.append(int(cands[np.argmin(np.abs(p - .5))]))
                elif policy == "bald":
                    L.append(int(cands[np.argmax(bald(mu, var))]))
    return rows


DENSE, HYP = {}, {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=12)
    ap.add_argument("--sigmas", default="0.0,0.5,1.0")
    ap.add_argument("--tag", default="development")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    sig = [float(s) for s in a.sigmas.split(",")]
    hf = OUT / "hyperparameters.json"
    store = json.loads(hf.read_text()) if hf.exists() else {}
    for s in ("BAL", "OLD", "NEW"):
        for g in sig:
            key = f"{s}_s{g}"
            if key not in store:
                store[key] = HYP13.get(key) or oracle_hypers(calibrated(s), g)
            HYP[(s, g)] = store[key]
    hf.write_text(json.dumps(store, indent=2))
    res = Parallel(n_jobs=7)(delayed(_run)(s, g, r, HYP) for s in ("BAL", "OLD", "NEW") for g in sig for r in range(a.reps))
    df = pd.DataFrame([x for rows in res for x in rows])
    df.to_csv(OUT / f"noise_acquisition_{a.tag}.csv", index=False)
    au = df.groupby(["scenario", "sigma", "rep", "policy"]).apply(
        lambda g: pd.Series({c: np.trapezoid(g.sort_values("budget")[c], g.sort_values("budget").budget) / 64 for c in ("NSD_0.1", "q20_accuracy", "BA")}),
        include_groups=False).reset_index()
    print(au.groupby(["scenario", "sigma", "policy"])[["NSD_0.1", "q20_accuracy", "BA"]].mean().round(3).unstack("policy").to_string())


def _run(s, g, r, hyp):
    HYP.update(hyp)
    return run(s, g, r)


if __name__ == "__main__":
    main()
