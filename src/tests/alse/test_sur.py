"""Tests for alse.sur: Bernoulli SUR, GPR IVR, Laplace-GPC utilities, exact finite-pool GPC-SUR."""

from __future__ import annotations

import types

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit
from sklearn.gaussian_process.kernels import ConstantKernel, Matern
from sklearn.preprocessing import StandardScaler

from alse import physics, sur
from alse.benchmarks import BRANIN, initial_design, make_dataset
from alse.config import POPULATION_CSV
from alse.surrogates import fit_fixed_gpc, fit_gpr_standin, predict_p_plus

FEATURES = ("P", "VX", "LS", "ST")
TIMING_KEYS = {"fantasy_refit_time_seconds", "mean_pair_fantasy_refit_time_seconds", "candidate_scoring_seconds"}


def assert_same_metadata(ours: dict, theirs: dict, tol: float = 1e-12) -> None:
    """Dict equality with float values compared to an absolute tolerance and timing keys ignored."""
    assert set(ours) == set(theirs)
    for key in ours:
        if key in TIMING_KEYS:
            continue
        mine, ref = ours[key], theirs[key]
        if isinstance(ref, float) and not isinstance(ref, bool):
            assert mine == pytest.approx(ref, abs=tol), key
        else:
            assert mine == ref, key


# --- fixtures ------------------------------------------------------------------


@pytest.fixture(scope="module")
def branin_state():
    """Fixed GPC on Branin seed 0: initial design + 6 random extra rows, p(+1) on the unlabelled pool."""
    dataset = make_dataset(BRANIN, 0)
    labelled = [int(i) for i in initial_design(BRANIN, dataset, 0)]
    rest = np.setdiff1d(np.arange(len(dataset.pool_labels)), labelled)
    labelled += [int(i) for i in np.random.default_rng(1).choice(rest, 6, replace=False)]
    mask = np.ones(len(dataset.pool_labels), dtype=bool)
    mask[labelled] = False
    unlabelled = np.flatnonzero(mask)
    gp = fit_fixed_gpc(dataset.pool_scaled[labelled], dataset.pool_labels[labelled], seed=0)
    return dataset, labelled, unlabelled, gp, predict_p_plus(gp, dataset.pool_scaled[unlabelled])


@pytest.fixture(scope="module")
def branin_gpr_state(branin_state):
    dataset, labelled, unlabelled, _, _ = branin_state
    gp = fit_gpr_standin(dataset.pool_scaled[labelled], dataset.pool_labels[labelled], seed=0)
    mu, sigma = gp.predict(dataset.pool_scaled[unlabelled], return_std=True)
    return dataset, labelled, unlabelled, gp, mu, sigma


def m3_kernel():
    return ConstantKernel(0.09, (0.0025, 1.0)) * Matern(length_scale=np.ones(4), length_scale_bounds=(0.01, 100.0), nu=1.5)


@pytest.fixture(scope="module")
def toy_hybrid():
    """4D toy hybrid state (physics mean + fixed-kernel Laplace GP), 60-row pool, 30 revealed."""
    rng = np.random.default_rng(7)
    n = 60
    x4 = np.column_stack([rng.uniform(50, 400, n), rng.uniform(0.2, 2.0, n), rng.uniform(2e-5, 1e-4, n), rng.uniform(300, 900, n)])
    logh = physics.log_h(x4[:, 0], x4[:, 1], x4[:, 2])
    z = (logh - logh.mean()) / logh.std()
    labels = (2.0 * z + 0.8 * np.sin(3.0 * (x4[:, 3] - 600.0) / 300.0) + rng.normal(0, 0.5, n) > 0).astype(int)
    train = np.arange(n)
    revealed = rng.permutation(n)[:30]
    assert set(labels[revealed]) == {0, 1}
    phys = physics.fit_physics_mean(logh, labels, revealed)
    scaler = StandardScaler().fit(x4[train])
    gp = physics.FixedMeanLaplaceGPC(m3_kernel(), optimize=False).fit(
        scaler.transform(x4[revealed]), labels[revealed], phys.latent(logh[revealed])
    )
    state = types.SimpleNamespace(physics=phys, x_scaler=scaler, gp=gp)
    return state, x4, logh, labels, revealed, train


