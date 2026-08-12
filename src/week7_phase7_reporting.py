"""Reporting and figure generation for the Week 7 Phase 7 benchmark."""

from __future__ import annotations

import json
import math
import sys
import textwrap
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_BOOTSTRAP_ROOT = Path(__file__).resolve().parents[1]
if str(_BOOTSTRAP_ROOT) not in sys.path:
    sys.path.insert(0, str(_BOOTSTRAP_ROOT))

from src.week7_sph_v2_common import sha256_file, write_csv


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs" / "week7_07_final_boundary_hybrid_benchmark"
FIGURE_DIR = OUTPUT_DIR / "figures"

M0 = "shared_random_binary_head"
M1 = "binary_uncertainty_repulsion"
M2 = "max_depth_straddle"
M3 = "hybrid_binary_gate20_max_depth_straddle"
M4 = "hybrid_equal_rank_fusion"
METHODS = [M0, M1, M2, M3, M4]
METHOD_LABELS = {
    M0: "Shared random\n(Binary head)",
    M1: "Binary\nuncertainty-repulsion",
    M2: "Max-Depth\nstraddle",
    M3: "Hybrid Gate",
    M4: "Hybrid Rank Fusion",
}
METHOD_COLORS = {
    M0: "#8c8c8c",
    M1: "#1f77b4",
    M2: "#d62728",
    M3: "#2ca02c",
    M4: "#9467bd",
}
PARTITION_COLORS = {
    "new-data": "#4c78a8",
    "old-data-local": "#f58518",
    "old-data-remote-clean": "#54a24b",
}


def load(name: str, output_dir: Path = OUTPUT_DIR) -> pd.DataFrame:
    return pd.read_csv(output_dir / name, low_memory=False)


def strict_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    return series.astype(str).str.strip().str.lower().isin(["true", "1"])


class FigureWriter:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.figure_dir = output_dir / "figures"
        self.figure_dir.mkdir(parents=True, exist_ok=True)
        self.rows: list[dict[str, Any]] = []

    def save(
        self,
        fig: plt.Figure,
        number: int,
        slug: str,
        *,
        title: str,
        question: str,
        sources: str,
        population: str,
        units: str,
        status: str,
        caveat: str,
    ) -> None:
        fig.suptitle(title, fontsize=16, fontweight="bold", y=0.985)
        context = f"Population: {population} | Units: {units} | Status: {status}"
        fig.text(0.5, 0.935, context, ha="center", va="top", fontsize=9.5, color="#333333")
        fig.text(0.01, 0.012, f"Caveat: {caveat}", ha="left", va="bottom", fontsize=8.5, color="#444444")
        if not getattr(fig, "_phase7_manual_layout", False):
            fig.tight_layout(rect=[0.02, 0.06, 0.98, 0.90])
        filename = f"{number:02d}_{slug}.png"
        path = self.figure_dir / filename
        fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        self.rows.append(
            {
                "figure_number": number,
                "relative_path": path.relative_to(self.output_dir).as_posix(),
                "filename": filename,
                "title": title,
                "question": question,
                "source_artifacts": sources,
                "population": population,
                "units": units,
                "evaluation_status": status,
                "major_caveat": caveat,
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "population_visible": True,
                "metric_status_visible": True,
                "units_visible": True,
                "caveat_visible": True,
                "meaningful_explanatory_figure": True,
            }
        )


def style_axis(ax: plt.Axes, *, grid: bool = True) -> None:
    if grid:
        ax.grid(True, alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)


def mean_curve(curves: pd.DataFrame, metric: str) -> pd.DataFrame:
    return (
        curves.groupby(["method", "budget"], as_index=False)[metric]
        .agg(["mean", "std", "count"])
        .reset_index()
    )


def plot_learning_curve(
    writer: FigureWriter,
    number: int,
    metric: str,
    title: str,
    *,
    units: str,
    caveat: str,
    curves: pd.DataFrame,
) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    summary = mean_curve(curves[curves["method"].isin(METHODS)], metric)
    for method in METHODS:
        part = summary[summary["method"].eq(method)].sort_values("budget")
        if part.empty:
            continue
        x = part["budget"].to_numpy(float)
        y = part["mean"].to_numpy(float)
        se = part["std"].to_numpy(float) / np.sqrt(np.maximum(part["count"].to_numpy(float), 1))
        ax.plot(x, y, label=METHOD_LABELS[method].replace("\n", " "), color=METHOD_COLORS[method], linewidth=2)
        ax.fill_between(x, y - se, y + se, color=METHOD_COLORS[method], alpha=0.10)
    ax.set_xlabel("Total simulator queries")
    ax.set_ylabel(units)
    ax.legend(fontsize=8, ncol=2)
    style_axis(ax)
    writer.save(
        fig,
        number,
        title.lower().replace(" ", "_").replace("/", "_").replace("–", "_"),
        title=title,
        question=f"How does {metric} change with simulator budget?",
        sources="phase7_learning_curve_summary.csv",
        population="405 common-ready simulations; 20 matched outer runs",
        units=units,
        status="held-out repeated-CV mean; shaded band is run-level SE",
        caveat=caveat,
    )


def plot_method_bars(
    writer: FigureWriter,
    number: int,
    scorecard: pd.DataFrame,
    columns: Mapping[str, str],
    title: str,
    *,
    lower_better: bool,
    units: str,
) -> None:
    methods = [method for method in METHODS if method in set(scorecard["method"])]
    x = np.arange(len(methods))
    width = 0.8 / len(columns)
    fig, ax = plt.subplots(figsize=(12, 6.4))
    for idx, (column, label) in enumerate(columns.items()):
        values = [float(scorecard.loc[scorecard["method"].eq(method), column].iloc[0]) for method in methods]
        ax.bar(x + (idx - (len(columns) - 1) / 2) * width, values, width, label=label)
    ax.set_xticks(x, [METHOD_LABELS[method] for method in methods], fontsize=8)
    ax.set_ylabel(units)
    ax.legend()
    style_axis(ax)
    direction = "lower is better" if lower_better else "higher is better"
    writer.save(
        fig,
        number,
        title.lower().replace(" ", "_").replace("/", "_"),
        title=title,
        question=f"How do methods rank when {direction}?",
        sources="phase7_method_scorecard.csv",
        population="405 simulations; 20 exactly matched outer runs",
        units=units,
        status="held-out common-budget normalized AULC",
        caveat="Repeated-CV runs reuse simulations; bars are descriptive means, not independent experiments.",
    )


