"""Build and execute the Week 7 Phase 4 teaching notebook from saved artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import nbformat
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs" / "week7_04_new_data_feature_effects_depth_diagnostics"
NOTEBOOK_PATH = (
    ROOT / "notebooks" / "week_07" / "04_new_data_feature_effects_depth_diagnostics.ipynb"
)


def teaching_before(*, doing: str, why: str, question: str, suspicious: str) -> str:
    return f"""**What are we doing?** {doing}

**Why?** {why}

**What question does it answer?** {question}

**What would be suspicious?** {suspicious}
"""


def teaching_after(*, observed: str, meaning: str, reproduced: str, uncertain: str) -> str:
    return f"""**What did we observe?** {observed}

**What does it mean?** {meaning}

**Did Week 6 reproduce?** {reproduced}

**What remains uncertain?** {uncertain}
"""


def add_section(
    cells: list,
    *,
    number: int,
    title: str,
    before: str,
    code: str,
    after: str,
) -> None:
    cells.append(nbformat.v4.new_markdown_cell(f"## {number}. {title}\n\n{before}"))
    cells.append(nbformat.v4.new_code_cell(code.strip()))
    cells.append(nbformat.v4.new_markdown_cell(after))


def build_notebook() -> Path:
    summary = json.loads((OUTPUT_DIR / "summary.json").read_text(encoding="utf-8"))
    depth = summary["depth_error"]
    trends = summary["depth_trends"]
    cells: list = [
        nbformat.v4.new_markdown_cell(
            """# Week 7 Phase 4 — New-data feature effects and depth-error diagnosis

This teaching notebook replicates the Week 6 input-to-physical-response analysis on the corrected new-data population, then diagnoses the fixed Phase 3 leave-one-out (LOO) depth errors. Historical Week 6 values are comparators only. The primary analysis never pools old and new data, changes labels, or redefines T0.

The nonlinear GP fits in Sections 8–10 are full-new-data interpretability fits. They describe the fitted response surface inside observed support; they are not out-of-sample performance estimates and not causal physics.
"""
        )
    ]

    add_section(
        cells,
        number=1,
        title="Scope, parent commit, and dataset provenance",
        before=teaching_before(
            doing="We pin the repository parent, immutable dataset revision, and machine-derived Phase 2 eligibility counts.",
            why="A feature replication is only interpretable when its lineage and population are explicit.",
            question="Is this exactly the Phase 4 analysis requested from the committed Phase 3 state?",
            suspicious="A different parent SHA, a moving dataset revision, pooled partitions, or a hand-written exclusion count.",
        ),
        code="""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from IPython.display import Image, display
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

ROOT = Path.cwd()
OUT = ROOT / "outputs" / "week7_04_new_data_feature_effects_depth_diagnostics"
PHASE3 = ROOT / "outputs" / "week7_03_new_data_physical_model_stability"
summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
provenance = json.loads((OUT / "input_provenance.json").read_text(encoding="utf-8"))
scope_view = pd.DataFrame([
    {"field": "Phase 3 parent", "value": summary["phase3_parent_sha"]},
    {"field": "dataset", "value": summary["dataset_repo_id"]},
    {"field": "revision", "value": summary["dataset_revision"]},
    {"field": "audit population", "value": summary["audit_population_count"]},
    {"field": "eligible by target", "value": summary["eligible_counts"]},
    {"field": "primary population", "value": summary["scope"]["primary_population"]},
])
display(scope_view)
""",
        after=teaching_after(
            observed=f"The parent is `{summary['phase3_parent_sha']}`, the dataset is pinned to `{summary['dataset_revision']}`, and readiness yields 164 rows for every primary target while retaining all 165 experiments in the audit interface.",
            meaning="Population selection is inherited from corrected Phase 2 readiness fields, not an exclusion list.",
            reproduced="This section establishes lineage rather than testing a Week 6 physical statement.",
            uncertain="One new-data experiment remains target-ineligible because its required physical-output files are absent; it is still represented in the audit table.",
        ),
    )

    add_section(
        cells,
        number=2,
        title="Phase 3 recap and why depth requires diagnosis",
        before=teaching_before(
            doing="We read the saved Phase 3 relative-error and model-selection artifacts without refitting predictive models.",
            why="Phase 4 must diagnose the already-observed LOO problem rather than replacing it with in-sample residuals.",
            question="Which response became scientifically concerning under the new design?",
            suspicious="New predictions, hidden trimming, or a metric computed on fitted training values.",
        ),
        code="""
