"""Week 17 real-data active learning (POST-HOC NEW-136 / HISTORICAL OLD-405; protocol frozen beforehand).

Splits: NEW — the 100 frozen Week 11/12 splits; OLD — Week 8.5 repeats 1–4 (20 runs).  Paid startup identical
for every arm: 8 maximin points of the training pool (seed [1717, 10·repeat + fold, 2]) + maximin continuation
until both classes are revealed; every query counts.  Each step refits the model by ML-II on revealed labels.
Models G3, M3, LT, M3_Cfree (week17_models; safeguarded Laplace).  Rules:
  margin  argmin |p − ½| over the unlabelled training pool
  candB   the exact historical Candidate-B selector (external_validation.runner._select; band coverage →
          margin at B40, standardized-x coverage, log-h band from revealed labels) fed with the model's p
  peer    Week 16 PEER on 400 targets uniform in the training pool's raw bounding box (seed [15, 97])
  random  uniform over the unlabelled training pool (seed [1717, 10·repeat + fold, rule, model])
Test-fold predictions at budgets 16–80 step 4.  Endpoints (pooled out-of-fold per repeat): BA AULC,
historical q20 mean-fold AULC, minority recall at B80, DC-BD AULC, AUC at B80.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

import src.week17_models as M
from src.week13_synthetic_al import maximin_order
from src.week17_audit import ROOT

OUT = ROOT / "outputs/week17_model_and_acquisition/real_al"
MODELS = ("G3", "M3", "LT", "M3_Cfree")
RULES = ("margin", "candB", "peer", "random")
BUDGETS = tuple(range(16, 81, 4))


def splits():
    from src.week12_development_common import load_new, load_old, load_splits
    from src.external_validation.analysis import boundary_flags
    from src import week8_5_frozen_sample_efficiency_confirmation as w85
    new, old = load_new(), load_old()
    out = []
    xn = new[["P", "VX", "LS", "ST"]].to_numpy(float); yn = new.has_keyhole.to_numpy(int); ids = new.sim_id.astype(str).to_numpy()
    for s in load_splits():
        te = np.asarray(s["test_indices"])
        out.append({"campaign": "NEW", "repeat": int(s["repeat"]), "fold": int(s["fold"]), "train": np.asarray(s["train_indices"]), "test": te,
                    "q20": boundary_flags(xn, yn, te, ids, "entire_evaluation_batch")[20]})
    man = pd.read_csv(ROOT / "outputs/week8_5_frozen_confirmation/split_manifest.csv", usecols=["run_id", "repeat", "fold", "role", "population_row_index"])
    dist = w85.b1_distance(old.rename(columns={"sim_id": "experiment_name"}))
    for _, g in man[man.repeat <= 4].groupby("run_id"):
        te = g[g.role == "untouched_test"].population_row_index.to_numpy()
        order = np.lexsort((old.sim_id.to_numpy(object)[te], dist[te])); q = np.zeros(len(te), bool); q[order[:math.ceil(.2 * len(te))]] = True
        out.append({"campaign": "OLD", "repeat": int(g.repeat.iloc[0]), "fold": int(g.fold.iloc[0]),
                    "train": g[g.role == "training_pool"].population_row_index.to_numpy(), "test": te, "q20": q})
    return out


def data():
    from src.week17_audit import campaigns
    return campaigns()


def run_split(s, C, horizon=80):
    from threadpoolctl import threadpool_limits
    from src.external_validation.runner import _select
    x4, lh, y = C[s["campaign"]]
    tr, te = s["train"], s["test"]
    sid = 10 * s["repeat"] + s["fold"]
    lo, hi = x4[tr].min(0), x4[tr].max(0)
    ref = lo + (hi - lo) * np.random.default_rng([15, 97]).random((400, 4))
    ref_h = np.log(ref[:, 0]) - .5 * np.log(ref[:, 1]) - 1.5 * np.log(ref[:, 2])
    order = tr[maximin_order(x4[tr], np.random.default_rng([1717, sid, 2]))]
    rows, paths = [], []
    with threadpool_limits(1):
        for mi, model in enumerate(MODELS):
            for ri, rule in enumerate(RULES):
                rng = np.random.default_rng([1717, sid, ri, mi])
                L = list(order[:8]); k = 8
                while len(set(y[L])) < 2:
                    L.append(int(order[k])); k += 1
                startup = len(L)
                while True:
                    b = len(L)
                    f = M.fit(model, x4, lh, y, tr, L)
                    if b in BUDGETS:
                        p = f.proba(x4[te], lh[te])
                        rows.append({"campaign": s["campaign"], "repeat": s["repeat"], "fold": s["fold"], "model": model, "rule": rule,
                                     "budget": b, "startup": startup, "fp_err": f.converged(),
                                     "rows": ",".join(map(str, te)), "p": ",".join(f"{v:.6g}" for v in p), "q20": ",".join("1" if v else "0" for v in s["q20"])})
                    if b >= horizon:
                        break
                    cands = np.setdiff1d(tr, L)
                    pc = f.proba(x4[cands], lh[cands])
                    if rule == "margin":
                        nxt = int(cands[np.argmin(np.abs(pc - .5))])
                    elif rule == "random":
                        nxt = int(rng.choice(cands))
                    elif rule == "candB":
                        nxt, _ = _select("Candidate_B__early8", b, x4, lh, tr, L, y[L], cands, pc, None, f"w17_{sid}")
                        nxt = int(nxt)
                    else:
                        v = M.peer_values(f, ref, ref_h, x4[cands], lh[cands]); nxt = int(cands[np.argmax(v)])
                    L.append(nxt)
                paths.append({"campaign": s["campaign"], "repeat": s["repeat"], "fold": s["fold"], "model": model, "rule": rule, "path": ",".join(map(str, L))})
    return rows, paths


def main():
    OUT.mkdir(parents=True, exist_ok=True); pdir = OUT / "splits"; pdir.mkdir(exist_ok=True)
    C = data(); S = splits()
    def go(s):
        dest = pdir / f"{s['campaign']}_r{s['repeat']:02d}_f{s['fold']}.json"
        if dest.exists():
            return json.loads(dest.read_text())
        r = run_split(s, C); dest.write_text(json.dumps(r, default=float)); return r
    S.sort(key=lambda s: s["campaign"] != "OLD")
    res = Parallel(n_jobs=7, verbose=5)(delayed(go)(s) for s in S)
    pd.DataFrame([x for r in res for x in r[0]]).to_csv(OUT / "real_al_predictions.csv.gz", index=False)
    pd.DataFrame([x for r in res for x in r[1]]).to_csv(OUT / "real_al_paths.csv.gz", index=False)


if __name__ == "__main__":
    main()
