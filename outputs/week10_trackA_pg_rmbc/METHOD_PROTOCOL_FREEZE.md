# Week 10 Track A — PG-RMBC method protocol freeze

Protocol ID: `week10_trackA_pg_rmbc/v1.0.0`  
Project: `week10-pg-rmbc-internal-replication`  
Frozen at (UTC): `2026-09-20T21:46:14.616686+00:00`  
Status: **FROZEN BEFORE FULL TRAJECTORIES**

`HISTORICAL_GATES.md` passed before this freeze. No Ioan/new-pool file was opened or read. The experiment below uses only the frozen 405-simulation internal benchmark. No post-result method change or additional arm is permitted.

## Fixed data and replication design

- Population: the same 405 rows (73 Keyhole, 332 Conduction), manual `has_keyhole` ground truth.
- Split generator: frozen Week 8.5 `StratifiedGroupKFold` generator.
- New internal repeat block: repeats **121–180**, fixed now; 60 repeat blocks, five paired folds each, 300 outer runs per policy.
- Inferential unit: repeat block after averaging its five folds. Folds are not independent units.
- Budgets: B16–B80 inclusive. q20 is primary; q30 remains secondary.
- Evaluator: exact M3 — revealed-prefix logistic mean on exact frozen `log h`, plus 4D ARD Matérn-3/2 discrepancy; refit at every budget.
- Numerical environment: single-thread BLAS variables fixed before scientific imports.

## Exact physics and geometry

`log h = log P - 0.5 log VX - 1.5 log LS`. Exponents are fixed; ST is absent from `h`.

The Phase 1.21 boundary band is reproduced exactly from revealed labels: endpoints are the lowest revealed Keyhole `log h` and highest revealed Conduction `log h`, sorted; padding is `max(0.05, 0.25 * width)`. Empty band falls back to plain M3 probability margin. Coverage is standardized `[P,VX,LS,ST]` Euclidean distance to the nearest queried row, with the scaler fitted label-blind on the outer training pool. Rank normalization reuses Phase 1.21 stable ordinal `_rank01` exactly.

## h-maximin seed

On each outer training pool, order rows label-blindly: smallest `log h`, largest `log h`, then the row maximizing distance to the nearest selected `log h`; every tie is resolved by the smaller population row index. Reveal along this fixed order until both observed classes exist. No pseudo-label is created. If an effective seed ever exceeds B16, the study fails validation because the common B16 metric grid would be unavailable; this is a predeclared integrity condition, not a tuning rule.

## Soft monotone leverage

`j` is more Keyhole-prone than `i` iff `P_j >= P_i`, `VX_j <= VX_i`, `LS_j <= LS_i`, with at least one strict inequality. ST is excluded.

At each acquisition step, the relevant set is exactly the unqueried outer-training candidates inside the current boundary band. For candidate `x` in that set:

- `G_KH(x)` counts other relevant candidates strictly more Keyhole-prone than `x`;
- `G_C(x)` counts other relevant candidates strictly more Conduction-prone than `x`;
- `M(x) = min(G_KH(x), G_C(x))`.

The PG-RMBC score is `rank(U) + rank(C) + rank(M)`, where `U=1-2|p_M3-0.5|`. All weights are one. Final score ties use the smaller population row index. Counts affect query priority only: they create no labels, remove no candidates, resolve no rows, enter no M3 fit, and never replace simulator truth.

## Adaptive switch

After both classes exist, revealed labels are h-separable iff `max(log h | revealed Conduction) < min(log h | revealed Keyhole)`. P4 uses RMBC while separable. The first newly queried real label that makes this false records the adaptive-switch budget; every subsequent query uses plain M3 probability margin permanently. There is no patience and no switch-back.

## Exactly five policies

1. P0: M3 margin + frozen B16 feature-maximin seed.
2. P1: exact frozen Phase 1.21 `early8__coverage_then_margin_B40` benchmark.
3. P2: h-maximin-until-both seed + exact Phase 1.21 coverage-until-B40, then margin.
4. P3: Phase 1.21 early8 seed + RMBC until B40, then margin.
5. P4: h-maximin-until-both seed + RMBC while h-separable, permanent margin after first observed violation.

No sixth arm or parameter search may be added.

## Endpoints and inference

