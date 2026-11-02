"""GT study, data layer (PROTOCOL_GT.md section 3): per-run melt-pool geometry definitions and causal early-time features, read only
from the verified raw copy (no new simulation; POOLED_MANIFEST unchanged).

Reused unchanged: src.week19_series.series_for (bounds rows, valid mask = finite, non-sentinel and ordered bounds, Week 19 active window,
frame timing), src.jdl_phys_al.load_monitor + src.jdl_physical_data2.local (channels; a channel is used only when its row count equals
time.dat, as in IR), the Week 6 aspect-ratio denominator guard (12 um = three 4 um SPH particle spacings,
src.week6_phase3_5_regime_target_design.PRIMARY_WIDTH_GUARD_M).

Geometry per run (um; valid rows of the Week 19 active window; depth = max(0, -z_min), width = y-extent of the melt bounds):
  A       active-window maximum depth (must reproduce the pooled A_um: acceptance V1)
  W_A     active-window maximum width (IR's W_A)
  W_atA   width at the row of the active depth maximum (IR's W_atA)
  R3inst  maximum over active valid rows with width >= 12 um of depth / width (the simultaneous ratio)
  timing  times of the depth, width and R3inst maxima; rows removed by the guard
Targets: g1 = log(2 A / W_A), g2 = log(2 A / W_atA), g3 = log(2 R3inst); physical boundary g = 0 (d / w = 1/2).

Early features (causal: only rows with time <= t; decision grid every 25 us from 0.300 ms to 2.100 ms after the simulation start t = 0):
  Dmax(t) running maximum depth of valid rows (0 before the first valid melt row)
  Dnow(t) median depth of valid rows in (t - 10 us, t] (0 if none)
  Tmax(t) running maximum of maximum-temperature_melt (finite rows)
  Tnow(t) median of maximum-temperature_melt in (t - 10 us, t] (NaN if none)
  ifrac(t) solver iteration at t / iteration of the last recorded row (a compute proxy, not CPU time)
  avail(t) t <= last recorded time
Evaluator-only timing (manual frames): first_K_ms, last_K_ms, first_active_frame_ms; never a learner or alarm input.
    python -m src.gt_data extract
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

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_pool as P

OUT = RC.ROOT / "outputs" / "research_campaign_20261102" / "opus_geometry_temperature"
DATA = OUT / "data"
TEMP = OUT / "temporal"
FRAMES = RC.ROOT / "outputs" / "week19_temporal_regime_audit" / "tables" / "frame_level_map.csv.gz"
GRID_MS = np.round(np.arange(0.300, 2.1000001, 0.025), 3)
NOW_WIN_MS = 0.010
WIDTH_GUARD_UM = 12.0
CEIL_UM = 295.0
U_REF_UM = 111.0
FEATS = ("Dmax", "Dnow", "Tmax", "Tnow", "ifrac", "avail")


def _setup():
    import src.jdl_physical_data2  # noqa: F401  (points src.week19_sources.RAW at the verified main-checkout cache, read only)


def _episodes(t, m):
    if not m.any():
        return 0, 0.0
    idx = np.flatnonzero(m); br = np.flatnonzero(np.diff(idx) > 1)
    s = np.r_[idx[0], idx[br + 1]]; e = np.r_[idx[br], idx[-1]]
    return int(len(s)), float(((t[e] - t[s])).max())


def one(args):
    sid, pop, frames = args
    _setup()
    import src.jdl_phys_al as PAL
    import src.jdl_physical_data2 as PD2
    import src.week19_series as SE
    from src.week6_phase3_5_regime_target_design import PRIMARY_WIDTH_GUARD_M
    if not np.isclose(PRIMARY_WIDTH_GUARD_M * 1e6, WIDTH_GUARD_UM):
        raise RuntimeError("Week 6 width guard changed")
    rec = {"sim_id": sid, "batch": pop}
    o, fmap, s = SE.series_for(sid, pop, frames, U_REF_UM)
    for k in ("first_valid_ms", "first_active_frame_ms", "first_K_ms", "last_K_ms", "active_cutoff_ms", "derived_exit_ms", "recording_end_ms",
              "A_active_max_um", "A_active_max_ms", "max_depth_whole_um", "failure"):
        rec[k] = o.get(k, np.nan if k != "failure" else "")
    early = {f: np.full(len(GRID_MS), np.nan, np.float32) for f in FEATS}
    if s is None:
        return rec, early
    t, D, Wd, valid, act = s["t_ms"], s["depth_um"], s["width_um"], s["valid"], s["active"]
    rec["rows"] = int(len(t)); rec["valid_rows"] = int(valid.sum()); rec["active_rows"] = int(act.sum())
    ia = np.flatnonzero(act & np.isfinite(D) & np.isfinite(Wd))
    if len(ia):
        iA = ia[int(np.nanargmax(D[ia]))]; iW = ia[int(np.nanargmax(Wd[ia]))]
        rec.update({"A_um": float(D[iA]), "t_A_ms": float(t[iA]), "W_A_um": float(Wd[iW]), "t_WA_ms": float(t[iW]), "W_atA_um": float(Wd[iA])})
        g = ia[Wd[ia] >= WIDTH_GUARD_UM]; rec["guard_excluded_active_rows"] = int(len(ia) - len(g)); rec["guard_kept_active_rows"] = int(len(g))
        if len(g):
            r = D[g] / Wd[g]; j = int(np.nanargmax(r)); iR = g[j]
            rec.update({"R3inst": float(r[j]), "t_R3_ms": float(t[iR]), "d_atR3_um": float(D[iR]), "w_atR3_um": float(Wd[iR]),
                        "R3_q99": float(np.nanquantile(r, 0.99))})
        cm = act & np.isfinite(D) & (D >= CEIL_UM)
        rec["ceil_rows"] = int(cm.sum())
        if cm.any():
            n_ep, longest = _episodes(t, cm); rec.update({"ceil_episodes": n_ep, "ceil_longest_ms": longest, "ceil_first_ms": float(t[cm][0]),
                                                          "ceil_plateau_median_um": float(np.median(D[cm])), "ceil_frac_active_rows": float(cm.sum() / len(ia))})
    # ---- channels used by the early features
    T = None
    try:
        v, _ = PAL.load_monitor(PD2.local(sid, "maximum-temperature_melt.dat", pop), "maximum-temperature_melt.dat"); v = np.asarray(v, float).ravel()
        rec["T_status"] = "ok" if len(v) == len(t) else f"ROW_MISMATCH {len(v)}/{len(t)}"
        T = v if len(v) == len(t) else None
    except FileNotFoundError:
        rec["T_status"] = "MISSING_FILE"
    except Exception as ex:  # noqa: BLE001
        rec["T_status"] = f"PARSE_ERROR {type(ex).__name__}"
    rev = SE.OLD_REV if pop == "OLD" else SE.NEW_REV
    it = np.loadtxt(SE.local_file(rev, f"{sid}/monitor/iter.dat"), ndmin=1).astype(float)
    if len(it) != len(t):
        it = None; rec["iter_status"] = "ROW_MISMATCH"
    else:
        rec["iter_status"] = "ok"; rec["iter_last"] = float(it[-1])
    # ---- causal early features on the fixed grid
    dv = np.where(valid & np.isfinite(D), D, -np.inf); cmD = np.maximum.accumulate(dv)
    if T is not None:
        tv = np.where(np.isfinite(T), T, -np.inf); cmT = np.maximum.accumulate(tv)
    for k, tc in enumerate(GRID_MS):
        n = int(np.searchsorted(t, tc, side="right"))
        early["avail"][k] = float(tc <= t[-1] + 1e-9)
        if n == 0 or tc > t[-1] + 1e-9:
            continue
        early["Dmax"][k] = float(max(cmD[n - 1], 0.0)) if np.isfinite(cmD[n - 1]) else 0.0
        lo = int(np.searchsorted(t, tc - NOW_WIN_MS, side="right")); w = slice(lo, n)
        dw = D[w][valid[w] & np.isfinite(D[w])]; early["Dnow"][k] = float(np.median(dw)) if len(dw) else 0.0
        if T is not None:
            early["Tmax"][k] = float(cmT[n - 1]) if np.isfinite(cmT[n - 1]) else np.nan
            tw = T[w][np.isfinite(T[w])]; early["Tnow"][k] = float(np.median(tw)) if len(tw) else np.nan
        if it is not None:
            early["ifrac"][k] = float(it[n - 1] / it[-1]) if it[-1] > 0 else np.nan
    return rec, early


def extract(workers=6):
    RC.limit_threads(1); M = P.manifest(); F = pd.read_csv(FRAMES, usecols=["sim_id", "frame_pos", "timestep", "code", "campaign"])
    jobs = []
    for sid, pop in zip(M.index.astype(str), M.source_batch.astype(str)):
        g = F[F.sim_id == sid]
        if len(g) and g.campaign.iloc[0] != pop:
            raise RuntimeError(f"batch mismatch {sid}")
        jobs.append((sid, pop, g[["sim_id", "frame_pos", "timestep", "code"]]))
    rows, E, t0 = [], {}, time.time()
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as ex:
        for i, (r, e) in enumerate(ex.map(one, jobs, chunksize=4), 1):
            rows.append(r); E[r["sim_id"]] = e
            if i % 60 == 0 or i == len(jobs):
                print(json.dumps({"extracted": i, "of": len(jobs), "s": round(time.time() - t0, 1)}), flush=True)
    R = pd.DataFrame(rows).set_index("sim_id").reindex(M.index.astype(str))
    R["TE_ms"] = M.TE_ms.to_numpy(float); R["XI_mm"] = M.XI_mm.to_numpy(float); R["beam_diameter_um"] = 2e6 * M.LS.to_numpy(float)
    R["short_record"] = M.short_record.to_numpy(bool)
    for j, (d, w) in enumerate((("A_um", "W_A_um"), ("A_um", "W_atA_um"))):
        R[f"g{j + 1}"] = np.log(2.0 * R[d] / R[w])
    R["g3"] = np.log(2.0 * R["R3inst"])
    DATA.mkdir(parents=True, exist_ok=True); TEMP.mkdir(parents=True, exist_ok=True)
    R.to_csv(DATA / "GT_RUNS.csv", lineterminator="\n")
    ids = np.asarray(M.index.astype(str).tolist(), dtype=str)
    arr = {f: np.stack([E[s][f] for s in ids]).astype(np.float32) for f in FEATS}
    np.savez_compressed(TEMP / "GT_EARLY.npz", ids=ids, grid_ms=GRID_MS, **arr)
    man = {"utc": RC.utc(), "runs": len(R), "grid_ms": [float(GRID_MS[0]), float(GRID_MS[-1]), len(GRID_MS)], "width_guard_um": WIDTH_GUARD_UM,
           "sha256_runs_csv": hashlib.sha256((DATA / "GT_RUNS.csv").read_bytes()).hexdigest(),
           "sha256_early_npz": hashlib.sha256((TEMP / "GT_EARLY.npz").read_bytes()).hexdigest(), "seconds": round(time.time() - t0, 1)}
    (DATA / "GT_DATA_MANIFEST.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(json.dumps(man), flush=True)


_CACHE = {}


def runs():
    if "R" not in _CACHE:
        _CACHE["R"] = pd.read_csv(DATA / "GT_RUNS.csv", index_col=0)
    return _CACHE["R"]


def early():
    if "E" not in _CACHE:
        z = np.load(TEMP / "GT_EARLY.npz", allow_pickle=False); _CACHE["E"] = {k: z[k] for k in z.files}
    return _CACHE["E"]


if __name__ == "__main__":
    {"extract": extract}[sys.argv[1]]()
