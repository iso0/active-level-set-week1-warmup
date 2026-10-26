"""C1 confirmation (C1C) forward runs (outputs/research_campaign_20261026/opus_c1_confirmation/PROTOCOL_C1C.md; frozen before any new result).

The unit code is src.ea_fwd.unit_L / unit_X, UNCHANGED (the EA validation code); this module only fixes the new IDs and startups:
  L  A = HA_LEAN + margin own path; on it at every budget 8..60: C1 (src.ea_cand SYSTEMS["C1"]), D (HA_LEAN selects / HA_TREND predicts),
     E (evidence mixture) via src.el_mix.mix_state (p_L checked equal to A's own predictions)
  X  C1 + margin own path (one-class rule = next on the label-free path); on it at every budget: A
Conditions (new IDs; none was used before, see the protocol's inventory):
  STD     repeats 203-282 x 5 folds (main validation; pre-defined subgroups S1 = 203-242, S2 = 243-282); standard 8-point label-free
          maximin startup of src.rc19_pool.tasks
  RAND8   repeats 283-302 x 5 folds; 8 pool points drawn at random (src.rc22_common.startup_task, rng [2222, repeat, fold, 1])
  LOCAL8  repeats 303-322 x 5 folds; the 8 pool points nearest to one random pool point (rng [2222, repeat, fold, 2])
  (RAND8 / LOCAL8 = the audited RC22 startup rules; labels are never read; continuation = greedy farthest point from the paid set)
Jobs
  c1c-main   800 units (STD)            c1c-start  400 units (RAND8, LOCAL8)
  c1c-repro  recomputes recorded EA units on OLD IDs (STD r163 f1, r197 f5; L and X) - reproduction check, no new ID
    python -m src.c1c_fwd work <job> | list | repro-check | startup-check
"""
from __future__ import annotations

import json
import sys

import numpy as np

import src.ea_fwd as F
import src.el_cross as X
import src.rc18_common as RC
import src.rc19_pool as P
import src.rc22_common as C22

OUT = RC.ROOT / "outputs" / "research_campaign_20261026" / "opus_c1_confirmation"
EA = RC.ROOT / "outputs" / "research_campaign_20261026" / "opus_error_attribution"
RC22 = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc22"
MAIN = tuple(range(203, 283)); SUB = {"S1": tuple(range(203, 243)), "S2": tuple(range(243, 283))}
START = {"RAND8": tuple(range(283, 303)), "LOCAL8": tuple(range(303, 323))}
REPRO = (("STD", 163, 1), ("STD", 197, 5))


def units(job):
    if job == "c1c-main":
        return [(f"STD__r{r}_f{f}__{p}", ("STD", r, f, p)) for r in MAIN for f in range(1, 6) for p in ("L", "X")]
    if job == "c1c-start":
        return [(f"{k}__r{r}_f{f}__{p}", (k, r, f, p)) for k, reps in START.items() for r in reps for f in range(1, 6) for p in ("L", "X")]
    if job == "c1c-repro":
        return [(f"{c}__r{r}_f{f}__{p}", (c, r, f, p)) for c, r, f in REPRO for p in ("L", "X")]
    raise ValueError(job)


def tasks(S, M):
    """STD tasks from src.rc19_pool.tasks; RAND8 / LOCAL8 = the same seeded split of that repeat with src.rc22_common.startup_task."""
    reps = sorted({r for c, r, f, p in S.values()}); base = {(t["repeat"], t["fold"]): t for t in P.tasks(reps)}; T = {}
    for c, r, f, p in S.values():
        T[(c, r, f)] = base[(r, f)] if c == "STD" else C22.startup_task(base[(r, f)], c)
    return T


