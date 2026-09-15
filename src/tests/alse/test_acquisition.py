"""Tests for alse.acquisition: fast unit checks plus archive parity (@pytest.mark.archive)."""

from __future__ import annotations

import hashlib
import importlib
from types import SimpleNamespace

import numpy as np
import pytest
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel

from alse import acquisition as acq

SEEDS = (0, 1, 2)


def problem(seed: int, n: int = 300, d: int = 2, labelled: int = 20, quantise: bool = True) -> SimpleNamespace:
    """Random pool with a labelled subset; quantised scores create many exact ties."""
    rng = np.random.default_rng(seed)
    pool = rng.uniform(0.0, 1.0, size=(n, d))
    labelled_idx = np.sort(rng.choice(n, labelled, replace=False))
    unlabelled = np.setdiff1d(np.arange(n), labelled_idx)
    p_all = rng.uniform(0.0, 1.0, n)
    mu_all = rng.normal(0.0, 1.0, n)
    sigma_all = rng.uniform(0.05, 1.0, n)
    if quantise:
        p_all, mu_all, sigma_all = np.round(p_all, 1), np.round(mu_all, 1), np.round(sigma_all, 1)
    return SimpleNamespace(
        pool=pool,
        labelled=labelled_idx,
        unlabelled=unlabelled,
        p=p_all[unlabelled],
        mu=mu_all[unlabelled],
        sigma=sigma_all[unlabelled],
        q=np.round(rng.uniform(0.0, 1.0, len(unlabelled)), 1),
    )


def lookahead_problem(seed: int = 0, n: int = 80, labelled: int = 12) -> SimpleNamespace:
    """Small 2D pool with a fitted GPR stand-in for the lookahead rule."""
    rng = np.random.default_rng(seed)
    pool = rng.uniform(0.0, 1.0, size=(n, 2))
    labels = np.where(pool[:, 0] + 0.5 * pool[:, 1] >= 0.7, 1.0, -1.0)
    while True:
        labelled_idx = np.sort(rng.choice(n, labelled, replace=False))
        if np.unique(labels[labelled_idx]).size == 2:
            break
    unlabelled = np.setdiff1d(np.arange(n), labelled_idx)
    kernel = ConstantKernel(1.0, (0.1, 10.0)) * RBF(0.2, (0.08, 1.0)) + WhiteKernel(1e-4, "fixed")
    gp = GaussianProcessRegressor(kernel=kernel, alpha=1e-6, normalize_y=False, random_state=seed)
    gp.fit(pool[labelled_idx], labels[labelled_idx])
    mu, sigma = gp.predict(pool[unlabelled], return_std=True)
    return SimpleNamespace(pool=pool, labels=labels, labelled=labelled_idx, unlabelled=unlabelled, gp=gp, mu=mu, sigma=sigma)


# --- fast unit tests ------------------------------------------------------------------


def test_argmax_position_breaks_ties_by_smallest_candidate():
    candidates = np.array([40, 10, 30, 20])
    scores = np.array([1.0, 1.0, 0.5, 1.0])
    assert acq.argmax_position(candidates, scores) == 1
    assert acq.argmax_index(candidates, scores) == 10
    with pytest.raises(RuntimeError):
        acq.argmax_index(candidates, np.array([1.0, np.nan, 0.0, 0.0]))


def test_shortlist_size_matches_phase6_min_max_form():
    for n in range(1, 400):
        expected = min(n, max(acq.MIN_SHORTLIST_SIZE, int(np.ceil(acq.GATE_FRACTION * n))))
        assert acq.shortlist_size(n, acq.GATE_FRACTION, acq.MIN_SHORTLIST_SIZE) == expected


def test_normalisers_and_flat_inputs():
    values = np.array([2.0, 4.0, 3.0])
    assert np.allclose(acq.normalize_scores_week4(values), [0.0, 1.0, 0.5])
    assert np.allclose(acq.normalize_scores(values), [0.0, 1.0, 0.5])
    assert np.all(acq.normalize_scores_week4(np.full(4, 0.3)) == 0.0)
    assert np.all(acq.normalize_scores(np.full(4, 0.3)) == 0.0)


