"""Evaluate pre-registered predictions P1-P4 on the C1 discovery benchmark."""
import json
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "outputs/week14_research_program/synthetic/discovery"
OUT = ROOT / "outputs/week14_research_program/benchmarks"
df = pd.read_parquet(D / "discovery_confirm.parquet")
key = ["family", "d", "n", "prevalence", "design", "rep"]
w = df.pivot_table(index=key, columns="strategy", values="T_both").reset_index()
info = df.drop_duplicates(key)[key + ["n_min_front", "n_max_front"]]
w = w.merge(info, on=key)
mono = w[w.family == "heldout_mono_curved"]
P1 = bool((mono.FRONT <= mono.n_min_front + mono.n_max_front).all())
cell = mono.groupby(["d", "n"])[["FRONT", "MAXI", "RAND"]].mean()
P2 = bool(((cell.FRONT < cell.MAXI) & (cell.MAXI < cell.RAND)).all())
P3a = bool((w.HEDGE_FR <= 2 * np.minimum(w.FRONT, w.RAND)).all())
fam = w.groupby("family")[["HEDGE_FR", "RAND", "MAXI", "FRONT", "SCORE", "HEDGE", "ADAPT8"]].mean()
P3b = bool((fam.HEDGE_FR <= 1.5 * fam.RAND).all())
nonmono = fam.drop(index="heldout_mono_curved")
P4 = bool((nonmono.MAXI > nonmono.RAND).any())
summary = {"P1_front_within_front_sizes": P1, "P2_front_lt_maxi_lt_rand_every_dn_cell": P2,
           "P2_cells": cell.round(3).reset_index().to_dict("records"),
           "P3a_hedge_pathwise_bound": P3a, "P3b_hedge_le_1.5x_rand_every_family": P3b,
           "P4_maxi_worse_than_rand_somewhere": P4, "family_means": fam.round(3).to_dict("index"),
           "family_q90": w.groupby("family")[["HEDGE_FR", "RAND", "MAXI", "FRONT"]].quantile(.9).to_dict("index"),
           "family_max": w.groupby("family")[["HEDGE_FR", "RAND", "MAXI", "FRONT"]].max().to_dict("index"),
           "n_pools": int(len(w))}
# where does FRONT lose to RAND / MAXI (mechanism table)
summary["front_vs_maxi_by_family_d"] = w.groupby(["family", "d"])[["FRONT", "MAXI", "RAND", "HEDGE_FR"]].mean().round(2).reset_index().to_dict("records")
(OUT / "C1_discovery_verdict.json").write_text(json.dumps(summary, indent=2, default=float))
print(json.dumps({k: v for k, v in summary.items() if k.startswith("P")}, indent=1, default=float))
print(pd.DataFrame(summary["front_vs_maxi_by_family_d"]).to_string())
