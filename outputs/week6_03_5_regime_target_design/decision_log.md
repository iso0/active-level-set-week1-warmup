# Week 6 Phase 3.5 decision log

## Why Phase 3.5 was needed

T0 was designed as typical late-active geometry.  The future
conduction–keyhole problem instead needs a scalar that distinguishes a
single-frame excursion from sustained deep, narrow melt behaviour.  Phase 3.5
therefore reconstructs depth, transverse width, and their ratio along physical
scan position without altering T0 or any Phase 1–3 conclusion.

## Physical definitions and boundaries

- Instantaneous length is `x_max - x_min` at one monitor row; it is not the
  cumulative melted-track length.
- Penetration depth is central because keyhole-like behaviour is associated
  with deep penetration, but width remains physically important through
  depth/width.
- Global maxima G1 and R1 are retained as spike-sensitive references, not
  recommended targets.
- Persistence uses physical scan distance because equal timestep counts
  correspond to different distances when VX differs.
- Normalized position uses the verified domain bounds and laser motion, never
  a per-simulation final-position normalization.
- Right-censoring matters: 136, 130,
  121, and 113
  simulations reach s=0.85, 0.90, 0.95, and 1.00 respectively.
- The common interior is s=0.10–0.55,
  selected by a predeclared 80% support rule.  The adaptive interior uses
  50 µm startup and end margins.

## Label evidence and circularity

- Stored rows: 65,472.
- Keyhole-containing simulations: 9.
- Simulations containing both Conduction and Keyhole: 8.
- Conduction-without-Keyhole simulations: 230.
- All 241 provenance files retain the automatic method
  `per-experiment-median-zmin, threshold = 1.5x median`.
- 177 simulations are marked
  human-verified and 64 automatic.

This creates circular validation: strong agreement between depth-derived
scores and depth-seeded labels is descriptive agreement, not independent
physical validation.  Screenshot Bug and Initial Emptiness are never used as
physical negative classes.

PR AUC is emphasized because the any-Keyhole prevalence is only
0.0375.  Accuracy would be misleading
under this imbalance.

All VX, coverage, and geometry associations are observational.  No causal
effect is inferred in Phase 3.5.

## Candidate interpretation

- G0 remains the geometry baseline.
- G1/R1 show the strongest label ranking but are intentionally spike-sensitive
  and therefore unsuitable as persistent targets.
- G2/R2 summarize robust high geometry but do not require persistence.
- G3/R3 use a 50 µm trailing rolling median and are tested at 20, 50, and
  100 µm plus 1%, 2.5%, and 5% of track length.
- R4 and R5 are threshold-dependent diagnostics.  The threshold is
  dataset-specific and recomputed from outer-training geometry for held-out R4
  evaluation.

## Representative cases

- C1 — Typical conduction-only: `sim_00157`. No Keyhole label; R3 closest to the conduction-only median.
- C2 — Typical keyhole-containing: `sim_00137`. Keyhole-containing; closest joint robust distance to median R3 and keyhole fraction.
- C3 — Mixed Conduction-to-Keyhole transition: `sim_00222`. Both labels, exact alignment, and maximum balanced labelled-frame support around first Keyhole.
- C4 — Maximum-versus-persistence disagreement: `sim_00036`. Largest combined percentile rank of global R1 and R1-minus-R3 spike gap.
- C5 — Persistent deep-melt: `sim_00214`. Largest combined rank of high R3 and small relative R1-to-R3 gap.
- C6 — Phase 1 unstable-window: `sim_00038`. Independent Phase 1 unstable ID; R3 closest to the remaining unstable-group median.

Each case was selected by a reproducible population rule after the audit; none
was manually chosen for visual impact.

## Final recommendation

Retain T0 as the geometry target.  Provisionally carry R3—the maximum 50 µm
rolling-median depth/width—as the regime-propensity target, with G3 persistent
depth retained as a companion sensitivity.  The later design should keep two
outputs until independently updated labels determine whether one continuous
target is sufficient.

The recommendation is based on physical interpretation, spike resistance,
window/domain robustness, coverage, and descriptive label agreement.  It is
not selected by an arbitrary weighted score or AUC alone.

## Remaining limitations and Ioan decisions

1. Confirm whether the intended physical target is sustained aspect ratio or
   sustained absolute penetration depth.
2. Confirm whether updated labels exist that were generated independently of
   z-min/depth.
3. Confirm whether a two-output level-set problem is acceptable later.
4. Confirm whether the 50 µm persistence scale has a preferred metallurgical
   interpretation.
5. Decide whether label uncertainty warrants a dedicated relabelling phase.

Kinetic energy, total-height Phase 4 modelling, feature effects, ARD, active
learning, classification, acquisition rules, and level-set estimation remain
deferred.
