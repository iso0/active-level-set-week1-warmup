"""Build the step-by-step Week 9 Phase 1 teaching notebook from final outputs."""

from __future__ import annotations

import json
from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "week9_phase1_close_week8"
NOTEBOOK = ROOT / "notebooks" / "week_09" / "01_week9_phase1_close_week8.ipynb"


def md(text: str):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text: str):
    return nbf.v4.new_code_cell(text.strip())


def interpretation(*, see: str, matter: str, claim: str, cannot: str):
    return md(
        f"""**What do we see?** {see}

**Why does it matter?** {matter}

**What can we claim?** {claim}

**What can we NOT claim?** {cannot}"""
    )


def build() -> Path:
    summary = json.loads((OUTPUT / "summary.json").read_text(encoding="utf-8"))
    claim = summary["query_saving_claim"]
    horizon = {(int(row["horizon"]), row["arm"]): row for row in summary["horizon_results"]}
    m320 = horizon[(320, "binary_margin")]
    r320 = horizon[(320, "binary_random")]
    notebook = nbf.v4.new_notebook()
    notebook["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    }
    notebook["cells"] = [
        md("""# Week 9 — Phase 1: closing the Week 8/8.5 sample-efficiency result

This notebook is a **teaching and reporting notebook**. It reads validated machine-readable outputs; it does not retune an acquisition rule or rewrite the frozen Week 8.5 protocol.

The new H=320 work is a **post-hoc horizon-extension closing diagnostic**."""),
        code("""from pathlib import Path
import json
import pandas as pd
from IPython.display import display, Image, Markdown

ROOT = Path.cwd().resolve().parents[1] if Path.cwd().name == 'week_09' else Path.cwd()
OUT = ROOT / 'outputs' / 'week9_phase1_close_week8'
summary = json.loads((OUT / 'summary.json').read_text(encoding='utf-8'))
summary['analysis_status']"""),
        md("""## 1. Question and why we are doing this

Week 8.5 confirmed faster Fold-B1-q20 learning by Binary Margin over matched Random using AULC from budgets 16–80. The remaining practical question was whether the persistent 0.80 target crossings that were unresolved at H=160 would become observable by H=320, and whether a defensible query-saving statement followed."""),
        code("""questions = pd.DataFrame({
    'Question': [
        'Which method improves faster over the query budget?',
        'Which method has the better model at a fixed final budget?',
        'How many paths have a confirmed persistent 0.80 Fold-B1-q20 crossing?',
    ],
    'Correct metric': ['AULC', 'Terminal accuracy / recall / specificity', 'Confirmation-aware crossing rate'],
})
display(questions)"""),
        interpretation(
            see="The scientific questions require three different estimands.",
            matter="Using the correct metric prevents a learning-speed result from being mislabeled as final-model quality.",
            claim="AULC and terminal metrics are complementary.",
            cannot="AULC is not terminal accuracy, and q20 is not the physical boundary.",
        ),
        md("""## 2. Existing frozen Week 8.5 state

Ground truth is the **manual `has_keyhole` label**. Inputs are `P`, `VX`, `LS`, and `ST`; **ST means substrate temperature**. Fold-B1-q20 is the 17 held-out test simulations with the smallest B1 distance within each 81-row fold. It is an empirical near-boundary evaluation subset."""),
        code("""frozen = pd.DataFrame([
    ['Population', '405 simulations: 73 Keyhole, 332 Conduction'],
    ['Outer design', '20 repeats × 5 folds = 100 runs'],
    ['Initial design', '16 feature-only, arm-matched queries'],
    ['Random', '30 continuations within each outer run'],
    ['Frozen AULC Margin', summary['frozen_AULC']['binary_margin']],
    ['Frozen AULC matched Random', summary['frozen_AULC']['matched_binary_random']],
    ['Frozen AULC delta', summary['frozen_AULC']['margin_minus_random']],
], columns=['Item', 'Frozen value'])
display(frozen)"""),
        interpretation(
            see="The population, labels, splits, initial designs, models, and seeds were inherited unchanged.",
            matter="The H=320 work continues the same trajectories rather than creating a new method search.",
            claim="The frozen AULC result remains the confirmatory Week 8.5 result.",
            cannot="The post-hoc extension cannot retroactively change the Week 8.5 decision ledger.",
        ),
        md("""## 3. Reproducibility validation through H=160

Every H=160 checkpoint was read from the pinned compressed bundle. The ordered 160-query prefix, split membership, initial 16 queries, Random order, fit seeds, and saved metrics were validated before any extension output was accepted."""),
        code("""validation = json.loads((OUT / 'validation_report.json').read_text(encoding='utf-8'))
checks = pd.DataFrame(validation['checks'])
display(checks[['check_id', 'status']])
assert validation['status'] == 'PASS'"""),
        interpretation(
            see="Historical H=80, H=120, and H=160 crossing counts and burdens reproduce exactly.",
            matter="An H=320 result is interpretable only after historical identity is preserved.",
            claim="The continuation is anchored to the frozen trajectories.",
            cannot="A merely similar rerun would not be the same scientific experiment.",
        ),
        md("""## 4. Horizon extension to 320

Only `binary_margin` and `binary_random` were extended. Margin was refit sequentially because each next query depends on its current classifier. Random used its frozen seeded order; after a persistent crossing was confirmed, intermediate fits were no longer needed, but budget 320 was still fit for terminal performance."""),
        code("""horizon = pd.read_csv(OUT / 'crossing_by_horizon.csv')
display(horizon.pivot(index='horizon', columns='arm', values=['finite_persistent_crossings','finite_rate','unresolved','restricted_mean_query_burden']))"""),
        interpretation(
            see=f"At H=320, Margin has {int(m320['finite_persistent_crossings'])}/100 confirmed crossings; Random has {int(r320['finite_persistent_crossings'])}/3000.",
            matter="The longer horizon directly answers how much H=160 right-tail uncertainty was resolved.",
            claim="These are post-hoc attainment diagnostics on the fixed 405-simulation benchmark.",
            cannot="They are not preregistered H=320 confirmation or independent physical campaigns.",
        ),
        md("""## 5. Persistent 80% crossing results

`Q` is the **first** checkpoint in a run of three passing checkpoints. The crossing becomes observable only at the **third** checkpoint. Therefore every horizon count below requires `confirmation_budget <= horizon`."""),
        code("""display(Image(filename=str(OUT / 'figures' / '02_persistent_target_attainment_vs_horizon.png')))"""),
        interpretation(
            see="The attainment curves use confirmation time, while the reported burden retains the historical Q-start definition.",
            matter="This prevents a triple completed after H from being counted as already observed at H.",
            claim="Historical counts are unchanged and later counts use the same definition.",
            cannot="A full-H320 Q cannot simply be compared with H to reconstruct earlier censoring.",
        ),
        md("""## 6. Query-saving interpretation

The naive statement “every unresolved Random path has Q>320” is not generally true. If 316 and 320 pass, a future 324 pass could later assign Q=316. The analysis therefore uses **path-specific lower bounds** for the unresolved tail and keeps the H=320 restricted burden descriptive."""),
        code("""claim = json.loads((OUT / 'query_saving_claim_decision.json').read_text(encoding='utf-8'))
display(pd.Series(claim, name='value').to_frame())
display(pd.read_csv(OUT / 'matched_pair_crossing_categories.csv').groupby('category').size().rename('matched comparisons').to_frame())"""),
        interpretation(
            see=claim["supervisor_safe_sentence"],
            matter="The statement follows the frozen crossing definition instead of assuming away the unobservable tail.",
            claim="Only the exact sentence in the claim decision is supervisor-safe.",
            cannot="The restricted 320-clipped mean is not automatically a mathematical lower bound.",
        ),
        md("""## 7. AULC versus terminal accuracy

| Question | Correct metric |
|---|---|
| Which method learns faster as query budget increases? | AULC |
| Which method has the best model at budget 80? | Terminal metric at 80 |
| Which method has the best model at budget 160? | Terminal metric at 160 |
| Which method has the best model at budget 320? | Terminal metric at 320 |"""),
        code("""terminal = pd.read_csv(OUT / 'terminal_metric_summary.csv')
accuracy = terminal[(terminal.metric == 'accuracy') & terminal.estimand.isin(['binary_margin','binary_random','margin_minus_random'])]
display(accuracy.pivot_table(index=['budget','subset'], columns='estimand', values='point_estimate'))
display(Image(filename=str(OUT / 'figures' / '04_aulc_vs_terminal_performance_summary.png')))"""),
        interpretation(
            see="The table reports final-model quality at each fixed budget, separately from the frozen 16–80 AULC.",
            matter="Agreement strengthens the practical story; disagreement identifies a genuine estimand difference rather than an error.",
            claim="Terminal results are post-hoc fixed-budget diagnostics.",
            cannot="A terminal advantage alone does not prove faster learning across the entire budget range.",
        ),
        md("""## 8. Full 81 versus q30 versus q20 performance

Full81 tests global prediction. Fold-B1-q30 (25 rows) and Fold-B1-q20 (17 rows) are nested, increasingly boundary-like held-out subsets."""),
        code("""display(Image(filename=str(OUT / 'figures' / '03_terminal_accuracy_full_q30_q20.png')))
selected = terminal[(terminal.budget.isin([80,160,320])) & terminal.estimand.isin(['binary_margin','binary_random'])]
display(selected.pivot_table(index=['budget','subset','metric'], columns='estimand', values='point_estimate'))"""),
        interpretation(
            see="Global and near-boundary metrics are shown side by side, including recall, specificity, false negatives, and false positives in the table.",
            matter="A high global score can hide the harder empirical near-boundary subset.",
            claim="q20/q30 quantify held-out difficulty under the manual labels.",
            cannot="Their accuracies measure neither physical-boundary certainty nor causality.",
        ),
        md("""## 9. PCA visualization and interpretation

PCA answers a narrow question: **which directions contain the most variation in the sampled four-input design?** It does not search for the direction that best separates Keyhole from Conduction. A supervised projection such as LDA would answer a different, label-dependent question and is outside this visualization-only analysis.

The primary PCA first standardizes `P`, `VX`, `LS`, and `ST`, because their physical units and numerical scales differ. Labels never enter the scaler or PCA fit. The global PCA coordinates also never enter GPC training or acquisition. Previously queried labels do train later GPC fits, as required by active learning."""),
        code("""pca = json.loads((OUT / 'pca_summary.json').read_text(encoding='utf-8'))
variance = pd.read_csv(OUT / 'pca_explained_variance.csv')
loadings = pd.read_csv(OUT / 'pca_feature_loadings.csv')
interpretations = pd.read_csv(OUT / 'pca_component_interpretations.csv')
display(variance)
display(loadings)
display(interpretations[['component','short_interpretation','explained_variance_ratio','scientific_scope']])
display(Image(filename=str(OUT / 'figures' / '05_pca_input_geometry_and_loadings.png')))"""),
        interpretation(
            see="PC1 is an almost balanced LS-versus-P contrast, while PC2 is mainly sampled ST variation. Together they retain 58.42% of standardized input variance.",
            matter="The loading bars make the plotted axes physically readable and expose the 41.58% of variance omitted from the 2D view.",
            claim="The Keyhole colors are an after-the-fact overlay on a label-free input-variance projection.",
            cannot="A large loading is not physical importance, causal influence, or proof that a feature is the best Keyhole predictor.",
        ),
        md("""### 9.1 Preprocessing robustness

StandardScaler is the declared primary view. RobustScaler is one sensitivity diagnostic, not a replacement. Each variant is shown in its own native explained-variance order; only the arbitrary sign is made deterministic by orienting the largest-magnitude coefficient positively."""),
        code("""display(pd.read_csv(OUT / 'pca_scaling_explained_variance.csv'))
display(Image(filename=str(OUT / 'figures' / '06_pca_scaling_robustness.png')))"""),
        interpretation(
            see="Standard and robust scaling agree that PC2 is strongly ST-related and PC3 is strongly VX-related, but they materially disagree on PC1.",
            matter="The sensitivity check distinguishes stable component structure from conclusions that depend on preprocessing.",
            claim="The ST/PC2 and VX/PC3 pattern is qualitatively robust; the exact PC1 interpretation is scaling-dependent.",
            cannot="The sensitivity result turns either representation into physical importance or causal evidence.",
        ),
        md("""### 9.2 What the main 2D view leaves out

PC3 explains 25.04%, nearly as much as PC2, and is overwhelmingly associated with `VX`. Therefore the PC1–PC2 scatter necessarily hides most scan-velocity variation."""),
        code("""display(Image(filename=str(OUT / 'figures' / '07_pca_component_loading_structure.png')))"""),
        interpretation(
            see="PC1 is the P–LS contrast, PC2 is mainly ST, and PC3 is mainly VX in the primary StandardScaler PCA.",
            matter="Showing PC3 prevents the 2D plot from silently erasing an input direction that carries one quarter of standardized variance.",
            claim="The PC1–PC3 coefficient panel makes the omitted VX-heavy direction explicit.",
            cannot="Component coefficients are causal or predictive feature importance.",
        ),
        md("""### 9.3 Boundary-like held-out subsets

The representative fold is chosen deterministically from label-informed q20 difficulty summaries, not from visual appearance. This choice is visualization-only and does not affect PCA, model fitting, acquisition, or performance estimates. q20 is nested inside q30 and is defined using opposite-label proximity in standardized 4D input space."""),
        code("""display(Image(filename=str(OUT / 'figures' / '08_pca_boundary_like_subset.png')))
diagnostics = pd.read_csv(OUT / 'pca_interpretation_diagnostics.csv')
display(diagnostics.groupby('representative_test_role')['opposite_label_fraction_10nn_in_pc1_pc2'].agg(['count','mean']))"""),
        interpretation(
            see="The q20 points show more class mixing in this PC1–PC2 projection than held-out points outside q30.",
            matter="This gives an interpretable 2D picture of the evaluation subset used for the frozen near-boundary metric.",
            claim="The projection is descriptively concordant with q20 being boundary-like in the frozen empirical definition.",
            cannot="Because q20 itself uses labels and 4D opposite-class distance, this is not independent boundary validation or a physical-boundary proof.",
        ),
        md("""### 9.4 Where Margin spends queries

The panels are mutually exclusive query stages. Color is an after-the-fact 10-nearest-neighbour class-mixing diagnostic in PC1–PC2. Held-out test rows and the four pool rows still unqueried at H320 are kept separate in the saved diagnostics."""),
        code("""display(Image(filename=str(OUT / 'figures' / '09_pca_margin_query_trajectory.png')))
stage = diagnostics.groupby('margin_query_stage')['opposite_label_fraction_10nn_in_pc1_pc2'].agg(['count','mean'])
display(stage.loc[['initial_1_16','acquired_17_40','acquired_41_80','acquired_81_160','acquired_161_320','unqueried_pool_by_h320','held_out_test']])"""),
        interpretation(
            see="Queries 17–40 have mean projected class mixing 0.412, compared with 0.205 for 41–80, 0.083 for 81–160, and 0.017 for 161–320.",
            matter="The exclusive stages show early concentration near 2D class overlap followed by broader coverage as the finite pool is exhausted.",
            claim="This representative fold shows a descriptive association between early Margin queries and projected class mixing.",
            cannot="The association is not causal, is not a performance estimate, and cannot establish that every early query lies on the true 4D boundary.",
        ),
        md("""### 9.5 Secondary model-slice diagnostic

This final panel is deliberately secondary. It evaluates the representative-fold H320 GPC on a PC1–PC2 grid while fixing PC3=PC4=0. Only observed points with `|PC3| <= 0.5` and `|PC4| <= 0.5` are overlaid, so points far from the displayed slice are not presented as pointwise checks."""),
        code("""display(Image(filename=str(OUT / 'figures' / '10_pca_gpc_slice_diagnostic.png')))
display(pd.Series({
    'role': pca['slice_role'],
    'overlay tolerance': pca['slice_overlay_tolerance_absolute_pc3_pc4'],
    'overlay point count': pca['slice_overlay_point_count'],
    'caveat': pca['slice_caveat'],
}))"""),
        interpretation(
            see="The dashed 0.5 contour belongs to one declared PC3=PC4=0 model slice inside the projected 2D hull.",
            matter="It can help inspect one cross-section of the fitted 4D classifier while keeping the geometry limitation visible.",
            claim="It is a model diagnostic for one representative fold and one slice at budget 320.",
            cannot="The contour is not the full 4D empirical boundary, not verified support on the observed 4D manifold, and not a physical Keyhole boundary.",
        ),
        md("""## 10. Claim ledger

Frozen confirmatory claims and new post-hoc diagnostics are deliberately separated."""),
        code("""ledger = pd.read_csv(OUT / 'claim_ledger.csv')
display(ledger[['category','claim','status','strongest_safe_wording','must_not_use']])"""),
        interpretation(
            see="Each claim has a category, status, safe wording, and prohibited wording.",
            matter="This prevents post-hoc evidence from being relabeled as frozen confirmation.",
            claim="The ledger is the authoritative language guide for the supervisor summary.",
            cannot="No claim may be strengthened by omitting its assumptions or status.",
        ),
        md("""## 11. Limitations

- H=320 was chosen after the frozen H=160 analysis.
- Results describe a fixed 405-simulation population plus split/acquisition randomness.
- The manual label is ground truth for this benchmark, not an error-free physical oracle.
- q20 contains 17 rows per fold, so a single classification changes accuracy by about 5.9 percentage points.
- PCA PC1+PC2 discards 41.58% of standardized 4D input variance, including most VX variation in PC3.
- PCA maximizes sampled-input variance rather than Keyhole/Conduction separation; PC1 is also materially scaling-sensitive.
- The persistent-Q start can be tail-indeterminate at the final horizon because two future checkpoints are needed.
- No new simulator or prospective physical validation was performed."""),
        interpretation(
            see="The main uncertainty is interpretive scope, not missing arithmetic.",
            matter="These limits define what belongs in thesis conclusions versus future validation.",
            claim="The analysis closes the retrospective sample-efficiency evidence as far as H=320 permits.",
            cannot="It does not establish universal transfer, causal physics, or online experimental safety.",
        ),
        md("""## 12. Supervisor-ready conclusions

The concise 5–8-message version is stored in `supervisor_summary.md`."""),
        code("""display(Markdown((OUT / 'supervisor_summary.md').read_text(encoding='utf-8')))"""),
    ]
    notebook["cells"].extend(
        [
            md("""# Label-aware discriminative upgrade

The earlier PCA section remains useful for **label-free input geometry**. This addendum asks the different, supervised question: *which variables, combinations, and fixed-form physical quantities distinguish the manual Keyhole label from Conduction?* Nothing here changes the frozen Week 8.5 result, H320 extension, or terminal analysis."""),
            code("""DU = OUT / 'discriminative_update'
du = json.loads((DU / 'summary.json').read_text(encoding='utf-8'))
audit = pd.read_csv(DU / 'data_audit_table.csv')
display(audit)
assert du['population']['rows'] == 405
assert du['population']['keyhole'] == 73
assert du['population']['conduction'] == 332"""),
            interpretation(
                see="The analysis uses exactly 405 canonical rows: 73 Keyhole and 332 Conduction. LS is stored as radius in metres and displayed in micrometres; the separate 407-row audit file is not modelling input.",
                matter="A correct unit audit is essential because every LS-based physical score contains LS to the first, second, or three-halves power.",
                claim="All new results use the same canonical manual labels and four physical inputs.",
                cannot="The manual labels are not an error-free physical oracle, and the sampled ranges do not establish universal transfer.",
            ),
            md("""## 13. Which individual variables discriminate the label?

**Question.** Does each variable rank Keyhole above Conduction by itself?

**Method.** We compute raw and direction-adjusted ROC-AUC. The positive/negative direction is chosen once from the observed feature, then held fixed in 5,000 class-stratified bootstrap resamples. This avoids artificially folding every weak bootstrap result above 0.5. Correlations and one-variable standardized logistic odds ratios are saved in the same table."""),
            code("""feature = pd.read_csv(DU / 'feature_discrimination.csv')
display(feature[['feature','empirical_direction','raw_roc_auc','direction_adjusted_roc_auc',
                 'direction_adjusted_auc_ci_lower','direction_adjusted_auc_ci_upper',
                 'point_biserial_correlation','spearman_correlation','odds_ratio_per_1sd']])
display(Image(filename=str(DU / 'figures' / '01_feature_discriminative_power.png')))"""),
            interpretation(
                see="P is strongly positive (AUC 0.931), LS strongly negative (0.897), VX moderately negative (0.614), and ST is near chance (0.528; interval includes 0.5).",
                matter="This directly answers label discrimination, unlike PCA loadings, which only describe input variance.",
                claim="Within the sampled data, higher P and smaller LS are the strongest individual label associations; VX is weaker and ST has no detectable univariate discrimination.",
                cannot="ST is noise, or any single variable is causal or defines the true physical boundary.",
            ),
            md("""## 14. What does a label-informed 2D view add?

**Question.** Can all four inputs be shown in a supervised two-dimensional linear view?

**Method.** A two-component PLS regression is fitted after standardization solely for visualization. Unlike PCA, it uses `has_keyhole`. Projection weights define the score axes; loadings describe reconstruction of standardized inputs. This fit is not used for CV, acquisition, or a physical boundary claim."""),
            code("""display(pd.read_csv(DU / 'pls_projection_loadings.csv'))
display(Image(filename=str(DU / 'figures' / '02_label_informed_pls_projection.png')))"""),
            interpretation(
                see="PLS1 emphasizes high P and small LS, while PLS2 contrasts LS and VX. ST receives little weight in this supervised view.",
                matter="The projection makes label separation visible while honestly declaring that the labels shaped the axes.",
                claim="PLS is a useful label-informed visualization of this sample.",
                cannot="PLS is PCA, independent validation, or true physical geometry.",
            ),
            md("""## 15. Do interactions materially improve the four-input model?

**Question.** Is a parsimonious interaction useful beyond the four main effects?

**Method.** M0 is intercept-only, M1 contains P+VX+LS+ST, M2 adds all six pairwise interactions, and M3 adds only P×VX while preserving all main effects. An L1 interaction model is kept as a separately named comparator. Scaling and model fitting occur inside each of 5×10 stratified CV folds."""),
            code("""display(pd.read_csv(DU / 'glm_hierarchy.csv'))
display(pd.read_csv(DU / 'glm_likelihood_ratio_tests.csv'))
display(pd.read_csv(DU / 'glm_cv_summary.csv')[['model','mean_roc_auc','mean_pr_auc',
                                                'mean_balanced_accuracy','mean_brier_score','mean_log_loss']])
display(Image(filename=str(DU / 'figures' / '03_glm_hierarchy_cv.png')))"""),
            interpretation(
                see="M1 reaches ROC-AUC 0.990 and M3 reaches 0.994. P×VX is supported in the full-data likelihood-ratio test, but its CV ROC-AUC gain is only +0.0034.",
                matter="The interaction changes fitted transition shape and improves calibration more clearly than ranking.",
                claim="M3 is a useful parsimonious descriptive model; its predictive gain over M1 is small.",
                cannot="P×VX is a major breakthrough, causal mechanism, or universally transferable law.",
            ),
            md("""## 16. Can one fixed-form physical score nearly match four inputs?

**Question.** How does `h = P / sqrt(VX*LS^3)` compare with simpler fixed-form quantities?

**Method.** Each scalar receives a fold-local scaler and fitted logistic calibration in the same repeated CV. Exponents are fixed before analysis. Raw and log forms are both evaluated. `h` has units W·s^0.5/m² here; it is not dimensionless without the omitted material and thermal normalization."""),
            code("""physical = pd.read_csv(DU / 'physical_score_cv_summary.csv')
display(physical.sort_values('mean_roc_auc', ascending=False)[['model','mean_roc_auc','mean_pr_auc',
                                                               'mean_balanced_accuracy','mean_brier_score','mean_log_loss']])
display(Image(filename=str(DU / 'figures' / '04_physics_score_benchmark.png')))
display(Image(filename=str(DU / 'figures' / '05_h_score_transition.png')))"""),
            interpretation(
                see="Raw and log(h) have virtually identical ROC-AUC (0.98979 versus 0.98976). Log(h) has lower Brier score and log loss, so it is preferred for calibration.",
                matter="A fixed-form one-dimensional score nearly matches M1 after fitting a logistic intercept and slope.",
                claim="The process-parameter part of the keyhole scaling is highly discriminative on this benchmark after calibration.",
                cannot="h is zero-parameter, dimensionless by itself, or proof that the true 4D boundary collapses to one dimension.",
            ),
            md("""## 17. Which physical 2D maps are operationally useful?

**Question.** Which two-input planes best explain the manual label?

**Method.** All six physical pairs are ranked with the same leak-free repeated CV. The two best planes are then fitted on all 405 rows only for visualization; dashed P(Keyhole)=0.5 curves are model-based transition contours."""),
            code("""display(pd.read_csv(DU / 'pairwise_plane_cv_summary.csv')[['model','mean_roc_auc','mean_pr_auc','mean_brier_score']])
display(Image(filename=str(DU / 'figures' / '06_operational_plane_ranking_and_maps.png')))
display(Image(filename=str(DU / 'figures' / '07_fold_b1_q20_geometry.png')))"""),
            interpretation(
                see="P–LS ranks first (ROC-AUC 0.975), followed by P–VX (0.956). The representative Fold-B1 plot contains exactly 17 q20 and 25 q30 held-out rows.",
                matter="These axes are physically readable and more useful for operational discussion than choosing axes by PCA variance.",
                claim="P–LS and P–VX are the strongest tested two-input surrogate views.",
                cannot="Their dashed contours are true physical boundaries, and the 2D q20 picture independently validates B1.",
            ),
            md("""## 18. Do early Margin queries concentrate near the transition?

**Question.** Are saved queries 17–40 closer to post-hoc transition references than the initial, late, and unqueried stages?

**Method.** The exact first 160 indices from every saved Binary Margin trajectory are used—no acquisition rerun and no synthetic order. Two separate references are computed inside each 324-row training pool: nearest opposite-manual-label distance (B1-like) and absolute logit from a post-hoc M3 fit using all pool labels. Inference first averages five folds inside each of 20 repeat blocks, then bootstraps repeat blocks."""),
            code("""active = pd.read_csv(DU / 'active_geometry_comparison_summary.csv')
display(active)
display(Image(filename=str(DU / 'figures' / '08_margin_query_transition_geometry.png')))"""),
            interpretation(
                see="Every headline comparison is positive in 100/100 outer runs and 20/20 repeat blocks. Early queries are 0.935 standardized B1 units closer than the initial design and 1.070 closer than the H160-unqueried pool; the corresponding absolute-logit contrasts are 9.097 and 12.591.",
                matter="This provides a stable descriptive mechanism for why uncertainty sampling learns the empirical transition efficiently.",
                claim="Early Margin queries preferentially concentrate near two post-hoc empirical/model transition references in this benchmark.",
                cannot="Those references entered acquisition, caused faster learning, or represent the true physical boundary.",
            ),
            md("""## 19. Upgrade claim ledger and validation

The new claims are stored separately from the frozen Week 8.5 ledger. PASS means the tested statement is supported under its stated scope; QUALIFY means the effect exists but stronger wording would overstate it; REJECT records a hypothesis that the data do not support."""),
            code("""display(pd.read_csv(DU / 'claim_ledger.csv'))
du_validation = json.loads((DU / 'validation_report.json').read_text(encoding='utf-8'))
display(pd.DataFrame(du_validation['checks']))
assert du_validation['status'] == 'PASS'"""),
            interpretation(
                see="The upgrade validates units, fold-local preprocessing, exact saved query prefixes, repeat-block inference, formulas, wording, and figure count.",
                matter="The claim ledger keeps strong numerical discrimination separate from causal or universal physical interpretation.",
                claim="The upgrade is reproducible, label-aware, and scoped to the canonical benchmark.",
                cannot="This retrospective analysis substitutes for prospective experiments or external validation.",
            ),
        ]
    )
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, NOTEBOOK)
    return NOTEBOOK


if __name__ == "__main__":
    print(build())
