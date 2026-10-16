"""PHYS_AL (Study 1; owner approval of 2026-10-17; Ioan: "try to fit other quantities ... energy or temperature"):
active learning of physical outputs from x = (P, VX, LS, ST).

Question.  How many paid simulations does each acquisition need to learn a physical output to a fixed accuracy, at the
same budget and with every query counted?  Does one shared acquisition for all outputs (one simulation reveals all its
monitors) cost accuracy relative to target-specific acquisition?  Does a joint multi-output GP (ICM) learn faster than
independent GPs on the same paid sets?
Targets (fixed; units in the name; NEW values from pilot B's frozen physical_summaries.csv and Week 19 depth_definitions):
  T1 log_A_um            log active-window maximum depth (E1's response)
  T2 log_ke_T0_nJ        log median melt kinetic energy over T0
  T3 vmax_spike_logratio log(p99.9/median) maximum melt velocity, post-onset active window
  T4 vmax_spike_us       time with velocity > 2 x median, microseconds
  T5 laser_T0_W          mean transferred laser power over T0
  T6 tmax_T0_K           median maximum melt temperature over T0
  secondary (new channels, learnability reported first): T7 log_etot_T0_J (mean total melt energy over T0),
  T8 log_npart_T0 (median melt particle number over T0, a melt-pool size proxy)
Populations, never pooled: NEW (136) and OLD (405; same extraction code on the pinned OLD monitors).  Splits: DEV repeats 3-4,
folds 1-5 (NEW: TRAINED_AL tasks; OLD: Stage M task builder, feature-only maximin paths from SMM.make_paths, label-free).
Start: first 8 points of the frozen feature-only maximin path.  Budgets B8-B60.  A target value that is unavailable for a paid
run is skipped for that target (QC; logged), never imputed; the run still counts as paid.
Model (every arm): GP Matern 3/2 ARD + white nugget on fold-standardised log inputs, normalize_y, ML-II, no restarts.
Arms (single target): RANDOM (seed independent of the target), MAXIMIN (frozen path continuation), MAXVAR (argmax predictive
sd), IVR (argmax integrated variance reduction over the fold pool, closed form with the fitted hyperparameters).
Arm MO_MAXVAR (all targets at once): argmax over candidates of sum_t var_t(c) / var(paid y_t).
Joint model ICM (secondary): B (x) Kx with per-output noise (whitened Kronecker, exact), B = w w' + diag(kappa), shared Matern
3/2 ARD; compared with independent GPs on the identical RANDOM, MAXIMIN and MO_MAXVAR paths at grid budgets 8..60 step 4.
Endpoints (fixed):
  R2(b) = 1 - SSE_b / SSE_ref on the pooled test predictions of each repeat (SSE_ref = deviations from the population mean;
  evaluator-only normalisation).  R2-AULC over B8-B60; paired simulation bootstrap (2000, class-stratified, seed 20261013).
  Attainable accuracy R2_full(t) = pooled out-of-fold R2 with the whole fold pool paid; a target is LEARNABLE if R2_full >= 0.5.
  Target level = 0.9 x R2_full(t).  Budget-to-target per repeat = first grid budget with R2 >= target there and at the next
  grid budget (sustained), right-censored at 64.
  "FEWER SIMULATIONS (DEV)" for an arm and target iff it reaches the level in both repeats and at least 4 queries before BOTH
  RANDOM and MAXIMIN in both repeats (censored references count as 64).  "SAME-BUDGET GAIN (DEV)" iff R2-AULC minus the better
  of RANDOM / MAXIMIN >= +0.02 with the bootstrap interval > 0 and both repeats positive.  Otherwise no claim.
Steps: python -m src.jdl_phys_al validate | manifest | extract | work [--pop NEW|OLD] | icm [--pop NEW|OLD] | evaluate
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
from scipy.optimize import minimize

import src.jdl_physical_data2 as PD2
import src.jdl_physical_pilot as PP
import src.jdl_stage_m as SMM
import src.jdl_trained_al as TA

STUDY = "PHYS_AL"
VERSION = "1.1"
REPAIRS = ["1.1 (2026-10-16 23:21 UTC, before any outcome): the frozen 1.0 extraction crashed on an OLD position-bounds file containing "
           "the token 's3.402823e+38'.  Position-bounds files now use Week 7's load_numeric (the supervisor-confirmed rule for that exact "
           "token; any other malformed token still raises), and a remaining per-run parse error is recorded as UNAVAILABLE.  No target, "
           "arm, endpoint or setting changed."]
OUT = SMM.OUT / "phys_al"
CACHE = SMM.OUT / "_cache" / "phys_al"
MANIFEST = OUT / "PHYS_AL_MANIFEST.json"
VALIDATION = OUT / "PHYS_AL_VALIDATION.json"
PRIMARY = ("log_A_um", "log_ke_T0_nJ", "vmax_spike_logratio", "vmax_spike_us", "laser_T0_W", "tmax_T0_K")
SECONDARY = ("log_etot_T0_J", "log_npart_T0")
SINGLE_ARMS = ("RANDOM", "MAXIMIN", "MAXVAR", "IVR")
REPEATS, FOLDS, B0, B1 = (3, 4), (1, 2, 3, 4, 5), 8, 60
GRID = tuple(range(8, 61, 4))
UNIT_TIME_LIMIT_S = 1800
CODE = ("src/jdl_phys_al.py", "src/jdl_physical_data2.py", "src/jdl_physical_data.py", "src/jdl_physical_pilot.py", "src/jdl_trained_al.py",
        "src/jdl_stage_m.py", "src/jdl_evaluate.py", "src/week7_phase2_sph_v2_physical_target_extraction.py")


# ======================================================================================== targets
def _summ_extra(t_s, zmin, etot, npart, cutoff_ms):
    t = np.asarray(t_s, float) * 1e3; valid = np.isfinite(zmin) & (np.abs(zmin) < PP.SENT); act = valid & (t <= cutoff_ms)
    out = {"log_etot_T0_J": np.nan, "log_npart_T0": np.nan}
    if act.sum() < 50:
        return out
    ia = np.flatnonzero(act); T0 = act & (t >= t[ia[0]] + 0.8 * (t[ia[-1]] - t[ia[0]]))
    if T0.sum() < 50:
        T0 = np.zeros(len(t), bool); T0[ia[-50:]] = True
    e = np.asarray(etot, float)[T0]; e = e[np.isfinite(e) & (e > 0)]; n = np.asarray(npart, float)[T0]; n = n[np.isfinite(n) & (n > 0)]
    if len(e):
        out["log_etot_T0_J"] = float(np.log(np.mean(e)))
    if len(n):
        out["log_npart_T0"] = float(np.log(np.median(n)))
    return out


def load_monitor(path, channel):
    """v1.1 repair: position-bounds files go through Week 7's load_numeric (the supervisor-confirmed rule for the exact
    malformed token 's3.402823e+38' -> ordinary no-melt sentinel; any other malformed token still raises); other channels
    unchanged (numpy.loadtxt)."""
    if channel == "position-bounds_melt.dat":
        from src.week7_phase2_sph_v2_physical_target_extraction import load_numeric
        v, audit = load_numeric(path, channel)
        return v, int(audit.get("known_malformed_no_melt_sentinel_count", 0) or 0)
    return PP._load(path), 0


def extract():
    """Primary targets for OLD (pilot B's summarize, unchanged) and secondary targets for both populations."""
    W = pd.read_csv(PP.W19_DEPTH).set_index("sim_id"); rows = []; t0 = time.time()
    pops = [("NEW", s) for s in PD2.PD.new_ids()] + [("OLD", s) for s in PD2.old_ids()]
    for k, (pop, s) in enumerate(pops):
        rec = {"population": pop, "sim_id": s}; fixes = []
        try:
            def f(c):
                v, n = load_monitor(PD2.local(s, c, pop), c); fixes.append(n); return v
            t = f("time.dat"); z = f("position-bounds_melt.dat")[:, 4]; cut = float(W.loc[s, "active_cutoff_ms"]) if s in W.index else np.nan
            ex = {c: f(c) for c in ("total-energy_melt.dat", "particle-number_melt.dat")}
            if pop == "OLD":
                ch = {c: f(c) for c in ("maximum-velocity_melt.dat", "kinetic-energy_melt.dat", "transferred-laser-power_melt.dat", "maximum-temperature_melt.dat")}
            n = {len(t), len(z), *(len(v) for v in ex.values()), *((len(v) for v in ch.values()) if pop == "OLD" else ())}
            if len(n) != 1 or not np.isfinite(cut):
                rec["status"] = "UNAVAILABLE: row counts differ or no cutoff"; rows.append(rec); continue
            rec.update(_summ_extra(t, z, ex["total-energy_melt.dat"], ex["particle-number_melt.dat"], cut))
            if pop == "OLD":
                summ, qc = PP.summarize(t, z, ch["maximum-velocity_melt.dat"], ch["kinetic-energy_melt.dat"], ch["transferred-laser-power_melt.dat"],
                                        ch["maximum-temperature_melt.dat"], cut)
                rec.update({"status": qc.pop("reason", "ok"), **qc, **summ})
            else:
                rec["status"] = "ok"
        except FileNotFoundError as e:
            rec["status"] = f"UNAVAILABLE: {e}"[:200]
        except ValueError as e:                                                # any other malformed token: recorded, never repaired
            rec["status"] = f"UNAVAILABLE: parse error {e}"[:200]
        rec["known_malformed_sentinel_replacements"] = int(sum(fixes))
        rows.append(rec)
        if (k + 1) % 50 == 0:
            print(json.dumps({"extracted": k + 1, "of": len(pops), "s": round(time.time() - t0, 1)}), flush=True)
    D = pd.DataFrame(rows); OUT.mkdir(parents=True, exist_ok=True); D.to_csv(OUT / "extracted_summaries.csv", index=False, lineterminator="\n")
    print(json.dumps({"rows": len(D), "status": D.groupby(["population", "status"]).size().to_dict(), "s": time.time() - t0}, default=str))


def targets(pop):
    """sim_id -> target table (NaN where unavailable)."""
    W = pd.read_csv(PP.W19_DEPTH).set_index("sim_id")
    ex = pd.read_csv(OUT / "extracted_summaries.csv") if (OUT / "extracted_summaries.csv").exists() else pd.DataFrame(columns=["population", "sim_id"])
    ex = ex[ex.population == pop].set_index("sim_id")
    if pop == "NEW":
        S = pd.read_csv(SMM.OUT / "physical" / "physical_summaries.csv").set_index("sim_id")
    else:
        S = ex
    T = pd.DataFrame(index=S.index)
    A = W.reindex(S.index)["A_active_max_um"]
    T["log_A_um"] = np.log(A.where(A > 0))
    T["log_ke_T0_nJ"] = np.log(S["ke_T0_med_nJ"].where(S["ke_T0_med_nJ"] > 0)) if "ke_T0_med_nJ" in S else np.nan
    for c, src in (("vmax_spike_logratio", "vmax_spike_logratio"), ("vmax_spike_us", "vmax_spike_us"), ("laser_T0_W", "laser_T0_mean_W"), ("tmax_T0_K", "tmax_T0_med_K")):
        T[c] = S[src] if src in S else np.nan
    for c in SECONDARY:
        T[c] = ex.reindex(T.index)[c] if c in ex.columns else np.nan
    return T


def tasks(pop):
    if pop == "NEW":
        return TA.build_tasks()
    old = SMM.REPEATS; SMM.REPEATS = REPEATS
    try:
        T = [t for t in SMM.build_tasks() if t["population"] == "OLD"]
    finally:
        SMM.REPEATS = old
    SMM.make_paths(T)                                                          # label-free feature-only maximin order (seed + [2])
    return T


# ======================================================================================== GP pieces
def gp_fit(Z, y):
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return GaussianProcessRegressor(ConstantKernel(1.0, (1e-3, 1e3)) * Matern(np.ones(Z.shape[1]), (1e-2, 1e2), nu=1.5) + WhiteKernel(0.1, (1e-6, 10.0)),
                                        normalize_y=True, n_restarts_optimizer=0, random_state=0).fit(Z, y)


def ivr_scores(gp, Zp, Zc, Zpool):
    """Integrated variance reduction over the pool for each candidate (latent posterior, fitted hyperparameters):
    sum_j cov_post(j, c)^2 / (var_post(c) + noise)."""
    k = gp.kernel_; noise = float(np.exp(k.theta[-1])) if hasattr(k, "theta") else 0.0
    kern = k.k1                                                                # C * Matern (without the white kernel)
    K = kern(Zp) + noise * np.eye(len(Zp)); Kinv = np.linalg.inv(K)
    kc, kp = kern(Zc, Zp), kern(Zpool, Zp)
    cov = kern(Zpool, Zc) - kp @ Kinv @ kc.T                                   # (npool, nc)
    vc = np.diag(kern(Zc)) - np.einsum("ij,jk,ik->i", kc, Kinv, kc)
    return np.sum(cov ** 2, axis=0) / (np.maximum(vc, 1e-12) + noise)


def run_traj(task, pop, arm, target, Tt, deadline=None):
    """One trajectory.  target: a target name (single-target MAXVAR / IVR), 'ALL' (target-independent RANDOM / MAXIMIN paths,
    every available target predicted) or 'MO' (MO_MAXVAR: acquisition over PRIMARY, every available target predicted)."""
    X, ids, pool, test = task["X"], np.asarray(task["ids"]).astype(str), task["pool"], task["test"]
    std = SMM.standardizer(task)[0]; Z = np.zeros((len(X), 4)); Z[pool] = std(X[pool]); Z[test] = std(X[test])
    cols = (list(PRIMARY) + [c for c in SECONDARY if Tt[c].notna().any()]) if target in ("MO", "ALL") else [target]
    Y = Tt.reindex(ids)[cols].to_numpy(float)
    rng = np.random.default_rng(31000 + 100 * task["repeat"] + task["fold"] + (17 if pop == "OLD" else 0))
    L = [int(i) for i in task["path"][:B0]]; evals, steps = [], []; t0 = time.time(); status = "ok"
    for b in range(B0, B1 + 1):
        if deadline is not None and time.time() > deadline:
            status = f"TIME_LIMIT at B{b}"; break
        ts = time.time(); unpaid = np.setdiff1d(pool, L); pred, gps = {}, {}
        for j, c in enumerate(cols):
            ok = np.isfinite(Y[L, j]); Lj = np.asarray(L)[ok]
            if len(Lj) < 3:
                pred[c] = None; continue
            g = gp_fit(Z[Lj], Y[Lj, j]); gps[c] = (g, Lj)
            pred[c] = g.predict(Z[test]).tolist()
        evals.append({"budget": b, "pred": pred}); steps.append({"budget": b, "fit_seconds": time.time() - ts})
        if b == B1:
            break
        if arm == "MAXIMIN":
            nxt = int([i for i in task["path"] if i not in set(L)][0])
        elif arm == "RANDOM":
            nxt = int(rng.choice(unpaid))
        elif arm == "MAXVAR" and gps:
            g, _ = gps[cols[0]]; sd = g.predict(Z[unpaid], return_std=True)[1]; nxt = int(unpaid[int(np.argmax(sd))])
        elif arm == "IVR" and gps:
            g, Lj = gps[cols[0]]; sc = ivr_scores(g, Z[Lj], Z[unpaid], Z[pool]); nxt = int(unpaid[int(np.argmax(sc))])
        elif arm == "MO_MAXVAR" and gps:
            s = np.zeros(len(unpaid))
            for c, (g, Lj) in gps.items():
                if c not in PRIMARY:
                    continue
                sd = g.predict(Z[unpaid], return_std=True)[1]; s += sd ** 2 / max(1e-12, np.var(Y[Lj, cols.index(c)]))
            nxt = int(unpaid[int(np.argmax(s))])
        else:                                                                  # too few usable values: label-free continuation
            nxt = int([i for i in task["path"] if i not in set(L)][0])
        L.append(nxt); steps[-1]["selected"] = ids[nxt]
    return {"population": pop, "repeat": task["repeat"], "fold": task["fold"], "arm": arm, "target": target, "paid": L, "paid_ids": [ids[i] for i in L],
            "test_ids": [ids[i] for i in test], "evals": evals, "steps": steps, "status": status, "seconds": time.time() - t0}


# ======================================================================================== ICM (exact, whitened Kronecker)
class ICM:
    """Y (n x m) isotopic; cov = B (x) Kx + D (x) I with B = w w' + diag(kappa), D = diag(noise); per-output standardisation."""

    def __init__(self, Z):
        self.Z = Z

    def _parts(self, p, m):
        ls = np.exp(p[:4]); w = p[4:4 + m]; kap = np.exp(p[4 + m:4 + 2 * m]); noi = np.exp(p[4 + 2 * m:4 + 3 * m])
        Kx = matern32(self.Z, self.Z, ls); B = np.outer(w, w) + np.diag(kap)
        Dm = np.diag(1 / np.sqrt(noi)); Bt = Dm @ B @ Dm
        eb, Ub = np.linalg.eigh(Bt); ex, Ux = np.linalg.eigh(Kx)
        lam = np.maximum(ex, 0)[:, None] * np.maximum(eb, 0)[None, :] + 1.0
        return ls, B, noi, Dm, Ub, Ux, lam, Kx

    def nlml(self, p, R):
        n, m = R.shape; ls, B, noi, Dm, Ub, Ux, lam, _ = self._parts(p, m)
        Rt = R @ Dm                                                            # whiten outputs
        A = Ux.T @ Rt @ Ub
        return 0.5 * float(np.sum(A ** 2 / lam) + np.sum(np.log(lam)) + n * np.sum(np.log(noi)) + n * m * np.log(2 * np.pi))

    def fit(self, Y):
        self.mu, self.sd = Y.mean(0), Y.std(0) + 1e-9; R = (Y - self.mu) / self.sd; m = R.shape[1]
        p0 = np.r_[np.zeros(4), np.full(m, 0.7), np.log(np.full(m, 0.3)), np.log(np.full(m, 0.1))]
        bounds = [(-4, 4)] * 4 + [(-5, 5)] * m + [(-8, 3)] * m + [(-10, 1)] * m
        r = minimize(self.nlml, p0, args=(R,), method="L-BFGS-B", bounds=bounds, options={"maxiter": 400})
        self.p, self.R, self.opt = r.x, R, {"nlml": float(r.fun), "success": bool(r.success), "nit": int(r.nit)}
        return self

    def predict(self, Zs):
        n, m = self.R.shape; ls, B, noi, Dm, Ub, Ux, lam, Kx = self._parts(self.p, m)
        Rt = self.R @ Dm; alpha = Ux @ ((Ux.T @ Rt @ Ub) / lam) @ Ub.T          # whitened (Kx (x) Bt + I)^-1 vec(Rt)
        Ksx = matern32(Zs, self.Z, ls)
        mean_w = Ksx @ alpha @ (Dm @ B @ Dm)                                   # in whitened output coordinates
        mean = mean_w @ np.linalg.inv(Dm)                                      # back to standardised outputs
        return mean * self.sd + self.mu


def matern32(A, Bm, ls):
    d = np.sqrt(np.maximum(0.0, (((A[:, None, :] - Bm[None, :, :]) / ls) ** 2).sum(-1)))
    return (1 + np.sqrt(3) * d) * np.exp(-np.sqrt(3) * d)


def icm_on_paths(pop):
    """ICM vs independent GPs on the identical target-independent paths (RANDOM, MAXIMIN, MO_MAXVAR) at the grid budgets."""
    Tt = targets(pop); T = {(t["repeat"], t["fold"]): t for t in tasks(pop)}; rows = []
    for arm in ("RANDOM", "MAXIMIN", "MO_MAXVAR"):
        for r in REPEATS:
            for f in FOLDS:
                key = "MO" if arm == "MO_MAXVAR" else "ALL"
                src = CACHE / f"{pop}__r{r}_f{f}__{arm}__{key}.json.gz"
                if not src.exists():
                    continue
                path = TA._read(src)["paid"]; t = T[(r, f)]; std = SMM.standardizer(t)[0]; ids = np.asarray(t["ids"]).astype(str)
                Y = Tt.reindex(ids)[list(PRIMARY)].to_numpy(float)
                for b in GRID:
                    Lb = [i for i in path[:b] if np.isfinite(Y[i]).all()]
                    if len(Lb) < 5:
                        continue
                    ts = time.time(); icm = ICM(std(t["X"][Lb])).fit(Y[Lb]); pm = icm.predict(std(t["X"][t["test"]])); sec = time.time() - ts
                    rows.append({"population": pop, "arm_path": arm, "repeat": r, "fold": f, "budget": b, "seconds": sec, "nit": icm.opt["nit"],
                                 "test_ids": [ids[i] for i in t["test"]], **{f"icm_{c}": pm[:, j].tolist() for j, c in enumerate(PRIMARY)}})
    OUT.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT / f"icm_predictions_{pop}.json.gz", "wt", encoding="utf-8") as fh:
        json.dump(rows, fh)
    print(json.dumps({"icm_fits": len(rows), "seconds": float(sum(r["seconds"] for r in rows))}))


