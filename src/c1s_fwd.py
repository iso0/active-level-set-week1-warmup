"""C1S fresh test runs (outputs/research_campaign_20261029/opus_c1_stability/PROTOCOL_C1S.md; frozen before any fresh result).

Unit code = src.ea_fwd.unit_L / unit_X, UNCHANGED (the EA / C1C validation code); tasks = src.c1c_fwd.tasks, UNCHANGED:
  L  HA_LEAN + margin own path; on it at every budget 8..60: C1, D, E
  X  C1 + margin own path (unchanged C1); on it at every budget: HA_LEAN
The candidate (AVG4) and the simple controls (EVERY4, FREEZE24) are computed by the evaluator from C1's OWN per-budget probabilities
(src.c1s_dev.variant), so they open exactly the runs C1 opens; no extra query exists.
New IDs (inventory: highest repeat used before = 322):
  STD     323-362 x 5 folds (primary set, 40 clusters)
  RAND8   363-372 x 5 folds   LOCAL8  373-382 x 5 folds   (limited startup control, 10 clusters each)
    python -m src.c1s_fwd work c1s-main | c1s-start | list
"""
from __future__ import annotations

import sys

import src.c1c_fwd as CF
import src.ea_fwd as F
import src.rc18_common as RC
import src.rc19_pool as P
import src.rc22_common as C22

OUT = RC.ROOT / "outputs" / "research_campaign_20261029" / "opus_c1_stability"
MAIN = tuple(range(323, 363)); START = {"RAND8": tuple(range(363, 373)), "LOCAL8": tuple(range(373, 383))}


def units(job):
    if job == "c1s-main":
        return [(f"STD__r{r}_f{f}__{p}", ("STD", r, f, p)) for r in MAIN for f in range(1, 6) for p in ("L", "X")]
    if job == "c1s-start":
        return [(f"{k}__r{r}_f{f}__{p}", (k, r, f, p)) for k, reps in START.items() for r in reps for f in range(1, 6) for p in ("L", "X")]
    raise ValueError(job)


def work(job):
    RC.limit_threads(1); U_ = units(job); M = P.manifest(); S = dict(U_); C22.set_manifest(M)
    import src.c1s_freeze as FR
    FR.check(job)
    T = CF.tasks(S, M)

    def fn(name):
        c, r, f, p = S[name]; task = T[(c, r, f)]
        return {**(F.unit_L(task, M, 60) if p == "L" else F.unit_X(task, M, 60)), "condition": c, "startup": task.get("startup", "STD")}
    d = OUT / job
    RC.run_units([n for n, _ in U_], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("c1s-main", "c1s-start")})
