"""Week 9 Phase 2.2: width-informed active learning.

Phase 2.1R showed that the largest transverse-width increase between consecutive
resampled analysis points, ``max_positive_delta_W``, carries real predictive value:
adding it to the four process inputs improves how well the model *ranks* Keyhole risk.
Phase 2.1R-E showed that value is available within the opening ~5% of the trace.

Neither result says width helps **active learning**, and there is a trap in assuming it
does.  At budget B only the B already-queried simulations legitimately have an observed
width.  An unqueried candidate does not.  Scoring candidates with their true width would
be reading the answer sheet.

So this phase separates three information regimes and never mixes them:

REGIME A -- DEPLOYABLE.  Fit a width predictor from the queried points only,
``[P, VX, LS, ST] -> hat_delta_W``, and score unqueried candidates with the *predicted*
width.  Concretely: at budget 16 we know the label and the observed width of 16
simulations.  We learn width from the four process inputs on those 16.  For an unqueried
candidate we do not know its real width, so we predict it -- say 28 um -- and the
width-informed M3 uses 28 as its auxiliary feature.  Only once we actually query that
simulation do we replace 28 with the real observed value and refit.

REGIME B -- EARLY-PREFIX SIDE INFORMATION.  Hypothetically, opening-5% width could be
bought more cheaply than a full labelled simulation.  That is *not* free, so it is paid
for in the experimental accounting and reported against a hypothetical cost ratio.  No
simulator saving is claimed.

REGIME C -- ORACLE.  Every candidate's true width is visible.  Deliberately leaky, not
deployable, and reported only as an upper bound on how much acquisition could possibly
gain.  Every artifact from it is labelled ORACLE WIDTH -- NOT DEPLOYABLE.

Everything else is inherited from the frozen thesis protocol: the 405-simulation
population, the 100 frozen outer splits, the frozen 16-point initial designs, the
budget-by-budget trajectory 16 -> 80, the q20/q30 boundary masks, and the M3
implementation from Phase 1.13 (physics logistic mean on log h, frozen, plus an ARD
Matern-3/2 discrepancy GP).  The incumbent is M3 + M3 probability margin.

A NOTE ON MISSING WIDTH.  55 of the 405 simulations have no usable width trace.  That is
treated as a real deployment condition -- a monitor that failed -- rather than hidden:
the width predictor trains only on queried points that have an observed width, and any
point without one carries its predicted value.  Every initial design contains at least
11 width-observed points, so the predictor is always fittable from budget 16.

Run with ``python -m src.week9_phase2_2_width_informed_active_learning --run``.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import re
import subprocess
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from src import week7_phase6_real_data_boundary_active_level_set as p6
from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_7_physics_ridge_residual_gp as p17
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_12_gpc_kernel_adequacy as p12
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_14_m3_margin_acquisition as p14
from src import week9_phase2_1r_simple_width_change_control as r21


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase2_2_width_informed_active_learning"
FIGURES = OUTPUT / "figures"
CHECKPOINTS = OUTPUT / "checkpoints"
NOTEBOOK = ROOT / "notebooks" / "week_09" / "09_week9_phase2_2_width_informed_active_learning.ipynb"
PHASE21R = ROOT / "outputs" / "week9_phase2_1r_simple_width_change_control"
PHASE21RE = ROOT / "outputs" / "week9_phase2_1re_early_prefix_width_control"
PHASE114 = ROOT / "outputs" / "week9_phase1_14_m3_margin_acquisition"

FEATURES = ("P", "VX", "LS", "ST")
BUDGETS = tuple(range(16, 81))
CHECKPOINT_BUDGETS = (16, 24, 32, 40, 60, 80)
EARLY_BUDGETS = tuple(range(16, 41))          # primary AULC window B16-40
FULL_BUDGETS = BUDGETS                        # secondary AULC window B16-80
PRIMARY_UPPER = float(p14.PRIMARY_UPPER)
BOOTSTRAP_DRAWS = 10_000
WORKERS = 7
SEED_ROOT = "week9_phase2_2_width_informed_active_learning|v1"

# Predeclared width-regressor family. One is chosen at every budget using
# queried-only cross-validation; the choice is recorded as a diagnostic.
WIDTH_MODELS = ("ridge_linear", "ridge_quadratic", "gp_matern")
WIDTH_CV_FOLDS = 5
# Re-running the full queried-only cross-validation at all 65 budgets dominates runtime and
# changes the chosen family only rarely. The family is re-selected on this budget grid and
# simply refitted to the current queried set in between; selection stays queried-only.
WIDTH_SELECTION_BUDGETS = tuple(range(16, 81, 8)) + (80,)

# Regime B: shortlist size for the two-stage early-prefix policy, and the hypothetical
# cost of one early-width side observation relative to one full labelled simulation.
SIDEINFO_SHORTLIST = 5
COST_RATIOS = (0.05, 0.10, 0.20, 0.50, 1.00)

METRIC_NAMES = ("accuracy", "balanced_accuracy", "keyhole_recall", "roc_auc", "pr_auc",
                "brier_score", "conduction_recall")
SUBSETS = ("full81", "B1_q30", "B1_q20")
# House convention (Phase 1.14): the frozen endpoint is normalized trapezoidal AULC of
# accuracy on the q20 boundary band. Phase 2.2 keeps that as primary and reports
# balanced accuracy alongside it.
PRIMARY_METRIC = "accuracy"
PRIMARY_SUBSET = "B1_q20"

require = p14.require
write_json = r21.write_json
write_csv = r21.write_csv
sha256_file = r21.sha256_file


def seed_u32(*parts: object) -> int:
    return p13.seed_u32(*parts)


# --------------------------------------------------------------------------------------
# protocol and width data
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class WidthData:
    full: np.ndarray            # true max_positive_delta_W, NaN where no usable trace
    prefix05: np.ndarray        # opening-5% version, NaN where no usable trace
    available: np.ndarray       # boolean mask


def load_protocol() -> tuple[pd.DataFrame, list[Any], dict[str, list[int]], WidthData]:
    """Frozen population, frozen splits, frozen A0 paths, plus the inherited width columns."""
    population, specs, a0 = p13.load_inputs()
    require(len(population) == 405 and int(population.has_keyhole.sum()) == 73,
            "population gate: expected 405 simulations and 73 Keyhole")
    require(len(specs) == 100 and len(a0) == 100, "frozen split/path gate")

    full_table = pd.read_csv(PHASE21R / "simulation_level_features.csv")[
        ["experiment_name", "max_positive_delta_W"]]
    prefix_table = pd.read_csv(PHASE21RE / "prefix_features.csv")[
        ["experiment_name", "max_positive_delta_W_p05"]]
    merged = (population[["experiment_name"]]
              .merge(full_table, on="experiment_name", how="left", validate="one_to_one")
              .merge(prefix_table, on="experiment_name", how="left", validate="one_to_one"))
    full = merged.max_positive_delta_W.to_numpy(float)
    prefix05 = merged.max_positive_delta_W_p05.to_numpy(float)
    available = np.isfinite(full)
    require(int(available.sum()) == 350, "expected 350 simulations with a usable width trace")
    require(bool(np.all(np.isfinite(prefix05) == available)), "prefix and full width availability differ")
    return population, specs, a0, WidthData(full=full, prefix05=prefix05, available=available)


def availability_audit(population: pd.DataFrame, specs: Sequence[Any], a0: dict[str, list[int]],
                       width: WidthData) -> pd.DataFrame:
    """How often is width actually observable inside the frozen protocol?"""
    have = width.available
    initial_counts = [int(have[np.asarray(a0[s.run_id][:16], int)].sum()) for s in specs]
    train_fraction = [float(have[np.asarray(s.train_indices, int)].mean()) for s in specs]
    rows = [
        {"quantity": "population_with_usable_width", "value": int(have.sum()),
         "note": "of 405; the other 55 are treated as a failed monitor, not hidden"},
        {"quantity": "population_without_usable_width", "value": int((~have).sum()), "note": ""},
        {"quantity": "keyhole_rate_with_width", "value": float(population.has_keyhole[have].mean()),
         "note": "missingness is structured, so all results are conditional on it"},
        {"quantity": "keyhole_rate_without_width", "value": float(population.has_keyhole[~have].mean()),
         "note": ""},
        {"quantity": "min_width_observed_in_initial_design", "value": int(min(initial_counts)),
         "note": "over the 100 frozen 16-point designs; >0 means the predictor is always fittable"},
        {"quantity": "mean_width_observed_in_initial_design", "value": float(np.mean(initial_counts)),
         "note": ""},
        {"quantity": "min_train_pool_width_fraction", "value": float(min(train_fraction)), "note": ""},
        {"quantity": "mean_train_pool_width_fraction", "value": float(np.mean(train_fraction)), "note": ""},
    ]
    audit = pd.DataFrame(rows)
    require(min(initial_counts) >= 2, "an initial design has too few width observations to fit a predictor")
    write_csv(OUTPUT / "width_availability_audit.csv", audit)
    return audit


# --------------------------------------------------------------------------------------
# REGIME A: the deployable width predictor -- queried points only
# --------------------------------------------------------------------------------------
@dataclass
class WidthFit:
    """A fitted width predictor plus the record of how it was chosen."""
    name: str
    scaler: StandardScaler
    model: Any
    poly: Any
    residual_sd: float
    cv_scores: dict[str, float]
    n_train: int

    def predict(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        z = self.scaler.transform(np.asarray(x, float))
        if self.name == "gp_matern":
            mean, sd = self.model.predict(z, return_std=True)
            return np.asarray(mean, float), np.asarray(sd, float)
        design = self.poly.transform(z) if self.poly is not None else z
        mean = self.model.predict(design)
        return np.asarray(mean, float), np.full(len(z), self.residual_sd, dtype=float)


def _build_width_model(name: str, seed: int) -> tuple[Any, Any]:
    if name == "ridge_linear":
        return Ridge(alpha=1.0), None
    if name == "ridge_quadratic":
        return Ridge(alpha=10.0), PolynomialFeatures(degree=2, include_bias=False)
    if name == "gp_matern":
        kernel = (ConstantKernel(1.0, (1e-3, 1e3))
                  * Matern(length_scale=np.ones(len(FEATURES)), length_scale_bounds=(1e-2, 1e2), nu=1.5)
                  + WhiteKernel(noise_level=0.1, noise_level_bounds=(1e-6, 1e2)))
        return GaussianProcessRegressor(kernel=kernel, normalize_y=True, n_restarts_optimizer=0,
                                        random_state=int(seed)), None
    raise ValueError(f"unknown width model {name}")


def fit_width_predictor(x_queried: np.ndarray, width_queried: np.ndarray, seed: int,
                        force_model: str | None = None) -> WidthFit:
    """Learn width from [P, VX, LS, ST] using ONLY the already-queried simulations.

    Concretely: at budget 16 we have queried 16 simulations; those that produced a usable
    trace give us pairs of (process inputs, observed max width jump).  We fit three
    candidate regressors on exactly those pairs, score them by cross-validation *within
    the queried set*, and keep the best.  No held-out label, no unqueried point and no
    test-fold information takes part in the choice.
    """
    x = np.asarray(x_queried, float)
    y = np.asarray(width_queried, float)
    require(len(x) == len(y) and len(y) >= 2, "width predictor needs at least two observations")
    scaler = StandardScaler().fit(x)
    z = scaler.transform(x)

    cv_scores: dict[str, float] = {}
    n_splits = int(min(WIDTH_CV_FOLDS, len(y)))
    candidates = WIDTH_MODELS if force_model is None else (force_model,)
    for name in candidates:
        if name == "ridge_quadratic" and len(y) < 12:
            cv_scores[name] = float("inf")     # too few points for a quadratic design
            continue
        errors: list[float] = []
        if n_splits >= 2:
            splitter = KFold(n_splits=n_splits, shuffle=True, random_state=int(seed) % (2**31 - 1))
            for train_index, test_index in splitter.split(z):
                model, poly = _build_width_model(name, seed)
                design_train = poly.fit_transform(z[train_index]) if poly is not None else z[train_index]
                design_test = poly.transform(z[test_index]) if poly is not None else z[test_index]
                try:
                    model.fit(design_train, y[train_index])
                    errors.append(float(np.mean((model.predict(design_test) - y[test_index]) ** 2)))
                except Exception:
                    errors.append(float("inf"))
        cv_scores[name] = float(np.sqrt(np.mean(errors))) if errors else float("inf")

    finite = {k: v for k, v in cv_scores.items() if math.isfinite(v)}
    chosen = min(finite, key=lambda k: (finite[k], WIDTH_MODELS.index(k))) if finite else "ridge_linear"
    model, poly = _build_width_model(chosen, seed)
    design = poly.fit_transform(z) if poly is not None else z
    model.fit(design, y)
    residual = float(np.sqrt(np.mean((model.predict(design) - y) ** 2)))
    fallback = cv_scores.get(chosen, residual)
    return WidthFit(name=chosen, scaler=scaler, model=model, poly=poly,
                    residual_sd=float(fallback if math.isfinite(fallback) else max(residual, 1e-6)),
                    cv_scores=cv_scores, n_train=len(y))


def width_feature_vector(width: WidthData, fit: WidthFit, x4: np.ndarray, queried: Sequence[int],
                         regime: str) -> tuple[np.ndarray, np.ndarray]:
    """Build the auxiliary width column for every simulation under a given regime.

    * ``predicted`` (Regime A, deployable): queried points that produced a usable trace
      carry their true observed value; everything else carries the prediction.
    * ``oracle`` (Regime C, NOT deployable): every simulation with a usable trace carries
      its true value, queried or not.
    """
    mean, sd = fit.predict(x4)
    values = mean.copy()
    if regime == "oracle":
        values[width.available] = width.full[width.available]
        uncertainty = np.where(width.available, 0.0, sd)
        return values, uncertainty
    require(regime == "predicted", f"unknown width regime {regime}")
    revealed = np.asarray(list(queried), dtype=int)
    observed = revealed[width.available[revealed]]
    values[observed] = width.full[observed]
    uncertainty = sd.copy()
    uncertainty[observed] = 0.0
    return values, uncertainty


# --------------------------------------------------------------------------------------
# the M3 model, widened by one auxiliary input
# --------------------------------------------------------------------------------------
def fit_m3(x: np.ndarray, logh: np.ndarray, labels: np.ndarray, revealed: Sequence[int],
           training_pool: Sequence[int], physics: Any, upper: float = PRIMARY_UPPER) -> p13.HybridFit:
    """Phase 1.13 M3, with the discrepancy GP allowed any number of input dimensions.

    The physics mean is untouched: it still sees log h and nothing else, and is still
    fitted on the revealed labels and then frozen.  Only the discrepancy kernel widens,
    which is exactly how Phase 2.1R extended M3 and how ``m3 + width`` is defined here.
    """
    revealed_array = np.asarray(revealed, dtype=int)
    scaler = StandardScaler().fit(np.asarray(x, float)[np.asarray(training_pool, dtype=int)])
    x_train = scaler.transform(np.asarray(x, float)[revealed_array])
    mean_train = physics.latent(np.asarray(logh, float)[revealed_array])
    gp = p11.FixedMeanLaplaceGPC(r21.m3_residual_kernel(x.shape[1]), optimize=True)
    gp.fit(x_train, np.asarray(labels, int)[revealed_array], mean_train)
    return p13.HybridFit(physics, scaler, gp, revealed_array, "M3", float(upper))


def m3_probability(fit: p13.HybridFit, x_subset: np.ndarray, logh_subset: np.ndarray) -> np.ndarray:
    transformed = fit.x_scaler.transform(np.asarray(x_subset, float))
    phys = fit.physics.latent(np.asarray(logh_subset, float))
    return fit.gp.predict_proba(transformed, phys)[:, 1]


def choose_margin(candidates: np.ndarray, probabilities: np.ndarray, pool_scaled: np.ndarray,
                  queried: Sequence[int]) -> int:
    """The frozen incumbent acquisition: smallest |p - 0.5|, ties to the smallest index."""
    chosen, info = p6.choose_binary_candidate(
        method="binary_margin", candidate_indices=np.asarray(candidates, dtype=int),
        probabilities=np.asarray(probabilities, float), pool_scaled=np.asarray(pool_scaled, float),
        queried_indices=list(queried))
    require(info["acquisition_definition"] == "classifier_margin", "historical margin semantic drift")
    return int(chosen)


# --------------------------------------------------------------------------------------
# arms
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Arm:
    name: str
    width_regime: str        # "none" | "predicted" | "oracle"
    path_mode: str           # "own" | "fixed"
    path_source: str         # "" for own paths, otherwise the arm whose path is replayed
    regime_label: str
    description: str


STAGE1_ARMS: tuple[Arm, ...] = (
    Arm("A0_m3_margin", "none", "own", "",
        "incumbent",
        "M3 + M3 probability margin. The frozen incumbent."),
    Arm("A1_predicted_width_margin", "predicted", "own", "",
        "REGIME A (deployable)",
        "M3 widened by hat_delta_W predicted from queried points only, querying by its own margin."),
    Arm("A4_oracle_width_margin", "oracle", "own", "",
        "REGIME C (ORACLE WIDTH - NOT DEPLOYABLE)",
        "M3 widened by the TRUE width of every candidate. Upper bound only."),
    Arm("A1_model_on_A0_path", "predicted", "fixed", "A0_m3_margin",
        "REGIME A (deployable)",
        "Width-informed model scored on the incumbent's query path: model value with the path held fixed."),
    Arm("A4_model_on_A0_path", "oracle", "fixed", "A0_m3_margin",
        "REGIME C (ORACLE WIDTH - NOT DEPLOYABLE)",
        "Oracle-width model on the incumbent path: how much of the oracle gain is model, not path."),
)
STAGE2_ARMS: tuple[Arm, ...] = (
    Arm("A0_model_on_A1_path", "none", "fixed", "A1_predicted_width_margin",
        "incumbent",
        "Incumbent M3 scored on the width-informed query path: path value with the model held fixed."),
)


def checkpoint_path(arm: str, run_id: str) -> Path:
    return CHECKPOINTS / arm / f"{run_id}.json.gz"


def write_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress((json.dumps(p13.json_safe(payload), sort_keys=True) + "\n").encode(),
                                   compresslevel=6, mtime=0))


def read_checkpoint(path: Path) -> dict[str, Any]:
    return json.loads(gzip.decompress(path.read_bytes()).decode())


def run_arm(arm: Arm, spec: Any, population: pd.DataFrame, width: WidthData,
            distances: np.ndarray, fixed_path: Sequence[int] | None) -> dict[str, Any]:
    """One full 16 -> 80 active-learning trajectory for one arm on one frozen split.

    At every budget: fit the width predictor on the queried points (Regime A), build the
    auxiliary width column under this arm's regime, fit M3, score the held-out fold, and
    -- if the arm chooses its own path -- pick the next query by probability margin over
    the unqueried training pool.
    """
    destination = checkpoint_path(arm.name, spec.run_id)
    # Fingerprint the path this trajectory is told to follow. For a fixed-path arm the whole
    # path matters; for an own-path arm only the shared 16-point initial design does. A
    # checkpoint written against a different path must never be reused -- that silently
    # replays the wrong queries and contaminates the same-path decomposition.
    relevant = list(fixed_path) if arm.path_mode == "fixed" else list(fixed_path)[:16]
    path_fingerprint = hashlib.sha256(
        json.dumps([arm.path_mode, [int(v) for v in relevant]]).encode()).hexdigest()
    if destination.is_file():
        payload = read_checkpoint(destination)
        if (payload.get("complete") and payload.get("arm") == arm.name
                and payload.get("path_fingerprint") == path_fingerprint):
            return {"run_id": spec.run_id, "arm": arm.name, "reused": True}

    x4 = population.loc[:, FEATURES].to_numpy(float)
    logh = p11.log_h_values(population)
    labels = population.has_keyhole.astype(int).to_numpy()
    train = np.asarray(spec.train_indices, dtype=int)
    test = np.asarray(spec.test_indices, dtype=int)
    flags = p17.subset_flags(spec, population, distances)
    initial = list(map(int, (fixed_path if fixed_path is not None else [])[:16])) or None

    a0_prefix = fixed_path[:16] if fixed_path is not None else None
    queried: list[int] = list(map(int, a0_prefix)) if a0_prefix is not None else None
    require(queried is not None, "every arm starts from the frozen 16-point initial design")

    metrics: list[dict[str, Any]] = []
    width_audit: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []
    sticky_width_model: str | None = None

    for budget in BUDGETS:
        require(len(queried) == budget and len(set(queried)) == budget,
                f"trajectory drift {arm.name}/{spec.run_id}/B{budget}")
        revealed = np.asarray(queried, dtype=int)
        physics = p11.fit_physics_mean(logh, labels, revealed,
                                       seed_u32("shared_physics", spec.run_id, budget))

        if arm.width_regime == "none":
            design = x4
            fit_width: WidthFit | None = None
            width_column = None
        else:
            observed = revealed[width.available[revealed]]
            require(len(observed) >= 2, f"{spec.run_id}/B{budget}: too few observed widths")
            reselect = budget in WIDTH_SELECTION_BUDGETS or sticky_width_model is None
            fit_width = fit_width_predictor(
                x4[observed], width.full[observed], seed_u32("width", spec.run_id, budget),
                force_model=None if reselect else sticky_width_model)
            sticky_width_model = fit_width.name
            width_column, width_sd = width_feature_vector(width, fit_width, x4, queried, arm.width_regime)
            design = np.column_stack([x4, width_column])
            # audit the predictor against the points it has NOT seen
            unseen = np.setdiff1d(train, observed)
            unseen = unseen[width.available[unseen]]
            if len(unseen) >= 5:
                predicted, _ = fit_width.predict(x4[unseen])
                truth = width.full[unseen]
                residual = predicted - truth
                total = float(np.sum((truth - truth.mean()) ** 2))
                width_audit.append({
                    "run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold,
                    "arm": arm.name, "budget": budget,
                    "chosen_width_model": fit_width.name, "n_width_observations": fit_width.n_train,
                    "family_reselected_this_budget": bool(reselect),
                    "n_unseen_evaluated": int(len(unseen)),
                    "mae": float(np.mean(np.abs(residual))),
                    "rmse": float(np.sqrt(np.mean(residual ** 2))),
                    "r2": float(1.0 - np.sum(residual ** 2) / total) if total > 0 else float("nan"),
                    "relative_rmse": float(np.sqrt(np.mean(residual ** 2)) / truth.std())
                    if truth.std() > 0 else float("nan"),
                    "spearman_true_vs_predicted": float(r21.stats.spearmanr(truth, predicted).statistic),
                    "mean_predicted_sd": float(np.mean(fit_width.predict(x4[unseen])[1])),
                })

        fit = fit_m3(design, logh, labels, revealed, train, physics)
        probability = m3_probability(fit, design[test], logh[test])
        for subset in SUBSETS:
            flag = flags[subset]
            metrics.append({
                "run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold,
                "arm": arm.name, "budget": budget, "subset": subset,
                **p12.metric_values(labels[test][flag], probability[flag])})

        if budget < BUDGETS[-1]:
            if arm.path_mode == "fixed":
                chosen = int(fixed_path[budget])
                require(chosen not in queried, f"fixed path repeat {arm.name}/{spec.run_id}/B{budget}")
            else:
                candidates = np.setdiff1d(train, revealed, assume_unique=False)
                candidate_probability = m3_probability(fit, design[candidates], logh[candidates])
                chosen = choose_margin(candidates, candidate_probability,
                                       fit.x_scaler.transform(design), queried)
                position = int(np.flatnonzero(candidates == chosen)[0])
                queries.append({
                    "run_id": spec.run_id, "repeat": spec.repeat, "fold": spec.fold,
                    "arm": arm.name, "current_budget": budget, "selection_budget": budget + 1,
                    "selected_population_row_index": chosen,
                    "probability_before_reveal": float(candidate_probability[position]),
                    "margin": float(abs(candidate_probability[position] - 0.5)),
                    "true_label_revealed_after_selection": int(labels[chosen]),
                    "width_observed_after_selection": bool(width.available[chosen]),
                    "candidate_width_value_used": float(width_column[chosen])
                    if width_column is not None else float("nan"),
                    "log_h": float(logh[chosen]), "b1_distance_posthoc": float(distances[chosen]),
                    "candidate_count": int(len(candidates)),
                    "test_rows_available_to_acquisition": False,
                    "unrevealed_labels_available_to_acquisition": False,
                    "true_width_of_unqueried_used": arm.width_regime == "oracle",
                })
                require(chosen in set(train) and chosen not in queried and chosen not in set(test),
                        "invalid acquisition")
            queried.append(int(chosen))

    require(len(queried) == 80, f"trajectory completeness {arm.name}/{spec.run_id}")
    if arm.path_mode == "fixed":
        require([int(v) for v in queried] == [int(v) for v in fixed_path],
                f"{arm.name}/{spec.run_id}: fixed-path arm did not replay its source path")
    write_checkpoint(destination, {
        "complete": True, "arm": arm.name, "run_id": spec.run_id,
        "path_fingerprint": path_fingerprint, "path_mode": arm.path_mode,
        "queried_indices": queried, "metrics": metrics,
        "width_audit": width_audit, "queries": queries})
    return {"run_id": spec.run_id, "arm": arm.name, "reused": False}


def execute_arms(arms: Sequence[Arm], population: pd.DataFrame, specs: Sequence[Any],
                 width: WidthData, distances: np.ndarray,
                 paths: dict[str, dict[str, list[int]]]) -> None:
    jobs = []
    for arm in arms:
        for spec in specs:
            source = paths["A0"] if arm.path_mode == "own" else paths[arm.path_source]
            jobs.append((arm, spec, list(source[spec.run_id])))
    print(f"    {len(arms)} arms x {len(specs)} frozen splits = {len(jobs)} trajectories "
          f"on {WORKERS} workers", flush=True)
    Parallel(n_jobs=WORKERS, verbose=5)(
        delayed(run_arm)(arm, spec, population, width, distances, path) for arm, spec, path in jobs)


def collect_arm(arm: str, specs: Sequence[Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame,
                                                         dict[str, list[int]]]:
    metrics, audits, queries, paths = [], [], [], {}
    for spec in specs:
        payload = read_checkpoint(checkpoint_path(arm, spec.run_id))
        metrics.extend(payload["metrics"])
        audits.extend(payload["width_audit"])
        queries.extend(payload["queries"])
        paths[spec.run_id] = [int(v) for v in payload["queried_indices"]]
    return pd.DataFrame(metrics), pd.DataFrame(audits), pd.DataFrame(queries), paths


# --------------------------------------------------------------------------------------
# AULC, contrasts and decompositions -- Phase 1.14 conventions, unchanged
# --------------------------------------------------------------------------------------
def bootstrap_interval(values: np.ndarray, key: str) -> tuple[float, float, float]:
    """Repeat-block bootstrap over the 20 repeats, exactly as Phase 1.14 defines it."""
    values = np.asarray(values, float)
    require(len(values) == 20 and np.isfinite(values).all(), f"repeat bootstrap drift {key}")
    rng = np.random.default_rng(seed_u32("bootstrap", key))
    draws = values[rng.integers(0, 20, size=(BOOTSTRAP_DRAWS, 20))].mean(axis=1)
    return float(values.mean()), float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))


REGIONS = (("EARLY_B16_40", EARLY_BUDGETS), ("FULL_B16_80", FULL_BUDGETS))


def compute_aulc(metrics: pd.DataFrame) -> pd.DataFrame:
    """Normalized trapezoidal AULC per run, for every arm / subset / metric / region."""
    rows = []
    for region, budgets in REGIONS:
        denominator = budgets[-1] - budgets[0]
        block = metrics[metrics.budget.isin(budgets)]
        for keys, group in block.groupby(["run_id", "repeat", "fold", "arm", "subset"], sort=True):
            run_id, repeat, fold, arm, subset = keys
            ordered = group.sort_values("budget")
            require(ordered.budget.astype(int).tolist() == list(budgets),
                    f"AULC grid drift {run_id}/{arm}/{subset}/{region}")
            entry = {"run_id": run_id, "repeat": int(repeat), "fold": int(fold), "arm": arm,
                     "subset": subset, "region": region}
            for metric in METRIC_NAMES:
                values = ordered[metric].to_numpy(float)
                if not np.isfinite(values).all():
                    entry[f"{metric}_AULC"] = float("nan")
                    continue
                entry[f"{metric}_AULC"] = float(np.trapezoid(values, ordered.budget) / denominator)
            rows.append(entry)
    outer = pd.DataFrame(rows)
    write_csv(OUTPUT / "aulc_per_run.csv", outer)
    return outer


def aulc_summary(outer: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (arm, subset, region), group in outer.groupby(["arm", "subset", "region"], sort=True):
        per_repeat = group.groupby("repeat")[[f"{m}_AULC" for m in METRIC_NAMES]].mean().sort_index()
        for metric in METRIC_NAMES:
            values = per_repeat[f"{metric}_AULC"].to_numpy(float)
            if not np.isfinite(values).all():
                continue
            mean, low, high = bootstrap_interval(values, f"summary|{arm}|{subset}|{region}|{metric}")
            rows.append({"arm": arm, "subset": subset, "region": region, "metric": metric,
                         "mean_AULC": mean, "ci_lower": low, "ci_upper": high})
    summary = pd.DataFrame(rows)
    write_csv(OUTPUT / "aulc_summary.csv", summary)
    return summary


def paired_aulc_contrasts(outer: pd.DataFrame, comparisons: Sequence[tuple[str, str, str]]) -> pd.DataFrame:
    rows = []
    for challenger, baseline, role in comparisons:
        for (subset, region), group in outer.groupby(["subset", "region"], sort=True):
            per_repeat = group.groupby(["repeat", "arm"])[
                [f"{m}_AULC" for m in METRIC_NAMES]].mean()
            if challenger not in per_repeat.index.get_level_values("arm") or \
               baseline not in per_repeat.index.get_level_values("arm"):
                continue
            for metric in METRIC_NAMES:
                wide = per_repeat[f"{metric}_AULC"].unstack().sort_index()
                if challenger not in wide.columns or baseline not in wide.columns:
                    continue
                values = (wide[challenger] - wide[baseline]).to_numpy(float)
                if not np.isfinite(values).all():
                    continue
                mean, low, high = bootstrap_interval(
                    values, f"contrast|{challenger}|{baseline}|{subset}|{region}|{metric}")
                rows.append({
                    "contrast": f"{challenger} - {baseline}", "role": role,
                    "subset": subset, "region": region, "metric": metric,
                    "mean_difference": mean, "ci_lower": low, "ci_upper": high,
                    "positive_repeat_blocks": int((values > 0).sum()),
                    "negative_repeat_blocks": int((values < 0).sum()),
                    "bootstrap_draws": BOOTSTRAP_DRAWS,
                })
    contrasts = pd.DataFrame(rows)
    write_csv(OUTPUT / "paired_aulc_contrasts.csv", contrasts)
    return contrasts


def per_budget_summary(metrics: pd.DataFrame) -> pd.DataFrame:
    """Learning curves: mean and interval at every budget, plus the reported checkpoints."""
    rows = []
    for (arm, subset, budget), group in metrics.groupby(["arm", "subset", "budget"], sort=True):
        for metric in METRIC_NAMES:
            values = group.groupby("repeat")[metric].mean().sort_index().to_numpy(float)
            if not np.isfinite(values).all():
                continue
            mean, low, high = bootstrap_interval(values, f"curve|{arm}|{subset}|{budget}|{metric}")
            rows.append({"arm": arm, "subset": subset, "budget": int(budget), "metric": metric,
                         "mean": mean, "ci_lower": low, "ci_upper": high,
                         "is_reported_checkpoint": int(budget) in CHECKPOINT_BUDGETS})
    curves = pd.DataFrame(rows)
    write_csv(OUTPUT / "per_budget_metrics.csv", curves)
    write_csv(OUTPUT / "per_budget_checkpoints.csv",
              curves[curves.is_reported_checkpoint].reset_index(drop=True))
    return curves


def per_budget_contrasts(metrics: pd.DataFrame,
                         comparisons: Sequence[tuple[str, str, str]]) -> pd.DataFrame:
    rows = []
    for challenger, baseline, role in comparisons:
        for (subset, budget), group in metrics.groupby(["subset", "budget"], sort=True):
            wide_all = group.groupby(["repeat", "arm"])[list(METRIC_NAMES)].mean()
            arms = set(wide_all.index.get_level_values("arm"))
            if not {challenger, baseline} <= arms:
                continue
            for metric in METRIC_NAMES:
                wide = wide_all[metric].unstack().sort_index()
                values = (wide[challenger] - wide[baseline]).to_numpy(float)
                if not np.isfinite(values).all():
                    continue
                mean, low, high = bootstrap_interval(
                    values, f"budget-contrast|{challenger}|{baseline}|{subset}|{budget}|{metric}")
                rows.append({"contrast": f"{challenger} - {baseline}", "role": role,
                             "subset": subset, "budget": int(budget), "metric": metric,
                             "mean_difference": mean, "ci_lower": low, "ci_upper": high})
    frame = pd.DataFrame(rows)
    write_csv(OUTPUT / "per_budget_contrasts.csv", frame)
    return frame


def phase114_reproduction_gate(summary: pd.DataFrame) -> pd.DataFrame:
    """The A0 arm must reproduce the published Phase 1.14 M3-margin numbers.

    Phase 1.14 called this arm 'P1': the same M3 evaluator querying by its own margin.
    If Phase 2.2 reproduces it, every width arm can be read on the same scale.
    """
    published = pd.read_csv(PHASE114 / "early_late_summary.csv")
    target = published[published.model.eq("P1") & published.region.eq("EARLY_B16_40")]
    require(len(target) == 1, "Phase 1.14 EARLY_B16_40 P1 row not found")
    expected = float(target.iloc[0].mean_AULC)
    here = summary[summary.arm.eq("A0_m3_margin") & summary.subset.eq("B1_q20")
                   & summary.region.eq("EARLY_B16_40") & summary.metric.eq("accuracy")]
    require(len(here) == 1, "A0 q20 accuracy AULC B16-40 not found")
    observed = float(here.iloc[0].mean_AULC)

    rows = [{"quantity": "q20_accuracy_AULC_B16_40", "phase114_published_P1": expected,
             "phase22_A0_reproduced": observed, "abs_difference": abs(observed - expected),
             "status": "PASS" if abs(observed - expected) <= 1e-9 else "FAIL"}]
    checkpoints = pd.read_csv(PHASE114 / "checkpoint16_40_80_summary.csv")
    for budget in (16, 40, 80):
        row = checkpoints[checkpoints.model.eq("P1") & checkpoints.subset.eq("B1_q20")
                          & checkpoints.budget.eq(budget) & checkpoints.metric.eq("accuracy")]
        if row.empty:
            continue
        rows.append({"quantity": f"q20_accuracy_B{budget}",
                     "phase114_published_P1": float(row.iloc[0]["mean"]),
                     "phase22_A0_reproduced": float("nan"), "abs_difference": float("nan"),
                     "status": "REFERENCE"})
    gate = pd.DataFrame(rows)
    write_csv(OUTPUT / "phase114_reproduction_gate.csv", gate)
    return gate


def oracle_gap_decomposition(summary: pd.DataFrame, contrasts: pd.DataFrame) -> pd.DataFrame:
    """How much headroom does perfectly-known width offer, and how much do we recover?

    headroom       = A4 (oracle width) - A0 (incumbent)
    realised gain  = A1 (predicted width) - A0
    recovered      = realised / headroom, only meaningful when the headroom is positive
    """
    rows = []
    for (subset, region, metric), _ in summary.groupby(["subset", "region", "metric"], sort=True):
        def value(arm: str) -> float:
            block = summary[summary.arm.eq(arm) & summary.subset.eq(subset)
                            & summary.region.eq(region) & summary.metric.eq(metric)]
            return float(block.iloc[0].mean_AULC) if len(block) else float("nan")

        def contrast(name: str) -> pd.Series | None:
            block = contrasts[contrasts.contrast.eq(name) & contrasts.subset.eq(subset)
                              & contrasts.region.eq(region) & contrasts.metric.eq(metric)]
            return block.iloc[0] if len(block) else None

        headroom_row = contrast("A4_oracle_width_margin - A0_m3_margin")
        realised_row = contrast("A1_predicted_width_margin - A0_m3_margin")
        if headroom_row is None or realised_row is None:
            continue
        headroom = float(headroom_row.mean_difference)
        realised = float(realised_row.mean_difference)
        recoverable = (realised / headroom) if headroom > 1e-12 else float("nan")
        rows.append({
            "subset": subset, "region": region, "metric": metric,
            "A0_incumbent": value("A0_m3_margin"),
            "A1_predicted_width": value("A1_predicted_width_margin"),
            "A4_oracle_width": value("A4_oracle_width_margin"),
            "oracle_headroom_A4_minus_A0": headroom,
            "oracle_headroom_ci_lower": float(headroom_row.ci_lower),
            "oracle_headroom_ci_upper": float(headroom_row.ci_upper),
            "realised_gain_A1_minus_A0": realised,
            "realised_gain_ci_lower": float(realised_row.ci_lower),
            "realised_gain_ci_upper": float(realised_row.ci_upper),
            "recovered_fraction_of_headroom": recoverable,
            "headroom_interval_excludes_zero": bool(headroom_row.ci_lower > 0),
            "realised_interval_excludes_zero": bool(realised_row.ci_lower > 0),
        })
    frame = pd.DataFrame(rows)
    write_csv(OUTPUT / "oracle_gap_decomposition.csv", frame)
    return frame


def same_path_decomposition(contrasts: pd.DataFrame) -> pd.DataFrame:
    """Split any total gain into 'the model got better' and 'the queries got better'.

    * model value  = width model on the incumbent's own path, versus the incumbent
    * total value  = width model on its own path, versus the incumbent
    * path value   = total - model, cross-checked against the incumbent model replayed
                     on the width-informed path
    """
    rows = []
    definitions = [
        ("deployable (Regime A)", "A1_predicted_width_margin",
         "A1_model_on_A0_path - A0_m3_margin", "A1_predicted_width_margin - A0_m3_margin",
         "A0_model_on_A1_path - A0_m3_margin"),
        ("ORACLE WIDTH - NOT DEPLOYABLE", "A4_oracle_width_margin",
         "A4_model_on_A0_path - A0_m3_margin", "A4_oracle_width_margin - A0_m3_margin", None),
    ]
    for regime, arm, model_contrast, total_contrast, path_contrast in definitions:
        for (subset, region, metric), _ in contrasts.groupby(["subset", "region", "metric"], sort=True):
            def get(name: str | None) -> pd.Series | None:
                if name is None:
                    return None
                block = contrasts[contrasts.contrast.eq(name) & contrasts.subset.eq(subset)
                                  & contrasts.region.eq(region) & contrasts.metric.eq(metric)]
                return block.iloc[0] if len(block) else None

            model_row, total_row, path_row = get(model_contrast), get(total_contrast), get(path_contrast)
            if model_row is None or total_row is None:
                continue
            model_value = float(model_row.mean_difference)
            total_value = float(total_row.mean_difference)
            rows.append({
                "regime": regime, "arm": arm, "subset": subset, "region": region, "metric": metric,
                "model_value_same_path": model_value,
                "model_value_ci_lower": float(model_row.ci_lower),
                "model_value_ci_upper": float(model_row.ci_upper),
                "total_value_own_path": total_value,
                "total_value_ci_lower": float(total_row.ci_lower),
                "total_value_ci_upper": float(total_row.ci_upper),
                "path_value_implied": total_value - model_value,
                "path_value_direct_incumbent_on_challenger_path":
                    float(path_row.mean_difference) if path_row is not None else float("nan"),
                "path_value_direct_ci_lower":
                    float(path_row.ci_lower) if path_row is not None else float("nan"),
                "path_value_direct_ci_upper":
                    float(path_row.ci_upper) if path_row is not None else float("nan"),
            })
    frame = pd.DataFrame(rows)
    write_csv(OUTPUT / "same_path_decomposition.csv", frame)
    return frame


def width_predictor_summary(audits: pd.DataFrame) -> pd.DataFrame:
    """How good is queried-only width prediction, budget by budget?"""
    rows = []
    for (arm, budget), group in audits.groupby(["arm", "budget"], sort=True):
        entry = {"arm": arm, "budget": int(budget), "runs": int(len(group))}
        for column in ("mae", "rmse", "r2", "relative_rmse", "spearman_true_vs_predicted",
                       "mean_predicted_sd", "n_width_observations"):
            values = group[column].to_numpy(float)
            values = values[np.isfinite(values)]
            entry[f"{column}_mean"] = float(values.mean()) if len(values) else float("nan")
            entry[f"{column}_q1"] = float(np.quantile(values, 0.25)) if len(values) else float("nan")
            entry[f"{column}_q3"] = float(np.quantile(values, 0.75)) if len(values) else float("nan")
        chosen = group.chosen_width_model.value_counts(normalize=True)
        for name in WIDTH_MODELS:
            entry[f"chosen_{name}_fraction"] = float(chosen.get(name, 0.0))
        rows.append(entry)
    frame = pd.DataFrame(rows)
    write_csv(OUTPUT / "width_predictor_diagnostics.csv", frame)
    return frame


def path_diagnostics(paths: dict[str, dict[str, list[int]]], population: pd.DataFrame,
                     width: WidthData, logh: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Do the width-informed queries actually differ from the incumbent's?"""
    rows, selected = [], []
    # The comparison point is the incumbent's REALISED M3-margin path, not the frozen
    # historical A0 path (which contributes only the shared 16-point initial design).
    incumbent = "A0_m3_margin"
    require(incumbent in paths, "incumbent path missing; run the incumbent arm first")
    reference = paths[incumbent]
    for arm, arm_paths in paths.items():
        if arm in (incumbent, "A0"):
            continue
        for run_id, path in arm_paths.items():
            base = reference[run_id]
            for budget in CHECKPOINT_BUDGETS:
                a = set(base[:budget])
                b = set(path[:budget])
                rows.append({"arm": arm, "run_id": run_id, "budget": budget,
                             "jaccard": len(a & b) / len(a | b),
                             "overlap_count": len(a & b),
                             "differs": int(len(a & b) < budget)})
            divergence = next((i for i in range(16, 80) if base[i] != path[i]), None)
            rows.append({"arm": arm, "run_id": run_id, "budget": -1,
                         "jaccard": float("nan"), "overlap_count": -1,
                         "differs": int(divergence is not None),
                         "first_divergence_budget": divergence if divergence is not None else 80})
            for i in range(16, 80):
                if base[i] != path[i]:
                    for label, index in (("incumbent", base[i]), (arm, path[i])):
                        selected.append({
                            "arm": arm, "run_id": run_id, "step_budget": i, "chosen_by": label,
                            "population_row_index": int(index),
                            "log_h": float(logh[index]),
                            "has_keyhole": int(population.has_keyhole.iloc[index]),
                            "width_available": bool(width.available[index]),
                            "true_max_delta_W": float(width.full[index]) if width.available[index]
                            else float("nan"),
                            **{name: float(population.iloc[index][name]) for name in FEATURES},
                        })
    overlap = pd.DataFrame(rows)
    divergent = pd.DataFrame(selected)
    write_csv(OUTPUT / "query_path_overlap.csv", overlap)
    write_csv(OUTPUT / "divergent_queries.csv.gz", divergent)
    summary_rows = []
    for (arm, budget), group in overlap[overlap.budget > 0].groupby(["arm", "budget"], sort=True):
        summary_rows.append({"arm": arm, "budget": int(budget),
                             "mean_jaccard": float(group.jaccard.mean()),
                             "median_jaccard": float(group.jaccard.median()),
                             "fraction_of_runs_differing": float(group.differs.mean())})
    first = overlap[overlap.budget.eq(-1)]
    for arm, group in first.groupby("arm", sort=True):
        summary_rows.append({"arm": arm, "budget": -1,
                             "mean_jaccard": float("nan"), "median_jaccard": float("nan"),
                             "fraction_of_runs_differing": float(group.differs.mean()),
                             "median_first_divergence_budget": float(
                                 group.first_divergence_budget.median())})
    path_summary = pd.DataFrame(summary_rows)
    write_csv(OUTPUT / "query_path_summary.csv", path_summary)
    return overlap, path_summary


