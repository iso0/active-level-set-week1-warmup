# Week 9 Phase 2.1R claim ledger

Primary question: **does the simple width change between consecutive resampled analysis points add
predictive value beyond `[P, VX, LS, ST]`?**

| claim | status | guardrail |
|---|---|---|
| Keyhole simulations show larger maximum width increases between consecutive resampled analysis points than Conduction simulations | NOT SUPPORTED | descriptive, whole sample: medians 29.27 vs 29.82 µm, Cliff's δ = -0.204, ROC-AUC = 0.398 |
| The MODEL-level gain from max_positive_delta_W survives changing the grid resolution (51 / 101 / 201 points) | SUPPORTED | same GPC, same folds, only the grid used to build the feature changes; q20 PR-AUC gain +0.0119 / +0.0207 / +0.0145 |
| That separation is robust to the choice of grid resolution (51 / 101 / 201 points) | QUALIFIED | Cliff's δ = -0.312 / -0.162 / -0.204 at 51 / 101 / 201 analysis points |
| A simple leak-free threshold on max_positive_delta_W classifies better than chance on the q20 boundary band | SUPPORTED | threshold learned on training folds only; q20 balanced accuracy 0.564 ± 0.025, Keyhole recall 0.866 |
| Dividing by the actual time gap (ΔW/Δt) changes the conclusion versus raw ΔW | QUALIFIED | Cliff's δ -0.204 (raw ΔW) vs -0.300 (rate); q20 threshold balanced accuracy 0.564 vs 0.433 |
| PRIMARY — adding max_positive_delta_W to the 4D GPC improves hard classification on q20 | NOT SUPPORTED | q20 balanced accuracy 0.8739 → 0.8830; Holm over six metrics within the contrast |
| PRIMARY — the same addition improves ranking / probability quality on q20 | SUPPORTED | q20 ROC-AUC / PR-AUC / Brier, read separately from the hard metrics |
| The biggest width jump is a melt-pool STARTUP quantity, not a Keyhole-onset signal | SUPPORTED | 95.4% of simulations have their largest jump inside the first 5% of the trace (median position 0.000); whatever predictive value it carries is about how the pool forms, not about a later transition |
| The small three-feature simple ΔW block improves the 4D GPC on q20 | SUPPORTED | hard NOT SUPPORTED, ranking SUPPORTED; q20 balanced accuracy 0.8773 |
| The rate block behaves differently from the raw ΔW block | QUALIFIED | 4D+rate hard NOT SUPPORTED / ranking NOT SUPPORTED versus 4D+ΔW hard NOT SUPPORTED / ranking SUPPORTED |
| M3 outperforms the plain 4D GPC on this usable subset | NOT SUPPORTED | q20 balanced accuracy 0.8739 (4D) vs 0.8464 (M3); predictive comparison, not an acquisition comparison |
| The best simple-width GPC beats M3 | SUPPORTED | 4D+simple ΔW block − M3 on q20: hard SUPPORTED, ranking SUPPORTED |
| Adding max_positive_delta_W to M3 itself improves M3 | SUPPORTED | physics mean untouched; only the discrepancy GP gains one input dimension. q20 balanced accuracy 0.8464 → 0.8656 |
| SECONDARY (historical) — the old three-feature shape subset still helps once the model is GPC rather than logistic regression | SUPPORTED | q20 balanced accuracy 0.8808 vs 4D 0.8739; Phase 2.1 saw this under logistic regression |
| SECONDARY (historical) — the old full eight-feature block helps | QUALIFIED | q20 balanced accuracy 0.8626 |
| A single robust-derivative feature is responsible for diluting the shape3 signal | QUALIFIED | worst single addition is old_shape3 (-0.0080 q20 balanced accuracy, DEGRADES); five one-at-a-time additions tested |
| These results describe raw SPH solver timesteps | NOT SUPPORTED | every ΔW here is between consecutive RESAMPLED analysis points on the Phase 2 grid; raw solver steps (~75k per simulation, dt ≈ 0.018 µs) were not used |
| Results generalise to simulations with no usable width trace | NOT SUPPORTED | every model is trained and scored only on the usable subset |
| This phase says anything about in-process monitoring hardware or about acquisition | NOT SUPPORTED | predictive feature-value experiment on frozen folds; no camera, no new active-learning path |

## Status vocabulary
- **SUPPORTED** — the 95% repeat-block interval excludes zero in the favourable direction and, for model
  contrasts, the effect survives Holm across the six predeclared metrics.
- **QUALIFIED / INCREMENTAL** — present on some metrics or some regions but not others, or directionally
  present with an interval that touches zero.
- **NOT SUPPORTED** — no detectable difference, or a difference in the unfavourable direction.
- **DESCRIPTIVE ONLY** — a marginal or exploratory observation with no held-out predictive backing.

## Corrections carried over from Phase 2.1

| previous statement | verdict | correction |
|---|---|---|
| "nothing anywhere survives the Holm adjustment" | **WRONG** | Within the six-metric Holm family, 2 results survive at the 0.05 level: q30 pr_auc +0.01043 (Holm p=0.0095); q30 brier_score -0.00463 (Holm p=0.0030). The q20 region alone showed no surviving effect. |
| "width adds no value beyond the 4D process inputs" | **OVERSTATED** | Safe wording: the full eight-feature width block did not show a supported q20 improvement over 4D, while a secondary three-feature shape subset showed a positive development signal (q20 balanced accuracy +0.0203 [+0.0094, +0.0313]). |
| "width dynamics is redundant because R-squared = 0.58" | **CAUSALLY OVERSTATED** | Safe wording: several width-derived features are substantially predictable from the process inputs (median R-squared 0.58, range 0.03-0.86). This is an association, not a demonstrated cause of the null result. |
| "the engineered eight-feature block is the width story" | **SUPERSEDED** | Phase 2.1 summarised the width trace using engineered shape and derivative descriptors. Phase 2.1R instead asks the simpler question: what happens between consecutive resampled analysis points? |
