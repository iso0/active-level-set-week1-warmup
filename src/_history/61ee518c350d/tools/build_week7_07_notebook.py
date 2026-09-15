"""Build and optionally execute the Week 7 Phase 7 teaching notebook.

The notebook reads the saved Phase 6/7 artifacts.  It does not refit a model or
alter the preregistered benchmark; its purpose is to expose the evidence chain
in small, auditable cells.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import nbformat as nbf
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week7_07_final_boundary_hybrid_benchmark"
NOTEBOOK = ROOT / "notebooks" / "week_07" / "07_final_boundary_hybrid_benchmark.ipynb"


@dataclass(frozen=True)
class Section:
    number: int
    title: str
    what: str
    why: str
    allowed: str
    leakage: str
    thesis: str
    misleading: str
    artifacts: tuple[str, ...]
    figures: tuple[int, ...]
    happened: str
    robust: str
    max_depth: str
    uncertain: str
    forbidden: str
    calculation: str = ""


def markdown(source: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(source.strip())


def code(source: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(source.strip())


def section_markdown(section: Section) -> str:
    return f"""## {section.number}. {section.title}

**What are we doing?** {section.what}

**Why?** {section.why}

**What information is allowed?** {section.allowed}

**What would constitute leakage?** {section.leakage}

**How does this answer the thesis question?** {section.thesis}

