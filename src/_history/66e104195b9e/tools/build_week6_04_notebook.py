#!/usr/bin/env python
"""Build the executed-report notebook for Week 6 Phase 3."""

from __future__ import annotations

from pathlib import Path
import textwrap

import nbformat as nbf
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week6_03_model_target_robustness"
NOTEBOOK = (
    ROOT / "notebooks" / "week_06" / "04_phase3_model_target_robustness.ipynb"
)


def md(text: str):
    return nbf.v4.new_markdown_cell(textwrap.dedent(text).strip())


def code(text: str):
    return nbf.v4.new_code_cell(textwrap.dedent(text).strip())


def phase3a_result_markdown() -> str:
    comparisons = pd.read_csv(
        OUTPUT / "simple_baseline_paired_bootstrap_summary.csv"
    )
    decisions = pd.read_csv(OUTPUT / "phase3_final_model_decision.csv")
    lines = [
        "### What the Phase 3A result means",
        "",
    ]
    for target in ["width", "length", "depth"]:
        decision = decisions.loc[decisions["target"] == target].iloc[0]
        target_comparisons = comparisons.loc[
            comparisons["target"] == target
        ]
        statements = []
        for _, row in target_comparisons.iterrows():
            statements.append(
                f"`{row['candidate_model']}` minus GP RMSE "
                f"{row['observed_rmse_difference_um']:+.3f} µm "
                f"(95% CI {row['rmse_difference_ci95_lower_um']:+.3f} to "
                f"{row['rmse_difference_ci95_upper_um']:+.3f})"
            )
        lines.append(
            f"- **{target.capitalize()}:** "
            + "; ".join(statements)
            + f". Final point-model decision: "
            f"`{decision['selected_final_model']}`."
        )
    lines.extend(
        [
            "",
            "**Why it matters.** A GP is only necessary for point prediction if "
            "its paired advantage is statistically robust and practically "
            "meaningful. If a Ridge model is competitive, parsimony favors the "
            "simpler point model.",
            "",
            "**What cannot be concluded.** Ridge has no directly comparable GP "
            "predictive distribution in this experiment. Similar point error does "
            "not mean that Ridge inherits GP uncertainty, NLPD, or coverage.",
        ]
    )
    return "\n".join(lines)


def phase3b_result_markdown() -> str:
    bootstrap = pd.read_csv(OUTPUT / "gp_kernel_paired_bootstrap_summary.csv")
    within = bootstrap.loc[bootstrap["summary_scope"] == "within_kernel"]
    decisions = pd.read_csv(OUTPUT / "provisional_kernel_decision.csv")
    nuggets = pd.read_csv(OUTPUT / "learned_nugget_by_kernel_summary.csv")
    lines = ["### What the Phase 3B result means", ""]
    for target in ["width", "length", "depth"]:
        decision = decisions.loc[decisions["target"] == target].iloc[0]
        lines.append(
            f"- **{target.capitalize()}:** provisional GP "
            f"`{decision['selected_provisional_gp_configuration']}`; "
            f"another kernel replaces the current model = "
            f"`{bool(decision['another_kernel_replaces_current'])}`."
        )
        for family in ["RBF", "Matérn 3/2", "Matérn 5/2"]:
            row = within.loc[
                (within["target"] == target)
                & (within["kernel_family_comparison"] == family)
            ].iloc[0]
            lines.append(
                f"  - {family}: nugget − no-nugget RMSE "
                f"{row['observed_rmse_difference_um']:+.3f} µm "
                f"(95% CI {row['rmse_difference_ci95_lower_um']:+.3f} to "
                f"{row['rmse_difference_ci95_upper_um']:+.3f}); "
                f"{row['nugget_conclusion']}."
            )
        current_nugget = nuggets.loc[
            (nuggets["target"] == target)
            & (
                nuggets["gp_configuration"]
                == "matern32_learned_nugget"
            )
        ].iloc[0]
        lines.append(
            f"  - Current Matérn 3/2 median learned nugget standard deviation: "
            f"{current_nugget['nugget_std_um_median']:.3f} µm."
        )
    lines.extend(
        [
            "",
            "**Why it matters.** The within-family comparisons distinguish a "
            "genuinely useful nugget from one that only patched Matérn 3/2 "
            "mismatch. The candidate-versus-current comparisons then ask whether "
            "a different smoothness family deserves replacement.",
            "",
            "**What cannot be concluded.** These are isotropic kernels under the "
            "same four inputs. They do not identify causal feature effects, and a "
            "learned nugget is not proof of stochastic simulator noise.",
        ]
    )
    return "\n".join(lines)


