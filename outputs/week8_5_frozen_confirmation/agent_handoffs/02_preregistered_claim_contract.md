# Week 8.5 preregistered claim contract

Protocol ID: `week8_5_frozen_confirmation_protocol/v1.0.0`
Status: **FROZEN BEFORE CONFIRMATION RUNS**
Scope: confirmatory computation only; no new simulator calls, labels, population rows, target definitions, feature changes, tuning, or post-hoc method selection.

## Locked question and population

On the frozen 405-row `primary_common` population (manual `has_keyhole` ground truth; features `P,VX,LS,ST`, where ST is substrate temperature), does **uncertainty-only Binary GPC margin acquisition** outperform matched Binary Random acquisition on untouched Fold-B1-q20 accuracy? B1/q20/q30 remain evaluation-only flags. The old Phase 6/7/8 data, split manifests, trajectories, model states, and seed namespace are comparison provenance only and are not continuation state.

## Design frozen now

- Create 20 new repeated `StratifiedGroupKFold` partitions, five folds each, grouping exactly by `input_tuple_sha256`: 100 outer training/test runs. Every run gets one shared, arm-blind, deterministic 16-query initial design; it must contain both revealed manual classes and may use only sequentially revealed labels. No test row, hidden pool label/response, or B1/B2/B3 flag may enter selection.
- Primary arms: `binary_margin` versus 30 independently seeded Random continuations per outer run. A Random continuation differs only in its predeclared pool order and shares that run’s split and 16-query design. Binary GPC/kernel/fallback behavior is frozen to the named Week 7 source implementation; no hyperparameter search or restarts are permitted.
- Confirmatory comparator: `binary_uncertainty_repulsion` with exactly `h=0.15`, one trajectory per outer run, versus margin. Its only confirmatory endpoints are AULC 16–80 and low-budget AULC 16–40. Any bandwidth other than 0.15 is exploratory only, clearly labelled, and cannot alter a confirmatory conclusion.
- Primary metric: Fold-B1-q20 accuracy AULC over every integer budget 16,17,…,80, with `trapezoid(accuracy,budget)/64`. This is exactly the historical convention.
- Secondary descriptive/confirmatory records: B1-q20 and B1-q30 accuracy at budget 40; B1-q30 AULC 16–80; B1-q20 persistent crossings at targets .80 (primary) and .75/.85 (sensitivity); B1-q20 recall, balanced accuracy, false negatives, and false positives at budget 40 and the terminal horizon. These do not replace the primary metric.

## Horizon, grid, and censoring

The mandatory grid is 16–80 at step 1. After 80, declared checkpoints are 82,84,…,120 and then 124,128,…,160. All trajectories acquire sequentially through the active horizon, but only the declared checkpoints are used for post-80 crossing summaries. At each horizon H, compute only

`rho_random(H) = (# finite binary_random B1-q20/.80 persistent crossings among 100 × 30 run-continuations) / 3000`.

If `rho_random(80) < .95`, extend **every** arm/continuation uniformly to 120. If `rho_random(120) < .95`, extend every arm/continuation uniformly to 160. Otherwise stop at that horizon. This criterion is computed from Random primary crossings alone; no observed margin, repulsion, AULC, q30, or diagnostic result may affect it.

A crossing is the first declared checkpoint at which the target and the next two declared checkpoints all meet or exceed the target. A trajectory without such a crossing by the active horizon is right-censored at `H+` and is never interpolated or extrapolated. The final report retains censoring indicators and reports `rho_random(H)` before any finite-only summaries.

## Estimands and inference unit

Let `a[r,f,m,c,b]` be untouched-test B1-q20 accuracy; margin and repulsion have `c=1`, Random has `c=1..30`. Let `A16_80` be the mandated normalized trapezoid AULC, and let `A16_40` use the same formula divided by 24. The primary estimand is

`Delta_AULC = mean_{repeat,fold}(A_margin - mean_continuation(A_random))`.

The target-query estimand is the restricted, right-censor-aware burden difference at the final adaptive horizon,

