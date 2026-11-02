"""GT section 9: the ~300 um depth pile-up. Internal evidence only (no parameter file holds the domain z-extent: the dataset's per-run
parameters.json has exactly four keys - laser_power, scan_speed_x, laser_spot_size, substrate_temperature - per the Week 11 arrival audit
validator, and the Week 7 file inventory lists only .png, .dat, .gif, .csv, .json and one extension-less file). Writes ceiling/CEILING_EVIDENCE.json.
    python -m src.gt_ceiling run
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import src.gt_data as GD
import src.rc18_common as RC
import src.rc19_pool as P

OUT = GD.OUT / "ceiling"


def run():
    M = P.manifest(); R = GD.runs().reindex(M.index); cap = (R.ceil_rows > 0).to_numpy()
    lev = R.ceil_plateau_median_um[cap]; res = {"utc": RC.utc(), "rule_um": GD.CEIL_UM}
    res["runs_with_rows_at_or_above_295um"] = int(cap.sum()); res["by_batch"] = R[cap].groupby("batch").size().to_dict()
    res["labels_of_ceiling_runs"] = M.y[cap].value_counts().to_dict()
    res["plateau_level_um"] = {"median": float(lev.median()), "q05": float(lev.quantile(0.05)), "q25": float(lev.quantile(0.25)), "q75": float(lev.quantile(0.75)),
                               "q95": float(lev.quantile(0.95)), "sd": float(lev.std()), "by_batch_median": R[cap].groupby("batch").ceil_plateau_median_um.median().to_dict()}
    res["plateau_level_vs_inputs_spearman"] = {c: float(spearmanr(lev, M[c][cap]).statistic) for c in ("P", "VX", "LS", "ST")}
    res["A_max_um_ceiling_runs"] = {"median": float(R.A_um[cap].median()), "max": float(R.A_um[cap].max()), "min": float(R.A_um[cap].min())}
    res["whole_record_max_um"] = {"max": float(R.max_depth_whole_um.max()), "runs_ge_295_outside_active": int(((R.max_depth_whole_um >= 295) & ~cap).sum())}
    res["time_at_ceiling"] = {"frac_active_rows_median": float(R.ceil_frac_active_rows[cap].median()), "frac_active_rows_q25_q75": [float(R.ceil_frac_active_rows[cap].quantile(q)) for q in (0.25, 0.75)],
                              "longest_episode_ms_median": float(R.ceil_longest_ms[cap].median()), "episodes_median": float(R.ceil_episodes[cap].median()),
                              "first_reach_ms_median": float(R.ceil_first_ms[cap].median())}
    A_ = R.A_um.to_numpy(float); k = (M.y == 1).to_numpy() & np.isfinite(A_)
    hist = np.histogram(A_[k], bins=np.arange(0, 320, 10))
    res["keyhole_A_histogram_10um"] = {f"{int(lo)}-{int(lo) + 10}": int(c) for lo, c in zip(hist[1][:-1], hist[0])}
    res["gap_check"] = {"keyhole_A_in_[280,295)": int(((A_ >= 280) & (A_ < 295) & k).sum()), "keyhole_A_in_[295,310)": int(((A_ >= 295) & (A_ < 310) & k).sum()),
                        "keyhole_A_in_[250,280)": int(((A_ >= 250) & (A_ < 280) & k).sum())}
    res["width_has_no_pile_up"] = {"W_A_ge_295_runs": int((R.W_A_um >= 295).sum()), "W_A_max_um": float(R.W_A_um.max())}
    res["sources_searched"] = ["local raw cache data/raw/sph_v2/<revision>/<run>: only frames.csv and monitor/*.dat (no parameter file)",
                               "src/week11_new_data_arrival_audit (tests): parameters.json holds exactly four keys (laser_power, scan_speed_x, laser_spot_size, substrate_temperature)",
                               "outputs/week7_01_sph_v2_audit/file_type_counts.csv: .png, .dat, .gif, .csv, .json (407 files, 120 kB in total) and one extension-less file",
                               "outputs/week19_temporal_regime_audit/REPORT.md hypothesis 3 (unverified)", "run-folder names: P, VX, LS, ST, M, XI, XF, XL, TE, DT, H (no z-extent)"]
    res["verdict"] = ("HYPOTHESIS (not verified): a hard geometric lower bound near z = -300 um (substrate / domain floor) is consistent with every internal check; "
                      "no available file states the domain z-extent")
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "CEILING_EVIDENCE.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"run": run}[sys.argv[1]]()
