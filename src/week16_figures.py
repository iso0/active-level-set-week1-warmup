"""Week 16 figures (outputs/week16_theory_meets_data/figures)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.week16_astra import E_T, first_hit_survival, p_T_greater

W = Path(__file__).resolve().parents[1] / "outputs/week16_theory_meets_data"
FIG = W / "figures"
COL = {"dev": "#0072B2", "curvedMono": "#E69F00", "rough": "#009E73", "branin4d": "#CC79A7", "gpworld": "#56B4E9"}
FAMS = ("dev", "curvedMono", "rough", "branin4d", "gpworld")
LABEL = {"dev": "development (Week 13)", "curvedMono": "curvedMono", "rough": "rough", "branin4d": "branin4d", "gpworld": "gpworld (corrected fit)"}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": .25})


def fig_validation():
    v = pd.read_csv(W / "validation/peer_validation.csv")
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.2))
    x = np.arange(len(v))
    ax[0].bar(x, v.spearman_peer_vsur.fillna(0), color="#0072B2")
    ax[0].axhline(0, color="k", lw=.8)
    ax[0].set(title="PEER vs VSUR refit look-ahead (per state)", ylabel="Spearman over candidates", xlabel="validation state", ylim=(-1, 1))
    ax[1].bar(x, v.martingale_gap_median, color="#D55E00")
    ax[1].set(title="Refit look-ahead martingale gap", ylabel=r"median $\sum_i |E_y q_i' - q_i|$ (400 targets)", xlabel="validation state")
    fig.text(.5, -.02, f"PEER vs Monte Carlo from the same posterior: Pearson min {v.mc_pearson.min():.3f} over {v.mc_pearson.notna().sum()} states",
             ha="center", fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "fig1_peer_validation.png", dpi=170, bbox_inches="tight"); plt.close(fig)


def fig_rmodel(S):
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
    for f in FAMS:
        h = S[(S.family == f) & ~S.saturated_ref].r_model_ref.sort_values()
        if len(h):
            ax[0].step(h.values, np.arange(1, len(h) + 1) / len(h), where="post", color=COL[f], label=f"{LABEL[f]} (n={len(h)})")
    ax[0].axvline(.8, color="k", ls=":", lw=1); ax[0].text(.81, .05, "P1 threshold", fontsize=7)
    ax[0].set(xlabel="r_model = V_model(margin) / max V_model (reference cloud)", ylabel="ECDF over states", title="Margin's value under its own model")
    ax[0].legend(fontsize=7, loc="upper left")
    g = S[~S.saturated_ref].groupby(["family", "budget"]).r_model_ref.median().unstack(0)
    for f in FAMS:
        if f in g:
            ax[1].plot(g.index, g[f], "o-", color=COL[f], ms=4, label=LABEL[f])
    ax[1].set(xlabel="budget", ylabel="median r_model", title="by budget", ylim=(0, 1))
    fig.tight_layout(); fig.savefig(FIG / "fig2_r_model.png", dpi=170); plt.close(fig)


def fig_headroom(S):
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
    for k, (vt, name, scale) in enumerate((("Vt_ham_ref", "Hamming, ref. cloud (points of 400)", 400), ("Vt_nsd", "NSD τ = 0.1 (×100)", 100))):
        H = S.groupby("family")[f"H|Vref|{vt}"].mean().reindex(FAMS) * scale
        A = S.groupby("family")[f"A|Vref|{vt}"].mean().reindex(FAMS) * scale
        x = np.arange(len(FAMS))
        ax[k].bar(x - .2, H, .4, color="#999999", label="H = max V_true − V_true(margin)")
        ax[k].bar(x + .2, A, .4, color=[COL[f] for f in FAMS], label="A = V_true(argmax PEER) − V_true(margin)")
        ax[k].axhline(0, color="k", lw=.8)
        ax[k].set_xticks(x, [f if f != "curvedMono" else "curved" for f in FAMS], fontsize=8)
        ax[k].set(title=f"One-step oracle headroom — {name}", ylabel="mean per state")
        ax[k].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "fig3_headroom_split.png", dpi=170); plt.close(fig)


def fig_decoys(S, D):
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.4))
    ns = S[~S.saturated_ref].copy(); ns["decoy"] = ns.r_model_ref < .5
    data = [ns[ns.decoy].margin_abs_latent.values, ns[~ns.decoy].margin_abs_latent.values]
    axs[0].boxplot(data, tick_labels=["decoy picks\n(r_model < 0.5)", "other margin picks"], showfliers=False)
    axs[0].set(ylabel="|true latent| at the margin pick", title="Decoys sit near the true boundary")
    sd = pd.read_csv(W / "headroom/decoy_sd.csv"); sd["decoy"] = sd.r_model_ref < .5
    sd = sd[sd.family.isin(("dev", "curvedMono", "rough"))]
    axs[1].boxplot([sd[sd.decoy].s_margin, sd[~sd.decoy].s_margin, sd.s_argmax],
                   tick_labels=["decoy\nmargin picks", "other\nmargin picks", "PEER\nargmax"], showfliers=False)
    axs[1].set(ylabel="posterior latent sd at the pick", title="…with a pinned latent (physics-like)")
    ax = [None, axs[2]]
    vs =("mean_base", "mean_zero", "mean_ml2", "mean_physics")
    share = D.groupby(["family", "variant"]).r_model_ref.apply(lambda x: (x.dropna() < .5).mean()).unstack()
    share = share.reindex(columns=[v for v in vs if v in share.columns]).reindex(FAMS)
    x = np.arange(len(FAMS)); w = .8 / share.shape[1]
    pal = {"mean_base": "#0072B2", "mean_zero": "#56B4E9", "mean_ml2": "#E69F00", "mean_physics": "#009E73"}
    for i, v in enumerate(share.columns):
        ax[1].bar(x + (i - (share.shape[1] - 1) / 2) * w, share[v], w, color=pal[v], label=v.replace("mean_", "mean: "))
    ax[1].set_xticks(x, [f if f != "curvedMono" else "curved" for f in FAMS], fontsize=8)
    ax[1].set(ylabel="decoy share", title="Decoy share by prior-mean rule", ylim=(0, 1)); ax[1].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "fig4_decoys.png", dpi=170); plt.close(fig)


def fig_calibration():
    p = W / "calibration/within_cell_spearman.csv"
    if not p.exists():
        return
    P = pd.read_csv(p)
    cols = [("rho_LL_NSD", "marginal\nlog loss"), ("rho_Brier_NSD", "marginal\nBrier"), ("rho_JLL_near_NSD", "joint near-pair\nlog loss"),
            ("rho_DE_near_NSD", "dependence\nexcess (near)"), ("rho_JLL_rand_NSD", "joint random-pair\nlog loss")]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.boxplot([P[c].dropna() for c, _ in cols], tick_labels=[l for _, l in cols], showfliers=True)
    ax.axhline(0, color="k", lw=.8)
    ax.set(ylabel="Spearman(−score, NSD AULC)", title="Within-cell rank agreement with margin NSD AULC (one point per cell)")
    fig.tight_layout(); fig.savefig(FIG / "fig5_calibration.png", dpi=170); plt.close(fig)


def fig_discovery():
    E = pd.read_csv(W / "discovery/tail_enrichment.csv")
    d = pd.read_csv(Path(__file__).resolve().parents[1] / "outputs/week12_startup_and_transfer_development/startup/benchmark/discovery_costs.csv")
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
    e = E[~E.whole_campaign]
    for camp, col in (("NEW", "#0072B2"), ("OLD", "#E69F00")):
        g = e[e.campaign == camp].groupby("M")[["tail_rate", "pool_rate"]].mean()
        ax[0].plot(g.index, g.tail_rate, "o-", color=col, label=f"{camp}: rare share in physics tail")
        ax[0].plot(g.index, g.pool_rate, "--", color=col, label=f"{camp}: rare share in pool (r/N)")
    ax[0].set(xlabel="tail size M", ylabel="rare-class share", title="Tail enrichment (eq. 11): s/M vs r/N", ylim=(0, 1.05)); ax[0].legend(fontsize=7)
    ks = np.arange(0, 50)
    pools = e[(e.campaign == "NEW") & (e.M == 5)][["N", "r"]].values
    exact = [np.mean([float(p_T_greater(k, int(N - r), int(r))) for N, r in pools]) for k in ks]
    ax[1].plot(ks, exact, "k-", lw=1.5, label="exact uniform law (eq. 9), mean over the 100 pools")
    for rule, col in (("uniform_random", "#999999"), ("maximin", "#0072B2"), ("adaptive_physics", "#009E73")):
        c = d[d.rule == rule].discovery_cost.values
        ax[1].step(ks, [(c > k).mean() for k in ks], where="post", color=col, label=f"Week 12 observed: {rule}")
    ax[1].set(xlabel="queries k", ylabel="P(T_both > k)", title="Discovery: exact law vs observed startups"); ax[1].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "fig6_discovery.png", dpi=170); plt.close(fig)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    S = pd.read_csv(W / "headroom/states.csv"); D = pd.read_csv(W / "headroom/decoy_variants.csv")
    fig_validation(); fig_rmodel(S); fig_headroom(S); fig_decoys(S, D); fig_calibration(); fig_discovery()


if __name__ == "__main__":
    main()
