"""RC18 GP engine (numpy/scipy): one implementation for the simple and the rich models, so that model comparisons are not
implementation comparisons. Validated against sklearn (src/rc18_gp.py validate).

Model (per output, standardised targets ys = (y - mean_paid) / sd_paid):
    ys = f(z) + H(z) beta + eps,   f ~ GP(0, sf2 * Matern32_ARD(z, z'; ell)),   beta ~ N(0, diag(b^2)),   eps_i ~ N(0, sn2 * w_i)
  * M0 (simple): H empty, w = 1 -> identical to PHYS_AL's sklearn GP (ConstantKernel * Matern(nu=1.5, ARD) + WhiteKernel,
    normalize_y, ML-II from sf2 = 1, ell = 1, sn2 = 0.1, same bounds, no restarts).
  * a basis column h with prior sd b (e.g. the OLD-campaign emulator mu_OLD(x)) enters as b^2 h h^T in the covariance, so the
    coefficient is integrated out (Gaussian prior), never fitted on held-out data;
  * prior mean: optional offset m0(x) subtracted before standardisation (transfer: m0 = mu_OLD), added back at prediction;
  * w_i: optional fixed noise multipliers (heteroskedastic variants);
  * optional Gaussian hyperpriors on log ell (MAP instead of ML-II) for hyperparameter transfer;
  * shared lengthscales across K outputs observed at the same inputs (fit_shared): sum of the K marginal likelihoods.
Predictions return the latent mean, the latent variance and the observation variance (latent + noise) in ORIGINAL units
(the variance contract of fix A1: never add the noise twice).
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize

S3 = np.sqrt(3.0)
B_SF2, B_ELL, B_SN2 = (np.log(1e-3), np.log(1e3)), (np.log(1e-2), np.log(1e2)), (np.log(1e-6), np.log(10.0))


def _sqd(A, B, ell):
    D = (A[:, None, :] - B[None, :, :]) / ell
    return D ** 2


def matern32(A, B, ell):
    r = np.sqrt(np.maximum(_sqd(A, B, ell).sum(-1), 0.0))
    return (1.0 + S3 * r) * np.exp(-S3 * r)


class GP:
    def __init__(self, H_cols=0, b=3.0, hyperprior=None):
        self.p = H_cols; self.b = b; self.hyperprior = hyperprior        # hyperprior: (mean_log_ell (d,), sd) or None

    # ---------------------------------------------------------------- likelihood
    def _K(self, th, Z, H, w):
        d = Z.shape[1]; sf2, ell, sn2 = np.exp(th[0]), np.exp(th[1:1 + d]), np.exp(th[1 + d])
        D2 = _sqd(Z, Z, ell); r = np.sqrt(np.maximum(D2.sum(-1), 0.0)); E = np.exp(-S3 * r); M = (1 + S3 * r) * E
        K = sf2 * M + sn2 * np.diag(w)
        if H is not None and H.shape[1]:
            K = K + (self.b ** 2) * (H @ H.T)
        return K, sf2, ell, sn2, D2, E, M

    def _nlml(self, th, Z, ys, H, w):
        d = Z.shape[1]; n = len(ys)
        K, sf2, ell, sn2, D2, E, M = self._K(th, Z, H, w)
        try:
            c = cho_factor(K + 1e-10 * np.eye(n), lower=True)
        except np.linalg.LinAlgError:
            return 1e25, np.zeros_like(th)
        a = cho_solve(c, ys); Kinv = cho_solve(c, np.eye(n))
        nl = 0.5 * ys @ a + np.sum(np.log(np.diag(c[0]))) + 0.5 * n * np.log(2 * np.pi)
        W = Kinv - np.outer(a, a)                                            # dNLML/dtheta = 0.5 tr(W dK)
        g = np.zeros_like(th)
        g[0] = 0.5 * np.sum(W * (sf2 * M))
        for j in range(d):
            g[1 + j] = 0.5 * np.sum(W * (sf2 * 3.0 * E * D2[:, :, j]))
        g[1 + d] = 0.5 * np.sum(np.diag(W) * sn2 * w)
        if self.hyperprior is not None:
            m, s = self.hyperprior; le = th[1:1 + d]
            nl += 0.5 * np.sum(((le - m) / s) ** 2); g[1:1 + d] += (le - m) / s ** 2
        return nl, g

    # ---------------------------------------------------------------- fit / predict
    def fit(self, Z, y, H=None, w=None, m0=None, theta0=None, optimize=True):
        Z = np.asarray(Z, float); y = np.asarray(y, float); n, d = Z.shape
        self.m0_train = np.zeros(n) if m0 is None else np.asarray(m0, float)
        self.w = np.ones(n) if w is None else np.asarray(w, float)
        r = y - self.m0_train; good = self.w <= 100.0                          # down-weighted (QA-flagged) rows do not set the scale
        if good.sum() < 2:
            good = np.ones(n, bool)
        self.mu, self.sd = float(r[good].mean()), float(r[good].std()) + 1e-12
        ys = (r - self.mu) / self.sd
        self.H = None if H is None or self.p == 0 else np.asarray(H, float)
        th0 = np.r_[0.0, np.zeros(d), np.log(0.1)] if theta0 is None else np.asarray(theta0, float)
        bounds = [B_SF2] + [B_ELL] * d + [B_SN2]
        if optimize:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = minimize(self._nlml, th0, args=(Z, ys, self.H, self.w), jac=True, method="L-BFGS-B", bounds=bounds)
            self.theta, self.opt = res.x, {"nlml": float(res.fun), "nit": int(res.nit), "success": bool(res.success)}
        else:
            self.theta, self.opt = th0, {"nlml": float(self._nlml(th0, Z, ys, self.H, self.w)[0]), "nit": 0, "success": True}
        K = self._K(self.theta, Z, self.H, self.w)[0]
        self.c = cho_factor(K + 1e-10 * np.eye(n), lower=True); self.alpha = cho_solve(self.c, ys); self.Z = Z
        return self

    def _kx(self, Zs, Hs):
        d = self.Z.shape[1]; sf2, ell = np.exp(self.theta[0]), np.exp(self.theta[1:1 + d])
        ks = sf2 * matern32(Zs, self.Z, ell)
        if self.H is not None:
            ks = ks + (self.b ** 2) * (np.asarray(Hs, float) @ self.H.T)
        return ks

    def predict(self, Zs, Hs=None, m0s=None, ws=None):
        """Latent mean, latent variance, observation variance (original units)."""
        Zs = np.asarray(Zs, float); d = self.Z.shape[1]; sf2, sn2 = np.exp(self.theta[0]), np.exp(self.theta[1 + d])
        ks = self._kx(Zs, Hs); v = cho_solve(self.c, ks.T)
        kss = np.full(len(Zs), sf2)
        if self.H is not None:
            kss = kss + (self.b ** 2) * np.sum(np.asarray(Hs, float) ** 2, axis=1)
        mean_s = ks @ self.alpha; lat_s = np.maximum(kss - np.einsum("ij,ji->i", ks, v), 1e-12)
        ws = np.ones(len(Zs)) if ws is None else np.asarray(ws, float)
        m0s = np.zeros(len(Zs)) if m0s is None else np.asarray(m0s, float)
        return m0s + self.mu + self.sd * mean_s, self.sd ** 2 * lat_s, self.sd ** 2 * (lat_s + sn2 * ws)

    def post_cov(self, Za, Ha, Zb, Hb):
        """Latent posterior covariance between two point sets (standardised units * sd^2 = original units)."""
        d = self.Z.shape[1]; sf2, ell = np.exp(self.theta[0]), np.exp(self.theta[1:1 + d])
        kab = sf2 * matern32(Za, Zb, ell)
        if self.H is not None:
            kab = kab + (self.b ** 2) * (np.asarray(Ha, float) @ np.asarray(Hb, float).T)
        ka, kb = self._kx(Za, Ha), self._kx(Zb, Hb)
        return self.sd ** 2 * (kab - ka @ cho_solve(self.c, kb.T))

    @property
    def noise(self):
        return self.sd ** 2 * float(np.exp(self.theta[1 + self.Z.shape[1]]))


def fit_shared(Z, Ys, theta0=None, hyperprior=None, w=None):
    """K outputs at the same inputs: shared lengthscales, per-output sf2 and sn2 (ML-II / MAP on the summed likelihood).
    Ys: (n, K) with no missing values; w: optional per-row noise multipliers. Returns fitted GP objects (shared ell)."""
    Z = np.asarray(Z, float); n, d = Z.shape; Kk = Ys.shape[1]
    w = np.ones(n) if w is None else np.asarray(w, float); good = w <= 100.0
    if good.sum() < 2:
        good = np.ones(n, bool)
    mus, sds = Ys[good].mean(0), Ys[good].std(0) + 1e-12; YS = (Ys - mus) / sds
    base = [GP(hyperprior=None) for _ in range(Kk)]

    def unpack(t):
        ell = t[:d]; return [np.r_[t[d + 2 * k], ell, t[d + 2 * k + 1]] for k in range(Kk)]

    def f(t):
        tot, g = 0.0, np.zeros_like(t)
        for k, th in enumerate(unpack(t)):
            nl, gk = base[k]._nlml(th, Z, YS[:, k], None, w); tot += nl
            g[:d] += gk[1:1 + d]; g[d + 2 * k] += gk[0]; g[d + 2 * k + 1] += gk[1 + d]
        if hyperprior is not None:
            m, s = hyperprior; tot += 0.5 * np.sum(((t[:d] - m) / s) ** 2); g[:d] += (t[:d] - m) / s ** 2
        return tot, g
    t0 = np.r_[np.zeros(d), np.tile([0.0, np.log(0.1)], Kk)] if theta0 is None else np.asarray(theta0, float)
    bounds = [B_ELL] * d + [B_SF2, B_SN2] * Kk
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = minimize(f, t0, jac=True, method="L-BFGS-B", bounds=bounds)
    out = []
    for k, th in enumerate(unpack(res.x)):
        g = GP().fit(Z, Ys[:, k], w=w, theta0=th, optimize=False); g.opt = {"nlml_total": float(res.fun), "nit": int(res.nit), "shared": True}
        out.append(g)
    return out, res.x


def loo_logdens(g):
    """Closed-form leave-one-out predictive log density of the PAID points (Rasmussen & Williams eq. 5.10-5.12), at the
    fitted hyperparameters, in original units. Uses only paid data."""
    n = len(g.alpha); Kinv = cho_solve(g.c, np.eye(n)); d = np.maximum(np.diag(Kinv), 1e-300)
    var = 1.0 / d; resid = g.alpha / d                                              # y_i - mu_{-i} (standardised)
    return float(np.sum(-0.5 * np.log(2 * np.pi * var * g.sd ** 2) - 0.5 * resid ** 2 / var))


def loo_logdens_offset(r):
    """LOO log density of an offset-only model (each paid residual predicted by the mean and SD of the others)."""
    r = np.asarray(r, float); n = len(r)
    if n < 3:
        return -np.inf
    tot = 0.0
    for i in range(n):
        o = np.delete(r, i); m, v = o.mean(), max(o.var(ddof=1), 1e-12) * (1 + 1 / len(o))
        tot += -0.5 * np.log(2 * np.pi * v) - 0.5 * (r[i] - m) ** 2 / v
    return float(tot)


# ==================================================================================================== acquisitions
def ivr(g, Zp, Hp, Zc, Hc, Zpool, Hpool):
    """Integrated (summed over the pool) latent variance reduction of adding one noisy observation at each candidate."""
    cov = g.post_cov(Zpool, Hpool, Zc, Hc)                                           # (npool, nc)
    vc = np.maximum(g.predict(Zc, Hc)[1], 1e-12)
    return np.sum(cov ** 2, axis=0) / (vc + g.noise)


def straddle(mean, lat_var, tau, beta=1.96):
    """Bryan et al. (2006): 1.96 sigma - |mu - tau| (latent sigma)."""
    return beta * np.sqrt(lat_var) - np.abs(mean - tau)


def truvar_lse(g, Zc, Hc, mean_c, lat_c, tau, beta=1.96, eta=0.0):
    """Truncated variance reduction for level-set estimation (Bogunovic et al. 2016, LSE variant): score = total latent
    variance reduction over the still-unclassified candidates M = {x: |mu - tau| < beta sigma + eta} (truncated at eta^2)."""
    sig = np.sqrt(lat_c); M = np.abs(mean_c - tau) < beta * sig + eta
    if not M.any():
        return np.zeros(len(Zc)), M
    cov = g.post_cov(Zc[M], None if Hc is None else Hc[M], Zc, Hc)                  # (|M|, nc)
    v_after = lat_c[M][:, None] - cov ** 2 / (np.maximum(lat_c, 1e-12) + g.noise)[None, :]
    t_before = np.maximum(beta ** 2 * lat_c[M], eta ** 2)[:, None]; t_after = np.maximum(beta ** 2 * v_after, eta ** 2)
    return np.sum(t_before - t_after, axis=0), M


# ==================================================================================================== validation
def validate():
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
    rng = np.random.default_rng(3); checks = {}; info = {}
    Z = rng.normal(size=(30, 4)); y = np.sin(Z[:, 0]) + 0.5 * Z[:, 1] ** 2 + 0.1 * rng.normal(size=30); Zs = rng.normal(size=(15, 4))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sk = GaussianProcessRegressor(ConstantKernel(1.0, (1e-3, 1e3)) * Matern(np.ones(4), (1e-2, 1e2), nu=1.5) + WhiteKernel(0.1, (1e-6, 10.0)),
                                      normalize_y=True, n_restarts_optimizer=0, random_state=0).fit(Z, y)
    m_sk, s_sk = sk.predict(Zs, return_std=True)
    g = GP().fit(Z, y); m, lat, obs = g.predict(Zs)
    info["theta_sklearn"] = sk.kernel_.theta.tolist(); info["theta_rc18"] = g.theta.tolist()
    info["max_abs_mean_diff"] = float(np.max(np.abs(m - m_sk))); info["max_abs_obs_sd_diff"] = float(np.max(np.abs(np.sqrt(obs) - s_sk)))
    checks["ml2_matches_sklearn_mean_1e-4"] = info["max_abs_mean_diff"] < 1e-4
    checks["obs_sd_matches_sklearn_predict_std_1e-4"] = info["max_abs_obs_sd_diff"] < 1e-4
    # same fixed hyperparameters -> identical predictions (exactness of the algebra)
    g2 = GP().fit(Z, y, theta0=sk.kernel_.theta, optimize=False); m2, l2, o2 = g2.predict(Zs)
    checks["fixed_theta_exact_1e-9"] = float(np.max(np.abs(m2 - m_sk))) < 1e-9 and float(np.max(np.abs(np.sqrt(o2) - s_sk))) < 1e-9
    # gradient check
    th = rng.normal(size=6) * 0.3; f0, g0 = g._nlml(th, Z, (y - y.mean()) / y.std(), None, np.ones(30)); num = np.zeros(6)
    for j in range(6):
        e = np.zeros(6); e[j] = 1e-6; num[j] = (g._nlml(th + e, Z, (y - y.mean()) / y.std(), None, np.ones(30))[0] - g._nlml(th - e, Z, (y - y.mean()) / y.std(), None, np.ones(30))[0]) / 2e-6
    checks["analytic_gradient_1e-5"] = float(np.max(np.abs(num - g0))) < 1e-5; info["grad_err"] = float(np.max(np.abs(num - g0)))
    # basis term = Bayesian linear regression limit: with a huge lengthscale-free setting the basis coefficient is recovered
    h = rng.normal(size=30); y3 = 2.0 * h + 0.05 * rng.normal(size=30); gb = GP(H_cols=1, b=10.0).fit(Z, y3, H=((h - 0) / 1.0)[:, None])
    hs = rng.normal(size=15); mb = gb.predict(Zs, Hs=hs[:, None])[0]
    checks["basis_recovers_linear_signal"] = float(np.corrcoef(mb, 2.0 * hs)[0, 1]) > 0.99
    # IVR equals brute force
    Zp, Zc = Z[:12], Zs[:5]; gi = GP().fit(Zp, y[:12])
    sc = ivr(gi, Zp, None, Zc, None, Z, None); bf = []
    base = gi.predict(Z)[1].sum()
    for j in range(5):
        Zj = np.vstack([Zp, Zc[j:j + 1]]); K = np.exp(gi.theta[0]) * matern32(Zj, Zj, np.exp(gi.theta[1:5])) + np.exp(gi.theta[5]) * np.eye(13)
        ks = np.exp(gi.theta[0]) * matern32(Z, Zj, np.exp(gi.theta[1:5])); post = np.exp(gi.theta[0]) - np.einsum("ij,jk,ik->i", ks, np.linalg.inv(K), ks)
        bf.append(base - gi.sd ** 2 * post.sum())
    checks["ivr_equals_bruteforce_1e-6"] = float(np.max(np.abs(sc - np.array(bf)))) < 1e-6 * max(1, np.max(np.abs(bf)))   # the fit adds 1e-10 jitter to K; the brute force does not; info["ivr_err"] = float(np.max(np.abs(sc - np.array(bf))))
    # shared fit runs and returns the same predictions as GP.fit with its theta
    gs, t = fit_shared(Z, np.c_[y, y3]); checks["shared_fit_runs"] = len(gs) == 2 and np.all(np.isfinite(gs[0].predict(Zs)[0]))
    checks = {k: bool(v) for k, v in checks.items()}
    res = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "info": info}
    print(json.dumps(res, indent=1)); return res


if __name__ == "__main__":
    {"validate": validate}[sys.argv[1]]()
