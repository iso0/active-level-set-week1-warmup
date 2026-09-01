# Supervisor one-page — Week 9 Phase 1.10

## What was tested

On Masinelli et al.'s independent experimental LPBF data, we compared a fixed physics direction `log h = const + log P - 0.5 log VX` with a generic two-slope `[log P, log VX]` logistic model. The target is transition-inclusive post-mortem morphology, so this is independent but non-identical validation.

## Data and fairness

- Ti64 (primary): 60 bundles, 38 unique conditions, 26 Conduction / 34 Keyhole; two repeated conditions have conflicting binary labels.
- 316L (secondary): 60 bundles, 38 conditions, 37 / 23; no binary-discordant condition.
- 20 × 5 grouped OOF; exact `(P,VX)` repeats never cross folds; complete 60-bundle OOF vector scored per repeat.
- `LS=25 µm` radius from the reported 50 µm `1/e²` diameter. Because LS is constant, only the `P*VX^-1/2` direction—not the LS exponent—is tested.

## Primary Ti64 result

- H: ROC-AUC 0.9765; PR-AUC 0.9842; balanced accuracy 0.9226; Keyhole recall 0.9029; Brier 0.0741.
- G: ROC-AUC 0.9921; PR-AUC 0.9937; balanced accuracy 0.9503; Keyhole recall 0.9294; Brier 0.0640.
- H−G ROC-AUC: -0.0156, 95% split-bootstrap CI [-0.0167, -0.0145].
- Secondary GPC ROC-AUC: 0.9896.

Verdict: **GENERIC_DIRECTION_SUPERIOR**. `h` is strongly discriminative, but fixing the −1/2 velocity exponent loses a small, stable amount relative to the generic two-slope model.

## Robustness and 316L

Excluding the two discordant Ti64 conditions raises H/G ROC-AUC to 0.9958/0.9970; H−G becomes -0.0012 [-0.0027, +0.0002], unresolved. In 316L, H/G ROC-AUC are 0.9912/0.9959; H−G -0.0047 [-0.0078, -0.0015].

## Safe conclusion

The physics-aligned direction transfers as a strong experimental discriminator, not as the optimal or universal law. The generic direction is better on the primary bundle-level protocol; the gap is largely attenuated when discordant repeated conditions are excluded. External AL replay is feasible but should be exploratory, not the next confirmatory claim.
