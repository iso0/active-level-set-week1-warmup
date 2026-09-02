# Final red-team report

- Phase 1.13 remains the immutable branch base; historical Phase 1.x artifacts were not edited.
- P0 is reused Phase 1.13 M3-on-A0; P1 uses the exact same M3 architecture and differs only by path.
- All 100 initial 16-point designs are identical, and B16 predictions are checked for exact equality.
- Evaluation folds are excluded from candidates; hidden labels, B1, q20, and q30 are absent from acquisition.
- Selection uses one query after current-budget evaluation; no future label or off-by-one prefix enters fitting.
- Historical classifier-margin orientation and smallest-index tie break are reused.
- Twenty repeat blocks, not 100 folds, are the inferential unit.
- Early/late regions and thresholds were frozen before P1 results.
- Keyhole recall, full81 behavior, bound hits, convergence, and L1000 path sensitivity are disclosed.
- Path divergence is described, not assumed beneficial.
- No universal acquisition, theoretical sample-complexity, external-transfer, or causal-ARD claim is made.
