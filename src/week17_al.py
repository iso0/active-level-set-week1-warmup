"""Week 17 — synthetic active level-set engine for model × acquisition studies (development and held-out).

A world provides (Week 16 `week16_cells.build` interface): pool inputs z (unit box), labels y, true latent f,
p_true, dense truth evaluator, 400-point reference cloud with true signs, paid startup, and a physics score
phys(z) (None → physics-free family; physics models then receive a constant score).
Every step refits the model by ML-II on the revealed labels (no oracle hyperparameters).  Rules:
  margin   argmin |p − ½| (predictive probability)          random   uniform over candidates
  coverage Week 13 Candidate-B-like rank(uncertainty) + rank(distance) inside the physics band, B < 40,
           margin afterwards (physics-free worlds: band = whole pool)
  peer     argmax one-step Hamming value on the reference cloud (Week 16 PEER under the current model)
Oracle diagnostics at chosen budgets (fixed-hyperparameter refits of the same model): V_true for up to `cap`
candidates (always including the margin and PEER picks), H, A and rank agreement.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler

import src.week17_models as M
from src.week13_synthetic_al import q20_flags
from src.week15_al import coverage_choice

TRACE = tuple(range(16, 81, 4))


def scores(c):
    ph = c.get("phys")
    sp = (lambda z: np.zeros(len(z))) if ph is None else ph
    return sp


def truth_eval(c, f, sp):
    d = c["dense"]
    mu_d, _ = f.latent(d.z, sp(d.z))
    m = d.metrics((mu_d > 0).astype(int))
    mu_r, _ = f.latent(c["zref"], sp(c["zref"]))
    m["ham_ref"] = float(np.mean((mu_r > 0) != (c["tref"] == 1)))
    return m


def oracle_state(c, model, f, L, cands, picks, sp, rng, cap):
    z, y, s = c["z_pool"], c["y_pool"], sp(c["z_pool"])
    base = truth_eval(c, f, sp)
    keep = sorted(set(int(p) for p in picks))
    rest = [k for k in cands if k not in keep]
    sub = np.array(sorted(keep + list(rng.choice(rest, min(cap, len(cands)) - len(keep), replace=False))), int)
    vt = {}
    for j in sub:
        acc = {"ham_ref": 0.0, "NSD_0.1": 0.0}
        for lab, w in ((1, c["p_true"][j]), (0, 1 - c["p_true"][j])):
            if w == 0:
                continue
            yy = y.copy(); yy[j] = lab
            g = M.fit(model, z, s, yy, np.arange(len(z)), np.r_[L, j], kernel=f.gp.kernel_, scalers=(f.xs, f.hs))
            e = truth_eval(c, g, sp)
            for k in acc:
                acc[k] += w * e[k]
        vt[int(j)] = (base["ham_ref"] - acc["ham_ref"], acc["NSD_0.1"] - base["NSD_0.1"])
    return sub, vt


def run_path(c, model, rule, seed, oracle_budgets=(), cap=60, horizon=80):
    sp = scores(c)
    z, y = c["z_pool"], c["y_pool"]; s = sp(z)
    zstd = StandardScaler().fit_transform(z)
    rng = np.random.default_rng(seed)
    L = list(c["start"]); trace, orc = [], []
    while True:
        b = len(L)
        f = M.fit(model, z, s, y, np.arange(len(z)), L)
        cands = np.setdiff1d(np.arange(len(z)), L)
        if b in TRACE:
            m = truth_eval(c, f, sp)
            pe = f.proba(c["z_eval"], sp(c["z_eval"])); q = q20_flags(c["z_eval"], c["y_eval"])
            m["q20_accuracy"] = float(np.mean((pe[q] >= .5) == c["y_eval"][q]))
            m["finite_BA"] = float(np.nanmean([np.mean((pe >= .5)[c["y_eval"] == k] == k) for k in (0, 1)]))
            trace.append({"budget": b, **m, "fp_err": f.converged()})
        if b >= horizon:
            return trace, orc
        p = f.proba(z[cands], s[cands])
        need_peer = rule == "peer" or b in oracle_budgets
        v = M.peer_values(f, c["zref"], sp(c["zref"]), z[cands], s[cands]) if need_peer else None
        mpick = int(cands[np.argmin(np.abs(p - .5))])
        if rule == "margin":
            nxt = mpick
        elif rule == "random":
            nxt = int(rng.choice(cands))
        elif rule == "coverage":
            nxt = coverage_choice(cands, p, None if c.get("phys") is None else s, L, y, zstd) if b < 40 else None
            nxt = mpick if nxt is None else int(nxt)
        elif rule == "peer":
            nxt = int(cands[np.argmax(v)])
        else:
            raise ValueError(rule)
        if b in oracle_budgets:
            ppick = int(cands[np.argmax(v)])
            sub, vt = oracle_state(c, model, f, L, cands, [mpick, ppick], sp, np.random.default_rng([seed[0], seed[1], b, 7] if isinstance(seed, list) else b), cap)
            idx = {int(k): i for i, k in enumerate(cands)}
            Vm = np.array([v[idx[j]] for j in sub]); Th = np.array([vt[j][0] for j in sub]); Tn = np.array([vt[j][1] for j in sub])
            r = {"budget": b, "n_cands": len(cands), "r_model": float(v[idx[mpick]] / v.max()) if v.max() > 1e-6 else np.nan,
                 "margin_abs_f": float(abs(c["f_pool"][mpick])), "peer_abs_f": float(abs(c["f_pool"][ppick])),
                 "median_abs_f_cands": float(np.median(np.abs(c["f_pool"][cands])))}
            for tag, T in (("ham", Th), ("nsd", Tn)):
                r[f"H_{tag}"] = float(T.max() - vt[mpick][0 if tag == "ham" else 1])
                r[f"A_{tag}"] = float(vt[ppick][0 if tag == "ham" else 1] - vt[mpick][0 if tag == "ham" else 1])
                r[f"rho_{tag}"] = float(spearmanr(Vm, T).statistic) if np.ptp(T) > 0 and np.ptp(Vm) > 0 else np.nan
                r[f"margin_{tag}"] = float(vt[mpick][0 if tag == "ham" else 1]); r[f"peer_{tag}"] = float(vt[ppick][0 if tag == "ham" else 1])
                r[f"rand_{tag}"] = float(T.mean()); r[f"max_{tag}"] = float(T.max())
            orc.append(r)
        L.append(nxt)


def aulc(trace, key):
    b = np.array([t["budget"] for t in trace]); v = np.array([t[key] for t in trace])
    return float(np.trapezoid(v, b) / 64)