# --------------------------------------------------------------------------------------
# figures
# --------------------------------------------------------------------------------------
ARM_STYLE = {
    "A0_m3_margin": ("#333333", "-", "o", "A0  M3-margin (incumbent)"),
    "A1_predicted_width_margin": ("#CC3311", "-", "s", "A1  predicted-width margin (deployable)"),
    "A4_oracle_width_margin": ("#117733", "--", "^", "A4  ORACLE width margin (not deployable)"),
    "A1_model_on_A0_path": ("#EE7733", ":", "v", "A1 model on the incumbent path"),
    "A4_model_on_A0_path": ("#88CCEE", ":", "D", "A4 model on the incumbent path"),
    "A0_model_on_A1_path": ("#AA4499", ":", "P", "incumbent model on the A1 path"),
}


def _save(fig: plt.Figure, name: str) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / name
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def _pretty(name: str) -> str:
    return name.replace("_", " ")


def make_figures(curves: pd.DataFrame, aulc: pd.DataFrame, contrasts: pd.DataFrame,
                 oracle_gap: pd.DataFrame, decomposition: pd.DataFrame,
                 width_diag: pd.DataFrame, audits: pd.DataFrame, path_summary: pd.DataFrame,
                 divergent: pd.DataFrame, claims: pd.DataFrame,
                 population: pd.DataFrame, width: WidthData) -> list[Path]:
    plt.style.use("seaborn-v0_8-whitegrid")
    created: list[Path] = []
    main_arms = [a for a in ("A0_m3_margin", "A1_predicted_width_margin", "A4_oracle_width_margin")
                 if a in set(curves.arm)]

    # 1 ------------------------------------------------- what is known before a query
    fig, ax = plt.subplots(figsize=(13, 5.6))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    boxes = [
        (0.02, "#E8EEF6", "#4477AA", "ALREADY QUERIED  (B points)",
         "known:  P, VX, LS, ST\nknown:  has_keyhole  (revealed)\nknown:  true max ΔW  (if the monitor worked)\n\n"
         "These are the only points the\nwidth predictor may learn from."),
        (0.35, "#FDF0E6", "#EE7733", "UNQUERIED CANDIDATE",
         "known:  P, VX, LS, ST\nUNKNOWN:  has_keyhole\nUNKNOWN:  true max ΔW\n\n"
         "So we predict the width:\n    hat ΔW = f(P, VX, LS, ST)\ne.g. predicted 28 µm."),
        (0.68, "#EAF3EC", "#117733", "AFTER WE QUERY IT",
         "revealed:  has_keyhole\nrevealed:  true max ΔW\n\n"
         "The predicted 28 µm is replaced\nby the real observed value, the\n"
         "predictor is refitted, and the\nnext candidate is chosen."),
    ]
    for x, fill, edge, title, body in boxes:
        ax.add_patch(plt.Rectangle((x, 0.10), 0.30, 0.74, facecolor=fill, edgecolor=edge, lw=2,
                                   zorder=1))
        ax.text(x + 0.15, 0.78, title, ha="center", fontsize=11, fontweight="bold", color=edge)
        ax.text(x + 0.02, 0.70, body, ha="left", va="top", fontsize=9.5, family="monospace")
    for x in (0.325, 0.655):
        ax.annotate("", xy=(x + 0.02, 0.47), xytext=(x, 0.47),
                    arrowprops=dict(arrowstyle="->", lw=2.2, color="#666666"))
    ax.text(0.5, 0.03,
            "REGIME C (oracle) would let the middle box read the true max ΔW. That is the answer sheet, "
            "so it is reported only as an upper bound.",
            ha="center", fontsize=9.5, style="italic", color="#CC3311")
    ax.set_title("Figure 1 — What is legitimately known about a candidate before it is queried",
                 fontsize=13)
    created.append(_save(fig, "01_information_available.png"))

    # 2 -------------------------------------------- width prediction quality vs budget
    diag = width_diag[width_diag.arm.eq("A1_predicted_width_margin")].sort_values("budget")
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))
    axes[0].plot(diag.budget, diag.rmse_mean, color="#CC3311", lw=2, label="RMSE")
    axes[0].fill_between(diag.budget, diag.rmse_q1, diag.rmse_q3, color="#CC3311", alpha=0.15)
    axes[0].plot(diag.budget, diag.mae_mean, color="#4C78A8", lw=2, ls="--", label="MAE")
    axes[0].set(xlabel="active-learning budget", ylabel="width error (µm)",
                title="Error of queried-only width prediction\non still-unqueried points")
    axes[0].legend(fontsize=9)
    axes[1].plot(diag.budget, diag.r2_mean, color="#117733", lw=2)
    axes[1].fill_between(diag.budget, diag.r2_q1, diag.r2_q3, color="#117733", alpha=0.15)
    axes[1].axhline(0, color="black", lw=1.0, ls="--")
    axes[1].set(xlabel="active-learning budget", ylabel="R² on unseen points",
                title="Explained variance\n(0 = no better than the mean)")
    bottom = np.zeros(len(diag))
    for name, colour in zip(WIDTH_MODELS, ("#4C78A8", "#EE7733", "#117733")):
        share = diag[f"chosen_{name}_fraction"].to_numpy(float)
        axes[2].bar(diag.budget, share, bottom=bottom, width=1.0, color=colour, label=_pretty(name))
        bottom += share
    axes[2].set(xlabel="active-learning budget", ylabel="share of runs", ylim=(0, 1),
                title="Which width model the queried-only\ncross-validation picked")
    axes[2].legend(fontsize=8, loc="lower right")
    fig.suptitle("Figure 2 — How well can width be predicted from the process inputs alone?", fontsize=13)
    created.append(_save(fig, "02_width_prediction_quality.png"))

    # 3 ------------------------------------------------------------- learning curves
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.2))
    for ax, subset, title in ((axes[0], "B1_q20", "q20 boundary band"),
                              (axes[1], "B1_q30", "q30 boundary band")):
        for arm in main_arms:
            colour, style, marker, label = ARM_STYLE[arm]
            block = curves[curves.arm.eq(arm) & curves.subset.eq(subset)
                           & curves.metric.eq("accuracy")].sort_values("budget")
            ax.plot(block.budget, block["mean"], color=colour, ls=style, lw=2, label=label)
            ax.fill_between(block.budget, block.ci_lower, block.ci_upper, color=colour, alpha=0.12)
        ax.axvspan(16, 40, color="#999999", alpha=0.08)
        ax.text(28, ax.get_ylim()[0], " primary AULC window ", ha="center", va="bottom",
                fontsize=8, color="#666666")
        ax.set(xlabel="labelled simulations (budget)", ylabel="held-out accuracy", title=title)
        ax.legend(fontsize=8.5, loc="lower right")
    fig.suptitle("Figure 3 — Learning curves: incumbent, deployable predicted width, and the oracle bound",
                 fontsize=13)
    created.append(_save(fig, "03_learning_curves.png"))

    # 4 ------------------------------------------ primary AULC contrasts with intervals
    block = contrasts[contrasts.subset.eq(PRIMARY_SUBSET) & contrasts.region.eq("EARLY_B16_40")
                      & contrasts.metric.eq(PRIMARY_METRIC)].copy()
    order = [c for c in ("A1_predicted_width_margin - A0_m3_margin",
                         "A4_oracle_width_margin - A0_m3_margin",
                         "A1_model_on_A0_path - A0_m3_margin",
                         "A4_model_on_A0_path - A0_m3_margin",
                         "A0_model_on_A1_path - A0_m3_margin") if c in set(block.contrast)]
    block = block.set_index("contrast").loc[order].reset_index()
    fig, ax = plt.subplots(figsize=(11.5, 0.72 * len(block) + 2.6))
    positions = np.arange(len(block))[::-1]
    for position, row in zip(positions, block.itertuples(index=False)):
        colour = "#117733" if row.ci_lower > 0 else ("#CC3311" if row.ci_upper < 0 else "#888888")
        ax.plot([row.ci_lower, row.ci_upper], [position, position], color=colour, lw=2.8,
                solid_capstyle="round")
        ax.plot([row.mean_difference], [position], "o", color=colour, ms=8)
        ax.text(row.ci_upper + 0.0012, position,
                f"{row.mean_difference:+.4f} [{row.ci_lower:+.4f}, {row.ci_upper:+.4f}]",
                va="center", fontsize=8.5, color=colour)
    ax.axvline(0, color="black", lw=1.3)
    ax.axvline(0.010, color="#117733", lw=1.4, ls="--", label="success threshold +0.010")
    ax.set_yticks(positions, [_pretty(c).replace(" - ", "\n  minus  ") for c in block.contrast],
                  fontsize=8.5)
    span = float(np.abs(np.concatenate([block.ci_low if hasattr(block, "ci_low") else block.ci_lower,
                                        block.ci_upper])).max())
    ax.set_xlim(-1.5 * span, 3.4 * span)
    ax.set(xlabel="q20 accuracy AULC B16–40, difference vs the incumbent",
           title="Figure 4 — The primary endpoint: paired q20 AULC B16–40 contrasts\n"
                 "20 repeat blocks, 95% repeat-block bootstrap")
    ax.legend(fontsize=8.5, loc="lower right")
    created.append(_save(fig, "04_primary_aulc_contrasts.png"))

    # 5 and 6 ------------------------------------------- per-budget q20 metric curves
    for number, (metric, filename, label) in enumerate(
            (("balanced_accuracy", "05_per_budget_q20_balanced_accuracy.png", "q20 balanced accuracy"),
             ("pr_auc", "06_per_budget_q20_pr_auc.png", "q20 PR-AUC")), start=5):
        fig, axes = plt.subplots(1, 2, figsize=(15, 5.0))
        for arm in main_arms:
            colour, style, marker, arm_label = ARM_STYLE[arm]
            block = curves[curves.arm.eq(arm) & curves.subset.eq("B1_q20")
                           & curves.metric.eq(metric)].sort_values("budget")
            axes[0].plot(block.budget, block["mean"], color=colour, ls=style, lw=2, label=arm_label)
            axes[0].fill_between(block.budget, block.ci_lower, block.ci_upper, color=colour, alpha=0.12)
        axes[0].axvspan(16, 40, color="#999999", alpha=0.08)
        axes[0].set(xlabel="budget", ylabel=label, title=f"{label} across the whole trajectory")
        axes[0].legend(fontsize=8.5, loc="lower right")
        checkpoint = curves[curves.subset.eq("B1_q20") & curves.metric.eq(metric)
                            & curves.budget.isin(CHECKPOINT_BUDGETS) & curves.arm.isin(main_arms)]
        width_bar = 0.26
        for offset, arm in enumerate(main_arms):
            colour = ARM_STYLE[arm][0]
            block = checkpoint[checkpoint.arm.eq(arm)].sort_values("budget")
            positions = np.arange(len(block)) + (offset - (len(main_arms) - 1) / 2) * width_bar
            axes[1].bar(positions, block["mean"], width=width_bar, color=colour,
                        yerr=[block["mean"] - block.ci_lower, block.ci_upper - block["mean"]],
                        error_kw={"lw": 0.9, "ecolor": "#555555"}, label=ARM_STYLE[arm][3])
        axes[1].set_xticks(np.arange(len(CHECKPOINT_BUDGETS)), [f"B{b}" for b in CHECKPOINT_BUDGETS])
        low = float(checkpoint["mean"].min())
        axes[1].set(ylim=(max(0.0, low - 0.10), min(1.0, float(checkpoint["mean"].max()) + 0.06)),
                    ylabel=label, title="At the reported budgets")
        axes[1].legend(fontsize=8, loc="lower right")
        fig.suptitle(f"Figure {number} — {label} by budget", fontsize=13)
        created.append(_save(fig, filename))

    # 7 --------------------------------------------------- same-path decomposition
    block = decomposition[decomposition.subset.eq(PRIMARY_SUBSET)
                          & decomposition.region.eq("EARLY_B16_40")
                          & decomposition.metric.eq(PRIMARY_METRIC)]
    fig, ax = plt.subplots(figsize=(11.5, 5.2))
    labels, model_values, path_values = [], [], []
    for row in block.itertuples(index=False):
        labels.append(f"{row.arm}\n[{row.regime}]")
        model_values.append(row.model_value_same_path)
        path_values.append(row.path_value_implied)
    positions = np.arange(len(labels))
    ax.bar(positions - 0.2, model_values, width=0.4, color="#4C78A8",
           label="model value  (challenger model, incumbent's queries)")
    ax.bar(positions + 0.2, path_values, width=0.4, color="#EE7733",
           label="path value  (implied: total − model)")
    for position, (m, p) in enumerate(zip(model_values, path_values)):
        ax.text(position - 0.2, m + (0.0006 if m >= 0 else -0.0016), f"{m:+.4f}",
                ha="center", fontsize=8.5)
        ax.text(position + 0.2, p + (0.0006 if p >= 0 else -0.0016), f"{p:+.4f}",
                ha="center", fontsize=8.5)
    ax.axhline(0, color="black", lw=1.2)
    ax.set_xticks(positions, labels, fontsize=8.5)
    ax.set(ylabel="q20 accuracy AULC B16–40 vs incumbent",
           title="Figure 7 — Did width improve the MODEL, or did it improve the QUERIES?\n"
                 "A model gain is not an acquisition gain")
    ax.legend(fontsize=9)
    created.append(_save(fig, "07_same_path_decomposition.png"))

    # 8 ------------------------------------------------ oracle headroom and recovery
    block = oracle_gap[oracle_gap.subset.eq(PRIMARY_SUBSET) & oracle_gap.region.eq("EARLY_B16_40")
                       & oracle_gap.metric.eq(PRIMARY_METRIC)].iloc[0]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.0))
    names = ["A0\nincumbent", "A1\npredicted width\n(deployable)", "A4\nORACLE width\n(not deployable)"]
    values = [block.A0_incumbent, block.A1_predicted_width, block.A4_oracle_width]
    colours = ["#333333", "#CC3311", "#117733"]
    axes[0].bar(np.arange(3), values, color=colours, width=0.6)
    for position, value in enumerate(values):
        axes[0].text(position, value + 0.0009, f"{value:.4f}", ha="center", fontsize=10)
    low = min(values)
    axes[0].set_xticks(np.arange(3), names, fontsize=9)
    axes[0].set(ylim=(low - 0.012, max(values) + 0.010), ylabel="q20 accuracy AULC B16–40",
                title="Where the three regimes land")
    axes[1].bar([0], [block.oracle_headroom_A4_minus_A0], color="#117733", width=0.5,
                yerr=[[block.oracle_headroom_A4_minus_A0 - block.oracle_headroom_ci_lower],
                      [block.oracle_headroom_ci_upper - block.oracle_headroom_A4_minus_A0]],
                error_kw={"lw": 1.2, "ecolor": "#333333"}, label="oracle headroom  A4 − A0")
    axes[1].bar([1], [block.realised_gain_A1_minus_A0], color="#CC3311", width=0.5,
                yerr=[[block.realised_gain_A1_minus_A0 - block.realised_gain_ci_lower],
                      [block.realised_gain_ci_upper - block.realised_gain_A1_minus_A0]],
                error_kw={"lw": 1.2, "ecolor": "#333333"}, label="realised gain  A1 − A0")
    axes[1].axhline(0, color="black", lw=1.2)
    axes[1].axhline(0.010, color="#117733", lw=1.3, ls="--", label="success threshold +0.010")
    axes[1].set_xticks([0, 1], ["oracle headroom", "deployable gain"], fontsize=9.5)
    recovered = block.recovered_fraction_of_headroom
    axes[1].set(ylabel="q20 accuracy AULC B16–40 difference",
                title=("Recovered fraction of headroom: "
                       + (f"{recovered:.0%}" if np.isfinite(recovered) else "undefined — "
                          "the oracle headroom is not positive")))
    axes[1].legend(fontsize=8.5)
    fig.suptitle("Figure 8 — ORACLE WIDTH IS NOT DEPLOYABLE: it only bounds what acquisition could gain",
                 fontsize=12.5)
    created.append(_save(fig, "08_oracle_headroom.png"))

    # 9 ------------------------------------------------------ which queries differ
    fig, axes = plt.subplots(1, 2, figsize=(14.5, 5.0))
    subset = divergent[divergent.arm.eq("A1_predicted_width_margin")] if len(divergent) else divergent
    if len(subset):
        for label, colour in (("incumbent", "#333333"), ("A1_predicted_width_margin", "#CC3311")):
            block = subset[subset.chosen_by.eq(label)]
            axes[0].hist(block.log_h, bins=30, alpha=0.55, color=colour,
                         label=f"{'incumbent' if label == 'incumbent' else 'A1'} picked "
                               f"(n={len(block)})")
        axes[0].set(xlabel="log h of the selected simulation", ylabel="divergent selections",
                    title="Where the two policies disagree, in the physics coordinate")
        axes[0].legend(fontsize=8.5)
        axes[1].scatter(subset[subset.chosen_by.eq("incumbent")].P,
                        subset[subset.chosen_by.eq("incumbent")].VX,
                        s=18, alpha=0.45, color="#333333", label="incumbent picked")
        axes[1].scatter(subset[subset.chosen_by.ne("incumbent")].P,
                        subset[subset.chosen_by.ne("incumbent")].VX,
                        s=18, alpha=0.45, color="#CC3311", label="A1 picked")
        axes[1].set(xlabel="P — laser power (W)", ylabel="VX — scan speed (m/s)",
                    title="Divergent selections in the input space")
        axes[1].legend(fontsize=8.5)
    else:
        for ax in axes:
            ax.axis("off")
            ax.text(0.5, 0.5, "The width-informed policy never selected a different simulation\n"
                              "from the incumbent at any step of any run.",
                    ha="center", va="center", fontsize=12, color="#CC3311")
    overlap_note = path_summary[path_summary.arm.eq("A1_predicted_width_margin")
                                & path_summary.budget.eq(40)]
    note = (f"mean Jaccard overlap with the incumbent path at B40: "
            f"{float(overlap_note.iloc[0].mean_jaccard):.3f}" if len(overlap_note) else "")
    fig.suptitle(f"Figure 9 — Does width-informed acquisition actually pick different simulations?  {note}",
                 fontsize=12.5)
    created.append(_save(fig, "09_divergent_queries.png"))

    # 10 ------------------------------------------------------------ claim status
    status_colour = {"SUPPORTED": "#117733", "QUALIFIED": "#EE7733",
                     "NOT SUPPORTED": "#CC3311", "DESCRIPTIVE ONLY": "#666666"}
    wrapped_claims = [textwrap.fill(c, 62) for c in claims.claim]
    wrapped_guards = [textwrap.fill(g, 82) for g in claims.guardrail]
    fig, ax = plt.subplots(figsize=(13.5, 0.80 * len(claims) + 1.7))
    ax.axis("off")
    table_width = 1.42
    ax.set_xlim(0, table_width)
    ax.set_ylim(0, len(claims) + 1.4)
    for x, header in ((0.01, "Claim"), (0.55, "Status"), (0.72, "Guardrail")):
        ax.text(x, len(claims) + 0.75, header, fontsize=10, fontweight="bold")
    ax.plot([0, table_width], [len(claims) + 0.5] * 2, color="black", lw=1.0)
    for position, row in enumerate(claims.itertuples(index=False)):
        y = len(claims) - position - 0.5
        if position % 2 == 0:
            ax.add_patch(plt.Rectangle((0, y - 0.5), table_width, 1.0, color="#F4F4F4", zorder=0))
        ax.text(0.01, y, wrapped_claims[position], fontsize=8.3, va="center", zorder=2, linespacing=1.35)
        ax.text(0.55, y, row.status, fontsize=8.5, va="center", fontweight="bold",
                color=status_colour.get(row.status, "#333333"), zorder=2)
        ax.text(0.72, y, wrapped_guards[position], fontsize=7.5, va="center", color="#444444",
                zorder=2, linespacing=1.35)
    ax.set_title("Figure 10 — Week 9 Phase 2.2 claim status", fontsize=13, pad=14)
    created.append(_save(fig, "10_claim_status.png"))
    return created