`Delta_Q(H) = mean(min(Q_random,H) - min(Q_margin,H))`,

where `Q` is the persistent .80 crossing and a non-crossing has `min(Q,H)=H`. The multiplier is `M(H)=mean(min(Q_random,H))/mean(min(Q_margin,H))`. These are restricted-horizon estimands, not claims about unobserved query counts. The replicate target-rate and the full right-censored distribution are reported beside them.

Inference uses a fixed 20,000-draw hierarchical repeat-block bootstrap. Resample the 20 repeat IDs with replacement; retain all five folds inside each chosen repeat; within every selected fold resample the 30 Random continuation IDs with replacement; calculate the statistic. The percentile 95% one-sided lower bound is the 5th percentile. Repeats/folds/continuations are not pooled as 100 or 3,000 independent physical campaigns. Claims are about this saved-simulation population and split/acquisition randomness, not causal or physical-boundary certainty.

## Decision ledger

| Claim | PASS | QUALIFY | FAIL |
|---|---|---|---|
| Primary performance | `Delta_AULC` lower 95% bound >= 0.020 | point estimate > 0 but PASS is not met | point estimate <= 0 |
| Query saving | `rho_random(H) >= .95` and lower bound of `Delta_Q(H)` >= 10 queries | lower bound > 0 but PASS is not met, or Random remains censored at H | lower bound <= 0 |
| Multiplier | `rho_random(H) >= .95` and lower bound of `M(H)` >= 1.25 | lower bound > 1 but PASS is not met, or Random remains censored at H | lower bound <= 1 |
| Repulsion h=.15 | simultaneous lower bound for `min(Delta_repulsion_AULC16_80, Delta_repulsion_AULC16_40)` >= 0.010 | both point contrasts > 0 but PASS is not met | either point contrast <= 0 |

`Delta_repulsion` is repulsion minus margin. The simultaneous lower bound is the 5th percentile of the bootstrap distribution of the two-endpoint minimum. Overall primary confirmation is PASS only when performance, query saving, and multiplier each PASS; otherwise report each ledger outcome without upgrading a QUALIFY result to confirmation.

## Seed and artifact contract

Every random state is derived by SHA-256 from the literal namespace `week8_5_frozen_confirmation|v1|...`, UTF-8, first eight digest bytes little-endian modulo `2^32`. Required keys are `outer_split|repeat|NN`, `run|<run_id>|initial_design`, `run|<run_id>|arm|binary_margin|fit|budget|BBB`, `run|<run_id>|arm|binary_random|continuation|CC|order`, `...|fit|budget|BBB`, and `run|<run_id>|arm|binary_uncertainty_repulsion|h|0.15|fit|budget|BBB`. This root and all child labels are disjoint from the old `6022026` / `primary_common` / `shared_pool_permutation` state family. A pre-run seed registry must store each complete key and derived value; complete keys, not 32-bit values alone, identify stochastic states.

Expected artifacts are the canonical protocol JSON and its SHA-256, seed registry, grouped split manifest, initial-design manifest, per-budget trajectory table, checkpoint metrics table, crossing/censoring table, continuation summary, bootstrap draws/summary, decision ledger, validation report, and runtime/compute report. Each must carry protocol ID, source hashes, run ID, repeat/fold, arm, continuation ID where applicable, horizon, and schema version.

## Compute-fit gate

At horizon H, the planned fitted-GPC count is `100 × (1 margin + 30 Random + 1 repulsion) × (H-15) = 3,200(H-15)`: 208,000 at H=80, 336,000 at H=120, and 464,000 at H=160. Before a full run, execute no confirmation result: perform only a code-path/resource smoke estimate on one synthetic/non-result fixture, record measured `seconds_per_fit` and projected wall time `3,200(H-15) × seconds_per_fit / workers`, and fail closed if memory, time allocation, determinism, grouping, or information-flow validation fails. If H=80 does not fit the approved allocation, stop and report a compute block; do not reduce repetitions, continuations, grid points, or change horizon logic. Extension is allowed only by the frozen `rho_random` rule above.
