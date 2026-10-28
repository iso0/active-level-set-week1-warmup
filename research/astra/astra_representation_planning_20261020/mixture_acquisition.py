"""One additional mechanism control: future component learning, same sign loss."""
import hashlib
import math
import numpy as np
from numpy.polynomial.hermite import hermgauss
from scipy.special import ndtr, logsumexp
import posterior
from planner import one_step, choose, gaussian_gain


def component_state(model, candidates, references):
    rm, rv, cm, cv, cross, noise = [], [], [], [], [], []
    for c in model.components:
        m, v = c.project(candidates)
        mr, vr = c.project(references)
        rm.append(mr)
        rv.append(np.maximum(c.diagonal-np.sum(vr*vr, axis=0), 1e-12))
        cm.append(m)
        cv.append(np.maximum(c.diagonal-np.sum(v*v, axis=0), 1e-12))
        cross.append(c.kernel(references, candidates)-vr.T@v)
        noise.append(np.full(len(candidates), c.spec.noise_sd**2))
    return dict(ref_mean=np.array(rm), ref_variance=np.array(rv), candidate_mean=np.array(cm),
                candidate_variance=np.array(cv), cross=np.array(cross), noise=np.array(noise),
                weights=model.weights.copy())


def state_hash(s):
    h = hashlib.sha256()
    for name in sorted(s):
        h.update(name.encode()); h.update(np.ascontiguousarray(s[name]).tobytes())
    return h.hexdigest()


def truncate(s, maximum_mass=1e-8):
    # A bounded-loss Bayes risk changes by at most omitted prior mixture mass;
    # a before-minus-after acquisition changes by at most twice that mass.
    order = np.argsort(s["weights"])
    omitted, drop = 0., []
    for i in order:
        w = float(s["weights"][i])
        if omitted+w > maximum_mass:
            break
        omitted += w; drop.append(i)
    keep = np.array([i for i in range(len(s["weights"])) if i not in drop])
    t = {name: value[keep] for name, value in s.items()}
    t["weights"] = t["weights"]/t["weights"].sum()
    return t, omitted


def current_risk(s):
    p = s["weights"] @ ndtr(s["ref_mean"]/np.sqrt(s["ref_variance"]))
    return float(np.mean(np.minimum(p, 1-p)))


def integrated_scores(s, order, availability=1., component_quadrature=False):
    """Exact component update; only the one-dimensional integral is approximated."""
    nodes, weights = hermgauss(order)
    nodes, weights = nodes*np.sqrt(2), weights/np.sqrt(np.pi)
    before = current_risk(s)
    scores, diagnostics = [], []
    w = s["weights"]
    if len(w) == 1:
        rho2 = s["cross"][0]**2/(s["ref_variance"][0, :, None]
                      *(s["candidate_variance"][0]+s["noise"][0])[None])
        gains = availability*gaussian_gain(s["ref_mean"][0, :, None]/np.sqrt(s["ref_variance"][0, :, None]), rho2).mean(0)
        return gains, [{"mass": 1., "quadrature_effective_nodes": None, "nodes": 0,
                        "maximum_normalized_weight": None, "analytic_single_component": True} for _ in gains]
    for i in range(s["candidate_mean"].shape[1]):
        cm = s["candidate_mean"][:, i]
        v = s["candidate_variance"][:, i]+s["noise"][:, i]
        mean = w@cm
        variance = w@(v+cm**2)-mean**2
        if component_quadrature:
            ys = (cm[:, None]+np.sqrt(v[:, None])*nodes).ravel()
            base_weights = (w[:, None]*weights).ravel()
        else:
            ys = mean+np.sqrt(variance)*nodes
            base_weights = weights
        posterior.METER.charge("planning_states", len(ys)) if posterior.METER else None
        posterior.COUNTERS["planning_states"] += len(ys)
        conditional_variance = np.maximum(s["ref_variance"]-s["cross"][:, :, i]**2/v[:, None], 1e-12)
        expected, total_mass, weighted_nodes = 0., 0., []
        for left in range(0, len(ys), 16):
            y = ys[left:left+16]
            lw = np.log(np.maximum(w[:, None], 1e-300))-.5*((y[None]-cm[:, None])**2/v[:, None]+np.log(2*np.pi*v[:, None]))
            log_density = logsumexp(lw, axis=0)
            conditional_weights = np.exp(lw-log_density[None])
            conditional_mean = (s["ref_mean"][:, :, None]
                    +s["cross"][:, :, i, None]*(y[None, None]-cm[:, None, None])/v[:, None, None])
            p = np.einsum("cs,crs->rs", conditional_weights,
                          ndtr(conditional_mean/np.sqrt(conditional_variance[:, :, None])))
            loss = np.minimum(p, 1-p).mean(0)
            if component_quadrature:
                iw = base_weights[left:left+16]
            else:
                log_q = -.5*((y-mean)**2/variance+np.log(2*np.pi*variance))
                iw = base_weights[left:left+16]*np.exp(log_density-log_q)
            expected += float(iw@loss)
            total_mass += float(iw.sum())
            weighted_nodes.extend(iw.tolist())
        iw = np.array(weighted_nodes)
        diagnostics.append({"mass": total_mass, "quadrature_effective_nodes": float(iw.sum()**2/(iw@iw)),
                            "nodes": len(ys), "maximum_normalized_weight": float(iw.max()/iw.sum())})
        scores.append(availability*(before-expected))
    return np.array(scores), diagnostics


