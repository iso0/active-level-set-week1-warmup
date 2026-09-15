"""Real-data active level-set benchmark under the Week 8.5 frozen protocol.

Runs one or more acquisition arms on the frozen 405-simulation population using
the 100 frozen outer splits and 16-point initial designs, evaluates B1-q20/q30
accuracy on the untouched test fold at every budget, and reports AULC 16-80.

    python experiments/real_benchmark.py --smoke
    python experiments/real_benchmark.py --arms binary_margin binary_random --runs 20 --workers 4
"""

from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.preprocessing import StandardScaler

import alse
from alse import protocol
from alse.acquisition import choose_binary_candidate
from alse.config import output_dir
from alse.data import SPH_V2_REVISION, load_population
from alse.io import seed_u32, write_csv, write_json
from alse.metrics import aulc, b1_distance, boundary_flags, compute_metrics
from alse.surrogates import fit_gpc, predict_gpc

ARMS = protocol.ARMS


def run_arm(spec: protocol.SplitSpec, arm: str, population: pd.DataFrame, distances: np.ndarray, budget: int) -> list[dict]:
    x = population.loc[:, list(protocol.FEATURES)].to_numpy(float)
    labels = population["has_keyhole"].astype(int).to_numpy()
    train = np.asarray(spec.train_indices)
    test = np.asarray(spec.test_indices)
    scaler = StandardScaler().fit(x[train])  # frozen: week8_5::run_trajectory
    x_scaled = scaler.transform(x)
    flags = boundary_flags(spec.test_indices, population, distances)
    initial = protocol.initial_design(spec, population)
    order = protocol.random_continuation_order(spec, initial, 1) if arm == "binary_random" else []

    def fit_fn(xr, yr, key):
        return fit_gpc(xr, yr, seed_u32(key), scaler=scaler)

    def choose_fn(model, xc, candidates, revealed):
        if arm == "binary_random":
            return next(i for i in order if i not in set(revealed))
        p = predict_gpc(model, xc)
        return choose_binary_candidate(arm, candidates, p, x_scaled, revealed)[0]

    def evaluate_fn(model, test_idx, b):
        p = predict_gpc(model, x[test_idx])
        row = {"run_id": spec.run_id, "arm": arm}
        for name, flag in {"full": np.ones(len(test_idx), bool), **flags}.items():
            for metric, value in compute_metrics(labels[test_idx], p, flag).items():
                row[f"{name}_{metric}"] = value
        return row

    _, rows = protocol.sequential_runner(
        spec, population, initial, budget, fit_fn, choose_fn, evaluate_fn,
        seed_key_fn=lambda b: protocol.fit_seed_key(spec, arm, 1, b),
    )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--arms", nargs="+", default=["binary_margin", "binary_random"], choices=ARMS)
    parser.add_argument("--runs", type=int, default=100, help="use the first N of the 100 frozen outer runs")
    parser.add_argument("--budget", type=int, default=80)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--smoke", action="store_true", help="2 runs, budget 24")
    parser.add_argument("--name", default="real_benchmark")
    args = parser.parse_args()
    if args.smoke:
        args.runs, args.budget = 2, 24

    population = load_population()
    distances = b1_distance(population)
    specs = protocol.build_splits(population)[: args.runs]
    started = time.time()
    jobs = [(spec, arm) for spec in specs for arm in args.arms]
    results = Parallel(n_jobs=args.workers)(delayed(run_arm)(s, a, population, distances, args.budget) for s, a in jobs)
    frame = pd.DataFrame([row for rows in results for row in rows])

    end = min(args.budget, 80)
    summary = {}
    for arm, group in frame.groupby("arm"):
        per_run = [aulc(g.budget.to_numpy(), g.B1_q20_accuracy.to_numpy(), 16, end) for _, g in group.groupby("run_id")]
        summary[arm] = {"mean_B1_q20_accuracy_AULC": float(np.mean(per_run)), "runs": len(per_run)}

    out = output_dir(args.name)
    write_csv(out / "trajectories.csv", frame)
    write_json(out / "summary.json", {
        "alse_version": alse.__version__, "protocol": protocol.PROTOCOL_ID, "data_revision": SPH_V2_REVISION,
        "settings": vars(args), "aulc_range": [16, end], "arms": summary, "runtime_seconds": time.time() - started,
    })
    print(pd.DataFrame(summary).T.to_string())
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
