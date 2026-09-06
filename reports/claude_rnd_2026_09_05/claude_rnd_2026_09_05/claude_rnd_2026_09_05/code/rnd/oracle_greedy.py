"""Test-label-informed greedy oracle for M3 (development diagnostic ONLY — uses held-out
labels to choose queries; it bounds what any acquisition could achieve on the endpoint).
At each step B16..B47 the oracle refits M3 with every eligible candidate's TRUE label and
picks the candidate that maximises held-out q20 accuracy (tie-break: q20 log-loss).
Eligible candidates: physical band OR current M3 p in (0.02, 0.98) (to bound cost).
From B48 the path continues with plain margin."""
import sys, numpy as np, pandas as pd, time
from joblib import Parallel, delayed
from core import *
d = Data(); y = d.labels; lh = d.logh
band = (lh >= 20.3621) & (lh <= 21.2533)
LIMIT_B = 40


def run(spec):
    tr = np.asarray(spec.train_indices); te = np.asarray(spec.test_indices); fl = d.flags(spec); q = fl["B1_q20"]
    queried = list(map(int, w85.initial_design(spec, d.population))); rows = []
    for b in BUDGETS:
        m = M3(d, spec).fit(np.asarray(queried), b); pr = m.proba(te)
        for subset, flag in (("full81", np.ones(len(te), bool)), ("B1_q20", q), ("B1_q30", fl["B1_q30"])):
            rows.append({"run_id": spec.run_id, "repeat": spec.repeat, "arm": "M3_ORACLE", "budget": b, "subset": subset, **metric_values(y[te][flag], pr[flag])})
        if b < 80:
            cand = np.setdiff1d(tr, np.asarray(queried)); pc = m.proba(cand)
            if b < LIMIT_B:
                elig = cand[band[cand] | ((pc > 0.05) & (pc < 0.95))]
                if len(elig) == 0: elig = cand
                best = None
                for x in elig:
                    mm = M3(d, spec).fit(np.asarray(queried + [int(x)]), b + 1); p2 = mm.proba(te)
                    acc = ((p2[q] >= .5).astype(int) == y[te][q]).mean(); ll = -np.mean(np.where(y[te][q] == 1, np.log(np.clip(p2[q], 1e-9, 1)), np.log(np.clip(1 - p2[q], 1e-9, 1))))
                    key = (acc, -ll, -int(x))
                    if best is None or key > best[0]: best = (key, int(x))
                queried.append(best[1])
            else:
                queried.append(margin_select(cand, pc))
    return rows, {"run_id": spec.run_id, "path": queried}


if __name__ == "__main__":
    specs = [s for s in d.specs if s.fold == ((s.repeat - 1) % 5) + 1][:8]
    t0 = time.time(); out = Parallel(n_jobs=1, verbose=5)(delayed(run)(s) for s in specs)
    pd.DataFrame([r for rows, p in out for r in rows]).to_csv("results/oracle_greedy_metrics.csv.gz", index=False)
    import json; json.dump([p for rows, p in out], open("results/oracle_greedy_paths.json", "w")); print("elapsed", time.time() - t0)
