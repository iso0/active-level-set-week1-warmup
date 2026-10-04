"""Week 15 held-out benchmark families (never used in Week 15 development).

HF1 gpworld   : f ~ GP(m0, Matérn-3/2 ARD, ls = (.4, .6, .8, 2.0), var = 25) in [0,1]^4, y ~ Bernoulli(sigmoid(f));
                the model uses the true prior (well-specified).  m0 in {0, -4} (balanced / ~20% class 1); draws are
                accepted only if the dense class-1 share lies in (.40,.60) resp. (.10,.30) (mild conditioning).
HF2 curvedMono: Week 14 held-out monotone latent with exponent drift, OLD box (18% class 1) or NEW box
                (~9% class 0); iid probit boundary noise sigma in {0, 0.5, 1.0}.
HF3 branin4d  : 2-D Branin basins (3 components) embedded in 4-D with 2 nuisance coordinates, 15% class 1,
                sigma in {0, 0.5}.
HF4 rough     : Week 14 hartmannDev latent on the NEW box plus a *deterministic* rough field
                y = 1[f + sigma g(u) > 0], g a fixed random-Fourier field (length scale 0.05): spatially
                coherent, SPH-like roughness rather than iid noise; sigma in {0.5, 1.0}.
Truth for NSD/ASSD is always the noise-free level set {f = 0} on 8,000 uniform points of the family box.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.linalg import cholesky
from scipy.special import expit, ndtr

from src.week13_synthetic import matern32
from src.week13_synthetic_al import oracle_hypers
from src.week13_synthetic import Scenario
from src.week14_transfer_study import NEW_BOX, OLD_BOX, calibrate, latent as w14_latent
from src.week15_al import POLICIES, DenseEval, knn_graph, run_path, start_design

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week15_boundary_acquisition/heldout"
W_PHYS = np.array([2.2, -.8, -1.2, 0.])
GP_LS, GP_VAR = np.array([.4, .6, .8, 2.0]), 25.0
GP_BANDS = {0.0: (.40, .60), -4.0: (.10, .30)}   # accepted dense class-1 share per draw (rejection sampling)
CELLS = ([("gpworld", {"m0": m0, "pool": n}) for m0 in (0.0, -4.0) for n in (108, 324)] +
         [("curvedMono", {"box": b, "sigma": s, "pool": 108}) for b in ("OLD", "NEW") for s in (0.0, .5, 1.0)] +
         [("curvedMono", {"box": "NEW", "sigma": s, "pool": 324}) for s in (.5, 1.0)] +
         [("branin4d", {"sigma": s, "pool": 108}) for s in (0.0, .5)] +
         [("rough", {"sigma": s, "pool": 108}) for s in (.5, 1.0)])
HELDOUT_POLICIES = ("random", "margin", "coverage", "bald", "ebrd", "vsur")


def branin(u):
    x1, x2 = 15 * u[:, 0] - 5, 15 * u[:, 1]
    return (x2 - 5.1 / (4 * np.pi ** 2) * x1 ** 2 + 5 / np.pi * x1 - 6) ** 2 + 10 * (1 - 1 / (8 * np.pi)) * np.cos(x1) + 10


BRANIN_T = float(np.quantile(branin(np.random.default_rng(1).random((200000, 4))), .15))


def rough_field(rng, n_feat=200, ls=.05):
    W = rng.standard_normal((n_feat, 4)) / ls
    W[:, 3] = 0.0                          # ST-like coordinate stays smooth
    b = rng.uniform(0, 2 * np.pi, n_feat)
    a = np.sqrt(2 / n_feat)
    return lambda z: a * np.cos(z @ W.T + b).sum(1)


def make_cell(fam, cfg, rep):
    """Return everything run_path needs, in unit-box model coordinates z."""
    rng = np.random.default_rng([152, ("gpworld", "curvedMono", "branin4d", "rough").index(fam), int(cfg.get("m0", 0) * 10) + 100,
                                 int(cfg.get("sigma", 0) * 10), cfg["pool"], ("OLD", "NEW").index(cfg.get("box", "OLD")), rep])
    n = cfg["pool"]; ne = int(round(n / .8))
    if fam == "gpworld":
        zall = rng.random((8000 + n + ne, 4))
        # exact joint draw is too large; draw on pool+eval+3000 dense jointly, evaluate truth on those 3000
        zd = zall[:3000]; zp = zall[8000:8000 + n]; ze = zall[8000 + n:]
        Z = np.vstack([zd, zp, ze])
        C = cholesky(matern32(Z, Z, GP_LS, GP_VAR) + 1e-8 * np.eye(len(Z)), lower=True)
        lo, hi = GP_BANDS[cfg["m0"]]
        for _ in range(1000):
            f = cfg["m0"] + C @ rng.standard_normal(len(Z))
            if lo < np.mean(f[:3000] > 0) < hi:
                break
        fd, fp, fe = f[:3000], f[3000:3000 + n], f[3000 + n:]
        yp = (rng.random(n) < expit(fp)).astype(int); ye = (rng.random(ne) < expit(fe)).astype(int)
        hyp = {"ls": GP_LS.tolist(), "var": GP_VAR, "m0": cfg["m0"]}
        return dict(z_pool=zp, y_pool=yp, f_pool=fp, s_pool=None, z_eval=ze, y_eval=ye,
                    dense=DenseEval(zd, (fd > 0).astype(int)), hyp=hyp)
    if fam in ("curvedMono", "rough"):
        famw14 = "curvedMono" if fam == "curvedMono" else "hartmannDev"
        par = PARS[famw14]
        box = OLD_BOX if cfg.get("box", "NEW") == "OLD" else NEW_BOX
        sample = lambda m, r: box[0] + (box[1] - box[0]) * r.random((m, 4))
        up, ue = sample(n, rng), sample(ne, rng)
        ud = sample(8000, np.random.default_rng(5))
        fz = lambda u: w14_latent(u, famw14, par)
        tz = lambda u: (u - box[0]) / (box[1] - box[0])
        if fam == "curvedMono":
            yp = (fz(up) + cfg["sigma"] * rng.standard_normal(n) > 0).astype(int)
            ye = (fz(ue) + cfg["sigma"] * rng.standard_normal(ne) > 0).astype(int)
        else:
            g = rough_field(np.random.default_rng([153, rep]))
            yp = (fz(up) + cfg["sigma"] * g(tz(up)) > 0).astype(int)
            ye = (fz(ue) + cfg["sigma"] * g(tz(ue)) > 0).astype(int)
        return dict(z_pool=tz(up), y_pool=yp, f_pool=fz(up), s_pool=up @ W_PHYS, z_eval=tz(ue), y_eval=ye,
                    dense=DenseEval(tz(ud), (fz(ud) > 0).astype(int)), hyp=None, box=box, famw14=famw14, par=par)
    if fam == "branin4d":
        fz = lambda u: (BRANIN_T - branin(u)) / 20.0
        up, ue, ud = rng.random((n, 4)), rng.random((ne, 4)), np.random.default_rng(5).random((8000, 4))
        yp = (fz(up) + cfg["sigma"] * rng.standard_normal(n) > 0).astype(int)
        ye = (fz(ue) + cfg["sigma"] * rng.standard_normal(ne) > 0).astype(int)
        return dict(z_pool=up, y_pool=yp, f_pool=fz(up), s_pool=None, z_eval=ue, y_eval=ye,
                    dense=DenseEval(ud, (fz(ud) > 0).astype(int)), hyp=None)
    raise ValueError(fam)


def cell_key(fam, cfg):
    return f"{fam}|" + "|".join(f"{k}={v}" for k, v in sorted(cfg.items()))


def hypers_for(fam, cfg):
    """Oracle fixed hyperparameters (ML-II once on 500 labelled cases of the family), as in Weeks 13-14."""
    if fam == "gpworld":
        return {"ls": GP_LS.tolist(), "var": GP_VAR, "m0": cfg["m0"]}
    rng = np.random.default_rng([154, sum(map(ord, cell_key(fam, cfg)))])
    if fam in ("curvedMono", "rough"):
        famw14 = "curvedMono" if fam == "curvedMono" else "hartmannDev"
        par = PARS[famw14]; box = OLD_BOX if cfg.get("box", "NEW") == "OLD" else NEW_BOX
        u = box[0] + (box[1] - box[0]) * rng.random((500, 4)); z = (u - box[0]) / (box[1] - box[0])
        if fam == "curvedMono":
            y = (w14_latent(u, famw14, par) + cfg["sigma"] * rng.standard_normal(500) > 0).astype(int)
        else:
            g = rough_field(np.random.default_rng([153, 10 ** 6]))
            y = (w14_latent(u, famw14, par) + cfg["sigma"] * g(z) > 0).astype(int)
    else:
        z = rng.random((500, 4)); y = ((BRANIN_T - branin(z)) / 20 + cfg["sigma"] * rng.standard_normal(500) > 0).astype(int)
    from sklearn.gaussian_process import GaussianProcessClassifier
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        g = GaussianProcessClassifier(ConstantKernel(4.0, (0.05, 400)) * Matern([0.3] * 4, (0.02, 50), nu=1.5),
                                      n_restarts_optimizer=2, random_state=0).fit(z, y)
    return {"ls": np.asarray(g.kernel_.k2.length_scale, float).tolist(), "var": float(g.kernel_.k1.constant_value)}


PARS: dict = {}


def job(fam, cfg, rep, policy, hyp, pars, out_dir=None):
    """One path; if out_dir is given the rows are written to their own file and existing files are reused
    (resumable execution; results are identical to a single run because every path is seeded independently)."""
    if out_dir is not None:
        dest = Path(out_dir) / (cell_key(fam, cfg).replace("|", "__").replace("=", "-") + f"__r{rep}__{policy}.csv")
        if dest.exists():
            return pd.read_csv(dest).to_dict("records")
        rows = job(fam, cfg, rep, policy, hyp, pars)
        pd.DataFrame(rows).to_csv(dest, index=False)
        return rows
    PARS.update(pars)
    c = make_cell(fam, cfg, rep)
    Zref = np.random.default_rng([15, 99]).random((400, 4)); Eref = knn_graph(Zref, 8)
    start = start_design(c["z_pool"], c["y_pool"], [152, rep, 2])
    gen = {"family": fam, **{f"cfg_{k}": v for k, v in cfg.items()}, "cell": cell_key(fam, cfg), "rep": rep, "startup": len(start)}
    return run_path(gen, policy, c["z_pool"], None, c["y_pool"], c["f_pool"], c["s_pool"], c["z_eval"], c["y_eval"],
                    c["dense"], Zref, Eref, hyp, start, [152, rep, HELDOUT_POLICIES.index(policy)])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--reps", type=int, default=8); ap.add_argument("--tag", default="confirm")
    ap.add_argument("--cells", default="all"); ap.add_argument("--policies", default=",".join(HELDOUT_POLICIES)); a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for f in ("curvedMono", "hartmannDev"):
        PARS[f] = calibrate(f)
    hf = OUT / "hyperparameters.json"
    H = json.loads(hf.read_text()) if hf.exists() else {}
    for fam, cfg in CELLS:
        k = cell_key(fam, cfg)
        if k not in H:
            H[k] = hypers_for(fam, cfg)
    hf.write_text(json.dumps(H, indent=2))
    cells = CELLS if a.cells == "all" else [CELLS[int(i)] for i in a.cells.split(",")]
    jobs = [(fam, cfg, r, p) for p in a.policies.split(",") for fam, cfg in cells for r in range(a.reps)]
    jobs.sort(key=lambda j: (j[3] not in ("ebrd", "vsur"), -j[1]["pool"]))   # heavy jobs first
    pdir = OUT / f"paths_{a.tag}"; pdir.mkdir(exist_ok=True)
    res = Parallel(n_jobs=7, verbose=2)(delayed(job)(fam, cfg, r, p, H[cell_key(fam, cfg)], PARS, pdir) for fam, cfg, r, p in jobs)
    df = pd.DataFrame([x for rows in res for x in rows]); df.to_csv(OUT / f"al_{a.tag}.csv.gz", index=False)


if __name__ == "__main__":
    main()
