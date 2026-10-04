"""Week 15 real-data secondary replays (executed only after the freeze).

NEW-136 (POST-HOC), OLD-405 Week 8.5 repeats 1-4 (HISTORICAL), Masinelli Ti64/316L (EXTERNAL).
Policies: random, margin, EBR-D (frozen definition).  Model: fixed-hyperparameter Laplace GPC; for
OLD/NEW the hyperparameters are the historical G3 ML-II fit on OLD-405 (Week 12, no NEW labels); for
Masinelli they are fitted on the *other* material.  Endpoints: historical-style q20 accuracy on test
folds, pooled out-of-fold balanced accuracy, pooled DC-BD (Week 15 metric), minority recall.
"""
from __future__ import annotations

import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.preprocessing import StandardScaler

from src.week13_synthetic_al import maximin_order
from src.week15_ebr import knn_graph, latent_mv, lookahead_scores, make_gp
from src.week15_metric import dc_boundary_dice

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week15_boundary_acquisition/real_data"
W12 = ROOT / "outputs/week12_startup_and_transfer_development"
F = ["P", "VX", "LS", "ST"]
REAL_POLICIES = ("random", "margin", "ebrd")


def g3_hypers(Z, y):
    from sklearn.gaussian_process import GaussianProcessClassifier
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern
    g = GaussianProcessClassifier(ConstantKernel(1.0, (1e-3, 1e3)) * Matern(np.ones(Z.shape[1]), (1e-2, 1e2), nu=1.5),
                                  n_restarts_optimizer=0, random_state=0).fit(Z, y)
    return {"ls": np.asarray(g.kernel_.k2.length_scale, float).tolist(), "var": float(g.kernel_.k1.constant_value)}


def path(z_tr, y_tr, z_te, hyp, policy, seed, b0=8, B=80, step=4):
    """Return {budget: test probabilities} for one acquisition path on a training pool."""
    rng = np.random.default_rng(seed)
    order = maximin_order(z_tr, np.random.default_rng([seed[0], seed[1], 2]))
    L = list(order[:b0]); k = b0
    while len(set(y_tr[L])) < 2:
        L.append(int(order[k])); k += 1
    lo, hi = z_tr.min(0), z_tr.max(0)
    Zref = lo + (hi - lo) * np.random.default_rng([15, 97]).random((400, z_tr.shape[1])); Eref = knn_graph(Zref, 8)
    out = {}
    while True:
        gp = make_gp(hyp).fit(z_tr[L], y_tr[L])
        b = len(L)
        if b % step == 0 and b >= 2 * b0 // 2:
            out[b] = gp.proba(z_te)
        if b >= B:
            return out
        cands = np.setdiff1d(np.arange(len(z_tr)), L)
        if policy == "random":
            L.append(int(rng.choice(cands)))
        elif policy == "margin":
            mu, var = latent_mv(gp, z_tr[cands]); p = 1 / (1 + np.exp(-mu / np.sqrt(1 + np.pi * var / 8)))
            L.append(int(cands[np.argmin(np.abs(p - .5))]))
        else:
            sc, _ = lookahead_scores(z_tr, y_tr, L, cands, hyp, Zref, Eref, "EBRD")
            L.append(int(cands[np.argmax(sc)]))


def score_pooled(z_eval, y, pred_by_row, q20_mask, minority):
    yh = (pred_by_row >= .5).astype(int)
    ba = (np.mean(yh[y == 1] == 1) + np.mean(yh[y == 0] == 0)) / 2
    return {"BA_pooled": float(ba), "DC_BD_pooled": dc_boundary_dice(z_eval, y, yh)["DC_BD"],
            "q20_accuracy_pooled": float(np.mean(yh[q20_mask] == y[q20_mask])),
            "minority_recall": float(np.mean(yh[y == minority] == minority))}


def run_new():
    old = pd.read_csv(W12 / "audit/old405_inputs_labels.csv"); new = pd.read_csv(W12 / "audit/new136.csv")
    sc = StandardScaler().fit(old[F]); hyp = g3_hypers(sc.transform(old[F]), old.has_keyhole.to_numpy())
    zn = sc.transform(new[F]); yn = new.has_keyhole.to_numpy()
    z_eval = StandardScaler().fit_transform(new[F])
    q = pd.read_csv(W12 / "active_learning/predictions.csv.gz", usecols=["split_id", "arm", "budget", "row_index", "q20"])
    q = q[(q.arm == "M3_margin__maximin16_continue") & (q.budget == 80)][["split_id", "row_index", "q20"]]
    splits = json.loads((W12 / "audit/original_splits.json").read_text())
    def one(s, pol):
        tr, te = np.asarray(s["train_indices"]), np.asarray(s["test_indices"])
        res = path(zn[tr], yn[tr], zn[te], hyp, pol, [15, s["repeat"] * 10 + s["fold"]])
        return s, te, res
    jobs = [(s, p) for p in REAL_POLICIES for s in splits]
    res = Parallel(n_jobs=7)(delayed(one)(s, p) for s, p in jobs)
    rows = []
    qm = {(r.split_id, r.row_index): r.q20 for r in q.itertuples()}
    for (s, p), (_, te, out) in zip(jobs, res):
        for b, pr in out.items():
            for i, row in enumerate(te):
                rows.append({"repeat": s["repeat"], "fold": s["fold"], "policy": p, "budget": b, "row": int(row), "prob": float(pr[i]),
                             "q20": bool(qm[(s["split_id"], int(row))])})
    P = pd.DataFrame(rows)
    out = []
    for (rep, pol, b), g in P.groupby(["repeat", "policy", "budget"]):
        pr = np.full(136, np.nan); pr[g.row.to_numpy()] = g.prob.to_numpy()
        mask = np.zeros(136, bool); mask[g.row.to_numpy()[g.q20.to_numpy()]] = True
        qacc = np.mean([np.mean((f.prob[f.q20] >= .5).astype(int) == yn[f.row[f.q20]]) for _, f in g.groupby("fold")])
        out.append({"campaign": "NEW", "repeat": rep, "policy": pol, "budget": b, "q20_accuracy_meanfold": float(qacc),
                    **score_pooled(z_eval, yn, pr, mask, 0)})
    return pd.DataFrame(out), hyp


