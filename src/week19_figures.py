"""Week 19 figures (matplotlib, static PNG).  Colours: Keyhole #CC3311, Conduction #4477AA, Forming Phase #999933,
technical labels light grey (the thesis palette); windows are shaded, never coloured like a class."""
from __future__ import annotations

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.week19_sources import OUT

FIG = OUT / "figures"
KH, CO, FO, TECH, INK, MUTED = "#CC3311", "#4477AA", "#999933", "#BBBBBB", "#222222", "#666666"
LABEL_COLOR = {"K": KH, "C": CO, "F": FO, "IE": TECH, "SS": "#888888", "SoS": "#AAAAAA", "SB": "#EE3377", "U": "#EE7733"}
DESC_COLOR = {"conduction_only": CO, "K_then_C__no_later_K": "#EE7733", "alternating__terminal_C": "#EE3377",
              "C_then_K__K_at_end": "#AA3377", "alternating__K_at_end": "#882255", "keyhole_only__K_at_end": KH,
              "forming_only": FO, "no_physical_label": TECH}
plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#888888", "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 130})


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name, bbox_inches="tight", dpi=160)
    plt.close(fig)
    return str((FIG / name).relative_to(OUT.parent.parent))


def descriptors_by_group(reg):
    from src.week19_temporal_audit import DESCRIPTOR_ORDER
    groups = [("OLD (405)", reg.campaign == "OLD")] + [(f"OLD {p}", (reg.campaign == "OLD") & (reg.partition == p)) for p in ("new-data", "old-data-local", "old-data-remote-clean")] + [("October NEW (136)", reg.campaign == "NEW")]
    fig, ax = plt.subplots(figsize=(8.2, 2.9))
    for i, (name, m) in enumerate(groups):
        sub = reg[m]; left = 0
        for dsc in DESCRIPTOR_ORDER:
            n = int((sub.descriptor == dsc).sum())
            if n:
                w = n / len(sub)
                ax.barh(i, w, left=left, color=DESC_COLOR[dsc], edgecolor="white", linewidth=1)
                if w > 0.06:
                    ax.text(left + w / 2, i, str(n), ha="center", va="center", color="white", fontsize=8)
                left += w
        ax.text(1.01, i, f"n={len(sub)}", va="center", fontsize=8, color=MUTED)
    ax.set_yticks(range(len(groups)), [g[0] for g in groups]); ax.invert_yaxis(); ax.set_xlim(0, 1); ax.set_xlabel("share of simulations")
    handles = [plt.Rectangle((0, 0), 1, 1, color=DESC_COLOR[d]) for d in DESCRIPTOR_ORDER if (reg.descriptor == d).any()]
    ax.legend(handles, [d for d in DESCRIPTOR_ORDER if (reg.descriptor == d).any()], ncol=3, fontsize=7, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.28))
    ax.set_title("Frame-label sequence descriptors (observation; OLD partition 'new-data' is not the October NEW campaign)", fontsize=9, loc="left")
    return _save(fig, "fig1_descriptors_by_group.png")


def kfraction_vs_vx(reg):
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.2), sharey=True)
    for ax, camp in zip(axs, ("OLD", "NEW")):
        s = reg[(reg.campaign == camp) & (reg.has_keyhole_frozen == 1)]
        for regime, col, mk in (("C", "#EE7733", "o"), ("K", KH, "s")):
            q = s[s.final_active_regime == regime]
            ax.scatter(q.VX, q.frac_K_FCK, s=16, c=col, marker=mk, edgecolors="white", linewidths=0.5, label=f"final active regime {regime} (n={len(q)})")
        ax.axhline(0.05, color=MUTED, lw=0.8, ls=":"); ax.axhline(0.10, color=MUTED, lw=0.8, ls="--")
        ax.set_yscale("log"); ax.set_xlabel("scan speed VX (m/s)"); ax.set_title(f"{camp} positives (n={len(s)})", loc="left", fontsize=9)
        ax.legend(fontsize=7, frameon=False, loc="lower left")
    axs[0].set_ylabel("K/(F+C+K) frames (log)")
    fig.suptitle("Keyhole frame fraction among has_keyhole positives; dotted 5 %, dashed 10 %", fontsize=9, x=0.01, ha="left")
    return _save(fig, "fig2_positive_K_fraction_vs_VX.png")


