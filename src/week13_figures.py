"""Week 13 figures (real-data diagnostics, theory checks, synthetic summaries)."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
W13 = ROOT / "outputs/week13_boundary_evaluation_and_mechanisms"
FIG = W13 / "figures"
BLUE, ORANGE, AQUA, GRAY, INK, MUTED = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984", "#0b0b0b", "#52514e"
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True,
                     "grid.color": "#e6e5e0", "grid.linewidth": .6, "lines.linewidth": 2, "legend.frameon": False})


def fig_discovery():
    new = pd.read_csv(W13 / "theory_checks/new_discovery_certificates.csv")
    old = pd.read_csv(W13 / "theory_checks/old_discovery_reference.csv")
    fig, ax = plt.subplots(1, 2, figsize=(8.6, 3.4))
    for d, c, lab in ((old, BLUE, "OLD pools"), (new, ORANGE, "NEW pools")):
        ax[0].scatter(d.h_16, d.rho_star, s=16, color=c, alpha=.75, label=lab, edgecolor="white", linewidth=.4)
    lim = [0.8, 3.4]
    ax[0].plot(lim, lim, color=GRAY, lw=1, ls="--")
    ax[0].text(2.55, 2.75, "certified\n(ρ* > h₁₆)", color=MUTED, fontsize=8)
    ax[0].text(2.3, 1.05, "not certified", color=MUTED, fontsize=8)
    ax[0].set(xlabel="fill distance of B16 maximin design, h₁₆", ylabel="largest rare-pure radius ρ*", xlim=lim, ylim=lim,
              title="Discovery certificate (Prop. 4)")
    ax[0].legend(loc="upper left")
    g = new.guarantee_budget.fillna(new.n_pool)
    ax[1].scatter(g, new.maximin_first_both, s=16, color=ORANGE, alpha=.75, edgecolor="white", linewidth=.4)
    ax[1].plot([0, 60], [0, 60], color=GRAY, lw=1, ls="--")
    ax[1].axhline(16, color=MUTED, lw=1, ls=":")
    ax[1].text(41, 17, "frozen B16", color=MUTED, fontsize=8)
    ax[1].set(xlabel="certified budget  min{b : h_b < ρ*}", ylabel="observed maximin discovery budget",
              title="NEW: discovery never exceeds the certificate", xlim=(0, 60), ylim=(0, 30))
    fig.tight_layout()
    fig.savefig(FIG / "fig1_discovery_certificate.png", dpi=200)


def fig_metric_window():
    aul = pd.read_csv(W13 / "real_data/new_al_mean_aulc_by_arm.csv").set_index("arm")
    order = ["ALWAYS_KEYHOLE_reference", "M3_random__maximin16_continue", "M3_margin__maximin16_continue",
             "Candidate_A__maximin16_continue", "Candidate_B__maximin8_continue", "M3_margin__maximin8_continue",
             "M3_margin__adaptive_physics8", "M3_margin__physics_stratified8", "M3_margin__uniform8_continue"]
    names = ["always-Keyhole", "random16", "margin16", "Cand. A", "Cand. B", "margin8", "adaptive8", "strata8", "uniform8"]
    metrics = [("q20_accuracy_meanfold", "q20 accuracy (primary)"), ("full_balanced_accuracy_pooled", "full balanced accuracy"),
               ("gabriel_BEF1", "boundary-edge F1 (Gabriel)")]
    fig, ax = plt.subplots(1, 3, figsize=(10, 3.4), sharey=True)
    y = np.arange(len(order))
    for a, (m, t) in zip(ax, metrics):
        v = aul.loc[order, m].to_numpy()
        cols = [GRAY] + [ORANGE if n == "random16" else BLUE for n in names[1:]]
        a.barh(y, v, color=cols, height=.6)
        a.set_xlim(v.min() - (v.max() - v.min()) * .6, v.max() + (v.max() - v.min()) * .25)
        a.axvline(v[0], color=GRAY, lw=1, ls="--")
        a.set_title(t)
        for yy, vv in zip(y, v):
            a.text(vv, yy, f" {vv:.3f}", va="center", fontsize=7, color=INK)
        a.grid(axis="y", visible=False)
    ax[0].set_yticks(y, names)
    ax[0].invert_yaxis()
    fig.suptitle("NEW-136, AULC B16–B80 of the same 800 Week 12 paths under three metrics (dashed: always-Keyhole)", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "fig2_new_metric_reversal.png", dpi=200)


def fig_rare_exhaustion():
    q = pd.read_csv(ROOT / "outputs/week12_startup_and_transfer_development/active_learning/query_paths.csv.gz")
    q = q.sort_values(["arm", "split_id", "query_order"])
    q["cum_rare"] = (1 - q.revealed_label).groupby([q.arm, q.split_id]).cumsum()
    m = q.groupby(["arm", "query_order"]).cum_rare.mean().unstack(0)
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for arm, c, lab in (("M3_margin__maximin16_continue", BLUE, "margin16"), ("Candidate_B__maximin8_continue", AQUA, "Candidate B"),
                        ("M3_random__maximin16_continue", ORANGE, "random16")):
        ax.plot(m.index, m[arm], color=c, label=lab)
    ax.axhline(9.6, color=GRAY, ls="--", lw=1)
    ax.text(2, 9.75, "mean rare cases in training pool (9.6)", color=MUTED, fontsize=8)
    ax.axvspan(16, 80, color="#f3f2ee", zorder=0)
    ax.text(48, 1, "primary AULC window", color=MUTED, fontsize=8, ha="center")
    ax.set(xlabel="paid queries", ylabel="rare (non-Keyhole) labels acquired", title="NEW: rare-class exhaustion", ylim=(0, 11))
    ax.legend(loc="center right")
    fig.tight_layout()
    fig.savefig(FIG / "fig3_new_rare_exhaustion.png", dpi=200)


def fig_level_shift():
    old = pd.read_csv(ROOT / "outputs/week12_startup_and_transfer_development/audit/old405_inputs_labels.csv")
    new = pd.read_csv(ROOT / "outputs/week12_startup_and_transfer_development/audit/new136.csv")
    fig, ax = plt.subplots(1, 2, figsize=(8.6, 3.4))
    for d, mk, lab in ((old, "o", "OLD"), (new, "^", "NEW")):
        for cls, c in ((1, BLUE), (0, ORANGE)):
            s = d[d.has_keyhole == cls]
            ax[0].scatter(np.log(s.VX), s.log_h, s=10 if lab == "OLD" else 22, marker=mk, color=c, alpha=.35 if lab == "OLD" else .9,
                          edgecolor="white", linewidth=.3, label=f"{lab} {'Keyhole' if cls else 'non-Keyhole'}")
    ax[0].set(xlabel="log VX", ylabel="log h", title="Physics coordinate: OLD separable, NEW oblique")
    ax[0].legend(fontsize=7, loc="lower left")
    s = new
    ax[1].scatter(s.VX[s.has_keyhole == 1], s.P[s.has_keyhole == 1], s=18, color=BLUE, alpha=.8, label="NEW Keyhole", edgecolor="white", linewidth=.3)
    ax[1].scatter(s.VX[s.has_keyhole == 0], s.P[s.has_keyhole == 0], s=30, marker="^", color=ORANGE, label="NEW non-Keyhole", edgecolor="white", linewidth=.3)
    box = (old.P.between(new.P.min(), new.P.max())) & (old.LS.between(new.LS.min(), new.LS.max()))
    o = old[box]
    ax[1].scatter(o.VX[o.has_keyhole == 1], o.P[o.has_keyhole == 1], s=14, marker="x", color=GRAY, label="OLD Keyhole in NEW P–LS range")
    ax[1].scatter(o.VX[o.has_keyhole == 0], o.P[o.has_keyhole == 0], s=60, marker="*", color=INK, label="OLD non-Keyhole in range (2)")
    ax[1].axvline(0.899, color=MUTED, ls="--", lw=1)
    ax[1].set(xlabel="VX [m/s]", ylabel="P [W]", title="NEW boundary ≈ VX threshold (BA 0.92)")
    ax[1].legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "fig4_level_and_orientation_shift.png", dpi=200)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    fig_discovery()
    fig_metric_window()
    fig_rare_exhaustion()
    fig_level_shift()


if __name__ == "__main__":
    main()


def fig_synthetic():
    S = W13 / "synthetic"
    R = pd.read_csv(S / "constant_predictor_rank.csv")
    V = pd.read_csv(S / "metric_validity_spearman.csv")
    mets = [("q20_accuracy", "q20 accuracy"), ("full_accuracy", "full accuracy"), ("full_balanced_accuracy", "full BA"), ("BEF1", "BEF1")]
    fig, ax = plt.subplots(1, 2, figsize=(9.4, 3.4))
    cells = [("BAL", "BAL"), ("OLD", "OLD-like"), ("NEW", "NEW-like")]
    w = .2
    for k, (m, lab) in enumerate(mets):
        vals = [R[(R.scenario == c) & (R.metric == m)].fraction_of_AL_predictors_beaten_by_constant.mean() for c, _ in cells]
        vv = [V[(V.scenario == c) & (V.finite_metric == m) & (V.truth == "NSD_0.1")].spearman_AL_predictors.mean() for c, _ in cells]
        col = [GRAY, MUTED, BLUE, AQUA][k]
        x = np.arange(3) + (k - 1.5) * w
        ax[0].bar(x, vals, w * .9, color=col, label=lab)
        ax[1].bar(x, vv, w * .9, color=col, label=lab)
    for a in ax:
        a.set_xticks(np.arange(3), [l for _, l in cells])
        a.grid(axis="x", visible=False)
    ax[0].set(ylabel="share of AL predictors beaten", title="Constant-majority predictor beats AL predictors")
    ax[1].set(ylabel="Spearman ρ with true NSD₀.₁", title="Agreement with the true boundary (synthetic)")
    ax[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "fig5_synthetic_metric_validity.png", dpi=200)

    H = pd.read_csv(S / "headroom.csv")
    h = H[H.metric.eq("NSD_0.1")]
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    for mdl, c, lab in (("G", BLUE, "generic GPC (G)"), ("P", ORANGE, "physics mean + capped GP (P)")):
        g = h[h.model.eq(mdl)]
        ax.scatter(g.random_AULC, g.margin_gain, s=34, color=c, label=lab, edgecolor="white", linewidth=.5)
    ax.set(xlabel="random-acquisition NSD AULC (predictive quality without acquisition)", ylabel="margin − random NSD AULC",
           title="Better predictor ⇒ less acquisition headroom (24 cells)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig6_synthetic_model_vs_acquisition.png", dpi=200)

    T = pd.read_csv(W13 / "synthetic_transfer/transfer_results.csv")
    fig, axs = plt.subplots(1, 2, figsize=(9.4, 3.6))
    for ax, col, ylab in ((axs[0], "NSD_0.1", "true-boundary NSD₀.₁ in NEW region"), (axs[1], "balanced_accuracy", "NEW balanced accuracy (136 cases)")):
        m = T.groupby(["amp", "model"])[col].agg(["mean", "std"]).reset_index()
        for mdl, c, lab in (("H_physics_only", GRAY, "H physics only"), ("M3_capped", ORANGE, "M3 analogue (σ² ≤ 1)"),
                            ("M3_uncapped", AQUA, "M3 analogue (σ² ≤ 1000)"), ("G3_generic", BLUE, "G3 analogue (zero mean)")):
            g = m[m.model.eq(mdl)]
            ax.errorbar(g.amp, g["mean"], yerr=g["std"] / np.sqrt(20), color=c, label=lab, marker="o", ms=5, capsize=2)
        ax.set(xlabel="local deviation of the physics law in the NEW corner, A", ylabel=ylab)
    axs[0].set_title("Synthetic OLD→NEW transfer (all OLD labels, 20 reps)")
    axs[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "fig7_synthetic_transfer.png", dpi=200)


if __name__ == "__main__":
    fig_synthetic()
