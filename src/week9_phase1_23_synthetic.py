"""Week 9 Phase 1.23 — synthetic 4D level-set stress test of the frozen Phase 1.21 policies.

Nothing here reads the SPH population.  Each ground truth is an independently generated function on
[0,1]^4 with a known physics coordinate

    h(x) = u . (x - 1/2),        u = (1, 1, 1, 1) / 2,

and a boundary that departs from a threshold in h in a controlled way (families below).  For every
function: an i.i.d. uniform candidate pool (the finite pool an active learner may query), an
independent i.i.d. dense test set, and an independent dense reference set used only to measure each
test point's distance to the true boundary.

The evaluator is M3 exactly as frozen (Phase 1.13 fit_hybrid: C = 1e6 physics logistic on h, ARD
Matern-3/2 fixed-mean Laplace GPC discrepancy on standardised x, refit at every budget).  The frozen
policies are the Phase 1.20 objects with the Phase 1.21 parameters, called through the same masked
State; they never see an unqueried label, the test set or the reference set.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
from joblib import Parallel, delayed
from scipy.spatial import cKDTree
from sklearn.preprocessing import StandardScaler

from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_20_acquisition_search as search

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase1_23_method_validity"
CHECKPOINTS = OUTPUT / "synthetic_checkpoints"
SMOKE = OUTPUT / "synthetic_smoke"

DIM = 4
U = np.full(DIM, 0.5)                                  # unit physics direction
SIGMA_COORD = math.sqrt(1.0 / 12.0)                    # SD of any unit-norm projection of U[0,1]^4
RFF_FEATURES = 1000
BUDGET_MAX = 80
SWITCH_BUDGET, PAD_FRACTION, UNCERTAINTY_WEIGHT = 40, 0.25, 1.0   # frozen Phase 1.21 values


def seed_u32(*parts: object) -> int:
    return p13.seed_u32("week9_phase1_23", *parts)


def orthonormal_complement() -> np.ndarray:
    q, _ = np.linalg.qr(np.column_stack([U, np.eye(DIM)[:, :3]]))
    basis = q[:, 1:]
    return basis * np.sign(basis[np.argmax(np.abs(basis), axis=0), range(3)])


Q = orthonormal_complement()                            # 4 x 3, columns orthonormal and orthogonal to U


# ---------------------------------------------------------------- ground truths


@dataclass(frozen=True)
class Cell:
    cell_id: str
    family: str             # physics_exact | shift | fold | islands | rotated
    amplitude: float = 0.0  # boundary displacement SD in units of SD(h)
    length: float = 0.0     # RFF length-scale of the displacement field (x units)
    het_dim: int = 0        # number of orthogonal coordinates the displacement depends on
    islands: int = 0
    island_radius: float = 0.0
    angle_deg: float = 0.0
    prevalence: float = 0.3
    pool: int = 400
    n_functions: int = 40


@dataclass
class Truth:
    pool_x: np.ndarray
    pool_h: np.ndarray
    pool_y: np.ndarray
    test_x: np.ndarray
    test_h: np.ndarray
    test_y: np.ndarray
    test_distance: np.ndarray   # distance to the nearest opposite-class reference point
    q20: np.ndarray
    q30: np.ndarray
    prevalence: float


def rff_field(rng: np.random.Generator, in_dim: int, length: float) -> Callable[[np.ndarray], np.ndarray]:
    omega = rng.normal(0.0, 1.0 / length, size=(RFF_FEATURES, in_dim))
    phase = rng.uniform(0.0, 2 * math.pi, size=RFF_FEATURES)
    weight = rng.normal(0.0, 1.0, size=RFF_FEATURES)

    def field(v: np.ndarray) -> np.ndarray:
        out = np.empty(len(v))
        for start in range(0, len(v), 20_000):
            block = v[start:start + 20_000]
            out[start:start + 20_000] = math.sqrt(2.0 / RFF_FEATURES) * np.cos(block @ omega.T + phase) @ weight
        return out
    return field


def physics_h(x: np.ndarray) -> np.ndarray:
    return (x - 0.5) @ U


def make_truth(cell: Cell, index: int, reference_size: int = 100_000, test_size: int = 4000) -> Truth:
    rng = np.random.default_rng(seed_u32("truth", cell.cell_id, index))
    ref = rng.uniform(size=(reference_size, DIM))
    pool = rng.uniform(size=(cell.pool, DIM))
    test = rng.uniform(size=(test_size, DIM))
    centred = lambda x: x - 0.5
    sigma_h = SIGMA_COORD

    if cell.family in ("physics_exact", "shift", "fold"):
        if cell.family == "physics_exact" or cell.amplitude == 0.0:
            displacement = lambda x: np.zeros(len(x))
        else:
            if cell.family == "shift":
                raw = rff_field(rng, cell.het_dim, cell.length)
                project = lambda x: centred(x) @ Q[:, :cell.het_dim]
            else:
                raw = rff_field(rng, DIM, cell.length)
                project = centred
            r = raw(project(ref))
            mu, sd = r.mean(), r.std()
            displacement = lambda x: cell.amplitude * sigma_h * (raw(project(x)) - mu) / sd
        score_ref = physics_h(ref) - displacement(ref)
        threshold = np.quantile(score_ref, 1.0 - cell.prevalence)
        label = lambda x: (physics_h(x) - displacement(x) - threshold > 0).astype(int)
    elif cell.family == "rotated":
        a = math.radians(cell.angle_deg)
        score = lambda x: math.cos(a) * physics_h(x) + math.sin(a) * (centred(x) @ Q[:, 0])
        threshold = np.quantile(score(ref), 1.0 - cell.prevalence)
        label = lambda x: (score(x) - threshold > 0).astype(int)
    elif cell.family == "islands":
        t0 = np.quantile(physics_h(ref), 1.0 - cell.prevalence)
        r = cell.island_radius
        eligible = ref[(np.abs(physics_h(ref) - t0) >= 1.2 * r) & (np.abs(physics_h(ref) - t0) <= 3 * r)
                       & np.all((ref > r) & (ref < 1 - r), axis=1)]
        centres = eligible[rng.choice(len(eligible), size=cell.islands, replace=False)]
        tree = cKDTree(centres)
        label = lambda x: ((physics_h(x) - t0 > 0) ^ (tree.query(x)[0] < r)).astype(int)
    else:
        raise ValueError(cell.family)

    ref_y, pool_y, test_y = label(ref), label(pool), label(test)
    trees = {c: cKDTree(ref[ref_y == c]) for c in (0, 1)}
    distance = np.empty(test_size)
    for c in (0, 1):
        mask = test_y == c
        distance[mask] = trees[1 - c].query(test[mask])[0]
    order = np.lexsort((np.arange(test_size), distance))
    q20, q30 = np.zeros(test_size, bool), np.zeros(test_size, bool)
    q20[order[:math.ceil(0.2 * test_size)]] = True
    q30[order[:math.ceil(0.3 * test_size)]] = True
    return Truth(pool, physics_h(pool), pool_y, test, physics_h(test), test_y, distance, q20, q30, float(ref_y.mean()))


def truth_path(cell: Cell, index: int, root: Path) -> Path:
    return root / "truths" / cell.cell_id / f"f{index:03d}.npz"


def load_truth(cell: Cell, index: int, root: Path) -> Truth:
    """Deterministic truth, generated once per function and shared by every policy (atomic write)."""
    path = truth_path(cell, index, root)
    if not path.is_file():
        truth = make_truth(cell, index)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.stem + f".{time.time_ns()}.tmp.npz")
        np.savez_compressed(tmp, **{k: np.asarray(v) for k, v in truth.__dict__.items()})
        tmp.replace(path)
    with np.load(path) as data:
        return Truth(**{k: (float(data[k]) if k == "prevalence" else data[k]) for k in Truth.__dataclass_fields__})


# ---------------------------------------------------------------- designs and policies


def maximin_order(x_scaled: np.ndarray, seed: int) -> list[int]:
    """Seeded feature-only greedy maximin order over the whole pool (Week 8.5 initial_design rule)."""
    rng = np.random.default_rng(seed)
    n = len(x_scaled)
    chosen = [int(rng.integers(n))]
    nearest = np.linalg.norm(x_scaled - x_scaled[chosen[0]], axis=1)
    nearest[chosen[0]] = -np.inf
    while len(chosen) < n:
        best = nearest.max()
        ties = np.flatnonzero(np.isclose(nearest, best, rtol=1e-12, atol=1e-14))
        nxt = int(ties.min())
        chosen.append(nxt)
        nearest = np.minimum(nearest, np.linalg.norm(x_scaled - x_scaled[nxt], axis=1))
        nearest[chosen] = -np.inf
    return chosen


def seed_prefix(order: list[int], labels: np.ndarray, k: int) -> list[int]:
    """First k points of the maximin order, extended along the SAME order until both classes are seen."""
    queried = list(order[:k])
    position = k
    while len(np.unique(labels[queried])) < 2:
        queried.append(order[position])
        position += 1
    return queried


def make_global_uncertainty_diversity(switch_budget: int = SWITCH_BUDGET,
                                      weight_unc: float = UNCERTAINTY_WEIGHT) -> Callable[[search.State], int]:
    """Literature analogue (sequential uncertainty + diversity, e.g. Brinker 2003): the frozen rank-sum
    score over ALL candidates, i.e. the frozen rule WITHOUT the label-estimated h-band."""
    def policy(s: search.State) -> int:
        if s.budget >= switch_budget:
            return search.pol_margin(s)
        c = s.x_scaled
        dist = np.sqrt(((c[s.candidates][:, None, :] - c[s.revealed][None, :, :]) ** 2).sum(-1)).min(axis=1)
        unc = 1.0 - 2.0 * np.abs(s.p_cand - 0.5)
        return search.argbest(s.candidates, weight_unc * search._rank01(unc) + search._rank01(dist))
    return policy


def pol_straddle(s: search.State) -> int:
    """Bryan et al. (2005) straddle on the M3 latent, level 0: 1.96 sd - |mean|."""
    return search.argbest(s.candidates, 1.96 * np.sqrt(s.var_cand) - np.abs(s.mean_cand))


def pol_random(s: search.State) -> int:
    order = s.cache["random_order"]
    taken = set(s.revealed.tolist())
    return int(next(i for i in order if i not in taken))


FROZEN_COVERAGE = search.make_band_coverage("x", weight_unc=UNCERTAINTY_WEIGHT, pad_fraction=PAD_FRACTION,
                                            switch_budget=SWITCH_BUDGET)
POLICIES: dict[str, tuple[int, Callable[[search.State], int]]] = {
    "random": (16, pol_random),
    "margin": (16, search.pol_margin),
    "coverage_then_margin_B40": (16, FROZEN_COVERAGE),
    "early8__coverage_then_margin_B40": (8, FROZEN_COVERAGE),
    "early8__margin": (8, search.pol_margin),
    "global_unc_div_then_margin_B40": (16, make_global_uncertainty_diversity()),
    "straddle": (16, pol_straddle),
}


# ---------------------------------------------------------------- one trajectory


def metrics(truth: Truth, probability: np.ndarray) -> dict[str, float]:
    pred = (probability >= 0.5).astype(int)
    y = truth.test_y
    wrong = pred != y
    out = {"acc_global": float(1 - wrong.mean()),
           "acc_q20": float(1 - wrong[truth.q20].mean()),
           "acc_q30": float(1 - wrong[truth.q30].mean()),
           "bacc_global": float(0.5 * ((pred[y == 1] == 1).mean() + (pred[y == 0] == 0).mean())),
           "fp_global": int((wrong & (y == 0)).sum()), "fn_global": int((wrong & (y == 1)).sum()),
           "fp_q20": int((wrong & (y == 0) & truth.q20).sum()), "fn_q20": int((wrong & (y == 1) & truth.q20).sum()),
           "error_depth_q95": float(np.quantile(truth.test_distance[wrong], 0.95)) if wrong.any() else 0.0}
    return out


def run_trajectory(cell: Cell, index: int, policy: str, root: Path) -> dict[str, Any]:
    destination = root / cell.cell_id / policy / f"f{index:03d}.json.gz"
    if destination.is_file():
        return {"cell": cell.cell_id, "index": index, "policy": policy, "reused": True, "seconds": 0.0}
    started = time.time()
    truth = load_truth(cell, index, root)
    k, select = POLICIES[policy]
    n = cell.pool
    train = np.arange(n)
    x_scaled = StandardScaler().fit(truth.pool_x).transform(truth.pool_x)
    order = maximin_order(x_scaled, seed_u32("maximin", cell.cell_id, index))
    queried = seed_prefix(order, truth.pool_y, k)
    seed_size = len(queried)
    cache: dict = {"random_order": list(np.random.default_rng(seed_u32("random", cell.cell_id, index)).permutation(n))}
    rows, steps = [], []
    for budget in range(seed_size, BUDGET_MAX + 1):
        revealed = np.asarray(queried, dtype=int)
        physics = p11.fit_physics_mean(truth.pool_h, truth.pool_y, revealed, seed_u32("physics", cell.cell_id, index, budget))
        fit = p13.fit_hybrid(truth.pool_x, truth.pool_h, truth.pool_y, revealed, train, physics, "M3", search.LENGTH_UPPER)
        if budget >= 16:
            probability = p13.components(fit, truth.test_x, truth.test_h)["probability"]
            rows.append({"budget": budget, **metrics(truth, probability)})
        if budget == BUDGET_MAX:
            break
        candidates = np.setdiff1d(train, revealed)
        comp = p13.components(fit, truth.pool_x[candidates], truth.pool_h[candidates])
        seen_label = np.full(n, -1, dtype=int)
        seen_label[revealed] = truth.pool_y[revealed]
        state = search.State(run_id=f"{cell.cell_id}|{index}", budget=budget, revealed=revealed, candidates=candidates,
                             seen_label=seen_label, seen_logdepth=np.full(n, np.nan), x_scaled=x_scaled,
                             z_scaled=x_scaled, logh=truth.pool_h, p_cand=comp["probability"],
                             mean_cand=comp["final_latent"], var_cand=comp["latent_variance"], fit=fit,
                             rng=np.random.default_rng(seed_u32("rng", cell.cell_id, index, budget)),
                             x4=truth.pool_x, train=train, cache=cache, leaky_rank=None)
        chosen = select(state)
        search.require(chosen in set(candidates.tolist()), f"invalid acquisition by {policy}")
        band = search.estimated_band(state, PAD_FRACTION)
        rev_y = seen_label[revealed]
        steps.append({"budget": budget, "chosen": int(chosen), "margin_choice": int(search.pol_margin(state)),
                      "chosen_in_band": bool(band[np.flatnonzero(candidates == chosen)[0]]),
                      "band_fraction": float(band.mean()),
                      "separable": bool(truth.pool_h[revealed][rev_y == 0].max() < truth.pool_h[revealed][rev_y == 1].min()),
                      "chosen_h": float(truth.pool_h[chosen]),
                      "residual_sd": float(fit.residual_sd)})
        queried.append(chosen)
    payload = {"complete": True, "cell": cell.cell_id, "index": index, "policy": policy, "seed_size": seed_size,
               "pool_prevalence": float(truth.pool_y.mean()), "reference_prevalence": truth.prevalence,
               "queried": [int(i) for i in queried], "metrics": rows, "steps": steps,
               "seconds": time.time() - started}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(gzip.compress(json.dumps(payload).encode(), compresslevel=6, mtime=0))
    return {"cell": cell.cell_id, "index": index, "policy": policy, "reused": False, "seconds": payload["seconds"]}


def run(jobs: list[tuple[Cell, int, str]], root: Path, workers: int) -> list[dict]:
    return Parallel(n_jobs=workers, verbose=2)(delayed(run_trajectory)(c, i, p, root) for c, i, p in jobs)


def main() -> None:
    from src import week9_phase1_23_grid as grid
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    search.require((OUTPUT / "PHASE1_23_SYNTHETIC_PROTOCOL.json").is_file(), "refusing to run before the protocol is frozen")
    functions = sorted({(c.cell_id, i): c for c, i, _ in grid.jobs()}.items())
    Parallel(n_jobs=args.workers)(delayed(load_truth)(c, i, CHECKPOINTS) for (_, i), c in functions)
    print("TRUTHS_READY", len(functions), flush=True)
    results = run(grid.jobs(), CHECKPOINTS, args.workers)
    print("SYNTHETIC_DONE", len(results), "new:", sum(not r["reused"] for r in results))


if __name__ == "__main__":
    main()
