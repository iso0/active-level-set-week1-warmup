"""Evaluator/oracle only. Selectors must never import this module."""
import hashlib
import math
import numpy as np
from scipy.stats import qmc

FAMILIES = ("smooth", "coordinate", "rotated", "local_scale", "island_small",
            "island_large", "heteroscedastic", "heavy_tail", "null", "corrupt_correlated",
            "missing")


def feature_prefix(x, n, seed):
    rng = np.random.default_rng(seed)
    chosen = [int(rng.integers(len(x)))]
    d2 = np.sum((x - x[chosen[0]]) ** 2, axis=1)
    while len(chosen) < n:
        d2[chosen] = -1
        i = int(np.argmax(d2))
        chosen.append(i)
        d2 = np.minimum(d2, np.sum((x - x[i]) ** 2, axis=1))
    return chosen


class World:
    def __init__(self, family, seed, pool_size=512, eval_size=2048, ref_size=1024, prefix=32):
        assert family in FAMILIES
        self.family, self.seed = family, int(seed)
        rng = np.random.default_rng(seed)
        self.x = rng.uniform(size=(pool_size, 4))
        self.eval_x = rng.uniform(size=(eval_size, 4))
        self.ref_x = qmc.Sobol(4, scramble=True, seed=20261020).random_base2(int(math.log2(ref_size)))
        assert len(self.ref_x) == ref_size
        self.prefix = feature_prefix(self.x, prefix, seed + 57)
        self.phase = float(rng.uniform(-math.pi, math.pi))
        self.w = rng.normal(size=4); self.w /= np.linalg.norm(self.w)
        # Independent random orientation, never supplied to learners.
        self.axis = rng.normal(size=4); self.axis /= np.linalg.norm(self.axis)
        self.offset = float(rng.uniform(-.1, .1))
        self.center = rng.uniform(.1, .9, 4)
        self.center[0] = rng.uniform(.6, .9)
        self.radius = float(rng.uniform(.17, .22) if family == "island_small" else rng.uniform(.28, .34))
        # No rejection, planted startup hit, or seed replacement.
        self.f, self.reported, self.island = self.truth(self.x)
        self.ef, self.er, self.ei = self.truth(self.eval_x)
        sigma = np.full(pool_size, .06)
        if family == "heteroscedastic":
            sigma += .32 * np.exp(-np.sum((self.x - self.center) ** 2, axis=1) / .12)
        noise = rng.normal(size=pool_size) * sigma
        if family == "heavy_tail":
            noise = .10 * rng.standard_t(3, pool_size) / math.sqrt(3)
            noise += (rng.uniform(size=pool_size) < .04) * rng.normal(0, .7, pool_size)
        self.y = self.reported + noise
        self.quality = np.ones(pool_size, bool)
        if family == "missing":
            self.quality = rng.uniform(size=pool_size) >= .15
        self.band = np.abs(self.ef) <= .10
        h = hashlib.sha256((family + str(seed)).encode())
        for a in (self.x, self.eval_x, self.ref_x, self.f, self.reported, self.island,
                  self.ef, self.er, self.ei, self.y, self.quality):
            h.update(a.tobytes())
        self.hash = h.hexdigest()

    def truth(self, x):
        smooth = 1.8 * ((x - .5) @ self.w) + .12 * np.sin(2 * math.pi * x[:, 1] + self.phase) + self.offset
        f = smooth
        island = np.zeros(len(x), bool)
        distance = np.linalg.norm(x - self.center, axis=1)
        if self.family.startswith("island"):
            f = 3 * np.maximum(.20 - x[:, 0], self.radius - distance)
            island = (distance < self.radius) & (x[:, 0] > .20)
        elif self.family == "coordinate":
            f = np.sin(8 * math.pi * x[:, 0] + self.phase) + .25 * (x[:, 1] - .5) + .05 * (x[:, 2] - .5)
        elif self.family == "rotated":
            f = np.sin(8 * math.pi * ((x - .5) @ self.axis) + self.phase) + .2 * ((x - .5) @ self.w)
        elif self.family == "local_scale":
            f = smooth + .85 * np.exp(-np.sum((x - self.center) ** 2, axis=1) / .12) * np.sin(10 * math.pi * x[:, 0] + self.phase)
        elif self.family in ("null", "corrupt_correlated"):
            f = -.5 + .12 * np.sin(2 * math.pi * x[:, 0] + self.phase)
        reported = f.copy()
        if self.family == "corrupt_correlated":
            reported += 1.4 * np.exp(-np.sum((x - self.center) ** 2, axis=1) / .065)
        return f, reported, island

    def pay(self, i):
        return {"paid_id": int(i), "outputs": [float(self.y[i]) if self.quality[i] else None],
                "quality": ["valid" if self.quality[i] else "missing"],
                "cost": 1., "physical_seconds": None}

    def provenance(self):
        hit = [j + 1 for j, i in enumerate(self.prefix) if self.island[i] and self.quality[i]]
        return {"world_hash": self.hash, "family": self.family, "seed": self.seed,
                "public_prefix_ids": self.prefix, "pool_island_n": int(self.island.sum()),
                "evaluator_island_n": int(self.ei.sum()), "center_evaluator_only": self.center.tolist(),
                "radius_evaluator_only": self.radius, "axis_evaluator_only": self.axis.tolist(),
                "common_prefix_first_valid_hit": hit[0] if hit else None,
                "common_prefix_contains_valid_hit": bool(hit), "conditioned_on_hit": False}

    def evaluate(self, model, paid):
        mean, var, p = model.predict(self.eval_x)
        label, decision = self.ef > 0, p > .5
        errors = label != decision
        r1 = float(decision[label].mean()) if label.any() else None
        r0 = float((~decision[~label]).mean()) if (~label).any() else None
        boundary = float(errors[self.band].mean()) if self.band.any() else None
        island = float(decision[self.ei].mean()) if self.ei.any() else None
        cp = np.clip(p, 1e-12, 1-1e-12)
        hit = [k+1 for k, i in enumerate(paid) if self.island[i] and self.quality[i]]
        result = {"budget": len(paid), "error": float(errors.mean()), "boundary_error": boundary,
                  "recall_positive": r1, "recall_negative": r0,
                  "BA": (r1+r0)/2 if r1 is not None and r0 is not None else None,
                  "island_recall": island, "island_error": None if island is None else 1-island,
                  "brier": float(np.mean((p-label) ** 2)),
                  "log_loss": float(-np.mean(label*np.log(cp)+(1-label)*np.log(1-cp))),
                  "RMSE": float(np.sqrt(np.mean((mean-self.ef) ** 2))),
                  "reported_RMSE": float(np.sqrt(np.mean((mean-self.er) ** 2))),
                  "coverage90": float(np.mean(abs(mean-self.ef) <= 1.6448536269514722*np.sqrt(var))),
                  "boundary_n": int(self.band.sum()), "island_n": int(self.ei.sum()),
                  "first_hit": hit[0] if hit else None, "third_hit": hit[2] if len(hit) >= 3 else None,
                  "island_queries": len(hit), "positive_queries": int((self.f[paid] > 0).sum()),
                  "missing_queries": int((~self.quality[paid]).sum())}
        result["target_met"] = (result["error"] <= .08 and (boundary is None or boundary <= .25)
             and (island is None or island >= .70) and (r1 is None or r1 >= .85) and (r0 is None or r0 >= .85))
        return result
