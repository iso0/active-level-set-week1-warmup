"""PHYS_DISCOVERY (Study 2; owner approval of 2026-10-17; Ioan, 2026-10-15: "find some kind of an outsider and then expand to
find its whole family").  Surprise-triggered local discovery on a CONTINUOUS physical response (pilot A used binary labels).

Response: the velocity spike log-ratio (PHYS_AL target T3; LEARNABLE on NEW, R2 0.87): brief melt-flow surges.
Family (evaluator truth only; rule fixed now): runs in the top decile of the population's observed values ("spiky
melt flow").  Secondary family: the bottom decile.  Neither membership nor any unpaid value enters a selector.
Rule SD-R (fixed): after paying run c, z = (y_c - mu_prev(c)) / sqrt(var_prev(c) + noise_prev) under the GP fitted on the paid
runs BEFORE c.  Surprise iff |z| >= 2.5 and the run passes QC (finite value, no implausible-velocity rows, no non-finite KE
rows, status ok); a QC failure is logged as QC_EVENT, never a surprise.  A surprise seeds up to 3 local probes (nearest
unpaid pool runs in fold-standardised log inputs, ties by simulation ID), alternating 1:1 with the base selector; a surprising
local probe seeds again.  Every probe is a paid query.
Arms: MAXVAR (base; argmax predictive sd), SD_MAXVAR (candidate), RANDOM, MAXIMIN (frozen feature-only path).  Same GP
(Matern 3/2 ARD + white nugget, normalize_y, ML-II, no restarts), same start (first 8 path points), budgets B8-B60.
Populations NEW and OLD (separate), DEV repeats 3-4, folds 1-5 (PHYS_AL tasks).
Endpoints (fixed): family discovery AUDC = area under the fraction of the fold pool's family members paid, B8-B60 (/52);
queries to half the family (censored at 64); global R2-AULC (PHYS_AL definition) as the no-harm check.
Verdict: DISCOVERY GAIN (DEV) iff SD_MAXVAR - MAXVAR family AUDC > 0 with a paired bootstrap interval (10 trajectories, 2000
draws, seed 20261017) above 0 AND the R2-AULC of SD_MAXVAR is not lower than MAXVAR's by more than 0.02 (mean of repeats).
Steps: python -m src.jdl_phys_discovery validate | manifest | work [--pop NEW|OLD] | evaluate
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

import numpy as np
import pandas as pd

import src.jdl_phys_al as PAL
import src.jdl_stage_m as SMM
import src.jdl_trained_al as TA

STUDY = "PHYS_DISCOVERY"
OUT = SMM.OUT / "phys_discovery"
CACHE = SMM.OUT / "_cache" / "phys_discovery"
MANIFEST = OUT / "PHYS_DISCOVERY_MANIFEST.json"
VALIDATION = OUT / "PHYS_DISCOVERY_VALIDATION.json"
RESPONSE = "vmax_spike_logratio"
Z_SURPRISE, M_LOCAL = 2.5, 3
ARMS = ("MAXVAR", "SD_MAXVAR", "RANDOM", "MAXIMIN")
REPEATS, FOLDS, B0, B1 = PAL.REPEATS, PAL.FOLDS, PAL.B0, PAL.B1
CODE = ("src/jdl_phys_discovery.py", "src/jdl_phys_al.py", "src/jdl_physical_pilot.py", "src/jdl_physical_data2.py", "src/jdl_trained_al.py", "src/jdl_stage_m.py")


def qc_table(pop):
    """Learner-visible QC flags of a paid run (from its own monitors): True = passes QC."""
    if pop == "NEW":
        S = pd.read_csv(SMM.OUT / "physical" / "physical_summaries.csv").set_index("sim_id")
    else:
        S = pd.read_csv(PAL.OUT / "extracted_summaries.csv"); S = S[S.population == "OLD"].set_index("sim_id")
    ok = (S.get("status", pd.Series("ok", index=S.index)) == "ok") & (S.get("implausible_vmax_rows", 0).fillna(0) == 0) & (S.get("nonfinite_ke", 0).fillna(0) == 0)
    return ok


def run_traj(task, pop, arm, Tt, qc, deadline=None):
    X, ids, pool, test = task["X"], np.asarray(task["ids"]).astype(str), task["pool"], task["test"]
    std = SMM.standardizer(task)[0]; Z = np.zeros((len(X), 4)); Z[pool] = std(X[pool]); Z[test] = std(X[test])
    y = Tt.reindex(ids)[RESPONSE].to_numpy(float); q = qc.reindex(ids).fillna(False).to_numpy(bool)
    rng = np.random.default_rng(41000 + 100 * task["repeat"] + task["fold"] + (17 if pop == "OLD" else 0))
    L = [int(i) for i in task["path"][:B0]]; seeds, last_local, log, evals = [], False, [], []; t0 = time.time(); status = "ok"; prev = None
    for b in range(B0, B1 + 1):
        if deadline is not None and time.time() > deadline:
            status = f"TIME_LIMIT at B{b}"; break
        ok = np.isfinite(y[L]); Lj = np.asarray(L)[ok]; g = PAL.gp_fit(Z[Lj], y[Lj]) if len(Lj) >= 3 else None
        evals.append({"budget": b, "pred": None if g is None else g.predict(Z[test]).tolist()})
        if b == B1:
            break
        unpaid = np.setdiff1d(pool, L); nxt = None; how = None
        if arm == "SD_MAXVAR":
            while seeds and seeds[0][1] <= 0:
                seeds.pop(0)
            if seeds and not last_local:
                s = seeds[0][0]; d = np.linalg.norm(Z[unpaid] - Z[s], axis=1); nxt = int(unpaid[np.lexsort((ids[unpaid], d))[0]]); seeds[0][1] -= 1; how = "local"
        if nxt is None:
            if arm == "RANDOM":
                nxt = int(rng.choice(unpaid)); how = "random"
            elif arm == "MAXIMIN" or g is None:
                nxt = int([i for i in task["path"] if i not in set(L)][0]); how = "path"
            else:
                sd = g.predict(Z[unpaid], return_std=True)[1]; nxt = int(unpaid[int(np.argmax(sd))]); how = "maxvar"
        last_local = how == "local"
        if arm == "SD_MAXVAR" and g is not None:                               # surprise of the observation under the PRE-observation posterior
            m, s_ = g.predict(Z[[nxt]], return_std=True); noise = float(np.exp(g.kernel_.theta[-1])) * float(g._y_train_std) ** 2
            zval = float((y[nxt] - m[0]) / np.sqrt(s_[0] ** 2 + noise)) if np.isfinite(y[nxt]) else None
            event = "QC_EVENT" if (not q[nxt] or zval is None) else ("SURPRISE" if abs(zval) >= Z_SURPRISE else "none")
            log.append({"budget": b + 1, "selected": ids[nxt], "how": how, "z": zval, "event": event})
            if event == "SURPRISE":
                seeds.append([int(nxt), M_LOCAL])
        L.append(nxt)
    return {"population": pop, "repeat": task["repeat"], "fold": task["fold"], "arm": arm, "paid": L, "paid_ids": [ids[i] for i in L], "test_ids": [ids[i] for i in test],
            "evals": evals, "sd_log": log, "status": status, "seconds": time.time() - t0}


def work(argv=()):
    argv = list(argv); pop = argv[argv.index("--pop") + 1] if "--pop" in argv else "NEW"
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not SMM._git("log", "--format=%H", "--", str(MANIFEST.relative_to(SMM.ROOT)).replace("\\", "/")):
        raise SystemExit("commit the PHYS_DISCOVERY manifest before any run")
    for c, h in man["code_sha256"].items():
        if SMM.sha256(SMM.ROOT / c) != h:
            raise SystemExit(f"{c} changed after the PHYS_DISCOVERY freeze")
    Tt, qc = PAL.targets(pop), qc_table(pop); T = {(t["repeat"], t["fold"]): t for t in PAL.tasks(pop)}
    CACHE.mkdir(parents=True, exist_ok=True); locks = CACHE / "locks"; locks.mkdir(exist_ok=True)
    for arm in ARMS:
        for r in REPEATS:
            for f in FOLDS:
                name = f"{pop}__r{r}_f{f}__{arm}"; out = CACHE / f"{name}.json.gz"
                if out.exists():
                    continue
                lock = locks / f"{name}.lock"
                try:
                    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                except FileExistsError:
                    continue
                os.write(fd, str(os.getpid()).encode()); os.close(fd)
                try:
                    t0 = time.time(); res = run_traj(T[(r, f)], pop, arm, Tt, qc, deadline=t0 + 1800)
                    res.update({"study": STUDY, "unit": name, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
                    TA._atomic_write(out, res); print(json.dumps({"unit": name, "status": res["status"], "s": round(res["seconds"], 1)}), flush=True)
                finally:
                    lock.unlink(missing_ok=True)


def evaluate(pops=("NEW", "OLD")):
    res = {}; rng = np.random.default_rng(20261017)
    for pop in pops:
        R = {}
        for p in CACHE.glob(f"{pop}__*.json.gz"):
            r = json.loads(gzip.decompress(p.read_bytes())); R[(r["repeat"], r["fold"], r["arm"])] = r
        if not R:
            continue
        Tt = PAL.targets(pop); yall = Tt[RESPONSE].dropna(); hi, lo_ = yall.quantile(0.9), yall.quantile(0.1)
        fam_hi, fam_lo = set(yall[yall >= hi].index), set(yall[yall <= lo_].index); T = {(t["repeat"], t["fold"]): t for t in PAL.tasks(pop)}
        rows = []
        for (r, f, a), u in R.items():
            t = T[(r, f)]; pool_ids = set(np.asarray(t["ids"]).astype(str)[t["pool"]]); nh, nl = len(fam_hi & pool_ids), len(fam_lo & pool_ids)
            ch = [len(fam_hi & set(u["paid_ids"][:b])) / max(1, nh) for b in range(B0, B1 + 1)]
            cl = [len(fam_lo & set(u["paid_ids"][:b])) / max(1, nl) for b in range(B0, B1 + 1)]
            half = next((B0 + i for i, v in enumerate(ch) if v >= 0.5), 64)
            yv_all, pv_all = [], []
            rows.append({"repeat": r, "fold": f, "arm": a, "family_hi_AUDC": float(np.trapezoid(ch) / (B1 - B0)), "family_lo_AUDC": float(np.trapezoid(cl) / (B1 - B0)),
                         "family_hi_found_B60": ch[-1], "queries_to_half_hi": half, "n_family_hi_pool": nh,
                         "surprises": sum(1 for x in u["sd_log"] if x["event"] == "SURPRISE"), "qc_events": sum(1 for x in u["sd_log"] if x["event"] == "QC_EVENT"),
                         "seconds": u["seconds"]})
        D = pd.DataFrame(rows)
        # global R2-AULC per repeat (pooled test predictions; PHYS_AL definition)
        ref = float(yall.mean()); r2 = {}
        for a in ARMS:
            for rep in REPEATS:
                cv = []
                for b in range(B0, B1 + 1):
                    yy, pp = [], []
                    for f in FOLDS:
                        u = R.get((rep, f, a)); e = None if u is None else {x["budget"]: x for x in u["evals"]}.get(b)
                        if e is None or e["pred"] is None:
                            break
                        yv = Tt.reindex(u["test_ids"])[RESPONSE].to_numpy(float); ok = np.isfinite(yv); yy.extend(yv[ok]); pp.extend(np.asarray(e["pred"])[ok])
                    else:
                        cv.append(1 - np.sum((np.asarray(yy) - np.asarray(pp)) ** 2) / np.sum((np.asarray(yy) - ref) ** 2))
                r2[(a, rep)] = float(np.trapezoid(cv) / (B1 - B0)) if len(cv) == B1 - B0 + 1 else None
        out = {"family_hi_threshold": float(hi), "family_lo_threshold": float(lo_), "n_family_hi": len(fam_hi),
               "arm_means": D.groupby("arm")[["family_hi_AUDC", "family_lo_AUDC", "family_hi_found_B60", "queries_to_half_hi", "surprises", "qc_events", "seconds"]].mean().round(4).to_dict(orient="index"),
               "R2_AULC": {f"{a}|r{rep}": v for (a, rep), v in r2.items()}, "contrasts": {}}
        for cand, refa in (("SD_MAXVAR", "MAXVAR"), ("SD_MAXVAR", "RANDOM"), ("MAXVAR", "RANDOM"), ("MAXVAR", "MAXIMIN")):
            m = D[D.arm == cand].set_index(["repeat", "fold"]).join(D[D.arm == refa].set_index(["repeat", "fold"]), rsuffix="_ref", how="inner")
            if not len(m):
                continue
            d = (m.family_hi_AUDC - m.family_hi_AUDC_ref).to_numpy(); bs = [np.mean(rng.choice(d, len(d))) for _ in range(2000)]
            harm = None
            if all(r2.get((x, rep)) is not None for x in (cand, refa) for rep in REPEATS):
                harm = float(np.mean([r2[(cand, rep)] - r2[(refa, rep)] for rep in REPEATS]))
            row = {"family_hi_AUDC_diff": float(d.mean()), "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5)), "pairs": len(d), "R2_AULC_diff": harm}
            if (cand, refa) == ("SD_MAXVAR", "MAXVAR"):
                row["verdict"] = "DISCOVERY GAIN (DEV)" if row["family_hi_AUDC_diff"] > 0 and row["lo"] > 0 and (harm is None or harm >= -0.02) else "NO DISCOVERY GAIN ESTABLISHED"
            out["contrasts"][f"{cand}-{refa}"] = row
        res[pop] = out
        D.to_csv(OUT / f"discovery_per_trajectory_{pop}.csv", index=False, lineterminator="\n")
    (OUT / "results").mkdir(parents=True, exist_ok=True); (OUT / "results" / "PHYS_DISCOVERY_RESULTS.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str)); return res


def validate():
    t0 = time.time(); checks, info = {}, {}
    try:
        Tt, qc = PAL.targets("NEW"), qc_table("NEW"); T = {(t["repeat"], t["fold"]): t for t in PAL.tasks("NEW")}; t = T[(3, 1)]
        tt = time.time(); a = run_traj(t, "NEW", "SD_MAXVAR", Tt, qc); info["unit_seconds"] = time.time() - tt
        checks["unit_runs"] = a["status"] == "ok" and len(a["paid"]) == B1
        info["events"] = pd.Series([x["event"] for x in a["sd_log"]]).value_counts().to_dict()
        T2 = Tt.copy(); hid = set(np.asarray(t["ids"]).astype(str)) - set(a["paid_ids"]); T2.loc[T2.index.isin(hid), RESPONSE] = 99.0
        b2 = run_traj(t, "NEW", "SD_MAXVAR", T2, qc)
        checks["hidden_values_do_not_change_path"] = a["paid"] == b2["paid"] and a["evals"][-1]["pred"] == b2["evals"][-1]["pred"]
        q2 = qc.copy(); q2.loc[:] = False; c2 = run_traj(t, "NEW", "SD_MAXVAR", Tt, q2)
        checks["qc_failures_are_never_surprises"] = all(x["event"] != "SURPRISE" for x in c2["sd_log"])
        m = run_traj(t, "NEW", "MAXVAR", Tt, qc)
        ks = next((k for k, x in enumerate(a["sd_log"]) if x["event"] == "SURPRISE"), None)      # log k = observation of paid index B0 + k
        cut = len(a["paid"]) if ks is None else B0 + ks + 1                                      # first possible local query
        checks["sd_equals_base_before_first_surprise"] = a["paid"][:cut] == m["paid"][:cut]
        info["first_surprise_log_index"] = ks
        checks["qc_table_new"] = int(qc.sum()) >= 120
    except Exception as ex:
        checks["selftest_completed"] = False; info["error"] = f"{type(ex).__name__}: {ex}"[:400]; info["traceback"] = traceback.format_exc()[-2000:]
    res = {"study": STUDY, "status": "PASS" if checks and all(checks.values()) else "FAIL", "checks": {k: bool(v) for k, v in checks.items()}, "info": info,
           "seconds": time.time() - t0, "module_sha256": SMM.sha256(SMM.ROOT / "src" / "jdl_phys_discovery.py")}
    OUT.mkdir(parents=True, exist_ok=True); VALIDATION.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"status": res["status"], "checks": res["checks"], "info": {k: v for k, v in info.items() if k != "traceback"}}, indent=1, default=str))
    if res["status"] != "PASS":
        raise SystemExit(1)


def write_manifest():
    val = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if val["status"] != "PASS" or val["module_sha256"] != SMM.sha256(SMM.ROOT / "src" / "jdl_phys_discovery.py"):
        raise SystemExit("PHYS_DISCOVERY validation must PASS with this module before the freeze")
    man = {"study": STUDY, "status": "FROZEN BEFORE ANY PHYS_DISCOVERY OUTCOME", "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "parent_commit": SMM._git("rev-parse", "HEAD"), "response": RESPONSE, "z_surprise": Z_SURPRISE, "m_local": M_LOCAL, "arms": list(ARMS),
           "family": "top decile of the population's observed response (evaluator-only); secondary bottom decile",
           "validation": {"status": val["status"], "sha256": SMM.sha256(VALIDATION)}, "code_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in CODE}}
    MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8"); print(json.dumps({k: man[k] for k in ("status", "written_utc")}, indent=1))


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "evaluate"
    {"validate": validate, "manifest": write_manifest, "work": lambda: work(sys.argv[2:]), "evaluate": evaluate}[step]()
