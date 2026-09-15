"""Tests for alse.stats: hierarchical bootstrap, repeat-block bootstrap, paired bootstrap, sign test, Holm, ledger."""

from __future__ import annotations

import importlib
import json

import numpy as np
import pandas as pd
import pytest

from alse import stats
from alse.config import ARCHIVE_OUTPUTS
from alse.io import seed_key, seed_u32, stable_seed
from alse.metrics import aulc as metrics_aulc
from alse.metrics import persistent_crossing as metrics_crossing

W85_OUTPUT = ARCHIVE_OUTPUTS / "week8_5_frozen_confirmation"
P13_OUTPUT = ARCHIVE_OUTPUTS / "week9_phase1_13_fixed_physics_ard_discrepancy"
P13_ROOT = "week9_phase1_13_fixed_physics_ard_discrepancy|v1"  # seed namespace of Phase 1.13
META_COLUMNS = ["protocol_id", "schema_version", "protocol_sha256", "source_hashes_json"]
ARMS = (("binary_margin", 1), ("binary_random", 3), ("binary_uncertainty_repulsion", 1))


def load(archive_src, name: str):
    return importlib.import_module(f"src.{name}")


def read_archive_csv(path) -> pd.DataFrame:
    frame = pd.read_csv(path, float_precision="round_trip")
    return frame.drop(columns=[c for c in META_COLUMNS if c in frame.columns])


# --- synthetic fixtures ----------------------------------------------------------


def synthetic_run_metrics(seed: int = 0, repeats: int = 20, folds: int = 5, continuations: int = 3, horizon: int = 80) -> pd.DataFrame:
    """Run-level table with the columns the Week 8.5 inference reads."""
    rng = np.random.default_rng(seed)
    rows = []
    for repeat in range(1, repeats + 1):
        for fold in range(1, folds + 1):
            for arm, count in ARMS:
                for continuation in range(1, (continuations if arm == "binary_random" else count) + 1):
                    base = 0.80 if arm == "binary_random" else 0.85
                    row = {"run_id": f"w85__r{repeat:02d}_f{fold:02d}", "repeat": repeat, "fold": fold, "arm": arm, "continuation_id": continuation, "horizon": horizon}
                    row["B1_q20_AULC_16_80"] = base + rng.normal(0, 0.03)
                    row["B1_q20_AULC_16_40"] = base - 0.05 + rng.normal(0, 0.03)
                    row["B1_q30_AULC_16_80"] = base + 0.02 + rng.normal(0, 0.03)
                    for label in ("budget40", "terminal"):
                        for subset, n in (("B1_q20", 17), ("B1_q30", 25)):
                            tp, fn, fp = (int(v) for v in rng.integers(0, 4, size=3))
                            tn = n - tp - fn - fp
                            row.update({f"{label}_{subset}_accuracy": (tp + tn) / n, f"{label}_{subset}_recall": tp / max(tp + fn, 1), f"{label}_{subset}_balanced_accuracy": 0.5 * (tp / max(tp + fn, 1) + tn / (tn + fp)), f"{label}_{subset}_false_negative": fn, f"{label}_{subset}_false_positive": fp, f"{label}_{subset}_true_negative": tn, f"{label}_{subset}_true_positive": tp, f"{label}_{subset}_row_count": n})
                    for target in stats.CROSSING_TARGETS:
                        observed = bool(rng.random() < 0.8)
                        crossing = float(rng.integers(16, horizon)) if observed else np.nan
                        row[f"crossing_{target:.2f}"] = crossing
                        row[f"crossing_{target:.2f}_observed"] = observed
                        row[f"restricted_crossing_{target:.2f}"] = crossing if observed else horizon
                    rows.append(row)
    return pd.DataFrame(rows)


