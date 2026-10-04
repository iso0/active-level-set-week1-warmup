"""Week 16 — audit of the Week 13 undamped Laplace iteration on the Week 15 benchmark.

For every development and held-out cell (reps 0-7) the Week 15 margin path is replayed with the original fit;
at every step the fixed-point error of the base fit, and of 6 sampled fantasy refits (the fits used by VSUR,
EBR-D and the expectation oracle), is recorded.  A fit counts as failed if its latent deviation at the training inputs differs from the safeguarded mode by more
than 1e-6.  The same
path is then replayed with the safeguarded fit to measure the effect on margin's NSD trace."""
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from src.week16_cells import ALL_CELLS, build, cell_key, margin_pick, margin_states, pars
from src.week16_peer import Model, mode_gap as fixed_point_error

OUT = Path(__file__).resolve().parents[1] / "outputs/week16_theory_meets_data/laplace_audit"


def one(fam, cfg, rep, P):
    c = build(fam, cfg, rep, P)
    old, new = Model.from_hyp(c["hyp"], robust=False), Model.from_hyp(c["hyp"])
    z, y = c["z_pool"], c["y_pool"]
    rng = np.random.default_rng([16, 7, rep])
    L = list(c["start"]); base_fail = refit_fail = refit_n = steps = 0
    while True:
        post = old.fit(z[L], y[L]); steps += 1
        base_fail += fixed_point_error(post.gp) > 1e-6
        cands = np.setdiff1d(np.arange(len(z)), L)
        for j in rng.choice(cands, 3, replace=False):
            for lab in (0, 1):
                refit_fail += fixed_point_error(old.fit(z[np.r_[L, j]], np.r_[y[L], lab]).gp) > 1e-6; refit_n += 1
        if len(L) >= 80:
            break
        L.append(margin_pick(post, z, cands))
    _, t_old = margin_states(c, (), old); _, t_new = margin_states(c, (), new)
    d = [t_new[b]["NSD_0.1"] - t_old[b]["NSD_0.1"] for b in t_old]
    return {"cell": cell_key(fam, cfg), "rep": rep, "steps": steps, "base_fail_frac": base_fail / steps,
            "refit_fail_frac": refit_fail / refit_n, "margin_nsd_aulc_old": float(np.mean([t_old[b]["NSD_0.1"] for b in t_old])),
            "margin_nsd_aulc_fixed": float(np.mean([t_new[b]["NSD_0.1"] for b in t_new])), "max_abs_nsd_change": float(np.max(np.abs(d)))}


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    P = pars()
    rows = Parallel(n_jobs=7, verbose=2)(delayed(one)(f, c, r, P) for f, c in ALL_CELLS for r in range(8))
    df = pd.DataFrame(rows); df.to_csv(OUT / "synthetic_paths.csv", index=False)
    print(df.groupby("cell")[["base_fail_frac", "refit_fail_frac", "margin_nsd_aulc_old", "margin_nsd_aulc_fixed", "max_abs_nsd_change"]].mean().round(3).to_string())


# ----------------------------------------------------------------------------- other users of the same fit
def audit_week13_models(reps=6):
    """Week 13 generic (G) and physics-trend (M3-type) synthetic models on random labelled subsets of the
    Week 13 pools (sizes 16-80); hyperparameters from the Week 13 oracle file."""
    import json
    from src.week13_synthetic import LaplaceGPC
    from src.week13_synthetic_al import Model as W13Model, calibrated, noisy_labels, to_box
    hyp = json.loads((Path(__file__).resolve().parents[1] / "outputs/week13_boundary_evaluation_and_mechanisms/synthetic/oracle_hyperparameters.json").read_text())
    rows = []
    for scn in ("BAL", "OLD", "NEW"):
        for sigma in (0.0, 0.5, 1.0):
            key = f"{scn}_s{sigma}"
            if key not in hyp:
                continue
            sc = calibrated(scn)
            for rep in range(reps):
                rng = np.random.default_rng([16, 13, rep, int(sigma * 10), ("BAL", "OLD", "NEW").index(scn)])
                u = sc.sample(108, rng); y = noisy_labels(u, sc, sigma, rng); z = to_box(u, sc)
                for n in (16, 32, 48, 64, 80):
                    idx = rng.choice(108, n, replace=False)
                    if len(set(y[idx])) < 2:
                        continue
                    for kind in ("G", "M"):
                        m = W13Model(kind, hyp[key], sc).fit(z[idx], u[idx], y[idx])
                        rows.append({"source": "week13_synthetic", "cell": key, "model": kind, "n": n, "fail": fixed_point_error(m.gp) > 1e-6})
    return rows


def audit_week15_wellspec(reps=8):
    from scipy.linalg import cholesky
    from scipy.special import expit
    from src.week13_synthetic import LaplaceGPC, matern32
    HYP = {"ls": [.35, .5, .7], "var": 9.0}
    rows = []
    for rep in range(reps):
        rng = np.random.default_rng([15, 77, rep])
        zd, zp = rng.random((1500, 3)), rng.random((108, 3))
        allz = np.vstack([zd, zp])
        C = cholesky(matern32(allz, allz, np.array(HYP["ls"]), HYP["var"]) + 1e-8 * np.eye(1608), lower=True)
        f = C @ rng.standard_normal(1608); yp = (rng.random(108) < expit(f[1500:])).astype(int)
        for n in (12, 20, 35, 50):
            idx = rng.choice(108, n, replace=False)
            gp = LaplaceGPC(HYP["ls"], HYP["var"]).fit(zp[idx], yp[idx])
            rows.append({"source": "week15_wellspec_gp3d", "cell": "gp3d", "model": "G", "n": n, "fail": fixed_point_error(gp) > 1e-6})
    return rows


def audit_week15_real():
    """Margin paths of the Week 15 NEW-136 / OLD-405 replays (G3 hypers fitted on OLD, zero mean)."""
    import json
    from sklearn.preprocessing import StandardScaler
    from src.week13_synthetic import LaplaceGPC
    from src.week15_real import F, W12, g3_hypers
    root = Path(__file__).resolve().parents[1]
    hyp = json.loads((root / "outputs/week15_boundary_acquisition/real_data/hyperparameters.json").read_text())["OLD_G3_ML2"]
    old = pd.read_csv(W12 / "audit/old405_inputs_labels.csv"); new = pd.read_csv(W12 / "audit/new136.csv")
    sc = StandardScaler().fit(old[F]); zn = sc.transform(new[F]); yn = new.has_keyhole.to_numpy()
    splits = json.loads((W12 / "audit/original_splits.json").read_text())
    rows = []
    for s in splits[:20]:
        tr = np.asarray(s["train_indices"]); z, y = zn[tr], yn[tr]
        rng = np.random.default_rng([16, 3, s["repeat"], s["fold"]])
        for n in (16, 32, 48, 64, 80):
            idx = rng.choice(len(tr), n, replace=False)
            if len(set(y[idx])) < 2:
                continue
            gp = LaplaceGPC(hyp["ls"], hyp["var"]).fit(z[idx], y[idx])
            rows.append({"source": "week15_real_NEW", "cell": "NEW136_G3", "model": "G", "n": n, "fail": fixed_point_error(gp) > 1e-6})
    return rows


def audit_other():
    df = pd.DataFrame(audit_week13_models() + audit_week15_wellspec() + audit_week15_real())
    df.to_csv(OUT / "other_users.csv", index=False)
    return df.groupby(["source", "model"]).fail.agg(["mean", "size"])
