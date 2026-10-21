"""RC24 Stage B pilots on ALREADY-USED DEV data (repeats 51-58 standard startup, k-means geometry blocks seeds 1-8). Pilots check
cost and discriminability of a prototype before any confirmatory run; they never decide a claim.
  b-pilot   P1 = PAC + margin (src.rc24_pac) own-query trajectories on std 51-58 (40) and blocks s1-8 (40), and the PAC family
            (PAC, PAC_PLUG, PAC_FLAT, PAC_GEN, HA_TREND) evaluated on the RC23 HA_LEAN + margin paths of the same tasks (matched, budgets
            8..60 step 4; 80 units). References HA_LEAN / HONLY_LR + margin are the RC23 h-std / h-block units (reused, not rerun).
    python -m src.rc24_pilot work b-pilot
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
import src.rc24_pac as PC

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc24"
R23 = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc23"
MB = tuple(range(8, 61, 4))


def run_pac(task, M, bmax=60, cons="PAC"):
    """PAC-family construction + margin; only that construction is computed."""
    rev = K._rev_with(task, M, []); Z = P.zstd(task); C22.startup(task, rev); nt = len(task["test"]); evals = []; t0 = time.time(); c0 = time.process_time()
    while True:
        b = rev.queries; cands = np.setdiff1d(task["pool"], rev.paid); t1 = time.process_time(); rows = np.r_[task["test"], cands]
        out, info = PC.state(task, rev, Z, rows, (cons,))
        e = {"budget": b, "p": {cons: LN._f32(out[cons][:nt])}}
        if b >= bmax:
            e["cpu_s"] = time.process_time() - t1; evals.append(e); break
        if info.get("one_class"):
            nxt = LN.next_on_path(task, rev); how = "path"
        else:
            nxt = int(cands[int(np.argmax(-np.abs(out[cons][nt:] - 0.5)))]); how = "margin"
        e["cpu_s"] = time.process_time() - t1; e["how"] = how; evals.append(e); rev.reveal(nxt)
    return {"repeat": task["repeat"], "fold": task["fold"], "startup": task.get("startup", "STD"), "block": task.get("block"), "construction": cons, "arm": f"{cons}_MARGIN",
            "paid": rev.order, "paid_ids": [task["ids"][i] for i in rev.order], "test_ids": [task["ids"][i] for i in task["test"]], "evals": evals,
            "seconds": time.time() - t0, "cpu_s": time.process_time() - c0, "queries": rev.queries}


def match_pac(task, unit, M, budgets=MB):
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in unit["paid_ids"]]; evals = []; t0 = time.time()
    for b in budgets:
        if b > len(paid):
            break
        rev = K._rev_with(task, M, paid[:b]); t1 = time.process_time(); out, info = PC.state(task, rev, Z, np.asarray(task["test"]))
        evals.append({"budget": b, "p": {k: LN._f32(v) for k, v in out.items()}, "cpu_s": time.process_time() - t1})
    return {"repeat": task["repeat"], "fold": task["fold"], "block": task.get("block"), "path_of": unit.get("arm", "HA_LEAN"), "paid_ids": unit["paid_ids"][:max(budgets)],
            "test_ids": unit["test_ids"], "evals": evals, "seconds": time.time() - t0}


def units(job):
    if job == "b-pilot":
        return ([(f"STD__r{r}_f{f}__PAC_MARGIN", ("own", "std", r, f)) for r in range(51, 59) for f in range(1, 6)]
                + [(f"s{s}_b{b}__PAC_MARGIN", ("own", "block", s, b)) for s in range(1, 9) for b in range(1, 6)]
                + [(f"MATCH_STD__r{r}_f{f}", ("match", "std", r, f)) for r in range(51, 59) for f in range(1, 6)]
                + [(f"MATCH_BLOCK__s{s}_b{b}", ("match", "block", s, b)) for s in range(1, 9) for b in range(1, 6)])
    if job == "b-smoke":
        return [("STD__r1_f1__PAC_MARGIN", ("own_smoke", "std", 1, 1))]
    raise ValueError(job)


def work(job):
    RC.limit_threads(1); U = units(job); M = P.manifest(); S = dict(U); C22.set_manifest(M)
    reps = sorted({s[2] for s in S.values() if s[1] == "std"}); seeds = sorted({s[2] for s in S.values() if s[1] == "block"})
    T = {(t["repeat"], t["fold"]): t for t in P.tasks(reps)} if reps else {}
    TB = {(t["repeat"], t["fold"]): t for t in C22.block_tasks(seeds, M)} if seeds else {}

    def fn(name):
        kind, part, r, f = S[name]; task = T[(r, f)] if part == "std" else TB[(r, f)]
        if kind == "own":
            return run_pac(task, M)
        if kind == "own_smoke":
            return run_pac(task, M, bmax=16)
        ref = R23 / ("h-std" if part == "std" else "h-block") / "units" / (f"STD__r{r}_f{f}__HA_LEAN.json.gz" if part == "std" else f"s{r}_b{f}__HA_LEAN.json.gz")
        return match_pac(task, RC.read_json_gz(ref), M)
    d = OUT / job
    RC.run_units([n for n, _ in U], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("b-pilot", "b-smoke")})
