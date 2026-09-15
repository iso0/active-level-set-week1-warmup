"""Real-data protocols.

Two protocols coexist in the thesis and both are frozen:

* Phase 6/7 (exploratory): 4 repeats x StratifiedGroupKFold(5) = 20 outer runs,
  sequential warm start of 12-16 points, budget 80.
* Week 8.5 (confirmatory, protocol ``week8_5_frozen_confirmation_protocol/v1.0.0``):
  20 repeats x 5 grouped folds = 100 runs, 16-point seeded maximin design,
  declared budgets to horizon 160.

Plus loaders for the frozen Week 9 query paths (A0 = binary_margin, P1 = M3
margin) and a generic sequential runner replacing the archive's six copies of
``run_one_spec`` / ``run_trajectory``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

import numpy as np
import pandas as pd
from scipy.spatial import distance
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler

from alse.config import archive_file
from alse.data import FEATURE_COLUMNS
from alse.io import require, seed_key, seed_u32, stable_rng, stable_seed

FEATURES = tuple(FEATURE_COLUMNS)  # ("P", "VX", "LS", "ST")

# --- Phase 6/7 exploratory protocol -----------------------------------------
# frozen: week7_phase6_real_data_boundary_active_level_set.py constants
BASE_SEED = 6022026
N_SPLITS = 5
N_REPEATS = 4
N_OUTER_RUNS = N_SPLITS * N_REPEATS
NOMINAL_WARM_START = 12
MAX_WARM_START = 80
FINAL_BUDGET = 80
PRESENTATION_CHECKPOINTS = (12, 15, 20, 25, 30, 40, 50, 60, 70, 80)
PRIMARY_POPULATION = "primary_common"

# --- Week 8.5 frozen protocol -----------------------------------------------
# frozen: week8_5_frozen_sample_efficiency_confirmation.py constants
PROTOCOL_ID = "week8_5_frozen_confirmation_protocol/v1.0.0"
FROZEN_SEED_ROOT = "week8_5_frozen_confirmation|v1"
ARMS = ("binary_margin", "binary_random", "binary_uncertainty_repulsion")
TARGETS = (0.75, 0.80, 0.85)
INITIAL_DESIGN_SIZE = 16
RANDOM_CONTINUATIONS = 30
REPULSION_BANDWIDTH_TAG = "0.15"

# Seed namespaces of the archived studies (verbatim; part of every stored seed).
SEED_ROOTS = {
    "week8_5": FROZEN_SEED_ROOT,
    "phase1_5": "week9_phase1_5_h_physics_confirmation|v1",
    "phase1_7": "week9_phase1_7_physics_ridge_residual_gp|v1",
    "phase1_8": "week9_phase1_8_model_path_decomposition|v1",
    "phase1_9": "week9_phase1_9_physics_specificity_control|v1",
    "phase1_11": "week9_phase1_11_fixed_mean_discrepancy_gp|v1",
    "phase1_12": "week9_phase1_12_gpc_kernel_adequacy|v1",
    "phase1_13": "week9_phase1_13_fixed_physics_ard_discrepancy|v1",
    "phase1_14": "week9_phase1_14_m3_margin_acquisition|v1",
    "phase1_15a": "week9_phase1_15a_physics_residual_signal_audit|v1",
    "phase1_16": "week9_phase1_16_m3_repulsion_scale_audit|v1",
    "phase1_17a": "week9_phase1_17a_physics_contour_geometry_audit|v1",
    "phase1_18a": "week9_phase1_18a|frozen-prefix|v1",
    "phase1_18b0": "week9_phase1_18b0|validation-gate|v1",
    "phase1_18b": "week9_phase1_18b_prospective_global_gpc_sur_benchmark|v1",
}


@dataclass(frozen=True)
class RunSpec:
    """One Phase 6/7 outer run. frozen: week7_phase6::RunSpec"""

    benchmark_population: str
    run_id: str
    repeat: int
    fold: int
    train_indices: tuple[int, ...]
    test_indices: tuple[int, ...]
    run_seed: int


@dataclass(frozen=True)
class SplitSpec:
    """One Week 8.5 outer run. frozen: week8_5::SplitSpec"""

    run_id: str
    repeat: int
    fold: int
    train_indices: tuple[int, ...]
    test_indices: tuple[int, ...]


def _labels_and_groups(population: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    labels = population["has_keyhole"].astype(int).to_numpy()
    groups = population["input_tuple_sha256"].astype(str).to_numpy()
    return labels, groups


def build_outer_splits(population: pd.DataFrame, benchmark_population: str = PRIMARY_POPULATION) -> list[RunSpec]:
    """4 x StratifiedGroupKFold(5, shuffle) grouped by input tuple.

    frozen: week7_phase6::build_outer_splits (manifest/balance tables dropped)
    """
    labels, groups = _labels_and_groups(population)
    dummy = np.zeros((len(population), 1))
    specs: list[RunSpec] = []
    for repeat in range(N_REPEATS):
        splitter = StratifiedGroupKFold(
            n_splits=N_SPLITS, shuffle=True, random_state=stable_seed(BASE_SEED, benchmark_population, repeat)
        )
        for fold, (train, test) in enumerate(splitter.split(dummy, labels, groups), start=1):
            run_id = f"{benchmark_population}__r{repeat + 1:02d}_f{fold:02d}"
            require(set(groups[train]).isdisjoint(groups[test]), f"{run_id}: duplicate input group leakage")
            specs.append(
                RunSpec(
                    benchmark_population=benchmark_population,
                    run_id=run_id,
                    repeat=repeat + 1,
                    fold=fold,
                    train_indices=tuple(map(int, train)),
                    test_indices=tuple(map(int, test)),
                    run_seed=stable_seed(BASE_SEED, run_id),
                )
            )
    require(len(specs) == N_OUTER_RUNS, f"Expected {N_OUTER_RUNS} runs")
    return specs


def warm_start_indices(spec: RunSpec, population: pd.DataFrame, final_budget: int = FINAL_BUDGET) -> tuple[list[int], np.ndarray]:
    """Shared random permutation revealed until both classes are seen (>= 12).

    frozen: week7_phase6::warm_start_indices
    """
    pool = np.asarray(spec.train_indices, dtype=int)
    rng = stable_rng(BASE_SEED, spec.run_id, "shared_pool_permutation")
    permutation = pool[rng.permutation(len(pool))]
    labels = population["has_keyhole"].astype(int).to_numpy()
    effective_limit = min(MAX_WARM_START, final_budget, len(permutation))
    queried: list[int] = []
    for idx in permutation[:effective_limit]:
        queried.append(int(idx))
        if len(queried) >= NOMINAL_WARM_START and len(np.unique(labels[queried])) == 2:
            break
    require(len(np.unique(labels[queried])) == 2, f"{spec.run_id}: warm start did not reveal both classes")
    return queried, permutation


# --- Week 8.5 -----------------------------------------------------------------


def frozen_key(*parts: object) -> str:
    """Seed key under the Week 8.5 namespace. frozen: week8_5::seed_key"""
    return seed_key(FROZEN_SEED_ROOT, *parts)


def declared_budgets(horizon: int) -> list[int]:
    """16..80 step 1, 82..120 step 2, 124..160 step 4. frozen: week8_5::declared_budgets"""
    if 16 <= horizon < 80:  # smoke fixtures only
        return list(range(16, horizon + 1))
    require(horizon in (80, 120, 160), "Confirmation horizon must be 80, 120, or 160")
    budgets = list(range(16, 81))
    if horizon >= 120:
        budgets.extend(range(82, 121, 2))
    if horizon >= 160:
        budgets.extend(range(124, 161, 4))
    return budgets


def build_splits(population: pd.DataFrame, repeats: int = 20, folds: int = 5) -> list[SplitSpec]:
    """20 x StratifiedGroupKFold(5, shuffle) seeded per repeat. frozen: week8_5::build_splits"""
    labels, groups = _labels_and_groups(population)
    dummy = np.zeros((len(population), 1))
    specs: list[SplitSpec] = []
    for repeat in range(1, repeats + 1):
        seed = seed_u32(frozen_key("outer_split", "repeat", f"{repeat:02d}"))
        splitter = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed)
        for fold, (train, test) in enumerate(splitter.split(dummy, labels, groups), start=1):
            specs.append(
                SplitSpec(
                    run_id=f"w85__r{repeat:02d}_f{fold:02d}",
                    repeat=repeat,
                    fold=fold,
                    train_indices=tuple(int(v) for v in train),
                    test_indices=tuple(int(v) for v in test),
                )
            )
    return specs


def initial_design(spec: SplitSpec, population: pd.DataFrame, size: int = INITIAL_DESIGN_SIZE) -> list[int]:
    """Seeded feature-only greedy maximin design; labels never influence selection.

    frozen: week8_5::initial_design (first point uniform; ties -> smallest population index)
    """
    train = np.asarray(spec.train_indices, dtype=int)
    x = population.loc[:, list(FEATURES)].to_numpy(float)
    scaled = StandardScaler().fit_transform(x[train])
    rng = np.random.default_rng(seed_u32(frozen_key("run", spec.run_id, "initial_design")))
    chosen_local = [int(rng.integers(len(train)))]
    while len(chosen_local) < size:
        remaining = np.setdiff1d(np.arange(len(train)), np.asarray(chosen_local), assume_unique=True)
        nearest = distance.cdist(scaled[remaining], scaled[chosen_local]).min(axis=1)
        best = float(nearest.max())
        ties = remaining[np.isclose(nearest, best, rtol=1e-12, atol=1e-14)]
        chosen_local.append(int(ties[np.argmin(train[ties])]))
    chosen = train[np.asarray(chosen_local, dtype=int)].astype(int).tolist()
    labels = population["has_keyhole"].astype(int).to_numpy()[chosen]
    require(len(np.unique(labels)) == 2, f"{spec.run_id}: initial design lacks both classes")
    return chosen


def fit_seed_key(spec: SplitSpec, arm: str, continuation: int, budget: int) -> str:
    """frozen: week8_5::fit_seed_key"""
    if arm == "binary_random":
        return frozen_key("run", spec.run_id, "arm", arm, "continuation", f"{continuation:02d}", "fit", "budget", f"{budget:03d}")
    if arm == "binary_uncertainty_repulsion":
        return frozen_key("run", spec.run_id, "arm", arm, "h", REPULSION_BANDWIDTH_TAG, "fit", "budget", f"{budget:03d}")
    return frozen_key("run", spec.run_id, "arm", arm, "fit", "budget", f"{budget:03d}")


def random_order_key(spec: SplitSpec, continuation: int) -> str:
    """frozen: week8_5::random_order_key"""
    return frozen_key("run", spec.run_id, "arm", "binary_random", "continuation", f"{continuation:02d}", "order")


def random_continuation_order(spec: SplitSpec, initial: Sequence[int], continuation: int) -> list[int]:
    """Predeclared permutation of the training pool minus the initial design."""
    remaining = np.array([i for i in spec.train_indices if i not in set(initial)], dtype=int)
    rng = np.random.default_rng(seed_u32(random_order_key(spec, continuation)))
    return remaining[rng.permutation(len(remaining))].astype(int).tolist()


# --- frozen query paths (archive artifacts) ------------------------------------


def _paths_from_csv(relpath: str, **filters: str) -> dict[str, list[int]]:
    frame = pd.read_csv(archive_file(relpath))
    for column, value in filters.items():
        frame = frame[frame[column] == value]
    frame = frame.sort_values(["run_id", "query_order"], kind="stable")
    return {run: group["population_row_index"].astype(int).tolist() for run, group in frame.groupby("run_id", sort=True)}


def load_a0_paths() -> dict[str, list[int]]:
    """Frozen binary_margin paths (80 queries per run), the A0 replay path of Phases 1.8-1.13."""
    return _paths_from_csv("outputs/week9_phase1_8_model_path_decomposition/tables/query_paths.csv.gz", path="A0")


def load_p1_paths() -> dict[str, list[int]]:
    """Phase 1.14 M3-margin paths (80 queries per run), the P1 baseline of Phases 1.15A-1.18B."""
    return _paths_from_csv("outputs/week9_phase1_14_m3_margin_acquisition/m3_margin_paths.csv.gz")


# --- generic sequential loop -----------------------------------------------------


def sequential_runner(
    spec: SplitSpec | RunSpec,
    population: pd.DataFrame,
    initial: Sequence[int],
    budget: int,
    fit_fn: Callable[[np.ndarray, np.ndarray, str], Any],
    choose_fn: Callable[[Any, np.ndarray, np.ndarray, list[int]], int],
    evaluate_fn: Callable[[Any, np.ndarray, int], dict[str, Any]] | None = None,
    *,
    seed_key_fn: Callable[[int], str] | None = None,
    evaluate_budgets: Sequence[int] | None = None,
) -> tuple[list[int], list[dict[str, Any]]]:
    """Reveal one label per step from the training pool only.

    ``fit_fn(x_revealed, y_revealed, seed_key)`` returns a fitted model;
    ``choose_fn(model, x_candidates, candidate_indices, revealed)`` returns the
    population row index to query next; ``evaluate_fn(model, test_indices, budget)``
    returns a metrics row. Information flow matches the archive: candidates come
    from the training pool minus revealed rows, test rows are never seen.
    frozen: mirrors week8_5::run_trajectory / week9_phase1_14::run_one_spec
    """
    x = population.loc[:, list(FEATURES)].to_numpy(float)
    y = population["has_keyhole"].astype(int).to_numpy()
    train = np.asarray(spec.train_indices, dtype=int)
    test = np.asarray(spec.test_indices, dtype=int)
    revealed = [int(i) for i in initial]
    require(set(revealed).issubset(set(train.tolist())), "initial design must lie in the training pool")
    budgets = set(evaluate_budgets or [])
    rows: list[dict[str, Any]] = []
    model = None
    for step in range(len(revealed), budget + 1):
        key = seed_key_fn(step) if seed_key_fn else f"budget|{step:03d}"
        model = fit_fn(x[revealed], y[revealed], key)
        if evaluate_fn is not None and (not budgets or step in budgets):
            rows.append({"budget": step, **evaluate_fn(model, test, step)})
        if step == budget:
            break
        candidates = np.array([i for i in train if i not in set(revealed)], dtype=int)
        chosen = int(choose_fn(model, x[candidates], candidates, revealed))
        require(chosen in set(candidates.tolist()), "acquisition returned a non-candidate")
        revealed.append(chosen)
    return revealed, rows
