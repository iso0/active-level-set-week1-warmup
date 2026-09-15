"""Week 9 Phase 1.21 — empirical all-label M3 reference on the replication partitions (descriptive).

M3 fitted on all 324 training labels of each outer run of repeats 61-120, evaluated on the same test
rows and subsets as the learning curves.  It is an observed reference for this model and evaluator,
not a bound; it is used only to state how much observed headroom the acquisition gains leave.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_7_physics_ridge_residual_gp as p17
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_20_acquisition_search as search
from src import week9_phase1_21_simplification_replication as rep


def one(spec, population, arrays, distances) -> list[dict]:
    train = np.asarray(spec.train_indices, dtype=int)
    test = np.asarray(spec.test_indices, dtype=int)
    physics = p11.fit_physics_mean(arrays.logh, arrays.labels, train, p13.seed_u32("shared_physics", spec.run_id, len(train)))
    fit = p13.fit_hybrid(arrays.x4, arrays.logh, arrays.labels, train, train, physics, "M3", search.LENGTH_UPPER)
    probability = p13.components(fit, arrays.x4[test], arrays.logh[test])["probability"]
    flags = p17.subset_flags(spec, population, distances)
    return [{"run_id": spec.run_id, "repeat": spec.repeat, "subset": s, "train_labels": len(train),
             **p17.metric_values(arrays.labels[test][flags[s]], probability[flags[s]])} for s in search.SUBSETS]


def main() -> None:
    population, specs = rep.load_all_specs()
    arrays = search.build_arrays(population)
    distances = w85.b1_distance(population)
    chosen = [s for s in specs if s.repeat in set(rep.REPLICATION_REPEATS)]
    rows = Parallel(n_jobs=8)(delayed(one)(s, population, arrays, distances) for s in chosen)
    frame = pd.DataFrame([r for rs in rows for r in rs])
    frame.to_csv(rep.OUTPUT / "all_label_reference_per_run.csv", index=False)
    summary = {s: {"accuracy": float(g.accuracy.mean()), "balanced_accuracy": float(g.balanced_accuracy.mean()),
                   "keyhole_recall": float(g.keyhole_recall.mean()), "false_positive": float(g.false_positive.mean()),
                   "false_negative": float(g.false_negative.mean())}
               for s, g in frame.groupby("subset")}
    payload = {"what": "empirical all-label M3 reference (M3 fitted on all training labels of each outer run)",
               "repeats": [min(rep.REPLICATION_REPEATS), max(rep.REPLICATION_REPEATS)], "runs": int(frame.run_id.nunique()),
               "train_labels_per_run": sorted(frame.train_labels.unique().tolist()), "by_subset": summary,
               "not": "not a theoretical ceiling or a maximum possible accuracy"}
    (rep.OUTPUT / "all_label_reference.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