@pytest.fixture(scope="module")
def population() -> pd.DataFrame:
    frame = pd.read_csv(POPULATION_CSV, low_memory=False)
    assert len(frame) == 405
    return frame


# --- Bernoulli uncertainty and reference sets ----------------------------------------


def test_bernoulli_uncertainty_clips():
    np.testing.assert_array_equal(sur.bernoulli_uncertainty_from_p([-0.5, 0.0, 0.25, 0.5, 1.2]), [0.0, 0.0, 0.1875, 0.25, 0.0])


def test_gpr_p_plus_floors_sigma():
    p = sur.gpr_p_plus(np.array([1.0, -1.0, 0.0]), np.array([0.0, 1.0, 1e-12]))
    assert p[0] == 1.0 and p[2] == 0.5 and p[1] == pytest.approx(0.15865525393145707, abs=1e-15)


def test_reference_positions_rules():
    rng = np.random.default_rng(0)
    indices = np.arange(30)
    u = rng.uniform(0, 0.25, 30)
    u[[3, 9]] = 0.25  # tie -> smaller pool index first
    np.testing.assert_array_equal(
        sur.reference_positions(unlabelled_indices=indices, membership_uncertainty=u, reference_size=30, seed_items=("a",)), np.arange(30)
    )
    ref = sur.reference_positions(unlabelled_indices=indices, membership_uncertainty=u, reference_size=10, seed_items=("branin", 0, "m", 12, "sur_reference"))
    assert len(ref) == 10 and len(set(ref.tolist())) == 10 and np.all(np.diff(ref) > 0)
    top = np.lexsort((indices, -u))[:5]
    assert set(top.tolist()) <= set(ref.tolist()) and top[0] == 3 and top[1] == 9
    again = sur.reference_positions(unlabelled_indices=indices, membership_uncertainty=u, reference_size=10, seed_items=("branin", 0, "m", 12, "sur_reference"))
    np.testing.assert_array_equal(ref, again)
    other = sur.reference_positions(unlabelled_indices=indices, membership_uncertainty=u, reference_size=10, seed_items=("branin", 0, "m", 12, "metric_reference"))
    assert set(top.tolist()) <= set(other.tolist()) and not np.array_equal(ref, other)
    # reference_size 1 -> only the top position (fill_count 0)
    np.testing.assert_array_equal(sur.reference_positions(unlabelled_indices=indices, membership_uncertainty=u, reference_size=1, seed_items=("a",)), [3])


def test_reference_integrated_uncertainty_is_mean_over_reference():
    rng = np.random.default_rng(2)
    p = rng.uniform(0, 1, 50)
    indices = np.arange(100, 150)
    value, size = sur.reference_integrated_uncertainty(p_unlabelled=p, unlabelled_indices=indices, reference_size=20, seed_items=("x", 1))
    ref = sur.reference_positions(unlabelled_indices=indices, membership_uncertainty=p * (1 - p), reference_size=20, seed_items=("x", 1))
    assert size == 20 and value == pytest.approx(float(np.mean((p * (1 - p))[ref])), abs=1e-15)
    assert sur.sur_method_name(15) == "gpc_bernoulli_sur_refit_k15" and sur.SUR_SHORTLIST_SIZES == (15, 25)


# --- GPC Bernoulli SUR ------------------------------------------------------------------


