"""IR post-registration EXTRAS (interpretation aids, labelled EXTRA; they change no registered rule or result):
  E1  the literature keyholing threshold W/D <= 2.75 (Sheikh et al. 2023, Eq. 8), found in part G after registration;
  E2  the ~300 um depth ceiling (Week 19 REPORT hypothesis 3: a geometric limit such as the substrate / domain depth, unverified):
      how many runs sit at it, and parts A1 / A3 / F1 / F3 for Keyhole runs below the ceiling (A < 295 um) vs at it.
    python -m src.ir_extras
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, theilslopes

import src.ir_data as IRD
import src.ir_desc as DS

OUT = IRD.OUT / "extras"
CAP_UM = 295.0


def run():
    OUT.mkdir(parents=True, exist_ok=True); X = pd.read_csv(IRD.OUT / "descriptive" / "analysis_table.csv", index_col=0); res = {"label": "EXTRA (added after registration; interpretation aid)"}
    good = (~X.short.astype(bool)) & X.D.notna() & X.W_A.notna(); A = np.exp(X.D); W = np.exp(X.W_A); y = X.y
    wd = (W / A)[good]; yy = y[good].to_numpy(); hat = (wd <= 2.75).to_numpy()
    res["E1_criterion_W_over_D_le_2.75"] = {"BA": float(0.5 * (hat[yy == 1].mean() + (~hat[yy == 0]).mean())), "sensitivity": float(hat[yy == 1].mean()), "specificity": float((~hat[yy == 0]).mean()), "n": int(good.sum())}
    cap = A >= CAP_UM
    res["E2_ceiling_counts"] = {"threshold_um": CAP_UM, "runs_at_ceiling": int(cap.sum()), "keyhole_at_ceiling": int((cap & (y == 1)).sum()), "keyhole_total": int((y == 1).sum()),
                                "conduction_at_ceiling": int((cap & (y == 0)).sum()),
                                "by_batch": {b: int((cap & (y == 1) & (X.batch == b)).sum()) for b in ("OLD", "NEW")},
                                "A_quantiles_keyhole_um": {str(q): float(A[y == 1].quantile(q)) for q in (0.1, 0.25, 0.5, 0.75, 0.9)}}
    kb = good & (y == 1) & ~cap; kc = good & (y == 1) & cap
    s = theilslopes(X.D[kb], X.W_A[kb]); res["E2_theil_sen_keyhole_below_ceiling"] = {"slope": float(s.slope), "lo95": float(s.low_slope), "hi95": float(s.high_slope), "n": int(kb.sum())}
    ar = (A / W)[kb]; res["E2_aspect_D_over_W_keyhole_below_ceiling"] = {"median": float(ar.median()), "q25": float(ar.quantile(0.25)), "q75": float(ar.quantile(0.75))}
    rows = []; rng = np.random.default_rng(DS.SEED)
    for sub, m0 in (("keyhole_below_ceiling", good & (y == 1) & ~cap), ("keyhole_at_ceiling", good & (y == 1) & cap)):
        for v in DS.VARS:
            if v == "D":
                continue
            m = m0 & X[v].notna()
            if m.sum() < 10:
                continue
            r, lo, hi = DS._boot_rho(X.D[m].to_numpy(), X[v][m].to_numpy(), rng)
            rows.append({"subset": sub, "var": v, "n": int(m.sum()), "rho": r, "lo95": lo, "hi95": hi})
    pd.DataFrame(rows).to_csv(OUT / "E2_keyhole_rho_by_ceiling.csv", index=False, lineterminator="\n")
    S = pd.read_csv(IRD.TEMP / "per_run_time_stats.csv", index_col="sim_id"); f1 = []
    for sub, m0 in (("keyhole_below_ceiling", (y == 1) & ~cap), ("keyhole_at_ceiling", (y == 1) & cap), ("conduction", y == 0)):
        ids = X.index[m0]
        for k in IRD.SIGNALS:
            r = S.reindex(ids)[f"F1_rho_{k}"].dropna()
            f1.append({"subset": sub, "signal": k, "n": int(len(r)), "rho_median": float(r.median()) if len(r) else np.nan})
    pd.DataFrame(f1).to_csv(OUT / "E2_F1_by_ceiling.csv", index=False, lineterminator="\n")
    E = np.load(IRD.TEMP / "F3_event_windows.npz"); sid = E["sim_ids"].astype(str); lag = E["lag_us"]; capd = cap.reindex(sid).to_numpy(bool); f3 = {}
    for k in ("D", "T", "V", "LASER", "KE", "W"):
        if f"K_{k}" not in E.files:
            continue
        for sub, msk in (("below_ceiling", ~capd), ("at_ceiling", capd)):
            Kw, Cw = np.asarray(E[f"K_{k}"], float)[msk], np.asarray(E[f"C_{k}"], float)[msk]; d = Kw - Cw; sel = (lag >= -50) & (lag <= -1); sel2 = (lag >= 0) & (lag <= 50)
            pre = np.nanmean(d[:, sel], 1); post = np.nanmean(d[:, sel2], 1); bb = [np.nanmean(pre[rng.integers(0, len(pre), len(pre))]) for _ in range(2000)]
            f3[f"{k}|{sub}"] = {"runs": int(msk.sum()), "pre_50_1_diff": float(np.nanmean(pre)), "pre_lo95": float(np.nanpercentile(bb, 2.5)), "pre_hi95": float(np.nanpercentile(bb, 97.5)), "post_0_50_diff": float(np.nanmean(post))}
    res["E2_F3_by_ceiling"] = f3
    (OUT / "EXTRAS.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    pd.set_option("display.width", 220)
    print(json.dumps({k: v for k, v in res.items() if k != "E2_F3_by_ceiling"}, indent=1, default=float)); print(json.dumps(f3, indent=1, default=float))
    print(pd.DataFrame(rows).pivot(index="var", columns="subset", values="rho").round(3).to_string()); print(pd.DataFrame(f1).pivot(index="signal", columns="subset", values="rho_median").round(3).to_string())


if __name__ == "__main__":
    run()
