"""Paid-only posterior implementations. Import after acquiring a coordinated slot."""
from dataclasses import dataclass
import hashlib
import json
import math
import time
import numpy as np
from scipy.linalg import cho_factor, cho_solve, solve_triangular
from scipy.optimize import minimize
from scipy.special import logsumexp, ndtr

COUNTERS = {"fit_requests": 0, "factorizations": 0, "optimizer_evaluations": 0,
            "planning_states": 0}
METER = None


def count(kind):
    if METER is not None:
        METER.charge(kind)
    COUNTERS[kind] += 1


def matern(x, z, length):
    q = np.sum(((x[:, None, :] - z[None, :, :]) / length) ** 2, axis=2)
    a = np.sqrt(3 * np.maximum(q, 0))
    return (1 + a) * np.exp(-a)


def compact(x, z, radius):
    r = np.sqrt(np.sum((x[:, None, :] - z[None, :, :]) ** 2, axis=2)) / radius
    return np.maximum(1 - r, 0) ** 5 * (5 * r + 1)


@dataclass(frozen=True)
class Spec:
    multiscale: bool = False
    noise_sd: float = .06
    short_axis: int = -1
    radius: float = 0.
    local_sd: float = 0.


class Component:
    def __init__(self, spec, lengths=None, signal_sd=1.):
        self.spec = spec
        self.lengths = lengths
        self.signal_sd = signal_sd

    @property
    def diagonal(self):
        return self.signal_sd ** 2 + self.spec.local_sd ** 2

    def local_kernel(self, x, z):
        return self.spec.local_sd ** 2 * compact(x, z, self.spec.radius) if self.spec.radius else np.zeros((len(x), len(z)))

    def kernel(self, x, z):
        if self.lengths is not None:
            lengths = self.lengths
        elif self.spec.short_axis >= 0:
            lengths = np.full(x.shape[1], 1.2)
            lengths[self.spec.short_axis] = .08
        else:
            lengths = .45
        k = matern(x, z, lengths)
        if self.spec.multiscale:
            k = .8 * k + .2 * matern(x, z, .12)
        return self.signal_sd ** 2 * k + self.local_kernel(x, z)

    def fit(self, x, y):
        count("factorizations")
        self.x, self.y = np.asarray(x), np.asarray(y)
        self.cache = {}
        if not len(y):
            self.factor = self.alpha = None
            self.log_evidence = 0.
        else:
            k = self.kernel(x, x) + (self.spec.noise_sd ** 2 + 1e-10) * np.eye(len(x))
            self.factor = cho_factor(k, lower=True, check_finite=False)
            self.alpha = cho_solve(self.factor, y, check_finite=False)
            self.log_evidence = float(-.5 * y @ self.alpha - np.log(np.diag(self.factor[0])).sum()
                                      - .5 * len(y) * math.log(2 * math.pi))
        return self

    def project(self, x):
        if id(x) not in self.cache:
            if self.factor is None:
                m, v = np.zeros(len(x)), np.zeros((0, len(x)))
            else:
                k = self.kernel(self.x, x)
                m = k.T @ self.alpha
                v = solve_triangular(self.factor[0], k, lower=True, check_finite=False)
            self.cache[id(x)] = (x, m, v)
        _, m, v = self.cache[id(x)]
        return m, v

    def predict(self, x):
        m, v = self.project(x)
        variance = self.diagonal - np.sum(v * v, axis=0)
        if variance.min(initial=0) < -1e-7:
            raise ArithmeticError("Invalid latent variance")
        return m, np.maximum(variance, 1e-12)

    def discrepancy(self, x):
        if not self.spec.radius or self.factor is None:
            return np.zeros(len(x)), np.full(len(x), self.spec.local_sd ** 2)
        k = self.local_kernel(self.x, x)
        v = solve_triangular(self.factor[0], k, lower=True, check_finite=False)
        return k.T @ self.alpha, np.maximum(self.spec.local_sd ** 2 - np.sum(v * v, axis=0), 0.)


