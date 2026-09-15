"""Tests for alse.metrics: boundary masks/flags, B1/B2/B3, metric dicts, AULC, crossings."""

from __future__ import annotations

import json
import math
import tarfile
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from sklearn.gaussian_process import GaussianProcessClassifier, GaussianProcessRegressor

from alse import metrics
from alse.config import ARCHIVE_OUTPUTS

W85_OUTPUT = ARCHIVE_OUTPUTS / "week8_5_frozen_confirmation"
P6_OUTPUT = ARCHIVE_OUTPUTS / "week7_06_real_data_boundary_active_level_set"
P7_OUTPUT = ARCHIVE_OUTPUTS / "week7_07_final_boundary_hybrid_benchmark"
MARGIN_Q20_AULC_16_80 = 0.8135202205882353  # reproduction gate G0 (binary_margin, B1_q20)


# --- helpers -----------------------------------------------------------------


def synthetic_population(n: int = 40, seed: int = 5) -> pd.DataFrame:
    """Population-shaped frame with a physics-like keyhole rule (both classes >= 2 rows)."""
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame(
        {
            "P": rng.uniform(50, 400, n),
            "VX": rng.uniform(0.2, 2.0, n),
            "LS": rng.uniform(2e-5, 1e-4, n),
            "ST": rng.uniform(300, 900, n),
        }
    )
    frame["experiment_name"] = [f"exp{i:03d}" for i in range(n)]
    frame["partition"] = np.where(np.arange(n) % 3 == 0, "new-data", "old-data-local")
    score = frame["P"] / np.sqrt(frame["VX"] * frame["LS"] ** 3)
    frame["has_keyhole"] = score > score.quantile(0.7)
    return frame[["experiment_name", "partition", "has_keyhole", "P", "VX", "LS", "ST"]]


class FakeGPR:
    def __init__(self, mu, sigma):
        self.mu, self.sigma = np.asarray(mu, float), np.asarray(sigma, float)

    def predict(self, X, return_std=False):
        return (self.mu, self.sigma) if return_std else self.mu


class FakeGPC:
    classes_ = np.array([-1.0, 1.0])

    def __init__(self, p_plus):
        self.p = np.asarray(p_plus, float)

    def predict_proba(self, X):
        return np.column_stack([1.0 - self.p, self.p])


def toy_level_set(seed: int = 0):
    """2-D toy level set with sklearn GPR/GPC surrogates on {-1,+1} labels."""
    rng = np.random.default_rng(seed)

    def f(X):
        return np.sin(3.0 * X[:, 0]) + X[:, 1] - 0.8

    X, X_test = rng.uniform(0, 1, (40, 2)), rng.uniform(0, 1, (60, 2))
    y, y_test = np.where(f(X) >= 0, 1.0, -1.0), np.where(f(X_test) >= 0, 1.0, -1.0)
    gpr = GaussianProcessRegressor(random_state=0).fit(X, f(X))
    gpc = GaussianProcessClassifier(random_state=0).fit(X, y)
    dataset = SimpleNamespace(test_scaled=X_test, test_labels=y_test)
    return gpr, gpc, dataset, np.abs(f(X_test))


def assert_dict_equal(ours: dict, theirs: dict, keys=None) -> None:
    for key in keys if keys is not None else theirs:
        a, b = ours[key], theirs[key]
        if isinstance(b, float) and math.isnan(b):
            assert isinstance(a, float) and math.isnan(a), key
        else:
            assert a == b, (key, a, b)


# --- fast unit tests ---------------------------------------------------------


def test_constants():
    assert metrics.BOUNDARY_QUANTILES == (10, 20, 30) and metrics.UNCERTAINTY_MULTIPLIER == 1.96
    assert metrics.CLASSIFIER_EPSILON == 0.10 and metrics.GPR_PROBABILITY_EPS == 1e-9
    assert metrics.FEATURES == ("P", "VX", "LS", "ST") and metrics.KNN_MIXING_K == 10
    assert metrics.BOUNDARY_IDS == ("B1", "B2", "B3") and metrics.PRIMARY_BOUNDARY_QUANTILES == (20, 30)
    assert metrics.CROSSING_TARGETS == (0.75, 0.80, 0.85) and metrics.PROBABILITY_EPS == 1e-12
    assert metrics.AULC_REGIONS == {
        "EARLY_B16_40": (16, 40), "LATE_B41_80": (41, 80), "EARLY_B16_24": (16, 24),
        "MID_B25_40": (25, 40), "BROAD_B16_40": (16, 40),
    }


