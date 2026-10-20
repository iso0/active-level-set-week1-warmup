"""RC21B unit lists for the persistent queue (src/rc21_runner.ps1; plan opus_rc21/runner/PLAN.json): e-final / e-smoke
(src.rc21b_final). Outputs: outputs/research_campaign_20261020/opus_rc21/<job>/units/<unit>.json.gz (src/rc18_common.run_units).
    python -m src.rc21b_jobs work <job> [--threads 1]        (set RC18_DEADLINE_UTC to the RC20/RC21 deadline when run by hand)
"""
from __future__ import annotations

import sys

import src.rc18_common as RC
import src.rc19_pool as P
import src.rc21b_final as F

OUT = F.OUT


def work(job):
    RC.limit_threads(1); U = F.units(job); M = P.manifest(); spec = dict(U); reps = sorted({s[2] for _, s in U}); T = {(t["repeat"], t["fold"]): t for t in P.tasks(reps)}
    if job == "e-final":
        F.check()                                                         # frozen hashes verified before any final unit

    def fn(name):
        _, a, r, f = spec[name]
        return F.run_unit(a, T[(r, f)], M)
    d = OUT / job
    RC.run_units([n for n, _ in U], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
