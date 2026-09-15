# Phase 3.5 implications for later conduction–keyhole active learning

## Recommended role separation

Phase 3.5 supports retaining two scientifically distinct outputs for now:

1. **Geometry state:** the existing T0 late-active width/depth summaries.
2. **Regime propensity:** provisional R3, the maximum 50 µm rolling-median
   penetration-depth/width ratio within the adaptive active interior.

G3, persistent depth over the same distance, should remain a companion
sensitivity.  It tests whether any apparent advantage of R3 is genuinely due
to width rather than depth alone.

## Why not collapse to a binary label now?

Only nine simulations contain a Keyhole-labelled frame.  More importantly,
every local labelling-provenance record identifies an automatic
per-experiment median-zmin threshold as the initial labelling method.  Human
verification is valuable, but the resulting depth agreement is not independent
validation.  A binary classifier or fixed regime threshold would therefore
look more certain than the available evidence permits.

## Later design options for Ioan

- Use a two-dimensional response: typical geometry plus persistent regime
  propensity.
- After updated independent relabelling, decide whether R3 alone is adequate
  as a continuous level-set target.
- If one scalar is required, confirm whether the physical definition should
  emphasize sustained aspect ratio (R3) or sustained absolute depth (G3).
- Do not reuse the exploratory dataset-specific threshold as a universal
  keyhole threshold.

No active-learning loop, acquisition function, GP classifier, or level-set
estimator is implemented in Phase 3.5.
