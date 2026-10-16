# SURPRISE_DISCOVERY (pilot A) — surprising observation → local exploration while global exploration continues

**Status: REGISTERED BEFORE ANY SURPRISE_DISCOVERY OUTCOME** (owner request of 2026-10-16: the primary method question; Ioan's post-meeting task).
- This is exploratory DEV work. The real replay uses NEW simulations that were inspected before.
- **Code:** `src/jdl_surprise.py` (rule, synthetic world, real replay, validation, frozen evaluation).
- **Manifest:** `SURPRISE_MANIFEST.json` with code hashes, committed before the first unit.

## Question

When a purchased observation contradicts the posterior that existed before it was bought, does a short local exploration around it find the other members of that behaviour family with fewer queries than margin, straddle or random selection? It must do so at the same budget and without global harm.

## Rule SD (fixed in advance; one rule, two base selectors)

- **Surprise:** the observed label had probability ≤ 0.2 under the posterior fitted before that observation. For a one-class paid set that posterior is the constant (n1 + 0.5)/(n + 1).
  - A missing or non-finite response is a QC event. It is logged and is never a surprise; the label still counts.
- **Seeds and alternation:** a surprising observation becomes a seed (FIFO). While a seed is active, queries alternate LOCAL, GLOBAL, LOCAL, … (1:1). Each seed gets at most 3 local probes.
- **Local probe:** the nearest unpaid pool point to the seed in fold-standardized log inputs, ties broken by simulation ID. A local probe that is itself surprising becomes a new seed.
- **Global step:** the base selector, margin or straddle.
- **Budget:** every probe is a paid query in the same budget.

## Arms and conditions

**Synthetic (evaluator-only truth).**
- **World:** 2-D, with a smooth background boundary and one small no-class island inside the class-1 side, plus a continuous noisy response r with label 1{r > 0}. Pool 300, test 1000, seeds 1–10.
- **Budget:** feature-only maximin start of 10, then B10 → B40.
- **Arms:** MARGIN (GPC), STRADDLE (GPR on r), RANDOM, SD_MARGIN, SD_STRADDLE.
- **Condition `synthetic`:** arms choose freely.
- **Condition `synthetic_planted`:** the first post-start query of every arm is the island point nearest the island centre. This is the experimental condition "a surprising observation has been purchased".

**Real replay.**
- **Data:** NEW, DEV repeats 3–4, folds 1–5, the frozen feature-only B16 starts (TRAINED_AL paths), B16 → B40.
- **References:**
  - **G3_MARGIN:** the Week 18 G3 GP classifier on the manual binary label, ML-II at every step, margin selection.
  - **E1_STRADDLE:** the ACTIVE depth GPR, ML-II at every step, straddle selection.
  - Validation shows both reproduce the frozen TRAINED_AL `r4_f1` paths exactly.
- **Control:** RANDOM (G3 model, seeded).
- **Candidates:** SD_MARGIN (G3 + SD) and SD_STRADDLE (E1 + SD).
- **One-class rule (all arms, fixed in advance; replaces TRAINED_AL's "not permitted"):** while the usable paid labels are one-class, the next query is the next unpaid point of the frozen feature-only path. That point is label-free, and the prediction is the constant. This makes `r3_f4` usable for every arm.
- **Observation contract:**
  - The selector sees paid features, labels and A only.
  - It never sees test labels, short-K or q20 membership, the corner (VX > 0.85) or global class counts. Validation checks this: corrupting hidden outcomes, or changing the evaluator corner, leaves paths unchanged.

## Endpoints (prospective)

**Synthetic.**
- **Primary:** island discovery AUDC, the area under the fraction of island pool points paid, over B10–B40.
- **Also reported:** first island hit, final test BA, and island test recall.
- **Contrasts:** SD_MARGIN − MARGIN, SD_STRADDLE − STRADDLE and SD_MARGIN − RANDOM, each with a paired bootstrap over the 10 seeds, for each condition.

**Real.**
- **Primary (query efficiency):** no-Keyhole discovery AUDC, the fraction of the training pool's no-Keyhole runs paid, over B16–B40, per trajectory. The contrasts are paired over the 10 fold × repeat pairs, with a bootstrap 95% interval:
  - SD_MARGIN − G3_MARGIN;
  - SD_STRADDLE − E1_STRADDLE;
  - SD_MARGIN − RANDOM.
- **Verdict:** **DISCOVERY GAIN (DEV)** iff the mean is > 0 with the interval above 0 and there is no global harm. Global harm means the B40 BA mean over repeats is lower than the reference's by more than 0.02, or the B40 short-K caught count is lower by more than 2 (of 20, summed over the two repeats).
- **Also reported:**
  - corner and short-K discovery (evaluator-only);
  - queries to half of the no-Keyhole runs (right-censored at B40);
  - same-budget BA, both recalls, q20, short-K caught/total, AUC and Brier at B16/24/32/40, per repeat;
  - surprises, local probes and seconds.
- **Short-K, fixed before evaluation (secondary):**
  - absolute protection target ≥ 7 of 10 per repeat at B40;
  - acceptable difference relative to the reference: at most 2 fewer of 20.
  - Two arms that are equally poor do not count as protection.
- **Fewer simulations:** a saving is claimed only if an arm sustains BA ≥ 0.75, short-K ≥ 0.70 and q20 ≥ 0.70 over two consecutive grid points (16..40, step 4) before its reference does, with the reference budget B40 and right-censoring. Same-budget improvement and demonstrated saving are reported separately.

## Budget and compute

- **Volume:** synthetic 100 units of about 1–2 s each; real 50 units of about 1–3 s each, measured in validation.
- **Limits:** per-unit time limit 1800 s (a breach is recorded as TIME_LIMIT). Results are written atomically per unit.
- **Threads:** at most 2 workers with one BLAS thread each, inside the four-thread total.

## Disclosure and limits

- The validation output printed one planted-condition sanity line for synthetic seed 1 (SD_MARGIN 5 vs MARGIN 2 island points found by B40) before this freeze. The registered result uses all 10 seeds.
- The real replay is DEV on inspected NEW runs; a new split is not new data. C3's failed superiority result and every frozen earlier experiment are unchanged.
