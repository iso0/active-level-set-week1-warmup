"""Build and execute the Week 6 Phase 4 explanatory notebook."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf
import pandas as pd
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week6_04_new_outputs_feature_effects"
NOTEBOOK = (
    ROOT / "notebooks" / "week_06" / "06_phase4_new_outputs_feature_effects.ipynb"
)


def code(source: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(source=source)


def markdown(source: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(source=source)


def main() -> None:
    sensitivity = pd.read_csv(
        OUTPUT / "phase4_target_definition_sensitivity.csv"
    ).set_index("response")
    decisions = pd.read_csv(OUTPUT / "phase4_selected_model_decisions.csv").set_index(
        "response"
    )
    correlations = pd.read_csv(OUTPUT / "phase4_spearman_correlations.csv")
    ridge = pd.read_csv(OUTPUT / "phase4_standardized_ridge_coefficients.csv")
    normalized = pd.read_csv(
        OUTPUT / "phase4_normalized_diagnostic_correlations.csv"
    )

    def rho(response: str, feature: str) -> float:
        return float(
            correlations[
                correlations["response"].eq(response)
                & correlations["feature"].eq(feature)
            ]["spearman_rho"].iloc[0]
        )

    def beta(response: str, feature: str) -> float:
        return float(
            ridge[
                ridge["response"].eq(response)
                & ridge["feature"].eq(feature)
            ]["standardized_coefficient"].iloc[0]
        )

    cells: list[nbf.NotebookNode] = [
        markdown(
            """# Week 6 Phase 4 — new outputs and focused physical associations

This notebook closes Ioan's remaining Week 6 requests without reopening the completed width, length, or penetration-depth model searches.

```text
Phase 4
├── A. Provenance and monitor audit
├── B. New target extraction
│   ├── Kinetic energy
│   └── Total vertical height
├── C. New GP regression models
├── D. Physical input–output relationships
├── E. Beam-normalized penetration diagnostics
└── F. Final conclusions and remaining caveats
```

Scope boundaries: no normalized first-Conduction analysis, no dataset update check, no ARD, no classifier, no active learning, and no causal inference."""
        ),
        markdown(
            """## A. Provenance and monitor audit

**Kinetic energy** is energy associated with particle motion. Here the monitor is best supported as an *instantaneous aggregate* over melt-phase particles. “Instantaneous” means the state can rise or fall at the next solver row; a *cumulative* quantity would accumulate and should not fall.

The exact solver reduction formula is not stored locally, so Ioan still needs to confirm the particle-mass weighting. That residual caveat is not hidden."""
        ),
        code(
            """from pathlib import Path
import json
import pandas as pd
from IPython.display import Image, display

ROOT = Path.cwd().resolve()
OUT = ROOT / "outputs" / "week6_04_new_outputs_feature_effects"
assert ROOT.name == "thesis-week6-melt-pool-audit"

config = json.loads((OUT / "phase4_configuration.json").read_text(encoding="utf-8"))
preflight = json.loads((OUT / "phase4_preflight_snapshot.json").read_text(encoding="utf-8"))
audit_ke = pd.read_csv(OUT / "kinetic_energy_monitor_audit.csv")
audit_height = pd.read_csv(OUT / "total_height_monitor_audit.csv")

display(pd.DataFrame({
    "item": ["branch", "HEAD", "dataset revision", "Phase 1 ledger SHA-256", "kinetic file", "kinetic meaning"],
    "value": [
        config["branch"],
        config["starting_head"],
        config["dataset"]["pinned_revision"],
        config["dataset"]["phase1_ledger_sha256"],
        config["kinetic_energy_monitor"]["file_name"],
        config["kinetic_energy_monitor"]["semantic_classification"],
    ],
}))
display(audit_ke[["simulation_id", "rows_align", "invalid_row_count", "strict_negative_step_count", "minimum_J", "maximum_J"]].describe(include="all"))
display(Image(filename=str(OUT / "figures" / "02_kinetic_energy_semantic_audit.png"), width=950))"""
        ),
        markdown(
            """The audit uses the exact pinned file, row alignment, SI-unit metadata, local aggregate-monitor documentation, and all 241 time-series traces. The target windows are fully covered in all simulations: 240 files fully align, while pinned `sim_00052` is source-short but remains target-complete. `sim_00034` contains 236 recorded `NaN` rows; one T0-endpoint `NaN` is excluded and 2,233 valid T0 rows remain. The valid traces contain many decreases, which rejects a cumulative interpretation.

