# Week 7 Phase 5 results: manual Keyhole label and continuous physical proxies

## Scope and evidence boundary

Phase 5 starts from exact Phase 4 commit `5b7004017cadc5ecd0eb128f2031f9148ed70900` and uses only the `new-data` population for primary science. The current Hugging Face main revision is `b6dc254a2b607a31cb9f97b40990339c3d5ca1e8`. Its only changes from the pinned revision are 110 added old-data monitor files (55 `time.dat` and 55 `kinetic-energy_melt.dat`); no new-data path, label, geometry monitor, or sentinel file changed.

## How the Keyhole labels were made

> I did it by hand. So almost qualitatively. Usually the existence of cavities directly under the meltpool determined my decision for keyhole.

The labels are therefore manual morphology annotations, usually guided by cavities directly below the melt pool. They were not reported as a deterministic threshold on depth, G3, R3, width, or kinetic energy. This analysis tests physical association and consistency; it neither changes the labels nor establishes causality.

## Population

All 165 new-data experiments remain in the audit interface: 63 Keyhole-positive and 102 Keyhole-negative. All 102 negatives contain at least one Conduction frame; 0 negatives lack Conduction. Machine-derived physical targets are ready for 164/165; the one file-missing case is retained and explicitly unavailable rather than silently removed.

## Main result

`G3` is the leading scalar. Its direction-adjusted ROC AUC is 1.0000, average precision is 1.0000, and exact leave-one-simulation-out threshold balanced accuracy is 1.0000. The threshold-stability class is `stable`. It is classified as **STRONG PROXY CANDIDATE** under the predeclared multi-evidence rule.

T0 depth is informative but weaker than the transient/persistence-aware depth quantities. Pairwise common-complete bootstrap comparisons, not separate-population point estimates, determine whether max depth, G3, and R3 materially improve on T0 depth.

## Transient and persistent Keyhole

For the leading scalar, held-out sensitivity is 1.0000 for transient Keyhole and 1.0000 for persistent-to-last-frame Keyhole. These groups reuse the validated Phase 1 sequence definitions; no new morphology rule was created.

## Phase 4 hard cases

The saved Phase 4 linkage table covers 164 target-ready experiments and marks 21 consensus hard cases. Of those hard cases, 18 are manual Keyhole cases and 0 cross any top-three held-out proxy decision. This linkage reuses saved Phase 4 residuals and does not refit any regression model.

## Target-formulation decision

**CONTINUOUS PROXY CANDIDATE**. G3 combines strong rank separation, near-complete held-out threshold performance, stable thresholds, high readiness, and robustness to transient Keyhole.

Phase 6 recommendation: Carry G3 as the predefined continuous candidate and compare its threshold/level-set formulation against the unchanged binary has_keyhole reference.

Even a strong continuous association does not replace Ioan's manual cavity-based label. The binary annotation remains the reference against which a continuous formulation must be tested.

## Hard stop

No final Keyhole classifier, GP classifier, new GP regression, active learning, level-set estimation, acquisition comparison, label correction, or old/new pooled model was run.
