"""RC18 data layer (fixes A2 + A3): channel-independent monitor loading, separated QA, native-time binning, explicit summaries.

A2  Every channel is read on its own. A missing or malformed file makes only THAT channel unavailable; depth (position bounds),
    KE, temperature etc. stay usable (the frozen TEMPORAL_STRUCT loader dropped all channels of the 56 OLD runs without a
    remote velocity file; its frozen results are not changed).
A3  QA keeps separate counters per run x channel: file present, row count, row count == time rows (row_match), non-finite
    values, no-melt sentinels (bounds), implausible velocity rows (> 100 m/s), non-positive values (log channels), known
    malformed bounds tokens (Week 7 rule), time-step regularity. A row mismatch never hides the other counters.
    Three summary families are defined separately (never mixed):
      row quantiles      quantiles over the valid rows of a window (pilot B / PHYS_AL convention);
      duration-weighted  integral of v dt / window length (left Riemann on the row grid; weights dt_i = t_{i+1} - t_i);
      alignment          onset t_on = first valid melt row; active window [t_on, active_cutoff] (Week 19); T0 = last 20 %
                         of the window; native time = t - t_on (ms); onset-normalised tau = (t - t_on)/(cutoff - t_on).
    The 40-bin onset-normalised curve of TEMPORAL_STRUCT is reproduced here only to MEASURE what it does to short peaks.
Outputs (per run, checkpointed): _cache/monitors/<pop>__<sim>.npz (1-us native bins: max/median/min/count per channel) and
units/<pop>__<sim>.json.gz (QA + summaries).
    python -m src.rc18_data work --threads 1      (runner job: one unit per run)
    python -m src.rc18_data collect                (QA and summary tables)
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import src.jdl_phys_al as PAL
import src.jdl_physical_data2 as PD2
import src.jdl_physical_pilot as PP
import src.rc18_common as RC

OUT = RC.CAMP / "data"
UNITS = OUT / "units"
BINS = RC.CAMP / "_cache" / "monitors"
CH = {"time": "time.dat", "bounds": "position-bounds_melt.dat", "vmax": "maximum-velocity_melt.dat", "ke": "kinetic-energy_melt.dat",
      "laser": "transferred-laser-power_melt.dat", "tmax": "maximum-temperature_melt.dat", "etot": "total-energy_melt.dat",
      "npart": "particle-number_melt.dat"}
SIGNAL = ("depth", "vmax", "ke", "laser", "tmax", "etot", "npart")
LOGPOS = {"vmax", "ke", "etot", "npart", "depth"}       # positive channels summarised on a log scale where stated
BIN_US = 1.0
K40 = 40


@__import__('functools').lru_cache(maxsize=1)
def run_list():
    W = pd.read_csv(PP.W19_DEPTH)
    new = set(PD2.PD.new_ids()); old = set(PD2.old_ids())
    return [("NEW", s) for s in W.sim_id if s in new] + [("OLD", s) for s in W.sim_id if s in old]


def unit_name(pop, sim):
    """Short unit name (Windows MAX_PATH): population + first 16 hex of sha1(full sim_id); full IDs are stored inside."""
    import hashlib
    return f"{pop}__{hashlib.sha1(sim.encode()).hexdigest()[:16]}"


@__import__('functools').lru_cache(maxsize=1)
def _name_map():
    return {unit_name(p, s): s for p, s in run_list()}


def sim_of(name):
    return _name_map()[name]


def _read(sim, pop, key):
    """(array, status, malformed_count) for one channel, independent of all other channels."""
    try:
        path = PD2.local(sim, CH[key], pop)
    except FileNotFoundError:
        return None, "MISSING_FILE", 0
    try:
        v, n = PAL.load_monitor(path, CH[key])
        v = np.asarray(v, float)
        if key == "bounds":
            v = v[:, 4] if v.ndim == 2 else np.full(len(v), np.nan)
        return v, "ok", n
    except Exception as ex:                                   # malformed file: this channel only
        return None, f"PARSE_ERROR: {type(ex).__name__}", 0


def wq(v, w, q):
    """Weighted quantile (weights w >= 0), inverted CDF convention."""
    o = np.argsort(v); v, w = v[o], w[o]; c = np.cumsum(w)
    if c[-1] <= 0:
        return np.nan
    return float(v[min(len(v) - 1, int(np.searchsorted(c, q * c[-1])))])


def unit(name):
    pop = name.split("__", 1)[0]; sim = sim_of(name)
    W = pd.read_csv(PP.W19_DEPTH).set_index("sim_id"); w = W.loc[sim]
    raw, qa = {}, {}
    for key in CH:
        v, st, nmal = _read(sim, pop, key); raw[key] = v
        qa[key] = {"status": st, "rows": None if v is None else int(len(v)), "malformed_tokens_replaced": nmal}
    t = raw["time"]
    rec = {"population": pop, "sim_id": sim, "unit": name, "y": int(w.y), "descriptor": w.descriptor, "early_end_flag": int(w.early_end_flag) if pd.notna(w.early_end_flag) else None,
           "incomplete_flag": int(w.incomplete_flag) if pd.notna(w.incomplete_flag) else None, "record_flags": None if pd.isna(w.record_flags) else str(w.record_flags),
           "first_active_frame_ms": float(w.first_active_frame_ms) if pd.notna(w.first_active_frame_ms) else None,
           "active_cutoff_ms": float(w.active_cutoff_ms) if pd.notna(w.active_cutoff_ms) else None,
           "recording_end_ms": float(w.recording_end_ms) if pd.notna(w.recording_end_ms) else None, "qa": qa, "summaries": {}}
    if t is None:
        rec["time_status"] = "NO_TIME"; return rec
    dt = np.diff(t); med = float(np.median(dt)) if len(dt) else np.nan
    rec["time"] = {"rows": int(len(t)), "t_end_ms": float(t[-1] * 1e3), "dt_median_s": med, "nonmonotone_steps": int((dt <= 0).sum()),
                   "irregular_steps_1pct": int((np.abs(dt / med - 1) > 0.01).sum()) if med > 0 else None,
                   "max_rel_dt_dev": float(np.max(np.abs(dt / med - 1))) if med > 0 and len(dt) else None}
    wts = np.r_[dt, med] if len(dt) else np.array([np.nan])   # row weight = step to the next row (last row: median step)
    z = raw["bounds"]
    sig = {}; zvalid = None
    if z is not None:                                         # counters never hidden by a row mismatch
        qa["bounds"].update({"row_match": bool(len(z) == len(t)), "nonfinite": int((~np.isfinite(z)).sum()),
                             "no_melt_sentinel": int((np.isfinite(z) & (np.abs(z) >= PP.SENT)).sum())})
        if len(z) == len(t):
            zvalid = np.isfinite(z) & (np.abs(z) < PP.SENT)
            sig["depth"] = np.where(zvalid, np.maximum(0.0, -z) * 1e6, np.nan)                          # um
    for key in ("vmax", "ke", "laser", "tmax", "etot", "npart"):
        v = raw[key]
        if v is None:
            continue
        q = qa[key]; q["row_match"] = bool(len(v) == len(t)); q["nonfinite"] = int((~np.isfinite(v)).sum())
        q["nonpositive"] = int((np.isfinite(v) & (v <= 0)).sum())
        if key == "vmax":
            q["implausible_gt_100"] = int((np.isfinite(v) & (v > PP.V_PLAUSIBLE_MAX)).sum())
        if q["row_match"]:
            good = np.isfinite(v) & ((v <= PP.V_PLAUSIBLE_MAX) if key == "vmax" else True)
            sig[key] = np.where(good, v * (1e9 if key == "ke" else 1.0), np.nan)                        # KE in nJ
    # alignment (needs bounds for onset and the Week 19 cutoff)
    t_on = None
    if zvalid is not None and zvalid.any():
        t_on = float(t[np.argmax(zvalid)])
    cut = rec["active_cutoff_ms"] / 1e3 if rec["active_cutoff_ms"] is not None else None
    rec["alignment"] = {"t_on_ms": None if t_on is None else t_on * 1e3, "cutoff_ms": rec["active_cutoff_ms"],
                        "window_ms": None if (t_on is None or cut is None) else (cut - t_on) * 1e3}
    # native 1-us bins (whole record) for every aligned signal channel
    nb = int(np.ceil(t[-1] * 1e6 / BIN_US)) + 1; bi = np.minimum(nb - 1, (t * 1e6 / BIN_US).astype(int))
    arrays = {"bin_us": np.float32(BIN_US), "t_on_ms": np.float32(np.nan if t_on is None else t_on * 1e3),
              "cutoff_ms": np.float32(np.nan if cut is None else cut * 1e3)}
    for key, v in sig.items():
        ok = np.isfinite(v); cnt = np.bincount(bi[ok], minlength=nb)
        mx = np.full(nb, np.nan); mn = np.full(nb, np.nan); md = np.full(nb, np.nan)
        if ok.any():
            o = np.lexsort((v[ok], bi[ok])); vb, bb = v[ok][o], bi[ok][o]
            starts = np.r_[0, np.flatnonzero(np.diff(bb)) + 1]; ends = np.r_[starts[1:], len(bb)]; ub = bb[starts]
            mn[ub] = vb[starts]; mx[ub] = vb[ends - 1]; md[ub] = [np.median(vb[s:e]) for s, e in zip(starts, ends)]
        arrays[f"{key}_max"] = mx.astype(np.float32); arrays[f"{key}_med"] = md.astype(np.float32)
        arrays[f"{key}_min"] = mn.astype(np.float32); arrays[f"{key}_n"] = cnt.astype(np.int32)
    BINS.mkdir(parents=True, exist_ok=True)
    tmp = BINS / f"{name}.tmp.npz"; np.savez_compressed(tmp, **arrays); tmp.replace(BINS / f"{name}.npz")
    # summaries (only where the window is defined)
    if t_on is not None and cut is not None and cut > t_on:
        act = (t >= t_on) & (t <= cut); T0 = act & (t >= cut - 0.2 * (cut - t_on))
        for key, v in sig.items():
            s = {}
            for wname, m in (("active", act), ("T0", T0)):
                ok = m & np.isfinite(v)
                if ok.sum() < 5:
                    continue
                vv, ww = v[ok], wts[ok]
                s[f"row_median_{wname}"] = float(np.median(vv)); s[f"row_p99_{wname}"] = float(np.quantile(vv, 0.99))
                s[f"row_max_{wname}"] = float(vv.max())
                s[f"dur_mean_{wname}"] = float(np.sum(vv * ww) / np.sum(ww)); s[f"dur_median_{wname}"] = wq(vv, ww, 0.5)
                s[f"row_mean_{wname}"] = float(vv.mean())
                if wname == "active":
                    i = int(np.argmax(np.where(ok, v, -np.inf))); s["native_peak_ms_after_onset"] = float((t[i] - t_on) * 1e3)
                    s["n_rows_active"] = int(ok.sum())
                    # TEMPORAL_STRUCT 40-bin onset-normalised median curve (log for positive channels) -> its peak
                    pos = ok & (v > 0) if key in LOGPOS else ok
                    if pos.sum() >= 4 * K40:
                        ta = t[pos]; tau = (ta - ta[0]) / max(1e-12, ta[-1] - ta[0]); b40 = np.minimum(K40 - 1, (tau * K40).astype(int))
                        lv = np.log(v[pos]) if key in LOGPOS else v[pos]
                        curve = np.array([np.median(lv[b40 == k]) if np.any(b40 == k) else np.nan for k in range(K40)])
                        if np.isfinite(curve).all():
                            kb = int(np.argmax(curve)); s["bin40_peak"] = float(np.exp(curve[kb]) if key in LOGPOS else curve[kb])
                            s["bin40_peak_ms_after_onset"] = float((ta[0] - t_on + (kb + 0.5) / K40 * (ta[-1] - ta[0])) * 1e3)
                            s["bin40_width_ms"] = float((ta[-1] - ta[0]) / K40 * 1e3)
            rec["summaries"][key] = s
    return rec


def work():
    RC.limit_threads(1)
    names = [unit_name(p, s) for p, s in run_list()]
    RC.run_units(names, unit, UNITS, OUT / "locks", OUT / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    {"work": work}[sys.argv[1]]()
