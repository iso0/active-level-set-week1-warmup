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
        md("""## 9. PCA 2D visualization and interpretation

PCA was fit after standardizing only `P`, `VX`, `LS`, and `ST`; labels never entered the PCA fit. The representative fold was chosen deterministically by median static q20 difficulty, not by visual appearance."""),
        code("""pca = json.loads((OUT / 'pca_summary.json').read_text(encoding='utf-8'))
display(pd.read_csv(OUT / 'pca_explained_variance.csv'))
display(pd.read_csv(OUT / 'pca_feature_loadings.csv'))
for name in ['05_pca_full_population.png','06_pca_boundary_subsets_representative_fold.png','07_pca_active_learning_trajectory.png','08_pca_plane_gpc_slice.png']:
    display(Image(filename=str(OUT / 'figures' / name)))"""),
        interpretation(
            see="PC1 and PC2 summarize part—not all—of the standardized 4D variation; q20 rows show greater projected class mixing and Margin queries concentrate around overlapping regions.",
            matter="The plots make the 4D query behavior explainable without feeding the projection into the model.",
            claim="The probability contour is a PC1–PC2 slice with PC3=PC4=0.",
            cannot="The contour is not the full 4D empirical boundary and is not a physical boundary proof.",
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
- PCA PC1+PC2 discards remaining 4D variance.
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
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, NOTEBOOK)
    return NOTEBOOK


if __name__ == "__main__":
    print(build())