def run_old():
    old = pd.read_csv(W12 / "audit/old405_inputs_labels.csv")
    sc = StandardScaler().fit(old[F]); zo = sc.transform(old[F]); yo = old.has_keyhole.to_numpy()
    hyp = g3_hypers(zo, yo)
    from src import week8_5_frozen_sample_efficiency_confirmation as w85
    man = pd.read_csv(ROOT / "outputs/week8_5_frozen_confirmation/split_manifest.csv", usecols=["run_id", "repeat", "fold", "role", "population_row_index"])
    man = man[man.repeat <= 4]
    dist = w85.b1_distance(old.rename(columns={"sim_id": "experiment_name"}))
    def one(run, g, pol):
        tr = g[g.role == "training_pool"].population_row_index.to_numpy(); te = g[g.role == "untouched_test"].population_row_index.to_numpy()
        return run, int(g.repeat.iloc[0]), int(g.fold.iloc[0]), te, path(zo[tr], yo[tr], zo[te], hyp, pol, [16, int(g.repeat.iloc[0]) * 10 + int(g.fold.iloc[0])])
    jobs = [(run, g, p) for p in REAL_POLICIES for run, g in man.groupby("run_id")]
    res = Parallel(n_jobs=7)(delayed(one)(*j) for j in jobs)
    z_eval = StandardScaler().fit_transform(old[F])
    out = []
    by = {}
    for (run, g, pol), (_, rep, fold, te, o) in zip(jobs, res):
        order = np.lexsort((old.sim_id.to_numpy(object)[te], dist[te]))
        qmask = np.zeros(len(te), bool); qmask[order[:math.ceil(.2 * len(te))]] = True
        for b, pr in o.items():
            by.setdefault((rep, pol, b), []).append((te, pr, qmask))
    for (rep, pol, b), parts in by.items():
        pr = np.full(405, np.nan); mask = np.zeros(405, bool); qa = []
        for te, p_, qm in parts:
            pr[te] = p_; mask[te[qm]] = True; qa.append(np.mean((p_[qm] >= .5).astype(int) == yo[te][qm]))
        out.append({"campaign": "OLD", "repeat": rep, "policy": pol, "budget": b, "q20_accuracy_meanfold": float(np.mean(qa)),
                    **score_pooled(z_eval, yo, pr, mask, 1)})
    return pd.DataFrame(out), hyp


def run_masinelli():
    from src.week14_real_checks import load_masinelli
    mas = load_masinelli()
    out = []
    for mat, other in (("Ti64", "316L"), ("316L", "Ti64")):
        d, o = mas[mat], mas[other]
        X = np.c_[np.log(d.P), np.log(d.V)]; Xo = np.c_[np.log(o.P), np.log(o.V)]
        sc = StandardScaler().fit(Xo); hyp = g3_hypers(sc.transform(Xo), o.y.values)
        z = sc.transform(X); y = d.y.values; z_eval = StandardScaler().fit_transform(X)
        from src.week13_boundary_metrics import nearest_opposite
        dist, _ = nearest_opposite(z_eval, y)
        minority = int(y.mean() > .5) ^ 1
        for rep in range(4):
            perm = np.random.default_rng([17, rep, ("Ti64", "316L").index(mat)]).permutation(len(y))
            folds = np.array_split(perm, 5)
            for pol in REAL_POLICIES:
                pr_b, qa_b = {}, {}
                for k, te in enumerate(folds):
                    tr = np.setdiff1d(perm, te)
                    o_ = path(z[tr], y[tr], z[te], hyp, pol, [18, rep * 10 + k], b0=4, B=30, step=2)
                    order = np.argsort(dist[te], kind="stable"); qm = np.zeros(len(te), bool); qm[order[:math.ceil(.2 * len(te))]] = True
                    for b, p_ in o_.items():
                        pr_b.setdefault(b, np.full(len(y), np.nan))[te] = p_
                        qa_b.setdefault(b, []).append(np.mean((p_[qm] >= .5).astype(int) == y[te][qm]))
                for b, pr in pr_b.items():
                    if np.isnan(pr).any():
                        continue
                    mask = np.zeros(len(y), bool)
                    out.append({"campaign": f"Masinelli_{mat}", "repeat": rep, "policy": pol, "budget": b,
                                "q20_accuracy_meanfold": float(np.mean(qa_b[b])), **{k_: v for k_, v in score_pooled(z_eval, y, pr, np.ones(len(y), bool), minority).items() if k_ != "q20_accuracy_pooled"}})
    return pd.DataFrame(out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    new, hyp_new = run_new(); new.to_csv(OUT / "new_replays.csv", index=False)
    old, hyp_old = run_old(); old.to_csv(OUT / "old_replays.csv", index=False)
    mas = run_masinelli(); mas.to_csv(OUT / "masinelli_replays.csv", index=False)
    (OUT / "hyperparameters.json").write_text(json.dumps({"OLD_G3_ML2": hyp_old, "used_for_NEW": hyp_new}, indent=2))


if __name__ == "__main__":
    main()
