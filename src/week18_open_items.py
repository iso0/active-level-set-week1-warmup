"""Week 18 Phase 0, open item (a): is NEW's "random beats margin" (Week 17) a hyperparameter artefact?

Factorial on the 100 frozen NEW splits (POST-HOC NEW):
  hyper  fixedOLD — G3 kernel fixed at the Week 15 OLD-405 ML-II hyperparameters, inputs standardized with the
                    OLD scaler (the Week 15 replay setting); mlii — per-step ML-II, pool-standardized (Week 17)
  seeds  w15 — maximin seed [15, sid, 2], random rng [15, sid] (Week 15); w17 — [1717, sid, 2], [1717, sid, 3, 0]
  rule   margin / random
All fits safeguarded Laplace (week17_models).  Endpoints as Week 17 (pooled per repeat).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.gaussian_process.kernels import ConstantKernel, Matern
from sklearn.preprocessing import StandardScaler

import src.week17_models as M
from src.week13_synthetic_al import maximin_order
from src.week17_real_al import BUDGETS, data, splits

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week18_independent_research/phase0"
HYP = json.loads((ROOT / "outputs/week15_boundary_acquisition/real_data/hyperparameters.json").read_text())["OLD_G3_ML2"]


def fixed_kernel():
    return ConstantKernel(HYP["var"], "fixed") * M.Proj(Matern(np.asarray(HYP["ls"], float), "fixed", nu=1.5), [0, 1, 2, 3])


def run_split(s, C):
    from threadpoolctl import threadpool_limits
    x4, lh, y = C["NEW"]; xo = C["OLD"][0]
    tr, te = s["train"], s["test"]; sid = 10 * s["repeat"] + s["fold"]
    old_sc = StandardScaler().fit(xo); h_sc = StandardScaler().fit(lh[tr, None])
    rows = []
    with threadpool_limits(1):
        for seeds in ("w15", "w17"):
            mm = [15, sid, 2] if seeds == "w15" else [1717, sid, 2]
            order = tr[maximin_order(x4[tr], np.random.default_rng(mm))]
            for hyper in ("fixedOLD", "mlii"):
                for rule in ("margin", "random"):
                    rng = np.random.default_rng([15, sid] if seeds == "w15" else [1717, sid, 3, 0])
                    L = list(order[:8]); k = 8
                    while len(set(y[L])) < 2:
                        L.append(int(order[k])); k += 1
                    while True:
                        b = len(L)
                        if hyper == "fixedOLD":
                            f = M.fit("G3", x4, lh, y, tr, L, kernel=fixed_kernel(), scalers=(old_sc, h_sc))
                        else:
                            f = M.fit("G3", x4, lh, y, tr, L)
                        if b in BUDGETS:
                            p = f.proba(x4[te], lh[te])
                            rows.append({"repeat": s["repeat"], "fold": s["fold"], "seeds": seeds, "hyper": hyper, "rule": rule, "budget": b,
                                         "fp_err": f.converged(), "rows": ",".join(map(str, te)), "p": ",".join(f"{v:.6g}" for v in p),
                                         "q20": ",".join("1" if v else "0" for v in s["q20"])})
                        if b >= 80:
                            break
                        cands = np.setdiff1d(tr, L)
                        if rule == "margin":
                            pc = f.proba(x4[cands], lh[cands]); L.append(int(cands[np.argmin(np.abs(pc - .5))]))
                        else:
                            L.append(int(rng.choice(cands)))
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    C = data(); S = [s for s in splits() if s["campaign"] == "NEW"]
    res = Parallel(n_jobs=7, verbose=5)(delayed(run_split)(s, C) for s in S)
    df = pd.DataFrame([r for rr in res for r in rr]); df.to_csv(OUT / "new_hyper_seed_factorial.csv.gz", index=False)
    from src.week17_analyze import boot
    from sklearn.metrics import roc_auc_score
    y = C["NEW"][2]; out = []
    for (seeds, hyper, rule, rep, b), g in df.groupby(["seeds", "hyper", "rule", "repeat", "budget"]):
        idx = np.concatenate([np.array(r.split(","), int) for r in g.rows]); p = np.concatenate([np.array(r.split(","), float) for r in g.p])
        yh = (p >= .5).astype(int); yy = y[idx]
        qa = [np.mean((np.array(r.p.split(","), float)[np.array(r.q20.split(","), int).astype(bool)] >= .5) == y[np.array(r.rows.split(","), int)][np.array(r.q20.split(","), int).astype(bool)]) for r in g.itertuples()]
        out.append({"seeds": seeds, "hyper": hyper, "rule": rule, "repeat": rep, "budget": b, "BA": (np.mean(yh[yy == 1] == 1) + np.mean(yh[yy == 0] == 0)) / 2,
                    "q20": float(np.mean(qa)), "nonKH_recall": float(np.mean(yh[yy == 0] == 0))})
    R = pd.DataFrame(out)
    au = R.groupby(["seeds", "hyper", "rule", "repeat"]).apply(lambda g: pd.Series({k: np.trapezoid(g.sort_values("budget")[k], g.sort_values("budget").budget) / 64 for k in ("BA", "q20")}), include_groups=False).reset_index()
    au.to_csv(OUT / "new_hyper_seed_factorial_aulc.csv", index=False)
    w = au.pivot_table(index="repeat", columns=["seeds", "hyper", "rule"], values="BA")
    summ = []
    for seeds in ("w15", "w17"):
        for hyper in ("fixedOLD", "mlii"):
            d = (w[(seeds, hyper, "random")] - w[(seeds, hyper, "margin")]).values
            summ.append({"seeds": seeds, "hyper": hyper, "margin_BA": float(w[(seeds, hyper, "margin")].mean()), "random_BA": float(w[(seeds, hyper, "random")].mean()),
                         "random_minus_margin": float(d.mean()), "ci": boot(d)})
    pd.DataFrame(summ).to_csv(OUT / "new_hyper_seed_factorial_summary.csv", index=False)
    print(pd.DataFrame(summ).to_string())


if __name__ == "__main__":
    main()
