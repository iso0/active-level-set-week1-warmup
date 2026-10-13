"""C3 confirmation of ACTIVE E1 + straddle vs G3 + margin (owner-approved 2026-10-13).  Data block C3 = repeats 17-20,
used once.  The freeze (c3/FREEZE_C3.md, c3/freeze_c3.json) is committed before any C3 task object is built.

Arms A (WHOLE E1, ablation), B (ACTIVE E1, candidate), C (G3, reference) run through the frozen Track 1 runner
(src.week20_track1_al.run_arm via A.job; 4 workers x 1 BLAS thread).  The only new code is the task builder for
block C3, identical to src.week20_track1_al.build_tasks except for the block name.

Steps: python -m src.week20_c3_confirm freeze | run [n_jobs] | analyze
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

import numpy as np
import pandas as pd

import src.week20_track1_al as A
from src.week20_track1_ext import BASE_ARMS, job_x

OUTC3 = A.OUT / "c3"
REPEATS_C3 = (17, 18, 19, 20)
BAR, NONINF = 0.02, -0.01
CAP_FITS = 15000
APPROVAL = "Owner approval in chat, 2026-10-13: 'C3 taslağını onaylıyorum, dondur ve çalıştır' (approve the C3 draft, freeze and run)."
CODE = ["src/week20_c3_confirm.py", "src/week20_track1_ext.py", "src/week20_track1_ext_analysis.py", "src/week20_track1_al.py", "src/week20_track1_analysis.py",
        "src/week18_engine.py", "src/week18_tasks.py", "src/week17_models.py", "src/week17_audit_impact.py", "src/week13_synthetic_al.py", "src/week18_metrics.py",
        "src/week19_dev_pilot.py"]


def build_tasks_block(block, repeats):
    """src.week20_track1_al.build_tasks with the block as a parameter (identical attachments and checks)."""
    import src.week18_tasks as T
    inp = pd.read_csv(A.PILOT / "tables/pilot_inputs.csv").set_index("sim_id")
    new, old = T.new_old_frames()
    ids_of = {"R3_NEW": new.sim_id.astype(str).to_numpy(), "R3_OLD": old.sim_id.astype(str).to_numpy(), "R1_POOLED": T.pooled_frame().sim_id.astype(str).to_numpy()}
    out = []
    for t in T.all_real_full_depth(block):
        if t["task"] not in A.TASKS or t["repeat"] not in repeats:
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


def builder_check_on_dev():
    """Pre-freeze check on DEV repeats 5-8 only: the parameterised builder equals the frozen one."""
    from src.week20_track1_ext import build_tasks_x
    a, b = build_tasks_x((5, 6, 7, 8)), build_tasks_block("DEV", (5, 6, 7, 8))
    same = len(a) == len(b) and all(
        (x["task"], x["repeat"], x["fold"]) == (y["task"], y["repeat"], y["fold"]) and np.array_equal(x["pool"], y["pool"]) and np.array_equal(x["test"], y["test"])
        and np.array_equal(x["y"], y["y"]) and np.array_equal(x["ids"], y["ids"]) and np.array_equal(x["A"], y["A"], equal_nan=True)
        and list(x["seed"]) == list(y["seed"]) for x, y in zip(a, b))
    return {"dev_task_folds": len(a), "identical": bool(same)}


SPEC = {
    "status": "FROZEN C3 CONFIRMATION - owner approved; data block C3 used once",
    "approval": APPROVAL,
    "draft": "c3_draft/C3_PROTOCOL_DRAFT.md (commit 2833e175); decision rule, candidate, reference and predictions unchanged",
    "candidate": "ACTIVE_E1_STRADDLE (Track 1 arm B, unchanged; no guard)",
    "reference": "G3_MARGIN (Track 1 arm C, unchanged)",
    "ablation_reported_not_decisive": "WHOLE_E1_STRADDLE (Track 1 arm A)",
    "data": "block C3 = repeats 17-20, 5 folds each, from src.week18_tasks.all_real_full_depth('C3'); tasks R3_NEW (primary), R3_OLD, R1_POOLED; split confirmation on the same 541 runs",
    "procedure": "frozen Track 1 protocol (track1/manifest_track1.json): startup, per-step ML-II fits to B80, straddle/margin, leakage guard (unpaid labels/responses masked), complete ledgers, failure rules (no reseeding, no repair, no forced queries); 4 workers x 1 BLAS thread",
    "endpoints": {"BA_AULC": "pooled-per-repeat BA on the Week 18 grid up to B80 (R3_NEW 16..80 step 4; R3_OLD, R1_POOLED 16..80 step 8), trapezoid / width (src.week20_track1_analysis.curves + aulc_table)",
                  "bootstrap": "src.week18_metrics.contrast: repeat bootstrap, 4,000 resamples, seed 0"},
    "decision_rule": {"Q3a_primary": f"R3_NEW BA-AULC ACTIVE - G3 >= +{BAR:.2f} AND 95 % interval lower bound > 0",
                      "Q3b_no_loss": f"R3_OLD and R1_POOLED BA-AULC ACTIVE - G3 >= {NONINF:+.2f} (point estimates)",
                      "interpretation": {"Q3a and Q3b": "CONFIRMED: ACTIVE E1 + straddle improves on G3 + margin on NEW, without loss on OLD / POOLED",
                                         "Q3a and not Q3b": "IMPROVEMENT ON NEW WITH A LOSS ELSEWHERE",
                                         "not Q3a, point estimate > 0": "NOT CONFIRMED AT THE FROZEN BAR",
                                         "point estimate <= 0": "DOES NOT REPLICATE"},
                      "reported_not_decisive": ["q20, specificity, sensitivity, short-K sensitivity, Brier, AUC", "ACTIVE - WHOLE and WHOLE - G3", "QTT (frozen definition; target = G3's mean BA at B40/B80 over C3)", "learned-threshold mechanism"]},
    "predictions_from_dev": {"R3_NEW_ACTIVE_minus_G3_repeats_1_8": "+0.056 [+0.015, +0.103]; per repeat +0.062, -0.032, +0.067, +0.132, +0.004, +0.029, +0.176, +0.013",
                             "Q3a_pass_probability_from_DEV_resampling": "about 60 % (bar alone 87 %, interval alone 62 %); optimistic, A was defined after the NEW labels were seen",
                             "Q3b": "expected to pass (DEV: OLD +0.023, POOLED +0.005)",
                             "mechanism": "WHOLE E1 expected to show reversed-slope trap episodes on R3_NEW whenever the late negative is the only startup negative; ACTIVE E1 expected to stay below u = 200 um"},
    "failure_rules": ["fit exception, non-finite prediction or score: the run stops, status recorded, later budgets missing; nothing is rerun",
                      "single-class usable response pairs for an E1 arm (e.g. the A-unavailable negative as the only startup negative): the run stops and is reported (the engine's 111 um fallback is never used)",
                      "every C3 run is executed once; no favourable selection; all 180 runs are reported"],
    "budget": f"180 runs x <= 73 fits = 13,140 scalar fits (cap {CAP_FITS:,} for this round)",
    "order": "1) this freeze is committed and pushed; 2) C3 tasks are built and their split hashes and startup composition recorded; 3) all 180 runs; 4) analysis and the locked decision",
}


def write_freeze():
    if any(A.CACHE.glob("*__r01[7-9]_*")) or any(A.CACHE.glob("*__r020_*")):
        raise SystemExit("C3 caches already exist")
    chk = builder_check_on_dev()
    if not chk["identical"]:
        raise SystemExit(f"builder check failed: {chk}")
    OUTC3.mkdir(parents=True, exist_ok=True)
    spec = {**SPEC, "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "parent_commit": A._git("rev-parse", "HEAD"),
            "builder_check_on_DEV_5_8": chk, "code_sha256": {c: A.sha256(A.ROOT / c) for c in CODE}}
    (OUTC3 / "freeze_c3.json").write_text(json.dumps(spec, indent=1), encoding="utf-8")
    r = spec["decision_rule"]
    md = f"""# Freeze — C3 confirmation: ACTIVE E1 + straddle vs G3 + margin

