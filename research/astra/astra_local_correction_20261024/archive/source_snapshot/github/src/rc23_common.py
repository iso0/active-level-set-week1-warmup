"""RC23 constructions and trajectories: the fully lean h + depth system against the RC22 candidates (margin fixed everywhere).

Constructions on one paid state (public inputs and PAID outcomes only; test outcomes evaluator-only; one-class rule of RC19):
  PHR_NRMAP  RC22 reference: SHQ upstream shared over (log A, T, S) [src.rc20_attr.cf, K = 10] + learned-regularisation classifier
             on [log h, A, T, S] (src.rc22_common.phr_family, residual-free grid)
  HA_LR      RC22 candidate: the SAME shared three-channel upstream; the classifier uses only [log h, A]
  HA_LEAN    fully lean h + depth system: the same SHQ GP code fitted on the paid DEPTHS ONLY (cols = (log A,)), so temperature and
             spike values never enter any fit, hyperparameter, normalisation, quality weight or decision; the same honest K = 10
             cross-fitting, Matern-3/2 ARD kernel, record-quality treatment, h definition and learned-regularisation classifier [log h, A]
  HONLY_LR   cheap control: the learned-regularisation classifier on exact log h only (no emulator at all)
Selector: margin -|p - 0.5| on the arm's own construction (first index on ties). Startups / blocks: src.rc22_common.
"""
from __future__ import annotations

import time
import warnings

import numpy as np

import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc20_attr as A
import src.rc22_common as C

DEPTH = ("log_A_um",)
CONS = ("PHR_NRMAP", "HA_LR", "HA_LEAN", "HONLY_LR")


def state(task, rev, Z, rows, which=CONS):
    y_p = rev.paid_y(); A_p = rev.paid_A(); L = rev.paid; y = y_p[L]; usable = np.isfinite(A_p[L])
    if len(set(y_p[L][usable].tolist())) < 2:
        return {k: np.full(len(rows), float(np.mean(y))) for k in which}, {"one_class": True}
    h = A.hcol(task); out = {}; info = {"one_class": False}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if {"PHR_NRMAP", "HA_LR"} & set(which):
            R = A.cf(Z, rev, A.ATS, "SHQ", rows, A.KF); info["fallbacks3"] = R["fallbacks"]
            if "PHR_NRMAP" in which:
                out["PHR_NRMAP"] = C.phr_family(R["F"], h[L], y, R["E"], h[rows])[0]
            if "HA_LR" in which:
                out["HA_LR"] = C.phr_family(R["F"], h[L], y, R["E"], h[rows], feats=(0,))[0]
        if "HA_LEAN" in which:
            R1 = A.cf(Z, rev, DEPTH, "SHQ", rows, A.KF); info["fallbacks1"] = R1["fallbacks"]
            out["HA_LEAN"] = C.phr_family(R1["F"], h[L], y, R1["E"], h[rows], feats=(0,))[0]
        if "HONLY_LR" in which:
            out["HONLY_LR"] = C.phr_family(np.zeros((len(L), 1)), h[L], y, np.zeros((len(rows), 1)), h[rows], feats=())[0]
    return {k: out[k] for k in which}, info


def run_arm(task, own, M, bmax=60):
    """One margin trajectory of construction `own`; only `own` is computed, so the recorded CPU is the arm's own cost."""
    rev = K._rev_with(task, M, []); Z = P.zstd(task); C.startup(task, rev); nt = len(task["test"]); evals = []; t0 = time.time(); c0 = time.process_time()
    while True:
        b = rev.queries; cands = np.setdiff1d(task["pool"], rev.paid); t1 = time.process_time()
        out, info = state(task, rev, Z, np.r_[task["test"], cands], which=(own,))
        e = {"budget": b, "p": {own: LN._f32(out[own][:nt])}, "info": info}
        if b >= bmax:
            e["cpu_s"] = time.process_time() - t1; evals.append(e); break
        if info["one_class"]:
            nxt = LN.next_on_path(task, rev); how = "path"
        else:
            nxt = int(cands[int(np.argmax(-np.abs(out[own][nt:] - 0.5)))]); how = "margin"
        e["cpu_s"] = time.process_time() - t1; e["how"] = how; evals.append(e); rev.reveal(nxt)
    return {"repeat": task["repeat"], "fold": task["fold"], "startup": task.get("startup", "STD"), "block": task.get("block"), "construction": own, "arm": own,
            "paid": rev.order, "paid_ids": [task["ids"][i] for i in rev.order], "test_ids": [task["ids"][i] for i in task["test"]], "evals": evals,
            "seconds": time.time() - t0, "cpu_s": time.process_time() - c0, "queries": rev.queries}
