# Historical repulsion audit

## Week 4 synthetic diversified straddle

- `week4_02_diversified_straddle.py` used `(1-alpha)*normalized_straddle + alpha*normalized_diversity`, with `alpha=0.25`.
- Diversity was minimum Euclidean distance to the queried set in scaled synthetic input coordinates, then min-max normalized over the candidate pool.
- Week 4.03 added a boundary shortlist before a similar additive mixture.
- These were tested on synthetic Branin and Ackley designs; the fixed mixture weight was not a systematic geometry-scale sweep.

## Week 7 / frozen Week 8.5 classifier repulsion

- `week7_phase6_real_data_boundary_active_level_set.py` and Week 8.5 used `normalized_uncertainty * (1-exp(-d_min^2/(2*0.15^2)))`.
- `d_min` used standardized `[P,VX,LS,ST]` geometry; the bandwidth was the fixed raw standardized-space value `0.15`.
- Week 8.5 found slightly larger nearest-query distance but no robust performance improvement for this single configuration.

## Scope of the old conclusion

The defensible historical conclusion is: **one small fixed repulsion configuration did not robustly outperform margin**. It does not establish that repulsion as a principle fails, because neither the raw bandwidth nor a geometry-relative scale response was audited systematically.
