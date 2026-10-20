"""RC21 unit lists for the persistent queue (src/rc21_runner.ps1; plan opus_rc21/runner/PLAN.json).
d-replay: matched-path replays of the RC21 constructions on the SAME paid prefixes of the 200 RC19B final trajectories (repeats
  11-18, every arm's own path) at budgets 8, 12, ..., 60. Only PHR / PHR_NR / PHR_FX / PHR_FXMAP and SHQ_ATS_H (the reproduction
  check against the RC20 c-replay cache) are computed; SHQ_ATS_X is NOT recomputed (read from the RC20 c-replay-x cache), and
  the system controls E1RAW, E1CAL, ATSAPPROX and G3 are read from the RC19B caches.
d-final / d-smoke: the RC21 sequential stage (src.rc21_final).
Outputs: outputs/research_campaign_20261020/opus_rc21/<job>/units/<unit>.json.gz (unit protocol of src/rc18_common.run_units).
    python -m src.rc21_jobs work <job> [--threads 1]        (set RC18_DEADLINE_UTC to the RC20/RC21 deadline when run by hand)
"""
from __future__ import annotations

import sys
import time

import numpy as np

import src.rc18_common as RC
import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc21_attr as RA

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc21"
B19 = RC.ROOT / "outputs" / "research_campaign_20261018" / "opus_rc19b" / "b-final-label" / "units"
C20 = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc20" / "c-replay" / "units"
ARMS19B = ("E1S", "ATSCF_MARGIN", "DEPTHCF_MARGIN", "G3_MARGIN", "ATSAPPROX_MARGIN")
REC = tuple(range(8, 61, 4))
REPLAY_WHICH = ("SHQ_ATS_H", "PHR", "PHR_NR", "PHR_FX", "PHR_FXMAP")


def replay_unit(task, unit, cache20, M):
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in unit["paid_ids"]]
    ref = {e["budget"]: e["p"]["SHQ_ATS_H"] for e in cache20["evals"]}; evals = []; t0 = time.time()
    for b in REC:
        rev = K._rev_with(task, M, paid[:b]); t1 = time.process_time(); out, info = RA.state(task, rev, Z, task["test"], which=REPLAY_WHICH)
        chk = float(np.nanmax(np.abs(out["SHQ_ATS_H"] - np.asarray([np.nan if v is None else v for v in ref[b]], float)))) if b in ref else None
        evals.append({"budget": b, "p": {k: LN._f32(v) for k, v in out.items()}, "info": info, "check_SHQ_ATS_H_vs_rc20": chk, "cpu_s": time.process_time() - t1})
    return {"repeat": task["repeat"], "fold": task["fold"], "path_of": unit["arm"], "paid_ids": unit["paid_ids"][:max(REC)], "test_ids": unit["test_ids"],
            "evals": evals, "seconds": time.time() - t0}


def units(job):
    if job == "d-replay":
        return [(f"r{r}_f{f}__{a}", ("replay", a, r, f)) for r in range(11, 19) for f in range(1, 6) for a in ARMS19B]
    import src.rc21_final as F
    return F.units(job)


def work(job):
    RC.limit_threads(1); U = units(job); M = P.manifest(); spec = dict(U); reps = sorted({s[2] for _, s in U}); T = {(t["repeat"], t["fold"]): t for t in P.tasks(reps)}
    if job == "d-final":
        import src.rc21_final as F
        F.check()                                                         # frozen hashes verified before any final unit

    def fn(name):
        kind, a, r, f = spec[name]; t = T[(r, f)]
        if kind == "replay":
            return replay_unit(t, RC.read_json_gz(B19 / f"r{r}_f{f}__{a}.json.gz"), RC.read_json_gz(C20 / f"r{r}_f{f}__{a}.json.gz"), M)
        import src.rc21_final as F
        return F.run_unit(a, t, M)
    d = OUT / job
    RC.run_units([n for n, _ in U], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("d-replay",)})
