"""RC24 post-audit queue units (runner src/rc24_runner.ps1, plan opus_rc24/runner/PLAN.json; the RC24 window is NOT restarted).
  p-match  DEVELOPMENT / diagnostic: the clean trend family (src.rc24p_models: TR_NONE = HA_LEAN, TR_PHYS = HA_TREND, TR_GEN3,
           TR_GEN15) and HONLY_LR evaluated on EXISTING HA_LEAN + margin query paths (same paid samples), budgets 8..60 step 4:
             RC23 h-std repeats 51-58, RC23 h-block startups 1-8, RC24 Stage A repeats 59-66, RC24 Stage C repeats 67-74 and block
             startups 9-16 (all DEV; Stage C data are re-used here post hoc and labelled so)
    python -m src.rc24p_jobs work <job>
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
R23 = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc23"
MB4 = tuple(range(8, 61, 4))
SOURCES = {"rc23_std": ("std", range(51, 59), lambda r, f: R23 / "h-std" / "units" / f"STD__r{r}_f{f}__HA_LEAN.json.gz"),
           "rc23_block": ("block", range(1, 9), lambda s, b: R23 / "h-block" / "units" / f"s{s}_b{b}__HA_LEAN.json.gz"),
           "stagea_std": ("std", range(59, 67), lambda r, f: OUT / "a-own" / "units" / f"HA_LEAN_MARGIN__r{r}_f{f}.json.gz"),
           "stagec_std": ("std", range(67, 75), lambda r, f: OUT / "c-own" / "units" / f"STD__r{r}_f{f}__HA_LEAN_MARGIN.json.gz"),
           "stagec_block": ("block", range(9, 17), lambda s, b: OUT / "c-own" / "units" / f"BLOCK__s{s}_b{b}__HA_LEAN_MARGIN.json.gz")}


def match_unit(task, unit, M, src, budgets=MB4):
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in unit["paid_ids"]]; rows = np.asarray(task["test"]); evals = []; t0 = time.time()
    for b in budgets:
        if b > len(paid):
            break
        rev = K._rev_with(task, M, paid[:b]); t1 = time.process_time()
        o1, _ = TM.state(task, rev, Z, rows); o2, _ = C23.state(task, rev, Z, rows, which=("HONLY_LR",))
        evals.append({"budget": b, "p": {**{k: LN._f32(v) for k, v in o1.items()}, "HONLY_LR": LN._f32(o2["HONLY_LR"])}, "cpu_s": time.process_time() - t1})
    return {"source": src, "repeat": task["repeat"], "fold": task["fold"], "block": task.get("block"), "path_of": "HA_LEAN_MARGIN", "paid_ids": unit["paid_ids"][:max(budgets)],
            "test_ids": unit["test_ids"], "evals": evals, "seconds": time.time() - t0}


def units(job):
    if job == "p-match":
        return [(f"{src}__r{r}_f{f}", ("match", src, r, f)) for src, (part, reps, _) in SOURCES.items() for r in reps for f in range(1, 6)]
    raise ValueError(job)


def work(job):
    RC.limit_threads(1); U = units(job); M = P.manifest(); S = dict(U); C22.set_manifest(M)
    std_reps = sorted({r for k, (kind, src, r, f) in S.items() if SOURCES[src][0] == "std"}); blk = sorted({r for k, (kind, src, r, f) in S.items() if SOURCES[src][0] == "block"})
    T = {(t["repeat"], t["fold"]): t for t in P.tasks(std_reps)} if std_reps else {}
    TB = {(t["repeat"], t["fold"]): t for t in C22.block_tasks(blk, M)} if blk else {}

    def fn(name):
        kind, src, r, f = S[name]; part, _, path = SOURCES[src]; task = T[(r, f)] if part == "std" else TB[(r, f)]
        return match_unit(task, RC.read_json_gz(path(r, f)), M, src)
    d = OUT / job
    RC.run_units([n for n, _ in U], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("p-match",)})
