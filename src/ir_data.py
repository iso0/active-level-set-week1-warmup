"""IR part P1 (PROTOCOL_IR.md section 2): melt-pool geometry, channel maxima and within-run time statistics per run; the paid-only
width reveal for learners. Read-only on the verified raw copy in the main checkout; no new simulation; POOLED_MANIFEST unchanged.

Per run (unchanged code paths):
  geometry  src.week19_series.process (bounds rows, valid mask, Week 19 active mask, T0 mask, first C/K frame, cutoff): depth A (must
            reproduce the pooled A_um, acceptance V1), W_A = active max of the y-extent, W_T0 = T0 median width, W_atA = width at the
            active depth maximum, L_A = active max of the x-extent
  channels  KE, maximum temperature, maximum velocity, transferred laser power, total energy, particle number through
            src.jdl_physical_data2.local (verified paths, both batches) and src.jdl_phys_al.load_monitor; a channel is used only
            when its row count equals time.dat (else UNAVAILABLE for that run); velocities > 100 m/s are implausible rows
            (excluded from that channel's statistics, counted)
  F1        Spearman rho over active valid rows between depth(t) and every other signal
  F2        lead-lag on the post-onset window [first C/K frame, cutoff], 1-us grid (linear interpolation of finite rows):
            tau* = argmax_{|tau| <= 100 us} corr(depth(t), s(t - tau)); levels (z-scored) and 20-us-smoothed first differences
  F3        Keyhole runs: event window [-100, +100] us around the first K frame (z-scored by the run's active-window mean / SD)
            and a random-time control window (uniform in the post-onset window, seed from the run id)
  F4        medians over the first 25 % of the active window (time from the first active row to the cutoff)
    python -m src.ir_data extract     (3 workers, single-thread)
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import concurrent.futures
import hashlib
import json
import sys
import time
import zlib

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import src.rc18_common as RC
import src.rc19_pool as P

OUT = RC.ROOT / "outputs" / "research_campaign_20261031" / "opus_ioan_requests"
DATA = OUT / "data"
TEMP = OUT / "temporal"
FRAMES = RC.ROOT / "outputs" / "week19_temporal_regime_audit" / "tables" / "frame_level_map.csv.gz"
CHANNELS = {"KE": "kinetic-energy_melt.dat", "T": "maximum-temperature_melt.dat", "V": "maximum-velocity_melt.dat",
            "LASER": "transferred-laser-power_melt.dat", "ETOT": "total-energy_melt.dat", "NPART": "particle-number_melt.dat"}
SIGNALS = ("W", "L", "KE", "T", "V", "LASER", "ETOT", "NPART")          # compared with depth D
V_PLAUSIBLE_MAX = 100.0
LAG_US = 100
SMOOTH_US = 20
EVENT_US = 100
EARLY_FRAC = 0.25
U_REF_UM = 111.0                                                      # passed to Week 19's process (time-above stats only; unused here)


def _setup():
    import src.jdl_physical_data2  # noqa: F401  (sets src.week19_sources.RAW to the main-checkout cache, read-only)


def _spearman(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 20 or np.nanstd(a[m]) == 0 or np.nanstd(b[m]) == 0:
        return np.nan, int(m.sum())
    return float(spearmanr(a[m], b[m]).statistic), int(m.sum())


def _grid(t_us, v, g):
    m = np.isfinite(v)
    if m.sum() < 20:
        return np.full(len(g), np.nan)
    return np.interp(g, t_us[m], v[m], left=np.nan, right=np.nan)


def _z(x):
    m = np.isfinite(x); s = np.nanstd(x)
    return (x - np.nanmean(x)) / s if m.sum() > 2 and s > 0 else np.full(len(x), np.nan)


def _lag(d, s, maxlag=LAG_US):
    """tau* (grid steps = 1 us) maximising corr(d(t), s(t - tau)); positive tau: s leads d."""
    best, bt = -np.inf, np.nan; n = len(d)
    for tau in range(-maxlag, maxlag + 1):
        if tau >= 0:
            a, b = d[tau:], s[:n - tau]
        else:
            a, b = d[:n + tau], s[-tau:]
        m = np.isfinite(a) & np.isfinite(b)
        if m.sum() < 50:
            continue
        aa, bb = a[m], b[m]
        if aa.std() == 0 or bb.std() == 0:
            continue
        r = float(np.corrcoef(aa, bb)[0, 1])
        if r > best:
            best, bt = r, tau
    return (bt, best) if np.isfinite(best) else (np.nan, np.nan)


def _smooth_diff(x, w=SMOOTH_US):
    if np.isfinite(x).sum() < 3 * w:
        return np.full(len(x), np.nan)
    k = np.ones(w) / w; xs = np.convolve(np.where(np.isfinite(x), x, np.nanmean(x)), k, mode="same"); xs[~np.isfinite(x)] = np.nan
    return np.r_[np.diff(xs), np.nan]


def one(args):
    sid, pop, frames, y = args
    _setup()
    import src.jdl_phys_al as PAL
    import src.jdl_physical_data2 as PD2
    import src.week19_series as SE
    rec = {"sim_id": sid, "batch": pop, "y": int(y)}
    o, fmap, s = SE.series_for(sid, pop, frames, U_REF_UM)
    rec["A_recomputed_um"] = o.get("A_active_max_um", np.nan); rec["w19_failure"] = o.get("failure", "")
    for k in ("first_active_frame_ms", "first_K_ms", "active_cutoff_ms"):
        rec[k] = o.get(k, np.nan)
    if s is None:
        return rec, None
    t_ms, D, Wd, Ld, valid, act, t0 = s["t_ms"], s["depth_um"], s["width_um"], s["length_um"], s["valid"], s["active"], s["t0"]
    n = len(t_ms)
    sig = {"D": np.where(act, D, np.nan), "W": np.where(act, Wd, np.nan), "L": np.where(act, Ld, np.nan)}
    if act.any() and np.isfinite(sig["D"]).any():
        ia = np.flatnonzero(act & np.isfinite(D))
        rec["W_A_um"] = float(np.nanmax(Wd[ia])); rec["L_A_um"] = float(np.nanmax(Ld[ia])); rec["W_atA_um"] = float(Wd[ia[np.nanargmax(D[ia])]])
    if (t0 & valid).any():
        rec["W_T0_um"] = float(np.nanmedian(Wd[t0 & valid]))
    for key, ch in CHANNELS.items():
        try:
            v, _ = PAL.load_monitor(PD2.local(sid, ch, pop), ch); v = np.asarray(v, float).ravel()
        except FileNotFoundError:
            rec[f"{key}_status"] = "MISSING_FILE"; continue
        except Exception as ex:                                      # noqa: BLE001  (malformed file: this channel only)
            rec[f"{key}_status"] = f"PARSE_ERROR {type(ex).__name__}"; continue
        if len(v) != n:
            rec[f"{key}_status"] = f"ROW_MISMATCH {len(v)}/{n}"; continue
        bad = ~np.isfinite(v)
        if key == "V":
            imp = np.isfinite(v) & (v > V_PLAUSIBLE_MAX); rec["V_implausible_rows"] = int(imp.sum()); bad |= imp
        rec[f"{key}_status"] = "ok"; rec[f"{key}_nonfinite_rows"] = int((~np.isfinite(v)).sum())
        sig[key] = np.where(act & ~bad, v, np.nan)
        if np.isfinite(sig[key]).any():
            rec[f"{key}_A_max"] = float(np.nanmax(sig[key]))
    # ---- F1: within-run Spearman with depth over active rows
    for k in SIGNALS:
        if k in sig:
            rec[f"F1_rho_{k}"], rec[f"F1_n_{k}"] = _spearman(sig["D"], sig[k])
    # ---- F4: early-window medians
    if act.any():
        ia = np.flatnonzero(act); ta, tb = t_ms[ia[0]], t_ms[ia[-1]]; early = act & (t_ms <= ta + EARLY_FRAC * (tb - ta))
        for k in ("D",) + SIGNALS:
            if k in sig and np.isfinite(sig[k][early]).any():
                rec[f"F4_early_med_{k}"] = float(np.nanmedian(sig[k][early]))
    # ---- F2 / F3 on the 1-us grid of the post-onset window
    ev = None; t_on, t_cut = rec["first_active_frame_ms"], rec["active_cutoff_ms"]
    if np.isfinite(t_on) and np.isfinite(t_cut) and t_cut > t_on:
        t_us = t_ms * 1e3; g = np.arange(np.ceil(t_on * 1e3), np.floor(t_cut * 1e3) + 1.0)
        if len(g) >= 4 * LAG_US:
            G = {k: _grid(t_us, sig[k], g) for k in sig}
            for k in SIGNALS:
                if k not in G:
                    continue
                tl, rl = _lag(_z(G["D"]), _z(G[k])); td, rd = _lag(_z(_smooth_diff(G["D"])), _z(_smooth_diff(G[k])))
                rec[f"F2_tau_level_{k}"], rec[f"F2_r_level_{k}"], rec[f"F2_tau_diff_{k}"], rec[f"F2_r_diff_{k}"] = tl, rl, td, rd
        if int(y) == 1 and np.isfinite(rec["first_K_ms"]):
            tk = rec["first_K_ms"] * 1e3; rng = np.random.default_rng(zlib.crc32(sid.encode()))
            tc = float(rng.uniform(t_on * 1e3 + EVENT_US, max(t_on * 1e3 + EVENT_US + 1, t_cut * 1e3 - EVENT_US)))
            gk = tk + np.arange(-EVENT_US, EVENT_US + 1.0); gc = tc + np.arange(-EVENT_US, EVENT_US + 1.0); ev = {"sim_id": sid}
            for k in ("D",) + SIGNALS:
                if k not in sig:
                    continue
                a = sig[k]; m = np.isfinite(a)
                if m.sum() < 20:
                    continue
                mu, sd = float(np.nanmean(a)), float(np.nanstd(a))
                if sd <= 0:
                    continue
                ev[f"K_{k}"] = ((_grid(t_us, a, gk) - mu) / sd).astype(np.float32); ev[f"C_{k}"] = ((_grid(t_us, a, gc) - mu) / sd).astype(np.float32)
    return rec, ev


def extract(workers=3):
    RC.limit_threads(1); M = P.manifest(); F = pd.read_csv(FRAMES, usecols=["sim_id", "frame_pos", "timestep", "code", "campaign"])
    jobs = []
    for sid, pop, y in zip(M.index.astype(str), M.source_batch.astype(str), M.y.astype(int)):
        g = F[F.sim_id == sid]
        if g.campaign.iloc[0] != pop:
            raise RuntimeError(f"batch mismatch {sid}")
        jobs.append((sid, pop, g[["sim_id", "frame_pos", "timestep", "code"]], y))
    rows, evs, t0 = [], [], time.time()
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as ex:
        for i, (r, ev) in enumerate(ex.map(one, jobs, chunksize=6), 1):
            rows.append(r)
            if ev is not None:
                evs.append(ev)
            if i % 60 == 0 or i == len(jobs):
                print(json.dumps({"extracted": i, "of": len(jobs), "s": round(time.time() - t0, 1)}), flush=True)
    R = pd.DataFrame(rows).set_index("sim_id").reindex(M.index.astype(str))
    DATA.mkdir(parents=True, exist_ok=True); TEMP.mkdir(parents=True, exist_ok=True)
    geo_cols = ["batch", "y", "A_recomputed_um", "W_A_um", "W_T0_um", "W_atA_um", "L_A_um", "KE_A_max", "T_A_max", "V_A_max",
                "first_active_frame_ms", "first_K_ms", "active_cutoff_ms", "w19_failure"] + [c for c in R.columns if c.endswith("_status") or c.endswith("_rows")]
    R[[c for c in geo_cols if c in R.columns]].to_csv(DATA / "IR_GEOMETRY.csv", lineterminator="\n")
    R[[c for c in R.columns if c.startswith(("F1_", "F2_", "F4_"))] + ["batch", "y"]].to_csv(TEMP / "per_run_time_stats.csv", lineterminator="\n")
    keys = sorted({k for e in evs for k in e if k != "sim_id"})
    arr = {k: np.stack([e.get(k, np.full(2 * EVENT_US + 1, np.nan, np.float32)) for e in evs]) for k in keys}
    np.savez_compressed(TEMP / "F3_event_windows.npz", sim_ids=np.array([e["sim_id"] for e in evs]), lag_us=np.arange(-EVENT_US, EVENT_US + 1), **arr)
    # ---- acceptance V1: recomputed depth = pooled A
    A = M.A_um.astype(float); d = (R.A_recomputed_um.astype(float) - A).abs(); fin = np.isfinite(A)
    v1 = {"runs": int(len(M)), "finite_pooled_A": int(fin.sum()), "compared": int(d[fin].notna().sum()), "max_abs_diff_um": float(d[fin].max()),
          "PASS": bool(d[fin].notna().all() and float(d[fin].max()) <= 1e-9)}
    man = {"V1": v1, "seconds": round(time.time() - t0, 1), "utc": RC.utc(), "files": {}}
    for f in (DATA / "IR_GEOMETRY.csv", TEMP / "per_run_time_stats.csv", TEMP / "F3_event_windows.npz"):
        man["files"][str(f.relative_to(OUT))] = hashlib.sha256(f.read_bytes()).hexdigest()
    man["channel_status"] = {k: R[f"{k}_status"].fillna("NOT_READ").value_counts().to_dict() for k in CHANNELS if f"{k}_status" in R}
    man["width_available"] = int(R.W_A_um.notna().sum()); man["keyhole_event_runs"] = len(evs)
    (DATA / "IR_DATA_MANIFEST.json").write_text(json.dumps(man, indent=1, default=str), encoding="utf-8")
    print(json.dumps(man, indent=1, default=str)); return man


# ======================================================================================== learner-side access (paid rows only)
_W = None


def geometry():
    global _W
    if _W is None:
        _W = pd.read_csv(DATA / "IR_GEOMETRY.csv", index_col="sim_id")
    return _W


def paid_W(task, rev):
    """log W_A (um) for the PAID rows of a Reveal, NaN for every other row (the learner contract of PROTOCOL_IR D4)."""
    G = geometry(); ids = np.asarray(task["ids"], str); out = np.full(len(ids), np.nan); L = rev.paid
    if len(L):
        out[L] = np.log(G.W_A_um.reindex(ids[L]).to_numpy(float))
    return out


def all_W(task):
    """Evaluator only: log W_A of every row (ORACLE diagnostics and evaluation)."""
    return np.log(geometry().W_A_um.reindex(np.asarray(task["ids"], str)).to_numpy(float))


if __name__ == "__main__":
    {"extract": extract}[sys.argv[1]]()
