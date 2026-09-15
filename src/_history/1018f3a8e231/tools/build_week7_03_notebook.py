"""Build and execute the Week 7 Phase 3 teaching notebook."""

from __future__ import annotations

import json
from pathlib import Path

import nbformat as nbf
import pandas as pd
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "week7_03_new_data_physical_model_stability"
NOTEBOOK = ROOT / "notebooks" / "week_07" / "03_new_data_physical_model_stability.ipynb"


def markdown(source: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(source=source)


def code(source: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(source=source)


def section(
    cells: list[nbf.NotebookNode],
    number: int,
    title: str,
    *,
    what: str,
    why: str,
    question: str,
    suspicious: str,
    calculation: str,
    observation: str,
) -> None:
    cells.extend(
        [
            markdown(
                f"""## {number}. {title}

**What are we doing?** {what}

**Why?** {why}

**What question does this answer?** {question}

**What would be suspicious?** {suspicious}"""
            ),
            code(calculation),
            markdown(f"**What did we observe?** {observation}"),
        ]
    )


def main() -> None:
    required = [
        "summary.json",
        "model_ready_population.csv",
        "model_ready_population_long.csv",
        "week6_model_traceability.csv",
        "fold_level_predictions.csv",
        "model_metric_table.csv",
        "model_selection_decisions.csv",
        "week6_vs_new_data_comparison.csv",
        "stability_conclusion_table.csv",
        "validation_results.csv",
    ]
    missing = [name for name in required if not (OUT / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Run the full Phase 3 analysis first; missing: {missing}")

    summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    decisions = pd.read_csv(OUT / "model_selection_decisions.csv").set_index("target")
    historical = pd.read_csv(OUT / "week6_vs_new_data_comparison.csv").set_index("target")
    conclusions = pd.read_csv(OUT / "stability_conclusion_table.csv")
    targets = summary["targets"]

    point_summary = "; ".join(
        f"{target.replace('_', ' ')}: {values['protocol_selected_point_model']} "
        f"(relative RMSE {values['relative_RMSE_pct']:.2f}%)"
        for target, values in targets.items()
    )
    status_counts = conclusions["status"].value_counts().to_dict()

    cells: list[nbf.NotebookNode] = [
        markdown(
            f"""# Week 7 Phase 3 — new-data physical-response model stability / replication

This notebook asks one bounded question:

> **Do the Week 6 physical-response modelling conclusions survive when the same scientific pipeline is evaluated independently on Ioan's newly generated simulation design?**

The primary domain is `partition == "new-data"`. Old and new simulations are never pooled. The immutable dataset is `{summary['dataset_repo_id']}@{summary['dataset_revision']}`, and the repository starting point is `{summary['starting_branch']}@{summary['starting_remote_head_sha']}`.

```text
Week 7 Phase 3
├── immutable provenance and readiness-derived population
├── executable Week 6 protocol traceability
├── exact simulation-level LOO baselines and Gaussian processes
├── numerical-jitter / shared-nugget / heteroskedastic-alpha comparison
├── median-scale relative errors and calibration
├── saved Week 6 versus new-data replication evidence
└── validation and hard stop before later Week 7 phases
```

Scope boundary: no Keyhole or extreme-event classifier, feature-effect or causal analysis, target redesign, active learning, level-set estimation, or pooled production model is created here."""
        )
    ]

    section(
        cells,
        1,
        "Scope and immutable data provenance",
        what="Load the full saved Phase 3 artifacts and verify their revision, branch base, and hard-stop flags.",
        why="A current remote branch head and one immutable `sph_v2` snapshot are prerequisites for a meaningful replication.",
        question="Did this analysis use the corrected Phase 2 dataset rather than a floating Hugging Face main or stale branch?",
        suspicious="Any revision mismatch, pooled-population flag, later-phase scope flag, or missing source hash.",
        calculation="""from pathlib import Path
import json
import numpy as np
import pandas as pd
from IPython.display import Image, Markdown, display

ROOT = Path.cwd().resolve()
OUT = ROOT / "outputs" / "week7_03_new_data_physical_model_stability"
P2 = ROOT / "outputs" / "week7_02_sph_v2_target_extraction"
assert ROOT.name == "thesis-week7-phase3-new-data-model-stability"

pd.set_option("display.max_columns", 100)
pd.set_option("display.max_colwidth", 110)

summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
configuration = json.loads((OUT / "phase3_configuration.json").read_text(encoding="utf-8"))
provenance = json.loads((OUT / "input_provenance.json").read_text(encoding="utf-8"))
assert summary["mode"] == "full"
assert summary["dataset_revision"] == "d69dac5bda8b622bc0de316b112815c6056c06ec"
assert summary["starting_remote_head_sha"] == "f26f0671dd59938a8111883398fe38afedb6915d"
assert not any(configuration["scope"].values())
display(pd.DataFrame({
    "item": ["starting branch", "starting SHA", "dataset", "revision", "old/new pooled", "later phases run"],
    "value": [summary["starting_branch"], summary["starting_remote_head_sha"], summary["dataset_repo_id"],
              summary["dataset_revision"], summary["scope"]["old_new_pooled"], summary["scope"]["later_week7_phases"]],
}))
display(provenance)""",
        observation="The full run is tied to the exact corrected Phase 2 revision and the verified current remote Week 7 head. All later-phase and pooled-analysis scope flags are false.",
    )

    section(
        cells,
        2,
        "New-data model-ready population",
        what="Re-derive each target's eligibility directly from its saved Phase 2 readiness fields while retaining the complete label/audit table.",
        why="The genuinely monitor-incomplete experiment must remain auditable but must not receive a fabricated physical response.",
        question="How many new-data experiments are eligible for each target, and was any identifier exclusion list needed?",
        suspicious="A hard-coded count or experiment name, a dropped audit row, an old-data row, or a finite invented target for an unavailable monitor.",
        calculation="""population = pd.read_csv(OUT / "model_ready_population.csv")
population_long = pd.read_csv(OUT / "model_ready_population_long.csv")
target_specs = configuration["primary_targets"]
rows = []
for target, spec in target_specs.items():
    eligible = pd.Series(True, index=population.index)
    for field in spec["eligibility_fields"]:
        eligible &= population[field].astype(bool)
    eligible &= pd.to_numeric(population[spec["phase2_column"]], errors="coerce").notna()
    assert eligible.equals(population[f"{target}_model_eligible"].astype(bool))
    rows.append({"target": target, "audit_n": len(population), "eligible_n": int(eligible.sum()),
                 "ineligible_n": int((~eligible).sum()), "eligibility_fields": ", ".join(spec["eligibility_fields"])})
assert set(population["partition"]) == {"new-data"}
assert set(population_long["partition"]) == {"new-data"}
display(pd.DataFrame(rows))
display(population.loc[~population["physical_target_extraction_success"].astype(bool),
    ["experiment_name", "partition", "extraction_failure_reasons", "physical_target_extraction_success"]])""",
        observation=f"All {summary['audit_new_data_experiment_count']} new-data rows remain in the audit interface; readiness flags yield {summary['eligible_experiment_counts']} eligible physical-response experiments. The incomplete row is explicit and is absent only from model-ready response rows.",
    )

    section(
        cells,
        3,
        "Week 6 modelling traceability",
        what="Inspect a method-by-method table generated from the actual Week 6 source functions and configuration artifacts.",
        why="The scientific intervention is a new population, not a new modelling protocol.",
        question="Which implementation, settings, bounds, normalization, optimizers, seeds, and evaluation rules were reused or necessarily changed?",
        suspicious="A setting recalled from memory, an unrecorded hyperparameter search, new kernel, or random split.",
        calculation="""traceability = pd.read_csv(OUT / "week6_model_traceability.csv")
display(traceability[["week6_model_method", "source_file", "source_function_class",
                      "important_settings", "phase3_reuse_change", "reason"]])
assert traceability["phase3_reuse_change"].str.contains("reuse", case=False).any()
assert configuration["outer_evaluation"] == "exact simulation-level leave-one-out"
""",
        observation="The executable Week 6 preprocessing, target normalization, nested Ridge selection, GP kernels/bounds, L-BFGS-B optimizer, deterministic seeds, and LOO evaluation are reused. Smoke-only reductions are not present in this full run.",
    )

    section(
        cells,
        4,
        "Target scales and descriptive context",
        what="Summarize the four saved Phase 2 T0 target distributions and their median absolute scales.",
        why="Absolute errors cannot be interpreted across shifted designs or physical units without target-scale context.",
        question="What denominators will anchor the required relative MAE and RMSE percentages?",
        suspicious="A recomputed T0, maximum response substituted for T0, zero denominator, or mixed units.",
        calculation="""scale_table = (population_long.groupby(["target", "target_label", "target_unit"])["target_value_um"]
    .agg(n="size", minimum="min", median="median", mean="mean", maximum="max", std="std").reset_index())
scale_table["median_abs_denominator"] = population_long.groupby("target")["target_value_um"].apply(lambda x: np.median(np.abs(x))).values
display(scale_table)
display(Image(filename=str(OUT / "figures" / "01_new_data_target_scales.png"), width=920))""",
        observation="The target distributions and units differ substantially, so the remainder reports both native-unit errors and percentages of `median(abs(y_observed))`. No maximum, G3, or R3 response is promoted.",
    )

    section(
        cells,
        5,
        "Mean / Linear Ridge / Polynomial Ridge baselines",
        what="Recompute baseline MAE and RMSE visibly from the held-out rows and compare them with the stored aggregate table.",
        why="This verifies that the GP is judged against meaningful simple surfaces under the identical outer folds.",
        question="Does a smooth nonlinear GP add value beyond a training mean, linear response, or degree-2 polynomial approximation?",
        suspicious="Feature or polynomial leakage, a held-out target used in inner tuning, or aggregate metrics that do not reconcile.",
        calculation="""pred = pd.read_csv(OUT / "fold_level_predictions.csv")
metrics = pd.read_csv(OUT / "model_metric_table.csv")
baseline_names = ["training_mean", "linear_ridge", "polynomial_ridge_degree2"]
baseline_pred = pred[pred["model"].isin(baseline_names)].copy()
recomputed = (baseline_pred.groupby(["target", "model"])
    .apply(lambda g: pd.Series({
        "n": len(g),
        "MAE_from_folds": np.mean(np.abs(g["observed_target_value"] - g["predicted_mean"])),
        "RMSE_from_folds": np.sqrt(np.mean((g["observed_target_value"] - g["predicted_mean"])**2)),
        "heldout_used_for_tuning": g["heldout_target_used_for_tuning"].astype(bool).any(),
    }), include_groups=False).reset_index())
stored = metrics[metrics["model"].isin(baseline_names)][["target", "model", "MAE", "RMSE", "relative_RMSE_pct", "R2"]]
check = recomputed.merge(stored, on=["target", "model"], validate="one_to_one")
assert np.allclose(check["MAE_from_folds"], check["MAE"])
assert np.allclose(check["RMSE_from_folds"], check["RMSE"])
assert not check["heldout_used_for_tuning"].any()
display(check.sort_values(["target", "RMSE"]))""",
        observation="Each baseline has one simulation-level held-out prediction per eligible experiment. Scaling, polynomial construction, y normalization, and inner alpha selection are recorded as outer-training-only, and aggregate errors reconcile exactly.",
    )

    section(
        cells,
        6,
        "GP kernel comparison",
        what="Rank the learned-nugget RBF, Matérn 3/2, and Matérn 5/2 candidates by held-out error, while retaining the Week 6 paired replacement rule.",
        why="A raw minimum alone can be too fragile to justify changing a previously selected kernel.",
        question="Does Matérn 3/2 remain the strongest protocol choice for each physical response?",
        suspicious="A new kernel, large unplanned search, ranking based on training likelihood, or hidden convergence failures.",
        calculation="""kernels = pd.read_csv(OUT / "kernel_comparison.csv")
decisions = pd.read_csv(OUT / "model_selection_decisions.csv")
display(kernels[["target", "model", "kernel", "n", "MAE", "RMSE", "relative_RMSE_pct", "R2",
                 "NLPD", "coverage_95", "fit_failures", "warnings", "bound_hit_fraction"]])
display(decisions[["target", "best_learned_nugget_gp_by_RMSE", "protocol_selected_gp", "kernel_replacement_rationale"]])""",
        observation="The table distinguishes the empirical learned-kernel RMSE winner from the protocol-selected GP. A replacement occurs only if paired MAE and RMSE improve robustly without unacceptable calibration or optimization deterioration.",
    )

    section(
        cells,
        7,
        "Nugget / noise-treatment comparison",
        what="Compare Week 6 methods A (numerical jitter), B (shared learned WhiteKernel nugget), and C (per-simulation target-summary bootstrap alpha).",
        why="The central uncertainty question is whether the shared learned nugget remains useful on the new design.",
        question="Which treatment improves held-out point error, NLPD, or interval coverage under the current regression model?",
        suspicious="Calling the nugget physical noise, using held-out target variability as deployable information, or silently omitting Method C failures.",
        calculation="""noise = pd.read_csv(OUT / "noise_treatment_comparison.csv")
target_uncertainty = pd.read_csv(OUT / "target_summary_uncertainty.csv")
paired = pd.read_csv(OUT / "paired_model_comparisons.csv")
display(noise[["target", "model", "kernel", "noise_method", "RMSE", "relative_RMSE_pct", "NLPD", "coverage_95", "fit_failures"]])
display(decisions[["target", "learned_nugget_robust_point_advantage", "learned_nugget_calibration_advantage",
                   "learned_nugget_NLPD_advantage", "learned_shared_nugget_remains_useful"]])
assert target_uncertainty["bootstrap_resamples"].eq(500).all()
assert target_uncertainty["phase2_target_reproduced"].astype(bool).all()
display(target_uncertainty.groupby("target").agg(experiments=("experiment_name", "nunique"),
    median_bootstrap_variance=("bootstrap_variance", "median"), max_bootstrap_variance=("bootstrap_variance", "max")))""",
        observation="Method C is a target-summary uncertainty proxy and its interval is explicitly retrospective/oracle because held-out variability is unavailable prospectively. Any poor Method C result means only that this within-window proxy may not represent observation uncertainty well under the model.",
    )

    section(
        cells,
        8,
        "Primary out-of-sample model table",
        what="Display the clean ranking table and identify raw RMSE winners separately from protocol-selected point and probabilistic models.",
        why="No single model must be forced to win point accuracy, uncertainty calibration, and parsimony simultaneously.",
        question="Which model is best for each target, and where does a simpler competitive model remain the scientific choice?",
        suspicious="Training metrics, mixed target populations, unexplained fit omission, or one universal best-model claim.",
        calculation="""rankings = pd.read_csv(OUT / "model_rankings.csv")
primary_columns = ["target", "model_family", "kernel", "noise_method", "n", "MAE", "relative_MAE_pct",
                   "RMSE", "relative_RMSE_pct", "R2", "NLPD", "coverage_95", "fit_failures", "warnings", "rank_by_RMSE"]
for target in rankings["target"].drop_duplicates():
    display(Markdown(f"### {target}"))
    display(rankings[rankings["target"].eq(target)][primary_columns])
display(decisions[["target", "best_point_prediction_model_by_RMSE", "protocol_selected_point_model",
                   "protocol_selected_uncertainty_model", "best_calibrated_deployable_probabilistic_model"]])""",
        observation=f"The protocol choices are: {point_summary}. Raw point-error winners and best calibrated probabilistic models remain explicit in the same artifacts.",
    )

    section(
        cells,
        9,
        "Relative-error interpretation",
        what="Recompute `MAE/median(abs(y))*100` and `RMSE/median(abs(y))*100` from fold rows for the selected point model.",
        why="Median-scale percentages are more stable than pointwise MAPE near zero and are central to cross-design interpretation.",
        question="How large are the held-out errors relative to a typical target magnitude?",
        suspicious="MAPE as the primary percentage, an unstored denominator, or a denominator estimated on a different population.",
        calculation="""relative = pd.read_csv(OUT / "relative_error_table.csv")
selected_rows = []
for row in decisions.itertuples(index=False):
    g = pred[(pred["target"].eq(row.target)) & (pred["model"].eq(row.protocol_selected_point_model))]
    denom = np.median(np.abs(g["observed_target_value"]))
    mae = np.mean(np.abs(g["observed_target_value"] - g["predicted_mean"]))
    rmse = np.sqrt(np.mean((g["observed_target_value"] - g["predicted_mean"])**2))
    selected_rows.append({"target": row.target, "model": row.protocol_selected_point_model,
        "denominator": denom, "unit": g["target_unit"].iloc[0], "MAE": mae, "relative_MAE_pct": mae/denom*100,
        "RMSE": rmse, "relative_RMSE_pct": rmse/denom*100})
selected_relative = pd.DataFrame(selected_rows)
display(selected_relative)
assert not any("MAPE" in column.upper() for column in relative.columns)""",
        observation="Every target has an explicit positive median-absolute denominator. The native-unit and relative percentages in this cell are derived from exactly the same held-out observations.",
    )

    section(
        cells,
        10,
        "Observed-versus-predicted diagnostics",
        what="Inspect GP and Polynomial Ridge held-out predictions against the identity line for every primary target.",
        why="Aggregate errors can hide bias, compression, and a few influential simulations.",
        question="Do the selected GP and polynomial baseline track the full observed scale, and where are major outliers?",
        suspicious="In-sample predictions, unequal populations, deleted outliers, or axes that visually exaggerate agreement.",
        calculation="""for target in ["width", "depth", "total_height", "kinetic_energy"]:
    filename = next(p.name for p in (OUT / "figures").glob(f"*_{target}_observed_vs_predicted.png"))
    display(Markdown(f"### {target}"))
    display(Image(filename=str(OUT / "figures" / filename), width=900))""",
        observation="All points are simulation-level out-of-sample predictions. Identity lines and shared axes expose both scale compression and major errors; no observation is removed because it hurts a model.",
    )

    section(
        cells,
        11,
        "Residual and error-versus-scale diagnostics",
        what="Inspect residual distributions and absolute error versus observed response scale for each target.",
        why="Model rankings are incomplete without checking skew, heteroscedasticity, and influential cases.",
        question="Are errors centered, and do they grow systematically with target magnitude?",
        suspicious="A strongly shifted residual distribution, unexplained scale trend, or outlier deletion.",
        calculation="""residuals = pd.read_csv(OUT / "residual_diagnostics.csv")
for target in ["width", "depth", "total_height", "kinetic_energy"]:
    display(Markdown(f"### {target}"))
    residual_file = next(p for p in (OUT / "figures").glob(f"*_{target}_residual_distribution.png"))
    scale_file = next(p for p in (OUT / "figures").glob(f"*_{target}_error_vs_observed_scale.png"))
    display(Image(filename=str(residual_file), width=760))
    display(Image(filename=str(scale_file), width=760))
display(residuals[residuals["major_outlier_flag_top3"].astype(bool)]
    [["target", "model", "experiment_name", "observed_target_value", "predicted_mean", "absolute_error"]]
    .sort_values(["target", "model", "absolute_error"], ascending=[True, True, False]).head(40))""",
        observation="Major errors are flagged conservatively for inspection, not excluded. Their experiment identifiers remain linked to every fold-level prediction and the complete audit population.",
    )

    section(
        cells,
        12,
        "Predictive interval and calibration diagnostics",
        what="Compare held-out 95% coverage, NLPD, interval widths, and standardized residual behavior for deployable GP intervals and retrospective Method C intervals.",
        why="A low point RMSE does not guarantee calibrated predictive uncertainty.",
        question="Which probabilistic model is best calibrated, and is the shared-nugget conclusion supported beyond point error?",
        suspicious="Intervals with reversed bounds, a mean outside its own interval, treating Method C as deployable, or claiming exact 95% coverage is guaranteed.",
        calculation="""intervals = pd.read_csv(OUT / "predictive_interval_diagnostics.csv")
interval_rows = pred[pred["predictive_interval_lower"].notna()]
assert (interval_rows["predictive_interval_lower"] <= interval_rows["predicted_mean"]).all()
assert (interval_rows["predicted_mean"] <= interval_rows["predictive_interval_upper"]).all()
display(intervals.sort_values(["target", "coverage_error_from_0_95", "model"]))
for target in ["width", "depth", "total_height", "kinetic_energy"]:
    filename = next(p for p in (OUT / "figures").glob(f"*_{target}_predictive_interval_calibration.png"))
    display(Image(filename=str(filename), width=860))""",
        observation="Calibration is assessed independently from point ranking. Method C remains labeled retrospective/oracle; learned-nugget gains are predictive-model evidence, not proof that the simulator or physical measurements are noisy.",
    )

    section(
        cells,
        13,
        "Week 6 versus new-data stability comparison",
        what="Place saved Week 6 old-design results beside the independent new-data results without refitting or pooling the old population.",
        why="Replication concerns ranking, relative error, kernel/noise preference, and calibration—not absolute native-unit errors alone across shifted target distributions.",
        question="Did the new sampled parameter domain materially change model difficulty or the qualitative conclusions?",
        suspicious="A pooled primary model, a claim based only on absolute RMSE, or a causal claim that the physics became more complex.",
        calculation="""historical = pd.read_csv(OUT / "week6_vs_new_data_comparison.csv")
display(historical)
display(Image(filename=str(next((OUT / "figures").glob("*_week6_vs_new_data_relative_rmse.png"))), width=900))
assert not historical["dataset_populations_pooled"].astype(bool).any()""",
        observation="The table reports both historical and new medians, relative errors, model/kernel selections, nugget conclusions, and GP-versus-polynomial gaps. Difficulty statements refer only to predictive error in the shifted sampled domain.",
    )

    section(
        cells,
        14,
        "Target-by-target conclusions",
        what="Answer the ten stability questions and classify each Week 6 conclusion as reproduced, weakened, reversed, or unresolved.",
        why="A replication should state exactly which conclusions survived and which did not.",
        question="Can the Week 6 physical-response modelling pipeline proceed unchanged on the new design?",
        suspicious="A blanket success claim, one model forced to win every metric, or interpretation beyond model-comparison evidence.",
        calculation="""conclusions = pd.read_csv(OUT / "stability_conclusion_table.csv")
display(conclusions[["question", "target", "week6_conclusion", "new_data_evidence", "status", "evidence"]])
display(conclusions.groupby("status").size().rename("count").reset_index())
display(Image(filename=str(next((OUT / "figures").glob("*_conclusion_stability_counts.png"))), width=700))""",
        observation=f"The explicit evidence table contains {status_counts}. These labels separate observed model ranking from interpretation and leave genuinely mixed evidence unresolved.",
    )

    section(
        cells,
        15,
        "Validation and hard stop",
        what="Display every automatic validation and requirement mapping, then assert the Phase 3 scope boundary.",
        why="Scientific conclusions are usable only if population, folds, metrics, artifacts, and notebook execution reconcile.",
        question="Did the full Phase 3 satisfy its requested checks without beginning later Week 7 work?",
        suspicious="A failed validation, missing output, stored notebook error, modified label, silent row removal, classifier, active-learning, or level-set artifact.",
        calculation="""validation = pd.read_csv(OUT / "validation_results.csv")
checklist = pd.read_csv(OUT / "requirement_checklist.csv")
manifest = pd.read_csv(OUT / "output_manifest.csv")
kinetic_scope = pd.read_csv(OUT / "kinetic_energy_scope_caution.csv")
display(validation)
display(validation.groupby("status").size().rename("count").reset_index())
display(checklist)
display(kinetic_scope)
assert not validation["status"].eq("FAIL").any()
assert not population["source_label_modified"].astype(bool).any()
assert not population["simulation_silently_removed"].astype(bool).any()
assert not any(configuration["scope"].values())
display(Markdown(f"**Manifest:** {len(manifest)} files are recorded under the Phase 3 output root."))""",
        observation="The full analysis stops here. No Keyhole classifier, feature-effect or causal interpretation, T0-versus-maximum target decision, extreme-event classifier, active learning, level-set estimation, acquisition change, or pooled production model has run.",
    )

    notebook = nbf.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
            "phase": "Week 7 Phase 3",
            "dataset_revision": summary["dataset_revision"],
            "starting_remote_head_sha": summary["starting_remote_head_sha"],
            "builder": "scripts/build_week7_03_notebook.py",
        },
    )
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, NOTEBOOK)
    client = NotebookClient(
        notebook,
        timeout=1200,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
        allow_errors=False,
    )
    executed = client.execute()
    nbf.write(executed, NOTEBOOK)
    print(f"wrote and executed {NOTEBOOK}")


if __name__ == "__main__":
    main()