def test_boundary_masks_nested_and_threshold():
    values = np.linspace(-1.0, 1.0, 101)
    masks = metrics.boundary_masks(values, 0.0)
    assert list(masks) == [10, 20, 30]
    assert masks[10].sum() == 11 and masks[20].sum() == 21 and masks[30].sum() == 31
    assert (masks[10] <= masks[20]).all() and (masks[20] <= masks[30]).all()
    direct = metrics.boundary_masks(np.abs(values))
    for q in metrics.BOUNDARY_QUANTILES:
        np.testing.assert_array_equal(masks[q], direct[q])
    # cutoff is inclusive
    assert metrics.boundary_masks(np.array([0.0, 1.0, 2.0, 3.0, 4.0]))[30][1]


def test_gpr_p_plus_and_predict_p_plus():
    p = metrics.gpr_p_plus([0.0, 1.96, -1.0], [1.0, 1.0, 0.0])
    assert p[0] == 0.5 and p[1] == pytest.approx(0.975, abs=1e-3) and p[2] == 0.0
    model = FakeGPC([0.2, 0.7])
    np.testing.assert_array_equal(metrics.predict_p_plus(model, None), [0.2, 0.7])
    model.classes_ = np.array([0.0, 2.0])
    with pytest.raises(RuntimeError, match="class \\+1"):
        metrics.predict_p_plus(model, None)


def test_evaluate_budget_gpr_known_values():
    model = FakeGPR([0.5, -0.2, 0.05, -1.0], [0.1, 0.3, 0.1, 0.2])
    masks = {10: np.array([True, False, False, False]), 20: np.array([True, True, False, False])}
    row = metrics.evaluate_budget(model, None, [1, 1, -1, -1], masks, benchmark="toy", budget=7)
    assert list(row)[:2] == ["benchmark", "budget"] and row["benchmark"] == "toy"
    assert row["global_error"] == 0.5 and row["uncertainty_region_fraction"] == 0.5
    p = metrics.gpr_p_plus(model.mu, model.sigma)
    assert row["integrated_bernoulli_uncertainty"] == pytest.approx(float(np.mean(p * (1 - p))))
    assert row["near_boundary_error_q10"] == 0.0 and row["near_boundary_error_q20"] == 0.5
    assert row["near_boundary_test_size_q10"] == 1 and row["near_boundary_test_size_q20"] == 2
    assert row["uncertainty_region_fraction_q10"] == 0.0 and row["uncertainty_region_fraction_q20"] == 0.5


def test_evaluate_budget_gpc_known_values():
    model = FakeGPC([0.9, 0.45, 0.55, 0.1])
    masks = {20: np.array([True, True, False, False])}
    row = metrics.evaluate_budget(model, None, [1, 1, -1, -1], masks, surrogate="gpc")
    assert row["global_error"] == 0.5 and row["uncertainty_region_fraction"] == 0.5
    assert row["integrated_bernoulli_uncertainty"] == pytest.approx(0.16875)
    assert row["near_boundary_error_q20"] == 0.5 and row["integrated_bernoulli_uncertainty_q20"] == pytest.approx(0.16875)
    wide = metrics.evaluate_budget(model, None, [1, 1, -1, -1], masks, surrogate="gpc", epsilon=0.45)
    assert wide["uncertainty_region_fraction"] == 1.0
    with pytest.raises(ValueError, match="surrogate"):
        metrics.evaluate_budget(model, None, [1, 1, -1, -1], masks, surrogate="tree")


def test_deterministic_order_and_rank_fraction():
    values, names = np.array([2.0, 1.0, 2.0, 1.0]), np.array(["b", "d", "a", "c"])
    assert metrics.deterministic_order(values, names, ascending=True).tolist() == [3, 1, 2, 0]
    assert metrics.deterministic_order(values, names, ascending=False).tolist() == [2, 0, 3, 1]
    np.testing.assert_array_equal(metrics.rank_fraction(values, names, ascending=True), [1.0, 0.5, 0.75, 0.25])
    np.testing.assert_array_equal(metrics.rank_fraction(values, names, ascending=False), [0.5, 1.0, 0.25, 0.75])


def test_robust_scaled():
    x = np.array([[1.0, 5.0], [2.0, 5.0], [3.0, 5.0], [4.0, 5.0], [5.0, 5.0]])
    scaled, median, iqr = metrics.robust_scaled(x)
    np.testing.assert_array_equal(median, [3.0, 5.0])
    np.testing.assert_array_equal(iqr, [2.0, 1.0])  # zero IQR -> 1
    np.testing.assert_array_equal(scaled[:, 0], [-1.0, -0.5, 0.0, 0.5, 1.0])
    np.testing.assert_array_equal(scaled[:, 1], 0.0)


