# Track A final state

Freeze date: 2026-09-21  
Scope: method and decision freeze before any genuinely new Ioan simulation batch is accessed.

## Final decision

- **Predictive model:** M3: a revealed-label logistic trend in `log h` plus a four-dimensional ARD Matérn-3/2 GP discrepancy over `[P, VX, LS, ST]`.
- **Physics coordinate:** `h = P / sqrt(VX * LS^3)` and `log h = log P - 0.5 log VX - 1.5 log LS`.
- **Binary target:** manual ground truth `has_keyhole`.
- **Live control/incumbent:** M3 probability margin with the frozen feature-only B16 maximin initialization.
- **Single frozen external challenger:** `early8__coverage_then_margin_B40`.
- **Same-B16 attribution control:** `coverage_then_margin_B40`.
- **Historical comparator, not the live control:** `historical_binary_A0_live` (the frozen Week 8.5 Binary-GPC margin policy, recreated with path parity for the Week 10 audit).
- **Status:** internal method development is closed. No further acquisition search on OLD-405 is authorized.

Candidate B is an internally replicated composite initial-design-plus-acquisition policy. It is not externally validated and does not replace the incumbent. Its q20 accuracy AULC B16-B80 advantage over the live M3-margin control is `+0.006708` (`[+0.004775,+0.008632]`), below the predeclared `+0.01` replacement threshold. The matched early-start comparison attributes `+0.001939` (`[+0.000458,+0.003402]`) to coverage conditional on that start.

Candidate A, `coverage_then_margin_B40`, shares the control's B16 start and therefore supplies the pure acquisition contrast: `+0.003171` (`[+0.001671,+0.004759]`) on q20 accuracy AULC B16-B80. The Week 10 live comparison against historical Binary-A0 is `+0.002990` (`[+0.000590,+0.005434]`), but that is a complete-policy comparison and must not be called a pure formula effect.

## Closure evidence

- G3-margin, generic repulsion, ordinary-M3 finite-pool SUR, hard monotone propagation, soft monotone leverage, physics-only early initialization, PG-RMBC, and boundary-displacement augmentation did not replace the frozen state.
- PG-RMBC's full policy is `NO_CLEAR_IMPROVEMENT` versus Candidate B.
- Boundary-displacement Gate 1 stopped before acquisition Gate 2: M0/M1/M2 q20 accuracy AULC B16-B40 is `0.837684/0.837688/0.837688`; M1-M0 is about `+0.000004` and M1-M2 is effectively zero.
- The large representative alternate-start covariance instability belongs to M2, the generic augmentation control, not M1. M1 independently failed because it added essentially no predictive value and did not beat M2.

## Claim boundary

This freeze supports an internally replicated, small OLD-405 policy-ordering effect. It does not establish external validity, physical-boundary truth, guaranteed simulator savings, camera/sensor feasibility, or replacement of M3-margin. q20 accuracy and q20 balanced accuracy are different endpoints and must never be combined.

The next Track A action is the label-free intake/provenance gate in `EXTERNAL_VALIDATION_PROTOCOL.md`, after a genuinely new immutable batch manifest is delivered.
