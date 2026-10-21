"""RC24 synthetic benchmark evaluation (per family x split: one learner per world; BA-AULC over B8-B24 / B8-B60 and log loss, mean over
seeds, paired differences with SE and the count of positive seeds).
    python -m src.rc24_synth_eval s-dev | s-test
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc24_synth as S
from src.rc19_report import md

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc24"
PAIRS = (("HA_TREND_MARGIN", "HA_LEAN_MARGIN"), ("HA_TREND_MARGIN", "HONLY_MARGIN"), ("HA_LEAN_MARGIN", "HONLY_MARGIN"), ("PAC_MARGIN", "HA_LEAN_MARGIN"),
         ("PAC_MARGIN", "HA_TREND_MARGIN"))


def curves(U):
    rows = []; cache = {}
    for u in U:
        key = (u["family"], u["seed"])
        if key not in cache:
            cache[key] = S.world(u["family"], u["seed"])[0]
        y = cache[key].reindex(u["test_ids"]).y.to_numpy(int)
        for e in u["evals"]:
            p = np.clip(np.asarray(list(e["p"].values())[0], float), 1e-6, 1 - 1e-6); hat = p >= 0.5
            ba = 0.5 * (np.mean(hat[y == 1]) + np.mean(~hat[y == 0])) if (y == 1).any() and (y == 0).any() else np.nan
            rows.append({"family": u["family"], "seed": u["seed"], "split": u["split"], "arm": u["arm"], "budget": e["budget"], "BA": ba,
                         "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))})
    return pd.DataFrame(rows)


def evaluate(job):
    U = EV.load_units(OUT / job); C = curves(U); d = OUT / "synthetic"; d.mkdir(parents=True, exist_ok=True); C.to_csv(d / f"{job}_curves.csv", index=False)
    W = {"B8_B24": range(8, 25), "B8_B60": range(8, 61)}; A = []
    for w, bs in W.items():
        a = C[C.budget.isin(list(bs))].groupby(["family", "seed", "split", "arm"])[["BA", "log_loss"]].mean().reset_index(); a["window"] = w; A.append(a)
    A = pd.concat(A); A.to_csv(d / f"{job}_aulc.csv", index=False)
    S1 = A.groupby(["window", "split", "family", "arm"])[["BA", "log_loss"]].mean().reset_index()
    D = []
    for (w, sp, fa), g in A.groupby(["window", "split", "family"]):
        P = g.pivot_table(index="seed", columns="arm", values="BA")
        for a, b in PAIRS:
            if a in P and b in P:
                x = (P[a] - P[b]).dropna(); D.append({"window": w, "split": sp, "family": fa, "contrast": f"{a} − {b}", "mean": x.mean(), "se": x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else np.nan,
                                                       "pos": f"{int((x > 0).sum())}/{len(x)}"})
    D = pd.DataFrame(D); D.to_csv(d / f"{job}_contrasts.csv", index=False)
    L = [f"# RC24 synthetic benchmark — {job}", "", f"{len(U)} units; one learner per world and split; BA-AULC (mean over seeds).", ""]
    for w in W:
        for sp in ("std", "block"):
            T = S1[(S1.window == w) & (S1.split == sp)].pivot_table(index="family", columns="arm", values="BA").reset_index()
            L += [f"## {w}, split {sp}", "", md(T, 4), "", md(D[(D.window == w) & (D.split == sp)].drop(columns=["window", "split"]), 4), ""]
    (d / f"{job.upper()}.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L))


if __name__ == "__main__":
    evaluate(sys.argv[1])
