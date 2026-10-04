"""Week 16 items 1-2 — does margin leave model-visible value on the table, and is the remaining headroom
model error?  Per state (margin path, budget b):

  V_model(j)  PEER one-step Hamming value under the fitted model, target (a) the whole pool's latent signs,
              (b) the 400-point reference cloud (closed form, src/week16_peer.py);
  V_true(j)   expectation oracle with the *same* refit model: E_{y ~ p_true(j)} of the reduction in the true
              error after refitting with (j, y); objectives: Hamming on the reference cloud (matched to (b)),
              Hamming on the pool latent signs (matched to (a)), dense error rate, NSD_0.1 (geometric);
  H = max_j V_true − V_true(margin),  A = V_true(argmax V_model) − V_true(margin),  H − A = model gap.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.optimize import linprog
from scipy.special import expit
from scipy.stats import spearmanr

from src.week16_cells import ALL_CELLS, build, cell_key, margin_pick, margin_states, pars
from src.week16_peer import Model, peer_values

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week16_theory_meets_data/headroom"
BUDGETS16 = (16, 24, 32, 48, 64, 80)
CAND_CAP = 120
V_FLOOR = 1e-6      # a model that believes no query changes the expected number of errors by 1e-6 is "saturated"


def ratio(v, vmax):
    return float(v / vmax) if vmax >= V_FLOOR else np.nan


def outside_hull(points, x):
    """True if x is not a convex combination of the rows of points (LP feasibility)."""
    n = len(points)
    res = linprog(np.zeros(n), A_eq=np.vstack([points.T, np.ones(n)]), b_eq=np.r_[x, 1], bounds=[(0, None)] * n, method="highs")
    return not res.success


def truth_errors(c, post):
    mu_ref = post.latent_mean(c["zref"]); mu_pool = post.latent_mean(c["z_pool"]); mu_d = post.latent_mean(c["dense"].z)
    yd = (mu_d > 0).astype(int)
    m = c["dense"].metrics(yd)
    return {"ham_ref": float(np.mean((mu_ref > 0) != (c["tref"] == 1))),
            "ham_pool": float(np.mean((mu_pool > 0) != (c["f_pool"] > 0))),
            "err_dense": float(np.mean(yd != c["dense"].y)), "nsd": m["NSD_0.1"]}


def v_true(c, model, L, j):
    z, y, p = c["z_pool"], c["y_pool"], c["p_true"][j]
    out = {}
    for lab, w in ((1, p), (0, 1 - p)):
        if w == 0:
            continue
        e = truth_errors(c, model.fit(z[np.r_[L, j]], np.r_[y[L], lab]))
        for k, v in e.items():
            out[k] = out.get(k, 0.0) + w * v
    return out


def evaluate_state(c, L, model, rng, cap=CAND_CAP, full=True):
    z = c["z_pool"]
    post = model.fit(z[L], c["y_pool"][L])
    cands = np.setdiff1d(np.arange(len(z)), L)
    m = margin_pick(post, z, cands)
    Vref = peer_values(post, c["zref"], z[cands]); Vpool = peer_values(post, z, z[cands])
    mu, var = post.mean_var(z[cands])
    p = expit(mu / np.sqrt(1 + np.pi * var / 8))
    im = int(np.flatnonzero(cands == m)[0])
    state = {"budget": len(L), "n_cands": len(cands), "margin": m,
             "argmax_ref": int(cands[np.argmax(Vref)]), "argmax_pool": int(cands[np.argmax(Vpool)]),
             "r_model_ref": ratio(Vref[im], Vref.max()), "r_model_pool": ratio(Vpool[im], Vpool.max()),
             "saturated_ref": bool(Vref.max() < V_FLOOR), "saturated_pool": bool(Vpool.max() < V_FLOOR),
             "Vref_margin": float(Vref[im]), "Vref_max": float(Vref.max()), "Vpool_margin": float(Vpool[im]), "Vpool_max": float(Vpool.max())}
    zl = z[L]
    for tag, j in (("margin", m), ("argmax_ref", state["argmax_ref"])):
        state[f"{tag}_dist_labelled"] = float(np.linalg.norm(zl - z[j], axis=1).min())
        state[f"{tag}_abs_latent"] = float(abs(c["f_pool"][j]))
        state[f"{tag}_outside_hull"] = bool(outside_hull(zl, z[j]))
        state[f"{tag}_p"] = float(p[np.flatnonzero(cands == j)[0]])
    state["median_dist_cand_labelled"] = float(np.median(np.linalg.norm(z[cands][:, None] - zl[None], axis=2).min(1)))
    if not full:
        return state, None
    base = truth_errors(c, post)
    state.update({f"base_{k}": v for k, v in base.items()})
    if len(cands) > cap:
        keep = {m, state["argmax_ref"], state["argmax_pool"]}
        rest = [k for k in cands if k not in keep]
        sub = np.sort(np.r_[list(keep), rng.choice(rest, cap - len(keep), replace=False)]).astype(int)
    else:
        sub = cands
    rows = []
    for j in sub:
        k = int(np.flatnonzero(cands == j)[0])
        vt = v_true(c, model, L, j)
        rows.append({"cand": int(j), "is_margin": j == m, "Vref": float(Vref[k]), "Vpool": float(Vpool[k]), "p": float(p[k]),
                     "abs_latent": float(abs(c["f_pool"][j])),
                     "Vt_ham_ref": base["ham_ref"] - vt["ham_ref"], "Vt_ham_pool": base["ham_pool"] - vt["ham_pool"],
                     "Vt_err_dense": base["err_dense"] - vt["err_dense"], "Vt_nsd": vt["nsd"] - base["nsd"]})
    C = pd.DataFrame(rows)
    state["subsampled"] = len(sub) < len(cands)
    for vm in ("Vref", "Vpool"):
        jm = C[vm].idxmax()
        for vt in ("Vt_ham_ref", "Vt_ham_pool", "Vt_err_dense", "Vt_nsd"):
            vmarg = float(C.loc[C.is_margin, vt].iloc[0])
            H = float(C[vt].max() - vmarg)
            A = float(C.loc[jm, vt] - vmarg)
            rho = spearmanr(C[vm], C[vt]).statistic if C[vt].nunique() > 1 else np.nan
            state.update({f"H|{vm}|{vt}": H, f"A|{vm}|{vt}": A, f"rho|{vm}|{vt}": float(rho),
                          f"vtmax|{vt}": float(C[vt].max()), f"vtmargin|{vt}": vmarg})
    return state, C


def variant_models(c):
    hyp = c["hyp"]
    out = {"mean_base": Model.from_hyp(hyp, name="mean_base"),
           "mean_zero": Model(hyp["ls"], hyp["var"], m0=0.0, name="mean_zero"),
           "mean_ml2": Model(hyp["ls"], hyp["var"], mean="ml2", name="mean_ml2")}
    if c.get("phys") is not None:
        out["mean_physics"] = Model(hyp["ls"], hyp["var"], mean="physics", phys=c["phys"], name="mean_physics")
    return out


def decoy_variants(c, L):
    """Item 2: margin pick, r_model and the oracle value of that pick under each prior-mean rule."""
    rows = []
    z = c["z_pool"]
    for name, mdl in variant_models(c).items():
        if name == "mean_zero" and c["hyp"].get("m0", 0.0) == 0.0:
            continue                                   # identical to mean_base
        st, _ = evaluate_state(c, L, mdl, None, full=False)
        post = mdl.fit(z[L], c["y_pool"][L]); base = truth_errors(c, post)
        vt = v_true(c, mdl, L, st["margin"])
        rows.append({"variant": name, **{k: st[k] for k in ("r_model_ref", "r_model_pool", "margin_dist_labelled", "margin_abs_latent",
                                                            "margin_outside_hull", "margin_p")},
                     "Vt_ham_ref_margin": base["ham_ref"] - vt["ham_ref"], "Vt_nsd_margin": vt["nsd"] - base["nsd"],
                     "base_nsd": base["nsd"], "base_ham_ref": base["ham_ref"]})
    return rows


def job(fam, cfg, rep, pars_, out_dir):
    dest = Path(out_dir) / f"{cell_key(fam, cfg).replace('|', '__').replace('=', '-')}__r{rep}.json"
    if dest.exists():
        return json.loads(dest.read_text())
    c = build(fam, cfg, rep, pars_)
    model = Model.from_hyp(c["hyp"])
    states, trace = margin_states(c, BUDGETS16, model)
    rng = np.random.default_rng([16, rep, len(c["z_pool"])])
    S, D, cand_frames = [], [], []
    meta = {"cell": cell_key(fam, cfg), "family": fam, "rep": rep, "pool": c["pool"],
            "sigma": cfg.get("sigma", np.nan), "m0": cfg.get("m0", np.nan), "box": cfg.get("box", cfg.get("scn", ""))}
    for b, L in states.items():
        st, C = evaluate_state(c, L, model, rng)
        S.append({**meta, **st})
        C = C.assign(**{k: meta[k] for k in ("cell", "rep")}, budget=b)
        cand_frames.append(C)
        D += [{**meta, "budget": b, **r} for r in decoy_variants(c, L)]
    res = {"states": S, "decoys": D, "cands": pd.concat(cand_frames).to_dict("records"),
           "trace": [{**meta, "budget": b, **v} for b, v in trace.items()]}
    dest.write_text(json.dumps(res, default=float))
    return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--reps", type=int, default=8); ap.add_argument("--cells", default="all")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True); pdir = OUT / "paths"; pdir.mkdir(exist_ok=True)
    P = pars()
    cells = ALL_CELLS if a.cells == "all" else [ALL_CELLS[int(i)] for i in a.cells.split(",")]
    jobs = sorted([(f, c, r) for f, c in cells for r in range(a.reps)], key=lambda j: -j[1].get("pool", 108))
    res = Parallel(n_jobs=7, verbose=5)(delayed(job)(f, c, r, P, pdir) for f, c, r in jobs)
    pd.DataFrame([s for r in res for s in r["states"]]).to_csv(OUT / "states.csv", index=False)
    pd.DataFrame([s for r in res for s in r["decoys"]]).to_csv(OUT / "decoy_variants.csv", index=False)
    pd.DataFrame([s for r in res for s in r["cands"]]).to_csv(OUT / "candidates.csv.gz", index=False)
    pd.DataFrame([s for r in res for s in r["trace"]]).to_csv(OUT / "margin_trace.csv", index=False)


if __name__ == "__main__":
    main()
