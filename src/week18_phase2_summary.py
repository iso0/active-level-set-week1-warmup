"""Week 18 Phase 2 summary: contrasts vs G3 + margin (repeat bootstrap) and queries-to-target for the baselines.

Reference arm per task: G3 + margin with the task's ML-II schedule (mlii, or mlii_k8 on R2/R2rev).
QTT targets: the reference arm's DEV mean at B40 and B80 (BA for real tasks, NSD_0.1 for twins); QTT ratio =
arm's median QTT / reference median QTT (censored runs count as +inf).
"""
from pathlib import Path

import numpy as np
import pandas as pd

from src.week18_metrics import contrast, qtt

ROOT = Path(__file__).resolve().parents[1]
P2 = ROOT / "outputs/week18_independent_research/phase2"


def ref_arm(arms):
    return next(a for a in ("G3|mlii|margin", "G3|mlii_k8|margin") if a in set(arms))


def summarize(curves, au, key):
    cons, qs = [], []
    for task, g in au.groupby("task"):
        ref = ref_arm(g.arm)
        for arm in sorted(set(g.arm) - {ref}):
            cons.append(contrast(g, f"{key}_AULC", arm, ref))
        c = curves[curves.task == task]
        q = qtt(c, key, ref)
        q["ref"] = ref
        qs.append(q)
    con = pd.concat(cons, ignore_index=True)
    q = pd.concat(qs, ignore_index=True)
    med = q.groupby(["task", "target_at", "arm"]).qtt.median().rename("qtt_median").reset_index()
    refm = med.merge(q[["task", "ref"]].drop_duplicates(), on="task")
    refm = refm[refm.arm == refm.ref][["task", "target_at", "qtt_median"]].rename(columns={"qtt_median": "ref_qtt"})
    med = med.merge(refm, on=["task", "target_at"])
    med["ratio"] = med.qtt_median / med.ref_qtt
    med["censored_frac"] = q.groupby(["task", "target_at", "arm"]).qtt.apply(lambda s: float(np.isinf(s).mean())).to_numpy()
    return con, med


def main():
    rc = pd.read_csv(P2 / "real_curves.csv")
    ra = pd.read_csv(P2 / "real_aulc.csv")
    con_r, q_r = summarize(rc, ra, "BA")
    tw = pd.read_csv(P2 / "baselines_twins.csv.gz", usecols=["task", "repeat", "model", "hyper", "rule", "budget", "NSD_0.1", "degenerate"])
    tw = tw[tw.degenerate != True].dropna(subset=["model"])
    tw["arm"] = tw.model + "|" + tw.hyper + "|" + tw.rule
    tc = tw.groupby(["task", "repeat", "arm", "budget"], as_index=False)["NSD_0.1"].mean()
    ta = pd.read_csv(P2 / "twin_aulc.csv")
    con_t, q_t = summarize(tc, ta, "NSD_0.1")
    con_r.to_csv(P2 / "contrasts_real.csv", index=False); q_r.to_csv(P2 / "qtt_real.csv", index=False)
    con_t.to_csv(P2 / "contrasts_twins.csv", index=False); q_t.to_csv(P2 / "qtt_twins.csv", index=False)
    return con_r, q_r, con_t, q_t


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    con_r, q_r, con_t, q_t = main()
    print(con_r.round(3).to_string()); print(q_r[q_r.target_at > 60].round(2).to_string())
    print(con_t.round(3).to_string())
