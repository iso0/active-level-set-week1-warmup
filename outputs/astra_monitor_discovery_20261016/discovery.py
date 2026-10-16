"""Cheap, paid-observation-only discovery episodes. No fit, file I/O or oracle.

All candidate coordinates must be scaled by PREDECLARED feature bounds. Prediction
moments must be produced before the selected outcome is revealed. A 'corroborated'
episode is a local model discrepancy, never a certified physical regime.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
import random
import statistics


@dataclass(frozen=True)
class Config:
    radius: float = 0.25
    trigger_z: float = 2.5
    confirmation_z: float = 1.5
    max_local: int = 4
    confirmation_attempts: int = 2
    episode_lifetime: int = 8
    calibration_window: int = 8
    calibration_minimum: int = 4
    calibration_alert: float = 2.0
    straddle_beta: float = 1.96
    threshold: float = 0.0
    sd_floor: float = 1e-8


@dataclass(frozen=True)
class Predictions:
    """ONLY posterior moments; no actual unpaid response or evaluator masks.

    latent_sd excludes observation noise. noise_sd is predictive observation noise
    known/estimated using paid data, not inferred from the outcome being queried.
    aux_variance is optional, already divided by a fixed/prior target scale squared.
    """
    model_id: str
    paid_count: int
    mean: tuple[float, ...]
    latent_sd: tuple[float, ...]
    noise_sd: tuple[float, ...]
    aux_variance: tuple[float, ...] | None = None

    def __post_init__(self):
        # Copy lists/arrays as well: frozen dataclass alone would not prevent mutation.
        for name in ("mean", "latent_sd", "noise_sd", "aux_variance"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, tuple(float(v) for v in value))

    def digest(self):
        return hashlib.sha256(json.dumps(self.__dict__, sort_keys=True,
                                        allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class Observation:
    index: int
    value: float | None
    quality_ok: bool
    quality_note: str
    canonical_label: int | None = None  # retained by caller; NOT a trigger here


@dataclass(frozen=True)
class Choice:
    index: int
    reason: str
    posterior_hash: str
    model_id: str
    paid_before: int


@dataclass
class Episode:
    anchor: int
    sign: int
    reference: Predictions  # entire frozen posterior BEFORE seeing the anchor
    scale: float
    born: int
    local_used: int = 0
    corroborated: bool = False


def distance(a, b):
    return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))


class SurpriseLocalDiscovery:
    """ask(posterior) -> Choice; pay one run; tell(Observation) -> audit event.

    Modes: surprise, straddle_global (episode ablation), straddle, margin, random,
    primary_variance, multi_variance. All except random consume the SAME moments.
    Surprise schedule per four post-startup queries: global, local, base, local.
    Empty/expired local slots revert to straddle. No future-outcome integration.
    """
    MODES = {"surprise", "straddle_global", "straddle", "margin", "random",
             "primary_variance", "multi_variance"}

    def __init__(self, x4, paid_indices=(), *, seed=0, mode="surprise", config=None):
        if mode not in self.MODES:
            raise ValueError("unknown acquisition")
        self.x = tuple(tuple(float(v) for v in row) for row in x4)
        if not self.x or any(len(row) != 4 or any(not math.isfinite(v) or
                not 0 <= v <= 1 for v in row) for row in self.x):
            raise ValueError("require finite, pre-scaled four-dimensional features")
        self.cfg = config or Config()
        if not (0 < self.cfg.radius <= 2 and self.cfg.max_local > 0 and
                0 < self.cfg.confirmation_attempts <= self.cfg.max_local):
            raise ValueError("invalid episode limits")
        self.mode = mode
        paid_list = list(paid_indices)
        self.paid = set(paid_list)
        if len(self.paid) != len(paid_list) or any(i not in range(len(self.x)) for i in self.paid):
            raise ValueError("invalid startup indices")
        self.initial_n = len(self.paid)
        self.sequence = 0
        self.episode = None
        self.pending = None
        self.global_residuals = []
        self.events = []
        self.global_order = list(range(len(self.x)))
        random.Random(seed).shuffle(self.global_order)

    def _validate(self, p):
        n = len(self.x)
        if p.paid_count != len(self.paid) or not p.model_id:
            raise ValueError("stale posterior or absent model identity")
        for name in ("mean", "latent_sd", "noise_sd", "aux_variance"):
            a = getattr(p, name)
            if a is None:
                continue
            if len(a) != n or any(not math.isfinite(v) for v in a):
                raise ValueError("invalid prediction array")
            if name != "mean" and any(v < 0 for v in a):
                raise ValueError("negative uncertainty")
        if self.mode == "multi_variance" and p.aux_variance is None:
            raise ValueError("multi_variance requires posterior auxiliary variance")

    def _score(self, p, i, base=None):
        base = base or self.mode
        m, s = p.mean[i], p.latent_sd[i]
        if base == "margin":
            z = (m-self.cfg.threshold)/max(s, self.cfg.sd_floor)
            prob = .5 * (1 + math.erf(z/math.sqrt(2)))
            return -abs(prob-.5)
        if base == "primary_variance":
            return s*s
        if base == "multi_variance":
            return .5 * (s*s + p.aux_variance[i])
        return self.cfg.straddle_beta*s - abs(m-self.cfg.threshold)

    def ask(self, p: Predictions) -> Choice:
        if self.pending is not None:
            raise RuntimeError("tell the pending paid observation before another ask")
        self._validate(p)
        candidates = [i for i in range(len(self.x)) if i not in self.paid]
        if not candidates:
            raise StopIteration("pool exhausted")
        if self.episode and self.sequence-self.episode.born >= self.cfg.episode_lifetime:
            self.episode = None
        slot = self.sequence % 4
        global_slot = self.mode == "random" or (
            self.mode in {"surprise", "straddle_global"} and slot == 0)
        local = []
        if self.mode == "surprise" and self.episode and slot in (1, 3):
            local = [i for i in candidates if distance(self.x[i], self.x[self.episode.anchor])
                     <= self.cfg.radius]
            if not local:
                self.episode = None
        if global_slot:
            i = next(j for j in self.global_order if j not in self.paid)
            reason = "global_random"
        elif local and not self.episode.corroborated:
            i = min(local, key=lambda j: (distance(self.x[j], self.x[self.episode.anchor]), j))
            reason = "local_verify"
        elif local:
            # Simple local boundary learning; physical proximity only bounds the set.
            i = max(local, key=lambda j: (self._score(p, j, "straddle"), -j))
            reason = "local_boundary"
        else:
            i = max(candidates, key=lambda j: (self._score(p, j), -j))
            reason = "global_" + ("straddle" if self.mode in {"surprise", "straddle_global"}
                                    else self.mode)
        choice = Choice(i, reason, p.digest(), p.model_id, len(self.paid))
        self.pending = (choice, p)
        return choice

    def _scale(self):
        z = self.global_residuals[-self.cfg.calibration_window:]
        if len(z) < self.cfg.calibration_minimum:
            return 1.0, False
        scale = max(1.0, statistics.median(z)/0.6744897501960817)
        return scale, scale > self.cfg.calibration_alert

    def tell(self, obs: Observation):
        if self.pending is None or obs.index != self.pending[0].index:
            raise ValueError("observation must match the unique pending query")
        if obs.canonical_label not in (None, 0, 1):
            raise ValueError("canonical labels must be 0/1 or unavailable")
        choice, p = self.pending
        i = obs.index
        # A paid run stays paid even if its primary channel is invalid or absent.
        self.paid.add(i)
        scale, health_alert = self._scale()  # strictly BEFORE the new residual
        valid = obs.quality_ok and obs.value is not None and math.isfinite(obs.value)
        event = {**choice.__dict__, "value": obs.value if valid else None,
                 "quality_ok": bool(valid), "quality_note": obs.quality_note,
                 "canonical_label": obs.canonical_label, "scale_before": scale,
                 "calibration_alert_before": health_alert, "triggered": False,
                 "corroborated_now": False, "episode_ended": None}
        if not valid:
            event["episode_ended"] = "quality_review" if self.episode else None
            self.episode = None
        else:
            sd = max(math.hypot(p.latent_sd[i], p.noise_sd[i]), self.cfg.sd_floor)
            z = (obs.value-p.mean[i])/sd
            event.update(raw_z=z, calibrated_z=z/scale)
            if choice.reason.startswith("local_") and self.episode:
                e = self.episode
                refsd = max(math.hypot(e.reference.latent_sd[i], e.reference.noise_sd[i]),
                            self.cfg.sd_floor)
                rz = (obs.value-e.reference.mean[i])/(refsd*e.scale)
                e.local_used += 1
                if not e.corroborated and e.sign*rz >= self.cfg.confirmation_z:
                    e.corroborated = True
                    event["corroborated_now"] = True
                event.update(anchor=e.anchor, reference_z=rz, local_used=e.local_used)
                if e.local_used >= self.cfg.max_local:
                    event["episode_ended"] = "local_quota"
                    self.episode = None
                elif not e.corroborated and e.local_used >= self.cfg.confirmation_attempts:
                    event["episode_ended"] = "no_local_corroboration"
                    self.episode = None
            elif self.mode == "surprise":
                # Only global queries can start episodes; no self-reinforcing reanchors.
                if health_alert:
                    if self.episode:
                        event["episode_ended"] = "calibration_review"
                    self.episode = None
                elif self.episode is None and abs(z/scale) >= self.cfg.trigger_z:
                    self.episode = Episode(i, 1 if z > 0 else -1, p, scale, self.sequence+1)
                    event["triggered"] = True
                self.global_residuals.append(abs(z))
        self.events.append(event)
        self.pending = None
        self.sequence += 1
        return event


def maximin_start(x4, n, seed):
    """Feature-only deterministic continuation of a random initial feature index."""
    if not 0 < n <= len(x4):
        raise ValueError("bad startup size")
    chosen = [random.Random(seed).randrange(len(x4))]
    remaining = set(range(len(x4))) - set(chosen)
    minimum = [distance(row, x4[chosen[0]]) for row in x4]
    while len(chosen) < n:
        j = max(remaining, key=lambda i: (minimum[i], -i))
        chosen.append(j)
        remaining.remove(j)
        for i in remaining:
            minimum[i] = min(minimum[i], distance(x4[i], x4[j]))
    return chosen
