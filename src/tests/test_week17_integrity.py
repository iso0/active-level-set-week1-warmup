"""Week 17 Phase 0 — convergence diagnostics for the authoritative Laplace GPC implementations."""
import numpy as np
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.gaussian_process.kernels import ConstantKernel, Matern

from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src.week17_audit import audit_fixedmean, audit_sklearn, safeguarded_mode
from src.week17_audit_impact import SafeguardedFixedMeanLaplaceGPC


def data(n=40, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.standard_normal((n, 4)); y = (x[:, 0] + .5 * x[:, 1] + .3 * rng.standard_normal(n) > 0).astype(int)
    return x, y


def test_safeguarded_mode_is_fixed_point_and_matches_converged_sklearn():
    x, y = data()
    k = ConstantKernel(4.0, "fixed") * Matern([1.0] * 4, "fixed", nu=1.5)
    g = GaussianProcessClassifier(k, optimizer=None).fit(x, y)
    r = audit_sklearn(g, x[:10])
    assert not r["flag"] and r["dp_test_max"] < 1e-8
    m = safeguarded_mode(k(x), y, np.zeros(len(y)))
    assert m["converged"] and m["fp"] < 1e-8


def test_safeguarded_fixedmean_equals_historical_when_historical_converges():
    x, y = data(seed=1)
    k = ConstantKernel(1.0, "fixed") * Matern([1.0] * 4, "fixed", nu=1.5)
    mean = .3 * x[:, 0]
    a = p11.FixedMeanLaplaceGPC(k, optimize=False).fit(x, y, mean)
    b = SafeguardedFixedMeanLaplaceGPC(k, optimize=False).fit(x, y, mean)
    xt = np.random.default_rng(2).standard_normal((15, 4))
    assert np.abs(a.predict_proba(xt, .3 * xt[:, 0]) - b.predict_proba(xt, .3 * xt[:, 0])).max() < 1e-7


def test_historical_m3_transfer_fit_is_not_at_its_mode():
    """The Week 12 OLD-405 M3 fit (C = 1e6 physics mean): the historical Newton stops after two steps away from
    the Laplace mode; the safeguarded refit is at the mode and does not change any NEW class decision."""
    from src.week17_audit import campaigns, fit_m3
    from src.week17_audit_impact import fit_m3 as fit_m3_safe, predict
    C = campaigns(); xo, lo, yo = C["OLD"]; xn, ln, yn = C["NEW"]
    fit, phys = fit_m3(xo, lo, yo, np.arange(len(yo)), np.arange(len(yo)))
    r = audit_fixedmean(fit.gp, fit.x_scaler.transform(xn), phys.latent(ln))
    assert fit.gp.diagnostics_.posterior_iterations == 2 and r["dg_train"] > .1 and r["dclass_test"] == 0
    gp, sc, ph = fit_m3_safe(xo, lo, yo, np.arange(len(yo)), np.arange(len(yo)), safe=True)
    r2 = audit_fixedmean(gp, sc.transform(xn), ph.latent(ln))
    assert r2["dg_train"] < 1e-8
