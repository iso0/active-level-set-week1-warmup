"""Week 18 theory check T18-5: ML-II hyperparameters under boundary-concentrated vs random designs (deterministic labels).

For a truth with latent f, compare the G3 ML-II optimum fitted on (a) b pool points drawn uniformly at random and
(b) the b pool points with the smallest |f| (an idealized margin design: every point next to the boundary).
Records amplitude, length-scales, log evidence and the test balanced accuracy of each fit, and the accuracy of
the boundary design re-fitted with the random design's hyperparameters (and vice versa) — the part of any
difference that is due to the hyperparameters rather than to the data.
Truths: twins T_GP / T_TOBIT (pooled, OLD; DEV reps 0–3) and real OLD (latent = full-data G3 latent, POST-HOC).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week18_independent_research/phase4"


def _fit(X, y, rows, pool, kernel=None):
    import src.week17_models as M
    import src.week18_engine as E
    return M.fit("G3", X, E.logh(X), y, pool, rows, kernel=kernel)


def _ba(f, X, y, idx):
    import src.week18_engine as E
    p = E.proba(f, X[idx]) >= .5
    yy = y[idx]
    return float((np.mean(p[yy == 1]) + np.mean(~p[yy == 0])) / 2)


def job(name, rep, X, y, lat, pool, test, b):
    from threadpoolctl import threadpool_limits
    import src.week17_models as M
    rng = np.random.default_rng([1830, rep, b])
    designs = {"random": rng.choice(pool, b, replace=False), "boundary": pool[np.argsort(np.abs(lat[pool]))[:b]]}
    out, fits = [], {}
    with threadpool_limits(1):
        for d, rows in designs.items():
            if len(set(y[rows])) < 2:
                return []
            f = _fit(X, y, rows, pool); fits[d] = f
            hs = M.hyper_summary(f)
            out.append({"truth": name, "rep": rep, "b": b, "design": d, "BA": _ba(f, X, y, test), **hs,
                        "fp": float(f.gp.mode_fp_)})
        for d, other in (("random", "boundary"), ("boundary", "random")):
            f = _fit(X, y, designs[d], pool, kernel=_copy(fits[other].gp.kernel_))
            out.append({"truth": name, "rep": rep, "b": b, "design": f"{d}@{other}_hypers", "BA": _ba(f, X, y, test), "fp": float(f.gp.mode_fp_)})
    return out


def _copy(k):
    from sklearn.base import clone
    c = clone(k); c.theta = k.theta
    return c


def tasks():
    import src.week18_twins as W
    import src.week18_tasks as T
    import src.week18_engine as E
    import src.week17_models as M
    J = []
    for tw, d, n in (("T_GP", "pooled", 433), ("T_GP", "OLD", 324), ("T_TOBIT", "pooled", 433), ("T_TOBIT", "OLD", 324)):
        f = W.truth(tw)
        for rep in range(4):
            t = W.twin_task(tw, d, n, rep)
            lat = f(t["z_of"](t["X"]))
            for b in (40, 80, 120):
                J.append((f"{tw}_{d}", rep, t["X"], t["y"], lat, t["pool"], t["test"], b))
    for t in [t for t in T.r3_old_tasks() if t["block"] == "DEV" and t["fold"] == 1][:4]:
        allrows = np.r_[t["pool"], t["test"]]
        g = M.fit("G3", t["X"], E.logh(t["X"]), t["y"], t["pool"], allrows)
        lat = np.asarray(E.latent(g, t["X"])[0])
        for b in (40, 80, 120):
            J.append(("REAL_OLD", t["repeat"], t["X"], t["y"], lat, t["pool"], t["test"], b))
    return J


def main(n_jobs=1):
    OUT.mkdir(parents=True, exist_ok=True)
    res = Parallel(n_jobs=n_jobs, verbose=5)(delayed(job)(*a) for a in tasks())
    df = pd.DataFrame([r for rr in res for r in rr]); df.to_csv(OUT / "mlii_design_bias.csv", index=False)
    return df


if __name__ == "__main__":
    import sys
    df = main(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    pd.set_option("display.width", 220)
    cols = [c for c in df.columns if c.startswith("hp_") or c in ("BA", "lml")]
    print(df.groupby(["truth", "b", "design"])[cols].median().round(3).to_string())
