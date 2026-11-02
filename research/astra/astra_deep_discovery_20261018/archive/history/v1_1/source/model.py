"""Paid-only finite GP mixture. Import only inside a coordinated numeric unit."""
from dataclasses import dataclass
import hashlib
import json
import math
import numpy as np
from scipy.linalg import cho_factor, cho_solve, solve_triangular
from scipy.special import logsumexp, ndtr


def matern(a, b, length):
    r = np.sqrt(np.maximum(((a[:, None, :]-b[None, :, :])**2).sum(2), 0))
    z = math.sqrt(3)*r/length
    return (1+z)*np.exp(-z)


@dataclass(frozen=True)
class Spec:
    multiscale: bool
    noise_sd: float
    correlation: float = 0.


class Component:
    def __init__(self, spec, channels):
        self.spec, self.channels = spec, channels

    def kernel(self, a, ao, b, bo):
        k = matern(a, b, .45)
        if self.spec.multiscale:
            k = .8*k+.2*matern(a, b, .12)
        corr = np.where(np.asarray(ao)[:, None] == np.asarray(bo)[None, :], 1., self.spec.correlation)
        return k*corr

    def fit(self, x, output, y):
        self.x, self.output, self.y = np.asarray(x), np.asarray(output), np.asarray(y)
        if not len(y):
            self.factor, self.alpha, self.log_evidence = None, None, 0.
            return self
        k = self.kernel(self.x, self.output, self.x, self.output)
        k += np.eye(len(y))*(self.spec.noise_sd**2+1e-10)
        self.factor = cho_factor(k, lower=True)
        self.alpha = cho_solve(self.factor, self.y)
        self.log_evidence = float(-.5*y@self.alpha-np.log(np.diag(self.factor[0])).sum()
                                  -.5*len(y)*math.log(2*math.pi))
        return self

    def project(self, x, output):
        if self.factor is None:
            return np.zeros(len(x)), np.zeros((0, len(x)))
        k = self.kernel(self.x, self.output, x, output)
        return k.T@self.alpha, solve_triangular(self.factor[0], k, lower=True)

    def predict(self, x, output):
        m, v = self.project(x, output)
        diag = 1.-np.sum(v*v, axis=0)
        if np.min(diag) < -1e-7:
            raise ArithmeticError("negative latent conditional variance")
        return m, np.maximum(diag, 1e-12)


def _array_hash(h, value):
    a = np.ascontiguousarray(value)
    h.update(str(a.shape).encode())
    h.update(a.tobytes())


@dataclass(frozen=True)
class Snapshot:
    model_hash: str
    paid_count: int
    mean: np.ndarray                  # candidate x output
    latent_cov: np.ndarray            # candidate x output x output
    noise_cov: np.ndarray             # candidate x output x output
    probability: np.ndarray           # primary component-mixture exceedance
    ref_mean: np.ndarray
    ref_variance: np.ndarray
    ref_probability: np.ndarray
    cross_cov: np.ndarray             # reference primary x candidate x output
    weights: np.ndarray
    availability_weights: np.ndarray  # patterns: none, primary, auxiliary, both (J=2)

    def digest(self):
        h = hashlib.sha256((self.model_hash+str(self.paid_count)).encode())
        for field in (self.mean, self.latent_cov, self.noise_cov, self.probability,
                      self.ref_mean, self.ref_variance, self.ref_probability,
                      self.cross_cov, self.weights, self.availability_weights):
            _array_hash(h, field)
        return h.hexdigest()


