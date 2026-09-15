"""Week 9 Phase 1.23 — numerical checks for the theory note and the 2D conceptual example.

Illustrations only (not part of the pre-registered stress test).  Uses separate seeds and data.
  1. 1D logistic (C = 1e6) on label-separable data: fitted threshold vs gap midpoint; slope x gap width.
  2. Monotonicity of E[sigmoid(F)], F ~ N(mu, v), in |mu| and v (the margin ordering lemma).
  3. Coupon-collector vs covering: distinct cells hit by m uniform queries.
  4. 2D analogue of M3 on a wavy boundary: where margin and the frozen band-coverage rule query,
     how long the queried labels stay separable in h, and how many boundary sections they visit.
"""
from __future__ import annotations

import json
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.special import expit
from sklearn.gaussian_process.kernels import ConstantKernel, Matern
from sklearn.preprocessing import StandardScaler

from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_20_acquisition_search as search
from src import week9_phase1_23_synthetic as syn

OUT = syn.OUTPUT
warnings.filterwarnings("ignore")


def check_logistic_midpoint(reps: int = 300) -> dict:
    rng = np.random.default_rng(1)
    offsets, logit_change = [], []
    for _ in range(reps):
        n = int(rng.integers(8, 60))
        h = rng.normal(size=n)
        y = (h > rng.normal(0, 0.5)).astype(int)
        if y.min() == y.max():
            continue
        phys = p11.fit_physics_mean(h, y, np.arange(n), 1)
        a, b = h[y == 0].max(), h[y == 1].min()
        slope = phys.model.coef_[0, 0] / phys.scaler.scale_[0]
        threshold = phys.scaler.mean_[0] - phys.model.intercept_[0] * phys.scaler.scale_[0] / phys.model.coef_[0, 0]
        offsets.append((threshold - (a + b) / 2) / (b - a))
        logit_change.append(slope * (b - a))
    offsets, logit_change = np.abs(offsets), np.asarray(logit_change)
    return {"cases": len(offsets), "threshold_offset_from_midpoint_in_gap_widths": {
                "median": float(np.median(offsets)), "q90": float(np.quantile(offsets, 0.9)), "max": float(offsets.max())},
            "logit_change_across_gap": {"min": float(logit_change.min()), "median": float(np.median(logit_change)),
                                        "max": float(logit_change.max())},
            "probability_at_gap_edges_if_threshold_at_midpoint": float(expit(-np.median(logit_change) / 2))}


def check_margin_monotonicity() -> dict:
    z = np.random.default_rng(2).normal(size=400_000)
    mus, vs = np.linspace(0.05, 4, 40), np.linspace(0.01, 4, 40)
    p = np.array([[expit(m + np.sqrt(v) * z).mean() for v in vs] for m in mus]) - 0.5
    return {"increasing_in_mu_for_every_v": bool((np.diff(p, axis=0) > 0).all()),
            "decreasing_in_v_for_every_mu": bool((np.diff(p, axis=1) < 0).all())}


def coupon(k: int, m: np.ndarray) -> np.ndarray:
    return k * (1 - (1 - 1 / k) ** m)


def model_2d(pool: np.ndarray, h: np.ndarray, y: np.ndarray, revealed: np.ndarray):
    physics = p11.fit_physics_mean(h, y, revealed, 1)
    scaler = StandardScaler().fit(pool)
    kernel = ConstantKernel(p13.INITIAL_RESIDUAL_VARIANCE, p13.RESIDUAL_VARIANCE_BOUNDS) * Matern(
        length_scale=np.ones(2), length_scale_bounds=(p13.PRIMARY_LENGTH_BOUNDS[0], search.LENGTH_UPPER), nu=1.5)
    gp = p11.FixedMeanLaplaceGPC(kernel, optimize=True).fit(scaler.transform(pool[revealed]), y[revealed],
                                                             physics.latent(h[revealed]))
    return physics, scaler, gp


