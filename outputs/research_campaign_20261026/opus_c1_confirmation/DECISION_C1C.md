# C1C use decision

The decision follows the mapping that was registered before any result (`PROTOCOL_C1C.md` §7). Its inputs:
- the verdicts of the 80-repeat main validation (STD 203–282, 400 learners, own paths);
- the startup rule (RAND8 283–302, LOCAL8 303–322);
- the prior rule (DEV paths 123–162).

Full tables: `evaluation/RESULTS_C1C.md`; data: `evaluation/C1C_DECISION.json`.

## 1. Registered outcomes

Unless noted, each row is C1 + margin minus HA_LEAN + margin, 80 clusters, one-sided 95 % bounds.

| item | result | status |
|---|---|---|
| early BA-AULC B8–B24 | +0.0053 [+0.0039, +0.0068], 59/80 clusters positive | **EARLY_GAIN_SHOWN + PRACTICAL**: replicated (EA: +0.0056) |
| 0.90 restricted-mean saving | +0.38 [+0.15] simulations | SAVING_SHOWN |
| 0.93 restricted-mean saving | +1.09 [+0.42] | **SAVING_SHOWN + PRACTICAL** (EA had NOT_WORSE, +0.61) |
| 0.95 restricted-mean saving | +1.81 [+0.53, +3.09] | **SAVING_SHOWN + PRACTICAL**: replicated (EA: +2.00) |
| 0.95 reliability | Δattain +0.040 [+0.011]; Δkept +0.015 [−0.016] | **RELIABLE** |
| late BA-AULC B28–B60 | −0.0006 [−0.0013, +0.0002] | NO_LOSS_SHOWN and **PRESERVED_WITHIN_0.003** |
| harm limits | ΔLL B8–B60 +0.0025 (limit 0.030); ΔBrier −0.0001 (limit 0.010); CPU 1.19× (limit 3×) | met |
| startup rule | early STARTUP_CONSISTENT (RAND8 +0.0055 [+0.0025]; LOCAL8 +0.0087 [+0.0041]); 0.95 saving NO_CONTRADICTION (RAND8 +2.12; LOCAL8 +3.33 [+0.50]) | consistent |
| prior rule | early vs A: SD × 0.5 +0.0055 [+0.0042]; SD × 2 +0.0047 [+0.0035] | **PRIOR_ROBUST_EARLY** |

## 2. Decision (registered mapping applied)

1. **Early, fixed-small-budget use (B8–B24): C1 + margin is recommended in this pool.**
   - The pool is the 541-run pool. The recommendation holds for the standard, random and clustered startups, and it is not tied to the exact prior width.
2. **Stop-at-0.95 use: C1 + margin is recommended in this pool.**
   - It reaches BA 0.95 with fewer simulations (restricted-mean +1.8) and is non-inferior in attaining and keeping 0.95, within 5 points.
   - RELIABLE is a non-inferiority statement. It is not superiority and it is not a per-run guarantee: 65 of 400 C1 learners reached 0.95 and fell below it again by budget 60 (A: 55).
3. **0.90 / 0.93 use:** C1 + margin needs fewer simulations, shown at both targets.
4. **Late / full-budget use:**
   - Late performance is preserved within 0.003 BA. This is more than "no loss shown", but it is not a late gain.
   - At budget 60, BA is equal: 0.9568 vs 0.9569.
5. **Recommended in-pool learner: C1 + margin.** Every registered condition holds:
   - early shown, 0.95 saving shown, RELIABLE;
   - no late loss, harm limits met;
   - startup consistent, prior robust.

   **HA_LEAN + margin** stays the frozen reference arm of the thesis comparisons and the extrapolation-safe choice (§4).
6. **This validation branch is complete.** No further seeds or variants are run. The next step is external data (`EXTERNAL_VALIDATION_PLAN_C1C.md`).

## 3. Caveats

