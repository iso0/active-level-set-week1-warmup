"""Week 14 real-data checks — executed only AFTER the pre-result freeze commit.

Evidence tags: HISTORICAL OLD (OLD-405), POST-HOC NEW (NEW-136, already open), EXTERNAL/PUBLIC
(Masinelli et al. 2025 Ti64 / 316L bundles).  The 49 Bug-withheld NEW outcomes are not used.
Nothing here selects or tunes a method; every candidate and setting is fixed in
CONFIRMATORY_BENCHMARK_FREEZE.md.
"""
from __future__ import annotations

import argparse
import json
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from src.week13_boundary_metrics import edge_metrics, gabriel_edges
from src.week14_metrics import weighted_edge_metrics
from src.week14_discovery import maximin, score_extremes
from src.week14_models import closure_override, fit_model
from src.week14_order import (SIGNS_O3, closure_labels, dominance, first_both, front_discovery_order,
                              interleave, maximal, minimal)

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week14_research_program/real_data"
W12 = ROOT / "outputs/week12_startup_and_transfer_development"
P10 = ROOT / "outputs/week9_phase1_10_external_experimental_validation"
F = ["P", "VX", "LS", "ST"]


def load_old_new():
    old = pd.read_csv(W12 / "audit/old405_inputs_labels.csv")
    new = pd.read_csv(W12 / "audit/new136.csv")
    return old, new


def to_log(x):
    """Monotone transform used by all models: (log P, log VX, log LS, ST)."""
    x = np.asarray(x, float)
    return np.c_[np.log(x[:, 0]), np.log(x[:, 1]), np.log(x[:, 2]), x[:, 3]]


def load_masinelli():
    out = {}
    for mat, fn in (("Ti64", "ti64"), ("316L", "ss316")):
        d = pd.read_csv(P10 / f"{fn}_oof_predictions.csv.gz")
        d = d[(d.repeat == 0) & (d.model == d.model.iloc[0])].drop_duplicates("bundle_id")
        m = d.condition_id.str.extract(r"_P(\d+)_V(\d+)").astype(float)
        out[mat] = pd.DataFrame({"bundle_id": d.bundle_id.values, "P": m[0].values, "V": m[1].values,
                                 "y": d.truth.astype(int).values})
    return out


# ------------------------------------------------------------------------------------- discovery
def discovery_orders(u, signs, score, rng, y=None):
    z = StandardScaler().fit_transform(u)
    mm = maximin(z, int(rng.integers(len(u))))
    D = dominance(u, signs)
    fr, mn, mx = front_discovery_order(D, np.arange(len(u)), score=score)
    front = np.r_[fr, [i for i in mm if i not in set(fr)]].astype(int)
    rand = rng.permutation(len(u))
    out = {"RAND": rand, "MAXI": mm, "SCORE": score_extremes(score), "FRONT": front,
           "HEDGE": interleave(mm, front, score_extremes(score)), "HEDGE_FR": interleave(front, rand)}
    if y is not None:
        seeds = list(mm[:8]); seen = set(y[seeds])
        if len(seen) == 2:
            out["ADAPT8"] = mm
        else:
            rest = [i for i in np.argsort(score * (1 if 1 in seen else -1), kind="stable") if i not in set(seeds)]
            out["ADAPT8"] = np.asarray(seeds + rest, int)
    return out, len(mn), len(mx)


