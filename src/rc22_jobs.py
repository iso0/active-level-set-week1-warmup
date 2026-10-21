"""RC22 unit lists for the persistent queue (src/rc22_runner.ps1; plan opus_rc22/runner/PLAN.json).
  g-ingr   matched states: the RC21B NEW_MARGIN and H_MARGIN paid prefixes (repeats 35-42), budgets IB; every ingredient
           construction + selector scores on the candidates (part 2 and the acquisition audit of part 3)
  g-miss   matched states: RC21B NEW_MARGIN prefixes, budgets MB, missing-channel / record-quality conditions (part 1c)
  g-start  sequential: startups RAND8 / LOCAL8 on the RC21B splits (repeats 35-42), arms REF, H, E1S (part 1a)
  g-block  sequential: geometry blocks (k-means k = 5) x seeds 1-8, arms REF, H, E1S (part 1b)
  g-acq    sequential: fresh repeats 43-50, acquisition arms (part 3; frozen separately)
  g-smoke  a few sequential units of every type on DEV repeat 1 / seed 1 (numerical acceptance)
Outputs: outputs/research_campaign_20261021/opus_rc22/<job>/units/<unit>.json.gz (unit protocol of src/rc18_common.run_units).
    python -m src.rc22_jobs work <job> [--threads 1]        (set RC18_DEADLINE_UTC to the RC22 deadline when run by hand)
"""
from __future__ import annotations

import hashlib
import sys
import time

import numpy as np

import src.rc18_common as RC
import src.rc19_learn as LN
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc22_common as C

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc22"
EB = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc21" / "e-final" / "units"
IB = (8, 12, 16, 20, 24, 32, 40, 60)
MB = (8, 12, 16, 20, 24, 40, 60)
MISS = ("REAL", "MCAR25", "MCAR50", "QOFF", "SHORTDROP")
INGR = ("SHQ_ATS_H", "PHR_NRMAP", "HA_LR", "HONLY_LR", "SHQ_ATS_H_RECAL")
REPEATS_B = tuple(range(35, 43)); REPEATS_ACQ = tuple(range(43, 51)); SEEDS_BLOCK = tuple(range(1, 9))
ROBUST_ARMS = ("REF", "H", "E1S")
ARM_SPEC = {"REF": ("PHR_NRMAP", "margin", None), "H": ("SHQ_ATS_H", "margin", None),
            "A1_MARGIN": ("PHR_NRMAP", "margin", None), "A2_MARGIN_COV": ("PHR_NRMAP", "margin", C.COVERAGE_EVERY), "A4_MAXIMIN": ("PHR_NRMAP", "MAXIMIN", None)}


def acq_arms():
    import src.rc22_decisions as DEC
    arms = ["A1_MARGIN", "A2_MARGIN_COV"] + (["A3_SEL_COV"] if DEC.SELECTOR else []) + ["A4_MAXIMIN"] + (["A5_SIMPLE"] if DEC.SIMPLE else [])
    return arms


def spec(arm):
    import src.rc22_decisions as DEC
    if arm == "A3_SEL_COV":
        return ("PHR_NRMAP", DEC.SELECTOR, C.COVERAGE_EVERY)
    if arm == "A5_SIMPLE":
        return (DEC.SIMPLE, "margin", None)
    return ARM_SPEC[arm]


# ======================================================================================== matched states
def _cand_pack(out, info, nt, cands):
    pk = {"cand_rows": [int(i) for i in cands]}
    for k, v in out.items():
        pk[f"p:{k}"] = LN._f32(v[nt:])
    for k in ("bald_grid", "bald_lap", "p_integrated", "eta_straddle_H"):
        if k in info:
            pk[k] = LN._f32(np.asarray(info[k])[nt:])
    return pk


def ingr_unit(task, unit, M):
    C.set_manifest(M); Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in unit["paid_ids"]]
    rec = {e["budget"]: e["p_all"] for e in unit["evals"]}; nt = len(task["test"]); evals = []; t0 = time.time()
    for b in IB:
        rev = K._rev_with(task, M, paid[:b]); cands = np.setdiff1d(task["pool"], rev.paid); t1 = time.process_time()
        out, info = C.state(task, rev, Z, np.r_[task["test"], cands], which=INGR, want_bald=True, want_eta=True)
        chk = {k: float(np.nanmax(np.abs(out[k][:nt] - np.asarray(rec[b][k], float)))) for k in ("SHQ_ATS_H", "PHR_NRMAP") if not info["one_class"]}
        e = {"budget": b, "p": {k: LN._f32(v[:nt]) for k, v in out.items()}, "one_class": info["one_class"], "check_vs_rc21b": chk,
             "recal": info.get("recal"), "phr_w": info.get("phr_w"), "cpu_s": time.process_time() - t1}
        if not info["one_class"]:
            e["cand"] = _cand_pack(out, info, nt, cands)
        evals.append(e)
    return {"repeat": task["repeat"], "fold": task["fold"], "path_of": unit["arm"], "paid_ids": unit["paid_ids"][:max(IB)], "test_ids": unit["test_ids"], "evals": evals,
            "seconds": time.time() - t0}


def _u(sim_id, ch):
    return np.random.default_rng([C.SEED, int(hashlib.sha256(sim_id.encode()).hexdigest()[:8], 16), ch]).random()