def synthetic_trajectory(seed: int = 0, folds: int = 2, horizon: int = 80) -> pd.DataFrame:
    """Per-budget checkpoint rows (one repeat, ``folds`` runs, three arms)."""
    rng = np.random.default_rng(seed)
    rows = []
    for fold in range(1, folds + 1):
        for arm, count in ARMS:
            for continuation in range(1, (2 if arm == "binary_random" else 1) + 1):
                budgets = np.arange(16, horizon + 1)
                curves = {s: np.clip(0.55 + 0.006 * (budgets - 16) + rng.normal(0, 0.04, len(budgets)), 0, 1) for s in ("B1_q20", "B1_q30")}
                for i, budget in enumerate(budgets):
                    row = {"run_id": f"w85__r01_f{fold:02d}", "repeat": 1, "fold": fold, "arm": arm, "continuation_id": continuation, "budget": int(budget)}
                    for subset, n in (("B1_q20", 17), ("B1_q30", 25)):
                        tp, fn, fp = (int(v) for v in rng.integers(0, 4, size=3))
                        row.update({f"{subset}_accuracy": float(curves[subset][i]), f"{subset}_recall": tp / max(tp + fn, 1), f"{subset}_balanced_accuracy": rng.random(), f"{subset}_false_negative": fn, f"{subset}_false_positive": fp, f"{subset}_true_negative": n - tp - fn - fp, f"{subset}_true_positive": tp, f"{subset}_row_count": n})
                    rows.append(row)
    return pd.DataFrame(rows)


def synthetic_decomposition(seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for repeat in range(1, 21):
        for fold in range(1, 6):
            for arm in ("Y00", "Y10", "Y01", "Y11"):
                for endpoint in ("B1_q20_accuracy_AULC_16_80", "B1_q30_accuracy_AULC_16_80"):
                    rows.append({"run_id": f"w85__r{repeat:02d}_f{fold:02d}", "repeat": repeat, "fold": fold, "arm": arm, "endpoint": endpoint, "AULC": 0.8 + rng.normal(0, 0.03)})
    return pd.DataFrame(rows)


# --- fast unit tests ---------------------------------------------------------------


def test_holm_known_values():
    np.testing.assert_allclose(stats.holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])
    np.testing.assert_allclose(stats.holm([0.5, 0.9]), [1.0, 1.0])
    np.testing.assert_allclose(stats.holm([0.02]), [0.02])
    assert stats.holm_reject([0.01, 0.04, 0.03]).tolist() == [True, False, False]


def test_holm_ties_and_monotone():
    raw = np.array([0.02, 0.02, 0.5, 0.001])
    adjusted = stats.holm(raw)
    assert adjusted[0] == adjusted[1]
    assert (adjusted >= raw).all() and (adjusted <= 1).all()
    assert adjusted[np.argsort(raw)].tolist() == sorted(adjusted)


def test_sign_test_pvalue():
    assert stats.sign_test_pvalue(0, 0) == 1.0
    assert stats.sign_test_pvalue(10, 10) == 1.0
    assert stats.sign_test_pvalue(18, 2) == pytest.approx(0.0004024505615234375)
    assert stats.sign_test_pvalue(18, 2) == stats.sign_test_pvalue(2, 18)


def test_repeat_block_bootstrap_matches_manual_derivation():
    values = np.random.default_rng(1).normal(size=20)
    rng = np.random.default_rng(seed_u32(seed_key("root|v1", "bootstrap", "k")))
    means = values[rng.integers(0, 20, size=(500, 20))].mean(axis=1)
    assert stats.repeat_block_bootstrap(values, "k", "root|v1", draws=500) == (float(values.mean()), float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975)))


def test_repeat_block_bootstrap_depends_on_root_and_key():
    values = np.random.default_rng(2).normal(size=20)
    a = stats.repeat_block_bootstrap(values, "k", "root_a|v1", draws=300)
    assert a == stats.repeat_block_bootstrap(values, "k", "root_a|v1", draws=300)
    assert a[1:] != stats.repeat_block_bootstrap(values, "k", "root_b|v1", draws=300)[1:]
    assert a[1:] != stats.repeat_block_bootstrap(values, "other", "root_a|v1", draws=300)[1:]
    assert a[1] <= a[0] <= a[2]
    with pytest.raises(RuntimeError):
        stats.repeat_block_bootstrap(values[:5], "k", "root_a|v1")
    with pytest.raises(RuntimeError):
        stats.repeat_block_bootstrap(np.r_[values[:19], np.nan], "k", "root_a|v1")
    assert stats.repeat_block_bootstrap(values[:5], "k", "root_a|v1", draws=100, blocks=None)[0] == pytest.approx(values[:5].mean())