@dataclass(frozen=True)
class GaussianState:
    """Scalar paid-output working posterior. Candidate covariance is LATENT."""
    reference_mean: np.ndarray
    reference_variance: np.ndarray
    candidate_mean: np.ndarray
    candidate_covariance: np.ndarray
    cross_covariance: np.ndarray
    noise_variance: np.ndarray
    availability: float
    source_hash: str
    ids: tuple

    def digest(self):
        h = hashlib.sha256((self.source_hash + repr(self.ids) + str(self.availability)).encode())
        for array in (self.reference_mean, self.reference_variance, self.candidate_mean,
                      self.candidate_covariance, self.cross_covariance, self.noise_variance):
            h.update(np.ascontiguousarray(array).tobytes())
        return h.hexdigest()


class Posterior:
    def __init__(self, kind="existing", dimension=4, ard_options=None):
        if kind not in ("existing", "local", "ard"):
            raise ValueError(kind)
        self.kind, self.dimension = kind, dimension
        self.ard_options = ard_options or {"maxiter": 120, "refit_every": 4,
                                           "ftol": 1e-9, "gtol": 1e-5}
        self.ard_theta = None
        self.ard_last_budget = None
        self.optimizer_log = []
        if kind != "ard":
            base = [Spec(ms, noise) for ms in (False, True) for noise in (.06, .25)]
            base += [Spec(False, noise, axis) for axis in range(dimension) for noise in (.06, .25)]
            prior = np.r_[np.full(4, .5 / 4), np.full(2 * dimension, .5 / (2 * dimension))]
            self.components, weights = [], []
            local_choices = [(0., 0., 1.)] if kind == "existing" else [(0., 0., .5), (.45, .6, .25), (.9, .6, .25)]
            for radius, sd, p in local_choices:
                for spec, w in zip(base, prior):
                    self.components.append(Component(Spec(spec.multiscale, spec.noise_sd, spec.short_axis, radius, sd)))
                    weights.append(w * p)
            self.prior = np.asarray(weights)
        else:
            self.components, self.prior = [], np.ones(1)

    def _ard(self, x, y, budget):
        opts, d = self.ard_options, self.dimension
        refit = self.ard_theta is None or budget - self.ard_last_budget >= opts["refit_every"]
        if not refit:
            return
        started = time.perf_counter()
        diff2 = (x[:, None] - x[None, :]) ** 2
        def objective(theta):
            count("factorizations")
            count("optimizer_evaluations")
            ell = np.exp(theta[:d])
            amp2, noise2 = np.exp(2 * theta[d:])
            q = diff2 / ell ** 2
            r = np.sqrt(np.maximum(q.sum(2), 0))
            e = np.exp(-math.sqrt(3) * r)
            k = amp2 * (1 + math.sqrt(3) * r) * e
            c = k + (noise2 + 1e-10) * np.eye(len(x))
            fac = cho_factor(c, lower=True, check_finite=False)
            alpha = cho_solve(fac, y, check_finite=False)
            loss = .5 * y @ alpha + np.log(np.diag(fac[0])).sum() + len(x) * .5 * math.log(2 * math.pi)
            w = cho_solve(fac, np.eye(len(x)), check_finite=False) - np.outer(alpha, alpha)
            grad = np.r_[.5 * np.einsum("ij,ijd->d", w, 3 * amp2 * e[:, :, None] * q),
                         np.sum(w * k), noise2 * np.trace(w)]
            return float(loss), grad
        initial_lengths = [np.full(d, .12), np.full(d, .45), np.full(d, 1.2)]
        for axis in range(d):
            ell = np.full(d, 1.2)
            ell[axis] = .08
            initial_lengths.append(ell)
        # All seven structural starts are retained at every optimizer refresh.
        starts = [np.log(np.r_[ell, 1., noise]) for ell in initial_lengths for noise in (.06, .25)]
        if self.ard_theta is not None:
            starts.insert(0, self.ard_theta.copy())
        bounds = [(math.log(.015), math.log(5.))] * d + [(math.log(.03), math.log(3.)), (math.log(.015), math.log(.6))]
        results = [minimize(objective, t, jac=True, method="L-BFGS-B", bounds=bounds,
                            options={k: opts[k] for k in ("maxiter", "ftol", "gtol")}) for t in starts]
        finite = [r for r in results if np.isfinite(r.fun)]
        if not finite:
            raise ArithmeticError("No finite ARD optimum; retain failed unit")
        best = min(finite, key=lambda r: r.fun)
        self.ard_theta = best.x.copy()
        self.ard_last_budget = budget
        self.optimizer_log.append({"budget": budget, "starts": len(starts),
                                   "successes": sum(bool(r.success) for r in results),
                                   "chosen_success": bool(best.success), "best_nll": float(best.fun),
                                   "max_gradient": float(np.max(np.abs(best.jac))),
                                   "theta": best.x.tolist(), "seconds": time.perf_counter() - started,
                                   "all_nll": [float(r.fun) for r in results],
                                   "all_messages": [str(r.message) for r in results]})

    def fit(self, x_paid, observations, ids):
        count("fit_requests")
        assert len(set(ids)) == len(ids), "A paid ID cannot be observed twice"
        good = np.array([y is not None and math.isfinite(y) for y in observations], bool)
        x = np.asarray(x_paid)[good]
        y = np.array([v for v, ok in zip(observations, good) if ok], float)
        if self.kind == "ard":
            self._ard(x, y, len(ids))
            d = self.dimension
            self.components = [Component(Spec(noise_sd=float(np.exp(self.ard_theta[-1]))),
                                         lengths=np.exp(self.ard_theta[:d]),
                                         signal_sd=float(np.exp(self.ard_theta[d])))]
        for c in self.components:
            c.fit(x, y)
        evidence = np.array([c.log_evidence for c in self.components]) + np.log(self.prior)
        self.weights = np.exp(evidence - logsumexp(evidence))
        # Availability is inferred only from paid observations, not the family name.
        self.availability = (2. + good.sum()) / (2.25 + len(ids))
        self.paid_count = len(ids)
        self.model_hash = hashlib.sha256(json.dumps({"kind": self.kind, "ids": list(map(int, ids)),
             "x": np.asarray(x_paid).tolist(), "observations": observations,
             "theta": self.ard_theta.tolist() if self.ard_theta is not None else None,
             "specs": [c.spec.__dict__ for c in self.components]}, sort_keys=True, allow_nan=False).encode()).hexdigest()
        return self

    def predict(self, x):
        pairs = [c.predict(x) for c in self.components]
        means, variances = map(np.asarray, zip(*pairs))
        mean = self.weights @ means
        var = self.weights @ (variances + means ** 2) - mean ** 2
        probability = self.weights @ ndtr(means / np.sqrt(variances))
        return mean, np.maximum(var, 1e-12), probability

    def snapshot(self, candidates, references, ids):
        cm, cc, rm, rv, cross = [], [], [], [], []
        for c in self.components:
            m, v = c.project(candidates)
            mr, vr = c.project(references)
            cm.append(m)
            cc.append(c.kernel(candidates, candidates) - v.T @ v)
            rm.append(mr)
            rv.append(c.diagonal - np.sum(vr * vr, axis=0))
            cross.append(c.kernel(references, candidates) - vr.T @ v)
        cm, cc, rm, rv, cross = map(np.asarray, (cm, cc, rm, rv, cross))
        w = self.weights
        m, mr = w @ cm, w @ rm
        cov = np.einsum("c,cij->ij", w, cc) + np.einsum("c,ci,cj->ij", w, cm, cm) - np.outer(m, m)
        rvar = w @ (rv + rm ** 2) - mr ** 2
        cr = np.einsum("c,cri->ri", w, cross) + np.einsum("c,cr,ci->ri", w, rm, cm) - np.outer(mr, m)
        noise = np.full(len(candidates), w @ np.array([c.spec.noise_sd ** 2 for c in self.components]))
        arrays = [mr, np.maximum(rvar, 1e-12), m, cov, cr, noise]
        for a in arrays:
            if not np.isfinite(a).all():
                raise ArithmeticError("Nonfinite snapshot")
            a.setflags(write=False)
        return GaussianState(*arrays, float(self.availability), self.model_hash, tuple(map(int, ids)))

    def local_summary(self):
        local = np.array([c.spec.radius > 0 for c in self.components])
        return {"local_posterior_weight": float(self.weights[local].sum()),
                "effective_components": float(1 / np.sum(self.weights ** 2)),
                "weights": self.weights.tolist(),
                "support_weight": {str(radius): float(sum(w for c, w in zip(self.components, self.weights) if c.spec.radius == radius))
                                   for radius in sorted({c.spec.radius for c in self.components})}}
