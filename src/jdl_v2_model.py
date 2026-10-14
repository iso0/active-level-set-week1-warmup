"""Joint depth-label model V2 (covariance-preserving uncertain coupling) — repository port of Astra's
`outputs/astra_joint_model_v2/joint_model_v2.py` (version jdl-v2-port-1.0).

Model (fixed fold reference pool Q, standardized log inputs):
    f, g ~ independent GP(0, k_f);  delta ~ GP(0, k_delta) centred on Q;  theta ~ N(theta0, s_theta^2)
    rho in {0, 0.5, 1} with prior masses 1/3;   h = rho f + sqrt(1 - rho^2) g - theta + delta
    z = log(A / 111 um) | f ~ N(f, sigma_z^2);   Y | h ~ Bernoulli(Phi(h / tau))
Cov(h, h | rho) is the same for every rho, so rho controls sharing, not the marginal classifier prior.

Inference per component: exact Gaussian conditioning of f on the paid responses, then probit expectation propagation
on the paid labels (sites start at zero, parallel updates, damping 0.5, stop after three consecutive relative site
changes < 1e-8, at most 200 iterations).  Component masses are prior x approximate label evidence (the response
evidence is identical across components and cancels).  Prediction integrates the mixture.  If EP fails in ANY
component, EVERY component is refitted with the declared Laplace routine (whitened Newton, acceptance: finite
objective and gradient infinity norm <= 2e-6); a failing fallback raises.  No component is ever dropped.

Independent of Astra's code in three places: the EP evidence uses a separately derived closed form (natural
parameters, no division by site precisions), the Laplace mode uses a damped whitened Newton with backtracking instead of
scipy's trust-exact, and the bivariate normal CDF / probit terms come from `src.jdl_model` (Genz BVNU, erfcx + inverted
Mills series).  The public API mirrors Astra's so that his reference checks can be run against this port unchanged.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
from numpy.polynomial.hermite import hermgauss
from scipy.linalg import cho_factor, cho_solve, solve_triangular
from scipy.special import log_ndtr, logsumexp, ndtr

from src.jdl_model import Config, matern32, phi2, probit_terms, STAGE_M_CONFIG  # noqa: F401  (re-exported for callers)

VERSION = "jdl-v2-port-1.0"
RHOS = (0.0, 0.5, 1.0)
EP_DAMPING, EP_TOL, EP_CONSECUTIVE, EP_MAX_ITER = 0.5, 1e-8, 3, 200
LAPLACE_ACCEPT, LAPLACE_TOL, LAPLACE_MAX_ITER = 2e-6, 1e-11, 200
NUMERICAL_ERRORS = (RuntimeError, FloatingPointError, np.linalg.LinAlgError)


def matrix(x):
    x = np.asarray(x, float)
    if x.ndim == 1:
        x = x[:, None]
    if x.ndim != 2 or not np.isfinite(x).all():
        raise ValueError("Expected finite input matrix")
    return x


@lru_cache(None)
def gh(order):
    """Probabilists' Gauss-Hermite rule: nodes and weights for E[g(Z)], Z ~ N(0, 1)."""
    u, w = hermgauss(order)
    return u * np.sqrt(2.0), w / np.sqrt(np.pi)


# ======================================================================================== probit inference
def _sites_posterior(m, K, ttau, tnu):
    """Gaussian posterior N(mu, Sigma) of prior N(m, K) times sites exp(tnu h - ttau h^2 / 2); also returns
    R = (K + diag(1/ttau))^{-1} in the stable form sw B^{-1} sw and the Cholesky factor of B = I + sw K sw."""
    n = len(m)
    sw = np.sqrt(np.maximum(ttau, 0.0))
    B = np.eye(n) + sw[:, None] * K * sw[None, :]
    L = np.linalg.cholesky(B)
    V = solve_triangular(L, sw[:, None] * K, lower=True)
    Sigma = K - V.T @ V
    Sigma = (Sigma + Sigma.T) / 2
    mu = m + Sigma @ (tnu - ttau * m)
    Binv_sw = cho_solve((L, True), np.diag(sw))
    R = sw[:, None] * Binv_sw
    return mu, Sigma, (R + R.T) / 2, L