def test_class_distance_components():
    x = np.array([[0.0], [1.0], [3.0], [7.0]])
    d_opp, d_same, nearest_opp, nearest_same = metrics.class_distance_components(x, np.array([0, 0, 1, 1]))
    np.testing.assert_array_equal(d_opp, [3.0, 2.0, 2.0, 6.0])
    np.testing.assert_array_equal(d_same, [1.0, 1.0, 4.0, 4.0])
    np.testing.assert_array_equal(nearest_opp, [2, 2, 1, 1])
    np.testing.assert_array_equal(nearest_same, [1, 0, 3, 2])
    with pytest.raises(RuntimeError, match="same-class"):
        metrics.class_distance_components(x, np.array([0, 0, 0, 1]))


def test_empirical_boundary_reference_small():
    population = synthetic_population()
    reference = metrics.build_empirical_boundary_reference(population)
    assert len(reference) == 40 and reference.index.equals(population.index)
    np.testing.assert_array_equal(reference["empirical_boundary_distance"], metrics.b1_distance(population))
    for q in metrics.BOUNDARY_QUANTILES:
        assert reference[f"global_q{q}"].sum() == math.ceil(q / 100 * 40)
    assert (reference["global_q10"] <= reference["global_q20"]).all()
    assert reference["knn_k"].eq(10).all() and reference["knn_positive_fraction"].between(0, 1).all()
    assert reference["knn_label_entropy_bits"].between(0, 1).all()
    assert reference["boundary_rank"].sort_values().tolist() == list(range(1, 41))
    assert (reference["nearest_opposite_label"] != reference["has_keyhole"].astype(int)).all()
    small = metrics.build_empirical_boundary_reference(population.iloc[:6])
    assert small["knn_k"].eq(5).all()


def test_boundary_metrics_small():
    population = synthetic_population()
    frame = metrics.boundary_metrics(population)
    np.testing.assert_array_equal(frame["B1_nearest_opposite_distance"], metrics.b1_distance(population))
    assert frame["B2_local_disagreement_k5"].isin([0, 0.2, 0.4, 0.6, 0.8, 1.0]).all()
    assert frame["B3_relative_class_distance_ratio"].between(0, 1).all()
    ratio = frame["B3_d_opp"] / (frame["B3_d_opp"] + frame["B3_d_same"])
    np.testing.assert_allclose(frame["B3_relative_class_distance_ratio"], ratio, rtol=1e-12)
    for metric in metrics.BOUNDARY_IDS:
        for q in metrics.BOUNDARY_QUANTILES:
            assert frame[f"{metric}_q{q}"].sum() == math.ceil(q / 100 * 40)
        assert frame[f"{metric}_boundary_rank_fraction"].max() == 1.0
    # B2 flags the LARGEST disagreement, B1/B3 the smallest values
    assert frame.loc[frame["B2_q10"], "B2_local_disagreement_k5"].min() >= frame.loc[~frame["B2_q10"], "B2_local_disagreement_k5"].max()
    assert frame.loc[frame["B1_q10"], "B1_nearest_opposite_distance"].max() <= frame.loc[~frame["B1_q10"], "B1_nearest_opposite_distance"].min()
    votes = frame[["B1_q20", "B2_q20", "B3_q20"]].sum(axis=1)
    np.testing.assert_array_equal(frame["consensus_q20"], votes >= 2)
    for feature in metrics.FEATURES:
        assert f"standardized_{feature}" in frame and f"robust_scaled_{feature}" in frame


def test_boundary_flags_and_subset_flags_small():
    population = synthetic_population()
    distances = metrics.b1_distance(population)
    test = list(range(0, 40, 3))  # 14 rows
    flags = metrics.boundary_flags(test, population, distances)
    assert list(flags) == ["B1_q20", "B1_q30"]
    assert flags["B1_q20"].sum() == 3 and flags["B1_q30"].sum() == 5
    assert (flags["B1_q20"] <= flags["B1_q30"]).all()
    assert distances[test][flags["B1_q20"]].max() <= distances[test][~flags["B1_q20"]].min()
    subsets = metrics.subset_flags(test, population, distances)
    assert list(subsets) == ["full81", "B1_q30", "B1_q20"]
    assert subsets["full81"].all() and len(subsets["full81"]) == 14
    np.testing.assert_array_equal(subsets["B1_q20"], flags["B1_q20"])


