"""PHYSICAL_PILOT (pilot B; owner request of 2026-10-16): are physical outputs learnable from x = (P, VX, LS, ST)?

New question relative to Weeks 6/7: those learned steady-state T0 summaries (KE R2 0.89, depth 0.91; Matern 3/2 + learned
nugget) on the OLD-era data (sph_v2 @ d69dac5b).  Here: the October NEW population (pinned 2e1eec9c, 136 runs incl. the
fast-scan corner) and TRANSIENT summaries (short spike size / duration of melt velocity and kinetic energy, and their
timing relative to depth) next to steady-state energy / temperature / laser-power levels.
Definitions reused unchanged from src/week19_series.py: depth = max(0, -z_min) on valid bounds rows (sentinel 3.4e38 =
no melt); active window = valid rows with t <= active_cutoff_ms (= min(recording end, 0.9 x derived domain exit); Week 19
table depth_definitions.csv; startup retained); T0 = last 20 % of [first valid time, active cutoff]; hold rule dt_i =
t_{i+1} - t_i (last row holds 0).  If channel row counts differ from time.dat the time-dependent summaries of that run are
UNAVAILABLE (recorded, never truncated or repaired).  Non-finite values and implausible velocities are counted per run and
excluded only from the order statistics they would corrupt (counts reported; never a silent exclusion of a run).
Summaries (fixed before any summary or relation was computed; units in the name):
  S1 ke_T0_med_nJ           median melt kinetic energy over T0 (continuity with Week 7)
  S2 vmax_spike_logratio    log(p99.9 / median) of maximum melt velocity over the post-onset active window
  S3 vmax_spike_us          time with maximum melt velocity > 2 x its active-window median (hold rule), microseconds
  S4 ke_spike_logratio      log(p99.9 / median) of melt kinetic energy over the post-onset active window
  S5 lag_ke_to_depth_us     t(argmax depth) - t(argmax KE) inside the active window, microseconds
  S6 laser_T0_mean_W        mean transferred laser power to the melt over T0
  S7 tmax_T0_med_K          median maximum melt temperature over T0
Learnability (prediction error; the learner side): for each summary, out-of-fold predictions on the DEV repeat 3-4 folds
(train = fold pool, all pool runs revealed as a diagnostic), models: training mean, ridge on standardised log inputs, GP
Matern 3/2 (ARD) + learned white nugget (Week 7 protocol GP).  Metrics: RMSE, R2_oof = 1 - SSE_model / SSE_mean, relative
RMSE (/ median |y|), GP 90 % interval coverage, corner RMSE ratio GP / mean (corner = VX > 0.85, evaluator-only).
Verdict per summary (fixed): LEARNABLE if mean R2_oof >= 0.5 over repeats, WEAK if 0.2 <= R2 < 0.5, NOT LEARNABLE otherwise.
Separate diagnosis (evaluator side, never a learner input): AUC of the OBSERVED summary for Keyhole inside the corner, and AUC
of the OUT-OF-FOLD GP-PREDICTED summary inside the corner (what an x-only learner could carry).
Steps: python -m src.jdl_physical_pilot validate | manifest | extract | learn
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
import pandas as pd

import src.jdl_physical_data as PD
import src.jdl_stage_m as SMM
import src.jdl_trained_al as TA

STUDY = "PHYSICAL_PILOT"
OUT = SMM.OUT / "physical"
MANIFEST = OUT / "PHYSICAL_MANIFEST.json"
VALIDATION = OUT / "PHYSICAL_VALIDATION.json"
W19_DEPTH = SMM.ROOT / "outputs" / "week19_temporal_regime_audit" / "tables" / "depth_definitions.csv"
SENT = 1e30
V_PLAUSIBLE_MAX = 100.0        # m/s; rows above are counted as implausible and excluded from velocity order statistics
SUMMARIES = ("ke_T0_med_nJ", "vmax_spike_logratio", "vmax_spike_us", "ke_spike_logratio", "lag_ke_to_depth_us", "laser_T0_mean_W", "tmax_T0_med_K")
CODE = ("src/jdl_physical_pilot.py", "src/jdl_physical_data.py", "src/jdl_trained_al.py", "src/jdl_stage_m.py")


def _load(path):
    return np.loadtxt(path, delimiter=",", ndmin=1) if path.name.startswith("position") else np.loadtxt(path, ndmin=1)


def summarize(t_s, zmin_m, vmax, ke_J, laser_W, tmax_K, cutoff_ms):
    """Pure function of one run's monitor arrays (row-aligned) -> summaries + QC counts."""
    t = np.asarray(t_s, float) * 1e3                                   # ms
    valid = np.isfinite(zmin_m) & (np.abs(zmin_m) < SENT)
    depth = np.where(valid, np.maximum(0.0, -np.asarray(zmin_m, float)) * 1e6, np.nan)
    act = valid & (t <= cutoff_ms)
    qc = {"rows": len(t), "valid_rows": int(valid.sum()), "active_rows": int(act.sum()),
          "nonfinite_ke": int((~np.isfinite(ke_J)).sum()), "nonfinite_vmax": int((~np.isfinite(vmax)).sum()),
          "nonfinite_laser": int((~np.isfinite(laser_W)).sum()), "nonfinite_tmax": int((~np.isfinite(tmax_K)).sum()),
          "implausible_vmax_rows": int((np.isfinite(vmax) & (vmax > V_PLAUSIBLE_MAX)).sum())}
    out = {k: np.nan for k in SUMMARIES}
    if act.sum() < 50:
        qc["reason"] = "fewer than 50 active rows"; return out, qc
    ia = np.flatnonzero(act); t0w = t[ia[0]] + 0.8 * (t[ia[-1]] - t[ia[0]]); T0 = act & (t >= t0w)
    if T0.sum() < 50:
        T0 = np.zeros(len(t), bool); T0[ia[-50:]] = True
    dt_ = np.r_[np.diff(t), 0.0] * 1e3                                   # microseconds held by each row
    ke = np.asarray(ke_J, float) * 1e9
    kv = act & np.isfinite(ke); vv = act & np.isfinite(vmax) & (vmax <= V_PLAUSIBLE_MAX)
    if (T0 & np.isfinite(ke)).sum():
        out["ke_T0_med_nJ"] = float(np.median(ke[T0 & np.isfinite(ke)]))
    if vv.sum() > 50:
        med = np.median(vmax[vv]); p = np.percentile(vmax[vv], 99.9)
        if med > 0:
            out["vmax_spike_logratio"] = float(np.log(p / med)); out["vmax_spike_us"] = float(np.sum(dt_[vv & (vmax > 2 * med)]))
    if kv.sum() > 50:
        med = np.median(ke[kv]); p = np.percentile(ke[kv], 99.9)
        if med > 0:
            out["ke_spike_logratio"] = float(np.log(p / med))
        dd = np.where(act, depth, -np.inf); kk = np.where(kv, ke, -np.inf)
        out["lag_ke_to_depth_us"] = float((t[int(np.argmax(dd))] - t[int(np.argmax(kk))]) * 1e3)
    if (T0 & np.isfinite(laser_W)).sum():
        out["laser_T0_mean_W"] = float(np.mean(np.asarray(laser_W, float)[T0 & np.isfinite(laser_W)]))
    if (T0 & np.isfinite(tmax_K)).sum():
        out["tmax_T0_med_K"] = float(np.median(np.asarray(tmax_K, float)[T0 & np.isfinite(tmax_K)]))
    return out, qc