def select_mixture(model, candidates, references, ids, gaussian,
                   orders=(17, 33, 65, 129), score_tolerance=1e-4, mass_tolerance=1e-4,
                   tie_tolerance=2e-5):
    full = component_state(model, candidates, references)
    s, omitted = truncate(full)
    previous, deltas, winners = None, [], []
    for order in orders:
        scores, diagnostic = integrated_scores(s, order, gaussian.availability)
        winners.append(int(ids[int(np.argmax(scores))]))
        if previous is not None:
            deltas.append(float(np.max(abs(scores-previous))))
        mass_ok = max(abs(r["mass"]-1) for r in diagnostic) <= mass_tolerance
        score_converged = len(deltas) >= 2 and max(deltas[-2:]) <= score_tolerance
        sorted_scores = np.sort(scores)
        gap = float(sorted_scores[-1]-sorted_scores[-2])
        ranking_resolved = (len(winners) >= 3 and len(set(winners[-3:])) == 1
                   and gap > 4*max(deltas[-2:], default=1.)+tie_tolerance)
        accepted = (score_converged or ranking_resolved) and mass_ok and min(scores) >= -score_tolerance
        if accepted:
            break
        previous = scores
    resolution = max(score_tolerance, max(deltas[-2:], default=score_tolerance))
    possible = np.flatnonzero(scores.max()-scores <= 2*resolution+tie_tolerance)
    myopic = one_step(gaussian)
    if not accepted:
        selected, ties, _ = choose(myopic, ids, tie_tolerance)
        fallback = "moment_h1_unaccepted_mixture_integral"
    elif len(possible) > 1:
        selected, ties, _ = choose(myopic[possible], [ids[k] for k in possible], tie_tolerance)
        fallback = "moment_h1_within_mixture_numerical_tie"
    else:
        selected = int(ids[int(possible[0])]); ties = 1; fallback = None
    details = {"scores": scores.tolist(), "order": order, "integration_deltas": deltas,
               "integration_accepted": bool(accepted), "rank_changed": len(set(winners)) > 1,
               "absolute_score_converged": bool(score_converged),
               "ranking_resolved": bool(ranking_resolved),
               "near_ties": ties, "fallback": fallback, "component_count": len(s["weights"]),
               "omitted_component_mass": omitted, "truncation_score_error_bound": 2*omitted,
               "quadrature_diagnostics": diagnostic, "mixture_state_hash": state_hash(full),
               "current_mixture_risk": current_risk(full),
               "scope": "Future component reweighting retained; deterministic importance quadrature, not exact integration."}
    return selected, details, full