def switch_timing(trans):
    fig, ax = plt.subplots(figsize=(6.4, 2.8))
    kc = trans[trans.type == "K_to_C"].sort_values("from_pos").groupby("sim_id").head(1)
    bins = np.linspace(0, 1.8, 37)
    for camp, col in (("OLD", "#555555"), ("NEW", "#EE7733")):
        v = kc[kc.campaign == camp].from_over_exit.dropna()
        ax.hist(v, bins=bins, histtype="step", lw=1.6, color=col, label=f"{camp}: first K->C switch per simulation (n={len(v)})")
    ax.axvline(0.9, color=MUTED, ls="--", lw=0.8); ax.axvline(1.0, color=INK, ls=":", lw=0.8)
    ax.text(0.9, ax.get_ylim()[1] * 0.95, " 90 % cutoff", fontsize=7, color=MUTED, va="top"); ax.text(1.0, ax.get_ylim()[1] * 0.8, " derived exit", fontsize=7, va="top")
    ax.set_xlabel("time of the last K frame before the switch / derived domain-exit time"); ax.set_ylabel("simulations")
    ax.legend(fontsize=7, frameon=False, loc="upper right", bbox_to_anchor=(1.0, 0.72))
    return _save(fig, "fig3_first_K_to_C_switch_timing.png")


def depth_definitions(d, u):
    cols = [("max_depth_whole_um", "frozen\nwhole max"), ("A_active_max_um", "A\nactive max"), ("B_postforming_max_um", "B post-\nforming max\n(uses labels)"),
            ("G3_persistent_depth_um", "C\nG3"), ("T0_depth_um", "C\nT0")]
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.4), sharey=True)
    rng = np.random.default_rng(0)
    for ax, camp in zip(axs, ("OLD", "NEW")):
        s = d[d.campaign == camp]
        for j, (c, lab) in enumerate(cols):
            for y, col, off in ((0, CO, -0.17), (1, KH, 0.17)):
                v = s.loc[s.y == y, c].dropna()
                ax.scatter(j + off + rng.uniform(-0.07, 0.07, len(v)), v, s=6 if camp == "OLD" else 10, c=col, alpha=0.6, linewidths=0)
        ax.axhline(u["u_ref_um"], color=INK, ls="--", lw=0.8)
        ax.set_xticks(range(len(cols)), [c[1] for c in cols], fontsize=7); ax.set_yscale("log")
        ax.set_title(f"{camp} ({len(s)} runs)", loc="left", fontsize=9)
    axs[0].set_ylabel("depth (um, log)")
    fig.suptitle(f"Depth definitions by class (blue has_keyhole=0, red has_keyhole=1); dashed = OLD reference threshold u_ref = {u['u_ref_um']:.2f} um",
                 fontsize=9, x=0.01, ha="left")
    return _save(fig, "fig4_depth_definitions_by_class.png")


def _label_strip(ax, fmap_sim, y0, h):
    for c, g in fmap_sim.groupby("code"):
        t = g.time_ms.dropna()
        ax.vlines(t, y0, y0 + h, color=LABEL_COLOR.get(c, TECH), lw=0.9)


def case_panel(ax, sim, fmap_sim, row, u, title, ke=None, show_geometry=False, ax2=None):
    t, dep = sim["t_ms"], sim["depth_um"]
    ax.plot(t, dep, color=INK, lw=0.6)
    ax.axhline(u, color=MUTED, ls="--", lw=0.7)
    if np.isfinite(row.get("active_cutoff_ms", np.nan)):
        ax.axvline(row["active_cutoff_ms"], color="#888888", ls="--", lw=0.7)
    if np.isfinite(row.get("derived_exit_ms", np.nan)):
        ax.axvline(row["derived_exit_ms"], color=INK, ls=":", lw=0.7)
    ymax = np.nanmax(dep) if np.isfinite(dep).any() else 1
    _label_strip(ax, fmap_sim, ymax * 1.05, ymax * 0.12)
    ax.set_ylim(0, ymax * 1.2)
    ax.set_title(title, loc="left", fontsize=7)
    if ax2 is not None:
        ax2.plot(t, sim["width_um"], color="#4477AA", lw=0.6, label="width")
        ax2.plot(t, sim["length_um"], color="#228833", lw=0.6, label="length")
        if ke is not None:
            ax3 = ax2.twinx(); ax3.plot(ke[0], ke[1], color="#AA3377", lw=0.6, label="melt kinetic energy"); ax3.set_ylabel("KE (nJ)", fontsize=7, color="#AA3377")
            ax3.spines["right"].set_visible(True)
        _label_strip(ax2, fmap_sim, 0, np.nanmax(sim["width_um"]) * 0.08 if np.isfinite(sim["width_um"]).any() else 1)
        ax2.legend(fontsize=6, frameon=False, loc="upper left")