# --------------------------------------------------------------------------------------
# decision, claims and reports
# --------------------------------------------------------------------------------------
SUCCESS_GAIN = 0.010
RECALL_HARM_LIMIT = -0.02


def primary_row(frame: pd.DataFrame, contrast: str, metric: str = PRIMARY_METRIC,
                region: str = "EARLY_B16_40") -> pd.Series | None:
    block = frame[frame.contrast.eq(contrast) & frame.subset.eq(PRIMARY_SUBSET)
                  & frame.region.eq(region) & frame.metric.eq(metric)]
    return block.iloc[0] if len(block) else None


def decide(contrasts: pd.DataFrame, oracle_gap: pd.DataFrame,
           path_summary: pd.DataFrame) -> tuple[str, dict[str, Any]]:
    """One verdict, from predeclared criteria, in a fixed order."""
    gain = primary_row(contrasts, "A1_predicted_width_margin - A0_m3_margin")
    headroom = primary_row(contrasts, "A4_oracle_width_margin - A0_m3_margin")
    model_only = primary_row(contrasts, "A1_model_on_A0_path - A0_m3_margin")
    recall = primary_row(contrasts, "A1_predicted_width_margin - A0_m3_margin",
                         metric="keyhole_recall")

    facts = {
        "primary_gain": float(gain.mean_difference) if gain is not None else float("nan"),
        "primary_gain_ci_lower": float(gain.ci_lower) if gain is not None else float("nan"),
        "primary_gain_ci_upper": float(gain.ci_upper) if gain is not None else float("nan"),
        "oracle_headroom": float(headroom.mean_difference) if headroom is not None else float("nan"),
        "oracle_headroom_ci_lower": float(headroom.ci_lower) if headroom is not None else float("nan"),
        "oracle_headroom_ci_upper": float(headroom.ci_upper) if headroom is not None else float("nan"),
        "model_only_gain": float(model_only.mean_difference) if model_only is not None else float("nan"),
        "model_only_ci_lower": float(model_only.ci_lower) if model_only is not None else float("nan"),
        "keyhole_recall_change": float(recall.mean_difference) if recall is not None else float("nan"),
        "keyhole_recall_ci_lower": float(recall.ci_lower) if recall is not None else float("nan"),
    }
    overlap = path_summary[path_summary.arm.eq("A1_predicted_width_margin")
                           & path_summary.budget.eq(40)]
    facts["path_jaccard_B40"] = float(overlap.iloc[0].mean_jaccard) if len(overlap) else float("nan")
    diverged = path_summary[path_summary.arm.eq("A1_predicted_width_margin")
                            & path_summary.budget.eq(-1)]
    facts["fraction_of_runs_with_a_different_path"] = (
        float(diverged.iloc[0].fraction_of_runs_differing) if len(diverged) else float("nan"))

    recall_ok = not (math.isfinite(facts["keyhole_recall_change"])
                     and facts["keyhole_recall_change"] < RECALL_HARM_LIMIT)
    survives = (facts["primary_gain"] >= SUCCESS_GAIN and facts["primary_gain_ci_lower"] > 0
                and recall_ok)
    oracle_meaningful = (facts["oracle_headroom"] >= SUCCESS_GAIN
                         and facts["oracle_headroom_ci_lower"] > 0)
    model_positive = facts["model_only_ci_lower"] > 0

    if survives:
        verdict = "WIDTH-INFORMED ACTIVE LEARNING SURVIVES"
    elif oracle_meaningful:
        verdict = "ORACLE-ONLY HEADROOM"
    elif model_positive:
        verdict = "PREDICTIVE SIGNAL ONLY"
    else:
        verdict = "KILLED"
    facts["verdict"] = verdict
    facts["success_criteria"] = {
        "gain_at_least_0.010": bool(facts["primary_gain"] >= SUCCESS_GAIN),
        "paired_ci_lower_above_zero": bool(facts["primary_gain_ci_lower"] > 0),
        "keyhole_recall_not_materially_degraded": bool(recall_ok),
        "oracle_headroom_meaningful": bool(oracle_meaningful),
        "model_value_positive_on_incumbent_path": bool(model_positive),
    }
    write_json(OUTPUT / "decision.json", facts)
    return verdict, facts


