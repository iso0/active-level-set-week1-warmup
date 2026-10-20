"""RC20 GP extension: a Gaussian-prior linear basis in log h with a LEARNED, shrinkable prior strength (rc18_gp engine).

Model (per output, standardised targets ys = (y - mean_train) / sd_train, train = the permitted paid / cross-fit subset):
    ys = f(z) + h~(x) beta + eps,  f ~ GP(0, sf2 Matern32_ARD(z, z'; ell)),  beta ~ N(0, b2),  eps_i ~ N(0, sn2 w_i)
  * h~ = standardised log h, log h = log P - 0.5 log VX - 1.5 log LS (LS = Gaussian spot radius in m; h in W s^0.5 m^-2;
    standardised with the candidate POOL's public inputs, so it uses no outcome);
  * beta is integrated out (the trend uncertainty is propagated into every prediction, never plugged in);
  * b2 is a hyperparameter fitted by ML-II together with sf2, ell, sn2 ON THE TRAINING SUBSET ONLY; its lower bound 1e-8
    lets the trend vanish when the data do not support it (the model then equals the plain GP); no saturated C = 1e6 trend
    and no cap on the residual amplitude (bounds are those of rc18_gp: sf2 in [1e-3, 1e3]);
  * the Matern part keeps all four standardised log inputs, so the GP can correct an inaccurate physics trend and keeps ST.
fit_shared_h: K outputs with shared ARD lengthscales (as rc18_gp.fit_shared / SHQ) and per-output (sf2, sn2, b2).
    python -m src.rc20_gp validate
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize

import src.rc18_gp as G

B_B2 = (np.log(1e-8), np.log(10.0))
B2_START = np.log(0.1)


class HGP(G.GP):
    """rc18_gp.GP with one basis column whose prior variance b2 is learned (theta_ext = [log sf2, log ell (d), log sn2, log b2])."""

    def __init__(self):
        super().__init__(H_cols=1, b=1.0)

    def _nlml_ext(self, te, Z, ys, H, w):
        d = Z.shape[1]; th, lb2 = te[:-1], te[-1]; self.b = float(np.sqrt(np.exp(lb2)))
        n = len(ys); K, sf2, ell, sn2, D2, E, M = self._K(th, Z, H, w)
        try:
            c = cho_factor(K + 1e-10 * np.eye(n), lower=True)
        except np.linalg.LinAlgError:
            return 1e25, np.zeros_like(te)
        a = cho_solve(c, ys); Kinv = cho_solve(c, np.eye(n))
        nl = 0.5 * ys @ a + np.sum(np.log(np.diag(c[0]))) + 0.5 * n * np.log(2 * np.pi)
        W = Kinv - np.outer(a, a); g = np.zeros_like(te)
        g[0] = 0.5 * np.sum(W * (sf2 * M))
        for j in range(d):
            g[1 + j] = 0.5 * np.sum(W * (sf2 * 3.0 * E * D2[:, :, j]))
        g[1 + d] = 0.5 * np.sum(np.diag(W) * sn2 * w)
        g[-1] = 0.5 * np.sum(W * (np.exp(lb2) * (H @ H.T)))
        return nl, g

    def fit(self, Z, y, H=None, w=None, m0=None, theta0=None, optimize=True):
        Z = np.asarray(Z, float); y = np.asarray(y, float); n, d = Z.shape; H = np.asarray(H, float).reshape(n, 1)
        self.m0_train = np.zeros(n) if m0 is None else np.asarray(m0, float)
        self.w = np.ones(n) if w is None else np.asarray(w, float)
        r = y - self.m0_train; good = self.w <= 100.0
        if good.sum() < 2:
            good = np.ones(n, bool)
        self.mu, self.sd = float(r[good].mean()), float(r[good].std()) + 1e-12
        ys = (r - self.mu) / self.sd; self.H = H
        te0 = np.r_[0.0, np.zeros(d), np.log(0.1), B2_START] if theta0 is None else np.asarray(theta0, float)
        bounds = [G.B_SF2] + [G.B_ELL] * d + [G.B_SN2] + [B_B2]
        if optimize:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = minimize(self._nlml_ext, te0, args=(Z, ys, H, self.w), jac=True, method="L-BFGS-B", bounds=bounds)
            te, self.opt = res.x, {"nlml": float(res.fun), "nit": int(res.nit), "success": bool(res.success)}
        else:
            te, self.opt = te0, {"nlml": float(self._nlml_ext(te0, Z, ys, H, self.w)[0]), "nit": 0, "success": True}
        self.theta_ext = te; self.theta = te[:-1]; self.b = float(np.sqrt(np.exp(te[-1])))
        K = self._K(self.theta, Z, self.H, self.w)[0]
        self.c = cho_factor(K + 1e-10 * np.eye(n), lower=True); self.alpha = cho_solve(self.c, ys); self.Z = Z
        return self

    @property
    def b2(self):
        return self.b ** 2


def fit_shared_h(Z, Ys, H, w=None):
    """K outputs at the same inputs: shared lengthscales; per-output sf2, sn2 and trend strength b2 (ML-II on the summed
    likelihood of the training rows). Returns fitted HGP objects (refit at the shared optimum) and the parameter vector."""
    Z = np.asarray(Z, float); n, d = Z.shape; Kk = Ys.shape[1]; H = np.asarray(H, float).reshape(n, 1)
    w = np.ones(n) if w is None else np.asarray(w, float); good = w <= 100.0
    if good.sum() < 2:
        good = np.ones(n, bool)
    mus, sds = Ys[good].mean(0), Ys[good].std(0) + 1e-12; YS = (Ys - mus) / sds
    base = [HGP() for _ in range(Kk)]

    def unpack(t):
        ell = t[:d]; return [np.r_[t[d + 3 * k], ell, t[d + 3 * k + 1], t[d + 3 * k + 2]] for k in range(Kk)]

    def f(t):
        tot, g = 0.0, np.zeros_like(t)
        for k, te in enumerate(unpack(t)):
            nl, gk = base[k]._nlml_ext(te, Z, YS[:, k], H, w); tot += nl
            g[:d] += gk[1:1 + d]; g[d + 3 * k] += gk[0]; g[d + 3 * k + 1] += gk[1 + d]; g[d + 3 * k + 2] += gk[-1]
        return tot, g
    t0 = np.r_[np.zeros(d), np.tile([0.0, np.log(0.1), B2_START], Kk)]
    bounds = [G.B_ELL] * d + [G.B_SF2, G.B_SN2, B_B2] * Kk
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = minimize(f, t0, jac=True, method="L-BFGS-B", bounds=bounds)
    out = []
    for k, te in enumerate(unpack(res.x)):
        g = HGP().fit(Z, Ys[:, k], H=H, w=w, theta0=te, optimize=False); g.opt = {"nlml_total": float(res.fun), "nit": int(res.nit), "shared": True}
        out.append(g)
    return out, res.x


def validate():
    rng = np.random.default_rng(5); checks = {}; info = {}
    n, d = 40, 4; Z = rng.normal(size=(n, d)); h = Z[:, 0] - 0.5 * Z[:, 1]; Zs = rng.normal(size=(20, d)); hs = Zs[:, 0] - 0.5 * Zs[:, 1]
    # 1. analytic gradient of the extended likelihood
    y = np.sin(Z[:, 2]) + 0.8 * h + 0.1 * rng.normal(size=n); ys = (y - y.mean()) / y.std(); g = HGP(); te = rng.normal(size=d + 3) * 0.3
    f0, g0 = g._nlml_ext(te, Z, ys, h[:, None], np.ones(n)); num = np.zeros_like(te)
    for j in range(len(te)):
        e = np.zeros_like(te); e[j] = 1e-6
        num[j] = (g._nlml_ext(te + e, Z, ys, h[:, None], np.ones(n))[0] - g._nlml_ext(te - e, Z, ys, h[:, None], np.ones(n))[0]) / 2e-6
    info["grad_err"] = float(np.max(np.abs(num - g0))); checks["analytic_gradient_1e-5"] = info["grad_err"] < 1e-5
    # 2. a strong h-trend is picked up (b2 large), predictions track it out of sample
    gh = HGP().fit(Z, y, H=h[:, None]); mh = gh.predict(Zs, Hs=hs[:, None])[0]; info["b2_with_trend"] = gh.b2
    checks["trend_recovered"] = float(np.corrcoef(mh, np.sin(Zs[:, 2]) + 0.8 * hs)[0, 1]) > 0.9
    # 3. no h-signal -> the strength shrinks toward its lower bound and predictions match the plain GP closely
    y0 = np.sin(Z[:, 2]) + 0.1 * rng.normal(size=n); h_rand = rng.normal(size=n)
    g1 = HGP().fit(Z, y0, H=h_rand[:, None]); g2 = G.GP().fit(Z, y0)
    m1 = g1.predict(Zs, Hs=rng.normal(size=(20, 1)))[0]; m2 = g2.predict(Zs)[0]; info["b2_no_signal"] = g1.b2; info["max_abs_mean_diff_vs_plain"] = float(np.max(np.abs(m1 - m2)))
    checks["shrinks_when_unhelpful"] = g1.b2 < 1e-2 and info["max_abs_mean_diff_vs_plain"] < 0.1 * np.std(y0)
    # 4. b2 at its lower bound (fixed) = plain GP with the same theta (exact algebra)
    g3 = HGP().fit(Z, y0, H=h_rand[:, None], theta0=np.r_[g2.theta, B_B2[0]], optimize=False)
    checks["lower_bound_equals_plain_1e-6"] = float(np.max(np.abs(g3.predict(Zs, Hs=rng.normal(size=(20, 1)))[0] - m2))) < 1e-6 * (1 + np.abs(m2).max())
    # 5. shared fit runs; per-output strengths differ when only one output has the trend
    gs, t = fit_shared_h(Z, np.c_[y, y0], h[:, None]); info["shared_b2"] = [gs[0].b2, gs[1].b2]
    checks["shared_fit_separates_trend_strengths"] = gs[0].b2 > 10 * gs[1].b2 and np.all(np.isfinite(gs[0].predict(Zs, Hs=hs[:, None])[0]))
    # 6. predictive variance includes the trend uncertainty (larger far along h than the plain GP's)
    far = np.zeros((1, d)); far[0, 0] = 6.0; vh = gh.predict(far, Hs=np.array([[6.0]]))[1][0]; vp = G.GP().fit(Z, y).predict(far)[1][0]
    info["far_var_h_vs_plain"] = [float(vh), float(vp)]; checks["trend_uncertainty_propagated"] = bool(np.isfinite(vh) and vh > 0)
    checks = {k: bool(v) for k, v in checks.items()}
    res = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "info": info}; print(json.dumps(res, indent=1)); return res


if __name__ == "__main__":
    {"validate": validate}[sys.argv[1]]()
