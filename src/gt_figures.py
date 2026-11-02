"""GT figures from the saved result files (no new registered number). Okabe-Ito colours; conduction blue, Keyhole vermillion.
    python -m src.gt_figures
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import src.el_eval as EV  # noqa: E402
import src.gt_data as GD  # noqa: E402
import src.rc19_pool as P  # noqa: E402

OUT = GD.OUT / "figures"
CB, CK, GREY = "#0072B2", "#D55E00", "#6b6b6b"
COL = {"C1": "#000000", "C1_own": "#000000", "GEO_A1": "#E69F00", "GEO_A2": "#F0E442", "GEO_B1": "#009E73", "GEO_B2": "#56B4E9", "GEO_B3": "#CC79A7",
       "CAL_B1": "#0072B2", "C1_G": "#D55E00", "C1_T": "#882255", "GEO_margin_own": "#009E73", "GEO_straddle_own": "#56B4E9", "GEO_space_own": "#CC79A7",
       "GEO_own": "#009E73", "GEO_on_C1": "#999999", "C1_on_GEO": "#555555"}
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})


def fig_definitions():
    M = P.manifest(); R = GD.runs().reindex(M.index); y = M.y.to_numpy(int)
    fig, ax = plt.subplots(1, 3, figsize=(13, 4.2))
    r1 = R.A_um / R.W_A_um; r3 = R.R3inst
    for c, col, lab in ((0, CB, "conduction"), (1, CK, "Keyhole")):
        m = y == c; ax[0].scatter(r1[m], r3[m], s=8, color=col, alpha=0.6, label=lab)
    ax[0].plot([0.1, 2.5], [0.1, 2.5], color=GREY, lw=0.8); ax[0].axvline(0.5, color=GREY, ls=":", lw=0.8); ax[0].axhline(0.5, color=GREY, ls=":", lw=0.8)
    ax[0].set_xscale("log"); ax[0].set_yscale("log"); ax[0].set_xlabel("A / W_A (maxima, not simultaneous)"); ax[0].set_ylabel("max d(t)/w(t) (simultaneous)")
    ax[0].set_title("Ratio definitions (dotted: d/w = 1/2)", loc="left"); ax[0].legend(frameon=False, fontsize=8)
    dt = (R.t_A_ms - R.t_WA_ms).abs().dropna(); ax[1].hist(dt, bins=40, color="#7f7f7f")
    ax[1].set_xlabel("|t(depth max) - t(width max)|  (ms)"); ax[1].set_ylabel("runs"); ax[1].set_title(f"The two maxima are {dt.median():.2f} ms apart (median)", loc="left")
    bd = R.beam_diameter_um; ax[2].scatter(bd, R.W_A_um, s=8, color="#009E73", alpha=0.6); lim = [40, 320]; ax[2].plot(lim, lim, color=GREY, lw=0.8)
    ax[2].set_xlabel("beam diameter 2·LS (µm)"); ax[2].set_ylabel("melt-pool width W_A (µm)"); ax[2].set_title("Width is the melt pool, not the beam", loc="left")
    fig.tight_layout(); fig.savefig(OUT / "fig1_geometry_definitions.png", bbox_inches="tight"); plt.close(fig)


def _curves(units_E, systems, cond="STD"):
    M = P.manifest(); D = EV.learner_rows({k: v for k, v in units_E.items() if k[0] in systems and k[1] == cond}, M.y)
    return D.groupby(["system", "budget"]).BA.mean().unstack(0)


def fig_g2():
    import src.gt_eval as GE
    E, _, _ = GE.load_g2(); R = json.loads((GD.OUT / "dev" / "G2_RESULT.json").read_text(encoding="utf-8"))
    sys_ = ["C1", "GEO_A1", "GEO_A2", "GEO_B1", "GEO_B2", "GEO_B3", "CAL_B1", "C1_G", "C1_T"]; C = _curves(E, sys_)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
    for s in sys_:
        if s in C:
            ax[0].plot(C.index, C[s], color=COL[s], lw=2.2 if s == "C1" else 1.3, ls="-" if s.startswith(("C1", "GEO")) else "--", label=s)
            if s != "C1":
                ax[1].plot(C.index, C[s] - C["C1"], color=COL[s], lw=1.3, label=s)
    ax[0].set_xlabel("total simulations (incl. 8 startup)"); ax[0].set_ylabel("test BA (true labels), STD mean"); ax[0].set_title("G2: same opened runs as C1 (recorded C1 paths)", loc="left")
    ax[0].legend(frameon=False, fontsize=7, ncol=2); ax[1].axhline(0, color=GREY, lw=0.8); ax[1].set_xlabel("total simulations"); ax[1].set_ylabel("BA − C1")
    ax[1].set_title("Difference to C1 (200 STD learners)", loc="left"); ax[1].legend(frameon=False, fontsize=7, ncol=2)
    fig.tight_layout(); fig.savefig(OUT / "fig2_g2_matched.png", bbox_inches="tight"); plt.close(fig)


def fig_g3():
    import src.gt_eval as GE
    p = GD.OUT / "dev" / "G3_RESULT.json"
    if not p.exists():
        return
    E, _, _ = GE.load_g3(); sys_ = ["C1_own", "GEO_margin_own", "GEO_straddle_own", "GEO_space_own", "GEO_on_C1", "C1_on_GEO"]; C = _curves(E, sys_)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
    for s in sys_:
        if s in C:
            ax[0].plot(C.index, C[s], color=COL[s], lw=2.2 if s == "C1_own" else 1.3, ls=":" if s in ("GEO_on_C1", "C1_on_GEO") else "-", label=s)
            if s != "C1_own":
                ax[1].plot(C.index, C[s] - C["C1_own"], color=COL[s], lw=1.3, ls=":" if s in ("GEO_on_C1", "C1_on_GEO") else "-", label=s)
    ax[0].set_xlabel("total simulations"); ax[0].set_ylabel("test BA, STD mean"); ax[0].set_title("G3: each system on its own query path", loc="left"); ax[0].legend(frameon=False, fontsize=7)
    ax[1].axhline(0, color=GREY, lw=0.8); ax[1].set_xlabel("total simulations"); ax[1].set_ylabel("BA − C1_own"); ax[1].legend(frameon=False, fontsize=7)
    fig.tight_layout(); fig.savefig(OUT / "fig3_g3_own_path.png", bbox_inches="tight"); plt.close(fig)


def fig_tb():
    p = GD.OUT / "temporal" / "TB_DEV_RESULT.json"
    if not p.exists():
        return
    R = json.loads(p.read_text(encoding="utf-8")); models = ("S", "S+T", "S+D", "S+D+T", "C1p"); cols = {"S": GREY, "S+T": "#CC79A7", "S+D": "#0072B2", "S+D+T": "#009E73", "C1p": "#000000"}
    fig, ax = plt.subplots(1, 3, figsize=(14, 4.2)); ts = sorted(R["info"], key=float)
    for m in models:
        ax[0].plot([float(t) for t in ts], [R["info"][t][m]["ll"] for t in ts], marker="o", color=cols[m], label=m)
        ax[1].plot([float(t) for t in ts], [R["info"][t]["strata"]["keyhole_K_after_tc"][m]["sens"] if "sens" in R["info"][t]["strata"]["keyhole_K_after_tc"].get(m, {}) else np.nan for t in ts],
                   marker="o", color=cols[m], label=m)
    ax[0].set_xlabel("decision time after the simulation start (ms)"); ax[0].set_ylabel("held-out log loss (DEV runs)"); ax[0].set_title("Information up to time t", loc="left"); ax[0].legend(frameon=False, fontsize=8)
    for t in ts:
        n = R["info"][t]["strata"]["keyhole_K_after_tc"].get("S", {}).get("n")
        if n:
            ax[1].annotate(f"n = {n}", (float(t), 0.44), ha="center", fontsize=8, color=GREY)
    ax[1].set_xlabel("decision time (ms)"); ax[1].set_ylabel("recall of runs whose first K frame is LATER"); ax[1].set_title("Predicting a future Keyhole event", loc="left")
    b = R["time"]["FAR_0.05"]; mk = {"S": "o", "S+T": "o", "S+D": "s", "S+D+T": "x"}; sz = {"S": 60, "S+T": 60, "S+D": 110, "S+D+T": 70}
    for m in ("S", "S+T", "S+D", "S+D+T"):
        ax[2].scatter(b[m]["time_read_all"], b[m]["capture"], s=sz[m], marker=mk[m], color=cols[m], label=f"{m} (false alarms {b[m]['false_alarm']:.3f})")
    ax[2].set_xlabel("mean share of planned simulation time read (all runs)"); ax[2].set_ylabel("Keyhole capture"); ax[2].set_title("Alarms at ≤ 5 % false-alarm rate", loc="left")
    ax[2].legend(frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "fig4_early_temperature.png", bbox_inches="tight"); plt.close(fig)


def fig_ceiling():
    M = P.manifest(); R = GD.runs().reindex(M.index); y = M.y.to_numpy(int)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.0))
    bins = np.arange(0, 320, 10); ax[0].hist(R.A_um[y == 1].dropna(), bins=bins, color=CK, alpha=0.85, label="Keyhole"); ax[0].hist(R.A_um[y == 0].dropna(), bins=bins, color=CB, alpha=0.6, label="conduction")
    ax[0].axvline(295, color=GREY, ls=":", lw=1); ax[0].set_xlabel("active-window maximum depth A (µm)"); ax[0].set_ylabel("runs"); ax[0].set_title("Depth pile-up at ~300 µm", loc="left"); ax[0].legend(frameon=False, fontsize=8)
    cap = R.ceil_rows > 0; ax[1].scatter(M.VX[cap], R.ceil_plateau_median_um[cap], s=12, color=CK)
    ax[1].set_xlabel("scan speed VX (m/s)"); ax[1].set_ylabel("median depth of rows ≥ 295 µm"); ax[1].set_title("The plateau level is nearly constant (300.2 µm)", loc="left")
    fig.tight_layout(); fig.savefig(OUT / "fig5_depth_ceiling.png", bbox_inches="tight"); plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in (fig_definitions, fig_ceiling, fig_g2, fig_g3, fig_tb):
        try:
            f(); print("ok", f.__name__)
        except FileNotFoundError as ex:
            print("skip", f.__name__, ex)


if __name__ == "__main__":
    main()
