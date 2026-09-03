# Final Phase 1.18B report

## Design
All 100 frozen outer runs used the same feature-only B16 design. P0 is the exact published Phase 1.14 M3-margin path. P1 is exact-fixed finite-pool GPC-SUR. P2 refits the revealed-label-fitted physics mean inside each hypothetical outcome while retaining the current Stage-2 kernel.

## Primary q20 AULC

| Arm | Mean AULC |
|---|---:|
| P0 M3 Margin | 0.844623162 |
| P1 exact-fixed SUR | 0.843244485 |
| P2 physics-refit SUR | 0.840170037 |

P1−P0 = **-0.001378676**, repeat-block 95% CI **[-0.003800551, +0.000726103]**. P2−P0 = **-0.004453125**, CI **[-0.010703240, +0.001627068]**. Holm adjustment is reported in `multiplicity_adjustment.csv`.

Primary decision: **GLOBAL_SUR_NO_GAIN**. Physics-refit decision: **PHYSICS_REFIT_SUR_CHANGES_PATH_ONLY**. Label-saving decision: **LABEL_SAVING_NOT_SUPPORTED**.

## Predeclared secondary checks

- EARLY/MID/LATE P1−P0 q20 contrasts: +0.002169, -0.003980, -0.001033.
- B40 q20 Keyhole recall P0/P1/P2: 0.748738 / 0.739679 / 0.744714; balanced accuracy: 0.827068 / 0.818377 / 0.817482.
- q30 AULC P1−P0: -0.001409, CI [-0.003044, +0.000088]. q30 remains secondary.
- B80 revealed-set Jaccard P1/P0: 0.9641; P2/P1: 0.6620.
- P1/P2 common-candidate score median Spearman: -0.3079; top-1 agreement: 0.0728; mean top-5 Jaccard: 0.1039.
- Mean P1−P0 global candidate-pool uncertainty at common checkpoints: +4.802678e-04.
- Observed median full-run time P1/P2: 216.86 s / 469.06 s.

## Mechanism and robustness
There were 0 failed hypothetical solves and 0 deterministic increased-iteration fallbacks. Path divergence, early/mid/late effects, B40 Keyhole recall, q30, full-heldout behavior, threshold attainment, score scale, near ties, and actual runtime are all disclosed in the companion machine-readable tables.

## Claim boundary
This is one finite simulator pool and a one-step probability-uncertainty SUR functional. It is not an exact implementation of a particular random-set SUR paper, does not prove theoretical sample complexity, and does not support universal label savings unless the predeclared threshold analysis says so.
