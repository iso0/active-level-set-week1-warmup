"""EL study FORWARD validation runs (PROTOCOL_EL_OBJECTIVES.md section 8; frozen by PROTOCOL_EL_FINAL.md before any run).
Per task, two units - one per selection path:
  path L  HA_LEAN selects (src.rc23_common.run_arm HA_LEAN, unchanged): own predictions = system A; HA_TREND predictions on the same
          path at every budget = system D;
  path T  HA_TREND selects (src.rc24_pilot.run_pac HA_TREND, unchanged): own predictions = system B; HA_LEAN predictions on the same
          path at every budget = system C.
Each cross prediction at budget b uses only the first b paid runs of the path (src.el_cross.cross_unit). CPU is recorded per step for
the selector (own state on test + candidates, then margin) and the predictor (fit + prediction at the test rows).
Fresh IDs (never run before): STD repeats 83-122 x 5 folds; K5 (the RC22 k = 5 regions) startups 25-32; K4 (the RC24P k = 4 partition)
startups 9-16.
    python -m src.el_final work el-fwd | el-smoke
"""
from __future__ import annotations

import sys

import src.el_cross as X
import src.rc18_common as RC
import src.rc19_pool as P
import src.rc22_common as C22
import src.rc23_common as C23

OUT = X.OUT
REP_F = tuple(range(83, 123)); K5_F = tuple(range(25, 33)); K4_F = tuple(range(9, 17))
PATHS = ("L", "T")
EXTRA = ()            # stage-2 system own paths, if registered in PROTOCOL_EL_FINAL.md (none at this point)


def run_path(task, which, M, bmax=60):
    import src.rc24_pilot as PL
    if which == "L":
        u = C23.run_arm(task, "HA_LEAN", M, bmax=bmax); other = "HA_TREND"
    elif which == "T":
        u = PL.run_pac(task, M, bmax=bmax, cons="HA_TREND"); other = "HA_LEAN"
    else:
        raise ValueError(which)
    ev, sec = X.cross_unit(task, u, other, tuple(range(8, bmax + 1)), M)
    u["cross"] = {"predicts": other, "evals": ev, "seconds_wall": sec}; u["selects"] = "HA_LEAN" if which == "L" else "HA_TREND"; u["path"] = which
    return u


def units(job):
    if job == "el-fwd":
        return ([(f"STD__r{r}_f{f}__{p}", ("STD", r, f, p)) for r in REP_F for f in range(1, 6) for p in PATHS]
                + [(f"K5__s{s}_b{b}__{p}", ("K5", s, b, p)) for s in K5_F for b in range(1, 6) for p in PATHS]
                + [(f"K4__s{s}_b{b}__{p}", ("K4", s, b, p)) for s in K4_F for b in range(1, 5) for p in PATHS])
    if job == "el-smoke":
        return [(f"STD__r1_f1__{p}", ("STD", 1, 1, p)) for p in PATHS]
    raise ValueError(job)


def work(job):
    RC.limit_threads(1); U = units(job); M = P.manifest(); S = dict(U); C22.set_manifest(M)
    import src.el_freeze as FR
    FR.check(job)
    T = X.tasks_for({n: (None, c, r, f) for n, (c, r, f, p) in S.items()}, M)

    def fn(name):
        c, r, f, p = S[name]; task = T[(c, r, f)]
        return {**run_path(task, p, M, bmax=14 if job == "el-smoke" else 60), "condition": c}
    d = OUT / job
    RC.run_units([n for n, _ in U], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("el-fwd", "el-smoke")})