phase3_relative = pd.read_csv(PHASE3 / "relative_error_table.csv")
phase3_choices = pd.read_csv(PHASE3 / "model_selection_decisions.csv")
display(phase3_relative.query("target == 'depth'").reset_index(drop=True))
display(phase3_choices.query("target == 'depth'").reset_index(drop=True))
""",
        after=teaching_after(
            observed="Phase 3 showed that penetration-depth LOO error increased substantially on the new-data design, motivating a case-level diagnosis.",
            meaning="A large aggregate RMSE is a symptom; it does not by itself identify model-family failure.",
            reproduced="Phase 3 retained the Matérn 3/2 family used here; Phase 4 does not introduce a new kernel family.",
            uncertain="The error could reflect a heavy tail, regime mixture, target quality, design geometry, or several mechanisms together.",
        ),
    )

    add_section(
        cells,
        number=3,
        title="Week 6 feature-analysis traceability",
        before=teaching_before(
            doing="We map every replicated Week 6 analysis to its executable source, function, settings, and Phase 4 change.",
            why="Replication should follow the actual Week 6 implementation rather than memory.",
            question="Which definitions are identical and which changes are transparent additions?",
            suspicious="A silently changed standardization, GP support rule, or historical result recomputed on pooled data.",
        ),
        code="""
traceability = pd.read_csv(OUT / "week6_feature_analysis_traceability.csv")
display(traceability)
""",
        after=teaching_after(
            observed="Spearman, standardized Ridge, controlled curves, P–VX surfaces, and support masking are traced to Week 6 code and saved artifacts.",
            meaning="The primary changes are the new-data population and inexpensive 2,000-resample simulation bootstrap intervals.",
            reproduced="The exact Week 6 coefficient standardization, alpha selection, anchor logic, and support rules are reused.",
            uncertain="Historical associations remain observational summaries of their sampled design, not universal causal constants.",
        ),
    )

    add_section(
        cells,
        number=4,
        title="New-data input and target descriptive context",
        before=teaching_before(
            doing="We summarize physical input and target ranges separately for each target-ready new-data population.",
            why="Effect sizes and support masks must be interpreted against the actual sampled ranges.",
            question="What design and response scales underlie the replication?",
            suspicious="Different sample counts by unexplained filtering or values outside the pinned population.",
        ),
        code="""
context = pd.read_csv(OUT / "new_data_input_target_summary.csv")
display(context)
""",
        after=teaching_after(
            observed="Every primary target uses 164 target-ready new-data simulations with documented physical units and observed quantiles.",
            meaning="Later curves and surfaces are bounded by these ranges and masked when local support is poor.",
            reproduced="The input names remain P, VX, LS, and ST; ST is substrate temperature.",
            uncertain="Coverage density is nonuniform even inside marginal ranges, which is why multivariate support checks are still needed.",
        ),
    )

    add_section(
        cells,
        number=5,
        title="Spearman input-output associations",
        before=teaching_before(
            doing="We inspect marginal Spearman associations with simulation-level bootstrap confidence intervals.",
            why="This cheaply tests monotone input-response structure without assuming linearity.",
            question="Which new-data input-output associations are strongest, and are their signs stable?",
            suspicious="Causal wording, confidence intervals from non-independent frames, or old-data rows in the calculation.",
        ),
        code="""
population = pd.read_csv(OUT / "model_ready_population_reference.csv")
spearman = pd.read_csv(OUT / "new_data_spearman_input_output.csv")
feature_columns = {"P": "P_W", "VX": "VX_m_per_s", "LS": "LS_um", "ST": "ST_K"}
target_columns = {
    "width": "T0_width_um", "depth": "T0_depth_um",
    "total_height": "T0_total_height_um", "kinetic_energy": "T0_kinetic_energy_nJ",
}
recomputed_rho = []
for target, target_column in target_columns.items():
    eligible = population[population[f"{target}_model_eligible"].astype(bool)]
    for input_name, input_column in feature_columns.items():
        rho, p_value = spearmanr(eligible[input_column], eligible[target_column])
        recomputed_rho.append({"target": target, "input": input_name, "recomputed_rho": rho, "recomputed_p": p_value})