def test_rng_key_grammar_replicates_archive_hashes():
    def archive_key(text: str) -> int:
        return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "little") % (2**32)

    for salt in ("week2", "week3_4d", "week3_4d_ackley"):
        expected = np.random.default_rng(archive_key(f"3:straddle:{salt}")).integers(2**31)
        assert acq.rng_for_method(3, "straddle", salt).integers(2**31) == expected
    for salt in ("week5", "week6_classifier", "week7", "week7_1"):
        expected = np.random.default_rng(archive_key(f"3:branin:margin:{salt}")).integers(2**31)
        assert acq.rng_for_method(3, "margin", salt, "branin").integers(2**31) == expected
        with pytest.raises(RuntimeError):
            acq.rng_for_method(3, "margin", salt)
    draws = {salt: acq.rng_for_method(0, "m", salt, "b").integers(2**31) for salt in acq.RNG_SALTS}
    assert len(set(draws.values())) == len(acq.RNG_SALTS)
    with pytest.raises(RuntimeError):
        acq.rng_for_method(0, "m", "week99")


def test_rng_for_benchmark_method_dispatch():
    assert acq.rng_for_benchmark_method(1, "straddle", "branin", "week5").integers(9) == acq.rng_for_method(1, "straddle", "week2").integers(9)
    assert acq.rng_for_benchmark_method(1, "random", "ackley", "week5").integers(9) == acq.rng_for_method(1, "random", "week3_4d_ackley").integers(9)
    week5 = acq.rng_for_benchmark_method(1, "diversified_straddle", "branin", "week5").integers(2**31)
    assert week5 == acq.rng_for_method(1, "diversified_straddle", "week5", "branin").integers(2**31)


def test_expected_feasibility_is_translation_invariant_and_nonnegative():
    case = problem(0, quantise=False)
    base = acq.expected_feasibility_scores(case.mu, case.sigma)
    assert np.all(base >= 0.0)
    assert np.allclose(acq.expected_feasibility_scores(case.mu + 3.5, case.sigma, 3.5), base, atol=1e-12)


def test_choose_next_index_reproducible_and_validates():
    case = problem(1)
    a = acq.choose_next_index("randomized_straddle", case.unlabelled, case.mu, case.sigma, acq.rng_for_method(1, "randomized_straddle"))
    b = acq.choose_next_index("randomized_straddle", case.unlabelled, case.mu, case.sigma, acq.rng_for_method(1, "randomized_straddle"))
    assert a == b and a.index in case.unlabelled
    with pytest.raises(ValueError):
        acq.choose_next_index("nope", case.unlabelled, case.mu, case.sigma, np.random.default_rng(0))
    with pytest.raises(ValueError):
        acq.choose_next_index("straddle", case.unlabelled, None, None, np.random.default_rng(0))


def test_shortlist_vs_pool_normalisation_split():
    case = problem(2)
    shortlist = acq.uncertainty_repulsion_scores(case.p, case.unlabelled, case.pool, case.labelled, normalise="shortlist")
    pool = acq.uncertainty_repulsion_scores(case.p, case.unlabelled, case.pool, case.labelled, normalise="pool")
    assert np.array_equal(shortlist["positions"], pool["positions"])
    assert np.allclose(shortlist["repulsion"], pool["repulsion"])
    assert not np.allclose(shortlist["normalized_uncertainty"], pool["normalized_uncertainty"])
    full_scores, _, _ = acq.classifier_repulsion_scores(case.p, case.unlabelled, case.pool, case.labelled)
    assert np.allclose(full_scores[pool["positions"]], pool["scores"])
    with pytest.raises(RuntimeError):
        acq.uncertainty_repulsion_scores(case.p, case.unlabelled, case.pool, case.labelled, normalise="other")


def test_binary_margin_ties_go_to_lowest_row_index():
    candidates = np.array([7, 3, 9])
    probabilities = np.array([0.5, 0.5, 0.9])
    index, info = acq.choose_binary_candidate("binary_margin", candidates, probabilities, np.zeros((10, 2)), [0])
    assert index == 3 and info["selected_uncertainty_score"] == 1.0
    assert acq.choose_gpc_margin(candidates, probabilities) == 3
    assert acq.choose_m3_margin(candidates, probabilities, np.zeros((10, 2)), [0])[0] == 3


