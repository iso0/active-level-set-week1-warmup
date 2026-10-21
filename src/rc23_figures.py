"""RC23 figures (presentation only).   python -m src.rc23_figures  -> opus_rc23/figures/*.png"""
from __future__ import annotations

import pandas as pd

import src.rc18_common as RC

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc23"
FIG = OUT / "figures"
COL = {"PHR_NRMAP": "#C0392B", "HA_LR": "#E69F00", "HA_LEAN": "#009E73", "HONLY_LR": "#7F7F7F"}
LAB = {"PHR_NRMAP": "RC22 reference (PHR_NRMAP)", "HA_LR": "shared-upstream h + depth (HA_LR)", "HA_LEAN": "fully lean h + depth (HA_LEAN)", "HONLY_LR": "h only (HONLY_LR)"}


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9.5, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e8e8e8", "lines.linewidth": 1.8})
    return plt


def main():
    plt = _plt(); FIG.mkdir(parents=True, exist_ok=True)
    B = pd.read_csv(OUT / "std" / "std_pooled_metrics.csv"); fig, ax = plt.subplots(1, 4, figsize=(20, 4.3))
    for a, (met, t) in zip(ax, (("BA", "balanced accuracy"), ("sensitivity", "Keyhole recall"), ("specificity", "conduction recall"), ("log_loss", "held-out log loss"))):
        for c in COL:
            g = B[B.arm == c].groupby("budget")[met].mean(); a.plot(g.index, g.values, color=COL[c], label=LAB[c])
        a.set_title(t); a.set_xlabel("paid simulations (startup included)")
        if met == "BA":
            a.set_ylim(0.80, 0.97)
        if met == "log_loss":
            a.set_ylim(0.08, 0.6)
    ax[0].legend(frameon=False, fontsize=8)
    fig.suptitle("RC23 stage 2: fresh DEV repeats 51–58, standard startup, margin in every arm (fold-pooled curves, mean of 8 repeats)", x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(); fig.savefig(FIG / "fig_rc23_std.png", dpi=150); plt.close(fig)
    fig, ax = plt.subplots(1, 4, figsize=(20, 4.3))
    for a, part, t in zip(ax, ("rob_std", "rob_rand8", "rob_local8", "block"), ("standard startup (35–42)", "random startup", "clustered startup", "geometry blocks (pooled)")):
        p = OUT / part / f"{part}_pooled_metrics.csv"
        if not p.exists():
            continue
        Q = pd.read_csv(p)
        for c in COL:
            g = Q[Q.arm == c].groupby("budget")["BA"].mean(); a.plot(g.index, g.values, color=COL[c], label=LAB[c])
        a.set_title(f"BA — {t}"); a.set_xlabel("paid simulations"); a.set_ylim(0.70, 0.97)
    ax[0].legend(frameon=False, fontsize=8)
    fig.suptitle("RC23 stage 3: robustness of the candidates (PHR_NRMAP reused from RC21B / RC22; fold-pooled, mean of 8 repeats / seeds; DEV)", x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(); fig.savefig(FIG / "fig_rc23_robustness.png", dpi=150); plt.close(fig); print("figures in", FIG)


if __name__ == "__main__":
    main()
