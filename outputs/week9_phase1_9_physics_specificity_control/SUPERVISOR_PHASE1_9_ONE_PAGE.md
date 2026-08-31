# Week 9 Phase 1.9 — supervisor one-page

## Frozen-path control

All three prediction models use the exact same canonical 4D Margin query path A0. No new query trajectory was generated. The only new arm replaces the one-dimensional fixed h trend by standardized `log P`, `log VX`, `log LS`, and `ST`; the residual Matérn-3/2 GP and its bounds remain unchanged.

## Primary Fold-B1-q20 AULC, budgets 16–80

- Generic G10: **0.812049632**.
- Physics Y10: **0.829972426**.
- Physics minus generic: **+0.017922794**, grouped 95% CI [+0.013441981, +0.022725299].
- Generic minus canonical 4D: **-0.001470588**, grouped 95% CI [-0.005712431, +0.002605813].
- Decision: **PHYSICS_SPECIFIC_SUPPORTED**.

At budget 16, q20 accuracy is 4D=0.731765, generic=0.722941, physics=0.784706. The generic trend does **not** reproduce most of the Phase 1.7 gain: its AULC contrast against 4D is statistically unresolved and slightly negative in mean.

## Optimization diagnostic

Residual-SD upper-bound fractions are generic=0.916 and physics=0.151; convergence-warning fractions are 0.987 and 0.573. This is descriptive, not causal and not a tuning result.

## Safe thesis claim

On the frozen simulator benchmark, the low-data benefit is not explained solely by adding a flexible parametric trend; alignment with the literature-supported h direction provides a statistically resolved additional advantage.
