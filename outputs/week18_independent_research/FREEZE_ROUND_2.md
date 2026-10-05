# Freeze — confirmation round 2: does E1's advantage extend to NEW / POOLED once NEW depth is observed?

Date 2026-10-05, pushed before any round-2 run. Prompted by owner decision D1 (NEW monitors downloaded; DATA_AUDIT
amendment 2). Runner: `python -m src.week18_confirm 2 real`; decision: `python -m src.week18_round_analysis 2 round2`.

## Candidate and reference (unchanged from round 1)
E1 = GPR on log max depth + straddle, per-step ML-II (identical code and settings to round 1; max depth by the
Week 7 definition for OLD **and NEW** runs, no post-hoc change of the depth target). REF = G3 + margin, Phase 2
schedule. Every real task now has depth for every run (`src/week18_tasks.attach_full_depth`).

## Data (used once)
Block **C2** (repeats 13–16, 5 folds each) of R1_POOLED (primary), R3_NEW, R2_TRANSFER, R2rev_TRANSFER (NEW prior now
with depth) and R3_OLD (replication). SPLIT-CONFIRMATION. Note: NEW's depth–label relation was inspected on all 136
NEW runs (descriptively, DATA_AUDIT amendment 2) before this freeze; the candidate was not changed in response.

## Locked decision rule (contrasts E1 − REF; repeat bootstrap, 4,000 resamples, seed 0; QTT as in round 1)
- **Q2a (POOLED improvement):** R1_POOLED BA AULC ≥ +0.02 with interval > 0, **or** R1_POOLED QTT reduction ≥ 15%
  with interval > 0.
- **Q2b (NEW non-inferiority):** R3_NEW and R2_TRANSFER BA AULC ≥ −0.01 (point estimates).
- **Q2c (OLD replication):** R3_OLD BA AULC ≥ +0.02 with interval > 0.
Interpretation fixed in advance: Q2a ∧ Q2b → the improvement extends to POOLED/NEW; ¬Q2a ∧ Q2c → the improvement is
confirmed for OLD-type data only; ¬Q2c → round 1 does not replicate. q20, R2rev and QTT on other tasks are reported,
not decisive.

## Predictions (from the full-depth DEV run `phase3/depth3/`, written before the run)
R1_POOLED ≈ 0 (DEV −0.001 [−0.004, 0.003]) → **Q2a expected to fail**; R3_NEW ≈ −0.02 (DEV, interval [−0.08, 0.04])
and R2_TRANSFER ≈ +0.02 (DEV, n.s.) → Q2b uncertain (R3_NEW likely below −0.01); R3_OLD ≈ +0.02…+0.03 → **Q2c
expected to pass**; R2rev ≈ +0.008; q20 lower than REF on every task. Mechanism predicted: on NEW the label is not a
max-depth threshold (AUC 0.891), and NEW rows contaminate the single depth threshold in pooled fits.
