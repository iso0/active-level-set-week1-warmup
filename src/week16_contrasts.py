"""Week 16 — one-step oracle value of margin vs PEER-argmax vs a random candidate, with cluster-bootstrap CIs
(clusters = (cell, rep) paths; descriptive, no confirmatory claim)."""
from pathlib import Path

import numpy as np
import pandas as pd

W = Path(__file__).resolve().parents[1] / "outputs/week16_theory_meets_data"


def boot(df, col, n=4000, seed=0):
    g = df.groupby(["cell", "rep"])[col].mean().values
    b = np.random.default_rng(seed).choice(g, (n, len(g))).mean(1)
    return float(g.mean()), float(np.quantile(b, .025)), float(np.quantile(b, .975)), len(g)


def main():
    C = pd.read_csv(W / "headroom/candidates.csv.gz")
    S = pd.read_csv(W / "headroom/states.csv")[["cell", "rep", "budget", "family"]]
    C = C.merge(S, on=["cell", "rep", "budget"])
    rows = []
    for (fam, cell, rep, b), g in C.groupby(["family", "cell", "rep", "budget"]):
        jm = g.Vref.idxmax(); jp = g.Vpool.idxmax()
        r = {"family": fam, "cell": cell, "rep": rep, "budget": b}
        for vt in ("Vt_ham_ref", "Vt_ham_pool", "Vt_nsd"):
            m = g.loc[g.is_margin, vt].iloc[0]
            r.update({f"{vt}|margin": m, f"{vt}|peer_ref": g.loc[jm, vt], f"{vt}|peer_pool": g.loc[jp, vt], f"{vt}|random": g[vt].mean(),
                      f"{vt}|max": g[vt].max(), f"{vt}|peer_minus_margin": g.loc[jm, vt] - m, f"{vt}|margin_minus_random": m - g[vt].mean()})
        rows.append(r)
    P = pd.DataFrame(rows); P.to_csv(W / "headroom/pick_values.csv", index=False)
    out = []
    groups = [("family", f, P[P.family == f]) for f in P.family.unique()] + [("cell", c, P[P.cell == c]) for c in P.cell.unique()]
    for kind, name, g in groups:
        for vt in ("Vt_ham_ref", "Vt_nsd"):
            for contrast in ("peer_minus_margin", "margin_minus_random"):
                m, lo, hi, n = boot(g, f"{vt}|{contrast}")
                out.append({"level": kind, "group": name, "objective": vt, "contrast": contrast, "mean": m, "lo": lo, "hi": hi, "paths": n})
    O = pd.DataFrame(out); O.to_csv(W / "headroom/pick_contrasts.csv", index=False)
    return P, O


if __name__ == "__main__":
    P, O = main()
    pd.set_option("display.width", 200)
    f = O[O.level == "family"].copy(); f[["mean", "lo", "hi"]] *= 400
    print("family level, x400 (ham: points of 400; nsd: x400 too)"); print(f.round(3).to_string(index=False))
    c = O[(O.level == "cell") & (O.objective == "Vt_ham_ref") & (O.contrast == "peer_minus_margin")].copy(); c[["mean", "lo", "hi"]] *= 400
    print(c.sort_values("mean").round(3).to_string(index=False))