def test_hybrid_gate_with_tiny_pool_returns_phase6_choice():
    case = problem(3, n=40, labelled=36)
    threshold = float(np.median(case.mu))
    index, info = acq.choose_hybrid_candidate("gate", case.unlabelled, case.p, case.mu, case.sigma, threshold, case.pool, case.labelled)
    assert info["gate_count"] == 1 and info["selected_equals_binary_phase6_choice"]
    assert index == acq.choose_binary_candidate("binary_uncertainty_repulsion", case.unlabelled, case.p, case.pool, case.labelled)[0]
    with pytest.raises(ValueError):
        acq.choose_hybrid_candidate("other", case.unlabelled, case.p, case.mu, case.sigma, threshold, case.pool, case.labelled)


def test_choose_repulsion_rejects_scales_outside_grid():
    case = problem(4)
    with pytest.raises(RuntimeError):
        acq.choose_repulsion(case.unlabelled, case.p, case.pool, case.labelled, 3.0)
    index, info = acq.choose_repulsion(case.unlabelled, case.p, case.pool, case.labelled, 1.0)
    assert index in case.unlabelled and info["lambda_B"] == info["s_B"]


# --- archive parity --------------------------------------------------------------------

ARCHIVE_MODULES = {
    "ar": "acquisition_rules",
    "w402": "week4_02_diversified_straddle",
    "w403": "week4_03_boundary_gated_diversified_straddle",
    "w404": "week4_04_lookahead_boundary_uncertainty",
    "w406": "week4_06_gp_classifier_surrogate",
    "w408": "week4_08_boundary_weighted_sur",
    "w409": "week4_09_gpc_bernoulli_sur_validation",
    "p6": "week7_phase6_real_data_boundary_active_level_set",
    "p7": "week7_phase7_final_boundary_hybrid_benchmark",
    "p15": "week9_phase1_5_h_physics_confirmation",
    "p14": "week9_phase1_14_m3_margin_acquisition",
    "p16": "week9_phase1_16_m3_repulsion_scale_audit",
}


@pytest.fixture(scope="module")
def arch(archive_src):
    return SimpleNamespace(**{key: importlib.import_module(f"src.{name}") for key, name in ARCHIVE_MODULES.items()})


def same_metadata(mine: dict, theirs: dict, keys: tuple[str, ...]) -> None:
    for key in keys:
        assert mine[key] == pytest.approx(theirs[key], abs=1e-12, rel=0), key


@pytest.mark.archive
def test_rng_salts_match_archive(arch):
    for seed in SEEDS:
        for method in acq.METHOD_ORDER:
            assert acq.rng_for_method(seed, method, "week2").integers(2**31) == arch.ar.rng_for_method(seed, method).integers(2**31)
            for benchmark, module in (("branin", arch.w402), ("ackley", arch.w403), ("hartmann", arch.w404)):
                assert (
                    acq.rng_for_benchmark_method(seed, method, benchmark, "week5").integers(2**31)
                    == module.rng_for_experiment_method(seed, method, benchmark).integers(2**31)
                )
        assert (
            acq.rng_for_method(seed, "diversified_straddle", "week5", "ackley").integers(2**31)
            == arch.w402.rng_for_experiment_method(seed, "diversified_straddle", "ackley").integers(2**31)
        )
        assert (
            acq.rng_for_method(seed, "classifier_margin", "week6_classifier", "branin").integers(2**31)
            == arch.w406.rng_for_experiment_method(seed, "classifier_margin", "branin").integers(2**31)
        )
        assert (
            acq.rng_for_benchmark_method(seed, "gpc_bernoulli_sur_refit", "hartmann", "week7").integers(2**31)
            == arch.w408.rng_for_method(seed, "gpc_bernoulli_sur_refit", "hartmann").integers(2**31)
        )
        assert (
            acq.rng_for_method(seed, "random_classifier", "week7_1", "branin").integers(2**31)
            == arch.w409.stable_rng(seed, "branin", "random_classifier").integers(2**31)
        )