spearman_reconciliation = spearman.merge(pd.DataFrame(recomputed_rho), on=["target", "input"])
spearman_reconciliation["absolute_rho_difference"] = (
    spearman_reconciliation["spearman_rho"] - spearman_reconciliation["recomputed_rho"]
).abs()
display(spearman_reconciliation.assign(absolute_rho=spearman_reconciliation["spearman_rho"].abs()).sort_values("absolute_rho", ascending=False).reset_index(drop=True))
print("maximum raw-table rho reconciliation difference:", spearman_reconciliation["absolute_rho_difference"].max())
display(Image(filename=str(OUT / "figures" / "01_new_data_spearman_heatmap.png")))
""",
        after=teaching_after(
            observed="Power has the strongest positive marginal association with kinetic energy, depth, and total height; scan speed has the strongest negative width association.",
            meaning="These are marginal associations in the sampled new-data design, not causal effects.",
            reproduced=f"Depth retains P-positive (rho={trends['P']['new_spearman_rho']:.3f}) and VX-negative (rho={trends['VX']['new_spearman_rho']:.3f}) directions.",
            uncertain="Correlated design inputs can make a marginal association differ from the conditional Ridge or local GP view.",
        ),
    )

    add_section(
        cells,
        number=6,
        title="Standardized Ridge coefficients",
        before=teaching_before(
            doing="We inspect Week 6-style standardized multivariable Ridge coefficients and fixed-specification bootstrap intervals.",
            why="This gives a conditional linear association view after jointly accounting for P, VX, LS, and ST.",
            question="Do coefficient signs and relative magnitudes agree with the marginal pattern?",
            suspicious="Unstandardized inputs, a different alpha protocol, or causal-constant interpretation.",
        ),
        code="""
ridge = pd.read_csv(OUT / "new_data_standardized_ridge_coefficients.csv")
ridge_recomputed = []
for target, target_column in target_columns.items():
    eligible = population[population[f"{target}_model_eligible"].astype(bool)]
    x = StandardScaler().fit_transform(eligible[list(feature_columns.values())])
    y = StandardScaler().fit_transform(eligible[[target_column]]).ravel()
    alpha = float(ridge.loc[ridge["target"].eq(target), "selected_alpha"].iloc[0])
    coefficients = Ridge(alpha=alpha).fit(x, y).coef_
    ridge_recomputed.extend(
        {"target": target, "input": input_name, "recomputed_coefficient": coefficient}
        for input_name, coefficient in zip(feature_columns, coefficients)
    )
ridge_reconciliation = ridge.merge(pd.DataFrame(ridge_recomputed), on=["target", "input"])
ridge_reconciliation["absolute_coefficient_difference"] = (
    ridge_reconciliation["standardized_coefficient"] - ridge_reconciliation["recomputed_coefficient"]
).abs()
display(ridge_reconciliation.sort_values(["target", "absolute_magnitude"], ascending=[True, False]))
print("maximum fixed-specification coefficient reconciliation difference:", ridge_reconciliation["absolute_coefficient_difference"].max())
display(Image(filename=str(OUT / "figures" / "02_new_data_ridge_coefficients.png")))
""",
        after=teaching_after(
            observed="Depth has positive P and negative VX/LS standardized coefficients, while the ST coefficient is close to zero in this sampled design.",
            meaning="The joint linear view agrees with the main depth direction while separating it from marginal input correlations.",
            reproduced="The exact Week 6 scaling and Ridge alpha-selection workflow is retained.",
            uncertain="A global linear coefficient cannot describe interactions or locally changing nonlinear response.",
        ),
    )

    add_section(
        cells,
        number=7,
        title="Week 6 versus new-data coefficient and correlation stability",
        before=teaching_before(
            doing="We compare saved Week 6 Spearman and Ridge results with their new-data replications, then inspect three-view depth consensus.",
            why="Agreement across historical and new designs is stronger evidence than a single new statistic.",
            question="Which relationships preserve sign and which weaken, reverse, or remain unresolved?",
            suspicious="Treating every numerical change as a scientific reversal or ignoring intervals that include zero.",
        ),
        code="""
