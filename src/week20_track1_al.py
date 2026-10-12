"""Week 20 Track 1 — real active-learning benchmark with complete acquisition ledgers (DEV repeats 1–4).

POST-HOC DEV RESEARCH (not confirmatory; C3 reserved).  Arms, all on the same tasks, folds and startup:
  A  WHOLE_E1_STRADDLE   historical Week 18 E1: GPR on log whole-record max depth (per-step ML-II) + straddle
  B  ACTIVE_E1_STRADDLE  identical code, response = A (active-window max depth; NaN for the one unavailable run)
  C  G3_MARGIN           historical Week 18 REF: G3 binary GPC (per-step ML-II, safeguarded Laplace) + margin
Tasks: R3_NEW, R3_OLD, R1_POOLED from src.week18_tasks (full depth), repeats 1–4, five folds; budgets up to 80.
The loop replicates src.week18_engine.run exactly (startup, fit_learner, straddle/margin choice) and records every
query; the learner receives labels/responses of paid rows only (unpaid rows masked).

Steps: python -m src.week20_track1_al manifest | run [n_jobs] | analyze | all
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")          # one BLAS thread per worker; at most 4 workers -> <= 4 CPU threads

import datetime as dt
import gzip
import hashlib
import json
import subprocess
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "week20_active_temporal_development"
T1 = OUT / "track1"
CACHE = OUT / "_cache" / "track1"
PILOT = ROOT / "outputs" / "week19_temporal_regime_dev_pilot"
W18 = ROOT / "outputs" / "week18_independent_research"
START_COMMIT = "7707d7f43f1c36a1d4cce3c18edaf563e75a1fe9"
TASKS = ("R3_NEW", "R3_OLD", "R1_POOLED")
REPEATS = (1, 2, 3, 4)
BMAX = 80
ARMS = {"WHOLE_E1_STRADDLE": {"learner": ("GPR_depth", "mlii"), "rule": "straddle", "response": "whole"},
        "ACTIVE_E1_STRADDLE": {"learner": ("GPR_depth", "mlii"), "rule": "straddle", "response": "A"},
        "G3_MARGIN": {"learner": ("G3", "mlii"), "rule": "margin", "response": None}}
LATE_NEG = "P-353p784791664_VX-0p953661701626_LS-4p00659722232e-05_ST-310p795032219_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p05852399734e-06_H-f4fc937e86"
HIGH_U = 200.0
CAPS = {"track1_max_scalar_fits": 13500, "total_scalar_fits": 15000, "workers": 4, "threads_per_worker": 1, "max_memory_gib_total": 8, "max_elapsed_h_total": 8}
FP_RULE = 1e-6


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def _git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, cwd=ROOT).stdout.strip()


def short(s):
    return "H-" + str(s).split("_H-")[-1]


def peak_memory_bytes():
    from src.week19_dev_pilot import peak_memory_bytes as pm
    return pm()


def grid(task):
    return tuple(range(16, BMAX + 1, 4)) if task == "R3_NEW" else tuple(range(16, BMAX + 1, 8))


# ======================================================================================== tasks
def build_tasks():
    """R3_NEW, R3_OLD, R1_POOLED (src.week18_tasks.all_real_full_depth, DEV), repeats 1–4, with ids and A attached."""
    import src.week18_tasks as T
    inp = pd.read_csv(PILOT / "tables/pilot_inputs.csv").set_index("sim_id")
    new, old = T.new_old_frames()
    ids_of = {"R3_NEW": new.sim_id.astype(str).to_numpy(), "R3_OLD": old.sim_id.astype(str).to_numpy(), "R1_POOLED": T.pooled_frame().sim_id.astype(str).to_numpy()}
    out = []
    for t in T.all_real_full_depth("DEV"):
        if t["task"] not in TASKS or t["repeat"] not in REPEATS:
            continue
        ids = ids_of[t["task"]]
        if len(ids) != len(t["y"]):
            raise ValueError("id order mismatch")
        t = dict(t)
        t["ids"] = ids
        t["A"] = pd.Series(ids).map(inp.A_um).to_numpy(float)
        t["whole_check"] = float(np.nanmax(np.abs(pd.Series(ids).map(inp.whole_max_um).to_numpy(float) - t["depth"])))
        t["y_check"] = bool((pd.Series(ids).map(inp.has_keyhole).to_numpy(int) == t["y"]).all())
        out.append(t)
    return sorted(out, key=lambda t: (t["task"], t["repeat"], t["fold"]))


def shortk_ids():
    from src.week19_dev_pilot import shortk_ids as sk
    return set(sk(pd.read_csv(PILOT / "tables/pilot_inputs.csv")))


# ======================================================================================== ledgered run
def threshold_details(t, y):
    from src.week19_dev_pilot import threshold_details as td
    return td(t, y)


def run_arm(task, arm_name):
    """One active-learning run.  Returns dict(ledger rows, fit rows, prediction rows, meta)."""
    from scipy.special import ndtr  # noqa: F401  (engine dependency)
    import src.week18_engine as E
    arm = ARMS[arm_name]
    E._PHYS[0] = task.get("phys_fn")
    X, y, ids, pool, test = task["X"], task["y"], task["ids"], task["pool"], task["test"]
    resp = task["depth"] if arm["response"] == "whole" else (task["A"] if arm["response"] == "A" else None)
    t0 = time.time()
    L = list(E.startup(task))                                    # identical for every arm (task seed + [2])
    startup_n = len(L)
    state = {"kernel": None, "b0": len(L)}
    ledger, fits, preds = [], [], []
    order = pool[E.maximin_order(X[pool], np.random.default_rng(list(task["seed"]) + [2]))]
    rank = {int(s): i + 1 for i, s in enumerate(order)}
    key = {"task": task["task"], "repeat": task["repeat"], "fold": task["fold"], "arm": arm_name}

    def reveal(q, i, rule, score, runner_up, n_cand, model_state):
        yL = y[np.asarray(L[:q])]
        row = {**key, "query_index": q, "sim_id": ids[i], "H": short(ids[i]), "rule": rule, "score": score, "runner_up_score": runner_up,
               "n_candidates": n_cand, "label": int(y[i]), "response_used": arm["response"] or "none",
               "response_value_um": float(resp[i]) if resp is not None else np.nan, "whole_um": float(task["depth"][i]), "A_um": float(task["A"][i]),
               "paid_pos": int((yL == 1).sum()), "paid_neg": int((yL == 0).sum()), "cumulative_cost": q}
        if resp is not None:
            r = resp[np.asarray(L[:q])]; ok = np.isfinite(r)
            row.update({"usable_pairs_pos": int((yL[ok] == 1).sum()), "usable_pairs_neg": int((yL[ok] == 0).sum()), "deepest_paid_negative_um": float(np.nanmax(np.where(yL == 0, r, np.nan))) if ((yL == 0) & ok).any() else np.nan})
        row.update(model_state or {})
        ledger.append(row)
    for q, i in enumerate(L, 1):
        reveal(q, i, "startup_maximin", float(rank[int(i)]), np.nan, len(pool), None)
    status = "ok"
    while True:
        b = len(L)
        Lr = np.asarray(L)
        y_m = np.full(len(y), -1, int); y_m[Lr] = y[Lr]
        d_m = np.full(len(y), np.nan)
        if resp is not None:
            d_m[Lr] = resp[Lr]
        mt = {"X": X, "y": y_m, "pool": pool, "prior": task["prior"], "depth": d_m}
        fs = {**key, "budget": b, "labels_passed": int((y_m >= 0).sum()), "responses_passed": int(np.isfinite(d_m).sum())}
        tf = time.time()
        with warnings.catch_warnings(record=True) as wl:
            warnings.simplefilter("always")
            try:
                if resp is not None:
                    ok = np.isfinite(resp[Lr])
                    if len(set(y[Lr][ok].tolist())) < 2:
                        raise RuntimeError("single-class usable response pairs (no 111 um fallback)")
                f = E.fit_learner(arm["learner"], mt, L, None, state)
                err = ""
            except Exception as e:  # recorded, not repaired
                f, err = None, f"{type(e).__name__}: {e}"
        msgs = [str(w.message) for w in wl]
        fs.update({"wall_s": time.time() - tf, "warnings": " | ".join(sorted({m[:120] for m in msgs}))[:400]})
        if f is None:
            fs.update({"status": "failed_exception", "error": err[:300]}); fits.append(fs); status = "failed_exception"; break
        ms = {}
        if arm["response"] is not None:
            tt = np.log(resp[Lr][ok]); yy = y[Lr][ok]
            td = threshold_details(tt, yy)
            ms = {"threshold_branch": td["threshold_branch"], "a": td["a"], "b": td["b"], "log_u": float(f.u), "u_um": float(np.exp(f.u)),
                  "threshold_replication_abs_diff": abs(td["log_u"] - float(f.u)), "root_outside_paid_range": bool(f.u < tt.min() or f.u > tt.max()),
                  "slope_nonpositive": bool(td["threshold_branch"] == "logistic" and not td["b"] > 0),
                  "lml": float(f.gp.log_marginal_likelihood_value_), "lbfgs_warning": any("failed to converge" in m.lower() for m in msgs),
                  "bound_warnings": int(sum("close to the specified" in m for m in msgs))}
        else:
            dg = f.gp.diagnostics_
            ms = {"fp_error": float(getattr(f.gp, "mode_fp_", np.nan)), "optimizer_success": bool(dg.optimizer_converged), "optimizer_iterations": int(dg.optimizer_iterations),
                  "fallback": str(dg.fallback_status), "lml": float(f.gp.log_marginal_likelihood_value_)}
            ms["fp_rule_violation"] = bool(not np.isfinite(ms["fp_error"]) or ms["fp_error"] > FP_RULE)
        fs.update({"status": "ok", **ms})
        fits.append(fs)
        p = np.asarray(E.proba(f, X[test]), float)
        mu, var = (np.asarray(v, float) for v in E.latent(f, X[test]))
        if not (np.isfinite(p).all() and np.isfinite(mu).all() and np.isfinite(var).all()):
            fs["status"] = "failed_nonfinite_prediction"; status = "failed_nonfinite_prediction"; break
        preds.append({"budget": b, "p": p.tolist(), "latent_mean": mu.tolist(), "latent_var": var.tolist()})
        if b >= BMAX:
            break
        cands = np.setdiff1d(pool, Lr)
        if len(cands) == 0:
            break
        if arm["rule"] == "straddle":
            m_c, v_c = E.latent(f, X[cands]); sc = 1.96 * np.sqrt(v_c) - np.abs(m_c); j = int(np.argmax(sc))
            ru = float(np.sort(sc)[-2]) if len(sc) > 1 else np.nan
        else:
            sc = np.abs(E.proba(f, X[cands]) - .5); j = int(np.argmin(sc))
            ru = float(np.sort(sc)[1]) if len(sc) > 1 else np.nan
        if not np.isfinite(sc).all():
            fs["status"] = "failed_nonfinite_score"; status = "failed_nonfinite_score"; break
        nxt = int(cands[j])
        L.append(nxt)
        reveal(len(L), nxt, arm["rule"], float(sc[j]), ru, len(cands), {f"selector_{k}": v for k, v in ms.items() if k in ("u_um", "log_u", "a", "b", "threshold_branch", "fp_error", "lml")})
    meta = {**key, "startup": startup_n, "final_budget": len(L), "status": status, "n_fits": len(fits), "elapsed_s": time.time() - t0,
            "peak_memory_bytes": peak_memory_bytes(), "test": [int(i) for i in test]}
    return {"meta": meta, "ledger": ledger, "fits": fits, "preds": preds}


def cache_path(task, arm):
    return CACHE / f"{task['task']}__r{task['repeat']:03d}_f{task['fold']}__{arm}.json.gz"


def job(task, arm):
    from threadpoolctl import threadpool_limits
    p = cache_path(task, arm)
    if p.exists():
        return json.loads(gzip.decompress(p.read_bytes()))["meta"]
    with threadpool_limits(limits=1):
        res = run_arm(task, arm)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_bytes(gzip.compress(json.dumps(res, default=float).encode()))
    tmp.replace(p)
    return res["meta"]


def run(n_jobs=4):
    from joblib import Parallel, delayed
    man = T1 / "manifest_track1.json"
    if not man.exists():
        raise SystemExit("commit the Track 1 manifest before any fit")
    tasks = build_tasks()
    todo = [(t, a) for t in tasks for a in ARMS]
    done_fits = sum(json.loads(gzip.decompress(cache_path(t, a).read_bytes()))["meta"]["n_fits"] for t, a in todo if cache_path(t, a).exists())
    remaining = [(t, a) for t, a in todo if not cache_path(t, a).exists()]
    worst = sum(BMAX - 8 + 1 for _ in remaining)
    print(f"{len(todo)} runs, {len(todo) - len(remaining)} cached ({done_fits} fits); remaining {len(remaining)} runs, at most {worst} fits", flush=True)
    if done_fits + worst > CAPS["track1_max_scalar_fits"]:
        raise SystemExit("planned fits would exceed the Track 1 cap")
    remaining.sort(key=lambda ta: -len(ta[0]["pool"]))
    t0 = time.time()
    metas = Parallel(n_jobs=n_jobs, verbose=5)(delayed(job)(t, a) for t, a in remaining)
    log = {"started_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "runs": len(metas), "elapsed_s": time.time() - t0, "n_jobs": n_jobs,
           "fits_this_session": int(sum(m["n_fits"] for m in metas)), "max_worker_peak_memory_bytes": int(max([m["peak_memory_bytes"] for m in metas] or [0])),
           "statuses": pd.Series([m["status"] for m in metas]).value_counts().to_dict() if metas else {}}
    (OUT / "provenance").mkdir(parents=True, exist_ok=True)
    with open(OUT / "provenance" / "track1_run_log.jsonl", "a") as fh:
        fh.write(json.dumps(log) + "\n")
    print(json.dumps(log, indent=1))


# ======================================================================================== manifest (written and committed before any fit)
HYPOTHESES = {
    "T1-H0_fidelity": "Arms A and C reproduce the historical Week 18 DEV caches (phase3/depth3 E1; phase2 G3|mlii|margin) on repeats 1-4 at every grid budget <= 80: max |p_new - p_cache| <= 1e-4 (cache rounding is 5 significant digits). Otherwise they are reported as re-implementations with the discrepancy.",
    "T1-H1_primary": "R3_NEW BA-AULC (grid 16..80 step 4), ACTIVE_E1_STRADDLE minus G3_MARGIN, is > 0. Supporting evidence: Week 19 shared-path pilot, B40 ACTIVE - G3 = +0.112 [-0.009, +0.212]; adaptive acquisition untested, so no magnitude is predicted.",
    "T1-H2_ablation": "R3_NEW BA-AULC, ACTIVE minus WHOLE, is > 0 (shared-path pilot B40: +0.098 [+0.013, +0.185]). No magnitude predicted.",
    "T1-H3_old": "R3_OLD: WHOLE minus G3 reproduces the historical DEV value (+0.0286 [+0.0117, +0.0518] on repeats 1-4 up to B80); ACTIVE minus WHOLE is small (|delta| < 0.01), because whole max and A separate OLD labels equally well (AUC 0.99996 both; 37/405 runs differ).",
    "T1-H4_pooled": "R1_POOLED: WHOLE minus G3 reproduces the historical DEV value (+0.0028 [-0.0003, +0.0062]); ACTIVE minus G3 >= WHOLE minus G3 (A separates POOLED labels better: AUC 0.9987 vs 0.9958). No magnitude predicted.",
    "T1-H5_threshold": "WHOLE E1 on R3_NEW reproduces the historical high thresholds (u >= 200 um in 6 of 20 folds of repeats 1-4: r1f5, r2f1, r3f1, r3f2, r4f1, r4f2). ACTIVE E1 never reaches u >= 200 um on R3_NEW (every NEW negative has A <= 131.2 um). Falsified by any ACTIVE R3_NEW step with u >= 200 um.",
    "T1-H6_precedence": "In every WHOLE R3_NEW run with a u >= 200 um step, the late negative H-f4fc937e86 was paid before the first such step. This is temporal precedence only; causal attribution would need an isolated refit and is not claimed.",
    "T1-H7_secondary": "No expectations are set for q20, short-K sensitivity, Brier or AUC; they are reported.",
}


def write_manifest():
    tasks = build_tasks()
    T1.mkdir(parents=True, exist_ok=True)
    code = ["src/week20_track1_al.py", "src/week18_engine.py", "src/week18_tasks.py", "src/week17_models.py", "src/week17_audit_impact.py",
            "src/week9_phase1_11_fixed_mean_discrepancy_gp.py", "src/week13_synthetic_al.py", "src/week18_metrics.py", "src/week19_dev_pilot.py"]
    man = {
        "status": "POST-HOC DEV RESEARCH — not confirmatory; C3 (repeats 17-20) reserved",
        "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "written_before_any_track1_fit": True,
        "start_commit": START_COMMIT, "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "arms": {k: {"learner": list(v["learner"]), "rule": v["rule"], "response": v["response"]} for k, v in ARMS.items()},
        "arm_notes": {"WHOLE_E1_STRADDLE": "historical Week 18 E1 (FREEZE_ROUND_2: GPR on log max depth + straddle, per-step ML-II); response = Week 7 OLD / phase1 NEW whole-record max (src.week18_tasks.depth_map)",
                      "ACTIVE_E1_STRADDLE": "identical code; response = A_active_max_um (Week 19 audit; NaN for H-e7dbd8e5ce, whose query is still paid and whose label is kept)",
                      "G3_MARGIN": "historical Week 18 REF (G3 'phase2' schedule = per-step ML-II for R1/R3, safeguarded Laplace FP_TOL 1e-9) + margin"},
        "tasks": {name: {"source": "src.week18_tasks.all_real_full_depth('DEV')", "repeats": list(REPEATS), "folds": 5, "grid": list(grid(name)),
                         "q20": "unchanged Week 18 construction (R3_NEW: boundary_flags; R3_OLD: Week 8.5 distance rule; R1_POOLED: pooled-q20)"} for name in TASKS},
        "task_checks": {"n_task_folds": len(tasks), "whole_response_equals_pilot_inputs_max_abs": max(t["whole_check"] for t in tasks),
                        "labels_equal_pilot_inputs": all(t["y_check"] for t in tasks),
                        "split_sha256": {f"{t['task']}_r{t['repeat']}_f{t['fold']}": hashlib.sha256((",".join(map(str, t["pool"])) + "|" + ",".join(map(str, t["test"]))).encode()).hexdigest()[:16] for t in tasks}},
        "seeds": "task seed from src.week18_tasks ([1820,rep,fold] R3_NEW; [1822,rep,fold] R3_OLD; [1818,rep,fold] R1_POOLED); startup maximin rng = seed+[2]; engine rule rng = seed+[RULE_ID,11] (unused by straddle/margin)",
        "startup": "src.week18_engine.startup: 8 maximin points of the paid pool + maximin continuation until both classes are revealed; identical for all arms; every query costs 1",
        "transformations": {"E1": "StandardScaler on log(pool X); log response standardized on paid finite responses; ARD Matern-3/2 + white noise; learned threshold: midpoint if separable, else logistic C=1e6 on log response",
                            "G3": "StandardScaler on raw pool X and pool log h; fixed-mean Laplace GPC (ARD Matern-3/2), ML-II one L-BFGS-B start"},
        "acquisition": {"straddle": "argmax 1.96*sd - |mu - log u| over unpaid pool (src.week18_engine.choose)", "margin": "argmin |p - 0.5| over unpaid pool"},
        "fits": "one learner fit after every paid query from the startup size to 80 (original methods); test predictions recorded at every fit",
        "leakage_guard": "the learner receives y and responses with every unpaid row masked (y=-1, response=NaN); held-out labels and q20 flags are evaluator-only",
        "endpoints": {"primary": "R3_NEW pooled-per-repeat BA AULC (trapezoid over 16..80 step 4 / width), ACTIVE_E1_STRADDLE - G3_MARGIN; per-repeat values and the Week 18 repeat bootstrap (4000, seed 0)",
                      "ablation": "R3_NEW ACTIVE - WHOLE", "secondary": ["R3_OLD and R1_POOLED (grid 16..80 step 8) for all contrasts", "q20 AULC (unchanged)",
                                                                         "specificity, sensitivity, short-K sensitivity (fixed ten NEW positives; NEW and POOLED-NEW rows), Brier, AUC at B40/B80 and as AULC",
                                                                         "full per-step curves"],
                      "query_savings": "QTT (Week 18 qtt): first grid budget at which an arm's repeat-pooled BA reaches G3_MARGIN's repeat-1-4 mean BA at B40 and at B80 on the same task; unreached by B80 = 'not reached' (no extrapolation); means use B80 + one grid step for unreached (Week 18 qtt_reduction convention), always with the unreached count",
                      "mechanism": "learned thresholds per step from the ledgers; u >= 200 um episodes; paid composition before the first such step; late-negative timing as precedence only"},
        "hypotheses": HYPOTHESES,
        "failure_rules": ["fit exception, non-finite prediction or non-finite acquisition score: the run stops there, status recorded, later budgets missing; no reseeding or repair",
                          "single-class usable response pairs for an E1 arm: run stops (the engine's 111 um fallback is never used); cannot arise in DEV 1-4 (checked: the A-unavailable run is in no startup set)",
                          "logistic slope <= 0 or root outside the paid range: recorded, not repaired (historical behaviour)",
                          "G3 Laplace fixed-point error > 1e-6: recorded as a Week 18 convergence violation, run continues (historical behaviour)",
                          "no forced queries, no favourable-repeat selection; all 180 runs are reported"],
        "resource_limits": CAPS, "expected_fits": "180 runs x at most 73 fits = 13,140",
        "code_sha256": {c: sha256(ROOT / c) for c in code}}
    (T1 / "manifest_track1.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    print("manifest", sha256(T1 / "manifest_track1.json"))
    return man


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step == "manifest":
        write_manifest()
    if step in ("run", "all"):
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
