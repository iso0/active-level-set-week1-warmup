# EL study: objectives, estimands and decision rules

Registered 2026-10-25, before any result of this study. Owner instruction of 2026-10-24.

## 0. What is already known at registration

**Already seen (RC23 / RC24 / RC24 post-audit):**
- Own-path results of A (HA_LEAN selects, HA_LEAN predicts) and B (HA_TREND selects, HA_TREND predicts) on the DEV repeats 51–58, 67–74, 75–82 and the block startups.
- The RC24 Stage C pooled block summary of the matched evaluation ("model effect on identical paths +0.0101").

**Partly computed:** D (HA_LEAN selects, HA_TREND predicts).
- Every budget: Stage C c-match, repeats 67–74 and k = 5 startups 9–16.
- Budgets 8, 12, …, 60 only: repeats 51–58 and 75–82, k = 5 startups 1–8 and 17–24, k = 4 startups 1–8.

**Never computed:** C (HA_TREND selects, HA_LEAN predicts).

**Unchanged:** the frozen decisions (RC23 D1; RC24 Stage C as recorded and narrowed; RC24P final "HA_LEAN + margin"). This study records its own result next to them.

## 1. Systems

No new model names.

| | selects (margin) | predicts |
|---|---|---|
| A | HA_LEAN | HA_LEAN |
| B | HA_TREND | HA_TREND |
| C | HA_TREND | HA_LEAN |
| D | HA_LEAN | HA_TREND |

**HA_LEAN and HA_TREND** are exactly as in RC23 / RC24:
- HA_LEAN: `src.rc23_common.state` HA_LEAN.
- HA_TREND: `src.rc24_pac.state` HA_TREND; its depth-emulator mean is θ·z_h with θ ~ N(0, 3²) integrated.

**"Selects" means:**
- The next simulation is the unpaid candidate with the largest −|p − 0.5| of that model's probability (first index on ties).
- Until both classes are present among the usable paid depths, the next point on the label-free maximin path is taken (the RC23 / RC24 one-class rule).
- The 8 startup simulations are the first 8 points of that path. They are the same for every system of a learner and are counted.

**Information contract:**
- Both models learn only from the same paid simulations: their label, log depth and record-quality flag, plus the public inputs.
- Unopened runs give nothing to any learner. Test outcomes are used only by the evaluator.

**Cost:** one simulation per query, however many models it trains. CPU is counted separately.

## 2. Objective ordering

Registered before results:
1. **O1** – high BA-AULC over the first 8–24 simulations.
2. **O2** – few simulations to BA 0.93 and 0.95.
3. **O3** – the probability of reaching the target over startups, and keeping it.
4. **O4** – probability quality (log loss, Brier) and compute.

Log loss is auxiliary. A small log-loss worsening does not by itself reject a real early-BA and simulation-saving gain; only the guardrail of §9 applies.

## 3. Learners

- **Individual learner (primary):** one STD task (repeat r, fold f; pool = 4 folds, test = 1 fold of the seeded random split [1919, r]) or one BLOCK task (one held-out region).
- **Pooled (shown beside):** the learners of one repeat or startup concatenated.
- **Budgets:** 8, 9, …, 60, including the 8 startup simulations.
- **Folds** of one repeat share the pool and are not independent data.

## 4. Metrics, per learner

- **BA:** threshold 0.5. Recalls are reported separately: Keyhole recall (class 1) and conduction recall (class 0).
- **BA-AULC:** the mean BA over b = 8..24 (window B8–B24) and over b = 8..60 (window B8–B60).
- **BA at budgets** 8, 12, 16, 24, 40, 60.
- **Target endpoints**, for τ ∈ {0.90, 0.93, 0.95}:
  - first(τ) = the first b with BA ≥ τ.
  - confirmed(τ) = the first b ≤ 56 with BA(b) ≥ τ and BA(b + 4) ≥ τ.
  - spend(τ) = confirmed(τ) + 4 simulations, counting the 8 startup ones.
  - attained(τ) = confirmed(τ) exists.
  - maintenance(τ) = the share of budgets ≥ confirmed(τ) with BA ≥ τ (attainers only).
  - kept(τ) = attained(τ) and BA(60) ≥ τ.
  - lost(τ) = attained(τ) and not kept(τ).
- **Log loss:** probabilities clipped to [1e-6, 1 − 1e-6].
- **Brier:** (p − y)².
- **Decision CPU:** process CPU seconds per step.
  - Selector: fit on the paid set plus scores at the unpaid candidates and the test rows. This is the `cpu_s` of an own-path step.
  - Predictor: fit plus prediction at the test rows; this is the `cpu_s` of a cross step.
  - A crossed system pays selector + predictor per step; A and B pay one fit per step.

## 5. Paired savings, with censoring explicit

Pairs are the same learner (task and startup) under system X and under the reference A.

For every τ:
1. **Attainment table:** both, X only, A only, neither.
2. **Restricted-mean spend, horizon 60:** RMS(τ) = mean over learners of min(spend(τ), 61); a learner that does not attain counts as 61.
   - RMS = 12 + Σ_{b=12..60} (1 − F(b)), where F(b) is the share of learners with spend ≤ b. A spend of 12 is the earliest possible.
   - The restricted-mean saving RMS_A − RMS_X is therefore the area between the two cumulative attainment curves over b = 12..60.
   - It is neither the true cost nor a bound on the true saving; it is reported only under this name.