spearman_compare = pd.read_csv(OUT / "week6_vs_new_data_spearman.csv")
ridge_compare = pd.read_csv(OUT / "week6_vs_new_data_standardized_coefficients.csv")
depth_consensus = pd.read_csv(OUT / "depth_feature_trend_consensus.csv")
display(spearman_compare)
display(ridge_compare)
display(depth_consensus)
""",
        after=teaching_after(
            observed="The P-positive and VX-negative depth relationships agree across Spearman, Ridge, and supported GP sensitivities; LS weakens and ST is unresolved for depth.",
            meaning="The large depth RMSE coexists with a stable broad response direction.",
            reproduced="P and VX are classified REPRODUCED under the predeclared three-view consensus logic.",
            uncertain="Agreement in sign does not imply uniform local magnitude or causal identification.",
        ),
    )

    add_section(
        cells,
        number=8,
        title="GP controlled response curves",
        before=teaching_before(
            doing="We vary one input while holding others at medians, including multiple P profiles for the KE–LS curve.",
            why="A nonlinear GP has no single global coefficient, so controlled curves reveal supported response shape.",
            question="Do Week 6-style width–LS and KE–LS patterns persist on new data?",
            suspicious="Far-range extrapolation, unsupported points presented as evidence, or performance claims from full-data fits.",
        ),
        code="""
curves = pd.read_csv(OUT / "gp_controlled_curve_data.csv")
display(curves.groupby(["target", "varying_input", "profile"], dropna=False).agg(
    grid_points=("input_value", "size"), supported_points=("within_observed_support", "sum")
).reset_index())
display(Image(filename=str(OUT / "figures" / "03_width_vs_ls_controlled_curve.png")))
display(Image(filename=str(OUT / "figures" / "04_kinetic_energy_ls_power_profiles.png")))
""",
        after=teaching_after(
            observed="Width rises with LS over supported portions of the median-anchored curve; KE–LS shape remains dependent on the power profile rather than uniformly decreasing.",
            meaning="Interaction-aware curves prevent a misleading single global KE–LS claim.",
            reproduced="The width–LS relationship reproduces; the qualified Week 6 KE–LS statement remains mixed but not reversed into a universal rule.",
            uncertain="These are fitted-surface summaries conditional on chosen anchors and observed support.",
        ),
    )

    add_section(
        cells,
        number=9,
        title="GP standardized local sensitivities",
        before=teaching_before(
            doing="We summarize guarded central finite differences of the full-data GP mean in standardized units.",
            why="This is a local nonlinear analogue of a standardized coefficient.",
            question="Are depth sensitivities consistently P-positive and VX-negative at observed points?",
            suspicious="One-sided out-of-range derivatives, unsupported finite differences, or calling model-surface derivatives true causal physics.",
        ),
        code="""
sensitivity = pd.read_csv(OUT / "gp_local_sensitivity_summary.csv")
sensitivity_values = pd.read_csv(OUT / "gp_local_sensitivity_values.csv")
valid_sensitivity = sensitivity_values[sensitivity_values["valid_supported_evaluation"].astype(bool)]
recomputed_sensitivity = valid_sensitivity.groupby(["target", "input"])["standardized_local_sensitivity"].agg(
    recomputed_median="median", recomputed_q25=lambda values: values.quantile(0.25),
    recomputed_q75=lambda values: values.quantile(0.75), recomputed_n="size",
).reset_index()
sensitivity_reconciliation = sensitivity.merge(recomputed_sensitivity, on=["target", "input"])
display(sensitivity_reconciliation)
display(Image(filename=str(OUT / "figures" / "05_gp_local_sensitivity_summary.png")))
""",
        after=teaching_after(
            observed=f"Median standardized depth sensitivities are P={trends['P']['new_gp_median_standardized_local_sensitivity']:.3f} and VX={trends['VX']['new_gp_median_standardized_local_sensitivity']:.3f}, with guarded evaluation counts reported.",
            meaning="The fitted nonlinear surface supports the same broad depth directions as Spearman and Ridge.",
            reproduced="P-positive and VX-negative depth effects reproduce across the third independent view.",
            uncertain="Local sensitivity distributions can still contain heterogeneity and are conditional on this fitted GP surface.",
        ),
    )

    add_section(
        cells,
        number=10,
        title="Depth and total-height P–VX surfaces",
        before=teaching_before(
            doing="We inspect P–VX response surfaces at median LS and ST with convex-hull and 4D-neighbour support masks.",
            why="The surfaces visualize nonlinear interactions while marking regions where the design gives weak support.",
            question="Do depth and total height rise with P and fall with VX inside supported regions?",
            suspicious="Smooth color outside observed support being presented as measured behaviour.",
        ),
        code="""
