"""Week 17 Phase 2 — development study (DEVELOPMENT; Week 13 generator + Week 15 curvedMono cells, which are
already used/descriptive).  Question: which model defect, once fixed, makes model-aware acquisition align
with true boundary improvement?  Models G3, LT, M3, M3_Cfree (week17_models), rules margin / peer
(+ random for G3); per-step ML-II; oracle splits at B24 and B48 on margin paths."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

import src.week17_al as A
from src.week16_cells import build, cell_key, pars

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week17_model_and_acquisition/development"
CELLS = ([("dev", {"scn": s, "sigma": g}) for s in ("BAL", "OLD", "NEW") for g in (0.0, 0.5)] +
         [("curvedMono", {"box": b, "sigma": g, "pool": 108}) for b in ("OLD", "NEW") for g in (0.0, 0.5)])
ARMS = [(m, r) for m in ("G3", "LT", "M3", "M3_Cfree") for r in ("margin", "peer")] + [("G3", "random")]


def job(fam, cfg, rep, P, out):
    dest = Path(out) / f"{cell_key(fam, cfg).replace('|', '__').replace('=', '-')}__r{rep}.json"
    if dest.exists():
        return json.loads(dest.read_text())
    from threadpoolctl import threadpool_limits
    c = build(fam, cfg, rep, P)
    rows = []
    with threadpool_limits(1):
        for i, (model, rule) in enumerate(ARMS):
            tr, orc = A.run_path(c, model, rule, [17, rep, i], oracle_budgets=(24, 48) if rule == "margin" else ())
            meta = {"cell": cell_key(fam, cfg), "family": fam, "rep": rep, "model": model, "rule": rule}
            rows.append({**meta, "kind": "aulc", **{f"{k}_AULC": A.aulc(tr, k) for k in ("NSD_0.1", "ASSD", "dense_BA", "q20_accuracy", "finite_BA", "ham_ref")},
                         "max_fp_err": float(max(t["fp_err"] for t in tr))})
            rows += [{**meta, "kind": "trace", **t} for t in tr]
            rows += [{**meta, "kind": "oracle", **o} for o in orc]
    dest.write_text(json.dumps(rows, default=float))
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True); pdir = OUT / "paths"; pdir.mkdir(exist_ok=True)
    P = pars()
    res = Parallel(n_jobs=7, verbose=5)(delayed(job)(f, c, r, P, pdir) for f, c in CELLS for r in range(4))
    df = pd.DataFrame([x for rows in res for x in rows]); df.to_csv(OUT / "dev_results.csv.gz", index=False)
    a = df[df.kind == "aulc"]
    print(a.groupby(["model", "rule"])[["NSD_0.1_AULC", "ASSD_AULC", "dense_BA_AULC", "q20_accuracy_AULC"]].mean().round(4).to_string())
    o = df[df.kind == "oracle"]
    print(o.groupby("model")[["r_model", "rho_ham", "rho_nsd", "H_ham", "A_ham", "H_nsd", "A_nsd"]].mean().round(4).to_string())


if __name__ == "__main__":
    main()