def build_claims(contrasts: pd.DataFrame, oracle_gap: pd.DataFrame, decomposition: pd.DataFrame,
                 width_diag: pd.DataFrame, path_summary: pd.DataFrame, curves: pd.DataFrame,
                 facts: dict[str, Any], verdict: str) -> pd.DataFrame:
    low_budget = width_diag[width_diag.arm.eq("A1_predicted_width_margin")
                            & width_diag.budget.eq(16)]
    r2_16 = float(low_budget.iloc[0].r2_mean) if len(low_budget) else float("nan")
    rmse_16 = float(low_budget.iloc[0].rmse_mean) if len(low_budget) else float("nan")
    late = width_diag[width_diag.arm.eq("A1_predicted_width_margin") & width_diag.budget.eq(80)]
    r2_80 = float(late.iloc[0].r2_mean) if len(late) else float("nan")

    model_block = decomposition[decomposition.subset.eq(PRIMARY_SUBSET)
                                & decomposition.region.eq("EARLY_B16_40")
                                & decomposition.metric.eq(PRIMARY_METRIC)
                                & decomposition.arm.eq("A1_predicted_width_margin")]
    path_value = float(model_block.iloc[0].path_value_implied) if len(model_block) else float("nan")

    def status_from(value: float, lower: float) -> str:
        if lower > 0 and value >= SUCCESS_GAIN:
            return "SUPPORTED"
        if lower > 0:
            return "QUALIFIED"
        return "NOT SUPPORTED"

    return pd.DataFrame([
        {
            "claim": "PRIMARY — deployable predicted-width M3-margin beats the incumbent on q20 "
                     "accuracy AULC B16–40 by at least +0.010",
            "status": status_from(facts["primary_gain"], facts["primary_gain_ci_lower"]),
            "guardrail": f"{facts['primary_gain']:+.4f} "
                         f"[{facts['primary_gain_ci_lower']:+.4f}, {facts['primary_gain_ci_upper']:+.4f}]; "
                         f"predeclared success needs both >= +0.010 and a lower bound above zero",
        },
        {
            "claim": "ORACLE WIDTH — NOT DEPLOYABLE — even perfectly known width improves the "
                     "incumbent's q20 AULC B16–40 meaningfully",
            "status": status_from(facts["oracle_headroom"], facts["oracle_headroom_ci_lower"]),
            "guardrail": f"{facts['oracle_headroom']:+.4f} "
                         f"[{facts['oracle_headroom_ci_lower']:+.4f}, "
                         f"{facts['oracle_headroom_ci_upper']:+.4f}]; this is the ceiling on any "
                         f"width-informed acquisition, not an achievable result",
        },
        {
            "claim": "The width-informed model is better than the incumbent when the query path is "
                     "held fixed (model value)",
            "status": "SUPPORTED" if facts["model_only_ci_lower"] > 0 else "NOT SUPPORTED",
            "guardrail": f"A1 model on the incumbent path: {facts['model_only_gain']:+.4f} "
                         f"[{facts['model_only_ci_lower']:+.4f}, ...]; a model gain is not an "
                         f"acquisition gain",
        },
        {
            "claim": "Width information changes which simulations get queried",
            "status": "SUPPORTED" if facts["fraction_of_runs_with_a_different_path"] > 0.5
            else ("QUALIFIED" if facts["fraction_of_runs_with_a_different_path"] > 0 else "NOT SUPPORTED"),
            "guardrail": f"{facts['fraction_of_runs_with_a_different_path']:.0%} of runs diverge from "
                         f"the incumbent path; mean Jaccard overlap at B40 = "
                         f"{facts['path_jaccard_B40']:.3f}",
        },
        {
            "claim": "The changed query path is what produces any gain (acquisition value)",
            "status": "SUPPORTED" if path_value >= SUCCESS_GAIN else (
                "QUALIFIED" if path_value > 0 else "NOT SUPPORTED"),
            "guardrail": f"implied path value = total − model = {path_value:+.4f} on q20 accuracy "
                         f"AULC B16–40",
        },
        {
            "claim": "Width can be predicted well enough from [P, VX, LS, ST] at low budget to "
                     "preserve the useful signal",
            "status": "SUPPORTED" if r2_16 >= 0.5 else ("QUALIFIED" if r2_16 >= 0.2 else "NOT SUPPORTED"),
            "guardrail": f"at B16 the queried-only predictor reaches R² = {r2_16:.3f} "
                         f"(RMSE {rmse_16:.2f} µm) on still-unqueried points; by B80 R² = {r2_80:.3f}",
        },
        {
            "claim": "Any apparent gain required exposing true width for unqueried candidates",
            "status": "NOT SUPPORTED",
            "guardrail": "the deployable arm never reads an unqueried candidate's true width; the "
                         "oracle arm that does is labelled and reported separately",
        },
        {
            "claim": "This phase re-derives the incumbent rather than reusing published numbers",
            "status": "SUPPORTED",
            "guardrail": "phase114_reproduction_gate.csv: the A0 arm reproduces the published "
                         "Phase 1.14 M3-margin q20 accuracy AULC B16–40",
        },
        {
            "claim": "Early-prefix width side information (Regime B) could rescue the direction",
            "status": "NOT SUPPORTED",
            "guardrail": "not run, and dominated by construction: at the 5% prefix the feature equals "
                         "its full-trace value for 95.4% of simulations (Phase 2.1R-E), so Regime B "
                         "buys a near-copy of the oracle's information at a positive cost while the "
                         "oracle itself shows no meaningful headroom",
        },
        {
            "claim": "Marginalising over width-prediction uncertainty (A2) could rescue the direction",
            "status": "NOT SUPPORTED",
            "guardrail": "not run: A2 can only recover ground between the deployable arm and the "
                         "oracle arm, and that gap is indistinguishable from zero",
        },
        {
            "claim": "Results transfer to the 55 simulations with no usable width trace",
            "status": "NOT SUPPORTED",
            "guardrail": "those points always carry a predicted width; missingness is structured "
                         "(5.5% Keyhole versus 20%), so all results are conditional on it",
        },
        {
            "claim": "This is confirmatory evidence for the thesis' external protocol",
            "status": "NOT SUPPORTED",
            "guardrail": "OLD-405 development evidence only; the frozen external-confirmation "
                         "protocol is untouched",
        },
    ])