class MixtureGP:
    def __init__(self, kind="simple", channels=1):
        if kind not in ("simple", "mixture") or channels not in (1, 2):
            raise ValueError("unknown model or output contract")
        self.kind, self.channels = kind, channels
        specs = [Spec(False, .06)] if kind == "simple" else [
            Spec(ms, noise, rho) for ms in (False, True) for noise in (.06, .25)
            for rho in ((0., .7, -.7) if channels == 2 else (0.,))]
        self.components = [Component(s, channels) for s in specs]

    def fit(self, x_paid, observations, ids):
        # observations are lists with None for missing/quality-invalid channels.
        xx, oo, yy = [], [], []
        counts = np.ones(2**self.channels)*.25
        counts[-1] = 2.  # mild prior that every channel is available
        for x, values in zip(x_paid, observations):
            mask = 0
            for j, y in enumerate(values):
                if y is not None and math.isfinite(y):
                    xx.append(x); oo.append(j); yy.append(y); mask |= 1 << j
            counts[mask] += 1
        x = np.asarray(xx, float).reshape(-1, x_paid.shape[1])
        y = np.asarray(yy, float)
        for c in self.components:
            c.fit(x, oo, y)
        le = np.array([c.log_evidence for c in self.components])
        self.weights = np.exp(le-logsumexp(le))
        self.availability_weights = counts/counts.sum()
        self.paid_count = len(ids)
        self.model_hash = hashlib.sha256(json.dumps({"ids": list(ids), "paid": observations,
            "kind": self.kind, "specs": [c.spec.__dict__ for c in self.components]},
            sort_keys=True, allow_nan=False).encode()).hexdigest()
        return self

    def predict(self, x, channel=0):
        out = np.full(len(x), channel, int)
        pair = [c.predict(x, out) for c in self.components]
        means, variances = np.array([a for a, b in pair]), np.array([b for a, b in pair])
        m = self.weights@means
        var = self.weights@(variances+means**2)-m*m
        p = self.weights@ndtr(means/np.sqrt(variances))
        return m, np.maximum(var, 1e-12), p

    def snapshot(self, candidates, references):
        n, j, r = len(candidates), self.channels, len(references)
        xx = np.repeat(candidates, j, axis=0)
        oo = np.tile(np.arange(j), n)
        zero = np.zeros(r, int)
        cm, cc, rm, rv, cross, probs, rprobs = [], [], [], [], [], [], []
        for c in self.components:
            m, v = c.project(xx, oo)
            mr, vr = c.project(references, zero)
            m = m.reshape(n, j)
            # Within-candidate output covariance without an n*j squared matrix.
            v = v.reshape(len(c.y), n, j)
            b = np.full((j, j), c.spec.correlation); np.fill_diagonal(b, 1.)
            cov = b[None, :, :]-np.einsum("tni,tnj->nij", v, v)
            refvar = np.maximum(1.-np.sum(vr*vr, axis=0), 1e-12)
            cr = c.kernel(references, zero, xx, oo)-vr.T@v.reshape(len(c.y), n*j)
            cm.append(m); cc.append(cov); rm.append(mr); rv.append(refvar)
            cross.append(cr.reshape(r, n, j))
            probs.append(ndtr(m[:, 0]/np.sqrt(np.maximum(cov[:, 0, 0], 1e-12))))
            rprobs.append(ndtr(mr/np.sqrt(refvar)))
        cm, cc, rm, rv, cross = map(np.asarray, (cm, cc, rm, rv, cross))
        w = self.weights
        m = np.einsum("c,cnj->nj", w, cm)
        mr = w@rm
        cov = np.einsum("c,cnij->nij", w, cc)+np.einsum("c,cni,cnj->nij", w, cm, cm)-np.einsum("ni,nj->nij", m, m)
        rvar = w@(rv+rm*rm)-mr*mr
        cr = np.einsum("c,crnj->rnj", w, cross)+np.einsum("c,cr,cnj->rnj", w, rm, cm)-mr[:, None, None]*m[None, :, :]
        noise = np.eye(j)[None, :, :]*float(w@np.array([c.spec.noise_sd**2 for c in self.components]))
        noise = np.broadcast_to(noise, (n, j, j)).copy()
        arrays = [m, cov, noise, w@np.asarray(probs), mr, np.maximum(rvar, 1e-12),
                  w@np.asarray(rprobs), cr, w.copy(), self.availability_weights.copy()]
        for a in arrays:
            if not np.isfinite(a).all():
                raise ArithmeticError("nonfinite posterior")
            a.setflags(write=False)
        return Snapshot(self.model_hash, self.paid_count, *arrays)
