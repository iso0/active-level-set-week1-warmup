# Week 6 Phase 2 GP response-noise comparison

## Scope and input

The corrected 241-row Phase 1 ledger at immutable Hugging Face revision
`0e859b748fdbc8454f66e58e101e333ac0479d42` was used unchanged. Inputs are exactly `[P, VX, LS, ST]`.
Targets are width, length, and penetration depth converted from metres to
micrometres without redefining their Phase 1 selected-window median rule.

All models use `ConstantKernel × isotropic Matérn 3/2`, L-BFGS-B, one
deterministic extra restart, exact simulation-level LOO, and fold-local X/y
scaling.

## Primary 241-simulation LOO metrics

| Target | Method | MAE µm | RMSE µm | R² | nRMSE | Mean NLPD | Latent cov. | Obs./oracle cov. |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| depth | A_tiny_jitter | 3.016 | 4.956 | 0.917 | 0.0463 | 5.199 | 0.975 | n/a |
| depth | B_learned_nugget | 2.362 | 4.596 | 0.929 | 0.0429 | 3.037 | 0.925 | 0.967 |
| depth | C_heteroskedastic | 2.533 | 4.091 | 0.943 | 0.0382 | 3.255 | 0.929 | 0.929 |
| length | A_tiny_jitter | 15.074 | 25.739 | 0.919 | 0.0602 | 5.377 | 0.934 | n/a |
| length | B_learned_nugget | 10.623 | 19.389 | 0.954 | 0.0453 | 4.472 | 0.884 | 0.954 |
| length | C_heteroskedastic | 15.046 | 25.688 | 0.919 | 0.0601 | 5.365 | 0.934 | 0.934 |
| width | A_tiny_jitter | 4.522 | 8.037 | 0.954 | 0.0472 | 3.742 | 0.934 | n/a |
| width | B_learned_nugget | 3.274 | 6.696 | 0.968 | 0.0393 | 3.574 | 0.876 | 0.963 |
| width | C_heteroskedastic | 4.521 | 8.037 | 0.954 | 0.0471 | 3.742 | 0.934 | 0.934 |

Approach A's NLPD uses latent variance. Approach B uses total variance including the
learned effective nugget. Approach C uses the explicitly labelled retrospective oracle
variance; that oracle interval is not deployable for a new simulation.

## Preferred observation treatment

- **width:** `B_learned_nugget` (robust paired-RMSE advantage).
- **length:** `B_learned_nugget` (robust paired-RMSE advantage).
- **depth:** `C_heteroskedastic` (numerical preference; paired uncertainty overlaps zero).

## Learned effective nugget

- **width:** median effective-nugget std 6.1849 µm; median fraction of fold training target std 0.1650; noise-bound hits 0/241.
- **length:** median effective-nugget std 16.1710 µm; median fraction of fold training target std 0.1786; noise-bound hits 0/241.
- **depth:** median effective-nugget std 3.7879 µm; median fraction of fold training target std 0.2201; noise-bound hits 0/241.

The nugget is an effective discrepancy term, not stochastic simulator noise.

## Observation-specific target-summary uncertainty

- **width:** bootstrap std median 0.0309 µm, q95 0.2647 µm, max 2.8321 µm.
- **length:** bootstrap std median 0.2194 µm, q95 0.7646 µm, max 3.2622 µm.
- **depth:** bootstrap std median 0.0076 µm, q95 0.5330 µm, max 1.9971 µm.

These values come from 500-resample circular moving-block bootstraps and are not
measurement-noise estimates.

## Paired conclusions

3/9 paired RMSE-difference intervals include
zero. Method superiority is not claimed for comparisons whose interval crosses zero.

## Stable-window sensitivity

- **width:** not material under the 5% RMSE rule.
- **length:** not material under the 5% RMSE rule.
- **depth:** material (≥5% RMSE change).

The 11 flagged simulations remain in the primary analysis and are not automatically
treated as invalid.

## Validation and readiness

24/24 automated checks pass.
The dataset is ready for later feature-effect analysis only under the target-specific
preferred observation treatments and the caveats above. No active learning or
level-set estimation was performed.



## Phase 2.5 addendum — matched stable-depth B/C closure

Phase 2.5 reran only penetration-depth Methods B and C on the same 230 stable
simulation IDs with identical fold ordering, fold-local scaling, seed logic,
kernel bounds, optimizer, and restart count. Historical Phase 2 results above
remain unchanged.

Decision: **B is preferred for stable-window penetration depth.**

`MAE_C − MAE_B = +0.274396 µm`
(95% paired-bootstrap CI
`[+0.134941,
+0.422091]`);
`RMSE_C − RMSE_B = +0.284855 µm`
(CI `[+0.048306,
+0.549011]`).

Runtime metadata correction: the historical `full_pipeline_runtime_seconds`
value is preserved but deprecated. It measured a cached pre-report invocation,
not the original end-to-end experiment. Its authoritative descriptive name is
`cached_artifact_assembly_figure_and_validation_runtime_seconds`. Full provenance is in
`outputs/week6_02_5_depth_model_closure/runtime_provenance.json`.

Phase 3, feature-effect analysis, active learning, and level-set estimation
remain deferred.
