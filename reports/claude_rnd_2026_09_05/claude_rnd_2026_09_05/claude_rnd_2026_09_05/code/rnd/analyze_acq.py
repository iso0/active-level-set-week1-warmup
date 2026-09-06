"""Analyse an acquisition replay: window AULCs, paired contrasts (repeat-block bootstrap),
ranking-novelty statistics, path overlap, selected-band/KH rates."""
import sys, json, numpy as np, pandas as pd
from core import *
TAG = sys.argv[1] if len(sys.argv) > 1 else "F7"
m = pd.read_csv(f"results/acq_{TAG}_metrics.csv.gz"); s = pd.read_csv(f"results/acq_{TAG}_steps.csv.gz"); paths = json.load(open(f"results/acq_{TAG}_paths.json"))
ref = pd.read_csv("results/p13_p14_q20_curves.csv"); ref = ref[ref.model == "P1"]  # committed M3-margin
W = ((16, 32), (16, 40), (16, 48), (16, 80))
def aulc_w(g, col, a, b):
    g = g[(g.budget >= a) & (g.budget <= b)].sort_values("budget"); return np.trapezoid(g[col].values, g.budget.values) / (b - a)
rows = []
q = m[m.subset == "B1_q20"]
for (arm, model, run, rep), g in q.groupby(["arm", "model", "run_id", "repeat"]):
    rows.append({"arm": f"{model}@{arm}", "run_id": run, "repeat": rep, **{f"A{a}_{b}": aulc_w(g, "accuracy", a, b) for a, b in W}})
for (run, rep), g in ref.groupby(["run_id", "repeat"]):
    rows.append({"arm": "M3@M3_MARGIN(P1)", "run_id": run, "repeat": rep, **{f"A{a}_{b}": aulc_w(g, "correct", a, b) for a, b in W}})
A = pd.DataFrame(rows); A.to_csv(f"results/acq_{TAG}_window_aulc.csv", index=False)
runs_done = sorted(set(A[A.arm.str.startswith("T@")].run_id)); A = A[A.run_id.isin(runs_done)]
rng = np.random.default_rng(0)
def contrast(a, b):
    X = A[A.arm == a].set_index("run_id"); Y = A[A.arm == b].set_index("run_id").loc[X.index]; out = {}
    for w in [f"A{i}_{j}" for i, j in W]:
        diff = X[w] - Y[w]; blocks = pd.DataFrame({"d": diff.values, "r": X.repeat.values}).groupby("r").d.mean().values
        boots = blocks[rng.integers(0, len(blocks), (10000, len(blocks)))].mean(1); lo, hi = np.quantile(boots, [.025, .975])
        out[w] = f"{diff.mean():+.4f} [{lo:+.4f},{hi:+.4f}] ({(blocks>0).sum()}/{(blocks<0).sum()})"
    return out
print(f"runs analysed: {len(runs_done)}\n")
print("Mean window AULC by arm:"); print(A.groupby("arm")[[f"A{i}_{j}" for i, j in W]].mean().round(4).to_string()); print()
pairs = [("T@T_SUR", "T@T_MARGIN"), ("T@T_TV", "T@T_MARGIN"), ("M3@T_SUR", "M3@T_MARGIN"), ("M3@T_TV", "M3@T_MARGIN"),
         ("M3@T_TV", "M3@M3_MARGIN(P1)"), ("M3@T_SUR", "M3@M3_MARGIN(P1)"), ("M3@T_MARGIN", "M3@M3_MARGIN(P1)"), ("T@T_MARGIN", "M3@T_MARGIN"), ("T@T_MARGIN", "M3@M3_MARGIN(P1)")]
for a, b in pairs:
    if a in set(A.arm) and b in set(A.arm):
        print(f"{a} minus {b}:"); [print(f"   {k}: {v}") for k, v in contrast(a, b).items()]
print("\nRanking novelty vs T-margin (per-step means):")
print(s.groupby("arm")[["same_as_margin", "rho_vs_margin", "top5_overlap", "chosen_band", "chosen_kh", "chosen_p"]].mean().round(3).to_string())
early = s[s.budget < 40]; print("\n… early steps (B16-39):"); print(early.groupby("arm")[["same_as_margin", "rho_vs_margin", "top5_overlap", "chosen_band", "chosen_kh"]].mean().round(3).to_string())
def jac(a, b, n): a = set(a[:n]); b = set(b[:n]); return len(a & b) / len(a | b)
for arm in ("T_SUR", "T_TV"):
    if arm in paths[0]:
        print(f"path Jaccard {arm} vs T_MARGIN: B40 {np.mean([jac(p[arm], p['T_MARGIN'], 40) for p in paths]):.3f}, B80 {np.mean([jac(p[arm], p['T_MARGIN'], 80) for p in paths]):.3f}")
# committed M3-margin path overlap with T-margin
cm = pd.read_csv(REPO / "outputs/week9_phase1_14_m3_margin_acquisition/m3_margin_paths.csv.gz"); P1 = {r: g.sort_values("query_order").population_row_index.astype(int).tolist() for r, g in cm[cm.path.eq("P1")].groupby("run_id")}
print(f"path Jaccard T_MARGIN vs committed M3-margin: B40 {np.mean([jac(p['T_MARGIN'], P1[p['run_id']], 40) for p in paths]):.3f}, B80 {np.mean([jac(p['T_MARGIN'], P1[p['run_id']], 80) for p in paths]):.3f}")
# KH recall at B40 (q20) per arm
print("\nq20 KH recall at B40:"); print(q[q.budget == 40].groupby(["model", "arm"]).keyhole_recall.mean().round(3).to_string())
