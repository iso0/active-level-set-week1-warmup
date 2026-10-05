"""Week 18 — censored (Tobit) GP: exactness in the all-Gaussian case, convergence, censoring behaviour."""
import numpy as np

from src.week18_tobit import kern, lik, mode


def test_all_conduction_mode_equals_exact_gp_regression():
    rng = np.random.default_rng(0)
    Z = rng.random((25, 4)); th = np.array([0., np.log(2.), np.log(.5), np.log(.7), np.log(1.), np.log(2.), np.log(.01)])
    K = kern(Z, Z, th) + 1e-8 * np.eye(25); t = np.sin(3 * Z[:, 0]) + .1 * rng.standard_normal(25)
    sig = np.exp(.5 * th[6])
    m = mode(K, t, np.zeros(25, bool), 0.0, sig)
    exact = K @ np.linalg.solve(K + sig ** 2 * np.eye(25), t)
    assert np.abs(m["f"] - exact).max() < 1e-7 and m["fp"] < 1e-8
    # exact Gaussian evidence
    C = K + sig ** 2 * np.eye(25); sign, logdet = np.linalg.slogdet(C)
    lml = -.5 * t @ np.linalg.solve(C, t) - .5 * logdet - 12.5 * np.log(2 * np.pi)
    assert abs(m["lml"] - lml) < 1e-6


def test_censored_points_pushed_above_threshold_and_converged():
    rng = np.random.default_rng(1)
    Z = rng.random((30, 4)); th = np.array([0., 0., np.log(.5), 0., 0., 0., np.log(.01)])
    K = kern(Z, Z, th) + 1e-8 * np.eye(30)
    kh = Z[:, 0] > .6; t = np.where(kh, 0.0, -1 + Z[:, 0])
    m = mode(K, t, kh, 0.0, np.exp(.5 * th[6]))
    assert m["fp"] < 1e-7 and np.all(m["f"][kh] > -0.05)
    ll, g, W = lik(m["f"], t, kh, 0.0, .1)
    assert np.all(W > 0)


def test_rows_without_depth_censor_below():
    rng = np.random.default_rng(2)
    Z = rng.random((20, 4)); th = np.array([0., 0., np.log(.5), 0., 0., 0., np.log(.01)])
    K = kern(Z, Z, th) + 1e-8 * np.eye(20)
    kh = Z[:, 0] > .5; below = ~kh
    m = mode(K, np.zeros(20), kh, 0.0, .1, below=below)
    assert m["fp"] < 1e-7 and np.all(m["f"][kh] > 0) and np.all(m["f"][below] < 0)
