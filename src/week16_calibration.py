"""Week 16 item 3 — does *joint* (pairwise) calibration explain margin's acquisition quality beyond marginal
calibration?  Acquisition is fixed to margin; only the model varies (definitions in PREDICTIONS.md).

Per (cell, rep, variant): the variant's own margin path; at budgets {16, 32, 48, 64, 80} marginal log loss /
Brier of the latent-sign probabilities on the reference cloud, joint log loss / Brier on its 8-NN edges and
on 2,000 fixed random pairs, and the dependence excess (joint − sum of marginal log losses); NSD and dense-BA
AULC (16-80, step 4, Week 15 normalization); one-step regret H at budgets {24, 48}.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.special import ndtr

from src.week15_ebr import bvn_lower, knn_graph
from src.week16_cells import ALL_CELLS, build, cell_key, margin_states, pars
from src.week16_headroom import evaluate_state
from src.week16_peer import Model

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week16_theory_meets_data/calibration"
SCORE_BUDGETS = (16, 32, 48, 64, 80)
H_BUDGETS = (24, 48)
TRACE = tuple(range(16, 81, 4))
EPS = 1e-12


def variants(hyp, phys):
    ls, var, m0 = np.asarray(hyp["ls"], float), float(hyp["var"]), hyp.get("m0", 0.0)
    out = {"base": Model(ls, var, m0=m0), "ls_x0.5": Model(ls * .5, var, m0=m0), "ls_x2": Model(ls * 2, var, m0=m0),
           "var_x0.25": Model(ls, var * .25, m0=m0), "var_x4": Model(ls, var * 4, m0=m0),
           "mean_ml2": Model(ls, var, mean="ml2")}
    if phys is not None:
        out["mean_physics"] = Model(ls, var, mean="physics", phys=phys)
    return out


def pair_probs(a_i, a_k, rho):
    """P(T_i = ±1, T_k = ±1) for latent signs with standardized means a and correlation rho."""
    p11 = bvn_lower(a_i, a_k, rho)
    p10 = bvn_lower(a_i, -a_k, -rho)
    p01 = bvn_lower(-a_i, a_k, -rho)
    p00 = np.clip(1 - p11 - p10 - p01, 0, 1)
    return {(1, 1): np.clip(p11, 0, 1), (1, 0): np.clip(p10, 0, 1), (0, 1): np.clip(p01, 0, 1), (0, 0): p00}


def joint_scores(mu, s, C, t, pairs):
    i, k = pairs[:, 0], pairs[:, 1]
    rho = np.clip(C[i, k] / (s[i] * s[k]), -.999999, .999999)
    P = pair_probs(mu[i] / s[i], mu[k] / s[k], rho)
    obs = np.select([(t[i] == a) & (t[k] == b) for a, b in P], [P[key] for key in P])
    brier = sum((P[(a, b)] - ((t[i] == a) & (t[k] == b))) ** 2 for a, b in P)
    q = ndtr(mu / s)
    ll_m = -np.log(np.clip(np.where(t == 1, q, 1 - q), EPS, 1))
    jll = -np.log(np.clip(obs, EPS, 1))
    return float(jll.mean()), float(brier.mean()), float((jll - ll_m[i] - ll_m[k]).mean())


def state_scores(c, post, near, rand):
    Z, t = c["zref"], c["tref"]
    mu, v = post.mean_var(Z); s = np.sqrt(v); C = post.cross_cov(Z, Z)
    q = ndtr(mu / s)
    ll = -np.log(np.clip(np.where(t == 1, q, 1 - q), EPS, 1))
    jn = joint_scores(mu, s, C, t, near); jr = joint_scores(mu, s, C, t, rand)
    return {"LL": float(ll.mean()), "Brier": float(((q - t) ** 2).mean()),
            "JLL_near": jn[0], "JBrier_near": jn[1], "DE_near": jn[2], "JLL_rand": jr[0], "JBrier_rand": jr[1], "DE_rand": jr[2]}


def aulc(trace, key):
    b = np.array(sorted(trace)); v = np.array([trace[x][key] for x in b])
    return float(np.trapezoid(v, b) / 64)


def job(fam, cfg, rep, pars_, out_dir):
    dest = Path(out_dir) / f"{cell_key(fam, cfg).replace('|', '__').replace('=', '-')}__r{rep}.json"
    if dest.exists():
        return json.loads(dest.read_text())
    c = build(fam, cfg, rep, pars_)
    near = knn_graph(c["zref"], 8)
    rr = np.random.default_rng([16, 55]); rand = np.unique(np.sort(rr.integers(0, 400, (2400, 2)), 1), axis=0)
    rand = rand[rand[:, 0] != rand[:, 1]][:2000]
    rows = []
    for name, mdl in variants(c["hyp"], c.get("phys")).items():
        states, trace = margin_states(c, set(SCORE_BUDGETS) | set(H_BUDGETS), mdl, TRACE)
        base = {"cell": cell_key(fam, cfg), "family": fam, "rep": rep, "variant": name,
                "NSD_AULC": aulc(trace, "NSD_0.1"), "BA_AULC": aulc(trace, "dense_BA"), "ASSD_AULC": aulc(trace, "ASSD")}
        for b in SCORE_BUDGETS:
            if b in states:
                post = mdl.fit(c["z_pool"][states[b]], c["y_pool"][states[b]])
                rows.append({**base, "budget": b, "kind": "score", **state_scores(c, post, near, rand)})
        for b in H_BUDGETS:
            if b in states:
                st, _ = evaluate_state(c, states[b], mdl, np.random.default_rng([16, 3, rep, b]), cap=60)
                rows.append({**base, "budget": b, "kind": "regret", "H_ham_ref": st["H|Vref|Vt_ham_ref"],
                             "H_nsd": st["H|Vref|Vt_nsd"], "A_ham_ref": st["A|Vref|Vt_ham_ref"], "r_model_ref": st["r_model_ref"]})
        if not any(r["variant"] == name for r in rows):
            rows.append({**base, "kind": "aulc_only"})
    dest.write_text(json.dumps(rows, default=float))
    return rows


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--reps", type=int, default=8); a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True); pdir = OUT / "paths"; pdir.mkdir(exist_ok=True)
    P = pars()
    jobs = sorted([(f, c, r) for f, c in ALL_CELLS for r in range(a.reps)], key=lambda j: -j[1].get("pool", 108))
    res = Parallel(n_jobs=7, verbose=5)(delayed(job)(f, c, r, P, pdir) for f, c, r in jobs)
    pd.DataFrame([x for rows in res for x in rows]).to_csv(OUT / "calibration.csv", index=False)


if __name__ == "__main__":
    main()
