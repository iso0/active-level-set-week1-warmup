"""Week 19 Phases 1 and 3: frame -> monitor-time mapping, pipeline windows and depth definitions per simulation.

Mapping chain (never assumes timestep x nominal DT): ledger row (sim, timestep) -> frames.csv row (frame_idx,
timestep, label) -> unique iter.dat row whose iteration equals the timestep -> time.dat value of the same row.
Every mismatch is recorded; no file is truncated, repaired or extrapolated.  If bounds and time row counts differ,
all time-dependent quantities are left unavailable for that simulation (the whole-record maximum, which needs no
time, is still reported).

Windows (all reproduced from src/week7_phase2_sph_v2_physical_target_extraction.py::extract_one; derived, not
observed):
  derived laser domain-exit time  = (min(XF, XL) + 12 um) / VX   (extraction convention x = VX t)
  pipeline active window          = valid rows with t <= min(recording end, 0.90 x domain-exit time); startup rows
                                    are retained (the 90 % cutoff does not remove startup)
  T0 window                       = last 20 % of [first valid time, active cutoff] (fallback last 50 active rows)
  adaptive interior (G3)          = laser x in [onset x + 50 um, min(last valid x, domain end) - 50 um]
Manual-label windows (observed, frame-sampled): first/last Forming Phase frame, first Conduction/Keyhole frame
("forming observed to have ended"), first Scanning Stopped / Solidifying Stopped frame, last labelled frame.

Depth definitions (um; depth = max(0, -z_min) on valid bounds rows):
  frozen  whole-record maximum (E1's target; unchanged)
  A       maximum inside the pipeline active window (startup retained)
  B       maximum inside the active window after the first Conduction/Keyhole frame (ANNOTATION-DEPENDENT,
          exploratory, POST-HOC with respect to the NEW labels)
  C       G3 persistent depth (max of the 50 um trailing rolling median in the adaptive interior) and T0 depth
  D       time above the OLD reference depth threshold u_ref, in four windows.  Hold rule: a valid row holds its
          value until the next monitor row (dt_i = t_{i+1} - t_i; the last row holds 0); invalid rows enter neither
          numerator nor denominator.
"""
from __future__ import annotations

import concurrent.futures
import io
import math

import numpy as np
import pandas as pd

from src.week19_sources import NEW_REV, OLD_REV, local_file, lp

# Executable Week 6/7 constants, imported (not re-typed) so the windows cannot drift.
from src.week6_phase1_melt_pool_data_audit import ACTIVE_DOMAIN_FRACTION, LATE_WINDOW_FRACTION, MIN_LATE_ROWS, SENTINEL_THRESHOLD  # noqa: E402
from src.week6_phase3_5_regime_target_design import END_MARGIN_M, PRIMARY_PERSISTENCE_WINDOW_UM, STARTUP_MARGIN_M  # noqa: E402
from src.week7_phase2_sph_v2_physical_target_extraction import DOMAIN_WALL_EXTENSION_M  # noqa: E402
PERSISTENCE_WINDOW_M = PRIMARY_PERSISTENCE_WINDOW_UM * 1e-6   # exactly as extract_one passes it
FRAMES_HEADER = ["frame_idx", "timestep", "label", "front_filename", "side_filename", "top_filename"]


def _check_constants():
    """Record the constants in use (they are imported from the Week 6/7 modules, so they equal them by construction)."""
    vals = {"ACTIVE_DOMAIN_FRACTION": ACTIVE_DOMAIN_FRACTION, "LATE_WINDOW_FRACTION": LATE_WINDOW_FRACTION, "MIN_LATE_ROWS": MIN_LATE_ROWS,
            "SENTINEL_THRESHOLD": SENTINEL_THRESHOLD, "STARTUP_MARGIN_M": STARTUP_MARGIN_M, "END_MARGIN_M": END_MARGIN_M,
            "PERSISTENCE_WINDOW_M": PERSISTENCE_WINDOW_M, "DOMAIN_WALL_EXTENSION_M": DOMAIN_WALL_EXTENSION_M}
    expected = {"ACTIVE_DOMAIN_FRACTION": 0.90, "LATE_WINDOW_FRACTION": 0.20, "MIN_LATE_ROWS": 50, "SENTINEL_THRESHOLD": 1e30,
                "STARTUP_MARGIN_M": 50e-6, "END_MARGIN_M": 50e-6, "PERSISTENCE_WINDOW_M": 50e-6, "DOMAIN_WALL_EXTENSION_M": 12e-6}
    return all(math.isclose(vals[k], expected[k], rel_tol=1e-12) for k in vals)


