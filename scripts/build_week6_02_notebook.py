"""Build the executable Week 6 Phase 2 evidence notebook."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = (
    ROOT
    / "notebooks"
    / "week_06"
    / "02_gp_response_noise_comparison.ipynb"
)


def markdown(source: str, *, tags: list[str] | None = None):
    cell = nbf.v4.new_markdown_cell(dedent(source).strip())
    if tags:
        cell.metadata["tags"] = tags
    return cell


def code(source: str, *, tags: list[str] | None = None):
    cell = nbf.v4.new_code_cell(dedent(source).strip())
    if tags:
        cell.metadata["tags"] = tags
    return cell


def build_notebook() -> None:
    cells = [
        markdown(
            """
            # Week 6, Phase 2 — GP observation-treatment comparison

            ## 1. Scope

            This notebook explains the complete 241-simulation comparison of
            three observation treatments for melt-pool width, length, and
            penetration depth. The covariance family is fixed to
            `ConstantKernel × isotropic Matérn 3/2`, so observed differences
            can be attributed to how the simulation-level targets are treated.

            No new kernel family, ARD, feature-effect analysis, active
            learning, level-set estimation, classifier, or new label analysis
            is performed.

            Rebuild command:

            ```powershell
            .\\.venv\\Scripts\\python.exe src\\week6_phase2_gp_response_noise_comparison.py --full --force --workers 4
            ```
            """,
            tags=["scope"],
        ),
        code(
            """
            from pathlib import Path
            import json
            import numpy as np
            import pandas as pd
            from IPython.display import Image, display

            START = Path.cwd().resolve()
            ROOT = next(
                (
                    candidate
                    for candidate in (START, *START.parents)
                    if (
                        candidate
                        / "outputs"
                        / "week6_02_gp_response_noise_comparison"
                    ).is_dir()
                ),
                None,
            )
            if ROOT is None:
                raise FileNotFoundError(
                    "Could not locate the repository from the notebook "
                    "working directory."
                )
            OUT = ROOT / "outputs" / "week6_02_gp_response_noise_comparison"
            PHASE1 = (
                ROOT
                / "outputs"
                / "week6_01_melt_pool_data_audit"
                / "week6_phase1_simulation_level_responses.csv"
            )
            config = json.loads(
                (OUT / "phase2_model_configuration.json").read_text(
                    encoding="utf-8"
                )
            )
            summary = json.loads(
                (OUT / "summary.json").read_text(encoding="utf-8")
            )
            pd.Series({
                "Phase 1 rows": summary["phase1_rows"],
                "immutable revision": summary["phase1_revision"],
                "features": summary["features"],
                "targets": list(summary["targets"]),
                "primary LOO models": summary["primary_loo_model_count"],
            })
            """,
            tags=["provenance"],
        ),
        markdown(
            """
            The source is the corrected Phase 1 ledger at one immutable
            Hugging Face revision. The study contains nine primary comparisons:
            three responses multiplied by three observation treatments.

            ## 2. Input and leakage policy
            """
        ),
        code(
            """
            input_table = pd.read_csv(OUT / "phase2_input_target_table.csv")
            feature_columns = ["P", "VX", "LS", "ST"]
            target_columns = [
                "width_target_um",
                "length_target_um",
                "depth_target_um",
            ]
            checks = pd.Series({
                "241 rows": len(input_table) == 241,
                "unique simulation IDs": input_table["simulation_id"].is_unique,
                "four finite inputs": np.isfinite(
                    input_table[feature_columns].to_numpy(float)
                ).all(),
                "three finite positive targets": (
                    np.isfinite(
                        input_table[target_columns].to_numpy(float)
                    ).all()
                    and (
                        input_table[target_columns].to_numpy(float) > 0
                    ).all()
                ),
                "exact feature policy": config["feature_columns"] == feature_columns,
            })
            display(checks)
            assert checks.all()
            """,
            tags=["input-policy"],
        ),
        markdown(
            """
            Only `P`, `VX`, `LS`, and `ST` enter the GP. IDs, timestamps,
            window diagnostics, target summaries, flags, provenance, and every
            target-derived field are excluded. Flags are used only for the
            later sensitivity subset.

            ## 3. What the three observation treatments mean
            """
        ),
        code(
            """
            pd.DataFrame(config["approaches"]).T[
                ["kernel", "interpretation"]
            ]
            """,
            tags=["observation-treatments"],
        ),
        markdown(
            """
            **A — tiny jitter:** `alpha=1e-6` in normalized units prevents
            numerical singularities. It is not a scientific noise estimate.

            **B — learned nugget:** WhiteKernel learns one shared effective
            discrepancy variance per fold. It can absorb target-summary
            variability, unmodelled inputs, fixed-kernel misspecification, and
            other residual discrepancy. It does not directly measure the
            target-definition error and is not stochastic simulator noise.

            **C — observation-specific alpha:** each simulation and response
            gets its own target-summary uncertainty proxy. Deterministic
            simulation does not make a finite-window median exact: the median
            can still depend on temporal variation and where the selected
            window lies.

            ## 4. Moving-block bootstrap uncertainty
            """
        ),
        code(
            """
            uncertainty = pd.read_csv(
                OUT / "target_summary_uncertainty_estimates.csv"
            )
            display(
                uncertainty.groupby("target").agg(
                    simulations=("simulation_id", "nunique"),
                    median_window_rows=(
                        "selected_window_observation_count",
                        "median",
                    ),
                    median_block_length=("block_length", "median"),
                    median_std_um=("bootstrap_median_std_um", "median"),
                    q95_std_um=(
                        "bootstrap_median_std_um",
                        lambda x: x.quantile(0.95),
                    ),
                    maximum_std_um=("bootstrap_median_std_um", "max"),
                )
            )
            assert len(uncertainty) == 723
            assert uncertainty["phase1_target_reproduced"].all()
            """,
            tags=["target-summary-bootstrap"],
        ),
        markdown(
            """
            Each selected window is resampled with contiguous circular blocks,
            not independent rows, because adjacent timesteps are temporally
            correlated. Five hundred resamples estimate the variance of the
            window median. The result describes stability of the chosen target
            summary; it is neither measurement error nor simulator randomness.
            Different temporal traces naturally produce different alpha values.
            """
        ),
        code(
            """
            block_sensitivity = pd.read_csv(
                OUT / "block_bootstrap_sensitivity.csv"
            )
            display(
                block_sensitivity[
                    [
                        "target",
                        "variability_class",
                        "simulation_id",
                        "block_scenario",
                        "block_length",
                        "bootstrap_median_std_um",
                        "std_ratio_to_base",
                        "qualitatively_stable_vs_base",
                    ]
                ]
            )
            """,
            tags=["block-sensitivity"],
        ),
        markdown(
            """
            Low-, middle-, and high-variability examples were repeated with
            half and double block lengths. Ratios show whether the qualitative
            magnitude of the uncertainty estimate survives this modelling
            choice; disagreement is a limitation, not a reason to silently
            tune the block length.

            ## 5. Fold-local scaling and predictive uncertainty
            """
        ),
        code(
            """
            width_predictions = pd.read_csv(
                OUT / "width_loo_predictions.csv"
            )
            example = width_predictions.loc[
                width_predictions["method"] == "C_heteroskedastic"
            ].iloc[0]
            variance_um2 = example["heldout_target_summary_variance_um2"]
            training_std_um = example["training_y_std_um"]
            normalized_variance_example = (
                variance_um2 / training_std_um**2 + 1e-6
            )
            pd.Series({
                "held-out simulation": example["heldout_simulation_id"],
                "training y std (µm)": training_std_um,
                "held-out proxy variance (µm²; oracle only)": variance_um2,
                "illustrative normalized variance + floor": (
                    normalized_variance_example
                ),
                "model normalize_y": example["normalize_y"],
                "training rows": example["training_size"],
            })
            """,
            tags=["fold-local-scaling"],
        ),
        markdown(
            """
            Every fold fits the X scaler and y mean/standard deviation on its
            240 training simulations only. Physical variances must be divided
            by the *training-fold* y variance before becoming GP alpha values;
            otherwise units are inconsistent and the held-out target can leak
            into preprocessing.

            The GP's latent interval describes uncertainty about the smooth
            underlying response. B's total interval adds its learned shared
            nugget. C's retrospective oracle interval adds the held-out
            simulation's own target-summary variance. That oracle quantity
            would not be known for a truly unseen, not-yet-run simulation, so
            it is not a deployable future interval.

            ## 6. Width LOO results
            """
        ),
        code(
            """
            metrics = pd.read_csv(OUT / "all_model_metrics.csv")
            primary = metrics.loc[
                metrics["analysis_label"] == "full_population_loo"
            ]
            width_metrics = primary.loc[
                primary["target"] == "width",
                [
                    "method",
                    "mae_um",
                    "rmse_um",
                    "r2",
                    "nrmse",
                    "mean_nlpd",
                    "latent_95_coverage",
                    "observation_95_coverage",
                    "optimizer_warning_folds",
                    "any_bound_hit_folds",
                ],
            ]
            display(width_metrics)
            """,
            tags=["width-results"],
        ),
        markdown(
            """
            Width methods are compared first on held-out point error, then on
            predictive density, calibration, optimization stability, and cost.
            R² is contextual evidence only and does not determine the choice.

            ## 7. Length LOO results
            """
        ),
        code(
            """
            length_metrics = primary.loc[
                primary["target"] == "length",
                width_metrics.columns,
            ]
            display(length_metrics)
            """,
            tags=["length-results"],
        ),
        markdown(
            """
            Length uses the identical folds, scalers, kernel bounds, and
            optimizer policy. Differences from width therefore concern the
            response surface and observation treatment, not a changed model
            family.

            ## 8. Depth LOO results
            """
        ),
        code(
            """
            depth_metrics = primary.loc[
                primary["target"] == "depth",
                width_metrics.columns,
            ]
            display(depth_metrics)
            """,
            tags=["depth-results"],
        ),
        markdown(
            """
            Penetration depth is evaluated independently. A treatment need not
            win all three responses, and small numerical differences are not
            called superior without paired uncertainty evidence.

            ## 9. Learned nugget and heteroskedastic alpha
            """
        ),
        code(
            """
            nugget = pd.read_csv(OUT / "learned_nugget_summary.csv")
            alpha = pd.read_csv(OUT / "heteroskedastic_alpha_summary.csv")
            display(nugget)
            display(alpha.loc[alpha["subset"] == "all"])
            """,
            tags=["nugget-alpha"],
        ),
        markdown(
            """
            The learned nugget is reported in normalized variance, normalized
            standard deviation, micrometres, and as a fraction of each fold's
            training-target standard deviation. Bound hits reveal when the
            optimum is weakly identified. Observation-specific alpha summaries
            retain the actual between-simulation distribution rather than
            collapsing it to one shared value.

            ## 10. Paired comparisons
            """
        ),
        code(
            """
            paired = pd.read_csv(OUT / "paired_bootstrap_summary.csv")
            display(
                paired[
                    [
                        "target",
                        "method_a",
                        "method_b",
                        "method_b_improved_count",
                        "method_b_worsened_count",
                        "tied_count",
                        "observed_mae_difference_b_minus_a_um",
                        "mae_difference_ci95_low_um",
                        "mae_difference_ci95_high_um",
                        "observed_rmse_difference_b_minus_a_um",
                        "rmse_difference_ci95_low_um",
                        "rmse_difference_ci95_high_um",
                    ]
                ]
            )
            """,
            tags=["paired-bootstrap"],
        ),
        markdown(
            """
            Every comparison is paired on the same held-out simulations.
            Negative B−A differences favor the second method. Ten thousand
            paired bootstrap resamples quantify uncertainty in MAE and RMSE
            differences. Intervals containing zero do not support a robust
            superiority claim.

            ## 11. Preferred treatment by response
            """
        ),
        code(
            """
            preferences = pd.read_csv(
                OUT / "preferred_method_selection.csv"
            )
            display(preferences)
            """,
            tags=["method-selection"],
        ),
        markdown(
            """
            Selection is response-specific. Held-out point prediction has
            priority; NLPD and calibration, optimizer stability,
            interpretability, and runtime provide secondary evidence. The
            `selection_strength` field distinguishes robust paired evidence
            from a merely numerical preference.

            ## 12. Stable-window sensitivity
            """
        ),
        code(
            """
            stable = pd.read_csv(OUT / "stable_subset_sensitivity.csv")
            display(
                stable[
                    [
                        "target",
                        "preferred_method",
                        "analysis_label",
                        "n_predictions",
                        "mae_um",
                        "rmse_um",
                        "mean_nlpd",
                        "unstable_windows_materially_affect_conclusion",
                    ]
                ]
            )
            """,
            tags=["stable-sensitivity"],
        ),
        markdown(
            """
            The 11 flagged simulations remain in the primary 241-row analysis.
            The sensitivity study separately compares the full result, the 230
            stable held-outs from that full LOO run, and a new 230-simulation
            stable-only LOO refit. A flag denotes temporal target-window
            instability, not automatic invalidity.

            ## 13. Concise model-ready table
            """
        ),
        code(
            """
            model_ready = pd.read_csv(
                OUT / "phase2_model_ready_summary.csv"
            )
            display(model_ready.head())
            print("shape:", model_ready.shape)
            """,
            tags=["model-ready"],
        ),
        markdown(
            """
            This 12-column table is the compact inspection view: simulation ID,
            four inputs, three selected targets, three bootstrap uncertainty
            standard deviations, and the Phase 1 instability flag. The
            original 199-column Phase 1 audit ledger remains unchanged.

            ## 14. Focused diagnostics
            """
        ),
        code(
            """
            for filename in [
                "point_metric_comparison.png",
                "nlpd_and_coverage_comparison.png",
                "learned_nugget_distributions.png",
                "observation_specific_uncertainty_distributions.png",
                "target_uncertainty_vs_unstable_flag.png",
                "stable_subset_sensitivity.png",
            ]:
                print(filename)
                display(Image(filename=str(OUT / filename)))
            """,
            tags=["figures"],
        ),
        markdown(
            """
            Separate focused figures cover point error, predictive density and
            calibration, learned nugget behavior, observation-specific
            uncertainty, the Phase 1 flag, and stable-only refitting. Additional
            target-specific observed/predicted, residual, interval, and paired
            difference figures are saved in the output directory.

            ## 15. Automated validation
            """
        ),
        code(
            """
            validation = pd.read_csv(OUT / "validation_results.csv")
            display(validation)
            non_notebook = validation.loc[
                validation["validation_check"]
                != "notebook has zero error outputs"
            ]
            assert non_notebook["status"].eq("PASS").all()
            print(
                "recorded validation:",
                validation["status"].value_counts().to_dict(),
            )
            """,
            tags=["validation"],
        ),
        markdown(
            """
            The validator independently recomputes fold-local scalers, metrics,
            NLPD, interval ordering, paired alignment, Phase 1 hashes, and both
            worktree protections. During the first notebook execution its own
            cleanliness check is necessarily pending; validation is refreshed
            after the executed notebook is saved.

            ## 16. Conclusion and boundary

            The accepted treatment for each target is a predictive modelling
            choice under a fixed Matérn 3/2 family. It does not establish
            causality, feature importance, simulator stochasticity, or a
            deployable oracle interval. Later feature-effect analysis may use
            the validated response-specific preferences; active learning and
            level-set estimation remain unstarted.
            """,
            tags=["conclusions"],
        ),
    ]

    notebook = nbf.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3"},
        },
    )
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, NOTEBOOK_PATH)


if __name__ == "__main__":
    build_notebook()
    print(NOTEBOOK_PATH)