def ep_probit(m, K, y, tau):
    """Damped parallel EP for prod_i Phi(s_i h_i / tau) under h ~ N(m, K)."""
    n = len(y)
    s = 2.0 * np.asarray(y, float) - 1.0
    ttau, tnu = np.zeros(n), np.zeros(n)
    stable, change, it = 0, np.inf, 0
    for it in range(1, EP_MAX_ITER + 1):
        mu, Sigma, R, L = _sites_posterior(m, K, ttau, tnu)
        d = np.diag(Sigma)
        tau_c = 1.0 / d - ttau
        if np.min(tau_c) <= 0:
            raise FloatingPointError("EP: nonpositive cavity precision")
        vc = 1.0 / tau_c
        mc = vc * (mu / d - tnu)
        den = np.sqrt(tau * tau + vc)
        t = s * mc / den
        _, lam, curv = probit_terms(t)
        m_hat = mc + s * vc * lam / den
        v_hat = vc - vc * vc * curv / (tau * tau + vc)
        if np.min(v_hat) <= 0 or not np.isfinite(m_hat).all():
            raise FloatingPointError("EP: nonpositive or nonfinite tilted moments")
        ttau_new = np.maximum(1.0 / v_hat - 1.0 / vc, 0.0)
        tnu_new = m_hat / v_hat - mc / vc
        change = max(float(np.max(np.abs(ttau_new - ttau) / (1 + np.abs(ttau)))), float(np.max(np.abs(tnu_new - tnu) / (1 + np.abs(tnu)))))
        ttau = (1 - EP_DAMPING) * ttau + EP_DAMPING * ttau_new
        tnu = (1 - EP_DAMPING) * tnu + EP_DAMPING * tnu_new
        stable = stable + 1 if change < EP_TOL else 0
        if stable >= EP_CONSECUTIVE:
            break
    else:
        raise RuntimeError(f"EP did not converge in {EP_MAX_ITER} iterations (last relative change {change:.3e})")
    mu, Sigma, R, L = _sites_posterior(m, K, ttau, tnu)
    d = np.diag(Sigma)
    tau_c = 1.0 / d - ttau
    if np.min(tau_c) <= 0:
        raise FloatingPointError("EP: nonpositive final cavity precision")
    vc = 1.0 / tau_c
    mc = vc * (mu / d - tnu)
    log_Z_tilted = log_ndtr(s * mc / np.sqrt(tau * tau + vc))
    # log Z_EP = log N(mu_site; m, K + S^-1) + sum_i [log Zhat_i - log N(mc_i; mu_site_i, vc_i + 1/ttau_i)], rewritten in
    # natural parameters (p = tnu - ttau m) so that no term divides by a site precision.
    p = tnu - ttau * m
    q1 = 1.0 + ttau * vc
    quad_sites = (-tnu * tnu * vc + 2 * tnu * (m - mc) + 2 * ttau * m * tnu * vc - ttau * m * m * q1 + ttau * mc * mc) / (2 * q1)
    log_evidence = float(log_Z_tilted.sum() - np.log(np.diag(L)).sum() + 0.5 * np.log(q1).sum() + 0.5 * p @ Sigma @ p + quad_sites.sum())
    alpha = tnu - ttau * mu                                                   # = K^{-1} (mu - m)
    return {"alpha": alpha, "R": R, "mean": mu, "cov": Sigma, "log_evidence": log_evidence,
            "diagnostics": {"method": "ep", "status": "accepted", "iterations": it, "relative_site_change": change,
                            "min_cavity_variance": float(vc.min()), "min_posterior_variance": float(d.min()),
                            "max_site_precision": float(ttau.max())}}


