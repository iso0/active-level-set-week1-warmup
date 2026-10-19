"""RC19B exploratory path diagnostic (evaluator-side; not part of the frozen verdicts): where does each final Keyhole arm spend its
queries? For every trajectory and budget b in (16, 24, 40, 60): share of paid runs that are Keyhole, share inside the fast-scan
conduction corner (NEW-batch conduction runs; batch is provenance and is used here only by the evaluator), and the median input
distance of the paid runs to the nearest opposite-class run (a boundary-proximity proxy computed on the whole pool).
    python -m src.rc19b_paths      -> opus_rc19b/report/PATHS_DIAGNOSTIC.md (+ csv)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc19_pool as P
from src.rc19_report import md

OUT = RC.ROOT / "outputs" / "research_campaign_20261018" / "opus_rc19b"
REP = OUT / "report"


def main():
    M = P.manifest(); ids = M.index.to_numpy(str); pos = {s: i for i, s in enumerate(ids)}
    Z = np.log(M[list(P.INPUTS)].to_numpy(float)); Z = (Z - Z.mean(0)) / Z.std(0); y = M.y.to_numpy(int)
    corner = ((M.source_batch == "NEW") & (M.y == 0)).to_numpy()
    d_opp = np.array([np.min(np.linalg.norm(Z[y != y[i]] - Z[i], axis=1)) for i in range(len(y))])
    rows = []
    for u in EV.load_units(OUT / "b-final-label"):
        p = np.asarray([pos[s] for s in u["paid_ids"]])
        for b in (16, 24, 40, 60):
            q = p[:b]
            rows.append({"arm": u["arm"], "repeat": u["repeat"], "fold": u["fold"], "budget": b, "keyhole_share": float(y[q].mean()), "corner_paid": int(corner[q].sum()),
                         "median_dist_to_opposite_class": float(np.median(d_opp[q]))})
    D = pd.DataFrame(rows); D.to_csv(REP / "paths_diagnostic.csv", index=False, lineterminator="\n")
    S = D.groupby(["arm", "budget"]).agg(keyhole_share=("keyhole_share", "mean"), corner_paid_mean=("corner_paid", "mean"), corner_paid_max=("corner_paid", "max"),
                                         median_dist_to_opposite=("median_dist_to_opposite_class", "mean")).reset_index()
    pool_corner = int(corner.sum())
    L = ["# RC19B path diagnostic (exploratory, evaluator-side): where the final Keyhole arms spend their queries", "",
         f"Pool: {len(y)} runs, Keyhole share {y.mean():.3f}; fast-scan conduction corner = {pool_corner} runs ({pool_corner / len(y):.1%}). "
         f"Distance = standardised log-input distance to the nearest run of the other class (pool median {np.median(d_opp):.3f}; smaller = nearer the boundary). "
         "Means over 40 trajectories (8 repeats × 5 folds) per arm.", "", md(S, 3), ""]
    (REP / "PATHS_DIAGNOSTIC.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L))


if __name__ == "__main__":
    main()
