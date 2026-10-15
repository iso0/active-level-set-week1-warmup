"""STOP_RULE (Experiment C2): a learner-side stopping rule on the completed J-family adaptive trajectories.  Exploratory DEV
on previously inspected simulations (owner execution request of 2026-10-15, mechanism-led candidate 2 of 2); not
confirmation.  This is a NEW, separately registered question; it does not alter TRAINED_AL's target endpoint (no arm
attained it; that result stands).

Mechanism.  After the smooth region is resolved, margin-type acquisition spends most later queries inside the fast-scan
corner (CORNER_LOCAL: by B40 nearly the whole corner of each training pool is paid), whose labels did not transfer to
held-out corner runs.  If so, the predicted labels of the fold pool stop changing and later queries buy no held-out
performance.  A learner-side rule that detects stabilised predictions can then stop early.
  expected benefit   fewer paid simulations per trajectory with no material loss against continuing to B40
  plausible failure  corner predictions keep flipping as each corner label arrives (no stop), or the rule stops before the
                     smooth region is resolved (loss)
  decisive control   FIXED_STOP: every trajectory stopped at the same budget, the rounded mean adaptive stop of that arm
                     (same average cost, no adaptivity)
Rule (stabilising predictions, Bloodgood & Vijay-Shanker 2009, standard parameters, not tuned): stop set = the fold pool
(features only, fixed across budgets); decisions at cutoff 0.5 of the arm's own predictor refitted on the stored paid
prefix; kappa between consecutive budgets (kappa = 1 for identical decision vectors); stop at the first b in [20, 40] whose
last three transitions (b-3 -> b-2 -> b-1 -> b) have mean kappa >= 0.99; otherwise no stop (cost 40, censored).
Arms (stored paths, never re-acquired): JT_MARGIN (TRAINED_AL) and TREED_MARGIN (CORNER_LOCAL), NEW DEV repeats 3-4.
Observation contract: unchanged (paid features, labels and A; pool features).  The evaluator reads stored test predictions.
Steps: python -m src.jdl_stop_rule validate | manifest | work | evaluate      (one BLAS thread)
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import datetime as dt
import json
import sys
import time
import traceback

import numpy as np
import pandas as pd

import src.jdl_corner_local as CL
import src.jdl_evaluate as EV
import src.jdl_stage_m as SMM
import src.jdl_trained_al as TA
import src.jdl_trained_al_eval as TE

STUDY = "STOP_RULE"
OUT = SMM.OUT / "stop_rule"
CACHE = SMM.OUT / "_cache" / "stop_rule"
MANIFEST = OUT / "STOP_RULE_MANIFEST.json"
VALIDATION = OUT / "STOP_RULE_VALIDATION.json"
RES = OUT / "results"
ARMS = {"JT_MARGIN": ("trained_al", "JT"), "TREED_MARGIN": ("corner_local", "TREED")}
REPEATS, FOLDS, B_MIN_STOP, B_MAX, WINDOW, KAPPA = (3, 4), (1, 2, 3, 4, 5), 20, 40, 3, 0.99
NONINF = {"BA": -0.02, "q20": -0.05, "shortK_events": -2}           # stopped minus B40 (point estimates, mean / sum over repeats)
MIN_SAVING = 4                                                      # queries per trajectory
CODE = ("src/jdl_stop_rule.py", "src/jdl_corner_local.py", "src/jdl_trained_al.py", "src/jdl_trained_al_eval.py", "src/jdl_ex2.py", "src/jdl_model.py",
        "src/jdl_stage_m.py", "src/jdl_evaluate.py", "src/jdl_vx_stump.py")


def kappa(a, b):
    a, b = np.asarray(a, int), np.asarray(b, int)
    if np.array_equal(a, b):
        return 1.0
    po = float(np.mean(a == b)); pa, pb = a.mean(), b.mean()
    pe = pa * pb + (1 - pa) * (1 - pb)
    return float((po - pe) / (1 - pe)) if pe < 1 else 0.0


def stop_budget(kappas):
    """kappas[b] = kappa between decisions at b-1 and b.  First b in [B_MIN_STOP, B_MAX] with mean of the last WINDOW >= KAPPA."""
    for b in range(B_MIN_STOP, B_MAX + 1):
        w = [kappas.get(x) for x in range(b - WINDOW + 1, b + 1)]
        if all(v is not None for v in w) and np.mean(w) >= KAPPA:
            return b
    return None


def stored(arm, r, f):
    src, _ = ARMS[arm]
    p = (TA.CACHE / f"NEW__r{r}_f{f}__JT_MARGIN.json.gz") if src == "trained_al" else (CL.CACHE / f"NEW__r{r}_f{f}__TREED_MARGIN.json.gz")
    return TA._read(p)


def pool_decisions(task, arm, paid_order, budgets, std):
    """Refit the arm's own predictor on each stored paid prefix; decisions on the fold pool and p on the test fold."""
    _, key = ARMS[arm]
    xs = {"pool": std(task["X"][task["pool"]]), "test": std(task["X"][task["test"]])}
    out = {}
    for b in budgets:
        res, _ = CL.predictors(task, std, list(paid_order[:b]), task["repeat"], task["fold"], b, xs)
        out[b] = {"pool": (res["pool"][0][key] >= 0.5).astype(int), "test_p": res["test"][0][key]}
    return out


