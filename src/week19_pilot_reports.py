"""Week 19 DEV pilot — no-fit companions: descriptive whole-vs-A table, Ioan's one-page summary figures and case list,
pilot figures, and the timestep×DT usage audit.  Nothing here fits a model or changes a label.

Steps: python -m src.week19_pilot_reports descriptive | ioan | pilotfigs | dtaudit | all
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from src.week19_dev_pilot import (AUDIT, BUDGETS, LATE_NEG, NEW_REV, OLD_REV, OUT, PULL_UM, ROOT, TAB, UNRESOLVED, UREF, _w, auc, ba_at,
                                  short)

FIG = OUT / "figures"
KH, CO, FO, TECH, INK, MUTED = "#CC3311", "#4477AA", "#999933", "#BBBBBB", "#222222", "#666666"
LABEL_COLOR = {"K": KH, "C": CO, "F": FO, "IE": TECH, "SS": "#888888", "SoS": "#AAAAAA", "SB": "#EE3377", "U": "#EE7733"}
ARM_COLOR = {"WHOLE_E1_SHARED": "#4477AA", "ACTIVE_E1_SHARED": "#CC3311", "G3_SHARED": "#666666"}
ARM_SHORT = {"WHOLE_E1_SHARED": "WHOLE E1", "ACTIVE_E1_SHARED": "ACTIVE E1", "G3_SHARED": "G3"}
HF = "https://huggingface.co/datasets/ioandanielc/sph_v2"
FAST_VX = 0.85
A_ORACLE_NEW = 142.23219999999998          # existing NEW same-population oracle threshold for A (separability.csv)
plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#888888", "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 130})


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name, bbox_inches="tight", dpi=160)
    plt.close(fig)
    return f"figures/{name}"


def oracle_ba(y, s):
    """Best single threshold (rule s >= c) on the same population: descriptive ORACLE, never a held-out estimate."""
    y, s = np.asarray(y), np.asarray(s, float)
    if len(np.unique(y)) < 2:
        return np.nan, np.nan
    best = max(((ba_at(y, s, c), c) for c in np.unique(s)), key=lambda t: (t[0], -t[1]))
    return best


# ======================================================================================== item 3: descriptive table
LABELS = {"has_keyhole": ("original benchmark label (unchanged)", None), "K/(K+C)>=0.05": ("descriptive alternative, not a replacement", 0.05),
          "K/(K+C)>=0.10": ("descriptive alternative, not a replacement", 0.10)}


def descriptive():
    inp = pd.read_csv(TAB / "pilot_inputs.csv")
    rows = []
    for camp in ("OLD", "NEW"):
        for subset in ("all", f"VX>{FAST_VX}"):
            d = inp[inp.campaign == camp]
            if subset != "all":
                d = d[d.VX_m_s > FAST_VX]
            for lab, (role, thr) in LABELS.items():
                if thr is None:
                    y = d.has_keyhole.astype(float); undef = pd.Series(False, index=d.index)
                else:
                    undef = d.frac_K_KC.isna(); y = (d.frac_K_KC >= thr).astype(float).where(~undef)
                relab = int(((y != d.has_keyhole) & ~undef).sum())
                for score, cohort in (("whole_max_um", "all runs with the score"), ("whole_max_um", "paired cohort (A available)"), ("A_um", "paired cohort (A available)")):
                    miss = d[score].isna() if cohort.startswith("all") else d.A_um.isna()
                    keep = ~undef & ~miss
                    yy, ss = y[keep].astype(int).to_numpy(), d.loc[keep, score].to_numpy(float)
                    ob, oc = oracle_ba(yy, ss)
                    rows.append({"campaign": camp, "subset": subset, "exploratory": subset != "all", "label": lab, "label_role": role, "score": score, "cohort": cohort,
                                 "n_runs_in_subset": len(d), "n_undefined_ratio": int(undef.sum()), "n_target_missing": int((miss & ~undef).sum()),
                                 "n_evaluated": int(keep.sum()), "n_positive": int(yy.sum()), "n_negative": int((yy == 0).sum()),
                                 "n_relabelled_vs_has_keyhole": relab, "AUC": auc(yy, ss), "oracle_BA_same_population": ob, "oracle_threshold_um": oc,
                                 "BA_at_uref": ba_at(yy, ss, UREF)})
    t = pd.DataFrame(rows)
    _w(t, "descriptive_whole_vs_A_by_label.csv")
    return t


def descriptive_markdown(t):
    p = t[t.cohort.str.startswith("paired")]
    lines = ["| Campaign | Runs | Label | n (pos/neg) | Undefined ratio | A missing | Whole max AUC | Whole max oracle BA | A AUC | A oracle BA |",
             "|---|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for (camp, subset, lab), g in p.groupby(["campaign", "subset", "label"], sort=False):
        w, a = g[g.score == "whole_max_um"].iloc[0], g[g.score == "A_um"].iloc[0]
        sub = "all" if subset == "all" else f"VX > {FAST_VX} *(exploratory)*"
        f = lambda v: "—" if not np.isfinite(v) else f"{v:.3f}"  # noqa: E731
        lines.append(f"| {camp} | {sub} | {lab} | {int(a.n_evaluated)} ({int(a.n_positive)}/{int(a.n_negative)}) | {int(a.n_undefined_ratio)} | {int(a.n_target_missing)} | "
                     f"{f(w.AUC)} | {f(w.oracle_BA_same_population)} | {f(a.AUC)} | {f(a.oracle_BA_same_population)} |")
    return "\n".join(lines)


# ======================================================================================== series helpers
def _registry():
    return pd.read_csv(AUDIT / "tables/temporal_registry.csv")


def _frames():
    return pd.read_csv(AUDIT / "tables/frame_level_map.csv.gz")


def _series(ids, reg):
    from src.week19_temporal_audit import _series_cache
    return _series_cache(ids, reg)


def _strip(ax, fm, y0, h, lw=0.8):
    for c, g in fm.groupby("code"):
        t = g.time_ms.dropna()
        ax.vlines(t, y0, y0 + h, color=LABEL_COLOR.get(c, TECH), lw=lw)


def _trace(ax, sim, fm, row, title, ymax=None, xlim=None):
    ax.plot(sim["t_ms"], sim["depth_um"], color=INK, lw=0.7)
    ax.axhline(UREF, color=MUTED, ls="--", lw=0.7)
    ax.axvline(row["active_cutoff_ms"], color="#888888", ls="--", lw=0.7)
    top = ymax or np.nanmax(sim["depth_um"]) * 1.05
    _strip(ax, fm, top * 1.02, top * 0.10)
    ax.set_ylim(0, top * 1.14)
    xr = xlim or (0, max(row["recording_end_ms"], row["derived_exit_ms"]) * 1.04)
    ax.set_xlim(*xr)
    if row["derived_exit_ms"] <= xr[1]:
        ax.axvline(row["derived_exit_ms"], color=INK, ls=":", lw=0.7)
    else:
        ax.text(0.99, 0.62, f"exit {row['derived_exit_ms']:.1f} ms →", transform=ax.transAxes, ha="right", fontsize=7, color=MUTED)
    ax.axvline(row["recording_end_ms"], color=INK, lw=0.5, alpha=0.6)
    ax.text(row["recording_end_ms"], top * 0.97, "recording end ", fontsize=6.5, color=MUTED, ha="right", va="top")
    ax.set_title(title, loc="left", fontsize=8)
    ax.set_xlabel("monitor time (ms, iter.dat → time.dat)")
    ax.set_ylabel("melt-subset depth (µm)")


def pick_K_to_C():
    """Deterministic: per NEW VX subgroup, the K-then-only-C run whose K/(F+C+K) is closest to the subgroup median (stable)."""
    k = pd.read_csv(AUDIT / "tables/K_then_C_cases.csv")
    out = {}
    for grp, name in (("fast VX>=0.85", "fast"), ("slow VX<0.4", "slow")):
        g = k[(k.campaign == "NEW") & (k.VX_group == grp)]
        j = (g.frac_K_FCK - g.frac_K_FCK.median()).abs().sort_values(kind="stable").index[0]
        out[name] = (g.loc[j, "sim_id"], f"closest to the NEW {grp} K-then-only-C median K/(F+C+K) {g.frac_K_FCK.median():.3f} (n={len(g)})")
    return out


MATCH_NEG = "P-387p361336282_VX-0p960187357846_LS-4p72484046084e-05_ST-390p52586458_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p02414509376e-06_H-b302fc6cbd"
MATCH_POS = "P-380p041479483_VX-0p952843483906_LS-4p56527036263e-05_ST-376p177191048_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p0628678104e-06_H-b7e3ed2e12"
B2EE = UNRESOLVED[0]
LATE_K = "P-351p92267109_VX-0p98107853237_LS-4p98248594664e-05_ST-477p481832276_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-4p91716049617e-06_H-349225d53c"
ALT_NEW = "P-366p200299346_VX-0p894349968262_LS-4p89176892953e-05_ST-476p393782659_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p39399650496e-06_H-6ca7f366ce"


def ioan_figures():
    reg = _registry(); R = reg.set_index("sim_id"); fmap = _frames()
    kc = pick_K_to_C()
    ids = [kc["fast"][0], kc["slow"][0], MATCH_NEG, MATCH_POS]
    ser = _series(ids, reg)
    paths = []
    # ---- figure 1: two K→C forms
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.4))
    for ax, key, head in zip(axs, ("fast", "slow"), ("Fast scan: a short Keyhole run, then Conduction to the end",
                                                    "Slow scan: long Keyhole, switching to Conduction just before the recording ends")):
        sid = kc[key][0]; row = R.loc[sid]; fm = fmap[fmap.sim_id == sid]
        ks = fm[fm.code == "K"]
        nxt = fm[(fm.time_ms > ks.time_ms.max()) & (fm.code == "C")].time_ms.min()
        _trace(ax, ser[sid], fm, row, f"{head}\n{short(sid)} · VX {row.VX:.3f} m/s · K/(F+C+K) {row.frac_K_FCK:.3f} · last K→C {ks.time_ms.max():.3f}→{nxt:.3f} ms",
               xlim=(0, row.recording_end_ms * 1.12) if key == "slow" else None)
        ax.axvspan(ks.time_ms.max(), nxt, color=KH, alpha=0.25, lw=0)
    fig.text(0.01, -0.06, "Top strip: manual frame labels at their exact monitor time (red Keyhole, blue Conduction, olive Forming, grey technical). "
             "Dashed horizontal: OLD reference threshold u_ref = 111 µm. Grey dashed vertical: 90 % active cutoff; dotted: derived exit. "
             "Shaded: the last K→C bracket (one frame interval). OBS only.", fontsize=7, color=MUTED, wrap=True)
    fig.tight_layout()
    paths.append(_save(fig, "ioan_fig1_two_K_to_C_forms.png"))
    # ---- figure 2: matched pair
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.4), gridspec_kw={"width_ratios": [1.3, 1]})
    for sid, col, lab in ((MATCH_NEG, CO, "negative"), (MATCH_POS, KH, "positive")):
        axs[0].plot(ser[sid]["t_ms"], ser[sid]["depth_um"], color=col, lw=0.7, label=f"{short(sid)} ({lab}, VX {R.loc[sid].VX:.3f})")
    axs[0].axhline(UREF, color=MUTED, ls="--", lw=0.7); axs[0].legend(fontsize=7, frameon=False, loc="upper right")
    axs[0].set_title("Matched fast-scan pair: nearly identical inputs and depth traces", loc="left", fontsize=8)
    axs[0].set_xlabel("monitor time (ms)"); axs[0].set_ylabel("melt-subset depth (µm)"); axs[0].set_ylim(0, 140)
    k = fmap[(fmap.sim_id == MATCH_POS) & (fmap.code == "K")]
    lo, hi = k.time_ms.min() - 0.06, k.time_ms.max() + 0.06
    for sid, col in ((MATCH_NEG, CO), (MATCH_POS, KH)):
        m = (ser[sid]["t_ms"] >= lo) & (ser[sid]["t_ms"] <= hi)
        axs[1].plot(ser[sid]["t_ms"][m], ser[sid]["depth_um"][m], color=col, lw=0.9)
    _strip(axs[1], fmap[(fmap.sim_id == MATCH_POS) & fmap.time_ms.between(lo, hi)], 132, 8, lw=1.2)
    _strip(axs[1], fmap[(fmap.sim_id == MATCH_NEG) & fmap.time_ms.between(lo, hi)], 120, 8, lw=1.2)
    axs[1].text(hi, 136, " positive labels", fontsize=7, va="center"); axs[1].text(hi, 124, " negative labels", fontsize=7, va="center")
    axs[1].axhline(UREF, color=MUTED, ls="--", lw=0.7); axs[1].set_ylim(60, 142); axs[1].set_xlim(lo, hi)
    axs[1].set_title(f"Zoom: the positive's {len(k)} Keyhole frames ({k.time_ms.min():.3f}–{k.time_ms.max():.3f} ms)\nsit on the same startup peak the negative labels C/F", loc="left", fontsize=8)
    axs[1].set_xlabel("monitor time (ms)")
    fig.tight_layout()
    paths.append(_save(fig, "ioan_fig2_matched_pair.png"))
    # ---- figure 3: A versus VX
    inp = pd.read_csv(TAB / "pilot_inputs.csv")
    reds = LinearSegmentedColormap.from_list("k_frac", ["#FDD9C4", "#F4A582", "#D6604D", "#B2182B", "#67001F"])
    fig, axs = plt.subplots(2, 2, figsize=(10, 6.4), sharex=True, sharey="row")
    for i, camp in enumerate(("OLD", "NEW")):
        d = inp[(inp.campaign == camp) & inp.A_available]
        sz = 12 if camp == "OLD" else 22
        ax = axs[i, 0]
        for yv, col, mk, lab in ((1, KH, "o", "has_keyhole = 1"), (0, CO, "s", "has_keyhole = 0")):      # negatives drawn on top
            g = d[d.has_keyhole == yv]
            ax.scatter(g.VX_m_s, g.A_um, s=sz, color=col, marker=mk, alpha=0.8, edgecolor="white", lw=0.3, label=f"{lab} ({len(g)})")
        ax.legend(fontsize=7, frameon=False, loc="upper center", ncol=2, handletextpad=0.2, columnspacing=0.8)
        ax = axs[i, 1]
        und = d[d.frac_K_KC.isna()]
        for yv, mk, lab in ((1, "o", "positive"), (0, "s", "negative")):
            dd = d[d.frac_K_KC.notna() & (d.has_keyhole == yv)]
            sc = ax.scatter(dd.VX_m_s, dd.A_um, c=dd.frac_K_KC, cmap=reds, vmin=0, vmax=1, s=sz, marker=mk, edgecolor="#555555", lw=0.3, label=f"{lab} (marker)")
        if len(und):
            ax.scatter(und.VX_m_s, und.A_um, color="#777777", s=24, marker="x", label=f"K/(K+C) undefined ({len(und)})")
        ax.legend(fontsize=7, frameon=False, loc="upper center", ncol=3, handletextpad=0.2, columnspacing=0.8)
        for ax in axs[i]:
            ax.axhline(UREF, color=MUTED, ls="--", lw=0.7)
            ax.axvline(FAST_VX, color=MUTED, ls=":", lw=0.7)
            if camp == "NEW":
                ax.axhline(A_ORACLE_NEW, color=MUTED, ls="-.", lw=0.7)
            ax.set_ylim(0, 365)
        axs[i, 0].set_ylabel(f"{camp}: A, active-window max depth (µm)")
        axs[i, 0].set_title(f"{camp} ({len(d)} runs with A): coloured by the benchmark label", loc="left", fontsize=8)
        axs[i, 1].set_title(f"{camp}: coloured by K/(K+C) frame fraction", loc="left", fontsize=8)
    cb = fig.colorbar(sc, ax=axs[:, 1], shrink=0.6, pad=0.02); cb.set_label("K/(K+C)")
    for ax in axs[1]:
        ax.set_xlabel("scan speed VX (m/s)")
    fig.text(0.01, -0.02, f"Dashed: u_ref = 111 µm (OLD rule). Dash-dot (NEW): descriptive same-population A oracle threshold 142 µm. Dotted: VX = {FAST_VX} "
             "(fast-scan cut, exploratory). H-e7dbd8e5ce (NEW negative) has no A and is not shown. OBS only; no model.", fontsize=7, color=MUTED)
    paths.append(_save(fig, "ioan_fig3_A_vs_VX.png"))
    return paths, kc


# ======================================================================================== Ioan cases: brackets and links
def _bracket_rows(sid, fm, kind, t_lo, t_hi, note):
    g = fm[(fm.sim_id == sid) & fm.time_ms.between(t_lo, t_hi)].sort_values("frame_pos")
    return {"sim_id": sid, "bracket": kind, "frame_first": int(g.frame_pos.min()), "frame_last": int(g.frame_pos.max()), "time_first_ms": float(g.time_ms.min()),
            "time_last_ms": float(g.time_ms.max()), "labels_in_bracket": "-".join(k for k, _ in __import__("itertools").groupby(g.code)), "note": note}


def _nearest_frame(fm, sid, t):
    g = fm[(fm.sim_id == sid) & fm.time_ms.notna()]
    return int(g.loc[(g.time_ms - t).abs().idxmin(), "frame_pos"])


def ioan_cases(verify=True):
    reg = _registry(); R = reg.set_index("sim_id"); fm = _frames()
    sw = pd.read_csv(AUDIT / "tables/regime_switches.csv"); kr = pd.read_csv(AUDIT / "tables/k_runs.csv")
    cases = [
        (MATCH_NEG, "fast-scan negative of the matched pair", "Is the startup peak (115.6 µm at 0.427 ms) a short Keyhole that was labelled Conduction/Forming?"),
        (MATCH_POS, "fast-scan positive of the matched pair", "Do the 16 Keyhole frames around its startup peak look different from the negative's frames at the same time?"),
        (LATE_NEG, "late-window maximum", "Is the 312 µm depth after the derived exit (frames labelled Scanning Stopped) a real cavity or an end-of-track artefact?"),
        (B2EE, "persistent depth elevation after the first Conduction frame", "Is the elevated depth just after the first Conduction frame a cavity that the labels missed?"),
        (LATE_K, "late Keyhole at shallow depth", "Are its Keyhole frames (all after the 90 % cutoff, around the exit) consistent with a keyhole at 80–90 µm depth?"),
        (ALT_NEW, "alternating Keyhole/Conduction, short K", "Are the K→C→K switches (one frame interval each) physical alternation or label flicker?")]
    rows, frames = [], []
    for sid, role, question in cases:
        r = R.loc[sid]
        if sid in (MATCH_NEG, MATCH_POS):
            k = fm[(fm.sim_id == MATCH_POS) & (fm.code == "K")]
            br = _bracket_rows(sid, fm, "the positive's Keyhole window, same times in both runs", k.time_ms.min(), k.time_ms.max(), "")
            keys = [_nearest_frame(fm, sid, r.A_active_max_ms)]
        elif sid == LATE_NEG:
            br = _bracket_rows(sid, fm, "depth ≥ 300 µm episode, first to last monitor row", r.first_ge300_ms, r.last_ge300_ms, f"First Scanning Stopped frame at {r.first_SS_ms:.3f} ms")
            keys = [_nearest_frame(fm, sid, r.first_ge300_ms), _nearest_frame(fm, sid, r.max_depth_whole_ms)]
        elif sid == B2EE:
            br = _bracket_rows(sid, fm, "first Conduction frame to the persistent-depth event", r.first_C_ms, r.G3_event_ms, f"A maximum {r.A_active_max_um:.1f} µm at {r.A_active_max_ms:.3f} ms")
            keys = [_nearest_frame(fm, sid, r.A_active_max_ms), _nearest_frame(fm, sid, r.G3_event_ms)]
        elif sid == LATE_K:
            g = kr[kr.sim_id == sid]
            br = _bracket_rows(sid, fm, "Keyhole frames, first to last", g.start_ms.min(), g.end_ms.max(), f"{len(g)} Keyhole run; 90 % cutoff at {r.active_cutoff_ms:.3f} ms, derived exit at {r.derived_exit_ms:.3f} ms")
            keys = [int(g.start_pos.min()), int(g.end_pos.max())]
        else:
            g = sw[sw.sim_id == sid].sort_values("from_pos")
            br = _bracket_rows(sid, fm, "all K/C switches, first to last", g.from_ms.min(), g.to_ms.max(),
                               "Switches: " + "; ".join(f"{t.type.replace('_to_', '→')} frames {t.from_pos}→{t.to_pos} ({t.from_ms:.4f}→{t.to_ms:.4f} ms)" for t in g.itertuples()))
            keys = [int(g.from_pos.iloc[0]), int(g.to_pos.iloc[0])]
        rows.append({"H": short(sid), "sim_id": sid, "has_keyhole": int(r.has_keyhole_frozen), "role": role, "question": question, "VX_m_s": float(r.VX),
                     "collapsed_sequence": r.collapsed_sequence, "whole_max_um": float(r.max_depth_whole_um), "A_um": float(r.A_active_max_um),
                     "recording_end_ms": float(r.recording_end_ms), **{k: v for k, v in br.items() if k != "sim_id"}, "key_frames": ",".join(map(str, keys)),
                     "folder_url": f"{HF}/tree/{NEW_REV}/{sid}/frames"})
        for fr in keys:
            for view in ("front", "side", "top"):
                p = f"{sid}/frames/{view}/frame_{fr:05d}.png"
                t = fm[(fm.sim_id == sid) & (fm.frame_pos == fr)]
                frames.append({"H": short(sid), "sim_id": sid, "frame_idx": fr, "time_ms": float(t.time_ms.iloc[0]), "label": t.label_final.iloc[0], "view": view,
                               "repo_path": p, "url": f"{HF}/resolve/{NEW_REV}/{p}", "revision": NEW_REV})
    cs, fr = pd.DataFrame(rows), pd.DataFrame(frames)
    # frames.csv cross-check: frame_pos equals frame_idx and the image names match
    from src.week19_sources import local_file
    ok = []
    for sid, g in fr.groupby("sim_id"):
        fc = pd.read_csv(local_file(NEW_REV, f"{sid}/frames.csv")).set_index("frame_idx")
        for t in g.itertuples():
            ok.append(fc.loc[t.frame_idx, f"{t.view}_filename"] == t.repo_path.split("/", 1)[1])
    fr["frames_csv_name_matches"] = ok
    if verify:
        from huggingface_hub import HfApi
        info = HfApi().get_paths_info("ioandanielc/sph_v2", fr.repo_path.tolist(), repo_type="dataset", revision=NEW_REV)
        found = {i.path: getattr(i, "size", None) for i in info}
        fr["exists_at_revision"] = fr.repo_path.isin(found); fr["size_bytes"] = fr.repo_path.map(found)
    _w(cs, "ioan_cases.csv"); _w(fr, "ioan_case_frames.csv")
    return cs, fr


# ======================================================================================== pilot figures
def pilot_figures():
    fd = pd.read_csv(TAB / "fit_diagnostics.csv"); mt = pd.read_csv(TAB / "metrics.csv")
    paths = []
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    e = fd[fd.arm.isin(["WHOLE_E1_SHARED", "ACTIVE_E1_SHARED"])]
    off = {"WHOLE_E1_SHARED": -1.5, "ACTIVE_E1_SHARED": 1.5}
    for arm, g in e.groupby("arm"):
        for lr, mk in ((True, "o"), (False, "^")):
            h = g[g.late_negative_revealed.astype(bool) == lr]
            ax.scatter(h.budget + off[arm] + np.linspace(-0.6, 0.6, len(h)), h.u_um, s=22, marker=mk, facecolor=ARM_COLOR[arm] if lr else "none",
                       edgecolor=ARM_COLOR[arm], lw=0.9, label=f"{ARM_SHORT[arm]}: late negative {'paid' if lr else 'not paid'} ({len(h)})")
    ax.axhline(PULL_UM, color=MUTED, ls="--", lw=0.7); ax.text(111, PULL_UM + 3, "200 µm pull level", va="bottom", ha="right", fontsize=7, color=MUTED)
    ax.axhline(309.619080770828, color=MUTED, ls=":", lw=0.7); ax.text(111, 312.6, "historical max 309.6 µm (Week 18 adaptive runs)", va="bottom", ha="right", fontsize=7, color=MUTED)
    ax.axhline(UREF, color=MUTED, ls="-.", lw=0.6); ax.text(111, UREF + 3, "u_ref 111 µm", va="bottom", ha="right", fontsize=7, color=MUTED)
    ax.set_xticks(BUDGETS); ax.set_xlim(8, 112); ax.set_ylim(0, 385)
    ax.set_xlabel("paid simulations (shared label-blind path)"); ax.set_ylabel("learned threshold u (µm)")
    ax.set_title("E1 learned thresholds on the shared paths: no pull, with or without the late negative", loc="left", fontsize=8)
    ax.legend(fontsize=6.5, frameon=False, loc="upper left", ncol=2)
    paths.append(_save(fig, "pilot_fig1_learned_thresholds.png"))
    fig, axs = plt.subplots(1, 4, figsize=(11, 3.0), sharey=False)
    for ax, (m, lab) in zip(axs, (("BA", "balanced accuracy"), ("specificity_12neg", "specificity (12 negatives)"), ("sensitivity_shortK", "short-K sensitivity (10)"), ("q20_acc", "q20 accuracy (co-endpoint)"))):
        for j, arm in enumerate(["WHOLE_E1_SHARED", "ACTIVE_E1_SHARED", "G3_SHARED"]):
            g = mt[(mt.arm == arm) & (mt.metric == m) & (mt.scope == "mean_over_repeats") & (mt.threshold_mode == "learned")].sort_values("budget")
            x = np.arange(len(g)) + (j - 1) * 0.22
            ax.errorbar(x, g.estimate, yerr=[g.estimate - g.lo95, g.hi95 - g.estimate], fmt="o", ms=4, color=ARM_COLOR[arm], lw=0.9, capsize=2, label=ARM_SHORT[arm])
        ax.set_xticks(range(3)); ax.set_xticklabels([f"B{b}" for b in BUDGETS]); ax.set_title(lab, loc="left", fontsize=8); ax.set_ylim(0, 1.05)
    axs[0].legend(fontsize=7, frameon=False, loc="lower right")
    fig.text(0.01, -0.05, "Mean over repeats 1–2; whiskers: paired conditional bootstrap 95 % interval (2000 draws, simulations resampled within label strata). DEV, post-hoc.", fontsize=7, color=MUTED)
    fig.tight_layout()
    paths.append(_save(fig, "pilot_fig2_metrics_by_budget.png"))
    return paths


# ======================================================================================== item 6: timestep×DT audit
DT_FINDINGS = [
    ("src/week19_series.py", "172-182", "Week 19 audit (diagnostic)", "timestep × DT compared with time.dat",
     "Correct use: only to show that timestep × DT overstates monitor time (by the iterations per frame); never used as time.", "none"),
    ("src/week18_data_audit.py", "39", "Week 18 data audit", "DTr = DT · VX / LS",
     "DT is the frame interval, so DTr is frame spacing in spot-crossing units, not a solver time step. Numbers are unaffected.", "wording"),
    ("outputs/week18_independent_research/DATA_AUDIT.md", "14", "Week 18", "'Time-step rule differs: DT·VX/LS …'",
     "Should read 'frame-spacing rule'; values (0.075 OLD vs 0.108 NEW) stand.", "wording"),
    ("outputs/week18_independent_research/RESEARCH_LOG.md", "23-24", "Week 18", "'time-step rule DT·VX/LS …'", "Same wording point.", "wording"),
    ("outputs/week18_independent_research/RED_TEAM.md", "9", "Week 18", "'the time-step rule differs between OLD and NEW'", "Same wording point.", "wording"),
    ("notebooks/week_05/01_first_conduction_data_audit.ipynb", "cells 40-54, 68", "Week 5", "first-Conduction target = raw timestep",
     "Raw iteration count, explicitly 'not established as physical time'; DT only parsed. Not a ×DT error, but iteration units are not comparable across runs (iterations per frame: median 410 OLD, 567 NEW).", "caveat"),
    ("notebooks/week_05/02_first_conduction_gp_kernel_comparison.ipynb", "-", "Week 5", "GP on raw first-Conduction timestep", "Same caveat (iteration units).", "caveat"),
    ("notebooks/week_05/03_bug_initial_emptiness_ls_analysis.ipynb", "cells 5-34", "Week 5", "initial empty-like block width in raw timestep units", "Same caveat.", "caveat"),
    ("notebooks/week_05/04_matern32_optimizer_comparison.ipynb", "-", "Week 5", "GP on raw first-Conduction timestep", "Same caveat.", "caveat"),
    ("notebooks/week_05/05_ard_matern32_extension.ipynb", "cell 0", "Week 5", "'the target is a simulation timestep number, not physical time'", "Same caveat.", "caveat"),
    ("outputs/week5_01_first_conduction_data_audit … week5_05_ard_matern32_extension", "-", "Week 5", "outputs of the notebooks above", "Same caveat; MAE/RMSE are in timesteps.", "caveat"),
    ("docs/week5_first_conduction_gp_log.md", "33, 51, 190", "Week 5", "'raw timestep … not converted to physical time'", "Same caveat; already stated in the log.", "caveat"),
    ("docs/week5_gp_meeting_brief.md", "5", "Week 5", "'The response is not converted to physical time'", "Same caveat; already stated.", "caveat"),
]


def dt_audit():
    """Re-runs the searches behind the audit and stores the curated findings (no file is rewritten)."""
    pats = {"product_with_DT_in_code": r"(timestep|time_step|iteration|frame)[\w.()\[\]\"']*\s*\*\s*[\w.\[\"']*(DT|dt_nom)\b|\b(DT|dt_nom)[\w.()\[\]\"']*\s*\*\s*[\w.\[\"']*(timestep|iteration|frame)",
            "DT_field_use_in_code": r"\[\"DT\"\]|\['DT'\]|g\(s, \"DT\"\)|DT_token|DT_encoded|dt_nom"}
    hits = []
    for p in sorted((ROOT / "src").rglob("*.py")):
        if "_history" in p.parts or p.name == "week19_pilot_reports.py":       # skip this module's own search patterns
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            for k, rx in pats.items():
                if re.search(rx, line):
                    hits.append({"search": k, "path": str(p.relative_to(ROOT)).replace("\\", "/"), "line": i, "text": line.strip()[:160]})
    for p in sorted((ROOT / "notebooks").rglob("*.ipynb")):
        if "_history" in p.parts:
            continue
        nb = json.loads(p.read_text(encoding="utf-8"))
        for ci, c in enumerate(nb["cells"]):
            if c["cell_type"] != "code":
                continue
            for line in "".join(c["source"]).splitlines():
                if re.search(r"\bDT\b|DT_encoded|DT_token", line) and re.search(r"[*/]", line):
                    hits.append({"search": "DT_arithmetic_in_notebook", "path": str(p.relative_to(ROOT)).replace("\\", "/"), "line": f"cell {ci}", "text": line.strip()[:160]})
    for base in ("outputs", "docs"):
        for p in sorted((ROOT / base).rglob("*.md")):
            if "_history" in p.parts or "week19_temporal_regime_dev_pilot" in p.parts:
                continue
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if re.search(r"(?i)time-step rule|time step rule|DT·VX", line):
                    hits.append({"search": "time_step_wording_in_reports", "path": str(p.relative_to(ROOT)).replace("\\", "/"), "line": i, "text": line.strip()[:160]})
    for p in sorted((ROOT / "src").glob("*.py")):
        if p.name != "week19_pilot_reports.py" and "time.dat" in p.read_text(encoding="utf-8", errors="ignore"):
            hits.append({"search": "reads_monitor_time_dat", "path": str(p.relative_to(ROOT)).replace("\\", "/"), "line": "", "text": "physical time from monitor/time.dat"})
    _w(pd.DataFrame(hits), "timestep_dt_search_hits.csv")
    f = pd.DataFrame(DT_FINDINGS, columns=["path", "lines", "week", "what", "assessment", "class"])
    _w(f, "timestep_dt_usage.csv")
    return f, pd.DataFrame(hits)


# ======================================================================================== IOAN_SUMMARY.md
def case_markdown():
    cs = pd.read_csv(TAB / "ioan_cases.csv"); fr = pd.read_csv(TAB / "ioan_case_frames.csv")
    if not (fr.exists_at_revision.all() and fr.frames_csv_name_matches.all()):
        raise ValueError("an image link failed verification")
    out = []
    for i, c in enumerate(cs.itertuples(), 1):
        lab = "positive (has_keyhole = 1)" if c.has_keyhole else "negative (has_keyhole = 0)"
        out.append(f"**{i}. {c.H}**: {lab}, {c.role}; VX {c.VX_m_s:.3f} m/s; label sequence `{c.collapsed_sequence}`; "
                   f"whole-record max {c.whole_max_um:.1f} µm, A {c.A_um:.1f} µm.  ")
        out.append(f"Full ID: `{c.sim_id}`  ")
        note = f" {c.note}." if isinstance(c.note, str) and c.note else ""
        out.append(f"Bracket: {c.bracket}; frames {c.frame_first}–{c.frame_last}, {c.time_first_ms:.4f}–{c.time_last_ms:.4f} ms; labels {c.labels_in_bracket}.{note}  ")
        links = []
        for fi, g in fr[fr.sim_id == c.sim_id].groupby("frame_idx", sort=False):
            v = {r.view: r.url for r in g.itertuples()}
            links.append(f"frame {fi} ({g.time_ms.iloc[0]:.4f} ms, {g.label.iloc[0]}): [front]({v['front']}) · [side]({v['side']}) · [top]({v['top']})")
        out.append("Images: " + "; ".join(links) + f"; [all frames]({c.folder_url})  ")
        out.append(f"Question: {c.question}")
        out.append("")
    return "\n".join(out)


def write_ioan_summary():
    t = pd.read_csv(TAB / "descriptive_whole_vs_A_by_label.csv")
    dec = json.loads((OUT / "decision.json").read_text())["decision"]
    mt = pd.read_csv(TAB / "metrics.csv")
    g = lambda arm, m: float(mt[(mt.arm == arm) & (mt.metric == m) & (mt.budget == 40) & (mt.scope == "mean_over_repeats") & (mt.threshold_mode == "learned")].estimate.iloc[0])  # noqa: E731
    p = t[t.cohort.str.startswith("paired")].set_index(["campaign", "subset", "label", "score"])
    a = lambda c, s, l, sc: p.loc[(c, s, l, sc), "AUC"]  # noqa: E731
    fast = f"VX>{FAST_VX}"
    alt = [a("NEW", fast, l, sc) for l in ("K/(K+C)>=0.05", "K/(K+C)>=0.10") for sc in ("whole_max_um", "A_um")]
    cnt = dec["counts_B40_two_repeats"]
    ev = pd.read_csv(TAB / "evaluation.csv")
    u4 = ev[(ev.arm == "ACTIVE_E1_SHARED") & (ev.threshold_mode == "learned") & (ev.budget == 40) & ev.unresolved_fast_scan_negative]
    text = f"""# Keyhole→Conduction and the NEW depth/label mismatch: summary for Ioan