@pytest.mark.archive
def test_gpr_score_functions_match_archive(arch):
    case = problem(0, quantise=False)
    assert np.allclose(acq.smallest_abs_mu_scores(case.mu), arch.ar.smallest_abs_mu_scores(case.mu), atol=1e-12)
    assert np.allclose(acq.straddle_scores(case.mu, case.sigma), arch.ar.straddle_scores(case.mu, case.sigma), atol=1e-12)
    assert np.allclose(acq.randomized_straddle_scores(case.mu, case.sigma, 2.7), arch.ar.randomized_straddle_scores(case.mu, case.sigma, 2.7), atol=1e-12)
    assert np.allclose(acq.expected_feasibility_scores(case.mu, case.sigma), arch.ar.expected_feasibility_scores(case.mu, case.sigma), atol=1e-12)
    tau = 0.37
    assert np.allclose(acq.expected_feasibility_scores(case.mu, case.sigma, tau), arch.p6.expected_feasibility_scores(case.mu, case.sigma, tau), atol=1e-12)
    assert np.allclose(acq.max_depth_straddle_scores(case.mu, case.sigma, tau), arch.p7.max_depth_straddle_scores(case.mu, case.sigma, tau), atol=1e-12)


@pytest.mark.archive
def test_choose_next_index_all_five_rules_match_archive(arch):
    for seed in SEEDS:
        case = problem(seed)
        for method in acq.METHOD_ORDER:
            mine = acq.choose_next_index(method, case.unlabelled, case.mu, case.sigma, acq.rng_for_method(seed, method))
            theirs = arch.ar.choose_next_index(method, case.unlabelled, case.mu, case.sigma, arch.ar.rng_for_method(seed, method))
            assert mine.index == theirs.index
            assert mine.metadata["selected_position"] == theirs.metadata["selected_position"]
            same_metadata(mine.metadata, theirs.metadata, tuple(k for k in ("selected_score", "beta") if k in theirs.metadata))


@pytest.mark.archive
def test_diversified_straddle_matches_archive(arch):
    for seed in SEEDS:
        case = problem(seed)
        mine = acq.choose_diversified_straddle(case.unlabelled, case.mu, case.sigma, case.pool, list(case.labelled))
        theirs = arch.w402.choose_diversified_straddle(
            unlabelled_indices=case.unlabelled, mu=case.mu, sigma=case.sigma, pool_scaled=case.pool,
            labelled_indices=list(case.labelled), alpha=arch.w402.DIVERSIFIED_ALPHA,
        )
        assert mine[0] == theirs[0]
        same_metadata(mine[1], theirs[1], ("selected_position", "selected_score", "selected_raw_straddle", "selected_raw_diversity"))


@pytest.mark.archive
def test_gated_diversified_straddle_matches_archive(arch):
    for seed in SEEDS:
        case = problem(seed)
        mine = acq.choose_boundary_gated_diversified_straddle(case.unlabelled, case.mu, case.sigma, case.pool, list(case.labelled))
        theirs = arch.w403.choose_boundary_gated_diversified_straddle(
            unlabelled_indices=case.unlabelled, mu=case.mu, sigma=case.sigma, pool_scaled=case.pool,
            labelled_indices=list(case.labelled), gate_fraction=arch.w403.BOUNDARY_GATED_GATE_FRACTION,
            beta=arch.w403.BOUNDARY_GATED_BETA, min_shortlist_size=arch.w403.BOUNDARY_GATED_MIN_SHORTLIST_SIZE,
        )
        assert mine[0] == theirs[0]
        same_metadata(mine[1], theirs[1], ("shortlist_size", "selected_position", "selected_shortlist_position", "selected_gated_score", "selected_raw_diversity"))


@pytest.mark.archive
def test_lookahead_matches_archive(arch):
    for seed in (0, 1):
        case = lookahead_problem(seed)
        mine = acq.choose_lookahead_boundary_uncertainty_reduction(
            case.unlabelled, case.mu, case.sigma, case.pool, case.labels, list(case.labelled), case.gp, seed
        )
        theirs = arch.w404.choose_lookahead_boundary_uncertainty_reduction(
            unlabelled_indices=case.unlabelled, mu=case.mu, sigma=case.sigma,
            dataset=SimpleNamespace(pool_scaled=case.pool, pool_labels=case.labels),
            labelled_indices=list(case.labelled), current_gp=case.gp, seed=seed,
            shortlist_size=arch.w404.LOOKAHEAD_SHORTLIST_SIZE,
        )
        assert mine[0] == theirs[0]
        same_metadata(mine[1], theirs[1], (
            "shortlist_size", "current_aggregate_uncertainty", "selected_position", "selected_p_plus",
            "selected_u_plus", "selected_u_minus", "selected_expected_uncertainty_reduction",
        ))
        assert np.allclose(acq.boundary_uncertainty_values(case.mu, case.sigma), arch.w404.boundary_uncertainty_values(case.mu, case.sigma), atol=1e-12)