# ======================================================================================== units and workers
def units(pop):
    U = [("RANDOM", "ALL"), ("MAXIMIN", "ALL"), ("MO_MAXVAR", "MO")] + [(arm, t) for t in PRIMARY + SECONDARY for arm in ("MAXVAR", "IVR")]
    return [(pop, r, f, arm, t) for (arm, t) in U for r in REPEATS for f in FOLDS]


def work(argv=()):
    argv = list(argv); pop = argv[argv.index("--pop") + 1] if "--pop" in argv else "NEW"
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not SMM._git("log", "--format=%H", "--", str(MANIFEST.relative_to(SMM.ROOT)).replace("\\", "/")):
        raise SystemExit("commit the PHYS_AL manifest before any run")
    for c, h in man["code_sha256"].items():
        if SMM.sha256(SMM.ROOT / c) != h:
            raise SystemExit(f"{c} changed after the PHYS_AL freeze")
    Tt = targets(pop); T = {(t["repeat"], t["fold"]): t for t in tasks(pop)}
    CACHE.mkdir(parents=True, exist_ok=True); locks = CACHE / "locks"; locks.mkdir(exist_ok=True)
    for (p, r, f, arm, tg) in units(pop):
        if tg in SECONDARY and not Tt[tg].notna().any():
            continue                                                           # secondary target not extracted yet
        name = f"{p}__r{r}_f{f}__{arm}__{tg}"; out = CACHE / f"{name}.json.gz"
        if out.exists():
            continue
        lock = locks / f"{name}.lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
        try:
            t0 = time.time(); res = run_traj(T[(r, f)], p, arm, tg, Tt, deadline=t0 + UNIT_TIME_LIMIT_S)
            res.update({"study": STUDY, "unit": name, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
            TA._atomic_write(out, res); print(json.dumps({"unit": name, "status": res["status"], "s": round(res["seconds"], 1)}), flush=True)
        finally:
            lock.unlink(missing_ok=True)


# ======================================================================================== evaluation (frozen)
def _full_r2(pop, Tt):
    """Attainable accuracy: pooled out-of-fold R2 with the whole fold pool paid (per target, per repeat)."""
    out = {}
    for t in tasks(pop):
        std = SMM.standardizer(t)[0]; ids = np.asarray(t["ids"]).astype(str)
        for c in PRIMARY + SECONDARY:
            y = Tt.reindex(ids)[c].to_numpy(float); tr = [i for i in t["pool"] if np.isfinite(y[i])]; te = [i for i in t["test"] if np.isfinite(y[i])]
            if len(tr) < 10 or not te:
                continue
            g = gp_fit(std(t["X"][tr]), y[tr]); p = g.predict(std(t["X"][te]))
            out.setdefault((c, t["repeat"]), []).extend(zip([ids[i] for i in te], y[te], p))
    return out


def evaluate(pops=("NEW", "OLD")):
    import src.jdl_evaluate as EV
    res = {}
    for pop in pops:
        Tt = targets(pop); R = {}
        for p in CACHE.glob(f"{pop}__*.json.gz"):
            r = json.loads(gzip.decompress(p.read_bytes())); R[(r["repeat"], r["fold"], r["arm"], r["target"])] = r
        if not R:
            continue
        full = _full_r2(pop, Tt); res[pop] = {"targets": {}, "units": len(R)}
        for c in PRIMARY + SECONDARY:
            yall = Tt[c].dropna()
            if len(yall) < 10 or (c, REPEATS[0]) not in full:
                res[pop]["targets"][c] = {"available": False}; continue
            ref_mean = float(yall.mean())
            r2full = {}
            for rep in REPEATS:
                z = full[(c, rep)]; yy = np.array([v[1] for v in z]); pp = np.array([v[2] for v in z])
                r2full[rep] = float(1 - np.sum((yy - pp) ** 2) / np.sum((yy - ref_mean) ** 2))
            r2f = float(np.mean(list(r2full.values()))); level = 0.9 * r2f
            entry = {"R2_full_per_repeat": r2full, "R2_full": r2f, "learnable": r2f >= 0.5, "target_level": level, "arms": {}}
            arm_keys = [(a, c) for a in ("MAXVAR", "IVR")] + [("RANDOM", "ALL"), ("MAXIMIN", "ALL"), ("MO_MAXVAR", "MO")]
            curves = {}
            for (a, key) in arm_keys:
                for rep in REPEATS:
                    curve = {}
                    for b in range(B0, B1 + 1):
                        yy, pp = [], []
                        for f in FOLDS:
                            u = R.get((rep, f, a, key))
                            if u is None:
                                break
                            e = {x["budget"]: x for x in u["evals"]}.get(b)
                            if e is None or e["pred"].get(c) is None:
                                break
                            yv = Tt.reindex(u["test_ids"])[c].to_numpy(float); pv = np.asarray(e["pred"][c], float); ok = np.isfinite(yv)
                            yy.extend(yv[ok]); pp.extend(pv[ok])
                        else:
                            yy, pp = np.asarray(yy), np.asarray(pp)
                            curve[b] = float(1 - np.sum((yy - pp) ** 2) / np.sum((yy - ref_mean) ** 2))
                    curves[(a, rep)] = curve
            for (a, key) in arm_keys:
                per = []
                for rep in REPEATS:
                    cv = curves[(a, rep)]
                    if len(cv) != B1 - B0 + 1:
                        per.append(None); continue
                    bs = np.array(sorted(cv)); vs = np.array([cv[b] for b in bs])
                    hit = next((g for i, g in enumerate(GRID[:-1]) if cv.get(g, -9) >= level and cv.get(GRID[i + 1], -9) >= level), None)
                    per.append({"AULC": float(np.trapezoid(vs, bs) / (B1 - B0)), "budget_to_target": hit if hit is not None else 64, "censored": hit is None,
                                "R2_at": {b: round(cv[b], 4) for b in (8, 16, 24, 40, 60)}})
                entry["arms"][a] = per
            # verdicts against the better of RANDOM / MAXIMIN
            for a in ("MAXVAR", "IVR", "MO_MAXVAR"):
                pa = entry["arms"].get(a); pr, pm = entry["arms"].get("RANDOM"), entry["arms"].get("MAXIMIN")
                if not pa or any(x is None for x in pa + pr + pm):
                    continue
                d = [pa[i]["AULC"] - max(pr[i]["AULC"], pm[i]["AULC"]) for i in range(len(REPEATS))]
                fewer = all(not pa[i]["censored"] and pa[i]["budget_to_target"] <= min(pr[i]["budget_to_target"], pm[i]["budget_to_target"]) - 4 for i in range(len(REPEATS)))
                entry[f"{a}_verdict"] = {"AULC_minus_best_nonadaptive_per_repeat": d, "same_budget_gain": bool(np.mean(d) >= 0.02 and all(v > 0 for v in d)),
                                         "fewer_simulations": bool(fewer)}
            res[pop]["targets"][c] = entry
    # ICM vs independent on identical paths (if run)
    for pop in pops:
        f = OUT / f"icm_predictions_{pop}.json.gz"
        if not f.exists() or pop not in res:
            continue
        rows = json.load(gzip.open(f, "rt", encoding="utf-8")); Tt = targets(pop); R = {}
        for p in CACHE.glob(f"{pop}__*.json.gz"):
            r = json.loads(gzip.decompress(p.read_bytes())); R[(r["repeat"], r["fold"], r["arm"], r["target"])] = r
        comp = {}
        for row in rows:
            key = "MO" if row["arm_path"] == "MO_MAXVAR" else "ALL"; u = R.get((row["repeat"], row["fold"], row["arm_path"], key))
            if u is None:
                continue
            e = {x["budget"]: x for x in u["evals"]}.get(row["budget"])
            for c in PRIMARY:
                yv = Tt.reindex(row["test_ids"])[c].to_numpy(float); ok = np.isfinite(yv)
                if e is None or e["pred"].get(c) is None:
                    continue
                ind = np.asarray(e["pred"][c], float)
                k = (row["arm_path"], c, row["budget"]); d = comp.setdefault(k, {"sse_icm": 0.0, "sse_ind": 0.0, "n": 0})
                d["sse_icm"] += float(np.sum((yv[ok] - np.asarray(row[f"icm_{c}"])[ok]) ** 2)); d["sse_ind"] += float(np.sum((yv[ok] - ind[ok]) ** 2)); d["n"] += int(ok.sum())
        res[pop]["icm_vs_independent"] = {f"{a}|{c}|B{b}": {"rmse_icm": np.sqrt(v["sse_icm"] / max(1, v["n"])), "rmse_ind": np.sqrt(v["sse_ind"] / max(1, v["n"]))}
                                          for (a, c, b), v in sorted(comp.items())}
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "results").mkdir(exist_ok=True)
    (OUT / "results" / "PHYS_AL_RESULTS.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    return res


# ======================================================================================== validation
def validate():
    t0 = time.time(); checks, info = {}, {}
    try:
        g = np.random.default_rng(4); Zs = g.normal(0, 1, (12, 4)); ys = np.sin(Zs[:, 0]) + 0.1 * g.normal(size=12); Zc = g.normal(0, 1, (5, 4)); Zpool = np.vstack([Zs, Zc])
        gp = gp_fit(Zs, ys); sc = ivr_scores(gp, Zs, Zc, Zpool)
        k = gp.kernel_.k1; noise = float(np.exp(gp.kernel_.theta[-1]))
        def postvar(Ztr):
            K = k(Ztr) + noise * np.eye(len(Ztr)); kp = k(Zpool, Ztr); return np.diag(k(Zpool)) - np.einsum("ij,jk,ik->i", kp, np.linalg.inv(K), kp)
        base = postvar(Zs).sum(); bf = np.array([base - postvar(np.vstack([Zs, Zc[[j]]])).sum() for j in range(5)])
        checks["ivr_equals_bruteforce_variance_reduction"] = float(np.max(np.abs(sc - bf))) < 1e-8
        m = 3; Y = np.c_[np.sin(Zs[:, 0]), np.cos(Zs[:, 1]), Zs[:, 0] * 0.5] + 0.05 * g.normal(size=(12, 3)); icm = ICM(Zs); R = (Y - Y.mean(0)) / Y.std(0)
        p = np.r_[np.zeros(4), [0.5, 0.2, -0.3], np.log([0.4, 0.3, 0.2]), np.log([0.05, 0.1, 0.2])]
        ls, B, noi, *_ = icm._parts(p, m); Kx = matern32(Zs, Zs, ls); C = np.kron(Kx, B) + np.kron(np.eye(12), np.diag(noi)); r = R.reshape(-1)
        ref = 0.5 * (r @ np.linalg.solve(C, r) + np.linalg.slogdet(C)[1] + len(r) * np.log(2 * np.pi))
        checks["icm_nlml_equals_bruteforce"] = abs(icm.nlml(p, R) - ref) < 1e-7 * max(1, abs(ref))
        icm.p, icm.R, icm.mu, icm.sd = p, R, Y.mean(0), Y.std(0) + 1e-9
        pm = icm.predict(Zc); Ks = np.kron(matern32(Zc, Zs, ls), B); mb = (Ks @ np.linalg.solve(C, r)).reshape(5, m) * icm.sd + icm.mu
        checks["icm_mean_equals_bruteforce"] = float(np.max(np.abs(pm - mb))) < 1e-7
        Tt = targets("NEW"); checks["new_primary_targets_present"] = all(Tt[c].notna().sum() >= 130 for c in PRIMARY)
        info["new_target_counts"] = {c: int(Tt[c].notna().sum()) for c in PRIMARY + SECONDARY}
        T = {(t["repeat"], t["fold"]): t for t in tasks("NEW")}; t = T[(3, 1)]
        tt = time.time(); a = run_traj(t, "NEW", "IVR", "log_A_um", Tt); info["unit_seconds_IVR"] = time.time() - tt
        checks["trajectory_runs"] = a["status"] == "ok" and len(a["paid"]) == B1
        T2 = Tt.copy(); hid = set(np.asarray(t["ids"]).astype(str)) - set(a["paid_ids"]); T2.loc[T2.index.isin(hid)] = 1e6
        b2 = run_traj(t, "NEW", "IVR", "log_A_um", T2)
        checks["hidden_targets_do_not_change_path_or_predictions"] = a["paid"] == b2["paid"] and a["evals"][-1]["pred"] == b2["evals"][-1]["pred"]
        tt = time.time(); mo = run_traj(t, "NEW", "MO_MAXVAR", "MO", Tt); info["unit_seconds_MO"] = time.time() - tt
        checks["mo_trajectory_runs"] = mo["status"] == "ok" and all(mo["evals"][-1]["pred"][c] is not None for c in PRIMARY)
        r1, r2 = run_traj(t, "NEW", "RANDOM", "log_A_um", Tt), run_traj(t, "NEW", "RANDOM", "vmax_spike_us", Tt)
        checks["random_path_independent_of_target"] = r1["paid"] == r2["paid"]
        old = tasks("OLD"); checks["old_tasks_with_label_free_paths"] = len(old) == 10 and all(len(x["path"]) >= B1 for x in old)
        # v1.1 repair: the known malformed token is mapped to the no-melt sentinel; any other malformed token still raises
        import tempfile
        from pathlib import Path
        d = Path(tempfile.mkdtemp()); p1 = d / "position-bounds_melt.dat"
        p1.write_text("1e-4,2e-4,1e-4,2e-4,-5e-5,0\ns3.402823e+38,-3.402823e+38,3.402823e+38,-3.402823e+38,3.402823e+38,-3.402823e+38\n")
        v, n = load_monitor(p1, "position-bounds_melt.dat")
        checks["known_malformed_token_mapped_to_sentinel"] = n == 1 and v.shape == (2, 6) and abs(v[1, 0] - 3.402823e38) < 1e32
        p1.write_text("1e-4,2e-4,1e-4,2e-4,-5e-5,0\nx1.0,2,3,4,5,6\n")
        try:
            load_monitor(p1, "position-bounds_melt.dat"); checks["other_malformed_token_still_raises"] = False
        except ValueError:
            checks["other_malformed_token_still_raises"] = True
    except Exception as ex:
        checks["selftest_completed"] = False; info["error"] = f"{type(ex).__name__}: {ex}"[:400]; info["traceback"] = traceback.format_exc()[-2500:]
    res = {"study": STUDY, "status": "PASS" if checks and all(checks.values()) else "FAIL", "checks": {k: bool(v) for k, v in checks.items()}, "info": info,
           "seconds": time.time() - t0, "module_sha256": SMM.sha256(SMM.ROOT / "src" / "jdl_phys_al.py")}
    OUT.mkdir(parents=True, exist_ok=True); VALIDATION.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"status": res["status"], "checks": res["checks"], "info": {k: v for k, v in info.items() if k != "traceback"}}, indent=1, default=str))
    if res["status"] != "PASS":
        raise SystemExit(1)


