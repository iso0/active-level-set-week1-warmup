# Freeze — C3 confirmation: ACTIVE E1 + straddle vs G3 + margin

*Written 2026-10-13T09:22:19+00:00; committed and pushed before any C3 task object was built.*

- **Approval:** Owner approval in chat, 2026-10-13: 'C3 taslağını onaylıyorum, dondur ve çalıştır' (approve the C3 draft, freeze and run).
- **Draft:** `c3_draft/C3_PROTOCOL_DRAFT.md` (commit 2833e175). Its decision rule, candidate, reference and predictions are unchanged.
- **Runner:** `python -m src.week20_c3_confirm run 4`
- **Decision:** `python -m src.week20_c3_confirm analyze`

## Candidate, reference and ablation
- **Candidate:** ACTIVE E1 + straddle (Track 1 arm B).
- **Reference:** G3 + margin (arm C).
- **Ablation:** WHOLE E1 + straddle (arm A), reported but not decisive.
- **Code:** all three use the frozen runner `src/week20_track1_al.py`, at 4 workers × 1 BLAS thread.
- **Task builder:** the only new code. It is the frozen builder with the block as a parameter, and was checked identical on DEV repeats 5–8 (60 task-folds).

## Data (used once)
- **Block:** C3 = repeats 17–20, 5 folds each.
- **Tasks:** R3_NEW (primary), R3_OLD and R1_POOLED.
- **Type:** split confirmation on the same 541 runs.

## Locked decision rule (ACTIVE − G3; repeat bootstrap, 4,000 resamples, seed 0)
- **Q3a (primary):** R3_NEW BA-AULC ACTIVE - G3 >= +0.02 AND 95 % interval lower bound > 0.
- **Q3b (no loss):** R3_OLD and R1_POOLED BA-AULC ACTIVE - G3 >= -0.01 (point estimates).
- **Interpretation:**
  - Q3a and Q3b → **CONFIRMED: ACTIVE E1 + straddle improves on G3 + margin on NEW, without loss on OLD / POOLED**
  - Q3a and not Q3b → **IMPROVEMENT ON NEW WITH A LOSS ELSEWHERE**
  - not Q3a, point estimate > 0 → **NOT CONFIRMED AT THE FROZEN BAR**
  - point estimate <= 0 → **DOES NOT REPLICATE**
- **Reported, not decisive:** q20, specificity, sensitivity, short-K sensitivity, Brier, AUC; ACTIVE - WHOLE and WHOLE - G3; QTT (frozen definition; target = G3's mean BA at B40/B80 over C3); learned-threshold mechanism.

## Predictions (from DEV, written before the run)
- **R3_NEW_ACTIVE_minus_G3_repeats_1_8:** +0.056 [+0.015, +0.103]; per repeat +0.062, -0.032, +0.067, +0.132, +0.004, +0.029, +0.176, +0.013
- **Q3a_pass_probability_from_DEV_resampling:** about 60 % (bar alone 87 %, interval alone 62 %); optimistic, A was defined after the NEW labels were seen
- **Q3b:** expected to pass (DEV: OLD +0.023, POOLED +0.005)
- **mechanism:** WHOLE E1 expected to show reversed-slope trap episodes on R3_NEW whenever the late negative is the only startup negative; ACTIVE E1 expected to stay below u = 200 um

## Failure rules
- fit exception, non-finite prediction or score: the run stops, status recorded, later budgets missing; nothing is rerun
- single-class usable response pairs for an E1 arm (e.g. the A-unavailable negative as the only startup negative): the run stops and is reported (the engine's 111 um fallback is never used)
- every C3 run is executed once; no favourable selection; all 180 runs are reported

## Budget and order
- **Budget:** 180 runs x <= 73 fits = 13,140 scalar fits (cap 15,000 for this round).
- **Order:** 1) this freeze is committed and pushed; 2) C3 tasks are built and their split hashes and startup composition recorded; 3) all 180 runs; 4) analysis and the locked decision.

## Caveats
- A was defined after the Week 19 audit had seen every NEW label, so C3 tests the procedure on new splits and seeds; it does not test a target chosen blind to the labels.
- C3 is the last unused block.
- With four repeats, the repeat bootstrap is coarse.
