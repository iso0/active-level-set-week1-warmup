"""Bootstrap inference, sign tests, Holm correction and the frozen decision ledger.

Three bootstrap families are used in the thesis and are kept separate because
their resampling units and seed derivations differ:

* ``hierarchical_bootstrap`` (Week 8.5 frozen confirmation): resample the 20
  repeats with replacement, keep all folds, resample the Random continuations
  within each fold; fold-matched contrasts averaged per draw.
* ``repeat_block_bootstrap`` (Week 9 Phase 1.7-1.18B): resample 20 repeat-block
  means with replacement; seed ``seed_u32(seed_key(root, 'bootstrap', key))``.
* ``paired_run_bootstrap`` (Phase 6/7): resample paired run differences.

Seed roots are parameters (``protocol.SEED_ROOTS`` holds the Week 9 literals);
only the Week 8.5 root lives here because the hierarchical bootstrap and the
decision ledger are specific to that protocol.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Sequence

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from alse.io import require, seed_key, seed_u32

# Seed namespace of the Week 8.5 frozen confirmation (legacy literal; do not rename).
FROZEN_CONFIRMATION_SEED_ROOT = "week8_5_frozen_confirmation|v1"
CONFIRMATION_ARMS = ("binary_margin", "binary_random", "binary_uncertainty_repulsion")
CROSSING_TARGETS = (0.75, 0.80, 0.85)
HIERARCHICAL_ESTIMANDS = (
    "delta_AULC",
    "delta_Q",
    "multiplier",
    "delta_repulsion_AULC16_80",
    "delta_repulsion_AULC16_40",
    "delta_repulsion_min",
)
# Pre-registered pass thresholds of the Week 8.5 decision ledger.
PERFORMANCE_PASS_LOWER = 0.020
QUERY_SAVING_PASS_LOWER = 10.0
MULTIPLIER_PASS_LOWER = 1.25
REPULSION_PASS_LOWER = 0.010
RHO_RANDOM_MINIMUM = 0.95
# Phase 1.8 two-by-two model/path effects (Y<model><path>; 1 = physics).
DECOMPOSITION_EFFECTS = ("TOTAL", "MODEL", "PATH", "ME_A0", "ME_A1", "PE_M0", "PE_M1", "INT", "MODEL_minus_PATH")

_KEY_COLUMNS = ("run_id", "repeat", "fold", "arm", "continuation_id")
_CHECKPOINT_METRICS = ("accuracy", "recall", "balanced_accuracy", "false_negative", "false_positive", "true_negative", "true_positive", "row_count")


# --- Week 8.5 run-level endpoints -------------------------------------------


def build_run_metrics(
    frame: pd.DataFrame,
    horizon: int,
    terminal_budget: int,
    *,
    aulc: Callable[[Sequence[int], Sequence[float], int, int], float],
    persistent_crossing: Callable[[Sequence[int], Sequence[float], float], tuple[float, bool]],
    targets: Sequence[float] = CROSSING_TARGETS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One row per (run, arm, continuation): q20 AULC 16-80 / 16-40, q30 AULC
    16-80, budget-40 and terminal checkpoint metrics, persistent crossings.

    ``frame`` holds one row per budget with ``B1_q20_accuracy`` etc. The
    endpoint functions are injected (``metrics.aulc``,
    ``metrics.persistent_crossing``); ``terminal_budget`` is
    ``protocol.declared_budgets(horizon)[-1]``. Returns (run_metrics, crossings).

    # frozen: week8_5_frozen_sample_efficiency_confirmation.py::build_run_metrics
    """
    rows: list[dict[str, Any]] = []
    crossings: list[dict[str, Any]] = []
    for keys, group in frame.groupby(list(_KEY_COLUMNS), sort=True):
        run_id, repeat, fold, arm, continuation = keys
        budgets = group["budget"].to_numpy(int)
        q20 = group["B1_q20_accuracy"].to_numpy(float)
        row: dict[str, Any] = {"run_id": run_id, "repeat": repeat, "fold": fold, "arm": arm, "continuation_id": continuation, "horizon": horizon}
        row["B1_q20_AULC_16_80"] = aulc(budgets, q20, 16, 80)
        row["B1_q20_AULC_16_40"] = aulc(budgets, q20, 16, 40)
        row["B1_q30_AULC_16_80"] = aulc(budgets, group["B1_q30_accuracy"].to_numpy(float), 16, 80)
        for budget, label in ((40, "budget40"), (terminal_budget, "terminal")):
            selected = group[group.budget.eq(budget)].iloc[0]
            for subset in ("B1_q20", "B1_q30"):
                for metric in _CHECKPOINT_METRICS:
                    row[f"{label}_{subset}_{metric}"] = selected[f"{subset}_{metric}"]
        for target in targets:
            crossing, observed = persistent_crossing(budgets, q20, target)
            name = f"{target:.2f}"
            row[f"crossing_{name}"] = crossing
            row[f"crossing_{name}_observed"] = observed
            row[f"restricted_crossing_{name}"] = crossing if observed else horizon
            crossings.append({**{k: row[k] for k in (*_KEY_COLUMNS, "horizon")}, "boundary": "B1", "quantile": 20, "target": target, "crossing_budget": crossing, "event_observed": observed, "censoring_label": "" if observed else f"{horizon}+", "restricted_crossing": crossing if observed else horizon})
        rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(crossings)


