"""Backend-neutral pending-ticket wrapper; no model fitting or evaluator access."""
from dataclasses import asdict
import hashlib
import json
from planner import plan


class PaidRiskAdapter:
    def __init__(self, paid_records=()):
        self.records = [dict(r) for r in paid_records]
        self.paid = {int(r["paid_id"]) for r in self.records}
        if len(self.paid) != len(self.records):
            raise ValueError("Duplicate paid ID in startup/history")
        self.pending = None

    def ask(self, state, remaining, horizon=2, forced_second=None):
        if self.pending is not None:
            raise ValueError("Resolve the existing paid ticket before asking again")
        if remaining < 1 or horizon not in (1, 2):
            raise ValueError("Need a positive paid budget and horizon one or two")
        if any(i in self.paid for i in state.ids):
            raise ValueError("Candidate already paid")
        chosen, diagnostic = plan(state, min(horizon, remaining),
            orders=(9, 17, 33, 65), score_tolerance=5e-5, tie_tolerance=2e-5,
            forced_second=forced_second)
        self.pending = {
            "paid_id": int(chosen), "prequery_hash": state.digest(),
            "posterior_source_hash": state.source_hash,
            "variance_contract": "latent covariance plus independent observation noise exactly once",
            "diagnostic": diagnostic, "declared_query_cost": 1.0,
        }
        return dict(self.pending)

    def tell(self, observation):
        if self.pending is None:
            raise ValueError("No pending paid query")
        record = dict(observation)
        if record["paid_id"] != self.pending["paid_id"] or record["paid_id"] in self.paid:
            raise ValueError("Wrong or duplicate paid ID")
        if record["prequery_hash"] != self.pending["prequery_hash"]:
            raise ValueError("Stale prequery posterior/hash")
        if record.get("cost") != 1 or not isinstance(record.get("outputs"), list):
            raise ValueError("One paid run and its complete available-output vector are required")
        if len(record["outputs"]) != len(record.get("quality", [])):
            raise ValueError("Quality is required for every available/missing channel")
        self.records.append(record)
        self.paid.add(int(record["paid_id"]))
        self.pending = None
        return record

    def export(self):
        return {"records": self.records, "pending": self.pending}

    @classmethod
    def restore(cls, state):
        restored = cls(state["records"])
        restored.pending = state["pending"]
        return restored
