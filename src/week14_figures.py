"""Week 14 figures."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
W = ROOT / "outputs/week14_research_program"
FIG = W / "figures"
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GRAY, INK, MUTED = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#8a8984", "#0b0b0b", "#52514e"
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True,
                     "grid.color": "#e6e5e0", "grid.linewidth": .6, "lines.linewidth": 2, "legend.frameon": False})
STRAT = {"RAND": (GRAY, "random"), "MAXI": (BLUE, "maximin"), "FRONT": (ORANGE, "Pareto front (order)"),
         "SCORE": (AQUA, "physics-score extremes"), "HEDGE": (MAGENTA, "hedge maximin+front+score")}


def fig_discovery_dimension():
    df = pd.read_parquet(W / "synthetic/discovery/discovery_confirm.parquet")
    fams = [("heldout_mono_curved", "monotone held-out family"), ("heldout_branin", "Branin (non-monotone)"),
            ("heldout_twoislands_skew", "two islands (non-monotone)")]
    fig, ax = plt.subplots(1, 3, figsize=(10.5, 3.3), sharey=True)
    for a, (f, t) in zip(ax, fams):
        g = df[df.family == f].groupby(["d", "strategy"]).T_both.mean().unstack()
        for s, (c, lab) in STRAT.items():
            a.plot(g.index, g[s], marker="o", ms=4, color=c, label=lab)
        a.set_title(t); a.set_xlabel("input dimension d"); a.set_xticks([2, 4, 6])
    ax[0].set_ylabel("mean queries until both classes seen")
    ax[0].legend(fontsize=7)
    fig.suptitle("Held-out discovery benchmark (frozen protocol, 100 reps per cell): the order certificate is dimension-free when its assumption holds", fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / "fig1_discovery_by_dimension.png", dpi=200)


def fig_discovery_real():
    d = pd.read_csv(W / "real_data/real_discovery.csv")
    camps = [("OLD", "OLD-405 pools (historical)"), ("NEW", "NEW-136 pools (post-hoc)"),
             ("Masinelli_Ti64", "Masinelli Ti64, K = 1-3 (external)")]
    fig, ax = plt.subplots(1, 3, figsize=(10.5, 3.3), sharey=True)
    order = ["RAND", "MAXI", "FRONT", "SCORE", "HEDGE"]
    for a, (c, t) in zip(ax, camps):
        g = d[d.campaign == c]
        for i, s in enumerate(order):
            v = g[g.strategy == s].T_both.to_numpy()
            col = STRAT[s][0]
            a.plot([i, i], [np.quantile(v, .5), np.quantile(v, .9)], color=col, lw=6, solid_capstyle="round", alpha=.8)
            a.plot(i, v.max(), "v", color=col, ms=6)
            a.plot(i, v.mean(), "o", color="white", mec=col, ms=5)
        a.axhline(16, color=MUTED, ls=":", lw=1)
        a.text(4.4, 16.6, "B16", color=MUTED, fontsize=7, ha="right")
        a.set_xticks(range(len(order)), [STRAT[s][1].split(" ")[0] for s in order], rotation=30)
        a.set_title(t)
    ax[0].set_ylabel("queries until both classes seen")
    fig.suptitle("bar: median to 90th percentile, ▼ maximum, ○ mean", fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "fig2_discovery_real_campaigns.png", dpi=200)


def fig_risk_asymmetry():
    C = pd.read_csv(W / "benchmarks/C2_paired_contrasts.csv")
    C = C[C.metric == "BA"]
    R = pd.read_csv(W / "real_data/real_models.csv")
    R = R[R.ok]
    real = []
    for st, g in R.groupby("setting"):
        m = g.groupby("model").BA.mean()
        for mdl in ("M3", "H", "G3S", "G3C"):
            real.append({"setting": st, "model": mdl, "delta": m[mdl] - m["G3"]})
    real = pd.DataFrame(real)
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    cols = {"M3": ORANGE, "H": GRAY, "G3S": AQUA, "G3C": BLUE}
    labels = {"M3": "physics as level (M3)", "H": "physics only (H)", "G3S": "physics as feature", "G3C": "physics as order (closure)"}
    for i, mdl in enumerate(("H", "M3", "G3S", "G3C")):
        syn = C[C.contrast == f"{mdl}-G3"]["mean"].to_numpy()
        rv = real[real.model == mdl].delta.to_numpy()
        ax.scatter(np.full(len(syn), i - .12) + np.random.default_rng(i).uniform(-.05, .05, len(syn)), syn, s=18, color=cols[mdl], alpha=.6, label=None)
        ax.scatter(np.full(len(rv), i + .12), rv, s=34, marker="D", color=cols[mdl], edgecolor=INK, linewidth=.5)
        ax.text(i, min(syn.min(), rv.min()) - .025, f"worst {min(syn.min(), rv.min()):+.3f}", ha="center", fontsize=7, color=MUTED)
    ax.axhline(0, color=MUTED, lw=1)
    ax.set_xticks(range(4), [labels[m] for m in ("H", "M3", "G3S", "G3C")], fontsize=8)
    ax.set_ylabel("balanced accuracy minus generic G3")
    ax.set_title("Risk asymmetry: ● held-out synthetic cells (12), ◆ real settings (OLD, NEW, Masinelli)", fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / "fig3_physics_risk_asymmetry.png", dpi=200)


def fig_metrics():
    S = pd.read_csv(W / "benchmarks/metrics_confirm/density_sensitivity.csv")
    s = S.groupby(["d", "shape"])[["q20_accuracy", "full_BA", "gabriel_BER", "gabriel_wBER", "gabriel_BEF1", "gabriel_wBEF1", "NSD"]].mean()
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    cols = [("q20_accuracy", GRAY, "q20 accuracy"), ("full_BA", MUTED, "full BA"), ("gabriel_BER", ORANGE, "Gabriel BER"),
            ("gabriel_wBER", BLUE, "Gabriel wBER (length-weighted)"), ("NSD", AQUA, "true NSD")]
    x = np.arange(len(s))
    for k, (c, col, lab) in enumerate(cols):
        ax.bar(x + (k - 2) * .16, s[c], .15, color=col, label=lab)
    ax.set_xticks(x, [f"{sh} d={d}" for d, sh in s.index])
    ax.set_ylabel("|score(error on side A) − score(error on side B)|")
    ax.set_title("Held-out metric benchmark: equal-geometry errors scored under side-concentrated densities", fontsize=9)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout(); fig.savefig(FIG / "fig4_metric_density_sensitivity.png", dpi=200)


def fig_headroom():
    h = pd.read_csv(W / "synthetic/headroom/headroom_oracle.csv")
    o = pd.read_csv(W / "synthetic/headroom/headroom_oracle_nsd.csv")
    mech = pd.read_csv(W / "synthetic/headroom/headroom_mechanism.csv")
    fig, ax = plt.subplots(1, 4, figsize=(11, 3.2))
    for a, scn in zip(ax[:3], ("BAL", "OLD", "NEW")):
        g = h[(h.scenario == scn) & (h.rep < 6)]
        for pol, col, lab in (("random", GRAY, "random"), ("margin", BLUE, "margin"), ("oracle", ORANGE, "oracle on finite-pool BA")):
            v = g[g.policy == pol].groupby("budget")["NSD_0.1"].mean()
            a.plot(v.index, v.values, color=col, label=lab)
        v = o[o.scenario == scn].groupby("budget")["NSD_0.1"].mean()
        a.plot(v.index, v.values, color=AQUA, label="oracle on true NSD")
        a.set_title(f"{scn}-like"); a.set_xlabel("budget"); a.set_ylim(.5, 1)
    ax[0].set_ylabel("true-boundary NSD₀.₁"); ax[0].legend(fontsize=7)
    m = mech.groupby(["scenario", "policy"]).frac_acquired_with_flipped_label.mean().unstack()
    xx = np.arange(3)
    ax[3].bar(xx - .18, m.loc[["BAL", "OLD", "NEW"], "margin"], .35, color=BLUE, label="margin")
    ax[3].bar(xx + .18, m.loc[["BAL", "OLD", "NEW"], "oracle_NSD"], .35, color=AQUA, label="NSD oracle")
    ax[3].set_xticks(xx, ["BAL", "OLD", "NEW"]); ax[3].set_title("acquired labels that are flipped")
    ax[3].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "fig5_headroom_identifiability.png", dpi=200)


def fig_new_violations():
    new = pd.read_csv(ROOT / "outputs/week12_startup_and_transfer_development/audit/new136.csv")
    from src.week14_order import SIGNS_O3, dominance
    from src.week14_real_checks import to_log
    u = to_log(new[["P", "VX", "LS", "ST"]].to_numpy()); y = new.has_keyhole.to_numpy()
    D = dominance(u, SIGNS_O3)
    V = D & (y[:, None] == 1) & (y[None, :] == 0)
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    ax.scatter(new.VX[y == 1], new.P[y == 1], s=14, color=BLUE, alpha=.6, label="Keyhole")
    rare = np.nonzero(y == 0)[0]
    nv = V.sum(0)[rare]
    ax.scatter(new.VX[rare], new.P[rare], s=30 + 3 * nv, marker="^", color=ORANGE, edgecolor=INK, linewidth=.4, label="non-Keyhole (size ∝ violations)")
    a = rare[np.argmax(nv)]
    ax.annotate(f"{nv.max()} of {int(V.sum())} order violations", (new.VX[a], new.P[a]), xytext=(.45, 445), fontsize=8,
                arrowprops=dict(arrowstyle="->", color=MUTED))
    ax.set(xlabel="VX [m/s]", ylabel="P [W]", title="NEW-136: monotone order (P↑, VX↓, LS↓) and its violations")
    ax.legend(fontsize=7, loc="lower left")
    fig.tight_layout(); fig.savefig(FIG / "fig6_new_order_violations.png", dpi=200)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    fig_discovery_dimension(); fig_discovery_real(); fig_risk_asymmetry(); fig_metrics(); fig_headroom(); fig_new_violations()


if __name__ == "__main__":
    main()