What this means: a late-active median is scientifically coherent. What it cannot prove: the exact solver-side mass weighting. This is a new Phase 4 audit; the coordinate and sentinel rules are reused from Phase 1."""
        ),
        code(
            """display(audit_height[[
    "simulation_id", "formula", "T0_observation_count",
    "T0_reproduction_absolute_error_m", "penetration_depth_not_substituted"
]].head())
display(Image(filename=str(OUT / "figures" / "01_phase4_analysis_tree.png"), width=950))
display(Image(filename=str(OUT / "figures" / "04_example_height_beside_depth.png"), width=950))"""
        ),
        markdown(
            """**Penetration depth** is `max(0, −z_min)`: below-surface reach. **Total vertical height** is `z_max − z_min`: the full top-to-bottom extent. For example, `z_max=20 µm` and `z_min=−50 µm` gives depth `50 µm` but total height `70 µm`.

The total-height T0 values reproduce the validated Phase 1 `delta_z` medians. This confirms identity and implementation, but neither response alone establishes a melt regime."""
        ),
        markdown(
            """## B. New target extraction

The **T0 window** is the final 20% of eligible melt-present observations before the laser reaches 90% of the positive-X domain. If 100 rows are eligible, T0 uses the final 20 and takes their median.

The **adaptive active interior** is the Phase 3.5 simulation-specific interior interval. It is used once as a sensitivity comparison, not as a second target search."""
        ),
        code(
            """targets = pd.read_csv(OUT / "phase4_simulation_level_targets.csv")
sensitivity = pd.read_csv(OUT / "phase4_target_definition_sensitivity.csv")
representatives = pd.read_csv(OUT / "representative_simulation_selection.csv")

display(targets[[
    "simulation_id", "P", "VX", "LS", "ST",
    "T0_melt_pool_kinetic_energy_nJ", "adaptive_melt_pool_kinetic_energy_nJ",
    "T0_total_vertical_height_um", "adaptive_total_vertical_height_um"
]].head())
display(sensitivity)
display(representatives)
for figure_id, name in [
    (3, "example_kinetic_energy_time_series"),
    (5, "new_target_distributions"),
    (6, "primary_vs_adaptive_targets"),
    (7, "representative_kinetic_energy_examples"),
    (8, "representative_total_height_examples"),
]:
    display(Image(filename=str(OUT / "figures" / f"{figure_id:02d}_{name}.png"), width=950))"""
        ),
        markdown(
            f"""Both new primary targets are available for all 241 simulations. The primary/adaptive correlations are {sensitivity.loc['kinetic_energy', 'primary_vs_alternative_spearman']:.3f} for kinetic energy and {sensitivity.loc['total_height', 'primary_vs_alternative_spearman']:.3f} for total height.

The three examples per response are selected reproducibly: closest to the median, largest response, and largest primary/adaptive disagreement after excluding duplicates. They illustrate behaviour; all scientific summaries use the full population."""
        ),
        markdown(
            """## C. Compact new-response modelling

**Leave-one-out (LOO) prediction** holds out one entire simulation, trains on the other 240, and predicts the held-out response. **Fold-local scaling** means the feature and response scalers are fitted only on those 240 training simulations.

Ridge is linear regression with **regularization**, a penalty that shrinks unstable coefficients. Polynomial Ridge adds degree-2 squares and pairwise interactions. The inner 5-fold CV chooses the regularization strength without seeing the outer held-out target.

A GP supplies a predictive mean and **predictive uncertainty**. The learned WhiteKernel **nugget** is effective unresolved model–data discrepancy; it is not identified as simulator noise. The no-nugget sensitivity keeps only fixed numerical jitter."""
        ),
        code(
            """model_metrics = pd.read_csv(OUT / "phase4_model_metrics.csv")
