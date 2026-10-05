"""Week 18 benchmark tasks (seeds and blocks locked in BENCHMARK_SPEC.md before any method work).

Real (labels seen in earlier weeks; confirmation on them = SPLIT-CONFIRMATION):
  R1 POOLED      OLD ∪ NEW (541); 20 repeats × 5 folds stratified by campaign × class, seed [1818, rep];
                 pool = 4 folds, test = 1 fold.  POOLED_STD: same on the 500 standard-settings runs.
  R2 TRANSFER    prior = all OLD labels (free); paid pool = NEW training pool of the frozen Week 11/12 split;
                 test = its NEW test fold.  R2rev: prior = all NEW, pool/test = Week 8.5 OLD run.
  R3 NEW / OLD   the frozen NEW splits / Week 8.5 OLD runs, no prior (Weeks 12–17 continuity).
Blocks (by repeat): DEV 1–8; C1 9–12; C2 13–16; C3 17–20.  Each confirmation block is used once.
Semi-synthetic digital twins (S1) and stress worlds (S2): src/week18_twins.py.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BLOCKS = {"DEV": range(1, 9), "C1": range(9, 13), "C2": range(13, 17), "C3": range(17, 21)}
F = ["P", "VX", "LS", "ST"]


def block_of(rep):
    return next(k for k, v in BLOCKS.items() if rep in v)


def pooled_frame():
    from src.week18_data_audit import load
    D = load()
    D["q20_id"] = D.sim_id.astype(str)
    return D


def q20_for(X, y, ids, test):
    from src.external_validation.analysis import boundary_flags
    return boundary_flags(X, y, test, ids, "entire_evaluation_batch")[20]


def pooled_tasks(subset="all"):
    D = pooled_frame()
    if subset == "standard":
        D = D[D.standard].reset_index(drop=True)
    X = D[F].to_numpy(float); y = D.y.to_numpy(int); ids = D.q20_id.to_numpy(str); camp = D.campaign.to_numpy(int)
    strat = camp * 2 + y
    out = []
    for rep in range(1, 21):
        rng = np.random.default_rng([1818, rep]); folds = np.zeros(len(D), int)
        for s in np.unique(strat):
            idx = np.flatnonzero(strat == s); rng.shuffle(idx); folds[idx] = np.arange(len(idx)) % 5
        for fold in range(5):
            te = np.flatnonzero(folds == fold); pool = np.flatnonzero(folds != fold)
            out.append({"task": f"R1_POOLED{'_STD' if subset == 'standard' else ''}", "repeat": rep, "fold": fold + 1, "block": block_of(rep),
                        "X": X, "y": y, "depth": np.full(len(y), np.nan), "campaign": camp, "pool": pool, "test": te, "prior": np.array([], int),
                        "q20": q20_for(X, y, ids, te), "seed": [1818, rep, fold + 1]})
    return out


def new_old_frames():
    from src.week12_development_common import load_new, load_old
    return load_new(), load_old()


def r3_new_tasks(prior_old=False):
    new, old = new_old_frames()
    splits = json.loads((ROOT / "outputs/week12_startup_and_transfer_development/audit/original_splits.json").read_text())
    if prior_old:
        X = np.r_[old[F].to_numpy(float), new[F].to_numpy(float)]; y = np.r_[old.has_keyhole.to_numpy(int), new.has_keyhole.to_numpy(int)]
        off = len(old); prior = np.arange(len(old)); ids = np.r_[old.sim_id.astype(str).to_numpy(), new.sim_id.astype(str).to_numpy()]
    else:
        X = new[F].to_numpy(float); y = new.has_keyhole.to_numpy(int); off = 0; prior = np.array([], int); ids = new.sim_id.astype(str).to_numpy()
    yn = new.has_keyhole.to_numpy(int); xn = new[F].to_numpy(float); idn = new.sim_id.astype(str).to_numpy()
    out = []
    for s in splits:
        te_local = np.asarray(s["test_indices"]); tr_local = np.asarray(s["train_indices"])
        q = q20_for(xn, yn, idn, te_local)
        out.append({"task": "R2_TRANSFER" if prior_old else "R3_NEW", "repeat": int(s["repeat"]), "fold": int(s["fold"]), "block": block_of(int(s["repeat"])),
                    "X": X, "y": y, "depth": np.full(len(y), np.nan), "pool": tr_local + off, "test": te_local + off, "prior": prior,
                    "q20": q, "seed": [1819 if prior_old else 1820, int(s["repeat"]), int(s["fold"])]})
    return out


def r3_old_tasks(prior_new=False, with_depth=True):
    new, old = new_old_frames()
    from src import week8_5_frozen_sample_efficiency_confirmation as w85
    man = pd.read_csv(ROOT / "outputs/week8_5_frozen_confirmation/split_manifest.csv", usecols=["run_id", "repeat", "fold", "role", "population_row_index"])
    dist = w85.b1_distance(old.rename(columns={"sim_id": "experiment_name"}))
    pop = pd.read_csv(ROOT / "outputs/week7_06_real_data_boundary_active_level_set/primary_common_population.csv", usecols=["experiment_name", "max_depth_um"])
    depth_old = old.sim_id.map(dict(zip(pop.experiment_name, pop.max_depth_um))).to_numpy(float) if with_depth else np.full(len(old), np.nan)
    if prior_new:
        X = np.r_[old[F].to_numpy(float), new[F].to_numpy(float)]; y = np.r_[old.has_keyhole.to_numpy(int), new.has_keyhole.to_numpy(int)]
        prior = np.arange(len(old), len(old) + len(new)); depth = np.r_[depth_old, np.full(len(new), np.nan)]
    else:
        X = old[F].to_numpy(float); y = old.has_keyhole.to_numpy(int); prior = np.array([], int); depth = depth_old
    out = []
    for run, g in man.groupby("run_id"):
        rep, fold = int(g.repeat.iloc[0]), int(g.fold.iloc[0])
        te = g[g.role == "untouched_test"].population_row_index.to_numpy(); pool = g[g.role == "training_pool"].population_row_index.to_numpy()
        order = np.lexsort((old.sim_id.to_numpy(object)[te], dist[te])); q = np.zeros(len(te), bool); q[order[:math.ceil(.2 * len(te))]] = True
        out.append({"task": "R2rev_TRANSFER" if prior_new else "R3_OLD", "repeat": rep, "fold": fold, "block": block_of(rep), "X": X, "y": y,
                    "depth": depth, "pool": pool, "test": te, "prior": prior, "q20": q, "seed": [1821 if prior_new else 1822, rep, fold]})
    return out


def all_real(block="DEV"):
    T = pooled_tasks() + r3_new_tasks(False) + r3_new_tasks(True) + r3_old_tasks(False) + r3_old_tasks(True)
    return [t for t in T if t["block"] == block]


def attach_old_depth(T):
    """Attach OLD max depth to R1_POOLED (OLD rows) and R2_TRANSFER (OLD prior rows); NEW rows stay NaN (no NEW
    continuous outputs in the repository, RESEARCH_LOG D1).  R3_OLD / R2rev already carry OLD depth."""
    pop = pd.read_csv(ROOT / "outputs/week7_06_real_data_boundary_active_level_set/primary_common_population.csv", usecols=["experiment_name", "max_depth_um"])
    dmap = dict(zip(pop.experiment_name, pop.max_depth_um))
    D = pooled_frame()
    from src.week12_development_common import load_old
    o = load_old()
    for t in T:
        if t["task"] == "R1_POOLED":
            t["depth"] = D.sim_id.map(dmap).to_numpy(float)
        if t["task"] == "R2_TRANSFER":
            t["depth"] = np.r_[o.sim_id.map(dmap).to_numpy(float), np.full(len(t["y"]) - len(o), np.nan)]
    return T


def all_real_with_depth(block="DEV"):
    return attach_old_depth(all_real(block))

