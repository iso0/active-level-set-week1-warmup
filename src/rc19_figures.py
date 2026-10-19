"""RC19 figures from the report CSVs (run after `python -m src.rc19_report all`). Static PNGs for the thesis.
    python -m src.rc19_figures
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import src.rc19_final as F
import src.rc19_pool as P

REP = P.OUT / "report"
# colour-blind-safe categorical order (Okabe-Ito), fixed per arm, never cycled
COL = {"M0": "#999999", "M0Q": "#56B4E9", "SHQ": "#0072B2", "MAXIMIN": "#555555", "RANDOM": "#999999", "STRADDLE": "#0072B2", "TRUVAR": "#E69F00",
       "MOIVR": "#D55E00", "G3_MARGIN": "#555555", "E1_STRADDLE": "#0072B2", "E1_MAXIMIN": "#56B4E9", "PHYSCF_ATS_MARGIN": "#D55E00",
       "PHYSCF_A_MARGIN": "#E69F00", "PHYSMC_ATS_MARGIN": "#CC79A7", "PHYSCF_ATS_MAXIMIN": "#F0C987"}


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9.5, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e8e8e8", "lines.linewidth": 1.8})
    return plt


def band(ax, g, x, y, color, label, ls="-"):
    m = g.groupby(x)[y].mean(); lo = g.groupby(x)[y].min(); hi = g.groupby(x)[y].max()
    ax.plot(m.index, m.values, color=color, ls=ls, label=label); ax.fill_between(m.index, lo.values, hi.values, color=color, alpha=0.12, lw=0)


def regression(plt):
    R = pd.read_csv(REP / "reg_curves.csv"); R = R[R.target.isin(F.PRIMARY_TARGETS) & (R.budget >= P.B0)]
    A = R.groupby(["model", "acq", "repeat", "budget"]).R2.mean().reset_index()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    for (m, a), g in A.groupby(["model", "acq"]):
        if a == "MAXIMIN":
            band(axes[0], g, "budget", "R2", COL[m], m)
        if m in ("SHQ", "M0Q"):
            band(axes[1], g, "budget", "R2", COL[a], f"{m} · {a}", ls="-" if m == "SHQ" else "--")
    axes[0].set_title("Same design (MAXIMIN): simple vs rich model"); axes[1].set_title("Same model: label-free vs adaptive designs")
    for ax in axes:
        ax.set_xlabel("total revealed simulations (startup included)"); ax.legend(frameon=False, fontsize=8)
    axes[0].set_ylabel("held-out R² (mean of the 8 outputs)")
    fig.suptitle("Pooled from scratch (DEV r3–10): physical outputs; line = mean of 8 repeats, band = range", x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(); fig.savefig(REP / "fig_regression_curves.png", dpi=160); plt.close(fig)
    fig, axes = plt.subplots(2, 4, figsize=(15, 6.4), sharex=True); axes = axes.ravel()
    for ax, t in zip(axes, F.PRIMARY_TARGETS):
        g0 = R[(R.target == t) & (R.acq == "MAXIMIN")]
        for m, g in g0.groupby("model"):
            band(ax, g, "budget", "R2", COL[m], m)
        g1 = R[(R.target == t) & (R.model == "SHQ") & (R.acq == "MOIVR")]; band(ax, g1, "budget", "R2", COL["MOIVR"], "SHQ · MOIVR", ls="--")
        ax.axhline(F.LEVELS[t], color="#CC79A7", ls=":", lw=1); ax.set_title(t, fontsize=9); ax.set_ylim(max(-0.2, ax.get_ylim()[0]), 1.0)
    axes[0].legend(frameon=False, fontsize=7.5)
    for ax in axes[4:]:
        ax.set_xlabel("total revealed simulations")
    fig.suptitle("Per output (dotted = absolute target level)", x=0.01, ha="left", fontsize=10.5); fig.tight_layout(); fig.savefig(REP / "fig_regression_per_output.png", dpi=160); plt.close(fig)


def region(plt):
    G = pd.read_csv(REP / "region_curves.csv")
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2), sharey=False)
    for (m, a), g in G.groupby(["model", "acq"]):
        ls = "-" if m == "SHQ" else "--"
        band(axes[0], g, "budget", "BA", COL[a], f"{m} · {a}", ls)
        if m == "SHQ":
            band(axes[1], g, "budget", "recall_in", COL[a], a); band(axes[2], g, "budget", "recall_out", COL[a], a)
    axes[0].set_title("balanced accuracy"); axes[1].set_title("recall inside the region (SHQ)"); axes[2].set_title("recall outside (SHQ)")
    for ax in axes:
        ax.set_xlabel("total revealed simulations"); ax.legend(frameon=False, fontsize=7.5)
    fig.suptitle("Velocity-spike region {spike log-ratio ≥ log 2}, pooled from scratch (DEV r3–10)", x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(); fig.savefig(REP / "fig_region_curves.png", dpi=160); plt.close(fig)


def label(plt):
    B = pd.read_csv(REP / "label_metrics.csv")
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    for a, g in B.groupby("arm"):
        ls = "--" if a.endswith("MAXIMIN") else "-"
        band(axes[0], g, "budget", "BA", COL.get(a, "k"), a, ls); band(axes[1], g, "budget", "log_loss", COL.get(a, "k"), a, ls); band(axes[2], g, "budget", "spec_NEW", COL.get(a, "k"), a, ls)
    axes[0].set_title("balanced accuracy (pooled test runs)"); axes[1].set_title("log loss (lower is better)"); axes[2].set_title("failed corner: conduction recall on NEW-batch runs")
    for ax in axes:
        ax.set_xlabel("total revealed simulations")
    axes[0].legend(frameon=False, fontsize=7.2)
    fig.suptitle("Keyhole label, pooled from scratch (DEV r3–10); the corner panel is an evaluator-only diagnostic", x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(); fig.savefig(REP / "fig_label_curves.png", dpi=160); plt.close(fig)


def main():
    plt = _plt()
    for fn in (regression, region, label):
        try:
            fn(plt)
        except FileNotFoundError as ex:
            print("skip", fn.__name__, ex)
    print("figures in", REP)


if __name__ == "__main__":
    main()
