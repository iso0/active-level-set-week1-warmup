"""RC22 figures (presentation only, not frozen).
    python -m src.rc22_figures      -> opus_rc22/figures/*.png
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import src.rc18_common as RC

OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc22"
FIG = OUT / "figures"
COL = {"PHR_NRMAP": "#C0392B", "SHQ_ATS_H": "#009E73", "HA_LR": "#E69F00", "HONLY_LR": "#7F7F7F", "SHQ_ATS_H_RECAL": "#56B4E9",
       "REF": "#C0392B", "H": "#009E73", "E1RAW+straddle": "#0072B2", "E1CAL+straddle": "#56B4E9",
       "A1_MARGIN": "#C0392B", "A2_MARGIN_COV": "#E69F00", "A3_SEL_COV": "#6A3D9A", "A4_MAXIMIN": "#7F7F7F", "A5_SIMPLE": "#009E73"}


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9.5, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e8e8e8", "lines.linewidth": 1.8})
    return plt


def _curves(ax, B, arms, met, key="arm", ls=None):
    for a in arms:
        g = B[B[key] == a]
        if g.empty:
            continue
        m = g.groupby("budget")[met].mean(); ax.plot(m.index, m.values, color=COL.get(a.split("|")[0], "k"), label=a.split("|")[0], ls=(ls or {}).get(a, "-"), marker="o" if len(m) < 12 else None, ms=3)


def ingr(plt):
    p = OUT / "ingr" / "ingr_pooled_metrics.csv"
    if not p.exists():
        return
    B = pd.read_csv(p); G = B.groupby(["cons", "repeat", "budget"])[["BA", "log_loss", "sensitivity", "specificity"]].mean().reset_index().rename(columns={"cons": "arm"})
    fig, axes = plt.subplots(1, 4, figsize=(19, 4.2)); arms = ["PHR_NRMAP", "SHQ_ATS_H", "SHQ_ATS_H_RECAL", "HA_LR", "HONLY_LR"]
    for ax, (met, t) in zip(axes, (("BA", "balanced accuracy"), ("log_loss", "held-out log loss"), ("sensitivity", "Keyhole recall"), ("specificity", "conduction recall"))):
        _curves(ax, G, arms, met); ax.set_title(t); ax.set_xlabel("paid simulations (identical saved prefixes)")
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("RC22 part 2: ingredients on identical paid prefixes (RC21B paths, repeats 35–42; mean over 2 path types and 8 repeats; DEV)", x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(); FIG.mkdir(parents=True, exist_ok=True); fig.savefig(FIG / "fig_rc22_ingredients.png", dpi=150); plt.close(fig)
    s = OUT / "ingr" / "ingr_scale_ranking.csv"
    if s.exists():
        S = pd.read_csv(s); fig, axes = plt.subplots(1, 4, figsize=(19, 4.0))
        for ax, (met, t) in zip(axes, (("slope", "slope of logit(other) on logit(SHQ_ATS_H)"), ("R2", "R² of that fit"), ("sign_disagree", "share of candidates with a different decision"),
                                        ("top1_same", "same margin choice as SHQ_ATS_H"))):
            for pr in sorted(S.pair.unique()):
                g = S[S.pair == pr].groupby("budget")[met].median() if met != "top1_same" else S[S.pair == pr].groupby("budget")[met].mean()
                ax.plot(g.index, g.values, marker="o", ms=3, color=COL.get(pr.split(" vs ")[0], "k"), label=pr.split(" vs ")[0])
            ax.set_title(t); ax.set_xlabel("paid simulations")
        axes[0].legend(frameon=False, fontsize=8)
        fig.suptitle("RC22: how far are the constructions from a common rescaling of SHQ_ATS_H's logit? (candidates of every matched state)", x=0.01, ha="left", fontsize=10.5)
        fig.tight_layout(); fig.savefig(FIG / "fig_rc22_scale.png", dpi=150); plt.close(fig)


def robust(plt):
    p, q = OUT / "start" / "start_pooled_metrics.csv", OUT / "block" / "block_pooled_metrics.csv"
    if not p.exists():
        return
    B = pd.read_csv(p); fig, axes = plt.subplots(2, 4, figsize=(20, 8)); arms = ["REF", "H", "E1RAW+straddle"]
    for j, st in enumerate(("STD", "RAND8", "LOCAL8")):
        for i, met in enumerate(("BA", "log_loss")):
            ax = axes[i, j]; _curves(ax, B, [f"{a}|{st}" for a in arms], met, ls={f"E1RAW+straddle|{st}": "--"}); ax.set_title(f"startup {st}: {met}"); ax.set_xlabel("paid simulations")
            if met == "log_loss":
                ax.set_ylim(0.08, 0.6)
            else:
                ax.set_ylim(0.70, 0.97)
    if q.exists():
        Q = pd.read_csv(q)
        for i, met in enumerate(("BA", "log_loss")):
            ax = axes[i, 3]; _curves(ax, Q, [f"{a}|STD" for a in arms], met, ls={"E1RAW+straddle|STD": "--"}); ax.set_title(f"geometry blocks (pooled over 5 blocks): {met}"); ax.set_xlabel("paid simulations")
    axes[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle("RC22 part 1: robustness of REF (PHR_NRMAP + margin) vs H (SHQ_ATS_H + margin) and E1 + straddle (fold-pooled curves, mean of 8 repeats / seeds; DEV)", x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(); FIG.mkdir(parents=True, exist_ok=True); fig.savefig(FIG / "fig_rc22_robustness.png", dpi=150); plt.close(fig)


def acq(plt):
    p = OUT / "acq" / "acq_pooled_metrics.csv"
    if not p.exists():
        return
    B = pd.read_csv(p); E = pd.read_csv(OUT / "acq" / "acq_endpoints.csv"); arms = [a for a in COL if a.startswith("A") and a in set(B.arm)]
    fig, axes = plt.subplots(1, 5, figsize=(23, 4.3))
    for ax, (met, t) in zip(axes[:4], (("BA", "balanced accuracy"), ("sensitivity", "Keyhole recall"), ("specificity", "conduction recall"), ("log_loss", "held-out log loss"))):
        _curves(ax, B, arms, met); ax.set_title(t); ax.set_xlabel("paid simulations")
        if met == "BA":
            ax.set_ylim(0.78, 0.97)
        if met == "log_loss":
            ax.set_ylim(0.08, 0.6)
    axes[0].legend(frameon=False, fontsize=8)
    e = E[E.target == "BA >= 0.93"]; data = [e[e.arm == a].spend.where(~e[e.arm == a].censored, 64).to_numpy(float) for a in arms]
    try:
        axes[4].boxplot(data, tick_labels=arms, widths=0.6)
    except TypeError:
        axes[4].boxplot(data, labels=arms, widths=0.6)
    axes[4].tick_params(axis="x", rotation=35); axes[4].set_title("sims to confirm BA ≥ 0.93 (censored = 64)", fontsize=9)
    fig.suptitle("RC22 part 3: acquisition with the predictive model fixed (PHR_NRMAP), fresh DEV repeats 43–50 (fold-pooled, mean of 8 repeats)", x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(); FIG.mkdir(parents=True, exist_ok=True); fig.savefig(FIG / "fig_rc22_acquisition.png", dpi=150); plt.close(fig)


def main():
    plt = _plt(); ingr(plt); robust(plt); acq(plt); print("figures in", FIG)


if __name__ == "__main__":
    main()
