"""Temporal stopping-rule audit (diagnostic only; reads the stored fit traces and checkpoint training targets).

Two implementation questions about src/jdl_temporal_svgp.train (frozen in 29ca7364; nothing here changes it):
1. Training uses VariationalELBO(num_data = n); the probe check builds VariationalELBO(num_data = len(probe)).  gpytorch
   returns (1/b) sum_batch E_q[log p(y_i | f_i)] - KL(q(u) || p(u)) / num_data, so the reported probe value is
       ELBO_probe = mean_{i in probe} E_q[log p(y_i | f_i)] - KL / m,       m = min(8192, n),
   the per-point ELBO of the probe subset treated as a whole data set, not the per-point training objective
   mean_all E_q[log p] - KL / n.  Its KL weight is n/m times larger; for n <= 8192 (probe = all points) the two coincide.
2. The probe predictive mean is in standardized response units (y = (log1p depth - ym) / ys); the documented tolerance
   (5e-3, "log1p units") is therefore applied to RMS_std, i.e. to RMS_log1p / ys.  The equivalent log1p tolerance is
   5e-3 * ys.

Per checkpoint this writes n, m, n/m, ys, the equivalent log1p tolerance, the last-window statistics of both stopping
statistics (also converted to log1p units) and whether any reinterpretation would have changed a stopping decision.

Step: python -m src.jdl_temporal_stopping_audit
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TR = ROOT / "outputs" / "joint_depth_label_development" / "temporal_repair"
CKPT = ROOT / "outputs" / "week20_active_temporal_development" / "_cache" / "track2" / "checkpoints"
PROBE, ELBO_TOL, MEAN_TOL, CONSEC, MIN_IT = 8192, 5e-4, 5e-3, 3, 1000


def would_stop(trace, elbo_tol, mean_tol, scale=1.0):
    """First iteration at which the frozen rule (3 consecutive checks, >= 1000 iterations) would have stopped if the
    mean-change statistic were measured as rms * scale; None if never."""
    stable = 0
    for row in trace:
        ok = row["rel_change"] <= elbo_tol and row["probe_mean_rms_change"] * scale <= mean_tol
        stable = stable + 1 if ok else 0
        if row["iteration"] >= MIN_IT and stable >= CONSEC:
            return row["iteration"]
    return None


def main():
    rows = [json.loads(l) for l in (TR / "svgp_ngd_fits.jsonl").read_text().splitlines() if l.strip()]
    out = []
    for r in rows:
        d = np.load(CKPT / f"{r['checkpoint']}.npz", allow_pickle=False)
        y0 = d["pts_y"]; n = int(len(y0)); ys = float(y0.std()); m = min(PROBE, n)
        tr = r["trace"]; last = tr[-12:]
        rel = np.array([t["rel_change"] for t in last]); rms = np.array([t["probe_mean_rms_change"] for t in last])
        out.append({"checkpoint": r["checkpoint"], "inducing_points": r["inducing_points"], "status_recorded": r["status"], "iterations": r["iterations"],
                    "n_training_points": n, "n_points_recorded": r.get("n_points"), "probe_points_m": m, "KL_weight_ratio_n_over_m": n / m,
                    "probe_equals_training_objective": n <= PROBE, "ys_log1p_units": ys, "equivalent_log1p_mean_tolerance": MEAN_TOL * ys,
                    "last12_rel_elbo_change_median": float(np.median(rel)), "last12_rel_elbo_change_min": float(rel.min()),
                    "last12_mean_rms_change_std_units_median": float(np.median(rms)), "last12_mean_rms_change_log1p_units_median": float(np.median(rms) * ys),
                    "checks_meeting_elbo_tol": int(sum(t["rel_change"] <= ELBO_TOL for t in tr)), "checks_meeting_mean_tol_std_units": int(sum(t["probe_mean_rms_change"] <= MEAN_TOL for t in tr)),
                    "checks_meeting_mean_tol_if_log1p_units": int(sum(t["probe_mean_rms_change"] * ys <= MEAN_TOL for t in tr)), "n_checks": len(tr),
                    "would_stop_as_implemented": would_stop(tr, ELBO_TOL, MEAN_TOL), "would_stop_if_mean_tol_in_log1p_units": would_stop(tr, ELBO_TOL, MEAN_TOL, ys),
                    "final_probe_elbo_per_point": r["final_probe_elbo_per_point"], "torch_threads": r.get("torch_threads", 3)})
    df = pd.DataFrame(out).sort_values(["inducing_points", "checkpoint"])
    df.to_csv(TR / "stopping_audit_per_fit.csv", index=False, lineterminator="\n")
    summ = {"fits": len(df), "recorded_converged": int((df.status_recorded == "converged").sum()),
            "fits_with_probe_equal_to_training_objective": int(df.probe_equals_training_objective.sum()),
            "KL_weight_ratio_range": [float(df.KL_weight_ratio_n_over_m.min()), float(df.KL_weight_ratio_n_over_m.max())],
            "ys_range": [float(df.ys_log1p_units.min()), float(df.ys_log1p_units.max())],
            "equivalent_log1p_tolerance_range": [float(df.equivalent_log1p_mean_tolerance.min()), float(df.equivalent_log1p_mean_tolerance.max())],
            "decisions_changed_by_log1p_reinterpretation": int((df.would_stop_as_implemented.astype(str) != df.would_stop_if_mean_tol_in_log1p_units.astype(str)).sum()),
            "fits_that_would_have_stopped_as_implemented": int(df.would_stop_as_implemented.notna().sum()),
            "fits_that_would_have_stopped_with_log1p_tolerance": int(df.would_stop_if_mean_tol_in_log1p_units.notna().sum())}
    (TR / "stopping_audit_summary.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(df.round(5).to_string(index=False))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
