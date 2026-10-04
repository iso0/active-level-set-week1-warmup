"""Week 15 — Expected Boundary-edge Risk reduction (EBR) for finite-pool active level-set estimation.

Estimand.  The level set Γ = {f = 0} of the latent of a GP classifier.  Evaluation (synthetic) is the
normalized surface distance NSD of the predicted boundary {μ = 0} against Γ under uniform surface
measure.

Model-internal surrogate risk.  Let Z be a *uniform* reference cloud in the input domain (label-free;
for real data, uniform in the pool's bounding box) and E the edges of its symmetric kNN graph.  With the
Laplace posterior latent marginals (μ_z, s_z) and plug-in predicted labels ŷ_z = 1[μ_z > 0],

    R(D) = Σ_{(i,j) ∈ E} P_D( 1[f_i > 0] ⊕ 1[f_j > 0]  ≠  ŷ_i ⊕ ŷ_j ),

the posterior expected number of graph edges on which the true boundary crossing disagrees with the
predicted boundary crossing.  Because Z is uniform, the expected number of cut edges per unit boundary
area is constant (the graph-cut limit of Theorem E2 with p ≡ const), so R is a resolution-r surrogate of
the expected surface-measure symmetric difference between Γ and the predicted boundary — the quantity
NSD scores — rather than of misclassified volume.  Pairwise posterior correlation is kept: each edge
probability is a bivariate-normal orthant probability.

Acquisition (one-step look-ahead, SUR form).
    EBR(c) = R(D) − Σ_{y∈{0,1}} p_D(y | c) R(D ∪ {(c, y)}),
choose argmax over unlabelled pool cases; p_D(y|c) is the model's predictive probability.  The
ablation VSUR replaces R by the expected misclassified latent-sign volume Σ_z min(q_z, 1 − q_z),
q_z = Φ(μ_z/s_z) (the classic excursion-set SUR / Vorob'ev-type risk), on the same cloud.
"""
from __future__ import annotations

import numpy as np
from scipy.linalg import solve_triangular
from scipy.spatial import cKDTree
from scipy.special import ndtr, owens_t

from src.week13_synthetic import LaplaceGPC, matern32


class MeanLaplaceGPC(LaplaceGPC):
    """LaplaceGPC with a known constant prior mean m0 (m0 = 0 reproduces LaplaceGPC exactly)."""

    def __init__(self, ls, var, m0=0.0):
        super().__init__(ls, var)
        self.m0 = float(m0)

    def fit(self, x, y, mean=None, iters=60):
        return super().fit(x, y, mean=np.full(len(y), self.m0), iters=iters)

    def latent_mean(self, xs, mean=None):
        return super().latent_mean(xs, np.full(len(xs), self.m0))

    def proba(self, xs, mean=None):
        return super().proba(xs, np.full(len(xs), self.m0))


def make_gp(hyp):
    return MeanLaplaceGPC(hyp["ls"], hyp["var"], hyp.get("m0", 0.0))


def latent_mv(gp, Z):
    """Posterior latent mean and variance (including a constant prior mean if present)."""
    ks = matern32(gp.x, Z, gp.ls, gp.var)
    mu = ks.T @ gp.resid + getattr(gp, "m0", 0.0)
    V = solve_triangular(gp.L, gp.sw[:, None] * ks, lower=True)
    return mu, np.maximum(gp.var - (V * V).sum(0), 1e-12)


def knn_graph(Z, k=8):
    _, nn = cKDTree(Z).query(Z, k=k + 1)
    e = {(min(i, j), max(i, j)) for i in range(len(Z)) for j in nn[i, 1:]}
    return np.asarray(sorted(e), int)


def bvn_lower(h, k, rho):
    """P(X <= h, Y <= k) for a standard bivariate normal with correlation rho (vectorized, Owen's T)."""
    h = np.where(np.abs(h) < 1e-10, 1e-10, h)
    k = np.where(np.abs(k) < 1e-10, 1e-10, k)
    rho = np.clip(rho, -.999999, .999999)
    sq = np.sqrt(1 - rho ** 2)
    ah = (k - rho * h) / (h * sq)
    ak = (h - rho * k) / (k * sq)
    corr = np.where(h * k < 0, .5, 0.0)
    return .5 * ndtr(h) + .5 * ndtr(k) - owens_t(h, ah) - owens_t(k, ak) - corr


