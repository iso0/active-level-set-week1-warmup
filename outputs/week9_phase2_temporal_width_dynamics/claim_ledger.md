# Phase 2 claim ledger — corrected transverse width

| Claim | Status | Guardrail |
|---|---|---|
| Transverse static width differs by eventual regime | QUALIFIED | Effect size, not standalone classifier claim |
| Transverse temporal profile differs by eventual regime | SUPPORTED | Frozen simulator subset |
| Transverse dW/dt is a robust discriminator | QUALIFIED | Raw versus fixed local-linear gate |
| Transverse width improves hard classification beyond h | NOT SUPPORTED | q20 BA and Keyhole recall primary |
| Transverse width improves ranking/probabilities beyond h | SUPPORTED | q20 ROC, PR and Brier secondary |
| Early prefix gives hard-decision improvement | SUPPORTED | τ=0.20 shown; all prefixes tabulated |
| Early prefix gives ranking/probability improvement | SUPPORTED | Secondary metrics interpreted separately |
| Verified pre-Keyhole warning | NOT SUPPORTED | No trained held-out warning rule; sparse observed onset |
| Longitudinal ΔX behaves differently from transverse ΔY | SUPPORTED | Side-by-side axis audit and summary |
| Top-view monitoring is industrially validated | NOT SUPPORTED | No prospective camera experiment |

## Canonical numbers
- Usable traces: 350/405; Keyhole: 70
- Wmax medians (Conduction, Keyhole): 174.829, 174.535 µm
- WT0 medians (Conduction, Keyhole): 161.118, 158.689 µm
- Best robust/shape temporal feature: robust_median_positive_dWdt_um_per_ms; Cliff's delta -0.2656
- q20 balanced accuracy (h, width dynamics, h+width): 0.8210, 0.5054, 0.8009
- q20 Keyhole recall (h, h+width): 0.7305, 0.6676
- q20 ROC/PR/Brier contrasts (h+width minus h): +0.0016, +0.0202, -0.0011
- τ=0.20 q20 BA/ROC/PR/Brier contrasts: +0.0185, +0.0058, +0.0186, -0.0043
- Final Phase 2 claim: INCREMENTAL / QUALIFIED SIGNAL; hard-decision NOT SUPPORTED; ranking/probability SUPPORTED