# --- Week 8.5 hierarchical bootstrap ----------------------------------------


def _fold_tables(run_metrics: pd.DataFrame, repeats: np.ndarray, folds: int) -> dict[str, np.ndarray]:
    """Per-(repeat, fold) arrays in repeat-major order (matches the archive loop)."""
    grouped = {
        (int(r), int(f), arm): group.sort_values("continuation_id")
        for (r, f, arm), group in run_metrics.groupby(["repeat", "fold", "arm"])
    }
    keys = [(int(r), f) for r in repeats for f in range(1, folds + 1)]
    missing = [(r, f, arm) for r, f in keys for arm in CONFIRMATION_ARMS if (r, f, arm) not in grouped]
    require(not missing, f"run metrics incomplete, first missing (repeat, fold, arm): {missing[:3]}")
    margin = [grouped[(r, f, "binary_margin")].iloc[0] for r, f in keys]
    repulsion = [grouped[(r, f, "binary_uncertainty_repulsion")].iloc[0] for r, f in keys]
    random = [grouped[(r, f, "binary_random")] for r, f in keys]
    sizes = {len(group) for group in random}
    require(len(sizes) == 1, f"Random continuation counts differ across folds: {sorted(sizes)}")
    return {
        "margin80": np.array([row.B1_q20_AULC_16_80 for row in margin], float),
        "margin40": np.array([row.B1_q20_AULC_16_40 for row in margin], float),
        "marginQ": np.array([row["restricted_crossing_0.80"] for row in margin], float),
        "rep80": np.array([row.B1_q20_AULC_16_80 for row in repulsion], float),
        "rep40": np.array([row.B1_q20_AULC_16_40 for row in repulsion], float),
        "random80": np.array([g.B1_q20_AULC_16_80.to_numpy(float) for g in random]),
        "randomQ": np.array([g["restricted_crossing_0.80"].to_numpy(float) for g in random]),
    }


