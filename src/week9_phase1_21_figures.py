"""Week 9 Phase 1.21 — learning curves, paired differences and POST-HOC mechanism checks.

The mechanism quantities explain; they never feed the pre-registered verdict.
"""
from __future__ import annotations

import gzip
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import distance
from sklearn.preprocessing import StandardScaler

from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_20_acquisition_search as search
from src import week9_phase1_21_analysis as ana
from src import week9_phase1_21_simplification_replication as rep

FIG = rep.OUTPUT / "figures"
COLOR = {rep.CONTROL: "#8c8c8c", rep.CANDIDATE_A: "#1f6fb4", "cov_then_misfit_B40": "#e08a1e",
         rep.CANDIDATE_B: "#117733", "early8__cov_then_misfit_B40": "#b0413e"}
LABEL = {rep.CONTROL: "M3 margin (control)", rep.CANDIDATE_A: "A: coverage -> margin",
         "cov_then_misfit_B40": "old CCM (coverage -> misfit-avoiding margin)",
         rep.CANDIDATE_B: "B: 8 maximin + coverage -> margin", "early8__cov_then_misfit_B40": "old early8 + CCM"}


def payloads(policy: str) -> list[dict]:
    out = []
    for path in sorted((rep.CHECKPOINTS / policy).glob("*.json.gz")):
        payload = json.loads(gzip.decompress(path.read_bytes()).decode())
        if payload["metrics"][0]["repeat"] in set(rep.REPLICATION_REPEATS):
            out.append(payload)
    return out


def curves(metrics: pd.DataFrame, subset="B1_q20", metric="accuracy") -> pd.DataFrame:
    return metrics[metrics.subset == subset].pivot_table(index="budget", columns="run_id", values=metric)


def band_of(diff: pd.DataFrame, key: str):
    repeat = {r: int(r.split("__r")[1].split("_")[0]) for r in diff.columns}
    blocks = diff.T.groupby(repeat).mean().T.to_numpy()
    rng = np.random.default_rng(p13.seed_u32("phase1_21-figband", key))
    boot = blocks[:, rng.integers(0, blocks.shape[1], size=(4000, blocks.shape[1]))].mean(axis=2)
    return blocks.mean(axis=1), np.quantile(boot, 0.025, axis=1), np.quantile(boot, 0.975, axis=1)