def generate_phase7_figures(output_dir: Path = OUTPUT_DIR) -> pd.DataFrame:
    writer = FigureWriter(output_dir)
    population = pd.read_csv(
        ROOT / "outputs" / "week7_06_real_data_boundary_active_level_set" / "primary_common_population.csv",
        low_memory=False,
    )
    population["has_keyhole"] = strict_bool(population["has_keyhole"])
    boundary = load("boundary_metric_reference.csv", output_dir)
    overlap = load("boundary_subset_overlap.csv", output_dir)
    scaling = load("boundary_scaling_sensitivity.csv", output_dir)
    reuse = load("phase6_run_reuse_audit.csv", output_dir)
    reproduction = load("phase6_reproduction_check.csv", output_dir)
    curves = load("phase7_learning_curve_summary.csv", output_dir)
    scorecard = load("phase7_method_scorecard.csv", output_dir)
    bootstrap = load("phase7_paired_bootstrap_intervals.csv", output_dir)
    tolerance = load("phase7_queries_to_tolerance.csv", output_dir)
    pareto = load("phase7_pareto_summary.csv", output_dir)
    behaviour = load("phase7_query_boundary_behavior.csv", output_dir)
    discovery = load("phase7_keyhole_discovery_summary.csv", output_dir)
    query_overlap = load("phase7_query_overlap_summary.csv", output_dir)
    transient = load("phase7_transient_persistent_summary.csv", output_dir)
    partition = load("phase7_partition_specific_summary.csv", output_dir)
    thresholds = load("hybrid_online_threshold_history.csv", output_dir)
    queries = load("phase7_all_method_query_history.csv", output_dir)
    representative = load("phase7_representative_runs.csv", output_dir)
    runtime = load("phase7_runtime_comparison.csv", output_dir)
    surfaces = load("phase7_supported_boundary_surfaces.csv", output_dir)
    decision = load("phase7_final_decision.csv", output_dir)
    rule = load("phase7_preregistered_rule_outcome.csv", output_dir)

    # 1. Population
    counts = (
        population.groupby(["partition", "has_keyhole"]).size().unstack(fill_value=0)
        .reindex(["new-data", "old-data-local", "old-data-remote-clean"])
    )
    fig, ax = plt.subplots(figsize=(9.5, 6))
    bottom = np.zeros(len(counts))
    for label, color in [(False, "#9ecae1"), (True, "#d62728")]:
        values = counts[label].to_numpy()
        ax.bar(counts.index, values, bottom=bottom, label="Keyhole" if label else "non-Keyhole", color=color)
        bottom += values
    ax.legend()
    ax.set_ylabel("Simulation count")
    style_axis(ax)
    writer.save(fig, 1, "phase7_population", title="Phase 7 primary population", question="What exact data support the final benchmark?", sources="primary_common_population.csv", population="405 simulations: 73 Keyhole, 332 non-Keyhole", units="simulation count", status="fixed published Phase 6 common population", caveat="Manual Keyhole prevalence differs sharply by partition; rows are not rebalanced or relabelled.")

    # 2. Exact run reuse
    fig, ax = plt.subplots(figsize=(11, 5.8))
    audit_matrix = np.vstack([
        strict_bool(reuse["split_hash_matches"]).to_numpy(int),
        strict_bool(reuse["warm_hash_matches"]).to_numpy(int),
        strict_bool(reuse["phase7_generated_warm_equals_phase6_saved"]).to_numpy(int),
    ])
    ax.imshow(audit_matrix, aspect="auto", vmin=0, vmax=1, cmap="RdYlGn")
    ax.set_yticks(range(3), ["Split hash", "Warm hash", "Generated warm sequence"])
    ax.set_xticks(range(20), [str(i + 1) for i in range(20)], fontsize=7)
    ax.set_xlabel("Matched outer run")
    writer.save(fig, 2, "exact_phase6_run_reuse", title="Exact Phase 6 run reuse audit", question="Were the same experimental realizations reused?", sources="phase6_run_reuse_audit.csv", population="20 primary outer runs", units="binary audit state (green = exact match)", status="provenance/fairness audit", caveat="Hash equality verifies run definitions, not the physical truth of a model.")

    metric_specs = [
        (3, "B1_nearest_opposite_distance", "B1 — nearest opposite-label distance", "standardized Euclidean distance", "Smaller values are more boundary-like."),
        (4, "B2_local_disagreement_k5", "B2 — local label disagreement", "fraction among five neighbours", "Larger values are more boundary-like; k=5 was not tuned."),
        (5, "B3_relative_class_distance_ratio", "B3 — relative class-distance ratio", "dimensionless ratio", "Smaller values are more boundary-like."),
    ]
    for number, column, title, units, caveat in metric_specs:
        fig, ax = plt.subplots(figsize=(9.5, 6))
        for label, color in [(False, "#4c78a8"), (True, "#e45756")]:
            values = pd.to_numeric(boundary.loc[strict_bool(boundary["has_keyhole"]).eq(label), column])
            ax.hist(values, bins=24, alpha=0.55, density=True, color=color, label="Keyhole" if label else "non-Keyhole")
        ax.set_xlabel(units)
        ax.set_ylabel("Density")
        ax.legend()
        style_axis(ax)
        writer.save(fig, number, f"{column}_distribution", title=title, question="What empirical transition region does this definition emphasize?", sources="boundary_metric_reference.csv", population="405 simulations", units=units, status="full-population model-independent evaluation diagnostic", caveat=caveat + " The metric never enters acquisition.")

    scatter_specs = [
        (6, "B1_nearest_opposite_distance", "B2_local_disagreement_k5", "B1 versus B2"),
        (7, "B1_nearest_opposite_distance", "B3_relative_class_distance_ratio", "B1 versus B3"),
        (8, "B2_local_disagreement_k5", "B3_relative_class_distance_ratio", "B2 versus B3"),
    ]
    for number, xcol, ycol, title in scatter_specs:
        fig, ax = plt.subplots(figsize=(8.5, 6.5))
        labels = strict_bool(boundary["has_keyhole"])
        ax.scatter(boundary.loc[~labels, xcol], boundary.loc[~labels, ycol], s=24, alpha=0.6, label="non-Keyhole")
        ax.scatter(boundary.loc[labels, xcol], boundary.loc[labels, ycol], s=32, alpha=0.8, label="Keyhole", marker="^")
        ax.set_xlabel(xcol.replace("_", " "))
        ax.set_ylabel(ycol.replace("_", " "))
        ax.legend()
        style_axis(ax)
        writer.save(fig, number, title.lower().replace(" ", "_"), title=title, question="Do two model-independent boundary diagnostics rank the same rows similarly?", sources="boundary_metric_reference.csv;boundary_metric_correlations.csv", population="405 simulations", units="native metric units on each axis", status="full-population evaluation-only diagnostic", caveat="Association does not make the definitions interchangeable; q-subset overlap is assessed separately.")

    for number, quantile in [(9, 20), (10, 30)]:
        part = overlap[pd.to_numeric(overlap["quantile"]).eq(quantile)]
        matrix = part.pivot(index="metric_a", columns="metric_b", values="jaccard").reindex(index=["B1", "B2", "B3"], columns=["B1", "B2", "B3"])
        fig, ax = plt.subplots(figsize=(7.5, 6.2))
        image = ax.imshow(matrix, vmin=0, vmax=1, cmap="Blues")
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f"{matrix.iloc[i, j]:.2f}", ha="center", va="center")
        ax.set_xticks(range(3), matrix.columns)
        ax.set_yticks(range(3), matrix.index)
        fig.colorbar(image, ax=ax, label="Jaccard")
        writer.save(fig, number, f"q{quantile}_boundary_overlap", title=f"q{quantile} boundary-subset overlap", question="How much do B1/B2/B3 agree on boundary membership?", sources="boundary_subset_overlap.csv", population=f"405 simulations; each metric selects ceil({quantile}% × 405)", units="Jaccard index", status="full-population evaluation-only diagnostic", caveat="Diagonal cells are one by construction; scientific comparison uses off-diagonal overlap.")

    for number, quantile in [(11, 20), (12, 30)]:
        fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), sharex=True, sharey=True)
        for ax, metric in zip(axes, ["B1", "B2", "B3"]):
            flag = strict_bool(boundary[f"{metric}_q{quantile}"])
            ax.scatter(population["P"], population["VX"], s=10, color="#d9d9d9", alpha=0.5)
            ax.scatter(population.loc[flag, "P"], population.loc[flag, "VX"], c=strict_bool(population.loc[flag, "has_keyhole"]).map({False: "#4c78a8", True: "#e45756"}), s=30)
            ax.set_title(metric)
            ax.set_xlabel("P (W)")
            style_axis(ax)
        axes[0].set_ylabel("VX (m/s)")
        writer.save(fig, number, f"q{quantile}_process_space_projection", title=f"q{quantile} boundary sets in P–VX projection", question="Where do the three empirical boundary definitions lie in process space?", sources="boundary_metric_reference.csv;primary_common_population.csv", population="405 simulations", units="P in W; VX in m/s", status="full-population evaluation-only projection", caveat="This 2D projection suppresses LS and ST and therefore cannot represent the full 4D neighbourhood geometry.")

    fig, ax = plt.subplots(figsize=(9, 5.8))
    consensus_counts = [int(strict_bool(boundary[f"consensus_q{q}"]).sum()) for q in [20, 30]]
    kh_counts = [int(strict_bool(boundary.loc[strict_bool(boundary[f"consensus_q{q}"]), "has_keyhole"]).sum()) for q in [20, 30]]
    ax.bar(["consensus q20", "consensus q30"], consensus_counts, color="#9ecae1", label="all")
    ax.bar(["consensus q20", "consensus q30"], kh_counts, color="#e45756", label="Keyhole")
    ax.set_ylabel("Simulation count")
    ax.legend()
    style_axis(ax)
    writer.save(fig, 13, "consensus_boundary_sets", title="Secondary consensus boundary sets", question="How large and label-balanced are the at-least-two-of-three consensus sets?", sources="boundary_metric_reference.csv;boundary_consensus_membership.csv", population="405 simulations", units="simulation count", status="secondary evaluation-only diagnostic", caveat="Consensus does not replace B1/B2/B3 and does not enter the preregistered primary decision.")

    fig, ax = plt.subplots(figsize=(9.5, 6))
    for metric, marker in [("B1", "o"), ("B3", "s")]:
        part = scaling[scaling["metric"].eq(metric)].sort_values("quantile")
        ax.plot(part["quantile"], part["membership_jaccard"], marker=marker, linewidth=2, label=metric)
    ax.set_xticks([20, 30])
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Boundary quantile (%)")
    ax.set_ylabel("z-score vs robust-scaling membership Jaccard")
    ax.legend()
    style_axis(ax)
    writer.save(fig, 14, "scaling_sensitivity", title="Boundary-metric scaling sensitivity", question="Do B1/B3 memberships survive median/IQR scaling?", sources="boundary_scaling_sensitivity.csv", population="405 simulations", units="Jaccard index", status="secondary robustness diagnostic", caveat="z-score scaling remains primary; robust scaling was not allowed to redefine the benchmark.")

    def schematic(number: int, title: str, boxes: Sequence[tuple[float, float, str, str]], arrows: Sequence[tuple[int, int]], caveat: str) -> None:
        fig, ax = plt.subplots(figsize=(12, 5.7))
        ax.axis("off")
        for start, end in arrows:
            x1, y1, _, _ = boxes[start]
            x2, y2, _, _ = boxes[end]
            ax.annotate(
                "",
                xy=(x2, y2),
                xytext=(x1, y1),
                xycoords=ax.transAxes,
                arrowprops=dict(arrowstyle="->", lw=1.8, shrinkA=28, shrinkB=28),
                zorder=1,
            )
        for x, y, text, color in boxes:
            ax.text(x, y, text, ha="center", va="center", fontsize=10, bbox=dict(boxstyle="round,pad=0.5", fc=color, ec="#333333"), transform=ax.transAxes, zorder=2)
        writer.save(fig, number, title.lower().replace(" ", "_"), title=title, question="What information flows through the preregistered method?", sources="phase7_method_definitions.csv;phase7_preregistered_decision_rule.json", population="one matched outer run at one acquisition step", units="information-flow schematic", status="preregistered method definition", caveat=caveat)

    schematic(15, "Phase 7 method set", [(0.08,0.55,"Shared query\nbudget","#eeeeee"),(0.30,0.75,"Binary GPC","#c6dbef"),(0.30,0.35,"Max-Depth GPR","#fdd0a2"),(0.58,0.75,"Binary champion","#9ecae1"),(0.58,0.35,"Max-Depth champion","#fdae6b"),(0.84,0.55,"Two fixed\nHybrids","#c7e9c0")], [(0,1),(0,2),(1,3),(2,4),(1,5),(2,5)], "Only M3 and M4 are new; no method was added after seeing results.")
    schematic(16, "Hybrid Gate acquisition", [(0.10,0.55,"Unqueried pool","#eeeeee"),(0.32,0.72,"Exact Binary\npriority","#c6dbef"),(0.54,0.72,"Top ceil(20%)\ngate","#9ecae1"),(0.54,0.35,"Max-Depth\nstraddle","#fdae6b"),(0.82,0.55,"Next simulator\nquery","#c7e9c0")], [(0,1),(1,2),(2,3),(3,4)], "Manual labels and unqueried max depth are unavailable before selection; B1/B2/B3 never enter this flow.")
    schematic(17, "Hybrid Equal-Rank Fusion", [(0.08,0.55,"Unqueried pool","#eeeeee"),(0.30,0.75,"Binary priority\npercentile","#c6dbef"),(0.30,0.32,"Depth straddle\npercentile","#fdd0a2"),(0.60,0.55,"0.5 + 0.5\nfixed fusion","#dadaeb"),(0.84,0.55,"Next simulator\nquery","#c7e9c0")], [(0,1),(0,2),(1,3),(2,3),(3,4)], "The weights are fixed and untuned; the final regime prediction still comes only from Binary GPC.")

    fig, ax = plt.subplots(figsize=(10, 6))
    rep = reproduction.copy()
    rep["log10_difference"] = np.log10(np.maximum(pd.to_numeric(rep["maximum_absolute_difference"]), 1e-16))
    for method, part in rep.groupby("method"):
        ax.scatter(range(len(part)), part["log10_difference"], label=method, alpha=0.75)
    ax.axhline(np.log10(1e-10), color="red", linestyle="--", label="largest numeric tolerance")
    ax.set_ylabel("log10 maximum absolute difference")
    ax.set_xlabel("Reproduction check item")
    ax.legend(fontsize=8)
    style_axis(ax)
    writer.save(fig, 18, "phase6_reproduction_check", title="Phase 6 champion reproduction check", question="Does the new engine reproduce saved Phase 6 behavior before Hybrid evaluation?", sources="phase6_reproduction_check.csv", population="first outer run; Binary and Max-Depth champions through budget 30", units="log10 absolute difference", status="deterministic implementation audit", caveat="Passing numerical reproduction supports code continuity; it does not validate a physical model.")

    learning_specs = [
        (19, "B1_q20_error", "B1 q20 learning curves"),
        (20, "B1_q30_error", "B1 q30 learning curves"),
        (21, "B2_q20_error", "B2 q20 learning curves"),
        (22, "B2_q30_error", "B2 q30 learning curves"),
        (23, "B3_q20_error", "B3 q20 learning curves"),
        (24, "B3_q30_error", "B3 q30 learning curves"),
        (25, "consensus_q20_error", "Consensus q20 learning curves"),
        (26, "consensus_q30_error", "Consensus q30 learning curves"),
    ]
    for number, metric, title in learning_specs:
        plot_learning_curve(
            writer,
            number,
            metric,
            title,
            units="held-out classification error fraction",
            caveat=(
                "B1/B2/B3 are evaluation-only and recomputed within each untouched test fold."
                if not metric.startswith("consensus")
                else "Consensus is secondary and never replaces the three individual definitions."
            ),
            curves=curves,
        )

    plot_learning_curve(writer, 27, "balanced_accuracy", "Balanced-accuracy learning curves", units="balanced accuracy", caveat="Global balanced accuracy and boundary localization answer different questions; repeated-CV runs are descriptive matched units.", curves=curves)
    plot_learning_curve(writer, 28, "sensitivity", "Keyhole-sensitivity learning curves", units="sensitivity", caveat="Sensitivity does not measure non-Keyhole specificity and is affected by sparse positive counts in old partitions.", curves=curves)
    plot_learning_curve(writer, 29, "brier_score", "Probability-calibration learning curves", units="Brier score (lower is better)", caveat="Brier score mixes calibration and discrimination and is not a boundary-specific success criterion.", curves=curves)

    plot_method_bars(
        writer,
        30,
        scorecard,
        {"mean_B1_q20_aulc": "B1", "mean_B2_q20_aulc": "B2", "mean_B3_q20_aulc": "B3"},
        "q20 AULC comparison",
        lower_better=True,
        units="normalized q20 error AULC",
    )
    plot_method_bars(
        writer,
        31,
        scorecard,
        {"mean_B1_q30_aulc": "B1", "mean_B2_q30_aulc": "B2", "mean_B3_q30_aulc": "B3"},
        "q30 AULC comparison",
        lower_better=True,
        units="normalized q30 error AULC",
    )

    interval_part = bootstrap[
        bootstrap["comparison"].isin(["hybrid_gate_minus_binary", "hybrid_fusion_minus_binary"])
        & bootstrap["metric"].isin([f"common_normalized_aulc__B{idx}_q20_error" for idx in [1, 2, 3]])
    ].copy()
    interval_part["label"] = interval_part.apply(
        lambda row: ("Gate" if row["comparison"].startswith("hybrid_gate") else "Fusion")
        + " / "
        + row["metric"].split("__B")[1].split("_")[0].join(["B", ""]),
        axis=1,
    )
    # Replace the compact construction above with explicit stable labels.
    interval_part["label"] = interval_part.apply(
        lambda row: f"{'Gate' if row['comparison'].startswith('hybrid_gate') else 'Fusion'} / {row['metric'].split('__')[1].split('_')[0]}",
        axis=1,
    )
    interval_part = interval_part.sort_values(["comparison", "metric"]).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    y = np.arange(len(interval_part))
    means = pd.to_numeric(interval_part["mean_paired_difference_a_minus_b"])
    lows = pd.to_numeric(interval_part["bootstrap_ci_low"])
    highs = pd.to_numeric(interval_part["bootstrap_ci_high"])
    ax.errorbar(means, y, xerr=[means - lows, highs - means], fmt="o", color="#333333", ecolor="#6baed6", capsize=4)
    ax.axvline(0, color="red", linestyle="--")
    ax.set_yticks(y, interval_part["label"])
    ax.set_xlabel("Hybrid minus Binary q20 AULC")
    style_axis(ax)
    writer.save(fig, 32, "paired_hybrid_minus_binary_intervals", title="Paired Hybrid-minus-Binary q20 intervals", question="Is either Hybrid reliably better than Binary under at least two definitions?", sources="phase7_paired_bootstrap_intervals.csv", population="20 matched outer runs; 5,000 paired bootstrap resamples", units="AULC difference; negative favours Hybrid", status="paired descriptive uncertainty", caveat="Repeated CV reuses simulations; intervals are not independent physical replications.")

    tolerance_part = tolerance[
        tolerance["method"].isin([M1, M2, M3, M4])
        & (
            (tolerance["metric"].isin(["B1_q20_error", "B2_q20_error", "B3_q20_error"]) & pd.to_numeric(tolerance["target"]).eq(0.20))
            | (tolerance["metric"].eq("balanced_accuracy") & pd.to_numeric(tolerance["target"]).eq(0.90))
        )
    ].copy()
    tol_rows = []
    for (method, metric), group in tolerance_part.groupby(["method", "metric"]):
        reached = group[group["status"].eq("reached")]
        tol_rows.append({"method": method, "metric": metric, "median": float(pd.to_numeric(reached["queries_required"]).median()) if len(reached) else np.nan, "reached": len(reached)})
    tol = pd.DataFrame(tol_rows)
    matrix = tol.pivot(index="method", columns="metric", values="median").reindex(index=[M1, M2, M3, M4], columns=["B1_q20_error", "B2_q20_error", "B3_q20_error", "balanced_accuracy"])
    reached_matrix = tol.pivot(index="method", columns="metric", values="reached").reindex_like(matrix)
    fig, ax = plt.subplots(figsize=(11, 6.5))
    image = ax.imshow(matrix, cmap="viridis_r", aspect="auto", vmin=12, vmax=80)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix.iloc[i, j]
            reached = reached_matrix.iloc[i, j]
            ax.text(j, i, "NA" if pd.isna(value) else f"{value:.1f}\n({int(reached)}/20)", ha="center", va="center", color="white" if value > 45 else "black", fontsize=8)
    ax.set_xticks(range(4), ["B1 q20≤.20", "B2 q20≤.20", "B3 q20≤.20", "BA≥.90"])
    ax.set_yticks(range(4), [METHOD_LABELS[m].replace("\n", " ") for m in [M1, M2, M3, M4]])
    fig.colorbar(image, ax=ax, label="Median queries among reached runs")
    writer.save(fig, 33, "queries_to_tolerance", title="Queries to useful performance", question="How quickly and how often does each method reach fixed tolerances?", sources="phase7_queries_to_tolerance.csv", population="20 matched outer runs", units="median simulator queries; parentheses show reached runs", status="held-out, no extrapolation when not reached", caveat="Medians condition on successful runs; success counts must be read alongside them.")

    for number, quantile in [(34, 20), (35, 30)]:
        fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), sharey=True)
        for ax, boundary_id in zip(axes, ["B1", "B2", "B3"]):
            part = pareto[pd.to_numeric(pareto["quantile"]).eq(quantile) & pareto["boundary_definition"].eq(boundary_id)]
            for _, row in part.iterrows():
                method = row["method"]
                ax.scatter(row["mean_boundary_error_aulc"], row["mean_balanced_accuracy_aulc"], s=90, color=METHOD_COLORS.get(method, "#333333"), marker="o" if strict_bool(pd.Series([row["on_pareto_frontier"]])).iloc[0] else "x")
                ax.annotate(METHOD_LABELS.get(method, method).split("\n")[0], (row["mean_boundary_error_aulc"], row["mean_balanced_accuracy_aulc"]), xytext=(4,4), textcoords="offset points", fontsize=7)
            ax.set_title(boundary_id)
            ax.set_xlabel(f"q{quantile} error AULC ↓")
            style_axis(ax)
        axes[0].set_ylabel("Balanced-accuracy AULC ↑")
        writer.save(fig, number, f"pareto_q{quantile}_vs_balanced_accuracy", title=f"Pareto frontier: q{quantile} localization versus balanced accuracy", question="Does Hybrid move the unweighted boundary/global trade-off frontier?", sources="phase7_pareto_summary.csv", population="405 simulations; 20 matched outer runs", units="normalized AULCs", status="held-out descriptive Pareto analysis", caveat="No arbitrary scalar weighting combines the two axes; crosses denote dominated methods.")

    at80 = behaviour[pd.to_numeric(behaviour["budget"]).eq(80) & behaviour["method"].isin(METHODS)]
    behaviour_summary = at80.groupby("method", as_index=False)[[f"fraction_queries_B{b}_q20" for b in [1,2,3]]].mean()
    fig, ax = plt.subplots(figsize=(12, 6.2))
    x = np.arange(len(METHODS)); width = 0.23
    for idx, boundary_id in enumerate(["B1", "B2", "B3"]):
        values = [float(behaviour_summary.loc[behaviour_summary["method"].eq(method), f"fraction_queries_{boundary_id}_q20"].iloc[0]) for method in METHODS]
        ax.bar(x + (idx-1)*width, values, width, label=boundary_id)
    ax.set_xticks(x, [METHOD_LABELS[m] for m in METHODS], fontsize=8)
    ax.set_ylabel("Fraction of 80 queries in global q20 set")
    ax.legend()
    style_axis(ax)
    writer.save(fig, 36, "true_boundary_query_fraction", title="Where did each method actually query?", question="What fraction of selected simulations belongs to each true empirical q20 set?", sources="phase7_query_boundary_behavior.csv", population="20 matched outer runs at budget 80", units="query fraction", status="post-selection evaluation only", caveat="True boundary memberships were joined after selection and never entered acquisition.")

    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    discovery_summary = discovery[discovery["method"].isin(METHODS)].groupby(["method", "budget"], as_index=False)["keyhole_discovered"].mean()
    for method in METHODS:
        part = discovery_summary[discovery_summary["method"].eq(method)].sort_values("budget")
        ax.plot(part["budget"], part["keyhole_discovered"], color=METHOD_COLORS[method], label=METHOD_LABELS[method].replace("\n", " "), linewidth=2)
    ax.set_xlabel("Total simulator queries")
    ax.set_ylabel("Mean Keyhole positives discovered")
    ax.legend(fontsize=8, ncol=2)
    style_axis(ax)
    writer.save(fig, 37, "keyhole_discovery_vs_budget", title="Early Keyhole discovery", question="Does Max-Depth side information reveal positive cases earlier?", sources="phase7_keyhole_discovery_summary.csv", population="20 matched outer training pools", units="mean discovered Keyhole simulations", status="query-behaviour diagnostic", caveat="Discovery count is not held-out boundary accuracy and can reward prevalence-seeking behaviour.")

    overlap80 = query_overlap[pd.to_numeric(query_overlap["budget"]).eq(80)]
    matrix = pd.DataFrame(np.eye(len([M1,M2,M3,M4])), index=[M1,M2,M3,M4], columns=[M1,M2,M3,M4])
    for _, row in overlap80.iterrows():
        a,b = row["method_a"], row["method_b"]
        if a in matrix.index and b in matrix.index:
            matrix.loc[a,b] = matrix.loc[b,a] = float(row["jaccard"]) if overlap80[(overlap80["method_a"].eq(a)&overlap80["method_b"].eq(b))].shape[0] == 1 else float(overlap80[((overlap80["method_a"].eq(a)&overlap80["method_b"].eq(b))|(overlap80["method_a"].eq(b)&overlap80["method_b"].eq(a)))]["jaccard"].mean())
    # Recompute pair means explicitly to avoid order dependence.
    for i,a in enumerate(matrix.index):
        for j,b in enumerate(matrix.columns):
            if i >= j: continue
            part=overlap80[((overlap80["method_a"].eq(a)&overlap80["method_b"].eq(b))|(overlap80["method_a"].eq(b)&overlap80["method_b"].eq(a)))]
            if len(part): matrix.loc[a,b]=matrix.loc[b,a]=float(part["jaccard"].mean())
    fig, ax = plt.subplots(figsize=(8.5, 7))
    image=ax.imshow(matrix, vmin=0, vmax=1, cmap="Purples")
    for i in range(len(matrix)):
        for j in range(len(matrix)): ax.text(j,i,f"{matrix.iloc[i,j]:.2f}",ha="center",va="center")
    ax.set_xticks(range(len(matrix)), [METHOD_LABELS[m].split("\n")[0] for m in matrix.columns], rotation=25, ha="right")
    ax.set_yticks(range(len(matrix)), [METHOD_LABELS[m].replace("\n", " ") for m in matrix.index])
    fig.colorbar(image, ax=ax, label="Mean Jaccard")
    writer.save(fig, 38, "query_overlap_matrix", title="Method query-set overlap at budget 80", question="How different are the selected simulator sets?", sources="phase7_query_overlap_summary.csv", population="20 matched outer runs", units="mean query-set Jaccard", status="post-selection trajectory diagnostic", caveat="High overlap does not imply identical query order or identical fitted models.")

    def subgroup_plot(number: int, subgroup: str, title: str) -> None:
        part = transient[pd.to_numeric(transient["budget"]).eq(80) & transient["subgroup"].eq(subgroup) & transient["method"].isin([M1,M2,M3,M4])]
        summary = part.groupby("method", as_index=False)["sensitivity"].mean()
        fig, ax = plt.subplots(figsize=(9.5, 5.8))
        methods=[M1,M2,M3,M4]
        values=[float(summary.loc[summary["method"].eq(m),"sensitivity"].iloc[0]) for m in methods]
        ax.bar(range(4), values, color=[METHOD_COLORS[m] for m in methods])
        ax.set_xticks(range(4), [METHOD_LABELS[m] for m in methods], fontsize=8)
        ax.set_ylim(0,1.05); ax.set_ylabel("Sensitivity")
        style_axis(ax)
        writer.save(fig, number, title.lower().replace(" ","_"), title=title, question=f"How well does each method identify {subgroup} cases at the final budget?", sources="phase7_transient_persistent_summary.csv", population="held-out manual Keyhole subgroup across 20 runs", units="sensitivity", status="held-out descriptive subgroup result", caveat="Subgroups are small and repeated-CV folds reuse the same physical simulations.")
    subgroup_plot(39, "transient_Keyhole", "Transient Keyhole sensitivity")
    subgroup_plot(40, "persistent_Keyhole", "Persistent Keyhole sensitivity")

    part = partition[pd.to_numeric(partition["budget"]).eq(80) & partition["method"].isin([M1,M2,M3,M4])]
    summary = part.groupby(["method","partition"],as_index=False)["balanced_accuracy"].mean()
    fig, ax = plt.subplots(figsize=(12,6.2)); x=np.arange(4); width=.24
    for idx,partition_name in enumerate(["new-data","old-data-local","old-data-remote-clean"]):
        values=[float(summary.loc[summary["method"].eq(m)&summary["partition"].eq(partition_name),"balanced_accuracy"].mean()) for m in [M1,M2,M3,M4]]
        ax.bar(x+(idx-1)*width,values,width,label=partition_name,color=PARTITION_COLORS[partition_name])
    ax.set_xticks(x,[METHOD_LABELS[m] for m in [M1,M2,M3,M4]],fontsize=8);ax.set_ylabel("Mean balanced accuracy");ax.legend();style_axis(ax)
    writer.save(fig, 41, "partition_specific_performance", title="Partition-specific held-out performance", question="Is a method's apparent advantage driven by one partition?", sources="phase7_partition_specific_summary.csv", population="partition subsets inside the same 20 primary held-out folds", units="balanced accuracy", status="secondary held-out subgroup diagnostic", caveat="Old-remote contains very few Keyhole cases; missing single-class fold metrics are not fabricated.")

    fig, ax=plt.subplots(figsize=(10.5,6.2))
    for method in [M3,M4]:
        summary=thresholds[thresholds["method"].eq(method)].groupby("budget",as_index=False)["threshold"].agg(["mean","std"]).reset_index()
        ax.plot(summary["budget"],summary["mean"],color=METHOD_COLORS[method],label=METHOD_LABELS[method],linewidth=2)
        ax.fill_between(summary["budget"],summary["mean"]-summary["std"],summary["mean"]+summary["std"],color=METHOD_COLORS[method],alpha=.12)
    ax.set_xlabel("Total simulator queries");ax.set_ylabel("Queried-only max-depth threshold (µm)");ax.legend();style_axis(ax)
    writer.save(fig, 42, "hybrid_threshold_trajectories", title="Hybrid online max-depth threshold trajectories", question="How stable is the auxiliary threshold while Hybrid query sets evolve?", sources="hybrid_online_threshold_history.csv", population="20 matched outer runs", units="µm; mean ± one run-level SD", status="queried-only auxiliary diagnostic", caveat="The threshold does not define manual Keyhole and is not a universal physical constant.")

    selection_map={43:"median_gate_minus_binary_B1_q20",44:"strongest_hybrid_improvement",45:"strongest_hybrid_deterioration"}
    title_map={43:"Representative median Hybrid-vs-Binary run",44:"Strongest Hybrid-improvement run",45:"Strongest Hybrid-deterioration run"}
    for number,selection in selection_map.items():
        run_id=str(representative.loc[representative["selection"].eq(selection),"run_id"].iloc[0])
        fig,axes=plt.subplots(1,2,figsize=(14,5.5))
        for method in [M1,M3]:
            part=curves[curves["run_id"].eq(run_id)&curves["method"].eq(method)].sort_values("budget")
            axes[0].plot(part["budget"],part["B1_q20_error"],color=METHOD_COLORS[method],label=METHOD_LABELS[method],linewidth=2)
            qpart=behaviour[behaviour["run_id"].eq(run_id)&behaviour["method"].eq(method)].sort_values("budget")
            axes[1].plot(qpart["budget"],qpart["fraction_queries_B1_q20"],color=METHOD_COLORS[method],label=METHOD_LABELS[method],linewidth=2)
        axes[0].set_xlabel("Queries");axes[0].set_ylabel("Held-out B1 q20 error");axes[1].set_xlabel("Queries");axes[1].set_ylabel("Cumulative B1 q20 query fraction")
        for ax in axes: ax.legend(fontsize=8);style_axis(ax)
        writer.save(fig,number,selection,title=title_map[number],question="How do Binary and Gate trajectories differ in an algorithmically selected run?",sources="phase7_representative_runs.csv;phase7_learning_curve_summary.csv;phase7_query_boundary_behavior.csv",population=f"outer run {run_id}",units="error fraction and query fraction",status="algorithmic representative-run diagnostic",caveat="Runs were selected by Gate-minus-Binary B1 q20 AULC, never by visual attractiveness.")

    def surface_plot(number:int,slice_name:str,title:str)->None:
        part=surfaces[surfaces["slice"].eq(slice_name)&surfaces["context"].eq("median")&pd.to_numeric(surfaces["budget"]).eq(80)]
        fig,axes=plt.subplots(1,2,figsize=(14,5.8),sharex=True,sharey=True)
        fig._phase7_manual_layout = True
        fig.subplots_adjust(left=.07,right=.87,bottom=.15,top=.80,wspace=.10)
        for ax,method in zip(axes,[M1,M3]):
            p=part[part["method"].eq(method)].copy();a=sorted(p["axis_a_value"].unique());b=sorted(p["axis_b_value"].unique())
            z=p.pivot(index="axis_b_value",columns="axis_a_value",values="keyhole_probability").reindex(index=b,columns=a).to_numpy(float)
            mask=p.pivot(index="axis_b_value",columns="axis_a_value",values="supported").reindex(index=b,columns=a).apply(strict_bool).to_numpy(bool)
            z=np.ma.masked_where(~mask,z);aa=np.array(a);bb=np.array(b)
            if slice_name in {"P-LS","VX-LS"}: bb=bb*1e6
            contour=ax.contourf(aa,bb,z,levels=np.linspace(0,1,11),cmap="RdBu_r",vmin=0,vmax=1)
            try: ax.contour(aa,bb,z,levels=[.5],colors="black",linewidths=1.5)
            except ValueError: pass
            ax.set_title(METHOD_LABELS[method].replace("\n"," "));ax.set_xlabel(f"{slice_name.split('-')[0]} ({'W' if slice_name.startswith('P') else 'm/s'})")
            style_axis(ax)
        second=slice_name.split('-')[1];axes[0].set_ylabel(f"{second} ({'µm' if second=='LS' else 'm/s'})")
        cax=fig.add_axes([.90,.19,.018,.56]);fig.colorbar(contour,cax=cax,label="P(Keyhole)")
        writer.save(fig,number,title.lower().replace(" ","_"),title=title,question="How do different queried training sets change the Binary GPC boundary?",sources="phase7_supported_boundary_surfaces.csv",population="algorithmic median run; budget 80; median fixed 4D context",units="axis physical units; probability",status="supported descriptive surface",caveat="Unsupported 4D regions are blank; contours are diagnostic predictions, not physical truth.")
    surface_plot(46,"P-VX","Supported P–VX boundary comparison")
    surface_plot(47,"P-LS","Supported P–LS boundary comparison")
    surface_plot(48,"VX-LS","Supported VX–LS boundary comparison")

    fig,ax=plt.subplots(figsize=(11,6));part=runtime[runtime["method"].isin([M1,M2,M3,M4])];methods=[M1,M2,M3,M4];values=[float(part.loc[part["method"].eq(m),"mean_runtime_seconds"].iloc[0]) for m in methods]
    ax.bar(range(4),values,color=[METHOD_COLORS[m] for m in methods]);ax.set_xticks(range(4),[METHOD_LABELS[m] for m in methods],fontsize=8);ax.set_ylabel("Mean wall seconds per outer run");style_axis(ax)
    writer.save(fig,49,"computational_overhead",title="Computational overhead of auxiliary Max-Depth fitting",question="What extra computation does Hybrid require at equal simulator budget?",sources="phase7_runtime_comparison.csv",population="20 outer runs; four local workers",units="wall seconds per method-run",status="measured computational cost",caveat="Simulator calls are assumed expensive and remain equal; local GP fitting time is a separate efficiency axis.")

    fig,axes=plt.subplots(1,2,figsize=(14,6),gridspec_kw={"width_ratios":[1.0,1.35]})
    fig._phase7_manual_layout = True
    fig.subplots_adjust(left=.08,right=.96,bottom=.20,top=.76,wspace=.22)
    cond_cols=["condition_A_q20","condition_B_q30","condition_C_no_material_BA_sacrifice","condition_D_beats_shared_random"]
    matrix=np.vstack([strict_bool(rule.set_index("method").loc[m,cond_cols]).to_numpy(int) for m in [M3,M4]])
    axes[0].imshow(matrix,vmin=0,vmax=1,cmap="RdYlGn");axes[0].set_xticks(range(4),["A q20","B q30","C BA","D random"],rotation=20);axes[0].set_yticks(range(2),["Hybrid Gate","Rank Fusion"])
    for i in range(2):
        for j in range(4): axes[0].text(j,i,"PASS" if matrix[i,j] else "FAIL",ha="center",va="center",fontsize=8)
    axes[1].axis("off");axes[1].text(.5,.68,str(decision["decision"].iloc[0]),ha="center",va="center",fontsize=16,fontweight="bold",bbox=dict(boxstyle="round,pad=.7",fc="#c6dbef",ec="#333333"),transform=axes[1].transAxes)
    reason_text=textwrap.fill(str(decision["reason"].iloc[0]),width=48)
    axes[1].text(.5,.35,reason_text,ha="center",va="center",fontsize=10,linespacing=1.35,transform=axes[1].transAxes)
    writer.save(fig,50,"final_phase7_decision",title="Final preregistered Phase 7 decision",question="Did either Hybrid satisfy the rule written before results?",sources="phase7_preregistered_rule_outcome.csv;phase7_final_decision.csv",population="405 simulations; 20 matched outer runs",units="boolean decision conditions",status="mechanical preregistered decision",caveat="Manual has_keyhole remains ground truth; no causal or universal-threshold claim follows.")

    manifest = pd.DataFrame(writer.rows).sort_values("figure_number").reset_index(drop=True)
    if len(manifest) != 50 or manifest["figure_number"].tolist() != list(range(1, 51)):
        raise RuntimeError(f"Expected exactly 50 figures numbered 1..50, found {len(manifest)}")
    write_csv(output_dir / "figure_manifest.csv", manifest)
    return manifest


def main() -> None:
    manifest = generate_phase7_figures()
    print(json.dumps({"figures": len(manifest), "output_dir": str(FIGURE_DIR), "status": "PASS"}, indent=2))


if __name__ == "__main__":
    main()
