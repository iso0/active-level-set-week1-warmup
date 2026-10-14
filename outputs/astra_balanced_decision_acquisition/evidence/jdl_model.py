"""Joint depth-label GP: repository port of Astra's Week 20 reference (outputs/astra_week20_method_development).

Model (fixed hyperparameters):
    f ~ GP(f_mean, k_f),  theta ~ N(theta_mean, threshold_sd^2),  delta ~ GP(0, k_delta centered on a fixed pool Q),
    h(x) = f(x) - theta + delta(x),   z | f ~ N(f, response_noise_sd^2),   Y | h ~ Bernoulli(Phi(h / probit_scale)).
Inference: exact Gaussian conditioning of f on the paid continuous responses, then a joint probit Laplace update on
the paid labels, keeping every f / theta / delta / h cross-covariance (GPML ch. 3 construction).

Independent of the reference implementation in three places (so that parity is a real check, not a copy):
  * the Laplace mode is found by a GPML Algorithm-3.1 Newton iteration on h with a backtracking line search
    (the reference uses a whitened trust-region Newton);
  * the bivariate normal CDF uses Genz's BVNU algorithm (Drezner-Wesolowsky Gauss-Legendre form, with the
    |rho| >= 0.925 asymptotic branch); the reference uses Plackett's angular integral with adaptive quadrature;
  * the inverse Mills ratio uses erfcx for t >= -30 and an asymptotic series (inverted Mills series) below.
Public API mirrors the reference (Config, JointDepthLabelGP, phi2, probit_terms, fit_paid_prefix) so that
Astra's run_checks.py can be executed against this module unchanged.

Information contract: fit() receives paid rows only (x, canonical 0/1 label, z = log(A/111) or NaN when the
response is missing).  The discrepancy is centered on x_ref, the fixed feature-only candidate pool; predictions
need only x.  Nothing here touches files, labels of unpaid rows or test outputs.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.polynomial.hermite import hermgauss
from numpy.polynomial.legendre import leggauss
from scipy.linalg import cho_factor, cho_solve
from scipy.special import erfcx, log_ndtr, ndtr

VERSION = "jdl-port-1.0"
GRADIENT_ACCEPT = 2e-6          # Astra's acceptance criterion on the whitened gradient (infinity norm)


@dataclass(frozen=True)
class Config:
    """Defaults equal Astra's one-dimensional prototype; STAGE_M_CONFIG holds the frozen four-input priors."""
    f_amplitude: float = 0.6
    f_lengthscale: object = 0.5
    discrepancy_amplitude: float = 0.35
    discrepancy_lengthscale: object = 0.5
    threshold_mean: float = 0.0
    threshold_sd: float = 0.35
    response_noise_sd: float = 0.03
    probit_scale: float = 0.15
    f_mean: float = 0.0
    jitter: float = 1e-10


STAGE_M_CONFIG = Config(f_amplitude=0.60, f_lengthscale=(1.5, 1.5, 1.5, 1.5), discrepancy_amplitude=0.35,
                        discrepancy_lengthscale=(1.5, 1.5, 1.5, 1.5), threshold_mean=0.0, threshold_sd=0.35,
                        response_noise_sd=0.03, probit_scale=0.15, f_mean=0.0, jitter=1e-10)
NEWTON_MAX_ITER = 100
NEWTON_GRAD_TOL = 1e-11


def _x(x):
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    if x.ndim != 2 or not np.isfinite(x).all():
        raise ValueError("X must be a finite two-dimensional input matrix")
    return x


def matern32(x, z, amplitude, lengthscale):
    x, z = _x(x), _x(z)
    ell = np.broadcast_to(np.asarray(lengthscale, float), (x.shape[1],))
    d2 = np.zeros((len(x), len(z)))
    for k in range(x.shape[1]):                      # memory-light distance accumulation
        d2 += ((x[:, k][:, None] - z[:, k][None, :]) / ell[k]) ** 2
    r = np.sqrt(3.0 * np.maximum(d2, 0.0))
    return amplitude ** 2 * (1.0 + r) * np.exp(-r)


# ======================================================================================== special functions
_GL = {n: leggauss(n) for n in (6, 12, 20)}


