"""Public-input / paid-only ask-tell policy. No truth, family, or future outcomes."""
from dataclasses import dataclass
import hashlib
import json
import time
import numpy as np
from scipy.linalg import cho_solve
from scipy.special import logsumexp, ndtr, ndtri
from posterior import Posterior
from planner import plan


def random_order(pool_size, seed, next_budget):
    return np.random.default_rng(np.random.SeedSequence([seed, next_budget, 28371])).permutation(pool_size).tolist()


def loo_anchor(model, paid_ids, observations):
    valid = [i for i, y in zip(paid_ids, observations) if y is not None]
    if not valid:
        return paid_ids[0], []
    logdens, tail = [], []
    for c in model.components:
        precision = np.diag(cho_solve(c.factor, np.eye(len(c.y)), check_finite=False))
        sd = np.sqrt(1 / precision)
        z = c.alpha / np.sqrt(precision)
        logdens.append(-.5*z*z - np.log(sd) - .5*np.log(2*np.pi))
        tail.append(ndtr(z))
    logdens, tail = np.array(logdens), np.array(tail)
    le = np.array([c.log_evidence for c in model.components])[:, None] + np.log(model.prior)[:, None] - logdens
    weight = np.exp(le-logsumexp(le, axis=0, keepdims=True))
    probability = np.sum(weight*tail, axis=0)
    surprise = np.abs(ndtri(np.clip(probability, 1e-10, 1-1e-10)))
    # Deterministic ID tie handling; diagnostic does not insert another likelihood.
    k = min(range(len(valid)), key=lambda k: (-surprise[k], valid[k]))
    return valid[k], [{"id": int(i), "loo_abs_z": float(z)} for i, z in zip(valid, surprise)]


class Policy:
    def __init__(self, x, references, kind, selector, seed, options):
        self.x, self.references = np.asarray(x), np.asarray(references)
        self.model = Posterior(kind, ard_options=options.get("ard_options"))
        self.selector, self.seed, self.options = selector, seed, options
        self.paid, self.observations, self.records = [], [], []
        self.pending = None
        self.fitted_count = -1

    def tell(self, record, startup=False):
        i = int(record["paid_id"])
        assert i not in self.paid, "Duplicate paid ID"
        assert record["cost"] == 1
        if not startup:
            assert self.pending is not None and self.pending["selected"] == i
            assert record["prequery_hash"] == self.pending["snapshot_hash"]
        self.paid.append(i)
        self.observations.append(record["outputs"][0])
        self.records.append(record)
        self.pending = None

    def fit(self):
        if self.fitted_count != len(self.paid):
            self.model.fit(self.x[self.paid], self.observations, self.paid)
            self.fitted_count = len(self.paid)

    def ask(self, remaining):
        assert self.pending is None
        self.fit()
        t = len(self.paid)
        unpaid = np.setdiff1d(np.arange(len(self.x)), self.paid, assume_unique=False)
        current_order = [i for i in random_order(len(self.x), self.seed, t+1) if i in set(unpaid)]
        global_now = (t - self.options["startup"]) % 4 == 3
        if self.selector == "random" or (global_now and self.selector in ("h1", "h2")):
            selected = current_order[0]
            ids, mode, details = [selected], "global_random", {}
        elif self.selector == "maximin":
            distance = np.min(np.sum((self.x[unpaid, None]-self.x[self.paid][None])**2, axis=2), axis=1)
            selected = int(unpaid[np.argmax(distance)])
            ids, mode, details = [selected], "maximin", {}
        else:
            pm, pv, pp = self.model.predict(self.x)
            straddle = 1.96*np.sqrt(pv)-abs(pm)
            ranking = sorted(unpaid, key=lambda i: (-straddle[i], i))
            if self.selector == "straddle":
                selected = int(ranking[0])
                ids, mode, details = [selected], "full_pool_straddle", {"full_pool_candidates": len(unpaid)}
            else:
                anchor, loo = loo_anchor(self.model, self.paid, self.observations)
                neighbours = sorted(unpaid, key=lambda i: (float(np.sum((self.x[i]-self.x[anchor])**2)), i))
                # Exactly common access for h1/h2. Two random priorities guarantee
                # the next scheduled exploration action remains available after any first.
                next_order = [i for i in random_order(len(self.x), self.seed, t+2) if i in set(unpaid)]
                ids = []
                for source, n in ((next_order, 2), (ranking, 2), (neighbours, 2)):
                    for i in source:
                        if i not in ids:
                            ids.append(int(i))
                            n -= 1
                            if n == 0:
                                break
                snapshot = self.model.snapshot(self.x[ids], self.references, ids)
                next_global = (t+1-self.options["startup"]) % 4 == 3
                horizon = 2 if self.selector == "h2" and remaining >= 2 else 1
                selected, details = plan(snapshot, horizon,
                       orders=tuple(self.options["gh_orders"]), score_tolerance=self.options["score_tolerance"],
                       tie_tolerance=self.options["tie_tolerance"], forced_second=next_order[:2] if next_global else None)
                mode = "risk_h" + str(horizon)
                details.update(anchor_id=int(anchor), loo=loo, next_step_forced_global=next_global,
                               forced_second_priority=next_order[:2] if next_global else [])
        if self.selector not in ("h1", "h2") or mode == "global_random":
            snapshot = self.model.snapshot(self.x[ids], self.references, ids)
        self.pending = {"selected": int(selected), "ids": list(map(int, ids)), "mode": mode,
                        "paid_before": t, "snapshot_hash": snapshot.digest(),
                        "model_hash": self.model.model_hash, "details": details,
                        "variance_type": "latent covariance; independent observation noise added exactly once",
                        "model_summary": self.model.local_summary()}
        return int(selected), snapshot, self.pending

    def export(self):
        return {"paid": self.paid, "observations": self.observations, "records": self.records,
                "ard_theta": None if self.model.ard_theta is None else self.model.ard_theta.tolist(),
                "ard_last_budget": self.model.ard_last_budget, "optimizer_log": self.model.optimizer_log}

    def restore(self, state):
        self.paid, self.observations, self.records = state["paid"], state["observations"], state["records"]
        assert len(set(self.paid)) == len(self.paid)
        self.model.ard_theta = None if state["ard_theta"] is None else np.array(state["ard_theta"])
        self.model.ard_last_budget = state["ard_last_budget"]
        self.model.optimizer_log = state["optimizer_log"]
        self.fitted_count = -1