@pytest.mark.archive
def test_classifier_candidate_matches_week4_06(arch):
    pairs = (("margin", "classifier_margin"), ("entropy", "classifier_entropy"), ("gated_diversity", "classifier_gated_diversity"), ("uncertainty_repulsion", "classifier_uncertainty_repulsion"), ("random", "random"))
    for seed in SEEDS:
        case = problem(seed)
        assert np.allclose(acq.classifier_uncertainty_score(case.p), arch.w406.classifier_uncertainty_score(case.p), atol=1e-12)
        assert np.allclose(acq.binary_entropy(case.p), arch.w406.binary_entropy(case.p), atol=1e-12)
        for mine_name, theirs_name in pairs:
            rng_mine = acq.rng_for_method(seed, theirs_name, "week6_classifier", "branin")
            rng_theirs = arch.w406.rng_for_experiment_method(seed, theirs_name, "branin")
            mine = acq.choose_classifier_candidate(mine_name, case.unlabelled, case.p, case.pool, list(case.labelled), rng_mine)
            theirs = arch.w406.choose_classifier_candidate(
                method=theirs_name, unlabelled_indices=case.unlabelled, p_plus=case.p, pool_scaled=case.pool,
                labelled_indices=list(case.labelled), rng=rng_theirs,
            )
            assert mine[0] == theirs[0], (seed, mine_name)
            same_metadata(mine[1], theirs[1], tuple(k for k in ("selected_position", "selected_uncertainty_score", "selected_entropy", "selected_score", "selected_raw_diversity", "selected_repulsion", "shortlist_size") if k in theirs[1]))


@pytest.mark.archive
def test_pool_normalised_repulsion_matches_week4_08_and_09(arch):
    for seed in SEEDS:
        case = problem(seed)
        mine_scores, mine_u, mine_rep = acq.classifier_repulsion_scores(case.p, case.unlabelled, case.pool, list(case.labelled))
        for module in (arch.w408, arch.w409):
            theirs_scores, theirs_u, theirs_rep = module.classifier_repulsion_scores(
                p_plus=case.p, unlabelled_indices=case.unlabelled, pool_scaled=case.pool, labelled_indices=list(case.labelled)
            )
            assert np.allclose(mine_scores, theirs_scores, atol=1e-12)
            assert np.allclose(mine_u, theirs_u, atol=1e-12) and np.allclose(mine_rep, theirs_rep, atol=1e-12)
        mine = acq.choose_classifier_candidate("uncertainty_repulsion", case.unlabelled, case.p, case.pool, list(case.labelled), normalise="pool")
        w408 = arch.w408.choose_classifier_candidate(
            method="classifier_uncertainty_repulsion", unlabelled_indices=case.unlabelled, p_plus=case.p,
            pool_scaled=case.pool, labelled_indices=list(case.labelled),
        )
        w409 = arch.w409.choose_classifier_baseline(
            method="classifier_uncertainty_repulsion", unlabelled_indices=case.unlabelled, p_plus=case.p,
            dataset=SimpleNamespace(pool_scaled=case.pool), labelled_indices=list(case.labelled), rng=np.random.default_rng(0),
        )
        assert mine[0] == w408[0] == w409[0]
        same_metadata(mine[1], w408[1], ("selected_position", "selected_shortlist_position", "selected_score", "selected_repulsion", "shortlist_size"))
        same_metadata(mine[1], w409[1], ("selected_position", "selected_score"))
        shortlist = acq.choose_classifier_candidate("uncertainty_repulsion", case.unlabelled, case.p, case.pool, list(case.labelled))
        assert shortlist[1]["normalisation"] == "shortlist" and mine[1]["normalisation"] == "pool"


