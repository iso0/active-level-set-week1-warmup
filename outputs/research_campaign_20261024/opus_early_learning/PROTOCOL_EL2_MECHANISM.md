# EL stage 2: one limited mechanism

Registered 2026-10-25, about 21:55 UTC, BEFORE any evaluation of the mechanism.

## 0. Why: a recorded direction change

The EL forward validation, frozen in 1751fd3b and run in 2dee796e, gave **NOT_ADOPTED** for D = HA_LEAN selects / HA_TREND predicts. The fixed crossing is therefore shown NOT enough on fresh data, although the DEV rule had judged it enough on point estimates.

`PROTOCOL_EL_OBJECTIVES.md` §7 allows ONE limited mechanism, learned only from paid observations, when the fixed crossing is not enough. The owner's stated priority is a concrete model + selector system that works in a single learner.

This stage opens one such mechanism. The rules are:
- The EL-1 verdict stays NOT_ADOPTED as recorded.
- The decision rule (§9) is not changed.
- The EL-1 forward repeats 83–122 and startups (K5 25–32, K4 9–16) are DEV data from now on.
- The mechanism is confirmed only on new IDs.

## 1. The measured problem

From the EL-1 forward run, 200 fresh learners. D − A in BA by budget:

| b | 8 | 12 | 16 | 24 | 40 | 60 |
|---|---|---|---|---|---|---|
| D − A | +0.016 | +0.005 | +0.003 | −0.001 | −0.002 | −0.001 |

Against A:
- attainment of 0.95: −4.5 points;
- kept at 0.95: −4.0 points.

The trend-emulator predictor is better only while few depths are paid, and slightly worse afterwards. A fixed choice of either predictor gives up one of the two phases.

## 2. The mechanism

It is fixed in full here; there are no free settings.

**System E:** HA_LEAN selects; the evidence-weighted HA_LEAN / HA_TREND mixture predicts.

**Selection:** unchanged from A. Margin −|p_L − 0.5| on the HA_LEAN probability, the same one-class rule, the same startup. So E's query path IS A's path, and also D's.

**Prediction:** the emulator choice e ∈ {L = HA_LEAN's constant-mean depth GP, T = HA_TREND's trend depth GP} is added as one more discrete hyperparameter of the SAME evidence rule that HA_LEAN already uses for its regularisation grid g = (τ_F, τ_h) ∈ {0.5, 1, 2, 4}².
- For each (e, g): log Z_{e,g} is the Laplace log marginal likelihood of the paid labels under the learned-regularisation classifier on [z_h, F_e]. F_e is emulator e's honest K = 10 out-of-fold predicted log depth of the paid runs (exactly as in HA_LEAN / HA_TREND).
- The prior is uniform over (e, g). The weights are w_{e,g} ∝ exp(log Z_{e,g}).
- The prediction is:

  p_E(x) = Σ_{e,g} w_{e,g} σ(m_{e,g}(x)) = W_L p_L(x) + W_T p_T(x),  with W_e = Σ_g w_{e,g}.

  - p_L and p_T are exactly the HA_LEAN and HA_TREND probabilities.
- **One-class rule:** HA_LEAN's (both share it). The paid class rate is used until both classes are present among the usable paid depths.

**Information used:**
- the labels, log depths and record-quality flags of the paid runs only, plus public inputs;
- no budget rule, no OLD/NEW information, no test labels.

**Compute:** in real use, E needs the HA_LEAN fit (as A, which also gives log Z_L) plus the HA_TREND fit, as D. Its decision CPU per step is reported as A's step + the HA_TREND fit.

## 3. DEV evaluation: one run, no tuning

**Data:** every recorded HA_LEAN path:
- STD repeats 51–58 and 67–122: 64 clusters, 320 learners;
- K5 startups 1–32: 160 learners;
- K4 startups 1–16: 64 learners.

**Job:** `el-mix-dev` (`src/el_mix.py`). At every budget 8..60 it computes p_L, p_T, both log-evidence grids, W_T and p_E, using only the first b paid runs of the path.

**Checks:**
- p_L must equal the recorded A predictions exactly;
- p_T must equal the recorded D predictions exactly, where they are stored in the same record (EL-1 forward units), and at b = 12 otherwise.

**Entry rule** (`PROTOCOL_EL_OBJECTIVES.md` §7): E enters the confirmation as primary only if, on DEV STD (individual learners, point estimates), all of these hold:
- ΔBA-AULC B8–B24 (E − A) > 0;
- the restricted-mean savings at 0.93 and at 0.95 are both > 0;
- attainment(0.95) and kept(0.95) are each not lower than A's by more than 0.025;
- E is better than the fixed candidate: its restricted-mean saving at 0.95 exceeds D's on the same DEV learners.

Otherwise EL-2 is closed as a DEV branch and the recommendation stays A.

## 4. Confirmation, only if E enters

**Fresh IDs:** never used before.
- STD repeats 123–162: 40 clusters, 200 learners;
- K5 startups 33–40;
- K4 startups 17–24.

**Runs:**
- the HA_LEAN path (A);
- on that path, every budget: p_L, p_T and the evidence grids, giving A, D and E;
- B and C are not part of this confirmation.

**Rule:** `PROTOCOL_EL_OBJECTIVES.md` §9 unchanged.
- E is the primary system against A.
- D against A is secondary (a replication of the EL-1 verdict on new data).
- Robustness (K5, K4, short-Keyhole group) is reported as before.

**Freeze:** `PROTOCOL_EL2_FINAL.md` and `freeze/EL2_FINAL_MANIFEST.json` are written after the DEV evaluation and before any confirmation run.