def test_bootstrap_repeat_ratio_basic():
    num = np.arange(1, 21, dtype=float)
    den = np.full(20, 4.0)
    point, lower, upper = stats.bootstrap_repeat_ratio(num, den, "k", "root|v1", draws=400)
    assert point == pytest.approx(num.sum() / den.sum())
    assert lower <= point <= upper
    with pytest.raises(RuntimeError):
        stats.bootstrap_repeat_ratio(num, np.zeros(20), "k", "root|v1")


def test_repeat_block_contrast_counts_and_sign_test():
    values = np.r_[np.full(15, 0.01), np.zeros(2), np.full(3, -0.02)]
    row = stats.repeat_block_contrast(values, "c", "root|v1", draws=200)
    assert (row["positive_repeat_blocks"], row["zero_repeat_blocks"], row["negative_repeat_blocks"]) == (15, 2, 3)
    assert row["raw_two_sided_sign_p"] == stats.sign_test_pvalue(15, 3)
    assert row["median_difference"] == 0.01 and row["bootstrap_draws"] == 200
    assert row["mean_difference"] == pytest.approx(values.mean())


def test_paired_run_bootstrap_matches_manual_loop():
    differences = np.random.default_rng(3).normal(0.1, 1, size=20)
    rng = np.random.default_rng(123)
    samples = np.array([differences[rng.integers(0, 20, 20)].mean() for _ in range(300)])
    row = stats.paired_run_bootstrap(differences, resamples=300, seed=123)
    assert (row["bootstrap_ci_low"], row["bootstrap_median"], row["bootstrap_ci_high"]) == tuple(np.quantile(samples, [0.025, 0.5, 0.975]))
    assert row["paired_run_count"] == 20 and row["mean_difference"] == float(differences.mean())


def test_hierarchical_bootstrap_shapes_and_identities():
    run_metrics = synthetic_run_metrics()
    draws, summary = stats.hierarchical_bootstrap(run_metrics, draws=25)
    assert list(draws.columns) == ["draw", *stats.HIERARCHICAL_ESTIMANDS] and len(draws) == 25
    assert summary.estimand.tolist() == list(stats.HIERARCHICAL_ESTIMANDS)
    assert (summary.two_sided_95pct_lower <= summary.one_sided_95pct_lower_bound).all()
    assert (summary.one_sided_95pct_lower_bound <= summary.two_sided_95pct_upper).all()
    assert (draws.delta_repulsion_min == np.minimum(draws.delta_repulsion_AULC16_80, draws.delta_repulsion_AULC16_40)).all()
    first, _ = stats.hierarchical_bootstrap(run_metrics, draws=25)
    pd.testing.assert_frame_equal(first, draws)
    with pytest.raises(RuntimeError):
        stats.hierarchical_bootstrap(run_metrics[run_metrics.arm.ne("binary_uncertainty_repulsion")], draws=2)


def test_point_estimands_single_fold_by_hand():
    frame = synthetic_run_metrics(repeats=1, folds=1)
    margin = frame[frame.arm.eq("binary_margin")].iloc[0]
    rep = frame[frame.arm.eq("binary_uncertainty_repulsion")].iloc[0]
    random = frame[frame.arm.eq("binary_random")]
    points = stats.point_estimands(frame)
    assert points["delta_AULC"] == pytest.approx(margin.B1_q20_AULC_16_80 - random.B1_q20_AULC_16_80.mean())
    assert points["multiplier"] == pytest.approx(random["restricted_crossing_0.80"].mean() / margin["restricted_crossing_0.80"])
    assert points["delta_repulsion_min"] == min(points["delta_repulsion_AULC16_80"], points["delta_repulsion_AULC16_40"])
    assert points["delta_repulsion_AULC16_80"] == pytest.approx(rep.B1_q20_AULC_16_80 - margin.B1_q20_AULC_16_80)