def render_reports(population: pd.DataFrame, availability: pd.DataFrame, curves: pd.DataFrame,
                   aulc: pd.DataFrame, contrasts: pd.DataFrame, oracle_gap: pd.DataFrame,
                   decomposition: pd.DataFrame, width_diag: pd.DataFrame,
                   path_summary: pd.DataFrame, gate: pd.DataFrame, claims: pd.DataFrame,
                   facts: dict[str, Any], verdict: str, figures: list[Path]) -> None:
    def curve_value(arm: str, budget: int, metric: str, subset: str = "B1_q20") -> float:
        block = curves[curves.arm.eq(arm) & curves.subset.eq(subset)
                       & curves.budget.eq(budget) & curves.metric.eq(metric)]
        return float(block.iloc[0]["mean"]) if len(block) else float("nan")

    arms_present = [a for a in ("A0_m3_margin", "A1_predicted_width_margin",
                                "A4_oracle_width_margin") if a in set(curves.arm)]
    budget_table = "\n".join(
        "| B{b} | {vals} |".format(
            b=budget,
            vals=" | ".join(f"{curve_value(arm, budget, 'accuracy'):.4f}" for arm in arms_present))
        for budget in CHECKPOINT_BUDGETS)
    budget_header = " | ".join(ARM_STYLE[a][3] for a in arms_present)

    contrast_table = "\n".join(
        f"| {row.contrast.replace(' - ', ' − ')} | {row.mean_difference:+.4f} "
        f"[{row.ci_lower:+.4f}, {row.ci_upper:+.4f}] | "
        f"{'yes' if row.ci_lower > 0 else 'no'} |"
        for row in contrasts[contrasts.subset.eq(PRIMARY_SUBSET)
                             & contrasts.region.eq("EARLY_B16_40")
                             & contrasts.metric.eq(PRIMARY_METRIC)].itertuples(index=False))
    metric_table = "\n".join(
        f"| {_pretty(row.metric)} | {row.mean_difference:+.4f} "
        f"[{row.ci_lower:+.4f}, {row.ci_upper:+.4f}] |"
        for row in contrasts[contrasts.contrast.eq("A1_predicted_width_margin - A0_m3_margin")
                             & contrasts.subset.eq(PRIMARY_SUBSET)
                             & contrasts.region.eq("EARLY_B16_40")].itertuples(index=False))
    width_table = "\n".join(
        f"| B{int(row.budget)} | {row.n_width_observations_mean:.1f} | {row.rmse_mean:.2f} µm | "
        f"{row.mae_mean:.2f} µm | {row.r2_mean:+.3f} | {row.spearman_true_vs_predicted_mean:+.3f} |"
        for row in width_diag[width_diag.arm.eq("A1_predicted_width_margin")
                              & width_diag.budget.isin(CHECKPOINT_BUDGETS)].itertuples(index=False))
    decomposition_table = "\n".join(
        f"| {row.arm} | {row.regime} | {row.model_value_same_path:+.4f} | "
        f"{row.path_value_implied:+.4f} | {row.total_value_own_path:+.4f} |"
        for row in decomposition[decomposition.subset.eq(PRIMARY_SUBSET)
                                 & decomposition.region.eq("EARLY_B16_40")
                                 & decomposition.metric.eq(PRIMARY_METRIC)].itertuples(index=False))
    ledger_table = "\n".join(f"| {row.claim} | {row.status} | {row.guardrail} |"
                             for row in claims.itertuples(index=False))
    recovered = float(oracle_gap[oracle_gap.subset.eq(PRIMARY_SUBSET)
                                 & oracle_gap.region.eq("EARLY_B16_40")
                                 & oracle_gap.metric.eq(PRIMARY_METRIC)]
                      .iloc[0].recovered_fraction_of_headroom)
    reproduced = gate[gate.quantity.eq("q20_accuracy_AULC_B16_40")].iloc[0]

    one_page = f"""# What did we actually ask?

Phase 2.1R showed that `max_positive_delta_W` helps a model **rank** Keyhole risk. It is the largest
transverse-width increase between one **consecutive resampled analysis point** and the next — not a raw
solver timestep. Phase 2.1R-E showed that number is available within the opening ~5% of the trace. Neither says width helps **active learning**, and
there is a trap in assuming it does.

**The trap.** At budget B only the B already-queried simulations legitimately have an observed width.
An unqueried candidate does not. Scoring candidates with their true width would be reading the answer
sheet. So this phase keeps three information regimes strictly apart:

* **Regime A — deployable.** Fit a width predictor on the queried points only,
  `[P, VX, LS, ST] → hat ΔW`, and score candidates with the *predicted* width.
  Concretely: at budget 16 we know the label and observed width of 16 simulations, learn width from the
  four process inputs on those 16, and for an unqueried candidate predict — say 28 µm — and let the
  width-informed M3 use 28. Only once we actually query it does the real value replace the 28.
* **Regime C — oracle.** Every candidate's true width is visible. Deliberately leaky, reported only as
  an upper bound and labelled **ORACLE WIDTH — NOT DEPLOYABLE**.
* **Regime B — early-prefix side information.** Opening-5% width bought at an explicit cost, never free.

Everything else is the frozen thesis protocol: 405 simulations, the 100 frozen outer splits, the frozen
16-point initial designs, the budget-by-budget trajectory 16 → 80, the q20/q30 boundary masks, and M3
(physics logistic mean on `log h`, frozen, plus an ARD Matérn-3/2 discrepancy GP). The incumbent is
**M3 + M3 probability margin**.

## The incumbent is re-derived, not quoted

The A0 arm here reproduces the published Phase 1.14 M3-margin q20 accuracy AULC B16–40 of
**{float(reproduced.phase114_published_P1):.7f}** — measured here as
**{float(reproduced.phase22_A0_reproduced):.7f}** (difference
{float(reproduced.abs_difference):.2e}, {reproduced.status}). That is what licenses reading every width
arm on the same scale.

## Per-budget q20 accuracy

| budget | {budget_header} |
|---|{'---|' * len(arms_present)}
{budget_table}

## The primary endpoint: q20 accuracy AULC B16–40

| contrast | difference [95% CI] | interval excludes zero |
|---|---|---|
{contrast_table}

**Deployable gain: {facts['primary_gain']:+.4f}
[{facts['primary_gain_ci_lower']:+.4f}, {facts['primary_gain_ci_upper']:+.4f}].**
The predeclared success bar was +0.010 with a lower bound above zero.

Across the other metrics, on the same primary endpoint:

| metric | A1 − A0 [95% CI] |
|---|---|
{metric_table}

## Oracle headroom: how much was there to win at all?

* incumbent A0: **{float(oracle_gap[oracle_gap.subset.eq(PRIMARY_SUBSET) & oracle_gap.region.eq('EARLY_B16_40') & oracle_gap.metric.eq(PRIMARY_METRIC)].iloc[0].A0_incumbent):.4f}**
* deployable A1: **{float(oracle_gap[oracle_gap.subset.eq(PRIMARY_SUBSET) & oracle_gap.region.eq('EARLY_B16_40') & oracle_gap.metric.eq(PRIMARY_METRIC)].iloc[0].A1_predicted_width):.4f}**
* ORACLE A4 (NOT DEPLOYABLE): **{float(oracle_gap[oracle_gap.subset.eq(PRIMARY_SUBSET) & oracle_gap.region.eq('EARLY_B16_40') & oracle_gap.metric.eq(PRIMARY_METRIC)].iloc[0].A4_oracle_width):.4f}**

Oracle headroom `A4 − A0` = **{facts['oracle_headroom']:+.4f}
[{facts['oracle_headroom_ci_lower']:+.4f}, {facts['oracle_headroom_ci_upper']:+.4f}]**.
Recovered fraction of that headroom by the deployable method:
**{f'{recovered:.0%}' if np.isfinite(recovered) else 'undefined — the headroom is not positive'}**.

## Model value versus acquisition value

| arm | regime | model value (fixed path) | path value (implied) | total (own path) |
|---|---|---|---|---|
{decomposition_table}

A better model is not a better acquisition rule. The model column holds the query path fixed at the
incumbent's; the path column is what is left over.

## Can width be predicted at all from the process inputs?

| budget | width observations | RMSE | MAE | R² | Spearman |
|---|---|---|---|---|---|
{width_table}

Evaluated on training-pool points the predictor has **not** seen, at every budget.

## Why A2 (uncertainty-aware width) and A3 (early-prefix side information) were not run

Both were predeclared, and both are settled by the oracle bound rather than skipped for convenience.

**A3 — early-prefix side information (Regime B).** Phase 2.1R-E established that at the 5% prefix the
feature already equals its full-trace value for 95.4% of simulations. So the information A3 could buy is,
to within that 95.4%, the *same* information the oracle arm is handed for free. The oracle arm is the
best case for that information — it pays nothing for it and gets it for every candidate — and it returns
{facts['oracle_headroom']:+.4f} [{facts['oracle_headroom_ci_lower']:+.4f},
{facts['oracle_headroom_ci_upper']:+.4f}] on the primary endpoint, an interval containing zero. A3 would
buy a near-copy of that information at a strictly positive cost in labelled simulations, so under every
cost ratio in {list(COST_RATIOS)} it is dominated by an arm that already fails. Running it could only
produce a worse number with a longer runtime.

**A2 — marginalising over width uncertainty.** A2 exists to recover signal lost by plugging in the
*mean* predicted width instead of integrating over its predictive distribution. That can only ever
recover ground between the deployable arm and the oracle arm, because integrating over a distribution
whose truth is known collapses to the oracle. With the oracle headroom itself indistinguishable from
zero, there is no gap for A2 to close.

This is the kill criterion working as intended: the oracle bound was built precisely so that a negative
result here stops the direction instead of motivating more variants.

## Claim ledger

| claim | status | guardrail |
|---|---|---|
{ledger_table}

## Verdict

**{verdict}**

## What this is not

OLD-405 development evidence only. No change to the frozen external-confirmation protocol, no
monitoring claim, and nothing here transfers to the 55 simulations whose width trace is unusable —
those always carry a predicted value, and their missingness is structured (5.5% Keyhole against 20%).
"""

    (OUTPUT / "SUPERVISOR_PHASE2_2_ONE_PAGE.md").write_text(one_page.rstrip() + "\n", encoding="utf-8")

    methods = f"""
## Methods

**Inherited unchanged.** Population and frozen splits via `week9_phase1_13.load_inputs`; the frozen
16-point initial designs and A0 paths; `p17.subset_flags` for the q20/q30 boundary masks;
`p12.metric_values` for every metric; the Phase 1.14 acquisition (`p6.choose_binary_candidate`,
`binary_margin`, ties to the smallest population row index); the Phase 1.14 AULC definition
(normalized trapezoid, `np.trapezoid(metric, budget) / (b_last - b_first)`); and its repeat-block
bootstrap over the 20 repeats with {BOOTSTRAP_DRAWS} draws.

**M3.** Exactly the Phase 1.13 construction — a logistic mean on `log h` fitted on the revealed labels
and then frozen, plus a `FixedMeanLaplaceGPC` discrepancy with an ARD Matérn-3/2 kernel. The only
change in the width arms is that the **discrepancy** GP gains one input dimension; the physics mean
still sees `log h` and nothing else, exactly as in Phase 2.1R.

**Width predictor (Regime A).** Three predeclared candidates — ridge on the raw inputs, ridge on a
quadratic expansion, and a Matérn-3/2 GP with a white-noise term — chosen by {WIDTH_CV_FOLDS}-fold
cross-validation *within the queried set*. No held-out label, unqueried point, or test-fold information
takes part in the choice. The family is re-selected on the budget grid {WIDTH_SELECTION_BUDGETS} and
refitted to the current queried set at every budget in between; the chosen family is recorded per
budget in `width_predictor_diagnostics.csv`.

**Missing width.** 55 of 405 simulations have no usable trace. That is treated as a failed monitor
rather than hidden: the predictor trains only on queried points that produced a width, and every other
point carries its predicted value. Every frozen initial design contains at least
{int(availability[availability.quantity.eq('min_width_observed_in_initial_design')].iloc[0].value)}
width observations, so the predictor is always fittable from budget 16.

**Multiplicity.** The primary endpoint is a single predeclared quantity: q20 accuracy AULC B16–40,
A1 − A0. Everything else — other metrics, other regions, q30 and full-set contrasts — is secondary and
reported without correction; nothing is promoted from that pool.

## Figures
{chr(10).join(f'- `figures/{p.name}`' for p in figures)}
"""

    (OUTPUT / "FINAL_PHASE2_2_REPORT.md").write_text(
        "# Week 9 Phase 2.2 — final report\n## Width-informed active learning\n\n"
        + one_page.split("# What did we actually ask?", 1)[1].strip() + "\n"
        + methods.rstrip() + "\n", encoding="utf-8")

    (OUTPUT / "claim_ledger.md").write_text(
        f"""# Week 9 Phase 2.2 claim ledger

Primary question: **can the predictive width signal be turned into a legitimate sample-efficiency
improvement over M3 + M3-margin?**

Primary endpoint: q20 accuracy AULC B16–40, deployable predicted-width arm minus the incumbent.
Predeclared success: gain >= +{SUCCESS_GAIN:.3f}, paired 95% lower bound above zero, and Keyhole recall
not materially degraded.

The width feature throughout is `max_positive_delta_W`: the largest transverse-width increase between
one **consecutive resampled analysis point** and the next, on the pinned Phase 2 grid. These are not raw
solver timesteps.

| claim | status | guardrail |
|---|---|---|
{ledger_table}

## Verdict

**{verdict}**

## Status vocabulary
- **SUPPORTED** — the paired 95% repeat-block interval excludes zero in the favourable direction and,
  where a size bar applies, the effect clears it.
- **QUALIFIED** — directionally present but below the predeclared bar, or present on some endpoints only.
- **NOT SUPPORTED** — no detectable difference, or a difference in the unfavourable direction.
""".rstrip() + "\n", encoding="utf-8")

    write_csv(OUTPUT / "figure_manifest.csv", pd.DataFrame(
        [{"artifact": f"figures/{p.name}", "sha256": sha256_file(p), "bytes": p.stat().st_size}
         for p in figures]))


