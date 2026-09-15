"""Build and execute the Week 7 Phase 5 teaching notebook."""

from __future__ import annotations

import json
from pathlib import Path

import nbformat as nbf
import pandas as pd
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week7_05_keyhole_physical_proxy_analysis"
NOTEBOOK = ROOT / "notebooks" / "week_07" / "05_keyhole_physical_proxy_analysis.ipynb"


def before(*, doing: str, why: str, question: str, misleading: str) -> str:
    return f"""**What are we doing?** {doing}

**Why are we doing it?** {why}

**What question does it answer?** {question}

**What would be misleading?** {misleading}"""


def after(*, observed: str, meaning: str, support: str, uncertain: str) -> str:
    return f"""**What did we observe?** {observed}

**What does it mean?** {meaning}

**Does it support a continuous proxy?** {support}

**What remains uncertain?** {uncertain}"""


def add_section(
    cells: list,
    *,
    number: int,
    title: str,
    doing: str,
    why: str,
    question: str,
    misleading: str,
    code: str,
    observed: str,
    meaning: str,
    support: str,
    uncertain: str,
) -> None:
    cells.append(nbf.v4.new_markdown_cell(f"## {number}. {title}\n\n" + before(doing=doing, why=why, question=question, misleading=misleading)))
    cells.append(nbf.v4.new_code_cell(code.strip()))
    cells.append(nbf.v4.new_markdown_cell(after(observed=observed, meaning=meaning, support=support, uncertain=uncertain)))


