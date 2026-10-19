"""RC19B static figures for the thesis (presentation only; run after `python -m src.rc19b_report all` and the viewer build).
    python -m src.rc19b_figures      -> opus_rc19b/report/fig_rc19b_*.png
Panels: Keyhole learning curves of the final arms (BA, log loss, fast-scan-corner conduction recall); the matched-path
decomposition on ATSCF's own paths; duration R2 of the own GP vs the hurdle per arm; joint completion; and the boundary evolution
of ONE learner (the viewer's pre-declared repeat 11 / fold 1) at one LS slice with ST fixed.
"""
from __future__ import annotations

import base64
import json

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_final as F19
import src.rc19b_final as F

OUT = RC.ROOT / "outputs" / "research_campaign_20261018" / "opus_rc19b"
REP = OUT / "report"
# Okabe-Ito, fixed per arm (never cycled)
COL = {"E1RAW+straddle": "#0072B2", "E1CAL+straddle": "#56B4E9", "ATSCF_MARGIN": "#D55E00", "DEPTHCF_MARGIN": "#E69F00", "G3_MARGIN": "#555555",
       "ATSAPPROX_MARGIN": "#CC79A7", "E1RAW": "#0072B2", "E1CAL": "#56B4E9", "ATSCF": "#D55E00", "DEPTHCF": "#E69F00", "G3": "#555555", "ATSAPPROX": "#CC79A7",
       "SHQ+RANDOM": "#555555", "M0Q+MOIVR": "#56B4E9", "SHQ+MOIVR": "#0072B2", "SHQ+MOIVRB": "#D55E00"}


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9.5, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e8e8e8", "lines.linewidth": 1.8})
    return plt


def band(ax, g, x, y, color, label, ls="-"):
    m = g.groupby(x)[y].mean(); lo = g.groupby(x)[y].min(); hi = g.groupby(x)[y].max()
    ax.plot(m.index, m.values, color=color, ls=ls, label=label); ax.fill_between(m.index, lo.values, hi.values, color=color, alpha=0.10, lw=0)


