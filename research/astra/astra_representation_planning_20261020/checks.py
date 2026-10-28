"""Independent numerical references; execution must enter a claimed slot first."""
import argparse
from fractions import Fraction
import itertools
import json
import math
import os
import time
from coordination import ROOT, Slot
from ledger import Meter, add_units, claim, finish, atomic_json
import psutil


def references():
    import numpy as np
    from scipy.integrate import quad
    from scipy.linalg import block_diag
    from scipy.special import ndtr
    from scipy.stats import norm
    import posterior
    from posterior import Component, Spec, Posterior, GaussianState, compact
    from planner import condition, one_step, two_step_at_order, risk, gaussian_gain

    rng = np.random.default_rng(192017)
    tests = {}
    x = rng.uniform(size=(17, 4))
    eig = np.linalg.eigvalsh(compact(x, x, .9))
    tests["compact_psd_min_eigenvalue"] = float(eig.min())
    assert eig.min() > -1e-11
    paid, target = x[:8], x[8:]
    y = np.sin(paid[:, 0] * 3) - .5
    c = Component(Spec(radius=.9, local_sd=.6)).fit(paid, y)
    k = c.kernel(paid, paid)
    obs = k + (c.spec.noise_sd ** 2 + 1e-10) * np.eye(len(paid))
    kc = c.kernel(paid, target)
    direct_mean = kc.T @ np.linalg.solve(obs, y)
    direct_cov = c.kernel(target, target) - kc.T @ np.linalg.solve(obs, kc)
    mean, var = c.predict(target)
    tests["dense_mean_max_error"] = float(np.max(np.abs(mean - direct_mean)))
    tests["dense_latent_variance_max_error"] = float(np.max(np.abs(var - np.diag(direct_cov))))
    assert tests["dense_mean_max_error"] < 1e-9 and tests["dense_latent_variance_max_error"] < 1e-9
    tests["observation_noise_added_once"] = float(c.spec.noise_sd ** 2)
    lm, lv = c.discrepancy(target)
    kl = c.local_kernel(paid, target)
    assert np.max(np.abs(lm - kl.T @ np.linalg.solve(obs, y))) < 1e-9
    assert np.max(np.abs(lv - (.36 - np.diag(kl.T @ np.linalg.solve(obs, kl))))) < 1e-9
    # Null shrinkage: coherent near-zero values support absence of unnecessary local variance.
    sx = rng.uniform(size=(48, 4))
    model = Posterior("local").fit(sx, [0.] * len(sx), list(range(len(sx))))
    tests["null_local_weight_prior"] = .5
    tests["null_local_weight_posterior"] = model.local_summary()["local_posterior_weight"]
    assert tests["null_local_weight_posterior"] < .5
    startup = Posterior("local").fit(sx[:8], [0., 0., .8, 0., 0., 0., 0., 0.], list(range(8)))
    tests["startup_paid_anchor_influence"] = max(float(abs(cc.discrepancy(sx[2:3])[0][0])) for cc in startup.components)
    assert tests["startup_paid_anchor_influence"] > .01
    # Cross-covariance and dense sequential Gaussian conditioning (no GP-model code in reference).
    a = rng.normal(size=(7, 7))
    joint = a @ a.T / 10 + np.eye(7) * .1
    mu = rng.normal(size=7) * .2
    ref, cand = 4, 3
    s = GaussianState(mu[:ref], np.diag(joint)[:ref], mu[ref:], joint[ref:, ref:],
                      joint[:ref, ref:], np.array([.03, .06, .04]), 1., "fixture", (2, 5, 9))
    i, observation = 1, .17
    conditioned = condition(s, i, observation)
    obsvar = joint[ref+i, ref+i] + s.noise_variance[i]
    whole_mean = mu + joint[:, ref+i] * (observation - mu[ref+i]) / obsvar
    whole_cov = joint - np.outer(joint[:, ref+i], joint[ref+i]) / obsvar
    keep = [ref, ref+2]
    assert np.max(abs(conditioned.reference_mean - whole_mean[:ref])) < 1e-12
    assert np.max(abs(conditioned.candidate_covariance - whole_cov[np.ix_(keep, keep)])) < 1e-12
    assert np.max(abs(conditioned.cross_covariance - whole_cov[:ref, keep])) < 1e-12
    tests["dense_conditional_update"] = "PASS"

    # Independent scalar adaptive quadrature of future Bayes error.
    references_one = []
    for standardized_mean, rho2 in itertools.product((0., .4, 1.7), (.0, .15, .65, .97)):
        new_sd = math.sqrt(1 - rho2)
        value = quad(lambda z: norm.pdf(z) * ndtr(-abs(standardized_mean + math.sqrt(rho2) * z) / new_sd),
                     -10, 10, points=[-standardized_mean / math.sqrt(rho2)] if rho2 and abs(standardized_mean / math.sqrt(rho2)) < 10 else None,
                     epsabs=1e-10, limit=100)[0]
        independent = ndtr(-abs(standardized_mean)) - value
        implemented = float(gaussian_gain(np.array(standardized_mean), np.array(rho2)))
        references_one.append(abs(implemented - independent))
    tests["one_step_independent_quad_max_error"] = max(references_one)
    assert max(references_one) < 1e-8

    # Independent two-step oracle: integrate pointwise decision changes in the
    # conditional Gaussian; does not call the implemented condition() or SUR().
    def second_expected_loss(ref_mu, ref_var, candidate_mu, candidate_var, cross):
        losses = []
        for rm, rv, cv in zip(ref_mu, ref_var, cross):
            after = max(rv - cv * cv / candidate_var, 1e-12)
            scale = cv / math.sqrt(candidate_var)
            root = -rm / scale if abs(scale) > 1e-15 else 100
            points = [root] if -9 < root < 9 else None
            value = quad(lambda z: norm.pdf(z) * ndtr(-abs(rm + scale * z) / math.sqrt(after)),
                         -9, 9, epsabs=2e-8, points=points, limit=80)[0]
            losses.append(value)
        return float(np.mean(losses))
    dense_two = []
    for i in range(cand):
        obsvar = s.candidate_covariance[i, i] + s.noise_variance[i]
        cross = s.cross_covariance[:, i]
        keep = [j for j in range(cand) if j != i]
        vref = s.reference_variance - cross ** 2 / obsvar
        k2 = s.candidate_covariance[np.ix_(keep, keep)] - np.outer(s.candidate_covariance[keep, i], s.candidate_covariance[i, keep]) / obsvar
        c2 = s.cross_covariance[:, keep] - np.outer(cross, s.candidate_covariance[i, keep]) / obsvar
        def outer(z):
            ref_mu = s.reference_mean + cross / math.sqrt(obsvar) * z
            cmu = s.candidate_mean[keep] + s.candidate_covariance[keep, i] / math.sqrt(obsvar) * z
            loss = min(second_expected_loss(ref_mu, vref, cmu[j], k2[j, j] + s.noise_variance[keep[j]], c2[:, j]) for j in range(len(keep)))
            return norm.pdf(z) * loss
        dense_two.append(risk(s) - quad(outer, -7, 7, epsabs=2e-6, limit=80)[0])
    scores = {str(order): two_step_at_order(s, order).tolist() for order in (9, 17, 33, 65)}
    errors = {order: float(np.max(np.abs(np.array(values) - dense_two))) for order, values in scores.items()}
    tests["two_step_dense_nested_quadrature"] = {"reference_scores": dense_two, "scores": scores,
        "max_errors": errors, "winners": {k: int(np.argmax(v)) for k, v in scores.items()},
        "reference_winner": int(np.argmax(dense_two)), "reference_epsabs": 2e-6}
    assert errors["65"] < .002
    assert np.all(np.array(scores["65"]) >= one_step(s) - 1e-10)

    # Exact, rational, finite posterior: an information investment whose useful
    # second query depends on a switch. No Gaussian approximation in this test.
    states = []
    for z, switch, ea, ub, uc in itertools.product((0, 1), repeat=5):
        weight = Fraction(1, 16) * (Fraction(1, 5) if ea else Fraction(4, 5))
        # candidate order: direct noisy, branch B, branch C, switch
        observations = (z ^ ea, z if switch == 0 else ub, z if switch == 1 else uc, switch)
        states.append((weight, z, observations))
    def exact_risk(selected):
        pos = sum((w for w, z, ys in selected if z), Fraction(0))
        neg = sum((w for w, z, ys in selected if not z), Fraction(0))
        return min(pos, neg)  # joint-probability contribution; no normalization error
    one_loss, two_loss = [], []
    for i in range(4):
        one_loss.append(sum((exact_risk([s0 for s0 in states if s0[2][i] == y]) for y in (0, 1)), Fraction(0)))
        loss = Fraction(0)
        for y in (0, 1):
            selected = [s0 for s0 in states if s0[2][i] == y]
            loss += min(sum((exact_risk([s0 for s0 in selected if s0[2][j] == v]) for v in (0, 1)), Fraction(0)) for j in range(4) if j != i)
        two_loss.append(loss)
    assert min(range(4), key=lambda i: one_loss[i]) == 0
    assert min(range(4), key=lambda i: two_loss[i]) == 3 and two_loss[3] == 0
    tests["exact_contingent_investment"] = {"one_step_losses": list(map(str, one_loss)),
        "two_step_losses": list(map(str, two_loss)), "one_step_first": 0, "two_step_first": 3,
        "interpretation": "Existence of horizon value, not proof about controlled GP worlds."}
    tests["status"] = "PASS"
    return tests


def main():
    unit = {"id": "reference_initial_v1", "kind": "reference"}
    add_units([unit], "REFERENCE")
    if (ROOT / "results/INITIAL_NUMERICAL_CHECKS.json").exists():
        print("Previously completed reference retained; not repeated")
        return
    with Slot():
        selected = claim(unit["id"], os.getpid(), psutil.Process().create_time())
        if selected is None:
            return
        attempt, _ = selected
        import posterior
        posterior.METER = Meter(attempt, reference=True)
        start = time.perf_counter()
        try:
            result = references()
            result.update(seconds=time.perf_counter() - start, counters=posterior.COUNTERS,
                          actual_budget=posterior.METER.actual)
            atomic_json(ROOT / "results/INITIAL_NUMERICAL_CHECKS.json", result)
            finish(unit["id"], attempt, "COMPLETE", "results/INITIAL_NUMERICAL_CHECKS.json")
            print(json.dumps(result, indent=2))
        except Exception as exc:
            finish(unit["id"], attempt, "FAILED", note=repr(exc))
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, choices=[1], required=True)
    parser.parse_args()
    main()
