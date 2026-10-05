# Confirmation round 1 — results (decision by the locked rule of FREEZE_ROUND_1.md, pushed in `fc1afb50`)

Candidate **E1 = GPR on log max depth + straddle** (Week 7 formulation) vs **REF = G3 + margin**. Real data:
block **C1** (repeats 9–12, first and only use; SPLIT-CONFIRMATION). Twins: fresh reps 100–107 (SEMI-SYNTHETIC).
2,064 fits, none with fixed-point error > 1e-6 (max 1.4e-9). Tables: `contrasts.csv`, `qtt_E1.csv`, `aulc_*.csv`,
`decision.json`.

| Task | Metric | E1 − REF | 95% interval | Prediction (freeze) |
|---|---|---:|---|---|
| **R3_OLD (primary)** | BA AULC | **+0.0285** | [+0.010, +0.047] | +0.01 … +0.03 ✓ |
| R3_OLD | queries to REF's B80 level | **30 vs 88 (−66%)** | reduction [44%, 74%] | 30–50% (exceeded) |
| R3_OLD | q20 AULC (historical) | −0.003 | [−0.031, +0.026] | lower (not observed) |
| R2rev_TRANSFER | BA AULC | +0.012 | [−0.001, +0.024] | ≈ +0.01 ✓ |
| R2rev_TRANSFER | q20 AULC | −0.024 | [−0.046, −0.001] | lower ✓ |
| R2rev_TRANSFER | queries | 48 vs 60 (−20%) | [−64%, +58%] | — |
| **T_DEPTH OLD (primary twin)** | NSD AULC | **+0.082** | [+0.041, +0.125] | ≈ +0.06 ✓ |
| T_TOBIT OLD | NSD AULC | +0.062 | [+0.028, +0.104] | — |
| T_TOBIT pooled | NSD AULC | +0.039 | [−0.036, +0.167] | — |
| T_TOBIT NEW | NSD AULC | +0.009 | [−0.000, +0.021] | small ✓ |

**Decision rule:** S-a (R3_OLD ≥ +0.02, interval > 0) ✓; S-b (T_DEPTH ≥ +0.015, interval > 0) ✓; S-c (R3_OLD QTT
reduction ≥ 15%, interval > 0) ✓; non-inferiority (every in-scope task ≥ −0.01; minimum +0.009) ✓.
**E1 PASSES round 1.** Phase 6 (depth stress worlds, round-1 seeds) decides whether it survives.

Learning curves (pooled BA, mean of 4 repeats): R3_OLD E1 0.927 / REF 0.863 at B24, 0.939 / 0.908 at B48,
0.953 / 0.934 at B120 — the gain is largest early, as predicted by T18-4 / P-T18-1.

Scope reminder (stated in the freeze): every paid simulation must report its max depth. Not tested and not
claimed: POOLED / NEW tasks (NEW runs have no depth in the repository — owner decision D1), binary-only tasks.
