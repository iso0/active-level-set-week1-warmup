"""PHYS_AUX (pilot B follow-up; owner request of 2026-10-16, item 2.3-2.4: show whether x-predicted physics actually helps).

Mechanism.  Pilot B: the steady melt KE (KE_T0) and the velocity spike size are learnable from x (R2_oof 0.74 / 0.87) and their
OUT-OF-FOLD predictions rank corner Keyhole above chance (AUC 0.77 / 0.67) when all pool runs are revealed.  A paid simulation
reveals its monitors with its label at no extra simulation cost; a continuous physical response may then teach the
classifier a better representation of x than binary labels alone.
Candidate PHYS_AUX: at each budget, GP regressions (Matern 3/2 ARD + white nugget, normalize_y, no restarts) of log KE_T0 and
of the velocity spike log-ratio are fitted on the PAID runs only (QC-unavailable values skipped and logged).  Features for the
classifier: the 4 standardised log inputs + the 2 auxiliary predictions, z-scored.  Paid runs use their leave-one-out GP
predictive means (closed form, same hyperparameters), unpaid and test runs the full-fit means: training and test features are
both predictions, never the true monitor value.  Classifier: GaussianProcessClassifier (C * RBF ARD, no restarts).  Acquisition:
margin |p - 0.5|, ties by simulation ID.  New or test runs' monitors are never read.
Decisive control GPC_X: the same classifier and acquisition on the 4 inputs only (isolates the auxiliary effect).
References (pilot A cache, same starts / budget / one-class rule): G3_MARGIN, E1_STRADDLE.
Design: NEW DEV repeats 3-4, frozen feature-only B16 starts, B16-B40, one-class rule of pilot A (frozen-path continuation).
Endpoints (fixed): BA-AULC B16-B40 (pooled per repeat, trapezoid), B40 BA, both recalls, q20, short-K caught/total, AUC, Brier,
corner AUC (evaluator-only).  Verdict PHYS_AUX - GPC_X and PHYS_AUX - G3_MARGIN / E1_STRADDLE: "PRACTICALLY BETTER" iff BA-AULC
>= +0.04 with the 95 % class-stratified cluster-bootstrap interval > 0, both repeats positive, short-K caught at B40 >= 7/10 per
repeat (absolute) and not more than 2 of 20 below the comparator; a BA gain failing only short-K = TRADE-OFF; else NO PRACTICAL
DIFFERENCE.  Savings: only with sustained target attainment (BA >= 0.75, short-K >= 0.70, q20 >= 0.70) before the reference.
Steps: python -m src.jdl_phys_aux validate | manifest | work | evaluate
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import datetime as dt
import gzip
import json
import sys
import time
import traceback
import warnings

import numpy as np
import pandas as pd

import src.jdl_stage_m as SMM
import src.jdl_surprise as SD
import src.jdl_trained_al as TA

STUDY = "PHYS_AUX"
OUT = SMM.OUT / "phys_aux"
CACHE = SMM.OUT / "_cache" / "phys_aux"
MANIFEST = OUT / "PHYS_AUX_MANIFEST.json"
VALIDATION = OUT / "PHYS_AUX_VALIDATION.json"
SUMM = SMM.OUT / "physical" / "physical_summaries.csv"
AUX = ("ke_T0_med_nJ", "vmax_spike_logratio")
ARMS = ("PHYS_AUX", "GPC_X")
REPEATS, FOLDS, B_START, B_END = (3, 4), (1, 2, 3, 4, 5), 16, 40
UNIT_TIME_LIMIT_S = 1800
CODE = ("src/jdl_phys_aux.py", "src/jdl_surprise.py", "src/jdl_trained_al.py", "src/jdl_stage_m.py", "src/jdl_evaluate.py", "src/jdl_trained_al_eval.py",
        "src/jdl_physical_pilot.py")


def aux_table():
    D = pd.read_csv(SUMM).set_index("sim_id")
    T = pd.DataFrame(index=D.index)
    T["ke_T0_med_nJ"] = np.log(D["ke_T0_med_nJ"].where(D["ke_T0_med_nJ"] > 0))
    T["vmax_spike_logratio"] = D["vmax_spike_logratio"]
    return T


def _gpr(Xp, yp):
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return GaussianProcessRegressor(ConstantKernel(1.0, (1e-3, 1e3)) * Matern(np.ones(Xp.shape[1]), (1e-2, 1e2), nu=1.5) + WhiteKernel(0.1, (1e-6, 10.0)),
                                        normalize_y=True, n_restarts_optimizer=0, random_state=0).fit(Xp, yp)


def loo_means(gp, y):
    """Closed-form LOO predictive means of a fitted sklearn GPR (normalize_y) with its fitted hyperparameters (R&W eq. 5.12)."""
    from scipy.linalg import cho_solve
    Kinv = cho_solve((gp.L_, True), np.eye(gp.L_.shape[0]))
    yn = (np.asarray(y, float) - gp._y_train_mean) / gp._y_train_std
    mu_n = yn - (Kinv @ yn) / np.diag(Kinv)
    return mu_n * gp._y_train_std + gp._y_train_mean


def features(Z, paid, others, auxv):
    """Classifier features for paid rows (LOO aux predictions) and other rows (full-fit predictions)."""
    if auxv is None:
        return Z[paid], Z[others], {}
    Fp, Fo, info = [Z[paid]], [Z[others]], {}
    for k, col in enumerate(AUX):
        v = auxv[:, k]; ok = np.isfinite(v[paid])
        idx = np.asarray(paid)[ok]
        if ok.sum() < 5:
            fp, fo = np.zeros(len(paid)), np.zeros(len(others)); info[col] = "too few paid values"
        else:
            gp = _gpr(Z[idx], v[idx]); fo = gp.predict(Z[others]); lo = loo_means(gp, v[idx])
            fp = gp.predict(Z[paid]); fp[ok] = lo                               # paid with a value: LOO; paid without one (QC): full-fit prediction
            info[col] = {"n_train": int(ok.sum()), "kernel": str(gp.kernel_)}
        m, s = fp.mean(), fp.std() + 1e-9
        Fp.append(((fp - m) / s)[:, None]); Fo.append(((fo - m) / s)[:, None])
    return np.hstack(Fp), np.hstack(Fo), info


def _gpc(F, y):
    from sklearn.gaussian_process import GaussianProcessClassifier
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return GaussianProcessClassifier(ConstantKernel(1.0, (0.05, 50)) * RBF(np.ones(F.shape[1]), (0.05, 50)), random_state=0).fit(F, y)


def run_unit(task, arm, auxT, deadline=None):
    X, y, ids, pool, test = task["X"], task["y"], np.asarray(task["ids"]).astype(str), task["pool"], task["test"]
    std = SMM.standardizer(task)[0]; Z = np.zeros((len(X), 4)); Z[pool] = std(X[pool]); Z[test] = std(X[test])
    auxv = auxT.reindex(ids)[list(AUX)].to_numpy(float) if arm == "PHYS_AUX" else None
    L = [int(i) for i in task["path"][:B_START]]; evals, steps = [], []; t0 = time.time(); status = "ok"
    for b in range(B_START, B_END + 1):
        if deadline is not None and time.time() > deadline:
            status = f"TIME_LIMIT at B{b}"; break
        ts = time.time(); unpaid = np.setdiff1d(pool, L); others = np.r_[unpaid, test]
        one_class = len(set(y[L].tolist())) < 2
        if one_class:
            pc = (int(y[L].sum()) + 0.5) / (len(L) + 1); p_other = np.full(len(others), pc); info = {"constant": pc}
        else:
            Fp, Fo, info = features(Z, L, others, auxv)
            clf = _gpc(Fp, y[L]); p_other = clf.predict_proba(Fo)[:, 1]
        p_un, p_te = p_other[:len(unpaid)], p_other[len(unpaid):]
        evals.append({"budget": b, "p": p_te.tolist(), "constant_predictor": bool(one_class)})
        steps.append({"budget": b, "seconds": time.time() - ts, "aux": info if arm == "PHYS_AUX" else None})
        if b == B_END:
            break
        if one_class:
            nxt = int([i for i in task["path"] if i not in set(L)][0]); how = "path_continuation"
        else:
            order = np.lexsort((ids[unpaid], np.abs(p_un - 0.5))); nxt = int(unpaid[order[0]]); how = "margin"
        L.append(nxt); steps[-1].update({"selected": ids[nxt], "how": how})
    return {"repeat": task["repeat"], "fold": task["fold"], "arm": arm, "paid": L, "paid_ids": [ids[i] for i in L], "test_ids": [ids[i] for i in test],
            "evals": evals, "steps": steps, "status": status, "seconds": time.time() - t0}


def units():
    return [((r, f), a) for a in ARMS for r in REPEATS for f in FOLDS]


def unit_name(key, arm):
    return f"NEW__r{key[0]}_f{key[1]}__{arm}"


def work(argv=()):
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not SMM._git("log", "--format=%H", "--", str(MANIFEST.relative_to(SMM.ROOT)).replace("\\", "/")):
        raise SystemExit("commit the PHYS_AUX manifest before any run")
    for c, h in man["code_sha256"].items():
        if SMM.sha256(SMM.ROOT / c) != h:
            raise SystemExit(f"{c} changed after the PHYS_AUX freeze")
    tasks = {(t["repeat"], t["fold"]): t for t in TA.build_tasks()}; auxT = aux_table()
    CACHE.mkdir(parents=True, exist_ok=True); locks = CACHE / "locks"; locks.mkdir(exist_ok=True)
    for key, arm in units():
        name = unit_name(key, arm); out = CACHE / f"{name}.json.gz"
        if out.exists():
            continue
        lock = locks / f"{name}.lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
        try:
            t0 = time.time(); res = run_unit(tasks[key], arm, auxT, deadline=t0 + UNIT_TIME_LIMIT_S)
            res.update({"study": STUDY, "unit": name, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
            TA._atomic_write(out, res); print(json.dumps({"unit": name, "status": res["status"], "s": round(res["seconds"], 1)}), flush=True)
        finally:
            lock.unlink(missing_ok=True)


def evaluate():
    import src.jdl_evaluate as EV
    import src.jdl_trained_al_eval as TE
    R = {}
    for p in sorted(CACHE.glob("NEW__*.json.gz")):
        r = json.loads(gzip.decompress(p.read_bytes())); R[(r["repeat"], r["fold"], r["arm"])] = r
    for a in ("G3_MARGIN", "E1_STRADDLE"):                                       # references from the pilot A cache (same design)
        for rep in REPEATS:
            for f in FOLDS:
                q = SD.CACHE / f"NEW__r{rep}_f{f}__{a}.json.gz"
                if q.exists():
                    r = json.loads(gzip.decompress(q.read_bytes())); R[(rep, f, a)] = r
    _, F = TE.frame(); y, sk = F["y"], F["shortk"]; W = EV.boot_weights(y); corner = np.asarray(F["VX"], float) > SMM.FAST_VX
    pos = {s: i for i, s in enumerate(F["ids"])}; budgets = range(B_START, B_END + 1); M = {}
    arms = ARMS + ("G3_MARGIN", "E1_STRADDLE")
    for a in arms:
        for rep in REPEATS:
            for b in budgets:
                p = np.full(len(F["ids"]), np.nan); okf = 0
                for f in FOLDS:
                    r = R.get((rep, f, a)); e = None if r is None else {x["budget"]: x for x in r["evals"]}.get(b)
                    if e is not None:
                        p[[pos[s] for s in r["test_ids"]]] = e["p"]; okf += 1
                if okf == len(FOLDS) and np.isfinite(p).all():
                    m = EV.wmetrics(p, np.ones(len(p), bool), y, sk, F["q20"][rep], F["fold"][rep], W)
                    c = EV.wmetrics(p, corner, y, sk, F["q20"][rep], F["fold"][rep], W)
                    M[(a, rep, b)] = {**{k: m[k] for k in ("BA", "sensitivity", "specificity", "q20", "shortK_sensitivity", "AUC", "brier")}, "corner_AUC": c["AUC"],
                                      "shortK_caught": int(((p >= .5) & sk).sum()), "shortK_total": int(sk.sum())}
    def aulc(a, rep):
        if not all((a, rep, b) in M for b in budgets):
            return None
        v = np.vstack([M[(a, rep, b)]["BA"] for b in budgets]); return np.trapezoid(v, x=np.array(list(budgets), float), axis=0) / (B_END - B_START)
    res = {"units_done": sum(1 for k in R if k[2] in ARMS), "units_expected": len(units()), "per_arm": {}, "contrasts": {}}
    for a in arms:
        res["per_arm"][a] = {"BA_AULC_per_repeat": [None if aulc(a, rep) is None else float(aulc(a, rep)[0]) for rep in REPEATS],
                             **{f"B40_{k}_per_repeat": [M[(a, rep, 40)][k] if isinstance(M.get((a, rep, 40), {}).get(k), int) else (float(M[(a, rep, 40)][k][0]) if (a, rep, 40) in M else None)
                                                         for rep in REPEATS] for k in ("BA", "sensitivity", "specificity", "q20", "AUC", "brier", "corner_AUC", "shortK_caught")}}
    for cand, ref in (("PHYS_AUX", "GPC_X"), ("PHYS_AUX", "G3_MARGIN"), ("PHYS_AUX", "E1_STRADDLE"), ("GPC_X", "G3_MARGIN")):
        A = [aulc(cand, rep) for rep in REPEATS]; B = [aulc(ref, rep) for rep in REPEATS]
        if any(x is None for x in A + B):
            res["contrasts"][f"{cand}-{ref}"] = {"available": False}; continue
        d = np.mean([x - z for x, z in zip(A, B)], axis=0); lo, hi = np.nanpercentile(d[1:], [2.5, 97.5]); per = [float(x[0] - z[0]) for x, z in zip(A, B)]
        skc = [M[(cand, rep, 40)]["shortK_caught"] for rep in REPEATS]; skr = [M[(ref, rep, 40)]["shortK_caught"] for rep in REPEATS]
        gain = d[0] >= 0.04 and lo > 0 and all(v > 0 for v in per); guard = all(v >= 7 for v in skc) and sum(skc) >= sum(skr) - 2
        res["contrasts"][f"{cand}-{ref}"] = {"BA_AULC_diff": float(d[0]), "lo": float(lo), "hi": float(hi), "per_repeat": per, "shortK_caught_B40": skc, "ref_shortK_caught_B40": skr,
                                             "verdict": "PRACTICALLY BETTER" if gain and guard else "TRADE-OFF (BA gain with short-K loss)" if gain else "NO PRACTICAL DIFFERENCE"}
    t = {a: float(np.sum([R[k]["seconds"] for k in R if k[2] == a])) for a in arms}; res["compute_seconds_total"] = t
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "results").mkdir(exist_ok=True)
    (OUT / "results" / "PHYS_AUX_RESULTS.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))
    return res


def validate():
    t0 = time.time(); checks, info = {}, {}
    try:
        g = np.random.default_rng(2); Xs = g.normal(0, 1, (25, 4)); ys = np.sin(Xs[:, 0]) + 0.1 * g.normal(size=25)
        gp = _gpr(Xs, ys); lo = loo_means(gp, ys)
        # brute-force LOO with the same fixed kernel AND the same target normalisation (direct conditioning on the other 24 points)
        K = gp.kernel_(Xs); yn = (ys - gp._y_train_mean) / gp._y_train_std; bf = []
        for i in range(25):
            m = np.arange(25) != i
            bf.append(K[i, m] @ np.linalg.solve(K[np.ix_(m, m)], yn[m]) * gp._y_train_std + gp._y_train_mean)
        checks["closed_form_loo_equals_direct_conditioning"] = float(np.max(np.abs(lo - np.asarray(bf)))) < 1e-6
        info["loo_max_abs_diff"] = float(np.max(np.abs(lo - np.asarray(bf))))
        auxT = aux_table(); checks["aux_table_has_136_runs"] = len(auxT) == 136 and auxT.notna().sum().min() >= 130
        tasks = {(t["repeat"], t["fold"]): t for t in TA.build_tasks()}; t = tasks[(3, 1)]
        tt = time.time(); r1 = run_unit(t, "PHYS_AUX", auxT); info["unit_seconds_PHYS_AUX_r3f1"] = time.time() - tt
        checks["unit_runs"] = r1["status"] == "ok" and len(r1["paid"]) == B_END
        # leakage: corrupt every unpaid/test label AND auxiliary value -> identical path and predictions
        y2 = t["y"].copy(); hidden = np.setdiff1d(np.arange(len(y2)), r1["paid"]); y2[hidden] = 1 - y2[hidden]
        aux2 = auxT.copy(); hid_ids = set(np.asarray(t["ids"]).astype(str)[hidden]); aux2.loc[aux2.index.isin(hid_ids)] = 99.0
        r2 = run_unit({**t, "y": y2}, "PHYS_AUX", aux2)
        checks["hidden_labels_and_monitors_do_not_change_path_or_predictions"] = r1["paid"] == r2["paid"] and r1["evals"][-1]["p"] == r2["evals"][-1]["p"]
        t4 = tasks[(3, 4)]; r4 = run_unit(t4, "GPC_X", auxT)
        checks["one_class_rule_same_as_pilot_A"] = r4["paid"][16] == int([i for i in t4["path"] if i not in set(t4["path"][:16])][0])
        checks["references_available_from_pilot_A"] = all((SD.CACHE / f"NEW__r{r}_f{f}__{a}.json.gz").exists() for a in ("G3_MARGIN", "E1_STRADDLE") for r in REPEATS for f in FOLDS)
    except Exception as ex:
        checks["selftest_completed"] = False; info["error"] = f"{type(ex).__name__}: {ex}"[:400]; info["traceback"] = traceback.format_exc()[-2000:]
    res = {"study": STUDY, "status": "PASS" if checks and all(checks.values()) else "FAIL", "checks": {k: bool(v) for k, v in checks.items()}, "info": info,
           "seconds": time.time() - t0, "module_sha256": SMM.sha256(SMM.ROOT / "src" / "jdl_phys_aux.py")}
    OUT.mkdir(parents=True, exist_ok=True); VALIDATION.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"status": res["status"], "checks": res["checks"], "info": {k: v for k, v in info.items() if k != "traceback"}}, indent=1, default=str))
    if res["status"] != "PASS":
        raise SystemExit(1)


def write_manifest():
    val = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if val["status"] != "PASS" or val["module_sha256"] != SMM.sha256(SMM.ROOT / "src" / "jdl_phys_aux.py"):
        raise SystemExit("PHYS_AUX validation must PASS with this module before the freeze")
    man = {"study": STUDY, "status": "FROZEN BEFORE ANY PHYS_AUX OUTCOME", "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "parent_commit": SMM._git("rev-parse", "HEAD"), "aux": list(AUX), "arms": list(ARMS), "references": ["G3_MARGIN", "E1_STRADDLE (pilot A cache)"],
           "validation": {"status": val["status"], "sha256": SMM.sha256(VALIDATION)}, "code_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in CODE}}
    MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8"); print(json.dumps({k: man[k] for k in ("status", "written_utc")}, indent=1))


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "evaluate"
    {"validate": validate, "manifest": write_manifest, "work": lambda: work(sys.argv[2:]), "evaluate": evaluate}[step]()