def run_unit(task, arm):
    st = stored(arm, task["repeat"], task["fold"]); std = SMM.standardizer(task)[0]
    d = pool_decisions(task, arm, st["paid"], range(16, B_MAX + 1), std)
    kap = {b: kappa(d[b - 1]["pool"], d[b]["pool"]) for b in range(17, B_MAX + 1)}
    s = stop_budget(kap)
    test_ok = all(np.array_equal(np.asarray(d[e["budget"]]["test_p"]), np.asarray(e[ARMS[arm][1]] if arm == "TREED_MARGIN" else e["p"]))
                  for e in st["evals"] if e["budget"] in d)
    return {"arm": arm, "repeat": task["repeat"], "fold": task["fold"], "kappa": kap, "stop_budget": s, "cost": s if s is not None else B_MAX,
            "censored": s is None, "pool_decision_changes": {b: int((d[b - 1]["pool"] != d[b]["pool"]).sum()) for b in range(17, B_MAX + 1)},
            "refit_reproduces_stored_test_predictions": bool(test_ok)}


def units():
    return [(a, r, f) for a in ARMS for r in REPEATS for f in FOLDS]


def work(argv=()):
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not SMM._git("log", "--format=%H", "--", str(MANIFEST.relative_to(SMM.ROOT)).replace("\\", "/")):
        raise SystemExit("commit the STOP_RULE manifest before any run")
    for c, h in man["code_sha256"].items():
        if SMM.sha256(SMM.ROOT / c) != h:
            raise SystemExit(f"{c} changed after the STOP_RULE freeze")
    tasks = {(t["repeat"], t["fold"]): t for t in TA.build_tasks()}
    CACHE.mkdir(parents=True, exist_ok=True); locks = CACHE / "locks"; locks.mkdir(exist_ok=True)
    for a, r, f in units():
        name = f"NEW__r{r}_f{f}__{a}"; out = CACHE / f"{name}.json.gz"
        if out.exists():
            continue
        lock = locks / f"{name}.lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
        try:
            t0 = time.time(); res = run_unit(tasks[(r, f)], a); res.update({"study": STUDY, "unit_seconds": time.time() - t0})
            TA._atomic_write(out, res)
            print(json.dumps({"unit": name, "stop": res["stop_budget"], "reproduced": res["refit_reproduces_stored_test_predictions"], "s": round(res["unit_seconds"], 1)}), flush=True)
        finally:
            lock.unlink(missing_ok=True)


