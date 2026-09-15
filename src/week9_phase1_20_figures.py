"""Week 9 Phase 1.20 — figures for the acquisition search and its confirmation."""
from __future__ import annotations

import argparse
import gzip
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_20_acquisition_search as search

FIG = search.OUTPUT / "figures"
INK, MUTED, BLUE, RED, GREEN, GREY = "#1c1c1c", "#5d5d5d", "#2e86c1", "#c0392b", "#117733", "#9a9a9a"


def curves(policy: str, repeats, subset="B1_q20", metric="accuracy") -> pd.DataFrame:
    m = search.load_metrics(policy, repeats)
    return m[m.subset == subset].pivot_table(index="budget", columns="run_id", values=metric)


def repeat_block_band(diff: pd.DataFrame, repeat_of: dict, key: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    blocks = diff.T.groupby(lambda r: repeat_of[r]).mean().T.to_numpy()        # budgets x blocks
    rng = np.random.default_rng(p13.seed_u32("fig-band", key))
    idx = rng.integers(0, blocks.shape[1], size=(4000, blocks.shape[1]))
    boot = blocks[:, idx].mean(axis=2)
    return blocks.mean(axis=1), np.quantile(boot, 0.025, axis=1), np.quantile(boot, 0.975, axis=1)


def fig_leaderboard() -> None:
    table = pd.read_csv(search.OUTPUT / "development_leaderboard.csv")
    table = table[table.policy != "margin"].copy()
    for w in ("16_80", "16_40"):
        lo_hi = table[f"ci_{w}"].str.strip("[]").str.split(",", expand=True).astype(float)
        table[f"lo_{w}"], table[f"hi_{w}"] = lo_hi[0], lo_hi[1]
    table = table.sort_values("d_16_80")
    fig, axes = plt.subplots(1, 2, figsize=(15, 0.33 * len(table) + 2), sharey=True)
    y = np.arange(len(table))
    for ax, w, title in zip(axes, ("16_80", "16_40"), ("q20 accuracy AULC 16-80", "q20 accuracy AULC 16-40")):
        for yy, (_, r) in zip(y, table.iterrows()):
            leaky = r.policy.startswith("LEAKY_")
            clear = r[f"lo_{w}"] > 0 or r[f"hi_{w}"] < 0
            color = GREY if leaky else (GREEN if clear and r[f"d_{w}"] > 0 else RED if clear else MUTED)
            ax.plot([r[f"lo_{w}"], r[f"hi_{w}"]], [yy, yy], color=color, lw=2)
            ax.plot(r[f"d_{w}"], yy, "o", color=color, ms=5, mfc="white" if leaky else color)
        ax.axvline(0, color=INK, lw=1)
        ax.set_title(f"{title}\n(difference vs M3 margin, development repeats 1-10)", fontsize=11)
        ax.grid(axis="x", alpha=0.3)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(table.policy, fontsize=8.5)
    fig.suptitle("Figure 1 - every screened acquisition rule (open grey = LEAKY diagnostics, never candidates)",
                 fontsize=12.5)
    fig.tight_layout()
    fig.savefig(FIG / "01_development_leaderboard.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_confirmation(finalist: str, label: str) -> None:
    population, specs, _ = search.load_inputs()
    repeat_of = {s.run_id: s.repeat for s in specs}
    reps = search.CONFIRMATION
    base, fin = curves("margin", reps), curves(finalist, reps)
    fin = fin[base.columns]
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.2))
    axes[0].plot(base.index, base.mean(axis=1), color=GREY, lw=2.2, label="M3 margin (incumbent)")
    axes[0].plot(fin.index, fin.mean(axis=1), color=BLUE, lw=2.4, label=label)
    axes[0].axhline(0.8565, color=RED, ls="--", lw=1.2, label="M3 with all 324 labels (ceiling)")
    axes[0].set_xlabel("simulations queried")
    axes[0].set_ylabel("Fold-B1-q20 accuracy")
    axes[0].set_title(f"q20 learning curves, confirmation set ({base.shape[1]} runs never used for design)", fontsize=11)
    axes[0].legend(fontsize=9.5, loc="lower right")
    axes[0].grid(alpha=0.3)
    mean, lo, hi = repeat_block_band(fin - base, repeat_of, finalist)
    axes[1].fill_between(base.index, lo, hi, color=BLUE, alpha=0.2, label="95% repeat-block bootstrap band")
    axes[1].plot(base.index, mean, color=BLUE, lw=2.2, label=f"{label} minus margin")
    axes[1].axhline(0, color=INK, lw=1)
    axes[1].axvline(40, color=MUTED, ls=":", lw=1.2)
    axes[1].text(40.5, axes[1].get_ylim()[1] * 0.9 if axes[1].get_ylim()[1] > 0 else 0.01,
                 "switch: coverage -> consistency", fontsize=9, color=MUTED)
    axes[1].set_xlabel("simulations queried")
    axes[1].set_ylabel("q20 accuracy difference")
    axes[1].set_title("paired difference per budget", fontsize=11)
    axes[1].legend(fontsize=9.5)
    axes[1].grid(alpha=0.3)
    fig.suptitle(f"Figure 2 - confirmation of {label}", fontsize=12.5)
    fig.tight_layout()
    fig.savefig(FIG / f"02_confirmation_{finalist}.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_mechanism(finalist: str) -> None:
    population, specs, _ = search.load_inputs()
    arrays = search.build_arrays(population)
    reps = search.CONFIRMATION
    fig, axes = plt.subplots(1, 3, figsize=(17, 4.8))
    for policy, color, name in (("margin", GREY, "margin"), (finalist, BLUE, finalist)):
        m = search.load_metrics(policy, reps)
        q = m[m.subset == "B1_q20"].groupby("budget")[["false_positive", "false_negative"]].mean()
        axes[0].plot(q.index, q.false_positive, color=color, lw=2.2, label=f"{name}: false positives")
        axes[0].plot(q.index, q.false_negative, color=color, lw=1.6, ls="--", label=f"{name}: false negatives")
        separable, misfit_share = {}, {}
        for path in sorted((search.CHECKPOINTS / policy).glob("*.json.gz")):
            payload = json.loads(gzip.decompress(path.read_bytes()).decode())
            if payload["metrics"][0]["repeat"] not in set(reps):
                continue
            queried = np.asarray(payload["queried_indices"])
            for b in range(16, 41, 2):
                lab, lh = arrays.labels[queried[:b]], arrays.logh[queried[:b]]
                separable.setdefault(b, []).append(lh[lab == 0].max() < lh[lab == 1].min())
        axes[1].plot(list(separable), [np.mean(v) for v in separable.values()], color=color, lw=2.2, label=name)
    axes[0].set_title("q20 errors per fold (17 rows): only false positives are reducible", fontsize=10.5)
    axes[0].set_xlabel("simulations queried")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.3)
    axes[1].set_title("share of runs whose queried labels are still\nseparable in log h (M3 = hard step)", fontsize=10.5)
    axes[1].set_xlabel("simulations queried")
    axes[1].legend(fontsize=9)
    axes[1].grid(alpha=0.3)
    board = pd.read_csv(search.OUTPUT / "development_leaderboard.csv").set_index("policy")
    conf_late = float((search.window_aulc(search.load_metrics(finalist, reps), 41, 80)
                       - search.window_aulc(search.load_metrics("margin", reps), 41, 80)).mean())
    labels = ["LEAKY: rows nearest an opposite\nlabel (development)", "misfit-avoiding late phase\n(development)",
              "misfit-avoiding late phase\n(CONFIRMATION)"]
    late = [board.loc["LEAKY_b1_nearest", "d_41_80"], board.loc["cov_then_misfit_B40", "d_41_80"], conf_late]
    axes[2].barh(labels, late, color=[RED, GREEN, BLUE])
    axes[2].axvline(0, color=INK, lw=1)
    axes[2].set_title("late window 41-80: conflicting labels hurt M3;\nthe avoidance gain did NOT replicate", fontsize=10.5)
    axes[2].set_xlabel("q20 accuracy AULC 41-80, difference vs margin")
    axes[2].grid(axis="x", alpha=0.3)
    fig.suptitle("Figure 3 - the two mechanisms behind the result", fontsize=12.5)
    fig.tight_layout()
    fig.savefig(FIG / "03_mechanisms.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--finalist", required=True)
    parser.add_argument("--label", default="CCM")
    args = parser.parse_args()
    FIG.mkdir(parents=True, exist_ok=True)
    fig_leaderboard()
    fig_confirmation(args.finalist, args.label)
    fig_mechanism(args.finalist)
    print("figures written to", FIG)


if __name__ == "__main__":
    main()