def extract():
    W = pd.read_csv(W19_DEPTH).set_index("sim_id")
    ids = PD.new_ids(); rows = []; t0 = time.time()
    for k, s in enumerate(ids):
        files = {c: PD.local(s, c) for c in ("time.dat", "position-bounds_melt.dat", "maximum-velocity_melt.dat", "kinetic-energy_melt.dat",
                                             "transferred-laser-power_melt.dat", "maximum-temperature_melt.dat")}
        arr = {c: _load(p) for c, p in files.items()}
        n = {c: len(a) for c, a in arr.items()}
        rec = {"sim_id": s, **{f"rows_{c.split('.')[0]}": v for c, v in n.items()}}
        cut = float(W.loc[s, "active_cutoff_ms"]) if s in W.index else np.nan
        rec["active_cutoff_ms"] = cut
        if len(set(n.values())) != 1 or not np.isfinite(cut):
            rec["status"] = "UNAVAILABLE: channel row counts differ from time.dat" if len(set(n.values())) != 1 else "UNAVAILABLE: no active cutoff"
            rec.update({k_: np.nan for k_ in SUMMARIES}); rows.append(rec); continue
        z = arr["position-bounds_melt.dat"][:, 4]
        summ, qc = summarize(arr["time.dat"], z, arr["maximum-velocity_melt.dat"], arr["kinetic-energy_melt.dat"], arr["transferred-laser-power_melt.dat"],
                             arr["maximum-temperature_melt.dat"], cut)
        rec.update({"status": qc.pop("reason", "ok"), **qc, **summ}); rows.append(rec)
        if (k + 1) % 20 == 0:
            print(json.dumps({"extracted": k + 1, "of": len(ids), "s": round(time.time() - t0, 1)}), flush=True)
    D = pd.DataFrame(rows); OUT.mkdir(parents=True, exist_ok=True)
    D.to_csv(OUT / "physical_summaries.csv", index=False, lineterminator="\n")
    qc = {"runs": len(D), "status_counts": D.status.value_counts().to_dict(), "nonfinite_ke_total": int(D.get("nonfinite_ke", pd.Series(dtype=float)).sum()),
          "runs_with_nonfinite_ke": int((D.get("nonfinite_ke", pd.Series(dtype=float)) > 0).sum()),
          "implausible_vmax_rows_total": int(D.get("implausible_vmax_rows", pd.Series(dtype=float)).sum()),
          "runs_with_implausible_vmax": int((D.get("implausible_vmax_rows", pd.Series(dtype=float)) > 0).sum()), "seconds": time.time() - t0}
    (OUT / "QC_SUMMARY.json").write_text(json.dumps(qc, indent=1, default=str), encoding="utf-8")
    print(json.dumps(qc, indent=1, default=str))