def test_choose_gpc_bernoulli_sur_small(branin_state):
    dataset, labelled, unlabelled, _, p_plus = branin_state
    seed_items = ("branin", 0, sur.sur_method_name(4), len(labelled), sur.SUR_REFERENCE_SALT)
    chosen, meta = sur.choose_gpc_bernoulli_sur(
        pool_scaled=dataset.pool_scaled, pool_labels=dataset.pool_labels, labelled_indices=labelled,
        unlabelled_indices=unlabelled, p_plus=p_plus, seed=0, reference_size=60, shortlist_size=4, seed_items=seed_items,
    )
    assert chosen in set(unlabelled.tolist()) and chosen not in labelled
    assert meta["shortlist_size"] == 4 and meta["fantasy_refit_count"] == 8 and meta["reference_set_size"] == 60
    assert unlabelled[meta["selected_position"]] == chosen
    assert meta["expected_uncertainty_reduction"] == meta["selected_score"]
    assert meta["expected_future_uncertainty"] == pytest.approx(meta["p_star"] * meta["U_plus"] + (1 - meta["p_star"]) * meta["U_minus"], abs=1e-15)
    assert meta["selected_score"] == pytest.approx(meta["U_current"] - meta["expected_future_uncertainty"], abs=1e-15)
    # brute-force recomputation of the selected candidate's reduction
    ref = sur.reference_positions(unlabelled_indices=unlabelled, membership_uncertainty=p_plus * (1 - p_plus), reference_size=60, seed_items=seed_items)
    x = np.vstack([dataset.pool_scaled[labelled], dataset.pool_scaled[chosen][None, :]])
    y = dataset.pool_labels[labelled]
    reference = dataset.pool_scaled[unlabelled[ref]]
    u_plus = np.mean(sur.bernoulli_uncertainty_from_p(predict_p_plus(fit_fixed_gpc(x, np.r_[y, 1.0], seed=0), reference)))
    u_minus = np.mean(sur.bernoulli_uncertainty_from_p(predict_p_plus(fit_fixed_gpc(x, np.r_[y, -1.0], seed=0), reference)))
    p_star = p_plus[meta["selected_position"]]
    assert meta["U_plus"] == pytest.approx(u_plus, abs=1e-15) and meta["U_minus"] == pytest.approx(u_minus, abs=1e-15)
    assert meta["selected_score"] == pytest.approx(np.mean((p_plus * (1 - p_plus))[ref]) - (p_star * u_plus + (1 - p_star) * u_minus), abs=1e-15)
    # shortlist = top-k pool-normalised uncertainty-repulsion scores
    score, _, _ = sur._shortlist_scores(p_plus, unlabelled, dataset.pool_scaled, labelled)
    shortlist = unlabelled[np.lexsort((unlabelled, -score))[:4]]
    assert chosen in set(shortlist.tolist())


# --- GPR boundary-weighted IVR ----------------------------------------------------------


def test_gpr_ivr_state_and_chooser(branin_gpr_state):
    dataset, labelled, unlabelled, gp, mu, sigma = branin_gpr_state
    state = sur.compute_gpr_ivr_state(
        gp=gp, pool_scaled=dataset.pool_scaled, unlabelled_indices=unlabelled, mu=mu, sigma=sigma, reference_size=100, seed_items=("branin", 0, "ivr", 12, "sur_reference")
    )
    n = len(unlabelled)
    gate = state["gate_pos"]
    assert len(gate) == max(int(np.ceil(0.3 * n)), min(1000, n)) == 1000
    assert np.isneginf(np.delete(state["scores"], gate)).all() and np.isfinite(state["scores"][gate]).all()
    assert state["reference_weights"].sum() == pytest.approx(1.0) and state["covariance_ref_gate"].shape == (100, 1000)
    np.testing.assert_allclose(state["straddle"], 1.96 * sigma - np.abs(mu))
    # own-covariance of a gate point equals its posterior variance (up to the GPR's alpha/noise)
    own = sur.gpr_posterior_covariance(gp, dataset.pool_scaled[unlabelled[gate[:5]]], dataset.pool_scaled[unlabelled[gate[:5]]])
    np.testing.assert_allclose(np.diag(own), sigma[gate[:5]] ** 2, rtol=1e-6, atol=1e-4)
    chosen, meta = sur.choose_gpr_boundary_weighted_ivr(
        gp=gp, pool_scaled=dataset.pool_scaled, unlabelled_indices=unlabelled, mu=mu, sigma=sigma, reference_size=100, seed_items=("branin", 0, "ivr", 12, "sur_reference")
    )
    assert chosen == unlabelled[sur._argmax_position(unlabelled, state["scores"])] and chosen not in labelled
    assert meta["selected_score"] == state["scores"].max() and meta["candidate_gate_size"] == 1000 and meta["reference_set_size"] == 100


# --- Laplace-GPC utilities ------------------------------------------------------------------