def hierarchical_bootstrap(
    run_metrics: pd.DataFrame,
    draws: int = 20000,
    *,
    root: str = FROZEN_CONFIRMATION_SEED_ROOT,
    repeats: int = 20,
    folds: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Repeat x continuation hierarchical bootstrap of the Week 8.5 estimands.

    Per draw: sample ``repeats`` repeat ids with replacement (``rng.choice``),
    keep every fold, and inside each fold resample the Random continuations
    with replacement (``rng.integers``); average the fold-matched contrasts.
    Seed ``seed_u32(seed_key(root, 'hierarchical_bootstrap', 'draws', draws))``.
    Returns (draws frame, summary frame) with the one-sided 95% lower bound as
    the 5th percentile and the two-sided 2.5/97.5 percentiles. The RNG call
    order is identical to the archive so the draws match bitwise.

    # frozen: week8_5_frozen_sample_efficiency_confirmation.py::hierarchical_bootstrap
    """
    repeat_ids = np.arange(1, repeats + 1)
    rng = np.random.default_rng(seed_u32(seed_key(root, "hierarchical_bootstrap", "draws", draws)))
    tables = _fold_tables(run_metrics, repeat_ids, folds)
    n_random = tables["random80"].shape[1]
    draw_rows: list[dict[str, float | int]] = []
    for draw in range(draws):
        sampled = rng.choice(repeat_ids, size=len(repeat_ids), replace=True)
        picks = np.empty((repeats * folds, n_random), dtype=np.int64)
        position = np.empty(repeats * folds, dtype=np.int64)
        slot = 0
        for repeat in sampled:
            for fold in range(folds):
                picks[slot] = rng.integers(0, n_random, size=n_random)
                position[slot] = (int(repeat) - 1) * folds + fold
                slot += 1
        random80 = np.take_along_axis(tables["random80"][position], picks, axis=1).mean(axis=1)
        random_q = np.take_along_axis(tables["randomQ"][position], picks, axis=1).mean(axis=1)
        margin80, margin40, margin_q = (tables[k][position] for k in ("margin80", "margin40", "marginQ"))
        rep80 = (tables["rep80"][position] - margin80).mean()
        rep40 = (tables["rep40"][position] - margin40).mean()
        draw_rows.append(
            {
                "draw": draw + 1,
                "delta_AULC": float((margin80 - random80).mean()),
                "delta_Q": float((random_q - margin_q).mean()),
                "multiplier": float(random_q.mean() / margin_q.mean()),
                "delta_repulsion_AULC16_80": float(rep80),
                "delta_repulsion_AULC16_40": float(rep40),
                "delta_repulsion_min": float(min(rep80, rep40)),
            }
        )
    draws_frame = pd.DataFrame(draw_rows)
    summary_rows = []
    for column in HIERARCHICAL_ESTIMANDS:
        values = draws_frame[column].to_numpy(float)
        summary_rows.append(
            {
                "estimand": column,
                "bootstrap_draws": draws,
                "point_estimate_bootstrap_mean": float(values.mean()),
                "one_sided_95pct_lower_bound": float(np.quantile(values, 0.05)),
                "two_sided_95pct_lower": float(np.quantile(values, 0.025)),
                "two_sided_95pct_upper": float(np.quantile(values, 0.975)),
            }
        )
    return draws_frame, pd.DataFrame(summary_rows)


def point_estimands(run_metrics: pd.DataFrame) -> dict[str, float]:
    """Fold-level point estimates of the six Week 8.5 estimands (mean over folds).

    # frozen: week8_5_frozen_sample_efficiency_confirmation.py::point_estimands
    """
    fold_rows: list[dict[str, float]] = []
    for _, group in run_metrics.groupby(["repeat", "fold"]):
        margin = group[group.arm.eq("binary_margin")].iloc[0]
        rep = group[group.arm.eq("binary_uncertainty_repulsion")].iloc[0]
        random = group[group.arm.eq("binary_random")]
        fold_rows.append(
            {
                "delta_AULC": float(margin.B1_q20_AULC_16_80 - random.B1_q20_AULC_16_80.mean()),
                "delta_Q": float(random["restricted_crossing_0.80"].mean() - margin["restricted_crossing_0.80"]),
                "random_Q": float(random["restricted_crossing_0.80"].mean()),
                "margin_Q": float(margin["restricted_crossing_0.80"]),
                "rep80": float(rep.B1_q20_AULC_16_80 - margin.B1_q20_AULC_16_80),
                "rep40": float(rep.B1_q20_AULC_16_40 - margin.B1_q20_AULC_16_40),
            }
        )
    frame = pd.DataFrame(fold_rows)
    return {
        "delta_AULC": float(frame.delta_AULC.mean()),
        "delta_Q": float(frame.delta_Q.mean()),
        "multiplier": float(frame.random_Q.mean() / frame.margin_Q.mean()),
        "delta_repulsion_AULC16_80": float(frame.rep80.mean()),
        "delta_repulsion_AULC16_40": float(frame.rep40.mean()),
        "delta_repulsion_min": float(min(frame.rep80.mean(), frame.rep40.mean())),
    }


def random_finite_fraction(run_metrics: pd.DataFrame, expected: int | None = 3000) -> float:
    """rho_random: fraction of Random continuations whose 0.80 crossing was observed.

    The archive recomputed ``persistent_crossing`` over the trajectory frame;
    here the run-level flag ``crossing_0.80_observed`` (the same computation,
    stored by ``build_run_metrics``) is averaged, exactly as ``decision_ledger``
    does. ``expected`` asserts the 100 x 30 continuation count (None disables).

    # frozen: week8_5_frozen_sample_efficiency_confirmation.py::random_finite_fraction
    """
    random = run_metrics[run_metrics.arm.eq("binary_random")]
    if expected is not None:
        require(len(random) == expected, f"Expected {expected} Random continuations, found {len(random)}")
    return float(random["crossing_0.80_observed"].astype(bool).mean())


def decision_ledger(run_metrics: pd.DataFrame, bootstrap_summary: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Pre-registered Week 8.5 claim decisions (PASS / QUALIFY / FAIL).

    primary_performance PASS iff lower(delta_AULC) >= 0.020; query_saving PASS
    iff rho >= 0.95 and lower(delta_Q) >= 10; multiplier PASS iff rho >= 0.95
    and lower >= 1.25; repulsion PASS iff lower(min delta) >= 0.010. Overall
    PASS iff the first three PASS, else NOT_CONFIRMED.

    # frozen: week8_5_frozen_sample_efficiency_confirmation.py::decision_ledger
    """
    points = point_estimands(run_metrics)
    lowers = bootstrap_summary.set_index("estimand")["one_sided_95pct_lower_bound"].to_dict()
    rho = float(run_metrics[run_metrics.arm.eq("binary_random")]["crossing_0.80_observed"].mean())
    perf = "PASS" if lowers["delta_AULC"] >= PERFORMANCE_PASS_LOWER else ("QUALIFY" if points["delta_AULC"] > 0 else "FAIL")
    query = "PASS" if rho >= RHO_RANDOM_MINIMUM and lowers["delta_Q"] >= QUERY_SAVING_PASS_LOWER else ("QUALIFY" if lowers["delta_Q"] > 0 else "FAIL")
    multiplier = "PASS" if rho >= RHO_RANDOM_MINIMUM and lowers["multiplier"] >= MULTIPLIER_PASS_LOWER else ("QUALIFY" if lowers["multiplier"] > 1 else "FAIL")
    repulsion = "PASS" if lowers["delta_repulsion_min"] >= REPULSION_PASS_LOWER else ("QUALIFY" if points["delta_repulsion_AULC16_80"] > 0 and points["delta_repulsion_AULC16_40"] > 0 else "FAIL")
    rows: list[dict[str, Any]] = []
    for claim, decision, estimate, lower, threshold in (
        ("primary_performance", perf, points["delta_AULC"], lowers["delta_AULC"], PERFORMANCE_PASS_LOWER),
        ("query_saving", query, points["delta_Q"], lowers["delta_Q"], QUERY_SAVING_PASS_LOWER),
        ("multiplier", multiplier, points["multiplier"], lowers["multiplier"], MULTIPLIER_PASS_LOWER),
        ("repulsion_h_0.15", repulsion, points["delta_repulsion_min"], lowers["delta_repulsion_min"], REPULSION_PASS_LOWER),
    ):
        rows.append({"claim": claim, "decision": decision, "point_estimate": estimate, "one_sided_95pct_lower_bound": lower, "pass_threshold": threshold, "rho_random": rho, "horizon": horizon})
    overall = "PASS" if all(value == "PASS" for value in (perf, query, multiplier)) else "NOT_CONFIRMED"
    rows.append({"claim": "overall_primary_confirmation", "decision": overall, "point_estimate": math.nan, "one_sided_95pct_lower_bound": math.nan, "pass_threshold": math.nan, "rho_random": rho, "horizon": horizon})
    return pd.DataFrame(rows)


def aggregate_repeat_metrics(run_metrics: pd.DataFrame) -> pd.DataFrame:
    """Per (repeat, arm): macro means of every numeric column plus pooled accuracies.

    # frozen: week8_5_frozen_sample_efficiency_confirmation.py::aggregate_repeat_metrics
    """
    numeric = [c for c in run_metrics.columns if c not in _KEY_COLUMNS and pd.api.types.is_numeric_dtype(run_metrics[c])]
    rows: list[dict[str, Any]] = []
    for (repeat, arm), group in run_metrics.groupby(["repeat", "arm"]):
        row: dict[str, Any] = {"repeat": repeat, "arm": arm, "fold_count": group.fold.nunique(), "continuation_count": group.continuation_id.nunique()}
        for column in numeric:
            row[f"macro_mean__{column}"] = float(group[column].mean())
        for label in ("budget40", "terminal"):
            for subset in ("B1_q20", "B1_q30"):
                correct = group[f"{label}_{subset}_true_positive"].sum() + group[f"{label}_{subset}_true_negative"].sum()
                total = group[f"{label}_{subset}_row_count"].sum()
                row[f"pooled__{label}_{subset}_accuracy"] = float(correct / total)
        rows.append(row)
    return pd.DataFrame(rows)


# --- Week 9 repeat-block bootstrap ------------------------------------------


def repeat_block_bootstrap(
    values: np.ndarray,
    key: str,
    root: str,
    draws: int = 10000,
    *,
    blocks: int | None = 20,
    salt: str = "bootstrap",
) -> tuple[float, float, float]:
    """(mean, 2.5%, 97.5%) of resampled repeat-block means.

    rng = default_rng(seed_u32(seed_key(root, salt, key))); one
    ``rng.integers(0, n, size=(draws, n))`` call. ``blocks`` asserts the
    archive's 20-repeat contract (None disables the check). Phase 1.7-1.16
    used draws=10000, Phase 1.18B 20000.

    # frozen: week9_phase1_11_fixed_mean_discrepancy_gp.py::bootstrap_interval
    # frozen: week9_phase1_13_fixed_physics_ard_discrepancy.py::bootstrap_interval
    # frozen: week9_phase1_8_model_path_decomposition.py::bootstrap_repeat
    # frozen: week9_phase1_16_m3_repulsion_scale_audit.py::bootstrap
    # frozen: week9_phase1_18b_finalize.py::bootstrap
    """
    values = np.asarray(values, dtype=float)
    if blocks is not None:
        require(len(values) == blocks, f"repeat bootstrap expects {blocks} blocks, got {len(values)} ({key})")
    require(np.isfinite(values).all(), f"repeat bootstrap input drift {key}")
    rng = np.random.default_rng(seed_u32(seed_key(root, salt, key)))
    means = values[rng.integers(0, len(values), size=(draws, len(values)))].mean(axis=1)
    return float(values.mean()), float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def bootstrap_repeat_ratio(
    numerators: np.ndarray,
    denominators: np.ndarray,
    key: str,
    root: str,
    draws: int = 10000,
    *,
    blocks: int | None = 20,
    salt: str = "bootstrap-ratio",
) -> tuple[float, float, float]:
    """Ratio-of-sums bootstrap over repeat blocks: (sum n / sum d, 2.5%, 97.5%).

    Draws with a zero resampled denominator are dropped; more than 99% of the
    draws must be valid. Seed ``seed_u32(seed_key(root, 'bootstrap-ratio', key))``.

    # frozen: week9_phase1_13_fixed_physics_ard_discrepancy.py::bootstrap_repeat_ratio
    """
    numerators = np.asarray(numerators, float)
    denominators = np.asarray(denominators, float)
    if blocks is not None:
        require(len(numerators) == len(denominators) == blocks, f"repeat ratio bootstrap expects {blocks} blocks ({key})")
    require(len(numerators) == len(denominators) and np.isfinite(numerators).all() and np.isfinite(denominators).all(), f"repeat ratio bootstrap drift {key}")
    require(denominators.sum() > 0, f"undefined repeat ratio {key}")
    rng = np.random.default_rng(seed_u32(seed_key(root, salt, key)))
    indices = rng.integers(0, len(numerators), size=(draws, len(numerators)))
    draw_denominators = denominators[indices].sum(axis=1)
    valid = draw_denominators > 0
    require(valid.mean() > 0.99, f"insufficient changed decisions for {key}")
    ratios = numerators[indices].sum(axis=1)[valid] / draw_denominators[valid]
    point = float(numerators.sum() / denominators.sum())
    return point, float(np.quantile(ratios, 0.025)), float(np.quantile(ratios, 0.975))


def repeat_block_contrast(values: np.ndarray, key: str, root: str, draws: int = 10000) -> dict[str, float | int]:
    """One paired-contrast row: repeat-block bootstrap of the 20 per-repeat
    differences plus median, sign counts and the exact two-sided sign test on
    the non-zero blocks (the shared core of the Phase 1.13 / 1.16 / 1.18B tables).

    # frozen: week9_phase1_13_fixed_physics_ard_discrepancy.py::compute_aulc (contrast rows)
    # frozen: week9_phase1_18b_finalize.py::contrasts
    """
    values = np.asarray(values, dtype=float)
    mean, lower, upper = repeat_block_bootstrap(values, key, root, draws)
    return {
        "mean_difference": mean,
        "median_difference": float(np.median(values)),
        "ci_lower": lower,
        "ci_upper": upper,
        "positive_repeat_blocks": int((values > 0).sum()),
        "zero_repeat_blocks": int((values == 0).sum()),
        "negative_repeat_blocks": int((values < 0).sum()),
        "raw_two_sided_sign_p": sign_test_pvalue(int((values > 0).sum()), int((values < 0).sum())),
        "bootstrap_draws": int(draws),
    }


def model_path_decomposition(
    aulc: pd.DataFrame,
    root: str,
    draws: int = 10000,
    endpoint: str = "B1_q20_accuracy_AULC_16_80",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Symmetric two-by-two decomposition of Y11 - Y00 into MODEL and PATH effects.

    ``aulc`` is long: run_id, repeat, fold, arm in {Y00, Y10, Y01, Y11},
    endpoint, AULC. Per run: TOTAL = Y11-Y00, ME_A0 = Y10-Y00, ME_A1 = Y11-Y01,
    PE_M0 = Y01-Y00, PE_M1 = Y11-Y10, INT = Y11-Y10-Y01+Y00, MODEL = mean of
    the ME's, PATH = mean of the PE's (MODEL + PATH == TOTAL). Effects are
    averaged per repeat and bootstrapped with key = effect name; the decision
    reads the MODEL_minus_PATH interval. Returns (run wide, repeat means, summary).

    # frozen: week9_phase1_8_model_path_decomposition.py::decompose
    """
    part = aulc[aulc.endpoint.eq(endpoint)]
    wide = part.pivot(index=["run_id", "repeat", "fold"], columns="arm", values="AULC").reset_index()
    require({"Y00", "Y10", "Y01", "Y11"}.issubset(wide.columns), "2x2 AULC incomplete")
    wide["TOTAL"] = wide.Y11 - wide.Y00
    wide["ME_A0"] = wide.Y10 - wide.Y00
    wide["ME_A1"] = wide.Y11 - wide.Y01
    wide["PE_M0"] = wide.Y01 - wide.Y00
    wide["PE_M1"] = wide.Y11 - wide.Y10
    wide["INT"] = wide.Y11 - wide.Y10 - wide.Y01 + wide.Y00
    wide["MODEL"] = 0.5 * (wide.ME_A0 + wide.ME_A1)
    wide["PATH"] = 0.5 * (wide.PE_M0 + wide.PE_M1)
    wide["MODEL_minus_PATH"] = wide.MODEL - wide.PATH
    require(np.allclose(wide.MODEL + wide.PATH, wide.TOTAL, atol=1e-14, rtol=0), "symmetric decomposition identity failed")
    repeat = wide.groupby("repeat", as_index=False).mean(numeric_only=True)
    summaries = []
    for effect in DECOMPOSITION_EFFECTS:
        mean, lower, upper = repeat_block_bootstrap(repeat[effect].to_numpy(float), effect, root, draws)
        summaries.append({"effect": effect, "mean": mean, "ci_lower": lower, "ci_upper": upper, "bootstrap_draws": draws})
    summary = pd.DataFrame(summaries)
    contrast = summary[summary.effect.eq("MODEL_minus_PATH")].iloc[0]
    decision = "MODEL_DOMINANT" if contrast.ci_lower > 0 else ("PATH_DOMINANT" if contrast.ci_upper < 0 else "MIXED_OR_UNRESOLVED")
    summary["decision"] = decision
    return wide, repeat, summary


# --- Phase 6/7 paired run bootstrap -----------------------------------------


def paired_run_bootstrap(differences: np.ndarray, resamples: int = 5000, seed: int = 0) -> dict[str, float]:
    """Percentile bootstrap of the mean of paired run differences (a - b).

    ``seed`` is the caller's ``stable_seed(BASE_SEED, comparison, metric,
    'paired_bootstrap')`` (Phase 6) or ``stable_seed(BASE_SEED, 'phase7', ...)``
    (Phase 7). One ``rng.integers(0, n, n)`` call per resample, then the
    2.5 / 50 / 97.5 percentiles of the resampled means.

    # frozen: week7_phase6_real_data_boundary_active_level_set.py::paired_comparisons
    """
    differences = np.asarray(differences, dtype=float)
    require(len(differences) > 0, "paired bootstrap needs at least one difference")
    rng = np.random.default_rng(seed)
    samples = np.empty(resamples, dtype=float)
    for index in range(resamples):
        sample = rng.integers(0, len(differences), len(differences))
        samples[index] = float(np.mean(differences[sample]))
    low, median, high = np.quantile(samples, [0.025, 0.5, 0.975])
    return {
        "paired_run_count": int(len(differences)),
        "mean_difference": float(np.mean(differences)),
        "median_difference": float(np.median(differences)),
        "bootstrap_resamples": int(resamples),
        "bootstrap_ci_low": float(low),
        "bootstrap_median": float(median),
        "bootstrap_ci_high": float(high),
    }


# --- sign test and Holm -----------------------------------------------------


def sign_test_pvalue(positive: int, negative: int) -> float:
    """Two-sided exact sign test on the non-zero repeat blocks (1.0 when none).

    # frozen: week9_phase1_16_m3_repulsion_scale_audit.py::holm_summary
    # frozen: week9_phase1_18b_finalize.py::contrasts
    """
    n = int(positive) + int(negative)
    return float(binomtest(int(positive), n, 0.5).pvalue) if n else 1.0


def holm(pvalues: np.ndarray) -> np.ndarray:
    """Holm step-down adjusted p-values (same order as the input).

    Sort ascending; adjusted_(k) = max over j <= k of min(1, (m - j + 1) p_(j)).

    # frozen: week9_phase1_16_m3_repulsion_scale_audit.py::holm_summary
    # frozen: week9_phase1_18b_finalize.py::contrasts
    """
    raw = np.asarray(pvalues, dtype=float)
    order = np.argsort(raw)
    adjusted = np.empty(len(raw))
    running = 0.0
    for rank, position in enumerate(order):
        running = max(running, min(1.0, (len(raw) - rank) * raw[position]))
        adjusted[position] = running
    return adjusted


def holm_reject(pvalues: np.ndarray, alpha: float = 0.05) -> np.ndarray:
    """Boolean rejections: Holm-adjusted p < alpha (strict, as in the archive)."""
    return holm(pvalues) < alpha
