# Week 14 confirmatory benchmark freeze

This document and the code it references are committed **before** any held-out synthetic family or
any Week 14 real-data check is executed. It must not be edited after results are seen; deviations
will be reported as deviations.

## Code (exact files at the freeze commit)

`src/week14_order.py`, `src/week14_discovery.py`, `src/week14_models.py`, `src/week14_monotone_gp.py`,
`src/week14_transfer_study.py`, `src/week14_metric_confirm.py`, `src/week14_real_checks.py`,
`src/week13_boundary_metrics.py` (unchanged), `src/week14_metrics.py` (`weighted_edge_metrics`), `src/week13_synthetic*.py`.

## C1 — discovery, held-out synthetic families

Command: `python -m src.week14_discovery --reps 100 --tag confirm --families
heldout_mono_curved,heldout_branin,heldout_hartmann,heldout_rotated_mono,heldout_twoislands_skew`
Cells: d ∈ {2,4,6} (Hartmann: 4,6), n ∈ {108,324}, prevalence ∈ {0.03,0.08,0.15},
design ∈ {uniform, skewed, clustered}, 100 reps; seeds `[14, family index, d, n, 1000·prev, design index, rep]`.
Strategies: RAND, MAXI, SCORE, FRONT, ADAPT8, HEDGE (MAXI+FRONT+SCORE), HEDGE_FR (FRONT+RAND); order
signs (+,−,−,0,…); score = signed sum. Outcome: T_both.

Pre-registered predictions:
- **P1 (theorem check).** heldout_mono_curved: T_both(FRONT) ≤ n_min + n_max in 100% of pools.
- **P2.** heldout_mono_curved: mean T_both FRONT < MAXI < RAND in every (d, n) cell.
- **P3 (theorem check + practical).** Every held-out pool: T_both(HEDGE_FR) ≤ 2·min(T_both(FRONT),
  T_both(RAND)). Every held-out family: mean T_both(HEDGE_FR) ≤ 1.5 × mean T_both(RAND).
- **P4.** In at least one non-monotone held-out family, mean T_both(MAXI) > mean T_both(RAND).

## C2 — models under shift, held-out synthetic families

Command: `python -m src.week14_transfer_study --reps 30 --tag confirm --families
curvedMono,hartmannDev,twoRegimeST --models H,M3,G3,G3S,G3C,GR,GRC`
Settings transfer / target40 / target80 / indomain80; label noise σ = 0.5; seeds
`[41, family index, setting index, rep]`.
Primary contrast: **G3C − G3** (balanced accuracy on the 136/405 evaluation pool). Secondary: NSD₀.₁,
ASSD, minority recall, BEF1; M3 − G3; G3S − G3.

- **P5.** Mean G3C − G3 BA ≥ 0 in every family × setting cell; no cell below −0.01; in curvedMono the
  paired bootstrap 95% CI excludes 0 in ≥ 50% of the shifted cells (transfer, target40, target80).
- **P6.** M3 BA < G3 BA in a majority of the 9 shifted cells; M3 BA ≥ G3 BA − 0.005 in indomain80.

## C3 — metrics, held-out shapes and densities

Command: `python -m src.week14_metric_confirm`. Shapes sphere (d = 3, 6; radius set for 10% uniform
volume), two-component (d = 3); densities uniform / denseA / denseB / clustered; noise 0 / 0.02;
n 136 / 405; 30 reps.

- **P7a.** Density sensitivity |sectorA − sectorB| under denseA/denseB is smaller for gabriel_wBER than for
  gabriel_BER in every (d, shape, density) cell.
- **P7b.** Mean Spearman ρ with −ASSD across predictors: gabriel_wBEF1 ≥ q20_accuracy in every
  (shape, d, density) cell.

## C4 — real data (executed after C1–C3; never used to change any choice)

Command: `python -m src.week14_real_checks --part all`.
- **R1 (POST-HOC NEW).** FRONT and HEDGE_FR on the 100 original NEW training pools: prediction
  max T_both(FRONT) ≤ 16 (i.e. the Week 11 single-class B16 STOP would not have occurred).
- **R2 (EXTERNAL).** Masinelli Ti64 and 316L with minority subsampled to K ∈ {1,2,3}: mean T_both(FRONT)
  < mean T_both(RAND) for each material and K.
- **R3 (EXTERNAL).** Ti64↔316L transfer and within-material n ∈ {10, 20}: report G3C − G3 and M3 − G3.
- **R4 (HISTORICAL OLD).** Week 8.5 splits, full training pool: |G3C − G3| BA ≤ 0.01 (no in-domain harm).
- **R5 (POST-HOC NEW).** OLD→NEW strict transfer and NEW-only 100 partitions: G3C − G3 reported with
  closure coverage and closure error counts.
- **R6 (POST-HOC NEW).** Week 12 paths rescored with wBER/wBEF1; descriptive only.
- **R7.** Proposition I1 on OLD and NEW rare classes.

## Failure handling

Every fit failure is retained (`ok = False`). No rep, seed, cell or family is removed. If a prediction
fails it is reported as failed.
