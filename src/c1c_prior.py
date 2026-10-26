"""C1C prior-width controls (PROTOCOL_C1C.md section 5): a CONTROL, never candidate selection.

  C1_S05  C1 with every prior SD multiplied by 0.5     C1_S2  C1 with every prior SD multiplied by 2
Prior centres (PRIOR_M), the two optimiser starts, the trend, the honest K = 10 cross-fit, the classifier, the threshold and the one-class rule
are those of C1 (src.ea_cand SYSTEMS["C1"]); the frozen C1 code path is run unchanged with src.ea_cand.PRIOR_S scaled inside a context
(restored afterwards). Scale 1 must reproduce the recorded C1 bit-exactly (job c1c-prior-repro, OLD units only).
Paths: the recorded HA_LEAN DEV paths of STD repeats 123-162 (src.ea_cand.dev_path_unit, the paths of the EA candidate DEV), every budget
8..60 (pre-set). These paths were reviewed in EA: this is NOT new independent validation.
    python -m src.c1c_prior work c1c-prior | c1c-prior-repro ; python -m src.c1c_prior repro-check
"""
from __future__ import annotations

import contextlib
import json
import sys
import time

import numpy as np

import src.ea_cand as CA
import src.el_cross as X
import src.rc18_common as RC
import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc22_common as C22

OUT = RC.ROOT / "outputs" / "research_campaign_20261026" / "opus_c1_confirmation"
SCALES = {"C1_S05": 0.5, "C1_S2": 2.0}
DEV_REPS = tuple(range(123, 163))


@contextlib.contextmanager
def prior_scale(s):
    old = CA.PRIOR_S; CA.PRIOR_S = old * float(s)
    try:
        yield
    finally:
        CA.PRIOR_S = old


def unit(task, u, M, budgets, systems):
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid_all = [pos[s] for s in u["paid_ids"]]; te = np.asarray(task["test"])
    if [task["ids"][i] for i in te] != list(u["test_ids"]):
        raise RuntimeError("recorded test set differs from the task")
    ev = []
    for b in budgets:
        rev = K._rev_with(task, M, paid_all[:b]); e = {"budget": b, "p": {}, "cpu_s": {}}
        for nm, s in systems.items():
            with prior_scale(s):
                t0 = time.process_time(); p, one = CA.predict(task, rev, Z, te, CA.SYSTEMS["C1"]); e["p"][nm] = LN._f32(p); e["cpu_s"][nm] = time.process_time() - t0
            e["one_class"] = one
        ev.append(e)
    if abs(float(CA.PRIOR_S[0]) - 1.5) > 0:
        raise RuntimeError("PRIOR_S not restored")
    return {"evals": ev}


def units(job):
    if job == "c1c-prior":
        return [(f"STD__r{r}_f{f}", ("STD", r, f)) for r in DEV_REPS for f in range(1, 6)]
    if job == "c1c-prior-repro":
        return [("STD__r123_f1", ("STD", 123, 1)), ("STD__r150_f3", ("STD", 150, 3))]
    raise ValueError(job)


def work(job):
    RC.limit_threads(1); U_ = units(job); M = P.manifest(); S = dict(U_); C22.set_manifest(M)
    if job != "c1c-prior-repro":
        import src.c1c_freeze as FR
        FR.check(job)
    T = X.tasks_for({n: (None, c, r, f) for n, (c, r, f) in S.items()}, M)

    def fn(name):
        c, r, f = S[name]; task = T[(c, r, f)]; u = CA.dev_path_unit(c, r, f)
        if job == "c1c-prior-repro":
            res = unit(task, u, M, (8, 12, 13, 24, 40), {"C1_S1": 1.0, **SCALES})
        else:
            res = unit(task, u, M, tuple(range(8, 61)), SCALES)
        return {"condition": c, "repeat": r, "fold": f, "paid_ids": u["paid_ids"][:60], "test_ids": u["test_ids"], **res}
    d = OUT / job
    RC.run_units([n for n, _ in U_], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


def repro_check():
    """Scale 1 = the recorded C1 of ea-cand-dev bit-exactly; scales 0.5 and 2 must differ from it (the control is active)."""
    out = {}
    for nm, (c, r, f) in units("c1c-prior-repro"):
        new = RC.read_json_gz(OUT / "c1c-prior-repro" / "units" / f"{nm}.json.gz"); old = RC.read_json_gz(CA.OUT / "ea-cand-dev" / "units" / f"{nm}.json.gz")
        rec = {e["budget"]: e["p"]["C1"] for e in old["evals"]}; row = {}
        for e in new["evals"]:
            b = e["budget"]; row[str(b)] = {k: float(np.max(np.abs(np.asarray(e["p"][k], float) - np.asarray(rec[b], float)))) for k in ("C1_S1", "C1_S05", "C1_S2")}
        ok1 = all(v["C1_S1"] == 0.0 for v in row.values()); act = all(v["C1_S05"] > 0 or v["C1_S2"] > 0 for k, v in row.items() if int(k) >= 12)
        out[nm] = {"maxabs_vs_recorded_C1": row, "scale1_bit_exact": ok1, "controls_differ": act, "PASS": bool(ok1 and act)}
    out["ALL_PASS"] = all(v["PASS"] for v in out.values() if isinstance(v, dict))
    (OUT / "repro").mkdir(parents=True, exist_ok=True); (OUT / "repro" / "REPRO_PRIOR_SCALE1.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("c1c-prior", "c1c-prior-repro")})
    elif sys.argv[1] == "repro-check":
        print(json.dumps(repro_check(), indent=1))
