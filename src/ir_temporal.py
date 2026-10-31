"""IR part F summaries (PROTOCOL_IR.md section 8): within-run coupling of depth(t) with the other monitor signals. DESCRIPTIVE.
Inputs: temporal/per_run_time_stats.csv and temporal/F3_event_windows.npz written by src.ir_data (extract).
    python -m src.ir_temporal run
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

import src.ir_data as IRD
import src.rc19_pool as P

OUT = IRD.TEMP
SIG = IRD.SIGNALS
NB = 2000
WINDOWS = {"pre_100_50": (-100, -51), "pre_50_1": (-50, -1), "post_0_50": (0, 50), "post_51_100": (51, 100)}


def f1_f2(S):
    rows = []
    for k in SIG:
        for cls, g in (("all", S), ("conduction", S[S.y == 0]), ("keyhole", S[S.y == 1])):
            r = g.get(f"F1_rho_{k}"); tl = g.get(f"F2_tau_level_{k}"); td = g.get(f"F2_tau_diff_{k}"); rl = g.get(f"F2_r_level_{k}"); rd = g.get(f"F2_r_diff_{k}")
            if r is None:
                continue
            r, tl, td, rl, rd = (x.dropna() for x in (r, tl, td, rl, rd))
            rows.append({"signal": k, "class": cls, "n_F1": int(len(r)), "rho_median": float(r.median()) if len(r) else np.nan,
                         "rho_q25": float(r.quantile(0.25)) if len(r) else np.nan, "rho_q75": float(r.quantile(0.75)) if len(r) else np.nan,
                         "share_rho_gt_0.5": float((r > 0.5).mean()) if len(r) else np.nan,
                         "n_F2": int(len(tl)), "tau_level_median_us": float(tl.median()) if len(tl) else np.nan, "share_level_s_leads": float((tl > 0).mean()) if len(tl) else np.nan,
                         "share_level_at_bound": float((tl.abs() == IRD.LAG_US).mean()) if len(tl) else np.nan, "r_level_median": float(rl.median()) if len(rl) else np.nan,
                         "tau_diff_median_us": float(td.median()) if len(td) else np.nan, "share_diff_s_leads": float((td > 0).mean()) if len(td) else np.nan,
                         "share_diff_at_bound": float((td.abs() == IRD.LAG_US).mean()) if len(td) else np.nan, "r_diff_median": float(rd.median()) if len(rd) else np.nan})
    return pd.DataFrame(rows)


def f3(E):
    lag = E["lag_us"]; out, curves = [], {}; rng = np.random.default_rng(31)
    for k in ("D",) + SIG:
        if f"K_{k}" not in E.files:
            continue
        Kw, Cw = np.asarray(E[f"K_{k}"], float), np.asarray(E[f"C_{k}"], float); ok = np.isfinite(Kw).sum(1) > 150
        Kw, Cw = Kw[ok], Cw[ok]; n = len(Kw)
        mK, mC = np.nanmean(Kw, 0), np.nanmean(Cw, 0); bs = np.empty((NB, len(lag)))
        for b in range(NB):
            i = rng.integers(0, n, n); bs[b] = np.nanmean(Kw[i], 0) - np.nanmean(Cw[i], 0)
        curves[k] = {"lag_us": lag.tolist(), "K_mean": mK.tolist(), "control_mean": mC.tolist(), "diff_lo95": np.nanpercentile(bs, 2.5, 0).tolist(), "diff_hi95": np.nanpercentile(bs, 97.5, 0).tolist()}
        for wn, (a, b_) in WINDOWS.items():
            sel = (lag >= a) & (lag <= b_); dK = np.nanmean(Kw[:, sel], 1); dC = np.nanmean(Cw[:, sel], 1); d = dK - dC; bb = np.empty(NB)
            for j in range(NB):
                i = rng.integers(0, n, n); bb[j] = np.nanmean(d[i])
            out.append({"signal": k, "window": wn, "runs": n, "K_aligned_mean_z": float(np.nanmean(dK)), "control_mean_z": float(np.nanmean(dC)), "diff": float(np.nanmean(d)),
                        "diff_lo95": float(np.nanpercentile(bb, 2.5)), "diff_hi95": float(np.nanpercentile(bb, 97.5))})
        # earliest lag at which the K-aligned mean exceeds the control with the bootstrap band above zero, continuously up to lag 0
        above = np.asarray(curves[k]["diff_lo95"]) > 0; first = None
        for j in range(len(lag)):
            if lag[j] > 0:
                break
            if above[j:np.searchsorted(lag, 0) + 1].all():
                first = int(lag[j]); break
        curves[k]["earliest_sustained_rise_before_K_us"] = first
    return pd.DataFrame(out), curves


def f4(S):
    M = P.manifest(); good = ~M.short_record.astype(bool); A = M.log_A_um; y = M.y.astype(int); rows = []
    for k in ("D",) + SIG:
        c = f"F4_early_med_{k}"
        if c not in S:
            continue
        v = S[c].reindex(M.index); m = good & v.notna() & A.notna(); vv = np.log(v[m]) if (v[m] > 0).all() else v[m]
        auc = roc_auc_score(y[m], vv); rows.append({"signal": k, "n": int(m.sum()), "spearman_with_final_logA": float(spearmanr(vv, A[m]).statistic), "label_AUC": float(max(auc, 1 - auc))})
    return pd.DataFrame(rows)


def run():
    S = pd.read_csv(OUT / "per_run_time_stats.csv", index_col="sim_id"); E = np.load(OUT / "F3_event_windows.npz")
    T12 = f1_f2(S); T12.to_csv(OUT / "F1_F2_summary.csv", index=False, lineterminator="\n")
    T3, curves = f3(E); T3.to_csv(OUT / "F3_event_windows_summary.csv", index=False, lineterminator="\n")
    T4 = f4(S); T4.to_csv(OUT / "F4_early_window.csv", index=False, lineterminator="\n")
    res = {"evidence": "DESCRIPTIVE (within-run monitor signals, true values)", "keyhole_event_runs": int(len(E["sim_ids"])),
           "earliest_sustained_rise_before_K_us": {k: v["earliest_sustained_rise_before_K_us"] for k, v in curves.items()}}
    (OUT / "PART_F_RESULTS.json").write_text(json.dumps({**res, "curves": curves}, indent=1, default=float), encoding="utf-8")
    pd.set_option("display.width", 250)
    print(T12[T12["class"] != "all"].round(3).to_string(index=False)); print(T3.round(3).to_string(index=False)); print(T4.round(3).to_string(index=False)); print(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    {"run": run}[sys.argv[1]]()