These are reported beside the registered decision. They do not change it.

- **Sustaining 0.95 did not improve.**
  - Δsustained(0.95) −0.007 [−0.044, +0.029]; the EA value +0.055 did not replicate.
  - Lost after attainment: 65 (C1) vs 55 (A).
  - The 0.95 claim is about reaching the target sooner or more often, not about staying above it.
- **The 0.95 saving comes mainly from more learners attaining**, not from faster attainment among learners that attain under both:
  - both 300, C1 only 35, A only 19, neither 46;
  - the both-attained saving is +0.66 [−0.28, +1.60], not shown;
  - cumulative attainment of 0.95 at b = 16 / 24 / 60: 0.390 / 0.575 / 0.838 (C1) vs 0.335 / 0.532 / 0.797 (A).
- **Subgroups.** The 40-repeat subgroups differ, as expected at this size:
  - S1 (203–242): 0.95 saving +1.25 [−0.31], not shown;
  - S2 (243–282): +2.37 [+0.30], shown.
  - The early gain is shown in both: +0.0055 and +0.0052.
- **Alternative startups:** 0.95 keeping is not shown, so the RELIABLE verdict belongs to the standard maximin startup.
  - Descriptive results (20 clusters each): RAND8 Δkept −0.030 [−0.098]; LOCAL8 −0.040 [−0.099].
  - Lost after attainment: 13 vs 8 (RAND8) and 17 vs 7 (LOCAL8).
- **Log loss.**
  - Over B8–B60 on own paths, a small increase is shown: +0.0025 [+0.0010, +0.0040], within the harm limit.
  - It is a path effect. On HA_LEAN's path, C1 has lower log loss than A (−0.0009). On C1's own path, HA_LEAN's log loss rises too (+0.0076).
  - The early log loss is lower: −0.0040.
- **Against the strong early control D** (HA_LEAN selects / HA_TREND predicts):
  - C1 + margin's own-path early advantage is not shown: +0.0011 [−0.0002].
  - On identical paid data, C1 improves on D in every window, so C1 keeps D's early gain without D's late loss and log-loss penalty:
    - early +0.0015 [+0.0010];
    - late +0.0008 [+0.0005];
    - log loss −0.0070 [−0.0074, −0.0066], lower in all 80 clusters;
    - 0.95 saving +1.46 [+0.58].
  - D itself shows a late loss again: −0.0014 [−0.0019, −0.0010].
- **The prior was chosen in EA after the full-pool ML-II diagnostics had been seen.**
  - The width controls show that the early gain does not hinge on the width.
  - New splits of the same 541 runs cannot remove this design effect.
  - SD × 0.5 looked better on the DEV paths (log loss −0.0026 vs A; 0.95 cross-path +1.71), but by protocol it is not adopted.

## 4. When HA_LEAN + margin is the safer reference

- **Extrapolation to an input region not covered by the paid runs.** The EA K5 geometric-block result stands: C1 − A per-region BA-AULC −0.049, LCB −0.072. No new geometric split was made.
- **When the goal is to stay at or above 0.95 through the whole budget**, or when the startup is not the standard maximin start. Keeping and sustaining were not improved, and they were not shown non-inferior under other startups.
- **As the frozen comparison reference** for all earlier thesis results. It keeps every earlier comparison reproducible.

## 5. Claim boundaries

- **All results are pool-only.** Every ID is a new split or startup of the same 541 runs, the pool the method was developed on. None is external validation.
- **No methodological novelty is claimed.** C1 consists of known components:
  - a GP with a linear trend (universal kriging);
  - MAP hyperparameters under a fixed weak log-normal prior;
  - honest stacking;
  - Laplace logistic;
  - uncertainty sampling.
- **The supported claim** is an application gain in this pool, replicated on fresh splits. Its mechanism was measured in EA (small-n ML-II artefacts of the trend GP) and is consistent here (C1 − D on identical paid data).
