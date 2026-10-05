"""Week 18 Phase 5 round analysis — implements the locked decision rule of FREEZE_ROUND_<k>.md.

Usage: python -m src.week18_round_analysis <k>
Contrasts CAND − REF (repeat bootstrap, 4,000 resamples, seed 0); real: pooled-per-repeat BA AULC; twins: NSD_0.1
AULC; QTT to REF's round-k mean at B80 with censored runs set to B_max + one grid step; reduction
1 − mean QTT(CAND)/mean QTT(REF) with the same bootstrap over repeats.  Writes round_<k>/decision.json and tables.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.week18_metrics import aulc, contrast, real_curves

ROOT = Path(__file__).resolve().parents[1]
W18 = ROOT / "outputs/week18_independent_research"


def qtt_reduction(cur, key, cand, ref, at=80, n=4000, seed=0):
    out = []
    for task, g in cur.groupby("task"):
        grid = np.sort(g.budget.unique()); bb = grid[np.argmin(np.abs(grid - at))]; step = grid[1] - grid[0]
        target = g[(g.arm == ref) & (g.budget == bb)][key].mean()
        q = {}
        for (rep, arm), h in g[g.arm.isin([cand, ref])].groupby(["repeat", "arm"]):
            h = h.sort_values("budget"); hit = h[h[key] >= target - 1e-12]
            q[(rep, arm)] = float(hit.budget.iloc[0]) if len(hit) else float(grid[-1] + step)
        reps = sorted({r for r, _ in q})
        a = np.array([q[(r, cand)] for r in reps]); b = np.array([q[(r, ref)] for r in reps])
        rng = np.random.default_rng(seed); idx = rng.integers(len(reps), size=(n, len(reps)))
        red = 1 - a[idx].mean(1) / b[idx].mean(1)
        out.append({"task": task, "target_budget": int(bb), "target": float(target), "qtt_cand_mean": float(a.mean()), "qtt_ref_mean": float(b.mean()),
                    "reduction": float(1 - a.mean() / b.mean()), "lo": float(np.quantile(red, .025)), "hi": float(np.quantile(red, .975)),
                    "censored_cand": int((a > grid[-1]).sum()), "censored_ref": int((b > grid[-1]).sum()), "repeats": len(reps)})
    return pd.DataFrame(out)


def load(k, which):
    f = W18 / f"round_{k}/results_{which}.csv.gz"
    d = pd.read_csv(f) if f.exists() else pd.DataFrame([r for p in sorted((W18 / f"round_{k}/cache_{which}").glob("*.json")) for r in json.loads(p.read_text())])
    if "degenerate" in d:
        d = d[d.degenerate != True]
    d = d.dropna(subset=["arm_name"]).copy()
    d["model"], d["hyper"], d["rule"] = d.arm_name, "r", "r"            # arm identity = frozen arm name
    return d


def main(k):
    spec = json.loads((W18 / f"round_{k}/freeze_spec.json").read_text())
    cand = [a["name"] for a in spec["arms"] if a["name"] != "REF"]
    out = {"round": k, "candidates": cand}
    import src.week18_tasks as T
    real = load(k, "real")
    y_of = {t["task"]: t["y"] for t in T.all_real(spec["real_block"])}
    rc = real_curves(real, y_of); rc["arm"] = rc.arm.str.split("|").str[0]
    ra = aulc(rc, "BA").merge(aulc(rc, "q20"), on=["task", "repeat", "arm"])
    tw = load(k, "twins"); tw["arm"] = tw.arm_name
    tc = tw.groupby(["task", "repeat", "arm", "budget"], as_index=False)[["NSD_0.1", "dense_BA"]].mean()
    ta = aulc(tc, "NSD_0.1")
    rows = []
    for c in cand:
        cr = pd.concat([contrast(ra, "BA_AULC", c, "REF"), contrast(ra, "q20_AULC", c, "REF"), contrast(ta, "NSD_0.1_AULC", c, "REF")])
        q = qtt_reduction(rc, "BA", c, "REF"); qt = qtt_reduction(tc, "NSD_0.1", c, "REF")
        rows.append(cr)
        r3 = cr[(cr.task == "R3_OLD") & (cr.metric == "BA_AULC")].iloc[0]
        td = cr[(cr.task == "S1_T_DEPTH_OLD_324") & (cr.metric == "NSD_0.1_AULC")].iloc[0]
        q3 = q[q.task == "R3_OLD"].iloc[0]
        S_a = bool(r3["mean"] >= .02 and r3["lo"] > 0)
        S_b = bool(td["mean"] >= .015 and td["lo"] > 0)
        S_c = bool(q3["reduction"] >= .15 and q3["lo"] > 0)
        scope = cr[cr.metric.isin(["BA_AULC", "NSD_0.1_AULC"])]
        B = bool((scope["mean"] >= -.01).all())
        out[c] = {"S_a_real_R3_OLD": S_a, "S_b_twin_T_DEPTH": S_b, "S_c_qtt_R3_OLD": S_c, "noninferior_all_in_scope": B,
                  "pass_round": bool((S_a or S_b or S_c) and B),
                  "R3_OLD_BA": r3[["mean", "lo", "hi"]].to_dict(), "T_DEPTH_NSD": td[["mean", "lo", "hi"]].to_dict(), "R3_OLD_QTT": q3.to_dict(),
                  "min_in_scope": float(scope["mean"].min())}
        pd.concat([q, qt]).to_csv(W18 / f"round_{k}/qtt_{c}.csv", index=False)
    pd.concat(rows).to_csv(W18 / f"round_{k}/contrasts.csv", index=False)
    ra.to_csv(W18 / f"round_{k}/aulc_real.csv", index=False); ta.to_csv(W18 / f"round_{k}/aulc_twins.csv", index=False)
    fp = pd.concat([real.fp, tw.fp]).astype(float)
    out["convergence"] = {"fits": int(len(fp)), "fp_gt_1e-6": int((fp > 1e-6).sum()), "fp_max": float(fp.max())}
    (W18 / f"round_{k}/decision.json").write_text(json.dumps(out, indent=1, default=float))
    return out



def stress_depth(k):
    """Phase 6: E1 vs REF on the depth stress worlds of round k (NSD_0.1 AULC; rule: no world below −0.03)."""
    d = load(k, "stress_depth"); d["arm"] = d.arm_name
    c = d.groupby(["task", "repeat", "arm", "budget"], as_index=False)[["NSD_0.1", "dense_BA"]].mean()
    a = aulc(c, "NSD_0.1")
    spec = json.loads((W18 / f"round_{k}/freeze_spec.json").read_text())
    res = {}
    for cand in [x["name"] for x in spec["arms"] if x["name"] != "REF"]:
        con = contrast(a, "NSD_0.1_AULC", cand, "REF"); con.to_csv(W18 / f"round_{k}/stress_depth_contrasts_{cand}.csv", index=False)
        res[cand] = {"worst_world": con.loc[con["mean"].idxmin(), "task"], "worst_mean": float(con["mean"].min()),
                     "pass_no_cell_below_-0.03": bool((con["mean"] >= -.03).all()), "table": con.round(4).to_dict("records")}
    (W18 / f"round_{k}/stress_depth_decision.json").write_text(json.dumps(res, indent=1, default=float))
    return res


def main_round2(k=2):
    """Round 2 (FREEZE_ROUND_2.md): E1 on full-depth real tasks, block C2. Q2a POOLED improvement, Q2b NEW
    non-inferiority, Q2c OLD replication."""
    import src.week18_tasks as T
    spec = json.loads((W18 / f"round_{k}/freeze_spec.json").read_text())
    real = load(k, "real")
    y_of = {t["task"]: t["y"] for t in T.all_real(spec["real_block"])}
    rc = real_curves(real, y_of); rc["arm"] = rc.arm.str.split("|").str[0]
    ra = aulc(rc, "BA").merge(aulc(rc, "q20"), on=["task", "repeat", "arm"])
    con = pd.concat([contrast(ra, "BA_AULC", "E1", "REF"), contrast(ra, "q20_AULC", "E1", "REF")])
    q = qtt_reduction(rc, "BA", "E1", "REF")
    get = lambda task: con[(con.task == task) & (con.metric == "BA_AULC")].iloc[0]
    r1, r3n, r2, r3o = get("R1_POOLED"), get("R3_NEW"), get("R2_TRANSFER"), get("R3_OLD")
    q1 = q[q.task == "R1_POOLED"].iloc[0]
    out = {"round": k,
           "Q2a_pooled_improvement": bool((r1["mean"] >= .02 and r1["lo"] > 0) or (q1["reduction"] >= .15 and q1["lo"] > 0)),
           "Q2b_new_noninferior": bool(r3n["mean"] >= -.01 and r2["mean"] >= -.01),
           "Q2c_old_replication": bool(r3o["mean"] >= .02 and r3o["lo"] > 0),
           "R1_POOLED": r1[["mean", "lo", "hi"]].to_dict(), "R1_QTT": q1.to_dict(), "R3_NEW": r3n[["mean", "lo", "hi"]].to_dict(),
           "R2_TRANSFER": r2[["mean", "lo", "hi"]].to_dict(), "R3_OLD": r3o[["mean", "lo", "hi"]].to_dict(),
           "R2rev": get("R2rev_TRANSFER")[["mean", "lo", "hi"]].to_dict()}
    fp = real.fp.astype(float); out["convergence"] = {"fits": int(len(fp)), "fp_gt_1e-6": int((fp > 1e-6).sum()), "fp_max": float(fp.max())}
    con.to_csv(W18 / f"round_{k}/contrasts.csv", index=False); q.to_csv(W18 / f"round_{k}/qtt_E1.csv", index=False)
    ra.to_csv(W18 / f"round_{k}/aulc_real.csv", index=False)
    (W18 / f"round_{k}/decision.json").write_text(json.dumps(out, indent=1, default=float))
    return out


if __name__ == "__main__":
    k = int(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 else ""
    res = stress_depth(k) if mode == "stress_depth" else (main_round2(k) if mode == "round2" else main(k))
    print(json.dumps(res, indent=1, default=float))