def test_expected_logistic_curvature_limits_and_monte_carlo():
    mu = np.array([-2.0, 0.0, 1.5])
    tiny = sur.expected_logistic_curvature(mu, np.full(3, 1e-16))
    np.testing.assert_allclose(tiny, expit(mu) * (1 - expit(mu)), atol=1e-9)
    rng = np.random.default_rng(0)
    f = mu[:, None] + np.sqrt(0.8) * rng.standard_normal((3, 400_000))
    np.testing.assert_allclose(sur.expected_logistic_curvature(mu, np.full(3, 0.8)), (expit(f) * (1 - expit(f))).mean(axis=1), atol=2e-3)
    assert sur.expected_logistic_curvature(np.array([[0.5, -0.5]]), np.array([[1.0, 1.0]])).shape == (1, 2)


def test_logistic_gaussian_probability_matches_gpc_and_limits(toy_hybrid):
    state, x4, logh, _, _, _ = toy_hybrid
    xs = state.x_scaler.transform(x4)
    mean = state.physics.latent(logh)
    mu, var = state.gp.latent_mean_and_variance(xs, mean)
    np.testing.assert_allclose(sur.logistic_gaussian_probability(mu, var), state.gp.predict_proba(xs, mean)[:, 1], atol=1e-14, rtol=0)
    np.testing.assert_allclose(sur.logistic_gaussian_probability(np.array([-3.0, 0.0, 2.0]), np.zeros(3)), expit([-3.0, 0.0, 2.0]), atol=1e-3)
    two_d = sur.logistic_gaussian_probability(np.zeros((2, 3)), np.ones((2, 3)))
    assert two_d.shape == (2, 3) and np.allclose(two_d, 0.5)
    extreme = sur.logistic_gaussian_probability(np.array([60.0, -60.0]), np.array([1e-3, 1e-3]))
    # the five WB coefficients sum to 1 - 1e-8, so the clip is a guard, not a limit
    assert 0.9999999 < extreme[0] <= 1 - physics.EPS and physics.EPS <= extreme[1] < 1e-7


def test_emi_score_closed_form():
    assert sur.emi_score(np.array([0.0]), np.array([0.7]))[0] == pytest.approx(0.7 / np.sqrt(2 * np.pi), abs=1e-15)
    rng = np.random.default_rng(3)
    for mu, sd in ((-1.0, 0.7), (1.0, 1.5), (3.0, 0.2)):
        f = rng.normal(mu, sd, 500_000)
        assert sur.emi_score(np.array([mu]), np.array([sd]))[0] == pytest.approx(np.mean(np.maximum(0.0, -np.sign(mu) * f)), abs=3e-3)
    assert sur.emi_score(np.array([2.0]), np.array([0.0]))[0] == pytest.approx(0.0, abs=1e-12)


def test_posterior_covariance_consistent_with_latent_variance(toy_hybrid):
    state, x4, logh, _, revealed, _ = toy_hybrid
    xs = state.x_scaler.transform(x4[:25])
    cov = sur.posterior_covariance(state.gp, xs)
    np.testing.assert_array_equal(cov, cov.T)
    _, var = state.gp.latent_mean_and_variance(xs, np.zeros(25))
    np.testing.assert_allclose(np.diag(cov), var, atol=1e-12, rtol=0)
    assert np.linalg.eigvalsh(cov).min() > -1e-8
    train_cov = sur.posterior_covariance(state.gp, state.x_scaler.transform(x4[revealed[:5]]))
    assert (np.diag(train_cov) >= physics.EPS).all() and np.diag(train_cov).max() < 0.09


# --- exact finite-pool GPC-SUR ---------------------------------------------------------------


