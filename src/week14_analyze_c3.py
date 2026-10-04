"""Evaluate pre-registered predictions P7a/P7b on the C3 metric benchmark."""
import json
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "outputs/week14_research_program/benchmarks"
sens = pd.read_csv(B / "metrics_confirm/density_sensitivity.csv")
A = pd.read_csv(B / "metrics_confirm/rank_agreement.csv")
s = sens.groupby(["d", "shape", "density"])[["gabriel_BER", "gabriel_wBER", "q20_accuracy", "full_BA", "gabriel_BEF1", "gabriel_wBEF1", "NSD"]].mean()
P7a = bool((s.gabriel_wBER < s.gabriel_BER).all())
r = A.groupby(["shape", "d", "density", "metric"]).rho_negASSD.mean().unstack()
P7b_cells = (r.gabriel_wBEF1 >= r.q20_accuracy)
skipped = int((pd.read_csv(B / "metrics_confirm/metric_confirm.csv.gz", usecols=["pred"]).pred == "SKIPPED_single_class").sum())
verdict = {"P7a_wBER_less_density_sensitive_every_cell": P7a, "P7b_wBEF1_ge_q20acc_every_cell": bool(P7b_cells.all()),
           "P7b_cells_passing": int(P7b_cells.sum()), "P7b_cells_total": int(len(P7b_cells)),
           "P7b_failing_cells": [list(map(str, k)) for k in P7b_cells[~P7b_cells].index],
           "skipped_single_class_pools": skipped,
           "density_sensitivity": s.round(3).reset_index().to_dict("records"),
           "rank_agreement_negASSD": r.round(3).reset_index().to_dict("records")}
(B / "C3_metric_verdict.json").write_text(json.dumps(verdict, indent=2))
print(json.dumps({k: v for k, v in verdict.items() if k.startswith(("P", "skipped"))}, indent=1))