def test_test_fold_boundary_flags_agree_with_boundary_flags():
    population = synthetic_population()
    reference = metrics.build_empirical_boundary_reference(population)
    test = [5, 17, 2, 33, 21, 9, 38, 0, 12, 26]  # unsorted test order is preserved
    fold = metrics.test_fold_boundary_flags(test, reference)
    assert list(fold) == [10, 20, 30] and all(len(fold[q]) == 10 for q in fold)
    assert fold[10].sum() == 1 and fold[20].sum() == 2 and fold[30].sum() == 3
    w85 = metrics.boundary_flags(test, population, metrics.b1_distance(population))
    np.testing.assert_array_equal(fold[20], w85["B1_q20"])
    np.testing.assert_array_equal(fold[30], w85["B1_q30"])


def test_classification_metrics_known_values():
    labels, preds = [1, 1, 1, 0, 0, 0], [1, 1, 0, 0, 0, 1]
    prob = np.array([0.9, 0.8, 0.4, 0.2, 0.3, 0.7])
    result = metrics.classification_metrics(labels, prob, preds, boundary_flags={20: [1, 0, 1, 0, 0, 1]})
    assert result["true_positive"] == 2 and result["false_negative"] == 1
    assert result["true_negative"] == 2 and result["false_positive"] == 1
    for key in ("balanced_accuracy", "sensitivity", "specificity", "precision", "f1"):
        assert result[key] == pytest.approx(2 / 3), key
    assert result["global_error"] == pytest.approx(1 / 3)
    assert result["roc_auc"] == pytest.approx(8 / 9) and result["brier_score"] == pytest.approx(1.03 / 6)
    assert result["q20_error"] == pytest.approx(2 / 3) and result["q20_count"] == 3 and result["q20_keyhole_count"] == 2
    ranked = metrics.classification_metrics(labels, None, preds, ranking_scores=prob)
    assert ranked["roc_auc"] == pytest.approx(8 / 9) and math.isnan(ranked["brier_score"])
    bare = metrics.classification_metrics(labels, None, preds)
    assert math.isnan(bare["roc_auc"]) and math.isnan(bare["average_precision"]) and "q20_error" not in bare
    single = metrics.classification_metrics([1, 1, 1], [0.2, 0.9, 0.8], [0, 1, 1])
    assert math.isnan(single["roc_auc"]) and math.isnan(single["specificity"]) and single["sensitivity"] == pytest.approx(2 / 3)


def test_regression_metrics_known_values():
    result = metrics.regression_metrics([1, 2, 3, 4], [1, 2, 3, 6])
    assert result == pytest.approx({"mae": 0.5, "rmse": 1.0, "relative_mae": 0.2, "relative_rmse": 0.4, "r2": 0.2})


def test_compute_metrics_known_values():
    result = metrics.compute_metrics(np.array([1, 0, 1, 0, 1]), np.array([0.6, 0.4, 0.3, 0.7, 0.5]), [1, 1, 1, 1, 0])
    assert result == {
        "accuracy": 0.5, "recall": 0.5, "balanced_accuracy": 0.5,
        "false_negative": 1, "false_positive": 1, "true_negative": 1, "true_positive": 1, "row_count": 4,
    }
    assert metrics.compute_metrics(np.array([1, 1]), np.array([0.5, 0.49]), [True, True])["accuracy"] == 0.5


def test_probability_metrics_clips_and_counts():
    truth = np.array([1, 0, 1, 0, 1, 0])
    result = metrics.probability_metrics(truth, [1.0, 0.0, 0.6, 0.7, 0.2, 0.1])
    assert result["row_count"] == 6 and result["accuracy"] == pytest.approx(4 / 6)
    assert result["true_positive"] == 2 and result["false_negative"] == 1 and result["false_positive"] == 1
    assert result["keyhole_recall"] == pytest.approx(2 / 3) and result["conduction_recall"] == pytest.approx(2 / 3)
    assert result["brier_score"] == pytest.approx((0.16 + 0.49 + 0.64 + 0.01) / 6, abs=1e-9)  # clipped 1.0/0.0 add ~0
    assert list(result) == [
        "roc_auc", "pr_auc", "accuracy", "balanced_accuracy", "keyhole_recall", "conduction_recall",
        "brier_score", "false_negative", "false_positive", "true_negative", "true_positive", "row_count",
    ]
    assert math.isnan(metrics.probability_metrics([1, 1], [0.9, 0.8])["roc_auc"])