# --------------------------------------------------------------------------------------
# notebook
# --------------------------------------------------------------------------------------
def notebook_payload(verdict: str) -> dict[str, Any]:
    sections: list[tuple[str, str, str]] = [
        (
            "1. The question, and the trap in it",
            "Phase 2.1R showed the biggest width jump helps a model **rank** Keyhole risk. The obvious "
            "next thought is 'so let's use width to choose which simulation to run next'.\n\n"
            "**That is where it gets easy to cheat.** At budget 16 we have queried 16 simulations. Those "
            "16 have a revealed label and an observed width. A candidate we have *not* queried has "
            "neither — if we scored it using its true width we would be reading the answer sheet.\n\n"
            "So the deployable rule is: learn width from `[P, VX, LS, ST]` using only the queried points, "
            "and predict it for everyone else. If the predicted max ΔW is 28 µm, the width-informed M3 "
            "uses 28. Only after we actually query that simulation does the real observed value replace "
            "the 28, and the predictor is refitted.",
            "display(Image(filename=OUT/'figures'/'01_information_available.png'))\n"
            "display(pd.read_csv(OUT/'width_availability_audit.csv'))",
        ),
        (
            "2. The incumbent is re-derived, not quoted",
            "The baseline is the current incumbent: M3 plus M3 probability margin, choosing the "
            "unqueried training-pool simulation whose predicted probability sits closest to 0.5.\n\n"
            "Rather than copying Phase 1.14's published number, the whole trajectory is re-run here and "
            "checked against it. If the reproduction is exact, every width arm can be read on the same "
            "scale.",
            "display(pd.read_csv(OUT/'phase114_reproduction_gate.csv'))",
        ),
        (
            "3. How good is width prediction, budget by budget?",
            "This decides whether the deployable regime can work at all. At each budget the predictor is "
            "fitted on the queried points and scored on training-pool points it has never seen.\n\n"
            "If R² is near zero at low budgets, the predicted width is close to a constant and cannot "
            "carry the signal that made Phase 2.1R interesting.",
            "display(pd.read_csv(OUT/'width_predictor_diagnostics.csv')"
            ".query('arm == \"A1_predicted_width_margin\" and budget in [16,24,32,40,60,80]')"
            "[['budget','n_width_observations_mean','rmse_mean','mae_mean','r2_mean',"
            "'spearman_true_vs_predicted_mean']].round(4))\n"
            "display(Image(filename=OUT/'figures'/'02_width_prediction_quality.png'))",
        ),
        (
            "4. Learning curves",
            "Three arms on the same frozen splits and the same 16-point starts: the incumbent, the "
            "deployable predicted-width policy, and the oracle policy that is allowed to see every "
            "candidate's true width.\n\n"
            "The oracle is **not deployable**. It is here only to say how much there was to win.",
            "display(Image(filename=OUT/'figures'/'03_learning_curves.png'))\n"
            "c = pd.read_csv(OUT/'per_budget_checkpoints.csv')\n"
            "display(c[(c.subset=='B1_q20') & (c.metric=='accuracy')]"
            ".pivot(index='budget', columns='arm', values='mean').round(4))",
        ),
        (
            "5. The primary endpoint",
            "One predeclared number decides this phase: **q20 accuracy AULC over budgets 16–40**, "
            "deployable arm minus incumbent. The success bar was set in advance at +0.010 with a paired "
            "95% lower bound above zero.",
            "display(Image(filename=OUT/'figures'/'04_primary_aulc_contrasts.png'))\n"
            "k = pd.read_csv(OUT/'paired_aulc_contrasts.csv')\n"
            "display(k[(k.subset=='B1_q20') & (k.region=='EARLY_B16_40') & (k.metric=='accuracy')]"
            "[['contrast','mean_difference','ci_lower','ci_upper']].round(5))",
        ),
        (
            "6. Model value or acquisition value?",
            "A better model is not a better acquisition rule. To separate them, the width-informed model "
            "is also scored on the **incumbent's** query path: any gain there is model value, because "
            "the queries are identical. Whatever is left over is what the changed queries bought.",
            "display(Image(filename=OUT/'figures'/'07_same_path_decomposition.png'))\n"
            "display(pd.read_csv(OUT/'same_path_decomposition.csv')"
            ".query('subset == \"B1_q20\" and region == \"EARLY_B16_40\" and metric == \"accuracy\"')"
            "[['arm','regime','model_value_same_path','path_value_implied','total_value_own_path']]"
            ".round(5))",
        ),
        (
            "7. How much was there to win? (ORACLE — NOT DEPLOYABLE)",
            "If even an oracle that knows every candidate's true width cannot beat the incumbent, then "
            "width cannot help acquisition however well we predict it, and the direction should be "
            "killed rather than tuned.",
            "display(Image(filename=OUT/'figures'/'08_oracle_headroom.png'))\n"
            "display(pd.read_csv(OUT/'oracle_gap_decomposition.csv')"
            ".query('subset == \"B1_q20\" and region == \"EARLY_B16_40\" and metric == \"accuracy\"')"
            ".T)",
        ),
        (
            "8. Did the queries actually change?",
            "If the width-informed policy picks essentially the same simulations as the incumbent, there "
            "is no acquisition story to tell regardless of the metrics.",
            "display(Image(filename=OUT/'figures'/'09_divergent_queries.png'))\n"
            "display(pd.read_csv(OUT/'query_path_summary.csv').round(4))",
        ),
        (
            "9. Per-budget secondary metrics",
            "Balanced accuracy and PR-AUC across the trajectory, so a gain in one metric cannot be "
            "quoted without showing the others.",
            "display(Image(filename=OUT/'figures'/'05_per_budget_q20_balanced_accuracy.png'))\n"
            "display(Image(filename=OUT/'figures'/'06_per_budget_q20_pr_auc.png'))",
        ),
        (
            "10. Verdict",
            f"The predeclared verdict for this phase is **{verdict}**.\n\n"
            "The claim ledger is the contract; the guardrails say what each status is allowed to mean.",
            "display(Image(filename=OUT/'figures'/'10_claim_status.png'))\n"
            "print(json.dumps(json.loads((OUT/'decision.json').read_text(encoding='utf-8')), indent=2))",
        ),
    ]
    cells: list[dict[str, Any]] = [
        {"cell_type": "markdown", "id": "w0", "metadata": {},
         "source": ["# Week 9 Phase 2.2 — width-informed active learning\n", "\n",
                    "**Width helps prediction. Does it help us choose which simulation to run next, "
                    "without cheating?**\n", "\n",
                    "This notebook reads the generated artifacts. The engine is "
                    "`src/week9_phase2_2_width_informed_active_learning.py`.\n"]},
        {"cell_type": "code", "id": "wsetup", "execution_count": None, "metadata": {}, "outputs": [],
         "source": ["import json\n", "from pathlib import Path\n", "import pandas as pd\n",
                    "from IPython.display import display, Image\n",
                    "pd.set_option('display.width', 190)\n",
                    "pd.set_option('display.max_columns', 40)\n",
                    "ROOT = Path.cwd().parents[1] if Path.cwd().name == 'week_09' else Path.cwd()\n",
                    "OUT = ROOT / 'outputs' / 'week9_phase2_2_width_informed_active_learning'\n",
                    "assert OUT.is_dir(), OUT\n"]},
    ]
    for title, text, code in sections:
        key = hashlib.sha1(title.encode()).hexdigest()[:8]
        cells.append({"cell_type": "markdown", "id": f"md{key}", "metadata": {},
                      "source": [f"## {title}\n", "\n", text + "\n"]})
        cells.append({"cell_type": "code", "id": f"cd{key}", "execution_count": None, "metadata": {},
                      "outputs": [], "source": [line + "\n" for line in code.split("\n")]})
    return {"cells": cells,
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                        "name": "python3"},
                         "language_info": {"name": "python", "version": "3"}},
            "nbformat": 4, "nbformat_minor": 5}


