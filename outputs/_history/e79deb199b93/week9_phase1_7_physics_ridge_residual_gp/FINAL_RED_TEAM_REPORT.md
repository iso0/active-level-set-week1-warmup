# Phase 1.7 final adversarial red-team report

## Verdict

**PASS with material qualifications.** The predeclared primary conclusion survives audit: Fold-B1-q20 AULC difference is +0.020018 with repeat-block 95% CI [+0.014071,+0.026264]. No acquisition leakage, split/initial-design drift, additive-kernel error, component-decomposition error, AULC/bootstrap error, or numerical inconsistency was found.

## Checks passed

- Exact 100 frozen splits and 100 feature-only initial designs match Week 8.5.
- Frozen 4D Margin/Random AULCs reproduce at 0.813520/0.776220.
- The custom covariance is genuinely additive: random intercept + linear standardized log(h) + a 4D-only Matérn-3/2 residual.
- Kernel symmetry, positive semidefiniteness and analytic gradients pass numerical tests.
- The recovered latent mean equals `g(log h)+r(x)`; changing only log(h) changes g but not the residual component.
- Flipping every hidden label while holding revealed labels fixed leaves predictions unchanged.
- Acquisition uses only combined-model probabilities on the unqueried training pool; no test row, hidden label, B1/q flag or external h threshold enters selection.
- Inference averages five folds within each repeat and resamples 20 repeat blocks.
- The PASS rule was applied without modification.

## Required qualifications

1. The gain is for the **combined model plus its Binary-Margin policy**, not acquisition alone. At the shared budget-16 design the accuracy advantage is already +0.05294.
2. Budget-40 q20 Keyhole recall difference is +0.01704 with CI [-0.01125,+0.04657]; the associated FN difference is -0.15 with CI [-0.330,+0.0203]. These single-budget missed-Keyhole improvements are descriptive, not resolved.
3. The internal residual mechanism is modest. At budget 40 it corrects 21 and worsens 20 of 1,700 q20 run-fold predictions; it recovers 13 physics-trend Keyhole misses and induces four new misses.
4. The amplitude constraint is material: upper/lower residual-SD bounds are hit in 3395/6500 and 1095/6500 active fits, length-scale bounds in 769/6500, and 4557/6500 fits emit optimizer-bound warnings. No fallback occurs.
5. Since log(h) is algebraically determined by P,VX,LS, the residual can imitate the physics trend. “Physics-dominant” is imposed by the amplitude cap, not identified uniquely from this dataset.
6. All evidence remains retrospective and conditional on one 405-simulation Ti-6Al-4V population.

## Corrections made during review

- Corrected the source docstring from an obsolete Nyström description to the exact Laplace GPC implementation.
- Changed Figure 1 mechanism arrows to compare `sigmoid(g)` with `sigmoid(g+r)`, excluding predictive-variance shrinkage from the displayed residual correction.
- Added lower-bound diagnostics and explicit unresolved-recall language.
- Added five representative residual cases to the report and notebook.

The safe PASS claim in `FINAL_PHASE1_7_REPORT.md` is consistent with these qualifications.