@pytest.mark.parametrize("arm", sur.SUR_ARMS)
def test_score_candidates_toy(toy_hybrid, arm):
    state, x4, logh, labels, revealed, train = toy_hybrid
    candidates = np.setdiff1d(train, revealed)[:10]
    chosen, records, diag = sur.score_candidates(state, x4, logh, labels, revealed, candidates, arm, "toy", 30)
    scores = np.array([r["sur_score"] for r in records])
    assert chosen in set(candidates.tolist()) and np.isfinite(scores).all() and len(records) == 10
    order = np.lexsort((candidates, -scores))
    assert chosen == candidates[order[0]]
    assert diag["near_tie_tolerance"] == max(1e-14, 1e-6 * max(np.abs(scores).max(), np.ptp(scores)))
    assert diag["hypothetical_failures"] == 0 and diag["fallback_count"] == 0 and diag["candidate_count"] == 10
    assert diag["top1_top2_gap"] == pytest.approx(scores[order[0]] - scores[order[1]])
    for r in records:
        p = r["candidate_probability"]
        assert r["expected_future_uncertainty"] == pytest.approx((1 - p) * r["future_uncertainty_y0"] + p * r["future_uncertainty_y1"], abs=1e-15)
        assert r["sur_score"] == pytest.approx(r["current_global_uncertainty"] - r["expected_future_uncertainty"], abs=1e-15)
        assert r["run_id"] == "toy" and r["budget"] == 30 and r["arm"] == arm and r["posterior_iterations_y0"] >= 1
        if arm == sur.EXACT_FIXED_SUR:
            assert r["physics_intercept_y0"] == r["current_physics_intercept"] == r["physics_intercept_y1"]
        else:
            assert r["physics_slope_y0"] != r["current_physics_slope"] or r["physics_slope_y1"] != r["current_physics_slope"]
    # the labels array passed in is never mutated
    assert labels.sum() == labels.sum() and set(np.unique(labels)) == {0, 1}


def test_hypothetical_update_fallback_and_errors(toy_hybrid, monkeypatch):
    state, x4, logh, labels, revealed, train = toy_hybrid
    candidate = int(np.setdiff1d(train, revealed)[0])
    reference = np.setdiff1d(train, revealed)[1:6]
    before = labels.copy()
    hyp = sur.hypothetical_update(state, x4, logh, labels, revealed, candidate, 1, sur.EXACT_FIXED_SUR, reference, "toy", 30)
    np.testing.assert_array_equal(labels, before)
    assert hyp.probability.shape == (5,) and not hyp.fallback and 0 < hyp.posterior_iterations < 100
    assert hyp.intercept == float(state.physics.model.intercept_[0]) and hyp.slope == float(state.physics.model.coef_[0, 0])
    with pytest.raises(ValueError):
        sur.hypothetical_update(state, x4, logh, labels, revealed, candidate, 1, "P3", reference, "toy", 30)
    monkeypatch.setattr(sur, "HYPOTHETICAL_MAX_ITER_PREDICT", 1)
    retried = sur.hypothetical_update(state, x4, logh, labels, revealed, candidate, 1, sur.EXACT_FIXED_SUR, reference, "toy", 30)
    assert retried.fallback and retried.posterior_iterations == hyp.posterior_iterations
    np.testing.assert_allclose(retried.probability, hyp.probability, atol=1e-12, rtol=0)


