"""Week 18 Phase 2 — baseline reproduction on the DEV blocks (real R1–R3 and S1 twins); resumable per task."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week18_independent_research/phase2"


def budgets(t):
    return tuple(range(16, 81, 4)) if len(t["pool"]) <= 120 else tuple(range(16, 121, 8))


def arms_for(t):
    big = len(t["prior"]) > 0 and len(t["prior"]) + 120 > 200
    h = "mlii_k8" if big else "mlii"
    A = [(("G3", h), "margin"), (("G3", h), "random"), (("G3", h), "candB"), (("LT", h), "margin"), (("M3", h), "margin"), (("H", "mlii"), "margin")]
    if t["task"] in ("R2_TRANSFER", "R3_NEW"):
        A += [(("G3", "fixed:old"), "margin"), (("G3", "fixed:old"), "random")]
    if np.isfinite(t["depth"][t["pool"]]).any():
        A += [(("GPR_depth", "mlii"), "straddle")]
    if t["block"] == "S2":                      # stress worlds (binary): label-only E3 as a development check
        A += [(("MixGP", "auto4"), "margin")]
    return A


def fixed_old():
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern
    from sklearn.preprocessing import StandardScaler
    import src.week17_models as M
    from src.week12_development_common import load_old
    hyp = json.loads((ROOT / "outputs/week15_boundary_acquisition/real_data/hyperparameters.json").read_text())["OLD_G3_ML2"]
    o = load_old()[["P", "VX", "LS", "ST"]].to_numpy(float)
    k = ConstantKernel(hyp["var"], "fixed") * M.Proj(Matern(np.asarray(hyp["ls"], float), "fixed", nu=1.5), [0, 1, 2, 3])
    return {"old": k, "scalers": (StandardScaler().fit(o), StandardScaler().fit(np.zeros((2, 1)) + [[0], [1]]))}


def task_job(t, out_dir):
    from threadpoolctl import threadpool_limits
    import src.week18_engine as E
    key = f"{t['task']}__r{t['repeat']:03d}_f{t['fold']}"
    dest = Path(out_dir) / f"{key}.json"
    if dest.exists():
        return json.loads(dest.read_text())
    rows = []
    if len(set(t["y"][t["pool"]]) | set(t["y"][t["prior"]])) < 2:
        dest.write_text(json.dumps([{"task": t["task"], "repeat": t["repeat"], "fold": t["fold"], "degenerate": True}]))
        return [{"task": t["task"], "repeat": t["repeat"], "fold": t["fold"], "degenerate": True}]
    fx = fixed_old() if t["task"] in ("R2_TRANSFER", "R3_NEW") else None
    with threadpool_limits(1):
        for learner, rule in arms_for(t):
            if learner[1] == "auto4":
                from src.week18_dev_arms import hyper_for
                learner = (learner[0], hyper_for(t, "auto4"))
            out, L = E.run(t, learner, rule, set(budgets(t)), fixed=fx)
            for o in out:
                r = {"task": t["task"], "repeat": t["repeat"], "fold": t["fold"], "model": learner[0], "hyper": learner[1], "rule": rule,
                     "budget": o["budget"], "startup": o["startup"], "fp": o["fp"], "u": o["u"],
                     "rows": ",".join(map(str, t["test"])), "p": ",".join(f"{v:.5g}" for v in o["p"]),
                     "q20": ",".join("1" if v else "0" for v in t["q20"]) if t["q20"] is not None else ""}
                for k in ("NSD_0.1", "NSD_0.05", "ASSD", "dense_BA"):
                    if k in o:
                        r[k] = o[k]
                rows.append(r)
    dest.write_text(json.dumps(rows, default=float))
    return rows


def main(which="real"):
    import src.week18_tasks as T
    import src.week18_twins as W
    OUT.mkdir(parents=True, exist_ok=True); pdir = OUT / f"cache_{which}"; pdir.mkdir(exist_ok=True)
    if which == "real":
        tasks = T.all_real("DEV")
    elif which == "stress":
        import src.week18_stress as S
        tasks = S.all_stress(0)
    else:
        tasks = [W.twin_task(tw, d, n, rep) for tw, d, n in
                 [(tw, d, n) for tw in ("T_GP", "T_GBT", "T_NW", "T_QL", "T_TOBIT") for d, n in (("pooled", 433), ("OLD", 324), ("NEW", 108))] + [("T_DEPTH", "OLD", 324)]
                 for rep in range(8)]
    tasks.sort(key=lambda t: -(len(t["prior"]) + len(t["pool"])))
    res = Parallel(n_jobs=7, verbose=5)(delayed(task_job)(t, pdir) for t in tasks)
    pd.DataFrame([r for rr in res for r in rr]).to_csv(OUT / f"baselines_{which}.csv.gz", index=False)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "real")
