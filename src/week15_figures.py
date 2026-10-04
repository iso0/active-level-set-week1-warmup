"""Week 15 figures."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
W = ROOT / "outputs/week15_boundary_acquisition"
FIG = W / "figures"
BLUE, ORANGE, AQUA, GRAY, INK, MUTED, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984", "#0b0b0b", "#52514e", "#e87ba4"
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True,
                     "grid.color": "#e6e5e0", "grid.linewidth": .6, "legend.frameon": False})


def forest():
    C = pd.read_csv(W / "heldout/cell_contrasts.csv").sort_values("ebrd-margin_NSD_0.1")
    fig, ax = plt.subplots(figsize=(7.4, 5.2))
    y = np.arange(len(C))
    ax.errorbar(C["ebrd-margin_NSD_0.1"], y, xerr=[C["ebrd-margin_NSD_0.1"] - C["ebrd-margin_NSD_0.1_lo"], C["ebrd-margin_NSD_0.1_hi"] - C["ebrd-margin_NSD_0.1"]],
                fmt="o", color=BLUE, ms=5, capsize=2, label="EBR-D − margin (95% paired bootstrap)")
    ax.scatter(C["vsur-margin_NSD_0.1"], y, marker="x", color=ORANGE, label="VSUR − margin (ablation)", zorder=3)
    ax.axvline(0, color=MUTED, lw=1); ax.axvline(-.05, color=MUTED, lw=1, ls=":")
    ax.text(-.05, len(C) - .3, "catastrophe threshold", color=MUTED, fontsize=7, ha="right")
    ax.set_yticks(y, [c.replace("|", "  ") for c in C.cell], fontsize=7)
    ax.set_xlabel("true-boundary NSD AULC difference vs margin")
    ax.set_title("Frozen held-out benchmark: EBR-D vs margin (7/16 cells positive)", fontsize=9)
    ax.legend(fontsize=7, loc="lower right")
    fig.tight_layout(); fig.savefig(FIG / "fig1_heldout_forest.png", dpi=200)


def oracle():
    t = pd.read_csv(W / "development/oracle_decomposition.csv").set_index("scenario")
    fig, ax = plt.subplots(1, 2, figsize=(9.6, 3.4))
    x = np.arange(len(t)); w = .2
    for k, (c, col, lab) in enumerate((("random", GRAY, "random"), ("margin", BLUE, "margin"), ("oracle_E", AQUA, "expectation oracle (knows f)"), ("oracle_R", ORANGE, "realized-label oracle (peeks)"))):
        ax[0].bar(x + (k - 1.5) * w, t[c], w * .9, color=col, label=lab)
    ax[0].set_xticks(x, [f"{s}-like" for s in t.index]); ax[0].set_ylim(.6, 1); ax[0].set_ylabel("NSD AULC (development generator)")
    ax[0].legend(fontsize=7); ax[0].set_title("Headroom is mostly truth-knowledge, not label peeking", fontsize=9)
    b = pd.read_csv(W / "development/bayes_frontier.csv").groupby("criterion")[["oracle_gain_of_choice", "oracle_best_gain"]].mean()
    order = ["margin", "vsur", "ebrd", "bayes_mc"]
    ax[1].bar(range(4), b.loc[order, "oracle_gain_of_choice"], color=[BLUE, ORANGE, MAGENTA, AQUA])
    ax[1].axhline(b.oracle_best_gain.mean(), color=MUTED, ls=":", lw=1); ax[1].text(3.4, b.oracle_best_gain.mean(), "oracle best", fontsize=7, color=MUTED, ha="right", va="bottom")
    ax[1].axhline(0, color=MUTED, lw=1)
    ax[1].set_xticks(range(4), ["margin", "VSUR", "EBR-D", "exact Bayes"]); ax[1].set_ylabel("true one-step NSD gain of the chosen case")
    ax[1].set_title("Well-specified GP world: what a legal rule can capture", fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / "fig2_oracle_decomposition.png", dpi=200)


def flips():
    C = pd.read_csv(W / "heldout/cell_contrasts.csv")
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    dfl = C.flip_margin - C.flip_ebrd
    cols = {"gpworld": AQUA, "curvedMono": BLUE, "branin4d": ORANGE, "rough": MAGENTA}
    for fam, g in C.groupby("family"):
        ax.scatter((g.flip_margin - g.flip_ebrd), g["ebrd-margin_NSD_0.1"], color=cols[fam], label=fam, s=30, edgecolor="white")
    ax.axhline(0, color=MUTED, lw=1); ax.axvline(0, color=MUTED, lw=1)
    ax.set_xlabel("flipped-label share among acquired cases: margin − EBR-D")
    ax.set_ylabel("EBR-D − margin NSD AULC")
    ax.set_title("Avoiding noisy labels does not by itself improve the boundary", fontsize=9)
    ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "fig3_flips_vs_gain.png", dpi=200)


def metric():
    s = pd.read_csv(W / "heldout/metric_density_sensitivity.csv")
    s = s[s.design.str.startswith("smooth")].groupby(["d", "shape"])[["q20_accuracy", "full_BA", "BEF1", "BD_unweighted", "DC_BD", "NSD"]].mean()
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    x = np.arange(len(s)); w = .14
    for k, (c, col) in enumerate((("q20_accuracy", GRAY), ("full_BA", MUTED), ("BEF1", ORANGE), ("BD_unweighted", MAGENTA), ("DC_BD", BLUE), ("NSD", AQUA))):
        ax.bar(x + (k - 2.5) * w, s[c], w * .9, color=col, label=c)
    ax.set_xticks(x, [f"{sh} d={d}" for d, sh in s.index]); ax.set_ylabel("|score(side A error) − score(side B error)|")
    ax.set_title("Held-out smooth density shifts: DC-BD fixes the r-graph but no finite metric is density-free", fontsize=9)
    ax.legend(fontsize=7, ncol=3)
    fig.tight_layout(); fig.savefig(FIG / "fig4_metric_density.png", dpi=200)


if __name__ == "__main__":
    FIG.mkdir(parents=True, exist_ok=True)
    forest(); oracle(); flips(); metric()
