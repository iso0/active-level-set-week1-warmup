"""Unit checks of the Week 13 propositions and boundary-metric invariances."""
import numpy as np
from scipy.spatial.distance import cdist

from src.week13_boundary_metrics import edge_metrics, gabriel_edges, knn_edges
from src.week13_discovery_and_anchoring import fill_distances
from src.week13_synthetic import LaplaceGPC


def _toy(seed=0, n=120, prevalence=.1):
    rng = np.random.default_rng(seed)
    z = rng.random((n, 3))
    y = (z[:, 0] > np.quantile(z[:, 0], prevalence)).astype(int)
    return z, y


def test_gabriel_contains_mst_and_is_symmetric_subset():
    z, _ = _toy()
    e = gabriel_edges(z)
    assert (e[:, 0] < e[:, 1]).all()
    d = cdist(z, z)
    for i, j in e[:50]:
        mid = (z[i] + z[j]) / 2
        r = d[i, j] / 2
        others = np.delete(np.arange(len(z)), [i, j])
        assert (np.linalg.norm(z[others] - mid, axis=1) >= r - 1e-9).all()
    # connectivity (Gabriel graph contains the Euclidean MST)
    seen, stack = {0}, [0]
    adj = {k: set() for k in range(len(z))}
    for i, j in e:
        adj[i].add(j); adj[j].add(i)
    while stack:
        for v in adj[stack.pop()] - seen:
            seen.add(v); stack.append(v)
    assert len(seen) == len(z)


def test_constant_predictor_values_are_prevalence_free():
    for prev in (.05, .3, .5):
        z, y = _toy(prevalence=prev)
        for graph in (gabriel_edges(z), knn_edges(z, 5)):
            for c in (0, 1):
                m = edge_metrics(graph, y, np.full(len(y), c))
                assert m["BER"] == 0 and m["BEF1"] == 0 and abs(m["BEBA"] - .5) < 1e-12


def test_perfect_predictor_scores_one():
    z, y = _toy()
    m = edge_metrics(gabriel_edges(z), y, y)
    assert m["BER"] == 1 and m["BEF1"] == 1 and m["spurious_cut"] == 0


def test_proposition1_identity():
    rng = np.random.default_rng(3)
    y = (rng.random(200) > .2).astype(int)  # majority 1
    yhat = (rng.random(200) > .3).astype(int)
    C = ((yhat == 0) & (y == 0)).sum()
    W = ((yhat == 0) & (y == 1)).sum()
    assert np.isclose(np.mean(yhat == y) - np.mean(y == 1), (C - W) / 200)


def test_proposition2_window():
    # BA and accuracy disagree exactly when marginal precision lies in (pi, 1/2)
    n_m, n_M = 10, 90
    pi = n_m / (n_m + n_M)
    for dC, dW in ((1, 3), (3, 2), (1, 20)):
        rho = dC / (dC + dW)
        d_acc = (dC - dW) / (n_m + n_M)
        d_ba = .5 * (dC / n_m - dW / n_M)
        assert (d_acc > 0) == (rho > .5)
        assert (d_ba > 0) == (rho > pi)


def test_proposition4_certificate():
    rng = np.random.default_rng(5)
    for _ in range(20):
        z = rng.random((150, 2))
        y = (np.linalg.norm(z - .8, axis=1) > .15).astype(int)  # small minority disc
        order = rng.permutation(150)
        h = fill_distances(z, order)
        mino, maj = np.nonzero(y == 0)[0], np.nonzero(y == 1)[0]
        if len(mino) == 0:
            continue
        rho_star = cdist(z[mino], z[maj]).min(axis=1).max()
        for b in range(1, 150):
            if h[b - 1] < rho_star:
                assert (y[order[:b]] == 0).any()
                break


def test_proposition7_anchoring_bound():
    rng = np.random.default_rng(11)
    x = rng.random((40, 2))
    y = (x[:, 0] > .3).astype(int)
    mean = np.full(40, 2.0)
    gp = LaplaceGPC([.3, .3], 1.0).fit(x, y, mean=mean)
    xs = rng.random((200, 2))
    from src.week13_synthetic import matern32
    k = matern32(gp.x, xs, gp.ls, gp.var)
    bound = k[gp.y == 0].sum(axis=0)
    mu = gp.latent_mean(xs, np.full(200, 2.0))
    assert not ((mu < 0) & (2.0 >= bound)).any()
