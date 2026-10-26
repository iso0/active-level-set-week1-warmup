"""EA forward validation runs (PROTOCOL_EA_VALIDATION.md, frozen before any run). Two units per fresh task:
  L  A = HA_LEAN + margin own path (src.rc23_common.run_arm, unchanged); on it at every budget 8..60: C1 (src.ea_cand SYSTEMS["C1"]),
     D (HA_TREND) and E (EL-2 evidence mixture) via src.el_mix.mix_state (whose p_L must equal A's own predictions)
  X  C1 + margin own path (margin -|p - 0.5| on C1's own probability, one-class rule = next on the label-free path); on it at every budget: A
Fresh IDs: STD repeats 163-202 x 5 folds; K5 startups 41-48 x 5; K4 startups 25-32 x 4.
    python -m src.ea_fwd work ea-fwd | ea-fwd-smoke
"""
from __future__ import annotations

import sys
import time

import numpy as np

import src.ea_cand as CA
import src.el_cross as X
import src.el_mix as MX
import src.rc18_common as RC
import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc22_common as C22
import src.rc23_common as C23

OUT = CA.OUT
REP = tuple(range(163, 203)); K5S = tuple(range(41, 49)); K4S = tuple(range(25, 33))


def unit_L(task, M, bmax=60):
    u = C23.run_arm(task, "HA_LEAN", M, bmax=bmax); Z = P.zstd(task); te = np.asarray(task["test"]); paid = list(u["paid"]); ev = []; chk = 0.0
    own = {e["budget"]: e["p"]["HA_LEAN"] for e in u["evals"]}
    for b in range(8, bmax + 1):
        rev = K._rev_with(task, M, paid[:b]); s = MX.mix_state(task, rev, Z, te)
        t0 = time.process_time(); pc, one = CA.predict(task, rev, Z, te, CA.SYSTEMS["C1"]); c1 = time.process_time() - t0
        chk = max(chk, float(np.max(np.abs(np.asarray(LN._f32(s["p_L"])) - np.asarray(own[b], float)))))
        ev.append({"budget": b, "p": {"D": LN._f32(s["p_T"]), "E": LN._f32(s["p_E"]), "C1": LN._f32(pc)}, "W_T": s["W_T"], "cpu_L": s["cpu_L"], "cpu_T": s["cpu_T"], "cpu_C1": c1, "one_class": bool(one)})
    u["cross"] = ev; u["check_pL_vs_own_A_maxabs"] = chk; u["path"] = "HA_LEAN"; return u


def unit_X(task, M, bmax=60):
    rev = K._rev_with(task, M, []); Z = P.zstd(task); C22.startup(task, rev); te = np.asarray(task["test"]); nt = len(te); evals = []; t0 = time.time(); c0 = time.process_time()
    while True:
        b = rev.queries; cands = np.setdiff1d(task["pool"], rev.paid); t1 = time.process_time()
        p, one = CA.predict(task, rev, Z, np.r_[te, cands], CA.SYSTEMS["C1"]); e = {"budget": b, "p": {"C1": LN._f32(p[:nt])}}
        if b >= bmax:
            e["cpu_s"] = time.process_time() - t1; evals.append(e); break
        if one:
            nxt = LN.next_on_path(task, rev); how = "path"
        else:
            nxt = int(cands[int(np.argmax(-np.abs(p[nt:] - 0.5)))]); how = "margin"
        e["cpu_s"] = time.process_time() - t1; e["how"] = how; evals.append(e); rev.reveal(nxt)
    paid = list(rev.order); cross = []
    for bb in range(8, bmax + 1):
        rv = K._rev_with(task, M, paid[:bb]); t2 = time.process_time(); o, info = C23.state(task, rv, Z, te, which=("HA_LEAN",))
        cross.append({"budget": bb, "p": {"A": LN._f32(o["HA_LEAN"])}, "cpu_s": time.process_time() - t2})
    return {"repeat": task["repeat"], "fold": task["fold"], "block": task.get("block"), "construction": "C1", "path": "C1", "paid": paid, "paid_ids": [task["ids"][i] for i in paid],
            "test_ids": [task["ids"][i] for i in te], "evals": evals, "cross": cross, "seconds": time.time() - t0, "cpu_s": time.process_time() - c0}


def units(job):
    if job == "ea-fwd":
        return ([(f"STD__r{r}_f{f}__{p}", ("STD", r, f, p)) for r in REP for f in range(1, 6) for p in ("L", "X")]
                + [(f"K5__s{s}_b{b}__{p}", ("K5", s, b, p)) for s in K5S for b in range(1, 6) for p in ("L", "X")]
                + [(f"K4__s{s}_b{b}__{p}", ("K4", s, b, p)) for s in K4S for b in range(1, 5) for p in ("L", "X")])
    if job == "ea-fwd-smoke":
        return [(f"STD__r1_f1__{p}", ("STD", 1, 1, p)) for p in ("L", "X")]
    raise ValueError(job)


def work(job):
    RC.limit_threads(1); U_ = units(job); M = P.manifest(); S = dict(U_); C22.set_manifest(M)
    import src.ea_freeze as FR
    FR.check(job)
    T = X.tasks_for({n: (None, c, r, f) for n, (c, r, f, p) in S.items()}, M)

    def fn(name):
        c, r, f, p = S[name]; task = T[(c, r, f)]
        return {**(unit_L(task, M, 60) if p == "L" else unit_X(task, M, 60)), "condition": c}
    d = OUT / job
    RC.run_units([n for n, _ in U_], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("ea-fwd", "ea-fwd-smoke")})