*Week 19, 10 October 2026. Everything below is observation (OBS) unless marked. Section 4 is a post-hoc, exploratory development check (DEV repeats only), not a confirmed result. No label, exclusion or historical result was changed.*

**Data.** All 541 eligible runs (405 OLD, 136 NEW): manual frame labels placed at their exact monitor time (`iter.dat` → `time.dat`; the folder `DT` is the frame interval, not the solver step) and melt-subset depth from `position-bounds_melt.dat`.

**1. Keyhole followed by only Conduction comes in two forms (Figure 1).**
- **Fast scans** (VX ≥ 0.85 m/s; 11 NEW, 10 OLD): a short Keyhole run right after Forming (median K/(F+C+K) 0.066 NEW, 0.043 OLD), ending near 0.47–0.48 ms; Conduction for the rest of the track.
- **Slow scans** (VX < 0.4; 12 NEW, 7 OLD): long Keyhole at about 300 µm, switching to Conduction 15–21 frames before the fixed 2.1 ms recording end, with the scan unfinished.
- Timing is almost the same in OLD and NEW. Alternation (C frames between K frames) occurs in 9 NEW and 13 OLD runs; each switch is known to one frame interval (about 7 µs).

**2. The matched fast-scan pair (Figure 2): similar inputs and depth trajectories, opposite recorded labels; the morphology difference has not been established.** *[corrected 2026-10-10]* H-b302fc6cbd is the negative and H-b7e3ed2e12 the positive. The positive's 16 Keyhole frames (0.395–0.471 ms) coincide with the same startup depth peak (112–116 µm) that the negative's frames label Forming/Conduction.

