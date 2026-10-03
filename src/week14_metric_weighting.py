"""Week 14 Study 3b — does length weighting remove density-induced rank reversals? (CONTROLLED SYNTHETIC)"""
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.preprocessing import StandardScaler
from src.week13_boundary_metrics import edge_metrics, gabriel_edges, knn_edges
from src.week14_metrics import weighted_edge_metrics
from src.week14_metric_study import Truth, predictor, sample

OUT = Path(__file__).resolve().parents[1] / "outputs/week14_research_program/synthetic/metrics"


def main():
    rows = []
    preds = [("left_error", .05), ("right_error", .05), ("left_error", .1), ("right_error", .1),
             ("displace", .02), ("displace", -.02), ("island", .06), ("constant", 0)]
    for d in (2, 4):
        truth = Truth(d)
        tm = {(k, a): truth.metrics(predictor(truth.u, k, a)) for k, a in preds}
        for density in ("uniform", "dense_left", "dense_right"):
            for n in (136, 405):
                for rep in range(30):
                    rng = np.random.default_rng([8, d, ("uniform", "dense_left", "dense_right").index(density), n, rep])
                    u = sample(n, d, density, rng)
                    y = (np.asarray(u[:, 1] - (.35 + .3 * (u[:, 0] - .5) ** 2 + .05 * np.sin(6 * u[:, 0]))) > 0).astype(int)
                    if y.min() == y.max():
                        continue
                    z = StandardScaler().fit_transform(u)
                    graphs = {"gabriel": gabriel_edges(z), "knn5": knn_edges(z, 5)}
                    for k, a in preds:
                        yh = predictor(u, k, a)
                        r = {"d": d, "density": density, "n": n, "rep": rep, "pred": k, "amount": a, **tm[(k, a)]}
                        for g, e in graphs.items():
                            m = edge_metrics(e, y, yh)
                            r[f"{g}_BER"], r[f"{g}_BEF1"] = m["BER"], m["BEF1"]
                            wm = weighted_edge_metrics(e, z, y, yh)
                            r[f"{g}_wBER"], r[f"{g}_wBEF1"] = wm["wBER"], wm["wBEF1"]
                        rows.append(r)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "weighting_study.csv.gz", index=False)
    cols = [c for c in df.columns if c.endswith(("BER", "BEF1"))] + ["NSD", "ASSD"]
    pd.set_option("display.width", 250)
    print(df[df.n == 405].groupby(["d", "density", "pred", "amount"])[cols].mean().round(3).to_string())
    # density sensitivity: |left - right| for equal-geometry errors, by metric
    piv = df[df.pred.isin(["left_error", "right_error"])].groupby(["d", "n", "density", "amount", "pred"])[cols].mean()
    sens = (piv.xs("left_error", level="pred") - piv.xs("right_error", level="pred")).abs()
    print(sens.groupby(["d", "density"]).mean().round(3).to_string())
    sens.to_csv(OUT / "weighting_density_sensitivity.csv")


if __name__ == "__main__":
    main()