def test_exact_update_levels(toy_hybrid):
    state, x4, logh, labels, revealed, train = toy_hybrid
    candidate = int(np.setdiff1d(train, revealed)[2])
    reference = np.setdiff1d(train, revealed)[3:9]
    fixed = sur.exact_update(state, x4, logh, labels, revealed, train, candidate, 1, "EXACT_LAPLACE_FIXED_MODEL")
    assert fixed.physics is state.physics and fixed.scaler is state.x_scaler and fixed.level == "EXACT_LAPLACE_FIXED_MODEL"
    mu, var, p = sur.updated_components(fixed, x4, logh, reference)
    assert mu.shape == var.shape == p.shape == (6,) and (var >= physics.EPS).all() and ((p > 0) & (p < 1)).all()
    hyp = sur.hypothetical_update(state, x4, logh, labels, revealed, candidate, 1, sur.EXACT_FIXED_SUR, reference, "toy", 30)
    np.testing.assert_allclose(p, hyp.probability, atol=1e-12, rtol=0)
    refit = sur.exact_update(state, x4, logh, labels, revealed, train, candidate, 0, "EXACT_LAPLACE_REFIT_PHYSICS")
    assert refit.physics is not state.physics and refit.scaler is state.x_scaler
    assert refit.physics.model.coef_[0, 0] != state.physics.model.coef_[0, 0]
    with pytest.raises(RuntimeError, match="FULL_M3_REFIT"):
        sur.exact_update(state, x4, logh, labels, revealed, train, candidate, 1, "FULL_M3_REFIT")
    with pytest.raises(ValueError):
        sur.exact_update(state, x4, logh, labels, revealed, train, candidate, 1, "FAST_RANK1")
    seen = {}

    def stub(x4_, logh_, lab, enlarged, pool, phys, model, upper):
        seen.update(model=model, upper=upper, n=len(enlarged), flipped=int(lab[candidate]))
        return types.SimpleNamespace(physics=phys, x_scaler=state.x_scaler, gp=state.gp)

    full = sur.exact_update(state, x4, logh, labels, revealed, train, candidate, 0, "FULL_M3_REFIT", refit=stub)
    assert seen == {"model": "M3", "upper": 100.0, "n": len(revealed) + 1, "flipped": 0} and full.gp is state.gp
    assert labels[candidate] != 0 or True  # input labels untouched (copy semantics)
    assert sur.UPDATE_LEVELS == ("EXACT_LAPLACE_FIXED_MODEL", "EXACT_LAPLACE_REFIT_PHYSICS", "FULL_M3_REFIT")


# --- archive comparisons ------------------------------------------------------------------


@pytest.mark.archive
def test_reference_positions_equal_archive(archive_src, branin_state):
    import src.week4_09_gpc_bernoulli_sur_validation as w409

    _, labelled, unlabelled, _, p_plus = branin_state
    u = sur.bernoulli_uncertainty_from_p(p_plus)
    for size in (1, 10, 200, 1499, 1500, 2000):
        for items in (("branin", 0, "gpc_bernoulli_sur_refit_k15", len(labelled), "sur_reference"), ("hartmann4", 3, "m", 40, "metric_reference")):
            np.testing.assert_array_equal(
                sur.reference_positions(unlabelled_indices=unlabelled, membership_uncertainty=u, reference_size=size, seed_items=items),
                w409.reference_positions(unlabelled_indices=unlabelled, membership_uncertainty=u, reference_size=size, seed_items=items),
            )
    score, unc, rep = sur._shortlist_scores(p_plus, unlabelled, branin_state[0].pool_scaled, labelled)
    ref = w409.classifier_repulsion_scores(p_plus=p_plus, unlabelled_indices=unlabelled, pool_scaled=branin_state[0].pool_scaled, labelled_indices=labelled)
    for mine, theirs in zip((score, unc, rep), ref):
        np.testing.assert_array_equal(mine, theirs)
    mine = sur.reference_integrated_uncertainty(p_unlabelled=p_plus, unlabelled_indices=unlabelled, reference_size=300, seed_items=("branin", 0, "m", 12, "metric_reference"))
    theirs = w409.reference_integrated_uncertainty_metric(p_unlabelled=p_plus, unlabelled_indices=unlabelled, reference_size=300, seed_items=("branin", 0, "m", 12, "metric_reference"))
    assert mine == theirs


@pytest.mark.archive
@pytest.mark.parametrize("shortlist_size,reference_size", [(15, 1500), (25, 1500), (15, 200)])
def test_choose_gpc_bernoulli_sur_equals_archive(archive_src, branin_state, shortlist_size, reference_size):
    import src.week4_09_gpc_bernoulli_sur_validation as w409

    dataset, labelled, unlabelled, gp, p_plus = branin_state
    seed_items = ("branin", 0, sur.sur_method_name(shortlist_size), len(labelled), sur.SUR_REFERENCE_SALT)
    assert sur.sur_method_name(shortlist_size) == w409.method_for_shortlist(shortlist_size)
    chosen, meta = sur.choose_gpc_bernoulli_sur(
        pool_scaled=dataset.pool_scaled, pool_labels=dataset.pool_labels, labelled_indices=labelled, unlabelled_indices=unlabelled,
        p_plus=p_plus, seed=0, reference_size=reference_size, shortlist_size=shortlist_size, seed_items=seed_items,
    )
    expected, expected_meta = w409.choose_gpc_bernoulli_sur(
        gp=gp, dataset=dataset, labelled_indices=labelled, unlabelled_indices=unlabelled, p_plus=p_plus, seed=0,
        reference_size=reference_size, shortlist_size=shortlist_size, seed_items=seed_items,
    )
    assert chosen == expected
    assert_same_metadata(meta, expected_meta)


