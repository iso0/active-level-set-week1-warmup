"""Numerical-only DEV snapshot audit, with no scientific endpoint-based selection."""
import argparse
import json
import math
import time
from coordination import ROOT, Slot
from ledger import Meter, add_units, claim, finish, atomic_json
import os
import psutil


def run():
    import numpy as np
    from scipy.integrate import quad
    from scipy.special import ndtr
    import posterior
    from posterior import GaussianState
    from planner import one_step, condition, two_step_at_order
    rows, summaries = [], []
    for file in (ROOT/"results/paths").glob("dev_v1*/*.pre.json"):
        r = json.loads(file.read_text())
        if r["mode"] == "risk_h2":
            d = r["details"]
            summaries.append({"delta": d["integration_delta"], "resolution": d["resolution_diagnostic"],
                              "deltas": d["integration_deltas"], "order": d["order"],
                              "fallback": d["numerical_ambiguity"]})
    for family in ("smooth", "island_small", "rotated", "corrupt_correlated"):
        for model in ("existing", "local"):
            path = ROOT/f"results/paths/dev_v1__{family}__{model}__h2/b009"
            info = json.loads(path.with_suffix(".pre.json").read_text())
            with np.load(path.with_suffix(".npz"), allow_pickle=False) as a:
                s = GaussianState(a["reference_mean"], a["reference_variance"], a["candidate_mean"],
                     a["candidate_covariance"], a["cross_covariance"], a["noise_variance"],
                     float(a["availability"]), str(a["source_hash"]), tuple(map(int, a["ids"])))
            first = one_step(s)
            start = time.process_time()
            values, errors, evaluations = [], [], []
            for i in range(len(s.ids)):
                sd = math.sqrt(s.candidate_covariance[i,i]+s.noise_variance[i])
                def integrand(z):
                    posterior.count("planning_states")
                    cs = condition(s, i, s.candidate_mean[i]+sd*z)
                    return math.exp(-z*z/2)/math.sqrt(2*math.pi)*float(np.max(one_step(cs)))
                value, error, details = quad(integrand, -7, 7, epsabs=2e-7, epsrel=1e-5, limit=20, full_output=1)[:3]
                missing = max(one_step(condition(s, i, 0., observed=False)))
                values.append(float(first[i]+s.availability*value+(1-s.availability)*missing))
                errors.append(float(s.availability*error+2*ndtr(-7)*.5))
                evaluations.append(details["neval"])
            quad_cpu = time.process_time()-start
            actual = np.array(info["details"]["scores"])
            order65 = two_step_at_order(s, 65)
            rows.append({"family": family, "model": model, "ids": s.ids, "snapshot_hash": s.digest(),
                  "h1_scores": first.tolist(), "cached_scores": actual.tolist(), "quad_scores": values,
                  "quad_errors": errors, "quad_evaluations": evaluations, "quad_cpu": quad_cpu,
                  "GH65_scores": order65.tolist(),
                  "cached_max_abs_error": float(max(abs(actual-values))),
                  "GH65_max_abs_error": float(max(abs(order65-values))),
                  "quad_winner": int(s.ids[int(np.argmax(values))]),
                  "h1_winner": int(s.ids[int(np.argmax(first))]),
                  "quad_tied_ids_2e_5": [int(i) for i,v in zip(s.ids, values) if max(values)-v <= .00002]})
    return {"status": "COMPLETE_NUMERICAL_DIAGNOSIS", "endpoint_access": False,
            "paid_prefixes": rows, "all_saved_h2_numerics": summaries,
            "scope": "Gaussian working posterior only; no scientific outcome or model fitting."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--threads", choices=[1], type=int, required=True); parser.parse_args()
    unit = {"id": "reference_dev_quadrature_v1", "kind": "reference"}
    add_units([unit], "REFERENCE")
    if not (ROOT/"results/DEV_NUMERICAL_AUDIT.json").exists():
        with Slot():
            selected = claim(unit["id"], os.getpid(), psutil.Process().create_time())
            if selected:
                attempt, _ = selected
                import posterior
                posterior.METER = Meter(attempt, reference=True)
                try:
                    result = run()
                    result["actual_budget"] = posterior.METER.actual
                    atomic_json(ROOT/"results/DEV_NUMERICAL_AUDIT.json", result)
                    finish(unit["id"], attempt, "COMPLETE", "results/DEV_NUMERICAL_AUDIT.json")
                    print(json.dumps(result["paid_prefixes"], indent=2))
                except Exception as exc:
                    finish(unit["id"], attempt, "FAILED", note=repr(exc)); raise
