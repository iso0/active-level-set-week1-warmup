# Phase 1.21 comparator audit — locked rationale

Frozen before any new comparator fit was run.

## Why this addendum exists

Phase 1.21 already showed a small, statistically resolved Candidate A gain over the live M3-margin incumbent with the same B16 start. Candidate B looked larger, but it changed both the starting design and the acquisition rule. The existing report therefore cannot tell how much of Candidate B's gain comes from coverage rather than its early start.

The term A0 is also ambiguous in the repository:

- `M3_margin_incumbent` is the current M3 probability-margin policy, called `A0_m3_margin` in Phase 2.2.
- `historical_binary_A0` is the older Week 8.5 isotropic Binary-GPC probability-margin path.

They are not interchangeable.

## Locked new tests

1. Candidate B versus `early8__margin` holds the early start fixed and isolates the coverage acquisition contribution.
2. Candidate A versus `historical_binary_A0_live` holds the B16 start and M3 evaluator fixed and compares the two acquisition policies.

The original stored A0 path exists only for repeats 1–20. On repeats 61–120 the old policy must be run live and sequentially; the output will be called a recreation of the frozen policy, not the frozen stored path.

## Interpretation boundary

Repeats 61–120 were untouched when the original Phase 1.21 replication was frozen, but their Phase 1.21 results are now known. This addendum is therefore a locked attribution and comparator audit, not a second independent confirmation. It can answer which component generated the internal effect on the 405-row population. It cannot establish external generalization.

The promotion endpoint remains q20 accuracy AULC B16–B80. Balanced accuracy and the early B16–B40 window are required robustness views, not replacements for the frozen primary. A mean gain below +0.01 cannot justify replacing the incumbent even if its interval excludes zero.
