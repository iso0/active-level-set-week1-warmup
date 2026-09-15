import numpy as np, pandas as pd, time, math, sys
from joblib import Parallel, delayed
from sklearn.preprocessing import StandardScaler
from core import *
from tmodel import TModel
d = Data(); pop = d.population; y = d.labels; lh = d.logh
Zraw = np.c_[np.log(pop.VX), np.log(pop.LS), pop.ST]
paths = pd.read_csv(REPO / 'outputs/week9_phase1_14_m3_margin_acquisition/m3_margin_paths.csv.gz')
P1 = {r: g.sort_values('query_order').population_row_index.astype(int).tolist() for r, g in paths[paths.path.eq('P1')].groupby('run_id')}
VARIANTS = {  # name: (c, s_u, ls, s_beta, s_mu)
    "T_c7_su01_sb02": (7.0, 0.1, [1.7, 30, 30], 0.2, 3.0),
    "T_c7_su02_sb05": (7.0, 0.2, [1.7, 30, 30], 0.5, 3.0),
    "T_c7_su02_sb02": (7.0, 0.2, [1.7, 30, 30], 0.2, 3.0),
    "T_c12_su02_sb03": (12.0, 0.2, [1.7, 30, 30], 0.3, 3.0),
    "T_c7_su005_sb01": (7.0, 0.05, [1.7, 30, 30], 0.1, 3.0),
    "T_c20_su01_sb02": (20.0, 0.1, [1.7, 30, 30], 0.2, 3.0),
}
def frozen_T(c, su, ls, sb, smu, mu0, l, Z, yy):
    m = TModel(mu0=mu0, s_mu=smu, s_beta=sb, optimize=False); m.dim = 3
    m.theta = np.r_[math.log(c), math.log(su), np.log(ls)]
    m.l, m.Z, m.y = l, Z, yy; m.mean_, m.K = m._build(m.theta, l, Z)
    m.f, m.alpha, m.w, m.sw, m.L, m.lml = m._mode(m.K, m.mean_, yy, return_all=True); m.c = c
    return m
def run(spec):
    tr = np.asarray(spec.train_indices); te = np.asarray(spec.test_indices); fl = d.flags(spec)
    Z = StandardScaler().fit(Zraw[tr]).transform(Zraw); path = P1[spec.run_id]; rows = []
    for b in BUDGETS:
        rev = np.asarray(path[:b]); mu0 = lh[rev].mean()
        for name, (c, su, ls, sb, smu) in VARIANTS.items():
            pr = frozen_T(c, su, ls, sb, smu, mu0, lh[rev], Z[rev], y[rev]).pi(lh[te], Z[te])
            for subset, flag in (("full81", np.ones(len(te), bool)), ("B1_q20", fl["B1_q20"]), ("B1_q30", fl["B1_q30"])):
                rows.append({"run_id": spec.run_id, "repeat": spec.repeat, "budget": b, "model": name, "subset": subset, **metric_values(y[te][flag], pr[flag])})
    return rows
if __name__ == "__main__":
    t0 = time.time(); out = Parallel(n_jobs=2)(delayed(run)(s) for s in d.specs)
    pd.DataFrame([r for rows in out for r in rows]).to_csv("results/samepath_T_variants.csv.gz", index=False); print("elapsed", time.time() - t0)
