"""Week 15 held-out check of DC-BD (run only after the freeze).

Shapes (never used for DC-BD development): sphere d = 3 and d = 5 (10% volume), two-component d = 3
(Week 14 held-out shapes).  Densities: uniform; smooth bumps (scale 0.15) on the boundary in the half
u0 < 0.5 (smoothA) or u0 >= 0.5 (smoothB) — theory-compatible; thin bands (Week 14 denseA/denseB) —
theory-violating.  Predictors: Week 14 held-out predictor family (displacement, sector errors, island,
perturbation, constant).
"""
from pathlib import Path
import math
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from src.week13_boundary_metrics import edge_metrics, gabriel_edges, nearest_opposite
from src.week14_metric_confirm import PREDS, Truth, f_true, predictor, sample as w14_sample
from src.week14_metrics import weighted_edge_metrics
from src.week15_metric import dc_boundary_dice

OUT = Path(__file__).resolve().parents[1] / "outputs/week15_boundary_acquisition/heldout"
DESIGNS = ("uniform", "smoothA", "smoothB", "denseA", "denseB")


def smooth(n, d, shape, side, rng):
    out = []
    while len(out) < n:
        u = rng.random((6 * n, d))
        half = (u[:, 0] < .5) if side == "A" else (u[:, 0] >= .5)
        dens = 1 + 6 * np.exp(-f_true(u, shape) ** 2 / (2 * .15 ** 2)) * half
        out.extend(u[rng.random(6 * n) < dens / 7])
    return np.asarray(out[:n])


def cell(d, shape, design, n, rep, tm):
    rng = np.random.default_rng([155, d, ("sphere", "twocomp").index(shape), DESIGNS.index(design), n, rep])
    u = rng.random((n, d)) if design == "uniform" else (smooth(n, d, shape, design[-1], rng) if design.startswith("smooth") else w14_sample(n, d, shape, design, rng))
    y = (f_true(u, shape) > 0).astype(int)
    if y.min() == y.max():
        return [{"d": d, "shape": shape, "design": design, "n": n, "rep": rep, "pred": "SKIPPED_single_class"}]
    z = StandardScaler().fit_transform(u)
    dist, _ = nearest_opposite(z, y)
    q = np.zeros(n, bool); q[np.argsort(dist, kind="stable")[:math.ceil(.2 * n)]] = True
    e = gabriel_edges(z)
    rows = []
    for k, a in PREDS:
        yh = predictor(u, shape, k, a)
        rows.append({"d": d, "shape": shape, "design": design, "n": n, "rep": rep, "pred": k, "amount": a, **tm[(k, a)],
                     "q20_accuracy": float(np.mean(yh[q] == y[q])),
                     "full_BA": float((np.mean(yh[y == 1] == 1) + np.mean(yh[y == 0] == 0)) / 2),
                     "BEF1": edge_metrics(e, y, yh)["BEF1"], "wBEF1": weighted_edge_metrics(e, z, y, yh)["wBEF1"],
                     "BD_unweighted": dc_boundary_dice(z, y, yh, weighted=False)["DC_BD"], "DC_BD": dc_boundary_dice(z, y, yh)["DC_BD"]})
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for d, shape in ((3, "sphere"), (5, "sphere"), (3, "twocomp")):
        truth = Truth(d, shape)
        tm = {(k, a): truth.metrics(predictor(truth.u, shape, k, a)) for k, a in PREDS}
        res = Parallel(n_jobs=7)(delayed(cell)(d, shape, des, n, rep, tm) for des in DESIGNS for n in (136, 405) for rep in range(20))
        rows += [x for r in res for x in r]
    df = pd.DataFrame(rows); df.to_csv(OUT / "metric_confirm.csv.gz", index=False)


if __name__ == "__main__":
    main()