@pytest.mark.archive
def test_choose_binary_candidate_matches_phase6(arch):
    for seed in SEEDS:
        case = problem(seed, d=4)
        for method in ("binary_margin", "binary_uncertainty_repulsion"):
            mine = acq.choose_binary_candidate(method, case.unlabelled, case.p, case.pool, list(case.labelled))
            theirs = arch.p6.choose_binary_candidate(
                method=method, candidate_indices=case.unlabelled, probabilities=case.p, pool_scaled=case.pool, queried_indices=list(case.labelled)
            )
            assert mine[0] == theirs[0]
            same_metadata(mine[1], theirs[1], tuple(k for k in ("selected_position", "selected_uncertainty_score", "selected_score", "selected_repulsion", "selected_distance_to_queried", "shortlist_size") if k in theirs[1]))
        assert acq.argmax_position(case.unlabelled, case.p) == arch.p6.deterministic_argmax(case.unlabelled, case.p)
        assert np.allclose(acq.normalize_scores(case.p), arch.p6.normalize_scores(case.p), atol=1e-12)


@pytest.mark.archive
def test_choose_continuous_candidate_matches_phase6_with_online_tau(arch):
    methods = ("max_depth_boundary_proximity", "max_depth_straddle", "max_depth_randomized_straddle", "max_depth_expected_feasibility")
    for seed in SEEDS:
        case = problem(seed, quantise=False)
        for tau in (float(np.median(case.mu)), float(np.percentile(case.mu, 80))):
            for method in methods:
                mine = acq.choose_continuous_candidate(method, case.unlabelled, case.mu, case.sigma, tau, np.random.default_rng(seed))
                theirs = arch.p6.choose_continuous_candidate(
                    method=method, candidate_indices=case.unlabelled, mu=case.mu, sigma=case.sigma, threshold=tau, rng=np.random.default_rng(seed)
                )
                assert mine[0] == theirs[0], (seed, method, tau)
                assert mine[1]["acquisition_definition"] == theirs[1]["acquisition_definition"]
                same_metadata(mine[1], theirs[1], tuple(k for k in ("selected_position", "selected_score", "selected_abs_mean_minus_threshold", "chi_square_df2_draw") if k in theirs[1]))


@pytest.mark.archive
def test_hybrid_rules_match_phase7(arch):
    for seed in SEEDS:
        case = problem(seed, n=200, d=4, labelled=16, quantise=False)
        case.p = np.round(case.p, 2)
        depth_mu = 10.0 * case.mu + 50.0
        depth_sigma = 10.0 * case.sigma
        tau = float(np.median(depth_mu))
        mine_priority = acq.phase6_binary_priority(case.unlabelled, case.p, case.pool, list(case.labelled))
        theirs_priority = arch.p7.phase6_binary_priority(
            candidate_indices=case.unlabelled, probabilities=case.p, pool_scaled=case.pool, queried_indices=list(case.labelled)
        )
        for key in ("ordered_indices", "ordered_positions", "phase6_shortlist_flag"):
            assert np.array_equal(mine_priority[key], theirs_priority[key]), key
        for key in ("percentile_rank", "fallback_full_score", "repulsion", "distance_to_queried"):
            assert np.allclose(mine_priority[key], theirs_priority[key], atol=1e-12), key
        assert np.allclose(mine_priority["phase6_shortlist_score"], theirs_priority["phase6_shortlist_score"], atol=1e-12, equal_nan=True)
        assert mine_priority["phase6_exact_choice"] == theirs_priority["phase6_exact_choice"]
        mine_rank, mine_order = acq.deterministic_percentile_rank(case.unlabelled, depth_mu)
        theirs_rank, theirs_order = arch.p7.deterministic_percentile_rank(case.unlabelled, depth_mu)
        assert np.array_equal(mine_order, theirs_order) and np.allclose(mine_rank, theirs_rank, atol=1e-12)
        for mine_name, theirs_name in (("gate", arch.p7.M3_GATE), ("rank_fusion", arch.p7.M4_FUSION)):
            mine = acq.choose_hybrid_candidate(mine_name, case.unlabelled, case.p, depth_mu, depth_sigma, tau, case.pool, list(case.labelled))
            theirs = arch.p7.choose_hybrid_candidate(
                method=theirs_name, candidate_indices=case.unlabelled, binary_probabilities=case.p, depth_mu=depth_mu,
                depth_sigma=depth_sigma, threshold=tau, pool_scaled=case.pool, queried_indices=list(case.labelled),
            )
            assert mine[0] == theirs[0], (seed, mine_name)
            same_metadata(mine[1], theirs[1], tuple(k for k in ("gate_count", "selected_binary_priority_percentile", "selected_fusion_score", "selected_depth_straddle_score", "selected_binary_probability") if k in theirs[1]))
            assert mine[1]["selected_equals_binary_phase6_choice"] == theirs[1]["selected_equals_binary_phase6_choice"]
        assert acq.HYBRID_GATE == arch.p7.M3_GATE and acq.HYBRID_FUSION == arch.p7.M4_FUSION