def summary_frame(lowers: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame({"estimand": list(lowers), "one_sided_95pct_lower_bound": list(lowers.values())})


@pytest.mark.parametrize(
    "rho, lowers, expected",
    [
        (1.0, {"delta_AULC": 0.03, "delta_Q": 12.0, "multiplier": 1.4, "delta_repulsion_min": 0.02}, ["PASS", "PASS", "PASS", "PASS", "PASS"]),
        (0.83, {"delta_AULC": 0.03, "delta_Q": 12.0, "multiplier": 1.4, "delta_repulsion_min": -0.001}, ["PASS", "QUALIFY", "QUALIFY", None, "NOT_CONFIRMED"]),
        (1.0, {"delta_AULC": 0.01, "delta_Q": -1.0, "multiplier": 0.9, "delta_repulsion_min": 0.02}, [None, "FAIL", "FAIL", "PASS", "NOT_CONFIRMED"]),
    ],
)
def test_decision_ledger_rules(rho, lowers, expected):
    frame = synthetic_run_metrics(repeats=2, folds=2)
    random = frame.arm.eq("binary_random")
    frame.loc[random, "crossing_0.80_observed"] = np.random.default_rng(0).random(random.sum()) < rho
    ledger = stats.decision_ledger(frame, summary_frame(lowers), horizon=80)
    assert ledger.claim.tolist() == ["primary_performance", "query_saving", "multiplier", "repulsion_h_0.15", "overall_primary_confirmation"]
    points = stats.point_estimands(frame)
    for decision, want, claim in zip(ledger.decision, expected, ledger.claim):
        if want is None:  # depends on the sign of the synthetic point estimate
            key = "delta_AULC" if claim == "primary_performance" else None
            positive = points["delta_AULC"] > 0 if key else points["delta_repulsion_AULC16_80"] > 0 and points["delta_repulsion_AULC16_40"] > 0
            want = "QUALIFY" if positive else "FAIL"
        assert decision == want, claim
    assert ledger.rho_random.iloc[0] == pytest.approx(frame.loc[random, "crossing_0.80_observed"].mean())
    assert ledger.pass_threshold.tolist()[:4] == [0.02, 10.0, 1.25, 0.01] and np.isnan(ledger.point_estimate.iloc[-1])


def test_aggregate_repeat_metrics_pooled_accuracy():
    frame = synthetic_run_metrics(repeats=2, folds=3)
    table = stats.aggregate_repeat_metrics(frame)
    assert len(table) == 6 and table.fold_count.tolist() == [3] * 6
    assert table.continuation_count.tolist() == [1, 3, 1, 1, 3, 1]
    group = frame[frame.repeat.eq(1) & frame.arm.eq("binary_random")]
    row = table[table.repeat.eq(1) & table.arm.eq("binary_random")].iloc[0]
    assert row["pooled__terminal_B1_q30_accuracy"] == pytest.approx((group.terminal_B1_q30_true_positive.sum() + group.terminal_B1_q30_true_negative.sum()) / group.terminal_B1_q30_row_count.sum())
    assert row["macro_mean__B1_q20_AULC_16_80"] == pytest.approx(group.B1_q20_AULC_16_80.mean())
    assert "macro_mean__run_id" not in table.columns


def test_random_finite_fraction():
    frame = synthetic_run_metrics(repeats=2, folds=2)
    random = frame[frame.arm.eq("binary_random")]
    assert stats.random_finite_fraction(frame, expected=len(random)) == pytest.approx(random["crossing_0.80_observed"].mean())
    assert stats.random_finite_fraction(frame, expected=None) == stats.random_finite_fraction(frame, expected=12)
    with pytest.raises(RuntimeError):
        stats.random_finite_fraction(frame)


def test_model_path_decomposition_identity():
    wide, repeat, summary = stats.model_path_decomposition(synthetic_decomposition(), "root|v1", draws=200)
    assert len(wide) == 100 and len(repeat) == 20 and summary.effect.tolist() == list(stats.DECOMPOSITION_EFFECTS)
    np.testing.assert_allclose(wide.MODEL + wide.PATH, wide.TOTAL, atol=1e-14)
    np.testing.assert_allclose(wide.ME_A0 + wide.PE_M1, wide.TOTAL, atol=1e-14)
    assert summary.decision.unique().tolist()[0] in {"MODEL_DOMINANT", "PATH_DOMINANT", "MIXED_OR_UNRESOLVED"}
    assert summary.set_index("effect").loc["TOTAL", "mean"] == pytest.approx(wide.TOTAL.mean())


def test_build_run_metrics_columns_and_crossings():
    frame = synthetic_trajectory()
    run_metrics, crossings = stats.build_run_metrics(frame, 80, 80, aulc=metrics_aulc, persistent_crossing=metrics_crossing)
    assert len(run_metrics) == 8 and len(crossings) == 24
    group = frame[frame.run_id.eq("w85__r01_f01") & frame.arm.eq("binary_margin")]
    row = run_metrics[run_metrics.run_id.eq("w85__r01_f01") & run_metrics.arm.eq("binary_margin")].iloc[0]
    assert row.B1_q20_AULC_16_80 == metrics_aulc(group.budget, group.B1_q20_accuracy, 16, 80)
    assert row.terminal_B1_q30_accuracy == group[group.budget.eq(80)].B1_q30_accuracy.iloc[0]
    for target in stats.CROSSING_TARGETS:
        crossing, observed = metrics_crossing(group.budget, group.B1_q20_accuracy, target)
        assert row[f"crossing_{target:.2f}_observed"] == observed
        assert row[f"restricted_crossing_{target:.2f}"] == (crossing if observed else 80)
    assert set(crossings.censoring_label.unique()) <= {"", "80+"}


# --- archive comparisons -----------------------------------------------------------


@pytest.mark.archive
def test_repeat_block_bootstrap_reproduces_phase1_13_contrasts():
    """Exact reproduction of paired_contrasts.csv / model_summary.csv (e.g. M3-H q20 [+0.007201, +0.016149])."""
    repeat = read_archive_csv(P13_OUTPUT / "repeat_metrics.csv")
    contrasts = read_archive_csv(P13_OUTPUT / "paired_contrasts.csv")
    wide = repeat.pivot(index=["repeat", "subset"], columns="model", values="accuracy_AULC_16_80").reset_index()
    assert len(contrasts) == 10
    for row in contrasts.itertuples(index=False):
        left, right = row.contrast.split("-")
        part = wide[wide.subset.eq(row.subset)].sort_values("repeat")
        values = (part[left] - part[right]).to_numpy(float)
        mine = stats.repeat_block_contrast(values, f"contrast|{left}-{right}|{row.subset}", P13_ROOT, draws=int(row.bootstrap_draws))
        assert (mine["mean_difference"], mine["ci_lower"], mine["ci_upper"]) == (row.mean_difference, row.ci_lower, row.ci_upper), row.contrast
        assert (mine["positive_repeat_blocks"], mine["zero_repeat_blocks"], mine["negative_repeat_blocks"]) == (row.positive_repeat_blocks, row.zero_repeat_blocks, row.negative_repeat_blocks)
    headline = contrasts[contrasts.contrast.eq("M3-H") & contrasts.subset.eq("B1_q20")].iloc[0]
    assert (round(headline.ci_lower, 6), round(headline.ci_upper, 6)) == (0.007201, 0.016149)
    summary = read_archive_csv(P13_OUTPUT / "model_summary.csv")
    for row in summary.itertuples(index=False):
        group = repeat[repeat.model.eq(row.model) & repeat.subset.eq(row.subset)].sort_values("repeat")
        mine = stats.repeat_block_bootstrap(group.accuracy_AULC_16_80.to_numpy(), f"summary|{row.model}|{row.subset}", P13_ROOT)
        assert mine == (row.mean_AULC, row.ci_lower, row.ci_upper), (row.model, row.subset)


@pytest.fixture(scope="module")
def week8_5_run_metrics() -> pd.DataFrame:
    return read_archive_csv(W85_OUTPUT / "run_level_metrics.csv")


@pytest.mark.archive
def test_hierarchical_bootstrap_reproduces_week8_5_interval(week8_5_run_metrics):
    """20 000 draws from run_level_metrics.csv reproduce the archived draws and the performance interval [0.030132, 0.044416]."""
    draws, summary = stats.hierarchical_bootstrap(week8_5_run_metrics, draws=20000)
    archived_draws = read_archive_csv(W85_OUTPUT / "hierarchical_bootstrap_draws.csv")
    pd.testing.assert_frame_equal(draws, archived_draws[draws.columns], check_dtype=False, check_exact=True)
    archived = read_archive_csv(W85_OUTPUT / "bootstrap_or_hierarchical_ci.csv")
    assert summary.estimand.tolist() == archived.estimand.tolist()
    for column in ("point_estimate_bootstrap_mean", "one_sided_95pct_lower_bound", "two_sided_95pct_lower", "two_sided_95pct_upper"):
        assert summary[column].tolist() == archived[column].tolist(), column  # bitwise; the contract allows 1e-9
    performance = summary.set_index("estimand").loc["delta_AULC"]
    assert (round(performance.two_sided_95pct_lower, 6), round(performance.two_sided_95pct_upper, 6)) == (0.030132, 0.044416)
    assert performance.one_sided_95pct_lower_bound == pytest.approx(0.031270335477941176, abs=1e-12)


@pytest.mark.archive
def test_decision_ledger_and_rho_reproduce_week8_5(week8_5_run_metrics):
    bootstrap = read_archive_csv(W85_OUTPUT / "bootstrap_or_hierarchical_ci.csv")
    ledger = stats.decision_ledger(week8_5_run_metrics, bootstrap, horizon=160)
    archived = read_archive_csv(W85_OUTPUT / "decision_ledger.csv")
    assert ledger.decision.tolist() == archived.decision.tolist() == ["PASS", "QUALIFY", "QUALIFY", "QUALIFY", "NOT_CONFIRMED"]
    assert ledger.claim.tolist() == archived.claim.tolist()
    for column in ("point_estimate", "one_sided_95pct_lower_bound", "pass_threshold", "rho_random", "horizon"):
        np.testing.assert_allclose(ledger[column].to_numpy(float), archived[column].to_numpy(float), rtol=0, atol=1e-12, equal_nan=True, err_msg=column)
    decision = json.loads((W85_OUTPUT / "adaptive_horizon_decision.json").read_text(encoding="utf-8"))
    final = [d for d in decision["decisions"] if d["horizon"] == 160][0]
    assert stats.random_finite_fraction(week8_5_run_metrics) == pytest.approx(final["rho_random"], abs=1e-12) == pytest.approx(0.831)


@pytest.mark.archive
def test_aggregate_repeat_metrics_reproduces_week8_5(week8_5_run_metrics):
    table = stats.aggregate_repeat_metrics(week8_5_run_metrics)
    archived = read_archive_csv(W85_OUTPUT / "repeat_level_metrics.csv")
    assert set(archived.columns) <= set(table.columns) and len(table) == len(archived) == 60
    assert table[["repeat", "arm"]].to_numpy().tolist() == archived[["repeat", "arm"]].to_numpy().tolist()
    numeric = [c for c in archived.columns if c not in ("repeat", "arm")]
    np.testing.assert_allclose(table[numeric].to_numpy(float), archived[numeric].to_numpy(float), rtol=0, atol=1e-12)


@pytest.mark.archive
def test_hierarchical_bootstrap_matches_archive_function(archive_src):
    w85 = load(archive_src, "week8_5_frozen_sample_efficiency_confirmation")
    run_metrics = synthetic_run_metrics(seed=7)
    draws, summary = stats.hierarchical_bootstrap(run_metrics, draws=20, root=w85.SEED_ROOT)
    archive_draws, archive_summary = w85.hierarchical_bootstrap(run_metrics, draws=20)
    pd.testing.assert_frame_equal(draws, archive_draws, check_exact=True)
    pd.testing.assert_frame_equal(summary, archive_summary, check_exact=True)
    assert stats.point_estimands(run_metrics) == w85.point_estimands(run_metrics)
    bootstrap = summary.assign(one_sided_95pct_lower_bound=[0.03, 5.0, 1.1, 0.0, 0.0, -0.001])
    pd.testing.assert_frame_equal(stats.decision_ledger(run_metrics, bootstrap, 80), w85.decision_ledger(run_metrics, bootstrap, 80), check_exact=True)
    pd.testing.assert_frame_equal(stats.aggregate_repeat_metrics(run_metrics), w85.aggregate_repeat_metrics(run_metrics), check_exact=True)


@pytest.mark.archive
def test_build_run_metrics_matches_archive_function(archive_src):
    w85 = load(archive_src, "week8_5_frozen_sample_efficiency_confirmation")
    frame = synthetic_trajectory(seed=11)
    run_metrics, crossings = stats.build_run_metrics(frame, 80, w85.declared_budgets(80)[-1], aulc=metrics_aulc, persistent_crossing=metrics_crossing)
    archive_metrics, archive_crossings = w85.build_run_metrics(frame, 80)
    pd.testing.assert_frame_equal(run_metrics, archive_metrics, check_dtype=False, check_exact=True)
    pd.testing.assert_frame_equal(crossings, archive_crossings, check_dtype=False, check_exact=True)
    assert run_metrics["crossing_0.80_observed"].sum() >= 1


@pytest.mark.archive
def test_repeat_block_bootstrap_matches_archive_functions(archive_src):
    p11 = load(archive_src, "week9_phase1_11_fixed_mean_discrepancy_gp")
    p13 = load(archive_src, "week9_phase1_13_fixed_physics_ard_discrepancy")
    p8 = load(archive_src, "week9_phase1_8_model_path_decomposition")
    p16 = load(archive_src, "week9_phase1_16_m3_repulsion_scale_audit")
    p18b = load(archive_src, "week9_phase1_18b_finalize")
    rng = np.random.default_rng(5)
    for key in ("contrast|M3-H|B1_q20", "summary|G0|B1_q30", "TOTAL", "checkpoint|B1_q20|40|accuracy|REP_C100"):
        values = 0.8 + rng.normal(0, 0.02, size=20)
        assert stats.repeat_block_bootstrap(values, key, p11.SEED_ROOT, p11.BOOTSTRAP_DRAWS) == p11.bootstrap_interval(values, key)
        assert stats.repeat_block_bootstrap(values, key, p13.SEED_ROOT, p13.BOOTSTRAP_DRAWS) == p13.bootstrap_interval(values, key)
        assert stats.repeat_block_bootstrap(values, key, p8.SEED_ROOT, p8.BOOTSTRAP_DRAWS) == p8.bootstrap_repeat(values, key)
        assert stats.repeat_block_bootstrap(values, key, p16.SEED_ROOT, p16.BOOTSTRAP_DRAWS) == p16.bootstrap(values, key)
        engine = p18b.engine
        mean, median, lower, upper = p18b.bootstrap(values, key)
        row = stats.repeat_block_contrast(values, key, engine.SEED_ROOT, engine.BOOTSTRAP_DRAWS)
        assert (row["mean_difference"], row["median_difference"], row["ci_lower"], row["ci_upper"]) == (mean, median, lower, upper)
        assert engine.BOOTSTRAP_DRAWS == 20000 and p13.BOOTSTRAP_DRAWS == 10000
    numerators = rng.integers(0, 6, size=20).astype(float)
    denominators = rng.integers(1, 10, size=20).astype(float)
    key = "role|40|B1_q20|accuracy"
    assert stats.bootstrap_repeat_ratio(numerators, denominators, key, p13.SEED_ROOT) == p13.bootstrap_repeat_ratio(numerators, denominators, key)


@pytest.mark.archive
def test_holm_matches_phase1_16_holm_summary(archive_src):
    p16 = load(archive_src, "week9_phase1_16_m3_repulsion_scale_audit")
    rng = np.random.default_rng(9)
    rows = []
    for arm in p16.ARMS:
        for subset in ("B1_q20", "B1_q30"):
            for region in ("OVERALL_B16_80", "EARLY_B16_40"):
                positive = int(rng.integers(0, 21))
                negative = int(rng.integers(0, 21 - positive)) if arm != "REP_C400" else 0
                rows.append({"arm": arm, "subset": subset, "region": region, "c": p16.ARM_TO_C.get(arm, 0.0), "delta_vs_M3_MARGIN": rng.normal(), "ci_lower": -1.0, "ci_upper": 1.0, "positive_repeat_blocks": positive, "negative_repeat_blocks": negative})
    inference = pd.DataFrame(rows)
    archive = p16.holm_summary(inference)
    primary = inference[inference.subset.eq("B1_q20") & inference.region.eq("OVERALL_B16_80") & inference.arm.ne("M3_MARGIN")]
    raw = np.array([stats.sign_test_pvalue(p, n) for p, n in zip(primary.positive_repeat_blocks, primary.negative_repeat_blocks)])
    assert archive.arm.tolist() == primary.arm.tolist() and len(archive) == 5
    assert archive.raw_sign_test_p.tolist() == raw.tolist()
    assert archive.holm_adjusted_p.tolist() == stats.holm(raw).tolist()
    assert archive.holm_reject_0_05.tolist() == stats.holm_reject(raw).tolist()


@pytest.mark.archive
def test_contrast_rows_match_phase1_18b_contrasts(archive_src):
    p18b = load(archive_src, "week9_phase1_18b_finalize")
    engine = p18b.engine
    rng = np.random.default_rng(13)
    repeat = pd.DataFrame([{"repeat": r, "model": model, "accuracy_AULC_16_80": 0.84 + rng.normal(0, 0.01)} for r in range(1, 21) for model in p18b.MODELS])
    primary, adjusted = p18b.contrasts(repeat, "B1_q20")
    wide = repeat.pivot(index="repeat", columns="model", values="accuracy_AULC_16_80").sort_index()
    for row in primary.itertuples(index=False):
        left, right = row.contrast.split("-")
        mine = stats.repeat_block_contrast((wide[left] - wide[right]).to_numpy(float), f"B1_q20|{left}-{right}", engine.SEED_ROOT, engine.BOOTSTRAP_DRAWS)
        for column, value in mine.items():
            assert getattr(row, column) == value, (row.contrast, column)
    family = primary[primary.contrast.isin(adjusted.contrast)].set_index("contrast")
    holm_mine = pd.Series(stats.holm(family.raw_two_sided_sign_p.to_numpy()), index=family.index)
    assert adjusted.set_index("contrast").holm_adjusted_p.to_dict() == holm_mine.to_dict()
    assert adjusted["supported_at_0.05"].tolist() == (adjusted.holm_adjusted_p < 0.05).tolist()


@pytest.mark.archive
def test_paired_run_bootstrap_matches_phase6_paired_comparisons(archive_src):
    p6 = load(archive_src, "week7_phase6_real_data_boundary_active_level_set")
    rng = np.random.default_rng(17)
    methods = {"max_depth_random": "max_depth", "max_depth_straddle": "max_depth", "max_depth_randomized_straddle": "max_depth", "binary_random": "binary", "binary_margin": "binary", "binary_uncertainty_repulsion": "binary"}
    metrics = ["common_normalized_aulc__q20_error", "common_normalized_aulc__q30_error", "common_normalized_aulc__balanced_accuracy"]
    rows = []
    for repeat in range(4):
        for fold in range(5):
            for method, formulation in methods.items():
                rows.append({"benchmark_population": "primary_common", "formulation": formulation, "method": method, "run_id": f"primary_common__r{repeat:02d}_f{fold:02d}", **{m: rng.random() for m in metrics}})
    aulc = pd.DataFrame(rows)
    _, bootstrap_rows = p6.paired_comparisons(aulc)
    assert len(bootstrap_rows) == 7 * 3
    for row in bootstrap_rows.itertuples(index=False):
        a = aulc[aulc.method.eq(row.method_a)].set_index("run_id")
        b = aulc[aulc.method.eq(row.method_b)].set_index("run_id")
        runs = sorted(set(a.index) & set(b.index))
        differences = a.loc[runs, row.metric].to_numpy(float) - b.loc[runs, row.metric].to_numpy(float)
        seed = stable_seed(p6.BASE_SEED, row.comparison, row.metric, "paired_bootstrap")
        assert seed == p6.stable_seed(p6.BASE_SEED, row.comparison, row.metric, "paired_bootstrap")
        mine = stats.paired_run_bootstrap(differences, p6.PAIRED_BOOTSTRAP_RESAMPLES, seed)
        assert (mine["bootstrap_ci_low"], mine["bootstrap_median"], mine["bootstrap_ci_high"]) == (row.bootstrap_ci_low, row.bootstrap_median, row.bootstrap_ci_high), (row.comparison, row.metric)
        assert (mine["mean_difference"], mine["median_difference"], mine["paired_run_count"]) == (row.mean_paired_difference_a_minus_b, row.median_paired_difference_a_minus_b, row.paired_run_count)


@pytest.mark.archive
def test_model_path_decomposition_matches_phase1_8_decompose(archive_src):
    p8 = load(archive_src, "week9_phase1_8_model_path_decomposition")
    aulc = synthetic_decomposition(seed=21)
    wide, repeat, summary = stats.model_path_decomposition(aulc, p8.SEED_ROOT, p8.BOOTSTRAP_DRAWS)
    archive_wide, archive_repeat, archive_summary = p8.decompose(aulc)
    pd.testing.assert_frame_equal(wide, archive_wide, check_exact=True)
    pd.testing.assert_frame_equal(repeat, archive_repeat, check_exact=True)
    pd.testing.assert_frame_equal(summary, archive_summary, check_exact=True)
