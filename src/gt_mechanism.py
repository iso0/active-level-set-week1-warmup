"""GT POST-HOC mechanism check (after the G2 result; descriptive, no rule changes): why does the label-free geometric classifier
over-call Keyhole? Compares the TRUE ratio target g1 = log(2 A / W_A) of the two classes near the physical boundary g = 0 with the
GEO_B1 latent mean m (recorded in the G2 units) at the test runs, at budgets 12 / 24 / 60 of the 200 STD learners.
    python -m src.gt_mechanism run
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.gt_data as GD
import src.gt_dev as DV
import src.rc18_common as RC
import src.rc19_pool as P

OUT = GD.OUT / "dev"


def run():
    M = P.manifest(); R = GD.runs().reindex(M.index); g = R.g1; y = M.y
    res = {"label": "POST-HOC (after the G2 result), descriptive", "true_g1_quantiles": {}}
    for c, nm in ((0, "conduction"), (1, "keyhole")):
        v = g[y == c].dropna(); res["true_g1_quantiles"][nm] = {q: float(v.quantile(q)) for q in (0.05, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99)}
    res["true_rule_errors"] = {"conduction_with_g1_ge_0": int(((g >= 0) & (y == 0)).sum()), "keyhole_with_g1_lt_0": int(((g < 0) & (y == 1)).sum()),
                               "n_conduction": int((y == 0).sum()), "n_keyhole": int((y == 1).sum())}
    gap = {"conduction_max_g1": float(g[y == 0].max()), "keyhole_min_g1": float(g[y == 1].min()),
           "keyhole_g1_q10": float(g[y == 1].quantile(0.10)), "conduction_g1_q90": float(g[y == 0].quantile(0.90))}
    res["class_gap_in_g1"] = gap
    rows = []
    for r in DV.DEV["STD"]:
        for f in range(1, 6):
            n = f"STD__r{r}_f{f}"; u = RC.read_json_gz(DV.OUT / "gt-dev" / "units" / f"{n}.json.gz"); ids = u["test_ids"]
            yt = y.reindex(ids).to_numpy(int); gt = g.reindex(ids).to_numpy(float)
            for e in u["evals"]:
                if e["budget"] in (12, 24, 60):
                    m = np.asarray(e["m_GEO_B1"], float)
                    for i in range(len(ids)):
                        rows.append((e["budget"], yt[i], gt[i], m[i]))
    T = pd.DataFrame(rows, columns=["b", "y", "g_true", "m_pred"]).dropna()
    res["by_budget"] = {}
    for b, G in T.groupby("b"):
        c = G[G.y == 0]; k = G[G.y == 1]; near = c[c.g_true > -0.35]
        res["by_budget"][int(b)] = {"conduction_pred_ge_0": float((c.m_pred >= 0).mean()), "conduction_true_ge_0": float((c.g_true >= 0).mean()),
                                    "keyhole_pred_lt_0": float((k.m_pred < 0).mean()),
                                    "near_boundary_conduction(g_true>-0.35)": {"n": int(len(near)), "pred_ge_0": float((near.m_pred >= 0).mean()),
                                                                              "mean_bias_m_minus_g": float((near.m_pred - near.g_true).mean())},
                                    "far_conduction(g_true<=-0.35)": {"pred_ge_0": float((c[c.g_true <= -0.35].m_pred >= 0).mean())},
                                    "keyhole_mean_bias_m_minus_g": float((k.m_pred - k.g_true).mean())}
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "G2_MECHANISM_POSTHOC.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"run": run}[sys.argv[1]]()
