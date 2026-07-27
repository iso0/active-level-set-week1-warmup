# Corrected Week 6 Phase 1 results

**Source:** `ioandanielc/sph_dataset` at immutable revision `0e859b748fdbc8454f66e58e101e333ac0479d42`.

## Repository enumeration

- Old pinned revision and current `main` resolve to the same SHA at inspection time.
- Directory-aware HfApi and independently paginated HTTP enumeration both find
  **241 simulation folders**.
- Numeric IDs run from **1 to 242** with one documented gap: **sim_00136**.
- `sim_00242` exists directly and appears in both complete folder enumerations.
- `experiments.csv` has 241 unique records.
- Records in both sources: 241.
- Experiments-only records: 0 (none).
- Folder-only records: 0 (none).
- Metadata IDs, hashes, and all four input values match the master table.

## File completeness

- Monitor-complete simulations: **241/241**.
- Target-complete simulations: **241/241**.
- Incomplete simulations: none.
- Every simulation has all 34 monitor types and equal front/side/top frame counts.

## Melt bounds and physical axes

`monitor/position-bounds_melt.dat` is headerless comma-separated
`[x_min, x_max, y_min, y_max, z_min, z_max]` in metres. Empty-melt rows use
alternating `+/-3.402823e38` sentinels.

- **X:** positive laser scan direction; `delta_x` is melt-pool length.
- **Y:** transverse direction; `delta_y` is melt-pool width.
- **Z:** vertical direction; `z=0` is the original substrate surface.
- **Penetration depth:** `max(0,-z_min)`.

All 241 configurations use `[VX,0,0]`; all gravity and beam vectors point
along negative Z. Full-population centre motion and low/middle/high-ID frames support
the mapping. Confidence is high.

## Responses and scalar targets

The retained responses are width, length, and penetration depth. Their primary scalar
is:

> median over final 20% of melt-present time before laser reaches 90% of +X domain

The full-population comparison supports this rule: it retains all 241
simulations and has lower selected-window variability and residual trend than
uncontrolled final-20% windows. Final recorded values are available in only
171/241 runs, while the
laser exits the domain before recording ends in
113/241.

Selected-window instability flags affect 11 simulations:
sim_00002, sim_00006, sim_00018, sim_00029, sim_00036, sim_00038, sim_00095, sim_00105, sim_00124, sim_00154, sim_00222.

## Final dataset

`week6_phase1_simulation_level_responses.csv` has
**241 rows × 199 columns**. It contains numeric and text
simulation IDs, immutable provenance, `[P,VX,LS,ST]`, source paths, axis mapping,
complete extent/response summaries, all required target candidates, selected targets,
window/maximum traceability, aligned time/iteration evidence, and quality flags.

## Validation and readiness

22/22 validation checks pass.
Failing checks, if any: none.

Phase 1 data are ready for later modelling as a complete 241-row table.
No GP, kernel comparison, cross-validation, active learning, or level-set estimation
was performed.