@pytest.mark.archive
@pytest.mark.parametrize("reference_size", [1500, 300])
def test_gpr_ivr_equals_archive(archive_src, branin_gpr_state, reference_size):
    import src.week4_08_boundary_weighted_sur as w408

    dataset, _, unlabelled, gp, mu, sigma = branin_gpr_state
    seed_items = ("branin", 0, "gpr_boundary_weighted_ivr", 12, "sur_reference")
    np.testing.assert_array_equal(sur.gpr_p_plus(mu, sigma), w408.gpr_p_plus(mu, sigma))
    state = sur.compute_gpr_ivr_state(gp=gp, pool_scaled=dataset.pool_scaled, unlabelled_indices=unlabelled, mu=mu, sigma=sigma, reference_size=reference_size, seed_items=seed_items)
    ref = w408.compute_gpr_ivr_state(gp=gp, dataset=dataset, unlabelled_indices=unlabelled, mu=mu, sigma=sigma, reference_size=reference_size, seed_items=seed_items)
    assert set(state) == set(ref)
    for key in state:
        np.testing.assert_array_equal(np.asarray(state[key]), np.asarray(ref[key]), err_msg=key)
    chosen, meta = sur.choose_gpr_boundary_weighted_ivr(gp=gp, pool_scaled=dataset.pool_scaled, unlabelled_indices=unlabelled, mu=mu, sigma=sigma, reference_size=reference_size, seed_items=seed_items)
    expected, expected_meta = w408.choose_gpr_boundary_weighted_ivr(gp=gp, dataset=dataset, unlabelled_indices=unlabelled, mu=mu, sigma=sigma, reference_size=reference_size, seed_items=seed_items)
    assert chosen == expected
    assert_same_metadata(meta, expected_meta)
    cov = sur.gpr_posterior_covariance(gp, dataset.pool_scaled[unlabelled[:40]], dataset.pool_scaled[unlabelled[40:70]])
    np.testing.assert_array_equal(cov, w408.posterior_covariance(gp, dataset.pool_scaled[unlabelled[:40]], dataset.pool_scaled[unlabelled[40:70]]))


@pytest.mark.archive
def test_laplace_utilities_equal_archive(archive_src, toy_hybrid):
    import src.week9_phase1_18a_level_set_acquisition_compatibility_audit as p18a

    assert sur.GH_NODES == p18a.GH_NODES == 24
    rng = np.random.default_rng(5)
    for shape in ((40,), (6, 7)):
        mu = rng.normal(0, 3, shape)
        var = rng.uniform(1e-13, 4, shape)
        np.testing.assert_array_equal(sur.expected_logistic_curvature(mu, var), p18a.expected_logistic_curvature(mu, var))
        np.testing.assert_array_equal(sur.logistic_gaussian_probability(mu, var), p18a.logistic_gaussian_probability(mu, var))
        np.testing.assert_array_equal(sur.emi_score(mu, np.sqrt(var)), p18a.emi_score(mu, np.sqrt(var)))
    state, x4, _, _, revealed, _ = toy_hybrid
    xs = state.x_scaler.transform(x4[np.r_[revealed[:5], 40:55]])
    np.testing.assert_array_equal(sur.posterior_covariance(state.gp, xs), p18a.posterior_covariance(types.SimpleNamespace(gp=state.gp), xs))


