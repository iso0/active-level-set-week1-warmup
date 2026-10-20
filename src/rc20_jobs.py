"""RC20 unit lists for the persistent queue (src/rc20_runner.ps1; plan opus_rc20/runner/PLAN.json).
Matched-path replays recompute constructions on the SAME paid prefixes of the RC19B final trajectories (repeats 11-18, every
arm's own path), at the budgets where RC19B recorded every system control (8, 12, ..., 60), so the controls E1RAW, E1CAL,
ATSCF, DEPTHCF, ATSAPPROX and G3 are read from the cache (and SHQ_ATS / M0Q_A are checked against ATSCF / DEPTHCF).
Outputs: outputs/research_campaign_20261020/opus_rc20/<job>/units/<unit>.json.gz (unit protocol of src/rc18_common.run_units).
    python -m src.rc20_jobs work <job> [--threads 1]        (set RC18_DEADLINE_UTC to the RC20 deadline when run by hand)
"""
from __future__ import annotations

import sys
import time

import numpy as np

import src.rc18_common as RC
import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc20_attr as A

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc20"
B19 = RC.ROOT / "outputs" / "research_campaign_20261018" / "opus_rc19b" / "b-final-label" / "units"
ARMS19B = ("E1S", "ATSCF_MARGIN", "DEPTHCF_MARGIN", "G3_MARGIN", "ATSAPPROX_MARGIN")
REC = tuple(range(8, 61, 4))
PILOT_BUDGETS = (8, 12, 16, 20, 24, 40, 60)
CHECK = (("SHQ_ATS", "ATSCF"), ("M0Q_A", "DEPTHCF"))


def replay_unit(task, unit, M, budgets, which, remedy, diag):
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in unit["paid_ids"]]
    cache = {e["budget"]: e["p_all"] for e in unit["evals"] if "p_all" in e}; evals = []; t0 = time.time()
    for b in budgets:
        rev = K._rev_with(task, M, paid[:b]); t1 = time.time()
        out, info = A.constructions(task, rev, Z, which, remedy=remedy, diag=diag); chk = {}
        for mine, theirs in CHECK:
            if mine in out and b in cache and theirs in cache[b]:
                ref = np.asarray([np.nan if v is None else v for v in cache[b][theirs]], float); chk[mine] = float(np.nanmax(np.abs(out[mine] - ref)))
        evals.append({"budget": b, "p": {k: LN._f32(v) for k, v in out.items()}, "info": info, "check_vs_cache": chk, "seconds": time.time() - t1})
    return {"repeat": task["repeat"], "fold": task["fold"], "path_of": unit["arm"], "paid_ids": unit["paid_ids"][:max(budgets)],
            "test_ids": unit["test_ids"], "evals": evals, "seconds": time.time() - t0, "remedy": list(remedy)}


def units(job):
    if job == "c-pilot":
        return [(f"r{r}_f{f}__{a}", ("replay", a, r, f)) for r in (11, 12) for f in range(1, 6) for a in ("E1S", "ATSCF_MARGIN")]
    if job in ("c-replay", "c-replay-x"):
        return [(f"r{r}_f{f}__{a}", ("replay", a, r, f)) for r in range(11, 19) for f in range(1, 6) for a in ARMS19B]
    import src.rc20_final as F
    return F.units(job)


def work(job):
    RC.limit_threads(1); U = units(job); M = P.manifest(); spec = dict(U); reps = sorted({s[2] for _, s in U}); T = {(t["repeat"], t["fold"]): t for t in P.tasks(reps)}
    if job == "c-replay":
        import src.rc20_decisions as DEC
        remedy, which = DEC.REMEDY, A.ATTR
    elif job == "c-pilot":
        remedy, which = ("FD", "MAP"), A.ATTR
    elif job == "c-replay-x":                                            # exploratory h-specificity control (registered after Stage 1)
        remedy, which = (), ("SHQ_A", "SHQ_ATS", "SHQ_A_H", "SHQ_ATS_H", "SHQ_A_X", "SHQ_ATS_X")
    else:
        import src.rc20_final as F
        if job == "c-final":
            F.check()                                                     # frozen hashes verified before any final unit
        remedy, which = (), ()

    def fn(name):
        kind, a, r, f = spec[name]; t = T[(r, f)]
        if kind == "replay":
            u = RC.read_json_gz(B19 / f"r{r}_f{f}__{a}.json.gz")
            return replay_unit(t, u, M, PILOT_BUDGETS if job == "c-pilot" else REC, which, remedy, diag=True)
        import src.rc20_final as F
        return F.run_unit(kind, a, t, M)
    d = OUT / job
    RC.run_units([n for n, _ in U], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("c-pilot", "c-replay")})
