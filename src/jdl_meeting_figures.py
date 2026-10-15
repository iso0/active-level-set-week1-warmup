"""Figures for IOAN_RESEARCH_UPDATE.md (2026-10-15).  Reads only committed result files; computes nothing new except
the interim ASTRA_AL evaluation it is given.  Fixed-path and adaptive studies are drawn in separate figures, and repeats
are never pooled across arms that were evaluated on different repeats.
    python -m src.jdl_meeting_figures --threads 1
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
W20 = ROOT / "outputs" / "week20_active_temporal_development"
JDL = ROOT / "outputs" / "joint_depth_label_development"
FIG = JDL / "meeting_figures"
# Okabe-Ito (colour-blind safe); one colour per system across all figures
COL = {"G3": "#555555", "WHOLE_E1": "#56B4E9", "ACTIVE_E1": "#0072B2", "J_trained": "#D55E00", "JT_PV": "#E69F00", "V2": "#009E73", "VX_stump": "#CC79A7"}
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e6e6", "grid.linewidth": 0.8,
                     "axes.axisbelow": True, "savefig.bbox": "tight", "savefig.dpi": 170})


def fig1():
    """Whole-record -> ACTIVE depth target: DEV (repeats 1-8) against the one-shot C3 confirmation (repeats 17-20)."""
    dev = pd.read_csv(W20 / "track1_ext" / "contrasts_r1_8.csv"); c3 = pd.read_csv(W20 / "c3" / "contrasts.csv")
    rows = [("WHOLE_E1_STRADDLE", "G3_MARGIN", "Original E1 (whole-record depth)\nminus G3"),
            ("ACTIVE_E1_STRADDLE", "WHOLE_E1_STRADDLE", "ACTIVE-window depth target\nminus whole-record target"),
            ("ACTIVE_E1_STRADDLE", "G3_MARGIN", "ACTIVE E1 + straddle\nminus G3 + margin")]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    for ax, task, title in ((axes[0], "R3_NEW", "NEW population (136 runs, 12 no-Keyhole)"), (axes[1], "R3_OLD", "OLD population (note the smaller x scale)")):
        for i, (a, r, lab) in enumerate(rows):
            y = len(rows) - 1 - i
            for df, dy, mk, fc, name in ((dev, 0.14, "o", "white", "DEV, repeats 1-8 (inspected)"), (c3, -0.14, "s", "black", "C3 confirmation, repeats 17-20 (one shot)")):
                q = df[(df.task == task) & (df.arm == a) & (df.ref == r) & (df.metric == "BA_AULC")].iloc[0]
                ax.errorbar(q["mean"], y + dy, xerr=[[q["mean"] - q["lo"]], [q["hi"] - q["mean"]]], fmt=mk, mfc=fc, mec="black", ecolor="black", ms=7, capsize=3, lw=1.2,
                            label=name if (i == 0 and task == "R3_NEW") else None)
                ax.annotate(f"{q['mean']:+.3f}", (q["hi"], y + dy), xytext=(5, -3), textcoords="offset points", fontsize=8.5)
        ax.axvline(0, color="black", lw=0.8)
        if task == "R3_NEW":
            ax.plot([0.02, 0.02], [-0.45, 0.45], color="#D55E00", lw=2)
            ax.text(-0.095, -0.70, "orange line = frozen C3 bar (>= +0.02 with interval > 0)", fontsize=8.5, color="#D55E00")
        ax.set_title(title, fontsize=10.5); ax.set_xlabel("difference in BA-AULC (95% interval)")
        ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[2] for r in rows][::-1]); ax.set_ylim(-0.8, len(rows) - 0.4)
    axes[0].legend(loc="lower left", bbox_to_anchor=(0.0, -0.42), ncol=2, frameon=False, fontsize=9)
    fig.suptitle("Figure 1. Whole-record -> ACTIVE depth target.  Replicated: ACTIVE beats WHOLE on NEW.  NOT CONFIRMED: ACTIVE beats G3.\n"
                 "(Week 18-20 adaptive runs: each arm on its own paths; BA-AULC up to B80; paired differences per repeat, 95% repeat-bootstrap interval)",
                 fontsize=10.5, x=0.02, ha="left", y=1.0)
    fig.subplots_adjust(top=0.82)
    FIG.mkdir(parents=True, exist_ok=True); fig.savefig(FIG / "fig1_whole_to_active.png"); plt.close(fig)


def fig2():
    """Strongest fair model comparison: identical fixed feature-only paths, NEW B40, DEV repeats 1-2."""
    m = pd.read_csv(JDL / "v2_model_comparison" / "metrics_per_repeat.csv"); m = m[m.budget == 40]
    a1 = pd.read_csv(JDL / "v2_decision_audit" / "A1_extended_ladder" / "metrics_per_repeat.csv")
    a1 = a1[(a1.arm == "V2_EP_mixture") & (a1.budget == 40) & (a1.rule == "finite_batch")]
    pts = [("G3", "p>=0.5", "G3, cutoff 0.5", "G3", "o"), ("ACTIVE_E1", "p>=0.5", "ACTIVE E1, cutoff 0.5", "ACTIVE_E1", "o"),
           ("J_trained", "p>=0.5", "J_trained, cutoff 0.5", "J_trained", "o"), ("V2_EP_mixture", "p>=0.5", "V2, cutoff 0.5", "V2", "o"),
           ("J_trained", "p>=pi_hat", "J_trained, cutoff pi-hat", "J_trained", "^"), ("V2_EP_mixture", "p>=pi_hat", "V2, cutoff pi-hat", "V2", "^"),
           ("V2_EP_mixture", "finite_batch", "V2, finite-batch BA rule\n(A1, amended)", "V2", "s"), ("ACTIVE_E1", "p>=pi_hat", "ACTIVE E1, cutoff pi-hat", "ACTIVE_E1", "^"),
           ("VX_stump", "p>=0.5", "VX stump\n(one learned VX cut)", "VX_stump", "D")]
    fig, ax = plt.subplots(figsize=(8.6, 5.6))
    g3 = m[(m.arm == "G3") & (m.rule == "p>=0.5")].shortK_sensitivity.mean()
    ax.axhspan(g3 - 0.10, 1.05, color="#0072B2", alpha=0.06, lw=0)
    ax.text(0.455, 1.03, "shaded: short-K retained relative to G3 (at most 2 more missed events of 20)", fontsize=8.5, color="#0072B2", va="top")
    # label positions in data coordinates (leader lines where the bottom-right corner is crowded)
    txt = {"G3, cutoff 0.5": (0.625, 0.345), "ACTIVE E1, cutoff 0.5": (0.745, 0.625), "J_trained, cutoff 0.5": (0.585, 0.545), "V2, cutoff 0.5": (0.565, 0.82),
           "ACTIVE E1, cutoff pi-hat": (0.80, 0.42), "J_trained, cutoff pi-hat": (0.885, 0.17), "V2, cutoff pi-hat": (0.86, 0.29),
           "V2, finite-batch BA rule\n(A1, amended)": (0.68, 0.05), "VX stump\n(one learned VX cut)": (0.70, 0.17)}
    for arm, rule, lab, c, mk in pts:
        d = a1 if rule == "finite_batch" else m[(m.arm == arm) & (m.rule == rule)]
        d = d.sort_values("repeat"); x, y = d.BA.to_numpy(float), d.shortK_sensitivity.to_numpy(float)
        ax.plot(x, y, color=COL[c], lw=0.8, alpha=0.6); ax.scatter(x, y, s=14, color=COL[c], alpha=0.6, marker=mk)
        ax.scatter(x.mean(), y.mean(), s=85, color=COL[c], marker=mk, edgecolor="black", lw=0.7, zorder=3)
        ax.annotate(lab, (x.mean(), y.mean()), xytext=txt[lab], textcoords="data", fontsize=8.5,
                    arrowprops=dict(arrowstyle="-", color="#888888", lw=0.6, shrinkA=0, shrinkB=5))
    cl = JDL / "corner_local" / "results" / "metrics_by_budget.csv"
    if cl.exists():                                                      # Experiment C1 on the same fixed paths (registered today)
        c = pd.read_csv(cl); c = c[(c.setting == "TREED@FIXED_PATHS") & (c.budget == 40)].sort_values("repeat")
        if len(c) == 2:
            x, y = c.BA.to_numpy(float), c.shortK_sensitivity.to_numpy(float)
            ax.plot(x, y, color="#000000", lw=0.8, alpha=0.6); ax.scatter(x, y, s=14, color="#000000", marker="*")
            ax.scatter(x.mean(), y.mean(), s=190, color="#F0E442", marker="*", edgecolor="black", lw=0.8, zorder=4)
            ax.annotate("C1 local corner model, cutoff 0.5\n(registered today)", (x.mean(), y.mean()), xytext=(0.80, 0.68), textcoords="data", fontsize=8.5,
                        arrowprops=dict(arrowstyle="-", color="#888888", lw=0.6, shrinkA=0, shrinkB=6))
    ax.set_xlim(0.45, 0.95); ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("balanced accuracy on NEW at B40 (mean of repeats 1-2; small dots = each repeat)")
    ax.set_ylabel("short-Keyhole recall (10 short-K runs per repeat)")
    ax.set_title("Figure 2. Same fixed paths, same budget: every rule above BA 0.8 gives up short-Keyhole detection", fontsize=10.5, loc="left")
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker=k, ls="", color="gray", mec="black", ms=8, label=v) for k, v in (("o", "cutoff 0.5"), ("^", "cutoff pi-hat (paid positive fraction)"),
                                                                                               ("s", "finite-batch BA rule"), ("D", "learned VX stump"))]
    ax.legend(handles=h, loc="lower left", frameon=False, fontsize=8.5)
    fig.savefig(FIG / "fig2_fixed_path_comparison.png"); plt.close(fig)


def fig3():
    """Sequential (adaptive) learning curves: TRAINED_AL B16-B40 and, if available, interim ASTRA_AL B16-B24, per repeat."""
    t = pd.read_csv(JDL / "trained_al" / "results" / "metrics_by_budget.csv")
    arms = [("G3_MARGIN", "G3 + margin", COL["G3"], "-"), ("ACTIVE_E1_STRADDLE", "ACTIVE E1 + straddle", COL["ACTIVE_E1"], "-"),
            ("JT_MARGIN", "J_trained + margin (cutoff 0.5)", COL["J_trained"], "-"), ("JT_PV", "J_trained + probability-variance", COL["JT_PV"], "--")]
    aa_file = JDL / "astra_al" / "results" / "metrics_by_budget.csv"
    aa = pd.read_csv(aa_file) if aa_file.exists() and aa_file.stat().st_size > 10 else pd.DataFrame()
    aa_status = json.loads((JDL / "astra_al" / "results" / "ASTRA_AL_RESULTS.json").read_text()) if (JDL / "astra_al" / "results" / "ASTRA_AL_RESULTS.json").exists() else None
    v2arms = [("ALIGNED_MARGIN", "ASTRA_AL interim: V2 + aligned margin (finite-batch rule)", "#009E73", "-"),
              ("V2_VARIANCE", "ASTRA_AL interim: V2 + variance lookahead (finite-batch rule)", "#009E73", ":"),
              ("BA_RISK", "ASTRA_AL interim: V2 + BA-risk lookahead (finite-batch rule)", "#000000", "-.")]
    clf = JDL / "corner_local" / "results" / "metrics_by_budget.csv"
    cl = pd.read_csv(clf) if clf.exists() else None
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.2), sharex=True)
    for j, rep in enumerate((3, 4)):
        for i, (key, ylab) in enumerate((("BA", "balanced accuracy"), ("shortK_sensitivity", "short-Keyhole recall"))):
            ax = axes[i, j]
            for arm, lab, c, ls in arms:
                d = t[(t.arm == arm) & (t.repeat == rep)].sort_values("budget")
                if len(d):
                    ax.plot(d.budget, d[key], color=c, ls=ls, lw=1.6, label=lab)
            if cl is not None:
                d = cl[(cl.setting == "TREED@TREED_PATHS") & (cl.repeat == rep)].sort_values("budget")
                if len(d):
                    ax.plot(d.budget, d[key], color="#CC79A7", ls="-", lw=2.0, label="C1 local corner model + margin (cutoff 0.5)")
            if len(aa):
                for arm, lab, c, ls in v2arms:
                    d = aa[(aa.arm == arm) & (aa.repeat == rep)].sort_values("budget")
                    if len(d):
                        ax.plot(d.budget, d[key], color=c, ls=ls, lw=2.0, label=lab)
            if rep == 3:
                ax.text(17, 0.05 if key == "BA" else 0.22, "G3 and ACTIVE E1: not available in repeat 3\n(the frozen start of fold 4 has no negative)",
                        fontsize=8, color="#555555")
            ax.set_ylim(0.0, 1.02) if key == "shortK_sensitivity" else ax.set_ylim(0.0, 1.0)
            if i == 1:
                ax.set_xlabel("simulations paid (budget)")
            if j == 0:
                ax.set_ylabel(ylab)
            ax.set_title(f"repeat {rep}: {ylab}", fontsize=10)
            ax.set_xticks(range(16, 41, 4))
    seen = {}
    for ax in axes.ravel():
        for hh, ll in zip(*ax.get_legend_handles_labels()):
            seen.setdefault(ll, hh)
    fig.legend(list(seen.values()), list(seen.keys()), loc="lower center", ncol=2, frameon=False, fontsize=8.8, bbox_to_anchor=(0.5, -0.10))
    note = "ASTRA_AL (V2 arms, B16-B24): ONGOING"
    if aa_status:
        note += f" - {aa_status['units_done']}/{aa_status['units_expected']} units finished; a curve is drawn only where all five folds of the repeat are finished"
    fig.suptitle("Figure 3. Adaptive (sequential) studies on NEW from the same frozen B16 starts; each repeat shown separately\n" + note, fontsize=10.5, x=0.02, ha="left")
    fig.savefig(FIG / "fig3_sequential_curves.png"); plt.close(fig)


if __name__ == "__main__":
    fig1(); fig2(); fig3()
    print("figures written to", FIG)