def test_aulc():
    budgets = np.arange(16, 81)
    assert metrics.aulc(budgets, np.full(65, 0.7)) == pytest.approx(0.7)
    assert metrics.aulc(budgets, budgets / 100.0) == pytest.approx(0.48)
    assert metrics.aulc(budgets, budgets / 100.0, 16, 40) == pytest.approx(0.28)
    # budgets outside the window are ignored, input order is irrelevant
    extended = np.r_[budgets, 82, 84, 100]
    values = np.r_[budgets / 100.0, 5.0, 5.0, 5.0]
    shuffle = np.random.default_rng(0).permutation(len(extended))
    assert metrics.aulc(extended[shuffle], values[shuffle]) == pytest.approx(0.48)
    with pytest.raises(RuntimeError, match="incomplete"):
        metrics.aulc(np.delete(budgets, 10), np.delete(budgets, 10) / 100.0)


def test_region_aulc():
    budgets = np.arange(16, 81)
    values = budgets / 100.0
    assert metrics.region_aulc(budgets, values, "EARLY_B16_40") == pytest.approx(0.28)
    assert metrics.region_aulc(budgets, values, "LATE_B41_80") == pytest.approx(0.605)
    assert metrics.region_aulc(budgets, values, "EARLY_B16_24") == pytest.approx(0.20)
    assert metrics.region_aulc(budgets, values, "MID_B25_40") == pytest.approx(0.325)
    assert metrics.region_aulc(budgets, values, "BROAD_B16_40") == metrics.region_aulc(budgets, values, "EARLY_B16_40")
    with pytest.raises(KeyError):
        metrics.region_aulc(budgets, values, "FULL")


def test_persistent_crossing():
    budgets = np.arange(16, 26)
    values = np.array([0.5, 0.9, 0.7, 0.85, 0.85, 0.9, 0.6, 0.8, 0.8, 0.8])
    assert metrics.persistent_crossing(budgets, values, 0.80) == (19.0, True)
    assert metrics.persistent_crossing(budgets, values, 0.80, consecutive=1) == (17.0, True)
    assert metrics.persistent_crossing(budgets, values, 0.80, consecutive=2) == (19.0, True)
    four, observed_four = metrics.persistent_crossing(budgets, values, 0.80, consecutive=4)
    assert math.isnan(four) and not observed_four  # never four in a row
    crossing, observed = metrics.persistent_crossing(budgets, values, 0.95)
    assert math.isnan(crossing) and observed is False
    assert metrics.persistent_crossing(budgets[::-1], values[::-1], 0.80) == (19.0, True)
    crossing, observed = metrics.persistent_crossing([16, 17], [1.0, 1.0], 0.5)
    assert math.isnan(crossing) and not observed  # fewer than three checkpoints: right-censored


# --- archive comparisons ------------------------------------------------------


@pytest.fixture(scope="module")
def archive_population(archive_src) -> pd.DataFrame:
    import src.week8_5_frozen_sample_efficiency_confirmation as w85

    return w85.load_population()


@pytest.fixture(scope="module")
def frozen_specs(archive_src, archive_population):
    import src.week8_5_frozen_sample_efficiency_confirmation as w85

    specs = w85.build_splits(archive_population)
    assert len(specs) == 100
    return specs


@pytest.fixture(scope="module")
def margin_trajectories() -> pd.DataFrame:
    """Per-budget rows of the 100 frozen binary_margin trajectories (checkpoint bundle)."""
    rows = []
    with tarfile.open(W85_OUTPUT / "week8_5_checkpoint_bundle.tar.gz", "r:gz") as tar:
        for member in tar:
            if member.isfile() and member.name.endswith("__binary_margin__c01.json"):
                payload = json.load(tar.extractfile(member))
                assert payload["complete"] and payload["horizon"] == 160
                rows.extend(payload["rows"])
    frame = pd.DataFrame(rows)
    assert frame["run_id"].nunique() == 100 and len(frame) == 100 * 95
    return frame