def real_discovery():
    old, new = load_old_new()
    rows = []
    splits = json.loads((W12 / "audit/original_splits.json").read_text())
    for s in splits:   # POST-HOC NEW: the 100 original training pools
        tr = np.asarray(s["train_indices"], int)
        u = to_log(new[F].to_numpy()[tr]); y = new.has_keyhole.to_numpy()[tr]
        rng = np.random.default_rng([14, 9, s["repeat"], s["fold"]])
        orders, nmin, nmax = discovery_orders(u, SIGNS_O3, new.log_h.to_numpy()[tr], rng, y)
        D = dominance(u, SIGNS_O3)
        for k, o in orders.items():
            rows.append({"campaign": "NEW", "pool": s["split_id"], "strategy": k, "T_both": first_both(o, y),
                         "n_min": nmin, "n_max": nmax, "violations": int((D & (y[:, None] == 1) & (y[None, :] == 0)).sum()),
                         "minority_on_min_front": int((y[minimal(D)] == 0).sum())})
    man = pd.read_csv(ROOT / "outputs/week8_5_frozen_confirmation/split_manifest.csv", usecols=["run_id", "role", "population_row_index"])
    for run, g in man[man.role.eq("training_pool")].groupby("run_id"):   # HISTORICAL OLD
        tr = g.population_row_index.to_numpy(int)
        u = to_log(old[F].to_numpy()[tr]); y = old.has_keyhole.to_numpy()[tr]
        rng = np.random.default_rng([14, 8, int(run.split("_r")[1].split("_")[0]), int(run.split("_f")[1])])
        orders, nmin, nmax = discovery_orders(u, SIGNS_O3, old.log_h.to_numpy()[tr], rng, y)
        D = dominance(u, SIGNS_O3)
        for k, o in orders.items():
            rows.append({"campaign": "OLD", "pool": run, "strategy": k, "T_both": first_both(o, y), "n_min": nmin, "n_max": nmax,
                         "violations": int((D & (y[:, None] == 1) & (y[None, :] == 0)).sum()),
                         "minority_on_max_front": int((y[maximal(D)] == 1).sum())})
    mas = load_masinelli()  # EXTERNAL: minority subsampled to K in {1,2,3}
    for mat, d in mas.items():
        for minority in (0, 1):
            for K in (1, 2, 3):
                for rep in range(200):
                    rng = np.random.default_rng([14, 7, ("Ti64", "316L").index(mat), minority, K, rep])
                    keep_min = rng.choice(np.nonzero(d.y.values == minority)[0], K, replace=False)
                    idx = np.r_[np.nonzero(d.y.values != minority)[0], keep_min]
                    u = np.c_[np.log(d.P.values[idx]), np.log(d.V.values[idx])]
                    y = d.y.values[idx]
                    score = u[:, 0] - .5 * u[:, 1]
                    orders, nmin, nmax = discovery_orders(u, np.array([1, -1]), score, rng, y)
                    for k, o in orders.items():
                        rows.append({"campaign": f"Masinelli_{mat}", "pool": f"min{minority}_K{K}_r{rep}", "strategy": k,
                                     "T_both": first_both(o, y), "n_min": nmin, "n_max": nmax, "K": K, "minority_class": minority})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "real_discovery.csv", index=False)
    return df


# ------------------------------------------------------------------------------------- models
MODELS = ("H", "M3", "G3", "G3S", "G3C")


def score_models(Xtr, ytr, str_, Xte, yte, ste, signs, tag, extra=None):
    rows = []
    for m in MODELS:
        try:
            f = fit_model(m, Xtr, ytr, str_, signs, seed=0)
            p = f.predict(Xte, ste)
            yh = (p >= .5).astype(int)
            minority = int(yte.mean() > .5) ^ 1
            r = {"setting": tag, "model": m, "ok": True, "n_train": len(ytr), "n_test": len(yte),
                 "BA": (np.mean(yh[yte == 1] == 1) + np.mean(yh[yte == 0] == 0)) / 2 if 0 < yte.mean() < 1 else np.nan,
                 "minority_recall": float(np.mean(yh[yte == minority] == minority)) if (yte == minority).any() else np.nan,
                 "majority_recall": float(np.mean(yh[yte != minority] != minority)),
                 "AUC": roc_auc_score(yte, p) if 0 < yte.mean() < 1 else np.nan}
            if m == "G3C":
                _, lab = closure_override(np.full(len(yte), .5), Xtr, ytr, Xte, signs)
                r["closure_coverage"] = float(np.mean(lab >= 0))
                r["closure_errors"] = int(((lab >= 0) & (lab != yte)).sum())
                r["closure_implied"] = int((lab >= 0).sum())
            r.update(extra or {})
            rows.append(r)
        except Exception as exc:
            rows.append({"setting": tag, "model": m, "ok": False, "error": repr(exc)[:200], **(extra or {})})
    return rows


