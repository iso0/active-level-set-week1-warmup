"""Independent accounting and adapter fixtures; no scientific model fits."""
import argparse
import importlib.util
import json
import os
import psutil
from coordination import ROOT, Slot, now
from ledger import Meter, add_units, claim, finish, atomic_json, sha256


def run():
    import numpy as np
    from posterior import GaussianState
    from planner import plan
    from analyze_test import _missing_bounds, clean
    module_spec = importlib.util.spec_from_file_location("review_adapter", ROOT/"handoff/adapter.py")
    mod = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(mod)
    a = np.array([[.4, .1, .2, 0., .2], [.1, .5, .1, .3, 0.],
                  [.2, .1, .6, .2, .1], [0., .3, .2, .5, .2], [.2, 0., .1, .2, .7]])
    assert np.linalg.eigvalsh(a).min() > 0
    s = GaussianState(np.array([.1, -.2]), np.diag(a)[:2], np.array([.0, .1, -.1]),
                      a[2:, 2:], a[:2, 2:], np.array([.01, .04, .1]), .8, "independent_adapter_fixture", (8, 9, 10))
    adapter = mod.PaidRiskAdapter()
    ticket = adapter.ask(s, remaining=1, horizon=2)
    assert ticket["paid_id"] == plan(s, 1, score_tolerance=5e-5)[0]
    restored = mod.PaidRiskAdapter.restore(adapter.export())
    assert restored.export() == adapter.export()
    record = {"paid_id": ticket["paid_id"], "prequery_hash": ticket["prequery_hash"], "cost": 1.,
              "outputs": [None, 2.75], "quality": ["missing", "valid"]}
    rejected = []
    for name, wrong in (
        ("stale_hash", {**record, "prequery_hash": "wrong"}),
        ("wrong_id", {**record, "paid_id": 999}),
        ("free_missing_query", {**record, "cost": 0.}),
        ("incomplete_quality", {**record, "quality": ["missing"]}),
    ):
        try:
            restored.tell(wrong)
            raise AssertionError("Invalid record accepted: "+name)
        except ValueError:
            rejected.append(name)
    restored.tell(record)
    assert len(restored.records) == 1 and restored.records[0]["outputs"] == [None, 2.75]
    try:
        restored.ask(s, remaining=2)
        raise AssertionError("Duplicate paid candidate allowed")
    except ValueError:
        rejected.append("duplicate_paid_candidate")
    manifest = {"family_counts": {"smooth": 1}, "worlds": [{"world_id": "w", "family": "smooth"}]}
    values = [("existing__h1", .3), ("existing__h2", .2), ("local__h1", .1), ("local__h2", .05)]
    lookup = {("prefix", "w", arm): {"final": {"error": value}} for arm, value in values}
    exact = _missing_bounds(manifest, lookup, {}, "error__R", [-.5, -.5, .5, .5])
    assert abs(exact["lower"]+.175) < 1e-12 and exact["lower"] == exact["upper"]
    del lookup["prefix", "w", "existing__h2"]
    interval = _missing_bounds(manifest, lookup, {}, "error__R", [-.5, -.5, .5, .5])
    assert abs(interval["lower"]+.575) < 1e-12 and abs(interval["upper"]+.075) < 1e-12
    assert clean({"undefined": np.nan, "array": np.array([1., np.inf])}) == {"undefined": None, "array": [1., None]}
    return {"status": "PASS_CONTRACT_AND_ACCOUNTING_FIXTURES", "utc": now().isoformat(),
            "rejected_invalid_contracts": rejected, "horizon_one_limiting_case": True,
            "pending_ticket_round_trip": True, "missing_channel_retains_cost_and_other_output": True,
            "complete_case_representation_contrast": exact, "missing_case_bounds": interval,
            "scope": "Software/accounting validation only; no scientific efficacy evidence or new GP fit.",
            "source_sha256": sha256(__file__), "adapter_sha256": sha256(ROOT/"handoff/adapter.py")}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--threads", type=int, choices=[1], required=True); p.parse_args()
    unit = {"id": "reference_finishing_contracts", "kind": "software_and_accounting_reference"}
    add_units([unit], "REFERENCE")
    with Slot():
        chosen = claim(unit["id"], os.getpid(), psutil.Process().create_time())
        if chosen:
            attempt, _ = chosen
            import posterior
            posterior.METER = Meter(attempt, reference=True)
            try:
                result = run()
                result["actual_budget"] = posterior.METER.actual
                atomic_json(ROOT/"results/audits/FINISHING_CONTRACT_CHECKS.json", result)
                finish(unit["id"], attempt, "COMPLETE", "results/audits/FINISHING_CONTRACT_CHECKS.json")
                print(json.dumps(result, indent=2))
            except Exception as exc:
                finish(unit["id"], attempt, "FAILED", note=repr(exc))
                raise
