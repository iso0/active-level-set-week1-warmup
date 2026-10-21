"""RC24 section 8 - synthetic benchmark with the unchanged RC23 / RC24 learners (src.rc23_common.run_arm, src.rc24_pilot.run_pac) on
synthetic worlds that have the real pool's information contract (src.rc19_pool.Reveal on a synthetic manifest; public inputs, paid-only
outcomes, 8-point maximin startup, one-class rule, budgets 8..60).

World (family parameters in FAMILIES; seed -> rng [2424, seed, family index]):
  inputs   N = 500 log-inputs u ~ U[-1, 1]^4, X = exp(base + u) (P, VX, LS, ST columns); public log h = u_P - u_VX / 2 - 3 u_LS / 2;
           z_h its standardisation.
  depth    a*(u) = theta z_dir(u) + s g(u),  z_dir = standardised projection of u on the direction at angle phi from the log-h
           direction (phi = 0: the physics anchor is right; phi = 90 deg: depth scales along an orthogonal direction), g a unit
           Matern-3/2 GP sample (lengthscale 0.8 in u units); observed log depth = 4.7 + 0.25 a* + e, e ~ N(0, 0.01^2);
           5 % of records are "short" (extra noise N(0, 0.3^2), flagged) - the record-quality contract of the real pool.
  label    eta = alpha_h z_h + alpha_a a* + beta_r r(u) (r: a second unit GP sample, lengthscale 0.6 - label structure that neither h nor
           depth explains); y = 1[eta + sigma_y Logistic > tau], tau = the (1 - pi) quantile of eta (positive rate pi);
           optional aleatoric corner (u_P > 0.55 and u_VX > 0.55, ~5 % of inputs): y ~ Bernoulli(1/2) independently of everything.
Splits per world: "std" = random 80 / 20 pool / test; "block" = k-means (k = 5, standardised u, seed-fixed): the test set is the block
  whose positive rate is closest to the world's among the blocks with >= 15 runs of each class (evaluator-side rule; learners never
  see it), the other blocks are the pool (extrapolation).
Families: DEV families (development only) and TEST families (frozen before any test-family world is run; different parameter values,
  fresh seeds 101-105). Arms: HONLY_MARGIN, HA_LEAN_MARGIN, HA_TREND_MARGIN, PAC_MARGIN (+ registered later candidates).
    python -m src.rc24_synth work s-dev | s-test
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_pool as P
import src.rc22_common as C22
import src.rc23_common as C23
from src.week13_synthetic_al import maximin_order

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc24"
BASE = np.log(np.array([350.0, 0.6, 4.5e-5, 400.0]))
D_H = np.array([1.0, -0.5, -1.5, 0.0])
N_WORLD = 500
BASE_FAM = {"theta": 0.9, "phi": 0.0, "s": 0.4, "alpha_h": 1.0, "alpha_a": 1.5, "beta_r": 0.0, "sigma_y": 0.25, "pi": 0.36, "corner": False}
FAMILIES = {
    # development families
    "D1_anchor_right": {},
    "D2_anchor_partial45": {"phi": 45.0},
    "D3_anchor_useless": {"theta": 0.0, "s": 1.0, "alpha_h": 0.6},
    "D4_weak_aux": {"alpha_a": 0.25, "alpha_h": 1.5},
    "D5_depth_threshold": {"alpha_h": 0.0, "alpha_a": 2.5, "sigma_y": 0.05},
    "D6_aleatoric_corner": {"corner": True},
    # test families (frozen before any test run)
    "T1_anchor_right_moderate": {"theta": 0.7, "s": 0.6, "alpha_h": 0.8, "alpha_a": 1.2, "sigma_y": 0.35, "pi": 0.30},
    "T2_anchor_partial25": {"phi": 25.0, "pi": 0.30},
    "T3_anchor_partial70": {"phi": 70.0, "pi": 0.30},
    "T4_anchor_useless_label_h": {"theta": 0.0, "s": 1.0, "alpha_h": 1.2, "alpha_a": 0.8},
    "T5_no_aux_value": {"alpha_a": 0.0, "alpha_h": 1.2},
    "T6_label_residual": {"beta_r": 0.8},
    "T7_balanced_noisy": {"pi": 0.5, "sigma_y": 0.6},
    "T8_corner_partial45": {"phi": 45.0, "corner": True},
}
DEV = [k for k in FAMILIES if k.startswith("D")]
TEST = [k for k in FAMILIES if k.startswith("T")]
SEEDS_DEV, SEEDS_TEST = (1, 2, 3, 4), (101, 102, 103, 104, 105)
ARMS = ("HONLY_MARGIN", "HA_LEAN_MARGIN", "HA_TREND_MARGIN", "PAC_MARGIN")


def _gp_sample(U, ell, rng):
    d = np.sqrt(np.maximum(((U[:, None, :] - U[None, :, :]) / ell) ** 2, 0).sum(-1)); s3 = np.sqrt(3.0) * d
    K = (1 + s3) * np.exp(-s3) + 1e-8 * np.eye(len(U)); return np.linalg.cholesky(K) @ rng.standard_normal(len(U))


def world(family, seed):
    p = {**BASE_FAM, **FAMILIES[family]}; rng = np.random.default_rng([2424, seed, list(FAMILIES).index(family)])
    U = rng.uniform(-1, 1, (N_WORLD, 4)); X = np.exp(BASE + U); dh = D_H / np.linalg.norm(D_H)
    q = np.array([0.0, 0.0, 0.0, 1.0]); q = q - (q @ dh) * dh; q /= np.linalg.norm(q); ph = np.deg2rad(p["phi"]); dd = np.cos(ph) * dh + np.sin(ph) * q
    std = lambda v: (v - v.mean()) / v.std(); zh = std(U @ D_H); zd = std(U @ dd)
    g = _gp_sample(U, 0.8, rng); r = _gp_sample(U, 0.6, rng); astar = p["theta"] * zd + p["s"] * g
    short = rng.random(N_WORLD) < 0.05; loga = 4.7 + 0.25 * astar + 0.01 * rng.standard_normal(N_WORLD) + np.where(short, 0.3 * rng.standard_normal(N_WORLD), 0.0)
    eta = p["alpha_h"] * zh + p["alpha_a"] * astar + p["beta_r"] * r; noise = p["sigma_y"] * rng.logistic(size=N_WORLD); tau = np.quantile(eta + noise, 1 - p["pi"])
    y = (eta + noise > tau).astype(int); corner = (U[:, 0] > 0.55) & (U[:, 1] > 0.55)
    if p["corner"]:
        y = np.where(corner, rng.integers(0, 2, N_WORLD), y)
    ids = [f"SYN_{family}_s{seed}_{i:03d}" for i in range(N_WORLD)]
    M = pd.DataFrame(index=pd.Index(ids, name="sim_id"))
    M["source_batch"] = "SYN"; M["P"], M["VX"], M["LS"], M["ST"] = X.T; M["y"] = y; M["A_um"] = np.exp(loga)
    for c in P.TARGETS:
        M[c] = np.nan
    M["log_A_um"] = loga; M["short_record"] = short; M["t_end_ms"] = np.where(short, 1.0, 2.1); M["TE_ms"] = 2.1
    M["shortK_pooled"] = False; M["shortK_NEW_original"] = False; M["corner_syn"] = corner
    return M, U, p


def task(M, U, seed, split):
    ids = np.asarray(M.index); n = len(ids); rng = np.random.default_rng([2424, seed, 7 if split == "std" else 8])
    if split == "std":
        test = np.sort(rng.permutation(n)[: n // 5])
    else:
        from sklearn.cluster import KMeans
        Us = (U - U.mean(0)) / U.std(0); lab = KMeans(5, n_init=20, random_state=2424 + seed).fit_predict(Us); y = M.y.to_numpy(int)
        ok = [b for b in range(5) if min(int(y[lab == b].sum()), int((1 - y[lab == b]).sum())) >= 15]
        b = min(ok or range(5), key=lambda b: (abs(y[lab == b].mean() - y.mean()), b)); test = np.flatnonzero(lab == b)
    pool = np.setdiff1d(np.arange(n), test); X = M[["P", "VX", "LS", "ST"]].to_numpy(float)
    path = pool[maximin_order(X[pool], np.random.default_rng([2424, seed, 9]))]
    return {"repeat": int(seed), "fold": 1 if split == "std" else 2, "ids": ids, "X": X, "pool": pool, "test": test, "path": path, "q20": np.zeros(len(test), bool), "split": split}


def run(family, seed, split, arm):
    import src.rc24_pilot as PL
    M, U, p = world(family, seed); t = task(M, U, seed, split); C22.set_manifest(M)
    if arm in ("HONLY_MARGIN", "HA_LEAN_MARGIN"):
        u = C23.run_arm(t, "HONLY_LR" if arm == "HONLY_MARGIN" else "HA_LEAN", M)
    elif arm in ("HA_TREND_MARGIN", "PAC_MARGIN"):
        u = PL.run_pac(t, M, cons=arm.replace("_MARGIN", ""))
    elif arm == "PAC_JEER":
        u = PL.run_jeer(t, M)
    else:
        raise ValueError(arm)
    u.update({"arm": arm, "family": family, "seed": seed, "split": split, "params": p, "positive_rate": float(M.y.mean()),
              "test_corner_share": float(M.corner_syn.to_numpy()[t["test"]].mean())})
    return u


def units(job):
    fams, seeds = (DEV, SEEDS_DEV) if job == "s-dev" else (TEST, SEEDS_TEST) if job == "s-test" else (None, None)
    if job == "s-smoke":
        return [("D1_anchor_right__s1__std__HA_TREND_MARGIN", ("D1_anchor_right", 1, "std", "HA_TREND_MARGIN"))]
    return [(f"{fa}__s{s}__{sp}__{a}", (fa, s, sp, a)) for fa in fams for s in seeds for sp in ("std", "block") for a in ARMS]


def work(job):
    RC.limit_threads(1); U = units(job); S = dict(U)
    if job == "s-test":
        import src.rc24_freeze as FR
        FR.check(job)
    d = OUT / job
    RC.run_units([n for n, _ in U], lambda name: run(*S[name]), d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("s-dev", "s-test", "s-smoke")})
