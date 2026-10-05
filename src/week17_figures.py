"""Week 17 figures (outputs/week17_model_and_acquisition/figures)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

W = Path(__file__).resolve().parents[1] / "outputs/week17_model_and_acquisition"
FIG = W / "figures"
COL = {"G3": "#0072B2", "M3": "#D55E00", "LT": "#009E73", "M3_Cfree": "#E69F00", "H": "#999999", "M3_C": "#CC79A7", "M3_free": "#56B4E9", "H_C1": "#BBBBBB"}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": .25})


def fig_physics_mean():
    b = pd.read_csv(W / "phase1/physics_mean_by_budget.csv")
    a = pd.read_csv(W / "phase1/physics_mean_anatomy.csv.gz")
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.3))
    for st, col, lab in (("old_a0_prefix", "#D55E00", "OLD A0 prefixes"), ("new_al_prefix", "#0072B2", "NEW AL prefixes")):
        g = b[b.set == st]
        ax[0].plot(g.budget, g.separable, "o-", color=col, label=lab)
        ax[1].plot(g.budget, g.maxlat_med, "o-", color=col, label=lab)
    ax[0].set(xlabel="budget", ylabel="share of prefixes separable in log h", title="Separable revealed labels", ylim=(0, 1)); ax[0].legend(fontsize=7)
    ax[1].set(xlabel="budget", ylabel="median max |physics latent| (C = 1e6)", title="Saturated physics prior"); ax[1].axhline(5, color="k", ls=":", lw=1)
    g = a[a.set.isin(["new_al_prefix", "old_a0_prefix"])].groupby(["set", "C"]).test_logloss_H.mean().unstack(0)
    for st, col in (("old_a0_prefix", "#D55E00"), ("new_al_prefix", "#0072B2")):
        ax[2].plot(g.index, g[st], "o-", color=col, label=st.replace("_", " "))
    ax[2].set(xscale="log", xlabel="logistic regularization C", ylabel="test log loss of H", title="Overconfidence vanishes with shrinkage"); ax[2].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "fig1_physics_mean_saturation.png", dpi=170); plt.close(fig)


def fig_override_transfer():
    d = pd.read_csv(W / "phase1/diagnose_real.csv.gz", usecols=lambda c: not c.startswith("pred_"))
    m = d[d.model.str.startswith("M3") & d.set.isin(["new_al", "new_cv"])]
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.4))
    order = ["M3", "M3_C", "M3_free", "M3_Cfree"]
    ov = m.groupby("model")[["override_rate", "needed_override_rate"]].mean().reindex(order)
    x = np.arange(len(order))
    ax[0].bar(x - .2, ov.needed_override_rate, .4, color="#999999", label="truth contradicts physics sign")
    ax[0].bar(x + .2, ov.override_rate, .4, color=[COL[k] for k in order], label="model overrides physics sign")
    ax[0].set_xticks(x, ["M3 (C=1e6, cap)", "C=1, cap", "C=1e6, free", "C=1, free"], fontsize=8)
    ax[0].set(ylabel="share of NEW test rows", title="Can the discrepancy override the physics mean?"); ax[0].legend(fontsize=7)
    R = pd.read_csv(W / "phase1/transfer_decomposition.csv")
    mods = ["G3", "LT", "M3_Cfree", "M3", "H"]
    t = R.pivot_table(index="model", columns="step", values="BA").reindex(mods)
    for i, (step, lab) in enumerate((("raw", "as transferred"), ("prior", "+ prevalence (label-shift) correction"), ("intercept", "+ ORACLE intercept"))):
        ax[1].bar(np.arange(len(mods)) + (i - 1) * .27, t[step], .27, label=lab, color=["#0072B2", "#999999", "#009E73"][i])
    ax[1].set_xticks(np.arange(len(mods)), mods); ax[1].set(ylabel="NEW balanced accuracy", ylim=(.4, .75), title="Strict OLD→NEW transfer: level, not label shift"); ax[1].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "fig2_override_and_transfer.png", dpi=170); plt.close(fig)


def fig_heldout():
    p = W / "heldout/heldout_results.csv.gz"
    if not p.exists():
        return
    df = pd.read_csv(p); a = df[df.kind == "aulc"]
    w = a.pivot_table(index=["cell", "rep"], columns=["model", "rule"], values="NSD_0.1_AULC")
    cells = sorted(a.cell.unique()); short = [c.split("_", 1)[0] for c in cells]
    fig, ax = plt.subplots(1, 2, figsize=(12, 3.6))
    for i, m in enumerate(("LT", "M3_Cfree", "M3")):
        d = (w[(m, "margin")] - w[("G3", "margin")]).groupby(level=0).mean().reindex(cells)
        ax[0].bar(np.arange(len(cells)) + (i - 1) * .27, d, .27, color=COL[m], label=f"{m} − G3")
    ax[0].axhline(0, color="k", lw=.8); ax[0].set_xticks(np.arange(len(cells)), short, fontsize=7)
    ax[0].set(ylabel="Δ NSD AULC (margin)", title="Held-out worlds: model effect under margin"); ax[0].legend(fontsize=7)
    for i, m in enumerate(("G3", "M3", "LT", "M3_Cfree")):
        for j, (rule, mk) in enumerate((("peer", "v"), ("coverage", "o"), ("random", "x"))):
            d = (w[(m, rule)] - w[(m, "margin")]).groupby(level=0).mean().mean()
            ax[1].scatter(i + (j - 1) * .2, d, marker=mk, color=COL[m], s=40, label=rule if i == 0 else None)
    ax[1].axhline(0, color="k", lw=.8); ax[1].set_xticks(range(4), ["G3", "M3", "LT", "M3_Cfree"])
    ax[1].set(ylabel="rule − margin, mean NSD AULC over cells", title="Acquisition rules under each model"); ax[1].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "fig3_heldout_models_and_rules.png", dpi=170); plt.close(fig)
    o = df[df.kind == "oracle"]
    g = o.groupby("model")[["margin_nsd", "peer_nsd", "rand_nsd", "max_nsd"]].mean().reindex(["G3", "M3", "LT", "M3_Cfree"])
    fig, ax = plt.subplots(figsize=(7, 3.3))
    x = np.arange(len(g))
    for i, (k, lab, c) in enumerate((("max_nsd", "best candidate (truth oracle)", "#999999"), ("margin_nsd", "margin pick", "#0072B2"),
                                     ("peer_nsd", "PEER pick", "#D55E00"), ("rand_nsd", "random candidate", "#BBBBBB"))):
        ax.bar(x + (i - 1.5) * .2, g[k] * 100, .2, color=c, label=lab)
    ax.set_xticks(x, g.index); ax.axhline(0, color="k", lw=.8)
    ax.set(ylabel="one-step true NSD gain (×100)", title="Oracle headroom at B24/B48 (held-out, margin paths)"); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "fig4_oracle_headroom.png", dpi=170); plt.close(fig)


def fig_real():
    p = W / "real_al/real_al_aulc_by_repeat.csv"
    if not p.exists():
        return
    au = pd.read_csv(p)
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.5))
    mods = ["G3", "M3", "LT", "M3_Cfree"]; rules = ["margin", "candB", "peer", "random"]
    for k, camp in enumerate(("NEW", "OLD")):
        g = au[au.campaign == camp].groupby(["model", "rule"]).BA_AULC.mean().unstack().reindex(index=mods, columns=rules)
        for j, r in enumerate(rules):
            ax[k].bar(np.arange(4) + (j - 1.5) * .2, g[r], .2, label=r, color=["#0072B2", "#E69F00", "#D55E00", "#999999"][j])
        lo = np.nanmin(g.values) - .03
        ax[k].set_xticks(range(4), mods); ax[k].set(ylabel="pooled BA AULC", ylim=(lo - .03, np.nanmax(g.values) + .01), title=f"{camp}: model × rule")
        ax[k].legend(fontsize=7, ncol=4, loc="lower center")
    fig.tight_layout(); fig.savefig(FIG / "fig5_real_al.png", dpi=170); plt.close(fig)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    fig_physics_mean(); fig_override_transfer(); fig_heldout(); fig_real()


if __name__ == "__main__":
    main()
