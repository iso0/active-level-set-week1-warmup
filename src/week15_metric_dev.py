"""Week 15 metric development (Week 14 development shape: curved boundary, d = 2, 4).

Densities: uniform; smooth bumps near the left/right half of the boundary (scale 0.15, theory-compatible);
thin bands (Week 14 dense_left/right, theory-violating).  Equal-geometry left/right errors measure density
sensitivity; rank agreement with ASSD measures validity.
"""
from pathlib import Path
import math
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from src.week13_boundary_metrics import edge_metrics, gabriel_edges, nearest_opposite
from src.week14_metrics import weighted_edge_metrics
from src.week14_metric_study import Truth, f_true, predictor, sample as band_sample
from src.week15_metric import dc_boundary_dice

OUT = Path(__file__).resolve().parents[1] / "outputs/week15_boundary_acquisition/development"


def smooth_sample(n, d, side, rng):
    cx = .25 if side == "L" else .75
    out = []
    while len(out) < n:
        u = rng.random((4 * n, d))
        yb = .35 + .3 * (u[:, 0] - .5) ** 2 + .05 * np.sin(6 * u[:, 0])
        dens = 1 + 6 * np.exp(-((u[:, 0] - cx) ** 2 + (u[:, 1] - yb) ** 2) / (2 * .15 ** 2))
        keep = rng.random(4 * n) < dens / 7
        out.extend(u[keep])
    return np.asarray(out[:n])


def sample(n, d, design, rng):
    if design == "uniform":
        return rng.random((n, d))
    if design in ("smoothL", "smoothR"):
        return smooth_sample(n, d, design[-1], rng)
    return band_sample(n, d, "dense_left" if design == "bandL" else "dense_right", rng)


PREDS = [("left_error", .05), ("right_error", .05), ("left_error", .1), ("right_error", .1), ("displace", .02),
         ("displace", -.04), ("island", .06), ("constant", 0)]


def main():
    rows = []
    for d in (2, 4):
        truth = Truth(d)
        tm = {(k, a): truth.metrics(predictor(truth.u, k, a)) for k, a in PREDS}
        for design in ("uniform", "smoothL", "smoothR", "bandL", "bandR"):
            for n in (136, 405):
                for rep in range(20):
                    rng = np.random.default_rng([151, d, n, rep, ("uniform", "smoothL", "smoothR", "bandL", "bandR").index(design)])
                    u = sample(n, d, design, rng)
                    y = (f_true(u) > 0).astype(int)
                    z = StandardScaler().fit_transform(u)
                    dist, _ = nearest_opposite(z, y)
                    q = np.zeros(n, bool); q[np.argsort(dist, kind="stable")[:math.ceil(.2 * n)]] = True
                    e = gabriel_edges(z)
                    for k, a in PREDS:
                        yh = predictor(u, k, a)
                        r = {"d": d, "design": design, "n": n, "rep": rep, "pred": k, "amount": a, **tm[(k, a)],
                             "q20_accuracy": float(np.mean(yh[q] == y[q])),
                             "full_BA": float((np.mean(yh[y == 1] == 1) + np.mean(yh[y == 0] == 0)) / 2),
                             "BEF1": edge_metrics(e, y, yh)["BEF1"], "wBEF1": weighted_edge_metrics(e, z, y, yh)["wBEF1"],
                             "DC_BD": dc_boundary_dice(z, y, yh)["DC_BD"], "BD_unweighted": dc_boundary_dice(z, y, yh, weighted=False)["DC_BD"]}
                        rows.append(r)
    df = pd.DataFrame(rows); OUT.mkdir(parents=True, exist_ok=True); df.to_csv(OUT / "metric_dev.csv.gz", index=False)
    mets = ["q20_accuracy", "full_BA", "BEF1", "wBEF1", "BD_unweighted", "DC_BD", "NSD"]
    sec = df[df.pred.isin(["left_error", "right_error"])].groupby(["d", "design", "n", "amount", "pred"])[mets].mean()
    sens = (sec.xs("left_error", level="pred") - sec.xs("right_error", level="pred")).abs().groupby(["d", "design"]).mean()
    agree = []
    for key, g in df.groupby(["d", "design", "n", "rep"]):
        agree.append({**dict(zip(["d", "design", "n", "rep"], key)), **{m: spearmanr(g[m], -g.ASSD).statistic for m in mets}})
    A = pd.DataFrame(agree).groupby(["d", "design"])[mets].mean()
    pd.set_option("display.width", 220)
    print("density sensitivity |left - right|"); print(sens.round(3).to_string())
    print("rank agreement with -ASSD"); print(A.round(3).to_string())


if __name__ == "__main__":
    main()
