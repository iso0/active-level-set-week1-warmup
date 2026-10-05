# Confirmation round 2 — results (decision by the locked rule of FREEZE_ROUND_2.md, pushed in `1d560792`)

Question: does E1's advantage extend to NEW / POOLED once NEW depth is observed (after owner decision D1)? Candidate
E1 and reference G3 + margin unchanged from round 1. Block **C2** (repeats 13–16, first and only use;
SPLIT-CONFIRMATION). Every run has max depth (Week 7 definition, OLD and NEW). Execution was split into chunks to fit
the background limit. That affected only the order of execution, not what was computed; caches are per task.

| Task | Metric | E1 − REF | 95% interval | Freeze prediction |
|---|---|---:|---|---|
| **R1_POOLED (primary)** | BA AULC | +0.004 | [−0.001, +0.009] | ≈ 0 ✓ |
| R1_POOLED | queries to REF's B80 level | 36 vs 62 (−42%) | [−15%, +64%] | — |
| R1_POOLED | q20 AULC | +0.002 | [−0.015, +0.020] | lower ✗ |
| R3_NEW | BA AULC | −0.022 | [−0.070, +0.030] | ≈ −0.02 ✓ |
| R3_NEW | q20 AULC | −0.073 | [−0.169, +0.014] | lower ✓ |
| R2_TRANSFER | BA AULC | R2_PENDING | | ≈ +0.02 (n.s.) |
| R2rev_TRANSFER (NEW prior with depth) | BA AULC | −0.001 | [−0.004, +0.002] | ≈ +0.008 ✗ |
| **R3_OLD (replication)** | BA AULC | **+0.016** | [+0.013, +0.020] | +0.02 … +0.03 (low end missed) |
| R3_OLD | queries to REF's B80 level | 42 vs 48 (−12%) | [−10%, +29%] | — |
| R3_OLD | q20 AULC | −0.028 | [−0.046, −0.017] | lower ✓ |

**Decision (frozen rule):**
- **Q2a** (R1_POOLED ≥ +0.02 with interval > 0, or QTT reduction ≥ 15% with interval > 0): **fails** (+0.004; the QTT
  interval includes 0).
- **Q2b** (R3_NEW and R2_TRANSFER ≥ −0.01): **fails** (R3_NEW −0.022).
- **Q2c** (R3_OLD ≥ +0.02 with interval > 0): **fails**. The effect is positive and its interval excludes 0
  (+0.016 [0.013, 0.020]), but it is below the pre-registered size bar.

By the interpretation fixed in advance, ¬Q2c means "round 1 does not replicate". That is: the round-1 effect *size* is
not reproduced on C2. The *direction* is reproduced in every block (DEV +0.021, C1 +0.029, C2 +0.016, all intervals
above 0). The queries-to-target advantage is much smaller in C2 (−12%) than in C1 (−66%). The improvement does not
extend to POOLED or NEW. On NEW the label is not a max-depth threshold (DATA_AUDIT amendment 2), and the single-threshold
depth model loses.
