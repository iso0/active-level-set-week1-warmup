"""Week 17 POST-HOC diagnostic (after the decisive run; cannot change the frozen verdict).

LT nests G3 (s0², s1² → lower bound), so at its ML-II optimum LML(LT) ≥ LML(G3) − O(1e-3).  On the
regenerated LT margin paths of the held-out worlds, record at B24/B48/B80 the frozen single-start LT
evidence, G3's evidence, and the evidence and boundary quality of an LT refit started from G3's optimum
(trend variances at their lower bounds) — i.e. how much of LT's held-out shortfall is optimizer failure.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.base import clone

import src.week17_al as A
import src.week17_heldout as HW
import src.week17_models as M
from src.week17_audit_impact import SafeguardedFixedMeanLaplaceGPC

OUT = Path(__file__).resolve().parents[1] / "outputs/week17_model_and_acquisition/heldout"


def warm_lt(z, s, y, L, g3):
    f = M.fit("LT", z, s, y, np.arange(len(z)), L)          # frozen fit (for scalers / structure)
    k = clone(M.kernel_for("LT"))
    th = k.theta.copy(); g_th = g3.gp.kernel_.theta          # [s0², s1², a², ℓ1..4] in log space
    th[0] = np.log(1e-3); th[1] = np.log(1e-3); th[2:] = g_th
    k.theta = th
    gp = SafeguardedFixedMeanLaplaceGPC(k, optimize=True).fit(f.inputs(z[L], s[L]), y[L], np.zeros(len(L)))
    f2 = M.Fitted("LT", gp, f.xs, f.hs, None)
    return f, f2


def one(cell, rep):
    from threadpoolctl import threadpool_limits
    c = HW.build(cell, rep); sp = A.scores(c); z, y = c["z_pool"], c["y_pool"]; s = sp(z)
    rows = []
    with threadpool_limits(1):
        L = list(c["start"])
        while True:
            b = len(L)
            f = M.fit("LT", z, s, y, np.arange(len(z)), L)
            if b in (24, 48, 80):
                g3 = M.fit("G3", z, s, y, np.arange(len(z)), L)
                _, fw = warm_lt(z, s, y, L, g3)
                r = {"cell": cell, "rep": rep, "budget": b, "lml_LT": f.gp.log_marginal_likelihood_value_, "lml_G3": g3.gp.log_marginal_likelihood_value_,
                     "lml_LT_warm": fw.gp.log_marginal_likelihood_value_}
                for tag, ff in (("LT", f), ("G3", g3), ("LT_warm", fw)):
                    r[f"NSD_{tag}"] = A.truth_eval(c, ff, sp)["NSD_0.1"]
                rows.append(r)
            if b >= 80:
                return rows
            cands = np.setdiff1d(np.arange(len(z)), L); p = f.proba(z[cands], s[cands]); L.append(int(cands[np.argmin(np.abs(p - .5))]))


if __name__ == "__main__":
    res = Parallel(n_jobs=3, verbose=5)(delayed(one)(n, r) for n, _ in HW.CELLS for r in range(8))
    df = pd.DataFrame([x for rows in res for x in rows]); df.to_csv(OUT / "posthoc_lt_optimizer_check.csv", index=False)
    df["fail"] = df.lml_LT < df.lml_G3 - .05
    print("share of states with LT evidence below G3:", round(df.fail.mean(), 3))
    print(df.groupby("cell")[["fail"]].mean().join(df.assign(gain=df.lml_LT_warm - df.lml_LT).groupby("cell")[["gain"]].mean()).round(3).to_string())
    print(df[df.fail][["NSD_LT", "NSD_LT_warm", "NSD_G3"]].mean().round(4).to_string())
