# Week 9 Phase 1.5 — final forensic confirmation

## Executive decision

`h=P/sqrt(VX·LS^3)` is a legitimate physics-inspired coordinate because its process exponents match Gan et al.'s Keyhole-number scaling when `LS` is the Gaussian spot radius. Bare `h` is dimensional and is not the full Keyhole number. Empirically it compresses most global discrimination into one coordinate, but measurable residual 4D structure remains near Fold-B1. Canonical 4D Margin remains the best verified acquisition policy for learning that 4D structure.

## Answers to the requested questions

1. **Physically supported?** Yes, as the process-dependent part of a material-normalized scaling; not as a standalone dimensionless number.
2. **Exponent agreement real?** Consistency is strong: VX/P -0.518 [-0.659,-0.381], LS/P -1.444 [-1.995,-1.074]. It is not independent discovery or proof.
3. **Nearly sufficient globally?** Nearly, but not fully. `log(h)` ROC-AUC 0.9897 versus 4D GPC 0.9926; PR-AUC 0.9501 versus 0.9683.
4. **Near-boundary degradation?** On q20, h Keyhole recall 0.710 versus 4D GPC 0.732; the paired h-minus-4D interval excludes zero for recall.
5. **Does ST add anything?** The predeclared partial `h/(1933-ST)` sensitivity, using Gan et al. Supplementary Table 3, is worse than bare h in this 300–400 K domain. This does not establish universal ST irrelevance.
6. **Does h improve GPC?** No verified gain. 5D-minus-4D full ROC-AUC is -0.000417; Brier is worse by +0.000584.
7. **Does h improve acquisition?** No fixed-model acquisition improvement was shown. The composite h-only model/policy has q20 AULC +0.0182 versus 4D Margin, but that comparison changes both model and acquisition and its advantage is already visible at the shared budget-16 design. The controlled fixed-4D comparison shows h queries significantly hurt the 4D GPC.
8. **Does pure h acquisition harm 4D exploration?** Yes: the same h-selected queries give the 4D GPC -0.0127 AULC versus 4D Margin, CI [-0.0218,-0.0030].
9. **Physics ridge + residual?** Scientifically plausible because h captures dominant variation and the 4D model recovers some OOF ensemble errors, but per-repeat residual stability was not separately established. No additive GP was implemented; it remains a focused next-step prototype.
10. **Three-zone screening?** It survives as retrospective simulator-domain screening: low zone 295 rows with one Keyhole (NPV 0.9966); high zone 48 with two Conduction (PPV 0.9583). It is not a safety or CAM-approval rule.
11. **Antigravity correct:** physical exponent family, strong 1D global discrimination, interesting OOF screening potential, and the need to inspect physics-informed acquisition.
12. **Antigravity wrong/overstated:** LS as diameter, h as dimensionless, universal thresholds, same-data screening confidence, hidden-label threshold acquisition, and ~45-query headlines.
13. **Core slides:** theory/empirical exponent figure; static/boundary comparison; active q20 curves emphasizing h-model gain versus h-query→4D loss.
14. **Appendix only:** calibration bins/zones, residual maps, physical-score candidates, H160 censoring details, 5D and uncertainty-product negatives.
15. **Most promising Phase 2 method:** a preregistered additive physics ridge plus lower-amplitude 4D residual GP, compared directly with canonical 4D Margin. It is a proposal, not a Phase 1.5 result.

## Calibration and limitations

OOF Brier is 0.0294, ECE 0.0187, and MCE 0.3590 using ten fixed equal-width bins. MCE is driven by a sparse worst bin, so it is not inconsistent with low weighted ECE. All inference describes one fixed 405-run Ti-6Al-4V simulator population and split stability; it is not prospective experimental, cross-alloy, causal, or safety validation.

All saved GPC fits optimized without fallback, but kernel-bound hits were non-negligible: 4D static 38/100 and the full table is in `gpc_kernel_bound_diagnostics.csv`. This does not invalidate protocol-matched comparisons, but it qualifies GPC probability/calibration interpretation and motivates a future kernel-sensitivity check rather than stronger claims here.
