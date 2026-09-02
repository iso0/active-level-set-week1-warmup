# Supervisor Phase 1.16 one-page

**Decision:** REPULSION_MECHANISM_ONLY

- Historical h=.15 repulsion was one fixed configuration; Phase 1.16 tested geometry-relative c=.25,.5,1,2,4 without held-out tuning.
- M3-margin baseline q20 AULC: 0.844623.
- Best numerical q20 arm: c=4, difference +0.0027 [-0.0009, +0.0060]; every primary CI includes zero.
- Early q20 AULC improves most for c=1 and c=4, but late gains are small and unresolved.
- B40 spread is larger for c≥.5 (maximum Δ +0.101), so spatial narrowing is genuinely mitigated.
- B40 q20 Keyhole recall does not improve at any scale; c=.25 is significantly worse (-0.0179).
- q30 AULC improves slightly at all five scales, but this is secondary to the unresolved q20 endpoint.
- .84 first-hit differences all include zero; there is no supported query-saving result.
- B80 full81 performance is essentially unchanged; no global harm signal.
- No primary q20 contrast survives Holm adjustment (minimum adjusted p=0.207).
- Safest conclusion: repulsion fixes geometry, not the Keyhole-recall/sample-efficiency problem. Close broad repulsion tuning rather than searching more scales.