def _auc(s, y):
    s, y = np.asarray(s, float), np.asarray(y, int); ok = np.isfinite(s); s, y = s[ok], y[ok]
    P, N = s[y == 1], s[y == 0]
    if not len(P) or not len(N):
        return np.nan
    return float(np.mean((P[:, None] > N[None, :]) + 0.5 * (P[:, None] == N[None, :])))


def learn():
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
    from sklearn.linear_model import Ridge
    D = pd.read_csv(OUT / "physical_summaries.csv").set_index("sim_id")
    tasks = TA.build_tasks(); rows, oof, cost = [], [], []
    for t in tasks:
        std = SMM.standardizer(t)[0]; ids = np.asarray(t["ids"]).astype(str)
        tr, te = t["pool"], t["test"]
        for s in SUMMARIES:
            ytr, yte = D.loc[ids[tr], s].to_numpy(float), D.loc[ids[te], s].to_numpy(float)
            mtr, mte = np.isfinite(ytr), np.isfinite(yte)
            if mtr.sum() < 10 or not mte.any():
                continue
            Xtr, Xte = std(t["X"][tr][mtr]), std(t["X"][te][mte])
            pm = np.full(mte.sum(), ytr[mtr].mean())
            pr = Ridge(alpha=1e-2).fit(Xtr, ytr[mtr]).predict(Xte)
            ts = time.time()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                gp = GaussianProcessRegressor(ConstantKernel(1.0, (1e-3, 1e3)) * Matern(np.ones(4), (1e-2, 1e2), nu=1.5) + WhiteKernel(0.1, (1e-6, 10.0)),
                                              normalize_y=True, n_restarts_optimizer=0, random_state=0).fit(Xtr, ytr[mtr])
                pg, sg = gp.predict(Xte, return_std=True)
            cost.append({"summary": s, "repeat": t["repeat"], "fold": t["fold"], "gp_fit_s": time.time() - ts, "n_train": int(mtr.sum())})
            for sid, yy, a, b_, c, sd in zip(ids[te][mte], yte[mte], pm, pr, pg, sg):
                oof.append({"repeat": t["repeat"], "fold": t["fold"], "summary": s, "sim_id": sid, "y": yy, "mean": a, "ridge": b_, "gp": c, "gp_sd": sd})
    O = pd.DataFrame(oof)
    import src.jdl_trained_al_eval as TE
    _, F = TE.frame(); lab = dict(zip(np.asarray(F["ids"]).astype(str), F["y"])); vx = dict(zip(np.asarray(F["ids"]).astype(str), F["VX"]))
    O["label"] = O.sim_id.map(lab); O["corner"] = O.sim_id.map(vx) > SMM.FAST_VX
    for s in SUMMARIES:
        Os = O[O.summary == s]
        if not len(Os):
            rows.append({"summary": s, "verdict": "UNAVAILABLE"}); continue
        per = []
        for rep in (3, 4):
            o = Os[Os.repeat == rep]
            sse = {m: float(np.sum((o.y - o[m]) ** 2)) for m in ("mean", "ridge", "gp")}
            per.append({"rep": rep, "R2_ridge": 1 - sse["ridge"] / sse["mean"], "R2_gp": 1 - sse["gp"] / sse["mean"],
                        "rmse_mean": np.sqrt(sse["mean"] / len(o)), "rmse_ridge": np.sqrt(sse["ridge"] / len(o)), "rmse_gp": np.sqrt(sse["gp"] / len(o)),
                        "cover90_gp": float(np.mean(np.abs(o.y - o.gp) <= 1.645 * o.gp_sd)),
                        "corner_rmse_ratio_gp_over_mean": float(np.sqrt(np.mean((o.y[o.corner] - o.gp[o.corner]) ** 2)) / max(1e-12, np.sqrt(np.mean((o.y[o.corner] - o["mean"][o.corner]) ** 2))))})
        r2 = float(np.mean([p["R2_gp"] for p in per]))
        obs = Os[Os.repeat == 3].drop_duplicates("sim_id")
        rows.append({"summary": s, "R2_gp_r3": per[0]["R2_gp"], "R2_gp_r4": per[1]["R2_gp"], "R2_gp_mean": r2, "R2_ridge_mean": float(np.mean([p["R2_ridge"] for p in per])),
                     "rmse_gp_mean": float(np.mean([p["rmse_gp"] for p in per])), "rmse_trainmean_mean": float(np.mean([p["rmse_mean"] for p in per])),
                     "rel_rmse_gp": float(np.mean([p["rmse_gp"] for p in per]) / max(1e-12, np.median(np.abs(obs.y)))), "cover90_gp": float(np.mean([p["cover90_gp"] for p in per])),
                     "corner_rmse_ratio_gp_over_mean": float(np.mean([p["corner_rmse_ratio_gp_over_mean"] for p in per])),
                     "verdict": "LEARNABLE" if r2 >= 0.5 else "WEAK" if r2 >= 0.2 else "NOT LEARNABLE",
                     "DIAG_corner_AUC_observed": _auc(obs.y[obs.corner], obs.label[obs.corner]), "DIAG_corner_AUC_gp_predicted_oof": _auc(obs.gp[obs.corner], obs.label[obs.corner]),
                     "DIAG_all_AUC_observed": _auc(obs.y, obs.label), "n_corner": int(obs.corner.sum())})
    Rr = pd.DataFrame(rows); (OUT / "results").mkdir(parents=True, exist_ok=True)
    Rr.to_csv(OUT / "results" / "learnability.csv", index=False, lineterminator="\n"); O.to_csv(OUT / "results" / "oof_predictions.csv", index=False, lineterminator="\n")
    C = pd.DataFrame(cost); C.to_csv(OUT / "results" / "cost.csv", index=False, lineterminator="\n")
    print(Rr.round(3).to_string()); print("GP fit seconds: median %.3f, total %.1f" % (C.gp_fit_s.median(), C.gp_fit_s.sum()))