Primary endpoint: q20 accuracy normalized trapezoidal AULC B16–B40. Primary contrast: P4−P1. Also predeclared in one Holm family: P2−P1, P3−P1, P4−P0. Paired deterministic percentile bootstrap uses 20,000 repeat-block draws; deterministic two-sided sign-flip Monte Carlo uses 100,000 draws. Positive-repeat counts are reported.

Secondary endpoints: q20 accuracy B16–B80; q20 balanced-accuracy B16–B40 and B16–B80; q20 Keyhole-recall AULC; q30 accuracy AULC; full81 accuracy AULC; B24/B32/B40/B80 checkpoints; q20 Keyhole recall and false negatives at B40; full81 accuracy at B80.

P4 classification is fixed:

- `PG_RMBC_IMPROVEMENT_SUPPORTED` only if P4−P1 mean >0, lower 95% interval >0, mean >=+0.005, B40 q20 KH-recall difference >=−0.03, B80 full81 accuracy difference >=−0.01, and all leakage/safety checks pass.
- positive interval but mean <+0.005: `SMALL_INTERNAL_GAIN`.
- interval includes zero: `NO_CLEAR_IMPROVEMENT`.
- either guardrail or leakage/safety failure: `REJECT_FOR_SAFETY_OR_ROBUSTNESS`.

The final policy decision is exactly one of `FREEZE_PG_RMBC_FOR_EXTERNAL_TEST`, `KEEP_PHASE121_CANDIDATE_B`, or `REJECT_PG_RMBC_FOR_SAFETY_OR_ROBUSTNESS`.

## Diagnostics, non-causal decomposition, and claim boundary

The frozen diagnostics are seed size, first-both-classes budget, adaptive-switch budget, h-separability fractions at B16/B20/B24/B32/B40, early band-query fraction, selected U/C/M and G counts, path Jaccard against P1, q20 FP/FN curves, and a probability-order disagreement score that is never an acquisition input. Algebraically: `P4−P1 = (P2−P1) + (P3−P1) + remainder`; the remainder is labelled adaptive/interaction and is not a causal percentage. P4's adaptive-switch contribution is not separately identifiable from the five arms.

Sample efficiency reports first crossing of P1's mean q20 accuracy at P1 B24/B32/B40, descriptively only. No external validation, universal monotonicity, theoretical complexity, guaranteed savings, exact physical boundary, industrial safety, or novelty claim is allowed.

## Frozen source and input hashes

- `src/week8_5_frozen_sample_efficiency_confirmation.py`: `cb63cd474817a91a755d779d8a0f4ad5337ab51a0778f3bc1788c3f6d943b60c`
- `src/week9_phase1_7_physics_ridge_residual_gp.py`: `74ca6376daa3da00d6578d7d48078fb60c7e017dae2bf209e79a3a018704ba92`
- `src/week9_phase1_11_fixed_mean_discrepancy_gp.py`: `cfbbbd4a8ddcdf88d04467b64c3908489c49265cedac1292bb77baa2cd8fc0e5`
- `src/week9_phase1_13_fixed_physics_ard_discrepancy.py`: `03928c4dbb11a1b925586443b7c9ace61e1ca0164782e3af7fa1b7401bffb0ba`
- `src/week9_phase1_20_acquisition_search.py`: `a47a4c2a872bda39da0ef1415360447d9fafb570c603cf3e6687ead5681a26b2`
- `src/week9_phase1_20_early_start.py`: `5a515d6c89d2a4c547f005fd58067d7385b2343795d136ac26b23bf8501b9a43`
- `src/week9_phase1_21_simplification_replication.py`: `b7c436e88c15cb569c4c5f8cf2f26f3c2742f436da403c8c4b6fce85386d19c9`
- `outputs/week7_06_real_data_boundary_active_level_set/primary_common_population.csv`: `c15658cac87a8616a1984185ec1afc8126a1db811f0d5819e62cfb621a7486c7`
- `outputs/week9_phase1_21_simplification_replication/FINAL_POLICY_FREEZE.json`: `84be2a270aaba453321c4a20a1603ec7834fb4de41afd5d48347bf78070be631`
- `src/week10_trackA_pg_rmbc.py`: `f2ef592cc17b60c0c175fc553f723ce9e17eac3a1b99ee3fbf95908801b9f93e`
- `src/tests/test_week10_trackA_pg_rmbc.py`: `ce2b100d756eb4b2b0c7f9329b54a083360ff6cbf6789d57bc460c39c1334fd8`
