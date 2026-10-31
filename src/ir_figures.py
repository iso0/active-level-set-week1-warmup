"""IR figures (parts A, B, C, F) from the saved result files; no new computation of any registered number.
Colours: Okabe-Ito (colour-blind safe); conduction blue, Keyhole vermillion.
    python -m src.ir_figures
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import src.ir_data as IRD  # noqa: E402

OUT = IRD.OUT / "figures"
CB, CK, GREY = "#0072B2", "#D55E00", "#6b6b6b"
QC = {"W": "#009E73", "KE": "#E69F00", "T": "#CC79A7"}
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})


def fig_q1():
    A1 = pd.read_csv(IRD.OUT / "descriptive" / "A1_spearman_with_depth.csv"); A2 = pd.read_csv(IRD.OUT / "descriptive" / "A2_beyond_inputs.csv").set_index("var")
    allv = A1[A1.subset == "all"].set_index("var").sort_values("rho"); vs = list(allv.index); y = np.arange(len(vs))
    fig, ax = plt.subplots(1, 2, figsize=(11, 5.2), sharey=True, gridspec_kw={"width_ratios": [1.4, 1]})
    ax[0].barh(y, allv.rho, color="#c9d6df", edgecolor="none", label="all runs (95 % bootstrap CI)")
    ax[0].errorbar(allv.rho, y, xerr=[allv.rho - allv.lo95, allv.hi95 - allv.rho], fmt="none", ecolor="#333", lw=1)
    for sub, c, mk in (("conduction", CB, "o"), ("keyhole", CK, "s")):
        s = A1[A1.subset == sub].set_index("var").reindex(vs); ax[0].scatter(s.rho, y, color=c, marker=mk, s=22, zorder=3, label=f"{sub} runs only")
    ax[0].set_yticks(y); ax[0].set_yticklabels([allv.label[v] for v in vs]); ax[0].axvline(0, color="#999", lw=0.8)
    ax[0].set_xlabel("Spearman correlation with log melt-pool depth"); ax[0].set_title("Raw association with depth", loc="left")
    ax[0].legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0.0, -0.11), ncol=3)
    gp = A2.reindex(vs)["gp_oof_resid_pearson"]; lin = A2.reindex(vs)["partial_rank_given_4_log_inputs"]
    ax[1].barh(y, gp.fillna(0), color="#7f7f7f", label="GP out-of-fold residuals"); ax[1].scatter(lin, y, color="#000", marker="|", s=80, label="linear in 4 log inputs (ranks)")
    ax[1].axvline(0, color="#999", lw=0.8); ax[1].set_xlim(-0.6, 1.0); ax[1].set_xlabel("correlation after removing the inputs"); ax[1].set_title("What is left once the inputs are known", loc="left")
    ax[1].legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0.0, -0.11), ncol=1)
    fig.tight_layout(); fig.savefig(OUT / "fig1_correlation_with_depth.png", bbox_inches="tight"); plt.close(fig)


def fig_q2():
    X = pd.read_csv(IRD.OUT / "descriptive" / "analysis_table.csv", index_col=0); R = json.loads((IRD.OUT / "descriptive" / "PART_A_RESULTS.json").read_text(encoding="utf-8"))["A3"]
    g = (~X.short.astype(bool)) & X.D.notna() & X.W_A.notna(); W, D, yv = np.exp(X.W_A[g]), np.exp(X.D[g]), X.y[g]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
    for cls, c, lab in ((0, CB, "conduction"), (1, CK, "Keyhole")):
        m = yv == cls; ax[0].scatter(W[m], D[m], s=10, alpha=0.7, color=c, label=f"{lab} (n = {int(m.sum())})", edgecolor="none")
    ww = np.linspace(W.min() * 0.95, W.max() * 1.05, 50); ax[0].plot(ww, ww / 2, color="#222", lw=1.2, ls="--", label="D = W/2 (W/D = 2)")
    Ex = json.loads((IRD.OUT / "extras" / "EXTRAS.json").read_text(encoding="utf-8")); cc = Ex["E2_ceiling_counts"]; sb = Ex["E2_theil_sen_keyhole_below_ceiling"]
    ax[0].axhline(295, color=CK, lw=0.8, ls=":"); ax[0].text(W.min() * 0.97, 268, f"~300 µm ceiling: {cc['keyhole_at_ceiling']}/{cc['keyhole_total']} Keyhole runs", color=CK, fontsize=7)
    ax[0].set_xscale("log"); ax[0].set_yscale("log"); ax[0].set_xlabel("melt-pool width W (µm, active-window max)"); ax[0].set_ylabel("melt-pool depth D (µm, active-window max)")
    sc, sk = R["theil_sen_logA_on_logW_conduction"], R["theil_sen_logA_on_logW_keyhole"]
    ax[0].set_title(f"log-log slope: conduction {sc['slope']:.2f}; Keyhole {sk['slope']:.2f} (below ceiling {sb['slope']:.2f}, CI {sb['lo95']:.2f} to {sb['hi95']:.2f})", loc="left", fontsize=8.5)
    ax[0].legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0.0, 0.93))
    ar = (D / W).to_numpy(); bins = np.linspace(0, 2.0, 41)
    ax[1].hist(ar[yv.to_numpy() == 0], bins=bins, color=CB, alpha=0.75, label="conduction"); ax[1].hist(ar[yv.to_numpy() == 1], bins=bins, color=CK, alpha=0.75, label="Keyhole")
    ba = {1.5: R["criterion_W_over_D_le_1.5"]["BA"], 2.0: R["criterion_W_over_D_le_2.0"]["BA"], 2.5: R["criterion_W_over_D_le_2.5"]["BA"], 2.75: Ex["E1_criterion_W_over_D_le_2.75"]["BA"]}
    for c, ls, col in ((1.5, ":", "#222"), (2.0, "--", "#222"), (2.5, "-.", "#222"), (2.75, "-", "#9a9a9a")):
        ax[1].axvline(1 / c, color=col, lw=1, ls=ls, label=f"W/D = {c}: BA {ba[c]:.3f}" + (" (extra)" if c == 2.75 else ""))
    ax[1].set_xlabel("aspect ratio D/W"); ax[1].set_ylabel("runs"); ax[1].set_title("Aspect ratio by regime and literature thresholds", loc="left"); ax[1].legend(frameon=False, fontsize=7)
    fig.tight_layout(); fig.savefig(OUT / "fig2_width_vs_depth.png"); plt.close(fig)


def fig_a4():
    import src.ir_desc as DS
    A4 = pd.read_csv(IRD.OUT / "descriptive" / "A4_label_information.csv"); T = A4[A4.set.str.startswith("[h, D, ")].copy(); T["x"] = T.set.str.replace("[h, D, ", "", regex=False).str.rstrip("]")
    T["x"] = T.x.map(lambda s: DS.VARS.get(s, s).replace("log ", "") if s in DS.VARS else s)
    T = T.sort_values("d_logloss_vs_hD"); y = np.arange(len(T))
    fig, ax = plt.subplots(1, 2, figsize=(10, 4.8), sharey=True)
    ax[0].errorbar(T.d_logloss_vs_hD, y, xerr=[T.d_logloss_vs_hD - T.d_logloss_lo95, T.d_logloss_hi95 - T.d_logloss_vs_hD], fmt="o", color="#333", ms=4)
    ax[0].axvline(0, color="#999", lw=0.8); ax[0].set_yticks(y); ax[0].set_yticklabels(T.x); ax[0].set_xlabel("change in CV log loss vs [h, depth] (lower = better)")
    ax[0].set_title("Adding a TRUE physical output to h + depth", loc="left")
    ax[1].errorbar(T.d_BA_vs_hD, y, xerr=[T.d_BA_vs_hD - T.d_BA_lo95, T.d_BA_hi95 - T.d_BA_vs_hD], fmt="o", color="#333", ms=4); ax[1].axvline(0, color="#999", lw=0.8)
    ax[1].set_xlabel("change in CV balanced accuracy (higher = better)")
    fig.tight_layout(); fig.savefig(OUT / "fig3_label_information_beyond_depth.png"); plt.close(fig)


def fig_screen():
    f = IRD.OUT / "screen" / "screen_rows.csv.gz"
    if not f.exists():
        return
    R = pd.read_csv(f); S = R[R.condition == "STD"]; base = S[S.model == "R0"].set_index(["cluster", "learner", "budget"])
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
    for m in sorted(S.model.unique()):
        if m == "R0":
            continue
        a = S[S.model == m].set_index(["cluster", "learner", "budget"]); d = (a.proxyBA - base.proxyBA).dropna(); dr = ((a.rmse_q20 - base.rmse_q20) / base.rmse_q20).dropna()
        cur = d.groupby(level=[0, 2]).mean().groupby(level=1).mean(); curr = dr.groupby(level=[0, 2]).mean().groupby(level=1).mean()
        q = m.split("_")[-1]; col = QC.get(q, GREY) if not m.startswith(("SUM2", "ICM")) else GREY
        ls = "-" if m.startswith("LMC") else "--" if m.startswith("CHAIN") else ":" if m.startswith("ORACLE") else "-."
        lw = 1.8 if m.startswith(("LMC", "CHAIN")) else 1.2
        ax[0].plot(cur.index, cur.values, ls=ls, color=col, lw=lw, marker="o", ms=3, label=m); ax[1].plot(curr.index, 100 * curr.values, ls=ls, color=col, lw=lw, marker="o", ms=3, label=m)
    ax[0].axhline(0, color="#999", lw=0.8); ax[0].axhline(0.005, color="#222", lw=0.8, ls=(0, (4, 4))); ax[0].set_ylim(-0.011, 0.0068); ax[0].text(40, 0.0054, "carry threshold +0.005 (S1)", fontsize=7)
    ax[0].set_xlabel("budget (opened simulations)"); ax[0].set_ylabel("proxy BA difference vs C1 depth model"); ax[0].set_title("STD: does the co-output help label accuracy?", loc="left")
    ax[1].axhline(0, color="#999", lw=0.8); ax[1].axhline(-3, color="#222", lw=0.8, ls=(0, (4, 4))); ax[1].set_xlabel("budget (opened simulations)"); ax[1].set_ylabel("q20 depth RMSE change vs C1 (%)")
    ax[1].set_title("STD: depth error near the boundary", loc="left"); ax[1].legend(frameon=False, fontsize=7, ncol=2)
    fig.tight_layout(); fig.savefig(OUT / "fig4_method_screen.png"); plt.close(fig)


def fig_learn():
    f = IRD.OUT / "screen" / "partB_learnability_STD.csv"
    if not f.exists():
        return
    B = pd.read_csv(f); lab = {"D": "depth (C1 model)", "W": "width", "KE": "kinetic energy", "T": "max temperature", "SPK": "velocity spike ratio", "LAS": "laser power",
                               "ETOT": "total energy", "NPART": "melt particles"}
    fig, ax = plt.subplots(figsize=(6.4, 4.2)); cols = {"D": "#000", "W": QC["W"], "KE": QC["KE"], "T": QC["T"], "SPK": "#56B4E9", "LAS": "#999999", "ETOT": "#8c564b", "NPART": "#bcbd22"}
    for q, g in B.groupby("output"):
        g = g.sort_values("budget"); ax.plot(g.budget, g.R2_median, marker="o", ms=3, lw=2.2 if q == "D" else 1.3, color=cols.get(q, GREY), label=lab.get(q, q))
    ax.axhline(0.8, color="#999", lw=0.8, ls="--"); ax.set_ylim(-0.2, 1.0); ax.set_xlabel("budget (opened simulations)"); ax.set_ylabel("median test R² (STD learner-paths)")
    ax.set_title("How fast each output is learned from the inputs", loc="left"); ax.legend(frameon=False, fontsize=7, ncol=2)
    fig.tight_layout(); fig.savefig(OUT / "fig5_learnability.png"); plt.close(fig)


def fig_events():
    f = IRD.TEMP / "PART_F_RESULTS.json"
    if not f.exists():
        return
    C = json.loads(f.read_text(encoding="utf-8"))["curves"]
    show = [("D", "depth", "#000"), ("T", "max temperature", QC["T"]), ("LASER", "absorbed laser power", "#8c564b"), ("W", "width", QC["W"]), ("V", "max velocity", "#56B4E9"), ("KE", "kinetic energy", QC["KE"])]
    E = np.load(IRD.TEMP / "F3_event_windows.npz"); sid = E["sim_ids"].astype(str); lag = E["lag_us"]
    A = pd.read_csv(IRD.OUT / "descriptive" / "analysis_table.csv", index_col=0).D.reindex(sid); below = (np.exp(A) < 295.0).to_numpy()
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True); rng = np.random.default_rng(31)
    for k, lab, col in show:
        if k in C:
            c = C[k]; d = np.array(c["K_mean"]) - np.array(c["control_mean"])
            ax[0].plot(lag, d, color=col, lw=1.8 if k == "D" else 1.2, label=lab); ax[0].fill_between(lag, c["diff_lo95"], c["diff_hi95"], color=col, alpha=0.12, lw=0)
        if f"K_{k}" in E.files:
            dd = (np.asarray(E[f"K_{k}"], float) - np.asarray(E[f"C_{k}"], float))[below]; m = np.nanmean(dd, 0)
            bs = np.array([np.nanmean(dd[rng.integers(0, len(dd), len(dd))], 0) for _ in range(500)])
            ax[1].plot(lag, m, color=col, lw=1.8 if k == "D" else 1.2, label=lab); ax[1].fill_between(lag, np.nanpercentile(bs, 2.5, 0), np.nanpercentile(bs, 97.5, 0), color=col, alpha=0.12, lw=0)
    for a in ax:
        a.axvline(0, color="#222", lw=0.8); a.axhline(0, color="#999", lw=0.8); a.set_xlabel("time relative to the first Keyhole frame (µs)")
    ax[0].set_ylabel("z-score: Keyhole-aligned minus random-time control")
    ax[0].set_title(f"All Keyhole runs (n = {len(sid)}; registered F3)", loc="left", fontsize=9.5)
    ax[1].set_title(f"Keyhole runs below the ~300 µm ceiling (n = {int(below.sum())}; extra)", loc="left", fontsize=9.5); ax[1].legend(frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout(); fig.savefig(OUT / "fig6_keyhole_onset.png"); plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in (fig_q1, fig_q2, fig_a4, fig_screen, fig_learn, fig_events):
        f(); print("ok", f.__name__, flush=True)


if __name__ == "__main__":
    main()
