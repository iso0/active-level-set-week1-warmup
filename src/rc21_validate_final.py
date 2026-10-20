"""RC21 sequential-stage acceptance (before the freeze; no evaluation metric is computed):
  1. H_MARGIN reproduces RC20's CAND_MARGIN trajectory exactly (same paid order and identical probabilities) on a DEV task;
  2. trajectory shadow test: with every outcome outside the trajectory's own paid runs randomised, every physical arm pays the
     same runs and predicts identically (it reads paid outcomes only);
  3. the margin choice uses only the arm's own construction (the other constructions are recorded, never used).
    python -m src.rc21_validate_final
"""
from __future__ import annotations

import json

import numpy as np

import src.rc18_common as RC
import src.rc19_pool as P
import src.rc21_final as F
from src.rc19_validate import _corrupt

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc21"


def stage1_reproduction(M):
    """After amendment A1 (PHR_NRMAP added) the code must reproduce the Stage 1 recorded constructions exactly (float32)."""
    import src.rc19_learn as LN
    import src.rc19b_keyhole as K
    import src.rc21_attr as RA
    worst = 0.0; n = 0; T = {(x["repeat"], x["fold"]): x for x in P.tasks([11, 15, 18])}
    for (r, f, arm, b) in ((11, 2, "E1S", 16), (15, 4, "G3_MARGIN", 40), (18, 5, "ATSCF_MARGIN", 60)):
        t = T[(r, f)]; u = RC.read_json_gz(OUT / "d-replay" / "units" / f"r{r}_f{f}__{arm}.json.gz"); pos = {s: i for i, s in enumerate(t["ids"])}
        rev = K._rev_with(t, M, [pos[s] for s in u["paid_ids"][:b]]); out, _ = RA.state(t, rev, P.zstd(t), t["test"])
        rec = [e for e in u["evals"] if e["budget"] == b][0]["p"]
        for k, v in rec.items():
            worst = max(worst, float(np.nanmax(np.abs(np.asarray(LN._f32(out[k]), float) - np.asarray(v, float))))); n += 1
    return {"constructions_compared": n, "max_abs_diff_float32": worst, "PASS": bool(worst == 0.0)}


def main():
    import src.rc20_final as F20
    RC.limit_threads(1); M = P.manifest(); t = P.tasks((1,))[0]; res = {"utc": RC.utc()}
    res["stage1_reproduction_after_A1"] = stage1_reproduction(M); print(res["stage1_reproduction_after_A1"], flush=True)
    a = F.run_phys(t, "H_MARGIN", 20, M); b = F20.run_cand(t, "CAND_MARGIN", 20, M)
    dp = max(float(np.nanmax(np.abs(np.asarray(ea["p"]["SHQ_ATS_H"], float) - np.asarray(eb["p"]["SHQ_ATS_H"], float)))) for ea, eb in zip(a["evals"], b["evals"]))
    res["H_vs_RC20_CAND"] = {"same_paid_order": a["paid_ids"] == b["paid_ids"], "max_abs_p_diff": dp, "PASS": bool(a["paid_ids"] == b["paid_ids"] and dp == 0.0)}
    print(res["H_vs_RC20_CAND"], flush=True); sh = {}
    for arm in F.PHYS_ARMS:
        u1 = F.run_phys(t, arm, 16, M); Mc = _corrupt(M, set(u1["paid_ids"]), 2121); u2 = F.run_phys(t, arm, 16, Mc)
        d = max(float(np.nanmax(np.abs(np.asarray(e1["p_all"][k], float) - np.asarray(e2["p_all"][k], float)))) for e1, e2 in zip(u1["evals"], u2["evals"]) for k in e1["p_all"])
        sh[arm] = {"same_paid_order": u1["paid_ids"] == u2["paid_ids"], "max_abs_p_diff_all_constructions": d, "construction": u1["construction"],
                   "PASS": bool(u1["paid_ids"] == u2["paid_ids"] and d == 0.0)}
        print(arm, sh[arm], flush=True)
    res["trajectory_shadow"] = sh
    res["status"] = "PASS" if res["H_vs_RC20_CAND"]["PASS"] and res["stage1_reproduction_after_A1"]["PASS"] and all(v["PASS"] for v in sh.values()) else "FAIL"
    (OUT / "RC21_VALIDATION_FINAL.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); print(res["status"])


if __name__ == "__main__":
    main()
