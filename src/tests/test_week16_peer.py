"""Week 16 item 0 — PEER closed form (Gaussian latent posterior, probit observation) against Monte Carlo."""
import numpy as np

from src.week15_ebr import MeanLaplaceGPC
from src.week16_peer import GaussPost, NOISE_VAR, expectations, peer_values, peer_values_mc


def fitted(seed=0, n=18, m0=0.0):
    rng = np.random.default_rng(seed)
    x = rng.random((n, 4))
    f = 4 * (x[:, 0] - .5) + 2 * np.sin(5 * x[:, 1])
    y = (f + .5 * rng.standard_normal(n) > 0).astype(int)
    return MeanLaplaceGPC([.4, .5, .6, 1.5], 9.0, m0).fit(x, y)


def test_expectations_against_monte_carlo():
    gp = fitted()
    post = GaussPost(gp)
    rng = np.random.default_rng(1)
    Zt, Zc = rng.random((25, 4)), rng.random((6, 4))
    ET, EO, ETO = expectations(post, Zt, Zc)
    Z = np.vstack([Zt, Zc]); mu, _ = post.mean_var(Z)
    S = post.cross_cov(Z, Z) + 1e-9 * np.eye(len(Z))
    F = mu + rng.standard_normal((400000, len(Z))) @ np.linalg.cholesky(S).T
    T = np.sign(F[:, :25]); O = np.sign(F[:, 25:] + np.sqrt(NOISE_VAR) * rng.standard_normal((400000, 6)))
    assert np.abs(T.mean(0) - ET).max() < 6e-3
    assert np.abs(O.mean(0) - EO).max() < 6e-3
    assert np.abs(T.T @ O / 400000 - ETO).max() < 8e-3


def test_peer_values_against_monte_carlo():
    for seed, m0 in ((0, 0.0), (2, -1.5)):
        gp = fitted(seed, m0=m0)
        post = GaussPost(gp)
        rng = np.random.default_rng(seed + 10)
        Zt, Zc = rng.random((40, 4)), rng.random((8, 4))
        v = peer_values(post, Zt, Zc)
        vm = peer_values_mc(post, Zt, Zc, n=300000, seed=seed)
        assert np.abs(v - vm).max() < 0.03 + 0.02 * np.abs(v).max()
        assert np.corrcoef(v, vm)[0, 1] > .97


def test_peer_self_term_only_when_independent():
    # a candidate far from every target (prior correlation ~0) has value only through its own target copy
    gp = fitted(3)
    post = GaussPost(gp)
    far = np.array([[30., 30., 30., 30.]])
    v = peer_values(post, np.random.default_rng(0).random((30, 4)), far)
    assert v[0] < 1e-6
    w = peer_values(post, far, far)        # self value: (|E[T O]| - |E T|)_+ / 2 at a prior point
    assert w[0] > 0


def test_robust_laplace_matches_converged_and_fixes_oscillation():
    from src.week13_synthetic import LaplaceGPC
    from src.week16_peer import RobustLaplaceGPC, mode_gap
    rng = np.random.default_rng(5)
    x = rng.random((30, 4)); y = (x[:, 0] + .3 * rng.standard_normal(30) > .5).astype(int)
    old = LaplaceGPC([.5] * 4, 4.0).fit(x, y); new = RobustLaplaceGPC([.5] * 4, 4.0).fit(x, y)
    xs = rng.random((50, 4))
    assert np.abs(old.latent_mean(xs) - new.latent_mean(xs)).max() < 1e-8 and new.converged
    # the Week 15 gpworld m0 = -4 startup state (8 maximin points) on which the undamped iteration oscillates
    from src.week16_cells import build
    c = build("gpworld", {"m0": -4.0, "pool": 108}, 0)
    L = c["start"]; m = np.full(len(L), -4.0)
    bad = LaplaceGPC(c["hyp"]["ls"], c["hyp"]["var"]).fit(c["z_pool"][L], c["y_pool"][L], mean=m)
    good = RobustLaplaceGPC(c["hyp"]["ls"], c["hyp"]["var"]).fit(c["z_pool"][L], c["y_pool"][L], mean=m)
    assert good.converged and good.fp_err < 1e-8
    assert mode_gap(bad) > 1.0 and mode_gap(good) < 1e-8
