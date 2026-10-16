"""TEMPORAL_STRUCT (Study 3; owner approval of 2026-10-17; Ioan, 2026-10-15: "try the temporal Gaussians for the monitor data
... 5d and time is a dimension ... maybe you'll find some paper where they have some structure for the temporal dimension").

Channels (log, bin median over K = 40 equal bins of onset-normalised active-window time tau, as in pilot C): maximum melt
velocity, melt kinetic energy, melt-pool depth (max(0, -z_min)).  Rows: post-onset valid active rows; non-finite values,
velocities > 100 m/s and non-positive values excluded from the bin statistic only.  A run without all 40 bins of a channel
is UNAVAILABLE for that channel (recorded).
Models (fixed; out-of-fold, DEV repeats 3-4, train = fold pool with all pool runs revealed: an upper bound, not acquisition):
  MEAN    per-bin training mean
  KRON    separable 5-D GP (Matern 3/2 ARD in x) (x) (Matern 3/2 in tau), exact Kronecker ML-II (pilot C's KronGP, unchanged)
          - the separable covariance of multi-output / dynamic emulators (Conti & O'Hagan 2010)
  PCA     basis emulator (Higdon et al. 2008): PCA of the centred training curves, k components reaching 95 % of the
          variance (k <= 10), one GP (Matern 3/2 ARD + white nugget, ML-II) per score, curves reconstructed; predictive
          variance from the score variances plus the discarded-component residual variance
  FULL5D  non-separable GP on (x, tau) jointly (Matern 3/2 ARD over all 5 dimensions + white nugget, ML-II) on every 4th
          bin (10 bins per run; NEW only, cost) - Ioan's literal "time is a dimension"; compared with KRON on the same bins
Decisive control for derived quantities: SCALAR = a direct GP (Matern 3/2 ARD + nugget) on the scalar itself.
Derived quantities (from each predicted curve and from the observed curve): T0 level (mean of the last 8 bins), peak height
(max bin value) and peak position (argmax bin).
Endpoints (fixed): curve RMSE and R2_curve = 1 - SSE_model / SSE_MEAN per channel and repeat; 90 % pointwise coverage
(KRON, PCA, FULL5D); derived-quantity RMSE (T0 level, peak height) and mean |peak-position error| in bins.
Verdicts: STRUCTURE HELPS for a channel iff PCA (or FULL5D) beats KRON on curve RMSE by >= 5 % in both repeats.
TEMPORAL BEATS SCALAR for a derived quantity iff the best temporal model's RMSE <= 0.95 x SCALAR's in both repeats; if SCALAR
is better, the temporal model adds nothing for that quantity.  Populations NEW and OLD reported separately.
Steps: python -m src.jdl_temporal_struct validate | manifest | run [--pop NEW|OLD]
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

import src.jdl_phys_al as PAL
import src.jdl_physical_data2 as PD2
import src.jdl_physical_pilot as PP
import src.jdl_stage_m as SMM
import src.jdl_temporal_vel as TV

STUDY = "TEMPORAL_STRUCT"
OUT = SMM.OUT / "temporal_struct"
MANIFEST = OUT / "TEMPORAL_STRUCT_MANIFEST.json"
VALIDATION = OUT / "TEMPORAL_STRUCT_VALIDATION.json"
K = TV.K_BINS
CHANNELS = ("velocity", "ke", "depth")
CODE = ("src/jdl_temporal_struct.py", "src/jdl_temporal_vel.py", "src/jdl_phys_al.py", "src/jdl_physical_pilot.py", "src/jdl_physical_data2.py", "src/jdl_stage_m.py")


def curves(pop, ids):
    W = pd.read_csv(PP.W19_DEPTH).set_index("sim_id")
    C = {c: np.full((len(ids), K), np.nan) for c in CHANNELS}; status = {c: [] for c in CHANNELS}
    for i, s in enumerate(ids):
        try:
            f = lambda ch: PAL.load_monitor(PD2.local(s, ch, pop), ch)[0]      # Week 7 known malformed-token rule for bounds files
            t = f("time.dat") * 1e3; z = f("position-bounds_melt.dat")[:, 4]; cut = float(W.loc[s, "active_cutoff_ms"]) if s in W.index else np.nan
            ser = {"velocity": f("maximum-velocity_melt.dat"), "ke": f("kinetic-energy_melt.dat") * 1e9}
        except (FileNotFoundError, KeyError, ValueError) as e:
            for c in CHANNELS:
                status[c].append(f"UNAVAILABLE: {type(e).__name__}")
            continue
        valid = np.isfinite(z) & (np.abs(z) < PP.SENT); ser["depth"] = np.where(valid, np.maximum(0, -z) * 1e6, np.nan)
        for c in CHANNELS:
            v = ser[c]
            if not (len(t) == len(z) == len(v)) or not np.isfinite(cut):
                status[c].append("UNAVAILABLE: row counts or cutoff"); continue
            act = valid & (t <= cut) & np.isfinite(v) & (v > 0) & ((v <= PP.V_PLAUSIBLE_MAX) if c == "velocity" else True)
            if act.sum() < 4 * K:
                status[c].append("UNAVAILABLE: few rows"); continue
            ta = t[act]; tau = (ta - ta[0]) / max(1e-12, ta[-1] - ta[0]); b = np.minimum(K - 1, (tau * K).astype(int)); lv = np.log(v[act])
            row = np.array([np.median(lv[b == k]) if np.any(b == k) else np.nan for k in range(K)])
            if np.isfinite(row).all():
                C[c][i] = row; status[c].append("ok")
            else:
                status[c].append("UNAVAILABLE: empty bin")
    return C, status


def pca_fit_predict(Ztr, Ytr, Zte):
    mu = Ytr.mean(0); R = Ytr - mu; U, S, Vt = np.linalg.svd(R, full_matrices=False); ev = S ** 2 / max(1e-12, np.sum(S ** 2))
    k = int(min(10, np.searchsorted(np.cumsum(ev), 0.95) + 1)); scores = R @ Vt[:k].T; resid_var = float(np.sum((R - scores @ Vt[:k]) ** 2) / R.size)
    M, V = np.zeros((len(Zte), k)), np.zeros((len(Zte), k))
    for j in range(k):
        g = PAL.gp_fit(Ztr, scores[:, j]); m, s = g.predict(Zte, return_std=True); M[:, j], V[:, j] = m, s ** 2
    mean = mu + M @ Vt[:k]; var = V @ (Vt[:k] ** 2) + resid_var
    return mean, var, k


def full5d_fit_predict(Ztr, Ytr, Zte, every=4):
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
    idx = np.arange(0, K, every); tau = (idx + 0.5) / K
    Xa = np.vstack([np.c_[np.repeat(Ztr[i:i + 1], len(idx), 0), tau] for i in range(len(Ztr))]); ya = Ytr[:, idx].reshape(-1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        g = GaussianProcessRegressor(ConstantKernel(1.0, (1e-3, 1e3)) * Matern(np.ones(5), (1e-2, 1e2), nu=1.5) + WhiteKernel(0.1, (1e-6, 10.0)),
                                     normalize_y=True, n_restarts_optimizer=0, random_state=0).fit(Xa, ya)
    Xs = np.vstack([np.c_[np.repeat(Zte[i:i + 1], len(idx), 0), tau] for i in range(len(Zte))]); m, s = g.predict(Xs, return_std=True)
    return m.reshape(len(Zte), len(idx)), (s ** 2).reshape(len(Zte), len(idx)), idx


def derived(Y):
    return Y[:, -8:].mean(1), Y.max(1), Y.argmax(1)


def run(pop="NEW"):
    T = {(t["repeat"], t["fold"]): t for t in PAL.tasks(pop)}; ids = np.asarray(next(iter(T.values()))["ids"]).astype(str)
    t0 = time.time(); C, status = curves(pop, list(ids)); idx = {s: i for i, s in enumerate(ids)}; tau = (np.arange(K) + 0.5) / K; rows, cost = [], []
    for (rep, fold), t in sorted(T.items()):
        std = SMM.standardizer(t)[0]; sid = np.asarray(t["ids"]).astype(str)
        for c in CHANNELS:
            Y = C[c]; tr = [i for i in t["pool"] if np.isfinite(Y[idx[sid[i]]]).all()]; te = [i for i in t["test"] if np.isfinite(Y[idx[sid[i]]]).all()]
            if len(tr) < 20 or not te:
                continue
            Ytr, Yte = Y[[idx[sid[i]] for i in tr]], Y[[idx[sid[i]] for i in te]]; Ztr, Zte = std(t["X"][tr]), std(t["X"][te])
            preds = {"MEAN": (np.broadcast_to(Ytr.mean(0), Yte.shape), None)}
            ts = time.time(); kg = TV.KronGP(Ztr, tau).fit(Ytr); m, v = kg.predict(Zte); preds["KRON"] = (m, v); cost.append({"pop": pop, "rep": rep, "fold": fold, "channel": c, "model": "KRON", "s": time.time() - ts})
            ts = time.time(); m, v, kk = pca_fit_predict(Ztr, Ytr, Zte); preds["PCA"] = (m, v); cost.append({"pop": pop, "rep": rep, "fold": fold, "channel": c, "model": "PCA", "s": time.time() - ts, "k": kk})
            f5 = None
            if pop == "NEW":
                ts = time.time(); m5, v5, sub = full5d_fit_predict(Ztr, Ytr, Zte); f5 = (m5, v5, sub); cost.append({"pop": pop, "rep": rep, "fold": fold, "channel": c, "model": "FULL5D", "s": time.time() - ts})
            dtr, dte = derived(Ytr), derived(Yte); scal = []
            for q in range(2):
                g = PAL.gp_fit(Ztr, dtr[q]); scal.append(g.predict(Zte))
            for j, i in enumerate(te):
                r = {"pop": pop, "repeat": rep, "fold": fold, "channel": c, "sim_id": sid[i], "corner": float(t["X"][i][1]) > SMM.FAST_VX,
                     "obs_T0": float(dte[0][j]), "obs_peak": float(dte[1][j]), "obs_peakpos": int(dte[2][j]),
                     "SCALAR_T0": float(scal[0][j]), "SCALAR_peak": float(scal[1][j])}
                for mname, (m, v) in preds.items():
                    dm = derived(m[j:j + 1]); r.update({f"{mname}_sse": float(np.sum((Yte[j] - m[j]) ** 2)), f"{mname}_T0": float(dm[0][0]), f"{mname}_peak": float(dm[1][0]),
                                                         f"{mname}_peakpos": int(dm[2][0])})
                    if v is not None:
                        r[f"{mname}_cover90"] = float(np.mean(np.abs(Yte[j] - m[j]) <= 1.645 * np.sqrt(v[j])))
                if f5 is not None:
                    m5, v5, sub = f5; r["FULL5D_sse_sub"] = float(np.sum((Yte[j, sub] - m5[j]) ** 2)); r["KRON_sse_sub"] = float(np.sum((Yte[j, sub] - preds["KRON"][0][j, sub]) ** 2))
                    r["MEAN_sse_sub"] = float(np.sum((Yte[j, sub] - preds["MEAN"][0][j, sub]) ** 2)); r["FULL5D_cover90"] = float(np.mean(np.abs(Yte[j, sub] - m5[j]) <= 1.645 * np.sqrt(v5[j])))
                rows.append(r)
        print(json.dumps({"pop": pop, "rep": rep, "fold": fold, "s": round(time.time() - t0, 1)}), flush=True)
    D, Cst = pd.DataFrame(rows), pd.DataFrame(cost); res = {"pop": pop, "status": {c: pd.Series(status[c]).value_counts().to_dict() for c in CHANNELS}, "channels": {}}
    for c in CHANNELS:
        d = D[D.channel == c]
        if not len(d):
            continue
        per = {}
        for rep in (3, 4):
            x = d[d.repeat == rep]; n = len(x)
            e = {m: float(np.sqrt(x[f"{m}_sse"].sum() / (n * K))) for m in ("MEAN", "KRON", "PCA")}
            e.update({f"R2_curve_{m}": float(1 - x[f"{m}_sse"].sum() / x.MEAN_sse.sum()) for m in ("KRON", "PCA")})
            e.update({f"cover90_{m}": float(x[f"{m}_cover90"].mean()) for m in ("KRON", "PCA")})
            if "FULL5D_sse_sub" in x:
                e.update({"R2_sub_FULL5D": float(1 - x.FULL5D_sse_sub.sum() / x.MEAN_sse_sub.sum()), "R2_sub_KRON": float(1 - x.KRON_sse_sub.sum() / x.MEAN_sse_sub.sum()),
                          "cover90_FULL5D": float(x.FULL5D_cover90.mean())})
            for q in ("T0", "peak"):
                for m in ("MEAN", "KRON", "PCA", "SCALAR"):
                    e[f"rmse_{q}_{m}"] = float(np.sqrt(np.mean((x[f"obs_{q}"] - x[f"{m}_{q}"]) ** 2)))
            for m in ("MEAN", "KRON", "PCA"):
                e[f"peakpos_err_{m}"] = float(np.mean(np.abs(x.obs_peakpos - x[f"{m}_peakpos"])))
            per[rep] = e
        v = {"per_repeat": per}
        v["STRUCTURE_HELPS_PCA_over_KRON"] = all(per[r]["PCA"] <= 0.95 * per[r]["KRON"] for r in (3, 4))
        if all("R2_sub_FULL5D" in per[r] for r in (3, 4)):
            v["FULL5D_beats_KRON_on_subgrid"] = all(per[r]["R2_sub_FULL5D"] > per[r]["R2_sub_KRON"] for r in (3, 4))
        for q in ("T0", "peak"):
            best = min(("KRON", "PCA"), key=lambda m: np.mean([per[r][f"rmse_{q}_{m}"] for r in (3, 4)]))
            v[f"TEMPORAL_BEATS_SCALAR_{q}"] = {"best_temporal": best, "verdict": all(per[r][f"rmse_{q}_{best}"] <= 0.95 * per[r][f"rmse_{q}_SCALAR"] for r in (3, 4))}
        res["channels"][c] = v
    res["cost"] = Cst.groupby("model").s.agg(["median", "sum"]).round(3).to_dict(orient="index") if len(Cst) else {}
    res["wall_seconds"] = time.time() - t0
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "results").mkdir(exist_ok=True)
    D.to_csv(OUT / "results" / f"per_run_{pop}.csv", index=False, lineterminator="\n"); Cst.to_csv(OUT / "results" / f"cost_{pop}.csv", index=False, lineterminator="\n")
    (OUT / "results" / f"TEMPORAL_STRUCT_RESULTS_{pop}.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("pop", "status", "cost", "wall_seconds")}, indent=1, default=str))


def validate():
    t0 = time.time(); checks, info = {}, {}
    try:
        g = np.random.default_rng(6); Z = g.normal(0, 1, (30, 4)); tau = (np.arange(K) + 0.5) / K
        Y = np.sin(Z[:, :1] + 4 * tau[None, :]) + 0.3 * Z[:, 1:2] + 0.05 * g.normal(size=(30, K))
        m, v, k = pca_fit_predict(Z[:24], Y[:24], Z[24:]); checks["pca_emulator_runs"] = m.shape == (6, K) and np.isfinite(v).all() and 1 <= k <= 10
        R = Y[:24] - Y[:24].mean(0); U, S, Vt = np.linalg.svd(R, full_matrices=False); checks["pca_reconstruction_exact_with_all_components"] = bool(np.allclose((R @ Vt.T) @ Vt, R))
        m5, v5, sub = full5d_fit_predict(Z[:24], Y[:24], Z[24:]); checks["full5d_runs"] = m5.shape == (6, len(sub)) and np.isfinite(v5).all()
        ids = PD2.PD.new_ids()[:3]; C, st = curves("NEW", ids); checks["curves_three_channels_new"] = all(all(x == "ok" for x in st[c]) for c in CHANNELS)
        info["ok_counts_first3"] = {c: st[c] for c in CHANNELS}
        dmean, dpeak, dpos = derived(Y[:2]); checks["derived_definitions"] = np.allclose(dmean, Y[:2, -8:].mean(1)) and np.allclose(dpeak, Y[:2].max(1))
    except Exception as ex:
        checks["selftest_completed"] = False; info["error"] = f"{type(ex).__name__}: {ex}"[:400]; info["traceback"] = traceback.format_exc()[-2000:]
    res = {"study": STUDY, "status": "PASS" if checks and all(checks.values()) else "FAIL", "checks": {k: bool(v) for k, v in checks.items()}, "info": info,
           "seconds": time.time() - t0, "module_sha256": SMM.sha256(SMM.ROOT / "src" / "jdl_temporal_struct.py")}
    OUT.mkdir(parents=True, exist_ok=True); VALIDATION.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"status": res["status"], "checks": res["checks"], "info": {k: v for k, v in info.items() if k != "traceback"}}, indent=1, default=str))
    if res["status"] != "PASS":
        raise SystemExit(1)


def write_manifest():
    val = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if val["status"] != "PASS" or val["module_sha256"] != SMM.sha256(SMM.ROOT / "src" / "jdl_temporal_struct.py"):
        raise SystemExit("TEMPORAL_STRUCT validation must PASS with this module before the freeze")
    man = {"study": STUDY, "status": "FROZEN BEFORE ANY TEMPORAL_STRUCT OUTCOME", "written_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "parent_commit": SMM._git("rev-parse", "HEAD"), "channels": list(CHANNELS), "models": ["MEAN", "KRON", "PCA", "FULL5D (NEW only)", "SCALAR (derived control)"],
           "validation": {"status": val["status"], "sha256": SMM.sha256(VALIDATION)}, "code_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in CODE}}
    MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8"); print(json.dumps({k: man[k] for k in ("status", "written_utc")}, indent=1))


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "run"
    pop_arg = sys.argv[sys.argv.index("--pop") + 1] if "--pop" in sys.argv else "NEW"
    {"validate": validate, "manifest": write_manifest, "run": lambda: run(pop_arg)}[step]()
