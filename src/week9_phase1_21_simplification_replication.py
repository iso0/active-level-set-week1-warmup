"""Week 9 Phase 1.21 — simplification of CCM and clean replication on untouched partitions.

Question: in Phase 1.20 only the EARLY coverage phase of CCM replicated.  Does
"coverage until B40, then plain M3 margin" do as well as CCM, and does it replicate, with and
without the earlier active start?

Nothing here is searched or tuned.  Every policy is an object imported from Phase 1.20:

    margin                              control; frozen 16-point seed
    coverage_then_margin_B40            Candidate A: search.make_band_coverage("x", weight_unc=1.0,
                                        pad_fraction=0.25, switch_budget=40) - CCM's early rule,
                                        plain margin from B40 (in Phase 1.20 screened as sched_bmm_B40)
    early8__coverage_then_margin_B40    Candidate B: first 8 frozen maximin points (extended along the
                                        frozen order only until both classes are queried), then A
    cov_then_misfit_B40                 descriptive reference (Phase 1.20 family-A finalist, CCM)
    early8__cov_then_misfit_B40         descriptive reference (Phase 1.20 family-B finalist)

The trajectory loop is Phase 1.20's (week9_phase1_20_early_start.run_spec); a gate proves the
Phase 1.21 runner reproduces Phase 1.20 checkpoints bit-identically before any replication run.
Beyond Phase 1.20 it records, for post-hoc mechanism analysis only, which row plain margin would
have chosen in the same state and whether the chosen row lay inside the label-estimated band.

Replication partitions are UNTOUCHED INTERNAL REPLICATION PARTITIONS: further outer cross-validation
repeats of the same 405-simulation population from the frozen generator w85.build_splits.  They are
not new simulations and not external data.
"""
from __future__ import annotations

import argparse
import gzip
import json
import time
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.preprocessing import StandardScaler

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_7_physics_ridge_residual_gp as p17
from src import week9_phase1_8_model_path_decomposition as p18
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_20_acquisition_search as search
from src import week9_phase1_20_early_start as early

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase1_21_simplification_replication"
CHECKPOINTS = OUTPUT / "checkpoints"
GATE_CHECKPOINTS = OUTPUT / "gate_checkpoints"
PHASE120 = ROOT / "outputs" / "week9_phase1_20_acquisition_search" / "checkpoints"

REPLICATION_REPEATS = tuple(range(61, 121))      # frozen in PHASE1_21_PREREGISTERED_PROTOCOL.json
GENERATOR_REPEATS = max(REPLICATION_REPEATS)
SWITCH_BUDGET = 40
PAD_FRACTION = 0.25
UNCERTAINTY_WEIGHT = 1.0
COORDINATES = "x"

CANDIDATE_A = "coverage_then_margin_B40"
CANDIDATE_B = "early8__coverage_then_margin_B40"
CONTROL = "margin"
REFERENCES = ("cov_then_misfit_B40", "early8__cov_then_misfit_B40")


def coverage_then_margin() -> Callable[[search.State], int]:
    return search.make_band_coverage(COORDINATES, weight_unc=UNCERTAINTY_WEIGHT,
                                     pad_fraction=PAD_FRACTION, switch_budget=SWITCH_BUDGET)


