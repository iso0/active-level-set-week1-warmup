"""TRAINED_AL: real-data DEV active-learning comparison with the trained joint model (owner authorization of 2026-10-15).

EXPLORATORY development on previously inspected simulations (NEW, DEV repeats 3-4, five folds); not confirmation.
C3 stays spent and failed; C4 is not run.  The frozen feature-only B16 starts are the Stage A paths
(outputs/joint_depth_label_development/stage_a/stage_a_paths_NEW_r3_r4.csv; maximin order with task seed + [2]).
Sequential queries B17-B40.  Every arm pays for its 16 startup simulations and every query; common starts and task seeds,
paths diverge after the start.

Arms (the J_trained arms share model and decision rule, so their contrast isolates query selection):
  G3_MARGIN           frozen Week 18 G3 GPC (per-step ML-II, safeguarded Laplace) + argmin |p - 0.5|   (jdl_stage_a.run_control)
  ACTIVE_E1_STRADDLE  frozen Week 18 GPR on log ACTIVE A (per-step ML-II) + straddle                (jdl_stage_a.run_control)
  JT_MARGIN           J_trained = joint depth-label GP (src.jdl_model, Laplace) whose response prior (amplitude, four ARD
                      lengthscales; noise 0.03) is re-estimated by ML-II on the CURRENTLY PAID responses at every budget
                      (src.jdl_ex2.trained_config, unchanged); theta, delta and probit priors as in Stage M; decision p >= 0.5;
                      selector argmin |p - 0.5| (ties by simulation ID)
  JT_PV               the SAME J_trained model and decision; selector = paired probability-variance acquisition: expected
                      reduction of the integrated label-probability variance over the fold reference pool from observing
                      the candidate's label AND response (JointDepthLabelGP.acquisition via jdl_stage_a.select_pv, with its
                      quadrature acceptance and fixed-ID tie rule; an unresolved ranking is a recorded NUMERICAL STOP)
Observation contract: all candidates' four physical inputs; for paid simulations only, the canonical label and the
available ACTIVE A (z = log(A/111)); a missing A keeps its label and its cost.  No short-K, q20, test outcome, global
count or VX cut enters any learner or selector.
Resumability: every J_trained trajectory writes its complete state after each budget to _cache/trained_al/partial/
(temp file in a tmp/ subdirectory + os.replace; only finished units sit at the top level of the cache); a resumed
trajectory is bitwise identical to an uninterrupted one (checked in `validate`).  Control trajectories are deterministic
and are recomputed from B16 if interrupted.  Workers claim units with O_EXCL lock files (no duplicate work).
Steps: python -m src.jdl_trained_al validate | manifest | work | status        (one BLAS thread per worker)
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
import warnings

import numpy as np
import pandas as pd

import src.jdl_model as JM
import src.jdl_stage_m as SMM

STUDY = "TRAINED_AL"
OUT = SMM.OUT / "trained_al"
CACHE = SMM.OUT / "_cache" / "trained_al"
PATHS = SMM.OUT / "stage_a" / "stage_a_paths_NEW_r3_r4.csv"
MANIFEST = OUT / "TRAINED_AL_MANIFEST.json"
VALIDATION = OUT / "TRAINED_AL_VALIDATION.json"
ARMS = ("G3_MARGIN", "ACTIVE_E1_STRADDLE", "JT_MARGIN", "JT_PV")
REPEATS, FOLDS, B_START, B_END = (3, 4), (1, 2, 3, 4, 5), 16, 40
CODE = ("src/jdl_trained_al.py", "src/jdl_trained_al_eval.py", "src/jdl_stage_a.py", "src/jdl_ex2.py", "src/jdl_model.py", "src/jdl_stage_m.py",
        "src/jdl_evaluate.py", "src/week18_engine.py")


def _atomic_write(path, obj):
    """Write to <dir>/tmp/<name>.<pid> and move into place (the tmp subdirectory never matches a unit glob)."""
    path.parent.mkdir(parents=True, exist_ok=True); (path.parent / "tmp").mkdir(exist_ok=True)
    tmp = path.parent / "tmp" / f"{path.name}.{os.getpid()}"
    tmp.write_bytes(gzip.compress(json.dumps(obj, default=_default).encode()))
    os.replace(tmp, path)


def _default(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.generic):
        return o.item()
    raise TypeError(type(o).__name__)


def _read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


# ======================================================================================== one J_trained trajectory
def run_jt(task, arm, b_start=B_START, b_end=B_END, ckpt=None, std_fn=None, stop_after=None):
    """J_trained trajectory with per-budget atomic state.  task: X, y, A, ids, pool, test, path."""
    import src.jdl_ex2 as EX2
    import src.jdl_stage_a as SA
    from src.jdl_stage_m import Oracle, standardizer
    oracle = Oracle(task)
    std = std_fn or standardizer(task)[0]
    x_ref = std(task["X"][task["pool"]]); x_test = std(task["X"][task["test"]])
    st = _read(ckpt) if (ckpt is not None and ckpt.exists()) else {"arm": arm, "paid": [int(i) for i in task["path"][:b_start]], "b": b_start,
                                                                  "steps": [], "evals": [], "scores": [], "status": "ok", "resumed_at": []}
    if st["b"] != b_start:
        st["resumed_at"].append(st["b"])
    while st["b"] <= b_end and st["status"] == "ok":
        b = st["b"]; paid = st["paid"]
        pt = oracle.reveal(paid)
        t0 = time.time()
        try:
            Xp = std(pt.X)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                cfg, info = EX2.trained_config(Xp, pt.z)                   # ML-II on the paid responses only
                m = JM.JointDepthLabelGP(x_ref, cfg).fit(Xp, pt.y, pt.z)
        except Exception as e:                                             # recorded, never repaired
            st["status"] = f"fit_failed at B{b}: {type(e).__name__}: {e}"[:300]; break
        q = m.marginals(x_test)
        st["evals"].append({"budget": b, "p": q["p"].tolist(), "h_mean": q["h_mean"].tolist(), "h_var": q["h_var"].tolist(), "f_mean": q["f_mean"].tolist()})
        state = {"budget": b, "n_paid": len(paid), "n_pos": int(pt.y.sum()), "n_neg": int((pt.y == 0).sum()), "n_response": int(np.isfinite(pt.z).sum()),
                 "f_amplitude": info["f_amplitude"], "f_lengthscale": list(info["f_lengthscale"]), "mlii_lml": info["lml"], "mlii_warnings": info["warnings"],
                 "solver_status": m.diagnostics["solver_status"], "gradient_inf": m.diagnostics["gradient_inf"], "theta_mean": q["theta_mean"],
                 "fit_seconds": time.time() - t0, "paid_prefix_sha256": hashlib.sha256("\n".join(pt.ids).encode()).hexdigest()}
        if b == b_end:
            st["steps"].append(state); st["b"] = b + 1
            if ckpt is not None:
                _atomic_write(ckpt, st)
            break
        cand = np.setdiff1d(task["pool"], paid)
        cand_ids = [str(task["ids"][i]) for i in cand]
        log, ts = [], time.time()
        if arm == "JT_PV":
            j, rec = SA.select_pv(m, std(task["X"][cand]), cand_ids, x_ref, log)
        else:
            j, rec = SA.select_margin(m, std(task["X"][cand]), cand_ids, log)
        rec["score_seconds"] = time.time() - ts; rec["score_evaluations"] = len(log)
        state.update(rec); st["steps"].append(state); st["scores"].append({"budget": b, "scores": log})
        if j is None:
            st["status"] = f"numerical_stop at B{b}"; st["b"] = b + 1
        else:
            paid.append(int(cand[j])); st["b"] = b + 1
        if ckpt is not None:
            _atomic_write(ckpt, st)
        if stop_after is not None and b == stop_after:
            return None                                                    # validation only: "killed" after this budget
    st["paid_ids"] = [str(task["ids"][i]) for i in st["paid"]]
    return st


# ======================================================================================== tasks and units
def build_tasks():
    old = SMM.REPEATS; SMM.REPEATS = REPEATS
    try:
        tasks = [t for t in SMM.build_tasks() if t["population"] == "NEW"]
    finally:
        SMM.REPEATS = old
    paths = pd.read_csv(PATHS)
    for t in tasks:
        g = paths[(paths.repeat == t["repeat"]) & (paths.fold == t["fold"])].sort_values("query_index")
        pos = {s: i for i, s in enumerate(t["ids"])}; t["path"] = g.sim_id.map(pos).to_numpy(int)
    return tasks


def units():
    return [(r, f, a) for r in REPEATS for f in FOLDS for a in ARMS]


def unit_name(r, f, a):
    return f"NEW__r{r}_f{f}__{a}"


def run_unit(task, arm):
    import src.jdl_stage_a as SA
    t0 = time.time()
    if arm.startswith("JT_"):
        res = run_jt(task, arm, ckpt=CACHE / "partial" / f"{unit_name(task['repeat'], task['fold'], arm)}.json.gz")
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = SA.run_control(task, arm, B_START, B_END)
    res.update({"study": STUDY, "repeat": task["repeat"], "fold": task["fold"], "arm": arm, "test_ids": [str(task["ids"][i]) for i in task["test"]],
                "start_ids": [str(task["ids"][i]) for i in task["path"][:B_START]], "unit_seconds": time.time() - t0,
                "logical_queries": len(res.get("paid_ids", [])), "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
    return res


def work():
    """Worker: claims unfinished units with O_EXCL locks and runs them; exits when nothing is claimable."""
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not SMM._git("log", "--format=%H", "--", str(MANIFEST.relative_to(SMM.ROOT)).replace("\\", "/")):
        raise SystemExit("commit the TRAINED_AL manifest before any run")
    for c, h in man["code_sha256"].items():
        if SMM.sha256(SMM.ROOT / c) != h:
            raise SystemExit(f"{c} changed after the TRAINED_AL freeze")
    tasks = {(t["repeat"], t["fold"]): t for t in build_tasks()}
    for t in tasks.values():
        if hashlib.sha256("\n".join(t["ids"][t["path"]]).encode()).hexdigest() != man["path_sha256"][f"r{t['repeat']}_f{t['fold']}"]:
            raise SystemExit("path differs from the frozen manifest")
    CACHE.mkdir(parents=True, exist_ok=True); locks = CACHE / "locks"; locks.mkdir(exist_ok=True)
    for r, f, a in units():
        name = unit_name(r, f, a); out = CACHE / f"{name}.json.gz"
        if out.exists():
            continue
        lock = locks / f"{name}.lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
        try:
            if out.exists():
                continue
            res = run_unit(tasks[(r, f)], a)
            _atomic_write(out, res)
            print(json.dumps({"unit": name, "status": res["status"], "seconds": round(res["unit_seconds"], 1), "queries": res["logical_queries"]}), flush=True)
        finally:
            lock.unlink(missing_ok=True)


def status():
    done = {p.name[:-len(".json.gz")] for p in CACHE.glob("NEW__*.json.gz")}
    rows = [{"unit": unit_name(r, f, a), "done": unit_name(r, f, a) in done} for r, f, a in units()]
    print(json.dumps({"done": sum(x["done"] for x in rows), "of": len(rows)}))
    return rows


# ======================================================================================== validation (synthetic + plumbing; no DEV 3-4 outcome revealed)
def validate():
    t0 = time.time(); checks, info = {}, {}
    try:
        import src.jdl_ex2 as EX2
        g = np.random.default_rng(23)
        n_pool, n_test = 40, 15
        Xr = np.exp(g.normal(0, 0.3, (n_pool + n_test, 4)))
        zt = 0.6 * np.log(Xr[:, 0]) / 0.3 - 0.2
        A = 111.0 * np.exp(zt + 0.03 * g.standard_normal(len(Xr)))
        y = ((zt + 0.25 * np.sin(3 * np.log(Xr[:, 1]))) > 0).astype(int)
        A[5] = np.nan
        ids = np.array([f"SIM-{i:03d}" for i in range(len(Xr))])
        pool, test = np.arange(n_pool), np.arange(n_pool, n_pool + n_test)
        path = pool[g.permutation(n_pool)]
        if 5 not in path[:16]:
            path = np.r_[path[path != 5][:8], 5, path[path != 5][8:]]
        task = {"X": Xr, "y": y, "A": A, "ids": ids, "pool": pool, "test": test, "path": path}
        std = lambda X: (np.log(X) - np.log(Xr[pool]).mean(0)) / np.log(Xr[pool]).std(0)
        a = run_jt(task, "JT_PV", 16, 21, std_fn=std); bm = run_jt(task, "JT_MARGIN", 16, 21, std_fn=std)
        checks["trajectories_ok"] = a["status"] == "ok" and bm["status"] == "ok" and len(a["paid"]) == 21 and len(bm["paid"]) == 21
        checks["missing_response_keeps_label_and_cost"] = all(s["n_paid"] == s["n_pos"] + s["n_neg"] and s["n_response"] == s["n_paid"] - 1 for s in a["steps"])
        # the trained prior is fitted on the paid responses only: hidden outcomes cannot change it, nor the first selection
        y2, A2 = y.copy(), A.copy(); hidden = np.setdiff1d(np.arange(len(y)), path[:16]); y2[hidden] = 1 - y2[hidden]; A2[hidden] = 4000.0
        a2 = run_jt({**task, "y": y2, "A": A2}, "JT_PV", 16, 17, std_fn=std)
        checks["hidden_outcomes_do_not_change_trained_prior"] = a2["steps"][0]["f_amplitude"] == a["steps"][0]["f_amplitude"] and a2["steps"][0]["f_lengthscale"] == a["steps"][0]["f_lengthscale"]
        checks["hidden_outcomes_do_not_change_first_selection"] = a2["paid"][16] == a["paid"][16] and [r["score"] for r in a2["scores"][0]["scores"]] == [r["score"] for r in a["scores"][0]["scores"]]
        # the trained prior differs from the frozen Stage M prior (not the fixed-prior implementation under another name)
        z16 = np.where(np.isfinite(A[path[:16]]), np.log(A[path[:16]] / 111.0), np.nan)
        cfg, _ = EX2.trained_config(std(Xr[path[:16]]), z16)
        checks["trained_prior_is_not_stage_m_prior"] = (cfg.f_amplitude, tuple(cfg.f_lengthscale)) != (JM.STAGE_M_CONFIG.f_amplitude, tuple(JM.STAGE_M_CONFIG.f_lengthscale))
        checks["shared_model_and_rule_at_start"] = a["evals"][0]["p"] == bm["evals"][0]["p"]          # same B16 fit in both J_trained arms
        # resumability: kill after B18 and resume in fresh state -> bitwise identical to the uninterrupted run
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            ck = Path(d) / "u.partial.json.gz"
            assert run_jt(task, "JT_PV", 16, 21, ckpt=ck, std_fn=std, stop_after=18) is None
            r = run_jt(task, "JT_PV", 16, 21, ckpt=ck, std_fn=std)
        strip = lambda s: json.dumps({k: s[k] for k in ("paid", "evals", "status")}, default=_default, sort_keys=True)
        checks["resume_bitwise_identical"] = strip(r) == strip(a) and r["resumed_at"] == [19] and \
            [{k: v for k, v in x.items() if not k.endswith("seconds")} for x in r["steps"]] == [{k: v for k, v in x.items() if not k.endswith("seconds")} for x in a["steps"]]
        import src.jdl_stage_a as SA
        ctl = {arm: SA.run_control(task, arm, 16, 18)["status"] for arm in ("G3_MARGIN", "ACTIVE_E1_STRADDLE")}
        checks["controls_run"] = all(s == "ok" or s.startswith("not permitted") for s in ctl.values()); info["controls"] = ctl
        # plumbing on the real tasks: frozen paths, starts, class composition of the starts (no outcome beyond B16)
        tasks = build_tasks()
        info["path_sha256"] = {f"r{t['repeat']}_f{t['fold']}": hashlib.sha256("\n".join(t["ids"][t["path"]]).encode()).hexdigest() for t in tasks}
        sa = json.loads((SMM.OUT / "stage_a" / "stage_a_runner_validation.json").read_text(encoding="utf-8"))["stage_a_plumbing"]["path_sha256"]
        checks["paths_equal_frozen_stage_a_paths"] = info["path_sha256"] == sa
        checks["ten_task_folds"] = len(tasks) == 10
    except Exception as ex:
        checks["selftest_completed"] = False; info["error"] = f"{type(ex).__name__}: {ex}"[:400]; info["traceback"] = traceback.format_exc()[-2000:]
    res = {"study": STUDY, "status": "PASS" if checks and all(checks.values()) else "FAIL", "checks": {k: bool(v) for k, v in checks.items()}, "info": info,
           "seconds": time.time() - t0, "module_sha256": SMM.sha256(SMM.ROOT / "src" / "jdl_trained_al.py")}
    OUT.mkdir(parents=True, exist_ok=True)
    VALIDATION.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"status": res["status"], "checks": res["checks"], "controls": info.get("controls")}, indent=1))
    if res["status"] != "PASS":
        raise SystemExit(1)


def write_manifest():
    val = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if val["status"] != "PASS" or val["module_sha256"] != SMM.sha256(SMM.ROOT / "src" / "jdl_trained_al.py"):
        raise SystemExit("TRAINED_AL validation must PASS with this module before the freeze")
    protocol = (OUT / "TRAINED_AL_PROTOCOL.md")
    man = {"study": STUDY, "status": "FROZEN BEFORE ANY TRAINED_AL OUTCOME", "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "parent_commit": SMM._git("rev-parse", "HEAD"), "authorization": "owner execution request of 2026-10-15 (real-data DEV active-learning comparison with the trained joint model)",
           "population": "NEW-136, DEV repeats 3-4, folds 1-5", "start": "frozen feature-only B16 (stage_a paths)", "budgets": [B_START, B_END], "arms": list(ARMS),
           "path_sha256": val["info"]["path_sha256"], "protocol_file": "trained_al/TRAINED_AL_PROTOCOL.md", "protocol_sha256": SMM.sha256(protocol),
           "validation": {"status": val["status"], "sha256": SMM.sha256(VALIDATION)}, "code_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in CODE},
           "caps": {"trajectories": 40, "fits_max": 40 * 25, "workers_max": 4, "threads_per_worker": 1}}
    MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(json.dumps({k: man[k] for k in ("status", "written_utc", "arms")}, indent=1))


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"validate": validate, "manifest": write_manifest, "work": work, "status": status}[step]()
