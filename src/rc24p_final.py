"""RC24 post-audit FINAL comparison (registered in post_audit/PROTOCOL_RC24P_FINAL.md before any of its outcomes).
Own-query arms (margin -|p - 0.5| everywhere, standard 8-point label-free maximin startup counted, budgets 8..60):
  F_HA_LEAN     RC23 D1 HA_LEAN (src.rc23_common.run_arm; = TR_NONE)
  F_HA_TREND    RC24 HA_TREND (src.rc24_pilot.run_pac cons HA_TREND; = TR_PHYS)
  F_HONLY       h-only learned-regularisation classifier (src.rc23_common.run_arm HONLY_LR)
  F_TR_GEN15    generic log-input trend control with the prior variance matched to TR_PHYS (src.rc24p_models TR_GEN15)
Conditions (all on the SAME 541-run pool; none is independent physical data):
  STD      fresh random-split repeats 75-82 (repeats 1-74 used before)
  BLOCK_A  the RC22 k-means k = 5 partition (seed 2222) - the SAME five regions as RC23 / RC24 - with NEW startups 17-24
  BLOCK_B  a NEW partition: k-means k = 4 (n_init 20, seed 2222) on the same public standardised log inputs, startups 1-8
Matched (f-match): on every F_HA_LEAN path, TR_NONE, TR_PHYS, TR_GEN3, TR_GEN15 and HONLY_LR at budgets 8..60 step 4.
    python -m src.rc24p_final work f-own | f-match | f-smoke
"""
from __future__ import annotations

import sys
import time

import numpy as np

import src.rc18_common as RC
import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc22_common as C22
import src.rc23_common as C23
import src.rc24p_models as TM

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc24"
REP_F = tuple(range(75, 83)); START_A = tuple(range(17, 25)); START_B = tuple(range(1, 9)); MB4 = tuple(range(8, 61, 4))
ARMS = ("F_HA_LEAN", "F_HA_TREND", "F_HONLY", "F_TR_GEN15")
COND = ("STD", "BLOCK_A", "BLOCK_B")


def blocks_k4(M):
    from sklearn.cluster import KMeans
    X = M[list(P.INPUTS)].to_numpy(float); return KMeans(n_clusters=4, n_init=20, random_state=C22.SEED).fit_predict(C22._z_all(X))


def block_tasks_b(starts, M):
    from src.external_validation.analysis import boundary_flags
    from src.week13_synthetic_al import maximin_order
    ids = M.index.to_numpy(str); X = M[list(P.INPUTS)].to_numpy(float); lab = blocks_k4(M); out = []
    for s in starts:
        for b in range(lab.max() + 1):
            test = np.flatnonzero(lab == b); pool = np.flatnonzero(lab != b)
            order = maximin_order(X[pool], np.random.default_rng([C22.SEED, 4, s, b + 1, 3])); path = pool[order]
            q20 = boundary_flags(X, M.y.to_numpy(int), test, ids, "entire_evaluation_batch")[20]
            out.append({"repeat": int(s), "fold": b + 1, "ids": ids, "X": X, "pool": pool, "test": test, "path": path, "q20": q20, "block": b, "startup": "STD", "partition": "k4"})
    return out


def run_trend(task, M, cons, bmax=60):
    rev = K._rev_with(task, M, []); Z = P.zstd(task); C22.startup(task, rev); nt = len(task["test"]); evals = []; t0 = time.time(); c0 = time.process_time()
    while True:
        b = rev.queries; cands = np.setdiff1d(task["pool"], rev.paid); t1 = time.process_time(); rows = np.r_[task["test"], cands]
        out, info = TM.state(task, rev, Z, rows, (cons,)); e = {"budget": b, "p": {cons: LN._f32(out[cons][:nt])}}
        if b >= bmax:
            e["cpu_s"] = time.process_time() - t1; evals.append(e); break
        if info.get("one_class"):
            nxt = LN.next_on_path(task, rev); how = "path"
        else:
            nxt = int(cands[int(np.argmax(-np.abs(out[cons][nt:] - 0.5)))]); how = "margin"
        e["cpu_s"] = time.process_time() - t1; e["how"] = how; evals.append(e); rev.reveal(nxt)
    return {"repeat": task["repeat"], "fold": task["fold"], "block": task.get("block"), "construction": cons, "paid": rev.order, "paid_ids": [task["ids"][i] for i in rev.order],
            "test_ids": [task["ids"][i] for i in task["test"]], "evals": evals, "seconds": time.time() - t0, "cpu_s": time.process_time() - c0, "queries": rev.queries}


