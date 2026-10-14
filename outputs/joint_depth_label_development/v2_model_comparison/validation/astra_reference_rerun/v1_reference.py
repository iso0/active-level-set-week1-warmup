"""Standalone joint depth/label GP reference; NumPy and SciPy only.

Fixed hyperparameters. No repository imports, no simulator access, no network.
Depth transform is external: z = log(depth_um / 111). Canonical labels are 0/1.
X_ref is the fixed, label-blind candidate pool used to center discrepancy.
All outputs in fit() belong to paid simulations; test monitors are never inputs.
"""
from dataclasses import dataclass
import numpy as np
from numpy.polynomial.hermite import hermgauss
from numpy.polynomial.legendre import leggauss
from scipy.linalg import cho_factor, cho_solve, solve_triangular
from scipy.integrate import quad
from scipy.optimize import minimize
from scipy.special import log_ndtr, ndtr


@dataclass(frozen=True)
class Config:
    f_amplitude: float = 0.6
    f_lengthscale: float = 0.5
    discrepancy_amplitude: float = 0.35
    discrepancy_lengthscale: float = 0.5
    threshold_mean: float = 0.0
    threshold_sd: float = 0.35
    response_noise_sd: float = 0.03
    probit_scale: float = 0.15
    f_mean: float = 0.0
    jitter: float = 1e-10


def _x(x):
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    if x.ndim != 2 or not np.isfinite(x).all():
        raise ValueError("X must be a finite two-dimensional input matrix")
    return x


def matern32(x, z, amplitude, lengthscale):
    x, z = _x(x), _x(z)
    d = np.sqrt(np.maximum(np.sum(((x[:, None, :] - z[None, :, :]) / np.asarray(lengthscale)) ** 2, axis=2), 0.0))
    r = np.sqrt(3.0) * d
    return amplitude ** 2 * (1.0 + r) * np.exp(-r)


def phi2(a, b, rho, order=48):
    """Deterministic bivariate-normal CDF via Plackett's angular integral.

    This integrates correlation rather than randomizing an MVN CDF routine.
    Explicit Frechet-bound checks expose unresolved quadrature errors.
    """
    a, b, rho = np.broadcast_arrays(np.asarray(a, float), np.asarray(b, float), np.asarray(rho, float))
    if np.max(np.abs(rho)) > 1 + 1e-8:
        raise ValueError("Invalid correlation")
    rho = np.clip(rho, -1, 1)
    nodes, weights = leggauss(order)
    angle = np.arcsin(rho)
    t = angle[..., None] * (nodes + 1) / 2
    rt = np.sin(t)
    ct2 = np.cos(t) ** 2
    expo = -(a[..., None] ** 2 - 2 * rt * a[..., None] * b[..., None] + b[..., None] ** 2) / (2 * ct2)
    value = np.asarray(ndtr(a) * ndtr(b) + angle / (4 * np.pi) * np.sum(weights * np.exp(expo), axis=-1)).copy()
    lo, hi = np.maximum(0, ndtr(a) + ndtr(b) - 1), np.minimum(ndtr(a), ndtr(b))
    # Fixed nodes can miss a narrow endpoint layer despite satisfying bounds.
    # Handle singular limits exactly, and near-singular correlations adaptively.
    value = np.where(rho == 1, hi, np.where(rho == -1, lo, value))
    flat = value.reshape(-1)
    af, bf, rf = a.reshape(-1), b.reshape(-1), rho.reshape(-1)
    for j in np.flatnonzero((np.abs(rf)>.995)&(np.abs(rf)<1)):
        aa, bb, rr = af[j], bf[j], rf[j]
        def integrand(t):
            return np.exp(-(aa*aa-2*np.sin(t)*aa*bb+bb*bb)/(2*np.cos(t)**2))
        end = np.arcsin(rr)
        points = [end*(1-10.0**(-k)) for k in range(1,9)]
        integ, error = quad(integrand,0,end,points=points,epsabs=2e-12,epsrel=2e-10,limit=150)
        if error/(2*np.pi)>1e-8:
            raise FloatingPointError("Near-singular bivariate CDF integral did not converge")
        flat[j] = ndtr(aa)*ndtr(bb)+integ/(2*np.pi)
    if np.any(value < lo - 5e-7) or np.any(value > hi + 5e-7):
        raise FloatingPointError("Bivariate CDF quadrature outside probability bounds; increase order")
    return np.minimum(np.maximum(value, lo), hi)