# ======================================================================================== evaluation (frozen with the manifest)
def evaluate():
    import gzip
    U = {}
    for p in sorted(CACHE.glob("NEW__*.json.gz")):
        r = json.loads(gzip.decompress(p.read_bytes())); U[(r["arm"], r["repeat"], r["fold"])] = r
    _, F = TE.frame(); W = EV.boot_weights(F["y"]); y, sk = F["y"], F["shortk"]
    pos = {s: i for i, s in enumerate(F["ids"])}
    res = {"units_done": len(U), "units_expected": len(units()), "complete": len(U) == len(units()), "arms": {}}
    rows = []
    for a in ARMS:
        if not all((a, r, f) in U for r in REPEATS for f in FOLDS):
            res["arms"][a] = {"available": False}; continue
        costs = [U[(a, r, f)]["cost"] for r in REPEATS for f in FOLDS]
        fixed_b = int(round(float(np.mean(costs))))
        M = {}
        for rep in REPEATS:
            for label, pick in (("STOPPED", lambda f: U[(a, rep, f)]["cost"]), ("B40", lambda f: B_MAX), ("FIXED_STOP", lambda f: fixed_b)):
                p = np.full(len(F["ids"]), np.nan)
                for f in FOLDS:
                    st = stored(a, rep, f); e = {x["budget"]: x for x in st["evals"]}[pick(f)]
                    q = e["TREED"] if a == "TREED_MARGIN" else e["p"]
                    test_ids = st["test_ids"]
                    p[[pos[s] for s in test_ids]] = q
                m = EV.wmetrics(p, np.ones(len(p), bool), y, sk, F["q20"][rep], F["fold"][rep], W)
                m["shortK_events"] = np.asarray([float(((p >= .5) & sk).sum())]); M[(label, rep)] = m
                rows.append({"arm": a, "setting": label, "repeat": rep, **{k: float(m[k][0]) for k in ("BA", "sensitivity", "specificity", "q20", "shortK_sensitivity", "AUC")},
                             "shortK_detected": int(((p >= .5) & sk).sum())})
        def diff(A, B, k):
            d = np.mean([M[(A, rep)][k] - M[(B, rep)][k] for rep in REPEATS], axis=0); lo, hi = np.nanpercentile(d[1:], [2.5, 97.5])
            return {"estimate": float(d[0]), "lo": float(lo), "hi": float(hi), "per_repeat": [float(M[(A, rep)][k][0] - M[(B, rep)][k][0]) for rep in REPEATS]}
        sk_ev = {lab: int(sum(M[(lab, rep)]["shortK_events"][0] for rep in REPEATS)) for lab in ("STOPPED", "B40", "FIXED_STOP")}
        sv = float(np.mean([B_MAX - c for c in costs]))
        c_ba, c_q = diff("STOPPED", "B40", "BA"), diff("STOPPED", "B40", "q20")
        noninf = c_ba["estimate"] >= NONINF["BA"] and c_q["estimate"] >= NONINF["q20"] and sk_ev["STOPPED"] - sk_ev["B40"] >= NONINF["shortK_events"]
        res["arms"][a] = {"available": True, "stop_budgets": {f"r{r}_f{f}": U[(a, r, f)]["stop_budget"] for r in REPEATS for f in FOLDS},
                          "censored_trajectories": int(sum(U[(a, r, f)]["censored"] for r in REPEATS for f in FOLDS)), "mean_cost": float(np.mean(costs)),
                          "mean_saving_vs_B40": sv, "fixed_stop_budget": fixed_b,
                          "stopped_minus_B40": {"BA": c_ba, "q20": c_q, "shortK_events_sum": sk_ev["STOPPED"] - sk_ev["B40"]},
                          "stopped_minus_fixed_stop": {"BA": diff("STOPPED", "FIXED_STOP", "BA"), "q20": diff("STOPPED", "FIXED_STOP", "q20"),
                                                       "shortK_events_sum": sk_ev["STOPPED"] - sk_ev["FIXED_STOP"]},
                          "shortK_events_of_20": sk_ev,
                          "refits_reproduce_stored_predictions": all(U[(a, r, f)]["refit_reproduces_stored_test_predictions"] for r in REPEATS for f in FOLDS),
                          "verdict": ("SAVING WITHOUT MATERIAL LOSS (DEV, relative to continuing to B40)" if sv >= MIN_SAVING and noninf else "NO SAVING ESTABLISHED")}
    RES.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(RES / "stopped_vs_b40.csv", index=False, lineterminator="\n")
    (RES / "STOP_RULE_RESULTS.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({a: ({k: v[k] for k in ("mean_cost", "mean_saving_vs_B40", "censored_trajectories", "verdict")} if v.get("available") else v) for a, v in res["arms"].items()}, indent=1))
    return res


# ======================================================================================== validation
def validate():
    t0 = time.time(); checks, info = {}, {}
    try:
        checks["kappa_identity_and_edge_cases"] = kappa([1, 1, 0], [1, 1, 0]) == 1.0 and kappa([1, 1, 1], [1, 1, 1]) == 1.0 and abs(kappa([1, 0, 1, 0], [0, 1, 0, 1]) + 1) < 1e-12
        checks["stop_rule_window"] = stop_budget({b: 1.0 for b in range(17, 41)}) == 20 and stop_budget({b: (1.0 if b >= 30 else 0.5) for b in range(17, 41)}) == 32 \
            and stop_budget({b: 0.5 for b in range(17, 41)}) is None
        tasks = {(t["repeat"], t["fold"]): t for t in TA.build_tasks()}; t = tasks[(3, 1)]; std = SMM.standardizer(t)[0]
        for a in ARMS:
            st = stored(a, 3, 1)
            d = pool_decisions(t, a, st["paid"], (16, 17, 40), std)
            ev = {e["budget"]: e for e in st["evals"]}
            checks[f"refit_reproduces_stored_{a}"] = all(np.array_equal(np.asarray(d[b]["test_p"]), np.asarray(ev[b]["TREED"] if a == "TREED_MARGIN" else ev[b]["p"])) for b in (16, 17, 40))
        # leakage: hidden labels and depths corrupted -> identical pool decisions (the rule never sees them)
        y2, A2 = t["y"].copy(), t["A"].copy(); st = stored("JT_MARGIN", 3, 1); hidden = np.setdiff1d(np.arange(len(y2)), st["paid"][:20]); y2[hidden] = 1 - y2[hidden]; A2[hidden] = 4000.0
        d1 = pool_decisions(t, "JT_MARGIN", st["paid"], (20,), std); d2 = pool_decisions({**t, "y": y2, "A": A2}, "JT_MARGIN", st["paid"], (20,), std)
        checks["hidden_outcomes_do_not_change_pool_decisions"] = np.array_equal(d1[20]["pool"], d2[20]["pool"])
        checks["stored_trajectories_complete"] = all((TA.CACHE / f"NEW__r{r}_f{f}__JT_MARGIN.json.gz").exists() and (CL.CACHE / f"NEW__r{r}_f{f}__TREED_MARGIN.json.gz").exists()
                                                     for r in REPEATS for f in FOLDS)
    except Exception as ex:
        checks["selftest_completed"] = False; info["error"] = f"{type(ex).__name__}: {ex}"[:400]; info["traceback"] = traceback.format_exc()[-2500:]
    res = {"study": STUDY, "status": "PASS" if checks and all(checks.values()) else "FAIL", "checks": {k: bool(v) for k, v in checks.items()}, "info": info,
           "seconds": time.time() - t0, "module_sha256": SMM.sha256(SMM.ROOT / "src" / "jdl_stop_rule.py")}
    OUT.mkdir(parents=True, exist_ok=True)
    VALIDATION.write_text(json.dumps(res, indent=1, default=TA._default), encoding="utf-8")
    print(json.dumps({"status": res["status"], "checks": res["checks"], "info": info}, indent=1, default=TA._default))
    if res["status"] != "PASS":
        raise SystemExit(1)


def write_manifest():
    val = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if val["status"] != "PASS" or val["module_sha256"] != SMM.sha256(SMM.ROOT / "src" / "jdl_stop_rule.py"):
        raise SystemExit("STOP_RULE validation must PASS with this module before the freeze")
    man = {"study": STUDY, "status": "FROZEN BEFORE ANY STOP_RULE COMPUTATION", "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "parent_commit": SMM._git("rev-parse", "HEAD"), "authorization": "owner execution request of 2026-10-15 (Experiment C, candidate 2 of 2)",
           "rule": {"stop_set": "fold pool (features only)", "kappa_threshold": KAPPA, "window": WINDOW, "min_stop_budget": B_MIN_STOP, "max_budget": B_MAX},
           "arms": list(ARMS), "noninferiority_vs_B40": NONINF, "min_saving_queries": MIN_SAVING, "decisive_control": "FIXED_STOP at the rounded mean adaptive cost",
           "validation": {"status": val["status"], "sha256": SMM.sha256(VALIDATION)}, "code_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in CODE}}
    MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(json.dumps({k: man[k] for k in ("status", "written_utc", "arms")}, indent=1))


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "evaluate"
    {"validate": validate, "manifest": write_manifest, "work": lambda: work(sys.argv[2:]), "evaluate": evaluate}[step]()
