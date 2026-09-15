"""Build the focused Week 6 Phase 2.5 depth-closure notebook."""

from __future__ import annotations

import textwrap
from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = (
    ROOT
    / "notebooks"
    / "week_06"
    / "03_phase2_5_depth_model_closure.ipynb"
)


def clean(text: str) -> str:
    return textwrap.dedent(text).strip()


def main() -> None:
    nb = nbf.v4.new_notebook()
    nb.metadata.kernelspec = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    nb.metadata.language_info = {"name": "python", "version": "3"}
    cells: list[nbf.NotebookNode] = []

    cells.append(
        nbf.v4.new_markdown_cell(
            clean(
                """
                # Week 6 Phase 2.5 — stable-depth model closure

                This notebook closes one specific gap from Phase 2: Method B
                (learned common effective nugget) and Method C
                (observation-specific heteroskedastic alpha) are compared on
                exactly the same 230 stable-window penetration-depth
                simulations. Width, length, Method A, new kernels, Phase 3,
                feature effects, active learning, and level-set estimation are
                outside this notebook.
                """
            )
        )
    )

    def add_section(
        number: int,
        title: str,
        purpose: str,
        code: str,
        explanation: str,
    ) -> None:
        cells.append(
            nbf.v4.new_markdown_cell(
                f"## {number}. {title}\n\n{clean(purpose)}"
            )
        )
        code_cell = nbf.v4.new_code_cell(clean(code))
        code_cell.metadata["tags"] = ["major", f"section-{number}"]
        cells.append(code_cell)
        cells.append(
            nbf.v4.new_markdown_cell(
                "**For Burak.** " + clean(explanation)
            )
        )

    add_section(
        1,
        "Why Phase 2.5 is needed",
        """
        Phase 2 found a depth trade-off, but only C received a stable-only
        refit. We first locate the repository and load the closure summary so
        the exact unresolved question is explicit.
        """,
        """
        from pathlib import Path
        import json
        import numpy as np
        import pandas as pd
        from IPython.display import Image, Markdown, display

        START = Path.cwd().resolve()
        ROOT = next(
            (
                candidate
                for candidate in (START, *START.parents)
                if (
                    candidate
                    / "outputs"
                    / "week6_02_5_depth_model_closure"
                ).is_dir()
            ),
            None,
        )
        if ROOT is None:
            raise FileNotFoundError("Could not locate the repository root.")

        OUT = ROOT / "outputs" / "week6_02_5_depth_model_closure"
        P2 = ROOT / "outputs" / "week6_02_gp_response_noise_comparison"
        summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
        pd.Series(
            {
                "phase": summary["phase"],
                "stable simulations": summary["stable_subset_size"],
                "new predictions": summary["new_prediction_count"],
                "methods": summary["methods"],
                "decision": summary["decision"]["headline"],
            }
        )
        """,
        """
        Phase 2.5 is not a new model search. It supplies the missing matched
        B-versus-C experiment. Nothing here can tell us which input causes
        penetration depth or whether another kernel family would be better.
        """,
    )

    add_section(
        2,
        "Load and validate Phase 2 artifacts",
        """
        The immutable Phase 1 revision, ledger hash, Phase 2 configuration,
        uncertainty artifact, and historical prediction hashes must match
        before any Phase 2.5 result is interpreted.
        """,
        """
        config = json.loads(
            (OUT / "phase2_5_configuration.json").read_text(encoding="utf-8")
        )
        stable_input = pd.read_csv(OUT / "stable_depth_input_table.csv")
        source_rows = pd.DataFrame(
            [
                ("Phase 1 revision", config["phase1_revision"]),
                ("Phase 1 ledger SHA-256", config["phase1_ledger_sha256"]),
                (
                    "Phase 2 configuration SHA-256",
                    config["phase2_configuration_sha256"],
                ),
                (
                    "Phase 2 uncertainty SHA-256",
                    config["phase2_uncertainty_sha256"],
                ),
                ("Protocol fingerprint", config["protocol_fingerprint"]),
            ],
            columns=["source", "recorded value"],
        )
        source_rows
        """,
        """
        A fingerprint is a file-content identifier. Matching fingerprints mean
        this closure used the same validated source artifacts; they do not by
        themselves prove that the scientific model is correct.
        """,
    )

    add_section(
        3,
        "Construct the exact 230-simulation stable subset",
        """
        The Phase 1 flag is checked against the expected 11 IDs. The remaining
        230 IDs are unique and ordered by numeric simulation ID.
        """,
        """
        expected_removed = config["stable_subset"]["removed_simulation_ids"]
        assert len(stable_input) == 230
        assert stable_input["simulation_id"].is_unique
        assert not stable_input["flag_primary_window_unstable"].astype(bool).any()
        assert stable_input["fold_index"].tolist() == list(range(230))
        pd.DataFrame(
            {
                "stable rows": [len(stable_input)],
                "removed rows": [len(expected_removed)],
                "first stable ID": [stable_input.iloc[0]["simulation_id"]],
                "last stable ID": [stable_input.iloc[-1]["simulation_id"]],
                "removed IDs": [", ".join(expected_removed)],
            }
        )
        """,
        """
        “Stable” means that Phase 1 did not raise its selected-window
        instability flag. It does not mean the simulation is perfect or that
        the removed simulations are invalid.
        """,
    )

    add_section(
        4,
        "Restate B and C mathematically and in plain language",
        """
        Both methods share the fixed isotropic Matérn 3/2 covariance. Only the
        observation treatment changes.
        """,
        """
        model_rows = []
        for method, settings in config["methods"].items():
            model_rows.append(
                {
                    "method": method,
                    "kernel": settings["kernel"],
                    "evaluation variance": settings["evaluation_variance"],
                    "interpretation": settings["interpretation"],
                }
            )
        pd.DataFrame(model_rows)
        """,
        """
        A nugget is a common residual variance learned by B. In scikit-learn it
        is represented by `WhiteKernel`; here it is effective model discrepancy,
        not random simulator noise. Heteroskedastic alpha means C gives
        different training variances to different simulations. For example,
        if a window variance is 0.04 µm² and the training-target standard
        deviation is 20 µm, its normalized contribution is
        0.04 / 20² = 0.0001 before the numerical floor.
        """,
    )

    add_section(
        5,
        "Verify the identical cross-validation protocol",
        """
        Leave-One-Out cross-validation (LOO) holds out one simulation, trains
        on the other 229, and repeats this for every stable simulation.
        """,
        """
        pred_b = pd.read_csv(OUT / "stable_depth_B_loo_predictions.csv")
        pred_c = pd.read_csv(OUT / "stable_depth_C_loo_predictions.csv")
        protocol_check = pd.Series(
            {
                "B rows": len(pred_b),
                "C rows": len(pred_c),
                "same simulation order": (
                    pred_b["simulation_id"].tolist()
                    == pred_c["simulation_id"].tolist()
                ),
                "same fold indices": (
                    pred_b["fold_index"].tolist()
                    == pred_c["fold_index"].tolist()
                ),
                "same fold seeds": (
                    pred_b["fold_random_seed"].tolist()
                    == pred_c["fold_random_seed"].tolist()
                ),
                "training rows per fold": pred_b["training_size"].unique().tolist(),
                "features": pred_b["feature_columns"].unique().tolist(),
            }
        )
        assert protocol_check["same simulation order"]
        assert protocol_check["same fold indices"]
        assert protocol_check["same fold seeds"]
        protocol_check
        """,
        """
        This alignment makes the comparison paired: B and C face exactly the
        same held-out cases. Fold-local scaling means the held-out target never
        influences scaling or hyperparameter optimization.
        """,
    )

    add_section(
        6,
        "Run or load the exact 230-fold results",
        """
        The reusable source performed 230 new B fits and 230 new C fits. This
        notebook loads those audited rows rather than hiding another expensive
        experiment inside one large cell.
        """,
        """
        required_prediction_columns = [
            "simulation_id",
            "observed_target_um",
            "predicted_mean_um",
            "latent_predictive_std_um",
            "evaluation_nlpd",
            "optimized_kernel",
            "runtime_seconds",
            "warnings",
            "any_hyperparameter_bound_hit",
        ]
        assert pred_b[required_prediction_columns].shape == (230, 9)
        assert pred_c[required_prediction_columns].shape == (230, 9)
        pd.concat(
            [
                pred_b[required_prediction_columns].head(2).assign(method="B"),
                pred_c[required_prediction_columns].head(2).assign(method="C"),
            ],
            ignore_index=True,
        )
        """,
        """
        Every row is one genuinely held-out stable simulation. The outputs
        retain predictions, uncertainty, optimized kernels, warnings, and bound
        hits so favorable aggregate metrics cannot conceal unstable fits.
        """,
    )

    add_section(
        7,
        "Compare point-prediction metrics",
        """
        MAE summarizes typical absolute error, RMSE penalizes large errors more,
        R² compares against a constant-mean predictor, and nRMSE scales RMSE by
        the observed depth range.
        """,
        """
        metrics = pd.read_csv(OUT / "stable_depth_model_metrics.csv")
        point_columns = [
            "method",
            "mae_um",
            "median_absolute_error_um",
            "rmse_um",
            "r2",
            "nrmse",
        ]
        metrics[point_columns].round(6)
        """,
        """
        Lower MAE/RMSE/nRMSE is better. R² is reported but is not the sole
        decision rule. A result on these 230 simulations does not guarantee the
        same ranking outside this design.
        """,
    )

    add_section(
        8,
        "Compare uncertainty metrics",
        """
        Calibration asks whether nominal intervals contain observations at
        approximately their stated frequency. NLPD (negative log predictive
        density) rewards accurate means and appropriately scaled uncertainty;
        lower is better.
        """,
        """
        uncertainty_columns = [
            "method",
            "mean_nlpd",
            "median_nlpd",
            "latent_95_coverage",
            "observation_95_coverage",
            "mean_latent_interval_width_um",
            "mean_observation_interval_width_um",
            "nlpd_variance_definition",
        ]
        display(metrics[uncertainty_columns].round(6))
        display(
            Image(
                filename=str(
                    OUT / "stable_depth_predictive_interval_calibration.png"
                )
            )
        )
        """,
        """
        Latent uncertainty concerns the smooth GP response before an observation
        term is added. B total uncertainty includes its learned nugget. C's
        oracle interval adds the held-out simulation's known-after-the-fact
        bootstrap variance; “oracle” means retrospective, so it is not
        deployable for a genuinely unseen simulation. Coverage should be close
        to 95%, not maximized.
        """,
    )

    add_section(
        9,
        "Perform the paired bootstrap comparison",
        """
        A paired bootstrap jointly resamples the same simulation IDs for both
        methods. A 95% confidence interval describes the resampling uncertainty
        of the observed method difference.
        """,
        """
        paired = pd.read_csv(OUT / "stable_depth_paired_comparison.csv")
        paired_summary = pd.read_csv(
            OUT / "stable_depth_paired_bootstrap_summary.csv"
        )
        display(paired_summary.T)
        display(
            Image(
                filename=str(
                    OUT / "stable_depth_paired_bootstrap_intervals.png"
                )
            )
        )
        """,
        """
        Differences are C minus B: negative favors C and positive favors B. If
        an interval crosses zero, superiority is not robust. An interval that
        excludes zero supports a stable ranking for this matched dataset, not a
        universal theorem about all possible simulations.
        """,
    )

    add_section(
        10,
        "Compare stable refits with full-population-trained models",
        """
        The same 230 stable held-outs are evaluated twice: once using models
        trained with all other 240 simulations, and once using only the other
        229 stable simulations.
        """,
        """
        stable_vs_full = pd.read_csv(
            OUT / "stable_vs_full_population_comparison.csv"
        )
        display(
            stable_vs_full.loc[
                stable_vs_full["metric"].isin(
                    ["mae_um", "rmse_um", "r2", "mean_nlpd"]
                ),
                [
                    "method",
                    "metric",
                    "full_population_model_stable_heldouts",
                    "stable_only_refit",
                    "percent_change",
                    "rmse_change_is_material",
                ],
            ].round(6)
        )
        display(
            Image(
                filename=str(OUT / "stable_depth_stable_vs_full_training.png")
            )
        )
        """,
        """
        This isolates the influence of unstable simulations in the training set.
        The 5% RMSE threshold is only a descriptive materiality flag; it is not
        a hypothesis test and does not declare any simulation invalid.
        """,
    )

    add_section(
        11,
        "Inspect learned nugget and heteroskedastic alpha",
        """
        The two observation treatments have different scientific meanings and
        should not be compared as though they estimated the same quantity.
        """,
        """
        nugget = summary["method_summaries"]["learned_B_effective_nugget"]
        alpha = summary["method_summaries"]["C_target_summary_uncertainty"]
        pd.DataFrame(
            [
                {
                    "quantity": "B effective-nugget std (µm)",
                    "median": nugget["std_um_median"],
                    "q95": nugget["std_um_q95"],
                    "max": nugget["std_um_max"],
                },
                {
                    "quantity": "C target-summary std (µm)",
                    "median": alpha["std_um_median"],
                    "q95": alpha["std_um_q95"],
                    "max": alpha["std_um_max"],
                },
            ]
        ).round(6)
        """,
        """
        WhiteKernel does not directly measure target-definition error: B's
        nugget can also absorb omitted variables and fixed-kernel mismatch.
        C's alpha comes only from temporal stability of each selected-window
        median. Neither quantity is evidence of stochastic simulator noise.
        """,
    )

    add_section(
        12,
        "Inspect optimizer warnings and bound hits",
        """
        A bound hit means an optimized hyperparameter reached a configured
        search boundary, which can signal weak identification or inadequate
        bounds.
        """,
        """
        hyper = pd.read_csv(
            OUT / "stable_depth_hyperparameter_diagnostics.csv"
        )
        diagnostics = (
            hyper.groupby("method")
            .agg(
                folds=("fold_index", "size"),
                warning_folds=("warning_count", lambda s: (s > 0).sum()),
                failed_folds=("failed_fold", "sum"),
                constant_bound_hits=("constant_bound_hit", "sum"),
                lengthscale_bound_hits=("length_scale_bound_hit", "sum"),
                noise_bound_hits=("noise_bound_hit", "sum"),
                median_lengthscale=("optimized_length_scale", "median"),
                median_signal_variance=(
                    "optimized_signal_variance_normalized",
                    "median",
                ),
            )
            .reset_index()
        )
        diagnostics
        """,
        """
        Warnings and bound hits are diagnostics, not automatic invalidation.
        Completed folds remain usable, but a method with repeated warnings or
        boundary solutions deserves less trust.
        """,
    )

    add_section(
        13,
        "Resolve the depth model decision",
        """
        The decision follows the requested priority: paired point prediction,
        calibration/NLPD, stable-training robustness, optimizer stability,
        deployability/interpretation, then runtime.
        """,
        """
        decision = summary["decision"]
        display(Markdown(f"### {decision['headline']}"))
        pd.Series(
            {
                "paired superiority robust": decision[
                    "paired_superiority_is_robust"
                ],
                "B has lower mean NLPD": decision["B_mean_nlpd_is_lower"],
                "B coverage closer to 95%": decision[
                    "B_observation_coverage_is_closer_to_95_percent"
                ],
                "B total interval deployable": decision[
                    "B_observation_interval_is_deployable_for_new_inputs"
                ],
                "C oracle interval deployable": decision[
                    "C_oracle_interval_is_deployable_for_new_inputs"
                ],
            }
        )
        """,
        """
        This is a target-specific operational decision under one fixed kernel,
        not a universal GP winner. It does not authorize feature-effect claims
        or Phase 3 work.
        """,
    )

    add_section(
        14,
        "Explain the runtime metadata correction",
        """
        The old 11.2-second field was traced to determine exactly what its timer
        included and excluded.
        """,
        """
        runtime = json.loads(
            (OUT / "runtime_provenance.json").read_text(encoding="utf-8")
        )
        correction = runtime["phase2_runtime_metadata_correction"]
        pd.Series(
            {
                "historical field": correction["original_field_name"],
                "historical seconds": correction["original_value_seconds"],
                "corrected name": correction[
                    "corrected_authoritative_field_name"
                ],
                "classification": correction["classification"],
                "all checkpoints predated invocation": correction[
                    "cache_evidence"
                ]["all_checkpoints_predate_timed_invocation"],
                "guessed durations reported": not runtime[
                    "timing_principles"
                ]["no_inferred_duration_reported_as_measured"],
            }
        )
        """,
        """
        The 11.2 seconds measured a cached pre-report invocation—artifact
        loading/assembly, figures, and validation—not the original bootstrap
        and GP fits. The historical value is preserved but its broad name is
        deprecated. No file-timestamp estimate or summed parallel-fold time is
        presented as a measured end-to-end runtime.
        """,
    )

    add_section(
        15,
        "Validation checklist",
        """
        Thirty automated checks cover provenance, subset identity, fold
        alignment, scaling, leakage, variance mathematics, paired resampling,
        source preservation, notebook execution, git hygiene, and runtime
        provenance.
        """,
        """
        validation = pd.read_csv(OUT / "validation_results.csv")
        non_notebook = validation.loc[validation["validation_number"] != 28]
        assert non_notebook["status"].eq("PASS").all()
        validation[["validation_number", "validation_check", "status", "details"]]
        """,
        """
        Before the notebook exists, check 28 is expected to be pending while
        all other checks must pass. After execution and final validation, the
        artifact becomes 30/30 PASS. Validation reduces implementation risk but
        cannot prove the fixed scientific assumptions are true.
        """,
    )

    add_section(
        16,
        "Final scientific conclusion",
        """
        We finish with the exact supported conclusion and the limits that must
        carry into later work.
        """,
        """
        display(Markdown((OUT / "depth_model_decision.md").read_text(encoding="utf-8")))
        """,
        """
        Phase 2.5 resolves only the missing fair B-versus-C stable-depth
        comparison. Width/length decisions remain historical Phase 2 results.
        Phase 3 still has to be requested separately.
        """,
    )

    nb["cells"] = cells
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, NOTEBOOK_PATH)
    print(NOTEBOOK_PATH)


if __name__ == "__main__":
    main()