def _bvnu(h, k, r):
    """Genz BVNU: P(X > h, Y > k) for a standard bivariate normal with correlation r (vectorised)."""
    h, k, r = np.broadcast_arrays(np.asarray(h, float), np.asarray(k, float), np.asarray(r, float))
    h, k, r = h.ravel().copy(), k.ravel().copy(), r.ravel().copy()
    out = np.empty_like(h)
    tp = 2.0 * np.pi
    # infinite arguments
    inf_mask = np.isinf(h) | np.isinf(k)
    if inf_mask.any():
        hh, kk = h[inf_mask], k[inf_mask]
        v = np.where((hh == np.inf) | (kk == np.inf), 0.0,
                     np.where(hh == -np.inf, np.where(kk == -np.inf, 1.0, ndtr(-kk)), ndtr(-hh)))
        out[inf_mask] = v
    fin = ~inf_mask
    zero = fin & (r == 0)
    out[zero] = ndtr(-h[zero]) * ndtr(-k[zero])
    todo = fin & (r != 0)
    small = todo & (np.abs(r) < 0.925)
    for n, sel in ((6, small & (np.abs(r) < 0.3)), (12, small & (np.abs(r) >= 0.3) & (np.abs(r) < 0.75)), (20, small & (np.abs(r) >= 0.75))):
        if not sel.any():
            continue
        t, w = _GL[n]
        hh, kk, rr = h[sel], k[sel], r[sel]
        hk, hs, asr = hh * kk, (hh * hh + kk * kk) / 2, np.arcsin(rr) / 2
        sn = np.sin(asr[:, None] * (1.0 + t[None, :]))          # theta = asr (1 + t) covers (0, asin r)
        val = np.exp((sn * hk[:, None] - hs[:, None]) / (1.0 - sn ** 2)) @ w
        out[sel] = val * asr / tp + ndtr(-hh) * ndtr(-kk)
    big = todo & (np.abs(r) >= 0.925)
    if big.any():
        t, w = _GL[20]
        idx = np.flatnonzero(big)
        for j in idx:
            hh, kk, rr = h[j], k[j], r[j]
            if rr < 0:
                kk = -kk
            hk = hh * kk
            bvn = 0.0
            if abs(rr) < 1:
                as_ = (1 - rr) * (1 + rr); a = np.sqrt(as_); bs = (hh - kk) ** 2
                asr = -(bs / as_ + hk) / 2; c = (4 - hk) / 8; d = (12 - hk) / 80
                if asr > -100:
                    bvn = a * np.exp(asr) * (1 - c * (bs - as_) * (1 - d * bs) / 3 + c * d * as_ * as_)
                if hk > -100:
                    b = np.sqrt(bs); sp = np.sqrt(tp) * ndtr(-b / a)
                    bvn = bvn - np.exp(-hk / 2) * sp * b * (1 - c * bs * (1 - d * bs) / 3)
                a = a / 2
                xs = (a * (1.0 + t)) ** 2                          # Legendre nodes mapped to (0, a)^2
                asr_v = -(bs / xs + hk) / 2
                ok = asr_v > -100
                xs, ww, asr_v = xs[ok], w[ok], asr_v[ok]
                sp = 1 + c * xs * (1 + 5 * d * xs)
                rs = np.sqrt(1 - xs)
                ep = np.exp(-(hk / 2) * xs / (1 + rs) ** 2) / rs
                bvn = (a * np.sum(np.exp(asr_v) * (sp - ep) * ww) - bvn) / tp
            if rr > 0:
                bvn = bvn + ndtr(-max(hh, kk))
            elif hh >= kk:
                bvn = -bvn
            else:
                L = ndtr(kk) - ndtr(hh) if hh < 0 else ndtr(-hh) - ndtr(-kk)
                bvn = L - bvn
            out[j] = bvn
    return np.clip(out, 0.0, 1.0)


