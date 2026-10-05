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


def test_analytic_gradient_matches_finite_differences():
    from src.week18_tobit import lml_grad
    rng = np.random.default_rng(3)
    Z = rng.random((30, 4)); th = np.array([np.log(.5), np.log(1.5), np.log(.6), np.log(.9), np.log(1.2), np.log(2.), np.log(.02)])
    kh = Z[:, 0] > .6; below = (Z[:, 1] > .7) & ~kh
    t = np.where(kh | below, 0.0, -1 + Z[:, 0] + .05 * rng.standard_normal(30))
    m, g = lml_grad(Z, th, t, kh, below)
    for j in range(7):
        e = np.zeros(7); e[j] = 1e-5
        num = (lml_grad(Z, th + e, t, kh, below)[0]["lml"] - lml_grad(Z, th - e, t, kh, below)[0]["lml"]) / 2e-5
        assert abs(num - g[j]) < 1e-4 * max(1.0, abs(num)), (j, num, g[j])


def test_mixed_gp_with_all_depths_is_gp_regression_and_converges():
    from src.week18_tobit import TobitGP
    rng = np.random.default_rng(4)
    X = 1 + rng.random((40, 4)); depth = np.exp(4.7 + .8 * (X[:, 0] - 1.5) - .5 * (X[:, 1] - 1.5) + .01 * rng.standard_normal(40))
    y = (depth >= 111).astype(int)
    f = TobitGP(X, censor_kh=False).fit(X, depth, y)
    assert not f.kh.any() and not f.below.any() and f.mode_fp_ < 1e-8
    C = f.K + f.sig ** 2 * np.eye(40); tc = f.tc
    assert np.abs(f.m["f"] - f.K @ np.linalg.solve(C, tc)).max() < 1e-6
    # label-only rows (no depth) are censored by their label
    d2 = depth.copy(); d2[:10] = np.nan
    f2 = TobitGP(X, censor_kh=False).fit(X, d2, y)
    assert (f2.kh | f2.below)[:10].all() and not (f2.kh | f2.below)[10:].any() and f2.mode_fp_ < 1e-8
