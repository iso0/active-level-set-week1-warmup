"""Joint depth-label study — Stage M (model value on identical feature-only paths), three populations.

DEV repeats 1-2, five folds, budgets B16 and B40, six arms per checkpoint (360 fit requests):
  J               joint model (src.jdl_model, STAGE_M_CONFIG)
  J_fixed_theta   theta fixed at its prior mean (threshold_sd = 0)
  J_no_delta      discrepancy amplitude 0
  Binary_matched  continuous likelihood removed; identical priors, centering and probit link
  ACTIVE_E1       frozen Week 18 E1 (GPR on log A, paid-only ML-II, learned threshold) via src.week19_dev_pilot.fit_one
  G3              frozen Week 18 G3 (binary GPC, paid-only ML-II) via src.week19_dev_pilot.fit_one
Paths are feature-only maximin orders (src.week13_synthetic_al.maximin_order, rng = task seed + [2]); NEW reproduces
the saved Week 19 paths exactly.  Separate objects: Oracle (all outcomes), PaidTable (what a learner receives),
Evaluator (held-out labels, q20, short-K).  The learner never receives an unpaid or held-out outcome.

Steps: python -m src.jdl_stage_m paths | manifest | run | evaluate
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "2")

import datetime as dt
import gzip
import hashlib
import json
import platform
import subprocess
import sys
import time
import warnings
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import ndtr

import src.jdl_model as JM

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "joint_depth_label_development"
SM = OUT / "stage_m"
CACHE = OUT / "_cache" / "stage_m"
PILOT = ROOT / "outputs" / "week19_temporal_regime_dev_pilot"
ASTRA = ROOT / "outputs" / "astra_week20_method_development"
BASELINE_COMMIT = "e2bcf97a55736cdd2933b6761678d8b695358205"
POPS = {"NEW": "R3_NEW", "OLD": "R3_OLD", "POOLED": "R1_POOLED"}
REPEATS = (1, 2)
BUDGETS = (16, 40)
PATH_LEN = 80
ARMS = ("J", "J_fixed_theta", "J_no_delta", "Binary_matched", "ACTIVE_E1", "G3")
J_ARMS = ARMS[:4]
Z_REF_UM = 111.0
FAST_VX = 0.85
VARIANTS = {"J": ({}, True), "J_fixed_theta": ({"threshold_sd": 0.0}, True), "J_no_delta": ({"discrepancy_amplitude": 0.0}, True),
            "Binary_matched": ({}, False)}
CAPS = {"fit_requests": 360, "cpu_threads": 4, "max_memory_gib": 8}


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def _git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, cwd=ROOT).stdout.strip()


def peak_memory_bytes():
    from src.week19_dev_pilot import peak_memory_bytes as pm
    return pm()


# ======================================================================================== data contract
def inputs_table():
    inp = pd.read_csv(PILOT / "tables/pilot_inputs.csv").set_index("sim_id")
    return inp


def shortk(inp):
    from src.week19_dev_pilot import shortk_ids
    return set(shortk_ids(inp.reset_index()))


def build_tasks():
    """The 30 task-folds (three populations x repeats 1-2 x five folds) with full IDs, A and evaluator-only fields."""
    import src.week18_tasks as T
    inp = inputs_table()
    new, old = T.new_old_frames()
    ids_of = {"R3_NEW": new.sim_id.astype(str).to_numpy(), "R3_OLD": old.sim_id.astype(str).to_numpy(), "R1_POOLED": T.pooled_frame().sim_id.astype(str).to_numpy()}
    pop_of = {v: k for k, v in POPS.items()}
    out = []
    for t in T.all_real_full_depth("DEV"):
        if t["task"] not in pop_of or t["repeat"] not in REPEATS:
            continue
        ids = ids_of[t["task"]]
        if len(ids) != len(t["y"]):
            raise ValueError("id order mismatch")
        A = pd.Series(ids).map(inp.A_um).to_numpy(float)
        y_chk = pd.Series(ids).map(inp.has_keyhole).to_numpy(int)
        if not (y_chk == t["y"]).all():
            raise ValueError("labels differ from pilot_inputs")
        out.append({"population": pop_of[t["task"]], "task": t["task"], "repeat": t["repeat"], "fold": t["fold"], "seed": list(t["seed"]),
                    "X": t["X"], "y": t["y"], "ids": ids, "pool": np.asarray(t["pool"]), "test": np.asarray(t["test"]), "q20": np.asarray(t["q20"], bool),
                    "prior": np.asarray(t["prior"], int), "A": A, "whole": t["depth"],
                    "VX": pd.Series(ids).map(inp.VX_m_s).to_numpy(float), "early_end": pd.Series(ids).map(inp.early_end).to_numpy(bool)})
    return sorted(out, key=lambda t: (list(POPS).index(t["population"]), t["repeat"], t["fold"]))


def make_paths(tasks):
    from src.week13_synthetic_al import maximin_order
    rows = []
    for t in tasks:
        order = maximin_order(t["X"][t["pool"]], np.random.default_rng(list(t["seed"]) + [2]))
        t["path"] = t["pool"][order][:PATH_LEN]
        sids = t["ids"][t["path"]].tolist()
        psha = hashlib.sha256("\n".join(sids).encode()).hexdigest()
        for q, s in enumerate(sids, 1):
            rows.append({"population": t["population"], "repeat": t["repeat"], "fold": t["fold"], "query_index": q, "sim_id": s,
                         "path_seed": json.dumps(list(t["seed"]) + [2]), "path_sha256": psha})
    return pd.DataFrame(rows)


def verify_new_paths(paths):
    pp = pd.read_csv(PILOT / "tables/paid_paths.csv")
    rows = []
    for (r, f), g in pp.groupby(["repeat", "fold"]):
        mine = paths[(paths.population == "NEW") & (paths.repeat == r) & (paths.fold == f)].sort_values("query_index").sim_id.tolist()
        rows.append({"repeat": r, "fold": f, "identical_to_week19_saved_path": mine == g.sort_values("query_index").sim_id.tolist()})
    return pd.DataFrame(rows)


# ======================================================================================== information objects
@dataclass(frozen=True)
class PaidTable:
    """Everything a learner may receive for one checkpoint: paid inputs, canonical labels and available responses."""
    ids: tuple
    X: np.ndarray
    y: np.ndarray
    z: np.ndarray            # log(A/111) or NaN (missing response; label and cost kept)


class Oracle:
    """Holds every outcome; hands out only the outcomes of the rows it is asked to reveal (the paid rows)."""

    def __init__(self, task):
        self._X, self._y, self._A, self._ids = task["X"], task["y"], task["A"], task["ids"]

    def reveal(self, rows):
        rows = np.asarray(rows, int)
        A = self._A[rows]
        ok = np.isfinite(A) & (A > 0)
        z = np.full(len(rows), np.nan); z[ok] = np.log(A[ok] / Z_REF_UM)
        return PaidTable(tuple(self._ids[rows]), self._X[rows].copy(), self._y[rows].astype(int).copy(), z)


def standardizer(task):
    lx = np.log(task["X"][task["pool"]])
    mu, sd = lx.mean(0), lx.std(0)
    return lambda X: (np.log(X) - mu) / sd, {"mean": mu.tolist(), "sd": sd.tolist()}


# ======================================================================================== fits
def fit_joint(task, arm, b):
    std, sc = standardizer(task)
    L = task["path"][:b]
    paid = Oracle(task).reveal(L)
    kw, use_resp = VARIANTS[arm]
    cfg = replace(JM.STAGE_M_CONFIG, **kw)
    x_ref = std(task["X"][task["pool"]])
    rec = {"population": task["population"], "repeat": task["repeat"], "fold": task["fold"], "budget": b, "arm": arm, "n_paid": len(L),
           "n_pos": int(paid.y.sum()), "n_neg": int((paid.y == 0).sum()), "n_response": int(np.isfinite(paid.z).sum()) if use_resp else 0,
           "missing_response_ids": ";".join(np.array(paid.ids)[~np.isfinite(paid.z)]), "prefix_sha256": hashlib.sha256("\n".join(paid.ids).encode()).hexdigest(),
           "config": json.dumps({k: (list(v) if isinstance(v, tuple) else v) for k, v in asdict(cfg).items()}), "use_response": use_resp, "scaler": json.dumps(sc)}
    t0 = time.time()
    try:
        m = JM.JointDepthLabelGP(x_ref, cfg).fit(std(paid.X), paid.y, paid.z, use_response=use_resp)
        d = m.diagnostics
        rec.update({"status": "ok", "solver_status": d["solver_status"], "gradient_inf": d["gradient_inf"], "gradient_accepted": d["gradient_accepted"],
                    "newton_iterations": d["newton_iterations"], "min_whitened_hessian_eigenvalue": d.get("min_whitened_hessian_eigenvalue", np.nan),
                    "condition_number_K": d.get("condition_number_K", np.nan), "mode_objective": d.get("objective", np.nan)})
    except Exception as e:                              # recorded, not repaired
        rec.update({"status": "failed", "error": f"{type(e).__name__}: {e}"[:300]})
        return rec, []
    Xt = std(task["X"][task["test"]])
    q = m.marginals(Xt)
    pc, cht = m.predict_proba_theta_conditioned(Xt)
    tau2 = cfg.probit_scale ** 2
    c_hf = q["f_var"] - q["f_theta_cov"] + q["f_delta_cov"]                      # Cov(h, f) at the same input
    At = task["A"][task["test"]]
    zt = np.where(np.isfinite(At) & (At > 0), np.log(np.where(np.isfinite(At) & (At > 0), At, 1.0) / Z_REF_UM), np.nan)
    vz = q["f_var"] + cfg.response_noise_sd ** 2
    m_or = q["h_mean"] + c_hf * (zt - q["f_mean"]) / vz
    v_or = np.maximum(q["h_var"] - c_hf ** 2 / vz, 0.0)
    p_or = ndtr(m_or / np.sqrt(tau2 + v_or))                                      # ORACLE: uses the held-out response (not deployable)
    rec.update({"theta_mean": q["theta_mean"], "theta_sd": float(np.sqrt(q["theta_var"])), "wall_seconds": time.time() - t0})
    preds = []
    for j, i in enumerate(task["test"]):
        preds.append({"population": task["population"], "repeat": task["repeat"], "fold": task["fold"], "budget": b, "arm": arm, "sim_id": task["ids"][i],
                      "p": float(q["p"][j]), "h_mean": float(q["h_mean"][j]), "h_var": float(q["h_var"][j]), "margin": float(q["h_mean"][j] / np.sqrt(tau2 + q["h_var"][j])),
                      "f_mean": float(q["f_mean"][j]), "f_var": float(q["f_var"][j]), "delta_mean": float(q["delta_mean"][j]), "delta_var": float(q["delta_var"][j]),
                      "theta_mean": q["theta_mean"], "theta_var": q["theta_var"], "f_theta_cov": float(q["f_theta_cov"][j]), "f_delta_cov": float(q["f_delta_cov"][j]),
                      "delta_theta_cov": float(q["delta_theta_cov"][j]), "h_theta_cov": float(cht[j]), "p_theta_conditioned": float(pc[j]),
                      "p_oracle_response_NOT_DEPLOYABLE": float(p_or[j]) if np.isfinite(p_or[j]) and use_resp else np.nan,
                      "prediction_status": "ok"})
    return rec, preds


def fit_baseline(task, arm, b, E, n_fits):
    import src.week19_dev_pilot as W
    t = {"X": task["X"], "y": task["y"], "ids": task["ids"], "pool": task["pool"], "test": task["test"], "prior": task["prior"], "path": task["path"],
         "whole": task["whole"], "A": task["A"], "repeat": task["repeat"], "fold": task["fold"]}
    name = "ACTIVE_E1_SHARED" if arm == "ACTIVE_E1" else "G3_SHARED"
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=2):
        rec, preds, orc, leak_ok = W.fit_one(E, t, name, b, task["path"][:b], n_fits)
    rec = {**{k: v for k, v in rec.items() if k not in ("arm",)}, "population": task["population"], "arm": arm, "frozen_arm_name": name, "leakage_guard_ok": bool(leak_ok)}
    out = []
    for p in preds:
        if p["threshold_mode"] != "learned":
            continue
        out.append({"population": task["population"], "repeat": task["repeat"], "fold": task["fold"], "budget": b, "arm": arm, "sim_id": p["sim_id"],
                    "p": p["p_keyhole"], "latent_mean": p["latent_mean"], "latent_var": p["latent_variance"], "prediction_status": p["prediction_status"]})
    oracle = [{"population": task["population"], **{k: o[k] for k in ("repeat", "fold", "budget", "sim_id", "observed_score", "training_threshold", "predicted_label", "status")},
               "arm": arm} for o in orc]
    return rec, out, oracle


def cache_file(task, b, arm):
    return CACHE / f"{task['population']}__r{task['repeat']}_f{task['fold']}__B{b}__{arm}.json.gz"


def run():
    import src.week18_engine as E
    if not (OUT / "STUDY_MANIFEST.json").exists():
        raise SystemExit("commit the study manifest before any comparative fit")
    man = json.loads((OUT / "STUDY_MANIFEST.json").read_text(encoding="utf-8"))
    tasks = build_tasks()
    paths = pd.read_csv(SM / "paths.csv")
    for t in tasks:
        g = paths[(paths.population == t["population"]) & (paths.repeat == t["repeat"]) & (paths.fold == t["fold"])].sort_values("query_index")
        pos = {s: i for i, s in enumerate(t["ids"])}
        t["path"] = g.sim_id.map(pos).to_numpy(int)
        if hashlib.sha256("\n".join(g.sim_id).encode()).hexdigest() != man["paths"]["sha256_by_task"][f"{t['population']}_r{t['repeat']}_f{t['fold']}"]:
            raise SystemExit("path differs from the frozen manifest")
    CACHE.mkdir(parents=True, exist_ok=True)
    n_req, t0 = 0, time.time()
    log = []
    for t in tasks:
        for b in BUDGETS:
            for arm in ARMS:
                cf = cache_file(t, b, arm)
                n_req += 1
                if cf.exists():
                    continue
                if n_req > CAPS["fit_requests"]:
                    raise SystemExit("fit-request cap")
                if arm in J_ARMS:
                    rec, preds = fit_joint(t, arm, b); orc = []
                else:
                    rec, preds, orc = fit_baseline(t, arm, b, E, n_req)
                rec.update({"fit_request": n_req, "peak_memory_bytes": peak_memory_bytes()})
                cf.write_bytes(gzip.compress(json.dumps({"fit": rec, "predictions": preds, "oracle": orc}, default=float).encode()))
                log.append({k: rec.get(k) for k in ("population", "repeat", "fold", "budget", "arm", "status", "solver_status", "gradient_inf")})
                print(f"{t['population']:6s} r{t['repeat']} f{t['fold']} B{b:2d} {arm:15s} {rec['status']:28s} {rec.get('solver_status', '')}", flush=True)
    import scipy
    import sklearn
    prov = {"finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "fit_requests": n_req, "new_fits_this_session": len(log),
            "elapsed_s": time.time() - t0, "peak_memory_bytes": peak_memory_bytes(), "python": platform.python_version(), "numpy": np.__version__,
            "scipy": scipy.__version__, "sklearn": sklearn.__version__, "pandas": pd.__version__,
            "threads": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}, "baseline_threadpool_limit": 2}
    (OUT / "provenance").mkdir(parents=True, exist_ok=True)
    with open(OUT / "provenance" / "stage_m_run_log.jsonl", "a") as fh:
        fh.write(json.dumps(prov) + "\n")
    print(json.dumps(prov, indent=1))


def load_cache():
    fits, preds, orc = [], [], []
    for f in sorted(CACHE.glob("*.json.gz")):
        r = json.loads(gzip.decompress(f.read_bytes()))
        fits.append(r["fit"]); preds += r["predictions"]; orc += r["oracle"]
    return pd.DataFrame(fits), pd.DataFrame(preds), pd.DataFrame(orc)


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "paths"
    if step == "paths":
        from src.jdl_freeze import write_paths
        write_paths()
    elif step == "manifest":
        from src.jdl_freeze import write_manifest
        write_manifest()
    elif step == "run":
        run()
    elif step == "evaluate":
        from src.jdl_evaluate import main
        main()
