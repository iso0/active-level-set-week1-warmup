"""Core R&D harness: wraps the repository's frozen components (population, splits,
initial designs, M3 model, B1-q20 evaluator) so that all development stays on
exactly the same protocol as Phase 1.13/1.14.

Development data only: the 405 old cases.  No new-pool labels are touched.
"""
from __future__ import annotations
import sys, math, hashlib, json
from pathlib import Path
import numpy as np, pandas as pd

REPO = Path('/home/claude/active-level-set-week1-warmup')
sys.path.insert(0, str(REPO))
from src import week8_5_frozen_sample_efficiency_confirmation as w85  # noqa: E402
from src import week9_phase1_7_physics_ridge_residual_gp as p17  # noqa: E402
from src import week9_phase1_8_model_path_decomposition as p18  # noqa: E402
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11  # noqa: E402
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13  # noqa: E402
from src import week7_phase6_real_data_boundary_active_level_set as p6  # noqa: E402

FEATURES = ("P", "VX", "LS", "ST")
BUDGETS = tuple(range(16, 81))
RND = Path('/home/claude/rnd')


def seed_u32(*parts) -> int:
    key = "|".join(("rnd2026|v1", *(str(p) for p in parts)))
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "little") % (2**32)


class Data:
    """Frozen population + 100 outer runs + A0 paths + initial designs."""

    def __init__(self):
        population, specs, a0 = p13.load_inputs()
        self.population = population
        self.specs = specs
        self.a0 = a0
        self.x4 = population.loc[:, FEATURES].to_numpy(float)
        self.logh = p11.log_h_values(population)
        self.labels = population.has_keyhole.astype(int).to_numpy()
        self.distances = w85.b1_distance(population)
        self.names = population.experiment_name.astype(str).to_numpy()
        self.spec_by_id = {s.run_id: s for s in specs}

    def flags(self, spec):
        return p17.subset_flags(spec, self.population, self.distances)


def metric_values(truth, prob):
    return p17.metric_values(np.asarray(truth, int), np.asarray(prob, float))


def aulc(values: np.ndarray, budgets: np.ndarray, start: int, end: int) -> float:
    m = (budgets >= start) & (budgets <= end)
    return float(np.trapezoid(values[m], budgets[m]) / (end - start))


# ---------------------------------------------------------------- M3 wrapper

class M3:
    """Exact Phase 1.13/1.14 M3: Stage-1 near-unregularized logistic on
    standardized log h (revealed prefix), frozen; Stage-2 Laplace logistic GPC
    with ARD Matern-3/2 discrepancy on standardized (P,VX,LS,ST)."""

    name = "M3"

    def __init__(self, data: Data, spec, upper: float = 100.0):
        self.d = data
        self.spec = spec
        self.train = np.asarray(spec.train_indices, int)
        self.upper = upper

    def fit(self, revealed, budget_for_seed=None):
        revealed = np.asarray(revealed, int)
        b = len(revealed) if budget_for_seed is None else budget_for_seed
        physics = p11.fit_physics_mean(self.d.logh, self.d.labels, revealed, p13.seed_u32("shared_physics", self.spec.run_id, b))
        self.fit_ = p13.fit_hybrid(self.d.x4, self.d.logh, self.d.labels, revealed, self.train, physics, "M3", self.upper)
        self.revealed_ = revealed
        return self

    def latent(self, idx):
        idx = np.asarray(idx, int)
        comp = p13.components(self.fit_, self.d.x4[idx], self.d.logh[idx])
        return comp["final_latent"], comp["latent_variance"], comp["probability"]

    def proba(self, idx):
        return self.latent(idx)[2]


def margin_select(candidates: np.ndarray, prob: np.ndarray) -> int:
    """Repository margin rule: maximise 1-2|p-0.5|, tie-break smallest row index."""
    score = 1 - 2 * np.abs(prob - 0.5)
    order = np.lexsort((candidates, -score))
    return int(candidates[order[0]])


def argmax_select(candidates: np.ndarray, score: np.ndarray) -> int:
    order = np.lexsort((candidates, -np.asarray(score, float)))
    return int(candidates[order[0]])


def evaluate_curve(model_factory, data: Data, spec, path_or_policy, budgets=BUDGETS, record_queries=None):
    """Run a full active trajectory.  `path_or_policy` is either a fixed list
    (evaluate model along a fixed path) or a callable policy(model, candidates)->int.
    Returns per-budget metric rows (q20/q30/full81) and the final path."""
    test = np.asarray(spec.test_indices, int)
    train = np.asarray(spec.train_indices, int)
    flags = data.flags(spec)
    fixed = not callable(path_or_policy)
    queried = list(map(int, (path_or_policy if fixed else w85.initial_design(spec, data.population))[:16]))
    rows = []
    for budget in budgets:
        assert len(queried) == budget
        model = model_factory(data, spec).fit(np.asarray(queried, int), budget)
        prob = model.proba(test)
        for subset, flag in (("full81", np.ones(len(test), bool)), ("B1_q20", flags["B1_q20"]), ("B1_q30", flags["B1_q30"])):
            rows.append({"run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold, "budget": budget, "subset": subset, **metric_values(data.labels[test][flag], prob[flag])})
        if budget < budgets[-1]:
            if fixed:
                nxt = int(path_or_policy[budget])
            else:
                candidates = np.setdiff1d(train, np.asarray(queried, int))
                nxt = int(path_or_policy(model, candidates, budget))
                if record_queries is not None:
                    record_queries.append({"run_id": spec.run_id, "budget": budget, "selected": nxt})
            assert nxt in set(train.tolist()) and nxt not in queried
            queried.append(nxt)
    return pd.DataFrame(rows), queried


def repeat_block_contrast(a: pd.Series, b: pd.Series, repeats: pd.Series, draws: int = 10000, seed: int = 0):
    """Paired repeat-block bootstrap of mean(a-b): 20 blocks, 5 folds each."""
    diff = pd.DataFrame({"d": np.asarray(a) - np.asarray(b), "r": np.asarray(repeats)}).groupby("r").d.mean()
    vals = diff.to_numpy(float)
    rng = np.random.default_rng(seed)
    boots = vals[rng.integers(0, len(vals), size=(draws, len(vals)))].mean(axis=1)
    return float(vals.mean()), float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975)), int((vals > 0).sum()), int((vals < 0).sum())