def phi2(a, b, rho, order=None):
    """Bivariate normal CDF P(X <= a, Y <= b; rho) via Genz BVNU.  `order` is accepted for API parity and ignored."""
    a, b, rho = np.broadcast_arrays(np.asarray(a, float), np.asarray(b, float), np.asarray(rho, float))
    if np.max(np.abs(rho), initial=0.0) > 1 + 1e-8:
        raise ValueError("Invalid correlation")
    rr = np.clip(rho, -1.0, 1.0)
    shape = a.shape
    flat_a, flat_b, flat_r = a.ravel(), b.ravel(), rr.ravel()
    val = np.empty(flat_a.shape)
    one, mone = flat_r == 1.0, flat_r == -1.0
    mid = ~(one | mone)
    val[one] = ndtr(np.minimum(flat_a[one], flat_b[one]))
    val[mone] = np.maximum(0.0, ndtr(flat_a[mone]) + ndtr(flat_b[mone]) - 1.0)
    if mid.any():
        val[mid] = _bvnu(-flat_a[mid], -flat_b[mid], flat_r[mid])
    lo = np.maximum(0.0, ndtr(flat_a) + ndtr(flat_b) - 1.0); hi = np.minimum(ndtr(flat_a), ndtr(flat_b))
    if np.any(val < lo - 5e-12) or np.any(val > hi + 5e-12):
        raise FloatingPointError("Bivariate CDF outside the Frechet bounds")
    return np.minimum(np.maximum(val, lo), hi).reshape(shape)


# Inverse Mills ratio lambda(t) = phi(t)/Phi(t) for t -> -inf:  1/R(a), R(a) = (1/a)(1 - a^-2 + 3 a^-4 - 15 a^-6 ...).
_MILLS = np.array([1.0, -1.0, 3.0, -15.0, 105.0, -945.0, 10395.0])             # (-1)^k (2k-1)!!


def _series_inverse(c, n):
    out = np.zeros(n); out[0] = 1.0 / c[0]
    for i in range(1, n):
        out[i] = -sum(c[j] * out[i - j] for j in range(1, i + 1)) / c[0]
    return out


_INV = _series_inverse(_MILLS, 6)                                              # 1, 1, -2, 10, -74, 706


def probit_terms(t):
    """log Phi(t), inverse Mills ratio lambda(t) and the negative log-likelihood curvature lambda (lambda + t)."""
    t = np.asarray(t, dtype=float)
    lp = log_ndtr(t)
    lam = np.empty_like(t); curv = np.empty_like(t)
    tail = t < -30
    mid = ~tail
    with np.errstate(over="ignore"):
        lam[mid] = np.sqrt(2.0 / np.pi) / erfcx(-t[mid] / np.sqrt(2.0))
    curv[mid] = lam[mid] * (lam[mid] + t[mid])
    if tail.any():
        a = -t[tail]; y = 1.0 / a ** 2
        s = sum(_INV[i] * y ** i for i in range(len(_INV)))                    # a * lambda = s(y)
        lam[tail] = a * s
        rest = sum(_INV[i] * y ** i for i in range(1, len(_INV)))              # lambda + t = a * (s - 1)
        curv[tail] = (a * s) * (a * rest)
    if np.min(curv, initial=0) < -1e-8 or np.max(curv, initial=0) > 1 + 1e-8 or not np.isfinite(lam).all():
        raise FloatingPointError("Invalid probit curvature")
    return lp, lam, np.clip(curv, 0.0, 1.0)