comparisons = pd.read_csv(OUT / "phase4_paired_bootstrap_comparisons.csv")
decisions = pd.read_csv(OUT / "phase4_selected_model_decisions.csv")

display(model_metrics[[
    "response", "model", "mae", "rmse", "r2", "nrmse",
    "mean_nlpd", "total_or_evaluation_95pct_coverage",
    "warning_folds", "failed_folds", "bound_hit_folds",
    "median_learned_nugget_std"
]])
display(decisions)
display(comparisons[comparisons["metric"].eq("RMSE")])
for figure_id, name in [
    (9, "kinetic_energy_model_comparison"),
    (10, "total_height_model_comparison"),
    (11, "kinetic_energy_observed_vs_loo"),
    (12, "total_height_observed_vs_loo"),
    (13, "loo_residual_distributions"),
    (14, "predictive_interval_diagnostics"),
]:
    display(Image(filename=str(OUT / "figures" / f"{figure_id:02d}_{name}.png"), width=950))"""
        ),
        markdown(
            f"""Kinetic energy selects `{decisions.loc['kinetic_energy', 'selected_point_model']}` for point prediction and `{decisions.loc['kinetic_energy', 'selected_uncertainty_model']}` for uncertainty. Total height selects `{decisions.loc['total_height', 'selected_point_model']}` and `{decisions.loc['total_height', 'selected_uncertainty_model']}` respectively.

A paired bootstrap resamples simulation identities together. Its **confidence interval** quantifies uncertainty in the paired MAE/RMSE difference. The GP improvements over the selected simple point models are statistically detectable, but smaller than the predeclared practical thresholds ({decisions.loc['kinetic_energy', 'practical_rmse_difference_threshold']:.4g} nJ and {decisions.loc['total_height', 'practical_rmse_difference_threshold']:.4g} µm), defined as the larger of 1% of target range and 2% of target IQR. This is why parsimony wins for point prediction while the learned-nugget GP remains the uncertainty model.

A kernel changes only when both errors improve robustly without calibration or optimizer deterioration. These results apply to the two new targets only."""
        ),
        markdown(
            """## D. Physical input–output relationships

**Spearman correlation** measures monotone rank association; +1 means identical ranking, −1 the reverse. A **standardized coefficient** reports the Ridge association after both input and output use standard-deviation units, conditional on the other inputs.

A **controlled-effect curve** varies one input while holding the other three at declared references. An **interaction** means the fitted association of one input changes with another. Curves and P×VX/P×LS surfaces are masked in sparse regions.

**Association versus causation:** these simulation-design patterns say “associated with” or “the fitted model predicts conditional on references.” They do not prove a physical mechanism."""
        ),
        code(
            """corr = pd.read_csv(OUT / "phase4_spearman_correlations.csv")
corr_ci = pd.read_csv(OUT / "phase4_spearman_bootstrap_intervals.csv")
ridge = pd.read_csv(OUT / "phase4_standardized_ridge_coefficients.csv")
support = pd.read_csv(OUT / "phase4_observed_support_summary.csv")

display(corr.merge(corr_ci, on=["response", "feature"]))
display(ridge)
display(support[[
    "response", "plot_type", "varying_features", "profile",
    "supported_fraction", "model_configuration", "training_sample_size"
]])
for figure_id, name in [
    (15, "spearman_input_output_overview"),
    (16, "standardized_ridge_coefficients"),
    (17, "width_vs_ls_controlled_curve"),
    (18, "kinetic_energy_vs_ls_power_profiles"),
    (19, "depth_P_VX_surface"),
    (20, "total_height_P_VX_surface"),
]:
    display(Image(filename=str(OUT / "figures" / f"{figure_id:02d}_{name}.png"), width=950))"""
        ),
        markdown(
            f"""Supervisor-focused readings:

