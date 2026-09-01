# Week 9 Phase 1.10 closure diagnostics

## Frozen result preserved

The predeclared Phase 1.10 bundle-level verdict remains **GENERIC_DIRECTION_SUPERIOR**: Ti64 H−G ROC-AUC = -0.015611, 95% split-bootstrap CI [-0.016686, -0.014536]. These diagnostics qualify interpretation; they do not replace the primary analysis.

## 1. Raw-scale external exponent recovery

For every original grouped training fold, the fitted standardized G coefficients were converted by `beta_j = gamma_j / sigma_j`; the reported exponent is `alpha = beta_VX / beta_P`. Five fold estimates were averaged within each repeat before bootstrapping the 20 repeat blocks. Numerical guards and coefficient signs were audited rather than hidden.

- **Ti64:** mean alpha -1.713000, median -1.640491, 95% split-sensitivity interval [-1.893124, -1.520871], IQR [-1.873436, -1.562556]. Valid/invalid fits: 100/0; beta_P sign flips: 1. Status: **THEORY_OFFSET_RESOLVED**.
- **316L:** mean alpha -1.219531, median -1.277558, interval [-1.459743, -0.905957]. Valid/invalid fits: 99/1; beta_P sign flips: 1. Status: **THEORY_OFFSET_RESOLVED**.
- Descriptive full-data fits only: Ti64 beta_P=3.708437, beta_VX=-5.432137, alpha=-1.464805; 316L beta_P=4.900305, beta_VX=-5.309170, alpha=-1.083437.

The theory reference −0.5 was fixed before fitting. Compatibility means only that −0.5 lies inside a split-sensitivity interval for this logistic separator; it is not exact equality, causal exponent recovery, or proof of a physical law.

## 2. Strict C-versus-K sensitivity

All T/CT/TK rows were removed without remapping. Ti64 retains 48 bundles (26 C, 22 K) across 32 conditions; 316L retains 48 (37 C, 11 K). Both support 20×5 exact-condition-grouped folds with both classes in every held-out fold.

- Ti64 strict H/G ROC-AUC: 1.000000/1.000000; H−G +0.000000 [+0.000000, +0.000000]. Relative to the frozen primary contrast, the absolute gap **shrinks**.
- 316L strict H/G ROC-AUC: 1.000000/1.000000; H−G +0.000000 [+0.000000, +0.000000].

Thus the external physics discrimination is not solely created by merging transition modes into Keyhole. Strict C/K remains a post-hoc label-definition sensitivity and is not identical to the thesis target.

## 3. Regularization sensitivity

Only R1 (`C=1`) and R2 (`C=1e6`) were run. R3 is recorded as **R3_UNAVAILABLE** because `penalty=None` emits a deprecation warning in installed scikit-learn 1.9.0; no library was changed.

- Transition-inclusive Ti64: R1 H−G -0.015611 [-0.016629, -0.014536], alpha -1.713000; R2 H−G +0.014593 [+0.012472, +0.016572], alpha -2.334019.
- Strict Ti64: R1 H−G +0.000000, alpha -1.699646; R2 H−G +0.000000, alpha -1.302044.

The transition-inclusive H−G sign reverses under weak regularization, and alpha moves farther from −0.5. Therefore **G > H is regularization-sensitive**; C=1e6 is a sensitivity, not a replacement or tuned choice, so this does not alter the frozen primary verdict.

## Final interpretation

Phase 1.10 can be closed with a qualified interpretation. The fixed `P*VX^-1/2` direction is a strong independent experimental discriminator, but the generic C=1 separator prefers a materially steeper negative velocity exponent (Ti64 alpha≈-1.713, interval excluding −0.5), not a small adjustment around theory. Removing transitions makes both H and G perfect rankers, so transition handling explains the frozen H–G gap but not the underlying physics discrimination. The G>H advantage also reverses at C=1e6 and is therefore penalty-sensitive. LS is fixed, so `LS^-3/2` remains not testable; no active-learning claim was tested.
