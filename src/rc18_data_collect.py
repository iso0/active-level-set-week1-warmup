"""RC18 fixes A2/A3 — collect the per-run units of src/rc18_data.py into QA and summary tables (no fits).

Writes outputs/research_campaign_20261018/opus/data/:
  QA_TABLE.csv            one row per run x channel: present, rows, row_match, nonfinite, sentinel, implausible, nonpositive
  SUMMARIES.csv           one row per run: row-quantile, duration-weighted and alignment summaries per channel
  DATA_QA_REPORT.md       coverage per channel (A2), separated QA counters (A3), row vs duration weighting, 40-bin peak loss
    python -m src.rc18_data_collect
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc18_data as D


def main():
    rows, srows = [], []
    for f in sorted(D.UNITS.glob("*.json.gz")):
        r = RC.read_json_gz(f)
        for ch, q in r["qa"].items():
            rows.append({"population": r["population"], "sim_id": r["sim_id"], "channel": ch, **{k: q.get(k) for k in
                         ("status", "rows", "row_match", "nonfinite", "no_melt_sentinel", "implausible_gt_100", "nonpositive", "malformed_tokens_replaced")}})
        s = {"population": r["population"], "sim_id": r["sim_id"], "unit": r["unit"], "y": r["y"], "descriptor": r["descriptor"],
             "early_end_flag": r["early_end_flag"], "record_flags": r["record_flags"], **{f"time_{k}": v for k, v in (r.get("time") or {}).items()},
             **{f"align_{k}": v for k, v in r["alignment"].items()}}
        for ch, d in r["summaries"].items():
            s.update({f"{ch}__{k}": v for k, v in d.items()})
        srows.append(s)
    Q, S = pd.DataFrame(rows), pd.DataFrame(srows)
    D.OUT.mkdir(parents=True, exist_ok=True)
    Q.to_csv(D.OUT / "QA_TABLE.csv", index=False, lineterminator="\n"); S.to_csv(D.OUT / "SUMMARIES.csv", index=False, lineterminator="\n")
    L = ["# RC18 data layer: channel coverage, separated QA, summary definitions (fixes A2 and A3)", "",
         "Every channel is read independently (src/rc18_data.py). A missing or malformed file removes only that channel; a row "
         "mismatch is recorded separately from non-finite values and never hides the other counters. Full simulation IDs throughout.", ""]
    # A2 coverage per channel
    L += ["## A2. Channel coverage (usable = file present and row count equal to time.dat)", "", "| population | channel | runs | present | row-matched (usable) |", "|---|---|---|---|---|"]
    for (pop, ch), g in Q[Q.channel != "time"].groupby(["population", "channel"]):
        L.append(f"| {pop} | {ch} | {g.sim_id.nunique()} | {int((g.status == 'ok').sum())} | {int((g.row_match == True).sum())} |")
    old = Q[Q.population == "OLD"]; nov = set(old[(old.channel == "vmax") & (old.status != "ok")].sim_id)
    keep = old[old.sim_id.isin(nov) & old.channel.isin(["bounds", "ke"]) & (old.row_match == True)]
    L += ["", f"OLD runs without a remote velocity file: {len(nov)}. Of these, depth (bounds) is usable in "
          f"{int((keep.channel == 'bounds').sum())} and KE in {int((keep.channel == 'ke').sum())}: the frozen TEMPORAL_STRUCT loader dropped them; "
          "the RC18 loader keeps them, and comparisons report per-channel coverage plus the matched subset.", ""]
    # A3 separated QA
    L += ["## A3. Separated QA counters (runs with any count > 0)", "", "| population | sim_id | channel | rows | row_match | non-finite | no-melt sentinel | implausible > 100 m/s |", "|---|---|---|---|---|---|---|---|"]
    flag = Q[(Q.row_match == False) | (Q.nonfinite.fillna(0) > 0) | (Q.implausible_gt_100.fillna(0) > 0) | (Q.status != "ok")]
    for _, r in flag.sort_values(["population", "sim_id", "channel"]).iterrows():
        L.append(f"| {r.population} | `{r.sim_id}` | {r.channel} | {r.rows} | {r.row_match} | {r.nonfinite} | {r.no_melt_sentinel} | {r.implausible_gt_100} |")
    # time grid and weighting
    L += ["", "## Time grid: row quantiles vs duration weighting", "",
          f"Runs with irregular steps (|dt/median - 1| > 1 %): {int((S.time_irregular_steps_1pct > 0).sum())} of {len(S)}; median share of irregular steps "
          f"{float((S.time_irregular_steps_1pct / S.time_rows).median()):.3f}. So a row median is not a duration median.", "",
          "| channel | median relative difference (duration-weighted median vs row median, T0) | 90th percentile |", "|---|---|---|"]
    for ch in D.SIGNAL:
        a, b = S.get(f"{ch}__dur_median_T0"), S.get(f"{ch}__row_median_T0")
        if a is None:
            continue
        rel = ((a - b) / b.abs()).abs().dropna()
        L.append(f"| {ch} | {rel.median():.4f} | {rel.quantile(0.9):.4f} |")
    # 40-bin peak attenuation
    L += ["", "## What the 40-bin onset-normalised median curve does to short peaks (TEMPORAL_STRUCT convention)", "",
          "Native peak = maximum over the valid rows of the active window; 40-bin peak = maximum of the per-bin medians.", "",
          "| population | channel | runs | median 40-bin / native peak | 10th pct | median abs. peak-time error (ms) | median bin width (ms) |", "|---|---|---|---|---|---|---|"]
    for pop in ("NEW", "OLD"):
        Sp = S[S.population == pop]
        for ch in D.SIGNAL:
            if f"{ch}__bin40_peak" not in Sp:
                continue
            ok = Sp[f"{ch}__bin40_peak"].notna() & Sp[f"{ch}__row_max_active"].notna()
            if not ok.any():
                continue
            ratio = Sp.loc[ok, f"{ch}__bin40_peak"] / Sp.loc[ok, f"{ch}__row_max_active"]
            terr = (Sp.loc[ok, f"{ch}__bin40_peak_ms_after_onset"] - Sp.loc[ok, f"{ch}__native_peak_ms_after_onset"]).abs()
            L.append(f"| {pop} | {ch} | {int(ok.sum())} | {ratio.median():.3f} | {ratio.quantile(0.1):.3f} | {terr.median():.3f} | {Sp.loc[ok, f'{ch}__bin40_width_ms'].median():.3f} |")
    (D.OUT / "DATA_QA_REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L[:60]))


if __name__ == "__main__":
    main()