# ======================================================================================== model
class JointDepthLabelGP:
    """h = f - theta + delta;  z | f Gaussian;  Y | h Bernoulli(Phi(h / tau))."""

    def __init__(self, x_ref, config=None):
        self.x_ref = _x(x_ref).copy()
        self.config = config or Config()
        c = self.config
        if c.probit_scale <= 0 or c.response_noise_sd <= 0 or c.threshold_sd < 0:
            raise ValueError("Require tau > 0, response noise > 0 and threshold sd >= 0")
        if c.f_amplitude < 0 or c.discrepancy_amplitude < 0 or c.jitter <= 0:
            raise ValueError("Invalid amplitude or jitter")
        self._kd_ref_ref = float(self._kd_raw(self.x_ref, self.x_ref).mean())
        self.is_fitted = False

    # ---- kernels
    def _kf(self, a, b):
        return matern32(a, b, self.config.f_amplitude, self.config.f_lengthscale)

    def _kd_raw(self, a, b):
        return matern32(a, b, self.config.discrepancy_amplitude, self.config.discrepancy_lengthscale)

    def _kd_ref_mean(self, a):
        return self._kd_raw(a, self.x_ref).mean(axis=1)

    def discrepancy_kernel(self, a, b):
        """Centering is defined by x_ref only (never by prediction batches or the paid subset)."""
        return self._kd_raw(a, b) - self._kd_ref_mean(a)[:, None] - self._kd_ref_mean(b)[None, :] + self._kd_ref_ref

    def _kd_diag(self, a):
        return self.config.discrepancy_amplitude ** 2 - 2.0 * self._kd_ref_mean(a) + self._kd_ref_ref

    # ---- response posterior (exact Gaussian conditioning on paid z)
    def _f_cond(self, a, b=None):
        a = _x(a); b = a if b is None else _x(b)
        m = np.full(len(a), self.config.f_mean)
        cov = self._kf(a, b)
        if len(self.x_response):
            ka = self._kf(a, self.x_response)
            m = m + ka @ self.response_alpha
            cov = cov - ka @ cho_solve(self.response_chol, self._kf(self.x_response, b))
        return m, cov

    def _f_cond_diag(self, a):
        a = _x(a)
        m = np.full(len(a), self.config.f_mean); v = np.full(len(a), self.config.f_amplitude ** 2)
        if len(self.x_response):
            ka = self._kf(a, self.x_response)
            m = m + ka @ self.response_alpha
            v = v - np.einsum("ij,ji->i", ka, cho_solve(self.response_chol, ka.T))
        return m, v

    # ---- fit
    def fit(self, x_paid, y_paid, z_paid, *, use_labels=True, use_response=True):
        """Paid observations only.  NaN z = missing response (label kept).  Refits from the prior every call."""
        self.x_paid = _x(x_paid).copy()
        y = np.asarray(y_paid, float).reshape(-1); z = np.asarray(z_paid, float).reshape(-1)
        if len(y) != len(z) or len(y) != len(self.x_paid):
            raise ValueError("Paid arrays must have the same length")
        if not np.isin(y, [0, 1]).all():
            raise ValueError("Every paid simulation must retain a canonical 0/1 label")
        if np.isinf(z).any():
            raise ValueError("Use NaN for a missing response, not infinity")
        c = self.config
        good = np.isfinite(z) & bool(use_response)
        self.x_response, self.z_response = self.x_paid[good], z[good].copy()
        if len(self.x_response):
            k = self._kf(self.x_response, self.x_response)
            k.flat[::len(k) + 1] += c.response_noise_sd ** 2 + c.jitter
            self.response_chol = cho_factor(k, lower=True)
            self.response_alpha = cho_solve(self.response_chol, self.z_response - c.f_mean)
        self.x_label = self.x_paid if use_labels else self.x_paid[:0]
        self.y_label = y if use_labels else y[:0]
        n = len(self.x_label)
        self.alpha, self.R = np.zeros(0), np.zeros((0, 0))
        self.diagnostics = {"version": VERSION, "n_paid": len(y), "n_response": int(len(self.x_response)), "n_labels": n,
                            "n_negative": int((self.y_label == 0).sum()), "n_missing_response": int((~np.isfinite(z)).sum()),
                            "solver_status": "prior only", "optimizer": "prior only", "gradient_inf": 0.0, "gradient_accepted": True,
                            "newton_iterations": 0}
        if n:
            fm, fc = self._f_cond(self.x_label)
            m = fm - c.threshold_mean
            K = fc + self.discrepancy_kernel(self.x_label, self.x_label) + c.threshold_sd ** 2
            K = (K + K.T) / 2
            K.flat[::n + 1] += c.jitter
            s = 2 * self.y_label - 1
            res = self._newton(K, m, s)
            self.alpha, self.R = res["a"], res["R"]
            self._h_mode, self._K_labels = res["h"], K
            self.diagnostics.update({k: v for k, v in res.items() if k not in ("a", "R", "h")})
            self.diagnostics["optimizer"] = res["solver_status"]
            self.diagnostics["optimizer_success"] = res["solver_status"] == "converged"
            self.diagnostics["iterations"] = res["newton_iterations"]
            self.diagnostics["mode_objective"] = res["objective"]
            if not res["gradient_accepted"]:
                raise RuntimeError(f"Laplace mode not accepted: status={res['solver_status']}; gradient={res['gradient_inf']:.3e}")
        self.is_fitted = True
        return self

    def _newton(self, K, m, s):
        tau = self.config.probit_scale
        n = len(m)
        Lk = np.linalg.cholesky(K)

        def objective(a):
            h = K @ a + m
            lp, lam, curv = probit_terms(s * h / tau)
            return 0.5 * a @ (h - m) - lp.sum(), h, lam, curv

        a = np.zeros(n)
        psi, h, lam, curv = objective(a)
        status, it = "max_iter", 0
        for it in range(1, NEWTON_MAX_ITER + 1):
            g = s * lam / tau; W = curv / tau ** 2
            grad_w = Lk.T @ (a - g)
            if np.max(np.abs(grad_w)) <= NEWTON_GRAD_TOL:
                status = "converged"; it -= 1; break
            sW = np.sqrt(W)
            B = np.eye(n) + sW[:, None] * K * sW[None, :]
            LB = cho_factor(B, lower=True)
            b = W * (h - m) + g
            a_new = b - sW * cho_solve(LB, sW * (K @ b))
            step = 1.0
            while True:
                cand = a + step * (a_new - a)
                psi_c, h_c, lam_c, curv_c = objective(cand)
                if psi_c <= psi + 1e-14 * max(1.0, abs(psi)) or step < 1e-10:
                    break
                step *= 0.5
            if step < 1e-10 and psi_c > psi:
                status = "line_search_failed"; break
            done = abs(psi - psi_c) <= 1e-15 * max(1.0, abs(psi))
            a, psi, h, lam, curv = cand, psi_c, h_c, lam_c, curv_c
            if done:
                status = "stalled_at_objective_tolerance"; break
        g = s * lam / tau; W = curv / tau ** 2
        grad_w = Lk.T @ (a - g)
        grad_inf = float(np.max(np.abs(grad_w)))
        if grad_inf <= NEWTON_GRAD_TOL:
            status = "converged"
        sW = np.sqrt(W)
        B = np.eye(n) + sW[:, None] * K * sW[None, :]
        LB = cho_factor(B, lower=True)
        R = sW[:, None] * cho_solve(LB, np.diag(sW))
        R = (R + R.T) / 2
        hess_min = float(np.linalg.eigvalsh(np.eye(n) + (Lk.T * W) @ Lk).min())
        return {"a": a, "R": R, "h": h, "solver_status": status, "newton_iterations": int(it), "objective": float(psi),
                "gradient_inf": grad_inf, "gradient_accepted": bool(np.isfinite(psi) and grad_inf <= GRADIENT_ACCEPT),
                "min_whitened_hessian_eigenvalue": hess_min, "condition_number_K": float(np.linalg.cond(K))}

    # ---- posterior
    def _cross_to_labels(self, x):
        """C^z_{f(x), h_P}, C^z_{delta(x), h_P} (and theta's -s^2 row) before label conditioning."""
        _, cfL = self._f_cond(x, self.x_label)
        kdL = self.discrepancy_kernel(x, self.x_label)
        return cfL, kdL

    def marginals(self, x):
        """Per-point posterior summaries (batch invariant: each row depends on x_ref, paid data and that point only)."""
        if not self.is_fitted:
            raise RuntimeError("Call fit first")
        x = _x(x); c = self.config; s2 = c.threshold_sd ** 2
        mf, vf = self._f_cond_diag(x)
        vd = self._kd_diag(x)
        out = {"f_mean": mf.copy(), "f_var": vf.copy(), "delta_mean": np.zeros(len(x)), "delta_var": vd.copy(),
               "theta_mean": float(c.threshold_mean), "theta_var": float(s2), "f_theta_cov": np.zeros(len(x)),
               "f_delta_cov": np.zeros(len(x)), "delta_theta_cov": np.zeros(len(x))}
        if len(self.x_label):
            cfL, kdL = self._cross_to_labels(x)
            one = np.ones(len(self.x_label))
            Rf, Rd, R1 = cfL @ self.R, kdL @ self.R, self.R @ one
            out["f_mean"] = mf + cfL @ self.alpha
            out["delta_mean"] = kdL @ self.alpha
            out["theta_mean"] = float(c.threshold_mean - s2 * one @ self.alpha)
            out["f_var"] = vf - np.einsum("ij,ij->i", Rf, cfL)
            out["delta_var"] = vd - np.einsum("ij,ij->i", Rd, kdL)
            out["theta_var"] = float(s2 - s2 * s2 * one @ R1)
            out["f_theta_cov"] = s2 * (cfL @ R1)
            out["delta_theta_cov"] = s2 * (kdL @ R1)
            out["f_delta_cov"] = -np.einsum("ij,ij->i", Rf, kdL)
        out["h_mean"] = out["f_mean"] - out["theta_mean"] + out["delta_mean"]
        out["h_var"] = (out["f_var"] + out["theta_var"] + out["delta_var"] - 2 * out["f_theta_cov"]
                        + 2 * out["f_delta_cov"] - 2 * out["delta_theta_cov"])
        if np.min(out["h_var"], initial=0) < -1e-9 or np.min(out["f_var"], initial=0) < -1e-9 or out["theta_var"] < -1e-12:
            raise FloatingPointError("Negative posterior variance")
        out["h_var"] = np.maximum(out["h_var"], 0.0)
        out["p"] = ndtr(out["h_mean"] / np.sqrt(c.probit_scale ** 2 + out["h_var"]))
        return out

    def predict_proba(self, x):
        return self.marginals(x)["p"]

    def posterior(self, x):
        """Joint Gaussian over the batch (full matrices), keys as in the reference implementation."""
        if not self.is_fitted:
            raise RuntimeError("Call fit first")
        x = _x(x); c = self.config; n = len(x); s2 = c.threshold_sd ** 2
        mf, cf = self._f_cond(x)
        kd = self.discrepancy_kernel(x, x)
        res = {"f_mean": mf.copy(), "f_cov": cf.copy(), "theta_mean": float(c.threshold_mean), "theta_var": float(s2),
               "f_theta_cov": np.zeros(n), "delta_mean": np.zeros(n), "delta_cov": kd.copy(), "f_delta_cov": np.zeros((n, n)),
               "delta_theta_cov": np.zeros(n)}
        ch = cf + kd + s2
        cfh = cf.copy()
        if len(self.x_label):
            cfL, kdL = self._cross_to_labels(x)
            one = np.ones(len(self.x_label))
            chL = cfL + kdL + s2
            res["f_mean"] = mf + cfL @ self.alpha
            res["delta_mean"] = kdL @ self.alpha
            res["theta_mean"] = float(c.threshold_mean - s2 * one @ self.alpha)
            res["f_cov"] = cf - cfL @ self.R @ cfL.T
            ch = ch - chL @ self.R @ chL.T
            cfh = cfh - cfL @ self.R @ chL.T
            res["delta_cov"] = kd - kdL @ self.R @ kdL.T
            res["f_delta_cov"] = -cfL @ self.R @ kdL.T
            R1 = self.R @ one
            res["theta_var"] = float(s2 - s2 * s2 * one @ R1)
            res["f_theta_cov"] = s2 * (cfL @ R1)
            res["delta_theta_cov"] = s2 * (kdL @ R1)
        res["f_cov"], res["delta_cov"] = (res["f_cov"] + res["f_cov"].T) / 2, (res["delta_cov"] + res["delta_cov"].T) / 2
        res["h_cov"] = (ch + ch.T) / 2
        res["h_mean"] = res["f_mean"] - res["theta_mean"] + res["delta_mean"]
        res["f_h_cov"] = cfh
        if np.min(np.diag(res["h_cov"])) < -1e-7 or np.min(np.diag(res["f_cov"])) < -1e-7 or res["theta_var"] < -1e-7:
            raise FloatingPointError("Negative posterior variance")
        res["theta_var"] = max(res["theta_var"], 0.0)
        return res

    def predict_proba_theta_conditioned(self, x):
        """Astra's diagnostic: condition the fitted joint Gaussian on theta = its posterior mean.
        h mean unchanged; Var(h) - Cov(h, theta)^2 / Var(theta) (skip when Var(theta) is negligible)."""
        q = self.marginals(x)
        cht = q["f_theta_cov"] - q["theta_var"] + q["delta_theta_cov"]       # Cov(h, theta) = Cov(f,theta) - Var(theta) + Cov(delta,theta)
        v = q["h_var"] - (cht ** 2 / q["theta_var"] if q["theta_var"] > 1e-14 else 0.0)
        return ndtr(q["h_mean"] / np.sqrt(self.config.probit_scale ** 2 + np.maximum(v, 0.0))), cht

    # ---- acquisition
    def acquisition(self, x_query, x_integrate=None, *, observe_response=True, observe_label=True, gh_order=15, cdf_order=48):
        """Expected reduction of the integrated Var[pi(x) | D], pi = Phi(h / tau), from observing (Z_j, Y_j) jointly.
        Fixed uniform weights on x_integrate (default x_ref); Gauss-Hermite over Z_j; exact bivariate-probit label term."""
        xq = _x(x_query); xi = self.x_ref if x_integrate is None else _x(x_integrate)
        nq, ni = len(xq), len(xi)
        q = self.posterior(np.vstack([xi, xq]))
        hm, C, F, FH = q["h_mean"], q["h_cov"], q["f_cov"], q["f_h_cov"]
        tau2 = self.config.probit_scale ** 2
        p0 = ndtr(hm[:ni] / np.sqrt(tau2 + np.maximum(np.diag(C)[:ni], 0)))
        if observe_response:
            nodes, weights = hermgauss(gh_order); weights = weights / np.sqrt(np.pi)
        else:
            nodes, weights = np.array([0.0]), np.array([1.0])
        score, resp, lab, bound = np.zeros(nq), np.zeros(nq), np.zeros(nq), np.zeros(nq)
        for j in range(nq):
            jj = ni + j
            idx = np.r_[np.arange(ni), jj]
            mm, cv = hm[idx], C[np.ix_(idx, idx)]
            if observe_response:
                vz = max(float(F[jj, jj]), 0.0) + self.config.response_noise_sd ** 2
                cross = FH[jj, idx]
                cv = cv - np.outer(cross, cross) / vz
                shift = cross / np.sqrt(vz)
            else:
                shift = np.zeros(ni + 1)
            vv = np.maximum(np.diag(cv), 0.0)
            den = np.sqrt(tau2 + vv)
            rho = np.clip(cv[:-1, -1] / (den[:-1] * den[-1]), -1.0, 1.0)
            for node, w in zip(nodes, weights):
                aa = (mm + np.sqrt(2.0) * node * shift) / den
                pp, pq = ndtr(aa[:-1]), float(ndtr(aa[-1]))
                resp[j] += w * float(np.mean((pp - p0) ** 2))
                if observe_label and 1e-12 < pq < 1 - 1e-12:
                    J = phi2(aa[:-1], np.full(ni, aa[-1]), rho)
                    lab[j] += w * float(np.mean((J - pp * pq) ** 2 / (pq * (1 - pq))))
                elif observe_label:
                    bound[j] += w * 1e-12          # (J - pq p)^2 / (q(1-q)) <= q/(1-q) per point when q -> 0 (and symmetric)
            score[j] = resp[j] + lab[j]
        return {"score": score, "response_component": resp, "label_component": lab, "omitted_label_term_upper_bound": bound,
                "gh_order": gh_order, "cdf_order": cdf_order}

    def integrated_probability_variance(self, x, cdf_order=None):
        q = self.marginals(x)
        a = q["h_mean"] / np.sqrt(self.config.probit_scale ** 2 + q["h_var"])
        rho = q["h_var"] / (self.config.probit_scale ** 2 + q["h_var"])
        return phi2(a, a, rho) - ndtr(a) ** 2


def fit_paid_prefix(x_pool, y_oracle, z_oracle, paid_indices, config=None):
    """Masking adapter for leakage tests: only the paid rows' outputs are materialised before fitting."""
    x_pool = _x(x_pool)
    idx = np.asarray(paid_indices, dtype=int)
    if len(np.unique(idx)) != len(idx) or np.any(idx < 0) or np.any(idx >= len(x_pool)):
        raise ValueError("Invalid paid prefix")
    yp = np.asarray(y_oracle)[idx].copy(); zp = np.asarray(z_oracle)[idx].copy()
    return JointDepthLabelGP(x_pool, config).fit(x_pool[idx], yp, zp)