def new_negatives(cases, series_by_id, fmap, reg, u):
    ids = cases.sim_id.tolist()
    fig, axs = plt.subplots(4, 3, figsize=(11, 10.5))
    R = reg.set_index("sim_id")
    for ax, sid in zip(axs.ravel(), ids):
        c = cases.set_index("sim_id").loc[sid]
        sim = series_by_id.get(sid)
        fm = fmap[fmap.sim_id == sid]
        title = f"H-{sid.split('_H-')[-1]}  VX={c.VX_m_s:.3f}  max={c.max_depth_whole_um:.1f}  G3pd={c.G3_um:.1f} um\n{c.mechanism_vs_uref}"
        if sim is None:
            ax.set_ylim(0, 1); ax.set_yticks([])
            _label_strip(ax, fm, 0.86, 0.1)
            ax.text(0.5, 0.45, "bounds/time row mismatch (40,805 vs 40,803 rows):\ntime-dependent depth unavailable, no truncation;\nlabels only: Initial Emptiness then Forming Phase, no C/K",
                    ha="center", va="center", fontsize=7, transform=ax.transAxes)
            ax.set_title(title, loc="left", fontsize=7)
            continue
        case_panel(ax, sim, fm, R.loc[sid].to_dict(), u["u_ref_um"], title)
    for ax in axs[-1]:
        ax.set_xlabel("monitor time (ms)")
    for ax in axs[:, 0]:
        ax.set_ylabel("depth (um)")
    fig.suptitle("The 12 October NEW has_keyhole=0 runs: melt-subset depth (black), OLD u_ref (dashed), 90 % active cutoff (grey dashed), derived exit (dotted);\n"
                 "top strip = manual frame labels at mapped monitor times (blue C, red K, olive F, grey technical); "
                 "G3pd = G3 persistent depth (physical rolling-median statistic, not the G3 classifier)", fontsize=8, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return _save(fig, "fig5_new_negatives_depth_with_labels.png")


def representative(cases_sel, series_by_id, ke_by_id, fmap, reg, u):
    out = []
    R = reg.set_index("sim_id")
    n = len(cases_sel)
    fig, axs = plt.subplots(n, 2, figsize=(11, 2.05 * n), squeeze=False)
    for i, r in enumerate(cases_sel.itertuples(index=False)):
        sim = series_by_id.get(r.sim_id); fm = fmap[fmap.sim_id == r.sim_id]
        row = R.loc[r.sim_id].to_dict()
        title = (f"{r.role}: {row['campaign']} H-{r.sim_id.split('_H-')[-1]} P={row['P']:.0f} VX={row['VX']:.3f} LS={row['LS_um_radius']:.1f}um ST={row['ST']:.0f}  "
                 f"has_keyhole={int(row['has_keyhole_frozen'])}  {row['collapsed_active_sequence'][:60]}")
        if sim is None:
            axs[i, 0].text(0.5, 0.5, "series unavailable", transform=axs[i, 0].transAxes, ha="center"); continue
        case_panel(axs[i, 0], sim, fm, row, u["u_ref_um"], title, ke=ke_by_id.get(r.sim_id), ax2=axs[i, 1])
        axs[i, 0].set_ylabel("depth (um)")
    axs[-1, 0].set_xlabel("monitor time (ms)"); axs[-1, 1].set_xlabel("monitor time (ms)")
    fig.suptitle("Representative cases: left depth with manual labels (strip) and windows; right width/length (um) and melt kinetic energy (not absorbed laser energy)",
                 fontsize=8, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.985))
    out.append(_save(fig, "fig6_representative_cases.png"))
    return out
