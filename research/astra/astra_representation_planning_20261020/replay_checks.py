"""Preselected immutable-state numerical replays, independent of scientific outcomes."""
import argparse
import hashlib
import json
import os
import time
import traceback
import psutil
from coordination import ROOT, Slot, now
from ledger import add_units, claim, finish, Meter, atomic_json, sha256, connection


def main():
    manifest = json.loads((ROOT/"FROZEN_TEST_V1.json").read_text())
    specs = []
    for world in manifest["worlds"][:6]:
        for model in ("existing", "local"):
            for selector in ("h2", "mixture_h1"):
                source = f"test__{world['world_id']}__prefix__{model}__{selector}"
                specs.append({"id": "replay__"+source, "source_unit": source, "phase": "REFERENCE",
                              "family": world["family"], "model": model, "selector": selector, "budget": 33})
    add_units(specs, "REFERENCE")
    with Slot() as slot:
        import numpy as np
        import posterior
        from posterior import GaussianState
        from planner import two_step_at_order, one_step, choose
        from mixture_acquisition import integrated_scores, state_hash, truncate
        rows = []
        for spec in specs:
            slot.check()
            file = ROOT/"results/audits/replays"/(spec["id"]+".json")
            with connection() as c:
                old = c.execute("SELECT status FROM units WHERE id=?", (spec["id"],)).fetchone()[0]
            if old == "COMPLETE":
                rows.append(json.loads(file.read_text()))
                continue
            if old == "FAILED":
                rows.append({"unit": spec["id"], "status": "FAILED_PRESERVED"})
                continue
            selected = claim(spec["id"], os.getpid(), psutil.Process().create_time())
            if selected is None:
                continue
            attempt, _ = selected
            posterior.METER = Meter(attempt, reference=True)
            clock = time.process_time()
            try:
                base = ROOT/"results/paths"/spec["source_unit"]/f"b{spec['budget']:03d}"
                pre = json.loads(base.with_suffix(".pre.json").read_text())
                assert pre["snapshot_file_sha256"] == sha256(base.with_suffix(".npz"))
                with np.load(base.with_suffix(".npz"), allow_pickle=False) as z:
                    s = GaussianState(*(z[k] for k in ("reference_mean", "reference_variance", "candidate_mean",
                        "candidate_covariance", "cross_covariance", "noise_variance")),
                        float(z["availability"]), str(z["source_hash"].item()), tuple(map(int, z["ids"])))
                    if spec["selector"] == "h2":
                        assert s.digest() == pre["snapshot_hash"]
                        forced = pre["details"].get("forced_second_priority") or None
                        vals = {str(order): two_step_at_order(s, order, forced) for order in (65, 129)}
                        reference = vals["129"]
                        baseline = one_step(s)
                        kind = "Gaussian working-posterior GH65/129; same recurrence, an integration refinement rather than an independent posterior reference."
                        extras = {}
                    else:
                        full = {k[len("component_"):]: z[k] for k in z.files if k.startswith("component_")}
                        h = hashlib.sha256((s.digest()+state_hash(full)).encode()).hexdigest()
                        assert h == pre["snapshot_hash"]
                        state, omitted = truncate(full)
                        vals, diags = {}, {}
                        for order in (129, 257):
                            vals[str(order)], diags[str(order)] = integrated_scores(state, order, s.availability)
                        reference = vals["257"]
                        baseline = one_step(s)
                        kind = "Exact retained-component updates with GH129/257 importance integration; not an exact integral or an iid ESS guarantee."
                        extras = {"diagnostics": diags, "omitted_mass": omitted}
                cached = np.array(pre["details"]["scores"])
                tol = 2e-5
                result = {"unit": spec["id"], "status": "COMPLETE_DIAGNOSTIC",
                    "source_unit": spec["source_unit"], "family": spec["family"],
                    "snapshot_hash": pre["snapshot_hash"], "selected": pre["selected"],
                    "cached_scores": cached.tolist(),
                    "refined_scores": {k: v.tolist() for k, v in vals.items()},
                    "moment_one_step_scores": baseline.tolist(),
                    "cached_vs_highest_max_abs": float(np.max(abs(cached-reference))),
                    "refinement_max_abs": float(np.max(abs(list(vals.values())[0]-reference))),
                    "refined_winner_with_ordinary_tie": choose(reference, s.ids, tol)[0],
                    "refined_tie_count": choose(reference, s.ids, tol)[1],
                    "selected_refined_score_gap": float(reference.max()-reference[s.ids.index(pre["selected"])]),
                    "moment_one_step_winner": choose(baseline, s.ids, tol)[0],
                    "interpretation": kind, **extras,
                    "cpu_seconds": time.process_time()-clock,
                    "actual_budget": posterior.METER.actual, "source_sha256": sha256(__file__)}
                atomic_json(file, result)
                finish(spec["id"], attempt, "COMPLETE", file.relative_to(ROOT).as_posix())
                rows.append(result)
            except Exception:
                note = traceback.format_exc()
                finish(spec["id"], attempt, "FAILED", note=note)
                rows.append({"unit": spec["id"], "status": "FAILED_PRESERVED", "error": note})
        result = {"status": "COMPLETE" if len(rows) == 24 and all(r["status"] == "COMPLETE_DIAGNOSTIC" for r in rows)
                  else "INCOMPLETE_DIAGNOSTICS_RETAINED",
                  "utc": now().isoformat(), "states": rows, "expected_states": 24,
                  "source_sha256": sha256(__file__),
                  "test_manifest_sha256": sha256(ROOT/"FROZEN_TEST_V1.json")}
        atomic_json(ROOT/"results/audits/NUMERICAL_REPLAY.json", result)
        print(json.dumps({"status": result["status"], "states": len(rows)}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--threads", type=int, choices=[1], required=True); p.parse_args()
    main()
