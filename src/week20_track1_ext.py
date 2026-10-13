"""Week 20 Track 1 extension — the frozen Track 1 benchmark on the remaining DEV repeats 5–8, plus one ablation arm.

POST-HOC DEV RESEARCH (not confirmatory; C3 = repeats 17–20 reserved; C1/C2 spent in Week 18).
The frozen runner src.week20_track1_al is imported unchanged (its file hash is recorded); this module only
  * selects DEV repeats 5–8 (Week 18 DEV block = 1–8),
  * adds arm D = WHOLE_E1_GUARD_STRADDLE: arm A with a slope-sign guard on the learned threshold.  When the paid
    (response, label) pairs are not separable and the 1-D logistic fit has a non-positive slope, the reversed root
    is not used; the threshold becomes the engine's own no-information default u = 111 um (src.week18_engine,
    DepthGPR.fit single-class branch).  Everything else (GP, straddle, startup, budgets) is identical to arm A.
Arms A, B, C run on R3_NEW, R3_OLD and R1_POOLED; arm D runs on R3_NEW, and on any R3_OLD / R1_POOLED run in which
arm A has a non-positive-slope step (elsewhere D is identical to A by construction; checked on R3_NEW).

Steps: python -m src.week20_track1_ext manifest | run [n_jobs] | analyze
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
from pathlib import Path

import numpy as np
import pandas as pd

import src.week20_track1_al as A

OUTX = A.OUT / "track1_ext"
REPEATS_X = (5, 6, 7, 8)
GUARD = "WHOLE_E1_GUARD_STRADDLE"
GUARD_SPEC = {"learner": ("GPR_depth", "mlii"), "rule": "straddle", "response": "whole"}
GUARD_LOG_U = float(np.log(111.0))                 # src.week18_engine.DepthGPR.fit: single-class default
BASE_ARMS = ("WHOLE_E1_STRADDLE", "ACTIVE_E1_STRADDLE", "G3_MARGIN")
CAPS_X = {"round_max_scalar_fits": 15000, "workers": 4, "threads_per_worker": 1, "max_memory_gib_total": 8, "max_elapsed_h_total": 8}
SHORT = {"WHOLE_E1_STRADDLE": "WHOLE E1", "ACTIVE_E1_STRADDLE": "ACTIVE E1", "G3_MARGIN": "G3", GUARD: "WHOLE E1 + guard"}


# ======================================================================================== guarded learner
def _guarded_class():
    import src.week18_engine as E
    from sklearn.linear_model import LogisticRegression

    class GuardedDepthGPR(E.DepthGPR):
        """DepthGPR with a slope-sign guard: a non-positive logistic slope never yields the threshold."""

        def fit(self, X, depth, y, kernel=None, optimize=True):
            super().fit(X, depth, y, kernel=kernel, optimize=optimize)
            ok = np.isfinite(depth); t = np.log(depth[ok]); yy = y[ok]
            kh, nk = t[yy == 1], t[yy == 0]
            self.guard_triggered = False
            if len(kh) and len(nk) and not nk.max() < kh.min():
                lr = LogisticRegression(C=1e6, max_iter=5000).fit(t[:, None], yy)
                if not lr.coef_[0, 0] > 0:
                    self.u = GUARD_LOG_U; self.guard_triggered = True
            return self
    return GuardedDepthGPR


def job_x(task, arm):
    """One run through the frozen runner (A.job: cache, ledger, fits, predictions); the guard arm swaps the engine's
    DepthGPR class for the guarded subclass for the duration of the run only."""
    import src.week18_engine as E
    A.ARMS.setdefault(GUARD, GUARD_SPEC)
    orig = E.DepthGPR
    if arm == GUARD:
        E.DepthGPR = _guarded_class()
    try:
        return A.job(task, arm)
    finally:
        E.DepthGPR = orig


def build_tasks_x(repeats=REPEATS_X):
    old = A.REPEATS
    A.REPEATS = tuple(repeats)
    try:
        return A.build_tasks()
    finally:
        A.REPEATS = old


def _load(task, arm):
    p = A.cache_path(task, arm)
    return json.loads(gzip.decompress(p.read_bytes())) if p.exists() else None


# ======================================================================================== historical expectations (Week 18 caches)
def historical(repeats=REPEATS_X):
    """WHOLE E1 (phase3/depth3) and G3 margin (phase2) from the Week 18 DEV caches, grid budgets <= 80: AULC
    contrasts per task and the folds whose WHOLE threshold reached 200 um.  Historical results, already known."""
    import src.week20_track1_analysis as N
    from src.week18_metrics import contrast
    tasks = build_tasks_x(repeats)
    hist = {"WHOLE_E1_STRADDLE": ("phase3/depth3/cache_real", ("GPR_depth", "mlii", "straddle")), "G3_MARGIN": ("phase2/cache_real", ("G3", "mlii", "margin"))}
    preds, hi = [], []
    for t in tasks:
        for arm, (sub, key) in hist.items():
            for r in json.loads((A.W18 / sub / f"{t['task']}__r{t['repeat']:03d}_f{t['fold']}.json").read_text()):
                if (r["model"], r["hyper"], r["rule"]) != key or int(r["budget"]) > A.BMAX:
                    continue
                preds.append({"task": t["task"], "repeat": t["repeat"], "fold": t["fold"], "arm": arm, "budget": int(r["budget"]),
                              "rows": np.array(r["rows"].split(","), int), "p": np.array(r["p"].split(","), float)})
                u = r.get("u")
                if arm == "WHOLE_E1_STRADDLE" and t["task"] == "R3_NEW" and u not in (None, "", "nan") and float(u) >= A.HIGH_U:
                    hi.append((t["repeat"], t["fold"]))
    c = N.curves(tasks, preds); au = N.aulc_table(c)
    ct = contrast(au, "BA_AULC", "WHOLE_E1_STRADDLE", "G3_MARGIN")
    return {"WHOLE_minus_G3_BA_AULC_to_B80": {r.task: {"mean": round(r["mean"], 4), "lo": round(r.lo, 4), "hi": round(r.hi, 4), "repeats": int(r.repeats)} for _, r in ct.iterrows()},
            "WHOLE_R3_NEW_folds_with_u_ge_200_at_grid_budgets": sorted({f"r{a}f{b}" for a, b in hi})}


def startup_checks(tasks):
    """Label use limited to the protocol's own startup (paid labels only): does any ACTIVE run start with single-class
    usable (finite-A) pairs, which the frozen failure rule turns into a stopped run?"""
    import src.week18_engine as E
    rows = []
    for t in tasks:
        L = np.asarray(E.startup(t)); ok = np.isfinite(t["A"][L])
        rows.append({"task": t["task"], "repeat": t["repeat"], "fold": t["fold"], "startup": len(L), "classes_all": len(set(t["y"][L])),
                     "classes_finite_A": len(set(t["y"][L][ok])), "A_unavailable_in_startup": int((~ok).sum())})
    return pd.DataFrame(rows)


# ======================================================================================== manifest (committed before any fit)
HYPOTHESES_X = {
    "X-H0_fidelity": "Arms A and C reproduce the Week 18 DEV caches (phase3/depth3 E1; phase2 G3|mlii|margin) on repeats 5-8 at every grid budget <= 80: max |p_new - p_cache| <= 1e-4. Their contrasts then equal the historical values listed under historical_expectations.",
    "X-H1_primary_replication": "R3_NEW BA-AULC (grid 16..80 step 4), ACTIVE_E1_STRADDLE minus G3_MARGIN, on repeats 5-8 is > 0 (repeat-bootstrap mean). Basis: repeats 1-4 +0.057 [-0.007, +0.115] (per repeat +0.062, -0.032, +0.067, +0.132). No magnitude predicted.",
    "X-H2_target_ablation": "R3_NEW BA-AULC, ACTIVE minus WHOLE, on repeats 5-8 is > 0. Basis: repeats 1-4 +0.070 [+0.030, +0.110]. No magnitude predicted.",
    "X-H3a_guard_identity": "In every run in which arm A has no non-positive-slope step, arm D (WHOLE + guard) is identical to arm A: the same paid sequence and the same test probabilities (max |dp| = 0). A code-level check of the ablation.",
    "X-H3b_guard_effect": "R3_NEW BA-AULC, WHOLE + guard minus WHOLE, on repeats 5-8 is > 0. Basis: the reversed-slope trap (only paid negative = the late negative, whole 312 um) caused all six long WHOLE episodes on repeats 1-4, and the historical WHOLE threshold reached 200 um in 7 of 20 R3_NEW folds of repeats 5-8 (historical_expectations). No magnitude predicted.",
    "X-H3c_remaining_target_effect": "R3_NEW BA-AULC, ACTIVE minus (WHOLE + guard): the part of the ACTIVE-WHOLE difference not removed by the guard. No directional expectation.",
    "X-H4_old_pooled": "R3_OLD: |ACTIVE - WHOLE| < 0.01 and ACTIVE - G3 > 0 (repeats 1-4: +0.001 and +0.030). R1_POOLED: ACTIVE - G3 >= WHOLE - G3 (repeats 1-4: +0.005 vs +0.003).",
    "X-H5_threshold_mechanism": "ACTIVE E1 never reaches u >= 200 um on R3_NEW (repeats 1-4 maximum 188.9 um); falsified by any such step. In every WHOLE R3_NEW run with a u >= 200 um step, the late negative was paid before the first such step (temporal precedence only).",
    "X-H6_eight_repeat_summary": "Descriptive: ACTIVE - G3 and ACTIVE - WHOLE on R3_NEW over DEV repeats 1-8 (repeat bootstrap, 8 repeats). No expectation on whether the interval excludes 0.",
    "X-H7_secondary": "q20, specificity, sensitivity, short-K sensitivity, Brier, AUC and QTT are reported without expectations.",
}
DECISION_RULE = ("C3 protocol draft: written (NOT executed) only if X-H1 holds (repeats 5-8 point estimate > 0) AND the repeats 1-8 point estimate of "
                 "R3_NEW ACTIVE - G3 BA-AULC is > 0; otherwise HOLD (no C3 protocol). Spending C3 remains the owner's decision.")


def write_manifest_x():
    tasks = build_tasks_x()
    OUTX.mkdir(parents=True, exist_ok=True)
    st = startup_checks(tasks); st.to_csv(OUTX / "startup_checks.csv", index=False, lineterminator="\n")
    hist = historical()
    code = ["src/week20_track1_ext.py", "src/week20_track1_ext_analysis.py", "src/week20_track1_al.py", "src/week20_track1_analysis.py", "src/week18_engine.py", "src/week18_tasks.py", "src/week17_models.py",
            "src/week17_audit_impact.py", "src/week13_synthetic_al.py", "src/week18_metrics.py", "src/week19_dev_pilot.py"]
    n_guard_new = sum(t["task"] == "R3_NEW" for t in tasks)
    man = {
        "status": "POST-HOC DEV RESEARCH - not confirmatory; C3 (repeats 17-20) reserved; C1/C2 spent in Week 18",
        "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "written_before_any_extension_fit": True,
        "branch": A._git("rev-parse", "--abbrev-ref", "HEAD"), "parent_commit": A._git("rev-parse", "HEAD"),
        "protocol": "frozen Track 1 protocol (track1/manifest_track1.json, commit acb14d4f) unchanged: tasks, splits, startup, per-step ML-II fits to B80, straddle/margin, leakage guard, ledgers, endpoints, failure rules",
        "repeats": list(REPEATS_X), "dev_block": "Week 18 DEV = repeats 1-8 (src.week18_tasks.BLOCKS)",
        "arms": {**{k: {"learner": list(v["learner"]), "rule": v["rule"], "response": v["response"]} for k, v in A.ARMS.items() if k in BASE_ARMS},
                 GUARD: {"learner": list(GUARD_SPEC["learner"]), "rule": "straddle", "response": "whole",
                         "guard": "if the paid (log whole, label) pairs are not separable and the logistic slope (C=1e6) is <= 0, u = log(111 um), the engine's single-class default; otherwise identical to WHOLE_E1_STRADDLE"}},
        "arm_scope": {"WHOLE_E1_STRADDLE": "R3_NEW, R3_OLD, R1_POOLED", "ACTIVE_E1_STRADDLE": "R3_NEW, R3_OLD, R1_POOLED", "G3_MARGIN": "R3_NEW, R3_OLD, R1_POOLED",
                      GUARD: "all R3_NEW runs; on R3_OLD / R1_POOLED only the runs in which arm A has >= 1 non-positive-slope step (phase 2, run in (task, repeat, fold) order while the round cap allows; any not run are listed). Elsewhere D equals A by construction."},
        "not_run_and_why": "arm D on repeats 1-4 (it would push the round above 15,000 scalar fits); C3; any simulator job",
        "tasks": {t: {"repeats": list(REPEATS_X), "folds": 5, "grid": list(A.grid(t))} for t in A.TASKS},
        "task_checks": {"n_task_folds": len(tasks), "whole_response_equals_pilot_inputs_max_abs": max(t["whole_check"] for t in tasks),
                        "labels_equal_pilot_inputs": all(t["y_check"] for t in tasks),
                        "split_sha256": {f"{t['task']}_r{t['repeat']}_f{t['fold']}": hashlib.sha256((",".join(map(str, t["pool"])) + "|" + ",".join(map(str, t["test"]))).encode()).hexdigest()[:16] for t in tasks},
                        "startup_single_class_finite_A_runs": st[st.classes_finite_A < 2][["task", "repeat", "fold"]].to_dict("records"),
                        "startup_A_unavailable_runs": st[st.A_unavailable_in_startup > 0][["task", "repeat", "fold"]].to_dict("records")},
        "historical_expectations": hist,
        "endpoints": {"primary": "R3_NEW BA-AULC ACTIVE - G3 on repeats 5-8 (Week 18 repeat bootstrap, 4000, seed 0)",
                      "ablations": ["R3_NEW ACTIVE - WHOLE", "R3_NEW (WHOLE + guard) - WHOLE", "R3_NEW ACTIVE - (WHOLE + guard)"],
                      "summary": "repeats 1-8 (Track 1 caches for 1-4 + this extension), same contrasts",
                      "secondary": "R3_OLD, R1_POOLED; q20, specificity, sensitivity, short-K sensitivity, Brier, AUC (AULC); QTT with the frozen definition (target = G3's mean BA at B40/B80 over the repeats analysed); guard activations; learned-threshold mechanism"},
        "hypotheses": HYPOTHESES_X, "decision_rule": DECISION_RULE,
        "budget_plan": {"phase1_runs": len(tasks) * len(BASE_ARMS) + n_guard_new, "phase1_max_fits": (len(tasks) * len(BASE_ARMS) + n_guard_new) * (A.BMAX - 8 + 1),
                        "round_cap": CAPS_X, "accounting": "this continuation round is counted separately from the Week 20 round (13,131 scalar fits); cumulative totals are reported"},
        "code_sha256": {c: A.sha256(A.ROOT / c) for c in code}}
    (OUTX / "manifest_track1_ext.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    lines = ["# Track 1 extension: hypotheses and decision rule (frozen before any extension fit)", "",
             f"*Written {man['written_utc']}; methods in `manifest_track1_ext.json`. Post-hoc DEV research, not confirmation.*", "", "## Hypotheses", ""]
    lines += [f"- **{k}.** {v}" for k, v in HYPOTHESES_X.items()]
    lines += ["", "## Decision rule", "", f"- {DECISION_RULE}", "", "## Historical expectations (Week 18 caches, grid budgets <= 80)", ""]
    lines += [f"- WHOLE - G3 BA-AULC, {k}: {v['mean']:+.4f} [{v['lo']:+.4f}, {v['hi']:+.4f}] ({v['repeats']} repeats)" for k, v in hist["WHOLE_minus_G3_BA_AULC_to_B80"].items()]
    lines += [f"- R3_NEW folds where the historical WHOLE threshold reached 200 um: {', '.join(hist['WHOLE_R3_NEW_folds_with_u_ge_200_at_grid_budgets'])}"]
    (OUTX / "HYPOTHESES_TRACK1_EXT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: man[k] for k in ("budget_plan", "historical_expectations")}, indent=1)); print(st.groupby("task")[["classes_finite_A", "A_unavailable_in_startup"]].agg(["min", "max"]))
    return man


# ======================================================================================== run
def _fits_in_cache(pairs):
    return sum(_load(t, a)["meta"]["n_fits"] for t, a in pairs if A.cache_path(t, a).exists())


def run_x(n_jobs=4):
    from joblib import Parallel, delayed
    if not (OUTX / "manifest_track1_ext.json").exists():
        raise SystemExit("commit the extension manifest before any fit")
    tasks = build_tasks_x()
    phase1 = [(t, a) for t in tasks for a in BASE_ARMS] + [(t, GUARD) for t in tasks if t["task"] == "R3_NEW"]
    log = []
    for phase, todo in (("phase1", phase1), ("phase2", None)):
        if todo is None:                                   # conditional guard runs on R3_OLD / R1_POOLED
            todo = []
            for t in tasks:
                if t["task"] == "R3_NEW":
                    continue
                f = pd.DataFrame(_load(t, "WHOLE_E1_STRADDLE")["fits"])
                if f.get("slope_nonpositive", pd.Series(dtype=bool)).fillna(False).astype(bool).any():
                    todo.append((t, GUARD))
        done = _fits_in_cache([(t, a) for t in tasks for a in (*BASE_ARMS, GUARD)])
        remaining = [(t, a) for t, a in todo if not A.cache_path(t, a).exists()]
        room = CAPS_X["round_max_scalar_fits"] - done
        allowed = []
        for ta in remaining:                               # (task, repeat, fold) order; stop before the cap
            if (len(allowed) + 1) * (A.BMAX - 8 + 1) > room:
                break
            allowed.append(ta)
        skipped = [(t["task"], t["repeat"], t["fold"], a) for t, a in remaining[len(allowed):]]
        print(f"{phase}: {len(todo)} runs, {len(todo) - len(remaining)} cached; {len(allowed)} to run (<= {len(allowed) * (A.BMAX - 8 + 1)} fits; room {room}); not run: {skipped}", flush=True)
        t0 = time.time()
        allowed.sort(key=lambda ta: -len(ta[0]["pool"]))
        metas = Parallel(n_jobs=n_jobs, verbose=5)(delayed(job_x)(t, a) for t, a in allowed) if allowed else []
        log.append({"phase": phase, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "runs": len(metas), "elapsed_s": time.time() - t0,
                    "n_jobs": n_jobs, "fits_this_phase": int(sum(m["n_fits"] for m in metas)), "not_run": skipped,
                    "max_worker_peak_memory_bytes": int(max([m["peak_memory_bytes"] for m in metas] or [0])),
                    "statuses": pd.Series([m["status"] for m in metas]).value_counts().to_dict() if metas else {}})
    (A.OUT / "provenance").mkdir(parents=True, exist_ok=True)
    with open(A.OUT / "provenance" / "track1_ext_run_log.jsonl", "a") as fh:
        for r in log:
            fh.write(json.dumps(r) + "\n")
    print(json.dumps(log, indent=1))


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "manifest"
    if step == "manifest":
        write_manifest_x()
    elif step == "run":
        run_x(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    elif step == "analyze":
        from src.week20_track1_ext_analysis import main
        main()
