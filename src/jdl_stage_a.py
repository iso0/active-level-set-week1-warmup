"""Stage A runner — acquisition value with the model held fixed (PREPARED AND VALIDATED; NOT EXECUTED).

Protocol (STAGE_A_PROTOCOL_DRAFT.md): NEW, DEV repeats 3-4, five folds; identical feature-only B16 startup
(maximin prefix, task seed + [2]); sequential queries B17-B40; refit from the prior with every paid factor at every
budget.  Arms: J_PV (J + paired probability-variance acquisition), J_MARGIN (J + argmin |p - 0.5|), and the system
controls G3_MARGIN and ACTIVE_E1_STRADDLE (frozen implementations) when their fit contracts permit the startup.
Both J arms receive the paid canonical label AND the available response of every query (paired information).

Numerical rule for J_PV (Astra): score with 15 and 31 Gauss-Hermite nodes (the bivariate CDF is Genz BVNU, exact to
about 1e-15, so the CDF-order pairs 48/64/96 reduce to the GH orders); e = max |s31 - s15|; rank by s31; accept the
top candidate if its gap to the runner-up exceeds 2e + the omitted-tail bound; otherwise compare 31 vs 63, rank by 63
and apply the same test; if still unresolved, a numerical tie (every relevant difference and gap <= 1e-8) is broken
by the fixed simulation-ID order, else the trajectory records a numerical STOP.  No fallback to margin.

Steps: python -m src.jdl_stage_a validate        (synthetic + plumbing; no DEV 3-4 label is revealed)
       python -m src.jdl_stage_a run --owner-authorized   (refuses unless an owner decision and a committed
                                                           outputs/joint_depth_label_development/stage_a/STAGE_A_MANIFEST.json exist)
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import gzip
import hashlib
import json
import sys
import time
from dataclasses import replace

import numpy as np
import pandas as pd

import src.jdl_model as JM

TIE_TOL = 1e-8
GH_ORDERS = (15, 31, 63)


# ======================================================================================== selection rules
def select_pv(model, X_cand, cand_ids, X_int, log):
    """Paired probability-variance acquisition with the quadrature acceptance rule.  Returns (index | None, record)."""
    order = np.argsort(np.asarray(cand_ids, dtype=str), kind="stable")             # fixed simulation-ID order for ties
    s = {}
    for g in GH_ORDERS[:2]:
        s[g] = model.acquisition(X_cand, X_int, gh_order=g)
    rec = {"rule": "paired_probability_variance", "n_candidates": len(cand_ids)}
    for lo, hi in ((15, 31), (31, 63)):
        if hi not in s:
            s[hi] = model.acquisition(X_cand, X_int, gh_order=hi)
        e = float(np.max(np.abs(s[hi]["score"] - s[lo]["score"])))
        sc = s[hi]["score"]; rank = np.argsort(-sc, kind="stable")
        top, run = int(rank[0]), int(rank[1]) if len(rank) > 1 else None
        gap = float(sc[top] - sc[run]) if run is not None else np.inf
        bound = float(np.max(s[hi]["omitted_label_term_upper_bound"]))
        rec.update({f"e_{lo}_{hi}": e, f"gap_{hi}": gap, f"tail_bound_{hi}": bound, f"top_{hi}": cand_ids[top]})
        if gap > 2 * e + bound:
            rec.update({"decision": f"accepted at {hi} nodes", "selected": cand_ids[top]})
            _log_scores(log, cand_ids, s, rec)
            return top, rec
    sc = s[63]["score"]; best = sc.max()
    tied = np.flatnonzero(best - sc <= TIE_TOL)
    if rec["e_31_63"] <= TIE_TOL and len(tied) > 1:
        pick = next(i for i in order if i in set(tied.tolist()))
        rec.update({"decision": "numerical tie broken by fixed simulation-ID order", "selected": cand_ids[pick], "tied": [cand_ids[i] for i in tied]})
        _log_scores(log, cand_ids, s, rec)
        return int(pick), rec
    rec.update({"decision": "NUMERICAL STOP (ranking unresolved at 63 nodes)", "selected": None})
    _log_scores(log, cand_ids, s, rec)
    return None, rec


def _log_scores(log, cand_ids, s, rec):
    for g, a in s.items():
        for i, cid in enumerate(cand_ids):
            log.append({"gh_order": g, "candidate": cid, "score": float(a["score"][i]), "response_component": float(a["response_component"][i]),
                        "label_component": float(a["label_component"][i]), "omitted_bound": float(a["omitted_label_term_upper_bound"][i])})


def select_margin(model, X_cand, cand_ids, log):
    p = model.predict_proba(X_cand); m = np.abs(p - 0.5)
    order = np.lexsort((np.asarray(cand_ids, dtype=str), m))
    for i, cid in enumerate(cand_ids):
        log.append({"candidate": cid, "p": float(p[i]), "margin": float(m[i])})
    return int(order[0]), {"rule": "probability_margin", "selected": cand_ids[int(order[0])], "decision": "argmin |p - 0.5| (ties by simulation ID)"}


# ======================================================================================== one J trajectory
def run_j(task, arm, b_start=16, b_end=40, config=None, oracle_cls=None, std_fn=None):
    """task: X, y, A, ids, pool, test, path (feature-only order).  The oracle reveals paired (Y, A) only when paid."""
    from src.jdl_stage_m import Oracle, standardizer
    cfg = config or JM.STAGE_M_CONFIG
    oracle = (oracle_cls or Oracle)(task)
    std = std_fn or standardizer(task)[0]
    x_ref = std(task["X"][task["pool"]])
    paid = list(task["path"][:b_start])
    steps, scores, evals = [], [], []
    status = "ok"
    for b in range(b_start, b_end + 1):
        pt = oracle.reveal(paid)                                                     # paired outcomes of paid rows only
        try:
            m = JM.JointDepthLabelGP(x_ref, cfg).fit(std(pt.X), pt.y, pt.z)
        except Exception as e:                                                      # recorded, not repaired
            status = f"fit_failed: {type(e).__name__}: {e}"[:200]; break
        q = m.marginals(std(task["X"][task["test"]]))
        evals.append({"budget": b, "p": q["p"].tolist()})
        state = {"budget": b, "n_paid": len(paid), "n_pos": int(pt.y.sum()), "n_neg": int((pt.y == 0).sum()), "n_response": int(np.isfinite(pt.z).sum()),
                 "theta_mean": q["theta_mean"], "theta_sd": float(np.sqrt(q["theta_var"])), "solver_status": m.diagnostics["solver_status"],
                 "gradient_inf": m.diagnostics["gradient_inf"], "integrated_probability_variance": float(np.mean(m.integrated_probability_variance(x_ref)))}
        if b == b_end:
            steps.append(state); break
        cand = np.setdiff1d(task["pool"], paid)
        cand_ids = [str(task["ids"][i]) for i in cand]
        log = []
        if arm == "J_PV":
            j, rec = select_pv(m, std(task["X"][cand]), cand_ids, x_ref, log)
        else:
            j, rec = select_margin(m, std(task["X"][cand]), cand_ids, log)
        state.update(rec); steps.append(state)
        scores.append({"budget": b, "scores": log})
        if j is None:
            status = "numerical_stop"; break
        paid.append(int(cand[j]))
    return {"arm": arm, "status": status, "paid_ids": [str(task["ids"][i]) for i in paid], "steps": steps, "scores": scores, "evals": evals}


def first_divergence(a, b):
    for i, (x, y) in enumerate(zip(a, b), 1):
        if x != y:
            return i
    return None


# ======================================================================================== validation (no DEV 3-4 label revealed)
def validate():
    from src.jdl_stage_m import PaidTable
    out = {}
    g = np.random.default_rng(17)
    n_pool, n_test = 50, 20
    Xr = np.exp(g.normal(0, 0.3, (n_pool + n_test, 4)))                               # positive raw inputs (log-standardised inside)
    z = 0.6 * np.log(Xr[:, 0]) / 0.3 - 0.2
    A = 111.0 * np.exp(z + 0.03 * g.standard_normal(len(Xr)))
    y = ((z + 0.25 * np.sin(3 * np.log(Xr[:, 1]))) > 0).astype(int)
    A[7] = np.nan                                                                     # a missing response in the pool
    ids = np.array([f"SIM-{i:03d}" for i in range(len(Xr))])
    pool, test = np.arange(n_pool), np.arange(n_pool, n_pool + n_test)
    path = pool[g.permutation(n_pool)]
    if 7 not in path[:16]:
        path = np.r_[path[path != 7][:10], 7, path[path != 7][10:]]                    # make the missing response part of the startup
    task = {"X": Xr, "y": y, "A": A, "ids": ids, "pool": pool, "test": test, "path": path}
    std = lambda X: (np.log(X) - np.log(Xr[pool]).mean(0)) / np.log(Xr[pool]).std(0)
    t0 = time.time()
    pv = run_j(task, "J_PV", 16, 21, std_fn=std); mg = run_j(task, "J_MARGIN", 16, 21, std_fn=std)
    out["runs"] = {"J_PV": pv["status"], "J_MARGIN": mg["status"], "seconds": time.time() - t0}
    out["paired_information"] = all(s["n_response"] == s["n_paid"] - 1 for s in pv["steps"])          # the one missing A is never counted as a response
    out["missing_response_keeps_label_and_cost"] = pv["steps"][0]["n_paid"] == 16 and pv["steps"][0]["n_pos"] + pv["steps"][0]["n_neg"] == 16
    out["first_divergent_query"] = first_divergence(pv["paid_ids"], mg["paid_ids"])
    out["decisions"] = [s.get("decision") for s in pv["steps"] if "decision" in s]
    # leakage: corrupt every unpaid and test outcome -> identical scores and selections
    y2, A2 = y.copy(), A.copy()
    hidden = np.setdiff1d(np.arange(len(y)), path[:16])
    y2[hidden] = 1 - y2[hidden]; A2[hidden] = 5000.0
    task2 = {**task, "y": y2, "A": A2}
    pv2 = run_j(task2, "J_PV", 16, 17, std_fn=std)
    s1 = [r["score"] for r in pv["scores"][0]["scores"]]; s2 = [r["score"] for r in pv2["scores"][0]["scores"]]
    out["leakage_first_selection_identical"] = pv["paid_ids"][16] == pv2["paid_ids"][16] and np.allclose(s1, s2, rtol=0, atol=0)
    # numerical rule: duplicated candidate inputs produce an exact tie -> fixed-ID tie rule, never margin
    m = JM.JointDepthLabelGP(std(Xr[pool]), JM.STAGE_M_CONFIG).fit(std(Xr[path[:16]]), y[path[:16]], np.log(np.where(np.isfinite(A[path[:16]]), A[path[:16]], np.nan) / 111.0))
    Xd = np.vstack([Xr[[40, 40, 41]]]); idd = ["SIM-B", "SIM-A", "SIM-C"]
    log = []
    j, rec = select_pv(m, std(Xd), idd, std(Xr[pool]), log)
    out["tie_rule"] = {"decision": rec["decision"], "selected": rec["selected"]}
    out["tie_rule_ok"] = rec["selected"] in ("SIM-A", "SIM-C") and ("tie" in rec["decision"] or "accepted" in rec["decision"])
    out["score_log_complete"] = all(len(sc["scores"]) >= 2 * len(np.setdiff1d(pool, path[:16 + k])) for k, sc in enumerate(pv["scores"]))
    ctl = {a: run_control(task, a, 16, 18) for a in ("G3_MARGIN", "ACTIVE_E1_STRADDLE")}
    out["controls"] = {a: r["status"] for a, r in ctl.items()}
    out["passed"] = bool(out["runs"]["J_PV"] == "ok" and out["runs"]["J_MARGIN"] == "ok" and out["paired_information"] and out["missing_response_keeps_label_and_cost"]
                         and out["leakage_first_selection_identical"] and out["tie_rule_ok"] and out["score_log_complete"]
                         and all(s == "ok" or s.startswith("not permitted") for s in out["controls"].values()))
    # plumbing on the real Stage A tasks: build NEW DEV repeats 3-4 and their feature-only paths (no label is revealed)
    import src.jdl_stage_m as SMM
    old = SMM.REPEATS; SMM.REPEATS = (3, 4)
    try:
        tasks = [t for t in SMM.build_tasks() if t["population"] == "NEW"]
    finally:
        SMM.REPEATS = old
    paths = SMM.make_paths(tasks)
    out["stage_a_plumbing"] = {"task_folds": len(tasks), "paths_built": int(paths.groupby(["repeat", "fold"]).ngroups),
                               "path_sha256": {f"r{r}_f{f}": hashlib.sha256("\n".join(g_.sort_values("query_index").sim_id).encode()).hexdigest()
                                               for (r, f), g_ in paths.groupby(["repeat", "fold"])},
                               "labels_revealed": 0}
    from src.jdl_stage_m import OUT
    d = OUT / "stage_a"; d.mkdir(parents=True, exist_ok=True)
    paths.to_csv(d / "stage_a_paths_NEW_r3_r4.csv", index=False, lineterminator="\n")
    (d / "stage_a_runner_validation.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "stage_a_plumbing"}, indent=1, default=str))
    return out


def run_control(task, arm, b_start=16, b_end=40):
    """Frozen G3 + margin or ACTIVE E1 + straddle from the SAME feature-only B16 prefix (no label-driven extension).
    If the prefix does not satisfy the learner's fit contract (one class; no usable negative response) the trajectory
    is recorded as not permitted - never extended, reseeded or silently dropped."""
    import warnings
    import src.week18_engine as E
    X, y, ids, pool = task["X"], task["y"], task["ids"], task["pool"]
    resp = task["A"] if arm == "ACTIVE_E1_STRADDLE" else None
    learner = ("GPR_depth", "mlii") if resp is not None else ("G3", "mlii")
    L = list(task["path"][:b_start]); steps, evals = [], []
    for b in range(b_start, b_end + 1):
        Lr = np.asarray(L)
        ok = np.isfinite(resp[Lr]) if resp is not None else np.ones(len(Lr), bool)
        if len(set(y[Lr][ok].tolist())) < 2:
            return {"arm": arm, "status": f"not permitted at B{b}: single-class usable paid data", "paid_ids": [str(ids[i]) for i in L], "steps": steps, "evals": evals}
        y_m = np.full(len(y), -1, int); y_m[Lr] = y[Lr]
        d_m = np.full(len(y), np.nan)
        if resp is not None:
            d_m[Lr] = resp[Lr]
        mt = {"X": X, "y": y_m, "pool": pool, "prior": np.array([], int), "depth": d_m}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                f = E.fit_learner(learner, mt, L, None, {"kernel": None, "b0": len(L)})
            except Exception as e:
                return {"arm": arm, "status": f"fit_failed at B{b}: {type(e).__name__}", "paid_ids": [str(ids[i]) for i in L], "steps": steps, "evals": evals}
        evals.append({"budget": b, "p": np.asarray(E.proba(f, X[task["test"]]), float).tolist()})
        steps.append({"budget": b, "n_paid": len(L), "u_um": float(np.exp(f.u)) if hasattr(f, "u") else None})
        if b == b_end:
            break
        cands = np.setdiff1d(pool, Lr)
        if resp is not None:
            m_c, v_c = E.latent(f, X[cands]); sc = 1.96 * np.sqrt(v_c) - np.abs(m_c); j = int(np.argmax(sc))
        else:
            sc = np.abs(E.proba(f, X[cands]) - 0.5); j = int(np.argmin(sc))
        L.append(int(cands[j]))
    return {"arm": arm, "status": "ok", "paid_ids": [str(ids[i]) for i in L], "steps": steps, "evals": evals}


def run(argv):
    """Executes the frozen Stage A protocol ONLY with explicit owner authorisation and a committed manifest."""
    import src.jdl_stage_m as SMM
    d = SMM.OUT / "stage_a"
    man = d / "STAGE_A_MANIFEST.json"
    if "--owner-authorized" not in argv or not man.exists() or not SMM._git("log", "--format=%H", "--", str(man.relative_to(SMM.ROOT)).replace("\\", "/")):
        raise SystemExit("Stage A is prepared but NOT authorized: it needs an owner decision and a committed STAGE_A_MANIFEST.json")
    old = SMM.REPEATS; SMM.REPEATS = (3, 4)
    try:
        tasks = [t for t in SMM.build_tasks() if t["population"] == "NEW"]
    finally:
        SMM.REPEATS = old
    paths = pd.read_csv(d / "stage_a_paths_NEW_r3_r4.csv")
    cache = SMM.OUT / "_cache" / "stage_a"; cache.mkdir(parents=True, exist_ok=True)
    for t in tasks:
        g = paths[(paths.repeat == t["repeat"]) & (paths.fold == t["fold"])].sort_values("query_index")
        pos = {s: i for i, s in enumerate(t["ids"])}; t["path"] = g.sim_id.map(pos).to_numpy(int)
        for arm in ("J_PV", "J_MARGIN", "G3_MARGIN", "ACTIVE_E1_STRADDLE"):
            cf = cache / f"NEW__r{t['repeat']}_f{t['fold']}__{arm}.json.gz"
            if cf.exists():
                continue
            res = run_j(t, arm) if arm.startswith("J_") else run_control(t, arm)
            res.update({"repeat": t["repeat"], "fold": t["fold"], "test_ids": [str(t["ids"][i]) for i in t["test"]]})
            cf.write_bytes(gzip.compress(json.dumps(res, default=float).encode()))
            print(t["repeat"], t["fold"], arm, res["status"], flush=True)


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "validate"
    if step == "validate":
        validate()
    elif step == "run":
        run(sys.argv[2:])
