"""RC23 unit lists (queue src/rc23_runner.ps1, plan opus_rc23/runner/PLAN.json).
  h-match  matched states: the RC22 g-acq A1_MARGIN (PHR_NRMAP) and A5_SIMPLE (HA_LR) paid prefixes, repeats 43-50, budgets 8..60 step 4;
           all four constructions on identical prefixes (+ candidate probabilities for ranking agreement)
  h-std    prospective, FRESH repeats 51-58 (never run: RC19 1-10, RC19B 11-18, RC20 19-26, RC21 27-34, RC21B 35-42, RC22 43-50),
           standard startup, all four arms
  h-rob    robustness on the RC21B / RC22 splits (repeats 35-42), startups STD / RAND8 / LOCAL8, arms HA_LR, HA_LEAN, HONLY_LR
           (PHR_NRMAP reused: RC21B e-final STD, RC22 g-start RAND8 / LOCAL8)
  h-block  geometry blocks (RC22 k-means k = 5) x seeds 1-8, arms HA_LR, HA_LEAN, HONLY_LR (PHR_NRMAP reused: RC22 g-block)
  h-smoke  a few units on DEV repeat 1 / seed 1
    python -m src.rc23_jobs work <job> [--threads 1]
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
import src.rc23_common as C

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc23"
ACQ = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc22" / "g-acq" / "units"
MB = tuple(range(8, 61, 4))
REP_STD = tuple(range(51, 59)); REP_ROB = tuple(range(35, 43)); SEEDS = tuple(range(1, 9))
NEW_ARMS = ("HA_LR", "HA_LEAN", "HONLY_LR")


def match_unit(task, unit, M):
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in unit["paid_ids"]]; nt = len(task["test"]); evals = []; t0 = time.time()
    rec = {e["budget"]: {**e.get("p_all", {}), **e["p"]} for e in unit["evals"]}
    for b in MB:
        rev = K._rev_with(task, M, paid[:b]); cands = np.setdiff1d(task["pool"], rev.paid); t1 = time.process_time()
        out, info = C.state(task, rev, Z, np.r_[task["test"], cands])
        e = {"budget": b, "p": {k: LN._f32(v[:nt]) for k, v in out.items()}, "one_class": info["one_class"], "cpu_s": time.process_time() - t1,
             "check_vs_rc22": {k: float(np.nanmax(np.abs(out[k][:nt] - np.asarray(rec[b][k], float)))) for k in out if k in rec[b] and not info["one_class"]}}
        if not info["one_class"]:
            e["cand"] = {"cand_rows": [int(i) for i in cands], **{f"p:{k}": LN._f32(v[nt:]) for k, v in out.items()}}
        evals.append(e)
    return {"repeat": task["repeat"], "fold": task["fold"], "path_of": unit["arm"], "paid_ids": unit["paid_ids"][:max(MB)], "test_ids": unit["test_ids"], "evals": evals,
            "seconds": time.time() - t0}


def units(job):
    if job == "h-match":
        return [(f"r{r}_f{f}__{a}", ("match", a, r, f, None)) for r in range(43, 51) for f in range(1, 6) for a in ("A1_MARGIN", "A5_SIMPLE")]
    if job == "h-std":
        return [(f"STD__r{r}_f{f}__{a}", ("seq", a, r, f, "STD")) for r in REP_STD for f in range(1, 6) for a in C.CONS]
    if job == "h-rob":
        return [(f"{st}__r{r}_f{f}__{a}", ("seq", a, r, f, st)) for st in ("STD", "RAND8", "LOCAL8") for r in REP_ROB for f in range(1, 6) for a in NEW_ARMS]
    if job == "h-block":
        return [(f"s{s}_b{b}__{a}", ("block", a, s, b, None)) for s in SEEDS for b in range(1, 6) for a in NEW_ARMS]
    if job == "h-smoke":
        return [(f"LOCAL8__r1_f1__{a}", ("seq", a, 1, 1, "LOCAL8")) for a in C.CONS] + [(f"s1_b2__{a}", ("block", a, 1, 2, None)) for a in ("HA_LEAN", "HONLY_LR")]
    raise ValueError(job)


def work(job):
    RC.limit_threads(1); U = units(job); M = P.manifest(); S = dict(U); C22.set_manifest(M)
    import src.rc23_freeze as FR
    FR.check(job)
    kinds = {s[0] for s in S.values()}; T, TB = {}, {}
    if kinds & {"match", "seq"}:
        T = {(t["repeat"], t["fold"]): t for t in P.tasks(sorted({s[2] for s in S.values() if s[0] != "block"}))}
    if "block" in kinds:
        TB = {(t["repeat"], t["fold"]): t for t in C22.block_tasks(sorted({s[2] for s in S.values() if s[0] == "block"}), M)}

    def fn(name):
        kind, a, r, f, st = S[name]
        if kind == "match":
            return match_unit(T[(r, f)], RC.read_json_gz(ACQ / f"r{r}_f{f}__{a}.json.gz"), M)
        task = TB[(r, f)] if kind == "block" else C22.startup_task(T[(r, f)], st)
        return C.run_arm(task, a, M)
    d = OUT / job
    RC.run_units([n for n, _ in U], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("h-match", "h-std", "h-rob", "h-block", "h-smoke")})
