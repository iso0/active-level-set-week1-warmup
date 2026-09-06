"""Same-path model contrast: evaluate several models on the exact published
Phase 1.14 M3-margin (P1) revealed prefixes, budgets 16..80, all 100 runs.
Model effect only (identical labels); M3 numbers are the committed ones."""
import numpy as np, pandas as pd, time, math, sys
from joblib import Parallel, delayed
from sklearn.preprocessing import StandardScaler
from core import *
from tmodel import TModel
from cdl import CDL

d = Data(); pop = d.population; y = d.labels; lh = d.logh
Zraw = np.c_[np.log(pop.VX), np.log(pop.LS), pop.ST]
U = np.c_[lh, Zraw]
D = pop.value__max_depth.to_numpy(float); logD = np.log(D)
paths = pd.read_csv(REPO / 'outputs/week9_phase1_14_m3_margin_acquisition/m3_margin_paths.csv.gz')
P1 = {r: g.sort_values('query_order').population_row_index.astype(int).tolist() for r, g in paths[paths.path.eq('P1')].groupby('run_id')}

VARIANTS = {  # (c, s_u, ls)
    "T_F7": (7.0, 0.41, [1.7, 30, 30]),
    "T_F7su8": (7.0, 0.8, [1.7, 30, 30]),
    "T_F4su8": (4.0, 0.8, [1.7, 30, 30]),
    "T_F7ls1": (7.0, 0.8, [1.0, 5.0, 5.0]),
}


def frozen_T(c, su, ls, mu0, l, Z, yy):
    m = TModel(mu0=mu0, optimize=False); m.dim = 3
    m.theta = np.r_[math.log(c), math.log(su), np.log(ls)]
    m.l, m.Z, m.y = l, Z, yy; m.mean_, m.K = m._build(m.theta, l, Z)
    m.f, m.alpha, m.w, m.sw, m.L, m.lml = m._mode(m.K, m.mean_, yy, return_all=True); m.c = c
    return m


def run(spec):
    tr = np.asarray(spec.train_indices); te = np.asarray(spec.test_indices); fl = d.flags(spec)
    scz = StandardScaler().fit(Zraw[tr]); Z = scz.transform(Zraw)
    scu = StandardScaler().fit(U[tr]); X = scu.transform(U)
    path = P1[spec.run_id]; rows = []
    for b in BUDGETS:
        rev = np.asarray(path[:b]); mu0 = lh[rev].mean()
        preds = {}
        for name, (c, su, ls) in VARIANTS.items():
            m = frozen_T(c, su, ls, mu0, lh[rev], Z[rev], y[rev]); preds[name] = m.pi(lh[te], Z[te])
        for dstar in (100.0,):
            LD = math.log(dstar)
            try:
                m = CDL(log_dstar=0.0).fit(X[rev], y[rev], logD[rev] - LD); preds[f"CDL_D{int(dstar)}"] = m.pi(X[te])
            except Exception as e:
                preds[f"CDL_D{int(dstar)}"] = np.full(len(te), np.nan)
        for name, pr in preds.items():
            for subset, flag in (("full81", np.ones(len(te), bool)), ("B1_q20", fl["B1_q20"]), ("B1_q30", fl["B1_q30"])):
                rows.append({"run_id": spec.run_id, "repeat": spec.repeat, "budget": b, "model": name, "subset": subset, **metric_values(y[te][flag], np.nan_to_num(pr[flag], nan=0.5))})
    return rows


if __name__ == "__main__":
    t0 = time.time()
    out = Parallel(n_jobs=2, verbose=5)(delayed(run)(s) for s in d.specs)
    df = pd.DataFrame([r for rows in out for r in rows]); df.to_csv("samepath_models_metrics.csv.gz", index=False)
    print("elapsed", time.time() - t0)
