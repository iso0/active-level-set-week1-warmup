"""IR part C models (PROTOCOL_IR.md section 5): bivariate linear model of coregionalisation (LMC) for (log depth, co-output q),
its tied-lengthscale ICM variant and the depth-only two-kernel control SUM2. numpy / scipy only; MAP hyperparameters; analytic
gradients (validated against finite differences, acceptance V3).

Model on standardised outputs (each output: mean / SD of its paid good records, src.rc18_gp convention):
  y_(o,i) = sum_r a[o, r] u_r(z_i) + beta_o hb_i + eps_(o,i),   u_r ~ GP(0, Matern32_ARD(ell_r)) independent, r = 1..R
  beta_o ~ N(0, b^2) independent per output (h trend, integrated), eps_(o,i) ~ N(0, s2_o w_i)
  => K[(o,i),(o',j)] = sum_r a[o,r] a[o',r] k_r(z_i, z_j) + delta_oo' b^2 hb_i hb_j + delta_(o,i),(o',j) s2_o w_i
Heterotopic data: an output entry is present only where that output is finite (missing q entries are simply absent).
Parameters theta = [log ell_1 (d), log ell_2 (d) (absent when tied), a (n_out x R, row major), log s2 (n_out)].
Priors (MAP): log ell ~ N(0, 1); a ~ N(0, 1); log s2 ~ N(log 0.01, 1.5^2).
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize

S3 = np.sqrt(3.0)
B_ELL = (np.log(1e-2), np.log(1e2)); B_A = (-10.0, 10.0); B_SN2 = (np.log(1e-6), np.log(10.0))
PRIOR_ELL = (0.0, 1.0); PRIOR_A = (0.0, 1.0); PRIOR_SN2 = (np.log(0.01), 1.5)


class LMC:
    def __init__(self, n_out=2, R=2, tied=False, b=3.0, use_prior=True):
        self.n_out, self.R, self.tied, self.b, self.use_prior = n_out, R, tied, b, use_prior

    # ------------------------------------------------------------------ parameter layout
    def _split(self, th, d):
        nl = 1 if self.tied else self.R
        le = th[:nl * d].reshape(nl, d); off = nl * d
        A = th[off:off + self.n_out * self.R].reshape(self.n_out, self.R); off += self.n_out * self.R
        ls2 = th[off:off + self.n_out]
        if self.tied:
            le = np.repeat(le, self.R, axis=0)
        return le, A, ls2

    def n_params(self, d):
        return (1 if self.tied else self.R) * d + self.n_out * self.R + self.n_out

    def bounds(self, d):
        return [B_ELL] * ((1 if self.tied else self.R) * d) + [B_A] * (self.n_out * self.R) + [B_SN2] * self.n_out

    # ------------------------------------------------------------------ likelihood
    def _kernel_parts(self, le, Z):
        D2 = (Z[:, None, :] - Z[None, :, :]) ** 2                       # (n, n, d)
        parts = []
        for r in range(self.R):
            S = D2 / np.exp(2 * le[r]); rr = np.sqrt(np.maximum(S.sum(-1), 0.0)); E = np.exp(-S3 * rr)
            parts.append(((1 + S3 * rr) * E, E, S))                       # k_r, exp term, scaled squared distances per dim
        return parts

    def _nlml(self, th, Z, y, o, hb, w):
        n, d = Z.shape; le, A, ls2 = self._split(th, d); parts = self._kernel_parts(le, Z)
        same = (o[:, None] == o[None, :])
        K = np.zeros((n, n)); C = []
        for r in range(self.R):
            Cr = A[o, r][:, None] * A[o, r][None, :]; C.append(Cr); K += Cr * parts[r][0]
        if self.b > 0 and hb is not None:
            K += same * (self.b ** 2) * np.outer(hb, hb)
        s2 = np.exp(ls2); K[np.diag_indices(n)] += s2[o] * w
        try:
            c = cho_factor(K + 1e-10 * np.eye(n), lower=True)
        except np.linalg.LinAlgError:
            return 1e25, np.zeros_like(th)
        al = cho_solve(c, y); Ki = cho_solve(c, np.eye(n))
        nl = 0.5 * y @ al + np.sum(np.log(np.diag(c[0]))) + 0.5 * n * np.log(2 * np.pi)
        Wm = Ki - np.outer(al, al); g = np.zeros_like(th)
        nlr = 1 if self.tied else self.R
        for r in range(self.R):                                           # lengthscales: dk/dlog ell_k = 3 E S_k (Matern 3/2)
            kr, E, S = parts[r]; rr_idx = 0 if self.tied else r
            WC = Wm * C[r] * 3.0 * E
            for k in range(d):
                g[rr_idx * d + k] += 0.5 * np.sum(WC * S[:, :, k])
        off = nlr * d
        for p in range(self.n_out):                                       # dK/da[p,r] = (d_op a[o',r] + d_o'p a[o,r]) k_r
            ip = (o == p).astype(float)
            for r in range(self.R):
                ar = A[o, r]; dC = ip[:, None] * ar[None, :] + ar[:, None] * ip[None, :]
                g[off + p * self.R + r] = 0.5 * np.sum(Wm * dC * parts[r][0])
        off2 = off + self.n_out * self.R
        dW = np.diag(Wm)
        for p in range(self.n_out):
            g[off2 + p] = 0.5 * np.sum(dW * (o == p) * s2[p] * w)
        if self.use_prior:
            le_raw = th[:nlr * d]; dl = (le_raw - PRIOR_ELL[0]) / PRIOR_ELL[1]; nl += 0.5 * dl @ dl; g[:nlr * d] += dl / PRIOR_ELL[1]
            av = th[off:off2]; da = (av - PRIOR_A[0]) / PRIOR_A[1]; nl += 0.5 * da @ da; g[off:off2] += da / PRIOR_A[1]
            sv = th[off2:]; ds = (sv - PRIOR_SN2[0]) / PRIOR_SN2[1]; nl += 0.5 * ds @ ds; g[off2:] += ds / PRIOR_SN2[1]
        return float(nl), g

    # ------------------------------------------------------------------ fit / predict
    def fit(self, Z, ys_list, w_list, hb=None, starts=(), theta=None):
        """Z: (n, d) inputs of all rows; ys_list[o]: (n,) raw values of output o (NaN = absent); w_list[o]: (n,) noise multipliers.
        Standardises each output on its present rows with w <= 100 (fallback: all present rows)."""
        Z = np.asarray(Z, float); n, d = Z.shape; rows, outs, vals, ws = [], [], [], []; self.mu, self.sd = [], []
        for oo, (v, wv) in enumerate(zip(ys_list, w_list)):
            v = np.asarray(v, float); wv = np.asarray(wv, float); pres = np.flatnonzero(np.isfinite(v)); good = pres[wv[pres] <= 100.0]
            ref = good if len(good) >= 2 else pres
            mu = float(v[ref].mean()) if len(ref) else 0.0; sd = float(v[ref].std()) + 1e-12 if len(ref) > 1 else 1.0
            self.mu.append(mu); self.sd.append(sd)
            rows.append(pres); outs.append(np.full(len(pres), oo)); vals.append((v[pres] - mu) / sd); ws.append(wv[pres])
        self.rows = np.concatenate(rows); self.o = np.concatenate(outs).astype(int); self.y = np.concatenate(vals); self.w = np.concatenate(ws)
        self.Zd = Z[self.rows]; self.hb = None if hb is None else np.asarray(hb, float)[self.rows]; self.d = d
        if theta is not None:
            self.theta = np.asarray(theta, float); self.opt = {"nlml": self._nlml(self.theta, self.Zd, self.y, self.o, self.hb, self.w)[0], "start": -1}
        else:
            best = None
            for si, th0 in enumerate(starts):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    res = minimize(self._nlml, np.asarray(th0, float), args=(self.Zd, self.y, self.o, self.hb, self.w), jac=True, method="L-BFGS-B", bounds=self.bounds(d))
                if best is None or res.fun < best[0].fun:
                    best = (res, si)
            self.theta = best[0].x; self.opt = {"nlml": float(best[0].fun), "nit": int(best[0].nit), "success": bool(best[0].success), "start": best[1]}
        self._factor(); return self

    def _cross(self, Za, oa, Zb, ob, hba=None, hbb=None):
        le, A, _ = self._split(self.theta, self.d); K = np.zeros((len(Za), len(Zb)))
        for r in range(self.R):
            S = ((Za[:, None, :] - Zb[None, :, :]) ** 2) / np.exp(2 * le[r]); rr = np.sqrt(np.maximum(S.sum(-1), 0.0))
            K += (A[oa, r][:, None] * A[ob, r][None, :]) * (1 + S3 * rr) * np.exp(-S3 * rr)
        if self.b > 0 and hba is not None and hbb is not None:
            K += (oa[:, None] == ob[None, :]) * (self.b ** 2) * np.outer(hba, hbb)
        return K

    def _factor(self):
        n = len(self.y); K = self._cross(self.Zd, self.o, self.Zd, self.o, self.hb, self.hb)
        _, _, ls2 = self._split(self.theta, self.d); K[np.diag_indices(n)] += np.exp(ls2)[self.o] * self.w
        self.c = cho_factor(K + 1e-10 * np.eye(n), lower=True); self.alpha = cho_solve(self.c, self.y)

    def predict(self, Zs, out=0, hbs=None):
        """Latent mean and latent variance of output `out` at Zs, original units."""
        Zs = np.asarray(Zs, float); os_ = np.full(len(Zs), out); le, A, _ = self._split(self.theta, self.d)
        ks = self._cross(Zs, os_, self.Zd, self.o, hbs, self.hb); v = cho_solve(self.c, ks.T)
        kss = np.full(len(Zs), float(np.sum(A[out] ** 2)))
        if self.b > 0 and hbs is not None:
            kss = kss + (self.b ** 2) * np.asarray(hbs, float) ** 2
        m = ks @ self.alpha; lat = np.maximum(kss - np.einsum("ij,ji->i", ks, v), 1e-12)
        return self.mu[out] + self.sd[out] * m, self.sd[out] ** 2 * lat

    def noise_var(self, out=0):
        _, _, ls2 = self._split(self.theta, self.d); return self.sd[out] ** 2 * float(np.exp(ls2[out]))


def starts_lmc(d, n_out=2, R=2, tied=False):
    """The two registered starts (PROTOCOL_IR section 5)."""
    nl = 1 if tied else R
    a1 = np.array([[0.9, 0.3], [0.3, 0.9]])[:n_out, :R]; a2 = np.array([[0.7, 0.5], [0.5, 0.7]])[:n_out, :R]
    l1 = np.zeros(nl * d); l2 = np.r_[np.full(d, -0.5), np.full(d, 0.5)][:nl * d] if not tied else np.zeros(d)
    s1 = np.full(n_out, np.log(0.1)); s2 = np.full(n_out, np.log(0.01))
    return (np.r_[l1, a1.ravel(), s1], np.r_[l2, a2.ravel(), s2])


# ======================================================================================== acceptance V3
def validate():
    import src.rc18_gp as G
    rng = np.random.default_rng(7); checks, info = {}, {}
    n, d = 18, 4; Z = rng.normal(size=(n, d)); hb = rng.normal(size=n)
    y0 = np.sin(Z[:, 0]) + 0.3 * Z[:, 1] + 0.05 * rng.normal(size=n); y1 = 0.7 * y0 + np.cos(Z[:, 2]) + 0.05 * rng.normal(size=n); y1[[2, 5]] = np.nan
    m = LMC(); m.fit(Z, [y0, y1], [np.ones(n), np.ones(n)], hb=hb, theta=starts_lmc(d)[0])
    th = rng.normal(size=m.n_params(d)) * 0.4; f0, g0 = m._nlml(th, m.Zd, m.y, m.o, m.hb, m.w); num = np.zeros_like(th)
    for j in range(len(th)):
        e = np.zeros_like(th); e[j] = 1e-6; num[j] = (m._nlml(th + e, m.Zd, m.y, m.o, m.hb, m.w)[0] - m._nlml(th - e, m.Zd, m.y, m.o, m.hb, m.w)[0]) / 2e-6
    rel = float(np.max(np.abs(num - g0)) / max(1.0, np.max(np.abs(num)))); info["lmc_grad_rel_err"] = rel; checks["lmc_gradient_1e-5"] = rel < 1e-5
    mt = LMC(tied=True); mt.fit(Z, [y0, y1], [np.ones(n), np.ones(n)], hb=hb, theta=starts_lmc(d, tied=True)[0])
    tht = rng.normal(size=mt.n_params(d)) * 0.4; ft, gt = mt._nlml(tht, mt.Zd, mt.y, mt.o, mt.hb, mt.w); numt = np.zeros_like(tht)
    for j in range(len(tht)):
        e = np.zeros_like(tht); e[j] = 1e-6; numt[j] = (mt._nlml(tht + e, mt.Zd, mt.y, mt.o, mt.hb, mt.w)[0] - mt._nlml(tht - e, mt.Zd, mt.y, mt.o, mt.hb, mt.w)[0]) / 2e-6
    relt = float(np.max(np.abs(numt - gt)) / max(1.0, np.max(np.abs(numt)))); info["icm_grad_rel_err"] = relt; checks["icm_gradient_1e-5"] = relt < 1e-5
    ms = LMC(n_out=1); ms.fit(Z, [y0], [np.ones(n)], hb=hb, theta=starts_lmc(d, n_out=1)[0])
    ths = rng.normal(size=ms.n_params(d)) * 0.4; fs, gs = ms._nlml(ths, ms.Zd, ms.y, ms.o, ms.hb, ms.w); nums = np.zeros_like(ths)
    for j in range(len(ths)):
        e = np.zeros_like(ths); e[j] = 1e-6; nums[j] = (ms._nlml(ths + e, ms.Zd, ms.y, ms.o, ms.hb, ms.w)[0] - ms._nlml(ths - e, ms.Zd, ms.y, ms.o, ms.hb, ms.w)[0]) / 2e-6
    rels = float(np.max(np.abs(nums - gs)) / max(1.0, np.max(np.abs(nums)))); info["sum2_grad_rel_err"] = rels; checks["sum2_gradient_1e-5"] = rels < 1e-5
    # reduction: no cross-coupling (a = diag) -> depth prediction = single-output src.rc18_gp.GP with sf2 = a00^2, ell_1, noise s2_0, h basis b = 3
    a00, ell1, ls20 = 1.3, rng.normal(size=d) * 0.3, np.log(0.02)
    th_red = np.r_[ell1, rng.normal(size=d) * 0.3, [a00, 0.0, 0.0, 0.8], [ls20, np.log(0.05)]]
    mr = LMC(); mr.fit(Z, [y0, y1], [np.ones(n), np.ones(n)], hb=hb, theta=th_red); Zs = rng.normal(size=(9, d)); hbs = rng.normal(size=9)
    pm, pv = mr.predict(Zs, 0, hbs)
    g1 = G.GP(H_cols=1, b=3.0).fit(Z, y0, H=hb[:, None], theta0=np.r_[np.log(a00 ** 2), ell1, ls20], optimize=False); gm, gl, _ = g1.predict(Zs, Hs=hbs[:, None])
    info["reduction_max_abs_mean"] = float(np.max(np.abs(pm - gm))); info["reduction_max_abs_var"] = float(np.max(np.abs(pv - gl)))
    checks["reduction_equals_single_output_1e-8"] = info["reduction_max_abs_mean"] < 1e-8 and info["reduction_max_abs_var"] < 1e-8
    # ICM cancellation (isotopic, noise-free, no basis): joint depth prediction = single-output prediction with kernel B00 k
    n2 = 15; Z2 = rng.normal(size=(n2, d)); u = rng.normal(size=n2); v0 = np.sin(Z2[:, 0]) + Z2[:, 1]; v1 = 0.5 * v0 + np.cos(Z2[:, 3])
    th_icm = np.r_[rng.normal(size=d) * 0.3, [1.1, 0.4, 0.6, 0.9], [np.log(1e-6), np.log(1e-6)]]
    mi = LMC(tied=True, b=0.0); mi.fit(Z2, [v0, v1], [np.ones(n2), np.ones(n2)], hb=None, theta=th_icm); Zs2 = rng.normal(size=(7, d)); im, iv = mi.predict(Zs2, 0, None)
    le, A, _ = mi._split(mi.theta, d); B00 = float(np.sum(A[0] ** 2))
    gi = G.GP().fit(Z2, v0, theta0=np.r_[np.log(B00), le[0], np.log(1e-6)], optimize=False); gim, giv, _ = gi.predict(Zs2)
    info["icm_cancellation_max_abs_mean"] = float(np.max(np.abs(im - gim)))
    checks["icm_noise_free_isotopic_cancels_1e-6"] = info["icm_cancellation_max_abs_mean"] < 1e-6 * max(1.0, float(np.max(np.abs(gim))))
    # a fitted LMC runs from the registered starts
    mf = LMC(); mf.fit(Z, [y0, y1], [np.ones(n), np.ones(n)], hb=hb, starts=starts_lmc(d)); checks["fit_runs"] = bool(np.all(np.isfinite(mf.predict(Zs, 0, hbs)[0])))
    checks = {k: bool(v) for k, v in checks.items()}
    res = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "info": info}
    print(json.dumps(res, indent=1)); return res


if __name__ == "__main__":
    {"validate": validate}[sys.argv[1]]()