support = pd.read_csv(OUT / "gp_observed_support_summary.csv")
display(support)
display(Image(filename=str(OUT / "figures" / "06_depth_P_VX_surface.png")))
display(Image(filename=str(OUT / "figures" / "07_total_height_P_VX_surface.png")))
""",
        after=teaching_after(
            observed="Supported surface regions show the broad P-positive/VX-negative pattern for depth and total height, with unsupported grid cells visibly masked.",
            meaning="The interaction pattern is compatible with Week 6 without claiming values in uncovered regions.",
            reproduced="P–VX structure for depth and total height is classified REPRODUCED.",
            uncertain="Surface shape depends on median LS/ST anchors and the retained Matérn 3/2 interpretability fit.",
        ),
    )

    add_section(
        cells,
        number=11,
        title="Depth LOO error distribution and concentration",
        before=teaching_before(
            doing="We reuse fixed Phase 3 LOO predictions for three Matérn configurations and quantify the heavy-error tail.",
            why="RMSE can be dominated by a small number of simulations; concentration must be measured before changing models.",
            question="Is poor depth performance broad or tail dominated?",
            suspicious="In-sample residuals, case removal, or trimmed RMSE replacing the full metric.",
        ),
        code="""
error_distribution = pd.read_csv(OUT / "depth_error_distribution.csv")
concentration = pd.read_csv(OUT / "depth_error_concentration.csv")
hard_cases = pd.read_csv(OUT / "depth_consensus_hard_cases.csv")
primary_squared_error = hard_cases["squared_error__matern32_learned_nugget"].sort_values(ascending=False)
recomputed_concentration = pd.DataFrame({
    "worst_simulation_count": [1, 3, 5, 10, 20],
    "recomputed_fraction": [primary_squared_error.head(k).sum() / primary_squared_error.sum() for k in [1, 3, 5, 10, 20]],
})
stored_primary_concentration = concentration[concentration["model"].eq("matern32_learned_nugget")]
concentration_reconciliation = stored_primary_concentration.merge(recomputed_concentration, on="worst_simulation_count")
concentration_reconciliation["absolute_difference"] = (
    concentration_reconciliation["fraction_total_squared_error"] - concentration_reconciliation["recomputed_fraction"]
).abs()
display(error_distribution)
display(concentration_reconciliation)
display(Image(filename=str(OUT / "figures" / "09_depth_error_concentration.png")))
""",
        after=teaching_after(
            observed=f"For the primary depth model, the worst 1/3/5/10 simulations contribute {100*depth['worst_1_squared_error_fraction']:.1f}%/{100*depth['worst_3_squared_error_fraction']:.1f}%/{100*depth['worst_5_squared_error_fraction']:.1f}%/{100*depth['worst_10_squared_error_fraction']:.1f}% of total squared error.",
            meaning="Depth error has a substantial heavy tail, but no difficult simulation is removed from reported metrics.",
            reproduced="This is a new Phase 4 diagnosis, not a Week 6 effect replication.",
            uncertain="Heavy-tail concentration alone does not distinguish regime mixture from target-quality or model-family problems.",
        ),
    )

    add_section(
        cells,
        number=12,
        title="Depth error versus observed depth",
        before=teaching_before(
            doing="We relate signed and absolute LOO residuals to observed depth and summarize quantile-based depth bins.",
            why="High-depth cases may be disproportionately difficult even if the broad P/VX trend is correct.",
            question="Are errors concentrated in the high-depth tail or distributed across scales?",
            suspicious="Bins chosen after inspecting outcomes or a high-depth association mistaken for proof of measurement error.",
        ),
        code="""