def real_models():
    old, new = load_old_new()
    rows = []
    Xo, yo, so = to_log(old[F].to_numpy()), old.has_keyhole.to_numpy(), old.log_h.to_numpy()
    Xn, yn, sn = to_log(new[F].to_numpy()), new.has_keyhole.to_numpy(), new.log_h.to_numpy()
    rows += score_models(Xo, yo, so, Xn, yn, sn, SIGNS_O3, "POSTHOC_OLD_to_NEW")
    from joblib import Parallel, delayed   # parallel execution only; results are deterministic per split
    sp = json.loads((W12 / "audit/original_splits.json").read_text())
    res = Parallel(n_jobs=7)(delayed(score_models)(Xn[np.asarray(s["train_indices"])], yn[np.asarray(s["train_indices"])], sn[np.asarray(s["train_indices"])],
                                                   Xn[np.asarray(s["test_indices"])], yn[np.asarray(s["test_indices"])], sn[np.asarray(s["test_indices"])],
                                                   SIGNS_O3, "POSTHOC_NEW_only", {"split": s["split_id"], "repeat": s["repeat"]}) for s in sp)
    rows += [x for r in res for x in r]
    man = pd.read_csv(ROOT / "outputs/week8_5_frozen_confirmation/split_manifest.csv", usecols=["run_id", "repeat", "role", "population_row_index"])
    jobs = []
    for run, g in man.groupby("run_id"):
        tr = g[g.role.eq("training_pool")].population_row_index.to_numpy(int)
        te = g[g.role.eq("untouched_test")].population_row_index.to_numpy(int)
        jobs.append((tr, te, run, int(g.repeat.iloc[0])))
    res = Parallel(n_jobs=7)(delayed(score_models)(Xo[tr], yo[tr], so[tr], Xo[te], yo[te], so[te], SIGNS_O3, "HISTORICAL_OLD_indomain",
                                                   {"split": run, "repeat": rep}) for tr, te, run, rep in jobs)
    rows += [x for r in res for x in r]
    mas = load_masinelli()
    for a, b in (("Ti64", "316L"), ("316L", "Ti64")):
        da, db = mas[a], mas[b]
        Xa, Xb = np.c_[np.log(da.P), np.log(da.V)], np.c_[np.log(db.P), np.log(db.V)]
        rows += score_models(Xa, da.y.values, Xa[:, 0] - .5 * Xa[:, 1], Xb, db.y.values, Xb[:, 0] - .5 * Xb[:, 1],
                             np.array([1, -1]), f"EXTERNAL_{a}_to_{b}")
    for mat, d in mas.items():
        X = np.c_[np.log(d.P), np.log(d.V)]
        for nt in (10, 20):
            for rep in range(50):
                rng = np.random.default_rng([14, 6, ("Ti64", "316L").index(mat), nt, rep])
                while True:
                    tr = rng.choice(len(d), nt, replace=False)
                    if 0 < d.y.values[tr].mean() < 1:
                        break
                te = np.setdiff1d(np.arange(len(d)), tr)
                rows += score_models(X[tr], d.y.values[tr], X[tr, 0] - .5 * X[tr, 1], X[te], d.y.values[te],
                                     X[te, 0] - .5 * X[te, 1], np.array([1, -1]), f"EXTERNAL_{mat}_within_n{nt}", {"repeat": rep})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "real_models.csv", index=False)
    return df


# ------------------------------------------------------------------------------------- metrics and information
def real_metric_rescore():
    """POST-HOC NEW: length-weighted cut-edge metrics on the retained Week 12 paths (descriptive)."""
    _, new = load_old_new()
    z = StandardScaler().fit_transform(new[F].to_numpy())
    y = new.has_keyhole.to_numpy()
    e = gabriel_edges(z)
    pred = pd.read_csv(W12 / "active_learning/predictions.csv.gz", usecols=["arm", "repeat", "budget", "row_index", "probability"])
    rows = []
    for (arm, rep, b), g in pred.groupby(["arm", "repeat", "budget"]):
        yh = np.empty(136, int); yh[g.row_index.to_numpy()] = (g.probability.to_numpy() >= .5)
        r = {"arm": arm, "repeat": rep, "budget": b, **{k: v for k, v in edge_metrics(e, y, yh).items() if k in ("BER", "BEF1")},
             **weighted_edge_metrics(e, z, y, yh)}
        rows.append(r)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "new_week12_paths_weighted_metrics.csv.gz", index=False)
    return df


def information_sufficiency():
    """Proposition I1 on both campaigns: fraction of rare cases dominated (rare direction) by another rare case."""
    old, new = load_old_new()
    out = {}
    for name, d, rare in (("OLD", old, 1), ("NEW", new, 0)):
        u = to_log(d[F].to_numpy()); y = d.has_keyhole.to_numpy()
        D = dominance(u, SIGNS_O3)
        r = np.nonzero(y == rare)[0]
        sub = D[np.ix_(r, r)]
        # rare = 1 (OLD): certified if some other rare is below it; rare = 0 (NEW): if some other rare is above it
        cert = sub.any(axis=0) if rare == 1 else sub.any(axis=1)
        out[name] = {"rare_class": rare, "K": int(len(r)), "LOO_front_certified_fraction": float(cert.mean()),
                     "rare_front_size": int((~cert).sum())}
    (OUT / "information_sufficiency.json").write_text(json.dumps(out, indent=2))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="all")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.part in ("all", "discovery"):
        real_discovery()
    if a.part in ("all", "models"):
        real_models()
    if a.part in ("all", "metrics"):
        real_metric_rescore()
    if a.part in ("all", "info"):
        information_sufficiency()


if __name__ == "__main__":
    main()