def work(job):
    RC.limit_threads(1); U_ = units(job); M = P.manifest(); S = dict(U_); C22.set_manifest(M)
    if job != "c1c-repro":
        import src.c1c_freeze as FR
        FR.check(job)
    T = tasks(S, M)

    def fn(name):
        c, r, f, p = S[name]; task = T[(c, r, f)]
        return {**(F.unit_L(task, M, 60) if p == "L" else F.unit_X(task, M, 60)), "condition": c, "startup": task.get("startup", "STD")}
    d = OUT / job
    RC.run_units([n for n, _ in U_], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


# ======================================================================================== checks on OLD IDs only
def _maxdiff(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    if a.shape != b.shape:
        return float("inf")
    return float(np.nanmax(np.abs(a - b))) if a.size else 0.0


def repro_check():
    """The recomputed c1c-repro units must equal the recorded EA ea-fwd units: every prediction (float32) and every paid id."""
    out = {}
    for c, r, f in REPRO:
        for p in ("L", "X"):
            nm = f"{c}__r{r}_f{f}__{p}"; new = RC.read_json_gz(OUT / "c1c-repro" / "units" / f"{nm}.json.gz"); old = RC.read_json_gz(EA / "ea-fwd" / "units" / f"{nm}.json.gz")
            row = {"paid_ids_equal": new["paid_ids"] == old["paid_ids"], "test_ids_equal": new["test_ids"] == old["test_ids"]}
            ks = ("HA_LEAN",) if p == "L" else ("C1",)
            row["own_pred_maxabs"] = max(_maxdiff(e1["p"][k], e0["p"][k]) for e1, e0 in zip(new["evals"], old["evals"]) for k in ks)
            ck = ("D", "E", "C1") if p == "L" else ("A",)
            row["cross_pred_maxabs"] = max(_maxdiff(e1["p"][k], e0["p"][k]) for e1, e0 in zip(new["cross"], old["cross"]) for k in ck)
            row["budgets_equal"] = [e["budget"] for e in new["evals"]] == [e["budget"] for e in old["evals"]] and [e["budget"] for e in new["cross"]] == [e["budget"] for e in old["cross"]]
            row["PASS"] = bool(row["paid_ids_equal"] and row["test_ids_equal"] and row["budgets_equal"] and row["own_pred_maxabs"] == 0.0 and row["cross_pred_maxabs"] == 0.0)
            out[nm] = row
    out["ALL_PASS"] = all(v["PASS"] for v in out.values() if isinstance(v, dict))
    (OUT / "repro").mkdir(parents=True, exist_ok=True); (OUT / "repro" / "REPRO_EA_UNITS.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def startup_check():
    """src.rc22_common.startup_task on OLD repeats 35-42 must reproduce the startups recorded by RC22 (job g-start, arm REF): the first 8 paid ids,
    and the label-free continuation used in one-class phases (every paid id chosen by the path rule)."""
    M = P.manifest(); C22.set_manifest(M); reps = tuple(range(35, 43)); base = {(t["repeat"], t["fold"]): t for t in P.tasks(reps)}; out = {}; ok = True
    for kind in ("RAND8", "LOCAL8"):
        n = 0; bad = []
        for r in reps:
            for f in range(1, 6):
                fp = RC22 / "g-start" / "units" / f"{kind}__r{r}_f{f}__REF.json.gz"
                if not fp.exists():
                    bad.append(f"missing {fp.name}"); continue
                u = RC.read_json_gz(fp); t = C22.startup_task(base[(r, f)], kind); ids = list(t["ids"])
                start = [ids[i] for i in t["path"][:P.B0]]
                if list(u["paid_ids"][:P.B0]) != start:
                    bad.append(f"{fp.name}: startup differs")
                # path-rule queries must be the next unpaid point of the new label-free order
                paid = []
                for q, (sid, e) in enumerate(zip(u["paid_ids"], [None] * P.B0 + list(u["evals"])), 1):
                    if q > P.B0 and e is not None and e.get("how") == "path":
                        s = set(paid); exp = next(ids[int(i)] for i in t["path"] if ids[int(i)] not in s)
                        if exp != sid:
                            bad.append(f"{fp.name}: path query {q} differs")
                    paid.append(sid)
                n += 1
        out[kind] = {"tasks_checked": n, "problems": bad[:20], "PASS": bool(n == 40 and not bad)}; ok &= out[kind]["PASS"]
    out["ALL_PASS"] = bool(ok); (OUT / "repro").mkdir(parents=True, exist_ok=True)
    (OUT / "repro" / "REPRO_STARTUPS_RC22.json").write_text(json.dumps(out, indent=1), encoding="utf-8"); return out


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("c1c-main", "c1c-start", "c1c-repro")})
    elif sys.argv[1] == "repro-check":
        print(json.dumps(repro_check(), indent=1))
    elif sys.argv[1] == "startup-check":
        print(json.dumps(startup_check(), indent=1))