**3. The active window restores the depth ranking, except in fast scans (Figure 3, Table 1).** A is the maximum depth up to 90 % of the derived exit time (startup kept).
- **NEW overall:** AUC {a('NEW', 'all', 'has_keyhole', 'whole_max_um'):.3f} for the whole-record maximum vs {a('NEW', 'all', 'has_keyhole', 'A_um'):.3f} for A (135 runs).
- **NEW fast scans** (VX > {FAST_VX}, 23 runs): {a('NEW', fast, 'has_keyhole', 'whole_max_um'):.3f} vs {a('NEW', fast, 'has_keyhole', 'A_um'):.3f}. Labels redefined by K/(K+C) ≥ 5 % or ≥ 10 % give {min(alt):.2f}–{max(alt):.2f}, so changing the label's K-fraction cut does not remove the problem.
- **OLD fast scans** separate almost perfectly (98 runs, AUC {a('OLD', fast, 'has_keyhole', 'A_um'):.3f}).

**4. Small model check (exploratory, DEV only).**
- **Setup.** Each model was trained on the same 40 simulations per NEW fold, picked by a fixed space-filling rule that ignores labels, and then predicted the held-out runs.
- **Result.** A GP of A beat the same GP of the whole-record maximum: balanced accuracy {g('ACTIVE_E1_SHARED', 'BA'):.2f} vs {g('WHOLE_E1_SHARED', 'BA'):.2f}, with {cnt['ACTIVE_E1_SHARED']['true_negatives_of_24']} vs {cnt['WHOLE_E1_SHARED']['true_negatives_of_24']} of 24 negative predictions right. The binary GP classifier scored {g('G3_SHARED', 'BA'):.2f}.
- **Not fixed.** The four unresolved fast-scan negatives were still called Keyhole in {int(u4.pred_label.sum())} of {len(u4)} predictions. H-349225d53c, whose Keyhole frames all come after the 90 % cutoff, was missed by the A model in both repeats (the whole-record model caught it).

