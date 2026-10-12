"""Week 20 Track 2 — depth-trajectory data for the temporal-GP development (NEW, shared label-blind paid paths).

No model is fitted here.  For every eligible NEW run with an aligned bounds/time record this module extracts the
native active-window trajectory y(s) = log(1 + depth_um) on s = t / derived_exit, with
  * depth = 0 on rows without melt (sentinel / non-finite bounds rows; NEW has no malformed rows),
  * planned horizon  s_plan = min(TE, 0.9 * exit) / exit   (scheduled settings, known before the query),
  * observed window  s_obs  = min(recording end, 0.9 * exit) / exit  (actual support; never stretched or filled).
Compression: per-bin means on a uniform s-grid of K bins over [0, 0.9] plus each run's exact native maximum.  The
resolution K is chosen per checkpoint from the PAID training runs only (rule in RESOLUTION_RULE).

Steps: python -m src.week20_track2_data extract
"""
from __future__ import annotations

import gzip
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "week20_active_temporal_development"
T2 = OUT / "track2"
CACHE = OUT / "_cache" / "track2"
AUDIT = ROOT / "outputs" / "week19_temporal_regime_audit"
PILOT = ROOT / "outputs" / "week19_temporal_regime_dev_pilot"
S_MAX = 0.9
K_CANDIDATES = (90, 180, 360, 720)
TAU = 0.04          # median training RMSE(native - bin-mean reconstruction) in log1p units (about 4 % in depth)
RESOLUTION_RULE = (f"For each checkpoint, K is the smallest value in {K_CANDIDATES} whose median, over the PAID training runs, of the "
                   f"RMSE between the native log1p-depth series and its bin-mean reconstruction (observed window only) is <= {TAU}; "
                   f"if none qualifies, K = {K_CANDIDATES[-1]} and the checkpoint is flagged.  Test runs never influence K.")


def registry():
    r = pd.read_csv(AUDIT / "tables/temporal_registry.csv")
    r = r[r.campaign == "NEW"].copy()
    r["TE_ms"] = r.TE * 1e3
    r["s_plan"] = np.minimum(r.TE_ms, S_MAX * r.derived_exit_ms) / r.derived_exit_ms
    r["s_obs"] = np.minimum(r.recording_end_ms, S_MAX * r.derived_exit_ms) / r.derived_exit_ms
    r["truncated_before_plan"] = r.s_obs < r.s_plan - 1e-4          # recording ended before the scheduled horizon
    return r.set_index("sim_id")


def extract():
    """Native active-window trajectories for every NEW run (cached pickle, git-ignored)."""
    from src.week19_temporal_audit import _series_cache
    reg = registry()
    ids = reg.index.tolist()
    ser = _series_cache(ids, reg.reset_index())
    out = {}
    for s in ids:
        z = ser.get(s)
        r = reg.loc[s]
        if z is None:
            out[s] = None                                            # bounds/time mismatch: no trajectory (H-e7dbd8e5ce)
            continue
        t = np.asarray(z["t_ms"], float); d = np.asarray(z["depth_um"], float); val = np.asarray(z["valid"], bool)
        sv = t / r.derived_exit_ms
        keep = sv <= r.s_obs + 1e-12
        y = np.log1p(np.where(val, d, 0.0))
        out[s] = {"s": sv[keep], "y": y[keep], "valid": val[keep], "t_ms": t[keep]}
    CACHE.mkdir(parents=True, exist_ok=True)
    with gzip.open(CACHE / "native_trajectories.pkl.gz", "wb") as fh:
        pickle.dump(out, fh, protocol=pickle.HIGHEST_PROTOCOL)
    summ = pd.DataFrame([{"sim_id": s, "rows": (len(v["s"]) if v else 0), "s_obs": reg.loc[s, "s_obs"], "s_plan": reg.loc[s, "s_plan"],
                          "truncated_before_plan": bool(reg.loc[s, "truncated_before_plan"]),
                          "native_max_log1p": float(v["y"].max()) if v else np.nan, "A_um": reg.loc[s, "A_active_max_um"]} for s, v in out.items()])
    chk = summ.dropna(subset=["A_um"])
    summ["A_check_abs_diff_um"] = np.nan
    summ.loc[chk.index, "A_check_abs_diff_um"] = np.abs(np.expm1(chk.native_max_log1p) - chk.A_um)
    return out, summ


def load_native():
    with gzip.open(CACHE / "native_trajectories.pkl.gz", "rb") as fh:
        return pickle.load(fh)


def bin_means(tr, K):
    """Bin means of y over the run's observed window on the common grid; returns (bin index, s centre, mean, count)."""
    edges = np.linspace(0.0, S_MAX, K + 1)
    b = np.clip(np.searchsorted(edges, tr["s"], side="right") - 1, 0, K - 1)
    df = pd.DataFrame({"b": b, "s": tr["s"], "y": tr["y"]})
    g = df.groupby("b").agg(s=("s", "mean"), y=("y", "mean"), n=("y", "size")).reset_index()
    return g


def compression_rmse(tr, K):
    g = bin_means(tr, K)
    edges = np.linspace(0.0, S_MAX, K + 1)
    b = np.clip(np.searchsorted(edges, tr["s"], side="right") - 1, 0, K - 1)
    rec = pd.Series(g.y.to_numpy(), index=g.b.to_numpy()).reindex(b).to_numpy()
    return float(np.sqrt(np.mean((tr["y"] - rec) ** 2))), float(tr["y"].max() - g.y.max())


def choose_K(train_ids, native):
    """Training-only resolution rule (RESOLUTION_RULE).  Returns (K, table of per-candidate medians)."""
    rows = []
    for K in K_CANDIDATES:
        e = [compression_rmse(native[s], K) for s in train_ids if native.get(s) is not None]
        rows.append({"K": K, "median_rmse": float(np.median([x[0] for x in e])), "p90_rmse": float(np.quantile([x[0] for x in e], .9)),
                     "median_max_loss": float(np.median([x[1] for x in e])), "n_runs": len(e)})
    t = pd.DataFrame(rows)
    ok = t[t.median_rmse <= TAU]
    return (int(ok.K.iloc[0]) if len(ok) else int(K_CANDIDATES[-1])), t


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "extract"
    if step == "extract":
        out, summ = extract()
        T2.mkdir(parents=True, exist_ok=True)
        summ.to_csv(T2 / "trajectory_inventory.csv", index=False, lineterminator="\n")
        print(summ.describe().T.to_string()); print("A check max abs diff (um):", summ.A_check_abs_diff_um.max())
