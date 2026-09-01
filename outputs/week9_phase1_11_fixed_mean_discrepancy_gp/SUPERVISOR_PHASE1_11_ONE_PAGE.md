# Supervisor Phase 1.11 — one page

**Decision:** FIXED_MEAN_SUPPORTED

- q20 AULC: M2 0.8302; M0 0.8135; M1 0.8300; h-only 0.8308.
- M2−M0: +0.0167 [+0.0102, +0.0230].
- M2−M1: +0.0003 [-0.0014, +0.0023].
- M2−h-only: -0.0006 [-0.0024, +0.0014]; the discrepancy adds no resolved predictive gain beyond h-only.
- Residual-SD any-bound rate: M1 51.0%; M2 28.1%.
- B16 q20 Keyhole recall: M0 0.497; MH 0.719; M1 0.722; M2 0.719.
- Fallbacks were 0%; M2 optimizer non-convergence flags occurred in 5.8% of fits.

All models saw identical A0 prefixes. The mean was learned from revealed labels only and frozen during GP fitting. M2 is cleaner than M1 on residual-SD bounds, but h-only remains the simpler equally predictive comparator. The residual still sees P, VX and LS, so orthogonality/identifiability is not claimed.
