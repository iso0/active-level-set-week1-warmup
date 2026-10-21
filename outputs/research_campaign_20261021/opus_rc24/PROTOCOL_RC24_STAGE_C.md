# RC24 Stage C protocol: confirmatory test of the Stage B candidate on fresh data

Registered before any Stage C outcome. Frozen code:
- `src/rc24_confirm.py` (units);
- `src/rc24_pac.py` (HA_TREND, PAC family);
- `src/rc24_pilot.py` (`run_pac`);
- `src/rc24_eval_c.py` and `src/rc24_eval.py` (metrics and decision);
- `src/rc24_correction.py` (explicit-status rules).

The manifest is `freeze/RC24_STAGE_C_MANIFEST.json`.

The window is the same RC24 48-hour window (t0 2026-10-21T20:32:31Z), not restarted.

## 1. What Stage B established (DEV, already-used data; exploratory)

**P1, PAC (structural physics-anchored composite with errors-in-variables depth).** Pilot on repeats 51–58 and block seeds 1–8:
- Standard startup: PAC + margin did not beat HA_LEAN (BA-AULC −0.001 / −0.004; log loss worse late, +0.013).
- Blocks: PAC + margin was better than HA_LEAN (+0.008 / +0.010) but below h-only.

Matched decomposition on HA_LEAN's own paths, in the blocks:
- the physics anchor of the depth emulator carries the gain;
- the structural model without an anchor is WORSE (−0.023, 0/8);
- a generic linear trend does not help (−0.006);
- **HA_TREND**, honest stacking with the physics-anchored emulator, is best (+0.012 / +0.011, 8/8; standard startup +0.007 early).

The structural errors-in-variables part (PAC) is **closed**: no gain over stacking. Proposition P3 explains why it cannot move a configuration's 0.5 decision.

**P2, JEER (two-observation expected error reduction under PAC).**
- After 16 of 40 pilot learners: −0.004 / −0.001 against PAC + margin.
- The corner query share was unchanged (0.349 vs 0.352), although 99 % of the choices differ.
- Cost: 4.1 s per step.
- The mechanism (avoid the aleatoric corner) was not realised. The branch is **closed** (PLAN.json `disabled_reason`).

**HA_TREND + margin, own query (DEV repeats 51–58).** BA-AULC 0.9389 / 0.9479:
- against HA_LEAN: +0.0037 / +0.0006, non-inferior;
- against h-only: −0.0021 / +0.0039, non-inferior.

**Path diagnostics** (Stage A repeats 59–66, matched): see `dev_paths/` (section 2).

## 2. Primary candidate (fixed here, before any fresh outcome)

**The primary candidate is HA_TREND_MARGIN** (`PRIMARY.txt`). It was written together with the freeze manifest, from the DEV evidence of section 1 only.

The other system is secondary:
- HA_TREND + margin;
- HT_PHYS = the HA_TREND predictor with the h-only classifier's margin choosing the queries.

**Definitions.**
- **HA_TREND.** The RC23 HA_LEAN classifier unchanged (learned-regularisation Laplace classifier on [z_h, honest K = 10 out-of-fold predicted log depth]). The depth emulator is replaced by the physics-anchored GP:
  - log A = μ + θ z_h + g + e;
  - θ ~ N(0, 3²), integrated out, on the standardised-target scale;
  - g: Matérn-3/2 ARD GP on the standardised log inputs;
  - e: record-quality noise ×1e4 for short records;
  - ML-II hyperparameters.
  - Acceptance V1–V5 PASS (`validation/RC24_STAGE_B_P1_VALIDATION.json`).
- **HT_PHYS.**
  - Queries: margin −|p_h − 1/2| of the h-only learned-regularisation classifier (HONLY_LR).
  - Predictions: HA_TREND fitted on the same paid runs.
  - The acquisition never reads HA_TREND, so its trajectories ARE the HONLY_MARGIN trajectories. Its own-query predictions are HA_TREND evaluated on those paths (c-match, every budget).
  - **Rationale (mechanism):** the queries follow the physics boundary, which is globally valid. They do not chase the depth model's local uncertainty in the label-interleaved corner (Proposition P4; HA_LEAN margin puts 45 % of its queries there). The depth information is used where it is reliable: in prediction.
  - **Falsifying controls:**
    - HONLY_MARGIN (same path, h-only predictions) → is the depth predictor needed?
    - HA_TREND_MARGIN (same predictor, its own margin path) → is the physics path needed?
    - HA_LEAN on the HONLY path → is the anchor needed?

## 3. Design (fresh data)

**Conditions.**
- **STD:** fresh repeats 67–74 × 5 folds, standard 8-point maximin startup.
- **BLOCK:** RC22 k-means (k = 5, public standardised log inputs) geometry blocks, fresh seeds 9–16 × 5 blocks. The block is withheld from fitting and querying.

**Own-query arms:** HA_LEAN_MARGIN (reference, RC23 D1), HONLY_MARGIN, HA_TREND_MARGIN. That is 240 units.

**Matched evaluation (c-match).** On every HA_LEAN_MARGIN and HONLY_MARGIN path, every budget 8–60, these constructions are evaluated (160 units):
- HA_LEAN and HONLY_LR;
- HA_TREND, with prior-sensitivity controls HA_TREND_B1 (b = 1) and HA_TREND_B10 (b = 10);
- PAC (structural);
- PAC_GEN (generic trend).

Budgets, information contract, one-class rule and record-quality rule are unchanged from RC19–RC23.

## 4. Pre-registered decision (`src/rc24_eval_c.py::decide`) for the primary candidate X against HA_LEAN_MARGIN

| component | condition | PASS iff |
|---|---|---|
| std_ni | STD | non-inferiority, one-sided 95 % t lower bound ≥ −0.010, in BOTH windows B8–B24 and B8–B60 (n = 8 repeats) |
| std_spend | STD | spend to BA ≥ 0.95 not MORE and complete (corrected status rule) |
| block_gain | BLOCK | one-sided 95 % t lower bound of X − HA_LEAN BA-AULC B8–B60 > 0 (n = 8 seeds; the 5 blocks of a seed fold-pooled) |

**Labels.**
- **CONFIRMED** if all three components PASS.
- **PARTIAL** if either the STD pair or block_gain passes, but not both.
- **NOT CONFIRMED** otherwise.
- **INCOMPLETE** if any component is incomplete.

**Reported, not decisive.**
- The same rule for the secondary system.
- X against HONLY_MARGIN non-inferiority in both conditions and both windows. "Dominates both references" requires all PASS.
- RC22 verdicts (0.020, 7/8) and MATERIAL labels.
- Both recalls.
- Attainment and spend for 0.80, 0.90, 0.93 and 0.95: first budget, b and b + 4 confirmation, maintenance, censoring; observed spend kept apart from restricted spend (censored = 61).
- Individual learners alongside fold-pooled results.
- Log loss, AUC, oracle-threshold gap.
- Hard group (10 NEW short-K, 12 NEW conduction) and the corner query share.
- CPU per step.
- Matched prior sensitivity and falsifying controls.

Nothing in this section is changed after Stage C outcomes.
