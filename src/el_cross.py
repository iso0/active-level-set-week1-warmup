"""EL study, DEV stage (PROTOCOL_EL_OBJECTIVES.md section 7): cross predictions on the EXISTING recorded query paths.

Systems (selects -> predicts): A HA_LEAN -> HA_LEAN, B HA_TREND -> HA_TREND, C HA_TREND -> HA_LEAN, D HA_LEAN -> HA_TREND.
A and B are the recorded own paths (never refitted). This module computes only what is missing:
  C  HA_LEAN predictions on every recorded HA_TREND path, every budget 8..60 (never computed before);
  D  HA_TREND predictions on the recorded HA_LEAN paths whose existing matched record has only budgets 8, 12, ..., 60:
     the 39 missing budgets plus ONE check budget (b = 12) compared with the existing value.
Each prediction at budget b uses ONLY the first b paid runs of its path (labels, log depths, record-quality flags of those runs)
and the public inputs; test outcomes are never read here. Code checks: at b = 8 the paid set is the common startup on both
paths, so C(8) must equal A(8) (recorded) and D(8) must equal B(8) (recorded).

Existing records used (read only):
  STD  r51-58: A opus_rc23/h-std HA_LEAN, B opus_rc24/b-pilot3 HA_TREND_MARGIN, D(step 4) opus_rc24/b-pilot MATCH_STD (HA_TREND)
       r67-74: A/B opus_rc24/c-own, D(every budget) opus_rc24/c-match MATCH_STD__..__HA_LEAN_MARGIN (HA_TREND) - nothing to compute for D
       r75-82: A/B opus_rc24/f-own F_HA_LEAN / F_HA_TREND, D(step 4) opus_rc24/f-match MATCH_STD (TR_PHYS = HA_TREND bit-exact)
  K5   (k-means k = 5, the same five regions) startups 1-8 (rc23 h-block / b-pilot3 / b-pilot MATCH_BLOCK), 9-16 (c-own / c-match),
       17-24 (f-own BLOCK_A / f-match MATCH_BLOCK_A)
  K4   (k-means k = 4) startups 1-8 (f-own BLOCK_B / f-match MATCH_BLOCK_B)
    python -m src.el_cross work el-cross | list
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
import src.rc23_common as C23
import src.rc24_pac as PC

R21 = RC.ROOT / "outputs" / "research_campaign_20261021"
R23, R24 = R21 / "opus_rc23", R21 / "opus_rc24"
OUT = RC.ROOT / "outputs" / "research_campaign_20261024" / "opus_early_learning"
BUD = tuple(range(8, 61)); MB4 = tuple(range(8, 61, 4)); CHECK_B = 12

# (condition, source) -> repeats/startups and the folds/blocks per learner
SOURCES = {("STD", "r51"): (tuple(range(51, 59)), 5), ("STD", "r67"): (tuple(range(67, 75)), 5), ("STD", "r75"): (tuple(range(75, 83)), 5),
           ("K5", "s1"): (tuple(range(1, 9)), 5), ("K5", "s9"): (tuple(range(9, 17)), 5), ("K5", "s17"): (tuple(range(17, 25)), 5),
           ("K4", "s1"): (tuple(range(1, 9)), 4)}


def src_of(cond, r):
    for (c, s), (reps, _) in SOURCES.items():
        if c == cond and r in reps:
            return s
    raise KeyError((cond, r))


def own_path(cond, r, f, which):
    """Recorded own-path unit file of A (which = 'L') or B (which = 'T') and the probability key inside it."""
    s = src_of(cond, r)
    if cond == "STD":
        if s == "r51":
            return (R23 / "h-std" / "units" / f"STD__r{r}_f{f}__HA_LEAN.json.gz", "HA_LEAN") if which == "L" else \
                   (R24 / "b-pilot3" / "units" / f"STD__r{r}_f{f}__HA_TREND_MARGIN.json.gz", "HA_TREND")
        if s == "r67":
            return (R24 / "c-own" / "units" / f"STD__r{r}_f{f}__{'HA_LEAN' if which == 'L' else 'HA_TREND'}_MARGIN.json.gz", "HA_LEAN" if which == "L" else "HA_TREND")
        return (R24 / "f-own" / "units" / f"STD__r{r}_f{f}__F_{'HA_LEAN' if which == 'L' else 'HA_TREND'}.json.gz", "HA_LEAN" if which == "L" else "HA_TREND")
    if cond == "K5":
        if s == "s1":
            return (R23 / "h-block" / "units" / f"s{r}_b{f}__HA_LEAN.json.gz", "HA_LEAN") if which == "L" else \
                   (R24 / "b-pilot3" / "units" / f"s{r}_b{f}__HA_TREND_MARGIN.json.gz", "HA_TREND")
        if s == "s9":
            return (R24 / "c-own" / "units" / f"BLOCK__s{r}_b{f}__{'HA_LEAN' if which == 'L' else 'HA_TREND'}_MARGIN.json.gz", "HA_LEAN" if which == "L" else "HA_TREND")
        return (R24 / "f-own" / "units" / f"BLOCK_A__s{r}_b{f}__F_{'HA_LEAN' if which == 'L' else 'HA_TREND'}.json.gz", "HA_LEAN" if which == "L" else "HA_TREND")
    return (R24 / "f-own" / "units" / f"BLOCK_B__s{r}_b{f}__F_{'HA_LEAN' if which == 'L' else 'HA_TREND'}.json.gz", "HA_LEAN" if which == "L" else "HA_TREND")


def existing_D(cond, r, f):
    """Existing HA_TREND predictions on the recorded HA_LEAN path: (unit file, key, every_budget?)."""
    s = src_of(cond, r)
    if cond == "STD":
        if s == "r51":
            return R24 / "b-pilot" / "units" / f"MATCH_STD__r{r}_f{f}.json.gz", "HA_TREND", False
        if s == "r67":
            return R24 / "c-match" / "units" / f"MATCH_STD__r{r}_f{f}__HA_LEAN_MARGIN.json.gz", "HA_TREND", True
        return R24 / "f-match" / "units" / f"MATCH_STD__r{r}_f{f}.json.gz", "TR_PHYS", False
    if cond == "K5":
        if s == "s1":
            return R24 / "b-pilot" / "units" / f"MATCH_BLOCK__s{r}_b{f}.json.gz", "HA_TREND", False
        if s == "s9":
            return R24 / "c-match" / "units" / f"MATCH_BLOCK__s{r}_b{f}__HA_LEAN_MARGIN.json.gz", "HA_TREND", True
        return R24 / "f-match" / "units" / f"MATCH_BLOCK_A__s{r}_b{f}.json.gz", "TR_PHYS", False
    return R24 / "f-match" / "units" / f"MATCH_BLOCK_B__s{r}_b{f}.json.gz", "TR_PHYS", False


def predict(model, task, rev, Z, rows):
    if model == "HA_LEAN":
        o, info = C23.state(task, rev, Z, rows, which=("HA_LEAN",)); return o["HA_LEAN"], bool(info.get("one_class"))
    o, info = PC.state(task, rev, Z, rows, ("HA_TREND",)); return o["HA_TREND"], bool(info.get("one_class"))


def cross_unit(task, path_unit, model, budgets, M):
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in path_unit["paid_ids"]]; rows = np.asarray(task["test"])
    if [task["ids"][i] for i in task["test"]] != list(path_unit["test_ids"]):
        raise RuntimeError("test set of the recorded path differs from the task")
    evals = []; t0 = time.time()
    for b in budgets:
        rev = K._rev_with(task, M, paid[:b]); t1 = time.process_time(); p, one = predict(model, task, rev, Z, rows)
        evals.append({"budget": b, "p": {model: LN._f32(p)}, "cpu_s": time.process_time() - t1, "one_class": one})
    return evals, time.time() - t0


def units():
    U = []
    for (cond, s), (reps, nf) in SOURCES.items():
        for r in reps:
            for f in range(1, nf + 1):
                U.append((f"C__{cond}__r{r}_f{f}", ("C", cond, r, f)))
                if not existing_D(cond, r, f)[2]:
                    U.append((f"D__{cond}__r{r}_f{f}", ("D", cond, r, f)))
    return U


def tasks_for(S, M):
    import src.rc24p_final as F
    T = {}
    reps = sorted({v[2] for v in S.values() if v[1] == "STD"}); k5 = sorted({v[2] for v in S.values() if v[1] == "K5"}); k4 = sorted({v[2] for v in S.values() if v[1] == "K4"})
    if reps:
        T.update({("STD", t["repeat"], t["fold"]): t for t in P.tasks(reps)})
    if k5:
        T.update({("K5", t["repeat"], t["fold"]): t for t in C22.block_tasks(k5, M)})
    if k4:
        T.update({("K4", t["repeat"], t["fold"]): t for t in F.block_tasks_b(k4, M)})
    return T


def work(job):
    RC.limit_threads(1); U = units(); M = P.manifest(); S = dict(U); C22.set_manifest(M); T = tasks_for(S, M)

    def fn(name):
        sysname, cond, r, f = S[name]; task = T[(cond, r, f)]
        fa, ka = own_path(cond, r, f, "L"); fb, kb = own_path(cond, r, f, "T"); A = RC.read_json_gz(fa); B = RC.read_json_gz(fb)
        if A["paid_ids"][:8] != B["paid_ids"][:8]:
            raise RuntimeError("A and B startups differ")
        if sysname == "C":
            ev, sec = cross_unit(task, B, "HA_LEAN", BUD, M)
            chk = float(np.max(np.abs(np.asarray(ev[0]["p"]["HA_LEAN"], float) - np.asarray(A["evals"][0]["p"][ka], float))))
            return {"system": "C", "selects": "HA_TREND", "predicts": "HA_LEAN", "condition": cond, "source": src_of(cond, r), "repeat": r, "fold": f,
                    "path_file": str(fb.relative_to(RC.ROOT)), "paid_ids": B["paid_ids"][:60], "test_ids": B["test_ids"], "evals": ev, "seconds_wall": sec,
                    "check_C8_equals_A8_maxabs": chk}
        fd, kd, _ = existing_D(cond, r, f); Dx = RC.read_json_gz(fd)
        if Dx["paid_ids"][:60] != A["paid_ids"][:len(Dx["paid_ids"][:60])]:
            raise RuntimeError("existing matched record is not on the recorded HA_LEAN path")
        have = {e["budget"] for e in Dx["evals"]}; need = [b for b in BUD if b not in have]
        ev, sec = cross_unit(task, A, "HA_TREND", sorted(need + [CHECK_B]), M)
        old = {e["budget"]: e["p"][kd] for e in Dx["evals"]}
        chk = float(np.max(np.abs(np.asarray([e for e in ev if e["budget"] == CHECK_B][0]["p"]["HA_TREND"], float) - np.asarray(old[CHECK_B], float))))
        chk8 = float(np.max(np.abs(np.asarray(old[8], float) - np.asarray(B["evals"][0]["p"][kb], float))))
        return {"system": "D", "selects": "HA_LEAN", "predicts": "HA_TREND", "condition": cond, "source": src_of(cond, r), "repeat": r, "fold": f,
                "path_file": str(fa.relative_to(RC.ROOT)), "existing_file": str(fd.relative_to(RC.ROOT)), "existing_key": kd, "paid_ids": A["paid_ids"][:60],
                "test_ids": A["test_ids"], "evals": ev, "seconds_wall": sec, "check_b12_vs_existing_maxabs": chk, "check_D8_equals_B8_maxabs": chk8,
                "computed_budgets": sorted(need), "check_budget": CHECK_B}
    d = OUT / job
    RC.run_units([n for n, _ in U], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        U = units(); print(len(U), {k: sum(1 for n, v in U if v[0] == k) for k in "CD"})