def write_manifest():
    val = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if val["status"] != "PASS" or val["module_sha256"] != SMM.sha256(SMM.ROOT / "src" / "jdl_phys_al.py"):
        raise SystemExit("PHYS_AL validation must PASS with this module before the freeze")
    man = {"study": STUDY, "version": VERSION, "repairs": REPAIRS, "status": "FROZEN BEFORE ANY PHYS_AL OUTCOME", "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "parent_commit": SMM._git("rev-parse", "HEAD"), "targets_primary": list(PRIMARY), "targets_secondary": list(SECONDARY), "arms": list(SINGLE_ARMS) + ["MO_MAXVAR"],
           "budgets": [B0, B1], "grid": list(GRID), "populations": ["NEW", "OLD"], "repeats": list(REPEATS),
           "endpoints": "R2-AULC; attainable R2_full; level 0.9 x R2_full; sustained budget-to-target, censored at 64; FEWER SIMULATIONS / SAME-BUDGET GAIN rules as in the module docstring",
           "validation": {"status": val["status"], "sha256": SMM.sha256(VALIDATION)}, "code_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in CODE}}
    MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8"); print(json.dumps({k: man[k] for k in ("status", "written_utc")}, indent=1))


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "evaluate"
    pop_arg = sys.argv[sys.argv.index("--pop") + 1] if "--pop" in sys.argv else None
    {"validate": validate, "manifest": write_manifest, "extract": extract, "work": lambda: work(sys.argv[2:]),
     "icm": lambda: icm_on_paths(pop_arg or "NEW"), "evaluate": lambda: print(json.dumps({k: {"units": v.get("units")} for k, v in evaluate().items()}))}[step]()