def laplace_probit(m, K, y, tau):
    """Laplace mode of prod_i Phi(s_i h_i / tau) under h ~ N(m, K) in whitened coordinates h = m + L v."""
    n = len(y)
    s = 2.0 * np.asarray(y, float) - 1.0
    Lk = np.linalg.cholesky(K)

    def psi(v):
        h = m + Lk @ v
        lp, lam, curv = probit_terms(s * h / tau)
        return 0.5 * v @ v - lp.sum(), v - Lk.T @ (s * lam / tau), curv / tau ** 2

    v = np.zeros(n)
    val, grad, W = psi(v)
    status, it = "max_iterations", 0
    for it in range(1, LAPLACE_MAX_ITER + 1):
        if np.max(np.abs(grad)) <= LAPLACE_TOL:
            status = "converged"; break
        H = np.eye(n) + (Lk.T * W) @ Lk
        step = -np.linalg.solve(H, grad)
        a = 1.0
        while True:                                                            # backtracking (Armijo) line search
            nv, ng, nW = psi(v + a * step)
            if np.isfinite(nv) and nv <= val + 1e-4 * a * grad @ step:
                break
            a *= 0.5
            if a < 1e-12:
                break
        if a < 1e-12:
            status = "line_search_failed"; break
        v, val, grad, W = v + a * step, nv, ng, nW
    g_inf = float(np.max(np.abs(grad))) if n else 0.0
    if not np.isfinite(val) or g_inf > LAPLACE_ACCEPT:
        raise RuntimeError(f"Laplace stationarity failure: gradient {g_inf:.3e}, status {status}")
    h = m + Lk @ v
    sw = np.sqrt(W)
    B = np.eye(n) + sw[:, None] * K * sw[None, :]
    Lb = np.linalg.cholesky(B)
    R = sw[:, None] * cho_solve((Lb, True), np.diag(sw))
    Sigma = K - K @ R @ K
    return {"alpha": solve_triangular(Lk.T, v, lower=False), "R": (R + R.T) / 2, "mean": h, "cov": (Sigma + Sigma.T) / 2,
            "log_evidence": float(-val - np.log(np.diag(Lb)).sum()),
            "diagnostics": {"method": "laplace", "status": "accepted", "solver_status": status, "gradient_inf": g_inf, "iterations": it}}


def infer_probit(m, K, y, tau, method="ep"):
    """Fixed-prior probit inference; failures are raised for the caller's whole-mixture policy."""
    if not len(y):
        return {"alpha": np.empty(0), "R": np.empty((0, 0)), "mean": np.asarray(m).copy(), "cov": np.asarray(K).copy(), "log_evidence": 0.0,
                "diagnostics": {"method": method, "status": "prior", "iterations": 0}}
    if method == "ep":
        return ep_probit(m, K, y, tau)
    if method == "laplace":
        return laplace_probit(m, K, y, tau)
    raise ValueError(method)