@pytest.mark.archive
def test_week4_boundary_masks_and_evaluate_budget_match(archive_src):
    import src.week4_01_boundary_metrics as w401
    import src.week4_06_gp_classifier_surrogate as w406
    import src.week4_08_boundary_weighted_sur as w408

    gpr, gpc, dataset, test_distances = toy_level_set()
    masks = metrics.boundary_masks(test_distances)
    theirs = w401.boundary_masks(test_distances)
    for q in metrics.BOUNDARY_QUANTILES:
        np.testing.assert_array_equal(masks[q], theirs[q])
        np.testing.assert_array_equal(masks[q], w408.boundary_masks(test_distances)[q])
    identity = dict(benchmark="toy", method="straddle", seed=0, budget=40)

    ours = metrics.evaluate_budget(gpr, dataset.test_scaled, dataset.test_labels, masks, **identity)
    ref = w401.evaluate_budget(gp=gpr, dataset=dataset, test_distances=test_distances, test_masks=masks, **identity)
    assert ours["global_error"] == ref["global_error"]
    assert ours["uncertainty_region_fraction"] == ref["latent_uncertainty_region_fraction"]
    for q in metrics.BOUNDARY_QUANTILES:
        assert ours[f"near_boundary_error_q{q}"] == ref[f"near_boundary_error_q{q}"]
        assert ours[f"near_boundary_test_size_q{q}"] == ref[f"near_boundary_test_size_q{q}"]
        assert ours[f"uncertainty_region_fraction_q{q}"] == ref[f"latent_uncertainty_region_fraction_q{q}"]
    config = SimpleNamespace(name="toy", display_name="Toy")
    ref8 = w408.evaluate_budget(
        config=config, surrogate_variant="gpr_fixed_or_existing", acquisition_rule="straddle", seed=0,
        budget=40, model=gpr, dataset=dataset, test_masks=masks, fit_time_seconds=0.0,
    )
    assert_dict_equal(ours, ref8, [k for k in ours if k not in identity])

    ours = metrics.evaluate_budget(gpc, dataset.test_scaled, dataset.test_labels, masks, surrogate="gpc", **identity)
    ref = w406.evaluate_budget(gp=gpc, dataset=dataset, test_masks=masks, **identity)
    assert ours["global_error"] == ref["global_error"]
    assert ours["uncertainty_region_fraction"] == ref["classifier_uncertainty_region_fraction_eps10"]
    for q in metrics.BOUNDARY_QUANTILES:
        assert ours[f"near_boundary_error_q{q}"] == ref[f"near_boundary_error_q{q}"]
        assert ours[f"uncertainty_region_fraction_q{q}"] == ref[f"classifier_uncertainty_region_fraction_q{q}_eps10"]
    ref8 = w408.evaluate_budget(
        config=config, surrogate_variant="gpc_fixed_iso", acquisition_rule="margin", seed=0,
        budget=40, model=gpc, dataset=dataset, test_masks=masks, fit_time_seconds=0.0,
    )
    assert_dict_equal(ours, ref8, [k for k in ours if k not in identity])
    assert 0.0 < ours["global_error"] < 0.5  # the toy surrogate actually learned something


@pytest.mark.archive
def test_phase7_helpers_match_archive(archive_src):
    import src.week7_phase7_final_boundary_hybrid_benchmark as p7

    rng = np.random.default_rng(3)
    values = rng.integers(0, 5, 60).astype(float)  # many ties
    names = np.array([f"exp{rng.integers(0, 1000):04d}" for _ in range(60)])
    for ascending in (True, False):
        np.testing.assert_array_equal(
            metrics.deterministic_order(values, names, ascending=ascending),
            p7.deterministic_order(values, names, ascending=ascending),
        )
        np.testing.assert_array_equal(
            metrics.rank_fraction(values, names, ascending=ascending),
            p7.rank_fraction(values, names, ascending=ascending),
        )
    x = rng.normal(size=(60, 4))
    x[:, 3] = 1.0  # constant column -> IQR floor
    for ours, theirs in zip(metrics.robust_scaled(x), p7.robust_scaled(x)):
        np.testing.assert_array_equal(ours, theirs)
    labels = rng.integers(0, 2, 60)
    for ours, theirs in zip(metrics.class_distance_components(x, labels), p7.class_distance_components(x, labels)):
        np.testing.assert_array_equal(ours, theirs)


@pytest.mark.archive
def test_empirical_boundary_reference_matches_archive(archive_src, archive_population):
    import src.week7_phase6_real_data_boundary_active_level_set as p6

    ours = metrics.build_empirical_boundary_reference(archive_population)
    theirs, _, _ = p6.build_empirical_boundary_reference(archive_population)
    pd.testing.assert_frame_equal(ours, theirs)
    frozen = pd.read_csv(P6_OUTPUT / "empirical_boundary_reference.csv", low_memory=False)
    assert frozen["experiment_name"].tolist() == ours["experiment_name"].tolist()
    np.testing.assert_allclose(ours["empirical_boundary_distance"], frozen["empirical_boundary_distance"], rtol=0, atol=1e-12)
    assert ours["nearest_opposite_experiment"].tolist() == frozen["nearest_opposite_experiment"].tolist()
    for q in metrics.BOUNDARY_QUANTILES:
        np.testing.assert_array_equal(ours[f"global_q{q}"].to_numpy(), frozen[f"global_q{q}"].astype(bool).to_numpy())
    assert ours["global_q10"].sum() == 41 and ours["global_q20"].sum() == 81 and ours["global_q30"].sum() == 122
    np.testing.assert_allclose(ours["knn_positive_fraction"], frozen["knn_positive_fraction"], rtol=0, atol=1e-12)
    np.testing.assert_allclose(ours["standardized_P"], frozen["standardized_P"], rtol=0, atol=1e-12)


