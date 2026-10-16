"""PHYS_AUX_REP: limited validation of PHYS_AUX on DEV repeats 5-8 (owner request of 2026-10-16: "if there is a signal, move to a
limited validation with a pre-written continuation criterion").  The PHYS_AUX code (src/jdl_phys_aux.py) and the pilot A references
(src/jdl_surprise.py::run_real) are reused UNCHANGED; only the task set differs.

Tasks: NEW, DEV repeats 5-8, folds 1-5, the frozen feature-only maximin paths of EX1 (exploratory/EX1_ba_aligned_decision_rule/
paths.csv; sha256 per task checked against EX1_MANIFEST.json), start = first 16 path points, B16-B40, pilot A one-class rule.
Arms: PHYS_AUX, GPC_X (decisive control), G3_MARGIN, E1_STRADDLE.  These repeats were inspected before (EX1/EX2) but never
used by PHYS_AUX; a new split is not new data.
Pre-written continuation criterion (fixed before any unit):
  primary   AUX EFFECT REPRODUCED (DEV) iff PHYS_AUX - GPC_X BA-AULC: mean over repeats 5-8 >= +0.04, 95 % class-stratified
            cluster-bootstrap interval > 0, and positive in >= 3 of 4 repeats.  Otherwise NOT REPRODUCED.
  secondary PHYS_AUX - G3_MARGIN and PHYS_AUX - E1_STRADDLE: PRACTICALLY BETTER iff >= +0.04, interval > 0, all 4 repeats
            positive, short-K caught at B40 >= 7/10 in every repeat and at most 4 of 40 below the comparator; a gain failing only
            short-K = TRADE-OFF; else NO PRACTICAL DIFFERENCE.  Repeats 3-4 and 5-8 are reported separately, never pooled.
Steps: python -m src.jdl_phys_aux_rep validate | manifest | work [--arms A,B] | evaluate
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import datetime as dt
import gzip
import hashlib
import json
import sys
import time
import traceback

import numpy as np
import pandas as pd

import src.jdl_phys_aux as PA
import src.jdl_stage_m as SMM
import src.jdl_surprise as SD
import src.jdl_trained_al as TA

STUDY = "PHYS_AUX_REP"
OUT = SMM.OUT / "phys_aux_rep"
CACHE = SMM.OUT / "_cache" / "phys_aux_rep"
MANIFEST = OUT / "PHYS_AUX_REP_MANIFEST.json"
VALIDATION = OUT / "PHYS_AUX_REP_VALIDATION.json"
EX1 = SMM.OUT / "exploratory" / "EX1_ba_aligned_decision_rule"
REPEATS, FOLDS = (5, 6, 7, 8), (1, 2, 3, 4, 5)
ARMS = ("PHYS_AUX", "GPC_X", "G3_MARGIN", "E1_STRADDLE")
CODE = ("src/jdl_phys_aux_rep.py", "src/jdl_phys_aux.py", "src/jdl_surprise.py", "src/jdl_trained_al.py", "src/jdl_stage_m.py", "src/jdl_evaluate.py",
        "src/week18_engine.py", "src/jdl_physical_pilot.py")


def build_tasks():
    old = SMM.REPEATS; SMM.REPEATS = REPEATS
    try:
        tasks = [t for t in SMM.build_tasks() if t["population"] == "NEW"]
    finally:
        SMM.REPEATS = old
    paths = pd.read_csv(EX1 / "paths.csv"); sha = json.loads((EX1 / "EX1_MANIFEST.json").read_text(encoding="utf-8"))["paths_sha256"]
    for t in tasks:
        g = paths[(paths.population == "NEW") & (paths.repeat == t["repeat"]) & (paths.fold == t["fold"])].sort_values("query_index")
        if hashlib.sha256("\n".join(g.sim_id).encode()).hexdigest() != sha[f"NEW_r{t['repeat']}_f{t['fold']}"]:
            raise SystemExit(f"EX1 path NEW_r{t['repeat']}_f{t['fold']} differs from its manifest")
        pos = {s: i for i, s in enumerate(t["ids"])}; t["path"] = g.sim_id.map(pos).to_numpy(int)
    return tasks


def run(task, arm, auxT, deadline):
    if arm in ("PHYS_AUX", "GPC_X"):
        return PA.run_unit(task, arm, auxT, deadline=deadline)
    return SD.run_real(task, arm, deadline=deadline)


def work(argv=()):
    argv = list(argv); arms = tuple(argv[argv.index("--arms") + 1].split(",")) if "--arms" in argv else ARMS
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not SMM._git("log", "--format=%H", "--", str(MANIFEST.relative_to(SMM.ROOT)).replace("\\", "/")):
        raise SystemExit("commit the PHYS_AUX_REP manifest before any run")
    for c, h in man["code_sha256"].items():
        if SMM.sha256(SMM.ROOT / c) != h:
            raise SystemExit(f"{c} changed after the PHYS_AUX_REP freeze")
    tasks = {(t["repeat"], t["fold"]): t for t in build_tasks()}; auxT = PA.aux_table()
    CACHE.mkdir(parents=True, exist_ok=True); locks = CACHE / "locks"; locks.mkdir(exist_ok=True)
    for arm in arms:
        for r in REPEATS:
            for f in FOLDS:
                name = f"NEW__r{r}_f{f}__{arm}"; out = CACHE / f"{name}.json.gz"
                if out.exists():
                    continue
                lock = locks / f"{name}.lock"
                try:
                    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                except FileExistsError:
                    continue
                os.write(fd, str(os.getpid()).encode()); os.close(fd)
                try:
                    t0 = time.time(); res = run(tasks[(r, f)], arm, auxT, t0 + PA.UNIT_TIME_LIMIT_S)
                    res.update({"study": STUDY, "unit": name, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
                    TA._atomic_write(out, res); print(json.dumps({"unit": name, "status": res["status"], "s": round(res["seconds"], 1)}), flush=True)
                finally:
                    lock.unlink(missing_ok=True)


def frame():
    import src.jdl_evaluate as EV
    old_s, old_e = SMM.REPEATS, EV.REPEATS; SMM.REPEATS, EV.REPEATS = REPEATS, REPEATS
    try:
        tasks = [t for t in SMM.build_tasks() if t["population"] == "NEW"]; F = EV.population_frame("NEW", tasks)
    finally:
        SMM.REPEATS, EV.REPEATS = old_s, old_e
    return F


def evaluate():
    import src.jdl_evaluate as EV
    R = {}
    for p in sorted(CACHE.glob("NEW__*.json.gz")):
        r = json.loads(gzip.decompress(p.read_bytes())); R[(r["repeat"], r["fold"], r["arm"])] = r
    F = frame(); y, sk = F["y"], F["shortk"]; W = EV.boot_weights(y); corner = np.asarray(F["VX"], float) > SMM.FAST_VX
    pos = {s: i for i, s in enumerate(F["ids"])}; budgets = range(16, 41); M = {}
    for a in ARMS:
        for rep in REPEATS:
            for b in budgets:
                p = np.full(len(F["ids"]), np.nan); okf = 0
                for f in FOLDS:
                    r = R.get((rep, f, a)); e = None if r is None else {x["budget"]: x for x in r["evals"]}.get(b)
                    if e is not None:
                        p[[pos[s] for s in r["test_ids"]]] = e["p"]; okf += 1
                if okf == len(FOLDS) and np.isfinite(p).all():
                    m = EV.wmetrics(p, np.ones(len(p), bool), y, sk, F["q20"][rep], F["fold"][rep], W); c = EV.wmetrics(p, corner, y, sk, F["q20"][rep], F["fold"][rep], W)
                    M[(a, rep, b)] = {**{k: m[k] for k in ("BA", "sensitivity", "specificity", "q20", "AUC", "brier")}, "corner_AUC": c["AUC"], "shortK_caught": int(((p >= .5) & sk).sum())}
    def aulc(a, rep):
        if not all((a, rep, b) in M for b in budgets):
            return None
        v = np.vstack([M[(a, rep, b)]["BA"] for b in budgets]); return np.trapezoid(v, x=np.array(list(budgets), float), axis=0) / 24.0
    res = {"units_done": len(R), "units_expected": len(ARMS) * len(REPEATS) * len(FOLDS), "per_arm": {}, "contrasts": {}}
    for a in ARMS:
        res["per_arm"][a] = {"BA_AULC_per_repeat": [None if aulc(a, r) is None else round(float(aulc(a, r)[0]), 4) for r in REPEATS],
                             "B40_BA_per_repeat": [round(float(M[(a, r, 40)]["BA"][0]), 4) if (a, r, 40) in M else None for r in REPEATS],
                             "B40_shortK_caught_per_repeat": [M[(a, r, 40)]["shortK_caught"] if (a, r, 40) in M else None for r in REPEATS],
                             "B40_corner_AUC_per_repeat": [round(float(M[(a, r, 40)]["corner_AUC"][0]), 4) if (a, r, 40) in M else None for r in REPEATS],
                             "B40_brier_per_repeat": [round(float(M[(a, r, 40)]["brier"][0]), 4) if (a, r, 40) in M else None for r in REPEATS],
                             "seconds_total": float(sum(R[k]["seconds"] for k in R if k[2] == a))}
    for cand, ref in (("PHYS_AUX", "GPC_X"), ("PHYS_AUX", "G3_MARGIN"), ("PHYS_AUX", "E1_STRADDLE")):
        A = [aulc(cand, r) for r in REPEATS]; B = [aulc(ref, r) for r in REPEATS]
        if any(x is None for x in A + B):
            res["contrasts"][f"{cand}-{ref}"] = {"available": False}; continue
        d = np.mean([x - z for x, z in zip(A, B)], axis=0); lo, hi = np.nanpercentile(d[1:], [2.5, 97.5]); per = [float(x[0] - z[0]) for x, z in zip(A, B)]
        row = {"BA_AULC_diff": float(d[0]), "lo": float(lo), "hi": float(hi), "per_repeat": per}
        if ref == "GPC_X":
            row["verdict"] = "AUX EFFECT REPRODUCED (DEV)" if d[0] >= 0.04 and lo > 0 and sum(v > 0 for v in per) >= 3 else "NOT REPRODUCED"
        else:
            skc = [M[(cand, r, 40)]["shortK_caught"] for r in REPEATS]; skr = [M[(ref, r, 40)]["shortK_caught"] for r in REPEATS]
            gain = d[0] >= 0.04 and lo > 0 and all(v > 0 for v in per); guard = all(v >= 7 for v in skc) and sum(skc) >= sum(skr) - 4
            row.update({"shortK_caught_B40": skc, "ref_shortK_caught_B40": skr,
                        "verdict": "PRACTICALLY BETTER" if gain and guard else "TRADE-OFF (BA gain with short-K loss)" if gain else "NO PRACTICAL DIFFERENCE"})
        res["contrasts"][f"{cand}-{ref}"] = row
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "results").mkdir(exist_ok=True)
    (OUT / "results" / "PHYS_AUX_REP_RESULTS.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str)); return res


def validate():
    t0 = time.time(); checks, info = {}, {}
    try:
        tasks = build_tasks(); checks["twenty_tasks_with_frozen_EX1_paths"] = len(tasks) == 20 and all(len(t["path"]) >= 40 for t in tasks)
        t = tasks[0]; auxT = PA.aux_table(); tt = time.time(); r = run(t, "PHYS_AUX", auxT, None); info["unit_seconds"] = time.time() - tt
        checks["unit_runs"] = r["status"] == "ok" and len(r["paid"]) == 40
        g = run(t, "G3_MARGIN", auxT, None); checks["reference_runs"] = g["status"] == "ok" and len(g["paid"]) == 40
        checks["frame_for_repeats_5_8"] = len(frame()["ids"]) == 136
        info["one_class_starts"] = [(x["repeat"], x["fold"]) for x in tasks if len(set(x["y"][x["path"][:16]].tolist())) < 2]
    except Exception as ex:
        checks["selftest_completed"] = False; info["error"] = f"{type(ex).__name__}: {ex}"[:400]; info["traceback"] = traceback.format_exc()[-2000:]
    res = {"study": STUDY, "status": "PASS" if checks and all(checks.values()) else "FAIL", "checks": {k: bool(v) for k, v in checks.items()}, "info": info,
           "seconds": time.time() - t0, "module_sha256": SMM.sha256(SMM.ROOT / "src" / "jdl_phys_aux_rep.py")}
    OUT.mkdir(parents=True, exist_ok=True); VALIDATION.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"status": res["status"], "checks": res["checks"], "info": {k: v for k, v in info.items() if k != "traceback"}}, indent=1, default=str))
    if res["status"] != "PASS":
        raise SystemExit(1)


def write_manifest():
    val = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if val["status"] != "PASS" or val["module_sha256"] != SMM.sha256(SMM.ROOT / "src" / "jdl_phys_aux_rep.py"):
        raise SystemExit("PHYS_AUX_REP validation must PASS with this module before the freeze")
    man = {"study": STUDY, "status": "FROZEN BEFORE ANY PHYS_AUX_REP OUTCOME", "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "parent_commit": SMM._git("rev-parse", "HEAD"), "repeats": list(REPEATS), "arms": list(ARMS),
           "continuation_criterion": "AUX EFFECT REPRODUCED iff PHYS_AUX - GPC_X BA-AULC mean >= +0.04, interval > 0, positive in >= 3 of 4 repeats",
           "validation": {"status": val["status"], "sha256": SMM.sha256(VALIDATION)}, "code_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in CODE}}
    MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8"); print(json.dumps({k: man[k] for k in ("status", "written_utc")}, indent=1))


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "evaluate"
    {"validate": validate, "manifest": write_manifest, "work": lambda: work(sys.argv[2:]), "evaluate": evaluate}[step]()