@pytest.mark.archive
def test_week9_margin_rules_match_archive(arch):
    for seed in SEEDS:
        case = problem(seed, d=4)
        assert acq.choose_gpc_margin(case.unlabelled, case.p) == arch.p15.choose_gpc_margin(case.unlabelled, case.p)
        assert acq.choose_h_margin(case.unlabelled, case.q) == arch.p15.choose_h_margin(case.unlabelled, case.q)
        assert acq.choose_assisted_product(case.unlabelled, case.p, case.q) == arch.p15.choose_assisted_product(case.unlabelled, case.p, case.q)
        assert acq.argmax_index(case.unlabelled, case.q) == arch.p15.deterministic_argmax(case.unlabelled, case.q)
        mine = acq.choose_m3_margin(case.unlabelled, case.p, case.pool, list(case.labelled))
        theirs = arch.p14.choose_m3_margin(case.unlabelled, case.p, case.pool, list(case.labelled))
        assert mine[0] == theirs[0]
        same_metadata(mine[1], theirs[1], ("selected_position", "selected_uncertainty_score"))


@pytest.mark.archive
def test_choose_repulsion_matches_week9_phase1_16(arch):
    assert acq.REPULSION_SCALE_GRID == arch.p16.C_GRID
    for seed in SEEDS:
        case = problem(seed, d=4)
        for c in acq.REPULSION_SCALE_GRID:
            mine = acq.choose_repulsion(case.unlabelled, case.p, case.pool, list(case.labelled), c)
            theirs = arch.p16.choose_repulsion(case.unlabelled, case.p, case.pool, list(case.labelled), c)
            assert mine[0] == theirs[0], (seed, c)
            same_metadata(mine[1], theirs[1], ("uncertainty_score", "d_min", "s_B", "lambda_B", "repulsion_factor", "acquisition_score"))


@pytest.mark.archive
def test_frozen_constants_match_archive(arch):
    assert acq.METHOD_ORDER == arch.ar.METHOD_ORDER and acq.METHOD_DESCRIPTIONS == arch.ar.METHOD_DESCRIPTIONS
    assert acq.DIVERSIFIED_ALPHA == arch.w402.DIVERSIFIED_ALPHA
    assert (acq.GATE_FRACTION, acq.MIN_SHORTLIST_SIZE, acq.DIVERSITY_BETA) == (
        arch.w403.BOUNDARY_GATED_GATE_FRACTION, arch.w403.BOUNDARY_GATED_MIN_SHORTLIST_SIZE, arch.w403.BOUNDARY_GATED_BETA
    )
    assert (acq.GATE_FRACTION, acq.MIN_SHORTLIST_SIZE, acq.REPULSION_BANDWIDTH) == (
        arch.p6.CLASSIFIER_GATE_FRACTION, arch.p6.CLASSIFIER_MIN_SHORTLIST_SIZE, arch.p6.CLASSIFIER_REPULSION_BANDWIDTH
    )
    assert acq.REPULSION_BANDWIDTH == arch.w406.CLASSIFIER_REPULSION_BANDWIDTH == arch.w409.CLASSIFIER_REPULSION_BANDWIDTH
    assert (acq.LOOKAHEAD_SHORTLIST_SIZE, acq.LOOKAHEAD_PROBABILITY_EPS) == (arch.w404.LOOKAHEAD_SHORTLIST_SIZE, arch.w404.LOOKAHEAD_PROBABILITY_EPS)
    assert acq.STRADDLE_KAPPA == arch.p6.STRADDLE_KAPPA
    assert (acq.HYBRID_GATE_FRACTION, acq.RANK_BINARY_WEIGHT, acq.RANK_DEPTH_WEIGHT) == (arch.p7.GATE_FRACTION, arch.p7.RANK_BINARY_WEIGHT, arch.p7.RANK_DEPTH_WEIGHT)