def toy_run(seed: int, policy: str, budget: int = 40, n: int = 400, amplitude: float = 0.12):
    rng = np.random.default_rng(seed)
    pool = rng.uniform(size=(n, 2))
    h = pool[:, 0]
    boundary = lambda x2: 0.55 + amplitude * np.sin(2 * np.pi * x2)
    y = (pool[:, 0] > boundary(pool[:, 1])).astype(int)
    xs = StandardScaler().fit_transform(pool)
    order = syn.maximin_order(xs, seed)
    queried = syn.seed_prefix(order, y, 8)
    select = search.pol_margin if policy == "margin" else syn.FROZEN_COVERAGE
    separable = []
    while len(queried) < budget:
        rev = np.asarray(queried)
        physics, scaler, gp = model_2d(pool, h, y, rev)
        cand = np.setdiff1d(np.arange(n), rev)
        p = gp.predict_proba(scaler.transform(pool[cand]), physics.latent(h[cand]))[:, 1]
        seen = np.full(n, -1)
        seen[rev] = y[rev]
        state = search.State(run_id="toy", budget=len(queried), revealed=rev, candidates=cand, seen_label=seen,
                             seen_logdepth=np.full(n, np.nan), x_scaled=xs, z_scaled=xs, logh=h, p_cand=p,
                             mean_cand=p, var_cand=p, fit=None, rng=rng, x4=pool, train=np.arange(n), cache={},
                             leaky_rank=None)
        separable.append(bool(h[rev][y[rev] == 0].max() < h[rev][y[rev] == 1].min()))
        queried.append(select(state))
    return pool, y, boundary, queried, separable, len(queried) - len(separable)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"logistic_midpoint": check_logistic_midpoint(), "margin_ordering": check_margin_monotonicity()}
    m = np.array([8, 16, 24, 32])
    result["coupon_collector"] = {f"K={k}": {"queries": m.tolist(), "expected_distinct_cells_uniform": coupon(k, m).round(2).tolist(),
                                             "covering_design": np.minimum(m, k).tolist()} for k in (8, 16, 27)}

    stats = {"margin": {"break_budget": [], "bins_visited_B8_24": []},
             "coverage_then_margin_B40": {"break_budget": [], "bins_visited_B8_24": []}}
    runs = {}
    for seed in range(40):
        for policy in stats:
            pool, y, boundary, queried, separable, s0 = toy_run(1000 + seed, policy)
            active = np.asarray(queried[s0:][:16])
            stats[policy]["break_budget"].append(next((s0 + i for i, s in enumerate(separable) if not s), 40))
            stats[policy]["bins_visited_B8_24"].append(int(len(np.unique((pool[active, 1] * 8).astype(int)))))
            if seed == 0:
                runs[policy] = (pool, y, boundary, queried, s0)
    result["toy_2d_wavy_boundary"] = {
        "setup": "400 uniform points in [0,1]^2, h = x1, y = 1[x1 > 0.55 + 0.12 sin(2 pi x2)], 8-point maximin seed, "
                 "2D analogue of M3, 40 toy seeds; illustration only",
        **{p: {"first_budget_with_non_separable_labels_median": float(np.median(s["break_budget"])),
               "share_still_separable_at_B24": float(np.mean(np.asarray(s["break_budget"]) > 24)),
               "distinct_x2_octants_among_first_16_active_queries_mean": float(np.mean(s["bins_visited_B8_24"]))}
           for p, s in stats.items()}}
    (OUT / "theory_toy_checks.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.6), sharey=True)
    grid = np.linspace(0, 1, 400)
    for ax, (policy, title) in zip(axes, (("margin", "plain M3-style margin"),
                                          ("coverage_then_margin_B40", "boundary-conditioned coverage (frozen rule)"))):
        pool, y, boundary, queried, s0 = runs[policy]
        ax.scatter(pool[:, 1], pool[:, 0], c=np.where(y == 1, "#f2b8b5", "#b9d3ee"), s=9, lw=0)
        ax.plot(grid, boundary(grid), color="black", lw=1.6, label="true boundary")
        seed_pts, active = queried[:s0], queried[s0:s0 + 24]
        ax.scatter(pool[seed_pts, 1], pool[seed_pts, 0], marker="s", facecolor="none", edgecolor="#444", s=46,
                   label="maximin seed")
        sc = ax.scatter(pool[active, 1], pool[active, 0], c=np.arange(len(active)), cmap="viridis", s=48,
                        edgecolor="black", lw=0.5, label="active queries (colour = order)")
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("orthogonal coordinate x2")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("physics coordinate h = x1")
    axes[0].legend(fontsize=8.5, loc="lower left")
    fig.colorbar(sc, ax=axes, label="query order (first 24 active queries)", shrink=0.85)
    fig.suptitle("Conceptual example: margin bisects along h near one level; coverage spreads along the boundary band",
                 fontsize=12)
    (OUT / "figures").mkdir(exist_ok=True)
    fig.savefig(OUT / "figures" / "concept_margin_vs_boundary_coverage.png", dpi=170, bbox_inches="tight")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
