"""Evaluator/oracle only. Never imported by model.py, acquisition.py or policy.py."""
import hashlib
import math
import numpy as np
from scipy.special import ndtr
from scipy.stats import qmc
from policy import PaidObservation, feature_start


FAMILIES = ("smooth", "island_small_unseen", "island_large_unseen",
    "island_small_seen", "island_large_seen", "anisotropic", "local_scale",
    "heteroscedastic", "heavy_tail", "null", "corrupt_correlated",
    "multi_shared", "multi_conflict", "multi_missing")


class World:
    def __init__(self, family, seed, dimension=4, pool_size=512, eval_size=2048, ref_size=128, startup=8,
                 reference_rule='iid', reference_seed=251018):
        if family not in FAMILIES:
            raise ValueError("unregistered family")
        self.family, self.seed, self.dimension = family, seed, dimension
        self.channels = 2 if family.startswith("multi_") else 1
        rng = np.random.default_rng(seed)
        self.x = rng.uniform(size=(pool_size, dimension))
        self.eval_x = rng.uniform(size=(eval_size, dimension))
        if reference_rule == 'sobol':
            rng.uniform(size=(128, dimension))  # Preserve the original world/noise stream.
            if ref_size < 1 or ref_size & (ref_size-1):
                raise ValueError('Sobol reference size must be a power of two')
            self.ref_x = qmc.Sobol(dimension, scramble=True, seed=reference_seed).random_base2(ref_size.bit_length()-1)
        elif reference_rule == 'iid':
            self.ref_x = rng.uniform(size=(ref_size, dimension))
        else:
            raise ValueError('unregistered public reference rule')
        self.startup = feature_start(self.x, startup, seed+57)
        self.phase = float(rng.uniform(-math.pi, math.pi))
        self.w = rng.normal(size=dimension); self.w /= np.linalg.norm(self.w)
        self.offset = float(rng.uniform(-.1, .1))
        self.radius = float(rng.uniform(.17, .22) if "small" in family else rng.uniform(.28, .34))
        self.center = rng.uniform(.35, .65, dimension); self.center[0] = rng.uniform(.65, .78)
        self.conditioning_attempts = 0
        if family.startswith("island_"):
            want_seen = family.endswith("_seen")
            for attempt in range(10000):
                center = rng.uniform(.05, .95, dimension); center[0] = rng.uniform(.60, .95)
                hit = bool(np.any(np.linalg.norm(self.x[self.startup]-center, axis=1) < self.radius))
                if hit == want_seen:
                    self.center = center; self.conditioning_attempts = attempt+1; break
            else:
                raise RuntimeError("world conditioning failed; retain failure, never silently replace seed")
        self._f, self._g, self._island, self._reported = self._truth(self.x)
        self._ef, self._eg, self._ei, self._er = self._truth(self.eval_x)
        sigma = np.full(pool_size, .06)
        if family == "heteroscedastic":
            sigma += .32*np.exp(-np.sum((self.x-self.center)**2, axis=1)/.12)
        noise = rng.normal(size=pool_size)*sigma
        if family == "heavy_tail":
            noise = .10*rng.standard_t(3, pool_size)/math.sqrt(3)
            noise += (rng.uniform(size=pool_size) < .04)*rng.normal(0, .7, pool_size)
        self._y = np.column_stack([self._reported+noise, self._g+rng.normal(0, .06, pool_size)])[:, :self.channels]
        self._quality = np.ones_like(self._y, bool)
        if family == "multi_missing":
            self._quality[:, 0] = rng.uniform(size=pool_size) >= .12
            self._quality[:, 1] = rng.uniform(size=pool_size) >= .22
        self._boundary = np.abs(self._ef) <= .10
        self.hash = hashlib.sha256(self.x.tobytes()+self.eval_x.tobytes()+self._y.tobytes()).hexdigest()

    def _truth(self, x):
        family = self.family
        smooth = 1.8*((x-.5)@self.w)+.12*np.sin(2*math.pi*x[:, 1]+self.phase)+self.offset
        d = np.linalg.norm(x-self.center, axis=1)
        island = np.zeros(len(x), bool)
        f = smooth
        if family.startswith("island_"):
            f = 3*np.maximum(.20-x[:, 0], self.radius-d)
            island = (d < self.radius) & (x[:, 0] > .20)
        elif family == "anisotropic":
            f = np.sin(8*math.pi*x[:, 0]+self.phase)+.25*(x[:, 1]-.5)+.05*(x[:, 2]-.5)
        elif family == "local_scale":
            gate = np.exp(-np.sum((x-self.center)**2, axis=1)/.12)
            f = smooth+.85*gate*np.sin(10*math.pi*x[:, 0]+self.phase)
        elif family in ("null", "corrupt_correlated"):
            f = -.5+.12*np.sin(2*math.pi*x[:, 0]+self.phase)
        reported = f.copy()
        if family == "corrupt_correlated":
            reported += 1.4*np.exp(-np.sum((x-self.center)**2, axis=1)/.065)
        g = .8*f+.25*np.sin(2*math.pi*x[:, 1]+self.phase)
        if family == "multi_conflict":
            g = .8*np.where(x[:, 0] < .5, 1., -1.)*f+.35*np.cos(3*math.pi*x[:, 2])
        return f, g, island, reported

    def pay(self, i):
        values = tuple(float(y) if good else None for y, good in zip(self._y[i], self._quality[i]))
        return PaidObservation(int(i), values, tuple(bool(q) for q in self._quality[i]),
                               1., None, "available" if self._quality[i].all() else "missing channel retained as paid")

    def evaluate(self, model, paid):
        m, v, probability = model.predict(self.eval_x)
        truth = self._ef > 0
        decision = probability > .5
        error = decision != truth
        r1 = float(decision[truth].mean()) if truth.any() else None
        r0 = float((~decision[~truth]).mean()) if (~truth).any() else None
        boundary_error = float(error[self._boundary].mean()) if self._boundary.any() else None
        island_recall = float(decision[self._ei].mean()) if self._ei.any() else None
        distance = np.linalg.norm(self.eval_x[:, None]-self.x[paid][None], axis=2).min(1)
        hits = [k+1 for k, i in enumerate(paid) if self._island[i] and self._quality[i, 0]]
        clipped = np.clip(probability, 1e-12, 1-1e-12)
        out = {"error": float(error.mean()), "boundary_error": boundary_error,
            "island_recall": island_recall, "recall_positive": r1, "recall_negative": r0,
            "BA": (r1+r0)/2 if r1 is not None and r0 is not None else None,
            "MAE": float(np.abs(m-self._ef).mean()), "RMSE": float(np.sqrt(np.mean((m-self._ef)**2))),
            "brier": float(np.mean((probability-truth)**2)),
            "log_loss": float(-np.mean(truth*np.log(clipped)+(1-truth)*np.log(1-clipped))),
            "coverage90": float(np.mean(np.abs(m-self._ef) <= 1.6448536269514722*np.sqrt(v))),
            "feature_coverage_025": float(np.mean(distance <= .25)),
            "island_feature_coverage_025": float(np.mean(distance[self._ei] <= .25)) if self._ei.any() else None,
            "positive_paid_count": int(np.sum(self._f[paid] > 0)), "paid_island_count": len(hits),
            "first_island_query": hits[0] if hits else None,
            "third_island_query": hits[2] if len(hits) >= 3 else None,
            "invalid_primary_paid": int(np.sum(~self._quality[paid, 0])),
            "evaluator_boundary_n": int(self._boundary.sum()), "evaluator_island_n": int(self._ei.sum()),
            "reported_channel_RMSE": float(np.sqrt(np.mean((m-self._er)**2))),
            "mixture_effective_components": float(1/np.sum(model.weights**2))}
        # Missing conditional subsets are N/A, not a reason to drop a world.
        out["target_met"] = bool(out["error"] <= .08 and (boundary_error is None or boundary_error <= .25)
            and (island_recall is None or island_recall >= .70)
            and (r0 is None or r0 >= .85) and (r1 is None or r1 >= .85))
        if self.channels == 2:
            am, av, ap = model.predict(self.eval_x, 1)
            out["aux_RMSE"] = float(np.sqrt(np.mean((am-self._eg)**2)))
            out["aux_MAE"] = float(np.abs(am-self._eg).mean())
            out["aux_coverage90"] = float(np.mean(np.abs(am-self._eg) <= 1.6448536269514722*np.sqrt(av)))
        return out

    def evaluator_provenance(self):
        return {"family": self.family, "seed": self.seed, "hash": self.hash,
            "center_evaluator_only": self.center.tolist(), "radius_evaluator_only": self.radius,
            "conditioning_attempts": self.conditioning_attempts,
            "startup_contains_island": bool(self._island[self.startup].any()),
            "pool_island_n": int(self._island.sum()), "eval_island_n": int(self._ei.sum())}