class Posterior:
    def __init__(self, gp: LaplaceGPC):
        self.gp = gp

    def marginals_and_edges(self, Z, edges):
        gp = self.gp
        ks = matern32(gp.x, Z, gp.ls, gp.var)
        mu = ks.T @ gp.resid + getattr(gp, "m0", 0.0)
        V = solve_triangular(gp.L, gp.sw[:, None] * ks, lower=True)
        var = np.maximum(gp.var - (V * V).sum(0), 1e-12)
        i, j = edges[:, 0], edges[:, 1]
        # prior covariance of neighbouring pairs (row-wise) without forming the full |Z|x|Z| matrix
        d = np.sqrt((((Z[i] - Z[j]) / gp.ls) ** 2).sum(1)) * np.sqrt(3.0)
        kij = gp.var * (1 + d) * np.exp(-d)
        cov = kij - (V[:, i] * V[:, j]).sum(0)
        s = np.sqrt(var)
        rho = cov / (s[i] * s[j])
        return mu, s, rho


def edge_risk(mu, s, rho, edges):
    """Σ_e P(true crossing ≠ predicted crossing) with bivariate-normal pair probabilities."""
    i, j = edges[:, 0], edges[:, 1]
    a_i, a_j = mu[i] / s[i], mu[j] / s[j]
    # P(f_i > 0, f_j <= 0) = P(-f_i < 0 ... ) = Phi2(a_i, -a_j; -rho)
    p10 = bvn_lower(a_i, -a_j, -rho)
    p01 = bvn_lower(-a_i, a_j, -rho)
    p_cut = np.clip(p10 + p01, 0, 1)
    pred_cut = (mu[i] > 0) != (mu[j] > 0)
    return float(np.where(pred_cut, 1 - p_cut, p_cut).sum())


def edge_dice_risk(mu, s, rho, edges):
    """Dice-normalized boundary risk E[W_err] / (E[W_true] + W_pred) (EBR-D).

    The unnormalized edge risk equals the expected graph perimeter of the error set, which scales with
    the size of the true and predicted boundaries; minimizing it rewards beliefs in *smaller* boundaries
    (development failure, Week 15).  Normalizing by the expected boundary size targets the surface-Dice
    deficit, i.e. 1 - NSD, which is scale-free.
    """
    i, j = edges[:, 0], edges[:, 1]
    a_i, a_j = mu[i] / s[i], mu[j] / s[j]
    p_cut = np.clip(bvn_lower(a_i, -a_j, -rho) + bvn_lower(-a_i, a_j, -rho), 0, 1)
    pred_cut = (mu[i] > 0) != (mu[j] > 0)
    w_err = np.where(pred_cut, 1 - p_cut, p_cut).sum()
    return float(w_err / (p_cut.sum() + pred_cut.sum() + 1e-9))


def volume_risk(mu, s):
    q = ndtr(mu / s)
    return float(np.minimum(q, 1 - q).sum())


def lookahead_scores(z_pool, y_pool, L, cands, hyp, Z, edges, kind="EBR"):
    """One-step expected risk reduction for each candidate (refits the Laplace posterior per fantasy)."""
    def risk(idx, ylab):
        gp = make_gp(hyp).fit(z_pool[idx], ylab)
        mu, s, rho = Posterior(gp).marginals_and_edges(Z, edges)
        if kind == "EBR":
            return edge_risk(mu, s, rho, edges)
        if kind == "EBRD":
            return edge_dice_risk(mu, s, rho, edges)
        return volume_risk(mu, s)
    idx = np.asarray(L)
    base = make_gp(hyp).fit(z_pool[idx], y_pool[idx])
    p1 = base.proba(z_pool[cands])
    r0 = risk(idx, y_pool[idx])
    scores = np.empty(len(cands))
    for t, c in enumerate(cands):
        ix = np.r_[idx, c]
        r_one = risk(ix, np.r_[y_pool[idx], 1])
        r_zero = risk(ix, np.r_[y_pool[idx], 0])
        scores[t] = r0 - (p1[t] * r_one + (1 - p1[t]) * r_zero)
    return scores, base