- Width–LS: raw ρ={rho('width', 'LS'):.3f}; conditional standardized β={beta('width', 'LS'):.3f}.
- Kinetic-energy–LS: raw ρ={rho('kinetic_energy', 'LS'):.3f}; conditional β={beta('kinetic_energy', 'LS'):.3f}.
- Depth: ρ(P)={rho('depth', 'P'):.3f}, ρ(VX)={rho('depth', 'VX'):.3f}; conditional β(P)={beta('depth', 'P'):.3f}, β(VX)={beta('depth', 'VX'):.3f}.
- Total height: ρ(P)={rho('total_height', 'P'):.3f}, ρ(VX)={rho('total_height', 'VX'):.3f}; conditional β(P)={beta('total_height', 'P'):.3f}, β(VX)={beta('total_height', 'VX'):.3f}.

ST is reported in the same tables rather than interpreted selectively. Width reuses the Phase 3 Matérn 3/2 uncertainty GP; depth reuses it on the exact stable 230 population. These full-data fits support interpretation, not new model selection."""
        ),
        markdown(
            """## E. Beam-normalized penetration diagnostics

**Beam-normalized penetration** divides depth by laser spot radius. Example: `50 µm / 50 µm = 1`, dimensionless. Absolute depth answers “how far below the surface?”; depth/LS answers “how large relative to the beam?”; depth/width answers “how deep and narrow?”

**Mathematical coupling through a denominator:** because LS appears in D/LS, LS can correlate negatively with D/LS partly by arithmetic even if absolute depth is unchanged. LS must therefore be interpreted primarily against absolute depth."""
        ),
        code(
            """beam = pd.read_csv(OUT / "phase4_beam_normalized_penetration.csv")
beam_corr = pd.read_csv(OUT / "phase4_normalized_diagnostic_correlations.csv")
unstable = pd.read_csv(OUT / "phase4_normalized_diagnostic_unstable_sensitivity.csv")

display(beam[[
    "simulation_id", "LS", "T0_penetration_depth_um", "T0_depth_over_LS",
    "G3", "G3_over_LS", "R0", "R3",
    "G3_over_LS_vs_R3_percentile_disagreement"
]].head())
display(beam_corr)
display(unstable)
for figure_id, name in [
    (21, "t0_depth_vs_depth_over_ls"),
    (22, "g3_vs_g3_over_ls"),
    (23, "r3_vs_g3_over_ls"),
]:
    display(Image(filename=str(OUT / "figures" / f"{figure_id:02d}_{name}.png"), width=950))"""
        ),
        markdown(
            """`G3_over_LS` exactly equals persistent depth divided by LS because LS is constant within each simulation; no redundant time-series calculation is needed. Persistent G3/R3 quantities are available for 240 simulations; `sim_00101` lacks the Phase 3.5 adaptive interior. G3/LS and R3 can rank simulations differently because their denominators are beam radius and melt-pool width.

The unstable-11 table reports whether those simulations change distributions. High D/LS or R3 does not establish Keyhole. G3/LS is retained only for future analysis with more independent labels."""
        ),
        markdown("## F. Final conclusions and remaining caveats"),
        code(
            """checklist = pd.read_csv(OUT / "phase4_requirement_checklist.csv")
manifest = pd.read_csv(OUT / "figure_manifest.csv")
display(Image(filename=str(OUT / "figures" / "24_final_physical_response_summary.png"), width=950))
display(Image(filename=str(OUT / "figures" / "25_phase4_final_decision_tree.png"), width=950))
display(manifest[["figure_id", "title", "presentation_ready", "file"]])
display(checklist.groupby(["category", "status"]).size().rename("count").reset_index())"""
        ),
        markdown(
            """Phase 4 closes the new-response and focused-association questions while keeping the evidence boundaries explicit.

What remains uncertain: Ioan should confirm the kinetic reduction formula; controlled effects remain associations within observed support; R3 and G3/LS remain provisional regime descriptors. Active learning, classification, acquisition design, and level-set estimation are deferred until explicit review.

The figure manifest marks exactly ten presentation-ready figures. The full checklist maps every requirement to this notebook and its source output."""
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
            "phase": "Week 6 Phase 4",
            "builder": "scripts/build_week6_06_notebook.py",
        },
    )
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    client = NotebookClient(
        notebook,
        timeout=900,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
        allow_errors=False,
    )
    executed = client.execute()
    nbf.write(executed, NOTEBOOK)
    print(f"wrote and executed {NOTEBOOK}")


if __name__ == "__main__":
    main()