# name -> (seed size k, inner policy); k = 16 is the frozen seed (early_start gate: early16 == margin)
POLICIES: dict[str, tuple[int, Callable[[search.State], int]]] = {
    CONTROL: (16, search.pol_margin),
    CANDIDATE_A: (16, coverage_then_margin()),
    CANDIDATE_B: (8, coverage_then_margin()),
    "cov_then_misfit_B40": (16, search.make_coverage_then_misfit(40)),
    "early8__cov_then_misfit_B40": (8, search.make_coverage_then_misfit(40)),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


# ---------------------------------------------------------------- splits


def load_all_specs() -> tuple[pd.DataFrame, list[Any]]:
    """Frozen generator extended to GENERATOR_REPEATS, gated against every historical use."""
    population, frozen = p18.load_population_specs()
    extended = w85.build_splits(population, repeats=GENERATOR_REPEATS, folds=5)
    for old, new in zip(frozen, extended[:100]):
        require(old.run_id == new.run_id and old.train_indices == new.train_indices
                and old.test_indices == new.test_indices, f"frozen split drift {old.run_id}")
    _, phase120_specs, _ = search.load_inputs()                  # repeats 1-60 as used in Phase 1.20
    for old, new in zip(phase120_specs, extended[:300]):
        require(old.run_id == new.run_id and old.train_indices == new.train_indices
                and old.test_indices == new.test_indices, f"Phase 1.20 split drift {old.run_id}")
    return population, extended


# ---------------------------------------------------------------- one trajectory


def run_spec(policy: str, spec: Any, population: pd.DataFrame, arrays: search.Arrays,
             distances: np.ndarray, root: Path) -> dict[str, Any]:
    destination = root / policy / f"{spec.run_id}.json.gz"
    if destination.is_file():
        payload = json.loads(gzip.decompress(destination.read_bytes()).decode())
        if payload.get("complete") and payload.get("policy") == policy:
            return {"run_id": spec.run_id, "reused": True}
    k, select = POLICIES[policy]
    frozen16 = w85.initial_design(spec, population)
    train = np.asarray(spec.train_indices, dtype=int)
    test = np.asarray(spec.test_indices, dtype=int)
    flags = p17.subset_flags(spec, population, distances)
    x_scaled = StandardScaler().fit(arrays.x4[train]).transform(arrays.x4)
    z_scaled = StandardScaler().fit(arrays.orth[train]).transform(arrays.orth)
    n = len(population)
    queried = early.seed_prefix(frozen16, arrays.labels, k)
    seed_size = len(queried)
    metrics: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    cache: dict = {}
    for budget in range(seed_size, 81):
        require(len(queried) == budget and len(set(queried)) == budget, "prefix drift")
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
        require(chosen in set(candidates.tolist()), f"invalid acquisition by {policy}")
        # post-hoc mechanism record: label-blind quantities of the SAME state, never fed back
        band = search.estimated_band(state, PAD_FRACTION)
        margin_choice = search.pol_margin(state)
        rev_lab = seen_label[revealed]
        lowest_k, highest_c = arrays.logh[revealed][rev_lab == 1].min(), arrays.logh[revealed][rev_lab == 0].max()
        steps.append({"budget": budget, "chosen": int(chosen), "margin_choice": int(margin_choice),
                      "chosen_in_band": bool(band[np.flatnonzero(candidates == chosen)[0]]),
                      "band_candidates": int(band.sum()), "band_lo": float(min(lowest_k, highest_c)),
                      "band_hi": float(max(lowest_k, highest_c)), "separable": bool(highest_c < lowest_k),
                      "chosen_logh": float(arrays.logh[chosen])})
        queried.append(chosen)
    require(len(queried) == 80, "trajectory completeness")
    destination.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps({"complete": True, "policy": policy, "run_id": spec.run_id, "seed_size": seed_size,
                       "queried_indices": queried, "metrics": metrics, "steps": steps}, default=float).encode()
    destination.write_bytes(gzip.compress(blob, compresslevel=6, mtime=0))
    return {"run_id": spec.run_id, "reused": False}


def run(policies: Sequence[str], repeats: Sequence[int], workers: int, root: Path) -> None:
    population, specs = load_all_specs()
    arrays = search.build_arrays(population)
    distances = w85.b1_distance(population)
    chosen = [s for s in specs if s.repeat in set(repeats)]
    for policy in policies:
        require(policy in POLICIES, f"unknown policy {policy}")
        started = time.time()
        results = Parallel(n_jobs=workers)(
            delayed(run_spec)(policy, spec, population, arrays, distances, root) for spec in chosen)
        print(f"  {policy:<34} runs={len(results)} reused={sum(r['reused'] for r in results)} "
              f"{time.time() - started:7.1f}s", flush=True)


# ---------------------------------------------------------------- equivalence gate


GATE_CASES = (
    # (Phase 1.21 policy, Phase 1.20 checkpoint folder, run ids)
    (CONTROL, "margin", ("w85__r01_f01", "w85__r05_f03", "w85__r09_f05")),
    (CANDIDATE_A, "sched_bmm_B40", ("w85__r01_f01", "w85__r05_f03", "w85__r09_f05")),
    ("cov_then_misfit_B40", "cov_then_misfit_B40", ("w85__r02_f02", "w85__r07_f04")),
    ("early8__cov_then_misfit_B40", "early8__cov_then_misfit_B40", ("w85__r03_f01", "w85__r08_f02")),
    (CANDIDATE_B, "early8__sched_bmm_B40", ("w85__r01_f01",)),
)


def equivalence_gate(workers: int = 7) -> dict[str, Any]:
    population, specs = load_all_specs()
    arrays = search.build_arrays(population)
    distances = w85.b1_distance(population)
    by_id = {s.run_id: s for s in specs}
    jobs = [(policy, by_id[r]) for policy, _, runs in GATE_CASES for r in runs]
    Parallel(n_jobs=workers)(delayed(run_spec)(policy, spec, population, arrays, distances, GATE_CHECKPOINTS)
                             for policy, spec in jobs)
    rows = []
    for policy, folder, runs in GATE_CASES:
        for run_id in runs:
            new = json.loads(gzip.decompress((GATE_CHECKPOINTS / policy / f"{run_id}.json.gz").read_bytes()))
            old = json.loads(gzip.decompress((PHASE120 / folder / f"{run_id}.json.gz").read_bytes()))
            strip = lambda ms: [{k: v for k, v in m.items() if k != "policy"} for m in ms]
            rows.append({"phase1_21_policy": policy, "phase1_20_checkpoint": folder, "run_id": run_id,
                         "queried_identical": new["queried_indices"] == old["queried_indices"],
                         "metrics_identical": strip(new["metrics"]) == strip(old["metrics"])})
    passed = all(r["queried_identical"] and r["metrics_identical"] for r in rows)
    payload = {"status": "PASS" if passed else "FAIL", "cases": rows,
               "meaning": "the Phase 1.21 runner and policy objects reproduce Phase 1.20 trajectories and "
                          "every recorded metric bit-identically on development runs"}
    (OUTPUT / "gate_runner_equivalence.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    require(passed, "runner equivalence gate failed")
    return payload


def split_gate() -> dict[str, Any]:
    population, specs = load_all_specs()                     # raises on any drift
    new = [s for s in specs if s.repeat in set(REPLICATION_REPEATS)]
    invalid = []
    for spec in new:
        try:
            w85.initial_design(spec, population)
        except AssertionError as exc:
            invalid.append({"run_id": spec.run_id, "reason": str(exc)})
    payload = {"status": "PASS" if not invalid else "FAIL",
               "frozen_100_runs_bit_identical": True, "phase1_20_repeats_1_60_bit_identical": True,
               "generator": "w85.build_splits(population, repeats=%d, folds=5)" % GENERATOR_REPEATS,
               "replication_repeats": [min(REPLICATION_REPEATS), max(REPLICATION_REPEATS)],
               "replication_runs": len(new), "runs_whose_frozen_seed_lacks_both_classes": invalid,
               "note": "the seed-validity check reads only the labels of the 16 frozen seed points, which every "
                       "policy queries anyway; no model is fitted and no held-out label is read"}
    (OUTPUT / "gate_splits.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    require(not invalid, f"invalid frozen seeds: {invalid}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", action="store_true")
    parser.add_argument("--policies", nargs="+")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.gate:
        print(json.dumps(split_gate(), indent=2))
        print(json.dumps(equivalence_gate(args.workers), indent=2))
        return
    protocol = OUTPUT / "PHASE1_21_PREREGISTERED_PROTOCOL.json"
    require(protocol.is_file(), "refusing to run replication before the protocol is frozen")
    run(args.policies, REPLICATION_REPEATS, args.workers, CHECKPOINTS)


if __name__ == "__main__":
    main()