@pytest.mark.archive
def test_boundary_metrics_match_archive(archive_src, archive_population):
    import src.week7_phase7_final_boundary_hybrid_benchmark as p7

    ours = metrics.boundary_metrics(archive_population)
    theirs = p7.build_boundary_metrics(archive_population)["reference"]
    pd.testing.assert_frame_equal(ours, theirs)
    frozen = pd.read_csv(P7_OUTPUT / "boundary_metric_reference.csv", low_memory=False)
    assert frozen["experiment_name"].tolist() == ours["experiment_name"].tolist()
    for column in (
        "B1_nearest_opposite_distance", "B2_local_disagreement_k5", "B2_local_disagreement_k10_secondary",
        "B3_relative_class_distance_ratio", "robust_B1_nearest_opposite_distance",
        "robust_B3_relative_class_distance_ratio", "B1_boundary_rank_fraction", "B2_boundary_rank_fraction",
        "B3_boundary_rank_fraction",
    ):
        np.testing.assert_allclose(ours[column], frozen[column], rtol=0, atol=1e-12, err_msg=column)
    flag_columns = [f"{m}_q{q}" for m in metrics.BOUNDARY_IDS for q in metrics.BOUNDARY_QUANTILES] + ["consensus_q20", "consensus_q30"]
    for column in flag_columns:
        np.testing.assert_array_equal(ours[column].to_numpy(), frozen[column].astype(bool).to_numpy(), err_msg=column)
    for metric in metrics.BOUNDARY_IDS:
        assert ours[f"{metric}_q20"].sum() == 81 and ours[f"{metric}_q30"].sum() == 122


@pytest.mark.archive
def test_b1_distance_and_flags_match_archive_for_all_specs(archive_src, archive_population, frozen_specs):
    import src.week7_phase6_real_data_boundary_active_level_set as p6
    import src.week8_5_frozen_sample_efficiency_confirmation as w85
    import src.week9_phase1_7_physics_ridge_residual_gp as p17

    distances = metrics.b1_distance(archive_population)
    np.testing.assert_array_equal(distances, w85.b1_distance(archive_population))
    reference = metrics.build_empirical_boundary_reference(archive_population)
    # Phase 6 empirical boundary distance is the Week 8.5 B1 distance
    np.testing.assert_array_equal(reference["empirical_boundary_distance"].to_numpy(), distances)
    for spec in frozen_specs:
        ours = metrics.boundary_flags(spec.test_indices, archive_population, distances)
        theirs = w85.boundary_flags(spec, archive_population, distances)
        assert list(ours) == list(theirs) == ["B1_q20", "B1_q30"]
        for key in ours:
            np.testing.assert_array_equal(ours[key], theirs[key], err_msg=f"{spec.run_id}/{key}")
        assert len(ours["B1_q20"]) == 81 and ours["B1_q20"].sum() == 17 and ours["B1_q30"].sum() == 25
        subsets = metrics.subset_flags(spec.test_indices, archive_population, distances)
        expected = p17.subset_flags(spec, archive_population, distances)
        assert list(subsets) == list(expected)
        for key in subsets:
            np.testing.assert_array_equal(subsets[key], expected[key], err_msg=f"{spec.run_id}/{key}")
        fold = metrics.test_fold_boundary_flags(spec.test_indices, reference)
        expected_fold = p6.test_boundary_flags(spec, reference)
        for q in metrics.BOUNDARY_QUANTILES:
            np.testing.assert_array_equal(fold[q], expected_fold[q], err_msg=f"{spec.run_id}/q{q}")
        np.testing.assert_array_equal(fold[20], ours["B1_q20"])
        np.testing.assert_array_equal(fold[30], ours["B1_q30"])
        assert fold[10].sum() == 9


