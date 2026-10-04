"""Week 16 — synthetic cells with the Week 15 seeds, plus the truth needed by the expectation oracle.

Every cell reproduces Week 15 exactly (pool, labels, startup, model hyperparameters, dense evaluator) and adds:
  zref, tref : the 400-point uniform reference cloud of EBR-D/VSUR (model coordinates) and its true latent signs
               (gpworld: truth exists only on the jointly drawn points, so the first 400 dense points are used);
  p_true     : P(y = 1 | pool point) under the generating law (deterministic labels -> 0/1);
  phys       : physics score as a function of model coordinates (None where the family has none).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.special import expit, ndtr

from src.week13_synthetic import latent, physics_score
from src.week13_synthetic_al import calibrated, noisy_labels, to_box
from src.week15_al import DenseEval, start_design
import src.week15_heldout as H
from src.week14_transfer_study import NEW_BOX, OLD_BOX, calibrate, latent as w14_latent

ROOT = Path(__file__).resolve().parents[1]
DEV_HYP = json.loads((ROOT / "outputs/week14_research_program/synthetic/noise_acquisition/hyperparameters.json").read_text())
HO_HYP = json.loads((ROOT / "outputs/week15_boundary_acquisition/heldout/hyperparameters.json").read_text())
ZREF = np.random.default_rng([15, 99]).random((400, 4))
DEV_CELLS = [("dev", {"scn": s, "sigma": g}) for s in ("BAL", "OLD", "NEW") for g in (0.0, 0.5, 1.0)]
HO_CELLS = list(H.CELLS)
ALL_CELLS = DEV_CELLS + HO_CELLS
_PARS: dict = {}


def pars():
    if not _PARS:
        for f in ("curvedMono", "hartmannDev"):
            _PARS[f] = calibrate(f)
    return _PARS


def cell_key(fam, cfg):
    if fam == "dev":
        return f"dev|{cfg['scn']}|sigma={cfg['sigma']}"
    return H.cell_key(fam, cfg)


def build(fam, cfg, rep, pars_=None):
    if fam == "dev":
        scn, sigma, n_pool = cfg["scn"], cfg["sigma"], 108
        sc = calibrated(scn)
        rng = np.random.default_rng([15, int(sigma * 10), n_pool, rep, ("BAL", "OLD", "NEW").index(scn)])
        u_pool, u_eval = sc.sample(n_pool, rng), sc.sample(int(round(n_pool / .8)), rng)
        y_pool, y_eval = noisy_labels(u_pool, sc, sigma, rng), noisy_labels(u_eval, sc, sigma, rng)
        z_pool, z_eval = to_box(u_pool, sc), to_box(u_eval, sc)
        ud = sc.sample(8000, np.random.default_rng(5))
        dense = DenseEval(to_box(ud, sc), (latent(ud, sc) > 0).astype(int))
        lo, hi = np.asarray(sc.lo), np.asarray(sc.hi)
        f_pool = latent(u_pool, sc)
        c = dict(z_pool=z_pool, y_pool=y_pool, f_pool=f_pool, z_eval=z_eval, y_eval=y_eval, dense=dense,
                 hyp=DEV_HYP[f"{scn}_s{sigma}"], zref=ZREF, tref=(latent(lo + (hi - lo) * ZREF, sc) > 0).astype(int),
                 p_true=ndtr(f_pool / sigma) if sigma > 0 else (f_pool > 0).astype(float),
                 phys=lambda z: physics_score(lo + (hi - lo) * np.asarray(z)),
                 start=start_design(z_pool, y_pool, [15, rep, 2]), pool=n_pool)
        c["s_pool"] = physics_score(u_pool)
        return c
    H.PARS.update(pars_ if pars_ is not None else pars())
    c = H.make_cell(fam, cfg, rep)
    hyp = HO_HYP[H.cell_key(fam, cfg)]
    c["hyp"] = hyp
    c["pool"] = cfg["pool"]
    c["start"] = start_design(c["z_pool"], c["y_pool"], [152, rep, 2])
    if fam == "gpworld":
        c["zref"], c["tref"] = c["dense"].z[:400], c["dense"].y[:400]
        c["p_true"], c["phys"] = expit(c["f_pool"]), None
        return c
    if fam in ("curvedMono", "rough"):
        box = c["box"]
        to_u = lambda z: box[0] + (box[1] - box[0]) * np.asarray(z)
        c["zref"], c["tref"] = ZREF, (w14_latent(to_u(ZREF), c["famw14"], c["par"]) > 0).astype(int)
        c["phys"] = lambda z: to_u(z) @ H.W_PHYS
        if fam == "curvedMono":
            s = cfg["sigma"]
            c["p_true"] = ndtr(c["f_pool"] / s) if s > 0 else (c["f_pool"] > 0).astype(float)
        else:
            c["p_true"] = c["y_pool"].astype(float)      # deterministic rough field: the label is the truth
        return c
    if fam == "branin4d":
        c["zref"], c["tref"] = ZREF, ((H.BRANIN_T - H.branin(ZREF)) / 20.0 > 0).astype(int)
        s = cfg["sigma"]
        c["p_true"] = ndtr(c["f_pool"] / s) if s > 0 else (c["f_pool"] > 0).astype(float)
        c["phys"] = None
        return c
    raise ValueError(fam)


def margin_pick(post, z_pool, cands):
    """Week 15 margin rule: argmin |p - 1/2| with the probit-averaged predictive (first index on ties)."""
    mu, var = post.mean_var(z_pool[cands])
    with np.errstate(over="ignore"):
        p = 1 / (1 + np.exp(-mu / np.sqrt(1 + np.pi * var / 8)))   # identical expression to week15_al.run_path
    return int(cands[np.argmin(np.abs(p - .5))])


def margin_states(c, budgets, model, trace_budgets=tuple(range(16, 81, 4))):
    """Regenerate a margin path with `model`; return {budget: labelled list} and dense metrics per trace budget."""
    L = list(c["start"]); out, trace = {}, {}
    while True:
        b = len(L)
        post = model.fit(c["z_pool"][L], c["y_pool"][L])
        if b in budgets:
            out[b] = list(L)
        if b in trace_budgets:
            trace[b] = c["dense"].metrics((post.latent_mean(c["dense"].z) > 0).astype(int))
        if b >= 80:
            return out, trace
        cands = np.setdiff1d(np.arange(len(c["z_pool"])), L)
        L.append(margin_pick(post, c["z_pool"], cands))