def rolling_distance_median(x_m, values, window_m):
    """Same computation as week6_phase3_5_regime_target_design.rolling_distance_stat(statistic='median').

    The historical helper assigns into ``Series.to_numpy()``; under pandas 3 copy-on-write that array is read-only,
    so the unchanged helper raises.  This wrapper reuses its DistanceWindowIndexer and constants and only takes a
    writable copy.  Equivalence is checked by reproducing the Week 7 G3 values of all OLD runs (CHECKS C12)."""
    from src.week6_phase3_5_regime_target_design import MIN_ROLLING_OBSERVATIONS, MIN_ROLLING_SPAN_FRACTION, DistanceWindowIndexer
    x_m = np.asarray(x_m, dtype=float); values = np.asarray(values, dtype=float)
    if not np.all(np.diff(x_m) >= 0):
        raise ValueError("Laser X position is not monotone")
    starts = np.searchsorted(x_m, x_m - window_m, side="left")
    rolling = pd.Series(values).rolling(DistanceWindowIndexer(starts), min_periods=MIN_ROLLING_OBSERVATIONS)
    result = rolling.median().to_numpy(dtype=float).copy()
    count = rolling.count().to_numpy(dtype=float).copy()
    span = x_m - x_m[starts]
    eligible = np.isfinite(result) & (count >= MIN_ROLLING_OBSERVATIONS) & (span >= MIN_ROLLING_SPAN_FRACTION * window_m)
    result[~eligible] = np.nan
    return result, count, span, starts


def parse_name(sid):
    from src.week7_sph_v2_common import parse_experiment_name
    return parse_experiment_name(sid)


def read_frames_csv(path):
    raw = lp(path).read_text(encoding="utf-8-sig")
    df = pd.read_csv(io.StringIO(raw), dtype={"label": str})
    if df.columns.tolist() != FRAMES_HEADER:
        raise ValueError(f"unexpected frames.csv schema {df.columns.tolist()}")
    return df


def _hold_dt(t):
    dt = np.zeros(len(t))
    dt[:-1] = np.diff(t)
    return dt


def _max_info(depth_um, mask, t):
    if mask is None or not mask.any():
        return np.nan, -1, np.nan
    v = np.where(mask, depth_um, np.nan)
    i = int(np.nanargmax(v))
    return float(v[i]), i, (float(t[i]) if t is not None else np.nan)


def _time_above(depth_um, mask, dt, u):
    if mask is None or not mask.any():
        return np.nan, np.nan, np.nan
    den = float(dt[mask].sum())
    num = float(dt[mask & (depth_um >= u)].sum())
    rows = float((depth_um[mask] >= u).mean())
    return num * 1e3, (num / den if den > 0 else np.nan), rows


