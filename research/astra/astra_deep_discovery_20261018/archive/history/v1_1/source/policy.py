"""Model-independent ask/tell selector; public features and paid data only."""
from dataclasses import dataclass
import math
import statistics
import numpy as np
from acquisition import sur_scores, baseline_scores, truvar_scores, vtl_scores


@dataclass(frozen=True)
class PaidObservation:
    paid_id: int
    values: tuple
    quality: tuple
    cost: float = 1.
    canonical_label: int | None = None
    quality_note: str = ""


class Policy:
    def __init__(self, features, startup, mode, seed):
        self.x = np.array(features, float, copy=True)
        if self.x.ndim != 2 or not np.isfinite(self.x).all():
            raise ValueError("finite public feature matrix required")
        self.paid = set(startup)
        if mode not in ('random', 'maximin', 'maxvar', 'straddle', 'margin', 'truvar',
                        'multiscale_tree', 'ca_smart_adapt', 'sur_global', 'sur_primary',
                        'regional', 'ungated_local', 'blind_local', 'vtl'):
            raise ValueError('unregistered selector')
        self.mode = mode
        self.order = np.random.default_rng(seed).permutation(len(self.x))
        self.step = 0
        self.pending = None
        self.episode = None
        self.residuals = []
        self.events = []
        self.eta = 1.

    def _nearest(self, options, anchor):
        d = np.linalg.norm(self.x[options]-self.x[anchor], axis=1)
        return int(options[np.lexsort((options, d))[0]])

    def _maximin(self, options):
        distance = np.linalg.norm(self.x[options, None]-self.x[sorted(self.paid)][None], axis=2).min(1)
        return int(options[np.argmax(distance)])

    def _tree_choice(self, p, options):
        # Explicit finite-pool adaptation: no arbitrary centers or replicated calls.
        leaves = [(options, 0)]
        best = None
        while leaves:
            ids, depth = leaves.pop()
            if not len(ids):
                continue
            center = self.x[ids].mean(0)
            j = int(ids[np.argmin(np.linalg.norm(self.x[ids]-center, axis=1))])
            radius = float(np.linalg.norm(self.x[ids]-self.x[j], axis=1).max())
            variation = min(2., 3*radius/.45)
            sd = math.sqrt(max(p.latent_cov[j, 0, 0], 1e-12))
            low, high = p.mean[j, 0]-3*sd-variation, p.mean[j, 0]+3*sd+variation
            if low > 0 or high < 0:
                continue
            if len(ids) > 8 and depth < 16 and 3*sd < variation:
                axis = int(np.argmax(np.ptp(self.x[ids], axis=0)))
                ordered = ids[np.lexsort((ids, self.x[ids, axis]))]
                middle = len(ordered)//2
                leaves.extend([(ordered[:middle], depth+1), (ordered[middle:], depth+1)])
            else:
                candidate = (max(high, -low), -j, j)
                best = candidate if best is None or candidate > best else best
        return best[2] if best else self._maximin(options)

    def ask(self, p):
        if self.pending is not None or p.paid_count != len(self.paid):
            raise RuntimeError("pending query or stale posterior")
        ids = np.array([i for i in range(len(self.x)) if i not in self.paid], int)
        if not len(ids):
            raise StopIteration
        mode = self.mode
        regional = mode in ("regional", "ungated_local", "blind_local")
        schedule = regional or mode in ("sur_global", "sur_primary", "vtl")
        scores, reason = None, mode
        if self.episode and self.step-self.episode["born"] >= 12:
            self.episode = None
        if mode == "random" or (schedule and self.step % 4 == 0):
            i = next(int(k) for k in self.order if k not in self.paid)
            reason = "global_random"
        elif mode == "maximin":
            i = self._maximin(ids)
        elif mode == "multiscale_tree":
            i = self._tree_choice(p, ids)
        elif mode in ("maxvar", "straddle", "margin"):
            scores = baseline_scores(p, mode)
            i = int(ids[np.argmax(scores[ids])])
        elif mode == "truvar":
            unresolved = np.abs(p.ref_mean) <= 3*np.sqrt(p.ref_variance)
            scores, self.eta = truvar_scores(p, self.eta, unresolved)
            i = int(ids[np.argmax(scores[ids])])
        elif mode == "ca_smart_adapt":
            if self.episode and self.step % 2:
                i = self._nearest(ids, self.episode["anchor"])
                reason = "local_nearest"
            else:
                i = self._maximin(ids)
                reason = "global_maximin"
        else:
            scores = vtl_scores(p) if mode == 'vtl' else sur_scores(p, primary_only=mode == "sur_primary")
            local = []
            if regional and self.step % 4 in (1, 3) and self.episode:
                e = self.episode
                local = ids[np.linalg.norm(self.x[ids]-self.x[e["anchor"]], axis=1) <= e["radius"]]
            if len(local):
                e = self.episode
                if mode == "blind_local" or e["used"] == 0:
                    i = self._nearest(local, e["anchor"])
                    reason = "local_verify" if mode != "blind_local" else "local_nearest"
                else:
                    i = int(local[np.argmax(scores[local])]); reason = "local_sur"
            else:
                i = int(ids[np.argmax(scores[ids])]); reason = "global_sur"
        if scores is not None:
            ordered = np.sort(scores[ids])
            gap = float(ordered[-1]-ordered[-2]) if len(ordered) > 1 else None
            top = float(ordered[-1])
        else:
            gap = top = None
        choice = {"paid_id": i, "reason": reason, "prequery_hash": p.digest(),
            "model_hash": p.model_hash, "paid_before": len(self.paid),
            "mean": p.mean[i].tolist(), "latent_cov": p.latent_cov[i].tolist(),
            "noise_cov": p.noise_cov[i].tolist(), "variance_kind": "latent plus separate observation noise",
            "model_weights": p.weights.tolist(), "best_score": top, "top_two_gap": gap,
            "near_tie": gap is not None and gap <= max(1e-10, 1e-3*abs(top))}
        self.pending = (choice, p)
        return choice

    def tell(self, observation):
        if not self.pending or observation.paid_id != self.pending[0]["paid_id"]:
            raise ValueError("unique pending paid ID required")
        if observation.cost <= 0 or not math.isfinite(observation.cost):
            raise ValueError("explicit positive paid cost required")
        choice, p = self.pending
        i = observation.paid_id
        self.paid.add(i)
        valid = bool(observation.quality[0] and observation.values[0] is not None
                     and math.isfinite(observation.values[0]))
        scale = max(1., statistics.median(self.residuals[-8:])/.6744897501960817) if len(self.residuals) >= 4 else 1.
        event = {**choice, "values": list(observation.values), "quality": list(observation.quality),
                 "cost": observation.cost, "canonical_label": observation.canonical_label,
                 "quality_note": observation.quality_note, "scale_before": scale,
                 "triggered": False, "confirmed_now": False, "ended": None}
        if not valid:
            self.episode = None; event["ended"] = "quality"
        else:
            z = float((observation.values[0]-p.mean[i, 0])/math.sqrt(max(p.latent_cov[i, 0, 0]+p.noise_cov[i, 0, 0], 1e-12)))
            event["raw_z"] = z
            local = choice["reason"].startswith("local")
            if local and self.episode:
                e = self.episode; e["used"] += 1
                ref = e["reference"]
                rz = float((observation.values[0]-ref.mean[i, 0]) /
                    math.sqrt(max(ref.latent_cov[i, 0, 0]+ref.noise_cov[i, 0, 0], 1e-12))/e["scale"])
                event["reference_z"] = rz
                if not e["confirmed"] and rz*e["sign"] >= 1.5:
                    e["confirmed"] = True; event["confirmed_now"] = True
                if e["used"] >= e["limit"]:
                    self.episode = None; event["ended"] = "quota"
                elif e["used"] >= 2 and not e["confirmed"] and self.mode != "ungated_local":
                    self.episode = None; event["ended"] = "no_corroboration"
            elif not local:
                threshold = 1.96 if self.mode == "ca_smart_adapt" else 2.5
                trigger = abs(z)/scale >= threshold and scale <= 2
                if self.mode == "ungated_local":
                    trigger = True
                if scale > 2 and self.mode != "ungated_local":
                    self.episode = None
                eligible = self.mode in ("regional", "blind_local", "ungated_local", "ca_smart_adapt")
                if eligible and trigger and self.episode is None:
                    distances = np.sort(np.linalg.norm(self.x-self.x[i], axis=1))
                    radius = float(np.clip(distances[min(12, len(distances)-1)], .15, .45))
                    self.episode = {"anchor": i, "radius": radius, "reference": p,
                        "born": self.step+1, "used": 0, "limit": 3 if self.mode == "ca_smart_adapt" else 6,
                        "confirmed": self.mode == "ungated_local", "sign": 1 if z >= 0 else -1, "scale": scale}
                    event["triggered"] = True
                self.residuals.append(abs(z))
        self.events.append(event)
        self.pending = None; self.step += 1
        return event


def feature_start(x, count, seed):
    rng = np.random.default_rng(seed)
    paid = [int(rng.integers(len(x)))]
    d = np.linalg.norm(x-x[paid[0]], axis=1)
    while len(paid) < count:
        d[paid] = -1
        j = int(np.argmax(d)); paid.append(j)
        d = np.minimum(d, np.linalg.norm(x-x[j], axis=1))
    return paid