by_depth = pd.read_csv(OUT / "depth_error_by_observed_depth.csv")
display(by_depth)
display(Image(filename=str(OUT / "figures" / "08_depth_error_vs_observed_depth.png")))
""",
        after=teaching_after(
            observed="Absolute error rises with observed depth, while the largest misses form a smaller heavy-error subgroup rather than uniform failure across all rows.",
            meaning="High penetration is an important descriptor of difficulty, not a reason to discard simulations.",
            reproduced="The positive P–depth trend remains visible despite larger errors at the high-depth end.",
            uncertain="Depth scale can co-vary with Keyhole context, local heterogeneity, and extraction-quality diagnostics.",
        ),
    )

    add_section(
        cells,
        number=13,
        title="Depth error versus Keyhole context",
        before=teaching_before(
            doing="We compare fixed LOO errors across existing Phase 1 Keyhole presence and timing contexts.",
            why="Regime-rich simulations may be overrepresented among hard depth cases.",
            question="Are catastrophic errors enriched among Keyhole-positive or timing-specific groups?",
            suspicious="Building a classifier, changing labels, or claiming Keyhole causes prediction error.",
        ),
        code="""
keyhole = pd.read_csv(OUT / "depth_error_by_keyhole_context.csv")
primary_abs = "absolute_residual__matern32_learned_nugget"
keyhole_recomputed = hard_cases.groupby("has_keyhole").agg(
    recomputed_n=(primary_abs, "size"),
    recomputed_MAE=(primary_abs, "mean"),
    recomputed_RMSE=("squared_error__matern32_learned_nugget", lambda values: np.sqrt(values.mean())),
).reset_index()
display(keyhole)
display(keyhole_recomputed)
display(Image(filename=str(OUT / "figures" / "10_depth_error_keyhole_context.png")))
""",
        after=teaching_after(
            observed="Keyhole-positive simulations have materially larger aggregate depth error, with timing groups reported descriptively.",
            meaning="Keyhole context is an enrichment signal compatible with regime mixture; it is not causal evidence.",
            reproduced="This diagnostic helps explain why a stable average P/VX trend can coexist with hard local cases.",
            uncertain="Group overlap, sparse subgroups, and correlated depth scale limit isolated interpretation.",
        ),
    )

    add_section(
        cells,
        number=14,
        title="Depth error versus input-space sparsity and local heterogeneity",
        before=teaching_before(
            doing="We compare absolute LOO error with standardized 4D neighbour distance and nearby observed-depth variation.",
            why="This separates simple lack of local design support from locally varying response structure.",
            question="Do hard cases occur because they are isolated, or because nearby inputs have sharply different depths?",
            suspicious="Calling neighbour variation a discontinuity without evidence or using old-data points as Phase 3 support.",
        ),
        code="""
sparsity_summary = pd.read_csv(OUT / "depth_sparsity_association_summary.csv")
sparsity_rows = pd.read_csv(OUT / "depth_error_by_local_sparsity.csv")
rho_sparse, p_sparse = spearmanr(sparsity_rows["nearest_neighbor_distance_standardized"], sparsity_rows["primary_absolute_depth_error_um"])
rho_heterogeneity, p_heterogeneity = spearmanr(sparsity_rows["local_5nn_depth_std_um"], sparsity_rows["primary_absolute_depth_error_um"])
display(sparsity_summary)
display(pd.DataFrame([
    {"diagnostic": "nearest-neighbour distance", "recomputed_rho": rho_sparse, "recomputed_p": p_sparse},
    {"diagnostic": "local 5-NN depth SD", "recomputed_rho": rho_heterogeneity, "recomputed_p": p_heterogeneity},
]))
display(sparsity_rows.sort_values("primary_absolute_depth_error_um", ascending=False).head(15))
display(Image(filename=str(OUT / "figures" / "11_sparsity_and_local_heterogeneity.png")))
""",
        after=teaching_after(
            observed=f"Nearest-neighbour sparsity has weak association with error (rho={depth['sparsity_error_rho']:.3f}), whereas local 5-NN depth heterogeneity is much stronger (rho={depth['heterogeneity_error_rho']:.3f}).",
            meaning="Simple marginal isolation is not the main signal; local response heterogeneity is more consistent with a transition/regime mechanism.",
            reproduced="The broad depth directions survive even though local response predictability varies.",
            uncertain="Neighbour heterogeneity is descriptive and does not prove a mathematical discontinuity.",
        ),
    )

    add_section(
        cells,
        number=15,
        title="Depth error versus old-design shift flags",
        before=teaching_before(
            doing="We group new-data errors by Phase 1 descriptors of whether points lie beyond old marginal ranges or the old 4D hull.",
            why="This asks whether newly explored physical regions are especially difficult.",
            question="Are hard new-data responses enriched in old-domain expansion regions?",
            suspicious="Calling these flags extrapolation for a GP trained entirely on new data.",
        ),
        code="""
