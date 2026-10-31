"""DESCRIPTIVE first look for Ioan's 30-10 request (not a method attempt; nothing in the repo is written or changed).
Melt-pool width per run from the SAME monitor file and the SAME audited Week 19 code path that gives the pooled depth A
(src.week19_series.process, unchanged): width = y-extent of position-bounds_melt.dat, in the same windows as depth.
Raw files are read (read-only) from the main checkout's verified data/raw copy.
    python width_extract.py   (run from the worktree root)
"""
import concurrent.futures
import sys
from pathlib import Path

import numpy as np
import pandas as pd

WT = Path(r"C:\Users\ozgur\Documents\thesis\.claude\worktrees\joint-depth-label-dev")
MAIN_RAW = Path(r"C:\Users\ozgur\Documents\thesis\data\raw\sph_v2")
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(WT))


def one(args):
    sid, camp, frames = args
    import src.week19_sources as S
    S.RAW = MAIN_RAW                                   # read-only redirect to the verified main-checkout copy
    import src.week19_series as SE
    u_ref = 111.0
    o, _, s = SE.series_for(sid, camp, frames, u_ref)
    r = {"sim_id": sid, "A_active_max_um_recomputed": o.get("A_active_max_um", np.nan), "failure": o.get("failure", "")}
    if s is None:
        return r
    d, w, act, t0, ok = s["depth_um"], s["width_um"], s["active"], s["t0"], s["valid"]
    if act.any():
        ia = np.flatnonzero(act)
        r["W_active_max_um"] = float(np.nanmax(w[ia]))
        r["W_at_Amax_um"] = float(w[ia[np.nanargmax(d[ia])]])
        r["W_active_median_um"] = float(np.nanmedian(w[ia]))
    if (t0 & ok).any():
        r["W_T0_median_um"] = float(np.nanmedian(w[t0 & ok]))
        r["D_T0_median_um"] = float(np.nanmedian(d[t0 & ok]))
    return r


def main():
    F = pd.read_csv(WT / "outputs/week19_temporal_regime_audit/tables/frame_level_map.csv.gz",
                    usecols=["sim_id", "frame_pos", "timestep", "code", "campaign"])
    M = pd.read_csv(WT / "outputs/research_campaign_20261018/opus_pooled/data/POOLED_MANIFEST.csv")
    jobs = []
    for sid in M.sim_id:
        g = F[F.sim_id == sid]
        jobs.append((sid, g.campaign.iloc[0], g[["sim_id", "frame_pos", "timestep", "code"]]))
    rows = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=3) as ex:
        for i, r in enumerate(ex.map(one, jobs, chunksize=8), 1):
            rows.append(r)
            if i % 100 == 0:
                print(i, flush=True)
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "width_per_run.csv", index=False, lineterminator="\n")
    chk = R.merge(M[["sim_id", "A_um"]], on="sim_id")
    diff = (chk.A_active_max_um_recomputed - chk.A_um).abs()
    print("rows", len(R), "failures", int((R.failure.fillna("") != "").sum()),
          "depth reproduces pooled A: max |diff| =", float(diff.max()), "n compared", int(diff.notna().sum()))


if __name__ == "__main__":
    main()