**What would be a misleading interpretation?** {section.misleading}"""


def section_code(section: Section) -> str:
    lines: list[str] = []
    if section.number == 1:
        lines.append(
            r'''from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd
from IPython.display import Image, Markdown, display

ROOT = Path.cwd()
OUT = ROOT / "outputs" / "week7_07_final_boundary_hybrid_benchmark"
PHASE6_OUT = ROOT / "outputs" / "week7_06_real_data_boundary_active_level_set"
FIGURES = OUT / "figures"

def artifact_path(name):
    candidates = [OUT / name, PHASE6_OUT / name]
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]

def show_artifact(name, rows=10):
    path = artifact_path(name)
    if not path.is_file():
        print(f"pending artifact: {path.relative_to(ROOT)}")
        return None
    print(f"{path.relative_to(ROOT)}  ({path.stat().st_size:,} bytes)")
    if path.suffix == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
        display(pd.Series(value, dtype="object") if isinstance(value, dict) else value)
        return value
    if path.suffix == ".md":
        display(Markdown(path.read_text(encoding="utf-8")[:5000]))
        return path
    frame = pd.read_csv(path, nrows=rows, low_memory=False)
    display(frame.iloc[:, : min(14, len(frame.columns))])
    if len(frame.columns) > 14:
        print(f"preview shows 14 of {len(frame.columns)} columns")
    return frame

def show_figure(number):
    manifest = pd.read_csv(OUT / "figure_manifest.csv")
    row = manifest.loc[pd.to_numeric(manifest["figure_number"]).eq(number)].iloc[0]
    path = OUT / row["relative_path"]
    print(f"Figure {number}: {row['title']} — {path.relative_to(ROOT)}")
    display(Image(filename=str(path)))

def explain(*, happened, robust, max_depth, uncertain, forbidden):
    display(Markdown(
        f"**What happened?** {happened}\n\n"
        f"**Is it robust across boundary metrics?** {robust}\n\n"
        f"**Does Max-Depth side information help?** {max_depth}\n\n"
        f"**What is still uncertain?** {uncertain}\n\n"
        f"**What claim are we NOT allowed to make?** {forbidden}"
    ))'''
        )
    for artifact in section.artifacts:
        lines.append(f"show_artifact({artifact!r})")
    if section.calculation:
        lines.append(section.calculation.strip())
    for figure in section.figures:
        lines.append(f"show_figure({figure})")
    lines.append(
        "explain(\n"
        f"    happened={section.happened!r},\n"
        f"    robust={section.robust!r},\n"
        f"    max_depth={section.max_depth!r},\n"
        f"    uncertain={section.uncertain!r},\n"
        f"    forbidden={section.forbidden!r},\n"
        ")"
    )
    return "\n\n".join(lines)


COMMON_ALLOWED = "Only saved artifacts from the fixed 405-row population and the exactly matched Phase 6/7 runs are read; nothing is selected from the held-out result."
COMMON_LEAKAGE = "Using held-out labels, B1/B2/B3 memberships, or unqueried maximum depth during acquisition, or tuning a method after seeing Phase 7 outcomes."
COMMON_FORBIDDEN = "We cannot claim causality, a universal physical Keyhole threshold, independent physical replication, or performance outside the sampled support."


def make_sections() -> list[Section]:
    s = Section
    return [
        s(1, "Phase 7 thesis question", "Restate the fixed question and inspect the top-level summary.", "The comparison needs a fixed target, cost unit, and decision hierarchy.", "Saved Phase 7 summary metadata and the manual experiment-level has_keyhole definition.", COMMON_LEAKAGE, "It asks whether same-query Max-Depth side information makes manual Keyhole boundary learning more sample-efficient.", "Treating maximum depth as a replacement ground-truth label.", ("summary.json",), (), "The completed benchmark retained manual has_keyhole as truth and applied the preregistered decision tree.", "Robustness is evaluated later under B1, B2, and B3 rather than assumed here.", "It is auxiliary acquisition information only.", "Metric-specific performance and external generalization still require the later evidence.", COMMON_FORBIDDEN),
        s(2, "Phase 6 parent and publication provenance", "Verify the exact published parent before interpreting Phase 7.", "Phase 7 is meaningful only as a matched extension of a frozen benchmark.", "Git publication audit and saved reuse hashes.", "Changing the Phase 6 parent or silently replacing its artifacts.", "This makes the comparison reproducible and prevents post-result benchmark drift.", "Calling a hash check scientific validation by itself.", ("phase6_publication_audit.json",), (2,), "Phase 6 is pinned at commit 5734de6f… and the saved run identities reconcile.", "The provenance statement is exact, not metric-dependent.", "No side-information result is inferred from provenance alone.", "A reproducible parent can still encode modelling limitations.", COMMON_FORBIDDEN),
        s(3, "Dataset revision check", "Compare the live/saved Hugging Face revision with the Phase 6 authority.", "A changed physical dataset would invalidate exact reuse.", "Revision identifiers and preflight metadata only.", "Proceeding after an unexplained revision change.", "It isolates algorithmic differences from data drift.", "Assuming an unchanged revision proves every physical measurement correct.", ("hf_revision_audit.json", "phase7_preflight.json"), (), "The Phase 7 revision equals the Phase 6 revision b6dc254a… .", "This guardrail applies to every boundary definition.", "It neither helps nor hurts a method; it fixes the evidence base.", "Repository identity does not resolve measurement uncertainty.", COMMON_FORBIDDEN),
        s(4, "Phase 6 population reuse", "Reconcile the exact 405 rows and 73/332 labels.", "Population drift would make method AULCs incomparable.", "The published Phase 6 primary_common_population table.", "Dropping difficult rows or rebalancing labels after seeing results.", "It fixes the real-data domain on which sample efficiency is measured.", "Treating this convenience sample as the full industrial process distribution.", ("primary_common_population.csv",), (1,), "The primary population remains 405 simulations: 73 Keyhole and 332 non-Keyhole.", "All B1/B2/B3 definitions use these same rows.", "Both Hybrid arms receive maximum depth only after querying a row.", "Class prevalence differs strongly by partition.", COMMON_FORBIDDEN, "population = pd.read_csv(PHASE6_OUT / 'primary_common_population.csv', low_memory=False)\ndisplay(population['has_keyhole'].astype(str).str.lower().isin(['true','1']).value_counts().rename(index={True:'Keyhole',False:'non-Keyhole'}))"),
        s(5, "Exact split and warm-start reuse audit", "Audit outer folds, candidate pools, permutations, warm starts, and budgets.", "Matched active-learning comparisons require identical experimental realizations.", COMMON_ALLOWED, "Giving one method an easier fold or a different initial query set.", "It makes AULC differences attributable to acquisition logic rather than run construction.", "Calling matched repeated CV twenty independent physical experiments.", ("phase6_run_reuse_audit.csv",), (2,), "All 20 primary Phase 6 outer runs and warm starts hash-match exactly.", "The same audit supports every B1/B2/B3 comparison.", "Side information changes only post-warm-start selection.", "Repeated folds reuse simulations and therefore share physical evidence.", COMMON_FORBIDDEN),
        s(6, "Phase 6 reproduction smoke check", "Numerically replay the published Binary and Max-Depth champions before Hybrid science.", "A new engine must reproduce its parent before extending it.", "Saved Phase 6 checkpoints and the reduced deterministic replay.", "Accepting changed baseline behaviour and attributing it to Hybrid design.", "It establishes continuity with the benchmark that motivated Phase 7.", "Interpreting numerical equality as proof that the surrogate is physically true.", ("phase6_reproduction_check.csv", "phase6_baseline_replay_reconciliation.csv"), (18,), "All reproduction checks pass; the largest numerical difference is about 8.24e-13.", "The replay covers shared predictions used by all boundary evaluations.", "No new advantage is claimed; this is a continuity check.", "Floating-point agreement does not test scientific adequacy.", COMMON_FORBIDDEN),
        s(7, "Why boundary-metric robustness matters", "Inspect the three model-independent boundary definitions before ranking methods.", "Phase 6's boundary conclusion should not depend on one convenient diagnostic.", "P, VX, LS, ST and manual labels for evaluation only.", "Letting a true boundary membership enter acquisition.", "It tests whether the central boundary claim survives alternative empirical notions of transition proximity.", "Calling an empirical neighborhood diagnostic the unique physical boundary.", ("boundary_metric_definitions.csv",), (3, 4, 5), "B1, B2, and B3 emphasize related but non-identical neighborhoods.", "Robustness must be demonstrated by agreement in method conclusions, not by identical memberships.", "Max-Depth is absent from all three definitions.", "Finite, uneven sampling limits every empirical boundary proxy.", COMMON_FORBIDDEN),
        s(8, "B1 definition", "Expose nearest opposite-label distance and its distribution.", "B1 directly locates rows near an observed label transition.", "Standardized process inputs and manual labels, evaluation-only.", COMMON_LEAKAGE, "It is the original Phase 6-style geometric boundary diagnostic.", "Equating a small sampled opposite-label distance with a continuous physical interface.", ("boundary_metric_definitions.csv", "boundary_metric_reference.csv"), (3,), "Smaller B1 values mark rows close to the nearest observed opposite label.", "B1 is one of three diagnostics and is not privileged after results.", "Maximum depth is not used to construct B1.", "Sparse regions can make nearest-neighbor distances large for sampling reasons.", COMMON_FORBIDDEN),
        s(9, "B2 definition", "Expose local k=5 label disagreement; retain k=10 as secondary sensitivity.", "A local mixed-label neighborhood captures boundary ambiguity differently from one nearest pair.", "Standardized process inputs and manual labels, evaluation-only.", COMMON_LEAKAGE, "It checks whether Binary's advantage survives a local-disagreement view.", "Treating local label mixing as simulator noise without evidence.", ("boundary_metric_definitions.csv", "boundary_metric_reference.csv"), (4,), "Higher k=5 disagreement marks locally mixed manual labels.", "It is deliberately different from B1/B3; agreement is evaluated rather than assumed.", "Maximum depth is absent from B2.", "Results may change with k; k=10 remains a declared secondary check.", COMMON_FORBIDDEN),
        s(10, "B3 definition", "Expose the relative opposite- versus same-class distance ratio.", "B3 normalizes opposite-class proximity by local same-class spacing.", "Standardized process inputs and manual labels, evaluation-only.", COMMON_LEAKAGE, "It adds a density-relative view of boundary proximity.", "Interpreting the ratio as a physical nondimensional law.", ("boundary_metric_definitions.csv", "boundary_metric_reference.csv"), (5,), "Lower B3 ratios identify rows whose opposite class is close relative to their own class.", "It overlaps with B1 but is not interchangeable with it.", "Maximum depth is absent from B3.", "Local density and duplicate geometry can affect ratios.", COMMON_FORBIDDEN),
        s(11, "Boundary-metric overlap", "Compare rank correlations and exact q20/q30 set overlap off the diagonal.", "The thesis needs both diversity and enough commonality for a meaningful robustness test.", "Full-population evaluation-only B1/B2/B3 values.", COMMON_LEAKAGE, "It quantifies whether conclusions span genuinely different boundary views.", "Using diagonal Jaccard=1 as evidence of cross-metric agreement.", ("boundary_metric_correlations.csv", "boundary_subset_overlap.csv"), (6, 7, 8, 9, 10), "Off-diagonal Spearman correlations span about 0.363–0.714; q20 Jaccard spans about 0.514–0.620.", "The metrics overlap but are demonstrably non-interchangeable.", "No maximum-depth response enters this agreement calculation.", "All three are induced by the same finite labelled sample.", COMMON_FORBIDDEN),
        s(12, "Consensus boundary subsets", "Inspect rows selected by at least two of B1/B2/B3.", "Consensus is a useful secondary descriptive summary without replacing primary metrics.", "Evaluation-only membership tables.", COMMON_LEAKAGE, "It checks whether conclusions also look sensible on shared transition rows.", "Substituting consensus for the preregistered B1/B2/B3 hierarchy.", ("boundary_consensus_membership.csv",), (13,), "Consensus subsets retain rows endorsed by at least two definitions and remain secondary.", "Consensus agreement supports, but cannot manufacture, robustness across the three primary diagnostics.", "Maximum depth is not used in membership.", "Consensus can hide definition-specific failure modes.", COMMON_FORBIDDEN),
        s(13, "Scaling sensitivity", "Compare primary z-score geometry with median/IQR scaling.", "Distance-based boundary metrics should not hinge on one feature scaling convention.", "Process inputs and manual labels, evaluation-only.", COMMON_LEAKAGE, "It stress-tests B1/B3 membership stability.", "Retuning scaling after observing the method winner.", ("boundary_scaling_sensitivity.csv",), (14,), "B1/B3 q20/q30 memberships show substantial but not perfect scaling stability.", "The main Binary-versus-Max-Depth direction is evaluated under the preregistered primary scaling.", "This is a boundary-definition robustness check, not acquisition side information.", "Different physically motivated scalings could still be investigated later.", COMMON_FORBIDDEN),
        s(14, "Predeclared Phase 7 methods", "Display the fixed baselines, two champions, and exactly two new Hybrids.", "Method proliferation after observing results would invalidate comparison.", "Preregistered method definitions and fixed Phase 6 champions.", "Adding or tuning acquisitions after full-result inspection.", "It restricts the final methodological experiment to the Phase 6-motivated hypothesis.", "Calling a fixed comparison an exhaustive search over all hybrids.", ("phase7_method_definitions.csv",), (15,), "Only Hybrid Gate and Hybrid Equal-Rank Fusion are new; the baselines are frozen.", "All methods are scored under B1/B2/B3.", "The Hybrids alone use queried Max-Depth to choose future points; their predictor stays Binary GPC.", "Other principled hybridizations may exist but were outside scope.", COMMON_FORBIDDEN),
        s(15, "Hybrid Gate derivation", "Trace Binary priority, the fixed ceil(20%) gate, then Max-Depth straddle.", "This operationalizes 'localize with Binary, refine with physical side information'.", "Only queried labels/depths and candidate features at the current step.", COMMON_LEAKAGE, "It tests whether physical depth can improve sample allocation without changing the regime predictor.", "Calling the 20% gate data-adaptively optimal.", ("phase7_method_definitions.csv", "phase7_preregistered_decision_rule.json"), (16,), "Gate applies the exact Binary priority, retains a fixed top 20%, and selects by queried-only depth straddle.", "It is evaluated identically under B1/B2/B3.", "Yes, but only inside the gate and only after depth is revealed by prior queries.", "A fixed gate can exclude useful candidates outside its shortlist.", COMMON_FORBIDDEN),
        s(16, "Hybrid Rank Fusion derivation", "Trace the fixed equal-percentile fusion of Binary and depth priorities.", "A soft fusion tests side information without a hard gate.", "Only queried labels/depths and candidate features at the current step.", COMMON_LEAKAGE, "It asks whether globally blending complementary rankings beats Binary alone.", "Calling the 0.5/0.5 weights optimized or learned.", ("phase7_method_definitions.csv", "phase7_preregistered_decision_rule.json"), (17,), "Rank Fusion averages two fixed percentile ranks with weights 0.5 and 0.5.", "The same fusion is tested without metric-specific tuning.", "Yes, through the depth-straddle rank; final probabilities still come from Binary GPC.", "Equal weighting may dilute the stronger signal.", COMMON_FORBIDDEN),
        s(17, "Preregistered decision rule", "Read the hash-locked A/B/C/D success rule before its outcomes.", "A mechanical final decision prevents narrative selection of a winner.", "The preregistration JSON and its SHA-256 sidecar.", "Editing the rule or weights after smoke/full results.", "It maps boundary, global accuracy, and random-baseline evidence into a reproducible thesis conclusion.", "Treating descriptive bootstrap intervals as a new post-hoc rule.", ("phase7_preregistered_decision_rule.json", "phase7_preregistered_decision_rule.sha256"), (), "The rule was hashed before smoke/full results and requires robust boundary gains, no material BA loss, and improvement over random.", "Conditions A/B explicitly require support under at least two of B1/B2/B3.", "It may help only if the complete rule is satisfied.", "A preregistered rule is a decision aid, not a theorem.", COMMON_FORBIDDEN),
        s(18, "Fairness and leakage audit", "Inspect per-run information-flow and accounting invariants.", "Hybrid comparisons are invalid if unqueried outcomes or test data enter selection.", "Saved audit flags, query histories, and fixed run manifests.", "Any held-out label/depth, B1/B2/B3 membership, or future query outcome entering acquisition.", "It verifies that sample-efficiency differences use the same simulator budget.", "Assuming an audit flag alone catches every possible implementation error.", ("phase7_fairness_audit.csv",), (), "All declared fairness, primary-predictor, gate-size, fusion-weight, and leakage invariants pass.", "The barriers apply uniformly to every evaluation metric.", "It is available only in the allowed queried-only channel.", "Audits establish implementation compliance, not causal validity.", COMMON_FORBIDDEN),
        s(19, "Smoke run", "Inspect the reduced two-run, budget-30 execution and its independent validator.", "A cheap end-to-end check should fail before the expensive full benchmark if schemas or leakage barriers break.", "Smoke-only artifacts explicitly marked non-scientific.", "Using smoke rankings as Phase 7 evidence or tuning on smoke outcomes.", "It validates execution mechanics while preserving the full benchmark as the scientific test.", "Reporting smoke performance as a thesis conclusion.", ("smoke/summary.json", "smoke/validation_results.csv", "smoke/requirement_checklist.csv"), (), "The reduced run passed 31/31 validations and 14/14 smoke requirements and was labelled non-scientific.", "It exercised all three boundary metrics but did not estimate robust performance.", "Both Hybrid mechanisms executed with queried-only depth.", "Two runs cannot characterize method performance.", COMMON_FORBIDDEN),
        s(20, "Full Hybrid active benchmark", "Inspect the full run manifest, common budget, and method scorecard.", "The scientific comparison requires all 20 matched outer runs through budget 80.", COMMON_ALLOWED, COMMON_LEAKAGE, "This is the final matched active-learning test of the Hybrid hypothesis.", "Reading a single final-budget point while ignoring the learning trajectory.", ("hybrid_run_manifest.csv", "phase7_method_scorecard.csv", "runtime_summary.json"), (), "The full benchmark completed 20 matched runs for all fixed arms through total budget 80 with no scientific reductions.", "Every run carries B1/B2/B3 held-out evaluation.", "Only the two Hybrid acquisitions consume queried depth side information.", "Repeated CV shares simulations across runs.", COMMON_FORBIDDEN),
        s(21, "B1 q20 learning curves", "Compare held-out B1 q20 error over query budget.", "q20 focuses on the most boundary-like fifth under the original geometric definition.", COMMON_ALLOWED, COMMON_LEAKAGE, "Lower trajectory AULC means fewer simulator queries are needed to localize the manual boundary.", "Selecting a winner from a visually convenient budget.", ("phase7_method_scorecard.csv",), (19,), "Mean B1 q20 AULC is about 0.1862 for Binary, 0.1943 for Gate, and 0.1872 for Rank Fusion.", "This section is B1-specific; B2/B3 follow independently.", "It does not improve on Binary here; Fusion is close but slightly worse.", "Run-level variation remains visible and intervals are assessed later.", COMMON_FORBIDDEN),
        s(22, "B1 q30 learning curves", "Repeat the B1 comparison on the broader q30 subset.", "A result should not depend only on the narrowest declared region.", COMMON_ALLOWED, COMMON_LEAKAGE, "It checks localization efficiency on a wider empirical transition neighborhood.", "Treating q30 as an independently collected dataset.", ("phase7_method_scorecard.csv",), (20,), "Binary has the lowest mean B1 q30 AULC; both Hybrids are higher.", "B1 agrees at q20 and q30, but cross-definition robustness still needs B2/B3.", "No Hybrid gain appears under B1 q30.", "The q20/q30 subsets are nested and statistically dependent.", COMMON_FORBIDDEN),
        s(23, "B2 q20/q30", "Evaluate the same trajectories with local label disagreement.", "B2 tests whether the boundary conclusion survives a different neighborhood notion.", COMMON_ALLOWED, COMMON_LEAKAGE, "It directly addresses metric robustness of sample-efficient boundary localization.", "Letting B2 membership affect which candidate is queried.", ("phase7_method_scorecard.csv",), (21, 22), "Binary outperforms Gate and Rank Fusion on mean B2 q20 and q30 AULC.", "Yes: B2 reinforces rather than reverses the B1 conclusion.", "Side information does not improve localization and Gate is reliably worse in the paired q20 comparison.", "B2 depends on the declared k=5 neighborhood.", COMMON_FORBIDDEN),
        s(24, "B3 q20/q30", "Evaluate the same trajectories with the relative class-distance ratio.", "B3 adds a density-relative boundary diagnostic.", COMMON_ALLOWED, COMMON_LEAKAGE, "Agreement across B1/B2/B3 strengthens the final boundary-method choice.", "Changing B3 after seeing which method wins.", ("phase7_method_scorecard.csv",), (23, 24), "Binary again has lower mean q20/q30 error AULC than Gate; Fusion is close but not better.", "Yes: the direction now agrees across all three primary definitions.", "It fails to create a robust gain and Gate is reliably worse for B3 q20.", "Empirical distances remain sample-density dependent.", COMMON_FORBIDDEN),
        s(25, "Consensus boundary results", "Inspect learning curves for at-least-two-of-three membership.", "Consensus provides an intuitive secondary summary of shared boundary rows.", COMMON_ALLOWED, COMMON_LEAKAGE, "It checks whether the metric-specific pattern persists on jointly endorsed transition cases.", "Replacing the preregistered multi-metric rule with consensus after the fact.", ("phase7_final_budget_summary.csv",), (25, 26), "Consensus trajectories do not reveal a Hybrid advantage over Binary.", "They are consistent with the separate B1/B2/B3 results but remain secondary.", "No clear benefit appears from depth side information.", "Consensus can suppress metric-specific structure.", COMMON_FORBIDDEN),
        s(26, "Balanced-accuracy curves", "Compare global held-out regime classification over budget.", "Boundary localization must be read alongside overall predictive usefulness.", COMMON_ALLOWED, COMMON_LEAKAGE, "It exposes the Phase 6 trade-off between Binary boundary focus and Max-Depth global classification.", "Using accuracy alone to answer a boundary-estimation thesis question.", ("phase7_method_scorecard.csv",), (27,), "Max-Depth has the highest mean BA AULC (~0.9432); Binary is ~0.9171, Fusion ~0.9076, and Gate ~0.8983.", "BA is global rather than boundary-definition-specific.", "Fusion stays within the preregistered 0.01 material-loss tolerance; Gate does not.", "BA can conceal class- and boundary-specific behavior.", COMMON_FORBIDDEN),
        s(27, "Sensitivity and calibration curves", "Inspect held-out Keyhole sensitivity and probability calibration.", "A boundary method should not be judged by one aggregate score.", COMMON_ALLOWED, COMMON_LEAKAGE, "It clarifies which aspects of predictive performance Max-Depth side information affects.", "Calling calibration or sensitivity a direct boundary metric.", ("phase7_final_budget_summary.csv",), (28, 29), "The richer side-information arms can alter sensitivity/calibration, but neither Hybrid dominates Binary across the full hierarchy.", "These diagnostics are not B1/B2/B3-specific and therefore supplement rather than replace boundary results.", "It may change discovery and probability behavior without improving boundary AULC.", "Small positive subgroups and repeated folds limit precision.", COMMON_FORBIDDEN),
        s(28, "Queries to tolerance", "Measure when each run first reaches q20 error ≤0.20 and BA ≥0.90.", "AULC averages trajectories; tolerance times provide an operational sample-count view.", COMMON_ALLOWED, COMMON_LEAKAGE, "It translates statistical curves into simulator-query counts.", "Imputing success after budget 80 for runs that never reach a tolerance.", ("phase7_queries_to_tolerance.csv",), (33,), "Binary reaches each q20 tolerance in 18–19 of 20 runs with a conditional median of 16 queries; Hybrid medians are later.", "The pattern appears under B1, B2, and B3.", "No faster robust boundary attainment is observed.", "Medians condition on successful runs and must be paired with reach counts.", COMMON_FORBIDDEN),
        s(29, "Paired bootstrap comparisons", "Inspect 5,000 matched-run bootstrap intervals for Hybrid minus Binary AULCs.", "Matched differences respect the reused outer-run design better than unpaired bars.", "Run-level saved AULCs and deterministic bootstrap seeds.", "Treating repeated-CV resamples as independent physical replications or changing interval rules after results.", "It quantifies uncertainty around the exact comparisons in the decision rule.", "Interpreting descriptive intervals as universal population confidence intervals.", ("phase7_paired_bootstrap_intervals.csv",), (32,), "Gate is reliably worse than Binary on B2/B3 q20; Fusion's small positive q20 differences have intervals crossing zero.", "No Hybrid has negative q20 intervals under at least two definitions, so condition A fails.", "The side information does not yield a reliable localization gain.", "Twenty matched folds still reuse the same 405 simulations.", COMMON_FORBIDDEN),
        s(30, "Pareto frontier", "Plot boundary-error AULC against balanced-accuracy AULC without scalar weighting.", "The Phase 6 trade-off should remain visible rather than hidden in an arbitrary composite score.", COMMON_ALLOWED, COMMON_LEAKAGE, "It asks whether a Hybrid expands the attainable boundary/global-performance frontier.", "Choosing weights post hoc to place a preferred method first.", ("phase7_pareto_summary.csv",), (34, 35), "Binary and Max-Depth occupy the q20/q30 frontiers; both Hybrids are dominated.", "The same conclusion holds for B1/B2/B3 panels.", "It does not add a new Pareto-efficient option.", "The frontier is empirical and limited to the fixed method set.", COMMON_FORBIDDEN),
        s(31, "Query-behaviour analysis", "Join true boundary membership only after selection and compare query sets.", "Mechanistic interpretation requires knowing where methods sampled without contaminating acquisition.", "Saved query histories joined post hoc to evaluation-only memberships.", COMMON_LEAKAGE, "It explains how algorithmic priorities translate into sampled regions.", "Inferring that boundary querying alone caused final performance.", ("phase7_query_boundary_behavior.csv", "phase7_query_overlap_summary.csv"), (36, 38), "Gate and Binary share about 0.63 of their budget-80 query sets, while Gate and Fusion share about 0.72.", "Boundary-query fractions are reported for each B1/B2/B3 q20 set.", "It changes selections substantially but not in a way that improves robust boundary AULC.", "Overlap does not reveal query order or causal contribution.", COMMON_FORBIDDEN),
        s(32, "Early Keyhole discovery", "Count queried positive cases as budget grows.", "Max-Depth side information may help discover Keyhole cases even if it does not improve boundary localization.", "Only outcomes of already queried simulations.", "Peeking at unqueried labels to count or select positives.", "It separates discovery behavior from held-out level-set accuracy.", "Equating more positives queried with a better boundary estimator.", ("phase7_keyhole_discovery_summary.csv",), (37,), "At budget 30 Gate discovers fewer Keyhole cases on average than Binary; Max-Depth shows the strongest global BA behavior.", "Discovery is not a B1/B2/B3 boundary metric.", "It can help prevalence-seeking behavior, but not the preregistered Hybrid boundary objective here.", "Discovery counts depend on candidate-pool prevalence.", COMMON_FORBIDDEN),
        s(33, "Transient and persistent results", "Compare final held-out sensitivity for the two declared Keyhole timing subgroups.", "Experiment-level labels do not require persistence, so subgroup behavior is scientifically relevant.", "Held-out manual labels and predeclared descriptive timing subgroups.", "Using subgroup outcomes to tune acquisition.", "It probes whether an apparent gain is confined to one type of positive experiment.", "Calling a saved-frame timing proxy continuous morphology at an unsaved monitor timestep.", ("phase7_transient_persistent_summary.csv",), (39, 40), "Subgroup sensitivities vary by method, but no Hybrid establishes a general boundary advantage.", "These are descriptive subgroup checks, not alternative boundary definitions.", "Side information can redistribute sensitivity without satisfying the robust rule.", "Small subgroup counts make estimates unstable.", COMMON_FORBIDDEN),
        s(34, "Partition-specific held-out results", "Break final held-out performance down by new, old-local, and old-remote subsets.", "Strong prevalence and process-space differences could hide a partition-driven effect.", "Partition labels inside the same untouched outer test folds.", "Training a primary rule on the subgroup test outcomes.", "It checks whether conclusions are obviously driven by one data partition.", "Treating secondary subgroup means as a separate randomized domain-transfer study.", ("phase7_partition_specific_summary.csv",), (41,), "Performance differs substantially by partition; Max-Depth is strongest in several subgroup means, while Hybrids do not show a uniform gain.", "The B1/B2/B3 conclusion remains based on combined primary held-out evaluation.", "It can affect subgroup accuracy but not robustly improve the main boundary hierarchy.", "Old-remote has very few Keyhole cases and some fold metrics are undefined.", COMMON_FORBIDDEN),
        s(35, "Representative trajectories", "Display algorithmically selected median, strongest-improvement, and strongest-deterioration runs.", "Individual paths make mean AULCs tangible without hand-picking attractive examples.", "Run selection rules saved before plotting and matched trajectories.", "Choosing a run visually or changing the selector after inspection.", "It shows how Hybrid and Binary can diverge despite shared starts and budgets.", "Generalizing from one representative run.", ("phase7_representative_runs.csv",), (43, 44, 45), "Gate sometimes improves and sometimes deteriorates relative to Binary; the median case is selected mechanically.", "The examples illustrate variability, while robustness comes from all 20 runs and all metrics.", "Side information changes query paths but not consistently in the beneficial direction.", "A trajectory cannot identify which individual query caused a later change.", COMMON_FORBIDDEN),
        s(36, "Supported boundary surfaces", "Compare Binary-GPC probability surfaces after Binary versus Gate acquisitions at a fixed 4D context.", "A level-set thesis benefits from a visual boundary comparison constrained to sampled support.", "Fitted Binary predictors and a support mask; unsupported cells stay blank.", "Displaying or interpreting extrapolated cells as observed physical truth.", "It visualizes how acquisition changes the estimated P(Keyhole)=0.5 contour.", "Calling a 2D slice the complete four-dimensional physical boundary.", ("phase7_boundary_surface_comparison.csv",), (46, 47, 48), "Binary and Gate surfaces are similar over supported regions but show local contour shifts from different query sets.", "The visual comparison spans P–VX, P–LS, and VX–LS slices, not the three empirical metrics.", "It changes the fitted surface locally without improving the robust held-out hierarchy.", "Fixed-context slices suppress the remaining dimensions and depend on support masking.", COMMON_FORBIDDEN),
        s(37, "Hybrid failure analysis", "Inspect rule failures, first divergence, gate composition, thresholds, and decision diagnostics.", "A negative result is useful only if the mechanism and failure conditions are explicit.", "Saved post-run diagnostics and queried-only online thresholds.", "Inventing a new Hybrid or changing hyperparameters in response to failure.", "It converts 'no win' into evidence about why side-information fusion did not beat the simpler acquisition.", "Calling failure proof that all possible hybrid methods are useless.", ("phase7_failure_diagnostics.csv", "phase7_preregistered_rule_outcome.csv"), (42,), "Gate fails A, B, and C; Rank Fusion fails A and B. Both pass the shared-random condition D.", "The boundary failures are determined across at least two of B1/B2/B3.", "It helps both Hybrids beat random, but does not beat Binary and adds overhead.", "Different untuned formulations remain possible but were deliberately not explored.", COMMON_FORBIDDEN),
        s(38, "Computational overhead", "Compare measured local fitting time at equal simulator budget.", "Sample efficiency and local computation are distinct costs.", "Measured wall time from the same four-worker execution.", "Counting auxiliary fitting as an extra simulator query or ignoring unequal local compute.", "It documents the practical price of fitting both GPC and GPR.", "Generalizing workstation timing to every deployment.", ("phase7_runtime_comparison.csv",), (49,), "Binary averages about 6.31 s per run; Gate and Fusion about 9.06 and 8.99 s, roughly 1.4× Binary.", "Runtime is independent of B1/B2/B3 evaluation.", "It adds cost without a robust performance gain in this benchmark.", "Simulator cost dominates in the intended setting and hardware timing is local.", COMMON_FORBIDDEN),
        s(39, "Final method decision", "Apply the locked decision tree to the saved rule outcomes.", "The final thesis method choice must follow the preregistered hierarchy.", "Only saved A/B/C/D outcomes and the pre-hashed rule.", "Overriding the decision because one secondary metric looks favorable.", "It selects the primary acquisition for thesis consolidation while preserving Max-Depth as a useful comparator.", "Calling the result a universal rejection of physical side information.", ("phase7_preregistered_rule_outcome.csv", "phase7_final_decision.csv", "results_summary.md"), (50,), "Neither Hybrid meets the robust success rule; the mechanical decision is BINARY ACQUISITION PRIMARY.", "Binary is no worse than both Hybrids on the preregistered boundary hierarchy under at least two definitions; in mean q20 it leads all three.", "It helps beat random, but not enough to displace Binary as the primary acquisition.", "Supervisor feedback or new external data could motivate a targeted correction, not post-hoc expansion here.", COMMON_FORBIDDEN),
        s(40, "Validation and hard stop", "Read the independent validation, requirement, figure, notebook, and manifest closeout state.", "The final result should stop only after scientific invariants and artifact integrity pass.", "Validator outputs and immutable hashes; no new method fitting.", "Changing science to satisfy a reporting check or continuing exploratory method invention after the declared stop.", "It closes the final major experiment and hands the thesis into consolidation/writing.", "Treating automated checks as a substitute for supervisor review.", ("validation_results.csv", "requirement_checklist.csv", "figure_manifest.csv", "output_manifest.csv"), (), "The final state is expected to show every validation and requirement PASS, at least 40 executed teaching sections, 50 verified figures, and a complete hash manifest.", "The validator checks all B1/B2/B3, fairness, preregistration, and decision invariants.", "No additional Hybrid is authorized; the result is frozen for writing.", "Scientific interpretation still needs careful thesis prose and supervisor review.", COMMON_FORBIDDEN, "for name in ['validation_results.csv','requirement_checklist.csv']:\n    path = OUT / name\n    if path.is_file():\n        frame = pd.read_csv(path)\n        status_col = 'status' if 'status' in frame else frame.columns[-1]\n        display(frame[status_col].value_counts().rename(name))\n    else:\n        print(f'{name}: pending first validator pass')")
    ]


def build_notebook() -> nbf.NotebookNode:
    sections = make_sections()
    if [section.number for section in sections] != list(range(1, 41)):
        raise RuntimeError("The teaching flow must contain exactly sections 1..40")
    cells: list[nbf.NotebookNode] = [
        markdown(
            """# Week 7 Phase 7 — final boundary-robustness and Hybrid benchmark

