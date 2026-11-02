"""Finalization figures (2026-11-02): the main C1C result drawn from its FROZEN exports. Nothing is refitted or recomputed
beyond means and cluster-bootstrap intervals of the exported per-learner values, and every plotted summary is checked
against the numbers the C1C records report (docs/final/figures/FIGURE_CHECKS.json); a mismatch stops the script.

Inputs (read-only): outputs/research_campaign_20261026/opus_c1_confirmation/evaluation/{main_d,main_ai,main_ei}.csv.gz
  main_d  : BA per learner and budget (systems C1_own = C1 + margin, A_own = HA_LEAN + margin; condition STD)
  main_ai : per-learner window summaries (B8_B24, B28_B60, ...)
  main_ei : per-learner target attainment (first, confirmed_b, spend, attained, ...)
Outputs: docs/final/figures/fig_final_{1,2,3}_*.{png,pdf}, matching *_data.csv and FIGURE_CHECKS.json.
    python -m src.fin_figures
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "outputs" / "research_campaign_20261026" / "opus_c1_confirmation" / "evaluation"
OUT = ROOT / "docs" / "final" / "figures"
SYS = {"C1_own": "C1 + margin", "A_own": "HA_LEAN + margin (reference)"}
COLOR = {"C1_own": "#2a78d6", "A_own": "#eb6834"}          # dataviz categorical slots 1-2, validated on the light surface
INK, INK2, MUTED, GRID, BASE, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
BOOT, SEED = 4000, 20261102
# Reported values (DECISION_C1C.md §1-3, evaluation/RESULTS_C1C.md §1.1): the figures must reproduce them.
REPORTED = {"early_diff": 0.0053, "late_diff": -0.0006, "ba60_C1": 0.9568, "ba60_A": 0.9569,
            "attain095": {"C1_own": {16: 0.390, 24: 0.575, 60: 0.838}, "A_own": {16: 0.335, 24: 0.532, 60: 0.797}}}


def boot_ci(x, rng):
    """Percentile 95 % interval of the mean over clusters (rows of x = clusters)."""
    x = np.asarray(x, float)
    idx = rng.integers(0, len(x), size=(BOOT, len(x)))
    m = x[idx].mean(axis=1)
    return np.percentile(m, [2.5, 97.5], axis=0)


def style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(BASE)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(True, axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def windows(ax, ymax):
    for (a, b, lab) in ((8, 24, "early B8–B24"), (28, 60, "late B28–B60")):
        ax.axvspan(a, b, color="#f0efec", zorder=0, linewidth=0)
        ax.text((a + b) / 2, ymax, lab, ha="center", va="top", fontsize=8.5, color=MUTED)


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    d = pd.read_csv(EV / "main_d.csv.gz")
    d = d[(d.condition == "STD") & d.system.isin(SYS)]
    ai = pd.read_csv(EV / "main_ai.csv.gz")
    ei = pd.read_csv(EV / "main_ei.csv.gz")
    checks = {}

    # --- checks against the reported numbers --------------------------------------------------------------------------
    for win, key in (("B8_B24", "early_diff"), ("B28_B60", "late_diff")):
        lo, hi = (8, 24) if win == "B8_B24" else (28, 60)
        own = d[(d.budget >= lo) & (d.budget <= hi)].groupby(["system", "cluster", "learner"]).BA.mean().unstack(0)
        exp = ai[ai.window == win].pivot_table(index=["cluster", "learner"], columns="system", values="BA")
        same = {s: float(np.abs(own[s] - exp.loc[own.index, s]).max()) for s in SYS}
        diff = float((own["C1_own"] - own["A_own"]).mean())
        checks[win] = {"max_abs_window_mean_vs_main_ai": same, "C1_minus_A": round(diff, 6), "reported": REPORTED[key],
                       "ok": bool(max(same.values()) < 1e-9 and abs(diff - REPORTED[key]) < 0.00005)}
    b60 = d[d.budget == 60].groupby("system").BA.mean()
    checks["BA_at_60"] = {"C1_own": round(float(b60["C1_own"]), 4), "A_own": round(float(b60["A_own"]), 4),
                          "reported": [REPORTED["ba60_C1"], REPORTED["ba60_A"]],
                          "ok": bool(abs(b60["C1_own"] - REPORTED["ba60_C1"]) < 5e-5 and abs(b60["A_own"] - REPORTED["ba60_A"]) < 5e-5)}
    t95 = ei[(ei.target == 0.95) & ei.system.isin(SYS)].copy()
    # spend = paid simulations used to reach AND confirm the target (confirmation runs counted); this is the definition
    # behind the reported cumulative attainment (confirmed_b alone gives higher shares at b = 16 / 24)
    t95["cb"] = np.where(t95.attained.astype(bool), t95.spend, np.inf)
    att = {}
    for s in SYS:
        x = t95[t95.system == s]
        att[s] = {b: round(float((x.cb <= b).mean()), 3) for b in (16, 24, 60)}
    checks["attainment_0.95_spend_within_b"] = {"computed": att, "reported": REPORTED["attain095"],
                                               "ok": bool(all(abs(att[s][b] - REPORTED["attain095"][s][b]) < 0.0015 for s in SYS for b in (16, 24, 60)))}
    checks["all_ok"] = bool(all(v["ok"] for v in checks.values() if isinstance(v, dict) and "ok" in v))
    (OUT / "FIGURE_CHECKS.json").write_text(json.dumps(checks, indent=1), encoding="utf-8")
    if not checks["all_ok"]:
        raise SystemExit(f"figure checks failed: {json.dumps(checks, indent=1)}")

    # --- per-cluster curves -------------------------------------------------------------------------------------------
    cm = d.groupby(["system", "cluster", "budget"]).BA.mean().unstack("budget")      # rows (system, cluster)
    budgets = cm.columns.to_numpy()
    rows = []
    for s in SYS:
        x = cm.loc[s].to_numpy()
        lo, hi = boot_ci(x, rng)
        for j, b in enumerate(budgets):
            rows.append({"series": SYS[s], "budget": int(b), "mean_BA": x[:, j].mean(), "ci_lo": lo[j], "ci_hi": hi[j]})
    curves = pd.DataFrame(rows)
    curves.to_csv(OUT / "fig_final_1_learning_curves_data.csv", index=False, float_format="%.6f")
    dx = cm.loc["C1_own"].to_numpy() - cm.loc["A_own"].to_numpy()
    dlo, dhi = boot_ci(dx, rng)
    diff = pd.DataFrame({"budget": budgets.astype(int), "mean_diff_BA": dx.mean(0), "ci_lo": dlo, "ci_hi": dhi})
    diff.to_csv(OUT / "fig_final_2_paired_difference_data.csv", index=False, float_format="%.6f")
    bgrid = np.arange(8, 61)
    attr = []
    for s in SYS:
        x = t95[t95.system == s]
        for b in bgrid:
            attr.append({"series": SYS[s], "budget": int(b), "share_reached_and_confirmed_0.95": float((x.cb <= b).mean())})
    attain = pd.DataFrame(attr)
    attain.to_csv(OUT / "fig_final_3_attainment_095_data.csv", index=False, float_format="%.6f")

    caption_src = "Source: C1C, 80 fresh STD repeats (203–282), 400 learners; frozen exports, no refit."

    # Figure 1: learning curves
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=200)
    fig.patch.set_facecolor(SURFACE); style(ax)
    ylo, yhi = 0.86, 0.965
    windows(ax, yhi - 0.001)
    for s in ("A_own", "C1_own"):
        c = curves[curves.series == SYS[s]]
        ax.fill_between(c.budget, c.ci_lo, c.ci_hi, color=COLOR[s], alpha=0.16, linewidth=0)
        ax.plot(c.budget, c.mean_BA, color=COLOR[s], linewidth=1.6, label=SYS[s])
    ax.set_xlim(8, 60); ax.set_ylim(ylo, yhi)
    ax.set_xlabel("paid simulations (budget b, startup of 8 included)", color=INK2, fontsize=9.5)
    ax.set_ylabel("balanced accuracy on the held-out fold", color=INK2, fontsize=9.5)
    ax.set_title("C1 + margin learns the Keyhole boundary earlier than the reference", color=INK, fontsize=11, loc="left")
    h, l = ax.get_legend_handles_labels()
    leg = ax.legend(h[::-1], l[::-1], frameon=False, fontsize=9, loc="lower right")      # C1 first
    for t in leg.get_texts():
        t.set_color(INK)
    fig.text(0.01, 0.005, caption_src + " Bands: 95 % cluster bootstrap.", fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"fig_final_1_learning_curves.{ext}", facecolor=SURFACE)
    plt.close(fig)

    # Figure 2: paired difference
    fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=200)
    fig.patch.set_facecolor(SURFACE); style(ax)
    ylo = min(-0.005, float(diff.ci_lo.min()) - 0.001)
    yhi = max(0.02, float(diff.ci_hi.max()) + 0.004)
    windows(ax, yhi - 0.0005)
    ax.axhline(0, color=BASE, linewidth=1.0)
    ax.fill_between(diff.budget, diff.ci_lo, diff.ci_hi, color=COLOR["C1_own"], alpha=0.16, linewidth=0)
    ax.plot(diff.budget, diff.mean_diff_BA, color=COLOR["C1_own"], linewidth=1.6, label="C1 + margin − HA_LEAN + margin")
    ax.text(18.5, 0.0125, "early ΔBA-AULC\n+0.0053 [+0.0039, +0.0068]", ha="center", va="bottom", fontsize=8.5, color=INK)
    ax.text(44, 0.0055, "late ΔBA-AULC\n−0.0006 [−0.0013, +0.0002]", ha="center", va="bottom", fontsize=8.5, color=INK)
    ax.set_xlim(8, 60); ax.set_ylim(ylo, yhi)
    ax.set_xlabel("paid simulations (budget b)", color=INK2, fontsize=9.5)
    ax.set_ylabel("ΔBA, C1 − reference\n(paired by repeat)", color=INK2, fontsize=9.5)
    ax.set_title("The gain is early; late performance is preserved", color=INK, fontsize=11, loc="left")
    fig.text(0.01, 0.005, caption_src + " Windows: DECISION_C1C.md.", fontsize=7.0, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"fig_final_2_paired_difference.{ext}", facecolor=SURFACE)
    plt.close(fig)

    # Figure 3: cumulative attainment of BA 0.95
    fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=200)
    fig.patch.set_facecolor(SURFACE); style(ax)
    for s in ("A_own", "C1_own"):
        a = attain[attain.series == SYS[s]]
        ax.step(a.budget, a["share_reached_and_confirmed_0.95"], where="post", color=COLOR[s], linewidth=1.6, label=SYS[s])
    for b, y, ha, dx in ((16, 0.95, "left", 0.5), (24, 0.88, "left", 0.5), (60, 0.95, "right", -0.5)):
        ax.axvline(b, color=GRID, linewidth=0.8, zorder=0)
        ax.text(b + dx, y, f"b = {b}: C1 {att['C1_own'][b]:.3f}, reference {att['A_own'][b]:.3f}", fontsize=8, color=INK2, ha=ha, va="center")
    ax.set_xlim(8, 60); ax.set_ylim(0, 1)
    ax.set_xlabel("paid simulations (budget b)", color=INK2, fontsize=9.5)
    ax.set_ylabel("share of learners that reached and\nconfirmed BA ≥ 0.95 within b simulations", color=INK2, fontsize=9.5)
    ax.set_title("More learners reach BA 0.95, and sooner", color=INK, fontsize=11, loc="left")
    h, l = ax.get_legend_handles_labels()
    leg = ax.legend(h[::-1], l[::-1], frameon=False, fontsize=9, loc="lower right")      # C1 first
    for t in leg.get_texts():
        t.set_color(INK)
    fig.text(0.01, 0.005, caption_src + " Sustaining 0.95 was not improved (C126).", fontsize=7.0, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"fig_final_3_attainment_095.{ext}", facecolor=SURFACE)
    plt.close(fig)
    print(json.dumps(checks, indent=1))


if __name__ == "__main__":
    main()
