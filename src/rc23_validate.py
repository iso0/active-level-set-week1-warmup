"""RC23 numerical acceptance (no evaluation metric):
  1. reproduction: HA_LR = the RC22 A5_SIMPLE trajectory (r43 f1) and PHR_NRMAP = the RC22 RAND8 REF trajectory (r35 f1) exactly;
     HONLY_LR = the RC22 g-ingr value;
  2. channel independence: changing or removing the PAID temperature / spike values leaves HA_LEAN and HONLY_LR identical
     (state and whole trajectory), while the three-channel constructions do change;
  3. shadow: randomising every never-paid outcome leaves HA_LEAN / HONLY_LR trajectories (predictions and next queries) identical;
  4. honest cross-fitting of the depth-only upstream: a paid run's own depth never changes its own out-of-fold feature;
  5. timing: CPU per paid state of each construction computed ALONE (upstream + classifier).
    python -m src.rc23_validate
"""
from __future__ import annotations

import json
import time

import numpy as np

import src.rc18_common as RC
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc20_attr as A
import src.rc22_common as C22
import src.rc23_common as C
from src.rc19_validate import _corrupt

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc23"
R22 = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc22"
TS = (C22.ATS_T, C22.ATS_S); TS_COLS = ("tmax_T0_K", "vmax_spike_logratio")


def _ts_corrupt(M, seed):
    rng = np.random.default_rng(seed); X = M.copy()
    for c in TS_COLS:
        X[c] = rng.normal(0, 10, len(X))
    return X


