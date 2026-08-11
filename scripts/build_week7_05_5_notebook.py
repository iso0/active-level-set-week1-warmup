"""Build and execute the Week 7 Phase 5.5 teaching notebook."""

from __future__ import annotations

import json
from pathlib import Path

import nbformat as nbf
import pandas as pd
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "week7_05_5_g3_robustness_transfer_analysis"
NOTEBOOK = ROOT / "notebooks" / "week_07" / "05_5_g3_robustness_transfer_analysis.ipynb"


def markdown(title: str, what: str, why: str, avoid: str) -> str:
    return (
        f"## {title}\n\n"
        f"**What are we checking?** {what}\n\n"
        f"**Why does it matter?** {why}\n\n"
        f"**Interpretation to avoid.** {avoid}"
    )


def result(text: str) -> str:
    return f"**Result and interpretation.** {text}"


def code(source: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(source.strip())


def main() -> int:
    summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    readiness = pd.read_csv(OUT / "population_readiness_by_partition.csv").set_index("population")
    labels = pd.read_csv(OUT / "label_composition_by_partition.csv").set_index("population")
    within = pd.read_csv(OUT / "threshold_within_population_summary.csv")
    transfer = pd.read_csv(OUT / "threshold_cross_population_transfer_summary.csv")
    bootstrap = pd.read_csv(OUT / "proxy_bootstrap_uncertainty_summary.csv")
    decisions = pd.read_csv(OUT / "g3_vs_r3_vs_max_vs_t0_transfer_decision.csv").set_index("candidate_id")
    margins = pd.read_csv(OUT / "threshold_margin_diagnostics.csv")
    g3_within = within[within["candidate_id"].eq("G3")].set_index("population")
    g3_transfer = transfer[
        transfer["candidate_id"].eq("G3")
        & transfer["evaluation_type"].eq("cross_population_transfer")
    ].set_index("route_id")
    remote_ci = bootstrap[
        bootstrap["candidate_id"].eq("G3")
        & bootstrap["population_or_route"].eq("old-data-remote-clean")
        & bootstrap["metric"].eq("loo_balanced_accuracy")
    ].iloc[0]
    g3_gap = margins[
        margins["candidate_id"].eq("G3") & margins["band_half_width"].eq(2.0)
    ].set_index("population")

    nb = nbf.v4.new_notebook()
    cells: list[nbf.NotebookNode] = []

    sections = [
        (
            "1. Scope and relationship to Phase 5",
            "Place this stress test after the committed Phase 5 scalar-proxy screen.",
            "Phase 5 used new-data only; Phase 5.5 asks whether that evidence survives domain transfer.",
            "This is not Phase 6 modelling and does not redefine Keyhole.",
            """
from pathlib import Path
import json
import pandas as pd
from IPython.display import Image, display
ROOT = Path.cwd()
OUT = ROOT / 'outputs' / 'week7_05_5_g3_robustness_transfer_analysis'
summary = json.loads((OUT / 'summary.json').read_text(encoding='utf-8'))
pd.Series({
    'phase': summary['phase'],
    'phase5_parent': summary['phase5_parent'],
    'phase55_branch': summary['phase55_branch'],
    'models_fitted': summary['scope']['predictive_models_fitted'],
    'labels_modified': summary['scope']['labels_modified'],
})
""",
            f"The analysis starts from exact Phase 5 commit `{summary['phase5_parent']}` and remains scalar-diagnostic only.",
        ),
        (
            "2. Provenance: Phase 5 commit and merged HF restoration",
            "Record the exact code parent and current dataset revision.",
            "A transfer conclusion is meaningful only for a fixed, auditable snapshot.",
            "Do not mix the pinned Phase 5 snapshot with floating `main` without an explicit diff.",
            """
provenance = json.loads((OUT / 'input_provenance.json').read_text(encoding='utf-8'))
pd.Series({
    'phase5_parent': provenance['phase55_parent'],
    'pinned_revision': provenance['pinned_revision'],
    'analysis_revision': provenance['analysis_revision'],
    'target_refresh_rule': provenance['target_refresh_rule'],
})
""",
            "The merged revision is treated as a new exact scientific snapshot; the original Phase 5 result remains pinned to its earlier revision.",
        ),
        (
            "3. Verification of what changed in HF since the pinned snapshot",
            "Inspect every changed path between the pinned and current revisions.",
            "Only the approved old-data monitor restoration may enter this analysis.",
            "The absence of a changed filename is not inferred; it is checked from the Git tree.",
            """
audit = json.loads((OUT / 'hf_change_audit.json').read_text(encoding='utf-8'))
display(pd.Series({k: audit[k] for k in [
    'change_record_count','changed_experiment_count','filename_counts',
    'partition_experiment_counts','new_data_paths_changed','label_paths_changed',
    'geometry_paths_changed','modified_or_deleted_paths','only_expected_monitor_additions'
]}))
display(pd.read_csv(OUT / 'hf_changed_paths.csv').head(8))
""",
            "Exactly 110 additions were found: 55 `time.dat` and 55 `kinetic-energy_melt.dat`, all old-data-local. No label, new-data, geometry, or iteration path changed.",
        ),
        (
            "4. Rebuilt full-population readiness table",
            "Show which retained simulations have complete physical targets at the current revision.",
            "Transfer calculations must exclude unavailable candidate values without deleting their simulations.",
            "A physically ineligible row is not a bad label and must not disappear.",
            """
readiness = pd.read_csv(OUT / 'population_readiness_by_partition.csv')
display(readiness)
display(Image(filename=str(OUT / 'figures' / '01_partition_overview.png')))
""",
            f"Usable counts are {int(readiness.loc['new-data','physical_target_ready_count'])}/165 new, {int(readiness.loc['old-data-local','physical_target_ready_count'])}/179 old-local, {int(readiness.loc['old-data-remote-clean','physical_target_ready_count'])}/63 old-remote, and {int(readiness.loc['all-combined','physical_target_ready_count'])}/407 overall. All 407 rows remain present.",
        ),
        (
            "5. Partition label composition",
            "Compare manual Keyhole prevalence across partitions.",
            "Large prevalence shifts affect precision-recall results and threshold stability.",
            "Do not interpret sparse old-data positives as proof that the physical process changed.",
            """
composition = pd.read_csv(OUT / 'label_composition_by_partition.csv')
display(composition)
display(Image(filename=str(OUT / 'figures' / '02_label_composition.png')))
""",
            f"Keyhole prevalence is {labels.loc['new-data','keyhole_positive_fraction']:.1%} in new-data, {labels.loc['old-data-local','keyhole_positive_fraction']:.1%} in old-local, and {labels.loc['old-data-remote-clean','keyhole_positive_fraction']:.1%} in old-remote. The old partitions therefore provide a severe sparse-positive stress test.",
        ),
        (
            "6. Reminder: what G3, R3, max depth, and T0 depth mean",
            "Restate the four primary scalar definitions before comparing metrics.",
            "The candidates answer different physical questions: persistence, ratio, spike, and late-window depth.",
            "A higher AUC does not make two physical definitions interchangeable.",
            """
definitions = pd.read_csv(ROOT / 'outputs' / 'week7_05_keyhole_physical_proxy_analysis' / 'physical_proxy_candidate_definitions.csv')
display(definitions[definitions['candidate_id'].isin(['G3','R3','max_depth','T0_depth'])][
    ['candidate_id','candidate_name','unit','definition','role']
])
""",
            "G3 is the predefined 50 μm persistent-depth statistic; max depth is intentionally more spike-sensitive. Both remain comparisons to the manual morphology label, not label definitions.",
        ),
        (
            "7. Candidate distributions by partition and label",
            "Inspect the raw scalar distributions before summarizing them with one score.",
            "Visible overlap, gaps, and partition shifts explain later threshold behavior.",
            "Do not read boxplots as held-out validation.",
            """
for name in ['03_G3_distributions.png','04_R3_distributions.png','05_max_depth_distributions.png','06_T0_depth_distributions.png']:
    display(Image(filename=str(OUT / 'figures' / name)))
""",
            "G3 and max depth retain strong ordering, but old-local has visibly more negative/positive overlap and a lower G3 decision region than new-data.",
        ),
        (
            "8. Within-population LOO threshold performance",
            "Select each threshold without the held-out simulation inside each population.",
            "This tests local threshold reproducibility while preventing single-row leakage.",
            "Within-population LOO is not the same as transfer to another partition.",
            """
within = pd.read_csv(OUT / 'threshold_within_population_summary.csv')
display(within[within['candidate_id'].isin(['G3','R3','max_depth','T0_depth'])][
    ['population','candidate_id','cv_n','balanced_accuracy','sensitivity_keyhole_recall','specificity',
     'false_positive','false_negative','full_data_descriptive_threshold']
])
display(Image(filename=str(OUT / 'figures' / '11_within_population_performance.png')))
""",
            f"G3 LOO balanced accuracy is {g3_within.loc['new-data','balanced_accuracy']:.3f} in new-data, {g3_within.loc['old-data-local','balanced_accuracy']:.3f} in old-local, and {g3_within.loc['old-data-remote-clean','balanced_accuracy']:.3f} in old-remote. The last value is driven by only two positives and must be read with its interval.",
        ),
        (
            "9. Cross-population threshold transfer",
            "Freeze a threshold on one population and evaluate it on a disjoint population.",
            "This is the direct test of whether the Phase 5 new-data threshold travels to old data and back.",
            "Do not tune a threshold after looking at the test partition.",
            """
transfer = pd.read_csv(OUT / 'threshold_cross_population_transfer_summary.csv')
display(transfer[(transfer['candidate_id'].isin(['G3','R3','max_depth','T0_depth'])) &
                 (transfer['evaluation_type'] == 'cross_population_transfer')][
    ['route_id','candidate_id','train_n','test_n','training_selected_threshold','balanced_accuracy',
     'sensitivity','specificity','false_positive','false_negative']
])
display(Image(filename=str(OUT / 'figures' / '12_cross_population_transfer.png')))
""",
            f"For G3, new→old-local balanced accuracy is {g3_transfer.loc['new_to_old_local','balanced_accuracy']:.3f} with sensitivity {g3_transfer.loc['new_to_old_local','sensitivity']:.3f}; all-old→new is {g3_transfer.loc['all_old_to_new','balanced_accuracy']:.3f}. G3 transfers directionally, but a single fixed threshold is not invariant.",
        ),
        (
            "10. Threshold stability",
            "Compare fold-selected threshold distributions within each population.",
            "Stable direction can coexist with a shifted numerical threshold.",
            "Do not call a threshold universal merely because its LOO IQR is small in one partition.",
            """
stability = pd.read_csv(OUT / 'threshold_stability_summary.csv')
display(stability[stability['candidate_id'].isin(['G3','R3','max_depth','T0_depth'])][
    ['population','candidate_id','majority_direction','majority_direction_fraction','threshold_median',
     'threshold_iqr','threshold_iqr_over_candidate_iqr','stability_class']
])
display(Image(filename=str(OUT / 'figures' / '13_threshold_stability.png')))
""",
            f"G3 points upward in every population, but descriptive thresholds shift from {g3_within.loc['old-data-local','full_data_descriptive_threshold']:.1f} μm (old-local) to {g3_within.loc['new-data','full_data_descriptive_threshold']:.1f} μm (new) and {g3_within.loc['old-data-remote-clean','full_data_descriptive_threshold']:.1f} μm (old-remote). Direction is robust; location is domain-sensitive.",
        ),
        (
            "11. Threshold margin and gap diagnostics",
            "Measure the nearest cases and occupancy around each descriptive threshold.",
            "An empty gap is stronger descriptive evidence than a threshold sitting inside dense overlap.",
            "A sample gap is not guaranteed to persist in future simulations.",
            """
margins = pd.read_csv(OUT / 'threshold_margin_diagnostics.csv')
display(margins[(margins['candidate_id'] == 'G3') & (margins['band_half_width'] == 2.0)][
    ['population','descriptive_threshold','class_gap_in_positive_direction','empty_class_gap',
     'threshold_inside_empty_gap','within_band_count','nearest_below_distance','nearest_above_distance']
])
display(Image(filename=str(OUT / 'figures' / '08_threshold_gap_margin.png')))
""",
            f"New-data has a {g3_gap.loc['new-data','class_gap_in_positive_direction']:.2f} μm empty G3 gap, while old-local has overlap ({g3_gap.loc['old-data-local','class_gap_in_positive_direction']:.2f} μm signed gap). The perfect Phase 5 separation is therefore not reproduced as a universal class gap.",
        ),
        (
            "12. Bootstrap uncertainty",
            "Attach simulation-level 95% intervals to rank, LOO, and transfer metrics.",
            "Sparse positive classes can make a seemingly good point estimate imprecise.",
            "Do not treat 5,000 resamples as 5,000 independent simulations.",
            """
boot = pd.read_csv(OUT / 'proxy_bootstrap_uncertainty_summary.csv')
display(boot[(boot['candidate_id'] == 'G3') &
             (boot['metric'].isin(['roc_auc','average_precision','loo_balanced_accuracy','transfer_balanced_accuracy']))][
    ['analysis_type','population_or_route','metric','estimate','ci_low','ci_high','bootstrap_resamples','bootstrap_unit']
])
display(Image(filename=str(OUT / 'figures' / '09_roc_by_population.png')))
display(Image(filename=str(OUT / 'figures' / '10_pr_by_population.png')))
""",
            f"Old-remote G3 LOO balanced accuracy is {remote_ci['estimate']:.2f}, but its 95% interval is {remote_ci['ci_low']:.2f}–{remote_ci['ci_high']:.2f}. The interval correctly exposes the two-positive limitation.",
        ),
        (
            "13. Transient vs persistent robustness",
            "Compare G3 and the other main candidates across label-sequence persistence groups.",
            "A useful proxy should not work only for long persistent Keyhole episodes.",
            "Saved-frame persistence is still an annotation subgroup, not continuous dwell time.",
            """
persistence = pd.read_csv(OUT / 'subgroup_transient_persistent_summary.csv')
display(persistence[(persistence['candidate_id'].isin(['G3','R3','max_depth','T0_depth'])) &
                    (persistence['subgroup_type'] == 'transient_persistent')])
display(Image(filename=str(OUT / 'figures' / '14_persistence_subgroups.png')))
""",
            "G3 remains elevated for transient and persistent positive groups, but sparse old-data positives prevent a strong partition-specific persistence claim.",
        ),
        (
            "14. T0-overlap timing robustness",
            "Stratify proxy values by where Keyhole-labelled frames fall relative to T0.",
            "This checks whether late-window timing explains why T0 depth underperforms persistent/extreme measures.",
            "Do not infer event causality from saved-frame alignment alone.",
            """
timing = pd.read_csv(OUT / 'subgroup_t0_timing_summary.csv')
display(timing[timing['candidate_id'].isin(['G3','R3','max_depth','T0_depth'])])
display(Image(filename=str(OUT / 'figures' / '15_t0_timing_subgroups.png')))
""",
            "Persistent and extreme measures retain information when Keyhole occurs outside the late T0 window; this is consistent with T0 depth's weaker transfer score, without proving a causal timing mechanism.",
        ),
        (
            "15. Old vs new domain and process-map context",
            "Compare P–VX coverage and G3 values across base partitions.",
            "Threshold movement may reflect domain composition as well as label prevalence.",
            "These maps are descriptive and are not a fitted process boundary.",
            """
process_map = pd.read_csv(OUT / 'process_map_partition_summary.csv')
display(process_map)
display(Image(filename=str(OUT / 'figures' / '16_process_map_label.png')))
display(Image(filename=str(OUT / 'figures' / '17_process_map_G3.png')))
""",
            "The partitions occupy different process ranges and carry sharply different positive prevalence. This supports a domain-shift caveat rather than a universal threshold claim.",
        ),
        (
            "16. Hard-case linkage",
            "Link Phase 4 depth-model hard cases and Phase 5 scalar discordances to current LOO predictions.",
            "Known difficult simulations should remain visible when judging a proxy.",
            "This review does not relabel or exclude any case.",
            """
hard = pd.read_csv(OUT / 'phase4_phase5_hard_case_transfer_context.csv')
display(hard[hard['consensus_hard_case'] | hard['phase5_discordant_review_case']][
    ['experiment_name','has_keyhole','consensus_hard_case','phase5_discordant_review_case',
     'loo_correct__G3','loo_signed_margin__G3','keyhole_persistence_group','keyhole_timing_group']
])
display(Image(filename=str(OUT / 'figures' / '18_G3_vs_R3.png')))
display(Image(filename=str(OUT / 'figures' / '19_G3_vs_max_depth.png')))
""",
            "Hard cases remain explicit and linked to held-out margins. Their presence supports carrying multiple physical diagnostics forward instead of silently pruning difficult rows.",
        ),
        (
            "17. Boundary-formulation interpretation",
            "Translate the stress tests into a conservative formulation recommendation.",
            "The key decision is whether G3 should be a universal threshold, a continuous companion, or neither.",
            "Do not let a post-hoc scalar threshold overwrite the manual morphology reference.",
            """
recommendation = pd.read_csv(OUT / 'phase55_boundary_formulation_recommendation.csv')
display(recommendation.T)
display(Image(filename=str(OUT / 'figures' / '07_sorted_values_thresholds.png')))
""",
            "The evidence supports retaining binary `has_keyhole`, rejecting a universal fixed G3 threshold, and carrying G3 only as a continuous companion with max depth as the stronger transfer benchmark under a separately approved Phase 6 protocol.",
        ),
        (
            "18. Final Phase 5.5 recommendation",
            "Compare the four primary candidates using the same within/transfer evidence.",
            "A final recommendation should reflect worst-route behavior, not only new-data AUC.",
            "Do not declare the leading scalar to be a causal or label-defining variable.",
            """
decisions = pd.read_csv(OUT / 'g3_vs_r3_vs_max_vs_t0_transfer_decision.csv')
scorecard = pd.read_csv(OUT / 'phase55_scorecard.csv')
display(decisions)
display(scorecard[scorecard['candidate_id'].isin(['G3','R3','max_depth','T0_depth'])])
display(Image(filename=str(OUT / 'figures' / '20_phase55_decision_summary.png')))
""",
            f"Max depth is the robust cross-partition benchmark (worst transfer BA {decisions.loc['max_depth','worst_transfer_balanced_accuracy']:.3f}). G3 is transferable with a partition-shift caveat (worst BA {decisions.loc['G3','worst_transfer_balanced_accuracy']:.3f}, worst sensitivity {decisions.loc['G3','worst_transfer_sensitivity']:.3f}).",
        ),
        (
            "19. Validation",
            "Show automated scientific, scope, and artifact checks.",
            "A teaching narrative is trustworthy only if its stored outputs match validated artifacts.",
            "Passing checks do not eliminate sampling limitations.",
            """
validation = pd.read_csv(OUT / 'validation_results.csv')
requirements = pd.read_csv(OUT / 'requirement_checklist.csv')
display(validation)
display(requirements)
""",
            f"The full analysis produced {summary['validation'].get('PASS',0)} passing core checks and {summary['requirements'].get('PASS',0)} passing requirements before notebook-aware closeout validation.",
        ),
        (
            "20. Hard stop",
            "Restate what Phase 5.5 did not do.",
            "Clear stopping boundaries prevent scalar diagnostics from silently becoming predictive modelling.",
            "Do not continue into classifiers, Gaussian processes, active learning, acquisition, or level-set estimation here.",
            """
scope = summary['scope']
pd.Series({
    'predictive_models_fitted': scope['predictive_models_fitted'],
    'classifiers_fitted': scope['classifiers_fitted'],
    'active_learning_run': scope['active_learning_run'],
    'level_set_estimated': scope['level_set_estimated'],
    'labels_modified': scope['labels_modified'],
    'simulations_removed': scope['simulations_removed'],
    'phase55_committed_or_pushed': False,
})
""",
            "Phase 5.5 stops at validated robustness and transfer diagnostics. The work remains uncommitted and unpushed, as requested.",
        ),
    ]

    cells.append(nbf.v4.new_markdown_cell(
        "# Week 7 Phase 5.5 — G3 robustness and transfer analysis\n\n"
        "A teaching notebook for current-revision target readiness, within-population thresholds, "
        "cross-population transfer, uncertainty, subgroup stress tests, and a conservative boundary recommendation."
    ))
    for title, what, why, avoid, source, interpretation in sections:
        cells.append(nbf.v4.new_markdown_cell(markdown(title, what, why, avoid)))
        cells.append(code(source))
        cells.append(nbf.v4.new_markdown_cell(result(interpretation)))

    nb["cells"] = cells
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3"},
    }
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, NOTEBOOK)
    client = NotebookClient(
        nb,
        timeout=600,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
        allow_errors=False,
    )
    executed = client.execute()
    nbf.write(executed, NOTEBOOK)
    print(f"Built {NOTEBOOK} with {len(sections)} executed code cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
