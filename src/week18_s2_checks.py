"""Week 18 S2 stress-world checks (HELD-OUT-SYNTHETIC development seeds, base 1840; predictions from THEORY_WEEK18).

  P-T18-3   two-campaign world (level shift δ = 0.6): with vs without the binary campaign-A prior, G3 + margin.
            Prediction: the prior lifts ranking quality (test AUC AULC) much more than BA AULC.
  POCKET    NEW-like rare pocket (9%): G3 + margin vs G3 + random.  Phase 0 found NEW's "random ≥ margin" to be a
            hyperparameter/seed artefact; here a genuine rare pocket exists, so random may win (pocket discovery).
Usage: python -m src.week18_s2_checks [n_jobs]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/week18_independent_research/phase4"


def job(kind, rep):
    from threadpoolctl import threadpool_limits
    from sklearn.metrics import roc_auc_score
    import src.week18_engine as E
    import src.week18_stress as S
    from src.week18_baselines import budgets
    base = 1840
    t = {"two": S.two_campaign, "two_np": S.two_campaign_noprior, "pocket": S.pocket}[kind](rep, base)
    rules = ["margin"] if kind.startswith("two") else ["margin", "random"]
    hyper = "mlii_k8" if len(t["prior"]) else "mlii"
    rows = []
    with threadpool_limits(1):
        for rule in rules:
            try:
                out, L = E.run(t, ("G3", hyper), rule, set(budgets(t)))
            except E.DegenerateTask:
                continue
            yt = t["y"][t["test"]]
            for o in out:
                p = np.asarray(o["p"]); yh = p >= .5
                ba = (np.mean(yh[yt == 1]) + np.mean(~yh[yt == 0])) / 2
                rows.append({"task": t["task"], "rep": rep, "rule": rule, "budget": o["budget"], "BA": ba,
                             "AUC": roc_auc_score(yt, p) if len(set(yt)) == 2 else np.nan, "NSD": o.get("NSD_0.1"), "fp": o["fp"]})
    return rows


def main(n_jobs=4):
    from src.week18_metrics import aulc
    jobs = [(k, r) for k in ("two", "two_np", "pocket") for r in range(8)]
    res = Parallel(n_jobs=n_jobs, verbose=5)(delayed(job)(*a) for a in jobs)
    d = pd.DataFrame([r for rr in res for r in rr]); d.to_csv(OUT / "s2_checks_curves.csv", index=False)
    d["arm"] = d.rule; d["repeat"] = d.rep
    au = aulc(d, "BA").merge(aulc(d, "AUC"), on=["task", "repeat", "arm"]).merge(aulc(d, "NSD"), on=["task", "repeat", "arm"])
    au.to_csv(OUT / "s2_checks_aulc.csv", index=False)
    summ = au.groupby(["task", "arm"])[["BA_AULC", "AUC_AULC", "NSD_AULC"]].mean()
    w = au[au.task.str.startswith("S2_TWO")].pivot_table(index="repeat", columns="task", values=["BA_AULC", "AUC_AULC"])
    lift = {"BA_lift_mean": float((w[("BA_AULC", "S2_TWO_CAMP")] - w[("BA_AULC", "S2_TWO_CAMP_NOPRIOR")]).mean()),
            "AUC_lift_mean": float((w[("AUC_AULC", "S2_TWO_CAMP")] - w[("AUC_AULC", "S2_TWO_CAMP_NOPRIOR")]).mean())}
    pk = au[au.task == "S2_POCKET"].pivot_table(index="repeat", columns="arm", values="NSD_AULC")
    lift["POCKET_random_minus_margin_NSD"] = float((pk["random"] - pk["margin"]).mean())
    pb = au[au.task == "S2_POCKET"].pivot_table(index="repeat", columns="arm", values="BA_AULC")
    lift["POCKET_random_minus_margin_BA"] = float((pb["random"] - pb["margin"]).mean())
    (OUT / "s2_checks_summary.json").write_text(json.dumps({"means": summ.round(4).reset_index().to_dict("records"), **lift}, indent=1, default=float))
    return summ, lift


if __name__ == "__main__":
    summ, lift = main(int(sys.argv[1]) if len(sys.argv) > 1 else 4)
    print(summ.round(4).to_string()); print(lift)