def fig_curves(metrics: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.3), sharey=True)
    for ax, group, title in ((axes[0], (rep.CONTROL, rep.CANDIDATE_A, "cov_then_misfit_B40"),
                              "frozen 16-point seed (pure acquisition)"),
                             (axes[1], (rep.CONTROL, rep.CANDIDATE_B, "early8__cov_then_misfit_B40"),
                              "earlier active start (8 maximin points)")):
        for p in group:
            c = curves(metrics[p]).mean(axis=1)
            ax.plot(c.index, c, color=COLOR[p], lw=2.4 if p in (rep.CANDIDATE_A, rep.CANDIDATE_B) else 1.8,
                    ls="--" if p in rep.REFERENCES else "-", label=LABEL[p])
        ax.axvline(40, color="#555", ls=":", lw=1)
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("simulations queried")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=9, loc="lower right")
    axes[0].set_ylabel("Fold-B1-q20 accuracy (mean of 300 outer CV runs)")
    fig.suptitle("Figure 1 - learning curves on untouched internal replication partitions (repeats 61-120)",
                 fontsize=12.5)
    fig.tight_layout()
    fig.savefig(FIG / "01_learning_curves.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_paired(metrics: dict) -> None:
    base = curves(metrics[rep.CONTROL])
    fig, axes = plt.subplots(1, 3, figsize=(19, 5.2))
    for ax, group, title in ((axes[0], (rep.CANDIDATE_A, "cov_then_misfit_B40"), "minus margin, frozen seed"),
                             (axes[1], (rep.CANDIDATE_B, "early8__cov_then_misfit_B40"), "minus margin, early start")):
        for p in group:
            d = curves(metrics[p])[base.columns] - base
            m, lo, hi = band_of(d, p)
            ax.fill_between(base.index, lo, hi, color=COLOR[p], alpha=0.18)
            ax.plot(base.index, m, color=COLOR[p], lw=2.2, ls="--" if p in rep.REFERENCES else "-", label=LABEL[p])
        ax.axhline(0, color="black", lw=1)
        ax.axvline(40, color="#555", ls=":", lw=1)
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("simulations queried")
        ax.set_ylabel("q20 accuracy difference (95% repeat-block band)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=9)
    for cand, ref in ana.PAIRS.items():
        d = curves(metrics[cand]) - curves(metrics[ref])[curves(metrics[cand]).columns]
        m, lo, hi = band_of(d, f"{cand}-{ref}")
        axes[2].fill_between(d.index, lo, hi, color=COLOR[cand], alpha=0.18)
        axes[2].plot(d.index, m, color=COLOR[cand], lw=2.2, label=f"{LABEL[cand]}  minus  {LABEL[ref]}")
    axes[2].axhline(0, color="black", lw=1)
    axes[2].axvline(40, color="#555", ls=":", lw=1)
    axes[2].set_title("is the misfit component needed? (simple minus old CCM)", fontsize=11)
    axes[2].set_xlabel("simulations queried")
    axes[2].grid(alpha=0.3)
    axes[2].legend(fontsize=8.5)
    fig.suptitle("Figure 2 - paired differences per budget", fontsize=12.5)
    fig.tight_layout()
    fig.savefig(FIG / "02_paired_differences.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def mechanism(metrics: dict) -> pd.DataFrame:
    population, specs = rep.load_all_specs()
    arrays = search.build_arrays(population)
    spec_of = {s.run_id: s for s in specs}
    margin_paths = {p["run_id"]: p["queried_indices"] for p in payloads(rep.CONTROL)}
    rows, positions = [], []
    for policy in (rep.CONTROL, rep.CANDIDATE_A, rep.CANDIDATE_B, *rep.REFERENCES):
        for pay in payloads(policy):
            spec = spec_of[pay["run_id"]]
            train = np.asarray(spec.train_indices, dtype=int)
            xs = StandardScaler().fit(arrays.x4[train]).transform(arrays.x4)
            q = np.asarray(pay["queried_indices"])
            rec = {"policy": policy, "run_id": pay["run_id"]}
            for b in (24, 40, 80):
                d = distance.cdist(xs[q[:b]], xs[q[:b]])
                np.fill_diagonal(d, np.inf)
                rec[f"nn_distance_B{b}"] = float(d.min(axis=1).mean())
                rec[f"jaccard_vs_margin_B{b}"] = len(set(q[:b]) & set(margin_paths[pay["run_id"]][:b])) / len(
                    set(q[:b]) | set(margin_paths[pay["run_id"]][:b]))
            steps = pd.DataFrame(pay["steps"])
            early = steps[(steps.budget >= 16) & (steps.budget < 40)]
            late = steps[steps.budget >= 40]
            rec["differs_from_margin_B16_39"] = float((early.chosen != early.margin_choice).mean())
            rec["differs_from_margin_B40_79"] = float((late.chosen != late.margin_choice).mean())
            rec["chosen_in_band_B16_39"] = float(early.chosen_in_band.mean())
            for b in (16, 20, 24, 28, 32):
                row = steps[steps.budget == b]
                rec[f"separable_B{b}"] = float(row.separable.iloc[0]) if len(row) else np.nan
            rows.append(rec)
            for _, s in early.iterrows():
                pad = max(0.05, 0.25 * (s.band_hi - s.band_lo))
                width = (s.band_hi + pad) - (s.band_lo - pad)
                positions.append({"policy": policy, "relative_position": (s.chosen_logh - (s.band_lo - pad)) / width})
    frame = pd.DataFrame(rows)
    frame.to_csv(rep.OUTPUT / "mechanism_per_run.csv", index=False)
    summary = frame.drop(columns="run_id").groupby("policy").mean()
    summary.to_csv(rep.OUTPUT / "mechanism_summary.csv")
    pd.DataFrame(positions).to_csv(rep.OUTPUT / "mechanism_band_positions.csv.gz", index=False)

    fig, axes = plt.subplots(2, 3, figsize=(18, 9.5))
    for p in (rep.CONTROL, rep.CANDIDATE_A, rep.CANDIDATE_B):
        m = metrics[p][metrics[p].subset == "B1_q20"].groupby("budget")[["false_positive", "false_negative"]].mean()
        axes[0, 0].plot(m.index, m.false_positive, color=COLOR[p], lw=2.2, label=LABEL[p])
        axes[0, 1].plot(m.index, m.false_negative, color=COLOR[p], lw=2.2, label=LABEL[p])
    rows_q20 = metrics[rep.CONTROL][metrics[rep.CONTROL].subset == "B1_q20"].row_count.mean()
    axes[0, 0].set_title(f"q20 false positives per outer run (mean {rows_q20:.1f} test rows)")
    axes[0, 1].set_title(f"q20 false negatives per outer run (mean {rows_q20:.1f} test rows)")
    for ax in axes[0, :2]:
        ax.set_xlabel("simulations queried")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8.5)
    sep = summary[[f"separable_B{b}" for b in (16, 20, 24, 28, 32)]]
    for p in (rep.CONTROL, rep.CANDIDATE_A, rep.CANDIDATE_B):             # references share A/B's path before B40
        axes[0, 2].plot((16, 20, 24, 28, 32), sep.loc[p].to_numpy(), "o-", color=COLOR[p], lw=2, label=LABEL[p])
    axes[0, 2].set_title("share of runs whose queried labels are\nstill separable in log h")
    axes[0, 2].set_xlabel("simulations queried")
    axes[0, 2].grid(alpha=0.3)
    axes[0, 2].legend(fontsize=8.5)
    x = np.arange(3)
    for i, p in enumerate((rep.CONTROL, rep.CANDIDATE_A, rep.CANDIDATE_B)):
        axes[1, 0].bar(x + (i - 1) * 0.27, [summary.loc[p, f"nn_distance_B{b}"] for b in (24, 40, 80)], 0.27,
                       color=COLOR[p], label=LABEL[p])
    axes[1, 0].set_xticks(x)
    axes[1, 0].set_xticklabels(["B24", "B40", "B80"])
    axes[1, 0].set_title("coverage: mean nearest-neighbour distance\nbetween queried points (standardised x)")
    axes[1, 0].legend(fontsize=8.5)
    axes[1, 0].grid(axis="y", alpha=0.3)
    pos = pd.DataFrame(positions)
    for p in (rep.CONTROL, rep.CANDIDATE_A):
        v = pos[pos.policy == p].relative_position.clip(-0.5, 1.5)
        axes[1, 1].hist(v, bins=40, range=(-0.5, 1.5), density=True, histtype="step", lw=2, color=COLOR[p], label=LABEL[p])
    axes[1, 1].axvspan(0, 1, color="#dddddd", alpha=0.4, lw=0)
    axes[1, 1].set_title("where B16-39 queries fall relative to the\nlabel-estimated band (0-1 = padded band)")
    axes[1, 1].set_xlabel("relative log-h position")
    axes[1, 1].legend(fontsize=8.5)
    group = (rep.CANDIDATE_A, "cov_then_misfit_B40", rep.CANDIDATE_B, "early8__cov_then_misfit_B40")
    short = {rep.CANDIDATE_A: "A", "cov_then_misfit_B40": "old CCM", rep.CANDIDATE_B: "B",
             "early8__cov_then_misfit_B40": "old early8\n+ CCM"}
    x = np.arange(len(group))
    for j, (col, hatch, name) in enumerate((("differs_from_margin_B16_39", "", "B16-39 (coverage phase)"),
                                            ("differs_from_margin_B40_79", "//", "B40-79 (late phase)"))):
        axes[1, 2].bar(x + (j - 0.5) * 0.38, [summary.loc[p, col] for p in group], 0.38, hatch=hatch,
                       color=[COLOR[p] for p in group], edgecolor="black", lw=0.6, label=name)
    axes[1, 2].set_xticks(x)
    axes[1, 2].set_xticklabels([short[p] for p in group])
    axes[1, 2].set_ylim(0, 1)
    axes[1, 2].set_title("share of steps where the rule picks a different\nrow than plain margin would in the same state")
    axes[1, 2].legend(fontsize=8.5)
    axes[1, 2].grid(axis="y", alpha=0.3)
    fig.suptitle("Figure 3 - post-hoc mechanism checks (explanatory only; not the basis of the statistical claim)",
                 fontsize=12.5)
    fig.tight_layout()
    fig.savefig(FIG / "03_mechanism.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    return summary


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    metrics = {p: ana.load_metrics(p) for p in (rep.CONTROL, rep.CANDIDATE_A, rep.CANDIDATE_B, *rep.REFERENCES)}
    fig_curves(metrics)
    fig_paired(metrics)
    print(mechanism(metrics).round(4).T.to_string())


if __name__ == "__main__":
    main()