This notebook teaches the final major scientific-method experiment of the thesis **Sample-Efficient Active Level-Set Estimation, with an Application to Melt-Pool Regime Boundaries**.

Manual experiment-level `has_keyhole` remains the regime ground truth. Maximum penetration depth is side information revealed by the same queried simulation and can affect only the two preregistered acquisition rules. The final predictor for both Hybrids remains the Binary GPC. B1/B2/B3 are model-independent, evaluation-only boundary diagnostics and never enter selection.

Every major section declares its allowed information and leakage barrier before one small visible code cell. Every result then answers five fixed interpretation questions. The notebook reads saved artifacts; it does not refit, retune, relabel, or invent methods."""
        )
    ]
    for section in sections:
        cells.append(markdown(section_markdown(section)))
        cells.append(code(section_code(section)))
    notebook = nbf.v4.new_notebook(cells=cells)
    notebook.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    notebook.metadata["language_info"] = {"name": "python", "version": "3"}
    return notebook


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--kernel-name", default="python3")
    parser.add_argument("--timeout", type=int, default=900)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    notebook = build_notebook()
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    if args.execute:
        client = NotebookClient(
            notebook,
            timeout=args.timeout,
            kernel_name=args.kernel_name,
            resources={"metadata": {"path": str(ROOT)}},
            allow_errors=False,
        )
        notebook = client.execute()
    nbf.write(notebook, NOTEBOOK)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    markdown_cells = [cell for cell in notebook.cells if cell.cell_type == "markdown"]
    errors = [
        output
        for cell in code_cells
        for output in cell.get("outputs", [])
        if output.get("output_type") == "error"
    ]
    print(
        {
            "notebook": str(NOTEBOOK),
            "markdown_cells": len(markdown_cells),
            "code_cells": len(code_cells),
            "executed": sum(cell.get("execution_count") is not None for cell in code_cells),
            "stored_errors": len(errors),
        }
    )


if __name__ == "__main__":
    main()
