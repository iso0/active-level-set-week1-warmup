"""Tests for Week 14 closure override, weighted cut-edge metrics and the front discovery order."""
import numpy as np
from scipy.spatial.distance import cdist

from src.week13_boundary_metrics import edge_metrics, gabriel_edges
from src.week14_metrics import weighted_edge_metrics
from src.week14_models import closure_override
from src.week14_order import SIGNS_O3, closure_labels, dominance, front_discovery_order, maximal, minimal


def test_closure_override_is_exact_under_monotone_labels():
    rng = np.random.default_rng(0)
    X = rng.random((200, 4)); y = (X[:, 0] - X[:, 1] - .5 * X[:, 2] > -.2).astype(int)
    tr, te = np.arange(120), np.arange(120, 200)
    p, lab = closure_override(np.full(80, .5), X[tr], y[tr], X[te], SIGNS_O3)
    implied = lab >= 0
    assert implied.any()
    assert (lab[implied] == y[te][implied]).all()           # never wrong when labels are monotone
    assert np.all((p[lab == 1] >= .999)) and np.all(p[lab == 0] <= .001)


def test_closure_conflicts_keep_base_prediction():
    X = np.array([[0., 1, 1, 0], [1., 0, 0, 0], [.5, .5, .5, 0]])
    y = np.array([1, 0])                                     # violation: a "low" point labelled 1 and a "high" point 0
    D = dominance(X, SIGNS_O3)
    lab = closure_labels(D, np.arange(2), y)
    assert lab[2] == -2                                      # conflict detected
    p, l2 = closure_override(np.array([.3]), X[:2], y, X[2:], SIGNS_O3)
    assert p[0] == .3


def test_weighted_metrics_constant_and_perfect():
    rng = np.random.default_rng(1)
    z = rng.random((150, 3)); y = (z[:, 0] > .7).astype(int)
    e = gabriel_edges(z)
    assert weighted_edge_metrics(e, z, y, np.ones(150, int))["wBER"] == 0
    w = weighted_edge_metrics(e, z, y, y)
    assert w["wBER"] == 1 and w["wBEF1"] == 1
    # power 0 recovers the unweighted metric
    yh = (z[:, 0] > .65).astype(int)
    assert np.isclose(weighted_edge_metrics(e, z, y, yh, power=0)["wBER"], edge_metrics(e, y, yh)["BER"])


def test_front_order_starts_with_fronts():
    rng = np.random.default_rng(2)
    X = rng.random((80, 4))
    D = dominance(X, SIGNS_O3)
    order, mn, mx = front_discovery_order(D, np.arange(80), score=X @ SIGNS_O3)
    k = len(set(mn) | set(mx))
    assert set(order[:k]) == set(mn) | set(mx)
    assert len(set(order)) == len(order)
