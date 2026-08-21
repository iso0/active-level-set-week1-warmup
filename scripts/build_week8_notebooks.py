"""Build the two Week 8 teaching notebooks from validated saved artifacts."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import nbformat as nbf
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT1 = ROOT / "outputs" / "week8_01_final_sample_efficiency"
OUT2 = ROOT / "outputs" / "week8_02_thesis_consolidation"
NOTEBOOK_DIR = ROOT / "notebooks" / "week_08"
NB1 = NOTEBOOK_DIR / "01_final_sample_efficiency.ipynb"
NB2 = NOTEBOOK_DIR / "02_thesis_evidence_consolidation.ipynb"


def md(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(dedent(text).strip())


def code(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(dedent(text).strip())


def section(
    number: int,
    title: str,
    explanation: str,
    code_text: str,
    interpretation: str,
) -> list[nbf.NotebookNode]:
    return [
        md(
            f"""
            ## {number}. {title}

            {explanation}

            **What does this mean in plain English?** {interpretation}
            """
        ),
        code(code_text),
    ]


def notebook_metadata() -> dict:
    return {
        "kernelspec": {
            "display_name": "Python 3 (ipykernel)",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.12"},
        "week8_scope": {
            "new_simulator_runs": False,
            "expensive_benchmark_rerun": False,
            "source_phase7_commit": "167aad945b20822de712e891e901bd3ec6d5ffc6",
        },
    }


def build_phase1() -> nbf.NotebookNode:
    snapshots = pd.read_csv(OUT1 / "budget_snapshot_b1.csv")
    equivalent = pd.read_csv(OUT1 / "random_equivalent_budget.csv")
    confidence = pd.read_csv(OUT1 / "predictive_confidence_summary.csv")
    b40 = snapshots[(snapshots["budget"] == 40) & (snapshots["method"] == "binary_uncertainty_repulsion")].iloc[0]
    r40 = snapshots[(snapshots["budget"] == 40) & (snapshots["method"] == "shared_random_binary_head")].iloc[0]
    eq30 = equivalent[equivalent["binary_budget"] == 30].iloc[0]
    eq40 = equivalent[equivalent["binary_budget"] == 40].iloc[0]
    conf40 = confidence[(confidence["budget"] == 40) & (confidence["subset"] == "B1_q20")].iloc[0]

    cells: list[nbf.NotebookNode] = [
        md(
            """
            # Week 8 Phase 1 — final sample-efficiency quantification

            This notebook turns the frozen Week 7 real-data active-learning experiment into concrete simulator-budget statements. It reads authoritative saved rows only. It does **not** run a simulator, fit a new acquisition family, change a split, relabel a case, or retune the Binary GPC.

            The primary result is empirical held-out accuracy on B1-q20/q30 boundary-like subsets. Saved GPC probabilities support a separate confidence/calibration diagnostic; neither quantity is called certainty about the continuous physical boundary.
            """
        )
    ]
    cells += section(
        1,
        "Week 8 question",
        "We ask how much held-out boundary-region performance is obtained for each total simulator-query budget and how many queries Binary saves relative to Random.",
        """
        question = "How many total queries are needed for a declared empirical boundary-accuracy target?"
        print(question)
        print("Mode: offline / retrospective; no new simulator runs")
        """,
        "The task is measurement and consolidation, not another method-development round.",
    )
    cells += section(
        2,
        "Exact Phase 7 provenance",
        "The Week 8 worktree must start at the exact published Phase 7 commit and preserve its validation state.",
        """
        from pathlib import Path
        import json
        import pandas as pd
        import numpy as np
        from IPython.display import Image, display

        ROOT = Path.cwd()
        OUT1 = ROOT / "outputs/week8_01_final_sample_efficiency"
        OUT2 = ROOT / "outputs/week8_02_thesis_consolidation"
        P7 = ROOT / "outputs/week7_07_final_boundary_hybrid_benchmark"
        preflight = json.loads((OUT1 / "phase8_01_preflight.json").read_text(encoding="utf-8"))
        source_audit = json.loads((OUT1 / "phase7_source_audit.json").read_text(encoding="utf-8"))
        display(pd.Series({
            "Week 8 branch": preflight["week8_branch"],
            "exact Phase 7 parent": preflight["exact_phase7_parent"],
            "remote verified": preflight["remote_phase7_verified"],
            "Phase 7 validation": f"{source_audit['phase7_validation_pass']}/{source_audit['phase7_validation_total']} PASS",
            "expensive benchmark rerun": preflight["expensive_experiment_rerun"],
        }))
        """,
        "Every result below is tied to one exact published parent, so later prose cannot silently drift to another experiment.",
    )
    cells += section(
        3,
        "Frozen primary method",
        "The final primary arm is Binary GPC plus `binary_uncertainty_repulsion`. Random is the exact shared baseline and Max-Depth straddle is the secondary comparator.",
        """
        methods = pd.DataFrame([
            ["Binary", "binary_uncertainty_repulsion", "primary"],
            ["Random", "shared_random_binary_head", "baseline"],
            ["Max-Depth", "max_depth_straddle", "secondary continuous comparator"],
        ], columns=["display", "saved method id", "Week 8 role"])
        display(methods)
        print("Inputs: P, VX, LS, ST; ST = substrate temperature")
        """,
        "The winner is already frozen; Week 8 quantifies its sample efficiency without tuning it again.",
    )
    cells += section(
        4,
        "Load the authoritative 20 matched runs",
        "The row-level learning curves retain all repeated folds and all integer budgets. We filter only the three declared Week 8 methods.",
        """
        raw = pd.read_csv(P7 / "phase7_learning_curve_summary.csv", low_memory=False)
        method_ids = methods["saved method id"].tolist()
        learning = raw[raw["method"].isin(method_ids)].copy()
        display(learning.groupby("method").agg(runs=("run_id", "nunique"), min_budget=("budget", "min"), max_budget=("budget", "max")))
        assert learning["run_id"].nunique() == 20
        """,
        "All comparisons use the same 20 outer runs; a favorable run is never selected by hand.",
    )
    cells += section(
        5,
        "Reconcile the budget axis",
        "Nineteen runs start at 12 queries and one effective warm start is 16. Therefore the complete matched mean-curve grid begins at budget 16.",
        """
        coverage = learning.groupby(["method", "budget"])["run_id"].nunique().unstack(0)
        display(coverage.loc[12:20])
        assert (coverage.loc[16:80] == 20).all().all()
        common_start, final_budget = 16, 80
        """,
        "Run-level first crossings can begin at each run's real warm start, while aggregate curves and AULCs use the fair common 16–80 grid.",
    )
    cells += section(
        6,
        "What q20 and q30 mean",
        "B1 ranks simulations by standardized distance to the nearest simulation with the opposite manual label. q20 and q30 select the most boundary-like 20% and 30% for evaluation only.",
        """
        predictions = pd.read_csv(P7 / "phase7_all_method_prediction_checkpoints.csv", low_memory=False)
        check = predictions[(predictions["method"] == "binary_uncertainty_repulsion") & (predictions["budget"] == 40)]
        display(pd.Series({
            "pooled B1-q20 held-out prediction rows": int(check["test_B1_q20"].sum()),
            "pooled B1-q30 held-out prediction rows": int(check["test_B1_q30"].sum()),
            "outer runs": check["run_id"].nunique(),
        }))
        """,
        "q20/q30 are declared subsets of sampled held-out points, not confidence bands around a continuous physical contour.",
    )
    cells += section(
        7,
        "Convert boundary error to accuracy",
        "For every run and budget, empirical boundary accuracy is defined exactly as one minus the saved boundary error.",
        """
        learning["recomputed_B1_q20_accuracy"] = 1 - learning["B1_q20_error"]
        saved_curve = pd.read_csv(OUT1 / "boundary_accuracy_run_level.csv")
        merged = saved_curve[(saved_curve["boundary_definition"] == "B1") & (saved_curve["quantile"] == 20)].merge(
            learning[["run_id", "method", "budget", "recomputed_B1_q20_accuracy"]],
            on=["run_id", "method", "budget"], validate="one_to_one"
        )
        max_difference = (merged["boundary_accuracy"] - merged["recomputed_B1_q20_accuracy"]).abs().max()
        print("maximum absolute identity difference:", max_difference)
        assert max_difference < 1e-12
        """,
        "The reported percentages are a transparent relabelling of error, not a newly fitted or smoothed statistic.",
    )
    cells += section(
        8,
        "Budget snapshots",
        "The headline budgets show q20/q30 accuracy, global balanced accuracy, and discovery counts side by side.",
        """
        snapshots = pd.read_csv(OUT1 / "budget_snapshot_b1.csv")
        view = snapshots[snapshots["budget"].isin([20, 30, 40, 50, 60, 70, 80])][[
            "budget", "method_label", "mean_q20_accuracy", "mean_q30_accuracy",
            "mean_balanced_accuracy", "mean_keyhole_discovered"
        ]]
        display(view.style.format({
            "mean_q20_accuracy": "{:.1%}", "mean_q30_accuracy": "{:.1%}",
            "mean_balanced_accuracy": "{:.1%}", "mean_keyhole_discovered": "{:.2f}"
        }))
        """,
        f"At budget 40, Binary is {b40['mean_q20_accuracy']:.1%} on B1-q20 versus Random {r40['mean_q20_accuracy']:.1%}; the difference is {(b40['mean_q20_accuracy']-r40['mean_q20_accuracy'])*100:.1f} percentage points.",
    )
    cells += section(
        9,
        "B1-q20 learning curve",
        "The mean curve and descriptive t intervals summarize the 20 matched run trajectories without smoothing.",
        """
        display(Image(filename=str(OUT1 / "figures/01_b1_q20_accuracy_vs_budget.png")))
        """,
        "Binary remains above Random over most of the common budget range; Max-Depth exposes the boundary/global trade-off.",
    )
    cells += section(
        10,
        "B1-q30 learning curve",
        "q30 broadens the evaluation region and checks that the conclusion is not unique to the narrow q20 subset.",
        """
        display(Image(filename=str(OUT1 / "figures/02_b1_q30_accuracy_vs_budget.png")))
        """,
        f"At budget 40, Binary reaches {b40['mean_q30_accuracy']:.1%} B1-q30 accuracy versus {r40['mean_q30_accuracy']:.1%} for Random.",
    )

    target_explanations = {
        70: "The 70% target is easy for this discrete held-out subset and is often met at the warm start.",
        75: "At 75%, reach counts begin to expose run-to-run difficulty even when conditional medians remain early.",
        80: "The 80% target is a useful operational reference: it separates Binary's reach reliability from Random.",
        85: "The 85% target is more demanding; success counts are as important as the conditional median.",
        90: "At 90%, many runs are censored by budget 80, so no universal query count is claimed.",
    }
    for section_number, target in enumerate([70, 75, 80, 85, 90], start=11):
        cells += section(
            section_number,
            f"Queries to {target}% accuracy",
            "First crossing is the first observed integer budget at which a run meets the target. Unsuccessful runs stay explicit rather than being assigned budget 81.",
            f"""
            targets = pd.read_csv(OUT1 / "queries_to_accuracy_target.csv")
            target_{target} = targets[(targets["boundary_definition"] == "B1") & (targets["target_accuracy_percent"] == {target})][[
                "quantile", "method_label", "successful_runs", "total_runs",
                "median_queries_successful_runs", "mean_queries_successful_runs", "not_reached_by_80"
            ]]
            display(target_{target})
            """,
            target_explanations[target],
        )
    cells += section(
        16,
        "Random-equivalent budget",
        "For each selected Binary budget, we find the first crossing of Binary's mean B1-q20 accuracy on the observed Random mean curve, using linear interpolation only between adjacent saved budgets.",
        """
        random_equivalent = pd.read_csv(OUT1 / "random_equivalent_budget.csv")
        display(random_equivalent[[
            "binary_budget", "binary_mean_accuracy", "random_equivalent_budget_display",
            "query_saving_display", "efficiency_multiplier_display", "status"
        ]].style.format({"binary_mean_accuracy": "{:.1%}"}))
        """,
        f"Binary at budget 30 is matched near Random budget {eq30['random_equivalent_budget']:.0f}; Binary at 40 is not matched by 80, so the latter remains a strict lower bound.",
    )
    cells += section(
        17,
        "Simulator-query savings",
        "Savings equal Random-equivalent budget minus Binary budget. Values above the observed horizon are shown only as lower bounds.",
        """
        display(Image(filename=str(OUT1 / "figures/07_query_savings.png")))
        """,
        f"The strongest exact result is about {eq30['query_saving']:.0f} saved calls for {eq30['binary_mean_accuracy']:.1%} mean B1-q20 accuracy; the budget-40 result is >{eq40['query_saving_lower_bound']:.0f}.",
    )
    cells += section(
        18,
        "Matched-run evidence and persistent crossings",
        "Aggregate savings are supplemented by paired run outcomes. Persistence requires the target to hold at the crossing and the next two stored integer budgets.",
        """
        matched = pd.read_csv(OUT1 / "matched_query_savings.csv")
        persistent = pd.read_csv(OUT1 / "persistent_queries_to_accuracy_target.csv")
        display(matched)
        display(persistent[(persistent["boundary_definition"] == "B1") & (persistent["quantile"] == 20) & (persistent["target_accuracy_percent"] == 80)][[
            "method_label", "successful_runs", "median_queries_successful_runs", "not_reached_by_80"
        ]])
        """,
        "Non-monotonic curves matter: first crossing is primary, while persistent crossing shows whether a threshold survives the next two observations.",
    )
    cells += section(
        19,
        "Keyhole discovery efficiency",
        "Discovery counts and enrichment use the actual candidate-pool prevalence for each run.",
        """
        discovery = pd.read_csv(OUT1 / "keyhole_discovery_by_budget.csv")
        display(discovery[discovery["budget"].isin([20, 30, 40, 60, 80])][[
            "budget", "method_label", "mean_keyhole_discovered", "mean_keyhole_enrichment"
        ]].style.format({"mean_keyhole_discovered": "{:.2f}", "mean_keyhole_enrichment": "{:.2f}x"}))
        display(Image(filename=str(OUT1 / "figures/08_keyhole_discovery.png")))
        """,
        "Binary finds substantially more positive cases than Random, but this secondary behavior is not substituted for held-out boundary accuracy.",
    )
    cells += section(
        20,
        "Saved predictive confidence and calibration",
        "Because Phase 7 stored held-out GPC probabilities, we can report confidence bands, correctness within those bands, Brier score, and fixed-bin reliability diagnostics.",
        """
        confidence = pd.read_csv(OUT1 / "predictive_confidence_summary.csv")
        display(confidence[(confidence["boundary_definition"] == "B1") & (confidence["budget"].isin([20, 40, 80]))][[
            "budget", "subset", "pooled_mean_confidence", "fraction_confidence_ge_080",
            "accuracy_confidence_ge_080", "fraction_confidence_ge_090",
            "accuracy_confidence_ge_090", "pooled_brier_score",
            "confidence_ece_10_equal_width_bins"
        ]].style.format({
            "pooled_mean_confidence": "{:.1%}", "fraction_confidence_ge_080": "{:.1%}",
            "accuracy_confidence_ge_080": "{:.1%}", "fraction_confidence_ge_090": "{:.1%}",
            "accuracy_confidence_ge_090": "{:.1%}", "pooled_brier_score": "{:.3f}",
            "confidence_ece_10_equal_width_bins": "{:.3f}"
        }))
        display(Image(filename=str(OUT1 / "figures/10_predictive_confidence_reliability.png")))
        """,
        f"At budget 40, {conf40['fraction_confidence_ge_080']:.1%} of B1-q20 predictions carry at least 80% model confidence and {conf40['accuracy_confidence_ge_080']:.1%} of that band is correct; this is model confidence, not physical-boundary certainty.",
    )
    cells += section(
        21,
        "B2/B3 robustness",
        "The same saved predictions are re-evaluated under local label disagreement (B2) and relative same/opposite class distance (B3). These metrics never enter acquisition.",
        """
        scorecard = pd.read_csv(OUT2 / "final_real_data_scorecard.csv")
        display(scorecard[[
            "method_label", "mean_B1_q20_error_aulc", "mean_B2_q20_error_aulc",
            "mean_B3_q20_error_aulc", "mean_balanced_accuracy_aulc"
        ]].style.format({column: "{:.4f}" for column in [
            "mean_B1_q20_error_aulc", "mean_B2_q20_error_aulc",
            "mean_B3_q20_error_aulc", "mean_balanced_accuracy_aulc"
        ]}))
        """,
        "Binary's q20 error AULC remains lower than Random under B1, B2, and B3, while Max-Depth remains strongest on global balanced accuracy.",
    )
    cells += section(
        22,
        "Machine-traceable headline results",
        "Every prose headline stores its source artifact and row filter so the thesis wording can be audited.",
        """
        headlines = pd.read_csv(OUT1 / "headline_results.csv")
        display(headlines[["claim_id", "statement", "source_artifact", "source_filter_or_metric"]])
        """,
        "The strongest statements are attached to rows, not copied from visual estimates.",
    )
    cells += section(
        23,
        "Scientific caveats",
        "The evaluation is repeated cross-validation over saved simulations. GPC probabilities are saved but not post-hoc calibrated. B1/B2/B3 are empirical diagnostics.",
        """
        caveats = pd.Series({
            "prospective simulator deployment": False,
            "independent physical campaigns": False,
            "universal threshold claim": False,
            "causal claim": False,
            "continuous-boundary certainty claim": False,
            "offline held-out active-learning benchmark": True,
        })
        display(caveats)
        """,
        "The retrospective benchmark is valid, but its evidence boundary must remain visible in every thesis claim.",
    )
    cells += section(
        24,
        "Phase 1 conclusion",
        "We now have budget snapshots, target crossings, matched censoring-aware evidence, Random-equivalent savings, discovery enrichment, and model-confidence diagnostics.",
        """
        print(f"Budget 40 B1-q20: Binary {snapshots[(snapshots.budget==40)&(snapshots.method_label=='Binary')].mean_q20_accuracy.iloc[0]:.1%}; Random {snapshots[(snapshots.budget==40)&(snapshots.method_label=='Random')].mean_q20_accuracy.iloc[0]:.1%}")
        print("Strongest exact saving: Binary budget 30 vs Random-equivalent budget 70 = 40 calls")
        print("Primary method remains Binary GPC + uncertainty-repulsion")
        print("No new simulator run was performed")
        """,
        "Week 8 has converted 'sample-efficient' into concrete, defensible query counts without reopening method selection.",
    )
    return nbf.v4.new_notebook(cells=cells, metadata=notebook_metadata())


def build_phase2() -> nbf.NotebookNode:
    cells: list[nbf.NotebookNode] = [
        md(
            """
            # Week 8 Phase 2 — final thesis evidence consolidation

            This concise teaching notebook assembles the source-backed thesis story. It reads final Week 8 tables and earlier authoritative artifacts; it does not rerun synthetic benchmarks, physical-response models, Phase 6, or Phase 7.
            """
        )
    ]
    common_setup = dedent(
        """
        from pathlib import Path
        import pandas as pd
        from IPython.display import Image, display
        ROOT = Path.cwd()
        OUT1 = ROOT / "outputs/week8_01_final_sample_efficiency"
        OUT2 = ROOT / "outputs/week8_02_thesis_consolidation"
        """
    ).strip()
    cells += section(
        1,
        "Thesis question",
        "The thesis asks whether an active learner can localize an empirical Keyhole transition with fewer expensive simulator queries than uninformed sampling.",
        common_setup + "\nprint('Final task: sample-efficient empirical manual-label boundary localization')",
        "The scientific object is a held-out manual-label boundary diagnostic, not a universal scalar threshold.",
    )
    cells += section(
        2,
        "Evidence chain",
        "The final story moves from synthetic method behavior through physical-response audits to matched real-data active learning and concrete Week 8 savings.",
        "display(Image(filename=str(OUT2 / 'final_thesis_figures/01_full_thesis_evidence_chain.png')))",
        "Each arrow is backed by saved artifacts; Week 8 adds quantification rather than a new method.",
    )
    cells += section(
        3,
        "Synthetic benchmark summary",
        "Branin, Hartmann4, and optional Ackley4 show that the best acquisition depends on geometry and metric.",
        """
        synthetic = pd.read_csv(OUT2 / "synthetic_to_real_summary.csv")
        display(synthetic[["benchmark", "seed_count", "best_q20_method", "best_q20_error", "best_sur_method", "best_sur_q20_error", "evidence_lesson"]])
        display(Image(filename=str(OUT2 / "final_thesis_figures/09_synthetic_to_real_summary.png")))
        """,
        "Complex uncertainty reduction is not automatically better; boundary-specific evaluation can reorder global winners.",
    )
    cells += section(
        4,
        "Week 7 real-data evidence chain",
        "Manual has_keyhole stayed ground truth; maximum depth became the robust continuous comparator; Phase 6 exposed a boundary/global trade-off; Phase 7 rejected two fixed Hybrids.",
        """
        phase6 = pd.read_csv(ROOT / "outputs/week7_06_real_data_boundary_active_level_set/phase6_formulation_scorecard.csv")
        phase7 = pd.read_csv(ROOT / "outputs/week7_07_final_boundary_hybrid_benchmark/phase7_final_decision.csv")
        display(phase6)
        display(phase7)
        """,
        "Real data favored direct Binary boundary acquisition while preserving a meaningful Max-Depth secondary role.",
    )
    cells += section(
        5,
        "Final primary method",
        "The frozen method maps P, VX, LS, and substrate temperature to P(Keyhole) and queries by uncertainty-repulsion.",
        "display(Image(filename=str(OUT2 / 'final_thesis_figures/10_final_method_schematic.png')))",
        "B1/B2/B3 are downstream evaluation only; no hidden label or response enters acquisition.",
    )
    cells += section(
        6,
        "Sample-efficiency headline table",
        "The final snapshot table expresses q20/q30 accuracy at intuitive budgets.",
        """
        snapshots = pd.read_csv(OUT1 / "budget_snapshot_b1.csv")
        display(snapshots[snapshots["budget"].isin([20,30,40,50,60,70,80])][[
            "budget", "method_label", "mean_q20_accuracy", "mean_q30_accuracy", "mean_balanced_accuracy"
        ]].style.format({"mean_q20_accuracy":"{:.1%}","mean_q30_accuracy":"{:.1%}","mean_balanced_accuracy":"{:.1%}"}))
        """,
        "Binary's boundary advantage and Max-Depth's global advantage are visible without combining them into an arbitrary weighted score.",
    )
    cells += section(
        7,
        "Queries and savings",
        "Target crossings retain success counts; Random-equivalent savings do not extrapolate beyond 80.",
        """
        targets = pd.read_csv(OUT1 / "queries_to_accuracy_target.csv")
        equivalent = pd.read_csv(OUT1 / "random_equivalent_budget.csv")
        display(targets[(targets["boundary_definition"]=="B1") & (targets["target_accuracy_percent"].isin([80,85]))][[
            "quantile", "target_accuracy_percent", "method_label", "successful_runs", "median_queries_successful_runs", "not_reached_by_80"
        ]])
        display(equivalent[["binary_budget", "binary_mean_accuracy", "random_equivalent_budget_display", "query_saving_display", "efficiency_multiplier_display"]])
        """,
        "The exact headline is 40 saved calls at Binary budget 30; budget-40 performance yields a strict >40 saving lower bound.",
    )
    cells += section(
        8,
        "Boundary–global trade-off",
        "B1-q20 accuracy AULC is plotted against balanced-accuracy AULC rather than collapsed into one post-hoc score.",
        "display(Image(filename=str(OUT2 / 'final_thesis_figures/07_boundary_global_tradeoff.png')))",
        "Binary is preferred for the thesis boundary objective; Max-Depth is stronger for global classification.",
    )
    cells += section(
        9,
        "Max-Depth secondary role",
        "The final scorecard keeps its physical and predictive contribution explicit.",
        """
        scorecard = pd.read_csv(OUT2 / "final_real_data_scorecard.csv")
        display(scorecard[["method_label", "mean_B1_q20_accuracy_aulc", "mean_balanced_accuracy_aulc", "mean_sensitivity_aulc", "mean_keyhole_discovered_budget30", "primary_role"]])
        """,
        "Max-Depth is not discarded; it simply does not replace the direct Binary boundary acquisition.",
    )
    cells += section(
        10,
        "Negative Hybrid result",
        "Gate20 and equal-rank fusion did not satisfy the preregistered robust rule and added local fitting overhead.",
        """
        outcome = pd.read_csv(ROOT / "outputs/week7_07_final_boundary_hybrid_benchmark/phase7_preregistered_rule_outcome.csv")
        runtime = pd.read_csv(ROOT / "outputs/week7_07_final_boundary_hybrid_benchmark/phase7_runtime_comparison.csv")
        display(outcome)
        display(runtime[runtime["method"].str.contains("hybrid|binary_uncertainty")][["method", "mean_runtime_seconds", "relative_overhead_vs_binary_champion"]])
        """,
        "The defensible conclusion is narrow: the two tested Hybrids failed to improve the frozen Binary method.",
    )
    cells += section(
        11,
        "Final claim ledger",
        "Supported claims, diagnostics, and prohibited overclaims are stored row by row with exact evidence paths.",
        """
        ledger = pd.read_csv(OUT2 / "final_thesis_claim_ledger.csv")
        display(ledger.groupby(["category", "status"]).size().rename("claim_count"))
        display(ledger[["claim_id", "category", "claim", "status", "allowed_wording", "forbidden_overclaim"]])
        """,
        "The ledger prevents strong results from silently turning into universal, causal, or prospective claims.",
    )
    cells += section(
        12,
        "Final thesis figures and tables",
        "Only ten distinct final figures and six compact final tables are retained.",
        """
        figures = sorted((OUT2 / "final_thesis_figures").glob("*.png"))
        tables = sorted((OUT2 / "final_thesis_tables").glob("*.csv"))
        print("final figures:", len(figures))
        print("final CSV tables:", len(tables))
        display(pd.DataFrame({"figure": [path.name for path in figures]}))
        display(pd.DataFrame({"table": [path.name for path in tables]}))
        """,
        "The final set is deliberately compact enough to map into Results and Discussion without a figure zoo.",
    )
    cells += section(
        13,
        "Limitations",
        "No genuinely new simulator evaluation was available. The 20 runs reuse 405 simulations in four repeated five-fold splits. Probability calibration is diagnostic.",
        """
        limitations = ledger[ledger["category"] == "CLAIMS WE MUST NOT MAKE"][
            ["claim_id", "claim", "allowed_wording", "forbidden_overclaim", "caveat"]
        ]
        display(limitations)
        """,
        "The evidence supports retrospective sample efficiency, not live closed-loop deployment or certainty about a continuous physical surface.",
    )
    cells += section(
        14,
        "Final conclusion",
        "Week 8 closes the experimental program and hands a stable evidence chain to thesis writing.",
        """
        print("FINAL PRIMARY: Binary GPC + binary_uncertainty_repulsion")
        print("SECONDARY: Max-Depth straddle / physical comparator")
        print("STRONGEST EXACT SAVING: 40 simulator calls for the 79.7% mean B1-q20 level")
        print("BOUNDARY-40 LOWER BOUND: Random does not match Binary by 80 (>40 calls saved)")
        print("EVIDENCE MODE: offline retrospective; no prospective simulator run")
        """,
        "The thesis can now make a concrete sample-efficiency claim while retaining honest limits on transfer, calibration, causality, and prospective validation.",
    )
    return nbf.v4.new_notebook(cells=cells, metadata=notebook_metadata())


def main() -> None:
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    phase1 = build_phase1()
    phase2 = build_phase2()
    nbf.write(phase1, NB1)
    nbf.write(phase2, NB2)
    print(f"wrote {NB1} with {len(phase1.cells)} cells")
    print(f"wrote {NB2} with {len(phase2.cells)} cells")


if __name__ == "__main__":
    main()
