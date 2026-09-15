"""Week 9 Phase 1.23 — figures for the synthetic stress test (reads the analysis outputs)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import week9_phase1_23_analysis as ana
from src import week9_phase1_23_grid as grid

OUT = ana.OUT
FIG = OUT / "figures"
CLASS_COLOR = {"HELPS_MATERIAL": "#1a7f37", "HELPS_SMALL": "#7fbf7b", "EQUIVALENT": "#8c8c8c",
               "INCONCLUSIVE": "#c7a252", "HURTS": "#c0392b"}
POLICY_COLOR = {"margin": "#555555", ana.A: "#1f6fb4", ana.B: "#117733", ana.GUD: "#d98c1f",
                ana.E8M: "#8e44ad", ana.RND: "#bbbbbb", ana.STR: "#c0392b"}
POLICY_LABEL = {"margin": "M3 margin", ana.A: "A: band coverage -> margin", ana.B: "B: 8 maximin + A",
                ana.GUD: "global unc+div -> margin", ana.E8M: "8 maximin + margin", ana.RND: "random",
                ana.STR: "straddle"}
SHORT = {"F7_exact": "F7 exact 1D", "F4_fold_a0.3": "F4 fold a0.3", "F4_fold_a0.6": "F4 fold a0.6",
         "F5_islands_k3": "F5 islands k3", "F5_islands_k8": "F5 islands k8", "F6_rot30": "F6 rot 30",
         "F6_rot60": "F6 rot 60", "F6_rot90": "F6 rot 90"}


def label(cell: str) -> str:
    return SHORT.get(cell, cell.replace("S_", "shift ").replace("_", " "))


def forest(contrasts: pd.DataFrame) -> None:
    order = ana.CORE_IDS[::-1]
    panels = [("A-margin", "A - margin"), ("B-margin", "B - margin"), ("global_unc_div-margin", "global unc+div - margin"),
              ("early8_margin-margin", "8-maximin margin - margin"), ("A-global_unc_div", "A - global unc+div")]
    fig, axes = plt.subplots(2, len(panels), figsize=(22, 13), sharey=True)
    for row, ep in enumerate(("acc_q20|16-40", "acc_q20|16-80")):
        for ax, (name, title) in zip(axes[row], panels):
            sub = contrasts[(contrasts.contrast == name) & (contrasts.endpoint == ep)].set_index("cell").loc[order]
            y = np.arange(len(order))
            for yi, (_, r) in zip(y, sub.iterrows()):
                ax.plot([r.ci_low, r.ci_high], [yi, yi], color=CLASS_COLOR[r["class"]], lw=2.2)
                ax.plot(r["mean"], yi, "o", color=CLASS_COLOR[r["class"]], ms=6)
            ax.axvline(0, color="black", lw=1)
            ax.axvspan(-ana.EQ, ana.EQ, color="#eeeeee", zorder=0)
            ax.set_title(f"{title}\n{ep.replace('acc_q20|', 'q20 accuracy AULC ')}", fontsize=10.5)
            ax.grid(axis="x", alpha=0.3)
            for boundary in (0.5, 12.5, 14.5, 16.5):          # F7 | shift | fold | islands | rotated
                ax.axhline(len(order) - 1 - boundary, color="#999999", lw=0.8)
        axes[row, 0].set_yticks(np.arange(len(order)))
        axes[row, 0].set_yticklabels([label(c) for c in order], fontsize=9)
    handles = [plt.Line2D([], [], color=c, lw=3, label=k) for k, c in CLASS_COLOR.items()]
    fig.legend(handles=handles, loc="lower center", ncol=5, fontsize=10, title="pre-registered class "
               "(Holm over 80 primary tests for A/B - margin; unadjusted otherwise); grey band = +/-0.005")
    fig.suptitle("Synthetic benchmark summary: paired differences per cell (mean and 95% bootstrap CI over 30 "
                 "independent functions)", fontsize=13)
    fig.tight_layout(rect=(0, 0.05, 1, 0.97))
    fig.savefig(FIG / "synthetic_benchmark_summary.png", dpi=150)
    plt.close(fig)


def validity(contrasts: pd.DataFrame, bins: pd.DataFrame) -> None:
    fig = plt.figure(figsize=(20, 11))
    gs = fig.add_gridspec(2, 3, height_ratios=(1.0, 1.0))
    columns = [(0.5, 1), (0.5, 3), (0.2, 1), (0.2, 3)]
    for k, (name, title) in enumerate((("A-margin", "A - margin"), ("B-margin", "B - margin"))):
        ax = fig.add_subplot(gs[0, k])
        grid_vals = np.full((4, 4), np.nan)
        classes = np.full((4, 4), "", dtype=object)
        for i, a in enumerate((0.0, 0.1, 0.3, 0.6)):
            for j, (length, d) in enumerate(columns):
                cell = "F7_exact" if a == 0.0 else f"S_a{a}_l{length}_d{d}"
                r = ana.get(contrasts, cell, name, "acc_q20|16-40")
                grid_vals[i, j], classes[i, j] = r["mean"], r["class"]
        lim = np.nanmax(np.abs(grid_vals))
        im = ax.imshow(grid_vals, cmap="RdBu", vmin=-lim, vmax=lim, origin="lower", aspect="auto")
        for i in range(4):
            for j in range(4):
                abbrev = {"HELPS_MATERIAL": "helps", "HELPS_SMALL": "helps (small)", "EQUIVALENT": "equiv.",
                          "INCONCLUSIVE": "inconcl.", "HURTS": "hurts"}[classes[i, j]]
                ax.text(j, i, f"{grid_vals[i, j]:+.4f}\n{abbrev}", ha="center", va="center", fontsize=9)
        ax.set_xticks(range(4))
        ax.set_xticklabels([f"l={l}, d={d}" for l, d in columns])
        ax.set_yticks(range(4))
        ax.set_yticklabels(["a=0 (F7)", "a=0.1 (F1)", "a=0.3", "a=0.6"])
        ax.set_xlabel("displacement length-scale l, heterogeneity dimension d")
        ax.set_ylabel("boundary displacement amplitude a (SD(h) units)")
        ax.set_title(f"{title}, q20 accuracy AULC 16-40 (smooth-shift family)", fontsize=11)
        fig.colorbar(im, ax=ax, shrink=0.8)
    ax = fig.add_subplot(gs[0, 2])
    others = ["F4_fold_a0.3", "F4_fold_a0.6", "F5_islands_k3", "F5_islands_k8", "F6_rot30", "F6_rot60", "F6_rot90"]
    x = np.arange(len(others))
    for off, (name, color) in zip((-0.2, 0.0, 0.2), (("A-margin", "#1f6fb4"), ("B-margin", "#117733"),
                                                   ("A-global_unc_div", "#d98c1f"))):
        rs = [ana.get(contrasts, c, name, "acc_q20|16-40") for c in others]
        ax.errorbar(x + off, [r["mean"] for r in rs], yerr=[[r["mean"] - r["ci_low"] for r in rs],
                    [r["ci_high"] - r["mean"] for r in rs]], fmt="o", color=color, capsize=3, label=name)
    ax.axhline(0, color="black", lw=1)
    ax.axhspan(-ana.EQ, ana.EQ, color="#eeeeee", zorder=0)
    ax.set_xticks(x)
    ax.set_xticklabels([label(c) for c in others], rotation=30, ha="right")
    ax.set_title("non-monotone, islands and misspecified-physics families\n(q20 accuracy AULC 16-40, 95% CI)",
                 fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    for k, (col, title) in enumerate((("A-margin|acc_q20|16-40", "A - margin"), ("B-margin|acc_q20|16-40", "B - margin"),
                                      ("A-global_unc_div|acc_q20|16-40", "A - global unc+div"))):
        ax = fig.add_subplot(gs[1, k])
        b = bins[bins.contrast == col].sort_values("quintile")
        centres = (b.error_low + b.error_high) / 2
        ax.errorbar(centres, b["mean"], yerr=[b["mean"] - b.ci_low, b.ci_high - b["mean"]], fmt="o-", capsize=4,
                    color="#333333")
        for _, r in b.iterrows():
            ax.axvspan(r.error_low, r.error_high, color="#f3f3f3" if r.quintile % 2 else "#e6e6e6", zorder=0)
        ax.axhline(0, color="black", lw=1)
        ax.set_xlabel("truth's best 1D-threshold-in-h error (0 = physics coordinate exact; label structure only)")
        ax.set_ylabel("paired difference, q20 accuracy AULC 16-40")
        ax.set_title(f"validity map: {title} by quintile of distance from a pure h-threshold (all 600 core functions)",
                     fontsize=10.5)
        ax.grid(alpha=0.3)
    fig.suptitle("Method validity map (pre-registered synthetic stress test)", fontsize=13.5)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "method_validity_map.png", dpi=150)
    plt.close(fig)


def curves(metrics: pd.DataFrame) -> None:
    cells = ["F7_exact", "S_a0.1_l0.5_d3", "S_a0.3_l0.5_d3", "S_a0.6_l0.2_d3", "F4_fold_a0.6", "F5_islands_k8",
             "F6_rot60", "F6_rot90"]
    fig, axes = plt.subplots(2, 4, figsize=(21, 9.5), sharex=True)
    for ax, cell in zip(axes.ravel(), cells):
        sub = metrics[metrics.cell == cell]
        for policy in ("random", "margin", ana.GUD, ana.A, ana.B):
            c = sub[sub.policy == policy].groupby("budget").acc_q20.mean()
            ax.plot(c.index, c, color=POLICY_COLOR[policy], lw=2.2 if policy in (ana.A, ana.B) else 1.6,
                    label=POLICY_LABEL[policy])
        ax.axvline(40, color="#777", ls=":", lw=1)
        ax.set_title(label(cell), fontsize=11)
        ax.grid(alpha=0.3)
    for ax in axes[1]:
        ax.set_xlabel("labels queried")
    for ax in axes[:, 0]:
        ax.set_ylabel("q20 accuracy (dense test set, mean of 30 functions)")
    axes[0, 0].legend(fontsize=8.5)
    fig.suptitle("Synthetic learning curves in representative cells", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "synthetic_learning_curves.png", dpi=150)
    plt.close(fig)


def mechanism(mech: pd.DataFrame) -> None:
    cells = ["F7_exact", "S_a0.3_l0.5_d3", "S_a0.6_l0.2_d3", "F6_rot60"]
    fig, axes = plt.subplots(1, len(cells) + 1, figsize=(24, 5))
    for ax, cell in zip(axes, cells):
        for policy in ("margin", ana.A, ana.B, ana.GUD):
            r = mech[(mech.cell == cell) & (mech.policy == policy)].iloc[0]
            ax.plot((16, 20, 24, 28, 32, 40), [r[f"separable_B{b}"] for b in (16, 20, 24, 28, 32, 40)], "o-",
                    color=POLICY_COLOR[policy], label=POLICY_LABEL[policy])
        ax.set_title(f"{label(cell)}: share of functions with queried\nlabels still separable in h", fontsize=10.5)
        ax.set_xlabel("labels queried")
        ax.set_ylim(-0.02, 1.02)
        ax.grid(alpha=0.3)
    axes[0].legend(fontsize=8.5)
    ax = axes[-1]
    sub = mech[mech.policy == ana.A].set_index("cell").loc[ana.CORE_IDS]
    ax.barh([label(c) for c in ana.CORE_IDS][::-1], sub.band_fraction_B16_39.to_numpy()[::-1], color="#1f6fb4")
    ax.set_title("A: share of the pool inside the label-estimated\nband (mean over B16-39)", fontsize=10.5)
    ax.tick_params(axis="y", labelsize=8)
    ax.grid(axis="x", alpha=0.3)
    fig.suptitle("Post-hoc mechanism diagnostics (explanatory only)", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(FIG / "synthetic_mechanism.png", dpi=150)
    plt.close(fig)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    contrasts = pd.read_csv(OUT / "synthetic_contrasts.csv")
    bins = pd.read_csv(OUT / "synthetic_validity_bins.csv")
    metrics = pd.read_csv(OUT / "synthetic_metrics_by_budget.csv.gz")
    mech = pd.read_csv(OUT / "synthetic_mechanism.csv")
    forest(contrasts)
    validity(contrasts, bins)
    curves(metrics)
    mechanism(mech)


if __name__ == "__main__":
    main()
