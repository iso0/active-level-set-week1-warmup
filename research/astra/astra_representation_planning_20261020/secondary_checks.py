"""Small-mixture, paid-only determinism and reference-cloud diagnostics."""
import argparse
import json
import os
import time
from coordination import ROOT, Slot
from ledger import Meter, add_units, claim, finish, atomic_json
import psutil


def run():
    import numpy as np
    from numpy.polynomial.hermite import hermgauss
    from scipy.special import ndtr, logsumexp
    from scipy.stats import qmc
    import posterior
    from posterior import GaussianState, Posterior
    from planner import one_step, two_step_at_order
    from policy import Policy
    from worlds import World

    result = {}
    # Independent finite mixture implementation: different code path from
    # posterior.py and planner.py, exact Gaussian component conditioning.
    rng = np.random.default_rng(620202)
    components, reference_count, candidate_count = 2, 3, 3
    dimensions = reference_count+candidate_count
    matrices = rng.normal(size=(components, dimensions, dimensions))
    covariance = matrices @ matrices.transpose(0, 2, 1)/20 + np.eye(dimensions)[None]*.06
    means = rng.normal(0, .35, (components, dimensions))
    weights = np.array([.55, .45])
    noise = np.array([[.01, .03, .02], [.08, .02, .05]])
    state = (weights, means, covariance, noise)

    def charge(n):
        posterior.METER.charge("planning_states", n)
        posterior.COUNTERS["planning_states"] += n

    def mixture_risk(s):
        w, m, c, n = s
        p = w @ ndtr(m[:, :reference_count]/np.sqrt(np.diagonal(c, axis1=1, axis2=2)[:, :reference_count]))
        return float(np.mean(np.minimum(p, 1-p)))

    def conditioned(s, i, y):
        w, m, c, noise = s
        idx = reference_count+i
        v = c[:, idx, idx]+noise[:, i]
        logw = np.log(np.maximum(w, 1e-300))-.5*((y-m[:, idx])**2/v+np.log(2*np.pi*v))
        wn = np.exp(logw-logsumexp(logw))
        mn = m+c[:, :, idx]*(y-m[:, idx])[:, None]/v[:, None]
        cn = c-np.einsum("ci,cj,c->cij", c[:, :, idx], c[:, idx, :], 1/v)
        keep = [j for j in range(m.shape[1]) if j != idx]
        return wn, mn[:, keep], cn[:, keep][:, :, keep], np.delete(noise, i, axis=1)

    def expected_risk_after_one(s, i, order):
        w, m, c, noise = s
        nodes, gw = hermgauss(order)
        idx = reference_count+i
        v = c[:, idx, idx]+noise[:, i]
        samples = (m[:, idx, None]+np.sqrt(2*v[:, None])*nodes).ravel()
        sample_weights = (w[:, None]*gw[None]/np.sqrt(np.pi)).ravel()
        logw = np.log(np.maximum(w[:, None], 1e-300))-.5*((samples[None]-m[:, idx, None])**2/v[:, None]+np.log(2*np.pi*v[:, None]))
        postw = np.exp(logw-logsumexp(logw, axis=0, keepdims=True))
        rm = m[:, :reference_count, None] + c[:, :reference_count, idx, None]*(samples[None, None]-m[:, idx, None, None])/v[:, None, None]
        rv = np.diagonal(c, axis1=1, axis2=2)[:, :reference_count]-c[:, :reference_count, idx]**2/v[:, None]
        probs = np.einsum("cs,crs->rs", postw, ndtr(rm/np.sqrt(rv[:, :, None])))
        charge(len(samples))
        return float(np.mean(np.minimum(probs, 1-probs), axis=0) @ sample_weights)

    actual_risk = mixture_risk(state)
    exact = {}
    for order in (9, 17, 33, 65):
        nodes, gw = hermgauss(order)
        one, two = [], []
        for i in range(candidate_count):
            one.append(actual_risk-expected_risk_after_one(state, i, order))
            total = 0.
            for c in range(components):
                v = covariance[c, reference_count+i, reference_count+i]+noise[c, i]
                for z, probability in zip(nodes*np.sqrt(2), gw/np.sqrt(np.pi)):
                    charge(1)
                    updated = conditioned(state, i, means[c, reference_count+i]+np.sqrt(v)*z)
                    total += weights[c]*probability*min(expected_risk_after_one(updated, j, order)
                                                       for j in range(candidate_count-1))
            two.append(actual_risk-total)
        exact[str(order)] = {"one": one, "two": two}
    mm = weights @ means
    cc = np.einsum("c,cij->ij", weights, covariance)+np.einsum("c,ci,cj->ij", weights, means, means)-np.outer(mm, mm)
    gs = GaussianState(mm[:reference_count], np.diag(cc)[:reference_count], mm[reference_count:],
              cc[reference_count:, reference_count:], cc[:reference_count, reference_count:],
              weights@noise, 1., "independent_mixture_fixture", (0, 1, 2))
    working = {"one": one_step(gs).tolist(), "two": two_step_at_order(gs, 65).tolist()}
    change = max(float(np.max(np.abs(np.array(exact["65"][h])-exact["33"][h]))) for h in ("one", "two"))
    result["mixture_approximation"] = {"actual_mixture_risk": actual_risk,
          "mixture_quadrature": exact, "gaussian_moment_scores": working,
          "last_refinement_max_change": change,
          "refinement_accepted_at_002": change <= .002,
          "score_differences_from_GH65": {h: (np.array(working[h])-exact["65"][h]).tolist() for h in ("one", "two")},
          "winners": {h: {"mixture": int(np.argmax(exact["65"][h])), "moment": int(np.argmax(working[h]))} for h in ("one", "two")},
          "scope": "Two-component toy, all future component weights updated; GH is a numerical reference, not an exact physical posterior."}

    # Deterministic paid-only state restore on a separate synthetic software fixture.
    w = World("missing", 620221, pool_size=64, eval_size=128, ref_size=128, prefix=8)
    opts = {"startup": 8, "readout_every": 4, "gh_orders": [9,17,33,65], "score_tolerance": .00005, "tie_tolerance": .00002}
    def trajectory(restore):
        p = Policy(w.x, w.ref_x, "local", "h2", 9321, opts)
        for i in w.prefix:
            p.tell(w.pay(i), startup=True)
        hashes, ids = [], []
        for b in range(8, 16):
            if restore and b == 12:
                saved = json.loads(json.dumps(p.export()))
                p = Policy(w.x, w.ref_x, "local", "h2", 9321, opts)
                p.restore(saved)
            i, snap, details = p.ask(16-b)
            hashes.append(snap.digest()); ids.append(i)
            obs = w.pay(i); obs["prequery_hash"] = snap.digest()
            p.tell(obs)
        duplicate_blocked = False
        try:
            p.tell(w.pay(p.paid[-1]), startup=True)
        except AssertionError:
            duplicate_blocked = True
        return ids, hashes, duplicate_blocked, p
    full, resumed = trajectory(False), trajectory(True)
    assert full[:3] == resumed[:3] and full[2]
    result["deterministic_paid_resume"] = {"status": "PASS", "adaptive_ids": full[0],
                "all_snapshot_hashes_identical": full[1] == resumed[1], "duplicate_paid_id_blocked": full[2],
                "paid_queries": len(full[3].paid), "observations_include_missing": any(y is None for y in full[3].observations)}
    # Public reference-cloud refinement, not an efficacy criterion or an iid CI.
    full[3].fit()
    model = full[3].model
    candidates = w.x[:6]
    clouds = {}
    for size in (256, 512, 1024, 2048):
        ref = qmc.Sobol(4, scramble=True, seed=20261020).random_base2(int(np.log2(size)))
        clouds[str(size)] = one_step(model.snapshot(candidates, ref, range(6))).tolist()
    result["reference_cloud_fixture"] = {"scores": clouds,
           "max_difference_1024_to_2048": float(np.max(abs(np.array(clouds["1024"])-clouds["2048"]))),
           "scope": "One fixed paid-state numerical fixture; no universal population integration bound."}
    result["status"] = "PASS_CONTRACTS_WITH_APPROXIMATION_DISCLOSURE"
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--threads", type=int, choices=[1], required=True); parser.parse_args()
    unit = {"id": "reference_secondary_v1", "kind": "reference"}
    add_units([unit], "REFERENCE")
    if not (ROOT/"results/SECONDARY_NUMERICAL_CHECKS.json").exists():
        with Slot():
            selected = claim(unit["id"], os.getpid(), psutil.Process().create_time())
            if selected:
                attempt, _ = selected
                import posterior
                posterior.METER = Meter(attempt, reference=True)
                start = time.perf_counter()
                try:
                    result = run()
                    result.update(seconds=time.perf_counter()-start, actual_budget=posterior.METER.actual)
                    atomic_json(ROOT/"results/SECONDARY_NUMERICAL_CHECKS.json", result)
                    finish(unit["id"], attempt, "COMPLETE", "results/SECONDARY_NUMERICAL_CHECKS.json")
                    print(json.dumps(result, indent=2))
                except Exception as exc:
                    finish(unit["id"], attempt, "FAILED", note=repr(exc)); raise