*Written {spec['written_utc']}; committed and pushed before any C3 task object was built.*

- **Approval:** {APPROVAL}
- **Draft:** `c3_draft/C3_PROTOCOL_DRAFT.md` (commit 2833e175). Its decision rule, candidate, reference and predictions are unchanged.
- **Runner:** `python -m src.week20_c3_confirm run 4`
- **Decision:** `python -m src.week20_c3_confirm analyze`

## Candidate, reference and ablation
- **Candidate:** ACTIVE E1 + straddle (Track 1 arm B).
- **Reference:** G3 + margin (arm C).
- **Ablation:** WHOLE E1 + straddle (arm A), reported but not decisive.
- **Code:** all three use the frozen runner `src/week20_track1_al.py`, at 4 workers × 1 BLAS thread.
- **Task builder:** the only new code. It is the frozen builder with the block as a parameter, and was checked identical on DEV repeats 5–8 ({chk['dev_task_folds']} task-folds).

## Data (used once)
- **Block:** C3 = repeats 17–20, 5 folds each.
- **Tasks:** R3_NEW (primary), R3_OLD and R1_POOLED.
- **Type:** split confirmation on the same 541 runs.

## Locked decision rule (ACTIVE − G3; repeat bootstrap, 4,000 resamples, seed 0)
- **Q3a (primary):** {r['Q3a_primary']}.
- **Q3b (no loss):** {r['Q3b_no_loss']}.
- **Interpretation:**
""" + "\n".join(f"  - {k} → **{v}**" for k, v in r["interpretation"].items()) + f"""
- **Reported, not decisive:** {'; '.join(r['reported_not_decisive'])}.

