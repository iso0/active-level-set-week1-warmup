# Freeze — confirmation round 1 (pushed before any round-1 run)

Date 2026-10-05. Candidate chosen on DEVELOPMENT data only (ATTEMPT_LEDGER E1; phase2/, phase3/depth2/). Runner:
`python -m src.week18_confirm 1 <real|twins|stress_depth>` (refuses to run unless this file and
`round_1/freeze_spec.json` are on origin/main unchanged).

## Candidate (one; the round allows ≤ 2)
**E1 = GPR on log max depth + straddle** — exactly the Phase 2 baseline implementation (`src/week18_engine.py`
DepthGPR: ARD Matérn-3/2 + white noise on standardized log inputs, standardized log-depth targets, ML-II at every
step from the default start; depth threshold u from revealed (depth, label) pairs; P(Keyhole) = Φ((μ − log u)/s);
straddle = argmax 1.96 s − |μ − log u|; rows without depth are not used). This is the Week 7 Phase 6 formulation,
re-implemented in the Week 18 engine. **Scope:** tasks in which every paid simulation reports its max depth.
Out of scope (stated in advance, not tested here): partial-depth tasks (R1_POOLED / R2_TRANSFER with the current
data, where NEW runs have no depth in the repository: DEV −0.037 on R1) and binary-only tasks (R3_NEW, S2 stress).

## Reference
G3 + margin with the locked Phase 2 schedule (per-step ML-II; every 8 queries on R2rev's large prior).
Startup identical for both arms (8 maximin + continuation; same seeds).

## Data (each used once)
- Real, SPLIT-CONFIRMATION: block **C1** (repeats 9–12, 5 folds each) of R3_OLD (primary) and R2rev_TRANSFER.
- Semi-synthetic: twins T_DEPTH OLD 324 (primary), T_TOBIT OLD 324, T_TOBIT pooled 433, T_TOBIT NEW 108, fresh reps
  **100–107** (frozen truths, `test_week18_twin_truth_frozen.py`).
- Phase 6 (after the round-1 decision, only if E1 passes): depth stress worlds `src/week18_stress_depth.py` round 1
  (base seed 1870): SD_NOISE10, SD_NOISE25, SD_DRIFT, SD_MISSING30, SD_NEWLIKE, SD_JUMP, reps 0–7.

## Endpoints and decision rule (locked)
Contrasts CAND − REF; 95% intervals by bootstrap over repeats (4 real repeats; 8 twin reps), 4,000 resamples,
seed 0 (`src/week18_metrics.contrast`). Real endpoint: pooled-per-repeat BA AULC over the task's budget grid; twins:
NSD_0.1 AULC. QTT: paid queries for the per-repeat curve to reach REF's mean value at B80 (round-1 data), censored
runs set to B_max + one grid step; reduction = 1 − mean QTT(E1)/mean QTT(REF), interval by the same bootstrap.
**E1 passes round 1 iff (A) at least one success route holds and (B) non-inferiority holds:**
- S-a (real): R3_OLD BA AULC difference ≥ +0.02 with interval excluding 0.
- S-b (synthetic): T_DEPTH OLD NSD AULC difference ≥ +0.015 with interval excluding 0.
- S-c (queries): R3_OLD QTT reduction ≥ 15% with interval excluding 0.
- (B) every in-scope task (R3_OLD, R2rev, T_DEPTH OLD, T_TOBIT OLD / pooled / NEW): difference ≥ −0.01 (point estimate).
- Phase 6 (separate, after a pass): no depth stress world below −0.03 NSD AULC (point estimate) vs REF.
Reported but not decisive: q20 AULC (historical definition), rare recall, AUC, R2rev QTT, secondary twins' S-b.
Multiplicity: three success routes (as set by the campaign brief) and six in-scope tasks; all results reported.

## Predictions (from DEV, written before the run)
R3_OLD +0.01 … +0.03 BA AULC (DEV +0.021); QTT reduction 30–50% (DEV 43%); gain concentrated at B16–B48; q20
lower than REF (DEV −0.026); R2rev ≈ +0.01; T_DEPTH ≈ +0.06; T_TOBIT NEW small (≤ +0.02).