def phase3c_result_markdown() -> str:
    differences = pd.read_csv(
        OUTPUT / "target_definition_difference_summary.csv"
    )
    decisions = pd.read_csv(OUTPUT / "target_definition_decision.csv")
    lines = ["### What the Phase 3C result means", ""]
    for target in ["width", "length", "depth"]:
        alternatives = differences.loc[
            (differences["target"] == target)
            & (differences["target_definition"] != "T0")
        ]
        largest = alternatives.sort_values(
            "median_absolute_difference_from_t0_um", ascending=False
        ).iloc[0]
        decision = decisions.loc[decisions["target"] == target].iloc[0]
        lines.append(
            f"- **{target.capitalize()}:** largest median absolute shift is "
            f"{largest['target_definition']} at "
            f"{largest['median_absolute_difference_from_t0_um']:.3f} µm "
            f"(q95 {largest['q95_absolute_difference_from_t0_um']:.3f} µm). "
            f"Selected target = `{decision['selected_target_definition']}`; "
            f"substantial sensitivity = "
            f"`{bool(decision['target_definition_sensitivity_substantial'])}`."
        )
    lines.extend(
        [
            "",
            "**Why it matters.** A model can predict an alternative target more "
            "easily simply because the physical quantity changed. The target "
            "decision therefore combines availability, temporal stability, "
            "domain-exit control, physical meaning, and paired predictability.",
            "",
            "**What cannot be concluded.** The target-shift scale is not the same "
            "thing as the GP nugget. Phase 3C holds one GP fixed per response, so "
            "it does not re-run kernel selection separately for T1–T5.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    required = [
        "phase3_configuration.json",
        "phase3_input_population_summary.csv",
        "simple_baseline_metrics.csv",
        "simple_baseline_paired_bootstrap_summary.csv",
        "gp_kernel_noise_metrics.csv",
        "gp_kernel_paired_bootstrap_summary.csv",
        "provisional_kernel_decision.csv",
        "target_definition_distribution_summary.csv",
        "target_definition_difference_summary.csv",
        "target_definition_model_metrics.csv",
        "target_definition_decision.csv",
        "phase3_final_model_decision.csv",
        "phase3_final_target_decision.csv",
        "validation_results.csv",
        "phase3_requirement_checklist.csv",
    ]
    missing = [name for name in required if not (OUTPUT / name).exists()]
    if missing:
        raise RuntimeError(f"Cannot build Phase 3 notebook; missing {missing}")

    nb = nbf.v4.new_notebook()
    nb.metadata.kernelspec = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    nb.metadata.language_info = {"name": "python", "version": "3.14"}
    cells = [
        md(
            r"""
            # Week 6 Phase 3 — model-and-target robustness

            **Burak Öztürk · TUM Mathematics MSc thesis**

            This notebook is an executed, human-readable report of the exact
            simulation-level experiment. The reusable source performs the long
            fits with checkpoints; this notebook loads the validated outputs and
            explains what they do and do not establish.

            ```text
            Phase 3
            ├── simple-model test
            ├── kernel/nugget test
            └── target-definition test
            ```

            Strict scope: no ARD, feature importance, causal feature-effect
            claim, kinetic energy, total height, active learning, level-set
            estimation, or GP classification.

            ## §0 — provenance, populations, and common protocol

            All predictions use exactly `X = [P, VX, LS, ST]`. Targets are
            converted only by \(y_{\mu m}=10^6 y_m\). Width and length use all
            241 simulations; depth uses the exact 230 stable simulations fixed
            in Phase 2.5.
            """
        ),
        code(
            """
            from pathlib import Path
            import json
            import pandas as pd
            from IPython.display import Image, display

            ROOT = Path.cwd()
            OUT = ROOT / "outputs" / "week6_03_model_target_robustness"
            FIG = OUT / "figures"
            config = json.loads((OUT / "phase3_configuration.json").read_text(encoding="utf-8"))
            populations = pd.read_csv(OUT / "phase3_input_population_summary.csv")
            runtime = json.loads((OUT / "phase3_runtime_provenance.json").read_text(encoding="utf-8"))

            print("Branch:", runtime["repository"]["branch"])
            print("HEAD:", runtime["repository"]["head"])
            print("Phase 1 revision:", config["phase1_revision"])
            print("Ledger SHA-256:", config["phase1_ledger_sha256"])
            display(populations[["target", "population_size", "excluded_count",
                                 "target_min_um", "target_median_um", "target_max_um"]])
            display(Image(filename=str(FIG / "01_phase3_experiment_tree.png")))
            """
        ),
        md(
            """
            **What was done.** The immutable revision, ledger hash, worktree, four
            features, and three target-specific populations were loaded before any
            result.

            **Why.** A robustness comparison is only fair when every model sees the
            same simulations, outer fold order, units, and inputs.

            **What the result means.** The table is the population contract for all
            later cells; depth alone excludes the eleven predeclared unstable IDs.

            **What cannot be concluded.** Provenance checks establish
            reproducibility, not physical correctness by themselves.
            """
        ),
        md(
            r"""
            ## Part 1 — Phase 3A: simple baselines

            **Ridge** is linear regression with **regularization**, a penalty that
            discourages very large coefficients. If two coefficients fit almost
            equally well, Ridge prefers the more restrained solution.

            **Polynomial features** add transformed inputs before regression. At
            degree 2, four inputs become their original terms, four squares, and
            six pairwise interactions. For a toy input \((x_1,x_2)\), the added
            terms are \(x_1^2,x_1x_2,x_2^2\). No degree above 2 is searched.

            **Nested cross-validation** separates tuning from evaluation.

            - The **outer LOO** (leave-one-out) fold holds out exactly one
              simulation for the scientific prediction.
            - The **inner CV** splits only the remaining outer-training simulations
              into five folds to select Ridge's alpha.

            Thus the held-out target never chooses preprocessing or alpha.

            A **paired bootstrap** resamples simulation IDs jointly for two models.
            A 95% **confidence interval** is the middle 95% of 10,000 paired
            resampled differences. Here “simple model − GP” below zero favors the
            simple model; an interval crossing zero is statistically non-robust.
            """
        ),
        code(
            """
            simple_metrics = pd.read_csv(OUT / "simple_baseline_metrics.csv")
            simple_pairs = pd.read_csv(OUT / "simple_baseline_paired_bootstrap_summary.csv")
            display(simple_metrics[["target", "model", "mae_um",
                                    "median_absolute_error_um", "rmse_um",
                                    "r2", "nrmse",
                                    "aggregate_fold_runtime_seconds"]])
            display(simple_pairs[["target", "candidate_model",
                                  "observed_mae_difference_um",
                                  "mae_difference_ci95_lower_um",
                                  "mae_difference_ci95_upper_um",
                                  "observed_rmse_difference_um",
                                  "rmse_difference_ci95_lower_um",
                                  "rmse_difference_ci95_upper_um",
                                  "simple_model_competitive"]])
            display(Image(filename=str(FIG / "02_simple_model_performance_comparison.png")))
            """
        ),
        md(phase3a_result_markdown()),
        code(
            """
            ridge_hyper = pd.read_csv(OUT / "simple_baseline_selected_hyperparameters.csv")
            alpha_summary = (ridge_hyper
                             .groupby(["target", "model"])["selected_ridge_alpha"]
                             .agg(["min", "median", "max", "nunique"])
                             .reset_index())
            display(alpha_summary)
            print("Every row used five inner folds:",
                  set(ridge_hyper["inner_cv_folds"].astype(int)))
            print("Alpha grid:", config["phase3a"]["ridge_alpha_grid"])
            """
        ),
        md(
            """
            **What was done.** The selected alpha was retained for every outer
            fold, and its distribution is shown rather than hiding tuning
            variability.

            **Why.** Fold-specific alpha choices verify that tuning occurred inside
            each outer training set.

            **What the result means.** A broad alpha distribution indicates that
            the preferred amount of shrinkage changes when one simulation is
            removed; a narrow distribution indicates stable tuning.

            **What cannot be concluded.** Alpha magnitude is not a feature-effect
            measure and does not identify which physical input is important.
            """
        ),
        md(
            r"""
            ## Part 2 — Phase 3B: kernel and nugget robustness

            A GP kernel specifies how outputs co-vary with input distance.

            - **RBF** is very smooth.
            - **Matérn 3/2** allows rougher functions.
            - **Matérn 5/2** is intermediate between RBF and Matérn 3/2.
            - The **lengthscale** controls how quickly correlation falls with
              standardized input distance: a smaller value permits faster change.
            - `ConstantKernel × base kernel` controls the overall vertical
              covariance or **signal variance**. It does *not* add a constant
              prediction to the mean. The base kernel controls how correlation
              decays; the ConstantKernel controls how large function variation may
              be.
            - **WhiteKernel** learns a diagonal effective **nugget**. It can absorb
              target instability, omitted structure, numerical/model discrepancy,
              or kernel mismatch; it is not automatically simulator noise.
            - Tiny numerical **jitter** (`alpha`) stabilizes matrix calculations
              and is kept separate from the learned nugget.

            **NLPD** (negative log predictive density) scores both prediction error
            and predicted uncertainty; lower is better. **Calibration** asks
            whether, for example, about 95% of observations fall inside nominal
            95% intervals. Perfect point error does not guarantee good calibration.
            """
        ),
        code(
            """
            gp_metrics = pd.read_csv(OUT / "gp_kernel_noise_metrics.csv")
            gp_pairs = pd.read_csv(OUT / "gp_kernel_paired_bootstrap_summary.csv")
            provisional = pd.read_csv(OUT / "provisional_kernel_decision.csv")
            display(gp_metrics[["target", "gp_configuration", "mae_um", "rmse_um",
                                "mean_nlpd", "latent_95_coverage",
                                "total_95_coverage", "optimizer_warning_folds",
                                "any_bound_hit_folds"]])
            display(provisional[["target", "selected_provisional_gp_configuration",
                                 "another_kernel_replaces_current", "rationale"]])
            display(Image(filename=str(FIG / "03_gp_kernel_noise_rmse_comparison.png")))
            display(Image(filename=str(FIG / "04_nugget_vs_no_nugget_paired_confidence_intervals.png")))
            """
        ),
        md(phase3b_result_markdown()),
        code(
            """
            nugget_summary = pd.read_csv(OUT / "learned_nugget_by_kernel_summary.csv")
            diagnostics = pd.read_csv(OUT / "gp_kernel_noise_hyperparameter_diagnostics.csv")
            display(nugget_summary[["target", "gp_configuration",
                                    "nugget_std_um_median",
                                    "nugget_fraction_training_target_std_median",
                                    "nugget_fraction_dataset_target_median_median",
                                    "nugget_bound_hit_folds", "warning_folds"]])
            display(Image(filename=str(FIG / "05_provisional_models_observed_vs_loo_predicted.png")))
            display(Image(filename=str(FIG / "06_learned_nugget_std_by_kernel_and_target.png")))
            print("Failed GP folds:", int(diagnostics["failed_fold"].astype(bool).sum()))
            print("Warning folds:", int((diagnostics["warning_count"] > 0).sum()))
            print("Any bound-hit folds:", int(diagnostics["any_hyperparameter_bound_hit"].astype(bool).sum()))
            """
        ),
        md(
            """
            **What was done.** Fold-level optimized signal variance, isotropic
            lengthscale, nugget, warnings, and bound hits were summarized beside
            observed-versus-predicted plots.

            **Why.** A small RMSE gain is not a trustworthy replacement if it
            depends on unstable optimization or systematic boundary solutions.

            **What the result means.** Nugget sizes are shown in micrometres and
            relative to both the fold's training-target standard deviation and the
            population target median. These are scale diagnostics.

            **What cannot be concluded.** The learned lengthscale is isotropic and
            cannot be read as a separate effect for P, VX, LS, or ST.
            """
        ),
        md(
            r"""
            ## Part 3 — Phase 3C: target-definition sensitivity

            **Target-definition sensitivity** is the change in target values,
            stability, model performance, or learned nugget caused by a reasonable
            change in the simulation-level summary rule.

            - **Pearson correlation** measures linear association. For example,
              points exactly on a rising straight line have Pearson correlation 1.
            - **Spearman correlation** measures rank association. If every
              simulation keeps the same ordering but the scale bends
              nonlinearly, Spearman can remain 1 while Pearson falls.

            T0–T4 use valid non-sentinel melt rows inside a controlled active
            window. T5 is the mean of the final 50 valid rows where available and
            is retained as a reference because it can include shutdown or
            post-domain-exit behavior. The Phase 3B provisional GP is fixed per
            response across all six definitions.
            """
        ),
        code(
            """
            target_distribution = pd.read_csv(OUT / "target_definition_distribution_summary.csv")
            target_difference = pd.read_csv(OUT / "target_definition_difference_summary.csv")
            display(target_distribution[["target", "target_definition",
                                         "availability_count", "target_median_um",
                                         "window_count_median",
                                         "within_window_cv_median",
                                         "fraction_unstable_windows",
                                         "simulations_with_rows_after_full_domain_exit"]])
            display(target_difference[["target", "target_definition",
                                       "pearson_correlation_with_t0",
                                       "spearman_correlation_with_t0",
                                       "median_absolute_difference_from_t0_um",
                                       "q95_absolute_difference_from_t0_um",
                                       "fraction_absolute_difference_exceeds_1_um",
                                       "fraction_absolute_difference_exceeds_current_learned_nugget_std",
                                       "fraction_absolute_difference_exceeds_5pct_t0"]])
            for target in ["width", "length", "depth"]:
                display(Image(filename=str(FIG / f"07_target_definition_scatter_{target}.png")))
            """
        ),
        md(phase3c_result_markdown()),
        code(
            """
            target_metrics = pd.read_csv(OUT / "target_definition_model_metrics.csv")
            target_nuggets = pd.read_csv(OUT / "target_definition_nugget_summary.csv")
            target_decisions = pd.read_csv(OUT / "target_definition_decision.csv")
            display(target_metrics[["target", "target_definition",
                                    "gp_configuration", "mae_um", "rmse_um",
                                    "r2", "nrmse", "mean_nlpd",
                                    "evaluation_95_coverage",
                                    "optimizer_warning_folds",
                                    "any_bound_hit_folds"]])
            display(target_nuggets[["target", "target_definition",
                                    "gp_configuration",
                                    "nugget_std_um_median",
                                    "warning_folds", "any_bound_hit_folds"]])
            display(Image(filename=str(FIG / "08_target_definition_absolute_difference_distributions.png")))
            display(Image(filename=str(FIG / "09_target_stability_vs_predictability.png")))
            display(Image(filename=str(FIG / "10_learned_nugget_vs_target_definition_shift.png")))
            """
        ),
        md(
            """
            **What was done.** Exact outer LOO was repeated for T0–T5 with the
            response-specific provisional GP held fixed. Predictability, NLPD,
            coverage, interval width, nugget, and optimizer behavior were retained.

            **Why.** Holding the GP fixed prevents a new kernel search from being
            confused with the target-definition change.

            **What the result means.** The stability-versus-nRMSE plot reveals
            trade-offs, while the nugget-versus-shift plot compares scales only.
            A lower RMSE does not by itself make an alternative target physically
            preferable.

            **What cannot be concluded.** Phase 3C does not prove which temporal
            definition is physically true, and the two scales in the last figure
            measure different concepts.
            """
        ),
        code(
            """
            display(target_decisions[["target", "selected_target_definition",
                                      "t0_retained",
                                      "target_definition_sensitivity_substantial",
                                      "fixed_gp_performance_or_nugget_materially_sensitive",
                                      "rationale", "physical_quantity_change"]])
            """
        ),
        md(
            """
            **What was done.** Each response was evaluated against the predeclared
            target rule: physical meaning, temporal stability, availability,
            robust paired predictability, domain-exit control, and optimizer
            stability.

            **Why.** This prevents a mechanically easy-to-predict but contaminated
            target from replacing T0.

            **What the result means.** A retained T0 preserves the Phase 1 physical
            quantity. If sensitivity is substantial without a superior
            alternative, that uncertainty remains an explicit limitation.

            **What cannot be concluded.** Retaining T0 does not claim that all
            alternatives are numerically identical.
            """
        ),
        md(
            """
            ## Final Phase 3 scorecard and validation

            The final point model may be simpler than the provisional GP. When that
            occurs, the provisional GP remains the tested uncertainty model because
            Phase 3 did not invent Ridge intervals after the fact.
            """
        ),
        code(
            """
            final_models = pd.read_csv(OUT / "phase3_final_model_decision.csv")
            final_targets = pd.read_csv(OUT / "phase3_final_target_decision.csv")
            validation = pd.read_csv(OUT / "validation_results.csv")
            checklist = pd.read_csv(OUT / "phase3_requirement_checklist.csv")
            display(final_models)
            display(final_targets)
            display(Image(filename=str(FIG / "11_phase3_final_decision_scorecard.png")))
            print("Validation:", int((validation["status"] == "PASS").sum()),
                  "/", len(validation), "PASS")
            display(validation)
            print("Requirement checklist:", int((checklist["status"] == "PASS").sum()),
                  "/", len(checklist), "PASS")
            """
        ),
        md(
            """
            **What was done.** Final response-specific model and target decisions
            were displayed with the complete automated validation and requirement
            map.

            **Why.** A scientific conclusion is only usable when its provenance,
            predictions, uncertainty algebra, tuning isolation, raw-target
            traceability, notebook execution, repository safety, and scope are all
            checked.

            **What the result means.** A complete PASS establishes internal
            reproducibility for this Phase 3 protocol.

            **What cannot be concluded.** Validation does not turn statistically
            uncertain differences into robust ones, and Phase 4 topics remain
            deferred.
            """
        ),
    ]
    nb.cells = cells
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, NOTEBOOK)
    print(f"built {NOTEBOOK}")


if __name__ == "__main__":
    main()