## Predictions (from DEV, written before the run)
""" + "\n".join(f"- **{k}:** {v}" for k, v in spec["predictions_from_dev"].items()) + f"""

## Failure rules
""" + "\n".join(f"- {x}" for x in spec["failure_rules"]) + f"""

## Budget and order
- **Budget:** {spec['budget']}.
- **Order:** {spec['order']}.

## Caveats
- A was defined after the Week 19 audit had seen every NEW label, so C3 tests the procedure on new splits and seeds; it does not test a target chosen blind to the labels.
- C3 is the last unused block.
- With four repeats, the repeat bootstrap is coarse.
"""
    (OUTC3 / "FREEZE_C3.md").write_text(md, encoding="utf-8")
    print(json.dumps(chk), A.sha256(OUTC3 / "freeze_c3.json"))


def run_c3(n_jobs=4):
    from joblib import Parallel, delayed
    import src.week18_engine as E
    fz = "outputs/week20_active_temporal_development/c3/freeze_c3.json"
    if not A._git("log", "--format=%H", "--", fz):
        raise SystemExit("commit and push the C3 freeze before any C3 computation")
    tasks = build_tasks_block("C3", REPEATS_C3)
    st = []
    for t in tasks:
        L = np.asarray(E.startup(t)); ok = np.isfinite(t["A"][L])
        st.append({"task": t["task"], "repeat": t["repeat"], "fold": t["fold"], "startup": len(L), "classes_finite_A": len(set(t["y"][L][ok])),
                   "A_unavailable_in_startup": int((~ok).sum()), "late_negative_in_startup": A.LATE_NEG in set(t["ids"][L]),
                   "split_sha256": hashlib.sha256((",".join(map(str, t["pool"])) + "|" + ",".join(map(str, t["test"]))).encode()).hexdigest()[:16],
                   "whole_check": t["whole_check"], "y_check": t["y_check"]})
    pd.DataFrame(st).to_csv(OUTC3 / "c3_tasks_and_startup.csv", index=False, lineterminator="\n")
    todo = [(t, a) for t in tasks for a in BASE_ARMS if not A.cache_path(t, a).exists()]
    if len(todo) * (A.BMAX - 8 + 1) > CAP_FITS:
        raise SystemExit("planned fits exceed the cap")
    print(f"C3: {len(tasks)} task-folds, {len(todo)} runs to execute (<= {len(todo) * (A.BMAX - 8 + 1)} fits)", flush=True)
    todo.sort(key=lambda ta: -len(ta[0]["pool"]))
    t0 = time.time()
    metas = Parallel(n_jobs=n_jobs, verbose=5)(delayed(job_x)(t, a) for t, a in todo)
    log = {"finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "runs": len(metas), "elapsed_s": time.time() - t0, "n_jobs": n_jobs,
           "fits": int(sum(m["n_fits"] for m in metas)), "max_worker_peak_memory_bytes": int(max([m["peak_memory_bytes"] for m in metas] or [0])),
           "statuses": pd.Series([m["status"] for m in metas]).value_counts().to_dict() if metas else {}}
    with open(A.OUT / "provenance" / "c3_run_log.jsonl", "a") as fh:
        fh.write(json.dumps(log) + "\n")
    print(json.dumps(log, indent=1))


def analyze_c3():
    import src.week20_track1_analysis as N
    from src.week18_metrics import contrast, qtt
    from src.week20_track1_ext_analysis import load, path_overlap_x, thresholds_x
    tasks = build_tasks_block("C3", REPEATS_C3)
    led, fits, preds, metas = load(tasks, BASE_ARMS)
    w = lambda df, name: df.to_csv(OUTC3 / name, index=False, lineterminator="\n")
    w(led, "ledger_all_queries.csv.gz"); w(fits, "fit_diagnostics_all.csv.gz"); w(metas.drop(columns=["test"]), "run_meta.csv")
    c = N.curves(tasks, preds); w(c, "curves_every_step.csv")
    au = N.aulc_table(c); w(au, "aulc_per_repeat.csv")
    rows = []
    for key in ("BA_AULC", "q20_AULC", "specificity_AULC", "sensitivity_AULC", "shortK_sensitivity_AULC", "brier_AULC", "AUC_AULC"):
        for arm, ref in (("ACTIVE_E1_STRADDLE", "G3_MARGIN"), ("ACTIVE_E1_STRADDLE", "WHOLE_E1_STRADDLE"), ("WHOLE_E1_STRADDLE", "G3_MARGIN")):
            rows.append(contrast(au, key, arm, ref))
    ct = pd.concat(rows, ignore_index=True); w(ct, "contrasts.csv")
    g = N.on_grid(c); q = qtt(g, "BA", "G3_MARGIN", at=(40, 80)); q["reached"] = np.isfinite(q.qtt); w(q, "qtt.csv")
    th = thresholds_x(led, fits, tasks); w(th, "threshold_mechanism_runs.csv")
    po = path_overlap_x(led); w(po, "path_overlap.csv")
    get = lambda task: ct[(ct.task == task) & (ct.arm == "ACTIVE_E1_STRADDLE") & (ct.ref == "G3_MARGIN") & (ct.metric == "BA_AULC")].iloc[0]
    new, old, pool = get("R3_NEW"), get("R3_OLD"), get("R1_POOLED")
    q3a = bool(new["mean"] >= BAR and new.lo > 0); q3b = bool(old["mean"] >= NONINF and pool["mean"] >= NONINF)
    verdict = ("CONFIRMED: ACTIVE E1 + straddle improves on G3 + margin on NEW, without loss on OLD / POOLED" if q3a and q3b else
               "IMPROVEMENT ON NEW WITH A LOSS ELSEWHERE" if q3a else "NOT CONFIRMED AT THE FROZEN BAR" if new["mean"] > 0 else "DOES NOT REPLICATE")
    status = metas.status.value_counts().to_dict()
    dec = {"freeze": "c3/freeze_c3.json", "R3_NEW_ACTIVE_minus_G3": {"mean": float(new["mean"]), "lo": float(new.lo), "hi": float(new.hi), "repeats": int(new.repeats)},
           "R3_OLD_ACTIVE_minus_G3": float(old["mean"]), "R1_POOLED_ACTIVE_minus_G3": float(pool["mean"]), "Q3a": q3a, "Q3b": q3b, "verdict": verdict,
           "run_statuses": status, "runs": int(len(metas)), "fits": int(metas.n_fits.sum())}
    (OUTC3 / "decision_c3.json").write_text(json.dumps(dec, indent=1), encoding="utf-8")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    col = {"WHOLE_E1_STRADDLE": "#4477AA", "ACTIVE_E1_STRADDLE": "#CC3311", "G3_MARGIN": "#666666"}
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.4))
    for ax, task in zip(axs, A.TASKS):
        for arm in BASE_ARMS:
            h = c[(c.task == task) & (c.arm == arm)].groupby("budget").BA.agg(["mean", "min", "max"]).reset_index(); h = h[h.budget >= 16]
            ax.plot(h.budget, h["mean"], color=col[arm], lw=1.4, label=arm.split("_")[0] + (" E1" if "E1" in arm else ""))
            ax.fill_between(h.budget, h["min"], h["max"], color=col[arm], alpha=.10, lw=0)
        ax.set_title(f"C3 {task}: BA (mean, range over repeats 17–20)", loc="left", fontsize=8); ax.set_xlabel("paid simulations"); ax.spines[["top", "right"]].set_visible(False)
    axs[0].set_ylabel("balanced accuracy"); axs[0].legend(fontsize=7, frameon=False)
    (OUTC3 / "figures").mkdir(parents=True, exist_ok=True); fig.tight_layout(); fig.savefig(OUTC3 / "figures/c3_BA_curves.png", dpi=160); plt.close(fig)
    pd.set_option("display.width", 250)
    print(au.groupby(["task", "arm"])[["BA_AULC", "q20_AULC"]].mean().round(4)); print(ct[ct.metric.isin(["BA_AULC", "q20_AULC"])].round(4).to_string())
    print(json.dumps(dec, indent=1))
    return dec


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "freeze"
    if step == "freeze":
        write_freeze()
    elif step == "run":
        run_c3(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    elif step == "analyze":
        analyze_c3()
