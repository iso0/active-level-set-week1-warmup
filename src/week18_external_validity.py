"""Week 18 Phase 2 — do synthetic / semi-synthetic rankings of the baselines predict real rankings?

Arms compared (the five available everywhere): G3+margin, G3+random, G3+coverage/Candidate B, LT+margin, M3+margin.
Families: Week 17 held-out cells (NSD AULC, `outputs/week17_model_and_acquisition/heldout`), Week 18 twins
(NSD AULC per twin truth × distribution), Week 18 real DEV tasks (BA AULC).  Agreement: Kendall τ between the
arm orderings of each pair of families; summary: mean τ of each synthetic family with the real tasks.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from src.week18_metrics import ranking_agreement

ROOT = Path(__file__).resolve().parents[1]
W18 = ROOT / "outputs/week18_independent_research"
ARMS = ["G3|margin", "G3|random", "G3|coverage", "LT|margin", "M3|margin"]


def canon(arm):
    m, h, r = arm.split("|")
    r = {"candB": "coverage"}.get(r, r)
    return f"{m}|{r}" if h.startswith("mlii") else None


def main():
    rows = []
    w17 = pd.read_csv(ROOT / "outputs/week17_model_and_acquisition/heldout/heldout_results.csv.gz", usecols=["kind", "cell", "model", "rule", "NSD_0.1_AULC"])
    w17 = w17[w17.kind == "aulc"]
    for cell, g in w17.groupby("cell"):
        lv = g.assign(arm=g.model + "|" + g.rule).groupby("arm")["NSD_0.1_AULC"].mean()
        rows.append({"family": f"W17:{cell}", "kind": "W17", **lv.to_dict()})
    real = pd.read_csv(W18 / "phase2/real_aulc.csv")
    real["carm"] = real.arm.map(canon)
    for task, g in real.dropna(subset=["carm"]).groupby("task"):
        rows.append({"family": f"REAL:{task}", "kind": "REAL", **g.groupby("carm").BA_AULC.mean().to_dict()})
    tw = W18 / "phase2/twin_aulc.csv"
    if tw.exists():
        t = pd.read_csv(tw); t["carm"] = t.arm.map(canon)
        for task, g in t.dropna(subset=["carm"]).groupby("task"):
            rows.append({"family": f"TWIN:{task}", "kind": "TWIN", **g.groupby("carm")["NSD_0.1_AULC"].mean().to_dict()})
    L = pd.DataFrame(rows).set_index("family")
    L.to_csv(W18 / "phase2/external_validity_levels.csv")
    fams = list(L.index)
    agr = ranking_agreement(L, fams, [a for a in ARMS if a in L.columns])
    agr.to_csv(W18 / "phase2/external_validity_pairs.csv", index=False)
    kind = L["kind"].to_dict()
    agr["ka"] = agr.a.map(kind); agr["kb"] = agr.b.map(kind)
    real_pairs = agr[(agr.kb == "REAL") | (agr.ka == "REAL")].copy()
    real_pairs["synthetic"] = np.where(real_pairs.ka == "REAL", real_pairs.b, real_pairs.a)
    real_pairs["skind"] = real_pairs.synthetic.map(kind)
    summ = real_pairs[real_pairs.skind != "REAL"].groupby("skind").kendall.agg(["mean", "median", "size"])
    within_real = agr[(agr.ka == "REAL") & (agr.kb == "REAL")].kendall.agg(["mean", "median", "size"])
    summ.loc["REAL_vs_REAL"] = within_real
    summ.to_csv(W18 / "phase2/external_validity_summary.csv")
    return L, agr, summ


if __name__ == "__main__":
    L, agr, summ = main()
    pd.set_option("display.width", 200)
    print(L.drop(columns="kind").round(3).to_string()); print(summ.round(3).to_string())
