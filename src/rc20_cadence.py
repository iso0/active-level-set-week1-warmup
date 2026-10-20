"""RC20 documentary repair: monitor cadence for the spike-duration interpretation (no target or label is changed).

The RC19B duration audit (opus_rc19b/DURATION_ZERO_AUDIT.json, "positives_with_at_most_2_rows" = 46) divided the spike
duration by the solver time step DT parsed from the run name (_DT-..._). DT is the solver step, NOT the cadence of the monitor
rows. The duration D = vmax_spike_us is a sum of time.dat row hold times (src/jdl_physical_pilot.summarize), so the number of
monitor rows in a spike is D / (monitor row interval). This script recomputes that count from the actual time.dat cadence
(SUMMARIES.csv time_dt_median_s, computed from time.dat by the RC18 data QA) and spot-checks it against the raw time.dat files.
Existing duration values and targets are unchanged.
    python -m src.rc20_cadence
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_pool as P

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc20" / "repairs"


def main():
    RC.limit_threads(1); M = P.manifest(); S = pd.read_csv(RC.CAMP / "data" / "SUMMARIES.csv").set_index("sim_id").reindex(M.index)
    D = M.vmax_spike_us; ok = D.notna(); pos = ok & (D > 0)
    dt_mon = S.time_dt_median_s * 1e6
    dt_sol = pd.Series(M.index, index=M.index).str.extract(r"_DT-([0-9pe\-]+)_")[0].str.replace("p", ".").astype(float) * 1e6
    rows_mon = (D / dt_mon).where(pos); rows_sol = (D / dt_sol).where(pos)
    q = lambda s: np.nanquantile(s, [0, .1, .25, .5, .75, .9, 1]).round(3).tolist()
    # spot check against raw time.dat (3 NEW, 2 OLD)
    import src.jdl_physical_data2 as PD2
    spots = []
    for b, k in (("NEW", 3), ("OLD", 2)):
        for s in list(M.index[(M.source_batch == b) & pos])[:k]:
            try:
                t = np.loadtxt(PD2.local(s, "time.dat", b), ndmin=1); spots.append({"sim_id": s, "batch": b, "raw_median_dt_us": float(np.median(np.diff(t)) * 1e6),
                                                                                  "summaries_dt_us": float(dt_mon[s]), "solver_DT_us": float(dt_sol[s])})
            except Exception as ex:
                spots.append({"sim_id": s, "batch": b, "error": f"{type(ex).__name__}: {ex}"[:200]})
    spot_ok = all(abs(x["raw_median_dt_us"] - x["summaries_dt_us"]) <= 1e-6 * max(1.0, x["summaries_dt_us"]) for x in spots if "raw_median_dt_us" in x) and any("raw_median_dt_us" in x for x in spots)
    out = {"valid_durations": int(ok.sum()), "positives": int(pos.sum()), "zeros": int((ok & (D == 0)).sum()),
           "monitor_row_interval_us_quantiles": q(dt_mon[ok]), "solver_DT_us_quantiles": q(dt_sol[ok]),
           "monitor_over_solver_ratio_quantiles": q((dt_mon / dt_sol)[ok]),
           "runs_with_irregular_monitor_steps_gt_1pct": int((S.time_irregular_steps_1pct[ok] > 0).sum()),
           "max_rel_dt_dev_quantiles": q(S.time_max_rel_dt_dev[ok]),
           "positive_duration_in_MONITOR_rows_quantiles": q(rows_mon[pos]),
           "positives_le_1_monitor_row": int((rows_mon[pos] <= 1.01).sum()), "positives_le_2_monitor_rows": int((rows_mon[pos] <= 2.01).sum()),
           "positives_le_5_monitor_rows": int((rows_mon[pos] <= 5.01).sum()),
           "previous_audit_le_2_rows_using_solver_DT": 46, "recomputed_le_2_using_solver_DT": int((rows_sol[pos] <= 2.01).sum()),
           "spot_check_raw_time_dat": spots, "spot_check_PASS": bool(spot_ok),
           "note": "Durations and the 0.60 duration R2 target are unchanged; only the 'rows' interpretation is repaired."}
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "DURATION_CADENCE_REPAIR.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps(out, indent=1, default=str)); return out


if __name__ == "__main__":
    main()