3. **Cumulative attainment** F(b) at b = 16, 24, 40, 60.
4. **Both-attained mean saving:** conditional on both systems attaining. Reported; never the basis of a general claim.
5. **Median spend:** reported when more than half of the learners attain.

## 6. Uncertainty

- **Cluster:** the repeat (STD) or the startup (BLOCK).
- **Statistic:** the per-cluster mean of the per-learner paired difference; one-sided 95 % t bounds over clusters (n_clusters − 1 degrees of freedom).
- **Check:** a cluster bootstrap with 10,000 resamples, seed 2024.
- **Proportions** (attainment, kept): per-cluster proportions, same t bounds.

## 7. DEV stage: existing paths

This stage is for mechanism and candidate selection. It is never evidence for a claim.

**Data:**
- STD repeats 51–58, 67–74, 75–82 (24 repeats, 120 learners).
- k = 5 blocks with startups 1–24.
- k = 4 blocks with startups 1–8.

**Computation:**
- **C** at every budget 8..60 on the recorded HA_TREND paths.
- **D** only where it is missing (budgets not on the 8, 12, …, 60 grid), plus one check budget per unit against the existing value.
- **Code check:** at b = 8 the paid set is the common startup on both paths, so C(8) = A(8) and D(8) = B(8) must hold.
- Each cross prediction uses only the first b paid runs of its path.

**2×2 decomposition** on identical startups:
- model effect on each path: D − A and B − C;
- path effect for each predictor: C − A and B − D;
- interaction: (B − C) − (D − A).

**Candidate rule** (DEV STD, individual learners):
- The forward primary candidate X is the fixed system in {B, C, D} with the largest ΔBA-AULC B8–B24 against A.
- Within 0.001, the larger restricted-mean saving at 0.95 wins, then at 0.93.

**"The fixed crossing is enough"** if the candidate shows on DEV (point estimates):
- ΔBA-AULC B8–B24 > 0;
- restricted-mean savings at 0.93 and at 0.95 both > 0;
- attainment(0.95) and kept(0.95) each not lower than A's by more than 0.025.

**Otherwise (stage 2)** at most ONE limited mechanism may be developed on DEV data:
- The measured problem is written down first.
- It is learned only from paid observations.
- No budget switch chosen from results, no OLD/NEW routing, and no test labels in any weight, threshold or switch.
- No variant search: any setting is fixed before the mechanism is first evaluated, or learned from paid data inside the learner.
- It enters the forward test as the primary candidate only if it meets the "enough" conditions on DEV better than the fixed candidate; otherwise it is reported as a closed DEV branch.

## 8. Forward validation

**Freeze:** registered after the DEV stage and before any fresh run, with a SHA-256 code manifest.

**Fresh IDs:**
- STD repeats 83–122: 40 repeats × 5 = 200 learners. Repeats 1–82 were used before.
- BLOCK_A: the same five k = 5 regions with new startups 25–32.
- BLOCK_B: the k = 4 partition with new startups 9–16.

All are new splits or startups of the same 541 runs: DEV evidence, not independent physical validation.

**Runs:**
- both selection paths (HA_LEAN-selected and HA_TREND-selected);
- on each path, both predictors at every budget, giving A, B, C and D;
- plus the stage-2 system's own path if there is one.

## 9. Final decision rule

Fixed here. The candidate X is compared with A on STD, individual learners, 40 clusters.

**E1 early:** ΔBA-AULC B8–B24 (X − A) with one-sided 95 % LCB > 0 → EARLY GAIN SHOWN.

**E2 savings** (separately for τ = 0.93 and 0.95), using the restricted-mean saving RMS_A − RMS_X:

| one-sided 95 % LCB | status |
|---|---|
| > 0 | SAVING SHOWN |
| > −1.0 simulation | NOT WORSE |
| otherwise | NOT SHOWN |

**E3 reliability** (τ = 0.93 and 0.95):
- Δattainment (X − A) LCB ≥ −0.05;
- Δkept (X − A) LCB ≥ −0.05.

**E4 guardrails** (auxiliary O4; point estimates):
- ΔLL B8–B60 ≤ +0.030;
- ΔBrier B8–B60 ≤ +0.010;
- mean decision CPU per step ≤ 3 × A's.

**Verdict:**

| verdict | conditions |
|---|---|
| SAVINGS_SHOWN | E1 shown; E2 SAVING SHOWN at both targets; E3 and E4 hold |
| PARTIAL_SAVINGS | E1 shown; E2 SAVING SHOWN at one target and NOT WORSE at the other; E3 and E4 hold |
| EARLY_ONLY | E1 shown; E2 NOT WORSE at both; E3 and E4 hold |
| NOT_ADOPTED | anything else |

The same rule is applied, as secondary results, to every other system against A. The candidate is also compared with B.

**Robustness** (reported, not part of the verdict): BLOCK_A, BLOCK_B (pooled and per region) and the short-Keyhole group.
- A warning is raised if X's per-region BA-AULC B8–B60 has a one-sided 95 % LCB below −0.02 against A in either partition.

**Practical reading:** the report states which system serves which use:
- a fixed small budget (8–24): O1;
- stop at a target: O2 / O3;
- calibrated probabilities: O4.
