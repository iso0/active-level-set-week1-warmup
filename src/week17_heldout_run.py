"""Week 17 decisive synthetic benchmark (HELD-OUT-SYNTHETIC; protocol frozen in PREDICTIONS_AND_FREEZE.md).

Per (cell, rep ∈ 0..7):
 (a) common-design model quality: labelled set = paid startup + uniform random fill to n ∈ {24, 48, 80}
     (seed [1717, cell, rep, 5]); models G3, M3, LT, M3_Cfree, H; dense NSD/ASSD/BA, reference-cloud
     latent-sign log loss/Brier, finite q20 accuracy and BA.
 (b) active learning: models {G3, M3, LT, M3_Cfree} × rules {margin, coverage, peer, random}, budgets 16–80.
 (c) oracle splits (fixed-hyperparameter refits of the same model) at B24 and B48 on every margin path.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.special import ndtr

import src.week17_al as A
import src.week17_heldout as HW
import src.week17_models as M
from src.week13_synthetic_al import q20_flags

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week17_model_and_acquisition/heldout"
AL_MODELS = ("G3", "M3", "LT", "M3_Cfree")
RULES = ("margin", "coverage", "peer", "random")
QUALITY_MODELS = ("G3", "M3", "LT", "M3_Cfree", "H")
REPS = range(8)


def model_quality(c, rep):
    sp = A.scores(c); z, y = c["z_pool"], c["y_pool"]; s = sp(z)
    rng = np.random.default_rng([1717, HW.CELL_INDEX[c["name"]], rep, 5])
    order = list(c["start"]) + [int(k) for k in rng.permutation(np.setdiff1d(np.arange(len(z)), c["start"]))]
    q = q20_flags(c["z_eval"], c["y_eval"]); rows = []
    for n in (24, 48, 80):
        L = order[:n]
        for name in QUALITY_MODELS:
            f = M.fit(name, z, s, y, np.arange(len(z)), L)
            mu_d, _ = f.latent(c["dense"].z, sp(c["dense"].z))
            r = {"n": n, "model": name, **c["dense"].metrics((mu_d > 0).astype(int))}
            mu_r, v_r = f.latent(c["zref"], sp(c["zref"]))
            pr = np.clip(ndtr(mu_r / np.sqrt(np.maximum(v_r, 1e-12))) if np.any(v_r) else (mu_r > 0).astype(float), 1e-9, 1 - 1e-9)
            t = c["tref"]
            r["sign_logloss_ref"] = float(-np.mean(t * np.log(pr) + (1 - t) * np.log(1 - pr)))
            r["sign_brier_ref"] = float(np.mean((pr - t) ** 2))
            pe = f.proba(c["z_eval"], sp(c["z_eval"])); ye = c["y_eval"]
            r["q20_accuracy"] = float(np.mean((pe[q] >= .5) == ye[q]))
            r["finite_BA"] = float(np.nanmean([np.mean((pe >= .5)[ye == k] == k) for k in (0, 1)]))
            r["minority_recall"] = float(np.mean((pe >= .5)[ye == int(ye.mean() < .5)] == int(ye.mean() < .5)))
            r["fp_err"] = f.converged() if isinstance(f, M.Fitted) else 0.0
            rows.append(r)
    return rows


def job(name, rep, out):
    dest = Path(out) / f"{name}__r{rep}.json"
    if dest.exists():
        return json.loads(dest.read_text())
    from threadpoolctl import threadpool_limits
    c = HW.build(name, rep); meta = {"cell": name, "rep": rep}
    rows = []
    with threadpool_limits(1):
        rows += [{**meta, "kind": "quality", **r} for r in model_quality(c, rep)]
        for i, model in enumerate(AL_MODELS):
            for j, rule in enumerate(RULES):
                tr, orc = A.run_path(c, model, rule, [1717, rep, 10 * i + j], oracle_budgets=(24, 48) if rule == "margin" else ())
                m2 = {**meta, "model": model, "rule": rule}
                rows.append({**m2, "kind": "aulc", **{f"{k}_AULC": A.aulc(tr, k) for k in ("NSD_0.1", "NSD_0.05", "ASSD", "dense_BA", "q20_accuracy", "finite_BA", "ham_ref")},
                             "max_fp_err": float(np.nanmax([t["fp_err"] for t in tr]))})
                rows += [{**m2, "kind": "trace", **t} for t in tr]
                rows += [{**m2, "kind": "oracle", **o} for o in orc]
    dest.write_text(json.dumps(rows, default=float))
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True); pdir = OUT / "paths"; pdir.mkdir(exist_ok=True)
    jobs = sorted([(n, r) for n, _ in HW.CELLS for r in REPS], key=lambda j: -dict(HW.CELLS)[j[0]]["pool"])
    res = Parallel(n_jobs=7, verbose=5)(delayed(job)(n, r, pdir) for n, r in jobs)
    pd.DataFrame([x for rows in res for x in rows]).to_csv(OUT / "heldout_results.csv.gz", index=False)


if __name__ == "__main__":
    main()
