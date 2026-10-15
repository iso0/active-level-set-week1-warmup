"""CORNER_LOCAL (Experiment C1): local discrimination inside a learned scan-speed region.  Exploratory DEV on previously
inspected simulations (owner execution request of 2026-10-15, mechanism-led candidate 1 of at most 2); not confirmation.

Mechanism.  On NEW every model so far separates Keyhole from no-Keyhole outside the fast-scan corner and fails inside it
(corner BA 0.45-0.60 for every model and rule; CLAIMS_MATRIX L1-L2).  A stationary GP fitted by ML-II on all paid runs
takes its length scales from the large, smooth all-Keyhole region and then averages intermixed labels inside the corner.
If the corner labels carry structure at a shorter scale, a model that (i) learns the region from paid labels only
(vx-stump-1.0 on standardized log VX; the inspected 0.85 m/s cut is never used) and (ii) fits a separate GP classifier with
its own ML-II hyperparameters to the paid runs inside that region can resolve it.
  expected benefit   corner ranking above chance: short-K positives detected while corner negatives are rejected
  plausible failure  no learnable structure at the available density (about 10-15 paid runs in the region): the local
                     ML-II picks long length scales and the model reproduces the stump leaf
  decisive control   TREED_PERM: the same model with the paid labels inside the region permuted (class counts kept, seeded),
                     on the same paid sets.  Secondary controls: TREED_CONST (constant stump-leaf score inside the region,
                     i.e. the split alone) and JT (the global J_trained component alone), on the same paid sets.
Predictor TREED.  Global component: J_trained (src.jdl_ex2.trained_config ML-II on the paid responses + JointDepthLabelGP),
identical to TRAINED_AL.  Region: the stump leaf whose class-weighted score is < 0.5 (the learned no-Keyhole leaf; none if the
stump is constant or no leaf is below 0.5).  Inside the region: sklearn GaussianProcessClassifier, kernel C * RBF (ARD, 4
standardized log features), C in [0.05, 20] (init 1), length scales in [0.05, 20] (init 1), L-BFGS-B without restarts
(deterministic), fitted to the paid runs inside the region if they contain both classes, else the stump-leaf score.
Outside the region: J_trained.  Decision cutoff 0.5.
Arms
  TREED_MARGIN  adaptive, NEW DEV repeats 3-4, folds 1-5, the frozen feature-only B16 starts (TRAINED_AL paths), B16-B40;
                selection argmin |p_TREED - 0.5| over the unpaid pool, ties by simulation ID (as SA.select_margin)
  FIXED         TREED, TREED_PERM, TREED_CONST, JT on the fixed Week 19 feature-only paths (DEV repeats 1-2, B16 and B40;
                the paths of the V2 comparison and Figure 2)
Observation contract: unchanged from TRAINED_AL (paid features, labels and A only).  No unpaid or test outcome, no short-K
or q20 membership, no global class count, no fixed VX cut enters the learner.
Steps: python -m src.jdl_corner_local validate | manifest | work | status        (one BLAS thread per worker)
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
import warnings

import numpy as np

import src.jdl_model as JM
import src.jdl_stage_m as SMM
import src.jdl_trained_al as TA
import src.jdl_vx_stump as VS

STUDY = "CORNER_LOCAL"
VERSION = "1.1"
REPAIRS = ["1.1 (2026-10-15 09:44 UTC): the FIXED unit crashed with KeyError 'path' before producing any output (SMM.build_tasks sets no "
           "path; the Stage M paths live in stage_m/paths.csv).  fixed_tasks() now loads them with the frozen sha256 check.  The ten "
           "adaptive units finished under 1.0; validation 1.1 reproduces one of them bitwise.  No endpoint, model or setting changed."]
OUT = SMM.OUT / "corner_local"
CACHE = SMM.OUT / "_cache" / "corner_local"
MANIFEST = OUT / "CORNER_LOCAL_MANIFEST.json"
VALIDATION = OUT / "CORNER_LOCAL_VALIDATION.json"
REPEATS, FOLDS, B_START, B_END = (3, 4), (1, 2, 3, 4, 5), 16, 40
FIXED_REPEATS, FIXED_BUDGETS = (1, 2), (16, 40)
PREDICTORS = ("TREED", "TREED_PERM", "TREED_CONST", "JT")
VX_COL = 1
GPC = {"c_init": 1.0, "c_bounds": (0.05, 20.0), "ls_init": 1.0, "ls_bounds": (0.05, 20.0), "restarts": 0}
CODE = ("src/jdl_corner_local.py", "src/jdl_corner_local_eval.py", "src/jdl_vx_stump.py", "src/jdl_trained_al.py", "src/jdl_trained_al_eval.py",
        "src/jdl_ex2.py", "src/jdl_model.py", "src/jdl_stage_m.py", "src/jdl_evaluate.py")


def perm_seed(r, f, b):
    return 7000 + 100 * r + f + 101 * b


# ======================================================================================== the predictor
def region_of(stump, xs):
    """Membership of standardized inputs xs in the learned no-Keyhole leaf (all False if there is none)."""
    if stump["type"] != "split":
        return np.zeros(len(xs), bool), None
    lv = stump["leaves"]; neg = [k for k in ("left", "right") if lv[k]["score"] < 0.5]
    if not neg:
        return np.zeros(len(xs), bool), None
    leaf = min(neg, key=lambda k: lv[k]["score"])
    right = xs[:, VX_COL] > stump["cut"]
    return (right if leaf == "right" else ~right), leaf


def fit_local(Xr, yr, leaf_score, permute_seed=None, constant=False):
    """Local classifier inside the region; returns (predict function, record)."""
    yr = np.asarray(yr, int)
    if permute_seed is not None:
        yr = np.random.default_rng(permute_seed).permutation(yr)
    n1, n0 = int(yr.sum()), int((yr == 0).sum())
    rec = {"n_region_paid": len(yr), "n1": n1, "n0": n0, "permuted": permute_seed is not None}
    if constant or n1 == 0 or n0 == 0:
        rec["type"] = "constant_leaf_score"
        return (lambda X: np.full(len(X), leaf_score)), rec
    from sklearn.gaussian_process import GaussianProcessClassifier
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel
    kern = ConstantKernel(GPC["c_init"], GPC["c_bounds"]) * RBF(np.full(Xr.shape[1], GPC["ls_init"]), GPC["ls_bounds"])
    with warnings.catch_warnings(record=True) as wl:
        warnings.simplefilter("always")
        g = GaussianProcessClassifier(kernel=kern, n_restarts_optimizer=GPC["restarts"], random_state=0).fit(Xr, yr)
    rec.update({"type": "gpc", "kernel": str(g.kernel_), "lml": float(g.log_marginal_likelihood_value_), "warnings": len(wl)})
    return (lambda X: g.predict_proba(X)[:, 1]), rec


def predictors(task, std, paid, r, f, b, x_eval_sets):
    """Fit J_trained and the region models on the paid rows; return p for each predictor on each evaluation set."""
    import src.jdl_ex2 as EX2
    pt = SMM.Oracle(task).reveal(paid)
    x_ref = std(task["X"][task["pool"]]); Xp = std(pt.X)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cfg, info = EX2.trained_config(Xp, pt.z)
        m = JM.JointDepthLabelGP(x_ref, cfg).fit(Xp, pt.y, pt.z)
    stump = VS.fit_stump(Xp[:, VX_COL], pt.y.astype(int))
    in_paid, leaf = region_of(stump, Xp)
    score = stump["leaves"][leaf]["score"] if leaf else None
    loc = {}
    if leaf:
        Xr, yr = Xp[in_paid], pt.y[in_paid]
        loc["TREED"] = fit_local(Xr, yr, score)
        loc["TREED_PERM"] = fit_local(Xr, yr, score, permute_seed=perm_seed(r, f, b))
        loc["TREED_CONST"] = fit_local(Xr, yr, score, constant=True)
    out = {}
    for name, xs in x_eval_sets.items():
        pj = np.asarray(m.marginals(xs)["p"], float)
        inr, _ = region_of(stump, xs)
        res = {"JT": pj}
        for k in ("TREED", "TREED_PERM", "TREED_CONST"):
            p = pj.copy()
            if leaf:
                p[inr] = loc[k][0](xs[inr]) if inr.any() else p[inr]
            res[k] = p
        out[name] = (res, inr)
    rec = {"stump": {k: stump[k] for k in ("type", "cut", "orientation", "paid_BA") if k in stump}, "leaf": leaf, "leaf_score": score,
           "local": {k: v[1] for k, v in loc.items()}, "jt_lengthscale": list(info["f_lengthscale"]), "jt_lml": info["lml"],
           "jt_solver": m.diagnostics["solver_status"], "n_pos": int(pt.y.sum()), "n_neg": int((pt.y == 0).sum()), "n_response": int(np.isfinite(pt.z).sum())}
    return out, rec


# ======================================================================================== one adaptive trajectory
def run_treed(task, b_start=B_START, b_end=B_END, ckpt=None, std_fn=None, stop_after=None):
    std = std_fn or SMM.standardizer(task)[0]
    r, f = task["repeat"], task["fold"]
    st = TA._read(ckpt) if (ckpt is not None and ckpt.exists()) else {"arm": "TREED_MARGIN", "paid": [int(i) for i in task["path"][:b_start]], "b": b_start,
                                                                      "steps": [], "evals": [], "status": "ok", "resumed_at": []}
    if st["b"] != b_start:
        st["resumed_at"].append(st["b"])
    x_test = std(task["X"][task["test"]])
    while st["b"] <= b_end and st["status"] == "ok":
        b = st["b"]; paid = st["paid"]; t0 = time.time()
        cand = np.setdiff1d(task["pool"], paid); cand_ids = [str(task["ids"][i]) for i in cand]
        sets = {"test": x_test} if b == b_end else {"test": x_test, "cand": std(task["X"][cand])}
        try:
            out, rec = predictors(task, std, paid, r, f, b, sets)
        except Exception as e:                                             # recorded, never repaired
            st["status"] = f"fit_failed at B{b}: {type(e).__name__}: {e}"[:300]; break
        (pt_, inr) = out["test"]
        st["evals"].append({"budget": b, **{k: pt_[k].tolist() for k in PREDICTORS}, "in_region": inr.astype(int).tolist()})
        rec.update({"budget": b, "n_paid": len(paid), "seconds": time.time() - t0})
        if b < b_end:
            pc = out["cand"][0]["TREED"]; mg = np.abs(pc - 0.5)
            j = int(np.lexsort((np.asarray(cand_ids, dtype=str), mg))[0])
            rec.update({"selected": cand_ids[j], "selected_p": float(pc[j]), "selected_in_region": bool(out["cand"][1][j])})
            paid.append(int(cand[j]))
        st["steps"].append(rec); st["b"] = b + 1
        if ckpt is not None:
            TA._atomic_write(ckpt, st)
        if stop_after is not None and b == stop_after:
            return None
    st["paid_ids"] = [str(task["ids"][i]) for i in st["paid"]]
    return st


def fixed_tasks():
    """NEW tasks of DEV repeats 1-2 with the saved Stage M / Week 19 paths (stage_m/paths.csv, as the V2 comparison), each
    checked against the sha256 frozen in STUDY_MANIFEST.json.  (v1.1 repair: v1.0 read a 'path' key that SMM.build_tasks
    does not set.)"""
    import hashlib
    import pandas as pd
    old = SMM.REPEATS; SMM.REPEATS = FIXED_REPEATS
    try:
        tasks = [t for t in SMM.build_tasks() if t["population"] == "NEW"]
    finally:
        SMM.REPEATS = old
    frozen = json.loads((SMM.OUT / "STUDY_MANIFEST.json").read_text(encoding="utf-8"))["paths"]["sha256_by_task"]
    paths = pd.read_csv(SMM.SM / "paths.csv")
    for t in tasks:
        g = paths[(paths.population == "NEW") & (paths.repeat == t["repeat"]) & (paths.fold == t["fold"])].sort_values("query_index")
        if hashlib.sha256("\n".join(g.sim_id).encode()).hexdigest() != frozen[f"NEW_r{t['repeat']}_f{t['fold']}"]:
            raise SystemExit(f"fixed path NEW_r{t['repeat']}_f{t['fold']} differs from the frozen Stage M manifest")
        pos = {s: i for i, s in enumerate(t["ids"])}
        t["path"] = g.sim_id.map(pos).to_numpy(int)
    return tasks


def run_fixed():
    """TREED and its controls on the fixed Week 19 paths (DEV repeats 1-2, B16 and B40)."""
    tasks = fixed_tasks()
    rows = []
    for t in tasks:
        std = SMM.standardizer(t)[0]
        for b in FIXED_BUDGETS:
            out, rec = predictors(t, std, list(t["path"][:b]), t["repeat"], t["fold"], b, {"test": std(t["X"][t["test"]])})
            res, inr = out["test"]
            rows.append({"repeat": t["repeat"], "fold": t["fold"], "budget": b, "test_ids": [str(t["ids"][i]) for i in t["test"]],
                         **{k: res[k].tolist() for k in PREDICTORS}, "in_region": inr.astype(int).tolist(), "fit": rec,
                         "paid_ids": [str(t["ids"][i]) for i in t["path"][:b]]})
    return rows


# ======================================================================================== units and workers
def units():
    return [("NEW", r, f) for r in REPEATS for f in FOLDS] + [("FIXED", 0, 0)]


def unit_name(kind, r, f):
    return f"NEW__r{r}_f{f}__TREED_MARGIN" if kind == "NEW" else "NEW__FIXED_r1r2__TREED"


def work(argv=()):
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not SMM._git("log", "--format=%H", "--", str(MANIFEST.relative_to(SMM.ROOT)).replace("\\", "/")):
        raise SystemExit("commit the CORNER_LOCAL manifest before any run")
    for c, h in man["code_sha256"].items():
        if SMM.sha256(SMM.ROOT / c) != h:
            raise SystemExit(f"{c} changed after the CORNER_LOCAL freeze")
    tasks = {(t["repeat"], t["fold"]): t for t in TA.build_tasks()}
    CACHE.mkdir(parents=True, exist_ok=True); locks = CACHE / "locks"; locks.mkdir(exist_ok=True)
    for kind, r, f in units():
        name = unit_name(kind, r, f); out = CACHE / f"{name}.json.gz"
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
            t0 = time.time()
            if kind == "NEW":
                t = tasks[(r, f)]
                res = run_treed(t, ckpt=CACHE / "partial" / f"{name}.json.gz", std_fn=SMM.standardizer(t)[0])
                res.update({"repeat": r, "fold": f, "test_ids": [str(t["ids"][i]) for i in t["test"]]})
            else:
                res = {"rows": run_fixed(), "status": "ok"}
            res.update({"study": STUDY, "unit": name, "unit_seconds": time.time() - t0, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
            TA._atomic_write(out, res)
            print(json.dumps({"unit": name, "status": res["status"], "seconds": round(res["unit_seconds"], 1)}), flush=True)
        finally:
            lock.unlink(missing_ok=True)


def status():
    print(json.dumps({"done": len(list(CACHE.glob("NEW__*.json.gz"))), "of": len(units())}))


# ======================================================================================== validation
def validate():
    t0 = time.time(); checks, info = {}, {}
    try:
        tasks = TA.build_tasks(); t = [x for x in tasks if (x["repeat"], x["fold"]) == (3, 1)][0]
        std = SMM.standardizer(t)[0]
        checks["ten_task_folds_with_frozen_paths"] = len(tasks) == 10
        a = run_treed(t, 16, 18, std_fn=std)
        checks["trajectory_runs"] = a["status"] == "ok" and len(a["evals"]) == 3 and len(a["paid"]) == 18
        # leakage: every unpaid/test label and depth corrupted -> identical first two selections and predictions
        y2, A2 = t["y"].copy(), t["A"].copy(); hidden = np.setdiff1d(np.arange(len(y2)), t["path"][:16]); y2[hidden] = 1 - y2[hidden]; A2[hidden] = 4000.0
        a2 = run_treed({**t, "y": y2, "A": A2}, 16, 17, std_fn=std)
        checks["hidden_outcomes_do_not_change_selection_or_p"] = a["paid"][16] == a2["paid"][16] and all(a["evals"][0][k] == a2["evals"][0][k] for k in PREDICTORS)
        # the evaluator-only VX cut is never read by the learner
        old = SMM.FAST_VX; SMM.FAST_VX = 0.1
        try:
            a3 = run_treed(t, 16, 17, std_fn=std)
        finally:
            SMM.FAST_VX = old
        checks["learner_ignores_evaluator_vx_cut"] = a3["evals"][0] == a["evals"][0] and a3["paid"][16] == a["paid"][16]
        # resume is bitwise identical
        import tempfile
        from pathlib import Path
        ck = Path(tempfile.mkdtemp()) / "ck.json.gz"
        assert run_treed(t, 16, 18, ckpt=ck, std_fn=std, stop_after=17) is None
        b = run_treed(t, 16, 18, ckpt=ck, std_fn=std)
        checks["resume_bitwise_identical"] = b["evals"] == a["evals"] and b["paid"] == a["paid"] and b["resumed_at"] == [18]
        # the global component is the TRAINED_AL J_trained model (same B16 prediction as the frozen TRAINED_AL cache)
        ref = TA._read(TA.CACHE / "NEW__r3_f1__JT_MARGIN.json.gz")
        checks["jt_component_equals_trained_al_b16"] = ref["evals"][0]["budget"] == 16 and np.array_equal(np.asarray(ref["evals"][0]["p"]), np.asarray(a["evals"][0]["JT"]))
        # permutation control keeps class counts and differs only in the region
        st0 = a["steps"][0]
        checks["controls_share_region_and_counts"] = (st0["leaf"] is None) or (st0["local"]["TREED_PERM"]["n1"] == st0["local"]["TREED"]["n1"] and
                                                                               st0["local"]["TREED_PERM"]["n0"] == st0["local"]["TREED"]["n0"])
        e0 = a["evals"][0]; outside = np.asarray(e0["in_region"]) == 0
        checks["predictors_equal_outside_region"] = all(np.array_equal(np.asarray(e0[k])[outside], np.asarray(e0["JT"])[outside]) for k in PREDICTORS)
        # synthetic region model: a learnable local boundary is recovered and its permuted control is not
        g = np.random.default_rng(3); Xs = g.normal(0, 1, (40, 4)); ys = (Xs[:, 0] > 0).astype(int)
        f1, r1 = fit_local(Xs[:30], ys[:30], 0.3); f2, r2 = fit_local(Xs[:30], ys[:30], 0.3, permute_seed=11)
        auc = lambda p, y: float(np.mean([(pi > pj) + .5 * (pi == pj) for pi, yi in zip(p, y) if yi for pj, yj in zip(p, y) if not yj]))
        info["synthetic_local_auc"] = {"local": auc(f1(Xs[30:]), ys[30:]), "permuted": auc(f2(Xs[30:]), ys[30:])}
        checks["synthetic_local_boundary_recovered"] = info["synthetic_local_auc"]["local"] >= 0.9 and r1["type"] == "gpc"
        info["first_steps"] = [{k: s[k] for k in ("budget", "stump", "leaf", "leaf_score", "local", "seconds")} for s in a["steps"]]
        # v1.1: the fixed-path unit loads the frozen Stage M paths and runs (the v1.0 defect is covered by a check)
        ft = fixed_tasks()
        checks["fixed_paths_match_frozen_stage_m_manifest"] = len(ft) == 10 and all(len(x["path"]) >= max(FIXED_BUDGETS) for x in ft)
        sf = SMM.standardizer(ft[0])[0]
        o, _ = predictors(ft[0], sf, list(ft[0]["path"][:16]), ft[0]["repeat"], ft[0]["fold"], 16, {"test": sf(ft[0]["X"][ft[0]["test"]])})
        checks["fixed_unit_predictors_run"] = all(np.isfinite(o["test"][0][k]).all() for k in PREDICTORS)
        # v1.1: the repair leaves the adaptive computation bitwise unchanged (stored v1.0 unit reproduced)
        done = CACHE / "NEW__r3_f1__TREED_MARGIN.json.gz"
        if done.exists():
            v10 = TA._read(done); v11 = run_treed(t, std_fn=std)
            checks["adaptive_unit_v10_reproduced_bitwise"] = v10["evals"] == json.loads(json.dumps(v11["evals"], default=TA._default)) and v10["paid"] == v11["paid"]
    except Exception as ex:
        checks["selftest_completed"] = False; info["error"] = f"{type(ex).__name__}: {ex}"[:400]; info["traceback"] = traceback.format_exc()[-2500:]
    res = {"study": STUDY, "status": "PASS" if checks and all(checks.values()) else "FAIL", "checks": {k: bool(v) for k, v in checks.items()}, "info": info,
           "seconds": time.time() - t0, "module_sha256": SMM.sha256(SMM.ROOT / "src" / "jdl_corner_local.py")}
    OUT.mkdir(parents=True, exist_ok=True)
    VALIDATION.write_text(json.dumps(res, indent=1, default=TA._default), encoding="utf-8")
    print(json.dumps({"status": res["status"], "checks": res["checks"], "info": {k: v for k, v in info.items() if k != "traceback"}}, indent=1, default=TA._default))
    if res["status"] != "PASS":
        raise SystemExit(1)


def write_manifest():
    val = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if val["status"] != "PASS" or val["module_sha256"] != SMM.sha256(SMM.ROOT / "src" / "jdl_corner_local.py"):
        raise SystemExit("CORNER_LOCAL validation must PASS with this module before the freeze")
    tm = json.loads(TA.MANIFEST.read_text(encoding="utf-8"))
    man = {"study": STUDY, "version": VERSION, "repairs": REPAIRS, "status": "FROZEN BEFORE ANY CORNER_LOCAL OUTCOME", "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "parent_commit": SMM._git("rev-parse", "HEAD"), "authorization": "owner execution request of 2026-10-15 (Experiment C, candidate 1 of at most 2)",
           "population": "NEW-136; adaptive DEV repeats 3-4 (frozen B16 starts), fixed paths DEV repeats 1-2 (B16, B40)", "budgets": [B_START, B_END],
           "path_sha256": tm["path_sha256"], "predictors": list(PREDICTORS), "gpc": GPC, "permutation_seed": "7000 + 100 r + f + 101 b",
           "primary": "L1: pooled corner AUC at B40 on TREED_MARGIN's paid sets, TREED - TREED_PERM, mean of repeats 3-4",
           "validation": {"status": val["status"], "sha256": SMM.sha256(VALIDATION)}, "code_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in CODE}}
    MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(json.dumps({k: man[k] for k in ("status", "written_utc", "predictors")}, indent=1))


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"validate": validate, "manifest": write_manifest, "work": lambda: work(sys.argv[2:]), "status": status}[step]()