def keyhole(plt):
    B = pd.read_csv(REP / "keyhole_final_metrics.csv")
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.3))
    for a in ("E1RAW+straddle", "E1CAL+straddle", "DEPTHCF_MARGIN", "ATSCF_MARGIN", "ATSAPPROX_MARGIN", "G3_MARGIN"):
        g = B[B.arm == a]
        if g.empty:
            continue
        band(axes[0], g, "budget", "BA", COL[a], a); band(axes[1], g, "budget", "log_loss", COL[a], a); band(axes[2], g, "budget", "spec_NEW", COL[a], a)
    axes[0].set_title("balanced accuracy"); axes[1].set_title("log loss (lower is better)"); axes[2].set_title("fast-scan corner: conduction recall (NEW-batch runs)")
    axes[1].set_ylim(0, min(0.6, axes[1].get_ylim()[1]))
    for ax in axes:
        ax.set_xlabel("total revealed simulations (startup included)")
    axes[0].legend(frameon=False, fontsize=7.5)
    fig.suptitle("RC19B Keyhole, fresh DEV repeats 11–18; each arm on its own adaptive path; line = mean of 8 repeats, band = range", x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(); fig.savefig(REP / "fig_rc19b_keyhole_curves.png", dpi=160); plt.close(fig)


def decomposition(plt):
    B = pd.read_csv(REP / "keyhole_final_decomposition_metrics.csv")
    paths = [a for a in ("ATSCF_MARGIN", "E1S") if B.arm.str.endswith("@" + a).any()]
    fig, axes = plt.subplots(1, len(paths), figsize=(6.2 * len(paths), 4.3), squeeze=False); axes = axes[0]
    for ax, path in zip(axes, paths):
        for c in ("E1RAW", "E1CAL", "DEPTHCF", "ATSCF", "ATSAPPROX", "G3"):
            g = B[B.arm == f"{c}@{path}"]
            if len(g):
                band(ax, g, "budget", "log_loss", COL[c], c)
        ax.set_title(f"same paid prefixes: the paths of {path}"); ax.set_xlabel("total revealed simulations"); ax.set_ylim(0, 0.6)
    axes[0].set_ylabel("log loss (held-out runs)"); axes[0].legend(frameon=False, fontsize=7.5)
    fig.suptitle("Where the probability gain comes from: every construction on the same paths (exploratory, fresh repeats)", x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(); fig.savefig(REP / "fig_rc19b_keyhole_decomposition.png", dpi=160); plt.close(fig)


def duration(plt):
    D = pd.read_csv(REP / "duration_final_curves.csv"); J = pd.read_csv(REP / "duration_final_joint.csv")
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.3))
    for (m, a), g in D.groupby(["model", "acq"]):
        arm = f"{m}+{a}"
        band(axes[0], g[g.variant == "ORIG_GP"], "budget", "R2", COL[arm], f"{arm} · own GP"); band(axes[0], g[g.variant == "HURDLE"], "budget", "R2", COL[arm], f"{arm} · hurdle", ls="--")
    axes[0].axhline(F19.LEVELS["vmax_spike_us"], color="#CC79A7", ls=":", lw=1); axes[0].set_ylim(-0.2, 1); axes[0].set_title("spike duration: held-out R² (dotted = target 0.60)")
    axes[0].set_xlabel("total revealed simulations"); axes[0].legend(frameon=False, fontsize=7)
    S = J.assign(done=~J.joint_censored.astype(bool)).groupby(["model", "acq", "variant"]).done.sum().reset_index(); S["arm"] = S.model + "+" + S.acq
    arms = [f"{m}+{a}" for m, a in F.REG_ARMS]; x = np.arange(len(arms)); w = 0.38
    for k, (v, ls) in enumerate((("ORIG_GP", "own GP duration"), ("HURDLE", "hurdle duration"))):
        y = [int(S[(S.arm == a) & (S.variant == v)].done.sum()) for a in arms]
        axes[1].bar(x + (k - 0.5) * w, y, w * 0.92, color=[COL[a] for a in arms], alpha=1.0 if v == "ORIG_GP" else 0.45, label=ls)
        for xi, yi in zip(x + (k - 0.5) * w, y):
            axes[1].text(xi, yi + 0.1, str(yi), ha="center", fontsize=8)
    axes[1].set_xticks(x, arms, fontsize=8); axes[1].set_ylim(0, 8.8); axes[1].set_ylabel("repeats with joint completion by B80 (of 8)")
    axes[1].set_title("joint 8-output completion (solid = own GP, light = hurdle)"); axes[1].legend(frameon=False, fontsize=7.5)
    fig.suptitle("RC19B physical outputs, fresh DEV repeats 11–18 (fixed absolute targets)", x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(); fig.savefig(REP / "fig_rc19b_duration.png", dpi=160); plt.close(fig)


def boundary(plt, learners=("E1S · E1CAL", "ATSCF_MARGIN · ATSCF"), budgets=(8, 16, 24, 40, 60), ls_i=2, st_i=1):
    V = json.loads((OUT / "viewer" / "single_learner_view.json").read_text(encoding="utf-8")); G = V["grid"]; NG = G["NG"]; T = V["tasks"]["label"]; R = V["runs"]
    fig, axes = plt.subplots(len(learners), len(budgets), figsize=(3.1 * len(budgets), 3.0 * len(learners)), squeeze=False, sharex=True, sharey=True)
    off = (st_i * len(G["LS_um"]) + ls_i) * NG * NG; LS0, ST0 = G["LS_um"][ls_i], G["ST_K"][st_i]
    for i, lname in enumerate(learners):
        Lr = T["learners"][lname]
        for j, b in enumerate(budgets):
            ax = axes[i, j]; E = Lr["budgets"][str(b)]; q = np.frombuffer(base64.b64decode(E["grid"]), np.uint8)[off:off + NG * NG].astype(float)
            z = np.where(q == 255, np.nan, q / 250).reshape(NG, NG)
            ax.pcolormesh(G["logP"], G["logVX"], z, cmap="RdBu_r", vmin=0, vmax=1, shading="nearest")
            if np.nanstd(z) > 1e-9:
                ax.contour(G["logP"], G["logVX"], z, levels=[0.5], colors="k", linewidths=1.6)
            band_ = [k for k in E["paid"] if abs(R["LS_um"][k] - LS0) <= G["ls_band"] and abs(R["ST"][k] - ST0) <= G["st_band"]]
            ax.scatter([R["logP"][k] for k in band_], [R["logVX"][k] for k in band_], marker="D", s=22, facecolors=["#7a2410" if R["y"][k] else "#10395c" for k in band_],
                       edgecolors="k", linewidths=0.8)
            ax.set_title(f"{lname.split(' · ')[1]} · b = {b}", fontsize=9); ax.grid(False)
            if i == len(learners) - 1:
                ax.set_xlabel("log P")
            if j == 0:
                ax.set_ylabel("log VX")
    fig.suptitle(f"Boundary evolution of ONE learner (repeat {T['repeat']}, fold {T['fold']}): P(Keyhole) on a grid at LS = {LS0:.0f} µm, ST = {ST0:.0f} K; "
                 f"black = p 0.5; diamonds = its paid runs within ±{G['ls_band']:.0f} µm / ±{G['st_band']:.1f} K", x=0.01, ha="left", fontsize=9.5)
    fig.tight_layout(); fig.savefig(REP / "fig_rc19b_boundary_evolution.png", dpi=160); plt.close(fig)


def main():
    plt = _plt()
    for fn in (keyhole, decomposition, duration, boundary):
        try:
            fn(plt)
        except FileNotFoundError as ex:
            print("skip", fn.__name__, ex)
    print("figures in", REP)


if __name__ == "__main__":
    main()