def build_notebook() -> Path:
    summary = json.loads((OUTPUT / "summary.json").read_text(encoding="utf-8"))
    score = pd.read_csv(OUTPUT / "physical_proxy_candidate_scorecard.csv")
    cv = pd.read_csv(OUTPUT / "physical_proxy_threshold_cv_summary.csv")
    pairwise = pd.read_csv(OUTPUT / "physical_proxy_pairwise_auc_comparison.csv")
    hard = pd.read_csv(OUTPUT / "phase4_depth_hard_cases_vs_phase5_proxy.csv")
    hard_only = hard.loc[hard["consensus_hard_case"].astype(bool)]
    top = score.iloc[0]
    t0 = score.set_index("candidate_id").loc["T0_depth"]
    pair_t0_g3 = pairwise.query("baseline_candidate == 'T0_depth' and comparator_candidate == 'G3'").iloc[0]
    decision = summary["final_target_formulation"]

    cells: list = [
        nbf.v4.new_markdown_cell(
            "# Week 7 Phase 5 — manual Keyhole morphology and continuous physical proxies\n\n"
            "This notebook asks whether one already-defined physical scalar can faithfully represent Ioan's manual cavity-based Keyhole regime. It is a target-formulation analysis, not a classifier, active-learning, or level-set experiment."
        )
    ]

    add_section(
        cells,
        number=1,
        title="Scope and Phase 4 parent commit",
        doing="We establish the exact parent commit, branch, paths, and analysis mode.",
        why="A target-formulation result is only reproducible if its repository parent and hard stop are explicit.",
        question="Did Phase 5 really start from the committed Phase 4 state?",
        misleading="Treating a later main-branch state or an unrecorded worktree as the scientific parent.",
        code="""
from pathlib import Path
import json
import pandas as pd
from IPython.display import display, Image, Markdown

ROOT = Path.cwd()
OUT = ROOT / "outputs" / "week7_05_keyhole_physical_proxy_analysis"
preflight = json.loads((OUT / "phase5_preflight.json").read_text(encoding="utf-8"))
pd.DataFrame([preflight])
""",
        observed=f"The branch is `{summary['phase5_preflight']['phase5_branch']}` at exact Phase 4 commit `{summary['phase5_preflight']['phase5_parent_sha']}`.",
        meaning="All Phase 5 artifacts share one committed Phase 4 parent.",
        support="This prevents repository drift from masquerading as proxy evidence.",
        uncertain="Phase 5 itself remains intentionally uncommitted for review.",
    )

    add_section(
        cells,
        number=2,
        title="Dataset provenance and accepted monitor restoration audit",
        doing="We inspect the exact pinned-to-current Hugging Face tree diff.",
        why="The accepted PR restored old-data monitors, but primary new-data science must remain unchanged.",
        question="Were the only changes 55 pairs of old-data monitor files?",
        misleading="Merely trusting a commit message without checking every changed path and registry partition.",
        code="""
dataset_audit = json.loads((OUT / "dataset_revision_audit.json").read_text(encoding="utf-8"))
revision_diff = pd.read_csv(OUT / "current_revision_diff_audit.csv")
display(pd.DataFrame([dataset_audit]))
display(revision_diff.groupby(["status", "registry_partition", "file_name"]).size().rename("path_count").reset_index())
""",
        observed="Exactly 110 added paths map to 55 `old-data-local` experiments: 55 `time.dat` and 55 `kinetic-energy_melt.dat`. No new-data, label, or geometry path changed.",
        meaning="Current repository provenance can be recorded while the pinned new-data scalar/label content remains the scientific source.",
        support="The restoration cannot create the new-data G3/Keyhole association because none of those paths changed.",
        uncertain="Future changes to Hugging Face main would require a fresh audit.",
    )

    add_section(
        cells,
        number=3,
        title="Ioan's manual Keyhole-label definition",
        doing="We record the supervisor's exact label-provenance statement and its evidence boundary.",
        why="The interpretation changes fundamentally if labels are morphology judgements rather than a known numerical threshold.",
        question="What visual rule informed the Keyhole annotations?",
        misleading="Claiming that Ioan labelled with G3, depth, or another deterministic scalar.",
        code="""
display(Markdown((OUT / "label_provenance.md").read_text(encoding="utf-8")))
""",
        observed="Ioan described manual, almost qualitative labelling, usually guided by cavities directly under the melt pool.",
        meaning="A strong scalar association is an empirical physical consistency result, not circular recovery of a reported threshold.",
        support="It makes a continuous candidate scientifically interesting while preserving the morphology label as reference.",
        uncertain="Manual visual decisions can still be physically coupled to penetration and aspect ratio.",
    )

    add_section(
        cells,
        number=4,
        title="Experiment-level label composition",
        doing="We audit all 165 new-data experiments using validated Phase 1 fields.",
        why="`has_keyhole=False` must not silently be equated with Conduction before checking frame composition.",
        question="How many positives, negatives, transient, persistent, repeated, and timing-defined cases exist?",
        misleading="Dropping the target-ineligible row or regenerating label semantics with a new rule.",
        code="""
labels = pd.read_csv(OUT / "experiment_level_label_audit.csv")
composition = {
    "total": len(labels),
    "Keyhole-positive": int(labels.has_keyhole.astype(bool).sum()),
    "Keyhole-negative": int((~labels.has_keyhole.astype(bool)).sum()),
    "negative without Conduction": int(labels.keyhole_negative_without_conduction.astype(bool).sum()),
    "transient": int(labels.keyhole_transient_by_sequence.astype(bool).sum()),
    "persistent": int(labels.keyhole_persistent_to_last_physical_frame.astype(bool).sum()),
    "repeated": int(labels.repeated_keyhole_episodes.astype(bool).sum()),
}
display(pd.Series(composition, name="experiment_count").to_frame())
display(labels.loc[labels.has_keyhole.astype(bool), "keyhole_timing_relative_to_T0"].value_counts().rename("count").to_frame())
""",
        observed="There are 63 Keyhole-positive and 102 negative experiments; all 102 negatives contain Conduction. Keyhole positives split into 30 transient and 33 persistent cases, including 16 repeated episodes.",
        meaning="The binary experiment label is well defined without relabelling, and important temporal subgroups are large enough to audit.",
        support="A candidate that works only for persistent cases can be detected rather than hidden in one aggregate metric.",
        uncertain="Only saved frame labels are observable; events between saved frames remain outside the label evidence.",
    )

    add_section(
        cells,
        number=5,
        title="Continuous candidate definitions and readiness",
        doing="We list the eight predefined scalars and their machine-derived availability.",
        why="Candidate definitions and missingness must be fixed before looking at separation.",
        question="Which physical quantities are compared, and for how many simulations are they valid?",
        misleading="Inventing a ratio after seeing labels or replacing unavailable values with zero/interpolation.",
        code="""
definitions = pd.read_csv(OUT / "physical_proxy_candidate_definitions.csv")
display(definitions[["candidate_id", "candidate_name", "unit", "definition", "ready_n", "missing_n", "source"]])
""",
        observed="All eight candidates are machine-ready for 164/165 experiments. The missing experiment stays in the population reference with unavailable scalar values.",
        meaning="Candidate comparisons have common missingness here, while readiness remains explicit.",
        support="G3/R3/max depth/T0 retain their earlier definitions; R0 is the predefined T0 depth/width diagnostic.",
        uncertain="R0 couples two scalars and is not as direct a dimensional level-set quantity as G3.",
    )

    add_section(
        cells,
        number=6,
        title="Keyhole versus non-Keyhole descriptive distributions",
        doing="We show distributions and ECDFs for T0 depth, max depth, G3, and R3 without hiding overlap.",
        why="Medians alone can conceal tails, multimodality, and exceptions.",
        question="Do manual Keyhole and negative simulations occupy visibly different physical ranges?",
        misleading="Showing only a fitted separator or a truncated axis that hides discordant cases.",
        code="""
for filename in [
    "01_T0_depth_keyhole_distribution.png",
    "02_max_depth_keyhole_distribution.png",
    "03_G3_keyhole_distribution.png",
    "04_R3_keyhole_distribution.png",
]:
    display(Image(filename=str(OUT / "figures" / filename)))
""",
        observed="G3 exhibits complete observed separation; max depth and R3 show only tiny overlap, while T0 depth shows visibly more overlap.",
        meaning="Persistence-aware or whole-track depth information aligns more closely with cavity-based morphology than an ordinary late-active median.",
        support="The descriptive view strongly motivates formal rank and held-out threshold tests.",
        uncertain="Observed separation in one finite design is not a universal physical law.",
    )

    add_section(
        cells,
        number=7,
        title="Effect sizes and bootstrap intervals",
        doing="We quantify median shifts, rank-biserial effects, Mann–Whitney tests, and simulation-level bootstrap intervals.",
        why="Practical separation and uncertainty matter more than a small p-value alone.",
        question="How large and directionally consistent are group differences?",
        misleading="Equating statistical significance with a faithful proxy.",
        code="""
effects = pd.read_csv(OUT / "physical_proxy_effect_sizes.csv")
display(effects.sort_values("rank_biserial_effect_size", ascending=False)[[
    "candidate_id", "median_difference_keyhole_minus_negative", "median_difference_ci_low",
    "median_difference_ci_high", "rank_biserial_effect_size", "rank_biserial_ci_low",
    "rank_biserial_ci_high", "mann_whitney_two_sided_pvalue"
]])
""",
        observed=f"G3 has the largest rank effect ({score.set_index('candidate_id').loc['G3','rank_biserial_effect_size']:.4f}); 5,000 simulation-level resamples quantify uncertainty in the full run.",
        meaning="The group shift is large in both magnitude and rank ordering.",
        support="This is necessary evidence for a continuous proxy, but threshold generalization remains separate.",
        uncertain="Bootstrap intervals describe this sampled design and label set, not unseen process regimes.",
    )

    add_section(
        cells,
        number=8,
        title="ROC AUC and PR AUC comparison",
        doing="We compare rank separation with both ROC AUC and average precision, preserving raw physical direction.",
        why="The 63/165 Keyhole prevalence makes accuracy alone insufficient.",
        question="Which scalar most consistently ranks manual Keyhole above negatives?",
        misleading="Quietly flipping a sign or claiming a high AUC supplies a stable threshold.",
        code="""
separation = pd.read_csv(OUT / "physical_proxy_univariate_separation.csv")
display(separation[["candidate_id", "n", "physical_direction", "direction_adjusted_roc_auc",
                    "direction_adjusted_roc_auc_ci_low", "direction_adjusted_roc_auc_ci_high",
                    "direction_adjusted_average_precision", "direction_adjusted_average_precision_ci_low",
                    "direction_adjusted_average_precision_ci_high"]])
display(Image(filename=str(OUT / "figures" / "05_main_candidate_roc_curves.png")))
display(Image(filename=str(OUT / "figures" / "06_main_candidate_precision_recall_curves.png")))
""",
        observed=f"G3 leads both ROC AUC ({summary['highest_roc_auc']:.4f}) and average precision ({summary['highest_average_precision']:.4f}).",
        meaning="G3 perfectly ranks the available new-data positives above negatives in this dataset.",
        support="This is exceptionally strong univariate separation with class-imbalance context.",
        uncertain="Rank perfection does not by itself establish that a fold-trained cutoff will handle boundary cases.",
    )

    add_section(
        cells,
        number=9,
        title="Fair paired AUC comparisons",
        doing="We compare specified candidate pairs on the same simulations with paired stratified bootstrap resampling.",
        why="Separate candidate populations or independent intervals can give unfair delta claims.",
        question="Do max depth, G3, or R3 materially improve over T0 depth?",
        misleading="Calling a tiny point-estimate difference material without common rows and a paired interval.",
        code="""
paired = pd.read_csv(OUT / "physical_proxy_pairwise_auc_comparison.csv")
display(paired[["baseline_candidate", "comparator_candidate", "common_complete_n",
                "delta_roc_auc_comparator_minus_baseline", "delta_roc_auc_ci_low",
                "delta_roc_auc_ci_high", "material_improvement"]])
""",
        observed=f"G3 improves on T0 depth by paired AUC Δ={pair_t0_g3['delta_roc_auc_comparator_minus_baseline']:.4f} (95% CI {pair_t0_g3['delta_roc_auc_ci_low']:.4f} to {pair_t0_g3['delta_roc_auc_ci_high']:.4f}); the predeclared material-improvement rule is `{bool(pair_t0_g3['material_improvement'])}`.",
        meaning="The gain over T0 depth is not a missingness artifact.",
        support="Transient/persistent-sensitive depth quantities materially outperform the ordinary T0 median in rank separation.",
        uncertain="G3, max depth, and R3 are so strong that their small pairwise differences are harder to distinguish reliably.",
    )

    add_section(
        cells,
        number=10,
        title="Leakage-free scalar threshold cross-validation",
        doing="For every held-out simulation, training rows alone select direction and threshold by balanced accuracy.",
        why="A continuous level-set proxy should admit a simple rule that generalizes, not only rank well in-sample.",
        question="Can a single scalar threshold predict the held-out manual label?",
        misleading="Reporting the full-data optimum cutoff as predictive performance.",
        code="""
cv = pd.read_csv(OUT / "physical_proxy_threshold_cv_summary.csv")
stability = pd.read_csv(OUT / "physical_proxy_threshold_stability.csv")
display(cv[["candidate_id", "balanced_accuracy", "sensitivity_keyhole_recall", "specificity",
            "precision", "f1", "false_positive", "false_negative",
            "full_data_descriptive_threshold", "full_data_threshold_is_predictive_performance"]])
display(stability[["candidate_id", "majority_direction", "majority_direction_fraction",
                   "threshold_median", "threshold_iqr_over_candidate_iqr", "stability_class"]])
""",
        observed=f"G3 achieves held-out balanced accuracy {top['balanced_accuracy']:.4f}, sensitivity {top['sensitivity_keyhole_recall']:.4f}, and specificity {top['specificity']:.4f}; its threshold class is `{top['stability_class']}`.",
        meaning="The observed G3 gap is wide enough that fold-trained thresholds classify every held-out ready simulation correctly.",
        support="This is the strongest evidence that G3 is more than a descriptive correlate.",
        uncertain="External designs may shrink or shift the threshold gap; Phase 5 does not test out-of-distribution generalization.",
    )

    add_section(
        cells,
        number=11,
        title="T0 timing versus brief Keyhole events",
        doing="We reuse validated timing groups to compare candidate values and held-out sensitivity.",
        why="A late-active T0 median can miss a morphology event that occurs only before T0.",
        question="Does max depth or G3 handle before-T0 Keyhole better than T0 depth?",
        misleading="Inventing exact frame-monitor alignment beyond the saved Phase 2 timing fields.",
        code="""
timing = pd.read_csv(OUT / "physical_proxy_by_keyhole_timing.csv")
display(timing[timing.candidate_id.isin(["T0_depth", "max_depth", "G3", "R3"])][[
    "candidate_id", "group", "n", "median", "cv_sensitivity_within_positive_group"
]])
display(Image(filename=str(OUT / "figures" / "10_keyhole_timing_main_candidates.png")))
""",
        observed=f"T0 depth's held-out transient sensitivity is {t0['transient_keyhole_cv_sensitivity']:.4f}, versus {top['transient_keyhole_cv_sensitivity']:.4f} for G3.",
        meaning="T0 depth loses information for brief/early morphology events that the persistent maximum can still capture.",
        support="G3 remains robust in the very subgroup most likely to challenge a T0 summary.",
        uncertain="The timing categories are coarse and inherit saved-label cadence.",
    )

    add_section(
        cells,
        number=12,
        title="Transient versus persistent Keyhole",
        doing="We compare unchanged Phase 1 transient and persistent groups.",
        why="A proxy that represents only persistent Keyhole would be incomplete for Ioan's experiment-level label.",
        question="Does the leading scalar retain sensitivity for both morphology patterns?",
        misleading="Redefining persistence from the scalar itself.",
        code="""
persistence = pd.read_csv(OUT / "physical_proxy_by_keyhole_persistence.csv")
display(persistence[persistence.candidate_id.isin(["T0_depth", "max_depth", "G3", "R3"])][[
    "candidate_id", "group", "n", "median", "cv_sensitivity_within_positive_group"
]])
display(Image(filename=str(OUT / "figures" / "11_transient_persistent_main_candidates.png")))
""",
        observed=f"G3's held-out sensitivity is {top['transient_keyhole_cv_sensitivity']:.4f} for transient and {top['persistent_keyhole_cv_sensitivity']:.4f} for persistent Keyhole.",
        meaning="The leading scalar is not merely a persistent-label detector on this population.",
        support="Robustness across both subgroups supports a single continuous candidate.",
        uncertain="Transient labels can still reflect short events whose exact duration is not resolved by scalar summaries.",
    )

    add_section(
        cells,
        number=13,
        title="Candidate-candidate redundancy",
        doing="We compute a common-complete Spearman matrix for all predefined scalars.",
        why="G3, max depth, R3, and T0 depth may carry mostly the same ordering information.",
        question="Does the leading scalar add distinct persistence structure or simply duplicate T0 depth?",
        misleading="Treating correlation as causal attribution or automatic feature selection.",
        code="""
correlations = pd.read_csv(OUT / "physical_proxy_candidate_correlations.csv")
display(correlations.query("candidate_left in ['T0_depth','max_depth','G3','R3'] and candidate_right in ['T0_depth','max_depth','G3','R3']").pivot(index="candidate_left", columns="candidate_right", values="spearman_rho"))
display(Image(filename=str(OUT / "figures" / "12_candidate_correlation_heatmap.png")))
""",
        observed="The principal depth candidates are strongly correlated, but T0 depth's weaker transient sensitivity shows that their summary windows are not interchangeable.",
        meaning="G3's value is its persistent high-depth definition rather than a multivariate combination.",
        support="A single physically interpretable scalar remains sufficient for the target-formulation question.",
        uncertain="Correlation does not isolate which physical mechanism creates cavities.",
    )

    add_section(
        cells,
        number=14,
        title="T0 depth versus max depth versus G3 versus R3",
        doing="We answer the ten predeclared main-candidate decision questions in one table.",
        why="A final recommendation should reconcile rank, threshold, subgroup, stability, and interpretability evidence.",
        question="Which of the four main candidates should Phase 6 carry?",
        misleading="Choosing the numerically largest AUC without considering physical meaning or held-out errors.",
        code="""
main_decision = pd.read_csv(OUT / "t0_vs_max_vs_g3_vs_r3_decision.csv")
display(main_decision)
""",
        observed="G3 leads; max depth and R3 are close, while T0 depth is weaker for transient Keyhole.",
        meaning="Persistence-aware dimensional depth offers the best combination of separation and physical interpretability.",
        support="The decision is consistent across multiple independent evidence columns.",
        uncertain="R3 may still be valuable diagnostically because it encodes narrowness as well as depth.",
    )

    add_section(
        cells,
        number=15,
        title="Discordant-case review",
        doing="We select deterministic false negatives/positives from held-out top-candidate thresholds and attach existing media/quality references.",
        why="Aggregate metrics can hide brief events, geometry artifacts, or deep negative cases.",
        question="What kinds of simulations disagree with otherwise strong scalar rules?",
        misleading="Using a cherry-picked in-sample threshold or changing labels after inspecting cases.",
        code="""
discordant = pd.read_csv(OUT / "physical_proxy_discordant_cases.csv")
display(discordant[["review_candidate", "error_type", "experiment_name", "keyhole_persistence_group",
                    "keyhole_timing_relative_to_T0", "diagnostic_review_outcome", "side_gif_reference",
                    "flag_depth_bounding_box_ambiguity_candidate", "label_changed"]])
""",
        observed=f"G3 has no held-out discordant ready simulation. The deterministic review set contains {len(pd.read_csv(OUTPUT / 'physical_proxy_discordant_cases.csv'))} rows from the next strongest proxies, including brief-Keyhole and deep-negative diagnostics.",
        meaning="The perfect G3 result is not obtained by relabelling or suppressing exceptions.",
        support="Absence of G3 fold errors strengthens its candidacy while preserved R3/max errors clarify the evidence boundary.",
        uncertain="Existing side-view references support later human review but Phase 5 does not create new ground truth.",
    )

    add_section(
        cells,
        number=16,
        title="Phase 4 hard-case linkage",
        doing="We join saved Phase 4 LOO depth hard cases to manual labels and held-out proxy results.",
        why="The prior heavy error tail may reflect Keyhole-associated physical extremes rather than simple input sparsity.",
        question="Are Phase 4 consensus hard cases also ambiguous under the strongest scalar proxies?",
        misleading="Refitting Phase 3/4 regression models or treating overlap as causal proof.",
        code="""
hard = pd.read_csv(OUT / "phase4_depth_hard_cases_vs_phase5_proxy.csv")
hard_only = hard.loc[hard.consensus_hard_case.astype(bool)]
display(hard_only[["experiment_name", "has_keyhole_phase5", "observed_depth_um", "value__G3",
                   "value__R3", "any_top3_proxy_cv_discordance", "phase5_interpretation"]])
display(Image(filename=str(OUT / "figures" / "14_phase4_hard_case_overlap.png")))
""",
        observed=f"Among {len(hard_only)} Phase 4 consensus hard cases, {int(hard_only.has_keyhole_phase5.astype(bool).sum())} are manual Keyhole and {int(hard_only.any_top3_proxy_cv_discordance.astype(bool).sum())} disagree with any top-three held-out proxy rule.",
        meaning="The Phase 4 depth tail is largely composed of physically clear Keyhole/extreme-response cases, not scalar-label ambiguity.",
        support="G3 explains regime structure associated with hard depth responses without refitting the depth models.",
        uncertain="This does not prove Keyhole causes GP error; local response heterogeneity remains a descriptive diagnosis.",
    )

    add_section(
        cells,
        number=17,
        title="Proxy candidate scoring",
        doing="We apply a predeclared multi-evidence strong/moderate/weak rule.",
        why="AUC alone cannot establish readiness, threshold stability, subgroup robustness, or physical interpretability.",
        question="Which candidates survive all required evidence dimensions?",
        misleading="Changing score thresholds after seeing which candidate wins.",
        code="""
scorecard = pd.read_csv(OUT / "physical_proxy_candidate_scorecard.csv")
display(scorecard[["overall_rank", "candidate_id", "proxy_classification", "rank_biserial_effect_size",
                   "direction_adjusted_roc_auc", "direction_adjusted_average_precision", "balanced_accuracy",
                   "transient_keyhole_cv_sensitivity", "persistent_keyhole_cv_sensitivity",
                   "threshold_iqr_over_candidate_iqr", "readiness_fraction", "physical_interpretability"]])
display(Image(filename=str(OUT / "figures" / "15_proxy_scorecard_decision.png")))
""",
        observed=f"G3 ranks first and is a `{top['proxy_classification']}` with complete held-out performance and stable thresholds.",
        meaning="Its result is supported by distribution, ranking, threshold, timing, persistence, readiness, and interpretability evidence.",
        support="This satisfies the Phase 5 decision framework for a continuous proxy candidate.",
        uncertain="External validation is still required before treating one numerical cutoff as universal.",
    )

    add_section(
        cells,
        number=18,
        title="Final target-formulation recommendation",
        doing="We state one formulation decision while keeping Ioan's labels as reference.",
        why="Phase 6 needs a controlled target choice, not an ambiguous list of promising metrics.",
        question="Binary primary, continuous candidate, or hybrid/unresolved?",
        misleading="Replacing the manual morphology label or already running the recommended next experiment.",
        code="""
formulation = pd.read_csv(OUT / "phase5_target_formulation_decision.csv")
display(formulation.T)
""",
        observed=f"The decision is **{decision['decision']}**, selecting `{decision['selected_continuous_candidate']}`.",
        meaning=decision["rationale"],
        support="Phase 6 can compare the predefined G3 continuous formulation against the unchanged binary `has_keyhole` reference.",
        uncertain="That comparison and any later level-set boundary are deliberately not executed here.",
    )

    add_section(
        cells,
        number=19,
        title="Validation",
        doing="We inspect automated scientific, provenance, leakage, artifact, and notebook checks.",
        why="A convincing result must reconcile from raw rows and preserve all scope invariants.",
        question="Did the analysis satisfy every declared validation and requirement?",
        misleading="Counting artifact existence without checking hashes or numerical reconciliation.",
        code="""
validation = pd.read_csv(OUT / "validation_results.csv")
requirements = pd.read_csv(OUT / "requirement_checklist.csv")
display(validation.groupby("status").size().rename("validation_count").to_frame())
display(requirements.groupby("status").size().rename("requirement_count").to_frame())
display(validation)
""",
        observed="All scientific and repository checks pass; after this notebook executes, the validator refreshes the notebook and manifest checks once more.",
        meaning="The stored claims are machine-reconciled rather than hand-copied from plots.",
        support="The result is review-ready and reproducible from saved artifacts.",
        uncertain="Automated validation cannot substitute for future external scientific validation.",
    )

    add_section(
        cells,
        number=20,
        title="Hard stop",
        doing="We display the prohibited-action ledger and end Phase 5.",
        why="Target formulation must not silently expand into modelling or acquisition selection.",
        question="What was intentionally not done?",
        misleading="Treating a recommendation as an executed classifier, level-set, or active-learning result.",
        code="""
summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
display(pd.Series(summary["hard_stop"], name="performed").to_frame())
print("STOP: Phase 5 complete. No classifier, GP fit, active learning, or level-set experiment follows.")
""",
        observed="Every prohibited action remains false.",
        meaning="Phase 5 ends at a target-formulation recommendation.",
        support="The evidence can inform Phase 6 without pre-empting it.",
        uncertain="The controlled G3-versus-binary comparison is future work and needs explicit approval.",
    )

    notebook = nbf.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
            "phase": "Week 7 Phase 5",
            "phase4_parent_sha": summary["phase5_preflight"]["phase5_parent_sha"],
        },
    )
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, NOTEBOOK)
    client = NotebookClient(
        notebook,
        timeout=1_200,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
        allow_errors=False,
    )
    executed = client.execute()
    nbf.write(executed, NOTEBOOK)
    return NOTEBOOK


if __name__ == "__main__":
    path = build_notebook()
    print(path)
