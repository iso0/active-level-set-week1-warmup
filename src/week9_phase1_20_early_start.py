"""Week 9 Phase 1.20 — earlier active start (acquisition-strategy variant).

Every earlier phase spends the first 16 labels on the frozen seeded maximin design and only then
acquires actively.  The greedy maximin sequence places its first points in the corners of the
standardised (P, VX, LS, ST) box, far from the regime boundary, and far labels are known to pull
M3's global fit (NESTED_SUBSET_LABEL_HARM_AUDIT).  This variant keeps everything else identical and
changes only WHEN the active phase starts:

    seed   the first k points of the SAME frozen maximin order, extended along that order (never by
           looking at hidden labels) only until the queried labels contain both classes, as M3's
           Stage-1 logistic requires
    active from that point on, the named inner policy of week9_phase1_20_acquisition_search
    budget identical label accounting: at budget b exactly b simulations have been queried; metrics
           are recorded from b = 16 so AULC 16-80 is computed on exactly the same grid as margin

Paired comparison: the margin control spends its first 16 labels on the frozen design; both arms
share the first k maximin points.  Checkpoints go to the Phase 1.20 checkpoint tree under the policy
name 'early{k}__{inner}', so the Phase 1.20 summary and confirmation code read them unchanged.
"""
from __future__ import annotations

import argparse
import gzip
import json
import time
from typing import Any, Sequence

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.preprocessing import StandardScaler

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_7_physics_ridge_residual_gp as p17
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_20_acquisition_search as search


def parse(policy: str) -> tuple[int, str]:
    head, inner = policy.split("__", 1)
    search.require(head.startswith("early") and inner in search.POLICIES, f"bad early-start policy {policy}")
    return int(head[len("early"):]), inner


def seed_prefix(frozen16: Sequence[int], labels: np.ndarray, k: int) -> list[int]:
    queried = list(map(int, frozen16[:k]))
    position = k
    while len(np.unique(labels[queried])) < 2:
        search.require(position < 16, "frozen design lacks both classes")
        queried.append(int(frozen16[position]))
        position += 1
    return queried


def run_spec(policy: str, spec: Any, frozen16: Sequence[int], population: pd.DataFrame,
             arrays: search.Arrays, distances: np.ndarray) -> dict[str, Any]:
    destination = search.checkpoint_path(policy, spec.run_id)
    if destination.is_file():
        payload = json.loads(gzip.decompress(destination.read_bytes()).decode())
        if payload.get("complete") and payload.get("policy") == policy:
            return {"run_id": spec.run_id, "reused": True}
    k, inner = parse(policy)
    select = search.POLICIES[inner]
    train = np.asarray(spec.train_indices, dtype=int)
    test = np.asarray(spec.test_indices, dtype=int)
    flags = p17.subset_flags(spec, population, distances)
    x_scaled = StandardScaler().fit(arrays.x4[train]).transform(arrays.x4)
    z_scaled = StandardScaler().fit(arrays.orth[train]).transform(arrays.orth)
    n = len(population)
    queried = seed_prefix(frozen16, arrays.labels, k)
    seed_size = len(queried)
    metrics: list[dict[str, Any]] = []
    cache: dict = {}
    for budget in range(seed_size, 81):
        search.require(len(queried) == budget and len(set(queried)) == budget, "prefix drift")
        revealed = np.asarray(queried, dtype=int)
        physics = p11.fit_physics_mean(arrays.logh, arrays.labels, revealed,
                                       p13.seed_u32("shared_physics", spec.run_id, budget))
        fit = p13.fit_hybrid(arrays.x4, arrays.logh, arrays.labels, revealed, train, physics, "M3",
                             search.LENGTH_UPPER)
        if budget >= 16:
            probability = p13.components(fit, arrays.x4[test], arrays.logh[test])["probability"]
            for subset in search.SUBSETS:
                flag = flags[subset]
                metrics.append({"policy": policy, "run_id": spec.run_id, "repeat": spec.repeat,
                                "fold": spec.fold, "budget": budget, "subset": subset,
                                **p17.metric_values(arrays.labels[test][flag], probability[flag])})
        if budget == 80:
            break
        candidates = np.setdiff1d(train, revealed, assume_unique=False)
        comp = p13.components(fit, arrays.x4[candidates], arrays.logh[candidates])
        seen_label = np.full(n, -1, dtype=int)
        seen_label[revealed] = arrays.labels[revealed]
        seen_depth = np.full(n, np.nan)
        seen_depth[revealed] = arrays.logdepth[revealed]
        state = search.State(run_id=spec.run_id, budget=budget, revealed=revealed, candidates=candidates,
                             seen_label=seen_label, seen_logdepth=seen_depth, x_scaled=x_scaled,
                             z_scaled=z_scaled, logh=arrays.logh, p_cand=comp["probability"],
                             mean_cand=comp["final_latent"], var_cand=comp["latent_variance"], fit=fit,
                             rng=np.random.default_rng(p13.seed_u32("random", spec.run_id, budget)),
                             x4=arrays.x4, train=train, cache=cache, leaky_rank=None)
        chosen = select(state)
        search.require(chosen in set(candidates.tolist()), f"invalid acquisition by {policy}")
        queried.append(chosen)
    search.require(len(queried) == 80, "trajectory completeness")
    destination.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps({"complete": True, "policy": policy, "run_id": spec.run_id, "seed_size": seed_size,
                       "queried_indices": queried, "metrics": metrics}, default=float).encode()
    destination.write_bytes(gzip.compress(blob, compresslevel=6, mtime=0))
    return {"run_id": spec.run_id, "reused": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policies", nargs="+", required=True)
    parser.add_argument("--repeats", choices=("dev", "conf", "ext", "confirmation"), default="dev")
    parser.add_argument("--workers", type=int, default=7)
    args = parser.parse_args()
    repeats = {"dev": search.DEV_REPEATS, "conf": search.CONF_REPEATS, "ext": search.EXT_REPEATS,
               "confirmation": search.CONFIRMATION}[args.repeats]
    population, specs, paths = search.load_inputs()
    arrays = search.build_arrays(population)
    distances = w85.b1_distance(population)
    chosen = [s for s in specs if s.repeat in set(repeats)]
    for policy in args.policies:
        parse(policy)
        started = time.time()
        results = Parallel(n_jobs=args.workers)(
            delayed(run_spec)(policy, spec, paths[spec.run_id][:16], population, arrays, distances)
            for spec in chosen)
        print(f"  {policy:<26} runs={len(results)} reused={sum(r['reused'] for r in results)} "
              f"{time.time() - started:7.1f}s", flush=True)


if __name__ == "__main__":
    main()