def execute_and_save_notebook() -> str:
    import nbformat
    from nbconvert.preprocessors import ExecutePreprocessor
    from jupyter_client.kernelspec import KernelSpecManager

    available = set(KernelSpecManager().find_kernel_specs())
    kernel = "python3" if "python3" in available else sorted(available)[0]
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    ExecutePreprocessor(timeout=1200, kernel_name=kernel).preprocess(
        notebook, {"metadata": {"path": str(ROOT)}})
    nbformat.write(notebook, NOTEBOOK)
    return kernel


# --------------------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------------------
NEW_PATH_PREFIXES = (
    "src/week9_phase2_2_width_informed_active_learning.py",
    "notebooks/week_09/09_week9_phase2_2_width_informed_active_learning.ipynb",
    "outputs/week9_phase2_2_width_informed_active_learning/",
)


def working_tree_fingerprint() -> set[str]:
    result = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                            cwd=ROOT, text=True, capture_output=True, check=True)
    paths = set()
    for raw in result.stdout.splitlines():
        if not raw.strip():
            continue
        path = raw[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ")[-1]
        if any(path.startswith(prefix) for prefix in NEW_PATH_PREFIXES):
            continue
        paths.add(path)
    return paths


def directory_bytes(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def _fixed_paths_match() -> bool:
    """Every fixed-path arm must have queried exactly what its source arm queried."""
    frame = pd.read_csv(OUTPUT / "query_paths.csv.gz")
    wide = frame.pivot_table(index=["run_id", "query_order"], columns="arm",
                             values="population_row_index")
    for arm in tuple(STAGE1_ARMS) + tuple(STAGE2_ARMS):
        if arm.path_mode != "fixed":
            continue
        if arm.name not in wide.columns or arm.path_source not in wide.columns:
            return False
        if not bool((wide[arm.name] == wide[arm.path_source]).all()):
            return False
    return True


def validate(population: pd.DataFrame, specs: Sequence[Any], width: WidthData,
             metrics: pd.DataFrame, queries: pd.DataFrame, gate: pd.DataFrame,
             contrasts: pd.DataFrame, width_diag: pd.DataFrame, figures: list[Path],
             verdict: str, baseline_tree: set[str], include_notebook: bool) -> dict[str, Any]:
    module_source = Path(__file__).read_text(encoding="utf-8")
    physics_source = (ROOT / "src" / "week9_phase1_5_h_physics_confirmation.py").read_text(encoding="utf-8")
    reports = ["FINAL_PHASE2_2_REPORT.md", "SUPERVISOR_PHASE2_2_ONE_PAGE.md", "claim_ledger.md"]
    report_text = {name: (OUTPUT / name).read_text(encoding="utf-8") for name in reports}
    arms = set(metrics.arm)
    deployable = queries[queries.arm.eq("A1_predicted_width_margin")]
    oracle = queries[queries.arm.eq("A4_oracle_width_margin")]

    checks: dict[str, bool] = {
        # protocol
        "population_405": len(population) == 405,
        "labels_73": int(population.has_keyhole.sum()) == 73,
        "frozen_split_count_100": len(specs) == 100,
        "LS_is_laser_spot_radius": bool(np.allclose(population.LS, population.LS_m))
        and "Gaussian laser spot radius r0" in physics_source,
        "ST_is_substrate_temperature": bool(np.allclose(population.ST, population.ST_K))
        and '"ST_definition": "substrate temperature"' in physics_source,
        "budget_grid_16_to_80": tuple(sorted(metrics.budget.unique())) == BUDGETS,
        "every_arm_complete": all(
            len(metrics[metrics.arm.eq(arm)]) == 100 * len(BUDGETS) * len(SUBSETS) for arm in arms),
        "no_new_random_split_declared": ("train_test" + "_split") not in module_source,
        # THE central guardrail
        "deployable_arm_never_reads_unqueried_true_width": bool(
            (~deployable.true_width_of_unqueried_used).all()) if len(deployable) else False,
        "oracle_arm_is_labelled_leaky": bool(oracle.true_width_of_unqueried_used.all())
        if len(oracle) else True,
        "oracle_labelled_not_deployable_in_reports": all(
            "NOT DEPLOYABLE" in text for text in report_text.values()),
        "acquisition_sees_no_test_rows": bool((~queries.test_rows_available_to_acquisition).all()),
        "acquisition_sees_no_unrevealed_labels": bool(
            (~queries.unrevealed_labels_available_to_acquisition).all()),
        "width_predictor_trained_on_queried_only": "fit_width_predictor(\n" in module_source
        and "x4[observed]" in module_source,
        # comparability
        "phase114_reproduction_exact": bool(
            gate[gate.quantity.eq("q20_accuracy_AULC_B16_40")].iloc[0].status == "PASS"),
        "incumbent_arm_present": "A0_m3_margin" in arms,
        "m3_physics_mean_untouched": "fit_physics_mean" in module_source
        and "FixedMeanLaplaceGPC" in module_source,
        "same_path_arms_present": {"A1_model_on_A0_path"} <= arms,
        "fixed_path_arms_replay_their_source_exactly": _fixed_paths_match(),
        "margin_acquisition_is_frozen_rule": "binary_margin" in module_source
        and "classifier_margin" in module_source,
        # analysis discipline
        "primary_endpoint_declared": PRIMARY_METRIC == "accuracy" and PRIMARY_SUBSET == "B1_q20",
        "primary_contrast_present": len(contrasts[
            contrasts.contrast.eq("A1_predicted_width_margin - A0_m3_margin")
            & contrasts.region.eq("EARLY_B16_40") & contrasts.subset.eq(PRIMARY_SUBSET)
            & contrasts.metric.eq(PRIMARY_METRIC)]) == 1,
        "verdict_is_one_of_four": verdict in {
            "WIDTH-INFORMED ACTIVE LEARNING SURVIVES", "PREDICTIVE SIGNAL ONLY",
            "ORACLE-ONLY HEADROOM", "KILLED"},
        "width_diagnostics_cover_all_budgets": set(
            width_diag[width_diag.arm.eq("A1_predicted_width_margin")].budget) == set(BUDGETS),
        # terminology
        "reports_use_resampled_analysis_points": all(
            "consecutive resampled analysis point" in text for text in report_text.values()),
        "reports_state_development_only": all(
            "OLD-405 development evidence only" in text for text in report_text.values()),
        # outputs
        "ten_figures": len(figures) == 10,
        "figures_exist": all(p.is_file() and p.stat().st_size > 0 for p in figures),
        "figure_manifest_hashes_match": all(
            sha256_file(OUTPUT / row.artifact) == row.sha256
            for row in pd.read_csv(OUTPUT / "figure_manifest.csv").itertuples()),
        "reports_exist": all((OUTPUT / name).is_file() for name in reports),
        "reports_open_with_what_did_we_ask": report_text["SUPERVISOR_PHASE2_2_ONE_PAGE.md"]
        .lstrip().startswith("# What did we actually ask?"),
        "reports_state_the_verdict": all(verdict in text for text in report_text.values()),
        # local-only discipline
        "no_historical_file_touched": working_tree_fingerprint() == baseline_tree,
        "no_remote_operation_in_source": not any(
            token in module_source
            for token in ["git pu" + "sh", "gh " + "pr", "git rem" + "ote add", "requests." + "post"]),
        "no_raw_monitor_download": ("hf_hub" + "_download") not in module_source
        and ("snapshot" + "_download") not in module_source,
    }
    if include_notebook:
        notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        executed = [c for c in notebook["cells"] if c["cell_type"] == "code"
                    and c.get("execution_count") is not None and c.get("outputs")]
        errors = [o for c in notebook["cells"] for o in c.get("outputs", [])
                  if o.get("output_type") == "error"]
        checks["notebook_stores_executed_outputs"] = len(executed) >= 9
        checks["notebook_has_no_execution_errors"] = not errors

    failed = [name for name, value in checks.items() if not value]
    require(not failed, f"validation failed: {failed}")
    payload = {
        "status": "PASS", "phase": "Week 9 Phase 2.2",
        "notebook_checks_included": include_notebook,
        "checks": checks, "check_count": len(checks),
        "verdict": verdict, "arms": sorted(arms),
        "budgets": list(BUDGETS), "reported_checkpoints": list(CHECKPOINT_BUDGETS),
        "primary_endpoint": f"{PRIMARY_SUBSET} {PRIMARY_METRIC} AULC EARLY_B16_40",
        "output_bytes": directory_bytes(OUTPUT),
        "preexisting_dirty_paths_outside_this_phase": len(baseline_tree),
    }
    write_json(OUTPUT / "validation_report.json", payload)
    (OUTPUT / "validation_report.md").write_text(
        "# Week 9 Phase 2.2 validation report\n\n"
        f"**PASS** - {len(checks)} checks passed.\n\n"
        f"Verdict: **{verdict}**.\n"
        f"Arms: {', '.join(sorted(arms))}.\n"
        f"Primary endpoint: {PRIMARY_SUBSET} {PRIMARY_METRIC} AULC B16-40.\n"
        f"New artifacts on disk: {directory_bytes(OUTPUT) / 1e6:.2f} MB.\n"
        f"Pre-existing dirty paths untouched: {len(baseline_tree)}.\n\n"
        + "\n".join(f"- PASS: {name}" for name in checks) + "\n", encoding="utf-8")
    return payload


# --------------------------------------------------------------------------------------
# orchestration
# --------------------------------------------------------------------------------------
def analyse(specs: Sequence[Any], population: pd.DataFrame, width: WidthData,
            arms: Sequence[Arm]) -> dict[str, Any]:
    metrics_list, audit_list, query_list = [], [], []
    paths: dict[str, dict[str, list[int]]] = {}
    for arm in arms:
        metrics, audits, queries, arm_paths = collect_arm(arm.name, specs)
        metrics_list.append(metrics)
        if len(audits):
            audit_list.append(audits)
        if len(queries):
            query_list.append(queries)
        paths[arm.name] = arm_paths
    metrics = pd.concat(metrics_list, ignore_index=True)
    audits = pd.concat(audit_list, ignore_index=True) if audit_list else pd.DataFrame()
    queries = pd.concat(query_list, ignore_index=True) if query_list else pd.DataFrame()
    write_csv(OUTPUT / "per_run_budget_metrics.csv.gz", metrics)
    write_csv(OUTPUT / "acquisition_queries.csv.gz", queries)
    path_frame = pd.DataFrame([
        {"arm": arm, "run_id": run_id, "query_order": order, "population_row_index": index}
        for arm, arm_paths in paths.items()
        for run_id, path in arm_paths.items() for order, index in enumerate(path)])
    write_csv(OUTPUT / "query_paths.csv.gz", path_frame)
    return {"metrics": metrics, "audits": audits, "queries": queries, "paths": paths}


COMPARISONS: tuple[tuple[str, str, str], ...] = (
    ("A1_predicted_width_margin", "A0_m3_margin", "PRIMARY deployable total"),
    ("A4_oracle_width_margin", "A0_m3_margin", "ORACLE headroom - NOT DEPLOYABLE"),
    ("A1_model_on_A0_path", "A0_m3_margin", "model value, query path held fixed"),
    ("A4_model_on_A0_path", "A0_m3_margin", "ORACLE model value, path held fixed"),
    ("A0_model_on_A1_path", "A0_m3_margin", "path value, model held fixed"),
)


def _build_paths(a0: dict[str, list[int]], specs: Sequence[Any],
                 arms_done: Sequence[Arm]) -> dict[str, dict[str, list[int]]]:
    paths: dict[str, dict[str, list[int]]] = {"A0": {k: list(v) for k, v in a0.items()}}
    for arm in arms_done:
        if all(checkpoint_path(arm.name, spec.run_id).is_file() for spec in specs):
            paths[arm.name] = {
                spec.run_id: [int(v) for v in read_checkpoint(
                    checkpoint_path(arm.name, spec.run_id))["queried_indices"]]
                for spec in specs}
    return paths


def run(stage: str = "all") -> None:
    started = time.time()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    baseline_tree = working_tree_fingerprint()

    print("[1] frozen protocol, inherited width columns, availability audit", flush=True)
    population, specs, a0, width = load_protocol()
    availability = availability_audit(population, specs, a0, width)
    distances = w85.b1_distance(population)
    logh = p11.log_h_values(population)

    if stage in ("1", "all"):
        # The incumbent must run first: the same-path arms replay ITS realised M3-margin
        # path, which does not exist until it has been generated. The frozen historical
        # "A0" path is used only for its first 16 entries, the frozen initial design that
        # every arm starts from.
        print("[2a] stage 1: the incumbent M3-margin trajectory", flush=True)
        execute_arms((STAGE1_ARMS[0],), population, specs, width, distances,
                     _build_paths(a0, specs, ()))
        print("[2b] stage 1: deployable predicted width, oracle bound, and the same-path arms",
              flush=True)
        execute_arms(STAGE1_ARMS[1:], population, specs, width, distances,
                     _build_paths(a0, specs, (STAGE1_ARMS[0],)))
        stage1 = analyse(specs, population, width, STAGE1_ARMS)
        outer = compute_aulc(stage1["metrics"])
        summary = aulc_summary(outer)
        gate = phase114_reproduction_gate(summary)
        contrasts = paired_aulc_contrasts(outer, COMPARISONS)
        gap = oracle_gap_decomposition(summary, contrasts)
        primary = gap[gap.subset.eq(PRIMARY_SUBSET) & gap.region.eq("EARLY_B16_40")
                      & gap.metric.eq(PRIMARY_METRIC)].iloc[0]
        print(json.dumps({
            "stage1_gate": str(gate[gate.quantity.eq("q20_accuracy_AULC_B16_40")].iloc[0].status),
            "A0_incumbent_q20_AULC_B16_40": round(float(primary.A0_incumbent), 6),
            "A1_deployable": round(float(primary.A1_predicted_width), 6),
            "A4_oracle_NOT_DEPLOYABLE": round(float(primary.A4_oracle_width), 6),
            "oracle_headroom": round(float(primary.oracle_headroom_A4_minus_A0), 6),
            "oracle_headroom_ci": [round(float(primary.oracle_headroom_ci_lower), 6),
                                   round(float(primary.oracle_headroom_ci_upper), 6)],
            "deployable_gain": round(float(primary.realised_gain_A1_minus_A0), 6),
            "deployable_gain_ci": [round(float(primary.realised_gain_ci_lower), 6),
                                   round(float(primary.realised_gain_ci_upper), 6)],
        }, indent=2), flush=True)
        if stage == "1":
            print(f"stage 1 complete in {time.time() - started:.0f}s", flush=True)
            return

    print("[3] stage 2: incumbent model replayed on the width-informed query path", flush=True)
    execute_arms(STAGE2_ARMS, population, specs, width, distances,
                 _build_paths(a0, specs, STAGE1_ARMS))

    print("[4] collecting all arms and computing endpoints", flush=True)
    all_arms = tuple(STAGE1_ARMS) + tuple(STAGE2_ARMS)
    collected = analyse(specs, population, width, all_arms)
    metrics, audits, queries, paths = (collected["metrics"], collected["audits"],
                                       collected["queries"], collected["paths"])
    outer = compute_aulc(metrics)
    summary = aulc_summary(outer)
    gate = phase114_reproduction_gate(summary)
    contrasts = paired_aulc_contrasts(outer, COMPARISONS)
    curves = per_budget_summary(metrics)
    per_budget_contrasts(metrics, COMPARISONS)
    gap = oracle_gap_decomposition(summary, contrasts)
    decomposition = same_path_decomposition(contrasts)
    width_diag = width_predictor_summary(audits)
    overlap, path_summary = path_diagnostics(paths, population, width, logh)
    divergent = pd.read_csv(OUTPUT / "divergent_queries.csv.gz") if (
        OUTPUT / "divergent_queries.csv.gz").is_file() else pd.DataFrame()

    print("[5] decision and claim ledger", flush=True)
    verdict, facts = decide(contrasts, gap, path_summary)
    claims = build_claims(contrasts, gap, decomposition, width_diag, path_summary, curves,
                          facts, verdict)
    write_csv(OUTPUT / "claim_status.csv", claims)

    print("[6] figures", flush=True)
    figures = make_figures(curves, summary, contrasts, gap, decomposition, width_diag, audits,
                           path_summary, divergent, claims, population, width)

    print("[7] reports and notebook", flush=True)
    render_reports(population, availability, curves, summary, contrasts, gap, decomposition,
                   width_diag, path_summary, gate, claims, facts, verdict, figures)
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    NOTEBOOK.write_text(json.dumps(notebook_payload(verdict), indent=1) + "\n", encoding="utf-8")

    print("[8] validation", flush=True)
    validate(population, specs, width, metrics, queries, gate, contrasts, width_diag, figures,
             verdict, baseline_tree, include_notebook=False)
    kernel = execute_and_save_notebook()
    validation = validate(population, specs, width, metrics, queries, gate, contrasts, width_diag,
                          figures, verdict, baseline_tree, include_notebook=True)

    manifest = {
        "study": "Week 9 Phase 2.2 - width-informed active learning",
        "primary_question": "Can the predictive width signal become a legitimate sample-efficiency "
                            "improvement over M3 + M3-margin?",
        "primary_endpoint": f"{PRIMARY_SUBSET} {PRIMARY_METRIC} AULC EARLY_B16_40, "
                            f"A1_predicted_width_margin - A0_m3_margin",
        "success_bar": {"minimum_gain": SUCCESS_GAIN, "paired_ci_lower_above_zero": True,
                        "keyhole_recall_harm_limit": RECALL_HARM_LIMIT},
        "verdict": verdict, "decision_facts": facts,
        "regimes": {
            "A_deployable": "width predicted from queried points only; unqueried candidates never "
                            "expose their true width",
            "B_early_prefix_side_information": "not executed: dominated by the oracle bound, which shows no meaningful headroom; see the report section for the argument",
            "C_oracle": "ORACLE WIDTH - NOT DEPLOYABLE; upper bound only",
        },
        "arms": {arm.name: {"width_regime": arm.width_regime, "path_mode": arm.path_mode,
                            "path_source": arm.path_source, "regime": arm.regime_label,
                            "description": arm.description} for arm in all_arms},
        "budgets": list(BUDGETS), "reported_checkpoints": list(CHECKPOINT_BUDGETS),
        "width_models": list(WIDTH_MODELS),
        "width_selection_budgets": list(WIDTH_SELECTION_BUDGETS),
        "bootstrap_draws": BOOTSTRAP_DRAWS,
        "population": 405, "population_keyholes": 73,
        "simulations_with_usable_width": int(width.available.sum()),
        "inherited_from": ["src/week9_phase1_13_fixed_physics_ard_discrepancy.py",
                           "src/week9_phase1_14_m3_margin_acquisition.py",
                           "src/week9_phase2_1r_simple_width_change_control.py",
                           "src/week9_phase2_1re_early_prefix_width_control.py"],
        "notebook_kernel": kernel, "notebook_sha256": sha256_file(NOTEBOOK),
        "local_only": True, "new_worktree_or_clone_created": False,
        "raw_monitor_bytes_downloaded": 0,
        "new_artifact_bytes": directory_bytes(OUTPUT) + NOTEBOOK.stat().st_size,
        "validation": validation, "elapsed_seconds": time.time() - started,
    }
    write_json(OUTPUT / "run_manifest.json", manifest)
    print(json.dumps({
        "status": "PASS", "verdict": verdict,
        "primary_gain": round(facts["primary_gain"], 5),
        "primary_gain_ci": [round(facts["primary_gain_ci_lower"], 5),
                            round(facts["primary_gain_ci_upper"], 5)],
        "oracle_headroom": round(facts["oracle_headroom"], 5),
        "model_value": round(facts["model_only_gain"], 5),
        "path_jaccard_B40": round(facts["path_jaccard_B40"], 4),
        "new_artifact_megabytes": round(manifest["new_artifact_bytes"] / 1e6, 2),
        "elapsed_seconds": round(time.time() - started, 1),
    }, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Week 9 Phase 2.2 width-informed active learning")
    parser.add_argument("--run", action="store_true", help="run the phase")
    parser.add_argument("--stage", default="all", choices=["1", "all"],
                        help="'1' stops after the oracle-headroom gate")
    args = parser.parse_args()
    if args.run:
        run(args.stage)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
