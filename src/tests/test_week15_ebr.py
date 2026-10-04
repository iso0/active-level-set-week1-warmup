"""Correctness of the EBR building blocks."""
import numpy as np
from scipy.stats import multivariate_normal

from src.week13_synthetic import LaplaceGPC, matern32
from src.week15_ebr import Posterior, bvn_lower, edge_risk, knn_graph, volume_risk


def test_bvn_against_scipy():
    rng = np.random.default_rng(0)
    for _ in range(60):
        h, k = rng.normal(0, 1.5, 2)
        r = rng.uniform(-.95, .95)
        ref = multivariate_normal([0, 0], [[1, r], [r, 1]]).cdf([h, k])
        assert abs(bvn_lower(np.array([h]), np.array([k]), np.array([r]))[0] - ref) < 2e-4


def test_edge_cov_matches_full_posterior_covariance():
    rng = np.random.default_rng(1)
    X = rng.random((25, 2)); y = (X[:, 0] > .5).astype(int)
    gp = LaplaceGPC([.3, .3], 4.0).fit(X, y)
    Z = rng.random((40, 2)); e = knn_graph(Z, 4)
    mu, s, rho = Posterior(gp).marginals_and_edges(Z, e)
    ks = matern32(gp.x, Z, gp.ls, gp.var)
    from scipy.linalg import solve_triangular
    V = solve_triangular(gp.L, gp.sw[:, None] * ks, lower=True)
    C = matern32(Z, Z, gp.ls, gp.var) - V.T @ V
    assert np.allclose(s, np.sqrt(np.diag(C)))
    assert np.allclose(rho, C[e[:, 0], e[:, 1]] / (s[e[:, 0]] * s[e[:, 1]]))


def test_risks_vanish_when_posterior_is_certain():
    Z = np.random.default_rng(2).random((30, 2)); e = knn_graph(Z, 4)
    mu = np.where(Z[:, 0] > .5, 50.0, -50.0); s = np.full(30, .01); rho = np.full(len(e), .5)
    assert edge_risk(mu, s, rho, e) < 1e-6 and volume_risk(mu, s) < 1e-6


def test_B3_unnormalized_risk_prefers_erasing_uncertain_boundary():
    """Flat boundary with location uncertainty s >> r: plug-in ~2x the constant predictor's error perimeter."""
    rng = np.random.default_rng(3)
    Z = rng.random((3000, 2)); e = knn_graph(Z, 8)
    thetas = rng.normal(.5, .15, 400)
    plug = (Z[:, 0] > .5).astype(int); const = np.zeros(3000, int)
    def mism(yhat):
        out_u, out_t = [], []
        for t in thetas:
            y = (Z[:, 0] > t).astype(int)
            err = (y != yhat).astype(int)
            out_u.append((err[e[:, 0]] != err[e[:, 1]]).sum())
            out_t.append((y[e[:, 0]] != y[e[:, 1]]).sum())
        pred = (yhat[e[:, 0]] != yhat[e[:, 1]]).sum()
        return np.mean(out_u), np.mean(out_u) / (np.mean(out_t) + pred)
    u_plug, d_plug = mism(plug); u_const, d_const = mism(const)
    assert u_plug > 1.5 * u_const               # unnormalized risk prefers the constant predictor
    assert abs(d_plug - d_const) < .1            # Dice-normalized risks are (nearly) tied