**What would help most.** Your reading of the six runs below: do the images show a cavity where depth is raised but the label says Conduction or Forming, or the reverse?

*[updated 2026-10-10]* The 30 linked images are now in [ioan_gallery/GALLERY.md](ioan_gallery/GALLERY.md) as contact sheets without labels; the labels are in a separate key. A usability check (no morphology judgement) found 22 usable, 6 nearly empty, 1 blank and 1 unclear. Meeting brief: [IOAN_MEETING_BRIEF.md](IOAN_MEETING_BRIEF.md).

![Figure 1](figures/ioan_fig1_two_K_to_C_forms.png)

*Figure 1. The two K→C forms (NEW examples, chosen as the runs closest to their subgroup's median K fraction).*

![Figure 2](figures/ioan_fig2_matched_pair.png)

*Figure 2. The matched fast-scan pair.*

![Figure 3](figures/ioan_fig3_A_vs_VX.png)

*Figure 3. A against scan speed, coloured by the benchmark label (left) and by K/(K+C) (right).*

**Table 1. How well whole-record max depth and A separate three label definitions.** Values are AUC and the descriptive same-population oracle BA. Both depths are computed on the same runs (A available). `has_keyhole` is the unchanged benchmark label; the K/(K+C) labels are descriptive alternatives only. "Undefined ratio" counts runs with no K or C frame; "A missing" counts the one NEW run whose bounds and time rows do not align. Fast-scan rows are exploratory. Full table with whole-record max on all runs: `tables/descriptive_whole_vs_A_by_label.csv`.

{descriptive_markdown(t)}

## Six runs to inspect

All links are at the pinned NEW revision `{NEW_REV}`. Each link was checked to exist there (`tables/ioan_case_frames.csv`). Frame numbers are `frame_idx` in `frames.csv`, and times are monitor times.

{case_markdown()}
*[added 2026-10-10]* Case 1's linked frame 82 is 0.18 µs after that run's depth maximum. It follows a sharp drop in monitored depth (114.3 µm at frame 81 → 89.1 µm at frame 82). The near-peak frame 81 is not among the linked images.
"""
    (OUT / "IOAN_SUMMARY.md").write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    import sys
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step in ("descriptive", "all"):
        print(descriptive_markdown(descriptive()))
    if step in ("ioan", "all"):
        print(ioan_figures()); print(ioan_cases()[0].to_string())
    if step in ("pilotfigs", "all"):
        print(pilot_figures())
    if step in ("dtaudit", "all"):
        f, h = dt_audit(); print(h.to_string())
    if step in ("summary", "all"):
        write_ioan_summary()
