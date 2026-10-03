"""Week 13 real-data diagnostics (EXPLORATORY; no model is refitted).

Reads only already-open artifacts: OLD-405 labels, NEW-136 included labels,
the Week 8.5 checkpoint confusion counts and the Week 12 retained
NEW-only active-learning predictions/query paths.  Nothing here changes a
historical endpoint; every new quantity is labelled exploratory.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.week13_boundary_metrics import (band_decomposition, cut_edges, edge_metrics,
                                         gabriel_edges, knn_edges, nearest_opposite,
                                         standardize)

ROOT = Path(__file__).resolve().parents[1]
W12 = ROOT / "outputs/week12_startup_and_transfer_development"
W85 = ROOT / "outputs/week8_5_frozen_confirmation"
OUT = ROOT / "outputs/week13_boundary_evaluation_and_mechanisms/real_data"
# per-budget Week 8.5 trajectories, extracted unchanged from
# outputs/week8_5_frozen_confirmation/week8_5_large_machine_readable_artifacts.tar.gz
import os
W85_TRAJ = Path(os.environ.get("W85_TRAJ", ROOT / "outputs/week8_5_frozen_confirmation/_extracted/trajectory_per_budget.csv"))


def ensure_w85_trajectories():
    """Extract the unchanged per-budget Week 8.5 table from its archived tarball if needed (not committed)."""
    global W85_TRAJ
    if W85_TRAJ.exists():
        return
    import tarfile
    import tempfile
    dest = Path(tempfile.gettempdir()) / "week13_w85"
    dest.mkdir(exist_ok=True)
    with tarfile.open(W85 / "week8_5_large_machine_readable_artifacts.tar.gz") as tar:
        tar.extract("trajectory_per_budget.csv", dest)
    W85_TRAJ = dest / "trajectory_per_budget.csv"
FEATURES = ["P", "VX", "LS", "ST"]


def aulc(budgets, values, lo=16, hi=80):
    b = np.asarray(budgets)
    v = np.asarray(values, float)
    m = (b >= lo) & (b <= hi)
    o = np.argsort(b[m])
    return float(np.trapezoid(v[m][o], b[m][o]) / (hi - lo))


def load():
    new = pd.read_csv(W12 / "audit/new136.csv")
    old = pd.read_csv(W12 / "audit/old405_inputs_labels.csv")
    return old, new


# ---------------------------------------------------------------- A1: band composition
def band_composition(old, new):
    rows = []
    # NEW: Week 11/12 construction, nearest opposite over the entire 136 batch
    splits = json.loads((W12 / "audit/original_splits.json").read_text())
    z = standardize(new[FEATURES])
    y = new.has_keyhole.to_numpy(int)
    dist, arg = nearest_opposite(z, y)
    for s in splits:
        test = np.asarray(s["test_indices"])
        order = np.lexsort((new.sim_id.to_numpy(object)[test], dist[test]))
        q = test[order[:int(np.ceil(.2 * len(test)))]]
        maj = 1
        majq = q[y[q] == maj]
        rows.append({"campaign": "NEW", "split_id": s["split_id"], "n_test": len(test), "n_q20": len(q),
                     "minority_in_test": int((y[test] != maj).sum()), "minority_in_q20": int((y[q] != maj).sum()),
                     "majority_share_q20": float(np.mean(y[q] == maj)),
                     "distinct_minority_targets_of_q20_majority": int(len(set(arg[majq]))) if len(majq) else 0})
    # OLD: Week 8.5 construction, B1 distance over all 405
    man = pd.read_csv(W85 / "split_manifest.csv", usecols=["run_id", "role", "population_row_index", "experiment_name"])
    zo = standardize(old[FEATURES])
    yo = old.has_keyhole.to_numpy(int)
    disto, argo = nearest_opposite(zo, yo)
    for run, g in man[man.role.eq("untouched_test")].groupby("run_id"):
        test = g.population_row_index.to_numpy(int)
        order = np.lexsort((old.sim_id.to_numpy(object)[test], disto[test]))
        q = test[order[:int(np.ceil(.2 * len(test)))]]
        maj = 0
        majq = q[yo[q] == maj]
        rows.append({"campaign": "OLD", "split_id": run, "n_test": len(test), "n_q20": len(q),
                     "minority_in_test": int((yo[test] != maj).sum()), "minority_in_q20": int((yo[q] != maj).sum()),
                     "majority_share_q20": float(np.mean(yo[q] == maj)),
                     "distinct_minority_targets_of_q20_majority": int(len(set(argo[majq]))) if len(majq) else 0})
    frame = pd.DataFrame(rows)
    # pool-level hubness: how many majority points name each minority point as nearest opposite
    hub = []
    for name, zz, yy, maj in (("OLD", zo, yo, 0), ("NEW", z, y, 1)):
        d, a = nearest_opposite(zz, yy)
        counts = pd.Series(a[yy == maj]).value_counts()
        minority = np.nonzero(yy != maj)[0]
        c = counts.reindex(minority, fill_value=0).to_numpy()
        hub.append({"campaign": name, "n": len(yy), "n_minority": len(minority), "minority_label": 1 - maj,
                    "pool_majority_share": float(np.mean(yy == maj)),
                    "mean_majority_per_minority_target": float(c.mean()), "max": int(c.max()),
                    "minority_never_targeted": int((c == 0).sum()),
                    "median_nearest_opposite_minority": float(np.median(d[yy != maj])),
                    "median_nearest_opposite_majority": float(np.median(d[yy == maj]))})
    return frame, pd.DataFrame(hub)


# ---------------------------------------------------------------- A2: NEW AL metric recomputation
def new_al_metrics(new):
    pred = pd.read_csv(W12 / "active_learning/predictions.csv.gz")
    y = new.set_index("row_index").has_keyhole
    z = standardize(new[FEATURES])
    yall = new.has_keyhole.to_numpy(int)
    gab = gabriel_edges(z)
    graphs = {"gabriel": gab, "knn5": knn_edges(z, 5), "knn10": knn_edges(z, 10)}
    pred["yhat"] = (pred.probability >= .5).astype(int)
    # add the always-Keyhole reference as a pseudo-arm with identical rows
    ref = pred[pred.arm.eq("M3_margin__maximin16_continue")].copy()
    ref["arm"] = "ALWAYS_KEYHOLE_reference"
    ref["probability"] = 1.0
    ref["yhat"] = 1
    pred = pd.concat([pred, ref], ignore_index=True)
    fold_rows, pooled_rows = [], []
    for (arm, rep, b), g in pred.groupby(["arm", "repeat", "budget"], sort=False):
        # mean-fold q20 accuracy exactly as historical primary (per fold, then mean)
        qacc = [np.mean(f.yhat[f.q20] == f.truth[f.q20]) for _, f in g.groupby("fold")]
        r = {"arm": arm, "repeat": rep, "budget": b, "q20_accuracy_meanfold": float(np.mean(qacc))}
        # pooled out-of-fold (each of 136 rows predicted once per repeat)
        require_rows = g.row_index.nunique() == 136 and len(g) == 136
        if not require_rows:
            raise RuntimeError(f"pooled OOF not complete {arm} {rep} {b}")
        yh = np.empty(136, int)
        yh[g.row_index.to_numpy()] = g.yhat.to_numpy()
        prob = np.empty(136)
        prob[g.row_index.to_numpy()] = g.probability.to_numpy()
        qmask = np.zeros(136, bool)
        qmask[g.row_index.to_numpy()[g.q20.to_numpy(bool)]] = True
        yq, yhq = yall[qmask], yh[qmask]
        r1 = np.mean(yhq[yq == 1] == 1)
        r0 = np.mean(yhq[yq == 0] == 0)
        r["q20_accuracy_pooled"] = float(np.mean(yq == yhq))
        r["q20_balanced_accuracy_pooled"] = float((r1 + r0) / 2)
        r["q20_rare_recall_pooled"] = float(r0)
        r["full_balanced_accuracy_pooled"] = float((np.mean(yh[yall == 1] == 1) + np.mean(yh[yall == 0] == 0)) / 2)
        r["full_rare_recall_pooled"] = float(np.mean(yh[yall == 0] == 0))
        dec = band_decomposition(yq, yhq, minority=0)
        r.update({f"q20_{k}": v for k, v in dec.items()})
        r["full_minority_calls"] = int((yh == 0).sum())
        for gname, e in graphs.items():
            m = edge_metrics(e, yall, yh)
            for k in ("BER", "BEBA", "BEF1", "n_pred_cut", "spurious_cut"):
                r[f"{gname}_{k}"] = m[k]
            r[f"{gname}_n_true_cut"] = m["n_true_cut"]
        pooled_rows.append(r)
    per = pd.DataFrame(pooled_rows)
    metric_cols = ["q20_accuracy_meanfold", "q20_accuracy_pooled", "q20_balanced_accuracy_pooled",
                   "q20_rare_recall_pooled", "full_balanced_accuracy_pooled", "full_rare_recall_pooled"] + \
        [f"{g}_{k}" for g in graphs for k in ("BER", "BEBA", "BEF1")]
    aul = []
    for (arm, rep), g in per.groupby(["arm", "repeat"]):
        row = {"arm": arm, "repeat": rep}
        for c in metric_cols:
            row[c] = aulc(g.budget, g[c])
        row["q20_minority_calls_B80"] = int(g[g.budget.eq(80)].q20_minority_calls.iloc[0])
        row["q20_wrong_minority_calls_mean_B16_80"] = float(g[g.budget.between(16, 80)].q20_wrong_minority_calls.mean())
        row["q20_correct_minority_calls_mean_B16_80"] = float(g[g.budget.between(16, 80)].q20_correct_minority_calls.mean())
        aul.append(row)
    aul = pd.DataFrame(aul)
    return per, aul, metric_cols, {k: int(len(cut_edges(v, yall))) for k, v in graphs.items()}, {k: int(len(v)) for k, v in graphs.items()}


def paired(aul, metric_cols, contrasts, draws=4000, seed=13):
    rng = np.random.default_rng(seed)
    rows = []
    w = aul.set_index(["arm", "repeat"])
    reps = sorted(aul.repeat.unique())
    for a, b in contrasts:
        for c in metric_cols:
            d = (w.loc[a][c] - w.loc[b][c]).reindex(reps).to_numpy()
            boot = rng.choice(d, size=(draws, len(d)), replace=True).mean(axis=1)
            rows.append({"contrast": f"{a} - {b}", "metric": c, "mean_difference": float(d.mean()),
                         "ci_low": float(np.quantile(boot, .025)), "ci_high": float(np.quantile(boot, .975)),
                         "positive_repeats": int((d > 0).sum()), "n_repeats": len(d)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- A3: OLD Week 8.5 margin vs random decomposition
def old_w85_decomposition():
    ensure_w85_trajectories()
    cm = pd.read_csv(W85_TRAJ,
                     usecols=["arm", "budget", "continuation_id", "repeat", "fold", "run_id", "horizon",
                              "B1_q20_accuracy", "B1_q20_balanced_accuracy", "B1_q20_false_negative",
                              "B1_q20_false_positive", "B1_q20_true_negative", "B1_q20_true_positive",
                              "B1_q20_row_count", "queried_keyhole_count", "queried_non_keyhole_count"])
    cm = cm.sort_values("horizon").drop_duplicates(["arm", "run_id", "continuation_id", "budget"], keep="last")
    cm = cm[cm.budget.between(16, 80)]
    # In OLD the minority (rare) class is Keyhole = positive.  Minority calls = TP + FP.
    cm["minority_calls"] = cm.B1_q20_true_positive + cm.B1_q20_false_positive
    cm["correct_minority_calls"] = cm.B1_q20_true_positive
    cm["wrong_minority_calls"] = cm.B1_q20_false_positive
    cm["labeled_keyhole_share"] = cm.queried_keyhole_count / (cm.queried_keyhole_count + cm.queried_non_keyhole_count)
    cm["majority_share_q20"] = (cm.B1_q20_true_negative + cm.B1_q20_false_positive) / cm.B1_q20_row_count
    cm["always_majority_q20_accuracy"] = cm.majority_share_q20
    out = []
    for (arm, run, cont), g in cm.groupby(["arm", "run_id", "continuation_id"]):
        r = {"arm": arm, "run_id": run, "continuation_id": cont, "repeat": int(g.repeat.iloc[0])}
        for c in ("B1_q20_accuracy", "B1_q20_balanced_accuracy", "always_majority_q20_accuracy"):
            r[c + "_AULC"] = aulc(g.budget, g[c])
        for c in ("minority_calls", "correct_minority_calls", "wrong_minority_calls", "labeled_keyhole_share"):
            r[c + "_mean"] = float(g[c].mean())
        out.append(r)
    out = pd.DataFrame(out)
    # random: average the 30 continuations within run first
    run = out.groupby(["arm", "run_id", "repeat"], as_index=False).mean(numeric_only=True)
    rep = run.groupby(["arm", "repeat"], as_index=False).mean(numeric_only=True)
    return cm, rep


def labeled_prevalence_new():
    q = pd.read_csv(W12 / "active_learning/query_paths.csv.gz")
    q = q.sort_values(["arm", "split_id", "query_order"])
    q["cum_rare"] = (1 - q.revealed_label).groupby([q.arm, q.split_id]).cumsum()
    rows = q[q.query_order.isin([16, 40, 80])].groupby(["arm", "query_order"]).cum_rare.mean().unstack()
    rows.columns = [f"mean_rare_labels_at_B{c}" for c in rows.columns]
    return rows.reset_index()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    old, new = load()
    comp, hub = band_composition(old, new)
    comp.to_csv(OUT / "q20_band_composition_by_split.csv", index=False)
    hub.to_csv(OUT / "nearest_opposite_hubness.csv", index=False)
    summary = {"band_composition": comp.groupby("campaign")[["n_q20", "minority_in_q20", "majority_share_q20",
                                                              "distinct_minority_targets_of_q20_majority"]].mean().to_dict("index"),
               "hubness": hub.to_dict("records")}
    per, aul, metric_cols, n_cut, n_edges = new_al_metrics(new)
    per.to_csv(OUT / "new_al_pooled_metrics_by_budget.csv.gz", index=False)
    aul.to_csv(OUT / "new_al_aulc_by_repeat.csv", index=False)
    summary["new_graph_edges"] = n_edges
    summary["new_true_cut_edges"] = n_cut
    mean = aul.groupby("arm").mean(numeric_only=True).drop(columns="repeat")
    mean.to_csv(OUT / "new_al_mean_aulc_by_arm.csv")
    contrasts = [("Candidate_B__maximin8_continue", "M3_margin__maximin16_continue"),
                 ("Candidate_A__maximin16_continue", "M3_margin__maximin16_continue"),
                 ("Candidate_B__maximin8_continue", "M3_margin__maximin8_continue"),
                 ("M3_random__maximin16_continue", "M3_margin__maximin16_continue"),
                 ("M3_margin__adaptive_physics8", "M3_margin__maximin8_continue"),
                 ("M3_margin__maximin16_continue", "ALWAYS_KEYHOLE_reference"),
                 ("M3_random__maximin16_continue", "ALWAYS_KEYHOLE_reference")]
    pc = paired(aul, metric_cols, contrasts)
    pc.to_csv(OUT / "new_al_paired_contrasts_all_metrics.csv", index=False)
    cm, rep85 = old_w85_decomposition()
    rep85.to_csv(OUT / "old_w85_margin_random_repeat_decomposition.csv", index=False)
    summary["old_w85_arm_means"] = rep85.groupby("arm").mean(numeric_only=True).drop(columns="repeat").to_dict("index")
    lp = labeled_prevalence_new()
    lp.to_csv(OUT / "new_labeled_set_rare_counts.csv", index=False)
    summary["new_labeled_rare_counts"] = lp.to_dict("records")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    pd.set_option("display.width", 250)
    print(json.dumps(summary["band_composition"], indent=1, default=float))
    print(hub.to_string())
    print(n_edges, n_cut)
    print(mean.T.to_string())
    print(pc.to_string())
    print(pd.DataFrame(summary["old_w85_arm_means"]).to_string())
    print(lp.to_string())


if __name__ == "__main__":
    main()
