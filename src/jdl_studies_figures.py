"""Figures for STUDIES_REPORT_20261017.md (PHYS_AL, PHYS_DISCOVERY, TEMPORAL_STRUCT).

Descriptive only: it reads the frozen unit caches and result files and fits nothing. The curves use the evaluators' own
definitions: R^2(b) pooled over the five folds of a repeat with the population mean as reference, and the fraction of the
fold pool's top-decile family paid by budget b.  Repeats are averaged only after each repeat's curve is formed.
    python -m src.jdl_studies_figures
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import gzip
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import src.jdl_phys_al as PAL
import src.jdl_phys_discovery as PD

FIG = PAL.SMM.OUT / "studies_20261017_figures"
# Okabe-Ito (colour-blind safe), one colour per arm or model in every figure
COL = {"RANDOM": "#999999", "MAXIMIN": "#000000", "MAXVAR": "#0072B2", "IVR": "#E69F00", "MO_MAXVAR": "#009E73", "SD_MAXVAR": "#D55E00",
       "MEAN": "#999999", "KRON": "#0072B2", "PCA": "#E69F00", "FULL5D": "#009E73", "SCALAR": "#D55E00"}
STYLE = {"RANDOM": "-", "MAXIMIN": "--", "MAXVAR": "-", "IVR": "-", "MO_MAXVAR": "-.", "SD_MAXVAR": "-"}
LABEL = {"log_A_um": "log A (active max depth)", "log_ke_T0_nJ": "log KE over T0", "vmax_spike_logratio": "velocity spike log-ratio",
         "vmax_spike_us": "velocity spike duration", "laser_T0_W": "laser power to melt, T0", "tmax_T0_K": "max melt temperature, T0",
         "log_etot_T0_J": "log total melt energy, T0", "log_npart_T0": "log melt particle number, T0"}
plt.rcParams.update({"font.size": 9.5, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e6e6",
                     "grid.linewidth": 0.8, "axes.axisbelow": True, "savefig.bbox": "tight", "savefig.dpi": 170, "lines.linewidth": 1.6})
BUD = np.arange(PAL.B0, PAL.B1 + 1)


def _units(cache, pop):
    R = {}
    for p in cache.glob(f"{pop}__*.json.gz"):
        r = json.loads(gzip.decompress(p.read_bytes())); R[(r["repeat"], r["fold"], r["arm"], r.get("target"))] = r
    return R


def fig_phys_al(pop, res):
    Tt = PAL.targets(pop); R = _units(PAL.CACHE, pop); T = res[pop]["targets"]
    cols = [c for c in PAL.PRIMARY + PAL.SECONDARY if T.get(c, {}).get("available", True) and c in T]
    fig, axes = plt.subplots(2, 4, figsize=(13.5, 6.2), sharex=True); axes = axes.ravel()
    for ax, c in zip(axes, cols):
        ref = float(Tt[c].dropna().mean())
        for arm, key in (("RANDOM", "ALL"), ("MAXIMIN", "ALL"), ("MAXVAR", c), ("IVR", c), ("MO_MAXVAR", "MO")):
            per = []
            for rep in PAL.REPEATS:
                cv = []
                for b in BUD:
                    yy, pp = [], []
                    for f in PAL.FOLDS:
                        u = R[(rep, f, arm, key)]; e = {x["budget"]: x for x in u["evals"]}[int(b)]
                        yv = Tt.reindex(u["test_ids"])[c].to_numpy(float); pv = np.asarray(e["pred"][c], float); ok = np.isfinite(yv)
                        yy.extend(yv[ok]); pp.extend(pv[ok])
                    yy, pp = np.asarray(yy), np.asarray(pp); cv.append(1 - np.sum((yy - pp) ** 2) / np.sum((yy - ref) ** 2))
                per.append(cv)
            ax.plot(BUD, np.mean(per, 0), STYLE[arm], color=COL[arm], label=arm)
        ax.axhline(T[c]["target_level"], color="#CC79A7", lw=1.0, ls=":")
        ax.set_title(f"{LABEL[c]}\nR²_full {T[c]['R2_full']:.2f}", fontsize=9.5); ax.set_ylim(max(-0.2, ax.get_ylim()[0]), 1.0)
    for ax in axes[len(cols):]:
        ax.axis("off")
    for ax in axes[4:]:
        ax.set_xlabel("paid simulations (budget)")
    for ax in axes[::4]:
        ax.set_ylabel("out-of-fold R² (mean of r3, r4)")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h + [plt.Line2D([], [], color="#CC79A7", ls=":")], l + ["target level 0.9 × R²_full"], loc="lower center", ncol=6, frameon=False,
               bbox_to_anchor=(0.5, -0.04))
    fig.suptitle(f"PHYS_AL ({pop}, DEV r3–4 × 5 folds): accuracy against paid simulations for each physical output", x=0.01, ha="left", fontsize=11)
    FIG.mkdir(parents=True, exist_ok=True); fig.savefig(FIG / f"phys_al_r2_curves_{pop}.png"); plt.close(fig)


def fig_discovery():
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.9))
    for ax, pop in zip(axes, ("NEW", "OLD")):
        Tt = PAL.targets(pop); y = Tt[PD.RESPONSE].dropna(); fam = set(y[y >= y.quantile(0.9)].index)
        T = {(t["repeat"], t["fold"]): t for t in PAL.tasks(pop)}; R = _units(PD.CACHE, pop)
        for arm in ("RANDOM", "MAXIMIN", "MAXVAR", "SD_MAXVAR"):
            curves = []
            for (r, f), t in T.items():
                u = R[(r, f, arm, None)]; pool = set(np.asarray(t["ids"]).astype(str)[t["pool"]]); nh = max(1, len(fam & pool))
                curves.append([len(fam & set(u["paid_ids"][:b])) / nh for b in BUD])
            curves = np.asarray(curves)
            ax.plot(BUD, curves.mean(0), STYLE[arm], color=COL[arm], label=arm)
            ax.fill_between(BUD, np.percentile(curves, 25, 0), np.percentile(curves, 75, 0), color=COL[arm], alpha=0.12, lw=0)
        ax.set_title(f"{pop}: top-decile family of the velocity spike log-ratio ({len(fam)} runs)", fontsize=9.5)
        ax.set_xlabel("paid simulations (budget)"); ax.set_ylabel("fraction of the pool's family paid"); ax.set_ylim(0, 1)
    axes[0].legend(frameon=False, loc="upper left")
    fig.suptitle("PHYS_DISCOVERY: family discovery (mean over 10 trajectories; band = interquartile range)", x=0.01, ha="left", fontsize=11)
    FIG.mkdir(parents=True, exist_ok=True); fig.savefig(FIG / "phys_discovery_curves.png"); plt.close(fig)


def fig_temporal():
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.2)); fig.subplots_adjust(wspace=0.3)
    chans = ("velocity", "ke", "depth"); res = {p: json.loads((PAL.SMM.OUT / "temporal_struct" / "results" / f"TEMPORAL_STRUCT_RESULTS_{p}.json").read_text(encoding="utf-8"))
                                               for p in ("NEW", "OLD")}
    x = np.arange(len(chans)); w = 0.18
    # (a) curve accuracy
    ax = axes[0]
    for k, (pop, m, key) in enumerate((("NEW", "KRON", "R2_curve_KRON"), ("NEW", "PCA", "R2_curve_PCA"), ("OLD", "KRON", "R2_curve_KRON"), ("OLD", "PCA", "R2_curve_PCA"))):
        v = [np.mean([res[pop]["channels"][c]["per_repeat"][r][key] for r in ("3", "4")]) for c in chans]
        ax.bar(x + (k - 1.5) * w, v, w * 0.92, color=COL[m], alpha=1.0 if pop == "NEW" else 0.55, label=f"{m} ({pop})", edgecolor="white", linewidth=1)
    ax.set_xticks(x); ax.set_xticklabels(chans); ax.set_ylim(0, 1); ax.set_ylabel("R²_curve vs mean curve (mean of r3, r4)"); ax.set_title("(a) whole-curve accuracy\n(R² vs the mean curve)", fontsize=9.5)
    ax.legend(frameon=False, fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    # (b) FULL5D vs KRON on the subgrid (NEW)
    ax = axes[1]
    for k, (m, key) in enumerate((("KRON", "R2_sub_KRON"), ("FULL5D", "R2_sub_FULL5D"))):
        v = [np.mean([res["NEW"]["channels"][c]["per_repeat"][r][key] for r in ("3", "4")]) for c in chans]
        ax.bar(x + (k - 0.5) * w * 1.6, v, w * 1.5, color=COL[m], label=m, edgecolor="white", linewidth=1)
    ax.set_xticks(x); ax.set_xticklabels(chans); ax.set_ylim(0, 1); ax.set_title("(b) separable KRON vs non-separable FULL5D\n(NEW, every 4th bin)", fontsize=9.5)
    ax.legend(frameon=False, fontsize=8)
    # (c) derived quantities: best temporal RMSE / SCALAR RMSE
    ax = axes[2]
    for k, (pop, q) in enumerate((("NEW", "T0"), ("NEW", "peak"), ("OLD", "T0"), ("OLD", "peak"))):
        v = []
        for c in chans:
            best = res[pop]["channels"][c][f"TEMPORAL_BEATS_SCALAR_{q}"]["best_temporal"]
            v.append(np.mean([res[pop]["channels"][c]["per_repeat"][r][f"rmse_{q}_{best}"] / res[pop]["channels"][c]["per_repeat"][r][f"rmse_{q}_SCALAR"] for r in ("3", "4")]))
        ax.bar(x + (k - 1.5) * w, v, w * 0.92, color="#56B4E9" if q == "T0" else "#CC79A7", alpha=1.0 if pop == "NEW" else 0.55, label=f"{q} ({pop})",
               edgecolor="white", linewidth=1)
    ax.axhline(1.0, color="black", lw=0.9); ax.axhline(0.95, color="#D55E00", lw=1.0, ls=":")
    ax.set_xticks(x); ax.set_xticklabels(chans); ax.set_ylabel("best temporal RMSE / direct scalar GP RMSE"); ax.set_ylim(0, 2.1)
    ax.set_title("(c) derived quantities: temporal / scalar RMSE\n(< 0.95 needed to beat SCALAR)", fontsize=9.5); ax.legend(frameon=False, fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    fig.suptitle("TEMPORAL_STRUCT: structured temporal GPs for monitor curves (DEV r3–4, all pool runs revealed: an upper bound)", x=0.01, ha="left", fontsize=11, y=1.07)
    FIG.mkdir(parents=True, exist_ok=True); fig.savefig(FIG / "temporal_struct_summary.png"); plt.close(fig)


def main():
    res = json.loads((PAL.OUT / "results" / "PHYS_AL_RESULTS.json").read_text(encoding="utf-8"))
    for pop in ("NEW", "OLD"):
        fig_phys_al(pop, res)
    fig_discovery(); fig_temporal(); print(sorted(p.name for p in FIG.glob("*.png")))


if __name__ == "__main__":
    main()
