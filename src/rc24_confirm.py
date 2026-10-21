"""RC24 Stage C - confirmatory test of the Stage B candidate on FRESH data (registered in PROTOCOL_RC24_STAGE_C.md before any run).
  c-own    own-query trajectories, budgets 8..60:
             standard startup, fresh repeats 67-74 (never run: 1-66 used by RC19-RC24) x 5 folds
             geometry blocks (RC22 k-means k = 5 on the public standardised log inputs), fresh seeds 9-16 (RC22/RC23 used 1-8) x 5 blocks
           arms ARMS (reference HA_LEAN_MARGIN, strong baseline HONLY_MARGIN, candidate(s))
  c-match  matched evaluation on every HA_LEAN_MARGIN and HONLY_MARGIN path of c-own: HA_LEAN, HONLY_LR, HA_TREND, HA_TREND_B1,
           HA_TREND_B10, PAC, PAC_GEN (prior sensitivity and falsifying controls on identical paid samples), every budget 8..60.
           HA_TREND on the HONLY_MARGIN path is exactly the own-query trajectory of the decoupled system HT_PHYS (HA_TREND predicts,
           the h-only classifier's margin chooses the queries): its acquisition never reads the HA_TREND predictions, so its paths are
           the HONLY_MARGIN paths.
  c-smoke  one unit per arm on DEV repeat 1 fold 1 (budget 14)
    python -m src.rc24_confirm work <job>
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
import src.rc24_pac as PC

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc24"
REP_C = tuple(range(67, 75)); SEEDS_C = tuple(range(9, 17)); MB = tuple(range(8, 61))
ARMS = ("HA_LEAN_MARGIN", "HONLY_MARGIN", "HA_TREND_MARGIN")
MATCH_CONS = ("HA_LEAN", "HONLY_LR", "HA_TREND", "HA_TREND_B1", "HA_TREND_B10", "PAC", "PAC_GEN")
MATCH_PATHS = ("HA_LEAN_MARGIN", "HONLY_MARGIN")      # HA_TREND on the HONLY_MARGIN path IS the decoupled system HT_PHYS (its acquisition reads only h)


def run_own(task, arm, M, bmax=60):
    import src.rc24_pilot as PL
    if arm in ("HA_LEAN_MARGIN", "HONLY_MARGIN"):
        u = C23.run_arm(task, "HA_LEAN" if arm == "HA_LEAN_MARGIN" else "HONLY_LR", M, bmax=bmax)
    elif arm == "HA_TREND_MARGIN":
        u = PL.run_pac(task, M, bmax=bmax, cons="HA_TREND")
    elif arm == "PAC_JEER":
        u = PL.run_jeer(task, M, bmax=bmax)
    else:
        raise ValueError(arm)
    u["arm"] = arm; return u


def match_unit(task, unit, M, budgets=MB):
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in unit["paid_ids"]]; nt = len(task["test"]); evals = []; t0 = time.time()
    own = {e["budget"]: e["p"] for e in unit["evals"]}
    for b in budgets:
        if b > len(paid):
            break
        rev = K._rev_with(task, M, paid[:b]); t1 = time.process_time(); rows = np.asarray(task["test"])
        o1, _ = C23.state(task, rev, Z, rows, which=("HA_LEAN", "HONLY_LR")); o2, _ = PC.state(task, rev, Z, rows, tuple(c for c in MATCH_CONS if c not in o1))
        out = {**o1, **o2}; chk = {k: float(np.max(np.abs(np.asarray(out[k], float).astype(np.float32).astype(float) - np.asarray(own[b][k], float)))) for k in own.get(b, {}) if k in out}
        evals.append({"budget": b, "p": {k: LN._f32(out[k]) for k in MATCH_CONS}, "cpu_s": time.process_time() - t1, "check_vs_own": chk})
    return {"repeat": task["repeat"], "fold": task["fold"], "block": task.get("block"), "path_of": unit["arm"], "paid_ids": unit["paid_ids"][:max(budgets)],
            "test_ids": unit["test_ids"], "evals": evals, "seconds": time.time() - t0}


def units(job, arms=None):
    arms = ARMS if arms is None else arms
    if job == "c-own":
        return ([(f"STD__r{r}_f{f}__{a}", ("own", "std", r, f, a)) for r in REP_C for f in range(1, 6) for a in arms]
                + [(f"BLOCK__s{s}_b{b}__{a}", ("own", "block", s, b, a)) for s in SEEDS_C for b in range(1, 6) for a in arms])
    if job == "c-match":
        return ([(f"MATCH_STD__r{r}_f{f}__{a}", ("match", "std", r, f, a)) for r in REP_C for f in range(1, 6) for a in MATCH_PATHS]
                + [(f"MATCH_BLOCK__s{s}_b{b}__{a}", ("match", "block", s, b, a)) for s in SEEDS_C for b in range(1, 6) for a in MATCH_PATHS])
    if job == "c-smoke":
        return [(f"STD__r1_f1__{a}", ("smoke", "std", 1, 1, a)) for a in arms]
    raise ValueError(job)


def work(job):
    RC.limit_threads(1); U = units(job); M = P.manifest(); S = dict(U); C22.set_manifest(M)
    import src.rc24_freeze as FR
    FR.check(job)
    reps = sorted({s[2] for s in S.values() if s[1] == "std"}); seeds = sorted({s[2] for s in S.values() if s[1] == "block"})
    T = {(t["repeat"], t["fold"]): t for t in P.tasks(reps)} if reps else {}
    TB = {(t["repeat"], t["fold"]): t for t in C22.block_tasks(seeds, M)} if seeds else {}

    def fn(name):
        kind, part, r, f, a = S[name]; task = T[(r, f)] if part == "std" else TB[(r, f)]
        if kind == "own":
            return run_own(task, a, M)
        if kind == "smoke":
            return run_own(task, a, M, bmax=14)
        ref = OUT / "c-own" / "units" / (f"STD__r{r}_f{f}__{a}.json.gz" if part == "std" else f"BLOCK__s{r}_b{f}__{a}.json.gz")
        return match_unit(task, RC.read_json_gz(ref), M)
    d = OUT / job
    RC.run_units([n for n, _ in U], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("c-own", "c-match", "c-smoke")})