def process(job):
    """One simulation.  job = dict(sim_id, campaign, revision, frames (DataFrame: frame_pos, timestep, code), u_ref)."""
    from src.week7_phase2_sph_v2_physical_target_extraction import load_numeric
    sid, rev, fr, u = job["sim_id"], job["revision"], job["frames"].reset_index(drop=True), job["u_ref"]
    meta = parse_name(sid)
    out = {"sim_id": sid, "campaign": job["campaign"], "revision": rev}
    fail = []
    # ---- frames.csv cross-check
    try:
        fc = read_frames_csv(local_file(rev, f"{sid}/frames.csv"))
        out["frames_csv_rows"] = len(fc)
        out["frames_csv_rows_match_ledger"] = int(len(fc) == len(fr))
        out["frames_csv_frame_idx_contiguous"] = int(fc.frame_idx.tolist() == list(range(len(fc))))
        fcs = fc.sort_values(["timestep", "frame_idx"], kind="stable").reset_index(drop=True)
        same_len = len(fcs) == len(fr)
        out["frames_csv_timesteps_match_ledger"] = int(same_len and np.array_equal(fcs.timestep.to_numpy(np.int64), fr.timestep.to_numpy(np.int64)))
        from src.week19_sequences import CODE
        out["frames_csv_labels_match_label_final"] = int(same_len and (fcs.label.map(CODE).to_numpy() == fr.code.to_numpy()).all())
        out["frames_csv_timesteps_strictly_increasing"] = int(np.all(np.diff(fc.timestep.to_numpy(np.int64)) > 0))
    except Exception as e:  # recorded, not hidden
        fail.append(f"frames.csv: {type(e).__name__}: {e}")
    # ---- monitors
    try:
        it = np.loadtxt(local_file(rev, f"{sid}/monitor/iter.dat"), ndmin=1)
        t = np.loadtxt(local_file(rev, f"{sid}/monitor/time.dat"), ndmin=1)
        b, baudit = load_numeric(local_file(rev, f"{sid}/monitor/position-bounds_melt.dat"), "position-bounds_melt.dat")
    except Exception as e:
        out["failure"] = "; ".join(fail + [f"monitor load: {type(e).__name__}: {e}"])
        return out, None, None
    out.update({"bounds_rows": len(b), "time_rows": len(t), "iter_rows": len(it),
                "iter_time_rows_match": int(len(it) == len(t)), "bounds_time_rows_match": int(len(b) == len(t)),
                "time_strictly_increasing": int(np.all(np.diff(t) > 0)), "iter_strictly_increasing": int(np.all(np.diff(it) > 0)),
                "iter_integer_valued": int(np.all(np.isfinite(it)) and np.all(it == np.round(it))),
                "recording_end_ms": float(t[-1]) * 1e3, "sentinel_rule_applied": int(bool(baudit.get("known_malformed_no_melt_sentinel_rule_applied", False)))})
    finite = np.isfinite(b).all(1); nonsent = (np.abs(b) < SENTINEL_THRESHOLD).all(1)
    ordered = (b[:, 1] >= b[:, 0]) & (b[:, 3] >= b[:, 2]) & (b[:, 5] >= b[:, 4])
    valid = finite & nonsent & ordered
    out["valid_rows"] = int(valid.sum()); out["malformed_rows"] = int((finite & nonsent & ~ordered).sum())
    depth_m = np.where(valid, np.maximum(0.0, -b[:, 4]), np.nan)      # metres, exactly as extract_one
    depth = depth_m * 1e6
    width = np.where(valid, b[:, 3] - b[:, 2], np.nan) * 1e6
    length = np.where(valid, b[:, 1] - b[:, 0], np.nan) * 1e6
    zmax = np.where(valid, b[:, 5], np.nan) * 1e6
    mx, imx, _ = _max_info(depth, valid, None)
    out.update({"max_depth_whole_um": mx, "max_depth_whole_row": imx, "max_depth_whole_is_last_row": int(imx == len(b) - 1)})
    aligned = len(b) == len(t) and out["time_strictly_increasing"]
    # ---- frame -> iteration -> time mapping (needs iter/time only)
    fmap = fr[["frame_pos", "timestep", "code"]].copy()
    if len(it) == len(t) and out["iter_strictly_increasing"]:
        itr = it.astype(np.int64)
        pos = np.searchsorted(itr, fmap.timestep.to_numpy(np.int64))
        pos_c = np.clip(pos, 0, len(itr) - 1)
        hit = itr[pos_c] == fmap.timestep.to_numpy(np.int64)
        fmap["monitor_row"] = np.where(hit, pos_c, -1)
        fmap["time_ms"] = np.where(hit, t[pos_c] * 1e3, np.nan)
        out["frames_unmatched_to_iter"] = int((~hit).sum())
        out["frames_matched_to_iter"] = int(hit.sum())
        out["frames_beyond_last_iter"] = int((fmap.timestep.to_numpy(np.int64) > itr[-1]).sum())
        dt_nom = meta["DT"]
        ok = hit & (fmap.timestep.to_numpy() > 0)
        if ok.any():
            rel = (fmap.timestep.to_numpy(float)[ok] * dt_nom) / (t[pos_c][ok]) - 1
            out["nominal_dt_time_rel_error_median"] = float(np.median(rel)); out["nominal_dt_time_rel_error_max_abs"] = float(np.max(np.abs(rel)))
        tf = fmap.time_ms.to_numpy()
        tfv = tf[np.isfinite(tf)]
        if len(tfv) > 1:
            d = np.diff(tfv) * 1e3
            out.update({"frame_dt_median_us": float(np.median(d)), "frame_dt_min_us": float(d.min()), "frame_dt_max_us": float(d.max()),
                        "frame_dt_median_over_nominal_DT": float(np.median(d)) * 1e-6 / dt_nom,
                        "iterations_per_frame_median": float(np.median(np.diff(fmap.timestep.to_numpy(float)[np.isfinite(tf)])))})
        out["timing_mapping_ok"] = int(out["frames_unmatched_to_iter"] == 0)
    else:
        fmap["monitor_row"] = -1; fmap["time_ms"] = np.nan
        out["timing_mapping_ok"] = 0
        fail.append("iter/time rows differ or iteration not strictly increasing: frame timing unavailable")
    # ---- manual-label windows (frame-sampled observations)
    tf = fmap.time_ms.to_numpy(); code = fmap.code.to_numpy()

    def ft(c, which):
        m = (code == c) & np.isfinite(tf)
        if not m.any():
            return np.nan
        return float(tf[m][0] if which == "first" else tf[m][-1])
    act_m = np.isin(code, ["C", "K"]) & np.isfinite(tf)
    t_first_active = float(tf[act_m][0]) if act_m.any() else np.nan
    out.update({"first_F_ms": ft("F", "first"), "last_F_ms": ft("F", "last"), "first_active_frame_ms": t_first_active,
                "first_K_ms": ft("K", "first"), "last_K_ms": ft("K", "last"), "first_C_ms": ft("C", "first"), "last_C_ms": ft("C", "last"),
                "first_SS_ms": ft("SS", "first"), "first_SoS_ms": ft("SoS", "first"),
                "last_frame_ms": float(np.nanmax(tf)) if np.isfinite(tf).any() else np.nan})
    out["last_frame_over_recording_end"] = out["last_frame_ms"] / out["recording_end_ms"] if np.isfinite(out["last_frame_ms"]) else np.nan
    # ---- pipeline windows (reproduction of extract_one); exit and cutoff need only time.dat and the folder name
    domain_max = min(float(meta["XF"]), float(meta["XL"])) + DOMAIN_WALL_EXTENSION_M
    vx = float(meta["VX"])
    exit_s = domain_max / vx
    cutoff = min(float(t[-1]), ACTIVE_DOMAIN_FRACTION * exit_s)
    out.update({"domain_max_x_m": domain_max, "derived_exit_ms": exit_s * 1e3, "active_cutoff_ms": cutoff * 1e3,
                "recording_ends_before_90pct_domain": int(float(t[-1]) < ACTIVE_DOMAIN_FRACTION * exit_s),
                "recording_end_over_exit": float(t[-1]) / exit_s})
    if not aligned:
        fail.append(f"bounds/time row mismatch {len(b)}/{len(t)}: time-dependent depth quantities unavailable (no truncation)")
        out["failure"] = "; ".join(fail)
        fmap["depth_um"] = np.nan
        return out, fmap, None
    vi = np.flatnonzero(valid)
    first_valid_t = float(t[vi[0]]) if len(vi) else np.nan
    active = valid & (t <= cutoff)
    out["first_valid_ms"] = first_valid_t * 1e3
    if not active.any() or cutoff < first_valid_t:
        fail.append("no active region before the 90% cutoff")
        t0 = np.zeros(len(t), bool)
    else:
        start = first_valid_t + (1 - LATE_WINDOW_FRACTION) * (cutoff - first_valid_t)
        t0 = valid & (t >= start) & (t <= cutoff)
        if t0.sum() < MIN_LATE_ROWS:
            ei = np.flatnonzero(active); t0 = np.zeros(len(t), bool); t0[ei[-min(MIN_LATE_ROWS, len(ei)):]] = True
            out["T0_fallback"] = 1
        else:
            out["T0_fallback"] = 0
    out["T0_depth_um"] = float(np.median(depth[t0 & valid])) if (t0 & valid).any() else np.nan
    if t0.any():
        ti = np.flatnonzero(t0); out["T0_start_ms"] = float(t[ti[0]]) * 1e3; out["T0_end_ms"] = float(t[ti[-1]]) * 1e3
    x = vx * t
    interior = np.zeros(len(t), bool)
    if len(vi):
        a0 = float(x[vi[0]]) + STARTUP_MARGIN_M; a1 = min(float(x[vi[-1]]), domain_max) - END_MARGIN_M
        interior = valid & (x >= a0) & (x <= a1)
        out["interior_start_ms"] = a0 / vx * 1e3; out["interior_end_ms"] = a1 / vx * 1e3
    out["G3_persistent_depth_um"] = np.nan
    if interior.any():
        ii = np.flatnonzero(interior)
        roll, cnt, span, _ = rolling_distance_median(x[ii], depth_m[ii], PERSISTENCE_WINDOW_M)
        if np.isfinite(roll).any():
            k = int(np.nanargmax(roll))
            out["G3_persistent_depth_um"] = float(roll[k] * 1e6); out["G3_event_row"] = int(ii[k]); out["G3_event_ms"] = float(t[ii[k]]) * 1e3
    # ---- depth definitions
    tms = t * 1e3
    for key, mask in [("A_active", active), ("B_postforming", active & (tms >= t_first_active) if np.isfinite(t_first_active) else None)]:
        v, i, tt = _max_info(depth, mask, tms)
        out[f"{key}_max_um"] = v; out[f"{key}_max_ms"] = tt
    out["max_depth_whole_ms"] = float(tms[imx]) if imx >= 0 else np.nan

    def pipeline_window(tt):
        """Location relative to the derived pipeline windows (no manual labels involved)."""
        if not np.isfinite(tt):
            return ""
        if tt <= cutoff * 1e3:
            return "active_window"
        return "after_cutoff_before_derived_exit" if tt <= exit_s * 1e3 else "after_derived_exit"

    def label_phase(tt):
        """Location relative to the manual labels: before or after the first Conduction/Keyhole frame."""
        if not (np.isfinite(tt) and np.isfinite(t_first_active)):
            return ""
        return "before_first_C_or_K_frame" if tt < t_first_active else "at_or_after_first_C_or_K_frame"
    tfs = np.sort(tf[np.isfinite(tf)])

    def frames_after_first_active(tt):
        """Signed number of labelled frames between the first C/K frame and time tt (frame-sampling resolution)."""
        if not (np.isfinite(tt) and np.isfinite(t_first_active)) or not len(tfs):
            return np.nan
        return int(np.searchsorted(tfs, tt, side="right") - np.searchsorted(tfs, t_first_active, side="left") - 1)
    tmax = out["max_depth_whole_ms"]
    out["max_depth_whole_location"] = pipeline_window(tmax)
    out["max_depth_whole_in_interior"] = int(bool(interior[imx])) if imx >= 0 else 0
    out["max_depth_whole_label_phase"] = label_phase(tmax)
    out["max_minus_first_active_frame_ms"] = tmax - t_first_active if np.isfinite(t_first_active) else np.nan
    out["max_frames_after_first_active_frame"] = frames_after_first_active(tmax)
    out["A_max_label_phase"] = label_phase(out["A_active_max_ms"])
    out["A_max_frames_after_first_active_frame"] = frames_after_first_active(out["A_active_max_ms"])
    out["G3_event_label_phase"] = label_phase(out.get("G3_event_ms", np.nan))
    out["G3_event_in_active_window"] = int(np.isfinite(out.get("G3_event_ms", np.nan)) and out["G3_event_ms"] <= cutoff * 1e3)
    out["max_after_first_SS"] = int(np.isfinite(out["first_SS_ms"]) and out["max_depth_whole_ms"] >= out["first_SS_ms"])
    dt = _hold_dt(t)
    post = active & (tms >= t_first_active) if np.isfinite(t_first_active) else None
    for key, mask in [("whole", valid), ("active", active), ("postforming", post), ("interior", interior)]:
        d_ms, frac, rowfrac = _time_above(depth, mask, dt, u)
        out[f"D_{key}_ms_above_uref"] = d_ms; out[f"D_{key}_frac_above_uref"] = frac; out[f"D_{key}_rowfrac_above_uref"] = rowfrac
    # Rows >= 300 um and >= 90 % of the whole-record maximum: episodes (first-to-last sample, no bridging of invalid rows)
    for name, thr in [("ge300", 300.0), ("ge90pct_max", 0.9 * mx), ("ge_uref", u)]:
        m = valid & (depth >= thr)
        out[f"rows_{name}"] = int(m.sum())
        if m.any():
            idx = np.flatnonzero(m); br = np.flatnonzero(np.diff(idx) > 1)
            starts = np.r_[idx[0], idx[br + 1]]; ends = np.r_[idx[br], idx[-1]]
            durs = (t[ends] - t[starts]) * 1e3
            out[f"episodes_{name}"] = len(starts); out[f"longest_episode_{name}_ms"] = float(durs.max()); out[f"total_episode_span_{name}_ms"] = float(durs.sum())
            out[f"first_{name}_ms"] = float(t[idx[0]]) * 1e3; out[f"last_{name}_ms"] = float(t[idx[-1]]) * 1e3
    # ---- label-aligned depth at frame rows (observation; frame row = exact iteration match)
    rows = fmap.monitor_row.to_numpy()
    dfr = np.full(len(fmap), np.nan)
    okr = rows >= 0
    dfr[okr] = depth[rows[okr]]
    fmap["depth_um"] = dfr
    fmap["in_active_window"] = np.where(okr, active[np.clip(rows, 0, len(t) - 1)], False).astype(int)
    fmap["valid_bounds"] = np.where(okr, valid[np.clip(rows, 0, len(t) - 1)], False).astype(int)
    for c in ("C", "K", "F"):
        m = (code == c) & np.isfinite(dfr)
        out[f"n_{c}_frames_with_depth"] = int(m.sum())
        if m.any():
            out[f"depth_at_{c}_frames_median_um"] = float(np.median(dfr[m])); out[f"depth_at_{c}_frames_max_um"] = float(dfr[m].max())
            out[f"frac_{c}_frames_depth_ge_uref"] = float((dfr[m] >= u).mean())
    out["failure"] = "; ".join(fail)
    series = {"t_ms": tms, "depth_um": depth, "width_um": width, "length_um": length, "zmax_um": zmax, "valid": valid,
              "active": active, "interior": interior, "t0": t0}
    return out, fmap, series


def run_all(frames, campaign_rev, u_ref, workers=6):
    jobs = []
    for sid, g in frames.groupby("sim_id", sort=False):
        camp = g.campaign.iloc[0]
        jobs.append({"sim_id": sid, "campaign": camp, "revision": campaign_rev[camp], "frames": g[["frame_pos", "timestep", "code"]], "u_ref": u_ref})
    rows, fmaps = [], []
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for i, (o, fm, _) in enumerate(pool.map(process, jobs, chunksize=4), 1):
            rows.append(o)
            if fm is not None:
                fm = fm.copy(); fm.insert(0, "sim_id", o["sim_id"]); fmaps.append(fm)
            if i % 50 == 0 or i == len(jobs):
                print(f"series {i}/{len(jobs)}", flush=True)
    return pd.DataFrame(rows), pd.concat(fmaps, ignore_index=True)


def series_for(sim_id, campaign, frames, u_ref):
    rev = OLD_REV if campaign == "OLD" else NEW_REV
    return process({"sim_id": sim_id, "campaign": campaign, "revision": rev, "frames": frames[frames.sim_id == sim_id][["frame_pos", "timestep", "code"]], "u_ref": u_ref})
