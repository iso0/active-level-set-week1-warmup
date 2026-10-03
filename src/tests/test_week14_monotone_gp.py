"""Correctness checks for the Laplace monotone GPC."""
import numpy as np
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.gaussian_process.kernels import RBF, ConstantKernel

from src.week14_monotone_gp import MonotoneGPC, joint_cov, virtual_design


def test_parity_with_sklearn_without_virtual_points():
    rng = np.random.default_rng(0)
    X = rng.random((40, 2))
    y = (X[:, 0] + .3 * rng.standard_normal(40) > .5).astype(int)
    ls, var = np.array([.4, .7]), 3.0
    sk = GaussianProcessClassifier(ConstantKernel(var, "fixed") * RBF(ls, "fixed"), optimizer=None).fit(X, y)
    m = MonotoneGPC(ls, var, jitter=0).fit(X, y)
    Xs = rng.random((30, 2))
    mu, _ = m.latent(Xs)
    # sklearn's predict_proba uses a different averaging; compare latent means through its internals
    K_star = sk.base_estimator_.kernel_(sk.base_estimator_.X_train_, Xs)
    mu_sk = K_star.T.dot(sk.base_estimator_.y_train_ - sk.base_estimator_.pi_)
    assert np.allclose(mu, mu_sk, atol=1e-5)


def test_joint_covariance_is_psd_and_matches_finite_differences():
    rng = np.random.default_rng(1)
    X = rng.random((5, 3)); V = rng.random((4, 3)); vd = np.array([0, 1, 2, 1])
    ls, var = np.array([.5, .8, .3]), 2.0
    K = joint_cov(X, V, vd, ls, var)
    assert np.linalg.eigvalsh(K).min() > -1e-9
    # finite-difference check of one Kfg entry
    from src.week14_monotone_gp import rbf
    e = np.zeros(3); e[vd[2]] = 1e-6
    fd = (rbf(X[:1], V[2:3] + e, ls, var) - rbf(X[:1], V[2:3] - e, ls, var)) / 2e-6
    assert np.isclose(K[0, 5 + 2], fd[0, 0], atol=1e-6)


def test_virtual_observations_enforce_monotone_mean():
    rng = np.random.default_rng(2)
    X = rng.random((25, 1)); y = (rng.random(25) < .5).astype(int)  # labels with no monotone trend
    grid = np.linspace(0, 1, 41)[:, None]
    V, vd, vs = virtual_design(grid, [1])
    m = MonotoneGPC([.2], 4.0, nu=.05).fit(X, y, V, vd, vs)
    mu, _ = m.latent(grid)
    assert (np.diff(mu) > -1e-3).all()