def main():
    RC.limit_threads(1); M = P.manifest(); C22.set_manifest(M); res = {"utc": RC.utc()}; T = {(t["repeat"], t["fold"]): t for t in P.tasks([1, 35, 43])}
    # 1. reproduction
    ref = RC.read_json_gz(R22 / "g-acq" / "units" / "r43_f1__A5_SIMPLE.json.gz"); u = C.run_arm(T[(43, 1)], "HA_LR", M)
    ok1 = u["paid_ids"] == ref["paid_ids"] and all(a["p"]["HA_LR"] == b["p"]["HA_LR"] for a, b in zip(u["evals"], ref["evals"]))
    ref2 = RC.read_json_gz(R22 / "g-start" / "units" / "RAND8__r35_f1__REF.json.gz"); u2 = C.run_arm(C22.startup_task(T[(35, 1)], "RAND8"), "PHR_NRMAP", M)
    ok2 = u2["paid_ids"] == ref2["paid_ids"] and all(a["p"]["PHR_NRMAP"] == b["p"]["PHR_NRMAP"] for a, b in zip(u2["evals"], ref2["evals"]))
    gi = RC.read_json_gz(R22 / "g-ingr" / "units" / "r35_f1__H_MARGIN.json.gz"); t = T[(35, 1)]; pos = {s: i for i, s in enumerate(t["ids"])}
    e24 = [e for e in gi["evals"] if e["budget"] == 24][0]; rev = K._rev_with(t, M, [pos[s] for s in gi["paid_ids"][:24]]); Z = P.zstd(t)
    o, _ = C.state(t, rev, Z, t["test"], which=("HONLY_LR",)); d3 = float(np.max(np.abs(np.asarray(e24["p"]["HONLY_LR"], float) - np.float32(o["HONLY_LR"]).astype(float))))
    res["reproduction"] = {"HA_LR_vs_RC22_A5_r43_f1": bool(ok1), "PHR_NRMAP_vs_RC22_RAND8_r35_f1": bool(ok2), "HONLY_LR_vs_RC22_ingr_max_abs": d3, "PASS": bool(ok1 and ok2 and d3 == 0.0)}
    print(res["reproduction"], flush=True)
    # 2. channel independence (state)
    rows = np.r_[t["test"], np.setdiff1d(t["pool"], rev.paid)]; base, _ = C.state(t, rev, Z, rows); ch = {}
    for kind in ("nan", "random"):
        r2 = K._rev_with(t, M, [pos[s] for s in gi["paid_ids"][:24]]); rng = np.random.default_rng(23)
        for i in r2.paid:
            for k in TS:
                r2._Y[i, k] = np.nan if kind == "nan" else rng.normal(0, 10)
        which = C.CONS if kind == "random" else ("HA_LEAN", "HONLY_LR")
        o2, _ = C.state(t, r2, Z, rows, which=which); ch[kind] = {k: float(np.max(np.abs(o2[k] - base[k]))) for k in which}
        if kind == "nan":                                                  # the three-channel upstream cannot run with a channel absent
            try:
                o3, _ = C.state(t, r2, Z, rows, which=("HA_LR",)); ch[kind]["HA_LR_finite"] = bool(np.all(np.isfinite(o3["HA_LR"])))
            except Exception as ex:
                ch[kind]["HA_LR_error"] = type(ex).__name__
    # 2b. trajectory with every run's T / S replaced
    tl = C22.startup_task(T[(1, 1)], "LOCAL8"); traj = {}
    for cons in ("HA_LEAN", "HONLY_LR"):
        a = C.run_arm(tl, cons, M, bmax=24); b = C.run_arm(tl, cons, _ts_corrupt(M, 7), bmax=24)
        traj[cons] = bool(a["paid_ids"] == b["paid_ids"] and all(x["p"] == y["p"] for x, y in zip(a["evals"], b["evals"])))
    res["channel_independence"] = {"state_change_max": ch, "trajectory_identical_with_all_TS_replaced": traj,
                                   "PASS": bool(all(ch[k]["HA_LEAN"] == 0.0 and ch[k]["HONLY_LR"] == 0.0 for k in ch) and all(traj.values())
                                                and ch["random"]["PHR_NRMAP"] > 0 and ch["random"]["HA_LR"] > 0)}
    print(res["channel_independence"], flush=True)
    # 3. shadow
    sh = {}
    for cons in ("HA_LEAN", "HONLY_LR"):
        a = C.run_arm(tl, cons, M, bmax=22); b = C.run_arm(tl, cons, _corrupt(M, set(a["paid_ids"]), 2301), bmax=22)
        sh[cons] = bool(a["paid_ids"] == b["paid_ids"] and all(x["p"] == y["p"] for x, y in zip(a["evals"], b["evals"])))
    res["shadow"] = {**sh, "PASS": bool(all(sh.values()))}; print(res["shadow"], flush=True)
    # 4. honesty of the depth-only upstream
    paid = [pos[s] for s in gi["paid_ids"][:24]]; r0 = K._rev_with(t, M, paid); R0 = A.cf(Z, r0, C.DEPTH, "SHQ", t["test"][:3], A.KF); fold, k = K.folds(len(paid), A.KF)
    worst, other = 0.0, 0
    for j in (1, 7, 15):
        r1 = K._rev_with(t, M, paid); i = paid[j]; r1._A[i] *= 1.6
        r1._Y[i, 0] = r1._Y[i, 0] + 0.5
        R1 = A.cf(Z, r1, C.DEPTH, "SHQ", t["test"][:3], A.KF); worst = max(worst, float(abs(R1["F"][j, 0] - R0["F"][j, 0])))
        other += int(np.any(np.abs(R1["F"][fold != fold[j], 0] - R0["F"][fold != fold[j], 0]) > 1e-9))
    res["honesty_depth_only"] = {"own_change_max": worst, "other_folds_changed_cases": other, "PASS": bool(worst == 0.0 and other > 0)}; print(res["honesty_depth_only"], flush=True)
    # 5. timing (each construction alone)
    tm = []
    for b in (16, 40, 60):
        rv = K._rev_with(t, M, [pos[s] for s in gi["paid_ids"][:b]]); rw = np.r_[t["test"], np.setdiff1d(t["pool"], rv.paid)]
        row = {"budget": b}
        for cons in C.CONS:
            c0 = time.process_time()
            for _ in range(3):
                C.state(t, rv, Z, rw, which=(cons,))
            row[cons] = (time.process_time() - c0) / 3
        tm.append(row)
    res["timing_cpu_s_per_state"] = tm; print(tm, flush=True)
    res["status"] = "PASS" if all(v["PASS"] for v in res.values() if isinstance(v, dict) and "PASS" in v) else "FAIL"
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "RC23_VALIDATION.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8"); print(res["status"])


if __name__ == "__main__":
    main()
