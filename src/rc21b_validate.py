"""RC21B acceptance before the freeze (no evaluation metric is computed):
  1. RC21B's H_MARGIN reproduces the RC21 d-final H_MARGIN trajectory (repeat 27, fold 1) exactly: paid order, own predictions and
     every recorded by-product (including PHR_NRMAP) at every budget 8-60;
  2. trajectory shadow test for NEW_MARGIN (PHR_NRMAP + margin): with every outcome outside its own paid runs randomised it pays
     the same runs and predicts identically.
    python -m src.rc21b_validate
"""
from __future__ import annotations

import json

import numpy as np

import src.rc18_common as RC
import src.rc19_pool as P
import src.rc21b_final as F
from src.rc19_validate import _corrupt


def main():
    RC.limit_threads(1); M = P.manifest(); t = {(x["repeat"], x["fold"]): x for x in P.tasks([27])}[(27, 1)]; res = {"utc": RC.utc()}
    ref = RC.read_json_gz(F.OUT / "d-final" / "units" / "r27_f1__H_MARGIN.json.gz"); u = F.run_phys(t, "H_MARGIN", 60, M)
    same = u["paid_ids"] == ref["paid_ids"] and all(e1["p"] == e2["p"] and e1["p_all"] == e2["p_all"] for e1, e2 in zip(u["evals"], ref["evals"])) and len(u["evals"]) == len(ref["evals"])
    res["H_vs_RC21_H_MARGIN_r27_f1"] = {"budgets": len(u["evals"]), "identical_paid_order_and_all_predictions": bool(same), "PASS": bool(same)}
    print(res["H_vs_RC21_H_MARGIN_r27_f1"], flush=True)
    u1 = F.run_phys(t, "NEW_MARGIN", 20, M); Mc = _corrupt(M, set(u1["paid_ids"]), 2122); u2 = F.run_phys(t, "NEW_MARGIN", 20, Mc)
    d = max(float(np.nanmax(np.abs(np.asarray(e1["p_all"][k], float) - np.asarray(e2["p_all"][k], float)))) for e1, e2 in zip(u1["evals"], u2["evals"]) for k in e1["p_all"])
    res["NEW_trajectory_shadow"] = {"construction": u1["construction"], "same_paid_order": u1["paid_ids"] == u2["paid_ids"], "max_abs_p_diff_all_constructions": d,
                                    "PASS": bool(u1["paid_ids"] == u2["paid_ids"] and d == 0.0)}
    print(res["NEW_trajectory_shadow"], flush=True)
    res["status"] = "PASS" if all(v["PASS"] for v in res.values() if isinstance(v, dict)) else "FAIL"
    (F.OUT / "RC21B_VALIDATION.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); print(res["status"])


if __name__ == "__main__":
    main()