@pytest.mark.archive
def test_metric_dicts_match_archive(archive_src):
    import src.week7_phase6_real_data_boundary_active_level_set as p6
    import src.week8_5_frozen_sample_efficiency_confirmation as w85
    import src.week9_phase1_12_gpc_kernel_adequacy as p12
    import src.week9_phase1_7_physics_ridge_residual_gp as p17

    rng = np.random.default_rng(11)
    labels = rng.integers(0, 2, 81)
    for probability in (rng.uniform(0, 1, 81), np.r_[0.0, 1.0, 0.5, rng.uniform(0, 1, 78)]):
        predictions = (probability >= 0.5).astype(int)
        flags = {q: rng.uniform(size=81) < q / 100 for q in metrics.BOUNDARY_QUANTILES}
        ours = metrics.classification_metrics(labels, probability, predictions, boundary_flags=flags)
        theirs = p6.classification_metrics(labels, probability, predictions, boundary_flags=flags)
        assert list(ours) == list(theirs)
        assert_dict_equal(ours, theirs)
        ours = metrics.classification_metrics(labels, None, predictions, ranking_scores=-probability)
        assert_dict_equal(ours, p6.classification_metrics(labels, None, predictions, ranking_scores=-probability))
        flag = rng.uniform(size=81) < 0.3
        assert metrics.compute_metrics(labels, probability, flag) == w85.compute_metrics(labels, probability, flag)
        ours = metrics.probability_metrics(labels, probability)
        assert ours == p12.metric_values(labels, probability)
        assert {k: v for k, v in ours.items() if k != "brier_score"} == p17.metric_values(labels, probability)
    y = rng.normal(size=50)
    y_hat = y + rng.normal(scale=0.3, size=50)
    assert metrics.regression_metrics(y, y_hat) == p6.regression_metrics(y, y_hat)


@pytest.mark.archive
def test_aulc_and_crossings_reproduce_frozen_margin_results(archive_src, margin_trajectories):
    import src.week8_5_frozen_sample_efficiency_confirmation as w85

    run_level = pd.read_csv(W85_OUTPUT / "run_level_metrics.csv", low_memory=False)
    stored = run_level[run_level["arm"].eq("binary_margin")].set_index("run_id")
    assert len(stored) == 100
    per_run: dict[str, float] = {}
    for run_id, group in margin_trajectories.groupby("run_id", sort=True):
        budgets, q20, q30 = group["budget"].to_numpy(), group["B1_q20_accuracy"].to_numpy(), group["B1_q30_accuracy"].to_numpy()
        per_run[run_id] = metrics.aulc(budgets, q20, 16, 80)
        assert per_run[run_id] == w85.aulc(group, "B1_q20_accuracy", 16, 80)
        assert per_run[run_id] == pytest.approx(stored.loc[run_id, "B1_q20_AULC_16_80"], abs=1e-12)
        assert metrics.aulc(budgets, q20, 16, 40) == pytest.approx(stored.loc[run_id, "B1_q20_AULC_16_40"], abs=1e-12)
        assert metrics.aulc(budgets, q30, 16, 80) == pytest.approx(stored.loc[run_id, "B1_q30_AULC_16_80"], abs=1e-12)
        for target in metrics.CROSSING_TARGETS:
            crossing, observed = metrics.persistent_crossing(budgets, q20, target)
            assert (crossing, observed) == w85.persistent_crossing(group, "B1_q20_accuracy", target) or (
                math.isnan(crossing) and not observed and not w85.persistent_crossing(group, "B1_q20_accuracy", target)[1]
            )
            assert observed == bool(stored.loc[run_id, f"crossing_{target:.2f}_observed"])
            if observed:
                assert crossing == stored.loc[run_id, f"crossing_{target:.2f}"]
            else:
                assert math.isnan(stored.loc[run_id, f"crossing_{target:.2f}"])
    assert abs(float(np.mean(list(per_run.values()))) - MARGIN_Q20_AULC_16_80) < 1e-9
    assert abs(float(stored["B1_q20_AULC_16_80"].mean()) - MARGIN_Q20_AULC_16_80) < 1e-9


@pytest.mark.archive
def test_aulc_regions_match_archive_budget_grids(archive_src, margin_trajectories):
    import src.week9_phase1_13_fixed_physics_ard_discrepancy as p13
    import src.week9_phase1_14_m3_margin_acquisition as p14

    for module in (p13, p14):
        assert metrics.AULC_REGIONS["EARLY_B16_40"] == (module.EARLY_BUDGETS[0], module.EARLY_BUDGETS[-1])
        assert metrics.AULC_REGIONS["LATE_B41_80"] == (module.LATE_BUDGETS[0], module.LATE_BUDGETS[-1])
        assert list(module.BUDGETS) == list(range(16, 81))
    group = margin_trajectories[margin_trajectories["run_id"].eq("w85__r01_f01")].sort_values("budget")
    for region, (start, end) in metrics.AULC_REGIONS.items():
        # the archive formula: trapezoid over the region grid / (budgets[-1] - budgets[0])
        part = group[group["budget"].between(start, end)]
        expected = float(np.trapezoid(part["B1_q20_accuracy"], part["budget"]) / (end - start))
        assert metrics.region_aulc(group["budget"], group["B1_q20_accuracy"], region) == pytest.approx(expected, abs=1e-15)