# ======================================================================================== one coupling component
class Component:
    def __init__(self, x_ref, config, rho):
        if not 0 <= rho <= 1:
            raise ValueError("rho must lie in [0, 1]")
        if config.f_mean != 0:
            raise ValueError("V2 fixes the response and residual GP means at zero")
        self.x_ref = matrix(x_ref).copy()
        self.c = config
        self.rho = float(rho)
        self.s = float(np.sqrt(1.0 - self.rho ** 2))
        self.kdbar = float(self.kd_raw(self.x_ref, self.x_ref).mean())
        self.xo = np.empty((0, self.x_ref.shape[1]))

    def kf(self, a, b):
        return matern32(a, b, self.c.f_amplitude, self.c.f_lengthscale)

    def kd_raw(self, a, b):
        return matern32(a, b, self.c.discrepancy_amplitude, self.c.discrepancy_lengthscale)

    def kd(self, a, b):
        a, b = matrix(a), matrix(b)
        return self.kd_raw(a, b) - self.kd_raw(a, self.x_ref).mean(1)[:, None] - self.kd_raw(self.x_ref, b).mean(0)[None, :] + self.kdbar

    def response(self, x, z=None):
        """Mean and covariance of f after conditioning on the paid responses."""
        x = matrix(x); z = x if z is None else matrix(z)
        mean, cov = np.zeros(len(x)), self.kf(x, z)
        if len(self.xo):
            k = self.kf(x, self.xo)
            mean = k @ self.za
            cov = cov - k @ cho_solve(self.zchol, self.kf(self.xo, z))
        return mean, cov

    def prior_h(self, x, z=None):
        z = x if z is None else z
        mf, cf = self.response(x, z)
        r = self.rho
        return r * mf - self.c.threshold_mean, r * r * cf + (1 - r * r) * self.kf(x, z) + self.kd(x, z) + self.c.threshold_sd ** 2

    def fit(self, x, y, z, method):
        self.xp = matrix(x).copy()
        self.yp = np.asarray(y, int).copy()
        good = np.isfinite(z)
        self.xo = self.xp[good]
        zz = np.asarray(z, float)[good]
        if len(zz):
            K = self.kf(self.xo, self.xo)
            K.flat[::len(K) + 1] += self.c.response_noise_sd ** 2 + self.c.jitter
            self.zchol = cho_factor(K, lower=True)
            self.za = cho_solve(self.zchol, zz)
        m, K = self.prior_h(self.xp)
        K = (K + K.T) / 2
        if len(K):
            K.flat[::len(K) + 1] += self.c.jitter
        self.hp_prior = (m, K)
        self.inf = infer_probit(m, K, self.yp, self.c.probit_scale, method)
        return self

    def posterior(self, x, full=False):
        x = matrix(x); n = len(x); r, s, c = self.rho, self.s, self.c
        a, R = self.inf["alpha"], self.inf["R"]
        mf, cf = self.response(x)
        mh, ch = self.prior_h(x)
        _, cfp = self.response(x, self.xp)
        _, chp = self.prior_h(x, self.xp)
        fp = r * cfp                                                         # Cov(f(x), h_P | z)
        out = {"f_mean": mf + fp @ a, "h_mean": mh + chp @ a}
        fc = cf - fp @ R @ fp.T
        hc = ch - chp @ R @ chp.T
        out["f_cov"] = (fc + fc.T) / 2; out["h_cov"] = (hc + hc.T) / 2
        out["f_h_cov"] = r * cf - fp @ R @ chp.T
        tp = np.full((1, len(self.xp)), -c.threshold_sd ** 2)
        out["theta_mean"] = float(c.threshold_mean + (tp @ a)[0])
        out["theta_var"] = float(c.threshold_sd ** 2 - (tp @ R @ tp.T)[0, 0])
        dp = self.kd(x, self.xp)
        out["delta_mean"] = dp @ a
        out["delta_var"] = np.diag(self.kd(x, x)) - np.einsum("ij,jk,ik->i", dp, R, dp)
        if np.min(np.diag(hc), initial=0) < -1e-7 or np.min(np.diag(fc), initial=0) < -1e-7:
            raise FloatingPointError("Negative component variance")
        if full:
            gp = s * self.kf(x, self.xp)
            D = 3 * n + 1
            mean = np.r_[mf, np.zeros(2 * n), c.threshold_mean]
            cov = np.zeros((D, D))
            cov[:n, :n] = cf; cov[n:2 * n, n:2 * n] = self.kf(x, x); cov[2 * n:3 * n, 2 * n:3 * n] = self.kd(x, x); cov[-1, -1] = c.threshold_sd ** 2
            cross = np.vstack([fp, gp, dp, tp])
            out["joint_mean"] = mean + cross @ a
            out["joint_cov"] = cov - cross @ R @ cross.T
            out["H"] = np.c_[r * np.eye(n), s * np.eye(n), np.eye(n), -np.ones((n, 1))]   # h = rho f + s g + delta - theta
        return out


