# Supervisor one-page — Phase 1.19A

- **Integrity:** 405 rows (73 KH / 332 C), with exact configuration counts CFG_MAIN=364, CFG_NEGATIVE_XI_SHORT=27, CFG_POSITIVE_XI_SHORT=14. 167 rows end before 90% verified x-domain traversal; no row was relabelled.
- **Main-only check:** H: balanced accuracy 0.9348; ROC-AUC 0.9914; G3: balanced accuracy 0.9532; ROC-AUC 0.9923; M3: balanced accuracy 0.9456; ROC-AUC 0.9947. M3 leads ROC-AUC/Brier; G3 leads balanced accuracy/Keyhole recall, so the conclusion is metric-dependent rather than reversed wholesale.
- **Depth:** 39 rows (39/73 KH) form a label-free terminal depth pile and should be treated as likely lower-bound/censored continuous depths.
- **Stage 1:** B16 median coefficient 20.978; exact separation 55.0% at B16, 39.0% at B20, 9.0% at B24. H/M3 B16 Brier 0.0483/0.0489.
- **Monotonicity:** 3/22,050 full-pool violations; 3/19,491 main-only. Hard implication still makes errors, so future use must be soft.
- **Decisions:** CONFIGURATION_SENSITIVITY_REQUIRED; DEPTH_CENSORING_CONFIRMED; STAGE1_OVERCONFIDENCE_MIXED; MONOTONIC_STRUCTURE_STRONG.
- **Next:** NEXT_MONOTONE_POOL_LSE.
- **Claim limit:** diagnostic evidence only; no new active-learning/sample-saving result.