old_shift = pd.read_csv(OUT / "depth_error_by_old_design_shift.csv")
display(old_shift)
""",
        after=teaching_after(
            observed="The table reports error by old-design membership without treating old data as training support.",
            meaning="These are descriptors of newly explored physical space, not Phase 3 GP extrapolation flags.",
            reproduced="This extends the Week 6/new-data comparison with correct design-shift semantics.",
            uncertain="Marginal-range and convex-hull membership do not fully measure local support density or regime structure.",
        ),
    )

    add_section(
        cells,
        number=16,
        title="Depth error versus Phase 2 quality and ambiguity flags",
        before=teaching_before(
            doing="We join fixed residuals to Phase 2 window stability, depth ambiguity, recording cutoff, and geometric ratio diagnostics.",
            why="Large errors could be amplified by uncertain target extraction rather than response complexity alone.",
            question="Do hard cases overlap the existing target-quality warnings?",
            suspicious="Relabelling targets, redefining T0, or converting diagnostic associations into exclusions.",
        ),
        code="""
quality = pd.read_csv(OUT / "depth_error_by_phase2_quality_flags.csv")
display(quality)
""",
        after=teaching_after(
            observed="Some Phase 2 continuous quality indicators associate with error, but the evidence is not a clean single-flag explanation.",
            meaning="Target quality remains a plausible contributor inside a mixed diagnosis, not grounds for automatic exclusion.",
            reproduced="T0 definitions and source labels remain unchanged.",
            uncertain="Associations among depth scale, sample count, ratios, and physical regime can confound one-variable quality summaries.",
        ),
    )

    add_section(
        cells,
        number=17,
        title="Consensus hard-case physical review",
        before=teaching_before(
            doing="We inspect a deterministic small set of top consensus errors plus well-predicted high-depth contrasts using existing raw traces.",
            why="Aggregate tables cannot reveal whether individual trajectories look physically plausible or geometrically suspicious.",
            question="What conservative mechanisms fit the most difficult cases?",
            suspicious="Downloading hundreds of media files, changing ground truth, or excluding cases after visual review.",
        ),
        code="""
hard_cases = pd.read_csv(OUT / "depth_consensus_hard_cases.csv")
review = pd.read_csv(OUT / "depth_hard_case_review.csv")
display(hard_cases.sort_values("consensus_mean_residual_rank").head(12))
display(review)
display(Image(filename=str(OUT / "figures" / "12_consensus_hard_cases.png")))
display(Image(filename=str(OUT / "figures" / "13_hard_case_depth_traces.png")))
""",
        after=teaching_after(
            observed=f"Twenty-one cases satisfy the cross-kernel consensus rule; the small raw-trace review assigns only conservative diagnostic labels.",
            meaning="Multiple reasonable Matérn configurations tend to fail on the same simulations, consistent with shared data/regime difficulty.",
            reproduced="The main physical trend can reproduce even when a localized subset defeats smooth LOO prediction.",
            uncertain="The small review cannot establish new ground-truth categories or justify exclusions.",
        ),
    )

    add_section(
        cells,
        number=18,
        title="Week 6 versus new-data physical-response stability",
        before=teaching_before(
            doing="We synthesize historical and new-data evidence statement by statement.",
            why="A thesis conclusion should distinguish reproduced, weakened, mixed, reversed, and unresolved claims.",
            question="Which Week 6 physical-response statements survive the new simulation design?",
            suspicious="Overclaiming weak ST evidence or turning a profile-dependent KE relationship into a universal rule.",
        ),
        code="""