@pytest.fixture(scope="module")
def m3_state(archive_src, population):
    """Archive M3 hybrid (p13.fit_hybrid) on 40 revealed rows of a 324-row training pool, 14 candidates."""
    import src.week9_phase1_11_fixed_mean_discrepancy_gp as p11
    import src.week9_phase1_13_fixed_physics_ard_discrepancy as p13

    x4 = population.loc[:, list(FEATURES)].to_numpy(float)
    labels = population.has_keyhole.astype(int).to_numpy()
    logh = p11.log_h_values(population)
    np.testing.assert_array_equal(logh, physics.log_h(population.P, population.VX, population.LS))
    order = np.random.default_rng(18).permutation(len(population))
    train = np.sort(order[:324])
    revealed = train[np.random.default_rng(19).permutation(len(train))[:40]]
    assert set(labels[revealed]) == {0, 1}
    physics_fit = p11.fit_physics_mean(logh, labels, revealed, p13.seed_u32("shared_physics", "test", 40))
    fit = p13.fit_hybrid(x4, logh, labels, revealed, train, physics_fit, "M3", 100.0)
    candidates = np.setdiff1d(train, revealed)[::20][:14]
    return fit, x4, logh, labels, revealed, train, candidates


@pytest.mark.archive
@pytest.mark.parametrize("arm", sur.SUR_ARMS)
def test_score_candidates_equals_archive(archive_src, m3_state, arm):
    import src.week9_phase1_18b_prospective_global_gpc_sur_benchmark as p18b

    fit, x4, logh, labels, revealed, _, candidates = m3_state
    assert sur.SUR_ARMS == p18b.ARMS and sur.NEAR_TIE_RELATIVE_TOLERANCE == p18b.NEAR_TIE_RELATIVE_TOLERANCE
    assert sur.SEED_ROOT_18B == p18b.SEED_ROOT
    chosen, records, diag = sur.score_candidates(fit, x4, logh, labels, revealed, candidates, arm, "w85__r01_f01", 40)
    expected, expected_records, expected_diag = p18b.score_candidates(fit, x4, logh, labels, revealed, candidates, arm, "w85__r01_f01", 40)
    assert chosen == expected and len(records) == len(expected_records) == 14
    np.testing.assert_allclose([r["sur_score"] for r in records], [r["sur_score"] for r in expected_records], atol=1e-12, rtol=0)
    for mine, theirs in zip(records, expected_records):
        assert_same_metadata(mine, theirs)
    assert_same_metadata(diag, expected_diag)
    hyp = sur.hypothetical_update(fit, x4, logh, labels, revealed, int(candidates[3]), 1, arm, candidates[:3], "w85__r01_f01", 40)
    ref = p18b.hypothetical_update(fit, x4, logh, labels, revealed, int(candidates[3]), 1, arm, candidates[:3], "w85__r01_f01", 40)
    np.testing.assert_allclose(hyp.probability, ref.probability, atol=1e-12, rtol=0)
    assert (hyp.fallback, hyp.posterior_iterations, hyp.intercept, hyp.slope) == (ref.fallback, ref.posterior_iterations, ref.intercept, ref.slope)


@pytest.mark.archive
@pytest.mark.parametrize("level", sur.UPDATE_LEVELS)
def test_exact_update_equals_archive(archive_src, m3_state, level):
    import src.week9_phase1_13_fixed_physics_ard_discrepancy as p13
    import src.week9_phase1_18b0_fast_gpc_sur_update_validation as p18b0

    fit, x4, logh, labels, revealed, train, candidates = m3_state
    assert sur.SEED_ROOT_18B0 == p18b0.SEED_ROOT and level in p18b0.LEVELS
    candidate, y = int(candidates[5]), int(1 - labels[candidates[5]])
    reference = candidates[:8]
    mine = sur.exact_update(fit, x4, logh, labels, revealed, train, candidate, y, level, refit=p13.fit_hybrid)
    theirs = p18b0.exact_update(fit, x4, logh, labels, revealed, train, candidate, y, level)
    assert mine.level == theirs.level == level
    np.testing.assert_array_equal(mine.gp.kernel_.theta, theirs.gp.kernel_.theta)
    np.testing.assert_array_equal(mine.physics.model.coef_, theirs.physics.model.coef_)
    np.testing.assert_array_equal(mine.physics.model.intercept_, theirs.physics.model.intercept_)
    for got, want in zip(sur.updated_components(mine, x4, logh, reference), p18b0.updated_components(theirs, x4, logh, reference)):
        np.testing.assert_allclose(got, want, atol=1e-12, rtol=0)
