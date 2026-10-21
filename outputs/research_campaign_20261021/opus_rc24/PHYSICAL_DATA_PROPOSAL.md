# RC24: concrete proposal for new physical-simulation data

This is a proposal only. No simulator job was started.

## Why new data is needed

Two questions are left open by RC24, and no amount of re-analysis of the 541-run pool can settle them.

1. **Is the hard-region label deterministic?**
   - In the fast-scan corner, the label is decided by a short keyhole event at the end of the forming phase. In all 10 NEW short-keyhole runs, every keyhole frame lies within the forming phase plus 10 % of the record.
   - At equal maximum depth, the available scalars do not separate the classes. The leave-one-out AUC is 0.745 with depth, and start-up summaries add nothing.
   - If the start-up transient is sensitive to numerical details, the region is aleatoric for any input-based learner. Then the right target there is a calibrated probability, not separation. If it is deterministic, a transient-resolving feature could separate it.
2. **Does the physics anchor hold out of the sampled design space?** The geometry blocks are an internal proxy. A small external set at new (P, VX, LS) combinations would test Proposition P1 directly.

## Requested runs (same solver, same version as the NEW batch, same record length TE = 2.1 ms)

| block | design | runs | purpose |
|---|---|---|---|
| R1 replicates | 8 existing corner runs (4 NEW short-keyhole, 4 NEW conduction, closest pairs in input space) × 3 replicates, changing only the solver's random seed / particle initialisation | 24 | estimate the within-x label flip rate. A flip rate ≥ 0.2 means the region is aleatoric |
| R2 forming-phase probe | 6 corner inputs × 2 settings: (a) as now; (b) a 2× longer laser ramp-up | 12 | test whether the short keyhole is a ramp-up overshoot |
| R3 external anchor test | 16 runs on a 4 × 4 grid in (P, VX) at an LS outside the pooled range (±10 %), ST at the median | 16 | out-of-range test of HA_TREND vs HA_LEAN vs h-only, with predictions frozen before the runs |

Total: 52 simulations. Plan the cost at the NEW batch's per-run cost.

## Pre-registration for these runs (if approved)

- **R1:** the flip rate per input, compared with its binomial confidence interval.
- **R2:** the change in the share of runs with keyhole frames.
- **R3:** BA of the three frozen learners, trained on the full 541-run pool, on the 16 external runs, with their predictions written before the runs.

No outcome of these runs enters any RC24 claim.
