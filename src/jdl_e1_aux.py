"""E1_AUX: the one justified correction allowed within the pilot budget (owner request of 2026-10-16).

Diagnosis that motivates it (PHYS_AUX, PHYS_AUX_REP): x-predicted physics reliably improves a label-only GP classifier
(PHYS_AUX - GPC_X +0.093 on DEV r3-4, +0.064 on r5-8, every repeat positive) but does not beat ACTIVE E1 + straddle, whose
base is a depth-response GP.  The failing piece is the weak label-only base, not the physical channel.  Correction: put the
same auxiliary predictions on E1's base.
E1_AUX: E1's DepthGPR unchanged in form (GP regression of standardised log depth, Matern 3/2 ARD + white noise, ML-II, no
restarts; online threshold u from the paid (log depth, label) pairs; latent noise removed; straddle 1.96 sd - |mu - u|) with
the input extended from the 4 standardised log inputs to 4 + 2 z-scored auxiliary predictions (log KE_T0, velocity spike
log-ratio) built exactly as in PHYS_AUX (paid-only GP regressions; LOO means for paid runs, full-fit means elsewhere; true
monitors never used as features; monitors of new or test runs never read).  The frozen week18_engine is not modified.
Decisive control: E1_STRADDLE on the same tasks (pilot A cache for r3-4, PHYS_AUX_REP cache for r5-8).  Reference: G3_MARGIN.
Pre-written criterion, per task block (r3-4 and r5-8 reported separately, never pooled): PRACTICALLY BETTER iff BA-AULC
>= +0.04, 95 % class-stratified cluster-bootstrap interval > 0, every repeat positive, short-K caught at B40 >= 7/10 in every
repeat and at most 2 of 20 (r3-4) / 4 of 40 (r5-8) below the comparator; gain failing only short-K = TRADE-OFF; else NO
PRACTICAL DIFFERENCE.  No saving is claimed without sustained target attainment before the reference.
Steps: python -m src.jdl_e1_aux validate | manifest | work | evaluate
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
from scipy.special import ndtr

import src.jdl_phys_aux as PA
import src.jdl_phys_aux_rep as PR
import src.jdl_stage_m as SMM
import src.jdl_surprise as SD
import src.jdl_trained_al as TA

STUDY = "E1_AUX"
OUT = SMM.OUT / "e1_aux"
CACHE = SMM.OUT / "_cache" / "e1_aux"
MANIFEST = OUT / "E1_AUX_MANIFEST.json"
VALIDATION = OUT / "E1_AUX_VALIDATION.json"
BLOCKS = {"r3_4": (3, 4), "r5_8": (5, 6, 7, 8)}
FOLDS, B_START, B_END = (1, 2, 3, 4, 5), 16, 40
CODE = ("src/jdl_e1_aux.py", "src/jdl_phys_aux.py", "src/jdl_phys_aux_rep.py", "src/jdl_surprise.py", "src/jdl_trained_al.py", "src/jdl_stage_m.py",
        "src/jdl_evaluate.py", "src/week18_engine.py")


class DepthGPRAux:
    """week18_engine.DepthGPR with an extended (already standardised) input; identical kernel family, threshold and latent."""

    def fit(self, F, depth, y):
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
        from sklearn.linear_model import LogisticRegression
        ok = np.isfinite(depth) & (depth > 0); F, depth, y = F[ok], depth[ok], y[ok]
        t = np.log(depth); self.mu_t, self.sd_t = t.mean(), t.std() + 1e-9
        k = ConstantKernel(1.0, (1e-3, 1e3)) * Matern(np.ones(F.shape[1]), (1e-2, 1e2), nu=1.5) + WhiteKernel(1e-2, (1e-6, 1.0))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.gp = GaussianProcessRegressor(k, normalize_y=False, n_restarts_optimizer=0, random_state=0).fit(F, (t - self.mu_t) / self.sd_t)
        kh, nk = t[y == 1], t[y == 0]
        if len(kh) and len(nk) and nk.max() < kh.min():
            self.u = .5 * (nk.max() + kh.min())
        elif len(kh) and len(nk):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                lr = LogisticRegression(C=1e6, max_iter=5000).fit(t[:, None], y)
            self.u = float(-lr.intercept_[0] / lr.coef_[0, 0])
        else:
            self.u = np.log(111.0)
        return self

    def latent(self, F):
        m, s = self.gp.predict(F, return_std=True); mu = m * self.sd_t + self.mu_t
        noise = np.exp(self.gp.kernel_.theta[-1]) * self.sd_t ** 2
        return mu - self.u, np.maximum((s * self.sd_t) ** 2 - noise, 1e-12)

    def proba(self, F):
        mu, var = self.latent(F); return ndtr(mu / np.sqrt(var))


def run_unit(task, auxT, deadline=None):
    X, y, A, ids, pool, test = task["X"], task["y"], task["A"], np.asarray(task["ids"]).astype(str), task["pool"], task["test"]
    std = SMM.standardizer(task)[0]; Z = np.zeros((len(X), 4)); Z[pool] = std(X[pool]); Z[test] = std(X[test])
    auxv = auxT.reindex(ids)[list(PA.AUX)].to_numpy(float)
    L = [int(i) for i in task["path"][:B_START]]; evals, steps = [], []; t0 = time.time(); status = "ok"
    for b in range(B_START, B_END + 1):
        if deadline is not None and time.time() > deadline:
            status = f"TIME_LIMIT at B{b}"; break
        ts = time.time(); unpaid = np.setdiff1d(pool, L); others = np.r_[unpaid, test]; Lr = np.asarray(L)
        usable = np.isfinite(A[Lr]) & (A[Lr] > 0); one_class = len(set(y[Lr][usable].tolist())) < 2
        if one_class:
            pc = (int(y[Lr][usable].sum()) + 0.5) / (int(usable.sum()) + 1); p_te = np.full(len(test), pc); m = None
        else:
            Fp, Fo, info = PA.features(Z, L, others, auxv)
            m = DepthGPRAux().fit(Fp, A[Lr], y[Lr]); p_te = m.proba(Fo[len(unpaid):])
        evals.append({"budget": b, "p": np.asarray(p_te).tolist(), "constant_predictor": bool(one_class)})
        steps.append({"budget": b, "seconds": time.time() - ts})
        if b == B_END:
            break
        if one_class:
            nxt = int([i for i in task["path"] if i not in set(L)][0]); how = "path_continuation"
        else:
            mu, var = m.latent(Fo[:len(unpaid)]); nxt = int(unpaid[int(np.argmax(1.96 * np.sqrt(var) - np.abs(mu)))]); how = "straddle"
        L.append(nxt); steps[-1].update({"selected": ids[nxt], "how": how})
    return {"repeat": task["repeat"], "fold": task["fold"], "arm": "E1_AUX", "paid": L, "paid_ids": [ids[i] for i in L], "test_ids": [ids[i] for i in test],
            "evals": evals, "steps": steps, "status": status, "seconds": time.time() - t0}


def all_tasks():
    T = {(t["repeat"], t["fold"]): t for t in TA.build_tasks()}
    T.update({(t["repeat"], t["fold"]): t for t in PR.build_tasks()}); return T


def work(argv=()):
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not SMM._git("log", "--format=%H", "--", str(MANIFEST.relative_to(SMM.ROOT)).replace("\\", "/")):
        raise SystemExit("commit the E1_AUX manifest before any run")
    for c, h in man["code_sha256"].items():
        if SMM.sha256(SMM.ROOT / c) != h:
            raise SystemExit(f"{c} changed after the E1_AUX freeze")
    T = all_tasks(); auxT = PA.aux_table(); CACHE.mkdir(parents=True, exist_ok=True); locks = CACHE / "locks"; locks.mkdir(exist_ok=True)
    for reps in BLOCKS.values():
        for r in reps:
            for f in FOLDS:
                name = f"NEW__r{r}_f{f}__E1_AUX"; out = CACHE / f"{name}.json.gz"
                if out.exists():
                    continue
                lock = locks / f"{name}.lock"
                try:
                    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                except FileExistsError:
                    continue
                os.write(fd, str(os.getpid()).encode()); os.close(fd)
                try:
                    t0 = time.time(); res = run_unit(T[(r, f)], auxT, deadline=t0 + PA.UNIT_TIME_LIMIT_S)
                    res.update({"study": STUDY, "unit": name, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
                    TA._atomic_write(out, res); print(json.dumps({"unit": name, "status": res["status"], "s": round(res["seconds"], 1)}), flush=True)
                finally:
                    lock.unlink(missing_ok=True)


def evaluate():
    import src.jdl_evaluate as EV
    import src.jdl_trained_al_eval as TE
    res = {"blocks": {}}
    for bname, reps in BLOCKS.items():
        F = TE.frame()[1] if bname == "r3_4" else PR.frame()
        refdir = SD.CACHE if bname == "r3_4" else PR.CACHE
        R = {}
        for r in reps:
            for f in FOLDS:
                for a, d in (("E1_AUX", CACHE), ("E1_STRADDLE", refdir), ("G3_MARGIN", refdir)):
                    q = d / f"NEW__r{r}_f{f}__{a}.json.gz"
                    if q.exists():
                        R[(r, f, a)] = json.loads(gzip.decompress(q.read_bytes()))
        y, sk = F["y"], F["shortk"]; W = EV.boot_weights(y); corner = np.asarray(F["VX"], float) > SMM.FAST_VX
        pos = {s: i for i, s in enumerate(F["ids"])}; budgets = range(B_START, B_END + 1); M = {}
        for a in ("E1_AUX", "E1_STRADDLE", "G3_MARGIN"):
            for rep in reps:
                for b in budgets:
                    p = np.full(len(F["ids"]), np.nan); okf = 0
                    for f in FOLDS:
                        r = R.get((rep, f, a)); e = None if r is None else {x["budget"]: x for x in r["evals"]}.get(b)
                        if e is not None:
                            p[[pos[s] for s in r["test_ids"]]] = e["p"]; okf += 1
                    if okf == len(FOLDS) and np.isfinite(p).all():
                        m = EV.wmetrics(p, np.ones(len(p), bool), y, sk, F["q20"][rep], F["fold"][rep], W); c = EV.wmetrics(p, corner, y, sk, F["q20"][rep], F["fold"][rep], W)
                        M[(a, rep, b)] = {"BA": m["BA"], "brier": m["brier"], "AUC": m["AUC"], "corner_AUC": c["AUC"], "shortK_caught": int(((p >= .5) & sk).sum())}
        def aulc(a, rep):
            if not all((a, rep, b) in M for b in budgets):
                return None
            v = np.vstack([M[(a, rep, b)]["BA"] for b in budgets]); return np.trapezoid(v, x=np.array(list(budgets), float), axis=0) / 24.0
        blk = {"per_arm": {}, "contrasts": {}}
        for a in ("E1_AUX", "E1_STRADDLE", "G3_MARGIN"):
            blk["per_arm"][a] = {"BA_AULC": [None if aulc(a, r) is None else round(float(aulc(a, r)[0]), 4) for r in reps],
                                 "B40_BA": [round(float(M[(a, r, 40)]["BA"][0]), 4) if (a, r, 40) in M else None for r in reps],
                                 "B40_shortK_caught": [M[(a, r, 40)]["shortK_caught"] if (a, r, 40) in M else None for r in reps],
                                 "B40_corner_AUC": [round(float(M[(a, r, 40)]["corner_AUC"][0]), 4) if (a, r, 40) in M else None for r in reps],
                                 "B40_brier": [round(float(M[(a, r, 40)]["brier"][0]), 4) if (a, r, 40) in M else None for r in reps],
                                 "seconds_total": float(sum(R[k]["seconds"] for k in R if k[2] == a))}
        tol = 2 if len(reps) == 2 else 4
        for ref in ("E1_STRADDLE", "G3_MARGIN"):
            Aa = [aulc("E1_AUX", r) for r in reps]; Bb = [aulc(ref, r) for r in reps]
            if any(x is None for x in Aa + Bb):
                blk["contrasts"][f"E1_AUX-{ref}"] = {"available": False}; continue
            d = np.mean([x - z for x, z in zip(Aa, Bb)], axis=0); lo, hi = np.nanpercentile(d[1:], [2.5, 97.5]); per = [float(x[0] - z[0]) for x, z in zip(Aa, Bb)]
            skc = [M[("E1_AUX", r, 40)]["shortK_caught"] for r in reps]; skr = [M[(ref, r, 40)]["shortK_caught"] for r in reps]
            gain = d[0] >= 0.04 and lo > 0 and all(v > 0 for v in per); guard = all(v >= 7 for v in skc) and sum(skc) >= sum(skr) - tol
            blk["contrasts"][f"E1_AUX-{ref}"] = {"BA_AULC_diff": float(d[0]), "lo": float(lo), "hi": float(hi), "per_repeat": per, "shortK_caught_B40": skc, "ref_shortK_caught_B40": skr,
                                                 "verdict": "PRACTICALLY BETTER" if gain and guard else "TRADE-OFF (BA gain with short-K loss)" if gain else "NO PRACTICAL DIFFERENCE"}
        res["blocks"][bname] = blk
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "results").mkdir(exist_ok=True)
    (OUT / "results" / "E1_AUX_RESULTS.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str)); return res


def validate():
    t0 = time.time(); checks, info = {}, {}
    try:
        import src.week18_engine as E
        T = all_tasks(); t = T[(4, 1)]; std = SMM.standardizer(t)[0]
        # with the auxiliary columns removed, DepthGPRAux equals the frozen DepthGPR (same inputs, kernel, threshold)
        L = list(t["path"][:20]); Lr = np.asarray(L); ok = np.isfinite(t["A"][Lr])
        ref = E.DepthGPR(t["X"][t["pool"]]).fit(t["X"][Lr], t["A"][Lr], t["y"][Lr])
        mine = DepthGPRAux().fit(std(t["X"][Lr]), t["A"][Lr], t["y"][Lr])
        pr, pm = ref.proba(t["X"][t["test"]]), mine.proba(std(t["X"][t["test"]]))
        checks["reduces_to_frozen_DepthGPR_without_aux"] = float(np.max(np.abs(pr - pm))) < 1e-6 and abs(ref.u - mine.u) < 1e-9
        info["max_abs_diff_vs_frozen"] = float(np.max(np.abs(pr - pm)))
        auxT = PA.aux_table(); tt = time.time(); r1 = run_unit(t, auxT); info["unit_seconds"] = time.time() - tt
        checks["unit_runs"] = r1["status"] == "ok" and len(r1["paid"]) == B_END
        y2, A2 = t["y"].copy(), t["A"].copy(); hidden = np.setdiff1d(np.arange(len(y2)), r1["paid"]); y2[hidden] = 1 - y2[hidden]; A2[hidden] = 4000.0
        aux2 = auxT.copy(); hid = set(np.asarray(t["ids"]).astype(str)[hidden]); aux2.loc[aux2.index.isin(hid)] = 99.0
        r2 = run_unit({**t, "y": y2, "A": A2}, aux2)
        checks["hidden_outcomes_and_monitors_do_not_change_path_or_predictions"] = r1["paid"] == r2["paid"] and r1["evals"][-1]["p"] == r2["evals"][-1]["p"]
        checks["controls_available"] = all((SD.CACHE / f"NEW__r{r}_f{f}__E1_STRADDLE.json.gz").exists() for r in (3, 4) for f in FOLDS) and \
            all((PR.CACHE / f"NEW__r{r}_f{f}__E1_STRADDLE.json.gz").exists() for r in (5, 6, 7, 8) for f in FOLDS)
    except Exception as ex:
        checks["selftest_completed"] = False; info["error"] = f"{type(ex).__name__}: {ex}"[:400]; info["traceback"] = traceback.format_exc()[-2000:]
    res = {"study": STUDY, "status": "PASS" if checks and all(checks.values()) else "FAIL", "checks": {k: bool(v) for k, v in checks.items()}, "info": info,
           "seconds": time.time() - t0, "module_sha256": SMM.sha256(SMM.ROOT / "src" / "jdl_e1_aux.py")}
    OUT.mkdir(parents=True, exist_ok=True); VALIDATION.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"status": res["status"], "checks": res["checks"], "info": {k: v for k, v in info.items() if k != "traceback"}}, indent=1, default=str))
    if res["status"] != "PASS":
        raise SystemExit(1)


def write_manifest():
    val = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if val["status"] != "PASS" or val["module_sha256"] != SMM.sha256(SMM.ROOT / "src" / "jdl_e1_aux.py"):
        raise SystemExit("E1_AUX validation must PASS with this module before the freeze")
    man = {"study": STUDY, "status": "FROZEN BEFORE ANY E1_AUX OUTCOME", "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "parent_commit": SMM._git("rev-parse", "HEAD"), "blocks": {k: list(v) for k, v in BLOCKS.items()},
           "criterion": "PRACTICALLY BETTER iff >= +0.04, interval > 0, every repeat positive, short-K >= 7/10 per repeat and within 2 of 20 (r3-4) / 4 of 40 (r5-8)",
           "validation": {"status": val["status"], "sha256": SMM.sha256(VALIDATION)}, "code_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in CODE}}
    MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8"); print(json.dumps({k: man[k] for k in ("status", "written_utc")}, indent=1))


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "evaluate"
    {"validate": validate, "manifest": write_manifest, "work": lambda: work(sys.argv[2:]), "evaluate": evaluate}[step]()
