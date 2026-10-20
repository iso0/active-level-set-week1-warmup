"""RC20 static figures (presentation only): Stage 1 matched-path learning curves (attribution and log-h variants) and the
sequential stage (learning curves, confirmation-spend distributions).
    python -m src.rc20_figures      -> opus_rc20/figures/*.png
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import src.rc18_common as RC

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc20"
FIG = OUT / "figures"
COL = {"E1RAW": "#0072B2", "E1CAL": "#56B4E9", "M0Q_A": "#E69F00", "SHQ_A": "#D55E00", "M0Q_ATS": "#999999", "SHQ_ATS": "#000000", "SHQ_ATS_H": "#009E73",
       "SHQ_A_H": "#8FD175", "SHQT_ATS": "#CC79A7", "ATSAPPROX": "#7F3C8D", "HONLY": "#F0C987", "G3": "#555555",
       "CAND_MARGIN": "#009E73", "CAND_ETASTRADDLE": "#8FD175", "ATSCF_MARGIN": "#000000", "ATSAPPROX_MARGIN": "#7F3C8D", "E1RAW+straddle": "#0072B2",
       "E1CAL+straddle": "#56B4E9", "G3_MARGIN": "#555555"}


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9.5, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e8e8e8", "lines.linewidth": 1.8})
    return plt


def stage1(plt):
    B = pd.read_csv(OUT / "stage1" / "stage1_metrics.csv"); B["cons"] = B.arm.str.split("@").str[0]
    G = B.groupby(["cons", "repeat", "budget"])[["log_loss", "BA"]].mean().reset_index()            # mean over the 5 path types
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    panels = [("attribution: features vs upstream", ["M0Q_A", "SHQ_A", "M0Q_ATS", "SHQ_ATS", "E1RAW", "E1CAL"], "log_loss"),
              ("log h variants (honest)", ["SHQ_ATS", "SHQ_ATS_H", "SHQ_A_H", "SHQT_ATS", "HONLY", "ATSAPPROX"], "log_loss"),
              ("balanced accuracy", ["SHQ_ATS", "SHQ_ATS_H", "SHQ_A_H", "HONLY", "E1RAW", "ATSAPPROX"], "BA")]
    for ax, (title, cons, met) in zip(axes, panels):
        for c in cons:
            g = G[G.cons == c]
            if g.empty:
                continue
            m = g.groupby("budget")[met].mean(); lo = g.groupby("budget")[met].min(); hi = g.groupby("budget")[met].max()
            ax.plot(m.index, m.values, color=COL.get(c, "k"), label=c, ls="--" if c in ("E1RAW", "E1CAL", "ATSAPPROX", "HONLY") else "-")
            ax.fill_between(m.index, lo.values, hi.values, color=COL.get(c, "k"), alpha=0.08, lw=0)
        ax.set_title(title); ax.set_xlabel("total paid simulations (startup included)")
        ax.set_ylabel("held-out log loss" if met == "log_loss" else "held-out BA")
        if met == "log_loss":
            ax.set_ylim(0.08, 0.6)
        ax.legend(frameon=False, fontsize=7.5)
    fig.suptitle("RC20 Stage 1: every construction on the SAME paid prefixes of the 200 RC19B paths (mean over 5 path types; band = range over 8 repeats; DEV)",
                 x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(); FIG.mkdir(parents=True, exist_ok=True); fig.savefig(FIG / "fig_rc20_stage1.png", dpi=160); plt.close(fig)


def final(plt):
    p = OUT / "final_report" / "final_metrics.csv"
    if not p.exists():
        print("final metrics missing; skip"); return
    B = pd.read_csv(p); E = pd.read_csv(OUT / "final_report" / "final_endpoints.csv")
    fig, axes = plt.subplots(1, 4, figsize=(19, 4.4))
    arms = ["CAND_MARGIN", "CAND_ETASTRADDLE", "ATSCF_MARGIN", "ATSAPPROX_MARGIN", "E1RAW+straddle", "E1CAL+straddle", "G3_MARGIN"]
    for ax, (met, title) in zip(axes[:3], (("log_loss", "held-out log loss"), ("BA", "balanced accuracy"), ("spec_NEW", "fast-scan corner: conduction recall"))):
        for a in arms:
            g = B[B.arm == a]
            if g.empty:
                continue
            m = g.groupby("budget")[met].mean(); ax.plot(m.index, m.values, color=COL.get(a, "k"), label=a, ls="--" if a.endswith("straddle") and not a.startswith("CAND") else "-")
        ax.set_title(title); ax.set_xlabel("total paid simulations")
        if met == "log_loss":
            ax.set_ylim(0.08, 0.6)
    axes[0].legend(frameon=False, fontsize=7.2)
    ax = axes[3]; tgt = [t for t in E.target.unique() if "log_loss" in t]
    if tgt:
        e = E[E.target == tgt[0]]; data = []; labels = []
        for a in arms:
            s = e[e.arm == a]; v = s.spend.where(~s.censored, 64).to_numpy(float); data.append(v); labels.append(a.replace("+straddle", "+str").replace("_MARGIN", ""))
        try:
            ax.boxplot(data, tick_labels=labels, vert=True, widths=0.6)
        except TypeError:
            ax.boxplot(data, labels=labels, vert=True, widths=0.6)
        ax.set_ylabel("paid simulations to confirm LL ≤ 0.20 (censored = 64)"); ax.tick_params(axis="x", rotation=45)
        ax.set_title("confirmation spend (b + 4)")
    fig.suptitle("RC20 sequential stage, fresh DEV repeats 19–26 (each arm on its own adaptive path; mean of 8 repeats)", x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(); FIG.mkdir(parents=True, exist_ok=True); fig.savefig(FIG / "fig_rc20_final.png", dpi=160); plt.close(fig)


def main():
    plt = _plt(); stage1(plt); final(plt); print("figures in", FIG)


if __name__ == "__main__":
    main()
