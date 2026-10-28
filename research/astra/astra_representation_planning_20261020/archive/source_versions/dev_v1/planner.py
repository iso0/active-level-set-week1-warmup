"""Posterior-agnostic bounded Gaussian risk planner; contains no evaluator access."""
from dataclasses import replace
import numpy as np
from numpy.polynomial.hermite import hermgauss
from scipy.special import ndtr, owens_t
from posterior import GaussianState, count


def gaussian_gain(a, rho2):
    if np.min(rho2, initial=0) < -1e-7 or np.max(rho2, initial=0) > 1 + 1e-7:
        raise ArithmeticError("Invalid information fraction: noise/covariance contract")
    rho2 = np.clip(rho2, 0, 1)
    ratio = np.sqrt((1 - rho2) / np.maximum(rho2, 1e-300))
    gain = ndtr(-np.abs(a)) - 2 * owens_t(np.abs(a), ratio)
    gain = np.where(rho2 < 1e-15, 0, gain)
    return np.maximum(gain, 0)


def risk(s):
    return float(ndtr(-np.abs(s.reference_mean / np.sqrt(s.reference_variance))).mean())


def one_step(s):
    vobs = np.diag(s.candidate_covariance) + s.noise_variance
    rho2 = s.cross_covariance ** 2 / (s.reference_variance[:, None] * vobs[None, :])
    return s.availability * gaussian_gain(s.reference_mean[:, None] / np.sqrt(s.reference_variance[:, None]), rho2).mean(0)


def condition(s, i, y, observed=True):
    keep = np.array([k for k in range(len(s.ids)) if k != i], int)
    if not observed:
        return GaussianState(s.reference_mean, s.reference_variance, s.candidate_mean[keep],
                 s.candidate_covariance[np.ix_(keep, keep)], s.cross_covariance[:, keep],
                 s.noise_variance[keep], s.availability, s.source_hash, tuple(s.ids[k] for k in keep))
    v = s.candidate_covariance[i, i] + s.noise_variance[i]
    cr, cc = s.cross_covariance[:, i], s.candidate_covariance[keep, i]
    dy = y - s.candidate_mean[i]
    return GaussianState(s.reference_mean + cr * dy / v,
                 np.maximum(s.reference_variance - cr * cr / v, 1e-12),
                 s.candidate_mean[keep] + cc * dy / v,
                 s.candidate_covariance[np.ix_(keep, keep)] - np.outer(cc, cc) / v,
                 s.cross_covariance[:, keep] - np.outer(cr, cc) / v,
                 s.noise_variance[keep], s.availability, s.source_hash,
                 tuple(s.ids[k] for k in keep))


def _second_gain(s, forced_id):
    if not len(s.ids):
        return 0.
    g = one_step(s)
    if forced_id is not None:
        return float(g[s.ids.index(forced_id)])
    return float(np.max(g))


def two_step_at_order(s, order, forced_second=None):
    """Outer GH; inner Gaussian sign-loss expectation is analytic. Missing costs stay paid."""
    nodes, weights = hermgauss(order)
    nodes, weights = nodes * np.sqrt(2), weights / np.sqrt(np.pi)
    gains = one_step(s)
    result = gains.copy()
    for i in range(len(s.ids)):
        # A scheduled random next action cannot be the already selected first action.
        forced = next((j for j in (forced_second or ()) if j != s.ids[i]), None)
        future = 0.
        sd = np.sqrt(s.candidate_covariance[i, i] + s.noise_variance[i])
        for node, w in zip(nodes, weights):
            count("planning_states")
            new = condition(s, i, s.candidate_mean[i] + sd * node)
            future += w * _second_gain(new, forced)
        missing = _second_gain(condition(s, i, 0., observed=False), forced)
        result[i] += s.availability * future + (1 - s.availability) * missing
    return result


def choose(scores, ids, tolerance):
    top = float(np.max(scores))
    tied = [int(i) for i, value in zip(ids, scores) if top - float(value) <= tolerance]
    return min(tied), len(tied), top


def plan(s, horizon, *, orders=(9, 17, 33, 65), score_tolerance=5e-4,
         tie_tolerance=2e-5, forced_second=None):
    if horizon == 1 or len(s.ids) < 2:
        scores = one_step(s)
        selected, ties, top = choose(scores, s.ids, tie_tolerance)
        return selected, {"scores": scores.tolist(), "order": 0, "integration_delta": 0.,
                          "integration_accepted": True, "near_ties": ties, "rank_changed": False,
                          "working_risk": risk(s), "score_max": top}
    previous = None
    winners = []
    deltas = []
    for order in orders:
        scores = two_step_at_order(s, order, forced_second)
        selected, ties, top = choose(scores, s.ids, tie_tolerance)
        winners.append(selected)
        delta = None if previous is None else float(np.max(np.abs(scores - previous)))
        if delta is not None:
            deltas.append(delta)
        if len(deltas) >= 2 and max(deltas[-2:]) <= score_tolerance:
            break
        previous = scores
    accepted = len(deltas) >= 2 and max(deltas[-2:]) <= score_tolerance
    # The refinement discrepancy is an empirical diagnostic, not a rigorous
    # quadrature bound. Do not invent an ordering inside its resolution.
    resolution = max(score_tolerance, max(deltas[-2:], default=score_tolerance))
    tied_positions = np.flatnonzero(scores.max() - scores <= 2 * resolution + tie_tolerance)
    numerical_ambiguity = len(tied_positions) > 1
    if numerical_ambiguity:
        myopic = one_step(s)
        selected, _, _ = choose(myopic[tied_positions], [s.ids[k] for k in tied_positions], tie_tolerance)
    return selected, {"scores": scores.tolist(), "order": order, "integration_delta": delta,
                      "integration_accepted": accepted, "integration_deltas": deltas,
                      "near_ties": ties, "rank_changed": len(set(winners)) > 1,
                      "numerical_ambiguity": numerical_ambiguity,
                      "fallback": "myopic_within_unresolved_set" if numerical_ambiguity else None,
                      "resolution_diagnostic": resolution,
                      "working_risk": risk(s), "score_max": top,
                      "precision_rule": "bounded refinement; no performance-based escalation"}