# ======================================================================================== mixture
class JointModelV2:
    def __init__(self, x_ref, config=None, rhos=RHOS, prior_weights=None, inference="ep", allow_fallback=True):
        self.x_ref = matrix(x_ref).copy()
        self.c = config or STAGE_M_CONFIG
        self.rhos = tuple(float(r) for r in rhos)
        self.prior_weights = np.ones(len(self.rhos)) / len(self.rhos) if prior_weights is None else np.asarray(prior_weights, float)
        if np.any(self.prior_weights <= 0) or not np.isclose(self.prior_weights.sum(), 1):
            raise ValueError("Proper positive mixture masses required")
        self.inference, self.allow_fallback = inference, allow_fallback

    def fit(self, x_paid, y_paid, z_paid, use_response=True, _inject_failure=None):
        """`_inject_failure`: validation hook — a rho value whose EP solve is forced to raise (fallback test only)."""
        x = matrix(x_paid); y = np.asarray(y_paid, float); z = np.asarray(z_paid, float).copy()
        if y.shape != (len(x),) or z.shape != (len(x),) or not np.isin(y, [0, 1]).all() or np.isinf(z).any():
            raise ValueError("Paid arrays invalid; a missing response must be NaN")
        self.use_response = bool(use_response)
        if not use_response:
            z[:] = np.nan
        self.solve_count, self.failures = 0, []
        actual = self.rhos if np.isfinite(z).any() else self.rhos[:1]          # no response: one identical classifier law
        methods = [self.inference, "laplace"] if self.inference == "ep" and self.allow_fallback else [self.inference]
        comps = []
        for method in methods:
            try:
                comps = []
                for rho in actual:
                    self.solve_count += 1
                    if method == "ep" and _inject_failure is not None and np.isclose(rho, _inject_failure):
                        raise RuntimeError(f"Injected EP failure at rho={rho} (validation only)")
                    comps.append(Component(self.x_ref, self.c, rho).fit(x, y, z, method))
                break
            except NUMERICAL_ERRORS as ex:
                self.failures.append({"method": method, "error": str(ex)})
                if method == "laplace" or not self.allow_fallback:
                    raise
        if len(comps) != len(actual):
            raise RuntimeError("Incomplete mixture")
        if len(actual) == 1 and len(self.rhos) > 1:                            # same h fit; each rho keeps its own cross-output prior
            proto, comps = comps[0], []
            for rho in self.rhos:
                obj = Component(self.x_ref, self.c, rho)
                obj.xp, obj.yp, obj.xo, obj.hp_prior, obj.inf = proto.xp, proto.yp, proto.xo, proto.hp_prior, proto.inf
                comps.append(obj)
        self.components = comps
        logZ = np.array([cp.inf["log_evidence"] for cp in comps])
        lw = np.log(self.prior_weights) + logZ
        self.weights = np.exp(lw - logsumexp(lw))
        self.diagnostics = {"version": VERSION, "n_paid": len(y), "n_negative": int((y == 0).sum()), "n_response": int(np.isfinite(z).sum()),
                            "component_solves": self.solve_count, "fallback": bool(self.failures), "failures": self.failures,
                            "rho_values": list(self.rhos), "rho_weights": self.weights.tolist(), "log_evidence": logZ.tolist(),
                            "components": [cp.inf["diagnostics"] for cp in comps]}
        return self

    def component_posteriors(self, x, full=False):
        return [cp.posterior(x, full) for cp in self.components]

    def component_probabilities(self, x):
        tau2 = self.c.probit_scale ** 2
        return np.array([ndtr(q["h_mean"] / np.sqrt(tau2 + np.maximum(np.diag(q["h_cov"]), 0))) for q in self.component_posteriors(x)])

    def predict_proba(self, x):
        return self.weights @ self.component_probabilities(x)

    def posterior(self, x):
        qs = self.component_posteriors(x)
        ans = {}
        for name in ("h", "f"):
            means = np.array([q[name + "_mean"] for q in qs])
            mu = self.weights @ means
            ans[name + "_mean"] = mu
            ans[name + "_cov"] = sum(w * (q[name + "_cov"] + np.outer(m - mu, m - mu)) for w, q, m in zip(self.weights, qs, means))
            ans[name + "_between_component_var"] = self.weights @ (means - mu) ** 2
        ans["f_h_cov"] = sum(w * (q["f_h_cov"] + np.outer(q["f_mean"] - ans["f_mean"], q["h_mean"] - ans["h_mean"])) for w, q in zip(self.weights, qs))
        tm = sum(w * q["theta_mean"] for w, q in zip(self.weights, qs))
        ans["theta_mean"] = tm
        ans["theta_var"] = sum(w * (q["theta_var"] + (q["theta_mean"] - tm) ** 2) for w, q in zip(self.weights, qs))
        return ans

    def probability_interval(self, x, level=0.90):
        """Interval for pi = Phi(h / tau) from the mixture of Gaussian h marginals (bisection on the mixture CDF)."""
        qs = self.component_posteriors(x)
        means = np.array([q["h_mean"] for q in qs])
        sd = np.sqrt(np.maximum(np.array([np.diag(q["h_cov"]) for q in qs]), 1e-16))
        lo0, hi0 = np.min(means - 10 * sd, axis=0), np.max(means + 10 * sd, axis=0)
        bounds = []
        for target in ((1 - level) / 2, (1 + level) / 2):
            a, b = lo0.copy(), hi0.copy()
            for _ in range(60):
                mid = (a + b) / 2
                cdf = self.weights @ ndtr((mid - means) / sd)
                a, b = np.where(cdf < target, mid, a), np.where(cdf < target, b, mid)
            bounds.append(ndtr((a + b) / (2 * self.c.probit_scale)))
        return np.array(bounds)

    def integrated_probability_variance(self, x):
        m1 = m2 = 0.0
        for w, q in zip(self.weights, self.component_posteriors(x)):
            v = np.maximum(np.diag(q["h_cov"]), 0)
            a = q["h_mean"] / np.sqrt(self.c.probit_scale ** 2 + v)
            m1 = m1 + w * ndtr(a)
            m2 = m2 + w * phi2(a, a, v / (self.c.probit_scale ** 2 + v))
        return m2 - m1 ** 2

    def acquisition(self, x_query, x_integrate=None, gh_order=15, cdf_order=48, observe_response=True, observe_label=True):
        """Expected reduction of the pool-averaged Var[pi] after observing the paired (Z_j, Y_j); the future response
        and label both reweight the components (not an average of component utilities)."""
        xq = matrix(x_query); xi = self.x_ref if x_integrate is None else matrix(x_integrate)
        ni, nq = len(xi), len(xq)
        qs = self.component_posteriors(np.vstack([xi, xq]))
        tau2 = self.c.probit_scale ** 2
        base = sum(w * ndtr(q["h_mean"][:ni] / np.sqrt(tau2 + np.maximum(np.diag(q["h_cov"])[:ni], 0))) for w, q in zip(self.weights, qs))
        observe_response = bool(observe_response and self.use_response)
        nodes, ghw = gh(gh_order)
        response, label, tails = np.zeros(nq), np.zeros(nq), np.zeros(nq)
        for j in range(nq):
            jj = ni + j; ids = np.r_[np.arange(ni), jj]
            vz = np.array([max(q["f_cov"][jj, jj], 0) + self.c.response_noise_sd ** 2 for q in qs])
            mf = np.array([q["f_mean"][jj] for q in qs])
            if observe_response:
                z = (mf[:, None] + np.sqrt(vz[:, None]) * nodes).ravel()
                zw = (self.weights[:, None] * ghw).ravel()
                logw = np.log(self.weights)[:, None] - 0.5 * (np.log(2 * np.pi * vz)[:, None] + (z - mf[:, None]) ** 2 / vz[:, None])
                postw = np.exp(logw - logsumexp(logw, axis=0))
            else:
                z, zw, postw = np.array([0.0]), np.array([1.0]), self.weights[:, None]
            pis, qjs, joints = [], [], []
            for k, q in enumerate(qs):
                mm = q["h_mean"][ids]; C = q["h_cov"][np.ix_(ids, ids)]
                if observe_response:
                    cross = q["f_h_cov"][jj, ids]
                    C = C - np.outer(cross, cross) / vz[k]
                    means = mm[None, :] + (z - mf[k])[:, None] * cross[None, :] / vz[k]
                else:
                    means = mm[None, :]
                if np.min(np.diag(C)) < -1e-7:
                    raise FloatingPointError("Negative response-conditioned variance")
                den = np.sqrt(tau2 + np.maximum(np.diag(C), 0))
                aa = means / den
                pis.append(ndtr(aa[:, :-1])); qjs.append(ndtr(aa[:, -1]))
                if observe_label:
                    corr = C[:-1, -1] / (den[:-1] * den[-1])
                    joints.append(phi2(aa[:, :-1], aa[:, -1, None], corr[None, :], order=cdf_order))
            pz = np.einsum("kg,kgm->gm", postw, np.asarray(pis))
            qz = np.einsum("kg,kg->g", postw, np.asarray(qjs))
            response[j] = float(zw @ np.mean((pz - base) ** 2, axis=1))
            if observe_label:
                J = np.einsum("kg,kgm->gm", postw, np.asarray(joints))
                valid = (qz > 1e-12) & (qz < 1 - 1e-12)
                term = np.zeros(len(z))
                term[valid] = np.mean((J[valid] - pz[valid] * qz[valid, None]) ** 2 / (qz[valid, None] * (1 - qz[valid, None])), axis=1)
                label[j] = float(zw @ term)
                tails[j] = float(zw[~valid].sum() * 1e-12)
        return {"score": response + label, "response_component": response, "label_component": label, "omitted_tail_bound": tails,
                "gh_order": gh_order, "cdf_order": cdf_order}
