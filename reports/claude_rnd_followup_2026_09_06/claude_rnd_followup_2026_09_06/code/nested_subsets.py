"""Section 8: does adding labels hurt M3 under LABEL-BLIND nested subsets?

Nested sequences on each of 20 outer runs (one fold per repeat), sizes 16..120 (step 4) then 160, 200, 260, 324:
  MAXIMIN  : feature-only maximin order over the whole training pool (extends the B16 design)
  MARGIN   : committed Phase 1.14 M3-margin path (16..80) then continued by margin to 120, then maximin fill
  RANDOM   : seeded random order after the shared B16 design (3 seeds, averaged)
  BAND     : shared B16, then band rows in random order (3 seeds), then the rest in random order
  CAMPAIGN : shared B16, then rows in random order but campaign-balanced (round-robin over partitions)
Metrics: q20/q30/full accuracy, BA, KH recall for M3 and for M3R(eps=0.05, fixed hyper).
"""
import sys, json, math, time, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/rnd"); sys.path.insert(0, "/home/claude/rnd/followup")
from joblib import Parallel, delayed
from scipy.spatial import distance
from sklearn.preprocessing import StandardScaler
from core import *
from m3r_tests import m3r_from_m3, P1

d = Data(); pop = d.population; y = d.labels; lh = d.logh; x4 = d.x4
band = (lh >= 20.3621) & (lh <= 21.2533); part = pop.partition.to_numpy()
SIZES = list(range(16, 121, 4)) + [160, 200, 260, 324]


def maximin_order(train, seed_init):
    scaled = StandardScaler().fit_transform(x4[train]); chosen = list(seed_init)
    local = {int(t): i for i, t in enumerate(train)}; chosen_local = [local[c] for c in chosen]
    while len(chosen_local) < len(train):
        remaining = np.setdiff1d(np.arange(len(train)), np.asarray(chosen_local), assume_unique=True)
        nearest = distance.cdist(scaled[remaining], scaled[chosen_local]).min(axis=1); best = nearest.max()
        ties = remaining[np.isclose(nearest, best, rtol=1e-12, atol=1e-14)]; chosen_local.append(int(ties[np.argmin(train[ties])]))
    return [int(train[i]) for i in chosen_local]


def margin_order(spec, train, init):
    q = list(P1[spec.run_id])
    while len(q) < 120:
        m = M3(d, spec).fit(np.asarray(q), len(q)); cand = np.setdiff1d(train, np.asarray(q)); q.append(margin_select(cand, m.proba(cand)))
    rest = maximin_order(train, q)  # deterministic fill
    return q + [r for r in rest if r not in set(q)]


def eval_seq(spec, seq, name, seed=None):
    tr = np.asarray(spec.train_indices); te = np.asarray(spec.test_indices); fl = d.flags(spec); rows = []
    X = None
    for n in SIZES:
        if n > len(seq): break
        rev = np.asarray(seq[:n]); m3 = M3(d, spec).fit(rev, n); fit = m3.fit_; X = fit.x_scaler.transform(x4); mean_all = fit.physics.latent(lh)
        preds = {"M3": m3.proba(te), "M3R05": m3r_from_m3(fit, X[rev], mean_all[rev], y[rev], 0.05).proba(X[te], mean_all[te])}
        for model, pr in preds.items():
            row = {"run_id": spec.run_id, "repeat": spec.repeat, "seq": name, "seed": seed, "n": n, "model": model, "frac_band_in_train": float(band[rev].mean())}
            for subset, flag in (("full", np.ones(len(te), bool)), ("q20", fl["B1_q20"]), ("q30", fl["B1_q30"])):
                mv = metric_values(y[te][flag], pr[flag]); row.update({f"{subset}_acc": mv["accuracy"], f"{subset}_ba": mv["balanced_accuracy"], f"{subset}_khrec": mv["keyhole_recall"]})
            rows.append(row)
    return rows


def run(spec):
    tr = np.asarray(spec.train_indices); init = list(map(int, w85.initial_design(spec, d.population))); rows = []
    rows += eval_seq(spec, maximin_order(tr, init), "MAXIMIN")
    rows += eval_seq(spec, margin_order(spec, tr, init), "MARGIN")
    rest = np.setdiff1d(tr, np.asarray(init))
    for s in range(3):
        rng = np.random.default_rng(seed_u32("nested", spec.run_id, s))
        rows += eval_seq(spec, init + [int(v) for v in rng.permutation(rest)], "RANDOM", s)
        b_in = rest[band[rest]]; b_out = rest[~band[rest]]
        rows += eval_seq(spec, init + [int(v) for v in rng.permutation(b_in)] + [int(v) for v in rng.permutation(b_out)], "BAND", s)
        groups = [list(rng.permutation(rest[part[rest] == p])) for p in np.unique(part[rest])]; seq = list(init)
        while any(groups):
            for g in groups:
                if g: seq.append(int(g.pop()))
        rows += eval_seq(spec, seq, "CAMPAIGN", s)
    return rows


if __name__ == "__main__":
    specs = [s for s in d.specs if s.fold == ((s.repeat - 1) % 5) + 1]
    t0 = time.time(); out = Parallel(n_jobs=2, verbose=5)(delayed(run)(s) for s in specs)
    pd.DataFrame([r for rows in out for r in rows]).to_csv("/home/claude/rnd/followup/results/nested_subsets.csv.gz", index=False); print("elapsed", time.time() - t0)
