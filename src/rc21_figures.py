"""RC21 static figures (presentation only, not frozen): Stage 1 matched-path learning curves (PHR and its decomposition vs the
RC20 candidate and generic inputs) and the sequential stage (BA, both recalls, log loss, BA-target confirmation spend).
    python -m src.rc21_figures      -> opus_rc21/figures/*.png
"""
from __future__ import annotations

import pandas as pd

import src.rc18_common as RC

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc21"
FIG = OUT / "figures"
COL = {"SHQ_ATS_H": "#009E73", "SHQ_ATS_X": "#E69F00", "PHR": "#C0392B", "PHR_NR": "#CC79A7", "PHR_FX": "#999999", "PHR_FXMAP": "#555555",
       "ATSAPPROX": "#7F3C8D", "E1RAW": "#0072B2", "E1CAL": "#56B4E9", "G3": "#333333",
       "NEW_MARGIN": "#C0392B", "H_MARGIN": "#009E73", "X_MARGIN": "#E69F00", "ATSAPPROX_MARGIN": "#7F3C8D", "E1RAW+straddle": "#0072B2",
       "E1CAL+straddle": "#56B4E9", "G3_MARGIN": "#333333"}


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9.5, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e8e8e8", "lines.linewidth": 1.8})
    return plt


def stage1(plt):
    p = OUT / "stage1" / "stage1_metrics.csv"
    if not p.exists():
        return
    B = pd.read_csv(p); B["cons"] = B.arm.str.split("@").str[0]
    G = B.groupby(["cons", "repeat", "budget"])[["log_loss", "BA", "sensitivity", "specificity"]].mean().reset_index()
    fig, axes = plt.subplots(1, 4, figsize=(19, 4.4))
    cons = ["SHQ_ATS_H", "SHQ_ATS_X", "PHR", "PHR_NR", "PHR_FX", "ATSAPPROX", "E1RAW"]
    for ax, (met, title) in zip(axes, (("log_loss", "held-out log loss"), ("BA", "balanced accuracy"), ("sensitivity", "Keyhole recall"), ("specificity", "conduction recall"))):
        for c in cons:
            g = G[G.cons == c]
            if g.empty:
                continue
            m = g.groupby("budget")[met].mean(); ax.plot(m.index, m.values, color=COL.get(c, "k"), label=c, ls="--" if c in ("ATSAPPROX", "E1RAW", "PHR_FX") else "-")
        ax.set_title(title); ax.set_xlabel("total paid simulations (startup included)")
        if met == "log_loss":
            ax.set_ylim(0.08, 0.6)
    axes[0].legend(frameon=False, fontsize=7.5)
    fig.suptitle("RC21 Stage 1: every construction on the SAME paid prefixes of the 200 RC19B paths (mean over 5 path types and 8 repeats; DEV)", x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(); FIG.mkdir(parents=True, exist_ok=True); fig.savefig(FIG / "fig_rc21_stage1.png", dpi=160); plt.close(fig)


def final(plt):
    p = OUT / "final_report" / "final_metrics.csv"
    if not p.exists():
        print("final metrics missing; skip"); return
    B = pd.read_csv(p); E = pd.read_csv(OUT / "final_report" / "final_endpoints.csv")
    fig, axes = plt.subplots(1, 5, figsize=(23, 4.4))
    arms = ["NEW_MARGIN", "H_MARGIN", "X_MARGIN", "ATSAPPROX_MARGIN", "E1RAW+straddle", "E1CAL+straddle", "G3_MARGIN"]
    for ax, (met, title) in zip(axes[:4], (("BA", "balanced accuracy"), ("sensitivity", "Keyhole recall"), ("specificity", "conduction recall"), ("log_loss", "held-out log loss"))):
        for a in arms:
            g = B[B.arm == a]
            if g.empty:
                continue
            m = g.groupby("budget")[met].mean(); ax.plot(m.index, m.values, color=COL.get(a, "k"), label=a, ls="--" if a.endswith("straddle") else "-")
        ax.set_title(title); ax.set_xlabel("total paid simulations")
        if met == "log_loss":
            ax.set_ylim(0.08, 0.6)
        if met == "BA":
            ax.set_ylim(0.78, 0.97)
    axes[0].legend(frameon=False, fontsize=7.2)
    ax = axes[4]; e = E[E.target == "BA >= 0.93"]; data = []; labels = []
    for a in arms:
        s = e[e.arm == a]
        if s.empty:
            continue
        data.append(s.spend.where(~s.censored, 64).to_numpy(float)); labels.append(a.replace("+straddle", "+str").replace("_MARGIN", ""))
    try:
        ax.boxplot(data, tick_labels=labels, vert=True, widths=0.6)
    except TypeError:
        ax.boxplot(data, labels=labels, vert=True, widths=0.6)
    ax.set_ylabel("paid simulations to confirm BA ≥ 0.93 (censored = 64)"); ax.tick_params(axis="x", rotation=45); ax.set_title("confirmation spend (b + 4)")
    fig.suptitle("RC21 sequential stage, fresh DEV repeats 27–34 (each arm on its own adaptive path; mean of 8 repeats)", x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(); FIG.mkdir(parents=True, exist_ok=True); fig.savefig(FIG / "fig_rc21_final.png", dpi=160); plt.close(fig)


def main():
    plt = _plt(); stage1(plt); final(plt); print("figures in", FIG)


if __name__ == "__main__":
    main()