def run_own(task, arm, M, bmax=60):
    import src.rc24_pilot as PL
    if arm == "F_HA_LEAN":
        u = C23.run_arm(task, "HA_LEAN", M, bmax=bmax)
    elif arm == "F_HONLY":
        u = C23.run_arm(task, "HONLY_LR", M, bmax=bmax)
    elif arm == "F_HA_TREND":
        u = PL.run_pac(task, M, bmax=bmax, cons="HA_TREND")
    elif arm == "F_TR_GEN15":
        u = run_trend(task, M, "TR_GEN15", bmax=bmax)
    else:
        raise ValueError(arm)
    u["arm"] = arm; u["partition"] = task.get("partition", "k5" if task.get("block") is not None else None); return u


def match_unit(task, unit, M, budgets=MB4):
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in unit["paid_ids"]]; rows = np.asarray(task["test"]); evals = []; t0 = time.time()
    own = {e["budget"]: e["p"] for e in unit["evals"]}
    for b in budgets:
        rev = K._rev_with(task, M, paid[:b]); t1 = time.process_time(); o1, _ = TM.state(task, rev, Z, rows); o2, _ = C23.state(task, rev, Z, rows, which=("HONLY_LR",))
        chk = float(np.max(np.abs(np.asarray(o1["TR_NONE"], float).astype(np.float32).astype(float) - np.asarray(own[b]["HA_LEAN"], float))))
        evals.append({"budget": b, "p": {**{k: LN._f32(v) for k, v in o1.items()}, "HONLY_LR": LN._f32(o2["HONLY_LR"])}, "cpu_s": time.process_time() - t1, "check_TR_NONE_vs_own_HA_LEAN": chk})
    return {"repeat": task["repeat"], "fold": task["fold"], "block": task.get("block"), "partition": unit.get("partition"), "path_of": "F_HA_LEAN", "paid_ids": unit["paid_ids"][:max(budgets)],
            "test_ids": unit["test_ids"], "evals": evals, "seconds": time.time() - t0}


def units(job):
    if job == "f-own":
        return ([(f"STD__r{r}_f{f}__{a}", ("own", "STD", r, f, a)) for r in REP_F for f in range(1, 6) for a in ARMS]
                + [(f"BLOCK_A__s{s}_b{b}__{a}", ("own", "BLOCK_A", s, b, a)) for s in START_A for b in range(1, 6) for a in ARMS]
                + [(f"BLOCK_B__s{s}_b{b}__{a}", ("own", "BLOCK_B", s, b, a)) for s in START_B for b in range(1, 5) for a in ARMS])
    if job == "f-match":
        return ([(f"MATCH_STD__r{r}_f{f}", ("match", "STD", r, f, "F_HA_LEAN")) for r in REP_F for f in range(1, 6)]
                + [(f"MATCH_BLOCK_A__s{s}_b{b}", ("match", "BLOCK_A", s, b, "F_HA_LEAN")) for s in START_A for b in range(1, 6)]
                + [(f"MATCH_BLOCK_B__s{s}_b{b}", ("match", "BLOCK_B", s, b, "F_HA_LEAN")) for s in START_B for b in range(1, 5)])
    if job == "f-smoke":
        return [(f"STD__r1_f1__{a}", ("smoke", "STD", 1, 1, a)) for a in ARMS] + [("BLOCK_B__s1_b1__F_TR_GEN15", ("smoke", "BLOCK_B", 1, 1, "F_TR_GEN15"))]
    raise ValueError(job)


def tasks_for(S, M):
    T = {}
    reps = sorted({s[2] for s in S.values() if s[1] == "STD"}); a = sorted({s[2] for s in S.values() if s[1] == "BLOCK_A"}); b = sorted({s[2] for s in S.values() if s[1] == "BLOCK_B"})
    if reps:
        T.update({("STD", t["repeat"], t["fold"]): t for t in P.tasks(reps)})
    if a:
        T.update({("BLOCK_A", t["repeat"], t["fold"]): {**t, "partition": "k5"} for t in C22.block_tasks(a, M)})
    if b:
        T.update({("BLOCK_B", t["repeat"], t["fold"]): t for t in block_tasks_b(b, M)})
    return T


def work(job):
    RC.limit_threads(1); U = units(job); M = P.manifest(); S = dict(U); C22.set_manifest(M)
    import src.rc24p_freeze as FR
    FR.check(job)
    T = tasks_for(S, M)

    def fn(name):
        kind, cond, r, f, a = S[name]; task = T[(cond, r, f)]
        if kind == "own":
            return {**run_own(task, a, M), "condition": cond}
        if kind == "smoke":
            return {**run_own(task, a, M, bmax=14), "condition": cond}
        ref = OUT / "f-own" / "units" / (f"STD__r{r}_f{f}__F_HA_LEAN.json.gz" if cond == "STD" else f"{cond}__s{r}_b{f}__F_HA_LEAN.json.gz")
        return {**match_unit(task, RC.read_json_gz(ref), M), "condition": cond}
    d = OUT / job
    RC.run_units([n for n, _ in U], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("f-own", "f-match", "f-smoke")})
