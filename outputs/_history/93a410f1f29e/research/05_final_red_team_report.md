# Week 9 Phase 1.5 — final adversarial red-team report

## Decision

**PASS with qualifications.** The strongest defensible conclusion is narrower than the original Antigravity story: `h=P/sqrt(VX*LS^3)` is a physically motivated, highly informative one-dimensional coordinate, but it is dimensional, it does not replace the 4D boundary model, and it does not improve the acquisition policy for learning the 4D boundary under the exact frozen protocol.

This audit checked the primary-literature report, data/protocol audit, implemented source, static and active-learning outputs, figures, notebook, claim ledger, final report, and frozen Week 8.5 protocol. Material contradictions found during review were corrected before this final decision.

## Adversarial checks

| Check | Result | Evidence / qualification |
|---|---|---|
| LS radius versus diameter | PASS | Authoritative repository provenance identifies `LS` as Gaussian spot radius `r0`, stored in metres; deliverables no longer call it diameter. |
| SI versus micrometre use | PASS | h is computed from SI values; µm appears only in display columns/labels. Bare h has units `W s^(1/2) m^-2`. |
| ST meaning | PASS | `ST` is consistently substrate temperature. The 1933 K correction is explicitly partial and uses Ti-6Al-4V liquidus temperature. |
| Literature equation transcription | PASS | Gan Eq. 1/3 supports the P^1 V^-1/2 r0^-3/2 process dependence. The full Keyhole number includes material/temperature factors; bare h is not dimensionless. |
| Unsupported depth law attribution | PASS after correction | The claimed `d/r0 ∝ Ke^1.69` attribution is rejected; Gan's reported depth scaling is not that exponent law. |
| Canonical data and labels | PASS | 405 rows, 73 Keyhole, 332 Conduction; manual `has_keyhole` retained. |
| Split and q20/q30 definitions | PASS | Exact frozen 20×5 runs, 324/81 split, exact 16-point initial design, q20=17 and q30=25; B1 is evaluation-only. |
| Training/test leakage | PASS | Saved 27,200-row information-flow audit shows no test row in acquisition. |
| Hidden-label / boundary leakage | PASS | Acquisition signatures use candidate inputs, revealed labels and fitted posteriors only; no hidden labels or B1/B2/B3. |
| Baseline reproduction | PASS | Frozen Margin q20 AULC reproduced at 0.813520; absolute discrepancy from the recorded bootstrap mean is 9.81e-06. |
| Pseudoreplication | PASS | Paired inference resamples 20 repeat blocks with all five folds retained. Random contrasts additionally resample the 30 saved continuations within fold. |
| Mean-Random trajectory error | PASS after correction | Crossing-time claims do not use an averaged synthetic Random trajectory. |
| Same-data calibration optimism | PASS | Screening/calibration use a 405-row ensemble of 20 genuinely held-out predictions per row. Results are labelled retrospective simulator-domain only. |
| Crossing definition | PASS | Stable target requires ≥0.80 for three consecutive declared checkpoints; H160 non-achievers remain censored. |
| Selective reporting | PASS with qualification | Negative 5D, assisted-acquisition, and h-query→4D results are retained. Additive ridge GP is reported as unimplemented future work. |
| Number consistency | PASS after correction | Model horizons, hierarchical bootstrap description, liquidus temperature, figure labels, and the static audit were reconciled with executed artifacts. |
| GPC numerical behavior | QUALIFY | No logistic fallbacks, but kernel-bound hits occur, especially 38/100 static 4D fits and about 14–16% of active 4D checkpoint fits. Discrimination comparisons remain protocol-matched; probability claims are qualified. |
| Historical artifact preservation | PASS | Validation finds no tracked changes under frozen Week 8.5 or existing Week 9 Phase 1 output directories. |

## Strongest attempted falsifications

1. **Could h be called the physical Keyhole number?** No. It retains units and omits absorptivity, material properties, and temperature normalization. Only its process-parameter exponents map to the literature scaling.
2. **Could exponent agreement be a mathematical artifact of standardization?** The implemented recovery uses unstandardized log predictors. The ratios -0.518 and -1.444 have stratified-bootstrap intervals containing -0.5 and -1.5. This supports consistency, not discovery or causality.
3. **Could near-perfect global AUC justify replacing 4D?** No. h has lower full PR-AUC/Brier performance and significantly lower q20 Keyhole recall than 4D GPC.
4. **Could the h-only AULC advantage prove a better acquisition function?** No. That arm changes both model and acquisition, and the advantage is already present at the shared budget-16 design. In the controlled fixed-4D comparison, h-selected queries reduce q20 AULC by 0.0127, with interval [-0.0218,-0.0030].
5. **Could 5D GPC be called physics-informed improvement?** No. `log(h)` is deterministic redundant information; 5D does not improve static or active primary results.
6. **Could the three-zone rule be a safety guarantee?** No. It is OOF retrospective evidence from one simulator/material population, with one Keyhole in the low zone and two Conduction cases in the high zone.

## Claims permitted after review

- h has genuine primary-literature support as the process-dependent part of a fuller normalized scaling.
- The empirical discriminative direction is consistent with the theoretical exponents.
- h captures most global class separation in this fixed simulator population.
- Residual 4D structure matters near Fold-B1-q20.
- The OOF three-zone view remains useful as an exploratory retrospective screening summary.
- A physics-ridge plus residual model is a justified, focused future prototype, not a completed result.

## Claims not permitted

- h is dimensionless or is the complete Keyhole number.
- LS is spot diameter.
- ST is universally irrelevant.
- h is sufficient for the 4D problem.
- h acquisition saves about 45 queries.
- 5D GPC improves sample efficiency.
- a universal numerical h threshold transfers across alloys or machines.
- the screening zones constitute manufacturing safety, CAM approval, or prospective validation.

## Final limitation statement

All numerical inference concerns split stability within one fixed 405-simulation Ti-6Al-4V simulator population. It is not evidence of cross-alloy transfer, experimental validation, causal mechanism identification, or an operational safety guarantee. These limitations are stated consistently in the final report and supervisor summary.