def validate():
    t0 = time.time(); checks, info = {}, {}
    try:
        n = 2000; t = np.arange(n) * 1e-8; z = np.where(np.arange(n) < 100, 3.4e38, -50e-6); z[1000:1010] = -150e-6
        v = np.full(n, 1.0); v[1500:1520] = 5.0; v[1700] = 500.0; ke = np.full(n, 1e-9); ke[990:1000] = 8e-9; ke[5] = np.nan
        lz = np.full(n, 10.0); tm = np.full(n, 2000.0)
        s, q = summarize(t, z, v, ke, lz, tm, cutoff_ms=1e3 * t[-1])
        checks["depth_peak_after_ke_peak_lag_positive"] = s["lag_ke_to_depth_us"] > 0
        checks["spike_duration_counts_held_time"] = abs(s["vmax_spike_us"] - 20 * 1e-8 * 1e6) < 1e-6
        checks["implausible_velocity_counted_not_used"] = q["implausible_vmax_rows"] == 1 and np.isfinite(s["vmax_spike_logratio"])
        checks["nonfinite_ke_counted"] = q["nonfinite_ke"] == 1
        checks["sentinel_rows_invalid"] = q["valid_rows"] == n - 100
        s2, q2 = summarize(t[:30], z[:30], v[:30], ke[:30], lz[:30], tm[:30], cutoff_ms=1.0)
        checks["too_short_window_unavailable"] = all(np.isnan(s2[k]) for k in SUMMARIES)
        ids = PD.new_ids(); checks["inventory_136_runs_verified"] = len(ids) == 136 and all(PD.local(ids[0], c).exists() for c in PD.CHANNELS + PD.LOCAL_CHANNELS)
        W = pd.read_csv(W19_DEPTH); checks["week19_active_cutoff_available_for_all_new"] = int(W[W.sim_id.isin(ids)].active_cutoff_ms.notna().sum()) >= 130
        info["cutoff_available"] = int(W[W.sim_id.isin(ids)].active_cutoff_ms.notna().sum())
    except Exception as ex:
        checks["selftest_completed"] = False; info["error"] = f"{type(ex).__name__}: {ex}"[:400]; info["traceback"] = traceback.format_exc()[-2000:]
    res = {"study": STUDY, "status": "PASS" if checks and all(checks.values()) else "FAIL", "checks": {k: bool(v) for k, v in checks.items()}, "info": info,
           "seconds": time.time() - t0, "module_sha256": SMM.sha256(SMM.ROOT / "src" / "jdl_physical_pilot.py")}
    OUT.mkdir(parents=True, exist_ok=True); VALIDATION.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"status": res["status"], "checks": res["checks"], "info": {k: v for k, v in info.items() if k != "traceback"}}, indent=1, default=str))
    if res["status"] != "PASS":
        raise SystemExit(1)


def write_manifest():
    val = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if val["status"] != "PASS" or val["module_sha256"] != SMM.sha256(SMM.ROOT / "src" / "jdl_physical_pilot.py"):
        raise SystemExit("PHYSICAL validation must PASS with this module before the freeze")
    man = {"study": STUDY, "status": "FROZEN BEFORE ANY SUMMARY WAS COMPUTED", "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "parent_commit": SMM._git("rev-parse", "HEAD"), "summaries": list(SUMMARIES), "v_plausible_max_m_s": V_PLAUSIBLE_MAX,
           "verdict_rule": "LEARNABLE if mean R2_oof >= 0.5 over repeats 3-4, WEAK if >= 0.2, else NOT LEARNABLE", "models": ["train mean", "ridge alpha 1e-2", "GP Matern 3/2 ARD + white nugget"],
           "validation": {"status": val["status"], "sha256": SMM.sha256(VALIDATION)}, "code_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in CODE}}
    MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8"); print(json.dumps({k: man[k] for k in ("status", "written_utc")}, indent=1))


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "learn"
    {"validate": validate, "manifest": write_manifest, "extract": extract, "learn": learn}[step]()
