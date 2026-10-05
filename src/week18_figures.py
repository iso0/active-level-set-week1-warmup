"""Week 18 figures (static PNG for the thesis). Usage: python -m src.week18_figures [name ...]"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
W18 = ROOT / "outputs/week18_independent_research"
FIG = W18 / "figures"
# validated categorical order (dataviz reference palette, light mode, adjacent pairs)
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": "#e6e6e3", "grid.linewidth": .6, "lines.linewidth": 1.6})


def real_curves():
    cur = pd.read_csv(W18 / "phase2/real_curves.csv")
    cur["key"] = cur.arm.str.replace("|mlii_k8|", "|", regex=False).str.replace("|mlii|", "|", regex=False)
    arms = [("G3|margin", "G3 + margin"), ("G3|random", "G3 + random"), ("LT|margin", "LT + margin"), ("M3|margin", "M3 + margin"),
            ("GPR_depth|straddle", "depth GPR + straddle (E1)")]
    tasks = ["R1_POOLED", "R2_TRANSFER", "R2rev_TRANSFER", "R3_NEW", "R3_OLD"]
    fig, axs = plt.subplots(1, 5, figsize=(13, 2.8), sharey=False)
    for ax, task in zip(axs, tasks):
        g = cur[cur.task == task]
        for i, (k, lab) in enumerate(arms):
            h = g[g.key == k].groupby("budget").BA.mean()
            if len(h):
                ax.plot(h.index, h.values, color=C[i], label=lab)
        ax.set_title(task, fontsize=9); ax.set_xlabel("paid simulations")
    axs[0].set_ylabel("balanced accuracy (DEV, mean of 8 repeats)")
    handles, labels = axs[-1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(.5, -.06))
    fig.tight_layout(rect=(0, .06, 1, 1))
    FIG.mkdir(exist_ok=True); fig.savefig(FIG / "fig_w18_real_baseline_curves.png", dpi=200, bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    for name in sys.argv[1:] or ["real_curves"]:
        globals()[name]()