stability = pd.read_csv(OUT / "week6_vs_new_data_feature_stability.csv")
display(stability)
display(Image(filename=str(OUT / "figures" / "14_feature_stability_counts.png")))
""",
        after=teaching_after(
            observed="Six statements are REPRODUCED and the qualified KE–LS statement is MIXED; no assessed statement is classified REVERSED.",
            meaning="The new design preserves the dominant physical-response picture while refining one interaction-dependent claim.",
            reproduced="Width–LS, depth P/VX, P–VX surface structure, total-height pattern, and weak sampled-design ST association reproduce.",
            uncertain="Weak observed ST association does not imply substrate temperature is physically unimportant.",
        ),
    )

    add_section(
        cells,
        number=19,
        title="Depth failure diagnosis",
        before=teaching_before(
            doing="We answer D1–D10 and place the evidence into the predeclared model/design/regime/quality/mixed categories.",
            why="Model changes should follow a mechanism-based diagnosis rather than discomfort with one metric.",
            question="Does current evidence justify replacing the retained GP family?",
            suspicious="Forcing a single cause or proposing a new model without resolving data/regime evidence.",
        ),
        code="""
diagnosis = pd.read_csv(OUT / "depth_error_diagnosis_summary.csv")
display(diagnosis)
display(Image(filename=str(OUT / "figures" / "15_depth_diagnosis_summary.png")))
""",
        after=teaching_after(
            observed=f"The overall category is {depth['decision_category']}; neighbour distance is weak, local target heterogeneity and Keyhole/high-depth context are stronger, and kernels share many hard cases.",
            meaning="The evidence is more consistent with a mixed regime/target-quality problem than a demonstrated global model-family failure.",
            reproduced="P-positive and VX-negative depth structure remains stable despite the large LOO tail.",
            uncertain="Targeted support, regime, and raw-quality follow-up is needed before deciding whether a model-family change is warranted.",
        ),
    )

    add_section(
        cells,
        number=20,
        title="Validation and hard stop",
        before=teaching_before(
            doing="We verify the automated safeguards, requirement checklist, notebook execution state, and every manifest hash.",
            why="The scientific handoff must be reproducible and must stop before later thesis phases.",
            question="Are all required artifacts internally consistent with the fixed scope?",
            suspicious="A failed check, stored notebook error, missing artifact, hash mismatch, classifier, new kernel, or silent label/exclusion change.",
        ),
        code="""
validation = pd.read_csv(OUT / "validation_results.csv")
requirements = pd.read_csv(OUT / "requirement_checklist.csv")
manifest = pd.read_csv(OUT / "output_manifest.csv")

def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

manifest_check = manifest.assign(
    exists=manifest["relative_path"].map(lambda name: (OUT / name).is_file()),
    current_sha256=manifest["relative_path"].map(lambda name: sha256(OUT / name)),
)
manifest_check["hash_matches"] = manifest_check["sha256"].eq(manifest_check["current_sha256"])
display(validation)
display(requirements)
display(manifest_check.groupby(["exists", "hash_matches"]).size().rename("files").reset_index())
assert set(validation["status"]) == {"PASS"}
assert set(requirements["status"]) == {"PASS"}
assert manifest_check[["exists", "hash_matches"]].all().all()
assert summary["scope"]["classifier_fitted"] is False
assert summary["scope"]["active_learning"] is False
assert summary["scope"]["level_set_estimation"] is False
print("HARD STOP CONFIRMED — Phase 4 outputs only; no later-phase modelling was performed.")
""",
        after=teaching_after(
            observed=f"The pre-notebook run recorded {summary['validation_counts'].get('PASS', 0)}/24 validation checks, {summary['requirement_counts'].get('PASS', 0)}/20 requirements, and {summary['figure_count']} figures; the final validator refreshes notebook-specific checks after execution.",
            meaning="The artifact set is internally consistent and explicitly bounded to Phase 4.",
            reproduced="The Week 6 replication and Phase 3 LOO reuse are both traceable without changing their source artifacts.",
            uncertain="Later classifier, target-selection, active-learning, level-set, and alternative-model decisions remain intentionally deferred.",
        ),
    )

    notebook = nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "thesis", "language": "python", "name": "thesis"},
            "language_info": {"name": "python", "version": "3"},
            "phase": "Week 7 Phase 4",
            "phase3_parent_sha": summary["phase3_parent_sha"],
            "dataset_revision": summary["dataset_revision"],
        },
    )
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    client = NotebookClient(
        notebook,
        timeout=1_200,
        kernel_name="thesis",
        resources={"metadata": {"path": str(ROOT)}},
        allow_errors=False,
    )
    executed = client.execute()
    nbformat.write(executed, NOTEBOOK_PATH)
    return NOTEBOOK_PATH


if __name__ == "__main__":
    path = build_notebook()
    print(path)