def masked_rev(task, M, paid_rows, cond):
    """Paid-only stress: missing T / S monitor channels (never labels, never depth, never unpaid runs) or the quality treatment."""
    rev = K._rev_with(task, M, paid_rows); n_masked = 0
    for i in rev.paid:
        for ch in (C.ATS_T, C.ATS_S):
            hit = (cond == "MCAR25" and _u(task["ids"][i], ch) < 0.25) or (cond == "MCAR50" and _u(task["ids"][i], ch) < 0.50) or (cond == "SHORTDROP" and rev._short[i])
            if hit and np.isfinite(rev._Y[i, ch]):
                rev._Y[i, ch] = np.nan; n_masked += 1
    if cond == "QOFF":
        rev._short[:] = False
    return rev, n_masked


def miss_unit(task, unit, M):
    Z = P.zstd(task); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in unit["paid_ids"]]; nt = len(task["test"]); evals = []; t0 = time.time()
    rec = {e["budget"]: e["p_all"] for e in unit["evals"]}
    for b in MB:
        for cond in MISS:
            rev, nm = masked_rev(task, M, paid[:b], cond); t1 = time.process_time()
            out, info = C.state(task, rev, Z, task["test"], which=("SHQ_ATS_H", "PHR_NRMAP"))
            e = {"budget": b, "cond": cond, "n_masked": nm, "n_short_paid": int(rev.paid_short()[rev.paid].sum()), "p": {k: LN._f32(v) for k, v in out.items()},
                 "cpu_s": time.process_time() - t1}
            if cond == "REAL" and not info["one_class"]:
                e["check_vs_rc21b"] = {k: float(np.nanmax(np.abs(out[k] - np.asarray(rec[b][k], float)))) for k in out}
            evals.append(e)
    return {"repeat": task["repeat"], "fold": task["fold"], "path_of": unit["arm"], "paid_ids": unit["paid_ids"][:max(MB)], "test_ids": unit["test_ids"], "evals": evals,
            "seconds": time.time() - t0}


# ======================================================================================== unit lists
def units(job):
    if job == "g-ingr":
        return [(f"r{r}_f{f}__{a}", ("ingr", a, r, f, None)) for r in REPEATS_B for f in range(1, 6) for a in ("NEW_MARGIN", "H_MARGIN")]
    if job == "g-miss":
        return [(f"r{r}_f{f}__NEW_MARGIN", ("miss", "NEW_MARGIN", r, f, None)) for r in REPEATS_B for f in range(1, 6)]
    if job == "g-start":
        return [(f"{st}__r{r}_f{f}__{a}", ("seq", a, r, f, st)) for st in ("RAND8", "LOCAL8") for r in REPEATS_B for f in range(1, 6) for a in ROBUST_ARMS]
    if job == "g-block":
        return [(f"s{s}_b{b}__{a}", ("block", a, s, b, None)) for s in SEEDS_BLOCK for b in range(1, 6) for a in ROBUST_ARMS]
    if job == "g-acq":
        return [(f"r{r}_f{f}__{a}", ("seq", a, r, f, "STD")) for r in REPEATS_ACQ for f in range(1, 6) for a in acq_arms()]
    if job == "g-smoke":
        return ([(f"{st}__r1_f1__{a}", ("seq", a, 1, 1, st)) for st in ("RAND8", "LOCAL8") for a in ROBUST_ARMS] + [(f"s1_b1__{a}", ("block", a, 1, 1, None)) for a in ROBUST_ARMS]
                + [(f"STD__r1_f2__{a}", ("seq", a, 1, 2, "STD")) for a in ("A2_MARGIN_COV", "A4_MAXIMIN")])
    raise ValueError(job)


def run_arm(task, arm, M):
    if arm == "E1S":
        return C.run_e1s(task, M)
    own, sel, cov = spec(arm); u = C.run_phys(task, own, sel, cov, M); u["arm"] = arm; return u


def work(job):
    RC.limit_threads(1); U = units(job); M = P.manifest(); S = dict(U); C.set_manifest(M)
    import src.rc22_freeze as FR
    FR.check(FR.stage_of(job))                                            # frozen hashes verified before any unit of this job
    kinds = {s[0] for s in S.values()}; T = {}
    if kinds & {"ingr", "miss", "seq"}:
        reps = sorted({s[2] for s in S.values() if s[0] != "block"}); T.update({(t["repeat"], t["fold"]): t for t in P.tasks(reps)})
    if "block" in kinds:
        TB = {(t["repeat"], t["fold"]): t for t in C.block_tasks(sorted({s[2] for s in S.values() if s[0] == "block"}), M)}

    def fn(name):
        kind, a, r, f, st = S[name]
        if kind == "ingr":
            return ingr_unit(T[(r, f)], RC.read_json_gz(EB / f"r{r}_f{f}__{a}.json.gz"), M)
        if kind == "miss":
            return miss_unit(T[(r, f)], RC.read_json_gz(EB / f"r{r}_f{f}__{a}.json.gz"), M)
        task = TB[(r, f)] if kind == "block" else C.startup_task(T[(r, f)], st)
        return run_arm(task, a, M)
    d = OUT / job
    RC.run_units([n for n, _ in U], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("g-ingr", "g-miss", "g-start", "g-block", "g-smoke")})