def probit_terms(t):
    """Stable log Phi(t), inverse Mills ratio, and negative log curvature.

    The negative-tail expansion avoids catastrophic cancellation in r+t.
    Curvature tends to one from below, not to infinity.
    """
    t = np.asarray(t, dtype=float)
    lp = log_ndtr(t)
    ratio = np.empty_like(t)
    curvature = np.empty_like(t)
    tail = t < -30
    a = -t[tail]
    u = 1/a
    ratio[tail] = a+u-2*u**3+10*u**5-74*u**7+706*u**9
    curvature[tail] = 1-u**2+6*u**4-50*u**6+518*u**8-6354*u**10
    tt = t[~tail]
    ratio[~tail] = np.exp(-.5*tt*tt-.5*np.log(2*np.pi)-lp[~tail])
    curvature[~tail] = ratio[~tail]*(ratio[~tail]+tt)
    if np.min(curvature, initial=0) < -1e-8 or np.max(curvature, initial=0) > 1+1e-8:
        raise FloatingPointError("Invalid probit curvature")
    return lp, ratio, np.clip(curvature, 0, 1)


class JointDepthLabelGP:
    """h=f-theta+delta, z|f Gaussian, y|h Bernoulli(Phi(h/tau))."""
    def __init__(self, x_ref, config=None):
        self.x_ref = _x(x_ref).copy()
        self.config = config or Config()
        c = self.config
        if c.probit_scale <= 0 or c.response_noise_sd <= 0 or c.threshold_sd < 0:
            raise ValueError("Require tau>0, response noise>0 and threshold sd>=0")
        if c.f_amplitude < 0 or c.discrepancy_amplitude < 0 or c.jitter <= 0:
            raise ValueError("Invalid amplitude or jitter")
        self._delta_ref_mean = float(self._kd_raw(self.x_ref, self.x_ref).mean())
        self.is_fitted = False

    def _kf(self, x, z):
        c = self.config
        return matern32(x, z, c.f_amplitude, c.f_lengthscale)

    def _kd_raw(self, x, z):
        c = self.config
        return matern32(x, z, c.discrepancy_amplitude, c.discrepancy_lengthscale)

    def discrepancy_kernel(self, x, z):
        """GP centering is defined by x_ref, never by prediction/test inputs."""
        return (self._kd_raw(x, z)
                - self._kd_raw(x, self.x_ref).mean(axis=1)[:, None]
                - self._kd_raw(self.x_ref, z).mean(axis=0)[None, :]
                + self._delta_ref_mean)

    def _f_response_posterior(self, x, z=None):
        x = _x(x)
        z = x if z is None else _x(z)
        m = np.full(len(x), self.config.f_mean)
        cov = self._kf(x, z)
        if len(self.x_response):
            kxo = self._kf(x, self.x_response)
            m += kxo @ self.response_alpha
            cov -= kxo @ cho_solve(self.response_chol, self._kf(self.x_response, z))
        return m, cov

    def fit(self, x_paid, y_paid, z_paid, *, use_labels=True, use_response=True):
        """Only paid observations. NaN z means missing depth; label is retained.

        use_labels/use_response are explicit diagnostic ablations. Fitting on
        zero rows is supported as a prior-predictive correctness check.
        """
        self.x_paid = _x(x_paid).copy()
        y = np.asarray(y_paid, float).reshape(-1)
        z = np.asarray(z_paid, float).reshape(-1)
        if len(y) != len(z) or len(y) != len(self.x_paid):
            raise ValueError("Paid arrays must have the same length")
        if not np.isin(y, [0, 1]).all():
            raise ValueError("Every paid simulation must retain a canonical 0/1 label")
        if np.isinf(z).any():
            raise ValueError("Use NaN for missing z, not infinity")
        good = np.isfinite(z) & bool(use_response)
        self.x_response = self.x_paid[good]
        self.z_response = z[good].copy()
        c = self.config
        if len(self.x_response):
            k = self._kf(self.x_response, self.x_response)
            k.flat[::len(k)+1] += c.response_noise_sd ** 2 + c.jitter
            self.response_chol = cho_factor(k, lower=True)
            self.response_alpha = cho_solve(self.response_chol, self.z_response - c.f_mean)
        self.x_label = self.x_paid if use_labels else self.x_paid[:0]
        self.y_label = y if use_labels else y[:0]
        n = len(self.x_label)
        self.alpha = np.empty(0)
        self.R = np.empty((0, 0))
        self.diagnostics = {"n_paid": len(y), "n_response": len(self.x_response), "n_labels": n,
                            "n_negative": int((self.y_label == 0).sum()), "optimizer": "prior only", "gradient_inf": 0.0}
        if n:
            fm, fc = self._f_response_posterior(self.x_label)
            m = fm - c.threshold_mean
            k = fc + self.discrepancy_kernel(self.x_label, self.x_label) + c.threshold_sd ** 2
            k = (k+k.T)/2
            k.flat[::n+1] += c.jitter
            L = np.linalg.cholesky(k)
            signs = 2*self.y_label - 1
            def objective(v):
                h = m + L @ v
                t = signs*h/c.probit_scale
                lp, ratio, curvature = probit_terms(t)
                grad_log = signs*ratio/c.probit_scale
                W = curvature/c.probit_scale**2
                val = .5*np.dot(v,v)-np.sum(lp)
                grad = v-L.T@grad_log
                hess = np.eye(n)+(L.T*W)@L
                return val, grad, hess
            res = minimize(lambda v: objective(v)[0], np.zeros(n),
                           jac=lambda v: objective(v)[1], hess=lambda v: objective(v)[2],
                           method="trust-exact", options={"gtol": 1e-9, "maxiter": 200})
            _, grad, hess = objective(res.x)
            grad_norm = float(np.max(np.abs(grad)))
            if grad_norm > 2e-6 or not np.isfinite(res.fun):
                raise RuntimeError(f"Laplace mode failed: {res.message}; gradient={grad_norm}")
            hhat = m + L @ res.x
            self.alpha = solve_triangular(L.T, res.x, lower=False)
            t = signs*hhat/c.probit_scale
            _, _, curvature = probit_terms(t)
            W = curvature/c.probit_scale**2
            sw = np.sqrt(W)
            B = np.eye(n)+(sw[:, None]*k)*sw[None, :]
            self.R = sw[:, None]*cho_solve(cho_factor(B, lower=True), np.diag(sw))
            self.R = (self.R+self.R.T)/2
            self.diagnostics.update({"optimizer": str(res.message), "optimizer_success": bool(res.success),
                                     "gradient_inf": grad_norm, "iterations": int(res.nit),
                                     "mode_objective": float(res.fun), "min_hessian_eigenvalue": float(np.linalg.eigvalsh(hess).min())})
        self.is_fitted = True
        return self

    def posterior(self, x):
        """Joint Gaussian marginals AFTER both observation types.

        Includes f-theta covariance rather than combining independent fits.
        h covariance already contains all f/theta/discrepancy covariance terms.
        """
        if not self.is_fitted:
            raise RuntimeError("Call fit first")
        x = _x(x)
        c, n = self.config, len(x)
        mf, cf = self._f_response_posterior(x)
        mh = mf-c.threshold_mean
        ch = cf+self.discrepancy_kernel(x,x)+c.threshold_sd**2
        cfh = cf.copy()
        mt, vt = c.threshold_mean, c.threshold_sd**2
        cov_ft = np.zeros(n)
        delta_mean = np.zeros(n)
        delta_cov = self.discrepancy_kernel(x,x)
        cov_fd = np.zeros((n,n))
        cov_dt = np.zeros(n)
        if len(self.x_label):
            _, cfL = self._f_response_posterior(x, self.x_label)
            kdL = self.discrepancy_kernel(x,self.x_label)
            chL = cfL+kdL+c.threshold_sd**2
            ctL = np.full(len(self.x_label), -c.threshold_sd**2)
            mf += cfL@self.alpha
            mh += chL@self.alpha
            delta_mean += kdL@self.alpha
            mt += ctL@self.alpha
            cf -= cfL@self.R@cfL.T
            ch -= chL@self.R@chL.T
            cfh -= cfL@self.R@chL.T
            vt -= ctL@self.R@ctL
            cov_ft -= cfL@self.R@ctL
            delta_cov -= kdL@self.R@kdL.T
            cov_fd -= cfL@self.R@kdL.T
            cov_dt -= kdL@self.R@ctL
        cf, ch, delta_cov = (cf+cf.T)/2, (ch+ch.T)/2, (delta_cov+delta_cov.T)/2
        if np.min(np.diag(ch)) < -1e-7 or np.min(np.diag(cf)) < -1e-7 or vt < -1e-7:
            raise FloatingPointError("Negative posterior variance")
        return {"f_mean": mf, "f_cov": cf, "h_mean": mh, "h_cov": ch, "f_h_cov": cfh,
                "theta_mean": float(mt), "theta_var": float(max(vt,0)), "f_theta_cov": cov_ft,
                "delta_mean": delta_mean, "delta_cov": delta_cov, "f_delta_cov": cov_fd,
                "delta_theta_cov": cov_dt}

    def predict_proba(self, x):
        q = self.posterior(x)
        return ndtr(q["h_mean"] / np.sqrt(self.config.probit_scale**2+np.maximum(np.diag(q["h_cov"]),0)))

    def acquisition(self, x_query, x_integrate=None, *, observe_response=True,
                    observe_label=True, gh_order=15, cdf_order=48):
        """Expected reduction in integrated Var[pi(x)|D], pi=Phi(h/tau).

        Integrate the joint future (Z,Y); no fantasy refits or hidden outputs.
        Uniform, fixed feature-only integration weights. Caller excludes paid
        candidates. All scores are conditional on fixed hyperparameters and
        the current joint Laplace approximation.
        """
        xq = _x(x_query)
        xi = self.x_ref if x_integrate is None else _x(x_integrate)
        nq, ni = len(xq), len(xi)
        q = self.posterior(np.vstack([xi,xq]))
        h, C, F, FH = q["h_mean"], q["h_cov"], q["f_cov"], q["f_h_cov"]
        tau2 = self.config.probit_scale**2
        p0 = ndtr(h[:ni]/np.sqrt(tau2+np.maximum(np.diag(C)[:ni],0)))
        nodes, weights = hermgauss(gh_order) if observe_response else (np.array([0.0]), np.array([np.sqrt(np.pi)]))
        weights = weights/np.sqrt(np.pi)
        scores, response_scores, label_scores = np.zeros(nq), np.zeros(nq), np.zeros(nq)
        tail_bounds = np.zeros(nq)
        for j in range(nq):
            jj = ni+j
            indices = np.r_[np.arange(ni), jj]
            mm = h[indices]
            cv = C[np.ix_(indices,indices)]
            if observe_response:
                vz = max(float(F[jj,jj]),0)+self.config.response_noise_sd**2
                cross = FH[jj,indices]
                cv = cv-np.outer(cross,cross)/vz
                shift = cross/np.sqrt(vz)
            else:
                shift = np.zeros(ni+1)
            vv = np.maximum(np.diag(cv),0)
            denom = np.sqrt(tau2+vv)
            rho = cv[:-1,-1]/(denom[:-1]*denom[-1])
            for node, w in zip(nodes,weights):
                aa = (mm+np.sqrt(2)*node*shift)/denom
                pp, pq = ndtr(aa[:-1]), float(ndtr(aa[-1]))
                response_scores[j] += w*float(np.mean((pp-p0)**2))
                if observe_label and 1e-12 < pq < 1-1e-12:
                    J = phi2(aa[:-1],aa[-1],rho,order=cdf_order)
                    label_scores[j] += w*float(np.mean((J-pp*pq)**2/(pq*(1-pq))))
                elif observe_label:
                    tail_bounds[j] += w*1e-12
            scores[j] = response_scores[j]+label_scores[j]
        return {"score": scores, "response_component": response_scores, "label_component": label_scores,
                "omitted_label_term_upper_bound": tail_bounds,
                "gh_order": gh_order, "cdf_order": cdf_order}

    def integrated_probability_variance(self, x, cdf_order=64):
        q = self.posterior(x)
        var = np.maximum(np.diag(q["h_cov"]),0)
        a = q["h_mean"]/np.sqrt(self.config.probit_scale**2+var)
        rho = var/(self.config.probit_scale**2+var)
        return phi2(a,a,rho,cdf_order)-ndtr(a)**2


def fit_paid_prefix(x_pool, y_oracle, z_oracle, paid_indices, config=None):
    """Masking adapter: materialize ONLY paid outputs before handing off.

    The caller owns oracle access. This convenience wrapper is for leakage
    tests; production code should provide a paid-only table directly.
    """
    x_pool = _x(x_pool)
    idx = np.asarray(paid_indices,dtype=int)
    if len(np.unique(idx)) != len(idx) or np.any(idx < 0) or np.any(idx >= len(x_pool)):
        raise ValueError("Invalid paid prefix")
    yp = np.asarray(y_oracle)[idx].copy()
    zp = np.asarray(z_oracle)[idx].copy()
    return JointDepthLabelGP(x_pool,config).fit(x_pool[idx],yp,zp)
