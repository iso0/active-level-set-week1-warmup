"""Week 15 expectation-oracle reference on two held-out cells (unattainable; knows the truth)."""
import json
from pathlib import Path
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from scipy.special import expit, ndtr
import src.week15_heldout as H
from src.week14_transfer_study import calibrate, latent as w14_latent
from src.week15_al import start_design, BUDGETS
from src.week15_ebr import make_gp

OUT = Path(__file__).resolve().parents[1] / "outputs/week15_boundary_acquisition/heldout"
REF_CELLS = [("curvedMono", {"box": "NEW", "sigma": 1.0, "pool": 108}), ("gpworld", {"m0": -4.0, "pool": 108})]


def run(fam, cfg, rep, hyp, pars):
    H.PARS.update(pars)
    c = H.make_cell(fam, cfg, rep)
    if fam == "gpworld":
        p_true = expit(c["f_pool"])
    else:
        p_true = ndtr(c["f_pool"] / cfg["sigma"])
    z, y, dense = c["z_pool"], c["y_pool"], c["dense"]
    L = start_design(z, y, [152, rep, 2])
    nsd = lambda idx, yy: dense.metrics((make_gp(hyp).fit(z[idx], yy).latent_mean(dense.z) > 0).astype(int))["NSD_0.1"]
    rows = []
    while True:
        b = len(L)
        if b in BUDGETS:
            m = dense.metrics((make_gp(hyp).fit(z[L], y[L]).latent_mean(dense.z) > 0).astype(int))
            rows.append({"cell": H.cell_key(fam, cfg), "rep": rep, "policy": "oracle_E", "budget": b, "NSD_0.1": m["NSD_0.1"], "ASSD": m["ASSD"]})
        if b >= 80:
            return rows
        cands = np.setdiff1d(np.arange(len(z)), L)
        vals = [p_true[k] * nsd(np.r_[L, k], np.r_[y[L], 1]) + (1 - p_true[k]) * nsd(np.r_[L, k], np.r_[y[L], 0]) for k in cands]
        L.append(int(cands[int(np.argmax(vals))]))


if __name__ == "__main__":
    pars = {f: calibrate(f) for f in ("curvedMono", "hartmannDev")}
    Hh = json.loads((OUT / "hyperparameters.json").read_text())
    res = Parallel(n_jobs=7, verbose=2)(delayed(run)(f, c, r, Hh[H.cell_key(f, c)], pars) for f, c in REF_CELLS for r in range(4))
    pd.DataFrame([x for rows in res for x in rows]).to_csv(OUT / "oracle_E_reference.csv", index=False)
